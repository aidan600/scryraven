from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_SUFFICIENT,
)
from core.controller_loop_spine import (
    ControllerLoopDispatchAuthorization,
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    ORDINARY_CONTINUATION_TRACE_KEY,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
    is_bounded_evaluator_continuation_candidate,
    is_bounded_expander_continuation_candidate,
    is_bounded_scout_continuation_candidate,
)
from core.ordinary_continuation_spine_gate import (
    ExpanderContinuationSpineGateFacts,
    authorize_expander_continuation_spine_gate,
    build_expander_continuation_spine_pregate,
)
from tests.test_evidence_integration_conflict_gate_ag37b import _decision
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _checkpoint(action_name: str) -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": action_name},
        "recommended_action_name": action_name,
    }


def _targeted_lifecycle(
    *,
    eligible: bool = True,
    queries: tuple[str, ...] = ("Acme Widget component warranty evidence",),
) -> dict[str, Any]:
    return {
        "targeted_retrieval_candidate_considered": True,
        "targeted_retrieval_candidate_eligible": eligible,
        "targeted_retrieval_candidate_used": False,
        "targeted_retrieval_candidate_reason": (
            "targeted_retrieval_candidate_available"
            if eligible
            else "query_generation_required"
        ),
        "targeted_retrieval_candidate_skip_reason": (
            None if eligible else "query_generation_required"
        ),
        "targeted_retrieval_candidate_blockers": (
            [] if eligible else ["query_generation_required"]
        ),
        "targeted_retrieval_candidate_queries": list(queries),
        "targeted_retrieval_candidate_query_provenance": (
            EXPANDER_COMPONENT_QUERIES
        ),
        "targeted_retrieval_candidate_conflict_resolving_queries": [],
    }


def _candidate(
    source_path: str = EXPANDER_COMPONENT_QUERIES,
    *,
    queries: tuple[str, ...] = ("Acme Widget component warranty evidence",),
    resolving_queries: tuple[str, ...] = (),
    current_iteration: int = 1,
    max_iterations: int = 2,
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=source_path,
        ordinary_next_queries=queries,
        conflict_resolving_queries=resolving_queries,
        prior_queries=("Acme Widget overview",),
        current_iteration=current_iteration,
        max_iterations=max_iterations,
    ).to_dict()


def test_ag45a_pure_candidate_authorizes_expander_and_preserves_other_lanes() -> None:
    expander = _candidate()
    evaluator = _candidate(EVALUATOR_NEXT_QUERIES)
    scout = _candidate(SCOUT_DIRECTED_QUERIES)
    conflict_mixed = _candidate(
        resolving_queries=("Care Program official corrected date",),
    )
    no_query = _candidate(queries=())
    budget_blocked = _candidate(current_iteration=2, max_iterations=2)

    assert is_bounded_expander_continuation_candidate(expander) is True
    assert is_bounded_evaluator_continuation_candidate(evaluator) is True
    assert is_bounded_scout_continuation_candidate(scout) is True
    assert is_bounded_expander_continuation_candidate(evaluator) is False
    assert is_bounded_expander_continuation_candidate(scout) is False
    assert is_bounded_expander_continuation_candidate(conflict_mixed) is False
    assert is_bounded_expander_continuation_candidate(no_query) is False
    assert is_bounded_expander_continuation_candidate(budget_blocked) is False


def test_ag45a_spine_authorizes_bounded_expander_retrieve_targeted() -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
            ordinary_continuation_candidate_trace=_candidate(),
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
        )
    )
    packet = result.trace_packet

    assert result.dispatch_authorization.authorized_action_name == RETRIEVE_TARGETED
    assert packet["promoted_action_name"] == RETRIEVE_TARGETED
    assert packet["executed_action_name"] is None
    assert packet["targeted_retrieval_gate_reason"] == (
        "bounded_expander_continuation_authorized"
    )
    assert packet["targeted_retrieval_dispatch_authorized"] is True
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert packet["targeted_retrieval_authorized_queries"] == [
        "Acme Widget component warranty evidence"
    ]
    assert packet[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        EXPANDER_COMPONENT_QUERIES
    )
    assert packet[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True


@pytest.mark.parametrize(
    "action_name",
    [
        STOP_SUFFICIENT,
        RECOVER_MISSING_SOURCE_CLASS,
        RECOVER_WEAK_CORPUS,
        RESOLVE_CONFLICT,
    ],
)
def test_ag45a_promoted_actions_block_expander_authorization(
    action_name: str,
) -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(action_name),
            ordinary_continuation_candidate_trace=_candidate(),
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
            source_class_lifecycle_trace={
                "active_source_class_recovery_eligible": True
            },
            weak_corpus_lifecycle_trace={"approved": True, "blockers": []},
            conflict_resolution_lifecycle_trace={
                "approved": True,
                "blockers": [],
                "active_conflict_resolution_considered": True,
            },
        )
    )
    packet = result.trace_packet

    assert result.dispatch_authorization.authorized_action_name != RETRIEVE_TARGETED
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False


def test_ag45a_arbitrary_retrieve_targeted_packets_cannot_authorize() -> None:
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"authorized_action_name": RETRIEVE_TARGETED}
    ).authorized_action_name is None
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {
            "authorized_action_name": RETRIEVE_TARGETED,
            "targeted_retrieval_dispatch_authorized": True,
            "targeted_retrieval_gate_reason": (
                "bounded_expander_continuation_authorized"
            ),
        }
    ).authorized_action_name is None


