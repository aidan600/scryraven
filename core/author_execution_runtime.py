"""RunKernel-authorized Author execution runtime for AG-91K."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from core.final_answer_packet import (
    AuthorInputStatus,
    FinalAnswerAuthorInputPayload,
)
from core.quantitative_consistency import (
    apply_quantitative_consistency_guard,
    build_two_item_normalized_consistency_diagnostic,
    is_two_item_calorie_gram_comparison_candidate,
)
from core.run_kernel import (
    AUTHOR_EXECUTION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)

AskModel = Callable[..., Any]
StreamDisplay = Callable[[Iterable[str]], None]


@dataclass(frozen=True, slots=True)
class AuthorExecutionResult:
    """Final report text plus compact RunKernel observation."""

    report: str
    observation: Observation
    author_seconds: float
    stream_buffered: bool
    stream_displayed: bool
    quantitative_consistency_telemetry: Mapping[str, Any] = field(default_factory=dict)
    quantitative_consistency_guard_telemetry: Mapping[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class AuthorExecutionHandoff:
    """RunKernel-reduced AuthorExecutor result with legacy local values."""

    result: AuthorExecutionResult
    report: str
    author_seconds: float
    synthesis_seconds: float
    quantitative_guard_stream_buffered: bool
    quantitative_consistency_telemetry: Mapping[str, Any]
    quantitative_consistency_guard_telemetry: Mapping[str, Any]


def _hash_text(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _require_action_payload_alignment(
    action: AuthorizedAction,
    payload: FinalAnswerAuthorInputPayload,
) -> None:
    if payload.status is not AuthorInputStatus.AUTHOR_INPUT_READY:
        raise ValueError("Author executor requires author_input_ready payload")
    if not payload.packet_id:
        raise ValueError("Author executor requires packet_id")
    if "FINAL ANSWER PACKET AUTHORITY" not in payload.prompt:
        raise ValueError("Author executor requires packet authority in prompt")
    expected = {
        "packet_id": payload.packet_id,
        "author_system_prompt_key": payload.author_system_prompt_key,
        "author_effort": payload.author_effort,
        "author_provider": payload.author_provider,
        "author_model": payload.author_model,
    }
    for key, value in expected.items():
        action_value = action.inputs.get(key)
        if value is not None and action_value != value:
            raise ValueError(f"Author action {key} does not match packet payload")


def _stream_report(
    stream_out: Any,
    *,
    stream_display: StreamDisplay | None,
    stream_buffered: bool,
) -> tuple[str, bool]:
    if isinstance(stream_out, str):
        return str(stream_out or ""), False

    chunks: list[str] = []

    def _author_stream_iter() -> Iterable[str]:
        for chunk in stream_out:
            chunks.append(str(chunk))
            yield str(chunk)

    stream_displayed = stream_display is not None and not stream_buffered
    if stream_displayed:
        stream_display(_author_stream_iter())
    else:
        for _ in _author_stream_iter():
            pass
    return "".join(chunks), stream_displayed


def execute_author_action(
    action: AuthorizedAction,
    *,
    author_payload: FinalAnswerAuthorInputPayload,
    ask_model: AskModel,
    system_prompt_registry: Mapping[str, str],
    base_url: str | None,
    api_key: str | None,
    query: str,
    quantitative_packet: Any | None = None,
    calculation_results: Any | None = None,
    stream_display: StreamDisplay | None = None,
) -> AuthorExecutionResult:
    """Execute the Author model call from a packet-derived payload."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.AUTHOR_EXECUTE,
        stage=AUTHOR_EXECUTION_STAGE,
        expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
    )
    _require_action_payload_alignment(authorized, author_payload)
    system_prompt = system_prompt_registry.get(author_payload.author_system_prompt_key)
    if system_prompt is None:
        raise ValueError("Author system prompt key is unavailable")

    stream_buffered = bool(
        stream_display is not None and is_two_item_calorie_gram_comparison_candidate(query)
    )
    started = time.monotonic()
    stream_out = ask_model(
        author_payload.prompt,
        system_prompt,
        provider=author_payload.author_provider,
        model=author_payload.author_model,
        effort=author_payload.author_effort,
        base_url=base_url,
        api_key=api_key,
        stream=True,
        use_reasoning=False,
    )
    report, stream_displayed = _stream_report(
        stream_out,
        stream_display=stream_display,
        stream_buffered=stream_buffered,
    )
    report = str(report or "")
    quantitative_consistency_telemetry = build_two_item_normalized_consistency_diagnostic(
        query=query,
        final_answer=report,
        quantitative_packet=quantitative_packet,
        calculation_results=calculation_results,
    )
    report, quantitative_consistency_guard_telemetry = apply_quantitative_consistency_guard(
        query=query,
        final_answer=report,
        diagnostic=quantitative_consistency_telemetry,
        quantitative_packet=quantitative_packet,
        calculation_results=calculation_results,
    )
    author_seconds = max(0.0, time.monotonic() - started)
    observation_payload = {
        "owner": "RunKernel.AuthorExecutor",
        "packet_id": author_payload.packet_id,
        "author_payload_status": author_payload.status.value,
        "prompt_hash": _hash_text(author_payload.prompt),
        "prompt_length": len(author_payload.prompt),
        "prompt_text_included": False,
        "authority_block_hash": (
            _hash_text(author_payload.authority_block)
            if author_payload.authority_block
            else None
        ),
        "authority_block_length": len(author_payload.authority_block),
        "author_provider": author_payload.author_provider,
        "author_model": author_payload.author_model,
        "author_effort": author_payload.author_effort,
        "author_system_prompt_key": author_payload.author_system_prompt_key,
        "citation_source_ids": list(author_payload.citation_source_ids),
        "citation_ineligible_count": len(author_payload.citation_ineligible_refs),
        "missing_source_obligation_count": len(
            author_payload.missing_source_obligations
        ),
        "partial_source_obligation_count": len(
            author_payload.partial_source_obligations
        ),
        "satisfied_source_obligation_count": len(
            author_payload.satisfied_source_obligations
        ),
        "source_bound_numeric_unknown_count": len(
            author_payload.source_bound_numeric_unknowns
        ),
        "readiness_status": author_payload.readiness_status,
        "final_answer_posture": author_payload.final_answer_posture,
        "sufficiency_decision": author_payload.sufficiency_decision,
        "claim_postures": list(author_payload.claim_postures),
        "mandatory_caveat_count": len(author_payload.mandatory_caveats),
        "prohibited_upgrade_count": len(author_payload.prohibited_upgrades),
        "authority_payload_ref": dict(author_payload.authority_payload),
        "report_hash": _hash_text(report),
        "report_length": len(report),
        "final_text_included": False,
        "author_seconds": author_seconds,
        "stream_requested": True,
        "stream_buffered": stream_buffered,
        "stream_displayed": stream_displayed,
        "quantitative_consistency_telemetry": dict(
            quantitative_consistency_telemetry or {}
        ),
        "quantitative_consistency_guard_telemetry": dict(
            quantitative_consistency_guard_telemetry or {}
        ),
    }
    return AuthorExecutionResult(
        report=report,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload=observation_payload,
        ),
        author_seconds=author_seconds,
        stream_buffered=stream_buffered,
        stream_displayed=stream_displayed,
        quantitative_consistency_telemetry=quantitative_consistency_telemetry,
        quantitative_consistency_guard_telemetry=quantitative_consistency_guard_telemetry,
    )


