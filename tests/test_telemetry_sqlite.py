"""SQLite telemetry: execution log mapping must persist KB instrumentation fields."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def test_insert_run_persists_kb_from_merged_execution_mapping(tmp_path: Path) -> None:
    """
    Regression guard: ``execution_jsonl_to_run_row`` reads ``kb_instrumentation``;
    orchestrator merges that onto the in-memory execution entry after KB review,
    then persists to SQLite so ``kb_score`` / ``kb_fired`` are not left NULL.
    """
    from core.db import execution_jsonl_to_run_row, init_db, insert_run

    db_path = tmp_path / "telemetry.db"
    init_db(db_path)
    execution_obj = {
        "event": "execution",
        "run_id": "run-test-kb-1",
        "session_id": "sess-1",
        "timestamp_utc": "2026-05-01T12:00:00+00:00",
        "query": "q",
        "mode": "Balanced",
        "report_type": "general_research",
        "complexity": "medium",
        "timing": {},
        "cost": {},
        "urls_fetched": 0,
        "iterations_run": 0,
        "kb_instrumentation": {
            "score": 0.1234,
            "fired": True,
            "agent_ran": True,
        },
    }
    row = execution_jsonl_to_run_row(execution_obj)
    assert row is not None
    insert_run(row, db_path=db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT kb_score, kb_fired FROM runs WHERE run_id = ?",
            ("run-test-kb-1",),
        )
        score, fired = cur.fetchone()
        assert abs(float(score) - 0.1234) < 1e-6
        assert fired == 1
    finally:
        conn.close()


def test_orchestrator_style_db_write_initializes_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ensure_telemetry_schema`` before connect/insert matches pipeline telemetry path."""

    db_path = tmp_path / "orch_telemetry.db"
    monkeypatch.setenv("PROPLEX_TELEMETRY_DB", str(db_path))

    from core.db import (
        ensure_telemetry_schema,
        execution_jsonl_to_run_row,
        insert_run,
        upsert_session,
    )

    assert not db_path.exists()
    ensure_telemetry_schema()
    execution_obj = {
        "event": "execution",
        "run_id": "run-orch-1",
        "session_id": "sess-orch",
        "timestamp_utc": "2026-05-02T10:00:00+00:00",
        "query": "q",
        "mode": "Balanced",
        "report_type": "general_research",
        "complexity": "low",
        "timing": {},
        "cost": {},
        "urls_fetched": 0,
        "iterations_run": 0,
    }
    row = execution_jsonl_to_run_row(execution_obj)
    assert row is not None
    conn = sqlite3.connect(db_path)
    try:
        insert_run(row, conn=conn)
        upsert_session(row.get("session_id"), row.get("timestamp_utc") or "", conn=conn)
        conn.commit()
    finally:
        conn.close()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT run_id FROM runs WHERE run_id = ?", ("run-orch-1",))
        assert cur.fetchone() is not None
        cur = conn.execute(
            "SELECT run_count FROM sessions WHERE session_id = ?", ("sess-orch",)
        )
        assert cur.fetchone() == (1,)
    finally:
        conn.close()
