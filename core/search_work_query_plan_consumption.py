"""SearchWorkPlan consumption helper for QueryPlan admission.

The helper is deliberately pure and execution-free. It can classify, tag,
reorder, admit, and reject existing candidate query strings, but it never
creates new executable query text or calls provider/search/retrieval surfaces.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

SEARCH_WORK_QUERY_PLAN_CONSUMPTION_SCHEMA_VERSION = "search_work_query_plan_consumption_ag96e2_v1"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)
_KIND_TERMS = {
    "official_current": ("official", "current", "fee", "filing", "rate", "agency"),
    "legal_current_primary": (
        "legal",
        "deadline",
        "law",
        "regulation",
        "regulatory",
        "court",
        "appeal",
    ),
    "canonical_documentation": (
        "api",
        "parameter",
        "docs",
        "documentation",
        "sdk",
        "reference",
        "manual",
        "changelog",
    ),
    "source_bound_numeric": (
        "numeric",
        "number",
        "amount",
        "rate",
        "fee",
        "threshold",
        "calculation",
        "calculated",
    ),
    "conflict_resolution": (
        "compare",
        "conflict",
        "reconcile",
        "currentness",
        "versus",
    ),
    "reputable_secondary": ("overview", "background", "review", "secondary"),
}
_PROVIDER_TERMS = {
    "official_candidate_acquisition": ("official", "agency", "current", "fee"),
    "canonical_extraction": ("api", "parameter", "docs", "documentation", "reference"),
    "fetch_read_extract": ("numeric", "source", "extract", "rate", "amount", "fee"),
    "conflict_currentness_check": ("conflict", "current", "deadline", "compare"),
    "direct_candidate_search": ("overview", "lookup", "background"),
}
_COMPONENT_GAP_AUTHORIZING_DECISIONS = frozenset(
    {
        "continue_targeted_search",
        "recover_missing_canonical",
        "recover_missing_legal_primary",
        "recover_missing_official_current",
        "recover_missing_source_bound_numeric",
    }
)


@dataclass(frozen=True, slots=True)
class SearchWorkComponentHint:
    component_id: str
    rank: int
    tokens: tuple[str, ...] = ()
    source_obligation_ids: tuple[str, ...] = ()
    source_obligation_kinds: tuple[str, ...] = ()
    required_source_classes: tuple[str, ...] = ()
    provider_job_ids: tuple[str, ...] = ()
    provider_job_kinds: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchWorkQueryMatch:
    query: str
    component_id: str | None
    component_rank: int | None
    score: int = 0
    source_obligation_ids: tuple[str, ...] = ()
    provider_job_ids: tuple[str, ...] = ()
    reason: str = "no_component_match"

    def metadata(self, *, used: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "search_work_consumption_used": bool(used),
            "component_coverage_reason": self.reason,
        }
        if self.component_id:
            payload["search_work_component_id"] = self.component_id
        if self.component_rank is not None:
            payload["search_work_component_rank"] = self.component_rank
        if self.source_obligation_ids:
            payload["source_obligation_candidate_ids"] = list(self.source_obligation_ids)
        if self.provider_job_ids:
            payload["provider_job_candidate_ids"] = list(self.provider_job_ids)
        return payload


@dataclass(frozen=True, slots=True)
class SearchWorkQueryPlanAllocationResult:
    search_work_consumed_by_query_plan: bool
    component_ids_considered: tuple[str, ...] = ()
    source_obligation_ids_considered: tuple[str, ...] = ()
    provider_job_ids_considered: tuple[str, ...] = ()
    admitted_query_order: tuple[str, ...] = ()
    rejected_over_budget_queries: tuple[str, ...] = ()
    unfilled_component_ids: tuple[str, ...] = ()
    behavior_boundary_flags: Mapping[str, Any] = field(default_factory=dict)
    fallback_reason: str | None = None
    query_metadata: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    version_bound_component_gap_authority_consumed: bool = False
    version_bound_component_gap_authorized_query: str | None = None
    version_bound_component_gap_fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": SEARCH_WORK_QUERY_PLAN_CONSUMPTION_SCHEMA_VERSION,
            "search_work_consumed_by_query_plan": self.search_work_consumed_by_query_plan,
            "component_ids_considered": list(self.component_ids_considered),
            "source_obligation_ids_considered": list(self.source_obligation_ids_considered),
            "provider_job_ids_considered": list(self.provider_job_ids_considered),
            "admitted_query_order": list(self.admitted_query_order),
            "rejected_over_budget_queries": list(self.rejected_over_budget_queries),
            "unfilled_component_ids": list(self.unfilled_component_ids),
            "behavior_boundary_flags": dict(self.behavior_boundary_flags),
            "fallback_reason": self.fallback_reason,
            "query_metadata": {
                query: dict(metadata)
                for query, metadata in self.query_metadata.items()
            },
            "version_bound_component_gap_authority_consumed": (
                self.version_bound_component_gap_authority_consumed
            ),
            "version_bound_component_gap_authorized_query": (
                self.version_bound_component_gap_authorized_query
            ),
            "version_bound_component_gap_fallback_reason": (
                self.version_bound_component_gap_fallback_reason
            ),
        }
        return _json_safe(_without_empty(payload))


def initial_strategy_search_work_bindings(
    search_work_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return compact exact bindings for component-aware initial admission.

    The result contains no executable query text.  It is safe to copy into
    QueryPlan item metadata so later SearchJudgment can identify prepared
    secondaries without acquiring provider, evidence, or dispatch authority.
    """

    plan = _extract_plan_like_projection(_mapping(search_work_projection))
    if not plan:
        raise ValueError(
            "initial query strategy requires a contract-bound SearchWorkPlan"
        )
    if plan.get("passive") is not False or plan.get("runtime_consumed") is not True:
        raise ValueError(
            "initial query strategy requires an active runtime-consumed SearchWorkPlan"
        )
    components = _sequence_of_mappings(plan.get("components"))
    provider_jobs = _sequence_of_mappings(plan.get("provider_jobs"))
    if not components:
        raise ValueError(
            "initial query strategy SearchWorkPlan has no accepted components"
        )
    plan_metadata = _mapping(plan.get("metadata"))
    plan_id = _clean_token(
        plan_metadata.get("search_work_plan_id")
        or plan_metadata.get("construction_id")
    )
    plan_digest = sha256(
        json.dumps(
            _json_safe(plan),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    contract_ref = _mapping(plan_metadata.get("accepted_contract_ref"))
    bindings: dict[str, dict[str, Any]] = {}
    for rank, component in enumerate(components, start=1):
        component_id = _clean_token(component.get("component_id"))
        if not component_id:
            raise ValueError("SearchWorkPlan component is missing component_id")
        metadata = _mapping(component.get("metadata"))
        accepted_component_ref = _mapping(
            metadata.get("accepted_component_ref")
        )
        if accepted_component_ref.get("component_id") != component_id:
            raise ValueError(
                "SearchWorkPlan accepted component binding is missing or stale"
            )
        source_ids = tuple(
            value
            for obligation in _sequence_of_mappings(
                component.get("source_obligations")
            )
            if (
                value := _clean_token(
                    obligation.get("obligation_id")
                    or obligation.get("candidate_id")
                )
            )
        )
        jobs = tuple(
            job
            for job in provider_jobs
            if component_id in _text_sequence(job.get("component_ids"))
        )
        provider_job_ids = tuple(
            value
            for job in jobs
            if (
                value := _clean_token(
                    job.get("provider_job_id")
                    or job.get("work_id")
                    or job.get("candidate_id")
                )
            )
        )
        requirement_refs = [
            _mapping(item)
            for item in _sequence_of_mappings(
                metadata.get("search_requirement_refs")
            )
        ]
        bindings[component_id] = {
            "search_work_consumption_used": True,
            "search_work_component_id": component_id,
            "search_work_component_rank": rank,
            "accepted_component_ref": accepted_component_ref,
            "source_obligation_candidate_ids": list(source_ids),
            "provider_job_candidate_ids": list(provider_job_ids),
            "search_requirement_refs": requirement_refs,
            "search_requirement_ids": [
                item["requirement_id"]
                for item in requirement_refs
                if item.get("requirement_id")
            ],
            "search_work_plan_ref": {
                "search_work_plan_id": plan_id,
                "search_work_plan_digest": plan_digest,
                "accepted_contract_ref": contract_ref,
            },
            "required_component": (
                accepted_component_ref.get("requirement_posture") == "required"
            ),
            "contains_executable_query_text": False,
        }
    return _json_safe(bindings)


def allocate_existing_queries_by_search_work(
    *,
    candidate_queries: Sequence[str],
    query_plan_context: Mapping[str, Any] | None,
    search_work_projection: Mapping[str, Any] | None,
    max_len: int | None,
    origin: str,
    role: str,
    phase: str,
    search_judgment_projection: Mapping[str, Any] | None = None,
) -> SearchWorkQueryPlanAllocationResult:
    """Allocate existing query strings across SearchWork components.

    No new query strings are synthesized. The returned order is a permutation of
    the supplied candidates, capped by ``max_len`` when SearchWork consumption is
    usable.
    """

    queries = tuple(_clean_query(query) for query in candidate_queries if _clean_query(query))
    flags = _behavior_boundary_flags(max_len=max_len, origin=origin, role=role, phase=phase)
    if search_work_projection is None:
        return SearchWorkQueryPlanAllocationResult(
            search_work_consumed_by_query_plan=False,
            admitted_query_order=queries if max_len is None else queries[: max(0, max_len)],
            rejected_over_budget_queries=() if max_len is None else queries[max(0, max_len) :],
            behavior_boundary_flags=flags,
            fallback_reason="search_work_projection_absent",
            version_bound_component_gap_fallback_reason=(
                "search_work_projection_absent"
                if search_judgment_projection
                else None
            ),
        )

    components, fallback_reason = _component_hints(search_work_projection)
    if fallback_reason or not components:
        return SearchWorkQueryPlanAllocationResult(
            search_work_consumed_by_query_plan=False,
            admitted_query_order=queries,
            behavior_boundary_flags=flags,
            fallback_reason=fallback_reason or "search_work_projection_has_no_components",
            version_bound_component_gap_fallback_reason=(
                fallback_reason or "search_work_projection_has_no_components"
                if search_judgment_projection
                else None
            ),
        )
    if not queries:
        return SearchWorkQueryPlanAllocationResult(
            search_work_consumed_by_query_plan=False,
            component_ids_considered=tuple(component.component_id for component in components),
            source_obligation_ids_considered=_all_obligation_ids(components),
            provider_job_ids_considered=_all_provider_job_ids(components),
            behavior_boundary_flags=flags,
            fallback_reason="candidate_queries_absent",
            version_bound_component_gap_fallback_reason=(
                "candidate_queries_absent" if search_judgment_projection else None
            ),
        )

    route_tokens = _context_tokens(query_plan_context)
    matches_by_query = {
        query: _best_match(query, components, route_tokens)
        for query in queries
    }
    ordered = _coverage_first_order(queries, components, matches_by_query)
    limit = len(ordered) if max_len is None else max(0, int(max_len))
    admitted = tuple(ordered[:limit])
    rejected = tuple(ordered[limit:])
    admitted_components = {
        match.component_id
        for query in admitted
        if (match := matches_by_query.get(query)) and match.component_id
    }
    unfilled = tuple(
        component.component_id
        for component in components
        if component.component_id not in admitted_components
    )
    metadata = {
        query: match.metadata(used=True)
        for query, match in matches_by_query.items()
        if match.component_id
    }
    metadata, gap_consumed, gap_query, gap_reason = (
        _apply_version_bound_component_gap_authority(
            admitted,
            metadata,
            search_judgment_projection=search_judgment_projection,
        )
    )
    return SearchWorkQueryPlanAllocationResult(
        search_work_consumed_by_query_plan=True,
        component_ids_considered=tuple(component.component_id for component in components),
        source_obligation_ids_considered=_all_obligation_ids(components),
        provider_job_ids_considered=_all_provider_job_ids(components),
        admitted_query_order=admitted,
        rejected_over_budget_queries=rejected,
        unfilled_component_ids=unfilled,
        behavior_boundary_flags=flags,
        query_metadata=metadata,
        version_bound_component_gap_authority_consumed=gap_consumed,
        version_bound_component_gap_authorized_query=gap_query,
        version_bound_component_gap_fallback_reason=gap_reason,
    )


def authorize_existing_query_by_version_bound_component_gap(
    *,
    existing_queries: Sequence[str],
    query_metadata: Mapping[str, Mapping[str, Any]],
    search_judgment_projection: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], bool, str | None, str | None]:
    """Tag one already-existing query from one version-bound semantic gap."""

    queries = tuple(_clean_query(query) for query in existing_queries if _clean_query(query))
    return _apply_version_bound_component_gap_authority(
        queries,
        query_metadata,
        search_judgment_projection=search_judgment_projection,
    )


def _apply_version_bound_component_gap_authority(
    queries: Sequence[str],
    query_metadata: Mapping[str, Mapping[str, Any]],
    *,
    search_judgment_projection: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], bool, str | None, str | None]:
    metadata = {
        _clean_query(query): dict(value)
        for query, value in query_metadata.items()
        if _clean_query(query) and isinstance(value, Mapping)
    }
    if not search_judgment_projection:
        return metadata, False, None, None
    gap, reason = _version_bound_component_gap(search_judgment_projection)
    if reason or not gap:
        return metadata, False, None, reason
    target_component = _normalize_component_id(gap["answer_component_id"])
    matches = [
        query
        for query in queries
        if _normalize_component_id(
            metadata.get(query, {}).get("search_work_component_id")
        )
        == target_component
    ]
    if not matches:
        return metadata, False, None, "zero_existing_candidate_query_matches_component_gap"
    if len(matches) > 1:
        return metadata, False, None, "multiple_existing_candidate_queries_match_component_gap"
    query = matches[0]
    existing = metadata.setdefault(query, {})
    existing["version_bound_component_gap_authorized"] = True
    existing["version_bound_component_gap_authority"] = {
        "owner": "RunKernel.RunAuthoritySearchJudgment",
        "judgment_id": _clean_token(search_judgment_projection.get("judgment_id")),
        "accepted_contract_version": gap["accepted_contract_version"],
        "accepted_contract_digest": gap["accepted_contract_digest"],
        "answer_component_id": gap["answer_component_id"],
        "component_digest": gap["component_digest"],
        "semantic_gap_code": gap["semantic_gap_code"],
        "existing_candidate_query": query,
        "query_text_generated": False,
        "new_executable_query_text_generated": False,
    }
    return metadata, True, query, None


