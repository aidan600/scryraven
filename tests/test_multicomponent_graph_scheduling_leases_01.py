"""PRODUCT-PATH-REGRESSION: RunKernel serial graph scheduling and leases.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded: run_pipeline -> selected ordinary multi-component
runtime -> Sufficiency -> FinalAnswerPacket -> Author or safe blocked RunOutcome.
Runtime consumer: core.ordinary_multicomponent_synthesis_runtime.
Exit condition: retain while the qualifying product path is scheduler-governed.
Forbidden interpretation: offline fixtures do not prove live model quality,
arbitrary-query support, permanent mode budgets, or physical parallelism.
"""

from __future__ import annotations

import inspect
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.multicomponent_graph_scheduling as scheduling
import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.pipeline_orchestrator as orchestrator
from core.component_work_graph_v1 import (
    finalize_component_work_graph_v1,
    reduce_component_work_graph_v1,
    reduce_selective_recomputation_closure,
)
from core.cost_accounting import CostAccumulator
from core.evidence_ledger import EvidenceCandidate
from core.multicomponent_component_admission import component_analyst_input_packet
from core.multicomponent_graph_scheduling import (
    LEASE_CANCELLED,
    LEASE_COMPLETED,
    LEASE_DENIED_EXHAUSTED,
    LEASE_EXECUTION_STARTED,
    LEASE_FAILED,
    LEASE_GRANTED,
    LEASE_STALE,
    MULTICOMPONENT_ROLE_CALL_LIMITS,
    MULTICOMPONENT_SCHEDULER_STAGE,
    MulticomponentGraphSchedulingError,
    derive_multicomponent_compatibility_envelope,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_SCHEMA,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    execute_prepared_multicomponent_transport,
    prepare_multicomponent_transport_call,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from core.run_kernel import (
    ActionType,
    Observation,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.fixtures.component_analyst_evidence_sets import (
    component_analyst_evidence_set_fixture,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_component_work_graph_v1 import (
    _structured_graph,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NORTHSTAR_REPORT,
    NorthstarHarness,
)
from tests.test_multicomponent_selective_recomputation_01 import (
    _closure_fixture,
)
from tests.test_searchos_boundary_b_ordinary_product_01 import (
    BoundaryBOrdinaryHarness,
)


def _run_product(tmp_path: Path, *, dynamic: bool = False, total: int | None = None):
    monkeypatch = pytest.MonkeyPatch()
    scrub_offline_runtime(monkeypatch)

    def forbidden_direct_semantic_producer(*_args, **_kwargs):
        raise AssertionError(
            "qualifying multicomponent run cannot use direct semantic authority"
        )

    monkeypatch.setattr(
        multicomponent_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        forbidden_direct_semantic_producer,
    )
    if total is not None:
        monkeypatch.setattr(
            scheduling,
            "derive_multicomponent_compatibility_envelope",
            lambda: total,
        )
    harness = BoundaryBOrdinaryHarness(tmp_path) if dynamic else NorthstarHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    try:
        outcome = orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-07-11",
                session_id=f"scheduler-{'dynamic' if dynamic else 'ordinary'}-{total}",
                run_id=f"scheduler-{'dynamic' if dynamic else 'ordinary'}-{total}",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )
        return outcome, captured["semantic_run_kernel"], captured, harness
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="module")
def ordinary_product(tmp_path_factory: pytest.TempPathFactory):
    return _run_product(tmp_path_factory.mktemp("scheduler-ordinary"))


@pytest.fixture(scope="module")
def dynamic_product(tmp_path_factory: pytest.TempPathFactory):
    return _run_product(tmp_path_factory.mktemp("scheduler-dynamic"), dynamic=True)


def _contract(kernel: RunKernel, *, component_count: int = 2) -> dict[str, Any]:
    components = [
        {
            "component_id": f"component:{index}",
            "component_revision": 1,
            "component_digest": f"component-digest:{index}",
            "user_facing_label": f"Fact {index}",
            "user_facing_question": f"What is fact {index}?",
            "mandatory_caveats": [],
            "prohibited_upgrades": [],
        }
        for index in range(component_count)
    ]
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": f"contract-digest:{component_count}",
        "parent_question_meaning_record_id": "qmr:scheduler-test",
        "parent_question_meaning_record_digest": "qmr-digest:scheduler-test",
        "accepted_answer_component_count": component_count,
        "accepted_answer_component_refs": components,
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain how these facts relate.",
        },
    }


