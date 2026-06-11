from __future__ import annotations

from typing import Any

import pytest

from core.authority_candidate_passport import (
    AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)
from core.source_class_recovery import (
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_lifecycle import (
    record_source_class_recovery_lifecycle,
)

_OFFICIAL_CURRENT = "official_current_rules"


def _acquire(
    query: str,
    *,
    core_topic: str,
    primary_entity: str,
    missing: str = _OFFICIAL_CURRENT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": [missing],
            "source_class_recovery_queries": [],
            "source_class_satisfaction_status": {
                missing: "expected_but_only_secondary"
            },
            "source_class_strong_satisfaction_counts": {missing: 0},
        },
        runtime_trace={
            "query": query,
            "query_preview": query,
            "query_type": "official_current_status",
            "core_topic": core_topic,
            "primary_entity": primary_entity,
            "source_class_gap_candidates": [missing],
        },
    )
    packet = result.trace["OfficialCanonicalRecoveryQueryAcquisition"]
    return result.recommendation, packet


def _authority_trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=_OFFICIAL_CURRENT,
        required_authority=_OFFICIAL_CURRENT,
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=("official current source access rule",),
        required_source_classes=(_OFFICIAL_CURRENT,),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
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
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_attempt_count": 1,
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": [_OFFICIAL_CURRENT],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    return trace


def _official_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "official-current-access-rule",
        "title": "Official accepted identification enforcement guidance",
        "url": "https://agency.example/current-access-rule",
        "text": (
            "Official current agency guidance lists accepted identification "
            "documents and states the enforcement date for access."
        ),
        "source_tier": "official",
        "source_class": _OFFICIAL_CURRENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "offline-fixture",
        "provider_rank_or_position": 1,
        "currentness_signal": "current enforcement date observed",
    }
    candidate.update(overrides)
    return candidate


def _secondary_context(url: str = "https://news.example/current-access-rule") -> dict[str, Any]:
    return {
        "title": "Secondary context",
        "url": url,
        "text": "Secondary discussion of an official rule.",
        "source_tier": "secondary",
        "source_class": "secondary_only",
    }


def test_ag93e8_airport_access_id_role_only_strategy_has_no_named_case_domain() -> None:
    recommendation, packet = _acquire(
        (
            "At airport checkpoints, which identification documents are accepted "
            "for domestic flights, and when did enforcement begin?"
        ),
        core_topic="airport checkpoint accepted identification for domestic flights",
        primary_entity="domestic flight identification access rule",
    )
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()
    plan = packet["official_authority_acquisition_plan"]

    assert "airport_screening_identity_access_rule" in plan["venue_families"]
    assert plan["hard_domains"] == []
    assert "airport screening" in query_text
    assert "accepted-id guidance" in query_text
    assert "enforcement-date notice" in query_text
    assert "source_class_recovery_official_domains" not in recommendation
    assert all(marker not in query_text for marker in ("real id", "real-id", "tsa", "dhs"))


@pytest.mark.parametrize(
    (
        "query",
        "core_topic",
        "primary_entity",
        "missing",
        "family",
        "hard_domain",
        "expected_terms",
    ),
    [
        (
            "What is the current IRS standard mileage rate for business use in 2026?",
            "IRS 2026 standard mileage rate business",
            "IRS",
            "official_current_rules",
            "tax_rate_form_fee_rule",
            "irs.gov",
            ("irs", "standard mileage rate", "revenue procedure"),
        ),
        (
            "What is the current USCIS N-400 naturalization filing fee?",
            "USCIS N-400 naturalization filing fee",
            "USCIS",
            "official_current_rules",
            "immigration_naturalization_filing_rule",
            "uscis.gov",
            ("uscis", "policy manual", "form instructions", "filing fee schedule"),
        ),
        (
            "What is the current FDA enforcement posture after the LDT final rule?",
            "FDA laboratory developed tests final rule enforcement posture",
            "FDA laboratory developed tests",
            "current_primary_or_official",
            "health_product_regulator_rule",
            "fda.gov",
            ("fda", "federal register", "enforcement discretion", "final rule"),
        ),
        (
            "What is the current legal status of the FTC noncompete rule?",
            "FTC noncompete rule current legal status",
            "FTC noncompete rule",
            "legal_or_regulatory_text",
            "consumer_finance_regulator_rule",
            "ftc.gov",
            ("ftc", "federal register", "court status", "final rule"),
        ),
        (
            "What current DOT rules apply to airline passengers who use wheelchairs?",
            "DOT wheelchair airline passenger current rules",
            "DOT wheelchair passenger rules",
            "current_primary_or_official",
            "travel_air_passenger_rights_rule",
            "transportation.gov",
            ("transportation.gov", "14 cfr part 382", "passenger rights"),
        ),
    ],
)
def test_ag93e8_explicit_authority_families_build_hard_domain_strategy(
    query: str,
    core_topic: str,
    primary_entity: str,
    missing: str,
    family: str,
    hard_domain: str,
    expected_terms: tuple[str, ...],
) -> None:
    recommendation, packet = _acquire(
        query,
        core_topic=core_topic,
        primary_entity=primary_entity,
        missing=missing,
    )
    plan = packet["official_authority_acquisition_plan"]
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert family in plan["venue_families"]
    assert hard_domain in plan["hard_domains"]
    assert hard_domain in recommendation["source_class_recovery_official_domains"]
    assert plan["source_classes_required"] == [missing]
    for term in expected_terms:
        assert term in query_text


