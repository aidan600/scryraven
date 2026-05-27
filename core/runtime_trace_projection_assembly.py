from __future__ import annotations

import logging
from typing import Any

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
from core.retrieval_batch_projection import (
    RETRIEVAL_BATCH_PROJECTION_TRACE_KEY,
    build_retrieval_batch_projection_trace,
)

_LOGGER = logging.getLogger(__name__)


def attach_passive_runtime_projection_traces(
    execution_trace: dict[str, Any],
    *,
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
    return execution_trace


__all__ = ["attach_passive_runtime_projection_traces"]
