"""Pure AG-46D retrieval-batch authorization readiness checks.

This module consumes the passive AG-46B projection shape and reports whether
that shape is structurally ready for a future active batch-dispatch contract.
It does not dispatch retrieval, call providers, select routing or depth, build
prompts, generate queries, mutate persistence, or alter handoffs.
"""

from __future__ import annotations

from typing import Any, Mapping

from core.retrieval_batch_projection import (
    CONFLICT_RESOLVING_QUERIES,
    ORDINARY_EVALUATOR_GAP_QUERIES,
    ORDINARY_EXPANDER_COMPONENT_QUERIES,
    ORDINARY_SCOUT_DIRECTED_QUERIES,
    RETRIEVE_TARGETED,
    SOURCE_CLASS_RECOVERY_QUERIES,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    WEAK_CORPUS_RECOVERY_QUERIES,
)

RETRIEVAL_BATCH_AUTHORIZATION_READINESS_SCHEMA_VERSION = (
    "retrieval_batch_authorization_readiness_ag46d_v1"
)
RETRIEVAL_BATCH_AUTHORIZATION_READINESS_TRACE_KEY = (
    "retrieval_batch_authorization_readiness"
)

_ORDINARY_LANE_TYPES = frozenset(
    {
        ORDINARY_EVALUATOR_GAP_QUERIES,
        ORDINARY_EXPANDER_COMPONENT_QUERIES,
        ORDINARY_SCOUT_DIRECTED_QUERIES,
    }
)
_SEPARATE_ACTION_LANE_TYPES = frozenset(
    {
        SOURCE_CLASS_RECOVERY_QUERIES,
        WEAK_CORPUS_RECOVERY_QUERIES,
        CONFLICT_RESOLVING_QUERIES,
    }
)
_TERMINAL_STOP_ACTIONS = frozenset(
    {
        STOP_INSUFFICIENT_WITH_CAVEAT,
        STOP_SUFFICIENT,
    }
)
_EXPECTED_SEPARATE_OWNERS = {
    SOURCE_CLASS_RECOVERY_QUERIES: "source_class_controller",
    WEAK_CORPUS_RECOVERY_QUERIES: "weak_corpus_controller",
    CONFLICT_RESOLVING_QUERIES: "conflict_controller",
}


