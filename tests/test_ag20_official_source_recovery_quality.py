from __future__ import annotations

from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.answer_contract_runtime_handoff import RuntimeAnswerContractFacts
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS, RECOVER_WEAK_CORPUS
from core.controller_state_reducer import ControllerEvidenceBoundary
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
    EvidenceIntegrationDecision,
    EvidenceIntegrationExpectedValue,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    apply_answer_contract_source_class_recovery_gap_trigger,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle
from tests.test_answer_contract_source_class_recovery_ag11 import (
    _base_recommendation,
    _recommendation_from_handoff,
)
from tests.test_source_class_recovery_trace import _run_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _query_text(trace: dict[str, Any]) -> str:
    return " ".join(trace["active_source_class_recovery_queries"]).casefold()


def _assert_existing_source_class_recovery_lane(
    trace: dict[str, Any],
    harness: Any,
    *,
    expected_depth: str = "basic",
) -> None:
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert trace["active_source_class_recovery_search_depth"] == expected_depth
    assert harness.search_calls[-1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[-1]["search_depth"] == expected_depth


def _checkpoint_decision(action_name: str) -> EvidenceIntegrationDecision:
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag20_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag20 forced checkpoint decision",
        blocked_or_skipped_action_rationale={},
        evidence_boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
    )


def _force_checkpoint_action(
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _checkpoint_decision(action_name),
    )


def test_ag20_dot_current_rules_queries_use_official_hints_and_recover_fixture(
    tmp_path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "As of today, what are the current U.S. DOT rules for airline "
            "passengers who use wheelchairs, including complaint rights and "
            "2026 enforcement milestones?"
        ),
        core_topic="DOT wheelchair airline passenger current rules",
        primary_entity="DOT wheelchair passenger rules",
        researcher_query="DOT wheelchair airline passenger rules news",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["news.example", "analysis.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["transportation.gov"],
    )

    trace = outcome.execution_trace
    _assert_existing_source_class_recovery_lane(trace, harness)
    queries = _query_text(trace)
    for term in (
        "official source",
        "federal register",
        "cfr",
        "ecfr",
        "govinfo",
        "transportation.gov",
        "14 cfr part 382",
    ):
        assert term in queries
    assert trace["recovery_source_quality_status"] == "official_or_primary_found"
    assert trace["recovered_official_or_primary_count"] >= 1


def test_ag20_ftc_legal_status_queries_use_court_and_federal_register_hints(
    tmp_path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "what would it have required, and what court or agency deadlines "
            "matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="FTC noncompete rule secondary analysis",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["federalregister.gov"],
    )

    trace = outcome.execution_trace
    _assert_existing_source_class_recovery_lane(trace, harness)
    queries = _query_text(trace)
    for term in ("ftc.gov", "federal register", "final rule", "court status"):
        assert term in queries
    assert trace["recovery_source_quality_status"] == "official_or_primary_found"


def test_ag20_fda_ldt_queries_use_enforcement_discretion_hints(tmp_path) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "What is the current FDA enforcement posture for laboratory "
            "developed tests after the LDT final rule, and what deadlines or "
            "phase-in milestones matter for labs?"
        ),
        core_topic="FDA LDT final rule enforcement posture",
        primary_entity="FDA laboratory developed tests",
        researcher_query="FDA LDT final rule secondary analysis",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["fda.gov"],
    )

    trace = outcome.execution_trace
    _assert_existing_source_class_recovery_lane(trace, harness)
    queries = _query_text(trace)
    for term in ("fda.gov", "federal register", "enforcement discretion"):
        assert term in queries
    assert trace["recovery_source_quality_status"] == "official_or_primary_found"


def test_ag20_legal_text_gap_queries_include_primary_legal_sources() -> None:
    recommendation = apply_answer_contract_source_class_recovery_gap_trigger(
        recommendation=_base_recommendation(),
        answer_contract_family="legal_or_regulatory_primary_text",
        answer_contract_source_classes_missing=("legal_or_regulatory_text",),
        query="What does the DOT rule text say about wheelchair complaint rights?",
        core_topic="DOT wheelchair complaint rights rule text",
        primary_entity="DOT wheelchair rule",
    )

    query_text = " ".join(
        recommendation["source_class_recovery_queries"]
    ).casefold()
    for term in ("cfr", "ecfr", "govinfo", "federal register"):
        assert term in query_text


