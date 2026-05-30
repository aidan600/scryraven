"""Persistence side-effect execution for the pipeline orchestrator.

This module executes already-authorized persistence writes. It does not decide
pipeline behavior, build final answers, select providers, or change persistence
payload shapes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.db import ensure_telemetry_schema, insert_run, upsert_session
from core.outcome_persistence_packaging import build_sqlite_row_payload
from core.policy import apply_policy_to_run_config
from core.review_flags import (
    compute_review_flags,
    load_feedback_for_session,
    review_score,
    should_auto_review,
)
from core.run_logging import append_jsonl, log_run_completed


@dataclass(frozen=True)
class KbReviewPersistenceContext:
    """Inputs needed to preserve the existing KB trigger logging side effect."""

    feedback_log_path: Path
    kb_triggers_path: Path
    session_id: str
    run_id: str
    query: str
    report_type: str
    query_type: str
    primary_entity: str | None
    entities_list: list[Any]
    empty_entity_flag: bool
    router_entity_retry_used: bool
    utilization_pre_retry: float
    utilization_rate_val: float
    retrieval_retry_used: bool
    corpus_state: str
    corpus_state_forced_flag: bool
    corpus_weak: bool
    useful_content: bool
    response_displayable: bool
    evidence_sufficient: bool
    answer_class: str
    useful_content_reason: str | None
    waste_flags: list[str]
    recon_fired: bool
    recon_confidence: float | None
    canonical_subject_resolved: str | None
    timing_payload: dict[str, Any]
    strategy: str
    fast_model: str
    smart_model: str
    complexity: str
    intent: str
    iterations_run: int
    providers_by_iteration: list[Any]
    queries_per_iter: dict[int, list[str]]
    queries_by_iteration: dict[int, list[str]]
    disambiguation_queries_per_iter: dict[int, list[str]]
    weak_corpus_recovery_considered: bool
    weak_corpus_recovery_used: bool
    weak_corpus_recovery_skip_reason: str | None
    weak_corpus_recovery_queries: list[str]
    weak_corpus_recovery_decision: str | None
    weak_corpus_recovery_reason: str | None
    weak_corpus_recovery_blockers: list[str]
    scout_fired: bool
    scout_key_used: str | None
    scout_queries: list[str]
    synth_was_insufficient: bool
    synth_sufficient_first_pass_raw: Any
    synth_sufficient_first_pass: bool
    failure_card_payload: dict[str, Any] | None
    supplemental_ran: bool
    delta_urls_supplemental: int
    total_chunks_embedded: int
    seen_urls: list[str]
    scrutineer_high_count: int
    scrutineer_flag_count: int
    synth_deficiency: str | None
    latency_seconds: float
    output_word_count: int
    report: str
    cost_snapshot: dict[str, Any]
    ask_model: Callable[..., Any]
    clean_json_response: Callable[..., Any]
    fast_provider: str
    local_url: str | None
    or_api_key: str | None
    kb_review_agent: Callable[..., Any]


@dataclass(frozen=True)
class PersistenceSideEffectResult:
    """Passive result values surfaced after persistence side effects run."""

    execution_log_entry: dict[str, Any]
    kb_instrumentation: dict[str, Any] | None = None
    kb_warning: str | None = None
    sqlite_row_written: bool = False


def _flatten_providers_used(providers_by_iteration: list[Any] | None) -> list[str]:
    providers: list[str] = []
    for item in providers_by_iteration or []:
        if isinstance(item, dict):
            vals = item.get("providers") or item.get("provider") or []
            if isinstance(vals, str):
                vals = [vals]
            for provider in vals:
                if provider and str(provider) not in providers:
                    providers.append(str(provider))
        elif item and str(item) not in providers:
            providers.append(str(item))
    return providers


def _append_policy_journal(
    *,
    policy_journal_path: Path,
    ts_utc: str,
    run_id: str,
    session_id: str,
    query: str,
    strategy: str,
    policy_applied: dict[str, Any],
    default_utilization_threshold: float,
    run_log: Any,
) -> None:
    try:
        defaults_for_journal = apply_policy_to_run_config(
            {
                "utilization_threshold": default_utilization_threshold,
                "synth_skip_utilization_threshold": default_utilization_threshold,
            },
            {},
        )
        override_used = any(
            float(policy_applied.get(k, defaults_for_journal.get(k)))
            != float(defaults_for_journal.get(k))
            for k in ("utilization_threshold", "synth_skip_utilization_threshold")
        )
        append_jsonl(
            policy_journal_path,
            {
                "event": "policy_applied",
                "timestamp_utc": ts_utc,
                "run_id": run_id,
                "session_id": session_id,
                "query": query[:200],
                "mode": strategy,
                "overrides_used": bool(override_used),
                "thresholds": policy_applied,
            },
            logger=run_log,
        )
    except Exception as e:
        run_log.warning("Non-fatal policy journaling failure: %s", e)


def _append_kb_trigger_review(
    *,
    context: KbReviewPersistenceContext,
    run_log: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    kb_instrumentation: dict[str, Any] | None = None
    kb_warning: str | None = None
    try:
        feedback_fb = load_feedback_for_session(
            context.feedback_log_path,
            context.session_id,
        )
        execution_record: dict[str, Any] = {
            "run_id": context.run_id,
            "session_id": context.session_id,
            "query": context.query[:200],
            "report_type": context.report_type,
            "query_type": context.query_type,
            "primary_entity": (context.primary_entity or "")[:200],
            "entities": [str(e)[:200] for e in (context.entities_list or [])],
            "empty_entity": context.empty_entity_flag,
            "router_entity_retry_used": context.router_entity_retry_used,
            "utilization_pre_retry": context.utilization_pre_retry,
            "utilization_rate": context.utilization_rate_val,
            "retrieval_retry_used": context.retrieval_retry_used,
            "corpus_state": context.corpus_state,
            "corpus_state_forced": context.corpus_state_forced_flag,
            "corpus_weak": context.corpus_weak,
            "useful_content": context.useful_content,
            "response_displayable": context.response_displayable,
            "evidence_sufficient": context.evidence_sufficient,
            "answer_class": context.answer_class,
            "useful_content_reason": context.useful_content_reason,
            "waste_flags": list(context.waste_flags),
            "query_redundancy_skipped": (
                "query_redundancy_skipped" in context.waste_flags
            ),
            "recon_fired": context.recon_fired,
            "recon_confidence": context.recon_confidence,
            "canonical_subject_resolved": (context.canonical_subject_resolved or "")[:200]
            or None,
            "timing": dict(context.timing_payload),
            "mode": context.strategy,
            "fast_model": context.fast_model,
            "smart_model": context.smart_model,
            "complexity": context.complexity,
            "intent": context.intent,
            "iterations_run": context.iterations_run,
            "pass_providers": context.providers_by_iteration,
            "queries_per_iteration": context.queries_per_iter,
            "queries_iter1": context.queries_by_iteration.get(1, []),
            "queries_iter2": context.queries_by_iteration.get(2, []),
            "disambiguation_queries_by_iteration": (
                context.disambiguation_queries_per_iter
            ),
            "weak_corpus_recovery_considered": (
                context.weak_corpus_recovery_considered
            ),
            "weak_corpus_recovery_used": context.weak_corpus_recovery_used,
            "weak_corpus_recovery_skip_reason": (
                context.weak_corpus_recovery_skip_reason
            ),
            "weak_corpus_recovery_queries": list(context.weak_corpus_recovery_queries),
            "weak_corpus_recovery_decision": context.weak_corpus_recovery_decision,
            "weak_corpus_recovery_reason": context.weak_corpus_recovery_reason,
            "weak_corpus_recovery_blockers": list(
                context.weak_corpus_recovery_blockers
            ),
            "scout_fired": context.scout_fired,
            "scout_key": context.scout_key_used,
            "scout_queries": list(context.scout_queries),
            "synth_was_insufficient": context.synth_was_insufficient,
            "synth_sufficient_first_pass_raw": context.synth_sufficient_first_pass_raw,
            "synth_sufficient_first_pass": context.synth_sufficient_first_pass,
            "failure_card": context.failure_card_payload,
            "supplemental_ran": context.supplemental_ran,
            "delta_urls_supplemental": context.delta_urls_supplemental,
            "total_chunks_embedded": context.total_chunks_embedded,
            "urls_fetched": len(context.seen_urls),
            "scrutineer_high_flags": context.scrutineer_high_count,
            "scrutineer_flag_count": context.scrutineer_flag_count,
            "synth_deficiency": context.synth_deficiency,
            "latency_seconds": context.latency_seconds,
            "output_word_count": context.output_word_count,
            "final_output_preview": (context.report or "")[:300],
            "cost": context.cost_snapshot,
        }
        flags_obj = compute_review_flags(execution_record, feedback_fb)
        score_val = review_score(flags_obj)
        review_f = should_auto_review(flags_obj)
        trigger_entry: dict[str, Any] = {
            **asdict(flags_obj),
            "event": "kb_trigger",
            "run_id": context.run_id,
            "session_id": context.session_id,
            "query": context.query[:200],
            "report_type": context.report_type,
            "mode": context.strategy,
            "synth_deficiency": context.synth_deficiency,
            "score": score_val,
            "fired": review_f,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "retrieval_yield_chunks": int(context.total_chunks_embedded),
            "providers_used": _flatten_providers_used(context.providers_by_iteration),
            "timing": dict(execution_record["timing"]),
        }
        kb_out = None
        if review_f:
            kb_out = context.kb_review_agent(
                context.ask_model,
                context.clean_json_response,
                trigger_entry,
                execution_record,
                context.report,
                context.fast_provider,
                context.fast_model,
                context.local_url,
                context.or_api_key,
            )
        if kb_out:
            trigger_entry["kb_review"] = kb_out
            if (
                kb_out.get("recurrence_risk") == "likely-recurring"
                and isinstance(kb_out.get("suggested_action"), dict)
            ):
                dtl = (kb_out.get("suggested_action") or {}).get("detail", "")
                if dtl:
                    kb_warning = dtl[:500]
        append_jsonl(context.kb_triggers_path, trigger_entry, logger=run_log)
        kb_instrumentation = {
            "score": round(float(score_val), 4),
            "fired": bool(review_f),
            "agent_ran": kb_out is not None,
        }
    except Exception as e:
        run_log.warning("Non-fatal KB review logging: %s", e)
    return kb_instrumentation, kb_warning


def _write_sqlite_telemetry(
    *,
    execution_log_entry: dict[str, Any],
    db_enabled: bool,
    run_log: Any,
) -> bool:
    if not db_enabled:
        return False
    sqlite_row_written = False
    try:
        row = build_sqlite_row_payload(execution_log_entry)
        if row:
            db_file = ensure_telemetry_schema()
            conn = sqlite3.connect(db_file)
            try:
                insert_run(row, conn=conn)
                upsert_session(
                    row.get("session_id"),
                    row.get("timestamp_utc") or "",
                    conn=conn,
                )
                conn.commit()
                sqlite_row_written = True
            finally:
                conn.close()
    except Exception as e:
        run_log.error("Failed to write telemetry to DB: %s", e)
    return sqlite_row_written


def execute_persistence_side_effects(
    *,
    execution_log_path: Path,
    execution_log_entry: dict[str, Any],
    run_id: str,
    session_id: str,
    latency_seconds: float,
    strategy: str,
    execution_trace: dict[str, Any],
    run_log: Any,
    policy_journal_path: Path,
    policy_applied: dict[str, Any],
    default_utilization_threshold: float,
    ts_utc: str,
    query: str,
    kb_context: KbReviewPersistenceContext,
    db_enabled: bool,
) -> PersistenceSideEffectResult:
    """Execute persistence side effects in the orchestrator's original order."""

    append_jsonl(
        execution_log_path,
        execution_log_entry,
        logger=run_log,
    )
    log_run_completed(
        run_id=run_id,
        session_id=session_id,
        phase="pipeline",
        latency_seconds=latency_seconds,
        mode=strategy,
        timing=dict(execution_trace["timing"]),
        path=execution_log_path,
        logger=run_log,
    )
    _append_policy_journal(
        policy_journal_path=policy_journal_path,
        ts_utc=ts_utc,
        run_id=run_id,
        session_id=session_id,
        query=query,
        strategy=strategy,
        policy_applied=policy_applied,
        default_utilization_threshold=default_utilization_threshold,
        run_log=run_log,
    )
    kb_instrumentation, kb_warning = _append_kb_trigger_review(
        context=kb_context,
        run_log=run_log,
    )
    if kb_instrumentation is not None:
        execution_log_entry["kb_instrumentation"] = kb_instrumentation
    sqlite_row_written = _write_sqlite_telemetry(
        execution_log_entry=execution_log_entry,
        db_enabled=db_enabled,
        run_log=run_log,
    )
    return PersistenceSideEffectResult(
        execution_log_entry=execution_log_entry,
        kb_instrumentation=kb_instrumentation,
        kb_warning=kb_warning,
        sqlite_row_written=sqlite_row_written,
    )