def _scheduler_kernel() -> tuple[RunKernel, dict[str, dict[str, Any]]]:
    kernel = RunKernel.start(run_id="scheduler-unit-run", request_id="scheduler-unit-request")
    contract = _contract(kernel)
    kernel.state.initial_answer_contract = contract
    kernel.state.initial_answer_contract_projection = {"accepted": True}
    for component in contract["accepted_answer_component_refs"]:
        candidate_id = f"evidence:{component['component_id']}"
        kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
            candidate_id=candidate_id,
            readable_status="readable",
        )
    evidence_sets: dict[str, dict[str, Any]] = {}
    packets: dict[str, dict[str, Any]] = {}
    for component in (
        item
        for item in contract["accepted_answer_component_refs"]
        if "direct" in list(item.get("allowed_support_kinds") or ("direct",))
    ):
        component_id = str(component["component_id"])
        evidence_set = component_analyst_evidence_set_fixture(
            {
                "evidence_status": "available",
                "evidence_ref_id": f"evidence:{component_id}",
                "bounded_text": "A bounded fixture fact.",
                "candidate_custody_ref": {
                    "candidate_id": f"evidence:{component_id}"
                },
            }
        )
        evidence_sets[component_id] = evidence_set
        packets[component_id] = component_analyst_input_packet(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            component_evidence_set=evidence_set,
        )
    kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive="Explain how these facts relate.",
    )
    return kernel, packets


def _initialize_existing_graph_scheduler(
    kernel: RunKernel,
    *,
    requested_synthesis_directive: str,
) -> dict[str, dict[str, Any]]:
    contract = dict(
        kernel.state.current_answer_contract
        or kernel.state.initial_answer_contract
    )
    contract["accepted_answer_component_count"] = len(
        contract.get("accepted_answer_component_refs") or ()
    )
    contract["question_meaning_metadata"] = {
        "explicit_factual_component_list": True,
        "requested_synthesis_directive": requested_synthesis_directive,
    }
    if kernel.state.current_answer_contract:
        kernel.state.current_answer_contract = contract
    else:
        kernel.state.initial_answer_contract = contract
    packets: dict[str, dict[str, Any]] = {}
    evidence_sets: dict[str, dict[str, Any]] = {}
    for component in (
        item
        for item in contract["accepted_answer_component_refs"]
        if "direct" in list(item.get("allowed_support_kinds") or ("direct",))
    ):
        component_id = str(component["component_id"])
        candidate = EvidenceCandidate(
            candidate_id=(
                "scheduler_authority_"
                + component_id.replace(":", "_").replace("-", "_")
            ),
            readable_status="readable",
        )
        candidate_id = candidate.candidate_id
        kernel.state.evidence_ledger.candidates[candidate_id] = candidate
        evidence_set = component_analyst_evidence_set_fixture(
            {
                "evidence_status": "available",
                "evidence_ref_id": candidate_id,
                "bounded_text": "A bounded scheduler authority fixture fact.",
                "candidate_custody_ref": {"candidate_id": candidate_id},
            }
        )
        evidence_sets[component_id] = evidence_set
        packets[component_id] = component_analyst_input_packet(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=contract,
            component_ref=component,
            component_evidence_set=evidence_set,
        )
    kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive=requested_synthesis_directive,
    )
    return packets


def _role_kwargs(*, ask_model=None, strict_one_shot_transport=None, provider="OpenAI", model="gpt-5.4"):
    if strict_one_shot_transport is None:
        if ask_model is None:
            raise ValueError("need transport")
        strict_one_shot_transport = wrap_text_callable_as_strict_one_shot_transport(
            ask_model, canonical_provider=provider, model=model
        )
    return {
        "strict_one_shot_transport": strict_one_shot_transport,
        "clean_json_response": None,
        "provider": provider,
        "model": model,
        "use_reasoning": False,
    }


def _scheduler(kernel: RunKernel) -> dict[str, Any]:
    return kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]


def test_01_ordinary_serial_product_success(ordinary_product) -> None:
    outcome, kernel, captured, harness = ordinary_product
    scheduler = _scheduler(kernel)
    assert outcome.report == NORTHSTAR_REPORT
    assert captured["author_handoff_called"] is True
    assert scheduler["status"] == "completed"
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(semantic_calls) == len(scheduler["lease_history"])
    assert all(lease["status"] == LEASE_COMPLETED for lease in scheduler["lease_history"])
    assert scheduler["active_physical_lease_count"] == 0

