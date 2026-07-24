from __future__ import annotations

import inspect
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline_orchestrator as pipeline_orchestrator
import core.run_authority_sufficiency_adapter as sufficiency_adapter
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_SCRUTINEER,
    ROLE_SYSTEM_PROMPTS,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.searchos_existing_gap_recovery_runtime import (
    MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES,
    SearchOSExistingGapRecoveryError,
    _digest,
    _envelope,
    _refresh_state,
    admit_searchos_existing_gap_recovery_cycle,
    build_searchos_existing_gap_basis,
    build_searchos_materially_novel_recovery_purpose,
    finalize_searchos_existing_gap_recovery_cycle,
    validate_active_searchos_recovery_cycle_ref,
    validate_searchos_existing_gap_basis,
    validate_searchos_recovery_purpose,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
)
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _official_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating rule",
            "url": "https://alpha.gov/operating-rule",
            "text": ("Alpha's current official operating rule sets an operating rate of 14 units per hour."),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _initial_incomplete_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating overview",
            "url": "https://alpha.gov/operating-overview",
            "text": (
                "Alpha publishes an official operating rule, but this overview "
                "omits the name of its current operating protocol."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _recovered_official_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating protocol",
            "url": "https://alpha.gov/operating-protocol",
            "text": (
                "Alpha's current official operating protocol is Raven."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _recovered_numeric_evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha official operating rate details",
            "url": "https://alpha.gov/operating-rate-details",
            "text": (
                "Alpha's current official operating rate is 14 units per hour."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "sourced_numeric_values",
            "currentness_signal": "current",
            "evidence_material_type": "structured_numeric",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _initial_incomplete_canonical_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha canonical API documentation",
            "url": "https://docs.alpha.example/api",
            "text": (
                "Alpha's canonical API documentation lists the endpoint, "
                "but omits its current response name."
            ),
            "credibility": 4,
            "source_tier": "canonical",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
        {
            "title": "Alpha API overview",
            "url": "https://example.test/alpha-api-overview",
            "text": (
                "A secondary overview confirms that Alpha publishes an API, "
                "without stating the current canonical response name."
            ),
            "credibility": 3,
            "source_tier": "secondary",
            "source_class": "reputable_secondary",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
    ]


def _recovered_canonical_rows() -> list[dict[str, Any]]:
    return [
        {
            "title": "Alpha canonical Raven endpoint documentation",
            "url": "https://docs.alpha.example/api/raven",
            "text": (
                "Alpha's current canonical API response name is Raven."
            ),
            "credibility": 4,
            "source_tier": "canonical",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        }
    ]


def _capture_sufficiency_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> list[Any]:
    captured: list[Any] = []
    original = (
        sufficiency_adapter.build_sufficiency_judgment_input_from_runtime
    )

    def wrapped(**kwargs: Any) -> Any:
        judgment_input = original(**kwargs)
        captured.append(judgment_input)
        return judgment_input

    monkeypatch.setattr(
        sufficiency_adapter,
        "build_sufficiency_judgment_input_from_runtime",
        wrapped,
    )
    return captured


def _forbid_post_terminal_blocked_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError(
            "post-terminal SearchOS blocked-FAP bypass was invoked"
        )

    monkeypatch.setattr(
        RunKernel,
        "authorize_searchos_required_needs_block",
        forbidden,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_required_needs_blocked_fap_projection",
        forbidden,
    )


def _install_initially_unsupported_component(
    monkeypatch: pytest.MonkeyPatch,
    *,
    remain_unsupported: bool,
    recovered_claim: str | None = None,
) -> None:
    original = PostRetirementOrdinaryPipelineHarness.ask_model
    analyst_calls = 0

    def scripted(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal analyst_calls
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            analyst_calls += 1
            if analyst_calls == 1 or remain_unsupported:
                self._record_model_call(system_prompt, kwargs)
                return json.dumps(
                    {
                        "claim_text": ("The current bounded material does not yet support this component."),
                        "support_status": "unsupported",
                        "caveats": [],
                        "nonclaims": ["No component conclusion is admitted."],
                        "blockers": ["exact_obligation_support_missing"],
                    }
                )
            if recovered_claim:
                self._record_model_call(system_prompt, kwargs)
                return json.dumps(
                    {
                        "claim_text": recovered_claim,
                        "support_status": "supported",
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
        return original(self, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        scripted,
    )


def _capture_first_gap_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    original = pipeline_orchestrator.build_searchos_existing_gap_basis

    def wrapped(**kwargs: Any) -> dict[str, Any]:
        try:
            basis = original(**kwargs)
        except Exception as exc:
            if not captured:
                captured.update(
                    {
                        "error": f"{type(exc).__name__}:{exc}",
                        "state": deepcopy(kwargs["state"]),
                        "slot_id": kwargs["slot_id"],
                        "component_admission_projection": deepcopy(
                            kwargs["component_admission_projection"]
                        ),
                    }
                )
            raise
        if not captured:
            captured.update(
                {
                    "state": deepcopy(kwargs["state"]),
                    "slot_id": kwargs["slot_id"],
                    "component_admission_projection": deepcopy(kwargs["component_admission_projection"]),
                    "component_coverage_history": deepcopy(kwargs["component_coverage_history"]),
                    "evidence_ledger_projection": deepcopy(kwargs["evidence_ledger_projection"]),
                    "basis": deepcopy(basis),
                }
            )
        return basis

    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_existing_gap_basis",
        wrapped,
    )
    return captured


def _reenvelope_gap_basis(
    basis: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in basis.items()
        if key
        not in {
            "gap_basis_id",
            "gap_basis_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    return _envelope(
        core,
        id_field="gap_basis_id",
        digest_field="gap_basis_digest",
        prefix="searchos-gap-basis",
    )


def _reenvelope_recovery_purpose(
    purpose: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in purpose.items()
        if key
        not in {
            "recovery_purpose_id",
            "recovery_purpose_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    return _envelope(
        core,
        id_field="recovery_purpose_id",
        digest_field="recovery_purpose_digest",
        prefix="searchos-recovery-purpose",
    )


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_product_existing_gap_recovers_through_same_component_roles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    captured_gap = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)

    def forbidden_dynamic_recovery(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("retained Scrutineer-derived recovery path was invoked")

    def forbidden_legacy_recovery(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("legacy existing-gap recovery path was invoked")

    monkeypatch.setattr(
        multicomponent_runtime,
        "_begin_scheduler_dynamic_recovery",
        forbidden_dynamic_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_component_gap_recovery",
        forbidden_legacy_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "run_source_class_recovery_dispatch",
        forbidden_legacy_recovery,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_run_authority_search_judgment_action",
        forbidden_legacy_recovery,
    )
    recovery_results: list[Any] = []
    reassessment_errors: list[str] = []
    original_recovery = (
        pipeline_orchestrator.execute_searchos_existing_gap_recovery_cycle
    )

    def capture_recovery(**kwargs: Any) -> Any:
        result = original_recovery(**kwargs)
        recovery_results.append(result)
        return result

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_searchos_existing_gap_recovery_cycle",
        capture_recovery,
    )
    original_reassessment = (
        pipeline_orchestrator
        .execute_searchos_same_component_reassessment_from_scope
    )

    def capture_reassessment(*args: Any, **kwargs: Any) -> Any:
        try:
            return original_reassessment(*args, **kwargs)
        except Exception as exc:
            reassessment_errors.append(f"{type(exc).__name__}:{exc}")
            raise

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_searchos_same_component_reassessment_from_scope",
        capture_reassessment,
    )
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current canonical API response name is Raven."
        ),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode=mode,
        query=(
            "What do Alpha's current API docs say about the Raven endpoint?"
        ),
        core_topic="Alpha current API documentation",
        primary_entity="Alpha",
        researcher_queries=["Alpha current API documentation"],
        evidence_rows=_initial_incomplete_canonical_rows(),
        followup_evidence_rows=_recovered_canonical_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://docs.alpha.example/api": (
                "Alpha's canonical API documentation lists the endpoint, "
                "but omits its current response name."
            ),
            "https://docs.alpha.example/api/raven": (
                "Alpha's current canonical API response name is Raven."
            ),
            "https://example.test/alpha-api-overview": (
                "A secondary overview confirms that Alpha publishes an API, "
                "without stating the current canonical response name."
            ),
        },
        raw_author_response=(
            "Alpha's current canonical API response name is Raven. "
            "[[1]](https://docs.alpha.example/api/raven)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    admission = kernel.state.projections["multicomponent_component_admission"]
    role_system_prompts = [item["system_prompt"] for item in harness.model_calls]

    assert terminal["terminal_status"] == "recovered", (
        terminal["terminal_reason"],
        terminal["expenditure"],
        {
            key: kernel.state.searchos_state["slots_by_id"][terminal["recovery_slot_ref"]["slot_id"]].get(key)
            for key in (
                "posture",
                "latest_reason",
                "judgment_call_count",
                "custody_refs",
                "action_history",
            )
        },
        outcome.execution_trace["searchos_slice_a"]["existing_gap_recovery"].get("same_component_reassessment"),
        reassessment_errors,
    )
    assert terminal["coverage_gained"] is True
    assert terminal["gap_remains"] is False
    assert terminal["further_existing_gap_recovery_authorized"] is False
    assert terminal["final_sufficiency_decided"] is False
    assert len(recovery_results) == 1
    initial_material = json.dumps(
        harness.searchos_semantic_material_before_pipeline_consumption,
        sort_keys=True,
    )
    recovered_material = json.dumps(
        recovery_results[0].searchos_semantic_material,
        sort_keys=True,
    )
    assert "response name is Raven" not in initial_material
    assert "response name is Raven" in recovered_material
    assert any(
        item.get("recovery_cycle_id")
        for item in harness.read_assessment_calls
    )
    assert len(harness.search_calls) == 2
    recovery_query_items = [
        item
        for item in outcome.execution_trace["query_plan"]["items"]
        if item.get("authorized_query")
        == "Alpha exact current official operating protocol details"
    ]
    assert len(recovery_query_items) == 1
    assert recovery_query_items[0]["iteration"] == 2
    assert admission["component_count"] == 2
    assert admission["component_admission_refs"][0]["admission_status"] == "unsupported"
    assert admission["component_admission_refs"][1]["admission_status"] in {"admitted", "admitted_with_caveats"}
    assert admission["component_admission_refs"][1]["same_component_reassessment"] is True
    recovered_coverage_ref = admission["component_admission_refs"][1][
        "component_coverage_ref"
    ]
    assert kernel.state.component_coverage_history[-1][
        "coverage_record_digest"
    ] == recovered_coverage_ref["coverage_record_digest"]
    recovered_evidence_ids = {
        item["evidence_ref_id"]
        for item in admission["component_admission_refs"][1]["evidence_refs"]
    }
    current_ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    recovered_candidates = [
        item
        for item in current_ledger["candidate_records"]
        if item.get("candidate_id") in recovered_evidence_ids
    ]
    assert recovered_candidates
    assert all(
        item.get("final_evidence_eligible") is True
        for item in recovered_candidates
    )
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    target_requirement_ids = kernel.state.component_coverage_history[-1][
        "evidence_ledger_binding"
    ]["source_requirement_ids"]
    assert len(target_requirement_ids) == 1
    target_requirement = next(
        item
        for item in current_ledger["source_requirements"]
        if item.get("requirement_id") == target_requirement_ids[0]
    )
    target_links = [
        item
        for item in current_ledger["requirement_links"]
        if item.get("requirement_id") == target_requirement_ids[0]
    ]
    cycle = kernel.state.searchos_state[
        "existing_gap_recovery_cycles"
    ][0]
    purpose = build_searchos_materially_novel_recovery_purpose(
        captured_gap["basis"]
    )
    _preview_state, preview_admission = (
        admit_searchos_existing_gap_recovery_cycle(
            state=captured_gap["state"],
            gap_basis=captured_gap["basis"],
            recovery_purpose=purpose,
        )
    )
    assert {
        captured_gap["basis"]["source_obligation_ref"][
            "source_obligation_id"
        ],
        purpose["source_obligation_ref"]["source_obligation_id"],
        cycle["source_obligation_ref"]["source_obligation_id"],
        cycle["recovery_slot_ref"]["source_obligation_id"],
        target_requirement["source_obligation_id"],
        terminal["source_obligation_ref"]["source_obligation_id"],
        terminal["recovery_slot_ref"]["source_obligation_id"],
    } == {target_obligation_id}
    assert preview_admission["lease"]["source_obligation_ref"][
        "source_obligation_id"
    ] == target_obligation_id
    assert {
        item["requirement_id"] for item in target_links
    } == set(target_requirement_ids)
    assert len(
        [
            item
            for item in target_links
            if item["candidate_id"] in recovered_evidence_ids
        ]
    ) == 1
    assert (
        terminal["component_coverage_ref"]["coverage_record_digest"]
        == recovered_coverage_ref["coverage_record_digest"]
    )
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]) == 2
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]) == 2
    assert ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER] not in role_system_prompts
    assert not harness.full_search_judgment_inputs
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency, (
        outcome.report,
        {
            key: outcome.execution_trace["searchos_slice_a"]
            .get("readiness_projection", {})
            .get(key)
            for key in (
                "all_required_slots_slice_a_ready",
                "unresolved_required_slots",
                "author_execution_allowed",
                "final_answer_packet_allowed",
            )
        },
    )
    assert sufficiency["decision"] == "ready_direct", json.dumps({
        "missing": [
            {
                key: item.get(key)
                for key in (
                    "requirement_id",
                    "requirement_kind",
                    "component_id",
                    "source_obligation_id",
                    "status",
                    "reason",
                )
            }
            for item in sufficiency["missing_required_obligations"]
        ],
        "partial": sufficiency["partial_obligations"],
        "readiness_reasons": sufficiency["readiness_reasons"],
        "rationale": sufficiency["rationale"],
        "terminal_assessments": sufficiency[
            "searchos_existing_gap_recovery_terminal_consumption"
        ]["required_source_obligation_assessments"],
    }, sort_keys=True)
    assert sufficiency["final_answer_posture"] == "direct_answer"
    assert sufficiency["contract_fulfilled"] is True
    assert sufficiency["required_obligations_satisfied"] is True
    assert sufficiency["final_answer_allowed"] is True
    assert sufficiency_inputs
    terminal_input = sufficiency_inputs[-1]
    assert (
        terminal_input.searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    terminal_consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert terminal_consumption["terminal_status"] == "recovered"
    assert (
        terminal_consumption["source_obligation_ref"][
            "source_obligation_id"
        ]
        == target_obligation_id
    )
    assert terminal_consumption["target_requirement_ids"] == (
        target_requirement_ids
    )
    assert "response name is Raven" in outcome.report
    assert harness.author_prompts
    assert "Raven" in harness.author_prompts[-1]
    assert "could not produce a supported answer" not in outcome.report


def test_two_obligation_recovery_credits_only_the_exact_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
        recovered_claim=(
            "Alpha's current official operating protocol is Raven."
        ),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_initial_incomplete_evidence_rows(),
        followup_evidence_rows=_recovered_official_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-overview": (
                "Alpha publishes an official operating rule, but this overview "
                "omits the name of its current operating protocol."
            ),
            "https://alpha.gov/operating-protocol": (
                "Alpha's current official operating protocol is Raven."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating protocol is Raven. "
            "[[1]](https://alpha.gov/operating-protocol)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections[
        "searchos_existing_gap_recovery_terminal"
    ]
    assert terminal["terminal_status"] == "recovered", terminal
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    component_ref = terminal["component_ref"]
    component_obligation_ids = set(
        next(
            item
            for item in kernel.state.initial_answer_contract[
                "accepted_answer_component_refs"
            ]
            if item["component_id"] == component_ref["component_id"]
        )["source_obligation_candidate_ids"]
    )
    assert len(component_obligation_ids) == 2
    sibling_obligation_id = next(
        item
        for item in component_obligation_ids
        if item != target_obligation_id
    )
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    coverage = kernel.state.component_coverage_history[-1]
    target_requirement_ids = coverage["evidence_ledger_binding"][
        "source_requirement_ids"
    ]
    assert target_requirement_ids
    target_requirements = [
        item
        for item in ledger["source_requirements"]
        if item.get("requirement_id") in target_requirement_ids
    ]
    assert {
        item.get("source_obligation_id")
        for item in target_requirements
    } == {target_obligation_id}
    recovered_candidate_ids = {
        item["evidence_ref_id"]
        for item in kernel.state.projections[
            "multicomponent_component_admission"
        ]["component_admission_refs"][-1]["evidence_refs"]
    }
    novel_ids = set(
        outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("materially_novel_recovery_evidence_ids") or ()
    )
    assert recovered_candidate_ids == novel_ids, {
        "recovered": recovered_candidate_ids,
        "novel": novel_ids,
        "reassessment": outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("same_component_reassessment"),
    }
    recovered_links = [
        item
        for item in ledger["requirement_links"]
        if item.get("candidate_id") in recovered_candidate_ids
        and item.get("requirement_id") in target_requirement_ids
    ]
    assert len(recovered_links) == len(target_requirement_ids)
    assert not [
        item
        for item in ledger["source_requirements"]
        if item.get("source_obligation_id") == sibling_obligation_id
        and item.get("requirement_id") in target_requirement_ids
    ]
    assert not [
        item
        for item in ledger["requirement_links"]
        if item.get("candidate_id") in recovered_candidate_ids
        and any(
            requirement.get("requirement_id")
            == item.get("requirement_id")
            and requirement.get("source_obligation_id")
            == sibling_obligation_id
            for requirement in ledger["source_requirements"]
        )
    ]
    semantic_outcomes = outcome.execution_trace["searchos_slice_a"][
        "semantic_outcomes_by_slot"
    ]
    target_original_slot = next(
        slot_id
        for slot_id, slot in kernel.state.searchos_state[
            "slots_by_id"
        ].items()
        if slot["slot_ref"].get("source_obligation_id")
        == target_obligation_id
        and not slot["slot_ref"].get("recovery_cycle_id")
    )
    sibling_slot = next(
        slot_id
        for slot_id, slot in kernel.state.searchos_state[
            "slots_by_id"
        ].items()
        if slot["slot_ref"].get("source_obligation_id")
        == sibling_obligation_id
    )
    assert semantic_outcomes[target_original_slot][
        "searchos_handoff_material_consumed"
    ] is True
    assert semantic_outcomes[sibling_slot][
        "searchos_handoff_material_consumed"
    ] is False
    readiness = outcome.execution_trace["searchos_slice_a"][
        "readiness_projection"
    ]
    sibling_readiness = next(
        item
        for item in readiness["slot_records"]
        if item["slot_ref"]["slot_id"] == sibling_slot
    )
    assert sibling_readiness["slice_a_ready"] is False
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["decision"] != "satisfied"
    assert sufficiency["final_answer_posture"] != "satisfied"
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assessments = {
        item["source_obligation_id"]: item
        for item in consumption[
            "required_source_obligation_assessments"
        ]
    }
    assert assessments[target_obligation_id]["status"] == "satisfied"
    assert assessments[sibling_obligation_id]["status"] != "satisfied"
    assert sufficiency_inputs[-1].to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_aggregate_id"] == terminal["terminal_aggregate_id"]
    if sufficiency["final_answer_allowed"]:
        assert sufficiency["final_answer_posture"] == "partial_answer"
        assert harness.author_prompts
    else:
        assert not harness.author_prompts


