"""Converged SearchOS initial strategy and QueryPlan admission boundaries.

The ordinary chain is SearchPlanner -> accepted AnswerContract -> QueryPlan.
Uncertainty is preserved as a provider-neutral QueryPlan job and resolved by
the existing SearchOS worklist. SearchWorkPlan and QueryProduction are not
ordinary semantic/query authorities. This module does not own provider
selection, READ, evidence, citation, or post-result follow-up dispatch.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.anchor_resolution import build_shadow_anchor_packet
from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    InitialQueryAllocationPolicy,
)
from core.initial_query_strategy_failure import (
    invoke_run_kernel_initial_planning,
)
from core.nutrition_lookup import detect_nutrition_lookup_telemetry
from core.query_plan import (
    QUERY_PLAN_TRACE_KEY,
    InitialQueryAdmissionResult,
    QueryPlanRole,
)
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.router_query_preparation_contract import (
    RouterQueryPreparationState,
    with_router_query_runtime_posture,
)
from core.run_authority_contract import contract_query_hints_from_projection
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerAdapter,
    SearchPlannerInput,
    execute_search_planner_action,
    initial_query_strategies_from_planner_state,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)
from core.search_work_provider_job_execution import (
    build_provider_job_execution_handoff,
)


class QueryStrategyConvergenceFailureCode(str, Enum):
    """Closed owner-authored safe code for ordinary initial convergence failures."""

    ANSWER_CONTRACT_BINDING_MISSING = "answer_contract_binding_missing"
    ALLOCATION_POLICY_REQUIRED = "allocation_policy_required"
    QUESTION_MEANING_RECORD_MISSING = "question_meaning_record_missing"
    INITIAL_STRATEGIES_EMPTY = "initial_strategies_empty"
    INITIAL_STRATEGY_TEXT_UNBOUNDED = "initial_strategy_text_unbounded"


class QueryStrategyConvergenceError(ValueError):
    """Raised before dispatch when the required initial chain cannot converge."""

    SAFE_FAILURE_ORIGIN = "query_strategy_convergence"
    __slots__ = ("_failure_code",)

    def __init__(
        self,
        message: str,
        *,
        failure_code: QueryStrategyConvergenceFailureCode,
    ) -> None:
        if not isinstance(failure_code, QueryStrategyConvergenceFailureCode):
            raise TypeError("failure_code must be a QueryStrategyConvergenceFailureCode")
        super().__init__(message)
        self._failure_code = failure_code

    @property
    def failure_code(self) -> QueryStrategyConvergenceFailureCode:
        return self._failure_code


@dataclass(frozen=True, slots=True)
class InitialQueryStrategyConvergenceResult:
    planner_action: AuthorizedAction
    candidate_queries: list[str]
    candidate_strategies: list[dict[str, Any]]
    candidate_source: str
    effective_route_posture: dict[str, Any]
    include_domains: list[str]
    anchor_packet_telemetry: dict[str, Any]
    nutrition_lookup_telemetry: dict[str, Any]
    waste_flags: list[str]
    empty_entity_flag: bool
    contract_source_requirement_hints: list[dict[str, Any]]
    initial_query_allocation_policy: InitialQueryAllocationPolicy

    @property
    def intent(self) -> str:
        return str(self.effective_route_posture["intent"])

    @property
    def report_type(self) -> str:
        return str(self.effective_route_posture["report_type"])

    @property
    def image_mode(self) -> str:
        return str(self.effective_route_posture["image_mode"])

    @property
    def core_topic(self) -> str:
        return str(self.effective_route_posture["core_topic"])

    @property
    def query_type(self) -> str:
        return str(self.effective_route_posture["query_type"])

    @property
    def primary_entity(self) -> str:
        return str(self.effective_route_posture["primary_entity"])

    @property
    def entities_list(self) -> list[str]:
        return list(self.effective_route_posture["entities_list"])

    @property
    def is_academic(self) -> bool:
        return bool(self.effective_route_posture["is_academic"])

    @property
    def routing_override_applied(self) -> bool:
        return bool(self.effective_route_posture["routing_override_applied"])

    @property
    def routing_override_reason(self) -> str | None:
        reason = self.effective_route_posture["routing_override_reason"]
        return None if reason is None else str(reason)

    @property
    def complexity(self) -> str:
        return str(self.effective_route_posture["complexity"])

    @property
    def max_queries(self) -> int:
        return int(self.effective_route_posture["max_queries"])

    @property
    def results_per_query(self) -> int:
        return int(self.effective_route_posture["results_per_query"])

    @property
    def search_depth(self) -> str:
        return str(self.effective_route_posture["search_depth"])

    @property
    def top_chunks(self) -> int:
        return int(self.effective_route_posture["top_chunks"])

    @property
    def max_iterations(self) -> int:
        return int(self.effective_route_posture["max_iterations"])


@dataclass(frozen=True, slots=True)
class InitialSearchPlannerAcceptanceResult:
    """Product-owned state available exactly after initial contract acceptance."""

    planner_action: AuthorizedAction
    acceptance_action: AuthorizedAction
    accepted_contract: Any


def _clean_query_projection(queries: Sequence[str]) -> list[str]:
    return [" ".join(str(query or "").split())[:300] for query in queries if str(query or "").strip()]


def _complexity_for_strategy(strategy: str) -> str:
    if strategy == "Fast":
        return "low"
    if strategy == "Balanced":
        return "medium"
    return "high"


def _budget_for_complexity(complexity: str) -> dict[str, int | str]:
    if complexity == "high":
        return {
            "max_queries": 3,
            "results_per_query": 8,
            "search_depth": "advanced",
            "top_chunks": 40,
            "max_iterations": 3,
        }
    if complexity == "medium":
        return {
            "max_queries": 2,
            "results_per_query": 6,
            "search_depth": "basic",
            "top_chunks": 20,
            "max_iterations": 2,
        }
    return {
        "max_queries": 2,
        "results_per_query": 5,
        "search_depth": "basic",
        "top_chunks": 8,
        "max_iterations": 1,
    }


def _effective_route_posture(
    *,
    intent: str,
    report_type: str,
    image_mode: str,
    core_topic: str,
    primary_entity: str,
    entities_list: Sequence[str],
    is_academic: bool,
    query_type: str,
    routing_override_applied: bool,
    routing_override_reason: str | None,
    focus_academic: bool,
    force_intent_news: bool,
    complexity: str,
    max_queries: int,
    results_per_query: int,
    search_depth: str,
    top_chunks: int,
    max_iterations: int,
    run_contract_ref: Mapping[str, Any] | None = None,
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "report_type": report_type,
        "query_type": query_type,
        "image_mode": image_mode,
        "core_topic": core_topic,
        "primary_entity": primary_entity,
        "entities_list": list(entities_list),
        "is_academic": bool(is_academic),
        "routing_override_applied": bool(routing_override_applied),
        "routing_override_reason": routing_override_reason,
        "focus_academic": bool(focus_academic),
        "force_intent_news": bool(force_intent_news),
        "complexity": complexity,
        "max_queries": int(max_queries),
        "results_per_query": int(results_per_query),
        "search_depth": search_depth,
        "top_chunks": int(top_chunks),
        "max_iterations": int(max_iterations),
        "run_contract_ref": dict(run_contract_ref or {}),
        "contract_source_requirement_hints": [
            dict(item) for item in (contract_source_requirement_hints or ()) if isinstance(item, Mapping)
        ],
        "contract_consumed_by_query_plan": bool(run_contract_ref),
    }


def _initial_route_posture_from_preparation(
    *,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: Sequence[str],
    news_preferred_domains: Sequence[str],
    run_contract_projection: Mapping[str, Any] | None,
    waste_flags: Sequence[str] | None,
) -> dict[str, Any]:
    intent = router_query_preparation_contract.intent
    report_type = router_query_preparation_contract.report_type
    image_mode = router_query_preparation_contract.image_mode
    core_topic = router_query_preparation_contract.core_topic
    is_academic = router_query_preparation_contract.is_academic
    query_type = router_query_preparation_contract.query_type
    primary_entity = router_query_preparation_contract.primary_entity
    entities_list = list(router_query_preparation_contract.entities_list)
    router_entity_retry_used = router_query_preparation_contract.router_entity_retry_used
    router_original_report_type = router_query_preparation_contract.router_original_report_type
    router_original_query_type = router_query_preparation_contract.router_original_query_type
    routing_override_applied = False
    routing_override_reason: str | None = None
    contract_source_requirement_hints = contract_query_hints_from_projection(run_contract_projection)
    run_contract_ref: dict[str, Any] = {}
    if isinstance(run_contract_projection, Mapping) and run_contract_projection:
        run_contract_ref = {
            "owner": run_contract_projection.get("owner"),
            "contract_id": run_contract_projection.get("contract_id"),
            "synthesis_mode": run_contract_projection.get("synthesis_mode"),
            "selected_template_ids": run_contract_projection.get(
                "selected_template_ids",
                [],
            ),
            "source_requirement_count": run_contract_projection.get(
                "source_requirement_count",
                0,
            ),
        }
    nutrition_lookup_telemetry = detect_nutrition_lookup_telemetry(query)
    if nutrition_lookup_telemetry["nutrition_lookup_detected"]:
        report_type = "quantitative_comparison"
        routing_override_applied = True
        routing_override_reason = "nutrition_macro_per_100g_lookup"
    if focus_academic:
        is_academic = True
    if force_intent_news:
        intent = "news"
    anchor_packet_telemetry: dict[str, Any] = {}
    if strategy == "Balanced":
        anchor_packet_telemetry = build_shadow_anchor_packet(
            mode=strategy,
            query=query,
            current_date=current_date,
            intent=intent,
            report_type=report_type,
            router_original_report_type=router_original_report_type,
            query_type=query_type,
            router_original_query_type=router_original_query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            entities=entities_list,
            router_entity_retry_used=router_entity_retry_used,
        )
    active_include_domains = list(include_domains)
    if intent == "news":
        active_include_domains = list(set(active_include_domains + list(news_preferred_domains)))
    complexity = _complexity_for_strategy(strategy)
    budget = _budget_for_complexity(complexity)
    entity_count_before = len(entities_list)
    if entities_list:
        primary_entity = entities_list[0][:200]
    elif primary_entity.strip():
        entities_list = [primary_entity.strip()[:200]]
        primary_entity = entities_list[0][:200]
    return {
        "effective_route_posture": _effective_route_posture(
            intent=intent,
            report_type=report_type,
            image_mode=image_mode,
            core_topic=core_topic,
            primary_entity=primary_entity,
            entities_list=entities_list,
            is_academic=is_academic,
            query_type=query_type,
            routing_override_applied=routing_override_applied,
            routing_override_reason=routing_override_reason,
            focus_academic=focus_academic,
            force_intent_news=force_intent_news,
            complexity=complexity,
            max_queries=int(budget["max_queries"]),
            results_per_query=int(budget["results_per_query"]),
            search_depth=str(budget["search_depth"]),
            top_chunks=int(budget["top_chunks"]),
            max_iterations=int(budget["max_iterations"]),
            run_contract_ref=run_contract_ref,
            contract_source_requirement_hints=contract_source_requirement_hints,
        ),
        "include_domains": active_include_domains,
        "anchor_packet_telemetry": anchor_packet_telemetry,
        "nutrition_lookup_telemetry": dict(nutrition_lookup_telemetry),
        "waste_flags": list(waste_flags or []),
        "empty_entity_flag": len(entities_list) == 0,
        "contract_source_requirement_hints": list(contract_source_requirement_hints),
        "entity_count_before": entity_count_before,
    }


def execute_initial_search_planner_acceptance(
    *,
    run_kernel: Any,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    include_domains: Sequence[str],
    exclude_domains: Sequence[str] = (),
    route_projection: Mapping[str, Any],
    run_contract_projection: Mapping[str, Any],
    supplied_context: Mapping[str, Any] | None = None,
    planner_adapter: SearchPlannerAdapter,
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
) -> InitialSearchPlannerAcceptanceResult:
    """Run the existing production Planner path through initial acceptance only.

    This shared prefix deliberately stops before candidate-strategy derivation
    and QueryPlan admission, preserving the ordinary convergence function as
    the sole consumer that proceeds into downstream query work.
    """

    if not isinstance(initial_query_allocation_policy, InitialQueryAllocationPolicy):
        raise QueryStrategyConvergenceError(
            "initial strategy convergence requires the code-owned policy",
            failure_code=QueryStrategyConvergenceFailureCode.ALLOCATION_POLICY_REQUIRED,
        )
    route_facts = {
        "intent": router_query_preparation_contract.intent,
        "report_type": router_query_preparation_contract.report_type,
        "query_type": router_query_preparation_contract.query_type,
        "core_topic": router_query_preparation_contract.core_topic,
        "primary_entity": router_query_preparation_contract.primary_entity,
        "entities": list(router_query_preparation_contract.entities_list),
        "is_academic": router_query_preparation_contract.is_academic,
    }
    planner_input = SearchPlannerInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        user_query_text=query,
        requested_mode=strategy,
        safe_context={
            "phase": "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01",
            "product_path": True,
            "route_facts": route_facts,
            "run_contract_projection": dict(run_contract_projection),
            "current_date": current_date,
            "include_domains": list(include_domains),
            "exclude_domains": list(exclude_domains),
            "supplied_context": dict(supplied_context or {}),
            "supplied_context_posture": {
                "planning_context_only": True,
                "evidence_admitted": False,
                "source_obligation_satisfied": False,
                "citation_eligible": False,
            },
            "initial_query_allocation_policy_version": (initial_query_allocation_policy.policy_version),
        },
        route_context_ref={
            "route_id": route_projection.get("route_id"),
        },
        run_context_ref={
            "run_contract_id": run_contract_projection.get("contract_id"),
        },
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    planner_action = invoke_run_kernel_initial_planning(
        "search_planner_production",
        lambda: run_kernel.authorize_search_planner_production(
            user_query_digest=planner_input.user_query_digest,
            planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
            inputs={
                "route_id": route_projection.get("route_id"),
                "run_contract_id": run_contract_projection.get("contract_id"),
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
            },
        ),
    )
    planner_result = execute_search_planner_action(
        action=planner_action,
        planner_input=planner_input,
        adapter=planner_adapter,
    )
    invoke_run_kernel_initial_planning(
        "search_planner_production",
        lambda: run_kernel.reduce(
            Observation.from_action(
                planner_action,
                observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
                status=RunStageStatus.COMPLETED,
                payload=planner_result.observation_payload,
            )
        ),
    )

    qmr = dict(run_kernel.state.search_planner_proposal_state.get("question_meaning_record") or {})
    if not qmr:
        raise QueryStrategyConvergenceError(
            "SearchPlanner reduction did not produce a QuestionMeaningRecord",
            failure_code=(QueryStrategyConvergenceFailureCode.QUESTION_MEANING_RECORD_MISSING),
        )
    acceptance_action = invoke_run_kernel_initial_planning(
        "initial_answer_contract_acceptance",
        lambda: run_kernel.authorize_initial_answer_contract_acceptance(
            parent_question_meaning_record_id=str(qmr.get("record_id") or ""),
            parent_proposal_digest=str(qmr.get("record_digest") or ""),
            inputs={
                "planner_action_id": planner_action.action_id,
                "allocation_policy_version": (initial_query_allocation_policy.policy_version),
            },
        ),
    )
    invoke_run_kernel_initial_planning(
        "initial_answer_contract_acceptance",
        lambda: run_kernel.reduce(
            Observation.from_action(
                acceptance_action,
                observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
                status=RunStageStatus.COMPLETED,
                payload={"question_meaning_record": qmr},
            )
        ),
    )
    accepted_contract = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    if not accepted_contract:
        raise QueryStrategyConvergenceError(
            "SearchPlanner reduction did not bind an accepted AnswerContract",
            failure_code=(QueryStrategyConvergenceFailureCode.ANSWER_CONTRACT_BINDING_MISSING),
        )
    return InitialSearchPlannerAcceptanceResult(
        planner_action=planner_action,
        acceptance_action=acceptance_action,
        accepted_contract=accepted_contract,
    )


def execute_initial_query_strategy_convergence(
    *,
    run_kernel: Any,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: Sequence[str],
    exclude_domains: Sequence[str] = (),
    news_preferred_domains: Sequence[str],
    route_projection: Mapping[str, Any],
    run_contract_projection: Mapping[str, Any],
    supplied_context: Mapping[str, Any] | None = None,
    planner_adapter: SearchPlannerAdapter,
    provider_diagnostics: MutableSequence[dict[str, Any]],
    waste_flags: Sequence[str] | None = None,
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
) -> InitialQueryStrategyConvergenceResult:
    """Run the one ordinary initial semantic-planning producer chain.

    A malformed planner proposal or stale contract ref yields no
    retrieval-dispatchable query. Initial uncertainty remains in the accepted
    contract and enters QueryPlan/SearchOS without a SearchWorkPlan or
    QueryProduction carrier.
    """

    acceptance = execute_initial_search_planner_acceptance(
        run_kernel=run_kernel,
        router_query_preparation_contract=router_query_preparation_contract,
        query=query,
        strategy=strategy,
        current_date=current_date,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        route_projection=route_projection,
        run_contract_projection=run_contract_projection,
        supplied_context=supplied_context,
        planner_adapter=planner_adapter,
        initial_query_allocation_policy=initial_query_allocation_policy,
    )
    planner_action = acceptance.planner_action
    accepted_contract = acceptance.accepted_contract
    candidate_strategies = initial_query_strategies_from_planner_state(
        planner_state=run_kernel.state.search_planner_proposal_state,
        accepted_contract=accepted_contract,
        policy=initial_query_allocation_policy,
    )
    if not candidate_strategies:
        raise QueryStrategyConvergenceError(
            "SearchPlanner produced no valid initial component query strategies; "
            "legacy initial producer fallback is retired",
            failure_code=QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY,
        )
    candidate_queries = [str(item.get("candidate_query_text") or "").strip() for item in candidate_strategies]
    if any(not query or len(query) > 300 for query in candidate_queries):
        raise QueryStrategyConvergenceError(
            "SearchPlanner initial query strategies require bounded exact text",
            failure_code=(QueryStrategyConvergenceFailureCode.INITIAL_STRATEGY_TEXT_UNBOUNDED),
        )
    route_bundle = _initial_route_posture_from_preparation(
        router_query_preparation_contract=router_query_preparation_contract,
        query=query,
        strategy=strategy,
        current_date=current_date,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        include_domains=include_domains,
        news_preferred_domains=news_preferred_domains,
        run_contract_projection=run_contract_projection,
        waste_flags=waste_flags,
    )
    return InitialQueryStrategyConvergenceResult(
        planner_action=planner_action,
        candidate_queries=list(candidate_queries),
        candidate_strategies=[dict(item) for item in candidate_strategies],
        candidate_source="search_planner",
        effective_route_posture=route_bundle["effective_route_posture"],
        include_domains=list(route_bundle["include_domains"]),
        anchor_packet_telemetry=dict(route_bundle["anchor_packet_telemetry"]),
        nutrition_lookup_telemetry=dict(route_bundle["nutrition_lookup_telemetry"]),
        waste_flags=list(route_bundle["waste_flags"]),
        empty_entity_flag=bool(route_bundle["empty_entity_flag"]),
        contract_source_requirement_hints=list(route_bundle["contract_source_requirement_hints"]),
        initial_query_allocation_policy=initial_query_allocation_policy,
    )


@dataclass(frozen=True, slots=True)
class QueryPlanAdmissionResult:
    """QueryPlan admission output plus the kernel observation to reduce."""

    queries: list[str]
    current_queries: list[str]
    recency_merge_used: bool
    recency_merge_query: str | None
    initial_query_admission: InitialQueryAdmissionResult
    router_query_preparation_contract: RouterQueryPreparationState
    observation: Observation


def _query_plan_projection(
    query_authority: QueryPlanRuntimeAdapter,
    *,
    query_source: str,
    recency_merge_used: bool,
    recency_merge_query: str | None,
    current_queries: Sequence[str],
    initial_query_admission: InitialQueryAdmissionResult,
    initial_query_allocation_policy: InitialQueryAllocationPolicy,
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
    provider_job_execution_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    query_plan = query_authority.to_trace_fragment().get(QUERY_PLAN_TRACE_KEY, {})
    projection = {
        "query_plan_ref": query_plan,
        "query_source": query_source,
        "recency_merge_used": bool(recency_merge_used),
        "recency_merge_query": recency_merge_query,
        "current_query_count": len(list(current_queries)),
        "query_order_owner": "QueryPlan",
        "initial_query_admission": initial_query_admission.to_dict(),
        "initial_query_allocation_policy": (initial_query_allocation_policy.to_dict()),
        "small_global_initial_query_cap_applied": False,
        "required_component_globally_truncated": False,
        "post_result_followup_dispatched": False,
        "contract_source_requirement_hints": [
            dict(item) for item in (contract_source_requirement_hints or ()) if isinstance(item, Mapping)
        ],
    }
    if provider_job_execution_handoff:
        projection["provider_job_execution_handoff"] = dict(provider_job_execution_handoff)
        projection["provider_job_execution_handoff_present"] = True
    return projection


def execute_query_plan_admission_action(
    action: AuthorizedAction,
    *,
    query_authority: QueryPlanRuntimeAdapter,
    router_query_preparation_contract: RouterQueryPreparationState,
    candidate_queries: Sequence[str],
    candidate_strategies: Sequence[Mapping[str, Any]],
    candidate_source: str,
    query_type: str,
    current_date: str,
    max_queries: int,
    route_runtime_posture: Mapping[str, Any],
    accepted_contract: Mapping[str, Any] | None = None,
    initial_query_allocation_policy: InitialQueryAllocationPolicy = (DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY),
) -> QueryPlanAdmissionResult:
    """Admit component-bound planner strategies into the first DISCOVER wave."""

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PLAN_ADMISSION,
        stage=QUERY_PLAN_ADMISSION_STAGE,
        expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
    )
    if candidate_source != "search_planner":
        raise ValueError(f"unsupported query admission candidate source: {candidate_source}")
    strategies = [dict(item) for item in candidate_strategies if isinstance(item, Mapping)]
    strategy_queries = [str(item.get("candidate_query_text") or "").strip() for item in strategies]
    if strategy_queries != [str(query) for query in candidate_queries]:
        raise ValueError("QueryPlan admission requires exact SearchPlanner strategy/query order")
    if not isinstance(initial_query_allocation_policy, InitialQueryAllocationPolicy):
        raise ValueError("QueryPlan admission requires the code-owned policy")
    allocation = query_authority.admit_initial_component_strategies(
        strategies,
        accepted_contract=accepted_contract or {},
        policy=initial_query_allocation_policy,
        origin=candidate_source,
    )
    current_queries = list(allocation.immediate_dispatch_queries)
    # Only the immediate first wave crosses the ordinary retrieval-loop seam.
    # Prepared secondaries remain QueryPlan state for later SearchJudgment.
    queries = list(current_queries)
    immediate_set = set(current_queries)
    immediate_strategies = [
        item for item in strategies if str(item.get("candidate_query_text") or "").strip() in immediate_set
    ]
    recency_queries = [
        str(item.get("candidate_query_text") or "").strip()
        for item in immediate_strategies
        if str(item.get("requested_role") or "").strip() == QueryPlanRole.RECENCY.value
    ]
    recency_merge_used = bool(recency_queries)
    recency_merge_query = recency_queries[0] if len(recency_queries) == 1 else None
    official_bias_requested = any(
        str(item.get("requested_role") or "").strip()
        in {
            QueryPlanRole.OFFICIAL_BIAS.value,
            QueryPlanRole.CANONICAL_BIAS.value,
        }
        for item in immediate_strategies
    )
    contract_source_requirement_hints = [
        dict(item)
        for item in route_runtime_posture.get("contract_source_requirement_hints", [])
        if isinstance(item, Mapping)
    ]
    run_contract_ref = (
        dict(route_runtime_posture.get("run_contract_ref") or {})
        if isinstance(route_runtime_posture.get("run_contract_ref"), Mapping)
        else {}
    )
    if run_contract_ref or contract_source_requirement_hints:
        query_authority.plan = query_authority.plan.append(
            origin="run_authority_contract",
            role="initial",
            status="admitted",
            phase="run_contract_source_requirements",
            admission_reason="source_requirement_hints_consumed",
            metadata={
                "contract_ref": run_contract_ref,
                "contract_source_requirement_hints": contract_source_requirement_hints,
                "contract_changed_query_order": False,
            },
        )

    provider_job_execution_handoff = build_provider_job_execution_handoff(
        search_work_projection=None,
        query_plan_trace=query_authority.to_trace_fragment().get(
            QUERY_PLAN_TRACE_KEY,
            {},
        ),
        current_queries=current_queries,
    )
    intent = str(route_runtime_posture["intent"])
    route_entities = route_runtime_posture.get(
        "entities_list",
        route_runtime_posture.get("entities"),
    )
    route_query_type = str(route_runtime_posture.get("query_type", query_type))
    router_query_preparation_contract = with_router_query_runtime_posture(
        router_query_preparation_contract,
        intent=intent,
        report_type=str(route_runtime_posture["report_type"]),
        query_type=route_query_type,
        primary_entity=str(route_runtime_posture["primary_entity"]),
        entities=route_entities,
        is_academic=bool(route_runtime_posture["is_academic"]),
        routing_override_applied=bool(route_runtime_posture["routing_override_applied"]),
        routing_override_reason=route_runtime_posture["routing_override_reason"],
        focus_academic=bool(route_runtime_posture["focus_academic"]),
        force_intent_news=bool(route_runtime_posture["force_intent_news"]),
        complexity=str(route_runtime_posture["complexity"]),
        max_queries=max_queries,
        results_per_query=int(route_runtime_posture["results_per_query"]),
        search_depth=str(route_runtime_posture["search_depth"]),
        top_chunks=int(route_runtime_posture["top_chunks"]),
        max_iterations=int(route_runtime_posture["max_iterations"]),
        recency_merge_used=recency_merge_used,
        recency_query=recency_merge_query,
        official_bias_requested=official_bias_requested,
        official_bias_phrase=None,
        finalized_queries=current_queries,
        current_queries=current_queries,
        query_source=candidate_source,
        run_contract_ref=run_contract_ref,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    payload = _query_plan_projection(
        query_authority,
        query_source=candidate_source,
        recency_merge_used=recency_merge_used,
        recency_merge_query=recency_merge_query,
        current_queries=current_queries,
        initial_query_admission=allocation,
        initial_query_allocation_policy=initial_query_allocation_policy,
        contract_source_requirement_hints=contract_source_requirement_hints,
        provider_job_execution_handoff=provider_job_execution_handoff,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return QueryPlanAdmissionResult(
        queries=list(queries),
        current_queries=list(current_queries),
        recency_merge_used=recency_merge_used,
        recency_merge_query=recency_merge_query,
        initial_query_admission=allocation,
        router_query_preparation_contract=router_query_preparation_contract,
        observation=observation,
    )


__all__ = [
    "InitialQueryStrategyConvergenceResult",
    "InitialSearchPlannerAcceptanceResult",
    "QueryPlanAdmissionResult",
    "QueryStrategyConvergenceError",
    "QueryStrategyConvergenceFailureCode",
    "execute_initial_query_strategy_convergence",
    "execute_initial_search_planner_acceptance",
    "execute_query_plan_admission_action",
]
