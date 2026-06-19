"""AG-96I3AC Z-consuming Author payload authority.

This module turns the canonical AG-96I3Z prompt assembly manifest into the
non-executable payload authority that a later Author execution phase must
consume. It keeps refs, digests, lengths, and closed-surface flags only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_author_execution_activation_runtime import (
    AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
)
from core.followup_author_execution_readiness_runtime import (
    AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
)
from core.followup_author_gate_runtime import AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_input_materialization_runtime import (
    AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
)
from core.followup_author_prompt_assembly_manifest_runtime import (
    AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
    validate_run_kernel_followup_author_prompt_assembly_manifest_state,
)
from core.followup_deliberation import safe_json
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.followup_fixture_boundaries import (
    followup_closed_surface_boundary_flags,
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_SCHEMA_VERSION = (
    "followup_author_payload_authority_ag96i3ac_v1"
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_TRACE_KEY = (
    "followup_author_payload_authority_runtime"
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE = "followup_author_payload_authority"
AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE = (
    "ag96i3ac_z_consuming_author_payload_authority_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS = (
    "author_payload_authority_ready_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS = (
    "z_bound_author_payload_authority_ready_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REASON = (
    "ag96i3ac_z_consuming_author_payload_authority_execution_closed"
)

AC_PACKET_MUTATION_FIELDS = frozenset(
    {
        "ag96i3_author_payload_authority_ref",
        "ag96i3_author_payload_authority_ref_created",
        "ag96i3_author_payload_authority_prepared",
        "ag96i3_author_payload_authority_status",
        "ag96i3_author_payload_authority_digest",
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_execution_deferred",
        "final_answer_author_input_payload_created",
        "prompt_text_retained",
        "authority_block_text_retained",
        "final_text_included",
        "product_answer_ready",
    }
)
AC_AUTHORITY_PROJECTION_MUTATION_FIELDS = AC_PACKET_MUTATION_FIELDS

_FALSE_FIELDS = (
    "author_input_ready",
    "author_execution_allowed",
    "author_activation_allowed",
    "final_answer_author_input_payload_created",
    "prompt_text_retained",
    "authority_block_text_retained",
    "final_text_included",
    "product_answer_ready",
    "model_called",
)
_TRUE_FIELDS = (
    "z_author_prompt_assembly_manifest_consumed",
    "y_author_execution_activation_consumed",
    "x_author_input_materialization_consumed",
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "payload_authority_created",
    "future_author_execution_must_consume",
    "legacy_author_payload_ref_subordinated",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)
_ACTION_FORBIDDEN_KEYS = {
    "followup_author_payload_authority_state",
    "author_payload_authority_state",
    "payload_authority_state",
    "ag96i3_author_payload_authority_ref",
    "author_payload_authority_ref",
    "final_answer_author_input_payload",
    "author_input_payload",
    "executable_author_input_payload",
    "prompt_text",
    "authority_block_text",
}
_CALLER_CONTROLLED_KEYS = (
    set(_ACTION_FORBIDDEN_KEYS)
    | set(_TRUE_FIELDS)
    | set(_FALSE_FIELDS)
    | set(AC_PACKET_MUTATION_FIELDS)
)
_CLOSED_KEY_PARTS = (
    "raw_prompt",
    "prompt_text",
    "prompt_body",
    "prompt_value",
    "prompt_content",
    "authority_block_text",
    "authority_block_text_value",
    "authority_block_text_body",
    "final_answer_text",
    "answer_text",
    "source_snippet",
    "citation_string",
    "inline_citation",
    "final_answer_citation",
    "ordered_sources",
    "ordered_product_source_output",
    "final_answer_author_input_payload",
    "author_input_payload",
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
_CLOSED_STRING_PARTS = (
    "write the final markdown report",
    "z_prompt_manifest",
    "z_authority_block_manifest",
    "ordered_sources",
    "product_output",
    "model_response",
    "raw_provider",
)
_PROJECTED_FIELDS = (
    "schema_version",
    "status",
    "payload_authority_id",
    "payload_authority_mode",
    "payload_authority_stage",
    "run_id",
    "checkpoint_id",
    "packet_id",
    "z_author_prompt_assembly_manifest_id",
    "z_author_prompt_assembly_manifest_status",
    "z_author_prompt_assembly_manifest_mode",
    "z_author_prompt_assembly_manifest_digest",
    "z_author_prompt_assembly_manifest_projection_digest",
    "z_author_prompt_assembly_manifest_ref_digest",
    "y_author_execution_activation_id",
    "y_author_execution_activation_digest",
    "y_author_execution_activation_ref_digest",
    "y_author_execution_activation_ref_status",
    "y_old_ready_status_demoted",
    "y_author_input_ready",
    "activation_consumable_by_future_author_execution",
    "x_author_input_materialization_id",
    "x_author_input_materialization_digest",
    "x_bill_of_materials",
    "w_author_execution_readiness_id",
    "w_author_execution_readiness_digest",
    "v1_author_gate_id",
    "v1_author_gate_digest",
    "u1_authority_id",
    "u1_authority_digest",
    "current_final_answer_packet_digest",
    "final_answer_packet_digest",
    "final_answer_authority_projection_digest",
    "author_input_refs_digest",
    "author_payload_ref_id",
    "author_payload_ref_status",
    "author_payload_ref_digest",
    "ag96i3_author_payload_authority_ref",
    "ag96i3_author_payload_authority_digest",
    "payload_authority_ref_id",
    "payload_authority_ref_status",
    "prompt_text_digest",
    "prompt_text_length",
    "authority_block_text_digest",
    "authority_block_text_length",
    "prompt_section_ids",
    "prompt_section_digests",
    *_TRUE_FIELDS,
    *_FALSE_FIELDS,
    "behavior_boundary_flags",
    "redaction_posture",
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorPayloadAuthorityActionResult:
    record: "FollowupAuthorPayloadAuthorityRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorPayloadAuthorityRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_payload_authority_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    action_inputs = _mapping(inputs)
    for key in action_inputs:
        token = str(key or "").casefold()
        if token in _CALLER_CONTROLLED_KEYS:
            raise PermissionError(
                "AC payload authority action cannot accept caller-supplied "
                f"{key!r}"
            )
    _reject_forbidden_payload(action_inputs)


def build_followup_author_payload_authority_action_inputs(
    *,
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    z_state = _mapping(followup_author_prompt_assembly_manifest_state)
    z_projection = _mapping(followup_author_prompt_assembly_manifest_projection)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    payload_ref = _mapping(packet.get("author_payload_ref"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    manifest_ref = _mapping(z_state.get("author_prompt_assembly_manifest_ref"))
    return {
        "run_id": z_state.get("run_id"),
        "checkpoint_id": z_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": z_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": z_state.get("sealed_candidate_id"),
        "followup_execution_id": z_state.get("followup_execution_id"),
        "execution_id": z_state.get("execution_id"),
        "followup_evidence_intake_id": z_state.get("followup_evidence_intake_id"),
        "intake_id": z_state.get("intake_id"),
        "followup_sufficiency_recheck_id": z_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": z_state.get("recheck_id"),
        "packet_id": packet.get("packet_id"),
        "payload_authority_id": _payload_authority_id(z_state),
        "payload_authority_mode": (
            AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE
        ),
        "status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
        "z_author_prompt_assembly_manifest_id": z_state.get(
            "author_prompt_assembly_manifest_id"
        ),
        "z_author_prompt_assembly_manifest_status": z_state.get("status"),
        "z_author_prompt_assembly_manifest_mode": z_state.get(
            "author_prompt_assembly_manifest_mode"
        ),
        "z_author_prompt_assembly_manifest_digest": _digest(z_state),
        "z_author_prompt_assembly_manifest_projection_digest": _digest(
            z_projection
        ),
        "z_author_prompt_assembly_manifest_ref_digest": _digest(manifest_ref),
        "y_author_execution_activation_id": z_state.get(
            "y_author_execution_activation_id"
        ),
        "y_author_execution_activation_digest": z_state.get(
            "y_author_execution_activation_digest"
        ),
        "y_author_execution_activation_ref_digest": z_state.get(
            "y_author_execution_activation_ref_digest"
        ),
        "x_author_input_materialization_id": z_state.get(
            "x_author_input_materialization_id"
        ),
        "x_author_input_materialization_digest": z_state.get(
            "x_author_input_materialization_digest"
        ),
        "w_author_execution_readiness_id": z_state.get(
            "w_author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": z_state.get(
            "w_author_execution_readiness_digest"
        ),
        "v1_author_gate_id": z_state.get("v1_author_gate_id"),
        "v1_author_gate_digest": z_state.get("v1_author_gate_digest"),
        "u1_authority_id": z_state.get("u1_authority_id"),
        "u1_authority_digest": z_state.get("u1_authority_digest"),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(author_input_refs),
        "author_payload_ref_id": payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": payload_ref.get("status"),
        "prompt_text_digest": z_state.get("prompt_text_digest"),
        "prompt_text_length": z_state.get("prompt_text_length"),
        "authority_block_text_digest": z_state.get("authority_block_text_digest"),
        "authority_block_text_length": z_state.get("authority_block_text_length"),
        "prompt_section_ids": list(z_state.get("prompt_section_ids", [])),
        "prompt_section_digests": _mapping(z_state.get("prompt_section_digests")),
        **{field: True for field in _TRUE_FIELDS},
        **{field: False for field in _FALSE_FIELDS},
    }


def execute_followup_author_payload_authority_action(
    action: Any,
    *,
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_projection: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_history: Sequence[Mapping[str, Any]],
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorPayloadAuthorityActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
        stage=FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_PREPARED
        ),
    )
    record = build_followup_author_payload_authority_record(
        action_inputs=_mapping(action.inputs),
        followup_author_prompt_assembly_manifest_state=(
            followup_author_prompt_assembly_manifest_state
        ),
        followup_author_prompt_assembly_manifest_projection=(
            followup_author_prompt_assembly_manifest_projection
        ),
        followup_author_prompt_assembly_manifest_history=(
            followup_author_prompt_assembly_manifest_history
        ),
        followup_author_execution_activation_state=(
            followup_author_execution_activation_state
        ),
        followup_author_input_materialization_state=(
            followup_author_input_materialization_state
        ),
        followup_author_execution_readiness_state=(
            followup_author_execution_readiness_state
        ),
        followup_author_gate_state=followup_author_gate_state,
        followup_author_input_authority_state=followup_author_input_authority_state,
        final_answer_packet=final_answer_packet,
        final_answer_authority_projection=final_answer_authority_projection,
    )
    observation = Observation.from_action(
        action,
        observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_PREPARED
        ),
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_payload_authority_state": record.to_dict()},
    )
    return FollowupAuthorPayloadAuthorityActionResult(record, observation)


def build_followup_author_payload_authority_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_projection: Mapping[str, Any],
    followup_author_prompt_assembly_manifest_history: Sequence[Mapping[str, Any]],
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorPayloadAuthorityRecord:
    action = _mapping(action_inputs)
    z_state = _mapping(followup_author_prompt_assembly_manifest_state)
    z_projection = _mapping(followup_author_prompt_assembly_manifest_projection)
    z_history = [
        _mapping(item) for item in followup_author_prompt_assembly_manifest_history
    ]
    y_state = _mapping(followup_author_execution_activation_state)
    x_state = _mapping(followup_author_input_materialization_state)
    w_state = _mapping(followup_author_execution_readiness_state)
    v1_state = _mapping(followup_author_gate_state)
    u1_state = _mapping(followup_author_input_authority_state)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)

    _validate_z(z_state, z_projection, z_history)
    _validate_upstream_bindings(z_state, y_state, x_state, w_state, v1_state, u1_state)
    _validate_packet_and_projection(action, z_state, packet, authority, u1_state)
    expected_action = build_followup_author_payload_authority_action_inputs(
        followup_author_prompt_assembly_manifest_state=z_state,
        followup_author_prompt_assembly_manifest_projection=z_projection,
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
    )
    _require(action == expected_action, "AC action must match canonical Z inputs")

    payload_ref = _mapping(packet.get("author_payload_ref"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    manifest_ref = _mapping(z_state.get("author_prompt_assembly_manifest_ref"))
    authority_ref = {
        "payload_authority_ref_id": (
            "ag96i3-author-payload-authority-ref:"
            f"{z_state.get('author_prompt_assembly_manifest_id')}:"
            f"{_digest(z_state)[:16]}"
        ),
        "status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "z_author_prompt_assembly_manifest_id": z_state.get(
            "author_prompt_assembly_manifest_id"
        ),
        "z_author_prompt_assembly_manifest_digest": _digest(z_state),
        "z_author_prompt_assembly_manifest_ref_digest": _digest(manifest_ref),
        "y_author_execution_activation_id": z_state.get(
            "y_author_execution_activation_id"
        ),
        "x_author_input_materialization_id": z_state.get(
            "x_author_input_materialization_id"
        ),
        "w_author_execution_readiness_id": z_state.get(
            "w_author_execution_readiness_id"
        ),
        "v1_author_gate_id": z_state.get("v1_author_gate_id"),
        "u1_authority_id": z_state.get("u1_authority_id"),
        "packet_id": packet.get("packet_id"),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(author_input_refs),
        "author_payload_ref_id": payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": payload_ref.get("status"),
        "prompt_text_digest": z_state.get("prompt_text_digest"),
        "prompt_text_length": z_state.get("prompt_text_length"),
        "authority_block_text_digest": z_state.get("authority_block_text_digest"),
        "authority_block_text_length": z_state.get("authority_block_text_length"),
        "prompt_section_ids": list(z_state.get("prompt_section_ids", [])),
        "prompt_section_digests": _mapping(z_state.get("prompt_section_digests")),
        "payload_authority_created": True,
        "future_author_execution_must_consume": True,
        "legacy_author_payload_ref_subordinated": True,
        "final_answer_author_input_payload_created": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }
    authority_ref_digest = _digest(authority_ref)
    mutation = _payload_authority_mutation(authority_ref, authority_ref_digest)
    state = {
        **action,
        "schema_version": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_TRACE_KEY,
        "record_type": "followup_author_payload_authority_record",
        "owner": "FollowupAuthorPayloadAuthorityRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "payload_authority_stage": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE,
        "z_author_prompt_assembly_manifest_ref_status": (
            FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS
        ),
        "y_author_execution_activation_mode": (
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
        ),
        "y_author_execution_activation_ref_status": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS
        ),
        "y_old_ready_status_demoted": True,
        "y_author_input_ready": False,
        "activation_consumable_by_future_author_execution": True,
        "x_author_input_materialization_mode": (
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
        ),
        "x_bill_of_materials": _x_bill_of_materials(x_state),
        "w_author_execution_readiness_mode": (
            AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
        ),
        "v1_author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
        "u1_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "final_answer_packet_digest": _digest(packet),
        "author_payload_ref_digest": _digest(payload_ref),
        "ag96i3_author_payload_authority_ref": safe_json(authority_ref),
        "ag96i3_author_payload_authority_digest": authority_ref_digest,
        "payload_authority_ref_id": authority_ref["payload_authority_ref_id"],
        "payload_authority_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "packet_mutation": safe_json(mutation),
        "final_answer_authority_projection_mutation": safe_json(mutation),
        "updated_final_answer_packet_digest": _digest(
            _updated_with_mutation(packet, mutation)
        ),
        "updated_final_answer_authority_projection_digest": _digest(
            _updated_with_mutation(authority, mutation)
        ),
        "behavior_boundary_flags": payload_authority_boundary_flags(),
        "redaction_posture": _redaction_posture(),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorPayloadAuthorityRecord(safe_json(state))


def build_run_kernel_followup_author_payload_authority_state(
    *,
    payload_authority_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **_mapping(payload_authority_record_state),
        "owner": "RunKernel.FollowupAuthorPayloadAuthority",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_payload_authority_state(
        payload_authority_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_payload_authority_state(
    *,
    payload_authority_state: Mapping[str, Any],
) -> None:
    state = _mapping(payload_authority_state)
    _require(
        state.get("owner") == "RunKernel.FollowupAuthorPayloadAuthority",
        "AC payload authority requires RunKernel owner",
    )
    _require(state.get("canonical_state") is True, "AC requires canonical state")
    _require(state.get("trace_only") is False, "AC cannot be trace-only")
    _require(state.get("storage_only") is False, "AC cannot be storage-only")
    _require(
        state.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
        "AC payload authority status mismatch",
    )
    _require(
        state.get("payload_authority_mode")
        == AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE,
        "AC payload authority mode mismatch",
    )
    _require(
        state.get("author_payload_ref_status") == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "AC payload authority requires deferred author_payload_ref",
    )
    _validate_closed_flags(state)
    _require(
        set(_mapping(state.get("packet_mutation"))) == set(AC_PACKET_MUTATION_FIELDS),
        "AC packet mutation keys mismatch",
    )
    _reject_forbidden_payload(state)


def build_followup_author_payload_authority_projection(
    *,
    payload_authority_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_prompt_assembly_manifest_stage: str,
) -> dict[str, Any]:
    state = _mapping(payload_authority_state)
    projection = {
        "owner": "RunKernel.FollowupAuthorPayloadAuthority",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        **{field: safe_json(state.get(field)) for field in _PROJECTED_FIELDS},
        "behavior_boundary_flags": dict(behavior_boundary_flags),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
        },
        "followup_author_prompt_assembly_manifest_ref": {
            "owner": "RunKernel.FollowupAuthorPromptAssemblyManifest",
            "canonical_state": True,
            "author_prompt_assembly_manifest_id": state.get(
                "z_author_prompt_assembly_manifest_id"
            ),
            "projection_stage": followup_author_prompt_assembly_manifest_stage,
        },
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_payload_authority_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_payload_authority_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_payload_authority_state)
    _require(observed, "AC observation requires payload authority state")
    _validate_closed_flags(observed)
    for field, expected in action.items():
        _require(observed.get(field) == expected, f"AC observation {field} mismatch")
    _reject_forbidden_payload(observed)


def ac_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    packet = _mapping(current_packet)
    record = _mapping(record_state)
    mutation = _mapping(record.get("packet_mutation"))
    _require(set(mutation) == set(AC_PACKET_MUTATION_FIELDS), "AC mutation mismatch")
    _require(_digest(packet) == record.get("current_final_answer_packet_digest"), "AC stale packet")
    updated = _updated_with_mutation(packet, mutation)
    _validate_projection_update(packet, updated, record, "packet")
    return safe_json(updated)


def ac_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _mapping(current_projection)
    record = _mapping(record_state)
    mutation = _mapping(record.get("final_answer_authority_projection_mutation"))
    _require(
        set(mutation) == set(AC_AUTHORITY_PROJECTION_MUTATION_FIELDS),
        "AC authority mutation mismatch",
    )
    _require(
        _digest(projection) == record.get("final_answer_authority_projection_digest"),
        "AC stale authority projection",
    )
    updated = _updated_with_mutation(projection, mutation)
    _validate_projection_update(projection, updated, record, "authority")
    return safe_json(updated)


def payload_authority_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "canonical_final_answer_packet_mutated": True,
        "final_answer_packet_updated": True,
        "final_answer_authority_projection_mutated": True,
        "z_author_prompt_assembly_manifest_consumed": True,
        "y_author_execution_activation_consumed": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "payload_authority_created": True,
        "future_author_execution_must_consume": True,
        "legacy_author_payload_ref_subordinated": True,
        "author_payload_created": False,
        "final_answer_author_input_payload_created": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def _validate_z(
    z_state: Mapping[str, Any],
    z_projection: Mapping[str, Any],
    z_history: Sequence[Mapping[str, Any]],
) -> None:
    _require(z_state, "AC requires Z prompt assembly manifest state")
    validate_run_kernel_followup_author_prompt_assembly_manifest_state(
        manifest_state=z_state
    )
    _require(
        z_state.get("owner") == "RunKernel.FollowupAuthorPromptAssemblyManifest",
        "AC requires RunKernel Z manifest state",
    )
    _require(
        z_state.get("status") == FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
        "AC requires execution-closed Z manifest",
    )
    _require(
        z_state.get("author_prompt_assembly_manifest_mode")
        == AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
        "AC requires AG-96I3Z manifest mode",
    )
    _require(
        z_projection.get("owner") == "RunKernel.FollowupAuthorPromptAssemblyManifest",
        "AC requires RunKernel Z manifest projection",
    )
    _require(z_projection.get("canonical_state") is True, "AC requires canonical Z")
    _require(z_history and _mapping(z_history[-1]) == z_projection, "AC requires current Z history")


def _validate_upstream_bindings(
    z: Mapping[str, Any],
    y: Mapping[str, Any],
    x: Mapping[str, Any],
    w: Mapping[str, Any],
    v1: Mapping[str, Any],
    u1: Mapping[str, Any],
) -> None:
    bindings = (
        ("y_author_execution_activation_id", y, "author_execution_activation_id", "y_author_execution_activation_digest", AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE, "author_execution_activation_mode"),
        ("x_author_input_materialization_id", x, "author_input_materialization_id", "x_author_input_materialization_digest", AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE, "author_input_materialization_mode"),
        ("w_author_execution_readiness_id", w, "author_execution_readiness_id", "w_author_execution_readiness_digest", AG96I3W_AUTHOR_EXECUTION_READINESS_MODE, "author_execution_readiness_mode"),
        ("v1_author_gate_id", v1, "author_gate_id", "v1_author_gate_digest", AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE, "author_gate_mode"),
        ("u1_authority_id", u1, "author_input_authority_id", "u1_authority_digest", AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE, "author_input_authority_mode"),
    )
    for z_id, state, state_id, z_digest, mode, mode_field in bindings:
        _require(z.get(z_id) == state.get(state_id), f"AC upstream {z_id} mismatch")
        _require(z.get(z_digest) == _digest(state), f"AC upstream {z_digest} stale")
        _require(state.get(mode_field) == mode, f"AC upstream {mode_field} mismatch")
    _require(
        y.get("author_execution_activation_ref_status")
        == FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
        "AC requires Y demoted activation ref status",
    )
    _require(y.get("author_input_ready") is False, "AC requires Y ready demotion")
    _require(
        y.get("activation_consumable_by_future_author_execution") is True,
        "AC requires Y future execution consumability",
    )


def _validate_packet_and_projection(
    action: Mapping[str, Any],
    z: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    u1: Mapping[str, Any],
) -> None:
    payload_ref = _mapping(packet.get("author_payload_ref"))
    authority_payload_ref = _mapping(authority.get("author_payload_ref"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    _require(packet.get("owner") == "RunKernel.FinalAnswerPacket", "AC packet owner")
    _require(packet.get("canonical_state") is True, "AC packet canonical")
    _require(packet.get("readiness_status") == "blocked", "AC packet must be blocked")
    _require(packet.get("final_answer_allowed") is False, "AC final answer closed")
    _require(packet.get("answer_ready") is False, "AC answer not ready")
    _require(authority.get("canonical_state") is True, "AC authority canonical")
    _require(
        payload_ref.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "AC requires deferred author_payload_ref",
    )
    _require(payload_ref.get("status") != "author_input_ready", "AC rejects ready ref")
    _require(payload_ref == authority_payload_ref, "AC packet/authority ref mismatch")
    _require(payload_ref == _mapping(u1.get("author_payload_ref")), "AC U1 ref mismatch")
    _require(
        author_input_refs.get("status") == FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AC requires U1 author_input_refs",
    )
    _require(
        packet.get("author_prompt_assembly_manifest_ref")
        == _mapping(z.get("author_prompt_assembly_manifest_ref")),
        "AC packet Z ref mismatch",
    )
    _require(
        authority.get("author_prompt_assembly_manifest_ref")
        == _mapping(z.get("author_prompt_assembly_manifest_ref")),
        "AC authority Z ref mismatch",
    )
    _require(_digest(packet) == z.get("updated_final_answer_packet_digest"), "AC stale packet from Z")
    _require(
        _digest(authority) == z.get("updated_final_answer_authority_projection_digest"),
        "AC stale authority projection from Z",
    )
    for key in AC_PACKET_MUTATION_FIELDS:
        if key.startswith("ag96i3_author_payload_authority"):
            _require(not packet.get(key), "AC packet already has payload authority")
            _require(not authority.get(key), "AC authority already has payload authority")
    expected = build_followup_author_payload_authority_action_inputs(
        followup_author_prompt_assembly_manifest_state=z,
        followup_author_prompt_assembly_manifest_projection={},
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
    )
    for key in (
        "current_final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "author_input_refs_digest",
        "author_payload_ref_id",
        "author_payload_ref_status",
    ):
        _require(action.get(key) == expected.get(key), f"AC action {key} mismatch")


def _payload_authority_mutation(
    payload_authority_ref: Mapping[str, Any],
    payload_authority_digest: str,
) -> dict[str, Any]:
    return {
        "ag96i3_author_payload_authority_ref": safe_json(payload_authority_ref),
        "ag96i3_author_payload_authority_ref_created": True,
        "ag96i3_author_payload_authority_prepared": True,
        "ag96i3_author_payload_authority_status": (
            FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS
        ),
        "ag96i3_author_payload_authority_digest": payload_authority_digest,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "final_answer_author_input_payload_created": False,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
    }


def _validate_projection_update(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    record: Mapping[str, Any],
    context: str,
) -> None:
    changed = {key for key in set(before) | set(updated) if before.get(key) != updated.get(key)}
    allowed = set(AC_PACKET_MUTATION_FIELDS)
    _require(changed <= allowed, f"AC {context} changed non-AC fields")
    _require(
        _mapping(updated.get("author_payload_ref")) == _mapping(before.get("author_payload_ref")),
        f"AC {context} must not change author_payload_ref",
    )
    _require(
        _mapping(updated.get("author_payload_ref")).get("status")
        == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        f"AC {context} must keep author_payload_ref deferred",
    )
    _require(
        _mapping(updated.get("ag96i3_author_payload_authority_ref"))
        == _mapping(record.get("ag96i3_author_payload_authority_ref")),
        f"AC {context} payload authority ref mismatch",
    )


def _x_bill_of_materials(x_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "section_ids": list(x_state.get("section_ids", [])),
        "section_digests": _mapping(x_state.get("section_digests")),
        "prompt_or_input_digest": x_state.get("prompt_or_input_digest"),
        "prompt_or_input_length": x_state.get("prompt_or_input_length"),
        "authority_block_digest": x_state.get("authority_block_digest"),
        "author_payload_ref_digest": x_state.get("author_payload_ref_digest"),
        "rendered_source_entry_digest": x_state.get("rendered_source_entry_digest"),
        "source_identity_digest": x_state.get("source_identity_digest"),
    }


def _validate_closed_flags(state: Mapping[str, Any]) -> None:
    for field in _TRUE_FIELDS:
        _require(state.get(field) is True, f"AC requires {field}=True")
    for field in _FALSE_FIELDS:
        _require(state.get(field) is False, f"AC requires {field}=False")
    flags = _mapping(state.get("behavior_boundary_flags"))
    if flags:
        for field, expected in payload_authority_boundary_flags().items():
            _require(flags.get(field) is expected, f"AC boundary {field} mismatch")


def _updated_with_mutation(
    value: Mapping[str, Any],
    mutation: Mapping[str, Any],
) -> dict[str, Any]:
    return safe_json({**_mapping(value), **_mapping(mutation)})


def _payload_authority_id(z_state: Mapping[str, Any]) -> str:
    return (
        "ag96i3-author-payload-authority:"
        f"{z_state.get('author_prompt_assembly_manifest_id')}:"
        f"{_digest(z_state)[:16]}"
    )


def _redaction_posture() -> dict[str, bool]:
    posture = followup_common_redaction_posture()
    posture.update(
        {
            "prompt_text_retained": False,
            "authority_block_text_retained": False,
            "final_text_included": False,
            "product_answer_ready": False,
        }
    )
    return posture


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key or "").casefold()
            if child is False and (
                token in _FALSE_FIELDS
                or token.endswith(
                    ("allowed", "called", "created", "included", "ready", "retained")
                )
            ):
                continue
            if _closed_text_key(token):
                raise PermissionError(f"AC payload authority cannot retain {key!r}")
            _reject_forbidden_payload(child)
    elif isinstance(value, str):
        lowered = value.casefold()
        for token in _CLOSED_STRING_PARTS:
            if token in lowered:
                raise PermissionError("AC payload authority contains closed text")
        if "author_input_ready" in lowered:
            raise PermissionError("AC payload authority cannot use old ready status")
    elif isinstance(value, Sequence) and not isinstance(value, bytes):
        for child in value:
            _reject_forbidden_payload(child)


def _closed_text_key(token: str) -> bool:
    if token in {
        "prompt_text_digest",
        "prompt_text_length",
        "authority_block_text_digest",
        "authority_block_text_length",
        "prompt_section_ids",
        "prompt_section_digests",
        "prompt_or_input_digest",
        "prompt_or_input_length",
        "authority_block_digest",
    }:
        return False
    return any(part in token for part in _CLOSED_KEY_PARTS)


def _digest(value: Mapping[str, Any]) -> str:
    return followup_projection_digest(_mapping(value))


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return safe_json(dict(value))
    return {}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


__all__ = [
    "AC_AUTHORITY_PROJECTION_MUTATION_FIELDS",
    "AC_PACKET_MUTATION_FIELDS",
    "AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REASON",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_TRACE_KEY",
    "FollowupAuthorPayloadAuthorityActionResult",
    "FollowupAuthorPayloadAuthorityRecord",
    "ac_authority_projection_from_record",
    "ac_packet_projection_from_record",
    "build_followup_author_payload_authority_action_inputs",
    "build_followup_author_payload_authority_projection",
    "build_followup_author_payload_authority_record",
    "build_run_kernel_followup_author_payload_authority_state",
    "execute_followup_author_payload_authority_action",
    "payload_authority_boundary_flags",
    "reject_followup_author_payload_authority_input_spoof",
    "validate_followup_author_payload_authority_observation_binding",
    "validate_run_kernel_followup_author_payload_authority_state",
]
