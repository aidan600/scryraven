"""Persistence side-effect execution for the pipeline orchestrator.

This module executes already-authorized persistence writes. It does not decide
pipeline behavior, build final answers, select providers, or change persistence
payload shapes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.db import ensure_telemetry_schema, insert_run, upsert_session
from core.kb_review_persistence_context import (
    KbReviewPersistenceContext,
    build_kb_execution_record,
    build_kb_trigger_entry,
)
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
class PersistenceSideEffectResult:
    """Passive result values surfaced after persistence side effects run."""

    execution_log_entry: dict[str, Any]
    kb_instrumentation: dict[str, Any] | None = None
    kb_warning: str | None = None
    sqlite_row_written: bool = False


def execute_safe_blocked_terminal_persistence(
    *,
    execution_log_path: Path,
    execution_log_entry: dict[str, Any],
    run_id: str,
    session_id: str,
    latency_seconds: float,
    strategy: str,
    execution_trace: dict[str, Any],
    run_log: Any,
) -> None:
    """Persist an already-authorized safe non-Author terminal.

    RunKernel and the installed blocked FinalAnswerPacket adapter own the
    terminal posture. This helper owns only the existing JSONL lifecycle side
    effects so an early safe return remains replay-identifiable and does not
    look like an abandoned run.
    """

    append_jsonl(
        execution_log_path,
        execution_log_entry,
        logger=run_log,
    )
    timing = execution_trace.get("timing")
    log_run_completed(
        run_id=run_id,
        session_id=session_id,
        phase="pipeline",
        latency_seconds=latency_seconds,
        mode=strategy,
        timing=dict(timing) if isinstance(timing, dict) else None,
        path=execution_log_path,
        logger=run_log,
    )


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
        execution_record = build_kb_execution_record(context)
        flags_obj = compute_review_flags(execution_record, feedback_fb)
        score_val = review_score(flags_obj)
        review_f = should_auto_review(flags_obj)
        trigger_entry = build_kb_trigger_entry(
            context=context,
            flags_obj=flags_obj,
            score_val=score_val,
            review_f=review_f,
            execution_record=execution_record,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
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