def test_two_obligation_recovery_completes_with_prior_sibling_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_gap = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    original_ask_model = PostRetirementOrdinaryPipelineHarness.ask_model
    analyst_calls = 0

    def scripted_model(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal analyst_calls
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            analyst_calls += 1
            self._record_model_call(system_prompt, kwargs)
            return json.dumps(
                {
                    "claim_text": (
                        "Alpha's current official operating rule is "
                        "canonically published."
                        if analyst_calls == 1
                        else (
                            "Alpha's current official operating rate is "
                            "14 units per hour."
                        )
                    ),
                    "support_status": "supported",
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        return original_ask_model(
            self,
            prompt,
            system_prompt,
            **kwargs,
        )

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        scripted_model,
    )
    original_outcomes = (
        pipeline_orchestrator.build_searchos_semantic_outcomes_by_slot
    )

    def keep_numeric_obligation_unresolved_until_recovery(
        **kwargs: Any,
    ) -> dict[str, dict[str, Any]]:
        outcomes = original_outcomes(**kwargs)
        admissions = list(
            dict(kwargs["component_admission_projection"]).get(
                "component_admission_refs"
            )
            or ()
        )
        if not any(
            dict(item).get("searchos_recovery_cycle_ref")
            for item in admissions
            if isinstance(item, Mapping)
        ):
            for slot_id, outcome in outcomes.items():
                if slot_id.endswith("obligation:source_bound_numeric"):
                    outcome.update(
                        {
                            "component_analyst_proposal_ref": {},
                            "component_analyst_proposal_status": (
                                "not_proposed"
                            ),
                            "component_dprime_validation_ref": {},
                            "component_dprime_validation_status": (
                                "not_accepted"
                            ),
                            "semantic_admission_outcome_ref": {},
                            "semantic_admission_status": "not_admitted",
                            "searchos_handoff_material_consumed": False,
                        }
                    )
        return outcomes

    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_semantic_outcomes_by_slot",
        keep_numeric_obligation_unresolved_until_recovery,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating protocol?",
        core_topic="Alpha current official operating protocol",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating protocol"],
        evidence_rows=_official_evidence_rows(),
        followup_evidence_rows=_recovered_numeric_evidence_rows(),
        read_assessment_decision="RECOVERY_FOLLOWUP_THEN_READ",
        read_content_by_url={
            "https://alpha.gov/operating-rule": (
                "Alpha's current official operating rule is canonically "
                "published."
            ),
            "https://alpha.gov/operating-rate-details": (
                "Alpha's current official operating rate is 14 units per hour."
            ),
        },
        raw_author_response=(
            "Alpha's current official operating rule is canonically published. "
            "[[1]](https://alpha.gov/operating-rule)"
        ),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    assert "searchos_existing_gap_recovery_terminal" in kernel.state.projections, {
        slot_id: {
            "posture": slot.get("posture"),
            "latest_reason": slot.get("latest_reason"),
        }
        for slot_id, slot in kernel.state.searchos_state.get(
            "slots_by_id", {}
        ).items()
    }
    terminal = kernel.state.projections[
        "searchos_existing_gap_recovery_terminal"
    ]
    assert terminal["terminal_status"] == "recovered", (
        terminal["terminal_reason"],
        terminal["terminal_blocker"],
        outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ],
    )
    target_obligation_id = terminal["source_obligation_ref"][
        "source_obligation_id"
    ]
    assert target_obligation_id == "obligation:source_bound_numeric"
    component_obligation_ids = set(
        next(
            item
            for item in kernel.state.initial_answer_contract[
                "accepted_answer_component_refs"
            ]
            if item["component_id"]
            == terminal["component_ref"]["component_id"]
        )["source_obligation_candidate_ids"]
    )
    assert len(component_obligation_ids) == 2
    sibling_obligation_id = next(
        item
        for item in component_obligation_ids
        if item != target_obligation_id
    )
    prior_ledger = captured_gap["evidence_ledger_projection"]
    prior_sibling_requirements = [
        deepcopy(item)
        for item in prior_ledger["source_requirements"]
        if item.get("source_obligation_id") == sibling_obligation_id
        and item.get("status") == "satisfied"
    ]
    assert prior_sibling_requirements
    prior_sibling_ids = {
        item["requirement_id"] for item in prior_sibling_requirements
    }
    prior_sibling_links = [
        deepcopy(item)
        for item in prior_ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
    ]
    assert prior_sibling_links
    prior_coverage = deepcopy(
        captured_gap["component_coverage_history"][-1]
    )

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    current_sibling_requirements = [
        item
        for item in ledger["source_requirements"]
        if item.get("requirement_id") in prior_sibling_ids
    ]
    assert [
        {
            key: value
            for key, value in item.items()
            if key != "linked_candidate_ids"
        }
        for item in current_sibling_requirements
    ] == [
        {
            key: value
            for key, value in item.items()
            if key != "linked_candidate_ids"
        }
        for item in prior_sibling_requirements
    ]
    assert [
        item
        for item in ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
    ] == prior_sibling_links
    assert kernel.state.component_coverage_history[0] == prior_coverage
    terminal_coverage_ref = terminal["component_coverage_ref"]
    assert terminal_coverage_ref.get("coverage_record_id"), (
        terminal_coverage_ref
    )
    matching_terminal_coverage = [
        item
        for item in kernel.state.component_coverage_history
        if item.get("coverage_record_id")
        == terminal_coverage_ref["coverage_record_id"]
        and item.get("coverage_record_digest")
        == terminal_coverage_ref["coverage_record_digest"]
    ]
    assert len(matching_terminal_coverage) == 1, {
        "terminal_coverage_ref": terminal_coverage_ref,
        "coverage_history_refs": [
            {
                "coverage_record_id": item.get("coverage_record_id"),
                "coverage_record_digest": item.get(
                    "coverage_record_digest"
                ),
            }
            for item in kernel.state.component_coverage_history
        ],
    }
    coverage = matching_terminal_coverage[0]
    target_requirement_ids = coverage["evidence_ledger_binding"][
        "source_requirement_ids"
    ]
    recovered_candidate_ids = {
        item["evidence_ref_id"]
        for item in kernel.state.projections[
            "multicomponent_component_admission"
        ]["component_admission_refs"][-1]["evidence_refs"]
    }
    assert len(target_requirement_ids) == 1, {
        "target_obligation_id": target_obligation_id,
        "target_requirement_ids": target_requirement_ids,
        "recovered_candidate_ids": recovered_candidate_ids,
        "recovered_candidate_links": [
            item
            for item in ledger["requirement_links"]
            if item.get("candidate_id") in recovered_candidate_ids
        ],
        "novel_ids": outcome.execution_trace["searchos_slice_a"][
            "existing_gap_recovery"
        ].get("materially_novel_recovery_evidence_ids"),
        "reassessment_evidence_refs": outcome.execution_trace[
            "searchos_slice_a"
        ]["existing_gap_recovery"].get(
            "same_component_reassessment", {}
        ).get("component_admission_ref", {}).get("evidence_refs"),
    }
    assert not prior_sibling_ids.intersection(target_requirement_ids)
    assert not [
        item
        for item in ledger["requirement_links"]
        if item.get("requirement_id") in prior_sibling_ids
        and item.get("candidate_id") in recovered_candidate_ids
    ]
    sufficiency = kernel.state.sufficiency_judgment_projection
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assessments = {
        item["source_obligation_id"]: item
        for item in consumption[
            "required_source_obligation_assessments"
        ]
    }
    assert assessments[target_obligation_id]["status"] == "satisfied"
    assert assessments[sibling_obligation_id]["status"] == "satisfied"
    assert sufficiency["decision"] == "ready_direct", (
        sufficiency.get("required_obligations_satisfied"),
        sufficiency.get("missing_obligations"),
        sufficiency.get("partial_obligations"),
        sufficiency.get("readiness_reasons"),
    )
    assert sufficiency["final_answer_posture"] == "direct_answer"
    assert sufficiency["contract_fulfilled"] is True
    assert sufficiency["required_obligations_satisfied"] is True
    assert sufficiency["final_answer_allowed"] is True
    assert sufficiency_inputs[-1].to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_aggregate_id"] == terminal["terminal_aggregate_id"]
    assert harness.author_prompts
    assert "canonically published" in outcome.report


def test_product_existing_gap_exhaustion_reaches_sufficiency_posture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    trace = outcome.execution_trace["searchos_slice_a"]
    assert terminal["terminal_status"] == "exhausted_insufficient"
    assert terminal["coverage_gained"] is False
    assert terminal["gap_remains"] is True
    assert terminal["whole_run_lease_status"] == (
        "settled_exhausted_insufficient"
    )
    assert terminal["local_budget_status"]["terminal"] is True
    assert terminal["novelty_exhausted"] is True
    assert (
        terminal[
            "lawful_materially_novel_recovery_purpose_remains"
        ]
        is False
    )
    recovery_slot = kernel.state.searchos_state["slots_by_id"][
        terminal["recovery_slot_ref"]["slot_id"]
    ]
    recovery_cycle = kernel.state.searchos_state[
        "existing_gap_recovery_cycles"
    ][0]
    prior_slot = kernel.state.searchos_state["slots_by_id"][
        recovery_cycle["prior_terminal_slot_ref"]["slot_id"]
    ]
    assert any(
        item.get("same_normalized_url_reused") is True
        for item in recovery_slot["custody_refs"]
    )
    assert {
        item["evidence_ledger_candidate_id"]
        for item in recovery_slot["custody_refs"]
    } <= {
        item["evidence_ledger_candidate_id"]
        for item in prior_slot["custody_refs"]
    }
    assert not kernel.state.component_coverage_history
    assert not kernel.state.semantic_observation_admission_history
    assert sufficiency_inputs
    terminal_input = sufficiency_inputs[-1]
    assert (
        terminal_input.searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    assert terminal_input.to_model_payload()[
        "searchos_existing_gap_recovery_terminal_ref"
    ]["terminal_status"] == "exhausted_insufficient"
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["final_answer_posture"] in {
        "partial_answer",
        "insufficient",
        "blocked",
    }
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert consumption["terminal_status"] == "exhausted_insufficient"
    assert consumption["target_source_truth_status"] != "satisfied"
    assert trace["existing_gap_recovery"]["derived_component_recovery_invoked"] is False
    assert trace["existing_gap_recovery"]["scrutineer_recovery_input_used"] is False
    if sufficiency["final_answer_allowed"]:
        assert sufficiency["final_answer_posture"] == "partial_answer"
        assert harness.author_prompts
        assert "could not produce a supported answer" not in outcome.report
    else:
        assert not harness.author_prompts


def test_recovery_policy_limit_and_exact_replay_do_not_open_more_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )
    kernel = harness.run_kernel
    assert kernel is not None
    terminal_state = deepcopy(kernel.state.searchos_state)
    pre_state = captured["state"]
    basis = captured["basis"]
    purpose = build_searchos_materially_novel_recovery_purpose(basis)
    prior_slot_id = basis["prior_terminal_slot_ref"]["slot_id"]
    prior_slot = deepcopy(pre_state["slots_by_id"][prior_slot_id])
    admitted_state, admission = admit_searchos_existing_gap_recovery_cycle(
        state=pre_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )

    assert len(pre_state["existing_gap_recovery_cycles"]) == 0
    assert admission["work_authorized"] is True
    assert len(admitted_state["existing_gap_recovery_cycles"]) == 1
    assert admitted_state["slots_by_id"][prior_slot_id] == prior_slot
    assert admitted_state["active_slot_ids"][:-1] == pre_state["active_slot_ids"]
    assert admitted_state["required_slot_ids"][:-1] == pre_state["required_slot_ids"]
    assert (
        admitted_state["budget"]["charged_logical_judgment_calls"]
        == pre_state["budget"]["charged_logical_judgment_calls"]
    )

    replayed_state, replay = admit_searchos_existing_gap_recovery_cycle(
        state=admitted_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )
    assert replayed_state == admitted_state
    assert replay == {
        **replay,
        "status": "already_admitted",
        "exact_replay": True,
        "work_authorized": False,
    }

    terminal_replay_state, terminal_replay = admit_searchos_existing_gap_recovery_cycle(
        state=terminal_state,
        gap_basis=basis,
        recovery_purpose=purpose,
    )
    assert terminal_replay_state == terminal_state
    assert terminal_replay["work_authorized"] is False
    assert terminal_replay["exact_replay"] is True

    before_kernel_replay_state = deepcopy(kernel.state.searchos_state)
    before_sufficiency = deepcopy(
        kernel.state.sufficiency_judgment_projection
    )
    before_ledger = deepcopy(
        kernel.state.evidence_ledger.to_projection().to_dict()
    )
    before_search_calls = len(harness.search_calls)
    before_read_calls = len(harness.read_transport_calls)
    before_read_assessments = len(harness.read_assessment_calls)
    before_model_calls = len(harness.model_calls)
    before_admission = deepcopy(
        kernel.state.projections["multicomponent_component_admission"]
    )
    before_semantic_admission_count = len(
        kernel.state.semantic_observation_admission_history
    )
    before_coverage = deepcopy(kernel.state.component_coverage_history)
    before_sufficiency_count = len(
        kernel.state.sufficiency_judgment_history
    )
    before_fap = deepcopy(kernel.state.final_answer_packet_history)
    before_author_calls = len(harness.author_prompts)
    replay_action = (
        kernel.authorize_searchos_existing_gap_recovery_admission(
            gap_basis=basis,
            recovery_purpose=purpose,
        )
    )
    kernel.reduce(
        Observation.from_action(
            replay_action,
            observation_type=(
                ObservationType.SEARCHOS_EXISTING_GAP_RECOVERY_ADMITTED
            ),
            status=RunStageStatus.COMPLETED,
            payload=replay_action.inputs[
                "recovery_admission_observation"
            ],
        )
    )
    assert kernel.state.searchos_state == before_kernel_replay_state
    assert kernel.state.projections[
        "searchos_existing_gap_recovery_admission"
    ]["work_authorized"] is False
    assert kernel.state.sufficiency_judgment_projection == before_sufficiency
    assert (
        kernel.state.evidence_ledger.to_projection().to_dict()
        == before_ledger
    )
    assert len(harness.search_calls) == before_search_calls
    assert len(harness.read_transport_calls) == before_read_calls
    assert len(harness.read_assessment_calls) == before_read_assessments
    assert len(harness.model_calls) == before_model_calls
    assert (
        kernel.state.projections["multicomponent_component_admission"]
        == before_admission
    )
    assert len(
        kernel.state.semantic_observation_admission_history
    ) == before_semantic_admission_count
    assert kernel.state.component_coverage_history == before_coverage
    assert len(
        kernel.state.sufficiency_judgment_history
    ) == before_sufficiency_count
    assert kernel.state.final_answer_packet_history == before_fap
    assert len(harness.author_prompts) == before_author_calls

    alternate_gap_kind = (
        "same_component_source_obligation_not_covered"
        if basis["gap_kind"] == "same_component_semantic_admission_not_supported"
        else "same_component_semantic_admission_not_supported"
    )
    stale_second_basis = _reenvelope_gap_basis(
        basis,
        gap_kind=alternate_gap_kind,
    )
    stale_second_purpose = build_searchos_materially_novel_recovery_purpose(stale_second_basis)
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="stale against canonical SearchOS state",
    ):
        admit_searchos_existing_gap_recovery_cycle(
            state=admitted_state,
            gap_basis=stale_second_basis,
            recovery_purpose=stale_second_purpose,
        )

    other_slot_id = next(
        slot_id
        for slot_id in pre_state["required_slot_ids"]
        if slot_id != prior_slot_id
    )
    other_gap_basis = build_searchos_existing_gap_basis(
        state=pre_state,
        slot_id=other_slot_id,
        component_admission_projection=(
            captured["component_admission_projection"]
        ),
        component_coverage_history=(
            captured["component_coverage_history"]
        ),
        evidence_ledger_projection=(
            captured["evidence_ledger_projection"]
        ),
    )
    assert (
        other_gap_basis["prior_terminal_slot_ref"][
            "source_obligation_id"
        ]
        != basis["prior_terminal_slot_ref"]["source_obligation_id"]
    )
    limit_plus_one_basis = _reenvelope_gap_basis(
        other_gap_basis,
        searchos_state_ref={
            "state_id": admitted_state["state_id"],
            "state_digest": admitted_state["state_digest"],
        },
    )
    limit_plus_one_purpose = build_searchos_materially_novel_recovery_purpose(limit_plus_one_basis)
    assert (
        limit_plus_one_purpose["recovery_purpose_id"]
        != purpose["recovery_purpose_id"]
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="cycle limit exhausted",
    ):
        admit_searchos_existing_gap_recovery_cycle(
            state=admitted_state,
            gap_basis=limit_plus_one_basis,
            recovery_purpose=limit_plus_one_purpose,
        )

    assert len(terminal_state["existing_gap_recovery_cycles"]) == MAXIMUM_EXISTING_GAP_RECOVERY_CYCLES
    assert terminal_state["active_existing_gap_recovery_cycle_ref"] == {}
    assert (
        terminal_state["existing_gap_recovery_terminal_aggregate"]["further_existing_gap_recovery_authorized"] is False
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="absent or terminal|exact active cycle",
    ):
        validate_active_searchos_recovery_cycle_ref(
            terminal_state,
            terminal_replay["cycle_ref"],
        )
    with pytest.raises(SearchOSExistingGapRecoveryError):
        finalize_searchos_existing_gap_recovery_cycle(
            state=terminal_state,
            cycle_ref=terminal_replay["cycle_ref"],
            component_admission_ref=None,
        )


