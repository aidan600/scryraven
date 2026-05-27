from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
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
    mark_ordinary_continuation_candidate_spine_authorized,
)
from core.retrieval_batch_projection import (
    CONFLICT_RESOLVING_QUERIES,
    ORDINARY_EVALUATOR_GAP_QUERIES,
    ORDINARY_EXPANDER_COMPONENT_QUERIES,
    ORDINARY_SCOUT_DIRECTED_QUERIES,
    RETRIEVAL_BATCH_PROJECTION_TRACE_KEY,
    SOURCE_CLASS_RECOVERY_QUERIES,
    WEAK_CORPUS_RECOVERY_QUERIES,
    build_retrieval_batch_projection_trace,
    retrieval_batch_projection_defaults,
)
from tests.test_evidence_integration_conflict_gate_ag37b import (
    _force_checkpoint_action,
    _inject_conflict_evidence_state,
)
from tests.test_ordinary_continuation_ownership_ag44a import (
    _provider_roles,
)
from tests.test_source_class_recovery_trace import _run_case as _run_source_case
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

_ROOT = Path(__file__).resolve().parents[1]
_PROJECTION_PATH = _ROOT / "core" / "retrieval_batch_projection.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _inner(trace: dict[str, Any]) -> dict[str, Any]:
    return trace["RetrievalBatchProjection"]


def _checkpoint(
    *,
    action: str = RETRIEVE_TARGETED,
    authorized: str | None = RETRIEVE_TARGETED,
    dispatch_authorized: bool = True,
) -> dict[str, Any]:
    return {
        "available": True,
        "checkpoint_action_name": action,
        "promoted_action_name": authorized,
        "authorized_action_name": authorized,
        "checkpoint_decision_count": 1,
        "targeted_retrieval_dispatch_authorized": dispatch_authorized,
        "targeted_retrieval_executor_dispatched": False,
        "blocked_or_skipped_actions": {},
    }


def _ordinary(source_path: str, queries: tuple[str, ...]) -> dict[str, Any]:
    candidate = build_ordinary_continuation_candidate(
        source_path=source_path,
        ordinary_next_queries=queries,
        query_provenance=source_path,
        prior_queries=("already searched",),
        conflict_resolving_queries=(),
        current_iteration=1,
        max_iterations=3,
        considered=True,
    ).to_dict()
    return mark_ordinary_continuation_candidate_spine_authorized(
        candidate,
        used=True,
    )


@pytest.mark.parametrize(
    ("source_path", "lane_type", "query_owner"),
    [
        (
            EVALUATOR_NEXT_QUERIES,
            ORDINARY_EVALUATOR_GAP_QUERIES,
            "evaluator",
        ),
        (
            EXPANDER_COMPONENT_QUERIES,
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
            "expander",
        ),
        (
            SCOUT_DIRECTED_QUERIES,
            ORDINARY_SCOUT_DIRECTED_QUERIES,
            "scout",
        ),
    ],
)
def test_ag46b_authorized_ordinary_continuation_lanes_map_by_source(
    source_path: str,
    lane_type: str,
    query_owner: str,
) -> None:
    trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(
            source_path,
            ("Acme Widget evidence gap",),
        ),
        targeted_retrieval_lifecycle_trace={
            "targeted_retrieval_candidate_considered": True,
            "targeted_retrieval_candidate_eligible": True,
            "targeted_retrieval_candidate_used": True,
            "targeted_retrieval_candidate_queries": [
                "Acme Widget evidence gap"
            ],
            "targeted_retrieval_candidate_query_provenance": source_path,
            "targeted_retrieval_candidate_blockers": [],
        },
    )
    projection = _inner(trace)

    assert projection["batch_status"] == "authorized"
    assert projection["selected_lane"] == lane_type
    assert projection["provider_policy_unchanged"] is True
    assert projection["depth_policy_unchanged"] is True
    assert projection["query_generation_unchanged"] is True
    assert projection["prompt_unchanged"] is True
    assert projection["runtime_behavior_changed"] is False
    assert projection["targeted_retrieval_executor_dispatched"] is False
    assert projection["retrieve_targeted_provider_role_used"] is False
    lane = projection["lanes"][0]
    assert lane["lane_type"] == lane_type
    assert lane["query_generation_owner"] == query_owner
    assert lane["approved_queries"] == ["Acme Widget evidence gap"]
    assert lane["conflict_resolving_queries"] == []
    assert lane["status"] == "authorized"


def test_ag46b_defaults_are_safe_not_applicable_projection() -> None:
    projection = _inner(retrieval_batch_projection_defaults())

    assert projection["batch_status"] == "not_applicable"
    assert projection["selected_lane"] is None
    assert projection["authorized_lane_count"] == 0
    assert projection["provider_policy_unchanged"] is True
    assert projection["runtime_behavior_changed"] is False
    assert projection["authorization"]["dispatch_authorized"] is False


