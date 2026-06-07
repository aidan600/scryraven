"""Deterministic retrieval-stop and continuation trace projections."""

from __future__ import annotations

import logging
from typing import Any, Callable

from core.controller_action_envelope import STOP_INSUFFICIENT_WITH_CAVEAT, ControllerActionAuthority
from core.ordinary_continuation_candidate import build_ordinary_continuation_candidate, source_path_from_runtime_source
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)

logger = logging.getLogger(__name__)

_RETRIEVAL_STOP_SHADOW_MODE = "shadow_only"
_RETRIEVAL_STOP_ACTIVE_MODE = "active_stop_no_queries"
_RETRIEVAL_STOP_ACTIVE_BUDGET_EXHAUSTED_MODE = "active_stop_budget_exhausted"
_RETRIEVAL_STOP_ACTIVE_FINAL_ANSWER_POSTURE = "answer with caveats"
_RETRIEVAL_STOP_ACTIVE_AG28_CANDIDATE = "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"


def retrieval_stop_shadow_defaults() -> dict[str, Any]:
    return {
        "retrieval_stop_shadow_available": False,
        "retrieval_stop_shadow_decision": None,
        "retrieval_stop_shadow_reason": None,
        "retrieval_stop_shadow_blockers": [],
        "retrieval_stop_shadow_next_query_count": 0,
        "retrieval_stop_shadow_alignment": None,
        "retrieval_stop_shadow_stage": None,
        "retrieval_stop_shadow_mode": _RETRIEVAL_STOP_SHADOW_MODE,
    }

def retrieval_stop_active_defaults() -> dict[str, Any]:
    return {
        "retrieval_stop_active_available": False,
        "retrieval_stop_active_action_name": None,
        "retrieval_stop_active_authority": None,
        "retrieval_stop_active_decision": None,
        "retrieval_stop_active_reason": None,
        "retrieval_stop_active_terminal_branch_reason": None,
        "retrieval_stop_active_blockers": [],
        "retrieval_stop_active_next_query_count": 0,
        "retrieval_stop_active_approved_query_count": 0,
        "retrieval_stop_active_stage": None,
        "retrieval_stop_active_mode": _RETRIEVAL_STOP_ACTIVE_MODE,
        "retrieval_stop_active_final_answer_posture": None,
        "retrieval_stop_active_ag28_candidate": None,
        "retrieval_stop_active_shadow_alignment": None,
        "retrieval_stop_active_fallback_reason": None,
    }

def compact_shadow_strings(
    values: list[str] | tuple[str, ...], *, max_items: int = 4, max_len: int = 80
) -> list[str]:
    return [
        text
        for value in values[:max_items]
        if (text := " ".join(str(value or "").split())[:max_len])
    ]

