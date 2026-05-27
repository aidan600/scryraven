from __future__ import annotations

from typing import Any

from core.answer_contract_controller import AnswerContractFamily
from core.answer_contract_runtime_handoff import (
    ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY,
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)


def _payload(facts: RuntimeAnswerContractFacts) -> tuple[AnswerContractFamily, dict[str, Any]]:
    result = build_runtime_answer_contract_handoff(facts)
    return (
        result.adapter_result.contract.family,
        result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY],
    )


def _secondary_only_status(*source_classes: str) -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            source_class: "expected_but_only_secondary"
            for source_class in source_classes
        }
    }


def test_ag10_legal_current_secondary_only_is_not_fully_fulfilled() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "What are the current federal rules for claiming a tax credit "
                "for installing an EV charger at home in 2026?"
            ),
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="federal EV charger tax credit rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry=_secondary_only_status(
                "legal_or_regulatory_text",
                "official_current_rules",
            ),
        )
    )

    assert family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert "identify relevant primary legal or regulatory text" not in payload["fulfilled_items"]
    assert "identify relevant primary legal or regulatory text" in payload["partial_items"]
    assert "legal_or_regulatory_text" in payload["unfulfilled_items"]
    assert "official_current_rules" in payload["unfulfilled_items"]
    assert "official/current legal evidence missing or secondary-only" in (
        payload["warnings_to_Analyst_or_Author"]
    )
    assert payload["final_answer_posture"] == "partial legal/regulatory explanation with caveat"


def test_ag10_legal_current_official_source_can_be_fulfilled() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "What are the current federal rules for claiming a tax credit "
                "for installing an EV charger at home in 2026?"
            ),
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="federal EV charger tax credit rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"official": 1, "secondary": 1},
        )
    )

    assert family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert "identify relevant primary legal or regulatory text" in payload["fulfilled_items"]
    assert payload["partial_items"] == []
    assert payload["unfulfilled_items"] == []
    assert payload["warnings_to_Analyst_or_Author"] == []


def test_ag10_recommendation_legal_constraint_preserves_family_but_caveats_gap() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "Which home EV charger should I buy if I want to stay eligible "
                "for a federal tax credit and still choose the best option?"
            ),
            intent="general",
            report_type="general_research",
            query_type="product",
            core_topic="home EV charger choice with tax-credit constraints",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["official_current_rules"],
            },
            fulfilled_obligations=(
                "identify decision criteria",
                "compare tradeoffs against user constraints",
                "verify federal tax credit eligibility",
            ),
        )
    )

    assert family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    assert "identify decision criteria" in payload["fulfilled_items"]
    assert "verify federal tax credit eligibility" not in payload["fulfilled_items"]
    assert "verify federal tax credit eligibility" in payload["partial_items"]
    assert "official_current_rules" in payload["unfulfilled_items"]
    assert payload["final_answer_posture"] == "qualified recommendation with evidence gaps"


def test_ag10_historical_archival_secondary_only_is_partial() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "What did the original U.S. leaded gasoline phase-down rules "
                "require, and how did the requirements change over time?"
            ),
            intent="historical",
            report_type="general_research",
            query_type="other",
            core_topic="original U.S. leaded gasoline phase-down rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
        )
    )

    assert family is AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER
    assert "use primary or archival material where appropriate" not in (
        payload["fulfilled_items"]
    )
    assert "use primary or archival material where appropriate" in payload["partial_items"]
    assert "primary_or_archival" in payload["unfulfilled_items"]
    assert "primary/archival source not found" in payload["warnings_to_Analyst_or_Author"]
    assert payload["final_answer_posture"] == "partial historical reconstruction with gaps"


def test_ag10_bread_calorie_density_negative_control_remains_fulfilled() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "A sandwich bread label says 90 calories per 35g, and an "
                "artisan loaf says 150 calories per 85g. Which is more "
                "calorie-dense?"
            ),
            intent="general",
            report_type="quantitative_comparison",
            query_type="comparison",
            core_topic="bread calorie density comparison",
            evidence_available=True,
            evidence_sufficient=True,
            fulfilled_obligations=(
                "identify variables and units",
                "state assumptions",
                "separate sourced values from calculations",
            ),
        )
    )

    assert family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    assert payload["fulfilled_items"] == [
        "identify variables and units",
        "state assumptions",
        "separate sourced values from calculations",
    ]
    assert payload["partial_items"] == []
    assert payload["unfulfilled_items"] == []
    assert "quantitative" in payload["final_answer_posture"]


def test_ag10_explicit_social_without_provider_stays_unfulfilled() -> None:
    family, payload = _payload(
        RuntimeAnswerContractFacts(
            query=(
                "What is Reddit or social media sentiment saying about Cursor's "
                "recent agent features?"
            ),
            intent="general",
            report_type="general_research",
            query_type="other",
            core_topic="Cursor agent feature social sentiment",
            evidence_available=True,
            evidence_sufficient=False,
            source_tier_counts={"secondary": 2},
        )
    )

    assert family is AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    assert payload["social_signal_summary"] == (
        "social_signal_relevance=central; status=provider_unavailable"
    )
    assert "social_signal" in payload["unfulfilled_items"]
    assert "provider_unavailable" in payload["warnings_to_Analyst_or_Author"][0]