def _version_bound_component_gap(
    projection: Mapping[str, Any],
) -> tuple[dict[str, str] | None, str | None]:
    source = _mapping(projection)
    if source.get("owner") != "RunKernel.RunAuthoritySearchJudgment":
        return None, "search_judgment_projection_not_canonical"
    if source.get("canonical_state") is not True or source.get("trace_only") is not False:
        return None, "search_judgment_projection_not_canonical"
    if _clean_token(source.get("decision")) not in _COMPONENT_GAP_AUTHORIZING_DECISIONS:
        return None, "search_judgment_decision_does_not_authorize_component_gap_query"
    continuation = _mapping(source.get("continuation"))
    if "allowed" in continuation and continuation.get("allowed") is not True:
        return None, "search_judgment_decision_does_not_authorize_component_gap_query"
    gaps = [
        item for item in _sequence_of_mappings(source.get("gaps"))
        if _clean_token(item.get("semantic_gap_code"))
        == "missing_required_component_coverage"
    ]
    if not gaps:
        return None, "search_judgment_has_no_version_bound_component_gap"
    if len(gaps) > 1:
        return None, "search_judgment_has_multiple_version_bound_component_gaps"
    gap = gaps[0]
    required = {
        "accepted_contract_version": _clean_token(
            gap.get("accepted_contract_version")
        ),
        "accepted_contract_digest": _clean_token(
            gap.get("accepted_contract_digest"),
            limit=128,
        ),
        "answer_component_id": _clean_token(gap.get("answer_component_id")),
        "component_digest": _clean_token(gap.get("component_digest"), limit=128),
        "semantic_gap_code": _clean_token(gap.get("semantic_gap_code")),
    }
    if not all(required.values()):
        return None, "version_bound_component_gap_missing_identity"
    if _clean_token(gap.get("requirement_kind")) != "semantic_component_coverage":
        return None, "version_bound_component_gap_generic_kind_erases_identity"
    return {key: str(value) for key, value in required.items()}, None


