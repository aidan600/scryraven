from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    _infer_official_authority_venue,
    build_official_source_recovery_domain_constraints,
    build_recovery_source_quality_diagnostics,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_BASE_AUTHORITY_DOMAINS = {
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "regulations.gov",
}


def _recommendation(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What are the current official rules for the public program?",
        "current_date": "2026-06-10",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": "public program current official rules",
        "primary_entity": "public program",
        "anchor_packet": None,
        "source_tier_counts": {"secondary": 3},
        "source_domain_counts": {"news.example": 2, "analysis.example": 1},
        "top_source_domains": [{"domain": "news.example", "count": 2}],
        "official_evidence_found": False,
    }
    base.update(overrides)
    return build_source_class_recovery_recommendation(**base)


def _evidence_signals() -> dict[str, Any]:
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


def _record_lifecycle(recommendation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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


def _candidate_by_family(venue: Any, family_id: str) -> Any:
    for candidate in venue.candidates:
        if candidate.family_id == family_id:
            return candidate
    raise AssertionError(f"missing venue family {family_id}")


def test_ag93e6_airport_screening_access_id_query_gets_role_level_venue_hints() -> None:
    query = (
        "At airport checkpoints, which identification documents are accepted "
        "for domestic flights, and when did enforcement begin?"
    )
    out = _recommendation(
        query=query,
        core_topic="airport checkpoint accepted identification for domestic flights",
        primary_entity="domestic flight identification access rule",
    )
    venue = _infer_official_authority_venue(
        query,
        "airport checkpoint accepted identification for domestic flights",
        "domestic flight identification access rule",
    )
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    domains = set(out.get("source_class_recovery_official_domains", ()))
    candidate = _candidate_by_family(
        venue,
        "airport_screening_identity_access_rule",
    )

    assert candidate.constraint_strength == "role_only"
    assert "accepted_id_guidance" in candidate.venue_roles
    assert "airport screening" in query_text
    assert "accepted-id guidance" in query_text
    assert "official agency" in " ".join(candidate.search_hints).casefold()
    assert "transportation.gov" not in venue.domain_constraints
    assert "transportation.gov" not in domains


def test_ag93e6_official_agency_domains_survive_query_hint_cap() -> None:
    cases = [
        (
            (
                "As of today, what are the current U.S. DOT rules for airline "
                "passengers who use wheelchairs?"
            ),
            "DOT wheelchair airline passenger current rules",
            "DOT wheelchair passenger rules",
            "transportation.gov",
            "14 cfr part 382",
        ),
        (
            (
                "What are the current official rules and legal status of the "
                "FTC noncompete rule?"
            ),
            "FTC noncompete rule current legal status",
            "FTC noncompete rule",
            "ftc.gov",
            "court status",
        ),
        (
            (
                "What are the current official rules for FDA enforcement of "
                "laboratory developed tests after the LDT final rule?"
            ),
            "FDA LDT final rule enforcement posture",
            "FDA laboratory developed tests",
            "fda.gov",
            "enforcement discretion",
        ),
    ]

    for query, core_topic, primary_entity, domain, legacy_hint in cases:
        out = _recommendation(
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
        )
        venue = _infer_official_authority_venue(query, core_topic, primary_entity)
        query_text = " ".join(out["source_class_recovery_queries"]).casefold()

        assert domain in query_text
        assert legacy_hint in query_text
        assert domain in venue.domain_constraints
        assert domain in out["source_class_recovery_official_domains"]

    dot_venue = _infer_official_authority_venue(
        "Current U.S. DOT wheelchair passenger rights under the Air Carrier Access Act",
        "DOT wheelchair airline passenger current rules",
        "DOT wheelchair passenger rules",
    )
    dot_candidate = _candidate_by_family(dot_venue, "travel_air_passenger_rights_rule")
    assert dot_candidate.constraint_strength == "hard_constraint"
    assert "transportation.gov" in dot_candidate.domain_constraints
    assert "14 CFR Part 382" in dot_candidate.search_hints


def test_ag93e6_non_air_government_credential_query_uses_program_access_family() -> None:
    query = (
        "Which identity credentials are required to access a state unemployment "
        "benefits service portal?"
    )
    out = _recommendation(
        query=query,
        core_topic="state unemployment benefits access credential rule",
        primary_entity="state unemployment benefits service portal",
    )
    venue = _infer_official_authority_venue(
        query,
        "state unemployment benefits access credential rule",
        "state unemployment benefits service portal",
    )
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    candidate = _candidate_by_family(
        venue,
        "government_program_eligibility_access_rule",
    )

    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert candidate.constraint_strength == "role_only"
    assert candidate.domain_constraints == ()
    assert "airport_screening_identity_access_rule" not in venue.family_ids
    assert "official program guidance" in query_text
    assert "agency faq" in query_text
    assert "source_class_recovery_official_domains" not in out
    assert build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=out["missing_expected_source_classes"],
        query=query,
        core_topic="state unemployment benefits access credential rule",
        primary_entity="state unemployment benefits service portal",
        recovery_queries=out["source_class_recovery_queries"],
    ) == []


