from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    SCOUT_DIRECTED_QUERIES,
)
from core.retrieval_batch_authorization_readiness import (
    assess_retrieval_batch_authorization_readiness,
)
from core.retrieval_batch_dispatch import (
    RETRIEVAL_BATCH_DISPATCH_TRACE_KEY,
    build_retrieval_batch_dispatch_decision,
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
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)
from tests.test_retrieval_batch_projection_ag46b import (
    _checkpoint,
    _inner,
    _ordinary,
)

_ROOT = Path(__file__).resolve().parents[1]
_CORE_PATHS = [
    _ROOT / "core" / "retrieval_batch_projection.py",
    _ROOT / "core" / "retrieval_batch_dispatch.py",
    _ROOT / "core" / "runtime_trace_projection_assembly.py",
]
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _dispatch_trace(
    *,
    source_path: str = EVALUATOR_NEXT_QUERIES,
    queries: tuple[str, ...] = ("NASA Artemis II current launch status",),
) -> dict[str, Any]:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(source_path, queries),
    )
    readiness_trace = assess_retrieval_batch_authorization_readiness(
        projection_trace
    )
    return build_retrieval_batch_dispatch_decision(
        projection_trace=projection_trace,
        readiness_trace=readiness_trace,
    ).to_trace()


def _final_style_trace(
    *,
    source_path: str = EVALUATOR_NEXT_QUERIES,
    queries: tuple[str, ...] = ("NASA Artemis II current launch status",),
    dispatch_trace: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    source_class_trace: dict[str, Any] | None = None,
    weak_corpus_trace: dict[str, Any] | None = None,
    conflict_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: checkpoint
        or _checkpoint(authorized=None, dispatch_authorized=False),
        "ordinary_continuation_candidate": {
            **_ordinary(source_path, queries),
            "currently_spine_authorized": False,
            "used": False,
        },
        "targeted_retrieval_candidate_considered": True,
        "targeted_retrieval_candidate_eligible": False,
        "targeted_retrieval_candidate_used": False,
        "targeted_retrieval_candidate_queries": list(queries),
        "targeted_retrieval_candidate_blockers": [
            "missing_current_primary_source",
            "news_source_fit_missing",
        ],
        "targeted_retrieval_candidate_reason": "currentness_blocked",
        "evaluator_continuation_spine_gate_trace": {
            "targeted_retrieval_dispatch_authorized": False,
        },
        RETRIEVAL_BATCH_DISPATCH_TRACE_KEY: dispatch_trace or {},
    }
    trace.update(
        source_class_trace
        or {
            "active_source_class_recovery_considered": True,
            "active_source_class_recovery_eligible": False,
            "active_source_class_recovery_used": False,
            "active_source_class_recovery_missing_classes": ["official"],
            "active_source_class_recovery_blockers": [
                "not_recommended",
                "blocked_by_iteration_budget",
            ],
            "active_source_class_recovery_reason": "official_source_gap",
        }
    )
    trace.update(weak_corpus_trace or {})
    trace.update(conflict_trace or {})
    return trace


def _attach_projection(trace: dict[str, Any]) -> dict[str, Any]:
    attach_passive_runtime_projection_traces(trace)
    return _inner(trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY])


def _readiness_from_projection(projection: dict[str, Any]) -> dict[str, Any]:
    readiness_trace = assess_retrieval_batch_authorization_readiness(
        {"RetrievalBatchProjection": projection}
    )
    return readiness_trace["RetrievalBatchAuthorizationReadiness"]


def _lane(projection: dict[str, Any], lane_type: str) -> dict[str, Any]:
    return {
        lane["lane_type"]: lane
        for lane in projection["lanes"]
    }[lane_type]


def test_ag47c_reproduces_q3_style_mismatch_without_dispatch_overlay() -> None:
    trace = _final_style_trace()
    projection = _inner(build_retrieval_batch_projection_trace(runtime_trace=trace))

    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY] == {}
    assert projection["batch_status"] == "blocked"
    assert projection["selected_lane"] is None
    assert "missing_current_primary_source" in projection["batch_blockers"]
    assert "news_source_fit_missing" in projection["batch_blockers"]


