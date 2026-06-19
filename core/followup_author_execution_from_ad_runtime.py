"""AG-96I3AE AD-consuming fake Author execution.

This module crosses the AG-96I3 Author execution boundary without using the
legacy AuthorExecutor or a real model. It consumes the canonical AD payload
envelope directly, derives a deterministic local fake report from envelope
IDs/digests only, and returns hash-only Author observation/final outcome state.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from hashlib import sha256
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
)
from core.followup_author_payload_construction_runtime import (
    AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
    validate_run_kernel_followup_author_payload_construction_state,
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
)
from core.followup_deliberation import safe_json
from core.followup_fixture_boundaries import (
    followup_common_redaction_posture,
)

FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_SCHEMA_VERSION = (
    "followup_author_execution_from_ad_ag96i3ae_v1"
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_TRACE_KEY = (
    "followup_author_execution_from_ad_runtime"
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE = "followup_author_execution_from_ad"
AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE = (
    "ag96i3ae_ad_consuming_author_execution_fake_model_product_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS = (
    "author_execution_observed_fake_model_product_closed"
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_REASON = (
    "ag96i3ae_ad_consuming_author_execution_fake_model_product_closed"
)

AE_PACKET_MUTATION_FIELDS = frozenset(
    {
        "ag96i3_author_execution_from_ad_ref",
        "ag96i3_author_execution_from_ad_ref_created",
        "ag96i3_author_execution_from_ad_observed",
        "ag96i3_author_execution_from_ad_status",
        "ag96i3_author_execution_from_ad_digest",
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "author_execution_deferred",
        "fake_model_used",
        "real_model_called",
        "ask_model_called",
        "execute_author_action_called",
        "author_observation_created",
        "final_answer_outcome_created",
        "prompt_text_retained",
        "report_text_retained",
        "final_text_retained",
        "final_text_included",
        "product_answer_ready",
        "citation_strings_included",
        "ordered_product_source_output_created",
    }
)
AE_AUTHORITY_PROJECTION_MUTATION_FIELDS = AE_PACKET_MUTATION_FIELDS

_TRUE_FIELDS = (
    "ad_author_payload_envelope_consumed",
    "ac_payload_authority_consumed",
    "z_author_prompt_assembly_manifest_consumed",
    "y_author_execution_activation_consumed",
    "x_author_input_materialization_consumed",
    "w_author_execution_readiness_consumed",
    "v1_author_gate_consumed",
    "u1_authority_consumed",
    "packet_authority_consumed",
    "fake_model_used",
    "legacy_author_payload_ref_subordinated",
    "author_execution_observed",
    "author_observation_created",
    "final_answer_outcome_created",
    "author_execution_deferred",
    "live_validation_not_run",
    "not_for_product_answer_activation",
)
_FALSE_FIELDS = (
    "author_input_ready",
    "author_execution_allowed",
    "author_activation_allowed",
    "real_model_called",
    "ask_model_called",
    "execute_author_action_called",
    "author_model_called",
    "model_called",
    "author_executor_invoked",
    "provider_execution_licensed",
    "live_provider_call_executed",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "prompt_text_retained",
    "report_text_retained",
    "final_text_retained",
    "final_text_included",
    "product_answer_ready",
    "citation_strings_included",
    "ordered_product_source_output_created",
    "final_answer_author_input_payload_created",
    "prompt_text_included",
    "authority_block_text_retained",
    "provider_payloads_retained",
    "prompts_retained",
    "model_responses_retained",
    "unsanitized_text_retained",
    "private_records_or_complete_traces_retained",
)
_ACTION_FORBIDDEN_KEYS = {
    "followup_author_execution_from_ad_state",
    "author_execution_from_ad_state",
    "author_execution_state",
    "author_observation",
    "final_answer_outcome",
    "author_payload",
    "author_input_payload",
    "final_answer_author_input_payload",
    "executable_author_input_payload",
    "payload_sections",
    "prompt_text",
    "authority_block_text",
    "report_text",
    "fake_report_text",
    "model_response",
    "author_output",
    "final_answer_text",
    "product_output",
}
_CALLER_CONTROLLED_KEYS = (
    set(_ACTION_FORBIDDEN_KEYS)
    | set(_TRUE_FIELDS)
    | set(_FALSE_FIELDS)
    | set(AE_PACKET_MUTATION_FIELDS)
)
_CLOSED_KEY_PARTS = (
    "raw_prompt",
    "prompt_text",
    "prompt_body",
    "prompt_value",
    "prompt_content",
    "authority_block_text",
    "report_text",
    "fake_report_text",
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
    "author_input_ready",
)
_CLOSED_KEY_ALLOWED_TOKENS = frozenset(
    {
        "prompt_text_digest",
        "prompt_text_length",
        "author_report_text_digest",
        "author_report_text_length",
        "report_hash",
        "report_length",
        "report_text_retained",
        "final_text_retained",
        "final_text_included",
        "fake_invocation_digest",
        "fake_invocation_length",
        "authority_block_text_digest",
        "authority_block_text_length",
        "payload_section_digests",
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
    context_label="AE Author execution",
)
_validate_projection_update = partial(
    _shared_validate_projection_update,
    allowed_mutation_fields=AE_PACKET_MUTATION_FIELDS,
    phase_label="AE",
    ref_field="ag96i3_author_execution_from_ad_ref",
    ref_label="execution ref",
    author_payload_ref_status=FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
_PROJECTED_FIELDS = (
    "schema_version",
    "status",
    "author_execution_from_ad_id",
    "author_execution_from_ad_mode",
    "author_execution_from_ad_stage",
    "payload_envelope_id",
    "payload_envelope_digest",
    "payload_envelope_ref_digest",
    "ac_payload_authority_id",
    "ac_payload_authority_digest",
    "ac_payload_authority_projection_digest",
    "ac_payload_authority_ref_digest",
    "z_author_prompt_assembly_manifest_id",
    "z_author_prompt_assembly_manifest_digest",
    "z_author_prompt_assembly_manifest_projection_digest",
    "z_author_prompt_assembly_manifest_ref_digest",
    "y_author_execution_activation_id",
    "y_author_execution_activation_digest",
    "y_author_execution_activation_projection_digest",
    "y_author_execution_activation_ref_digest",
    "x_author_input_materialization_id",
    "x_author_input_materialization_digest",
    "x_author_input_materialization_projection_digest",
    "w_author_execution_readiness_id",
    "w_author_execution_readiness_digest",
    "w_author_execution_readiness_projection_digest",
    "v1_author_gate_id",
    "v1_author_gate_digest",
    "v1_author_gate_projection_digest",
    "u1_authority_id",
    "u1_authority_digest",
    "u1_authority_projection_digest",
    "packet_id",
    "current_final_answer_packet_digest",
    "final_answer_authority_projection_digest",
    "final_answer_packet_digest",
    "ad_payload_construction_digest",
    "ad_payload_construction_projection_digest",
    "ad_updated_final_answer_packet_digest",
    "ad_updated_final_answer_authority_projection_digest",
    "author_input_refs_digest",
    "legacy_author_payload_ref_id",
    "legacy_author_payload_ref_status",
    "legacy_author_payload_ref_digest",
    "payload_section_ids",
    "payload_section_digests",
    "x_bill_of_materials_digest",
    "prompt_text_digest",
    "prompt_text_length",
    "fake_invocation_digest",
    "fake_invocation_length",
    "author_report_text_digest",
    "author_report_text_length",
    "author_observation_id",
    "author_observation_digest",
    "final_answer_outcome_id",
    "final_answer_outcome_digest",
    "ag96i3_author_execution_from_ad_ref",
    "ag96i3_author_execution_from_ad_digest",
    *_TRUE_FIELDS,
    *_FALSE_FIELDS,
)
_BOUNDARY_FLAG_TOKENS = "+canonical_final_answer_packet_mutated +final_answer_packet_updated +final_answer_authority_projection_mutated +ad_author_payload_envelope_consumed +ac_payload_authority_consumed +z_author_prompt_assembly_manifest_consumed +y_author_execution_activation_consumed +x_author_input_materialization_consumed +w_author_execution_readiness_consumed +v1_author_gate_consumed +u1_authority_consumed +packet_authority_consumed +fake_model_used +legacy_author_payload_ref_subordinated +author_execution_observed -real_model_called -ask_model_called -execute_author_action_called -author_model_called -model_called -author_executor_invoked -provider_payloads_retained -prompts_retained -model_responses_retained -unsanitized_text_retained -private_records_or_complete_traces_retained +author_observation_created +final_answer_outcome_created -author_input_ready -author_execution_allowed -author_activation_allowed +author_execution_deferred -final_answer_author_input_payload_created -prompt_text_included -prompt_text_retained -authority_block_text_retained -report_text_retained -final_text_retained -final_text_included -product_answer_ready -citation_strings_included -ordered_product_source_output_created +live_validation_not_run +not_for_product_answer_activation".split()


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionFromADActionResult:
    record: "FollowupAuthorExecutionFromADRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionFromADRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _mapping(self.state)


def reject_followup_author_execution_from_ad_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    reject_caller_controlled_inputs(inputs, caller_controlled_keys=_CALLER_CONTROLLED_KEYS, context_label="AE Author execution action", closed_surface_rejector=_reject_forbidden_payload, check_raw_keys=True)


def build_followup_author_execution_from_ad_action_inputs(
    *,
    followup_author_payload_construction_state: Mapping[str, Any],
    followup_author_payload_construction_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
) -> dict[str, Any]:
    ad_state = _mapping(followup_author_payload_construction_state)
    ad_projection = _mapping(followup_author_payload_construction_projection)
    packet = _mapping(final_answer_packet)
    authority = _mapping(final_answer_authority_projection)
    envelope_ref = _mapping(ad_state.get("ag96i3_author_payload_envelope_ref"))
    author_input_refs = _mapping(packet.get("author_input_refs"))
    legacy_payload_ref = _mapping(packet.get("author_payload_ref"))
    return {
        "run_id": ad_state.get("run_id"),
        "checkpoint_id": ad_state.get("checkpoint_id"),
        "followup_authorization_consumption_id": ad_state.get(
            "followup_authorization_consumption_id"
        ),
        "sealed_candidate_id": ad_state.get("sealed_candidate_id"),
        "followup_execution_id": ad_state.get("followup_execution_id"),
        "execution_id": ad_state.get("execution_id"),
        "followup_evidence_intake_id": ad_state.get("followup_evidence_intake_id"),
        "intake_id": ad_state.get("intake_id"),
        "followup_sufficiency_recheck_id": ad_state.get(
            "followup_sufficiency_recheck_id"
        ),
        "recheck_id": ad_state.get("recheck_id"),
        "packet_id": packet.get("packet_id"),
        "author_execution_from_ad_id": _execution_id(ad_state),
        "author_execution_from_ad_mode": (
            AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE
        ),
        "status": FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS,
        "payload_envelope_id": ad_state.get("payload_envelope_id"),
        "payload_envelope_digest": ad_state.get("ag96i3_author_payload_digest"),
        "payload_envelope_ref_digest": _digest(envelope_ref),
        "ac_payload_authority_id": ad_state.get("ac_payload_authority_id"),
        "ac_payload_authority_digest": ad_state.get("ac_payload_authority_digest"),
        "ac_payload_authority_projection_digest": ad_state.get(
            "ac_payload_authority_projection_digest"
        ),
        "ac_payload_authority_ref_digest": ad_state.get(
            "ac_payload_authority_ref_digest"
        ),
        "z_author_prompt_assembly_manifest_id": ad_state.get(
            "z_author_prompt_assembly_manifest_id"
        ),
        "z_author_prompt_assembly_manifest_digest": ad_state.get(
            "z_author_prompt_assembly_manifest_digest"
        ),
        "z_author_prompt_assembly_manifest_ref_digest": ad_state.get(
            "z_author_prompt_assembly_manifest_ref_digest"
        ),
        "y_author_execution_activation_id": ad_state.get(
            "y_author_execution_activation_id"
        ),
        "y_author_execution_activation_digest": ad_state.get(
            "y_author_execution_activation_digest"
        ),
        "y_author_execution_activation_ref_digest": ad_state.get(
            "y_author_execution_activation_ref_digest"
        ),
        "x_author_input_materialization_id": ad_state.get(
            "x_author_input_materialization_id"
        ),
        "x_author_input_materialization_digest": ad_state.get(
            "x_author_input_materialization_digest"
        ),
        "w_author_execution_readiness_id": ad_state.get(
            "w_author_execution_readiness_id"
        ),
        "w_author_execution_readiness_digest": ad_state.get(
            "w_author_execution_readiness_digest"
        ),
        "v1_author_gate_id": ad_state.get("v1_author_gate_id"),
        "v1_author_gate_digest": ad_state.get("v1_author_gate_digest"),
        "u1_authority_id": ad_state.get("u1_authority_id"),
        "u1_authority_digest": ad_state.get("u1_authority_digest"),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "ad_payload_construction_digest": _digest(ad_state),
        "ad_payload_construction_projection_digest": _digest(ad_projection),
        "ad_updated_final_answer_packet_digest": ad_state.get(
            "updated_final_answer_packet_digest"
        ),
        "ad_updated_final_answer_authority_projection_digest": ad_state.get(
            "updated_final_answer_authority_projection_digest"
        ),
        "author_input_refs_digest": _digest(author_input_refs),
        "legacy_author_payload_ref_id": legacy_payload_ref.get("payload_ref_id"),
        "legacy_author_payload_ref_status": legacy_payload_ref.get("status"),
        "legacy_author_payload_ref_digest": _digest(legacy_payload_ref),
        "prompt_text_digest": ad_state.get("prompt_text_digest"),
        "prompt_text_length": ad_state.get("prompt_text_length"),
        "ad_author_payload_envelope_consumed": True,
        "fake_model_used": True,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "legacy_author_payload_ref_subordinated": True,
        "author_execution_deferred": True,
        "author_execution_observed": True,
        "author_observation_created": True,
        "final_answer_outcome_created": True,
        "prompt_text_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def execute_followup_author_execution_from_ad_action(
    action: Any,
    **runtime_inputs: Any,
) -> FollowupAuthorExecutionFromADActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
        stage=FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_OBSERVED
        ),
    )
    record = build_followup_author_execution_from_ad_record(
        action_inputs=_mapping(action.inputs),
        **runtime_inputs,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_OBSERVED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_execution_from_ad_state": record.to_dict()},
    )
    return FollowupAuthorExecutionFromADActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_execution_from_ad_record(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> FollowupAuthorExecutionFromADRecord:
    action = _mapping(action_inputs)
    ad_state = _mapping(runtime_inputs.get("followup_author_payload_construction_state"))
    ad_projection = _mapping(
        runtime_inputs.get("followup_author_payload_construction_projection")
    )
    ad_history = _history(runtime_inputs, "followup_author_payload_construction")
    ac_state = _mapping(runtime_inputs.get("followup_author_payload_authority_state"))
    ac_projection = _mapping(
        runtime_inputs.get("followup_author_payload_authority_projection")
    )
    ac_history = _history(runtime_inputs, "followup_author_payload_authority")
    z_state = _mapping(
        runtime_inputs.get("followup_author_prompt_assembly_manifest_state")
    )
    z_projection = _mapping(
        runtime_inputs.get("followup_author_prompt_assembly_manifest_projection")
    )
    z_history = _history(runtime_inputs, "followup_author_prompt_assembly_manifest")
    y_state = _mapping(runtime_inputs.get("followup_author_execution_activation_state"))
    y_projection = _mapping(
        runtime_inputs.get("followup_author_execution_activation_projection")
    )
    y_history = _history(runtime_inputs, "followup_author_execution_activation")
    x_state = _mapping(runtime_inputs.get("followup_author_input_materialization_state"))
    x_projection = _mapping(
        runtime_inputs.get("followup_author_input_materialization_projection")
    )
    x_history = _history(runtime_inputs, "followup_author_input_materialization")
    w_state = _mapping(runtime_inputs.get("followup_author_execution_readiness_state"))
    w_projection = _mapping(
        runtime_inputs.get("followup_author_execution_readiness_projection")
    )
    w_history = _history(runtime_inputs, "followup_author_execution_readiness")
    v1_state = _mapping(runtime_inputs.get("followup_author_gate_state"))
    v1_projection = _mapping(runtime_inputs.get("followup_author_gate_projection"))
    v1_history = _history(runtime_inputs, "followup_author_gate")
    u1_state = _mapping(runtime_inputs.get("followup_author_input_authority_state"))
    u1_projection = _mapping(
        runtime_inputs.get("followup_author_input_authority_projection")
    )
    u1_history = _history(runtime_inputs, "followup_author_input_authority")
    packet = _mapping(runtime_inputs.get("final_answer_packet"))
    authority = _mapping(runtime_inputs.get("final_answer_authority_projection"))

    _validate_ad_current(ad_state, ad_projection, ad_history)
    _validate_upstream_bindings(
        ad_state=ad_state,
        ac_state=ac_state,
        ac_projection=ac_projection,
        ac_history=ac_history,
        z_state=z_state,
        z_projection=z_projection,
        z_history=z_history,
        y_state=y_state,
        y_projection=y_projection,
        y_history=y_history,
        x_state=x_state,
        x_projection=x_projection,
        x_history=x_history,
        w_state=w_state,
        w_projection=w_projection,
        w_history=w_history,
        v1_state=v1_state,
        v1_projection=v1_projection,
        v1_history=v1_history,
        u1_state=u1_state,
        u1_projection=u1_projection,
        u1_history=u1_history,
    )
    _validate_packet_and_projection(action, ad_state, packet, authority, u1_state)
    expected_action = build_followup_author_execution_from_ad_action_inputs(
        followup_author_payload_construction_state=ad_state,
        followup_author_payload_construction_projection=ad_projection,
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
    )
    _require(action == expected_action, "AE action must match canonical AD inputs")

    envelope_ref = _mapping(ad_state.get("ag96i3_author_payload_envelope_ref"))
    legacy_payload_ref = _mapping(packet.get("author_payload_ref"))
    payload_section_digests = _mapping(ad_state.get("payload_section_digests"))
    invocation_ref = _fake_invocation_ref(ad_state)
    fake_report_facts = _fake_report_facts(invocation_ref)
    author_observation_id = (
        "ag96i3ae-author-observation:"
        f"{action.get('author_execution_from_ad_id')}:"
        f"{action.get('payload_envelope_digest', '')[:16]}"
    )
    final_answer_outcome_id = (
        "ag96i3ae-final-answer-outcome:"
        f"{action.get('author_execution_from_ad_id')}:"
        f"{action.get('payload_envelope_digest', '')[:16]}"
    )
    author_observation = _author_observation(
        action=action,
        author_observation_id=author_observation_id,
        fake_report_facts=fake_report_facts,
    )
    final_answer_outcome = _final_answer_outcome(
        action=action,
        final_answer_outcome_id=final_answer_outcome_id,
        author_observation=author_observation,
        fake_report_facts=fake_report_facts,
    )
    execution_ref = {
        "author_execution_from_ad_ref_id": (
            "ag96i3-author-execution-from-ad-ref:"
            f"{action.get('payload_envelope_id')}:"
            f"{action.get('payload_envelope_digest', '')[:16]}"
        ),
        "status": FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS,
        "author_execution_from_ad_mode": (
            AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE
        ),
        "payload_envelope_id": action.get("payload_envelope_id"),
        "payload_envelope_digest": action.get("payload_envelope_digest"),
        "payload_envelope_ref_digest": action.get("payload_envelope_ref_digest"),
        "ac_payload_authority_id": action.get("ac_payload_authority_id"),
        "z_author_prompt_assembly_manifest_id": action.get(
            "z_author_prompt_assembly_manifest_id"
        ),
        "x_author_input_materialization_id": action.get(
            "x_author_input_materialization_id"
        ),
        "packet_id": action.get("packet_id"),
        "current_final_answer_packet_digest": action.get(
            "current_final_answer_packet_digest"
        ),
        "final_answer_authority_projection_digest": action.get(
            "final_answer_authority_projection_digest"
        ),
        "author_observation_id": author_observation_id,
        "author_observation_digest": _digest(author_observation),
        "final_answer_outcome_id": final_answer_outcome_id,
        "final_answer_outcome_digest": _digest(final_answer_outcome),
        "fake_model_used": True,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "prompt_text_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
        "not_for_product_answer_activation": True,
    }
    execution_digest = _digest(execution_ref)
    mutation = _execution_mutation(execution_ref, execution_digest)
    state = {
        **action,
        **author_execution_from_ad_boundary_flags(),
        "schema_version": FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_SCHEMA_VERSION,
        "trace_key": FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_TRACE_KEY,
        "record_type": "followup_author_execution_from_ad_record",
        "owner": "FollowupAuthorExecutionFromADRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "author_execution_from_ad_stage": FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE,
        "ad_author_payload_envelope_status": (
            FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS
        ),
        "ad_author_payload_envelope_mode": AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
        "ad_author_payload_envelope_ref_status": (
            FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS
        ),
        "ac_payload_authority_mode": (
            AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE
        ),
        "ac_payload_authority_ref_status": FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "z_author_prompt_assembly_manifest_mode": (
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
        ),
        "y_author_execution_activation_mode": AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
        "y_author_execution_activation_ref_status": (
            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS
        ),
        "y_old_ready_status_demoted": True,
        "y_author_input_ready": False,
        "activation_consumable_by_future_author_execution": True,
        "x_author_input_materialization_mode": AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
        "w_author_execution_readiness_mode": AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
        "v1_author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
        "u1_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
        "payload_envelope_ref": safe_json(envelope_ref),
        "payload_section_ids": list(ad_state.get("payload_section_ids", [])),
        "payload_section_digests": safe_json(payload_section_digests),
        "x_bill_of_materials_digest": _digest(
            _mapping(ad_state.get("x_bill_of_materials"))
        ),
        "fake_invocation_digest": _digest(invocation_ref),
        "fake_invocation_length": len(repr(safe_json(invocation_ref))),
        "transient_ad_native_invocation_text_constructed": False,
        "fake_noop_model_marker": (
            "deterministic_local_fake_model_product_closed"
        ),
        "author_report_text_digest": fake_report_facts[
            "author_report_text_digest"
        ],
        "author_report_text_length": fake_report_facts[
            "author_report_text_length"
        ],
        "author_observation_id": author_observation_id,
        "author_observation": safe_json(author_observation),
        "author_observation_digest": _digest(author_observation),
        "final_answer_outcome_id": final_answer_outcome_id,
        "final_answer_outcome": safe_json(final_answer_outcome),
        "final_answer_outcome_digest": _digest(final_answer_outcome),
        "ag96i3_author_execution_from_ad_ref": safe_json(execution_ref),
        "ag96i3_author_execution_from_ad_digest": execution_digest,
        "packet_mutation": safe_json(mutation),
        "final_answer_authority_projection_mutation": safe_json(mutation),
        "updated_final_answer_packet_digest": _digest(
            _updated_with_mutation(packet, mutation)
        ),
        "updated_final_answer_authority_projection_digest": _digest(
            _updated_with_mutation(authority, mutation)
        ),
        "legacy_author_payload_ref_digest": _digest(legacy_payload_ref),
        "behavior_boundary_flags": author_execution_from_ad_boundary_flags(),
        "redaction_posture": _redaction_posture(),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorExecutionFromADRecord(safe_json(state))


def build_run_kernel_followup_author_execution_from_ad_state(
    *,
    execution_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **_mapping(execution_record_state),
        "owner": "RunKernel.FollowupAuthorExecutionFromAD",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_execution_from_ad_state(
        execution_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_execution_from_ad_state(
    *,
    execution_state: Mapping[str, Any],
) -> None:
    state = _mapping(execution_state)
    _require(
        state.get("owner") == "RunKernel.FollowupAuthorExecutionFromAD",
        "AE Author execution requires RunKernel owner",
    )
    _require(state.get("canonical_state") is True, "AE requires canonical state")
    _require(state.get("trace_only") is False, "AE cannot be trace-only")
    _require(state.get("storage_only") is False, "AE cannot be storage-only")
    _require(
        state.get("status") == FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS,
        "AE Author execution status mismatch",
    )
    _require(
        state.get("author_execution_from_ad_mode")
        == AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE,
        "AE Author execution mode mismatch",
    )
    _require(
        state.get("legacy_author_payload_ref_status") == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        "AE requires deferred legacy author_payload_ref",
    )
    _validate_closed_flags(state)
    _require(
        set(_mapping(state.get("packet_mutation"))) == set(AE_PACKET_MUTATION_FIELDS),
        "AE packet mutation keys mismatch",
    )
    _require(_mapping(state.get("author_observation")), "AE requires observation")
    _require(_mapping(state.get("final_answer_outcome")), "AE requires outcome")
    _reject_forbidden_payload(state)


def build_followup_author_execution_from_ad_projection(
    *,
    execution_state: Mapping[str, Any],
    behavior_boundary_flags: Mapping[str, Any],
    final_answer_packet_stage: str,
    followup_author_payload_construction_stage: str,
) -> dict[str, Any]:
    state = _mapping(execution_state)
    projection = {
        "owner": "RunKernel.FollowupAuthorExecutionFromAD",
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
        "followup_author_payload_construction_ref": {
            "owner": "RunKernel.FollowupAuthorPayloadConstruction",
            "canonical_state": True,
            "payload_envelope_id": state.get("payload_envelope_id"),
            "projection_stage": followup_author_payload_construction_stage,
        },
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_execution_from_ad_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_execution_state: Mapping[str, Any],
) -> None:
    action = _mapping(action_inputs)
    observed = _mapping(observed_execution_state)
    _require(observed, "AE observation requires execution state")
    _validate_closed_flags(observed)
    _reject_forbidden_payload(observed)
    for field, expected in action.items():
        _require(observed.get(field) == expected, f"AE observation {field} mismatch")


def ae_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return _projection_from_record_mutation(
        current_packet, record_state, "packet", "packet_mutation", AE_PACKET_MUTATION_FIELDS, "current_final_answer_packet_digest", "AE mutation mismatch", "AE stale packet", _validate_projection_update
    )


def ae_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return _projection_from_record_mutation(
        current_projection, record_state, "authority", "final_answer_authority_projection_mutation", AE_AUTHORITY_PROJECTION_MUTATION_FIELDS, "final_answer_authority_projection_digest", "AE authority mutation mismatch", "AE stale authority projection", _validate_projection_update
    )


def author_execution_from_ad_boundary_flags() -> dict[str, bool]:
    return boundary_flags_from_tokens(_BOUNDARY_FLAG_TOKENS)


_validate_closed_flags = partial(
    _shared_validate_closed_flags,
    true_fields=_TRUE_FIELDS,
    false_fields=_FALSE_FIELDS,
    boundary_flags=author_execution_from_ad_boundary_flags,
    context_label="AE",
)


def _validate_ad_current(
    ad_state: Mapping[str, Any],
    ad_projection: Mapping[str, Any],
    ad_history: Sequence[Mapping[str, Any]],
) -> None:
    _require(ad_state, "AE requires AD payload envelope state")
    validate_run_kernel_followup_author_payload_construction_state(
        payload_construction_state=ad_state
    )
    _require(
        ad_state.get("owner") == "RunKernel.FollowupAuthorPayloadConstruction",
        "AE requires RunKernel AD payload envelope state",
    )
    _require(
        ad_state.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
        "AE requires execution-closed AD payload envelope",
    )
    _require(
        ad_state.get("payload_envelope_mode") == AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
        "AE requires AG-96I3AD payload envelope mode",
    )
    _require(
        ad_projection.get("owner") == "RunKernel.FollowupAuthorPayloadConstruction",
        "AE requires RunKernel AD projection",
    )
    _require(ad_projection.get("canonical_state") is True, "AE requires canonical AD")
    _require(
        ad_history and _mapping(ad_history[-1]) == ad_projection,
        "AE requires current AD history",
    )
    for key, projected_value in ad_projection.items():
        if key in ad_state:
            _require(
                safe_json(ad_state.get(key)) == projected_value,
                f"AE stale AD projection field {key}",
            )
    envelope_ref = _mapping(ad_state.get("ag96i3_author_payload_envelope_ref"))
    _require(
        ad_state.get("ag96i3_author_payload_digest") == _digest(envelope_ref),
        "AE stale AD payload envelope ref digest",
    )
    _require(
        ad_state.get("payload_envelope_ref_status")
        == FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
        "AE requires AD payload envelope ref status",
    )
    _require(
        ad_state.get("future_author_execution_must_consume") is True,
        "AE requires AD future-execution consumption authority",
    )
    ad_boundary_flags = _mapping(ad_state.get("behavior_boundary_flags"))
    for field in (
        "ac_payload_authority_consumed",
        "z_author_prompt_assembly_manifest_consumed",
        "y_author_execution_activation_consumed",
        "x_author_input_materialization_consumed",
        "w_author_execution_readiness_consumed",
        "v1_author_gate_consumed",
        "u1_authority_consumed",
        "packet_authority_consumed",
        "payload_constructed",
    ):
        _require(ad_boundary_flags.get(field) is True, f"AE requires AD {field}=True")
    for field in (
        "author_observation_created",
        "final_answer_outcome_created",
        "product_answer_ready",
        "final_text_included",
    ):
        _require(ad_state.get(field) is False, f"AE requires AD {field}=False")


def _validate_upstream_bindings(
    *,
    ad_state: Mapping[str, Any],
    ac_state: Mapping[str, Any],
    ac_projection: Mapping[str, Any],
    ac_history: Sequence[Mapping[str, Any]],
    z_state: Mapping[str, Any],
    z_projection: Mapping[str, Any],
    z_history: Sequence[Mapping[str, Any]],
    y_state: Mapping[str, Any],
    y_projection: Mapping[str, Any],
    y_history: Sequence[Mapping[str, Any]],
    x_state: Mapping[str, Any],
    x_projection: Mapping[str, Any],
    x_history: Sequence[Mapping[str, Any]],
    w_state: Mapping[str, Any],
    w_projection: Mapping[str, Any],
    w_history: Sequence[Mapping[str, Any]],
    v1_state: Mapping[str, Any],
    v1_projection: Mapping[str, Any],
    v1_history: Sequence[Mapping[str, Any]],
    u1_state: Mapping[str, Any],
    u1_projection: Mapping[str, Any],
    u1_history: Sequence[Mapping[str, Any]],
) -> None:
    _validate_current_projection(
        state=ac_state,
        projection=ac_projection,
        history=ac_history,
        owner="RunKernel.FollowupAuthorPayloadAuthority",
        context="AC payload authority",
    )
    bindings = (
        (
            "ac_payload_authority_id",
            ac_state,
            ac_projection,
            "payload_authority_id",
            "ac_payload_authority_digest",
            "ac_payload_authority_projection_digest",
            AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE,
            "payload_authority_mode",
        ),
        (
            "z_author_prompt_assembly_manifest_id",
            z_state,
            z_projection,
            "author_prompt_assembly_manifest_id",
            "z_author_prompt_assembly_manifest_digest",
            "z_author_prompt_assembly_manifest_projection_digest",
            AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
            "author_prompt_assembly_manifest_mode",
        ),
        (
            "y_author_execution_activation_id",
            y_state,
            y_projection,
            "author_execution_activation_id",
            "y_author_execution_activation_digest",
            "y_author_execution_activation_projection_digest",
            AG96I3Y_AUTHOR_EXECUTION_ACTIVATION_MODE,
            "author_execution_activation_mode",
        ),
        (
            "x_author_input_materialization_id",
            x_state,
            x_projection,
            "author_input_materialization_id",
            "x_author_input_materialization_digest",
            "x_author_input_materialization_projection_digest",
            AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
            "author_input_materialization_mode",
        ),
        (
            "w_author_execution_readiness_id",
            w_state,
            w_projection,
            "author_execution_readiness_id",
            "w_author_execution_readiness_digest",
            "w_author_execution_readiness_projection_digest",
            AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
            "author_execution_readiness_mode",
        ),
        (
            "v1_author_gate_id",
            v1_state,
            v1_projection,
            "author_gate_id",
            "v1_author_gate_digest",
            "v1_author_gate_projection_digest",
            AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
            "author_gate_mode",
        ),
        (
            "u1_authority_id",
            u1_state,
            u1_projection,
            "author_input_authority_id",
            "u1_authority_digest",
            "u1_authority_projection_digest",
            AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
            "author_input_authority_mode",
        ),
    )
    histories = {
        "z_author_prompt_assembly_manifest_id": z_history,
        "y_author_execution_activation_id": y_history,
        "x_author_input_materialization_id": x_history,
        "w_author_execution_readiness_id": w_history,
        "v1_author_gate_id": v1_history,
        "u1_authority_id": u1_history,
    }
    owners = {
        "z_author_prompt_assembly_manifest_id": (
            "RunKernel.FollowupAuthorPromptAssemblyManifest"
        ),
        "y_author_execution_activation_id": (
            "RunKernel.FollowupAuthorExecutionActivation"
        ),
        "x_author_input_materialization_id": (
            "RunKernel.FollowupAuthorInputMaterialization"
        ),
        "w_author_execution_readiness_id": (
            "RunKernel.FollowupAuthorExecutionReadiness"
        ),
        "v1_author_gate_id": "RunKernel.FollowupAuthorGate",
        "u1_authority_id": "RunKernel.FollowupAuthorInputAuthority",
    }
    for ad_id, state, projection, state_id, ad_digest, projection_digest, mode, mode_field in bindings:
        if ad_id in histories:
            _validate_current_projection(
                state=state,
                projection=projection,
                history=histories[ad_id],
                owner=owners[ad_id],
                context=ad_id,
            )
        _require(ad_state.get(ad_id) == state.get(state_id), f"AE {ad_id} mismatch")
        _require(
            ad_state.get(ad_digest) == _digest(state),
            f"AE {ad_digest} stale",
        )
        _require(state.get(mode_field) == mode, f"AE {mode_field} mismatch")
        if projection_digest in ad_state:
            _require(
                ad_state.get(projection_digest) == _digest(projection),
                f"AE {projection_digest} stale",
            )
    _require(
        ac_state.get("payload_authority_ref_status")
        == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
        "AE requires AC payload authority ref status",
    )
    _require(
        ad_state.get("ac_payload_authority_projection_digest") == _digest(ac_projection),
        "AE AC projection digest stale",
    )
    _require(
        y_state.get("author_execution_activation_ref_status")
        == FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REF_STATUS,
        "AE requires Y demoted activation ref status",
    )
    _require(y_state.get("author_input_ready") is False, "AE requires Y demotion")
    _require(
        y_state.get("activation_consumable_by_future_author_execution") is True,
        "AE requires Y future execution consumability",
    )


def _validate_current_projection(
    *,
    state: Mapping[str, Any],
    projection: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    owner: str,
    context: str,
) -> None:
    _require(state, f"AE requires {context} state")
    _require(projection.get("owner") == owner, f"AE requires {context} projection")
    _require(projection.get("canonical_state") is True, f"AE {context} canonical")
    _require(history and _mapping(history[-1]) == projection, f"AE {context} history")


def _validate_packet_and_projection(
    action: Mapping[str, Any],
    ad_state: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    u1_state: Mapping[str, Any],
) -> None:
    legacy_payload_ref, author_input_refs = validate_packet_projection_base(
        packet,
        authority,
        u1_state,
        "AE",
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AE packet/authority payload ref mismatch",
        "AE U1 payload ref mismatch",
    )
    envelope_ref = _mapping(ad_state.get("ag96i3_author_payload_envelope_ref"))
    _require(
        packet.get("ag96i3_author_payload_envelope_ref") == envelope_ref,
        "AE packet AD payload envelope ref mismatch",
    )
    _require(
        authority.get("ag96i3_author_payload_envelope_ref") == envelope_ref,
        "AE authority AD payload envelope ref mismatch",
    )
    _require(
        packet.get("ag96i3_author_payload_digest")
        == ad_state.get("ag96i3_author_payload_digest"),
        "AE packet AD payload digest mismatch",
    )
    _require(
        authority.get("ag96i3_author_payload_digest")
        == ad_state.get("ag96i3_author_payload_digest"),
        "AE authority AD payload digest mismatch",
    )
    validate_packet_authority_currentness(
        packet,
        authority,
        ad_state,
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        "AE stale packet from AD",
        "AE stale authority projection from AD",
    )
    validate_no_existing_prefixed_fields(
        packet,
        authority,
        AE_PACKET_MUTATION_FIELDS,
        "ag96i3_author_execution_from_ad",
        "AE packet already has execution ref",
        "AE authority already has execution ref",
    )
    expected = build_followup_author_execution_from_ad_action_inputs(
        followup_author_payload_construction_state=ad_state,
        followup_author_payload_construction_projection={},
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
            "payload_envelope_digest",
            "payload_envelope_ref_digest",
            "ad_payload_construction_digest",
        ),
        "AE",
    )


def _author_observation(
    *,
    action: Mapping[str, Any],
    author_observation_id: str,
    fake_report_facts: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorExecutionFromAD",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "record_type": "ag96i3ae_author_observation",
        "author_observation_id": author_observation_id,
        "author_execution_from_ad_id": action.get("author_execution_from_ad_id"),
        "packet_id": action.get("packet_id"),
        "payload_envelope_id": action.get("payload_envelope_id"),
        "payload_envelope_digest": action.get("payload_envelope_digest"),
        "payload_envelope_ref_digest": action.get("payload_envelope_ref_digest"),
        "ac_payload_authority_id": action.get("ac_payload_authority_id"),
        "z_author_prompt_assembly_manifest_id": action.get(
            "z_author_prompt_assembly_manifest_id"
        ),
        "x_author_input_materialization_id": action.get(
            "x_author_input_materialization_id"
        ),
        "current_final_answer_packet_digest": action.get(
            "current_final_answer_packet_digest"
        ),
        "final_answer_authority_projection_digest": action.get(
            "final_answer_authority_projection_digest"
        ),
        "prompt_text_digest": action.get("prompt_text_digest"),
        "prompt_text_length": action.get("prompt_text_length"),
        "author_report_text_digest": fake_report_facts[
            "author_report_text_digest"
        ],
        "author_report_text_length": fake_report_facts[
            "author_report_text_length"
        ],
        "report_hash": fake_report_facts["author_report_text_digest"],
        "report_length": fake_report_facts["author_report_text_length"],
        "fake_model_used": True,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "author_execution_observed": True,
        "author_observation_created": True,
        "final_answer_outcome_created": True,
        "prompt_text_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def _final_answer_outcome(
    *,
    action: Mapping[str, Any],
    final_answer_outcome_id: str,
    author_observation: Mapping[str, Any],
    fake_report_facts: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorExecutionFromADOutcome",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "record_type": "ag96i3ae_final_answer_outcome",
        "final_answer_outcome_id": final_answer_outcome_id,
        "author_observation_id": author_observation.get("author_observation_id"),
        "author_observation_digest": _digest(author_observation),
        "author_execution_from_ad_id": action.get("author_execution_from_ad_id"),
        "packet_id": action.get("packet_id"),
        "payload_envelope_id": action.get("payload_envelope_id"),
        "payload_envelope_digest": action.get("payload_envelope_digest"),
        "author_report_text_digest": fake_report_facts[
            "author_report_text_digest"
        ],
        "author_report_text_length": fake_report_facts[
            "author_report_text_length"
        ],
        "report_hash": fake_report_facts["author_report_text_digest"],
        "report_length": fake_report_facts["author_report_text_length"],
        "fake_model_used": True,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "author_observation_created": True,
        "final_answer_outcome_created": True,
        "prompt_text_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
        "live_validation_not_run": True,
        "not_for_product_answer_activation": True,
    }


def _execution_mutation(
    execution_ref: Mapping[str, Any],
    execution_digest: str,
) -> dict[str, Any]:
    return {
        "ag96i3_author_execution_from_ad_ref": safe_json(execution_ref),
        "ag96i3_author_execution_from_ad_ref_created": True,
        "ag96i3_author_execution_from_ad_observed": True,
        "ag96i3_author_execution_from_ad_status": (
            FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS
        ),
        "ag96i3_author_execution_from_ad_digest": execution_digest,
        "author_input_ready": False,
        "author_execution_allowed": False,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "fake_model_used": True,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "author_observation_created": True,
        "final_answer_outcome_created": True,
        "prompt_text_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "final_text_included": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
    }


def _fake_invocation_ref(ad_state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "mode": AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE,
        "payload_envelope_id": ad_state.get("payload_envelope_id"),
        "payload_envelope_digest": ad_state.get("ag96i3_author_payload_digest"),
        "payload_envelope_ref_digest": _digest(
            _mapping(ad_state.get("ag96i3_author_payload_envelope_ref"))
        ),
        "payload_section_ids": list(ad_state.get("payload_section_ids", [])),
        "payload_section_digests": _mapping(ad_state.get("payload_section_digests")),
        "prompt_text_digest": ad_state.get("prompt_text_digest"),
        "prompt_text_length": ad_state.get("prompt_text_length"),
        "authority_block_text_digest": ad_state.get("authority_block_text_digest"),
        "authority_block_text_length": ad_state.get("authority_block_text_length"),
    }


def _fake_report_facts(invocation_ref: Mapping[str, Any]) -> dict[str, Any]:
    material = safe_json(invocation_ref)
    report = (
        "AG96I3AE fake author execution;"
        f"payload={material.get('payload_envelope_id')};"
        f"digest={material.get('payload_envelope_digest')};"
        f"sections={_digest(_mapping(material.get('payload_section_digests')))}"
    )
    return {
        "author_report_text_digest": sha256(report.encode("utf-8")).hexdigest(),
        "author_report_text_length": len(report),
    }


def _execution_id(ad_state: Mapping[str, Any]) -> str:
    return (
        "followup-author-execution-from-ad:"
        f"{ad_state.get('payload_envelope_id')}:"
        f"{_digest(ad_state)[:16]}"
    )


def _redaction_posture() -> dict[str, bool]:
    posture = followup_common_redaction_posture(
        sanitized_fixture_summary_only=False,
        packet_authority_refs_only=True,
        final_text_retained=False,
    )
    posture.update(
        {
            "prompt_text_retained": False,
            "report_text_retained": False,
            "final_text_retained": False,
            "final_text_included": False,
            "product_answer_ready": False,
        }
    )
    return posture


def _history(runtime_inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [_mapping(item) for item in runtime_inputs.get(f"{prefix}_history", [])]


__all__ = [
    "AE_AUTHORITY_PROJECTION_MUTATION_FIELDS",
    "AE_PACKET_MUTATION_FIELDS",
    "AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_REASON",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_TRACE_KEY",
    "ae_authority_projection_from_record",
    "ae_packet_projection_from_record",
    "author_execution_from_ad_boundary_flags",
    "build_followup_author_execution_from_ad_action_inputs",
    "build_followup_author_execution_from_ad_projection",
    "build_followup_author_execution_from_ad_record",
    "build_run_kernel_followup_author_execution_from_ad_state",
    "execute_followup_author_execution_from_ad_action",
    "reject_followup_author_execution_from_ad_input_spoof",
    "validate_followup_author_execution_from_ad_observation_binding",
    "validate_run_kernel_followup_author_execution_from_ad_state",
]