def test_02_multiple_ready_items_are_serial_and_deterministic(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    scheduler = _scheduler(kernel)
    first_grant = next(
        item for item in scheduler["transition_history"] if item["transition"] == LEASE_GRANTED
    )
    assert first_grant["ready_work_count"] == 5
    works = [lease["work"] for lease in scheduler["lease_history"]]
    assert [work["role"] for work in works[:5]] == [ROLE_COMPONENT_ANALYST] * 5
    assert works[5]["role"] == ROLE_CROSS_COMPONENT_ANALYST
    assert scheduler["maximum_active_physical_leases"] == 1


def test_03_work_is_derived_only_after_exact_upstream_authority(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    leases = _scheduler(kernel)["lease_history"]
    analyst_work = [
        lease["work"]
        for lease in leases
        if lease["work"]["role"] == ROLE_COMPONENT_ANALYST
    ]
    assert len(analyst_work) == 5
    assert not any(
        lease["work"]["role"] == ROLE_COMPONENT_ANALYST_RESUME
        for lease in leases
    )
    admission_refs = kernel.state.projections["multicomponent_component_admission"]["component_admission_refs"]
    assert all(ref["component_analyst_case_ref"]["role"] == ROLE_COMPONENT_ANALYST for ref in admission_refs)
    assert all("dprime_validation_ref" not in ref for ref in admission_refs)
    assert "scheduler_graph" not in _scheduler(kernel)


def test_04_layered_synthesis_preserves_topological_readiness(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    synthesis = [
        lease["work"]
        for lease in _scheduler(kernel)["lease_history"]
        if lease["work"]["role"] == ROLE_SYNTHESIS_DPRIME
    ]
    assert [work["synthesis_key"] for work in synthesis] == ["E", "S"]
    assert any(ref.get("node_id") for ref in synthesis[1]["prerequisite_refs"])


def test_05_full_product_path_lease_coverage(dynamic_product) -> None:
    outcome, kernel, captured, _harness = dynamic_product
    assert outcome.report
    assert captured["author_handoff_called"] is True
    works = [lease["work"] for lease in _scheduler(kernel)["lease_history"]]
    assert {work["role"] for work in works} == set(MULTICOMPONENT_ROLE_CALL_LIMITS) - {ROLE_COMPONENT_ANALYST_RESUME}
    assert not any(work.get("recovery_authorization_ref") for work in works)
    assert not any(work.get("selective_closure_ref") for work in works)
    assert len(
        kernel.state.searchos_state["recovery_cycle_admission_history"]
    ) == 1
    assert len(
        kernel.state.searchos_state["recovery_cycle_terminal_history"]
    ) == 1
    assert any(
        stage.startswith(
            "multicomponent_role:cross_component_analyst:selective:"
        )
        for stage in kernel.state.projections
    )


def test_06_compatibility_envelope_has_one_shared_cap_owner() -> None:
    kernel, packets = _scheduler_kernel()
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert envelope["role_limits"] == dict(MULTICOMPONENT_ROLE_CALL_LIMITS)
    assert envelope["total_units"] == sum(MULTICOMPONENT_ROLE_CALL_LIMITS.values())
    assert envelope["total_units"] == derive_multicomponent_compatibility_envelope()
    with pytest.raises(TypeError):
        kernel.initialize_multicomponent_graph_scheduler(
            component_analyst_input_packets=packets,
            requested_synthesis_directive="Explain how these facts relate.",
            total_units=1,  # type: ignore[call-arg]
        )


def test_07_dispatch_commitment_spends_immediately_before_transport() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert lease["status"] == LEASE_GRANTED
    assert envelope["reserved_units"] == 1
    assert envelope["spent_units"] == 0
    work = lease["work"]
    kernel.prepare_multicomponent_role_dispatch(
        lease_id=lease["lease_id"],
        role=work["role"],
        input_packet_digest=safe_packet_digest(packets[str(work["component_id"])]),
        logical_evaluation_key=work["logical_evaluation_key"],
    )
    latest = _scheduler(kernel)["lease_history"][-1]
    assert latest["status"] == LEASE_EXECUTION_STARTED
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1


def test_08_atomic_role_admission_and_lease_completion() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=work["role"],
        input_packet=packets[str(work["component_id"])],
        logical_evaluation_key=work["logical_evaluation_key"],
        lease_id=lease["lease_id"],
        **_role_kwargs(
            ask_model=lambda *_args, **_kwargs: json.dumps(
                {
                    "case_posture": "supported",
                    "supporting_evidence_aliases": ["component_evidence_01"],
                    "claim_text": "A bounded claim.",
                    "evidence_analysis": "The bounded evidence directly supports the claim.",
                    "self_audit": "The claim stays within the bounded evidence.",
                }
            )
        ),
    )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_COMPLETED
    role_action = next(
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
    )
    assert kernel.state.projections[role_action.stage]["artifact_digest"] == artifact["artifact_digest"]
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(
            Observation.from_action(
                role_action,
                observation_type=role_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"semantic_role_artifact": artifact},
            )
        )


def test_09_transport_failure_is_spent_and_admits_no_artifact() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    with pytest.raises(MulticomponentRoleRuntimeError, match="model_transport_failure"):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("transport failed"))),
        )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1
    assert kernel.state.projections[
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{work['logical_evaluation_key']}"
    ]["semantic_artifact_admitted"] is False


def test_10_invalid_role_output_is_spent_without_retry() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    calls = {"count": 0}

    def invalid(*_args, **_kwargs):
        calls["count"] += 1
        return "not-json"

    with pytest.raises(Exception):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=invalid),
        )
    assert calls["count"] == 1
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED


def _prepared_component_analyst_worker_result(raw_output: dict[str, Any]):
    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    lease = leases[0]
    packet = packets[str(lease["work"]["component_id"])]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=[safe_packet_digest(packet)]
        + [
            safe_packet_digest(packets[str(item["work"]["component_id"])])
            for item in leases[1:]
        ],
    )
    prepared = prepare_multicomponent_transport_call(
        action=actions[0],
        input_packet=packet,
        strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
            lambda *_args, **_kwargs: json.dumps(raw_output),
            canonical_provider="OpenAI",
            model="gpt-5.4",
        ),
        clean_json_response=None,
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
    )
    return kernel, actions[0], execute_prepared_multicomponent_transport(prepared)


