"""Pure retrieval stop/continue decision boundary.

This module mirrors the existing main-loop retrieval stop semantics without
executing retrieval, choosing providers, altering prompts, ranking sources, or
owning recovery behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

REDUNDANT_QUERY_JACCARD_THRESHOLD = 0.7


class RetrievalStopControllerDecision(str, Enum):
    """Stable retrieval stop/continue decision values."""

    PROCEED_TO_SYNTHESIS = "proceed_to_synthesis"
    CONTINUE_RETRIEVAL = "continue_retrieval"
    STOP_NO_QUERIES = "stop_no_queries"
    STOP_BUDGET_EXHAUSTED = "stop_budget_exhausted"
    STOP_REDUNDANT_QUERIES = "stop_redundant_queries"
    STOP_AFTER_RECOVERY = "stop_after_recovery"
    BLOCKED_WITH_REASON = "blocked_with_reason"


@dataclass(frozen=True)
class RetrievalStopControllerInput:
    """Compact retrieval-loop snapshot for the stop/continue decision."""

    evaluator_sufficient: bool | None
    iteration: int
    max_iterations: int
    prior_queries: tuple[str, ...] = ()
    next_queries: tuple[str, ...] = ()
    query_source: str | None = None
    weak_corpus_recovery_used: bool = False
    weak_corpus_recovery_completed: bool = False
    blockers: tuple[str, ...] = ()
    redundancy_threshold: float = REDUNDANT_QUERY_JACCARD_THRESHOLD

    @property
    def iteration_budget_available(self) -> bool:
        return self.iteration < self.max_iterations

    @property
    def recovery_completed_for_stop(self) -> bool:
        return self.weak_corpus_recovery_completed or (
            self.weak_corpus_recovery_used and self.iteration > 1
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator_sufficient": self.evaluator_sufficient,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "prior_queries": list(self.prior_queries),
            "next_queries": list(self.next_queries),
            "query_source": self.query_source,
            "weak_corpus_recovery_used": self.weak_corpus_recovery_used,
            "weak_corpus_recovery_completed": self.weak_corpus_recovery_completed,
            "blockers": list(self.blockers),
            "redundancy_threshold": self.redundancy_threshold,
        }


@dataclass(frozen=True)
class RetrievalStopDecision:
    """Controller-owned retrieval stop/continue decision."""

    decision: RetrievalStopControllerDecision
    reason: str
    blockers: tuple[str, ...] = ()
    next_queries: tuple[str, ...] = ()
    query_source: str | None = None
    redundancy_score: float | None = None

    @property
    def should_continue(self) -> bool:
        return self.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL

    @property
    def should_stop(self) -> bool:
        return self.decision in {
            RetrievalStopControllerDecision.STOP_NO_QUERIES,
            RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED,
            RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES,
            RetrievalStopControllerDecision.STOP_AFTER_RECOVERY,
            RetrievalStopControllerDecision.BLOCKED_WITH_REASON,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "next_queries": list(self.next_queries),
            "query_source": self.query_source,
            "redundancy_score": self.redundancy_score,
        }


def _clean_query(query: str) -> str:
    text = " ".join((query or "").strip().split())
    if not text:
        return ""
    words = text.split(" ")
    last = words[-1]
    if len(last) < 3 and last.isalpha() and "." not in last:
        words = words[:-1]
    return " ".join(words)[:300]


def _copy_string_list(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        text = _clean_query(str(item or ""))
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _query_jaccard_similarity(
    queries_a: tuple[str, ...],
    queries_b: tuple[str, ...],
) -> float:
    tokens_a = set(" ".join(queries_a).lower().split())
    tokens_b = set(" ".join(queries_b).lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def build_retrieval_stop_controller_input(
    *,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    blockers: list[str] | tuple[str, ...] = (),
    redundancy_threshold: float = REDUNDANT_QUERY_JACCARD_THRESHOLD,
) -> RetrievalStopControllerInput:
    """Build the compact controller input from already-computed loop facts."""
    return RetrievalStopControllerInput(
        evaluator_sufficient=(
            None if evaluator_sufficient is None else bool(evaluator_sufficient)
        ),
        iteration=max(0, int(iteration or 0)),
        max_iterations=max(0, int(max_iterations or 0)),
        prior_queries=_copy_string_list(prior_queries),
        next_queries=_copy_string_list(next_queries),
        query_source=(
            None if query_source is None else str(query_source).strip() or None
        ),
        weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
        weak_corpus_recovery_completed=bool(weak_corpus_recovery_completed),
        blockers=_copy_string_list(blockers),
        redundancy_threshold=float(redundancy_threshold),
    )


def decide_retrieval_stop(
    snapshot: RetrievalStopControllerInput,
) -> RetrievalStopDecision:
    """Return the passive retrieval stop/continue decision for a compact snapshot."""
    if snapshot.blockers:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.BLOCKED_WITH_REASON,
            reason=snapshot.blockers[0],
            blockers=snapshot.blockers,
            next_queries=snapshot.next_queries,
            query_source=snapshot.query_source,
        )

    if snapshot.evaluator_sufficient is True:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS,
            reason="evaluator_sufficient",
        )

    if snapshot.recovery_completed_for_stop:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.STOP_AFTER_RECOVERY,
            reason="weak_corpus_recovery_completed",
            blockers=("weak_corpus_recovery_completed",),
        )

    if (
        snapshot.query_source == "budget"
        and not snapshot.iteration_budget_available
    ):
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED,
            reason="iteration_budget_exhausted",
            blockers=("iteration_budget_exhausted",),
            next_queries=snapshot.next_queries,
            query_source=snapshot.query_source,
        )

    if not snapshot.next_queries:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.STOP_NO_QUERIES,
            reason="no_new_queries",
            blockers=("no_new_queries",),
            query_source=snapshot.query_source,
        )

    redundancy_score = _query_jaccard_similarity(
        snapshot.prior_queries,
        snapshot.next_queries,
    )
    if redundancy_score > snapshot.redundancy_threshold:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES,
            reason="redundant_with_prior_queries",
            blockers=("redundant_queries",),
            next_queries=snapshot.next_queries,
            query_source=snapshot.query_source,
            redundancy_score=redundancy_score,
        )

    if not snapshot.iteration_budget_available:
        return RetrievalStopDecision(
            decision=RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED,
            reason="iteration_budget_exhausted",
            blockers=("iteration_budget_exhausted",),
            next_queries=snapshot.next_queries,
            query_source=snapshot.query_source,
            redundancy_score=redundancy_score,
        )

    return RetrievalStopDecision(
        decision=RetrievalStopControllerDecision.CONTINUE_RETRIEVAL,
        reason="candidate_queries_available",
        next_queries=snapshot.next_queries,
        query_source=snapshot.query_source,
        redundancy_score=redundancy_score,
    )


__all__ = [
    "REDUNDANT_QUERY_JACCARD_THRESHOLD",
    "RetrievalStopControllerDecision",
    "RetrievalStopControllerInput",
    "RetrievalStopDecision",
    "build_retrieval_stop_controller_input",
    "decide_retrieval_stop",
]
