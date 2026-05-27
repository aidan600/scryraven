from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.pipeline import (
    _quant_retrieval_sufficiency_shadow_telemetry,
    detect_target_metric_buckets,
    economist_high_stakes_quant_telemetry_defaults,
    economist_quantitative_packet_telemetry_defaults,
    execute_economist_calculations_shadow,
    quant_retrieval_sufficiency_telemetry_defaults,
    run_economist_code,
    run_economist_step,
    validate_economist_schema_v1,
    validate_economist_source_bindings,
    validate_high_stakes_quantitative_query_shadow,
    validate_high_stakes_quantitative_shadow,
    validate_target_metric_shadow,
)
from core.prompts import DEFAULT_SYSTEM


def _run_economist_payload(
    *,
    query: str,
    payload: dict[str, Any],
    all_passages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(payload)

    result = run_economist_step(
        core_topic=query,
        all_passages=all_passages
        or [
            {"source_id": 1, "text": "Old revenue was 100 USD."},
            {"source_id": 2, "text": "New revenue was 150 USD."},
        ],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    return telemetry


def _valid_target_metric_shadow(
    *,
    query: str,
    source_bound_values: list[dict[str, Any]],
    calculation_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return validate_target_metric_shadow(
        query=query,
        payload={"source_bound_values": source_bound_values, "unsupported_values": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": calculation_results or []},
    )


def _quant_sufficiency_base_passages() -> list[dict[str, Any]]:
    return [
        {
            "source_id": 1,
            "title": "Alpha Air 2025 operating metrics",
            "url": "https://alpha.example/report",
            "text": "Alpha Air cost per seat mile was 8 cents in 2025.",
        },
        {
            "source_id": 2,
            "title": "Beta Air 2025 operating metrics",
            "url": "https://beta.example/report",
            "text": "Beta Air cost per seat mile was 10 cents in 2025.",
        },
    ]


def _quant_sufficiency_base_values() -> list[dict[str, Any]]:
    return [
        {
            "entity": "Alpha Air",
            "name": "cost_per_seat_mile",
            "value": "8",
            "unit": "cents per seat mile",
            "source_id": "1",
            "year": "2025",
        },
        {
            "entity": "Beta Air",
            "name": "cost_per_seat_mile",
            "value": "10",
            "unit": "cents per seat mile",
            "source_id": "2",
            "year": "2025",
        },
    ]


def _costco_walmart_fy2024_revenue_passages() -> list[dict[str, Any]]:
    return [
        {
            "source_id": 1,
            "title": "Costco Q4 2024 and fiscal 2024 results",
            "url": "https://costco.example/fy2024",
            "text": "Costco Q4 2024 results also reported fiscal 2024 revenue of $254.45 billion.",
        },
        {
            "source_id": 2,
            "title": "Walmart fiscal 2024 results",
            "url": "https://walmart.example/fy2024",
            "text": "Walmart fiscal 2024 revenue was $648.13 billion.",
        },
    ]


def _costco_walmart_fy2024_revenue_values() -> list[dict[str, Any]]:
    return [
        {
            "entity": "Costco",
            "name": "costco_fy2024_revenue",
            "metric": "revenue",
            "value": "254.45",
            "unit": "USD billions",
            "source_id": "1",
            "period": "fiscal 2024",
        },
        {
            "entity": "Walmart",
            "name": "walmart_fy2024_revenue",
            "metric": "revenue",
            "value": "648.13",
            "unit": "USD billions",
            "source_id": "2",
            "period": "fiscal 2024",
        },
    ]


def _run_costco_walmart_revenue_packet(
    *,
    source_bound_values: list[dict[str, Any]],
    query: str = "Compare Costco vs Walmart on fiscal 2024 revenue.",
    calculations_requested: list[dict[str, Any]] | None = None,
    unsupported_values: list[str] | None = None,
) -> dict[str, Any]:
    return _run_economist_payload(
        query=query,
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": source_bound_values,
            "assumptions": [],
            "calculations_requested": calculations_requested or [],
            "confidence": "medium",
            "unsupported_values": unsupported_values or [],
        },
        all_passages=_costco_walmart_fy2024_revenue_passages(),
    )


def test_quant_retrieval_sufficiency_defaults_are_non_quantitative() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Summarize Alpha Air's strategy.",
        report_type="general_research",
        final_top_evidence=_quant_sufficiency_base_passages(),
    )

    assert telemetry == quant_retrieval_sufficiency_telemetry_defaults()
    assert telemetry["quant_retrieval_target_detected"] is False
    assert telemetry["quant_retrieval_sufficiency_valid"] is False
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == "not_quantitative_target"
    assert telemetry["quant_retrieval_sufficiency_blockers"] == []


def test_quant_retrieval_sufficiency_clean_bounded_comparison_valid() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=_quant_sufficiency_base_values(),
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_target_detected"] is True
    assert telemetry["quant_retrieval_comparison_subjects"] == ["Alpha Air", "Beta Air"]
    assert telemetry["quant_retrieval_entity_coverage_valid"] is True
    assert telemetry["quant_retrieval_metric_coverage_valid"] is True
    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is True
    assert telemetry["quant_retrieval_comparison_coverage_valid"] is True
    assert telemetry["quant_retrieval_exact_value_binding_valid"] is True
    assert telemetry["quant_retrieval_source_diversity_count"] == 2
    assert telemetry["quant_retrieval_sufficiency_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_blockers"] == []
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == "sufficient_shadow_only"


def test_quant_retrieval_sufficiency_router_entities_strip_fiscal_context() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Costco vs Walmart on fiscal 2024 revenue.",
        report_type="quantitative_comparison",
        final_top_evidence=_costco_walmart_fy2024_revenue_passages(),
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
        router_entities=["Costco", "Walmart"],
    )

    assert telemetry["quant_retrieval_entities"] == ["Costco", "Walmart"]
    assert telemetry["quant_retrieval_comparison_subjects"] == ["Costco", "Walmart"]
    assert "Walmart on fiscal 2024" not in telemetry["quant_retrieval_entities"]
    assert "financial_line_item" in telemetry["quant_retrieval_metrics"]
    assert telemetry["quant_retrieval_timeframes"] == ["2024"]
    assert telemetry["quant_retrieval_entity_coverage_valid"] is True
    assert telemetry["quant_retrieval_comparison_coverage_valid"] is True
    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_blockers"] == []


@pytest.mark.parametrize(
    ("time_field", "time_value"),
    [
        ("period", "fiscal 2024"),
        ("year", "2024"),
        ("timeframe", "FY2024"),
    ],
)
def test_quant_retrieval_sufficiency_normalizes_annual_requested_timeframes(
    time_field: str,
    time_value: str,
) -> None:
    values: list[dict[str, Any]] = []
    for item in _costco_walmart_fy2024_revenue_values():
        value = {
            key: item_value
            for key, item_value in item.items()
            if key not in {"period", "year", "timeframe"}
        }
        value[time_field] = time_value
        values.append(value)

    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Costco vs Walmart on FY2024 revenue.",
        report_type="quantitative_comparison",
        final_top_evidence=_costco_walmart_fy2024_revenue_passages(),
        source_bound_values=values,
        router_entities=["Costco", "Walmart"],
    )

    assert telemetry["quant_retrieval_timeframes"] == ["2024"]
    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_valid"] is True


def test_quant_retrieval_sufficiency_one_annual_entity_still_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Costco vs Walmart on fiscal 2024 revenue.",
        report_type="quantitative_comparison",
        final_top_evidence=_costco_walmart_fy2024_revenue_passages()[:1],
        source_bound_values=_costco_walmart_fy2024_revenue_values()[:1],
        router_entities=["Costco", "Walmart"],
    )

    assert telemetry["quant_retrieval_sufficiency_valid"] is False
    assert "missing_entity_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "missing_comparison_coverage" in telemetry[
        "quant_retrieval_sufficiency_blockers"
    ]


