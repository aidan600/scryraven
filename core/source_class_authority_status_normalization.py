"""Normalize status-only strong authority source-class obligations.

This helper is pure control-input normalization. It does not retrieve, route
providers, choose depth, generate queries, rank/filter sources, call models, or
affect final answers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

SUPPORTED_STATUS_ONLY_STRONG_AUTHORITY_CLASSES = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
    "primary_source_documents",
    "archival_primary_text",
)

_SUPPORTED_STATUS_ONLY_STRONG_AUTHORITY_CLASS_SET = frozenset(
    SUPPORTED_STATUS_ONLY_STRONG_AUTHORITY_CLASSES
)
_NON_STRONG_STATUS_VALUES = frozenset(
    {
        "expected_but_only_secondary",
        "expected_only_secondary",
        "secondary_only",
        "satisfied_weak",
        "weakly_satisfied",
        "weak_satisfied",
        "unsatisfied",
        "not_satisfied",
        "missing",
    }
)
_STRONG_STATUS_VALUES = frozenset({"satisfied_strong", "strongly_satisfied"})


def status_only_strong_authority_missing_classes(
    recommendation: Mapping[str, Any] | None,
    *status_sources: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Return supported strong classes whose only control signal is status.

    Promotion is intentionally narrow: the recovery recommendation must already
    be active, executable recovery queries must already exist, the class must be
    one of the supported strong authority classes, status must show non-strong
    satisfaction, and no source reports strong satisfaction or a positive
    strong count.
    """

    base = recommendation if isinstance(recommendation, Mapping) else {}
    if not base.get("source_class_recovery_recommended"):
        return ()
    if not _has_recovery_queries(base):
        return ()

    sources = tuple(
        source for source in (base, *status_sources) if isinstance(source, Mapping)
    )
    promoted: list[str] = []
    for source_class in _candidate_status_classes(sources):
        statuses = _status_values_for_class(sources, source_class)
        if not statuses:
            continue
        if statuses & _STRONG_STATUS_VALUES:
            continue
        if not (statuses & _NON_STRONG_STATUS_VALUES):
            continue
        if _strong_count_positive(sources, source_class):
            continue
        promoted.append(source_class)
    return tuple(promoted)


def append_status_only_strong_authority_missing_classes(
    missing_expected_source_classes: Iterable[Any],
    recommendation: Mapping[str, Any] | None,
    *status_sources: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Append normalized status-only authority classes to an existing list."""

    out: list[str] = []
    seen: set[str] = set()
    for value in missing_expected_source_classes:
        text = _clean_text(value)
        key = text.casefold() if text else ""
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    for source_class in status_only_strong_authority_missing_classes(
        recommendation,
        *status_sources,
    ):
        if source_class.casefold() not in seen:
            out.append(source_class)
            seen.add(source_class.casefold())
    return tuple(out)


def _has_recovery_queries(source: Mapping[str, Any]) -> bool:
    return bool(_string_list(source.get("source_class_recovery_queries")))


def _candidate_status_classes(
    sources: Iterable[Mapping[str, Any]],
) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for source in sources:
        status = source.get("source_class_satisfaction_status")
        if not isinstance(status, Mapping):
            continue
        for key in status:
            token = _clean_token(key)
            if (
                token in _SUPPORTED_STATUS_ONLY_STRONG_AUTHORITY_CLASS_SET
                and token not in seen
            ):
                out.append(token)
                seen.add(token)
    return tuple(out)


def _status_values_for_class(
    sources: Iterable[Mapping[str, Any]],
    source_class: str,
) -> frozenset[str]:
    values: set[str] = set()
    for source in sources:
        status = source.get("source_class_satisfaction_status")
        if not isinstance(status, Mapping):
            continue
        for key, raw_value in status.items():
            if _clean_token(key) != source_class:
                continue
            token = _clean_token(raw_value)
            if token:
                values.add(token)
    return frozenset(values)


def _strong_count_positive(
    sources: Iterable[Mapping[str, Any]],
    source_class: str,
) -> bool:
    for source in sources:
        counts = source.get("source_class_strong_satisfaction_counts")
        if not isinstance(counts, Mapping):
            continue
        try:
            if int(counts.get(source_class, 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _string_list(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, (str, bytes, Mapping)):
        return ()
    out: list[str] = []
    try:
        values = tuple(value)
    except TypeError:
        return ()
    for item in values:
        text = _clean_text(item)
        if text:
            out.append(text)
    return tuple(out)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text or None


def _clean_token(value: Any) -> str:
    return (_clean_text(value) or "").casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "SUPPORTED_STATUS_ONLY_STRONG_AUTHORITY_CLASSES",
    "append_status_only_strong_authority_missing_classes",
    "status_only_strong_authority_missing_classes",
]
