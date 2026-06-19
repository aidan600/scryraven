"""AG-96I3X closed Author input materialization checkpoint.

This helper materializes only a non-executable Author input manifest from the
current W/V1/U1/packet authority. It computes deterministic section digests and
a transient label/digest envelope hash while keeping Author execution, prompt
text retention, final text, product output, live calls, and model behavior
closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
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
from core.followup_deliberation import safe_json
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.followup_fixture_boundaries import (
    followup_closed_surface_boundary_flags,
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_SCHEMA_VERSION = (
    "followup_author_input_materialization_ag96i3x_v1"
)
FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_TRACE_KEY = (
    "followup_author_input_materialization_runtime"
)
FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE = (
    "followup_author_input_materialization"
)
AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE = (
    "ag96i3x_author_input_materialization_execution_closed"
)
FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS = (
    "author_input_materialized_execution_deferred"
)
FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_REASON = (
    "ag96i3x_author_input_materialization_execution_closed"
)

AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS = (
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
)

_FALSE_FIELDS = AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS
_TRUE_FIELDS = (
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "author_input_materialized",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)

_ACTION_FORBIDDEN_KEYS = {
    "followup_author_input_materialization_state",
    "author_input_materialization_state",
    "materialization_state",
    "author_input_materialization_manifest",
    "materialization_manifest",
    "executable_author_input_payload",
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
class FollowupAuthorInputMaterializationActionResult:
    record: "FollowupAuthorInputMaterializationRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorInputMaterializationRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_input_materialization_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    """Reject caller-supplied state/payload attempts before canonical rebuild."""

    action_inputs = _mapping(inputs)
    for key in action_inputs:
        token = str(key or "").casefold()
        if token in _ACTION_FORBIDDEN_KEYS:
            raise PermissionError(
                "X materialization action cannot accept caller-supplied "
                f"{key!r}"
            )
    _reject_forbidden_payload(action_inputs)


def build_followup_author_input_materialization_action_inputs(
    *,
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_execution_readiness_projection: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_gate_projection: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    followup_author_input_authority_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
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
    return {
        "run_id": w_state.get("run_id"),
        "checkpoint_id": w_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": w_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": w_state.get("sealed_candidate_id"),
        "followup_execution_id": w_state.get("followup_execution_id"),
        "execution_id": w_state.get("execution_id"),
        "followup_evidence_intake_id": w_state.get("followup_evidence_intake_id"),
        "intake_id": w_state.get("intake_id"),
        "followup_sufficiency_recheck_id": w_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": w_state.get("recheck_id"),
        "packet_preparation_readiness_id": w_state.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": w_state.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": w_state.get("final_evidence_selection_id"),
        "citation_eligibility_id": w_state.get("citation_eligibility_id"),
        "citation_source_handoff_id": w_state.get("citation_source_handoff_id"),
        "citation_rendering_id": w_state.get("citation_rendering_id"),
        "packet_id": packet.get("packet_id"),
        "author_input_materialization_id": (
            "followup-author-input-materialization:"
            f"{w_state.get('author_execution_readiness_id')}"
        ),
        "author_input_materialization_mode": (
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
        ),
        "status": FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_status": w_state.get("status"),
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
        "current_final_answer_packet_digest": followup_projection_digest(packet),
        "final_answer_packet_digest": followup_projection_digest(packet),
        "final_answer_authority_projection_digest": followup_projection_digest(
            authority
        ),
        "author_input_refs_digest": followup_projection_digest(author_input_refs),
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "rendered_source_entry_digest": author_input_refs.get(
            "rendered_source_entry_digest"
        ),
        "source_identity_digest": author_input_refs.get("source_identity_digest"),
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_input_materialized": True,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
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


def execute_followup_author_input_materialization_action(
    action: Any,
    *,
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
) -> FollowupAuthorInputMaterializationActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
        stage=FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZED
        ),
    )
    record = build_followup_author_input_materialization_record(
        action_inputs=_mapping(action.inputs),
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
        observation_type=ObservationType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZED,
        status=RunStageStatus.COMPLETED,
        payload={
            "followup_author_input_materialization_state": record.to_dict()
        },
    )
    return FollowupAuthorInputMaterializationActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_input_materialization_record(
    *,
    action_inputs: Mapping[str, Any],
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
) -> FollowupAuthorInputMaterializationRecord:
    action = _mapping(action_inputs)
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
    _validate_w_current(
        action=action,
        w_state=w_state,
        w_projection=w_projection,
        w_history=w_history,
    )
    _validate_v1_current(
        action=action,
        w_state=w_state,
        v1_state=v1_state,
        v1_projection=v1_projection,
        v1_history=v1_history,
    )
    _validate_u1_current(
        action=action,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        u1_history=u1_history,
        authority=authority,
    )
    _validate_packet_authority(
        action=action,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        packet=packet,
        authority=authority,
    )

    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
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

    section_manifest = _section_manifest(
        w_digest=w_digest,
        w_projection_digest=w_projection_digest,
        v1_digest=v1_digest,
        v1_projection_digest=v1_projection_digest,
        u1_digest=u1_digest,
        u1_projection_digest=u1_projection_digest,
        packet_digest=packet_digest,
        authority_digest=authority_digest,
        author_input_refs_digest=author_input_refs_digest,
        payload_ref_digest=payload_ref_digest,
        rendered_source_entry_digest=author_input_refs.get(
            "rendered_source_entry_digest"
        ),
        source_identity_digest=author_input_refs.get("source_identity_digest"),
    )
    authority_block = {
        "section_ids": [
            "final_answer_authority_projection",
            "author_input_refs",
            "author_payload_ref",
        ],
        "section_digests": {
            "final_answer_authority_projection": authority_digest,
            "author_input_refs": author_input_refs_digest,
            "author_payload_ref": payload_ref_digest,
        },
    }
    authority_block_digest = followup_projection_digest(authority_block)
    transient_envelope = _transient_materialization_envelope(
        materialization_id=action.get("author_input_materialization_id"),
        status=FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
        section_manifest=section_manifest,
        authority_block_digest=authority_block_digest,
        author_payload_ref_status=author_payload_ref.get("status"),
    )
    prompt_or_input_digest = _text_digest(transient_envelope)
    prompt_or_input_length = len(transient_envelope)
    section_digests = {
        item["section_id"]: item["section_digest"] for item in section_manifest
    }
    manifest = {
        "manifest_type": "non_executable_author_input_materialization_manifest",
        "author_input_materialization_id": action.get(
            "author_input_materialization_id"
        ),
        "status": FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "section_ids": list(section_digests),
        "section_digests": section_digests,
        "prompt_or_input_digest": prompt_or_input_digest,
        "prompt_or_input_length": prompt_or_input_length,
        "authority_block_digest": authority_block_digest,
        "redaction_posture": _redaction_posture(),
        "executable_payload_created": False,
        "prompt_text_retained": False,
        "final_text_included": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }
    state = {
        "schema_version": FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_TRACE_KEY,
        "record_type": "followup_author_input_materialization_record",
        "owner": "FollowupAuthorInputMaterializationRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "author_input_materialization_id": action.get(
            "author_input_materialization_id"
        ),
        "author_input_materialization_mode": (
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
        ),
        "author_input_materialization_stage": (
            FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE
        ),
        "status": FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
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
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_status": w_state.get("status"),
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
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "author_payload_ref_digest": payload_ref_digest,
        "rendered_source_entry_digest": author_input_refs.get(
            "rendered_source_entry_digest"
        ),
        "source_identity_digest": author_input_refs.get("source_identity_digest"),
        "section_ids": list(section_digests),
        "section_digests": section_digests,
        "authority_block_digest": authority_block_digest,
        "prompt_or_input_digest": prompt_or_input_digest,
        "prompt_or_input_length": prompt_or_input_length,
        "author_input_materialization_manifest": manifest,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_input_materialized": True,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
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
        "packet_readiness_posture": {
            "readiness_status": packet.get("readiness_status"),
            "final_answer_allowed": packet.get("final_answer_allowed"),
            "answer_ready": packet.get("answer_ready"),
            "product_answer_ready": packet.get("product_answer_ready"),
        },
        "behavior_boundary_flags": materialization_boundary_flags(),
        "redaction_posture": _redaction_posture(),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorInputMaterializationRecord(state=safe_json(state))


def build_followup_author_input_materialization_projection(
    *,
    materialization_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_execution_readiness_stage: str,
    followup_author_gate_stage: str,
    followup_author_input_authority_stage: str,
) -> dict[str, Any]:
    state = _mapping(materialization_state)
    return {
        "owner": "RunKernel.FollowupAuthorInputMaterialization",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": state.get("schema_version"),
        "status": state.get("status"),
        "author_input_materialization_id": state.get(
            "author_input_materialization_id"
        ),
        "author_input_materialization_mode": state.get(
            "author_input_materialization_mode"
        ),
        "author_input_materialization_stage": state.get(
            "author_input_materialization_stage"
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
        "w_author_execution_readiness_id": state.get(
            "w_author_execution_readiness_id"
        ),
        "w_author_execution_readiness_status": state.get(
            "w_author_execution_readiness_status"
        ),
        "w_author_execution_readiness_digest": state.get(
            "w_author_execution_readiness_digest"
        ),
        "w_author_execution_readiness_projection_digest": state.get(
            "w_author_execution_readiness_projection_digest"
        ),
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
        "author_payload_ref_id": state.get("author_payload_ref_id"),
        "author_payload_ref_status": state.get("author_payload_ref_status"),
        "author_payload_ref_digest": state.get("author_payload_ref_digest"),
        "rendered_source_entry_digest": state.get("rendered_source_entry_digest"),
        "source_identity_digest": state.get("source_identity_digest"),
        "section_ids": list(state.get("section_ids", [])),
        "section_digests": dict(_mapping(state.get("section_digests"))),
        "authority_block_digest": state.get("authority_block_digest"),
        "prompt_or_input_digest": state.get("prompt_or_input_digest"),
        "prompt_or_input_length": state.get("prompt_or_input_length"),
        "author_input_materialization_manifest": _mapping(
            state.get("author_input_materialization_manifest")
        ),
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_input_materialized": True,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
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
        "redaction_posture": _mapping(state.get("redaction_posture")),
        "canonical_final_answer_packet_ref": {
            "owner": "RunKernel.FinalAnswerPacket",
            "canonical_state": True,
            "packet_id": state.get("packet_id"),
            "projection_stage": final_answer_packet_stage,
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


def validate_followup_author_input_materialization_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_materialization_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_materialization_state)
    if not observed:
        raise PermissionError(
            "X observation requires followup_author_input_materialization_state"
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
        "author_input_materialization_id",
        "author_input_materialization_mode",
        "w_author_execution_readiness_id",
        "w_author_execution_readiness_status",
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
        "rendered_source_entry_digest",
        "source_identity_digest",
    ):
        if observed.get(field) != action.get(field):
            raise PermissionError(f"X observation {field} does not match action")
    if observed.get("status") != FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS:
        raise PermissionError("X observation status mismatch")
    for field in _TRUE_FIELDS:
        if observed.get(field) is not True:
            raise PermissionError(f"X observation requires {field}=True")
    for field in _FALSE_FIELDS:
        if observed.get(field) is not False:
            raise PermissionError(f"X observation requires {field}=False")
    if observed.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("X observation must not make payload executable")
    _reject_forbidden_payload(observed)


def materialization_boundary_flags() -> dict[str, bool]:
    return {
        **followup_closed_surface_boundary_flags(),
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_rebuilt": False,
        "final_answer_packet_updated": False,
        "canonical_final_answer_packet_mutated": False,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "author_input_materialized": True,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_payload_status_changed": False,
        "prompt_text_retained": False,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "analyst_handoff_created": False,
        "economist_handoff_created": False,
    }


def _validate_action(action: Mapping[str, Any]) -> None:
    if action.get("author_input_materialization_mode") != (
        AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
    ):
        raise PermissionError("X action requires AG-96I3X materialization mode")
    if action.get("status") not in (
        None,
        FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
    ):
        raise PermissionError("X action status mismatch")
    if action.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("X action requires deferred author_payload_ref")
    if action.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("X action must not use executable payload status")
    for key in action:
        if str(key or "").casefold() in _ACTION_FORBIDDEN_KEYS:
            raise PermissionError(
                "X action cannot accept caller-supplied materialization state"
            )
    for field in _TRUE_FIELDS:
        if action.get(field) is not True:
            raise PermissionError(f"X action requires {field}=True")
    for field in _FALSE_FIELDS:
        if action.get(field) is not False:
            raise PermissionError(f"X action requires {field}=False")
    _reject_forbidden_payload(action)


def _validate_w_current(
    *,
    action: Mapping[str, Any],
    w_state: Mapping[str, Any],
    w_projection: Mapping[str, Any],
    w_history: Sequence[Mapping[str, Any]],
) -> None:
    if w_state.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("X requires RunKernel W readiness state")
    if w_state.get("canonical_state") is not True:
        raise PermissionError("X requires canonical W readiness state")
    if w_state.get("trace_only") is not False or w_state.get("storage_only") is not False:
        raise PermissionError("X requires active W readiness state")
    if w_state.get("author_execution_readiness_mode") != (
        AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
    ):
        raise PermissionError("X requires AG-96I3W readiness mode")
    if w_state.get("status") != FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS:
        raise PermissionError("X requires W execution-closed readiness status")
    if w_projection.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("X requires RunKernel W readiness projection")
    if w_projection.get("canonical_state") is not True:
        raise PermissionError("X requires canonical W readiness projection")
    if not w_history:
        raise PermissionError("X requires W readiness history")
    if _mapping(w_history[-1]) != w_projection:
        raise PermissionError("X requires current W readiness history")
    if w_projection.get("author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("X W projection/state id mismatch")
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
            raise PermissionError(f"X requires W {field}=True")
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
            raise PermissionError(f"X requires W {field}=False")
    if w_state.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("X rejects executable W payload status")
    if w_state.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("X requires deferred W payload status")
    flags = _mapping(w_state.get("behavior_boundary_flags"))
    for field in (
        "author_execution_allowed",
        "author_activation_allowed",
        "author_payload_status_changed",
        "prompt_text_included",
        "final_text_included",
        "product_answer_ready",
        "model_called",
    ):
        if flags.get(field) is not False:
            raise PermissionError(f"X requires W boundary {field}=False")
    if action.get("w_author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("X W readiness id mismatch")
    if action.get("w_author_execution_readiness_status") != w_state.get("status"):
        raise PermissionError("X W readiness status mismatch")
    if action.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("X W readiness digest mismatch")
    if action.get("w_author_execution_readiness_projection_digest") != (
        followup_projection_digest(w_projection)
    ):
        raise PermissionError("X W readiness projection digest mismatch")


def _validate_v1_current(
    *,
    action: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    v1_projection: Mapping[str, Any],
    v1_history: Sequence[Mapping[str, Any]],
) -> None:
    if v1_state.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("X requires RunKernel V1 Author gate state")
    if v1_state.get("canonical_state") is not True:
        raise PermissionError("X requires canonical V1 Author gate state")
    if v1_state.get("trace_only") is not False or v1_state.get("storage_only") is not False:
        raise PermissionError("X requires active V1 Author gate state")
    if v1_state.get("author_gate_mode") != AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE:
        raise PermissionError("X requires AG-96I3V1 Author gate mode")
    if v1_projection.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("X requires RunKernel V1 Author gate projection")
    if v1_projection.get("canonical_state") is not True:
        raise PermissionError("X requires canonical V1 Author gate projection")
    if not v1_history:
        raise PermissionError("X requires V1 Author gate history")
    if _mapping(v1_history[-1]) != v1_projection:
        raise PermissionError("X requires current V1 Author gate history")
    if w_state.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("X W/V1 Author gate id mismatch")
    if w_state.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("X stale W V1 digest")
    if w_state.get("v1_author_gate_projection_digest") != (
        followup_projection_digest(v1_projection)
    ):
        raise PermissionError("X stale W V1 projection digest")
    for field in (
        "author_gate_consumed",
        "author_input_authority_consumed",
        "packet_authority_consumed",
        "author_execution_deferred",
        "live_validation_not_run",
    ):
        if v1_state.get(field) is not True:
            raise PermissionError(f"X requires V1 {field}=True")
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
            raise PermissionError(f"X requires V1 {field}=False")
    if action.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("X V1 Author gate id mismatch")
    if action.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("X V1 Author gate digest mismatch")
    if action.get("v1_author_gate_projection_digest") != (
        followup_projection_digest(v1_projection)
    ):
        raise PermissionError("X V1 Author gate projection digest mismatch")


def _validate_u1_current(
    *,
    action: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    u1_history: Sequence[Mapping[str, Any]],
    authority: Mapping[str, Any],
) -> None:
    if u1_state.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("X requires RunKernel U1 authority state")
    if u1_state.get("canonical_state") is not True:
        raise PermissionError("X requires canonical U1 authority state")
    if u1_state.get("trace_only") is not False or u1_state.get("storage_only") is not False:
        raise PermissionError("X requires active U1 authority state")
    if u1_state.get("author_input_authority_mode") != (
        AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    ):
        raise PermissionError("X requires AG-96I3U1 authority mode")
    if u1_projection.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("X requires RunKernel U1 authority projection")
    if u1_projection.get("canonical_state") is not True:
        raise PermissionError("X requires canonical U1 authority projection")
    if not u1_history:
        raise PermissionError("X requires U1 authority history")
    if _mapping(u1_history[-1]) != u1_projection:
        raise PermissionError("X requires current U1 authority history")
    if authority != u1_projection:
        raise PermissionError("X requires current U1 final-answer authority")
    if _mapping(u1_state.get("final_answer_authority_projection")) != u1_projection:
        raise PermissionError("X requires U1 state/projection binding")
    if v1_state.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("X V1/U1 authority id mismatch")
    if w_state.get("u1_authority_id") != u1_state.get("author_input_authority_id"):
        raise PermissionError("X W/U1 authority id mismatch")
    if w_state.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("X stale W U1 digest")
    if w_state.get("u1_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("X stale W U1 projection digest")
    if w_state.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("X stale W final_answer_authority_projection digest")
    if action.get("u1_authority_id") != u1_state.get("author_input_authority_id"):
        raise PermissionError("X U1 authority id mismatch")
    if action.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("X U1 authority digest mismatch")
    if action.get("u1_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("X U1 authority projection digest mismatch")


def _validate_packet_authority(
    *,
    action: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("X requires RunKernel FinalAnswerPacket")
    if packet.get("canonical_state") is not True:
        raise PermissionError("X requires canonical FinalAnswerPacket")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("X requires blocked FinalAnswerPacket")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("X requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("X requires answer_ready=false")
    if packet.get("product_answer_ready") is not False:
        raise PermissionError("X requires product_answer_ready=false")
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    if author_input_refs.get("status") != FOLLOWUP_AUTHOR_INPUT_REFS_STATUS:
        raise PermissionError("X requires U1 author_input_refs")
    if author_payload_ref.get("status") == "author_input_ready":
        raise PermissionError("X rejects executable author_payload_ref")
    if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("X requires deferred author_payload_ref")
    if author_input_refs != _mapping(u1_state.get("author_input_refs")):
        raise PermissionError("X packet author_input_refs mismatch")
    if author_payload_ref != _mapping(u1_state.get("author_payload_ref")):
        raise PermissionError("X packet author_payload_ref mismatch")
    if author_payload_ref != _mapping(u1_projection.get("author_payload_ref")):
        raise PermissionError("X U1 projection author_payload_ref mismatch")
    if author_input_refs.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("X author_input_refs authority id mismatch")
    if author_input_refs.get("author_payload_ref_id") != (
        author_payload_ref.get("payload_ref_id")
    ):
        raise PermissionError("X author_input_refs payload ref mismatch")
    if author_input_refs.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("X author_input_refs authority digest mismatch")
    if v1_state.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("X stale V1 FinalAnswerPacket digest")
    if v1_state.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("X stale V1 author_input_refs digest")
    if v1_state.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("X V1 author_payload_ref id mismatch")
    if v1_state.get("author_payload_ref_status") != author_payload_ref.get(
        "status"
    ):
        raise PermissionError("X V1 author_payload_ref status mismatch")
    if w_state.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("X stale W FinalAnswerPacket digest")
    if w_state.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("X stale W author_input_refs digest")
    if w_state.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("X W author_payload_ref id mismatch")
    if w_state.get("author_payload_ref_status") != author_payload_ref.get("status"):
        raise PermissionError("X W author_payload_ref status mismatch")
    if action.get("current_final_answer_packet_digest") != (
        followup_projection_digest(packet)
    ):
        raise PermissionError("X current FinalAnswerPacket digest mismatch")
    if action.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(authority)
    ):
        raise PermissionError("X final_answer_authority_projection digest mismatch")
    if action.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("X author_input_refs digest mismatch")
    if action.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("X author_payload_ref id mismatch")
    if action.get("author_payload_ref_status") != author_payload_ref.get("status"):
        raise PermissionError("X author_payload_ref status mismatch")
    if action.get("rendered_source_entry_digest") != author_input_refs.get(
        "rendered_source_entry_digest"
    ):
        raise PermissionError("X rendered source entry digest mismatch")
    if action.get("source_identity_digest") != author_input_refs.get(
        "source_identity_digest"
    ):
        raise PermissionError("X source identity digest mismatch")


def _section_manifest(
    *,
    w_digest: str,
    w_projection_digest: str,
    v1_digest: str,
    v1_projection_digest: str,
    u1_digest: str,
    u1_projection_digest: str,
    packet_digest: str,
    authority_digest: str,
    author_input_refs_digest: str,
    payload_ref_digest: str,
    rendered_source_entry_digest: Any,
    source_identity_digest: Any,
) -> list[dict[str, str | None]]:
    return [
        {
            "section_id": "w_author_execution_readiness",
            "section_digest": w_digest,
        },
        {
            "section_id": "w_author_execution_readiness_projection",
            "section_digest": w_projection_digest,
        },
        {"section_id": "v1_author_gate", "section_digest": v1_digest},
        {
            "section_id": "v1_author_gate_projection",
            "section_digest": v1_projection_digest,
        },
        {"section_id": "u1_authority", "section_digest": u1_digest},
        {
            "section_id": "u1_authority_projection",
            "section_digest": u1_projection_digest,
        },
        {"section_id": "final_answer_packet", "section_digest": packet_digest},
        {
            "section_id": "final_answer_authority_projection",
            "section_digest": authority_digest,
        },
        {
            "section_id": "author_input_refs",
            "section_digest": author_input_refs_digest,
        },
        {"section_id": "author_payload_ref", "section_digest": payload_ref_digest},
        {
            "section_id": "rendered_source_entries",
            "section_digest": rendered_source_entry_digest,
        },
        {"section_id": "source_identity", "section_digest": source_identity_digest},
    ]


def _transient_materialization_envelope(
    *,
    materialization_id: Any,
    status: str,
    section_manifest: Sequence[Mapping[str, Any]],
    authority_block_digest: str,
    author_payload_ref_status: Any,
) -> str:
    lines = [
        f"materialization_id:{materialization_id}",
        f"status:{status}",
        f"authority_block_digest:{authority_block_digest}",
        f"author_payload_ref_status:{author_payload_ref_status}",
    ]
    for section in section_manifest:
        lines.append(f"{section.get('section_id')}:{section.get('section_digest')}")
    return "\n".join(lines)


def _text_digest(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _redaction_posture() -> dict[str, bool]:
    posture = followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )
    posture["prompt_text_retained"] = False
    posture["final_text_included"] = False
    return posture


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").casefold()
            if token in {
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
            }:
                if item is not False:
                    raise PermissionError(f"X {token} must be false")
                continue
            if token == "status" and item == "author_input_ready":
                raise PermissionError("X materialization must not be executable")
            if token == "author_payload_ref_status" and item == "author_input_ready":
                raise PermissionError("X materialization must not be executable")
            if token == "not_role_consumption_payload":
                if item is not True:
                    raise PermissionError(
                        "X not_role_consumption_payload must be true"
                    )
                continue
            if any(part in token for part in _FORBIDDEN_KEY_PARTS):
                if item in (None, False, [], {}, (), ""):
                    continue
                raise PermissionError(f"X materialization includes closed field {key!r}")
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
            "sk-",
        ):
            if marker in lowered:
                raise PermissionError(
                    "X materialization includes private text marker"
                )
        if lowered == "author_input_ready":
            raise PermissionError("X materialization must not be executable")


def _mapping(value: Any) -> dict[str, Any]:
    safe = safe_json(value or {})
    return dict(safe) if isinstance(safe, Mapping) else {}


__all__ = [
    "AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE",
    "AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_REASON",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_TRACE_KEY",
    "FollowupAuthorInputMaterializationActionResult",
    "FollowupAuthorInputMaterializationRecord",
    "build_followup_author_input_materialization_action_inputs",
    "build_followup_author_input_materialization_projection",
    "build_followup_author_input_materialization_record",
    "execute_followup_author_input_materialization_action",
    "materialization_boundary_flags",
    "reject_followup_author_input_materialization_input_spoof",
    "validate_followup_author_input_materialization_observation_binding",
]
