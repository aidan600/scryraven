from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
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
from tests.test_source_class_recovery_trace import _run_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus

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

_CONFLICT_NOTES = ("official date conflicts with secondary report date",)
_RESOLVING_QUERIES = (
    "Care Program official current eligibility corrected date",
    "Care Program regulator eligibility filing current date",
)
_ORDINARY_NEXT_QUERIES = ("Care Program ordinary eligibility background",)
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
        reason=f"ag37b_forced_{action_name}",
        contract_gap_addressed=(
            "conflicting evidence"
            if action_name == RESOLVE_CONFLICT
            else "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag37b forced checkpoint decision",
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


def _inject_conflict_evidence_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    conflicts_present: bool = True,
    conflict_notes: tuple[str, ...] = _CONFLICT_NOTES,
    resolving_queries: tuple[str, ...] = _RESOLVING_QUERIES,
    ordinary_next_queries: tuple[str, ...] = (),
    prior_attempt_count: int = 0,
) -> None:
    original = orchestrator.build_runtime_answer_contract_handoff

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        state = result.adapter_result.state
        updated_summary = replace(
            state.evidence_state_summary,
            conflicts_present=conflicts_present,
            conflict_notes=conflict_notes,
            resolving_queries=resolving_queries,
            next_queries=ordinary_next_queries,
        )
        state.evidence_state_summary = updated_summary
        if prior_attempt_count:
            state.recovery_attempts["resolve_conflict"] = prior_attempt_count
        return replace(
            result,
            adapter_result=replace(
                result.adapter_result,
                evidence_state_summary=updated_summary,
            ),
        )

    monkeypatch.setattr(orchestrator, "build_runtime_answer_contract_handoff", wrapped)


def _force_conflict_policy(
    monkeypatch: pytest.MonkeyPatch,
    **policy_overrides: Any,
) -> None:
    original = orchestrator._build_conflict_resolution_lifecycle_from_runtime_answer_contract

    def wrapped(**kwargs: Any) -> Any:
        kwargs.update(policy_overrides)
        return original(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "_build_conflict_resolution_lifecycle_from_runtime_answer_contract",
        wrapped,
    )


def _gate_packet(trace: dict[str, Any]) -> dict[str, Any]:
    return trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]


def _provider_roles_from_source_harness(harness: Any) -> list[str | None]:
    return [call["provider_role"] for call in harness.search_calls]


def _provider_roles_from_weak_harness(harness: Any) -> list[str | None]:
    return [call["provider_role"] for call in harness.search_call_details]


def test_ag37b_normal_runtime_lacks_conflict_fact_producer_and_blocks_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_considered"] is False
    assert trace["active_conflict_resolution_eligible"] is False
    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_conflict_resolution_skip_reason"] == "no_conflict"
    assert trace["active_conflict_resolution_queries"] == []
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason="no_conflict",
    )
    assert packet["conflict_resolution_executor_dispatched"] is False
    assert_blocked_or_skipped(packet, RESOLVE_CONFLICT, "no_conflict")


def test_ag37b_disabled_runtime_handoff_fails_closed_without_conflict_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DisabledHandoff:
        def execution_trace_fragment(self) -> dict[str, Any]:
            return {}

    def disabled_handoff(*_args: Any, **_kwargs: Any) -> _DisabledHandoff:
        return _DisabledHandoff()

    monkeypatch.setattr(
        orchestrator,
        "build_runtime_answer_contract_handoff",
        disabled_handoff,
    )
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_conflict_resolution_skip_reason"] == "not_evaluated"
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert packet["available"] is False
    assert packet["checkpoint_action_name"] is None
    assert packet["promoted_action_name"] is None
    assert packet["executed_action_name"] is None
    assert packet["gate_reason"] == "checkpoint_unavailable"
    assert packet["conflict_resolution_executor_dispatched"] is False


def test_ag37b_resolve_conflict_checkpoint_dispatches_one_conflict_executor_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(monkeypatch)
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_used"] is True
    assert trace["active_conflict_resolution_queries"] == list(_RESOLVING_QUERIES)
    assert trace["active_conflict_resolution_provider_role"] == "conflict_resolution"
    assert trace["active_conflict_resolution_search_depth"] == "basic"
    assert trace["active_source_class_recovery_used"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert _provider_roles_from_source_harness(harness) == [
        "main_retrieval",
        "conflict_resolution",
    ]
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=RESOLVE_CONFLICT,
        executed_action_name=RESOLVE_CONFLICT,
        gate_reason="approved",
    )
    assert packet["conflict_resolution_executor_dispatched"] is True
    assert packet["executor_dispatched"] is True


def test_ag37b_non_conflict_checkpoint_does_not_dispatch_conflict_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(monkeypatch)
    _force_checkpoint_action(monkeypatch, RETRIEVE_TARGETED)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_used"] is False
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RETRIEVE_TARGETED,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason="query_generation_required",
    )
    assert packet["conflict_resolution_executor_dispatched"] is False
    assert_blocked_or_skipped(
        packet,
        RETRIEVE_TARGETED,
        "query_generation_required",
    )
    assert_blocked_or_skipped(
        packet,
        RESOLVE_CONFLICT,
        "checkpoint_action_not_approved",
    )


