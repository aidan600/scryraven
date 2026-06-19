"""AG-96I3AC Z-consuming Author payload authority.

This module turns the canonical AG-96I3Z prompt assembly manifest into the
non-executable payload authority that a later Author execution phase must
consume. It keeps refs, digests, lengths, and closed-surface flags only.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
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
from core.followup_author_payload_safety import (
    boundary_flags_from_tokens,
    reject_caller_controlled_inputs,
    validate_expected_action_fields,
    validate_no_existing_prefixed_fields,
    validate_packet_authority_currentness,
    validate_packet_projection_base,
)
from core.followup_author_payload_safety import (
    projection_digest as _digest,
)
from core.followup_author_payload_safety import (
    projection_from_record_mutation as _projection_from_record_mutation,
)
from core.followup_author_payload_safety import (
    reject_closed_surface_payload as _reject_closed_surface_payload,
)
from core.followup_author_payload_safety import (
    require as _require,
)
from core.followup_author_payload_safety import (
    safe_mapping as _mapping,
)
from core.followup_author_payload_safety import (
    updated_with_mutation as _updated_with_mutation,
)
from core.followup_author_payload_safety import (
    validate_closed_flags as _shared_validate_closed_flags,
)
from core.followup_author_payload_safety import (
    validate_projection_update as _shared_validate_projection_update,
)
from core.followup_author_prompt_assembly_manifest_runtime import (
    AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
    validate_run_kernel_followup_author_prompt_assembly_manifest_state,
)
from core.followup_deliberation import safe_json
from core.followup_fixture_boundaries import (
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
_CLOSED_KEY_ALLOWED_TOKENS = frozenset(
    {
        "prompt_text_digest",
        "prompt_text_length",
        "authority_block_text_digest",
        "authority_block_text_length",
        "prompt_section_ids",
        "prompt_section_digests",
        "prompt_or_input_digest",
        "prompt_or_input_length",
        "authority_block_digest",
    }
)
_reject_forbidden_payload = partial(
    _reject_closed_surface_payload,
    false_fields=_FALSE_FIELDS,
    allowed_key_tokens=_CLOSED_KEY_ALLOWED_TOKENS,
    closed_key_parts=_CLOSED_KEY_PARTS,
    closed_string_parts=_CLOSED_STRING_PARTS,
    context_label="AC payload authority",
    old_ready_status_policy="contains",
)
_validate_projection_update = partial(
    _shared_validate_projection_update,
    allowed_mutation_fields=AC_PACKET_MUTATION_FIELDS,
    phase_label="AC",
    ref_field="ag96i3_author_payload_authority_ref",
    ref_label="payload authority ref",
    author_payload_ref_status=FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
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
_BOUNDARY_FLAG_TOKENS = "+canonical_final_answer_packet_mutated +final_answer_packet_updated +final_answer_authority_projection_mutated +z_author_prompt_assembly_manifest_consumed +y_author_execution_activation_consumed +x_author_input_materialization_consumed +w_author_execution_readiness_consumed +v1_author_gate_consumed +u1_authority_consumed +packet_authority_consumed +payload_authority_created +future_author_execution_must_consume +legacy_author_payload_ref_subordinated -author_payload_created -final_answer_author_input_payload_created -author_input_ready -author_execution_allowed -author_activation_allowed +author_execution_deferred -prompt_text_retained -authority_block_text_retained -final_text_included -product_answer_ready -model_called -author_observation_created -final_answer_outcome_created +live_validation_not_run +not_for_product_answer_activation".split()


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
    reject_caller_controlled_inputs(inputs, caller_controlled_keys=_CALLER_CONTROLLED_KEYS, context_label="AC payload authority action", closed_surface_rejector=_reject_forbidden_payload)


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
    return _projection_from_record_mutation(
        current_packet, record_state, "packet", "packet_mutation", AC_PACKET_MUTATION_FIELDS, "current_final_answer_packet_digest", "AC mutation mismatch", "AC stale packet", _validate_projection_update
    )


def ac_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return _projection_from_record_mutation(
        current_projection, record_state, "authority", "final_answer_authority_projection_mutation", AC_AUTHORITY_PROJECTION_MUTATION_FIELDS, "final_answer_authority_projection_digest", "AC authority mutation mismatch", "AC stale authority projection", _validate_projection_update
    )


def payload_authority_boundary_flags() -> dict[str, bool]:
    return boundary_flags_from_tokens(_BOUNDARY_FLAG_TOKENS)


_validate_closed_flags = partial(
    _shared_validate_closed_flags,
    true_fields=_TRUE_FIELDS,
    false_fields=_FALSE_FIELDS,
    boundary_flags=payload_authority_boundary_flags,
    context_label="AC",
)


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
    payload_ref, author_input_refs = validate_packet_projection_base(
        packet,
        authority,
        u1,
        "AC",
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AC packet/authority ref mismatch",
        "AC U1 ref mismatch",
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
    validate_packet_authority_currentness(
        packet,
        authority,
        z,
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        "AC stale packet from Z",
        "AC stale authority projection from Z",
    )
    validate_no_existing_prefixed_fields(
        packet,
        authority,
        AC_PACKET_MUTATION_FIELDS,
        "ag96i3_author_payload_authority",
        "AC packet already has payload authority",
        "AC authority already has payload authority",
    )
    expected = build_followup_author_payload_authority_action_inputs(
        followup_author_prompt_assembly_manifest_state=z,
        followup_author_prompt_assembly_manifest_projection={},
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
    )
    validate_expected_action_fields(
        action,
        expected,
        (
            "current_final_answer_packet_digest",
            "final_answer_authority_projection_digest",
            "author_input_refs_digest",
            "author_payload_ref_id",
            "author_payload_ref_status",
        ),
        "AC",
    )


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
