from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping
from unittest.mock import patch

import pytest

from core.evidence_ledger import CandidateDisposition
from core.ordinary_semantic_producer_runtime import (
    SKIP_REASON_ADMISSION_PREFLIGHT_FAILED,
    SKIP_REASON_BINDABLE_PASSAGE_MISSING,
    SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT,
    SKIP_REASON_CONTRACT_PREFLIGHT_FAILED,
    SKIP_REASON_COVERAGE_PREFLIGHT_FAILED,
    SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE,
    SKIP_REASON_SEARCH_WORK_PLAN_MISSING,
    OrdinarySemanticProducerBundle,
    OrdinarySemanticProducerComponentBundle,
    OrdinarySemanticProducerHandoffStatus,
    OrdinarySemanticProducerPreflightResult,
    OrdinarySemanticProducerTransactionError,
    build_ordinary_semantic_producer_bundle,
    build_question_meaning_record_from_search_work_plan,
    execute_ordinary_semantic_producer_handoff_from_scope,
    preflight_ordinary_semantic_producer_bundle,
    select_bindable_final_passage,
)
from core.run_authority_search_judgment import RunSearchJudgmentInput
from core.run_authority_search_judgment_validation import (
    build_deterministic_search_judgment,
)
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_PACKET,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    assert_no_semantic_state,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

AG_CHECK_01_QUERY = "What is the current official rule for Example Program?"
MULTIPART_QUERY = "What are the current official fee and legal deadline?"


def _compatibility_search_work_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    plan = deepcopy(dict(value or {}))
    metadata = dict(plan.get("metadata") or {})
    metadata["implements_query_shape_classifier"] = True
    plan["metadata"] = metadata
    return plan


def _capture_ag_check_01_handoff_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[RunKernel, dict[str, Any]]:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    return captured["run_kernel"], dict(captured["sufficiency_runtime_scope"])


def _fresh_kernel_for_handoff(source_kernel: RunKernel) -> RunKernel:
    kernel = RunKernel.start(
        run_id=f"{source_kernel.state.run_id}:handoff-retest",
        request_id=f"{source_kernel.state.request_id}:handoff-retest",
    )
    kernel.state.search_work_plan = _compatibility_search_work_plan(
        source_kernel.state.search_work_plan
    )
    kernel.state.evidence_ledger = deepcopy(source_kernel.state.evidence_ledger)
    return kernel


def _preflight_kwargs_from_capture(
    kernel: RunKernel,
    scope: Mapping[str, Any],
    *,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ledger = (
        dict(evidence_ledger_projection)
        if evidence_ledger_projection is not None
        else kernel.state.evidence_ledger.to_projection().to_dict()
    )
    return {
        "search_work_plan": _compatibility_search_work_plan(
            kernel.state.search_work_plan
        ),
        "route_projection": kernel.state.projections.get("route_request"),
        "run_contract_projection": scope["run_contract_projection"],
        "final_top_evidence": scope["final_top_evidence"],
        "evidence_ledger_projection": ledger,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "query": scope["query"],
        "requested_mode": scope.get("strategy"),
    }


def _component_payloads_from_bundle(
    bundle: OrdinarySemanticProducerBundle,
) -> list[dict[str, Any]]:
    return [
        {
            "answer_component_id": component_bundle.answer_component_id,
            "semantic_observation": component_bundle.semantic_observation.to_dict(),
            "sanitized_content_references": [
                ref.to_dict() for ref in component_bundle.sanitized_content_references
            ],
            "component_coverage_record": (
                component_bundle.component_coverage_record.to_dict()
            ),
        }
        for component_bundle in bundle.component_bundles
    ]


def _preflight_bundle_for_fresh_kernel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[RunKernel, OrdinarySemanticProducerBundle]:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kernel = _fresh_kernel_for_handoff(source_kernel)
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(kernel, scope)
    )
    assert preflight.bundle is not None
    return kernel, preflight.bundle


def _assert_atomic_failure_closed(kernel: RunKernel) -> None:
    assert_no_semantic_state(kernel)
    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=kernel.state.initial_answer_contract,
        component_coverage_history=kernel.state.component_coverage_history,
        contract_amendment_admission_history=(
            kernel.state.contract_amendment_admission_history
        ),
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    assert facts["accepted_contract_digest"] is None
    search_judgment = build_deterministic_search_judgment(
        RunSearchJudgmentInput(
            contract_projection={},
            evidence_ledger_projection=(
                kernel.state.evidence_ledger.to_projection().to_dict()
            ),
            helper_proposals={
                "semantic_state_facts": facts,
                "semantic_missing_assessments": [],
            },
        )
    )
    assert search_judgment.gaps == ()
    assert not kernel.state.final_answer_packet
    assert not kernel.state.author_observation


