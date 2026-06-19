"""AG-96I3Z Y-bound Author prompt assembly manifest checkpoint.

This helper prepares only a non-executable prompt assembly manifest from the
current Y/X/W/V1/U1/packet authority chain. Prompt and authority-block text are
constructed only in local variables to compute hashes, lengths, and section
digests; neither text is retained in state, projection, history, observation, or
packet surfaces.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.followup_author_execution_activation_runtime import (
    AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS,
    validate_run_kernel_followup_author_execution_activation_state,
)
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

FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_SCHEMA_VERSION = (
    "followup_author_prompt_assembly_manifest_ag96i3z_v1"
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_TRACE_KEY = (
    "followup_author_prompt_assembly_manifest_runtime"
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE = (
    "followup_author_prompt_assembly_manifest"
)
AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE = (
    "ag96i3z_y_bound_prompt_assembly_manifest_execution_closed"
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS = (
    "author_prompt_assembly_manifest_ready_execution_closed"
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS = (
    "y_bound_prompt_assembly_manifest_ready_execution_closed"
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REASON = (
    "ag96i3z_y_bound_prompt_assembly_manifest_execution_closed"
)

Z_PACKET_MUTATION_FIELDS = frozenset(
    {
        "author_prompt_assembly_manifest_ref",
        "author_prompt_assembly_manifest_ref_created",
        "author_prompt_assembly_manifest_prepared",
        "author_prompt_assembly_manifest_status",
        "author_prompt_assembly_manifest_digest",
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_execution_deferred",
        "prompt_text_included",
        "prompt_text_retained",
        "authority_block_text_retained",
        "final_text_included",
        "product_answer_ready",
    }
)
Z_AUTHORITY_PROJECTION_MUTATION_FIELDS = Z_PACKET_MUTATION_FIELDS

_FALSE_FIELDS = (
    "author_input_ready",
    "author_execution_allowed",
    "author_activation_allowed",
    "author_payload_ref_status_changed",
    "prompt_text_retained",
    "authority_block_text_retained",
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
    "final_answer_author_input_payload_created",
    "author_payload_ref_status_changed",
)
_OPTIONAL_FALSE_FIELDS = {
    "author_payload_ref_status_changed_to_author_input_ready",
    "author_payload_ref_status_changed_from_deferred",
    "author_input_payload_created",
}
_TRUE_FIELDS = (
    "y_author_execution_activation_consumed",
    "x_author_input_materialization_consumed",
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "prompt_assembly_manifest_prepared",
    "transient_prompt_text_constructed",
    "transient_authority_block_text_constructed",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)

_ACTION_FORBIDDEN_KEYS = {
    "followup_author_prompt_assembly_manifest_state",
    "author_prompt_assembly_manifest_state",
    "prompt_assembly_manifest_state",
    "author_prompt_assembly_manifest_ref",
    "prompt_assembly_manifest_ref",
    "prompt_text",
    "authority_block_text",
    "final_answer_author_input_payload",
    "author_input_payload",
    "executable_author_input_payload",
}

_PROMPT_METADATA_KEYS = {
    "author_prompt_assembly_manifest_ref",
    "author_prompt_assembly_manifest_ref_created",
    "author_prompt_assembly_manifest_prepared",
    "author_prompt_assembly_manifest_status",
    "author_prompt_assembly_manifest_digest",
    "author_prompt_assembly_manifest_id",
    "author_prompt_assembly_manifest_mode",
    "author_prompt_assembly_manifest_stage",
    "prompt_assembly_manifest_ref_id",
    "prompt_assembly_manifest_prepared",
    "prompt_text_digest",
    "prompt_text_length",
    "prompt_section_ids",
    "prompt_section_digests",
    "transient_prompt_text_constructed",
    "prompt_text_retained",
    "prompt_text_included",
}
_AUTHORITY_BLOCK_METADATA_KEYS = {
    "authority_block_text_digest",
    "authority_block_text_length",
    "transient_authority_block_text_constructed",
    "authority_block_text_retained",
}
_CLOSED_KEY_PARTS = (
    "raw_prompt",
    "author_prompt_text",
    "prompt_body",
    "prompt_value",
    "prompt_content",
    "authority_block_text_value",
    "authority_block_text_body",
    "final_answer_text",
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
class FollowupAuthorPromptAssemblyManifestActionResult:
    record: "FollowupAuthorPromptAssemblyManifestRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorPromptAssemblyManifestRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_prompt_assembly_manifest_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    """Reject caller-supplied state/payload/text attempts before rebuild."""

    action_inputs = _mapping(inputs)
    for key in action_inputs:
        token = str(key or "").casefold()
        if token in _ACTION_FORBIDDEN_KEYS:
            raise PermissionError(
                "Z prompt assembly manifest action cannot accept "
                f"caller-supplied {key!r}"
            )
    _reject_forbidden_payload(action_inputs)


def build_followup_author_prompt_assembly_manifest_action_inputs(
    *,
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_execution_activation_projection: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    y_state = _mapping(followup_author_execution_activation_state)
    y_projection = _mapping(followup_author_execution_activation_projection)
    x_state = _mapping(followup_author_input_materialization_state)
    w_state = _mapping(followup_author_execution_readiness_state)
    v1_state = _mapping(followup_author_gate_state)
    u1_state = _mapping(followup_author_input_authority_state)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    y_digest = followup_projection_digest(y_state)
    y_projection_digest = followup_projection_digest(y_projection)
    y_activation_ref = _mapping(y_state.get("author_execution_activation_ref"))
    y_activation_ref_digest = followup_projection_digest(y_activation_ref)
    packet_digest = followup_projection_digest(packet)
    authority_digest = followup_projection_digest(authority)
    prompt_material = _prompt_material(
        manifest_id=_manifest_id(y_state),
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        packet=packet,
        authority=authority,
    )
    return {
        "run_id": y_state.get("run_id"),
        "checkpoint_id": y_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": y_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": y_state.get("sealed_candidate_id"),
        "followup_execution_id": y_state.get("followup_execution_id"),
        "execution_id": y_state.get("execution_id"),
        "followup_evidence_intake_id": y_state.get("followup_evidence_intake_id"),
        "intake_id": y_state.get("intake_id"),
        "followup_sufficiency_recheck_id": y_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": y_state.get("recheck_id"),
        "packet_preparation_readiness_id": y_state.get(
            "packet_preparation_readiness_id"
        ),
        "blocked_final_answer_packet_shell_id": y_state.get(
            "blocked_final_answer_packet_shell_id"
        ),
        "final_evidence_selection_id": y_state.get("final_evidence_selection_id"),
        "citation_eligibility_id": y_state.get("citation_eligibility_id"),
        "citation_source_handoff_id": y_state.get("citation_source_handoff_id"),
        "citation_rendering_id": y_state.get("citation_rendering_id"),
        "packet_id": packet.get("packet_id"),
        "author_prompt_assembly_manifest_id": _manifest_id(y_state),
        "author_prompt_assembly_manifest_mode": (
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
        ),
        "status": FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
        "y_author_execution_activation_id": y_state.get(
            "author_execution_activation_id"
        ),
        "y_author_execution_activation_digest": y_digest,
        "y_author_execution_activation_projection_digest": y_projection_digest,
        "y_author_execution_activation_ref_id": y_activation_ref.get(
            "activation_ref_id"
        ),
        "y_author_execution_activation_ref_digest": y_activation_ref_digest,
        "x_author_input_materialization_id": x_state.get(
            "author_input_materialization_id"
        ),
        "x_author_input_materialization_digest": followup_projection_digest(x_state),
        "w_author_execution_readiness_id": w_state.get(
            "author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": followup_projection_digest(w_state),
        "v1_author_gate_id": v1_state.get("author_gate_id"),
        "v1_author_gate_digest": followup_projection_digest(v1_state),
        "u1_authority_id": u1_state.get("author_input_authority_id"),
        "u1_authority_digest": followup_projection_digest(u1_state),
        "current_final_answer_packet_digest": packet_digest,
        "final_answer_packet_digest": packet_digest,
        "final_answer_authority_projection_digest": authority_digest,
        "author_input_refs_digest": followup_projection_digest(author_input_refs),
        "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
        "author_payload_ref_status": author_payload_ref.get("status"),
        "prompt_text_digest": prompt_material["prompt_text_digest"],
        "prompt_text_length": prompt_material["prompt_text_length"],
        "authority_block_text_digest": prompt_material[
            "authority_block_text_digest"
        ],
        "authority_block_text_length": prompt_material[
            "authority_block_text_length"
        ],
        "prompt_section_ids": prompt_material["prompt_section_ids"],
        "prompt_section_digests": prompt_material["prompt_section_digests"],
        "y_author_execution_activation_consumed": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "prompt_assembly_manifest_prepared": True,
        "transient_prompt_text_constructed": True,
        "transient_authority_block_text_constructed": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_answer_author_input_payload_created": False,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
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


def execute_followup_author_prompt_assembly_manifest_action(
    action: Any,
    *,
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_execution_activation_projection: Mapping[str, Any],
    followup_author_execution_activation_history: Sequence[Mapping[str, Any]],
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
) -> FollowupAuthorPromptAssemblyManifestActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
        stage=FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_PREPARED
        ),
    )
    record = build_followup_author_prompt_assembly_manifest_record(
        action_inputs=_mapping(action.inputs),
        followup_author_execution_activation_state=(
            followup_author_execution_activation_state
        ),
        followup_author_execution_activation_projection=(
            followup_author_execution_activation_projection
        ),
        followup_author_execution_activation_history=(
            followup_author_execution_activation_history
        ),
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
        observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_PREPARED
        ),
        status=RunStageStatus.COMPLETED,
        payload={
            "followup_author_prompt_assembly_manifest_state": record.to_dict()
        },
    )
    return FollowupAuthorPromptAssemblyManifestActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_prompt_assembly_manifest_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_execution_activation_projection: Mapping[str, Any],
    followup_author_execution_activation_history: Sequence[Mapping[str, Any]],
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
) -> FollowupAuthorPromptAssemblyManifestRecord:
    action = _mapping(action_inputs)
    y_state = _mapping(followup_author_execution_activation_state)
    y_projection = _mapping(followup_author_execution_activation_projection)
    y_history = [
        _mapping(item) for item in followup_author_execution_activation_history
    ]
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
    _validate_y_current(
        action=action,
        y_state=y_state,
        y_projection=y_projection,
        y_history=y_history,
    )
    _validate_x_current(
        action=action,
        y_state=y_state,
        x_state=x_state,
        x_projection=x_projection,
        x_history=x_history,
    )
    _validate_w_current(
        action=action,
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        w_projection=w_projection,
        w_history=w_history,
    )
    _validate_v1_current(
        action=action,
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        v1_projection=v1_projection,
        v1_history=v1_history,
    )
    _validate_u1_current(
        action=action,
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        u1_history=u1_history,
    )
    _validate_packet_authority(
        action=action,
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        u1_projection=u1_projection,
        packet=packet,
        authority=authority,
    )

    y_digest = followup_projection_digest(y_state)
    y_projection_digest = followup_projection_digest(y_projection)
    y_activation_ref = _mapping(y_state.get("author_execution_activation_ref"))
    y_activation_ref_digest = followup_projection_digest(y_activation_ref)
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
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    author_input_refs_digest = followup_projection_digest(author_input_refs)
    payload_ref_digest = followup_projection_digest(author_payload_ref)
    prompt_material = _prompt_material(
        manifest_id=action.get("author_prompt_assembly_manifest_id"),
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
        packet=packet,
        authority=authority,
    )
    ref_id = (
        "author-prompt-assembly-manifest-ref:"
        f"{y_digest[:16]}:{packet_digest[:16]}"
    )
    manifest_ref = {
        "prompt_assembly_manifest_ref_id": ref_id,
        "status": FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS,
        "y_author_execution_activation_id": y_state.get(
            "author_execution_activation_id"
        ),
        "y_author_execution_activation_digest": y_digest,
        "y_author_execution_activation_ref_id": y_activation_ref.get(
            "activation_ref_id"
        ),
        "y_author_execution_activation_ref_digest": y_activation_ref_digest,
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
        "prompt_text_digest": prompt_material["prompt_text_digest"],
        "prompt_text_length": prompt_material["prompt_text_length"],
        "authority_block_text_digest": prompt_material[
            "authority_block_text_digest"
        ],
        "authority_block_text_length": prompt_material[
            "authority_block_text_length"
        ],
        "prompt_section_ids": prompt_material["prompt_section_ids"],
        "prompt_section_digests": prompt_material["prompt_section_digests"],
        "transient_prompt_text_constructed": True,
        "transient_authority_block_text_constructed": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_answer_author_input_payload_created": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_included": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "model_called": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }
    manifest_digest = followup_projection_digest(manifest_ref)
    packet_mutation = _manifest_mutation(
        manifest_ref=manifest_ref,
        manifest_digest=manifest_digest,
    )
    state = {
        "schema_version": FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_TRACE_KEY,
        "record_type": "followup_author_prompt_assembly_manifest_record",
        "owner": "FollowupAuthorPromptAssemblyManifestRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "status": FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
        "author_prompt_assembly_manifest_id": action.get(
            "author_prompt_assembly_manifest_id"
        ),
        "author_prompt_assembly_manifest_mode": (
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
        ),
        "author_prompt_assembly_manifest_stage": (
            FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE
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
        "y_author_execution_activation_id": y_state.get(
            "author_execution_activation_id"
        ),
        "y_author_execution_activation_status": y_state.get("status"),
        "y_author_execution_activation_mode": (
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
        ),
        "y_author_execution_activation_digest": y_digest,
        "y_author_execution_activation_projection_digest": y_projection_digest,
        "y_author_execution_activation_ref_id": y_activation_ref.get(
            "activation_ref_id"
        ),
        "y_author_execution_activation_ref_digest": y_activation_ref_digest,
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
        "author_prompt_assembly_manifest_ref": safe_json(manifest_ref),
        "prompt_assembly_manifest_ref_id": ref_id,
        "author_prompt_assembly_manifest_digest": manifest_digest,
        "prompt_text_digest": prompt_material["prompt_text_digest"],
        "prompt_text_length": prompt_material["prompt_text_length"],
        "authority_block_text_digest": prompt_material[
            "authority_block_text_digest"
        ],
        "authority_block_text_length": prompt_material[
            "authority_block_text_length"
        ],
        "prompt_section_ids": prompt_material["prompt_section_ids"],
        "prompt_section_digests": prompt_material["prompt_section_digests"],
        "y_author_execution_activation_consumed": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "prompt_assembly_manifest_prepared": True,
        "transient_prompt_text_constructed": True,
        "transient_authority_block_text_constructed": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_answer_author_input_payload_created": False,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
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
        "behavior_boundary_flags": manifest_boundary_flags(),
        "redaction_posture": _redaction_posture(),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorPromptAssemblyManifestRecord(state=safe_json(state))


def build_run_kernel_followup_author_prompt_assembly_manifest_state(
    *,
    manifest_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **_mapping(manifest_record_state),
        "owner": "RunKernel.FollowupAuthorPromptAssemblyManifest",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_prompt_assembly_manifest_state(
        manifest_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_prompt_assembly_manifest_state(
    *,
    manifest_state: Mapping[str, Any],
) -> None:
    state = _mapping(manifest_state)
    flags = _mapping(state.get("behavior_boundary_flags"))
    if state.get("owner") != "RunKernel.FollowupAuthorPromptAssemblyManifest":
        raise PermissionError("Z prompt manifest requires RunKernel owner")
    if state.get("canonical_state") is not True:
        raise PermissionError("Z prompt manifest requires canonical state")
    if state.get("trace_only") is not False or state.get("storage_only") is not False:
        raise PermissionError("Z prompt manifest requires active canonical state")
    if state.get("status") != FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS:
        raise PermissionError("Z prompt manifest status mismatch")
    if state.get("author_prompt_assembly_manifest_mode") != (
        AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
    ):
        raise PermissionError("Z prompt manifest mode mismatch")
    for field in _TRUE_FIELDS:
        if state.get(field) is not True:
            raise PermissionError(f"Z prompt manifest requires {field}=True")
    for field in _FALSE_FIELDS:
        if state.get(field) is not False:
            raise PermissionError(f"Z prompt manifest requires {field}=False")
    if state.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z prompt manifest requires deferred payload")
    if state.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Z prompt manifest must not make payload executable")
    for field, expected in manifest_boundary_flags().items():
        if flags.get(field) is not expected:
            raise PermissionError(
                f"Z prompt manifest boundary requires {field}={expected}"
            )
    _reject_forbidden_payload(state)


def build_followup_author_prompt_assembly_manifest_projection(
    *,
    manifest_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_execution_activation_stage: str,
    followup_author_input_materialization_stage: str,
    followup_author_execution_readiness_stage: str,
    followup_author_gate_stage: str,
    followup_author_input_authority_stage: str,
) -> dict[str, Any]:
    state = _mapping(manifest_state)
    return {
        "owner": "RunKernel.FollowupAuthorPromptAssemblyManifest",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": state.get("schema_version"),
        "status": state.get("status"),
        "author_prompt_assembly_manifest_id": state.get(
            "author_prompt_assembly_manifest_id"
        ),
        "author_prompt_assembly_manifest_mode": state.get(
            "author_prompt_assembly_manifest_mode"
        ),
        "author_prompt_assembly_manifest_stage": state.get(
            "author_prompt_assembly_manifest_stage"
        ),
        "run_id": state.get("run_id"),
        "checkpoint_id": state.get("checkpoint_id"),
        "packet_id": state.get("packet_id"),
        "y_author_execution_activation_id": state.get(
            "y_author_execution_activation_id"
        ),
        "y_author_execution_activation_status": state.get(
            "y_author_execution_activation_status"
        ),
        "y_author_execution_activation_mode": state.get(
            "y_author_execution_activation_mode"
        ),
        "y_author_execution_activation_digest": state.get(
            "y_author_execution_activation_digest"
        ),
        "y_author_execution_activation_projection_digest": state.get(
            "y_author_execution_activation_projection_digest"
        ),
        "y_author_execution_activation_ref_id": state.get(
            "y_author_execution_activation_ref_id"
        ),
        "y_author_execution_activation_ref_digest": state.get(
            "y_author_execution_activation_ref_digest"
        ),
        "x_author_input_materialization_id": state.get(
            "x_author_input_materialization_id"
        ),
        "x_author_input_materialization_status": state.get(
            "x_author_input_materialization_status"
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
        "author_prompt_assembly_manifest_ref": _mapping(
            state.get("author_prompt_assembly_manifest_ref")
        ),
        "prompt_assembly_manifest_ref_id": state.get(
            "prompt_assembly_manifest_ref_id"
        ),
        "author_prompt_assembly_manifest_digest": state.get(
            "author_prompt_assembly_manifest_digest"
        ),
        "prompt_text_digest": state.get("prompt_text_digest"),
        "prompt_text_length": state.get("prompt_text_length"),
        "authority_block_text_digest": state.get("authority_block_text_digest"),
        "authority_block_text_length": state.get("authority_block_text_length"),
        "prompt_section_ids": list(state.get("prompt_section_ids", [])),
        "prompt_section_digests": _mapping(state.get("prompt_section_digests")),
        "y_author_execution_activation_consumed": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "prompt_assembly_manifest_prepared": True,
        "transient_prompt_text_constructed": True,
        "transient_authority_block_text_constructed": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_answer_author_input_payload_created": False,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
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
        "followup_author_execution_activation_ref": {
            "owner": "RunKernel.FollowupAuthorExecutionActivation",
            "canonical_state": True,
            "author_execution_activation_id": state.get(
                "y_author_execution_activation_id"
            ),
            "projection_stage": followup_author_execution_activation_stage,
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


def validate_followup_author_prompt_assembly_manifest_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_manifest_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_manifest_state)
    if not observed:
        raise PermissionError(
            "Z observation requires followup_author_prompt_assembly_manifest_state"
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
        "author_prompt_assembly_manifest_id",
        "author_prompt_assembly_manifest_mode",
        "status",
        "y_author_execution_activation_id",
        "y_author_execution_activation_digest",
        "y_author_execution_activation_projection_digest",
        "y_author_execution_activation_ref_id",
        "y_author_execution_activation_ref_digest",
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
        "prompt_text_digest",
        "prompt_text_length",
        "authority_block_text_digest",
        "authority_block_text_length",
    ):
        if observed.get(field) != action.get(field):
            raise PermissionError(f"Z observation {field} does not match action")
    if list(observed.get("prompt_section_ids", [])) != list(
        action.get("prompt_section_ids", [])
    ):
        raise PermissionError("Z observation prompt_section_ids do not match action")
    if _mapping(observed.get("prompt_section_digests")) != _mapping(
        action.get("prompt_section_digests")
    ):
        raise PermissionError(
            "Z observation prompt_section_digests do not match action"
        )
    if observed.get("status") != FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS:
        raise PermissionError("Z observation status mismatch")
    for field in _TRUE_FIELDS:
        if observed.get(field) is not True:
            raise PermissionError(f"Z observation requires {field}=True")
    for field in _FALSE_FIELDS:
        if observed.get(field) is not False:
            raise PermissionError(f"Z observation requires {field}=False")
    if observed.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Z observation must not make payload executable")
    _reject_forbidden_payload(observed)


def z_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    packet = _mapping(current_packet)
    record = _mapping(record_state)
    mutation = _mapping(record.get("packet_mutation"))
    _validate_exact_mutation_keys(mutation, Z_PACKET_MUTATION_FIELDS, "packet")
    _validate_packet_pre_mutation(packet, record)
    updated = _updated_with_mutation(packet, mutation)
    _validate_packet_post_mutation(packet, updated, record)
    return safe_json(updated)


def z_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    projection = _mapping(current_projection)
    record = _mapping(record_state)
    mutation = _mapping(record.get("final_answer_authority_projection_mutation"))
    _validate_exact_mutation_keys(
        mutation,
        Z_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection",
    )
    _validate_authority_pre_mutation(projection, record)
    updated = _updated_with_mutation(projection, mutation)
    _validate_authority_post_mutation(projection, updated, record)
    return safe_json(updated)


def manifest_boundary_flags() -> dict[str, bool]:
    flags = {
        **followup_closed_surface_boundary_flags(),
        "canonical_final_answer_packet_mutated": True,
        "final_answer_packet_updated": True,
        "final_answer_packet_rebuilt": False,
        "final_answer_authority_projection_mutated": True,
        "y_author_execution_activation_consumed": True,
        "x_author_input_materialization_consumed": True,
        "w_author_execution_readiness_consumed": True,
        "v1_author_gate_consumed": True,
        "u1_authority_consumed": True,
        "packet_authority_consumed": True,
        "prompt_assembly_manifest_prepared": True,
        "transient_prompt_text_constructed": True,
        "transient_authority_block_text_constructed": True,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_answer_author_input_payload_created": False,
        "author_payload_ref_status_changed": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
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
    flags["author_payload_created"] = False
    return flags


def _validate_action(action: Mapping[str, Any]) -> None:
    if action.get("author_prompt_assembly_manifest_mode") != (
        AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
    ):
        raise PermissionError("Z action requires AG-96I3Z prompt manifest mode")
    if action.get("status") not in (
        None,
        FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
    ):
        raise PermissionError("Z action status mismatch")
    if action.get("author_payload_ref_status") == "author_input_ready":
        raise PermissionError("Z action must not use executable payload status")
    if action.get("author_payload_ref_status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z action requires deferred author_payload_ref")
    for field in _TRUE_FIELDS:
        if action.get(field) is not True:
            raise PermissionError(f"Z action requires {field}=True")
    for field in _FALSE_FIELDS:
        if action.get(field) is not False:
            raise PermissionError(f"Z action requires {field}=False")
    _reject_forbidden_payload(action)


def _validate_y_current(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    y_projection: Mapping[str, Any],
    y_history: Sequence[Mapping[str, Any]],
) -> None:
    if not y_state:
        raise PermissionError("Z requires Y activation state")
    validate_run_kernel_followup_author_execution_activation_state(
        activation_state=y_state
    )
    if y_state.get("owner") != "RunKernel.FollowupAuthorExecutionActivation":
        raise PermissionError("Z requires RunKernel Y activation state")
    if y_state.get("author_execution_activation_mode") != (
        AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE
    ):
        raise PermissionError("Z requires AG-96I3Y activation mode")
    if y_state.get("status") != FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STATUS:
        raise PermissionError("Z requires Y activation status")
    if y_projection.get("owner") != "RunKernel.FollowupAuthorExecutionActivation":
        raise PermissionError("Z requires RunKernel Y activation projection")
    if y_projection.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical Y activation projection")
    if not y_history:
        raise PermissionError("Z requires Y activation history")
    if _mapping(y_history[-1]) != y_projection:
        raise PermissionError("Z requires current Y activation history")
    y_ref = _mapping(y_state.get("author_execution_activation_ref"))
    if not y_ref:
        raise PermissionError("Z requires Y activation ref")
    if y_ref.get("status") != FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS:
        raise PermissionError("Z requires non-executable Y activation ref")
    if y_ref.get("author_execution_allowed") is not False:
        raise PermissionError("Z requires Y activation execution closed")
    if y_state.get("author_input_ready") is not False:
        raise PermissionError("Z requires Y author_input_ready=false")
    if y_state.get("author_execution_allowed") is not False:
        raise PermissionError("Z requires Y execution closed")
    if y_state.get("author_activation_allowed") is not False:
        raise PermissionError("Z requires Y activation closed")
    if y_state.get("author_execution_deferred") is not True:
        raise PermissionError("Z requires Y execution deferred")
    if action.get("y_author_execution_activation_id") != y_state.get(
        "author_execution_activation_id"
    ):
        raise PermissionError("Z Y activation id mismatch")
    if action.get("y_author_execution_activation_digest") != (
        followup_projection_digest(y_state)
    ):
        raise PermissionError("Z stale Y digest")
    if action.get("y_author_execution_activation_projection_digest") != (
        followup_projection_digest(y_projection)
    ):
        raise PermissionError("Z stale Y projection digest")
    if action.get("y_author_execution_activation_ref_id") != y_ref.get(
        "activation_ref_id"
    ):
        raise PermissionError("Z Y activation ref id mismatch")
    if action.get("y_author_execution_activation_ref_digest") != (
        followup_projection_digest(y_ref)
    ):
        raise PermissionError("Z stale Y activation ref digest")


def _validate_x_current(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    x_projection: Mapping[str, Any],
    x_history: Sequence[Mapping[str, Any]],
) -> None:
    if x_state.get("owner") != "RunKernel.FollowupAuthorInputMaterialization":
        raise PermissionError("Z requires RunKernel X materialization state")
    if x_state.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical X materialization state")
    if x_state.get("trace_only") is not False or x_state.get("storage_only") is not False:
        raise PermissionError("Z requires active X materialization state")
    if x_state.get("author_input_materialization_mode") != (
        AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE
    ):
        raise PermissionError("Z requires AG-96I3X materialization mode")
    if x_state.get("status") != FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS:
        raise PermissionError("Z requires X materialization status")
    if x_projection.get("owner") != "RunKernel.FollowupAuthorInputMaterialization":
        raise PermissionError("Z requires RunKernel X materialization projection")
    if x_projection.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical X materialization projection")
    if not x_history:
        raise PermissionError("Z requires X materialization history")
    if _mapping(x_history[-1]) != x_projection:
        raise PermissionError("Z requires current X materialization history")
    if y_state.get("x_author_input_materialization_id") != x_state.get(
        "author_input_materialization_id"
    ):
        raise PermissionError("Z Y/X materialization id mismatch")
    if y_state.get("x_author_input_materialization_digest") != (
        followup_projection_digest(x_state)
    ):
        raise PermissionError("Z stale Y X digest")
    if y_state.get("x_author_input_materialization_projection_digest") != (
        followup_projection_digest(x_projection)
    ):
        raise PermissionError("Z stale Y X projection digest")
    if action.get("x_author_input_materialization_id") != x_state.get(
        "author_input_materialization_id"
    ):
        raise PermissionError("Z X materialization id mismatch")
    if action.get("x_author_input_materialization_digest") != (
        followup_projection_digest(x_state)
    ):
        raise PermissionError("Z stale X digest")


def _validate_w_current(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    w_projection: Mapping[str, Any],
    w_history: Sequence[Mapping[str, Any]],
) -> None:
    if w_state.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("Z requires RunKernel W readiness state")
    if w_state.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical W readiness state")
    if w_state.get("author_execution_readiness_mode") != (
        AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
    ):
        raise PermissionError("Z requires AG-96I3W readiness mode")
    if w_state.get("status") != FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS:
        raise PermissionError("Z requires W readiness status")
    if w_projection.get("owner") != "RunKernel.FollowupAuthorExecutionReadiness":
        raise PermissionError("Z requires RunKernel W readiness projection")
    if w_projection.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical W readiness projection")
    if not w_history:
        raise PermissionError("Z requires W readiness history")
    if _mapping(w_history[-1]) != w_projection:
        raise PermissionError("Z requires current W readiness history")
    if y_state.get("w_author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("Z Y/W readiness id mismatch")
    if y_state.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("Z stale Y W digest")
    if x_state.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("Z stale X W digest")
    if action.get("w_author_execution_readiness_id") != w_state.get(
        "author_execution_readiness_id"
    ):
        raise PermissionError("Z W readiness id mismatch")
    if action.get("w_author_execution_readiness_digest") != (
        followup_projection_digest(w_state)
    ):
        raise PermissionError("Z stale W digest")


def _validate_v1_current(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    v1_projection: Mapping[str, Any],
    v1_history: Sequence[Mapping[str, Any]],
) -> None:
    if v1_state.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("Z requires RunKernel V1 Author gate state")
    if v1_state.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical V1 Author gate state")
    if v1_state.get("author_gate_mode") != AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE:
        raise PermissionError("Z requires AG-96I3V1 Author gate mode")
    if v1_projection.get("owner") != "RunKernel.FollowupAuthorGate":
        raise PermissionError("Z requires RunKernel V1 Author gate projection")
    if v1_projection.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical V1 Author gate projection")
    if not v1_history:
        raise PermissionError("Z requires V1 Author gate history")
    if _mapping(v1_history[-1]) != v1_projection:
        raise PermissionError("Z requires current V1 Author gate history")
    if y_state.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("Z stale Y V1 digest")
    if x_state.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("Z stale X V1 digest")
    if w_state.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("Z stale W V1 digest")
    if action.get("v1_author_gate_id") != v1_state.get("author_gate_id"):
        raise PermissionError("Z V1 Author gate id mismatch")
    if action.get("v1_author_gate_digest") != followup_projection_digest(v1_state):
        raise PermissionError("Z stale V1 digest")


def _validate_u1_current(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    u1_history: Sequence[Mapping[str, Any]],
) -> None:
    if u1_state.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("Z requires RunKernel U1 authority state")
    if u1_state.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical U1 authority state")
    if u1_state.get("author_input_authority_mode") != (
        AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    ):
        raise PermissionError("Z requires AG-96I3U1 authority mode")
    if u1_projection.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("Z requires RunKernel U1 authority projection")
    if u1_projection.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical U1 authority projection")
    if not u1_history:
        raise PermissionError("Z requires U1 authority history")
    if _mapping(u1_history[-1]) != u1_projection:
        raise PermissionError("Z requires current U1 authority history")
    if v1_state.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("Z V1/U1 authority id mismatch")
    if y_state.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("Z stale Y U1 digest")
    if x_state.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("Z stale X U1 digest")
    if w_state.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("Z stale W U1 digest")
    if action.get("u1_authority_id") != u1_state.get("author_input_authority_id"):
        raise PermissionError("Z U1 authority id mismatch")
    if action.get("u1_authority_digest") != followup_projection_digest(u1_state):
        raise PermissionError("Z stale U1 digest")


def _validate_packet_authority(
    *,
    action: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> None:
    if packet.get("owner") != "RunKernel.FinalAnswerPacket":
        raise PermissionError("Z requires RunKernel FinalAnswerPacket")
    if packet.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical FinalAnswerPacket")
    if packet.get("readiness_status") != "blocked":
        raise PermissionError("Z requires blocked FinalAnswerPacket")
    if packet.get("final_answer_allowed") is not False:
        raise PermissionError("Z requires final_answer_allowed=false")
    if packet.get("answer_ready") is not False:
        raise PermissionError("Z requires answer_ready=false")
    if packet.get("product_answer_ready") is not False:
        raise PermissionError("Z requires product_answer_ready=false")
    if not authority:
        raise PermissionError("Z requires final_answer_authority_projection")
    if authority.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
        raise PermissionError("Z requires U1-owned final-answer authority")
    if authority.get("canonical_state") is not True:
        raise PermissionError("Z requires canonical final-answer authority")
    for existing in Z_PACKET_MUTATION_FIELDS:
        if existing.startswith("author_prompt_assembly_manifest") and packet.get(
            existing
        ) not in (None, False, [], {}, (), ""):
            raise PermissionError("Z requires no existing packet prompt manifest")
    for existing in Z_AUTHORITY_PROJECTION_MUTATION_FIELDS:
        if existing.startswith("author_prompt_assembly_manifest") and authority.get(
            existing
        ) not in (None, False, [], {}, (), ""):
            raise PermissionError("Z requires no existing authority prompt manifest")
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    if author_input_refs.get("status") != FOLLOWUP_AUTHOR_INPUT_REFS_STATUS:
        raise PermissionError("Z requires U1 author_input_refs")
    if author_payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Z rejects executable author_payload_ref")
    if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z requires deferred author_payload_ref")
    if author_input_refs != _mapping(u1_state.get("author_input_refs")):
        raise PermissionError("Z packet author_input_refs mismatch")
    if author_payload_ref != _mapping(u1_state.get("author_payload_ref")):
        raise PermissionError("Z packet author_payload_ref mismatch")
    if author_payload_ref != _mapping(u1_projection.get("author_payload_ref")):
        raise PermissionError("Z U1 projection author_payload_ref mismatch")
    if author_input_refs.get("author_input_authority_id") != u1_state.get(
        "author_input_authority_id"
    ):
        raise PermissionError("Z author_input_refs authority id mismatch")
    if author_input_refs.get("author_payload_ref_id") != (
        author_payload_ref.get("payload_ref_id")
    ):
        raise PermissionError("Z author_input_refs payload ref mismatch")
    if author_input_refs.get("final_answer_authority_projection_digest") != (
        followup_projection_digest(u1_projection)
    ):
        raise PermissionError("Z U1 author_input_refs authority digest mismatch")
    for binding, label in ((v1_state, "V1"), (w_state, "W"), (x_state, "X")):
        if binding.get("author_input_refs_digest") != (
            followup_projection_digest(author_input_refs)
        ):
            raise PermissionError(f"Z stale {label} author_input_refs digest")
        if binding.get("author_payload_ref_id") != author_payload_ref.get(
            "payload_ref_id"
        ):
            raise PermissionError(f"Z {label} author_payload_ref id mismatch")
        if binding.get("author_payload_ref_status") != author_payload_ref.get(
            "status"
        ):
            raise PermissionError(f"Z {label} author_payload_ref status mismatch")
    if y_state.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("Z stale Y author_input_refs digest")
    if y_state.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("Z Y author_payload_ref id mismatch")
    if y_state.get("author_payload_ref_status") != author_payload_ref.get("status"):
        raise PermissionError("Z Y author_payload_ref status mismatch")
    if packet.get("author_execution_activation_ref") != _mapping(
        y_state.get("author_execution_activation_ref")
    ):
        raise PermissionError("Z packet Y activation ref mismatch")
    if authority.get("author_execution_activation_ref") != _mapping(
        y_state.get("author_execution_activation_ref")
    ):
        raise PermissionError("Z authority Y activation ref mismatch")
    if packet.get("author_execution_activation_digest") != y_state.get(
        "author_execution_activation_digest"
    ):
        raise PermissionError("Z packet Y activation digest mismatch")
    if authority.get("author_execution_activation_digest") != y_state.get(
        "author_execution_activation_digest"
    ):
        raise PermissionError("Z authority Y activation digest mismatch")
    packet_digest = followup_projection_digest(packet)
    authority_digest = followup_projection_digest(authority)
    if y_state.get("updated_final_answer_packet_digest") != packet_digest:
        raise PermissionError("Z stale Y current FinalAnswerPacket digest")
    if y_state.get("updated_final_answer_authority_projection_digest") != (
        authority_digest
    ):
        raise PermissionError(
            "Z stale Y final_answer_authority_projection digest"
        )
    if action.get("current_final_answer_packet_digest") != packet_digest:
        raise PermissionError("Z current FinalAnswerPacket digest mismatch")
    if action.get("final_answer_authority_projection_digest") != authority_digest:
        raise PermissionError(
            "Z final_answer_authority_projection digest mismatch"
        )
    if action.get("author_input_refs_digest") != (
        followup_projection_digest(author_input_refs)
    ):
        raise PermissionError("Z author_input_refs digest mismatch")
    if action.get("author_payload_ref_id") != author_payload_ref.get(
        "payload_ref_id"
    ):
        raise PermissionError("Z author_payload_ref id mismatch")
    if action.get("author_payload_ref_status") != author_payload_ref.get("status"):
        raise PermissionError("Z author_payload_ref status mismatch")


def _validate_packet_pre_mutation(
    packet: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    if followup_projection_digest(packet) != record.get(
        "current_final_answer_packet_digest"
    ):
        raise PermissionError("Z packet mutation requires current packet digest")
    payload_ref = _mapping(packet.get("author_payload_ref"))
    if payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Z packet mutation rejects executable payload")
    if payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z packet mutation requires deferred payload")


def _validate_packet_post_mutation(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    _validate_changed_keys(before, updated, Z_PACKET_MUTATION_FIELDS, "packet")
    before_payload = _mapping(before.get("author_payload_ref"))
    updated_payload = _mapping(updated.get("author_payload_ref"))
    if updated_payload != before_payload:
        raise PermissionError("Z must not change packet author_payload_ref")
    if updated_payload.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z must keep packet author_payload_ref deferred")
    if updated_payload.get("status") == "author_input_ready":
        raise PermissionError("Z must not make packet payload executable")
    if updated.get("readiness_status") != "blocked":
        raise PermissionError("Z must keep packet blocked")
    if updated.get("final_answer_allowed") is not False:
        raise PermissionError("Z must keep final_answer_allowed=false")
    if updated.get("answer_ready") is not False:
        raise PermissionError("Z must keep answer_ready=false")
    if updated.get("product_answer_ready") is not False:
        raise PermissionError("Z must keep product_answer_ready=false")
    manifest_ref = _mapping(updated.get("author_prompt_assembly_manifest_ref"))
    if manifest_ref != _mapping(record.get("author_prompt_assembly_manifest_ref")):
        raise PermissionError("Z packet manifest ref mismatch")


def _validate_authority_pre_mutation(
    projection: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    if followup_projection_digest(projection) != record.get(
        "final_answer_authority_projection_digest"
    ):
        raise PermissionError(
            "Z authority mutation requires current projection digest"
        )
    payload_ref = _mapping(projection.get("author_payload_ref"))
    if payload_ref.get("status") == "author_input_ready":
        raise PermissionError("Z authority mutation rejects executable payload")
    if payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z authority mutation requires deferred payload")


def _validate_authority_post_mutation(
    before: Mapping[str, Any],
    updated: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    _validate_changed_keys(
        before,
        updated,
        Z_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection",
    )
    before_payload = _mapping(before.get("author_payload_ref"))
    updated_payload = _mapping(updated.get("author_payload_ref"))
    if updated_payload != before_payload:
        raise PermissionError("Z must not change authority author_payload_ref")
    if updated_payload.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
        raise PermissionError("Z must keep authority author_payload_ref deferred")
    manifest_ref = _mapping(updated.get("author_prompt_assembly_manifest_ref"))
    if manifest_ref != _mapping(record.get("author_prompt_assembly_manifest_ref")):
        raise PermissionError("Z authority manifest ref mismatch")


def _manifest_mutation(
    *,
    manifest_ref: Mapping[str, Any],
    manifest_digest: str,
) -> dict[str, Any]:
    return {
        "author_prompt_assembly_manifest_ref": safe_json(manifest_ref),
        "author_prompt_assembly_manifest_ref_created": True,
        "author_prompt_assembly_manifest_prepared": True,
        "author_prompt_assembly_manifest_status": (
            FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS
        ),
        "author_prompt_assembly_manifest_digest": manifest_digest,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "prompt_text_included": False,
        "prompt_text_retained": False,
        "authority_block_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
    }


def _prompt_material(
    *,
    manifest_id: Any,
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    author_input_refs = _mapping(packet.get("author_input_refs"))
    author_payload_ref = _mapping(packet.get("author_payload_ref"))
    section_digests = {
        "y_author_execution_activation": followup_projection_digest(y_state),
        "y_author_execution_activation_ref": followup_projection_digest(
            _mapping(y_state.get("author_execution_activation_ref"))
        ),
        "x_author_input_materialization": followup_projection_digest(x_state),
        "w_author_execution_readiness": followup_projection_digest(w_state),
        "v1_author_gate": followup_projection_digest(v1_state),
        "u1_authority": followup_projection_digest(u1_state),
        "final_answer_packet": followup_projection_digest(packet),
        "final_answer_authority_projection": followup_projection_digest(authority),
        "author_input_refs": followup_projection_digest(author_input_refs),
        "author_payload_ref": followup_projection_digest(author_payload_ref),
    }
    authority_block_text = _transient_authority_block_text(
        manifest_id=manifest_id,
        section_digests=section_digests,
        author_payload_ref_status=author_payload_ref.get("status"),
    )
    authority_block_digest = _text_digest(authority_block_text)
    section_digests["authority_block"] = authority_block_digest
    prompt_text = _transient_prompt_text(
        manifest_id=manifest_id,
        section_digests=section_digests,
        authority_block_digest=authority_block_digest,
        author_payload_ref_status=author_payload_ref.get("status"),
    )
    return {
        "prompt_text_digest": _text_digest(prompt_text),
        "prompt_text_length": len(prompt_text),
        "authority_block_text_digest": authority_block_digest,
        "authority_block_text_length": len(authority_block_text),
        "prompt_section_ids": list(section_digests),
        "prompt_section_digests": section_digests,
    }


def _transient_prompt_text(
    *,
    manifest_id: Any,
    section_digests: Mapping[str, Any],
    authority_block_digest: str,
    author_payload_ref_status: Any,
) -> str:
    lines = [
        "z_prompt_manifest",
        f"manifest_id:{manifest_id}",
        f"status:{FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS}",
        f"authority_block_digest:{authority_block_digest}",
        f"author_payload_ref_status:{author_payload_ref_status}",
        "execution_closed:true",
    ]
    for section_id, digest in section_digests.items():
        lines.append(f"{section_id}:{digest}")
    return "\n".join(lines)


def _transient_authority_block_text(
    *,
    manifest_id: Any,
    section_digests: Mapping[str, Any],
    author_payload_ref_status: Any,
) -> str:
    lines = [
        "z_authority_block_manifest",
        f"manifest_id:{manifest_id}",
        f"author_payload_ref_status:{author_payload_ref_status}",
        "author_input_ready:false",
        "author_execution_allowed:false",
    ]
    for section_id in (
        "y_author_execution_activation",
        "x_author_input_materialization",
        "w_author_execution_readiness",
        "v1_author_gate",
        "u1_authority",
        "final_answer_packet",
        "final_answer_authority_projection",
        "author_input_refs",
        "author_payload_ref",
    ):
        lines.append(f"{section_id}:{section_digests.get(section_id)}")
    return "\n".join(lines)


def _manifest_id(y_state: Mapping[str, Any]) -> str:
    y_id = y_state.get("author_execution_activation_id")
    y_digest = followup_projection_digest(y_state)
    return f"followup-author-prompt-assembly-manifest:{y_id}:{y_digest[:16]}"


def _validate_exact_mutation_keys(
    mutation: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    if set(mutation) != set(allowed):
        raise PermissionError(f"Z {context} mutation keys mismatch")


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
        raise PermissionError(f"Z {context} mutation changed unlicensed fields")


def _updated_with_mutation(
    value: Mapping[str, Any],
    mutation: Mapping[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(_mapping(value))
    updated.update(_mapping(mutation))
    return updated


def _text_digest(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _redaction_posture() -> dict[str, bool]:
    posture = followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )
    posture["prompt_text_retained"] = False
    posture["authority_block_text_retained"] = False
    posture["prompt_text_included"] = False
    posture["final_text_included"] = False
    return posture


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").casefold()
            if token in set(_FALSE_FIELDS) | _OPTIONAL_FALSE_FIELDS:
                if item is not False:
                    raise PermissionError(f"Z {token} must be false")
                continue
            if token in set(_TRUE_FIELDS) | {"not_role_consumption_payload"}:
                if item is not True:
                    raise PermissionError(f"Z {token} must be true")
                continue
            if token == "status" and item == "author_input_ready":
                raise PermissionError("Z prompt manifest must not be executable")
            if token == "author_payload_ref_status" and item == "author_input_ready":
                raise PermissionError("Z prompt manifest must not be executable")
            if _closed_text_key(token):
                if item in (None, False, [], {}, (), ""):
                    continue
                raise PermissionError(
                    f"Z prompt manifest includes closed field {key!r}"
                )
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
            "source snippet",
            "model response",
            "sk-",
        ):
            if marker in lowered:
                raise PermissionError(
                    "Z prompt manifest includes private or retained text marker"
                )
        if lowered == "author_input_ready":
            raise PermissionError("Z prompt manifest must not be executable")


def _closed_text_key(token: str) -> bool:
    if token in _PROMPT_METADATA_KEYS or token in _AUTHORITY_BLOCK_METADATA_KEYS:
        return False
    if "prompt" in token and not _safe_prompt_metadata_key(token):
        return True
    if "authority_block_text" in token and token not in _AUTHORITY_BLOCK_METADATA_KEYS:
        return True
    return any(part in token for part in _CLOSED_KEY_PARTS)


def _safe_prompt_metadata_key(token: str) -> bool:
    if token in _PROMPT_METADATA_KEYS:
        return True
    return (
        token.startswith("y_bound_prompt_assembly_manifest")
        or token.startswith("ag96i3z_y_bound_prompt_assembly_manifest")
        or token.startswith("followup_author_prompt_assembly_manifest")
        or token.startswith("author_prompt_assembly_manifest")
        or token.startswith("prompt_assembly_manifest")
    )


def _mapping(value: Any) -> dict[str, Any]:
    safe = safe_json(value or {})
    return dict(safe) if isinstance(safe, Mapping) else {}


__all__ = [
    "AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REASON",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_TRACE_KEY",
    "FollowupAuthorPromptAssemblyManifestActionResult",
    "FollowupAuthorPromptAssemblyManifestRecord",
    "Z_AUTHORITY_PROJECTION_MUTATION_FIELDS",
    "Z_PACKET_MUTATION_FIELDS",
    "build_followup_author_prompt_assembly_manifest_action_inputs",
    "build_followup_author_prompt_assembly_manifest_projection",
    "build_followup_author_prompt_assembly_manifest_record",
    "build_run_kernel_followup_author_prompt_assembly_manifest_state",
    "execute_followup_author_prompt_assembly_manifest_action",
    "manifest_boundary_flags",
    "reject_followup_author_prompt_assembly_manifest_input_spoof",
    "validate_followup_author_prompt_assembly_manifest_observation_binding",
    "validate_run_kernel_followup_author_prompt_assembly_manifest_state",
    "z_authority_projection_from_record",
    "z_packet_projection_from_record",
]
