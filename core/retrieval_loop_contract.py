"""Controller-owned retrieval-loop contract and mechanical handoff.

This module is passive and deterministic. It packages already-computed
retrieval-loop facts for Controller-visible state and exposes a tiny handoff
adapter for an existing search executor. It does not generate queries, select
providers, choose search depth, rank/filter sources, call prompts/models, or
persist session/DB state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Sequence

from core.retrieval_stop_controller import RetrievalStopDecision
from core.router_query_preparation_contract import RouterQueryPreparationState

RETRIEVAL_LOOP_TRACE_KEY = "retrieval_loop_contract"
RETRIEVAL_LOOP_SCHEMA_VERSION = "ag76d_rl_v1"


def _string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    for item in value or ():
        text = str(item or "").strip()
        if text:
            out.append(text)
    return tuple(out)


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _stop_decision_reference(
    retrieval_stop_decision: RetrievalStopDecision | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if retrieval_stop_decision is None:
        return {"available": False, "owner": "RetrievalStopDecision"}
    if isinstance(retrieval_stop_decision, Mapping):
        data = _mapping(retrieval_stop_decision)
        data.setdefault("available", True)
        data.setdefault("owner", "RetrievalStopDecision")
        return data
    decision = getattr(retrieval_stop_decision, "decision", None)
    reason = getattr(retrieval_stop_decision, "reason", None)
    return {
        "available": True,
        "owner": "RetrievalStopDecision",
        "decision": getattr(decision, "value", str(decision or "")),
        "reason": str(reason or ""),
    }


@dataclass(frozen=True)
class RetrievalPassDescriptor:
    """Controller-owned descriptor for one already-authorized retrieval pass."""

    iteration: int
    query_source: str
    current_queries: tuple[str, ...]
    provider_list: tuple[str, ...]
    search_depth: str
    results_per_query: int
    top_chunks: int
    max_iterations: int
    intent: str
    complexity: str
    provider_role: str = "main_retrieval"
    query_similarity_basis: str | None = None
    prior_queries_for_similarity: tuple[str, ...] = field(default_factory=tuple)
    retrieval_budget_facts: dict[str, Any] = field(default_factory=dict)
    batch_dispatch_authorization_ref: dict[str, Any] = field(default_factory=dict)
    source_class_recovery_action_ref: dict[str, Any] = field(default_factory=dict)
    weak_corpus_recovery_ref: dict[str, Any] = field(default_factory=dict)

    @property
    def controller_owned(self) -> bool:
        return True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": True,
            "iteration": int(self.iteration),
            "query_source": self.query_source,
            "current_queries": list(self.current_queries),
            "provider_list": list(self.provider_list),
            "search_depth": self.search_depth,
            "results_per_query": int(self.results_per_query),
            "top_chunks": int(self.top_chunks),
            "max_iterations": int(self.max_iterations),
            "intent": self.intent,
            "complexity": self.complexity,
            "provider_role": self.provider_role,
            "query_similarity_basis": self.query_similarity_basis,
            "prior_queries_for_similarity": list(self.prior_queries_for_similarity),
            "retrieval_budget_facts": deepcopy(self.retrieval_budget_facts),
            "batch_dispatch_authorization_ref": deepcopy(
                self.batch_dispatch_authorization_ref
            ),
            "source_class_recovery_action_ref": deepcopy(
                self.source_class_recovery_action_ref
            ),
            "weak_corpus_recovery_ref": deepcopy(self.weak_corpus_recovery_ref),
        }


@dataclass(frozen=True)
class RetrievalExecutionEnvelope:
    """Mechanical runner envelope for executing a descriptor with existing deps."""

    descriptor: RetrievalPassDescriptor
    include_domains: tuple[str, ...] = field(default_factory=tuple)
    exclude_domains: tuple[str, ...] = field(default_factory=tuple)
    exa_domain_filter: tuple[str, ...] | None = None
    entity_hint: str | None = None

    @property
    def controller_owned(self) -> bool:
        return True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": True,
            "descriptor": self.descriptor.to_trace(),
            "include_domains_count": len(self.include_domains),
            "exclude_domains_count": len(self.exclude_domains),
            "exa_domain_filter_count": (
                len(self.exa_domain_filter) if self.exa_domain_filter is not None else 0
            ),
            "entity_hint_available": bool(self.entity_hint),
            "mechanical_runner_boundary": True,
            "runner_selects_providers": False,
            "runner_selects_depth": False,
            "runner_generates_queries": False,
        }


@dataclass(frozen=True)
class RetrievalPassResultSummary:
    """Controller-visible summary of an already-completed retrieval pass."""

    iteration: int
    query_count: int
    provider_count: int
    result_count: int
    seen_url_delta: int
    provider_role: str

    def to_trace(self) -> dict[str, Any]:
        return {
            "iteration": int(self.iteration),
            "query_count": int(self.query_count),
            "provider_count": int(self.provider_count),
            "result_count": int(self.result_count),
            "seen_url_delta": int(self.seen_url_delta),
            "provider_role": self.provider_role,
        }


@dataclass(frozen=True)
class RetrievalLoopState:
    """Passive Controller-owned retrieval-loop state."""

    schema_version: str
    controller_owned: bool
    run_id: str | None
    iteration: int
    query_source: str
    current_queries: tuple[str, ...]
    finalized_queries: tuple[str, ...]
    provider_list: tuple[str, ...]
    search_depth: str
    results_per_query: int
    top_chunks: int
    max_iterations: int
    retrieval_budget_facts: dict[str, Any]
    retrieval_stop_decision_ref: dict[str, Any]
    router_query_preparation_ref: dict[str, Any]
    pass_descriptor: RetrievalPassDescriptor
    execution_envelope: RetrievalExecutionEnvelope
    pass_result_summaries: tuple[RetrievalPassResultSummary, ...] = field(
        default_factory=tuple
    )
    controller_visibility: dict[str, Any] = field(default_factory=dict)
    did_generate_queries: bool = False
    did_select_providers: bool = False
    did_choose_depth: bool = False
    did_rank_or_filter_sources: bool = False
    did_change_prompt_behavior: bool = False

    def with_pass_result(
        self, summary: RetrievalPassResultSummary
    ) -> "RetrievalLoopState":
        return replace(self, pass_result_summaries=self.pass_result_summaries + (summary,))

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            RETRIEVAL_LOOP_TRACE_KEY: {
                "schema_version": self.schema_version,
                "controller_owned": bool(self.controller_owned),
                "run_id": self.run_id,
                "iteration": int(self.iteration),
                "query_source": self.query_source,
                "current_queries": list(self.current_queries),
                "finalized_queries": list(self.finalized_queries),
                "provider_list": list(self.provider_list),
                "search_depth": self.search_depth,
                "results_per_query": int(self.results_per_query),
                "top_chunks": int(self.top_chunks),
                "max_iterations": int(self.max_iterations),
                "retrieval_budget_facts": deepcopy(self.retrieval_budget_facts),
                "retrieval_stop_decision_ref": deepcopy(
                    self.retrieval_stop_decision_ref
                ),
                "router_query_preparation_ref": deepcopy(
                    self.router_query_preparation_ref
                ),
                "pass_descriptor": self.pass_descriptor.to_trace(),
                "execution_envelope": self.execution_envelope.to_trace(),
                "pass_result_summaries": [
                    summary.to_trace() for summary in self.pass_result_summaries
                ],
                "controller_visibility": deepcopy(self.controller_visibility),
                "did_generate_queries": bool(self.did_generate_queries),
                "did_select_providers": bool(self.did_select_providers),
                "did_choose_depth": bool(self.did_choose_depth),
                "did_rank_or_filter_sources": bool(self.did_rank_or_filter_sources),
                "did_change_prompt_behavior": bool(self.did_change_prompt_behavior),
                "provider_selection_unchanged": True,
                "search_depth_unchanged": True,
                "query_order_unchanged": True,
                "final_answer_behavior_unchanged": True,
                "mechanical_runner_boundary": True,
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY])


def build_retrieval_pass_descriptor(
    *,
    iteration: int,
    query_source: str,
    current_queries: Sequence[Any],
    provider_list: Sequence[Any],
    search_depth: str,
    results_per_query: int,
    top_chunks: int,
    max_iterations: int,
    intent: str,
    complexity: str,
    provider_role: str = "main_retrieval",
    query_similarity_basis: str | None = None,
    prior_queries_for_similarity: Sequence[Any] | None = None,
    retrieval_budget_facts: Mapping[str, Any] | None = None,
    batch_dispatch_authorization_ref: Mapping[str, Any] | None = None,
    source_class_recovery_action_ref: Mapping[str, Any] | None = None,
    weak_corpus_recovery_ref: Mapping[str, Any] | None = None,
) -> RetrievalPassDescriptor:
    return RetrievalPassDescriptor(
        iteration=int(iteration),
        query_source=str(query_source or "orchestrator_precomputed"),
        current_queries=_string_tuple(current_queries),
        provider_list=_string_tuple(provider_list),
        search_depth=str(search_depth or ""),
        results_per_query=int(results_per_query),
        top_chunks=int(top_chunks),
        max_iterations=int(max_iterations),
        intent=str(intent or ""),
        complexity=str(complexity or ""),
        provider_role=str(provider_role or "main_retrieval"),
        query_similarity_basis=query_similarity_basis,
        prior_queries_for_similarity=_string_tuple(prior_queries_for_similarity),
        retrieval_budget_facts=_mapping(retrieval_budget_facts),
        batch_dispatch_authorization_ref=_mapping(batch_dispatch_authorization_ref),
        source_class_recovery_action_ref=_mapping(source_class_recovery_action_ref),
        weak_corpus_recovery_ref=_mapping(weak_corpus_recovery_ref),
    )


def build_retrieval_execution_envelope(
    descriptor: RetrievalPassDescriptor,
    *,
    include_domains: Sequence[Any] | None = None,
    exclude_domains: Sequence[Any] | None = None,
    exa_domain_filter: Sequence[Any] | None = None,
    entity_hint: str | None = None,
) -> RetrievalExecutionEnvelope:
    return RetrievalExecutionEnvelope(
        descriptor=descriptor,
        include_domains=_string_tuple(include_domains),
        exclude_domains=_string_tuple(exclude_domains),
        exa_domain_filter=(
            _string_tuple(exa_domain_filter) if exa_domain_filter is not None else None
        ),
        entity_hint=(str(entity_hint).strip() if entity_hint else None),
    )


def build_retrieval_loop_state(
    *,
    router_query_preparation_state: RouterQueryPreparationState | None,
    pass_descriptor: RetrievalPassDescriptor,
    execution_envelope: RetrievalExecutionEnvelope,
    retrieval_stop_decision: RetrievalStopDecision | Mapping[str, Any] | None = None,
    run_id: str | None = None,
    retrieval_budget_facts: Mapping[str, Any] | None = None,
    controller_visibility: Mapping[str, Any] | None = None,
) -> RetrievalLoopState:
    rq_trace = (
        router_query_preparation_state.to_controller_state()
        if router_query_preparation_state is not None
        else {}
    )
    finalized_queries = _string_tuple(
        (rq_trace.get("query_text_order_facts") or {}).get("finalized_queries")
        if rq_trace
        else ()
    )
    if not finalized_queries:
        finalized_queries = pass_descriptor.current_queries
    current_queries = _string_tuple(
        (rq_trace.get("query_text_order_facts") or {}).get("current_queries")
        if rq_trace
        else ()
    )
    if not current_queries:
        current_queries = pass_descriptor.current_queries
    return RetrievalLoopState(
        schema_version=RETRIEVAL_LOOP_SCHEMA_VERSION,
        controller_owned=True,
        run_id=run_id,
        iteration=pass_descriptor.iteration,
        query_source=pass_descriptor.query_source,
        current_queries=current_queries,
        finalized_queries=finalized_queries,
        provider_list=pass_descriptor.provider_list,
        search_depth=pass_descriptor.search_depth,
        results_per_query=pass_descriptor.results_per_query,
        top_chunks=pass_descriptor.top_chunks,
        max_iterations=pass_descriptor.max_iterations,
        retrieval_budget_facts=(
            _mapping(retrieval_budget_facts) or deepcopy(pass_descriptor.retrieval_budget_facts)
        ),
        retrieval_stop_decision_ref=_stop_decision_reference(retrieval_stop_decision),
        router_query_preparation_ref={
            "available": router_query_preparation_state is not None,
            "schema_version": rq_trace.get("schema_version"),
            "controller_owned": bool(rq_trace.get("controller_owned")),
            "query_source": (
                rq_trace.get("query_preparation_provenance") or {}
            ).get("query_source"),
        },
        pass_descriptor=pass_descriptor,
        execution_envelope=execution_envelope,
        controller_visibility={
            "trace_key": RETRIEVAL_LOOP_TRACE_KEY,
            "owned_by": "Controller",
            "mechanical_runner": "pipeline_orchestrator_adapter",
            **_mapping(controller_visibility),
        },
    )


def summarize_retrieval_pass_result(
    *,
    descriptor: RetrievalPassDescriptor,
    result_count: int,
    seen_url_delta: int,
) -> RetrievalPassResultSummary:
    return RetrievalPassResultSummary(
        iteration=descriptor.iteration,
        query_count=len(descriptor.current_queries),
        provider_count=len(descriptor.provider_list),
        result_count=int(result_count),
        seen_url_delta=int(seen_url_delta),
        provider_role=descriptor.provider_role,
    )


def execute_retrieval_pass_handoff(
    envelope: RetrievalExecutionEnvelope,
    *,
    process_search_queries: Callable[..., list[dict[str, Any]]],
    query_embedding: Any,
    seen_urls: set[str],
    collected_images: set[str],
    embed_provider: str,
    embed_model: str,
    local_url: str | None,
    embed_texts: Callable[..., Any],
    compute_similarities: Callable[..., Any],
    status_container: Any,
    provider_diagnostics: list[dict[str, Any]],
    iteration: int | None = None,
    prior_queries_for_similarity: Sequence[Any] | None = None,
    query_similarity_basis: str | None = None,
) -> list[dict[str, Any]]:
    """Run an already-authorized pass without choosing queries/providers/depth."""

    descriptor = envelope.descriptor
    return process_search_queries(
        list(descriptor.current_queries),
        descriptor.intent,
        descriptor.complexity,
        descriptor.search_depth,
        descriptor.results_per_query,
        list(envelope.include_domains),
        list(envelope.exclude_domains),
        query_embedding,
        seen_urls,
        collected_images,
        embed_provider,
        embed_model,
        local_url,
        embed_texts,
        compute_similarities,
        status_container=status_container,
        search_providers=list(descriptor.provider_list),
        exa_domain_filter=(
            list(envelope.exa_domain_filter)
            if envelope.exa_domain_filter is not None
            else None
        ),
        entity_hint=envelope.entity_hint,
        provider_diagnostics=provider_diagnostics,
        provider_role=descriptor.provider_role,
        iteration=descriptor.iteration if iteration is None else iteration,
        prior_queries_for_similarity=(
            list(prior_queries_for_similarity)
            if prior_queries_for_similarity is not None
            else list(descriptor.prior_queries_for_similarity)
        ),
        query_similarity_basis=(
            query_similarity_basis
            if query_similarity_basis is not None
            else descriptor.query_similarity_basis
        ),
    )
