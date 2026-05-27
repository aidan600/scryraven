from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
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
)
from tests.test_weak_corpus_recovery import _run

_TERMINAL_STOPS = {
    STOP_SUFFICIENT: ("terminal_stop_sufficient", "sufficient"),
    STOP_INSUFFICIENT_WITH_CAVEAT: (
        "terminal_stop_insufficient_with_caveat",
        "insufficient_with_caveat",
    ),
}


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
        reason=f"ag36_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag36 forced checkpoint decision for weak-corpus gate",
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
    return [call["provider_role"] for call in harness.search_call_details]


def test_ag36_recover_weak_corpus_checkpoint_dispatches_existing_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_WEAK_CORPUS)

    outcome, harness = _run(tmp_path)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["weak_corpus_recovery_used"] is True
    assert trace["weak_corpus_recovery_skip_reason"] is None
    assert _provider_roles(harness)[-1] == "weak_corpus_recovery"
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_WEAK_CORPUS,
        promoted_action_name=RECOVER_WEAK_CORPUS,
        executed_action_name=RECOVER_WEAK_CORPUS,
        gate_reason="approved",
    )
    assert packet["weak_corpus_gate_active"] is True
    assert packet["weak_corpus_lifecycle_eligible"] is True
    assert packet["weak_corpus_executor_dispatched"] is True
    assert packet["runtime_behavior_changed"] is True


@pytest.mark.parametrize("action_name", list(_TERMINAL_STOPS))
def test_ag36_terminal_stop_blocks_eligible_weak_corpus_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    gate_reason, final_answer_posture = _TERMINAL_STOPS[action_name]
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness = _run(tmp_path)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == "blocked_by_terminal_stop"
    assert "weak_corpus_recovery" not in _provider_roles(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=action_name,
        promoted_action_name=action_name,
        executed_action_name=None,
        gate_reason=gate_reason,
    )
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == final_answer_posture
    assert_blocked_or_skipped(
        packet,
        RECOVER_WEAK_CORPUS,
        "blocked_by_terminal_stop",
    )


def test_ag36_recover_missing_source_class_blocks_weak_and_preserves_ag33(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness = _run(
        tmp_path,
        query="What are the current official rules and requirements for Acme Widget?",
        core_topic="Acme Widget current official rules requirements",
        primary_entity="Acme Widget",
        researcher_query="current official rules requirements",
    )
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == (
        "checkpoint_action_not_approved"
    )
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert "source_class_recovery" in _provider_roles(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_MISSING_SOURCE_CLASS,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved",
    )
    assert_blocked_or_skipped(
        packet,
        RECOVER_WEAK_CORPUS,
        "checkpoint_action_not_approved",
    )


@pytest.mark.parametrize(
    "action_name",
    [
        RETRIEVE_TARGETED,
        REQUEST_SOCIAL_SIGNAL_CHECK,
        RUN_SCRUTINEER_REVIEW,
    ],
)
def test_ag36_unpromoted_checkpoint_actions_do_not_dispatch_substitutes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness = _run(tmp_path)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)
    roles = _provider_roles(harness)

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == (
        "checkpoint_action_not_approved"
    )
    assert "weak_corpus_recovery" not in roles
    assert "source_class_recovery" not in roles
    assert trace["scrutineer_ran"] is False
    assert len(harness.search_calls) == 2
    gate_reason = (
        "query_generation_required"
        if action_name == RETRIEVE_TARGETED
        else "alternate_action_not_promoted"
    )
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=action_name,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason=gate_reason,
    )
    assert_blocked_or_skipped(
        packet,
        RECOVER_WEAK_CORPUS,
        "checkpoint_action_not_approved",
    )


def test_ag36_weak_corpus_lifecycle_blocker_wins_over_recovery_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_WEAK_CORPUS)

    outcome, harness = _run(tmp_path, mode="Fast")
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == "max_iterations_1"
    assert "max_iterations_1" in trace["weak_corpus_recovery_blockers"]
    assert _provider_roles(harness) == ["main_retrieval", "disambiguation_retry"]
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_WEAK_CORPUS,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason="max_iterations_1",
    )
    assert packet["weak_corpus_lifecycle_eligible"] is False
    assert_blocked_or_skipped(packet, RECOVER_WEAK_CORPUS, "max_iterations_1")
