"""Shadow-only retrieval budget pressure diagnostics.

This module is intentionally pure. It reads already-computed execution trace
facts and final source metadata, then returns a compact nested telemetry
payload. It does not call providers, models, prompts, retrieval, storage, or
routing code.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA_VERSION = "retrieval_budget_pressure_shadow_v1"

SOURCE_CLASS_BUCKETS = (
    "official_current_rules",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
    "primary_source_documents",
    "none",
)

EXTRA_PASS_REASONS = (
    "budget_exhausted",
    "missing_expected_source_class",
    "nonredundant_next_queries",
    "useful_last_pass_yield",
    "official_evidence_missing",
    "quant_metric_coverage_missing",
)

EXTRA_PASS_BLOCKERS = (
    "not_budget_exhausted",
    "evaluator_sufficient",
    "no_unresolved_gaps",
    "no_next_queries",
    "query_novelty_low",
    "last_pass_low_yield",
    "weak_corpus_recovery_completed",
    "corpus_off_topic",
    "cost_state_unavailable",
)

_RETRIEVAL_ATTEMPT_ROLES = {
    "main_retrieval",
    "weak_corpus_recovery",
    "disambiguation_retry",
}
_OFFICIAL_GAP_SOURCE_CLASSES = {
    "official_current_rules",
    "issuer_filings_or_company_materials",
    "primary_source_documents",
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _bool_or_none(value: Any) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_01_or_none(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None:
        return None
    return max(0.0, min(1.0, number))


def _compact_string(value: Any, *, limit: int = 80) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:limit]


def _source_class_bucket(value: Any) -> str:
    text = _compact_string(value, limit=120)
    if text in SOURCE_CLASS_BUCKETS and text != "none":
        return text
    return "unknown"


def _source_class_list(value: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _as_list(value):
        bucket = _source_class_bucket(item)
        if bucket == "unknown":
            continue
        if bucket not in seen:
            out.append(bucket)
            seen.add(bucket)
    return out


def _compact_string_list(value: Any, *, max_items: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _as_list(value):
        text = _compact_string(item)
        if text and text not in seen:
            out.append(text)
            seen.add(text)
        if len(out) >= max_items:
            break
    return out


def _last_iteration_from_queries(trace: Mapping[str, Any]) -> int | None:
    queries = _as_mapping(trace.get("queries_per_iteration"))
    iterations: list[int] = []
    for key in queries:
        value = _nonnegative_int(key)
        if value is not None:
            iterations.append(value)
    return max(iterations) if iterations else None


def _provider_attempts(trace: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        attempt
        for attempt in _as_list(trace.get("provider_diagnostics"))
        if isinstance(attempt, Mapping)
    ]


def _last_pass_attempts(
    trace: Mapping[str, Any],
    iteration: int | None,
) -> list[Mapping[str, Any]]:
    attempts = [
        attempt
        for attempt in _provider_attempts(trace)
        if str(attempt.get("provider_role") or "") in _RETRIEVAL_ATTEMPT_ROLES
    ]
    if not attempts:
        return []

    numeric_iterations = [
        value
        for attempt in attempts
        if (value := _nonnegative_int(attempt.get("iteration"))) is not None
    ]
    target_iteration = iteration or (max(numeric_iterations) if numeric_iterations else None)
    if target_iteration is None:
        return []
    return [
        attempt
        for attempt in attempts
        if _nonnegative_int(attempt.get("iteration")) == target_iteration
    ]


def _sum_attempt_field(
    attempts: list[Mapping[str, Any]],
    field: str,
) -> int | None:
    if not attempts:
        return None
    total = 0
    for attempt in attempts:
        if field not in attempt:
            return None
        value = _nonnegative_int(attempt.get(field))
        if value is None:
            return None
        total += value
    return total


def _provider_attempt_count(attempts: list[Mapping[str, Any]]) -> int | None:
    if not attempts:
        return None
    total = 0
    for attempt in attempts:
        total += _nonnegative_int(attempt.get("logical_attempt_count")) or 1
    return total


def _query_novelty_score(attempts: list[Mapping[str, Any]]) -> float | None:
    similarities = [
        value
        for attempt in attempts
        if (value := _float_01_or_none(attempt.get("query_similarity_max"))) is not None
    ]
    if not similarities:
        return None
    return round(1.0 - max(similarities), 3)


def _budget_pressure_bucket(
    *,
    budget_stop_triggered: bool,
    iterations_run: int | None,
    max_iterations: int | None,
) -> str:
    if budget_stop_triggered:
        return "exhausted"
    if iterations_run is None or max_iterations is None or max_iterations <= 0:
        return "unknown"
    if iterations_run >= max_iterations:
        return "at_cap"
    remaining = max_iterations - iterations_run
    if remaining == 1:
        return "near_cap"
    if remaining > 1:
        return "room_remaining"
    return "unknown"


def _query_source_from_stage(stage: Any) -> str:
    text = str(stage or "")
    if "source_class" in text:
        return "source_class_recovery"
    if "expander" in text:
        return "expander"
    if "scout" in text:
        return "scout"
    if "evaluator" in text:
        return "evaluator"
    if "budget" in text:
        return "budget"
    if "weak_corpus" in text:
        return "weak_corpus_recovery"
    if "pre_search" in text:
        return "pre_search"
    return "unknown" if text else "none"


def _cost_state(trace: Mapping[str, Any]) -> dict[str, Any]:
    cost = _as_mapping(trace.get("cost"))
    estimated = _float_or_none(cost.get("total_cost_usd"))
    available = estimated is not None
    return {
        "estimated_cost_usd": round(estimated, 6) if available else None,
        "estimated_cost_available": available,
        "estimated_cost_source": (
            "cost_accumulator_snapshot" if available else "unavailable"
        ),
        "estimated_cost_confidence_bucket": (
            "directional_partial" if available else "unavailable"
        ),
        "cost_budget_soft_cap_usd": None,
        "cost_budget_hard_cap_usd": None,
        "cost_budget_spent_ratio": None,
    }


def _last_pass_marginal_yield(
    trace: Mapping[str, Any],
    *,
    iteration: int | None,
) -> dict[str, Any]:
    attempts = _last_pass_attempts(trace, iteration)
    return {
        "new_source_count_last_pass": _sum_attempt_field(
            attempts,
            "new_source_count",
        ),
        "new_domain_count_last_pass": _sum_attempt_field(
            attempts,
            "new_domain_count",
        ),
        "new_accepted_source_count_last_pass": _sum_attempt_field(
            attempts,
            "accepted_url_count",
        ),
        "accepted_overlap_last_pass": _sum_attempt_field(
            attempts,
            "accepted_url_overlap_count",
        ),
        "query_novelty_score": _query_novelty_score(attempts),
        "provider_attempts_last_pass": _provider_attempt_count(attempts),
        "new_official_source_count_last_pass": None,
        "new_primary_source_count_last_pass": None,
    }


def _remaining_evidence_gaps(trace: Mapping[str, Any]) -> dict[str, Any]:
    missing_classes = _source_class_list(trace.get("missing_expected_source_classes"))
    source_class_query_count = _nonnegative_int(
        trace.get("source_class_recovery_query_count")
    )
    if source_class_query_count is None:
        source_class_query_count = len(_as_list(trace.get("source_class_recovery_queries")))

    if missing_classes and source_class_query_count > 0:
        next_query_count = source_class_query_count
        next_query_source = "source_class_recovery"
    else:
        next_query_count = _nonnegative_int(
            trace.get("retrieval_stop_shadow_next_query_count")
        ) or 0
        next_query_source = (
            _query_source_from_stage(trace.get("retrieval_stop_shadow_stage"))
            if next_query_count > 0
            else "none"
        )

    shadow_decision = str(trace.get("retrieval_stop_shadow_decision") or "")
    shadow_reason = str(trace.get("retrieval_stop_shadow_reason") or "")
    evaluator_sufficient: bool | None
    if shadow_decision == "proceed_to_synthesis" or shadow_reason == "evaluator_sufficient":
        evaluator_sufficient = True
    elif shadow_decision in {
        "continue_retrieval",
        "stop_no_queries",
        "stop_redundant_queries",
    }:
        evaluator_sufficient = False
    else:
        evaluator_sufficient = None

    return {
        "evaluator_sufficient": evaluator_sufficient,
        "next_query_count": next_query_count,
        "next_query_source": next_query_source,
        "missing_expected_source_classes": missing_classes,
        "official_evidence_found": _bool_or_none(trace.get("official_evidence_found")),
        "community_signal_found": _bool_or_none(trace.get("community_signal_found")),
        "quant_metric_coverage_valid": (
            _bool_or_none(trace.get("quant_retrieval_metric_coverage_valid"))
            if "quant_retrieval_metric_coverage_valid" in trace
            else None
        ),
        "corpus_state": _compact_string(trace.get("corpus_state"), limit=80),
        "pre_analyst_gate_signals": _compact_string_list(
            trace.get("pre_analyst_gate_signals")
        ),
    }


def _has_useful_yield(yield_payload: Mapping[str, Any]) -> bool:
    for field in (
        "new_source_count_last_pass",
        "new_domain_count_last_pass",
        "new_accepted_source_count_last_pass",
    ):
        value = _nonnegative_int(yield_payload.get(field))
        if value is not None and value > 0:
            return True
    return False


def _last_pass_low_yield(yield_payload: Mapping[str, Any]) -> bool:
    if _nonnegative_int(yield_payload.get("provider_attempts_last_pass")) is None:
        return False
    values = [
        _nonnegative_int(yield_payload.get(field))
        for field in (
            "new_source_count_last_pass",
            "new_domain_count_last_pass",
            "new_accepted_source_count_last_pass",
        )
    ]
    known_values = [value for value in values if value is not None]
    return bool(known_values) and all(value <= 0 for value in known_values)


def _unresolved_gap_state(
    trace: Mapping[str, Any],
    remaining: Mapping[str, Any],
) -> tuple[int, bool, bool, bool, bool]:
    missing_classes = list(remaining.get("missing_expected_source_classes") or [])
    signals = set(remaining.get("pre_analyst_gate_signals") or [])
    official_found = remaining.get("official_evidence_found")
    community_found = remaining.get("community_signal_found")
    quant_metric_valid = remaining.get("quant_metric_coverage_valid")

    official_missing = (
        official_found is False
        and (
            bool(set(missing_classes) & _OFFICIAL_GAP_SOURCE_CLASSES)
            or "missing_expected_official_evidence" in signals
        )
    )
    community_missing = (
        community_found is False
        and "missing_expected_community_signal" in signals
    )
    quant_missing = (
        trace.get("quant_retrieval_target_detected") is True
        and quant_metric_valid is False
    )

    unresolved = len(missing_classes)
    if official_missing and not (set(missing_classes) & _OFFICIAL_GAP_SOURCE_CLASSES):
        unresolved += 1
    if community_missing:
        unresolved += 1
    if quant_missing:
        unresolved += 1
    return unresolved, bool(missing_classes), official_missing, quant_missing, community_missing


def _extra_pass_judgment(
    *,
    hard_budget: Mapping[str, Any],
    cost_state: Mapping[str, Any],
    last_pass_yield: Mapping[str, Any],
    remaining: Mapping[str, Any],
    unresolved_gap_count: int,
    has_missing_source_class: bool,
    official_missing: bool,
    quant_missing: bool,
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    blockers: list[str] = []

    budget_stop_triggered = hard_budget.get("budget_stop_triggered") is True
    if budget_stop_triggered:
        reasons.append("budget_exhausted")
    else:
        blockers.append("not_budget_exhausted")

    if remaining.get("evaluator_sufficient") is True:
        blockers.append("evaluator_sufficient")

    if unresolved_gap_count <= 0:
        blockers.append("no_unresolved_gaps")
    if has_missing_source_class:
        reasons.append("missing_expected_source_class")
    if official_missing:
        reasons.append("official_evidence_missing")
    if quant_missing:
        reasons.append("quant_metric_coverage_missing")

    next_query_count = _nonnegative_int(remaining.get("next_query_count")) or 0
    if next_query_count > 0:
        reasons.append("nonredundant_next_queries")
    else:
        blockers.append("no_next_queries")

    novelty = _float_01_or_none(last_pass_yield.get("query_novelty_score"))
    if novelty is not None and novelty < 0.25:
        blockers.append("query_novelty_low")

    if _has_useful_yield(last_pass_yield):
        reasons.append("useful_last_pass_yield")
    elif _last_pass_low_yield(last_pass_yield):
        blockers.append("last_pass_low_yield")

    if (
        trace.get("weak_corpus_recovery_used") is True
        or trace.get("retrieval_stop_shadow_decision") == "stop_after_recovery"
    ):
        blockers.append("weak_corpus_recovery_completed")

    if remaining.get("corpus_state") == "OFF_TOPIC":
        blockers.append("corpus_off_topic")

    if cost_state.get("estimated_cost_available") is not True:
        blockers.append("cost_state_unavailable")

    deduped_reasons = [reason for reason in EXTRA_PASS_REASONS if reason in set(reasons)]
    deduped_blockers = [
        blocker for blocker in EXTRA_PASS_BLOCKERS if blocker in set(blockers)
    ]
    candidate = bool(
        budget_stop_triggered
        and unresolved_gap_count > 0
        and next_query_count > 0
        and not deduped_blockers
    )
    return {
        "extra_pass_candidate_shadow": candidate,
        "extra_pass_candidate_reasons": deduped_reasons,
        "extra_pass_candidate_blockers": deduped_blockers,
        "extra_pass_candidate_query_count": next_query_count,
        "extra_pass_candidate_query_source": remaining.get("next_query_source") or "none",
        "extra_pass_budget_class": hard_budget.get("budget_pressure_bucket")
        or "unknown",
    }


def _final_answer_source_ids(trace: Mapping[str, Any]) -> set[str] | None:
    value = trace.get("final_answer_source_ids_used")
    if not isinstance(value, (list, tuple, set)):
        return None
    return {
        str(item).strip()
        for item in value
        if str(item).strip()
    }


def _final_answer_official_source_count(
    *,
    cited_source_ids: set[str] | None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
) -> int | None:
    if cited_source_ids is None or final_top_evidence is None:
        return None
    official_ids: set[str] = set()
    for source in final_top_evidence:
        if not isinstance(source, Mapping):
            continue
        source_id = str(source.get("source_id") or "").strip()
        if source_id and str(source.get("source_tier") or "") == "official":
            official_ids.add(source_id)
    return len(cited_source_ids & official_ids)


def _answer_quality_impact(
    *,
    trace: Mapping[str, Any],
    budget_stop_triggered: bool,
    unresolved_gap_count: int,
    has_missing_source_class: bool,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    cited_source_ids = _final_answer_source_ids(trace)
    budget_limited = bool(budget_stop_triggered and unresolved_gap_count > 0)
    if budget_limited:
        reason = "budget_exhausted_with_unresolved_gaps"
    elif budget_stop_triggered:
        reason = "budget_exhausted_no_unresolved_gaps"
    else:
        reason = "not_budget_exhausted"

    answer_outcome = trace.get("answer_outcome")
    if answer_outcome is None:
        answer_outcome = trace.get("answer_class")

    return {
        "budget_limited_answer_shadow": budget_limited,
        "budget_limited_answer_reason": reason,
        "unresolved_gap_count_at_synthesis": unresolved_gap_count,
        "author_budget_caveat_present": None,
        "answer_outcome": _compact_string(answer_outcome, limit=80),
        "review_flags": trace.get("review_flags") if "review_flags" in trace else None,
        "final_answer_source_count": (
            len(cited_source_ids) if cited_source_ids is not None else None
        ),
        "final_answer_official_source_count": _final_answer_official_source_count(
            cited_source_ids=cited_source_ids,
            final_top_evidence=final_top_evidence,
        ),
        "final_answer_missing_expected_source_class": has_missing_source_class,
        "user_feedback_rating": None,
        "manual_eval_score_if_available": None,
    }


def build_retrieval_budget_pressure_shadow(
    *,
    trace: Mapping[str, Any],
    max_iterations: Any = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the nested retrieval budget pressure shadow payload."""
    execution_trace = _as_mapping(trace)
    iterations_run = _nonnegative_int(execution_trace.get("iterations_run"))
    max_iterations_int = _nonnegative_int(max_iterations)
    last_iteration = _last_iteration_from_queries(execution_trace)

    active_decision = execution_trace.get("retrieval_stop_active_decision")
    shadow_decision = execution_trace.get("retrieval_stop_shadow_decision")
    budget_stop_triggered = (
        active_decision == "stop_budget_exhausted"
        or shadow_decision == "stop_budget_exhausted"
    )
    budget_stop_reason = None
    if active_decision == "stop_budget_exhausted":
        budget_stop_reason = _compact_string(
            execution_trace.get("retrieval_stop_active_reason")
        )
    elif shadow_decision == "stop_budget_exhausted":
        budget_stop_reason = _compact_string(
            execution_trace.get("retrieval_stop_shadow_reason")
        )

    hard_budget = {
        "mode": _compact_string(execution_trace.get("mode"), limit=80),
        "iteration": last_iteration,
        "max_iterations": max_iterations_int,
        "iterations_run": iterations_run,
        "budget_stop_triggered": budget_stop_triggered,
        "budget_stop_reason": budget_stop_reason,
        "budget_pressure_bucket": _budget_pressure_bucket(
            budget_stop_triggered=budget_stop_triggered,
            iterations_run=iterations_run,
            max_iterations=max_iterations_int,
        ),
    }
    cost = _cost_state(execution_trace)
    last_pass_yield = _last_pass_marginal_yield(
        execution_trace,
        iteration=last_iteration,
    )
    remaining = _remaining_evidence_gaps(execution_trace)
    (
        unresolved_gap_count,
        has_missing_source_class,
        official_missing,
        quant_missing,
        _community_missing,
    ) = _unresolved_gap_state(execution_trace, remaining)
    extra_pass = _extra_pass_judgment(
        hard_budget=hard_budget,
        cost_state=cost,
        last_pass_yield=last_pass_yield,
        remaining=remaining,
        unresolved_gap_count=unresolved_gap_count,
        has_missing_source_class=has_missing_source_class,
        official_missing=official_missing,
        quant_missing=quant_missing,
        trace=execution_trace,
    )
    answer_quality = _answer_quality_impact(
        trace=execution_trace,
        budget_stop_triggered=budget_stop_triggered,
        unresolved_gap_count=unresolved_gap_count,
        has_missing_source_class=has_missing_source_class,
        final_top_evidence=final_top_evidence,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "shadow_mode": True,
        "hard_mode_budget": hard_budget,
        "cost_state": cost,
        "last_pass_marginal_yield": last_pass_yield,
        "remaining_evidence_gaps": remaining,
        "extra_pass_judgment": extra_pass,
        "answer_quality_impact": answer_quality,
    }


__all__ = [
    "EXTRA_PASS_BLOCKERS",
    "EXTRA_PASS_REASONS",
    "SCHEMA_VERSION",
    "SOURCE_CLASS_BUCKETS",
    "build_retrieval_budget_pressure_shadow",
]
