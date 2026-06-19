"""AG-96I3AD AC-consuming Author payload envelope construction.

This module constructs the first AG-96I3 Author payload envelope from the
canonical AC payload authority. The envelope is a non-executable machine-readable
input package for a future Author execution phase; it stores safe refs, section
digests, prompt digests/lengths, and closed-surface flags only.
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
from core.followup_author_payload_authority_runtime import (
    AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
    validate_run_kernel_followup_author_payload_authority_state,
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
    safe_mapping_sequence as _mappings,
)
from core.followup_author_payload_safety import (
    safe_string_sequence as _strings,
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
)
from core.followup_deliberation import safe_json
from core.followup_fixture_boundaries import (
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_SCHEMA_VERSION = (
    "followup_author_payload_construction_ag96i3ad_v1"
)
FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_TRACE_KEY = (
    "followup_author_payload_construction_runtime"
)
FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE = "followup_author_payload_construction"
AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE = (
    "ag96i3ad_ac_consuming_author_payload_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS = (
    "author_payload_constructed_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS = (
    "ac_bound_author_payload_constructed_execution_closed"
)
FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_REASON = (
    "ag96i3ad_ac_consuming_author_payload_execution_closed"
)

AD_PACKET_MUTATION_FIELDS = frozenset(
    {
        "ag96i3_author_payload_envelope_ref",
        "ag96i3_author_payload_envelope_ref_created",
        "ag96i3_author_payload_constructed",
        "ag96i3_author_payload_status",
        "ag96i3_author_payload_digest",
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_execution_deferred",
        "final_answer_author_input_payload_created",
        "author_model_called",
        "execute_author_action_called",
        "ask_model_called",
        "author_observation_created",
        "final_answer_outcome_created",
        "final_text_included",
        "product_answer_ready",
    }
)
AD_AUTHORITY_PROJECTION_MUTATION_FIELDS = AD_PACKET_MUTATION_FIELDS

_FALSE_FIELDS = (
    "final_answer_author_input_payload_created",
    "author_input_ready",
    "author_execution_allowed",
    "author_activation_allowed",
    "author_model_called",
    "execute_author_action_called",
    "ask_model_called",
    "author_observation_created",
    "final_answer_outcome_created",
    "product_answer_ready",
    "final_text_included",
    "model_called",
    "author_executor_invoked",
    "provider_execution_licensed",
    "prompt_text_retained",
    "authority_block_text_retained",
    "provider_payloads_retained",
    "prompts_retained",
    "model_responses_retained",
    "unsanitized_text_retained",
    "private_records_or_complete_traces_retained",
    "final_text_retained",
    "citation_strings_included",
    "ordered_product_source_output_created",
)
_TRUE_FIELDS = (
    "ac_payload_authority_consumed",
    "z_author_prompt_assembly_manifest_consumed",
    "y_author_execution_activation_consumed",
    "x_author_input_materialization_consumed",
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "payload_constructed",
    "future_author_execution_must_consume",
    "legacy_author_payload_ref_subordinated",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)
_ACTION_FORBIDDEN_KEYS = {
    "followup_author_payload_construction_state",
    "author_payload_construction_state",
    "payload_construction_state",
    "payload_envelope_state",
    "ag96i3_author_payload_envelope_ref",
    "author_payload_envelope_ref",
    "payload_sections",
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
    | set(AD_PACKET_MUTATION_FIELDS)
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
    "snippet",
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
    "final answer packet authority",
    "ordered_sources",
    "ordered product source",
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
        "final_answer_packet_digest",
        "current_final_answer_packet_digest",
        "updated_final_answer_packet_digest",
    }
)
_reject_forbidden_payload = partial(
    _reject_closed_surface_payload,
    false_fields=_FALSE_FIELDS,
    allowed_key_tokens=_CLOSED_KEY_ALLOWED_TOKENS,
    closed_key_parts=_CLOSED_KEY_PARTS,
    closed_string_parts=_CLOSED_STRING_PARTS,
    context_label="AD payload envelope",
    old_ready_status_policy="exact",
)
_validate_projection_update = partial(
    _shared_validate_projection_update,
    allowed_mutation_fields=AD_PACKET_MUTATION_FIELDS,
    phase_label="AD",
    ref_field="ag96i3_author_payload_envelope_ref",
    ref_label="payload envelope ref",
    author_payload_ref_status=FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
_PROJECTED_FIELDS = (
    "schema_version",
    "status",
    "payload_envelope_id",
    "payload_envelope_mode",
    "payload_envelope_stage",
    "payload_envelope_ref_id",
    "payload_envelope_ref_status",
    "run_id",
    "checkpoint_id",
    "packet_id",
    "ac_payload_authority_id",
    "ac_payload_authority_digest",
    "ac_payload_authority_projection_digest",
    "ac_payload_authority_ref_digest",
    "z_author_prompt_assembly_manifest_id",
    "z_author_prompt_assembly_manifest_digest",
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
    "legacy_author_payload_ref_id",
    "legacy_author_payload_ref_status",
    "legacy_author_payload_ref_digest",
    "ag96i3_author_payload_envelope_ref",
    "ag96i3_author_payload_digest",
    "payload_sections",
    "payload_section_ids",
    "payload_section_digests",
    "allowed_evidence_refs",
    "citation_eligibility_refs_or_digest",
    "rendered_source_entries_refs_or_digest",
    "mandatory_caveats_refs_or_digest",
    "prohibited_upgrades_refs_or_digest",
    "source_bound_unknowns_refs_or_digest",
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
_BOUNDARY_FLAG_TOKENS = "+canonical_final_answer_packet_mutated +final_answer_packet_updated +final_answer_authority_projection_mutated +ac_payload_authority_consumed +z_author_prompt_assembly_manifest_consumed +y_author_execution_activation_consumed +x_author_input_materialization_consumed +w_author_execution_readiness_consumed +v1_author_gate_consumed +u1_authority_consumed +packet_authority_consumed +payload_constructed +future_author_execution_must_consume +legacy_author_payload_ref_subordinated +author_payload_created -final_answer_author_input_payload_created -author_input_ready -author_execution_allowed -author_activation_allowed +author_execution_deferred -prompt_text_retained -authority_block_text_retained -citation_strings_included -ordered_product_source_output_created -final_text_included -product_answer_ready -model_called -author_model_called -execute_author_action_called -ask_model_called -author_observation_created -final_answer_outcome_created +live_validation_not_run +not_for_product_answer_activation".split()
_AC_STATE_RECORD_ONLY_FIELDS = frozenset(
    {
        "trace_key",
        "record_type",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "z_author_prompt_assembly_manifest_ref_status",
        "y_author_execution_activation_mode",
        "x_author_input_materialization_mode",
        "w_author_execution_readiness_mode",
        "v1_author_gate_mode",
        "u1_authority_mode",
        "packet_mutation",
        "final_answer_authority_projection_mutation",
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        "observation_id",
    }
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorPayloadConstructionActionResult:
    record: "FollowupAuthorPayloadConstructionRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorPayloadConstructionRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_payload_construction_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    reject_caller_controlled_inputs(inputs, caller_controlled_keys=_CALLER_CONTROLLED_KEYS, context_label="AD payload construction action", closed_surface_rejector=_reject_forbidden_payload)


def build_followup_author_payload_construction_action_inputs(
    *,
    followup_author_payload_authority_state: Mapping[str, Any],
    followup_author_payload_authority_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    ac_state = _mapping(followup_author_payload_authority_state)
    ac_projection = _mapping(followup_author_payload_authority_projection)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    author_input_refs = _mapping(packet.get("author_input_refs"))
    legacy_payload_ref = _mapping(packet.get("author_payload_ref"))
    ac_ref = _mapping(ac_state.get("ag96i3_author_payload_authority_ref"))
    return {
        "run_id": ac_state.get("run_id"),
        "checkpoint_id": ac_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": ac_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": ac_state.get("sealed_candidate_id"),
        "followup_execution_id": ac_state.get("followup_execution_id"),
        "execution_id": ac_state.get("execution_id"),
        "followup_evidence_intake_id": ac_state.get("followup_evidence_intake_id"),
        "intake_id": ac_state.get("intake_id"),
        "followup_sufficiency_recheck_id": ac_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": ac_state.get("recheck_id"),
        "packet_id": packet.get("packet_id"),
        "payload_envelope_id": _payload_envelope_id(ac_state),
        "payload_envelope_mode": AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
        "status": FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
        "ac_payload_authority_id": ac_state.get("payload_authority_id"),
        "ac_payload_authority_digest": _digest(ac_state),
        "ac_payload_authority_projection_digest": _digest(ac_projection),
        "ac_payload_authority_ref_digest": _digest(ac_ref),
        "z_author_prompt_assembly_manifest_id": ac_state.get(
            "z_author_prompt_assembly_manifest_id"
        ),
        "z_author_prompt_assembly_manifest_digest": ac_state.get(
            "z_author_prompt_assembly_manifest_digest"
        ),
        "z_author_prompt_assembly_manifest_ref_digest": ac_state.get(
            "z_author_prompt_assembly_manifest_ref_digest"
        ),
        "y_author_execution_activation_id": ac_state.get(
            "y_author_execution_activation_id"
        ),
        "y_author_execution_activation_digest": ac_state.get(
            "y_author_execution_activation_digest"
        ),
        "y_author_execution_activation_ref_digest": ac_state.get(
            "y_author_execution_activation_ref_digest"
        ),
        "x_author_input_materialization_id": ac_state.get(
            "x_author_input_materialization_id"
        ),
        "x_author_input_materialization_digest": ac_state.get(
            "x_author_input_materialization_digest"
        ),
        "w_author_execution_readiness_id": ac_state.get(
            "w_author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": ac_state.get(
            "w_author_execution_readiness_digest"
        ),
        "v1_author_gate_id": ac_state.get("v1_author_gate_id"),
        "v1_author_gate_digest": ac_state.get("v1_author_gate_digest"),
        "u1_authority_id": ac_state.get("u1_authority_id"),
        "u1_authority_digest": ac_state.get("u1_authority_digest"),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(author_input_refs),
        "legacy_author_payload_ref_id": legacy_payload_ref.get("payload_ref_id"),
        "legacy_author_payload_ref_status": legacy_payload_ref.get("status"),
        "prompt_text_digest": ac_state.get("prompt_text_digest"),
        "prompt_text_length": ac_state.get("prompt_text_length"),
        "authority_block_text_digest": ac_state.get("authority_block_text_digest"),
        "authority_block_text_length": ac_state.get("authority_block_text_length"),
        **{field: True for field in _TRUE_FIELDS},
        **{field: False for field in _FALSE_FIELDS},
    }


def execute_followup_author_payload_construction_action(
    action: Any,
    *,
    followup_author_payload_authority_state: Mapping[str, Any],
    followup_author_payload_authority_projection: Mapping[str, Any],
    followup_author_payload_authority_history: Sequence[Mapping[str, Any]],
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any],
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorPayloadConstructionActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
        stage=FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTED
        ),
    )
    record = build_followup_author_payload_construction_record(
        action_inputs=_mapping(action.inputs),
        followup_author_payload_authority_state=(
            followup_author_payload_authority_state
        ),
        followup_author_payload_authority_projection=(
            followup_author_payload_authority_projection
        ),
        followup_author_payload_authority_history=(
            followup_author_payload_authority_history
        ),
        followup_author_prompt_assembly_manifest_state=(
            followup_author_prompt_assembly_manifest_state
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
        observation_type=ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_payload_construction_state": record.to_dict()},
    )
    return FollowupAuthorPayloadConstructionActionResult(record, observation)


def build_followup_author_payload_construction_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_author_payload_authority_state: Mapping[str, Any],
    followup_author_payload_authority_projection: Mapping[str, Any],
    followup_author_payload_authority_history: Sequence[Mapping[str, Any]],
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any],
    followup_author_execution_activation_state: Mapping[str, Any],
    followup_author_input_materialization_state: Mapping[str, Any],
    followup_author_execution_readiness_state: Mapping[str, Any],
    followup_author_gate_state: Mapping[str, Any],
    followup_author_input_authority_state: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> FollowupAuthorPayloadConstructionRecord:
    action = _mapping(action_inputs)
    ac_state = _mapping(followup_author_payload_authority_state)
    ac_projection = _mapping(followup_author_payload_authority_projection)
    ac_history = [_mapping(item) for item in followup_author_payload_authority_history]
    z_state = _mapping(followup_author_prompt_assembly_manifest_state)
    y_state = _mapping(followup_author_execution_activation_state)
    x_state = _mapping(followup_author_input_materialization_state)
    w_state = _mapping(followup_author_execution_readiness_state)
    v1_state = _mapping(followup_author_gate_state)
    u1_state = _mapping(followup_author_input_authority_state)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)

    _validate_ac_current(ac_state, ac_projection, ac_history)
    _validate_ac_bindings(
        ac_state=ac_state,
        z_state=z_state,
        y_state=y_state,
        x_state=x_state,
        w_state=w_state,
        v1_state=v1_state,
        u1_state=u1_state,
    )
    _validate_packet_and_projection(action, ac_state, packet, authority, u1_state)
    expected_action = build_followup_author_payload_construction_action_inputs(
        followup_author_payload_authority_state=ac_state,
        followup_author_payload_authority_projection=ac_projection,
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
    )
    _require(action == expected_action, "AD action must match canonical AC inputs")

    author_input_refs = _mapping(packet.get("author_input_refs"))
    legacy_payload_ref = _mapping(packet.get("author_payload_ref"))
    ac_ref = _mapping(ac_state.get("ag96i3_author_payload_authority_ref"))
    x_bill_of_materials = _mapping(ac_state.get("x_bill_of_materials"))
    payload_sections = _payload_sections(
        ac_state=ac_state,
        ac_projection=ac_projection,
        u1_state=u1_state,
        x_state=x_state,
        packet=packet,
        authority=authority,
        author_input_refs=author_input_refs,
        legacy_payload_ref=legacy_payload_ref,
        x_bill_of_materials=x_bill_of_materials,
    )
    section_digests = {
        section_id: _digest(section)
        for section_id, section in payload_sections.items()
    }
    envelope_ref = {
        "payload_envelope_ref_id": (
            "ag96i3-author-payload-envelope-ref:"
            f"{ac_state.get('payload_authority_id')}:"
            f"{_digest(ac_state)[:16]}"
        ),
        "status": FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
        "payload_envelope_mode": AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
        "ac_payload_authority_id": ac_state.get("payload_authority_id"),
        "ac_payload_authority_digest": _digest(ac_state),
        "ac_payload_authority_ref_digest": _digest(ac_ref),
        "z_author_prompt_assembly_manifest_id": ac_state.get(
            "z_author_prompt_assembly_manifest_id"
        ),
        "x_author_input_materialization_id": ac_state.get(
            "x_author_input_materialization_id"
        ),
        "y_author_execution_activation_id": ac_state.get(
            "y_author_execution_activation_id"
        ),
        "packet_id": packet.get("packet_id"),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(author_input_refs),
        "legacy_author_payload_ref_id": legacy_payload_ref.get("payload_ref_id"),
        "legacy_author_payload_ref_status": legacy_payload_ref.get("status"),
        "payload_section_ids": list(payload_sections),
        "payload_section_digests": section_digests,
        "prompt_text_digest": ac_state.get("prompt_text_digest"),
        "prompt_text_length": ac_state.get("prompt_text_length"),
        "authority_block_text_digest": ac_state.get("authority_block_text_digest"),
        "authority_block_text_length": ac_state.get("authority_block_text_length"),
        "payload_constructed": True,
        "future_author_execution_must_consume": True,
        "legacy_author_payload_ref_subordinated": True,
        "final_answer_author_input_payload_created": False,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "author_model_called": False,
        "execute_author_action_called": False,
        "ask_model_called": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "product_answer_ready": False,
        "final_text_included": False,
        "live_validation_not_run": True,
    }
    envelope_digest = _digest(envelope_ref)
    mutation = _payload_envelope_mutation(envelope_ref, envelope_digest)
    allowed_evidence_refs = _mappings(u1_state.get("author_allowed_evidence_refs"))
    citation_refs = _mappings(u1_state.get("citation_eligibility_refs"))
    rendered_source_refs = _mappings(u1_state.get("author_rendered_source_entry_refs"))
    state = {
        **action,
        "schema_version": FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_TRACE_KEY,
        "record_type": "followup_author_payload_construction_record",
        "owner": "FollowupAuthorPayloadConstructionRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "payload_envelope_stage": FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE,
        "ac_payload_authority_mode": (
            AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE
        ),
        "ac_payload_authority_status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
        "ac_payload_authority_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "z_author_prompt_assembly_manifest_mode": (
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
        ),
        "z_author_prompt_assembly_manifest_ref_status": (
            FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS
        ),
        "y_author_execution_activation_mode": AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
        "y_author_execution_activation_ref_status": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS
        ),
        "y_old_ready_status_demoted": True,
        "y_author_input_ready": False,
        "activation_consumable_by_future_author_execution": True,
        "x_author_input_materialization_mode": AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
        "x_bill_of_materials": x_bill_of_materials,
        "w_author_execution_readiness_mode": AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
        "v1_author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
        "u1_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "final_answer_packet_digest": _digest(packet),
        "legacy_author_payload_ref_digest": _digest(legacy_payload_ref),
        "ag96i3_author_payload_envelope_ref": safe_json(envelope_ref),
        "ag96i3_author_payload_digest": envelope_digest,
        "payload_envelope_ref_id": envelope_ref["payload_envelope_ref_id"],
        "payload_envelope_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
        "payload_sections": safe_json(payload_sections),
        "payload_section_ids": list(payload_sections),
        "payload_section_digests": section_digests,
        "allowed_evidence_refs": safe_json(allowed_evidence_refs),
        "citation_eligibility_refs_or_digest": _refs_or_digest(citation_refs),
        "rendered_source_entries_refs_or_digest": _refs_or_digest(rendered_source_refs),
        "mandatory_caveats_refs_or_digest": _refs_or_digest(
            _strings(u1_state.get("author_mandatory_caveat_refs"))
        ),
        "prohibited_upgrades_refs_or_digest": _refs_or_digest(
            _strings(u1_state.get("author_prohibited_upgrade_refs"))
        ),
        "source_bound_unknowns_refs_or_digest": _refs_or_digest(
            _mappings(u1_state.get("source_bound_unknown_refs"))
        ),
        "prompt_section_ids": list(ac_state.get("prompt_section_ids", [])),
        "prompt_section_digests": _mapping(ac_state.get("prompt_section_digests")),
        "packet_mutation": safe_json(mutation),
        "final_answer_authority_projection_mutation": safe_json(mutation),
        "updated_final_answer_packet_digest": _digest(
            _updated_with_mutation(packet, mutation)
        ),
        "updated_final_answer_authority_projection_digest": _digest(
            _updated_with_mutation(authority, mutation)
        ),
        "behavior_boundary_flags": payload_construction_boundary_flags(),
        "redaction_posture": _redaction_posture(),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorPayloadConstructionRecord(safe_json(state))


def build_run_kernel_followup_author_payload_construction_state(
    *,
    payload_construction_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **_mapping(payload_construction_record_state),
        "owner": "RunKernel.FollowupAuthorPayloadConstruction",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_payload_construction_state(
        payload_construction_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_payload_construction_state(
    *,
    payload_construction_state: Mapping[str, Any],
) -> None:
    state = _mapping(payload_construction_state)
    _require(
        state.get("owner") == "RunKernel.FollowupAuthorPayloadConstruction",
        "AD payload construction requires RunKernel owner",
    )
    _require(state.get("canonical_state") is True, "AD requires canonical state")
    _require(state.get("trace_only") is False, "AD cannot be trace-only")
    _require(state.get("storage_only") is False, "AD cannot be storage-only")
    _require(
        state.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
        "AD payload construction status mismatch",
    )
    _require(
        state.get("payload_envelope_mode")
        == AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
        "AD payload construction mode mismatch",
    )
    _require(
        state.get("payload_envelope_ref_status")
        == FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
        "AD payload envelope ref status mismatch",
    )
    _require(
        state.get("legacy_author_payload_ref_status")
        == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "AD requires deferred legacy author_payload_ref",
    )
    _validate_closed_flags(state)
    _require(
        set(_mapping(state.get("packet_mutation"))) == set(AD_PACKET_MUTATION_FIELDS),
        "AD packet mutation keys mismatch",
    )
    _reject_forbidden_payload(state)


def build_followup_author_payload_construction_projection(
    *,
    payload_construction_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_payload_authority_stage: str,
) -> dict[str, Any]:
    state = _mapping(payload_construction_state)
    projection = {
        "owner": "RunKernel.FollowupAuthorPayloadConstruction",
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
        "followup_author_payload_authority_ref": {
            "owner": "RunKernel.FollowupAuthorPayloadAuthority",
            "canonical_state": True,
            "payload_authority_id": state.get("ac_payload_authority_id"),
            "projection_stage": followup_author_payload_authority_stage,
        },
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_payload_construction_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_payload_construction_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_payload_construction_state)
    _require(observed, "AD observation requires payload construction state")
    _validate_closed_flags(observed)
    for field, expected in action.items():
        _require(observed.get(field) == expected, f"AD observation {field} mismatch")
    _reject_forbidden_payload(observed)


def ad_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return _projection_from_record_mutation(
        current_packet, record_state, "packet", "packet_mutation", AD_PACKET_MUTATION_FIELDS, "current_final_answer_packet_digest", "AD mutation mismatch", "AD stale packet", _validate_projection_update
    )


def ad_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return _projection_from_record_mutation(
        current_projection, record_state, "authority", "final_answer_authority_projection_mutation", AD_AUTHORITY_PROJECTION_MUTATION_FIELDS, "final_answer_authority_projection_digest", "AD authority mutation mismatch", "AD stale authority projection", _validate_projection_update
    )


def payload_construction_boundary_flags() -> dict[str, bool]:
    return boundary_flags_from_tokens(_BOUNDARY_FLAG_TOKENS)


_validate_closed_flags = partial(
    _shared_validate_closed_flags,
    true_fields=_TRUE_FIELDS,
    false_fields=_FALSE_FIELDS,
    boundary_flags=payload_construction_boundary_flags,
    context_label="AD",
)


def _validate_ac_current(
    ac_state: Mapping[str, Any],
    ac_projection: Mapping[str, Any],
    ac_history: Sequence[Mapping[str, Any]],
) -> None:
    _require(ac_state, "AD requires AC payload authority state")
    validate_run_kernel_followup_author_payload_authority_state(
        payload_authority_state=ac_state
    )
    _require(
        ac_state.get("owner") == "RunKernel.FollowupAuthorPayloadAuthority",
        "AD requires RunKernel AC payload authority state",
    )
    _require(
        ac_state.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
        "AD requires execution-closed AC payload authority",
    )
    _require(
        ac_state.get("payload_authority_mode")
        == AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE,
        "AD requires AG-96I3AC payload authority mode",
    )
    _require(
        ac_projection.get("owner") == "RunKernel.FollowupAuthorPayloadAuthority",
        "AD requires RunKernel AC payload authority projection",
    )
    _require(ac_projection.get("canonical_state") is True, "AD requires canonical AC")
    _require(
        ac_history and _mapping(ac_history[-1]) == ac_projection,
        "AD requires current AC history",
    )
    unexpected_state_fields = set(ac_state) - set(ac_projection) - _AC_STATE_RECORD_ONLY_FIELDS
    _require(
        not unexpected_state_fields,
        "AD stale AC payload authority state has unprojected fields",
    )
    for key, projected_value in ac_projection.items():
        if key in ac_state:
            _require(
                safe_json(ac_state.get(key)) == projected_value,
                f"AD stale AC projection field {key}",
            )
    _require(
        ac_state.get("ag96i3_author_payload_authority_digest")
        == _digest(_mapping(ac_state.get("ag96i3_author_payload_authority_ref"))),
        "AD stale AC authority ref digest",
    )
    _require(
        ac_state.get("payload_authority_ref_status")
        == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "AD requires AC payload authority ref status",
    )
    _require(
        ac_state.get("future_author_execution_must_consume") is True,
        "AD requires AC future-execution consumption authority",
    )


def _validate_ac_bindings(
    *,
    ac_state: Mapping[str, Any],
    z_state: Mapping[str, Any],
    y_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    w_state: Mapping[str, Any],
    v1_state: Mapping[str, Any],
    u1_state: Mapping[str, Any],
) -> None:
    bindings = (
        (
            "z_author_prompt_assembly_manifest_id",
            z_state,
            "author_prompt_assembly_manifest_id",
            "z_author_prompt_assembly_manifest_digest",
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
            "author_prompt_assembly_manifest_mode",
        ),
        (
            "y_author_execution_activation_id",
            y_state,
            "author_execution_activation_id",
            "y_author_execution_activation_digest",
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
            "author_execution_activation_mode",
        ),
        (
            "x_author_input_materialization_id",
            x_state,
            "author_input_materialization_id",
            "x_author_input_materialization_digest",
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
            "author_input_materialization_mode",
        ),
        (
            "w_author_execution_readiness_id",
            w_state,
            "author_execution_readiness_id",
            "w_author_execution_readiness_digest",
            AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
            "author_execution_readiness_mode",
        ),
        (
            "v1_author_gate_id",
            v1_state,
            "author_gate_id",
            "v1_author_gate_digest",
            AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
            "author_gate_mode",
        ),
        (
            "u1_authority_id",
            u1_state,
            "author_input_authority_id",
            "u1_authority_digest",
            AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
            "author_input_authority_mode",
        ),
    )
    for ac_id, state, state_id, ac_digest, mode, mode_field in bindings:
        _require(ac_state.get(ac_id) == state.get(state_id), f"AD {ac_id} mismatch")
        _require(ac_state.get(ac_digest) == _digest(state), f"AD {ac_digest} stale")
        _require(state.get(mode_field) == mode, f"AD {mode_field} mismatch")
    _require(
        y_state.get("author_execution_activation_ref_status")
        == FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
        "AD requires Y demoted activation ref status",
    )
    _require(y_state.get("author_input_ready") is False, "AD requires Y demotion")
    _require(
        y_state.get("activation_consumable_by_future_author_execution") is True,
        "AD requires Y future execution consumability",
    )


def _validate_packet_and_projection(
    action: Mapping[str, Any],
    ac_state: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    u1_state: Mapping[str, Any],
) -> None:
    legacy_payload_ref, author_input_refs = validate_packet_projection_base(
        packet,
        authority,
        u1_state,
        "AD",
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AD packet/authority payload ref mismatch",
        "AD U1 payload ref mismatch",
    )
    ac_ref = _mapping(packet.get("ag96i3_author_payload_authority_ref"))
    authority_ac_ref = _mapping(authority.get("ag96i3_author_payload_authority_ref"))
    _require(
        ac_ref == _mapping(ac_state.get("ag96i3_author_payload_authority_ref")),
        "AD packet AC ref mismatch",
    )
    _require(
        authority_ac_ref == _mapping(ac_state.get("ag96i3_author_payload_authority_ref")),
        "AD authority AC ref mismatch",
    )
    _require(
        packet.get("ag96i3_author_payload_authority_digest")
        == ac_state.get("ag96i3_author_payload_authority_digest"),
        "AD packet AC digest mismatch",
    )
    _require(
        authority.get("ag96i3_author_payload_authority_digest")
        == ac_state.get("ag96i3_author_payload_authority_digest"),
        "AD authority AC digest mismatch",
    )
    validate_packet_authority_currentness(
        packet,
        authority,
        ac_state,
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        "AD stale packet from AC",
        "AD stale authority projection from AC",
    )
    validate_no_existing_prefixed_fields(
        packet,
        authority,
        AD_PACKET_MUTATION_FIELDS,
        "ag96i3_author_payload",
        "AD packet already has payload envelope",
        "AD authority already has payload envelope",
    )
    expected = build_followup_author_payload_construction_action_inputs(
        followup_author_payload_authority_state=ac_state,
        followup_author_payload_authority_projection={},
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
            "legacy_author_payload_ref_id",
            "legacy_author_payload_ref_status",
            "ac_payload_authority_digest",
        ),
        "AD",
    )


def _payload_sections(
    *,
    ac_state: Mapping[str, Any],
    ac_projection: Mapping[str, Any],
    u1_state: Mapping[str, Any],
    x_state: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    author_input_refs: Mapping[str, Any],
    legacy_payload_ref: Mapping[str, Any],
    x_bill_of_materials: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "ac_payload_authority": {
            "section_id": "ac_payload_authority",
            "payload_authority_id": ac_state.get("payload_authority_id"),
            "status": ac_state.get("payload_authority_ref_status"),
            "state_digest": _digest(ac_state),
            "projection_digest": _digest(ac_projection),
            "ref_digest": _digest(_mapping(ac_state.get("ag96i3_author_payload_authority_ref"))),
        },
        "x_bill_of_materials": {
            "section_id": "x_bill_of_materials",
            **_mapping(x_bill_of_materials),
        },
        "author_input_refs": {
            "section_id": "author_input_refs",
            "section_digest": _digest(author_input_refs),
            "refs": safe_json(author_input_refs),
        },
        "legacy_author_payload_ref": {
            "section_id": "legacy_author_payload_ref",
            "section_digest": _digest(legacy_payload_ref),
            "ref": safe_json(legacy_payload_ref),
            "subordinated": True,
        },
        "final_answer_packet_snapshot": {
            "section_id": "final_answer_packet_snapshot",
            "packet_id": packet.get("packet_id"),
            "section_digest": _digest(packet),
            "projection_digest": _digest(authority),
            "readiness_status": packet.get("readiness_status"),
            "final_answer_allowed": packet.get("final_answer_allowed"),
        },
        "allowed_evidence_refs": {
            "section_id": "allowed_evidence_refs",
            "refs": safe_json(_mappings(u1_state.get("author_allowed_evidence_refs"))),
        },
        "citation_eligibility_refs": {
            "section_id": "citation_eligibility_refs",
            "refs": safe_json(_mappings(u1_state.get("citation_eligibility_refs"))),
        },
        "rendered_source_entry_refs": {
            "section_id": "rendered_source_entry_refs",
            "refs": safe_json(_mappings(u1_state.get("author_rendered_source_entry_refs"))),
            "rendered_source_entry_digest": u1_state.get("rendered_source_entry_digest"),
            "source_identity_digest": u1_state.get("source_identity_digest"),
        },
        "mandatory_caveat_refs": {
            "section_id": "mandatory_caveat_refs",
            "refs": _strings(u1_state.get("author_mandatory_caveat_refs")),
        },
        "prohibited_upgrade_refs": {
            "section_id": "prohibited_upgrade_refs",
            "refs": _strings(u1_state.get("author_prohibited_upgrade_refs")),
        },
        "source_bound_unknown_refs": {
            "section_id": "source_bound_unknown_refs",
            "refs": safe_json(_mappings(u1_state.get("source_bound_unknown_refs"))),
        },
        "prompt_digest_manifest": {
            "section_id": "prompt_digest_manifest",
            "prompt_text_digest": ac_state.get("prompt_text_digest"),
            "prompt_text_length": ac_state.get("prompt_text_length"),
            "authority_block_text_digest": ac_state.get("authority_block_text_digest"),
            "authority_block_text_length": ac_state.get("authority_block_text_length"),
            "prompt_section_ids": list(ac_state.get("prompt_section_ids", [])),
            "prompt_section_digests": _mapping(ac_state.get("prompt_section_digests")),
        },
        "x_materialization_manifest": {
            "section_id": "x_materialization_manifest",
            "manifest_digest": _digest(_mapping(x_state.get("author_input_materialization_manifest"))),
            "section_ids": list(x_state.get("section_ids", [])),
            "section_digests": _mapping(x_state.get("section_digests")),
            "prompt_or_input_digest": x_state.get("prompt_or_input_digest"),
            "prompt_or_input_length": x_state.get("prompt_or_input_length"),
            "authority_block_digest": x_state.get("authority_block_digest"),
        },
    }


def _payload_envelope_mutation(
    payload_envelope_ref: Mapping[str, Any],
    payload_envelope_digest: str,
) -> dict[str, Any]:
    return {
        "ag96i3_author_payload_envelope_ref": safe_json(payload_envelope_ref),
        "ag96i3_author_payload_envelope_ref_created": True,
        "ag96i3_author_payload_constructed": True,
        "ag96i3_author_payload_status": FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
        "ag96i3_author_payload_digest": payload_envelope_digest,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "final_answer_author_input_payload_created": False,
        "author_model_called": False,
        "execute_author_action_called": False,
        "ask_model_called": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "final_text_included": False,
        "product_answer_ready": False,
    }


def _payload_envelope_id(ac_state: Mapping[str, Any]) -> str:
    return (
        "ag96i3-author-payload-envelope:"
        f"{ac_state.get('payload_authority_id')}:"
        f"{_digest(ac_state)[:16]}"
    )


def _refs_or_digest(value: Any) -> dict[str, Any]:
    refs = safe_json(value or [])
    return {
        "digest": _digest({"refs": refs}),
        "refs": refs,
        "ref_count": len(refs) if isinstance(refs, list) else 0,
    }


def _redaction_posture() -> dict[str, bool]:
    posture = followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )
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
    "AD_AUTHORITY_PROJECTION_MUTATION_FIELDS",
    "AD_PACKET_MUTATION_FIELDS",
    "AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_REASON",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_TRACE_KEY",
    "FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS",
    "FollowupAuthorPayloadConstructionActionResult",
    "FollowupAuthorPayloadConstructionRecord",
    "ad_authority_projection_from_record",
    "ad_packet_projection_from_record",
    "build_followup_author_payload_construction_action_inputs",
    "build_followup_author_payload_construction_projection",
    "build_followup_author_payload_construction_record",
    "build_run_kernel_followup_author_payload_construction_state",
    "execute_followup_author_payload_construction_action",
    "payload_construction_boundary_flags",
    "reject_followup_author_payload_construction_input_spoof",
    "validate_followup_author_payload_construction_observation_binding",
    "validate_run_kernel_followup_author_payload_construction_state",
]
