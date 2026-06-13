from __future__ import annotations

from typing import Any

from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    _official_source_target_hints,
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
_USCIS_QUERY = (
    "What official source currently states the current USCIS filing fee for "
    "Form N-400? Answer from official/current sources and cite the official source."
)
_SSA_QUERY = (
    "What official source currently states the Social Security taxable maximum "
    "wage base for 2026? Answer from official/current sources and cite the "
    "official source."
)
_IRS_QUERY = (
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
        source_tier_counts={"secondary": 2},
        source_domain_counts={"secondary.example": 2},
        top_source_domains=[{"domain": "secondary.example", "count": 2}],
        official_evidence_found=False,
    )


def _acquire_with_existing(
    query: str,
    *,
    existing_queries: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": [_OFFICIAL_CURRENT],
            "source_class_recovery_queries": list(existing_queries or []),
            "source_class_satisfaction_status": {
                _OFFICIAL_CURRENT: "expected_but_only_secondary"
            },
            "source_class_strong_satisfaction_counts": {_OFFICIAL_CURRENT: 0},
        },
        runtime_trace={
            "query": query,
            "query_preview": query,
            "query_type": "official_current_status",
            "core_topic": query,
            "primary_entity": query,
            "source_class_gap_candidates": [_OFFICIAL_CURRENT],
        },
    )
    return (
        result.recommendation,
        result.trace["OfficialCanonicalRecoveryQueryAcquisition"],
    )


def _lifecycle_trace(query: str, queries: list[str]) -> dict[str, Any]:
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_execution_attempted": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": (
            "official_canonical_recovery_query_acquisition:official_current_rules"
        ),
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
        "active_source_class_recovery_queries": queries,
        "active_source_class_recovery_action_envelope": {
            "action_type": "recover_missing_source_class",
            "required_source_class": [_OFFICIAL_CURRENT],
            "allowed_action": True,
        },
        "query": query,
        "query_preview": query,
        "core_topic": query,
        "primary_entity": query,
    }


def _official_candidate(url: str, title: str, text: str) -> dict[str, Any]:
    return {
        "url": url,
        "title": title,
        "text": text,
        "source_tier": "official",
        "source_class": _OFFICIAL_CURRENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "readable_text_available": True,
        "readability_status": "readable",
        "currentness_signal": "current",
    }


def _select(query: str, candidate: dict[str, Any]) -> tuple[list[Any], Any]:
    queries = list(_plan(query)["query_variants"])
    return apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[candidate],
        lifecycle_trace=_lifecycle_trace(query, queries),
        max_final_evidence=3,
    )


def test_ag96a4_explicit_agency_form_fee_queries_are_answer_bearing_and_bounded() -> None:
    plan = _plan(_USCIS_QUERY)
    recommendation = _recommendation(
        _USCIS_QUERY,
        core_topic="USCIS Form N-400 filing fee",
    )
    combined = " ".join(
        [
            *plan["query_variants"],
            *recommendation["source_class_recovery_queries"],
            *_official_source_target_hints(_USCIS_QUERY),
            *recommendation.get("source_class_recovery_official_domains", []),
        ]
    ).casefold()

    assert _decision(plan)["decision_type"] == "hard_corridor"
    assert "uscis.gov" in plan["hard_domains"]
    assert "uscis" in combined
    assert "n-400" in combined
    assert "filing fee" in combined
    assert "fee schedule" in combined or "form instructions" in combined
    assert "irs" not in combined
    assert "irs.gov" not in combined


def test_ag96a4_cross_family_recovery_query_contamination_is_dropped() -> None:
    recommendation, packet = _acquire_with_existing(
        _USCIS_QUERY,
        existing_queries=[
            "IRS 2026 standard mileage rate business official notice revenue procedure"
        ],
    )
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()
    domain_text = " ".join(
        recommendation.get("source_class_recovery_official_domains", [])
    ).casefold()

    assert packet["stale_cross_family_query_count"] == 1
    assert "uscis.gov" in recommendation["source_class_recovery_official_domains"]
    assert "irs" not in query_text
    assert "irs.gov" not in domain_text
    assert "n-400" in query_text
    assert "filing fee" in query_text


