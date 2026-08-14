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

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Final, Mapping, MutableSequence, Sequence

from core.retrieval_loop_contract import (
    RetrievalLoopState,
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
    summarize_retrieval_pass_result,
)
from core.retrieval_scheduler import (
    RetrievalScheduledAction,
    bind_recorded_discovery_lineage,
    schedule_recorded_discovery_dispatch,
)
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
    discovery_result_store: Any | None = None


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
    discovery_result_context: Mapping[str, Any] | None = None
    discovery_result_store: Any | None = None


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
    *,
    discovery_result_store: Any | None = None,
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
    has_discovery_context = dispatch.discovery_result_context is not None
    if has_discovery_context:
        kwargs["discovery_result_context"] = dict(
            dispatch.discovery_result_context
        )
    store = (
        dispatch.discovery_result_store
        if dispatch.discovery_result_store is not None
        else discovery_result_store
    )
    if has_discovery_context and store is not None:
        kwargs["discovery_result_store"] = store


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

    effective_store = (
        dispatch.discovery_result_store
        if dispatch.discovery_result_store is not None
        else deps.discovery_result_store
    )
    if dispatch.providers and effective_store is not None and (
        dispatch.discovery_result_context is None
    ):
        raise ValueError(
            "ordinary discovery dispatch has a result store but no exact lineage"
        )
    seen_before = len(deps.seen_urls)
    kwargs: dict[str, Any] = {
        "status_container": deps.status_container,
        "search_providers": list(dispatch.providers),
    }
    _append_optional_kwargs(
        kwargs,
        dispatch,
        discovery_result_store=deps.discovery_result_store,
    )
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


RETRIEVAL_POST_MATERIAL_CAUSE_OWNER: Final = (
    "core.retrieval_dispatch_runtime.execute_main_retrieval_pass_from_scope"
)
RETRIEVAL_POST_MATERIAL_CAUSE_CLASSIFICATION: Final = (
    "retrieval_post_material_failure"
)


class RetrievalPostMaterialFailureSubtype(str, Enum):
    """Closed mechanical failures inside the post-material packaging span."""

    SOURCE_RESULT_IDENTITY_SET_PROJECTION = (
        "source_result_identity_set_projection"
    )
    DISCOVERY_RESULT_TELEMETRY_PROJECTION = (
        "discovery_result_telemetry_projection"
    )
    RETRIEVAL_PASS_OBSERVATION_CONSTRUCTION = (
        "retrieval_pass_observation_construction"
    )
    MAIN_RETRIEVAL_OUTCOME_CONSTRUCTION = (
        "main_retrieval_outcome_construction"
    )
    POST_MATERIAL_UNCLASSIFIED = "post_material_unclassified"


class RetrievalPostMaterialDispatchError(RuntimeError):
    """Message-free carrier for one closed post-material failure subtype."""

    __slots__ = ("_subtype",)

    def __init__(self, subtype: RetrievalPostMaterialFailureSubtype) -> None:
        if not isinstance(subtype, RetrievalPostMaterialFailureSubtype):
            raise TypeError("subtype must be a closed post-material failure subtype")
        super().__init__("retrieval post-material dispatch failed")
        self._subtype = subtype

    @property
    def subtype(self) -> RetrievalPostMaterialFailureSubtype:
        return self._subtype

    def to_terminal_cause_projection(self) -> dict[str, str]:
        return {
            "cause_owner": RETRIEVAL_POST_MATERIAL_CAUSE_OWNER,
            "cause_classification": (
                RETRIEVAL_POST_MATERIAL_CAUSE_CLASSIFICATION
            ),
            "cause_subtype": self._subtype.value,
        }


def _invoke_post_material_operation(
    subtype: RetrievalPostMaterialFailureSubtype,
    operation: Callable[[], Any],
) -> Any:
    try:
        return operation()
    except RetrievalPostMaterialDispatchError:
        raise
    except Exception as exc:
        raise RetrievalPostMaterialDispatchError(subtype) from exc


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
        discovery_result_store=_discovery_result_store_from_scope(scope),
    )


