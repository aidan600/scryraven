from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_SUFFICIENT,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
)
from core.retrieval_batch_authorization_readiness import (
    assess_retrieval_batch_authorization_readiness,
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
from tests.test_retrieval_batch_projection_ag46b import (
    _checkpoint,
    _inner,
    _ordinary,
)

_ROOT = Path(__file__).resolve().parents[1]
_READINESS_PATH = _ROOT / "core" / "retrieval_batch_authorization_readiness.py"


def _readiness(projection_trace: dict[str, Any]) -> dict[str, Any]:
    trace = assess_retrieval_batch_authorization_readiness(projection_trace)
    return trace["RetrievalBatchAuthorizationReadiness"]


@pytest.mark.parametrize(
    ("source_path", "lane_type", "owner"),
    [
        (EVALUATOR_NEXT_QUERIES, ORDINARY_EVALUATOR_GAP_QUERIES, "evaluator"),
        (
            EXPANDER_COMPONENT_QUERIES,
            ORDINARY_EXPANDER_COMPONENT_QUERIES,
            "expander",
        ),
        (SCOUT_DIRECTED_QUERIES, ORDINARY_SCOUT_DIRECTED_QUERIES, "scout"),
    ],
)
def test_ag46d_authorized_ordinary_lanes_are_structurally_ready(
    source_path: str,
    lane_type: str,
    owner: str,
) -> None:
    projection_trace = build_retrieval_batch_projection_trace(
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

    readiness = _readiness(projection_trace)

    assert readiness["ready_for_active_batch_dispatch"] is True
    assert readiness["blockers"] == []
    assert readiness["represented_lanes"] == [lane_type]
    assert readiness["selected_authorized_lane"] == {
        "lane_id": lane_type,
        "lane_type": lane_type,
        "query_generation_owner": owner,
        "query_count": 1,
        "status": "authorized",
    }
    assert readiness["authorized_ordinary_lane_count"] == 1
    assert readiness["dispatch_owner"] == "controller_loop_spine"
    assert all(readiness["protected_surface_status"].values())


def test_ag46d_terminal_stop_blocks_ordinary_batch_authorization() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=STOP_SUFFICIENT,
            authorized=STOP_SUFFICIENT,
            dispatch_authorized=False,
        ),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget unnecessary follow-up",),
        ),
    )

    readiness = _readiness(projection_trace)
    projection = _inner(projection_trace)

    assert projection["selected_lane"] is None
    assert readiness["ready_for_active_batch_dispatch"] is False
    assert "terminal_stop_blocks_batch_authorization" in readiness["blockers"]
    assert "dispatch_not_authorized_by_spine" in readiness["blockers"]
    assert readiness["selected_authorized_lane"] is None


@pytest.mark.parametrize(
    ("action", "lane_type", "owner", "lifecycle_trace"),
    [
        (
            RECOVER_MISSING_SOURCE_CLASS,
            SOURCE_CLASS_RECOVERY_QUERIES,
            "source_class_controller",
            {
                "source_class_lifecycle_trace": {
                    "active_source_class_recovery_considered": True,
                    "active_source_class_recovery_eligible": True,
                    "active_source_class_recovery_used": True,
                    "active_source_class_recovery_queries": [
                        "official eligibility source"
                    ],
                }
            },
        ),
        (
            RECOVER_WEAK_CORPUS,
            WEAK_CORPUS_RECOVERY_QUERIES,
            "weak_corpus_controller",
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
            "conflict_controller",
            {
                "conflict_resolution_lifecycle_trace": {
                    "active_conflict_resolution_considered": True,
                    "active_conflict_resolution_eligible": True,
                    "active_conflict_resolution_used": True,
                    "active_conflict_resolution_queries": [
                        "official corrected date"
                    ],
                }
            },
        ),
    ],
)
def test_ag46d_recovery_and_conflict_lanes_remain_separate_not_ordinary_ready(
    action: str,
    lane_type: str,
    owner: str,
    lifecycle_trace: dict[str, Any],
) -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=action,
            authorized=action,
            dispatch_authorized=False,
        ),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("ordinary background query",),
        ),
        **lifecycle_trace,
    )

    readiness = _readiness(projection_trace)
    projection = _inner(projection_trace)
    lanes = {lane["lane_type"]: lane for lane in projection["lanes"]}

    assert projection["selected_lane"] == lane_type
    assert lanes[lane_type]["query_generation_owner"] == owner
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["status"] == "blocked"
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["approved_queries"] == []
    assert readiness["ready_for_active_batch_dispatch"] is False
    assert "selected_lane_not_ordinary_continuation" in readiness["blockers"]
    assert (
        readiness["protected_surface_status"][
            "separate_action_lanes_remain_bounded"
        ]
        is True
    )


