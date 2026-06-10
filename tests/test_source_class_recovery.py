from __future__ import annotations

from pathlib import Path
from typing import Any

from core.source_class_recovery import (
    build_source_class_observability_telemetry,
    build_source_class_recovery_candidate_v2,
    build_source_class_recovery_recommendation,
)


def _recommendation(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What changed for the example topic?",
        "current_date": "2026-05-18",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "current_events",
        "core_topic": "example topic",
        "primary_entity": "Example",
        "anchor_packet": None,
        "source_tier_counts": {"secondary": 2, "unknown": 2},
        "source_domain_counts": {"apnews.com": 2, "analysis.example": 2},
        "top_source_domains": [{"domain": "apnews.com", "count": 2}],
        "official_evidence_found": False,
    }
    base.update(overrides)
    return build_source_class_recovery_recommendation(**base)


def _observability(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What does the example rule require?",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": "example rule",
        "primary_entity": "Example",
        "anchor_packet": None,
        "final_top_evidence": [
            {
                "source_id": 1,
                "title": "Secondary explainer",
                "url": "https://analysis.example/story",
                "text": "A secondary overview of the issue.",
                "source_tier": "secondary",
            }
        ],
        "final_answer_source_ids": [],
    }
    base.update(overrides)
    return build_source_class_observability_telemetry(**base)


def _candidate_budget_payload(bucket: str = "room_remaining") -> dict[str, Any]:
    return {
        "schema_version": "retrieval_budget_pressure_shadow_v1",
        "shadow_mode": True,
        "hard_mode_budget": {"budget_pressure_bucket": bucket},
    }


def _candidate_from_observability(
    *,
    trace_updates: dict[str, Any] | None = None,
    **observability_overrides: Any,
) -> dict[str, Any]:
    trace = _observability(**observability_overrides)
    trace.update(
        {
            "answer_class": "partial_answer",
            "evidence_sufficient": False,
            "corpus_state": "HEALTHY",
            "weak_corpus_recovery_used": False,
            "weak_corpus_recovery_decision": "no_action",
            "weak_corpus_recovery_reason": "not_weak_corpus",
            "weak_corpus_recovery_blockers": [],
            "active_source_class_recovery_used": False,
            "active_source_class_recovery_skip_reason": "not_recommended",
            "active_source_class_recovery_blockers": [],
            "retrieval_budget_pressure_shadow": _candidate_budget_payload(),
        }
    )
    if trace_updates:
        trace.update(trace_updates)
    return build_source_class_recovery_candidate_v2(trace)


def _assert_shadow_recovery_shape(out: dict[str, Any]) -> None:
    assert out["source_class_recovery_shadow_mode"] is True
    assert out["source_class_recovery_recommended"] is True
    assert 1 <= out["source_class_recovery_query_count"] <= 2
    assert out["source_class_recovery_query_count"] == len(out["source_class_recovery_queries"])
    assert "provider" not in out
    assert "search_depth" not in out


def _assert_candidate_v2_shape(
    out: dict[str, Any],
    *,
    candidate: bool,
) -> None:
    assert out["schema_version"] == "source_class_recovery_candidate_v2"
    assert out["shadow_mode"] is True
    assert out["source_class_recovery_candidate_v2_shadow"] is candidate
    assert isinstance(out["source_class_recovery_candidate_v2_classes"], list)
    assert isinstance(out["source_class_recovery_candidate_v2_reasons"], list)
    assert isinstance(out["source_class_recovery_candidate_v2_blockers"], list)
    assert isinstance(
        out["source_class_recovery_candidate_v2_status_by_class"],
        dict,
    )
    if candidate:
        assert out["source_class_recovery_candidate_v2_query_source"] == (
            "class_intent_catalog"
        )
        assert out["source_class_recovery_candidate_v2_query_count"] == min(
            len(out["source_class_recovery_candidate_v2_classes"]),
            2,
        )
    else:
        assert out["source_class_recovery_candidate_v2_query_source"] == "none"
        assert out["source_class_recovery_candidate_v2_query_count"] == 0


def _assert_observability_official_current_gap(out: dict[str, Any]) -> None:
    assert "official_current_rules" in out["expected_source_classes_raw"]
    assert "official_current_rules" in out["source_class_gap_candidates"]
    assert out["source_class_underfire_shadow"] is True
    assert out["source_class_satisfaction_status"]["official_current_rules"] == (
        "unsatisfied"
    )
    assert out["final_official_source_count"] == 0


