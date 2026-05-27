from __future__ import annotations

from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    ASK_USER_CLARIFICATION,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)
from core.controller_state_reducer import ControllerEvidenceBoundary
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
    EvidenceIntegrationDecision,
    EvidenceIntegrationExpectedValue,
)
from tests.test_source_class_recovery_trace import _run_case

_CARE_CASE = {
    "query": (
        "What are the current eligibility requirements and official rules for "
        "the care program?"
    ),
    "core_topic": "care program current eligibility requirements",
    "primary_entity": "Care Program",
    "researcher_query": "Care Program eligibility requirements",
    "router_query_type": "other",
}

_BOUNDED_EXECUTOR_TYPES = [
    "source_class_recovery",
    "targeted_retrieval",
    "weak_corpus_recovery",
    "conflict_resolution",
]


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _decision(action_name: str) -> EvidenceIntegrationDecision:
    boundary = (
        ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY
        if action_name in {STOP_INSUFFICIENT_WITH_CAVEAT, STOP_SUFFICIENT}
        else ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY
    )
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag34_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag34 forced checkpoint decision for stop gate test",
        blocked_or_skipped_action_rationale={},
        evidence_boundary=boundary,
    )


def _force_checkpoint_action(
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(action_name),
    )


def _provider_roles(harness: Any) -> list[str | None]:
    return [call["provider_role"] for call in harness.search_calls]


def _gate_packet(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]


def test_ag34_stop_insufficient_blocks_bounded_executors_and_sets_posture(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, STOP_INSUFFICIENT_WITH_CAVEAT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]
    assert packet["controller_stop_gate_active"] is True
    assert packet["checkpoint_action_name"] == STOP_INSUFFICIENT_WITH_CAVEAT
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == "insufficient_with_caveat"
    assert packet["executor_dispatch_blocked"] is False
    assert packet["blocked_executor_types"] == []
    assert packet["runtime_behavior_changed"] is True
    assert packet["gate_reason"] == "approved_by_official_canonical_admission"
    assert packet["executor_dispatched"] is True
    assert packet["blocked_or_skipped_actions"][STOP_INSUFFICIENT_WITH_CAVEAT] == (
        "authority_lifecycle_preserved_required_recovery"
    )


def test_ag34_stop_sufficient_blocks_bounded_executors_and_sets_posture(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, STOP_SUFFICIENT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]
    assert packet["controller_stop_gate_active"] is True
    assert packet["checkpoint_action_name"] == STOP_SUFFICIENT
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == "sufficient"
    assert packet["executor_dispatch_blocked"] is False
    assert packet["blocked_executor_types"] == []
    assert packet["gate_reason"] == "approved_by_official_canonical_admission"
    assert packet["executor_dispatched"] is True
    assert packet["blocked_or_skipped_actions"][STOP_SUFFICIENT] == (
        "authority_lifecycle_preserved_required_recovery"
    )


def test_ag34_recover_missing_source_class_preserves_ag33_dispatch(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]
    assert packet["terminal_stop_approved"] is False
    assert packet["final_answer_posture"] == "existing_posture"
    assert packet["executor_dispatch_blocked"] is False
    assert packet["executor_dispatched"] is True
    assert packet["gate_reason"] == "approved"


def test_ag34_recover_missing_source_class_preserves_lifecycle_blocker(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, mode="Fast", **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is False
    assert outcome.execution_trace["active_source_class_recovery_used"] is False
    assert "blocked_by_iteration_budget" in outcome.execution_trace[
        "active_source_class_recovery_blockers"
    ]
    assert _provider_roles(harness) == ["main_retrieval"]
    assert packet["terminal_stop_approved"] is False
    assert packet["executor_dispatched"] is False
    assert packet["gate_reason"] == "blocked_by_lifecycle"


@pytest.mark.parametrize(
    "action_name",
    [
        RETRIEVE_TARGETED,
        RECOVER_WEAK_CORPUS,
        REQUEST_SOCIAL_SIGNAL_CHECK,
        RUN_SCRUTINEER_REVIEW,
        ASK_USER_CLARIFICATION,
    ],
)
def test_ag34_unpromoted_non_stop_actions_do_not_dispatch_substitutes(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)
    lifecycle_preserves_recovery = action_name == RECOVER_WEAK_CORPUS

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is (
        lifecycle_preserves_recovery
    )
    assert _provider_roles(harness) == (
        ["main_retrieval", "source_class_recovery"]
        if lifecycle_preserves_recovery
        else ["main_retrieval"]
    )
    assert packet["controller_stop_gate_active"] is True
    assert packet["checkpoint_action_name"] == action_name
    assert packet["terminal_stop_approved"] is False
    assert packet["final_answer_posture"] == "existing_posture"
    assert packet["executor_dispatch_blocked"] is (not lifecycle_preserves_recovery)
    expected_blocked_executor_types = (
        []
        if lifecycle_preserves_recovery
        else (
        ["targeted_retrieval"]
        if action_name == RETRIEVE_TARGETED
        else _BOUNDED_EXECUTOR_TYPES
        )
    )
    assert packet["blocked_executor_types"] == expected_blocked_executor_types
    assert packet["executor_dispatched"] is lifecycle_preserves_recovery
    expected_gate_reason = (
        "approved_by_official_canonical_admission"
        if lifecycle_preserves_recovery
        else (
        "query_generation_required"
        if action_name == RETRIEVE_TARGETED
        else "alternate_action_not_promoted"
        )
    )
    assert packet["gate_reason"] == expected_gate_reason
