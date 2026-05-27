from __future__ import annotations

from typing import Any

from core.quantitative_consistency import (
    build_two_item_normalized_consistency_diagnostic,
)
from core.source_class_recovery import (
    apply_answer_contract_source_class_recovery_gap_trigger,
    build_recovery_source_quality_diagnostics,
    build_source_class_observability_telemetry,
    build_source_class_recovery_recommendation,
)
from tests.test_source_class_recovery_trace import _run_case


def _recommendation(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What are the current official rules for the program?",
        "current_date": "2026-05-22",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": "program current official rules",
        "primary_entity": "Program",
        "anchor_packet": None,
        "source_tier_counts": {"secondary": 2},
        "source_domain_counts": {"news.example": 2},
        "top_source_domains": [{"domain": "news.example", "count": 2}],
        "official_evidence_found": False,
    }
    base.update(overrides)
    return build_source_class_recovery_recommendation(**base)


def test_ag15_recovery_quality_counts_official_dot_source() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "title": "DOT official agency guidance",
                "url": "https://www.transportation.gov/briefing-room/current-rule",
                "text": "Official agency guidance explains the current rule and requirements.",
                "source_tier": "official",
            }
        ]
    )

    assert diagnostics["recovered_official_or_primary_count"] == 1
    assert diagnostics["recovered_source_class_counts"]["official_current_rules"] == 1
    assert diagnostics["recovery_source_quality_status"] == "official_or_primary_found"


def test_ag15_recovery_quality_counts_official_fda_source() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "title": "FDA guidance on current requirements",
                "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/example",
                "text": "FDA official guidance describes current requirements and enforcement status.",
                "source_tier": "official",
            }
        ]
    )

    assert diagnostics["recovered_official_or_primary_count"] == 1
    assert diagnostics["recovered_source_class_counts"]["official_current_rules"] == 1
    assert diagnostics["recovery_source_quality_status"] == "official_or_primary_found"


def test_ag15_recovery_quality_counts_legal_regulatory_authority_sources() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "title": "Federal Register final rule",
                "url": "https://www.federalregister.gov/documents/2026/01/01/example-final-rule",
                "text": "The Federal Register publishes the final rule and regulation text.",
                "source_tier": "official",
            },
            {
                "title": "eCFR 21 CFR Part 101",
                "url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-101",
                "text": "The eCFR contains current Code of Federal Regulations text.",
                "source_tier": "official",
            },
            {
                "title": "GovInfo statute compilation",
                "url": "https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/example.htm",
                "text": "GovInfo provides official statute and regulation source text.",
                "source_tier": "official",
            },
        ]
    )

    assert diagnostics["recovered_official_or_primary_count"] == 3
    assert diagnostics["recovered_source_class_counts"]["legal_or_regulatory_text"] == 3
    assert diagnostics["recovery_source_quality_status"] == "official_or_primary_found"


def test_ag15_recovery_quality_secondary_only_does_not_improve_official_counts() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "title": "News report about official agency rule",
                "url": "https://www.apnews.com/article/example-rule",
                "text": "A secondary report discusses what the agency said about the rule.",
                "source_tier": "secondary",
            },
            {
                "title": "Policy analysis",
                "url": "https://analysis.example/program-rule",
                "text": "A secondary policy analysis summarizes official guidance.",
                "source_tier": "secondary",
            },
        ]
    )

    assert diagnostics["recovered_official_or_primary_count"] == 0
    assert diagnostics["recovered_source_class_counts"] == {}
    assert diagnostics["recovery_source_quality_status"] == "secondary_only"


def test_ag15_recovered_official_source_is_visible_after_merge(tmp_path: Any) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
        recovery_source_tiers=["official"],
        recovery_domains=["transportation.gov"],
    )

    trace = outcome.execution_trace
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_provider_role"] == "source_class_recovery"
    assert trace["active_source_class_recovery_search_depth"] == "basic"
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert trace["recovered_official_or_primary_count"] == 1
    assert trace["recovered_accepted_url_count"] == 1
    assert trace["recovered_promoted_source_count"] == 1
    assert trace["recovered_source_class_counts"]["official_current_rules"] == 1
    assert trace["recovery_source_quality_status"] == "official_or_primary_found"
    assert trace["final_official_source_count"] >= 1