@pytest.mark.parametrize(
    ("name", "inject_overrides", "run_mode", "policy_overrides", "reason"),
    [
        (
            "no_resolving_queries",
            {"resolving_queries": ()},
            "Balanced",
            {},
            "no_resolving_queries",
        ),
        (
            "already_attempted",
            {"prior_attempt_count": 1},
            "Balanced",
            {},
            "already_attempted",
        ),
        (
            "no_iteration_budget",
            {},
            "Fast",
            {},
            "blocked_by_iteration_budget",
        ),
        (
            "provider_policy_change_required",
            {},
            "Balanced",
            {"provider_policy_reusable": False},
            "blocked_by_provider_policy_change_required",
        ),
        (
            "search_depth_change_required",
            {},
            "Balanced",
            {"search_depth_reusable": False},
            "blocked_by_search_depth_policy_change_required",
        ),
    ],
)
def test_ag37b_conflict_lifecycle_blockers_remain_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    inject_overrides: dict[str, Any],
    run_mode: str,
    policy_overrides: dict[str, Any],
    reason: str,
) -> None:
    _inject_conflict_evidence_state(monkeypatch, **inject_overrides)
    if policy_overrides:
        _force_conflict_policy(monkeypatch, **policy_overrides)
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path / name, mode=run_mode, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_conflict_resolution_skip_reason"] == reason
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason=reason,
    )
    assert packet["conflict_resolution_lifecycle_eligible"] is False
    assert_blocked_or_skipped(packet, RESOLVE_CONFLICT, reason)


@pytest.mark.parametrize("action_name", list(_TERMINAL_STOPS))
def test_ag37b_terminal_stop_blocks_eligible_conflict_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    _gate_reason, final_answer_posture = _TERMINAL_STOPS[action_name]
    _inject_conflict_evidence_state(monkeypatch)
    _force_checkpoint_action(monkeypatch, action_name)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_source_class_recovery_used"] is True
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=action_name,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved_by_official_canonical_admission",
    )
    assert packet["terminal_stop_approved"] is True
    assert packet["final_answer_posture"] == final_answer_posture
    assert_blocked_or_skipped(
        packet,
        action_name,
        "authority_lifecycle_preserved_required_recovery",
    )
    assert_blocked_or_skipped(
        packet,
        RESOLVE_CONFLICT,
        "blocked_by_authority_lifecycle_required_recovery",
    )


def test_ag37b_source_class_checkpoint_blocks_conflict_and_runs_only_source_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(monkeypatch)
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)
    roles = _provider_roles_from_source_harness(harness)

    assert trace["active_conflict_resolution_eligible"] is True
    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_source_class_recovery_used"] is True
    assert roles == ["main_retrieval", "source_class_recovery"]
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_MISSING_SOURCE_CLASS,
        promoted_action_name=RECOVER_MISSING_SOURCE_CLASS,
        executed_action_name=RECOVER_MISSING_SOURCE_CLASS,
        gate_reason="approved",
    )
    assert_blocked_or_skipped(
        packet,
        RESOLVE_CONFLICT,
        "checkpoint_action_not_approved",
    )


def test_ag37b_weak_corpus_checkpoint_blocks_conflict_and_runs_only_weak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(monkeypatch)
    _force_checkpoint_action(monkeypatch, RECOVER_WEAK_CORPUS)

    outcome, harness = _run_weak_corpus(tmp_path)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)
    roles = _provider_roles_from_weak_harness(harness)

    assert trace["active_conflict_resolution_used"] is False
    assert trace["weak_corpus_recovery_used"] is True
    assert "weak_corpus_recovery" in roles
    assert "conflict_resolution" not in roles
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RECOVER_WEAK_CORPUS,
        promoted_action_name=RECOVER_WEAK_CORPUS,
        executed_action_name=RECOVER_WEAK_CORPUS,
        gate_reason="approved",
    )
    assert_blocked_or_skipped(
        packet,
        RESOLVE_CONFLICT,
        "checkpoint_action_not_approved",
    )


def test_ag37b_ordinary_next_queries_do_not_become_conflict_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(
        monkeypatch,
        resolving_queries=(),
        ordinary_next_queries=_ORDINARY_NEXT_QUERIES,
    )
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)

    outcome, harness, _log_entry = _run_case(tmp_path, **_CARE_CASE)
    trace = outcome.execution_trace
    packet = _gate_packet(trace)

    assert trace["active_conflict_resolution_used"] is False
    assert trace["active_conflict_resolution_queries"] == []
    assert trace["active_conflict_resolution_skip_reason"] == "no_resolving_queries"
    assert "conflict_resolution" not in _provider_roles_from_source_harness(harness)
    assert_active_gate_packet_invariants(
        packet,
        checkpoint_action_name=RESOLVE_CONFLICT,
        promoted_action_name=None,
        executed_action_name=None,
        gate_reason="no_resolving_queries",
    )
    assert "retrieve_targeted" not in _provider_roles_from_source_harness(harness)
