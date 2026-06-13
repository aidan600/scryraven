from __future__ import annotations

import pytest

from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
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


def _plan(
    query: str,
    *,
    source_class: str = _OFFICIAL_CURRENT,
    subject: str = "",
) -> dict[str, object]:
    return build_official_authority_acquisition_plan(
        source_classes=(source_class,),
        subject=subject or query,
        context_text=query,
        max_query_variants=3,
    )


def _decision(plan: dict[str, object]) -> dict[str, object]:
    decision = plan["authority_acquisition_decision"]
    assert isinstance(decision, dict)
    return decision


def _acquire(
    query: str,
    *,
    source_class: str = _OFFICIAL_CURRENT,
    core_topic: str = "",
    primary_entity: str = "",
) -> tuple[dict[str, object], dict[str, object]]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": [source_class],
            "source_class_recovery_queries": [],
            "source_class_satisfaction_status": {
                source_class: "expected_but_only_secondary"
            },
            "source_class_strong_satisfaction_counts": {source_class: 0},
        },
        runtime_trace={
            "query": query,
            "query_preview": query,
            "query_type": "official_current_status",
            "core_topic": core_topic or query,
            "primary_entity": primary_entity or query,
            "source_class_gap_candidates": [source_class],
        },
    )
    packet = result.trace["OfficialCanonicalRecoveryQueryAcquisition"]
    return result.recommendation, packet


def _recovery_domains(
    query: str,
    *,
    source_class: str = _LEGAL_TEXT,
    core_topic: str = "",
    primary_entity: str = "",
) -> list[str]:
    return build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=(source_class,),
        query=query,
        core_topic=core_topic or query,
        primary_entity=primary_entity or query,
    )