@pytest.mark.parametrize(
    "raw_output",
    [
        {
            "claim_text": "Legacy thin claim.",
            "support_status": "supported",
            "caveats": [],
            "nonclaims": [],
            "blockers": [],
        },
        {
            "case_posture": "supported",
            "claim_text": "Claim.",
            "self_audit": "I checked for overreach.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        },
        {
            "case_posture": "supported",
            "claim_text": "Claim.",
            "evidence_analysis": "The exact bounded evidence supports the claim.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        },
    ],
    ids=("support_status_only", "missing_analysis", "missing_self_audit"),
)
def test_prepared_component_analyst_worker_rejects_thin_or_incomplete_case(
    raw_output: dict[str, Any],
) -> None:
    kernel, action, result = _prepared_component_analyst_worker_result(raw_output)
    assert result.failure_kind == "output_validation_failure"
    assert result.normalized_semantic_output is None
    assert result.role == ROLE_COMPONENT_ANALYST
    projection = kernel.state.projections.get(action.stage) or {}
    assert projection.get("semantic_artifact_admitted") is not True


def test_prepared_component_analyst_worker_accepts_modern_supporting_case() -> None:
    _kernel, _action, result = _prepared_component_analyst_worker_result(
        {
            "case_posture": "supported",
            "supporting_evidence_aliases": ["component_evidence_01"],
            "claim_text": "A bounded claim.",
            "evidence_analysis": "The bounded evidence directly supports the claim.",
            "self_audit": "The claim stays within the bounded evidence.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        }
    )
    assert result.failure_kind is None
    assert result.normalized_semantic_output is not None
    assert result.normalized_semantic_output["case_posture"] == "supported"
    assert result.normalized_semantic_output["support_status"] == "supported"
    assert "_runtime_legacy_fixture_compatibility" not in (
        result.normalized_semantic_output
    )


def test_component_analyst_prompt_requires_minimal_typed_json_and_omission() -> None:
    prompt = ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
    assert "minimal schema" in prompt
    assert "self_audit as a string" in prompt
    assert "arrays of strings" in prompt
    assert "do not return them as null, empty objects" in prompt
    assert "literal already explicit in the bounded evidence" in prompt


def test_scheduler_direct_component_analyst_call_rejects_support_status_only() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="requires a valid case_posture",
    ):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(
                ask_model=lambda *_args, **_kwargs: json.dumps(
                    {
                        "claim_text": "Legacy thin claim.",
                        "support_status": "supported",
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                    }
                )
            ),
        )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_FAILED
    assert kernel.state.projections[
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{work['logical_evaluation_key']}"
    ]["semantic_artifact_admitted"] is False


def test_11_predispatch_cancellation_returns_exactly_once() -> None:
    kernel, _packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    initial_remaining = _scheduler(kernel)["compatibility_envelope"]["remaining_units"]
    kernel.cancel_multicomponent_work_lease(lease_id=lease["lease_id"])
    envelope = _scheduler(kernel)["compatibility_envelope"]
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_CANCELLED
    assert envelope["remaining_units"] == initial_remaining + 1
    assert envelope["returned_units"] == 1
    with pytest.raises(MulticomponentGraphSchedulingError):
        kernel.cancel_multicomponent_work_lease(lease_id=lease["lease_id"])


def test_12_postdispatch_staleness_rejects_result_and_keeps_spend() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]

    def stale_after_dispatch(*_args, **_kwargs):
        changed = dict(kernel.state.initial_answer_contract)
        changed["accepted_contract_digest"] = "changed-after-dispatch"
        kernel.state.initial_answer_contract = changed
        return json.dumps({
            "case_posture": "supported",
            "supporting_evidence_aliases": ["component_evidence_01"],
            "claim_text": "Late claim.",
            "evidence_analysis": "The bounded evidence directly supports the claim.",
            "self_audit": "The claim stays within the bounded evidence.",
        })

    with pytest.raises(Exception, match="stale"):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=work["role"],
            input_packet=packets[str(work["component_id"])],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id=lease["lease_id"],
            **_role_kwargs(ask_model=stale_after_dispatch),
        )
    assert _scheduler(kernel)["lease_history"][-1]["status"] == LEASE_STALE
    assert _scheduler(kernel)["compatibility_envelope"]["spent_units"] == 1