def test_quant_retrieval_sufficiency_quarterly_side_blocks_full_year_query() -> None:
    passages = [
        _costco_walmart_fy2024_revenue_passages()[0],
        {
            "source_id": 2,
            "title": "Walmart Q4 fiscal 2024 results",
            "url": "https://walmart.example/q4-2024",
            "text": "Walmart Q4 2024 revenue was $173.39 billion.",
        },
    ]
    values = [
        _costco_walmart_fy2024_revenue_values()[0],
        {
            "entity": "Walmart",
            "name": "walmart_q4_2024_revenue",
            "value": "173.39",
            "unit": "USD billions",
            "source_id": "2",
            "period": "Q4 2024",
        },
    ]

    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Costco vs Walmart on fiscal 2024 revenue.",
        report_type="quantitative_comparison",
        final_top_evidence=passages,
        source_bound_values=values,
        router_entities=["Costco", "Walmart"],
    )

    assert telemetry["quant_retrieval_entity_coverage_valid"] is True
    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is False
    assert "timeframe_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_broad_comparison_does_not_invent_metric() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Costco vs Walmart.",
        report_type="quantitative_comparison",
        final_top_evidence=_costco_walmart_fy2024_revenue_passages(),
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
        router_entities=["Costco", "Walmart"],
    )

    assert "comparative_terms" in telemetry["quant_retrieval_metrics"]
    assert "financial_line_item" not in telemetry["quant_retrieval_metrics"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_missing_entity_coverage_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2025 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in 2025.",
            }
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            }
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_sufficiency_valid"] is False
    assert "missing_entity_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "missing_comparison_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]


def test_quant_retrieval_sufficiency_proxy_metric_only_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Airline utilization metrics",
                "url": "https://air.example/load-factor",
                "text": "Alpha Air and Beta Air reported 2025 load factor and revenue.",
            }
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "load_factor",
                "value": "84",
                "unit": "%",
                "source_id": "1",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "revenue",
                "value": "100",
                "unit": "USD",
                "source_id": "1",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_proxy_metric_detected"] is True
    assert telemetry["quant_retrieval_metric_coverage_valid"] is False
    assert "proxy_metric_only" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_missing_timeframe_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in Q4 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2024 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in Q4 2024.",
            },
            {
                "source_id": 2,
                "title": "Beta Air 2024 operating metrics",
                "url": "https://beta.example/report",
                "text": "Beta Air cost per seat mile was 10 cents in Q4 2024.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "period": "Q4 2024",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "2",
                "period": "Q4 2024",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is False
    assert "timeframe_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_missing_value_source_binding_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "99",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_exact_value_binding_valid"] is False
    assert "value_source_binding_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_low_source_diversity_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Airline comparison table",
                "url": "https://air.example/table",
                "text": (
                    "Alpha Air cost per seat mile was 8 cents in 2025. "
                    "Beta Air cost per seat mile was 10 cents in 2025."
                ),
            }
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_source_diversity_count"] == 1
    assert "low_source_diversity" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_benchmark_report_type_valid() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Benchmark Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="benchmark",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=_quant_sufficiency_base_values(),
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_sufficiency_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_blockers"] == []
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == "sufficient_shadow_only"


def test_quant_retrieval_sufficiency_no_explicit_timeframe_does_not_block() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=_quant_sufficiency_base_values(),
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_timeframes"] == []
    assert telemetry["quant_retrieval_timeframe_coverage_valid"] is True
    assert "timeframe_missing" not in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is True


def test_quant_retrieval_sufficiency_uses_packet_source_bound_values() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        economist_safety_telemetry={
            "quantitative_packet": {
                "source_bound_values": _quant_sufficiency_base_values(),
            }
        },
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_exact_value_binding_valid"] is True
    assert telemetry["quant_retrieval_entity_coverage_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == "sufficient_shadow_only"


def test_quant_retrieval_sufficiency_equivalent_metric_wording_passes() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on unit cost in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2025 operating expense table",
                "url": "https://alpha-air.test/report",
                "text": "Alpha Air expense per trip was 8 USD in 2025.",
            },
            {
                "source_id": 2,
                "title": "Beta Air 2025 operating expense table",
                "url": "https://beta-air.test/report",
                "text": "Beta Air expense per trip was 10 USD in 2025.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "unit_cost",
                "value": "8",
                "unit": "USD per trip",
                "source_id": "1",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "unit_cost",
                "value": "10",
                "unit": "USD per trip",
                "source_id": "2",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_metric_coverage_valid"] is True
    assert telemetry["quant_retrieval_proxy_metric_detected"] is False
    assert "proxy_metric_only" not in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is True


def test_quant_retrieval_sufficiency_unknown_comparison_subjects_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Cost table",
                "url": "https://one.example/report",
                "text": "Cost per seat mile was 8 cents in 2025.",
            },
            {
                "source_id": 2,
                "title": "Cost table",
                "url": "https://two.example/report",
                "text": "Cost per seat mile was 10 cents in 2025.",
            },
        ],
        source_bound_values=[
            {
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            },
            {
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "2",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "comparison_subjects_unknown" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_missing_comparison_coverage"
    )
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_nutrition_single_entity_source_bound_values() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="salmon protein and calories per 100g",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Salmon nutrition facts",
                "url": "https://nutrition.example/salmon",
                "text": "Salmon has 208 calories and 20 g protein per 100g.",
            }
        ],
        source_bound_values=[
            {
                "entity": "salmon",
                "name": "calories",
                "value": "208",
                "unit": "kcal per 100g",
                "source_id": "1",
            },
            {
                "entity": "salmon",
                "name": "protein",
                "value": "20",
                "unit": "g per 100g",
                "source_id": "1",
            },
        ],
        nutrition_lookup_telemetry={
            "nutrition_lookup_detected": True,
            "nutrition_lookup_reason": "nutrition_metric_per_100g",
            "nutrition_lookup_metrics_requested": ["protein", "calories"],
            "nutrition_lookup_unit": "per_100g",
            "nutrition_lookup_shadow_mode": True,
        },
        nutrition_lookup_entity="salmon",
    )

    assert "comparison_subjects_unknown" not in telemetry[
        "quant_retrieval_sufficiency_blockers"
    ]
    assert telemetry["quant_retrieval_comparison_coverage_valid"] is True
    assert telemetry["quant_retrieval_sufficiency_valid"] is True


def test_quant_retrieval_sufficiency_nutrition_partial_macro_coverage_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="silver round herring macros per 100g",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Silver round herring calories",
                "url": "https://nutrition.example/herring",
                "text": "Silver round herring has 93 kcal per 100g.",
            }
        ],
        source_bound_values=[
            {
                "entity": "silver round herring",
                "name": "calories",
                "value": "93",
                "unit": "kcal per 100g",
                "source_id": "1",
            }
        ],
        nutrition_lookup_telemetry={
            "nutrition_lookup_detected": True,
            "nutrition_lookup_reason": "nutrition_metric_per_100g",
            "nutrition_lookup_metrics_requested": [
                "calories",
                "protein",
                "fat",
                "carbohydrates",
            ],
            "nutrition_lookup_unit": "per_100g",
            "nutrition_lookup_shadow_mode": True,
        },
        nutrition_lookup_entity="silver round herring",
    )

    blockers = telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False
    assert "comparison_subjects_unknown" not in blockers
    assert "nutrition_metrics_missing" in blockers
    assert "nutrition_partial_macro_coverage" in blockers


def test_quant_retrieval_sufficiency_one_comparison_subject_missing_blocks() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2025 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in 2025.",
            },
            {
                "source_id": 2,
                "title": "Alpha Air supplemental table",
                "url": "https://alpha.example/supplement",
                "text": "Alpha Air cost data was audited in 2025.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            }
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "missing_entity_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "missing_comparison_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_wrong_year_blocks_with_timeframe_reason() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2024 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in 2024.",
            },
            {
                "source_id": 2,
                "title": "Beta Air 2024 operating metrics",
                "url": "https://beta.example/report",
                "text": "Beta Air cost per seat mile was 10 cents in 2024.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2024",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "2",
                "year": "2024",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "timeframe_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_missing_timeframe_coverage"
    )
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_unknown_source_id_blocks() -> None:
    values = _quant_sufficiency_base_values()
    values[1] = {**values[1], "source_id": "99"}

    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=values,
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_exact_value_binding_valid"] is False
    assert "value_source_binding_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_valid"] is False


def test_quant_retrieval_sufficiency_proxy_metric_reason_has_priority() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Airline usage table",
                "url": "https://air.example/usage",
                "text": "Alpha Air and Beta Air reported 2025 load factor only.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "load_factor",
                "value": "84",
                "unit": "%",
                "source_id": "1",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "load_factor",
                "value": "80",
                "unit": "%",
                "source_id": "1",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "missing_metric_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "proxy_metric_only" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == "blocked_by_proxy_metric"


def test_quant_retrieval_sufficiency_value_source_binding_reason_has_priority() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=_quant_sufficiency_base_passages(),
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "99",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "proxy_metric_only" not in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "value_source_binding_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_value_source_binding"
    )


