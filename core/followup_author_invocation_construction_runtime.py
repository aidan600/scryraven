"""AG-96I3AF4a AD-bound blocked Author invocation manifest."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, Mapping, Sequence

from core.followup_author_evidence_content_bridge_runtime import (
    ANSWER_BEARING_SANITIZED_EXCERPT,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
    validate_run_kernel_followup_author_evidence_content_bridge_state,
)
from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_payload_construction_runtime import (
    AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
    validate_run_kernel_followup_author_payload_construction_state,
)
from core.followup_author_payload_safety import (
    projection_digest as _digest,
)
from core.followup_author_payload_safety import (
    projection_from_record_mutation,
    reject_caller_controlled_inputs,
    require,
    safe_mapping,
    safe_mapping_sequence,
    updated_with_mutation,
    validate_expected_action_fields,
    validate_no_existing_prefixed_fields,
    validate_packet_authority_currentness,
    validate_packet_projection_base,
    validate_projection_update,
)
from core.followup_deliberation import safe_json

FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE = (
    "followup_author_invocation_construction"
)
AG96I3AF4_AD_BOUND_AUTHOR_INVOCATION_MODEL_CLOSED_MODE = (
    "ag96i3af4_ad_bound_author_invocation_model_closed"
)
AG96I3AF4C_BRIDGE_CONSUMING_AUTHOR_INVOCATION_MODEL_CLOSED_MODE = (
    "ag96i3af4c_bridge_consuming_author_invocation_model_closed"
)
FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS = (
    "author_invocation_blocked_missing_author_content_model_closed"
)
FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS = (
    "author_invocation_constructed_model_closed"
)
FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_REASON = (
    "ag96i3af4_ad_bound_author_invocation_model_closed"
)

_MUTATION_KEYS = """
ag96i3_author_invocation_ref ag96i3_author_invocation_ref_created
ag96i3_author_invocation_status ag96i3_author_invocation_digest
ag96i3_author_invocation_content_sufficient author_input_ready
author_execution_allowed author_activation_allowed author_execution_deferred
model_execution_allowed real_model_called ask_model_called
execute_author_action_called author_observation_created
final_answer_outcome_created prompt_text_retained model_response_retained
report_text_retained final_text_retained final_text_included product_answer_ready
citation_strings_included ordered_product_source_output_created
""".split()
AF4_PACKET_MUTATION_FIELDS = frozenset(_MUTATION_KEYS)
AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS = AF4_PACKET_MUTATION_FIELDS
_FALSE_FLAGS = [key for key in _MUTATION_KEYS if key not in {
    "ag96i3_author_invocation_ref",
    "ag96i3_author_invocation_ref_created",
    "ag96i3_author_invocation_status",
    "ag96i3_author_invocation_digest",
    "ag96i3_author_invocation_content_sufficient",
    "author_execution_deferred",
}]
_CLOSED_FLAGS = {key: False for key in _FALSE_FLAGS} | {
    "author_execution_deferred": True,
}
_FORBIDDEN_PAYLOAD_KEYS = set(
    """