def _assert_failed_atomic_projection(kernel: RunKernel) -> None:
    projection = kernel.state.projections["semantic_producer_bundle_commit"]
    assert projection["semantic_producer_bundle_commit_failed"] is True
    assert projection["semantic_state_mutated"] is False


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _OfflineOrdinaryHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=AG_CHECK_01_QUERY,
            core_topic="Example Program current official rule",
            primary_entity="Example Program",
            raw_author_response=(
                "AG_SEM_11_AUTHOR_FINAL_REPORT: Example Program remains governed "
                "by the retrieved official rule."
            ),
            analyst_response=(
                "Analysis is limited to the retrieved official Example Program rule."
            ),
            logger_name="test_ag_sem_11",
        )
        self.weakened_evidence = False
        self.stale_readable_official = False

    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = [
            {
                "source_id": 1,
                "title": "Example Program official rule",
                "url": "https://www.irs.gov/example-program-fictional/rule",
                "text": (
                    "Example Program official current rule says the program "
                    "uses the current eligibility rule and remains in effect."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            }
        ]
        if not self.weakened_evidence:
            passages.append(
                {
                    "source_id": 2,
                    "title": "Example Program implementation memo",
                    "url": "https://www.irs.gov/example-program-fictional/memo",
                    "text": (
                        "Official implementation memo confirms the current rule "
                        "and gives supporting context for Example Program."
                    ),
                    "score": 0.97,
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "official_current_rules",
                    "_provider": "offline_fake_search",
                }
            )
        if self.stale_readable_official:
            for passage in passages:
                passage["currentness_signal"] = "stale"
        elif self.weakened_evidence:
            for passage in passages:
                passage["source_tier"] = "weak"
                passage["source_class"] = "contextual_secondary"
                passage["lower_tier"] = True
                passage["currentness_signal"] = "stale"
                passage["readable_status"] = "unreadable"
        return passages


def _run_offline_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    weakened_evidence: bool = False,
    stale_readable_official: bool = False,
) -> dict[str, Any]:
    harness = _OfflineOrdinaryHarness(tmp_path)
    harness.weakened_evidence = weakened_evidence
    harness.stale_readable_official = stale_readable_official
    captured, _outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-22",
        session_id="ag-sem-11-session",
        run_id="ag-sem-11-run",
        capture_stages=(HANDOFF_SUFFICIENCY, HANDOFF_PACKET),
    )
    return captured


def test_offline_run_pipeline_atomic_semantic_commit_reaches_real_sufficiency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    kernel = captured["run_kernel"]
    state = kernel.state

    assert state.initial_answer_contract
    assert state.semantic_observation_admission_history
    assert state.component_coverage_history

    component_ref = state.initial_answer_contract["accepted_answer_component_refs"][0]
    assert component_ref.get("source_obligation_candidate_ids")
    assert "obligation:official_current" in component_ref["source_obligation_candidate_ids"]

    coverage = state.component_coverage_history[-1]
    assert coverage.get("source_obligation_status") == "satisfied"
    ledger_binding = coverage.get("evidence_ledger_binding") or {}
    assert ledger_binding.get("source_requirement_ids")

    sufficiency_projection = captured["sufficiency_projection"]
    assert sufficiency_projection.get("semantic_consumption")
    assert sufficiency_projection.get("semantic_state_facts_summary")
    assert sufficiency_projection["semantic_consumption"].get("schema_version")
    assert sufficiency_projection["semantic_state_facts_summary"].get(
        "semantic_state_facts_digest"
    )


def test_stale_readable_official_evidence_blocks_satisfied_source_obligation_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    stale = _mutate_bound_candidate_in_projection(
        source_kernel,
        scope,
        currentness_signal="stale",
        readable_status="readable",
    )
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=stale,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_BINDABLE_PASSAGE_MISSING


def test_unqualified_or_stale_evidence_blocks_ready_direct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    weakened = _mutate_bound_candidate_in_projection(
        source_kernel,
        scope,
        source_class="secondary_analysis",
        source_tier="secondary",
        eligible_for_stronger_obligation=False,
    )
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=weakened,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED


def test_prerequisites_absent_leaves_no_orphan_initial_answer_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    source_kernel = captured["run_kernel"]
    kernel = RunKernel.start(run_id="run:sem-11-absent", request_id="request:sem-11-absent")
    kernel.state.search_work_plan = _compatibility_search_work_plan(
        source_kernel.state.search_work_plan
    )
    scope = dict(captured["sufficiency_runtime_scope"])
    scope["final_top_evidence"] = []
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_BINDABLE_PASSAGE_MISSING
    assert_no_semantic_state(kernel)


@pytest.mark.skip(
    reason="retired forward direct-producer success fixture has no current SearchOS compatibility input"
)
def test_preflight_bundle_builds_for_ag_check_01_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    kernel = captured["run_kernel"]
    scope = captured["sufficiency_runtime_scope"]
    bundle = build_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(kernel, scope),
    )
    assert bundle is not None
    assert bundle.question_meaning_record.record_id.startswith("qmr:")
    component = bundle.question_meaning_record.answer_components[0]
    assert component.source_obligation_candidate_ids
    assert "obligation:official_current" in component.source_obligation_candidate_ids
    assert bundle.component_coverage_record.coverage_state.value == "satisfied"
    assert bundle.component_coverage_record.source_obligation_status.value == "satisfied"
    assert bundle.component_coverage_record.evidence_ledger_binding.source_requirement_ids


@pytest.mark.skip(
    reason="retired forward direct-producer success fixture has no current SearchOS compatibility input"
)
def test_atomic_bundle_commit_commits_contract_observations_and_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, bundle = _preflight_bundle_for_fresh_kernel(tmp_path, monkeypatch)
    kernel.commit_semantic_producer_bundle(
        question_meaning_record=bundle.question_meaning_record.to_dict(),
        component_bundles=_component_payloads_from_bundle(bundle),
    )

    assert kernel.state.initial_answer_contract
    assert len(kernel.state.initial_answer_contract_history) == 1
    assert len(kernel.state.semantic_observation_admission_history) == len(
        bundle.component_bundles
    )
    assert len(kernel.state.component_coverage_history) == len(bundle.component_bundles)

    projection = kernel.state.projections["semantic_producer_bundle_commit"]
    assert projection["atomic_semantic_producer_commit"] is True
    assert projection["accepted_contract_committed"] is True
    assert projection["semantic_observation_count"] == len(bundle.component_bundles)
    assert projection["component_coverage_count"] == len(bundle.component_bundles)


@pytest.mark.skip(
    reason="retired forward bundle fixture is unavailable; direct atomic handoff failure remains executable"
)
def test_atomic_bundle_commit_failures_leave_no_semantic_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    mutations: tuple[
        tuple[str, Callable[[dict[str, Any], list[dict[str, Any]]], None]],
        ...,
    ] = (
        (
            "proposal_digest",
            lambda qmr, _payloads: qmr.update(record_digest="0" * 64),
        ),
        (
            "observation_digest",
            lambda _qmr, payloads: payloads[0]["semantic_observation"].update(
                claim_or_value="tampered claim without digest update",
            ),
        ),
        (
            "observation_contract_digest",
            lambda _qmr, payloads: payloads[0]["semantic_observation"].update(
                contract_digest="stale-contract-digest",
            ),
        ),
        (
            "coverage_digest",
            lambda _qmr, payloads: payloads[0]["component_coverage_record"].update(
                record_digest="0" * 64,
            ),
        ),
        (
            "coverage_payload_missing",
            lambda _qmr, payloads: payloads[0].update(
                component_coverage_record={},
            ),
        ),
    )

    for _case_name, mutate in mutations:
        kernel = _fresh_kernel_for_handoff(source_kernel)
        preflight = preflight_ordinary_semantic_producer_bundle(
            **_preflight_kwargs_from_capture(kernel, scope)
        )
        assert preflight.bundle is not None
        qmr_payload = preflight.bundle.question_meaning_record.to_dict()
        component_payloads = _component_payloads_from_bundle(preflight.bundle)
        mutate(qmr_payload, component_payloads)

        with pytest.raises(RunKernelTransitionError):
            kernel.commit_semantic_producer_bundle(
                question_meaning_record=qmr_payload,
                component_bundles=component_payloads,
            )

        _assert_atomic_failure_closed(kernel)
        _assert_failed_atomic_projection(kernel)