def _component_hints(
    projection: Mapping[str, Any],
) -> tuple[tuple[SearchWorkComponentHint, ...], str | None]:
    source = _mapping(projection)
    if not source:
        return (), "search_work_projection_malformed"
    query_plan_shadow = _extract_query_plan_shadow(source)
    if query_plan_shadow:
        return _component_hints_from_query_plan_shadow(query_plan_shadow), None
    plan = _extract_plan_like_projection(source)
    if plan:
        return _component_hints_from_plan(plan), None
    return (), "search_work_projection_missing_query_plan_or_plan_components"


def _extract_query_plan_shadow(source: Mapping[str, Any]) -> dict[str, Any]:
    if source.get("trace_key") == "query_plan_work_shadow_projection":
        return _mapping(source)
    nested = _mapping(source.get("query_plan_work_shadow_projection"))
    if nested:
        return nested
    projections = _mapping(source.get("projections"))
    return _mapping(projections.get("query_plan_work_shadow_projection"))


def _extract_plan_like_projection(source: Mapping[str, Any]) -> dict[str, Any]:
    if _sequence_of_mappings(source.get("components")):
        return _mapping(source)
    plan = _mapping(source.get("search_work_plan"))
    if _sequence_of_mappings(plan.get("components")):
        return plan
    return {}


