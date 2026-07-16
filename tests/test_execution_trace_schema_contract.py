from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.db import execution_jsonl_to_run_row
from scripts.summarize_economist_telemetry import summarize_log
from tests.helpers.offline_ordinary_pipeline import (
    execution_event_from_log,
    run_post_retirement_ordinary_pipeline,
)

_MISSING = object()

PINNED_EXECUTION_ROW_FIELDS = (
    "run_id",
    "session_id",
    "timestamp_utc",
    "mode",
    "report_type",
    "complexity",
    "corpus_state",
    "analyst_skipped",
    "analyst_skip_reason",
    "analyst_skipped_after_economist",
    "analyst_after_economist_skip_reason",
    "economist_output_used_as_analysis",
    "economist_code_execution_requested",
    "quantitative_packet_present",
    "quantitative_packet_valid",
    "quantitative_packet_direct_use_eligible",
    "quantitative_packet_requires_analyst",
    "quant_retrieval_sufficiency_valid",
    "quant_retrieval_sufficiency_blockers",
    "economist_pre_analyst_skip_candidate_shadow",
    "economist_skip_eligible_shadow",
    "economist_skip_shadow_alignment",
    "author_quant_content_source",
    "author_received_raw_quant_packet",
    "author_received_economist_framework",
    "author_received_analyst_packet_marker",
    "source_tier_counts",
    "source_domain_counts",
    "response_displayable",
    "evidence_sufficient",
    "answer_class",
    "scout_skip_reason",
    "economist_preflight_allowed",
    "economist_preflight_block_reason",
    "economist_preflight_missing_entities",
    "missing_target_metric_directive_emitted",
    "author_system_prompt_key",
    "estimate_from_priors_requested",
    "estimate_from_priors_blocked_by_pre_analyst_gate",
)

BOOLEAN_SAFETY_FIELDS = (
    "analyst_skipped",
    "analyst_skipped_after_economist",
    "economist_output_used_as_analysis",
    "economist_code_execution_requested",
    "quantitative_packet_present",
    "quantitative_packet_valid",
    "quantitative_packet_direct_use_eligible",
    "quantitative_packet_requires_analyst",
    "quant_retrieval_sufficiency_valid",
    "economist_pre_analyst_skip_candidate_shadow",
    "economist_skip_eligible_shadow",
    "author_received_raw_quant_packet",
    "author_received_economist_framework",
    "author_received_analyst_packet_marker",
    "response_displayable",
    "evidence_sufficient",
    "missing_target_metric_directive_emitted",
    "estimate_from_priors_requested",
    "estimate_from_priors_blocked_by_pre_analyst_gate",
)


def _rich_execution_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row[field]
    trace = row.get("execution_trace")
    if isinstance(trace, dict) and field in trace:
        return trace[field]
    return _MISSING


def _safety_bool_label(row: dict[str, Any], field: str) -> str:
    value = _rich_execution_value(row, field)
    if value is _MISSING:
        return "missing"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "invalid"


def _assert_pinned_schema(row: dict[str, Any]) -> None:
    missing = [
        field
        for field in PINNED_EXECUTION_ROW_FIELDS
        if _rich_execution_value(row, field) is _MISSING
    ]
    assert missing == []

    for field in BOOLEAN_SAFETY_FIELDS:
        assert type(_rich_execution_value(row, field)) is bool, field

    blockers = _rich_execution_value(row, "quant_retrieval_sufficiency_blockers")
    assert isinstance(blockers, list)
    assert all(isinstance(blocker, str) for blocker in blockers)

    preflight_missing = _rich_execution_value(
        row,
        "economist_preflight_missing_entities",
    )
    assert isinstance(preflight_missing, list)
    assert all(isinstance(entity, str) for entity in preflight_missing)

    for field in ("source_tier_counts", "source_domain_counts"):
        counts = _rich_execution_value(row, field)
        assert isinstance(counts, dict), field
        assert all(isinstance(key, str) for key in counts), field
        assert all(isinstance(value, int) for value in counts.values()), field


