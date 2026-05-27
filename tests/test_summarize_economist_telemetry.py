from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from scripts.summarize_economist_telemetry import format_summary, main, summarize_log


@pytest.fixture
def local_tmp_dir() -> Path:
    path = Path.cwd() / f".summarizer-test-{uuid.uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _write_jsonl(path: Path, rows: list[object]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) if not isinstance(row, str) else row for row in rows),
        encoding="utf-8",
    )


def _clean_positive_readiness_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "event": "execution",
        "run_id": "run-clean-positive",
        "report_type": "quantitative_comparison",
        "mode": "Balanced",
        "complexity": "medium",
        "economist_pre_analyst_skip_candidate_shadow": True,
        "economist_pre_analyst_skip_candidate_gate_reason": "candidate_shadow_only",
        "economist_pre_analyst_skip_candidate_blockers": [],
        "economist_skip_eligible_shadow": True,
        "economist_skip_eligibility_gate_reason": "eligible_shadow_only",
        "economist_skip_eligibility_blockers": [],
        "economist_skip_shadow_alignment": "candidate_and_posthoc_eligible",
        "quant_retrieval_target_detected": True,
        "quant_retrieval_sufficiency_valid": True,
        "quant_retrieval_sufficiency_blockers": [],
        "quant_retrieval_sufficiency_gate_reason": "sufficient_shadow_only",
        "high_stakes_quant_detected": False,
        "high_stakes_quant_future_direct_use_allowed": True,
        "author_quant_content_source": "analyst_reviewed",
        "analyst_quant_packet_reviewed_by_model": True,
        "analyst_model_called": True,
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
        "analyst_skipped_after_economist": False,
        "economist_output_used_as_analysis": False,
        "economist_code_execution_requested": False,
    }
    row.update(overrides)
    return row


def test_summarizer_readiness_reports_clean_positive_and_blocked_negative_controls(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _clean_positive_readiness_row(),
            _clean_positive_readiness_row(
                run_id="run-high-stakes-blocked",
                economist_pre_analyst_skip_candidate_shadow=False,
                economist_pre_analyst_skip_candidate_blockers=[
                    "high_stakes_requires_analyst",
                ],
                economist_pre_analyst_skip_candidate_gate_reason="blocked_by_high_stakes",
                economist_skip_eligible_shadow=False,
                economist_skip_eligibility_blockers=[
                    "high_stakes_requires_analyst",
                    "retrieval_sufficiency_failed",
                ],
                economist_skip_eligibility_gate_reason="blocked_by_high_stakes",
                economist_skip_shadow_alignment="neither",
                quant_retrieval_sufficiency_valid=False,
                quant_retrieval_sufficiency_blockers=[
                    "missing_metric_coverage",
                    "high_stakes_requires_analyst",
                ],
                quant_retrieval_sufficiency_gate_reason="blocked_by_high_stakes",
                high_stakes_quant_detected=True,
                high_stakes_quant_future_direct_use_allowed=False,
                author_quant_content_source="none",
                analyst_quant_packet_reviewed_by_model=False,
                analyst_model_called=False,
            ),
        ],
    )

    summary = summarize_log(log_path)
    readiness = summary["readiness"]
    output = format_summary(summary)

    assert readiness["diagnostic_only"] is True
    assert readiness["readiness_for_review"] is True
    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["promotion_blocker_counts"] == {}
    assert readiness["negative_control_blocked_counts"][
        "high_stakes_guardrail_blocked"
    ] == 1
    assert readiness["negative_control_blocked_counts"][
        "retrieval_sufficiency_blocked"
    ] == 1
    assert "readiness diagnostics:" in output
    assert "readiness_for_review: true" in output
    assert "readiness blockers:\n  (none)" in output
    assert "high_stakes_guardrail_blocked: 1" in output


