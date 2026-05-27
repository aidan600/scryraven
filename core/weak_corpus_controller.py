"""Minimal active controller decision for weak-corpus recovery.

The controller owns the post-first-pass decision for whether existing
weak-corpus recovery should run. It does not retrieve, route providers,
choose providers, alter prompts, rank sources, persist data, or call models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.run_controller import ControllerDecision, RetrievalAction, RunController

WEAK_CORPUS_RECOVERY_PROVIDER_ROLE = "weak_corpus_recovery"

_WEAK_CORPUS_SKIP_REASON_PRIORITY = (
    "not_first_iteration",
    "max_iterations_1",
    "already_attempted",
    "no_readable_passages",
    "no_recovery_queries",
)


class WeakCorpusRecoveryControllerDecision(str, Enum):
    """Stable weak-corpus recovery decision values."""

    NO_ACTION = "no_action"
    BLOCKED_WITH_REASON = "blocked_with_reason"
    RUN_WEAK_CORPUS_RECOVERY = "run_weak_corpus_recovery"


@dataclass(frozen=True)
class WeakCorpusRecoveryControllerInput:
    """Compact retrieval snapshot for the weak-corpus recovery decision."""

    corpus_state: str | None
    corpus_weak: bool
    iteration: int
    max_iterations: int
    prior_attempted: bool = False
    readable_passage_count: int = 0
    recovery_queries: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_state": self.corpus_state,
            "corpus_weak": self.corpus_weak,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "prior_attempted": self.prior_attempted,
            "readable_passage_count": self.readable_passage_count,
            "recovery_queries": list(self.recovery_queries),
        }


@dataclass(frozen=True)
class WeakCorpusRecoveryDecision:
    """Controller-owned decision and approved recovery parameters."""

    decision: WeakCorpusRecoveryControllerDecision
    reason: str
    blockers: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        return self.decision is (
            WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY
        )

    @property
    def considered(self) -> bool:
        return self.reason != "not_weak_corpus"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "queries": list(self.queries),
        }


def _copy_string_list(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def build_weak_corpus_recovery_controller_input(
    *,
    corpus_state: str | None,
    corpus_weak: bool,
    iteration: int,
    max_iterations: int,
    prior_attempted: bool,
    readable_passage_count: int,
    recovery_queries: list[str] | tuple[str, ...],
) -> WeakCorpusRecoveryControllerInput:
    """Build the compact controller input from existing retrieval facts."""
    return WeakCorpusRecoveryControllerInput(
        corpus_state=corpus_state,
        corpus_weak=bool(corpus_weak),
        iteration=max(0, int(iteration or 0)),
        max_iterations=max(0, int(max_iterations or 0)),
        prior_attempted=bool(prior_attempted),
        readable_passage_count=max(0, int(readable_passage_count or 0)),
        recovery_queries=_copy_string_list(recovery_queries),
    )


def _first_skip_reason(blockers: tuple[str, ...]) -> str:
    for reason in _WEAK_CORPUS_SKIP_REASON_PRIORITY:
        if reason in blockers:
            return reason
    return blockers[0] if blockers else "weak_corpus_recovery_not_used"


def decide_weak_corpus_recovery(
    snapshot: WeakCorpusRecoveryControllerInput,
) -> WeakCorpusRecoveryDecision:
    """Return no_action, blocked_with_reason, or run_weak_corpus_recovery."""
    if not snapshot.corpus_weak:
        return WeakCorpusRecoveryDecision(
            decision=WeakCorpusRecoveryControllerDecision.NO_ACTION,
            reason="not_weak_corpus",
        )

    blockers: list[str] = []
    if snapshot.iteration != 1:
        blockers.append("not_first_iteration")
    if snapshot.max_iterations <= 1:
        blockers.append("max_iterations_1")
    if snapshot.prior_attempted:
        blockers.append("already_attempted")
    if snapshot.readable_passage_count <= 0:
        blockers.append("no_readable_passages")
    if not snapshot.recovery_queries:
        blockers.append("no_recovery_queries")

    blocker_tuple = tuple(blockers)
    if blocker_tuple:
        return WeakCorpusRecoveryDecision(
            decision=WeakCorpusRecoveryControllerDecision.BLOCKED_WITH_REASON,
            reason=_first_skip_reason(blocker_tuple),
            blockers=blocker_tuple,
            queries=snapshot.recovery_queries,
        )

    return WeakCorpusRecoveryDecision(
        decision=WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY,
        reason="weak_corpus_first_pass",
        queries=snapshot.recovery_queries,
    )


def weak_corpus_recovery_trace_fields(
    decision: WeakCorpusRecoveryDecision,
) -> dict[str, Any]:
    """Return stable trace fields for the compact weak-corpus decision."""
    return {
        "weak_corpus_recovery_decision": decision.decision.value,
        "weak_corpus_recovery_reason": decision.reason,
        "weak_corpus_recovery_blockers": list(decision.blockers),
    }


def record_weak_corpus_recovery_decision(
    controller: RunController,
    *,
    snapshot: WeakCorpusRecoveryControllerInput,
    decision: WeakCorpusRecoveryDecision,
    action_promoted: bool | None = None,
) -> dict[str, Any]:
    """Record the weak-corpus recovery controller decision without executing it."""
    trace_fields = weak_corpus_recovery_trace_fields(decision)
    promoted = decision.approved if action_promoted is None else bool(action_promoted)
    promotion_source = (
        "controller_approved_pending_orchestrator"
        if action_promoted is None
        else "checkpoint_promoted_pending_orchestrator"
    )
    signals = {
        "corpus_state": snapshot.corpus_state,
        "corpus_weak": snapshot.corpus_weak,
        "iteration": snapshot.iteration,
        "max_iterations": snapshot.max_iterations,
        "readable_passage_count": snapshot.readable_passage_count,
        "weak_corpus_recovery_decision": decision.decision.value,
        "weak_corpus_recovery_reason": decision.reason,
        "weak_corpus_recovery_blockers": list(decision.blockers),
    }

    action: RetrievalAction | None = None
    if decision.approved and promoted:
        action = RetrievalAction(
            name="weak_corpus_recovery",
            queries=list(decision.queries),
            provider=None,
            provider_role=WEAK_CORPUS_RECOVERY_PROVIDER_ROLE,
            search_depth=None,
            results_per_query=None,
            active=True,
            shadow=False,
            reason=decision.reason,
            signals=signals,
            trace_fields={},
            metadata={
                "execution": promotion_source,
                "controller_decision": decision.decision.value,
            },
        )
        controller.state.record_recovery_action(action)
        controller.record_retrieval_action(action)

    controller.record_decision(
        ControllerDecision(
            name=decision.decision.value,
            active=True,
            shadow=False,
            reason=decision.reason,
            signals=signals,
            recommended_actions=[action] if action is not None else [],
            trace_fields={},
            metadata={
                "execution": "minimal_active_controller",
                "decision": decision.decision.value,
                "checkpoint_promoted": bool(promoted),
                "decision_contract": [
                    item.value for item in WeakCorpusRecoveryControllerDecision
                ],
            },
        )
    )
    controller.ledger.record_fact(
        stage="weak_corpus_recovery",
        name="decision",
        value=decision.decision.value,
        metadata={
            "reason": decision.reason,
            "blockers": list(decision.blockers),
        },
    )
    controller.ledger.record_fact(
        stage="weak_corpus_recovery",
        name="skip_reason",
        value=None if decision.approved else decision.reason,
        metadata={"decision": decision.decision.value},
    )
    return trace_fields


__all__ = [
    "WEAK_CORPUS_RECOVERY_PROVIDER_ROLE",
    "WeakCorpusRecoveryControllerDecision",
    "WeakCorpusRecoveryControllerInput",
    "WeakCorpusRecoveryDecision",
    "build_weak_corpus_recovery_controller_input",
    "decide_weak_corpus_recovery",
    "record_weak_corpus_recovery_decision",
    "weak_corpus_recovery_trace_fields",
]