def test_ag47c_final_trace_no_longer_contradicts_authorized_dispatch() -> None:
    dispatch = _dispatch_trace()
    trace = _final_style_trace(dispatch_trace=dispatch)

    projection = _attach_projection(trace)
    readiness = _readiness_from_projection(projection)

    assert dispatch["dispatch_authorized"] is True
    assert projection["batch_status"] == "authorized"
    assert projection["selected_lane"] == ORDINARY_EVALUATOR_GAP_QUERIES
    assert projection["authorization"]["dispatch_authorized"] is True
    assert readiness["ready_for_active_batch_dispatch"] is True
    assert readiness["selected_authorized_lane"]["lane_type"] == (
        ORDINARY_EVALUATOR_GAP_QUERIES
    )


def test_ag47c_dispatch_authorized_evaluator_lane_stays_selected_visible() -> None:
    dispatch = _dispatch_trace()
    projection = _attach_projection(_final_style_trace(dispatch_trace=dispatch))

    selected_lane = _lane(projection, ORDINARY_EVALUATOR_GAP_QUERIES)

    assert projection["selected_lane"] == dispatch["selected_lane_id"]
    assert selected_lane["status"] == "authorized"
    assert selected_lane["approved_queries"] == dispatch["authorized_queries"]
    assert selected_lane["blockers"] == []


def test_ag47c_source_class_and_currentness_blockers_remain_visible() -> None:
    dispatch = _dispatch_trace()
    projection = _attach_projection(_final_style_trace(dispatch_trace=dispatch))

    source_lane = _lane(projection, SOURCE_CLASS_RECOVERY_QUERIES)

    assert source_lane["status"] == "blocked"
    assert source_lane["blockers"] == [
        "not_recommended",
        "blocked_by_iteration_budget",
    ]
    assert "missing_current_primary_source" in projection["batch_blockers"]
    assert "news_source_fit_missing" in projection["batch_blockers"]
    assert _lane(projection, ORDINARY_EVALUATOR_GAP_QUERIES)["blockers"] == []


@pytest.mark.parametrize(
    ("source_path", "lane_type", "queries"),
    [
        (
            EXPANDER_COMPONENT_QUERIES,
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
            ("Artemis II Orion hardware current status",),
        ),
        (
            SCOUT_DIRECTED_QUERIES,
            ORDINARY_SCOUT_DIRECTED_QUERIES,
            ("Artemis II crew milestone watch items",),
        ),
    ],
)
def test_ag47c_expander_and_scout_authorized_paths_stay_consistent(
    source_path: str,
    lane_type: str,
    queries: tuple[str, ...],
) -> None:
    dispatch = _dispatch_trace(source_path=source_path, queries=queries)
    projection = _attach_projection(
        _final_style_trace(
            source_path=source_path,
            queries=queries,
            dispatch_trace=dispatch,
        )
    )
    readiness = _readiness_from_projection(projection)

    assert projection["selected_lane"] == lane_type
    assert _lane(projection, lane_type)["approved_queries"] == list(queries)
    assert readiness["ready_for_active_batch_dispatch"] is True
    assert readiness["selected_authorized_lane"]["lane_type"] == lane_type


def test_ag47c_blocked_dispatch_remains_blocked_with_projection_readiness() -> None:
    trace = _final_style_trace(
        dispatch_trace=build_retrieval_batch_dispatch_decision(
            projection_trace=build_retrieval_batch_projection_trace(
                runtime_trace=_final_style_trace()
            )
        ).to_trace()
    )

    projection = _attach_projection(trace)
    readiness = _readiness_from_projection(projection)

    assert trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY]["dispatch_authorized"] is False
    assert projection["batch_status"] == "blocked"
    assert projection["selected_lane"] is None
    assert readiness["ready_for_active_batch_dispatch"] is False


