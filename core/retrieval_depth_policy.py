"""Deterministic retrieval depth selection helpers."""

from __future__ import annotations


def has_explicit_retrieval_escalation(
    explicit_escalation_reason: str | None,
) -> bool:
    return bool(str(explicit_escalation_reason or "").strip())


def choose_retrieval_search_depth(
    complexity: str,
    base_search_depth: str | None,
    iteration: int,
    explicit_escalation_reason: str | None = None,
) -> str:
    """Choose main-loop retrieval depth without implicit medium second-pass escalation."""
    base_depth = str(base_search_depth or "basic").strip().lower() or "basic"
    if has_explicit_retrieval_escalation(explicit_escalation_reason):
        return "advanced"
    if str(complexity or "").strip().lower() == "high":
        return "advanced"
    return base_depth


def choose_supplemental_search_depth(
    complexity: str,
    base_search_depth: str | None,
    explicit_escalation_reason: str | None = None,
) -> str:
    """Choose synthesis-gap supplemental retrieval depth from the same base policy."""
    base_depth = str(base_search_depth or "basic").strip().lower() or "basic"
    if has_explicit_retrieval_escalation(explicit_escalation_reason):
        return "advanced"
    if str(complexity or "").strip().lower() == "high":
        return "advanced"
    return base_depth
