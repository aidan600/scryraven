"""AG-96I3AF4B2 AD-consuming Author evidence-content bridge."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, Mapping, Sequence

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
    require,
    safe_mapping,
    safe_mapping_sequence,
    updated_with_mutation,
    validate_no_existing_prefixed_fields,
    validate_packet_authority_currentness,
    validate_packet_projection_base,
    validate_projection_update,
)
from core.followup_deliberation import clean_text, safe_json

FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE = "followup_author_evidence_content_bridge"
AG96I3AF4B2_AD_CONSUMING_AUTHOR_EVIDENCE_CONTENT_MODEL_CLOSED_MODE = "ag96i3af4b2_ad_consuming_author_evidence_content_model_closed"
FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS = "author_evidence_content_bound_model_closed"
FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS = "author_evidence_content_blocked_missing_sanitized_excerpt_model_closed"
FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_REASON = AG96I3AF4B2_AD_CONSUMING_AUTHOR_EVIDENCE_CONTENT_MODEL_CLOSED_MODE
SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES = "sanitized_author_evidence_excerpt_candidates"
ANSWER_BEARING_SANITIZED_EXCERPT = "answer_bearing_sanitized_excerpt"
MAX_SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CHARS = 800

_NEW_FIELDS = """
ag96i3_author_evidence_content_bridge_ref
ag96i3_author_evidence_content_bridge_ref_created
ag96i3_author_evidence_content_status
ag96i3_author_evidence_content_bridge_digest
ag96i3_author_evidence_content_sufficient
""".split()
_CLOSED_FALSE_FIELDS = """
author_input_ready author_execution_allowed author_activation_allowed
model_execution_allowed real_model_called ask_model_called
execute_author_action_called author_observation_created
final_answer_outcome_created prompt_text_retained model_response_retained
report_text_retained final_text_retained final_text_included product_answer_ready
citation_strings_included ordered_product_source_output_created
""".split()
_CLOSED_FLAGS = {field: False for field in _CLOSED_FALSE_FIELDS} | {"author_execution_deferred": True}
AF4B2_PACKET_MUTATION_FIELDS = frozenset([*_NEW_FIELDS, *_CLOSED_FLAGS])
AF4B2_AUTHORITY_PROJECTION_MUTATION_FIELDS = AF4B2_PACKET_MUTATION_FIELDS
_FORBIDDEN_KEYS = frozenset("raw_text source_text provider_payload raw_provider_payload raw_prompt prompt_text model_response report_text final_answer_text product_output db_row cache private_log full_trace secret api_key".split())
_CALLER_CONTROLLED_KEYS = frozenset(
    {
        *AF4B2_PACKET_MUTATION_FIELDS,
        "answer_bearing_sanitized_excerpt_refs",
        "content_bridge_ref",
        "followup_author_evidence_content_bridge_history",
        "followup_author_evidence_content_bridge_projection",
        "followup_author_evidence_content_bridge_state",
        "missing_author_evidence_content",
        "packet_mutation",
        "sanitized_author_evidence_content_payload",
        "source_identity_only_refs",
    }
)
_PRIVATE_VALUE_MARKERS = ("api_key", "authorization:", "bearer ", "raw_provider_payload", "raw prompt", "sk-")
_AD_BINDINGS = (
    ("ac", "followup_author_payload_authority", "payload_authority_id", "ac_payload_authority_id", "ac_payload_authority_digest"),
    ("z", "followup_author_prompt_assembly_manifest", "author_prompt_assembly_manifest_id", "z_author_prompt_assembly_manifest_id", "z_author_prompt_assembly_manifest_digest"),
    ("y", "followup_author_execution_activation", "author_execution_activation_id", "y_author_execution_activation_id", "y_author_execution_activation_digest"),
    ("x", "followup_author_input_materialization", "author_input_materialization_id", "x_author_input_materialization_id", "x_author_input_materialization_digest"),
    ("w", "followup_author_execution_readiness", "author_execution_readiness_id", "w_author_execution_readiness_id", "w_author_execution_readiness_digest"),
    ("v1", "followup_author_gate", "author_gate_id", "v1_author_gate_id", "v1_author_gate_digest"),
    ("u1", "followup_author_input_authority", "author_input_authority_id", "u1_authority_id", "u1_authority_digest"),
)
_U1_CHAIN = (
    ("p1", "followup_final_evidence_selection", "final_evidence_selection_id"),
    ("q1", "followup_citation_eligibility", "citation_eligibility_id"),
    ("r1", "followup_citation_source_handoff", "citation_source_handoff_id"),
    ("t1", "followup_citation_rendering", "citation_rendering_id"),
)
_PROJECTED_FROM_STATE = """
status author_evidence_content_bridge_id author_evidence_content_sufficient
answer_bearing_sanitized_excerpt_refs
sanitized_author_evidence_content_payload_ref
sanitized_author_evidence_content_payload_digest missing_author_evidence_content
source_identity_only_refs content_bridge_ref content_bridge_digest
ag96i3_author_evidence_content_bridge_ref
ag96i3_author_evidence_content_bridge_digest
ag96i3_author_evidence_content_status ag96i3_author_evidence_content_sufficient
current_final_answer_packet_digest final_answer_authority_projection_digest
updated_final_answer_packet_digest
updated_final_answer_authority_projection_digest
""".split()
_validate_projection_update = partial(
    validate_projection_update,
    allowed_mutation_fields=AF4B2_PACKET_MUTATION_FIELDS,
    phase_label="AF4B2",
    ref_field="ag96i3_author_evidence_content_bridge_ref",
    ref_label="Author evidence content bridge ref",
    author_payload_ref_status=FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorEvidenceContentBridgeRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return safe_mapping(self.state)


def reject_followup_author_evidence_content_bridge_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    raw = dict(inputs or {}) if isinstance(inputs, Mapping) else {}
    for key in raw:
        token = _token(key)
        if token != SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES:
            raise PermissionError("AF4B2 accepts only sanitized_author_evidence_excerpt_candidates")
        if token in _CALLER_CONTROLLED_KEYS:
            raise PermissionError(f"AF4B2 cannot accept caller-supplied {key!r}")
    _reject_forbidden_payload(raw)


def build_followup_author_evidence_content_bridge_action_inputs(
    *,
    followup_author_payload_construction_state: Mapping[str, Any],
    followup_author_payload_construction_projection: Mapping[str, Any],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    sanitized_author_evidence_excerpt_candidates: Any = None,
    **_: Any,
) -> dict[str, Any]:
    ad = safe_mapping(followup_author_payload_construction_state)
    packet = safe_mapping(final_answer_packet)
    authority = safe_mapping(final_answer_authority_projection)
    candidates = _candidate_inputs(sanitized_author_evidence_excerpt_candidates)
    sufficient = any(_excerpt_text(item) for item in candidates)
    status = FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS if sufficient else FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS
    return {
        "run_id": ad.get("run_id"),
        "checkpoint_id": ad.get("checkpoint_id"),
        "packet_id": packet.get("packet_id"),
        "author_evidence_content_bridge_id": _bridge_id(ad),
        "author_evidence_content_bridge_mode": AG96I3AF4B2_AD_CONSUMING_AUTHOR_EVIDENCE_CONTENT_MODEL_CLOSED_MODE,
        "status": status,
        "payload_envelope_id": ad.get("payload_envelope_id"),
        "payload_envelope_digest": ad.get("ag96i3_author_payload_digest"),
        "payload_envelope_ref_digest": _digest(safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))),
        "ad_payload_construction_digest": _digest(ad),
        "ad_payload_construction_projection_digest": _digest(safe_mapping(followup_author_payload_construction_projection)),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "author_input_refs_digest": _digest(safe_mapping(packet.get("author_input_refs"))),
        "legacy_author_payload_ref_status": safe_mapping(packet.get("author_payload_ref")).get("status"),
        "author_evidence_content_sufficient": sufficient,
        SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES: safe_json(candidates),
    }


def build_followup_author_evidence_content_bridge_record(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> FollowupAuthorEvidenceContentBridgeRecord:
    action = safe_mapping(action_inputs)
    ad = safe_mapping(runtime_inputs.get("followup_author_payload_construction_state"))
    packet = safe_mapping(runtime_inputs.get("final_answer_packet"))
    authority = safe_mapping(runtime_inputs.get("final_answer_authority_projection"))
    upstreams = _validate_runtime(action, ad, packet, authority, runtime_inputs)
    refs, payload, missing, identities = _bound_content(action, ad, upstreams["u1"])
    sufficient = bool(payload)
    status = FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS if sufficient else FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS
    require(action.get("status") == status, "AF4B2 action status mismatch")
    payload_digest = _digest({"payload": payload})
    payload_ref = {
        "content_payload_ref_id": f"ag96i3-af4b2-content:{action.get('author_evidence_content_bridge_id')}",
        "content_class": ANSWER_BEARING_SANITIZED_EXCERPT,
        "sanitization_status": "sanitized",
        "excerpt_count": len(payload),
        "payload_digest": payload_digest,
        "payload_resolves_in_canonical_bridge_state": sufficient,
    }
    bridge_ref = {
        "author_evidence_content_bridge_ref_id": f"ag96i3-af4b2-author-evidence-content:{action.get('payload_envelope_id')}",
        "mode": AG96I3AF4B2_AD_CONSUMING_AUTHOR_EVIDENCE_CONTENT_MODEL_CLOSED_MODE,
        "status": status,
        "packet_id": action.get("packet_id"),
        "payload_envelope_id": action.get("payload_envelope_id"),
        "payload_envelope_digest": action.get("payload_envelope_digest"),
        "ad_payload_construction_digest": action.get("ad_payload_construction_digest"),
        "author_evidence_content_sufficient": sufficient,
        "answer_bearing_sanitized_excerpt_refs": refs,
        "sanitized_author_evidence_content_payload_ref": payload_ref,
        "missing_author_evidence_content": missing,
        "source_identity_only_refs": identities,
        "bounded_sanitized_excerpt_text_retained": sufficient,
        "content_recovered_or_fetched": False,
        "evidence_selection_changed": False,
        **_CLOSED_FLAGS,
    }
    bridge_digest = _digest(bridge_ref)
    mutation = _bridge_mutation(bridge_ref, bridge_digest, status, sufficient)
    state = {
        **{
            key: value
            for key, value in action.items()
            if key != SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES
        },
        "schema_version": "followup_author_evidence_content_bridge_ag96i3af4b2_v1",
        "record_type": "followup_author_evidence_content_bridge_record",
        "owner": "FollowupAuthorEvidenceContentBridgeRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "content_bridge_ref": bridge_ref,
        "content_bridge_digest": bridge_digest,
        "ag96i3_author_evidence_content_bridge_ref": bridge_ref,
        "ag96i3_author_evidence_content_bridge_digest": bridge_digest,
        "ag96i3_author_evidence_content_status": status,
        "ag96i3_author_evidence_content_sufficient": sufficient,
        "answer_bearing_sanitized_excerpt_refs": refs,
        "sanitized_author_evidence_content_payload": payload,
        "sanitized_author_evidence_content_payload_ref": payload_ref,
        "sanitized_author_evidence_content_payload_digest": payload_digest,
        "missing_author_evidence_content": missing,
        "source_identity_only_refs": identities,
        "bounded_sanitized_excerpt_text_retained": sufficient,
        "content_recovered_or_fetched": False,
        "evidence_selection_changed": False,
        "ad_author_payload_envelope_consumed": True,
        "packet_authority_consumed": True,
        **_CLOSED_FLAGS,
        **_ad_bound_fields(ad),
        **_upstream_projection_digests(upstreams),
        **_u1_chain_digests(runtime_inputs),
        "packet_mutation": mutation,
        "final_answer_authority_projection_mutation": mutation,
        "updated_final_answer_packet_digest": _digest(updated_with_mutation(packet, mutation)),
        "updated_final_answer_authority_projection_digest": _digest(
            updated_with_mutation(authority, mutation)
        ),
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorEvidenceContentBridgeRecord(safe_json(state))


def build_run_kernel_followup_author_evidence_content_bridge_state(
    *,
    bridge_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **safe_mapping(bridge_record_state),
        "owner": "RunKernel.FollowupAuthorEvidenceContentBridge",
        "canonical_state": True,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_evidence_content_bridge_state(bridge_state=state)
    return safe_json(state)


def validate_run_kernel_followup_author_evidence_content_bridge_state(
    *,
    bridge_state: Mapping[str, Any],
) -> None:
    state = safe_mapping(bridge_state)
    require(state.get("owner") == "RunKernel.FollowupAuthorEvidenceContentBridge", "AF4B2 owner")
    require(state.get("canonical_state") is True, "AF4B2 canonical state")
    status = state.get("status")
    require(status in {FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS, FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS}, "AF4B2 status")
    if status == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS:
        require(state.get("author_evidence_content_sufficient") is True, "AF4B2 sufficient content")
        require(state.get("answer_bearing_sanitized_excerpt_refs"), "AF4B2 bound refs")
        require(state.get("sanitized_author_evidence_content_payload"), "AF4B2 content payload")
    else:
        require(state.get("author_evidence_content_sufficient") is False, "AF4B2 blocked content")
        require(state.get("missing_author_evidence_content") == [ANSWER_BEARING_SANITIZED_EXCERPT], "AF4B2 missing sanitized excerpt")
    require(set(safe_mapping(state.get("packet_mutation"))) == AF4B2_PACKET_MUTATION_FIELDS, "AF4B2 packet mutation keys")
    _validate_closed(state)
    _reject_forbidden_payload(state)


def build_followup_author_evidence_content_bridge_projection(
    *,
    bridge_state: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    state = safe_mapping(bridge_state)
    projection = {
        "owner": "RunKernel.FollowupAuthorEvidenceContentBridge",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "author_evidence_content_bridge_mode": AG96I3AF4B2_AD_CONSUMING_AUTHOR_EVIDENCE_CONTENT_MODEL_CLOSED_MODE,
        **{field: state.get(field) for field in _PROJECTED_FROM_STATE},
        **_lineage_fields(state),
        **_CLOSED_FLAGS,
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_evidence_content_bridge_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_bridge_state: Mapping[str, Any],
) -> None:
    action = safe_mapping(action_inputs)
    observed = safe_mapping(observed_bridge_state)
    _validate_closed(observed)
    for field, expected in action.items():
        if field == SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES:
            continue
        require(observed.get(field) == expected, f"AF4B2 observation {field} mismatch")
    _reject_forbidden_payload(observed)


def af4b2_packet_projection_from_record(
    *,
    current_packet: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return projection_from_record_mutation(
        current_packet,
        record_state,
        "packet",
        "packet_mutation",
        AF4B2_PACKET_MUTATION_FIELDS,
        "current_final_answer_packet_digest",
        "AF4B2 mutation mismatch",
        "AF4B2 stale packet",
        _validate_projection_update,
    )


def af4b2_authority_projection_from_record(
    *,
    current_projection: Mapping[str, Any],
    record_state: Mapping[str, Any],
) -> dict[str, Any]:
    return projection_from_record_mutation(
        current_projection,
        record_state,
        "authority",
        "final_answer_authority_projection_mutation",
        AF4B2_AUTHORITY_PROJECTION_MUTATION_FIELDS,
        "final_answer_authority_projection_digest",
        "AF4B2 authority mutation mismatch",
        "AF4B2 stale authority projection",
        _validate_projection_update,
    )


def _validate_runtime(
    action: Mapping[str, Any],
    ad: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    ad_projection = safe_mapping(
        runtime_inputs.get("followup_author_payload_construction_projection")
    )
    history = _history(runtime_inputs, "followup_author_payload_construction")
    require(ad, "AF4B2 requires AD payload envelope state")
    validate_run_kernel_followup_author_payload_construction_state(
        payload_construction_state=ad
    )
    require(ad_projection.get("canonical_state") is True, "AF4B2 canonical AD projection")
    require(history and history[-1] == ad_projection, "AF4B2 current AD history")
    require(ad.get("status") == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS, "AF4B2 AD status")
    require(ad.get("payload_envelope_mode") == AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE, "AF4B2 AD mode")
    require(ad.get("payload_envelope_ref_status") == FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS, "AF4B2 AD ref status")
    require(ad.get("ag96i3_author_payload_digest") == _digest(safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))), "AF4B2 AD ref digest")

    upstreams = _current_upstreams(runtime_inputs)
    for key, _, state_id, ad_id, ad_digest in _AD_BINDINGS:
        require(ad.get(ad_id) == upstreams[key].get(state_id), f"AF4B2 {key} id")
        require(ad.get(ad_digest) == _digest(upstreams[key]), f"AF4B2 {key} digest")
    _validate_u1_chain(upstreams["u1"], runtime_inputs)
    _validate_packet(action, ad, packet, authority, upstreams["u1"])
    expected = build_followup_author_evidence_content_bridge_action_inputs(
        followup_author_payload_construction_state=ad,
        followup_author_payload_construction_projection=ad_projection,
        final_answer_packet=packet,
        final_answer_authority_projection=authority,
        sanitized_author_evidence_excerpt_candidates=action.get(
            SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES
        ),
    )
    require(action == expected, "AF4B2 action must match canonical AD inputs")
    return upstreams


def _validate_packet(
    action: Mapping[str, Any],
    ad: Mapping[str, Any],
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
    u1: Mapping[str, Any],
) -> None:
    _, author_input_refs = validate_packet_projection_base(
        packet,
        authority,
        u1,
        "AF4B2",
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
        FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
        "AF4B2 packet/authority payload ref mismatch",
        "AF4B2 U1 payload ref mismatch",
    )
    envelope_ref = safe_mapping(ad.get("ag96i3_author_payload_envelope_ref"))
    require(packet.get("ag96i3_author_payload_envelope_ref") == envelope_ref, "AF4B2 packet AD envelope ref")
    require(authority.get("ag96i3_author_payload_envelope_ref") == envelope_ref, "AF4B2 authority AD envelope ref")
    require(packet.get("ag96i3_author_payload_digest") == ad.get("ag96i3_author_payload_digest"), "AF4B2 packet AD digest")
    require(authority.get("ag96i3_author_payload_digest") == ad.get("ag96i3_author_payload_digest"), "AF4B2 authority AD digest")
    require(safe_mapping_sequence(ad.get("allowed_evidence_refs")) == safe_mapping_sequence(u1.get("author_allowed_evidence_refs")), "AF4B2 AD/U1 allowed evidence refs")
    validate_packet_authority_currentness(
        packet,
        authority,
        ad,
        "updated_final_answer_packet_digest",
        "updated_final_answer_authority_projection_digest",
        "AF4B2 stale packet from AD",
        "AF4B2 stale authority projection from AD",
    )
    validate_no_existing_prefixed_fields(
        packet,
        authority,
        AF4B2_PACKET_MUTATION_FIELDS,
        "ag96i3_author_evidence_content",
        "AF4B2 packet already has author evidence content",
        "AF4B2 authority already has author evidence content",
    )
    require(author_input_refs.get("status") == FOLLOWUP_AUTHOR_INPUT_REFS_STATUS, "AF4B2 U1 refs status")


def _current_upstreams(runtime_inputs: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, prefix, *_ in _AD_BINDINGS:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4B2 requires {key} state")
        require(projection.get("canonical_state") is True, f"AF4B2 {key} projection")
        require(history and history[-1] == projection, f"AF4B2 {key} history")
        out[key] = state
        out[f"{key}_projection"] = projection
    return out


def _validate_u1_chain(u1: Mapping[str, Any], runtime_inputs: Mapping[str, Any]) -> None:
    for label, prefix, id_field in _U1_CHAIN:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4B2 requires {label} state")
        require(projection.get("canonical_state") is True, f"AF4B2 {label} projection")
        require(history and history[-1] == projection, f"AF4B2 {label} history")
        require(u1.get(id_field) == state.get(id_field), f"AF4B2 {label} id mismatch")


def _bound_content(
    action: Mapping[str, Any],
    ad: Mapping[str, Any],
    u1: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    allowed = _allowed_refs(ad, u1)
    identities = [_identity_ref(ref) for ref in allowed]
    candidates = safe_mapping_sequence(
        action.get(SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CANDIDATES)
    )
    if not candidates:
        return [], [], [ANSWER_BEARING_SANITIZED_EXCERPT], safe_json(identities)
    seen: set[str] = set()
    refs: list[dict[str, Any]] = []
    payload: list[dict[str, Any]] = []
    for candidate in candidates:
        _reject_forbidden_payload(candidate)
        excerpt_ref_id = clean_text(candidate.get("excerpt_ref_id"), limit=220)
        require(excerpt_ref_id, "AF4B2 excerpt_ref_id required")
        require(excerpt_ref_id not in seen, "AF4B2 duplicate excerpt_ref_id")
        seen.add(excerpt_ref_id)
        text = _excerpt_text(candidate)
        if not text:
            continue
        require(candidate.get("content_class") == ANSWER_BEARING_SANITIZED_EXCERPT, "AF4B2 requires answer_bearing_sanitized_excerpt")
        require(candidate.get("sanitization_status") == "sanitized", "AF4B2 requires sanitized excerpt")
        char_limit = _candidate_char_limit(candidate)
        require(len(text) <= char_limit, "AF4B2 sanitized excerpt exceeds limit")
        allowed_ref = _matching_allowed_ref(candidate, allowed)
        caller_digest = clean_text(candidate.get("excerpt_digest"), limit=220)
        require(not caller_digest, "AF4B2 caller-supplied excerpt_digest rejected")
        allowed_citation_id = clean_text(allowed_ref.get("citation_id"), limit=220)
        caller_citation_id = clean_text(candidate.get("citation_id"), limit=220)
        require(not caller_citation_id or caller_citation_id == allowed_citation_id, "AF4B2 caller-supplied citation_id mismatch")
        excerpt_digest = _digest({"sanitized_excerpt_text": text, "excerpt_ref_id": excerpt_ref_id})
        ref = {
            "excerpt_ref_id": excerpt_ref_id,
            "evidence_id": candidate.get("evidence_id"),
            "candidate_id": candidate.get("candidate_id"),
            "source_id": candidate.get("source_id"),
            "citation_id": allowed_citation_id,
            "content_class": ANSWER_BEARING_SANITIZED_EXCERPT,
            "sanitization_status": "sanitized",
            "excerpt_digest": excerpt_digest,
            "excerpt_length": len(text),
            "excerpt_char_limit": char_limit,
            "bound_allowed_evidence_ref_digest": _digest(allowed_ref),
            "evidence_binding_status": "bound_to_ad_authorized_evidence_ref",
            "source_binding_status": "bound_to_ad_authorized_evidence_ref",
            "bounded_sanitized_excerpt_text_retained": True,
        }
        refs.append(ref)
        payload.append({**ref, "sanitized_excerpt_text": text})
    if not payload:
        return [], [], [ANSWER_BEARING_SANITIZED_EXCERPT], safe_json(identities)
    return safe_json(refs), safe_json(payload), [], safe_json(identities)


def _allowed_refs(ad: Mapping[str, Any], u1: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = safe_mapping_sequence(ad.get("allowed_evidence_refs"))
    u1_refs = safe_mapping_sequence(u1.get("author_allowed_evidence_refs"))
    require(refs, "AF4B2 requires AD allowed evidence refs")
    require(refs == u1_refs, "AF4B2 requires AD/U1-bound allowed evidence refs")
    return refs


def _matching_allowed_ref(
    candidate: Mapping[str, Any],
    allowed_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    identity = {
        field: clean_text(candidate.get(field), limit=220)
        for field in ("evidence_id", "candidate_id", "source_id")
        if clean_text(candidate.get(field), limit=220)
    }
    require(identity, "AF4B2 excerpt requires evidence identity")
    for ref in allowed_refs:
        if any(clean_text(ref.get(field), limit=220) == value for field, value in identity.items()):
            if all(clean_text(ref.get(field), limit=220) == value for field, value in identity.items()):
                return safe_mapping(ref)
    raise PermissionError("AF4B2 unbound or spoofed evidence excerpt")


def _candidate_inputs(value: Any) -> list[dict[str, Any]]:
    if value in (None, "", (), {}, []):
        return []
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise PermissionError("AF4B2 requires a sanitized excerpt candidate list")
    out: list[dict[str, Any]] = []
    for item in value:
        require(isinstance(item, Mapping), "AF4B2 candidates must be mappings")
        _reject_forbidden_payload(item)
        _excerpt_text(item)
        out.append(safe_mapping(item))
    return out


def _excerpt_text(candidate: Mapping[str, Any]) -> str | None:
    text = clean_text(
        candidate.get("sanitized_excerpt_text"),
        limit=MAX_SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CHARS + 1,
    )
    if text:
        require(
            len(text) <= MAX_SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CHARS,
            "AF4B2 sanitized excerpt over length",
        )
    return text


def _candidate_char_limit(candidate: Mapping[str, Any]) -> int:
    if candidate.get("excerpt_char_limit") in (None, ""):
        return MAX_SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CHARS
    try:
        limit = int(candidate.get("excerpt_char_limit"))
    except (TypeError, ValueError) as exc:
        raise PermissionError("AF4B2 excerpt_char_limit invalid") from exc
    require(0 < limit <= MAX_SANITIZED_AUTHOR_EVIDENCE_EXCERPT_CHARS, "AF4B2 excerpt_char_limit invalid")
    return limit


def _bridge_mutation(
    bridge_ref: Mapping[str, Any],
    bridge_digest: str,
    status: str,
    sufficient: bool,
) -> dict[str, Any]:
    return {
        "ag96i3_author_evidence_content_bridge_ref": safe_json(bridge_ref),
        "ag96i3_author_evidence_content_bridge_ref_created": True,
        "ag96i3_author_evidence_content_status": status,
        "ag96i3_author_evidence_content_bridge_digest": bridge_digest,
        "ag96i3_author_evidence_content_sufficient": sufficient,
        **_CLOSED_FLAGS,
    }


def _ad_bound_fields(ad: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"{key}_ad_bound_{suffix}": ad.get(field)
        for key, _, _, id_field, digest_field in _AD_BINDINGS
        for suffix, field in (("id", id_field), ("digest", digest_field))
    }


def _upstream_projection_digests(upstreams: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {f"{key}_projection_digest": _digest(upstreams[f"{key}_projection"]) for key, *_ in _AD_BINDINGS}


def _u1_chain_digests(runtime_inputs: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, prefix, id_field in _U1_CHAIN:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        out[f"{label}_u1_bound_id"] = state.get(id_field)
        out[f"{label}_u1_bound_digest"] = _digest(state)
        out[f"{label}_projection_digest"] = _digest(projection)
    return out


def _lineage_fields(state: Mapping[str, Any]) -> dict[str, Any]:
    suffixes = (
        "_ad_bound_id",
        "_ad_bound_digest",
        "_projection_digest",
        "_u1_bound_id",
        "_u1_bound_digest",
    )
    return {key: state.get(key) for key in state if key.endswith(suffixes)}


def _identity_ref(ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: ref.get(key)
        for key in ("evidence_id", "candidate_id", "source_id", "citation_id", "status")
        if ref.get(key) not in (None, "", [], {})
    }


def _validate_closed(state: Mapping[str, Any]) -> None:
    for field, expected in _CLOSED_FLAGS.items():
        require(state.get(field) is expected, f"AF4B2 {field} must be {expected}")


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _token(key) in _FORBIDDEN_KEYS:
                raise PermissionError(f"AF4B2 cannot accept or retain {key!r}")
            _reject_forbidden_payload(child)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for child in value:
            _reject_forbidden_payload(child)
    elif isinstance(value, str):
        lowered = value.casefold()
        if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
            raise PermissionError("AF4B2 payload includes private text marker")


def _history(runtime_inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [safe_mapping(item) for item in runtime_inputs.get(f"{prefix}_history", [])]


def _bridge_id(ad: Mapping[str, Any]) -> str:
    return f"followup-author-evidence-content-bridge:{ad.get('payload_envelope_id')}:{_digest(ad)[:16]}"


def _token(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
