"""Pure AG-47A active retrieval-batch dispatch decisions.

This module consumes existing controller-owned projection/readiness facts and
returns the ordinary-continuation scheduling decision. It does not execute
retrieval, call providers, select routing or depth, generate queries, build
prompts, mutate persistence, or alter handoffs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.retrieval_batch_authorization_readiness import (
    assess_retrieval_batch_authorization_readiness,
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

RETRIEVAL_BATCH_DISPATCH_SCHEMA_VERSION = "retrieval_batch_dispatch_ag47a_v1"
RETRIEVAL_BATCH_DISPATCH_TRACE_KEY = "retrieval_batch_dispatch_trace"
RUNTIME_BEHAVIOR_CONTRACT = "existing_retrieval_mechanics_only"

_ORDINARY_LANE_TYPES = frozenset(
    {
        ORDINARY_EVALUATOR_GAP_QUERIES,
        ORDINARY_EXPANDER_COMPONENT_QUERIES,
        ORDINARY_SCOUT_DIRECTED_QUERIES,
    }
)
_SEPARATE_LANE_TYPES = frozenset(
    {
        SOURCE_CLASS_RECOVERY_QUERIES,
        WEAK_CORPUS_RECOVERY_QUERIES,
        CONFLICT_RESOLVING_QUERIES,
    }
)


@dataclass(frozen=True)
class RetrievalBatchDispatchFacts:
    """Sanitized facts for one active ordinary batch-dispatch decision."""

    projection_trace: dict[str, Any] = field(default_factory=dict)
    readiness_trace: dict[str, Any] = field(default_factory=dict)
    checkpoint_trace: dict[str, Any] = field(default_factory=dict)
    ordinary_continuation_candidate_trace: dict[str, Any] = field(
        default_factory=dict
    )
    targeted_retrieval_lifecycle_trace: dict[str, Any] = field(
        default_factory=dict
    )
    source_class_lifecycle_trace: dict[str, Any] = field(default_factory=dict)
    weak_corpus_lifecycle_trace: dict[str, Any] = field(default_factory=dict)
    conflict_resolution_lifecycle_trace: dict[str, Any] = field(
        default_factory=dict
    )
    evaluator_continuation_spine_gate_trace: dict[str, Any] = field(
        default_factory=dict
    )
    expander_continuation_spine_gate_trace: dict[str, Any] = field(
        default_factory=dict
    )
    scout_continuation_spine_gate_trace: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_traces(
        cls,
        *,
        projection_trace: Mapping[str, Any] | None = None,
        readiness_trace: Mapping[str, Any] | None = None,
        checkpoint_trace: Mapping[str, Any] | None = None,
        ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
        targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
        source_class_lifecycle_trace: Mapping[str, Any] | None = None,
        weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
        conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
        evaluator_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
        expander_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
        scout_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
    ) -> "RetrievalBatchDispatchFacts":
        return cls(
            projection_trace=_json_safe_mapping(projection_trace),
            readiness_trace=_json_safe_mapping(readiness_trace),
            checkpoint_trace=_json_safe_mapping(checkpoint_trace),
            ordinary_continuation_candidate_trace=_json_safe_mapping(
                ordinary_continuation_candidate_trace
            ),
            targeted_retrieval_lifecycle_trace=_json_safe_mapping(
                targeted_retrieval_lifecycle_trace
            ),
            source_class_lifecycle_trace=_json_safe_mapping(
                source_class_lifecycle_trace
            ),
            weak_corpus_lifecycle_trace=_json_safe_mapping(
                weak_corpus_lifecycle_trace
            ),
            conflict_resolution_lifecycle_trace=_json_safe_mapping(
                conflict_resolution_lifecycle_trace
            ),
            evaluator_continuation_spine_gate_trace=_json_safe_mapping(
                evaluator_continuation_spine_gate_trace
            ),
            expander_continuation_spine_gate_trace=_json_safe_mapping(
                expander_continuation_spine_gate_trace
            ),
            scout_continuation_spine_gate_trace=_json_safe_mapping(
                scout_continuation_spine_gate_trace
            ),
        )


@dataclass(frozen=True)
class RetrievalBatchDispatchDecision:
    """Active scheduling decision for one existing ordinary continuation lane."""

    considered: bool
    dispatch_authorized: bool
    selected_lane: str | None
    selected_lane_type: str | None
    query_provenance: str | None
    authorized_queries: tuple[str, ...]
    blocked_reason: str | None
    blockers: tuple[str, ...]
    readiness_summary: dict[str, Any]
    dispatch_owner: str | None
    provider_policy: str = "reuse_existing"
    depth_policy: str = "reuse_existing"
    query_generation_policy: str = "reuse_existing"
    executor_dispatched: bool = False
    targeted_retrieval_executor_dispatched: bool = False
    retrieve_targeted_provider_role_used: bool = False
    runtime_behavior_contract: str = RUNTIME_BEHAVIOR_CONTRACT

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema_version": RETRIEVAL_BATCH_DISPATCH_SCHEMA_VERSION,
            "considered": bool(self.considered),
            "dispatch_authorized": bool(self.dispatch_authorized),
            "selected_lane_id": self.selected_lane,
            "selected_lane_type": self.selected_lane_type,
            "query_provenance": self.query_provenance,
            "authorized_query_count": len(self.authorized_queries),
            "authorized_queries": list(self.authorized_queries),
            "blocked_reason": self.blocked_reason,
            "blockers": list(self.blockers),
            "readiness_status": self.readiness_summary.get(
                "ready_for_active_batch_dispatch"
            ),
            "readiness_summary": dict(self.readiness_summary),
            "dispatch_owner": self.dispatch_owner,
            "provider_policy": self.provider_policy,
            "depth_policy": self.depth_policy,
            "query_generation_policy": self.query_generation_policy,
            "provider_policy_unchanged": self.provider_policy == "reuse_existing",
            "depth_policy_unchanged": self.depth_policy == "reuse_existing",
            "query_generation_unchanged": (
                self.query_generation_policy == "reuse_existing"
            ),
            "prompt_unchanged": True,
            "runtime_behavior_changed": False,
            "executor_dispatched": bool(self.executor_dispatched),
            "targeted_retrieval_executor_dispatched": bool(
                self.targeted_retrieval_executor_dispatched
            ),
            "retrieve_targeted_provider_role_used": bool(
                self.retrieve_targeted_provider_role_used
            ),
            "runtime_behavior_contract": self.runtime_behavior_contract,
        }


def retrieval_batch_dispatch_defaults(
    reason: str = "not_evaluated",
) -> dict[str, Any]:
    """Return a not-considered AG-47A dispatch trace."""
    return _blocked_decision(
        considered=False,
        blocked_reason=reason,
        blockers=(reason,),
        readiness_summary={},
        dispatch_owner=None,
    ).to_trace()


def build_retrieval_batch_dispatch_decision(
    facts: RetrievalBatchDispatchFacts | Mapping[str, Any] | None = None,
    *,
    projection_trace: Mapping[str, Any] | None = None,
    readiness_trace: Mapping[str, Any] | None = None,
) -> RetrievalBatchDispatchDecision:
    """Return the active ordinary-lane scheduling decision for one batch."""
    if facts is None or isinstance(facts, Mapping):
        facts = RetrievalBatchDispatchFacts.from_traces(
            projection_trace=(
                projection_trace
                if projection_trace is not None
                else facts.get("projection_trace")
                if isinstance(facts, Mapping)
                else None
            ),
            readiness_trace=(
                readiness_trace
                if readiness_trace is not None
                else facts.get("readiness_trace")
                if isinstance(facts, Mapping)
                else None
            ),
        )

    projection_trace_payload = facts.projection_trace
    if not projection_trace_payload:
        projection_trace_payload = build_retrieval_batch_projection_trace(
            checkpoint_trace=facts.checkpoint_trace,
            ordinary_continuation_candidate_trace=(
                facts.ordinary_continuation_candidate_trace
            ),
            targeted_retrieval_lifecycle_trace=(
                facts.targeted_retrieval_lifecycle_trace
            ),
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            evaluator_continuation_spine_gate_trace=(
                facts.evaluator_continuation_spine_gate_trace
            ),
            expander_continuation_spine_gate_trace=(
                facts.expander_continuation_spine_gate_trace
            ),
            scout_continuation_spine_gate_trace=(
                facts.scout_continuation_spine_gate_trace
            ),
        )
    readiness_trace_payload = facts.readiness_trace or readiness_trace
    if not readiness_trace_payload:
        readiness_trace_payload = assess_retrieval_batch_authorization_readiness(
            projection_trace_payload
        )

    projection = _projection_payload(projection_trace_payload)
    readiness = _readiness_payload(readiness_trace_payload)
    lanes = _safe_lanes(projection.get("lanes"))
    selected_lane = _selected_lane(projection, lanes)
    blockers = list(_compact_strings(readiness.get("blockers")))

    if not projection:
        blockers.append("projection_missing")
    if not readiness:
        blockers.append("readiness_missing")
    if readiness.get("ready_for_active_batch_dispatch") is not True:
        blockers.append("readiness_not_ready")
    if selected_lane is None:
        blockers.append("no_selected_authorized_lane")
    elif selected_lane.get("lane_type") not in _ORDINARY_LANE_TYPES:
        blockers.append("selected_lane_not_ordinary_continuation")
    if selected_lane and selected_lane.get("lane_type") in _SEPARATE_LANE_TYPES:
        blockers.append("separate_action_lane_not_ordinary_dispatch")
    if selected_lane and _compact_strings(
        selected_lane.get("conflict_resolving_queries")
    ):
        blockers.append("ordinary_conflict_query_separation_failed")
    if any(
        lane.get("lane_type") in _ORDINARY_LANE_TYPES
        and _compact_strings(lane.get("conflict_resolving_queries"))
        for lane in lanes
    ):
        blockers.append("ordinary_conflict_query_separation_failed")
    if int(projection.get("authorized_lane_count") or 0) != 1:
        blockers.append("authorized_lane_count_not_one")

    blockers_tuple = _dedupe_strings(blockers)
    authorized_queries = (
        _compact_strings(selected_lane.get("approved_queries"))
        if selected_lane is not None and not blockers_tuple
        else ()
    )
    if selected_lane is not None and not authorized_queries and not blockers_tuple:
        blockers_tuple = ("authorized_queries_missing",)

    if blockers_tuple:
        return _blocked_decision(
            considered=bool(projection or readiness),
            selected_lane=(
                _string_or_none(selected_lane.get("lane_id"))
                if selected_lane is not None
                else None
            ),
            selected_lane_type=(
                _string_or_none(selected_lane.get("lane_type"))
                if selected_lane is not None
                else None
            ),
            query_provenance=(
                _string_or_none(selected_lane.get("query_provenance"))
                if selected_lane is not None
                else None
            ),
            blocked_reason=blockers_tuple[0],
            blockers=blockers_tuple,
            readiness_summary=readiness,
            dispatch_owner=_string_or_none(projection.get("dispatch_owner")),
        )

    return RetrievalBatchDispatchDecision(
        considered=True,
        dispatch_authorized=True,
        selected_lane=_string_or_none(selected_lane.get("lane_id")),
        selected_lane_type=_string_or_none(selected_lane.get("lane_type")),
        query_provenance=_string_or_none(selected_lane.get("query_provenance")),
        authorized_queries=authorized_queries,
        blocked_reason=None,
        blockers=(),
        readiness_summary=readiness,
        dispatch_owner=_string_or_none(projection.get("dispatch_owner")),
        provider_policy="reuse_existing",
        depth_policy="reuse_existing",
        query_generation_policy="reuse_existing",
        executor_dispatched=False,
        targeted_retrieval_executor_dispatched=False,
        retrieve_targeted_provider_role_used=False,
        runtime_behavior_contract=RUNTIME_BEHAVIOR_CONTRACT,
    )


def _blocked_decision(
    *,
    considered: bool,
    blocked_reason: str,
    blockers: tuple[str, ...],
    readiness_summary: Mapping[str, Any],
    dispatch_owner: str | None,
    selected_lane: str | None = None,
    selected_lane_type: str | None = None,
    query_provenance: str | None = None,
) -> RetrievalBatchDispatchDecision:
    return RetrievalBatchDispatchDecision(
        considered=considered,
        dispatch_authorized=False,
        selected_lane=selected_lane,
        selected_lane_type=selected_lane_type,
        query_provenance=query_provenance,
        authorized_queries=(),
        blocked_reason=blocked_reason,
        blockers=_dedupe_strings(blockers),
        readiness_summary=dict(readiness_summary),
        dispatch_owner=dispatch_owner,
    )


def _projection_payload(projection_trace: Mapping[str, Any] | None) -> dict[str, Any]:
    trace = _json_safe_mapping(projection_trace)
    if RETRIEVAL_BATCH_PROJECTION_TRACE_KEY in trace:
        trace = _json_safe_mapping(trace.get(RETRIEVAL_BATCH_PROJECTION_TRACE_KEY))
    return _json_safe_mapping(trace.get("RetrievalBatchProjection"))


def _readiness_payload(readiness_trace: Mapping[str, Any] | None) -> dict[str, Any]:
    trace = _json_safe_mapping(readiness_trace)
    return _json_safe_mapping(trace.get("RetrievalBatchAuthorizationReadiness"))


def _selected_lane(
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


def _safe_lanes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [_json_safe_mapping(item) for item in value if isinstance(item, Mapping)]


def _json_safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in dict(value or {}).items():
        if isinstance(item, Mapping):
            safe[str(key)] = _json_safe_mapping(item)
        elif isinstance(item, tuple):
            safe[str(key)] = list(item)
        else:
            safe[str(key)] = item
    return safe


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
    return _dedupe_strings(str(item) for item in iterable if str(item or "").strip())


def _dedupe_strings(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = " ".join(str(item or "").strip().split())[:300]
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _string_or_none(value: Any) -> str | None:
    text = " ".join(str(value or "").strip().split())[:300]
    return text or None


__all__ = [
    "RETRIEVAL_BATCH_DISPATCH_SCHEMA_VERSION",
    "RETRIEVAL_BATCH_DISPATCH_TRACE_KEY",
    "RUNTIME_BEHAVIOR_CONTRACT",
    "RetrievalBatchDispatchDecision",
    "RetrievalBatchDispatchFacts",
    "build_retrieval_batch_dispatch_decision",
    "retrieval_batch_dispatch_defaults",
]