def test_13_wrong_and_caller_authored_bindings_are_rejected() -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    wrongs = (
        {"role": ROLE_COMPONENT_ANALYST_RESUME},
        {"logical_evaluation_key": "forged-key"},
        {"input_packet_digest": "forged-digest"},
        {"output_schema_variant": SELECTIVE_CROSS_COMPONENT_SCHEMA},
    )
    base = {
        "lease_id": lease["lease_id"],
        "role": work["role"],
        "input_packet_digest": safe_packet_digest(packets[str(work["component_id"])]),
        "logical_evaluation_key": work["logical_evaluation_key"],
        "output_schema_variant": None,
    }
    for replacement in wrongs:
        with pytest.raises(RunKernelTransitionError, match="scheduler-selected"):
            kernel.prepare_multicomponent_role_dispatch(**{**base, **replacement})
    with pytest.raises(RunKernelTransitionError, match="exact granted lease"):
        kernel.authorize_multicomponent_role_call(
            role=work["role"],
            input_packet_digest=work["input_packet_digest"],
            logical_evaluation_key=work["logical_evaluation_key"],
            lease_id="caller-forged-lease",
            dispatch_action_id="caller-forged-dispatch",
        )


def test_14_selective_recovery_reproves_only_affected_branches(dynamic_product) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    works = [lease["work"] for lease in _scheduler(kernel)["lease_history"]]
    assert not [work for work in works if work.get("selective_closure_ref")]
    closure = kernel.state.projections[
        "multicomponent_selective_recomputation_closure"
    ]
    assert closure["affected_synthesis_keys"] == ["target_E"]
    assert closure["unaffected_active_synthesis_keys"] == []
    selective_dprime_actions = [
        action
        for action in kernel.state.issued_actions.values()
        if action.inputs.get("role") == ROLE_SYNTHESIS_DPRIME
        and ":selective:" in str(
            action.inputs.get("logical_evaluation_key")
        )
    ]
    assert len(selective_dprime_actions) == 1
    assert str(
        selective_dprime_actions[0].inputs["logical_evaluation_key"]
    ).startswith("target_E:")
    assert any(
        action.inputs.get("role") == ROLE_SCRUTINEER
        and ":selective:" in str(
            action.inputs.get("logical_evaluation_key")
        )
        for action in kernel.state.issued_actions.values()
    )


def test_15_early_exhaustion_returns_safe_blocked_runoutcome(tmp_path: Path) -> None:
    outcome, kernel, captured, harness = _run_product(tmp_path, total=0)
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "blocked_exhausted"
    assert scheduler["lease_history"][0]["status"] == LEASE_DENIED_EXHAUSTED
    assert not [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert captured["author_handoff_called"] is False
    assert outcome.failure_card["blocked_fap"] is True


def test_16_late_exhaustion_preserves_progress_and_blocks_author(tmp_path: Path) -> None:
    outcome, kernel, captured, harness = _run_product(tmp_path, total=8)
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "blocked_exhausted"
    assert scheduler["compatibility_envelope"]["spent_units"] == 8
    assert scheduler["lease_history"][-1]["work"]["role"] == ROLE_SCRUTINEER
    assert scheduler["lease_history"][-1]["status"] == LEASE_DENIED_EXHAUSTED
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(semantic_calls) == 8
    assert captured["author_handoff_called"] is False
    assert outcome.failure_card["blocked_fap"] is True


def test_17_deterministic_transitions_consume_no_semantic_units(ordinary_product) -> None:
    _outcome, kernel, _captured, harness = ordinary_product
    scheduler = _scheduler(kernel)
    role_actions = [
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type
        in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_RESUME_EXECUTE,
            ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
        }
    ]
    assert scheduler["compatibility_envelope"]["spent_units"] == len(role_actions)
    semantic_calls = [
        call for call in harness.model_calls if call.get("system_prompt") in ROLE_SYSTEM_PROMPTS.values()
    ]
    assert len(role_actions) == len(semantic_calls)


def test_18_nonqualifying_path_creates_no_scheduler() -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    kernel = RunKernel.start(run_id="nonqualifying-run", request_id="nonqualifying-request")
    kernel.state.initial_answer_contract = _contract(kernel, component_count=1)
    result = runtime.execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
        kernel,
        {"query": "one component"},
        execute_selected_lane=False,
    )
    assert result.status is runtime.OrdinaryMulticomponentStatus.NOT_QUALIFIED
    assert MULTICOMPONENT_SCHEDULER_STAGE not in kernel.state.projections


