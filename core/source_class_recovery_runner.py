"""Mechanical runner for canonical source-class recovery dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_provider_search_allocation import (
    ProviderSearchAllocationExecutionContext,
    ProviderSearchAllocationGateResult,
    record_provider_search_allocation_if_authority_authorized,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import (
    execute_source_class_recovery_action,
    record_source_class_recovery_execution_blocked_if_needed,
)


@dataclass(frozen=True)
class SourceClassRecoveryRunnerContext:
    controller: RunController
    lifecycle_trace: dict[str, Any]
    process_search_queries: Any
    all_passages: list[dict[str, Any]]
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
    search_providers: list[str]
    exa_domain_filter: list[str] | None
    entity_hint: str | None
    provider_diagnostics: list[dict[str, Any]]
    retrieval_pass_records: list[dict[str, Any]]
    error_type: type[Exception] = RuntimeError


@dataclass(frozen=True)
class SourceClassRecoveryRunnerResult:
    source_class_recovery_execution: dict[str, int | bool]
    total_urls_delta: int
    total_chunks_delta: int
    provider_search_allocation: ProviderSearchAllocationGateResult | None = None


def _canonical_source_class_recovery_dispatch_authorized(
    lifecycle_trace: dict[str, Any],
) -> tuple[bool, str]:
    if (
        lifecycle_trace.get("active_source_class_recovery_used") is True
        or lifecycle_trace.get("active_source_class_recovery_execution_attempted")
        is True
    ):
        return False, "canonical_recovery_already_attempted"
    authority = lifecycle_trace.get("authority_lifecycle")
    if not isinstance(authority, dict) or not authority:
        return False, "canonical_authority_lifecycle_absent"
    action = authority.get("recovery_action")
    execution = authority.get("execution_state")
    action = action if isinstance(action, dict) else {}
    execution = execution if isinstance(execution, dict) else {}
    checks = (
        (authority.get("recovery_needed") != "required", "canonical_recovery_not_required"),
        (
            action.get("action_type") != RECOVER_MISSING_SOURCE_CLASS,
            "canonical_recovery_action_absent",
        ),
        (action.get("approved") is not True, "canonical_recovery_action_not_approved"),
        (execution.get("state") == "blocked", "canonical_recovery_execution_blocked"),
        (
            execution.get("state") not in {"approved_pending_execution", None},
            "canonical_recovery_execution_not_pending",
        ),
    )
    for blocked, reason in checks:
        if blocked:
            return False, reason
    return True, "canonical_authority_lifecycle_recovery_action"


def _no_execution() -> dict[str, int | bool]:
    return {"attempted": False, "result_count": 0, "new_url_count": 0}


def _active_source_class_recovery_action(controller: RunController) -> Any | None:
    actions = (
        list(controller.state.recovery_action_records)
        + list(controller.ledger.retrieval_actions)
    )
    for action in actions:
        if getattr(action, "name", None) != "source_class_recovery":
            continue
        if getattr(action, "active", None) is True and getattr(action, "shadow", None) is False:
            return action
    return None


def _list_from_trace(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _provider_search_allocation_execution_context(
    context: SourceClassRecoveryRunnerContext,
) -> ProviderSearchAllocationExecutionContext:
    action = _active_source_class_recovery_action(context.controller)
    action_queries = list(getattr(action, "queries", None) or [])
    provider_role = getattr(action, "provider_role", None)
    search_depth = getattr(action, "search_depth", None)
    if not action_queries:
        action_queries = _list_from_trace(
            context.lifecycle_trace.get("active_source_class_recovery_queries")
        )
    if provider_role is None:
        provider_role = context.lifecycle_trace.get(
            "active_source_class_recovery_provider_role"
        )
    if search_depth is None:
        search_depth = context.lifecycle_trace.get(
            "active_source_class_recovery_search_depth"
        )
    return ProviderSearchAllocationExecutionContext(
        process_search_queries=context.process_search_queries,
        queries=[str(query) for query in action_queries],
        provider_role=None if provider_role is None else str(provider_role),
        search_depth=None if search_depth is None else str(search_depth),
        search_providers=list(context.search_providers),
        intent=context.intent,
        complexity=context.complexity,
        results_per_query=context.results_per_query,
        include_domains=list(context.include_domains),
        exclude_domains=list(context.exclude_domains),
        query_embedding=context.query_embedding,
        seen_urls=set(context.seen_urls),
        collected_images=set(context.collected_images),
        embed_provider=context.embed_provider,
        embed_model=context.embed_model,
        local_url=context.local_url,
        embed_texts=context.embed_texts,
        compute_similarities=context.compute_similarities,
        status_container=context.status_container,
        exa_domain_filter=(
            list(context.exa_domain_filter)
            if context.exa_domain_filter is not None
            else None
        ),
        entity_hint=context.entity_hint,
    )


def run_source_class_recovery_dispatch(
    context: SourceClassRecoveryRunnerContext,
) -> SourceClassRecoveryRunnerResult:
    """Dispatch one source-class recovery action without making recovery decisions."""

    canonical_dispatch_authorized, dispatch_reason = (
        _canonical_source_class_recovery_dispatch_authorized(context.lifecycle_trace)
    )
    context.lifecycle_trace["source_class_recovery_dispatch_authority"] = (
        "authority_lifecycle.recovery_action"
    )
    context.lifecycle_trace["source_class_recovery_dispatch_authorized"] = (
        canonical_dispatch_authorized
    )
    context.lifecycle_trace["source_class_recovery_dispatch_reason"] = dispatch_reason

    provider_search_allocation: ProviderSearchAllocationGateResult | None = None
    if canonical_dispatch_authorized:
        blocker_reason = (
            "missing_process_search_queries"
            if not callable(context.process_search_queries)
            else "missing_search_providers"
            if not context.search_providers
            else None
        )
        if blocker_reason is not None:
            record_source_class_recovery_execution_blocked_if_needed(
                context.lifecycle_trace,
                authorized_for_executor=False,
                blocker_reason=blocker_reason,
            )
            source_class_recovery_execution = _no_execution()
        else:
            source_class_recovery_execution = execute_source_class_recovery_action(
                context.controller,
                lifecycle_trace=context.lifecycle_trace,
                process_search_queries=context.process_search_queries,
                all_passages=context.all_passages,
                intent=context.intent,
                complexity=context.complexity,
                results_per_query=context.results_per_query,
                include_domains=context.include_domains,
                exclude_domains=context.exclude_domains,
                query_embedding=context.query_embedding,
                seen_urls=context.seen_urls,
                collected_images=context.collected_images,
                embed_provider=context.embed_provider,
                embed_model=context.embed_model,
                local_url=context.local_url,
                embed_texts=context.embed_texts,
                compute_similarities=context.compute_similarities,
                status_container=context.status_container,
                search_providers=context.search_providers,
                exa_domain_filter=context.exa_domain_filter,
                entity_hint=context.entity_hint,
                provider_diagnostics=context.provider_diagnostics,
                retrieval_pass_records=context.retrieval_pass_records,
                error_type=context.error_type,
            )
        provider_search_allocation = ProviderSearchAllocationGateResult(
            allocated=False,
            reason="canonical_source_class_recovery_permission_active",
        )
    else:
        provider_search_allocation = (
            record_provider_search_allocation_if_authority_authorized(
                context.lifecycle_trace,
                _provider_search_allocation_execution_context(context),
            )
        )
        if provider_search_allocation.allocated:
            source_class_recovery_execution = _no_execution()
        else:
            record_source_class_recovery_execution_blocked_if_needed(
                context.lifecycle_trace,
                authorized_for_executor=False,
                blocker_reason=dispatch_reason,
            )
            context.lifecycle_trace["active_source_class_recovery_skip_reason"] = (
                context.lifecycle_trace.get("active_source_class_recovery_skip_reason")
                or dispatch_reason
            )
            blockers = list(
                context.lifecycle_trace.get("active_source_class_recovery_blockers")
                or []
            )
            if dispatch_reason not in blockers:
                blockers.append(dispatch_reason)
            context.lifecycle_trace["active_source_class_recovery_blockers"] = blockers
            source_class_recovery_execution = _no_execution()

    attempted = bool(source_class_recovery_execution["attempted"])
    return SourceClassRecoveryRunnerResult(
        source_class_recovery_execution,
        int(source_class_recovery_execution["new_url_count"]) if attempted else 0,
        int(source_class_recovery_execution["result_count"]) if attempted else 0,
        provider_search_allocation,
    )


__all__ = [
    "SourceClassRecoveryRunnerContext",
    "SourceClassRecoveryRunnerResult",
    "run_source_class_recovery_dispatch",
]