def test_handoff_atomic_commit_failure_leaves_no_semantic_state() -> None:
    from dataclasses import dataclass

    @dataclass
    class _FakeRecord:
        record_id: str
        record_digest: str

        def to_dict(self) -> dict[str, str]:
            return {"record_id": self.record_id, "record_digest": self.record_digest}

    @dataclass
    class _FakeObservation:
        observation_id: str
        observation_digest: str

        def to_dict(self) -> dict[str, str]:
            return {
                "observation_id": self.observation_id,
                "observation_digest": self.observation_digest,
            }

    kernel = RunKernel.start(run_id="run:sem-11-txn", request_id="request:sem-11-txn")
    kernel.state.search_work_plan = {
        "metadata": {
            "construction_metadata": {"implements_query_shape_classifier": True},
        }
    }
    bundle = OrdinarySemanticProducerBundle(
        question_meaning_record=_FakeRecord("qmr:test", "d" * 64),
        component_bundles=(
            OrdinarySemanticProducerComponentBundle(
                answer_component_id="component:test",
                semantic_observation=_FakeObservation("observation:test", "e" * 64),
                sanitized_content_references=(),
                component_coverage_record=_FakeRecord("coverage:test", "f" * 64),
                dry_run_admission_projection={},
            ),
        ),
        dry_run_accepted_contract={},
    )
    scope = {
        "query": AG_CHECK_01_QUERY,
        "strategy": "Balanced",
        "run_contract_projection": {},
        "final_top_evidence": [{"url": "https://example.test", "text": "bounded", "title": "t"}],
        "evidence_ledger_projection": {},
    }
    with patch(
        "core.ordinary_semantic_producer_runtime.preflight_ordinary_semantic_producer_bundle",
        return_value=OrdinarySemanticProducerPreflightResult(bundle=bundle),
    ):
        with patch.object(
            kernel,
            "commit_semantic_producer_bundle",
            side_effect=RunKernelTransitionError("forced"),
        ):
            with pytest.raises(
                OrdinarySemanticProducerTransactionError,
                match="atomic handoff failed",
            ):
                execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert_no_semantic_state(kernel)