def _component_hints_from_query_plan_shadow(
    projection: Mapping[str, Any],
) -> tuple[SearchWorkComponentHint, ...]:
    components = _sequence_of_mappings(projection.get("components"))
    obligations_by_component = _mapping(projection.get("source_obligations_by_component"))
    jobs_by_component = _mapping(projection.get("provider_jobs_by_component"))
    hints: list[SearchWorkComponentHint] = []
    for rank, component in enumerate(components, start=1):
        component_id = _clean_token(component.get("component_id")) or f"component-{rank}"
        obligations = _sequence_of_mappings(obligations_by_component.get(component_id))
        jobs = _sequence_of_mappings(jobs_by_component.get(component_id))
        obligation_kinds = tuple(
            value for obligation in obligations if (value := _clean_token(obligation.get("kind")))
        )
        provider_kinds = tuple(
            value for job in jobs if (value := _clean_token(job.get("work_kind")))
        )
        hints.append(
            SearchWorkComponentHint(
                component_id=component_id,
                rank=rank,
                tokens=_tokens(
                    component_id,
                    component.get("group_id"),
                    *obligation_kinds,
                    *provider_kinds,
                ),
                source_obligation_ids=tuple(
                    value
                    for obligation in obligations
                    if (value := _clean_token(obligation.get("obligation_id")))
                ),
                source_obligation_kinds=obligation_kinds,
                required_source_classes=tuple(
                    value
                    for obligation in obligations
                    if (value := _clean_token(obligation.get("required_source_class")))
                ),
                provider_job_ids=tuple(
                    value for job in jobs if (value := _clean_token(job.get("work_id")))
                ),
                provider_job_kinds=provider_kinds,
            )
        )
    return tuple(hints)