def test_care_like_official_current_rules_recommends_generic_recovery() -> None:
    out = _recommendation(
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program eligibility requirements",
        primary_entity="care program",
        anchor_packet={
            "source_class_expectation": "official",
            "claim_or_metric_type": "rule",
            "freshness_requirement": "official-current",
        },
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert out["source_class_recovery_reason"] == "missing_expected_source_class:official_current_rules"
    assert "query" in out["source_class_recovery_trigger_fields"]
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    assert "official" in query_text
    assert "current" in query_text
    assert "rules" in query_text
    assert "government" in query_text


def test_access_id_enforcement_question_recommends_official_current_rules() -> None:
    out = _recommendation(
        query=(
            "Do people need REAL ID or other acceptable identification for "
            "domestic flights now, and when did enforcement start?"
        ),
        core_topic="acceptable identification for domestic flights",
        primary_entity="domestic flight identification requirements",
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert out["source_class_recovery_reason"] == (
        "missing_expected_source_class:official_current_rules"
    )


def test_generic_government_access_document_rule_recommends_official_current_rules() -> None:
    out = _recommendation(
        query=(
            "What identification documents are accepted for entry at a state "
            "courthouse screening checkpoint?"
        ),
        core_topic="state courthouse screening accepted identification documents",
        primary_entity="state courthouse screening",
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["official_current_rules"]


def test_non_government_document_explainer_does_not_recommend_official_recovery() -> None:
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


def test_enforcement_date_access_rule_uses_active_recovery() -> None:
    out = _recommendation(
        query=(
            "When did enforcement begin for the state access credential rule "
            "used for public service entry?"
        ),
        core_topic="state public service access credential enforcement date",
        primary_entity="state access credential rule",
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert "query" in out["source_class_recovery_trigger_fields"]


def test_existing_irs_uscis_and_canonical_active_cases_still_work() -> None:
    irs = _recommendation(
        query="What is the current IRS standard mileage rate for 2026?",
        core_topic="IRS standard mileage rate",
        primary_entity="IRS",
    )
    uscis = _recommendation(
        query="What is the current USCIS N-400 naturalization filing fee?",
        core_topic="USCIS N-400 naturalization filing fee",
        primary_entity="USCIS",
    )
    canonical = _recommendation(
        query="Use official documentation to explain PostgreSQL MVCC concurrency behavior.",
        core_topic="PostgreSQL MVCC official documentation",
        primary_entity="PostgreSQL",
    )

    assert irs["missing_expected_source_classes"] == ["official_current_rules"]
    assert uscis["missing_expected_source_classes"] == ["official_current_rules"]
    assert canonical["missing_expected_source_classes"] == [
        "primary_source_documents"
    ]


def test_existing_legal_observability_case_still_works() -> None:
    out = _observability(
        query=(
            "What legal or regulatory text explains the public access rule, "
            "and what does the regulation require?"
        ),
        core_topic="public access regulation text",
        primary_entity="public access regulation",
    )

    assert "legal_or_regulatory_text" in out["expected_source_classes_raw"]
    assert "legal_or_regulatory_text" in out["source_class_gap_candidates"]


def test_tesla_like_issuer_filings_recommends_investor_or_sec_recovery() -> None:
    out = _recommendation(
        query=(
            "Use company filings and reported company materials to compare the exact "
            "company-reported margin metric from the latest quarterly results."
        ),
        report_type="quantitative_comparison",
        query_type="company_metric",
        core_topic="reported company margin metric",
        primary_entity="Tesla",
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["issuer_filings_or_company_materials"]
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    assert "investor relations" in query_text or "sec" in query_text
    assert "quarterly results" in query_text
    assert "earnings release" in query_text or "10-q" in query_text or "10-k" in query_text


def test_governor_polling_average_recommends_polling_recovery() -> None:
    out = _recommendation(
        query=(
            "For the governor race, distinguish the latest poll from broader polling "
            "averages, toplines, and crosstabs."
        ),
        core_topic="governor race polling",
        primary_entity="governor race",
        source_tier_counts={"secondary": 4},
        source_domain_counts={"cbsnews.com": 2, "politico.com": 2},
        top_source_domains=[{"domain": "cbsnews.com", "count": 2}],
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["polling_data_or_aggregator"]
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    assert "polling average" in query_text
    assert "toplines" in query_text
    assert "crosstabs" in query_text
    assert "aggregator" in query_text


def test_primary_source_documents_recommends_primary_document_recovery() -> None:
    out = _recommendation(
        query="Find primary sources and primary documents for the policy change.",
        core_topic="policy change evidence",
        primary_entity="policy change",
    )

    _assert_shadow_recovery_shape(out)
    assert out["missing_expected_source_classes"] == ["primary_source_documents"]
    query_text = " ".join(out["source_class_recovery_queries"]).casefold()
    assert "primary sources" in query_text
    assert "documents" in query_text
    assert "records" in query_text
    assert "archive" in query_text


def test_latest_news_about_governor_race_does_not_recommend_recovery() -> None:
    out = _recommendation(
        query="What is the latest news about the governor race?",
        core_topic="governor race latest news",
        primary_entity="governor race",
        source_tier_counts={"secondary": 4},
        source_domain_counts={"cbsnews.com": 2, "politico.com": 2},
        top_source_domains=[{"domain": "cbsnews.com", "count": 2}],
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []
    assert out["source_class_recovery_reason"] is None
    assert out["source_class_recovery_queries"] == []
    assert out["source_class_recovery_query_count"] == 0


def test_top_two_primary_system_does_not_recommend_primary_documents() -> None:
    out = _recommendation(
        query="How does the top-two primary system affect the governor race?",
        core_topic="top-two primary system",
        primary_entity="governor race",
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []


def test_primary_false_positive_wording_does_not_trigger_primary_recovery() -> None:
    out = _recommendation(
        query="What is the primary reason the care program rules changed?",
        core_topic="primary reason care program rules changed",
        primary_entity="Care Program",
    )

    assert out["source_class_recovery_recommended"] is False
    assert "primary_source_documents" not in out["missing_expected_source_classes"]


def test_historical_conceptual_current_rule_wording_does_not_recommend_rules() -> None:
    out = _recommendation(
        query=(
            "Explain the historical background of the current official rule concept "
            "for this program, not the current requirements."
        ),
        core_topic="official current rule concept",
        primary_entity="program",
        anchor_packet={
            "source_class_expectation": "official",
            "claim_or_metric_type": "rule",
            "freshness_requirement": "official-current",
        },
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []


def test_agency_official_wording_does_not_change_active_recovery_contract() -> None:
    out = _recommendation(
        query="What does NHTSA officially say about the latest vehicle recall?",
        core_topic="NHTSA latest vehicle recall",
        primary_entity="NHTSA",
        source_tier_counts={"secondary": 2, "social_or_forum": 1},
        source_domain_counts={"news.example": 2, "forum.example": 1},
        top_source_domains=[{"domain": "news.example", "count": 2}],
    )

    assert out["source_class_recovery_recommended"] is False
    assert out["missing_expected_source_classes"] == []
    assert out["source_class_recovery_queries"] == []


def test_source_class_observability_flags_agency_official_secondary_only() -> None:
    out = _observability(
        query="What does NHTSA officially say about the latest vehicle recall?",
        core_topic="NHTSA latest vehicle recall",
        primary_entity="NHTSA",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News report on NHTSA official recall notice",
                "url": "https://news.example/nhtsa-recall",
                "text": "A news summary describes what the agency said.",
                "source_tier": "secondary",
            },
            {
                "source_id": 2,
                "title": "Owner forum recall discussion",
                "url": "https://forum.example/thread",
                "text": "Community discussion of the vehicle recall.",
                "source_tier": "social_or_forum",
            },
        ],
    )

    assert "official_current_rules" in out["expected_source_classes_raw"]
    assert out["source_class_underfire_shadow"] is True
    assert "official_current_rules" in out["source_class_gap_candidates"]
    assert out["source_class_satisfaction_status"]["official_current_rules"] == (
        "expected_but_only_secondary"
    )
    assert out["source_class_strong_satisfaction_counts"]["official_current_rules"] == 0
    assert out["source_class_secondary_only_counts"]["official_current_rules"] >= 1


def test_source_class_observability_agency_official_domain_satisfies_strongly() -> None:
    out = _observability(
        query="What does NHTSA officially say about the latest vehicle recall?",
        core_topic="NHTSA latest vehicle recall",
        primary_entity="NHTSA",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "NHTSA official recall notice",
                "url": "https://www.nhtsa.gov/recalls",
                "text": "Official agency recall guidance and notice.",
                "source_tier": "official",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is False
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_satisfaction_status"]["official_current_rules"] == (
        "satisfied_strong"
    )
    assert out["final_official_source_count"] == 1


def test_source_class_observability_flags_current_official_state_agency_guidance() -> None:
    out = _observability(
        query=(
            "Who is eligible under current official state agency guidance, "
            "and what are the application rules?"
        ),
        core_topic="state court program eligibility and application rules",
        primary_entity="state court program",
    )

    _assert_observability_official_current_gap(out)


def test_source_class_observability_flags_current_state_agency_application_rules() -> None:
    out = _observability(
        query="Current official state agency eligibility and application rules",
        core_topic="public benefits program eligibility and application rules",
        primary_entity="public benefits program",
    )

    _assert_observability_official_current_gap(out)


def test_source_class_observability_flags_blind_housing_assistance_program() -> None:
    out = _observability(
        query=(
            "For a state housing assistance program, who qualifies under "
            "current official agency guidance and how do applications work?"
        ),
        core_topic="state housing assistance program",
        primary_entity="state housing assistance program",
    )

    _assert_observability_official_current_gap(out)


def test_source_class_observability_flags_blind_county_childcare_subsidy() -> None:
    out = _observability(
        query=(
            "For a county childcare subsidy, what official state agency "
            "guidance controls eligibility and application rules?"
        ),
        core_topic="county childcare subsidy",
        primary_entity="county childcare subsidy",
    )

    _assert_observability_official_current_gap(out)


def test_source_class_observability_clinical_trial_eligibility_stays_unclassified() -> None:
    out = _observability(
        query=(
            "What clinical trial eligibility criteria apply under the study "
            "protocol?"
        ),
        core_topic="clinical trial eligibility criteria",
        primary_entity="study protocol",
    )

    assert "official_current_rules" not in out["expected_source_classes_raw"]


def test_source_class_observability_software_application_rules_stay_unclassified() -> None:
    out = _observability(
        query=(
            "What application rules control a framework app configuration "
            "under the current release?"
        ),
        core_topic="framework app configuration",
        primary_entity="software framework",
    )

    assert "official_current_rules" not in out["expected_source_classes_raw"]


def test_source_class_observability_sports_game_rules_stay_unclassified() -> None:
    out = _observability(
        query="How do official overtime rules work in a chess league game?",
        core_topic="chess league game overtime rules",
        primary_entity="chess league",
    )

    assert "official_current_rules" not in out["expected_source_classes_raw"]


def test_source_class_observability_regulatory_background_stays_unclassified() -> None:
    out = _observability(
        query=(
            "Explain the history and background of this regulation concept "
            "rather than identifying current official rules."
        ),
        core_topic="regulation concept background",
        primary_entity="regulation concept",
    )

    assert "official_current_rules" not in out["expected_source_classes_raw"]


def test_source_class_observability_primary_false_positive_phrasing_stays_non_primary() -> None:
    primary_reason = _observability(
        query="What is the primary reason this public program changed?",
        core_topic="primary reason public program changed",
        primary_entity="public program",
    )
    top_two_primary_reasons = _observability(
        query="What are the top-two primary reasons this policy changed?",
        core_topic="top-two primary reasons policy changed",
        primary_entity="policy",
    )

    assert "primary_source_documents" not in primary_reason[
        "expected_source_classes_raw"
    ]
    assert "primary_source_documents" not in top_two_primary_reasons[
        "expected_source_classes_raw"
    ]


def test_source_class_observability_flags_legal_statutory_gap_candidate() -> None:
    out = _observability(
        query=(
            "What does the public offices act say about membership rules, "
            "and which parliamentary material explains the statutory change?"
        ),
        core_topic="public offices act statutory change",
        primary_entity="Public Offices Act",
    )

    assert out["source_class_underfire_shadow"] is True
    assert "legal_or_regulatory_text" in out["expected_source_classes_raw"]
    assert "parliamentary_or_legislative_material" in out[
        "expected_source_classes_raw"
    ]
    assert "legal_or_regulatory_text" in out["source_class_gap_candidates"]
    assert "parliamentary_or_legislative_material" in out[
        "source_class_gap_candidates"
    ]
    assert out["final_legal_or_regulatory_source_count"] == 0
    assert out["source_class_underfire_reasons"] == [
        "missing_expected_source_class"
    ]


def test_source_class_observability_parliament_news_is_secondary_only() -> None:
    out = _observability(
        query=(
            "Which parliamentary material explains the House of Lords hereditary "
            "peers bill?"
        ),
        core_topic="House of Lords hereditary peers bill",
        primary_entity="House of Lords",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News commentary on Parliament and the hereditary peers bill",
                "url": "https://news.example/peers-bill",
                "text": "Commentary mentions Parliament, the bill, and the House of Lords.",
                "source_tier": "secondary",
            }
        ],
    )

    assert "parliamentary_or_legislative_material" in out[
        "expected_source_classes_raw"
    ]
    assert out["source_class_underfire_shadow"] is True
    assert "parliamentary_or_legislative_material" in out[
        "source_class_gap_candidates"
    ]
    assert out["source_class_satisfaction_status"][
        "parliamentary_or_legislative_material"
    ] == "expected_but_only_secondary"
    assert out["source_class_strong_satisfaction_counts"][
        "parliamentary_or_legislative_material"
    ] == 0


def test_source_class_observability_parliament_domain_satisfies_strongly() -> None:
    out = _observability(
        query=(
            "Which parliamentary material explains the House of Lords hereditary "
            "peers bill?"
        ),
        core_topic="House of Lords hereditary peers bill",
        primary_entity="House of Lords",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "House of Lords hereditary peers bill parliamentary stages",
                "url": "https://bills.parliament.uk/bills/1234",
                "text": "Official bill page with parliamentary stages and materials.",
                "source_tier": "official",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is False
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_satisfaction_status"][
        "parliamentary_or_legislative_material"
    ] == "satisfied_strong"


def test_source_class_observability_flags_regulatory_secondary_only_gap() -> None:
    out = _observability(
        query=(
            "For an AI Act-style regulation, what obligations are already in "
            "force, what enforcement dates are still ahead, and does signing "
            "a Code of Practice change legal duties or mainly reduce "
            "compliance uncertainty?"
        ),
        core_topic="AI Act-style regulation obligations and enforcement dates",
        primary_entity="AI Act-style regulation",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News explainer on compliance uncertainty",
                "url": "https://news.example/ai-regulation-explainer",
                "text": "A secondary news summary without official legal text.",
                "source_tier": "secondary",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is True
    assert "official_current_rules" in out["expected_source_classes_raw"]
    assert "legal_or_regulatory_text" in out["expected_source_classes_raw"]
    assert "official_current_rules" in out["source_class_gap_candidates"]
    assert "legal_or_regulatory_text" in out["source_class_gap_candidates"]
    assert out["final_official_source_count"] == 0


def test_source_class_observability_ai_act_secondary_legal_discussion_is_not_strong() -> None:
    out = _observability(
        query=(
            "For the EU AI Act GPAI Code of Practice, what obligations are "
            "already in force and what legal duties change?"
        ),
        core_topic="EU AI Act GPAI Code of Practice legal duties",
        primary_entity="EU AI Act",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "arXiv discussion of GPAI Code of Practice legal duties",
                "url": "https://arxiv.org/abs/2601.00001",
                "text": "A secondary discussion of the AI Act and legal obligations.",
                "source_tier": "secondary",
            },
            {
                "source_id": 2,
                "title": "Nature analysis of AI Act obligations",
                "url": "https://www.nature.com/articles/example",
                "text": "Analysis discusses the Code of Practice and compliance uncertainty.",
                "source_tier": "secondary",
            },
        ],
    )

    assert "legal_or_regulatory_text" in out["expected_source_classes_raw"]
    assert out["source_class_underfire_shadow"] is True
    assert "legal_or_regulatory_text" in out["source_class_gap_candidates"]
    assert out["source_class_satisfaction_status"]["legal_or_regulatory_text"] == (
        "expected_but_only_secondary"
    )
    assert out["source_class_strong_satisfaction_counts"][
        "legal_or_regulatory_text"
    ] == 0
    assert out["final_legal_or_regulatory_source_count"] == 0


def test_source_class_observability_ai_act_eurlex_satisfies_legal_strongly() -> None:
    out = _observability(
        query=(
            "For the EU AI Act GPAI Code of Practice, what obligations are "
            "already in force and what legal duties change?"
        ),
        core_topic="EU AI Act GPAI Code of Practice legal duties",
        primary_entity="EU AI Act",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Regulation (EU) 2024/1689 AI Act full text Article 53",
                "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
                "text": "Official Journal legal text with GPAI obligations.",
                "source_tier": "official",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is False
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_satisfaction_status"]["legal_or_regulatory_text"] == (
        "satisfied_strong"
    )
    assert out["final_legal_or_regulatory_source_count"] == 1


def test_source_class_observability_flags_historical_primary_source_gap() -> None:
    out = _observability(
        query=(
            "Find historical public health orders using archival primary-source "
            "texts rather than secondary summaries."
        ),
        core_topic="historical public health orders",
        primary_entity="public health orders",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Historical overview",
                "url": "https://history.example/overview",
                "text": "A secondary historical summary.",
                "source_tier": "secondary",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is True
    assert "primary_source_documents" in out["source_class_gap_candidates"]
    assert "archival_primary_text" in out["source_class_gap_candidates"]
    assert out["final_primary_source_count"] == 0
    assert out["final_archival_source_count"] == 0


def test_source_class_observability_flags_historical_law_code_text_gap() -> None:
    out = _observability(
        query=(
            "For a medieval law code, use the direct translated legal text to "
            "explain what the code says about obligations."
        ),
        core_topic="medieval law code translated legal text",
        primary_entity="medieval law code",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Modern scholarly summary",
                "url": "https://scholarship.example/law-code-summary",
                "text": "A secondary summary of the historical legal tradition.",
                "source_tier": "secondary",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is True
    assert "historical_legal_text" in out["source_class_gap_candidates"]
    assert "legal_or_regulatory_text" in out["source_class_gap_candidates"]
    assert out["final_legal_or_regulatory_source_count"] == 0


def test_source_class_observability_historical_legal_secondary_is_not_strong() -> None:
    out = _observability(
        query=(
            "For medieval Cnut law codes, use direct translated legal text and "
            "primary source documents to explain what the laws say."
        ),
        core_topic="medieval Cnut law codes translated legal text",
        primary_entity="Cnut law codes",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "JSTOR article on Cnut law codes and legal history",
                "url": "https://www.jstor.org/stable/example",
                "text": "Secondary historical discussion of law codes and obligations.",
                "source_tier": "secondary",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is True
    assert "historical_legal_text" in out["source_class_gap_candidates"]
    assert out["source_class_satisfaction_status"]["historical_legal_text"] == (
        "expected_but_only_secondary"
    )
    assert out["source_class_strong_satisfaction_counts"]["historical_legal_text"] == 0


def test_source_class_observability_historical_sourcebook_satisfies_strongly() -> None:
    out = _observability(
        query=(
            "For medieval Cnut law codes, use direct translated legal text and "
            "primary source documents to explain what the laws say."
        ),
        core_topic="medieval Cnut law codes translated legal text",
        primary_entity="Cnut law codes",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Cnut law codes translated source text full text",
                "url": "https://sourcebooks.fordham.edu/source/cnut-laws.asp",
                "text": "Direct translated legal text from the medieval law codes.",
                "source_tier": "unknown",
            }
        ],
    )

    assert out["source_class_underfire_shadow"] is False
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_satisfaction_status"]["historical_legal_text"] == (
        "satisfied_strong"
    )
    assert out["source_class_satisfaction_status"]["primary_source_documents"] == (
        "satisfied_strong"
    )


def test_source_class_observability_magna_carta_style_primary_text_satisfies_gap() -> None:
    out = _observability(
        query=(
            "Use the primary text of a medieval charter and an authoritative "
            "explanation to describe what its clauses say."
        ),
        core_topic="medieval charter primary text clauses",
        primary_entity="medieval charter",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Medieval charter primary source text translation clauses",
                "url": "https://archive.example/medieval-charter/full-text",
                "text": "Primary source text with translated clauses from the charter.",
                "source_tier": "secondary",
            },
            {
                "source_id": 2,
                "title": "Authoritative library explanation of the charter",
                "url": "https://library.example/charter-explanation",
                "text": "Archival library explanation of the historical charter.",
                "source_tier": "secondary",
            },
        ],
    )

    assert out["source_class_underfire_shadow"] is False
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_underfire_blockers"] == [
        "all_expected_source_classes_satisfied"
    ]
    assert out["final_primary_source_count"] >= 1
    assert out["final_archival_source_count"] >= 1
    assert out["final_legal_or_regulatory_source_count"] >= 1
    assert all(
        status == "satisfied_strong"
        for status in out["source_class_satisfaction_status"].values()
    )


def test_candidate_v2_nhtsa_style_official_secondary_only_positive() -> None:
    out = _candidate_from_observability(
        query="What does NHTSA officially say about the latest vehicle recall?",
        core_topic="NHTSA latest vehicle recall",
        primary_entity="NHTSA",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News report on NHTSA official recall notice",
                "url": "https://news.example/vehicle-recall",
                "text": "A secondary news report describes what the agency said.",
                "source_tier": "secondary",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=True)
    assert out["source_class_recovery_candidate_v2_classes"] == [
        "official_current_rules"
    ]
    assert "expected_source_class_secondary_only" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]
    assert "final_answer_lacks_official_source" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]