def test_quant_retrieval_sufficiency_timeframe_reason_has_priority() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in Q4 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air Q4 2024 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in Q4 2024.",
            },
            {
                "source_id": 2,
                "title": "Beta Air Q4 2024 operating metrics",
                "url": "https://beta.example/report",
                "text": "Beta Air cost per seat mile was 10 cents in Q4 2024.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "period": "Q4 2024",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "2",
                "period": "Q4 2024",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "timeframe_missing" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_missing_timeframe_coverage"
    )


def test_quant_retrieval_sufficiency_comparison_reason_has_priority() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2025 operating metrics",
                "url": "https://alpha.example/report",
                "text": "Alpha Air cost per seat mile was 8 cents in 2025.",
            },
            {
                "source_id": 2,
                "title": "Alpha Air supplemental metrics",
                "url": "https://alpha-supplement.example/report",
                "text": "Alpha Air cost per seat mile was audited in 2025.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            }
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert "missing_comparison_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_missing_comparison_coverage"
    )


def test_quant_retrieval_sufficiency_low_source_diversity_reason_has_priority() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha Air vs Beta Air on cost per seat mile in 2025.",
        report_type="quantitative_comparison",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Alpha Air 2025 operating metrics",
                "url": "https://air.example/alpha",
                "text": "Alpha Air cost per seat mile was 8 cents in 2025.",
            },
            {
                "source_id": 2,
                "title": "Beta Air 2025 operating metrics",
                "url": "https://air.example/beta",
                "text": "Beta Air cost per seat mile was 10 cents in 2025.",
            },
        ],
        source_bound_values=[
            {
                "entity": "Alpha Air",
                "name": "cost_per_seat_mile",
                "value": "8",
                "unit": "cents per seat mile",
                "source_id": "1",
                "year": "2025",
            },
            {
                "entity": "Beta Air",
                "name": "cost_per_seat_mile",
                "value": "10",
                "unit": "cents per seat mile",
                "source_id": "2",
                "year": "2025",
            },
        ],
        target_metric_names=["price_cost_rate"],
    )

    assert telemetry["quant_retrieval_source_diversity_count"] == 1
    assert telemetry["quant_retrieval_sufficiency_blockers"] == ["low_source_diversity"]
    assert telemetry["quant_retrieval_sufficiency_gate_reason"] == (
        "blocked_by_low_source_diversity"
    )


def test_run_economist_code_blocks_python_side_effect(tmp_path: Path) -> None:
    marker = tmp_path / "economist_side_effect.txt"
    payload = f"from pathlib import Path\nPath({str(marker)!r}).write_text('owned')"

    result = run_economist_code(payload)

    assert not marker.exists()
    assert result["computed"] == {}
    assert result["error"] == "dynamic_code_execution_disabled"
    assert result["economist_code_execution_requested"] is True
    assert result["economist_code_execution_blocked"] is True
    assert result["economist_safety_status"] == "code_execution_disabled"
    assert result["economist_skip_reason"] == "dynamic_code_execution_disabled"


def test_run_economist_step_blocks_legacy_python_code_payload(tmp_path: Path) -> None:
    marker = tmp_path / "economist_step_side_effect.txt"
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "assumptions": ["synthetic assumption"],
                "python_code": f"from pathlib import Path\nPath({str(marker)!r}).write_text('owned')",
                "reasoning": "legacy executable payload",
            }
        )

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert not marker.exists()
    assert telemetry["economist_code_execution_requested"] is True
    assert telemetry["economist_code_execution_blocked"] is True
    assert telemetry["economist_safety_status"] == "code_execution_disabled"
    assert telemetry["economist_skip_reason"] == "dynamic_code_execution_disabled"
    assert telemetry["economist_schema_valid"] is False
    assert "missing:schema_version" in telemetry["economist_invalid_fields"]
    for key in economist_quantitative_packet_telemetry_defaults():
        assert key in telemetry
    assert telemetry["quantitative_packet_direct_use_eligible"] is False


def test_run_economist_step_blocks_nested_code_request_payload(tmp_path: Path) -> None:
    marker = tmp_path / "economist_nested_side_effect.txt"
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [
                    {"name": "unit_cost", "value": "10", "unit": "USD", "source_id": "1"}
                ],
                "assumptions": [],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": [],
                "nested_payload": {
                    "python_code": (
                        "from pathlib import Path\n"
                        f"Path({str(marker)!r}).write_text('owned')"
                    ),
                    "commands": [
                        "subprocess.run(['python', '-c', 'print(1)'])",
                        {"derived": "eval('1 + 1')"},
                        {"audit": "exec('print(2)')"},
                        {"shell": "bash -c echo owned"},
                        "```python\nprint('owned')\n```",
                    ],
                },
            }
        )

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert not marker.exists()
    assert telemetry["economist_code_execution_requested"] is True
    assert telemetry["economist_code_execution_blocked"] is True
    assert telemetry["economist_safety_status"] == "code_execution_disabled"
    assert telemetry["economist_skip_reason"] == "dynamic_code_execution_disabled"
    assert telemetry["calculation_results"] == []


def test_run_economist_step_empty_payload_not_code_requested() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return "{}"

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_code_execution_requested"] is False
    assert telemetry["economist_code_execution_blocked"] is False
    assert telemetry["economist_safety_status"] == "code_execution_disabled"
    assert telemetry["economist_skip_reason"] is None
    assert "missing:schema_version" in telemetry["economist_invalid_fields"]
    assert telemetry["calculation_results"] == []


def test_run_economist_step_valid_schema_records_shadow_telemetry() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [{"name": "unit_cost", "value": "10", "unit": "USD"}],
                "source_bound_values": [
                    {"name": "unit_cost", "value": "10", "unit": "USD", "source_id": "1"}
                ],
                "assumptions": ["synthetic assumption"],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": ["second vendor unit cost"],
            }
        )

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_code_execution_requested"] is False
    assert telemetry["economist_code_execution_blocked"] is False
    assert telemetry["economist_safety_status"] == "code_execution_disabled"
    assert telemetry["economist_skip_reason"] is None
    assert telemetry["economist_schema_valid"] is True
    assert telemetry["economist_schema_version"] == "economist_v1"
    assert telemetry["economist_invalid_fields"] == []
    assert telemetry["unsupported_values_count"] == 1
    assert telemetry["economist_shadow_mode"] is True
    assert telemetry["source_binding_valid"] is True
    assert telemetry["source_bound_value_count"] == 1
    assert telemetry["source_binding_invalid_fields"] == []
    assert telemetry["source_binding_missing_source_id_count"] == 0
    assert telemetry["source_binding_unknown_source_id_count"] == 0
    assert telemetry["source_binding_malformed_count"] == 0
    assert telemetry["source_ids_seen"] == ["1"]
    assert telemetry["source_ids_used"] == ["1"]
    assert telemetry["economist_evidence_source_ids_seen"] == ["1"]
    assert telemetry["economist_evidence_source_ids_used"] == ["1"]
    assert telemetry["economist_source_ids_used_outside_evidence_window"] == []
    assert telemetry["source_binding_shadow_mode"] is True
    assert telemetry["calculation_requests_count"] == 0
    assert telemetry["calculation_results_shadow_mode"] is True
    assert telemetry["calculation_results"] == []
    assert telemetry["target_metric_shadow_mode"] is True
    assert telemetry["target_metric_detected"] is True
    assert telemetry["target_metric_names"] == ["price_cost_rate"]
    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["target_metric_shadow_would_block"] is True


