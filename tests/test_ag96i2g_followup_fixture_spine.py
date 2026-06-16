from __future__ import annotations

from typing import Any, Mapping

import pytest

from core.followup_author_gate_runtime import execute_followup_author_gate_action
from core.followup_authorization_runtime import (
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import GapType, build_followup_deliberation_checkpoint
from core.followup_evidence_intake_runtime import execute_followup_evidence_intake_action
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    execute_followup_fixture_action,
)
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
    followup_projection_digest,
)
from core.followup_sufficiency_recheck_runtime import (
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    FINAL_ANSWER_PACKET_STAGE,
    FOLLOWUP_AUTHOR_GATE_STAGE,
    FOLLOWUP_AUTHORIZATION_STAGE,
    FOLLOWUP_EVIDENCE_INTAKE_STAGE,
    FOLLOWUP_EXECUTION_STAGE,
    FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
    RUN_KERNEL_TRACE_KEY,
    SUFFICIENCY_JUDGMENT_STAGE,
    RunKernel,
    RunKernelTransitionError,
)

NO_LIVE_FALSE_FLAGS = (
    "provider_execution_licensed",
    "live_provider_call_executed",
    "provider_job_scheduled",
    "provider_job_dispatched",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "model_called",
)

AUTHOR_CITATION_PRODUCT_FALSE_FLAGS = (
    "author_activation_allowed",
    "author_executor_invoked",
    "author_prompt_changed",
    "author_prose_behavior_changed",
    "citation_rendering_changed",
    "citation_formatter_invoked",
    "citation_behavior_changed",
    "product_answer_behavior_changed",
    "final_answer_behavior_changed",
)


def _budget(**overrides: int) -> dict[str, int]:
    base = {
        "cost_points_remaining": 8,
        "provider_calls_remaining": 3,
        "fetches_remaining": 3,
        "read_units_remaining": 3,
        "followup_rounds_remaining": 2,
        "meso_authorizations_remaining": 3,
        "macro_hops_remaining": 1,
    }
    base.update(overrides)
    return base


def _component(component_id: str) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "central": True,
        "served_minimum": True,
        "minimum_provider_calls": 1,
        "minimum_fetches": 1,
        "minimum_read_units": 1,
    }


def _checkpoint() -> Any:
    return build_followup_deliberation_checkpoint(
        {
            "run_id": "ag96i2g-fixture",
            "checkpoint_id": "after-first-pass",
            "mode": "balanced",
            "components": [_component("component-rule")],
            "budget_ledger": _budget(),
            "gaps": [
                {
                    "gap_id": "gap.official",
                    "gap_type": GapType.OFFICIAL_CURRENT_GAP.value,
                    "component_id": "component-rule",
                    "source_obligation_id": "obligation-official-current",
                    "requirement_ids": ["requirement-official-current"],
                    "severity": "central_required",
                    "evidence_indicators": ["required_obligation_unsatisfied"],
                }
            ],
            "sufficiency_handoff": {
                "satisfied_obligations": [],
                "missing_obligations": ["obligation-official-current"],
                "recommended_final_posture": "answer_with_caveats",
                "mandatory_caveats": ["prior_missing_official_current_caveat"],
                "prohibited_upgrades": ["prior_do_not_upgrade_fixture_gap"],
            },
        }
    )


def _fixture_payload() -> dict[str, Any]:
    return {
        "result_status": "fixture_success",
        "summary": "Sanitized official current fixture candidate observed.",
        "url": "https://agency.example/current-rule",
        "title": "Current Official Rule",
        "domain": "agency.example",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "answer_bearing_extract_available": True,
        "eligible_for_stronger_obligation": True,
    }


