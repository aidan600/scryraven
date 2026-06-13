from __future__ import annotations

from typing import Any

import pytest

import core.pipeline as pipeline
from core.routing import select_providers
from core.run_controller import RunController
from core.source_class_recovery import build_source_class_recovery_recommendation
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_OFFICIAL_CURRENT = "official_current_rules"
_LEGAL_TEXT = "legal_or_regulatory_text"
_USCIS_QUERY = (
    "What official source currently states the current USCIS filing fee for "
    "Form N-400? Answer from official/current sources and cite the official source."
)
_SSA_QUERY = (
    "What official source currently states the Social Security taxable maximum "
    "wage base for 2026? Answer from official/current sources and cite the "
    "official source."
)
_DENMARK_QUERY = (
    "What official legal or regulatory source currently lists which "
    "preservatives or additives are permitted in infant formula sold in Denmark?"
)
_SINGAPORE_QUERY = (
    "What current official source lists workplace safety requirements for "
    "employers in Singapore?"
)
_KNOWN_US_AUTHORITY_DOMAINS = {
    "consumerfinance.gov",
    "dol.gov",
    "fda.gov",
    "ftc.gov",
    "irs.gov",
    "osha.gov",
    "sec.gov",
    "transportation.gov",
    "uscis.gov",
}


def _evidence_signals() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 2},
        "source_domain_counts": {"secondary.example": 2},
        "top_source_domains": [{"domain": "secondary.example", "count": 2}],
        "unique_source_domain_count": 1,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _recommendation(
    query: str,
    *,
    source_class: str = _OFFICIAL_CURRENT,
    core_topic: str | None = None,
    primary_entity: str | None = None,
) -> dict[str, Any]:
    del source_class
    return build_source_class_recovery_recommendation(
        query=query,
        current_date="2026-06-13",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic=core_topic or query,
        primary_entity=primary_entity or core_topic or query,
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"secondary.example": 2},
        top_source_domains=[{"domain": "secondary.example", "count": 2}],
        official_evidence_found=False,
    )


def _record_lifecycle(
    recommendation: dict[str, Any],
) -> tuple[RunController, dict[str, Any], dict[str, Any]]:
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals=_evidence_signals(),
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
        official_canonical_source_class_slot_available=True,
    )
    action = controller.snapshot_ledger()["retrieval_actions"][0]
    return controller, lifecycle, action


