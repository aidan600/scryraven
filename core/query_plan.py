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
from core.query_equivalence import queries_materially_equivalent
from core.retrieval_quality import (
    apply_domain_anchor_to_query,
    approved_entity_aliases,
    format_quoted_anchor,
    official_bias_phrase,
    primary_anchor,
    query_has_domain_anchor,
    wants_official_source_bias,
)

QUERY_PLAN_TRACE_KEY = "query_plan"
_RECORDED_DISPATCH_ADMISSION_REASON = "recorded_from_existing_dispatch_authority"
_AUTHORITY_SOURCE_TOKEN_MAX_LENGTH = 120
_AUTHORITY_SOURCE_TOKEN_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")


class QueryPlanStatus(str, Enum):
    OBSERVED_MODEL_QUERY = "observed_model_query"
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


class DiscoveryJobClass(str, Enum):
    """Provider-neutral DISCOVER intent owned by QueryPlan."""

    ORIENTATION = "orientation"
    STANDARD_DISCOVERY = "standard_discovery"
    DEEP_DISCOVERY = "deep_discovery"


_FACTUAL_ORIENTATION_SLOT_KINDS = frozenset(
    {
        "entity",
        "variant",
        "time_period",
        "source_basis",
        "unknown_or_other",
    }
)
_MATERIAL_UNRESOLVED_SLOT_STATUSES = frozenset({"ambiguous", "unresolved"})


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
        and all(character in _AUTHORITY_SOURCE_TOKEN_CHARACTERS for character in value)
    )


def _is_full_sha256_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


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
    discovery_job_class: DiscoveryJobClass | str | None = None
    component_ref: Mapping[str, Any] = field(default_factory=dict)
    semantic_slot_refs: tuple[Mapping[str, Any], ...] = ()
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
        if self.discovery_job_class is not None:
            try:
                job_class = DiscoveryJobClass(self.discovery_job_class)
            except ValueError as exc:
                raise ValueError(
                    f"unknown discovery job class: {self.discovery_job_class}"
                ) from exc
            if not _clean_text(self.component_ref.get("component_id"), limit=160):
                raise ValueError("discovery job requires exact component lineage")
            slot_ids = [
                _clean_text(item.get("slot_id"), limit=160)
                for item in self.semantic_slot_refs
                if isinstance(item, Mapping)
            ]
            if (
                not slot_ids
                or any(slot_id is None for slot_id in slot_ids)
                or len(slot_ids) != len(self.semantic_slot_refs)
                or len(set(slot_ids)) != len(slot_ids)
            ):
                raise ValueError(
                    "discovery job requires unique plural semantic-slot lineage"
                )
            object.__setattr__(self, "discovery_job_class", job_class)
        object.__setattr__(
            self,
            "semantic_slot_refs",
            tuple(dict(item) for item in self.semantic_slot_refs),
        )

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
            "discovery_job_class": (
                self.discovery_job_class.value
                if isinstance(self.discovery_job_class, DiscoveryJobClass)
                else self.discovery_job_class
            ),
            "component_ref": _safe_json(self.component_ref),
            "semantic_slot_refs": _safe_json(self.semantic_slot_refs),
            "metadata": _safe_json(self.metadata),
        }
        return {key: value for key, value in payload.items() if value not in (None, {}, [])}

    def to_ref(self, plan_id: str) -> dict[str, Any]:
        """Return the canonical execution lineage ref for this exact plan item."""

        canonical_plan_id = _clean_text(plan_id, limit=120)
        if canonical_plan_id is None:
            raise ValueError("query plan item ref requires plan_id")
        authorized_query = self.authorized_query
        if authorized_query is None:
            raise ValueError("query plan item ref requires an authorized query")
        ref: dict[str, Any] = {
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
        if self.discovery_job_class is not None:
            ref["discovery_job_class"] = self.discovery_job_class.value
            ref["component_ref"] = _safe_json(self.component_ref)
            ref["semantic_slot_refs"] = _safe_json(self.semantic_slot_refs)
        return ref


@dataclass(frozen=True, slots=True)
class InitialQueryAdmissionResult:
    admitted_candidate_queries: tuple[str, ...]
    immediate_dispatch_queries: tuple[str, ...]
    prepared_secondary_candidates: tuple[Mapping[str, Any], ...]
    required_component_ids: tuple[str, ...]
    dispatch_required_component_ids: tuple[str, ...]
    primary_item_ids_by_component: Mapping[str, tuple[str, ...]]
    discovery_job_classes_by_component: Mapping[str, str]
    semantic_slot_refs_by_component: Mapping[
        str, tuple[Mapping[str, Any], ...]
    ]
    clarification_required_semantic_slots: tuple[Mapping[str, Any], ...] = ()
    duplicate_candidates_rejected: tuple[Mapping[str, Any], ...] = ()
    over_ceiling_candidates_rejected: tuple[Mapping[str, Any], ...] = ()
    unjustified_secondary_candidates_rejected: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted_candidate_queries": list(self.admitted_candidate_queries),
            "immediate_dispatch_queries": list(self.immediate_dispatch_queries),
            "prepared_secondary_candidates": [dict(item) for item in self.prepared_secondary_candidates],
            "required_component_ids": list(self.required_component_ids),
            "dispatch_required_component_ids": list(
                self.dispatch_required_component_ids
            ),
            "primary_item_ids_by_component": {
                component_id: list(item_ids) for component_id, item_ids in self.primary_item_ids_by_component.items()
            },
            "discovery_job_classes_by_component": dict(
                self.discovery_job_classes_by_component
            ),
            "semantic_slot_refs_by_component": {
                component_id: [dict(slot_ref) for slot_ref in slot_refs]
                for component_id, slot_refs in self.semantic_slot_refs_by_component.items()
            },
            "clarification_required_semantic_slots": [
                dict(item)
                for item in self.clarification_required_semantic_slots
            ],
            "duplicate_candidates_rejected": [dict(item) for item in self.duplicate_candidates_rejected],
            "over_ceiling_candidates_rejected": [dict(item) for item in self.over_ceiling_candidates_rejected],
            "unjustified_secondary_candidates_rejected": [
                dict(item) for item in self.unjustified_secondary_candidates_rejected
            ],
            "post_result_followup_dispatched": False,
        }


