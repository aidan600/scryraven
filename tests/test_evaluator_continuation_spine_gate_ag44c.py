from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
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
    RETRIEVAL_STOP_CONTINUE,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
    is_bounded_evaluator_continuation_candidate,
    is_bounded_expander_continuation_candidate,
    is_bounded_scout_continuation_candidate,
    mark_ordinary_continuation_candidate_spine_authorized,
)
from core.ordinary_continuation_spine_gate import (
    EvaluatorContinuationSpineGateFacts,
    authorize_evaluator_continuation_spine_gate,
    build_evaluator_continuation_spine_pregate,
)
from tests.test_evidence_integration_conflict_gate_ag37b import (
    _force_checkpoint_action,
    _inject_conflict_evidence_state,
)
from tests.test_source_class_recovery_trace import _run_case as _run_source_case
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_CORE_PATH = _ROOT / "core"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_GATE_PATH = _ROOT / "core" / "ordinary_continuation_spine_gate.py"


def _checkpoint(action_name: str) -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": action_name},
        "recommended_action_name": action_name,
    }


def _targeted_lifecycle(
    *,
    eligible: bool = True,
    queries: tuple[str, ...] = ("Acme Widget migration timeline",),
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
        "targeted_retrieval_candidate_query_provenance": EVALUATOR_NEXT_QUERIES,
        "targeted_retrieval_candidate_conflict_resolving_queries": [],
    }


def _candidate(
    source_path: str = EVALUATOR_NEXT_QUERIES,
    *,
    queries: tuple[str, ...] = ("Acme Widget migration timeline",),
    resolving_queries: tuple[str, ...] = (),
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=source_path,
        ordinary_next_queries=queries,
        conflict_resolving_queries=resolving_queries,
        prior_queries=("Acme Widget rollout evidence",),
        current_iteration=1,
        max_iterations=2,
    ).to_dict()


def test_ag44c_pure_evaluator_candidate_remains_bounded_after_expander_promotion() -> None:
    evaluator = _candidate()
    expander = _candidate(EXPANDER_COMPONENT_QUERIES)
    scout = _candidate(SCOUT_DIRECTED_QUERIES)
    conflict_mixed = _candidate(
        resolving_queries=("Care Program official corrected date",),
    )

    assert is_bounded_evaluator_continuation_candidate(evaluator) is True
    assert is_bounded_evaluator_continuation_candidate(expander) is False
    assert is_bounded_evaluator_continuation_candidate(scout) is False
    assert is_bounded_evaluator_continuation_candidate(conflict_mixed) is False
    assert is_bounded_expander_continuation_candidate(expander) is True
    assert is_bounded_expander_continuation_candidate(evaluator) is False
    assert is_bounded_expander_continuation_candidate(scout) is False
    assert is_bounded_expander_continuation_candidate(conflict_mixed) is False
    assert is_bounded_scout_continuation_candidate(scout) is True
    assert is_bounded_scout_continuation_candidate(evaluator) is False
    assert is_bounded_scout_continuation_candidate(expander) is False
    assert is_bounded_scout_continuation_candidate(conflict_mixed) is False
    assert mark_ordinary_continuation_candidate_spine_authorized(
        evaluator,
        used=True,
    )["currently_spine_authorized"] is True
    assert mark_ordinary_continuation_candidate_spine_authorized(
        expander,
        used=True,
    )["currently_spine_authorized"] is True
    assert mark_ordinary_continuation_candidate_spine_authorized(
        scout,
        used=True,
    )["currently_spine_authorized"] is True


def test_ag44c_spine_authorizes_only_bounded_evaluator_retrieve_targeted() -> None:
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
    assert packet["authorized_action_name"] == RETRIEVE_TARGETED
    assert packet["targeted_retrieval_dispatch_authorized"] is True
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert packet["targeted_retrieval_gate_reason"] == (
        "bounded_evaluator_continuation_authorized"
    )
    assert packet["targeted_retrieval_authorized_queries"] == [
        "Acme Widget migration timeline"
    ]
    assert packet[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True
    assert packet[ORDINARY_CONTINUATION_TRACE_KEY][
        "currently_spine_authorized"
    ] is True


@pytest.mark.parametrize("source_path", [RETRIEVAL_STOP_CONTINUE])
def test_ag44c_non_evaluator_candidates_cannot_authorize_retrieve_targeted(
    source_path: str,
) -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
            ordinary_continuation_candidate_trace=_candidate(source_path),
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
        )
    )
    packet = result.trace_packet

    assert result.dispatch_authorization.authorized_action_name is None
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_gate_reason"] == (
        "blocked_by_runtime_dispatch_not_inverted"
    )


