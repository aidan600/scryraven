"""Canonical provider/search allocation review gate for bounded review cleanup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PROVIDER_SEARCH_ALLOCATION_TRACE_KEY = "provider_search_allocation_trace"
PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION = (
    "canonical_provider_search_allocation_gate_ag95q_v1"
)
PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY = (
    "provider_search_allocation_execution_trace"
)
PROVIDER_SEARCH_ALLOCATION_EXECUTION_SCHEMA_VERSION = (
    "canonical_provider_review_allocation_execution_ag95q_v1"
)
PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY = "allocation_result_summaries"
PROVIDER_SEARCH_REVIEW_REQUEST = "request_provider_search_review"
PROVIDER_SEARCH_ALLOCATION_ACTION = "record_provider_search_review_request"
PROVIDER_SEARCH_ALLOCATION_EXECUTION_ACTION = (
    "execute_bounded_provider_search_review_request"
)
BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE = (
    "bounded_existing_source_class_recovery_profile_v1"
)
PROVIDER_SEARCH_ALLOCATION_OWNER = "RunAuthorityProviderReviewAllocation"
PROVIDER_SEARCH_ALLOCATION_AUTHORITY_SOURCE = (
    "authority_lifecycle.search_judgment_lifecycle_state"
)

_NO_CANDIDATE_REASON = "no_candidate_acquired_provider_search_review_needed"
_NO_CANDIDATE_STATE = "no_plausible_official_current_candidate_acquired"
_SOURCE_CLASS_RECOVERY_PROVIDER_ROLE = "source_class_recovery"
_OFFICIAL_CURRENT_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)


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
    """Existing runner-owned provider/search inputs for bounded execution."""

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


@dataclass(frozen=True)
class ProviderReviewAllocationRequest:
    """Canonical provider-review action consumed by the allocation helper."""

    decision: str = PROVIDER_SEARCH_REVIEW_REQUEST
    decision_reason: str = _NO_CANDIDATE_REASON
    candidate_state_summary: str = _NO_CANDIDATE_STATE
    allowed_executor_action: str = PROVIDER_SEARCH_ALLOCATION_ACTION
    allocation_owner: str = PROVIDER_SEARCH_ALLOCATION_OWNER
    authority_source: str = PROVIDER_SEARCH_ALLOCATION_AUTHORITY_SOURCE


def build_provider_review_allocation_request(
    lifecycle_trace: Mapping[str, Any] | None,
) -> ProviderReviewAllocationRequest | None:
    """Return the canonical provider-review action when lifecycle state allows it."""

    trace = lifecycle_trace if isinstance(lifecycle_trace, Mapping) else {}
    if _canonical_source_class_action_approved(trace):
        return None
    if _source_obligation_status(trace) != "official_current_required_unmet":
        return None
    if _hard_blocker_present(trace):
        return None
    if _recovery_budget_state(trace) != "exhausted":
        return None
    if _candidate_state_summary(trace) != _NO_CANDIDATE_STATE:
        return None
    return ProviderReviewAllocationRequest()


def build_provider_search_allocation_record(
    request: ProviderReviewAllocationRequest | None,
) -> dict[str, Any] | None:
    """Return a bounded allocation-review record only for canonical approval."""

    if request is None:
        return None
    if request.decision != PROVIDER_SEARCH_REVIEW_REQUEST:
        return None
    if request.allowed_executor_action != PROVIDER_SEARCH_ALLOCATION_ACTION:
        return None
    if (
        request.decision_reason != _NO_CANDIDATE_REASON
        and request.candidate_state_summary != _NO_CANDIDATE_STATE
    ):
        return None

    return {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "allocation_owner": request.allocation_owner,
        "authority_source": request.authority_source,
        "mechanical_owner": "source_class_recovery_runner",
        "decision": PROVIDER_SEARCH_REVIEW_REQUEST,
        "decision_reason": request.decision_reason,
        "candidate_state_summary": request.candidate_state_summary,
        "allocation_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
        "allocation_shape": "bounded_record_plus_execution_provider_search_review",
        "execution_mode": "record_plus_optional_bounded_existing_provider_call",
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
    request: ProviderReviewAllocationRequest,
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
        "allocation_owner": request.allocation_owner,
        "authority_source": request.authority_source,
        "mechanical_owner": "source_class_recovery_runner",
        "authorized_decision": PROVIDER_SEARCH_REVIEW_REQUEST,
        "authorized_executor_action": request.allowed_executor_action,
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
    request: ProviderReviewAllocationRequest,
    reason: str,
    provider_role: str | None = None,
    search_depth: str | None = None,
    query_count: int = 0,
) -> dict[str, Any]:
    return _base_execution_trace(
        request=request,
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


def execute_provider_search_allocation_if_authority_authorized(
    request: ProviderReviewAllocationRequest | None,
    execution_context: ProviderSearchAllocationExecutionContext | None,
) -> dict[str, Any] | None:
    """Execute the bounded existing-provider profile only after canonical approval."""

    if build_provider_search_allocation_record(request) is None:
        return None
    assert request is not None

    if execution_context is None:
        return _unexecutable_execution_trace(
            request=request,
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
            request=request,
            reason="missing_process_search_queries",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if provider_role != _SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
        return _unexecutable_execution_trace(
            request=request,
            reason="missing_or_unsupported_provider_role",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if not queries:
        return _unexecutable_execution_trace(
            request=request,
            reason="missing_existing_action_queries",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=0,
        )
    if not search_depth:
        return _unexecutable_execution_trace(
            request=request,
            reason="missing_existing_action_search_depth",
            provider_role=provider_role,
            search_depth=search_depth,
            query_count=len(queries),
        )
    if not execution_context.search_providers:
        return _unexecutable_execution_trace(
            request=request,
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
        request=request,
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
        "retrieval_pass_id": "canonical_provider_review_allocation_result",
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


def record_provider_search_allocation_if_authority_authorized(
    lifecycle_trace: dict[str, Any],
    execution_context: ProviderSearchAllocationExecutionContext | None = None,
) -> ProviderSearchAllocationGateResult:
    """Record a provider/search allocation review request if canonically approved."""

    request = build_provider_review_allocation_request(lifecycle_trace)
    record = build_provider_search_allocation_record(request)
    if record is None:
        return ProviderSearchAllocationGateResult(
            allocated=False,
            reason="canonical_provider_review_allocation_not_requested",
        )

    execution_trace = execute_provider_search_allocation_if_authority_authorized(
        request,
        execution_context,
    )
    if execution_trace is None:
        execution_trace = _unexecutable_execution_trace(
            request=request,
            reason="canonical_provider_review_allocation_not_requested",
        )

    lifecycle_trace["provider_review_allocation_request"] = (
        PROVIDER_SEARCH_REVIEW_REQUEST
    )
    lifecycle_trace["provider_review_allocation_reason"] = request.decision_reason
    lifecycle_trace["provider_review_allocation_owner"] = request.allocation_owner
    lifecycle_trace[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY] = {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "trace_mode": "canonical_provider_review_allocation_execution",
        "ProviderSearchAllocation": dict(record),
        PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: dict(execution_trace),
        "ProviderSearchAllocationExecution": dict(execution_trace),
    }
    lifecycle_trace["active_source_class_recovery_skip_reason"] = (
        "canonical_provider_review_allocation_requested"
    )
    lifecycle_trace["active_source_class_recovery_blockers"] = list(
        lifecycle_trace.get("active_source_class_recovery_blockers") or []
    ) + [PROVIDER_SEARCH_REVIEW_REQUEST]

    return ProviderSearchAllocationGateResult(
        allocated=True,
        reason=PROVIDER_SEARCH_ALLOCATION_ACTION,
        trace=dict(record),
        execution_attempted=bool(execution_trace["execution_attempted"]),
        executed=bool(execution_trace["executed"]),
        execution_trace=dict(execution_trace),
    )


def _canonical_source_class_action_approved(trace: Mapping[str, Any]) -> bool:
    if (
        trace.get("active_source_class_recovery_used") is True
        or trace.get("active_source_class_recovery_execution_attempted") is True
    ):
        return False
    authority = trace.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return False
    action = authority.get("recovery_action")
    execution = authority.get("execution_state")
    action = action if isinstance(action, Mapping) else {}
    execution = execution if isinstance(execution, Mapping) else {}
    return bool(
        action.get("action_type") == "recover_missing_source_class"
        and action.get("approved") is True
        and execution.get("state") in {"approved_pending_execution", None}
    )


def _source_obligation_status(trace: Mapping[str, Any]) -> str:
    direct = _clean_summary_text(trace.get("source_obligation_status"), limit=120)
    if direct and direct not in {"unknown", "not_observable"}:
        return direct
    unsatisfied = _string_list(trace.get("unsatisfied_required_source_classes"))
    if not unsatisfied:
        unsatisfied = _string_list(
            trace.get("active_source_class_recovery_missing_classes")
        )
    if any(item in _OFFICIAL_CURRENT_CLASSES for item in unsatisfied):
        return "official_current_required_unmet"
    return "unknown"


def _hard_blocker_present(trace: Mapping[str, Any]) -> bool:
    blockers = set(
        _string_list(trace.get("admission_blockers"))
        + _string_list(trace.get("active_source_class_recovery_blockers"))
        + _string_list(trace.get("source_class_recovery_candidate_v2_blockers"))
        + _string_list(trace.get("candidate_acquisition_blockers"))
    )
    skip_reason = _clean_summary_text(
        trace.get("admission_skip_reason")
        or trace.get("active_source_class_recovery_skip_reason")
        or trace.get("candidate_acquisition_skip_reason"),
        limit=160,
    )
    if blockers & {"terminal_stop_approved", "blocked_by_terminal_stop"}:
        return True
    if blockers & {"budget_hard_exhausted", "already_attempted"}:
        return True
    if skip_reason and "hard_recovery_attempt_cap" in skip_reason:
        return True
    if blockers & {"conflict_resolution_owns_path", "blocked_by_conflict_resolution"}:
        return True
    return bool(
        blockers
        & {
            "blocked_by_provider_policy_change_required",
            "blocked_by_search_depth_escalation_required",
        }
    )


def _recovery_budget_state(trace: Mapping[str, Any]) -> str:
    slot_available = trace.get("recovery_slot_available")
    if slot_available is True:
        return "available"
    if slot_available is False:
        return "exhausted"
    prior = _safe_int(
        trace.get("prior_recovery_attempt_count")
        or trace.get("active_source_class_recovery_attempt_count")
    )
    maximum = _safe_int(trace.get("max_recovery_attempts"))
    if prior is not None and maximum is not None:
        return "available" if prior < maximum else "exhausted"
    if (
        trace.get("active_source_class_recovery_eligible") is True
        or trace.get("source_class_recovery_eligible") is True
    ):
        return "available"
    return "unknown"


def _candidate_state_summary(trace: Mapping[str, Any]) -> str:
    candidate_status = _clean_summary_text(trace.get("candidate_return_status"), limit=120)
    recovered_result = _safe_int(
        trace.get("recovered_result_count")
        or trace.get("active_source_class_recovery_result_count")
    )
    if recovered_result == 0 or candidate_status == "zero_candidates":
        return _NO_CANDIDATE_STATE
    final_selected = _safe_int(trace.get("final_selected_authority_evidence_count"))
    final_evidence = _safe_int(trace.get("final_evidence_official_or_canonical_count"))
    final_citation = _safe_int(trace.get("final_citation_official_or_canonical_count"))
    if (final_selected and final_selected > 0) or (
        final_evidence
        and final_evidence > 0
        and final_citation
        and final_citation > 0
    ):
        return "selected_complete_official_current_evidence_exists"
    official_candidate = _safe_int(trace.get("candidate_official_or_canonical_count"))
    if official_candidate and official_candidate > 0:
        return "official_current_candidate_acquired"
    return "unknown"


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = []
    out: list[str] = []
    for item in values:
        text = _clean_summary_text(item, limit=120)
        if text and text not in {"unknown", "not_observable"}:
            out.append(text)
    return out


__all__ = [
    "BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE",
    "PROVIDER_SEARCH_ALLOCATION_ACTION",
    "PROVIDER_SEARCH_ALLOCATION_AUTHORITY_SOURCE",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_ACTION",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_SCHEMA_VERSION",
    "PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY",
    "PROVIDER_SEARCH_ALLOCATION_OWNER",
    "PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY",
    "PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION",
    "PROVIDER_SEARCH_ALLOCATION_TRACE_KEY",
    "PROVIDER_SEARCH_REVIEW_REQUEST",
    "ProviderReviewAllocationRequest",
    "ProviderSearchAllocationExecutionContext",
    "ProviderSearchAllocationGateResult",
    "build_provider_review_allocation_request",
    "build_provider_search_allocation_record",
    "execute_provider_search_allocation_if_authority_authorized",
    "record_provider_search_allocation_if_authority_authorized",
]
