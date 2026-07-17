"""Mechanical retrieval dispatch/pass-record runtime helpers.

This module only executes already-authorized retrieval requests and assembles
already-existing pass telemetry. It does not generate or mutate queries, select
providers, choose depth, rank/filter results, import prompt/model code, or make
provider policy decisions.

The legacy ``execute_retrieval_pass_handoff`` contract remains a separately
tested compatibility surface; this module only dispatches already-scheduled
provider-capability decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, MutableSequence, Sequence

from core.retrieval_loop_contract import (
    RetrievalLoopState,
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
    summarize_retrieval_pass_result,
)
from core.retrieval_scheduler import RetrievalScheduledAction
from core.run_kernel import (
    MAIN_RETRIEVAL_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
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
class EmbeddingActionRecord:
    """Already-authorized embedding kickoff facts for the initial topic embedding."""

    topic_text: str
    provider: str
    model: str
    base_url: str | None
    action_role: str = "pre_retrieval_topic_embedding"


def execute_embedding_action(
    action: EmbeddingActionRecord,
    embed_texts: Callable[..., Sequence[Any]],
) -> Any:
    """Execute an already-authorized embedding action without changing call shape."""

    return embed_texts(
        [action.topic_text],
        provider=action.provider,
        model=action.model,
        base_url=action.base_url,
    )[0]


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
    passages = []
    if dispatch.providers:
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
    observation: Observation


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
    "provider_plan",
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


def _recovery_process_with_recorded_variant(values: dict[str, Any]) -> Callable[..., Any]:
    process_search_queries = values["process_search_queries"]
    latest_providers = tuple(_latest_iteration_providers(values))
    if latest_providers != ("linkup",):
        return process_search_queries
    records = tuple(getattr(values["provider_plan"], "records", ()))
    variant = next(
        (record.provider_variant for record in reversed(records) if tuple(record.providers) == latest_providers),
        None,
    )
    if variant is None:
        return process_search_queries

    def process_with_variant(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("linkup_depth_override", variant)
        return process_search_queries(*args, **kwargs)

    return process_with_variant


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
        "main_retrieval_kernel_action",
        "retrieval_scheduled_action",
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
    kernel_action: AuthorizedAction = validate_authorized_action(
        values["main_retrieval_kernel_action"],
        action_type=ActionType.MAIN_RETRIEVAL_PASS,
        stage=MAIN_RETRIEVAL_STAGE,
        expected_observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
    )
    scheduled_action: RetrievalScheduledAction = values["retrieval_scheduled_action"]
    action_iteration = scheduled_action.iteration or values["iteration"]
    router_state = values["router_query_preparation_contract"]
    query_source = router_state.query_preparation_provenance.get("query_source") or scheduled_action.provider_role
    retrieval_budget_facts = {
        "iteration": action_iteration,
        "max_iterations": values["max_iterations"],
        "iterations_remaining_after_pass": max(0, values["max_iterations"] - action_iteration),
        "results_per_query": values["results_per_query"],
        "top_chunks": values["top_chunks"],
    }
    dispatch_action = RecordedRetrievalDispatch(
        stage=scheduled_action.stage,
        queries=scheduled_action.current_queries,
        intent=values["intent"],
        complexity=values["complexity"],
        search_depth=scheduled_action.search_depth,
        results_per_query=values["results_per_query"],
        include_domains=values["include_domains"],
        exclude_domains=values["exclude_domains"],
        providers=scheduled_action.providers,
        provider_role=scheduled_action.provider_role,
        iteration=action_iteration,
        exa_domain_filter=_exa_filter(values),
        linkup_depth_override=(
            scheduled_action.provider_variant if tuple(scheduled_action.providers) == ("linkup",) else None
        ),
        entity_hint=values["entity_hint_for_retrieval"],
        prior_queries_for_similarity=values["similarity_prior_queries"],
        query_similarity_basis=values["query_similarity_basis"],
    )
    descriptor = build_retrieval_pass_descriptor(
        iteration=dispatch_action.iteration or values["iteration"],
        query_source=query_source,
        current_queries=dispatch_action.queries,
        provider_list=dispatch_action.providers,
        search_depth=dispatch_action.search_depth,
        results_per_query=dispatch_action.results_per_query,
        top_chunks=values["top_chunks"],
        max_iterations=values["max_iterations"],
        intent=values["intent"],
        complexity=values["complexity"],
        provider_role=dispatch_action.provider_role,
        query_similarity_basis=dispatch_action.query_similarity_basis,
        prior_queries_for_similarity=dispatch_action.prior_queries_for_similarity,
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
        include_domains=dispatch_action.include_domains,
        exclude_domains=dispatch_action.exclude_domains,
        exa_domain_filter=dispatch_action.exa_domain_filter,
        entity_hint=dispatch_action.entity_hint,
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
    passages = []
    if dispatch_action.providers:
        passages = execute_recorded_retrieval_dispatch(
            dispatch_action,
            deps,
        ).passages
    seen_url_delta = max(0, len(deps.seen_urls) - seen_before)
    loop_state = loop_state.with_pass_result(
        summarize_retrieval_pass_result(
            descriptor=descriptor,
            result_count=len(passages),
            seen_url_delta=seen_url_delta,
        )
    )
    pass_record = build_retrieval_pass_record(
        stage=dispatch_action.stage,
        iteration=dispatch_action.iteration,
        queries=dispatch_action.queries,
        providers=dispatch_action.providers,
        provider_role=dispatch_action.provider_role,
        search_depth=dispatch_action.search_depth,
        results_per_query=dispatch_action.results_per_query,
    )
    retrieval_pass_records.append(pass_record)
    observation = Observation.from_action(
        kernel_action,
        observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
        status=RunStageStatus.COMPLETED,
        payload={
            "stage": dispatch_action.stage,
            "iteration": dispatch_action.iteration,
            "provider_role": dispatch_action.provider_role,
            "provider_count": len(tuple(dispatch_action.providers)),
            "query_count": len(tuple(dispatch_action.queries)),
            "search_depth": dispatch_action.search_depth,
            "results_per_query": dispatch_action.results_per_query,
            "seen_url_delta": seen_url_delta,
            "chunk_delta": len(passages),
            "scheduled_action": scheduled_action.to_trace(),
            "pass_record": pass_record,
        },
    )
    return MainRetrievalPassOutcome(
        passages=passages,
        pass_record=pass_record,
        seen_url_delta=seen_url_delta,
        chunk_delta=len(passages),
        retrieval_loop_contract_state=loop_state,
        descriptor=descriptor,
        execution_envelope=envelope,
        observation=observation,
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
        "retrieval_scheduled_action",
    )
    scheduled_action: RetrievalScheduledAction = values["retrieval_scheduled_action"]
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
        linkup_depth_override=(
            scheduled_action.provider_variant if tuple(values["loop_providers"]) == ("linkup",) else None
        ),
    )


def execute_supplemental_search_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    search_depth: str,
    providers: Sequence[str],
    provider_variant: str | None = None,
) -> RetrievalDispatchOutcome:
    return _execute_scope_dispatch(
        scope,
        stage="supplemental_search",
        queries=queries,
        providers=providers,
        provider_role="supplemental_search",
        search_depth=search_depth,
        linkup_depth_override=(provider_variant if tuple(providers) == ("linkup",) else None),
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
    error_type: type[Exception],
) -> Any:
    from core.source_class_recovery_runner import SourceClassRecoveryRunnerContext

    values = _require_scope(
        scope,
        (
            "_run_controller_mirror",
            "active_source_class_recovery_lifecycle",
            *_RECOVERY_SCOPE_KEYS,
        ),
    )
    return SourceClassRecoveryRunnerContext(
        controller=values["_run_controller_mirror"],
        process_search_queries=_recovery_process_with_recorded_variant(values),
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
        process_conflict_resolution_queries=_recovery_process_with_recorded_variant(values),
        error_type=error_type,
        **_recovery_dispatch_kwargs(values, lifecycle_key="active_conflict_resolution_lifecycle"),
    )
