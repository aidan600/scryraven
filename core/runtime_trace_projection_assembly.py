from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from core.allocation_result_candidate_custody import (
    ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
    build_allocation_result_candidate_custody_trace,
)
from core.authority_candidate_passport import (
    AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
    build_authority_candidate_passport_trace,
)
from core.controller_evidence_ledger import (
    CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
    build_controller_evidence_ledger_trace,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY,
    build_official_canonical_recovery_visibility_trace,
)
from core.official_source_obligation_bridge import (
    OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY,
    build_official_source_obligation_bridge_trace,
)
from core.official_source_obligation_candidate_visibility import (
    build_official_source_obligation_candidate_visibility_traces,
)
from core.official_source_survival_projection import (
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY,
    build_official_source_survival_projection_trace,
)
from core.provider_result_represented_visibility import (
    PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
    build_provider_result_represented_visibility_trace,
)
from core.retrieval_batch_projection import (
    RETRIEVAL_BATCH_PROJECTION_TRACE_KEY,
    build_retrieval_batch_projection_trace,
)

_LOGGER = logging.getLogger(__name__)


def attach_passive_runtime_projection_traces(
    execution_trace: dict[str, Any],
    *,
    recovered_passages: Iterable[Mapping[str, Any]] | None = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    surface_visibility: Mapping[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Attach passive controller projections to an assembled runtime trace."""
    active_logger = logger or _LOGGER
    try:
        retrieval_batch_projection_trace = build_retrieval_batch_projection_trace(
            runtime_trace=execution_trace
        )
        execution_trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY] = (
            retrieval_batch_projection_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY] = (
                retrieval_batch_projection_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal retrieval-batch passive projection omitted: %s",
            exc,
        )
    try:
        official_source_survival_projection_trace = (
            build_official_source_survival_projection_trace(
                runtime_trace=execution_trace
            )
        )
        execution_trace[OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY] = (
            official_source_survival_projection_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY] = (
                official_source_survival_projection_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official-source survival projection omitted: %s",
            exc,
        )
    try:
        official_source_obligation_candidate_traces = (
            build_official_source_obligation_candidate_visibility_traces(
                runtime_trace=execution_trace
            )
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        for key, trace in official_source_obligation_candidate_traces.items():
            execution_trace[key] = trace
            if isinstance(checkpoint_packet, dict):
                checkpoint_packet[key] = trace
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official-source obligation/candidate projection omitted: %s",
            exc,
        )
    try:
        bridge_trace = execution_trace.get(OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY)
        if not isinstance(bridge_trace, dict):
            bridge_trace = build_official_source_obligation_bridge_trace(
                runtime_trace=execution_trace
            )
            execution_trace[OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY] = (
                bridge_trace
            )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY] = (
                bridge_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official-source obligation bridge projection omitted: %s",
            exc,
        )
    try:
        acquisition_trace = execution_trace.get(
            OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(acquisition_trace, dict) and isinstance(
            checkpoint_packet,
            dict,
        ):
            checkpoint_packet[
                OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY
            ] = acquisition_trace
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official/canonical acquisition trace mirror omitted: %s",
            exc,
        )
    try:
        admission_trace = execution_trace.get(
            OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(admission_trace, dict) and isinstance(
            checkpoint_packet,
            dict,
        ):
            checkpoint_packet[
                OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY
            ] = admission_trace
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official/canonical admission trace mirror omitted: %s",
            exc,
        )
    try:
        allocation_result_custody_trace = (
            build_allocation_result_candidate_custody_trace(execution_trace)
        )
        execution_trace[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY] = (
            allocation_result_custody_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY] = (
                allocation_result_custody_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal allocation-result candidate custody omitted: %s",
            exc,
        )
    try:
        passport_trace = build_authority_candidate_passport_trace(
            lifecycle_trace=execution_trace,
            recovered_passages=recovered_passages,
            final_top_evidence=final_top_evidence,
            surface_visibility=surface_visibility,
        )
        execution_trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY] = passport_trace
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY] = (
                passport_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal authority-candidate passport projection omitted: %s",
            exc,
        )
    try:
        provider_result_bridge_trace = (
            build_provider_result_represented_visibility_trace(execution_trace)
        )
        execution_trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY] = (
            provider_result_bridge_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY] = (
                provider_result_bridge_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal provider-result represented bridge omitted: %s",
            exc,
        )
    try:
        visibility_trace = build_official_canonical_recovery_visibility_trace(
            execution_trace
        )
        execution_trace[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY] = (
            visibility_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY] = (
                visibility_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official/canonical recovery visibility export omitted: %s",
            exc,
        )
    try:
        ledger_trace = build_controller_evidence_ledger_trace(
            execution_trace,
            final_top_evidence=final_top_evidence,
            final_citations=_final_citations_from_execution_trace(
                execution_trace,
                final_top_evidence=final_top_evidence,
            ),
            surface_visibility=surface_visibility,
        )
        execution_trace[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY] = ledger_trace
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY] = ledger_trace
    except Exception as exc:
        active_logger.warning(
            "Non-fatal controller evidence ledger custody omitted: %s",
            exc,
        )
    try:
        allocation_result_custody_trace = (
            build_allocation_result_candidate_custody_trace(execution_trace)
        )
        execution_trace[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY] = (
            allocation_result_custody_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY] = (
                allocation_result_custody_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal allocation-result custody visibility refresh omitted: %s",
            exc,
        )
    try:
        if CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY not in execution_trace:
            return execution_trace
        visibility_trace = build_official_canonical_recovery_visibility_trace(
            execution_trace
        )
        execution_trace[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY] = (
            visibility_trace
        )
        checkpoint_packet = execution_trace.get(
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
        )
        if isinstance(checkpoint_packet, dict):
            checkpoint_packet[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY] = (
                visibility_trace
            )
    except Exception as exc:
        active_logger.warning(
            "Non-fatal official/canonical visibility ledger refresh omitted: %s",
            exc,
        )
    return execution_trace


def _final_citations_from_execution_trace(
    execution_trace: Mapping[str, Any],
    *,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], ...]:
    survival = execution_trace.get("final_authority_citation_survival")
    if not isinstance(survival, Mapping) or not _positive_int(
        survival.get("selected_authority_evidence_count")
    ):
        return ()

    final_by_source_id: dict[str, Mapping[str, Any]] = {}
    for source in final_top_evidence or ():
        if not isinstance(source, Mapping):
            continue
        source_id = _clean_text(source.get("source_id"))
        if source_id:
            final_by_source_id.setdefault(source_id, source)

    citations: list[dict[str, Any]] = []
    source_ids = execution_trace.get("final_answer_source_ids_used")
    if not isinstance(source_ids, (list, tuple, set)):
        return ()
    for source_id in source_ids:
        clean_id = _clean_text(source_id)
        if not clean_id:
            continue
        source = final_by_source_id.get(clean_id, {})
        citations.append(
            {
                "citation_id": clean_id,
                "source_id": clean_id,
                "url": _clean_text(source.get("url")),
                "source_url": _clean_text(source.get("url")),
                "source_class": _clean_text(source.get("source_class")),
                "source_tier": _clean_text(source.get("source_tier")),
            }
        )
    return tuple(citations)


def _positive_int(value: Any) -> bool:
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return False


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value or "").strip().split())


__all__ = ["attach_passive_runtime_projection_traces"]