def test_summarizer_readiness_blocks_author_marker_leak(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _clean_positive_readiness_row(run_id="run-clean-positive"),
            _clean_positive_readiness_row(
                run_id="run-marker-leak",
                author_received_raw_quant_packet=True,
                author_quant_content_source="raw_quant_packet_detected",
            ),
        ],
    )

    summary = summarize_log(log_path)
    readiness = summary["readiness"]
    output = format_summary(summary)

    assert readiness["readiness_for_review"] is False
    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["promotion_blocker_counts"][
        "author_marker_leak:author_received_raw_quant_packet"
    ] == 1
    assert readiness["marker_leak_counts"]["author_received_raw_quant_packet"] == 1
    assert "author_marker_leak:author_received_raw_quant_packet: 1" in output
    assert "author_received_raw_quant_packet: 1" in output


def test_summarizer_readiness_blocks_historical_economist_framework_marker_leak(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _clean_positive_readiness_row(run_id="run-clean-positive"),
            _clean_positive_readiness_row(
                run_id="run-framework-leak",
                author_received_economist_framework=True,
                author_quant_content_source="raw_economist_block_detected",
            ),
        ],
    )

    summary = summarize_log(log_path)
    readiness = summary["readiness"]
    output = format_summary(summary)

    assert readiness["readiness_for_review"] is False
    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["promotion_blocker_counts"][
        "author_marker_leak:author_received_economist_framework"
    ] == 1
    assert readiness["marker_leak_counts"]["author_received_economist_framework"] == 1
    assert summary["safety_anomaly_counts"]["author_received_economist_framework"] == 1
    assert "author_marker_leak:author_received_economist_framework: 1" in output
    assert "author_received_economist_framework: 1" in output


def test_summarizer_readiness_blocks_unsafe_shadow_eligible_controls(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _clean_positive_readiness_row(run_id="run-clean-positive"),
            _clean_positive_readiness_row(
                run_id="run-unsafe-eligible",
                quant_retrieval_sufficiency_valid=False,
                quant_retrieval_sufficiency_blockers=["missing_metric_coverage"],
                high_stakes_quant_detected=True,
                high_stakes_quant_future_direct_use_allowed=True,
                economist_code_execution_requested=True,
            ),
        ],
    )

    summary = summarize_log(log_path)
    readiness = summary["readiness"]

    assert readiness["readiness_for_review"] is False
    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["promotion_blocker_counts"][
        "unsafe_shadow_eligible:high_stakes"
    ] == 1
    assert readiness["promotion_blocker_counts"][
        "unsafe_shadow_eligible:code_execution_requested"
    ] == 1
    assert readiness["promotion_blocker_counts"][
        "unsafe_shadow_eligible:retrieval_not_valid"
    ] == 1
    assert readiness["promotion_blocker_counts"][
        "high_stakes_guardrail:not_future_blocked"
    ] == 1
    assert readiness["unsafe_shadow_eligible_counts"][
        "unsafe_shadow_eligible:high_stakes"
    ] == 1


def test_summarizer_readiness_blocks_candidate_posthoc_alignment_mismatch(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _clean_positive_readiness_row(run_id="run-clean-positive"),
            _clean_positive_readiness_row(
                run_id="run-candidate-only",
                economist_skip_eligible_shadow=False,
                economist_skip_eligibility_blockers=[
                    "packet_not_reviewed_by_analyst",
                ],
                economist_skip_eligibility_gate_reason="blocked_by_missing_analyst_review",
                economist_skip_shadow_alignment="candidate_only",
            ),
        ],
    )

    summary = summarize_log(log_path)
    readiness = summary["readiness"]

    assert readiness["readiness_for_review"] is False
    assert readiness["clean_positive_evidence_count"] == 1
    assert readiness["promotion_blocker_counts"][
        "alignment_mismatch:candidate_only"
    ] == 1
    assert readiness["alignment_mismatch_counts"][
        "alignment_mismatch:candidate_only"
    ] == 1


