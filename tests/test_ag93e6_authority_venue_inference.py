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


def test_ag93e6_air_travel_access_id_query_gets_official_venue_hints() -> None:
    query = (
        "Do people need REAL ID or other acceptable identification for "
        "domestic flights now, and when did enforcement start?"
    )
    out = _recommendation(
        query=query,
        core_topic="acceptable identification for domestic flights",
        primary_entity="domestic flight identification requirements",
    )
    venue = _infer_official_authority_venue(
        query,
        "acceptable identification for domestic flights",
        "domestic flight identification requirements",
    )
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    domains = set(out["source_class_recovery_official_domains"])

    assert "travel_air_access_credential_rule" in venue.family_ids
    assert "airport screening" in query_text
    assert "official agency" in query_text
    assert _BASE_AUTHORITY_DOMAINS | {"transportation.gov"} <= domains


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
        query_text = " ".join(out["source_class_recovery_queries"]).casefold()

        assert domain in query_text
        assert legacy_hint in query_text
        assert domain in out["source_class_recovery_official_domains"]


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

    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert "government_program_eligibility_access_rule" in venue.family_ids
    assert "travel_air_access_credential_rule" not in venue.family_ids
    assert "official program guidance" in query_text
    assert "agency faq" in query_text


def test_ag93e6_tax_immigration_labor_and_legal_current_venues_remain_mapped() -> None:
    cases = [
        (
            "What is the current tax filing fee, form instruction, and rate rule?",
            "tax_rate_form_fee_rule",
            "irs.gov",
        ),
        (
            "What is the current naturalization filing fee and service rule?",
            "immigration_naturalization_filing_rule",
            "uscis.gov",
        ),
        (
            "What workplace wage compliance rule applies to the current minimum wage?",
            "labor_workplace_wage_compliance_rule",
            "dol.gov",
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
    assert "travel_air_access_credential_rule" in first.family_ids
    for forbidden in ("raw_prompt", "provider_payload", "secret"):
        assert forbidden not in encoded


def test_ag93e6_recommendation_domains_are_consumed_by_lifecycle_action() -> None:
    recommendation = _recommendation(
        query=(
            "Do people need REAL ID or other acceptable identification for "
            "domestic flights now, and when did enforcement start?"
        ),
        core_topic="acceptable identification for domestic flights",
        primary_entity="domestic flight identification requirements",
    )

    lifecycle, action = _record_lifecycle(recommendation)

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert any(
        "airport screening" in query.casefold()
        for query in action["queries"]
    )
    assert "transportation.gov" in action["metadata"]["official_domain_constraints"]


def test_ag93e6_acquired_queries_receive_same_official_domain_constraints() -> None:
    query = (
        "Do people need REAL ID or other acceptable identification for "
        "domestic flights now, and when did enforcement start?"
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
            "core_topic": "acceptable identification for domestic flights",
            "primary_entity": "domestic flight identification requirements",
        },
    )

    recommendation = result.recommendation
    lifecycle, action = _record_lifecycle(recommendation)

    assert result.trace["OfficialCanonicalRecoveryQueryAcquisition"][
        "acquisition_repair_used"
    ] is True
    assert "transportation.gov" in recommendation[
        "source_class_recovery_official_domains"
    ]
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert "transportation.gov" in action["metadata"]["official_domain_constraints"]


def test_ag93e6_production_code_has_no_named_case_hardcoding() -> None:
    marker = re.compile(r"\breal[-\s]?id\b|\btsa\b|\bdhs\b", re.IGNORECASE)
    for path in (
        _ROOT / "core" / "source_class_recovery.py",
        _ROOT / "core" / "official_canonical_recovery_query_acquisition.py",
    ):
        assert marker.search(path.read_text(encoding="utf-8")) is None
