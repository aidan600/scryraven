"""Small helpers for canonical RunAuthority projection references."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

RUN_AUTHORITY_SEARCH_JUDGMENT_OWNER = "RunKernel.RunAuthoritySearchJudgment"
RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER = (
    "RunKernel.RunAuthoritySufficiencyJudgment"
)


def _projection(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def canonical_projection_ref(value: Any, *, owner: str) -> dict[str, Any]:
    """Return a projection only when it is the canonical RunKernel owner."""

    projection = _projection(value)
    if projection.get("owner") != owner:
        return {}
    if projection.get("canonical_state") is not True:
        return {}
    if projection.get("trace_only") is not False:
        return {}
    return projection


def is_canonical_search_judgment_projection(value: Any) -> bool:
    return bool(canonical_search_judgment_projection(value))


def canonical_search_judgment_projection(value: Any) -> dict[str, Any]:
    return canonical_projection_ref(
        value,
        owner=RUN_AUTHORITY_SEARCH_JUDGMENT_OWNER,
    )


def compact_search_judgment_ref(value: Any) -> dict[str, Any]:
    projection = canonical_search_judgment_projection(value)
    if not projection:
        return {}
    return {
        "owner": projection.get("owner"),
        "judgment_id": projection.get("judgment_id"),
        "decision": projection.get("decision"),
        "classifications": projection.get("classifications", []),
        "target_source_classes": projection.get("target_source_classes", []),
        "validation_status": projection.get("validation_status"),
        "canonical_state": projection.get("canonical_state"),
        "trace_only": projection.get("trace_only"),
    }


def is_canonical_sufficiency_judgment_projection(value: Any) -> bool:
    return bool(canonical_sufficiency_judgment_projection(value))


def canonical_sufficiency_judgment_projection(value: Any) -> dict[str, Any]:
    return canonical_projection_ref(
        value,
        owner=RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER,
    )


def compact_sufficiency_judgment_ref(value: Any) -> dict[str, Any]:
    projection = canonical_sufficiency_judgment_projection(value)
    if not projection:
        return {}
    return {
        "owner": projection.get("owner"),
        "judgment_id": projection.get("judgment_id"),
        "decision": projection.get("decision"),
        "final_answer_posture": projection.get("final_answer_posture"),
        "final_answer_allowed": projection.get("final_answer_allowed"),
        "canonical_state": projection.get("canonical_state"),
        "trace_only": projection.get("trace_only"),
    }


__all__ = [
    "RUN_AUTHORITY_SEARCH_JUDGMENT_OWNER",
    "RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER",
    "canonical_projection_ref",
    "canonical_search_judgment_projection",
    "canonical_sufficiency_judgment_projection",
    "compact_search_judgment_ref",
    "compact_sufficiency_judgment_ref",
    "is_canonical_search_judgment_projection",
    "is_canonical_sufficiency_judgment_projection",
]