def test_run_economist_step_records_window_and_binds_walmart_fy2024_revenue() -> None:
    telemetry: dict[str, Any] = {}
    prompts: list[str] = []

    def ask_model(prompt: str, *_args: Any, **_kwargs: Any) -> str:
        prompts.append(prompt)
        assert "[2]" in prompt
        assert "Walmart total revenues reached USD 648 billion in fiscal 2024." in prompt
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [
                    {
                        "name": "costco_fy2024_total_revenue",
                        "entity": "Costco",
                        "metric": "annual revenue",
                        "period": "fiscal 2024",
                        "value": "254.453",
                        "unit": "USD billion",
                        "source_id": "1",
                    },
                    {
                        "name": "walmart_fy2024_total_revenue",
                        "entity": "Walmart",
                        "metric": "total revenue",
                        "period": "fiscal 2024",
                        "value": "648",
                        "unit": "USD billion",
                        "source_id": "2",
                    },
                ],
                "assumptions": [],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    all_passages = [
        {
            "source_id": 1,
            "text": "Costco fiscal 2024 annual revenue was USD 254.453 billion.",
        },
        {
            "source_id": 2,
            "text": "Walmart total revenues reached USD 648 billion in fiscal 2024.",
        },
    ] + [
        {"source_id": source_id, "text": f"Later evidence chunk {source_id}."}
        for source_id in range(3, 25)
    ]

    result = run_economist_step(
        core_topic="Compare Costco vs Walmart on fiscal 2024 revenue.",
        all_passages=all_passages,
        current_date="2026-05-10",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
        user_query="Compare Costco vs Walmart on fiscal 2024 revenue.",
    )

    assert result is None
    assert prompts
    assert set(telemetry["economist_evidence_source_ids_seen"]) == {
        str(source_id) for source_id in range(1, 21)
    }
    assert "21" not in telemetry["economist_evidence_source_ids_seen"]
    assert telemetry["economist_evidence_source_ids_used"] == ["1", "2"]
    assert telemetry["economist_source_ids_used_outside_evidence_window"] == []
    assert telemetry["quantitative_packet_valid"] is True
    packet = telemetry["quantitative_packet"]
    assert packet["source_ids_used"] == ["1", "2"]
    assert {
        item["name"] for item in packet["source_bound_values"]
    } >= {"costco_fy2024_total_revenue", "walmart_fy2024_total_revenue"}


def test_run_economist_step_unknown_source_id_records_invalid_binding() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [{"name": "unit_cost", "value": "10", "unit": "USD"}],
                "source_bound_values": [
                    {"name": "unit_cost", "value": "10", "unit": "USD", "source_id": "missing"}
                ],
                "assumptions": [],
                "calculations_requested": [
                    {"name": "difference", "args": {"a": "unit_cost", "b": "unit_cost"}}
                ],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_schema_valid"] is True
    assert telemetry["source_binding_valid"] is False
    assert telemetry["source_binding_unknown_source_id_count"] == 1
    assert telemetry["source_binding_missing_source_id_count"] == 0
    assert telemetry["source_binding_malformed_count"] == 0
    assert telemetry["source_ids_seen"] == ["1"]
    assert telemetry["source_ids_used"] == ["missing"]
    assert "unknown_source_id:source_bound_values[0].source_id" in telemetry[
        "source_binding_invalid_fields"
    ]
    assert telemetry["calculation_success_count"] == 0
    assert telemetry["calculation_results"] == []


def test_validate_economist_source_bindings_records_malformed_item() -> None:
    telemetry = validate_economist_source_bindings(
        {
            "source_bound_values": [
                "not a dict",
                {"name": "unit_cost", "value": "10", "source_id": 7},
            ]
        },
        {"7"},
    )

    assert telemetry["source_binding_valid"] is False
    assert telemetry["source_bound_value_count"] == 2
    assert telemetry["source_binding_malformed_count"] == 1
    assert telemetry["source_binding_unknown_source_id_count"] == 0
    assert telemetry["source_ids_seen"] == ["7"]
    assert telemetry["source_ids_used"] == ["7"]
    assert "malformed:source_bound_values[0]" in telemetry["source_binding_invalid_fields"]


def test_run_economist_step_narrative_response_records_parse_error() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return "A narrative response with figures, but no parseable schema."

    result = run_economist_step(
        core_topic="synthetic unit cost",
        all_passages=[{"source_id": 1, "text": "The synthetic unit cost was 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_schema_valid"] is False
    assert telemetry["economist_schema_version"] is None
    assert "parse_error" in telemetry["economist_invalid_fields"]
    assert telemetry["unsupported_values_count"] == 0
    assert telemetry["economist_shadow_mode"] is True
    assert telemetry["target_metric_shadow_mode"] is True
    assert telemetry["target_metric_detected"] is False
    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["quantitative_packet_present"] is False
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert telemetry["quantitative_packet_gate_reason"] == "not_quantitative"


def test_validate_economist_schema_v1_rejects_bad_field_types() -> None:
    telemetry = validate_economist_schema_v1(
        {
            "schema_version": "economist_v1",
            "variables": {},
            "source_bound_values": [],
            "assumptions": [],
            "calculations_requested": [],
            "confidence": "certain",
            "unsupported_values": [],
        }
    )

    assert telemetry["economist_schema_valid"] is False
    assert "type:variables" in telemetry["economist_invalid_fields"]
    assert "value:confidence" in telemetry["economist_invalid_fields"]


def test_economist_shadow_calculation_positive_records_result_and_returns_none() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [
                    {"name": "old_revenue", "value": "$1.0M", "unit": "USD", "source_id": "1"},
                    {"name": "new_revenue", "value": "$1.5M", "unit": "USD", "source_id": "2"},
                ],
                "assumptions": [],
                "calculations_requested": [
                    {
                        "name": "percent_change",
                        "args": {"old": "old_revenue", "new": "new_revenue"},
                    }
                ],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    result = run_economist_step(
        core_topic="synthetic revenue change",
        all_passages=[
            {"source_id": 1, "text": "Old revenue was $1.0M."},
            {"source_id": 2, "text": "New revenue was $1.5M."},
        ],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_code_execution_requested"] is False
    assert telemetry["economist_code_execution_blocked"] is False
    assert telemetry["calculation_requests_count"] == 1
    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["calculation_results_count"] == 1
    assert telemetry["calculation_results"][0]["result"] == 0.5
    assert telemetry["target_metric_detected"] is True
    assert "growth_change" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_calculation_refs"] == ["percent_change"]
    assert telemetry["target_metric_shadow_would_block"] is False


def test_quantitative_packet_valid_non_high_stakes_revenue_growth() -> None:
    telemetry = _run_economist_payload(
        query="What was revenue growth?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "unit": "USD", "source_id": "1"},
                {"name": "new_revenue", "value": "150", "unit": "USD", "source_id": "2"},
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
    )

    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is True
    assert telemetry["quantitative_packet_direct_use_eligible"] is True
    assert telemetry["quantitative_packet_requires_analyst"] is False
    assert telemetry["quantitative_packet_shadow_mode"] is True
    assert telemetry["quantitative_packet_gate_reason"] == "valid_non_high_stakes_packet"
    assert telemetry["quantitative_packet_validation_errors"] == []
    packet = telemetry["quantitative_packet"]
    assert packet["schema_version"] == "quantitative_packet_v1"
    assert packet["calculation_results"][0]["name"] == "percent_change"
    assert packet["target_metric_calculation_refs"] == ["percent_change"]
    assert packet["direct_use_eligible"] is True
    assert packet["requires_analyst"] is False


def test_quantitative_packet_valid_difference_accepts_semantic_arg_aliases() -> None:
    telemetry = _run_economist_payload(
        query="Compare Costco vs Walmart fiscal 2024 revenue delta.",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {
                    "name": "costco_fy2024_revenue",
                    "value": "254.45",
                    "unit": "USD billions",
                    "source_id": "1",
                },
                {
                    "name": "walmart_fy2024_revenue",
                    "value": "648.13",
                    "unit": "USD billions",
                    "source_id": "2",
                },
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "minuend": "walmart_fy2024_revenue",
                        "subtrahend": "costco_fy2024_revenue",
                    },
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[
            {"source_id": 1, "text": "Costco fiscal 2024 revenue was $254.45 billion."},
            {"source_id": 2, "text": "Walmart fiscal 2024 revenue was $648.13 billion."},
        ],
    )

    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is True
    assert telemetry["quantitative_packet_direct_use_eligible"] is True
    packet = telemetry["quantitative_packet"]
    result = packet["calculation_results"][0]
    assert result["name"] == "difference"
    assert result["result"] == pytest.approx(393.68)
    assert result["input_refs"] == {
        "a": "walmart_fy2024_revenue",
        "b": "costco_fy2024_revenue",
    }
    assert packet["direct_use_eligible"] is True
    assert packet["requires_analyst"] is False


def test_quantitative_packet_high_stakes_medical_requires_analyst() -> None:
    telemetry = _run_economist_payload(
        query="Does treatment A lower A1C more than treatment B?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {
                    "name": "treatment_a_a1c",
                    "value": "7.1",
                    "unit": "%",
                    "source_id": "1",
                },
                {
                    "name": "treatment_b_a1c",
                    "value": "8.0",
                    "unit": "%",
                    "source_id": "2",
                },
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {"a": "treatment_a_a1c", "b": "treatment_b_a1c"},
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[
            {"source_id": 1, "text": "Treatment A mean A1C was 7.1%."},
            {"source_id": 2, "text": "Treatment B mean A1C was 8.0%."},
        ],
    )

    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is True
    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert telemetry["quantitative_packet_requires_analyst"] is True
    assert telemetry["quantitative_packet_gate_reason"] == "high_stakes_requires_analyst"
    packet = telemetry["quantitative_packet"]
    assert packet["high_stakes_quant_detected"] is True
    assert packet["high_stakes_quant_domain"] == "medical"
    assert packet["direct_use_eligible"] is False
    assert packet["requires_analyst"] is True


def test_quantitative_packet_high_stakes_difference_aliases_still_require_analyst() -> None:
    telemetry = _run_economist_payload(
        query="Does treatment A lower A1C more than treatment B?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {
                    "name": "treatment_a_a1c",
                    "value": "7.1",
                    "unit": "%",
                    "source_id": "1",
                },
                {
                    "name": "treatment_b_a1c",
                    "value": "8.0",
                    "unit": "%",
                    "source_id": "2",
                },
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "minuend": "treatment_a_a1c",
                        "subtrahend": "treatment_b_a1c",
                    },
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[
            {"source_id": 1, "text": "Treatment A mean A1C was 7.1%."},
            {"source_id": 2, "text": "Treatment B mean A1C was 8.0%."},
        ],
    )

    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["quantitative_packet_valid"] is True
    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert telemetry["quantitative_packet_requires_analyst"] is True
    assert telemetry["quantitative_packet_gate_reason"] == "high_stakes_requires_analyst"


