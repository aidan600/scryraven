"""AG-96I3W closed Author execution readiness checkpoint.

This helper proves the current U1/V1-bound packet authority is ready for a
later Author execution phase while keeping execution, prompt construction,
final-answer text, product output, live calls, and model behavior closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_author_gate_runtime import AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_deliberation import safe_json
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.followup_fixture_boundaries import (
    followup_closed_surface_boundary_flags,
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_EXECUTION_READINESS_SCHEMA_VERSION = (
    "followup_author_execution_readiness_ag96i3w_v1"
)
FOLLOWUP_AUTHOR_EXECUTION_READINESS_TRACE_KEY = (
    "followup_author_execution_readiness_runtime"
)
FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE = "followup_author_execution_readiness"
AG96I3W_AUTHOR_EXECUTION_READINESS_MODE = (
    "ag96i3w_author_execution_readiness_execution_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS = (
    "author_execution_ready_execution_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_READINESS_REASON = (
    "ag96i3w_author_execution_readiness_execution_closed"
)

_FALSE_FIELDS = (
    "author_execution_allowed",
    "author_activation_allowed",
    "author_payload_status_changed",
    "prompt_text_included",
    "final_text_included",
    "product_answer_ready",
    "model_called",
    "author_executor_invoked",
    "provider_execution_licensed",
)

_TRUE_FIELDS = (
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "author_execution_readiness_recorded",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)

_FORBIDDEN_KEY_PARTS = (
    "followup_author_execution_readiness_state",
    "readiness_payload",
    "prompt_text",
    "final_answer_text",
    "final_text",
    "ordered_sources",
    "ordered_product_source_output",
    "markdown_source_list",
    "source_list_prose",
    "inline_citation",
    "final_answer_citation",
    "rendered_citation",
    "formatted_citation",
    "author_input_payload",
    "author_prompt",
    "author_prose",
    "prose_instruction",
    "style_instruction",
    "author_output",
    "product_output",
    "analyst_handoff",
    "economist_handoff",
    "raw_prompt",
    "raw_provider",
    "raw_payload",
    "raw_trace",
    "raw_text",
    "snippet",
    "private_payload",
    "provider_payload",
    "model_response",
    "db_row",
    "private_log",
    "secret",
    "api_key",
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionReadinessActionResult:
    record: "FollowupAuthorExecutionReadinessRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionReadinessRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def build_followup_author_execution_readiness_action_inputs(
    *,
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    v1_state = _mapping(followup_author_gate_state)
    v1_projection = _mapping(followup_author_gate_projection)
    u1_state = _mapping(followup_author_input_authority_state)
    u1_projection = _mapping(followup_author_input_authority_projection)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    return {
        "run_id": v1_state.get("run_id"),
        "checkpoint_id": v1_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": v1_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": v1_state.get("sealed_candidate_id"),
        "followup_execution_id": v1_state.get("followup_execution_id"),
        "execution_id": v1_state.get("execution_id"),
        "followup_evidence_intake_id": v1_state.get("followup_evidence_intake_id"),
        "intake_id": v1_state.get("intake_id"),
        "followup_sufficiency_recheck_id": v1_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": v1_state.get("recheck_id"),
        "packet_preparation_readiness_id": v1_state.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": v1_state.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": v1_state.get("final_evidence_selection_id"),
        "citation_eligibility_id": v1_state.get("citation_eligibility_id"),
        "citation_source_handoff_id": v1_state.get("citation_source_handoff_id"),
        "citation_rendering_id": v1_state.get("citation_rendering_id"),
        "packet_id": packet.get("packet_id"),
        "author_execution_readiness_id": (
            "followup-author-execution-readiness:"
            f"{v1_state.get('author_gate_id')}"
        ),
        "author_execution_readiness_mode": (
            AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
        ),
        "status": FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS,
        "v1_author_gate_id": v1_state.get("author_gate_id"),
        "v1_author_gate_digest": followup_projection_digest(v1_state),
        "v1_author_gate_projection_digest": followup_projection_digest(
            v1_projection
        ),
        "u1_authority_id": u1_state.get("author_input_authority_id"),
        "u1_authority_digest": followup_projection_digest(u1_state),
        "u1_authority_projection_digest": followup_projection_digest(
            u1_projection
        ),
        "current_final_answer_packet_digest": followup_projection_digest(packet),
        "final_answer_authority_projection_digest": followup_projection_digest(
            authority
        ),
        "author_input_refs_digest": followup_projection_digest(author_input_refs),
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "rendered_source_entry_digest": author_input_refs.get(
            "rendered_source_entry_digest"
        ),
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_readiness_recorded": True,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def execute_followup_author_execution_readiness_action(
    action: Any,
    *,
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_gate_history: Sequence[Mapping[str, Any]],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    followup_author_input_authority_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorExecutionReadinessActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
        stage=FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_EXECUTION_READINESS_PREPARED
        ),
    )
    record = build_followup_author_execution_readiness_record(
        action_inputs=_mapping(action.inputs),
        followup_author_gate_state=followup_author_gate_state,
        followup_author_gate_projection=followup_author_gate_projection,
        followup_author_gate_history=followup_author_gate_history,
        followup_author_input_authority_state=(
            followup_author_input_authority_state
        ),
        followup_author_input_authority_projection=(
            followup_author_input_authority_projection
        ),
        followup_author_input_authority_history=(
            followup_author_input_authority_history
        ),
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
    )
    observation = Observation.from_action(
        action,
        observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_EXECUTION_READINESS_PREPARED
        ),
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_execution_readiness_state": record.to_dict()},
    )
    return FollowupAuthorExecutionReadinessActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_execution_readiness_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_gate_history: Sequence[Mapping[str, Any]],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    followup_author_input_authority_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorExecutionReadinessRecord:
    action = _mapping(action_inputs)
    v1_state = _mapping(followup_author_gate_state)
    v1_projection = _mapping(followup_author_gate_projection)
    v1_history = [_mapping(item) for item in followup_author_gate_history]
    u1_state = _mapping(followup_author_input_authority_state)
    u1_projection = _mapping(followup_author_input_authority_projection)
    u1_history = [
        _mapping(item) for item in followup_author_input_authority_history
    ]
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)

    _validate_action(action)
    _validate_v1_current(
        action=action,
        v1_state=v1_state,
        v1_projection=v1_projection,
        v1_history=v1_history,
    )
    _validate_u1_current(
        action=action,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        u1_history=u1_history,
        authority=authority,
    )
    _validate_packet_authority(
        action=action,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        packet=packet,
        authority=authority,
    )

    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    v1_digest = followup_projection_digest(v1_state)
    u1_digest = followup_projection_digest(u1_state)
    packet_digest = followup_projection_digest(packet)
    authority_digest = followup_projection_digest(authority)
    author_input_refs_digest = followup_projection_digest(author_input_refs)
    state = {
        "schema_version": FOLLOWUP_AUTHOR_EXECUTION_READINESS_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_EXECUTION_READINESS_TRACE_KEY,
        "record_type": "followup_author_execution_readiness_record",
        "owner": "FollowupAuthorExecutionReadinessRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "status": FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS,
        "author_execution_readiness_id": action.get(
            "author_execution_readiness_id"
        ),
        "author_execution_readiness_mode": (
            AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
        ),
        "author_execution_readiness_stage": (
            FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE
        ),
        "run_id": action.get("run_id"),
        "checkpoint_id": action.get("checkpoint_id"),
        "followup_authorization_consumption_id": action.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": action.get("sealed_candidate_id"),
        "followup_execution_id": action.get("followup_execution_id"),
        "execution_id": action.get("execution_id"),
        "followup_evidence_intake_id": action.get(
            "followup_evidence_intake_id"
        ),
        "intake_id": action.get("intake_id"),
        "followup_sufficiency_recheck_id": action.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": action.get("recheck_id"),
        "packet_preparation_readiness_id": action.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": action.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": action.get("final_evidence_selection_id"),
        "citation_eligibility_id": action.get("citation_eligibility_id"),
        "citation_source_handoff_id": action.get("citation_source_handoff_id"),
        "citation_rendering_id": action.get("citation_rendering_id"),
        "packet_id": packet.get("packet_id"),
        "v1_author_gate_id": v1_state.get("author_gate_id"),
        "v1_author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
        "v1_author_gate_digest": v1_digest,
        "v1_author_gate_projection_digest": followup_projection_digest(
            v1_projection
        ),
        "followup_author_gate_digest": v1_digest,
        "u1_authority_id": u1_state.get("author_input_authority_id"),
        "u1_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "u1_authority_digest": u1_digest,
        "u1_authority_projection_digest": followup_projection_digest(
            u1_projection
        ),
        "followup_author_input_authority_digest": u1_digest,
        "followup_author_input_authority_projection_digest": (
            followup_projection_digest(u1_projection)
        ),
        "current_final_answer_packet_digest": packet_digest,
        "final_answer_packet_digest": packet_digest,
        "final_answer_authority_projection_digest": authority_digest,
        "author_input_refs": safe_json(author_input_refs),
        "author_input_refs_digest": author_input_refs_digest,
        "author_input_refs_authority_id": author_input_refs.get(
            "author_input_authority_id"
        ),
        "author_payload_ref": safe_json(author_payload_ref),
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "rendered_source_entry_digest": author_input_refs.get(
            "rendered_source_entry_digest"
        ),
        "source_identity_digest": author_input_refs.get("source_identity_digest"),
        "packet_readiness_posture": {
            "readiness_status": packet.get("readiness_status"),
            "final_answer_allowed": packet.get("final_answer_allowed"),
            "answer_ready": packet.get("answer_ready"),
            "product_answer_ready": packet.get("product_answer_ready"),
        },
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_readiness_recorded": True,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
        "behavior_boundary_flags": readiness_boundary_flags(),
        "redaction_posture": followup_common_redaction_posture(
            sanitized_fixture_summary_only=False,
            packet_authority_refs_only=True,
            final_text_retained=False,
        ),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorExecutionReadinessRecord(state=safe_json(state))


def build_followup_author_execution_readiness_projection(
    *,
    readiness_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_gate_stage: str,
    followup_author_input_authority_stage: str,
) -> dict[str, Any]:
    state = _mapping(readiness_state)
    return {
        "owner": "RunKernel.FollowupAuthorExecutionReadiness",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": state.get("schema_version"),
        "status": state.get("status"),
        "author_execution_readiness_id": state.get(
            "author_execution_readiness_id"
        ),
        "author_execution_readiness_mode": state.get(
            "author_execution_readiness_mode"
        ),
        "author_execution_readiness_stage": state.get(
            "author_execution_readiness_stage"
        ),
        "run_id": state.get("run_id"),
        "checkpoint_id": state.get("checkpoint_id"),
        "followup_authorization_consumption_id": state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": state.get("sealed_candidate_id"),
        "followup_execution_id": state.get("followup_execution_id"),
        "execution_id": state.get("execution_id"),
        "followup_evidence_intake_id": state.get("followup_evidence_intake_id"),
        "intake_id": state.get("intake_id"),
        "followup_sufficiency_recheck_id": state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": state.get("recheck_id"),
        "packet_id": state.get("packet_id"),
        "v1_author_gate_id": state.get("v1_author_gate_id"),
        "v1_author_gate_mode": state.get("v1_author_gate_mode"),
        "v1_author_gate_digest": state.get("v1_author_gate_digest"),
        "v1_author_gate_projection_digest": state.get(
            "v1_author_gate_projection_digest"
        ),
        "u1_authority_id": state.get("u1_authority_id"),
        "u1_authority_mode": state.get("u1_authority_mode"),
        "u1_authority_digest": state.get("u1_authority_digest"),
        "u1_authority_projection_digest": state.get(
            "u1_authority_projection_digest"
        ),
        "current_final_answer_packet_digest": state.get(
            "current_final_answer_packet_digest"
        ),
        "final_answer_packet_digest": state.get("final_answer_packet_digest"),
        "final_answer_authority_projection_digest": state.get(
            "final_answer_authority_projection_digest"
        ),
        "author_input_refs_digest": state.get("author_input_refs_digest"),
        "author_input_refs_authority_id": state.get(
            "author_input_refs_authority_id"
        ),
        "author_payload_ref_id": state.get("author_payload_ref_id"),
        "author_payload_ref_status": state.get("author_payload_ref_status"),
        "rendered_source_entry_digest": state.get("rendered_source_entry_digest"),
        "source_identity_digest": state.get("source_identity_digest"),
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_readiness_recorded": True,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
        "followup_author_gate_ref": {
            "owner": "RunKernel.FollowupAuthorGate",
            "canonical_state": True,
            "author_gate_id": state.get("v1_author_gate_id"),
            "projection_stage": followup_author_gate_stage,
        },
        "followup_author_input_authority_ref": {
            "owner": "RunKernel.FollowupAuthorInputAuthority",
            "canonical_state": True,
            "author_input_authority_id": state.get("u1_authority_id"),
            "projection_stage": followup_author_input_authority_stage,
        },
    }


def validate_followup_author_execution_readiness_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_readiness_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_readiness_state)
    if not observed:
        raise PermissionError(
            "W observation requires followup_author_execution_readiness_state"
        )
    _validate_action(action)
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "packet_id",
        "author_execution_readiness_id",
        "author_execution_readiness_mode",
        "v1_author_gate_id",
        "v1_author_gate_digest",
        "u1_authority_id",
        "u1_authority_digest",
        "current_final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "author_input_refs_digest",
        "author_payload_ref_id",
        "author_payload_ref_status",
        "rendered_source_entry_digest",
    ):
        if observed.get(field) != action.get(field):
            raise PermissionError(f"W observation {field} does not match action")
    if observed.get("status") != FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS:
        raise PermissionError("W observation status mismatch")
    for field in _TRUE_FIELDS:
        if observed.get(field) is not True:
            raise PermissionError(f"W observation requires {field}=True")
    for field in _FALSE_FIELDS:
        if observed.get(field) is not False:
            raise PermissionError(f"W observation requires {field}=False")
    if observed.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("W observation must not make payload executable")
    _reject_forbidden_payload(observed)


def readiness_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_rebuilt": False,
        "final_answer_packet_updated": False,
        "canonical_final_answer_packet_mutated": False,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_readiness_recorded": True,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def _validate_action(action: Mapping[str, Any]) -> None:
    if action.get("author_execution_readiness_mode") != (
        AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
    ):
        raise PermissionError("W action requires AG-96I3W readiness mode")
    if action.get("status") not in (None, FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS):
        raise PermissionError("W action status mismatch")
    if action.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("W action requires deferred author_payload_ref")
    if action.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("W action must not use executable payload status")
    for field in _TRUE_FIELDS:
        if action.get(field) is not True:
            raise PermissionError(f"W action requires {field}=True")
    for field in _FALSE_FIELDS:
        if action.get(field) is not False:
            raise PermissionError(f"W action requires {field}=False")
    _reject_forbidden_payload(action)


def _validate_v1_current(
    *,
    action: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    v1_projection: Mapping[str, Any],
    v1_history: Sequence[Mapping[str, Any]],
) -> None:
    if v1_state.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("W requires RunKernel V1 Author gate state")
    if v1_state.get("canonical_state") is not True:
        raise PermissionError("W requires canonical V1 Author gate state")
    if v1_state.get("trace_only") is not False or v1_state.get("storage_only") is not False:
        raise PermissionError("W requires active V1 Author gate state")
    if v1_state.get("author_gate_mode") != AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE:
        raise PermissionError("W requires AG-96I3V1 Author gate mode")
    if v1_projection.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("W requires RunKernel V1 Author gate projection")
    if v1_projection.get("canonical_state") is not True:
        raise PermissionError("W requires canonical V1 Author gate projection")
    if not v1_history:
        raise PermissionError("W requires V1 Author gate history")
    if _mapping(v1_history[-1]) != v1_projection:
        raise PermissionError("W requires current V1 Author gate history")
    if v1_projection.get("author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("W V1 projection/state id mismatch")
    for field in (
        "author_gate_consumed",
        "author_input_authority_consumed",
        "packet_authority_consumed",
        "author_execution_deferred",
        "live_validation_not_run",
    ):
        if v1_state.get(field) is not True:
            raise PermissionError(f"W requires V1 {field}=True")
    for field in (
        "author_execution_allowed",
        "author_activation_allowed",
        "prompt_text_included",
        "final_text_included",
        "product_answer_ready",
        "model_called",
        "author_executor_invoked",
    ):
        if v1_state.get(field) is not False:
            raise PermissionError(f"W requires V1 {field}=False")
    if action.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("W V1 Author gate id mismatch")
    if action.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("W V1 Author gate digest mismatch")
    if action.get("v1_author_gate_projection_digest") != (
        followup_projection_digest(v1_projection)
    ):
        raise PermissionError("W V1 Author gate projection digest mismatch")


def _validate_u1_current(
    *,
    action: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    u1_history: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> None:
    if u1_state.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("W requires RunKernel U1 authority state")
    if u1_state.get("canonical_state") is not True:
        raise PermissionError("W requires canonical U1 authority state")
    if u1_state.get("trace_only") is not False or u1_state.get("storage_only") is not False:
        raise PermissionError("W requires active U1 authority state")
    if u1_state.get("author_input_authority_mode") != (
        AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    ):
        raise PermissionError("W requires AG-96I3U1 authority state")
    if u1_projection.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("W requires RunKernel U1 authority projection")
    if u1_projection.get("canonical_state") is not True:
        raise PermissionError("W requires canonical U1 authority projection")
    if not u1_history:
        raise PermissionError("W requires U1 authority history")
    if _mapping(u1_history[-1]) != u1_projection:
        raise PermissionError("W requires current U1 authority history")
    if authority != u1_projection:
        raise PermissionError("W requires current U1 final-answer authority")
    if _mapping(u1_state.get("final_answer_authority_projection")) != u1_projection:
        raise PermissionError("W requires U1 state/projection binding")
    if v1_state.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("W V1/U1 authority id mismatch")
    if v1_state.get("followup_author_input_authority_digest") != (
        followup_projection_digest(u1_state)
    ):
        raise PermissionError("W stale U1 authority digest")
    if v1_state.get("followup_author_input_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("W stale U1 projection digest")
    if v1_state.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("W stale final_answer_authority_projection digest")
    if action.get("u1_authority_id") != u1_state.get("author_input_authority_id"):
        raise PermissionError("W U1 authority id mismatch")
    if action.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("W U1 authority digest mismatch")
    if action.get("u1_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("W U1 authority projection digest mismatch")


def _validate_packet_authority(
    *,
    action: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("W requires RunKernel FinalAnswerPacket")
    if packet.get("canonical_state") is not True:
        raise PermissionError("W requires canonical FinalAnswerPacket")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("W requires blocked FinalAnswerPacket")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("W requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("W requires answer_ready=false")
    if packet.get("product_answer_ready") is not False:
        raise PermissionError("W requires product_answer_ready=false")
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    if author_input_refs.get("status") != FOLLOWUP_AUTHOR_INPUT_REFS_STATUS:
        raise PermissionError("W requires U1 author_input_refs")
    if author_payload_ref.get("status") == "author_input_ready":
        raise PermissionError("W rejects executable author_payload_ref")
    if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("W requires deferred author_payload_ref")
    if author_input_refs != _mapping(u1_state.get("author_input_refs")):
        raise PermissionError("W packet author_input_refs mismatch")
    if author_payload_ref != _mapping(u1_state.get("author_payload_ref")):
        raise PermissionError("W packet author_payload_ref mismatch")
    if author_payload_ref != _mapping(u1_projection.get("author_payload_ref")):
        raise PermissionError("W U1 projection author_payload_ref mismatch")
    if author_input_refs.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("W author_input_refs authority id mismatch")
    if author_input_refs.get("author_payload_ref_id") != (
        author_payload_ref.get("payload_ref_id")
    ):
        raise PermissionError("W author_input_refs payload ref mismatch")
    if author_input_refs.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("W author_input_refs authority digest mismatch")
    if v1_state.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("W stale V1 FinalAnswerPacket digest")
    if v1_state.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("W stale V1 author_input_refs digest")
    if v1_state.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("W V1 author_payload_ref id mismatch")
    if v1_state.get("author_payload_ref_status") != author_payload_ref.get(
        "status"
    ):
        raise PermissionError("W V1 author_payload_ref status mismatch")
    if action.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("W current FinalAnswerPacket digest mismatch")
    if action.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("W final_answer_authority_projection digest mismatch")
    if action.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("W author_input_refs digest mismatch")
    if action.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("W author_payload_ref id mismatch")
    if action.get("rendered_source_entry_digest") != author_input_refs.get(
        "rendered_source_entry_digest"
    ):
        raise PermissionError("W rendered source entry digest mismatch")


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").casefold()
            if token in {
                "prompt_text_included",
                "final_text_included",
                "product_answer_ready",
            }:
                if item is not False:
                    raise PermissionError(f"W {token} must be false")
                continue
            if any(part in token for part in _FORBIDDEN_KEY_PARTS):
                if item in (None, False, [], {}, (), ""):
                    continue
                raise PermissionError(f"W readiness includes closed field {key!r}")
            _reject_forbidden_payload(item)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _reject_forbidden_payload(item)
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in ("api_key", "authorization:", "bearer ", "raw prompt", "sk-"):
            if marker in lowered:
                raise PermissionError("W readiness includes private text marker")


def _mapping(value: Any) -> dict[str, Any]:
    safe = safe_json(value or {})
    return dict(safe) if isinstance(safe, Mapping) else {}


__all__ = [
    "AG96I3W_AUTHOR_EXECUTION_READINESS_MODE",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_REASON",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_TRACE_KEY",
    "FollowupAuthorExecutionReadinessActionResult",
    "FollowupAuthorExecutionReadinessRecord",
    "build_followup_author_execution_readiness_action_inputs",
    "build_followup_author_execution_readiness_projection",
    "build_followup_author_execution_readiness_record",
    "execute_followup_author_execution_readiness_action",
    "readiness_boundary_flags",
    "validate_followup_author_execution_readiness_observation_binding",
]
