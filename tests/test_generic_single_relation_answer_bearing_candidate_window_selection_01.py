"""PRODUCT-PATH-REGRESSION: answer-bearing provider candidate/window selection.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation must
inject fake provider results so no live Tavily, Serper, fetch/read, retrieval,
broker/doorman, or model calls occur.
Integration deadline: current phase.
Exit condition: keep while provider-extracted candidate/window selection feeds
the generic single-relation product path, or replace with a broader ordinary
supported-query live validation guard after that path is generalized.
Why this is not a shadow product path: tests call the ordinary dogfood builder
and assert the retained fetch/read packet consumed by the existing path.
Forbidden interpretation: candidate/window selection is not source authority,
semantic support, citation eligibility, source-obligation satisfaction, answer
correctness, FAP/Author output, or live validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proplex.mvp_single_relation_live_dogfood_run import (
    ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED,
    DEFAULT_OUTPUT_DIR,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_generic_single_relation_live_dogfood_01 import (
    N400_QUERY,
    _failing_fetch_runner,
    _fake_fetch_runner,
    _provider_extracted_result,
    _provider_result,
    _recording_proxy_runner,
    _retained_fetch_packet,
)

SSA_WAGE_BASE_QUERY = "What is the current SSA taxable maximum wage base for 2026?"


def test_later_provider_extracted_candidate_with_currency_window_is_selected(
    tmp_path: Path,
) -> None:
    calls: list[Any] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="candidate-window-n400",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "USCIS N-400 Overview",
                    "https://example.invalid/n400-overview",
                    "USCIS Application for Naturalization Form N-400 overview "
                    "with eligibility instructions and filing steps.",
                    rank=1,
                ),
                _provider_extracted_result(
                    "Synthetic N-400 Fee Schedule",
                    "https://example.invalid/n400-fee-schedule",
                    "USCIS Form N-400 paper filing fee schedule. The current "
                    "Form N-400 paper filing fee is $760 in this synthetic "
                    "provider-extracted fixture.",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert result.packet["provider_extracted_content_candidate_count"] == 2
    assert result.packet["provider_extracted_content_obtained"] is True
    assert result.packet["direct_fetch_read_attempts"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["candidate_selection_created_source_authority"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["candidate_selection_claims_correctness"] is False

    fetch_packet = _retained_fetch_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["original_source_url"] == "https://example.invalid/n400-fee-schedule"
    selection = reference["bounded_text_selection"]
    assert selection["expected_value_token_kinds"] == ["currency"]
    assert selection["matched_value_token_kinds"] == ["currency"]
    assert selection["matched_anchor_count"] > 1

    by_rank = {
        item["result_rank"]: item
        for item in result.packet["fetch_read_candidate_diagnostics"]
    }
    assert by_rank[1]["answer_bearing_candidate_window_selected"] is False
    assert by_rank[2]["answer_bearing_candidate_window_selected"] is True
    assert by_rank[2]["title"] == "Synthetic N-400 Fee Schedule"
    assert by_rank[2]["domain"] == "example.invalid"
    assert by_rank[2]["matched_value_token_kinds"] == ["currency"]
    assert by_rank[2]["candidate_window_score_components"][
        "expected_value_token_kind_match_count"
    ] == 1
    assert by_rank[2]["raw_private_retention_flags"][
        "raw_provider_payload_retained"
    ] is False
    serialized = json.dumps(result.packet, sort_keys=True)
    assert '"candidate_selection_created_source_authority": true' not in serialized
    assert '"candidate_selection_citation_eligible": true' not in serialized
    assert "$760" not in json.dumps(result.packet["fast_planner_output"], sort_keys=True)


def test_non_uscis_numeric_value_kind_influences_candidate_window_selection(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=SSA_WAGE_BASE_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="candidate-window-ssa",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_extracted_result(
                    "SSA Wage Base Background",
                    "https://example.invalid/ssa-background",
                    "SSA taxable maximum wage base background and official "
                    "program overview without the current numeric value.",
                    rank=1,
                ),
                _provider_extracted_result(
                    "SSA Wage Base Table",
                    "https://example.invalid/ssa-wage-base-table",
                    "SSA taxable maximum wage base table for 2026. The current "
                    "taxable maximum wage base is 176100 in this synthetic "
                    "official fixture.",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    fetch_packet = _retained_fetch_packet(result)
    reference = fetch_packet["reference_records"][0]
    selection = reference["bounded_text_selection"]
    assert reference["original_source_url"] == "https://example.invalid/ssa-wage-base-table"
    assert result.packet["expected_value_token_kinds"] == ["number"]
    assert selection["matched_value_token_kinds"] == ["number"]

    diagnostics = result.packet["answer_bearing_candidate_window_diagnostics"]
    assert len(diagnostics) == 2
    assert [item["selected"] for item in diagnostics] == [False, True]
    assert diagnostics[1]["matched_value_token_kinds"] == ["number"]
    assert diagnostics[1]["score_components"][
        "expected_value_token_kind_match_count"
    ] == 1
    assert "USCIS" not in result.packet["acquisition_query"]
    assert "N-400" not in result.packet["acquisition_query"]


def test_weak_provider_extracted_candidate_set_is_diagnosed_without_support_upgrade(
    tmp_path: Path,
) -> None:
    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="candidate-window-weak",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_extracted_result(
                    "Generic Naturalization Page",
                    "https://example.invalid/naturalization",
                    "Naturalization overview with filing steps and no fee table.",
                    rank=1,
                ),
                _provider_extracted_result(
                    "Generic Form Help",
                    "https://example.invalid/form-help",
                    "Form help page with eligibility notes and no current amount.",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.packet["answer_bearing_candidate_window_not_established"] is True
    assert result.packet["answer_bearing_candidate_window_status"] == (
        ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED
    )
    selected = [
        item
        for item in result.packet["fetch_read_candidate_diagnostics"]
        if item["answer_bearing_candidate_window_selected"] is True
    ]
    assert len(selected) == 1
    assert selected[0]["matched_value_token_kinds"] == []
    assert selected[0]["anchor_match_status"] in {
        "no_required_anchors_matched",
        "partial_required_anchor_match",
    }
    assert result.packet["answer_text_present"] is False
    assert result.packet["actual_source_authority_posture_created"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["product_correctness_claimed"] is False


def test_direct_fetch_fallback_cap_and_closed_surfaces_remain_unchanged(
    tmp_path: Path,
) -> None:
    fetch_urls: list[str] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="candidate-window-direct-fallback",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(
            [],
            [
                _provider_result(
                    f"Synthetic N-400 Candidate {index}",
                    f"https://example.invalid/n400/{index}",
                    rank=index,
                )
                for index in range(1, 6)
            ],
        ),
        fetch_read_runner=_failing_fetch_runner(fetch_urls),
        environ={},
    )

    assert len(fetch_urls) == 3
    assert result.packet["fetch_read_attempts"] == 3
    assert result.packet["direct_fetch_read_attempts"] == 3
    assert result.packet["provider_extracted_content_candidate_count"] == 0
    assert result.packet["answer_bearing_candidate_window_diagnostics"] == []
    assert result.packet["candidate_selection_created_source_authority"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["fap_calls"] == 0
    assert result.packet["author_calls"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
