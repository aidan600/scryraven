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


def test_ag6_recommendation_intent_beats_quantitative_comparison_metadata() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "For a developer choosing between Cursor and VS Code with GitHub Copilot "
            "in 2026, what are the practical tradeoffs, and what user-experience "
            "evidence would matter?"
        ),
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="Cursor versus VS Code with GitHub Copilot",
    )

    assert contract.family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    assert contract.social_signal_relevance is SocialSignalRelevance.RELEVANT_OPTIONAL
    assert "sourced_numeric_values" not in contract.evidence_classes_needed


def test_ag6_recommendation_with_numbers_stays_decision_support() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Which coding assistant should I choose for a two-person team if the "
            "budget is about $40 per user per month and latency matters?"
        ),
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="coding assistant subscription choice",
    )

    assert contract.family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    assert contract.social_signal_relevance is SocialSignalRelevance.RELEVANT_OPTIONAL
    assert "sourced_numeric_values" not in contract.evidence_classes_needed


def test_ag6_social_platform_adoption_beats_quantitative_comparison_metadata() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Is Bluesky overtaking X among journalists in 2026, and what evidence "
            "would actually be needed to answer that responsibly?"
        ),
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="Bluesky versus X among journalists",
    )

    assert contract.family is AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    assert contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
    assert contract.evidence_classes_needed == ("social_signal",)


def test_ag6_social_platform_numeric_near_miss_remains_quantitative() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Compare Bluesky and X monthly active user counts from published "
            "company or regulator figures."
        ),
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="Bluesky and X active user count comparison",
    )

    assert contract.family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    assert contract.social_signal_relevance is SocialSignalRelevance.IRRELEVANT
    assert "sourced_numeric_values" in contract.evidence_classes_needed


def test_ag6_historical_archival_intent_beats_comparison_metadata() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What did the original U.S. leaded gasoline phase-down rules require, "
            "and how did the requirements change over time?"
        ),
        intent="general",
        report_type="general_research",
        query_type="comparison",
        core_topic="original U.S. leaded gasoline phase-down rules",
    )

    assert contract.family is AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER
    assert "primary_or_archival" in contract.evidence_classes_needed
    assert "sourced_numeric_values" not in contract.evidence_classes_needed


def test_ag6_conceptual_history_context_near_miss_stays_conceptual() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "Give historical context for why TCP congestion control exists, "
            "but explain the concept at a high level."
        ),
        intent="general",
        report_type="general_research",
        query_type="concept",
        core_topic="TCP congestion control background",
    )

    assert contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER
    assert contract.social_signal_relevance is SocialSignalRelevance.IRRELEVANT
    assert contract.evidence_classes_needed == ("reputable_secondary",)


def test_ag6_current_legal_obligations_beat_comparison_metadata() -> None:
    eu_contract = draft_answer_contract_from_router_metadata(
        query=(
            "As of today, what are the current EU AI Act obligations and timeline "
            "for general-purpose AI model providers, and what changes or enforcement "
            "milestones matter in 2026?"
        ),
        intent="general",
        report_type="comparative_analysis",
        query_type="comparison",
        core_topic="EU AI Act general-purpose AI provider obligations",
    )
    ev_contract = draft_answer_contract_from_router_metadata(
        query=(
            "What are the current federal rules for claiming a tax credit for "
            "installing an EV charger at home in 2026, and what deadlines or limits matter?"
        ),
        intent="general",
        report_type="comparative_analysis",
        query_type="comparison",
        core_topic="federal EV charger tax credit rules",
    )

    for contract in (eu_contract, ev_contract):
        assert contract.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
        assert "legal_or_regulatory_text" in contract.evidence_classes_needed
        assert "official_current_rules" in contract.evidence_classes_needed
        assert "sourced_numeric_values" not in contract.evidence_classes_needed


def test_ag6_explicit_social_runtime_handoff_marks_provider_unavailable() -> None:
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What is Reddit or social media sentiment saying about Cursor's recent "
                "agent features, and how much should I trust that signal?"
            ),
            intent="general",
            report_type="quantitative_comparison",
            query_type="comparison",
            mode="Balanced",
            current_date="2026-05-21",
            core_topic="Cursor agent feature social sentiment",
            evidence_available=True,
            evidence_sufficient=False,
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


def test_ag6_quantitative_negative_control_remains_quantitative() -> None:
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
    assert contract.social_signal_relevance is SocialSignalRelevance.IRRELEVANT
    assert "sourced_numeric_values" in contract.evidence_classes_needed
