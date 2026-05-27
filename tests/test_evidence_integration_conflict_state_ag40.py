from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.conflict_state_producer import (
    ConflictStateProducerInput,
    build_conflict_state,
)
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RESOLVE_CONFLICT,
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
from tests.test_source_class_recovery_trace import _run_case

_CARE_CASE = {
    "query": (
        "What are the current eligibility requirements and official rules for "
        "the Care Program?"
    ),
    "core_topic": "Care Program current eligibility requirements",
    "primary_entity": "Care Program",
    "researcher_query": "Care Program eligibility requirements",
    "router_query_type": "other",
    "source_tiers": ["official", "secondary"],
    "domains": ["official.gov", "analysis.example"],
    "source_texts": [
        (
            "The Care Program current official rule effective date is May 1, "
            "2026. Eligibility requirements apply to current applicants."
        ),
        (
            "The Care Program reputable secondary summary says the current "
            "rule effective date is June 1, 2026."
        ),
    ],
}


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _decision(action_name: str) -> EvidenceIntegrationDecision:
    boundary = (
        ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY
        if action_name == STOP_SUFFICIENT
        else ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY
    )
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag40_forced_{action_name}",
        contract_gap_addressed=(
            "conflicting evidence"
            if action_name == RESOLVE_CONFLICT
            else "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag40 forced checkpoint decision",
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


def _fixture_conflict_state():
    final_top_evidence = [
        {
            "source_id": idx + 1,
            "text": text,
            "source_tier": _CARE_CASE["source_tiers"][idx],
            "url": f"https://{_CARE_CASE['domains'][idx]}/fixture",
        }
        for idx, text in enumerate(_CARE_CASE["source_texts"])
    ]
    return build_conflict_state(
        ConflictStateProducerInput(
            query=_CARE_CASE["query"],
            core_topic=_CARE_CASE["core_topic"],
            primary_entity=_CARE_CASE["primary_entity"],
            current_date="2026-05-18",
            final_top_evidence=final_top_evidence,
            source_tier_counts={"official": 1, "secondary": 1},
        )
    )


def test_ag40_normal_runtime_surfaces_conflict_facts_without_handoff_monkeypatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_considered"] is True
    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is True
    assert trace["active_conflict_resolution_conflict_notes"]
    assert trace["active_conflict_resolution_queries"] == [
        (
            "Care Program official current effective date "
            "May 1, 2026 June 1, 2026"
        ),
        "Care Program regulator filing current effective date",
    ]
    assert _provider_roles(harness) == ["main_retrieval", "conflict_resolution"]
    assert packet["snapshot"]["conflicts"]["present"] is True
    assert packet["snapshot"]["conflicts"]["resolution_available"] is True
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=RESOLVE_CONFLICT,
        executed_action_name=RESOLVE_CONFLICT,
        gate_reason="approved",
    )


def test_ag40_natural_checkpoint_selects_and_executes_conflict_resolution(
    tmp_path: Path,
) -> None:
    conflict_state = _fixture_conflict_state()
    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert conflict_state.conflicts_present is True
    assert conflict_state.centrality_to_contract == "central"
    assert conflict_state.safe_to_dispatch_resolve_conflict is True
    assert conflict_state.conflict_notes
    assert conflict_state.resolving_query_candidates
    assert trace["active_conflict_resolution_considered"] is True
    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is True
    assert trace["active_conflict_resolution_conflict_notes"]
    assert trace["active_conflict_resolution_queries"] == [
        (
            "Care Program official current effective date "
            "May 1, 2026 June 1, 2026"
        ),
        "Care Program regulator filing current effective date",
    ]
    assert _provider_roles(harness).count("conflict_resolution") == 1
    assert packet["snapshot"]["conflicts"]["present"] is True
    assert packet["snapshot"]["conflicts"]["resolution_available"] is True
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=RESOLVE_CONFLICT,
        executed_action_name=RESOLVE_CONFLICT,
        gate_reason="approved",
    )


def test_ag40_dispatches_conflict_resolution_exactly_once_for_central_queryable_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace

    assert trace["active_conflict_resolution_attempt_count"] == 1
    assert _provider_roles(harness).count("conflict_resolution") == 1


def test_ag40_terminal_stop_still_beats_normal_conflict_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, STOP_SUFFICIENT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is False
    assert "conflict_resolution" not in _provider_roles(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=STOP_SUFFICIENT,
        promoted_action_name=STOP_SUFFICIENT,
        executed_action_name=None,
        gate_reason="terminal_stop_sufficient",
    )
    assert_blocked_or_skipped(packet, RESOLVE_CONFLICT, "blocked_by_terminal_stop")


def test_ag40_source_class_checkpoint_still_beats_normal_conflict_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is False
    assert "conflict_resolution" not in _provider_roles(harness)
    assert packet["checkpoint_action_name"] == RECOVER_MISSING_SOURCE_CLASS
    assert_blocked_or_skipped(
        packet,
        RESOLVE_CONFLICT,
        "checkpoint_action_not_approved",
    )
