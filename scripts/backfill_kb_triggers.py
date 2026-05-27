#!/usr/bin/env python3
"""
Recompute KB trigger lines from execution_log.jsonl and append to kb_triggers.jsonl.

The pipeline logs one kb_trigger line per run with deterministic flags from
compute_review_flags; historical logs may lack matching KB rows if logging changed.

Dry-run by default. Use --apply to append (optionally backup KB file).

Examples:
  python scripts/backfill_kb_triggers.py
  python scripts/backfill_kb_triggers.py --dry-run
  python scripts/backfill_kb_triggers.py --apply --backup
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_EXECUTION_LOG = ROOT / "output" / "execution_log.jsonl"
DEFAULT_KB_TRIGGERS = ROOT / "output" / "kb_triggers.jsonl"
DEFAULT_FEEDBACK_LOG = ROOT / "output" / "feedback_log.jsonl"


def _flatten_providers_used(providers_by_iteration: list | None) -> list[str]:
    """Mirror ui.pages._flatten_providers_used without importing Streamlit."""
    seen: set[str] = set()
    out: list[str] = []
    for group in providers_by_iteration or []:
        for name in group or []:
            n = str(name).strip()
            if not n or n in seen:
                continue
            seen.add(n)
            out.append(n)
    return out


def feedback_last_by_session(feedback_path: Path) -> dict[str, dict[str, Any]]:
    """Latest feedback payload per session_id (same shape as load_feedback_for_session)."""
    out: dict[str, dict[str, Any]] = {}
    if not feedback_path.exists():
        return out
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("event") != "feedback":
            continue
        sid = str(o.get("session_id") or "").strip()
        if not sid:
            continue
        out[sid] = {
            "user_rating": o.get("user_rating"),
            "user_notes": o.get("user_notes"),
            "scout_helpful": o.get("scout_helpful"),
            "run_id": o.get("run_id"),
            "overall": o.get("overall"),
            "answer_completeness": o.get("answer_completeness"),
            "evidence_quality": o.get("evidence_quality"),
            "output_precision": o.get("output_precision"),
            "scout_contribution": o.get("scout_contribution"),
            "overall_auto": o.get("overall_auto"),
            "timestamp_utc": o.get("timestamp_utc"),
        }
    return out


def execution_row_to_record(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten execution log JSON object into the dict compute_review_flags expects."""
    base = dict(row)
    et = base.get("execution_trace")
    if isinstance(et, dict):
        for k, v in et.items():
            base.setdefault(k, v)

    if base.get("pass_providers") is None and base.get("providers_by_iteration") is not None:
        base["pass_providers"] = base["providers_by_iteration"]

    qp = base.get("queries_per_iteration")
    if isinstance(qp, dict):
        base.setdefault("queries_iter1", qp.get("1") if "1" in qp else qp.get(1) or [])
        base.setdefault("queries_iter2", qp.get("2") if "2" in qp else qp.get(2) or [])

    tc = base.get("total_chunks_embedded")
    if tc is None and base.get("total_chunks") is not None:
        base["total_chunks_embedded"] = base["total_chunks"]

    base.setdefault("intent", "general")
    base.setdefault("complexity", "medium")
    base.setdefault("scout_fired", False)
    base.setdefault("synth_was_insufficient", False)
    base.setdefault("supplemental_ran", False)
    base.setdefault("delta_urls_supplemental", 0)
    base.setdefault("queries_iter1", [])
    base.setdefault("queries_iter2", [])
    base.setdefault("total_chunks_embedded", 0)
    base.setdefault("scrutineer_high_flags", 0)

    return base


def existing_kb_run_ids(kb_path: Path) -> set[str]:
    ids: set[str] = set()
    if not kb_path.exists():
        return ids
    for line in kb_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("event") == "kb_trigger" and o.get("run_id"):
            ids.add(str(o["run_id"]))
    return ids


def kb_trigger_timestamp(row: dict[str, Any]) -> str:
    for key in ("timestamp_utc",):
        v = row.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    et = row.get("execution_trace")
    if isinstance(et, dict):
        v = et.get("timestamp_utc")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return datetime.now(timezone.utc).isoformat()


