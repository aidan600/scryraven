"""
SQLite schema and initialization for telemetry (runs, sessions).
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

RUN_COLUMNS: tuple[str, ...] = (
    "run_id",
    "session_id",
    "timestamp_utc",
    "query",
    "mode",
    "report_type",
    "complexity",
    "primary_entity",
    "entities",
    "economist_ran",
    "scout_key",
    "corpus_state",
    "retrieval_yield_chunks",
    "discover_candidate_urls_admitted",
    "urls_fetched",
    "iterations_run",
    "economist_seconds",
    "analyst_seconds",
    "author_seconds",
    "total_latency_seconds",
    "total_cost_usd",
    "total_input_tokens",
    "total_output_tokens",
    "output_word_count",
    "final_output_preview",
    "kb_score",
    "kb_fired",
    "useful_content",
)


def execution_jsonl_to_run_row(obj: dict[str, Any]) -> dict[str, Any] | None:
    """Map one execution_log JSON object (event ``execution``) to ``runs`` column keys."""
    if obj.get("event") != "execution":
        return None
    run_id = obj.get("run_id")
    if not run_id:
        return None

    timing = obj.get("timing") if isinstance(obj.get("timing"), dict) else {}
    cost = obj.get("cost") if isinstance(obj.get("cost"), dict) else {}

    ts = obj.get("timestamp_utc") or obj.get("timestamp") or ""

    retrieval = obj.get("retrieval_yield_chunks")
    if retrieval is None:
        retrieval = obj.get("total_chunks_embedded")
    if retrieval is None:
        et = obj.get("execution_trace")
        if isinstance(et, dict):
            retrieval = et.get("total_chunks")

    kb_inst = obj.get("kb_instrumentation")
    kb_score = obj.get("kb_score")
    kb_fired = obj.get("kb_fired")
    if kb_score is None and isinstance(kb_inst, dict):
        kb_score = kb_inst.get("score")
    if kb_fired is None and isinstance(kb_inst, dict):
        ar = kb_inst.get("agent_ran")
        kb_fired = ar if ar is not None else kb_inst.get("kb_fired")

    return {
        "run_id": str(run_id),
        "session_id": obj.get("session_id"),
        "timestamp_utc": ts,
        "query": obj.get("query"),
        "mode": obj.get("mode"),
        "report_type": obj.get("report_type"),
        "complexity": obj.get("complexity"),
        "primary_entity": obj.get("primary_entity"),
        "entities": obj.get("entities"),
        "economist_ran": obj.get("economist_ran"),
        "scout_key": obj.get("scout_key"),
        "corpus_state": obj.get("corpus_state"),
        "retrieval_yield_chunks": int(retrieval or 0),
        "discover_candidate_urls_admitted": int(
            obj.get("discover_candidate_urls_admitted") or 0
        ),
        "urls_fetched": int(obj.get("urls_fetched") or 0),
        "iterations_run": int(obj.get("iterations_run") or 0),
        "economist_seconds": timing.get("economist_seconds"),
        "analyst_seconds": timing.get("analyst_seconds"),
        "author_seconds": timing.get("author_seconds"),
        "total_latency_seconds": obj.get("latency_seconds"),
        "total_cost_usd": cost.get("total_cost_usd"),
        "total_input_tokens": cost.get("total_input_tokens"),
        "total_output_tokens": cost.get("total_output_tokens"),
        "output_word_count": obj.get("output_word_count"),
        "final_output_preview": obj.get("final_output_preview"),
        "kb_score": kb_score,
        "kb_fired": kb_fired,
        "useful_content": obj.get("useful_content"),
    }


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT PRIMARY KEY,
    session_id      TEXT,
    timestamp_utc   TEXT,
    query           TEXT,
    mode            TEXT,
    report_type     TEXT,
    complexity      TEXT,
    primary_entity  TEXT,
    entities        TEXT,
    economist_ran   INTEGER,
    scout_key       TEXT,
    corpus_state    TEXT,
    retrieval_yield_chunks INTEGER,
    discover_candidate_urls_admitted INTEGER,
    urls_fetched    INTEGER,
    iterations_run  INTEGER,
    economist_seconds   REAL,
    analyst_seconds     REAL,
    author_seconds      REAL,
    total_latency_seconds REAL,
    total_cost_usd      REAL,
    total_input_tokens  INTEGER,
    total_output_tokens INTEGER,
    output_word_count   INTEGER,
    final_output_preview TEXT,
    kb_score            REAL,
    kb_fired            INTEGER,
    useful_content      INTEGER
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    first_seen_utc  TEXT,
    last_seen_utc   TEXT,
    run_count       INTEGER
);
"""

_DEFAULT_TELEMETRY_DB = "proplex.db"


def telemetry_db_path() -> Path:
    """Default SQLite path for run telemetry (``PROPLEX_TELEMETRY_DB`` overrides)."""
    return Path(os.environ.get("PROPLEX_TELEMETRY_DB", _DEFAULT_TELEMETRY_DB))