def test_gap_eligibility_and_novelty_are_exact_and_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    assert "basis" in captured, captured.get("error")
    state = captured["state"]
    slot_id = captured["slot_id"]
    basis = captured["basis"]
    projection = captured["component_admission_projection"]
    ledger = captured["evidence_ledger_projection"]
    purpose = build_searchos_materially_novel_recovery_purpose(basis)

    nonterminal = deepcopy(state)
    nonterminal_slot = deepcopy(nonterminal["slots_by_id"][slot_id])
    nonterminal_slot["posture"] = "active_unjudged"
    nonterminal_slot.pop("slot_state_digest", None)
    nonterminal_slot["slot_state_digest"] = _digest(nonterminal_slot)
    nonterminal["slots_by_id"][slot_id] = nonterminal_slot
    nonterminal = _refresh_state(nonterminal)
    with pytest.raises(ValueError):
        build_searchos_existing_gap_basis(
            state=nonterminal,
            slot_id=slot_id,
            component_admission_projection=projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    optional_basis = _reenvelope_gap_basis(
        basis,
        requirement_posture="optional",
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="broadens recovery authority",
    ):
        validate_searchos_existing_gap_basis(optional_basis)

    ambiguous_coverage = [
        {
            "answer_component_id": basis["prior_terminal_slot_ref"]["component_id"],
            "coverage_state": "unsatisfied",
        }
    ]
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="ambiguous component coverage",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=projection,
            component_coverage_history=ambiguous_coverage,
            evidence_ledger_projection=ledger,
        )

    satisfied_projection = deepcopy(projection)
    satisfied_projection["component_admission_refs"][-1]["admission_status"] = "admitted"
    satisfied_coverage = [
        {
            "coverage_record_id": "coverage:component_1",
            "coverage_record_digest": "a" * 64,
            "answer_component_id": basis["prior_terminal_slot_ref"]["component_id"],
            "coverage_state": "satisfied",
            "evidence_ledger_binding": {"source_requirement_ids": ["requirement:official_current"]},
        }
    ]
    satisfied_ledger = deepcopy(ledger)
    satisfied_ledger.setdefault("source_requirements", []).append(
        {
            "requirement_id": "requirement:official_current",
            "requirement_kind": "official_current",
            "source_obligation_id": basis["prior_terminal_slot_ref"][
                "source_obligation_id"
            ],
            "component_id": basis["prior_terminal_slot_ref"][
                "component_id"
            ],
            "status": "satisfied",
        }
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="cannot reopen a satisfied source obligation",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=satisfied_projection,
            component_coverage_history=satisfied_coverage,
            evidence_ledger_projection=satisfied_ledger,
        )

    missing_role_projection = deepcopy(projection)
    missing_role_projection["component_admission_refs"][-1]["dprime_validation_ref"] = {}
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=missing_role_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    stale_component_projection = deepcopy(projection)
    stale_component_projection["component_admission_refs"][-1][
        "component_revision"
    ] = "stale-revision"
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=stale_component_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    stale_contract_projection = deepcopy(projection)
    stale_contract_projection["component_admission_refs"][-1][
        "accepted_contract_digest"
    ] = "f" * 64
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="role provenance",
    ):
        build_searchos_existing_gap_basis(
            state=state,
            slot_id=slot_id,
            component_admission_projection=stale_contract_projection,
            component_coverage_history=[],
            evidence_ledger_projection=ledger,
        )

    source_identity_purpose = _reenvelope_recovery_purpose(
        purpose,
        physical_source_identity_establishes_novelty=True,
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="non-semantic novelty basis",
    ):
        validate_searchos_recovery_purpose(source_identity_purpose)

    no_delta_purpose = _reenvelope_recovery_purpose(
        purpose,
        intended_evidence_delta={
            "delta_kind": "same_source_rewording",
            "component_id": basis["prior_terminal_slot_ref"]["component_id"],
            "source_obligation_id": basis["prior_terminal_slot_ref"]["source_obligation_id"],
        },
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="materially novel evidence delta",
    ):
        validate_searchos_recovery_purpose(no_delta_purpose)

    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="absent or terminal|exact active cycle",
    ):
        validate_active_searchos_recovery_cycle_ref(state, {})


