"""AG-75A-Z operational handoff for allocation candidates.

This module returns admitted allocation-result candidates as inputs for the
existing recovered-evidence disposition/selection corridor. It does not select
evidence, classify sources, evaluate fit, write final prose, or format
citations.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.allocation_result_candidate_custody import (
    build_allocation_result_candidate_custody_projection,
)

ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION = (
    "allocation_candidate_selection_activation_ag75a_z_v1"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_LOWER_TIER_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "context", "analysis"}
)
_LOWER_TIER_CLASSES = frozenset({"secondary", "secondary_only", "context"})
_MISSING_CLASSIFICATION_VALUES = frozenset({"", UNKNOWN, NOT_OBSERVABLE})
_MISSING_CURRENTNESS_VALUES = frozenset({"", UNKNOWN, NOT_OBSERVABLE})


def allocation_result_candidates_for_existing_selection_corridor(
    runtime_trace: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return admitted allocation candidates eligible for the existing selector."""

    custody = build_allocation_result_candidate_custody_projection(runtime_trace)
    if custody.get("allocation_execution_authorized") is not True:
        return []
    if custody.get("admission_used") is not True:
        return []

    candidates: list[dict[str, Any]] = []
    for candidate in _record_list(custody.get("represented_candidate_inputs")):
        if not _eligible_for_existing_selection_corridor(candidate):
            continue
        candidates.append(_selection_candidate(candidate))
    return candidates


def _eligible_for_existing_selection_corridor(candidate: Mapping[str, Any]) -> bool:
    source_tier = _token(candidate.get("source_tier"))
    source_class = _token(candidate.get("source_class"))
    currentness = _token(candidate.get("currentness_signal"))
    if source_tier in _LOWER_TIER_TIERS or source_class in _LOWER_TIER_CLASSES:
        return False
    if source_class in _MISSING_CLASSIFICATION_VALUES:
        return False
    return currentness not in _MISSING_CURRENTNESS_VALUES


def _selection_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    source_url = _text(
        candidate.get("source_url") or candidate.get("url") or candidate.get("accepted_url")
    )
    candidate_id = _text(candidate.get("candidate_id"))
    out = {
        "source_id": candidate_id,
        "candidate_id": candidate_id,
        "provider_result_id": _text(candidate.get("provider_result_id")),
        "title": _text(candidate.get("title")),
        "url": source_url,
        "source_url": source_url,
        "accepted_url": source_url,
        "source_tier": _token(candidate.get("source_tier")),
        "source_class": _token(candidate.get("source_class")),
        "currentness_signal": _text(candidate.get("currentness_signal")) or UNKNOWN,
        "retrieval_stage": "source_class_recovery",
        "provider_name": _text(candidate.get("provider_name")) or UNKNOWN,
        "provider_role": _text(candidate.get("provider_role"))
        or "source_class_recovery",
        "query_preview": _text(candidate.get("query_preview")) or UNKNOWN,
        "allocation_result_admitted": True,
        "selection_corridor_source": "allocation_result_candidate_custody",
        "raw_payload_exposed": False,
    }
    return {key: value for key, value in out.items() if value not in {"", None}}


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:240]


def _token(value: Any) -> str:
    return _text(value).casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION",
    "allocation_result_candidates_for_existing_selection_corridor",
]