def init_db(db_path: str | Path | None = None) -> None:
    """
    Create the SQLite database file and apply schema if tables are missing.
    """
    path = Path(db_path) if db_path is not None else telemetry_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
        run_columns = {
            str(row[1]) for row in conn.execute("PRAGMA table_info(runs)").fetchall()
        }
        if "discover_candidate_urls_admitted" not in run_columns:
            conn.execute(
                "ALTER TABLE runs ADD COLUMN "
                "discover_candidate_urls_admitted INTEGER"
            )
        conn.commit()
    finally:
        conn.close()


def ensure_telemetry_schema(db_path: str | Path | None = None) -> Path:
    """Resolve the telemetry DB path and ensure tables exist. Returns the resolved path."""
    path = Path(db_path) if db_path is not None else telemetry_db_path()
    init_db(path)
    return path


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_int(value: Any) -> int | None:
    if value is None:
        return None
    return 1 if bool(value) else 0


def insert_run(
    run_data: dict[str, Any],
    *,
    db_path: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """
    Insert or replace one row in ``runs``. Keys should match ``RUN_COLUMNS``;
    missing optional fields become SQL NULL; integer/real fields are coerced safely.
    """
    rid = run_data.get("run_id")
    if not rid:
        raise ValueError("insert_run requires a non-empty run_id")

    entities = run_data.get("entities")
    if isinstance(entities, (list, tuple, dict)):
        entities_val = json.dumps(entities, ensure_ascii=True)
    else:
        entities_val = entities

    row: dict[str, Any] = {
        "run_id": str(rid),
        "session_id": run_data.get("session_id"),
        "timestamp_utc": run_data.get("timestamp_utc"),
        "query": run_data.get("query"),
        "mode": run_data.get("mode"),
        "report_type": run_data.get("report_type"),
        "complexity": run_data.get("complexity"),
        "primary_entity": run_data.get("primary_entity"),
        "entities": entities_val,
        "economist_ran": run_data.get("economist_ran"),
        "scout_key": run_data.get("scout_key"),
        "corpus_state": run_data.get("corpus_state"),
        "retrieval_yield_chunks": run_data.get("retrieval_yield_chunks"),
        "discover_candidate_urls_admitted": run_data.get(
            "discover_candidate_urls_admitted"
        ),
        "urls_fetched": run_data.get("urls_fetched"),
        "iterations_run": run_data.get("iterations_run"),
        "economist_seconds": run_data.get("economist_seconds"),
        "analyst_seconds": run_data.get("analyst_seconds"),
        "author_seconds": run_data.get("author_seconds"),
        "total_latency_seconds": run_data.get("total_latency_seconds"),
        "total_cost_usd": run_data.get("total_cost_usd"),
        "total_input_tokens": run_data.get("total_input_tokens"),
        "total_output_tokens": run_data.get("total_output_tokens"),
        "output_word_count": run_data.get("output_word_count"),
        "final_output_preview": run_data.get("final_output_preview"),
        "kb_score": run_data.get("kb_score"),
        "kb_fired": run_data.get("kb_fired"),
        "useful_content": run_data.get("useful_content"),
    }

    if isinstance(row["economist_ran"], bool):
        row["economist_ran"] = _bool_int(row["economist_ran"])
    elif row["economist_ran"] is not None:
        row["economist_ran"] = _optional_int(row["economist_ran"])

    for k in ("kb_fired", "useful_content"):
        if isinstance(row[k], bool):
            row[k] = _bool_int(row[k])
        elif row[k] is not None:
            row[k] = _optional_int(row[k])

    for k in (
        "retrieval_yield_chunks",
        "discover_candidate_urls_admitted",
        "urls_fetched",
        "iterations_run",
        "total_input_tokens",
        "total_output_tokens",
        "output_word_count",
    ):
        if row[k] is not None:
            row[k] = _optional_int(row[k])

    for k in ("economist_seconds", "analyst_seconds", "author_seconds", "total_latency_seconds", "total_cost_usd", "kb_score"):
        if row[k] is not None:
            row[k] = _optional_float(row[k])

    cols = ", ".join(RUN_COLUMNS)
    placeholders = ", ".join("?" * len(RUN_COLUMNS))
    sql = f"INSERT OR REPLACE INTO runs ({cols}) VALUES ({placeholders})"
    values = tuple(row[c] for c in RUN_COLUMNS)

    own_conn = conn is None
    if conn is None:
        resolved = Path(db_path) if db_path is not None else telemetry_db_path()
        conn = sqlite3.connect(resolved)
    try:
        conn.execute(sql, values)
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def upsert_session(
    session_id: str | None,
    timestamp_utc: str,
    *,
    db_path: str | Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """
    Insert a session or bump ``run_count`` and set ``last_seen_utc`` on conflict.
    ``first_seen_utc`` is set only on first insert.
    """
    sid = (session_id or "").strip()
    if not sid:
        return
    ts = timestamp_utc or ""

    sql = """
    INSERT INTO sessions (session_id, first_seen_utc, last_seen_utc, run_count)
    VALUES (?, ?, ?, 1)
    ON CONFLICT(session_id) DO UPDATE SET
        last_seen_utc = excluded.last_seen_utc,
        run_count = sessions.run_count + 1
    """

    own_conn = conn is None
    if conn is None:
        resolved = Path(db_path) if db_path is not None else telemetry_db_path()
        conn = sqlite3.connect(resolved)
    try:
        conn.execute(sql, (sid, ts, ts))
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()
