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
    STOP_SUFFICIENT,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
    mark_ordinary_continuation_candidate_spine_authorized,
)
from core.retrieval_batch_authorization_readiness import (
    assess_retrieval_batch_authorization_readiness,
)
from core.retrieval_batch_dispatch import (
    RETRIEVAL_BATCH_DISPATCH_TRACE_KEY,
    RUNTIME_BEHAVIOR_CONTRACT,
    RetrievalBatchDispatchDecision,
    build_retrieval_batch_dispatch_decision,
)
from core.retrieval_batch_projection import (
    CONFLICT_RESOLVING_QUERIES,
    ORDINARY_EVALUATOR_GAP_QUERIES,
    ORDINARY_EXPANDER_COMPONENT_QUERIES,
    ORDINARY_SCOUT_DIRECTED_QUERIES,
    SOURCE_CLASS_RECOVERY_QUERIES,
    WEAK_CORPUS_RECOVERY_QUERIES,
    build_retrieval_batch_projection_trace,
)
from tests.test_evidence_integration_conflict_gate_ag37b import _decision
from tests.test_retrieval_batch_projection_ag46b import (
    _checkpoint,
    _inner,
    _ordinary,
)
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_DISPATCH_PATH = _ROOT / "core" / "retrieval_batch_dispatch.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _readiness(projection_trace: dict[str, Any]) -> dict[str, Any]:
    return assess_retrieval_batch_authorization_readiness(projection_trace)


def _decision_for_projection(projection_trace: dict[str, Any]):
    return build_retrieval_batch_dispatch_decision(
        projection_trace=projection_trace,
        readiness_trace=_readiness(projection_trace),
    )


@pytest.mark.parametrize(
    ("source_path", "lane_type", "queries"),
    [
        (
            EVALUATOR_NEXT_QUERIES,
            ORDINARY_EVALUATOR_GAP_QUERIES,
            ("Acme Widget migration timeline",),
        ),
        (
            EXPANDER_COMPONENT_QUERIES,
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
            ("Acme Widget component warranty evidence",),
        ),
        (
            SCOUT_DIRECTED_QUERIES,
            ORDINARY_SCOUT_DIRECTED_QUERIES,
            ("Acme Widget benchmark adoption data",),
        ),
    ],
)
def test_ag47a_dispatch_helper_authorizes_existing_ordinary_lane(
    source_path: str,
    lane_type: str,
    queries: tuple[str, ...],
) -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(source_path, queries),
    )

    decision = _decision_for_projection(projection_trace)

    assert decision.dispatch_authorized is True
    assert decision.selected_lane == lane_type
    assert decision.selected_lane_type == lane_type
    assert decision.query_provenance == source_path
    assert decision.authorized_queries == queries
    assert decision.runtime_behavior_contract == RUNTIME_BEHAVIOR_CONTRACT
    trace = decision.to_trace()
    assert trace["targeted_retrieval_executor_dispatched"] is False
    assert trace["retrieve_targeted_provider_role_used"] is False


def test_ag47a_dispatch_helper_rejects_multiple_authorized_ordinary_lanes() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget migration timeline",),
        ),
    )
    projection = _inner(projection_trace)
    extra_lane = dict(projection["lanes"][0])
    extra_lane["lane_id"] = ORDINARY_EXPANDER_COMPONENT_QUERIES
    extra_lane["lane_type"] = ORDINARY_EXPANDER_COMPONENT_QUERIES
    projection["lanes"].append(extra_lane)
    projection["authorized_lane_count"] = 2

    decision = _decision_for_projection(projection_trace)

    assert decision.dispatch_authorized is False
    assert "multiple_authorized_lanes" in decision.blockers
    assert "authorized_lane_count_not_one" in decision.blockers


def test_ag47a_dispatch_helper_rejects_terminal_stop() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=STOP_SUFFICIENT,
            authorized=None,
            dispatch_authorized=False,
        ),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget migration timeline",),
        ),
    )

    decision = _decision_for_projection(projection_trace)

    assert decision.dispatch_authorized is False
    assert "terminal_stop_blocks_batch_authorization" in decision.blockers
    assert decision.authorized_queries == ()