def test_quantitative_packet_semaglutide_metformin_a1c_query_is_high_stakes() -> None:
    telemetry = _run_economist_payload(
        query="Does semaglutide lower A1C more than metformin in adults with type 2 diabetes?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {
                    "name": "semaglutide_a1c_change",
                    "value": "-1.4",
                    "unit": "percentage points",
                    "source_id": "1",
                },
                {
                    "name": "metformin_a1c_change",
                    "value": "-1.0",
                    "unit": "percentage points",
                    "source_id": "2",
                },
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "a": "semaglutide_a1c_change",
                        "b": "metformin_a1c_change",
                    },
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[
            {"source_id": 1, "text": "Adults in one treatment arm had A1C change of -1.4 percentage points."},
            {"source_id": 2, "text": "Adults in the comparator arm had A1C change of -1.0 percentage points."},
        ],
    )

    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["high_stakes_quant_domain"] == "medical"
    assert "clinical_metric_patient_context_signal" in telemetry["high_stakes_quant_reasons"]
    assert telemetry["high_stakes_quant_requires_analyst"] is True
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is False
    assert telemetry["high_stakes_quant_gate_reason"] == "medical_quantitative_requires_analyst"
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert telemetry["quantitative_packet_requires_analyst"] is True
    assert telemetry["quantitative_packet_gate_reason"] == "high_stakes_requires_analyst"


def test_quantitative_packet_missing_target_metric_evidence_records_error() -> None:
    telemetry = _run_economist_payload(
        query="What was the launch price?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {
                    "name": "release_date",
                    "value": "2025-09-01",
                    "unit": "date",
                    "source_id": "1",
                }
            ],
            "assumptions": [],
            "calculations_requested": [],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[
            {"source_id": 1, "text": "The product launched on September 1, 2025."}
        ],
    )

    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is False
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert "target_metric_evidence_missing" in telemetry[
        "quantitative_packet_validation_errors"
    ]
    assert telemetry["quantitative_packet_gate_reason"] == "packet_validation_failed"


def test_quantitative_packet_invalid_source_binding_records_error() -> None:
    telemetry = _run_economist_payload(
        query="What was revenue growth?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "unit": "USD", "source_id": "1"},
                {
                    "name": "new_revenue",
                    "value": "150",
                    "unit": "USD",
                    "source_id": "unknown",
                },
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
    )

    assert telemetry["source_binding_valid"] is False
    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is False
    assert "source_binding_invalid" in telemetry["quantitative_packet_validation_errors"]
    assert telemetry["quantitative_packet_direct_use_eligible"] is False


def test_quantitative_packet_calculation_error_records_error() -> None:
    telemetry = _run_economist_payload(
        query="What was revenue growth?",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [
                {"name": "old_revenue", "value": "0", "unit": "USD", "source_id": "1"},
                {"name": "new_revenue", "value": "150", "unit": "USD", "source_id": "2"},
            ],
            "assumptions": [],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
            "confidence": "medium",
            "unsupported_values": [],
        },
    )

    assert telemetry["calculation_error_count"] == 1
    assert telemetry["quantitative_packet_present"] is True
    assert telemetry["quantitative_packet_valid"] is False
    assert "calculation_errors_present" in telemetry[
        "quantitative_packet_validation_errors"
    ]
    assert telemetry["quantitative_packet_direct_use_eligible"] is False


