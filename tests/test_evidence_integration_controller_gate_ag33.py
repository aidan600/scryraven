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
    "query": "What are the current eligibility requirements and official rules for the care program?",
    "core_topic": "care program current eligibility requirements",
    "primary_entity": "Care Program",
    "researcher_query": "Care Program eligibility requirements",
    "router_query_type": "other",
}


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _decision(action_name: str) -> EvidenceIntegrationDecision:
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag33_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag33 forced checkpoint decision for runtime gate test",
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
        lambda _snapshot: _decision(action_name),
    )


def _provider_roles(harness: Any) -> list[str | None]:
    return [call["provider_role"] for call in harness.search_calls]


def _gate_packet(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]


def _expected_gate_reason(action_name: str) -> str:
    if action_name == STOP_SUFFICIENT:
        return "terminal_stop_sufficient"
    if action_name == STOP_INSUFFICIENT_WITH_CAVEAT:
        return "terminal_stop_insufficient_with_caveat"
    return "alternate_action_not_promoted"


def test_ag33_eligible_checkpoint_recovery_dispatches_executor_as_before(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]
    assert packet["controller_gate_active"] is True
    assert packet["gated_action"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["checkpoint_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["lifecycle_eligible"] is True
    assert packet["executor_dispatched"] is True
    assert packet["runtime_behavior_changed"] is True
    assert packet["shadow_mode"] is False


@pytest.mark.parametrize(
    "action_name",
    [
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        RETRIEVE_TARGETED,
        RECOVER_WEAK_CORPUS,
        ASK_USER_CLARIFICATION,
        REQUEST_SOCIAL_SIGNAL_CHECK,
        RUN_SCRUTINEER_REVIEW,
    ],
)
def test_ag33_eligible_checkpoint_non_recovery_blocks_source_class_executor(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)
    lifecycle_preserves_recovery = action_name in {
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        RECOVER_WEAK_CORPUS,
    }

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]
    assert packet["controller_gate_active"] is True
    expected_gated_action = (
        RETRIEVE_TARGETED
        if action_name == RETRIEVE_TARGETED and not lifecycle_preserves_recovery
        else RECOVER_MISSING_SOURCE_CLASS
    )
    assert packet["gated_action"] == expected_gated_action
    assert packet["checkpoint_action_name"] == action_name
    assert packet["lifecycle_eligible"] is (action_name != RETRIEVE_TARGETED)
    assert packet["executor_dispatched"] is lifecycle_preserves_recovery
    expected_gate_reason = (
        "approved_by_official_canonical_admission"
        if lifecycle_preserves_recovery
        else (
        "query_generation_required"
        if action_name == RETRIEVE_TARGETED
        else _expected_gate_reason(action_name)
        )
    )
    assert packet["gate_reason"] == expected_gate_reason
    if action_name in {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}:
        assert packet["blocked_or_skipped_actions"][action_name] == (
            "authority_lifecycle_preserved_required_recovery"
        )
    elif action_name == RECOVER_WEAK_CORPUS:
        assert RECOVER_WEAK_CORPUS not in packet["blocked_or_skipped_actions"]
    assert packet["runtime_behavior_changed"] is True


def test_ag33_lifecycle_blocker_wins_over_recovery_checkpoint(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(
        tmp_path,
        mode="Fast",
        **_CARE_CASE,
    )
    packet = _gate_packet(outcome.execution_trace)

    assert outcome.execution_trace["active_source_class_recovery_eligible"] is False
    assert outcome.execution_trace["active_source_class_recovery_used"] is False
    assert "blocked_by_iteration_budget" in outcome.execution_trace[
        "active_source_class_recovery_blockers"
    ]
    assert _provider_roles(harness) == ["main_retrieval"]
    assert packet["controller_gate_active"] is True
    assert packet["checkpoint_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["lifecycle_eligible"] is False
    assert packet["executor_dispatched"] is False
    assert packet["gate_reason"] == "blocked_by_lifecycle"
