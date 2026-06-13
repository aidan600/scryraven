"""Compatibility provider/search allocation review gate for AG-75A."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    ControllerRecoveryDecision,
)

PROVIDER_SEARCH_ALLOCATION_TRACE_KEY = "provider_search_allocation_trace"
PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION = (
    "controller_provider_search_allocation_gate_ag75a_v1"
)
PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY = (
    "provider_search_allocation_execution_trace"
)
PROVIDER_SEARCH_ALLOCATION_EXECUTION_SCHEMA_VERSION = (
    "controller_authorized_existing_provider_allocation_execution_ag75a_x_v1"
)
PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY = "allocation_result_summaries"
PROVIDER_SEARCH_ALLOCATION_ACTION = "record_provider_search_review_request"
PROVIDER_SEARCH_ALLOCATION_EXECUTION_ACTION = (
    "execute_bounded_provider_search_review_request"
)
BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE = (
    "bounded_existing_source_class_recovery_profile_v1"
)

_NO_CANDIDATE_REASON = "no_candidate_acquired_provider_search_review_needed"
_NO_CANDIDATE_STATE = "no_plausible_official_current_candidate_acquired"
_SOURCE_CLASS_RECOVERY_PROVIDER_ROLE = "source_class_recovery"


@dataclass(frozen=True)
class ProviderSearchAllocationGateResult:
    """Mechanical result for the AG-75A provider/search allocation gate."""

    allocated: bool
    reason: str
    trace: dict[str, Any] | None = None
    execution_attempted: bool = False
    executed: bool = False
    execution_trace: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderSearchAllocationExecutionContext:
    """Existing runner-owned provider/search inputs for AG-75A-X execution."""

    process_search_queries: Any
    queries: list[str]
    provider_role: str | None
    search_depth: str | None
    search_providers: list[str]
    intent: str
    complexity: str
    results_per_query: int
    include_domains: list[str]
    exclude_domains: list[str]
    query_embedding: Any
    seen_urls: set[str]
    collected_images: set[str]
    embed_provider: str
    embed_model: str
    local_url: str
    embed_texts: Any
    compute_similarities: Any
    status_container: Any
    exa_domain_filter: list[str] | None
    entity_hint: str | None


def build_provider_search_allocation_record(
    decision: ControllerRecoveryDecision | None,
) -> dict[str, Any] | None:
    """Return a bounded allocation-review record only for Controller approval."""

    if decision is None:
        return None
    payload = decision.payload
    decision_reason = str(payload.get("decision_reason") or "")
    candidate_state = str(payload.get("candidate_state_summary") or "")
    if decision.decision != REQUEST_PROVIDER_SEARCH_REVIEW:
        return None
    if decision.provider_search_review_requested is not True:
        return None
    if payload.get("allowed_executor_action") != PROVIDER_SEARCH_ALLOCATION_ACTION:
        return None
    if decision_reason != _NO_CANDIDATE_REASON and candidate_state != _NO_CANDIDATE_STATE:
        return None

    return {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "allocation_owner": "ControllerRecoveryDecision",
        "mechanical_owner": "source_class_recovery_runner",
        "decision": REQUEST_PROVIDER_SEARCH_REVIEW,
        "decision_reason": decision_reason,
        "candidate_state_summary": candidate_state,
        "allocation_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
        "allocation_shape": "bounded_record_plus_execution_provider_search_review",
        "execution_mode": "record_plus_optional_bounded_existing_provider_call",
        "provider_search_review_requested": True,
        "provider_policy_unchanged": True,
        "provider_selection_unchanged": True,
        "search_depth_policy_unchanged": True,
        "query_strategy_unchanged": True,
        "source_constraints_unchanged": True,
        "new_provider_added": False,
        "provider_swap": False,
        "unbounded_depth": False,
        "linkup_escalation_added": False,
        "live_validation_used": False,
        "final_answer_behavior_unchanged": True,
        "citation_behavior_unchanged": True,
    }


def _base_execution_trace(
    *,
    decision: ControllerRecoveryDecision,
    execution_mode: str,
    executed: bool,
    execution_attempted: bool,
    unexecutable_reason: str | None,
    provider_role: str | None,
    search_depth: str | None,
    query_count: int,
    result_count: int,
    new_url_count: int,
    allocation_result_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summaries = list(allocation_result_summaries or [])
    return {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_EXECUTION_SCHEMA_VERSION,
        "allocation_owner": "ControllerRecoveryDecision",
        "mechanical_owner": "source_class_recovery_runner",
        "authorized_decision": REQUEST_PROVIDER_SEARCH_REVIEW,
        "authorized_executor_action": decision.payload.get(
            "allowed_executor_action"
        ),
        "bounded_profile": BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
        "execution_mode": execution_mode,
        "executed": bool(executed),
        "execution_attempted": bool(execution_attempted),
        "unexecutable_reason": unexecutable_reason,
        "provider_role": provider_role,
        "search_depth": search_depth,
        "query_count": max(0, int(query_count)),
        "result_count": max(0, int(result_count)),
        "new_url_count": max(0, int(new_url_count)),
        "allocation_result_summary_count": len(summaries),
        PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY: summaries,
        "provider_policy_unchanged": True,
        "provider_selection_unchanged": True,
        "search_depth_policy_unchanged": True,
        "query_strategy_unchanged": True,
        "source_constraints_unchanged": True,
        "new_provider_added": False,
        "provider_swap": False,
        "unbounded_depth": False,
        "linkup_escalation_added": False,
        "live_validation_used": False,
        "final_answer_behavior_unchanged": True,
        "citation_behavior_unchanged": True,
        "raw_payload_exposed": False,
    }


def _unexecutable_execution_trace(
    *,
    decision: ControllerRecoveryDecision,
    reason: str,
    provider_role: str | None = None,
    search_depth: str | None = None,
    query_count: int = 0,
) -> dict[str, Any]:
    return _base_execution_trace(
        decision=decision,
        execution_mode="bounded_existing_provider_allocation_unexecutable",
        executed=False,
        execution_attempted=False,
        unexecutable_reason=reason,
        provider_role=provider_role,
        search_depth=search_depth,
        query_count=query_count,
        result_count=0,
        new_url_count=0,
    )


def execute_provider_search_allocation_if_controller_authorized(
    decision: ControllerRecoveryDecision | None,
    execution_context: ProviderSearchAllocationExecutionContext | None,
) -> dict[str, Any] | None:
    """Execute the bounded existing-provider profile only after Controller approval."""

    if build_provider_search_allocation_record(decision) is None:
        return None
    assert decision is not None

    if execution_context is None:
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_execution_context",
        )

    queries = [
        str(query).strip()
        for query in list(execution_context.queries or [])
        if str(query).strip()
    ]
    provider_role = (
        str(execution_context.provider_role).strip()
        if execution_context.provider_role is not None
        else None
    )
    search_depth = (
        str(execution_context.search_depth).strip()
        if execution_context.search_depth is not None
        else None
    )
    if not callable(execution_context.process_search_queries):
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_process_search_queries",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if provider_role != _SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_or_unsupported_provider_role",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if not queries:
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_existing_action_queries",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=0,
        )
    if not search_depth:
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_existing_action_search_depth",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if not execution_context.search_providers:
        return _unexecutable_execution_trace(
            decision=decision,
            reason="missing_existing_search_providers",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )

    allocation_seen_urls = set(execution_context.seen_urls)
    allocation_collected_images = set(execution_context.collected_images)
    provider_diagnostics: list[dict[str, Any]] = []
    seen_before = len(allocation_seen_urls)
    results = execution_context.process_search_queries(
        queries,
        execution_context.intent,
        execution_context.complexity,
        search_depth,
        execution_context.results_per_query,
        list(execution_context.include_domains),
        list(execution_context.exclude_domains),
        execution_context.query_embedding,
        allocation_seen_urls,
        allocation_collected_images,
        execution_context.embed_provider,
        execution_context.embed_model,
        execution_context.local_url,
        execution_context.embed_texts,
        execution_context.compute_similarities,
        status_container=execution_context.status_container,
        search_providers=list(execution_context.search_providers),
        exa_domain_filter=(
            list(execution_context.exa_domain_filter)
            if execution_context.exa_domain_filter is not None
            else None
        ),
        entity_hint=execution_context.entity_hint,
        provider_diagnostics=provider_diagnostics,
        provider_role=provider_role,
    )
    result_count = sum(1 for result in (results or []) if isinstance(result, dict))
    allocation_result_summaries = _allocation_result_summaries(
        results,
        provider_role=provider_role,
        query_preview=queries[0] if queries else None,
    )
    return _base_execution_trace(
        decision=decision,
        execution_mode="bounded_existing_provider_allocation_executed",
        executed=True,
        execution_attempted=True,
        unexecutable_reason=None,
        provider_role=provider_role,
        search_depth=search_depth,
        query_count=len(queries),
        result_count=result_count,
        new_url_count=max(0, len(allocation_seen_urls) - seen_before),
        allocation_result_summaries=allocation_result_summaries,
    )


def _allocation_result_summaries(
    results: Any,
    *,
    provider_role: str | None,
    query_preview: str | None,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for index, result in enumerate(results or (), start=1):
        if not isinstance(result, dict):
            continue
        summary = _allocation_result_summary(
            result,
            provider_role=provider_role,
            query_preview=query_preview,
            position=index,
        )
        if summary:
            summaries.append(summary)
    return summaries[:20]


def _allocation_result_summary(
    result: dict[str, Any],
    *,
    provider_role: str | None,
    query_preview: str | None,
    position: int,
) -> dict[str, Any]:
    summary = {
        "provider_name": _clean_summary_text(
            result.get("provider_name") or result.get("provider"),
            limit=80,
        )
        or "unknown",
        "provider_role": _clean_summary_text(provider_role, limit=80)
        or "source_class_recovery",
        "retrieval_pass_id": "controller_authorized_allocation_result",
        "query_preview": _clean_summary_text(
            result.get("query_preview") or result.get("query") or query_preview,
            limit=140,
        )
        or "unknown",
        "provider_rank_or_position": _safe_position(result, default=position),
        "source_url": _clean_summary_text(
            result.get("source_url") or result.get("url") or result.get("accepted_url"),
            limit=240,
        ),
        "title": _clean_summary_text(result.get("title"), limit=180),
        "normalized_domain": _clean_summary_text(
            result.get("normalized_domain") or result.get("domain"),
            limit=120,
        ),
        "source_tier": _clean_summary_text(result.get("source_tier"), limit=80),
        "source_class": _clean_summary_text(
            result.get("source_class") or result.get("observed_source_class"),
            limit=80,
        ),
        "provider_returned": True,
        "sanitized": True,
        "raw_payload_exposed": False,
    }
    return {key: value for key, value in summary.items() if value not in {"", None}}


def _clean_summary_text(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit]


def _safe_position(result: dict[str, Any], *, default: int) -> int:
    for key in ("provider_rank_or_position", "rank", "position"):
        try:
            return max(0, int(result.get(key)))
        except (TypeError, ValueError):
            continue
    return default


def record_provider_search_allocation_if_controller_authorized(
    lifecycle_trace: dict[str, Any],
    decision: ControllerRecoveryDecision | None,
    execution_context: ProviderSearchAllocationExecutionContext | None = None,
) -> ProviderSearchAllocationGateResult:
    """Record a provider/search allocation review request if Controller-approved."""

    record = build_provider_search_allocation_record(decision)
    if record is None:
        return ProviderSearchAllocationGateResult(
            allocated=False,
            reason="controller_recovery_decision_did_not_request_provider_search_review",
        )

    execution_trace = execute_provider_search_allocation_if_controller_authorized(
        decision,
        execution_context,
    )
    if execution_trace is None:
        execution_trace = _unexecutable_execution_trace(
            decision=decision,
            reason="controller_recovery_decision_did_not_request_provider_search_review",
        )

    lifecycle_trace.update(decision.to_executor_trace_fields())
    lifecycle_trace[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY] = {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "trace_mode": "controller_authorized_provider_search_allocation_execution",
        "ProviderSearchAllocation": dict(record),
        PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: dict(execution_trace),
        "ProviderSearchAllocationExecution": dict(execution_trace),
    }
    lifecycle_trace["active_source_class_recovery_skip_reason"] = (
        "controller_recovery_decision_requested_provider_search_review"
    )
    lifecycle_trace["active_source_class_recovery_blockers"] = list(
        lifecycle_trace.get("active_source_class_recovery_blockers") or []
    ) + [REQUEST_PROVIDER_SEARCH_REVIEW]

    return ProviderSearchAllocationGateResult(
        allocated=True,
        reason=PROVIDER_SEARCH_ALLOCATION_ACTION,
        trace=dict(record),
        execution_attempted=bool(execution_trace["execution_attempted"]),
        executed=bool(execution_trace["executed"]),
        execution_trace=dict(execution_trace),
    )


__all__ = [
    "BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE",
    "PROVIDER_SEARCH_ALLOCATION_ACTION",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_ACTION",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_SCHEMA_VERSION",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY",
    "PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY",
    "PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION",
    "PROVIDER_SEARCH_ALLOCATION_TRACE_KEY",
    "ProviderSearchAllocationExecutionContext",
    "ProviderSearchAllocationGateResult",
    "build_provider_search_allocation_record",
    "execute_provider_search_allocation_if_controller_authorized",
    "record_provider_search_allocation_if_controller_authorized",
]
