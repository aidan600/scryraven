from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

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
)
from core.followup_sufficiency_recheck_runtime import (
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import RunKernel

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


@dataclass(frozen=True, slots=True)
class FollowupFixtureSpineResult:
    kernel: RunKernel
    authorization_result: Any
    execution_result: Any
    intake_result: Any
    recheck_result: Any
    packet_result: Any
    gate_result: Any


def build_followup_fixture_checkpoint(
    *,
    run_id: str,
    checkpoint_id: str = "after-first-pass",
    **overrides: Any,
) -> Any:
    fixture = {
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
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
    fixture.update(overrides)
    return build_followup_deliberation_checkpoint(fixture)


def followup_fixture_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
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
    payload.update(overrides)
    return payload


def run_followup_fixture_spine(
    *,
    run_id: str,
    request_id: str = "request-1",
    candidate_id: str = "auth.candidate.001",
    checkpoint_id: str = "after-first-pass",
    checkpoint: Any | None = None,
    fixture_payload: Mapping[str, Any] | None = None,
    packet_mutator: Callable[[RunKernel], None] | None = None,
) -> FollowupFixtureSpineResult:
    kernel = RunKernel.start(run_id=run_id, request_id=request_id)

    auth_action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": checkpoint_id}
    )
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=checkpoint
        or build_followup_fixture_checkpoint(
            run_id=run_id,
            checkpoint_id=checkpoint_id,
        ),
    )
    kernel.reduce(auth_result.observation)

    exec_action = kernel.authorize_followup_fixture_execution(
        candidate_id=candidate_id,
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    exec_result = execute_followup_fixture_action(
        exec_action,
        authorization_state=kernel.state.followup_authorization_state,
        sealed_candidate_id=candidate_id,
        fixture_result_payload=dict(fixture_payload or followup_fixture_payload()),
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

    if packet_mutator is not None:
        packet_mutator(kernel)

    gate_action = kernel.authorize_followup_author_gate()
    gate_result = execute_followup_author_gate_action(
        gate_action,
        followup_final_answer_packet_state=kernel.state.followup_final_answer_packet_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )
    kernel.reduce(gate_result.observation)

    return FollowupFixtureSpineResult(
        kernel=kernel,
        authorization_result=auth_result,
        execution_result=exec_result,
        intake_result=intake_result,
        recheck_result=recheck_result,
        packet_result=packet_result,
        gate_result=gate_result,
    )


def assert_projection_from_state(
    projection: Mapping[str, Any],
    state: Mapping[str, Any],
    fields: tuple[str, ...],
) -> None:
    assert state["canonical_state"] is True
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    for field in fields:
        assert projection[field] == state[field]


def boundary_flag_sets(kernel: RunKernel) -> tuple[Mapping[str, Any], ...]:
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
