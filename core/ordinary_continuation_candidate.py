"""Pure ordinary-continuation candidate normalization.

This module owns the AG-44B passive seam between legacy ordinary continuation
paths and the controller spine. It consumes already-computed continuation facts
and returns JSON-safe facts only. It does not execute retrieval, choose
providers, choose search depth, generate prompts, persist data, or mutate
runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

ORDINARY_CONTINUATION_TRACE_KEY = "ordinary_continuation_candidate"

EVALUATOR_NEXT_QUERIES = "evaluator_next_queries"
EXPANDER_COMPONENT_QUERIES = "expander_component_queries"
SCOUT_DIRECTED_QUERIES = "scout_directed_queries"
RETRIEVAL_STOP_CONTINUE = "retrieval_stop_continue"

ORDINARY_CONTINUATION_SOURCE_PATHS = frozenset(
    {
        EVALUATOR_NEXT_QUERIES,
        EXPANDER_COMPONENT_QUERIES,
        SCOUT_DIRECTED_QUERIES,
        RETRIEVAL_STOP_CONTINUE,
    }
)

_SOURCE_ALIASES = {
    "evaluator": EVALUATOR_NEXT_QUERIES,
    "evaluator_new_queries": EVALUATOR_NEXT_QUERIES,
    "expander": EXPANDER_COMPONENT_QUERIES,
    "scout": SCOUT_DIRECTED_QUERIES,
    "retrieval_stop": RETRIEVAL_STOP_CONTINUE,
    "pre_search": RETRIEVAL_STOP_CONTINUE,
}


@dataclass(frozen=True)
class OrdinaryContinuationCandidate:
    """JSON-safe ordinary continuation facts for passive spine consumption."""

    considered: bool
    eligible: bool
    reason: str
    blockers: tuple[str, ...]
    ordinary_next_queries: tuple[str, ...]
    query_provenance: str | None
    prior_queries: tuple[str, ...]
    prior_query_count: int
    conflict_resolving_queries: tuple[str, ...]
    source_path: str | None
    current_iteration: int
    max_iterations: int
    can_be_future_retrieve_targeted_candidate: bool = True
    currently_spine_authorized: bool = False
    used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "considered": bool(self.considered),
            "eligible": bool(self.eligible),
            "reason": self.reason,
            "blockers": list(self.blockers),
            "ordinary_next_queries": list(self.ordinary_next_queries),
            "query_provenance": self.query_provenance,
            "prior_queries": list(self.prior_queries),
            "prior_query_count": max(0, int(self.prior_query_count or 0)),
            "conflict_resolving_queries": list(self.conflict_resolving_queries),
            "source_path": self.source_path,
            "current_iteration": max(0, int(self.current_iteration or 0)),
            "max_iterations": max(0, int(self.max_iterations or 0)),
            "can_be_future_retrieve_targeted_candidate": bool(
                self.can_be_future_retrieve_targeted_candidate
            ),
            "currently_spine_authorized": bool(self.currently_spine_authorized),
            "used": bool(self.used),
        }

    def to_trace_fields(self) -> dict[str, Any]:
        return {ORDINARY_CONTINUATION_TRACE_KEY: self.to_dict()}


def ordinary_continuation_candidate_defaults() -> dict[str, Any]:
    """Return a passive not-evaluated candidate payload."""
    return OrdinaryContinuationCandidate(
        considered=False,
        eligible=False,
        reason="not_evaluated",
        blockers=("not_evaluated",),
        ordinary_next_queries=(),
        query_provenance=None,
        prior_queries=(),
        prior_query_count=0,
        conflict_resolving_queries=(),
        source_path=None,
        current_iteration=0,
        max_iterations=0,
    ).to_dict()


def build_ordinary_continuation_candidate(
    *,
    source_path: str | None,
    ordinary_next_queries: list[str] | tuple[str, ...] = (),
    query_provenance: str | None = None,
    prior_queries: list[str] | tuple[str, ...] = (),
    prior_query_count: int | None = None,
    conflict_resolving_queries: list[str] | tuple[str, ...] = (),
    current_iteration: int = 0,
    max_iterations: int = 0,
    next_queries_redundant: bool = False,
    budget_exhausted: bool = False,
    considered: bool | None = None,
    extra_blockers: list[str] | tuple[str, ...] = (),
) -> OrdinaryContinuationCandidate:
    """Normalize old ordinary continuation facts into one passive candidate."""
    normalized_source = _normalize_source_path(source_path or query_provenance)
    ordinary_queries = _copy_string_tuple(ordinary_next_queries)
    prior = _copy_string_tuple(prior_queries)
    conflicts = _copy_string_tuple(conflict_resolving_queries)
    iteration = max(0, int(current_iteration or 0))
    max_iter = max(0, int(max_iterations or 0))
    exhausted = bool(budget_exhausted or (max_iter and iteration >= max_iter))
    blockers = list(_copy_string_tuple(extra_blockers))

    if not ordinary_queries:
        blockers.append("no_ordinary_next_queries")
    if next_queries_redundant:
        blockers.append("redundant_with_prior_queries")
    if exhausted:
        blockers.append("blocked_by_iteration_budget")
    if normalized_source not in ORDINARY_CONTINUATION_SOURCE_PATHS:
        blockers.append("source_path_not_ordinary_continuation")

    blockers_tuple = _dedupe_strings(blockers)
    eligible = not blockers_tuple
    reason = (
        "ordinary_continuation_candidate_available"
        if eligible
        else blockers_tuple[0]
        if blockers_tuple
        else "not_evaluated"
    )
    was_considered = (
        bool(ordinary_queries or normalized_source or conflicts)
        if considered is None
        else bool(considered)
    )
    count = len(prior) if prior_query_count is None else max(0, int(prior_query_count))

    return OrdinaryContinuationCandidate(
        considered=was_considered,
        eligible=eligible,
        reason=reason,
        blockers=blockers_tuple,
        ordinary_next_queries=ordinary_queries,
        query_provenance=normalized_source,
        prior_queries=prior,
        prior_query_count=count,
        conflict_resolving_queries=conflicts,
        source_path=normalized_source,
        current_iteration=iteration,
        max_iterations=max_iter,
        can_be_future_retrieve_targeted_candidate=eligible,
        currently_spine_authorized=False,
        used=False,
    )


def ordinary_continuation_candidate_from_mapping(
    value: Mapping[str, Any] | None,
) -> OrdinaryContinuationCandidate:
    """Rehydrate sanitized mapping facts without trusting caller types."""
    payload = dict(value or {})
    return build_ordinary_continuation_candidate(
        source_path=_string_or_none(payload.get("source_path")),
        ordinary_next_queries=_list_or_tuple(payload.get("ordinary_next_queries")),
        query_provenance=_string_or_none(payload.get("query_provenance")),
        prior_queries=_list_or_tuple(payload.get("prior_queries")),
        prior_query_count=_int_or_none(payload.get("prior_query_count")),
        conflict_resolving_queries=_list_or_tuple(
            payload.get("conflict_resolving_queries")
        ),
        current_iteration=max(0, int(payload.get("current_iteration") or 0)),
        max_iterations=max(0, int(payload.get("max_iterations") or 0)),
        next_queries_redundant=(
            "redundant_with_prior_queries" in set(payload.get("blockers") or [])
        ),
        budget_exhausted=(
            "blocked_by_iteration_budget" in set(payload.get("blockers") or [])
        ),
        considered=bool(payload.get("considered")),
        extra_blockers=[
            str(blocker)
            for blocker in (payload.get("blockers") or [])
            if str(blocker)
            not in {
                "no_ordinary_next_queries",
                "redundant_with_prior_queries",
                "blocked_by_iteration_budget",
                "source_path_not_ordinary_continuation",
            }
        ],
    )


def is_bounded_evaluator_continuation_candidate(
    value: Mapping[str, Any] | None,
) -> bool:
    """Return whether a candidate is the AG-44C evaluator gate surface."""
    return _is_bounded_continuation_candidate_for_source(
        value,
        EVALUATOR_NEXT_QUERIES,
    )


def is_bounded_expander_continuation_candidate(
    value: Mapping[str, Any] | None,
) -> bool:
    """Return whether a candidate is the AG-45A expander gate surface."""
    return _is_bounded_continuation_candidate_for_source(
        value,
        EXPANDER_COMPONENT_QUERIES,
    )


def is_bounded_scout_continuation_candidate(
    value: Mapping[str, Any] | None,
) -> bool:
    """Return whether a candidate is the AG-45C scout gate surface."""
    return _is_bounded_continuation_candidate_for_source(
        value,
        SCOUT_DIRECTED_QUERIES,
    )


def is_bounded_spine_authorized_continuation_candidate(
    value: Mapping[str, Any] | None,
) -> bool:
    """Return whether a candidate is an actively promoted ordinary lane."""
    return bool(
        is_bounded_evaluator_continuation_candidate(value)
        or is_bounded_expander_continuation_candidate(value)
        or is_bounded_scout_continuation_candidate(value)
    )


def bounded_continuation_authorization_reason(
    value: Mapping[str, Any] | None,
) -> str | None:
    """Return the spine gate reason for an authorized bounded ordinary lane."""
    if is_bounded_evaluator_continuation_candidate(value):
        return "bounded_evaluator_continuation_authorized"
    if is_bounded_expander_continuation_candidate(value):
        return "bounded_expander_continuation_authorized"
    if is_bounded_scout_continuation_candidate(value):
        return "bounded_scout_continuation_authorized"
    return None


def _is_bounded_continuation_candidate_for_source(
    value: Mapping[str, Any] | None,
    expected_source_path: str,
) -> bool:
    payload = dict(value or {})
    source_path = _normalize_source_path(
        _string_or_none(payload.get("source_path"))
        or _string_or_none(payload.get("query_provenance"))
    )
    return bool(
        payload.get("eligible")
        and source_path == expected_source_path
        and _copy_string_tuple(payload.get("ordinary_next_queries"))
        and not _copy_string_tuple(payload.get("conflict_resolving_queries"))
        and payload.get("can_be_future_retrieve_targeted_candidate", True)
    )


def mark_ordinary_continuation_candidate_spine_authorized(
    value: Mapping[str, Any] | None,
    *,
    used: bool,
) -> dict[str, Any]:
    """Mark only bounded actively promoted ordinary candidates as authorized."""
    payload = ordinary_continuation_candidate_from_mapping(value).to_dict()
    if is_bounded_spine_authorized_continuation_candidate(payload):
        payload["currently_spine_authorized"] = True
        payload["used"] = bool(used)
    return payload


def source_path_from_runtime_source(source: str | None) -> str | None:
    """Return the ordinary-continuation source path for a legacy source token."""
    return _normalize_source_path(source)


def _normalize_source_path(value: str | None) -> str | None:
    text = _clean_token(value)
    if text in ORDINARY_CONTINUATION_SOURCE_PATHS:
        return text
    return _SOURCE_ALIASES.get(text or "")


def _copy_string_tuple(value: Any) -> tuple[str, ...]:
    return _dedupe_strings(_list_or_tuple(value))


def _dedupe_strings(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _list_or_tuple(value):
        text = " ".join(str(item or "").strip().split())[:300]
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _list_or_tuple(value: Any) -> list[Any] | tuple[Any, ...]:
    return value if isinstance(value, (list, tuple)) else ()


def _clean_token(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())[:80]
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())[:300]
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


__all__ = [
    "EVALUATOR_NEXT_QUERIES",
    "EXPANDER_COMPONENT_QUERIES",
    "ORDINARY_CONTINUATION_SOURCE_PATHS",
    "ORDINARY_CONTINUATION_TRACE_KEY",
    "RETRIEVAL_STOP_CONTINUE",
    "SCOUT_DIRECTED_QUERIES",
    "OrdinaryContinuationCandidate",
    "build_ordinary_continuation_candidate",
    "bounded_continuation_authorization_reason",
    "is_bounded_expander_continuation_candidate",
    "is_bounded_evaluator_continuation_candidate",
    "is_bounded_spine_authorized_continuation_candidate",
    "mark_ordinary_continuation_candidate_spine_authorized",
    "ordinary_continuation_candidate_defaults",
    "ordinary_continuation_candidate_from_mapping",
    "source_path_from_runtime_source",
]
