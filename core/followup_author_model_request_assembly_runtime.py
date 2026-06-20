"""AG-96I3AF4D AF4C-bound transient Author model request assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.followup_author_evidence_content_bridge_runtime import (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
    validate_run_kernel_followup_author_evidence_content_bridge_state,
)
from core.followup_author_invocation_construction_runtime import (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
    validate_run_kernel_followup_author_invocation_construction_state,
)
from core.followup_author_payload_safety import (
    projection_digest as _digest,
)
from core.followup_author_payload_safety import (
    reject_caller_controlled_inputs,
    require,
    safe_mapping,
    safe_mapping_sequence,
)
from core.followup_deliberation import clean_text, safe_json

FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE = "followup_author_model_request_assembly"
AG96I3AF4D_AF4C_BOUND_AUTHOR_MODEL_REQUEST_MODEL_CLOSED_MODE = (
    "ag96i3af4d_af4c_bound_author_model_request_model_closed"
)
FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS = "author_model_request_assembled_model_closed"
FOLLOWUP_AUTHOR_MODEL_REQUEST_BLOCKED_STATUS = (
    "author_model_request_blocked_missing_invocation_or_content_model_closed"
)
FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_REASON = (
    AG96I3AF4D_AF4C_BOUND_AUTHOR_MODEL_REQUEST_MODEL_CLOSED_MODE
)

_CLOSED_FLAGS = {
    field: False
    for field in "model_execution_allowed real_model_called ask_model_called execute_author_action_called author_observation_created final_answer_outcome_created prompt_text_retained model_response_retained report_text_retained final_text_retained product_answer_ready citation_strings_included ordered_product_source_output_created".split()
} | {
    "author_execution_deferred": True,
}
_FORBIDDEN_PAYLOAD_KEYS = frozenset("prompt_text raw_prompt invocation_text raw_invocation_text model_response final_answer_text report_text product_output sanitized_excerpt_text raw_provider_payload provider_payload raw_payload db_row cache private_log full_trace secret api_key author_observation final_answer_outcome output".split())
_CALLER_CONTROLLED_KEYS = frozenset(
    {
        *_FORBIDDEN_PAYLOAD_KEYS,
        *"followup_author_model_request_assembly_state followup_author_model_request_assembly_projection followup_author_model_request_assembly_history author_model_request_ref author_model_request_digest assembled_author_model_request model_request_text request_prompt raw_prompt output".split(),
    }
)
_REQUEST_TEXT_FIELDS = "bounded_user_request_text user_question question query request_text user_request_text".split()
_AD_BINDINGS = (("ac", "followup_author_payload_authority", "payload_authority_id"), ("z", "followup_author_prompt_assembly_manifest", "author_prompt_assembly_manifest_id"), ("y", "followup_author_execution_activation", "author_execution_activation_id"), ("x", "followup_author_input_materialization", "author_input_materialization_id"), ("w", "followup_author_execution_readiness", "author_execution_readiness_id"), ("v1", "followup_author_gate", "author_gate_id"), ("u1", "followup_author_input_authority", "author_input_authority_id"))
_U1_CHAIN = (("p1", "followup_final_evidence_selection", "final_evidence_selection_id"), ("q1", "followup_citation_eligibility", "citation_eligibility_id"), ("r1", "followup_citation_source_handoff", "citation_source_handoff_id"), ("t1", "followup_citation_rendering", "citation_rendering_id"))


@dataclass(frozen=True, slots=True)
class FollowupAuthorModelRequestAssemblyRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return safe_mapping(self.state)


def reject_followup_author_model_request_assembly_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    _reject_forbidden_payload(dict(inputs or {}) if isinstance(inputs, Mapping) else {})
    reject_caller_controlled_inputs(inputs, caller_controlled_keys=_CALLER_CONTROLLED_KEYS, context_label="AF4D Author model request assembly action", closed_surface_rejector=_reject_forbidden_payload, check_raw_keys=True)


def build_followup_author_model_request_assembly_action_inputs(
    *,
    run_request: Mapping[str, Any],
    followup_author_invocation_construction_state: Mapping[str, Any],
    followup_author_invocation_construction_projection: Mapping[str, Any],
    followup_author_invocation_construction_history: Sequence[Mapping[str, Any]],
    followup_author_evidence_content_bridge_state: Mapping[str, Any],
    followup_author_evidence_content_bridge_projection: Mapping[str, Any],
    followup_author_evidence_content_bridge_history: Sequence[Mapping[str, Any]],
    **_: Any,
) -> dict[str, Any]:
    invocation = safe_mapping(followup_author_invocation_construction_state)
    invocation_projection = safe_mapping(followup_author_invocation_construction_projection)
    bridge = safe_mapping(followup_author_evidence_content_bridge_state)
    bridge_projection = safe_mapping(followup_author_evidence_content_bridge_projection)
    request_context = _bounded_user_request_context(run_request)
    missing = []
    if not request_context:
        missing.append("bounded_user_request_text")
    status = (
        FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS
        if not missing
        else FOLLOWUP_AUTHOR_MODEL_REQUEST_BLOCKED_STATUS
    )
    payload_ref = safe_mapping(bridge.get("sanitized_author_evidence_content_payload_ref"))
    excerpt_refs = safe_mapping_sequence(bridge.get("answer_bearing_sanitized_excerpt_refs"))
    af4c_history = list(followup_author_invocation_construction_history or [{}])[-1]
    af4b2_history = list(followup_author_evidence_content_bridge_history or [{}])[-1]
    return {
        "run_id": invocation.get("run_id"),
        "checkpoint_id": invocation.get("checkpoint_id"),
        "packet_id": invocation.get("packet_id"),
        "author_model_request_assembly_id": _assembly_id(invocation, bridge),
        "author_model_request_assembly_mode": (
            AG96I3AF4D_AF4C_BOUND_AUTHOR_MODEL_REQUEST_MODEL_CLOSED_MODE
        ),
        "status": status,
        "missing_model_request_input_classes": missing,
        "bounded_user_request_ref": _bounded_user_request_ref(request_context) if request_context else {},
        "run_request_digest": _digest(safe_mapping(run_request)),
        "af4c_author_invocation_construction_id": invocation.get(
            "author_invocation_construction_id"
        ),
        "af4c_author_invocation_digest": invocation.get(
            "ag96i3_author_invocation_digest"
        ),
        "af4c_author_invocation_projection_digest": _digest(invocation_projection),
        "af4b2_author_evidence_content_bridge_id": bridge.get(
            "author_evidence_content_bridge_id"
        ),
        "af4b2_author_evidence_content_bridge_digest": bridge.get(
            "content_bridge_digest"
        ),
        "af4b2_author_evidence_content_projection_digest": _digest(bridge_projection),
        "sanitized_author_evidence_content_payload_ref": payload_ref,
        "sanitized_author_evidence_content_payload_digest": bridge.get(
            "sanitized_author_evidence_content_payload_digest"
        ),
        "af4b2_sanitized_content_payload_ref_digest": _digest(payload_ref),
        "answer_bearing_sanitized_excerpt_refs": excerpt_refs,
        "answer_bearing_sanitized_excerpt_ref_count": len(excerpt_refs),
        "af4c_history_projection_digest": _digest(safe_mapping(af4c_history)),
        "af4b2_history_projection_digest": _digest(safe_mapping(af4b2_history)),
    }


def build_followup_author_model_request_assembly_record(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> FollowupAuthorModelRequestAssemblyRecord:
    action = safe_mapping(action_inputs)
    invocation = _validate_invocation(runtime_inputs)
    bridge = _validate_bridge(invocation["state"], runtime_inputs)
    _validate_bound_upstreams(invocation["state"], bridge["state"], runtime_inputs)
    expected = build_followup_author_model_request_assembly_action_inputs(
        run_request=safe_mapping(runtime_inputs.get("run_request")),
        followup_author_invocation_construction_state=invocation["state"],
        followup_author_invocation_construction_projection=invocation["projection"],
        followup_author_invocation_construction_history=invocation["history"],
        followup_author_evidence_content_bridge_state=bridge["state"],
        followup_author_evidence_content_bridge_projection=bridge["projection"],
        followup_author_evidence_content_bridge_history=bridge["history"],
    )
    require(action == expected, "AF4D action must match canonical AF4C/AF4B2 inputs")
    request_context = _bounded_user_request_context(
        safe_mapping(runtime_inputs.get("run_request"))
    )
    missing = list(action.get("missing_model_request_input_classes") or [])
    assembled = not missing
    request_sections: list[dict[str, Any]] = []
    request_digest = None
    request_length = 0
    if assembled:
        request_sections = _transient_request_sections(
            request_context=request_context,
            invocation=invocation["state"],
            bridge=bridge["state"],
        )
        request_digest = _digest({"sections": request_sections})
        request_length = sum(section["section_length"] for section in request_sections)
    section_refs = _section_refs(request_sections)
    request_ref = _request_ref(
        action=action,
        request_digest=request_digest,
        request_length=request_length,
        section_refs=section_refs,
        assembled=assembled,
    )
    state = {
        **action,
        "schema_version": "followup_author_model_request_assembly_ag96i3af4d_v1",
        "record_type": "followup_author_model_request_assembly_record",
        "owner": "FollowupAuthorModelRequestAssemblyRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "author_model_request_assembled": assembled,
        "author_model_request_ready_for_execution": assembled,
        "author_model_request_ref": request_ref,
        "author_model_request_digest": request_digest,
        "ag96i3_author_model_request_digest": request_digest,
        "author_model_request_length": request_length,
        "author_model_request_section_refs": section_refs,
        "author_model_request_section_names": [
            section["section_name"] for section in section_refs
        ],
        "author_model_request_section_digests": {
            section["section_name"]: section["section_digest"]
            for section in section_refs
        },
        "author_model_request_section_lengths": {
            section["section_name"]: section["section_length"]
            for section in section_refs
        },
        "author_model_request_section_count": len(section_refs),
        "af4c_invocation_digest": action.get("af4c_author_invocation_digest"),
        "af4c_invocation_projection_digest": action.get(
            "af4c_author_invocation_projection_digest"
        ),
        "af4b2_bridge_digest": action.get(
            "af4b2_author_evidence_content_bridge_digest"
        ),
        "af4b2_bridge_projection_digest": action.get(
            "af4b2_author_evidence_content_projection_digest"
        ),
        "binding_proof": _binding_proof(action, invocation["state"], bridge["state"]),
        **_ad_bound_fields(invocation["state"], bridge["state"]),
        **_u1_chain_fields(bridge["state"]),
        **_source_ref_fields(invocation["state"]),
        **_CLOSED_FLAGS,
    }
    _reject_forbidden_payload(state)
    return FollowupAuthorModelRequestAssemblyRecord(safe_json(state))


def build_run_kernel_followup_author_model_request_assembly_state(
    *,
    model_request_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **safe_mapping(model_request_record_state),
        "owner": "RunKernel.FollowupAuthorModelRequestAssembly",
        "canonical_state": True,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_model_request_assembly_state(
        model_request_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_model_request_assembly_state(
    *,
    model_request_state: Mapping[str, Any],
) -> None:
    state = safe_mapping(model_request_state)
    require(
        state.get("owner") == "RunKernel.FollowupAuthorModelRequestAssembly",
        "AF4D owner",
    )
    require(state.get("canonical_state") is True, "AF4D canonical state")
    require(state.get("trace_only") is False, "AF4D cannot be trace-only")
    require(state.get("storage_only") is False, "AF4D cannot be storage-only")
    status = state.get("status")
    require(
        status
        in {
            FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS,
            FOLLOWUP_AUTHOR_MODEL_REQUEST_BLOCKED_STATUS,
        },
        "AF4D model request status",
    )
    if status == FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS:
        require(state.get("author_model_request_assembled") is True, "AF4D assembled")
        require(
            state.get("author_model_request_ready_for_execution") is True,
            "AF4D request ready",
        )
        require(state.get("author_model_request_digest"), "AF4D request digest")
        require(state.get("author_model_request_length", 0) > 0, "AF4D request length")
        require(state.get("author_model_request_section_refs"), "AF4D sections")
    else:
        require(
            state.get("author_model_request_assembled") is False,
            "AF4D blocked assembly",
        )
        require(
            state.get("author_model_request_ready_for_execution") is False,
            "AF4D blocked readiness",
        )
        require(
            "bounded_user_request_text"
            in list(state.get("missing_model_request_input_classes") or []),
            "AF4D missing bounded user request text",
        )
    require(state.get("af4c_invocation_digest"), "AF4D AF4C digest")
    require(state.get("af4b2_bridge_digest"), "AF4D AF4B2 digest")
    require(
        state.get("sanitized_author_evidence_content_payload_digest"),
        "AF4D content payload digest",
    )
    require(state.get("answer_bearing_sanitized_excerpt_refs"), "AF4D excerpt refs")
    _validate_closed(state)
    _reject_forbidden_payload(state)


def build_followup_author_model_request_assembly_projection(
    *,
    model_request_state: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    state = safe_mapping(model_request_state)
    fields = (
        "schema_version",
        "status",
        "author_model_request_assembly_id",
        "author_model_request_assembly_mode",
        "author_model_request_assembled",
        "author_model_request_ready_for_execution",
        "missing_model_request_input_classes",
        "bounded_user_request_ref",
        "run_request_digest",
        "author_model_request_ref",
        "author_model_request_digest",
        "ag96i3_author_model_request_digest",
        "author_model_request_length",
        "author_model_request_section_refs",
        "author_model_request_section_names",
        "author_model_request_section_digests",
        "author_model_request_section_lengths",
        "author_model_request_section_count",
        "af4c_invocation_digest",
        "af4c_invocation_projection_digest",
        "af4b2_bridge_digest",
        "af4b2_bridge_projection_digest",
        "sanitized_author_evidence_content_payload_ref",
        "sanitized_author_evidence_content_payload_digest",
        "answer_bearing_sanitized_excerpt_refs",
        "answer_bearing_sanitized_excerpt_ref_count",
        "rendered_source_entries_refs_or_digest",
        "mandatory_caveats_refs_or_digest",
        "prohibited_upgrades_refs_or_digest",
        "source_bound_unknowns_refs_or_digest",
        "binding_proof",
    )
    projection = {
        "owner": "RunKernel.FollowupAuthorModelRequestAssembly",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        **{field: safe_json(state.get(field)) for field in fields},
        **_CLOSED_FLAGS,
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_model_request_assembly_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_model_request_state: Mapping[str, Any],
) -> None:
    observed = safe_mapping(observed_model_request_state)
    _validate_closed(observed)
    for field, expected in safe_mapping(action_inputs).items():
        require(observed.get(field) == expected, f"AF4D observation {field} mismatch")
    _reject_forbidden_payload(observed)


def _validate_invocation(runtime_inputs: Mapping[str, Any]) -> dict[str, Any]:
    state = safe_mapping(
        runtime_inputs.get("followup_author_invocation_construction_state")
    )
    projection = safe_mapping(
        runtime_inputs.get("followup_author_invocation_construction_projection")
    )
    history = _history(runtime_inputs, "followup_author_invocation_construction")
    require(state, "AF4D requires AF4C invocation state")
    validate_run_kernel_followup_author_invocation_construction_state(
        invocation_state=state
    )
    require(
        state.get("status") == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
        "AF4D requires constructed AF4C invocation",
    )
    require(
        state.get("author_invocation_ready_for_model") is True,
        "AF4D requires AF4C model-ready invocation",
    )
    require(
        state.get("model_execution_allowed") is False,
        "AF4D requires AF4C model execution closed",
    )
    require(
        projection.get("owner") == "RunKernel.FollowupAuthorInvocationConstruction",
        "AF4D AF4C projection owner",
    )
    require(projection.get("canonical_state") is True, "AF4D canonical AF4C")
    require(history and history[-1] == projection, "AF4D current AF4C history")
    require(
        state.get("ag96i3_author_invocation_digest")
        == _digest(safe_mapping(state.get("ag96i3_author_invocation_ref"))),
        "AF4D stale AF4C invocation ref digest",
    )
    return {"state": state, "projection": projection, "history": history}


def _validate_bridge(
    invocation: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    state = safe_mapping(runtime_inputs.get("followup_author_evidence_content_bridge_state"))
    projection = safe_mapping(
        runtime_inputs.get("followup_author_evidence_content_bridge_projection")
    )
    history = _history(runtime_inputs, "followup_author_evidence_content_bridge")
    require(state, "AF4D requires AF4B2 evidence-content bridge state")
    validate_run_kernel_followup_author_evidence_content_bridge_state(
        bridge_state=state
    )
    require(
        state.get("status") == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
        "AF4D requires bound AF4B2 evidence content",
    )
    require(
        projection.get("owner") == "RunKernel.FollowupAuthorEvidenceContentBridge",
        "AF4D AF4B2 projection owner",
    )
    require(projection.get("canonical_state") is True, "AF4D canonical AF4B2")
    require(history and history[-1] == projection, "AF4D current AF4B2 history")
    payload = safe_mapping_sequence(state.get("sanitized_author_evidence_content_payload"))
    payload_digest = _digest({"payload": payload})
    payload_ref = safe_mapping(state.get("sanitized_author_evidence_content_payload_ref"))
    require(
        state.get("sanitized_author_evidence_content_payload_digest")
        == payload_digest,
        "AF4D stale AF4B2 content payload digest",
    )
    require(
        payload_ref.get("payload_digest") == payload_digest,
        "AF4D stale AF4B2 content payload ref",
    )
    require(
        state.get("content_bridge_digest")
        == _digest(safe_mapping(state.get("content_bridge_ref"))),
        "AF4D stale AF4B2 bridge ref digest",
    )
    require(
        invocation.get("af4b2_author_evidence_content_bridge_digest")
        == state.get("content_bridge_digest"),
        "AF4D AF4C stale AF4B2 bridge digest",
    )
    require(
        invocation.get("sanitized_author_evidence_content_payload_digest")
        == payload_digest,
        "AF4D AF4C stale AF4B2 content payload digest",
    )
    require(
        safe_mapping(invocation.get("sanitized_author_evidence_content_payload_ref"))
        == payload_ref,
        "AF4D AF4C stale AF4B2 content payload ref",
    )
    require(
        safe_mapping_sequence(invocation.get("answer_bearing_sanitized_excerpt_refs"))
        == safe_mapping_sequence(state.get("answer_bearing_sanitized_excerpt_refs")),
        "AF4D AF4C stale answer-bearing excerpt refs",
    )
    require(payload, "AF4D requires answer-bearing sanitized excerpt payload")
    return {"state": state, "projection": projection, "history": history}


def _validate_bound_upstreams(
    invocation: Mapping[str, Any],
    bridge: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> None:
    ad = safe_mapping(runtime_inputs.get("followup_author_payload_construction_state"))
    ad_projection = safe_mapping(
        runtime_inputs.get("followup_author_payload_construction_projection")
    )
    ad_history = _history(runtime_inputs, "followup_author_payload_construction")
    require(ad, "AF4D requires AD payload construction state")
    require(ad_projection.get("canonical_state") is True, "AF4D canonical AD")
    require(ad_history and ad_history[-1] == ad_projection, "AF4D current AD history")
    require(
        invocation.get("ad_payload_construction_digest") == _digest(ad),
        "AF4D AF4C stale AD digest",
    )
    require(
        bridge.get("ad_payload_construction_digest") == _digest(ad),
        "AF4D AF4B2 stale AD digest",
    )
    for key, prefix, id_field in _AD_BINDINGS:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4D requires {key} state")
        require(projection.get("canonical_state") is True, f"AF4D {key} projection")
        require(history and history[-1] == projection, f"AF4D {key} history")
        require(
            invocation.get(f"{key}_ad_bound_id") == state.get(id_field),
            f"AF4D AF4C {key} id",
        )
        require(
            invocation.get(f"{key}_ad_bound_digest") == _digest(state),
            f"AF4D AF4C {key} digest",
        )
        require(
            invocation.get(f"{key}_projection_digest") == _digest(projection),
            f"AF4D AF4C {key} projection",
        )
        require(
            bridge.get(f"{key}_ad_bound_digest") == _digest(state),
            f"AF4D AF4B2 {key} digest",
        )
        require(
            bridge.get(f"{key}_projection_digest") == _digest(projection),
            f"AF4D AF4B2 {key} projection",
        )
    for key, prefix, id_field in _U1_CHAIN:
        state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
        projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
        history = _history(runtime_inputs, prefix)
        require(state, f"AF4D requires {key} state")
        require(projection.get("canonical_state") is True, f"AF4D {key} projection")
        require(history and history[-1] == projection, f"AF4D {key} history")
        require(
            bridge.get(f"{key}_u1_bound_id") == state.get(id_field),
            f"AF4D AF4B2 {key} id",
        )
        require(
            bridge.get(f"{key}_u1_bound_digest") == _digest(state),
            f"AF4D AF4B2 {key} digest",
        )
        require(
            bridge.get(f"{key}_projection_digest") == _digest(projection),
            f"AF4D AF4B2 {key} projection",
        )


def _bounded_user_request_context(request: Mapping[str, Any]) -> dict[str, Any]:
    data = safe_mapping(request)
    for field in _REQUEST_TEXT_FIELDS:
        text = clean_text(data.get(field), limit=2000)
        if text:
            return {
                "source_field": field,
                "request_text": text,
                "request_digest": _digest({"field": field, "value": text}),
                "request_length": len(text),
            }
    for field in ("bounded_user_request", "user_request"):
        nested = safe_mapping(data.get(field))
        text = clean_text(nested.get("text"), limit=2000)
        if text:
            return {
                "source_field": f"{field}.text",
                "request_text": text,
                "request_digest": _digest({"field": f"{field}.text", "value": text}),
                "request_length": len(text),
            }
    return {}


def _bounded_user_request_ref(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "request_context_ref_id": f"bounded-user-request:{context.get('source_field')}",
        "source_field": context.get("source_field"),
        "request_digest": context.get("request_digest"),
        "request_length": context.get("request_length"),
        "request_text_retained": False,
    }


def _transient_request_sections(
    *,
    request_context: Mapping[str, Any],
    invocation: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> list[dict[str, Any]]:
    payload = safe_mapping_sequence(bridge.get("sanitized_author_evidence_content_payload"))
    excerpt_lines = [
        _transient_excerpt_line(excerpt)
        for excerpt in payload
        if clean_text(excerpt.get("sanitized_excerpt_text"), limit=1000)
    ]
    sections = [
        (
            "bounded_user_request",
            str(request_context.get("request_text") or ""),
        ),
        (
            "af4c_invocation_manifest",
            repr(
                safe_json(
                    {
                        "invocation_id": invocation.get(
                            "author_invocation_construction_id"
                        ),
                        "invocation_digest": invocation.get(
                            "ag96i3_author_invocation_digest"
                        ),
                        "payload_envelope_digest": invocation.get(
                            "payload_envelope_digest"
                        ),
                        "content_payload_digest": invocation.get(
                            "sanitized_author_evidence_content_payload_digest"
                        ),
                        "excerpt_refs": invocation.get(
                            "answer_bearing_sanitized_excerpt_refs"
                        ),
                    }
                )
            ),
        ),
        ("af4b2_sanitized_evidence_content", "\n".join(excerpt_lines)),
        (
            "source_and_caveat_refs",
            repr(
                safe_json(
                    {
                        "rendered_source_entries": _source_ref_fields(invocation).get(
                            "rendered_source_entries_refs_or_digest"
                        ),
                        "mandatory_caveats": _source_ref_fields(invocation).get(
                            "mandatory_caveats_refs_or_digest"
                        ),
                        "prohibited_upgrades": _source_ref_fields(invocation).get(
                            "prohibited_upgrades_refs_or_digest"
                        ),
                        "source_bound_unknowns": _source_ref_fields(invocation).get(
                            "source_bound_unknowns_refs_or_digest"
                        ),
                    }
                )
            ),
        ),
    ]
    return [
        {
            "section_name": name,
            "section_digest": _digest({"section_name": name, "section_text": text}),
            "section_length": len(text),
        }
        for name, text in sections
    ]


def _transient_excerpt_line(excerpt: Mapping[str, Any]) -> str:
    text = clean_text(excerpt.get("sanitized_excerpt_text"), limit=1000)
    ref = clean_text(excerpt.get("excerpt_ref_id"), limit=220)
    evidence = clean_text(excerpt.get("evidence_id"), limit=220)
    source = clean_text(excerpt.get("source_id"), limit=220)
    return f"{ref}|{evidence}|{source}: {text}"


def _section_refs(sections: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section_ref_id": f"af4d-author-model-request-section:{section.get('section_name')}",
            "section_name": section.get("section_name"),
            "section_digest": section.get("section_digest"),
            "section_length": section.get("section_length"),
            "section_text_retained": False,
        }
        for section in sections
    ]


def _request_ref(
    *,
    action: Mapping[str, Any],
    request_digest: str | None,
    request_length: int,
    section_refs: Sequence[Mapping[str, Any]],
    assembled: bool,
) -> dict[str, Any]:
    return {
        "author_model_request_ref_id": (
            f"ag96i3-af4d-author-model-request:"
            f"{action.get('author_model_request_assembly_id')}"
        ),
        "mode": AG96I3AF4D_AF4C_BOUND_AUTHOR_MODEL_REQUEST_MODEL_CLOSED_MODE,
        "status": action.get("status"),
        "request_digest": request_digest,
        "request_length": request_length,
        "section_refs": safe_json(section_refs),
        "section_count": len(section_refs),
        "author_model_request_assembled": assembled,
        "author_model_request_ready_for_execution": assembled,
        "model_execution_allowed": False,
        "prompt_text_retained": False,
        "model_response_retained": False,
        "final_answer_outcome_created": False,
        "product_answer_ready": False,
    }


def _binding_proof(
    action: Mapping[str, Any],
    invocation: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    content_digest = action.get("sanitized_author_evidence_content_payload_digest")
    return {
        "af4c_author_invocation_construction_id": action.get(
            "af4c_author_invocation_construction_id"
        ),
        "af4c_author_invocation_digest": action.get("af4c_author_invocation_digest"),
        "af4c_author_invocation_projection_digest": action.get(
            "af4c_author_invocation_projection_digest"
        ),
        "af4b2_author_evidence_content_bridge_id": action.get(
            "af4b2_author_evidence_content_bridge_id"
        ),
        "af4b2_author_evidence_content_bridge_digest": action.get(
            "af4b2_author_evidence_content_bridge_digest"
        ),
        "af4b2_author_evidence_content_projection_digest": action.get(
            "af4b2_author_evidence_content_projection_digest"
        ),
        "af4c_bound_content_payload_digest": invocation.get(
            "sanitized_author_evidence_content_payload_digest"
        ),
        "af4b2_content_payload_digest": bridge.get(
            "sanitized_author_evidence_content_payload_digest"
        ),
        "content_payload_digest_match": (
            invocation.get("sanitized_author_evidence_content_payload_digest")
            == content_digest
            == bridge.get("sanitized_author_evidence_content_payload_digest")
        ),
        "answer_bearing_excerpt_ref_count": action.get(
            "answer_bearing_sanitized_excerpt_ref_count"
        ),
    }


def _ad_bound_fields(
    invocation: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    out = {}
    for key, *_ in _AD_BINDINGS:
        out[f"{key}_af4c_bound_digest"] = invocation.get(f"{key}_ad_bound_digest")
        out[f"{key}_af4b2_bound_digest"] = bridge.get(f"{key}_ad_bound_digest")
        out[f"{key}_projection_digest"] = invocation.get(f"{key}_projection_digest")
    return out


def _u1_chain_fields(bridge: Mapping[str, Any]) -> dict[str, Any]:
    out = {}
    for key, *_ in _U1_CHAIN:
        out[f"{key}_u1_bound_digest"] = bridge.get(f"{key}_u1_bound_digest")
        out[f"{key}_projection_digest"] = bridge.get(f"{key}_projection_digest")
    return out


def _source_ref_fields(invocation: Mapping[str, Any]) -> dict[str, Any]:
    manifest = safe_mapping(invocation.get("invocation_manifest"))
    return {
        "rendered_source_entries_refs_or_digest": safe_mapping(
            manifest.get("rendered_source_entries_refs_or_digest")
        ),
        "mandatory_caveats_refs_or_digest": safe_mapping(
            manifest.get("mandatory_caveats_refs_or_digest")
        ),
        "prohibited_upgrades_refs_or_digest": safe_mapping(
            manifest.get("prohibited_upgrades_refs_or_digest")
        ),
        "source_bound_unknowns_refs_or_digest": safe_mapping(
            manifest.get("source_bound_unknowns_refs_or_digest")
        ),
    }


def _validate_closed(state: Mapping[str, Any]) -> None:
    for field, expected in _CLOSED_FLAGS.items():
        require(state.get(field) is expected, f"AF4D {field} must be {expected}")


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key or "").casefold()
            require(token not in _FORBIDDEN_PAYLOAD_KEYS, f"AF4D cannot retain {key!r}")
            _reject_forbidden_payload(child)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for child in value:
            _reject_forbidden_payload(child)


def _history(runtime_inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [safe_mapping(item) for item in runtime_inputs.get(f"{prefix}_history", [])]


def _assembly_id(invocation: Mapping[str, Any], bridge: Mapping[str, Any]) -> str:
    return (
        "followup-author-model-request-assembly:"
        f"{invocation.get('author_invocation_construction_id')}:"
        f"{_digest(bridge)[:16]}"
    )