def test_ag93e6_tax_immigration_labor_and_legal_current_venues_remain_mapped() -> None:
    cases = [
        (
            "What is the current legal status of the FTC noncompete rule?",
            "consumer_finance_regulator_rule",
            "ftc.gov",
        ),
        (
            "What is the current FDA enforcement posture for laboratory developed tests?",
            "health_product_regulator_rule",
            "fda.gov",
        ),
        (
            "What is the current IRS tax filing fee, form instruction, and rate rule?",
            "tax_rate_form_fee_rule",
            "irs.gov",
        ),
        (
            "What is the current USCIS naturalization filing fee and service rule?",
            "immigration_naturalization_filing_rule",
            "uscis.gov",
        ),
        (
            "What Department of Labor workplace wage compliance rule applies?",
            "labor_workplace_wage_compliance_rule",
            "dol.gov",
        ),
        (
            "Which current SEC issuer filing contains the company's Form 10-Q?",
            "securities_issuer_filing_rule",
            "sec.gov",
        ),
        (
            "What is the current legal status, court order, and effective date for the final rule?",
            "legal_regulatory_challenge_effective_date_rule",
            None,
        ),
    ]

    for query, family_id, domain in cases:
        venue = _infer_official_authority_venue(query)
        assert family_id in venue.family_ids
        if domain is not None:
            assert domain in venue.domain_constraints


def test_ag93e6_ordinary_private_id_document_explainer_does_not_trigger() -> None:
    out = _recommendation(
        query=(
            "Explain why gyms ask for identification documents when people "
            "sign up for membership."
        ),
        core_topic="gym membership identification documents explainer",
        primary_entity="gym membership",
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []
    assert out["source_class_recovery_queries"] == []
    assert "source_class_recovery_official_domains" not in out


def test_ag93e6_secondary_news_candidate_remains_non_satisfying() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "title": "News report about an official access rule",
                "url": "https://apnews.com/example-access-rule",
                "text": "A secondary story summarizes agency guidance.",
                "source_tier": "secondary",
                "_provider_role": "source_class_recovery",
                "retrieval_stage": "source_class_recovery",
            }
        ]
    )

    assert diagnostics["recovery_source_quality_status"] == "secondary_only"
    assert diagnostics["recovered_official_or_primary_count"] == 0
    assert diagnostics["recovered_source_class_counts"] == {}


def test_ag93e6_venue_hints_are_trace_safe_and_deterministic() -> None:
    text = (
        "raw_prompt provider_payload secret: current airport screening "
        "accepted identification enforcement date"
    )
    first = _infer_official_authority_venue(text)
    second = _infer_official_authority_venue(text)
    encoded = repr(first).casefold()

    assert first == second
    assert "airport_screening_identity_access_rule" in first.family_ids
    for forbidden in ("raw_prompt", "provider_payload", "secret"):
        assert forbidden not in encoded


def test_ag93e6_explicit_agency_domains_are_consumed_by_lifecycle_action() -> None:
    recommendation = _recommendation(
        query=(
            "As of today, what are the current U.S. DOT rules for airline "
            "passengers who use wheelchairs?"
        ),
        core_topic="DOT wheelchair airline passenger current rules",
        primary_entity="DOT wheelchair passenger rules",
    )

    lifecycle, action = _record_lifecycle(recommendation)

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert any(
        "transportation.gov" in query.casefold()
        for query in action["queries"]
    )
    assert "transportation.gov" in action["metadata"]["official_domain_constraints"]


def test_ag93e6_acquired_queries_consume_venue_inference_with_domain_gating() -> None:
    query = (
        "At airport checkpoints, which identification documents are accepted "
        "for domestic flights, and when did enforcement begin?"
    )
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["official_current_rules"],
            "source_class_recovery_queries": [],
        },
        runtime_trace={
            "query_preview": query,
            "query_type": "official_current_status",
            "core_topic": "airport checkpoint accepted identification for domestic flights",
            "primary_entity": "domestic flight identification access rule",
        },
    )

    recommendation = result.recommendation
    lifecycle, action = _record_lifecycle(recommendation)
    query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()

    assert result.trace["OfficialCanonicalRecoveryQueryAcquisition"][
        "acquisition_repair_used"
    ] is True
    assert recommendation["source_class_recovery_queries"]
    assert "airport screening" in query_text
    assert "accepted-id guidance" in query_text
    assert "enforcement-date notice" in query_text
    assert "transportation.gov" not in recommendation.get(
        "source_class_recovery_official_domains",
        (),
    )
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert "transportation.gov" not in action["metadata"].get(
        "official_domain_constraints",
        (),
    )


def test_ag93e6_production_code_has_no_named_case_hardcoding() -> None:
    marker = re.compile(r"\breal[-\s]?id\b|\btsa\b|\bdhs\b", re.IGNORECASE)
    for path in (
        _ROOT / "core" / "source_class_recovery.py",
        _ROOT / "core" / "official_canonical_recovery_query_acquisition.py",
    ):
        assert marker.search(path.read_text(encoding="utf-8")) is None