followup_author_invocation_construction_state author_invocation_manifest
available_author_content_sections answer_bearing_excerpt_refs prompt_text
invocation_text authority_block_text model_response report_text final_answer_text
product_output raw_prompt raw_provider_payload provider_payload raw_payload db_row
cache private_log full_trace secret api_key sanitized_excerpt_text
sanitized_author_evidence_content_payload
""".split()
)
_FORBIDDEN_INPUTS = set(_MUTATION_KEYS) | _FORBIDDEN_PAYLOAD_KEYS
_BINDINGS = (
    (
        "ac",
        "followup_author_payload_authority",
        "payload_authority_id",
        "ac_payload_authority_id",
        "ac_payload_authority_digest",
    ),
    (
        "z",
        "followup_author_prompt_assembly_manifest",
        "author_prompt_assembly_manifest_id",
        "z_author_prompt_assembly_manifest_id",
        "z_author_prompt_assembly_manifest_digest",
    ),
    (
        "y",
        "followup_author_execution_activation",
        "author_execution_activation_id",
        "y_author_execution_activation_id",
        "y_author_execution_activation_digest",
    ),
    (
        "x",
        "followup_author_input_materialization",
        "author_input_materialization_id",
        "x_author_input_materialization_id",
        "x_author_input_materialization_digest",
    ),
    (
        "w",
        "followup_author_execution_readiness",
        "author_execution_readiness_id",
        "w_author_execution_readiness_id",
        "w_author_execution_readiness_digest",
    ),
    ("v1", "followup_author_gate", "author_gate_id", "v1_author_gate_id", "v1_author_gate_digest"),
    ("u1", "followup_author_input_authority", "author_input_authority_id", "u1_authority_id", "u1_authority_digest"),
)
_U1_CHAIN = (
    ("p1", "followup_final_evidence_selection", "final_evidence_selection_id"),
    ("q1", "followup_citation_eligibility", "citation_eligibility_id"),
    ("r1", "followup_citation_source_handoff", "citation_source_handoff_id"),
    ("t1", "followup_citation_rendering", "citation_rendering_id"),
)
_validate_projection_update = partial(
    validate_projection_update,
    allowed_mutation_fields=AF4_PACKET_MUTATION_FIELDS,
    phase_label="AF4a",
    ref_field="ag96i3_author_invocation_ref",
    ref_label="author invocation ref",
    author_payload_ref_status=FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)


@dataclass(frozen=True)
class FollowupAuthorInvocationConstructionRecord:
    state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return safe_mapping(self.state)


def reject_followup_author_invocation_construction_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    _reject_forbidden_payload(dict(inputs or {}) if isinstance(inputs, Mapping) else {})
    reject_caller_controlled_inputs(
        inputs,
        caller_controlled_keys=_FORBIDDEN_INPUTS,
        context_label="AF4a Author invocation action",
        closed_surface_rejector=_reject_forbidden_payload,
        check_raw_keys=True,
    )


def build_followup_author_invocation_construction_action_inputs(
    *,
    followup_author_payload_construction_state: Mapping[str, Any],
    followup_author_payload_construction_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    followup_author_evidence_content_bridge_state: Mapping[str, Any] | None = None,
    followup_author_evidence_content_bridge_projection: Mapping[str, Any] | None = None,
    followup_author_evidence_content_bridge_history: Sequence[Mapping[str, Any]] | None = None,
    **_: Any,
) -> dict[str, Any]:
    ad = safe_mapping(followup_author_payload_construction_state)
    packet = safe_mapping(final_answer_packet)
    authority = safe_mapping(final_answer_authority_projection)
    legacy_ref = safe_mapping(packet.get("author_payload_ref"))
    bridge_fields = _bridge_action_fields(
        bridge_state=followup_author_evidence_content_bridge_state,
        bridge_projection=followup_author_evidence_content_bridge_projection,
        bridge_history=followup_author_evidence_content_bridge_history,
    )
    bridge_consumed = bool(bridge_fields)
    sufficient = bridge_fields.get("af4b2_author_evidence_content_sufficient") is True
    status = (
        FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
        if sufficient
        else FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS
    )
    return {
        "run_id": ad.get("run_id"),
        "checkpoint_id": ad.get("checkpoint_id"),
        "packet_id": packet.get("packet_id"),
        "author_invocation_construction_id": _invocation_id(ad),
        "author_invocation_construction_mode": (
            AG96I3AF4C_BRIDGE_CONSUMING_AUTHOR_INVOCATION_MODEL_CLOSED_MODE
            if bridge_consumed
            else AG96I3AF4_AD_BOUND_AUTHOR_INVOCATION_MODEL_CLOSED_MODE
        ),
        "status": status,
        "payload_envelope_id": ad.get("payload_envelope_id"),
        "payload_envelope_digest": ad.get("ag96i3_author_payload_digest"),
        "payload_envelope_ref_digest": _digest(
            safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))
        ),
        "ad_payload_construction_digest": _digest(ad),
        "ad_payload_construction_projection_digest": _digest(
            safe_mapping(followup_author_payload_construction_projection)
        ),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(safe_mapping(packet.get("author_input_refs"))),
        "legacy_author_payload_ref_status": legacy_ref.get("status"),
        "author_evidence_content_sufficient": sufficient,
        "content_resolution_status": (
            "af4b2_author_evidence_content_bound"
            if sufficient
            else (
                "af4b2_author_evidence_content_blocked"
                if bridge_consumed
                else "blocked_missing_author_evidence_content"
            )
        ),
        **bridge_fields,
    }


def build_followup_author_invocation_construction_record(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> FollowupAuthorInvocationConstructionRecord:
    action = safe_mapping(action_inputs)
    ad = safe_mapping(runtime_inputs.get("followup_author_payload_construction_state"))
    ad_projection = safe_mapping(runtime_inputs.get("followup_author_payload_construction_projection"))
    packet = safe_mapping(runtime_inputs.get("final_answer_packet"))
    authority = safe_mapping(runtime_inputs.get("final_answer_authority_projection"))
    upstreams = _current_upstreams(runtime_inputs)
    _validate_ad(ad, ad_projection, runtime_inputs)
    _validate_upstreams(ad, upstreams)
    bridge = _validate_bridge(ad, packet, authority, runtime_inputs)
    _validate_packet(action, ad, packet, authority, upstreams["u1"], bridge)
    expected = build_followup_author_invocation_construction_action_inputs(
        followup_author_payload_construction_state=ad,
        followup_author_payload_construction_projection=ad_projection,
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
        followup_author_evidence_content_bridge_state=bridge.get("state"),
        followup_author_evidence_content_bridge_projection=bridge.get("projection"),
        followup_author_evidence_content_bridge_history=bridge.get("history"),
    )
    require(action == expected, "AF4a action must match canonical AD inputs")
    sufficient = bridge.get("sufficient") is True
    missing_refs, identity_refs = _missing_content_refs(ad, upstreams["u1"], bridge)
    manifest = _invocation_manifest(
        action=action,
        ad=ad,
        bridge=bridge,
        missing_refs=missing_refs,
        identity_refs=identity_refs,
    )
    invocation_ref = {
        "author_invocation_ref_id": _invocation_ref_id(action, sufficient),
        **manifest,
        "packet_id": action.get("packet_id"),
        "payload_envelope_ref_digest": action.get("payload_envelope_ref_digest"),
        "ad_payload_construction_digest": action.get("ad_payload_construction_digest"),
        "current_final_answer_packet_digest": action.get("current_final_answer_packet_digest"),
        "final_answer_authority_projection_digest": action.get("final_answer_authority_projection_digest"),
    }
    invocation_digest = _digest(invocation_ref)
    mutation = _invocation_mutation(
        invocation_ref,
        invocation_digest,
        status=manifest["status"],
        sufficient=sufficient,
    )
    state = {
        **action,
        **manifest,
        **_CLOSED_FLAGS,
        "owner": "FollowupAuthorInvocationConstructionRuntime",
        "canonical_state": False,
        "ad_author_payload_envelope_consumed": True,
        "packet_authority_consumed": True,
        "author_evidence_content_bridge_consumed": bool(bridge),
        "author_invocation_constructed": sufficient,
        "author_invocation_ready_for_model": sufficient,
        **_ad_bound_fields(ad),
        **_upstream_projection_digests(upstreams),
        **_bridge_state_fields(bridge),
        "ag96i3_author_invocation_ref": safe_json(invocation_ref),
        "ag96i3_author_invocation_digest": invocation_digest,
        "invocation_manifest": safe_json(manifest),
        "invocation_manifest_digest": _digest(manifest),
        "invocation_manifest_length": len(repr(safe_json(manifest))),
        "packet_mutation": safe_json(mutation),
        "final_answer_authority_projection_mutation": safe_json(mutation),
        "updated_final_answer_packet_digest": _digest(updated_with_mutation(packet, mutation)),
        "updated_final_answer_authority_projection_digest": _digest(updated_with_mutation(authority, mutation)),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorInvocationConstructionRecord(safe_json(state))


def build_run_kernel_followup_author_invocation_construction_state(
    *,
    invocation_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **safe_mapping(invocation_record_state),
        "owner": "RunKernel.FollowupAuthorInvocationConstruction",
        "canonical_state": True,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_invocation_construction_state(invocation_state=state)
    return safe_json(state)


def validate_run_kernel_followup_author_invocation_construction_state(
    *,
    invocation_state: Mapping[str, Any],
) -> None:
    state = safe_mapping(invocation_state)
    require(state.get("owner") == "RunKernel.FollowupAuthorInvocationConstruction", "AF4a owner")
    require(state.get("canonical_state") is True, "AF4a canonical state")
    status = state.get("status")
    require(
        status
        in {
            FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS,
            FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
        },
        "AF4 invocation status",
    )
    if status == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS:
        require(state.get("author_evidence_content_sufficient") is True, "AF4C sufficient content")
        require(state.get("author_invocation_constructed") is True, "AF4C constructed")
        require(state.get("author_invocation_ready_for_model") is True, "AF4C model-ready manifest")
        require(state.get("af4b2_author_evidence_content_bridge_digest"), "AF4C bridge digest")
        require(state.get("sanitized_author_evidence_content_payload_digest"), "AF4C content payload digest")
        require(state.get("answer_bearing_sanitized_excerpt_refs"), "AF4C excerpt refs")
    else:
        require(state.get("author_evidence_content_sufficient") is False, "AF4a insufficient content")
        require(bool(state.get("missing_author_evidence_content_refs")), "AF4a missing content refs")
        require(state.get("author_invocation_constructed") is False, "AF4a blocked construction")
        require(state.get("author_invocation_ready_for_model") is False, "AF4a blocked model readiness")
    require(set(safe_mapping(state.get("packet_mutation"))) == AF4_PACKET_MUTATION_FIELDS, "AF4a packet mutation keys")
    _validate_closed(state)
    _reject_forbidden_payload(state)


def build_followup_author_invocation_construction_projection(
    *,
    invocation_state: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    state = safe_mapping(invocation_state)
    projection = {
        "owner": "RunKernel.FollowupAuthorInvocationConstruction",
        "canonical_state": True,
        "status": state.get("status"),
        "author_invocation_construction_mode": state.get(
            "author_invocation_construction_mode"
        ),
        "author_invocation_construction_id": state.get("author_invocation_construction_id"),
        "author_evidence_content_sufficient": state.get(
            "author_evidence_content_sufficient"
        ),
        "author_invocation_constructed": state.get("author_invocation_constructed"),
        "author_invocation_ready_for_model": state.get(
            "author_invocation_ready_for_model"
        ),
        "missing_author_evidence_content": state.get("missing_author_evidence_content"),
        "missing_author_evidence_content_refs": state.get("missing_author_evidence_content_refs"),
        "source_identity_only_refs": state.get("source_identity_only_refs"),
        **_bridge_projection_fields(state),
        "ag96i3_author_invocation_ref": state.get("ag96i3_author_invocation_ref"),
        "ag96i3_author_invocation_digest": state.get("ag96i3_author_invocation_digest"),
        "prompt_invocation_digest": None,
        "prompt_invocation_length": 0,
        **_CLOSED_FLAGS,
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_invocation_construction_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_invocation_state: Mapping[str, Any],
) -> None:
    observed = safe_mapping(observed_invocation_state)
    _validate_closed(observed)
    for field, expected in safe_mapping(action_inputs).items():
        require(observed.get(field) == expected, f"AF4a observation {field} mismatch")
    _reject_forbidden_payload(observed)


def af4_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return projection_from_record_mutation(
        current_packet,
        record_state,
        "packet",
        "packet_mutation",
        AF4_PACKET_MUTATION_FIELDS,
        "current_final_answer_packet_digest",
        "AF4a mutation mismatch",
        "AF4a stale packet",
        _validate_projection_update,
    )


def af4_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return projection_from_record_mutation(
        current_projection,
        record_state,
        "authority",
        "final_answer_authority_projection_mutation",
        AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection_digest",
        "AF4a authority mutation mismatch",
        "AF4a stale authority projection",
        _validate_projection_update,
    )


def _validate_ad(ad: Mapping[str, Any], projection: Mapping[str, Any], runtime_inputs: Mapping[str, Any]) -> None:
    history = _history(runtime_inputs, "followup_author_payload_construction")
    require(ad, "AF4a requires AD payload envelope state")
    validate_run_kernel_followup_author_payload_construction_state(payload_construction_state=ad)
    require(projection.get("owner") == "RunKernel.FollowupAuthorPayloadConstruction", "AF4a AD projection owner")
    require(projection.get("canonical_state") is True, "AF4a canonical AD projection")
    require(history and history[-1] == projection, "AF4a current AD history")
    require(ad.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS, "AF4a AD status")
    require(ad.get("payload_envelope_mode") == AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE, "AF4a AD mode")
    require(ad.get("payload_envelope_ref_status") == FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS, "AF4a AD ref status")
    require(ad.get("ag96i3_author_payload_digest") == _digest(safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))), "AF4a AD envelope ref digest")


def _validate_upstreams(ad: Mapping[str, Any], upstreams: Mapping[str, Mapping[str, Any]]) -> None:
    for key, _, state_id, ad_id, ad_digest in _BINDINGS:
        require(ad.get(ad_id) == upstreams[key].get(state_id), f"AF4a {key} id")
        require(ad.get(ad_digest) == _digest(upstreams[key]), f"AF4a {key} digest")


def _validate_packet(
    action: Mapping[str, Any],
    ad: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    u1: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> None:
    legacy_ref, author_input_refs = validate_packet_projection_base(
        packet,
        authority,
        u1,
        "AF4a",
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AF4a packet/authority payload ref mismatch",
        "AF4a U1 payload ref mismatch",
    )
    require(legacy_ref.get("status") != "author_input_ready", "AF4a rejects ready ref")
    envelope_ref = safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))
    require(packet.get("ag96i3_author_payload_envelope_ref") == envelope_ref, "AF4a packet AD envelope ref")
    require(authority.get("ag96i3_author_payload_envelope_ref") == envelope_ref, "AF4a authority AD envelope ref")
    require(packet.get("ag96i3_author_payload_digest") == ad.get("ag96i3_author_payload_digest"), "AF4a packet AD digest")
    require(authority.get("ag96i3_author_payload_digest") == ad.get("ag96i3_author_payload_digest"), "AF4a authority AD digest")
    current_source = safe_mapping(bridge.get("state")) if bridge else ad
    source_label = "AF4C stale packet from AF4B2" if bridge else "AF4a stale packet from AD"
    authority_label = (
        "AF4C stale authority projection from AF4B2"
        if bridge
        else "AF4a stale authority projection from AD"
    )
    validate_packet_authority_currentness(
        packet,
        authority,
        current_source,
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        source_label,
        authority_label,
    )
    validate_no_existing_prefixed_fields(
        packet,
        authority,
        AF4_PACKET_MUTATION_FIELDS,
        "ag96i3_author_invocation",
        "AF4a packet already has author invocation",
        "AF4a authority already has author invocation",
    )
    expected = build_followup_author_invocation_construction_action_inputs(
        followup_author_payload_construction_state=ad,
        followup_author_payload_construction_projection={},
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
        followup_author_evidence_content_bridge_state=bridge.get("state"),
        followup_author_evidence_content_bridge_projection=bridge.get("projection"),
        followup_author_evidence_content_bridge_history=bridge.get("history"),
    )
    validate_expected_action_fields(
        action,
        expected,
        (
            "current_final_answer_packet_digest",
            "final_answer_authority_projection_digest",
            "author_input_refs_digest",
            "legacy_author_payload_ref_status",
            "payload_envelope_digest",
            "payload_envelope_ref_digest",
            "ad_payload_construction_digest",
        ),
        "AF4a",
    )
    require(author_input_refs.get("status") == FOLLOWUP_AUTHOR_INPUT_REFS_STATUS, "AF4a U1 refs status")


def _current_upstreams(runtime_inputs: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, prefix, *_ in _BINDINGS:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4a requires {key} state")
        require(projection.get("canonical_state") is True, f"AF4a {key} projection")
        require(history and history[-1] == projection, f"AF4a {key} history")
        out[key] = state
        out[f"{key}_projection"] = projection
    return out


def _validate_bridge(
    ad: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    state = safe_mapping(runtime_inputs.get("followup_author_evidence_content_bridge_state"))
    projection = safe_mapping(runtime_inputs.get("followup_author_evidence_content_bridge_projection"))
    history = _history(runtime_inputs, "followup_author_evidence_content_bridge")
    if not (state or projection or history):
        return {}
    require(state and projection and history, "AF4C requires current AF4B2 bridge state/projection/history")
    validate_run_kernel_followup_author_evidence_content_bridge_state(
        bridge_state=state
    )
    require(projection.get("owner") == "RunKernel.FollowupAuthorEvidenceContentBridge", "AF4C AF4B2 projection owner")
    require(projection.get("canonical_state") is True, "AF4C canonical AF4B2 projection")
    require(history[-1] == projection, "AF4C current AF4B2 history")
    require(state.get("ad_payload_construction_digest") == _digest(ad), "AF4C AF4B2 stale AD")
    require(state.get("content_bridge_digest") == projection.get("content_bridge_digest"), "AF4C AF4B2 bridge digest")
    require(
        state.get("content_bridge_digest")
        == _digest(safe_mapping(state.get("content_bridge_ref"))),
        "AF4C stale AF4B2 bridge ref digest",
    )
    payload = safe_mapping_sequence(state.get("sanitized_author_evidence_content_payload"))
    payload_digest = _digest({"payload": payload})
    payload_ref = safe_mapping(state.get("sanitized_author_evidence_content_payload_ref"))
    require(
        state.get("sanitized_author_evidence_content_payload_digest")
        == payload_digest,
        "AF4C stale AF4B2 content payload digest",
    )
    require(
        payload_ref.get("payload_digest") == payload_digest,
        "AF4C stale AF4B2 content payload ref",
    )
    require(_digest(packet) == state.get("updated_final_answer_packet_digest"), "AF4C stale packet from AF4B2")
    require(
        _digest(authority)
        == state.get("updated_final_answer_authority_projection_digest"),
        "AF4C stale authority projection from AF4B2",
    )
    _validate_bridge_bound_inputs(state, runtime_inputs)
    sufficient = (
        state.get("status") == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS
        and state.get("author_evidence_content_sufficient") is True
    )
    if state.get("status") == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS:
        require(state.get("author_evidence_content_sufficient") is False, "AF4C blocked AF4B2 sufficiency")
    return {
        "state": state,
        "projection": projection,
        "history": history,
        "sufficient": sufficient,
        "payload_ref": payload_ref,
        "payload_digest": payload_digest,
        "bridge_ref": safe_mapping(state.get("content_bridge_ref")),
        "bridge_digest": state.get("content_bridge_digest"),
        "excerpt_refs": safe_mapping_sequence(
            state.get("answer_bearing_sanitized_excerpt_refs")
        ),
    }


def _validate_bridge_bound_inputs(
    bridge_state: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> None:
    for key, prefix, *_ in _BINDINGS:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        require(bridge_state.get(f"{key}_ad_bound_digest") == _digest(state), f"AF4C AF4B2 {key} digest")
        require(bridge_state.get(f"{key}_projection_digest") == _digest(projection), f"AF4C AF4B2 {key} projection")
    for key, prefix, id_field in _U1_CHAIN:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4C requires {key} state")
        require(projection.get("canonical_state") is True, f"AF4C {key} projection")
        require(history and history[-1] == projection, f"AF4C {key} history")
        require(bridge_state.get(f"{key}_u1_bound_id") == state.get(id_field), f"AF4C AF4B2 {key} id")
        require(bridge_state.get(f"{key}_u1_bound_digest") == _digest(state), f"AF4C AF4B2 {key} digest")
        require(bridge_state.get(f"{key}_projection_digest") == _digest(projection), f"AF4C AF4B2 {key} projection")


def _missing_content_refs(
    ad: Mapping[str, Any],
    u1: Mapping[str, Any],
    bridge: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bridge_state = safe_mapping((bridge or {}).get("state"))
    if bridge_state.get("status") == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS:
        missing = [
            {
                "class": ANSWER_BEARING_SANITIZED_EXCERPT,
                "ref": "af4b2.author_evidence_content_bridge",
                "reason": "af4b2_bridge_blocked_missing_sanitized_excerpt",
            }
        ]
        return safe_json(missing), safe_mapping_sequence(
            bridge_state.get("source_identity_only_refs")
        )
    refs = safe_mapping_sequence(ad.get("allowed_evidence_refs")) + safe_mapping_sequence(u1.get("author_allowed_evidence_refs"))
    refs = refs or [{"ref": "ad.allowed_evidence_refs"}]
    missing = [
        {
            "class": "answer_bearing_sanitized_excerpt",
            "ref": _ref_id(ref),
            "reason": "ad_author_payload_contains_refs_or_digests_not_excerpt_text",
        }
        for ref in refs
    ]
    identity = [
        {key: ref.get(key) for key in ("evidence_id", "candidate_id", "source_id", "status") if ref.get(key) not in (None, "", [], {})}
        for ref in refs
    ]
    return safe_json(missing), safe_json(identity)


def _invocation_mutation(
    invocation_ref: Mapping[str, Any],
    digest: str,
    *,
    status: str,
    sufficient: bool,
) -> dict[str, Any]:
    return {
        "ag96i3_author_invocation_ref": safe_json(invocation_ref),
        "ag96i3_author_invocation_ref_created": True,
        "ag96i3_author_invocation_status": status,
        "ag96i3_author_invocation_digest": digest,
        "ag96i3_author_invocation_content_sufficient": sufficient,
        **_CLOSED_FLAGS,
    }


def _bridge_action_fields(
    *,
    bridge_state: Mapping[str, Any] | None,
    bridge_projection: Mapping[str, Any] | None,
    bridge_history: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    state = safe_mapping(bridge_state)
    projection = safe_mapping(bridge_projection)
    history = [safe_mapping(item) for item in bridge_history or []]
    if not (state and projection and history and history[-1] == projection):
        return {}
    refs = safe_mapping_sequence(state.get("answer_bearing_sanitized_excerpt_refs"))
    payload_ref = safe_mapping(state.get("sanitized_author_evidence_content_payload_ref"))
    return {
        "af4b2_author_evidence_content_bridge_id": state.get("author_evidence_content_bridge_id"),
        "af4b2_author_evidence_content_status": state.get("status"),
        "af4b2_author_evidence_content_sufficient": state.get("author_evidence_content_sufficient") is True,
        "af4b2_author_evidence_content_bridge_digest": state.get("content_bridge_digest"),
        "af4b2_author_evidence_content_projection_digest": _digest(projection),
        "af4b2_sanitized_content_payload_ref_digest": _digest(payload_ref),
        "af4b2_sanitized_content_payload_digest": state.get("sanitized_author_evidence_content_payload_digest"),
        "af4b2_answer_bearing_sanitized_excerpt_ref_count": len(refs),
    }


def _bridge_state_fields(bridge: Mapping[str, Any]) -> dict[str, Any]:
    if not bridge:
        return {}
    state = safe_mapping(bridge.get("state"))
    return {
        "af4b2_author_evidence_content_bridge_id": state.get("author_evidence_content_bridge_id"),
        "af4b2_author_evidence_content_status": state.get("status"),
        "af4b2_author_evidence_content_bridge_ref": bridge.get("bridge_ref"),
        "af4b2_author_evidence_content_bridge_digest": bridge.get("bridge_digest"),
        "sanitized_author_evidence_content_payload_ref": bridge.get("payload_ref"),
        "sanitized_author_evidence_content_payload_digest": bridge.get("payload_digest"),
        "answer_bearing_sanitized_excerpt_refs": bridge.get("excerpt_refs"),
    }


def _bridge_projection_fields(state: Mapping[str, Any]) -> dict[str, Any]:
    if not state.get("author_evidence_content_bridge_consumed"):
        return {}
    return {
        "author_evidence_content_bridge_consumed": True,
        "af4b2_author_evidence_content_bridge_id": state.get("af4b2_author_evidence_content_bridge_id"),
        "af4b2_author_evidence_content_status": state.get("af4b2_author_evidence_content_status"),
        "af4b2_author_evidence_content_bridge_digest": state.get("af4b2_author_evidence_content_bridge_digest"),
        "sanitized_author_evidence_content_payload_ref": state.get("sanitized_author_evidence_content_payload_ref"),
        "sanitized_author_evidence_content_payload_digest": state.get("sanitized_author_evidence_content_payload_digest"),
        "answer_bearing_sanitized_excerpt_refs": state.get("answer_bearing_sanitized_excerpt_refs"),
    }


def _invocation_manifest(
    *,
    action: Mapping[str, Any],
    ad: Mapping[str, Any],
    bridge: Mapping[str, Any],
    missing_refs: Sequence[Mapping[str, Any]],
    identity_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    sufficient = bridge.get("sufficient") is True
    mode = (
        AG96I3AF4C_BRIDGE_CONSUMING_AUTHOR_INVOCATION_MODEL_CLOSED_MODE
        if bridge
        else AG96I3AF4_AD_BOUND_AUTHOR_INVOCATION_MODEL_CLOSED_MODE
    )
    status = (
        FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
        if sufficient
        else FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS
    )
    manifest = {
        "mode": mode,
        "status": status,
        "payload_envelope_id": action.get("payload_envelope_id"),
        "payload_envelope_digest": action.get("payload_envelope_digest"),
        "author_evidence_content_sufficient": sufficient,
        "missing_author_evidence_content": [] if sufficient else [ANSWER_BEARING_SANITIZED_EXCERPT],
        "missing_author_evidence_content_refs": [] if sufficient else safe_json(missing_refs),
        "source_identity_only_refs": safe_json(identity_refs),
        "prompt_invocation_digest": None,
        "prompt_invocation_length": 0,
    }
    if bridge:
        manifest.update(
            {
                "ad_payload_envelope_ref": safe_mapping(
                    ad.get("ag96i3_author_payload_envelope_ref")
                ),
                "ad_payload_construction_digest": action.get("ad_payload_construction_digest"),
                "rendered_source_entries_refs_or_digest": safe_mapping(
                    ad.get("rendered_source_entries_refs_or_digest")
                ),
                "mandatory_caveats_refs_or_digest": safe_mapping(
                    ad.get("mandatory_caveats_refs_or_digest")
                ),
                "prohibited_upgrades_refs_or_digest": safe_mapping(
                    ad.get("prohibited_upgrades_refs_or_digest")
                ),
                "source_bound_unknowns_refs_or_digest": safe_mapping(
                    ad.get("source_bound_unknowns_refs_or_digest")
                ),
                "closed_model_product_final_citation_flags": _manifest_closed_flags(),
                "af4b2_author_evidence_content_bridge_ref": bridge.get("bridge_ref"),
                "af4b2_author_evidence_content_bridge_digest": bridge.get("bridge_digest"),
                "sanitized_author_evidence_content_payload_ref": bridge.get("payload_ref"),
                "sanitized_author_evidence_content_payload_digest": bridge.get("payload_digest"),
                "answer_bearing_sanitized_excerpt_refs": bridge.get("excerpt_refs"),
                "answer_bearing_sanitized_excerpt_ref_count": len(bridge.get("excerpt_refs") or []),
                "binding_proof": {
                    "ad_payload_construction_digest": action.get("ad_payload_construction_digest"),
                    "af4b2_author_evidence_content_bridge_digest": bridge.get("bridge_digest"),
                    "sanitized_author_evidence_content_payload_digest": bridge.get("payload_digest"),
                    "af4b2_projection_digest": action.get("af4b2_author_evidence_content_projection_digest"),
                },
            }
        )
    return safe_json(manifest)


def _invocation_ref_id(action: Mapping[str, Any], sufficient: bool) -> str:
    prefix = "ag96i3-af4c-constructed" if sufficient else "ag96i3-af4a-blocked"
    return f"{prefix}:{action.get('payload_envelope_id')}"


def _manifest_closed_flags() -> dict[str, bool]:
    return {
        "model_execution_allowed": False,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "author_observation_created": False,
        "final_answer_outcome_created": False,
        "prompt_text_retained": False,
        "model_response_retained": False,
        "report_text_retained": False,
        "final_text_retained": False,
        "product_answer_ready": False,
        "citation_strings_included": False,
        "ordered_product_source_output_created": False,
    }


def _ad_bound_fields(ad: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"{key}_ad_bound_{suffix}": ad.get(field)
        for key, _, _, id_field, digest_field in _BINDINGS
        for suffix, field in (("id", id_field), ("digest", digest_field))
    }


def _upstream_projection_digests(upstreams: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {f"{key}_projection_digest": _digest(upstreams[f"{key}_projection"]) for key, *_ in _BINDINGS}


def _validate_closed(state: Mapping[str, Any]) -> None:
    for field, expected in _CLOSED_FLAGS.items():
        require(state.get(field) is expected, f"AF4a {field} must be {expected}")


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            require(str(key or "").casefold() not in _FORBIDDEN_PAYLOAD_KEYS, f"AF4a cannot retain {key!r}")
            _reject_forbidden_payload(child)
    elif isinstance(value, list | tuple):
        for child in value:
            _reject_forbidden_payload(child)


def _history(runtime_inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [safe_mapping(item) for item in runtime_inputs.get(f"{prefix}_history", [])]


def _ref_id(ref: Mapping[str, Any]) -> str:
    return str(ref.get("evidence_id") or ref.get("candidate_id") or ref.get("source_id") or ref.get("ref") or "unknown_author_evidence_ref")


def _invocation_id(ad: Mapping[str, Any]) -> str:
    return f"followup-author-invocation-construction:{ad.get('payload_envelope_id')}:{_digest(ad)[:16]}"