def test_ag96a4_form_fee_answer_bearing_candidate_admitted_generic_page_rejected() -> None:
    positive = _official_candidate(
        "https://www.uscis.gov/forms/fee-fixture/form-n-400",
        "Form N-400 filing fee schedule",
        "USCIS official current fee schedule lists the Form N-400 filing fee.",
    )
    generic = _official_candidate(
        "https://www.uscis.gov/alerts",
        "USCIS alerts",
        "Official USCIS alert page with general updates and notifications.",
    )

    selected, positive_decision = _select(_USCIS_QUERY, positive)
    rejected, negative_decision = _select(_USCIS_QUERY, generic)

    assert selected == [positive]
    assert positive_decision.source_fit_status == "matched_selected"
    assert rejected == []
    assert negative_decision.source_fit_status == "no_matching_source_fit"
    assert "official_candidate_not_answer_bearing" in (
        negative_decision.source_fit_rejection_reasons
    )


def test_ag96a4_inferable_program_rate_queries_are_answer_bearing_and_bounded() -> None:
    plan = _plan(_SSA_QUERY)
    query_text = " ".join(plan["query_variants"]).casefold()

    assert "social_security_contribution_benefit_rule" in plan["venue_families"]
    assert _decision(plan)["decision_type"] == "hard_corridor"
    assert "ssa.gov" in plan["hard_domains"]
    assert "ssa" in query_text
    assert "social security" in query_text
    assert "taxable maximum" in query_text
    assert "wage base" in query_text
    assert "contribution benefit base" in query_text
    assert "irs" not in query_text


def test_ag96a4_program_threshold_candidate_admitted_generic_page_rejected() -> None:
    positive = _official_candidate(
        "https://www.ssa.gov/oact/cola/cbb-fixture.html",
        "Contribution and benefit base",
        (
            "Official Social Security table states the 2026 taxable maximum "
            "wage base and contribution and benefit base."
        ),
    )
    generic = _official_candidate(
        "https://www.ssa.gov/agency",
        "Social Security Administration",
        "Official agency page for Social Security online services and updates.",
    )

    selected, positive_decision = _select(_SSA_QUERY, positive)
    rejected, negative_decision = _select(_SSA_QUERY, generic)

    assert selected == [positive]
    assert positive_decision.source_fit_status == "matched_selected"
    assert rejected == []
    assert negative_decision.source_fit_status == "no_matching_source_fit"
    assert "official_candidate_not_answer_bearing" in (
        negative_decision.source_fit_rejection_reasons
    )


def test_ag96a4_irs_mileage_authority_success_fixture_preserved() -> None:
    plan = _plan(_IRS_QUERY)
    recommendation = _recommendation(
        _IRS_QUERY,
        core_topic="U.S. business standard mileage rate 2026",
    )
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert "tax_rate_form_fee_rule" in plan["venue_families"]
    assert "irs.gov" in plan["hard_domains"]
    assert _decision(plan)["decision_type"] == "hard_corridor"
    assert "irs" in query_text
    assert "standard mileage rate" in query_text
    assert "revenue procedure" in query_text


def test_ag96a4_international_off_list_resilience_preserved() -> None:
    denmark = (
        "What official legal or regulatory source currently lists which "
        "preservatives or additives are permitted in infant formula sold in Denmark?"
    )
    singapore = (
        "What current official source lists workplace safety requirements for "
        "employers in Singapore?"
    )

    denmark_plan = _plan(denmark, source_class=_LEGAL_TEXT)
    singapore_domains = set(
        build_official_source_recovery_domain_constraints(
            missing_expected_source_classes=(_LEGAL_TEXT,),
            query=singapore,
            core_topic="workplace safety requirements for employers in Singapore",
            primary_entity="Singapore workplace safety requirements",
        )
    )

    assert _decision(denmark_plan)["decision_type"] == "discovery_corridor"
    assert denmark_plan["hard_domains"] == []
    assert singapore_domains.isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)


def test_ag96a4_legacy_domains_still_need_ag96_decision_to_constrain_provider() -> None:
    controller = RunController()
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

    record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
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