def test_ag15_recovery_queries_emphasize_official_and_legal_authority_sources() -> None:
    official = _recommendation(
        query="What are the current eligibility requirements and official rules?",
        core_topic="program current official eligibility requirements",
        primary_entity="Program",
        anchor_packet={
            "source_class_expectation": "official",
            "claim_or_metric_type": "rule",
            "freshness_requirement": "official-current",
        },
    )
    official_query_text = " ".join(official["source_class_recovery_queries"]).casefold()
    assert "official source" in official_query_text
    assert "agency guidance" in official_query_text
    assert "enforcement status" in official_query_text

    legal = apply_answer_contract_source_class_recovery_gap_trigger(
        recommendation={
            "source_class_recovery_recommended": False,
            "missing_expected_source_classes": [],
            "source_class_recovery_queries": [],
            "source_class_recovery_reason": None,
        },
        answer_contract_family="legal_or_regulatory_primary_text",
        answer_contract_source_classes_missing=("legal_or_regulatory_text",),
        answer_contract_unfulfilled_items=(),
        answer_contract_partial_items=(),
        query="What does the current statute and regulation require?",
        core_topic="current statute and regulation",
        primary_entity="Example Act",
    )
    legal_query_text = " ".join(legal["source_class_recovery_queries"]).casefold()
    assert "federal register" in legal_query_text
    assert "govinfo" in legal_query_text
    assert "ecfr" in legal_query_text


def test_ag15_historical_archival_control_does_not_become_current_official() -> None:
    telemetry = build_source_class_observability_telemetry(
        query="Find historical public health orders using archival primary-source text.",
        intent="history",
        report_type="general_research",
        query_type="history",
        core_topic="historical public health orders archival primary source text",
        primary_entity="public health orders",
        anchor_packet=None,
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Secondary historical overview",
                "url": "https://history.example/orders",
                "text": "Secondary history summarizes archival public health orders.",
                "source_tier": "secondary",
            }
        ],
    )

    assert "archival_primary_text" in telemetry["source_class_gap_candidates"]
    assert "official_current_rules" not in telemetry["source_class_gap_candidates"]


def test_ag15_protein_bar_quantitative_control_does_not_trigger_source_recovery() -> None:
    out = _recommendation(
        query=(
            "A protein bar has 220 calories / 60g and another has "
            "170 calories / 45g. Which is more calorie-dense?"
        ),
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="protein bar calorie density comparison",
        primary_entity="protein bar",
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []


def test_ag15_quantitative_consistency_flags_wrong_stated_winner() -> None:
    diagnostics = build_two_item_normalized_consistency_diagnostic(
        query=(
            "A protein bar has 220 calories / 60g and another has "
            "170 calories / 45g. Which is more calorie-dense?"
        ),
        final_answer=(
            "The 220 calorie / 60g bar is more calorie-dense. "
            "The normalized values are 3.67 and 3.78 calories per gram."
        ),
    )

    assert diagnostics["quantitative_consistency_check_attempted"] is True
    assert diagnostics["quantitative_consistency_contradiction_flag"] is True
    assert diagnostics["quantitative_consistency_status"] == "contradiction_detected"
    assert diagnostics["quantitative_consistency_computed_winner"] == "item_b"
    assert diagnostics["quantitative_consistency_stated_winner"] == "item_a"


def test_ag15_quantitative_consistency_passes_correct_stated_winner() -> None:
    diagnostics = build_two_item_normalized_consistency_diagnostic(
        query=(
            "A protein bar has 220 calories / 60g and another has "
            "170 calories / 45g. Which is more calorie-dense?"
        ),
        final_answer=(
            "The 170 calorie / 45g bar is more calorie-dense. "
            "It is about 3.78 calories per gram versus about 3.67."
        ),
    )

    assert diagnostics["quantitative_consistency_check_attempted"] is True
    assert diagnostics["quantitative_consistency_contradiction_flag"] is False
    assert diagnostics["quantitative_consistency_status"] == "consistent"
    assert diagnostics["quantitative_consistency_computed_winner"] == "item_b"
    assert diagnostics["quantitative_consistency_stated_winner"] == "item_b"


def test_ag15_quantitative_consistency_uses_structured_calculation_when_available() -> None:
    diagnostics = build_two_item_normalized_consistency_diagnostic(
        query="Which bar is more calorie-dense?",
        final_answer="The 220 calorie / 60g bar is denser.",
        source_bound_values=[
            {"name": "bar_a_calories", "value": 220, "unit": "calories"},
            {"name": "bar_a_grams", "value": 60, "unit": "g"},
            {"name": "bar_b_calories", "value": 170, "unit": "calories"},
            {"name": "bar_b_grams", "value": 45, "unit": "g"},
        ],
        calculation_results=[
            {
                "name": "normalize_per_100g",
                "item_id": "item_a",
                "result": 366.67,
                "input_refs": {
                    "value": "bar_a_calories",
                    "serving_grams": "bar_a_grams",
                },
            },
            {
                "name": "normalize_per_100g",
                "item_id": "item_b",
                "result": 377.78,
                "input_refs": {
                    "value": "bar_b_calories",
                    "serving_grams": "bar_b_grams",
                },
            },
        ],
    )

    assert diagnostics["quantitative_consistency_status"] == "contradiction_detected"
    assert diagnostics["quantitative_consistency_computed_winner"] == "item_b"
