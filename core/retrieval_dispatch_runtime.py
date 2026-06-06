"""Mechanical retrieval dispatch/pass-record runtime helpers.

This module only executes already-authorized retrieval requests and assembles
already-existing pass telemetry. It does not generate or mutate queries, select
providers, choose depth, rank/filter results, import prompt/model code, or make
provider policy decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, MutableSequence, Sequence

from core.retrieval_loop_contract import (
    RetrievalLoopState,
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
    execute_retrieval_pass_handoff,
    summarize_retrieval_pass_result,
)


@dataclass(frozen=True)
class RetrievalDispatchDeps:
    """Existing callable/dependency bundle for a mechanical retrieval call."""

    process_search_queries: Callable[..., list[dict[str, Any]]]
    query_embedding: Any
    seen_urls: set[str]
    collected_images: set[str]
    embed_provider: str
    embed_model: str
    local_url: str | None
    embed_texts: Callable[..., Any]
    compute_similarities: Callable[..., Any]
    status_container: Any
    provider_diagnostics: list[dict[str, Any]]


@dataclass(frozen=True)
class RecordedRetrievalDispatch:
    """Already-authorized dispatch facts supplied by the orchestrator."""

    stage: str
    queries: Sequence[str]
    intent: str
    complexity: str
    search_depth: str
    results_per_query: int
    include_domains: Sequence[str]
    exclude_domains: Sequence[str]
    providers: Sequence[str]
    provider_role: str
    iteration: int | None = None
    exa_domain_filter: Sequence[str] | None = None
    linkup_depth_override: str | None = None
    entity_hint: str | None = None
    prior_queries_for_similarity: Sequence[str] | None = None
    query_similarity_basis: str | None = None


@dataclass(frozen=True)
class RetrievalDispatchOutcome:
    """Mechanical result and caller-owned counter deltas."""

    passages: list[dict[str, Any]]
    pass_record: dict[str, Any]
    seen_url_delta: int
    chunk_delta: int


def build_retrieval_pass_record(
    *,
    stage: str,
    iteration: int | None,
    queries: Sequence[str],
    providers: Sequence[str],
    provider_role: str,
    search_depth: str,
    results_per_query: int,
) -> dict[str, Any]:
    """Build the existing retrieval_pass_records item shape."""

    return {
        "stage": stage,
        "iteration": iteration,
        "queries": list(queries),
        "providers": list(providers),
        "provider_role": provider_role,
        "search_depth": search_depth,
        "results_per_query": results_per_query,
    }


def _append_optional_kwargs(
    kwargs: dict[str, Any],
    dispatch: RecordedRetrievalDispatch,
) -> None:
    if dispatch.exa_domain_filter is not None:
        kwargs["exa_domain_filter"] = list(dispatch.exa_domain_filter)
    if dispatch.linkup_depth_override is not None:
        kwargs["linkup_depth_override"] = dispatch.linkup_depth_override
    if dispatch.entity_hint is not None:
        kwargs["entity_hint"] = dispatch.entity_hint
    kwargs["provider_diagnostics"] = None
    kwargs["provider_role"] = dispatch.provider_role
    if dispatch.iteration is not None:
        kwargs["iteration"] = dispatch.iteration
    if dispatch.prior_queries_for_similarity is not None:
        kwargs["prior_queries_for_similarity"] = list(dispatch.prior_queries_for_similarity)
    if dispatch.query_similarity_basis is not None:
        kwargs["query_similarity_basis"] = dispatch.query_similarity_basis


def execute_recorded_retrieval_dispatch(
    dispatch: RecordedRetrievalDispatch,
    deps: RetrievalDispatchDeps,
    *,
    retrieval_pass_records: MutableSequence[dict[str, Any]] | None = None,
) -> RetrievalDispatchOutcome:
    """Execute an already-authorized retrieval call and optionally record it.

    Provider list, query text/order, depth, result count, and continuation
    decisions are all supplied by the caller.
    """

    seen_before = len(deps.seen_urls)
    kwargs: dict[str, Any] = {
        "status_container": deps.status_container,
        "search_providers": list(dispatch.providers),
    }
    _append_optional_kwargs(kwargs, dispatch)
    kwargs["provider_diagnostics"] = deps.provider_diagnostics
    passages = deps.process_search_queries(
        list(dispatch.queries),
        dispatch.intent,
        dispatch.complexity,
        dispatch.search_depth,
        dispatch.results_per_query,
        list(dispatch.include_domains),
        list(dispatch.exclude_domains),
        deps.query_embedding,
        deps.seen_urls,
        deps.collected_images,
        deps.embed_provider,
        deps.embed_model,
        deps.local_url,
        deps.embed_texts,
        deps.compute_similarities,
        **kwargs,
    )
    pass_record = build_retrieval_pass_record(
        stage=dispatch.stage,
        iteration=dispatch.iteration,
        queries=dispatch.queries,
        providers=dispatch.providers,
        provider_role=dispatch.provider_role,
        search_depth=dispatch.search_depth,
        results_per_query=dispatch.results_per_query,
    )
    if retrieval_pass_records is not None:
        retrieval_pass_records.append(pass_record)
    seen_url_delta = max(0, len(deps.seen_urls) - seen_before)
    return RetrievalDispatchOutcome(
        passages=passages,
        pass_record=pass_record,
        seen_url_delta=seen_url_delta,
        chunk_delta=len(passages),
    )


@dataclass(frozen=True)
class MainRetrievalPassOutcome(RetrievalDispatchOutcome):
    retrieval_loop_contract_state: RetrievalLoopState
    descriptor: Any
    execution_envelope: Any


_DISPATCH_DEP_KEYS = (
    "process_search_queries",
    "query_embedding",
    "seen_urls",
    "collected_images",
    "embed_provider",
    "embed_model",
    "local_url",
    "embed_texts",
    "deps",
    "status",
    "provider_diagnostics",
)
_RECORDED_SCOPE_KEYS = (
    "intent",
    "complexity",
    "results_per_query",
    "include_domains",
    "exclude_domains",
    "entity_hint_for_retrieval",
)
_RECOVERY_SCOPE_KEYS = (
    "process_search_queries",
    "all_passages",
    "intent",
    "complexity",
    "results_per_query",
    "include_domains",
    "exclude_domains",
    "query_embedding",
    "seen_urls",
    "collected_images",
    "embed_provider",
    "embed_model",
    "local_url",
    "embed_texts",
    "deps",
    "status",
    "providers_by_iteration",
    "ACADEMIC_DOMAINS",
    "is_academic",
    "entity_hint_for_retrieval",
    "provider_diagnostics",
    "retrieval_pass_records",
)


def _require_scope(scope: dict[str, Any], names: Sequence[str]) -> dict[str, Any]:
    """Read only a fixed whitelist from an orchestrator scope mapping."""

    missing = [name for name in names if name not in scope]
    if missing:
        raise KeyError(f"retrieval dispatch scope missing keys: {missing}")
    return {name: scope[name] for name in names}


def _scope_values(scope: dict[str, Any], *names: str) -> dict[str, Any]:
    return _require_scope(scope, names)


def _exa_filter(values: dict[str, Any]) -> Sequence[str] | None:
    return values["ACADEMIC_DOMAINS"] if values["is_academic"] else None


def _latest_iteration_providers(values: dict[str, Any]) -> list[str]:
    return list(values["providers_by_iteration"][-1]) if values["providers_by_iteration"] else []


def retrieval_dispatch_deps_from_scope(scope: dict[str, Any]) -> RetrievalDispatchDeps:
    values = _require_scope(scope, _DISPATCH_DEP_KEYS)
    return RetrievalDispatchDeps(
        process_search_queries=values["process_search_queries"],
        query_embedding=values["query_embedding"],
        seen_urls=values["seen_urls"],
        collected_images=values["collected_images"],
        embed_provider=values["embed_provider"],
        embed_model=values["embed_model"],
        local_url=values["local_url"],
        embed_texts=values["embed_texts"],
        compute_similarities=values["deps"].compute_similarities,
        status_container=values["status"],
        provider_diagnostics=values["provider_diagnostics"],
    )


def execute_main_retrieval_pass_from_scope(
    scope: dict[str, Any],
    *,
    retrieval_pass_records: MutableSequence[dict[str, Any]],
) -> MainRetrievalPassOutcome:
    values = _scope_values(
        scope,
        "iteration",
        "router_query_preparation_contract",
        "retrieval_provider_role",
        "current_queries",
        "loop_providers",
        "current_search_depth",
        "results_per_query",
        "top_chunks",
        "max_iterations",
        "intent",
        "complexity",
        "include_domains",
        "exclude_domains",
        "ACADEMIC_DOMAINS",
        "is_academic",
        "entity_hint_for_retrieval",
        "retrieval_stop_active_telemetry",
        "run_id",
        "retrieval_batch_dispatch_trace",
        "active_source_class_recovery_lifecycle",
        "weak_corpus_recovery_used",
        "weak_corpus_recovery_attempted",
        "weak_corpus_recovery_decision",
        "retrieval_loop_contract_state",
        "similarity_prior_queries",
        "query_similarity_basis",
    )
    router_state = values["router_query_preparation_contract"]
    query_source = router_state.query_preparation_provenance.get("query_source") or values["retrieval_provider_role"]
    retrieval_budget_facts = {
        "iteration": values["iteration"],
        "max_iterations": values["max_iterations"],
        "iterations_remaining_after_pass": max(0, values["max_iterations"] - values["iteration"]),
        "results_per_query": values["results_per_query"],
        "top_chunks": values["top_chunks"],
    }
    descriptor = build_retrieval_pass_descriptor(
        iteration=values["iteration"],
        query_source=query_source,
        current_queries=values["current_queries"],
        provider_list=values["loop_providers"],
        search_depth=values["current_search_depth"],
        results_per_query=values["results_per_query"],
        top_chunks=values["top_chunks"],
        max_iterations=values["max_iterations"],
        intent=values["intent"],
        complexity=values["complexity"],
        provider_role=values["retrieval_provider_role"],
        query_similarity_basis=values["query_similarity_basis"],
        prior_queries_for_similarity=values["similarity_prior_queries"],
        retrieval_budget_facts=retrieval_budget_facts,
        batch_dispatch_authorization_ref=values["retrieval_batch_dispatch_trace"],
        source_class_recovery_action_ref=values["active_source_class_recovery_lifecycle"],
        weak_corpus_recovery_ref={
            "weak_corpus_recovery_used": values["weak_corpus_recovery_used"],
            "weak_corpus_recovery_attempted": values["weak_corpus_recovery_attempted"],
            "weak_corpus_recovery_decision": values["weak_corpus_recovery_decision"],
        },
    )
    envelope = build_retrieval_execution_envelope(
        descriptor,
        include_domains=values["include_domains"],
        exclude_domains=values["exclude_domains"],
        exa_domain_filter=_exa_filter(values),
        entity_hint=values["entity_hint_for_retrieval"],
    )
    loop_state = build_retrieval_loop_state(
        router_query_preparation_state=router_state,
        pass_descriptor=descriptor,
        execution_envelope=envelope,
        retrieval_stop_decision=values["retrieval_stop_active_telemetry"],
        run_id=values["run_id"],
        retrieval_budget_facts=descriptor.retrieval_budget_facts,
        controller_visibility={
            "production_active": True,
            "provider_search_executor": "existing_process_search_queries",
        },
    )
    previous_state = values["retrieval_loop_contract_state"]
    if previous_state is not None:
        for previous_summary in previous_state.pass_result_summaries:
            loop_state = loop_state.with_pass_result(previous_summary)

    deps = retrieval_dispatch_deps_from_scope(scope)
    seen_before = len(deps.seen_urls)
    passages = execute_retrieval_pass_handoff(
        envelope,
        process_search_queries=deps.process_search_queries,
        query_embedding=deps.query_embedding,
        seen_urls=deps.seen_urls,
        collected_images=deps.collected_images,
        embed_provider=deps.embed_provider,
        embed_model=deps.embed_model,
        local_url=deps.local_url,
        embed_texts=deps.embed_texts,
        compute_similarities=deps.compute_similarities,
        status_container=deps.status_container,
        provider_diagnostics=deps.provider_diagnostics,
        iteration=values["iteration"],
        prior_queries_for_similarity=values["similarity_prior_queries"],
        query_similarity_basis=values["query_similarity_basis"],
    )
    seen_url_delta = max(0, len(deps.seen_urls) - seen_before)
    loop_state = loop_state.with_pass_result(
        summarize_retrieval_pass_result(
            descriptor=descriptor,
            result_count=len(passages),
            seen_url_delta=seen_url_delta,
        )
    )
    pass_record = build_retrieval_pass_record(
        stage="main_retrieval",
        iteration=values["iteration"],
        queries=values["current_queries"],
        providers=values["loop_providers"],
        provider_role=values["retrieval_provider_role"],
        search_depth=values["current_search_depth"],
        results_per_query=values["results_per_query"],
    )
    retrieval_pass_records.append(pass_record)
    return MainRetrievalPassOutcome(
        passages=passages,
        pass_record=pass_record,
        seen_url_delta=seen_url_delta,
        chunk_delta=len(passages),
        retrieval_loop_contract_state=loop_state,
        descriptor=descriptor,
        execution_envelope=envelope,
    )


def _execute_scope_dispatch(
    scope: dict[str, Any],
    *,
    stage: str,
    queries: Sequence[str],
    providers: Sequence[str],
    provider_role: str,
    search_depth: str,
    retrieval_pass_records: MutableSequence[dict[str, Any]] | None = None,
    iteration: int | None = None,
    exa_domain_filter: Sequence[str] | None = None,
    linkup_depth_override: str | None = None,
) -> RetrievalDispatchOutcome:
    values = _require_scope(scope, _RECORDED_SCOPE_KEYS)
    return execute_recorded_retrieval_dispatch(
        RecordedRetrievalDispatch(
            stage=stage,
            queries=queries,
            intent=values["intent"],
            complexity=values["complexity"],
            search_depth=search_depth,
            results_per_query=values["results_per_query"],
            include_domains=values["include_domains"],
            exclude_domains=values["exclude_domains"],
            providers=providers,
            provider_role=provider_role,
            iteration=iteration,
            exa_domain_filter=exa_domain_filter,
            linkup_depth_override=linkup_depth_override,
            entity_hint=values["entity_hint_for_retrieval"],
        ),
        retrieval_dispatch_deps_from_scope(scope),
        retrieval_pass_records=retrieval_pass_records,
    )


def execute_disambiguation_retry_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    retrieval_pass_records: MutableSequence[dict[str, Any]],
) -> RetrievalDispatchOutcome:
    values = _scope_values(
        scope,
        "current_search_depth",
        "loop_providers",
        "iteration",
        "ACADEMIC_DOMAINS",
        "is_academic",
    )
    return _execute_scope_dispatch(
        scope,
        stage="disambiguation_retry",
        queries=queries,
        providers=values["loop_providers"],
        provider_role="disambiguation_retry",
        search_depth=values["current_search_depth"],
        retrieval_pass_records=retrieval_pass_records,
        iteration=values["iteration"],
        exa_domain_filter=_exa_filter(values),
    )


def execute_supplemental_search_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    search_depth: str,
    providers: Sequence[str],
) -> RetrievalDispatchOutcome:
    return _execute_scope_dispatch(
        scope,
        stage="supplemental_search",
        queries=queries,
        providers=providers,
        provider_role="supplemental_search",
        search_depth=search_depth,
    )


def execute_scrutineer_remediation_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    providers: Sequence[str],
) -> RetrievalDispatchOutcome:
    values = _scope_values(scope, "search_depth")
    return _execute_scope_dispatch(
        scope,
        stage="scrutineer_remediation",
        queries=queries,
        providers=providers,
        provider_role="scrutineer_remediation",
        search_depth=values["search_depth"],
        linkup_depth_override="deep",
    )


def _recovery_dispatch_kwargs(values: dict[str, Any], *, lifecycle_key: str) -> dict[str, Any]:
    return {
        "lifecycle_trace": values[lifecycle_key],
        "all_passages": values["all_passages"],
        "intent": values["intent"],
        "complexity": values["complexity"],
        "results_per_query": values["results_per_query"],
        "include_domains": values["include_domains"],
        "exclude_domains": values["exclude_domains"],
        "query_embedding": values["query_embedding"],
        "seen_urls": values["seen_urls"],
        "collected_images": values["collected_images"],
        "embed_provider": values["embed_provider"],
        "embed_model": values["embed_model"],
        "local_url": values["local_url"],
        "embed_texts": values["embed_texts"],
        "compute_similarities": values["deps"].compute_similarities,
        "status_container": values["status"],
        "search_providers": _latest_iteration_providers(values),
        "exa_domain_filter": _exa_filter(values),
        "entity_hint": values["entity_hint_for_retrieval"],
        "provider_diagnostics": values["provider_diagnostics"],
        "retrieval_pass_records": values["retrieval_pass_records"],
    }


def source_class_recovery_context_from_scope(
    scope: dict[str, Any],
    *,
    controller_recovery_decision: Any,
    error_type: type[Exception],
) -> Any:
    from core.source_class_recovery_runner import SourceClassRecoveryRunnerContext

    values = _require_scope(
        scope,
        (
            "_run_controller_mirror",
            "authorized_spine_action",
            "active_source_class_recovery_lifecycle",
            *_RECOVERY_SCOPE_KEYS,
        ),
    )
    return SourceClassRecoveryRunnerContext(
        controller=values["_run_controller_mirror"],
        authorized_spine_action=values["authorized_spine_action"],
        controller_recovery_decision=controller_recovery_decision,
        process_search_queries=values["process_search_queries"],
        error_type=error_type,
        **_recovery_dispatch_kwargs(values, lifecycle_key="active_source_class_recovery_lifecycle"),
    )


def execute_conflict_resolution_from_scope(
    scope: dict[str, Any],
    *,
    decision: Any,
    error_type: type[Exception],
) -> dict[str, int | bool]:
    from core.conflict_resolution_executor import execute_conflict_resolution_action

    values = _require_scope(
        scope,
        ("active_conflict_resolution_lifecycle", *_RECOVERY_SCOPE_KEYS),
    )
    return execute_conflict_resolution_action(
        decision,
        process_conflict_resolution_queries=values["process_search_queries"],
        error_type=error_type,
        **_recovery_dispatch_kwargs(values, lifecycle_key="active_conflict_resolution_lifecycle"),
    )