def execute_author_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    ask_model: AskModel,
    system_prompt_registry: Mapping[str, str],
    base_url: str | None,
    api_key: str | None,
    stream_display: StreamDisplay | None = None,
) -> AuthorExecutionHandoff:
    """Authorize, execute, and reduce the packet-derived AuthorExecutor handoff."""

    action = run_kernel.authorize_author_execution(
        inputs={
            "packet_action_id": runtime_scope["final_answer_packet_action"].action_id,
        }
    )
    economist_safety_telemetry = runtime_scope.get("economist_safety_telemetry") or {}
    execution = execute_author_action(
        action,
        author_payload=runtime_scope["final_answer_author_payload"],
        ask_model=ask_model,
        system_prompt_registry=system_prompt_registry,
        base_url=base_url,
        api_key=api_key,
        query=runtime_scope["query"],
        quantitative_packet=economist_safety_telemetry.get("quantitative_packet"),
        calculation_results=economist_safety_telemetry.get("calculation_results"),
        stream_display=stream_display,
    )
    run_kernel.reduce(execution.observation)
    return AuthorExecutionHandoff(
        result=execution,
        report=execution.report,
        author_seconds=execution.author_seconds,
        synthesis_seconds=execution.author_seconds,
        quantitative_guard_stream_buffered=execution.stream_buffered,
        quantitative_consistency_telemetry=execution.quantitative_consistency_telemetry,
        quantitative_consistency_guard_telemetry=(
            execution.quantitative_consistency_guard_telemetry
        ),
    )


__all__ = [
    "AuthorExecutionHandoff",
    "AuthorExecutionResult",
    "execute_author_action",
    "execute_author_handoff_from_scope",
]
