"""Offline eval-harness process and pipeline status contract.

This module classifies existing manifest rows and execution_log.jsonl lifecycle
events. It does not run ProPlex, Streamlit, providers, models, or searches.

Future PowerShell wrappers should capture ``$LASTEXITCODE`` immediately after a
direct native invocation. If they use ``Start-Process``, they should use
``-Wait -PassThru`` and read ``.ExitCode``.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TIME_MATCH_TOLERANCE = timedelta(seconds=5)
MIN_EXCEL_SERIAL_DATETIME = 25569.0  # 1970-01-01 in Excel's 1900 date system.
MAX_EXCEL_SERIAL_DATETIME = 80000.0

PROCESS_STATUSES = {"completed", "failed", "timeout", "launch_failed", "unknown"}
PIPELINE_STATUSES = {"completed", "failed", "not_started", "unknown"}


def parse_exit_code(value: Any) -> int | None:
    """Parse manifest exit_code values, keeping missing/blank values nullable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def process_status_from_row(row: dict[str, Any]) -> str:
    """Classify wrapper/native-process status from manifest-like fields."""
    explicit = str(row.get("process_status") or "").strip()
    if explicit in PROCESS_STATUSES:
        return explicit
    if _truthy(row.get("timeout")) or _truthy(row.get("timed_out")):
        return "timeout"
    if _truthy(row.get("launch_failed")):
        return "launch_failed"

    exit_code = parse_exit_code(row.get("exit_code"))
    if exit_code is None or exit_code == -1:
        return "unknown"
    if exit_code == 0:
        return "completed"
    return "failed"


def pipeline_status_from_events(events: list[dict[str, Any]] | None) -> str:
    """Classify pipeline lifecycle status from execution_log.jsonl events.

    ``None`` means lifecycle evidence was unavailable. An empty list means the
    evidence source was available but no matching run lifecycle was found.
    """
    if events is None:
        return "unknown"
    if not events:
        return "not_started"

    for event in reversed(events):
        event_name = event.get("event")
        if event_name == "run_failed":
            return "failed"
        if event_name == "run_completed":
            return "completed" if not event.get("error") else "failed"
    return "unknown"


def classify_manifest_row(
    row: dict[str, Any],
    *,
    lifecycle_events: list[dict[str, Any]] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return the offline status contract for one manifest-like row."""
    output_file = str(row.get("output_file") or row.get("report_path") or "").strip()
    stderr_ref = str(row.get("stderr") or row.get("stderr_file") or row.get("stderr_text") or "").strip()

    return {
        "run_id": row.get("run_id"),
        "query": row.get("query"),
        "exit_code": parse_exit_code(row.get("exit_code")),
        "process_status": process_status_from_row(row),
        "pipeline_status": pipeline_status_from_events(lifecycle_events),
        "report_path_exists": _path_exists(output_file, root=root),
        "stderr_present": bool(stderr_ref),
    }


def classify_manifest(
    manifest_path: Path,
    *,
    execution_jsonl_path: Path | None = None,
    root: Path = ROOT,
) -> list[dict[str, Any]]:
    """Classify every row in a manifest CSV using optional lifecycle evidence."""
    rows = _read_manifest_rows(manifest_path)
    events = read_jsonl_events(execution_jsonl_path) if execution_jsonl_path else None
    return [
        classify_manifest_row(
            row,
            lifecycle_events=match_lifecycle_events(row, events),
            root=root,
        )
        for row in rows
    ]


def read_jsonl_events(path: Path | None) -> list[dict[str, Any]] | None:
    """Read JSONL events; return None when the evidence source is unavailable."""
    if path is None or not path.exists():
        return None

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def match_lifecycle_events(
    row: dict[str, Any],
    events: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Find lifecycle events for a manifest row by run_id or query/time window."""
    if events is None:
        return None

    run_id = str(row.get("run_id") or "").strip()
    if run_id:
        matches = [event for event in events if str(event.get("run_id") or "").strip() == run_id]
        if matches:
            return matches

    query = str(row.get("query") or "").strip()
    if not query:
        return []

    started_at_raw = _parse_datetime(row.get("started_at"))
    finished_at_raw = _parse_datetime(row.get("finished_at"))
    if started_at_raw is None or finished_at_raw is None:
        return []

    started_at = started_at_raw - TIME_MATCH_TOLERANCE
    finished_at = finished_at_raw + TIME_MATCH_TOLERANCE

    matched: list[dict[str, Any]] = []
    for event in events:
        event_query = str(event.get("query") or event.get("query_preview") or "").strip()
        if event_query != query:
            continue
        event_time = _parse_datetime(event.get("timestamp_utc"))
        if event_time is None:
            continue
        if started_at <= event_time <= finished_at:
            matched.append(event)
    return matched


def _read_manifest_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _path_exists(path_text: str, *, root: Path) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = root / path
    return path.exists()


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        serial = float(text)
    except ValueError:
        serial = None
    if serial is not None and MIN_EXCEL_SERIAL_DATETIME <= serial <= MAX_EXCEL_SERIAL_DATETIME:
        return datetime(1899, 12, 30) + timedelta(days=serial)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
