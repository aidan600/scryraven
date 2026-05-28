"""Mechanical runner for Controller-approved source-class recovery dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_provider_search_allocation import (
    ProviderSearchAllocationGateResult,
    record_provider_search_allocation_if_controller_authorized,
)
from core.controller_recovery_decision import ControllerRecoveryDecision
from core.run_controller import RunController
from core.source_class_recovery_executor import (
    execute_source_class_recovery_action,
    record_source_class_recovery_execution_blocked_if_needed,
)


@dataclass(frozen=True)
class SourceClassRecoveryRunnerContext:
    controller: RunController
    authorized_spine_action: str | None
    controller_recovery_decision: ControllerRecoveryDecision | None
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


def run_source_class_recovery_dispatch(
    context: SourceClassRecoveryRunnerContext,
) -> SourceClassRecoveryRunnerResult:
    """Dispatch one source-class recovery action without making recovery decisions."""

    provider_search_allocation = (
        record_provider_search_allocation_if_controller_authorized(
            context.lifecycle_trace,
            context.controller_recovery_decision,
        )
    )
    if provider_search_allocation.allocated:
        source_class_recovery_execution = {
            "attempted": False,
            "result_count": 0,
            "new_url_count": 0,
        }
    elif context.authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS:
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
    else:
        record_source_class_recovery_execution_blocked_if_needed(
            context.lifecycle_trace,
            authorized_for_executor=False,
            blocker_reason="source_class_recovery_executor_dispatch_not_authorized",
        )
        source_class_recovery_execution = {
            "attempted": False,
            "result_count": 0,
            "new_url_count": 0,
        }

    if not source_class_recovery_execution["attempted"]:
        return SourceClassRecoveryRunnerResult(
            source_class_recovery_execution=source_class_recovery_execution,
            total_urls_delta=0,
            total_chunks_delta=0,
            provider_search_allocation=provider_search_allocation,
        )

    return SourceClassRecoveryRunnerResult(
        source_class_recovery_execution=source_class_recovery_execution,
        total_urls_delta=int(source_class_recovery_execution["new_url_count"]),
        total_chunks_delta=int(source_class_recovery_execution["result_count"]),
        provider_search_allocation=provider_search_allocation,
    )


__all__ = [
    "SourceClassRecoveryRunnerContext",
    "SourceClassRecoveryRunnerResult",
    "run_source_class_recovery_dispatch",
]