@pytest.mark.parametrize(
    ("action", "lane_type", "extra_trace"),
    [
        (
            RECOVER_MISSING_SOURCE_CLASS,
            SOURCE_CLASS_RECOVERY_QUERIES,
            {
                "active_source_class_recovery_considered": True,
                "active_source_class_recovery_eligible": True,
                "active_source_class_recovery_used": True,
                "active_source_class_recovery_queries": [
                    "NASA Artemis II official status"
                ],
                "active_source_class_recovery_missing_classes": ["official"],
            },
        ),
        (
            RECOVER_WEAK_CORPUS,
            WEAK_CORPUS_RECOVERY_QUERIES,
            {
                "weak_corpus_recovery_considered": True,
                "weak_corpus_recovery_used": True,
                "weak_corpus_recovery_queries": [
                    "NASA Artemis II official mission status"
                ],
            },
        ),
        (
            RESOLVE_CONFLICT,
            CONFLICT_RESOLVING_QUERIES,
            {
                "active_conflict_resolution_considered": True,
                "active_conflict_resolution_eligible": True,
                "active_conflict_resolution_used": True,
                "active_conflict_resolution_queries": [
                    "NASA Artemis II launch date conflict"
                ],
            },
        ),
    ],
)
def test_ag47c_separate_selected_paths_are_not_relabelled_as_ordinary(
    action: str,
    lane_type: str,
    extra_trace: dict[str, Any],
) -> None:
    trace = _final_style_trace(
        checkpoint=_checkpoint(action=action, authorized=action),
        source_class_trace={},
        dispatch_trace={"dispatch_authorized": False},
    )
    trace.update(extra_trace)

    projection = _attach_projection(trace)

    assert projection["selected_lane"] == lane_type
    assert _lane(projection, lane_type)["status"] == "authorized"
    assert projection["selected_lane"] not in {
        ORDINARY_EVALUATOR_GAP_QUERIES,
        ORDINARY_EXPANDER_COMPONENT_QUERIES,
        ORDINARY_SCOUT_DIRECTED_QUERIES,
    }


def test_ag47c_conflict_and_ordinary_queries_remain_distinct() -> None:
    trace = _final_style_trace(
        checkpoint=_checkpoint(action=RESOLVE_CONFLICT, authorized=RESOLVE_CONFLICT),
        source_class_trace={},
        conflict_trace={
            "active_conflict_resolution_considered": True,
            "active_conflict_resolution_eligible": True,
            "active_conflict_resolution_used": True,
            "active_conflict_resolution_queries": [
                "NASA Artemis II official launch conflict"
            ],
        },
        dispatch_trace={"dispatch_authorized": False},
    )

    projection = _attach_projection(trace)
    conflict_lane = _lane(projection, CONFLICT_RESOLVING_QUERIES)
    ordinary_lane = _lane(projection, ORDINARY_EVALUATOR_GAP_QUERIES)

    assert projection["selected_lane"] == CONFLICT_RESOLVING_QUERIES
    assert conflict_lane["conflict_resolving_queries"] == [
        "NASA Artemis II official launch conflict"
    ]
    assert ordinary_lane["approved_queries"] == []
    assert ordinary_lane["conflict_resolving_queries"] == []


def test_ag47c_static_guard_no_provider_routing_prompt_or_sensitive_imports() -> None:
    forbidden_modules = {
        "core.provider",
        "core.providers",
        "core.router",
        "core.routing",
        "core.prompt",
        "core.prompts",
        "core.cache",
        "core.db",
        "core.database",
        "core.output",
        "core.secrets",
    }
    for path in _CORE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imported.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert imported.isdisjoint(forbidden_modules), path


def test_ag47c_static_guard_no_retrieve_targeted_provider_role_string() -> None:
    joined = "\n".join(path.read_text(encoding="utf-8") for path in _CORE_PATHS)

    forbidden_fragments = [
        'provider_role="retrieve_targeted"',
        "provider_role='retrieve_targeted'",
        '"provider_role": "retrieve_targeted"',
        "'provider_role': 'retrieve_targeted'",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in joined


def test_ag47c_static_guard_no_targeted_executor_introduced() -> None:
    joined = "\n".join(path.read_text(encoding="utf-8") for path in _CORE_PATHS)

    assert "execute_retrieve_targeted_action" not in joined
    assert "class RetrieveTargetedExecutor" not in joined


def test_ag47c_static_guard_controller_loop_spine_not_changed_for_ag47c() -> None:
    source = _SPINE_PATH.read_text(encoding="utf-8")

    assert "dispatch_projection_consistency" not in source
    assert "RETRIEVAL_BATCH_DISPATCH_TRACE_KEY" not in source