def _execute_with_capture(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    include_domains: list[str] | None = None,
    search_providers: list[str] | None = None,
    exa_domain_filter: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        _results_per_query: int,
        captured_include_domains: list[str],
        captured_exclude_domains: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured.append(
            {
                "queries": list(queries),
                "search_depth": search_depth,
                "include_domains": list(captured_include_domains),
                "exclude_domains": list(captured_exclude_domains),
                "search_providers": list(kwargs["search_providers"]),
                "exa_domain_filter": (
                    list(kwargs["exa_domain_filter"])
                    if kwargs.get("exa_domain_filter") is not None
                    else None
                ),
                "provider_role": kwargs["provider_role"],
            }
        )
        return []

    retrieval_pass_records: list[dict[str, Any]] = []
    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
        intent="general",
        complexity="low",
        results_per_query=5,
        include_domains=list(include_domains or []),
        exclude_domains=[],
        query_embedding=[0.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=list(search_providers or ["tavily"]),
        exa_domain_filter=exa_domain_filter,
        entity_hint="official authority",
        provider_diagnostics=[],
        retrieval_pass_records=retrieval_pass_records,
    )
    assert result["attempted"] is True
    assert captured
    captured[0]["retrieval_pass_records"] = retrieval_pass_records
    return captured[0], retrieval_pass_records


@pytest.mark.parametrize(
    ("query", "core_topic", "primary_entity", "expected_domain", "forbidden_terms"),
    [
        (
            _USCIS_QUERY,
            "USCIS Form N-400 filing fee",
            "USCIS Form N-400",
            "uscis.gov",
            ("irs", "irs.gov"),
        ),
        (
            _SSA_QUERY,
            "Social Security taxable maximum wage base 2026",
            "Social Security taxable maximum wage base",
            "ssa.gov",
            ("irs.gov",),
        ),
    ],
)
def test_ag96a5_hard_corridor_domains_reach_lifecycle_and_executor_dispatch(
    query: str,
    core_topic: str,
    primary_entity: str,
    expected_domain: str,
    forbidden_terms: tuple[str, ...],
) -> None:
    recommendation = _recommendation(
        query,
        core_topic=core_topic,
        primary_entity=primary_entity,
    )
    decision = recommendation["source_class_recovery_authority_acquisition_decision"]

    assert decision["decision_type"] == "hard_corridor"
    assert decision["provider_domain_constraints_allowed"] is True
    assert expected_domain in recommendation["source_class_recovery_official_domains"]

    controller, lifecycle, action = _record_lifecycle(recommendation)
    metadata = action["metadata"]
    assert expected_domain in metadata["official_domain_constraints"]
    assert metadata["official_domain_constraint_source"] == (
        "official_source_recovery_lane"
    )

    call, pass_records = _execute_with_capture(
        controller,
        lifecycle,
        include_domains=["secondary.example"],
        search_providers=["tavily"],
        exa_domain_filter=["secondary.example"],
    )
    assert expected_domain in call["include_domains"]
    assert expected_domain in call["exa_domain_filter"]
    assert call["provider_role"] == "source_class_recovery"
    assert pass_records[0]["official_domain_constraints"] == (
        metadata["official_domain_constraints"]
    )
    combined_query_and_domains = " ".join(
        [
            *recommendation["source_class_recovery_queries"],
            *recommendation["source_class_recovery_official_domains"],
        ]
    ).casefold()
    for term in forbidden_terms:
        assert term not in combined_query_and_domains


def test_ag96a5_supported_provider_request_construction_consumes_constraints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def record_provider(provider: str):
        def fake_provider(
            query: str,
            *,
            include_domains: list[str] | None = None,
            exclude_domains: list[str] | None = None,
            **kwargs: Any,
        ) -> tuple[list[dict[str, Any]], list[str]]:
            calls.append(
                {
                    "provider": provider,
                    "query": query,
                    "include_domains": list(include_domains or []),
                    "exclude_domains": list(exclude_domains or []),
                    "kwargs": kwargs,
                }
            )
            return [], []

        return fake_provider

    monkeypatch.setenv("LINKUP_API_KEY", "offline-linkup-key")
    monkeypatch.setenv("EXA_API_KEY", "offline-exa-key")
    monkeypatch.setattr(pipeline, "search_web_results", record_provider("tavily"))
    monkeypatch.setattr(pipeline, "search_linkup_results", record_provider("linkup"))
    monkeypatch.setattr(pipeline, "search_exa_results", record_provider("exa"))

    pipeline.process_search_queries(
        ["USCIS Form N-400 filing fee official current fee schedule"],
        "general",
        "high",
        "basic",
        5,
        ["uscis.gov"],
        [],
        [0.0],
        set(),
        set(),
        "OpenAI",
        "text-embedding-3-small",
        "http://localhost",
        lambda *_args, **_kwargs: [],
        lambda *_args, **_kwargs: [],
        search_providers=["tavily", "linkup", "exa"],
        exa_domain_filter=["uscis.gov"],
        provider_diagnostics=[],
        provider_role="source_class_recovery",
    )

    assert {call["provider"] for call in calls} == {"tavily", "linkup", "exa"}
    assert all(call["include_domains"] == ["uscis.gov"] for call in calls)
    assert all(call["exclude_domains"] == [] for call in calls)


def test_ag96a5_dispatch_distinguishes_unsupported_provider_from_lost_constraints() -> None:
    recommendation = _recommendation(
        _USCIS_QUERY,
        core_topic="USCIS Form N-400 filing fee",
        primary_entity="USCIS Form N-400",
    )
    controller, lifecycle, action = _record_lifecycle(recommendation)

    call, pass_records = _execute_with_capture(
        controller,
        lifecycle,
        search_providers=["offline-unsupported"],
    )

    assert "uscis.gov" in action["metadata"]["official_domain_constraints"]
    assert call["search_providers"] == ["offline-unsupported"]
    assert "uscis.gov" in call["include_domains"]
    assert pass_records[0]["providers"] == ["offline-unsupported"]
    assert "uscis.gov" in pass_records[0]["official_domain_constraints"]


@pytest.mark.parametrize(
    ("query", "source_class", "core_topic", "primary_entity"),
    [
        (
            _DENMARK_QUERY,
            _LEGAL_TEXT,
            "infant formula additives permitted in Denmark",
            "infant formula sold in Denmark",
        ),
        (
            _SINGAPORE_QUERY,
            _LEGAL_TEXT,
            "workplace safety requirements for employers in Singapore",
            "Singapore workplace safety requirements",
        ),
    ],
)
def test_ag96a5_off_list_foreign_cases_do_not_receive_us_hard_domain_dispatch(
    query: str,
    source_class: str,
    core_topic: str,
    primary_entity: str,
) -> None:
    recommendation = _recommendation(
        query,
        source_class=source_class,
        core_topic=core_topic,
        primary_entity=primary_entity,
    )
    assert "source_class_recovery_official_domains" not in recommendation

    executable_discovery_recommendation = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_queries": [f"official current source {core_topic}"],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_reason": "ag96a5_off_list_discovery_fixture",
        "source_class_recovery_authority_acquisition_decision": {
            "decision_type": "discovery_corridor",
            "provider_domain_constraints_allowed": False,
        },
    }
    controller, lifecycle, action = _record_lifecycle(executable_discovery_recommendation)

    assert "official_domain_constraints" not in action["metadata"]

    call, pass_records = _execute_with_capture(
        controller,
        lifecycle,
        search_providers=["tavily"],
    )
    assert set(call["include_domains"]).isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)
    assert "official_domain_constraints" not in pass_records[0]


def test_ag96a5_legacy_domains_without_authority_decision_still_do_not_dispatch() -> None:
    recommendation = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [_OFFICIAL_CURRENT],
        "source_class_recovery_queries": [
            "USCIS Form N-400 filing fee official current fee schedule"
        ],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_reason": "legacy_domain_fixture",
        "source_class_recovery_official_domains": ["uscis.gov"],
    }
    controller, lifecycle, action = _record_lifecycle(recommendation)

    assert "official_domain_constraints" not in action["metadata"]

    call, pass_records = _execute_with_capture(
        controller,
        lifecycle,
        search_providers=["tavily"],
    )
    assert call["include_domains"] == []
    assert "official_domain_constraints" not in pass_records[0]


def test_ag96a5_fast_provider_policy_tavily_only_is_expected_without_exa_key() -> None:
    providers = select_providers(
        "official_current_status",
        "general",
        "low",
        {"tavily": True, "linkup": False, "exa": False},
        report_type="general_research",
        is_academic=False,
    )

    assert providers == ["tavily"]