def test_recovery_model_failure_exhausts_without_author_or_role_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    sufficiency_inputs = _capture_sufficiency_inputs(monkeypatch)
    _forbid_post_terminal_blocked_adapter(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=False,
    )
    prior = PostRetirementOrdinaryPipelineHarness.ask_model

    def fail_recovery_judgment(
        self: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt == SEARCHOS_JUDGMENT_SYSTEM_PROMPT and captured:
            raise AssertionError("offline recovery SearchOS model failure")
        return prior(self, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        fail_recovery_judgment,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )

    kernel = harness.run_kernel
    assert kernel is not None
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    role_system_prompts = [item["system_prompt"] for item in harness.model_calls]
    assert terminal["terminal_status"] == "exhausted_insufficient"
    assert terminal["expenditure"]["failed_logical_judgment_calls"] > 0
    assert terminal["terminal_blocker"]["blocker_class"] == (
        "provider_or_acquisition"
    )
    assert "model" in terminal["terminal_blocker"]["reason_code"]
    assert sufficiency_inputs
    assert (
        sufficiency_inputs[-1]
        .searchos_existing_gap_recovery_terminal_state
        == terminal
    )
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert sufficiency["final_answer_posture"] == "blocked"
    assert sufficiency["final_answer_allowed"] is False
    consumption = sufficiency[
        "searchos_existing_gap_recovery_terminal_consumption"
    ]
    assert consumption["terminal_blocker"] == terminal[
        "terminal_blocker"
    ]
    assert any(
        "provider_or_acquisition" in reason
        for reason in sufficiency["readiness_reasons"]
    )
    assert role_system_prompts.count(ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]) == 1
    assert ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER] not in role_system_prompts
    assert not harness.author_prompts
    assert "could not produce a supported answer" in outcome.report