def test_ag20_weak_corpus_current_legal_gap_checkpoint_preserves_authority_recovery(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_WEAK_CORPUS)

    outcome, harness = _run_weak_corpus_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "and what court or agency deadlines matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="current legal status court deadlines",
    )

    trace = outcome.execution_trace
    packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert trace["weak_corpus_recovery_used"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert trace["authority_lifecycle_required_recovery_allowed"] is True
    assert packet["checkpoint_action_name"] == RECOVER_WEAK_CORPUS
    assert packet["promoted_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["blocked_or_skipped_actions"][RECOVER_WEAK_CORPUS] == (
        "blocked_by_authority_lifecycle_required_recovery"
    )
    provider_roles = [detail["provider_role"] for detail in harness.search_call_details]
    assert "weak_corpus_recovery" in provider_roles
    assert "source_class_recovery" in provider_roles


def test_ag20_weak_corpus_current_legal_gap_checkpoint_source_class_skips_weak(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness = _run_weak_corpus_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "and what court or agency deadlines matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="current legal status court deadlines",
    )

    trace = outcome.execution_trace
    packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == (
        "checkpoint_action_not_approved"
    )
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_attempt_count"] == 1
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert packet["checkpoint_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["promoted_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["executed_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["blocked_or_skipped_actions"][RECOVER_WEAK_CORPUS] == (
        "checkpoint_action_not_approved"
    )
    assert harness.search_call_details[-1]["provider_role"] == (
        "source_class_recovery"
    )
    assert harness.search_call_details[-1]["search_depth"] == "basic"


def test_ag20_true_weak_corpus_without_official_legal_gap_stays_weak_owned(
    tmp_path,
) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path)

    trace = outcome.execution_trace
    assert trace["weak_corpus_recovery_used"] is True
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_attempt_count"] == 0
    assert all(
        detail["provider_role"] != "source_class_recovery"
        for detail in harness.search_call_details
    )


def test_ag20_weak_corpus_with_official_evidence_does_not_spend_exception() -> None:
    _result, recommendation = _recommendation_from_handoff(
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
    controller = RunController()
    trace = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"official": 1, "secondary": 1},
            "source_domain_counts": {"official.gov": 1},
            "top_source_domains": [{"domain": "official.gov", "count": 1}],
            "official_evidence_found": True,
        },
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_attempt_count"] == 0
    assert controller.snapshot_ledger()["retrieval_actions"] == []


def test_ag20_duplicate_source_class_attempt_remains_blocked() -> None:
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
    controller = RunController()
    first = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"official_evidence_found": False},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
        answer_contract_source_class_slot_available=True,
    )
    second = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"official_evidence_found": False},
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert first["active_source_class_recovery_eligible"] is True
    assert second["active_source_class_recovery_eligible"] is False
    assert second["active_source_class_recovery_skip_reason"] == "already_attempted"
    assert len(controller.snapshot_ledger()["retrieval_actions"]) == 1


def test_ag20_negative_controls_do_not_become_current_official_recovery() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query=(
            "What did OSHA's original hazard communication standard require "
            "when it was first issued, and how did the initial requirements work?"
        ),
        current_date="2026-05-22",
        intent="general",
        report_type="general_research",
        query_type="history",
        core_topic="original OSHA hazard communication standard history",
        primary_entity="OSHA hazard communication standard",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"history.example": 2},
        top_source_domains=[{"domain": "history.example", "count": 2}],
        official_evidence_found=False,
    )
    _result, recommendation_case = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "Which cookie-consent platform should a small SaaS company "
                "consider if it wants to reduce GDPR compliance risk?"
            ),
            intent="general",
            report_type="general_research",
            query_type="product",
            core_topic="cookie consent platform recommendation",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            source_class_recovery_telemetry={
                "missing_expected_source_classes": ["official_current_rules"],
            },
        )
    )
    _result, quantitative_case = _recommendation_from_handoff(
        RuntimeAnswerContractFacts(
            query=(
                "A snack has 140 calories per 28g, and another has "
                "210 calories per 55g. Which is more calorie-dense?"
            ),
            intent="general",
            report_type="quantitative_comparison",
            query_type="comparison",
            core_topic="snack calorie density comparison",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"secondary": 2},
            fulfilled_obligations=(
                "identify variables and units",
                "state assumptions",
                "separate sourced values from calculations",
            ),
        )
    )

    assert recommendation["source_class_recovery_recommended"] is False
    assert not str(
        recommendation_case.get("source_class_recovery_reason") or ""
    ).startswith("answer_contract_")
    assert quantitative_case["source_class_recovery_recommended"] is False