def test_19_scheduler_trace_is_sanitized(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    rendered = json.dumps(_scheduler(kernel), sort_keys=True)
    for forbidden in (
        "SECRET_PROMPT",
        "provider_payload_value",
        "api_key_value",
        "private_log_value",
        "database_row_value",
        "cache_row_value",
    ):
        assert forbidden not in rendered
    assert '"component_evidence_set":' not in rendered
    assert '"component_evidence_set_digest"' in rendered
    assert "sanitized_excerpt" not in rendered


def test_20_no_parallelism_and_serial_trace(ordinary_product) -> None:
    _outcome, kernel, _captured, _harness = ordinary_product
    source = Path("core/multicomponent_graph_scheduling.py").read_text(encoding="utf-8")
    for forbidden in ("ThreadPoolExecutor", "multiprocessing", "asyncio", "create_task"):
        assert forbidden not in source
    scheduler = _scheduler(kernel)
    assert scheduler["runtime_parallelism"] is False
    assert scheduler["serial_scheduling"] is True
    assert scheduler["maximum_active_physical_leases"] == 1


def test_21_product_driver_dispatches_only_scheduler_selected_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    original = runtime.execute_prepared_multicomponent_transport
    observed: list[tuple[str, str, str, str]] = []

    def exact_dispatch(prepared):
        kernel = captured_kernel["value"]
        lease = next(
            item
            for item in _scheduler(kernel)["lease_history"]
            if item["lease_id"] == prepared.lease_id
        )
        work = lease["work"]
        assert prepared.lease_id == lease["lease_id"]
        assert prepared.role == work["role"]
        assert prepared.logical_evaluation_key == work["logical_evaluation_key"]
        assert safe_packet_digest(prepared.input_packet) == work[
            "input_packet_digest"
        ]
        assert prepared.output_schema_variant == work.get(
            "output_schema_variant"
        )
        observed.append(
            (
                str(lease["lease_id"]),
                str(work["role"]),
                str(work["component_id"] or work["synthesis_key"] or "whole-case"),
                str(work["logical_evaluation_key"]),
            )
        )
        return original(prepared)

    captured_kernel: dict[str, Any] = {"value": None}
    original_commit = RunKernel.commit_multicomponent_batch_dispatch

    def capture_commit(self: RunKernel, **kwargs):
        captured_kernel["value"] = self
        return original_commit(self, **kwargs)

    monkeypatch.setattr(RunKernel, "commit_multicomponent_batch_dispatch", capture_commit)
    monkeypatch.setattr(runtime, "execute_prepared_multicomponent_transport", exact_dispatch)
    _outcome, kernel, _captured, _harness = _run_product(tmp_path)
    assert len(observed) == len(_scheduler(kernel)["lease_history"])


def test_22_scheduler_order_overrides_legacy_component_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = scheduling.derive_ready_work

    def reverse_scheduler_order(state, *, allow_active_lease=False):
        return list(
            reversed(
                original(state, allow_active_lease=allow_active_lease)
            )
        )

    monkeypatch.setattr(scheduling, "derive_ready_work", reverse_scheduler_order)
    _outcome, kernel, _captured, _harness = _run_product(tmp_path)
    legacy_order = [
        item["component_id"]
        for item in kernel.state.initial_answer_contract[
            "accepted_answer_component_refs"
        ]
    ]
    physical_order = [
        lease["work"]["component_id"]
        for lease in _scheduler(kernel)["lease_history"]
        if lease["work"]["role"] == ROLE_COMPONENT_ANALYST
    ]
    assert physical_order == list(reversed(legacy_order))
    assert physical_order != legacy_order


def test_23_selected_product_path_does_not_consume_legacy_semantic_loops(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy semantic enumeration helper was invoked")

    for name in (
        "execute_multicomponent_role_call",
        "_execute_fresh_resynthesis",
        "_execute_selective_reconstruction",
        "_execute_selective_resynthesis",
    ):
        monkeypatch.setattr(runtime, name, forbidden)
    outcome, kernel, _captured, _harness = _run_product(tmp_path, dynamic=True)
    assert outcome.report
    assert _scheduler(kernel)["status"] == "completed"
    selected_source = inspect.getsource(runtime._execute_selected_lane)
    assert "_drive_run_kernel_selected_semantic_work" in selected_source
    assert "execute_multicomponent_role_call(" not in selected_source


@pytest.mark.parametrize("dispatched", [False, True])
def test_24_completion_rejects_active_lease_without_mutation(
    dispatched: bool,
) -> None:
    kernel, packets = _scheduler_kernel()
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    if dispatched:
        kernel.prepare_multicomponent_role_dispatch(
            lease_id=lease["lease_id"],
            role=work["role"],
            input_packet_digest=safe_packet_digest(
                packets[str(work["component_id"])]
            ),
            logical_evaluation_key=work["logical_evaluation_key"],
        )
    before = deepcopy(_scheduler(kernel))
    expected = LEASE_EXECUTION_STARTED if dispatched else LEASE_GRANTED
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="cannot complete while a semantic lease is active",
    ):
        kernel.complete_multicomponent_graph_scheduler()
    assert _scheduler(kernel) == before
    assert _scheduler(kernel)["lease_history"][-1]["status"] == expected


def test_25_forged_terminal_scheduler_with_active_lease_is_rejected() -> None:
    kernel, _packets = _scheduler_kernel()
    kernel.grant_next_multicomponent_work_lease()
    forged = deepcopy(_scheduler(kernel))
    forged["status"] = "completed"
    forged.pop("scheduler_digest")
    forged = scheduling._refresh_scheduler(forged)
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="terminal scheduler state cannot contain an active semantic lease",
    ):
        scheduling.validate_scheduler_state(forged)


