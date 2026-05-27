from __future__ import annotations

import json
from pathlib import Path

from scripts.eval_harness_status import (
    classify_manifest,
    classify_manifest_row,
    match_lifecycle_events,
    pipeline_status_from_events,
)


def test_exit_code_zero_and_run_completed_are_completed(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("synthetic report", encoding="utf-8")

    status = classify_manifest_row(
        {
            "run_id": "run-1",
            "query": "synthetic query",
            "exit_code": "0",
            "output_file": str(report),
        },
        lifecycle_events=[{"event": "run_completed", "run_id": "run-1", "error": None}],
    )

    assert status["exit_code"] == 0
    assert status["process_status"] == "completed"
    assert status["pipeline_status"] == "completed"
    assert status["report_path_exists"] is True


def test_exit_code_one_without_lifecycle_is_process_failed_pipeline_not_started(
    tmp_path: Path,
) -> None:
    status = classify_manifest_row(
        {"run_id": "run-2", "exit_code": "1", "output_file": str(tmp_path / "missing.md")},
        lifecycle_events=[],
    )

    assert status["process_status"] == "failed"
    assert status["pipeline_status"] == "not_started"
    assert status["report_path_exists"] is False


def test_legacy_minus_one_with_run_completed_is_unknown_process_completed_pipeline() -> None:
    status = classify_manifest_row(
        {"run_id": "legacy-run", "exit_code": "-1"},
        lifecycle_events=[{"event": "run_completed", "run_id": "legacy-run", "error": None}],
    )

    assert status["exit_code"] == -1
    assert status["process_status"] == "unknown"
    assert status["pipeline_status"] == "completed"


def test_stderr_presence_with_exit_code_zero_does_not_fail_process() -> None:
    status = classify_manifest_row(
        {"run_id": "stderr-run", "exit_code": "0", "stderr": "NativeCommandError text"},
        lifecycle_events=[{"event": "run_completed", "run_id": "stderr-run", "error": None}],
    )

    assert status["stderr_present"] is True
    assert status["process_status"] == "completed"
    assert status["pipeline_status"] == "completed"


def test_run_failed_lifecycle_marks_pipeline_failed() -> None:
    assert (
        pipeline_status_from_events(
            [{"event": "run_failed", "run_id": "failed-run", "error": "boom"}]
        )
        == "failed"
    )


def test_missing_jsonl_lifecycle_evidence_is_unknown() -> None:
    assert pipeline_status_from_events(None) == "unknown"


def test_query_match_without_manifest_times_is_not_started() -> None:
    events = [
        {
            "event": "run_completed",
            "query_preview": "synthetic query",
            "timestamp_utc": "2026-05-12T23:57:13+00:00",
            "error": None,
        }
    ]

    assert match_lifecycle_events({"query": "synthetic query"}, events) == []
    assert pipeline_status_from_events([]) == "not_started"


def test_manifest_classification_can_match_lifecycle_by_query_time_window(
    tmp_path: Path,
) -> None:
    report = tmp_path / "CB-002.md"
    report.write_text("synthetic report", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "\n".join(
            [
                "run_id,mode,query,output_file,started_at,finished_at,exit_code",
                (
                    '"CB-002","Balanced","compare cost per passenger mile MD-80 vs 777-300",'
                    f'"{report}","2026-05-12T16:55:24-07:00",'
                    '"2026-05-12T16:57:13-07:00",-1'
                ),
            ]
        ),
        encoding="utf-8",
    )
    log = tmp_path / "execution_log.jsonl"
    rows = [
        {
            "event": "run_started",
            "run_id": "uuid-run",
            "query_preview": "compare cost per passenger mile MD-80 vs 777-300",
            "timestamp_utc": "2026-05-12T23:55:25+00:00",
        },
        {
            "event": "run_completed",
            "run_id": "uuid-run",
            "query_preview": "compare cost per passenger mile MD-80 vs 777-300",
            "timestamp_utc": "2026-05-12T23:57:13+00:00",
            "error": None,
        },
    ]
    log.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    [status] = classify_manifest(manifest, execution_jsonl_path=log)

    assert status["process_status"] == "unknown"
    assert status["pipeline_status"] == "completed"
    assert status["report_path_exists"] is True


def test_manifest_classification_matches_excel_serial_time_window(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "\n".join(
            [
                "run_id,mode,query,output_file,started_at,finished_at,exit_code",
                (
                    '"CB-002","Balanced","compare cost per passenger mile MD-80 vs 777-300",'
                    '"missing.md",46154.99680685185,46154.99807440972,-1'
                ),
            ]
        ),
        encoding="utf-8",
    )
    log = tmp_path / "execution_log.jsonl"
    rows = [
        {
            "event": "run_started",
            "run_id": "uuid-run",
            "query_preview": "compare cost per passenger mile MD-80 vs 777-300",
            "timestamp_utc": "2026-05-12T23:55:24+00:00",
        },
        {
            "event": "run_completed",
            "run_id": "uuid-run",
            "query_preview": "compare cost per passenger mile MD-80 vs 777-300",
            "timestamp_utc": "2026-05-12T23:57:13+00:00",
            "error": None,
        },
    ]
    log.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    [status] = classify_manifest(manifest, execution_jsonl_path=log, root=tmp_path)

    assert status["process_status"] == "unknown"
    assert status["pipeline_status"] == "completed"


def test_invalid_numeric_and_date_like_manifest_times_do_not_match_lifecycle() -> None:
    events = [
        {
            "event": "run_completed",
            "query_preview": "synthetic query",
            "timestamp_utc": "2026-05-12T23:57:13+00:00",
            "error": None,
        }
    ]
    row = {
        "query": "synthetic query",
        "started_at": "42",
        "finished_at": "2026-05-12-ish",
    }

    matches = match_lifecycle_events(row, events)

    assert matches == []
    assert pipeline_status_from_events(matches) == "not_started"
    assert pipeline_status_from_events(None) == "unknown"
