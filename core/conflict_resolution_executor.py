"""Dependency-injected executor shape for conflict-resolution actions.

This module is wired only behind the AG-37B checkpoint gate. Normal runtime
dispatch still depends on an upstream producer for conflict facts and resolving
queries; this executor does not detect conflicts or generate queries.
"""

from __future__ import annotations

from typing import Any

from core.conflict_resolution_controller import (
    CONFLICT_RESOLUTION_PROVIDER_ROLE,
    CONFLICT_RESOLUTION_STAGE,
    ConflictResolutionDecision,
)

_MAX_EXECUTOR_QUERIES = 2


def execute_conflict_resolution_action(
    decision: ConflictResolutionDecision,
    *,
    lifecycle_trace: dict[str, Any],
    process_conflict_resolution_queries: Any,
    all_passages: list[dict[str, Any]],
    intent: str,
    complexity: str,
    results_per_query: int,
    include_domains: list[str],
    exclude_domains: list[str],
    query_embedding: Any,
    seen_urls: set[str],
    collected_images: set[str],
    embed_provider: str,
    embed_model: str,
    local_url: str,
    embed_texts: Any,
    compute_similarities: Any,
    status_container: Any,
    search_providers: list[str],
    exa_domain_filter: list[str] | None,
    entity_hint: str | None,
    provider_diagnostics: list[dict[str, Any]],
    retrieval_pass_records: list[dict[str, Any]],
    error_type: type[Exception] = RuntimeError,
) -> dict[str, int | bool]:
    """Execute one injected conflict-resolution query pass when approved."""
    if lifecycle_trace.get("active_conflict_resolution_used") is True:
        return {
            "attempted": False,
            "result_count": int(
                lifecycle_trace.get("active_conflict_resolution_result_count") or 0
            ),
            "new_url_count": int(
                lifecycle_trace.get("active_conflict_resolution_new_url_count") or 0
            ),
        }
    if not decision.approved:
        return {"attempted": False, "result_count": 0, "new_url_count": 0}
    if decision.provider_role != CONFLICT_RESOLUTION_PROVIDER_ROLE:
        raise error_type("conflict_resolution action has unexpected provider role")

    queries = list(decision.queries[:_MAX_EXECUTOR_QUERIES])
    search_depth = decision.search_depth
    if not queries or search_depth is None:
        return {"attempted": False, "result_count": 0, "new_url_count": 0}

    lifecycle_trace["active_conflict_resolution_used"] = True
    lifecycle_trace["active_conflict_resolution_attempt_count"] = 1
    seen_before = len(seen_urls)
    resolved_passages = process_conflict_resolution_queries(
        queries,
        intent,
        complexity,
        str(search_depth),
        results_per_query,
        include_domains,
        exclude_domains,
        query_embedding,
        seen_urls,
        collected_images,
        embed_provider,
        embed_model,
        local_url,
        embed_texts,
        compute_similarities,
        status_container=status_container,
        search_providers=list(search_providers),
        exa_domain_filter=exa_domain_filter,
        entity_hint=entity_hint,
        provider_diagnostics=provider_diagnostics,
        provider_role=CONFLICT_RESOLUTION_PROVIDER_ROLE,
    )
    new_url_count = max(0, len(seen_urls) - seen_before)
    usable_passages: list[dict[str, Any]] = []
    for passage in resolved_passages or []:
        if not isinstance(passage, dict):
            continue
        resolved = dict(passage)
        resolved.setdefault("_provider_role", CONFLICT_RESOLUTION_PROVIDER_ROLE)
        resolved.setdefault("retrieval_stage", CONFLICT_RESOLUTION_STAGE)
        usable_passages.append(resolved)

    if usable_passages:
        all_passages.extend(usable_passages)

    result_count = len(usable_passages)
    lifecycle_trace["active_conflict_resolution_result_count"] = result_count
    lifecycle_trace["active_conflict_resolution_new_url_count"] = new_url_count
    retrieval_pass_records.append(
        {
            "stage": CONFLICT_RESOLUTION_STAGE,
            "iteration": None,
            "queries": list(queries),
            "providers": list(search_providers),
            "provider_role": CONFLICT_RESOLUTION_PROVIDER_ROLE,
            "search_depth": str(search_depth),
            "results_per_query": results_per_query,
        }
    )
    return {
        "attempted": True,
        "result_count": result_count,
        "new_url_count": new_url_count,
    }


__all__ = [
    "execute_conflict_resolution_action",
]
