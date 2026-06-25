"""Authoritative QueryPlan state for retrieval query identity.

AG-89C keeps this seam deliberately narrow: existing query producers may still
produce candidates, but finalized query identity, ordering, and trace projection
are represented here before retrieval consumes query text.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from core.retrieval_quality import (
    apply_domain_anchor_to_query,
    approved_entity_aliases,
    format_quoted_anchor,
    official_bias_phrase,
    primary_anchor,
    query_has_domain_anchor,
    wants_official_source_bias,
)
from core.search_work_query_plan_consumption import (
    allocate_existing_queries_by_search_work,
    authorize_existing_query_by_version_bound_component_gap,
)

QUERY_PLAN_TRACE_KEY = "query_plan"


class QueryPlanStatus(str, Enum):
    OBSERVED_MODEL_QUERY = "observed_model_query"
    OBSERVED_RECON_REWRITE = "observed_recon_rewrite"
    OBSERVED_ENTITY_CORRECTION = "observed_entity_correction"
    ADMITTED = "admitted"
    DEDUPLICATED = "deduplicated"
    FINALIZED = "finalized"
    RECENCY_MERGED = "recency_merged"
    OFFICIAL_BIAS_APPLIED = "official_bias_applied"
    CANONICAL_BIAS_APPLIED = "canonical_bias_applied"
    ORDERED = "ordered"
    RECOVERY_ADMITTED = "recovery_admitted"
    CONTINUATION_ADMITTED = "continuation_admitted"
    SUPPLEMENTAL_ADMITTED = "supplemental_admitted"
    REMEDIATION_ADMITTED = "remediation_admitted"
    REJECTED_EMPTY = "rejected_empty"
    REJECTED_DUPLICATE = "rejected_duplicate"
    REJECTED_OVER_BUDGET = "rejected_over_budget"
    REJECTED_BLOCKED = "rejected_blocked"
    PROVIDER_POLICY_UNCHANGED = "provider_policy_unchanged"
    DEPTH_POLICY_UNCHANGED = "depth_policy_unchanged"


class QueryPlanRole(str, Enum):
    INITIAL = "initial"
    FINALIZED = "finalized"
    RECENCY = "recency"
    OFFICIAL_BIAS = "official_bias"
    CANONICAL_BIAS = "canonical_bias"
    RECOVERY = "recovery"
    CONTINUATION = "continuation"
    SUPPLEMENTAL = "supplemental"
    REMEDIATION = "remediation"
    DISAMBIGUATION = "disambiguation"
    RECON_REWRITE = "recon_rewrite"


_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)


def _clean_text(value: Any, *, limit: int = 300) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return text[:limit]


def _safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=500)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_text(key, limit=80)
            if not key_text:
                continue
            if key_text.lower() in _SENSITIVE_KEYS:
                out[key_text] = "[redacted]"
            else:
                out[key_text] = _safe_json(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(item, depth=depth + 1) for item in list(value)[:50]]
    return _clean_text(value, limit=200)


@dataclass(frozen=True, slots=True)
class QueryPlanItem:
    item_id: str
    origin: str
    role: QueryPlanRole | str
    status: QueryPlanStatus | str
    original_query: str | None = None
    authorized_query: str | None = None
    mutation_reason: str | None = None
    admission_reason: str | None = None
    phase: str | None = None
    iteration: int | None = None
    order: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, QueryPlanStatus) else str(self.status)
        role = self.role.value if isinstance(self.role, QueryPlanRole) else str(self.role)
        if status not in {item.value for item in QueryPlanStatus}:
            raise ValueError(f"unknown query plan status: {status}")
        if role not in {item.value for item in QueryPlanRole}:
            raise ValueError(f"unknown query plan role: {role}")
        if not _clean_text(self.item_id, limit=80):
            raise ValueError("query plan item requires item_id")
        object.__setattr__(self, "status", QueryPlanStatus(status))
        object.__setattr__(self, "role", QueryPlanRole(role))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "item_id": _clean_text(self.item_id, limit=80),
            "origin": _clean_text(self.origin, limit=80),
            "role": self.role.value,
            "status": self.status.value,
            "original_query": _clean_text(self.original_query, limit=300),
            "authorized_query": _clean_text(self.authorized_query, limit=300),
            "mutation_reason": _clean_text(self.mutation_reason, limit=120),
            "admission_reason": _clean_text(self.admission_reason, limit=120),
            "phase": _clean_text(self.phase, limit=80),
            "iteration": self.iteration,
            "order": self.order,
            "metadata": _safe_json(self.metadata),
        }
        return {key: value for key, value in payload.items() if value not in (None, {}, [])}


@dataclass(frozen=True, slots=True)
class QueryPlan:
    plan_id: str = "query-plan-1"
    items: tuple[QueryPlanItem, ...] = ()
    search_work_consumption: Mapping[str, Any] = field(default_factory=dict)

    def _next_id(self) -> str:
        return f"{self.plan_id}:q{len(self.items) + 1}"

    def append(
        self,
        *,
        origin: str,
        role: QueryPlanRole | str,
        status: QueryPlanStatus | str,
        original_query: str | None = None,
        authorized_query: str | None = None,
        mutation_reason: str | None = None,
        admission_reason: str | None = None,
        phase: str | None = None,
        iteration: int | None = None,
        order: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "QueryPlan":
        item = QueryPlanItem(
            item_id=self._next_id(),
            origin=origin,
            role=role,
            status=status,
            original_query=original_query,
            authorized_query=authorized_query,
            mutation_reason=mutation_reason,
            admission_reason=admission_reason,
            phase=phase,
            iteration=iteration,
            order=order,
            metadata=dict(metadata or {}),
        )
        return replace(self, items=self.items + (item,))

    def admit_execution_queries(
        self,
        queries: Sequence[str],
        *,
        phase: str,
        iteration: int,
        role: QueryPlanRole | str = QueryPlanRole.FINALIZED,
        origin: str = "retrieval_loop",
    ) -> "QueryPlan":
        plan = self
        for order, query in enumerate(queries, start=1):
            plan = plan.append(
                origin=origin,
                role=role,
                status=QueryPlanStatus.ORDERED,
                authorized_query=query,
                phase=phase,
                iteration=iteration,
                order=order,
                admission_reason="ordered_for_consumption",
            )
        return plan

    def consume_search_work_for_existing_queries(
        self,
        queries: Sequence[str],
        *,
        query_plan_context: Mapping[str, Any] | None = None,
        search_work_projection: Mapping[str, Any] | None = None,
        search_judgment_projection: Mapping[str, Any] | None = None,
        max_len: int | None,
        origin: str,
        role: QueryPlanRole | str,
        phase: str = "search_work_component_allocation",
    ) -> tuple["QueryPlan", list[str]]:
        if search_work_projection is None:
            return self, list(queries)
        result = allocate_existing_queries_by_search_work(
            candidate_queries=queries,
            query_plan_context=query_plan_context,
            search_work_projection=search_work_projection,
            search_judgment_projection=search_judgment_projection,
            max_len=max_len,
            origin=origin,
            role=role.value if isinstance(role, QueryPlanRole) else str(role),
            phase=phase,
        )
        plan = replace(self, search_work_consumption=result.to_dict())
        if not result.search_work_consumed_by_query_plan:
            return plan, list(queries)
        admitted = list(result.admitted_query_order)
        metadata_by_query = {
            str(query): dict(metadata)
            for query, metadata in result.query_metadata.items()
            if isinstance(metadata, Mapping)
        }
        for order, query in enumerate(admitted, start=1):
            plan = plan.append(
                origin=origin,
                role=role,
                status=QueryPlanStatus.FINALIZED,
                authorized_query=query,
                admission_reason="search_work_component_allocation",
                mutation_reason="search_work_component_aware_order",
                phase=phase,
                order=order,
                metadata=metadata_by_query.get(query, {}),
            )
        for offset, query in enumerate(result.rejected_over_budget_queries, start=len(admitted) + 1):
            metadata = {
                "max_len": max_len,
                "would_have_status": QueryPlanStatus.FINALIZED.value,
                **metadata_by_query.get(query, {}),
            }
            plan = plan.append(
                origin=origin,
                role=role,
                status=QueryPlanStatus.REJECTED_OVER_BUDGET,
                authorized_query=query,
                admission_reason="rejected_over_budget",
                mutation_reason="search_work_component_aware_cap",
                phase=phase,
                order=offset,
                metadata=metadata,
            )
        return plan, admitted

    def consume_search_judgment_component_gap_authority(
        self,
        queries: Sequence[str],
        *,
        search_judgment_projection: Mapping[str, Any] | None,
        origin: str = "run_authority_search_judgment",
        role: QueryPlanRole | str = QueryPlanRole.FINALIZED,
        phase: str = "search_judgment_component_gap_authority",
    ) -> "QueryPlan":
        metadata, consumed, authorized_query, fallback_reason = (
            authorize_existing_query_by_version_bound_component_gap(
                existing_queries=queries,
                query_metadata=self.search_work_consumption.get(
                    "query_metadata",
                    {},
                )
                if isinstance(self.search_work_consumption, Mapping)
                else {},
                search_judgment_projection=search_judgment_projection,
            )
        )
        consumption = dict(self.search_work_consumption or {})
        if metadata:
            consumption["query_metadata"] = metadata
        consumption["version_bound_component_gap_authority_consumed"] = consumed
        if authorized_query:
            consumption["version_bound_component_gap_authorized_query"] = (
                authorized_query
            )
        if fallback_reason:
            consumption["version_bound_component_gap_fallback_reason"] = (
                fallback_reason
            )
        plan = replace(self, search_work_consumption=consumption)
        if not consumed or not authorized_query:
            return plan
        return plan.append(
            origin=origin,
            role=role,
            status=QueryPlanStatus.FINALIZED,
            authorized_query=authorized_query,
            admission_reason="version_bound_component_gap_authority_consumed",
            mutation_reason="metadata_only_existing_query_authority",
            phase=phase,
            metadata=metadata.get(authorized_query, {}),
        )

    def queries_by_iteration(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        ordered = [
            item for item in self.items
            if item.status == QueryPlanStatus.ORDERED and item.iteration is not None and item.authorized_query
        ]
        for item in sorted(ordered, key=lambda x: (int(x.iteration or 0), int(x.order or 0), x.item_id)):
            out.setdefault(int(item.iteration or 0), []).append(str(item.authorized_query))
        return out

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "plan_id": _clean_text(self.plan_id, limit=80),
            "items": [item.to_dict() for item in self.items],
            "authorized_queries_by_iteration": {
                str(key): value for key, value in self.queries_by_iteration().items()
            },
            "provider_policy": QueryPlanStatus.PROVIDER_POLICY_UNCHANGED.value,
            "depth_policy": QueryPlanStatus.DEPTH_POLICY_UNCHANGED.value,
            "custody_satisfaction_owner": "official_current_source_custody",
        }
        if self.search_work_consumption:
            payload["search_work_consumption"] = _safe_json(
                self.search_work_consumption
            )
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {QUERY_PLAN_TRACE_KEY: self.to_dict()}


def authorize_retrieval_queries(
    queries: Sequence[str],
    *,
    primary_entity: str,
    entities_list: Sequence[str] | None,
    core_topic: str,
    user_query: str,
    intent: str,
    clean: Callable[[str], str] | None = None,
    include_official_bias: bool = True,
    max_len: int | None = None,
    origin: str = "model_query_output",
    role: QueryPlanRole | str = QueryPlanRole.INITIAL,
    plan: QueryPlan | None = None,
    phase: str = "finalize_retrieval_queries",
) -> tuple[QueryPlan, list[str]]:
    _clean = clean or (lambda s: " ".join((s or "").strip().split()))
    aliases = approved_entity_aliases(primary_entity, list(entities_list or []), core_topic)
    primary_display = primary_anchor(primary_entity, list(entities_list or []), core_topic)
    active = plan or QueryPlan()
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        observed = _clean(str(query))
        active = active.append(
            origin=origin,
            role=role,
            status=QueryPlanStatus.OBSERVED_MODEL_QUERY,
            original_query=observed or None,
            phase=phase,
        )
        if not observed:
            active = active.append(
                origin=origin,
                role=role,
                status=QueryPlanStatus.REJECTED_EMPTY,
                original_query=str(query),
                phase=phase,
            )
            continue
        authorized = _clean(
            apply_domain_anchor_to_query(
                observed,
                aliases=aliases,
                primary_display=primary_display,
            )
        )[:300]
        key = authorized.casefold()
        if key in seen:
            active = active.append(
                origin=origin,
                role=role,
                status=QueryPlanStatus.REJECTED_DUPLICATE,
                original_query=observed,
                authorized_query=authorized,
                phase=phase,
                mutation_reason="deduplicated",
            )
            continue
        seen.add(key)
        candidates.append(
            {
                "origin": origin,
                "role": QueryPlanRole.FINALIZED,
                "status": QueryPlanStatus.FINALIZED,
                "original_query": observed,
                "authorized_query": authorized,
                "mutation_reason": "finalized",
                "admission_reason": "admitted",
                "phase": phase,
            }
        )
    if include_official_bias and wants_official_source_bias(user_query, intent) and (primary_display or "").strip():
        phrase = official_bias_phrase(user_query)
        candidate_queries = [str(item["authorized_query"]) for item in candidates]
        has_existing = any(
            "official" in query.lower() and query_has_domain_anchor(query, aliases)
            for query in candidate_queries
        )
        if has_existing:
            active = active.append(
                origin="official_bias",
                role=QueryPlanRole.OFFICIAL_BIAS,
                status=QueryPlanStatus.OFFICIAL_BIAS_APPLIED,
                mutation_reason="official_bias_already_present",
                admission_reason="admitted",
                phase=phase,
                metadata={
                    "custody_satisfied": False,
                    "custody_owner": "official_current_source_custody",
                },
            )
        else:
            bias_q = _clean(f"{format_quoted_anchor(primary_display)} {phrase}")[:300]
            low = bias_q.casefold()
            duplicate = any(low == query.casefold() for query in candidate_queries) or any(
                low in query.casefold() for query in candidate_queries
            )
            if not bias_q:
                active = active.append(
                    origin="official_bias",
                    role=QueryPlanRole.OFFICIAL_BIAS,
                    status=QueryPlanStatus.REJECTED_EMPTY,
                    mutation_reason="official_bias_applied",
                    phase=phase,
                    metadata={"custody_satisfied": False},
                )
            elif duplicate:
                active = active.append(
                    origin="official_bias",
                    role=QueryPlanRole.OFFICIAL_BIAS,
                    status=QueryPlanStatus.REJECTED_DUPLICATE,
                    authorized_query=bias_q,
                    mutation_reason="official_bias_applied",
                    phase=phase,
                    metadata={"custody_satisfied": False},
                )
            else:
                candidates = [
                    {
                        "origin": "official_bias",
                        "role": QueryPlanRole.OFFICIAL_BIAS,
                        "status": QueryPlanStatus.OFFICIAL_BIAS_APPLIED,
                        "authorized_query": bias_q,
                        "mutation_reason": "official_bias_applied",
                        "admission_reason": "admitted",
                        "phase": phase,
                        "metadata": {
                            "custody_satisfied": False,
                            "custody_owner": "official_current_source_custody",
                        },
                    }
                ] + candidates

    limit = max_len if max_len is not None else len(candidates)
    consumed: list[str] = []
    for order, candidate in enumerate(candidates, start=1):
        if order <= max(0, limit):
            consumed.append(str(candidate["authorized_query"]))
            active = active.append(order=order, **candidate)
            continue
        active = active.append(
            origin=str(candidate["origin"]),
            role=candidate["role"],
            status=QueryPlanStatus.REJECTED_OVER_BUDGET,
            original_query=candidate.get("original_query"),
            authorized_query=str(candidate["authorized_query"]),
            mutation_reason="max_len_cap_applied",
            admission_reason="rejected_over_budget",
            phase=phase,
            order=order,
            metadata={
                "max_len": max_len,
                "would_have_status": (
                    candidate["status"].value
                    if isinstance(candidate["status"], QueryPlanStatus)
                    else str(candidate["status"])
                ),
            },
        )
    return active, consumed


def authorize_recency_merge(
    plan: QueryPlan,
    current_queries: Sequence[str],
    *,
    recency_query: str,
    max_queries: int | None,
    phase: str = "recency_merge",
) -> tuple[QueryPlan, list[str]]:
    merged = ([recency_query] + [q for q in current_queries if q and q != recency_query])[: max_queries or 1]
    plan = plan.append(
        origin="recency_merge",
        role=QueryPlanRole.RECENCY,
        status=QueryPlanStatus.RECENCY_MERGED,
        authorized_query=recency_query,
        mutation_reason="recency_merged",
        admission_reason="admitted",
        phase=phase,
        order=1,
        metadata={"max_queries": max_queries, "output_order": list(merged)},
    )
    return plan, merged