def test_ag46b_source_class_recovery_remains_higher_priority_lane() -> None:
    projection = _inner(
        build_retrieval_batch_projection_trace(
            checkpoint_trace=_checkpoint(
                action=RECOVER_MISSING_SOURCE_CLASS,
                authorized=RECOVER_MISSING_SOURCE_CLASS,
                dispatch_authorized=False,
            ),
            ordinary_continuation_candidate_trace=_ordinary(
                EVALUATOR_NEXT_QUERIES,
                ("ordinary query",),
            ),
            source_class_lifecycle_trace={
                "active_source_class_recovery_considered": True,
                "active_source_class_recovery_eligible": True,
                "active_source_class_recovery_used": True,
                "active_source_class_recovery_queries": [
                    "official eligibility source"
                ],
                "active_source_class_recovery_missing_classes": [
                    "official"
                ],
            },
        )
    )

    assert projection["selected_lane"] == SOURCE_CLASS_RECOVERY_QUERIES
    lanes = {lane["lane_type"]: lane for lane in projection["lanes"]}
    assert lanes[SOURCE_CLASS_RECOVERY_QUERIES]["status"] == "authorized"
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["status"] == "blocked"
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["approved_queries"] == []


def test_ag46b_weak_corpus_recovery_remains_higher_priority_lane() -> None:
    projection = _inner(
        build_retrieval_batch_projection_trace(
            checkpoint_trace=_checkpoint(
                action=RECOVER_WEAK_CORPUS,
                authorized=RECOVER_WEAK_CORPUS,
                dispatch_authorized=False,
            ),
            ordinary_continuation_candidate_trace=_ordinary(
                EXPANDER_COMPONENT_QUERIES,
                ("ordinary component query",),
            ),
            weak_corpus_lifecycle_trace={
                "weak_corpus_recovery_considered": True,
                "weak_corpus_recovery_used": True,
                "weak_corpus_recovery_queries": ["broader evidence query"],
            },
        )
    )

    assert projection["selected_lane"] == WEAK_CORPUS_RECOVERY_QUERIES
    lanes = {lane["lane_type"]: lane for lane in projection["lanes"]}
    assert lanes[WEAK_CORPUS_RECOVERY_QUERIES]["status"] == "authorized"
    assert lanes[ORDINARY_EXPANDER_COMPONENT_QUERIES]["status"] == "blocked"


def test_ag46b_conflict_resolving_queries_remain_separate_from_ordinary() -> None:
    ordinary = build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=("ordinary background query",),
        query_provenance=EVALUATOR_NEXT_QUERIES,
        conflict_resolving_queries=("official corrected date",),
        current_iteration=1,
        max_iterations=3,
        considered=True,
    ).to_dict()
    projection = _inner(
        build_retrieval_batch_projection_trace(
            checkpoint_trace=_checkpoint(
                action=RESOLVE_CONFLICT,
                authorized=RESOLVE_CONFLICT,
                dispatch_authorized=False,
            ),
            ordinary_continuation_candidate_trace=ordinary,
            conflict_resolution_lifecycle_trace={
                "active_conflict_resolution_considered": True,
                "active_conflict_resolution_eligible": True,
                "active_conflict_resolution_used": True,
                "active_conflict_resolution_queries": [
                    "official corrected date"
                ],
            },
        )
    )
    lanes = {lane["lane_type"]: lane for lane in projection["lanes"]}

    assert projection["selected_lane"] == CONFLICT_RESOLVING_QUERIES
    assert lanes[CONFLICT_RESOLVING_QUERIES]["approved_queries"] == [
        "official corrected date"
    ]
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["approved_queries"] == []
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES][
        "conflict_resolving_queries"
    ] == ["official corrected date"]


def test_ag46b_blocked_targeted_lifecycle_does_not_dispatch_substitute() -> None:
    projection = _inner(
        build_retrieval_batch_projection_trace(
            checkpoint_trace=_checkpoint(
                action=RETRIEVE_TARGETED,
                authorized=None,
                dispatch_authorized=False,
            ),
            ordinary_continuation_candidate_trace={
                **_ordinary(SCOUT_DIRECTED_QUERIES, ("directed query",)),
                "currently_spine_authorized": False,
                "used": False,
            },
            targeted_retrieval_lifecycle_trace={
                "targeted_retrieval_candidate_considered": True,
                "targeted_retrieval_candidate_eligible": False,
                "targeted_retrieval_candidate_used": False,
                "targeted_retrieval_candidate_blockers": [
                    "blocked_by_provider_policy_change_required"
                ],
            },
        )
    )

    assert projection["batch_status"] == "blocked"
    assert projection["authorized_lane_count"] == 0
    assert projection["targeted_retrieval_executor_dispatched"] is False
    assert projection["retrieve_targeted_provider_role_used"] is False
    lane = projection["lanes"][0]
    assert lane["lane_type"] == ORDINARY_SCOUT_DIRECTED_QUERIES
    assert lane["status"] == "blocked"
    assert lane["approved_queries"] == []