def _component_hints_from_plan(plan: Mapping[str, Any]) -> tuple[SearchWorkComponentHint, ...]:
    provider_jobs = _sequence_of_mappings(plan.get("provider_jobs"))
    hints: list[SearchWorkComponentHint] = []
    for rank, component in enumerate(_sequence_of_mappings(plan.get("components")), start=1):
        component_id = _clean_token(component.get("component_id")) or f"component-{rank}"
        obligations = _sequence_of_mappings(component.get("source_obligations"))
        jobs = tuple(
            job for job in provider_jobs
            if component_id in _text_sequence(job.get("component_ids"))
        )
        subquestion = (
            component.get("user_facing_subquestion")
            or component.get("subquestion")
            or component.get("component_label")
        )
        obligation_kinds = tuple(
            value for obligation in obligations if (value := _clean_token(obligation.get("kind")))
        )
        provider_kinds = tuple(
            value
            for job in jobs
            if (
                value := _clean_token(
                    job.get("job_kind") or job.get("work_kind")
                )
            )
        )
        source_classes = tuple(
            value
            for obligation in obligations
            if (
                value := _clean_token(
                    obligation.get("required_source_class")
                    or obligation.get("source_class")
                )
            )
        )
        hints.append(
            SearchWorkComponentHint(
                component_id=component_id,
                rank=rank,
                tokens=_tokens(
                    component_id,
                    subquestion,
                    *(component.get("entities") or ()),
                    *(component.get("anchors") or ()),
                    *obligation_kinds,
                    *provider_kinds,
                    *source_classes,
                ),
                source_obligation_ids=tuple(
                    value
                    for obligation in obligations
                    if (
                        value := _clean_token(
                            obligation.get("obligation_id")
                            or obligation.get("candidate_id")
                        )
                    )
                ),
                source_obligation_kinds=obligation_kinds,
                required_source_classes=source_classes,
                provider_job_ids=tuple(
                    value
                    for job in jobs
                    if (
                        value := _clean_token(
                            job.get("provider_job_id")
                            or job.get("work_id")
                            or job.get("candidate_id")
                        )
                    )
                ),
                provider_job_kinds=provider_kinds,
            )
        )
    return tuple(hints)