def _canonical_component_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _clean_text(component.get("component_id"), limit=160)
    revision = _clean_text(component.get("component_revision"), limit=160)
    digest = _clean_text(component.get("component_digest"), limit=128)
    if not component_id or not revision or not digest:
        raise ValueError(
            "QueryPlan job derivation requires accepted component identity"
        )
    return {
        "component_id": component_id,
        "component_revision": revision,
        "component_digest": digest,
        "component_purpose": _clean_text(
            component.get("component_purpose"), limit=120
        ),
        "requirement_posture": _clean_text(
            component.get("requirement_posture"), limit=80
        ),
        "materiality": _clean_text(component.get("materiality"), limit=80),
        "semantic_slot_ids": [
            str(value) for value in component.get("semantic_slot_ids") or ()
        ],
        "source_obligation_candidate_ids": [
            str(value)
            for value in component.get("source_obligation_candidate_ids") or ()
        ],
        "dependency_component_ids": [
            str(value)
            for value in component.get("dependency_component_ids") or ()
        ],
    }


def _canonical_semantic_slot_ref(slot: Mapping[str, Any]) -> dict[str, Any]:
    slot_id = _clean_text(slot.get("slot_id"), limit=160)
    slot_kind = _clean_text(slot.get("slot_kind"), limit=80)
    status = _clean_text(slot.get("status"), limit=80)
    if not slot_id or not slot_kind or not status:
        raise ValueError(
            "QueryPlan job derivation requires accepted semantic-slot identity"
        )
    return {
        "slot_id": slot_id,
        "slot_kind": slot_kind,
        "status": status,
        "materiality": _clean_text(slot.get("materiality"), limit=80),
        "candidate_values": [
            str(value) for value in slot.get("candidate_values") or ()
        ],
        "selected_value": _clean_text(slot.get("selected_value"), limit=220),
        "user_confirmation_required": bool(
            slot.get("user_confirmation_required", False)
        ),
        "unresolved_material": bool(slot.get("unresolved_material", False)),
    }