@pytest.mark.parametrize(
    ("checkpoint_action", "lane_type", "extra_trace"),
    [
        (
            RECOVER_MISSING_SOURCE_CLASS,
            SOURCE_CLASS_RECOVERY_QUERIES,
            {
                "source_class_lifecycle_trace": {
                    "active_source_class_recovery_considered": True,
                    "active_source_class_recovery_eligible": True,
                    "active_source_class_recovery_used": True,
                    "active_source_class_recovery_queries": ["official source"],
                    "active_source_class_recovery_missing_classes": ["official"],
                }
            },
        ),
        (
            RECOVER_WEAK_CORPUS,
            WEAK_CORPUS_RECOVERY_QUERIES,
            {
                "weak_corpus_lifecycle_trace": {
                    "weak_corpus_recovery_considered": True,
                    "weak_corpus_recovery_used": True,
                    "weak_corpus_recovery_queries": ["broader evidence query"],
                }
            },
        ),
        (
            RESOLVE_CONFLICT,
            CONFLICT_RESOLVING_QUERIES,
            {
                "conflict_resolution_lifecycle_trace": {
                    "active_conflict_resolution_considered": True,
                    "active_conflict_resolution_eligible": True,
                    "active_conflict_resolution_used": True,
                    "active_conflict_resolution_queries": ["official corrected date"],
                }
            },
        ),
    ],
)
def test_ag47a_dispatch_helper_rejects_separate_action_lanes(
    checkpoint_action: str,
    lane_type: str,
    extra_trace: dict[str, Any],
) -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=checkpoint_action,
            authorized=checkpoint_action,
            dispatch_authorized=False,
        ),
        **extra_trace,
    )

    decision = _decision_for_projection(projection_trace)

    assert _inner(projection_trace)["selected_lane"] == lane_type
    assert decision.dispatch_authorized is False
    assert decision.selected_lane_type == lane_type
    assert "selected_lane_not_ordinary_continuation" in decision.blockers


def test_ag47a_dispatch_helper_preserves_ordinary_conflict_query_separation() -> None:
    ordinary = build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=("ordinary background query",),
        query_provenance=EVALUATOR_NEXT_QUERIES,
        conflict_resolving_queries=("official corrected date",),
        current_iteration=1,
        max_iterations=3,
        considered=True,
    ).to_dict()
    ordinary = mark_ordinary_continuation_candidate_spine_authorized(
        ordinary,
        used=True,
    )
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=ordinary,
    )

    decision = _decision_for_projection(projection_trace)

    assert decision.dispatch_authorized is False
    assert decision.authorized_queries == ()
    assert "ordinary_conflict_query_separation_failed" in decision.blockers


def test_ag47a_dispatch_helper_exposes_blocked_readiness_rationale() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=STOP_SUFFICIENT,
            authorized=None,
            dispatch_authorized=False,
        ),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget migration timeline",),
        ),
    )

    decision = _decision_for_projection(projection_trace)
    trace = decision.to_trace()

    assert decision.dispatch_authorized is False
    assert decision.blocked_reason == "terminal_stop_blocks_batch_authorization"
    assert trace["readiness_status"] is False
    assert trace["blockers"]


@pytest.mark.parametrize(
    ("name", "harness_kwargs", "expected_lane", "expected_queries"),
    [
        (
            "evaluator",
            {
                "evaluator_responses": [
                    {
                        "is_sufficient": False,
                        "new_queries": ["Acme Widget migration timeline"],
                    }
                ],
            },
            ORDINARY_EVALUATOR_GAP_QUERIES,
            ["Acme Widget migration timeline"],
        ),
        (
            "expander",
            {
                "expander_queries": (
                    "Acme Widget component warranty evidence",
                    "Acme Widget component rollout evidence",
                ),
            },
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
            [
                "Acme Widget component warranty evidence",
                "Acme Widget component rollout evidence",
            ],
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
            ORDINARY_SCOUT_DIRECTED_QUERIES,
            [
                "Acme Widget benchmark adoption data",
                "Acme Widget benchmark support matrix",
            ],
        ),
    ],
)
def test_ag47a_runtime_ordinary_continuation_uses_batch_dispatch_decision(
    tmp_path: Path,
    name: str,
    harness_kwargs: dict[str, Any],
    expected_lane: str,
    expected_queries: list[str],
) -> None:
    outcome, harness = _run_passive_case(tmp_path / name, **harness_kwargs)
    trace = outcome.execution_trace
    dispatch = trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]

    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == expected_queries
    assert harness.search_calls[1]["provider_role"] == "main_retrieval"
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert trace["queries_per_iteration"]["2"] == expected_queries
    assert trace["final_output_preview"]
    assert dispatch["dispatch_authorized"] is True
    assert dispatch["selected_lane_type"] == expected_lane
    assert dispatch["authorized_queries"] == expected_queries
    assert dispatch["provider_policy_unchanged"] is True
    assert dispatch["depth_policy_unchanged"] is True
    assert dispatch["query_generation_unchanged"] is True
    assert dispatch["targeted_retrieval_executor_dispatched"] is False
    assert "retrieve_targeted" not in {
        call["provider_role"] for call in harness.search_calls
    }
    assert trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
        RETRIEVAL_BATCH_DISPATCH_TRACE_KEY
    ] == dispatch


