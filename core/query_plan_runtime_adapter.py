"""Runtime adapter that keeps QueryPlan wiring out of the orchestrator.

The adapter is intentionally narrow: it owns AG-89C QueryPlan state transitions
for existing sanitized query lists while leaving provider, depth, prompt,
ranking, citation, Author, and final-answer behavior untouched.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.query_plan import (
    QueryPlan,
    QueryPlanRole,
    authorize_recency_merge,
    authorize_retrieval_queries,
)
from core.retrieval_quality import should_merge_recency_queries


def _extract_recency_year(text: str) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", text or "")
    return match.group(0) if match else "2026"


@dataclass(frozen=True, slots=True)
class RecencyMergeProjection:
    current_queries: list[str]
    recency_merge_used: bool
    recency_merge_query: str | None


@dataclass(slots=True)
class QueryPlanRuntimeAdapter:
    plan: QueryPlan
    primary_entity: str
    entities_list: Sequence[str] | None
    core_topic: str
    user_query: str
    intent: str
    clean: Callable[[str], str]

    def finalize(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None = None,
        include_official_bias: bool = True,
        origin: str = "model_query_output",
        role: QueryPlanRole | str = QueryPlanRole.INITIAL,
        phase: str = "finalize_retrieval_queries",
    ) -> list[str]:
        self.plan, authorized = authorize_retrieval_queries(
            queries,
            primary_entity=self.primary_entity,
            entities_list=self.entities_list,
            core_topic=self.core_topic,
            user_query=self.user_query,
            intent=self.intent,
            clean=self.clean,
            include_official_bias=include_official_bias,
            max_len=max_len,
            origin=origin,
            role=role,
            plan=self.plan,
            phase=phase,
        )
        return authorized

    def consume_search_work_for_existing_queries(
        self,
        queries: Sequence[str],
        *,
        search_work_projection: Mapping[str, Any] | None,
        search_judgment_projection: Mapping[str, Any] | None = None,
        max_len: int | None,
        origin: str,
        role: QueryPlanRole | str,
        phase: str = "search_work_component_allocation",
    ) -> list[str]:
        context = {
            "primary_entity": self.primary_entity,
            "entities_list": list(self.entities_list or []),
            "core_topic": self.core_topic,
            "user_query": self.user_query,
            "intent": self.intent,
        }
        self.plan, allocated = self.plan.consume_search_work_for_existing_queries(
            queries,
            query_plan_context=context,
            search_work_projection=search_work_projection,
            search_judgment_projection=search_judgment_projection,
            max_len=max_len,
            origin=origin,
            role=role,
            phase=phase,
        )
        return allocated

    def consume_search_judgment_component_gap_authority(
        self,
        queries: Sequence[str],
        *,
        search_judgment_projection: Mapping[str, Any] | None,
    ) -> list[str]:
        self.plan = self.plan.consume_search_judgment_component_gap_authority(
            queries,
            search_judgment_projection=search_judgment_projection,
        )
        return list(queries)

    def admit_recon_candidates(self, queries: Sequence[str]) -> list[str]:
        """Admit recon-rewriter candidates before they become retrieval queries."""

        return self.finalize(
            queries,
            include_official_bias=True,
            origin="recon_rewriter",
            role=QueryPlanRole.RECON_REWRITE,
            phase="recon_seeded_queries",
        )

    def admit_researcher_candidates(self, queries: Sequence[str]) -> list[str]:
        """Admit researcher fallback candidates before they become retrieval queries."""

        return self.finalize(
            queries,
            include_official_bias=True,
            origin="researcher",
            role=QueryPlanRole.INITIAL,
            phase="initial_researcher_queries",
        )

    def merge_recency(
        self,
        current_queries: Sequence[str],
        *,
        recency_query: str,
        max_queries: int | None,
    ) -> list[str]:
        self.plan, merged = authorize_recency_merge(
            self.plan,
            current_queries,
            recency_query=recency_query,
            max_queries=max_queries,
        )
        return merged

    def apply_initial_recency_merge(
        self,
        queries: Sequence[str],
        *,
        query_type: str,
        current_date: str,
        max_queries: int | None,
    ) -> RecencyMergeProjection:
        current_queries = list(queries[:max_queries])
        if not should_merge_recency_queries(self.user_query, self.intent, query_type):
            return RecencyMergeProjection(
                current_queries=current_queries,
                recency_merge_used=False,
                recency_merge_query=None,
            )

        anchor = (self.primary_entity or self.core_topic or "")[:200]
        if not anchor or not max_queries:
            return RecencyMergeProjection(
                current_queries=current_queries,
                recency_merge_used=False,
                recency_merge_query=None,
            )

        year = _extract_recency_year(current_date)
        recency_query = self.clean(f"{anchor} {year} news")
        return RecencyMergeProjection(
            current_queries=self.merge_recency(
                current_queries,
                recency_query=recency_query,
                max_queries=max_queries,
            ),
            recency_merge_used=True,
            recency_merge_query=recency_query,
        )

    def finalize_disambiguation(self, queries: Sequence[str]) -> list[str]:
        return self.finalize(
            queries,
            include_official_bias=False,
            origin="entity_correction",
            role=QueryPlanRole.DISAMBIGUATION,
            phase="disambiguation_retry",
        )

    def finalize_recovery(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None,
        include_official_bias: bool,
    ) -> list[str]:
        return self.finalize(
            queries,
            max_len=max_len,
            include_official_bias=include_official_bias,
            origin="weak_corpus_recovery",
            role=QueryPlanRole.RECOVERY,
            phase="weak_corpus_recovery",
        )

    def finalize_expander_continuation(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None,
    ) -> list[str]:
        return self.finalize(
            queries,
            max_len=max_len,
            include_official_bias=False,
            origin="expander_continuation",
            role=QueryPlanRole.CONTINUATION,
            phase="expander_component_queries",
        )

    def finalize_evaluator_continuation(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None,
    ) -> list[str]:
        return self.finalize(
            queries,
            max_len=max_len,
            include_official_bias=False,
            origin="evaluator_continuation",
            role=QueryPlanRole.CONTINUATION,
            phase="evaluator_next_queries",
        )

    def finalize_supplemental(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None,
    ) -> list[str]:
        return self.finalize(
            queries,
            max_len=max_len,
            include_official_bias=False,
            origin="synthesis_evaluator",
            role=QueryPlanRole.SUPPLEMENTAL,
            phase="supplemental_search",
        )

    def finalize_remediation(
        self,
        queries: Sequence[str],
        *,
        max_len: int | None,
    ) -> list[str]:
        return self.finalize(
            queries,
            max_len=max_len,
            include_official_bias=False,
            origin="scrutineer_remediation",
            role=QueryPlanRole.REMEDIATION,
            phase="scrutineer_remediation",
        )

    def admit_execution_queries(
        self,
        queries: Sequence[str],
        *,
        iteration: int,
        recovery_active: bool,
    ) -> list[str]:
        self.plan = self.plan.admit_execution_queries(
            queries,
            phase="retrieval_execution",
            iteration=iteration,
            role=QueryPlanRole.RECOVERY if recovery_active else QueryPlanRole.FINALIZED,
            origin="retrieval_loop",
        )
        return self.authorized_queries_for_iteration(iteration)

    def record_authorized_dispatch_queries(
        self,
        queries: Sequence[str],
        *,
        origin: str,
        role: QueryPlanRole | str,
        phase: str,
        iteration: int | None,
        authority_source: str,
        authority_ref_digest: str,
    ) -> list[dict[str, Any]]:
        """Identity-record exact queries already approved by another owner."""

        self.plan, item_refs = self.plan.record_authorized_dispatch_queries(
            queries,
            origin=origin,
            role=role,
            phase=phase,
            iteration=iteration,
            authority_source=authority_source,
            authority_ref_digest=authority_ref_digest,
        )
        return [dict(item_ref) for item_ref in item_refs]

    def authorized_queries_for_iteration(self, iteration: int) -> list[str]:
        return list(self.plan.queries_by_iteration().get(iteration, []))

    def queries_by_iteration(self) -> dict[int, list[str]]:
        return self.plan.queries_by_iteration()

    def to_trace_fragment(self) -> dict[str, object]:
        return self.plan.to_trace_fragment()


def build_query_plan_runtime_adapter(
    *,
    run_id: str,
    primary_entity: str,
    entities_list: Sequence[str] | None,
    core_topic: str,
    user_query: str,
    intent: str,
    clean: Callable[[str], str],
) -> QueryPlanRuntimeAdapter:
    return QueryPlanRuntimeAdapter(
        plan=QueryPlan(plan_id=f"query-plan-{run_id}"),
        primary_entity=primary_entity,
        entities_list=entities_list,
        core_topic=core_topic,
        user_query=user_query,
        intent=intent,
        clean=clean,
    )