def test_quantitative_packet_non_quantitative_query_not_present() -> None:
    telemetry = _run_economist_payload(
        query="Summarize the product positioning.",
        payload={
            "schema_version": "economist_v1",
            "variables": [],
            "source_bound_values": [],
            "assumptions": [],
            "calculations_requested": [],
            "confidence": "medium",
            "unsupported_values": [],
        },
        all_passages=[{"source_id": 1, "text": "The product is positioned for teams."}],
    )

    assert telemetry["quantitative_packet_present"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert telemetry["quantitative_packet_direct_use_eligible"] is False
    assert telemetry["quantitative_packet_requires_analyst"] is True
    assert telemetry["quantitative_packet_gate_reason"] == "not_quantitative"
    assert telemetry["quantitative_packet"] is None


def test_economist_target_metric_missing_price_records_shadow_block() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [
                    {
                        "name": "release_date",
                        "value": "2025-09-01",
                        "unit": "date",
                        "source_id": "1",
                    },
                    {
                        "name": "width",
                        "value": "10",
                        "unit": "cm",
                        "source_id": "2",
                    },
                ],
                "assumptions": [],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": ["launch price"],
            }
        )

    result = run_economist_step(
        core_topic="What was the product launch price?",
        all_passages=[
            {"source_id": 1, "text": "The product launched on September 1, 2025."},
            {"source_id": 2, "text": "The product is 10 cm wide."},
        ],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["target_metric_detected"] is True
    assert telemetry["target_metric_evidence_found"] is False
    assert "price_cost_rate" in telemetry["target_metric_missing"]
    assert telemetry["target_metric_shadow_would_block"] is True


def test_economist_target_metric_price_supports_unit_cost_bound_value() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Which option has the lower cost?",
        source_bound_values=[
            {
                "name": "unit_cost",
                "value": "12",
                "unit": "per unit",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "price_cost_rate" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_bound_value_refs"] == ["unit_cost"]
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_price_supports_hourly_rate_currency_unit() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Which provider has the lower hourly rate?",
        source_bound_values=[
            {
                "name": "hourly_rate",
                "value": "12",
                "unit": "USD/hour",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "price_cost_rate" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_price_does_not_support_approval_rate() -> None:
    telemetry = _valid_target_metric_shadow(
        query="What was the launch price?",
        source_bound_values=[
            {
                "name": "approval_rate",
                "value": "92%",
                "unit": "%",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "price_cost_rate" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["target_metric_shadow_would_block"] is True
    assert "approval_rate" not in telemetry["target_metric_bound_value_refs"]


def test_economist_target_metric_price_does_not_support_conversion_rate() -> None:
    telemetry = _valid_target_metric_shadow(
        query="What was the launch price?",
        source_bound_values=[
            {
                "name": "conversion_rate",
                "value": "4.2%",
                "unit": "%",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "price_cost_rate" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["target_metric_shadow_would_block"] is True
    assert "conversion_rate" not in telemetry["target_metric_bound_value_refs"]


def test_economist_target_metric_qualitative_rate_request_not_shadow_blocked() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Can you rate the narrative?",
        source_bound_values=[],
    )

    assert telemetry["target_metric_detected"] is False
    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["target_metric_gate_reason"] != "missing_target_metric_evidence"


def test_economist_target_metric_compare_positioning_not_shadow_blocked() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Compare the product positioning between A and B.",
        source_bound_values=[],
    )

    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["target_metric_gate_reason"] != "missing_target_metric_evidence"


def test_economist_target_metric_positioning_timeline_phrase_not_shadow_blocked() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Tell me more about the product positioning over the timeline.",
        source_bound_values=[],
    )

    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["target_metric_gate_reason"] != "missing_target_metric_evidence"


def test_economist_target_metric_performance_supports_duration_comparison() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Which system is faster based on response time?",
        source_bound_values=[
            {
                "name": "response_time_a",
                "value": "120",
                "unit": "ms",
                "source_id": "1",
            },
            {
                "name": "response_time_b",
                "value": "90",
                "unit": "ms",
                "source_id": "2",
            },
        ],
        calculation_results=[
            {
                "name": "difference",
                "result": 30,
                "input_refs": {"a": "response_time_a", "b": "response_time_b"},
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "performance_speed_throughput" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_calculation_refs"] == ["difference"]
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_performance_supports_latency_ratio() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Which system is faster by latency?",
        source_bound_values=[
            {
                "name": "latency_a",
                "value": "1.2",
                "unit": "seconds",
                "source_id": "1",
            },
            {
                "name": "latency_b",
                "value": "0.8",
                "unit": "seconds",
                "source_id": "2",
            },
        ],
        calculation_results=[
            {
                "name": "ratio",
                "result": 1.5,
                "input_refs": {"numerator": "latency_a", "denominator": "latency_b"},
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "performance_speed_throughput" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert "ratio" in telemetry["target_metric_calculation_refs"]
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_performance_rejects_unrelated_numeric_evidence() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Which system is faster?",
        source_bound_values=[
            {
                "name": "review_count",
                "value": "1200",
                "unit": "count",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "performance_speed_throughput" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["target_metric_shadow_would_block"] is True


def test_economist_target_metric_conversion_rate_supports_ratio_not_price() -> None:
    telemetry = _valid_target_metric_shadow(
        query="What was the conversion rate?",
        source_bound_values=[
            {
                "name": "conversion_rate",
                "value": "4.2%",
                "unit": "%",
                "source_id": "1",
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "ratio_margin_share" in telemetry["target_metric_names"]
    assert "price_cost_rate" not in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_growth_supports_percent_change() -> None:
    telemetry = _valid_target_metric_shadow(
        query="What was revenue growth?",
        source_bound_values=[
            {
                "name": "old_revenue",
                "value": "100",
                "unit": "USD",
                "source_id": "1",
            },
            {
                "name": "new_revenue",
                "value": "150",
                "unit": "USD",
                "source_id": "2",
            },
        ],
        calculation_results=[
            {
                "name": "percent_change",
                "result": 0.5,
                "input_refs": {"old": "old_revenue", "new": "new_revenue"},
            }
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "growth_change" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert "percent_change" in telemetry["target_metric_calculation_refs"]
    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_revenue_move_remains_deferred() -> None:
    # "Move" remains intentionally deferred pending more telemetry.
    telemetry = _valid_target_metric_shadow(
        query="How much did revenue move?",
        source_bound_values=[
            {
                "name": "old_revenue",
                "value": "100",
                "unit": "USD",
                "source_id": "1",
            },
            {
                "name": "new_revenue",
                "value": "150",
                "unit": "USD",
                "source_id": "2",
            },
        ],
        calculation_results=[
            {
                "name": "percent_change",
                "result": 0.5,
                "input_refs": {"old": "old_revenue", "new": "new_revenue"},
            }
        ],
    )

    assert telemetry["target_metric_shadow_would_block"] is False


def test_economist_target_metric_price_rejects_unrelated_numeric_anchors() -> None:
    telemetry = _valid_target_metric_shadow(
        query="What was the price?",
        source_bound_values=[
            {
                "name": "review_count",
                "value": "500",
                "unit": "count",
                "source_id": "1",
            },
            {
                "name": "rating",
                "value": "4.8",
                "unit": "stars",
                "source_id": "2",
            },
        ],
    )

    assert telemetry["target_metric_detected"] is True
    assert "price_cost_rate" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["target_metric_shadow_would_block"] is True
    assert telemetry["target_metric_bound_value_refs"] == []


def test_economist_target_metric_non_quantitative_query_not_detected() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [],
                "assumptions": [],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    result = run_economist_step(
        core_topic="Summarize the product positioning qualitatively.",
        all_passages=[{"source_id": 1, "text": "The product is positioned for teams."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["target_metric_detected"] is False
    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["target_metric_gate_reason"] == "not_quantitative_target"


def test_high_stakes_medical_quantitative_comparison_records_shadow_guardrail() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [
                    {
                        "name": "treatment_a_a1c",
                        "value": "7.2",
                        "unit": "%",
                        "source_id": "1",
                    },
                    {
                        "name": "treatment_b_a1c",
                        "value": "8.1",
                        "unit": "%",
                        "source_id": "2",
                    },
                ],
                "assumptions": [],
                "calculations_requested": [
                    {
                        "name": "difference",
                        "args": {"a": "treatment_a_a1c", "b": "treatment_b_a1c"},
                    }
                ],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    result = run_economist_step(
        core_topic="Does treatment A lower A1C more than treatment B?",
        all_passages=[
            {"source_id": 1, "text": "Treatment A reported A1C of 7.2%."},
            {"source_id": 2, "text": "Treatment B reported A1C of 8.1%."},
        ],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["high_stakes_quant_domain"] == "medical"
    assert telemetry["high_stakes_quant_requires_analyst"] is True
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is False
    assert telemetry["high_stakes_quant_shadow_mode"] is True
    assert telemetry["high_stakes_quant_gate_reason"] == "medical_quantitative_requires_analyst"


def test_high_stakes_medical_safety_risk_comparison_records_shadow_guardrail() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Which therapy has lower adverse event risk?",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["high_stakes_quant_domain"] == "medical"
    assert telemetry["high_stakes_quant_requires_analyst"] is True
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is False


def test_high_stakes_patient_metric_blood_pressure_comparison_records_shadow_guardrail() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Which medication lowers systolic blood pressure more in patients with a diagnosis?",
        payload={
            "source_bound_values": [
                {
                    "name": "systolic_blood_pressure_change",
                    "value": "-8",
                    "unit": "mmHg",
                    "source_id": "1",
                }
            ],
            "calculations_requested": [],
        },
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["high_stakes_quant_domain"] == "medical"
    assert telemetry["high_stakes_quant_requires_analyst"] is True
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is False
    assert telemetry["high_stakes_quant_gate_reason"] == "medical_quantitative_requires_analyst"


def test_high_stakes_no_payload_query_shadow_cases() -> None:
    cases = [
        (
            "Does semaglutide lower A1C more than metformin in adults with type 2 diabetes?",
            True, "medical", True, False,
            ("clinical_metric_patient_context_signal", "explicit_quantitative_metric_signal"),
            "medical_quantitative_requires_analyst",
        ),
        (
            "For patients with chronic symptoms, which treatment has higher remission response rate?",
            True, "medical", True, False, (), None,
        ),
        ("Compare Apple vs Microsoft gross margin.", False, None, None, True, (), None),
        ("Compare GitHub Copilot vs Cursor pricing for small teams.", False, None, None, True, (), None),
        ("Summarize Nvidia's data center strategy.", False, None, None, True, (), None),
        ("Summarize clinical trial design considerations for adults.", False, None, False, None, (), None),
    ]

    for (
        query,
        detected,
        domain,
        requires_analyst,
        future_allowed,
        reasons,
        gate_reason,
    ) in cases:
        telemetry = validate_high_stakes_quantitative_query_shadow(query=query)

        assert telemetry["high_stakes_quant_detected"] is detected
        if domain is not None:
            assert telemetry["high_stakes_quant_domain"] == domain
        if requires_analyst is not None:
            assert telemetry["high_stakes_quant_requires_analyst"] is requires_analyst
        if future_allowed is not None:
            assert telemetry["high_stakes_quant_future_direct_use_allowed"] is future_allowed
        for reason in reasons:
            assert reason in telemetry["high_stakes_quant_reasons"]
        if gate_reason is not None:
            assert telemetry["high_stakes_quant_gate_reason"] == gate_reason


def test_high_stakes_non_medical_quantitative_comparison_not_detected() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Which SaaS plan is cheaper?",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is False
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is True


def test_high_stakes_apple_microsoft_gross_margin_negative_control() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Compare Apple vs Microsoft gross margin.",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is False
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is True


def test_high_stakes_copilot_cursor_pricing_negative_control() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Compare GitHub Copilot vs Cursor pricing for small teams.",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is False
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is True


def test_high_stakes_nvidia_strategy_negative_control() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Summarize Nvidia's data center strategy.",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": False},
    )

    assert telemetry["high_stakes_quant_detected"] is False
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is True


def test_high_stakes_medical_adjacent_qualitative_query_not_detected() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Summarize the clinical trial design.",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": False},
    )

    assert telemetry["high_stakes_quant_detected"] is False
    assert telemetry["high_stakes_quant_requires_analyst"] is False


def test_high_stakes_consumer_wellness_product_query_not_detected() -> None:
    telemetry = validate_high_stakes_quantitative_shadow(
        query="Which running shoe is more comfortable?",
        payload={"source_bound_values": [], "calculations_requested": []},
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={"calculation_results": [], "calculation_results_count": 0},
        target_metric_telemetry={"target_metric_detected": True},
    )

    assert telemetry["high_stakes_quant_detected"] is False


def test_high_stakes_defaults_present_on_malformed_non_medical_response() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return "A narrative response with figures, but no parseable schema."

    result = run_economist_step(
        core_topic="Which SaaS plan is cheaper?",
        all_passages=[{"source_id": 1, "text": "Plan A costs 10 USD."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    for key, value in economist_high_stakes_quant_telemetry_defaults().items():
        assert telemetry[key] == value


def test_high_stakes_detects_clear_medical_query_even_with_parse_error() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return "A narrative response with figures, but no parseable schema."

    result = run_economist_step(
        core_topic="Does treatment A lower A1C more than treatment B?",
        all_passages=[{"source_id": 1, "text": "Treatment A reported A1C of 7.2%."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["economist_schema_valid"] is False
    assert telemetry["high_stakes_quant_detected"] is True
    assert telemetry["high_stakes_quant_domain"] == "medical"
    assert telemetry["high_stakes_quant_requires_analyst"] is True
    assert telemetry["high_stakes_quant_future_direct_use_allowed"] is False


def test_economist_target_metric_broad_more_time_phrase_not_numeric_missing() -> None:
    telemetry: dict[str, Any] = {}

    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "schema_version": "economist_v1",
                "variables": [],
                "source_bound_values": [],
                "assumptions": [],
                "calculations_requested": [],
                "confidence": "medium",
                "unsupported_values": [],
            }
        )

    result = run_economist_step(
        core_topic="Tell me more about the product positioning over time",
        all_passages=[{"source_id": 1, "text": "The product positioning changed as teams adopted it."}],
        current_date="2026-05-07",
        ask_model=ask_model,
        clean_json_response=lambda s: s,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
    )

    assert result is None
    assert telemetry["target_metric_detected"] is False
    assert telemetry["target_metric_shadow_would_block"] is False
    assert telemetry["target_metric_gate_reason"] != "missing_target_metric_evidence"


def test_economist_target_metric_comparative_terms_detect_generic_buckets() -> None:
    cheaper = detect_target_metric_buckets("A vs B, which is cheaper?")
    faster = detect_target_metric_buckets("A versus B, which is faster?")

    assert "comparative_terms" in cheaper
    assert "price_cost_rate" in cheaper
    assert "comparative_terms" in faster
    assert "performance_speed_throughput" in faster


def test_economist_target_metric_explicit_financial_line_items_detected() -> None:
    revenue = detect_target_metric_buckets(
        "Compare Costco vs Walmart on fiscal 2024 revenue."
    )
    net_income = detect_target_metric_buckets(
        "Compare Microsoft vs Alphabet on net income for fiscal 2024."
    )
    telemetry = _valid_target_metric_shadow(
        query="Compare Costco vs Walmart on fiscal 2024 revenue.",
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
    )

    assert "financial_line_item" in revenue
    assert "financial_line_item" in net_income
    assert "financial_line_item" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_bound_value_refs"] == [
        "costco_fy2024_revenue",
        "walmart_fy2024_revenue",
    ]


def test_economist_target_metric_financial_line_item_matches_metric_field() -> None:
    telemetry = _valid_target_metric_shadow(
        query="Compare Costco vs Walmart on fiscal 2024 revenue.",
        source_bound_values=[
            {
                "entity": "Costco",
                "name": "costco_fy2024_value",
                "metric": "revenue",
                "value": "254.45",
                "unit": "USD billions",
                "source_id": "1",
                "period": "fiscal 2024",
            },
            {
                "entity": "Walmart",
                "name": "walmart_fy2024_value",
                "metric": "revenue",
                "value": "648.13",
                "unit": "USD billions",
                "source_id": "2",
                "period": "fiscal 2024",
            },
        ],
    )

    assert "financial_line_item" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_bound_value_refs"] == [
        "costco_fy2024_value",
        "walmart_fy2024_value",
    ]


def test_quantitative_packet_requested_fiscal_revenue_binds_both_subjects() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=[
            {
                "entity": "Costco",
                "name": "costco_fy2024_net_sales",
                "metric": "net sales",
                "value": "$254.45 billion",
                "unit": "USD",
                "source_id": "1",
                "period": "fiscal 2024",
            },
            {
                "entity": "Walmart",
                "name": "walmart_fy2024_total_revenues",
                "metric": "total revenues",
                "value": "$648.13 billion",
                "unit": "USD",
                "source_id": "2",
                "period": "fiscal 2024",
            },
        ]
    )

    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_bound_value_refs"] == [
        "costco_fy2024_net_sales",
        "walmart_fy2024_total_revenues",
    ]
    assert telemetry["quantitative_packet_valid"] is True
    packet = telemetry["quantitative_packet"]
    assert packet["target_metric_bound_value_refs"] == [
        "costco_fy2024_net_sales",
        "walmart_fy2024_total_revenues",
    ]


def test_quantitative_packet_derived_gap_unsupported_keeps_revenue_evidence() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
        unsupported_values=["revenue gap"],
    )

    assert telemetry["unsupported_values_count"] == 1
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["target_metric_bound_value_refs"] == [
        "costco_fy2024_revenue",
        "walmart_fy2024_revenue",
    ]


def test_quantitative_packet_successful_comparison_calcs_cover_derived_unsupported_values() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
        calculations_requested=[
            {
                "name": "difference",
                "args": {
                    "minuend": "walmart_fy2024_revenue",
                    "subtrahend": "costco_fy2024_revenue",
                },
            },
            {
                "name": "ratio",
                "args": {
                    "numerator": "walmart_fy2024_revenue",
                    "denominator": "costco_fy2024_revenue",
                },
            },
        ],
        unsupported_values=["revenue gap", "revenue ratio"],
    )

    assert telemetry["calculation_requests_count"] == 2
    assert telemetry["calculation_success_count"] == 2
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["target_metric_evidence_found"] is True
    assert telemetry["quantitative_packet_valid"] is True
    assert telemetry["quantitative_packet_validation_errors"] == []


def test_quantitative_packet_unsupported_requested_revenue_still_blocks() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
        unsupported_values=["Costco fiscal 2024 revenue"],
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "target_metric_evidence_missing" in telemetry[
        "quantitative_packet_validation_errors"
    ]


def test_quantitative_packet_one_requested_annual_subject_missing_remains_invalid() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=_costco_walmart_fy2024_revenue_values()[:1],
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "target_metric_evidence_missing" in telemetry[
        "quantitative_packet_validation_errors"
    ]


def test_quantitative_packet_quarterly_value_does_not_satisfy_full_year_request() -> None:
    values = [
        _costco_walmart_fy2024_revenue_values()[0],
        {
            "entity": "Walmart",
            "name": "walmart_q4_2024_revenue",
            "metric": "revenue",
            "value": "173.39",
            "unit": "USD billions",
            "source_id": "2",
            "period": "Q4 2024",
        },
    ]

    telemetry = _run_costco_walmart_revenue_packet(source_bound_values=values)

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False


def test_quantitative_packet_wrong_annual_year_remains_invalid() -> None:
    values = [
        _costco_walmart_fy2024_revenue_values()[0],
        {
            "entity": "Walmart",
            "name": "walmart_fy2023_revenue",
            "metric": "revenue",
            "value": "611.29",
            "unit": "USD billions",
            "source_id": "2",
            "period": "fiscal 2023",
        },
    ]

    telemetry = _run_costco_walmart_revenue_packet(source_bound_values=values)

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False


def test_quantitative_packet_revenue_growth_does_not_satisfy_annual_revenue_request() -> None:
    values = [
        _costco_walmart_fy2024_revenue_values()[0],
        {
            "entity": "Walmart",
            "name": "walmart_fy2024_revenue_growth",
            "metric": "revenue growth",
            "value": "6",
            "unit": "percent",
            "source_id": "2",
            "period": "fiscal 2024",
        },
    ]

    telemetry = _run_costco_walmart_revenue_packet(source_bound_values=values)

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "walmart_fy2024_revenue_growth" not in telemetry[
        "target_metric_bound_value_refs"
    ]


def test_quantitative_packet_broad_comparison_without_explicit_metric_invalid() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        query="Compare Costco vs Walmart.",
        source_bound_values=_costco_walmart_fy2024_revenue_values(),
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False


def test_quantitative_packet_model_derived_values_do_not_count_as_source_bound() -> None:
    telemetry = _run_costco_walmart_revenue_packet(
        source_bound_values=[
            {
                "entity": "Costco",
                "name": "costco_fy2024_revenue_estimate",
                "metric": "revenue",
                "value": "254.45",
                "unit": "USD billions",
                "source_id": "1",
                "period": "fiscal 2024",
                "provenance": "model-derived",
            },
            _costco_walmart_fy2024_revenue_values()[1],
        ],
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "costco_fy2024_revenue_estimate" not in telemetry[
        "target_metric_bound_value_refs"
    ]


def test_economist_target_metric_rate_and_timeline_terms_are_contextual() -> None:
    conversion_rate = detect_target_metric_buckets("What was the conversion rate?")
    hourly_rate = detect_target_metric_buckets("Which provider has the lower hourly rate?")
    launch_timeline = detect_target_metric_buckets("What was the launch timeline?")
    qualitative_timeline = detect_target_metric_buckets(
        "Tell me more about the product positioning over the timeline."
    )

    assert "ratio_margin_share" in conversion_rate
    assert "price_cost_rate" not in conversion_rate
    assert "price_cost_rate" in hourly_rate
    assert "date_duration_timeline" in launch_timeline
    assert "date_duration_timeline" not in qualitative_timeline


def test_economist_target_metric_proxy_efficiency_is_conservative() -> None:
    # Phase 4A is intentionally conservative on proxy metrics;
    # Phase 7 Analyst review is where proxy acceptance is evaluated.
    telemetry = validate_target_metric_shadow(
        query="Which operation has better operating efficiency?",
        payload={
            "source_bound_values": [
                {"name": "cost_per_unit", "value": "10", "unit": "USD/unit", "source_id": "1"}
            ],
            "unsupported_values": [],
        },
        schema_telemetry={"economist_schema_valid": True},
        source_binding_telemetry={"source_binding_valid": True},
        calculation_telemetry={
            "calculation_results": [
                {
                    "name": "ratio",
                    "result": 0.5,
                    "input_refs": {"numerator": "total_cost", "denominator": "units"},
                }
            ]
        },
    )

    assert telemetry["target_metric_detected"] is True
    assert "performance_speed_throughput" in telemetry["target_metric_names"]
    assert telemetry["target_metric_evidence_found"] is False
    assert "performance_speed_throughput" in telemetry["target_metric_missing"]


def test_economist_shadow_calculation_unsupported_name_records_error() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "source_id": "1"},
                {"name": "new_revenue", "value": "150", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "hallucinated_model",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["unsupported_calculation_names"] == ["hallucinated_model"]
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_results"] == []


def test_economist_shadow_calculation_empty_requests_not_binding_valid() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "source_id": "1"},
            ],
            "calculations_requested": [],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_requests_count"] == 0
    assert telemetry["calculation_input_binding_valid"] is False
    assert telemetry["calculation_results_count"] == 0


def test_economist_shadow_calculation_unresolved_ref_records_error() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "source_id": "1"},
            ],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "missing_revenue"},
                }
            ],
        },
        source_binding_valid=True,
    )

    assert "missing_revenue" in telemetry["calculation_unresolved_input_refs"]
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_results"] == []


def test_economist_shadow_calculation_difference_accepts_semantic_arg_aliases() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "minuend_value", "value": "150", "source_id": "1"},
                {"name": "subtrahend_value", "value": "100", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "minuend": "minuend_value",
                        "subtrahend": "subtrahend_value",
                    },
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["calculation_results_count"] == 1
    assert telemetry["calculation_input_binding_valid"] is True
    assert telemetry["calculation_results"] == [
        {
            "name": "difference",
            "result": 50.0,
            "input_refs": {
                "a": "minuend_value",
                "b": "subtrahend_value",
            },
        }
    ]


def test_economist_shadow_calculation_ratio_and_percent_change_args_still_work() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "source_id": "1"},
                {"name": "new_revenue", "value": "150", "source_id": "2"},
                {"name": "gross_profit", "value": "25", "source_id": "1"},
                {"name": "sales", "value": "100", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                },
                {
                    "name": "ratio",
                    "args": {"numerator": "gross_profit", "denominator": "sales"},
                },
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 2
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["calculation_input_binding_valid"] is True
    assert [result["name"] for result in telemetry["calculation_results"]] == [
        "percent_change",
        "ratio",
    ]
    assert telemetry["calculation_results"][0]["result"] == 0.5
    assert telemetry["calculation_results"][1]["result"] == 0.25


def test_economist_shadow_calculation_difference_alias_missing_ref_still_fails() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "minuend_value", "value": "150", "source_id": "1"},
            ],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "minuend": "minuend_value",
                        "subtrahend": "missing_subtrahend",
                    },
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 0
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_unresolved_input_refs"] == ["missing_subtrahend"]
    assert telemetry["calculation_results"] == []


def test_economist_shadow_calculation_difference_alias_nonnumeric_ref_still_fails() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "minuend_value", "value": "about a lot", "source_id": "1"},
                {"name": "subtrahend_value", "value": "100", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "difference",
                    "args": {
                        "minuend": "minuend_value",
                        "subtrahend": "subtrahend_value",
                    },
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 0
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_error_summaries"] == ["sanitize:ValueError"]
    assert telemetry["calculation_results"] == []


def test_economist_shadow_calculation_type_coercion_succeeds() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "$1,000.00", "source_id": "1"},
                {"name": "new_revenue", "value": "1500", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_results"][0]["result"] == 0.5


def test_economist_shadow_calculation_normalizes_nutrition_value_per_100g() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {
                    "name": "protein_per_serving",
                    "value": "1.88",
                    "unit": "g",
                    "source_id": "1",
                },
                {
                    "name": "serving_size_grams",
                    "value": "10",
                    "unit": "g",
                    "source_id": "1",
                },
            ],
            "calculations_requested": [
                {
                    "name": "normalize_per_100g",
                    "args": {
                        "value": "protein_per_serving",
                        "serving_grams": "serving_size_grams",
                    },
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 1
    assert telemetry["calculation_error_count"] == 0
    assert telemetry["calculation_results_count"] == 1
    result = telemetry["calculation_results"][0]
    assert result["name"] == "normalize_per_100g"
    assert result["result"] == pytest.approx(18.8)
    assert result["input_refs"] == {
        "value": "protein_per_serving",
        "serving_grams": "serving_size_grams",
    }
    assert result["result_basis"] == "per_100g"


def test_economist_shadow_calculation_missing_serving_grams_does_not_normalize() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {
                    "name": "protein_per_serving",
                    "value": "1.88",
                    "unit": "g",
                    "source_id": "1",
                }
            ],
            "calculations_requested": [
                {
                    "name": "normalize_per_100g",
                    "args": {
                        "value": "protein_per_serving",
                        "serving_grams": "missing_serving_grams",
                    },
                }
            ],
        },
        source_binding_valid=True,
    )

    assert telemetry["calculation_success_count"] == 0
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_unresolved_input_refs"] == ["missing_serving_grams"]
    assert telemetry["calculation_results"] == []


def test_economist_shadow_calculation_invalid_source_binding_does_not_execute() -> None:
    telemetry = execute_economist_calculations_shadow(
        {
            "source_bound_values": [
                {"name": "old_revenue", "value": "100", "source_id": "999"},
                {"name": "new_revenue", "value": "150", "source_id": "2"},
            ],
            "calculations_requested": [
                {
                    "name": "percent_change",
                    "args": {"old": "old_revenue", "new": "new_revenue"},
                }
            ],
        },
        source_binding_valid=False,
    )

    assert telemetry["calculation_success_count"] == 0
    assert telemetry["calculation_error_count"] == 1
    assert telemetry["calculation_results"] == []
