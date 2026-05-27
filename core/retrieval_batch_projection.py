"""Pure passive retrieval-batch projection trace.

This module consumes already-computed sanitized controller/runtime trace facts
and projects the typed retrieval-batch shape documented in AG-46A. It is
descriptive only: it does not authorize dispatch, execute retrieval, choose
providers, choose depth, generate queries, build prompts, or mutate runtime
state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

RETRIEVAL_BATCH_PROJECTION_TRACE_KEY = "retrieval_batch_projection_trace"
RETRIEVAL_BATCH_DISPATCH_TRACE_KEY = "retrieval_batch_dispatch_trace"
RETRIEVAL_BATCH_PROJECTION_SCHEMA_VERSION = (
    "retrieval_batch_projection_ag46b_v1"
)

STOP_SUFFICIENT = "stop_sufficient"
STOP_INSUFFICIENT_WITH_CAVEAT = "stop_insufficient_with_caveat"
RETRIEVE_TARGETED = "retrieve_targeted"
RECOVER_MISSING_SOURCE_CLASS = "recover_missing_source_class"
RECOVER_WEAK_CORPUS = "recover_weak_corpus"
RESOLVE_CONFLICT = "resolve_conflict"

ORDINARY_CONTINUATION_TRACE_KEY = "ordinary_continuation_candidate"
EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY = (
    "evidence_integration_checkpoint_shadow"
)

EVALUATOR_NEXT_QUERIES = "evaluator_next_queries"
EXPANDER_COMPONENT_QUERIES = "expander_component_queries"
SCOUT_DIRECTED_QUERIES = "scout_directed_queries"

ORDINARY_EVALUATOR_GAP_QUERIES = "ordinary_evaluator_gap_queries"
ORDINARY_EXPANDER_COMPONENT_QUERIES = "ordinary_expander_component_queries"
ORDINARY_SCOUT_DIRECTED_QUERIES = "ordinary_scout_directed_queries"
SOURCE_CLASS_RECOVERY_QUERIES = "source_class_recovery_queries"
WEAK_CORPUS_RECOVERY_QUERIES = "weak_corpus_recovery_queries"
CONFLICT_RESOLVING_QUERIES = "conflict_resolving_queries"
FUTURE_SOCIAL_SIGNAL_QUERIES = "future_social_signal_queries"
FUTURE_LEGAL_CURRENT_PRIMARY_ADAPTER_LANE = (
    "future_legal_current_primary_adapter_lane"
)

_ORDINARY_SOURCE_TO_LANE = {
    EVALUATOR_NEXT_QUERIES: (
        ORDINARY_EVALUATOR_GAP_QUERIES,
        "evaluator",
        "evaluator",
        "evaluator ordinary continuation gap",
    ),
    EXPANDER_COMPONENT_QUERIES: (
        ORDINARY_EXPANDER_COMPONENT_QUERIES,
        "expander",
        "expander",
        "expander component evidence gap",
    ),
    SCOUT_DIRECTED_QUERIES: (
        ORDINARY_SCOUT_DIRECTED_QUERIES,
        "scout",
        "scout",
        "scout directed evidence gap",
    ),
}
_ORDINARY_LANE_TYPES = frozenset(
    lane_info[0] for lane_info in _ORDINARY_SOURCE_TO_LANE.values()
)
_ORDINARY_LANE_TO_SOURCE = {
    lane_info[0]: (source_path, *lane_info[1:])
    for source_path, lane_info in _ORDINARY_SOURCE_TO_LANE.items()
}
_SEPARATE_LANE_TYPES = frozenset(
    {
        SOURCE_CLASS_RECOVERY_QUERIES,
        WEAK_CORPUS_RECOVERY_QUERIES,
        CONFLICT_RESOLVING_QUERIES,
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
)


class RetrievalBatchLaneType(str, Enum):
    """Stable typed retrieval lane taxonomy."""

    ORDINARY_EVALUATOR_GAP_QUERIES = ORDINARY_EVALUATOR_GAP_QUERIES
    ORDINARY_EXPANDER_COMPONENT_QUERIES = ORDINARY_EXPANDER_COMPONENT_QUERIES
    ORDINARY_SCOUT_DIRECTED_QUERIES = ORDINARY_SCOUT_DIRECTED_QUERIES
    SOURCE_CLASS_RECOVERY_QUERIES = SOURCE_CLASS_RECOVERY_QUERIES
    WEAK_CORPUS_RECOVERY_QUERIES = WEAK_CORPUS_RECOVERY_QUERIES
    CONFLICT_RESOLVING_QUERIES = CONFLICT_RESOLVING_QUERIES
    FUTURE_SOCIAL_SIGNAL_QUERIES = FUTURE_SOCIAL_SIGNAL_QUERIES
    FUTURE_LEGAL_CURRENT_PRIMARY_ADAPTER_LANE = (
        FUTURE_LEGAL_CURRENT_PRIMARY_ADAPTER_LANE
    )


@dataclass(frozen=True)
class RetrievalBatchProjectionFacts:
    """Sanitized trace facts consumed by the passive projection builder."""

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
    dispatch_trace: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_runtime_trace(
        cls,
        runtime_trace: Mapping[str, Any] | None,
    ) -> "RetrievalBatchProjectionFacts":
        trace = _json_safe_mapping(runtime_trace)
        checkpoint = _json_safe_mapping(
            trace.get(EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY)
        )
        return cls(
            checkpoint_trace=checkpoint,
            ordinary_continuation_candidate_trace=_json_safe_mapping(
                trace.get(ORDINARY_CONTINUATION_TRACE_KEY)
                or checkpoint.get(ORDINARY_CONTINUATION_TRACE_KEY)
            ),
            targeted_retrieval_lifecycle_trace={
                key: trace.get(key)
                for key in trace
                if str(key).startswith("targeted_retrieval_candidate_")
            },
            source_class_lifecycle_trace={
                key: trace.get(key)
                for key in trace
                if str(key).startswith("active_source_class_recovery_")
            },
            weak_corpus_lifecycle_trace={
                key: trace.get(key)
                for key in trace
                if str(key).startswith("weak_corpus_recovery_")
            },
            conflict_resolution_lifecycle_trace={
                key: trace.get(key)
                for key in trace
                if str(key).startswith("active_conflict_resolution_")
            },
            evaluator_continuation_spine_gate_trace=_json_safe_mapping(
                trace.get("evaluator_continuation_spine_gate_trace")
                or checkpoint.get("evaluator_continuation_spine_gate_trace")
            ),
            expander_continuation_spine_gate_trace=_json_safe_mapping(
                trace.get("expander_continuation_spine_gate_trace")
                or checkpoint.get("expander_continuation_spine_gate_trace")
            ),
            scout_continuation_spine_gate_trace=_json_safe_mapping(
                trace.get("scout_continuation_spine_gate_trace")
                or checkpoint.get("scout_continuation_spine_gate_trace")
            ),
            dispatch_trace=_json_safe_mapping(
                trace.get(RETRIEVAL_BATCH_DISPATCH_TRACE_KEY)
                or checkpoint.get(RETRIEVAL_BATCH_DISPATCH_TRACE_KEY)
            ),
        )


def retrieval_batch_projection_defaults(reason: str = "not_evaluated") -> dict[str, Any]:
    """Return a safe not-applicable projection trace."""
    return build_retrieval_batch_projection_trace(
        RetrievalBatchProjectionFacts(
            checkpoint_trace={"reason": _clean_text(reason, limit=120)}
        )
    )


def build_retrieval_batch_projection_trace(
    facts: RetrievalBatchProjectionFacts | None = None,
    *,
    runtime_trace: Mapping[str, Any] | None = None,
    checkpoint_trace: Mapping[str, Any] | None = None,
    ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
    targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
    source_class_lifecycle_trace: Mapping[str, Any] | None = None,
    weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
    conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
    evaluator_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
    expander_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
    scout_continuation_spine_gate_trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project typed retrieval-batch visibility from existing trace facts."""
    if facts is None:
        if runtime_trace is not None:
            facts = RetrievalBatchProjectionFacts.from_runtime_trace(runtime_trace)
        else:
            facts = RetrievalBatchProjectionFacts(
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

    checkpoint = _json_safe_mapping(facts.checkpoint_trace)
    ordinary = _json_safe_mapping(facts.ordinary_continuation_candidate_trace)
    targeted = _json_safe_mapping(facts.targeted_retrieval_lifecycle_trace)
    source_class = _json_safe_mapping(facts.source_class_lifecycle_trace)
    weak_corpus = _json_safe_mapping(facts.weak_corpus_lifecycle_trace)
    conflict = _json_safe_mapping(facts.conflict_resolution_lifecycle_trace)
    gate_traces = (
        _json_safe_mapping(facts.evaluator_continuation_spine_gate_trace),
        _json_safe_mapping(facts.expander_continuation_spine_gate_trace),
        _json_safe_mapping(facts.scout_continuation_spine_gate_trace),
    )

    checkpoint_action_name = _action_name_from_checkpoint(checkpoint)
    promoted_action_name = _string_or_none(checkpoint.get("promoted_action_name"))
    authorized_action_name = _string_or_none(checkpoint.get("authorized_action_name"))
    action_name = (
        authorized_action_name
        or promoted_action_name
        or checkpoint_action_name
        or "not_applicable"
    )
    targeted_dispatch_authorized = bool(
        checkpoint.get("targeted_retrieval_dispatch_authorized")
        or any(
            gate.get("targeted_retrieval_dispatch_authorized")
            for gate in gate_traces
        )
    )
    targeted_executor_dispatched = bool(
        checkpoint.get("targeted_retrieval_executor_dispatched")
        or any(
            gate.get("targeted_retrieval_executor_dispatched")
            for gate in gate_traces
        )
    )

    lanes = _build_lanes(
        checkpoint_action_name=checkpoint_action_name,
        authorized_action_name=authorized_action_name,
        targeted_dispatch_authorized=targeted_dispatch_authorized,
        ordinary=ordinary,
        targeted=targeted,
        source_class=source_class,
        weak_corpus=weak_corpus,
        conflict=conflict,
    )
    selected_lane = _selected_lane(lanes)
    authorized_lane_ids = [
        lane["lane_id"] for lane in lanes if lane["status"] == "authorized"
    ]
    blocked_lane_ids = [
        lane["lane_id"]
        for lane in lanes
        if lane["status"] in {"blocked", "skipped", "future_non_authorized"}
    ]
    batch_blockers = _batch_blockers(
        lanes=lanes,
        checkpoint=checkpoint,
        targeted=targeted,
    )
    selected_queries = (
        _lane_queries(selected_lane) if isinstance(selected_lane, Mapping) else []
    )
    batch_status = _batch_status(
        lanes=lanes,
        checkpoint_action_name=checkpoint_action_name,
        targeted_dispatch_authorized=targeted_dispatch_authorized,
        batch_blockers=batch_blockers,
    )
    batch_reason = _batch_reason(
        selected_lane=selected_lane,
        batch_status=batch_status,
        checkpoint=checkpoint,
        targeted=targeted,
        batch_blockers=batch_blockers,
    )

    projection = {
        "batch_id": _batch_id(action_name, selected_lane),
        "action_name": action_name,
        "checkpoint_action_name": checkpoint_action_name,
        "promoted_action_name": promoted_action_name,
        "authorized_action_name": authorized_action_name,
        "batch_status": batch_status,
        "batch_reason": batch_reason,
        "lanes": lanes,
        "authorized_lane_count": len(authorized_lane_ids),
        "blocked_lane_count": len(blocked_lane_ids),
        "selected_lane": (
            selected_lane["lane_id"] if isinstance(selected_lane, Mapping) else None
        ),
        "query_count": len(selected_queries),
        "batch_blockers": batch_blockers,
        "provider_policy_unchanged": True,
        "depth_policy_unchanged": True,
        "query_generation_unchanged": True,
        "prompt_unchanged": True,
        "dispatch_owner": "controller_loop_spine",
        "runtime_behavior_changed": False,
        "targeted_retrieval_executor_dispatched": targeted_executor_dispatched,
        "retrieve_targeted_provider_role_used": False,
        "orphan_dispatch_path_visible": False,
        "constraints": {
            "one_checkpoint_decision": True,
            "one_promoted_action_at_most": True,
            "one_dispatch_owner": "controller_loop_spine",
            "terminal_stops_before_bounded_retrieval": True,
            "lifecycle_blockers_authoritative": True,
            "no_provider_policy_change": True,
            "no_depth_policy_change": True,
            "no_query_generation": True,
            "no_prompt_change": True,
            "no_targeted_executor": not targeted_executor_dispatched,
            "no_retrieve_targeted_provider_role": True,
            "ordinary_conflict_query_separation_preserved": True,
        },
        "authorization": {
            "authorized_by": "controller_loop_spine",
            "checkpoint_decision_count": _checkpoint_decision_count(checkpoint),
            "projected_authorized_from_spine": bool(authorized_lane_ids),
            "dispatch_authorized": bool(targeted_dispatch_authorized),
            "executor_dispatched": False,
            "promoted_action_name": promoted_action_name,
            "authorized_action_name": authorized_action_name,
            "allowed_lane_ids": authorized_lane_ids,
            "blocked_lane_ids": blocked_lane_ids,
            "blocked_or_skipped_actions": _json_safe_mapping(
                checkpoint.get("blocked_or_skipped_actions")
            ),
        },
        "handoff_summary": {
            "action_name": action_name,
            "approved_query_count": len(selected_queries),
            "lane_types": _dedupe_strings(
                lane["lane_type"] for lane in lanes if lane.get("lane_type")
            ),
            "evidence_obligations": _dedupe_strings(
                lane["evidence_obligation"]
                for lane in lanes
                if lane.get("evidence_obligation")
            ),
            "provider_policy": "reuse_existing",
            "depth_policy": "reuse_existing",
            "runtime_handoff_changed": False,
        },
    }
    projection = _apply_authorized_dispatch_overlay(
        projection=projection,
        dispatch_trace=facts.dispatch_trace,
    )
    return {
        "schema_version": RETRIEVAL_BATCH_PROJECTION_SCHEMA_VERSION,
        "trace_mode": "passive_runtime_visibility",
        "RetrievalBatchProjection": _json_safe_value(projection),
    }


def lane_type_for_ordinary_source(source_path: str | None) -> str | None:
    """Return the batch lane type for a bounded ordinary source path."""
    normalized = _clean_token(source_path)
    mapping = _ORDINARY_SOURCE_TO_LANE.get(normalized or "")
    return mapping[0] if mapping else None


def _build_lanes(
    *,
    checkpoint_action_name: str | None,
    authorized_action_name: str | None,
    targeted_dispatch_authorized: bool,
    ordinary: Mapping[str, Any],
    targeted: Mapping[str, Any],
    source_class: Mapping[str, Any],
    weak_corpus: Mapping[str, Any],
    conflict: Mapping[str, Any],
) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    source_lane = _source_class_lane(
        checkpoint_action_name=checkpoint_action_name,
        authorized_action_name=authorized_action_name,
        source_class=source_class,
    )
    if source_lane is not None:
        lanes.append(source_lane)
    weak_lane = _weak_corpus_lane(
        checkpoint_action_name=checkpoint_action_name,
        authorized_action_name=authorized_action_name,
        weak_corpus=weak_corpus,
    )
    if weak_lane is not None:
        lanes.append(weak_lane)
    conflict_lane = _conflict_lane(
        checkpoint_action_name=checkpoint_action_name,
        authorized_action_name=authorized_action_name,
        conflict=conflict,
        ordinary=ordinary,
        targeted=targeted,
    )
    if conflict_lane is not None:
        lanes.append(conflict_lane)
    ordinary_lane = _ordinary_lane(
        checkpoint_action_name=checkpoint_action_name,
        authorized_action_name=authorized_action_name,
        targeted_dispatch_authorized=targeted_dispatch_authorized,
        ordinary=ordinary,
        targeted=targeted,
    )
    if ordinary_lane is not None:
        lanes.append(ordinary_lane)
    return lanes


def _ordinary_lane(
    *,
    checkpoint_action_name: str | None,
    authorized_action_name: str | None,
    targeted_dispatch_authorized: bool,
    ordinary: Mapping[str, Any],
    targeted: Mapping[str, Any],
) -> dict[str, Any] | None:
    source_path = _clean_token(
        ordinary.get("source_path") or ordinary.get("query_provenance")
    )
    lane_info = _ORDINARY_SOURCE_TO_LANE.get(source_path or "")
    ordinary_queries = _compact_strings(ordinary.get("ordinary_next_queries"))
    if not ordinary_queries:
        ordinary_queries = _compact_strings(
            targeted.get("targeted_retrieval_candidate_queries")
        )
    conflict_queries = _compact_strings(
        ordinary.get("conflict_resolving_queries")
    )
    if not conflict_queries:
        conflict_queries = _compact_strings(
            targeted.get(
                "targeted_retrieval_candidate_conflict_resolving_queries"
            )
        )
    considered = bool(
        ordinary.get("considered")
        or ordinary_queries
        or targeted.get("targeted_retrieval_candidate_considered")
    )
    if lane_info is None and not considered:
        return None
    if lane_info is None:
        lane_type = "ordinary_unknown_queries"
        lane_source = "ordinary_continuation"
        owner = "ordinary_continuation"
        obligation = "ordinary continuation gap"
    else:
        lane_type, lane_source, owner, obligation = lane_info

    blockers = _compact_strings(ordinary.get("blockers")) + _compact_strings(
        targeted.get("targeted_retrieval_candidate_blockers")
    )
    if conflict_queries:
        blockers = tuple(
            list(blockers) + ["conflict_resolving_queries_present"]
        )
    authorized = bool(
        authorized_action_name == RETRIEVE_TARGETED
        and targeted_dispatch_authorized
        and lane_info is not None
        and ordinary_queries
        and not conflict_queries
        and (
            ordinary.get("currently_spine_authorized")
            or targeted.get("targeted_retrieval_candidate_used")
            or targeted.get("targeted_retrieval_candidate_eligible")
        )
    )
    if authorized:
        status = "authorized"
        blockers = ()
    elif not considered:
        status = "skipped"
        blockers = blockers or ("not_evaluated",)
    elif checkpoint_action_name in {
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        RECOVER_MISSING_SOURCE_CLASS,
        RECOVER_WEAK_CORPUS,
        RESOLVE_CONFLICT,
    }:
        status = "blocked"
        blockers = blockers or (f"blocked_by_{checkpoint_action_name}",)
    else:
        status = "blocked"
        blockers = blockers or (
            _string_or_none(targeted.get("targeted_retrieval_candidate_reason"))
            or _string_or_none(ordinary.get("reason"))
            or "targeted_retrieval_not_authorized",
        )

    return _lane(
        lane_id=lane_type,
        lane_type=lane_type,
        lane_source=lane_source,
        query_provenance=source_path,
        query_generation_owner=owner,
        approved_queries=ordinary_queries if authorized else (),
        prior_queries=_compact_strings(ordinary.get("prior_queries")),
        conflict_resolving_queries=conflict_queries,
        contract_gap_addressed=_string_or_none(
            targeted.get("targeted_retrieval_candidate_reason")
            or ordinary.get("reason")
        ),
        evidence_obligation=obligation,
        source_class_obligations=(),
        currentness_obligations=_currentness_obligations(targeted),
        status=status,
        blockers=blockers,
        used=bool(authorized and ordinary.get("used")),
    )


def _source_class_lane(
    *,
    checkpoint_action_name: str | None,
    authorized_action_name: str | None,
    source_class: Mapping[str, Any],
) -> dict[str, Any] | None:
    queries = _compact_strings(
        source_class.get("active_source_class_recovery_queries")
    )
    missing = _compact_strings(
        source_class.get("active_source_class_recovery_missing_classes")
    )
    considered = bool(
        source_class.get("active_source_class_recovery_considered")
        or source_class.get("active_source_class_recovery_eligible")
        or source_class.get("active_source_class_recovery_used")
        or queries
        or missing
        or checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS
    )
    if not considered:
        return None
    authorized = bool(
        authorized_action_name == RECOVER_MISSING_SOURCE_CLASS
        or source_class.get("active_source_class_recovery_used")
    )
    blockers = _compact_strings(
        source_class.get("active_source_class_recovery_blockers")
    )
    return _lane(
        lane_id=SOURCE_CLASS_RECOVERY_QUERIES,
        lane_type=SOURCE_CLASS_RECOVERY_QUERIES,
        lane_source="source_class_recovery",
        query_provenance="source_class_recovery_queries" if queries else None,
        query_generation_owner="source_class_controller",
        approved_queries=queries if authorized else (),
        prior_queries=(),
        conflict_resolving_queries=(),
        contract_gap_addressed=_string_or_none(
            source_class.get("active_source_class_recovery_reason")
        ),
        evidence_obligation="missing required source class recovery",
        source_class_obligations=missing,
        currentness_obligations=(),
        status=_authorized_or_blocked_status(authorized, blockers),
        blockers=() if authorized else blockers or ("source_class_recovery_not_authorized",),
        used=bool(source_class.get("active_source_class_recovery_used")),
    )


def _weak_corpus_lane(
    *,
    checkpoint_action_name: str | None,
    authorized_action_name: str | None,
    weak_corpus: Mapping[str, Any],
) -> dict[str, Any] | None:
    queries = _compact_strings(weak_corpus.get("weak_corpus_recovery_queries"))
    considered = bool(
        weak_corpus.get("weak_corpus_recovery_considered")
        or weak_corpus.get("weak_corpus_recovery_used")
        or queries
        or checkpoint_action_name == RECOVER_WEAK_CORPUS
    )
    if not considered:
        return None
    authorized = bool(
        authorized_action_name == RECOVER_WEAK_CORPUS
        or weak_corpus.get("weak_corpus_recovery_used")
    )
    blockers = _compact_strings(weak_corpus.get("weak_corpus_recovery_blockers"))
    return _lane(
        lane_id=WEAK_CORPUS_RECOVERY_QUERIES,
        lane_type=WEAK_CORPUS_RECOVERY_QUERIES,
        lane_source="weak_corpus_recovery",
        query_provenance="weak_corpus_recovery_queries" if queries else None,
        query_generation_owner="weak_corpus_controller",
        approved_queries=queries if authorized else (),
        prior_queries=(),
        conflict_resolving_queries=(),
        contract_gap_addressed=_string_or_none(
            weak_corpus.get("weak_corpus_recovery_reason")
        ),
        evidence_obligation="weak corpus recovery",
        source_class_obligations=(),
        currentness_obligations=(),
        status=_authorized_or_blocked_status(authorized, blockers),
        blockers=() if authorized else blockers or ("weak_corpus_recovery_not_authorized",),
        used=bool(weak_corpus.get("weak_corpus_recovery_used")),
    )


def _conflict_lane(
    *,
    checkpoint_action_name: str | None,
    authorized_action_name: str | None,
    conflict: Mapping[str, Any],
    ordinary: Mapping[str, Any],
    targeted: Mapping[str, Any],
) -> dict[str, Any] | None:
    queries = _compact_strings(conflict.get("active_conflict_resolution_queries"))
    if not queries:
        queries = _compact_strings(ordinary.get("conflict_resolving_queries"))
    if not queries:
        queries = _compact_strings(
            targeted.get(
                "targeted_retrieval_candidate_conflict_resolving_queries"
            )
        )
    considered = bool(
        conflict.get("active_conflict_resolution_considered")
        or conflict.get("active_conflict_resolution_eligible")
        or conflict.get("active_conflict_resolution_used")
        or queries
        or checkpoint_action_name == RESOLVE_CONFLICT
    )
    if not considered:
        return None
    authorized = bool(
        authorized_action_name == RESOLVE_CONFLICT
        or conflict.get("active_conflict_resolution_used")
    )
    blockers = _compact_strings(conflict.get("active_conflict_resolution_blockers"))
    return _lane(
        lane_id=CONFLICT_RESOLVING_QUERIES,
        lane_type=CONFLICT_RESOLVING_QUERIES,
        lane_source="conflict_resolution",
        query_provenance="conflict_resolving_queries" if queries else None,
        query_generation_owner="conflict_controller",
        approved_queries=queries if authorized else (),
        prior_queries=(),
        conflict_resolving_queries=queries,
        contract_gap_addressed=_string_or_none(
            conflict.get("active_conflict_resolution_reason")
        ),
        evidence_obligation="conflict resolution",
        source_class_obligations=(),
        currentness_obligations=(),
        status=_authorized_or_blocked_status(authorized, blockers),
        blockers=() if authorized else blockers or ("conflict_resolution_not_authorized",),
        used=bool(conflict.get("active_conflict_resolution_used")),
    )


def _lane(
    *,
    lane_id: str,
    lane_type: str,
    lane_source: str,
    query_provenance: str | None,
    query_generation_owner: str,
    approved_queries: Any,
    prior_queries: Any,
    conflict_resolving_queries: Any,
    contract_gap_addressed: str | None,
    evidence_obligation: str,
    source_class_obligations: Any,
    currentness_obligations: Any,
    status: str,
    blockers: Any,
    used: bool,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "lane_type": lane_type,
        "lane_source": lane_source,
        "query_provenance": query_provenance,
        "query_generation_owner": query_generation_owner,
        "approved_queries": list(_compact_strings(approved_queries)),
        "prior_queries": list(_compact_strings(prior_queries)),
        "conflict_resolving_queries": list(
            _compact_strings(conflict_resolving_queries)
        ),
        "contract_gap_addressed": contract_gap_addressed,
        "evidence_obligation": evidence_obligation,
        "source_class_obligations": list(
            _compact_strings(source_class_obligations)
        ),
        "currentness_obligations": list(_compact_strings(currentness_obligations)),
        "provider_policy": "reuse_existing",
        "depth_policy": "reuse_existing",
        "status": status,
        "blockers": list(_compact_strings(blockers)),
        "used": bool(used),
        "trace_visibility": {
            "sanitized_queries": True,
            "raw_prompt": False,
            "raw_provider_payload": False,
            "private_runtime_state": False,
        },
    }


def _authorized_or_blocked_status(authorized: bool, blockers: tuple[str, ...]) -> str:
    if authorized:
        return "authorized"
    if blockers:
        return "blocked"
    return "skipped"


def _selected_lane(lanes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for lane in lanes:
        if lane.get("status") == "authorized":
            return lane
    return None


def _lane_queries(lane: Mapping[str, Any]) -> list[str]:
    queries = _compact_strings(lane.get("approved_queries"))
    if not queries and lane.get("lane_type") == CONFLICT_RESOLVING_QUERIES:
        queries = _compact_strings(lane.get("conflict_resolving_queries"))
    return list(queries)


def _apply_authorized_dispatch_overlay(
    *,
    projection: Mapping[str, Any],
    dispatch_trace: Mapping[str, Any],
) -> dict[str, Any]:
    active_projection = _json_safe_mapping(projection)
    dispatch = _json_safe_mapping(dispatch_trace)
    selected_lane_type = _clean_token(
        dispatch.get("selected_lane_type") or dispatch.get("selected_lane_id")
    )
    if (
        dispatch.get("dispatch_authorized") is not True
        or selected_lane_type not in _ORDINARY_LANE_TYPES
    ):
        return active_projection

    lanes = [
        _json_safe_mapping(lane)
        for lane in active_projection.get("lanes") or []
        if isinstance(lane, Mapping)
    ]
    if any(
        lane.get("status") == "authorized"
        and lane.get("lane_type") in _SEPARATE_LANE_TYPES
        for lane in lanes
    ):
        return active_projection

    selected_lane = _overlay_selected_dispatch_lane(
        lanes=lanes,
        selected_lane_type=selected_lane_type,
        dispatch_trace=dispatch,
    )
    if selected_lane is None:
        return active_projection

    selected_queries = _lane_queries(selected_lane)
    authorized_lane_ids = [
        str(lane["lane_id"])
        for lane in lanes
        if lane.get("status") == "authorized" and lane.get("lane_id")
    ]
    blocked_lane_ids = [
        str(lane["lane_id"])
        for lane in lanes
        if lane.get("status") in {"blocked", "skipped", "future_non_authorized"}
        and lane.get("lane_id")
    ]
    authorization = _json_safe_mapping(active_projection.get("authorization"))
    readiness_summary = _json_safe_mapping(dispatch.get("readiness_summary"))
    constraints = _json_safe_mapping(active_projection.get("constraints"))
    handoff_summary = _json_safe_mapping(active_projection.get("handoff_summary"))
    lane_types = _dedupe_strings(
        lane["lane_type"] for lane in lanes if lane.get("lane_type")
    )
    evidence_obligations = _dedupe_strings(
        lane["evidence_obligation"]
        for lane in lanes
        if lane.get("evidence_obligation")
    )

    active_projection.update(
        {
            "batch_id": _batch_id(RETRIEVE_TARGETED, selected_lane),
            "action_name": RETRIEVE_TARGETED,
            "promoted_action_name": RETRIEVE_TARGETED,
            "authorized_action_name": RETRIEVE_TARGETED,
            "batch_status": "authorized",
            "batch_reason": (
                _string_or_none(selected_lane.get("contract_gap_addressed"))
                or "authorized_dispatch_trace_selected_lane"
            ),
            "lanes": lanes,
            "authorized_lane_count": len(authorized_lane_ids),
            "blocked_lane_count": len(blocked_lane_ids),
            "selected_lane": selected_lane.get("lane_id"),
            "query_count": len(selected_queries),
            "dispatch_owner": (
                _string_or_none(dispatch.get("dispatch_owner"))
                or active_projection.get("dispatch_owner")
            ),
            "dispatch_projection_consistency": {
                "dispatch_trace_authoritative": True,
                "projection_reconciled_with_dispatch": True,
                "selected_lane_type": selected_lane_type,
                "projection_scope": (
                    "final_runtime_projection_reconciled_with_active_dispatch"
                ),
            },
        }
    )
    constraints["no_targeted_executor"] = not bool(
        dispatch.get("targeted_retrieval_executor_dispatched")
    )
    active_projection["constraints"] = constraints
    authorization.update(
        {
            "projected_authorized_from_spine": True,
            "dispatch_authorized": True,
            "executor_dispatched": False,
            "promoted_action_name": RETRIEVE_TARGETED,
            "authorized_action_name": RETRIEVE_TARGETED,
            "allowed_lane_ids": authorized_lane_ids,
            "blocked_lane_ids": blocked_lane_ids,
            "checkpoint_decision_count": (
                readiness_summary.get("checkpoint_decision_count")
                or authorization.get("checkpoint_decision_count")
                or 1
            ),
        }
    )
    active_projection["authorization"] = authorization
    handoff_summary.update(
        {
            "action_name": RETRIEVE_TARGETED,
            "approved_query_count": len(selected_queries),
            "lane_types": lane_types,
            "evidence_obligations": evidence_obligations,
            "provider_policy": "reuse_existing",
            "depth_policy": "reuse_existing",
            "runtime_handoff_changed": False,
        }
    )
    active_projection["handoff_summary"] = handoff_summary
    return active_projection


def _overlay_selected_dispatch_lane(
    *,
    lanes: list[dict[str, Any]],
    selected_lane_type: str,
    dispatch_trace: Mapping[str, Any],
) -> dict[str, Any] | None:
    selected_lane = next(
        (
            lane
            for lane in lanes
            if lane.get("lane_type") == selected_lane_type
            or lane.get("lane_id") == selected_lane_type
        ),
        None,
    )
    if selected_lane is None:
        selected_lane = _dispatch_lane_from_trace(
            selected_lane_type=selected_lane_type,
            dispatch_trace=dispatch_trace,
        )
        if selected_lane is None:
            return None
        lanes.append(selected_lane)

    authorized_queries = _compact_strings(dispatch_trace.get("authorized_queries"))
    selected_lane["lane_id"] = selected_lane_type
    selected_lane["lane_type"] = selected_lane_type
    selected_lane["status"] = "authorized"
    selected_lane["blockers"] = []
    if authorized_queries:
        selected_lane["approved_queries"] = list(authorized_queries)
    selected_lane["query_provenance"] = (
        _string_or_none(dispatch_trace.get("query_provenance"))
        or selected_lane.get("query_provenance")
    )
    selected_lane["used"] = True
    return selected_lane


def _dispatch_lane_from_trace(
    *,
    selected_lane_type: str,
    dispatch_trace: Mapping[str, Any],
) -> dict[str, Any] | None:
    lane_defaults = _ORDINARY_LANE_TO_SOURCE.get(selected_lane_type)
    if lane_defaults is None:
        return None
    source_path, lane_source, owner, obligation = lane_defaults
    return _lane(
        lane_id=selected_lane_type,
        lane_type=selected_lane_type,
        lane_source=lane_source,
        query_provenance=(
            _string_or_none(dispatch_trace.get("query_provenance"))
            or source_path
        ),
        query_generation_owner=owner,
        approved_queries=_compact_strings(dispatch_trace.get("authorized_queries")),
        prior_queries=(),
        conflict_resolving_queries=(),
        contract_gap_addressed="authorized_dispatch_trace_selected_lane",
        evidence_obligation=obligation,
        source_class_obligations=(),
        currentness_obligations=(),
        status="authorized",
        blockers=(),
        used=True,
    )


def _batch_status(
    *,
    lanes: list[dict[str, Any]],
    checkpoint_action_name: str | None,
    targeted_dispatch_authorized: bool,
    batch_blockers: list[str],
) -> str:
    if any(lane.get("status") == "authorized" for lane in lanes):
        return "authorized"
    if checkpoint_action_name == RETRIEVE_TARGETED and not targeted_dispatch_authorized:
        return "blocked"
    if batch_blockers:
        return "blocked"
    if lanes:
        return "skipped"
    return "not_applicable"


def _batch_reason(
    *,
    selected_lane: Mapping[str, Any] | None,
    batch_status: str,
    checkpoint: Mapping[str, Any],
    targeted: Mapping[str, Any],
    batch_blockers: list[str],
) -> str:
    if selected_lane:
        return (
            _string_or_none(selected_lane.get("contract_gap_addressed"))
            or "selected_lane_authorized"
        )
    if batch_blockers:
        return batch_blockers[0]
    return (
        _string_or_none(targeted.get("targeted_retrieval_candidate_reason"))
        or _string_or_none(checkpoint.get("reason"))
        or batch_status
    )


def _batch_blockers(
    *,
    lanes: list[dict[str, Any]],
    checkpoint: Mapping[str, Any],
    targeted: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for lane in lanes:
        if lane.get("status") in {"blocked", "skipped"}:
            blockers.extend(_compact_strings(lane.get("blockers")))
    blockers.extend(
        _compact_strings(targeted.get("targeted_retrieval_candidate_blockers"))
    )
    blockers.extend(
        _compact_strings(
            _json_safe_mapping(checkpoint.get("blocked_or_skipped_actions")).values()
        )
    )
    return list(_dedupe_strings(blockers))


def _batch_id(action_name: str | None, selected_lane: Mapping[str, Any] | None) -> str:
    lane_id = (
        _clean_token(selected_lane.get("lane_id")) if isinstance(selected_lane, Mapping) else None
    )
    action = _clean_token(action_name) or "not_applicable"
    return f"ag46b:{action}:{lane_id or 'no_selected_lane'}"


def _checkpoint_decision_count(checkpoint: Mapping[str, Any]) -> int:
    value = checkpoint.get("checkpoint_decision_count")
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 1 if _action_name_from_checkpoint(checkpoint) else 0


def _action_name_from_checkpoint(checkpoint: Mapping[str, Any]) -> str | None:
    action = _string_or_none(checkpoint.get("checkpoint_action_name"))
    if action:
        return action
    decision = checkpoint.get("decision")
    if isinstance(decision, Mapping):
        action = _string_or_none(decision.get("action_name"))
        if action:
            return action
    return _string_or_none(checkpoint.get("recommended_action_name"))


def _currentness_obligations(targeted: Mapping[str, Any]) -> tuple[str, ...]:
    obligations: list[str] = []
    flag_to_name = {
        "targeted_retrieval_candidate_currentness_gap_detected": "currentness_gap",
        "targeted_retrieval_candidate_official_current_source_gap": (
            "official_current_source_gap"
        ),
        "targeted_retrieval_candidate_legal_or_regulatory_current_event_gap": (
            "legal_or_regulatory_current_event_gap"
        ),
        "targeted_retrieval_candidate_reputable_news_or_primary_update_needed": (
            "reputable_news_or_primary_update_needed"
        ),
    }
    for key, name in flag_to_name.items():
        if targeted.get(key):
            obligations.append(name)
    return tuple(obligations)


def _json_safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _json_safe_value(item)
    return out


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe_value(item) for item in sorted(value, key=str)]
    return _clean_text(value, limit=300)


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
    return _dedupe_strings(iterable)


def _dedupe_strings(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = _clean_text(item, limit=300)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _string_or_none(value: Any) -> str | None:
    return _clean_text(value, limit=300)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "CONFLICT_RESOLVING_QUERIES",
    "FUTURE_LEGAL_CURRENT_PRIMARY_ADAPTER_LANE",
    "FUTURE_SOCIAL_SIGNAL_QUERIES",
    "ORDINARY_EVALUATOR_GAP_QUERIES",
    "ORDINARY_EXPANDER_COMPONENT_QUERIES",
    "ORDINARY_SCOUT_DIRECTED_QUERIES",
    "RETRIEVAL_BATCH_PROJECTION_SCHEMA_VERSION",
    "RETRIEVAL_BATCH_PROJECTION_TRACE_KEY",
    "SOURCE_CLASS_RECOVERY_QUERIES",
    "WEAK_CORPUS_RECOVERY_QUERIES",
    "RetrievalBatchLaneType",
    "RetrievalBatchProjectionFacts",
    "build_retrieval_batch_projection_trace",
    "lane_type_for_ordinary_source",
    "retrieval_batch_projection_defaults",
]
