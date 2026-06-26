"""RunKernel-owned passive map for answer-component authority.

The map is a schema/projection surface only. It observes already-safe
RunKernel, RunAuthority, component-work, ledger, semantic, Sufficiency, and
FinalAnswerPacket projections without calling models, providers, search,
fetch/read, retrieval, citation rendering, or Author execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION = (
    "answer_contract_authority_map_ag_answer_contract_01_v1"
)
ANSWER_CONTRACT_AUTHORITY_MAP_TRACE_KEY = "answer_contract_authority_map"
ANSWER_CONTRACT_AUTHORITY_MAP_OWNER = "RunKernel.AnswerContractAuthorityMap"

_FALSE_BOUNDARY_FLAGS = {
    "model_called": False,
    "provider_selected": False,
    "search_executed": False,
    "fetch_read_executed": False,
    "retrieval_executed": False,
    "author_called": False,
    "raw_prompt_retained": False,
    "raw_provider_payload_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
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
_OFFICIAL_SOURCE_CLASSES = (
    "official",
    "official_current",
    "official_current_rules",
    "official_docs",
    "primary_source",
    "primary_source_documents",
)
_SOURCE_BOUND_MARKERS = ("source_bound", "numeric")


class AnswerComponentWorkStatus(str, Enum):
    PLANNED = "planned"
    NOT_PLANNED = "not_planned"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class AnswerComponentCustodyStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"
    LEDGER_ABSENT = "ledger_absent"
    NO_COMPONENT_REQUIREMENT = "no_component_requirement"


class AnswerComponentBindingStatus(str, Enum):
    BOUND = "bound"
    NOT_BOUND = "not_bound"
    UNKNOWN = "unknown"


class AnswerContractSufficiencyStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    UNKNOWN = "unknown"


class AnswerContractAuthorHandoffStatus(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class AnswerContractComponentAuthority:
    component_id: str
    understanding: Mapping[str, Any] = field(default_factory=dict)
    subordinate_work: Mapping[str, Any] = field(default_factory=dict)
    evidence_custody: Mapping[str, Any] = field(default_factory=dict)
    semantic_coverage: Mapping[str, Any] = field(default_factory=dict)
    binding_status: Mapping[str, Any] = field(default_factory=dict)
    sufficiency_status: Mapping[str, Any] = field(default_factory=dict)
    final_answer_status: Mapping[str, Any] = field(default_factory=dict)
    blocker_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "component_id": _clean_token(self.component_id),
                "understanding": _json_safe(self.understanding),
                "subordinate_work": _json_safe(self.subordinate_work),
                "evidence_custody": _json_safe(self.evidence_custody),
                "semantic_coverage": _json_safe(self.semantic_coverage),
                "binding_status": _json_safe(self.binding_status),
                "sufficiency_status": _json_safe(self.sufficiency_status),
                "final_answer_status": _json_safe(self.final_answer_status),
                "blocker_reasons": list(self.blocker_reasons),
            }
        )


@dataclass(frozen=True, slots=True)
class AnswerContractAuthorityMap:
    components: tuple[AnswerContractComponentAuthority, ...]
    source_projection_refs: Mapping[str, Any] = field(default_factory=dict)
    sufficiency_status: Mapping[str, Any] = field(default_factory=dict)
    final_answer_status: Mapping[str, Any] = field(default_factory=dict)
    component_counts: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION
    owner: str = ANSWER_CONTRACT_AUTHORITY_MAP_OWNER

    def to_projection(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "trace_key": ANSWER_CONTRACT_AUTHORITY_MAP_TRACE_KEY,
            "owner": self.owner,
            "run_authority_owned": True,
            "canonical_state": False,
            "derived_from_canonical_state": True,
            "schema_or_passive_record": True,
            "raw_safe": True,
            "retains_raw_private_material": False,
            "authority_boundary": {
                "root_owner": "RunKernel / RunAuthority",
                "map_owner": self.owner,
                "subordinate_component_search_surfaces": [
                    "InitialAnswerContract",
                    "ComponentPlan",
                    "ComponentSearchPlan",
                    "SearchWork",
                    "QueryPlan",
                    "future SearchExecutor",
                ],
                "subordinates": [
                    "InitialAnswerContract",
                    "ComponentPlan",
                    "ComponentSearchPlan",
                    "SearchWork",
                    "QueryPlan",
                    "future SearchExecutor",
                ],
                "component_plan_role": (
                    "legacy/compat input name for subordinate component-search "
                    "planning"
                ),
                "component_search_plan_role": (
                    "preferred subordinate name for component-scoped search "
                    "planning input"
                ),
                "observes": [
                    "EvidenceLedger",
                    "SemanticObservation",
                    "ComponentCoverage",
                    "SearchJudgment",
                    "SufficiencyJudgment",
                    "FinalAnswerPacket",
                    "Author handoff",
                ],
                "does_not_replace": [
                    "EvidenceLedger custody",
                    "SufficiencyJudgment answerability",
                    "FinalAnswerPacket Author-safe readiness",
                ],
                "readiness_owners": [
                    "EvidenceLedger",
                    "SemanticObservation / ComponentCoverage",
                    "SearchJudgment",
                    "SufficiencyJudgment",
                    "FinalAnswerPacket",
                ],
                "plan_presence_never_satisfies": [
                    "evidence_bound",
                    "citation_bound",
                    "source_obligation_satisfied",
                    "source_obligation_bound",
                    "answer_value_bound",
                    "final_answer_allowed",
                    "partial_user_answer_candidate",
                    "author_payload_ready",
                    "full_component_success",
                ],
            },
            "source_projection_refs": _json_safe(self.source_projection_refs),
            "component_counts": _json_safe(self.component_counts),
            "components": [component.to_dict() for component in self.components],
            "sufficiency_status": _json_safe(self.sufficiency_status),
            "final_answer_status": _json_safe(self.final_answer_status),
            "behavior_boundary_flags": dict(_FALSE_BOUNDARY_FLAGS),
            "raw_private_retention": dict(_FALSE_BOUNDARY_FLAGS),
        }
        projection = _json_safe(payload)
        if isinstance(projection, dict):
            projection["behavior_boundary_flags"] = dict(_FALSE_BOUNDARY_FLAGS)
            projection["raw_private_retention"] = dict(_FALSE_BOUNDARY_FLAGS)
        return projection

    def to_dict(self) -> dict[str, Any]:
        return self.to_projection()


def build_answer_contract_authority_map(
    *,
    component_executor_contract_projection: Mapping[str, Any] | None = None,
    component_plan_projection: Mapping[str, Any] | None = None,
    search_work_plan_projection: Mapping[str, Any] | None = None,
    query_plan_work_shadow_projection: Mapping[str, Any] | None = None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    semantic_observation_projection: Mapping[str, Any] | None = None,
    component_coverage_projection: Mapping[str, Any] | None = None,
    search_judgment_projection: Mapping[str, Any] | None = None,
    sufficiency_judgment_projection: Mapping[str, Any] | None = None,
    final_answer_packet_projection: Mapping[str, Any] | None = None,
    final_answer_authority_projection: Mapping[str, Any] | None = None,
    blocked_final_answer_packet_summary: Mapping[str, Any] | None = None,
) -> AnswerContractAuthorityMap:
    contract = _mapping(component_executor_contract_projection)
    component_plan = _first_mapping(
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
    ledger = _mapping(evidence_ledger_projection)
    semantic = _mapping(semantic_observation_projection)
    coverage = _mapping(component_coverage_projection)
    search_judgment = _mapping(search_judgment_projection)
    sufficiency = _mapping(sufficiency_judgment_projection)
    packet = _mapping(final_answer_packet_projection)
    final_authority = _mapping(final_answer_authority_projection)
    blocked_summary = _mapping(blocked_final_answer_packet_summary)

    source_refs = _source_projection_refs(
        component_executor_contract=contract,
        component_plan=component_plan,
        search_work_plan=search_work,
        query_plan_work_shadow=query_shadow,
        evidence_ledger=ledger,
        semantic_observation=semantic,
        component_coverage=coverage,
        search_judgment=search_judgment,
        sufficiency_judgment=sufficiency,
        final_answer_packet=packet,
        final_answer_authority=final_authority,
        blocked_final_answer_packet_summary=blocked_summary,
    )
    rows = _component_rows(
        component_plan=component_plan,
        search_work=search_work,
        query_shadow=query_shadow,
        coverage=coverage,
    )
    final_status = _final_answer_status(
        sufficiency=sufficiency,
        packet=packet,
        final_authority=final_authority,
        blocked_summary=blocked_summary,
    )
    components = tuple(
        _component_authority(
            component=row,
            search_work=search_work,
            query_shadow=query_shadow,
            ledger=ledger,
            semantic=semantic,
            coverage=coverage,
            search_judgment=search_judgment,
            sufficiency=sufficiency,
            packet=packet,
            final_status=final_status,
        )
        for row in rows
    )
    return AnswerContractAuthorityMap(
        source_projection_refs=source_refs,
        components=components,
        sufficiency_status=_sufficiency_status(sufficiency),
        final_answer_status=final_status,
        component_counts=_component_counts(components),
    )


def _component_authority(
    *,
    component: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
    ledger: Mapping[str, Any],
    semantic: Mapping[str, Any],
    coverage: Mapping[str, Any],
    search_judgment: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    packet: Mapping[str, Any],
    final_status: Mapping[str, Any],
) -> AnswerContractComponentAuthority:
    component_id = _clean_token(component.get("component_id")) or "component:unknown"
    work = _subordinate_work(component, search_work, query_shadow)
    custody = _evidence_custody(component_id, ledger)
    semantic_status = _semantic_coverage(component_id, semantic, coverage)
    binding = _binding_status(
        component_id=component_id,
        packet=packet,
        custody=custody,
        semantic_coverage=semantic_status,
    )
    blockers = _blocker_reasons(
        work=work,
        custody=custody,
        semantic_coverage=semantic_status,
        binding=binding,
        sufficiency=sufficiency,
        search_judgment=search_judgment,
    )
    return AnswerContractComponentAuthority(
        component_id=component_id,
        understanding=_component_understanding(component),
        subordinate_work=work,
        evidence_custody=custody,
        semantic_coverage=semantic_status,
        binding_status=binding,
        sufficiency_status=_component_sufficiency_status(component_id, sufficiency),
        final_answer_status={
            "final_answer_allowed": final_status.get("final_answer_allowed"),
            "author_handoff_status": final_status.get("author_handoff_status"),
            "author_payload_ready": False,
            "component_readiness_owner": "FinalAnswerPacket",
        },
        blocker_reasons=tuple(blockers),
    )


def _component_rows(
    *,
    component_plan: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    rows: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def add(component_id: str | None, values: Mapping[str, Any]) -> None:
        safe_id = _clean_token(component_id)
        if not safe_id:
            return
        if safe_id not in rows:
            rows[safe_id] = {"component_id": safe_id}
            order.append(safe_id)
        rows[safe_id].update(_json_safe(values) or {})

    plan_components = _sequence_of_mappings(component_plan.get("components"))
    for item in plan_components:
        add(
            _clean_token(item.get("component_id")),
            {
                **item,
                "component_identity_source": "ComponentPlan",
                "component_plan_id": component_plan.get("plan_id"),
                "component_plan_schema_version": component_plan.get("schema_version"),
                "plan_ambiguity_status": component_plan.get("ambiguity_status"),
            },
        )

    for item in _sequence_of_mappings(search_work.get("components")):
        component_id = _clean_token(item.get("component_id"))
        existing = rows.get(component_id or "", {})
        metadata = _mapping(item.get("metadata"))
        add(
            component_id,
            {
                "component_identity_source": existing.get("component_identity_source")
                or "SearchWork",
                "search_work_component": item,
                "label": existing.get("label") or metadata.get("component_label"),
                "answer_target": existing.get("answer_target")
                or metadata.get("answer_target"),
                "expected_answerable": existing.get("expected_answerable")
                if "expected_answerable" in existing
                else metadata.get("expected_answerable"),
                "disambiguation_status": existing.get("disambiguation_status")
                or metadata.get("disambiguation_status"),
                "source_requirement": existing.get("source_requirement")
                or metadata.get("source_requirement"),
            },
        )

    for item in _sequence_of_mappings(query_shadow.get("components")):
        component_id = _clean_token(item.get("component_id"))
        existing = rows.get(component_id or "", {})
        add(
            component_id,
            {
                "component_identity_source": existing.get("component_identity_source")
                or "QueryPlanWorkShadow",
                "query_plan_work_shadow_component": item,
            },
        )

    coverage_component_id = _clean_token(
        coverage.get("answer_component_id") or coverage.get("component_id")
    )
    if coverage_component_id:
        existing = rows.get(coverage_component_id, {})
        add(
            coverage_component_id,
            {
                "component_identity_source": existing.get("component_identity_source")
                or "ComponentCoverage",
            },
        )
    return tuple(rows[item] for item in order)


def _component_understanding(component: Mapping[str, Any]) -> dict[str, Any]:
    requirement = _mapping(component.get("source_requirement"))
    source_obligations = _source_obligations_for_component(component)
    source_classes = _source_classes(requirement, source_obligations)
    freshness_kinds = _freshness_kinds(component)
    official_required = any(_contains_marker(item, _OFFICIAL_SOURCE_CLASSES) for item in source_classes)
    current_required = any(item in {"current", "recent"} for item in freshness_kinds) or any(
        _contains_marker(item, ("current",)) for item in source_classes
    )
    source_bound_required = any(
        _contains_marker(item, _SOURCE_BOUND_MARKERS) for item in source_classes
    ) or any(
        _contains_marker(_clean_token(item.get("kind")), _SOURCE_BOUND_MARKERS)
        for item in source_obligations
    )
    return _without_empty(
        {
            "label": _clean_text(component.get("label"), limit=180),
            "answer_target": _clean_text(component.get("answer_target"), limit=180),
            "answer_need": _clean_text(component.get("answer_target"), limit=180),
            "expected_answerable": _optional_bool(component.get("expected_answerable")),
            "ambiguity_status": _clean_token(
                component.get("disambiguation_status")
                or component.get("plan_ambiguity_status")
            ),
            "materiality_status": "required",
            "required_source_classes": source_classes,
            "source_obligations": source_obligations,
            "official_source_required": official_required,
            "current_source_required": current_required,
            "source_bound_required": source_bound_required,
            "component_identity_source": _clean_token(
                component.get("component_identity_source")
            )
            or "unavailable_or_deferred",
        }
    )


def _subordinate_work(
    component: Mapping[str, Any],
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
) -> dict[str, Any]:
    component_id = _clean_token(component.get("component_id")) or "component:unknown"
    search_component = _mapping(component.get("search_work_component"))
    query_component = _mapping(component.get("query_plan_work_shadow_component"))
    provider_job_refs = _provider_job_refs(component_id, search_work, query_shadow)
    obligation_ids = [
        item.get("obligation_id")
        for item in _source_obligations_for_component(component)
        if item.get("obligation_id")
    ]
    planned = bool(component.get("component_plan_id") or search_component or query_component)
    return _without_empty(
        {
            "work_status": (
                AnswerComponentWorkStatus.PLANNED.value
                if planned
                else AnswerComponentWorkStatus.UNAVAILABLE.value
            ),
            "planned": planned,
            "component_plan_ref": _component_plan_ref(component),
            "component_search_plan_ref": _search_component_ref(search_component),
            "search_work_ref": _search_work_ref(
                component_id,
                search_work,
                obligation_ids,
                provider_job_refs,
            ),
            "query_plan_ref": _query_plan_ref(component_id, query_shadow),
            "future_search_executor_status": "deferred",
            "searched_status": "not_started",
            "fetch_read_status": "not_started",
            "execution_status": "not_started",
            "execution_failed": False,
            "execution_blocked": False,
            "execution_skipped": False,
            "execution_deferred": True,
            "provider_search_refs": provider_job_refs,
            "raw_query_text_retained": False,
            "planned_queries_retained_as_text": False,
        }
    )


def _evidence_custody(component_id: str, ledger: Mapping[str, Any]) -> dict[str, Any]:
    if not ledger:
        return {
            "ledger_ref_available": False,
            "custody_status": AnswerComponentCustodyStatus.LEDGER_ABSENT.value,
            "source_obligation_satisfied": "unknown",
            "source_obligation_satisfaction_owner": "EvidenceLedger",
            "source_obligation_satisfaction_inferred_from_plan": False,
            "candidate_refs": [],
            "component_candidate_link_refs": [],
            "source_requirement_refs": [],
            "component_source_obligation_refs": [],
            "custody_gaps": [],
            "component_custody_gap_refs": [],
            "official_current_compatibility_status": "unknown",
            "readability_status": "unknown",
            "source_bound_compatibility_status": "unknown",
        }
    component_custody = _component_scoped_custody_for_component(
        ledger,
        component_id,
    )
    requirements = [
        item
        for item in _sequence_of_mappings(ledger.get("source_requirements"))
        if _matches_component(component_id, item)
    ]
    requirement_ids = [
        item.get("requirement_id")
        for item in requirements
        if _clean_token(item.get("requirement_id"))
    ]
    candidates = _candidate_refs(ledger, requirement_ids, component_id)
    gaps = [
        _gap_ref(item)
        for item in _sequence_of_mappings(ledger.get("custody_gaps"))
        if _matches_component(component_id, item)
        or _clean_token(item.get("requirement_id")) in requirement_ids
    ]
    component_obligations = [
        _component_source_obligation_ref(item)
        for item in _sequence_of_mappings(
            component_custody.get("source_obligation_refs")
        )
    ]
    component_candidates = [
        _component_candidate_link_ref(item)
        for item in _sequence_of_mappings(component_custody.get("candidate_links"))
    ]
    component_gaps = [
        _gap_ref(item)
        for item in _sequence_of_mappings(component_custody.get("custody_gaps"))
    ]
    statuses = [_clean_token(item.get("status")) or "unknown" for item in requirements]
    custody_status = _custody_status(statuses, requirements, ledger)
    return {
        "ledger_ref_available": True,
        "ledger_owner": _clean_token(ledger.get("owner")),
        "ledger_schema_version": _clean_token(ledger.get("schema_version")),
        "custody_status": custody_status,
        "candidate_refs": candidates,
        "component_candidate_link_refs": component_candidates,
        "component_scoped_source_custody_ref": _component_custody_projection_ref(
            ledger,
            component_custody,
        ),
        "source_requirement_refs": [
            _without_empty(
                {
                    "requirement_id": _clean_token(item.get("requirement_id")),
                    "requirement_kind": _clean_token(item.get("requirement_kind")),
                    "required_source_class": _clean_token(
                        item.get("required_source_class")
                    ),
                    "required_currentness": _clean_token(
                        item.get("required_currentness")
                    ),
                    "status": _clean_token(item.get("status")),
                    "linked_candidate_ids": _text_list(
                        item.get("linked_candidate_ids")
                    ),
                }
            )
            for item in requirements
        ],
        "component_source_obligation_refs": component_obligations,
        "custody_gaps": gaps,
        "component_custody_gap_refs": component_gaps,
        "source_obligation_satisfied": (
            "satisfied"
            if custody_status == AnswerComponentCustodyStatus.SATISFIED.value
            else "unsatisfied"
            if custody_status
            in {
                AnswerComponentCustodyStatus.UNSATISFIED.value,
                AnswerComponentCustodyStatus.PARTIALLY_SATISFIED.value,
            }
            else "unknown"
        ),
        "source_obligation_satisfaction_owner": "EvidenceLedger",
        "source_obligation_satisfaction_inferred_from_plan": False,
        "official_current_compatibility_status": _compatibility_status(
            requirements,
            marker="official",
        ),
        "readability_status": _readability_status(candidates),
        "source_bound_compatibility_status": _compatibility_status(
            requirements,
            marker="source_bound",
        ),
    }


def _semantic_coverage(
    component_id: str,
    semantic: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_refs: list[dict[str, Any]] = []
    if semantic and _matches_component(component_id, semantic):
        semantic_refs.append(
            _without_empty(
                {
                    "semantic_observation_id": _clean_token(
                        semantic.get("observation_id")
                        or semantic.get("semantic_observation_id")
                    ),
                    "semantic_observation_digest": _clean_token(
                        semantic.get("observation_digest")
                        or semantic.get("semantic_observation_digest"),
                        limit=128,
                    ),
                    "support_status": _clean_token(semantic.get("support_status")),
                }
            )
        )
    coverage_refs: list[dict[str, Any]] = []
    coverage_status = "unknown"
    if coverage and _matches_component(component_id, coverage):
        coverage_status = _clean_token(coverage.get("coverage_state")) or "unknown"
        coverage_refs.append(
            _without_empty(
                {
                    "coverage_record_id": _clean_token(
                        coverage.get("coverage_record_id")
                        or coverage.get("record_id")
                    ),
                    "coverage_record_digest": _clean_token(
                        coverage.get("coverage_record_digest"),
                        limit=128,
                    ),
                    "coverage_state": coverage_status,
                    "semantic_support_status": _clean_token(
                        coverage.get("semantic_support_status")
                    ),
                }
            )
        )
    ledger_compatible_support = bool(
        coverage_status == "satisfied"
        and _clean_token(coverage.get("ledger_custody_status")) == "satisfied"
    )
    return {
        "semantic_observation_refs": semantic_refs,
        "component_coverage_refs": coverage_refs,
        "coverage_status": coverage_status,
        "support_status": _clean_token(semantic.get("support_status")) or "unknown",
        "caveat_status": "unknown",
        "blocker_status": "unknown",
        "ledger_compatible_support": ledger_compatible_support,
        "coverage_requires_ledger_compatible_support": True,
        "coverage_inferred_from_evidence_id_only": False,
        "coverage_inferred_from_author_prose": False,
    }


def _binding_status(
    *,
    component_id: str,
    packet: Mapping[str, Any],
    custody: Mapping[str, Any],
    semantic_coverage: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_bindings = [
        item
        for item in _sequence_of_mappings(packet.get("semantic_packet_evidence_bindings"))
        if _matches_component(component_id, item)
    ]
    source_obligations = [
        item
        for item in _sequence_of_mappings(packet.get("source_obligations"))
        if _matches_component(component_id, item)
    ]
    source_obligation_bound = any(
        _clean_token(item.get("status")) == "satisfied" for item in source_obligations
    )
    evidence_bound = bool(semantic_bindings)
    citation_binding_refs = _component_compatible_citation_refs(
        component_id=component_id,
        semantic_bindings=semantic_bindings,
        packet=packet,
        custody=custody,
    )
    citation_bound = bool(citation_binding_refs)
    answer_value_bound = bool(
        semantic_bindings and semantic_coverage.get("coverage_status") == "satisfied"
    )
    full_success = (
        evidence_bound
        and citation_bound
        and source_obligation_bound
        and answer_value_bound
    )
    blocker_reasons: list[str] = []
    if not evidence_bound:
        blocker_reasons.append("evidence_not_bound_by_final_answer_packet")
    if not citation_bound:
        blocker_reasons.append("citation_not_bound_by_final_answer_packet")
    if not source_obligation_bound:
        blocker_reasons.append("source_obligation_not_bound_by_final_answer_packet")
    if not answer_value_bound:
        blocker_reasons.append("answer_value_not_bound_by_semantic_packet")
    blocker_reasons.extend(_component_custody_binding_blockers(custody))
    return {
        "evidence_bound": evidence_bound,
        "evidence_binding_status": (
            AnswerComponentBindingStatus.BOUND.value
            if evidence_bound
            else AnswerComponentBindingStatus.NOT_BOUND.value
        ),
        "citation_bound": citation_bound,
        "citation_binding_status": (
            AnswerComponentBindingStatus.BOUND.value
            if citation_bound
            else AnswerComponentBindingStatus.NOT_BOUND.value
        ),
        "citation_binding_refs": citation_binding_refs,
        "source_obligation_bound": source_obligation_bound,
        "source_obligation_binding_status": (
            AnswerComponentBindingStatus.BOUND.value
            if source_obligation_bound
            else AnswerComponentBindingStatus.NOT_BOUND.value
        ),
        "answer_value_bound": answer_value_bound,
        "answer_value_binding_status": (
            AnswerComponentBindingStatus.BOUND.value
            if answer_value_bound
            else AnswerComponentBindingStatus.NOT_BOUND.value
        ),
        "full_component_success": full_success,
        "partial_user_answer_candidate": False,
        "source_obligation_satisfied_from_ledger": (
            custody.get("source_obligation_satisfied") == "satisfied"
        ),
        "plan_presence_contributed_to_binding": False,
        "component_candidate_link_refs": _json_safe(
            custody.get("component_candidate_link_refs") or []
        ),
        "component_custody_gap_refs": _json_safe(
            custody.get("component_custody_gap_refs") or []
        ),
        "blocker_reasons": list(
            dict.fromkeys(reason for reason in blocker_reasons if reason)
        ),
    }


def _component_compatible_citation_refs(
    *,
    component_id: str,
    semantic_bindings: Sequence[Mapping[str, Any]],
    packet: Mapping[str, Any],
    custody: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not semantic_bindings:
        return []
    evidence_refs, candidate_refs, source_refs = _component_binding_ref_sets(
        semantic_bindings=semantic_bindings,
        packet=packet,
        custody=custody,
    )
    compatible_refs: list[dict[str, Any]] = []
    for citation in _sequence_of_mappings(packet.get("citation_eligible")):
        status = _clean_token(citation.get("status"))
        if status and status != "citation_eligible":
            continue
        relation = _citation_component_relation(
            component_id=component_id,
            citation=citation,
            evidence_refs=evidence_refs,
            candidate_refs=candidate_refs,
            source_refs=source_refs,
        )
        if not relation:
            continue
        compatible_refs.append(
            _without_empty(
                {
                    "citation_id": _clean_token(citation.get("citation_id")),
                    "evidence_id": _clean_token(citation.get("evidence_id")),
                    "source_id": _clean_token(citation.get("source_id")),
                    "relation": relation,
                }
            )
        )
    return compatible_refs


def _component_binding_ref_sets(
    *,
    semantic_bindings: Sequence[Mapping[str, Any]],
    packet: Mapping[str, Any],
    custody: Mapping[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    evidence_refs: set[str] = set()
    candidate_refs: set[str] = set()
    source_refs: set[str] = set()

    for binding in semantic_bindings:
        for key in (
            "packet_evidence_id",
            "origin_evidence_ref_id",
            "evidence_id",
            "admitted_evidence_ref",
        ):
            _add_normalized_ref(evidence_refs, binding.get(key))
        for key in ("candidate_id", "origin_candidate_id"):
            _add_normalized_ref(candidate_refs, binding.get(key))
        for key in ("source_id", "citation_source_id", "source_ref_id"):
            _add_normalized_ref(source_refs, binding.get(key))

    for candidate in _sequence_of_mappings(custody.get("candidate_refs")):
        if _candidate_ref_binding_eligible(candidate):
            _add_normalized_ref(candidate_refs, candidate.get("candidate_id"))

    for evidence in _sequence_of_mappings(packet.get("evidence_allowed")):
        if _evidence_record_matches_component_refs(
            evidence,
            evidence_refs=evidence_refs,
            candidate_refs=candidate_refs,
        ):
            _add_normalized_ref(evidence_refs, evidence.get("evidence_id"))
            _add_normalized_ref(evidence_refs, evidence.get("origin_evidence_ref_id"))
            _add_normalized_ref(source_refs, evidence.get("source_id"))
    return evidence_refs, candidate_refs, source_refs


def _evidence_record_matches_component_refs(
    evidence: Mapping[str, Any],
    *,
    evidence_refs: set[str],
    candidate_refs: set[str],
) -> bool:
    return any(
        _normalized_ref(evidence.get(key)) in evidence_refs | candidate_refs
        for key in ("evidence_id", "origin_evidence_ref_id")
        if _normalized_ref(evidence.get(key))
    )


def _citation_component_relation(
    *,
    component_id: str,
    citation: Mapping[str, Any],
    evidence_refs: set[str],
    candidate_refs: set[str],
    source_refs: set[str],
) -> str | None:
    if _citation_directly_matches_component(component_id, citation):
        return "direct_component_ref"
    evidence_id = _normalized_ref(citation.get("evidence_id"))
    if evidence_id and evidence_id in evidence_refs | candidate_refs:
        return "component_evidence_ref"
    source_id = _normalized_ref(citation.get("source_id"))
    if source_id and source_id in source_refs | candidate_refs:
        return "component_source_ref"
    return None


def _citation_directly_matches_component(
    component_id: str,
    citation: Mapping[str, Any],
) -> bool:
    component = _normalize(component_id)
    if not component:
        return False
    for key in (
        "component_id",
        "answer_component_id",
        "search_work_component_id",
        "requirement_id",
        "obligation_id",
        "custody_requirement_id",
    ):
        value = _normalize(citation.get(key))
        if value and component in value:
            return True
    return False


def _add_normalized_ref(target: set[str], value: Any) -> None:
    normalized = _normalized_ref(value)
    if normalized:
        target.add(normalized)


def _normalized_ref(value: Any) -> str | None:
    token = _clean_token(value, limit=200)
    return _normalize(token) if token else None


def _sufficiency_status(sufficiency: Mapping[str, Any]) -> dict[str, Any]:
    if not sufficiency:
        return {
            "status": AnswerContractSufficiencyStatus.UNKNOWN.value,
            "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
            "final_answer_allowed": None,
            "readiness_status": "unknown",
        }
    allowed = sufficiency.get("final_answer_allowed")
    status = (
        AnswerContractSufficiencyStatus.ALLOWED.value
        if allowed is True
        else AnswerContractSufficiencyStatus.BLOCKED.value
        if allowed is False
        else AnswerContractSufficiencyStatus.DEFERRED.value
    )
    final_packet_inputs = _mapping(sufficiency.get("final_packet_inputs"))
    semantic_summary = _mapping(sufficiency.get("semantic_state_facts_summary"))
    if not semantic_summary:
        semantic_summary = _mapping(sufficiency.get("semantic_consumption"))
    return {
        "status": status,
        "owner": _clean_token(sufficiency.get("owner"))
        or "RunKernel.RunAuthoritySufficiencyJudgment",
        "judgment_id": _clean_token(sufficiency.get("judgment_id")),
        "decision": _clean_token(sufficiency.get("decision")),
        "final_answer_posture": _clean_token(sufficiency.get("final_answer_posture")),
        "final_answer_allowed": allowed if isinstance(allowed, bool) else None,
        "readiness_status": _clean_token(final_packet_inputs.get("readiness_status"))
        or "unknown",
        "required_obligations_satisfied": _optional_bool(
            sufficiency.get("required_obligations_satisfied")
        ),
        "missing_required_obligation_count": len(
            _sequence_of_mappings(sufficiency.get("missing_required_obligations"))
        ),
        "partial_obligation_count": len(
            _sequence_of_mappings(sufficiency.get("partial_obligations"))
        ),
        "satisfied_obligation_count": len(
            _sequence_of_mappings(sufficiency.get("satisfied_obligations"))
        ),
        "mandatory_caveats": _text_list(sufficiency.get("mandatory_caveats")),
        "prohibited_upgrades": _text_list(sufficiency.get("prohibited_upgrades")),
        "semantic_component_counts": _without_empty(
            {
                "required_component_count": semantic_summary.get(
                    "required_component_count"
                ),
                "covered_component_count": semantic_summary.get(
                    "covered_component_count"
                ),
                "missing_component_count": semantic_summary.get(
                    "missing_component_count"
                ),
            }
        ),
        "does_not_replace_sufficiency_judgment": True,
    }


def _component_sufficiency_status(
    component_id: str,
    sufficiency: Mapping[str, Any],
) -> dict[str, Any]:
    missing = [
        item
        for item in _sequence_of_mappings(sufficiency.get("missing_required_obligations"))
        if _matches_component(component_id, item)
    ]
    partial = [
        item
        for item in _sequence_of_mappings(sufficiency.get("partial_obligations"))
        if _matches_component(component_id, item)
    ]
    satisfied = [
        item
        for item in _sequence_of_mappings(sufficiency.get("satisfied_obligations"))
        if _matches_component(component_id, item)
    ]
    if missing:
        status = "missing"
    elif partial:
        status = "partial"
    elif satisfied:
        status = "satisfied"
    else:
        status = "unknown"
    return {
        "status": status,
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "missing_required_obligation_refs": [_requirement_ref(item) for item in missing],
        "partial_obligation_refs": [_requirement_ref(item) for item in partial],
        "satisfied_obligation_refs": [_requirement_ref(item) for item in satisfied],
        "final_answer_allowed_for_component": None,
    }


def _final_answer_status(
    *,
    sufficiency: Mapping[str, Any],
    packet: Mapping[str, Any],
    final_authority: Mapping[str, Any],
    blocked_summary: Mapping[str, Any],
) -> dict[str, Any]:
    source = final_authority or packet
    payload_ref = _mapping(source.get("author_payload_ref"))
    authority_payload = _mapping(payload_ref.get("authority_payload"))
    allowed = _first_bool(
        packet.get("final_answer_allowed"),
        final_authority.get("final_answer_allowed"),
        authority_payload.get("final_answer_allowed"),
        sufficiency.get("final_answer_allowed"),
        blocked_summary.get("final_answer_allowed"),
    )
    readiness = (
        _clean_token(source.get("readiness_status"))
        or _clean_token(packet.get("readiness_status"))
        or _clean_token(payload_ref.get("readiness_status"))
        or _clean_token(blocked_summary.get("readiness_status"))
        or "unknown"
    )
    payload_status = _clean_token(payload_ref.get("status"))
    if payload_status == "author_input_ready":
        handoff = AnswerContractAuthorHandoffStatus.READY.value
    elif payload_status == "blocked" or readiness == "blocked" or allowed is False:
        handoff = AnswerContractAuthorHandoffStatus.BLOCKED.value
    elif source or sufficiency:
        handoff = AnswerContractAuthorHandoffStatus.DEFERRED.value
    else:
        handoff = AnswerContractAuthorHandoffStatus.ABSENT.value
    return {
        "owner": "RunKernel.FinalAnswerPacket",
        "packet_present": bool(source or packet),
        "packet_id": _clean_token(
            source.get("packet_id")
            or packet.get("packet_id")
            or blocked_summary.get("packet_id")
        ),
        "readiness_status": readiness,
        "final_answer_allowed": allowed,
        "author_handoff_status": handoff,
        "author_payload_present": bool(payload_ref),
        "author_payload_ready": handoff == AnswerContractAuthorHandoffStatus.READY.value,
        "author_payload_blocked": handoff == AnswerContractAuthorHandoffStatus.BLOCKED.value,
        "blocked_fap_summary_ref": _blocked_summary_ref(blocked_summary),
        "missing_source_obligation_count": _optional_int(
            source.get("missing_source_obligation_count")
            or blocked_summary.get("missing_source_obligation_count")
        ),
        "partial_source_obligation_count": _optional_int(
            source.get("partial_source_obligation_count")
            or blocked_summary.get("partial_source_obligation_count")
        ),
        "satisfied_source_obligation_count": _optional_int(
            source.get("satisfied_source_obligation_count")
            or blocked_summary.get("satisfied_source_obligation_count")
        ),
        "mandatory_caveat_count": _optional_int(
            source.get("mandatory_caveat_count")
            or blocked_summary.get("mandatory_caveat_count")
        ),
        "prohibited_upgrade_count": _optional_int(
            source.get("prohibited_upgrade_count")
            or blocked_summary.get("prohibited_upgrade_count")
        ),
        "does_not_replace_final_answer_packet": True,
    }


def _component_counts(
    components: Sequence[AnswerContractComponentAuthority],
) -> dict[str, Any]:
    full = [
        component
        for component in components
        if component.binding_status.get("full_component_success") is True
    ]
    partial = [
        component
        for component in components
        if component.binding_status.get("full_component_success") is not True
        and (
            component.evidence_custody.get("candidate_refs")
            or component.semantic_coverage.get("coverage_status") not in {None, "unknown"}
        )
    ]
    missing = len(components) - len(full) - len(partial)
    return {
        "required_component_count": len(components),
        "satisfied_component_count": len(full),
        "partial_component_count": len(partial),
        "missing_component_count": max(0, missing),
        "full_component_success_count": len(full),
        "partial_user_answer_candidate_count": 0,
        "author_payload_ready_component_count": 0,
    }


def _source_projection_refs(**sources: Mapping[str, Any]) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for name, value in sources.items():
        mapping = _mapping(value)
        if not mapping:
            continue
        refs[name] = _without_empty(
            {
                "available": True,
                "owner": _clean_token(mapping.get("owner")),
                "schema_version": _clean_token(mapping.get("schema_version")),
                "trace_key": _clean_token(mapping.get("trace_key")),
                "digest": _stable_digest(mapping),
            }
        )
    refs["available_source_count"] = len(refs)
    return refs


def _component_plan_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    if not component.get("component_plan_id"):
        return {}
    return _without_empty(
        {
            "source": "ComponentPlan",
            "source_alias": "ComponentSearchPlan",
            "authority_role": "subordinate_component_search_planning_input",
            "authority_owner": ANSWER_CONTRACT_AUTHORITY_MAP_OWNER,
            "plan_id": _clean_token(component.get("component_plan_id")),
            "schema_version": _clean_token(
                component.get("component_plan_schema_version")
            ),
            "component_id": _clean_token(component.get("component_id")),
            "cannot_decide": [
                "final_answer_allowed",
                "partial_user_answer_candidate",
                "source_obligation_satisfied",
                "evidence_bound",
                "citation_bound",
                "answer_value_bound",
                "author_payload_ready",
                "full_component_success",
            ],
        }
    )


def _search_component_ref(component: Mapping[str, Any]) -> dict[str, Any]:
    if not component:
        return {}
    return _without_empty(
        {
            "source": "SearchWorkPlan.components",
            "component_id": _clean_token(component.get("component_id")),
            "source_obligation_count": len(
                _sequence_of_mappings(component.get("source_obligations"))
            ),
            "required_provider_job_count": len(
                _text_list(component.get("required_provider_jobs"))
            ),
            "stop_condition_count": len(
                _sequence_of_mappings(component.get("stop_conditions"))
            ),
        }
    )


def _search_work_ref(
    component_id: str,
    search_work: Mapping[str, Any],
    obligation_ids: Sequence[Any],
    provider_job_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not search_work:
        return {}
    return _without_empty(
        {
            "source": "SearchWork",
            "schema_version": _clean_token(search_work.get("schema_version")),
            "planning_posture": _clean_token(search_work.get("planning_posture")),
            "passive": _optional_bool(search_work.get("passive")),
            "runtime_consumed": _optional_bool(search_work.get("runtime_consumed")),
            "component_id": _clean_token(component_id),
            "source_obligation_ids": _text_list(obligation_ids),
            "provider_job_ids": [
                ref.get("provider_job_id")
                for ref in provider_job_refs
                if ref.get("provider_job_id")
            ],
        }
    )


def _query_plan_ref(
    component_id: str,
    query_shadow: Mapping[str, Any],
) -> dict[str, Any]:
    if not query_shadow:
        return {}
    obligations = _mapping(query_shadow.get("source_obligations_by_component")).get(
        component_id,
        (),
    )
    jobs = _mapping(query_shadow.get("provider_jobs_by_component")).get(component_id, ())
    return _without_empty(
        {
            "source": "QueryPlanWorkShadow",
            "owner": _clean_token(query_shadow.get("owner")),
            "schema_version": _clean_token(query_shadow.get("schema_version")),
            "shadow_only": _optional_bool(query_shadow.get("shadow_only")),
            "runtime_consumed_by_query_plan": _optional_bool(
                query_shadow.get("runtime_consumed_by_query_plan")
            ),
            "component_id": _clean_token(component_id),
            "source_obligation_ids": [
                _clean_token(item.get("obligation_id"))
                for item in _sequence_of_mappings(obligations)
                if _clean_token(item.get("obligation_id"))
            ],
            "provider_work_ids": [
                _clean_token(item.get("work_id"))
                for item in _sequence_of_mappings(jobs)
                if _clean_token(item.get("work_id"))
            ],
            "query_text_generated": False,
            "provider_selected": False,
        }
    )


def _provider_job_refs(
    component_id: str,
    search_work: Mapping[str, Any],
    query_shadow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _sequence_of_mappings(search_work.get("provider_jobs")):
        if component_id not in _text_list(item.get("component_ids")):
            continue
        refs.append(
            _without_empty(
                {
                    "provider_job_id": _clean_token(item.get("provider_job_id")),
                    "job_kind": _clean_token(item.get("job_kind")),
                    "source_obligation_ids": _text_list(
                        item.get("source_obligation_ids")
                    ),
                    "job_posture": _clean_token(item.get("job_posture")),
                    "executes_runtime_work": False,
                }
            )
        )
    for item in _sequence_of_mappings(
        _mapping(query_shadow.get("provider_jobs_by_component")).get(component_id)
    ):
        ref = _without_empty(
            {
                "provider_job_id": _clean_token(item.get("work_id")),
                "job_kind": _clean_token(item.get("work_kind")),
                "source_obligation_ids": _text_list(item.get("source_obligation_ids")),
                "query_plan_shadow_only": True,
                "executes_runtime_work": False,
            }
        )
        if ref not in refs:
            refs.append(ref)
    return refs


def _source_obligations_for_component(
    component: Mapping[str, Any],
) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    component_id = _clean_token(component.get("component_id")) or "component:unknown"
    requirement = _mapping(component.get("source_requirement"))
    if requirement:
        source_class = _clean_token(requirement.get("source_class"))
        obligations.append(
            _without_empty(
                {
                    "obligation_id": f"{component_id}:source-requirement",
                    "source": "ComponentPlan.source_requirement",
                    "source_class": source_class,
                    "citation_required": _optional_bool(
                        requirement.get("citation_required")
                    ),
                    "fetch_read_required": _optional_bool(
                        requirement.get("fetch_read_required")
                    ),
                }
            )
        )
    search_component = _mapping(component.get("search_work_component"))
    for item in _sequence_of_mappings(search_component.get("source_obligations")):
        obligation = _without_empty(
            {
                "obligation_id": _clean_token(item.get("obligation_id")),
                "source": "SearchWorkPlan.source_obligations",
                "kind": _clean_token(item.get("kind")),
                "strictness": _clean_token(item.get("strictness")),
                "search_constraint": _clean_token(item.get("search_constraint")),
                "currentness_required": _optional_bool(
                    item.get("currentness_required")
                    or bool(item.get("currentness_requirement"))
                ),
                "satisfaction_rule_present": bool(item.get("satisfaction_rule")),
            }
        )
        if obligation and obligation not in obligations:
            obligations.append(obligation)
    query_shadow_component = _mapping(component.get("query_plan_work_shadow_component"))
    if query_shadow_component.get("source_obligation_count") and not obligations:
        obligations.append(
            {
                "source": "QueryPlanWorkShadow",
                "obligation_id": f"{component_id}:query-plan-shadow-obligation",
                "status": "hint_only",
            }
        )
    return obligations


def _source_classes(
    requirement: Mapping[str, Any],
    source_obligations: Sequence[Mapping[str, Any]],
) -> list[str]:
    classes: list[str] = []
    for value in (
        requirement.get("source_class"),
        requirement.get("required_source_class"),
    ):
        token = _clean_token(value)
        if token and token not in classes:
            classes.append(token)
    for obligation in source_obligations:
        for key in ("source_class", "search_constraint", "kind"):
            token = _clean_token(obligation.get(key))
            if token and token not in classes:
                classes.append(token)
    return classes


def _freshness_kinds(component: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for intent in _sequence_of_mappings(component.get("search_intents")):
        policy = _mapping(intent.get("freshness_policy"))
        kind = _clean_token(policy.get("kind"))
        if kind:
            out.add(kind)
    search_component = _mapping(component.get("search_work_component"))
    metadata = _mapping(search_component.get("metadata"))
    for intent in _sequence_of_mappings(metadata.get("search_intents")):
        policy = _mapping(intent.get("freshness_policy"))
        kind = _clean_token(policy.get("kind"))
        if kind:
            out.add(kind)
    return out


def _candidate_refs(
    ledger: Mapping[str, Any],
    requirement_ids: Sequence[str],
    component_id: str,
) -> list[dict[str, Any]]:
    linked_ids = set(requirement_ids)
    for link in _sequence_of_mappings(ledger.get("requirement_links")):
        if _clean_token(link.get("requirement_id")) in linked_ids:
            candidate_id = _clean_token(link.get("candidate_id"))
            if candidate_id:
                linked_ids.add(candidate_id)
    refs: list[dict[str, Any]] = []
    for candidate in _sequence_of_mappings(ledger.get("candidate_records")):
        candidate_id = _clean_token(candidate.get("candidate_id"))
        if not candidate_id:
            continue
        match = candidate_id in linked_ids or _matches_component(component_id, candidate)
        if not match:
            continue
        refs.append(
            _without_empty(
                {
                    "candidate_id": candidate_id,
                    "domain": _clean_token(candidate.get("domain")),
                    "source_class": _clean_token(candidate.get("source_class")),
                    "source_tier": _clean_token(candidate.get("source_tier")),
                    "readable_status": _clean_token(candidate.get("readable_status")),
                    "fetchable_status": _clean_token(candidate.get("fetchable_status")),
                    "fact_disposition": _clean_token(candidate.get("fact_disposition")),
                    "final_evidence_eligible": candidate.get(
                        "final_evidence_eligible"
                    ),
                }
            )
        )
    return refs


def _component_scoped_custody_for_component(
    ledger: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    custody_projection = _mapping(ledger.get("component_scoped_source_custody"))
    normalized_component = _normalize(component_id)
    for item in _sequence_of_mappings(custody_projection.get("per_component_custody")):
        if _normalize(item.get("component_id")) == normalized_component:
            return _json_safe(item) or {}
    return {}


def _component_custody_projection_ref(
    ledger: Mapping[str, Any],
    component_custody: Mapping[str, Any],
) -> dict[str, Any]:
    if not component_custody:
        return {}
    custody_projection = _mapping(ledger.get("component_scoped_source_custody"))
    return _without_empty(
        {
            "available": True,
            "owner": _clean_token(custody_projection.get("owner"))
            or _clean_token(ledger.get("owner")),
            "schema_version": _clean_token(custody_projection.get("schema_version")),
            "trace_key": _clean_token(custody_projection.get("trace_key")),
            "component_id": _clean_token(component_custody.get("component_id")),
            "candidate_links_are_evidence": False,
            "source_obligations_satisfied_by_candidate_presence": False,
        }
    )


def _component_source_obligation_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "component_id": _clean_token(item.get("component_id")),
            "source_obligation_id": _clean_token(
                item.get("source_obligation_id")
                or item.get("requirement_id")
                or item.get("obligation_id")
            ),
            "source": _clean_token(item.get("source")),
            "kind": _clean_token(item.get("kind") or item.get("requirement_kind")),
            "required_source_class": _clean_token(
                item.get("required_source_class")
                or item.get("source_class")
                or item.get("search_constraint")
            ),
            "status": _clean_token(item.get("status")),
            "source_obligation_status": _clean_token(
                item.get("source_obligation_status")
            ),
            "source_obligation_satisfied": False,
        }
    )


def _component_candidate_link_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    ref = _without_empty(
        {
            "component_id": _clean_token(item.get("component_id")),
            "candidate_id": _clean_token(item.get("candidate_id")),
            "source_obligation_id": _clean_token(
                item.get("source_obligation_id")
                or item.get("requirement_id")
                or item.get("obligation_id")
            ),
            "url": _clean_text(item.get("url"), limit=500),
            "domain": _clean_token(item.get("domain"), limit=160),
            "title": _clean_text(item.get("title"), limit=220),
            "source_class_hint": _clean_token(
                item.get("source_class_hint") or item.get("source_class")
            ),
            "candidate_kind": _clean_token(item.get("candidate_kind")),
            "custody_status": _clean_token(item.get("custody_status")),
        }
    )
    for field_name in (
        "fetched",
        "read",
        "evidence_ledger_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "semantic_coverage",
        "final_evidence",
        "evidence_bound",
        "citation_bound",
        "answer_value_bound",
        "full_component_success",
        "partial_user_answer_candidate",
        "final_answer_allowed",
        "author_payload_ready",
    ):
        ref[field_name] = False
    return ref


def _candidate_ref_binding_eligible(candidate: Mapping[str, Any]) -> bool:
    disposition = _clean_token(candidate.get("fact_disposition"))
    return (
        disposition in {"accepted", "partially_accepted"}
        and candidate.get("final_evidence_eligible") is True
    )


def _component_custody_binding_blockers(custody: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    obligations = _sequence_of_mappings(
        custody.get("component_source_obligation_refs")
    )
    candidates = _sequence_of_mappings(custody.get("component_candidate_link_refs"))
    if obligations and not candidates:
        blockers.append("no_candidate")
        blockers.append("missing_component_source_candidate")
    for gap in _sequence_of_mappings(custody.get("component_custody_gap_refs")):
        gap_type = _clean_token(gap.get("gap_type"))
        if gap_type:
            blockers.append(gap_type)
    if candidates:
        if any(candidate.get("fetched") is not True for candidate in candidates):
            blockers.append("candidate_not_fetched")
        if any(candidate.get("read") is not True for candidate in candidates):
            blockers.append("candidate_not_read")
        if any(
            candidate.get("evidence_ledger_admitted") is not True
            for candidate in candidates
        ):
            blockers.append("candidate_not_admitted_by_evidenceledger")
        if any(
            candidate.get("citation_eligible") is not True for candidate in candidates
        ):
            blockers.append("citation_not_eligible")
    if obligations and custody.get("source_obligation_satisfied") != "satisfied":
        blockers.append("source_obligation_unsatisfied")
    return blockers


def _custody_status(
    statuses: Sequence[str],
    requirements: Sequence[Mapping[str, Any]],
    ledger: Mapping[str, Any],
) -> str:
    if not ledger:
        return AnswerComponentCustodyStatus.LEDGER_ABSENT.value
    if not requirements:
        return AnswerComponentCustodyStatus.NO_COMPONENT_REQUIREMENT.value
    if all(status == "satisfied" for status in statuses):
        return AnswerComponentCustodyStatus.SATISFIED.value
    if any(status == "partially_satisfied" for status in statuses):
        return AnswerComponentCustodyStatus.PARTIALLY_SATISFIED.value
    if any(status == "unsatisfied" for status in statuses):
        return AnswerComponentCustodyStatus.UNSATISFIED.value
    return AnswerComponentCustodyStatus.UNKNOWN.value


def _compatibility_status(
    requirements: Sequence[Mapping[str, Any]],
    *,
    marker: str,
) -> str:
    relevant = [
        item
        for item in requirements
        if _contains_marker(item.get("required_source_class"), (marker,))
        or _contains_marker(item.get("requirement_kind"), (marker,))
    ]
    if not relevant:
        return "unknown"
    if all(_clean_token(item.get("status")) == "satisfied" for item in relevant):
        return "compatible"
    if any(_clean_token(item.get("status")) == "unsatisfied" for item in relevant):
        return "incompatible"
    return "unknown"


def _readability_status(candidates: Sequence[Mapping[str, Any]]) -> str:
    statuses = [
        _clean_token(item.get("readable_status")) for item in candidates if item
    ]
    if not statuses:
        return "unknown"
    if all(status in {"readable", "ok"} for status in statuses):
        return "readable"
    if any(status in {"unreadable", "failed"} for status in statuses):
        return "unreadable"
    return "unknown"


def _blocker_reasons(
    *,
    work: Mapping[str, Any],
    custody: Mapping[str, Any],
    semantic_coverage: Mapping[str, Any],
    binding: Mapping[str, Any],
    sufficiency: Mapping[str, Any],
    search_judgment: Mapping[str, Any],
) -> list[str]:
    reasons = list(binding.get("blocker_reasons") or [])
    if work.get("execution_status") == "not_started":
        reasons.append("subordinate_search_execution_not_started")
    if custody.get("source_obligation_satisfied") != "satisfied":
        reasons.append("ledger_source_obligation_not_satisfied")
    if semantic_coverage.get("coverage_status") != "satisfied":
        reasons.append("semantic_component_coverage_not_satisfied")
    if sufficiency.get("final_answer_allowed") is False:
        reasons.append("sufficiency_blocks_final_answer")
    if _clean_token(search_judgment.get("decision")) in {
        "continue_search",
        "continue_targeted_search",
    }:
        reasons.append("search_judgment_requires_more_work")
    return list(dict.fromkeys(reason for reason in reasons if reason))


def _requirement_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "requirement_id": _clean_token(
                item.get("requirement_id") or item.get("obligation_id")
            ),
            "requirement_kind": _clean_token(
                item.get("requirement_kind") or item.get("kind")
            ),
            "status": _clean_token(item.get("status")),
            "reason": _clean_text(item.get("reason")),
        }
    )


def _gap_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "gap_type": _clean_token(item.get("gap_type")),
            "requirement_id": _clean_token(item.get("requirement_id")),
            "candidate_id": _clean_token(item.get("candidate_id")),
            "reason": _clean_text(item.get("reason")),
        }
    )


def _blocked_summary_ref(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not summary:
        return {}
    return _without_empty(
        {
            "available": True,
            "schema_version": _clean_token(summary.get("schema_version")),
            "packet_id": _clean_token(summary.get("packet_id")),
            "status": _clean_token(summary.get("status")),
            "blocked_fap": _optional_bool(summary.get("blocked_fap")),
            "digest": _stable_digest(summary),
        }
    )


def _matches_component(component_id: str, item: Mapping[str, Any]) -> bool:
    component = _clean_token(component_id)
    if not component:
        return False
    normalized = _normalize(component)
    candidate_values = [
        item.get("component_id"),
        item.get("answer_component_id"),
        item.get("search_work_component_id"),
        item.get("requirement_id"),
        item.get("obligation_id"),
        item.get("custody_requirement_id"),
        item.get("origin_ref"),
        item.get("source_ref"),
    ]
    return any(normalized in _normalize(value) for value in candidate_values if value)


def _stable_digest(value: Any) -> str:
    safe = _json_safe(value)
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":"))
    return "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()


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


def _text_list(value: Any) -> list[str]:
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


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _first_bool(*values: Any) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None


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


def _contains_marker(value: Any, markers: Sequence[str]) -> bool:
    text = _normalize(value)
    return any(marker in text for marker in markers)


def _normalize(value: Any) -> str:
    return str(value or "").strip().casefold().replace("_", "-")


__all__ = [
    "ANSWER_CONTRACT_AUTHORITY_MAP_OWNER",
    "ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION",
    "ANSWER_CONTRACT_AUTHORITY_MAP_TRACE_KEY",
    "AnswerComponentBindingStatus",
    "AnswerComponentCustodyStatus",
    "AnswerComponentWorkStatus",
    "AnswerContractAuthorHandoffStatus",
    "AnswerContractAuthorityMap",
    "AnswerContractComponentAuthority",
    "AnswerContractSufficiencyStatus",
    "build_answer_contract_authority_map",
]
