"""Authoritative QueryPlan state for retrieval query identity.

AG-89C keeps this seam deliberately narrow: existing query producers may still
produce candidates, but finalized query identity, ordering, and trace projection
are represented here before retrieval consumes query text.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.initial_query_allocation_policy import InitialQueryAllocationPolicy
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
    initial_strategy_search_work_bindings,
)

QUERY_PLAN_TRACE_KEY = "query_plan"
_RECORDED_DISPATCH_ADMISSION_REASON = (
    "recorded_from_existing_dispatch_authority"
)
_AUTHORITY_SOURCE_TOKEN_MAX_LENGTH = 120
_AUTHORITY_SOURCE_TOKEN_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
)


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


def _canonical_sha256(value: Any) -> str:
    """Return a full SHA-256 digest over a deterministic JSON encoding."""

    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _text_sha256(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _is_bounded_authority_source_token(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= _AUTHORITY_SOURCE_TOKEN_MAX_LENGTH
        and all(
            character in _AUTHORITY_SOURCE_TOKEN_CHARACTERS
            for character in value
        )
    )


def _is_full_sha256_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


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

    def to_ref(self, plan_id: str) -> dict[str, str]:
        """Return the canonical execution lineage ref for this exact plan item."""

        canonical_plan_id = _clean_text(plan_id, limit=120)
        if canonical_plan_id is None:
            raise ValueError("query plan item ref requires plan_id")
        authorized_query = self.authorized_query
        if authorized_query is None:
            raise ValueError("query plan item ref requires an authorized query")
        return {
            "query_plan_item_id": self.item_id,
            "query_plan_item_digest": _canonical_sha256(
                {
                    "query_plan_id": canonical_plan_id,
                    "item": self.to_dict(),
                }
            ),
            "query_digest": _text_sha256(authorized_query),
            "authorized_query": authorized_query,
            "query_plan_role": self.role.value,
            "iteration": self.iteration,
            "order": self.order,
        }


@dataclass(frozen=True, slots=True)
class InitialQueryAdmissionResult:
    admitted_candidate_queries: tuple[str, ...]
    immediate_dispatch_queries: tuple[str, ...]
    prepared_secondary_candidates: tuple[Mapping[str, Any], ...]
    required_component_ids: tuple[str, ...]
    primary_item_ids_by_component: Mapping[str, tuple[str, ...]]
    duplicate_candidates_rejected: tuple[Mapping[str, Any], ...] = ()
    over_ceiling_candidates_rejected: tuple[Mapping[str, Any], ...] = ()
    unjustified_secondary_candidates_rejected: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted_candidate_queries": list(self.admitted_candidate_queries),
            "immediate_dispatch_queries": list(self.immediate_dispatch_queries),
            "prepared_secondary_candidates": [
                dict(item) for item in self.prepared_secondary_candidates
            ],
            "required_component_ids": list(self.required_component_ids),
            "primary_item_ids_by_component": {
                component_id: list(item_ids)
                for component_id, item_ids in self.primary_item_ids_by_component.items()
            },
            "duplicate_candidates_rejected": [
                dict(item) for item in self.duplicate_candidates_rejected
            ],
            "over_ceiling_candidates_rejected": [
                dict(item) for item in self.over_ceiling_candidates_rejected
            ],
            "unjustified_secondary_candidates_rejected": [
                dict(item)
                for item in self.unjustified_secondary_candidates_rejected
            ],
            "post_result_followup_dispatched": False,
        }


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

    def admit_initial_component_strategies(
        self,
        strategies: Sequence[Mapping[str, Any]],
        *,
        search_work_projection: Mapping[str, Any],
        policy: InitialQueryAllocationPolicy,
        clean: Callable[[str], str],
        origin: str = "search_planner",
        phase: str = "initial_component_query_admission",
    ) -> tuple["QueryPlan", InitialQueryAdmissionResult]:
        """Admit component-bound initial candidates without a small global cap."""

        bindings = initial_strategy_search_work_bindings(search_work_projection)
        required_component_ids = tuple(
            component_id
            for component_id, binding in bindings.items()
            if binding.get("required_component") is True
        )
        if not required_component_ids:
            raise ValueError(
                "initial QueryPlan admission requires accepted required components"
            )
        grouped: dict[str, list[Mapping[str, Any]]] = {
            component_id: [] for component_id in bindings
        }
        for strategy in strategies:
            component_id = _clean_text(strategy.get("component_id"), limit=160)
            if not component_id or component_id not in bindings:
                raise ValueError(
                    "initial query strategy references an unknown SearchWork component"
                )
            grouped[component_id].append(strategy)

        plan = self
        admitted_candidates: list[str] = []
        immediate_primary: dict[str, list[str]] = {
            component_id: [] for component_id in required_component_ids
        }
        immediate_secondary: list[str] = []
        prepared_secondary: list[dict[str, Any]] = []
        primary_item_ids: dict[str, list[str]] = {
            component_id: [] for component_id in required_component_ids
        }
        duplicates: list[dict[str, Any]] = []
        over_ceiling: list[dict[str, Any]] = []
        unjustified_secondary: list[dict[str, Any]] = []
        canonical_candidates: list[dict[str, Any]] = []
        query_metadata: dict[str, dict[str, Any]] = {}

        for component_id in bindings:
            component_strategies = sorted(
                grouped.get(component_id, []),
                key=lambda item: (
                    0 if item.get("candidate_kind") == "primary" else 1,
                    str(item.get("strategy_id") or ""),
                ),
            )
            admitted_for_component = 0
            primary_for_component = 0
            immediate_for_component = 0
            for strategy in component_strategies:
                strategy_id = _clean_text(strategy.get("strategy_id"), limit=160)
                candidate_kind = _clean_text(
                    strategy.get("candidate_kind"), limit=40
                ) or "primary"
                raw_query = _clean_text(
                    strategy.get("candidate_query_text"), limit=300
                )
                requested_role = _clean_text(
                    strategy.get("requested_role"), limit=80
                ) or QueryPlanRole.INITIAL.value
                if not strategy_id or not raw_query:
                    raise ValueError(
                        "initial query strategy requires identity and bounded text"
                    )
                try:
                    role = QueryPlanRole(requested_role)
                except ValueError as exc:
                    raise ValueError(
                        f"unsupported initial QueryPlan role: {requested_role}"
                    ) from exc
                authorized = clean(raw_query)[:300]
                compact_strategy = _compact_initial_strategy_metadata(strategy)
                binding = dict(bindings[component_id])
                metadata = {
                    **binding,
                    **compact_strategy,
                    "allocation_policy_version": policy.policy_version,
                    "query_plan_owns_executable_text": True,
                    "provider_selection_unchanged": True,
                }
                plan = plan.append(
                    origin=origin,
                    role=role,
                    status=QueryPlanStatus.OBSERVED_MODEL_QUERY,
                    original_query=authorized or raw_query,
                    phase=phase,
                    metadata=metadata,
                )
                if not authorized:
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_EMPTY,
                        original_query=raw_query,
                        phase=phase,
                        metadata=metadata,
                    )
                    continue

                duplicate = _find_duplicate_initial_candidate(
                    authorized,
                    strategy,
                    canonical_candidates,
                    redundancy_rejection_enabled=(
                        policy.redundancy_rejection_enabled
                    ),
                )
                if duplicate is not None:
                    contributor_ref = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "search_requirement_ref": strategy.get(
                            "search_requirement_ref"
                        ),
                    }
                    plan = _append_contributor_to_item(
                        plan,
                        item_id=str(duplicate["item_id"]),
                        contributor_ref=contributor_ref,
                    )
                    rejection = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "duplicate_of_query_plan_item_id": duplicate["item_id"],
                        "duplicate_kind": duplicate["duplicate_kind"],
                    }
                    duplicates.append(rejection)
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_DUPLICATE,
                        original_query=raw_query,
                        authorized_query=authorized,
                        mutation_reason=str(duplicate["duplicate_kind"]),
                        admission_reason="redundancy_rejected",
                        phase=phase,
                        metadata={**metadata, **rejection},
                    )
                    continue

                if (
                    candidate_kind == "secondary"
                    and not _secondary_candidate_has_distinct_need(strategy)
                ):
                    rejection = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "reason": "secondary_missing_distinct_need_justification",
                    }
                    unjustified_secondary.append(rejection)
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_BLOCKED,
                        original_query=raw_query,
                        authorized_query=authorized,
                        admission_reason="secondary_distinct_need_not_proved",
                        phase=phase,
                        metadata={**metadata, **rejection},
                    )
                    continue

                if (
                    admitted_for_component
                    >= policy.initial_candidate_ceiling_per_required_component
                ):
                    rejection = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "per_component_candidate_ceiling": (
                            policy.initial_candidate_ceiling_per_required_component
                        ),
                    }
                    over_ceiling.append(rejection)
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_OVER_BUDGET,
                        original_query=raw_query,
                        authorized_query=authorized,
                        admission_reason="per_component_candidate_ceiling",
                        phase=phase,
                        metadata={**metadata, **rejection},
                    )
                    continue

                immediate = False
                if candidate_kind == "primary":
                    primary_for_component += 1
                    immediate = (
                        immediate_for_component
                        < policy.immediate_dispatch_target_per_required_component
                    )
                elif (
                    strategy.get("immediate_dispatch_requested") is True
                    and strategy.get("immediate_dispatch_distinct_need") is True
                    and _secondary_need_cannot_reasonably_share_primary(
                        strategy,
                        component_strategies,
                    )
                ):
                    immediate = True

                status = (
                    QueryPlanStatus.FINALIZED
                    if immediate
                    else QueryPlanStatus.ADMITTED
                )
                admission_reason = (
                    "required_component_primary_first_wave"
                    if candidate_kind == "primary" and immediate
                    else "distinct_need_secondary_first_wave"
                    if immediate
                    else "prepared_for_later_search_judgment"
                )
                plan = plan.append(
                    origin=origin,
                    role=role,
                    status=status,
                    original_query=raw_query,
                    authorized_query=authorized,
                    admission_reason=admission_reason,
                    phase=phase,
                    order=admitted_for_component + 1,
                    metadata={
                        **metadata,
                        "candidate_kind": candidate_kind,
                        "dispatch_posture": (
                            "immediate_first_wave"
                            if immediate
                            else "prepared_for_later_search_judgment"
                        ),
                        "post_result_followup_authorized": False,
                        "contributor_lineage": [
                            {
                                "strategy_id": strategy_id,
                                "component_id": component_id,
                                "search_requirement_ref": strategy.get(
                                    "search_requirement_ref"
                                ),
                            }
                        ],
                    },
                )
                item = plan.items[-1]
                canonical_candidates.append(
                    {
                        "query": authorized,
                        "strategy": dict(strategy),
                        "item_id": item.item_id,
                    }
                )
                admitted_for_component += 1
                admitted_candidates.append(authorized)
                query_metadata[authorized] = dict(item.metadata)
                if candidate_kind == "primary":
                    primary_item_ids.setdefault(component_id, []).append(
                        item.item_id
                    )
                if immediate:
                    immediate_for_component += 1
                    if candidate_kind == "primary":
                        immediate_primary.setdefault(component_id, []).append(
                            authorized
                        )
                    else:
                        immediate_secondary.append(authorized)
                elif candidate_kind == "secondary":
                    prepared_secondary.append(
                        {
                            "query_plan_item_id": item.item_id,
                            "strategy_id": strategy_id,
                            "component_id": component_id,
                            "authorized_query": authorized,
                            "requested_role": role.value,
                            "distinct_need_justification": strategy.get(
                                "distinct_need_justification"
                            ),
                            "source_obligation_candidate_ids": list(
                                strategy.get(
                                    "source_obligation_candidate_ids"
                                )
                                or []
                            ),
                            "later_authorizer": "SearchJudgment",
                            "post_result_followup_authorized": False,
                        }
                    )

            if component_id in required_component_ids and (
                policy.required_component_floor_enabled
                and primary_for_component
                < policy.primary_query_target_per_required_component
            ):
                raise ValueError(
                    f"required component {component_id} was not admitted a primary query"
                )

        immediate_queries = tuple(
            query
            for component_id in required_component_ids
            for query in immediate_primary.get(component_id, [])
        ) + tuple(immediate_secondary)
        if policy.required_component_floor_enabled:
            uncovered = [
                component_id
                for component_id in required_component_ids
                if not immediate_primary.get(component_id)
            ]
            if uncovered:
                raise ValueError(
                    "initial first-wave safety floor would omit required components: "
                    + ", ".join(uncovered)
                )

        consumption = {
            "schema_version": "searchos_initial_query_allocation_consumption_v1",
            "search_work_consumed_by_query_plan": True,
            "allocation_policy": policy.to_dict(),
            "required_component_ids": list(required_component_ids),
            "primary_item_ids_by_component": {
                key: list(value) for key, value in primary_item_ids.items()
            },
            "admitted_query_order": list(admitted_candidates),
            "immediate_dispatch_query_order": list(immediate_queries),
            "prepared_secondary_candidates": prepared_secondary,
            "query_metadata": query_metadata,
            "small_global_initial_query_cap_applied": False,
            "required_component_globally_truncated": False,
            "post_result_followup_dispatched": False,
        }
        plan = replace(plan, search_work_consumption=consumption)
        result = InitialQueryAdmissionResult(
            admitted_candidate_queries=tuple(admitted_candidates),
            immediate_dispatch_queries=immediate_queries,
            prepared_secondary_candidates=tuple(prepared_secondary),
            required_component_ids=required_component_ids,
            primary_item_ids_by_component={
                key: tuple(value) for key, value in primary_item_ids.items()
            },
            duplicate_candidates_rejected=tuple(duplicates),
            over_ceiling_candidates_rejected=tuple(over_ceiling),
            unjustified_secondary_candidates_rejected=tuple(
                unjustified_secondary
            ),
        )
        return plan, result

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
            parent_item = None
            if iteration == 1 and role != QueryPlanRole.RECOVERY:
                parent_item = next(
                    (
                        item
                        for item in reversed(plan.items)
                        if item.authorized_query == query
                        and item.status
                        in {QueryPlanStatus.FINALIZED, QueryPlanStatus.ADMITTED}
                        and item.phase == "initial_component_query_admission"
                    ),
                    None,
                )
            execution_role = parent_item.role if parent_item is not None else role
            execution_metadata = (
                {
                    **dict(parent_item.metadata),
                    "parent_initial_query_plan_item_id": parent_item.item_id,
                    "parent_initial_query_plan_item_digest": _canonical_sha256(
                        parent_item.to_dict()
                    ),
                    "exact_query_text_preserved_from_initial_admission": True,
                }
                if parent_item is not None
                else {}
            )
            plan = plan.append(
                origin=origin,
                role=execution_role,
                status=QueryPlanStatus.ORDERED,
                authorized_query=query,
                phase=phase,
                iteration=iteration,
                order=order,
                admission_reason="ordered_for_consumption",
                metadata=execution_metadata,
            )
        return plan

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
    ) -> tuple["QueryPlan", tuple[dict[str, Any], ...]]:
        """Record exact already-authorized dispatch text without rewriting it.

        Recovery and review owners decide whether these queries may run.  This
        method only gives their exact text and order canonical QueryPlan
        identity immediately before the mechanical DISCOVER dispatch.
        """

        plan = self
        appended: list[QueryPlanItem] = []
        for order, value in enumerate(queries, start=1):
            query = str(value)
            if not query.strip():
                raise ValueError(
                    "authorized discovery dispatch cannot record an empty query"
                )
            plan = plan.append(
                origin=origin,
                role=role,
                # Preserve the ordinary iteration view: this is an exact
                # record of already-authorized side work, not newly ordered
                # work for the main search pass.
                status=QueryPlanStatus.FINALIZED,
                authorized_query=query,
                phase=phase,
                iteration=iteration,
                order=order,
                admission_reason=_RECORDED_DISPATCH_ADMISSION_REASON,
                metadata={
                    "authority_source": authority_source,
                    "authority_ref_digest": authority_ref_digest,
                    "query_text_unchanged": True,
                },
            )
            appended.append(plan.items[-1])
        return plan, tuple(item.to_ref(plan.plan_id) for item in appended)

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

    def execution_item_refs(self, iteration: int) -> list[dict[str, str]]:
        """Return ordered refs for the exact queries authorized for one pass."""

        ordered = [
            item
            for item in self.items
            if item.status == QueryPlanStatus.ORDERED
            and item.iteration == iteration
            and item.authorized_query is not None
        ]
        return [
            item.to_ref(self.plan_id)
            for item in sorted(
                ordered,
                key=lambda item: (
                    int(item.order or 0),
                    item.item_id,
                ),
            )
        ]

    def authorized_discovery_item_refs(self) -> list[dict[str, Any]]:
        """Return current QueryPlan members authorized to own DISCOVER results.

        Ordinary ordered execution items carry that authority directly. A
        finalized side-dispatch item carries it only when the existing dispatch
        owner recorded the complete, exact authority markers. Iterating the
        immutable plan value preserves canonical QueryPlan order without
        broadening the narrower per-iteration execution view.
        """

        refs: list[dict[str, Any]] = []
        for item in self.items:
            if (
                not isinstance(item.authorized_query, str)
                or not item.authorized_query.strip()
            ):
                continue
            if item.status == QueryPlanStatus.ORDERED:
                refs.append(item.to_ref(self.plan_id))
                continue
            if item.status != QueryPlanStatus.FINALIZED:
                continue
            metadata = item.metadata
            if (
                item.admission_reason != _RECORDED_DISPATCH_ADMISSION_REASON
                or not isinstance(metadata, Mapping)
                or metadata.get("query_text_unchanged") is not True
                or not _is_bounded_authority_source_token(
                    metadata.get("authority_source")
                )
                or not _is_full_sha256_digest(
                    metadata.get("authority_ref_digest")
                )
            ):
                continue
            refs.append(item.to_ref(self.plan_id))
        return refs

    def to_ref(self) -> dict[str, str]:
        """Return a compact canonical ref to the current immutable plan value."""

        return {
            "query_plan_id": self.plan_id,
            "query_plan_digest": _canonical_sha256(self.to_dict()),
        }

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


def _compact_initial_strategy_metadata(
    strategy: Mapping[str, Any],
) -> dict[str, Any]:
    recon = strategy.get("recon_requirement")
    recon = dict(recon) if isinstance(recon, Mapping) else {}
    return {
        "strategy_id": _clean_text(strategy.get("strategy_id"), limit=160),
        "candidate_kind": _clean_text(
            strategy.get("candidate_kind"), limit=40
        ),
        "requested_role": _clean_text(
            strategy.get("requested_role"), limit=80
        ),
        "source_obligation_candidate_ids": list(
            strategy.get("source_obligation_candidate_ids") or []
        ),
        "search_requirement_ref": _safe_json(
            strategy.get("search_requirement_ref")
        ),
        "accepted_component_ref": _safe_json(
            strategy.get("accepted_component_ref")
        ),
        "parent_search_planner_proposal_ref": _safe_json(
            strategy.get("parent_search_planner_proposal_ref")
        ),
        "parent_search_planner_revision_ref": _safe_json(
            strategy.get("parent_search_planner_revision_ref")
        ),
        "distinct_need_justification": _clean_text(
            strategy.get("distinct_need_justification"), limit=300
        ),
        "currentness_posture": _clean_text(
            strategy.get("currentness_posture"), limit=180
        ),
        "official_canonical_intent": _clean_text(
            strategy.get("official_canonical_intent"), limit=120
        ),
        "domain_constraints": _safe_json(strategy.get("domain_constraints")),
        "document_family": _clean_text(
            strategy.get("document_family"), limit=160
        ),
        "recon_requirement_ref": {
            "posture": _clean_text(
                recon.get("posture") or strategy.get("recon_posture"),
                limit=40,
            ),
            "unresolved_dimension_ids": list(
                recon.get("unresolved_dimension_ids")
                or strategy.get("recon_unresolved_dimension_ids")
                or []
            ),
            "required_for_truthful_targeting": bool(
                recon.get("required_for_truthful_targeting")
                or strategy.get("recon_required_for_truthful_targeting")
            ),
            "recon_query_text_retained": False,
        },
        "planner_provider_identity_ignored": bool(
            strategy.get("planner_provider_identity_ignored")
        ),
        "provider_name_neutral": True,
    }


def _find_duplicate_initial_candidate(
    query: str,
    strategy: Mapping[str, Any],
    canonical_candidates: Sequence[Mapping[str, Any]],
    *,
    redundancy_rejection_enabled: bool,
) -> dict[str, Any] | None:
    for candidate in canonical_candidates:
        existing_query = str(candidate.get("query") or "")
        if query.casefold() == existing_query.casefold():
            return {
                "item_id": candidate.get("item_id"),
                "duplicate_kind": "exact_duplicate",
            }
        if not redundancy_rejection_enabled:
            continue
        existing_strategy = candidate.get("strategy")
        existing_strategy = (
            existing_strategy if isinstance(existing_strategy, Mapping) else {}
        )
        if (
            _queries_materially_equivalent(query, existing_query)
            and not _strategies_prove_distinct_need(strategy, existing_strategy)
        ):
            return {
                "item_id": candidate.get("item_id"),
                "duplicate_kind": "materially_equivalent",
            }
    return None


def _queries_materially_equivalent(left: str, right: str) -> bool:
    left_tokens = set(_query_equivalence_tokens(left))
    right_tokens = set(_query_equivalence_tokens(right))
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union and overlap / union >= 0.86:
        return True
    return (
        min(len(left_tokens), len(right_tokens)) >= 4
        and overlap == min(len(left_tokens), len(right_tokens))
        and abs(len(left_tokens) - len(right_tokens)) <= 1
    )


def _query_equivalence_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in {"a", "an", "and", "for", "of", "the", "to"}
    )


def _strategies_prove_distinct_need(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    left_sources = set(left.get("source_obligation_candidate_ids") or [])
    right_sources = set(right.get("source_obligation_candidate_ids") or [])
    if left_sources != right_sources and (left_sources or right_sources):
        return True
    left_role = _clean_text(left.get("requested_role"), limit=80)
    right_role = _clean_text(right.get("requested_role"), limit=80)
    if left_role != right_role and {left_role, right_role} & {
        QueryPlanRole.OFFICIAL_BIAS.value,
        QueryPlanRole.CANONICAL_BIAS.value,
        QueryPlanRole.RECENCY.value,
        QueryPlanRole.DISAMBIGUATION.value,
        QueryPlanRole.RECON_REWRITE.value,
    }:
        return True
    for key in (
        "currentness_posture",
        "official_canonical_intent",
        "document_family",
    ):
        if left.get(key) != right.get(key) and (left.get(key) or right.get(key)):
            return True
    return False


def _secondary_candidate_has_distinct_need(
    strategy: Mapping[str, Any],
) -> bool:
    justification = _clean_text(
        strategy.get("distinct_need_justification"), limit=300
    )
    if not justification:
        return False
    recon = strategy.get("recon_requirement")
    recon = recon if isinstance(recon, Mapping) else {}
    domain_constraints = strategy.get("domain_constraints")
    domain_constraints = (
        domain_constraints if isinstance(domain_constraints, Mapping) else {}
    )
    return bool(
        strategy.get("source_obligation_candidate_ids")
        or strategy.get("currentness_posture")
        or strategy.get("official_canonical_intent")
        or strategy.get("document_family")
        or domain_constraints.get("include")
        or recon.get("unresolved_dimension_ids")
        or strategy.get("recon_unresolved_dimension_ids")
    )


def _secondary_need_cannot_reasonably_share_primary(
    secondary: Mapping[str, Any],
    component_strategies: Sequence[Mapping[str, Any]],
) -> bool:
    primaries = [
        item
        for item in component_strategies
        if item.get("candidate_kind") == "primary"
    ]
    if not primaries:
        return False
    return all(
        _strategies_prove_distinct_need(secondary, primary)
        for primary in primaries
    )


def _append_contributor_to_item(
    plan: QueryPlan,
    *,
    item_id: str,
    contributor_ref: Mapping[str, Any],
) -> QueryPlan:
    items = list(plan.items)
    for index, item in enumerate(items):
        if item.item_id != item_id:
            continue
        metadata = dict(item.metadata)
        contributors = [
            dict(value)
            for value in metadata.get("contributor_lineage") or []
            if isinstance(value, Mapping)
        ]
        contributors.append(dict(contributor_ref))
        metadata["contributor_lineage"] = contributors
        metadata["duplicate_contributor_count"] = len(contributors) - 1
        items[index] = replace(item, metadata=metadata)
        return replace(plan, items=tuple(items))
    raise ValueError("duplicate contributor target QueryPlan item was not found")


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