def test_summarizer_counts_candidate_and_posthoc_eligible_happy_path(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "report_type": "quantitative_comparison",
                "mode": "Balanced",
                "complexity": "medium",
                "economist_pre_analyst_skip_candidate_shadow": True,
                "economist_skip_eligible_shadow": True,
                "economist_skip_shadow_alignment": "candidate_and_posthoc_eligible",
                "quant_retrieval_sufficiency_valid": True,
                "quant_retrieval_sufficiency_blockers": [],
                "economist_pre_analyst_skip_candidate_blockers": [],
                "economist_skip_eligibility_blockers": [],
                "high_stakes_quant_detected": False,
                "author_received_raw_quant_packet": False,
                "author_received_economist_framework": False,
                "author_received_analyst_packet_marker": False,
                "analyst_skipped_after_economist": False,
                "economist_output_used_as_analysis": False,
                "economist_code_execution_requested": False,
            }
        ],
    )

    summary = summarize_log(log_path)

    assert summary["total_lines_read"] == 1
    assert summary["total_execution_events"] == 1
    assert summary["report_type_counts"]["quantitative_comparison"] == 1
    assert summary["mode_counts"]["Balanced"] == 1
    assert summary["complexity_counts"]["medium"] == 1
    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "true"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["true"] == 1
    assert summary["boolean_counts"]["high_stakes_quant_detected"]["false"] == 1
    assert summary["economist_skip_shadow_alignment_counts"]["candidate_and_posthoc_eligible"] == 1
    assert summary["quant_retrieval_sufficiency_valid_counts"]["true"] == 1
    assert summary["safety_anomaly_counts"]["economist_code_execution_requested"] == 0

    assert main([str(log_path)]) == 0
    output = capsys.readouterr().out
    assert "total_lines_read: 1" in output
    assert "execution_events: 1" in output
    assert "medium: 1" in output
    assert "economist_pre_analyst_skip_candidate_shadow counts:" in output
    assert "candidate_and_posthoc_eligible: 1" in output
    assert "notable runs:" not in output


def test_summarizer_ignores_malformed_and_non_execution_rows(local_tmp_dir: Path) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            "{not-json",
            {"event": "kb_trigger", "report_type": "ignored"},
            ["also", "ignored"],
            {
                "event": "execution",
                "report_type": "",
                "mode": None,
                "quant_retrieval_sufficiency_valid": None,
            },
        ],
    )

    summary = summarize_log(log_path)
    output = format_summary(summary)

    assert summary["total_lines_read"] == 4
    assert summary["total_execution_events"] == 1
    assert summary["malformed_rows"] == 1
    assert summary["non_execution_rows"] == 2
    assert summary["report_type_counts"]["missing"] == 1
    assert summary["mode_counts"]["missing"] == 1
    assert summary["complexity_counts"]["missing"] == 1
    assert summary["quant_retrieval_sufficiency_valid_counts"]["missing"] == 1
    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "missing"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["missing"] == 1
    assert "total_lines_read: 4" in output
    assert "malformed_rows: 1" in output
    assert "non_execution_rows: 2" in output