def _evidence_signals() -> dict[str, object]:
    return {
        "source_tier_counts": {"secondary": 3},
        "source_domain_counts": {"news.example": 2, "analysis.example": 1},
        "top_source_domains": [{"domain": "news.example", "count": 2}],
        "unique_source_domain_count": 2,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _record_lifecycle(recommendation: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
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
    return lifecycle, action


def _provenance_for(plan: dict[str, object], domain: str) -> dict[str, str]:
    provenance = plan["domain_constraint_provenance"]
    assert isinstance(provenance, list)
    for item in provenance:
        assert isinstance(item, dict)
        if item.get("domain") == domain:
            return {str(key): str(value) for key, value in item.items()}
    raise AssertionError(f"missing provenance for {domain}")


@pytest.mark.parametrize(
    ("family", "domain", "query", "subject", "source_class"),
    [
        (
            "tax_rate_form_fee_rule",
            "irs.gov",
            "What is the IRS 2026 standard mileage rate for business use?",
            "IRS 2026 standard mileage rate business",
            _OFFICIAL_CURRENT,
        ),
        (
            "travel_air_passenger_rights_rule",
            "transportation.gov",
            (
                "What current U.S. DOT rules under the Air Carrier Access Act "
                "apply to airline passengers who use wheelchairs?"
            ),
            "DOT wheelchair airline passenger current rules",
            _OFFICIAL_CURRENT,
        ),
        (
            "immigration_naturalization_filing_rule",
            "uscis.gov",
            "What is the current USCIS N-400 naturalization filing fee?",
            "USCIS N-400 naturalization filing fee",
            _OFFICIAL_CURRENT,
        ),
        (
            "labor_workplace_wage_compliance_rule",
            "dol.gov",
            "What current Department of Labor minimum wage rule applies?",
            "Department of Labor current minimum wage",
            _OFFICIAL_CURRENT,
        ),
        (
            "labor_workplace_wage_compliance_rule",
            "osha.gov",
            (
                "What current OSHA hazard communication workplace safety rule "
                "under 29 CFR 1910.1200 applies?"
            ),
            "OSHA hazard communication workplace safety rule",
            _OFFICIAL_CURRENT,
        ),
        (
            "consumer_finance_regulator_rule",
            "consumerfinance.gov",
            "What current CFPB mortgage servicing compliance rule applies?",
            "CFPB mortgage servicing compliance rule",
            _LEGAL_TEXT,
        ),
        (
            "consumer_finance_regulator_rule",
            "ftc.gov",
            (
                "What is the current FTC negative option click-to-cancel "
                "consumer protection rule legal status?"
            ),
            "FTC negative option click-to-cancel consumer protection rule",
            _LEGAL_TEXT,
        ),
        (
            "securities_issuer_filing_rule",
            "sec.gov",
            "Which current SEC issuer filing or Form 10-Q contains the rule?",
            "SEC issuer filing Form 10-Q",
            _OFFICIAL_CURRENT,
        ),
        (
            "health_product_regulator_rule",
            "fda.gov",
            "What is the current FDA enforcement posture for laboratory developed tests?",
            "FDA laboratory developed tests enforcement discretion",
            _OFFICIAL_CURRENT,
        ),
    ],
)
def test_ag96a2_explicit_or_strong_authority_signals_may_hard_constrain(
    family: str,
    domain: str,
    query: str,
    subject: str,
    source_class: str,
) -> None:
    plan = _plan(query, subject=subject, source_class=source_class)
    provenance = _provenance_for(plan, domain)

    assert family in plan["venue_families"]
    assert domain in plan["hard_domains"]
    assert provenance["constraint_strength"] == "hard_constraint"
    assert provenance["provenance"] == (
        "explicit_agency_domain_or_strong_authority_signal"
    )
    assert provenance["confidence"] == "high"
    decision = _decision(plan)
    assert decision["decision_type"] == "hard_corridor"
    assert decision["provider_domain_constraints_allowed"] is True
    assert decision["fallback_widening"] == (
        "bounded_soft_or_discovery_posture_if_hard_corridor_unsatisfied"
    )


def test_ag96a2_soft_family_candidates_do_not_become_hard_constraints() -> None:
    plan = _plan(
        (
            "What current official consumer finance regulator compliance rule "
            "applies to bank account fees?"
        ),
        source_class=_LEGAL_TEXT,
    )
    provenance = {
        item["domain"]: item
        for item in plan["domain_constraint_provenance"]
        if item["constraint_strength"] == "soft_domain_candidate"
    }

    assert "consumer_finance_regulator_rule" in plan["venue_families"]
    assert {"consumerfinance.gov", "ftc.gov"}.issubset(
        set(plan["soft_candidate_domains"])
    )
    assert plan["hard_domains"] == []
    assert _decision(plan)["decision_type"] == "soft_corridor"
    assert _decision(plan)["provider_domain_constraints_allowed"] is False
    assert provenance["consumerfinance.gov"]["provenance"] == "known_family_candidate"
    assert provenance["ftc.gov"]["confidence"] == "medium"


@pytest.mark.parametrize(
    ("query", "expected_family", "expected_hint"),
    [
        (
            (
                "At airport checkpoints, which identification documents are "
                "accepted for domestic flights?"
            ),
            "airport_screening_identity_access_rule",
            "accepted-ID guidance",
        ),
        (
            "Which identity credentials are required to access a state benefits portal?",
            "government_program_eligibility_access_rule",
            "agency FAQ",
        ),
        (
            "What is the current legal status and effective date for the final rule?",
            "legal_regulatory_challenge_effective_date_rule",
            "Federal Register",
        ),
    ],
)
def test_ag96a2_role_only_hints_do_not_force_domains(
    query: str,
    expected_family: str,
    expected_hint: str,
) -> None:
    plan = _plan(query)

    assert expected_family in plan["venue_families"]
    assert expected_hint in plan["role_hints"]
    assert plan["hard_domains"] == []
    assert _decision(plan)["provider_domain_constraints_allowed"] is False


def test_ag96a2_off_list_foreign_legal_question_uses_discovery_posture() -> None:
    query = (
        "What official legal or regulatory source currently lists which "
        "preservatives or additives are permitted in infant formula sold in Denmark?"
    )
    plan = _plan(query, source_class=_LEGAL_TEXT)
    recovery_domains = set(_recovery_domains(query))
    decision = _decision(plan)

    assert plan["hard_domains"] == []
    assert decision["decision_type"] == "discovery_corridor"
    assert decision["provider_domain_constraints_allowed"] is False
    assert "non_us_jurisdiction_signal" in decision["jurisdiction_disqualifiers"]
    assert recovery_domains.isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)
    assert all(
        domain not in " ".join(plan["query_variants"]).casefold()
        for domain in _KNOWN_US_AUTHORITY_DOMAINS
    )


@pytest.mark.parametrize(
    "query",
    [
        (
            "What official legal source currently lists workplace safety "
            "requirements for employers in Canada?"
        ),
        (
            "What official source states the legal status of a consumer finance "
            "noncompete rule in Canada?"
        ),
        (
            "Which official source in Canada lists public company filings "
            "and securities filing requirements?"
        ),
        (
            "What current official source lists medical device regulatory "
            "requirements in Denmark?"
        ),
        (
            "What current official source lists workplace safety requirements "
            "for employers in Singapore?"
        ),
    ],
)
def test_ag96a2_near_list_foreign_topics_are_not_caged_in_us_domains(
    query: str,
) -> None:
    plan = _plan(query, source_class=_LEGAL_TEXT)
    recovery_domains = set(_recovery_domains(query))
    decision = _decision(plan)

    assert set(plan["hard_domains"]).isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)
    assert decision["provider_domain_constraints_allowed"] is False
    assert recovery_domains.isdisjoint(_KNOWN_US_AUTHORITY_DOMAINS)


