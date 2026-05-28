from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
    RETRIEVE_TARGETED,
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
)
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _checkpoint(action_name: str) -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": action_name},
        "recommended_action_name": action_name,
    }


def _targeted_lifecycle(*, eligible: bool = True) -> dict[str, Any]:
    return {
        "targeted_retrieval_candidate_considered": True,
        "targeted_retrieval_candidate_eligible": eligible,
        "targeted_retrieval_candidate_used": False,
        "targeted_retrieval_candidate_reason": (
            "targeted_retrieval_candidate_available"
            if eligible
            else "no_ordinary_next_queries"
        ),
        "targeted_retrieval_candidate_skip_reason": (
            None if eligible else "no_ordinary_next_queries"
        ),
        "targeted_retrieval_candidate_blockers": (
            [] if eligible else ["no_ordinary_next_queries"]
        ),
        "targeted_retrieval_candidate_queries": (
            ["Acme Widget support matrix"] if eligible else []
        ),
        "targeted_retrieval_candidate_conflict_resolving_queries": [],
    }


@pytest.mark.parametrize(
    ("source_path", "queries"),
    [
        (EVALUATOR_NEXT_QUERIES, ("Acme Widget release timeline",)),
        (EXPANDER_COMPONENT_QUERIES, ("Acme Widget component warranty",)),
        (SCOUT_DIRECTED_QUERIES, ("Acme Widget benchmark support matrix",)),
    ],
)
def test_ag44b_pure_candidate_approves_old_ordinary_query_sources(
    source_path: str,
    queries: tuple[str, ...],
) -> None:
    candidate = build_ordinary_continuation_candidate(
        source_path=source_path,
        ordinary_next_queries=queries,
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=3,
    ).to_dict()

    assert candidate["considered"] is True
    assert candidate["eligible"] is True
    assert candidate["reason"] == "ordinary_continuation_candidate_available"
    assert candidate["ordinary_next_queries"] == list(queries)
    assert candidate["query_provenance"] == source_path
    assert candidate["source_path"] == source_path
    assert candidate["prior_query_count"] == 1
    assert candidate["currently_spine_authorized"] is False
    assert candidate["used"] is False
    assert candidate["can_be_future_retrieve_targeted_candidate"] is True


@pytest.mark.parametrize(
    ("name", "kwargs", "expected_blocker"),
    [
        (
            "no_query",
            {"ordinary_next_queries": ()},
            "no_ordinary_next_queries",
        ),
        (
            "redundant",
            {
                "ordinary_next_queries": ("Acme Widget overview",),
                "next_queries_redundant": True,
            },
            "redundant_with_prior_queries",
        ),
        (
            "budget_exhausted",
            {
                "ordinary_next_queries": ("Acme Widget overview",),
                "current_iteration": 2,
                "max_iterations": 2,
            },
            "blocked_by_iteration_budget",
        ),
    ],
)
def test_ag44b_pure_candidate_blocks_no_query_redundant_and_budget_cases(
    name: str,
    kwargs: dict[str, Any],
    expected_blocker: str,
) -> None:
    values = {
        "source_path": EVALUATOR_NEXT_QUERIES,
        "prior_queries": ("Acme Widget overview",),
        "current_iteration": 1,
        "max_iterations": 3,
        **kwargs,
    }
    candidate = build_ordinary_continuation_candidate(
        **values,
    ).to_dict()

    assert name
    assert candidate["considered"] is True
    assert candidate["eligible"] is False
    assert expected_blocker in candidate["blockers"]
    assert candidate["used"] is False
    assert candidate["currently_spine_authorized"] is False


def test_ag44b_conflict_resolving_queries_remain_separate_from_ordinary_queries() -> None:
    candidate = build_ordinary_continuation_candidate(
        source_path=RETRIEVAL_STOP_CONTINUE,
        ordinary_next_queries=("Care Program ordinary background",),
        conflict_resolving_queries=("Care Program official corrected date",),
        current_iteration=1,
        max_iterations=3,
    ).to_dict()

    assert candidate["ordinary_next_queries"] == [
        "Care Program ordinary background"
    ]
    assert candidate["conflict_resolving_queries"] == [
        "Care Program official corrected date"
    ]
    assert candidate["conflict_resolving_queries"] != candidate[
        "ordinary_next_queries"
    ]


def test_ag44b_spine_records_candidate_and_ag44c_authorizes_evaluator_targeted() -> None:
    candidate = build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=("Acme Widget support matrix",),
        current_iteration=1,
        max_iterations=3,
    ).to_dict()
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
            source_class_lifecycle_trace={
                "active_source_class_recovery_eligible": False
            },
            weak_corpus_lifecycle_trace={"approved": False},
            conflict_resolution_lifecycle_trace={"approved": False},
            ordinary_continuation_candidate_trace=candidate,
            targeted_retrieval_lifecycle_trace=_targeted_lifecycle(),
        )
    )
    packet = result.trace_packet

    assert packet[ORDINARY_CONTINUATION_TRACE_KEY] == {
        **candidate,
        "currently_spine_authorized": True,
        "used": True,
    }
    assert packet["ordinary_continuation_candidate_eligible"] is True
    assert packet["targeted_retrieval_gate_reason"] == (
        "bounded_evaluator_continuation_authorized"
    )
    assert packet["targeted_retrieval_dispatch_authorized"] is True
    assert packet["targeted_retrieval_executor_dispatched"] is False
    assert result.dispatch_authorization.authorized_action_name == RETRIEVE_TARGETED