def test_candidate_v2_uk_parliamentary_secondary_only_positive() -> None:
    out = _candidate_from_observability(
        query=(
            "Which parliamentary material explains the House of Lords hereditary "
            "peers bill?"
        ),
        core_topic="House of Lords hereditary peers bill",
        primary_entity="House of Lords",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News commentary on Parliament and the hereditary peers bill",
                "url": "https://news.example/peers-bill",
                "text": "Commentary mentions Parliament, the bill, and the House of Lords.",
                "source_tier": "secondary",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=True)
    assert out["source_class_recovery_candidate_v2_classes"] == [
        "parliamentary_or_legislative_material"
    ]
    assert "expected_source_class_secondary_only" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]


def test_candidate_v2_eu_legal_regulatory_secondary_only_positive() -> None:
    out = _candidate_from_observability(
        query=(
            "For the EU AI Act GPAI Code of Practice, what obligations are "
            "already in force and what legal duties change?"
        ),
        core_topic="EU AI Act GPAI Code of Practice legal duties",
        primary_entity="EU AI Act",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Analysis of legal duties and compliance uncertainty",
                "url": "https://analysis.example/legal-duties",
                "text": "A secondary discussion of legal obligations and duties.",
                "source_tier": "secondary",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=True)
    assert "legal_or_regulatory_text" in out[
        "source_class_recovery_candidate_v2_classes"
    ]
    assert "expected_source_class_secondary_only" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]
    assert "final_answer_lacks_legal_or_regulatory_source" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]