def _discovery_result_store_from_scope(scope: Mapping[str, Any]) -> Any | None:
    store = scope.get("discovery_result_store")
    if store is not None:
        return store
    return getattr(scope.get("deps"), "discovery_result_store", None)


def _request_id_from_scope(scope: Mapping[str, Any]) -> str | None:
    request_id = scope.get("request_id")
    if request_id is None:
        request_id = getattr(getattr(scope.get("run_kernel"), "state", None), "request_id", None)
    text = str(request_id or "").strip()
    return text or None


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _discovery_iteration_from_scope(
    scope: Mapping[str, Any],
    iteration: int | None,
) -> int:
    value: Any = iteration
    if value is None:
        for key in ("iterations_run", "iteration"):
            if scope.get(key) is not None:
                value = scope[key]
                break
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            "ordinary discovery dispatch requires an exact nonnegative iteration"
        )
    return value


def _matching_provider_record(
    scope: Mapping[str, Any],
    providers: Sequence[str],
    *,
    provider_record: Any | None = None,
) -> tuple[Any, Any]:
    provider_plan = scope.get("provider_plan")
    records = tuple(getattr(provider_plan, "records", ()))
    if provider_plan is None or not records:
        raise ValueError("ordinary discovery requires a completed ProviderPlan route")
    provider_tuple = tuple(str(provider) for provider in providers)
    record = provider_record
    if record is None:
        record = next(
            (
                candidate
                for candidate in reversed(records)
                if tuple(getattr(candidate, "providers", ())) == provider_tuple
            ),
            None,
        )
    if record is None or tuple(getattr(record, "providers", ())) != provider_tuple:
        raise ValueError(
            "ordinary discovery providers do not match a completed ProviderPlan route"
        )
    record_ref = record.to_ref()
    if not any(candidate.to_ref() == record_ref for candidate in records):
        raise ValueError("ordinary discovery ProviderPlan record is stale")
    return provider_plan, record


def _recorded_discovery_context_from_scope(
    scope: Mapping[str, Any],
    *,
    stage: str,
    queries: Sequence[str],
    providers: Sequence[str],
    provider_role: str,
    search_depth: str,
    iteration: int | None,
    query_origin: str,
    query_role: str,
    authority_source: str,
    authority_anchor: Mapping[str, Any],
    provider_record: Any | None = None,
) -> dict[str, Any] | None:
    store = _discovery_result_store_from_scope(scope)
    if store is None:
        return None
    query_authority = scope.get("query_authority")
    if query_authority is None or not callable(
        getattr(query_authority, "record_authorized_dispatch_queries", None)
    ):
        raise ValueError(
            "ordinary discovery dispatch requires the canonical QueryPlan adapter"
        )
    provider_plan, exact_record = _matching_provider_record(
        scope,
        providers,
        provider_record=provider_record,
    )
    exact_iteration = _discovery_iteration_from_scope(scope, iteration)
    authority_ref_digest = _canonical_digest(dict(authority_anchor))
    scheduled_action = schedule_recorded_discovery_dispatch(
        stage=stage,
        current_queries=queries,
        iteration=exact_iteration,
        provider_role=provider_role,
        search_depth=search_depth,
        provider_record=exact_record,
        authority_source=authority_source,
        authority_ref_digest=authority_ref_digest,
    )
    item_refs = query_authority.record_authorized_dispatch_queries(
        queries,
        origin=query_origin,
        role=query_role,
        phase=stage,
        iteration=exact_iteration,
        authority_source=authority_source,
        authority_ref_digest=authority_ref_digest,
    )
    scheduled_action = bind_recorded_discovery_lineage(
        scheduled_action,
        query_plan=query_authority.plan,
        query_plan_item_refs=item_refs,
        provider_plan=provider_plan,
        provider_record=exact_record,
        authority_ref_digest=authority_ref_digest,
    )
    return _discovery_result_context_from_scheduled_action(
        scheduled_action=scheduled_action,
        scope=scope,
    )


