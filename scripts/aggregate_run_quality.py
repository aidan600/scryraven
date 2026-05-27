"""Read output/execution_log.jsonl and print quick run-quality snapshots.

After changing retrieval or routing, run a few queries from docs/eval_queries.md, then:

    python scripts/aggregate_run_quality.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "output" / "execution_log.jsonl"
KB_TRIGGERS = ROOT / "output" / "kb_triggers.jsonl"
DEFAULT_LAST_N = 20


def _count_bucket(value: Any, buckets: tuple[tuple[int, str], ...], fallback: str) -> str:
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        n = 0
    for upper, label in buckets:
        if n <= upper:
            return label
    return fallback


def _query_count_bucket(value: Any) -> str:
    return _count_bucket(value, ((0, "0"), (1, "1"), (3, "2-3")), "4+")


def _new_passage_count_bucket(value: Any) -> str:
    return _count_bucket(value, ((0, "0"), (1, "1"), (5, "2-5")), "6+")


def _source_card_count_bucket(value: Any) -> str:
    return _count_bucket(value, ((0, "0"), (1, "1"), (5, "2-5")), "6+")


def _provider_overlap_count_bucket(value: Any) -> str:
    return _count_bucket(value, ((0, "0"), (1, "1"), (5, "2-5"), (20, "6-20")), "21+")


def _provider_similarity_bucket(value: Any) -> str:
    if value is None:
        return "missing"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "missing"
    if n <= 0:
        return "0"
    if n <= 0.25:
        return "0.01-0.25"
    if n <= 0.5:
        return "0.26-0.50"
    if n <= 0.75:
        return "0.51-0.75"
    return "0.76-1.00"


_CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION = "controller_diagnostics_v1"
_CONTROLLER_DIAGNOSTICS_SOURCE = "posthoc_execution_trace"
_CONTROLLER_PLAN_DISPOSITIONS = (
    "required",
    "optional",
    "shadow",
    "may_run",
    "blocked_by_mode",
    "not_applicable",
)
_CONTROLLER_TASK_STATUSES = (
    "planned",
    "started",
    "completed",
    "skipped",
    "blocked",
    "failed",
)
_CONTROLLER_PLANNED_STATUSES = (
    "observed_started",
    "observed_completed",
    "observed_skipped",
    "observed_blocked",
    "observed_failed",
    "missing_required",
    "dependency_blocked",
    "optional_not_observed",
    "may_run_not_observed",
    "shadow_not_observed",
    "blocked_by_mode",
    "not_applicable",
)
_SOURCE_CLASS_RECOVERY_NOT_OBSERVED_STATUSES = (
    "optional_not_observed",
    "may_run_not_observed",
    "shadow_not_observed",
)
_CONTROLLER_DIAGNOSTICS_OMISSION_REASON_FIELDS = (
    "controller_diagnostics_omission_reason",
    "controller_diagnostics_omitted_reason",
    "controller_diagnostics_skip_reason",
)
_CONTROLLER_DIAGNOSTICS_OMISSION_FLAG_FIELDS = (
    "controller_diagnostics_omitted",
    "controller_diagnostics_payload_omitted",
)
_RETRIEVAL_STOP_SHADOW_FIELDS = (
    "retrieval_stop_shadow_available",
    "retrieval_stop_shadow_decision",
    "retrieval_stop_shadow_reason",
    "retrieval_stop_shadow_blockers",
    "retrieval_stop_shadow_next_query_count",
    "retrieval_stop_shadow_alignment",
    "retrieval_stop_shadow_stage",
    "retrieval_stop_shadow_mode",
)
_RETRIEVAL_STOP_SHADOW_DECISIONS = (
    "proceed_to_synthesis",
    "continue_retrieval",
    "stop_no_queries",
    "stop_budget_exhausted",
    "stop_redundant_queries",
    "stop_after_recovery",
    "blocked_with_reason",
)
_RETRIEVAL_STOP_SHADOW_REASONS = (
    "evaluator_sufficient",
    "candidate_queries_available",
    "no_new_queries",
    "iteration_budget_exhausted",
    "redundant_with_prior_queries",
    "weak_corpus_recovery_completed",
    "shadow_unavailable",
)
_RETRIEVAL_STOP_SHADOW_ALIGNMENTS = (
    "aligned",
    "mismatch",
    "unavailable",
)
_RETRIEVAL_STOP_SHADOW_STAGES = (
    "pre_search_redundant_queries",
    "weak_corpus_recovery_completed",
    "scout_directed_continuation",
    "expander_component_queries",
    "evaluator",
    "evaluator_redundant_queries",
    "evaluator_no_queries",
    "iteration_budget_exhausted",
)
_RETRIEVAL_STOP_ACTIVE_FIELDS = (
    "retrieval_stop_active_available",
    "retrieval_stop_active_decision",
    "retrieval_stop_active_reason",
    "retrieval_stop_active_blockers",
    "retrieval_stop_active_next_query_count",
    "retrieval_stop_active_stage",
    "retrieval_stop_active_mode",
    "retrieval_stop_active_shadow_alignment",
    "retrieval_stop_active_fallback_reason",
)
_RETRIEVAL_STOP_ACTIVE_DECISIONS = (
    "stop_no_queries",
    "stop_budget_exhausted",
)
_RETRIEVAL_STOP_ACTIVE_REASONS = (
    "no_new_queries",
    "iteration_budget_exhausted",
    "active_controller_unavailable",
)
_RETRIEVAL_STOP_ACTIVE_STAGES = (
    "evaluator_no_queries",
    "iteration_budget_exhausted",
)
_RETRIEVAL_STOP_ACTIVE_MODES = (
    "active_stop_no_queries",
    "active_stop_budget_exhausted",
)
_RETRIEVAL_STOP_ACTIVE_SHADOW_ALIGNMENTS = (
    "aligned",
    "mismatch",
    "shadow_unavailable",
    "not_evaluated",
)
_RETRIEVAL_STOP_ACTIVE_FALLBACK_REASONS = (
    "unexpected_controller_decision",
    "controller_exception",
)
_RETRIEVAL_BUDGET_PRESSURE_SCHEMA_VERSION = "retrieval_budget_pressure_shadow_v1"
_RETRIEVAL_BUDGET_PRESSURE_BUCKETS = (
    "exhausted",
    "at_cap",
    "near_cap",
    "room_remaining",
    "unknown",
)
_RETRIEVAL_BUDGET_STOP_REASONS = (
    "iteration_budget_exhausted",
)
_RETRIEVAL_BUDGET_COST_SOURCES = (
    "cost_accumulator_snapshot",
    "unavailable",
)
_RETRIEVAL_BUDGET_COST_CONFIDENCE_BUCKETS = (
    "directional_partial",
    "unavailable",
)
_RETRIEVAL_BUDGET_SOURCE_CLASS_BUCKETS = (
    "official_current_rules",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
    "primary_source_documents",
    "none",
)
_RETRIEVAL_BUDGET_EXTRA_PASS_REASONS = (
    "budget_exhausted",
    "missing_expected_source_class",
    "nonredundant_next_queries",
    "useful_last_pass_yield",
    "official_evidence_missing",
    "quant_metric_coverage_missing",
)
_RETRIEVAL_BUDGET_EXTRA_PASS_BLOCKERS = (
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
_RETRIEVAL_BUDGET_QUERY_SOURCES = (
    "source_class_recovery",
    "evaluator",
    "expander",
    "scout",
    "budget",
    "weak_corpus_recovery",
    "pre_search",
    "none",
)
_RETRIEVAL_BUDGET_LIMITED_ANSWER_REASONS = (
    "budget_exhausted_with_unresolved_gaps",
    "budget_exhausted_no_unresolved_gaps",
    "not_budget_exhausted",
)
_RETRIEVAL_BUDGET_ANSWER_OUTCOMES = (
    "answered",
    "partial_answer",
    "no_evidence_found",
    "off_topic_retrieval",
    "declined_by_policy",
)
_SOURCE_CLASS_OBSERVABILITY_FIELDS = (
    "expected_source_classes_raw",
    "source_class_gap_candidates",
    "source_class_underfire_shadow",
    "source_class_underfire_reasons",
    "source_class_underfire_blockers",
    "final_official_source_count",
    "final_primary_source_count",
    "final_archival_source_count",
    "final_legal_or_regulatory_source_count",
    "source_class_satisfaction_counts",
    "source_class_satisfaction_status",
    "source_class_satisfaction_strength_counts",
    "source_class_strong_satisfaction_counts",
    "source_class_weak_satisfaction_counts",
    "source_class_secondary_only_counts",
)
_SOURCE_CLASS_OBSERVABILITY_BUCKETS = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "parliamentary_or_legislative_material",
    "primary_source_documents",
    "archival_primary_text",
    "historical_legal_text",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
    "none",
)
_SOURCE_CLASS_UNDERFIRE_REASONS = (
    "missing_expected_source_class",
    "no_final_evidence",
)
_SOURCE_CLASS_UNDERFIRE_BLOCKERS = (
    "no_expected_source_class",
    "all_expected_source_classes_satisfied",
)
_SOURCE_CLASS_SATISFACTION_STATUSES = (
    "satisfied_strong",
    "satisfied_weak",
    "expected_but_only_secondary",
    "unsatisfied",
)
_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_SCHEMA_VERSION = (
    "source_class_recovery_candidate_v2"
)
_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS = (
    "expected_source_class_unsatisfied",
    "expected_source_class_secondary_only",
    "expected_source_class_weakly_satisfied",
    "final_answer_lacks_official_source",
    "final_answer_lacks_primary_source",
    "final_answer_lacks_archival_source",
    "final_answer_lacks_legal_or_regulatory_source",
    "answer_class_partial_or_no_evidence",
    "corpus_off_topic_with_expected_source_class",
    "at_cap_with_source_class_underfire",
    "budget_exhausted_with_source_class_underfire",
)
_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS = (
    "all_expected_source_classes_satisfied_strong",
    "no_expected_source_class",
    "weak_corpus_recovery_owns_path",
    "active_recovery_already_used",
    "no_recovery_query_available",
    "budget_hard_exhausted",
    "fast_mode_policy_block",
    "existing_active_recovery_blocked_by_budget",
    "unsupported_off_domain_retrieval",
)
_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_QUERY_SOURCES = (
    "class_intent_catalog",
    "none",
)
SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION = (
    "source_class_recovery_validation_l1"
)
SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY = "source_class_recovery_validation_l1"
SOURCE_CLASS_RECOVERY_BOTTLENECK_STATUSES = (
    "not_triggered",
    "triggered_no_candidates",
    "candidates_not_accepted",
    "accepted_not_visible",
    "visible_not_final_cited",
    "satisfied",
    "unknown",
)
_SOURCE_CLASS_RECOVERY_VALIDATION_ACTION_STATUSES = (
    "approved",
    "blocked",
    "skipped",
    "shadow",
    "completed",
    "failed",
    "informational",
)
_SOURCE_CLASS_RECOVERY_VALIDATION_QUALITY_STATUSES = (
    "official_or_primary_found",
    "secondary_only",
    "no_relevant_sources",
    "classification_mismatch",
    "promoted_but_not_final",
    "unknown",
)


def _controller_count(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _controller_count_bucket(value: Any) -> str:
    return _count_bucket(
        _controller_count(value),
        ((0, "0"), (1, "1"), (5, "2-5"), (20, "6-20")),
        "21+",
    )


def _controller_expected_bucket(value: Any, expected: str) -> str:
    if value == expected:
        return expected
    return "unexpected_or_missing"


def _controller_true_bucket(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "missing"


def _controller_safe_scalar_bucket(
    value: Any,
    allowed_keys: tuple[str, ...],
    anomalies: Counter[str],
    anomaly_name: str,
) -> str:
    if value is None:
        return "missing"
    bucket = str(value)
    if bucket in set(allowed_keys):
        return bucket
    anomalies[anomaly_name] += 1
    return "unknown"


def _controller_diagnostics_omission_reason_bucket(trace: dict[str, Any]) -> str | None:
    reason_present = False
    for field in _CONTROLLER_DIAGNOSTICS_OMISSION_REASON_FIELDS:
        raw_reason = trace.get(field)
        if raw_reason is None:
            continue
        reason_present = True
        reason = str(raw_reason).casefold()
        if any(
            marker in reason
            for marker in ("size", "oversize", "too_large", "too large", "max bytes")
        ):
            return "size_or_oversized"
        if any(
            marker in reason
            for marker in ("builder", "exception", "error", "failed", "failure")
        ):
            return "builder_exception"
        if reason.strip():
            return "other"
    if any(
        trace.get(field) is True
        for field in _CONTROLLER_DIAGNOSTICS_OMISSION_FLAG_FIELDS
    ):
        return "missing"
    if reason_present:
        return "missing"
    return None


def _add_source_class_recovery_stage_counts(
    summary: dict[str, Any],
    trace: dict[str, Any],
    payload: dict[str, Any],
    anomalies: Counter[str],
) -> None:
    planned_vs_observed = payload.get("planned_vs_observed")
    if not isinstance(planned_vs_observed, dict):
        return
    stages = planned_vs_observed.get("stages")
    if stages is None:
        return
    if not isinstance(stages, list):
        anomalies["planned_vs_observed_stages_not_list"] += 1
        return

    for stage in stages:
        if not isinstance(stage, dict):
            anomalies["planned_vs_observed_stage_not_mapping"] += 1
            continue
        if stage.get("stage_id") != "source_class_recovery":
            continue

        summary["source_class_recovery_payload_rows"] += 1
        summary["source_class_recovery_stage_present_rows"] += 1
        status_bucket = _controller_safe_scalar_bucket(
            stage.get("status"),
            _CONTROLLER_PLANNED_STATUSES,
            anomalies,
            "source_class_recovery_status_unknown",
        )
        summary["source_class_recovery_stage_status_counts"][status_bucket] += 1
        if status_bucket in _SOURCE_CLASS_RECOVERY_NOT_OBSERVED_STATUSES:
            summary["source_class_recovery_not_observed_rows"] += 1
        elif status_bucket == "observed_blocked":
            summary["source_class_recovery_observed_blocked_rows"] += 1
        elif status_bucket == "observed_completed":
            summary["source_class_recovery_observed_completed_rows"] += 1

        observed_bucket = _controller_safe_scalar_bucket(
            stage.get("observed_status"),
            _CONTROLLER_TASK_STATUSES,
            anomalies,
            "source_class_recovery_observed_status_unknown",
        )
        summary["source_class_recovery_observed_status_counts"][observed_bucket] += 1
        disposition_bucket = _controller_safe_scalar_bucket(
            stage.get("disposition"),
            _CONTROLLER_PLAN_DISPOSITIONS,
            anomalies,
            "source_class_recovery_disposition_unknown",
        )
        summary["source_class_recovery_disposition_counts"][disposition_bucket] += 1
        if trace.get("active_source_class_recovery_used") is True:
            summary["source_class_recovery_active_used_rows"] += 1
        if status_bucket in ("missing", "unknown") or observed_bucket == "unknown":
            summary["source_class_recovery_unknown_or_malformed_status_rows"] += 1
        return


def _add_known_controller_counts(
    target: Counter[str],
    value: Any,
    allowed_keys: tuple[str, ...],
    anomalies: Counter[str],
    anomaly_prefix: str,
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        anomalies[f"{anomaly_prefix}_not_mapping"] += 1
        return

    allowed = set(allowed_keys)
    for raw_key, raw_count in value.items():
        count = _controller_count(raw_count)
        if str(raw_key) in allowed:
            if count > 0:
                target[str(raw_key)] += count
            continue
        anomalies[f"{anomaly_prefix}_unknown_key"] += 1
        if count > 0:
            target["unknown"] += count


def _ordered_counter_dict(
    counter: Counter[str],
    order: tuple[str, ...] = (),
) -> dict[str, int]:
    ordered = {
        key: counter[key]
        for key in order
        if counter.get(key, 0) > 0
    }
    for key, value in counter.most_common():
        if value > 0 and key not in ordered:
            ordered[key] = value
    return ordered


def _retrieval_stop_safe_bucket(
    value: Any,
    allowed_keys: tuple[str, ...],
) -> tuple[str, bool]:
    if value is None:
        return "missing", True
    if not isinstance(value, str):
        return "unknown", True
    if value in set(allowed_keys):
        return value, False
    return "unknown", True


def _retrieval_stop_next_query_count_bucket(value: Any) -> tuple[str, bool]:
    if value is None:
        return "missing", True
    if isinstance(value, bool):
        return "unknown", True
    try:
        count = int(value)
    except (TypeError, ValueError):
        return "unknown", True
    if count < 0:
        return "unknown", True
    return _query_count_bucket(count), False


def _summarize_retrieval_stop_shadow(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "retrieval_stop_shadow_available_rows": 0,
        "retrieval_stop_shadow_decision_counts": Counter(),
        "retrieval_stop_shadow_reason_counts": Counter(),
        "retrieval_stop_shadow_alignment_counts": Counter(),
        "retrieval_stop_shadow_stage_counts": Counter(),
        "retrieval_stop_shadow_next_query_count_buckets": Counter(),
        "retrieval_stop_shadow_unknown_or_malformed_rows": 0,
    }

    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            continue
        if not any(field in trace for field in _RETRIEVAL_STOP_SHADOW_FIELDS):
            continue

        row_unknown_or_malformed = False
        available = trace.get("retrieval_stop_shadow_available")
        mode = trace.get("retrieval_stop_shadow_mode")
        if mode is not None and mode != "shadow_only":
            row_unknown_or_malformed = True

        if available is not True:
            if available is not False:
                row_unknown_or_malformed = True
            else:
                for field, allowed_keys in (
                    (
                        "retrieval_stop_shadow_decision",
                        _RETRIEVAL_STOP_SHADOW_DECISIONS,
                    ),
                    (
                        "retrieval_stop_shadow_reason",
                        _RETRIEVAL_STOP_SHADOW_REASONS,
                    ),
                    (
                        "retrieval_stop_shadow_alignment",
                        _RETRIEVAL_STOP_SHADOW_ALIGNMENTS,
                    ),
                    (
                        "retrieval_stop_shadow_stage",
                        _RETRIEVAL_STOP_SHADOW_STAGES,
                    ),
                ):
                    if field in trace and trace.get(field) is not None:
                        _bucket, malformed = _retrieval_stop_safe_bucket(
                            trace.get(field),
                            allowed_keys,
                        )
                        if malformed:
                            row_unknown_or_malformed = True
                if (
                    "retrieval_stop_shadow_next_query_count" in trace
                    and trace.get("retrieval_stop_shadow_next_query_count") is not None
                ):
                    _bucket, malformed = _retrieval_stop_next_query_count_bucket(
                        trace.get("retrieval_stop_shadow_next_query_count")
                    )
                    if malformed:
                        row_unknown_or_malformed = True
            if row_unknown_or_malformed:
                summary["retrieval_stop_shadow_unknown_or_malformed_rows"] += 1
            continue

        summary["retrieval_stop_shadow_available_rows"] += 1

        decision_bucket, decision_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_shadow_decision"),
            _RETRIEVAL_STOP_SHADOW_DECISIONS,
        )
        reason_bucket, reason_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_shadow_reason"),
            _RETRIEVAL_STOP_SHADOW_REASONS,
        )
        alignment_bucket, alignment_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_shadow_alignment"),
            _RETRIEVAL_STOP_SHADOW_ALIGNMENTS,
        )
        stage_bucket, stage_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_shadow_stage"),
            _RETRIEVAL_STOP_SHADOW_STAGES,
        )
        next_query_bucket, next_query_unknown = (
            _retrieval_stop_next_query_count_bucket(
                trace.get("retrieval_stop_shadow_next_query_count")
            )
        )

        summary["retrieval_stop_shadow_decision_counts"][decision_bucket] += 1
        summary["retrieval_stop_shadow_reason_counts"][reason_bucket] += 1
        summary["retrieval_stop_shadow_alignment_counts"][alignment_bucket] += 1
        summary["retrieval_stop_shadow_stage_counts"][stage_bucket] += 1
        summary["retrieval_stop_shadow_next_query_count_buckets"][
            next_query_bucket
        ] += 1

        if any(
            (
                decision_unknown,
                reason_unknown,
                alignment_unknown,
                stage_unknown,
                next_query_unknown,
                row_unknown_or_malformed,
            )
        ):
            summary["retrieval_stop_shadow_unknown_or_malformed_rows"] += 1

    return summary


def _print_retrieval_stop_shadow_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_retrieval_stop_shadow(tail)

    print()
    print(f"=== Retrieval-stop shadow telemetry (last {len(tail)} runs) ===")
    print(
        "retrieval_stop_shadow_available_rows: "
        f"{summary['retrieval_stop_shadow_available_rows']}"
    )
    print(
        "retrieval_stop_shadow_decision_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_shadow_decision_counts"],
            (*_RETRIEVAL_STOP_SHADOW_DECISIONS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_shadow_reason_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_shadow_reason_counts"],
            (*_RETRIEVAL_STOP_SHADOW_REASONS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_shadow_alignment_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_shadow_alignment_counts"],
            (*_RETRIEVAL_STOP_SHADOW_ALIGNMENTS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_shadow_stage_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_shadow_stage_counts"],
            (*_RETRIEVAL_STOP_SHADOW_STAGES, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_shadow_next_query_count_buckets:",
        _ordered_counter_dict(
            summary["retrieval_stop_shadow_next_query_count_buckets"],
            ("0", "1", "2-3", "4+", "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_shadow_unknown_or_malformed_rows: "
        f"{summary['retrieval_stop_shadow_unknown_or_malformed_rows']}"
    )


def _summarize_retrieval_stop_active(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "retrieval_stop_active_available_rows": 0,
        "retrieval_stop_active_fallback_rows": 0,
        "retrieval_stop_active_decision_counts": Counter(),
        "retrieval_stop_active_reason_counts": Counter(),
        "retrieval_stop_active_stage_counts": Counter(),
        "retrieval_stop_active_mode_counts": Counter(),
        "retrieval_stop_active_shadow_alignment_counts": Counter(),
        "retrieval_stop_active_fallback_reason_counts": Counter(),
        "retrieval_stop_active_next_query_count_buckets": Counter(),
        "retrieval_stop_active_unknown_or_malformed_rows": 0,
    }

    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            continue
        if not any(field in trace for field in _RETRIEVAL_STOP_ACTIVE_FIELDS):
            continue

        row_unknown_or_malformed = False
        available = trace.get("retrieval_stop_active_available")

        mode_bucket, mode_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_active_mode"),
            _RETRIEVAL_STOP_ACTIVE_MODES,
        )
        fallback_reason = trace.get("retrieval_stop_active_fallback_reason")
        fallback_reason_unknown = False
        if fallback_reason is not None:
            fallback_bucket, fallback_reason_unknown = (
                _retrieval_stop_safe_bucket(
                    fallback_reason,
                    _RETRIEVAL_STOP_ACTIVE_FALLBACK_REASONS,
                )
            )
            summary["retrieval_stop_active_fallback_reason_counts"][
                fallback_bucket
            ] += 1
            summary["retrieval_stop_active_fallback_rows"] += 1

        if available is not True:
            if available is not False:
                row_unknown_or_malformed = True
            for field, allowed_keys in (
                (
                    "retrieval_stop_active_decision",
                    _RETRIEVAL_STOP_ACTIVE_DECISIONS,
                ),
                (
                    "retrieval_stop_active_reason",
                    _RETRIEVAL_STOP_ACTIVE_REASONS,
                ),
                (
                    "retrieval_stop_active_stage",
                    _RETRIEVAL_STOP_ACTIVE_STAGES,
                ),
                (
                    "retrieval_stop_active_shadow_alignment",
                    _RETRIEVAL_STOP_ACTIVE_SHADOW_ALIGNMENTS,
                ),
            ):
                if field in trace and trace.get(field) is not None:
                    _bucket, malformed = _retrieval_stop_safe_bucket(
                        trace.get(field),
                        allowed_keys,
                    )
                    if malformed:
                        row_unknown_or_malformed = True
            if (
                "retrieval_stop_active_next_query_count" in trace
                and trace.get("retrieval_stop_active_next_query_count") is not None
            ):
                _bucket, malformed = _retrieval_stop_next_query_count_bucket(
                    trace.get("retrieval_stop_active_next_query_count")
                )
                if malformed:
                    row_unknown_or_malformed = True
            if any(
                (
                    mode_unknown,
                    fallback_reason_unknown,
                    row_unknown_or_malformed,
                )
            ):
                summary["retrieval_stop_active_unknown_or_malformed_rows"] += 1
            if mode_bucket != "missing":
                summary["retrieval_stop_active_mode_counts"][mode_bucket] += 1
            continue

        summary["retrieval_stop_active_available_rows"] += 1

        decision_bucket, decision_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_active_decision"),
            _RETRIEVAL_STOP_ACTIVE_DECISIONS,
        )
        reason_bucket, reason_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_active_reason"),
            _RETRIEVAL_STOP_ACTIVE_REASONS,
        )
        stage_bucket, stage_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_active_stage"),
            _RETRIEVAL_STOP_ACTIVE_STAGES,
        )
        alignment_bucket, alignment_unknown = _retrieval_stop_safe_bucket(
            trace.get("retrieval_stop_active_shadow_alignment"),
            _RETRIEVAL_STOP_ACTIVE_SHADOW_ALIGNMENTS,
        )
        next_query_bucket, next_query_unknown = (
            _retrieval_stop_next_query_count_bucket(
                trace.get("retrieval_stop_active_next_query_count")
            )
        )

        summary["retrieval_stop_active_decision_counts"][decision_bucket] += 1
        summary["retrieval_stop_active_reason_counts"][reason_bucket] += 1
        summary["retrieval_stop_active_stage_counts"][stage_bucket] += 1
        summary["retrieval_stop_active_mode_counts"][mode_bucket] += 1
        summary["retrieval_stop_active_shadow_alignment_counts"][
            alignment_bucket
        ] += 1
        summary["retrieval_stop_active_next_query_count_buckets"][
            next_query_bucket
        ] += 1

        if any(
            (
                decision_unknown,
                reason_unknown,
                stage_unknown,
                mode_unknown,
                alignment_unknown,
                next_query_unknown,
                fallback_reason_unknown,
                row_unknown_or_malformed,
            )
        ):
            summary["retrieval_stop_active_unknown_or_malformed_rows"] += 1

    return summary


def _print_retrieval_stop_active_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_retrieval_stop_active(tail)

    print()
    print(f"=== Retrieval-stop active telemetry (last {len(tail)} runs) ===")
    print(
        "retrieval_stop_active_available_rows: "
        f"{summary['retrieval_stop_active_available_rows']}"
    )
    print(
        "retrieval_stop_active_fallback_rows: "
        f"{summary['retrieval_stop_active_fallback_rows']}"
    )
    print(
        "retrieval_stop_active_decision_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_decision_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_DECISIONS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_reason_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_reason_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_REASONS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_stage_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_stage_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_STAGES, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_mode_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_mode_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_MODES, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_shadow_alignment_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_shadow_alignment_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_SHADOW_ALIGNMENTS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_fallback_reason_counts:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_fallback_reason_counts"],
            (*_RETRIEVAL_STOP_ACTIVE_FALLBACK_REASONS, "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_next_query_count_buckets:",
        _ordered_counter_dict(
            summary["retrieval_stop_active_next_query_count_buckets"],
            ("0", "1", "2-3", "4+", "missing", "unknown"),
        ),
    )
    print(
        "retrieval_stop_active_unknown_or_malformed_rows: "
        f"{summary['retrieval_stop_active_unknown_or_malformed_rows']}"
    )


def _retrieval_budget_bool_bucket(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "missing"


def _retrieval_budget_safe_bucket(
    value: Any,
    allowed_keys: tuple[str, ...],
) -> tuple[str, bool]:
    if value is None:
        return "missing", False
    if not isinstance(value, str):
        return "unknown", True
    if value in set(allowed_keys):
        return value, False
    return "unknown", True


def _retrieval_budget_count_bucket(value: Any) -> tuple[str, bool]:
    if value is None:
        return "missing", False
    if isinstance(value, bool):
        return "unknown", True
    try:
        count = int(value)
    except (TypeError, ValueError):
        return "unknown", True
    if count < 0:
        return "unknown", True
    return _provider_overlap_count_bucket(count), False


def _retrieval_budget_query_novelty_bucket(value: Any) -> tuple[str, bool]:
    if value is None:
        return "missing", False
    if isinstance(value, bool):
        return "unknown", True
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown", True
    if number < 0 or number > 1:
        return "unknown", True
    return _provider_similarity_bucket(number), False


def _retrieval_budget_list_counts(
    target: Counter[str],
    value: Any,
    allowed_keys: tuple[str, ...],
) -> bool:
    if value is None:
        target["none"] += 1
        return False
    if not isinstance(value, list):
        target["unknown"] += 1
        return True
    if not value:
        target["none"] += 1
        return False

    malformed = False
    allowed = set(allowed_keys)
    for item in value:
        if not isinstance(item, str):
            target["unknown"] += 1
            malformed = True
            continue
        if item in allowed:
            target[item] += 1
        else:
            target["unknown"] += 1
            malformed = True
    return malformed


def _summarize_retrieval_budget_pressure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "payload_rows": 0,
        "malformed_rows": 0,
        "budget_pressure_bucket_counts": Counter(),
        "budget_stop_reason_counts": Counter(),
        "cost_availability_counts": Counter(),
        "cost_source_counts": Counter(),
        "cost_confidence_counts": Counter(),
        "last_pass_new_source_count_buckets": Counter(),
        "last_pass_new_domain_count_buckets": Counter(),
        "last_pass_new_accepted_source_count_buckets": Counter(),
        "last_pass_accepted_overlap_buckets": Counter(),
        "last_pass_provider_attempt_buckets": Counter(),
        "query_novelty_buckets": Counter(),
        "missing_source_class_counts": Counter(),
        "official_evidence_found_counts": Counter(),
        "community_signal_found_counts": Counter(),
        "quant_metric_coverage_valid_counts": Counter(),
        "extra_pass_candidate_counts": Counter(),
        "extra_pass_reason_counts": Counter(),
        "extra_pass_blocker_counts": Counter(),
        "extra_pass_query_source_counts": Counter(),
        "extra_pass_budget_class_counts": Counter(),
        "budget_limited_answer_counts": Counter(),
        "budget_limited_answer_reason_counts": Counter(),
        "unresolved_gap_buckets": Counter(),
        "answer_outcome_counts": Counter(),
    }

    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            continue
        if "retrieval_budget_pressure_shadow" not in trace:
            continue
        payload = trace.get("retrieval_budget_pressure_shadow")
        if not isinstance(payload, dict):
            summary["malformed_rows"] += 1
            continue

        summary["payload_rows"] += 1
        malformed = False
        if payload.get("schema_version") != _RETRIEVAL_BUDGET_PRESSURE_SCHEMA_VERSION:
            malformed = True
        if payload.get("shadow_mode") is not True:
            malformed = True

        hard_budget = payload.get("hard_mode_budget")
        if not isinstance(hard_budget, dict):
            hard_budget = {}
            malformed = True
        cost_state = payload.get("cost_state")
        if not isinstance(cost_state, dict):
            cost_state = {}
            malformed = True
        last_pass_yield = payload.get("last_pass_marginal_yield")
        if not isinstance(last_pass_yield, dict):
            last_pass_yield = {}
            malformed = True
        remaining_gaps = payload.get("remaining_evidence_gaps")
        if not isinstance(remaining_gaps, dict):
            remaining_gaps = {}
            malformed = True
        extra_pass = payload.get("extra_pass_judgment")
        if not isinstance(extra_pass, dict):
            extra_pass = {}
            malformed = True
        answer_quality = payload.get("answer_quality_impact")
        if not isinstance(answer_quality, dict):
            answer_quality = {}
            malformed = True

        bucket, bad = _retrieval_budget_safe_bucket(
            hard_budget.get("budget_pressure_bucket"),
            _RETRIEVAL_BUDGET_PRESSURE_BUCKETS,
        )
        summary["budget_pressure_bucket_counts"][bucket] += 1
        malformed = malformed or bad

        stop_reason, bad = _retrieval_budget_safe_bucket(
            hard_budget.get("budget_stop_reason"),
            _RETRIEVAL_BUDGET_STOP_REASONS,
        )
        summary["budget_stop_reason_counts"][stop_reason] += 1
        malformed = malformed or bad

        summary["cost_availability_counts"][
            _retrieval_budget_bool_bucket(cost_state.get("estimated_cost_available"))
        ] += 1
        cost_source, bad = _retrieval_budget_safe_bucket(
            cost_state.get("estimated_cost_source"),
            _RETRIEVAL_BUDGET_COST_SOURCES,
        )
        summary["cost_source_counts"][cost_source] += 1
        malformed = malformed or bad
        confidence, bad = _retrieval_budget_safe_bucket(
            cost_state.get("estimated_cost_confidence_bucket"),
            _RETRIEVAL_BUDGET_COST_CONFIDENCE_BUCKETS,
        )
        summary["cost_confidence_counts"][confidence] += 1
        malformed = malformed or bad

        for field, counter_name in (
            ("new_source_count_last_pass", "last_pass_new_source_count_buckets"),
            ("new_domain_count_last_pass", "last_pass_new_domain_count_buckets"),
            (
                "new_accepted_source_count_last_pass",
                "last_pass_new_accepted_source_count_buckets",
            ),
            ("accepted_overlap_last_pass", "last_pass_accepted_overlap_buckets"),
            ("provider_attempts_last_pass", "last_pass_provider_attempt_buckets"),
        ):
            count_bucket, bad = _retrieval_budget_count_bucket(
                last_pass_yield.get(field)
            )
            summary[counter_name][count_bucket] += 1
            malformed = malformed or bad
        novelty_bucket, bad = _retrieval_budget_query_novelty_bucket(
            last_pass_yield.get("query_novelty_score")
        )
        summary["query_novelty_buckets"][novelty_bucket] += 1
        malformed = malformed or bad

        malformed = (
            _retrieval_budget_list_counts(
                summary["missing_source_class_counts"],
                remaining_gaps.get("missing_expected_source_classes"),
                _RETRIEVAL_BUDGET_SOURCE_CLASS_BUCKETS,
            )
            or malformed
        )
        summary["official_evidence_found_counts"][
            _retrieval_budget_bool_bucket(remaining_gaps.get("official_evidence_found"))
        ] += 1
        summary["community_signal_found_counts"][
            _retrieval_budget_bool_bucket(remaining_gaps.get("community_signal_found"))
        ] += 1
        summary["quant_metric_coverage_valid_counts"][
            _retrieval_budget_bool_bucket(
                remaining_gaps.get("quant_metric_coverage_valid")
            )
        ] += 1

        summary["extra_pass_candidate_counts"][
            _retrieval_budget_bool_bucket(extra_pass.get("extra_pass_candidate_shadow"))
        ] += 1
        malformed = (
            _retrieval_budget_list_counts(
                summary["extra_pass_reason_counts"],
                extra_pass.get("extra_pass_candidate_reasons"),
                _RETRIEVAL_BUDGET_EXTRA_PASS_REASONS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["extra_pass_blocker_counts"],
                extra_pass.get("extra_pass_candidate_blockers"),
                _RETRIEVAL_BUDGET_EXTRA_PASS_BLOCKERS,
            )
            or malformed
        )
        query_source, bad = _retrieval_budget_safe_bucket(
            extra_pass.get("extra_pass_candidate_query_source"),
            _RETRIEVAL_BUDGET_QUERY_SOURCES,
        )
        summary["extra_pass_query_source_counts"][query_source] += 1
        malformed = malformed or bad
        budget_class, bad = _retrieval_budget_safe_bucket(
            extra_pass.get("extra_pass_budget_class"),
            _RETRIEVAL_BUDGET_PRESSURE_BUCKETS,
        )
        summary["extra_pass_budget_class_counts"][budget_class] += 1
        malformed = malformed or bad

        summary["budget_limited_answer_counts"][
            _retrieval_budget_bool_bucket(
                answer_quality.get("budget_limited_answer_shadow")
            )
        ] += 1
        limited_reason, bad = _retrieval_budget_safe_bucket(
            answer_quality.get("budget_limited_answer_reason"),
            _RETRIEVAL_BUDGET_LIMITED_ANSWER_REASONS,
        )
        summary["budget_limited_answer_reason_counts"][limited_reason] += 1
        malformed = malformed or bad
        gap_bucket, bad = _retrieval_budget_count_bucket(
            answer_quality.get("unresolved_gap_count_at_synthesis")
        )
        summary["unresolved_gap_buckets"][gap_bucket] += 1
        malformed = malformed or bad
        answer_outcome = answer_quality.get("answer_outcome")
        if answer_outcome is not None:
            outcome_bucket, bad = _retrieval_budget_safe_bucket(
                answer_outcome,
                _RETRIEVAL_BUDGET_ANSWER_OUTCOMES,
            )
            summary["answer_outcome_counts"][outcome_bucket] += 1
            malformed = malformed or bad

        if malformed:
            summary["malformed_rows"] += 1

    return summary


def _print_retrieval_budget_pressure_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_retrieval_budget_pressure(tail)

    print()
    print(f"=== Retrieval budget pressure shadow (last {len(tail)} runs) ===")
    print(
        "retrieval_budget_pressure_payload_rows: "
        f"{summary['payload_rows']}"
    )
    print(
        "retrieval_budget_pressure_malformed_rows: "
        f"{summary['malformed_rows']}"
    )
    print(
        "budget_pressure_bucket_counts:",
        _ordered_counter_dict(
            summary["budget_pressure_bucket_counts"],
            (*_RETRIEVAL_BUDGET_PRESSURE_BUCKETS, "missing", "unknown"),
        ),
    )
    print(
        "budget_stop_reason_counts:",
        _ordered_counter_dict(
            summary["budget_stop_reason_counts"],
            (*_RETRIEVAL_BUDGET_STOP_REASONS, "missing", "unknown"),
        ),
    )
    print(
        "cost_availability_counts:",
        _ordered_counter_dict(
            summary["cost_availability_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "cost_source_counts:",
        _ordered_counter_dict(
            summary["cost_source_counts"],
            (*_RETRIEVAL_BUDGET_COST_SOURCES, "missing", "unknown"),
        ),
    )
    print(
        "cost_confidence_counts:",
        _ordered_counter_dict(
            summary["cost_confidence_counts"],
            (*_RETRIEVAL_BUDGET_COST_CONFIDENCE_BUCKETS, "missing", "unknown"),
        ),
    )
    print(
        "last_pass_new_source_count_buckets:",
        _ordered_counter_dict(summary["last_pass_new_source_count_buckets"]),
    )
    print(
        "last_pass_new_domain_count_buckets:",
        _ordered_counter_dict(summary["last_pass_new_domain_count_buckets"]),
    )
    print(
        "last_pass_new_accepted_source_count_buckets:",
        _ordered_counter_dict(
            summary["last_pass_new_accepted_source_count_buckets"]
        ),
    )
    print(
        "last_pass_accepted_overlap_buckets:",
        _ordered_counter_dict(summary["last_pass_accepted_overlap_buckets"]),
    )
    print(
        "last_pass_provider_attempt_buckets:",
        _ordered_counter_dict(summary["last_pass_provider_attempt_buckets"]),
    )
    print(
        "query_novelty_buckets:",
        _ordered_counter_dict(
            summary["query_novelty_buckets"],
            ("0", "0.01-0.25", "0.26-0.50", "0.51-0.75", "0.76-1.00", "missing", "unknown"),
        ),
    )
    print(
        "missing_source_class_counts:",
        _ordered_counter_dict(
            summary["missing_source_class_counts"],
            (*_RETRIEVAL_BUDGET_SOURCE_CLASS_BUCKETS, "unknown"),
        ),
    )
    print(
        "official_evidence_found_counts:",
        _ordered_counter_dict(
            summary["official_evidence_found_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "community_signal_found_counts:",
        _ordered_counter_dict(
            summary["community_signal_found_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "quant_metric_coverage_valid_counts:",
        _ordered_counter_dict(
            summary["quant_metric_coverage_valid_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "extra_pass_candidate_counts:",
        _ordered_counter_dict(
            summary["extra_pass_candidate_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "extra_pass_reason_counts:",
        _ordered_counter_dict(
            summary["extra_pass_reason_counts"],
            (*_RETRIEVAL_BUDGET_EXTRA_PASS_REASONS, "none", "unknown"),
        ),
    )
    print(
        "extra_pass_blocker_counts:",
        _ordered_counter_dict(
            summary["extra_pass_blocker_counts"],
            (*_RETRIEVAL_BUDGET_EXTRA_PASS_BLOCKERS, "none", "unknown"),
        ),
    )
    print(
        "extra_pass_query_source_counts:",
        _ordered_counter_dict(
            summary["extra_pass_query_source_counts"],
            (*_RETRIEVAL_BUDGET_QUERY_SOURCES, "missing", "unknown"),
        ),
    )
    print(
        "extra_pass_budget_class_counts:",
        _ordered_counter_dict(
            summary["extra_pass_budget_class_counts"],
            (*_RETRIEVAL_BUDGET_PRESSURE_BUCKETS, "missing", "unknown"),
        ),
    )
    print(
        "budget_limited_answer_counts:",
        _ordered_counter_dict(
            summary["budget_limited_answer_counts"],
            ("true", "false", "missing"),
        ),
    )
    print(
        "budget_limited_answer_reason_counts:",
        _ordered_counter_dict(
            summary["budget_limited_answer_reason_counts"],
            (*_RETRIEVAL_BUDGET_LIMITED_ANSWER_REASONS, "missing", "unknown"),
        ),
    )
    print(
        "unresolved_gap_buckets:",
        _ordered_counter_dict(summary["unresolved_gap_buckets"]),
    )
    print(
        "answer_outcome_counts:",
        _ordered_counter_dict(
            summary["answer_outcome_counts"],
            (*_RETRIEVAL_BUDGET_ANSWER_OUTCOMES, "unknown"),
        ),
    )


def _source_class_observability_bool_bucket(value: Any) -> tuple[str, bool]:
    if value is True:
        return "true", False
    if value is False:
        return "false", False
    if value is None:
        return "missing", False
    return "unknown", True


def _source_class_observability_present(trace: dict[str, Any]) -> bool:
    return any(field in trace for field in _SOURCE_CLASS_OBSERVABILITY_FIELDS)


def _source_class_observability_count_map(
    target: Counter[str],
    value: Any,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        target["unknown"] += 1
        return True

    malformed = False
    allowed = set(_SOURCE_CLASS_OBSERVABILITY_BUCKETS)
    for raw_key, raw_count in value.items():
        if isinstance(raw_count, bool):
            count = 0
            malformed = True
        else:
            try:
                count = max(0, int(raw_count or 0))
            except (TypeError, ValueError):
                count = 0
                malformed = True
        key = str(raw_key)
        if key in allowed and key != "none":
            if count > 0:
                target[key] += count
        else:
            malformed = True
            if count > 0:
                target["unknown"] += count
    return malformed


def _source_class_observability_status_map(
    target: Counter[str],
    value: Any,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        target["unknown"] += 1
        return True

    malformed = False
    allowed_buckets = set(_SOURCE_CLASS_OBSERVABILITY_BUCKETS)
    allowed_statuses = set(_SOURCE_CLASS_SATISFACTION_STATUSES)
    for raw_key, raw_status in value.items():
        key = str(raw_key)
        status = str(raw_status)
        if key not in allowed_buckets or key == "none":
            malformed = True
            target["unknown"] += 1
            continue
        if status in allowed_statuses:
            target[status] += 1
        else:
            malformed = True
            target["unknown"] += 1
    return malformed


def _source_class_observability_strength_count_map(
    target: Counter[str],
    value: Any,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        target["unknown"] += 1
        return True

    malformed = False
    allowed = set(_SOURCE_CLASS_SATISFACTION_STATUSES)
    for raw_key, raw_count in value.items():
        if isinstance(raw_count, bool):
            count = 0
            malformed = True
        else:
            try:
                count = max(0, int(raw_count or 0))
            except (TypeError, ValueError):
                count = 0
                malformed = True
        key = str(raw_key)
        if key in allowed:
            if count > 0:
                target[key] += count
        else:
            malformed = True
            if count > 0:
                target["unknown"] += count
    return malformed


def _summarize_source_class_observability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "payload_rows": 0,
        "malformed_rows": 0,
        "underfire_shadow_counts": Counter(),
        "expected_source_class_counts": Counter(),
        "gap_candidate_counts": Counter(),
        "underfire_reason_counts": Counter(),
        "underfire_blocker_counts": Counter(),
        "final_official_source_count_buckets": Counter(),
        "final_primary_source_count_buckets": Counter(),
        "final_archival_source_count_buckets": Counter(),
        "final_legal_or_regulatory_source_count_buckets": Counter(),
        "satisfaction_count_totals": Counter(),
        "satisfaction_status_counts": Counter(),
        "satisfaction_strength_count_totals": Counter(),
        "strong_satisfaction_count_totals": Counter(),
        "weak_satisfaction_count_totals": Counter(),
        "secondary_only_count_totals": Counter(),
    }

    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            continue
        if not _source_class_observability_present(trace):
            continue

        summary["payload_rows"] += 1
        malformed = False

        underfire_bucket, bad = _source_class_observability_bool_bucket(
            trace.get("source_class_underfire_shadow")
        )
        summary["underfire_shadow_counts"][underfire_bucket] += 1
        malformed = malformed or bad

        malformed = (
            _retrieval_budget_list_counts(
                summary["expected_source_class_counts"],
                trace.get("expected_source_classes_raw"),
                _SOURCE_CLASS_OBSERVABILITY_BUCKETS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["gap_candidate_counts"],
                trace.get("source_class_gap_candidates"),
                _SOURCE_CLASS_OBSERVABILITY_BUCKETS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["underfire_reason_counts"],
                trace.get("source_class_underfire_reasons"),
                _SOURCE_CLASS_UNDERFIRE_REASONS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["underfire_blocker_counts"],
                trace.get("source_class_underfire_blockers"),
                _SOURCE_CLASS_UNDERFIRE_BLOCKERS,
            )
            or malformed
        )

        for field, counter_name in (
            ("final_official_source_count", "final_official_source_count_buckets"),
            ("final_primary_source_count", "final_primary_source_count_buckets"),
            ("final_archival_source_count", "final_archival_source_count_buckets"),
            (
                "final_legal_or_regulatory_source_count",
                "final_legal_or_regulatory_source_count_buckets",
            ),
        ):
            count_bucket, bad = _retrieval_budget_count_bucket(trace.get(field))
            summary[counter_name][count_bucket] += 1
            malformed = malformed or bad

        malformed = (
            _source_class_observability_count_map(
                summary["satisfaction_count_totals"],
                trace.get("source_class_satisfaction_counts"),
            )
            or malformed
        )
        malformed = (
            _source_class_observability_status_map(
                summary["satisfaction_status_counts"],
                trace.get("source_class_satisfaction_status"),
            )
            or malformed
        )
        malformed = (
            _source_class_observability_strength_count_map(
                summary["satisfaction_strength_count_totals"],
                trace.get("source_class_satisfaction_strength_counts"),
            )
            or malformed
        )
        for field, counter_name in (
            (
                "source_class_strong_satisfaction_counts",
                "strong_satisfaction_count_totals",
            ),
            (
                "source_class_weak_satisfaction_counts",
                "weak_satisfaction_count_totals",
            ),
            (
                "source_class_secondary_only_counts",
                "secondary_only_count_totals",
            ),
        ):
            malformed = (
                _source_class_observability_count_map(
                    summary[counter_name],
                    trace.get(field),
                )
                or malformed
            )

        if malformed:
            summary["malformed_rows"] += 1

    return summary


def _print_source_class_observability_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_source_class_observability(tail)

    print()
    print(f"=== Source-class observability (last {len(tail)} runs) ===")
    print(f"source_class_observability_payload_rows: {summary['payload_rows']}")
    print(f"source_class_observability_malformed_rows: {summary['malformed_rows']}")
    print(
        "source_class_underfire_shadow_counts:",
        _ordered_counter_dict(
            summary["underfire_shadow_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "expected_source_class_counts:",
        _ordered_counter_dict(
            summary["expected_source_class_counts"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_gap_candidate_counts:",
        _ordered_counter_dict(
            summary["gap_candidate_counts"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_underfire_reason_counts:",
        _ordered_counter_dict(
            summary["underfire_reason_counts"],
            (*_SOURCE_CLASS_UNDERFIRE_REASONS, "none", "unknown"),
        ),
    )
    print(
        "source_class_underfire_blocker_counts:",
        _ordered_counter_dict(
            summary["underfire_blocker_counts"],
            (*_SOURCE_CLASS_UNDERFIRE_BLOCKERS, "none", "unknown"),
        ),
    )
    print(
        "final_official_source_count_buckets:",
        _ordered_counter_dict(summary["final_official_source_count_buckets"]),
    )
    print(
        "final_primary_source_count_buckets:",
        _ordered_counter_dict(summary["final_primary_source_count_buckets"]),
    )
    print(
        "final_archival_source_count_buckets:",
        _ordered_counter_dict(summary["final_archival_source_count_buckets"]),
    )
    print(
        "final_legal_or_regulatory_source_count_buckets:",
        _ordered_counter_dict(
            summary["final_legal_or_regulatory_source_count_buckets"]
        ),
    )
    print(
        "source_class_satisfaction_count_totals:",
        _ordered_counter_dict(
            summary["satisfaction_count_totals"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_satisfaction_status_counts:",
        _ordered_counter_dict(
            summary["satisfaction_status_counts"],
            (*_SOURCE_CLASS_SATISFACTION_STATUSES, "unknown"),
        ),
    )
    print(
        "source_class_satisfaction_strength_count_totals:",
        _ordered_counter_dict(
            summary["satisfaction_strength_count_totals"],
            (*_SOURCE_CLASS_SATISFACTION_STATUSES, "unknown"),
        ),
    )
    print(
        "source_class_strong_satisfaction_count_totals:",
        _ordered_counter_dict(
            summary["strong_satisfaction_count_totals"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_weak_satisfaction_count_totals:",
        _ordered_counter_dict(
            summary["weak_satisfaction_count_totals"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_secondary_only_count_totals:",
        _ordered_counter_dict(
            summary["secondary_only_count_totals"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )


def _source_class_candidate_v2_status_by_class_map(
    target: Counter[str],
    value: Any,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        target["unknown"] += 1
        return True

    malformed = False
    allowed_buckets = set(_SOURCE_CLASS_OBSERVABILITY_BUCKETS)
    allowed_statuses = set(_SOURCE_CLASS_SATISFACTION_STATUSES)
    for raw_key, raw_status in value.items():
        key = str(raw_key)
        status = str(raw_status)
        if key not in allowed_buckets or key == "none":
            malformed = True
            target["unknown"] += 1
            continue
        if status in allowed_statuses:
            target[f"{key}:{status}"] += 1
        else:
            malformed = True
            target["unknown"] += 1
    return malformed


def _summarize_source_class_candidate_v2(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "payload_rows": 0,
        "malformed_rows": 0,
        "candidate_counts": Counter(),
        "candidate_class_counts": Counter(),
        "reason_counts": Counter(),
        "blocker_counts": Counter(),
        "status_by_class_counts": Counter(),
        "query_count_buckets": Counter(),
        "query_source_counts": Counter(),
        "budget_context_counts": Counter(),
        "weak_corpus_blocker_counts": Counter(),
        "budget_blocker_counts": Counter(),
        "answer_class_counts_for_candidate_rows": Counter(),
    }

    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            continue
        if "source_class_recovery_candidate_v2" not in trace:
            continue
        payload = trace.get("source_class_recovery_candidate_v2")
        if not isinstance(payload, dict):
            summary["malformed_rows"] += 1
            continue

        summary["payload_rows"] += 1
        malformed = False
        if (
            payload.get("schema_version")
            != _SOURCE_CLASS_RECOVERY_CANDIDATE_V2_SCHEMA_VERSION
        ):
            malformed = True
        if payload.get("shadow_mode") is not True:
            malformed = True

        candidate_bucket, bad = _source_class_observability_bool_bucket(
            payload.get("source_class_recovery_candidate_v2_shadow")
        )
        summary["candidate_counts"][candidate_bucket] += 1
        malformed = malformed or bad

        malformed = (
            _retrieval_budget_list_counts(
                summary["candidate_class_counts"],
                payload.get("source_class_recovery_candidate_v2_classes"),
                _SOURCE_CLASS_OBSERVABILITY_BUCKETS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["reason_counts"],
                payload.get("source_class_recovery_candidate_v2_reasons"),
                _SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )
            or malformed
        )
        malformed = (
            _retrieval_budget_list_counts(
                summary["blocker_counts"],
                payload.get("source_class_recovery_candidate_v2_blockers"),
                _SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
            )
            or malformed
        )
        malformed = (
            _source_class_candidate_v2_status_by_class_map(
                summary["status_by_class_counts"],
                payload.get("source_class_recovery_candidate_v2_status_by_class"),
            )
            or malformed
        )

        query_bucket, bad = _retrieval_budget_count_bucket(
            payload.get("source_class_recovery_candidate_v2_query_count")
        )
        summary["query_count_buckets"][query_bucket] += 1
        malformed = malformed or bad

        query_source, bad = _retrieval_budget_safe_bucket(
            payload.get("source_class_recovery_candidate_v2_query_source"),
            _SOURCE_CLASS_RECOVERY_CANDIDATE_V2_QUERY_SOURCES,
        )
        summary["query_source_counts"][query_source] += 1
        malformed = malformed or bad

        budget_context, bad = _retrieval_budget_safe_bucket(
            payload.get("source_class_recovery_candidate_v2_budget_context"),
            _RETRIEVAL_BUDGET_PRESSURE_BUCKETS,
        )
        summary["budget_context_counts"][budget_context] += 1
        malformed = malformed or bad

        weak_bucket, bad = _source_class_observability_bool_bucket(
            payload.get(
                "source_class_recovery_candidate_v2_blocked_by_weak_corpus"
            )
        )
        summary["weak_corpus_blocker_counts"][weak_bucket] += 1
        malformed = malformed or bad

        budget_bucket, bad = _source_class_observability_bool_bucket(
            payload.get("source_class_recovery_candidate_v2_blocked_by_budget")
        )
        summary["budget_blocker_counts"][budget_bucket] += 1
        malformed = malformed or bad

        if payload.get("source_class_recovery_candidate_v2_shadow") is True:
            answer_class, bad = _retrieval_budget_safe_bucket(
                trace.get("answer_class"),
                _RETRIEVAL_BUDGET_ANSWER_OUTCOMES,
            )
            summary["answer_class_counts_for_candidate_rows"][answer_class] += 1
            malformed = malformed or bad

        if malformed:
            summary["malformed_rows"] += 1

    return summary


def _print_source_class_candidate_v2_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_source_class_candidate_v2(tail)

    print()
    print(f"=== Source-class recovery candidate v2 (last {len(tail)} runs) ===")
    print(
        "source_class_recovery_candidate_v2_payload_rows: "
        f"{summary['payload_rows']}"
    )
    print(
        "source_class_recovery_candidate_v2_malformed_rows: "
        f"{summary['malformed_rows']}"
    )
    print(
        "source_class_recovery_candidate_v2_counts:",
        _ordered_counter_dict(
            summary["candidate_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_class_counts:",
        _ordered_counter_dict(
            summary["candidate_class_counts"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_reason_counts:",
        _ordered_counter_dict(
            summary["reason_counts"],
            (*_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS, "none", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_blocker_counts:",
        _ordered_counter_dict(
            summary["blocker_counts"],
            (*_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS, "none", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_status_by_class_counts:",
        _ordered_counter_dict(summary["status_by_class_counts"]),
    )
    print(
        "source_class_recovery_candidate_v2_query_count_buckets:",
        _ordered_counter_dict(summary["query_count_buckets"]),
    )
    print(
        "source_class_recovery_candidate_v2_query_source_counts:",
        _ordered_counter_dict(
            summary["query_source_counts"],
            (*_SOURCE_CLASS_RECOVERY_CANDIDATE_V2_QUERY_SOURCES, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_budget_context_counts:",
        _ordered_counter_dict(
            summary["budget_context_counts"],
            (*_RETRIEVAL_BUDGET_PRESSURE_BUCKETS, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_weak_corpus_blocker_counts:",
        _ordered_counter_dict(
            summary["weak_corpus_blocker_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_budget_blocker_counts:",
        _ordered_counter_dict(
            summary["budget_blocker_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_candidate_v2_answer_class_counts_for_candidate_rows:",
        _ordered_counter_dict(
            summary["answer_class_counts_for_candidate_rows"],
            (*_RETRIEVAL_BUDGET_ANSWER_OUTCOMES, "missing", "unknown"),
        ),
    )


def _source_class_recovery_validation_packet(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    packet = row.get(SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY)
    if isinstance(packet, dict):
        return packet
    trace = row.get("execution_trace")
    if isinstance(trace, dict):
        packet = trace.get(SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY)
        if isinstance(packet, dict):
            return packet
    return None


def _source_class_recovery_validation_count_map(
    target: Counter[str],
    value: Any,
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        target["unknown"] += 1
        return True
    malformed = False
    for raw_key, raw_count in value.items():
        key = str(raw_key)
        count = _controller_count(raw_count)
        if key in set(_SOURCE_CLASS_OBSERVABILITY_BUCKETS) or key in {
            "current_primary_or_official_proxy",
        }:
            if count > 0:
                target[key] += count
        else:
            malformed = True
            if count > 0:
                target["unknown"] += count
    return malformed


def _summarize_source_class_recovery_validation(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "payload_rows": 0,
        "malformed_rows": 0,
        "action_status_counts": Counter(),
        "bottleneck_status_counts": Counter(),
        "considered_counts": Counter(),
        "recommended_counts": Counter(),
        "eligible_counts": Counter(),
        "used_counts": Counter(),
        "missing_source_class_counts": Counter(),
        "query_count_buckets": Counter(),
        "domain_constraint_rows": 0,
        "jurisdiction_counts": Counter(),
        "provider_attempt_count_buckets": Counter(),
        "provider_counts": Counter(),
        "provider_depth_counts": Counter(),
        "provider_max_results_buckets": Counter(),
        "accepted_url_count_buckets": Counter(),
        "recovered_quality_status_counts": Counter(),
        "visibility_used_counts": Counter(),
        "visibility_reason_counts": Counter(),
        "evidence_bundle_source_class_counts": Counter(),
        "final_cited_available_counts": Counter(),
        "final_cited_source_class_counts": Counter(),
    }

    for row in rows:
        packet = _source_class_recovery_validation_packet(row)
        if packet is None:
            continue
        summary["payload_rows"] += 1
        malformed = False
        if (
            packet.get("schema_version")
            != SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION
        ):
            malformed = True
        if packet.get("diagnostic_only") is not True:
            malformed = True
        if packet.get("sanitized") is not True:
            malformed = True

        action = packet.get("ag25_action")
        if isinstance(action, dict):
            action_status, bad = _retrieval_budget_safe_bucket(
                action.get("status"),
                _SOURCE_CLASS_RECOVERY_VALIDATION_ACTION_STATUSES,
            )
        else:
            action_status, bad = "unknown", True
        summary["action_status_counts"][action_status] += 1
        malformed = malformed or bad

        bottleneck, bad = _retrieval_budget_safe_bucket(
            packet.get("recovery_bottleneck_status"),
            SOURCE_CLASS_RECOVERY_BOTTLENECK_STATUSES,
        )
        summary["bottleneck_status_counts"][bottleneck] += 1
        malformed = malformed or bad

        for field, counter_name in (
            ("recovery_considered", "considered_counts"),
            ("recovery_recommended", "recommended_counts"),
            ("recovery_eligible", "eligible_counts"),
            ("recovery_used", "used_counts"),
            ("final_cited_counts_available", "final_cited_available_counts"),
        ):
            bucket, bad = _source_class_observability_bool_bucket(packet.get(field))
            summary[counter_name][bucket] += 1
            malformed = malformed or bad

        malformed = (
            _retrieval_budget_list_counts(
                summary["missing_source_class_counts"],
                packet.get("missing_source_classes"),
                _SOURCE_CLASS_OBSERVABILITY_BUCKETS,
            )
            or malformed
        )

        queries = packet.get("recovery_query_previews")
        if isinstance(queries, list):
            summary["query_count_buckets"][_query_count_bucket(len(queries))] += 1
        else:
            summary["query_count_buckets"]["unknown"] += 1
            malformed = True

        domains = packet.get("official_domain_constraints")
        if isinstance(domains, list):
            if domains:
                summary["domain_constraint_rows"] += 1
        elif domains is not None:
            malformed = True

        jurisdictions = packet.get("jurisdiction_constraints")
        if isinstance(jurisdictions, list):
            if not jurisdictions:
                summary["jurisdiction_counts"]["none"] += 1
            for jurisdiction in jurisdictions:
                summary["jurisdiction_counts"][str(jurisdiction)] += 1
        else:
            summary["jurisdiction_counts"]["unknown"] += 1
            malformed = True

        provider_attempts = packet.get("provider_attempts")
        if isinstance(provider_attempts, list):
            summary["provider_attempt_count_buckets"][
                _provider_overlap_count_bucket(len(provider_attempts))
            ] += 1
            for attempt in provider_attempts:
                if not isinstance(attempt, dict):
                    malformed = True
                    continue
                summary["provider_counts"][
                    str(attempt.get("provider") or "unknown")
                ] += 1
                summary["provider_depth_counts"][
                    str(attempt.get("depth") or "missing")
                ] += 1
                summary["provider_max_results_buckets"][
                    _provider_overlap_count_bucket(attempt.get("max_results"))
                ] += 1
        else:
            summary["provider_attempt_count_buckets"]["unknown"] += 1
            malformed = True

        count_bucket, bad = _retrieval_budget_count_bucket(
            packet.get("accepted_url_count")
        )
        summary["accepted_url_count_buckets"][count_bucket] += 1
        malformed = malformed or bad

        quality_status, bad = _retrieval_budget_safe_bucket(
            packet.get("recovery_source_quality_status"),
            _SOURCE_CLASS_RECOVERY_VALIDATION_QUALITY_STATUSES,
        )
        summary["recovered_quality_status_counts"][quality_status] += 1
        malformed = malformed or bad

        visibility = packet.get("recovered_visibility_decision")
        if isinstance(visibility, dict):
            visible_bucket, bad = _source_class_observability_bool_bucket(
                visibility.get("used")
            )
            summary["visibility_used_counts"][visible_bucket] += 1
            summary["visibility_reason_counts"][
                str(visibility.get("reason") or "missing")
            ] += 1
            malformed = malformed or bad
        else:
            summary["visibility_used_counts"]["unknown"] += 1
            malformed = True

        malformed = (
            _source_class_recovery_validation_count_map(
                summary["evidence_bundle_source_class_counts"],
                packet.get("evidence_bundle_official_legal_current_primary_counts"),
            )
            or malformed
        )
        malformed = (
            _source_class_recovery_validation_count_map(
                summary["final_cited_source_class_counts"],
                packet.get("final_cited_official_legal_current_primary_counts"),
            )
            or malformed
        )
        if malformed:
            summary["malformed_rows"] += 1

    return summary


def _print_source_class_recovery_validation_summary(
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_source_class_recovery_validation(tail)
    if summary["payload_rows"] <= 0:
        return

    print()
    print(f"=== L1 source-class recovery validation (last {len(tail)} runs) ===")
    print(
        "source_class_recovery_validation_l1_payload_rows: "
        f"{summary['payload_rows']}"
    )
    print(
        "source_class_recovery_validation_l1_malformed_rows: "
        f"{summary['malformed_rows']}"
    )
    print(
        "source_class_recovery_validation_l1_action_status_counts:",
        _ordered_counter_dict(
            summary["action_status_counts"],
            (*_SOURCE_CLASS_RECOVERY_VALIDATION_ACTION_STATUSES, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_validation_l1_bottleneck_status_counts:",
        _ordered_counter_dict(
            summary["bottleneck_status_counts"],
            (*SOURCE_CLASS_RECOVERY_BOTTLENECK_STATUSES, "missing", "unknown"),
        ),
    )
    for label, counter_name in (
        ("considered", "considered_counts"),
        ("recommended", "recommended_counts"),
        ("eligible", "eligible_counts"),
        ("used", "used_counts"),
    ):
        print(
            f"source_class_recovery_validation_l1_{label}_counts:",
            _ordered_counter_dict(
                summary[counter_name],
                ("true", "false", "missing", "unknown"),
            ),
        )
    print(
        "source_class_recovery_validation_l1_missing_source_class_counts:",
        _ordered_counter_dict(
            summary["missing_source_class_counts"],
            (*_SOURCE_CLASS_OBSERVABILITY_BUCKETS, "none", "unknown"),
        ),
    )
    print(
        "source_class_recovery_validation_l1_query_count_buckets:",
        _ordered_counter_dict(summary["query_count_buckets"]),
    )
    print(
        "source_class_recovery_validation_l1_domain_constraint_rows: "
        f"{summary['domain_constraint_rows']}"
    )
    print(
        "source_class_recovery_validation_l1_jurisdiction_counts:",
        _ordered_counter_dict(summary["jurisdiction_counts"]),
    )
    print(
        "source_class_recovery_validation_l1_provider_attempt_count_buckets:",
        _ordered_counter_dict(summary["provider_attempt_count_buckets"]),
    )
    print(
        "source_class_recovery_validation_l1_provider_counts:",
        _ordered_counter_dict(summary["provider_counts"]),
    )
    print(
        "source_class_recovery_validation_l1_provider_depth_counts:",
        _ordered_counter_dict(summary["provider_depth_counts"]),
    )
    print(
        "source_class_recovery_validation_l1_provider_max_results_buckets:",
        _ordered_counter_dict(summary["provider_max_results_buckets"]),
    )
    print(
        "source_class_recovery_validation_l1_accepted_url_count_buckets:",
        _ordered_counter_dict(summary["accepted_url_count_buckets"]),
    )
    print(
        "source_class_recovery_validation_l1_recovered_quality_status_counts:",
        _ordered_counter_dict(
            summary["recovered_quality_status_counts"],
            (*_SOURCE_CLASS_RECOVERY_VALIDATION_QUALITY_STATUSES, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_validation_l1_visibility_used_counts:",
        _ordered_counter_dict(
            summary["visibility_used_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_validation_l1_visibility_reason_counts:",
        _ordered_counter_dict(summary["visibility_reason_counts"]),
    )
    print(
        "source_class_recovery_validation_l1_evidence_bundle_source_class_counts:",
        _ordered_counter_dict(summary["evidence_bundle_source_class_counts"]),
    )
    print(
        "source_class_recovery_validation_l1_final_cited_available_counts:",
        _ordered_counter_dict(
            summary["final_cited_available_counts"],
            ("true", "false", "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_validation_l1_final_cited_source_class_counts:",
        _ordered_counter_dict(summary["final_cited_source_class_counts"]),
    )


def _summarize_controller_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "execution_rows": len(rows),
        "payload_rows": 0,
        "legacy_missing_rows": 0,
        "omitted_rows": 0,
        "malformed_payload_rows": 0,
        "missing_legacy_or_omitted": 0,
        "omission_reason_counts": Counter(),
        "schema_version": Counter(),
        "passive_only": Counter(),
        "diagnostic_only": Counter(),
        "authority": Counter(),
        "source": Counter(),
        "run_plan_stage_count_buckets": Counter(),
        "run_plan_disposition_counts": Counter(),
        "task_ledger_record_count_buckets": Counter(),
        "task_ledger_status_counts": Counter(),
        "planned_vs_observed_status_counts": Counter(),
        "planned_vs_observed_failure_count_buckets": Counter(),
        "observed_stage_count_buckets": Counter(),
        "observed_status_counts": Counter(),
        "source_class_recovery_payload_rows": 0,
        "source_class_recovery_stage_present_rows": 0,
        "source_class_recovery_not_observed_rows": 0,
        "source_class_recovery_observed_blocked_rows": 0,
        "source_class_recovery_observed_completed_rows": 0,
        "source_class_recovery_active_used_rows": 0,
        "source_class_recovery_unknown_or_malformed_status_rows": 0,
        "source_class_recovery_stage_status_counts": Counter(),
        "source_class_recovery_observed_status_counts": Counter(),
        "source_class_recovery_disposition_counts": Counter(),
        "anomalies": Counter(),
    }

    anomalies: Counter[str] = summary["anomalies"]
    for row in rows:
        trace = row.get("execution_trace")
        if not isinstance(trace, dict):
            summary["legacy_missing_rows"] += 1
            summary["missing_legacy_or_omitted"] += 1
            continue
        payload = trace.get("controller_diagnostics")
        if not isinstance(payload, dict):
            if "controller_diagnostics" in trace and payload is not None:
                summary["malformed_payload_rows"] += 1
                anomalies["controller_diagnostics_payload_not_mapping"] += 1
            else:
                omission_bucket = _controller_diagnostics_omission_reason_bucket(trace)
                if omission_bucket is None:
                    summary["legacy_missing_rows"] += 1
                else:
                    summary["omitted_rows"] += 1
                    summary["omission_reason_counts"][omission_bucket] += 1
            summary["missing_legacy_or_omitted"] += 1
            continue

        summary["payload_rows"] += 1

        schema_bucket = _controller_expected_bucket(
            payload.get("schema_version"),
            _CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION,
        )
        summary["schema_version"][schema_bucket] += 1
        if schema_bucket != _CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION:
            anomalies["schema_version_unexpected_or_missing"] += 1

        passive_bucket = _controller_true_bucket(payload.get("passive_only"))
        summary["passive_only"][passive_bucket] += 1
        if passive_bucket != "true":
            anomalies["passive_only_not_true"] += 1

        diagnostic_bucket = _controller_true_bucket(payload.get("diagnostic_only"))
        summary["diagnostic_only"][diagnostic_bucket] += 1
        if diagnostic_bucket != "true":
            anomalies["diagnostic_only_not_true"] += 1

        authority_bucket = _controller_expected_bucket(payload.get("authority"), "none")
        summary["authority"][authority_bucket] += 1
        if authority_bucket != "none":
            anomalies["authority_not_none"] += 1

        source_bucket = _controller_expected_bucket(
            payload.get("source"),
            _CONTROLLER_DIAGNOSTICS_SOURCE,
        )
        summary["source"][source_bucket] += 1
        if source_bucket != _CONTROLLER_DIAGNOSTICS_SOURCE:
            anomalies["source_unexpected_or_missing"] += 1

        run_plan = payload.get("run_plan")
        if isinstance(run_plan, dict):
            summary["run_plan_stage_count_buckets"][
                _controller_count_bucket(run_plan.get("stage_count"))
            ] += 1
            _add_known_controller_counts(
                summary["run_plan_disposition_counts"],
                run_plan.get("disposition_counts"),
                _CONTROLLER_PLAN_DISPOSITIONS,
                anomalies,
                "run_plan_disposition_counts",
            )
        elif run_plan is not None:
            anomalies["run_plan_not_mapping"] += 1

        task_ledger = payload.get("task_ledger")
        if isinstance(task_ledger, dict):
            summary["task_ledger_record_count_buckets"][
                _controller_count_bucket(task_ledger.get("record_count"))
            ] += 1
            _add_known_controller_counts(
                summary["task_ledger_status_counts"],
                task_ledger.get("status_counts"),
                _CONTROLLER_TASK_STATUSES,
                anomalies,
                "task_ledger_status_counts",
            )
        elif task_ledger is not None:
            anomalies["task_ledger_not_mapping"] += 1

        planned_vs_observed = payload.get("planned_vs_observed")
        if isinstance(planned_vs_observed, dict):
            _add_known_controller_counts(
                summary["planned_vs_observed_status_counts"],
                planned_vs_observed.get("status_counts"),
                _CONTROLLER_PLANNED_STATUSES,
                anomalies,
                "planned_vs_observed_status_counts",
            )
            summary["planned_vs_observed_failure_count_buckets"][
                _controller_count_bucket(planned_vs_observed.get("failure_count"))
            ] += 1
        elif planned_vs_observed is not None:
            anomalies["planned_vs_observed_not_mapping"] += 1

        observed_summary = payload.get("observed_summary")
        if isinstance(observed_summary, dict):
            summary["observed_stage_count_buckets"][
                _controller_count_bucket(observed_summary.get("observed_stage_count"))
            ] += 1
            _add_known_controller_counts(
                summary["observed_status_counts"],
                observed_summary.get("observed_status_counts"),
                _CONTROLLER_TASK_STATUSES,
                anomalies,
                "observed_status_counts",
            )
        elif observed_summary is not None:
            anomalies["observed_summary_not_mapping"] += 1
        _add_source_class_recovery_stage_counts(summary, trace, payload, anomalies)

    return summary


def _print_controller_diagnostics_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_controller_diagnostics(tail)

    print()
    print(f"=== Controller diagnostics (last {len(tail)} runs) ===")
    print(f"controller_diagnostics_execution_rows: {summary['execution_rows']}")
    print(f"controller_diagnostics_payload_rows: {summary['payload_rows']}")
    print(f"controller_diagnostics_legacy_missing_rows: {summary['legacy_missing_rows']}")
    print(f"controller_diagnostics_omitted_rows: {summary['omitted_rows']}")
    print(f"controller_diagnostics_malformed_payload_rows: {summary['malformed_payload_rows']}")
    print(
        "controller_diagnostics_missing_legacy_or_omitted: "
        f"{summary['missing_legacy_or_omitted']}"
    )
    print(
        "controller_diagnostics_omission_reason_counts:",
        _ordered_counter_dict(
            summary["omission_reason_counts"],
            ("size_or_oversized", "builder_exception", "other", "missing"),
        ),
    )
    print(
        "schema_version:",
        _ordered_counter_dict(
            summary["schema_version"],
            (_CONTROLLER_DIAGNOSTICS_SCHEMA_VERSION, "unexpected_or_missing"),
        ),
    )
    print(
        "passive_only:",
        _ordered_counter_dict(summary["passive_only"], ("true", "false", "missing")),
    )
    print(
        "diagnostic_only:",
        _ordered_counter_dict(summary["diagnostic_only"], ("true", "false", "missing")),
    )
    print(
        "authority:",
        _ordered_counter_dict(summary["authority"], ("none", "unexpected_or_missing")),
    )
    print(
        "source:",
        _ordered_counter_dict(
            summary["source"],
            (_CONTROLLER_DIAGNOSTICS_SOURCE, "unexpected_or_missing"),
        ),
    )
    print(
        "run_plan_stage_count_buckets:",
        _ordered_counter_dict(summary["run_plan_stage_count_buckets"]),
    )
    print(
        "run_plan_disposition_counts:",
        _ordered_counter_dict(
            summary["run_plan_disposition_counts"],
            (*_CONTROLLER_PLAN_DISPOSITIONS, "unknown"),
        ),
    )
    print(
        "task_ledger_record_count_buckets:",
        _ordered_counter_dict(summary["task_ledger_record_count_buckets"]),
    )
    print(
        "task_ledger_status_counts:",
        _ordered_counter_dict(
            summary["task_ledger_status_counts"],
            (*_CONTROLLER_TASK_STATUSES, "unknown"),
        ),
    )
    print(
        "planned_vs_observed_status_counts:",
        _ordered_counter_dict(
            summary["planned_vs_observed_status_counts"],
            (*_CONTROLLER_PLANNED_STATUSES, "unknown"),
        ),
    )
    print(
        "planned_vs_observed_failure_count_buckets:",
        _ordered_counter_dict(summary["planned_vs_observed_failure_count_buckets"]),
    )
    print(
        "observed_stage_count_buckets:",
        _ordered_counter_dict(summary["observed_stage_count_buckets"]),
    )
    print(
        "observed_status_counts:",
        _ordered_counter_dict(
            summary["observed_status_counts"],
            (*_CONTROLLER_TASK_STATUSES, "unknown"),
        ),
    )
    print(
        "controller_diagnostics_source_class_recovery_payload_rows: "
        f"{summary['source_class_recovery_payload_rows']}"
    )
    print(
        "source_class_recovery_stage_present_rows: "
        f"{summary['source_class_recovery_stage_present_rows']}"
    )
    print(
        "source_class_recovery_not_observed_rows: "
        f"{summary['source_class_recovery_not_observed_rows']}"
    )
    print(
        "source_class_recovery_observed_blocked_rows: "
        f"{summary['source_class_recovery_observed_blocked_rows']}"
    )
    print(
        "source_class_recovery_observed_completed_rows: "
        f"{summary['source_class_recovery_observed_completed_rows']}"
    )
    print(
        "source_class_recovery_active_used_rows: "
        f"{summary['source_class_recovery_active_used_rows']}"
    )
    print(
        "source_class_recovery_unknown_or_malformed_status_rows: "
        f"{summary['source_class_recovery_unknown_or_malformed_status_rows']}"
    )
    print(
        "source_class_recovery_stage_status_counts:",
        _ordered_counter_dict(
            summary["source_class_recovery_stage_status_counts"],
            (*_CONTROLLER_PLANNED_STATUSES, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_observed_status_counts:",
        _ordered_counter_dict(
            summary["source_class_recovery_observed_status_counts"],
            (*_CONTROLLER_TASK_STATUSES, "missing", "unknown"),
        ),
    )
    print(
        "source_class_recovery_disposition_counts:",
        _ordered_counter_dict(
            summary["source_class_recovery_disposition_counts"],
            (*_CONTROLLER_PLAN_DISPOSITIONS, "missing", "unknown"),
        ),
    )
    print(
        "controller_diagnostics_anomalies:",
        _ordered_counter_dict(summary["anomalies"]),
    )


def _diagnostic_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value) if value else "missing"


def _diagnostic_count(value: Any) -> int:
    if isinstance(value, (list, tuple, set)):
        return len(value)
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 1


def _summarize_followup_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "chat_followup_rows": len(rows),
        "chat_followup_missing_diagnostics": 0,
        "needs_search_true": 0,
        "needs_search_false": 0,
        "search_ran_true": 0,
        "search_ran_false": 0,
        "search_skip_reason": Counter(),
        "evaluator_parse_status": Counter(),
        "query_count_buckets": Counter(),
        "new_passage_count_buckets": Counter(),
        "source_card_count_buckets": Counter(),
        "followup_route_observed": Counter(),
        "followup_route_shadow": Counter(),
        "followup_route_reason": Counter(),
        "freshness_cue_detected": Counter(),
        "freshness_cue_type": Counter(),
        "source_constraint_detected": Counter(),
        "source_constraint_type": Counter(),
        "contradiction_cue_detected": Counter(),
        "ambiguity_cue_detected": Counter(),
        "source_card_parity_status": Counter(),
        "cited_ids_without_cards_present": 0,
        "cited_ids_without_cards_total": 0,
        "cited_ids_without_cards_count_buckets": Counter(),
        "card_ids_not_cited_present": 0,
        "card_ids_not_cited_total": 0,
        "card_ids_not_cited_count_buckets": Counter(),
        "cards_from_error_response": Counter(),
        "no_results_count": 0,
        "retrieval_error_count": 0,
        "synthesis_error_count": 0,
        "suspicious": Counter(),
    }

    for row in rows:
        diagnostics = row.get("followup_diagnostics")
        if not isinstance(diagnostics, dict):
            summary["chat_followup_missing_diagnostics"] += 1
            continue

        needs_search = diagnostics.get("needs_search")
        search_ran = diagnostics.get("search_ran")
        search_skip_reason = diagnostics.get("search_skip_reason")
        query_count = diagnostics.get("query_count")
        new_passage_count = diagnostics.get("new_passage_count")
        source_card_count = diagnostics.get("source_card_count")

        for key in (
            "followup_route_observed",
            "followup_route_shadow",
            "followup_route_reason",
            "freshness_cue_detected",
            "freshness_cue_type",
            "source_constraint_detected",
            "source_constraint_type",
            "contradiction_cue_detected",
            "ambiguity_cue_detected",
            "source_card_parity_status",
            "cards_from_error_response",
        ):
            if key in diagnostics:
                summary[key][_diagnostic_value(diagnostics.get(key))] += 1

        cited_ids_without_cards_count = _diagnostic_count(
            diagnostics.get("cited_ids_without_cards")
        )
        card_ids_not_cited_count = _diagnostic_count(diagnostics.get("card_ids_not_cited"))
        if cited_ids_without_cards_count > 0:
            summary["cited_ids_without_cards_present"] += 1
        if card_ids_not_cited_count > 0:
            summary["card_ids_not_cited_present"] += 1
        summary["cited_ids_without_cards_total"] += cited_ids_without_cards_count
        summary["card_ids_not_cited_total"] += card_ids_not_cited_count
        summary["cited_ids_without_cards_count_buckets"][
            _source_card_count_bucket(cited_ids_without_cards_count)
        ] += 1
        summary["card_ids_not_cited_count_buckets"][
            _source_card_count_bucket(card_ids_not_cited_count)
        ] += 1

        if needs_search is True:
            summary["needs_search_true"] += 1
        elif needs_search is False:
            summary["needs_search_false"] += 1

        if search_ran is True:
            summary["search_ran_true"] += 1
        elif search_ran is False:
            summary["search_ran_false"] += 1

        reason = str(search_skip_reason) if search_skip_reason else "none"
        summary["search_skip_reason"][reason] += 1
        summary["evaluator_parse_status"][str(diagnostics.get("evaluator_parse_status") or "missing")] += 1
        summary["query_count_buckets"][_query_count_bucket(query_count)] += 1
        summary["new_passage_count_buckets"][_new_passage_count_bucket(new_passage_count)] += 1
        summary["source_card_count_buckets"][_source_card_count_bucket(source_card_count)] += 1

        if diagnostics.get("no_results") is True:
            summary["no_results_count"] += 1
        if diagnostics.get("retrieval_error") is True:
            summary["retrieval_error_count"] += 1
            summary["suspicious"]["retrieval_error"] += 1
        if diagnostics.get("synthesis_error") is True:
            summary["synthesis_error_count"] += 1
            summary["suspicious"]["synthesis_error"] += 1
        if diagnostics.get("evaluator_parse_status") == "parse_failed":
            summary["suspicious"]["parse_failed"] += 1
        if (
            needs_search is True
            and search_ran is False
            and search_skip_reason != "missing_followup_queries"
        ):
            summary["suspicious"][
                "needs_search_true_but_search_not_ran_without_missing_query_reason"
            ] += 1
        try:
            new_passage_n = int(new_passage_count or 0)
            source_card_n = int(source_card_count or 0)
        except (TypeError, ValueError):
            new_passage_n = 0
            source_card_n = 0
        if source_card_n == 0 and new_passage_n > 0:
            summary["suspicious"]["source_card_count_zero_with_new_passages"] += 1

    for key in (
        "needs_search_true_but_search_not_ran_without_missing_query_reason",
        "parse_failed",
        "retrieval_error",
        "synthesis_error",
        "source_card_count_zero_with_new_passages",
    ):
        summary["suspicious"].setdefault(key, 0)

    return summary


def _print_followup_diagnostics_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_followup_diagnostics(tail)

    print()
    print(f"=== Chat follow-up diagnostics (last {len(tail)} rows) ===")
    print(f"chat_followup_rows: {summary['chat_followup_rows']}")
    print(
        "chat_followup_missing_diagnostics: "
        f"{summary['chat_followup_missing_diagnostics']}"
    )
    print(f"needs_search_true: {summary['needs_search_true']}")
    print(f"needs_search_false: {summary['needs_search_false']}")
    print(f"search_ran_true: {summary['search_ran_true']}")
    print(f"search_ran_false: {summary['search_ran_false']}")
    print("search_skip_reason:", dict(summary["search_skip_reason"].most_common()))
    print("evaluator_parse_status:", dict(summary["evaluator_parse_status"].most_common()))
    print("query_count_buckets:", dict(summary["query_count_buckets"].most_common()))
    print(
        "new_passage_count_buckets:",
        dict(summary["new_passage_count_buckets"].most_common()),
    )
    print(
        "source_card_count_buckets:",
        dict(summary["source_card_count_buckets"].most_common()),
    )
    print("followup_route_observed:", dict(summary["followup_route_observed"].most_common()))
    print("followup_route_shadow:", dict(summary["followup_route_shadow"].most_common()))
    print("followup_route_reason:", dict(summary["followup_route_reason"].most_common()))
    print("freshness_cue_detected:", dict(summary["freshness_cue_detected"].most_common()))
    print("freshness_cue_type:", dict(summary["freshness_cue_type"].most_common()))
    print(
        "source_constraint_detected:",
        dict(summary["source_constraint_detected"].most_common()),
    )
    print("source_constraint_type:", dict(summary["source_constraint_type"].most_common()))
    print(
        "contradiction_cue_detected:",
        dict(summary["contradiction_cue_detected"].most_common()),
    )
    print(
        "ambiguity_cue_detected:",
        dict(summary["ambiguity_cue_detected"].most_common()),
    )
    print(
        "source_card_parity_status:",
        dict(summary["source_card_parity_status"].most_common()),
    )
    print(
        "cited_ids_without_cards_present: "
        f"{summary['cited_ids_without_cards_present']}"
    )
    print(f"cited_ids_without_cards_total: {summary['cited_ids_without_cards_total']}")
    print(
        "cited_ids_without_cards_count_buckets:",
        dict(summary["cited_ids_without_cards_count_buckets"].most_common()),
    )
    print(f"card_ids_not_cited_present: {summary['card_ids_not_cited_present']}")
    print(f"card_ids_not_cited_total: {summary['card_ids_not_cited_total']}")
    print(
        "card_ids_not_cited_count_buckets:",
        dict(summary["card_ids_not_cited_count_buckets"].most_common()),
    )
    print(
        "cards_from_error_response:",
        dict(summary["cards_from_error_response"].most_common()),
    )
    print(f"no_results_count: {summary['no_results_count']}")
    print(f"retrieval_error_count: {summary['retrieval_error_count']}")
    print(f"synthesis_error_count: {summary['synthesis_error_count']}")
    print("suspicious:", dict(summary["suspicious"].most_common()))


def _summarize_provider_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "rows_with_provider_diagnostics": 0,
        "provider_diagnostic_attempts": 0,
        "attempts_by_provider": Counter(),
        "successes_by_provider": Counter(),
        "failures_by_provider": Counter(),
        "attempts_by_role": Counter(),
        "depth_buckets": Counter(),
        "output_type_buckets": Counter(),
        "cost_estimate_available_count": 0,
        "estimated_cost_null_disabled_count": 0,
        "overlap_diagnostic_attempts": 0,
        "raw_url_count_buckets": Counter(),
        "raw_unique_url_count_buckets": Counter(),
        "raw_url_overlap_count_buckets": Counter(),
        "raw_domain_count_buckets": Counter(),
        "raw_domain_overlap_count_buckets": Counter(),
        "accepted_url_overlap_count_buckets": Counter(),
        "accepted_domain_count_buckets": Counter(),
        "new_domain_count_buckets": Counter(),
        "new_source_count_buckets": Counter(),
        "query_similarity_max_buckets": Counter(),
        "query_similarity_basis": Counter(),
    }

    for row in rows:
        diagnostics = row.get("provider_diagnostics")
        if not isinstance(diagnostics, list):
            continue
        summary["rows_with_provider_diagnostics"] += 1
        if row.get("provider_shadow_cost_estimate_available") is True:
            summary["cost_estimate_available_count"] += 1
        if row.get("provider_estimated_cost_usd") is None:
            summary["estimated_cost_null_disabled_count"] += 1

        for attempt in diagnostics:
            if not isinstance(attempt, dict):
                continue
            logical_attempt_count = _diagnostic_count(attempt.get("logical_attempt_count")) or 1
            provider = str(attempt.get("provider") or "unknown")
            role = str(attempt.get("provider_role") or "unknown")
            depth = str(attempt.get("depth") or "missing")
            output_type = str(attempt.get("output_type") or "missing")
            summary["provider_diagnostic_attempts"] += logical_attempt_count
            summary["attempts_by_provider"][provider] += logical_attempt_count
            summary["attempts_by_role"][role] += logical_attempt_count
            summary["depth_buckets"][depth] += logical_attempt_count
            summary["output_type_buckets"][output_type] += logical_attempt_count
            if attempt.get("success") is False:
                summary["failures_by_provider"][provider] += logical_attempt_count
            else:
                summary["successes_by_provider"][provider] += logical_attempt_count
            if attempt.get("provider_overlap_diagnostics_available") is True:
                summary["overlap_diagnostic_attempts"] += logical_attempt_count
                for key in (
                    "raw_url_count",
                    "raw_unique_url_count",
                    "raw_url_overlap_count",
                    "raw_domain_count",
                    "raw_domain_overlap_count",
                    "accepted_url_overlap_count",
                    "accepted_domain_count",
                    "new_domain_count",
                    "new_source_count",
                ):
                    summary[f"{key}_buckets"][
                        _provider_overlap_count_bucket(attempt.get(key))
                    ] += logical_attempt_count
                summary["query_similarity_max_buckets"][
                    _provider_similarity_bucket(attempt.get("query_similarity_max"))
                ] += logical_attempt_count
                summary["query_similarity_basis"][
                    str(attempt.get("query_similarity_basis") or "missing")
                ] += logical_attempt_count

    return summary


def _print_provider_diagnostics_summary(rows: list[dict[str, Any]]) -> None:
    tail = rows[-DEFAULT_LAST_N:]
    summary = _summarize_provider_diagnostics(tail)
    if summary["rows_with_provider_diagnostics"] <= 0:
        return

    print()
    print(
        "=== Provider diagnostics "
        f"(last {len(tail)} rows, {summary['rows_with_provider_diagnostics']} with diagnostics) ==="
    )
    print(f"provider_diagnostic_attempts: {summary['provider_diagnostic_attempts']}")
    print("attempts_by_provider:", dict(summary["attempts_by_provider"].most_common()))
    print("successes_by_provider:", dict(summary["successes_by_provider"].most_common()))
    print("failures_by_provider:", dict(summary["failures_by_provider"].most_common()))
    print("attempts_by_role:", dict(summary["attempts_by_role"].most_common()))
    print("depth_buckets:", dict(summary["depth_buckets"].most_common()))
    print("output_type_buckets:", dict(summary["output_type_buckets"].most_common()))
    print(f"cost_estimate_available_count: {summary['cost_estimate_available_count']}")
    print(
        "estimated_cost_null_disabled_count: "
        f"{summary['estimated_cost_null_disabled_count']}"
    )
    if summary["overlap_diagnostic_attempts"] > 0:
        print(f"overlap_diagnostic_attempts: {summary['overlap_diagnostic_attempts']}")
        print("raw_url_count_buckets:", dict(summary["raw_url_count_buckets"].most_common()))
        print(
            "raw_unique_url_count_buckets:",
            dict(summary["raw_unique_url_count_buckets"].most_common()),
        )
        print(
            "raw_url_overlap_count_buckets:",
            dict(summary["raw_url_overlap_count_buckets"].most_common()),
        )
        print(
            "raw_domain_count_buckets:",
            dict(summary["raw_domain_count_buckets"].most_common()),
        )
        print(
            "raw_domain_overlap_count_buckets:",
            dict(summary["raw_domain_overlap_count_buckets"].most_common()),
        )
        print(
            "accepted_url_overlap_count_buckets:",
            dict(summary["accepted_url_overlap_count_buckets"].most_common()),
        )
        print(
            "accepted_domain_count_buckets:",
            dict(summary["accepted_domain_count_buckets"].most_common()),
        )
        print("new_domain_count_buckets:", dict(summary["new_domain_count_buckets"].most_common()))
        print("new_source_count_buckets:", dict(summary["new_source_count_buckets"].most_common()))
        print(
            "query_similarity_max_buckets:",
            dict(summary["query_similarity_max_buckets"].most_common()),
        )
        print("query_similarity_basis:", dict(summary["query_similarity_basis"].most_common()))


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    idx = int(round((len(vs) - 1) * p))
    idx = max(0, min(idx, len(vs) - 1))
    return float(vs[idx])


def _fmt_s(v: float) -> str:
    if abs(v - round(v)) < 0.05:
        return f"{int(round(v))}s"
    return f"{v:.1f}s"


def main() -> None:
    if not LOG.exists():
        print(f"No log at {LOG}")
        return

    runs: list[dict] = []
    followups: list[dict] = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("event") == "execution":
            runs.append(o)
        elif o.get("event") == "chat_followup":
            followups.append(o)
    if not runs:
        _print_provider_diagnostics_summary(followups)
        _print_followup_diagnostics_summary(followups)
        print("No execution events found.")
        return

    tail = runs[-DEFAULT_LAST_N:]
    n = len(tail)
    flags: Counter[str] = Counter()
    by_qt: Counter[str] = Counter()
    by_corpus_state: Counter[str] = Counter()

    recon_times: list[float] = []
    iter1_times: list[float] = []
    iter2_times: list[float] = []
    synth_times: list[float] = []
    iter2_nonzero: list[float] = []
    timing_n = 0

    redundancy_skipped = 0
    synth_sufficient_p1 = 0
    recon_fired = 0
    total_costs: list[float] = []
    input_tokens: list[float] = []
    output_tokens: list[float] = []
    total_calls: list[float] = []

    for o in tail:
        by_qt[str(o.get("query_type") or "?")] += 1
        by_corpus_state[str(o.get("corpus_state") or ("OFF_TOPIC" if o.get("corpus_weak") else "HEALTHY"))] += 1
        for f in o.get("waste_flags") or []:
            flags[str(f)] += 1

        if o.get("query_redundancy_skipped") is True:
            redundancy_skipped += 1
        if o.get("synth_sufficient_first_pass") is True:
            synth_sufficient_p1 += 1
        if o.get("recon_fired") is True:
            recon_fired += 1
        cost = o.get("cost")
        if isinstance(cost, dict):
            try:
                total_costs.append(float(cost.get("total_cost_usd") or 0.0))
                input_tokens.append(float(cost.get("total_input_tokens") or 0.0))
                output_tokens.append(float(cost.get("total_output_tokens") or 0.0))
                total_calls.append(float(cost.get("total_calls") or 0.0))
            except (TypeError, ValueError):
                pass

        t = o.get("timing")
        if isinstance(t, dict):
            timing_n += 1
            r = float(t.get("recon_seconds") or 0.0)
            i1 = float(t.get("iter1_seconds") or 0.0)
            i2 = float(t.get("iter2_seconds") or 0.0)
            sy = float(t.get("synthesis_seconds") or 0.0)
            recon_times.append(r)
            iter1_times.append(i1)
            iter2_times.append(i2)
            synth_times.append(sy)
            if i2 > 0:
                iter2_nonzero.append(i2)

    skipped_i2 = sum(1 for x in iter2_times if x <= 0.01)
    baseline_i2 = (sum(iter2_nonzero) / len(iter2_nonzero)) if iter2_nonzero else 0.0
    avg_saved = baseline_i2 if redundancy_skipped else 0.0

    print(f"=== Timing (last {n} runs, timing available on {timing_n}) ===")
    print(
        f"recon_seconds:      median={_fmt_s(_percentile(recon_times, 0.5))}   "
        f"p95={_fmt_s(_percentile(recon_times, 0.95))}"
    )
    print(
        f"iter1_seconds:      median={_fmt_s(_percentile(iter1_times, 0.5))}   "
        f"p95={_fmt_s(_percentile(iter1_times, 0.95))}"
    )
    print(
        f"iter2_seconds:      median={_fmt_s(_percentile(iter2_times, 0.5))}   "
        f"p95={_fmt_s(_percentile(iter2_times, 0.95))}   "
        f"(skipped in {skipped_i2}/{max(1, timing_n)} runs)"
    )
    print(
        f"synthesis_seconds:  median={_fmt_s(_percentile(synth_times, 0.5))}   "
        f"p95={_fmt_s(_percentile(synth_times, 0.95))}"
    )
    print()

    print(f"=== Cost (last {n} runs, cost available on {len(total_costs)}) ===")
    if total_costs:
        print(
            f"total_cost_usd:     median=${_percentile(total_costs, 0.5):.4f}   "
            f"p95=${_percentile(total_costs, 0.95):.4f}"
        )
        print(
            f"input_tokens:       median={int(_percentile(input_tokens, 0.5))}   "
            f"p95={int(_percentile(input_tokens, 0.95))}"
        )
        print(
            f"output_tokens:      median={int(_percentile(output_tokens, 0.5))}   "
            f"p95={int(_percentile(output_tokens, 0.95))}"
        )
        print(
            f"total_calls:        median={int(_percentile(total_calls, 0.5))}   "
            f"p95={int(_percentile(total_calls, 0.95))}"
        )
    else:
        print("(no cost blocks found; historical records are still readable)")
    print()

    print("=== Efficiency ===")
    print(
        f"redundancy_skipped:     {redundancy_skipped}/{n} runs "
        f"({(100.0 * redundancy_skipped / n):.0f}%)  avg saved: {_fmt_s(avg_saved)}/run"
    )
    print(
        f"synth_sufficient_p1:   {synth_sufficient_p1}/{n} runs "
        f"({(100.0 * synth_sufficient_p1 / n):.0f}%)"
    )
    print(
        f"recon_fired:           {recon_fired}/{n} runs "
        f"({(100.0 * recon_fired / n):.0f}%)"
    )
    print()

    print("=== Waste flags (frequency) ===")
    if flags:
        for k, c in flags.most_common(20):
            print(f"{k}: {c}")
    else:
        print("(none)")
    print()
    print("by query_type:", dict(by_qt.most_common(20)))
    print("by corpus_state:", dict(by_corpus_state.most_common(20)))

    _print_controller_diagnostics_summary(runs)
    _print_source_class_observability_summary(runs)
    _print_source_class_candidate_v2_summary(runs)
    _print_source_class_recovery_validation_summary(runs)
    _print_retrieval_stop_shadow_summary(runs)
    _print_retrieval_stop_active_summary(runs)
    _print_retrieval_budget_pressure_summary(runs)
    _print_provider_diagnostics_summary(runs + followups)
    _print_followup_diagnostics_summary(followups)

    if KB_TRIGGERS.exists():
        kb_lines: list[dict] = []
        try:
            for line in KB_TRIGGERS.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("event") == "kb_trigger":
                    kb_lines.append(o)
        except Exception:
            kb_lines = []
        tail_kb = kb_lines[-DEFAULT_LAST_N:] if len(kb_lines) > DEFAULT_LAST_N else kb_lines
        inline = [o for o in tail_kb if isinstance(o.get("providers_used"), list)]
        if inline:
            print()
            print(f"=== KB triggers (last {len(tail_kb)} lines, {len(inline)} with inline providers_used) ===")
            mix_total: Counter[str] = Counter()
            mix_fired: Counter[str] = Counter()
            yield_fired: list[int] = []
            yield_not: list[int] = []
            iter1_by_mix: dict[str, list[float]] = defaultdict(list)
            for o in inline:
                key = ",".join(o["providers_used"])
                mix_total[key] += 1
                chunks = int(o.get("retrieval_yield_chunks") or 0)
                if o.get("fired") is True:
                    mix_fired[key] += 1
                    yield_fired.append(chunks)
                else:
                    yield_not.append(chunks)
                tm = o.get("timing")
                if isinstance(tm, dict):
                    iter1_by_mix[key].append(float(tm.get("iter1_seconds") or 0.0))
            for key in sorted(mix_total.keys()):
                t = mix_total[key]
                f = mix_fired[key]
                pct = 100.0 * f / t if t else 0.0
                extra = ""
                if key in iter1_by_mix and iter1_by_mix[key]:
                    avg_i1 = sum(iter1_by_mix[key]) / len(iter1_by_mix[key])
                    extra = f"  avg_iter1={avg_i1:.2f}s"
                print(f"  [{key}]  lines={t}  fired={f} ({pct:.0f}%){extra}")
            if yield_fired or yield_not:
                af = sum(yield_fired) / len(yield_fired) if yield_fired else 0.0
                an = sum(yield_not) / len(yield_not) if yield_not else 0.0
                print(
                    f"  avg retrieval_yield_chunks: fired={af:.1f}  not_fired={an:.1f} "
                    f"(n_fired={len(yield_fired)} n_not={len(yield_not)})"
                )


if __name__ == "__main__":
    main()