def test_candidate_v2_cnut_historical_legal_secondary_only_positive() -> None:
    out = _candidate_from_observability(
        query=(
            "For medieval Cnut law codes, use direct translated legal text and "
            "primary source documents to explain what the laws say."
        ),
        core_topic="medieval Cnut law codes translated legal text",
        primary_entity="Cnut law codes",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Scholarly discussion of Cnut law codes",
                "url": "https://scholarship.example/cnut-laws",
                "text": "Secondary historical discussion of law codes and obligations.",
                "source_tier": "secondary",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=True)
    assert "historical_legal_text" in out[
        "source_class_recovery_candidate_v2_classes"
    ]
    assert "expected_source_class_secondary_only" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]


def test_candidate_v2_magna_carta_strong_source_satisfied_negative() -> None:
    out = _candidate_from_observability(
        query=(
            "Use the primary source text of the medieval Magna Carta charter "
            "and an authoritative explanation to describe what its clauses say."
        ),
        core_topic="medieval Magna Carta charter primary source text clauses",
        primary_entity="Magna Carta",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Magna Carta primary source text translation clauses",
                "url": "https://sourcebooks.fordham.edu/source/magnacarta.asp",
                "text": "Primary source text with translated clauses from the charter.",
                "source_tier": "unknown",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=False)
    assert out["source_class_recovery_candidate_v2_classes"] == []
    assert out["source_class_recovery_candidate_v2_blockers"] == [
        "all_expected_source_classes_satisfied_strong"
    ]


