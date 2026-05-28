from __future__ import annotations

from typing import Any

from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    build_official_source_recovery_domain_constraints,
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
_ORDINARY_SECONDARY_CORRIDOR = ["taxfoundation.org", "hrblock.com", "shrm.org"]


def _recommendation() -> dict[str, Any]:
    official_domains = build_official_source_recovery_domain_constraints(
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
        "source_class_recovery_official_domains": official_domains,
        "source_class_recovery_domain_constraint_source": (
            "official_source_recovery_lane"
        ),
    }


def _record_lifecycle(controller: RunController) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=_recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 3},
            "source_domain_counts": {
                "taxfoundation.org": 1,
                "hrblock.com": 1,
                "shrm.org": 1,
            },
            "top_source_domains": [
                {"domain": "taxfoundation.org", "count": 1},
                {"domain": "hrblock.com", "count": 1},
                {"domain": "shrm.org", "count": 1},
            ],
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


def _authority_trace() -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=tuple(_IRS_RECOVERY_QUERIES),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_result_count": 1,
            "recovered_accepted_url_count": 1,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": ["official_current_rules"],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=1,
        recovered_result_count=1,
        accepted_url_count=1,
    )
    return trace


def _official_irs_candidate() -> dict[str, Any]:
    return {
        "title": "IRS 2026 standard mileage rates notice",
        "url": "https://www.irs.gov/newsroom/irs-issues-standard-mileage-rates-for-2026",
        "text": (
            "Official IRS current guidance states the 2026 standard mileage "
            "rate for business use of a car."
        ),
        "source_tier": "official",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }


def _secondary_context() -> dict[str, Any]:
    return {
        "title": "Secondary mileage-rate context",
        "url": "https://www.shrm.org/secondary-mileage-context",
        "text": "Secondary context about mileage rates.",
        "source_tier": "secondary",
        "source_class": "secondary_only",
    }


def test_ag71a_irs_recovery_domain_constraints_survive_secondary_corridor() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(controller)
    captured_call: dict[str, Any] = {}

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        include_domains: list[str],
        _exclude_domains: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_call.update(
            {
                "queries": list(queries),
                "include_domains": list(include_domains),
                "exa_domain_filter": list(kwargs["exa_domain_filter"]),
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
        results_per_query=5,
        include_domains=list(_ORDINARY_SECONDARY_CORRIDOR),
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
        search_providers=["offline-fixture"],
        exa_domain_filter=list(_ORDINARY_SECONDARY_CORRIDOR),
        entity_hint="IRS",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )

    assert result["attempted"] is True
    assert captured_call["queries"] == _IRS_RECOVERY_QUERIES
    assert "irs.gov" in captured_call["include_domains"]
    assert "federalregister.gov" in captured_call["include_domains"]
    assert set(_ORDINARY_SECONDARY_CORRIDOR).issubset(
        captured_call["include_domains"]
    )
    assert "irs.gov" in captured_call["exa_domain_filter"]


def test_ag71a_satisfying_irs_candidate_survives_fit_and_visibility() -> None:
    lifecycle = _authority_trace()

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_secondary_context()],
        recovered_passages=[_official_irs_candidate()],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )
    lifecycle.update(decision.to_trace_fields())
    export = build_official_canonical_recovery_visibility_export(lifecycle)

    assert final[-1]["url"].startswith("https://www.irs.gov/")
    assert decision.source_fit_status == "matched_selected"
    assert export["accepted_readable_authority_evidence_count"] == 1
    assert export["final_selected_authority_evidence_count"] == 1
    assert export["citation_eligibility_state"] == "eligible"