def test_summarizer_official_target_evidence_diagnostics_positive_cases(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-source-divergence",
                "final_answer_packet_source_ids_diverged": True,
                "final_answer_source_ids_not_in_packet": ["7"],
                "packet_source_ids_not_in_final_answer": ["1"],
                "economist_evidence_source_ids_seen": ["1", "7", "8"],
                "economist_evidence_source_ids_used": ["1"],
            },
            {
                "event": "execution",
                "run_id": "run-official-like-missed",
                "official_evidence_found": False,
                "source_domain_counts": {
                    "sec.gov": 2,
                    "s201.q4cdn.com": 3,
                },
            },
            {
                "event": "execution",
                "run_id": "run-polluted-quant",
                "report_type": "quantitative_comparison",
                "source_domain_counts": {
                    "arxiv.org": 4,
                    "pubmed.ncbi.nlm.nih.gov": 2,
                },
            },
            {
                "event": "execution",
                "run_id": "run-target-missing-despite-sufficiency",
                "quant_retrieval_sufficiency_valid": True,
                "quantitative_packet_validation_errors": [
                    "target_metric_evidence_missing",
                ],
                "target_metric_bound_value_refs": ["costco_fy2024_revenue"],
                "target_metric_evidence_found": False,
            },
        ],
    )

    summary = summarize_log(log_path)
    diagnostics = summary["official_target_evidence_diagnostics"]
    output = format_summary(summary)

    assert diagnostics["diagnostic_only"] is True
    assert diagnostics["rows_with_final_packet_source_divergence"] == 1
    assert diagnostics["rows_with_final_sources_not_in_packet"] == 1
    assert diagnostics["rows_with_packet_sources_not_in_final"] == 1
    assert diagnostics["rows_with_economist_window_seen_but_not_used"] == 1
    assert diagnostics["top_final_answer_source_ids_not_in_packet"]["7"] == 1
    assert diagnostics["top_packet_source_ids_not_in_final_answer"]["1"] == 1
    assert (
        diagnostics[
            "rows_with_official_evidence_found_false_but_official_like_domains_present"
        ]
        == 1
    )
    assert (
        diagnostics[
            "top_official_like_domains_present_when_official_evidence_found_false"
        ]["q4cdn.com"]
        == 3
    )
    assert diagnostics["top_official_like_domains_present_when_official_evidence_found_false"][
        "sec.gov"
    ] == 2
    assert (
        diagnostics[
            "rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison"
        ]
        == 1
    )
    assert diagnostics["top_polluted_domains_for_quantitative_comparison"][
        "academic_preprint"
    ] == 4
    assert diagnostics["top_polluted_domains_for_quantitative_comparison"][
        "biomedical_index"
    ] == 2
    assert (
        diagnostics[
            "rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid"
        ]
        == 1
    )
    assert (
        diagnostics[
            "rows_where_target_bound_refs_present_but_target_metric_evidence_found_false"
        ]
        == 1
    )
    assert "official_target_evidence_diagnostics:" in output
    assert "rows_with_final_packet_source_divergence: 1" in output
    assert "q4cdn.com: 3" in output
    assert "academic_preprint: 4" in output


def test_summarizer_official_target_evidence_diagnostics_negative_controls(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-clean-matching-sources",
                "final_answer_packet_source_ids_diverged": False,
                "final_answer_source_ids_not_in_packet": [],
                "packet_source_ids_not_in_final_answer": [],
                "economist_evidence_source_ids_seen": ["1"],
                "economist_evidence_source_ids_used": ["1"],
            },
            {
                "event": "execution",
                "run_id": "run-non-quant-pollution-source",
                "report_type": "general_research",
                "source_domain_counts": {"arxiv.org": 5},
            },
            {
                "event": "execution",
                "run_id": "run-official-found",
                "official_evidence_found": True,
                "source_domain_counts": {"sec.gov": 3},
            },
            {
                "event": "execution",
                "run_id": "run-no-domain-counts",
            },
        ],
    )

    summary = summarize_log(log_path)
    diagnostics = summary["official_target_evidence_diagnostics"]
    output = format_summary(summary)

    assert diagnostics["rows_with_final_packet_source_divergence"] == 0
    assert diagnostics["rows_with_final_sources_not_in_packet"] == 0
    assert diagnostics["rows_with_packet_sources_not_in_final"] == 0
    assert diagnostics["rows_with_economist_window_seen_but_not_used"] == 0
    assert (
        diagnostics[
            "rows_with_official_evidence_found_false_but_official_like_domains_present"
        ]
        == 0
    )
    assert (
        diagnostics[
            "rows_with_academic_or_biomedical_domain_pollution_on_quantitative_comparison"
        ]
        == 0
    )
    assert (
        diagnostics[
            "rows_where_target_metric_evidence_missing_but_retrieval_sufficiency_valid"
        ]
        == 0
    )
    assert (
        diagnostics[
            "rows_where_target_bound_refs_present_but_target_metric_evidence_found_false"
        ]
        == 0
    )
    assert "top final_answer_source_ids_not_in_packet:\n  (none)" in output
    assert (
        "top official-like domains present when official_evidence_found=false:\n  (none)"
        in output
    )
    assert "top polluted domains for quantitative comparison rows:\n  (none)" in output