def test_ag44b_spine_seam_blocker_wins_when_candidate_is_not_eligible() -> None:
    candidate = build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=(),
        current_iteration=1,
        max_iterations=3,
    ).to_dict()
    result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
            source_class_lifecycle_trace={
                "active_source_class_recovery_eligible": False
            },
            weak_corpus_lifecycle_trace={"approved": False},
            conflict_resolution_lifecycle_trace={"approved": False},
            ordinary_continuation_candidate_trace=candidate,
        )
    )
    packet = result.trace_packet

    assert packet["ordinary_continuation_candidate_eligible"] is False
    assert packet["targeted_retrieval_gate_reason"] == "no_ordinary_next_queries"
    assert packet["blocked_or_skipped_actions"][RETRIEVE_TARGETED] == (
        "no_ordinary_next_queries"
    )
    assert packet["targeted_retrieval_dispatch_authorized"] is False
    assert packet["targeted_retrieval_executor_dispatched"] is False


@pytest.mark.parametrize(
    ("name", "harness_kwargs", "expected_source_path"),
    [
        (
            "evaluator",
            {
                "evaluator_responses": [
                    {
                        "is_sufficient": False,
                        "new_queries": [
                            "Acme Widget migration timeline",
                            "Acme Widget support matrix",
                        ],
                    }
                ],
            },
            EVALUATOR_NEXT_QUERIES,
        ),
        (
            "expander",
            {
                "expander_queries": (
                    "Acme Widget component warranty evidence",
                    "Acme Widget component rollout evidence",
                ),
            },
            EXPANDER_COMPONENT_QUERIES,
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
            SCOUT_DIRECTED_QUERIES,
        ),
    ],
)
def test_ag44b_runtime_ordinary_continuation_records_passive_candidate_without_behavior_change(
    tmp_path: Path,
    name: str,
    harness_kwargs: dict[str, Any],
    expected_source_path: str,
) -> None:
    outcome, harness = _run_passive_case(tmp_path / name, **harness_kwargs)
    trace = outcome.execution_trace
    candidate = trace[ORDINARY_CONTINUATION_TRACE_KEY]
    checkpoint_packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    authorization = ControllerLoopDispatchAuthorization.from_trace_packet(
        checkpoint_packet
    )

    assert len(harness.search_calls) == 2
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert trace["queries_per_iteration"]["2"] == harness.search_calls[1]["queries"]
    assert candidate["considered"] is True
    assert candidate["eligible"] is True
    assert candidate["source_path"] == expected_source_path
    assert candidate["query_provenance"] == expected_source_path
    assert candidate["ordinary_next_queries"] == harness.search_calls[1]["queries"]
    assert candidate["conflict_resolving_queries"] == []
    expected_spine_authorized = expected_source_path in {
        EVALUATOR_NEXT_QUERIES,
        EXPANDER_COMPONENT_QUERIES,
        SCOUT_DIRECTED_QUERIES,
    }
    assert candidate["currently_spine_authorized"] is expected_spine_authorized
    assert candidate["used"] is expected_spine_authorized
    assert checkpoint_packet[ORDINARY_CONTINUATION_TRACE_KEY] == candidate
    assert trace["targeted_retrieval_candidate_used"] is expected_spine_authorized
    if expected_source_path == EVALUATOR_NEXT_QUERIES:
        assert trace["evaluator_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
    elif expected_source_path == EXPANDER_COMPONENT_QUERIES:
        assert trace["expander_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
    elif expected_source_path == SCOUT_DIRECTED_QUERIES:
        assert trace["scout_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
    else:
        assert authorization.authorized_action_name != RETRIEVE_TARGETED
        assert checkpoint_packet["targeted_retrieval_dispatch_authorized"] is False
    assert checkpoint_packet["targeted_retrieval_executor_dispatched"] is False
    assert {
        "retrieve_targeted",
        "source_class_recovery",
        "weak_corpus_recovery",
        "conflict_resolution",
        "scrutineer_remediation",
    }.isdisjoint({call["provider_role"] for call in harness.search_calls})


def test_ag44b_static_guards_keep_retrieve_targeted_unpromoted() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    pipeline_tree = ast.parse(pipeline_source)
    spine_source = _SPINE_PATH.read_text(encoding="utf-8")

    assert "execute_retrieve_targeted_action" not in pipeline_source
    assert 'provider_role == "retrieve_targeted"' not in pipeline_source
    assert "provider_role == 'retrieve_targeted'" not in pipeline_source
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": RETRIEVE_TARGETED}
    ).authorized_action_name is None
    assert "RECOVER_MISSING_SOURCE_CLASS" in spine_source
    assert "RECOVER_WEAK_CORPUS" in spine_source
    assert "RESOLVE_CONFLICT" in spine_source

    for node in ast.walk(pipeline_tree):
        if not isinstance(node, ast.Compare):
            continue
        left_is_authorized_spine_action = (
            isinstance(node.left, ast.Name)
            and node.left.id == "authorized_spine_action"
        )
        compares_to_retrieve_targeted = any(
            isinstance(comparator, ast.Constant)
            and comparator.value == RETRIEVE_TARGETED
            for comparator in node.comparators
        )
        assert not (
            left_is_authorized_spine_action and compares_to_retrieve_targeted
        )


def test_ag44b_static_guard_ordinary_candidate_does_not_relabel_bounded_lanes() -> None:
    source = _PIPELINE_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")

    assert "weak_corpus_recovery_queries = list(" in source
    assert "run_source_class_recovery_dispatch(" in source
    assert "execute_source_class_recovery_action(" in runner_source
    assert "execute_conflict_resolution_action(" in source
    assert "conflict_resolving_queries=conflict_resolving_queries" in source
    assert "ordinary_next_queries=conflict_resolving_queries" not in source
    assert "approved_ordinary_next_queries=conflict_resolving_queries" not in source