def _best_match(
    query: str,
    components: Sequence[SearchWorkComponentHint],
    route_tokens: set[str],
) -> SearchWorkQueryMatch:
    query_tokens = set(_tokens(query))
    best: SearchWorkQueryMatch | None = None
    for component in components:
        component_tokens = set(component.tokens) - route_tokens
        kind_terms = {
            token
            for kind in component.source_obligation_kinds
            for token in _KIND_TERMS.get(kind, ())
        }
        provider_terms = {
            token
            for kind in component.provider_job_kinds
            for token in _PROVIDER_TERMS.get(kind, ())
        }
        source_class_terms = set(_tokens(*component.required_source_classes))
        overlap = query_tokens & (component_tokens | kind_terms | provider_terms | source_class_terms)
        score = len(overlap)
        if score <= 0:
            continue
        reason = "component_token_match"
        if query_tokens & kind_terms:
            reason = "source_obligation_kind_match"
        if query_tokens & provider_terms:
            reason = "provider_job_hint_match"
        if query_tokens & component_tokens:
            reason = "component_subquestion_token_match"
        match = SearchWorkQueryMatch(
            query=query,
            component_id=component.component_id,
            component_rank=component.rank,
            score=score,
            source_obligation_ids=component.source_obligation_ids,
            provider_job_ids=component.provider_job_ids,
            reason=reason,
        )
        if best is None or (match.score, -match.component_rank) > (
            best.score,
            -(best.component_rank or 9999),
        ):
            best = match
    return best or SearchWorkQueryMatch(query=query, component_id=None, component_rank=None)


def _coverage_first_order(
    queries: Sequence[str],
    components: Sequence[SearchWorkComponentHint],
    matches_by_query: Mapping[str, SearchWorkQueryMatch],
) -> tuple[str, ...]:
    remaining = list(queries)
    ordered: list[str] = []
    for component in components:
        matches = [
            query for query in remaining
            if matches_by_query[query].component_id == component.component_id
        ]
        if not matches:
            continue
        selected = max(
            matches,
            key=lambda query: (matches_by_query[query].score, -queries.index(query)),
        )
        ordered.append(selected)
        remaining.remove(selected)
    ordered.extend(remaining)
    return tuple(ordered)


def _context_tokens(context: Mapping[str, Any] | None) -> set[str]:
    if not isinstance(context, Mapping):
        return set()
    values: list[Any] = [
        context.get("primary_entity"),
        context.get("core_topic"),
        context.get("intent"),
        context.get("query_type"),
    ]
    for key in ("entities_list", "entities"):
        value = context.get(key)
        if isinstance(value, Sequence) and not isinstance(value, str):
            values.extend(value)
    return set(_tokens(*values))


def _all_obligation_ids(components: Sequence[SearchWorkComponentHint]) -> tuple[str, ...]:
    return tuple(
        value
        for component in components
        for value in component.source_obligation_ids
    )


def _all_provider_job_ids(components: Sequence[SearchWorkComponentHint]) -> tuple[str, ...]:
    return tuple(
        value
        for component in components
        for value in component.provider_job_ids
    )


def _behavior_boundary_flags(
    *,
    max_len: int | None,
    origin: str,
    role: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "query_text_generated": False,
        "new_executable_query_text_generated": False,
        "component_gap_authority_changed_retrieval_queries": False,
        "provider_job_hints_executed": False,
        "provider_selected": False,
        "provider_search_behavior_changed": False,
        "search_depth_changed": False,
        "retrieval_behavior_changed": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "final_answer_behavior_changed": False,
        "source_obligation_satisfaction_changed": False,
        "source_obligations_marked_satisfied": False,
        "official_current_custody_satisfied": False,
        "max_len_respected": max_len is None or max_len >= 0,
        "query_plan_admission_order_may_change": True,
        "origin": _clean_token(origin),
        "role": _clean_token(role),
        "phase": _clean_token(phase),
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ()
    return tuple(text for item in value if (text := _clean_token(item)))


def _clean_query(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:300]


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_component_id(value: Any) -> str | None:
    token = _clean_token(value)
    if not token:
        return None
    return token.casefold().removeprefix("component:")


def _tokens(*values: Any) -> tuple[str, ...]:
    tokens: list[str] = []
    for value in values:
        text = str(value or "").casefold()
        tokens.extend(re.findall(r"[a-z0-9]+", text))
    return tuple(token for token in tokens if len(token) >= 3)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "SEARCH_WORK_QUERY_PLAN_CONSUMPTION_SCHEMA_VERSION",
    "SearchWorkQueryPlanAllocationResult",
    "allocate_existing_queries_by_search_work",
    "authorize_existing_query_by_version_bound_component_gap",
    "initial_strategy_search_work_bindings",
]