def test_ag93e8_soft_domain_candidates_are_query_hints_not_hard_constraints() -> None:
    recommendation, packet = _acquire(
        (
            "What current official consumer finance regulator compliance rule "
            "applies to bank account fees?"
        ),
        core_topic="consumer finance regulator compliance rule",
        primary_entity="bank account fee compliance rule",
    )
    plan = packet["official_authority_acquisition_plan"]
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert "consumer_finance_regulator_rule" in plan["venue_families"]
    assert {"consumerfinance.gov", "ftc.gov"}.issubset(
        set(plan["soft_candidate_domains"])
    )
    assert plan["hard_domains"] == []
    assert "source_class_recovery_official_domains" not in recommendation
    assert "consumerfinance.gov" in query_text or "ftc.gov" in query_text


def test_ag93e8_state_public_program_stays_role_only_without_federal_domains() -> None:
    recommendation, packet = _acquire(
        "Which identity credentials are required to access a state benefits portal?",
        core_topic="state benefits portal credential access rule",
        primary_entity="state benefits service portal",
    )
    plan = packet["official_authority_acquisition_plan"]
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert "government_program_eligibility_access_rule" in plan["venue_families"]
    assert plan["hard_domains"] == []
    assert plan["soft_candidate_domains"] == []
    assert "official program guidance" in query_text
    assert "agency faq" in query_text
    assert "federalregister.gov" not in query_text
    assert "source_class_recovery_official_domains" not in recommendation


def test_ag93e8_readable_official_fixture_is_admitted_and_passported() -> None:
    trace = _authority_trace()
    candidate = _official_candidate()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_secondary_context()],
        recovered_passages=[candidate],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[candidate],
        final_top_evidence=final,
        surface_visibility={
            "answer_contract_visible_candidate_ids": [candidate["candidate_id"]],
            "context_packet_visible_candidate_ids": [candidate["candidate_id"]],
            "analyst_visible_candidate_ids": [candidate["candidate_id"]],
            "author_visible_candidate_ids": [candidate["candidate_id"]],
            "cited_in_final_answer_candidate_ids": [candidate["candidate_id"]],
        },
    )
    export = build_official_canonical_recovery_visibility_export(trace)
    passport = trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY][
        "AuthorityCandidatePassportProjection"
    ]["passports"][0]

    assert decision.source_fit_status == "matched_selected"
    assert final[-1]["url"] == candidate["url"]
    assert export["accepted_readable_authority_evidence_count"] == 1
    assert passport["final_disposition"] == "promoted_final_authority_evidence"


def test_ag93e8_news_and_unreadable_official_candidates_do_not_satisfy() -> None:
    news_trace = _authority_trace(result_count=1, accepted_url_count=0)
    news_final, news_decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_secondary_context("https://analysis.example/context")],
        recovered_passages=[_secondary_context()],
        lifecycle_trace=news_trace,
        max_final_evidence=4,
    )
    news_trace.update(news_decision.to_trace_fields())
    news_export = build_official_canonical_recovery_visibility_export(news_trace)

    unreadable_trace = _authority_trace(result_count=1, accepted_url_count=1)
    unreadable = _official_candidate(
        candidate_id="official-looking-unreadable",
        text="",
        readable_text_available=False,
        readability_status="readability_failed",
    )
    unreadable_final, unreadable_decision = (
        apply_recovered_evidence_visibility_boundary(
            final_top_evidence=[_secondary_context("https://analysis.example/context")],
            recovered_passages=[unreadable],
            lifecycle_trace=unreadable_trace,
            max_final_evidence=4,
        )
    )
    unreadable_trace.update(unreadable_decision.to_trace_fields())
    unreadable_export = build_official_canonical_recovery_visibility_export(
        unreadable_trace
    )

    assert news_final == [_secondary_context("https://analysis.example/context")]
    assert news_decision.source_fit_status == "no_matching_source_fit"
    assert news_export["accepted_readable_authority_evidence_count"] == 0
    assert unreadable_final == [_secondary_context("https://analysis.example/context")]
    assert unreadable_decision.source_fit_status == "no_matching_source_fit"
    assert "readability_failed" in unreadable_decision.source_fit_rejection_reasons
    assert unreadable_export["accepted_readable_authority_evidence_count"] == 0


def test_ag93e8_negative_controls_do_not_open_recovery_without_obligation() -> None:
    private = build_source_class_recovery_recommendation(
        query="Explain why private gyms ask for identification at sign-up.",
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="conceptual_explainer",
        core_topic="private gym identification explainer",
        primary_entity="private gym membership",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"analysis.example": 2},
        top_source_domains=[{"domain": "analysis.example", "count": 2}],
        official_evidence_found=False,
    )
    ordinary = apply_official_canonical_recovery_query_acquisition(
        recommendation={"source_class_recovery_recommended": False},
        runtime_trace={
            "query_preview": "Summarize ordinary weak corpus context about gym IDs.",
            "query_type": "conceptual_explainer",
            "corpus_weak": True,
            "weak_corpus_recovery_used": True,
        },
    )

    assert private["source_class_recovery_recommended"] is False
    assert private["missing_expected_source_classes"] == []
    assert ordinary.recommendation == {"source_class_recovery_recommended": False}
    assert ordinary.trace["OfficialCanonicalRecoveryQueryAcquisition"][
        "acquisition_repair_used"
    ] is False


def test_ag93e8_hard_iteration_budget_still_blocks_recovery_action() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="What is the current IRS standard mileage rate for 2026?",
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic="IRS standard mileage rate",
        primary_entity="IRS",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"news.example": 2},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )
    lifecycle = record_source_class_recovery_lifecycle(
        RunController(),
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"news.example": 2},
            "top_source_domains": [{"domain": "news.example", "count": 2}],
            "official_evidence_found": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=False,
    )

    assert recommendation["source_class_recovery_recommended"] is True
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert "blocked_by_iteration_budget" in lifecycle[
        "active_source_class_recovery_blockers"
    ]
