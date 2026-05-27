"""Passive controller mirror for source-class recovery diagnostics.

This module only records already-computed source-class recovery facts into
controller-shaped records. It does not call retrieval, providers, prompts, or
models, and it does not assemble persisted telemetry.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from core.run_controller import ControllerDecision, RetrievalAction, RunController

SOURCE_CLASS_EVIDENCE_SIGNAL_KEYS = (
    "source_tier_counts",
    "source_domain_counts",
    "top_source_domains",
    "unique_source_domain_count",
    "on_domain_source_count",
    "off_domain_source_count",
    "official_evidence_found",
    "community_signal_found",
    "low_trust_sources_found",
    "pollution_detected",
)


def _copy_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return deepcopy(list(value))
    return []


def _copy_evidence_signals(signals: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(signals[key])
        for key in SOURCE_CLASS_EVIDENCE_SIGNAL_KEYS
        if key in signals
    }


def record_source_class_recovery_recommendation(
    controller: RunController,
    *,
    source_class_recovery_telemetry: Mapping[str, Any],
    source_class_evidence_signals: Mapping[str, Any],
) -> RunController:
    """Mirror source-class recovery telemetry into passive controller records."""
    reason = source_class_recovery_telemetry.get("source_class_recovery_reason")
    queries = _copy_list(
        source_class_recovery_telemetry.get("source_class_recovery_queries")
    )
    missing_expected_source_classes = _copy_list(
        source_class_recovery_telemetry.get("missing_expected_source_classes")
    )
    trigger_fields = _copy_list(
        source_class_recovery_telemetry.get("source_class_recovery_trigger_fields")
    )

    signals = {
        "missing_expected_source_classes": missing_expected_source_classes,
        "source_class_recovery_trigger_fields": trigger_fields,
        **_copy_evidence_signals(source_class_evidence_signals),
    }

    recommended_actions: list[RetrievalAction] = []
    if (
        bool(
            source_class_recovery_telemetry.get(
                "source_class_recovery_recommended"
            )
        )
        and queries
    ):
        action = RetrievalAction(
            name="source_class_recovery_recommendation",
            queries=queries,
            active=False,
            shadow=True,
            reason=reason,
        )
        recommended_actions.append(action)
        controller.record_retrieval_action(action)

    controller.record_decision(
        ControllerDecision(
            name="source_class_recovery",
            active=False,
            shadow=True,
            reason=reason,
            signals=signals,
            recommended_actions=recommended_actions,
        )
    )
    return controller


__all__ = [
    "SOURCE_CLASS_EVIDENCE_SIGNAL_KEYS",
    "record_source_class_recovery_recommendation",
]
