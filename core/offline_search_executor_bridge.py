"""Offline SearchExecutor-shaped bridge observations for product-path scaffolding.

The bridge consumes already-safe AnswerContractAuthorityMap and subordinate
ComponentSearchPlan/SearchWork/QueryPlan projections. It emits sanitized,
per-component execution observations only; it never calls live providers,
fetch/read, retrieval, EvidenceLedger admission, citation rendering, or Author
execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

OFFLINE_SEARCH_EXECUTOR_BRIDGE_SCHEMA_VERSION = (
    "offline_search_executor_bridge_ag_search_executor_01_v1"
)
OFFLINE_SEARCH_EXECUTOR_BRIDGE_TRACE_KEY = "offline_search_executor_bridge"
OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER = "RunKernel.OfflineSearchExecutorBridge"
OFFLINE_SEARCH_EXECUTOR_BRIDGE_PROOF_CLASS = "offline_product_path_projection_proof"

_BOUNDARY_FALSE_FLAGS = {
    "offline_only": True,
    "live_search_executed": False,
    "search_executed": False,
    "provider_selected": False,
    "provider_called": False,
    "model_called": False,
    "fetch_read_executed": False,
    "retrieval_executed": False,
    "evidence_ledger_admission_performed": False,
    "citation_rendering_performed": False,
    "author_called": False,
}
_RAW_PRIVATE_FALSE_FLAGS = {
    "raw_prompt_retained": False,
    "raw_provider_payload_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
    "raw_private_material_serialized": False,
    "retains_raw_private_material": False,
}
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "answer_value_bound",
        "author_payload_ready",
        "citation_bound",
        "citation_eligible",
        "evidence_bound",
        "final_answer_allowed",
        "full_component_success",
        "partial_user_answer_candidate",
        "source_obligation_satisfied",
    }
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "private_log",
        "private_logs",
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
_SENSITIVE_VALUE_MARKERS = (
    "RAW_PROMPT",
    "RAW_PROVIDER_PAYLOAD",
    "RAW_MODEL_RESPONSE",
    "PRIVATE_LOG",
    "DB_CACHE_ROW",
    "FULL_TRACE",
)


class OfflineSearchExecutorExecutionStatus(str, Enum):
    OFFLINE_OBSERVED = "offline_observed"
    NOT_STARTED = "not_started"
    DEFERRED = "deferred"
    BLOCKED_MISSING_COMPONENT_WORK = "blocked_missing_component_work"


@dataclass(frozen=True, slots=True)
class OfflineSearchExecutorComponentObservation:
    component_id: str
    label: str | None = None
    answer_target: str | None = None
    source_obligation_refs: tuple[Mapping[str, Any], ...] = ()
    provider_work_refs: tuple[Mapping[str, Any], ...] = ()
    component_search_plan_ref: Mapping[str, Any] = field(default_factory=dict)
    search_work_ref: Mapping[str, Any] = field(default_factory=dict)
    query_plan_ref: Mapping[str, Any] = field(default_factory=dict)
    candidate_observation_refs: tuple[Mapping[str, Any], ...] = ()
    execution_status: OfflineSearchExecutorExecutionStatus | str = (
        OfflineSearchExecutorExecutionStatus.NOT_STARTED
    )
    rejected_authority_claims: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = _without_empty(
            {
                "component_id": _clean_token(self.component_id),
                "label": _clean_text(self.label, limit=180),
                "answer_target": _clean_text(self.answer_target, limit=180),
                "execution_status": _enum_value(self.execution_status),
                "execution_mode": "offline_inert_product_path_projection",
                "source_obligation_refs": [
                    _json_safe(item) for item in self.source_obligation_refs
                ],
                "provider_work_refs": [
                    _json_safe(item) for item in self.provider_work_refs
                ],
                "component_search_plan_ref": _json_safe(
                    self.component_search_plan_ref
                ),
                "search_work_ref": _json_safe(self.search_work_ref),
                "query_plan_ref": _json_safe(self.query_plan_ref),
                "candidate_observation_refs": [
                    _json_safe(item) for item in self.candidate_observation_refs
                ],
                "candidate_observation_count": len(self.candidate_observation_refs),
                "offline_candidate_observation_refs_are_evidence": False,
                "source_obligation_satisfied": False,
                "evidence_bound": False,
                "citation_bound": False,
                "citation_eligible": False,
                "answer_value_bound": False,
                "semantic_coverage": False,
                "partial_user_answer_candidate": False,
                "full_component_success": False,
                "author_payload_ready": False,
                "final_answer_allowed": None,
                "evidence_ledger_admission_performed": False,
                "fetch_read_executed": False,
                "retrieval_executed": False,
                "rejected_authority_claims": [
                    _json_safe(item) for item in self.rejected_authority_claims
                ],
            }
        )
        payload["final_answer_allowed"] = None
        return payload


@dataclass(frozen=True, slots=True)
class OfflineSearchExecutorBridgeProjection:
    component_observations: tuple[OfflineSearchExecutorComponentObservation, ...]
    source_projection_refs: Mapping[str, Any] = field(default_factory=dict)
    rejected_authority_claims: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = OFFLINE_SEARCH_EXECUTOR_BRIDGE_SCHEMA_VERSION
    owner: str = OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER

    def to_projection(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "trace_key": OFFLINE_SEARCH_EXECUTOR_BRIDGE_TRACE_KEY,
            "owner": self.owner,
            "proof_class": OFFLINE_SEARCH_EXECUTOR_BRIDGE_PROOF_CLASS,
            "offline_product_path_projection_proof": True,
            "offline_only": True,
            "live_search_executed": False,
            "provider_selected": False,
            "provider_called": False,
            "model_called": False,
            "fetch_read_executed": False,
            "retrieval_executed": False,
            "evidence_ledger_admission_performed": False,
            "citation_rendering_performed": False,
            "author_called": False,
            "final_answer_allowed": None,
            "raw_safe": True,
            "retains_raw_private_material": False,
            "source_obligation_satisfied": False,
            "evidence_bound": False,
            "citation_bound": False,
            "citation_eligible": False,
            "answer_value_bound": False,
            "partial_user_answer_candidate": False,
            "full_component_success": False,
            "author_payload_ready": False,
            "authority_boundary": {
                "root_owner": "RunKernel / RunAuthority",
                "bridge_owner": self.owner,
                "consumes": [
                    "AnswerContractAuthorityMap",
                    "ComponentSearchPlan",
                    "SearchWork",
                    "QueryPlan",
                    "offline_candidate_observation",
                ],
                "does_not_admit": ["EvidenceLedger custody"],
                "does_not_satisfy": ["source obligations"],
                "does_not_decide": sorted(_FORBIDDEN_AUTHORITY_FIELDS),
                "next_consumer": "component-scoped EvidenceLedger source custody",
            },
            "source_projection_refs": _json_safe(self.source_projection_refs),
            "component_count": len(self.component_observations),
            "component_observations": [
                item.to_dict() for item in self.component_observations
            ],
            "rejected_authority_claims": [
                _json_safe(item) for item in self.rejected_authority_claims
            ],
            "behavior_boundary_flags": {
                **_BOUNDARY_FALSE_FLAGS,
                **_RAW_PRIVATE_FALSE_FLAGS,
            },
            "raw_private_retention": dict(_RAW_PRIVATE_FALSE_FLAGS),
        }
        projection = _json_safe(payload)
        if isinstance(projection, dict):
            projection["behavior_boundary_flags"] = {
                **_BOUNDARY_FALSE_FLAGS,
                **_RAW_PRIVATE_FALSE_FLAGS,
            }
            projection["raw_private_retention"] = dict(_RAW_PRIVATE_FALSE_FLAGS)
        return projection

    def to_dict(self) -> dict[str, Any]:
        return self.to_projection()


def build_offline_search_executor_bridge_projection(
    *,
    answer_contract_authority_map_projection: Mapping[str, Any] | None = None,
    component_executor_contract_projection: Mapping[str, Any] | None = None,
    component_search_plan_projection: Mapping[str, Any] | None = None,
    component_plan_projection: Mapping[str, Any] | None = None,
    search_work_plan_projection: Mapping[str, Any] | None = None,
    query_plan_work_shadow_projection: Mapping[str, Any] | None = None,
    offline_candidate_observations: Sequence[Mapping[str, Any]] | None = None,
    offline_candidate_fixtures: Sequence[Mapping[str, Any]] | None = None,
) -> OfflineSearchExecutorBridgeProjection:
    """Build an inert SearchExecutor-shaped observation projection."""

    contract = _mapping(component_executor_contract_projection)
    component_plan = _first_mapping(
        component_search_plan_projection,
        component_plan_projection,
        contract.get("component_plan"),
    )
    search_work = _first_mapping(
        search_work_plan_projection,
        contract.get("search_work_plan"),
    )
    query_shadow = _first_mapping(
        query_plan_work_shadow_projection,
        contract.get("query_plan_work_shadow_projection"),
    )
    answer_map = _mapping(answer_contract_authority_map_projection)
    candidate_inputs = tuple(offline_candidate_observations or ()) + tuple(
        offline_candidate_fixtures or ()
    )
    candidates_by_component = _candidate_observations_by_component(
        candidate_inputs
    )
    components = _component_rows(
        answer_map=answer_map,
        component_plan=component_plan,
        search_work=search_work,
        query_shadow=query_shadow,
    )
    observations = tuple(
        _component_observation(
            row,
            answer_map=answer_map,
            search_work=search_work,
            query_shadow=query_shadow,
            candidate_refs=candidates_by_component.get(row["component_id"], ()),
        )
        for row in components
    )
    return OfflineSearchExecutorBridgeProjection(
        source_projection_refs=_source_projection_refs(
            answer_map=answer_map,
            component_executor_contract=contract,
            component_search_plan=component_plan,
            search_work_plan=search_work,
            query_plan_work_shadow=query_shadow,
        ),
        component_observations=observations,
        rejected_authority_claims=tuple(
            _rejected_authority_claims(
                "bridge_input",
                {
                    "answer_contract_authority_map_projection": answer_map,
                    "component_executor_contract_projection": contract,
                    "component_search_plan_projection": component_plan,
                    "search_work_plan_projection": search_work,
                    "query_plan_work_shadow_projection": query_shadow,
                    "offline_candidate_observations": list(candidate_inputs),
                },
            )
        ),
    )


def _component_rows(
    *,
    answer_map: Mapping[str, Any],
    component_plan: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    rows: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def add(component_id: Any, values: Mapping[str, Any]) -> None:
        safe_id = _clean_token(component_id)
        if not safe_id:
            return
        if safe_id not in rows:
            rows[safe_id] = {"component_id": safe_id}
            order.append(safe_id)
        rows[safe_id].update(values)

    for component in _sequence_of_mappings(answer_map.get("components")):
        add(
            component.get("component_id"),
            {
                "answer_contract_component": component,
                "identity_source": "AnswerContractAuthorityMap",
            },
        )
    for component in _sequence_of_mappings(component_plan.get("components")):
        add(
            component.get("component_id"),
            {
                "component_plan_component": component,
                "component_plan_id": component_plan.get("plan_id"),
                "component_plan_schema_version": component_plan.get(
                    "schema_version"
                ),
                "identity_source": rows.get(
                    _clean_token(component.get("component_id")) or "",
                    {},
                ).get("identity_source", "ComponentSearchPlan"),
            },
        )
    for component in _sequence_of_mappings(search_work.get("components")):
        add(
            component.get("component_id"),
            {
                "search_work_component": component,
                "identity_source": rows.get(
                    _clean_token(component.get("component_id")) or "",
                    {},
                ).get("identity_source", "SearchWork"),
            },
        )
    for component in _sequence_of_mappings(query_shadow.get("components")):
        add(
            component.get("component_id"),
            {
                "query_plan_component": component,
                "identity_source": rows.get(
                    _clean_token(component.get("component_id")) or "",
                    {},
                ).get("identity_source", "QueryPlan"),
            },
        )
    return tuple(rows[item] for item in order)


def _component_observation(
    row: Mapping[str, Any],
    *,
    answer_map: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
    candidate_refs: Sequence[Mapping[str, Any]],
) -> OfflineSearchExecutorComponentObservation:
    component_id = _clean_token(row.get("component_id")) or "component:unknown"
    answer_component = _mapping(row.get("answer_contract_component"))
    understanding = _mapping(answer_component.get("understanding"))
    subordinate_work = _mapping(answer_component.get("subordinate_work"))
    search_component = _mapping(row.get("search_work_component"))
    search_metadata = _mapping(search_component.get("metadata"))
    component_plan_component = _mapping(row.get("component_plan_component"))
    query_component = _mapping(row.get("query_plan_component"))
    source_refs = _source_obligation_refs(
        component_id,
        understanding=understanding,
        search_component=search_component,
        query_shadow=query_shadow,
    )
    provider_refs = _provider_work_refs(
        component_id,
        subordinate_work=subordinate_work,
        search_work=search_work,
        query_shadow=query_shadow,
    )
    component_search_plan_ref = _first_mapping(
        subordinate_work.get("component_plan_ref"),
        _component_search_plan_ref(row),
    )
    search_work_ref = _first_mapping(
        subordinate_work.get("search_work_ref"),
        _search_work_ref(component_id, search_work, source_refs, provider_refs),
    )
    query_plan_ref = _first_mapping(
        subordinate_work.get("query_plan_ref"),
        _query_plan_ref(component_id, query_shadow),
    )
    rejected_claims = _rejected_authority_claims(
        component_id,
        {
            "answer_contract_component": answer_component,
            "component_plan_component": component_plan_component,
            "search_work_component": search_component,
            "query_plan_component": query_component,
            "candidate_observation_refs": list(candidate_refs),
        },
    )
    return OfflineSearchExecutorComponentObservation(
        component_id=component_id,
        label=_clean_text(
            understanding.get("label")
            or component_plan_component.get("label")
            or search_metadata.get("component_label"),
            limit=180,
        ),
        answer_target=_clean_text(
            understanding.get("answer_target")
            or component_plan_component.get("answer_target")
            or search_metadata.get("answer_target"),
            limit=180,
        ),
        source_obligation_refs=tuple(source_refs),
        provider_work_refs=tuple(provider_refs),
        component_search_plan_ref=component_search_plan_ref,
        search_work_ref=search_work_ref,
        query_plan_ref=query_plan_ref,
        candidate_observation_refs=tuple(candidate_refs),
        execution_status=_execution_status(
            source_refs=source_refs,
            provider_refs=provider_refs,
            component_search_plan_ref=component_search_plan_ref,
            search_work_ref=search_work_ref,
            query_plan_ref=query_plan_ref,
        ),
        rejected_authority_claims=tuple(rejected_claims),
    )


def _source_obligation_refs(
    component_id: str,
    *,
    understanding: Mapping[str, Any],
    search_component: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for obligation in _sequence_of_mappings(understanding.get("source_obligations")):
        refs.append(
            _without_empty(
                {
                    "source": _clean_token(obligation.get("source"))
                    or "AnswerContractAuthorityMap",
                    "source_obligation_id": _clean_token(
                        obligation.get("obligation_id")
                        or obligation.get("requirement_id")
                    ),
                    "kind": _clean_token(
                        obligation.get("kind")
                        or obligation.get("requirement_kind")
                    ),
                    "source_class": _clean_token(
                        obligation.get("source_class")
                        or obligation.get("search_constraint")
                    ),
                    "component_id": component_id,
                    "satisfied": False,
                }
            )
        )
    for obligation in _sequence_of_mappings(search_component.get("source_obligations")):
        ref = _without_empty(
            {
                "source": "SearchWorkPlan.source_obligations",
                "source_obligation_id": _clean_token(obligation.get("obligation_id")),
                "kind": _clean_token(obligation.get("kind")),
                "source_class": _clean_token(
                    obligation.get("source_class")
                    or obligation.get("search_constraint")
                ),
                "component_id": component_id,
                "satisfied": False,
            }
        )
        if ref and ref not in refs:
            refs.append(ref)
    obligations_by_component = _mapping(
        query_shadow.get("source_obligations_by_component")
    )
    for obligation in _sequence_of_mappings(obligations_by_component.get(component_id)):
        ref = _without_empty(
            {
                "source": "QueryPlanWorkShadow.source_obligations_by_component",
                "source_obligation_id": _clean_token(obligation.get("obligation_id")),
                "kind": _clean_token(obligation.get("kind")),
                "source_class": _clean_token(
                    obligation.get("required_source_class")
                    or obligation.get("source_class")
                ),
                "component_id": component_id,
                "satisfied": False,
            }
        )
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _provider_work_refs(
    component_id: str,
    *,
    subordinate_work: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _sequence_of_mappings(subordinate_work.get("provider_job_refs")):
        ref = _provider_ref(
            item,
            source="AnswerContractAuthorityMap.subordinate_work.provider_job_refs",
        )
        if ref:
            refs.append(ref)
    for item in _sequence_of_mappings(search_work.get("provider_jobs")):
        if component_id not in _text_sequence(item.get("component_ids")):
            continue
        ref = _provider_ref(item, source="SearchWorkPlan.provider_jobs")
        if ref and ref not in refs:
            refs.append(ref)
    jobs_by_component = _mapping(query_shadow.get("provider_jobs_by_component"))
    for item in _sequence_of_mappings(jobs_by_component.get(component_id)):
        ref = _provider_ref(
            item,
            source="QueryPlanWorkShadow.provider_jobs_by_component",
        )
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _provider_ref(item: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    provider_job_id = _clean_token(
        item.get("provider_job_id") or item.get("work_id") or item.get("candidate_id")
    )
    return _without_empty(
        {
            "source": source,
            "provider_job_id": provider_job_id,
            "work_id": provider_job_id,
            "job_kind": _clean_token(item.get("job_kind") or item.get("work_kind")),
            "source_obligation_ids": _text_sequence(
                item.get("source_obligation_ids")
            ),
            "executes_runtime_work": False,
            "provider_selected": False,
            "provider_called": False,
        }
    )


def _component_search_plan_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _clean_token(row.get("component_id"))
    if not row.get("component_plan_id") and not row.get("component_plan_component"):
        return {}
    return _without_empty(
        {
            "source": "ComponentSearchPlan",
            "source_alias": "ComponentPlan",
            "plan_id": _clean_token(row.get("component_plan_id")),
            "schema_version": _clean_token(row.get("component_plan_schema_version")),
            "component_id": component_id,
            "authority_role": "subordinate_component_search_planning_input",
        }
    )


def _search_work_ref(
    component_id: str,
    search_work: Mapping[str, Any],
    source_refs: Sequence[Mapping[str, Any]],
    provider_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not search_work:
        return {}
    return _without_empty(
        {
            "source": "SearchWork",
            "schema_version": _clean_token(search_work.get("schema_version")),
            "trace_key": _clean_token(search_work.get("trace_key")),
            "planning_posture": _clean_token(search_work.get("planning_posture")),
            "component_id": component_id,
            "source_obligation_ids": [
                ref.get("source_obligation_id")
                for ref in source_refs
                if ref.get("source_obligation_id")
            ],
            "provider_job_ids": [
                ref.get("provider_job_id")
                for ref in provider_refs
                if ref.get("provider_job_id")
            ],
            "runtime_consumed": False,
        }
    )


def _query_plan_ref(component_id: str, query_shadow: Mapping[str, Any]) -> dict[str, Any]:
    if not query_shadow:
        return {}
    obligations_by_component = _mapping(
        query_shadow.get("source_obligations_by_component")
    )
    jobs_by_component = _mapping(query_shadow.get("provider_jobs_by_component"))
    return _without_empty(
        {
            "source": "QueryPlanWorkShadow",
            "owner": _clean_token(query_shadow.get("owner")),
            "schema_version": _clean_token(query_shadow.get("schema_version")),
            "component_id": component_id,
            "source_obligation_ids": [
                _clean_token(item.get("obligation_id"))
                for item in _sequence_of_mappings(
                    obligations_by_component.get(component_id)
                )
                if _clean_token(item.get("obligation_id"))
            ],
            "provider_work_ids": [
                _clean_token(item.get("work_id"))
                for item in _sequence_of_mappings(jobs_by_component.get(component_id))
                if _clean_token(item.get("work_id"))
            ],
            "query_text_generated": False,
            "provider_selected": False,
        }
    )


def _candidate_observations_by_component(
    observations: Sequence[Mapping[str, Any]] | None,
) -> dict[str, tuple[dict[str, Any], ...]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in observations or ():
        candidate = _candidate_observation_ref(item)
        component_id = candidate.get("component_id")
        if not component_id:
            continue
        grouped.setdefault(str(component_id), []).append(candidate)
    return {key: tuple(value) for key, value in grouped.items()}


def _candidate_observation_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _clean_token(item.get("component_id"))
    candidate_id = _clean_token(item.get("candidate_id"))
    source_obligation_id = _clean_token(
        item.get("source_obligation_id")
        or item.get("obligation_id")
        or item.get("requirement_id")
    )
    source_class_hint = _clean_token(
        item.get("source_class_hint") or item.get("source_class")
    )
    url = _clean_text(item.get("url"), limit=500)
    domain = _clean_token(item.get("domain"), limit=160)
    title = _clean_text(item.get("title"), limit=220)
    return _without_empty(
        {
            "candidate_id": candidate_id,
            "component_id": component_id,
            "url": url,
            "domain": domain,
            "title": title,
            "source_class_hint": source_class_hint,
            "source_obligation_id": source_obligation_id,
            "candidate_input_kind": "offline_candidate_observation",
            "offline_candidate_observation": True,
            "future_evidence_ledger_intake_shape": True,
            "evidence_ledger_candidate_observation": _without_empty(
                {
                    "candidate_id": candidate_id,
                    "component_id": component_id,
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "source_class_hint": source_class_hint,
                    "source_obligation_id": source_obligation_id,
                    "admission_status": "not_admitted_offline_bridge_only",
                }
            ),
            "fetched": False,
            "read": False,
            "evidence_ledger_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "semantic_coverage": False,
            "final_evidence": False,
            "not_fetched": True,
            "not_read": True,
            "not_evidence_ledger_admitted": True,
            "not_citation_eligible": True,
            "not_source_obligation_satisfied": True,
            "not_semantic_coverage": True,
            "not_final_evidence": True,
            "rejected_authority_claims": _rejected_authority_claims(
                component_id or "candidate_fixture",
                item,
            ),
        }
    )


def _execution_status(
    *,
    source_refs: Sequence[Mapping[str, Any]],
    provider_refs: Sequence[Mapping[str, Any]],
    component_search_plan_ref: Mapping[str, Any],
    search_work_ref: Mapping[str, Any],
    query_plan_ref: Mapping[str, Any],
) -> OfflineSearchExecutorExecutionStatus:
    if not (component_search_plan_ref or search_work_ref or query_plan_ref):
        return OfflineSearchExecutorExecutionStatus.BLOCKED_MISSING_COMPONENT_WORK
    if source_refs or provider_refs:
        return OfflineSearchExecutorExecutionStatus.OFFLINE_OBSERVED
    return OfflineSearchExecutorExecutionStatus.NOT_STARTED


def _source_projection_refs(**projections: Mapping[str, Any]) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, projection in projections.items():
        source = _mapping(projection)
        if not source:
            continue
        refs[name] = _without_empty(
            {
                "owner": _clean_token(source.get("owner")),
                "schema_version": _clean_token(source.get("schema_version")),
                "trace_key": _clean_token(source.get("trace_key")),
                "digest": _stable_digest(source),
            }
        )
    return refs


def _rejected_authority_claims(context: str, value: Any) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, Mapping):
            for key, item in node.items():
                key_text = _clean_token(key, limit=120)
                if not key_text or _is_sensitive_key(key_text):
                    continue
                next_path = (*path, key_text)
                if key_text in _FORBIDDEN_AUTHORITY_FIELDS and item is True:
                    rejected.append(
                        {
                            "context": _clean_token(context),
                            "field": key_text,
                            "path": ".".join(next_path),
                            "claimed_value": True,
                            "disposition": "rejected_subordinate_spoof",
                        }
                    )
                walk(item, next_path)
        elif isinstance(node, Sequence) and not isinstance(node, str | bytes):
            for index, item in enumerate(list(node)[:120]):
                walk(item, (*path, str(index)))

    walk(value, ())
    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in rejected:
        marker = (item.get("context"), item.get("field"), item.get("path"))
        if marker not in seen:
            seen.add(marker)
            unique.append(item)
    return unique


def _first_mapping(*values: Any) -> dict[str, Any]:
    for value in values:
        mapping = _mapping(value)
        if mapping:
            return mapping
    return {}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text_sequence(value: Any) -> list[str]:
    if isinstance(value, str):
        text = _clean_token(value)
        return [text] if text else []
    if not isinstance(value, Sequence):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_token(item)
        if text:
            out.append(text)
    return out


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _stable_digest(value: Any) -> str:
    safe = _json_safe(value)
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":"))
    return "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    if any(marker in text for marker in _SENSITIVE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return (
        normalized.startswith("raw_")
        or normalized in _SENSITIVE_KEYS
        or "secret" in normalized
        or "token" in normalized
        or "password" in normalized
    )


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=120)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item, depth=depth + 1) for item in list(value)[:120]]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER",
    "OFFLINE_SEARCH_EXECUTOR_BRIDGE_PROOF_CLASS",
    "OFFLINE_SEARCH_EXECUTOR_BRIDGE_SCHEMA_VERSION",
    "OFFLINE_SEARCH_EXECUTOR_BRIDGE_TRACE_KEY",
    "OfflineSearchExecutorBridgeProjection",
    "OfflineSearchExecutorComponentObservation",
    "OfflineSearchExecutorExecutionStatus",
    "build_offline_search_executor_bridge_projection",
]
