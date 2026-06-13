from __future__ import annotations

from typing import Any

from core.pipeline_orchestrator import choose_retrieval_search_depth
from core.routing import select_providers
from core.run_controller import RunController
from core.source_class_recovery import (
    build_official_source_recovery_domain_constraint_policy,
)
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_IRS_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it? Keep the answer concise."
)
_IRS_RECOVERY_QUERIES = [
    "IRS 2026 standard mileage rate business official notice revenue procedure",
    "IRS 2026 standard mileage rate revenue procedure official current source",
]
_SECONDARY_CORRIDOR = ["taxfoundation.org", "hrblock.com", "shrm.org"]


def _irs_recommendation() -> dict[str, Any]:
    domain_policy = build_official_source_recovery_domain_constraint_policy(
        missing_expected_source_classes=["official_current_rules"],
        query=_IRS_QUERY,
        core_topic="IRS 2026 standard mileage rate business",
        primary_entity="IRS",
        recovery_queries=_IRS_RECOVERY_QUERIES,
    )
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_reason": (
            "official_canonical_recovery_query_acquisition:"
            "official_current_rules"
        ),
        "source_class_recovery_queries": list(_IRS_RECOVERY_QUERIES),
        "source_class_recovery_query_count": len(_IRS_RECOVERY_QUERIES),
        "source_class_recovery_trigger_fields": [
            "official_canonical_recovery_query_acquisition"
        ],
        "source_class_recovery_authority_acquisition_decision": (
            domain_policy["authority_acquisition_decision"]
        ),
        "source_class_recovery_official_domains": domain_policy["official_domains"],
        "source_class_recovery_domain_constraint_source": (
            "official_source_recovery_lane"
        ),
    }


def _record_irs_lifecycle(controller: RunController) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=_irs_recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 3},
            "source_domain_counts": {
                "taxfoundation.org": 1,
                "hrblock.com": 1,
                "shrm.org": 1,
            },
            "official_evidence_found": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
    )


def test_ag72r_medium_general_provider_policy_excludes_linkup_without_escalation() -> None:
    providers = select_providers(
        "other",
        "general",
        "medium",
        {"tavily": True, "linkup": True, "exa": True, "brave": True},
        report_type="general_research",
        is_academic=False,
    )

    assert providers == ["tavily", "exa"]
    assert "linkup" not in providers
    assert choose_retrieval_search_depth("medium", "basic", iteration=1) == "basic"


def test_ag72r_recovery_reuses_existing_allocation_with_official_domain_overlay() -> None:
    providers = select_providers(
        "other",
        "general",
        "medium",
        {"tavily": True, "linkup": True, "exa": True, "brave": True},
        report_type="general_research",
        is_academic=False,
    )
    controller = RunController()
    lifecycle = _record_irs_lifecycle(controller)
    captured: dict[str, Any] = {}
    retrieval_pass_records: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        _results_per_query: int,
        include_domains: list[str],
        _exclude_domains: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured.update(
            {
                "queries": list(queries),
                "search_depth": search_depth,
                "include_domains": list(include_domains),
                "search_providers": list(kwargs["search_providers"]),
                "exa_domain_filter": list(kwargs["exa_domain_filter"]),
                "provider_role": kwargs["provider_role"],
            }
        )
        return []

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=6,
        include_domains=list(_SECONDARY_CORRIDOR),
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
        search_providers=providers,
        exa_domain_filter=list(_SECONDARY_CORRIDOR),
        entity_hint="IRS",
        provider_diagnostics=[],
        retrieval_pass_records=retrieval_pass_records,
    )

    assert result["attempted"] is True
    assert captured["queries"] == _IRS_RECOVERY_QUERIES
    assert captured["search_depth"] == "basic"
    assert captured["search_providers"] == ["tavily", "exa"]
    assert captured["provider_role"] == "source_class_recovery"
    assert "linkup" not in captured["search_providers"]
    assert set(_SECONDARY_CORRIDOR).issubset(captured["include_domains"])
    assert {"irs.gov", "federalregister.gov"}.issubset(
        captured["include_domains"]
    )
    assert {"irs.gov", "federalregister.gov"}.issubset(
        captured["exa_domain_filter"]
    )
    assert len(retrieval_pass_records) == 1
    pass_record = retrieval_pass_records[0]
    assert pass_record["stage"] == "source_class_recovery"
    assert pass_record["queries"] == _IRS_RECOVERY_QUERIES
    assert pass_record["providers"] == ["tavily", "exa"]
    assert pass_record["provider_role"] == "source_class_recovery"
    assert pass_record["search_depth"] == "basic"
    assert pass_record["results_per_query"] == 6
    assert set(_SECONDARY_CORRIDOR).issubset(pass_record["include_domains"])
    assert {"irs.gov", "federalregister.gov"}.issubset(
        pass_record["official_domain_constraints"]
    )