def test_ag46b_projection_is_json_safe_and_sanitized() -> None:
    trace = build_retrieval_batch_projection_trace(
        checkpoint_trace={
            **_checkpoint(),
            "raw_prompt": "raw prompt: secret instruction",
        },
        ordinary_continuation_candidate_trace={
            **_ordinary(EVALUATOR_NEXT_QUERIES, ("  query   text  ",)),
            "raw_provider_payload": {"token": "secret"},
        },
    )
    serialized = json.dumps(trace, sort_keys=True)

    assert "raw prompt: secret instruction" not in serialized
    assert "raw_provider_payload" not in serialized
    assert "secret" not in serialized
    assert "query text" in serialized


@pytest.mark.parametrize(
    ("name", "harness_kwargs", "expected_lane"),
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
        ),
        (
            "expander",
            {
                "expander_queries": (
                    "Acme Widget component warranty evidence",
                ),
            },
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
        ),
        (
            "scout",
            {
                "router_report_type": "quantitative_comparison",
                "scout_queries": ("Acme Widget benchmark adoption data",),
            },
            ORDINARY_SCOUT_DIRECTED_QUERIES,
        ),
    ],
)
def test_ag46b_runtime_trace_includes_passive_projection_for_ordinary_lanes(
    tmp_path: Path,
    name: str,
    harness_kwargs: dict[str, Any],
    expected_lane: str,
) -> None:
    outcome, harness = _run_passive_case(tmp_path / name, **harness_kwargs)
    trace = outcome.execution_trace
    projection_trace = trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    projection = _inner(projection_trace)
    checkpoint = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert checkpoint[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY] == projection_trace
    assert projection["selected_lane"] == expected_lane
    assert projection["batch_status"] == "authorized"
    assert projection["authorization"]["dispatch_authorized"] is True
    assert projection["provider_policy_unchanged"] is True
    assert projection["depth_policy_unchanged"] is True
    assert projection["runtime_behavior_changed"] is False
    assert projection["targeted_retrieval_executor_dispatched"] is False
    assert projection["retrieve_targeted_provider_role_used"] is False
    assert projection["authorized_action_name"] == RETRIEVE_TARGETED
    assert len(harness.search_calls) == 2
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert [call["search_depth"] for call in harness.search_calls] == [
        "basic",
        "basic",
    ]
    assert trace["queries_per_iteration"]["2"] == harness.search_calls[1][
        "queries"
    ]
    assert trace["final_output_preview"]


def test_ag46b_runtime_source_class_blocks_ordinary_without_relabeling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)
    outcome, harness, _log_entry = _run_source_case(
        tmp_path,
        query="What are the current official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    projection = _inner(
        outcome.execution_trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    )

    assert projection["selected_lane"] == SOURCE_CLASS_RECOVERY_QUERIES
    assert "source_class_recovery" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag46b_runtime_weak_corpus_blocks_ordinary_without_relabeling(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path)
    projection = _inner(
        outcome.execution_trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    )

    assert projection["selected_lane"] == WEAK_CORPUS_RECOVERY_QUERIES
    assert "weak_corpus_recovery" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag46b_runtime_conflict_keeps_resolving_queries_separate(
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
    projection = _inner(
        outcome.execution_trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    )
    lanes = {lane["lane_type"]: lane for lane in projection["lanes"]}

    assert projection["selected_lane"] == CONFLICT_RESOLVING_QUERIES
    assert lanes[CONFLICT_RESOLVING_QUERIES][
        "conflict_resolving_queries"
    ] == ["Care Program official corrected date"]
    assert lanes.get(ORDINARY_EVALUATOR_GAP_QUERIES, {}).get(
        "approved_queries",
        [],
    ) == []
    assert "conflict_resolution" in _provider_roles(harness)
    assert "retrieve_targeted" not in _provider_roles(harness)


def test_ag46b_static_projection_module_keeps_protected_imports_out() -> None:
    source = _PROJECTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "core.pipeline_orchestrator",
        "core.providers",
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
    assert "provider_role = \"retrieve_targeted\"" not in source


def test_ag46b_static_controller_loop_spine_remains_outside_projection() -> None:
    source = _SPINE_PATH.read_text(encoding="utf-8")

    assert "retrieval_batch_projection" not in source
    assert "RetrievalBatchProjection" not in source
    assert RETRIEVAL_BATCH_PROJECTION_TRACE_KEY not in source
    assert "build_retrieval_batch_projection_trace" not in source


def test_ag46b_runtime_projection_does_not_change_existing_dispatch_surfaces(
    tmp_path: Path,
) -> None:
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

    assert len(harness.search_calls) == 2
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert [call["queries"] for call in harness.search_calls] == [
        trace["queries_per_iteration"]["1"],
        trace["queries_per_iteration"]["2"],
    ]
    assert [call["search_depth"] for call in harness.search_calls] == [
        "basic",
        "basic",
    ]
    assert trace["targeted_retrieval_candidate_used"] is True
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        EVALUATOR_NEXT_QUERIES
    )
    assert trace["final_output_preview"]
    projection = _inner(trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY])
    assert projection["query_count"] == len(trace["queries_per_iteration"]["2"])
    assert projection["runtime_behavior_changed"] is False