def build_trigger_entry(
    row: dict[str, Any],
    feedback_fb: dict[str, Any],
    *,
    compute_review_flags: Any,
    review_score: Any,
    should_auto_review: Any,
) -> dict[str, Any] | None:
    run_id = str(row.get("run_id") or "").strip()
    session_id = str(row.get("session_id") or "").strip()
    if not run_id or not session_id:
        return None

    record = execution_row_to_record(row)

    flags_obj = compute_review_flags(record, feedback_fb)
    score_val = review_score(flags_obj)
    review_f = should_auto_review(flags_obj)

    strategy_mode = str(row.get("mode") or "Balanced")
    report_type = str(row.get("report_type") or "general_research")

    trigger_entry = {
        **asdict(flags_obj),
        "event": "kb_trigger",
        "run_id": run_id,
        "session_id": session_id,
        "query": str(record.get("query") or row.get("query") or "")[:200],
        "report_type": report_type,
        "mode": strategy_mode,
        "synth_deficiency": record.get("synth_deficiency"),
        "score": score_val,
        "fired": review_f,
        "timestamp_utc": kb_trigger_timestamp(row),
        "retrieval_yield_chunks": int(record.get("total_chunks_embedded") or 0),
        "providers_used": _flatten_providers_used(record.get("pass_providers")),
        "timing": dict(record.get("timing") or {}),
    }
    return trigger_entry


def run_backfill(
    execution_log: Path,
    kb_triggers: Path,
    feedback_log: Path,
    *,
    apply: bool,
    skip_existing: bool,
    backup: bool,
) -> dict[str, int]:
    """Returns counters: scanned, appended, skipped_existing, skipped_invalid."""
    from core.review_flags import compute_review_flags, review_score, should_auto_review

    stats = {"scanned": 0, "appended": 0, "skipped_existing": 0, "skipped_invalid": 0}
    fb_index = feedback_last_by_session(feedback_log)
    existing = existing_kb_run_ids(kb_triggers) if skip_existing else set()

    new_lines: list[str] = []

    if not execution_log.exists():
        return stats

    for raw in execution_log.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            stats["skipped_invalid"] += 1
            continue
        if row.get("event") != "execution":
            continue
        stats["scanned"] += 1
        rid = str(row.get("run_id") or "").strip()
        if not rid:
            stats["skipped_invalid"] += 1
            continue
        if skip_existing and rid in existing:
            stats["skipped_existing"] += 1
            continue

        sid = str(row.get("session_id") or "").strip()
        feedback_fb = fb_index.get(sid, {})

        trigger_entry = build_trigger_entry(
            row,
            feedback_fb,
            compute_review_flags=compute_review_flags,
            review_score=review_score,
            should_auto_review=should_auto_review,
        )
        if not trigger_entry:
            stats["skipped_invalid"] += 1
            continue

        new_lines.append(json.dumps(trigger_entry, ensure_ascii=True))
        existing.add(rid)
        stats["appended"] += 1

    if apply and new_lines:
        kb_triggers.parent.mkdir(parents=True, exist_ok=True)
        if backup and kb_triggers.exists():
            shutil.copy2(kb_triggers, kb_triggers.with_suffix(kb_triggers.suffix + ".bak"))
        with kb_triggers.open("a", encoding="utf-8") as f:
            for ln in new_lines:
                f.write(ln + "\n")

    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill kb_triggers.jsonl from execution_log.jsonl")
    ap.add_argument(
        "--execution-log",
        type=Path,
        default=DEFAULT_EXECUTION_LOG,
        help=f"path to execution_log.jsonl (default: {DEFAULT_EXECUTION_LOG})",
    )
    ap.add_argument(
        "--kb-triggers",
        type=Path,
        default=DEFAULT_KB_TRIGGERS,
        help=f"path to kb_triggers.jsonl (default: {DEFAULT_KB_TRIGGERS})",
    )
    ap.add_argument(
        "--feedback-log",
        type=Path,
        default=DEFAULT_FEEDBACK_LOG,
        help=f"path to feedback_log.jsonl (default: {DEFAULT_FEEDBACK_LOG})",
    )
    mode_g = ap.add_mutually_exclusive_group()
    mode_g.add_argument(
        "--apply",
        action="store_true",
        help="append new kb_trigger lines to kb_triggers.jsonl",
    )
    mode_g.add_argument(
        "--dry-run",
        action="store_true",
        help="only print statistics (default if neither flag is passed)",
    )
    ap.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="append even when run_id already appears in kb_triggers.jsonl",
    )
    ap.add_argument(
        "--backup",
        action="store_true",
        help="copy kb_triggers.jsonl to .bak before appending (--apply only)",
    )
    args = ap.parse_args()

    exec_log = args.execution_log.resolve()
    kb_path = args.kb_triggers.resolve()
    fb_path = args.feedback_log.resolve()

    stats = run_backfill(
        exec_log,
        kb_path,
        fb_path,
        apply=bool(args.apply),
        skip_existing=not bool(args.no_skip_existing),
        backup=bool(args.backup),
    )

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[backfill_kb_triggers] {mode}")
    print(f"  execution_log: {exec_log}")
    print(f"  kb_triggers:   {kb_path}")
    print(f"  feedback_log:  {fb_path}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if not args.apply and stats["appended"] > 0:
        print("  (no files modified; pass --apply to append)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