def build_retrieval_stop_shadow_telemetry(
    *,
    actual_decision: str,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    blockers: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    telemetry = retrieval_stop_shadow_defaults()
    telemetry["retrieval_stop_shadow_stage"] = str(stage or "")[:80] or None
    try:
        decision = decide_retrieval_stop(
            build_retrieval_stop_controller_input(
                evaluator_sufficient=evaluator_sufficient,
                iteration=iteration,
                max_iterations=max_iterations,
                prior_queries=prior_queries,
                next_queries=next_queries,
                query_source=query_source,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_completed=weak_corpus_recovery_completed,
                blockers=blockers,
            )
        )
        decision_value = decision.decision.value
        telemetry.update(
            retrieval_stop_shadow_available=True,
            retrieval_stop_shadow_decision=decision_value,
            retrieval_stop_shadow_reason=decision.reason,
            retrieval_stop_shadow_blockers=compact_shadow_strings(decision.blockers),
            retrieval_stop_shadow_next_query_count=len(decision.next_queries),
            retrieval_stop_shadow_alignment=(
                "aligned" if decision_value == actual_decision else "mismatch"
            ),
        )
    except Exception:
        logger.warning("Non-fatal retrieval-stop shadow telemetry omitted.")
        telemetry.update(
            retrieval_stop_shadow_reason="shadow_unavailable",
            retrieval_stop_shadow_blockers=["shadow_exception"],
            retrieval_stop_shadow_alignment="unavailable",
        )
    return telemetry

def _active_decision_value(decision: Any) -> str | None:
    value = getattr(getattr(decision, "decision", None), "value", None)
    value = getattr(decision, "decision", None) if value is None else value
    if not isinstance(value, str):
        return None
    return (" ".join(value.split())[:80]) or None

def _active_decision_reason(decision: Any) -> str | None:
    value = getattr(decision, "reason", None)
    if not isinstance(value, str):
        return None
    return (" ".join(value.split())[:80]) or None

def _active_decision_next_query_count(decision: Any) -> int:
    value = getattr(decision, "next_queries", ())
    return len(value) if isinstance(value, (list, tuple)) else 0

def build_retrieval_stop_alignment_projection(
    *, active_decision: str | None, shadow_telemetry: dict[str, Any]
) -> str:
    if not active_decision:
        return "not_evaluated"
    if shadow_telemetry.get("retrieval_stop_shadow_available") is not True:
        return "shadow_unavailable"
    return (
        "aligned"
        if shadow_telemetry.get("retrieval_stop_shadow_decision") == active_decision
        else "mismatch"
    )

def _build_retrieval_stop_active_telemetry(
    *,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    expected_decision: str,
    active_mode: str,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    shadow_telemetry: dict[str, Any] | None = None,
    decide_retrieval_stop_for_active: Callable[[Any], Any] = decide_retrieval_stop,
) -> dict[str, Any]:
    telemetry = retrieval_stop_active_defaults()
    telemetry["retrieval_stop_active_stage"] = str(stage or "")[:80] or None
    telemetry["retrieval_stop_active_mode"] = str(active_mode or "")[:80] or None
    shadow = shadow_telemetry if isinstance(shadow_telemetry, dict) else {}
    try:
        decision = decide_retrieval_stop_for_active(
            build_retrieval_stop_controller_input(
                evaluator_sufficient=evaluator_sufficient,
                iteration=iteration,
                max_iterations=max_iterations,
                prior_queries=prior_queries,
                next_queries=next_queries,
                query_source=query_source,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_completed=weak_corpus_recovery_completed,
            )
        )
        decision_value = _active_decision_value(decision)
        telemetry.update(
            retrieval_stop_active_decision=decision_value,
            retrieval_stop_active_reason=_active_decision_reason(decision),
            retrieval_stop_active_blockers=compact_shadow_strings(
                getattr(decision, "blockers", ())
            ),
            retrieval_stop_active_next_query_count=_active_decision_next_query_count(
                decision
            ),
            retrieval_stop_active_shadow_alignment=build_retrieval_stop_alignment_projection(
                active_decision=decision_value, shadow_telemetry=shadow
            ),
        )
        if decision_value == expected_decision:
            telemetry.update(
                retrieval_stop_active_available=True,
                retrieval_stop_active_action_name=STOP_INSUFFICIENT_WITH_CAVEAT,
                retrieval_stop_active_authority=ControllerActionAuthority.ACTIVE.value,
                retrieval_stop_active_terminal_branch_reason=_active_decision_reason(
                    decision
                ),
                retrieval_stop_active_final_answer_posture=_RETRIEVAL_STOP_ACTIVE_FINAL_ANSWER_POSTURE,
                retrieval_stop_active_approved_query_count=0,
                retrieval_stop_active_ag28_candidate=_RETRIEVAL_STOP_ACTIVE_AG28_CANDIDATE,
            )
        else:
            telemetry["retrieval_stop_active_fallback_reason"] = "unexpected_controller_decision"
    except Exception:
        logger.warning("Non-fatal active retrieval-stop handoff fell back.")
        telemetry.update(
            retrieval_stop_active_reason="active_controller_unavailable",
            retrieval_stop_active_blockers=["active_controller_exception"],
            retrieval_stop_active_shadow_alignment="not_evaluated",
            retrieval_stop_active_fallback_reason="controller_exception",
        )
    return telemetry

def build_retrieval_stop_active_stop_no_queries_telemetry(
    **kwargs: Any,
) -> dict[str, Any]:
    return _build_retrieval_stop_active_telemetry(
        **kwargs,
        expected_decision="stop_no_queries",
        active_mode=_RETRIEVAL_STOP_ACTIVE_MODE,
    )

def build_retrieval_stop_active_stop_budget_exhausted_telemetry(
    **kwargs: Any,
) -> dict[str, Any]:
    return _build_retrieval_stop_active_telemetry(
        **kwargs,
        expected_decision="stop_budget_exhausted",
        active_mode=_RETRIEVAL_STOP_ACTIVE_BUDGET_EXHAUSTED_MODE,
    )

def build_ordinary_continuation_trace_projection(
    *,
    existing_candidate_trace: dict[str, Any],
    evidence_state: Any,
    compact_runtime_strings_fn: Callable[..., list[str]],
    conflict_resolving_queries: list[str] | tuple[str, ...] = (),
    current_iteration: int = 0,
    max_iterations: int = 0,
) -> dict[str, Any]:
    existing = dict(existing_candidate_trace or {})
    ordinary_queries = compact_runtime_strings_fn(existing.get("ordinary_next_queries"))
    if not ordinary_queries:
        ordinary_queries = compact_runtime_strings_fn(getattr(evidence_state, "next_queries", ()))
    prior_queries = compact_runtime_strings_fn(existing.get("prior_queries"))
    if not prior_queries:
        prior_queries = compact_runtime_strings_fn(getattr(evidence_state, "prior_queries", ()))
    resolving_queries = compact_runtime_strings_fn(conflict_resolving_queries)
    if not resolving_queries:
        resolving_queries = compact_runtime_strings_fn(existing.get("conflict_resolving_queries"))
    if not resolving_queries:
        resolving_queries = compact_runtime_strings_fn(getattr(evidence_state, "resolving_queries", ()))
    source_path = existing.get("source_path") or existing.get("query_provenance")
    blockers = [
        blocker
        for blocker in (existing.get("blockers") or [])
        if blocker
        not in {
            "not_evaluated",
            "no_ordinary_next_queries",
            "source_path_not_ordinary_continuation",
        }
    ]
    return build_ordinary_continuation_candidate(
        source_path=str(source_path) if source_path else None,
        ordinary_next_queries=ordinary_queries,
        query_provenance=str(source_path) if source_path else None,
        prior_queries=prior_queries,
        prior_query_count=existing.get("prior_query_count"),
        conflict_resolving_queries=resolving_queries,
        current_iteration=int(existing.get("current_iteration") or current_iteration or 0),
        max_iterations=int(existing.get("max_iterations") or max_iterations or 0),
        next_queries_redundant="redundant_with_prior_queries" in set(existing.get("blockers") or []),
        budget_exhausted="blocked_by_iteration_budget" in set(existing.get("blockers") or []),
        considered=bool(existing.get("considered") or ordinary_queries),
        extra_blockers=blockers,
    ).to_dict()

def build_retrieval_stop_trace_projection(
    *,
    decision: RetrievalStopDecision,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    blockers: list[str] | tuple[str, ...] = (),
    build_shadow_telemetry: Callable[..., dict[str, Any]] = build_retrieval_stop_shadow_telemetry,
) -> dict[str, Any]:
    decision_value = decision.decision.value
    shadow_telemetry = build_shadow_telemetry(
        actual_decision=decision_value,
        stage=stage,
        evaluator_sufficient=evaluator_sufficient,
        iteration=iteration,
        max_iterations=max_iterations,
        prior_queries=prior_queries,
        next_queries=next_queries,
        query_source=query_source,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_completed=weak_corpus_recovery_completed,
        blockers=blockers,
    )
    is_continue_retrieval = decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
    source_path = source_path_from_runtime_source(query_source)
    return {
        "retrieval_stop_shadow_telemetry": shadow_telemetry,
        "ordinary_continuation_candidate_trace": build_ordinary_continuation_candidate(
            source_path=source_path,
            ordinary_next_queries=next_queries,
            query_provenance=source_path,
            prior_queries=prior_queries,
            conflict_resolving_queries=(),
            current_iteration=iteration,
            max_iterations=max_iterations,
            next_queries_redundant=(
                (not is_continue_retrieval)
                and decision.decision is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
            ),
            budget_exhausted=(
                (not is_continue_retrieval)
                and decision.decision is RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED
            ),
            considered=True,
            extra_blockers=blockers,
        ).to_dict(),
    }
