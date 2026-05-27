from __future__ import annotations

from core.answer_contract_controller import (
    AnswerContractFamily,
    SocialSignalRelevance,
    draft_answer_contract_from_router_metadata,
)
from core.answer_contract_runtime_handoff import (
    ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY,
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)


def test_ag8_eu_ai_act_obligations_with_news_router_maps_to_official_legal() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "As of today, what are the current EU AI Act obligations and timeline "
            "for general-purpose AI model providers, and what compliance or "
            "enforcement milestones matter in 2026?"
        ),
        intent="news",
        report_type="general_research",
        query_type="current_events",
        core_topic="EU AI Act general-purpose AI provider obligations",
    )

    assert contract.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert "legal_or_regulatory_text" in contract.evidence_classes_needed
    assert "official_current_rules" in contract.evidence_classes_needed


def test_ag8_ev_charger_tax_credit_with_news_router_maps_to_official_legal() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What are the current federal rules for claiming a tax credit for "
            "installing an EV charger at home in 2026, and what deadlines or "
            "eligibility limits matter?"
        ),
        intent="news",
        report_type="general_research",
        query_type="current_events",
        core_topic="federal EV charger tax credit rules",
    )

    assert contract.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert "legal_or_regulatory_text" in contract.evidence_classes_needed
    assert "official_current_rules" in contract.evidence_classes_needed


def test_ag8_unsettled_agency_guideline_status_can_stay_developing_but_surfaces_gap() -> None:
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What is currently happening with the European Commission's high-risk "
                "AI guidelines under the AI Act, what is settled, and what remains uncertain?"
            ),
            intent="news",
            report_type="general_research",
            query_type="current_events",
            mode="Balanced",
            current_date="2026-05-21",
            core_topic="European Commission high-risk AI guidelines",
            evidence_available=True,
            evidence_sufficient=False,
            source_tier_counts={"secondary": 2},
            final_top_evidence=(
                {
                    "source_id": 1,
                    "title": "Secondary AI Act guideline status report",
                    "url": "https://analysis.example/high-risk-ai-guidelines",
                    "source_tier": "secondary",
                },
            ),
            partial_obligations=("identify unsettled points",),
        )
    )
    payload = result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION
    )
    assert "current_primary_or_official" in payload["unfulfilled_items"]
    assert payload["evidence_used"][0]["source_class"] == "reputable_secondary"


def test_ag8_breaking_policy_news_story_remains_developing_event_orientation() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What is the breaking news story about the FTC announcement today, "
            "and what is still unsettled?"
        ),
        intent="news",
        report_type="general_research",
        query_type="current_events",
        core_topic="FTC announcement",
    )

    assert contract.family is AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION


def test_ag8_conceptual_law_explainer_remains_conceptual() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Explain the basic idea of administrative law at a high level for "
            "someone new to the topic."
        ),
        intent="general",
        report_type="general_research",
        query_type="concept",
        core_topic="administrative law basics",
    )

    assert contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER


def test_ag8_recommendation_with_legal_constraints_remains_decision_support() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Which home EV charger should I buy if I want to stay eligible for "
            "a federal tax credit and still choose the best option for my garage?"
        ),
        intent="general",
        report_type="general_research",
        query_type="product",
        core_topic="home EV charger choice with tax-credit constraints",
    )

    assert contract.family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    assert contract.social_signal_relevance is SocialSignalRelevance.RELEVANT_OPTIONAL


def test_ag8_bread_calorie_density_remains_quantitative() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "A sandwich bread label says 90 calories per 35g, and an artisan loaf "
            "says 150 calories per 85g. Which is more calorie-dense?"
        ),
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="bread calorie density comparison",
    )

    assert contract.family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL


def test_ag8_cursor_choice_remains_recommendation() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "For a developer choosing between Cursor and VS Code with GitHub Copilot "
            "in 2026, what are the practical tradeoffs?"
        ),
        intent="recommendation",
        report_type="general_research",
        query_type="product",
        core_topic="Cursor versus VS Code with GitHub Copilot",
    )

    assert contract.family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT


def test_ag8_social_provider_unavailable_behavior_remains_unchanged() -> None:
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What is Reddit or social media sentiment saying about Cursor's "
                "recent agent features?"
            ),
            intent="general",
            report_type="general_research",
            query_type="other",
            mode="Balanced",
            current_date="2026-05-21",
            core_topic="Cursor agent feature social sentiment",
            evidence_available=True,
            evidence_sufficient=False,
            source_tier_counts={"secondary": 2},
            unfulfilled_obligations=("social_signal",),
        )
    )
    payload = result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    )
    assert payload["social_signal_summary"] == (
        "social_signal_relevance=central; status=provider_unavailable"
    )
    assert "social_signal" in payload["unfulfilled_items"]
