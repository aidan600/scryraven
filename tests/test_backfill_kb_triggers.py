"""Tests for scripts/backfill_kb_triggers.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_backfill():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "backfill_kb_triggers.py"
    spec = importlib.util.spec_from_file_location("backfill_kb_triggers", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_execution_row_to_record_merges_trace_and_queries() -> None:
    bf = _load_backfill()
    row = {
        "event": "execution",
        "run_id": "r1",
        "session_id": "s1",
        "mode": "Deep",
        "execution_trace": {
            "intent": "news",
            "queries_per_iteration": {"1": ["q1a"], "2": ["q2a"]},
            "total_chunks": 42,
            "timestamp_utc": "2026-01-01T00:00:00+00:00",
        },
    }
    rec = bf.execution_row_to_record(row)
    assert rec["intent"] == "news"
    assert rec["queries_iter1"] == ["q1a"]
    assert rec["queries_iter2"] == ["q2a"]
    assert rec["total_chunks_embedded"] == 42


def test_backfill_dry_run_does_not_write(tmp_path: Path) -> None:
    bf = _load_backfill()
    exec_log = tmp_path / "execution_log.jsonl"
    kb = tmp_path / "kb_triggers.jsonl"
    fb = tmp_path / "feedback_log.jsonl"
    exec_log.write_text(
        json.dumps(
            {
                "event": "execution",
                "run_id": "r-new",
                "session_id": "s1",
                "mode": "Balanced",
                "report_type": "general_research",
                "intent": "general",
                "total_chunks_embedded": 100,
                "final_output_preview": "answer text",
                "complexity": "medium",
                "pass_providers": [["tavily"]],
                "queries_iter1": ["a"],
                "queries_iter2": ["b"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    kb.write_text("", encoding="utf-8")
    fb.write_text("", encoding="utf-8")

    stats = bf.run_backfill(exec_log, kb, fb, apply=False, skip_existing=True, backup=False)
    assert stats["appended"] == 1
    assert kb.read_text().strip() == ""


def test_backfill_apply_appends_and_skips_existing(tmp_path: Path) -> None:
    bf = _load_backfill()
    exec_log = tmp_path / "execution_log.jsonl"
    kb = tmp_path / "kb_triggers.jsonl"
    fb = tmp_path / "feedback_log.jsonl"
    row = {
        "event": "execution",
        "run_id": "r-one",
        "session_id": "s1",
        "mode": "Balanced",
        "report_type": "general_research",
        "intent": "general",
        "total_chunks_embedded": 100,
        "final_output_preview": "answer text",
        "complexity": "medium",
        "pass_providers": [["tavily"]],
        "queries_iter1": ["a"],
        "queries_iter2": ["b"],
        "timestamp_utc": "2026-04-01T12:00:00+00:00",
    }
    exec_log.write_text(json.dumps(row) + "\n", encoding="utf-8")
    kb.write_text("", encoding="utf-8")
    fb.write_text("", encoding="utf-8")

    stats1 = bf.run_backfill(exec_log, kb, fb, apply=True, skip_existing=True, backup=False)
    assert stats1["appended"] == 1
    lines = kb.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    o = json.loads(lines[0])
    assert o["event"] == "kb_trigger"
    assert o["run_id"] == "r-one"
    assert o["timestamp_utc"] == "2026-04-01T12:00:00+00:00"

    stats2 = bf.run_backfill(exec_log, kb, fb, apply=True, skip_existing=True, backup=False)
    assert stats2["appended"] == 0
    assert stats2["skipped_existing"] == 1
    assert len(kb.read_text(encoding="utf-8").strip().splitlines()) == 1
