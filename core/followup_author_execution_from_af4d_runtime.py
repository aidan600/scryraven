"""AG-96I3AF5A AF4D-bound Author execution seam, live disabled."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from core.followup_author_evidence_content_bridge_runtime import (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
    validate_run_kernel_followup_author_evidence_content_bridge_state,
)
from core.followup_author_invocation_construction_runtime import (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
    validate_run_kernel_followup_author_invocation_construction_state,
)
from core.followup_author_model_request_assembly_runtime import (
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS,
    validate_run_kernel_followup_author_model_request_assembly_state,
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

FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_SCHEMA_VERSION = "followup_author_execution_from_af4d_ag96i3af5a_v1"
FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE = "followup_author_execution_from_af4d"
AG96I3AF5A_AF4D_BOUND_AUTHOR_EXECUTION_LIVE_DISABLED_MODE = "ag96i3af5a_af4d_bound_author_execution_live_disabled"
FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS = "author_execution_from_af4d_completed_live_disabled"
FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_REASON = AG96I3AF5A_AF4D_BOUND_AUTHOR_EXECUTION_LIVE_DISABLED_MODE

MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS = 800

AUTHOR_MODEL_CALL_MODE_FAKE = "fake"
AUTHOR_MODEL_CALL_STATUS_COMPLETED_FAKE = "completed_fake"
AUTHOR_MODEL_CALL_SOURCE_FAKE_ADAPTER = "injected_fake_model_adapter"
AUTHOR_MODEL_CALL_MODE_LIVE_ADAPTER_MOCKED = "live_adapter_mocked"
AUTHOR_MODEL_CALL_STATUS_COMPLETED_MOCK_LIVE_ADAPTER = "completed_mock_live_adapter"
AUTHOR_MODEL_CALL_SOURCE_MOCK_LIVE_ADAPTER = "mock_live_model_adapter"
_MODEL_CALL_CUSTODY_FIELDS = (
    "author_model_call_mode",
    "author_model_call_status",
    "author_model_call_source",
    "max_model_calls",
    "model_calls_used",
    "mock_model_adapter_calls_used",
    "live_model_call_performed",
    "live_adapter_mocked",
    "fake_adapter_used",
    "broker_live_adapter_deferred",
    "broker_live_requested",
    "broker_live_execution_enabled",
    "prompt_raw_payload_retained",
    "model_request_raw_payload_retained",
    "provider_raw_payload_retained",
    "payload_raw_retained",
    "model_response_raw_payload_retained",
    "private_logs_retained",
    "db_cache_rows_retained",
    "full_trace_retained",
)
_FAKE_MODEL_CALL_CUSTODY = {
    "author_model_call_mode": AUTHOR_MODEL_CALL_MODE_FAKE,
    "author_model_call_status": AUTHOR_MODEL_CALL_STATUS_COMPLETED_FAKE,
    "author_model_call_source": AUTHOR_MODEL_CALL_SOURCE_FAKE_ADAPTER,
    "max_model_calls": 0,
    "model_calls_used": 0,
    "mock_model_adapter_calls_used": 0,
    "live_model_call_performed": False,
    "live_adapter_mocked": False,
    "fake_adapter_used": True,
    "broker_live_adapter_deferred": False,
    "broker_live_requested": False,
    "broker_live_execution_enabled": False,
    "prompt_raw_payload_retained": False,
    "model_request_raw_payload_retained": False,
    "provider_raw_payload_retained": False,
    "payload_raw_retained": False,
    "model_response_raw_payload_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
_MOCK_LIVE_ADAPTER_MODEL_CALL_CUSTODY = {
    "author_model_call_mode": AUTHOR_MODEL_CALL_MODE_LIVE_ADAPTER_MOCKED,
    "author_model_call_status": AUTHOR_MODEL_CALL_STATUS_COMPLETED_MOCK_LIVE_ADAPTER,
    "author_model_call_source": AUTHOR_MODEL_CALL_SOURCE_MOCK_LIVE_ADAPTER,
    "max_model_calls": 0,
    "model_calls_used": 0,
    "mock_model_adapter_calls_used": 1,
    "live_model_call_performed": False,
    "live_adapter_mocked": True,
    "fake_adapter_used": False,
    "broker_live_adapter_deferred": False,
    "broker_live_requested": False,
    "broker_live_execution_enabled": False,
    "prompt_raw_payload_retained": False,
    "model_request_raw_payload_retained": False,
    "provider_raw_payload_retained": False,
    "payload_raw_retained": False,
    "model_response_raw_payload_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}

_CLOSED_BASE_FLAGS = {
    field: False
    for field in "model_execution_allowed live_provider_call_allowed real_model_called ask_model_called execute_author_action_called author_observation_created final_answer_outcome_created prompt_text_retained request_text_retained model_response_retained provider_payload_retained report_text_retained final_text_retained final_text_included product_answer_ready citation_strings_included ordered_product_source_output_created".split()
} | {
    "author_execution_deferred": True,
    "live_validation_not_run": True,
    "not_for_product_answer_activation": True,
}
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    "prompt_text raw_prompt request_text raw_request_text assembled_author_model_request model_request_text invocation_text raw_invocation_text model_response raw_model_response final_answer_text report_text product_output output sanitized_excerpt_text raw_provider_payload provider_payload raw_payload db_row cache private_log full_trace secret api_key author_observation final_answer_outcome".split()
)
_CALLER_CONTROLLED_KEYS = frozenset(
    {
        *_FORBIDDEN_PAYLOAD_KEYS,
        *_MODEL_CALL_CUSTODY_FIELDS,
        *"followup_author_execution_from_af4d_state followup_author_execution_from_af4d_projection followup_author_execution_from_af4d_history bounded_sanitized_author_response_candidate bounded_sanitized_author_response_candidate_text author_response_candidate_digest author_response_candidate_length adapter_receipt_metadata adapter_invocation_count fake_adapter_used reconstructed_author_model_request_digest".split(),
    }
)
_REQUEST_TEXT_FIELDS = "bounded_user_request_text user_question question query request_text user_request_text".split()
_PRIVATE_TEXT_MARKERS = "raw_prompt|raw provider|raw_provider|provider_payload|api_key|secret|sanitized_excerpt_text|product_output|report_text|final_answer_text".split(
    "|"
)


class FollowupAuthorExecutionFromAF4DModelAdapter(Protocol):
    def __call__(
        self, request_text: str, *, request_digest: str, request_length: int, request_metadata: Mapping[str, Any]
    ) -> Mapping[str, Any] | str: ...


@dataclass(frozen=True, slots=True)
class TransientAuthorModelRequest:
    request_text: str
    request_digest: str
    request_length: int
    section_refs: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionFromAF4DActionResult:
    record: "FollowupAuthorExecutionFromAF4DRecord"
    observation: Any


@dataclass(frozen=True, slots=True)
class FollowupAuthorExecutionFromAF4DRecord:
    state: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return safe_mapping(self.state)


def reject_followup_author_execution_from_af4d_input_spoof(
    inputs: Mapping[str, Any] | None,
) -> None:
    _reject_forbidden_payload(dict(inputs or {}) if isinstance(inputs, Mapping) else {})
    reject_caller_controlled_inputs(
        inputs,
        caller_controlled_keys=_CALLER_CONTROLLED_KEYS,
        context_label="AF5A Author execution from AF4D action",
        closed_surface_rejector=_reject_forbidden_payload,
        check_raw_keys=True,
    )


def build_followup_author_execution_from_af4d_action_inputs(
    *,
    followup_author_model_request_assembly_state: Mapping[str, Any],
    followup_author_model_request_assembly_projection: Mapping[str, Any],
    followup_author_model_request_assembly_history: Sequence[Mapping[str, Any]],
    **_: Any,
) -> dict[str, Any]:
    af4d = safe_mapping(followup_author_model_request_assembly_state)
    af4d_projection = safe_mapping(followup_author_model_request_assembly_projection)
    af4d_history = [safe_mapping(item) for item in followup_author_model_request_assembly_history or []]
    copied = {
        "af4d_author_model_request_assembly_id": "author_model_request_assembly_id",
        "af4d_author_model_request_digest": "author_model_request_digest",
        "af4d_author_model_request_length": "author_model_request_length",
        "af4d_author_model_request_section_count": "author_model_request_section_count",
        "af4c_author_invocation_construction_id": "af4c_author_invocation_construction_id",
        "af4c_author_invocation_digest": "af4c_author_invocation_digest",
        "af4c_author_invocation_projection_digest": "af4c_author_invocation_projection_digest",
        "af4b2_author_evidence_content_bridge_id": "af4b2_author_evidence_content_bridge_id",
        "af4b2_author_evidence_content_bridge_digest": "af4b2_author_evidence_content_bridge_digest",
        "af4b2_author_evidence_content_projection_digest": "af4b2_author_evidence_content_projection_digest",
        "sanitized_author_evidence_content_payload_digest": "sanitized_author_evidence_content_payload_digest",
        "answer_bearing_sanitized_excerpt_ref_count": "answer_bearing_sanitized_excerpt_ref_count",
    }
    return {
        "run_id": af4d.get("run_id"),
        "checkpoint_id": af4d.get("checkpoint_id"),
        "packet_id": af4d.get("packet_id"),
        "author_execution_from_af4d_id": _execution_id(af4d),
        "author_execution_from_af4d_stage": FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE,
        "author_execution_from_af4d_mode": AG96I3AF5A_AF4D_BOUND_AUTHOR_EXECUTION_LIVE_DISABLED_MODE,
        "status": FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS,
        **{target: af4d.get(source) for target, source in copied.items()},
        "af4d_author_model_request_section_refs": safe_mapping_sequence(af4d.get("author_model_request_section_refs")),
        "af4d_author_model_request_ref_digest": _digest(safe_mapping(af4d.get("author_model_request_ref"))),
        "af4d_author_model_request_projection_digest": _digest(af4d_projection),
        "af4d_author_model_request_history_projection_digest": _digest(af4d_history[-1] if af4d_history else {}),
        "run_request_digest": af4d.get("run_request_digest"),
        **_FAKE_MODEL_CALL_CUSTODY,
        **_closed_flags_for_custody(_FAKE_MODEL_CALL_CUSTODY),
    }


def validate_followup_author_execution_from_af4d_authorization(
    *,
    action_inputs: Mapping[str, Any],
    **runtime_inputs: Any,
) -> None:
    _validated_context(action_inputs=safe_mapping(action_inputs), runtime_inputs=runtime_inputs)


def build_followup_author_execution_from_af4d_record(
    *,
    action_inputs: Mapping[str, Any],
    adapter_response: Mapping[str, Any] | str | None = None,
    observed_execution_state: Mapping[str, Any] | None = None,
    **runtime_inputs: Any,
) -> FollowupAuthorExecutionFromAF4DRecord:
    context = _validated_context(
        action_inputs=safe_mapping(action_inputs),
        runtime_inputs=runtime_inputs,
    )
    if observed_execution_state is not None:
        observed = safe_mapping(observed_execution_state)
        candidate = _candidate_from_observed(context, observed)
        receipt = _receipt_from_observed(context, observed)
    else:
        require(adapter_response is not None, "AF5A requires injected adapter response")
        candidate = _candidate_from_adapter_response(context, adapter_response)
        receipt = _receipt_from_adapter_response(context, adapter_response, candidate)
    model_call_custody = _model_call_custody_from_receipt(receipt)
    transient = context["transient"]
    state = {
        **context["action"],
        "schema_version": FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_SCHEMA_VERSION,
        "record_type": "followup_author_execution_from_af4d_record",
        "owner": "FollowupAuthorExecutionFromAF4DRuntime",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "af4d_author_model_request_consumed": True,
        "af4c_author_invocation_consumed": True,
        "af4b2_author_evidence_content_consumed": True,
        "transient_author_model_request_reconstructed": True,
        "transient_author_model_request_text_retained": False,
        "reconstructed_author_model_request_digest": transient.request_digest,
        "reconstructed_author_model_request_length": transient.request_length,
        "af4d_reconstructed_request_digest_match": True,
        "digest_match_proof": {
            "af4d_author_model_request_digest": context["af4d"].get("author_model_request_digest"),
            "reconstructed_author_model_request_digest": transient.request_digest,
            "digest_match": True,
            "request_text_retained": False,
        },
        "bounded_sanitized_author_response_candidate": candidate,
        "author_response_candidate_digest": candidate.get("author_response_candidate_digest"),
        "author_response_candidate_length": candidate.get("author_response_candidate_length"),
        "adapter_receipt_metadata": receipt,
        **model_call_custody,
        **_closed_flags_for_custody(model_call_custody),
    }
    _validate_closed(state)
    _reject_forbidden_payload(state)
    return FollowupAuthorExecutionFromAF4DRecord(safe_json(state))


def execute_followup_author_execution_from_af4d_action(
    action: Any,
    *,
    model_adapter: FollowupAuthorExecutionFromAF4DModelAdapter,
    **runtime_inputs: Any,
) -> FollowupAuthorExecutionFromAF4DActionResult:
    from core.run_kernel import ActionType, Observation, ObservationType

    action.validate(
        action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D,
        stage=FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE,
        expected_observation_type=ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_OBSERVED,
    )
    context = _validated_context(
        action_inputs=safe_mapping(action.inputs),
        runtime_inputs=runtime_inputs,
    )
    transient = context["transient"]
    adapter_response = model_adapter(
        transient.request_text,
        request_digest=transient.request_digest,
        request_length=transient.request_length,
        request_metadata={
            "stage": FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE,
            "mode": AG96I3AF5A_AF4D_BOUND_AUTHOR_EXECUTION_LIVE_DISABLED_MODE,
            "af4d_author_model_request_assembly_id": context["af4d"].get("author_model_request_assembly_id"),
            "af4d_author_model_request_digest": context["af4d"].get("author_model_request_digest"),
            "live_provider_call_allowed": False,
        },
    )
    record = build_followup_author_execution_from_af4d_record(
        action_inputs=action.inputs,
        adapter_response=adapter_response,
        **runtime_inputs,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_OBSERVED,
        status="completed",
        payload={"followup_author_execution_from_af4d_state": record.to_dict()},
    )
    return FollowupAuthorExecutionFromAF4DActionResult(
        record=record,
        observation=observation,
    )


def build_run_kernel_followup_author_execution_from_af4d_state(
    *,
    execution_record_state: Mapping[str, Any],
    observation_id: str | None,
) -> dict[str, Any]:
    state = {
        **safe_mapping(execution_record_state),
        "owner": "RunKernel.FollowupAuthorExecutionFromAF4D",
        "canonical_state": True,
        "observation_id": observation_id,
    }
    validate_run_kernel_followup_author_execution_from_af4d_state(execution_state=state)
    return safe_json(state)


def validate_run_kernel_followup_author_execution_from_af4d_state(
    *,
    execution_state: Mapping[str, Any],
) -> None:
    state = safe_mapping(execution_state)
    for condition, message in (
        (state.get("owner") == "RunKernel.FollowupAuthorExecutionFromAF4D", "AF5A owner"),
        (state.get("canonical_state") is True, "AF5A canonical state"),
        (state.get("trace_only") is False, "AF5A cannot be trace-only"),
        (state.get("storage_only") is False, "AF5A cannot be storage-only"),
        (state.get("status") == FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS, "AF5A status"),
        (state.get("af4d_author_model_request_consumed") is True, "AF5A AF4D"),
        (state.get("transient_author_model_request_reconstructed") is True, "AF5A reconstructed request"),
        (state.get("af4d_reconstructed_request_digest_match") is True, "AF5A digest match"),
        (
            state.get("af4d_author_model_request_digest") == state.get("reconstructed_author_model_request_digest"),
            "AF5A request digest mismatch",
        ),
    ):
        require(condition, message)
    _candidate_from_observed({"action": state}, state)
    _receipt_from_observed({"action": state, "transient": _transient_from_state(state)}, state)
    _validate_closed(state)
    _reject_forbidden_payload(state)


def build_followup_author_execution_from_af4d_projection(
    *,
    execution_state: Mapping[str, Any],
    **_: Any,
) -> dict[str, Any]:
    state = safe_mapping(execution_state)
    fields = "schema_version status author_execution_from_af4d_id author_execution_from_af4d_stage author_execution_from_af4d_mode af4d_author_model_request_assembly_id af4d_author_model_request_digest af4d_author_model_request_length af4d_author_model_request_section_count af4d_author_model_request_section_refs af4d_author_model_request_projection_digest af4c_author_invocation_construction_id af4c_author_invocation_digest af4c_author_invocation_projection_digest af4b2_author_evidence_content_bridge_id af4b2_author_evidence_content_projection_digest af4b2_author_evidence_content_bridge_digest sanitized_author_evidence_content_payload_digest answer_bearing_sanitized_excerpt_ref_count reconstructed_author_model_request_digest reconstructed_author_model_request_length af4d_reconstructed_request_digest_match digest_match_proof bounded_sanitized_author_response_candidate author_response_candidate_digest author_response_candidate_length adapter_receipt_metadata author_model_call_mode author_model_call_status author_model_call_source max_model_calls model_calls_used mock_model_adapter_calls_used live_model_call_performed live_adapter_mocked fake_adapter_used broker_live_adapter_deferred broker_live_requested broker_live_execution_enabled prompt_raw_payload_retained model_request_raw_payload_retained provider_raw_payload_retained payload_raw_retained model_response_raw_payload_retained private_logs_retained db_cache_rows_retained full_trace_retained".split()
    projection = {
        "owner": "RunKernel.FollowupAuthorExecutionFromAF4D",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        **{field: safe_json(state.get(field)) for field in fields},
        **_closed_flags_for_custody(state),
    }
    _reject_forbidden_payload(projection)
    return safe_json(projection)


def validate_followup_author_execution_from_af4d_observation_binding(
    *,
    action_inputs: Mapping[str, Any],
    observed_execution_state: Mapping[str, Any],
) -> None:
    action = safe_mapping(action_inputs)
    observed = safe_mapping(observed_execution_state)
    _validate_closed(observed)
    for field, expected in action.items():
        if field in _MODEL_CALL_CUSTODY_FIELDS or field == "injected_fake_model_adapter_used":
            continue
        require(observed.get(field) == expected, f"AF5A observation {field} mismatch")
    _candidate_from_observed({"action": action}, observed)
    _receipt_from_observed({"action": action, "transient": _transient_from_state(observed)}, observed)
    _reject_forbidden_payload(observed)


def reconstruct_transient_author_model_request_from_af4d(
    *,
    run_request: Mapping[str, Any],
    followup_author_invocation_construction_state: Mapping[str, Any],
    followup_author_evidence_content_bridge_state: Mapping[str, Any],
) -> TransientAuthorModelRequest:
    request_context = _bounded_user_request_context(run_request)
    require(request_context, "AF5A requires bounded user request text")
    sections = _transient_request_sections(
        request_context=request_context,
        invocation=safe_mapping(followup_author_invocation_construction_state),
        bridge=safe_mapping(followup_author_evidence_content_bridge_state),
    )
    digest = _digest({"sections": [_section_ref_with_digest(section) for section in sections]})
    length = sum(int(section.get("section_length") or 0) for section in sections)
    request_text = "\n\n".join(
        f"[{section.get('section_name')}]\n{section.get('section_text') or ''}" for section in sections
    )
    return TransientAuthorModelRequest(
        request_text=request_text,
        request_digest=digest,
        request_length=length,
        section_refs=tuple(_section_ref(section) for section in sections),
    )


def _validated_context(
    *,
    action_inputs: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    action = safe_mapping(action_inputs)
    af4d = _validate_af4d(runtime_inputs)
    af4c = _validate_af4c(af4d["state"], runtime_inputs)
    af4b2 = _validate_af4b2(af4d["state"], af4c["state"], runtime_inputs)
    expected = build_followup_author_execution_from_af4d_action_inputs(
        followup_author_model_request_assembly_state=af4d["state"],
        followup_author_model_request_assembly_projection=af4d["projection"],
        followup_author_model_request_assembly_history=af4d["history"],
    )
    require(action == expected, "AF5A action must match canonical AF4D inputs")
    transient = reconstruct_transient_author_model_request_from_af4d(
        run_request=safe_mapping(runtime_inputs.get("run_request")),
        followup_author_invocation_construction_state=af4c["state"],
        followup_author_evidence_content_bridge_state=af4b2["state"],
    )
    require(
        transient.request_digest == af4d["state"].get("author_model_request_digest"),
        "AF5A reconstructed request digest must match AF4D",
    )
    require(
        transient.request_length == af4d["state"].get("author_model_request_length"),
        "AF5A reconstructed request length must match AF4D",
    )
    require(
        list(transient.section_refs) == safe_mapping_sequence(af4d["state"].get("author_model_request_section_refs")),
        "AF5A reconstructed request sections must match AF4D",
    )
    return {
        "action": action,
        "af4d": af4d["state"],
        "af4c": af4c["state"],
        "af4b2": af4b2["state"],
        "transient": transient,
    }


def _validate_af4d(runtime_inputs: Mapping[str, Any]) -> dict[str, Any]:
    current = _current_surface(
        runtime_inputs,
        "followup_author_model_request_assembly",
        "RunKernel.FollowupAuthorModelRequestAssembly",
        "AF4D",
    )
    state, projection = current["state"], current["projection"]
    require(state, "AF5A requires canonical AF4D model request assembly")
    validate_run_kernel_followup_author_model_request_assembly_state(model_request_state=state)
    for condition, message in (
        (state.get("status") == FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS, "AF5A requires successful AF4D"),
        (state.get("author_model_request_ready_for_execution") is True, "AF5A requires AF4D execution-ready request"),
        (state.get("model_execution_allowed") is False, "AF5A requires AF4D live execution disabled"),
        (
            projection.get("author_model_request_digest") == state.get("author_model_request_digest"),
            "AF5A stale AF4D projection digest",
        ),
        (
            projection.get("author_model_request_assembly_id") == state.get("author_model_request_assembly_id"),
            "AF5A stale AF4D projection id",
        ),
    ):
        require(condition, message)
    return current


def _validate_af4c(
    af4d_state: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    current = _current_surface(
        runtime_inputs,
        "followup_author_invocation_construction",
        "RunKernel.FollowupAuthorInvocationConstruction",
        "AF4C",
    )
    state, projection = current["state"], current["projection"]
    require(state, "AF5A requires current AF4C invocation")
    validate_run_kernel_followup_author_invocation_construction_state(invocation_state=state)
    for condition, message in (
        (
            state.get("status") == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
            "AF5A requires constructed AF4C invocation",
        ),
        (state.get("author_invocation_ready_for_model") is True, "AF5A requires model-ready AF4C"),
        (
            af4d_state.get("af4c_author_invocation_construction_id") == state.get("author_invocation_construction_id"),
            "AF5A AF4D/AF4C id mismatch",
        ),
        (
            af4d_state.get("af4c_author_invocation_digest") == state.get("ag96i3_author_invocation_digest"),
            "AF5A AF4D/AF4C digest mismatch",
        ),
        (
            af4d_state.get("af4c_author_invocation_projection_digest") == _digest(projection),
            "AF5A stale AF4C projection digest",
        ),
        (state.get("model_execution_allowed") is False, "AF5A requires AF4C live execution disabled"),
    ):
        require(condition, message)
    return current


def _validate_af4b2(
    af4d_state: Mapping[str, Any],
    af4c_state: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    current = _current_surface(
        runtime_inputs,
        "followup_author_evidence_content_bridge",
        "RunKernel.FollowupAuthorEvidenceContentBridge",
        "AF4B2",
    )
    state, projection = current["state"], current["projection"]
    require(state, "AF5A requires current AF4B2 evidence content")
    validate_run_kernel_followup_author_evidence_content_bridge_state(bridge_state=state)
    payload = safe_mapping_sequence(state.get("sanitized_author_evidence_content_payload"))
    payload_digest = _digest({"payload": payload})
    for condition, message in (
        (
            state.get("status") == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
            "AF5A requires bound AF4B2 evidence content",
        ),
        (
            payload_digest == state.get("sanitized_author_evidence_content_payload_digest"),
            "AF5A stale AF4B2 content payload digest",
        ),
        (
            af4d_state.get("af4b2_author_evidence_content_bridge_id") == state.get("author_evidence_content_bridge_id"),
            "AF5A AF4D/AF4B2 id mismatch",
        ),
        (
            af4d_state.get("af4b2_author_evidence_content_bridge_digest") == state.get("content_bridge_digest"),
            "AF5A AF4D/AF4B2 digest mismatch",
        ),
        (
            af4d_state.get("af4b2_author_evidence_content_projection_digest") == _digest(projection),
            "AF5A stale AF4B2 projection digest",
        ),
        (
            af4d_state.get("sanitized_author_evidence_content_payload_digest") == payload_digest,
            "AF5A AF4D/AF4B2 content payload digest mismatch",
        ),
        (
            af4c_state.get("af4b2_author_evidence_content_bridge_digest") == state.get("content_bridge_digest"),
            "AF5A AF4C/AF4B2 digest mismatch",
        ),
        (
            af4c_state.get("sanitized_author_evidence_content_payload_digest") == payload_digest,
            "AF5A AF4C/AF4B2 content payload digest mismatch",
        ),
    ):
        require(condition, message)
    return current


def _candidate_from_adapter_response(
    context: Mapping[str, Any],
    adapter_response: Mapping[str, Any] | str,
) -> dict[str, Any]:
    if isinstance(adapter_response, Mapping):
        raw_text = (
            adapter_response.get("candidate_text") or adapter_response.get("text") or adapter_response.get("content")
        )
    else:
        raw_text = adapter_response
    text = clean_text(raw_text, limit=MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS + 1)
    require(text, "AF5A adapter response candidate required")
    return _candidate_from_text(context, text[:MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS])


def _candidate_from_observed(
    context: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = safe_mapping(observed.get("bounded_sanitized_author_response_candidate"))
    text = clean_text(
        candidate.get("bounded_sanitized_author_response_candidate_text"),
        limit=MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS + 1,
    )
    require(text, "AF5A observed response candidate text")
    require(
        text == candidate.get("bounded_sanitized_author_response_candidate_text"),
        "AF5A observed response candidate text must be canonical",
    )
    canonical = _candidate_from_text(context, text)
    require(candidate == canonical, "AF5A observed response candidate mismatch")
    return canonical


def _candidate_from_text(context: Mapping[str, Any], text: str) -> dict[str, Any]:
    require(len(text) <= MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS, "AF5A response candidate over bound")
    _reject_private_text(text)
    action = safe_mapping(context.get("action"))
    digest = _digest(
        {
            "bounded_sanitized_author_response_candidate_text": text,
            "af4d_author_model_request_digest": action.get("af4d_author_model_request_digest"),
        }
    )
    return safe_json(
        {
            "author_response_candidate_ref_id": f"af5a-author-response-candidate:{action.get('author_execution_from_af4d_id')}",
            "content_class": "bounded_sanitized_author_response_candidate",
            "sanitization_status": "bounded_sanitized",
            "bounded_sanitized_author_response_candidate_text": text,
            "author_response_candidate_digest": digest,
            "author_response_candidate_length": len(text),
            "author_response_candidate_char_limit": MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS,
            "model_response_retained": False,
            "provider_payload_retained": False,
            "product_output_created": False,
        }
    )


def _receipt_from_adapter_response(
    context: Mapping[str, Any],
    adapter_response: Mapping[str, Any] | str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = safe_mapping(adapter_response.get("metadata")) if isinstance(adapter_response, Mapping) else {}
    transient = context["transient"]
    receipt = {
        "adapter_receipt_id": f"af5a-adapter-receipt:{safe_mapping(context.get('action')).get('author_execution_from_af4d_id')}",
        "adapter_kind": clean_text(metadata.get("adapter_kind") or "injected_fake_model_adapter", limit=100),
        "adapter_invoked": True,
        "adapter_invocation_count": _bounded_int(
            metadata.get("adapter_invocation_count") or metadata.get("invocation_count") or 1
        ),
        "request_digest_seen": clean_text(metadata.get("request_digest_seen") or transient.request_digest, limit=160),
        "request_length_seen": _bounded_int(metadata.get("request_length_seen") or len(transient.request_text)),
        "response_candidate_digest": candidate.get("author_response_candidate_digest"),
        "request_text_retained": False,
        "model_response_retained": False,
        "provider_payload_retained": False,
        "live_provider_call_allowed": False,
        "real_model_called": False,
        "ask_model_called": False,
        **_model_call_custody_from_adapter_metadata(metadata),
    }
    _validate_receipt(context, receipt)
    return safe_json(receipt)


def _receipt_from_observed(
    context: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = safe_mapping(observed.get("adapter_receipt_metadata"))
    _validate_receipt(context, receipt)
    return safe_json(receipt)


def _validate_receipt(
    context: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> None:
    transient = context.get("transient")
    request_digest = (
        transient.request_digest
        if isinstance(transient, TransientAuthorModelRequest)
        else safe_mapping(context.get("action")).get("af4d_author_model_request_digest")
    )
    for condition, message in (
        (receipt.get("adapter_invoked") is True, "AF5A adapter invoked"),
        (receipt.get("adapter_invocation_count") == 1, "AF5A adapter must be invoked exactly once"),
        (receipt.get("request_digest_seen") == request_digest, "AF5A adapter receipt request digest mismatch"),
    ):
        require(condition, message)
    for field in "request_text_retained model_response_retained provider_payload_retained live_provider_call_allowed real_model_called ask_model_called".split():
        require(receipt.get(field) is False, f"AF5A receipt {field}=False")
    _validate_model_call_custody(receipt)
    _reject_forbidden_payload(receipt)


def _transient_from_state(state: Mapping[str, Any]) -> TransientAuthorModelRequest:
    digest = clean_text(
        state.get("reconstructed_author_model_request_digest") or state.get("af4d_author_model_request_digest"),
        limit=160,
    )
    return TransientAuthorModelRequest(
        request_text="",
        request_digest=digest or "",
        request_length=int(state.get("reconstructed_author_model_request_length") or 0),
        section_refs=tuple(safe_mapping_sequence(state.get("af4d_author_model_request_section_refs"))),
    )


def _bounded_user_request_context(request: Mapping[str, Any]) -> dict[str, Any]:
    data = safe_mapping(request)
    candidates = [(field, data.get(field)) for field in _REQUEST_TEXT_FIELDS]
    candidates += [
        (f"{field}.text", safe_mapping(data.get(field)).get("text"))
        for field in ("bounded_user_request", "user_request")
    ]
    for field, value in candidates:
        if text := clean_text(value, limit=2000):
            return {
                "source_field": field,
                "request_text": text,
                "request_digest": _digest({"field": field, "value": text}),
                "request_length": len(text),
            }
    return {}


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
    manifest = safe_mapping(invocation.get("invocation_manifest"))
    manifest_refs = {
        "rendered_source_entries": safe_mapping(manifest.get("rendered_source_entries_refs_or_digest")),
        "mandatory_caveats": safe_mapping(manifest.get("mandatory_caveats_refs_or_digest")),
        "prohibited_upgrades": safe_mapping(manifest.get("prohibited_upgrades_refs_or_digest")),
        "source_bound_unknowns": safe_mapping(manifest.get("source_bound_unknowns_refs_or_digest")),
    }
    invocation_refs = {
        "invocation_id": invocation.get("author_invocation_construction_id"),
        "invocation_digest": invocation.get("ag96i3_author_invocation_digest"),
        "payload_envelope_digest": invocation.get("payload_envelope_digest"),
        "content_payload_digest": invocation.get("sanitized_author_evidence_content_payload_digest"),
        "excerpt_refs": invocation.get("answer_bearing_sanitized_excerpt_refs"),
    }
    sections = [
        ("bounded_user_request", str(request_context.get("request_text") or "")),
        ("af4c_invocation_manifest", repr(safe_json(invocation_refs))),
        ("af4b2_sanitized_evidence_content", "\n".join(excerpt_lines)),
        ("source_and_caveat_refs", repr(safe_json(manifest_refs))),
    ]
    return [
        {
            "section_name": name,
            "section_text": text,
            "section_digest": _digest({"section_name": name, "section_text": text}),
            "section_length": len(text),
        }
        for name, text in sections
    ]


def _transient_excerpt_line(excerpt: Mapping[str, Any]) -> str:
    text, ref, evidence, source = (
        clean_text(excerpt.get(field), limit=1000 if field == "sanitized_excerpt_text" else 220)
        for field in ("sanitized_excerpt_text", "excerpt_ref_id", "evidence_id", "source_id")
    )
    return f"{ref}|{evidence}|{source}: {text}"


def _section_ref_with_digest(section: Mapping[str, Any]) -> dict[str, Any]:
    return {key: section.get(key) for key in ("section_name", "section_digest", "section_length")}


def _section_ref(section: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "section_ref_id": f"af4d-author-model-request-section:{section.get('section_name')}",
        **_section_ref_with_digest(section),
        "section_text_retained": False,
    }


def _validate_closed(state: Mapping[str, Any]) -> None:
    for field, expected in _closed_flags_for_custody(state).items():
        require(state.get(field) is expected, f"AF5A {field} must be {expected}")
    _validate_model_call_custody(state)


def _validate_model_call_custody(surface: Mapping[str, Any]) -> None:
    current = safe_mapping(surface)
    expected = _expected_model_call_custody(current)
    for field, expected_value in expected.items():
        require(
            current.get(field) == expected_value,
            f"AF5A {field} must be {expected_value!r}",
        )


def _model_call_custody_from_adapter_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    mode = clean_text(metadata.get("author_model_call_mode"), limit=100)
    if mode == AUTHOR_MODEL_CALL_MODE_LIVE_ADAPTER_MOCKED or metadata.get("live_adapter_mocked") is True:
        return dict(_MOCK_LIVE_ADAPTER_MODEL_CALL_CUSTODY)
    return dict(_FAKE_MODEL_CALL_CUSTODY)


def _model_call_custody_from_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    custody = {field: safe_json(safe_mapping(receipt).get(field)) for field in _MODEL_CALL_CUSTODY_FIELDS}
    _validate_model_call_custody(custody)
    return custody


def _expected_model_call_custody(surface: Mapping[str, Any]) -> Mapping[str, Any]:
    mode = surface.get("author_model_call_mode")
    if mode == AUTHOR_MODEL_CALL_MODE_LIVE_ADAPTER_MOCKED:
        return _MOCK_LIVE_ADAPTER_MODEL_CALL_CUSTODY
    return _FAKE_MODEL_CALL_CUSTODY


def _closed_flags_for_custody(custody: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_CLOSED_BASE_FLAGS,
        "injected_fake_model_adapter_used": safe_mapping(custody).get("fake_adapter_used") is True,
    }


def _reject_forbidden_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            token = str(key or "").casefold()
            require(token not in _FORBIDDEN_PAYLOAD_KEYS, f"AF5A cannot retain {key!r}")
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
        "AF5A cannot retain private or closed text marker",
    )


def _bounded_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise PermissionError("AF5A adapter receipt integer invalid") from exc
    require(result >= 0, "AF5A adapter receipt integer negative")
    return result


def _history(runtime_inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [safe_mapping(item) for item in runtime_inputs.get(f"{prefix}_history", [])]


def _current_surface(
    runtime_inputs: Mapping[str, Any],
    prefix: str,
    owner: str,
    label: str,
) -> dict[str, Any]:
    state = safe_mapping(runtime_inputs.get(f"{prefix}_state"))
    projection = safe_mapping(runtime_inputs.get(f"{prefix}_projection"))
    history = _history(runtime_inputs, prefix)
    require(projection.get("owner") == owner, f"AF5A {label} projection owner")
    require(projection.get("canonical_state") is True, f"AF5A canonical {label}")
    require(history and history[-1] == projection, f"AF5A current {label} history")
    return {"state": state, "projection": projection, "history": history}


def _execution_id(af4d_state: Mapping[str, Any]) -> str:
    return (
        "followup-author-execution-from-af4d:"
        f"{af4d_state.get('author_model_request_assembly_id')}:"
        f"{str(af4d_state.get('author_model_request_digest') or '')[:16]}"
    )
