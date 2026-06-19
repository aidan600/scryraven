"""AG-96I3Y X-bound Author execution activation checkpoint.

This helper creates a non-executable activation reference from the current
X/W/V1/U1/packet authority chain. It keeps Author execution, prompt
construction, final answer text, product output, live calls, and model behavior
closed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_author_execution_readiness_runtime import (
    AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS,
)
from core.followup_author_gate_runtime import AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_input_materialization_runtime import (
    AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
)
from core.followup_deliberation import safe_json
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.followup_fixture_boundaries import (
    followup_closed_surface_boundary_flags,
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_SCHEMA_VERSION = (
    "followup_author_execution_activation_ag96i3y_v1"
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_TRACE_KEY = (
    "followup_author_execution_activation_runtime"
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE = (
    "followup_author_execution_activation"
)
AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE = (
    "ag96i3y_x_bound_author_execution_activation_execution_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS = (
    "author_execution_activation_ready_execution_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS = (
    "x_bound_author_execution_activation_ready_execution_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REASON = (
    "ag96i3y_x_bound_author_execution_activation_execution_closed"
)

Y_PACKET_MUTATION_FIELDS = frozenset(
    {
        "author_execution_activation_ref",
        "author_execution_activation_ref_created",
        "author_execution_activation_prepared",
        "author_execution_activation_status",
        "author_execution_activation_digest",
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_execution_deferred",
        "prompt_text_included",
        "prompt_text_retained",
        "final_text_included",
        "product_answer_ready",
    }
)
Y_AUTHORITY_PROJECTION_MUTATION_FIELDS = Y_PACKET_MUTATION_FIELDS

_FALSE_FIELDS = (
    "author_input_ready",
    "author_execution_allowed",
    "author_activation_allowed",
    "author_payload_ref_status_changed",
    "prompt_text_retained",
    "prompt_text_included",
    "final_text_included",
    "product_answer_ready",
    "model_called",
    "author_executor_invoked",
    "provider_execution_licensed",
    "author_observation_created",
    "final_answer_outcome_created",
    "analyst_handoff_created",
    "economist_handoff_created",
)
_TRUE_FIELDS = (
    "x_author_input_materialization_consumed",
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "author_execution_activation_prepared",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)

_ACTION_FORBIDDEN_KEYS = {
    "followup_author_execution_activation_state",
    "author_execution_activation_state",
    "activation_state",
    "author_execution_activation_ref",
    "activation_ref",
    "author_input_payload",
    "executable_author_input_payload",
    "final_answer_author_input_payload",
}

_FORBIDDEN_KEY_PARTS = (
    "prompt_text",
    "raw_prompt",
    "author_prompt",
    "final_answer_text",
    "final_text",
    "answer_text",
    "source_snippet",
    "snippet",
    "citation_string",
    "inline_citation",
    "final_answer_citation",
    "rendered_citation",
    "formatted_citation",
    "markdown_source_list",
    "source_list_prose",
    "ordered_sources",
    "ordered_product_source_output",
    "ordered_source_output",
    "final_answer_author_input_payload",
    "author_input_payload",
    "role_consumption_payload",
    "executable_payload",
    "author_output",
    "product_output",
    "raw_provider",
    "raw_payload",
    "raw_trace",
    "raw_text",
    "private_payload",
    "provider_payload",
    "model_response",
    "db_row",
    "private_log",
    "secret",
    "api_key",
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionActivationActionResult:
    record: "FollowupAuthorExecutionActivationRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionActivationRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_execution_activation_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    """Reject caller-supplied state/payload attempts before canonical rebuild."""

    action_inputs = _mapping(inputs)
    for key in action_inputs:
        token = str(key or "").casefold()
        if token in _ACTION_FORBIDDEN_KEYS:
            raise PermissionError(
                "Y activation action cannot accept caller-supplied "
                f"{key!r}"
            )
    _reject_forbidden_payload(action_inputs)


def build_followup_author_execution_activation_action_inputs(
    *,
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_input_materialization_projection: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_execution_readiness_projection: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    x_state = _mapping(followup_author_input_materialization_state)
    x_projection = _mapping(followup_author_input_materialization_projection)
    w_state = _mapping(followup_author_execution_readiness_state)
    w_projection = _mapping(followup_author_execution_readiness_projection)
    v1_state = _mapping(followup_author_gate_state)
    v1_projection = _mapping(followup_author_gate_projection)
    u1_state = _mapping(followup_author_input_authority_state)
    u1_projection = _mapping(followup_author_input_authority_projection)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    x_digest = followup_projection_digest(x_state)
    packet_digest = followup_projection_digest(packet)
    return {
        "run_id": x_state.get("run_id"),
        "checkpoint_id": x_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": x_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": x_state.get("sealed_candidate_id"),
        "followup_execution_id": x_state.get("followup_execution_id"),
        "execution_id": x_state.get("execution_id"),
        "followup_evidence_intake_id": x_state.get("followup_evidence_intake_id"),
        "intake_id": x_state.get("intake_id"),
        "followup_sufficiency_recheck_id": x_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": x_state.get("recheck_id"),
        "packet_preparation_readiness_id": x_state.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": x_state.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": x_state.get("final_evidence_selection_id"),
        "citation_eligibility_id": x_state.get("citation_eligibility_id"),
        "citation_source_handoff_id": x_state.get("citation_source_handoff_id"),
        "citation_rendering_id": x_state.get("citation_rendering_id"),
        "packet_id": packet.get("packet_id"),
        "author_execution_activation_id": (
            "followup-author-execution-activation:"
            f"{x_digest[:16]}:{packet_digest[:16]}"
        ),
        "author_execution_activation_mode": (
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
        ),
        "status": FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS,
        "x_author_input_materialization_id": x_state.get(
            "author_input_materialization_id"
        ),
        "x_author_input_materialization_status": x_state.get("status"),
        "x_author_input_materialization_digest": x_digest,
        "x_author_input_materialization_projection_digest": (
            followup_projection_digest(x_projection)
        ),
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": followup_projection_digest(w_state),
        "w_author_execution_readiness_projection_digest": (
            followup_projection_digest(w_projection)
        ),
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
        "current_final_answer_packet_digest": packet_digest,
        "final_answer_packet_digest": packet_digest,
        "final_answer_authority_projection_digest": followup_projection_digest(
            authority
        ),
        "author_input_refs_digest": followup_projection_digest(author_input_refs),
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "prompt_or_input_digest": x_state.get("prompt_or_input_digest"),
        "prompt_or_input_length": x_state.get("prompt_or_input_length"),
        "authority_block_digest": x_state.get("authority_block_digest"),
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_activation_prepared": True,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_retained": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "analyst_handoff_created": False,
        "economist_handoff_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def execute_followup_author_execution_activation_action(
    action: Any,
    *,
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_input_materialization_projection: Mapping[str, Any],
    followup_author_input_materialization_history: Sequence[Mapping[str, Any]],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_execution_readiness_projection: Mapping[str, Any],
    followup_author_execution_readiness_history: Sequence[Mapping[str, Any]],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_gate_history: Sequence[Mapping[str, Any]],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    followup_author_input_authority_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorExecutionActivationActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
        stage=FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_PREPARED
        ),
    )
    record = build_followup_author_execution_activation_record(
        action_inputs=_mapping(action.inputs),
        followup_author_input_materialization_state=(
            followup_author_input_materialization_state
        ),
        followup_author_input_materialization_projection=(
            followup_author_input_materialization_projection
        ),
        followup_author_input_materialization_history=(
            followup_author_input_materialization_history
        ),
        followup_author_execution_readiness_state=(
            followup_author_execution_readiness_state
        ),
        followup_author_execution_readiness_projection=(
            followup_author_execution_readiness_projection
        ),
        followup_author_execution_readiness_history=(
            followup_author_execution_readiness_history
        ),
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
        observation_type=ObservationType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_PREPARED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_execution_activation_state": record.to_dict()},
    )
    return FollowupAuthorExecutionActivationActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_execution_activation_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_input_materialization_projection: Mapping[str, Any],
    followup_author_input_materialization_history: Sequence[Mapping[str, Any]],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_execution_readiness_projection: Mapping[str, Any],
    followup_author_execution_readiness_history: Sequence[Mapping[str, Any]],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_gate_history: Sequence[Mapping[str, Any]],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    followup_author_input_authority_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorExecutionActivationRecord:
    action = _mapping(action_inputs)
    x_state = _mapping(followup_author_input_materialization_state)
    x_projection = _mapping(followup_author_input_materialization_projection)
    x_history = [
        _mapping(item) for item in followup_author_input_materialization_history
    ]
    w_state = _mapping(followup_author_execution_readiness_state)
    w_projection = _mapping(followup_author_execution_readiness_projection)
    w_history = [
        _mapping(item) for item in followup_author_execution_readiness_history
    ]
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
    _validate_x_current(
        action=action,
        x_state=x_state,
        x_projection=x_projection,
        x_history=x_history,
    )
    _validate_w_current(
        action=action,
        x_state=x_state,
        w_state=w_state,
        w_projection=w_projection,
        w_history=w_history,
    )
    _validate_v1_current(
        action=action,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        v1_projection=v1_projection,
        v1_history=v1_history,
    )
    _validate_u1_current(
        action=action,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        u1_history=u1_history,
        authority=authority,
    )
    _validate_packet_authority(
        action=action,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        packet=packet,
        authority=authority,
    )

    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    x_digest = followup_projection_digest(x_state)
    x_projection_digest = followup_projection_digest(x_projection)
    w_digest = followup_projection_digest(w_state)
    w_projection_digest = followup_projection_digest(w_projection)
    v1_digest = followup_projection_digest(v1_state)
    v1_projection_digest = followup_projection_digest(v1_projection)
    u1_digest = followup_projection_digest(u1_state)
    u1_projection_digest = followup_projection_digest(u1_projection)
    packet_digest = followup_projection_digest(packet)
    authority_digest = followup_projection_digest(authority)
    author_input_refs_digest = followup_projection_digest(author_input_refs)
    payload_ref_digest = followup_projection_digest(author_payload_ref)
    activation_ref_id = (
        "author-execution-activation-ref:"
        f"{x_digest[:16]}:{packet_digest[:16]}"
    )
    activation_ref = {
        "activation_ref_id": activation_ref_id,
        "status": FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
        "x_author_input_materialization_id": x_state.get(
            "author_input_materialization_id"
        ),
        "x_author_input_materialization_digest": x_digest,
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": w_digest,
        "v1_author_gate_id": v1_state.get("author_gate_id"),
        "v1_author_gate_digest": v1_digest,
        "u1_authority_id": u1_state.get("author_input_authority_id"),
        "u1_authority_digest": u1_digest,
        "packet_id": packet.get("packet_id"),
        "current_final_answer_packet_digest": packet_digest,
        "final_answer_authority_projection_digest": authority_digest,
        "author_input_refs_digest": author_input_refs_digest,
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "prompt_or_input_digest": x_state.get("prompt_or_input_digest"),
        "prompt_or_input_length": x_state.get("prompt_or_input_length"),
        "authority_block_digest": x_state.get("authority_block_digest"),
        "activation_consumable_by_future_author_execution": True,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_included": False,
        "prompt_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }
    activation_digest = followup_projection_digest(activation_ref)
    packet_mutation = _activation_mutation(
        activation_ref=activation_ref,
        activation_digest=activation_digest,
    )
    state = {
        "schema_version": FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_TRACE_KEY,
        "record_type": "followup_author_execution_activation_record",
        "owner": "FollowupAuthorExecutionActivationRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "status": FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS,
        "author_execution_activation_id": action.get(
            "author_execution_activation_id"
        ),
        "author_execution_activation_mode": (
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
        ),
        "author_execution_activation_stage": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE
        ),
        "run_id": action.get("run_id"),
        "checkpoint_id": action.get("checkpoint_id"),
        "followup_authorization_consumption_id": action.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": action.get("sealed_candidate_id"),
        "followup_execution_id": action.get("followup_execution_id"),
        "execution_id": action.get("execution_id"),
        "followup_evidence_intake_id": action.get("followup_evidence_intake_id"),
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
        "x_author_input_materialization_id": x_state.get(
            "author_input_materialization_id"
        ),
        "x_author_input_materialization_status": x_state.get("status"),
        "x_author_input_materialization_mode": (
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
        ),
        "x_author_input_materialization_digest": x_digest,
        "x_author_input_materialization_projection_digest": x_projection_digest,
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_status": w_state.get("status"),
        "w_author_execution_readiness_mode": AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
        "w_author_execution_readiness_digest": w_digest,
        "w_author_execution_readiness_projection_digest": w_projection_digest,
        "v1_author_gate_id": v1_state.get("author_gate_id"),
        "v1_author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
        "v1_author_gate_digest": v1_digest,
        "v1_author_gate_projection_digest": v1_projection_digest,
        "u1_authority_id": u1_state.get("author_input_authority_id"),
        "u1_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "u1_authority_digest": u1_digest,
        "u1_authority_projection_digest": u1_projection_digest,
        "current_final_answer_packet_digest": packet_digest,
        "final_answer_packet_digest": packet_digest,
        "final_answer_authority_projection_digest": authority_digest,
        "author_input_refs_digest": author_input_refs_digest,
        "author_payload_ref_digest": payload_ref_digest,
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "prompt_or_input_digest": x_state.get("prompt_or_input_digest"),
        "prompt_or_input_length": x_state.get("prompt_or_input_length"),
        "authority_block_digest": x_state.get("authority_block_digest"),
        "author_execution_activation_ref": safe_json(activation_ref),
        "author_execution_activation_ref_id": activation_ref_id,
        "author_execution_activation_ref_status": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS
        ),
        "author_execution_activation_digest": activation_digest,
        "activation_consumable_by_future_author_execution": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_activation_prepared": True,
        "author_payload_ref_status_changed": False,
        "author_payload_ref_status_changed_to_author_input_ready": False,
        "author_payload_ref_status_changed_from_deferred": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_retained": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "analyst_handoff_created": False,
        "economist_handoff_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
        "packet_mutation": safe_json(packet_mutation),
        "final_answer_authority_projection_mutation": safe_json(packet_mutation),
        "updated_final_answer_packet_digest": followup_projection_digest(
            _updated_with_mutation(packet, packet_mutation)
        ),
        "updated_final_answer_authority_projection_digest": (
            followup_projection_digest(_updated_with_mutation(authority, packet_mutation))
        ),
        "behavior_boundary_flags": activation_boundary_flags(),
        "redaction_posture": followup_common_redaction_posture(
            sanitized_fixture_summary_only=False,
            packet_authority_refs_only=True,
            final_text_retained=False,
        )
        | {
            "prompt_text_retained": False,
            "activation_ref_only": True,
        },
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorExecutionActivationRecord(state=safe_json(state))


def build_followup_author_execution_activation_projection(
    *,
    activation_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_input_materialization_stage: str,
    followup_author_execution_readiness_stage: str,
    followup_author_gate_stage: str,
    followup_author_input_authority_stage: str,
) -> dict[str, Any]:
    state = _mapping(activation_state)
    return {
        "owner": "RunKernel.FollowupAuthorExecutionActivation",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": state.get("schema_version"),
        "status": state.get("status"),
        "author_execution_activation_id": state.get(
            "author_execution_activation_id"
        ),
        "author_execution_activation_mode": state.get(
            "author_execution_activation_mode"
        ),
        "author_execution_activation_stage": state.get(
            "author_execution_activation_stage"
        ),
        "run_id": state.get("run_id"),
        "checkpoint_id": state.get("checkpoint_id"),
        "packet_id": state.get("packet_id"),
        "x_author_input_materialization_id": state.get(
            "x_author_input_materialization_id"
        ),
        "x_author_input_materialization_status": state.get(
            "x_author_input_materialization_status"
        ),
        "x_author_input_materialization_mode": state.get(
            "x_author_input_materialization_mode"
        ),
        "x_author_input_materialization_digest": state.get(
            "x_author_input_materialization_digest"
        ),
        "x_author_input_materialization_projection_digest": state.get(
            "x_author_input_materialization_projection_digest"
        ),
        "w_author_execution_readiness_id": state.get(
            "w_author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": state.get(
            "w_author_execution_readiness_digest"
        ),
        "w_author_execution_readiness_projection_digest": state.get(
            "w_author_execution_readiness_projection_digest"
        ),
        "v1_author_gate_id": state.get("v1_author_gate_id"),
        "v1_author_gate_digest": state.get("v1_author_gate_digest"),
        "v1_author_gate_projection_digest": state.get(
            "v1_author_gate_projection_digest"
        ),
        "u1_authority_id": state.get("u1_authority_id"),
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
        "author_payload_ref_digest": state.get("author_payload_ref_digest"),
        "author_payload_ref_id": state.get("author_payload_ref_id"),
        "author_payload_ref_status": state.get("author_payload_ref_status"),
        "prompt_or_input_digest": state.get("prompt_or_input_digest"),
        "prompt_or_input_length": state.get("prompt_or_input_length"),
        "authority_block_digest": state.get("authority_block_digest"),
        "author_execution_activation_ref": safe_json(
            state.get("author_execution_activation_ref")
        ),
        "author_execution_activation_digest": state.get(
            "author_execution_activation_digest"
        ),
        "activation_consumable_by_future_author_execution": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_activation_prepared": True,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_retained": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_executor_invoked": False,
        "provider_execution_licensed": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "analyst_handoff_created": False,
        "economist_handoff_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
        "followup_author_input_materialization_ref": {
            "owner": "RunKernel.FollowupAuthorInputMaterialization",
            "canonical_state": True,
            "author_input_materialization_id": state.get(
                "x_author_input_materialization_id"
            ),
            "projection_stage": followup_author_input_materialization_stage,
        },
        "followup_author_execution_readiness_ref": {
            "owner": "RunKernel.FollowupAuthorExecutionReadiness",
            "canonical_state": True,
            "author_execution_readiness_id": state.get(
                "w_author_execution_readiness_id"
            ),
            "projection_stage": followup_author_execution_readiness_stage,
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


def validate_followup_author_execution_activation_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_activation_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_activation_state)
    if not observed:
        raise PermissionError(
            "Y observation requires followup_author_execution_activation_state"
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
        "author_execution_activation_id",
        "author_execution_activation_mode",
        "x_author_input_materialization_id",
        "x_author_input_materialization_digest",
        "w_author_execution_readiness_id",
        "w_author_execution_readiness_digest",
        "v1_author_gate_id",
        "v1_author_gate_digest",
        "u1_authority_id",
        "u1_authority_digest",
        "current_final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "author_input_refs_digest",
        "author_payload_ref_id",
        "author_payload_ref_status",
        "prompt_or_input_digest",
        "prompt_or_input_length",
        "authority_block_digest",
    ):
        if observed.get(field) != action.get(field):
            raise PermissionError(f"Y observation {field} does not match action")
    if observed.get("status") != FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS:
        raise PermissionError("Y observation status mismatch")
    for field in _TRUE_FIELDS:
        if observed.get(field) is not True:
            raise PermissionError(f"Y observation requires {field}=True")
    for field in _FALSE_FIELDS:
        if observed.get(field) is not False:
            raise PermissionError(f"Y observation requires {field}=False")
    if observed.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Y observation must not make payload executable")
    _reject_forbidden_payload(observed)


def y_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    packet = _mapping(current_packet)
    record = _mapping(record_state)
    mutation = _mapping(record.get("packet_mutation"))
    _validate_exact_mutation_keys(mutation, Y_PACKET_MUTATION_FIELDS, "packet")
    _validate_packet_pre_mutation(packet, record)
    updated = _updated_with_mutation(packet, mutation)
    _validate_packet_post_mutation(packet, updated, record)
    return safe_json(updated)


def y_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _mapping(current_projection)
    record = _mapping(record_state)
    mutation = _mapping(record.get("final_answer_authority_projection_mutation"))
    _validate_exact_mutation_keys(
        mutation,
        Y_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection",
    )
    _validate_authority_pre_mutation(projection, record)
    updated = _updated_with_mutation(projection, mutation)
    _validate_authority_post_mutation(projection, updated, record)
    return safe_json(updated)


def activation_boundary_flags() -> dict[str, bool]:
    flags = {
        **followup_closed_surface_boundary_flags(),
        "canonical_final_answer_packet_mutated": True,
        "final_answer_packet_updated": True,
        "final_answer_packet_rebuilt": False,
        "final_answer_authority_projection_mutated": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_execution_activation_prepared": True,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_ref_status_changed": False,
        "prompt_text_retained": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }
    flags["author_payload_created"] = False
    return flags


def build_run_kernel_followup_author_execution_activation_state(
    *,
    activation_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **_mapping(activation_record_state),
        "owner": "RunKernel.FollowupAuthorExecutionActivation",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_execution_activation_state(
        activation_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_execution_activation_state(
    *,
    activation_state: Mapping[str, Any],
) -> None:
    state = _mapping(activation_state)
    flags = _mapping(state.get("behavior_boundary_flags"))
    for field in _TRUE_FIELDS:
        if state.get(field) is not True:
            raise PermissionError(
                f"Y Author execution activation requires {field}=True"
            )
    for field in _FALSE_FIELDS:
        if state.get(field) is not False:
            raise PermissionError(
                f"Y Author execution activation requires {field}=False"
            )
    if state.get("status") != FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS:
        raise PermissionError("Y Author execution activation status mismatch")
    if state.get("author_execution_activation_mode") != (
        AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
    ):
        raise PermissionError("Y Author execution activation mode mismatch")
    if state.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError(
            "Y Author execution activation requires deferred payload"
        )
    if state.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError(
            "Y Author execution activation must not make payload executable"
        )
    for field, expected in activation_boundary_flags().items():
        if flags.get(field) is not expected:
            raise PermissionError(
                "Y Author execution activation boundary requires "
                f"{field}={expected}"
            )


def _validate_action(action: Mapping[str, Any]) -> None:
    if action.get("author_execution_activation_mode") != (
        AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
    ):
        raise PermissionError("Y action requires AG-96I3Y activation mode")
    if action.get("status") not in (None, FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS):
        raise PermissionError("Y action status mismatch")
    if action.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Y action must not use executable payload status")
    if action.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y action requires deferred author_payload_ref")
    if action.get("x_author_input_materialization_status") != (
        FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS
    ):
        raise PermissionError("Y action requires X materialization status")
    for field in _TRUE_FIELDS:
        if action.get(field) is not True:
            raise PermissionError(f"Y action requires {field}=True")
    for field in _FALSE_FIELDS:
        if action.get(field) is not False:
            raise PermissionError(f"Y action requires {field}=False")
    _reject_forbidden_payload(action)


def _validate_x_current(
    *,
    action: Mapping[str, Any],
    x_state: Mapping[str, Any],
    x_projection: Mapping[str, Any],
    x_history: Sequence[Mapping[str, Any]],
) -> None:
    if x_state.get("owner") != "RunKernel.FollowupAuthorInputMaterialization":
        raise PermissionError("Y requires RunKernel X materialization state")
    if x_state.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical X materialization state")
    if x_state.get("trace_only") is not False or x_state.get("storage_only") is not False:
        raise PermissionError("Y requires active X materialization state")
    if x_state.get("author_input_materialization_mode") != (
        AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
    ):
        raise PermissionError("Y requires AG-96I3X materialization mode")
    if x_state.get("status") != FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS:
        raise PermissionError("Y requires X materialization status")
    if x_projection.get("owner") != "RunKernel.FollowupAuthorInputMaterialization":
        raise PermissionError("Y requires RunKernel X materialization projection")
    if x_projection.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical X materialization projection")
    if not x_history:
        raise PermissionError("Y requires X materialization history")
    if _mapping(x_history[-1]) != x_projection:
        raise PermissionError("Y requires current X materialization history")
    for field in (
        "w_author_execution_readiness_consumed",
        "v1_author_gate_consumed",
        "u1_authority_consumed",
        "packet_authority_consumed",
        "author_input_materialized",
        "author_execution_deferred",
        "live_validation_not_run",
        "not_for_product_answer_activation",
    ):
        if x_state.get(field) is not True:
            raise PermissionError(f"Y requires X {field}=True")
    for field in (
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_payload_status_changed",
        "prompt_text_retained",
        "prompt_text_included",
        "final_text_included",
        "product_answer_ready",
        "model_called",
        "author_executor_invoked",
        "provider_execution_licensed",
        "author_observation_created",
        "final_answer_outcome_created",
        "analyst_handoff_created",
        "economist_handoff_created",
    ):
        if x_state.get(field) is not False:
            raise PermissionError(f"Y requires X {field}=False")
    if x_state.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Y rejects executable X payload status")
    if x_state.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y requires deferred X payload status")
    if action.get("x_author_input_materialization_id") != x_state.get(
        "author_input_materialization_id"
    ):
        raise PermissionError("Y X materialization id mismatch")
    if action.get("x_author_input_materialization_digest") != (
        followup_projection_digest(x_state)
    ):
        raise PermissionError("Y X materialization digest mismatch")
    if action.get("x_author_input_materialization_projection_digest") != (
        followup_projection_digest(x_projection)
    ):
        raise PermissionError("Y X materialization projection digest mismatch")
    if action.get("prompt_or_input_digest") != x_state.get("prompt_or_input_digest"):
        raise PermissionError("Y X prompt/input digest mismatch")
    if action.get("prompt_or_input_length") != x_state.get("prompt_or_input_length"):
        raise PermissionError("Y X prompt/input length mismatch")
    if action.get("authority_block_digest") != x_state.get("authority_block_digest"):
        raise PermissionError("Y X authority block digest mismatch")


def _validate_w_current(
    *,
    action: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    w_projection: Mapping[str, Any],
    w_history: Sequence[Mapping[str, Any]],
) -> None:
    if w_state.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("Y requires RunKernel W readiness state")
    if w_state.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical W readiness state")
    if w_state.get("trace_only") is not False or w_state.get("storage_only") is not False:
        raise PermissionError("Y requires active W readiness state")
    if w_state.get("author_execution_readiness_mode") != (
        AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
    ):
        raise PermissionError("Y requires AG-96I3W readiness mode")
    if w_state.get("status") != FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS:
        raise PermissionError("Y requires W readiness status")
    if w_projection.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("Y requires RunKernel W readiness projection")
    if w_projection.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical W readiness projection")
    if not w_history:
        raise PermissionError("Y requires W readiness history")
    if _mapping(w_history[-1]) != w_projection:
        raise PermissionError("Y requires current W readiness history")
    if x_state.get("w_author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("Y X/W readiness id mismatch")
    if x_state.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("Y stale X W digest")
    if x_state.get("w_author_execution_readiness_projection_digest") != (
        followup_projection_digest(w_projection)
    ):
        raise PermissionError("Y stale X W projection digest")
    for field in (
        "v1_author_gate_consumed",
        "u1_authority_consumed",
        "packet_authority_consumed",
        "author_execution_readiness_recorded",
        "author_execution_deferred",
        "live_validation_not_run",
        "not_for_product_answer_activation",
    ):
        if w_state.get(field) is not True:
            raise PermissionError(f"Y requires W {field}=True")
    for field in (
        "author_execution_allowed",
        "author_activation_allowed",
        "author_payload_status_changed",
        "prompt_text_included",
        "final_text_included",
        "product_answer_ready",
        "model_called",
        "author_executor_invoked",
        "provider_execution_licensed",
    ):
        if w_state.get(field) is not False:
            raise PermissionError(f"Y requires W {field}=False")
    if w_state.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Y rejects executable W payload status")
    if w_state.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y requires deferred W payload status")
    if action.get("w_author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("Y W readiness id mismatch")
    if action.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("Y W readiness digest mismatch")
    if action.get("w_author_execution_readiness_projection_digest") != (
        followup_projection_digest(w_projection)
    ):
        raise PermissionError("Y W readiness projection digest mismatch")


def _validate_v1_current(
    *,
    action: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    v1_projection: Mapping[str, Any],
    v1_history: Sequence[Mapping[str, Any]],
) -> None:
    if v1_state.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("Y requires RunKernel V1 Author gate state")
    if v1_state.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical V1 Author gate state")
    if v1_state.get("trace_only") is not False or v1_state.get("storage_only") is not False:
        raise PermissionError("Y requires active V1 Author gate state")
    if v1_state.get("author_gate_mode") != AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE:
        raise PermissionError("Y requires AG-96I3V1 Author gate mode")
    if v1_projection.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("Y requires RunKernel V1 Author gate projection")
    if v1_projection.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical V1 Author gate projection")
    if not v1_history:
        raise PermissionError("Y requires V1 Author gate history")
    if _mapping(v1_history[-1]) != v1_projection:
        raise PermissionError("Y requires current V1 Author gate history")
    for binding, label in ((w_state, "W"), (x_state, "X")):
        if binding.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
            raise PermissionError(f"Y {label}/V1 Author gate id mismatch")
        if binding.get("v1_author_gate_digest") != (
            followup_projection_digest(v1_state)
        ):
            raise PermissionError(f"Y stale {label} V1 digest")
        if binding.get("v1_author_gate_projection_digest") != (
            followup_projection_digest(v1_projection)
        ):
            raise PermissionError(f"Y stale {label} V1 projection digest")
    for field in (
        "author_gate_consumed",
        "author_input_authority_consumed",
        "packet_authority_consumed",
        "author_execution_deferred",
        "live_validation_not_run",
    ):
        if v1_state.get(field) is not True:
            raise PermissionError(f"Y requires V1 {field}=True")
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
            raise PermissionError(f"Y requires V1 {field}=False")
    if action.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("Y V1 Author gate id mismatch")
    if action.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("Y V1 Author gate digest mismatch")
    if action.get("v1_author_gate_projection_digest") != (
        followup_projection_digest(v1_projection)
    ):
        raise PermissionError("Y V1 Author gate projection digest mismatch")


def _validate_u1_current(
    *,
    action: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    u1_history: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> None:
    if u1_state.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("Y requires RunKernel U1 authority state")
    if u1_state.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical U1 authority state")
    if u1_state.get("trace_only") is not False or u1_state.get("storage_only") is not False:
        raise PermissionError("Y requires active U1 authority state")
    if u1_state.get("author_input_authority_mode") != (
        AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    ):
        raise PermissionError("Y requires AG-96I3U1 authority mode")
    if u1_projection.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("Y requires RunKernel U1 authority projection")
    if u1_projection.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical U1 authority projection")
    if not u1_history:
        raise PermissionError("Y requires U1 authority history")
    if _mapping(u1_history[-1]) != u1_projection:
        raise PermissionError("Y requires current U1 authority history")
    if authority != u1_projection:
        raise PermissionError("Y requires current U1 final-answer authority")
    if _mapping(u1_state.get("final_answer_authority_projection")) != u1_projection:
        raise PermissionError("Y requires U1 state/projection binding")
    if v1_state.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("Y V1/U1 authority id mismatch")
    for binding, label in ((w_state, "W"), (x_state, "X")):
        if binding.get("u1_authority_id") != u1_state.get(
            "author_input_authority_id"
        ):
            raise PermissionError(f"Y {label}/U1 authority id mismatch")
        if binding.get("u1_authority_digest") != followup_projection_digest(
            u1_state
        ):
            raise PermissionError(f"Y stale {label} U1 digest")
        if binding.get("u1_authority_projection_digest") != (
            followup_projection_digest(u1_projection)
        ):
            raise PermissionError(f"Y stale {label} U1 projection digest")
    if action.get("u1_authority_id") != u1_state.get("author_input_authority_id"):
        raise PermissionError("Y U1 authority id mismatch")
    if action.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("Y U1 authority digest mismatch")
    if action.get("u1_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("Y U1 authority projection digest mismatch")


def _validate_packet_authority(
    *,
    action: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("Y requires RunKernel FinalAnswerPacket")
    if packet.get("canonical_state") is not True:
        raise PermissionError("Y requires canonical FinalAnswerPacket")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("Y requires blocked FinalAnswerPacket")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("Y requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("Y requires answer_ready=false")
    if packet.get("product_answer_ready") is not False:
        raise PermissionError("Y requires product_answer_ready=false")
    for existing in Y_PACKET_MUTATION_FIELDS:
        if existing.startswith("author_execution_activation") and packet.get(
            existing
        ) not in (None, False, [], {}, (), ""):
            raise PermissionError("Y requires no existing packet activation ref")
    for existing in Y_AUTHORITY_PROJECTION_MUTATION_FIELDS:
        if existing.startswith("author_execution_activation") and authority.get(
            existing
        ) not in (None, False, [], {}, (), ""):
            raise PermissionError("Y requires no existing authority activation ref")
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    if author_input_refs.get("status") != FOLLOWUP_AUTHOR_INPUT_REFS_STATUS:
        raise PermissionError("Y requires U1 author_input_refs")
    if author_payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Y rejects executable author_payload_ref")
    if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y requires deferred author_payload_ref")
    if author_input_refs != _mapping(u1_state.get("author_input_refs")):
        raise PermissionError("Y packet author_input_refs mismatch")
    if author_payload_ref != _mapping(u1_state.get("author_payload_ref")):
        raise PermissionError("Y packet author_payload_ref mismatch")
    if author_payload_ref != _mapping(u1_projection.get("author_payload_ref")):
        raise PermissionError("Y U1 projection author_payload_ref mismatch")
    if author_input_refs.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("Y author_input_refs authority id mismatch")
    if author_input_refs.get("author_payload_ref_id") != (
        author_payload_ref.get("payload_ref_id")
    ):
        raise PermissionError("Y author_input_refs payload ref mismatch")
    if author_input_refs.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("Y author_input_refs authority digest mismatch")
    for binding, label in ((v1_state, "V1"), (w_state, "W"), (x_state, "X")):
        if binding.get("current_final_answer_packet_digest") != (
            followup_projection_digest(packet)
        ):
            raise PermissionError(f"Y stale {label} FinalAnswerPacket digest")
        if binding.get("author_input_refs_digest") != (
            followup_projection_digest(author_input_refs)
        ):
            raise PermissionError(f"Y stale {label} author_input_refs digest")
        if binding.get("author_payload_ref_id") != author_payload_ref.get(
            "payload_ref_id"
        ):
            raise PermissionError(f"Y {label} author_payload_ref id mismatch")
        if binding.get("author_payload_ref_status") != author_payload_ref.get(
            "status"
        ):
            raise PermissionError(f"Y {label} author_payload_ref status mismatch")
    if x_state.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("Y stale X final_answer_authority_projection digest")
    if action.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("Y current FinalAnswerPacket digest mismatch")
    if action.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("Y final_answer_authority_projection digest mismatch")
    if action.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("Y author_input_refs digest mismatch")
    if action.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("Y author_payload_ref id mismatch")
    if action.get("author_payload_ref_status") != author_payload_ref.get("status"):
        raise PermissionError("Y author_payload_ref status mismatch")


def _validate_packet_pre_mutation(
    packet: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    if followup_projection_digest(packet) != record.get(
        "current_final_answer_packet_digest"
    ):
        raise PermissionError("Y packet mutation requires current packet digest")
    payload_ref = _mapping(packet.get("author_payload_ref"))
    if payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Y packet mutation rejects executable payload")
    if payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y packet mutation requires deferred payload")


def _validate_packet_post_mutation(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    _validate_changed_keys(before, updated, Y_PACKET_MUTATION_FIELDS, "packet")
    before_payload = _mapping(before.get("author_payload_ref"))
    updated_payload = _mapping(updated.get("author_payload_ref"))
    if updated_payload != before_payload:
        raise PermissionError("Y must not change packet author_payload_ref")
    if updated_payload.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y must keep packet author_payload_ref deferred")
    if updated_payload.get("status") == "author_input_ready":
        raise PermissionError("Y must not make packet payload executable")
    if updated.get("readiness_status") != "blocked":
        raise PermissionError("Y must keep packet blocked")
    if updated.get("final_answer_allowed") is not False:
        raise PermissionError("Y must keep final_answer_allowed=false")
    if updated.get("answer_ready") is not False:
        raise PermissionError("Y must keep answer_ready=false")
    if updated.get("product_answer_ready") is not False:
        raise PermissionError("Y must keep product_answer_ready=false")
    activation_ref = _mapping(updated.get("author_execution_activation_ref"))
    if activation_ref != _mapping(record.get("author_execution_activation_ref")):
        raise PermissionError("Y packet activation ref mismatch")


def _validate_authority_pre_mutation(
    projection: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    if followup_projection_digest(projection) != record.get(
        "final_answer_authority_projection_digest"
    ):
        raise PermissionError(
            "Y authority mutation requires current projection digest"
        )
    payload_ref = _mapping(projection.get("author_payload_ref"))
    if payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Y authority mutation rejects executable payload")
    if payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y authority mutation requires deferred payload")


def _validate_authority_post_mutation(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    _validate_changed_keys(
        before,
        updated,
        Y_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection",
    )
    before_payload = _mapping(before.get("author_payload_ref"))
    updated_payload = _mapping(updated.get("author_payload_ref"))
    if updated_payload != before_payload:
        raise PermissionError("Y must not change authority author_payload_ref")
    if updated_payload.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Y must keep authority author_payload_ref deferred")
    activation_ref = _mapping(updated.get("author_execution_activation_ref"))
    if activation_ref != _mapping(record.get("author_execution_activation_ref")):
        raise PermissionError("Y authority activation ref mismatch")


def _activation_mutation(
    *,
    activation_ref: Mapping[str, Any],
    activation_digest: str,
) -> dict[str, Any]:
    return {
        "author_execution_activation_ref": safe_json(activation_ref),
        "author_execution_activation_ref_created": True,
        "author_execution_activation_prepared": True,
        "author_execution_activation_status": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS
        ),
        "author_execution_activation_digest": activation_digest,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_included": False,
        "prompt_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
    }


def _validate_exact_mutation_keys(
    mutation: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    if set(mutation) != set(allowed):
        raise PermissionError(f"Y {context} mutation keys mismatch")


def _validate_changed_keys(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    changed = {
        key for key in set(before) | set(updated) if before.get(key) != updated.get(key)
    }
    if not changed.issubset(allowed):
        raise PermissionError(f"Y {context} mutation changed unlicensed fields")


def _updated_with_mutation(
    value: Mapping[str, Any],
    mutation: Mapping[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(_mapping(value))
    updated.update(_mapping(mutation))
    return updated


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").casefold()
            if token in set(_FALSE_FIELDS) | {
                "author_payload_ref_status_changed_to_author_input_ready",
                "author_payload_ref_status_changed_from_deferred",
            }:
                if item is not False:
                    raise PermissionError(f"Y {token} must be false")
                continue
            if token in set(_TRUE_FIELDS) | {
                "activation_consumable_by_future_author_execution",
                "not_role_consumption_payload",
            }:
                if item is not True:
                    raise PermissionError(f"Y {token} must be true")
                continue
            if token == "status" and item == "author_input_ready":
                raise PermissionError("Y activation must not be executable")
            if token == "author_payload_ref_status" and item == "author_input_ready":
                raise PermissionError("Y activation must not be executable")
            if any(part in token for part in _FORBIDDEN_KEY_PARTS):
                if item in (None, False, [], {}, (), ""):
                    continue
                raise PermissionError(f"Y activation includes closed field {key!r}")
            _reject_forbidden_payload(item)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _reject_forbidden_payload(item)
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in (
            "api_key",
            "authorization:",
            "bearer ",
            "raw prompt",
            "final answer text",
            "sk-",
        ):
            if marker in lowered:
                raise PermissionError("Y activation includes private text marker")
        if lowered == "author_input_ready":
            raise PermissionError("Y activation must not be executable")


def _mapping(value: Any) -> dict[str, Any]:
    safe = safe_json(value or {})
    return dict(safe) if isinstance(safe, Mapping) else {}


__all__ = [
    "AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REASON",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_TRACE_KEY",
    "FollowupAuthorExecutionActivationActionResult",
    "FollowupAuthorExecutionActivationRecord",
    "Y_AUTHORITY_PROJECTION_MUTATION_FIELDS",
    "Y_PACKET_MUTATION_FIELDS",
    "activation_boundary_flags",
    "build_run_kernel_followup_author_execution_activation_state",
    "build_followup_author_execution_activation_action_inputs",
    "build_followup_author_execution_activation_projection",
    "build_followup_author_execution_activation_record",
    "execute_followup_author_execution_activation_action",
    "reject_followup_author_execution_activation_input_spoof",
    "validate_followup_author_execution_activation_observation_binding",
    "y_authority_projection_from_record",
    "y_packet_projection_from_record",
]
