from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_economist_telemetry import format_summary, summarize_log


def _write_jsonl(path: Path, rows: list[object]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) if not isinstance(row, str) else row for row in rows),
        encoding="utf-8",
    )


def test_pre_analyst_retrieval_gate_audit_buckets_active_skips(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "execution.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "active-skip",
                "execution_trace": {
                    "analyst_skipped": True,
                    "analyst_skip_reason": "missing_expected_official_evidence",
                    "analyst_skipped_after_economist": False,
                    "economist_output_used_as_analysis": False,
                    "corpus_state": "healthy",
                    "utilization_rate": 0.28,
                    "source_tier_counts": {"unknown": 5},
                    "source_domain_counts": {"news.example": 4, "blog.example": 1},
                    "top_source_domains": [{"domain": "news.example", "count": 4}],
                    "official_evidence_found": False,
                    "community_signal_found": False,
                    "on_domain_source_count": 0,
                    "off_domain_source_count": 5,
                    "answer_class": "partial_answer",
                    "response_displayable": True,
                    "evidence_sufficient": False,
                },
            },
            {
                "event": "execution",
                "run_id": "healthy-denominator",
                "execution_trace": {
                    "analyst_skipped": False,
                    "analyst_skipped_after_economist": False,
                    "economist_output_used_as_analysis": False,
                },
            },
        ],
    )

    summary = summarize_log(log_path)
    audit = summary["pre_analyst_retrieval_gate_audit"]
    detail = audit["skip_reason_details"]["missing_expected_official_evidence"]
    output = format_summary(summary)

    assert audit["diagnostic_only"] is True
    assert audit["source_of_truth"] == "execution_jsonl_full_trace"
    assert audit["sqlite_compact_summary_complete"] is False
    assert audit["denominator_execution_events"] == 2
    assert audit["active_pre_analyst_skip_count"] == 1
    assert audit["analyst_skipped_counts"]["true"] == 1
    assert audit["analyst_skipped_counts"]["false"] == 1
    assert audit["analyst_skip_reason_counts"][
        "missing_expected_official_evidence"
    ] == 1
    assert detail["corpus_state_counts"]["healthy"] == 1
    assert detail["utilization_band_counts"]["low_<=0.35"] == 1
    assert detail["source_tier_mix_counts"]["unknown=5"] == 1
    assert detail["source_tier_counts"]["unknown"] == 5
    assert detail["top_source_domains"]["news.example"] == 4
    assert detail["official_evidence_found_counts"]["false"] == 1
    assert detail["community_signal_found_counts"]["false"] == 1
    assert detail["on_domain_source_count_counts"]["0"] == 1
    assert detail["off_domain_source_count_counts"]["5"] == 1
    assert detail["answer_class_counts"]["partial_answer"] == 1
    assert detail["response_displayable_counts"]["true"] == 1
    assert detail["evidence_sufficient_counts"]["false"] == 1
    assert "pre_analyst_retrieval_gate_audit:" in output
    assert "missing_expected_official_evidence: 1" in output


def test_post_economist_fields_do_not_count_as_active_pre_analyst_skips(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "execution.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "post-economist-anomaly",
                "analyst_skipped": False,
                "analyst_skipped_after_economist": True,
                "analyst_after_economist_skip_reason": "disabled_shadow_anomaly",
                "economist_output_used_as_analysis": True,
            },
        ],
    )

    audit = summarize_log(log_path)["pre_analyst_retrieval_gate_audit"]

    assert audit["denominator_execution_events"] == 1
    assert audit["active_pre_analyst_skip_count"] == 0
    assert audit["analyst_skipped_counts"]["false"] == 1
    assert audit["analyst_skip_reason_counts"] == {}
    assert audit["post_economist_separate_counts"][
        "analyst_skipped_after_economist:true"
    ] == 1
    assert audit["post_economist_separate_counts"][
        "economist_output_used_as_analysis:true"
    ] == 1
    assert audit["analyst_after_economist_skip_reason_counts"][
        "disabled_shadow_anomaly"
    ] == 1


def test_historical_missing_pre_analyst_fields_remain_missing(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "execution.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "old-row",
                "report_type": "general_research",
            },
        ],
    )

    audit = summarize_log(log_path)["pre_analyst_retrieval_gate_audit"]

    assert audit["denominator_execution_events"] == 1
    assert audit["active_pre_analyst_skip_count"] == 0
    assert audit["analyst_skipped_counts"]["missing"] == 1
    assert audit["missing_field_counts"]["analyst_skipped"] == 1
    assert audit["missing_field_counts"]["analyst_skip_reason"] == 1
    assert audit["missing_field_counts"]["source_tier_counts"] == 1
    assert audit["missing_field_counts"]["response_displayable"] == 1


def test_historical_missing_source_diagnostics_remain_missing_on_active_skip(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "execution.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "old-active-skip",
                "execution_trace": {
                    "analyst_skipped": True,
                    "analyst_skip_reason": "corpus_weak",
                    "corpus_state": "weak",
                    "utilization_rate": 0.18,
                },
            },
        ],
    )

    audit = summarize_log(log_path)["pre_analyst_retrieval_gate_audit"]
    detail = audit["skip_reason_details"]["corpus_weak"]

    assert audit["denominator_execution_events"] == 1
    assert audit["active_pre_analyst_skip_count"] == 1
    assert audit["missing_field_counts"]["source_tier_counts"] == 1
    assert audit["missing_field_counts"]["source_domain_counts"] == 1
    assert audit["missing_field_counts"]["top_source_domains"] == 1
    assert audit["missing_field_counts"]["official_evidence_found"] == 1
    assert audit["missing_field_counts"]["community_signal_found"] == 1
    assert detail["source_tier_mix_counts"]["missing"] == 1
    assert detail["official_evidence_found_counts"]["missing"] == 1
    assert detail["official_evidence_found_counts"]["false"] == 0
    assert detail["community_signal_found_counts"]["missing"] == 1
    assert detail["community_signal_found_counts"]["false"] == 0
    assert detail["on_domain_source_count_counts"]["missing"] == 1
    assert detail["off_domain_source_count_counts"]["missing"] == 1
