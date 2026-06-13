from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    build_official_authority_acquisition_plan,
    build_official_source_recovery_domain_constraints,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_OFFICIAL_CURRENT = "official_current_rules"
_LEGAL_TEXT = "legal_or_regulatory_text"
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
_LIVE_DOGFOOD_QUERY = (
    "What official source currently states the U.S. standard mileage rates for "
    "business use in 2026? Answer from official/current sources and cite the "
    "official source."
)


def _plan(query: str, *, source_class: str = _OFFICIAL_CURRENT) -> dict[str, Any]:
    return build_official_authority_acquisition_plan(
        source_classes=(source_class,),
        subject=query,
        context_text=query,
        max_query_variants=3,
    )


def _decision(plan: dict[str, Any]) -> dict[str, Any]:
    decision = plan["authority_acquisition_decision"]
    assert isinstance(decision, dict)
    return decision


def _recommendation(query: str, *, core_topic: str | None = None) -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query=query,
        current_date="2026-06-13",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic=core_topic or query,
        primary_entity=core_topic or query,
        anchor_packet=None,
        source_tier_counts={"secondary": 3},
        source_domain_counts={"taxpublisher.example": 2, "hr.example": 1},
        top_source_domains=[{"domain": "taxpublisher.example", "count": 2}],
        official_evidence_found=False,
    )


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=None,
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(
                source_classes_missing=(),
                next_queries=(),
            )
        ),
        fulfillment_handoff=SimpleNamespace(unfulfilled_items=(), partial_items=()),
    )


def _handoff(query: str) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state={
            "query": query,
            "intent": "general",
            "report_type": "general_research",
            "query_type": "official_current_status",
            "core_topic": "U.S. business standard mileage rate 2026",
            "primary_entity": "U.S. business standard mileage rate",
            "_source_class_recovery_lifecycle_recommendation": _recommendation(
                query,
                core_topic="U.S. business standard mileage rate 2026",
            ),
            "_source_class_recovery_answer_contract_observability": {
                "source_class_satisfaction_status": {
                    _OFFICIAL_CURRENT: "expected_but_only_secondary"
                },
                "source_class_strong_satisfaction_counts": {_OFFICIAL_CURRENT: 0},
            },
            "_source_tier_recovery_lifecycle": {
                "source_tier_counts": {"secondary": 3},
                "official_evidence_found": False,
                "community_signal_found": False,
                "low_trust_sources_found": False,
                "pollution_detected": False,
            },
            "_source_domain_recovery_lifecycle": {
                "source_domain_counts": {"taxpublisher.example": 2},
                "top_source_domains": [
                    {"domain": "taxpublisher.example", "count": 2}
                ],
                "unique_source_domain_count": 1,
                "on_domain_source_count": 0,
                "off_domain_source_count": 1,
            },
            "_pre_recovery_answer_contract_result": _answer_contract_result(),
            "corpus_state": "OFF_TOPIC",
            "corpus_weak": True,
            "weak_corpus_recovery_considered": True,
            "weak_corpus_recovery_used": True,
            "weak_corpus_recovery_skip_reason": "weak_corpus_recovery_used",
            "evidence_integration_checkpoint_trace": {},
            "current_search_depth_for_recovery": "basic",
            "iterations_run": 1,
            "max_iterations": 1,
            "waste_flags": [],
        },
    )


def _assert_no_docs_manual_queries(queries: list[str]) -> None:
    joined = " ".join(queries).casefold()
    assert "documentation reference manual" not in joined
    assert "reference documentation official docs" not in joined


def test_ag96a3_exact_live_query_infers_shared_tax_rate_authority() -> None:
    plan = _plan(_LIVE_DOGFOOD_QUERY)
    decision = _decision(plan)

    assert "tax_rate_form_fee_rule" in plan["venue_families"]
    assert "irs.gov" in plan["hard_domains"]
    assert decision["decision_type"] == "hard_corridor"
    assert decision["provider_domain_constraints_allowed"] is True
    assert any(
        item["domain"] == "irs.gov"
        and item["family_id"] == "tax_rate_form_fee_rule"
        for item in plan["domain_constraint_provenance"]
    )
    query_text = " ".join(plan["query_variants"]).casefold()
    assert "irs" in query_text
    assert "standard mileage rate" in query_text
    assert "revenue procedure" in query_text