def _discovery_result_context_from_scheduled_action(
    *,
    scheduled_action: RetrievalScheduledAction,
    scope: Mapping[str, Any],
    run_id: str | None = None,
) -> dict[str, Any]:
    if not scheduled_action.query_plan_ref:
        raise ValueError("ordinary discovery scheduled action lacks QueryPlan lineage")
    request_id = _request_id_from_scope(scope)
    if request_id is None:
        raise ValueError("ordinary discovery result context requires request_id")
    resolved_run_id = str(
        run_id
        or scope.get("run_id")
        or getattr(getattr(scope.get("run_kernel"), "state", None), "run_id", "")
    ).strip()
    if not resolved_run_id:
        raise ValueError("ordinary discovery result context requires run_id")
    providers = tuple(scheduled_action.providers)
    if len(providers) != 1:
        raise ValueError(
            "ordinary discovery result context requires one completed provider route"
        )
    return {
        "run_id": resolved_run_id,
        "request_id": request_id,
        "stage": scheduled_action.stage,
        "iteration": scheduled_action.iteration,
        "provider_role": scheduled_action.provider_role,
        "provider": providers[0],
        "retrieval_action_ref": dict(scheduled_action.retrieval_action_ref),
        "query_plan_ref": dict(scheduled_action.query_plan_ref),
        "query_plan_item_refs": [
            dict(item_ref) for item_ref in scheduled_action.query_plan_item_refs
        ],
        "provider_plan_ref": dict(scheduled_action.provider_plan_ref),
        "provider_plan_record_ref": dict(
            scheduled_action.provider_plan_record_ref
        ),
        "provider_route_ref": dict(scheduled_action.provider_route_ref),
        "provider_capability": scheduled_action.provider_capability,
        "provider_qualifier": scheduled_action.provider_qualifier,
        "provider_operation": scheduled_action.provider_operation,
        "provider_variant": scheduled_action.provider_variant,
        "provider_output_type": scheduled_action.provider_output_type,
    }


