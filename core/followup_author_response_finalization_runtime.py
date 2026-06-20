"""AG-96I3AF5B AF5A candidate to final/product answer output."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.followup_author_execution_from_af4d_runtime import (
    validate_run_kernel_followup_author_execution_from_af4d_state,
)
from core.followup_author_payload_safety import (
    projection_digest as _digest,
)
from core.followup_author_payload_safety import (
    reject_caller_controlled_inputs,
    require,
    safe_mapping,
    safe_mapping_sequence,
    safe_string_sequence,
)
from core.followup_deliberation import clean_text, safe_json

FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_SCHEMA_VERSION = (
    "followup_author_response_finalization_ag96i3af5b_v1"
)
FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE = (
    "followup_author_response_finalization"
)
AG96I3AF5B_AF5A_RESPONSE_CANDIDATE_FINAL_ANSWER_MODE = (
    "ag96i3af5b_af5a_response_candidate_final_answer_output"
)
FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS = (
    "author_response_finalized_from_af5a"
)
FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_REASON = (
    AG96I3AF5B_AF5A_RESPONSE_CANDIDATE_FINAL_ANSWER_MODE
)

_FALSE_FLAGS = {
    field: False
    for field in """
        model_execution_allowed live_provider_call_allowed real_model_called
        ask_model_called execute_author_action_called author_executor_invoked
        prompt_text_retained request_text_retained model_request_text_retained
        model_response_retained provider_payload_retained
        report_text_retained search_executed retrieval_executed
        fetch_executed provider_search_changed retrieval_ranking_filtering_changed
        evidence_reselected citation_rendering_changed citation_formatter_invoked
        citation_reselection_changed ordered_product_source_output_created
        live_validation_run followup_author_execution_from_ad_consumed
    """.split()
}
_TRUE_FLAGS = {
    field: True
    for field in """
        af5a_response_candidate_consumed final_answer_packet_consumed
        final_answer_authority_projection_consumed author_observation_created
        final_answer_outcome_created final_text_included final_text_retained
        product_answer_ready answer_text_output_created
        final_answer_packet_refs_preserved source_refs_preserved
        citation_refs_preserved caveat_refs_preserved live_validation_not_run
        injected_fake_model_adapter_used
    """.split()
}
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    """
    prompt raw_prompt prompt_text request raw_request request_text
    raw_request_text model_request_text raw_model_request_text
    bounded_sanitized_author_response_candidate_text
    model_response raw_model_response provider_payload raw_provider_payload
    raw_payload raw_text raw_response raw_trace db_row cache private_log
    full_trace secret secrets api_key
    """.split()
)
_CALLER_CONTROLLED_KEYS = frozenset(
    {
        *_FORBIDDEN_PAYLOAD_KEYS,
        *"""
        followup_author_response_finalization_state
        followup_author_response_finalization_projection
        followup_author_response_finalization_history
        author_observation final_answer_outcome final_answer_text
        product_answer_text answer_text report output product_output
        final_answer_output product_answer
        """.split(),
    }
)
_PRIVATE_TEXT_MARKERS = (
    "raw_prompt",
    "raw provider",
    "raw_provider",
    "provider_payload",
    "raw_model_response",
    "api_key",
    "secret",
)


@dataclass(frozen=True, slots=True)
class FollowupAuthorResponseFinalizationActionResult:
    record: "FollowupAuthorResponseFinalizationRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorResponseFinalizationRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return safe_mapping(self.state)


def reject_followup_author_response_finalization_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    _reject_forbidden_payload(dict(inputs or {}) if isinstance(inputs, Mapping) else {})
    reject_caller_controlled_inputs(
        inputs,
        caller_controlled_keys=_CALLER_CONTROLLED_KEYS,
        context_label="AF5B Author response finalization action",
        closed_surface_rejector=_reject_forbidden_payload,
        check_raw_keys=True,
    )


def build_followup_author_response_finalization_action_inputs(
    *,
    followup_author_execution_from_af4d_state: Mapping[str, Any],
    followup_author_execution_from_af4d_projection: Mapping[str, Any],
    followup_author_execution_from_af4d_history: Sequence[Mapping[str, Any]],
    final_answer_packet: Mapping[str, Any],
    final_answer_authority_projection: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    af5a = _current_af5a(
        followup_author_execution_from_af4d_state,
        followup_author_execution_from_af4d_projection,
        followup_author_execution_from_af4d_history,
    )
    packet, authority = _current_packet_authority(
        final_answer_packet,
        final_answer_authority_projection,
    )
    candidate = _candidate_from_af5a(af5a["state"])
    refs = _packet_output_refs(packet, authority)
    finalization_id = _finalization_id(af5a["state"], candidate)
    return {
        "run_id": af5a["state"].get("run_id"),
        "checkpoint_id": af5a["state"].get("checkpoint_id"),
        "packet_id": packet.get("packet_id") or authority.get("packet_id"),
        "author_response_finalization_id": finalization_id,
        "author_response_finalization_stage": (
            FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE
        ),
        "author_response_finalization_mode": (
            AG96I3AF5B_AF5A_RESPONSE_CANDIDATE_FINAL_ANSWER_MODE
        ),
        "status": FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS,
        "af5a_author_execution_from_af4d_id": af5a["state"].get(
            "author_execution_from_af4d_id"
        ),
        "af5a_author_execution_from_af4d_status": af5a["state"].get("status"),
        "af5a_author_execution_from_af4d_mode": af5a["state"].get(
            "author_execution_from_af4d_mode"
        ),
        "af5a_author_response_candidate_ref_id": candidate.get(
            "author_response_candidate_ref_id"
        ),
        "af5a_author_response_candidate_digest": candidate.get(
            "author_response_candidate_digest"
        ),
        "af5a_author_response_candidate_length": candidate.get(
            "author_response_candidate_length"
        ),
        "af5a_execution_projection_digest": _digest(af5a["projection"]),
        "af5a_execution_history_projection_digest": _digest(
            af5a["history"][-1]
        ),
        "current_final_answer_packet_digest": _digest(packet),
        "final_answer_authority_projection_digest": _digest(authority),
        "final_answer_packet_ref_digest": _digest(
            refs["final_answer_packet_ref"]
        ),
        "source_refs_digest": _digest(refs["source_refs"]),
        "citation_refs_digest": _digest(refs["citation_refs"]),
        "caveat_refs_digest": _digest(refs["caveat_refs"]),
        **_FALSE_FLAGS,
        **_TRUE_FLAGS,
    }


def validate_followup_author_response_finalization_authorization(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> None:
    _validated_context(
        action_inputs=safe_mapping(action_inputs),
        runtime_inputs=runtime_inputs,
    )


def execute_followup_author_response_finalization_action(
    action: Any,
    **runtime_inputs: Any,
) -> FollowupAuthorResponseFinalizationActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType, RunStageStatus

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE,
        stage=FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZED
        ),
    )
    record = build_followup_author_response_finalization_record(
        action_inputs=action.inputs,
        **runtime_inputs,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZED,
        status=RunStageStatus.COMPLETED,
        payload={"followup_author_response_finalization_state": record.to_dict()},
    )
    return FollowupAuthorResponseFinalizationActionResult(
        record=record,
        observation=observation,
    )


def build_followup_author_response_finalization_record(
    *,
    action_inputs: Mapping[str, Any],
    observed_finalization_state: Mapping[str, Any] | None = None,
    **runtime_inputs: Any,
) -> FollowupAuthorResponseFinalizationRecord:
    context = _validated_context(
        action_inputs=safe_mapping(action_inputs),
        runtime_inputs=runtime_inputs,
    )
    action = context["action"]
    answer_text = context["answer_text"]
    answer_digest = _hash_text(answer_text)
    author_observation_id = (
        "af5b-author-observation:"
        f"{action.get('author_response_finalization_id')}"
    )
    final_answer_outcome_id = (
        "af5b-final-answer-outcome:"
        f"{action.get('author_response_finalization_id')}"
    )
    refs = context["refs"]
    author_observation = _author_observation(
        action=action,
        answer_text=answer_text,
        answer_digest=answer_digest,
        author_observation_id=author_observation_id,
        refs=refs,
    )
    final_answer_outcome = _final_answer_outcome(
        action=action,
        answer_text=answer_text,
        answer_digest=answer_digest,
        final_answer_outcome_id=final_answer_outcome_id,
        author_observation=author_observation,
        refs=refs,
    )
    state = {
        **action,
        "schema_version": FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_SCHEMA_VERSION,
        "record_type": "followup_author_response_finalization_record",
        "owner": "FollowupAuthorResponseFinalizationRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "af5a_author_response_candidate_consumed_ref": _candidate_ref(
            context["candidate"]
        ),
        "final_answer_text_digest": answer_digest,
        "final_answer_text_length": len(answer_text),
        "product_answer_text_digest": answer_digest,
        "product_answer_text_length": len(answer_text),
        "author_observation_id": author_observation_id,
        "author_observation_digest": _digest(author_observation),
        "author_observation": author_observation,
        "final_answer_outcome_id": final_answer_outcome_id,
        "final_answer_outcome_digest": _digest(final_answer_outcome),
        "final_answer_outcome": final_answer_outcome,
        "final_answer_packet_ref": refs["final_answer_packet_ref"],
        "source_refs": refs["source_refs"],
        "citation_refs": refs["citation_refs"],
        "caveat_refs": refs["caveat_refs"],
        "output_surface": {
            "surface": "RunKernel.final_answer_outcome",
            "final_answer_text_digest": answer_digest,
            "final_answer_text_length": len(answer_text),
            "product_answer_ready": True,
        },
        **_FALSE_FLAGS,
        **_TRUE_FLAGS,
    }
    _validate_state(state)
    _reject_forbidden_payload(state)
    if observed_finalization_state is not None:
        _validate_observed_matches_canonical(
            safe_mapping(observed_finalization_state),
            state,
        )
    return FollowupAuthorResponseFinalizationRecord(safe_json(state))


def build_run_kernel_followup_author_response_finalization_state(
    *,
    finalization_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **safe_mapping(finalization_record_state),
        "owner": "RunKernel.FollowupAuthorResponseFinalization",
        "canonical_state": True,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_response_finalization_state(
        finalization_state=state
    )
    return safe_json(state)


def validate_run_kernel_followup_author_response_finalization_state(
    *,
    finalization_state: Mapping[str, Any],
) -> None:
    state = safe_mapping(finalization_state)
    for condition, message in (
        (
            state.get("owner") == "RunKernel.FollowupAuthorResponseFinalization",
            "AF5B owner",
        ),
        (state.get("canonical_state") is True, "AF5B canonical state"),
        (state.get("trace_only") is False, "AF5B cannot be trace-only"),
        (state.get("storage_only") is False, "AF5B cannot be storage-only"),
        (
            state.get("status") == FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS,
            "AF5B status",
        ),
        (
            state.get("af5a_response_candidate_consumed") is True,
            "AF5B consumes AF5A",
        ),
        (
            state.get("followup_author_execution_from_ad_consumed") is False,
            "AF5B must not consume old AE",
        ),
        (state.get("product_answer_ready") is True, "AF5B product ready"),
        (state.get("final_text_included") is True, "AF5B final text included"),
    ):
        require(condition, message)
    _validate_state(state)
    _reject_forbidden_payload(state)


def build_followup_author_response_finalization_projection(
    *,
    finalization_state: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    state = safe_mapping(finalization_state)
    fields = """
        schema_version status author_response_finalization_id
        author_response_finalization_stage author_response_finalization_mode
        packet_id af5a_author_execution_from_af4d_id
        af5a_author_response_candidate_ref_id
        af5a_author_response_candidate_digest
        af5a_author_response_candidate_length
        final_answer_text_digest final_answer_text_length
        product_answer_text_digest product_answer_text_length
        author_observation_id author_observation_digest
        final_answer_outcome_id final_answer_outcome_digest
        final_answer_packet_ref source_refs citation_refs caveat_refs
        output_surface
    """.split()
    projection = {
        "owner": "RunKernel.FollowupAuthorResponseFinalization",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        **{field: safe_json(state.get(field)) for field in fields},
        **_FALSE_FLAGS,
        **_TRUE_FLAGS,
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_response_finalization_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_finalization_state: Mapping[str, Any],
) -> None:
    action = safe_mapping(action_inputs)
    observed = safe_mapping(observed_finalization_state)
    for field, expected in action.items():
        require(observed.get(field) == expected, f"AF5B observation {field} mismatch")
    _validate_flags(observed)
    _reject_forbidden_payload(observed)


def _validated_context(
    *,
    action_inputs: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    action = safe_mapping(action_inputs)
    af5a = _current_af5a(
        runtime_inputs.get("followup_author_execution_from_af4d_state"),
        runtime_inputs.get("followup_author_execution_from_af4d_projection"),
        runtime_inputs.get("followup_author_execution_from_af4d_history"),
    )
    packet, authority = _current_packet_authority(
        runtime_inputs.get("final_answer_packet"),
        runtime_inputs.get("final_answer_authority_projection"),
    )
    expected = safe_mapping(
        build_followup_author_response_finalization_action_inputs(
            followup_author_execution_from_af4d_state=af5a["state"],
            followup_author_execution_from_af4d_projection=af5a["projection"],
            followup_author_execution_from_af4d_history=af5a["history"],
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
    )
    require(action == expected, "AF5B action must match canonical AF5A inputs")
    candidate = _candidate_from_af5a(af5a["state"])
    answer_text = _answer_text(candidate)
    refs = _packet_output_refs(packet, authority)
    require(
        action.get("final_answer_packet_ref_digest")
        == _digest(refs["final_answer_packet_ref"]),
        "AF5B stale FinalAnswerPacket ref digest",
    )
    require(
        action.get("source_refs_digest") == _digest(refs["source_refs"]),
        "AF5B stale source refs digest",
    )
    require(
        action.get("citation_refs_digest") == _digest(refs["citation_refs"]),
        "AF5B stale citation refs digest",
    )
    require(
        action.get("caveat_refs_digest") == _digest(refs["caveat_refs"]),
        "AF5B stale caveat refs digest",
    )
    return {
        "action": action,
        "af5a": af5a["state"],
        "candidate": candidate,
        "answer_text": answer_text,
        "packet": packet,
        "authority": authority,
        "refs": refs,
    }


def _current_af5a(
    state_value: Any,
    projection_value: Any,
    history_value: Any,
) -> dict[str, Any]:
    state = safe_mapping(state_value)
    projection = safe_mapping(projection_value)
    history = [
        safe_mapping(item)
        for item in (history_value or [])
        if isinstance(item, Mapping)
    ]
    require(state, "AF5B requires canonical AF5A state")
    validate_run_kernel_followup_author_execution_from_af4d_state(
        execution_state=state
    )
    require(
        projection.get("owner") == "RunKernel.FollowupAuthorExecutionFromAF4D",
        "AF5B AF5A projection owner",
    )
    require(projection.get("canonical_state") is True, "AF5B canonical AF5A")
    require(history and history[-1] == projection, "AF5B current AF5A history")
    require(
        projection.get("author_response_candidate_digest")
        == state.get("author_response_candidate_digest"),
        "AF5B stale AF5A candidate digest",
    )
    return {"state": state, "projection": projection, "history": history}


def _current_packet_authority(
    packet_value: Any,
    authority_value: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = safe_mapping(packet_value)
    authority = safe_mapping(authority_value)
    packet_id = packet.get("packet_id") or authority.get("packet_id")
    require(packet_id, "AF5B requires FinalAnswerPacket packet_id")
    if authority.get("owner") is not None:
        require(
            str(authority.get("owner")).startswith("RunKernel."),
            "AF5B requires RunKernel-owned final-answer authority",
        )
    if authority.get("canonical_state") is not None:
        require(
            authority.get("canonical_state") is True,
            "AF5B requires canonical FinalAnswerPacket authority",
        )
    require(
        authority.get("packet_id") == packet_id,
        "AF5B packet/authority packet_id mismatch",
    )
    if packet.get("owner") is not None:
        require(
            packet.get("owner") == "RunKernel.FinalAnswerPacket",
            "AF5B packet owner",
        )
    if packet.get("canonical_state") is not None:
        require(packet.get("canonical_state") is True, "AF5B packet canonical")
    require(
        _digest(packet) == _digest(safe_mapping(packet_value)),
        "AF5B packet digest",
    )
    return packet, authority


def _candidate_from_af5a(af5a_state: Mapping[str, Any]) -> dict[str, Any]:
    candidate = safe_mapping(
        safe_mapping(af5a_state).get("bounded_sanitized_author_response_candidate")
    )
    text = _answer_text(candidate)
    digest = _digest(
        {
            "bounded_sanitized_author_response_candidate_text": text,
            "af4d_author_model_request_digest": af5a_state.get(
                "af4d_author_model_request_digest"
            ),
        }
    )
    require(
        candidate.get("author_response_candidate_digest") == digest,
        "AF5B AF5A candidate digest mismatch",
    )
    require(
        af5a_state.get("author_response_candidate_digest") == digest,
        "AF5B AF5A state candidate digest mismatch",
    )
    return candidate


def _answer_text(candidate: Mapping[str, Any]) -> str:
    text = clean_text(
        candidate.get("bounded_sanitized_author_response_candidate_text"),
        limit=1000,
    )
    require(text, "AF5B requires AF5A response candidate text")
    require(
        text == candidate.get("bounded_sanitized_author_response_candidate_text"),
        "AF5B requires canonical AF5A candidate text",
    )
    require(
        len(text) <= int(candidate.get("author_response_candidate_char_limit") or 800),
        "AF5B candidate exceeds AF5A bound",
    )
    _reject_private_text(text)
    return text


def _packet_output_refs(
    packet: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    payload_ref = safe_mapping(authority.get("author_payload_ref")) or safe_mapping(
        packet.get("author_payload_ref")
    )
    citation_source_ids = (
        safe_json(authority.get("citation_eligible_source_ids"))
        or safe_json(payload_ref.get("citation_source_ids"))
        or []
    )
    final_answer_packet_ref = {
        "packet_id": packet.get("packet_id") or authority.get("packet_id"),
        "readiness_status": packet.get("readiness_status")
        or authority.get("readiness_status"),
        "readiness_reasons": safe_string_sequence(packet.get("readiness_reasons")),
        "final_answer_allowed": packet.get("final_answer_allowed"),
        "final_answer_posture": packet.get("final_answer_posture")
        or payload_ref.get("final_answer_posture"),
        "sufficiency_decision": packet.get("sufficiency_decision")
        or payload_ref.get("sufficiency_decision"),
        "author_payload_status": payload_ref.get("status"),
    }
    source_refs = {
        "evidence_allowed": safe_mapping_sequence(packet.get("evidence_allowed")),
        "source_obligations": safe_mapping_sequence(
            packet.get("source_obligations")
        ),
        "citation_eligible_source_ids": citation_source_ids,
        "missing_source_obligations": safe_mapping_sequence(
            payload_ref.get("missing_source_obligations")
            or packet.get("missing_required_obligations")
        ),
        "partial_source_obligations": safe_mapping_sequence(
            payload_ref.get("partial_source_obligations")
            or packet.get("partial_obligations")
        ),
        "satisfied_source_obligations": safe_mapping_sequence(
            payload_ref.get("satisfied_source_obligations")
            or packet.get("satisfied_obligations")
        ),
    }
    citation_refs = {
        "citation_eligible": safe_mapping_sequence(packet.get("citation_eligible")),
        "citation_ineligible": safe_mapping_sequence(
            packet.get("citation_ineligible")
        ),
        "citation_source_ids": citation_source_ids,
    }
    caveat_refs = {
        "mandatory_caveats": safe_string_sequence(packet.get("mandatory_caveats")),
        "prohibited_upgrades": safe_string_sequence(
            packet.get("prohibited_upgrades")
        ),
        "source_bound_numeric_unknowns": safe_mapping_sequence(
            packet.get("source_bound_numeric_unknowns")
            or payload_ref.get("source_bound_numeric_unknowns")
        ),
        "source_bound_numeric_resolutions": safe_mapping_sequence(
            packet.get("source_bound_numeric_resolutions")
            or payload_ref.get("source_bound_numeric_resolutions")
        ),
    }
    return safe_json(
        {
            "final_answer_packet_ref": final_answer_packet_ref,
            "source_refs": source_refs,
            "citation_refs": citation_refs,
            "caveat_refs": caveat_refs,
        }
    )


def _candidate_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "author_response_candidate_ref_id": candidate.get(
            "author_response_candidate_ref_id"
        ),
        "author_response_candidate_digest": candidate.get(
            "author_response_candidate_digest"
        ),
        "author_response_candidate_length": candidate.get(
            "author_response_candidate_length"
        ),
        "content_class": candidate.get("content_class"),
        "sanitization_status": candidate.get("sanitization_status"),
        "candidate_text_retained_as_candidate": False,
    }


def _author_observation(
    *,
    action: Mapping[str, Any],
    answer_text: str,
    answer_digest: str,
    author_observation_id: str,
    refs: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorResponseFinalization",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "record_type": "ag96i3af5b_author_observation",
        "author_observation_id": author_observation_id,
        "packet_id": action.get("packet_id"),
        "af5a_author_execution_from_af4d_id": action.get(
            "af5a_author_execution_from_af4d_id"
        ),
        "af5a_author_response_candidate_ref_id": action.get(
            "af5a_author_response_candidate_ref_id"
        ),
        "final_answer_text": answer_text,
        "product_answer_text": answer_text,
        "report_hash": answer_digest,
        "report_length": len(answer_text),
        "final_answer_text_digest": answer_digest,
        "final_answer_text_length": len(answer_text),
        "final_answer_packet_ref": refs["final_answer_packet_ref"],
        "source_refs": refs["source_refs"],
        "citation_refs": refs["citation_refs"],
        "caveat_refs": refs["caveat_refs"],
        **_FALSE_FLAGS,
        **_TRUE_FLAGS,
    }


def _final_answer_outcome(
    *,
    action: Mapping[str, Any],
    answer_text: str,
    answer_digest: str,
    final_answer_outcome_id: str,
    author_observation: Mapping[str, Any],
    refs: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.FollowupAuthorResponseFinalizationOutcome",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "record_type": "ag96i3af5b_final_answer_outcome",
        "final_answer_outcome_id": final_answer_outcome_id,
        "packet_id": action.get("packet_id"),
        "author_observation_id": author_observation.get("author_observation_id"),
        "author_observation_digest": _digest(author_observation),
        "af5a_author_execution_from_af4d_id": action.get(
            "af5a_author_execution_from_af4d_id"
        ),
        "af5a_author_response_candidate_ref_id": action.get(
            "af5a_author_response_candidate_ref_id"
        ),
        "final_answer_text": answer_text,
        "product_answer_text": answer_text,
        "final_answer_output": {
            "answer_text": answer_text,
            "packet_id": action.get("packet_id"),
            "answer_text_digest": answer_digest,
            "product_answer_ready": True,
        },
        "report_hash": answer_digest,
        "report_length": len(answer_text),
        "final_answer_text_digest": answer_digest,
        "final_answer_text_length": len(answer_text),
        "final_answer_packet_ref": refs["final_answer_packet_ref"],
        "source_refs": refs["source_refs"],
        "citation_refs": refs["citation_refs"],
        "caveat_refs": refs["caveat_refs"],
        **_FALSE_FLAGS,
        **_TRUE_FLAGS,
    }


def _validate_state(state: Mapping[str, Any]) -> None:
    payload = safe_mapping(state)
    _validate_flags(payload)
    author_observation = safe_mapping(payload.get("author_observation"))
    final_answer_outcome = safe_mapping(payload.get("final_answer_outcome"))
    require(author_observation, "AF5B requires author observation")
    require(final_answer_outcome, "AF5B requires final answer outcome")
    text = final_answer_outcome.get("final_answer_text")
    require(text, "AF5B final answer text exists")
    require(
        text == final_answer_outcome.get("product_answer_text"),
        "AF5B product/final answer text mismatch",
    )
    require(
        text == author_observation.get("final_answer_text"),
        "AF5B observation/outcome text mismatch",
    )
    digest = _hash_text(str(text))
    for surface in (payload, author_observation, final_answer_outcome):
        if surface.get("final_answer_text_digest") is not None:
            require(
                surface.get("final_answer_text_digest") == digest,
                "AF5B final text digest mismatch",
            )


def _validate_flags(payload: Mapping[str, Any]) -> None:
    for field, expected in _FALSE_FLAGS.items():
        require(payload.get(field) is expected, f"AF5B {field} must be {expected}")
    for field, expected in _TRUE_FLAGS.items():
        require(payload.get(field) is expected, f"AF5B {field} must be {expected}")


def _validate_observed_matches_canonical(
    observed: Mapping[str, Any],
    canonical: Mapping[str, Any],
) -> None:
    if not observed:
        return
    canonical = safe_mapping(canonical)
    for field in (
        "author_response_finalization_id",
        "af5a_author_response_candidate_digest",
        "final_answer_text_digest",
        "final_answer_text_length",
        "final_answer_packet_ref_digest",
        "source_refs_digest",
        "citation_refs_digest",
        "caveat_refs_digest",
    ):
        require(observed.get(field) == canonical.get(field), f"AF5B observed {field} mismatch")
    observed_outcome = safe_mapping(observed.get("final_answer_outcome"))
    canonical_outcome = safe_mapping(canonical.get("final_answer_outcome"))
    if observed_outcome:
        require(
            observed_outcome.get("final_answer_text")
            == canonical_outcome.get("final_answer_text"),
            "AF5B observed final answer text mismatch",
        )


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key or "").casefold()
            require(token not in _FORBIDDEN_PAYLOAD_KEYS, f"AF5B cannot retain {key!r}")
            _reject_forbidden_payload(child)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for child in value:
            _reject_forbidden_payload(child)
    elif isinstance(value, str):
        _reject_private_text(value)


def _reject_private_text(value: str) -> None:
    lowered = str(value or "").casefold()
    require(
        not any(marker in lowered for marker in _PRIVATE_TEXT_MARKERS),
        "AF5B cannot retain private or closed text marker",
    )


def _hash_text(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _finalization_id(
    af5a_state: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> str:
    return (
        "followup-author-response-finalization:"
        f"{af5a_state.get('author_execution_from_af4d_id')}:"
        f"{str(candidate.get('author_response_candidate_digest') or '')[:16]}"
    )


__all__ = [
    "AG96I3AF5B_AF5A_RESPONSE_CANDIDATE_FINAL_ANSWER_MODE",
    "FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_REASON",
    "FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_SCHEMA_VERSION",
    "FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE",
    "FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS",
    "FollowupAuthorResponseFinalizationActionResult",
    "FollowupAuthorResponseFinalizationRecord",
    "build_followup_author_response_finalization_action_inputs",
    "build_followup_author_response_finalization_projection",
    "build_followup_author_response_finalization_record",
    "build_run_kernel_followup_author_response_finalization_state",
    "execute_followup_author_response_finalization_action",
    "reject_followup_author_response_finalization_input_spoof",
    "validate_followup_author_response_finalization_authorization",
    "validate_followup_author_response_finalization_observation_binding",
    "validate_run_kernel_followup_author_response_finalization_state",
]