def test_ag96a3_non_explicit_us_rate_query_uses_same_authority_core() -> None:
    query = "official source for 2026 U.S. business standard mileage rate"
    recommendation = _recommendation(
        query,
        core_topic="U.S. business standard mileage rate 2026",
    )
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert recommendation["missing_expected_source_classes"] == [_OFFICIAL_CURRENT]
    assert "irs.gov" in recommendation["source_class_recovery_official_domains"]
    assert "irs" in query_text
    assert "standard mileage rate" in query_text
    assert "revenue procedure" in query_text
    _assert_no_docs_manual_queries(recommendation["source_class_recovery_queries"])


def test_ag96a3_explicit_authority_easy_path_still_uses_decision() -> None:
    query = "IRS 2026 business standard mileage rate official source"
    plan = _plan(query)

    assert _decision(plan)["decision_type"] == "hard_corridor"
    assert "irs.gov" in plan["hard_domains"]
    assert any(
        item["provenance"] == "explicit_agency_domain_or_strong_authority_signal"
        for item in plan["domain_constraint_provenance"]
    )


def test_ag96a3_ambiguous_rate_query_uses_discovery_not_us_gravity() -> None:
    query = "business mileage rate 2026 official source"
    plan = _plan(query)

    assert plan["hard_domains"] == []
    assert "tax_rate_form_fee_rule" not in plan["venue_families"]
    assert _decision(plan)["decision_type"] == "discovery_corridor"
    assert "irs" not in " ".join(plan["query_variants"]).casefold()


def test_ag96a3_generic_live_shape_avoids_documentation_manual_queries() -> None:
    query = (
        "official current source agency guidance current requirements U.S. "
        "standard mileage rates for business use in 2026"
    )
    recommendation = _recommendation(
        query,
        core_topic="U.S. standard mileage rates for business use in 2026",
    )

    assert recommendation["missing_expected_source_classes"] == [_OFFICIAL_CURRENT]
    _assert_no_docs_manual_queries(recommendation["source_class_recovery_queries"])
    assert "irs" in " ".join(recommendation["source_class_recovery_queries"]).casefold()


def test_ag96a3_denmark_off_list_remains_discovery_without_us_domains() -> None:
    query = (
        "What official legal or regulatory source currently lists which "
        "preservatives or additives are permitted in infant formula sold in Denmark?"
    )
    plan = _plan(query, source_class=_LEGAL_TEXT)
    recovery_domains = set(
        build_official_source_recovery_domain_constraints(
            missing_expected_source_classes=(_LEGAL_TEXT,),
            query=query,
            core_topic="infant formula additives permitted in Denmark",
            primary_entity="infant formula sold in Denmark",
        )
    )

    assert _decision(plan)["decision_type"] == "discovery_corridor"
    assert plan["hard_domains"] == []
    assert recovery_domains.isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)


def test_ag96a3_singapore_near_list_remains_outside_us_hard_domains() -> None:
    query = (
        "What current official source lists workplace safety requirements for "
        "employers in Singapore?"
    )
    plan = _plan(query, source_class=_LEGAL_TEXT)
    recovery_domains = set(
        build_official_source_recovery_domain_constraints(
            missing_expected_source_classes=(_LEGAL_TEXT,),
            query=query,
            core_topic="workplace safety requirements for employers in Singapore",
            primary_entity="Singapore workplace safety requirements",
        )
    )

    assert set(plan["hard_domains"]).isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)
    assert _decision(plan)["provider_domain_constraints_allowed"] is False
    assert recovery_domains.isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)


def test_ag96a3_weak_corpus_does_not_starve_bounded_official_slot() -> None:
    handoff = _handoff(_LIVE_DOGFOOD_QUERY)
    admission = handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is True
    assert "budget_hard_exhausted" not in admission["admission_blockers"]
    assert "weak_corpus_recovery_owns_path" not in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert "irs.gov" in handoff.recommendation["source_class_recovery_official_domains"]


def test_ag96a3_legacy_domains_without_decision_do_not_constrain_provider() -> None:
    controller = RunController()
    recommendation = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [_OFFICIAL_CURRENT],
        "source_class_recovery_queries": [
            "IRS 2026 standard mileage rate business official notice revenue procedure"
        ],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_reason": "legacy_domain_fixture",
        "source_class_recovery_official_domains": ["irs.gov"],
    }

    record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"taxpublisher.example": 2},
            "top_source_domains": [
                {"domain": "taxpublisher.example", "count": 2}
            ],
            "official_evidence_found": False,
        },
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

    assert "official_domain_constraints" not in action["metadata"]
