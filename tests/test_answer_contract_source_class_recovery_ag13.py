from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.answer_contract_controller import AnswerContractFamily
from core.answer_contract_runtime_handoff import RuntimeAnswerContractFacts
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig
from tests.test_answer_contract_source_class_recovery_ag11 import (
    _recommendation_from_handoff,
    _record_lifecycle,
)
from tests.test_source_class_recovery_trace import (
    _execution_event_from_log,
    _TraceHarness,
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


class _BudgetExhaustionHarness(_TraceHarness):
    def __init__(self, *args: Any, second_iteration_query: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.second_iteration_query = second_iteration_query
        self.evaluator_calls = 0

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            self.evaluator_calls += 1
            return json.dumps(
                {
                    "is_sufficient": False,
                    "new_queries": [self.second_iteration_query],
                }
            )
        return super().ask_model(prompt, system_prompt, **kwargs)


def _run_budget_exhaustion_case(
    tmp_path: Path,
    *,
    second_iteration_query: str,
    mode: str = "Balanced",
    **harness_kwargs: Any,
) -> tuple[Any, _BudgetExhaustionHarness, dict[str, Any]]:
    harness = _BudgetExhaustionHarness(
        tmp_path,
        second_iteration_query=second_iteration_query,
        **harness_kwargs,
    )
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode=mode,
            current_date="2026-05-18",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    return outcome, harness, log_entry


def test_ag13_official_current_gap_uses_reserved_slot_after_main_budget(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_budget_exhaustion_case(
        tmp_path,
        query=(
            "What are the current official rules for Care Program eligibility "
            "in 2026?"
        ),
        core_topic="Care Program current official eligibility rules",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements secondary analysis",
        second_iteration_query="Care Program eligibility analysis deadlines",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["official.gov"],
    )

    trace = outcome.execution_trace

    assert trace["iterations_run"] == 2
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_reason"].startswith(
        "answer_contract_"
    )
    assert set(trace["active_source_class_recovery_missing_classes"]) & (
        {"official_current_rules", "legal_or_regulatory_text"}
    )
    assert "blocked_by_iteration_budget" not in trace[
        "active_source_class_recovery_blockers"
    ]
    assert trace["active_source_class_recovery_attempt_count"] == 1
    assert len(harness.search_calls) == 3
    assert harness.search_calls[2]["queries"] == trace[
        "active_source_class_recovery_queries"
    ]
    assert harness.search_calls[2]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[2]["search_providers"] == trace["pass_providers"][-1]
    assert harness.search_calls[2]["search_depth"] == trace[
        "active_source_class_recovery_search_depth"
    ]
    assert harness.search_calls[2]["search_depth"] == "basic"
    assert trace["provider_attempts_by_role"]["source_class_recovery"] == 1


def test_ag13_legal_text_gap_can_use_answer_contract_slot() -> None:
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

    _controller, trace = _record_lifecycle(
        recommendation,
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_reason"].startswith(
        "answer_contract_legal_text_gap:"
    )
    assert "legal_or_regulatory_text" in trace[
        "active_source_class_recovery_missing_classes"
    ]
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )


def test_ag13_developing_current_primary_gap_preserves_search_depth() -> None:
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

    _controller, trace = _record_lifecycle(
        recommendation,
        current_search_depth="advanced",
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_reason"] == (
        "answer_contract_current_primary_gap:current_primary_or_official"
    )
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert trace["active_source_class_recovery_search_depth"] == "advanced"


def test_ag13_duplicate_attempt_still_blocks_reserved_slot() -> None:
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
    controller, first = _record_lifecycle(
        recommendation,
        answer_contract_source_class_slot_available=True,
    )
    _controller, second = _record_lifecycle(
        recommendation,
        controller=controller,
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert first["active_source_class_recovery_eligible"] is True
    assert second["active_source_class_recovery_eligible"] is False
    assert second["active_source_class_recovery_skip_reason"] == "already_attempted"
    assert len(controller.snapshot_ledger()["retrieval_actions"]) == 1


def test_ag20_weak_corpus_official_gap_can_use_reserved_slot_once() -> None:
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
        answer_contract_source_class_slot_available=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_attempt_count"] == 1
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )


def test_ag13_iteration_budget_still_blocks_when_no_reserved_slot() -> None:
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
        answer_contract_source_class_slot_available=False,
    )

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_skip_reason"] == (
        "blocked_by_iteration_budget"
    )


@pytest.mark.parametrize(
    "facts",
    [
        RuntimeAnswerContractFacts(
            query="Explain administrative law at a high level for a beginner.",
            intent="general",
            report_type="general_research",
            query_type="concept",
            core_topic="administrative law basics",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
        ),
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
        ),
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
        ),
        RuntimeAnswerContractFacts(
            query=(
                "What did the original U.S. leaded gasoline phase-down rules "
                "require, and how did those requirements change over time?"
            ),
            intent="general",
            report_type="general_research",
            query_type="history",
            core_topic="original U.S. leaded gasoline phase-down rules",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["archival_primary_text"],
            },
        ),
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
        ),
    ],
)
def test_ag13_negative_controls_do_not_use_official_current_pilot(
    facts: RuntimeAnswerContractFacts,
) -> None:
    _result, recommendation = _recommendation_from_handoff(facts)
    reason = recommendation.get("source_class_recovery_reason")

    assert not str(reason or "").startswith("answer_contract_")