def test_candidate_v2_blind_agency_official_positive_and_negative() -> None:
    secondary = _candidate_from_observability(
        query=(
            "What does the food safety agency officially say about the current "
            "advisory?"
        ),
        core_topic="food safety agency current advisory",
        primary_entity="food safety agency",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News report on an agency official advisory",
                "url": "https://news.example/agency-advisory",
                "text": "A secondary story summarizes the official agency advisory.",
                "source_tier": "secondary",
            }
        ],
    )
    official = _candidate_from_observability(
        query=(
            "What does the food safety agency officially say about the current "
            "advisory?"
        ),
        core_topic="food safety agency current advisory",
        primary_entity="food safety agency",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Official food safety agency advisory",
                "url": "https://foodsafety.gov/advisory",
                "text": "Official current agency advisory and guidance.",
                "source_tier": "official",
            }
        ],
    )

    _assert_candidate_v2_shape(secondary, candidate=True)
    assert secondary["source_class_recovery_candidate_v2_classes"] == [
        "official_current_rules"
    ]
    _assert_candidate_v2_shape(official, candidate=False)
    assert official["source_class_recovery_candidate_v2_blockers"] == [
        "all_expected_source_classes_satisfied_strong"
    ]


def test_candidate_v2_blind_legislative_legal_positive_and_negative() -> None:
    secondary = _candidate_from_observability(
        query=(
            "What does the state clean water statute say, and which legislative "
            "material explains the bill?"
        ),
        core_topic="state clean water statute legislative material",
        primary_entity="state clean water statute",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "News commentary on the clean water law",
                "url": "https://news.example/clean-water-law",
                "text": "Commentary mentions the statute, bill, and legal provisions.",
                "source_tier": "secondary",
            }
        ],
    )
    official = _candidate_from_observability(
        query=(
            "What does the state clean water statute say, and which legislative "
            "material explains the bill?"
        ),
        core_topic="state clean water statute legislative material",
        primary_entity="state clean water statute",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Clean water bill official legislative text section 12",
                "url": "https://www.congress.gov/bill/example",
                "text": "Official bill and statute text with sections and provisions.",
                "source_tier": "official",
            }
        ],
    )

    _assert_candidate_v2_shape(secondary, candidate=True)
    assert "legal_or_regulatory_text" in secondary[
        "source_class_recovery_candidate_v2_classes"
    ]
    assert "parliamentary_or_legislative_material" in secondary[
        "source_class_recovery_candidate_v2_classes"
    ]
    _assert_candidate_v2_shape(official, candidate=False)


