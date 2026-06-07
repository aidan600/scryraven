from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
)
from core.controller_loop_spine import ControllerLoopDispatchAuthorization
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from tests.test_evidence_integration_conflict_gate_ag37b import (
    _decision,
    _force_checkpoint_action,
    _inject_conflict_evidence_state,
)
from tests.test_source_class_recovery_trace import _run_case as _run_source_case
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_CLASSIFICATIONS = {
    "ordinary_continuation_legacy_owner",
    "bounded_spine_authorized_retrieve_targeted",
    "bounded_spine_authorized_recovery",
    "conflict_resolution_separate_lane",
    "terminal_stop_no_continuation",
    "controller_owned_retrieval_stop",
    "non_continuation",
}


@dataclass(frozen=True)
class ContinuationOwnershipPath:
    path_name: str
    classification: str
    code_surface: str
    code_marker: str
    query_source_field: str | None
    can_assign_current_queries_or_reenter_retrieval: bool
    currently_spine_authorized: bool
    future_retrieve_targeted_candidate: bool


ORDINARY_CONTINUATION_OWNERSHIP_MAP = (
    ContinuationOwnershipPath(
        path_name="scout_directed_queries",
        classification="bounded_spine_authorized_retrieve_targeted",
        code_surface="run_pipeline / SCOUT branch",
        code_marker='query_source="scout"',
        query_source_field="scout_context.directed_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=True,
    ),
    ContinuationOwnershipPath(
        path_name="expander_component_queries",
        classification="bounded_spine_authorized_retrieve_targeted",
        code_surface="run_pipeline / QUERY EXPANDER branch",
        code_marker='query_source="expander"',
        query_source_field="expander_data.component_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=True,
    ),
    ContinuationOwnershipPath(
        path_name="evaluator_new_queries",
        classification="bounded_spine_authorized_retrieve_targeted",
        code_surface="run_pipeline / GAP EVALUATOR branch",
        code_marker='eval_data.get("new_queries", [])',
        query_source_field="eval_data.new_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=True,
    ),
    ContinuationOwnershipPath(
        path_name="retrieval_stop_continue",
        classification="controller_owned_retrieval_stop",
        code_surface="_record_retrieval_stop_shadow_once",
        code_marker="RetrievalStopControllerDecision.CONTINUE_RETRIEVAL",
        query_source_field="next_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="weak_corpus_recovery_queries",
        classification="bounded_spine_authorized_recovery",
        code_surface="run_pipeline / weak corpus recovery gate",
        code_marker="weak_corpus_authorized_action == RECOVER_WEAK_CORPUS",
        query_source_field="weak_corpus_decision.queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="source_class_recovery_queries",
        classification="bounded_spine_authorized_recovery",
        code_surface="run_pipeline / source class recovery runner handoff",
        code_marker="run_source_class_recovery_dispatch(",
        query_source_field="active_source_class_recovery_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="conflict_resolving_queries",
        classification="conflict_resolution_separate_lane",
        code_surface="runtime answer-contract conflict projection",
        code_marker="conflict_resolving_queries=conflict_resolving_queries",
        query_source_field="evidence_state.resolving_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=True,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="evaluator_no_queries_stop",
        classification="terminal_stop_no_continuation",
        code_surface="run_pipeline / GAP EVALUATOR no-query branch",
        code_marker="RetrievalStopControllerDecision.STOP_NO_QUERIES",
        query_source_field=None,
        can_assign_current_queries_or_reenter_retrieval=False,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="pre_search_redundant_queries_stop",
        classification="terminal_stop_no_continuation",
        code_surface="run_pipeline / pre-search redundant query branch",
        code_marker="RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES",
        query_source_field=None,
        can_assign_current_queries_or_reenter_retrieval=False,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="iteration_budget_exhausted_stop",
        classification="terminal_stop_no_continuation",
        code_surface="run_pipeline / iteration budget branch",
        code_marker="RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED",
        query_source_field=None,
        can_assign_current_queries_or_reenter_retrieval=False,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="disambiguation_retry",
        classification="non_continuation",
        code_surface="run_pipeline / first-pass utilization retry",
        code_marker="execute_disambiguation_retry_from_scope",
        query_source_field="build_disambiguation_queries(...)",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
    ContinuationOwnershipPath(
        path_name="supplemental_synthesis_search",
        classification="non_continuation",
        code_surface="run_pipeline / synthesis evaluator supplemental search",
        code_marker="execute_supplemental_search_from_scope",
        query_source_field="synth_eval_data.supplemental_queries",
        can_assign_current_queries_or_reenter_retrieval=True,
        currently_spine_authorized=False,
        future_retrieve_targeted_candidate=False,
    ),
)


def _pipeline_source() -> str:
    legacy_stage = _ROOT / "core" / "legacy_review_runtime_stage.py"
    return _PIPELINE_PATH.read_text(encoding="utf-8") + "\n" + legacy_stage.read_text(encoding="utf-8")


def _provider_roles(harness: Any) -> list[str | None]:
    calls = getattr(harness, "search_calls", None)
    if calls and isinstance(calls[0], dict):
        return [call["provider_role"] for call in calls]
    details = getattr(harness, "search_call_details", ())
    return [call["provider_role"] for call in details]


def _assert_checkpoint_does_not_authorize_retrieve_targeted(trace: dict[str, Any]) -> None:
    packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    authorization = ControllerLoopDispatchAuthorization.from_trace_packet(packet)

    assert authorization.authorized_action_name != RETRIEVE_TARGETED
    assert authorization.authorized_action_name is None
    assert packet["executed_action_name"] != RETRIEVE_TARGETED
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False


def test_ag44a_executable_ownership_map_is_complete_and_source_anchored() -> None:
    source = _pipeline_source()
    mapped_names = {entry.path_name for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP}

    assert {entry.classification for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP} <= (
        _CLASSIFICATIONS
    )
    assert {
        "scout_directed_queries",
        "expander_component_queries",
        "evaluator_new_queries",
        "retrieval_stop_continue",
        "weak_corpus_recovery_queries",
        "source_class_recovery_queries",
        "conflict_resolving_queries",
        "evaluator_no_queries_stop",
        "pre_search_redundant_queries_stop",
        "iteration_budget_exhausted_stop",
        "disambiguation_retry",
        "supplemental_synthesis_search",
    } <= mapped_names

    for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP:
        assert entry.code_marker in source, entry.path_name

    ordinary_entries = [
        entry
        for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
        if entry.classification == "ordinary_continuation_legacy_owner"
    ]
    assert not ordinary_entries

    controller_owned_entries = [
        entry
        for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
        if entry.classification == "controller_owned_retrieval_stop"
    ]
    assert {entry.path_name for entry in controller_owned_entries} == {
        "retrieval_stop_continue"
    }
    assert all(entry.query_source_field for entry in controller_owned_entries)
    assert all(
        entry.can_assign_current_queries_or_reenter_retrieval
        for entry in controller_owned_entries
    )
    assert all(
        not entry.currently_spine_authorized for entry in controller_owned_entries
    )
    assert all(
        not entry.future_retrieve_targeted_candidate
        for entry in controller_owned_entries
    )
    evaluator_entry = {
        entry.path_name: entry for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
    }["evaluator_new_queries"]
    assert evaluator_entry.classification == (
        "bounded_spine_authorized_retrieve_targeted"
    )
    assert evaluator_entry.currently_spine_authorized is True
    assert evaluator_entry.future_retrieve_targeted_candidate is True
    expander_entry = {
        entry.path_name: entry for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
    }["expander_component_queries"]
    assert expander_entry.classification == (
        "bounded_spine_authorized_retrieve_targeted"
    )
    assert expander_entry.currently_spine_authorized is True
    assert expander_entry.future_retrieve_targeted_candidate is True
    scout_entry = {
        entry.path_name: entry for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
    }["scout_directed_queries"]
    assert scout_entry.classification == (
        "bounded_spine_authorized_retrieve_targeted"
    )
    assert scout_entry.currently_spine_authorized is True
    assert scout_entry.future_retrieve_targeted_candidate is True

    separate_lanes = {
        entry.path_name: entry
        for entry in ORDINARY_CONTINUATION_OWNERSHIP_MAP
        if entry.classification
        in {
            "bounded_spine_authorized_recovery",
            "conflict_resolution_separate_lane",
        }
    }
    assert separate_lanes["weak_corpus_recovery_queries"].currently_spine_authorized
    assert separate_lanes["source_class_recovery_queries"].currently_spine_authorized
    assert separate_lanes["conflict_resolving_queries"].currently_spine_authorized
    assert all(
        not entry.future_retrieve_targeted_candidate
        for entry in separate_lanes.values()
    )


def test_ag44a_static_guards_keep_ordinary_paths_outside_retrieve_targeted_dispatch() -> None:
    source = _pipeline_source()
    tree = ast.parse(source)

    assert "execute_retrieve_targeted_action" not in source
    assert 'provider_role == "retrieve_targeted"' not in source
    assert "provider_role == 'retrieve_targeted'" not in source

    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left_is_authorized_spine_action = (
            isinstance(node.left, ast.Name)
            and node.left.id == "authorized_spine_action"
        )
        compares_to_retrieve_targeted = any(
            (
                isinstance(comparator, ast.Constant)
                and comparator.value == RETRIEVE_TARGETED
            )
            or (
                isinstance(comparator, ast.Name)
                and comparator.id == "RETRIEVE_TARGETED"
            )
            for comparator in node.comparators
        )
        assert not (
            left_is_authorized_spine_action and compares_to_retrieve_targeted
        )


def test_ag44a_dispatch_authorization_allowlist_still_excludes_retrieve_targeted() -> None:
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RETRIEVE_TARGETED}
    ).authorized_action_name is None
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RECOVER_MISSING_SOURCE_CLASS}
    ).authorized_action_name == RECOVER_MISSING_SOURCE_CLASS
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RECOVER_WEAK_CORPUS}
    ).authorized_action_name == RECOVER_WEAK_CORPUS
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RESOLVE_CONFLICT}
    ).authorized_action_name == RESOLVE_CONFLICT