def _discovery_result_context(
    *,
    scheduled_action: RetrievalScheduledAction,
    kernel_action: AuthorizedAction,
    scope: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project exact scheduler lineage for the provider-result boundary."""

    if not scheduled_action.query_plan_ref:
        return None
    if dict(scheduled_action.retrieval_action_ref).get("action_id") != kernel_action.action_id:
        raise ValueError("scheduled retrieval action ref does not match RunKernel action")
    if str(scope.get("run_id") or kernel_action.run_id) != kernel_action.run_id:
        raise ValueError("ordinary discovery result context run_id mismatch")
    return _discovery_result_context_from_scheduled_action(
        scheduled_action=scheduled_action,
        scope=scope,
        run_id=kernel_action.run_id,
    )


def _store_mapping(store: Any, *method_names: str) -> dict[str, Any] | None:
    if store is None:
        return None
    for method_name in method_names:
        method = getattr(store, method_name, None)
        if not callable(method):
            continue
        value = method()
        if isinstance(value, Mapping):
            return dict(value)
    return None


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
    discovery_result_store = _discovery_result_store_from_scope(scope)
    discovery_result_context = (
        _discovery_result_context(
            scheduled_action=scheduled_action,
            kernel_action=kernel_action,
            scope=scope,
        )
        if discovery_result_store is not None
        else None
    )
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
        discovery_result_context=discovery_result_context,
        discovery_result_store=discovery_result_store,
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
    try:
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
        observation_payload: dict[str, Any] = {
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
        }
        source_result_identity_set_ref = _invoke_post_material_operation(
            RetrievalPostMaterialFailureSubtype.SOURCE_RESULT_IDENTITY_SET_PROJECTION,
            lambda: _store_mapping(
                discovery_result_store,
                "identity_set_ref",
                "to_identity_set_ref",
            ),
        )
        if source_result_identity_set_ref is not None:
            observation_payload["source_result_identity_set_ref"] = (
                source_result_identity_set_ref
            )
        discovery_result_telemetry = _invoke_post_material_operation(
            RetrievalPostMaterialFailureSubtype.DISCOVERY_RESULT_TELEMETRY_PROJECTION,
            lambda: _store_mapping(
                discovery_result_store,
                "telemetry",
                "to_telemetry",
            ),
        )
        if discovery_result_telemetry is not None:
            observation_payload["discovery_result_telemetry"] = (
                discovery_result_telemetry
            )
        observation = _invoke_post_material_operation(
            RetrievalPostMaterialFailureSubtype.RETRIEVAL_PASS_OBSERVATION_CONSTRUCTION,
            lambda: Observation.from_action(
                kernel_action,
                observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
                status=RunStageStatus.COMPLETED,
                payload=observation_payload,
            ),
        )
        return _invoke_post_material_operation(
            RetrievalPostMaterialFailureSubtype.MAIN_RETRIEVAL_OUTCOME_CONSTRUCTION,
            lambda: MainRetrievalPassOutcome(
                passages=passages,
                pass_record=pass_record,
                seen_url_delta=seen_url_delta,
                chunk_delta=len(passages),
                retrieval_loop_contract_state=loop_state,
                descriptor=descriptor,
                execution_envelope=envelope,
                observation=observation,
            ),
        )
    except RetrievalPostMaterialDispatchError:
        raise
    except Exception as exc:
        raise RetrievalPostMaterialDispatchError(
            RetrievalPostMaterialFailureSubtype.POST_MATERIAL_UNCLASSIFIED
        ) from exc


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
    provider_record: Any | None = None,
    query_origin: str,
    query_role: str,
    authority_source: str,
    authority_anchor: Mapping[str, Any],
) -> RetrievalDispatchOutcome:
    values = _require_scope(scope, _RECORDED_SCOPE_KEYS)
    discovery_result_store = _discovery_result_store_from_scope(scope)
    discovery_result_context = _recorded_discovery_context_from_scope(
        scope,
        stage=stage,
        queries=queries,
        providers=providers,
        provider_role=provider_role,
        search_depth=search_depth,
        iteration=iteration,
        query_origin=query_origin,
        query_role=query_role,
        authority_source=authority_source,
        authority_anchor=authority_anchor,
        provider_record=provider_record,
    )
    dispatch_iteration = (
        int(discovery_result_context["iteration"])
        if discovery_result_context is not None
        else iteration
    )
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
            iteration=dispatch_iteration,
            exa_domain_filter=exa_domain_filter,
            linkup_depth_override=linkup_depth_override,
            entity_hint=values["entity_hint_for_retrieval"],
            discovery_result_context=discovery_result_context,
            discovery_result_store=discovery_result_store,
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
        query_origin="entity_correction",
        query_role="disambiguation",
        authority_source="main_retrieval_disambiguation_retry",
        authority_anchor={
            "parent_retrieval_action_ref": dict(
                scheduled_action.retrieval_action_ref
            ),
            "retry_used": True,
        },
    )


def execute_supplemental_search_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    search_depth: str,
    providers: Sequence[str],
    provider_variant: str | None = None,
    provider_record: Any | None = None,
) -> RetrievalDispatchOutcome:
    return _execute_scope_dispatch(
        scope,
        stage="supplemental_search",
        queries=queries,
        providers=providers,
        provider_role="supplemental_search",
        search_depth=search_depth,
        linkup_depth_override=(provider_variant if tuple(providers) == ("linkup",) else None),
        provider_record=provider_record,
        query_origin="synthesis_evaluator",
        query_role="supplemental",
        authority_source="synthesis_evaluator_supplemental",
        authority_anchor={
            "provider_plan_record_ref": (
                provider_record.to_ref() if provider_record is not None else {}
            ),
            "dispatch_authorized": True,
        },
    )


def execute_scrutineer_remediation_from_scope(
    scope: dict[str, Any],
    *,
    queries: Sequence[str],
    providers: Sequence[str],
    provider_record: Any | None = None,
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
        provider_record=provider_record,
        query_origin="scrutineer_remediation",
        query_role="remediation",
        authority_source="scrutineer_remediation_dispatch",
        authority_anchor={
            "provider_plan_record_ref": (
                provider_record.to_ref() if provider_record is not None else {}
            ),
            "dispatch_authorized": True,
        },
    )


def _bind_ordinary_discovery_process(
    scope: Mapping[str, Any],
    process_search_queries: Callable[..., Any],
    *,
    stage: str,
    query_origin: str,
    query_role: str,
    authority_source: str,
    authority_anchor: Mapping[str, Any],
) -> Callable[..., Any]:
    """Bind each invocation of an injected recovery runner to exact lineage."""

    if _discovery_result_store_from_scope(scope) is None:
        return process_search_queries

    def bound(*args: Any, **kwargs: Any) -> Any:
        if not args:
            raise ValueError("ordinary discovery process requires ordered queries")
        queries = list(args[0])
        providers = list(kwargs.get("search_providers") or ())
        provider_role = str(kwargs.get("provider_role") or stage)
        search_depth = str(args[3]) if len(args) > 3 else ""
        context = _recorded_discovery_context_from_scope(
            scope,
            stage=stage,
            queries=queries,
            providers=providers,
            provider_role=provider_role,
            search_depth=search_depth,
            iteration=None,
            query_origin=query_origin,
            query_role=query_role,
            authority_source=authority_source,
            authority_anchor=authority_anchor,
        )
        if context is None:
            raise ValueError(
                "ordinary discovery recovery dispatch failed to bind lineage"
            )
        if kwargs.get("discovery_result_context") not in (None, context):
            raise ValueError("ordinary discovery recovery context was prebound")
        kwargs["discovery_result_context"] = context
        kwargs["discovery_result_store"] = _discovery_result_store_from_scope(
            scope
        )
        return process_search_queries(*args, **kwargs)

    return bound


def _ordinary_discovery_process_binder(
    scope: Mapping[str, Any],
    process_search_queries: Callable[..., Any],
) -> Callable[..., Callable[..., Any]]:
    def bind(
        *,
        stage: str,
        query_origin: str,
        query_role: str,
        authority_source: str,
        authority_anchor: Mapping[str, Any],
    ) -> Callable[..., Any]:
        return _bind_ordinary_discovery_process(
            scope,
            process_search_queries,
            stage=stage,
            query_origin=query_origin,
            query_role=query_role,
            authority_source=authority_source,
            authority_anchor=authority_anchor,
        )

    return bind


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
        bind_process_search_queries=_ordinary_discovery_process_binder(
            scope,
            _recovery_process_with_recorded_variant(values),
        ),
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
    values["process_search_queries"] = _bind_ordinary_discovery_process(
        scope,
        _recovery_process_with_recorded_variant(values),
        stage="conflict_resolution",
        query_origin="conflict_resolution_controller",
        query_role="recovery",
        authority_source="retrieval_authority_stage.resolve_conflict",
        authority_anchor={
            "authorized_spine_action": scope.get("authorized_spine_action"),
            "decision": (
                decision.to_dict()
                if callable(getattr(decision, "to_dict", None))
                else str(decision)
            ),
        },
    )
    return execute_conflict_resolution_action(
        decision,
        process_conflict_resolution_queries=values["process_search_queries"],
        error_type=error_type,
        **_recovery_dispatch_kwargs(values, lifecycle_key="active_conflict_resolution_lifecycle"),
    )
