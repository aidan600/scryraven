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
from tests.active_gate_invariant_utils import (
    assert_active_gate_packet_invariants,
    assert_blocked_or_skipped,
    assert_passive_checkpoint_handoff_reference,
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

_TERMINAL_STOPS = {
    STOP_SUFFICIENT: ("terminal_stop_sufficient", "sufficient"),
    STOP_INSUFFICIENT_WITH_CAVEAT: (
        "terminal_stop_insufficient_with_caveat",
        "insufficient_with_caveat",
    ),
}

_UNPROMOTED_ACTIONS = [
    RETRIEVE_TARGETED,
    RECOVER_WEAK_CORPUS,
    ASK_USER_CLARIFICATION,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RUN_SCRUTINEER_REVIEW,
]


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _decision(action_name: str) -> EvidenceIntegrationDecision:
    boundary = (
        ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY
        if action_name in _TERMINAL_STOPS
        else ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY
    )
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag35_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag35 forced checkpoint decision for active gate invariant",
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


def _gate_packet(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]


def _provider_roles(harness: Any) -> list[str | None]:
    return [call["provider_role"] for call in harness.search_calls]


def test_ag35_checkpoint_recovery_is_the_only_executed_promoted_action(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_MISSING_SOURCE_CLASS,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved",
    )
    assert packet["terminal_stop_approved"] is False
    assert packet["executor_dispatch_blocked"] is False
    assert packet["executor_dispatched"] is True
    assert packet["blocked_or_skipped_actions"] == {
        RETRIEVE_TARGETED: "query_generation_required",
    }
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]


def test_ag35_lifecycle_blocker_remains_authoritative_for_recovery_checkpoint(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, mode="Fast", **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_MISSING_SOURCE_CLASS,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason="blocked_by_lifecycle",
    )
    assert_blocked_or_skipped(
        packet,
        RECOVER_MISSING_SOURCE_CLASS,
        "blocked_by_lifecycle",
    )
    assert packet["lifecycle_eligible"] is False
    assert packet["executor_dispatched"] is False
    assert outcome.execution_trace["active_source_class_recovery_used"] is False
    assert "blocked_by_iteration_budget" in packet["lifecycle_blockers"]
    assert _provider_roles(harness) == ["main_retrieval"]


@pytest.mark.parametrize("action_name", list(_TERMINAL_STOPS))
def test_ag35_terminal_stop_blocks_downstream_bounded_executor(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _gate_reason, final_answer_posture = _TERMINAL_STOPS[action_name]
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)

    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=action_name,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved_by_official_canonical_admission",
    )
    assert_blocked_or_skipped(
        packet,
        action_name,
        "authority_lifecycle_preserved_required_recovery",
    )
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == final_answer_posture
    assert packet["executor_dispatch_blocked"] is False
    assert packet["executor_dispatched"] is True
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert _provider_roles(harness) == ["main_retrieval", "source_class_recovery"]


@pytest.mark.parametrize("action_name", _UNPROMOTED_ACTIONS)
def test_ag35_unpromoted_checkpoint_actions_do_not_execute_substitutes(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)
    lifecycle_preserves_recovery = action_name == RECOVER_WEAK_CORPUS

    gate_reason = (
        "approved_by_official_canonical_admission"
        if lifecycle_preserves_recovery
        else (
        "query_generation_required"
        if action_name == RETRIEVE_TARGETED
        else "alternate_action_not_promoted"
        )
    )
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=action_name,
        promoted_action_name=(
            RECOVER_MISSING_SOURCE_CLASS if lifecycle_preserves_recovery else None
        ),
        executed_action_name=(
            RECOVER_MISSING_SOURCE_CLASS if lifecycle_preserves_recovery else None
        ),
        gate_reason=gate_reason,
    )
    if lifecycle_preserves_recovery:
        assert action_name not in packet["blocked_or_skipped_actions"]
    else:
        assert_blocked_or_skipped(packet, action_name, gate_reason)
    if not lifecycle_preserves_recovery:
        assert_blocked_or_skipped(
            packet,
            RECOVER_MISSING_SOURCE_CLASS,
            "checkpoint_action_not_approved",
        )
    assert packet["terminal_stop_approved"] is False
    assert packet["executor_dispatch_blocked"] is (not lifecycle_preserves_recovery)
    assert packet["executor_dispatched"] is lifecycle_preserves_recovery
    assert outcome.execution_trace["active_source_class_recovery_used"] is (
        lifecycle_preserves_recovery
    )
    assert outcome.execution_trace["weak_corpus_recovery_used"] is False
    assert outcome.execution_trace["scrutineer_ran"] is False
    assert harness.author_calls == 1
    assert _provider_roles(harness) == (
        ["main_retrieval", "source_class_recovery"]
        if lifecycle_preserves_recovery
        else ["main_retrieval"]
    )


def test_ag35_active_gate_runtime_change_does_not_leak_to_passive_handoff(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, STOP_SUFFICIENT)

    outcome, _harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    packet = _gate_packet(outcome.execution_trace)
    handoff_reference = outcome.execution_trace["answer_contract_fulfillment_handoff"][
        "evidence_integration_checkpoint"
    ]

    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=STOP_SUFFICIENT,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved_by_official_canonical_admission",
    )
    assert_passive_checkpoint_handoff_reference(
        handoff_reference,
        action_name=STOP_SUFFICIENT,
    )