def test_recovery_records_are_ref_only_and_boundary_b_is_static_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_first_gap_basis(monkeypatch)
    _install_initially_unsupported_component(
        monkeypatch,
        remain_unsupported=True,
    )
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=_official_evidence_rows(),
    )
    kernel = harness.run_kernel
    assert kernel is not None
    purpose = build_searchos_materially_novel_recovery_purpose(captured["basis"])
    terminal = kernel.state.projections["searchos_existing_gap_recovery_terminal"]
    cycle = kernel.state.searchos_state["existing_gap_recovery_cycles"][0]
    serialized = json.dumps(
        {
            "basis": captured["basis"],
            "purpose": purpose,
            "cycle": cycle,
            "terminal": terminal,
        },
        sort_keys=True,
    ).casefold()
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert "raw_provider_payload" not in serialized
    assert "raw_model_response" not in serialized
    assert "system_prompt" not in serialized
    assert '"raw_content_retained": true' not in serialized

    same_component_source = inspect.getsource(
        multicomponent_runtime.execute_searchos_same_component_reassessment_from_scope
    )
    for forbidden in (
        "_begin_scheduler_dynamic_recovery(",
        "ROLE_SCRUTINEER",
        "execute_specialist",
        "component_work_graph",
    ):
        assert forbidden not in same_component_source
    retained_source = inspect.getsource(multicomponent_runtime._begin_scheduler_dynamic_recovery)
    assert "recovery_authorization" in retained_source
    pipeline_source = inspect.getsource(
        pipeline_orchestrator._run_pipeline_inner
    )
    assert (
        "if searchos_slice_a_active:\n"
        "        authorized_spine_action = None\n"
        "        source_class_recovery_execution"
    ) in pipeline_source
    assert (
        "component_gap_recovery_result = None\n"
        "    if not searchos_slice_a_active:\n"
        "        recovery_policy"
    ) in pipeline_source
    assert (
        "if not searchos_slice_a_active\n"
        "        else None"
    ) in pipeline_source