def test_balanced_followup_fixture_spine_consumes_author_gate_without_opening_closed_surfaces() -> None:
    kernel = RunKernel.start(run_id="ag96i2g-fixture", request_id="request-1")

    auth_action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=_checkpoint(),
    )
    kernel.reduce(auth_result.observation)

    exec_action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    exec_result = execute_followup_fixture_action(
        exec_action,
        authorization_state=kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=_fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    )
    kernel.reduce(exec_result.observation)

    intake_action = kernel.authorize_followup_evidence_intake()
    intake_result = execute_followup_evidence_intake_action(
        intake_action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(intake_result.observation)

    recheck_action = kernel.authorize_followup_sufficiency_recheck()
    recheck_result = execute_followup_sufficiency_recheck_action(
        recheck_action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(recheck_result.observation)

    packet_action = kernel.authorize_followup_final_answer_packet_prepare()
    packet_result = execute_followup_final_answer_packet_prepare_action(
        packet_action,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    kernel.reduce(packet_result.observation)

    gate_action = kernel.authorize_followup_author_gate()
    gate_result = execute_followup_author_gate_action(
        gate_action,
        followup_final_answer_packet_state=kernel.state.followup_final_answer_packet_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )
    kernel.reduce(gate_result.observation)

    assert [observation.stage for observation in kernel.state.observations] == [
        FOLLOWUP_AUTHORIZATION_STAGE,
        FOLLOWUP_EXECUTION_STAGE,
        FOLLOWUP_EVIDENCE_INTAKE_STAGE,
        FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
        FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
        FOLLOWUP_AUTHOR_GATE_STAGE,
    ]

    _assert_projection_from_state(
        kernel.state.followup_authorization_projection,
        kernel.state.followup_authorization_state,
        ("consumption_id", "checkpoint_id", "run_id", "status"),
    )
    _assert_projection_from_state(
        kernel.state.followup_execution_projection,
        kernel.state.followup_execution_state,
        ("execution_id", "observation_id", "sealed_candidate_id", "result_status"),
    )
    _assert_projection_from_state(
        kernel.state.followup_evidence_intake_projection,
        kernel.state.followup_evidence_intake_state,
        (
            "intake_id",
            "observation_id",
            "sealed_candidate_id",
            "source_obligation_satisfied",
        ),
    )
    _assert_projection_from_state(
        kernel.state.followup_sufficiency_recheck_projection,
        kernel.state.followup_sufficiency_recheck_state,
        ("recheck_id", "observation_id", "fixture_sufficiency_posture"),
    )
    _assert_projection_from_state(
        kernel.state.followup_final_answer_packet_projection,
        kernel.state.followup_final_answer_packet_state,
        ("packet_preparation_id", "observation_id", "packet_id"),
    )
    _assert_projection_from_state(
        kernel.state.followup_author_gate_projection,
        kernel.state.followup_author_gate_state,
        ("author_gate_id", "observation_id", "packet_id"),
    )

    assert kernel.state.followup_authorization_history == [
        kernel.state.followup_authorization_projection
    ]
    assert kernel.state.followup_execution_history == [
        kernel.state.followup_execution_projection
    ]
    assert kernel.state.followup_evidence_intake_history == [
        kernel.state.followup_evidence_intake_projection
    ]
    assert kernel.state.followup_sufficiency_recheck_history == [
        kernel.state.followup_sufficiency_recheck_projection
    ]
    assert kernel.state.followup_final_answer_packet_history == [
        kernel.state.followup_final_answer_packet_projection
    ]
    assert kernel.state.followup_author_gate_history == [
        kernel.state.followup_author_gate_projection
    ]

    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == ledger_projection
    assert kernel.state.projections[SUFFICIENCY_JUDGMENT_STAGE] == (
        kernel.state.sufficiency_judgment_projection
    )
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == (
        kernel.state.final_answer_authority_projection
    )
    assert ledger_projection["owner"] == "RunKernel.EvidenceLedger"
    assert ledger_projection["canonical_state"] is True
    assert ledger_projection["candidate_count"] == 1
    assert kernel.state.final_answer_authority_projection["packet_id"] == (
        kernel.state.final_answer_packet["packet_id"]
    )

    gate_state = kernel.state.followup_author_gate_state
    assert gate_state["packet_authority_consumed"] is True
    assert gate_state["final_answer_packet_digest"] == followup_projection_digest(
        kernel.state.final_answer_packet
    )
    assert gate_state["final_answer_authority_projection_digest"] == (
        followup_projection_digest(kernel.state.final_answer_authority_projection)
    )
    assert gate_result.record.to_dict()["packet_authority_consumed"] is True

    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    with pytest.raises(RunKernelTransitionError, match="author input payload"):
        kernel.authorize_author_execution()

    for flags in _boundary_flag_sets(kernel):
        for flag in NO_LIVE_FALSE_FLAGS:
            if flag in flags:
                assert flags[flag] is False
        for flag in AUTHOR_CITATION_PRODUCT_FALSE_FLAGS:
            if flag in flags:
                assert flags[flag] is False
        if "live_validation_not_run" in flags:
            assert flags["live_validation_not_run"] is True

    assert kernel.state.followup_final_answer_packet_projection[
        "canonical_final_answer_packet_ref"
    ] == {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "packet_id": kernel.state.final_answer_packet["packet_id"],
        "projection_stage": FINAL_ANSWER_PACKET_STAGE,
    }
    assert kernel.state.followup_author_gate_projection[
        "canonical_final_answer_packet_ref"
    ] == {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "packet_id": kernel.state.final_answer_packet["packet_id"],
        "projection_stage": FINAL_ANSWER_PACKET_STAGE,
    }

    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_author_gate_state"]["author_gate_id"] == (
        kernel.state.followup_author_gate_state["author_gate_id"]
    )
    assert trace["followup_author_gate_state"]["packet_authority_consumed"] is True
    assert trace["followup_author_gate_projection"] == (
        kernel.state.followup_author_gate_projection
    )


def _assert_projection_from_state(
    projection: Mapping[str, Any],
    state: Mapping[str, Any],
    fields: tuple[str, ...],
) -> None:
    assert state["canonical_state"] is True
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    for field in fields:
        assert projection[field] == state[field]


def _boundary_flag_sets(kernel: RunKernel) -> tuple[Mapping[str, Any], ...]:
    return (
        kernel.state.followup_authorization_state["behavior_boundary_flags"],
        kernel.state.followup_execution_state["behavior_boundary_flags"],
        kernel.state.followup_evidence_intake_state["behavior_boundary_flags"],
        kernel.state.followup_sufficiency_recheck_state["behavior_boundary_flags"],
        kernel.state.followup_final_answer_packet_state["behavior_boundary_flags"],
        kernel.state.final_answer_packet["behavior_boundary_flags"],
        kernel.state.final_answer_authority_projection,
        kernel.state.followup_author_gate_state["behavior_boundary_flags"],
    )