def assess_retrieval_batch_authorization_readiness(
    projection_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return structural readiness facts from one passive projection trace."""
    projection = _projection_payload(projection_trace)
    lanes = _safe_lanes(projection.get("lanes"))
    authorization = _safe_mapping(projection.get("authorization"))
    constraints = _safe_mapping(projection.get("constraints"))

    represented_lanes = [
        str(lane.get("lane_type") or lane.get("lane_id"))
        for lane in lanes
        if lane.get("lane_type") or lane.get("lane_id")
    ]
    authorized_lanes = [
        lane for lane in lanes if lane.get("status") == "authorized"
    ]
    authorized_ordinary_lanes = [
        lane
        for lane in authorized_lanes
        if lane.get("lane_type") in _ORDINARY_LANE_TYPES
    ]
    selected_lane = _selected_authorized_lane(projection, lanes)
    blocked_or_skipped_lanes = _blocked_or_skipped_lanes(lanes)

    protected_surface_status = _protected_surface_status(
        projection=projection,
        constraints=constraints,
        lanes=lanes,
        authorized_lanes=authorized_lanes,
        authorized_ordinary_lanes=authorized_ordinary_lanes,
    )
    blockers = _readiness_blockers(
        projection=projection,
        authorization=authorization,
        lanes=lanes,
        selected_lane=selected_lane,
        blocked_or_skipped_lanes=blocked_or_skipped_lanes,
        protected_surface_status=protected_surface_status,
    )

    ready = not blockers
    readiness = {
        "ready_for_active_batch_dispatch": ready,
        "readiness_scope": (
            "structural_only_no_active_dispatch_authorized"
        ),
        "readiness_wording": (
            "A true value means the passive projection is structurally ready "
            "only; it does not authorize an executor, provider role, routing, "
            "depth, query-generation, prompt, persistence, final-answer, or "
            "handoff change."
        ),
        "blockers": blockers,
        "represented_lanes": represented_lanes,
        "selected_authorized_lane": (
            _lane_summary(selected_lane) if selected_lane is not None else None
        ),
        "authorized_lane_count": len(authorized_lanes),
        "authorized_ordinary_lane_count": len(authorized_ordinary_lanes),
        "blocked_or_skipped_lanes": blocked_or_skipped_lanes,
        "protected_surface_status": protected_surface_status,
        "dispatch_owner": projection.get("dispatch_owner"),
        "checkpoint_decision_count": authorization.get(
            "checkpoint_decision_count"
        ),
    }
    return {
        "schema_version": (
            RETRIEVAL_BATCH_AUTHORIZATION_READINESS_SCHEMA_VERSION
        ),
        "trace_mode": "passive_structural_readiness",
        "RetrievalBatchAuthorizationReadiness": readiness,
    }


def _readiness_blockers(
    *,
    projection: Mapping[str, Any],
    authorization: Mapping[str, Any],
    lanes: list[dict[str, Any]],
    selected_lane: Mapping[str, Any] | None,
    blocked_or_skipped_lanes: list[dict[str, Any]],
    protected_surface_status: Mapping[str, bool],
) -> list[str]:
    blockers: list[str] = []
    if not projection:
        blockers.append("projection_missing")
    if authorization.get("checkpoint_decision_count") != 1:
        blockers.append("checkpoint_decision_count_not_one")
    if projection.get("dispatch_owner") != "controller_loop_spine":
        blockers.append("dispatch_owner_not_controller_loop_spine")
    if int(projection.get("authorized_lane_count") or 0) > 1:
        blockers.append("multiple_authorized_lanes")
    if not protected_surface_status["at_most_one_ordinary_lane_authorized"]:
        blockers.append("multiple_ordinary_lanes_authorized")
    if projection.get("checkpoint_action_name") in _TERMINAL_STOP_ACTIONS:
        blockers.append("terminal_stop_blocks_batch_authorization")
    if selected_lane is None:
        blockers.append("no_selected_authorized_lane")
    elif selected_lane.get("lane_type") not in _ORDINARY_LANE_TYPES:
        blockers.append("selected_lane_not_ordinary_continuation")
    if projection.get("action_name") != RETRIEVE_TARGETED:
        blockers.append("action_name_not_retrieve_targeted")
    if authorization.get("dispatch_authorized") is not True:
        blockers.append("dispatch_not_authorized_by_spine")

    for name, ok in protected_surface_status.items():
        if not ok:
            blockers.append(f"protected_surface_failed:{name}")
    for lane in blocked_or_skipped_lanes:
        if not lane.get("blockers"):
            blockers.append(
                f"lane_missing_blocked_or_skipped_rationale:{lane['lane_id']}"
            )
    return _dedupe(blockers)


def _protected_surface_status(
    *,
    projection: Mapping[str, Any],
    constraints: Mapping[str, Any],
    lanes: list[dict[str, Any]],
    authorized_lanes: list[dict[str, Any]],
    authorized_ordinary_lanes: list[dict[str, Any]],
) -> dict[str, bool]:
    separate_lanes_are_bounded = all(
        lane.get("query_generation_owner")
        == _EXPECTED_SEPARATE_OWNERS.get(str(lane.get("lane_type")))
        for lane in lanes
        if lane.get("lane_type") in _SEPARATE_ACTION_LANE_TYPES
    )
    ordinary_lanes_keep_conflicts_separate = all(
        not lane.get("conflict_resolving_queries")
        for lane in authorized_ordinary_lanes
    )
    blocked_lanes_have_rationale = all(
        bool(lane.get("blockers"))
        for lane in lanes
        if lane.get("status") in {"blocked", "skipped"}
    )
    return {
        "one_checkpoint_decision": bool(
            _constraint_bool(constraints, "one_checkpoint_decision")
        ),
        "one_dispatch_owner": (
            projection.get("dispatch_owner") == "controller_loop_spine"
            and constraints.get("one_dispatch_owner") == "controller_loop_spine"
        ),
        "at_most_one_ordinary_lane_authorized": (
            len(authorized_ordinary_lanes) <= 1
        ),
        "at_most_one_lane_authorized": len(authorized_lanes) <= 1,
        "lifecycle_blockers_authoritative": bool(
            _constraint_bool(constraints, "lifecycle_blockers_authoritative")
        ),
        "blocked_lanes_have_rationale": blocked_lanes_have_rationale,
        "terminal_stops_before_bounded_retrieval": bool(
            _constraint_bool(
                constraints,
                "terminal_stops_before_bounded_retrieval",
            )
        ),
        "provider_policy_unchanged": (
            projection.get("provider_policy_unchanged") is True
            and _constraint_bool(constraints, "no_provider_policy_change")
        ),
        "depth_policy_unchanged": (
            projection.get("depth_policy_unchanged") is True
            and _constraint_bool(constraints, "no_depth_policy_change")
        ),
        "query_generation_unchanged": (
            projection.get("query_generation_unchanged") is True
            and _constraint_bool(constraints, "no_query_generation")
        ),
        "prompt_unchanged": (
            projection.get("prompt_unchanged") is True
            and _constraint_bool(constraints, "no_prompt_change")
        ),
        "runtime_behavior_unchanged": (
            projection.get("runtime_behavior_changed") is False
        ),
        "no_targeted_executor": (
            projection.get("targeted_retrieval_executor_dispatched") is False
            and _constraint_bool(constraints, "no_targeted_executor")
        ),
        "no_retrieve_targeted_provider_role": (
            projection.get("retrieve_targeted_provider_role_used") is False
            and _constraint_bool(
                constraints,
                "no_retrieve_targeted_provider_role",
            )
        ),
        "no_orphan_dispatch_path_visible": (
            projection.get("orphan_dispatch_path_visible") is False
        ),
        "ordinary_conflict_query_separation_preserved": (
            ordinary_lanes_keep_conflicts_separate
            and _constraint_bool(
                constraints,
                "ordinary_conflict_query_separation_preserved",
            )
        ),
        "separate_action_lanes_remain_bounded": separate_lanes_are_bounded,
    }


def _projection_payload(
    projection_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    trace = _safe_mapping(projection_trace)
    return _safe_mapping(trace.get("RetrievalBatchProjection"))


def _selected_authorized_lane(
    projection: Mapping[str, Any],
    lanes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    selected_lane_id = projection.get("selected_lane")
    for lane in lanes:
        if (
            lane.get("lane_id") == selected_lane_id
            and lane.get("status") == "authorized"
        ):
            return lane
    return None


def _blocked_or_skipped_lanes(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lane_id": str(lane.get("lane_id") or lane.get("lane_type")),
            "lane_type": str(lane.get("lane_type") or ""),
            "status": str(lane.get("status") or ""),
            "blockers": list(_compact_strings(lane.get("blockers"))),
        }
        for lane in lanes
        if lane.get("status") in {"blocked", "skipped", "future_non_authorized"}
    ]


def _lane_summary(lane: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lane_id": lane.get("lane_id"),
        "lane_type": lane.get("lane_type"),
        "query_generation_owner": lane.get("query_generation_owner"),
        "query_count": len(_compact_strings(lane.get("approved_queries"))),
        "status": lane.get("status"),
    }


def _safe_lanes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [_safe_mapping(item) for item in value if isinstance(item, Mapping)]


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _constraint_bool(constraints: Mapping[str, Any], key: str) -> bool:
    return constraints.get(key) is True


def _compact_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        iterable = value.values()
    elif isinstance(value, (str, bytes)) or value is None:
        iterable = ()
    else:
        try:
            iterable = tuple(value)
        except TypeError:
            iterable = ()
    return tuple(str(item) for item in iterable if str(item or "").strip())


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            out.append(value)
            seen.add(key)
    return out


__all__ = [
    "RETRIEVAL_BATCH_AUTHORIZATION_READINESS_SCHEMA_VERSION",
    "RETRIEVAL_BATCH_AUTHORIZATION_READINESS_TRACE_KEY",
    "assess_retrieval_batch_authorization_readiness",
]