def test_unit_multipart_assessment_builds_bounded_component_qmr() -> None:
    records = build_deterministic_search_work_runtime_records(
        DeterministicSearchWorkRuntimeInput(
            contract_id="ag-sem-11b-multipart",
            run_contract_projection={},
            route_facts={"core_topic": MULTIPART_QUERY, "primary_entity": "Example Program"},
            requested_mode="Balanced",
            selected_depth="Balanced",
            safe_query_preview=MULTIPART_QUERY,
        )
    )
    assert len(records.query_shape_assessment.component_candidates) >= 2
    qmr = build_question_meaning_record_from_search_work_plan(
        assessment=records.query_shape_assessment,
        route_facts={"core_topic": MULTIPART_QUERY},
        run_contract_projection={"contract_id": "ag-sem-11b-multipart"},
        run_id="run:multipart",
        request_id="request:multipart",
        query=MULTIPART_QUERY,
        requested_mode="Balanced",
    )
    assert qmr is not None
    assert len(qmr.answer_components) == len(records.query_shape_assessment.component_candidates)
    assert len(qmr.answer_components) <= 5
    assert len({component.component_id for component in qmr.answer_components}) == len(
        qmr.answer_components
    )
    preflight = preflight_ordinary_semantic_producer_bundle(
        search_work_plan={
            "metadata": {
                "construction_metadata": {"implements_query_shape_classifier": True},
            }
        },
        route_projection={"core_topic": MULTIPART_QUERY},
        run_contract_projection={"contract_id": "ag-sem-11b-multipart"},
        final_top_evidence=(),
        evidence_ledger_projection={},
        run_id="run:multipart",
        request_id="request:multipart",
        query=MULTIPART_QUERY,
        requested_mode="Balanced",
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_BINDABLE_PASSAGE_MISSING


def test_unit_stale_readable_candidate_is_not_bindable() -> None:
    url = "https://official.example/rule"
    candidate_id = (
        f"candidate:{hashlib.sha256(url.casefold().rstrip('/').encode()).hexdigest()[:16]}"
    )
    passage = {
        "url": url,
        "title": "Example Program official rule",
        "text": "Example Program official current rule remains in effect.",
        "currentness_signal": "stale",
    }
    projection = {
        "candidate_records": [
            {
                "candidate_id": candidate_id,
                "url": url,
                "readable_status": "readable",
                "fact_disposition": "accepted",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "stale",
            }
        ]
    }
    assert select_bindable_final_passage([passage], projection) is None


def test_handoff_preflight_uses_kernel_ledger_not_stale_scope_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kernel = _fresh_kernel_for_handoff(source_kernel)
    poisoned_scope = dict(scope)
    poisoned_scope["evidence_ledger_projection"] = {
        "candidate_records": [],
        "source_requirements": [],
        "requirement_links": [],
    }
    with patch(
        "core.ordinary_semantic_producer_runtime.preflight_ordinary_semantic_producer_bundle",
        wraps=preflight_ordinary_semantic_producer_bundle,
    ) as preflight_mock:
        result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, poisoned_scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED
    ledger_arg = preflight_mock.call_args.kwargs["evidence_ledger_projection"]
    assert ledger_arg == kernel.state.evidence_ledger.to_projection().to_dict()
    assert ledger_arg != poisoned_scope["evidence_ledger_projection"]


def test_handoff_prerequisite_guards_skip_without_reducing() -> None:
    missing_plan = RunKernel.start(
        run_id="run:sem-11-missing-plan",
        request_id="request:sem-11-missing-plan",
    )
    result = execute_ordinary_semantic_producer_handoff_from_scope(missing_plan, {})
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_SEARCH_WORK_PLAN_MISSING
    assert_no_semantic_state(missing_plan)

    existing_state = RunKernel.start(
        run_id="run:sem-11-existing-state",
        request_id="request:sem-11-existing-state",
    )
    existing_state.state.initial_answer_contract = {"sentinel": "contract"}
    existing_state.state.semantic_observation_admission_history = [
        {"sentinel": "admission"}
    ]
    existing_state.state.component_coverage_history = [{"sentinel": "coverage"}]
    before = (
        dict(existing_state.state.initial_answer_contract),
        list(existing_state.state.semantic_observation_admission_history),
        list(existing_state.state.component_coverage_history),
    )
    result = execute_ordinary_semantic_producer_handoff_from_scope(existing_state, {})
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT
    assert existing_state.state.initial_answer_contract == before[0]
    assert existing_state.state.semantic_observation_admission_history == before[1]
    assert existing_state.state.component_coverage_history == before[2]


def test_query_shape_classifier_unavailable_skips_without_orphan_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kernel = _fresh_kernel_for_handoff(source_kernel)
    kernel.state.search_work_plan = {
        "metadata": {
            "construction_metadata": {"runtime_shadow_scaffolding": True},
        }
    }
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE
    assert_no_semantic_state(kernel)


@pytest.mark.skip(
    reason="retired forward direct-producer success fixture has no current SearchOS compatibility input"
)
def test_multipart_assessment_can_commit_bounded_component_subset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kernel = _fresh_kernel_for_handoff(source_kernel)
    scope = dict(scope)
    scope["query"] = MULTIPART_QUERY
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.COMMITTED
    component_refs = kernel.state.initial_answer_contract["accepted_answer_component_refs"]
    assert len(component_refs) >= 2
    assert kernel.state.semantic_observation_admission_history
    assert kernel.state.component_coverage_history
    assert len(kernel.state.component_coverage_history) <= len(component_refs)


def _mutate_bound_candidate_in_projection(
    source_kernel: RunKernel,
    scope: Mapping[str, Any],
    *,
    evidence_ledger_projection: dict[str, Any] | None = None,
    **updates: Any,
) -> dict[str, Any]:
    ledger = dict(
        evidence_ledger_projection
        or source_kernel.state.evidence_ledger.to_projection().to_dict()
    )
    bindable = select_bindable_final_passage(scope["final_top_evidence"], ledger)
    assert bindable is not None
    bound_ref = bindable.evidence_ref_id
    bound_url = bindable.passage.get("url")
    mutated_records: list[dict[str, Any]] = []
    for record in ledger.get("candidate_records") or ():
        item = dict(record)
        candidate_id = item.get("candidate_id")
        url = item.get("url")
        if candidate_id == bound_ref or (bound_url and url == bound_url):
            item.update(updates)
        mutated_records.append(item)
    ledger["candidate_records"] = mutated_records
    return ledger


def test_coverage_preflight_blocks_obligation_incompatible_readable_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    incompatible = _mutate_bound_candidate_in_projection(
        source_kernel,
        scope,
        source_class="secondary_analysis",
        source_tier="secondary",
        readable_status="readable",
        eligible_for_stronger_obligation=False,
        lower_tier=False,
    )
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=incompatible,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED

    kernel = _fresh_kernel_for_handoff(source_kernel)
    bindable = select_bindable_final_passage(
        scope["final_top_evidence"],
        kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    assert bindable is not None
    candidate = kernel.state.evidence_ledger.candidates[bindable.evidence_ref_id]
    candidate.source_class = "secondary_analysis"
    candidate.source_tier = "secondary"
    candidate.readable_status = "readable"
    candidate.eligible_for_stronger_obligation = False
    candidate.lower_tier = False
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED
    assert_no_semantic_state(kernel)


def test_coverage_preflight_blocks_unlinked_source_requirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    ledger = dict(source_kernel.state.evidence_ledger.to_projection().to_dict())
    ledger["requirement_links"] = []
    ledger["source_requirements"] = [
        {**dict(requirement), "linked_candidate_ids": []}
        if isinstance(requirement, dict)
        else requirement
        for requirement in ledger.get("source_requirements") or ()
    ]
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=ledger,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED

    kernel = _fresh_kernel_for_handoff(source_kernel)
    kernel.state.evidence_ledger.links.clear()
    for requirement in kernel.state.evidence_ledger.requirements.values():
        requirement.linked_candidate_ids = ()
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED
    assert_no_semantic_state(kernel)


def test_coverage_preflight_blocks_unsatisfied_source_requirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    ledger = dict(source_kernel.state.evidence_ledger.to_projection().to_dict())
    requirements = [dict(item) for item in ledger.get("source_requirements") or ()]
    for requirement in requirements:
        requirement["status"] = "unsatisfied"
    ledger["source_requirements"] = requirements
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=ledger,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED


def test_coverage_preflight_blocks_custody_gap_on_requirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    ledger = dict(source_kernel.state.evidence_ledger.to_projection().to_dict())
    bindable = select_bindable_final_passage(scope["final_top_evidence"], ledger)
    assert bindable is not None
    requirement_ids = [
        link.get("requirement_id")
        for link in ledger.get("requirement_links") or ()
        if isinstance(link, dict)
        and link.get("candidate_id") == bindable.evidence_ref_id
        and link.get("requirement_id")
    ]
    assert requirement_ids
    ledger["custody_gaps"] = [
        {"requirement_id": requirement_id} for requirement_id in requirement_ids
    ]
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=ledger,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED


def test_coverage_preflight_blocks_observed_disposition_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    ledger = _mutate_bound_candidate_in_projection(
        source_kernel,
        scope,
        fact_disposition="observed",
        readable_status="readable",
    )
    preflight = preflight_ordinary_semantic_producer_bundle(
        **_preflight_kwargs_from_capture(
            source_kernel,
            scope,
            evidence_ledger_projection=ledger,
        )
    )
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED

    kernel = _fresh_kernel_for_handoff(source_kernel)
    bindable = select_bindable_final_passage(
        scope["final_top_evidence"],
        kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    assert bindable is not None
    candidate = kernel.state.evidence_ledger.candidates[bindable.evidence_ref_id]
    candidate.fact_disposition = CandidateDisposition.OBSERVED
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_COVERAGE_PREFLIGHT_FAILED
    assert_no_semantic_state(kernel)


def test_contract_preflight_failed_skipped_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kwargs = _preflight_kwargs_from_capture(source_kernel, scope)
    with patch(
        "core.ordinary_semantic_producer_runtime._dry_run_accepted_contract",
        return_value=None,
    ):
        preflight = preflight_ordinary_semantic_producer_bundle(**kwargs)
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_CONTRACT_PREFLIGHT_FAILED


def test_admission_preflight_failed_skipped_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_kernel, scope = _capture_ag_check_01_handoff_inputs(tmp_path, monkeypatch)
    kwargs = _preflight_kwargs_from_capture(source_kernel, scope)
    with patch(
        "core.ordinary_semantic_producer_runtime._dry_run_admission_projection",
        return_value=None,
    ):
        preflight = preflight_ordinary_semantic_producer_bundle(**kwargs)
    assert preflight.bundle is None
    assert preflight.skipped_reason == SKIP_REASON_ADMISSION_PREFLIGHT_FAILED
