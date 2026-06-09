"""RunKernel-authorized QueryPlan admission boundary.

AG-91H leaves router/recon/researcher candidate production behavior in the
compatibility runtime. This module governs the point where those already-built
candidates are accepted into QueryPlan and projected back to RunState.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.retrieval_quality import official_bias_phrase, wants_official_source_bias
from core.router_query_preparation_contract import (
    RouterQueryPreparationState,
    with_router_query_runtime_posture,
)
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class QueryPlanAdmissionResult:
    """QueryPlan admission output plus the kernel observation to reduce."""

    queries: list[str]
    current_queries: list[str]
    recency_merge_used: bool
    recency_merge_query: str | None
    router_query_preparation_contract: RouterQueryPreparationState
    observation: Observation


def _query_plan_projection(
    query_authority: QueryPlanRuntimeAdapter,
    *,
    query_source: str,
    recency_merge_used: bool,
    recency_merge_query: str | None,
    current_queries: Sequence[str],
) -> dict[str, Any]:
    query_plan = query_authority.to_trace_fragment().get(QUERY_PLAN_TRACE_KEY, {})
    return {
        "query_plan_ref": query_plan,
        "query_source": query_source,
        "recency_merge_used": bool(recency_merge_used),
        "recency_merge_query": recency_merge_query,
        "current_query_count": len(list(current_queries)),
        "query_order_owner": "QueryPlan",
    }


def execute_query_plan_admission_action(
    action: AuthorizedAction,
    *,
    query_authority: QueryPlanRuntimeAdapter,
    router_query_preparation_contract: RouterQueryPreparationState,
    candidate_queries: Sequence[str],
    candidate_source: str,
    query_type: str,
    current_date: str,
    max_queries: int,
    route_runtime_posture: Mapping[str, Any],
) -> QueryPlanAdmissionResult:
    """Admit existing candidates into QueryPlan after RunKernel authorization."""

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PLAN_ADMISSION,
        stage=QUERY_PLAN_ADMISSION_STAGE,
        expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
    )
    if candidate_source == "recon":
        queries = query_authority.admit_recon_candidates(candidate_queries)
    elif candidate_source == "researcher":
        queries = query_authority.admit_researcher_candidates(candidate_queries)
    else:
        raise ValueError(f"unsupported query admission candidate source: {candidate_source}")

    recency_projection = query_authority.apply_initial_recency_merge(
        queries,
        query_type=query_type,
        current_date=current_date,
        max_queries=max_queries,
    )
    current_queries = query_authority.finalize(
        recency_projection.current_queries,
        max_len=max_queries,
        include_official_bias=False,
    )

    intent = str(route_runtime_posture["intent"])
    router_query_preparation_contract = with_router_query_runtime_posture(
        router_query_preparation_contract,
        intent=intent,
        report_type=str(route_runtime_posture["report_type"]),
        query_type=query_type,
        primary_entity=str(route_runtime_posture["primary_entity"]),
        entities=route_runtime_posture["entities"],
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
        recency_merge_used=recency_projection.recency_merge_used,
        recency_query=recency_projection.recency_merge_query,
        official_bias_requested=wants_official_source_bias(
            query_authority.user_query,
            intent,
        ),
        official_bias_phrase=(
            official_bias_phrase(query_authority.user_query)
            if wants_official_source_bias(query_authority.user_query, intent)
            else None
        ),
        finalized_queries=queries,
        current_queries=current_queries,
        query_source=candidate_source,
    )
    payload = _query_plan_projection(
        query_authority,
        query_source=candidate_source,
        recency_merge_used=recency_projection.recency_merge_used,
        recency_merge_query=recency_projection.recency_merge_query,
        current_queries=current_queries,
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
        recency_merge_used=recency_projection.recency_merge_used,
        recency_merge_query=recency_projection.recency_merge_query,
        router_query_preparation_contract=router_query_preparation_contract,
        observation=observation,
    )


__all__ = [
    "QueryPlanAdmissionResult",
    "execute_query_plan_admission_action",
]
