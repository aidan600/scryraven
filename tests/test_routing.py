"""Focused tests for the sole provider-capability policy owner."""

from __future__ import annotations

import pytest

from core.routing import (
    QUERY_TYPE_ENUM,
    AcquisitionCapability,
    DiscoverQualifier,
    ProviderCapabilityRequest,
    RouteFidelity,
    is_quantitative_query,
    merge_search_provider_overrides,
    route_provider_capability,
    select_providers,
)


def _all_on() -> dict[str, bool]:
    return {
        "tavily": True,
        "linkup": True,
        "exa": True,
        "serper": True,
        "brave": True,
    }


def _all_off() -> dict[str, bool]:
    return {provider: False for provider in _all_on()}


def test_query_type_enum_includes_router_and_spec_types() -> None:
    assert "comparison" in QUERY_TYPE_ENUM
    assert "quantitative_comparison" in QUERY_TYPE_ENUM
    assert "place" in QUERY_TYPE_ENUM


def test_is_quantitative_query_honors_query_and_report_types() -> None:
    assert is_quantitative_query("comparison", "general_research") is True
    assert is_quantitative_query("quantitative_comparison", "general_research") is True
    assert is_quantitative_query("product", "comparative_analysis") is True
    assert is_quantitative_query("other", "benchmark") is True
    assert is_quantitative_query("product", "general_research") is False


@pytest.mark.parametrize(
    ("query_type", "intent", "complexity", "report_type"),
    [
        ("product", "news", "high", "general_research"),
        ("current_events", "general", "low", "general_research"),
        ("quantitative_comparison", "general", "high", "quantitative_comparison"),
        ("comparison", "general", "medium", "general_research"),
        ("product", "general", "low", "general_research"),
        ("product", "general", "medium", "benchmark"),
        ("product", "general", "high", "cost_analysis"),
    ],
)
def test_general_news_and_quantitative_requests_share_linkup_first_discovery(
    query_type: str,
    intent: str,
    complexity: str,
    report_type: str,
) -> None:
    assert select_providers(
        query_type,
        intent,
        complexity,
        _all_on(),
        report_type=report_type,
    ) == ["linkup"]


def test_academic_prefers_exa_and_uses_explicitly_degraded_fallbacks() -> None:
    assert select_providers("concept", "general", "high", _all_on(), is_academic=True) == ["exa"]

    linkup_fallback = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC,
        ),
        {"linkup": True, "tavily": True},
    )
    tavily_fallback = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC,
        ),
        {"tavily": True},
    )

    assert linkup_fallback.selected_provider == "linkup"
    assert linkup_fallback.fidelity is RouteFidelity.DEGRADED
    assert tavily_fallback.selected_provider == "tavily"
    assert tavily_fallback.fidelity is RouteFidelity.DEGRADED


def test_domain_constraints_select_same_linkup_first_policy() -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=DiscoverQualifier.DOMAIN_TARGETED,
            include_domains=("reddit.com",),
            exclude_domains=("blocked.example",),
        ),
        _all_on(),
    )

    assert decision.selected_provider == "linkup"
    assert decision.request.include_domains == ("reddit.com",)
    assert decision.request.exclude_domains == ("blocked.example",)
    assert decision.social_authority_granted is False


def test_suppress_tavily_never_manufactures_a_fallback() -> None:
    assert select_providers("product", "general", "high", _all_on(), suppress_tavily=True) == ["linkup"]
    assert (
        select_providers(
            "product",
            "general",
            "high",
            {"tavily": True},
            suppress_tavily=True,
        )
        == []
    )


def test_override_selects_first_available_compatible_preference() -> None:
    assert select_providers(
        "other",
        "general",
        "medium",
        {"tavily": True, "linkup": True},
        override=["tavily", "linkup"],
    ) == ["tavily"]
    assert select_providers(
        "other",
        "general",
        "medium",
        {"tavily": False, "linkup": True},
        override=["tavily", "linkup"],
    ) == ["linkup"]


def test_incompatible_or_unavailable_override_blocks_instead_of_falling_back() -> None:
    assert (
        select_providers(
            "other",
            "general",
            "high",
            {"serper": True, "linkup": True},
            override=["serper"],
        )
        == []
    )
    assert (
        select_providers(
            "other",
            "general",
            "high",
            {"linkup": False, "tavily": True},
            override=["linkup"],
        )
        == []
    )


def test_no_keys_returns_empty_provider_projection() -> None:
    assert select_providers("other", "general", "high", _all_off()) == []


def test_merge_override_preserves_order_and_unsatisfied_preferences() -> None:
    keys = {"tavily": True, "linkup": False, "exa": False}
    assert merge_search_provider_overrides(["linkup"], ["tavily", "linkup"], keys, complexity="medium") == [
        "linkup",
        "tavily",
    ]
    assert merge_search_provider_overrides(["unknown"], ["exa"], keys) == [
        "unknown",
        "exa",
    ]
    assert merge_search_provider_overrides(None, None, keys) is None


@pytest.mark.parametrize(
    ("qualifier", "provider"),
    [
        (DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION, "serper"),
        (DiscoverQualifier.INDEPENDENT_INDEX, "brave"),
    ],
)
def test_explicit_candidate_only_roles_do_not_enter_general_discovery(
    qualifier: DiscoverQualifier,
    provider: str,
) -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(
            capability=AcquisitionCapability.DISCOVER,
            qualifier=qualifier,
        ),
        {provider: True},
    )

    assert decision.selected_provider == provider
    assert decision.authority_posture == "candidate_only_no_evidence_authority"
    assert select_providers("other", "general", "high", {provider: True}) == []


@pytest.mark.parametrize(
    "capability",
    [
        AcquisitionCapability.FOCUSED_EXTRACT,
        AcquisitionCapability.MAP_SITE,
        AcquisitionCapability.CRAWL_SITE,
        AcquisitionCapability.PROVIDER_SYNTHESIS,
    ],
)
def test_noninstalled_or_disabled_capability_requests_are_typed_blocks(
    capability: AcquisitionCapability,
) -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(capability=capability),
        _all_on(),
    )

    assert decision.fidelity is RouteFidelity.BLOCKED
    assert decision.selected_provider is None
    assert decision.providers() == ()


def test_read_is_an_installed_ordinary_product_route() -> None:
    decision = route_provider_capability(
        ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
        _all_on(),
    )

    assert decision.fidelity is RouteFidelity.EXACT
    assert decision.selected_provider == "linkup"
    assert decision.operation == "fetch"