def test_summarizer_details_output_includes_notable_runs_section(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-details",
                "query": "Compare Alpha Air and Beta Air CASM.",
                "quant_retrieval_sufficiency_valid": False,
                "quant_retrieval_sufficiency_blockers": ["missing_metric_coverage"],
            }
        ],
    )

    assert main(["--details", str(log_path)]) == 0
    output = capsys.readouterr().out

    assert "notable runs:" in output
    assert "run_id: run-details" in output
    assert "retrieval_valid: false" in output


def test_summarizer_details_include_high_stakes_run_with_blockers(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-high-stakes",
                "timestamp_utc": "2026-05-08T12:00:00Z",
                "query": "Compare hospital mortality rates by provider for 2025.",
                "mode": "Balanced",
                "report_type": "quantitative_comparison",
                "complexity": "medium",
                "economist_pre_analyst_skip_candidate_shadow": False,
                "economist_skip_eligible_shadow": False,
                "economist_skip_shadow_alignment": "neither",
                "quant_retrieval_sufficiency_valid": False,
                "quant_retrieval_sufficiency_blockers": [
                    "missing_metric_coverage",
                    "high_stakes_requires_analyst",
                ],
                "economist_pre_analyst_skip_candidate_blockers": [
                    "high_stakes_requires_analyst",
                ],
                "economist_skip_eligibility_blockers": [
                    "retrieval_sufficiency_failed",
                ],
                "quant_retrieval_sufficiency_gate_reason": (
                    "blocked_by_missing_metric_coverage"
                ),
                "economist_pre_analyst_skip_candidate_gate_reason": (
                    "blocked_by_high_stakes"
                ),
                "economist_skip_eligibility_gate_reason": "blocked_by_high_stakes",
                "high_stakes_quant_detected": True,
                "author_quant_content_source": "none",
                "final_output_preview": "Final answer preview.",
            }
        ],
    )

    assert main(["--details", str(log_path)]) == 0
    output = capsys.readouterr().out

    assert "run_id: run-high-stakes" in output
    assert "query: Compare hospital mortality rates by provider for 2025." in output
    assert "high_stakes: true" in output
    assert (
        "blockers: missing_metric_coverage, high_stakes_requires_analyst, "
        "retrieval_sufficiency_failed"
    ) in output


def test_summarizer_max_details_limits_notable_runs(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-one",
                "quant_retrieval_sufficiency_valid": False,
            },
            {
                "event": "execution",
                "run_id": "run-two",
                "quant_retrieval_sufficiency_valid": False,
            },
            {
                "event": "execution",
                "run_id": "run-three",
                "quant_retrieval_sufficiency_valid": False,
            },
        ],
    )

    assert main(["--details", "--max-details", "2", str(log_path)]) == 0
    output = capsys.readouterr().out

    assert "run_id: run-one" in output
    assert "run_id: run-two" in output
    assert "run_id: run-three" not in output
    assert "... 1 more notable runs not shown" in output


@pytest.mark.parametrize("bad_timestamp", ["not-a-timestamp", None])
def test_summarizer_newest_first_sorts_details_before_limit(
    local_tmp_dir: Path,
    capsys: pytest.CaptureFixture[str],
    bad_timestamp: str | None,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-old",
                "timestamp_utc": "2026-05-07T12:00:00Z",
                "quant_retrieval_sufficiency_valid": False,
            },
            {
                "event": "execution",
                "run_id": "run-bad-timestamp",
                "timestamp_utc": bad_timestamp,
                "quant_retrieval_sufficiency_valid": False,
            },
            {
                "event": "execution",
                "run_id": "run-new",
                "timestamp_utc": "2026-05-08T12:00:00Z",
                "quant_retrieval_sufficiency_valid": False,
            },
        ],
    )

    assert main(["--details", "--max-details", "2", str(log_path)]) == 0
    default_output = capsys.readouterr().out

    assert default_output.index("run_id: run-old") < default_output.index(
        "run_id: run-bad-timestamp"
    )
    assert "run_id: run-new" not in default_output

    assert (
        main(["--details", "--newest-first", "--max-details", "2", str(log_path)])
        == 0
    )
    newest_first_output = capsys.readouterr().out

    assert newest_first_output.index("run_id: run-new") < newest_first_output.index(
        "run_id: run-old"
    )
    assert "run_id: run-bad-timestamp" not in newest_first_output
    assert "... 1 more notable runs not shown" in newest_first_output


