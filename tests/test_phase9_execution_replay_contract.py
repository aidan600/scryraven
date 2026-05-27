from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from scripts.summarize_economist_telemetry import summarize_log
from tests.replay_jsonl_utils import load_jsonl_dict_rows

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "phase9_execution_replay.jsonl"
MAX_FIXTURE_BYTES = 12 * 1024
MAX_EXECUTION_ROWS = 5

EXPECTED_RUN_IDS = [
    "phase9-clean-quant-shadow",
    "phase9-active-pre-analyst-skip",
    "phase9-historical-minimal",
    "phase9-blocked-shadow-control",
]

FORBIDDEN_FIELD_NAMES = {
    "conversation",
    "final_answer",
    "final_output",
    "golden_answer",
    "golden_report",
    "messages",
    "model_output",
    "prompt",
    "provider_payload",
    "provider_response",
    "raw_model_output",
    "raw_prompt",
    "raw_transcript",
    "report_text",
    "system_prompt",
    "transcript",
    "user_prompt",
}

FORBIDDEN_VALUE_MARKERS = (
    "BEGIN TRANSCRIPT",
    "FINAL REPORT",
    "GOLDEN ANSWER",
    "MODEL OUTPUT",
    "PROVIDER PAYLOAD",
    "RAW PROMPT",
    "RAW TRANSCRIPT",
    "SYSTEM PROMPT",
    "USER PROMPT",
)

SAFETY_ONLY_FIELDS = {
    "analyst_skipped_after_economist",
    "author_received_analyst_packet_marker",
    "author_received_economist_framework",
    "author_received_raw_quant_packet",
    "economist_code_execution_requested",
    "economist_output_used_as_analysis",
    "quant_retrieval_sufficiency_valid",
    "source_domain_counts",
    "source_tier_counts",
}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows),
        encoding="utf-8",
    )