def test_candidate_v2_blind_historical_primary_positive_and_negative() -> None:
    secondary = _candidate_from_observability(
        query=(
            "Use archival primary source text of a colonial charter to explain "
            "what the ordinance says."
        ),
        core_topic="colonial charter archival primary source text",
        primary_entity="colonial charter",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Historical overview of a colonial charter",
                "url": "https://history.example/colonial-charter",
                "text": "A secondary discussion of the charter and ordinance.",
                "source_tier": "secondary",
            }
        ],
    )
    archive = _candidate_from_observability(
        query=(
            "Use archival primary source text of a colonial charter to explain "
            "what the ordinance says."
        ),
        core_topic="colonial charter archival primary source text",
        primary_entity="colonial charter",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Colonial charter primary source text full text",
                "url": "https://archives.gov/colonial-charter/full-text",
                "text": "Archival primary source text and full transcription.",
                "source_tier": "unknown",
            }
        ],
    )

    _assert_candidate_v2_shape(secondary, candidate=True)
    assert "primary_source_documents" in secondary[
        "source_class_recovery_candidate_v2_classes"
    ]
    assert "archival_primary_text" in secondary[
        "source_class_recovery_candidate_v2_classes"
    ]
    _assert_candidate_v2_shape(archive, candidate=False)