def test_ag96a2_source_class_recommendation_attaches_consumed_decision() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="What is the IRS 2026 standard mileage rate for business use?",
        current_date="2026-06-13",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic="IRS 2026 standard mileage rate business",
        primary_entity="IRS standard mileage rate",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"news.example": 2},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )
    decision = recommendation["source_class_recovery_authority_acquisition_decision"]

    assert decision["decision_type"] == "hard_corridor"
    assert "irs.gov" in recommendation["source_class_recovery_official_domains"]


def test_ag96a2_lifecycle_rejects_legacy_domains_without_decision() -> None:
    recommendation = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [_OFFICIAL_CURRENT],
        "source_class_recovery_queries": ["IRS official current rate"],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_reason": "legacy_test",
        "source_class_recovery_official_domains": ["irs.gov"],
    }

    _lifecycle, action = _record_lifecycle(recommendation)

    assert "official_domain_constraints" not in action["metadata"]


def test_ag96a2_lifecycle_consumes_decision_before_provider_constraints() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="What is the IRS 2026 standard mileage rate for business use?",
        current_date="2026-06-13",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic="IRS 2026 standard mileage rate business",
        primary_entity="IRS standard mileage rate",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"news.example": 2},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )

    _lifecycle, action = _record_lifecycle(recommendation)

    assert "irs.gov" in action["metadata"]["official_domain_constraints"]


def test_ag96a2_runtime_consumes_hard_corridor_for_provider_domain_constraints() -> None:
    recommendation, packet = _acquire(
        "What is the IRS 2026 standard mileage rate for business use?",
        core_topic="IRS 2026 standard mileage rate business",
        primary_entity="IRS standard mileage rate",
    )
    plan = packet["official_authority_acquisition_plan"]
    decision = _decision(plan)

    assert decision["decision_type"] == "hard_corridor"
    assert "irs.gov" in plan["hard_domains"]
    assert "irs.gov" in recommendation["source_class_recovery_official_domains"]


def test_ag96a2_runtime_does_not_promote_soft_corridor_to_hard_filter() -> None:
    recommendation, packet = _acquire(
        (
            "What current official consumer finance regulator compliance rule "
            "applies to bank account fees?"
        ),
        source_class=_LEGAL_TEXT,
        core_topic="consumer finance regulator compliance rule",
        primary_entity="bank account fee compliance rule",
    )
    plan = packet["official_authority_acquisition_plan"]
    decision = _decision(plan)

    assert decision["decision_type"] == "soft_corridor"
    assert {"consumerfinance.gov", "ftc.gov"}.issubset(
        set(plan["soft_candidate_domains"])
    )
    assert "source_class_recovery_official_domains" not in recommendation


def test_ag96a2_runtime_uses_discovery_corridor_for_off_list_foreign_question() -> None:
    recommendation, packet = _acquire(
        (
            "What official legal or regulatory source currently lists which "
            "preservatives or additives are permitted in infant formula sold in Denmark?"
        ),
        source_class=_LEGAL_TEXT,
        core_topic="infant formula additives permitted in Denmark",
        primary_entity="infant formula sold in Denmark",
    )
    plan = packet["official_authority_acquisition_plan"]
    decision = _decision(plan)

    assert decision["decision_type"] == "discovery_corridor"
    assert plan["hard_domains"] == []
    assert "source_class_recovery_official_domains" not in recommendation