def test_summarizer_details_exclude_non_notable_clean_row(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-clean",
                "query": "Clean quantitative comparison.",
                "economist_pre_analyst_skip_candidate_shadow": False,
                "economist_skip_eligible_shadow": False,
                "high_stakes_quant_detected": False,
                "quant_retrieval_sufficiency_valid": True,
                "author_received_raw_quant_packet": False,
                "author_received_economist_framework": False,
                "author_received_analyst_packet_marker": False,
                "analyst_skipped_after_economist": False,
                "economist_output_used_as_analysis": False,
                "economist_code_execution_requested": False,
            },
            {
                "event": "execution",
                "run_id": "run-notable",
                "high_stakes_quant_detected": True,
                "quant_retrieval_sufficiency_valid": True,
            },
        ],
    )

    assert main(["--details", str(log_path)]) == 0
    output = capsys.readouterr().out

    assert "run_id: run-notable" in output
    assert "run_id: run-clean" not in output


def test_summarizer_details_do_not_crash_on_malformed_or_non_execution_rows(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            "{not-json",
            {"event": "kb_trigger", "run_id": "ignored"},
            ["also", "ignored"],
        ],
    )

    assert main(["--details", str(log_path)]) == 0
    output = capsys.readouterr().out

    assert "malformed_rows: 1" in output
    assert "non_execution_rows: 2" in output
    assert "notable runs:" in output
    assert "  (none)" in output


def test_summarizer_aggregates_blockers_for_negative_control(local_tmp_dir: Path) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "report_type": "quantitative_comparison",
                "mode": "Balanced",
                "economist_pre_analyst_skip_candidate_shadow": False,
                "economist_skip_eligible_shadow": False,
                "economist_skip_shadow_alignment": "neither",
                "quant_retrieval_sufficiency_valid": False,
                "quant_retrieval_sufficiency_blockers": [
                    "retrieval_sufficiency_failed",
                    "high_stakes_requires_analyst",
                ],
                "economist_pre_analyst_skip_candidate_blockers": [
                    "retrieval_sufficiency_failed",
                    "high_stakes_requires_analyst",
                ],
                "economist_skip_eligibility_blockers": [
                    "retrieval_sufficiency_failed",
                    "high_stakes_requires_analyst",
                ],
                "high_stakes_quant_detected": True,
            }
        ],
    )

    summary = summarize_log(log_path)

    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "false"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["false"] == 1
    assert summary["boolean_counts"]["high_stakes_quant_detected"]["true"] == 1
    assert summary["quant_retrieval_sufficiency_valid_counts"]["false"] == 1
    assert summary["blocker_counts"]["quant_retrieval_sufficiency_blockers"][
        "retrieval_sufficiency_failed"
    ] == 1
    assert summary["blocker_counts"]["economist_pre_analyst_skip_candidate_blockers"][
        "high_stakes_requires_analyst"
    ] == 1
    assert summary["blocker_counts"]["economist_skip_eligibility_blockers"][
        "retrieval_sufficiency_failed"
    ] == 1


