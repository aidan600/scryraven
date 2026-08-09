"""Focused offline proof for the ordinary required-Scout composition.

Mode: BUILD.
Test path/node id: tests/test_searchos_required_scout_ordinary_composition_01.py
Proof class: OFFLINE_COMPONENT_PROOF.
Validation bucket: phase_focus.
Surface guarded: provider-neutral Scout route admission, bounded dispatch, and
direction-only result sanitization.
High-custody or closed-this-phase surface: evidence/citation/source-obligation
authority, READ, retrieval, and Author remain closed.
Runtime/product path guarded: the ordinary Scout adapter's immediate
producer/consumer seam, using injected route/search callables.
Expected cost: local mocked tests, under one second.
Promotion posture: remain phase_focus.
Demotion/retirement condition: replace when an equivalent durable ordinary-path
sentinel supersedes these phase-specific cap and route cases.
Why not fast_pr: detailed provider-route and cap-accounting cases are not a
cheap broad sentinel.
No test in this module makes a network, provider, model, fetch, or read call.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from core.cap_enforcement import (
    ExternalCallFamily,
    RoutePricing,
    RunCapEnvelope,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
)
from core.ordinary_scout_disambiguation_adapter import (
    ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY,
    OrdinaryScoutDisambiguationAdapter,
)
from core.routing import (
    AcquisitionCapability,
    DiscoverQualifier,
    route_provider_capability,
)


def _scout_input(*, query_count: int = 1) -> dict[str, Any]:
    return {
        "query_budget": {
            "max_queries_per_component": query_count,
            "max_dimensions_per_component": 1,
            "authorized_query_count": query_count,
        },
        "candidate_queries": [
            {
                "query_id": f"scout-query:{index}",
                "safe_query_text": f"Example identity direction {index}",
                "query_kind": "disambiguation_probe",
                "priority": index,
                "related_dimension_ids": ["dimension:entity"],
            }
            for index in range(1, query_count + 1)
        ],
    }


def _bounded_cap_policy() -> RunCapPolicy:
    zero_usage = TokenUsage()
    envelope = RunCapEnvelope(
        profile_name="test-scout-composition",
        profile_digest="a" * 64,
        pricing_version="test-scout-pricing",
        deadline_seconds=30.0,
        max_total_attempts=3,
        max_attempts_by_family={family: 3 for family in ExternalCallFamily},
        max_tokens=zero_usage,
        max_tokens_by_family={
            family: zero_usage for family in ExternalCallFamily
        },
        max_per_attempt_usd=Decimal("0.10"),
        max_run_usd=Decimal("0.30"),
        max_retries=0,
        max_fallbacks=0,
    )
    return RunCapPolicy(
        envelope=envelope,
        route_pricing={
            (
                ExternalCallFamily.SEARCH,
                "serper",
                "search",
            ): RoutePricing(
                pricing_key="test.scout.search",
                flat_attempt_usd=Decimal("0.01"),
            )
        },
    )


def test_ordinary_scout_routes_bounded_live_direction_without_raw_authority() -> None:
    cap_policy = _bounded_cap_policy()
    route_calls: list[tuple[Any, dict[str, object]]] = []
    search_calls: list[dict[str, Any]] = []

    def route(request: Any, available: dict[str, object]) -> Any:
        route_calls.append((request, dict(available)))
        return route_provider_capability(request, available)

    def search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        return [
            {
                "title": "Official Example identity",
                "url": "https://official.example.invalid/identity",
                "snippet": "Bounded directional material only.",
                "domain": "official.example.invalid",
                "position": 1,
                "raw_provider_payload": {"secret": "must-not-retain"},  # pragma: allowlist secret
            }
        ]

    result = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": True},
        cap_policy=cap_policy,
        scout_search=search,
        route=route,
    ).produce(_scout_input())

    assert len(route_calls) == 1
    request, availability = route_calls[0]
    assert request.capability is AcquisitionCapability.DISCOVER
    assert request.qualifier is DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION
    assert availability == {"serper": True}

    assert len(search_calls) == 1
    call = search_calls[0]
    assert call["provider"] == "serper"
    assert call["max_results"] == ORDINARY_SCOUT_MAX_RESULTS_PER_QUERY
    assert call["cap_policy"] is cap_policy
    assert call["cost_phase"] == "scout_disambiguation"
    assert str(call["logical_call_id"]).startswith("scout_disambiguation:")

    assert result["scout_execution_posture"] == "executed"
    assert result["route_available"] is True
    assert result["scout_queries"][0]["execution_status"] == "executed"
    assert result["scout_queries"][0]["not_live"] is False
    assert result["scout_queries"][0]["provider_payload_retained"] is False
    assert result["organic_results"][0]["title"] == "Official Example identity"
    assert "raw_provider_payload" not in result["organic_results"][0]
    assert "evidence" not in result


def test_ordinary_scout_truncates_over_returned_provider_results() -> None:
    def search(**_: Any) -> list[dict[str, Any]]:
        return [
            {"title": "first", "url": "https://example.invalid/first"},
            {"title": "second", "url": "https://example.invalid/second"},
        ]

    result = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": True},
        scout_search=search,
        max_results_per_query=1,
    ).produce(_scout_input())

    assert [item["title"] for item in result["organic_results"]] == ["first"]

def test_ordinary_scout_route_unavailable_blocks_without_dispatch() -> None:
    search_calls: list[dict[str, Any]] = []

    def search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        raise AssertionError("blocked Scout route must not dispatch")

    result = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": False},
        scout_search=search,
    ).produce(_scout_input(query_count=2))

    assert search_calls == []
    assert result["scout_execution_posture"] == "blocked"
    assert result["route_available"] is False
    assert all(
        query["execution_status"] == "blocked"
        and query["not_live"] is True
        for query in result["scout_queries"]
    )


def test_ordinary_scout_propagates_cap_terminal_without_retry() -> None:
    cap_policy = _bounded_cap_policy()
    search_calls: list[dict[str, Any]] = []

    def exhausted_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        raise RunCapExceeded(
            "search_attempt_cap",
            family=ExternalCallFamily.SEARCH,
        )

    adapter = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": True},
        cap_policy=cap_policy,
        scout_search=exhausted_search,
    )

    with pytest.raises(RunCapExceeded, match="bounded_run_cap_reached"):
        adapter.produce(_scout_input())

    assert len(search_calls) == 1
    assert search_calls[0]["cap_policy"] is cap_policy
    assert str(search_calls[0]["logical_call_id"]).startswith(
        "scout_disambiguation:"
    )