@pytest.mark.parametrize(
    ("name", "harness_kwargs", "expected_provenance"),
    [
        (
            "expander",
            {
                "expander_queries": (
                    "Acme Widget component warranty evidence",
                    "Acme Widget component rollout evidence",
                ),
            },
            "expander_component_queries",
        ),
        (
            "scout",
            {
                "router_report_type": "quantitative_comparison",
                "scout_queries": (
                    "Acme Widget benchmark adoption data",
                    "Acme Widget benchmark support matrix",
                ),
            },
            "scout_directed_queries",
        ),
    ],
)
def test_ag44a_ordinary_continuation_runtime_ownership_matches_promoted_paths(
    tmp_path: Path,
    name: str,
    harness_kwargs: dict[str, Any],
    expected_provenance: str,
) -> None:
    outcome, harness = _run_passive_case(tmp_path / name, **harness_kwargs)
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 2
    assert _provider_roles(harness) == ["main_retrieval", "main_retrieval"]
    assert trace["queries_per_iteration"]["2"] == harness.search_calls[1]["queries"]
    assert trace["targeted_retrieval_candidate_considered"] is True
    expected_authorized = expected_provenance in {
        "expander_component_queries",
        "scout_directed_queries",
    }
    assert trace["targeted_retrieval_candidate_used"] is expected_authorized
    assert trace["targeted_retrieval_candidate_query_provenance"] == (
        expected_provenance
    )
    assert trace["targeted_retrieval_candidate_queries"] == harness.search_calls[1][
        "queries"
    ]
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == []
    assert trace["active_source_class_recovery_used"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["active_conflict_resolution_used"] is False
    assert trace["scrutineer_ran"] is False
    assert {
        "retrieve_targeted",
        "source_class_recovery",
        "weak_corpus_recovery",
        "conflict_resolution",
        "scrutineer_remediation",
    }.isdisjoint(_provider_roles(harness))
    if expected_authorized:
        packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
        authorization = ControllerLoopDispatchAuthorization.from_trace_packet(packet)
        assert authorization.authorized_action_name == RETRIEVE_TARGETED
        assert packet["targeted_retrieval_dispatch_authorized"] is True
        assert packet["targeted_retrieval_executor_dispatched"] is False
    else:
        _assert_checkpoint_does_not_authorize_retrieve_targeted(trace)


def test_ag44a_conflict_resolving_queries_remain_separate_from_ordinary_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inject_conflict_evidence_state(
        monkeypatch,
        resolving_queries=("Care Program official corrected date",),
        ordinary_next_queries=("Care Program ordinary background",),
    )
    _force_checkpoint_action(monkeypatch, RESOLVE_CONFLICT)
    outcome, harness, _log_entry = _run_source_case(
        tmp_path,
        query="Care Program current official dates conflict",
        core_topic="Care Program current official dates conflict",
        primary_entity="Care Program",
        researcher_query="Care Program current official dates",
    )
    trace = outcome.execution_trace

    assert trace["active_conflict_resolution_used"] is True
    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_conflict_resolution" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert trace["targeted_retrieval_candidate_queries"] == [
        "Care Program ordinary background"
    ]
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == [
        "Care Program official corrected date"
    ]
    assert "conflict_resolution" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag44a_source_class_recovery_remains_bounded_spine_authorized_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)
    outcome, harness, _log_entry = _run_source_case(
        tmp_path,
        query=(
            "What are the current eligibility requirements and official rules "
            "for the care program?"
        ),
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    trace = outcome.execution_trace

    assert trace["active_source_class_recovery_used"] is True
    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_source_class_recovery" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert "source_class_recovery" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag44a_weak_corpus_recovery_remains_bounded_spine_authorized_recovery(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path)
    trace = outcome.execution_trace

    assert trace["weak_corpus_recovery_used"] is True
    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_weak_corpus_recovery" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert "weak_corpus_recovery" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag44a_terminal_stop_blocks_continuation_before_targeted_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.pipeline_orchestrator.decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision("stop_sufficient"),
    )
    outcome, harness = _run_passive_case(
        tmp_path,
        evaluator_responses=[
            {
                "is_sufficient": False,
                "new_queries": ["Acme Widget migration timeline"],
            }
        ],
    )
    trace = outcome.execution_trace

    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_terminal_stop" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert "retrieve_targeted" not in _provider_roles(harness)
    _assert_checkpoint_does_not_authorize_retrieve_targeted(trace)
