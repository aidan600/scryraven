from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.answer_contract_controller import AnswerContractFamily
from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    apply_answer_contract_source_class_recovery_gap_trigger,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_CLASS_RECOVERY_PATH = _ROOT / "core" / "source_class_recovery.py"


def _base_recommendation() -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": False,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [],
        "source_class_recovery_reason": None,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": [],
    }


def _recommendation_from_handoff(
    facts: RuntimeAnswerContractFacts,
) -> tuple[Any, dict[str, Any]]:
    result = build_runtime_answer_contract_handoff(facts)
    recommendation = apply_answer_contract_source_class_recovery_gap_trigger(
        recommendation=_base_recommendation(),
        answer_contract_family=result.adapter_result.contract.family.value,
        answer_contract_source_classes_missing=(
            result.state.evidence_state_summary.source_classes_missing
        ),
        answer_contract_unfulfilled_items=result.fulfillment_handoff.unfulfilled_items,
        answer_contract_partial_items=result.fulfillment_handoff.partial_items,
        query=facts.query,
        core_topic=facts.core_topic or "",
        primary_entity=facts.core_topic or "",
    )
    return result, recommendation


def _record_lifecycle(
    recommendation: dict[str, Any],
    *,
    current_search_depth: str = "basic",
    iteration_budget_available: bool = True,
    weak_corpus_recovery_considered: bool = False,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_skip_reason: str | None = None,
    answer_contract_source_class_slot_available: bool = False,
    controller: RunController | None = None,
) -> tuple[RunController, dict[str, Any]]:
    active_controller = controller or RunController()
    trace = record_source_class_recovery_lifecycle(
        active_controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "official_evidence_found": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth=current_search_depth,
        iteration_budget_available=iteration_budget_available,
        answer_contract_source_class_slot_available=(
            answer_contract_source_class_slot_available
        ),
    )
    return active_controller, trace


def test_ag11_official_current_gap_authorizes_one_existing_recovery_action() -> None:
    result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What are the current official rules for Care Program eligibility "
                "in 2026?"
            ),
            intent="general",
            report_type="general_research",
            query_type="other",
            core_topic="Care Program current official eligibility rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "source_class_satisfaction_status": {
                    "official_current_rules": "expected_but_only_secondary",
                }
            },
        )
    )

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.CURRENT_OFFICIAL_RULES
    )
    assert "official_current_rules" in result.fulfillment_handoff.unfulfilled_items
    assert recommendation["missing_expected_source_classes"] == [
        "official_current_rules"
    ]
    assert recommendation["source_class_recovery_reason"] == (
        "answer_contract_official_gap:official_current_rules"
    )

    controller, trace = _record_lifecycle(recommendation)

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_reason"] == (
        "answer_contract_official_gap:official_current_rules"
    )
    assert trace["active_source_class_recovery_missing_classes"] == [
        "official_current_rules"
    ]
    assert trace["active_source_class_recovery_attempt_count"] == 1
    assert len(controller.snapshot_ledger()["retrieval_actions"]) == 1


def test_ag11_legal_text_gap_authorizes_one_existing_recovery_action() -> None:
    result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What does the Public Offices Act say about membership rules "
                "and current statutory obligations?"
            ),
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="Public Offices Act membership rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "source_class_satisfaction_status": {
                    "legal_or_regulatory_text": "expected_but_only_secondary",
                }
            },
        )
    )

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    )
    assert "legal_or_regulatory_text" in result.fulfillment_handoff.unfulfilled_items
    assert "legal_or_regulatory_text" in recommendation[
        "missing_expected_source_classes"
    ]
    assert recommendation["source_class_recovery_reason"].startswith(
        "answer_contract_legal_text_gap:"
    )

    _controller, trace = _record_lifecycle(recommendation)

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_reason"].startswith(
        "answer_contract_legal_text_gap:"
    )
    assert trace["active_source_class_recovery_attempt_count"] == 1