def test_candidate_v2_legal_history_interpretation_without_expected_class_negative() -> None:
    out = _candidate_from_observability(
        query="Explain why scholars interpret this legal history debate differently.",
        core_topic="legal history interpretation debate",
        primary_entity="legal history debate",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Scholarly interpretation of legal history",
                "url": "https://scholarship.example/legal-history",
                "text": "Secondary scholarship is enough for this interpretation query.",
                "source_tier": "secondary",
            }
        ],
    )

    _assert_candidate_v2_shape(out, candidate=False)
    assert out["source_class_recovery_candidate_v2_blockers"] == [
        "no_expected_source_class"
    ]


def test_candidate_v2_no_expected_class_negative() -> None:
    out = _candidate_from_observability(
        query="What is the latest news about a regional event?",
        core_topic="regional event latest news",
        primary_entity="regional event",
    )

    _assert_candidate_v2_shape(out, candidate=False)
    assert out["source_class_recovery_candidate_v2_classes"] == []
    assert out["source_class_recovery_candidate_v2_blockers"] == [
        "no_expected_source_class"
    ]


def test_candidate_v2_budget_context_adds_shadow_budget_blockers() -> None:
    out = _candidate_from_observability(
        query="What are the official current rules for the benefit program?",
        core_topic="benefit program official current rules",
        primary_entity="benefit program",
        trace_updates={
            "retrieval_budget_pressure_shadow": _candidate_budget_payload(
                "exhausted"
            ),
            "active_source_class_recovery_skip_reason": (
                "blocked_by_iteration_budget"
            ),
            "active_source_class_recovery_blockers": [
                "blocked_by_iteration_budget"
            ],
        },
    )

    _assert_candidate_v2_shape(out, candidate=True)
    assert out["source_class_recovery_candidate_v2_budget_context"] == "exhausted"
    assert out["source_class_recovery_candidate_v2_blocked_by_budget"] is True
    assert "budget_exhausted_with_source_class_underfire" in out[
        "source_class_recovery_candidate_v2_reasons"
    ]
    assert "budget_hard_exhausted" in out[
        "source_class_recovery_candidate_v2_blockers"
    ]
    assert "existing_active_recovery_blocked_by_budget" in out[
        "source_class_recovery_candidate_v2_blockers"
    ]


def test_candidate_v2_production_predicates_do_not_hardcode_named_topics() -> None:
    source = Path(__file__).parents[1] / "core" / "source_class_recovery.py"
    production_text = source.read_text(encoding="utf-8").casefold()

    for marker in (
        "real id",
        "real-id",
        "realid",
        "tsa",
        "dhs",
        "homeland security",
        "transportation security",
        "nhtsa",
        "cybertruck",
        "uk hereditary peers",
        "eu ai act",
        "gpai",
        "magna carta",
        "cnut",
        "wulfstan",
        "plague orders",
        "care court",
        "new york paid family leave",
        "washington pfml",
        "texas snap",
        "california care court",
        "paidfamilyleave.ny.gov",
        "washington paid family and medical leave",
    ):
        assert marker not in production_text