def initial_component_bindings_from_accepted_contract(
    accepted_contract: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return compact component bindings owned by the accepted AnswerContract."""

    if not isinstance(accepted_contract, Mapping):
        raise ValueError("initial QueryPlan admission requires an accepted contract")
    components = [
        dict(item)
        for item in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping) and str(item.get("component_id") or "").strip()
    ]
    if not components:
        raise ValueError("initial QueryPlan admission requires accepted components")
    contract_ref = {
        "contract_version": str(
            accepted_contract.get("accepted_contract_version") or ""
        ).strip(),
        "contract_digest": str(
            accepted_contract.get("accepted_contract_digest") or ""
        ).strip(),
    }
    if not contract_ref["contract_version"] or not contract_ref["contract_digest"]:
        raise ValueError(
            "initial QueryPlan admission requires accepted contract identity"
        )
    bindings: dict[str, dict[str, Any]] = {}
    for rank, component in enumerate(components, start=1):
        component_id = str(component.get("component_id") or "").strip()
        accepted_component_ref = {
            "component_id": component_id,
            "component_revision": component.get("component_revision"),
            "component_digest": component.get("component_digest"),
            "requirement_posture": component.get("requirement_posture"),
            "semantic_slot_ids": list(component.get("semantic_slot_ids") or []),
        }
        bindings[component_id] = {
            "component_rank": rank,
            "accepted_component_ref": accepted_component_ref,
            "source_obligation_candidate_ids": list(
                component.get("source_obligation_candidate_ids")
                or component.get("source_obligation_candidate_refs")
                or []
            ),
            "required_component": (
                str(component.get("requirement_posture") or "") == "required"
            ),
            "accepted_contract_ref": dict(contract_ref),
        }
    return bindings


def derive_initial_component_discovery_postures(
    accepted_contract: Mapping[str, Any],
    *,
    component_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """Derive initial job/clarification posture solely from accepted semantics."""

    if not isinstance(accepted_contract, Mapping):
        raise ValueError("QueryPlan job derivation requires an accepted contract")
    components = {
        str(item.get("component_id")): item
        for item in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping) and item.get("component_id")
    }
    slots = {
        str(item.get("slot_id")): item
        for item in accepted_contract.get("accepted_semantic_slot_refs") or ()
        if isinstance(item, Mapping) and item.get("slot_id")
    }
    postures: dict[str, dict[str, Any]] = {}
    for component_id in component_ids:
        component = components.get(str(component_id))
        if component is None:
            raise ValueError(
                "accepted component is absent from the accepted AnswerContract"
            )
        component_ref = _canonical_component_ref(component)
        declared_slot_ids = list(component_ref["semantic_slot_ids"])
        component_slots = [
            slots[slot_id]
            for slot_id in declared_slot_ids
            if slot_id in slots
        ]
        if (
            not component_slots
            or len(component_slots) != len(declared_slot_ids)
            or len(set(declared_slot_ids)) != len(declared_slot_ids)
        ):
            raise ValueError(
                f"accepted component {component_id} has incomplete or duplicate semantic-slot lineage"
            )

        def is_materially_unresolved(slot: Mapping[str, Any]) -> bool:
            return bool(slot.get("unresolved_material")) or (
                str(slot.get("status") or "")
                in _MATERIAL_UNRESOLVED_SLOT_STATUSES
                and str(slot.get("materiality") or "material") == "material"
            )

        semantic_slot_refs = [
            _canonical_semantic_slot_ref(slot) for slot in component_slots
        ]
        clarification_semantic_slot_refs = [
            _canonical_semantic_slot_ref(slot)
            for slot in component_slots
            if is_materially_unresolved(slot)
            and slot.get("user_confirmation_required") is True
        ]
        orientation_semantic_slot_refs = [
            _canonical_semantic_slot_ref(slot)
            for slot in component_slots
            if is_materially_unresolved(slot)
            and str(slot.get("slot_kind") or "")
            in _FACTUAL_ORIENTATION_SLOT_KINDS
            and slot.get("user_confirmation_required") is not True
        ]
        inferred_only = {
            str(item)
            for item in component.get("allowed_support_kinds") or ()
        } == {"inferred"}
        if inferred_only:
            discovery_semantic_slot_refs = []
            job_class: DiscoveryJobClass | None = None
            posture_name = "inference_pending"
        elif orientation_semantic_slot_refs:
            discovery_semantic_slot_refs = orientation_semantic_slot_refs
            job_class = DiscoveryJobClass.ORIENTATION
            posture_name = "discovery_ready"
        elif clarification_semantic_slot_refs:
            discovery_semantic_slot_refs = []
            job_class = None
            posture_name = "clarification_required"
        else:
            discovery_semantic_slot_refs = semantic_slot_refs
            job_class = DiscoveryJobClass.STANDARD_DISCOVERY
            posture_name = "discovery_ready"
        postures[str(component_id)] = {
            "posture": posture_name,
            "component_ref": component_ref,
            "semantic_slot_refs": semantic_slot_refs,
            "discovery_semantic_slot_refs": (
                discovery_semantic_slot_refs
            ),
            "clarification_semantic_slot_refs": (
                clarification_semantic_slot_refs
            ),
            "discovery_job_class": (
                job_class.value if job_class is not None else None
            ),
        }
    return postures


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
        discovery_job_class: DiscoveryJobClass | str | None = None,
        component_ref: Mapping[str, Any] | None = None,
        semantic_slot_refs: Sequence[Mapping[str, Any]] = (),
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
            discovery_job_class=discovery_job_class,
            component_ref=dict(component_ref or {}),
            semantic_slot_refs=tuple(
                dict(item) for item in semantic_slot_refs
            ),
            metadata=dict(metadata or {}),
        )
        return replace(self, items=self.items + (item,))

    def admit_initial_component_strategies(
        self,
        strategies: Sequence[Mapping[str, Any]],
        *,
        accepted_contract: Mapping[str, Any],
        policy: InitialQueryAllocationPolicy,
        clean: Callable[[str], str],
        origin: str = "search_planner",
        phase: str = "initial_component_query_admission",
    ) -> tuple["QueryPlan", InitialQueryAdmissionResult]:
        """Admit component-bound initial candidates without a small global cap."""

        bindings = initial_component_bindings_from_accepted_contract(
            accepted_contract
        )
        required_component_ids = tuple(
            component_id for component_id, binding in bindings.items() if binding.get("required_component") is True
        )
        if not required_component_ids:
            raise ValueError("initial QueryPlan admission requires accepted required components")
        component_postures = derive_initial_component_discovery_postures(
            accepted_contract,
            component_ids=tuple(bindings),
        )
        dispatch_required_component_ids = tuple(
            component_id
            for component_id in required_component_ids
            if component_postures[component_id]["posture"] == "discovery_ready"
        )
        grouped: dict[str, list[Mapping[str, Any]]] = {component_id: [] for component_id in bindings}
        for strategy in strategies:
            component_id = _clean_text(strategy.get("component_id"), limit=160)
            if not component_id or component_id not in bindings:
                raise ValueError("initial query strategy references an unknown accepted component")
            grouped[component_id].append(strategy)

        plan = self
        admitted_candidates: list[str] = []
        immediate_primary: dict[str, list[str]] = {
            component_id: [] for component_id in dispatch_required_component_ids
        }
        immediate_secondary: list[str] = []
        prepared_secondary: list[dict[str, Any]] = []
        primary_item_ids: dict[str, list[str]] = {
            component_id: [] for component_id in dispatch_required_component_ids
        }
        duplicates: list[dict[str, Any]] = []
        over_ceiling: list[dict[str, Any]] = []
        unjustified_secondary: list[dict[str, Any]] = []
        canonical_candidates: list[dict[str, Any]] = []
        query_metadata: dict[str, dict[str, Any]] = {}
        clarification_required_semantic_slots: list[dict[str, Any]] = []

        for component_id in bindings:
            posture = component_postures[component_id]
            component_ref = dict(posture["component_ref"])
            semantic_slot_refs = tuple(
                dict(item) for item in posture["semantic_slot_refs"]
            )
            discovery_semantic_slot_refs = tuple(
                dict(item)
                for item in posture["discovery_semantic_slot_refs"]
            )
            clarification_semantic_slot_refs = tuple(
                dict(item)
                for item in posture["clarification_semantic_slot_refs"]
            )
            discovery_job_class = posture.get("discovery_job_class")
            component_clarifications = [
                {
                    "component_ref": component_ref,
                    "semantic_slot_ref": semantic_slot_ref,
                    "clarification_required": True,
                    "declared_candidates": list(
                        semantic_slot_ref.get("candidate_values") or ()
                    ),
                    "reason": (
                        "accepted_semantic_slot_requires_user_confirmation"
                    ),
                }
                for semantic_slot_ref in clarification_semantic_slot_refs
            ]
            clarification_required_semantic_slots.extend(
                component_clarifications
            )
            if posture["posture"] == "clarification_required":
                for strategy in grouped.get(component_id, []):
                    raw_query = _clean_text(
                        strategy.get("candidate_query_text"), limit=300
                    )
                    role_value = (
                        _clean_text(strategy.get("requested_role"), limit=80)
                        or QueryPlanRole.INITIAL.value
                    )
                    try:
                        role = QueryPlanRole(role_value)
                    except ValueError as exc:
                        raise ValueError(
                            f"unsupported initial QueryPlan role: {role_value}"
                        ) from exc
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.OBSERVED_MODEL_QUERY,
                        original_query=raw_query,
                        phase=phase,
                        component_ref=component_ref,
                        semantic_slot_refs=semantic_slot_refs,
                        metadata=_compact_initial_strategy_metadata(strategy),
                    )
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_BLOCKED,
                        original_query=raw_query,
                        admission_reason="semantic_slot_requires_user_clarification",
                        phase=phase,
                        component_ref=component_ref,
                        semantic_slot_refs=semantic_slot_refs,
                        metadata={
                            **_compact_initial_strategy_metadata(strategy),
                            "clarification_required_semantic_slots": (
                                component_clarifications
                            ),
                            "provider_dispatch_authorized": False,
                        },
                    )
                continue
            if posture["posture"] == "inference_pending":
                continue
            component_strategies = sorted(
                grouped.get(component_id, []),
                # Stable partition: primaries precede secondaries while the
                # planner/revision proposal order remains exact within each
                # class.  Strategy identifiers never become an order policy.
                key=lambda item: 0 if item.get("candidate_kind") == "primary" else 1,
            )
            admitted_for_component = 0
            primary_for_component = 0
            immediate_for_component = 0
            for strategy in component_strategies:
                strategy_id = _clean_text(strategy.get("strategy_id"), limit=160)
                candidate_kind = _clean_text(strategy.get("candidate_kind"), limit=40) or "primary"
                if candidate_kind not in {"primary", "secondary"}:
                    raise ValueError("initial query strategy candidate_kind must be primary or secondary")
                raw_query = _clean_text(strategy.get("candidate_query_text"), limit=300)
                requested_role = _clean_text(strategy.get("requested_role"), limit=80) or QueryPlanRole.INITIAL.value
                if not strategy_id or not raw_query:
                    raise ValueError("initial query strategy requires identity and bounded text")
                try:
                    role = QueryPlanRole(requested_role)
                except ValueError as exc:
                    raise ValueError(f"unsupported initial QueryPlan role: {requested_role}") from exc
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
                    discovery_job_class=discovery_job_class,
                    component_ref=component_ref,
                    semantic_slot_refs=discovery_semantic_slot_refs,
                    metadata=metadata,
                )
                if not authorized:
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_EMPTY,
                        original_query=raw_query,
                        phase=phase,
                        discovery_job_class=discovery_job_class,
                        component_ref=component_ref,
                        semantic_slot_refs=discovery_semantic_slot_refs,
                        metadata=metadata,
                    )
                    continue

                duplicate = _find_duplicate_initial_candidate(
                    authorized,
                    strategy,
                    canonical_candidates,
                    redundancy_rejection_enabled=(policy.redundancy_rejection_enabled),
                )
                if duplicate is not None:
                    contributor_ref = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "search_requirement_ref": strategy.get("search_requirement_ref"),
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
                        discovery_job_class=discovery_job_class,
                        component_ref=component_ref,
                        semantic_slot_refs=discovery_semantic_slot_refs,
                        metadata={**metadata, **rejection},
                    )
                    continue

                additional_candidate = admitted_for_component > 0
                if (
                    candidate_kind == "secondary" or additional_candidate
                ) and not _secondary_candidate_has_distinct_need(strategy):
                    rejection = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "reason": "additional_candidate_missing_distinct_need_justification",
                    }
                    unjustified_secondary.append(rejection)
                    plan = plan.append(
                        origin=origin,
                        role=role,
                        status=QueryPlanStatus.REJECTED_BLOCKED,
                        original_query=raw_query,
                        authorized_query=authorized,
                        admission_reason="additional_distinct_need_not_proved",
                        phase=phase,
                        discovery_job_class=discovery_job_class,
                        component_ref=component_ref,
                        semantic_slot_refs=discovery_semantic_slot_refs,
                        metadata={**metadata, **rejection},
                    )
                    continue

                if admitted_for_component >= policy.initial_candidate_ceiling_per_required_component:
                    rejection = {
                        "strategy_id": strategy_id,
                        "component_id": component_id,
                        "per_component_candidate_ceiling": (policy.initial_candidate_ceiling_per_required_component),
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
                        discovery_job_class=discovery_job_class,
                        component_ref=component_ref,
                        semantic_slot_refs=discovery_semantic_slot_refs,
                        metadata={**metadata, **rejection},
                    )
                    continue

                immediate = False
                if candidate_kind == "primary":
                    primary_for_component += 1
                    immediate = (
                        not additional_candidate
                        and immediate_for_component < policy.immediate_dispatch_target_per_required_component
                    )
                if additional_candidate and (
                    strategy.get("immediate_dispatch_requested") is True
                    and strategy.get("immediate_dispatch_distinct_need") is True
                    and _secondary_need_cannot_reasonably_share_primary(
                        strategy,
                        component_strategies,
                    )
                ):
                    immediate = True

                status = QueryPlanStatus.FINALIZED if immediate else QueryPlanStatus.ADMITTED
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
                    discovery_job_class=discovery_job_class,
                    component_ref=component_ref,
                    semantic_slot_refs=discovery_semantic_slot_refs,
                    metadata={
                        **metadata,
                        "candidate_kind": candidate_kind,
                        "dispatch_posture": (
                            "immediate_first_wave" if immediate else "prepared_for_later_search_judgment"
                        ),
                        "post_result_followup_authorized": False,
                        "contributor_lineage": [
                            {
                                "strategy_id": strategy_id,
                                "component_id": component_id,
                                "search_requirement_ref": strategy.get("search_requirement_ref"),
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
                query_metadata[authorized] = {
                    **dict(item.metadata),
                    "accepted_component_id": component_id,
                }
                if candidate_kind == "primary":
                    primary_item_ids.setdefault(component_id, []).append(item.item_id)
                if immediate:
                    immediate_for_component += 1
                    if candidate_kind == "primary":
                        immediate_primary.setdefault(component_id, []).append(authorized)
                    else:
                        immediate_secondary.append(authorized)
                elif candidate_kind == "secondary" or additional_candidate:
                    prepared_secondary.append(
                        {
                            "query_plan_item_id": item.item_id,
                            "strategy_id": strategy_id,
                            "component_id": component_id,
                            "authorized_query": authorized,
                            "requested_role": role.value,
                            "candidate_kind": candidate_kind,
                            "distinct_need_justification": strategy.get("distinct_need_justification"),
                            "source_obligation_candidate_ids": list(
                                strategy.get("source_obligation_candidate_ids") or []
                            ),
                            "later_authorizer": "SearchJudgment",
                            "post_result_followup_authorized": False,
                        }
                    )

            if component_id in dispatch_required_component_ids and (
                policy.required_component_floor_enabled
                and primary_for_component < policy.primary_query_target_per_required_component
            ):
                raise ValueError(f"required component {component_id} was not admitted a primary query")

        immediate_queries = tuple(
            query
            for component_id in dispatch_required_component_ids
            for query in immediate_primary.get(component_id, [])
        ) + tuple(immediate_secondary)
        if policy.required_component_floor_enabled:
            uncovered = [
                component_id
                for component_id in dispatch_required_component_ids
                if not immediate_primary.get(component_id)
            ]
            if uncovered:
                raise ValueError(
                    "initial first-wave safety floor would omit required components: " + ", ".join(uncovered)
                )

        consumption = {
            "schema_version": "searchos_initial_query_allocation_consumption_v1",
            "allocation_policy": policy.to_dict(),
            "required_component_ids": list(required_component_ids),
            "dispatch_required_component_ids": list(
                dispatch_required_component_ids
            ),
            "discovery_job_classes_by_component": {
                component_id: posture["discovery_job_class"]
                for component_id, posture in component_postures.items()
                if posture.get("discovery_job_class")
            },
            "semantic_slot_refs_by_component": {
                component_id: [
                    dict(item) for item in posture["semantic_slot_refs"]
                ]
                for component_id, posture in component_postures.items()
            },
            "clarification_required_semantic_slots": (
                clarification_required_semantic_slots
            ),
            "primary_item_ids_by_component": {key: list(value) for key, value in primary_item_ids.items()},
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
            dispatch_required_component_ids=dispatch_required_component_ids,
            primary_item_ids_by_component={key: tuple(value) for key, value in primary_item_ids.items()},
            discovery_job_classes_by_component={
                component_id: str(posture["discovery_job_class"])
                for component_id, posture in component_postures.items()
                if posture.get("discovery_job_class")
            },
            semantic_slot_refs_by_component={
                component_id: tuple(
                    dict(item) for item in posture["semantic_slot_refs"]
                )
                for component_id, posture in component_postures.items()
            },
            clarification_required_semantic_slots=tuple(
                clarification_required_semantic_slots
            ),
            duplicate_candidates_rejected=tuple(duplicates),
            over_ceiling_candidates_rejected=tuple(over_ceiling),
            unjustified_secondary_candidates_rejected=tuple(unjustified_secondary),
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
                        and item.status in {QueryPlanStatus.FINALIZED, QueryPlanStatus.ADMITTED}
                        and item.phase == "initial_component_query_admission"
                    ),
                    None,
                )
            execution_role = parent_item.role if parent_item is not None else role
            execution_metadata = (
                {
                    **dict(parent_item.metadata),
                    "parent_initial_query_plan_item_id": parent_item.item_id,
                    "parent_initial_query_plan_item_digest": _canonical_sha256(parent_item.to_dict()),
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
                discovery_job_class=(
                    parent_item.discovery_job_class
                    if parent_item is not None
                    else None
                ),
                component_ref=(
                    parent_item.component_ref if parent_item is not None else None
                ),
                semantic_slot_refs=(
                    parent_item.semantic_slot_refs
                    if parent_item is not None
                    else ()
                ),
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
                raise ValueError("authorized discovery dispatch cannot record an empty query")
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

    def admit_searchos_followup_query(
        self,
        *,
        judgment_decision: Mapping[str, Any],
        iteration: int,
    ) -> tuple["QueryPlan", dict[str, Any]]:
        """Append one exact model-authored SearchOS follow-up DISCOVER query.

        SearchJudgment owns the nomination; QueryPlan remains the sole owner of
        executable query text and append-only query identity.  This method does
        not clean, rewrite, expand, or otherwise substitute the admitted text.
        """

        from core.searchos_iterative_judgment_runtime import (
            SearchOSJudgmentAction,
            SearchOSRuntimeError,
        )

        decision = dict(judgment_decision) if isinstance(judgment_decision, Mapping) else {}
        if decision.get("action") != SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY.value:
            raise ValueError("SearchOS QueryPlan admission requires a follow-up decision")
        query = decision.get("followup_query")
        if not isinstance(query, str) or not query.strip() or len(query) > 300:
            raise ValueError("SearchOS follow-up query must be exact bounded text")
        if query != query.strip():
            raise ValueError("SearchOS follow-up query cannot be rewritten at admission")
        try:
            discovery_job_class = DiscoveryJobClass(
                decision.get("discovery_job_class")
            )
        except (TypeError, ValueError) as exc:
            raise SearchOSRuntimeError(
                "SearchOS follow-up query requires a provider-neutral discovery job class"
            ) from exc
        if any(
            queries_materially_equivalent(
                str(item.authorized_query or ""),
                query,
            )
            for item in self.items
            if item.authorized_query
        ):
            raise SearchOSRuntimeError(
                "SearchOS follow-up query is materially equivalent to existing QueryPlan text"
            )
        iteration_ordinal = int(iteration)
        if iteration_ordinal < 2:
            raise ValueError("SearchOS follow-up query requires iteration >= 2")
        decision_id = _clean_text(decision.get("judgment_decision_id"), limit=260)
        decision_digest = _clean_text(
            decision.get("judgment_decision_digest"), limit=128
        )
        slot_ref = decision.get("slot_ref")
        if (
            not decision_id
            or not _is_full_sha256_digest(decision_digest)
            or not isinstance(slot_ref, Mapping)
            or not _clean_text(slot_ref.get("slot_id"), limit=260)
        ):
            raise SearchOSRuntimeError(
                "SearchOS follow-up decision lacks exact judgment/slot lineage"
            )
        component_ref = slot_ref.get("component_ref")
        semantic_slot_refs = decision.get("semantic_slot_refs")
        if not isinstance(component_ref, Mapping) or not isinstance(
            semantic_slot_refs, Sequence
        ) or isinstance(
            semantic_slot_refs, (str, bytes)
        ) or not all(
            isinstance(item, Mapping) for item in semantic_slot_refs
        ):
            raise SearchOSRuntimeError(
                "SearchOS follow-up decision lacks exact plural semantic-slot lineage"
            )
        parent_plan_ref = self.to_ref()
        plan = self.append(
            origin="searchos_iterative_judgment",
            role=QueryPlanRole.FINALIZED,
            status=QueryPlanStatus.ORDERED,
            original_query=query,
            authorized_query=query,
            mutation_reason=None,
            admission_reason="searchos_exact_model_followup_query",
            phase="searchos_followup_discover",
            iteration=iteration_ordinal,
            order=1,
            discovery_job_class=discovery_job_class,
            component_ref=component_ref,
            semantic_slot_refs=semantic_slot_refs,
            metadata={
                "searchos_judgment_decision_id": decision_id,
                "searchos_judgment_decision_digest": decision_digest,
                "searchos_slot_ref": dict(slot_ref),
                "parent_query_plan_ref": parent_plan_ref,
                "query_text_unchanged": True,
                "evaluator_authority_used": False,
                "expander_authority_used": False,
            },
        )
        item_ref = plan.items[-1].to_ref(plan.plan_id)
        projection = {
            "schema_version": "searchos_followup_query_admission_v1",
            "owner": "QueryPlan",
            "parent_query_plan_ref": parent_plan_ref,
            "current_query_plan_ref": plan.to_ref(),
            "query_plan_item_ref": item_ref,
            "judgment_decision_ref": {
                "judgment_decision_id": decision_id,
                "judgment_decision_digest": decision_digest,
            },
            "slot_ref": dict(slot_ref),
            "discovery_job_class": discovery_job_class.value,
            "exact_query_text_preserved": True,
            "append_only": True,
            "provider_selection_unchanged": True,
            "provider_depth_unchanged": True,
        }
        return plan, projection

    def queries_by_iteration(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        ordered = [
            item
            for item in self.items
            if item.status == QueryPlanStatus.ORDERED and item.iteration is not None and item.authorized_query
        ]
        for item in sorted(ordered, key=lambda x: (int(x.iteration or 0), int(x.order or 0), x.item_id)):
            out.setdefault(int(item.iteration or 0), []).append(str(item.authorized_query))
        return out

    def execution_item_refs(
        self,
        iteration: int,
        *,
        discovery_job_class: DiscoveryJobClass | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return ordered refs for the exact queries authorized for one pass."""

        selected_job_class = (
            DiscoveryJobClass(discovery_job_class)
            if discovery_job_class is not None
            else None
        )
        ordered = [
            item
            for item in self.items
            if item.status == QueryPlanStatus.ORDERED
            and item.iteration == iteration
            and item.authorized_query is not None
            and (
                selected_job_class is None
                or item.discovery_job_class == selected_job_class
                or (
                    selected_job_class
                    is DiscoveryJobClass.STANDARD_DISCOVERY
                    and item.discovery_job_class is None
                )
            )
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

    def execution_job_batches(self, iteration: int) -> tuple[dict[str, Any], ...]:
        """Project one ordered pass subset per provider-neutral job class."""

        ordered_items = [
            item
            for item in sorted(
                self.items,
                key=lambda item: (int(item.order or 0), item.item_id),
            )
            if item.status == QueryPlanStatus.ORDERED
            and item.iteration == iteration
            and item.authorized_query is not None
        ]
        ordered_job_classes: list[DiscoveryJobClass] = []
        for item in ordered_items:
            job_class = (
                item.discovery_job_class
                or DiscoveryJobClass.STANDARD_DISCOVERY
            )
            if job_class not in ordered_job_classes:
                ordered_job_classes.append(job_class)
        batches: list[dict[str, Any]] = []
        for job_class in ordered_job_classes:
            item_refs = self.execution_item_refs(
                iteration,
                discovery_job_class=job_class,
            )
            if not item_refs:
                continue
            batches.append(
                {
                    "discovery_job_class": job_class.value,
                    "query_plan_item_refs": item_refs,
                    "queries": [
                        str(item_ref["authorized_query"])
                        for item_ref in item_refs
                    ],
                }
            )
        return tuple(batches)

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
            if not isinstance(item.authorized_query, str) or not item.authorized_query.strip():
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
                or not _is_bounded_authority_source_token(metadata.get("authority_source"))
                or not _is_full_sha256_digest(metadata.get("authority_ref_digest"))
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
            "authorized_queries_by_iteration": {str(key): value for key, value in self.queries_by_iteration().items()},
            "provider_policy": QueryPlanStatus.PROVIDER_POLICY_UNCHANGED.value,
            "depth_policy": QueryPlanStatus.DEPTH_POLICY_UNCHANGED.value,
            "custody_satisfaction_owner": "official_current_source_custody",
        }
        if self.search_work_consumption:
            payload["search_work_consumption"] = _safe_json(self.search_work_consumption)
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {QUERY_PLAN_TRACE_KEY: self.to_dict()}


def _compact_initial_strategy_metadata(
    strategy: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "strategy_id": _clean_text(strategy.get("strategy_id"), limit=160),
        "candidate_kind": _clean_text(strategy.get("candidate_kind"), limit=40),
        "requested_role": _clean_text(strategy.get("requested_role"), limit=80),
        "source_obligation_candidate_ids": list(strategy.get("source_obligation_candidate_ids") or []),
        "search_requirement_ref": _safe_json(strategy.get("search_requirement_ref")),
        "accepted_component_ref": _safe_json(strategy.get("accepted_component_ref")),
        "parent_search_planner_proposal_ref": _safe_json(strategy.get("parent_search_planner_proposal_ref")),
        "distinct_need_justification": _clean_text(strategy.get("distinct_need_justification"), limit=300),
        "currentness_posture": _clean_text(strategy.get("currentness_posture"), limit=180),
        "official_canonical_intent": _clean_text(strategy.get("official_canonical_intent"), limit=120),
        "domain_constraints": _safe_json(strategy.get("domain_constraints")),
        "document_family": _clean_text(strategy.get("document_family"), limit=160),
        "planner_provider_identity_ignored": bool(strategy.get("planner_provider_identity_ignored")),
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
        existing_strategy = existing_strategy if isinstance(existing_strategy, Mapping) else {}
        if _queries_materially_equivalent(query, existing_query) and not _strategies_prove_distinct_need(
            strategy, existing_strategy
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
    justification = _clean_text(strategy.get("distinct_need_justification"), limit=300)
    if not justification:
        return False
    domain_constraints = strategy.get("domain_constraints")
    domain_constraints = domain_constraints if isinstance(domain_constraints, Mapping) else {}
    return bool(
        strategy.get("source_obligation_candidate_ids")
        or strategy.get("currentness_posture")
        or strategy.get("official_canonical_intent")
        or strategy.get("document_family")
        or domain_constraints.get("include")
    )


def _secondary_need_cannot_reasonably_share_primary(
    secondary: Mapping[str, Any],
    component_strategies: Sequence[Mapping[str, Any]],
) -> bool:
    primaries = [
        item
        for item in component_strategies
        if item.get("candidate_kind") == "primary" and item.get("strategy_id") != secondary.get("strategy_id")
    ]
    if not primaries:
        return False
    return all(_strategies_prove_distinct_need(secondary, primary) for primary in primaries)


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
            dict(value) for value in metadata.get("contributor_lineage") or [] if isinstance(value, Mapping)
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
            "official" in query.lower() and query_has_domain_anchor(query, aliases) for query in candidate_queries
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