def test_execution_jsonl_rich_trace_schema_contract_for_synthetic_runs(
    tmp_path: Path, monkeypatch: Any
) -> None:
    run_post_retirement_ordinary_pipeline(
        tmp_path / "healthy", monkeypatch, healthy=True
    )
    healthy = execution_event_from_log(tmp_path / "healthy" / "execution.jsonl")

    run_post_retirement_ordinary_pipeline(
        tmp_path / "weak", monkeypatch, healthy=False
    )
    weak = execution_event_from_log(tmp_path / "weak" / "execution.jsonl")

    quant_outcome, quant_harness = run_post_retirement_ordinary_pipeline(
        tmp_path / "quant",
        monkeypatch,
        report_type="quantitative_comparison",
        query_type="comparison",
    )
    quant = execution_event_from_log(tmp_path / "quant" / "execution.jsonl")

    for row in (healthy, weak, quant):
        _assert_pinned_schema(row)

    assert _rich_execution_value(healthy, "analyst_skipped") is False
    assert _rich_execution_value(weak, "analyst_skipped") is True
    assert _rich_execution_value(weak, "analyst_skip_reason") == "corpus_off_topic"
    assert _rich_execution_value(quant, "quantitative_packet_present") is False
    assert _rich_execution_value(quant, "quantitative_packet_valid") is False
    assert _rich_execution_value(quant, "economist_preflight_allowed") is None
    assert _rich_execution_value(quant, "economist_preflight_missing_entities") == []
    assert _rich_execution_value(quant, "economist_preflight_block_reason") == (
        "legacy_economist_ordinary_execution_retired"
    )
    assert _rich_execution_value(quant, "author_received_raw_quant_packet") is False
    assert _rich_execution_value(quant, "author_received_economist_framework") is False
    assert _rich_execution_value(quant, "economist_output_used_as_analysis") is False
    assert quant_outcome.execution_trace["economist_ran"] is False
    assert quant_outcome.execution_trace["timing"]["economist_seconds"] == 0.0
    assert quant_harness.economist_calls == []
    assert quant_harness.analyst_calls == 1
    assert quant_harness.author_prompts


def test_historical_execution_row_missing_safety_fields_stays_unknown(
    tmp_path: Path,
) -> None:
    historical_row = {
        "event": "execution",
        "run_id": "historical-minimal",
        "session_id": "session-historical",
        "timestamp_utc": "2026-04-01T12:00:00+00:00",
        "mode": "Balanced",
        "report_type": "general_research",
        "complexity": "low",
        "corpus_state": "healthy",
    }
    log_path = tmp_path / "historical.jsonl"
    log_path.write_text(json.dumps(historical_row) + "\n", encoding="utf-8")

    for field in BOOLEAN_SAFETY_FIELDS:
        assert _safety_bool_label(historical_row, field) == "missing"

    summary = summarize_log(log_path)
    assert summary["total_execution_events"] == 1
    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "missing"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["missing"] == 1
    assert summary["quant_retrieval_sufficiency_valid_counts"]["missing"] == 1
    assert execution_jsonl_to_run_row(historical_row)["run_id"] == "historical-minimal"


def test_sqlite_summary_is_not_the_complete_safety_trace(
    tmp_path: Path, monkeypatch: Any
) -> None:
    run_post_retirement_ordinary_pipeline(
        tmp_path / "quant",
        monkeypatch,
        report_type="quantitative_comparison",
        query_type="comparison",
    )
    row = execution_event_from_log(tmp_path / "quant" / "execution.jsonl")

    sqlite_row = execution_jsonl_to_run_row(row)
    assert sqlite_row is not None
    assert "execution_trace" in row
    assert "execution_trace" not in sqlite_row
    assert "economist_code_execution_requested" not in sqlite_row
    assert "author_received_raw_quant_packet" not in sqlite_row
    assert "source_tier_counts" not in sqlite_row
    assert _rich_execution_value(row, "economist_code_execution_requested") is False
    assert _rich_execution_value(row, "author_received_raw_quant_packet") is False
    assert isinstance(_rich_execution_value(row, "source_tier_counts"), dict)