def test_26_real_graph_transition_refunds_affected_granted_lease_once() -> None:
    kernel, graph = _structured_graph()
    _initialize_existing_graph_scheduler(
        kernel,
        requested_synthesis_directive=str(graph["requested_synthesis_directive"]),
    )
    lease = kernel.grant_next_multicomponent_work_lease()
    after_grant = deepcopy(_scheduler(kernel)["compatibility_envelope"])
    next_graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    scheduler = _scheduler(kernel)
    envelope = scheduler["compatibility_envelope"]
    assert next_graph["graph_digest"] != graph["graph_digest"]
    assert kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ] == next_graph
    assert scheduler["lease_history"][-1]["status"] == LEASE_CANCELLED
    assert envelope["remaining_units"] == after_grant["remaining_units"] + 1
    assert envelope["returned_units"] == after_grant["returned_units"] + 1
    ready = kernel.derive_current_multicomponent_ready_work()
    assert ready
    assert ready[0]["graph_ref"]["graph_digest"] == next_graph["graph_digest"]
    assert ready[0]["graph_ref"] != lease["work"]["graph_ref"]


def test_27_real_postdispatch_graph_transition_rejects_late_observation() -> None:
    kernel, graph = _structured_graph()
    _initialize_existing_graph_scheduler(
        kernel,
        requested_synthesis_directive=str(graph["requested_synthesis_directive"]),
    )
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    role_action = kernel.prepare_multicomponent_role_dispatch(
        lease_id=lease["lease_id"],
        role=work["role"],
        input_packet_digest=str(work["input_packet_digest"]),
        logical_evaluation_key=work["logical_evaluation_key"],
    )
    next_graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    scheduler = _scheduler(kernel)
    assert next_graph["graph_digest"] != graph["graph_digest"]
    assert scheduler["lease_history"][-1]["status"] == LEASE_STALE
    assert scheduler["compatibility_envelope"]["spent_units"] == 1
    assert kernel.state.projections[role_action.stage][
        "semantic_artifact_admitted"
    ] is False
    before_late_result = deepcopy(scheduler)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(
            Observation.from_action(
                role_action,
                observation_type=role_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
    assert _scheduler(kernel) == before_late_result
    assert kernel.state.projections[role_action.stage]["settlement"] == LEASE_STALE


def test_28_unrelated_selective_closure_does_not_cancel_current_lease() -> None:
    kernel, graph, closure = _closure_fixture()
    _initialize_existing_graph_scheduler(
        kernel,
        requested_synthesis_directive=str(graph["requested_synthesis_directive"]),
    )
    lease = kernel.grant_next_multicomponent_work_lease()
    before = deepcopy(_scheduler(kernel)["compatibility_envelope"])
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    scheduler = _scheduler(kernel)
    assert canonical_closure["closure_digest"] == closure["closure_digest"]
    assert scheduler["lease_history"][-1]["lease_id"] == lease["lease_id"]
    assert scheduler["lease_history"][-1]["status"] == LEASE_GRANTED
    assert scheduler["compatibility_envelope"] == before
    assert kernel.multicomponent_work_lease_is_current(lease["lease_id"]) is True


def test_29_failed_real_graph_transition_preserves_graph_and_scheduler() -> None:
    kernel, graph = _structured_graph()
    _initialize_existing_graph_scheduler(
        kernel,
        requested_synthesis_directive=str(graph["requested_synthesis_directive"]),
    )
    lease = kernel.grant_next_multicomponent_work_lease()
    work = lease["work"]
    role_action = kernel.prepare_multicomponent_role_dispatch(
        lease_id=lease["lease_id"],
        role=work["role"],
        input_packet_digest=str(work["input_packet_digest"]),
        logical_evaluation_key=work["logical_evaluation_key"],
    )
    before_graph = deepcopy(
        kernel.state.projections["multicomponent_component_work_graph_v1"]
    )
    before_scheduler = deepcopy(_scheduler(kernel))
    with pytest.raises(RunKernelTransitionError):
        reduce_component_work_graph_v1(
            run_kernel=kernel,
            operation="accounting",
            graph_candidate=graph,
        )
    assert kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ] == before_graph
    assert _scheduler(kernel) == before_scheduler
    assert role_action.action_id not in kernel.state.reduced_action_ids
    assert kernel.state.next_observation_sequence == role_action.sequence


def test_30_callers_have_no_authority_change_label_or_digest_api() -> None:
    kernel, _packets = _scheduler_kernel()
    assert not hasattr(kernel, "apply_multicomponent_scheduler_authority_change")
    assert not hasattr(scheduling, "record_scheduler_authority_change")


def test_31_no_scrutiny_graph_reaches_deterministic_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = NorthstarHarness.ask_model

    def flat_synthesis(self, prompt, system_prompt, **kwargs):
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            payload = json.loads(prompt)
            component_ids = [
                item["component_id"] for item in payload["component_nodes"]
            ]
            return json.dumps(
                {
                    "synthesis_proposals": [
                        {
                            "synthesis_key": "flat_summary",
                            "claim_text": (
                                "The admitted Northstar facts jointly describe the "
                                "rebate, deadline, eligibility, and filing routes."
                            ),
                            "relationship_type": "bounded_summary",
                            "component_inputs": component_ids,
                            "synthesis_inputs": [],
                            "caveats": [],
                            "nonclaims": [],
                            "blockers": [],
                        }
                    ]
                }
            )
        return original(self, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(NorthstarHarness, "ask_model", flat_synthesis)
    outcome, kernel, captured, _harness = _run_product(tmp_path)
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    assert outcome.report
    assert captured["author_handoff_called"] is True
    assert graph["scrutineer_required"] is False
    assert graph["graph_status"] in {"ready", "ready_with_caveats"}
    assert _scheduler(kernel)["status"] == "completed"
    assert not [
        lease
        for lease in _scheduler(kernel)["lease_history"]
        if lease["work"]["role"] == ROLE_SCRUTINEER
    ]


def test_32_recovery_and_selective_transitions_record_canonical_bindings(
    dynamic_product,
) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    assert (
        kernel.state.current_answer_contract["accepted_contract_digest"]
        != kernel.state.initial_answer_contract["accepted_contract_digest"]
    )
    assert kernel.state.contract_amendment_application_projection[
        "current_answer_contract_projection"
    ]["accepted_contract_digest"] == kernel.state.current_answer_contract[
        "accepted_contract_digest"
    ]
    closure = kernel.state.projections[
        "multicomponent_selective_recomputation_closure"
    ]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    admission = kernel.state.contract_amendment_admission_projection
    application = kernel.state.contract_amendment_application_projection
    expected_admission_ref = {
        "amendment_record_id": admission["amendment_record_id"],
        "amendment_record_digest": admission["amendment_record_digest"],
        "authorized_action_id": admission["authorized_action_id"],
        "admission_digest": admission["admission_digest"],
    }
    expected_application_ref = {
        "amendment_record_id": application["amendment_record_id"],
        "authorized_action_id": application["authorized_action_id"],
        "application_digest": application["application_digest"],
    }
    assert closure["contract_amendment_admission_ref"] == (
        expected_admission_ref
    )
    assert closure["contract_amendment_application_ref"] == (
        expected_application_ref
    )
    terminal = kernel.state.projections[
        "searchos_recovery_cycle_terminal"
    ]
    admission_history = kernel.state.searchos_state[
        "recovery_cycle_admission_history"
    ]
    assert len(admission_history) == 1
    assert terminal["cycle_admission_ref"] == {
        key: admission_history[0][key]
        for key in (
            "schema_version",
            "cycle_id",
            "cycle_admission_id",
            "cycle_admission_digest",
            "stable_replay_key",
            "recovery_classification",
            "generation_depth",
        )
    }
    assert graph["graph_status"] == "ready"
    assert graph["selective_recomputation_rounds"] == 1
    assert graph["whole_graph_resynthesis_rounds"] == 0
    assert not any(
        item["transition"] == "recovery_scheduler_context_registered"
        for item in _scheduler(kernel)["transition_history"]
    )


def test_33_legacy_recovery_scheduler_authority_is_absent() -> None:
    assert not hasattr(
        RunKernel,
        "register_multicomponent_recovery_scheduler_context",
    )
    assert not hasattr(
        RunKernel,
        "authorize_multicomponent_dynamic_recovery",
    )


def test_34_searchos_recovery_does_not_register_scheduler_work(
    dynamic_product,
) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    scheduler = _scheduler(kernel)
    assert not [
        lease
        for lease in scheduler["lease_history"]
        if lease["work"].get("recovery_authorization_ref")
    ]
    assert not [
        item
        for item in scheduler["transition_history"]
        if "recovery" in str(item.get("transition") or "")
    ]
    assert len(
        kernel.state.searchos_state["recovery_cycle_admission_history"]
    ) == 1


def test_35_recovery_admission_and_terminal_are_immutable_records(
    dynamic_product,
) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    admissions = kernel.state.searchos_state[
        "recovery_cycle_admission_history"
    ]
    terminals = kernel.state.searchos_state[
        "recovery_cycle_terminal_history"
    ]
    assert len(admissions) == len(terminals) == 1
    assert admissions[0]["immutable_admission_record"] is True
    assert terminals[0]["admission_record_rewritten"] is False
    assert terminals[0]["cycle_admission_ref"]["cycle_admission_digest"] == (
        admissions[0]["cycle_admission_digest"]
    )


def test_36_searchos_recovery_preserves_completed_graph_scheduler(
    dynamic_product,
) -> None:
    _outcome, kernel, _captured, _harness = dynamic_product
    scheduler = _scheduler(kernel)
    assert scheduler["status"] == "completed"
    assert scheduler["active_physical_lease_count"] == 0
    assert all(
        lease["status"] == LEASE_COMPLETED
        for lease in scheduler["lease_history"]
    )
    assert kernel.state.searchos_state["active_recovery_cycle_ref"] == {}