def test_ag11_current_primary_gap_reuses_existing_provider_role_and_depth() -> None:
    result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "What is currently happening with the Commission high-risk AI "
                "guidelines, what is settled, and what remains uncertain?"
            ),
            intent="news",
            report_type="general_research",
            query_type="current_events",
            core_topic="Commission high-risk AI guidelines",
            evidence_available=True,
            evidence_sufficient=False,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": [
                    "current_primary_or_official",
                ]
            },
        )
    )

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION
    )
    assert "current_primary_or_official" in (
        result.fulfillment_handoff.unfulfilled_items
    )

    controller, trace = _record_lifecycle(
        recommendation,
        current_search_depth="advanced",
    )
    action = controller.snapshot_ledger()["retrieval_actions"][0]

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_reason"] == (
        "answer_contract_current_primary_gap:current_primary_or_official"
    )
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert trace["active_source_class_recovery_search_depth"] == "advanced"
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert action["search_depth"] == "advanced"
    assert action["metadata"]["controller_decision"] == "run_source_class_recovery"


def test_ag11_official_evidence_present_does_not_trigger_recovery() -> None:
    result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query="What are the current official rules for Care Program eligibility?",
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="Care Program current official eligibility rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"official": 1, "secondary": 1},
        )
    )

    assert result.fulfillment_handoff.unfulfilled_items == ()
    assert recommendation["source_class_recovery_recommended"] is False

    _controller, trace = _record_lifecycle(recommendation)

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_skip_reason"] == "not_recommended"


def test_ag11_conceptual_sufficient_evidence_does_not_trigger_recovery() -> None:
    result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query="Explain administrative law at a high level for a beginner.",
            intent="general",
            report_type="general_research",
            query_type="concept",
            core_topic="administrative law basics",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
        )
    )

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.CONCEPTUAL_EXPLAINER
    )
    assert recommendation["source_class_recovery_recommended"] is False


def test_ag11_recommendation_legal_constraint_does_not_hijack_recovery() -> None:
    result, recommendation = _recommendation_from_handoff(
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
        )
    )

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    )
    assert "official_current_rules" in result.fulfillment_handoff.unfulfilled_items
    assert recommendation["source_class_recovery_recommended"] is False


def test_ag11_existing_weak_corpus_ownership_blocks_answer_contract_trigger() -> None:
    _result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query="What are the current official rules for Care Program eligibility?",
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="Care Program current official eligibility rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["official_current_rules"],
            },
        )
    )

    _controller, trace = _record_lifecycle(
        recommendation,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
    )

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_skip_reason"] == (
        "blocked_by_weak_corpus_recovery"
    )


def test_ag11_retrieval_budget_exhaustion_blocks_answer_contract_trigger() -> None:
    _result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query="What are the current official rules for Care Program eligibility?",
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="Care Program current official eligibility rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["official_current_rules"],
            },
        )
    )

    _controller, trace = _record_lifecycle(
        recommendation,
        iteration_budget_available=False,
    )

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_skip_reason"] == (
        "blocked_by_iteration_budget"
    )


def test_ag11_source_class_recovery_attempt_is_not_duplicated() -> None:
    _result, recommendation = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query="What are the current official rules for Care Program eligibility?",
            intent="regulatory",
            report_type="general_research",
            query_type="other",
            core_topic="Care Program current official eligibility rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["official_current_rules"],
            },
        )
    )
    controller, first = _record_lifecycle(recommendation)
    _controller, second = _record_lifecycle(recommendation, controller=controller)

    assert first["active_source_class_recovery_eligible"] is True
    assert second["active_source_class_recovery_eligible"] is False
    assert second["active_source_class_recovery_skip_reason"] == "already_attempted"
    assert len(controller.snapshot_ledger()["retrieval_actions"]) == 1


def test_ag11_social_provider_unavailable_does_not_trigger_source_recovery() -> None:
    result, recommendation = _recommendation_from_handoff(
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

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    )
    assert "social_signal" in result.fulfillment_handoff.unfulfilled_items
    assert recommendation["source_class_recovery_recommended"] is False


def test_ag11_bread_calorie_density_quantitative_control_does_not_trigger() -> None:
    result, recommendation = _recommendation_from_handoff(
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

    assert result.adapter_result.contract.family is (
        AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    )
    assert recommendation["source_class_recovery_recommended"] is False


def test_ag11_helper_does_not_import_protected_runtime_surfaces() -> None:
    tree = ast.parse(_SOURCE_CLASS_RECOVERY_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.db",
        "sqlite3",
        "openai",
        "anthropic",
        "requests",
        "httpx",
    )
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]

    assert violations == []
