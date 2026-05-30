from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from core.planned_observed_diagnostics import build_controller_diagnostics_payload
from core.retrieval_budget_pressure import build_retrieval_budget_pressure_shadow
from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from core.source_class_recovery import build_source_class_recovery_candidate_v2
from core.source_class_recovery_diagnostics import (
    SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY,
    build_source_class_recovery_validation_packet,
)

_CONTROLLER_DIAGNOSTICS_STAGE_ITEMS_LIMIT_BYTES = 8 * 1024
_CONTROLLER_DIAGNOSTICS_MAX_SIZE_BYTES = 12 * 1024
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeTraceExportAttachmentResult:
    """Passive attachment result returned to the legacy orchestrator handoff."""

    execution_trace: dict[str, Any]
    source_class_recovery_validation_packet: dict[str, Any] | None


def _json_payload_size_bytes(payload: dict[str, Any]) -> int:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return len(encoded)


def _build_controller_diagnostics_payload_with_size_guard(
    execution_trace: dict[str, Any],
    *,
    logger: logging.Logger | None = None,
) -> dict[str, Any] | None:
    active_logger = logger or _LOGGER
    try:
        payload = build_controller_diagnostics_payload(
            execution_trace,
            include_stage_items=True,
        )
        if (
            _json_payload_size_bytes(payload)
            <= _CONTROLLER_DIAGNOSTICS_STAGE_ITEMS_LIMIT_BYTES
        ):
            return payload

        payload = build_controller_diagnostics_payload(
            execution_trace,
            include_stage_items=False,
        )
        if _json_payload_size_bytes(payload) <= _CONTROLLER_DIAGNOSTICS_MAX_SIZE_BYTES:
            return payload
    except Exception as exc:
        active_logger.warning("Non-fatal controller diagnostics omitted: %s", exc)
    return None


def _build_source_class_recovery_validation_packet_safe(
    execution_trace: dict[str, Any],
    *,
    evidence_bundle_source_class_counts: dict[str, Any] | None,
    logger: logging.Logger | None = None,
) -> dict[str, Any] | None:
    active_logger = logger or _LOGGER
    try:
        return build_source_class_recovery_validation_packet(
            execution_trace,
            evidence_bundle_source_class_counts=evidence_bundle_source_class_counts,
        )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal source-class recovery validation packet omitted: %s",
            exc,
        )
    return None


def attach_runtime_trace_export_compatibility_payloads(
    execution_trace: dict[str, Any],
    *,
    recovered_passages: Iterable[Mapping[str, Any]] | None = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    max_iterations: int | None = None,
    evidence_bundle_source_class_counts: dict[str, Any] | None = None,
    session_payload: MutableMapping[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> RuntimeTraceExportAttachmentResult:
    """Attach passive runtime trace/export/checkpoint compatibility payloads.

    The helper receives already-computed runtime facts, preserves legacy trace
    field names, mirrors observer projections into checkpoint packets through
    existing projection helpers, and optionally attaches the final execution
    trace to the session payload. It does not choose providers, queries,
    candidate admission, final evidence, citations, prompts, or answer prose.
    """

    attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=recovered_passages,
        final_top_evidence=final_top_evidence,
        logger=logger,
    )
    execution_trace["retrieval_budget_pressure_shadow"] = (
        build_retrieval_budget_pressure_shadow(
            trace=execution_trace,
            max_iterations=max_iterations,
            final_top_evidence=final_top_evidence,
        )
    )
    execution_trace["source_class_recovery_candidate_v2"] = (
        build_source_class_recovery_candidate_v2(execution_trace)
    )
    source_class_recovery_validation_packet = (
        _build_source_class_recovery_validation_packet_safe(
            execution_trace,
            evidence_bundle_source_class_counts=evidence_bundle_source_class_counts,
            logger=logger,
        )
    )
    if source_class_recovery_validation_packet is not None:
        execution_trace[SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY] = (
            source_class_recovery_validation_packet
        )
    controller_diagnostics_payload = (
        _build_controller_diagnostics_payload_with_size_guard(
            execution_trace,
            logger=logger,
        )
    )
    if controller_diagnostics_payload is not None:
        execution_trace["controller_diagnostics"] = controller_diagnostics_payload
    if session_payload is not None:
        session_payload["execution_trace"] = execution_trace

    return RuntimeTraceExportAttachmentResult(
        execution_trace=execution_trace,
        source_class_recovery_validation_packet=source_class_recovery_validation_packet,
    )


__all__ = [
    "RuntimeTraceExportAttachmentResult",
    "attach_runtime_trace_export_compatibility_payloads",
]
