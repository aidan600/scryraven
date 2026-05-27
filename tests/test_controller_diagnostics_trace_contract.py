from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from scripts import aggregate_run_quality
from scripts.summarize_economist_telemetry import summarize_log
from tests.controller_diagnostics_contract_utils import (
    ALLOWED_FUTURE_TRACE_KEY_DELTA,
    assert_execution_trace_payload_contract,
    assert_jsonl_event_controller_payload_contract,
    assert_no_top_level_controller_payload,
    assert_session_controller_payload_contract,
    assert_trace_key_delta_only_controller_diagnostics,
    disallowed_payload_keys,
    trace_key_delta,
)
from tests.replay_jsonl_utils import load_jsonl_dict_rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows),
        encoding="utf-8",
    )


def _synthetic_execution_event() -> dict[str, Any]:
    return {
        "event": "execution",
        "run_id": "synthetic-controller-diagnostics-contract",
        "session_id": "synthetic-session",
        "timestamp_utc": "2026-05-19T12:00:00Z",
        "query": "synthetic offline controller diagnostics compatibility row",
        "mode": "Balanced",
        "report_type": "general_research",
        "complexity": "medium",
        "corpus_state": "healthy",
        "execution_trace": {
            "total_chunks": 3,
            "analyst_skipped": False,
            "controller_diagnostics": {
                "schema_version": "controller_diagnostics_v1",
                "passive_only": True,
                "diagnostic_only": True,
                "authority": "none",
                "source": "posthoc_execution_trace",
                "run_plan": {
                    "stage_count": 1,
                    "disposition_counts": {"required": 1},
                },
                "task_ledger": {
                    "record_count": 1,
                    "status_counts": {"completed": 1},
                },
                "planned_vs_observed": {
                    "status_counts": {"observed_completed": 1},
                    "failure_count": 0,
                    "stages": [],
                    "failures": [],
                },
                "observed_summary": {
                    "observed_stage_count": 1,
                    "observed_stage_ids": ["route_intent"],
                    "observed_status_counts": {"completed": 1},
                },
            },
        },
    }


def test_nested_controller_diagnostics_maps_without_run_columns_change() -> None:
    row = _synthetic_execution_event()
    run_columns_before = tuple(RUN_COLUMNS)

    mapped = execution_jsonl_to_run_row(row)

    assert tuple(RUN_COLUMNS) == run_columns_before
    assert mapped is not None
    assert set(mapped) == set(RUN_COLUMNS)
    assert mapped["run_id"] == row["run_id"]
    assert mapped["retrieval_yield_chunks"] == 3
    assert "execution_trace" not in mapped
    assert "controller_diagnostics" not in mapped
    assert_jsonl_event_controller_payload_contract(row)
    assert_no_top_level_controller_payload(mapped)


def test_top_level_controller_diagnostics_jsonl_event_is_invalid() -> None:
    row = _synthetic_execution_event()
    row["controller_diagnostics"] = {"must": "not-be-top-level"}

    assert disallowed_payload_keys(row) == {"controller_diagnostics"}
    with pytest.raises(AssertionError):
        assert_jsonl_event_controller_payload_contract(row)


def test_session_allows_only_nested_trace_controller_diagnostics() -> None:
    session = {
        "id": "synthetic-session",
        "run_id": "synthetic-controller-diagnostics-contract",
        "execution_trace": {
            "controller_diagnostics": {
                "schema_version": "controller_diagnostics_v1",
            },
        },
    }

    assert_session_controller_payload_contract(session)

    top_level_payload = dict(session)
    top_level_payload["controller_diagnostics"] = {"must": "not-be-top-level"}
    with pytest.raises(AssertionError):
        assert_session_controller_payload_contract(top_level_payload)


def test_trace_key_delta_allowlist_only_controller_diagnostics() -> None:
    baseline_trace = {"queries_per_iteration": {"1": ["synthetic"]}}
    future_trace = {
        **baseline_trace,
        "controller_diagnostics": {"schema_version": "controller_diagnostics_v1"},
    }

    assert trace_key_delta(future_trace, baseline_trace) == (
        ALLOWED_FUTURE_TRACE_KEY_DELTA
    )
    assert_trace_key_delta_only_controller_diagnostics(future_trace, baseline_trace)

    for bad_key in (
        "controller_state",
        "controller_payload",
        "controller_diagnostics_extra",
        "run_controller",
        "stage_ledger",
        "stage_ledger_payload",
        "evidence_registry",
        "evidence_registry_payload",
    ):
        bad_trace = {**baseline_trace, bad_key: {"must": "stay-disallowed"}}
        with pytest.raises(AssertionError):
            assert_execution_trace_payload_contract(bad_trace)
        with pytest.raises(AssertionError):
            assert_trace_key_delta_only_controller_diagnostics(
                bad_trace,
                baseline_trace,
            )


def test_aggregate_run_quality_summarizes_nested_controller_diagnostics_safely(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_synthetic_execution_event()])
    monkeypatch.setattr(aggregate_run_quality, "LOG", log_path)
    monkeypatch.setattr(
        aggregate_run_quality,
        "KB_TRIGGERS",
        tmp_path / "missing_kb_triggers.jsonl",
    )

    aggregate_run_quality.main()
    out = capsys.readouterr().out

    assert "No execution events found." not in out
    assert "=== Controller diagnostics (last 1 runs) ===" in out
    assert "controller_diagnostics_payload_rows: 1" in out
    assert "controller_diagnostics_missing_legacy_or_omitted: 0" in out
    assert "schema_version: {'controller_diagnostics_v1': 1}" in out
    assert "authority: {'none': 1}" in out
    assert "run_plan_disposition_counts: {'required': 1}" in out
    assert "planned_vs_observed_status_counts: {'observed_completed': 1}" in out
    assert "observed_stage_ids" not in out


def test_summarize_economist_telemetry_ignores_nested_controller_diagnostics(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_synthetic_execution_event()])

    summary = summarize_log(log_path)

    assert summary["total_execution_events"] == 1
    assert summary["total_lines_read"] == 1
    assert summary["malformed_rows"] == 0


def test_replay_jsonl_loader_accepts_nested_controller_diagnostics(
    tmp_path: Path,
) -> None:
    row = _synthetic_execution_event()
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [row])

    loaded = load_jsonl_dict_rows(log_path)

    assert loaded == [row]
    assert_jsonl_event_controller_payload_contract(loaded[0])