def test_ag44c_terminal_stop_still_wins_before_evaluator_gate() -> None:
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(STOP_SUFFICIENT),
            ordinary_continuation_candidate_trace=_candidate(),
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
        )
    )
    packet = result.trace_packet

    assert result.terminal_stop_approved is True
    assert result.dispatch_authorization.authorized_action_name is None
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_gate_reason"] == "blocked_by_terminal_stop"


def test_ag44c_dispatch_authorization_rejects_arbitrary_retrieve_targeted_packets() -> None:
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RETRIEVE_TARGETED}
    ).authorized_action_name is None
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {
            "authorized_action_name": RETRIEVE_TARGETED,
            "targeted_retrieval_dispatch_authorized": True,
        }
    ).authorized_action_name is None


def test_ag44d_extracted_helper_authorizes_same_evaluator_gate_outputs() -> None:
    evaluator_queries = (
        "Acme Widget migration timeline",
        "Acme Widget support matrix",
    )
    facts = EvaluatorContinuationSpineGateFacts.from_traces(
        evaluator_queries=evaluator_queries,
        prior_queries=("Acme Widget rollout evidence",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(
            queries=evaluator_queries
        ),
    )
    output = authorize_evaluator_continuation_spine_gate(facts)

    assert output.authorized is True
    assert output.authorized_queries == list(evaluator_queries)
    assert output.checkpoint_decided is True
    assert output.fallback_preserves_legacy is False
    assert output.evaluator_continuation_spine_gate_trace == {
        "available": True,
        "reason": "bounded_evaluator_continuation_authorized",
        "checkpoint_action_name": RETRIEVE_TARGETED,
        "authorized_action_name": RETRIEVE_TARGETED,
        "targeted_retrieval_dispatch_authorized": True,
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": list(evaluator_queries),
        "query_provenance": EVALUATOR_NEXT_QUERIES,
    }
    assert output.ordinary_continuation_candidate_trace["source_path"] == (
        EVALUATOR_NEXT_QUERIES
    )
    assert output.ordinary_continuation_candidate_trace["used"] is True
    assert output.ordinary_continuation_candidate_trace[
        "currently_spine_authorized"
    ] is True
    assert output.targeted_retrieval_lifecycle_trace[
        "targeted_retrieval_candidate_used"
    ] is True
    assert output.checkpoint_trace["targeted_retrieval_executor_dispatched"] is False


def test_ag44d_extracted_helper_preserves_legacy_fallback_when_not_safe() -> None:
    evaluator_queries = ("Acme Widget migration timeline",)
    facts = EvaluatorContinuationSpineGateFacts.from_traces(
        evaluator_queries=evaluator_queries,
        prior_queries=("Acme Widget rollout evidence",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(
            eligible=False,
            queries=evaluator_queries,
        ),
    )
    output = authorize_evaluator_continuation_spine_gate(facts)

    assert output.authorized is False
    assert output.authorized_queries == list(evaluator_queries)
    assert output.checkpoint_decided is False
    assert output.checkpoint_handoff == {}
    assert output.fallback_preserves_legacy is True
    assert output.reason == (
        "evaluator_continuation_gate_not_authorized_legacy_preserved"
    )
    assert output.checkpoint_trace["available"] is False
    assert output.evaluator_continuation_spine_gate_trace[
        "targeted_retrieval_dispatch_authorized"
    ] is False
    assert output.evaluator_continuation_spine_gate_trace[
        "targeted_retrieval_executor_dispatched"
    ] is False


def test_ag44d_extracted_helper_preserves_terminal_stop_without_fallback() -> None:
    facts = EvaluatorContinuationSpineGateFacts.from_traces(
        evaluator_queries=("Acme Widget migration timeline",),
        prior_queries=("Acme Widget rollout evidence",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(STOP_SUFFICIENT),
        checkpoint_handoff={"action_name": STOP_SUFFICIENT},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
    )
    output = authorize_evaluator_continuation_spine_gate(facts)

    assert output.authorized is False
    assert output.authorized_queries == []
    assert output.checkpoint_decided is True
    assert output.checkpoint_handoff == {"action_name": STOP_SUFFICIENT}
    assert output.fallback_preserves_legacy is False
    assert output.checkpoint_trace["checkpoint_action_name"] == STOP_SUFFICIENT
    assert output.evaluator_continuation_spine_gate_trace["reason"] == (
        "blocked_by_terminal_stop"
    )


def test_ag44d_extracted_pregate_keeps_candidate_construction_out_of_pipeline() -> None:
    facts = EvaluatorContinuationSpineGateFacts.from_traces(
        evaluator_queries=("Acme Widget migration timeline",),
        prior_queries=("Acme Widget rollout evidence",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
    )
    pregate = build_evaluator_continuation_spine_pregate(facts)

    assert pregate.ordinary_continuation_candidate_trace["source_path"] == (
        EVALUATOR_NEXT_QUERIES
    )
    assert pregate.ordinary_continuation_candidate_trace[
        "ordinary_next_queries"
    ] == ["Acme Widget migration timeline"]
    assert (
        pregate.controller_loop_spine_result.dispatch_authorization.authorized_action_name
        is None
    )
    assert pregate.controller_loop_spine_result.trace_packet[
        "targeted_retrieval_executor_dispatched"
    ] is False


def test_ag44c_runtime_evaluator_continuation_is_gated_before_second_search(
    tmp_path: Path,
) -> None:
    evaluator_queries = [
        "Acme Widget migration timeline",
        "Acme Widget support matrix",
    ]
    outcome, harness = _run_passive_case(
        tmp_path,
        evaluator_responses=[
            {"is_sufficient": False, "new_queries": evaluator_queries}
        ],
    )
    trace = outcome.execution_trace
    gate_trace = trace["evaluator_continuation_spine_gate_trace"]
    checkpoint_packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == evaluator_queries
    assert trace["queries_per_iteration"]["2"] == evaluator_queries
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert gate_trace["targeted_retrieval_dispatch_authorized"] is True
    assert gate_trace["targeted_retrieval_executor_dispatched"] is False
    assert gate_trace["authorized_queries"] == evaluator_queries
    assert gate_trace["authorized_action_name"] == RETRIEVE_TARGETED
    assert checkpoint_packet["evaluator_continuation_spine_gate_trace"] == gate_trace
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        EVALUATOR_NEXT_QUERIES
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY][
        "currently_spine_authorized"
    ] is True
    assert trace["targeted_retrieval_candidate_used"] is True
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag44c_scout_runtime_uses_scout_spine_gate(
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
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY][
        "currently_spine_authorized"
    ] is True
    assert trace["targeted_retrieval_candidate_used"] is True
    assert trace["evaluator_continuation_spine_gate_trace"]["available"] is False
    assert trace["scout_continuation_spine_gate_trace"][
        "targeted_retrieval_dispatch_authorized"
    ] is True


def test_ag44c_conflict_resolving_queries_do_not_become_ordinary_next_queries(
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
    assert trace["targeted_retrieval_candidate_queries"] == [
        "Care Program ordinary background"
    ]
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == [
        "Care Program official corrected date"
    ]
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag44c_static_protected_surfaces_remain_unpromoted() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    spine_tree = ast.parse(_SPINE_PATH.read_text(encoding="utf-8"))
    gate_source = _GATE_PATH.read_text(encoding="utf-8")
    gate_tree = ast.parse(gate_source)

    assert "execute_retrieve_targeted_action" not in pipeline_source
    assert "execute_retrieve_targeted_action" not in gate_source
    assert 'provider_role == "retrieve_targeted"' not in pipeline_source
    assert "provider_role == 'retrieve_targeted'" not in pipeline_source
    assert 'provider_role == "retrieve_targeted"' not in gate_source
    assert "provider_role == 'retrieve_targeted'" not in gate_source
    assert "ordinary_next_queries=conflict_resolving_queries" not in pipeline_source
    assert "approved_ordinary_next_queries=conflict_resolving_queries" not in (
        pipeline_source
    )
    assert not (_CORE_PATH / "evaluator_continuation_spine_gate.py").exists()
    for production_path in _CORE_PATH.rglob("*.py"):
        production_source = production_path.read_text(encoding="utf-8")
        assert "core.evaluator_continuation_spine_gate" not in production_source
    assert (
        "evaluator_continuation_gate_not_authorized_legacy_preserved"
        not in pipeline_source
    )
    assert (
        "evaluator_continuation_gate_not_authorized_legacy_preserved"
        in gate_source
    )

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

    forbidden_controller_imports = {
        "core.providers",
        "core.retrieval",
        "core.routing",
        "core.search_providers",
        "core.prompts",
    }
    helper_imports = {
        node.module
        for node in ast.walk(gate_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert helper_imports.isdisjoint(forbidden_controller_imports)

    pipeline_tree = ast.parse(pipeline_source)
    evaluator_gate_function = next(
        node
        for node in ast.walk(pipeline_tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_authorize_evaluator_continuation_before_scheduling"
    )
    evaluator_gate_calls = {
        node.func.id
        for node in ast.walk(evaluator_gate_function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "build_controller_loop_spine_result" not in evaluator_gate_calls
    assert "build_ordinary_continuation_candidate" not in evaluator_gate_calls
    assert "authorize_evaluator_continuation_spine_gate" in evaluator_gate_calls