def test_ag47a_runtime_blocked_batch_does_not_dispatch_substitute_retrieval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocked = RetrievalBatchDispatchDecision(
        considered=True,
        dispatch_authorized=False,
        selected_lane=ORDINARY_EVALUATOR_GAP_QUERIES,
        selected_lane_type=ORDINARY_EVALUATOR_GAP_QUERIES,
        query_provenance=EVALUATOR_NEXT_QUERIES,
        authorized_queries=(),
        blocked_reason="forced_readiness_block",
        blockers=("forced_readiness_block",),
        readiness_summary={"ready_for_active_batch_dispatch": False},
        dispatch_owner="controller_loop_spine",
    )
    monkeypatch.setattr(
        orchestrator,
        "build_retrieval_batch_dispatch_decision",
        lambda *_args, **_kwargs: blocked,
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

    assert len(harness.search_calls) == 1
    assert "2" not in trace["queries_per_iteration"]
    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]["dispatch_authorized"] is False
    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]["blocked_reason"] == (
        "forced_readiness_block"
    )
    assert trace["targeted_retrieval_candidate_used"] is False


def test_ag47a_static_dispatch_helper_has_no_provider_or_runtime_coupling() -> None:
    source = _DISPATCH_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "core.pipeline_orchestrator",
        "core.providers",
        "core.retrieval",
        "core.routing",
        "core.search_providers",
        "core.prompts",
        "core.db",
        "core.cache",
        "core.output",
        "core.secrets",
        "core.source_class_recovery_executor",
        "core.conflict_resolution_executor",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert forbidden.isdisjoint(imported)
    assert "process_search_queries" not in source
    assert "run_pipeline" not in source


def test_ag47a_static_no_retrieve_targeted_provider_role_is_introduced() -> None:
    for path in (_DISPATCH_PATH, _PIPELINE_PATH):
        source = path.read_text(encoding="utf-8")
        assert 'provider_role="retrieve_targeted"' not in source
        assert "provider_role='retrieve_targeted'" not in source
        assert 'provider_role = "retrieve_targeted"' not in source
        assert "provider_role = 'retrieve_targeted'" not in source
        assert 'provider_role == "retrieve_targeted"' not in source
        assert "provider_role == 'retrieve_targeted'" not in source


def test_ag47a_static_no_targeted_executor_is_introduced() -> None:
    for path in (_DISPATCH_PATH, _PIPELINE_PATH):
        source = path.read_text(encoding="utf-8")
        assert "execute_retrieve_targeted_action" not in source
        assert "execute_targeted_retrieval" not in source


def test_ag47a_static_controller_loop_spine_remains_unchanged_boundary() -> None:
    source = _SPINE_PATH.read_text(encoding="utf-8")

    assert "retrieval_batch_dispatch" not in source
    assert RETRIEVAL_BATCH_DISPATCH_TRACE_KEY not in source
    assert build_retrieval_batch_dispatch_decision(
        projection_trace=build_retrieval_batch_projection_trace(
            checkpoint_trace=_checkpoint(),
            ordinary_continuation_candidate_trace=_ordinary(
                EVALUATOR_NEXT_QUERIES,
                ("Acme Widget migration timeline",),
            ),
        )
    ).dispatch_authorized is True


def test_ag47a_runtime_forced_conflict_checkpoint_does_not_use_batch_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(RESOLVE_CONFLICT),
    )

    outcome, harness = _run_passive_case(
        tmp_path,
        evaluator_responses=[
            {
                "is_sufficient": False,
                "new_queries": ["ordinary background query"],
            }
        ],
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 1
    assert "2" not in trace["queries_per_iteration"]
    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]["dispatch_authorized"] is False
    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]["considered"] is False
    assert trace["targeted_retrieval_candidate_used"] is False
    assert "retrieve_targeted" not in {
        call["provider_role"] for call in harness.search_calls
    }