def test_ag45a_expander_adapter_authorizes_exact_component_queries() -> None:
    component_queries = (
        "Acme Widget component warranty evidence",
        "Acme Widget component rollout evidence",
    )
    facts = ExpanderContinuationSpineGateFacts.from_traces(
        component_queries=component_queries,
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(
            queries=component_queries
        ),
    )
    output = authorize_expander_continuation_spine_gate(facts)

    assert output.authorized is True
    assert output.authorized_queries == list(component_queries)
    assert output.expander_continuation_spine_gate_trace["reason"] == (
        "bounded_expander_continuation_authorized"
    )
    assert output.expander_continuation_spine_gate_trace["query_provenance"] == (
        EXPANDER_COMPONENT_QUERIES
    )
    assert output.ordinary_continuation_candidate_trace["used"] is True
    assert output.targeted_retrieval_lifecycle_trace[
        "targeted_retrieval_candidate_used"
    ] is True


def test_ag45a_expander_adapter_blocks_unapproved_candidate_without_fallback() -> None:
    facts = ExpanderContinuationSpineGateFacts.from_traces(
        component_queries=("Acme Widget component warranty evidence",),
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(eligible=False),
    )
    output = authorize_expander_continuation_spine_gate(facts)

    assert output.authorized is False
    assert output.authorized_queries == []
    assert output.fallback_preserves_legacy is False
    assert output.expander_continuation_spine_gate_trace[
        "targeted_retrieval_dispatch_authorized"
    ] is False


def test_ag45a_expander_pregate_keeps_spine_composition_out_of_pipeline() -> None:
    facts = ExpanderContinuationSpineGateFacts.from_traces(
        component_queries=("Acme Widget component warranty evidence",),
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
    )
    pregate = build_expander_continuation_spine_pregate(facts)

    assert pregate.ordinary_continuation_candidate_trace["source_path"] == (
        EXPANDER_COMPONENT_QUERIES
    )
    assert (
        pregate.controller_loop_spine_result.dispatch_authorization.authorized_action_name
        is None
    )


def test_ag45a_runtime_expander_continuation_uses_authorized_queries_only(
    tmp_path: Path,
) -> None:
    component_queries = [
        "Acme Widget component warranty evidence",
        "Acme Widget component rollout evidence",
    ]
    outcome, harness = _run_passive_case(
        tmp_path,
        expander_queries=tuple(component_queries),
    )
    trace = outcome.execution_trace
    checkpoint_packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == component_queries
    assert trace["queries_per_iteration"]["2"] == component_queries
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert trace["targeted_retrieval_candidate_used"] is True
    assert trace["targeted_retrieval_candidate_query_provenance"] == (
        EXPANDER_COMPONENT_QUERIES
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        EXPANDER_COMPONENT_QUERIES
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["ordinary_next_queries"] == (
        component_queries
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True
    assert trace["expander_continuation_spine_gate_trace"][
        "authorized_queries"
    ] == component_queries
    assert checkpoint_packet["targeted_retrieval_executor_dispatched"] is False
    assert checkpoint_packet["targeted_retrieval_authorized_queries"] == (
        component_queries
    )
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag45a_runtime_expander_terminal_stop_blocks_second_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(STOP_SUFFICIENT),
    )
    outcome, harness = _run_passive_case(
        tmp_path,
        expander_queries=("Acme Widget component warranty evidence",),
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 1
    assert trace["targeted_retrieval_candidate_used"] is False
    assert trace["expander_continuation_spine_gate_trace"]["reason"] == (
        "blocked_by_terminal_stop"
    )
    assert "2" not in trace["queries_per_iteration"]


def test_ag45a_runtime_scout_uses_scout_spine_gate(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_passive_case(
        tmp_path,
        router_report_type="quantitative_comparison",
        scout_queries=(
            "Acme Widget benchmark adoption data",
            "Acme Widget benchmark support matrix",
        ),
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 2
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        SCOUT_DIRECTED_QUERIES
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True
    assert trace["targeted_retrieval_candidate_used"] is True
    assert trace["expander_continuation_spine_gate_trace"]["available"] is False
    assert trace["scout_continuation_spine_gate_trace"][
        "targeted_retrieval_dispatch_authorized"
    ] is True


def test_ag45a_static_protected_surfaces_remain_unpromoted() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    spine_tree = ast.parse(_SPINE_PATH.read_text(encoding="utf-8"))

    assert "execute_retrieve_targeted_action" not in pipeline_source
    assert 'provider_role == "retrieve_targeted"' not in pipeline_source
    assert "provider_role == 'retrieve_targeted'" not in pipeline_source
    assert "ordinary_next_queries=conflict_resolving_queries" not in pipeline_source
    assert "approved_ordinary_next_queries=conflict_resolving_queries" not in (
        pipeline_source
    )
    assert "core.evaluator_continuation_spine_gate" not in pipeline_source

    forbidden_spine_imports = {
        "core.providers",
        "core.retrieval",
        "core.routing",
        "core.search_providers",
        "core.prompts",
    }
    imported = {
        node.module
        for node in ast.walk(spine_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported.isdisjoint(forbidden_spine_imports)
