"""PRODUCT-PATH-REGRESSION: generic acquisition query planning repair.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation must
inject fake product-provider callables so no live Tavily, Serper, fetch/read, or
model calls occur.
Integration deadline: current phase.
Exit condition: keep while the generic single-relation product path consumes the
canonical acquisition plan, or replace with a broader product-path planner guard.
Why this is not a shadow product path: tests call the ordinary dogfood builder
and product-owned acquisition adapter seam consumed by that builder.
Forbidden interpretation: fake-provider PASS is not live validation, source
authority, citation eligibility, source-obligation satisfaction, D-prime support,
FAP/Author output, or product correctness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.generic_product_provider_acquisition as product_acquisition
from proplex.mvp_single_relation_live_dogfood_run import (
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED,
    DEFAULT_OUTPUT_DIR,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_generic_single_relation_live_dogfood_01 import (
    N400_QUERY,
    _fake_fetch_runner,
    _retained_fetch_packet,
)

IRS_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car in 2026?"
)
AMBIGUOUS_QUERY = "What is the current filing fee for the form?"
SSA_WAGE_BASE_QUERY = "What is the current SSA taxable maximum wage base for 2026?"
FAFSA_DEADLINE_QUERY = "What is the current FAFSA filing deadline for 2026?"


def test_clear_n400_product_path_sends_artifact_oriented_acquisition_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tavily_calls: list[dict[str, Any]] = []
    extracted_text = (
        "USCIS Form N-400 paper filing fee schedule. The current Form N-400 "
        "paper filing fee is $760 in this synthetic provider-extracted fixture."
    )

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": "USCIS Form N-400 Filing Fee",
                    "url": "https://example.invalid/n400-fees",
                    "domain": "uscis.gov",
                    "snippet": "Current filing fee table.",
                    "raw_content": extracted_text,
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="planner-n400",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    packet = result.packet
    plan = packet["fast_planner_output"]
    serialized_plan = json.dumps(plan, sort_keys=True)

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert packet["acquisition_plan_consumed_by_product_path"] is True
    assert packet["provider_acquisition_query_from_plan"] is True
    assert packet["serper_scout_calls_attempted"] == 0
    assert packet["planner_marked_ambiguity"] is False
    assert tavily_calls[0]["query"] == packet["acquisition_query"]
    assert tavily_calls[0]["query"] != packet["relation_plan_search_query_seed"]
    assert "USCIS" in tavily_calls[0]["query"]
    assert "Form N-400" in tavily_calls[0]["query"]
    assert "paper filing fee" in tavily_calls[0]["query"]
    assert "fee schedule" in tavily_calls[0]["query"]
    assert "current" in tavily_calls[0]["query"]
    assert packet["expected_value_token_kinds"] == ["currency"]
    assert packet["answer_bearing_anchor_count"] >= 4
    assert packet["selected_window_guidance_produced"] is True
    assert packet["selected_window_guidance_consumed"] is True
    assert packet["selected_window_guidance_blocked"] is False
    assert packet["selected_window_anchor_guidance_consumed"] is True
    assert packet["selected_window_value_token_guidance_consumed"] is True
    assert packet["selected_window_value_token_guidance_blocked"] is False
    assert "$760" not in serialized_plan
    assert "uscis.gov/forms" not in serialized_plan
    assert "G-1055" not in serialized_plan
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_model_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False

    fetch_packet = _retained_fetch_packet(result)
    selection = fetch_packet["reference_records"][0]["bounded_text_selection"]
    assert selection["required_anchor_count"] == packet["answer_bearing_anchor_count"]
    assert selection["matched_anchor_count"] >= 4
    assert selection["value_token_guidance_consumed"] is True
    assert selection["expected_value_token_kinds"] == ["currency"]
    assert selection["matched_value_token_kinds"] == ["currency"]


def test_non_uscis_rate_fixture_uses_generic_artifact_fact_kind_logic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tavily_calls: list[dict[str, Any]] = []

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": "IRS Standard Mileage Rates",
                    "url": "https://example.invalid/irs-mileage-rates",
                    "domain": "irs.gov",
                    "snippet": "Official mileage rate notice.",
                    "raw_content": (
                        "IRS standard mileage rate notice for 2026. The business "
                        "use standard mileage rate is 70 cents per mile in this "
                        "synthetic provider-extracted fixture."
                    ),
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=IRS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="planner-irs-rate",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    query = tavily_calls[0]["query"]
    serialized_plan = json.dumps(result.packet["fast_planner_output"], sort_keys=True)

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert "IRS" in query
    assert "standard mileage rate" in query
    assert "business use" in query
    assert "official" in query
    assert "rate" in query
    assert "notice" in query
    assert "USCIS" not in query
    assert "N-400" not in query
    assert "uscis" not in serialized_plan.casefold()
    assert result.packet["expected_value_token_kinds"] == ["currency", "number"]
    assert result.packet["selected_window_guidance_consumed"] is True
    assert result.packet["selected_window_anchor_guidance_consumed"] is True
    assert result.packet["selected_window_value_token_guidance_consumed"] is True
    assert result.packet["selected_window_value_token_guidance_blocked"] is False
    assert result.packet["provider_query_generation_changed"] is True


def test_ambiguous_query_uses_scout_directionality_without_evidence_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scout_calls: list[dict[str, Any]] = []
    tavily_calls: list[dict[str, Any]] = []

    def fake_scout(**kwargs: Any) -> list[dict[str, Any]]:
        scout_calls.append(kwargs)
        return [
            {
                "title": "Example County Small Claims Filing Fee",
                "url": "https://example.invalid/small-claims-fees",
                "domain": "example.invalid",
                "snippet": "Directionality only scout result.",
                "position": 1,
            }
        ]

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": "Example County Small Claims Filing Fee",
                    "url": "https://example.invalid/small-claims-fees",
                    "domain": "example.invalid",
                    "snippet": "Official fee schedule.",
                    "raw_content": (
                        "Example County small claims filing fee schedule. The "
                        "current filing fee is $42 in this synthetic fixture."
                    ),
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_scout_results", fake_scout)
    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=AMBIGUOUS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="planner-ambiguous",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert result.packet["planner_marked_ambiguity"] is True
    assert result.packet["serper_scout_calls_attempted"] == 1
    assert scout_calls[0]["query"] == AMBIGUOUS_QUERY
    assert "Example County Small Claims Filing Fee" in tavily_calls[0]["query"]
    assert result.packet["serper_output_recorded_as_non_evidence"] is True
    assert result.packet["serper_output_used_as_evidence"] is False
    observation = result.packet["disambiguation_record"]["observations"][0]
    assert observation["not_evidence"] is True
    assert observation["not_source_custody"] is True
    assert observation["not_citation_eligible"] is True
    assert observation["not_source_obligation_satisfaction"] is True
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False


@pytest.mark.parametrize(
    (
        "query",
        "provider_title",
        "provider_text",
        "expected_query_terms",
        "expected_fact_kind",
        "expected_value_kinds",
        "expected_artifact_terms",
        "forbidden_terms",
    ),
    [
        (
            SSA_WAGE_BASE_QUERY,
            "SSA Taxable Maximum Wage Base",
            (
                "SSA taxable maximum wage base table for 2026. The taxable "
                "maximum wage base is 176100 in this synthetic official fixture."
            ),
            ("SSA", "2026", "wage base", "official", "current", "table", "notice"),
            "current_value",
            ["number"],
            ("official", "current", "rate", "notice", "table"),
            (
                "USCIS",
                "N-400",
                "paper filing fee",
                "small claims",
                "standard mileage rate",
            ),
        ),
        (
            FAFSA_DEADLINE_QUERY,
            "FAFSA Filing Deadline Instructions",
            (
                "FAFSA filing deadline instructions for 2026. The current "
                "filing deadline is 2026-06-30 in this synthetic official fixture."
            ),
            ("FAFSA", "2026", "filing deadline", "official", "current", "instructions"),
            "deadline",
            ["date_like"],
            ("official", "current", "deadline", "instructions", "effective"),
            (
                "USCIS",
                "N-400",
                "paper filing fee",
                "small claims",
                "standard mileage rate",
                "filing fees",
                "fee schedule",
                "rate notice",
            ),
        ),
    ],
)
def test_table_driven_non_overfit_fact_kind_artifact_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    provider_title: str,
    provider_text: str,
    expected_query_terms: tuple[str, ...],
    expected_fact_kind: str,
    expected_value_kinds: list[str],
    expected_artifact_terms: tuple[str, ...],
    forbidden_terms: tuple[str, ...],
) -> None:
    tavily_calls: list[dict[str, Any]] = []

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        tavily_calls.append(kwargs)
        return (
            [
                {
                    "title": provider_title,
                    "url": "https://example.invalid/source-of-record",
                    "domain": "example.invalid",
                    "snippet": "Synthetic source-of-record fixture.",
                    "raw_content": provider_text,
                }
            ],
            [],
        )

    monkeypatch.setattr(product_acquisition, "search_web_results", fake_tavily)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=query,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id=f"planner-table-{expected_fact_kind}",
        confirm_live_dogfood=True,
        fetch_read_runner=_fake_fetch_runner("unused"),
        environ={},
    )
    packet = result.packet
    plan = packet["fast_planner_output"]
    acquisition_query = tavily_calls[0]["query"]
    serialized_plan = json.dumps(plan, sort_keys=True)

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert packet["acquisition_plan_consumed_by_product_path"] is True
    assert packet["provider_acquisition_query_from_plan"] is True
    assert plan["fact_kind"] == expected_fact_kind
    assert packet["expected_value_token_kinds"] == expected_value_kinds
    assert packet["selected_window_anchor_guidance_consumed"] is True
    assert packet["selected_window_value_token_guidance_consumed"] is True
    assert packet["selected_window_value_token_guidance_blocked"] is False
    assert plan["selected_window_guidance"]["selection_system_parallel_path_created"] is False

    for term in expected_query_terms:
        assert term in acquisition_query
    for term in expected_artifact_terms:
        assert term in packet["artifact_source_terms_used"]
    for term in forbidden_terms:
        assert term.casefold() not in acquisition_query.casefold()
        assert term.casefold() not in serialized_plan.casefold()

    fetch_packet = _retained_fetch_packet(result)
    selection = fetch_packet["reference_records"][0]["bounded_text_selection"]
    assert selection["value_token_guidance_consumed"] is True
    assert selection["expected_value_token_kinds"] == expected_value_kinds
    assert selection["matched_value_token_kind_count"] >= 1
