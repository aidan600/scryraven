#!/usr/bin/env python3
"""
Migrate historical ``output/execution_log.jsonl`` rows into SQLite (runs + sessions).

Run from the repo root::

    python scripts/migrate_jsonl_to_sqlite.py

Uses ``core.db.insert_run`` and ``core.db.upsert_session``. By default clears
``runs`` and ``sessions`` then reloads from JSONL so re-running stays consistent.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.db import execution_jsonl_to_run_row, init_db, insert_run, upsert_session

DEFAULT_JSONL = ROOT / "output" / "execution_log.jsonl"
DEFAULT_DB = ROOT / "proplex.db"


def migrate(
    *,
    jsonl_path: Path,
    db_path: Path,
    clear_tables: bool = True,
) -> tuple[int, int, int]:
    """
    Returns ``(migrated_runs, lines_skipped_json, lines_non_execution)``.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    migrated = 0
    skipped_json = 0
    non_execution = 0

    try:
        if clear_tables:
            conn.execute("DELETE FROM runs")
            conn.execute("DELETE FROM sessions")
            conn.commit()

        text = jsonl_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped_json += 1
                continue
            if obj.get("event") != "execution":
                if obj.get("event") is not None:
                    non_execution += 1
                continue

            row = execution_jsonl_to_run_row(obj)
            if row is None:
                continue

            insert_run(row, conn=conn)
            upsert_session(row.get("session_id"), row.get("timestamp_utc") or "", conn=conn)
            migrated += 1

        conn.commit()
    finally:
        conn.close()

    return migrated, skipped_json, non_execution


def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate execution_log.jsonl into SQLite.")
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=DEFAULT_JSONL,
        help=f"Path to execution_log.jsonl (default: {DEFAULT_JSONL})",
    )
    ap.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})",
    )
    ap.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not delete existing runs/sessions before import (may duplicate session counts).",
    )
    args = ap.parse_args()

    jsonl_path = args.jsonl.resolve()
    db_path = args.db.resolve()

    if not jsonl_path.is_file():
        print(f"Missing JSONL file: {jsonl_path}")
        sys.exit(1)

    migrated, skipped_json, non_exec = migrate(
        jsonl_path=jsonl_path,
        db_path=db_path,
        clear_tables=not args.no_clear,
    )

    print(f"Migrated {migrated} execution rows into {db_path}")
    if skipped_json:
        print(f"  (skipped {skipped_json} invalid JSON lines)")
    if non_exec:
        print(f"  (ignored {non_exec} non-execution event lines with an event field)")


if __name__ == "__main__":
    main()
