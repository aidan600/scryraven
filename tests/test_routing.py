"""Tests for core/routing.py (Phase A4)."""

from __future__ import annotations

from core.routing import QUERY_TYPE_ENUM, is_quantitative_query, merge_search_provider_overrides, select_providers


def _all_on() -> dict[str, bool]:
    return {"tavily": True, "linkup": True, "exa": True}


def _all_off() -> dict[str, bool]:
    return {"tavily": False, "linkup": False, "exa": False}


def test_query_type_enum_includes_router_and_spec_types() -> None:
    assert "comparison" in QUERY_TYPE_ENUM
    assert "quantitative_comparison" in QUERY_TYPE_ENUM
    assert "place" in QUERY_TYPE_ENUM


def test_is_quantitative_query_honors_query_types() -> None:
    assert is_quantitative_query("comparison", "general_research") is True
    assert is_quantitative_query("quantitative_comparison", "general_research") is True
    assert is_quantitative_query("product", "general_research") is False


def test_is_quantitative_query_honors_report_types() -> None:
    assert is_quantitative_query("product", "comparative_analysis") is True
    assert is_quantitative_query("other", "benchmark") is True
    assert is_quantitative_query(None, "quantitative_comparison") is True
    assert is_quantitative_query("concept", "cost_analysis") is True


def test_quantitative_comparison_overrides_academic_for_providers() -> None:
    prov = select_providers(
        "quantitative_comparison",
        "general",
        "high",
        _all_on(),
        report_type="quantitative_comparison",
        is_academic=True,
    )
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_news_intent_returns_tavily_linkup() -> None:
    prov = select_providers("product", "news", "high", _all_on(), report_type="general_research")
    assert prov == ["tavily", "linkup"]


def test_newsish_query_type_returns_tavily_linkup() -> None:
    prov = select_providers("current_events", "general", "high", _all_on())
    assert prov == ["tavily", "linkup"]


def test_academic_prefers_exa_when_available() -> None:
    assert select_providers("concept", "general", "high", _all_on(), is_academic=True) == ["exa"]


def test_academic_falls_back_tavily_when_no_exa() -> None:
    keys = {"tavily": True, "linkup": True, "exa": False}
    assert select_providers("concept", "general", "high", keys, is_academic=True) == ["tavily"]


def test_quant_query_type_drops_exa() -> None:
    prov = select_providers("quantitative_comparison", "general", "high", _all_on())
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_medium_quantitative_query_skips_linkup_by_default() -> None:
    prov = select_providers("quantitative_comparison", "general", "medium", _all_on())
    assert prov == ["tavily"]
    assert "linkup" not in prov


def test_comparison_query_type_drops_exa() -> None:
    prov = select_providers("comparison", "general", "medium", _all_on())
    assert prov == ["tavily"]
    assert "linkup" not in prov


def test_quantitative_report_type_drops_exa_even_if_query_type_other() -> None:
    prov = select_providers("product", "general", "high", _all_on(), report_type="quantitative_comparison")
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_comparative_analysis_report_type_drops_exa() -> None:
    prov = select_providers("product", "general", "high", _all_on(), report_type="comparative_analysis")
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_benchmark_report_type_drops_exa() -> None:
    prov = select_providers("product", "general", "high", _all_on(), report_type="benchmark")
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_cost_analysis_report_type_drops_exa() -> None:
    prov = select_providers("product", "general", "high", _all_on(), report_type="cost_analysis")
    assert prov == ["tavily", "linkup"]
    assert "exa" not in prov


def test_default_general_gets_exa_on_deep() -> None:
    prov = select_providers("product", "general", "high", _all_on(), report_type="general_research")
    assert prov == ["tavily", "linkup", "exa"]


def test_default_medium_general_skips_linkup() -> None:
    prov = select_providers("product", "general", "medium", _all_on(), report_type="general_research")
    assert prov == ["tavily", "exa"]
    assert "linkup" not in prov


def test_default_low_complexity_no_linkup() -> None:
    prov = select_providers("other", "general", "low", _all_on())
    assert prov == ["tavily", "exa"]


def test_low_news_complexity_no_linkup_by_default() -> None:
    prov = select_providers("news", "news", "low", _all_on())
    assert prov == ["tavily"]


def test_suppress_tavily_skips_tavily_in_default() -> None:
    prov = select_providers("product", "general", "high", _all_on(), suppress_tavily=True)
    assert prov == ["linkup", "exa"]
    assert "tavily" not in prov


def test_explicit_user_override_allows_medium_linkup() -> None:
    prov = select_providers("other", "general", "medium", _all_on(), override=["linkup"])
    assert prov == ["linkup"]


def test_internal_medium_override_does_not_force_linkup() -> None:
    prov = select_providers(
        "other",
        "general",
        "medium",
        _all_on(),
        override=["exa", "linkup"],
        override_is_user=False,
    )
    assert prov == ["exa"]


def test_override_filters_by_availability() -> None:
    prov = select_providers(
        "other",
        "general",
        "high",
        {"tavily": True, "linkup": False, "exa": True},
        override=["exa", "linkup"],
    )
    assert prov == ["exa"]


def test_no_keys_fallback_tavily() -> None:
    assert select_providers("other", "general", "high", _all_off()) == ["tavily"]


def test_merge_override_primary_first_then_scout() -> None:
    keys = {"tavily": True, "linkup": True, "exa": True}
    m = merge_search_provider_overrides(["exa"], ["tavily", "linkup"], keys)
    assert m == ["exa", "tavily", "linkup"]


def test_merge_override_keeps_primary_medium_linkup() -> None:
    keys = {"tavily": True, "linkup": True, "exa": True}
    m = merge_search_provider_overrides(["linkup"], ["exa"], keys, complexity="medium")
    assert m == ["linkup", "exa"]


def test_merge_override_filters_secondary_medium_linkup() -> None:
    keys = {"tavily": True, "linkup": True, "exa": True}
    m = merge_search_provider_overrides(None, ["exa", "linkup"], keys, complexity="medium")
    assert m == ["exa"]


def test_merge_override_dedupes() -> None:
    keys = {"tavily": True, "linkup": True, "exa": False}
    m = merge_search_provider_overrides(["tavily"], ["tavily", "linkup"], keys)
    assert m == ["tavily", "linkup"]


def test_merge_override_filters_unavailable() -> None:
    keys = {"tavily": True, "linkup": False, "exa": False}
    m = merge_search_provider_overrides(["linkup"], ["exa"], keys)
    assert m is None


def test_merge_override_none_when_both_empty() -> None:
    assert merge_search_provider_overrides(None, None, _all_on()) is None
