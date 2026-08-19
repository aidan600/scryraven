"""COMPONENT-ANALYST-CURRENT-AUTHORITY-INPUT-BINDING-01 focused regressions.

Test class: phase_focus / offline_product_path_proof.
No test in this file performs live, provider, or secrets-backed work.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
from core.evidence_ledger import EvidenceCandidate
from core.multicomponent_component_admission import (
    MulticomponentComponentAdmissionError,
    component_analyst_input_packet,
    stage_multicomponent_component_admission,
)
from core.multicomponent_graph_scheduling import (
    MulticomponentGraphSchedulingError,
    validate_current_component_analyst_input_packets,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    safe_packet_digest,
)
from core.run_kernel import (
    RunKernel,
    RunKernelTransitionError,
)
from tests.helpers.canonical_answer_contract_fixture import (
    apply_nonmaterial_current_contract_fixture,
)
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)
from tests.test_ag_search_executor_handoff_01 import (
    COMPONENT_ID,
    _current_contract_kernel,
)
from tests.test_searchos_slice_a_product_cutover_01 import (
    _establish_official_current_qualification_truth,
)


def _evidence_input(candidate_id: str | None = None) -> dict[str, Any]:
    candidate_id = candidate_id or f"evidence:{COMPONENT_ID}"
    return {
        "evidence_status": "available",
        "evidence_ref_id": candidate_id,
        "bounded_text": "rel_tol defaults to 1e-09 and abs_tol defaults to 0.0.",
        "candidate_custody_ref": {"candidate_id": candidate_id},
    }


def _seed_ledger_candidate(kernel: RunKernel) -> str:
    candidate_id = f"evidence:{COMPONENT_ID}"
    kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
        candidate_id=candidate_id,
        readable_status="readable",
    )
    records = kernel.state.evidence_ledger.to_projection().to_dict().get(
        "candidate_records", ()
    )
    return str(records[0]["candidate_id"])


def _kernel_with_installed_current_authority() -> tuple[RunKernel, dict[str, Any], dict[str, Any]]:
    kernel = _current_contract_kernel()
    initial = deepcopy(kernel.state.initial_answer_contract)
    current = dict(kernel.state.current_answer_contract)
    assert current["accepted_contract_digest"] != initial["accepted_contract_digest"]
    _seed_ledger_candidate(kernel)
    return kernel, initial, current


def _packet_for_contract(
    *,
    kernel: RunKernel,
    accepted_contract: dict[str, Any],
    component_ref: dict[str, Any] | None = None,
    evidence_ref_id: str | None = None,
) -> dict[str, Any]:
    component = component_ref or dict(
        accepted_contract["accepted_answer_component_refs"][0]
    )
    if evidence_ref_id is None:
        records = kernel.state.evidence_ledger.to_projection().to_dict().get(
            "candidate_records", ()
        )
        evidence_ref_id = str(records[0]["candidate_id"]) if records else f"evidence:{COMPONENT_ID}"
    return component_analyst_input_packet(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_contract=accepted_contract,
        component_ref=component,
        evidence_input=_evidence_input(evidence_ref_id),
    )


def _analyst_artifact(
    *,
    run_id: str,
    request_id: str,
    component_id: str,
    input_packet: dict[str, Any],
) -> dict[str, Any]:
    core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": ROLE_COMPONENT_ANALYST,
        "artifact_id": f"{ROLE_COMPONENT_ANALYST}:{component_id}",
        "run_id": run_id,
        "request_id": request_id,
        "input_packet_digest": safe_packet_digest(input_packet),
        "logical_evaluation_key": component_id,
        "logical_evaluations": 1,
        "physical_calls": 1,
        "configured_model_route": {
            "provider": "offline",
            "model": "fixture",
            "role": "SmartModel",
        },
        "authorized_action_ref": {
            "action_id": f"action:{component_id}",
            "stage": "component-analyst",
            "sequence": 1,
            "observation_type": "multicomponent_component_analyst_completed",
        },
        "semantic_output": {
            "case_posture": "supported",
            "support_status": "supported",
            "claim_text": "rel_tol defaults to 1e-09 and abs_tol defaults to 0.0.",
            "evidence_analysis": "The bounded READ custody supports the defaults.",
            "self_audit": "The case stays within the bounded evidence.",
            "caveats": [],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        },
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    return {**core, "artifact_digest": safe_packet_digest(core)}


def test_component_analyst_dispatch_binds_current_not_initial() -> None:
    kernel, initial, current = _kernel_with_installed_current_authority()
    initial_packet = _packet_for_contract(kernel=kernel, accepted_contract=initial)
    current_packet = _packet_for_contract(kernel=kernel, accepted_contract=current)
    assert safe_packet_digest(initial_packet) != safe_packet_digest(current_packet)
    snapshot = multicomponent_runtime._canonical_accepted_contract_snapshot(kernel)
    assert snapshot["accepted_contract_digest"] == current["accepted_contract_digest"]
    assert snapshot["accepted_contract_digest"] != initial["accepted_contract_digest"]
    dispatched = _packet_for_contract(kernel=kernel, accepted_contract=snapshot)
    assert safe_packet_digest(dispatched) == safe_packet_digest(current_packet)


def test_component_analyst_artifact_input_digest_matches_dispatched_packet() -> None:
    kernel, _initial, current = _kernel_with_installed_current_authority()
    dispatched = _packet_for_contract(kernel=kernel, accepted_contract=current)
    artifact = _analyst_artifact(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        component_id=COMPONENT_ID,
        input_packet=dispatched,
    )
    assert artifact["input_packet_digest"] == safe_packet_digest(dispatched)


def test_stable_current_authority_admission_succeeds() -> None:
    kernel, _initial, current = _kernel_with_installed_current_authority()
    component_id = COMPONENT_ID
    current_packet = _packet_for_contract(kernel=kernel, accepted_contract=current)
    artifact = _analyst_artifact(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        component_id=component_id,
        input_packet=current_packet,
    )
    artifact["semantic_output"] = {
        **artifact["semantic_output"],
        "case_posture": "blocked",
        "support_status": "blocked",
        "blockers": ["fixture blocker"],
    }
    artifact["artifact_digest"] = safe_packet_digest(
        {key: value for key, value in artifact.items() if key != "artifact_digest"}
    )
    staged = stage_multicomponent_component_admission(
        action_id="action:stable-current-authority",
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_contract=current,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        semantic_observation_admission_history=[],
        component_coverage_history=[],
        component_id=component_id,
        analyst_artifact=artifact,
        analyst_input_packet=current_packet,
        semantic_observation=None,
        sanitized_content_references=[],
        component_coverage_record=None,
    )
    assert staged["component_admission_ref"]["component_id"] == component_id


def test_stale_initial_packet_rejected_under_current_authority() -> None:
    kernel, initial, current = _kernel_with_installed_current_authority()
    component_id = COMPONENT_ID
    stale_packet = _packet_for_contract(kernel=kernel, accepted_contract=initial)
    stale_artifact = _analyst_artifact(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        component_id=component_id,
        input_packet=stale_packet,
    )
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="component Analyst exact input binding mismatch",
    ):
        stage_multicomponent_component_admission(
            action_id="action:stale-initial",
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=current,
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            semantic_observation_admission_history=[],
            component_coverage_history=[],
            component_id=component_id,
            analyst_artifact=stale_artifact,
            analyst_input_packet=stale_packet,
            semantic_observation=None,
            sanitized_content_references=[],
            component_coverage_record=None,
        )


def test_post_dispatch_authority_advance_rejects_stale_artifact() -> None:
    kernel, _initial, current_b = _kernel_with_installed_current_authority()
    component_id = COMPONENT_ID
    packet_b = _packet_for_contract(kernel=kernel, accepted_contract=current_b)
    artifact_b = _analyst_artifact(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        component_id=component_id,
        input_packet=packet_b,
    )
    apply_nonmaterial_current_contract_fixture(
        kernel,
        fixture_id="authority-binding-c",
    )
    current_c = dict(kernel.state.current_answer_contract)
    assert current_c["accepted_contract_digest"] != current_b["accepted_contract_digest"]
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="component Analyst exact input binding mismatch",
    ):
        stage_multicomponent_component_admission(
            action_id="action:stale-after-advance",
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=current_c,
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            semantic_observation_admission_history=[],
            component_coverage_history=[],
            component_id=component_id,
            analyst_artifact=artifact_b,
            analyst_input_packet=packet_b,
            semantic_observation=None,
            sanitized_content_references=[],
            component_coverage_record=None,
        )


def test_scheduler_rejects_stale_component_analyst_packets() -> None:
    kernel, initial, current = _kernel_with_installed_current_authority()
    stale_packet = _packet_for_contract(kernel=kernel, accepted_contract=initial)
    component_refs = [
        item
        for item in current["accepted_answer_component_refs"]
        if "direct" in list(item.get("allowed_support_kinds") or ("direct",))
    ]
    with pytest.raises(
        MulticomponentGraphSchedulingError,
        match="stale against current authority",
    ):
        validate_current_component_analyst_input_packets(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            accepted_contract=current,
            component_refs=component_refs,
            packets={COMPONENT_ID: stale_packet},
        )


def test_scheduler_initialization_rejects_stale_packets() -> None:
    kernel, initial, current = _kernel_with_installed_current_authority()
    stale_packet = _packet_for_contract(kernel=kernel, accepted_contract=initial)
    with pytest.raises(
        RunKernelTransitionError,
        match="scheduler component packet is not current canonical input|stale against current authority",
    ):
        kernel.initialize_multicomponent_graph_scheduler(
            component_analyst_input_packets={COMPONENT_ID: stale_packet},
            requested_synthesis_directive="single_component_direct_admission",
            allow_single_component_direct_admission=True,
        )


def test_q1_shaped_searchos_component_receiver_admits_without_cross_or_synthesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded N=1 SearchOS component-receiver path with direct admission."""

    scheduler_initializations: list[dict[str, Any]] = []
    original_scheduler_initialize = RunKernel.initialize_multicomponent_graph_scheduler

    def capture_scheduler_initialization(self: RunKernel, **kwargs: Any) -> Any:
        result = original_scheduler_initialize(self, **kwargs)
        scheduler_initializations.append(
            {
                "packets": {
                    str(key): dict(value)
                    for key, value in kwargs["component_analyst_input_packets"].items()
                },
                "ready_work": self.derive_current_multicomponent_ready_work(),
            }
        )
        return result

    monkeypatch.setattr(
        RunKernel,
        "initialize_multicomponent_graph_scheduler",
        capture_scheduler_initialization,
    )
    _establish_official_current_qualification_truth(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response=(
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )

    assert len(scheduler_initializations) == 1
    initialization = scheduler_initializations[0]
    assert len(initialization["packets"]) == 1
    [analyst_packet] = initialization["packets"].values()
    authority = (
        harness.run_kernel.state.current_answer_contract
        or harness.run_kernel.state.initial_answer_contract
    )
    assert analyst_packet["run_binding"]["accepted_contract_digest"] == authority[
        "accepted_contract_digest"
    ]
    ready_work = list(initialization["ready_work"])
    assert ready_work
    assert ready_work[0]["role"] == ROLE_COMPONENT_ANALYST
    assert ready_work[0]["input_packet_digest"] == safe_packet_digest(analyst_packet)
    assert harness.run_kernel.state.projections["multicomponent_component_admission"]
    assert all(
        ROLE_SYSTEM_PROMPTS[role] not in harness.model_system_prompts
        for role in (
            ROLE_COMPONENT_DPRIME,
            ROLE_CROSS_COMPONENT_ANALYST,
            ROLE_SYNTHESIS_DPRIME,
        )
    )
    assert outcome.terminal_status == "completed"


def test_realistic_contract_amendment_current_authority_transition_binds_dispatch() -> None:
    """Installed RunKernel CONTRACT_AMENDMENT_APPLIED ADD_NORMALIZATION path."""

    kernel, initial, current = _kernel_with_installed_current_authority()
    assert kernel.state.contract_amendment_application_projection
    assert current["accepted_contract_digest"] != initial["accepted_contract_digest"]
    snapshot = multicomponent_runtime._canonical_accepted_contract_snapshot(kernel)
    packet = _packet_for_contract(kernel=kernel, accepted_contract=snapshot)
    assert packet["run_binding"]["accepted_contract_digest"] == current[
        "accepted_contract_digest"
    ]


def test_recovery_resume_nonregression_reuses_existing_role_artifact_tests() -> None:
    from tests.test_multicomponent_role_artifact_custody_sequence_closure_01 import (
        test_invalid_role_artifact_reduction_is_atomic_and_blocks_n_plus_one,
        test_semantic_role_observation_defensively_preserves_nested_output,
    )

    test_semantic_role_observation_defensively_preserves_nested_output()
    test_invalid_role_artifact_reduction_is_atomic_and_blocks_n_plus_one()