def _iter_keys_and_values(value: Any) -> list[tuple[str | None, Any]]:
    found: list[tuple[str | None, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append((key, item))
            found.extend(_iter_keys_and_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_iter_keys_and_values(item))
    else:
        found.append((None, value))
    return found


def _assert_no_scrubbed_content_markers(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for key, value in _iter_keys_and_values(row):
            assert key not in FORBIDDEN_FIELD_NAMES
            if isinstance(value, str):
                upper_value = value.upper()
                assert not any(
                    marker in upper_value for marker in FORBIDDEN_VALUE_MARKERS
                )


def _assert_no_safety_anomalies(summary: dict[str, Any]) -> None:
    anomalies = {
        field: count
        for field, count in summary["safety_anomaly_counts"].items()
        if count
    }
    assert anomalies == {}


def test_phase9_execution_replay_fixture_is_small_jsonl_and_scrubbed() -> None:
    raw = FIXTURE_PATH.read_bytes()
    rows = load_jsonl_dict_rows(FIXTURE_PATH)

    assert FIXTURE_PATH.suffix == ".jsonl"
    assert len(raw) <= MAX_FIXTURE_BYTES
    assert len(rows) <= MAX_EXECUTION_ROWS
    assert all(row.get("event") == "execution" for row in rows)
    assert [row.get("run_id") for row in rows] == EXPECTED_RUN_IDS
    assert raw[:1] != b"["
    _assert_no_scrubbed_content_markers(rows)


@pytest.mark.parametrize("raw_line", ["{not-json", "[]"])
def test_phase9_execution_replay_loader_rejects_invalid_rows(
    tmp_path: Path,
    raw_line: str,
) -> None:
    log_path = tmp_path / "invalid_replay.jsonl"
    log_path.write_text(raw_line, encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_jsonl_dict_rows(log_path)


def test_phase9_execution_replay_summarizer_contract() -> None:
    rows = load_jsonl_dict_rows(FIXTURE_PATH)
    summary = summarize_log(FIXTURE_PATH)
    audit = summary["pre_analyst_retrieval_gate_audit"]
    readiness = summary["readiness"]

    assert summary["total_execution_events"] == len(rows)
    assert summary["total_lines_read"] == len(rows)
    assert summary["malformed_rows"] == 0
    assert summary["non_execution_rows"] == 0
    _assert_no_safety_anomalies(summary)

    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "missing"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["missing"] == 1
    assert summary["boolean_counts"]["high_stakes_quant_detected"]["missing"] == 1

    assert audit["active_pre_analyst_skip_count"] == 1
    assert audit["analyst_skipped_counts"]["true"] == 1
    assert audit["analyst_skipped_counts"]["missing"] == 1
    assert audit["analyst_skip_reason_counts"]["corpus_off_topic"] == 1
    assert (
        audit["post_economist_separate_counts"][
            "analyst_skipped_after_economist:true"
        ]
        == 0
    )
    assert (
        audit["post_economist_separate_counts"][
            "economist_output_used_as_analysis:true"
        ]
        == 0
    )

    detail = audit["skip_reason_details"]["corpus_off_topic"]
    assert detail["source_tier_counts"]["official"] == 1
    assert detail["source_tier_counts"]["independent"] == 2
    assert detail["source_tier_counts"]["unknown"] == 1
    assert detail["top_source_domains"]["reference.example"] == 2

    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["negative_control_blocked_counts"][
        "high_stakes_guardrail_blocked"
    ] == 1
    assert readiness["negative_control_blocked_counts"][
        "retrieval_sufficiency_blocked"
    ] == 1
    assert summary["quant_retrieval_sufficiency_valid_counts"]["false"] == 1


def test_phase9_execution_replay_sqlite_mapping_remains_compact() -> None:
    rows = load_jsonl_dict_rows(FIXTURE_PATH)

    for row in rows:
        mapped = execution_jsonl_to_run_row(row)
        assert mapped is not None
        assert set(mapped) == set(RUN_COLUMNS)
        assert mapped["run_id"] == row["run_id"]
        assert "execution_trace" not in mapped
        assert not (SAFETY_ONLY_FIELDS & set(mapped))

    nested_row = rows[1]
    nested_mapped = execution_jsonl_to_run_row(nested_row)
    assert nested_mapped is not None
    assert nested_mapped["run_id"] == "phase9-active-pre-analyst-skip"
    assert nested_mapped["corpus_state"] == "weak"
    assert nested_mapped["retrieval_yield_chunks"] == 0

    historical_row = rows[2]
    historical_mapped = execution_jsonl_to_run_row(historical_row)
    assert historical_mapped is not None
    assert historical_mapped["timestamp_utc"] == "2026-04-01T12:00:00Z"


def test_replay_summarizer_ignores_active_source_class_recovery_trace_fields(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "active_source_class_recovery.jsonl"
    active_trace = {
        "active_source_class_recovery_considered": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_queries": [
            "Care Program official current eligibility requirements rules government",
        ],
        "active_source_class_recovery_result_count": 1,
        "active_source_class_recovery_new_url_count": 1,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_search_depth": "basic",
        "active_source_class_recovery_attempt_count": 1,
        "source_class_recovery_recommended": False,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [],
        "source_class_recovery_reason": None,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": [],
        "analyst_skipped_after_economist": False,
        "economist_output_used_as_analysis": False,
        "economist_code_execution_requested": False,
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
    }
    row = {
        "event": "execution",
        "run_id": "phase17h-active-source-class-recovery",
        "session_id": "phase17h-session",
        "timestamp_utc": "2026-05-18T12:00:00Z",
        "query": "current official rules for care program",
        "mode": "Balanced",
        "report_type": "general_research",
        "complexity": "medium",
        "corpus_state": "HEALTHY",
        "execution_trace": active_trace,
    }
    _write_jsonl(log_path, [row])

    rows = load_jsonl_dict_rows(log_path)
    summary = summarize_log(log_path)
    mapped = execution_jsonl_to_run_row(row)

    assert rows == [row]
    assert summary["total_execution_events"] == 1
    assert summary["total_lines_read"] == 1
    assert summary["malformed_rows"] == 0
    _assert_no_safety_anomalies(summary)
    assert mapped is not None
    assert set(mapped) == set(RUN_COLUMNS)
    assert "execution_trace" not in mapped
    assert not any(key.startswith("active_source_class_recovery") for key in mapped)


def test_phase9_execution_replay_inline_anomaly_row_is_flagged(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "inline_anomaly.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "phase9-inline-anomaly-control",
                "analyst_skipped_after_economist": True,
                "economist_output_used_as_analysis": True,
            }
        ],
    )

    summary = summarize_log(log_path)

    assert summary["safety_anomaly_counts"]["analyst_skipped_after_economist"] == 1
    assert summary["safety_anomaly_counts"]["economist_output_used_as_analysis"] == 1
    assert summary["readiness"]["live_behavior_anomaly_counts"][
        "analyst_skipped_after_economist"
    ] == 1
    assert summary["readiness"]["live_behavior_anomaly_counts"][
        "economist_output_used_as_analysis"
    ] == 1
    with pytest.raises(AssertionError):
        _assert_no_safety_anomalies(summary)