def test_summarizer_aggregates_safety_anomalies(local_tmp_dir: Path) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "author_received_raw_quant_packet": True,
                "author_received_economist_framework": True,
                "author_received_analyst_packet_marker": False,
                "analyst_skipped_after_economist": True,
                "economist_output_used_as_analysis": False,
                "economist_code_execution_requested": True,
            },
            {
                "event": "execution",
                "author_received_raw_quant_packet": False,
                "author_received_economist_framework": True,
                "author_received_analyst_packet_marker": True,
                "analyst_skipped_after_economist": False,
                "economist_output_used_as_analysis": True,
                "economist_code_execution_requested": False,
            },
        ],
    )

    summary = summarize_log(log_path)

    assert summary["safety_anomaly_counts"]["author_received_raw_quant_packet"] == 1
    assert summary["safety_anomaly_counts"]["author_received_economist_framework"] == 2
    assert summary["safety_anomaly_counts"]["author_received_analyst_packet_marker"] == 1
    assert summary["safety_anomaly_counts"]["analyst_skipped_after_economist"] == 1
    assert summary["safety_anomaly_counts"]["economist_output_used_as_analysis"] == 1
    assert summary["safety_anomaly_counts"]["economist_code_execution_requested"] == 1


def test_summarizer_labels_historical_rows_without_recomputing_counts(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "run_id": "run-old-anomaly",
                "timestamp_utc": "2026-04-24T12:00:00Z",
                "author_received_economist_framework": True,
                "economist_code_execution_requested": True,
            },
            {
                "event": "execution",
                "run_id": "run-new-clean",
                "timestamp_utc": "2026-05-08T12:00:00Z",
                "author_received_economist_framework": False,
                "economist_code_execution_requested": False,
            },
        ],
    )

    summary = summarize_log(log_path)
    output = format_summary(summary)

    assert summary["oldest_execution_timestamp"] == "2026-04-24T12:00:00Z"
    assert summary["newest_execution_timestamp"] == "2026-05-08T12:00:00Z"
    assert summary["execution_rows_with_commit_metadata"] == 0
    assert summary["safety_anomaly_counts"]["author_received_economist_framework"] == 1
    assert summary["safety_anomaly_counts"]["economist_code_execution_requested"] == 1
    assert "log metadata:" in output
    assert "historical_log_only: true" in output
    assert "recomputed_with_current_code: false" in output
    assert (
        "diagnostic_note: historical log only; parsed rows are not recomputed "
        "with current code."
    ) in output
    assert "oldest_execution_timestamp: 2026-04-24T12:00:00Z" in output
    assert "newest_execution_timestamp: 2026-05-08T12:00:00Z" in output
    assert (
        "commit_metadata_warning: missing commit SHA/code version metadata; "
        "use timestamps and run_id only."
    ) in output


def test_summarizer_counts_execution_rows_with_commit_metadata(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {"event": "execution", "run_id": "run-with-sha", "commit_sha": "abc123"},
            {"event": "execution", "run_id": "run-without-sha"},
            {"event": "run_completed", "run_id": "non-execution", "commit_sha": "ignored"},
        ],
    )

    summary = summarize_log(log_path)

    assert summary["total_execution_events"] == 2
    assert summary["execution_rows_with_commit_metadata"] == 1
    assert summary["commit_metadata_fields_seen"]["commit_sha"] == 1


def test_summarizer_counts_older_execution_rows_missing_phase_11_fields(
    local_tmp_dir: Path,
) -> None:
    log_path = local_tmp_dir / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                "event": "execution",
                "report_type": "general_research",
                "mode": "Fast",
                "complexity": "low",
            }
        ],
    )

    summary = summarize_log(log_path)
    output = format_summary(summary)

    assert summary["boolean_counts"]["economist_pre_analyst_skip_candidate_shadow"][
        "missing"
    ] == 1
    assert summary["boolean_counts"]["economist_skip_eligible_shadow"]["missing"] == 1
    assert "economist_pre_analyst_skip_candidate_shadow counts:" in output
    assert "economist_skip_eligible_shadow counts:" in output
    assert "  missing: 1" in output


def test_summarizer_missing_file_returns_nonzero_and_prints_message(
    local_tmp_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing_path = local_tmp_dir / "missing.jsonl"

    result = main([str(missing_path)])

    assert result == 1
    assert f"No log at {missing_path}" in capsys.readouterr().out