def test_ag46d_conflict_resolving_queries_do_not_make_ordinary_lane_ready() -> None:
    ordinary = build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=("ordinary background query",),
        query_provenance=EVALUATOR_NEXT_QUERIES,
        conflict_resolving_queries=("official corrected date",),
        current_iteration=1,
        max_iterations=3,
        considered=True,
    ).to_dict()
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(
            action=RETRIEVE_TARGETED,
            authorized=RETRIEVE_TARGETED,
            dispatch_authorized=True,
        ),
        ordinary_continuation_candidate_trace=ordinary,
        targeted_retrieval_lifecycle_trace={
            "targeted_retrieval_candidate_considered": True,
            "targeted_retrieval_candidate_eligible": True,
            "targeted_retrieval_candidate_used": False,
            "targeted_retrieval_candidate_blockers": [],
        },
    )

    readiness = _readiness(projection_trace)
    lanes = {lane["lane_type"]: lane for lane in _inner(projection_trace)["lanes"]}

    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES]["status"] == "blocked"
    assert lanes[ORDINARY_EVALUATOR_GAP_QUERIES][
        "conflict_resolving_queries"
    ] == ["official corrected date"]
    assert lanes[CONFLICT_RESOLVING_QUERIES]["status"] == "skipped"
    assert readiness["ready_for_active_batch_dispatch"] is False
    assert readiness["selected_authorized_lane"] is None
    assert "no_selected_authorized_lane" in readiness["blockers"]


def test_ag46d_readiness_blocks_protected_surface_drift() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget evidence gap",),
        ),
    )
    projection = _inner(projection_trace)
    projection["provider_policy_unchanged"] = False

    readiness = _readiness(projection_trace)

    assert readiness["ready_for_active_batch_dispatch"] is False
    assert (
        "protected_surface_failed:provider_policy_unchanged"
        in readiness["blockers"]
    )


def test_ag46d_readiness_rejects_multiple_authorized_ordinary_lanes() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
        checkpoint_trace=_checkpoint(),
        ordinary_continuation_candidate_trace=_ordinary(
            EVALUATOR_NEXT_QUERIES,
            ("Acme Widget evidence gap",),
        ),
    )
    projection = _inner(projection_trace)
    duplicate = dict(projection["lanes"][0])
    duplicate["lane_id"] = ORDINARY_SCOUT_DIRECTED_QUERIES
    duplicate["lane_type"] = ORDINARY_SCOUT_DIRECTED_QUERIES
    duplicate["lane_source"] = "scout"
    duplicate["query_generation_owner"] = "scout"
    projection["lanes"].append(duplicate)
    projection["authorized_lane_count"] = 2

    readiness = _readiness(projection_trace)

    assert readiness["ready_for_active_batch_dispatch"] is False
    assert "multiple_authorized_lanes" in readiness["blockers"]
    assert "multiple_ordinary_lanes_authorized" in readiness["blockers"]
    assert (
        "protected_surface_failed:at_most_one_ordinary_lane_authorized"
        in readiness["blockers"]
    )


def test_ag46d_blocked_lanes_must_carry_stable_rationale() -> None:
    projection_trace = build_retrieval_batch_projection_trace(
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
            "active_source_class_recovery_queries": ["official source"],
        },
    )
    projection = _inner(projection_trace)
    ordinary_lane = next(
        lane
        for lane in projection["lanes"]
        if lane["lane_type"] == ORDINARY_EVALUATOR_GAP_QUERIES
    )
    ordinary_lane["blockers"] = []

    readiness = _readiness(projection_trace)

    assert readiness["ready_for_active_batch_dispatch"] is False
    assert (
        "lane_missing_blocked_or_skipped_rationale:"
        f"{ORDINARY_EVALUATOR_GAP_QUERIES}"
    ) in readiness["blockers"]
    assert (
        "protected_surface_failed:blocked_lanes_have_rationale"
        in readiness["blockers"]
    )


def test_ag46d_static_readiness_helper_has_no_dispatch_or_provider_coupling() -> None:
    source = _READINESS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.providers",
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

    assert forbidden_imports.isdisjoint(imported)
    assert "process_search_queries" not in source
    assert "select_providers" not in source
    assert "execute_retrieve_targeted_action" not in source
    assert 'provider_role="retrieve_targeted"' not in source
    assert "provider_role = \"retrieve_targeted\"" not in source
