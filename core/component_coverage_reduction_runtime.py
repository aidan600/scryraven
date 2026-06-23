"""Canonical ComponentCoverageRecord reduction runtime for AG-SEM-07.

This module is the third canonical semantic authority bridge. It provides the
bounded, pure helpers a RunKernel/RunAuthority-authorized reducer uses to reduce
exactly one validated passive ``ComponentCoverageRecord`` proposal into canonical
RunKernel-owned component coverage state.

It reduces coverage only. It does not consume coverage in Sufficiency, accept or
apply contract amendments, decide SearchJudgment, activate QueryPlan/SearchWorkPlan,
authorize follow-up, create Author input, create a FinalAnswerPacket, or perform
any provider, search, retrieval, fetch/read, citation, or live validation behavior.

The helpers here are imported by ``core.run_kernel``; to keep the import graph
acyclic this module must not import ``core.run_kernel``.
"""

from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_record import (
    COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION,
    ComponentCoverageRecord,
    ContentReferenceCoverageBinding,
    CoverageLineage,
    CoverageState,
    EvidenceLedgerSnapshotBinding,
    SemanticObservationCoverageRef,
)
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION

COMPONENT_COVERAGE_REDUCTION_SCHEMA_VERSION = "component_coverage_reduction_ag_sem_07_v1"
COMPONENT_COVERAGE_REDUCTION_STAGE = "component_coverage_reduction"
COMPONENT_COVERAGE_REDUCTION_REASON = (
    "component_coverage_reduction_from_authorized_passive_record"
)
COMPONENT_COVERAGE_REDUCTION_TRACE_KEY = "component_coverage_reduction"
COMPONENT_COVERAGE_REDUCTION_OWNER = "RunKernel.ComponentCoverageReduction"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "page_corpus",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "secret",
        "token",
        "unbounded_text",
    }
)

_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "accepted_amendment",
        "author_input",
        "canonical_coverage",
        "contract_amendment_record",
        "coverage_decision_applied",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "search_work_plan_activation",
        "sufficiency_decision_applied",
        "sufficiency_judgment",
    }
)

_COVERAGE_UNSAFE_IF_TRUE = (
    "accepted_authority",
    "canonical_state",
    "coverage_decision",
    "component_satisfied",
    "final_answer_authority",
    "author_input_created",
    "runtime_behavior_changed",
    "accepted_contract_amendment",
    "final_answer_decision",
    "answer_decision",
    "sufficiency_decision",
    "sufficiency_judgment",
    "final_answer_packet",
    "author_input",
    "canonical_coverage",
    "contract_amendment_record",
    "amendment_created",
    "followup_authorized",
    "search_judgment_decided",
    "query_plan_activated",
    "search_work_plan_activated",
)

_COVERAGE_UNSAFE_IF_FALSE = (
    "passive",
)

_LINEAGE_UNSAFE_IF_TRUE = (
    "reducer_consumed",
    "runtime_consumed",
)

_REQUIRED_INPUT_KEYS = (
    "coverage_record_id",
    "coverage_record_digest",
    "accepted_contract_digest",
    "accepted_contract_version",
    "answer_component_id",
    "component_revision",
    "component_digest",
)


class ComponentCoverageReductionError(ValueError):
    """Raised when a passive coverage record cannot be reduced to canonical state."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _digest_json(value: Any) -> str:
    return sha256(
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def evidence_ledger_projection_digest(evidence_ledger_projection: Mapping[str, Any]) -> str:
    """Deterministic digest of an EvidenceLedger projection for binding validation."""

    return sha256(repr(_json_safe(evidence_ledger_projection)).encode("utf-8")).hexdigest()


def _ledger_snapshot_id(run_id: str, ledger_digest: str) -> str:
    clean_run = _clean_token(run_id, limit=120) or "run"
    clean_digest = _clean_token(ledger_digest, limit=128) or ""
    return f"evidence-ledger:{clean_run}:{clean_digest[:32]}"


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return out


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _normalize_evidence_ref(value: Any) -> str | None:
    text = _clean_token(value, limit=200)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _require_match(condition: bool, message: str) -> None:
    if not condition:
        raise ComponentCoverageReductionError(message)


def _reject_unsafe_coverage_posture(raw_record: Mapping[str, Any]) -> None:
    """Reject authority-tainted payloads before reconstruction normalizes them away."""

    if raw_record.get("passive") is False:
        raise ComponentCoverageReductionError(
            "passive component coverage record must remain passive"
        )
    if raw_record.get("canonical_state") is True:
        raise ComponentCoverageReductionError(
            "passive coverage record cannot already be canonical state"
        )
    if raw_record.get("runtime_behavior_changed") is True:
        raise ComponentCoverageReductionError(
            "passive coverage record must not have changed runtime behavior"
        )
    for key in _COVERAGE_UNSAFE_IF_FALSE:
        if key in raw_record and raw_record.get(key) is False:
            raise ComponentCoverageReductionError(
                f"passive coverage record has unsafe posture: {key}=False"
            )
    for key in _COVERAGE_UNSAFE_IF_TRUE:
        if raw_record.get(key) is True:
            raise ComponentCoverageReductionError(
                f"passive coverage record has closed authority posture: {key}"
            )
    lineage = raw_record.get("lineage")
    if isinstance(lineage, Mapping):
        for key in _LINEAGE_UNSAFE_IF_TRUE:
            if lineage.get(key) is True:
                raise ComponentCoverageReductionError(
                    f"passive coverage record lineage has unsafe consumption posture: {key}"
                )


def _reconstruct_observation_ref(payload: Mapping[str, Any]) -> SemanticObservationCoverageRef:
    return SemanticObservationCoverageRef(
        observation_id=str(payload.get("observation_id") or ""),
        observation_digest=str(payload.get("observation_digest") or ""),
        answer_component_id=str(payload.get("answer_component_id") or ""),
        component_revision=str(payload.get("component_revision") or ""),
        component_contract_digest=str(payload.get("component_contract_digest") or ""),
        support_status=str(payload.get("support_status") or "unknown"),
        support_posture=str(payload.get("support_posture") or "direct"),
        content_refs=tuple(_text_list(payload.get("content_refs"))),
        accepted=bool(payload.get("accepted", True)),
        semantic_observation_schema_version=_clean_token(payload.get("semantic_observation_schema_version")),
    )


def _reconstruct_content_binding(payload: Mapping[str, Any]) -> ContentReferenceCoverageBinding:
    return ContentReferenceCoverageBinding(
        content_ref_id=str(payload.get("content_ref_id") or ""),
        content_digest=str(payload.get("content_digest") or ""),
        evidence_ref_id=str(payload.get("evidence_ref_id") or ""),
        answer_component_id=str(payload.get("answer_component_id") or ""),
        component_revision=str(payload.get("component_revision") or ""),
        component_contract_digest=str(payload.get("component_contract_digest") or ""),
        answer_bearing=bool(payload.get("answer_bearing", True)),
        availability_status=str(payload.get("availability_status") or "unknown"),
        content_reference_schema_version=_clean_token(payload.get("content_reference_schema_version")),
    )


def _reconstruct_lineage(payload: Mapping[str, Any] | None) -> CoverageLineage:
    lineage = _safe_mapping(payload)
    return CoverageLineage(
        created_by=str(lineage.get("created_by") or "ag-sem-03-passive-schema"),
        created_from=tuple(_text_list(lineage.get("created_from"), limit=180)),
        supersedes_record_id=lineage.get("supersedes_record_id"),
        parent_record_digest=lineage.get("parent_record_digest"),
    )


def _reconstruct_coverage_record(payload: Mapping[str, Any]) -> ComponentCoverageRecord:
    binding_dict = _safe_mapping(payload.get("evidence_ledger_binding"))
    if not binding_dict:
        raise ComponentCoverageReductionError("coverage record requires evidence_ledger_binding")
    try:
        ledger_binding = EvidenceLedgerSnapshotBinding(
            ledger_snapshot_id=str(binding_dict.get("ledger_snapshot_id") or ""),
            ledger_schema_version=str(binding_dict.get("ledger_schema_version") or ""),
            ledger_digest=str(binding_dict.get("ledger_digest") or ""),
            custody_status=str(binding_dict.get("custody_status") or "unknown"),
            source_requirement_ids=tuple(_text_list(binding_dict.get("source_requirement_ids"))),
            ledger_observation_refs=tuple(_text_list(binding_dict.get("ledger_observation_refs"))),
            version_validity=str(binding_dict.get("version_validity") or "valid"),
        )
        observation_refs = tuple(
            _reconstruct_observation_ref(_safe_mapping(ref))
            for ref in payload.get("accepted_observation_refs") or ()
            if isinstance(ref, Mapping)
        )
        content_bindings = tuple(
            _reconstruct_content_binding(_safe_mapping(ref))
            for ref in payload.get("content_reference_bindings") or ()
            if isinstance(ref, Mapping)
        )
        return ComponentCoverageRecord(
            record_id=str(payload.get("record_id") or ""),
            run_id=str(payload.get("run_id") or ""),
            request_id=str(payload.get("request_id") or ""),
            request_digest=str(payload.get("request_digest") or ""),
            accepted_contract_version=str(payload.get("accepted_contract_version") or ""),
            accepted_contract_digest=str(payload.get("accepted_contract_digest") or ""),
            answer_component_id=str(payload.get("answer_component_id") or ""),
            component_revision=str(payload.get("component_revision") or ""),
            component_digest=str(payload.get("component_digest") or ""),
            evidence_ledger_binding=ledger_binding,
            coverage_state=str(payload.get("coverage_state") or "unassessed"),
            semantic_support_status=str(payload.get("semantic_support_status") or "unassessed"),
            support_posture=str(payload.get("support_posture") or "direct"),
            derived_support_status=str(payload.get("derived_support_status") or "not_applicable"),
            source_obligation_status=str(payload.get("source_obligation_status") or "unknown"),
            content_availability_status=str(payload.get("content_availability_status") or "unknown"),
            evidence_custody_status=str(payload.get("evidence_custody_status") or "unknown"),
            version_validity=str(payload.get("version_validity") or "valid"),
            accepted_observation_refs=observation_refs,
            content_reference_bindings=content_bindings,
            evidence_basis=tuple(payload.get("evidence_basis") or ()),
            normalization_posture=str(payload.get("normalization_posture") or "not_applicable"),
            assumption_posture=str(payload.get("assumption_posture") or "not_applicable"),
            conflict_posture=str(payload.get("conflict_posture") or "unknown"),
            currentness_posture=str(payload.get("currentness_posture") or "unknown"),
            remaining_unknowns=tuple(_text_list(payload.get("remaining_unknowns"), limit=400)),
            required_caveats=tuple(_text_list(payload.get("required_caveats"), limit=400)),
            prohibited_upgrades=tuple(_text_list(payload.get("prohibited_upgrades"), limit=400)),
            followup_need=str(payload.get("followup_need") or "unknown"),
            mode_budget_posture=str(payload.get("mode_budget_posture") or "unknown"),
            stale=bool(payload.get("stale")),
            diagnostic_score=payload.get("diagnostic_score"),
            lineage=_reconstruct_lineage(
                payload.get("lineage") if isinstance(payload.get("lineage"), Mapping) else None
            ),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
            schema_version=str(payload.get("schema_version") or COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION),
        )
    except (ValueError, TypeError) as exc:
        raise ComponentCoverageReductionError(f"invalid component coverage record payload: {exc}") from exc


def _accepted_component_index(accepted_contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for ref in accepted_contract.get("accepted_answer_component_refs") or ():
        if isinstance(ref, Mapping):
            component_id = _clean_token(ref.get("component_id"))
            if component_id:
                index[component_id] = ref
    return index


def _admission_index(
    admission_history: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for item in admission_history:
        mapping = _safe_mapping(item)
        observation_id = _clean_token(mapping.get("observation_id"))
        if observation_id:
            index[observation_id] = mapping
    return index


def _component_relevant_admissions(
    admission_history: Sequence[Mapping[str, Any]],
    *,
    answer_component_id: str,
    component_revision: str,
    component_digest: str,
) -> list[Mapping[str, Any]]:
    matches: list[Mapping[str, Any]] = []
    for item in admission_history:
        mapping = _safe_mapping(item)
        if mapping.get("answer_component_id") != answer_component_id:
            continue
        if _clean_token(mapping.get("component_revision")) != component_revision:
            continue
        if _clean_token(mapping.get("component_digest"), limit=128) != component_digest:
            continue
        matches.append(mapping)
    return matches


def _evidence_custody_refs(evidence_ledger_projection: Mapping[str, Any]) -> set[str]:
    allowed: set[str] = set()
    for record in evidence_ledger_projection.get("candidate_records") or ():
        if isinstance(record, Mapping):
            candidate_id = _normalize_evidence_ref(record.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for record in evidence_ledger_projection.get("custody_records") or ():
        if isinstance(record, Mapping):
            candidate_id = _normalize_evidence_ref(record.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for link in evidence_ledger_projection.get("requirement_links") or ():
        if isinstance(link, Mapping):
            candidate_id = _normalize_evidence_ref(link.get("candidate_id"))
            if candidate_id:
                allowed.add(candidate_id)
    for requirement in evidence_ledger_projection.get("source_requirements") or ():
        if isinstance(requirement, Mapping):
            for candidate_id in _text_list(requirement.get("linked_candidate_ids")):
                normalized = _normalize_evidence_ref(candidate_id)
                if normalized:
                    allowed.add(normalized)
    return allowed


def _requirement_ids_from_projection(projection: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for requirement in projection.get("source_requirements") or ():
        if isinstance(requirement, Mapping):
            requirement_id = _clean_token(requirement.get("requirement_id"))
            if requirement_id:
                ids.add(requirement_id)
    return ids


def _observation_ids_from_projection(projection: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for ref in projection.get("observation_refs") or ():
        if isinstance(ref, Mapping):
            observation_id = _clean_token(ref.get("observation_id"))
            if observation_id:
                ids.add(observation_id)
    return ids


def _relevant_custody_gaps(
    projection: Mapping[str, Any],
    binding: EvidenceLedgerSnapshotBinding,
    cited_evidence_refs: Sequence[str],
) -> list[Mapping[str, Any]]:
    relevant_requirements = set(binding.source_requirement_ids)
    relevant_observations = set(binding.ledger_observation_refs)
    normalized_evidence = {
        normalized
        for ref in cited_evidence_refs
        if (normalized := _normalize_evidence_ref(ref))
    }
    gaps: list[Mapping[str, Any]] = []
    for gap in projection.get("custody_gaps") or ():
        if not isinstance(gap, Mapping):
            continue
        requirement_id = _clean_token(gap.get("requirement_id"))
        candidate_id = _normalize_evidence_ref(gap.get("candidate_id"))
        observation_id = _clean_token(gap.get("observation_id"))
        if requirement_id and requirement_id in relevant_requirements:
            gaps.append(gap)
            continue
        if candidate_id and candidate_id in normalized_evidence:
            gaps.append(gap)
            continue
        if observation_id and observation_id in relevant_observations:
            gaps.append(gap)
    return gaps


def _validate_evidence_ledger_binding(
    binding: EvidenceLedgerSnapshotBinding,
    *,
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    cited_evidence_refs: Sequence[str],
    coverage_state: CoverageState,
) -> None:
    projection = _safe_mapping(evidence_ledger_projection)
    if not projection:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires an EvidenceLedger projection"
        )
    computed_digest = evidence_ledger_projection_digest(projection)
    expected_snapshot_id = _ledger_snapshot_id(run_id, computed_digest)
    projection_schema = _clean_token(projection.get("schema_version"))
    _require_match(
        binding.ledger_schema_version == EVIDENCE_LEDGER_SCHEMA_VERSION,
        "evidence ledger binding schema version does not match canonical EvidenceLedger schema",
    )
    _require_match(
        projection_schema == EVIDENCE_LEDGER_SCHEMA_VERSION,
        "EvidenceLedger projection schema version is not canonical",
    )
    _require_match(
        binding.ledger_digest == computed_digest,
        "evidence ledger binding digest does not match current EvidenceLedger projection digest",
    )
    _require_match(
        binding.ledger_snapshot_id == expected_snapshot_id,
        "evidence ledger binding snapshot id does not match canonical snapshot binding",
    )
    requirement_ids = _requirement_ids_from_projection(projection)
    foreign_requirements = sorted(
        req for req in binding.source_requirement_ids if req not in requirement_ids
    )
    if foreign_requirements:
        raise ComponentCoverageReductionError(
            "evidence ledger binding cites unknown source requirements: "
            + ", ".join(foreign_requirements)
        )
    observation_ids = _observation_ids_from_projection(projection)
    foreign_observations = sorted(
        obs for obs in binding.ledger_observation_refs if obs not in observation_ids
    )
    if foreign_observations:
        raise ComponentCoverageReductionError(
            "evidence ledger binding cites unknown ledger observation refs: "
            + ", ".join(foreign_observations)
        )
    if coverage_state is CoverageState.SATISFIED:
        relevant_gaps = _relevant_custody_gaps(projection, binding, cited_evidence_refs)
        if relevant_gaps:
            gap_types = ", ".join(
                sorted(
                    {
                        str(_clean_token(gap.get("gap_type")) or "unknown")
                        for gap in relevant_gaps
                    }
                )
            )
            raise ComponentCoverageReductionError(
                "satisfied coverage cannot depend on EvidenceLedger custody gaps "
                f"relevant to linked requirements or evidence refs: {gap_types}"
            )


def _content_ref_owner_observation_ids(
    accepted_observation_refs: Sequence[SemanticObservationCoverageRef],
    content_ref_id: str,
) -> set[str]:
    owners: set[str] = set()
    for ref in accepted_observation_refs:
        if content_ref_id in ref.content_refs:
            owners.add(ref.observation_id)
    return owners


def _admitted_content_digest(
    admission: Mapping[str, Any],
    content_ref_id: str,
) -> str | None:
    for record in admission.get("content_ref_records") or ():
        if isinstance(record, Mapping) and record.get("content_ref_id") == content_ref_id:
            return _clean_token(record.get("content_digest"), limit=128)
    return None


def _coverage_reduction_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "run_id": state_core.get("run_id"),
        "request_id": state_core.get("request_id"),
        "coverage_record_id": state_core.get("coverage_record_id"),
        "coverage_record_digest": state_core.get("coverage_record_digest"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "accepted_contract_digest": state_core.get("accepted_contract_digest"),
        "answer_component_id": state_core.get("answer_component_id"),
        "component_revision": state_core.get("component_revision"),
        "component_digest": state_core.get("component_digest"),
        "coverage_state": state_core.get("coverage_state"),
        "semantic_support_status": state_core.get("semantic_support_status"),
        "support_posture": state_core.get("support_posture"),
        "derived_support_status": state_core.get("derived_support_status"),
        "source_obligation_status": state_core.get("source_obligation_status"),
        "content_availability_status": state_core.get("content_availability_status"),
        "evidence_custody_status": state_core.get("evidence_custody_status"),
        "version_validity": state_core.get("version_validity"),
        "accepted_observation_refs": state_core.get("accepted_observation_refs"),
        "content_reference_bindings": state_core.get("content_reference_bindings"),
        "evidence_basis": state_core.get("evidence_basis"),
        "normalization_posture": state_core.get("normalization_posture"),
        "assumption_posture": state_core.get("assumption_posture"),
        "conflict_posture": state_core.get("conflict_posture"),
        "currentness_posture": state_core.get("currentness_posture"),
        "remaining_unknowns": state_core.get("remaining_unknowns"),
        "required_caveats": state_core.get("required_caveats"),
        "prohibited_upgrades": state_core.get("prohibited_upgrades"),
        "followup_need": state_core.get("followup_need"),
        "mode_budget_posture": state_core.get("mode_budget_posture"),
        "stale": state_core.get("stale"),
        "evidence_ledger_binding": state_core.get("evidence_ledger_binding"),
        "lineage": lineage,
    }


def build_component_coverage_reduction_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    coverage_payload: Mapping[str, Any] | None,
    accepted_contract: Mapping[str, Any] | None,
    admission_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any] | None,
    existing_coverage_record_ids: Sequence[str] = (),
    existing_coverage_record_digests: Sequence[str] = (),
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Validate one passive coverage record and build canonical reduction state."""

    clean_action_id = _clean_token(action_id, limit=200)
    if not clean_action_id:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires an authorized action id"
        )
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_run_id or not clean_request_id:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires run_id and request_id"
        )

    contract = _safe_mapping(accepted_contract)
    if not contract or contract.get("canonical_state") is not True:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires an accepted initial answer contract"
        )
    accepted_contract_version = _clean_token(contract.get("accepted_contract_version"))
    accepted_contract_digest = _clean_token(contract.get("accepted_contract_digest"), limit=128)
    if not accepted_contract_version or not accepted_contract_digest:
        raise ComponentCoverageReductionError(
            "accepted initial answer contract is missing required version/digest bindings"
        )
    component_index = _accepted_component_index(contract)
    if not component_index:
        raise ComponentCoverageReductionError(
            "accepted initial answer contract has no accepted answer component refs"
        )

    raw_payload = coverage_payload if isinstance(coverage_payload, Mapping) else {}
    raw_record_dict = raw_payload.get("component_coverage_record")
    raw_record_dict = dict(raw_record_dict) if isinstance(raw_record_dict, Mapping) else {}
    if not raw_record_dict:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires a component_coverage_record proposal payload"
        )

    _reject_unsafe_coverage_posture(raw_record_dict)

    payload = _safe_mapping(raw_payload)
    record_dict = dict(raw_record_dict)
    forbidden = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise ComponentCoverageReductionError(
            "coverage payload includes closed authority fields: " + ", ".join(forbidden)
        )

    record = _reconstruct_coverage_record(record_dict)

    if record.passive is not True or record.canonical_state is True:
        raise ComponentCoverageReductionError(
            "component coverage record must be a passive, non-canonical proposal"
        )
    if record.runtime_behavior_changed is True:
        raise ComponentCoverageReductionError(
            "component coverage record must not have changed runtime behavior"
        )

    recomputed_digest = record.record_digest
    declared_digest = _clean_token(record_dict.get("record_digest"), limit=128)
    if declared_digest and declared_digest != recomputed_digest:
        raise ComponentCoverageReductionError(
            "stale coverage payload: coverage record digest does not match payload content"
        )

    inputs = dict(action_inputs or {})
    missing_inputs = [key for key in _REQUIRED_INPUT_KEYS if not _clean_token(inputs.get(key), limit=200)]
    if missing_inputs:
        raise ComponentCoverageReductionError(
            "authorized action must bind: " + ", ".join(missing_inputs)
        )
    bound_request_id = _clean_token(inputs.get("request_id"))
    if bound_request_id and bound_request_id != clean_request_id:
        raise ComponentCoverageReductionError(
            "authorized action request_id binding does not match the request"
        )

    _require_match(
        _clean_token(inputs.get("coverage_record_id")) == record.record_id,
        "action coverage_record_id binding does not match the coverage record id",
    )
    _require_match(
        _clean_token(inputs.get("coverage_record_digest"), limit=128) == recomputed_digest,
        "action coverage_record_digest binding does not match the recomputed coverage record digest",
    )
    _require_match(
        _clean_token(inputs.get("accepted_contract_digest"), limit=128) == accepted_contract_digest,
        "action accepted_contract_digest binding does not match the accepted contract digest",
    )
    _require_match(
        _clean_token(inputs.get("accepted_contract_version")) == accepted_contract_version,
        "action accepted_contract_version binding does not match the accepted contract version",
    )
    _require_match(
        _clean_token(inputs.get("answer_component_id")) == record.answer_component_id,
        "action answer_component_id binding does not match the coverage record component",
    )

    accepted_component = component_index.get(record.answer_component_id)
    if accepted_component is None:
        raise ComponentCoverageReductionError(
            "coverage record answer_component_id is not an accepted answer component ref"
        )
    accepted_component_revision = _clean_token(accepted_component.get("component_revision"))
    accepted_component_digest = _clean_token(accepted_component.get("component_digest"), limit=128)
    _require_match(
        _clean_token(inputs.get("component_revision")) == accepted_component_revision,
        "action component_revision binding does not match the accepted component revision",
    )
    _require_match(
        _clean_token(inputs.get("component_digest"), limit=128) == accepted_component_digest,
        "action component_digest binding does not match the accepted component digest",
    )
    _require_match(
        record.component_revision == accepted_component_revision,
        "coverage record component_revision does not match the accepted component revision",
    )
    _require_match(
        record.component_digest == accepted_component_digest,
        "coverage record component_digest does not match the accepted component digest",
    )
    _require_match(
        record.accepted_contract_version == accepted_contract_version,
        "coverage record accepted_contract_version does not match the accepted contract version",
    )
    _require_match(
        record.accepted_contract_digest == accepted_contract_digest,
        "coverage record accepted_contract_digest does not match the accepted contract digest",
    )

    relevant_admissions = _component_relevant_admissions(
        admission_history,
        answer_component_id=record.answer_component_id,
        component_revision=accepted_component_revision or "",
        component_digest=accepted_component_digest or "",
    )
    if not relevant_admissions:
        raise ComponentCoverageReductionError(
            "component coverage reduction requires at least one admitted SemanticObservation "
            "for the answer component"
        )

    admission_by_id = _admission_index(admission_history)
    admitted_observation_inputs: list[dict[str, Any]] = []
    cited_evidence_refs: list[str] = []

    for obs_ref in record.accepted_observation_refs:
        admission = admission_by_id.get(obs_ref.observation_id)
        if admission is None:
            raise ComponentCoverageReductionError(
                f"semantic observation ref {obs_ref.observation_id} is not admitted"
            )
        admitted_digest = _clean_token(admission.get("observation_digest"), limit=128)
        if obs_ref.observation_digest != admitted_digest:
            raise ComponentCoverageReductionError(
                f"semantic observation ref {obs_ref.observation_id} has stale observation digest"
            )
        if admission.get("answer_component_id") != record.answer_component_id:
            raise ComponentCoverageReductionError(
                f"admitted observation {obs_ref.observation_id} is bound to another component"
            )
        if _clean_token(admission.get("component_revision")) != record.component_revision:
            raise ComponentCoverageReductionError(
                f"admitted observation {obs_ref.observation_id} is bound to another component revision"
            )
        if _clean_token(admission.get("component_digest"), limit=128) != record.component_digest:
            raise ComponentCoverageReductionError(
                f"admitted observation {obs_ref.observation_id} component digest mismatch"
            )
        admitted_content_ids = set(_text_list(admission.get("content_refs")))
        for content_ref_id in obs_ref.content_refs:
            if content_ref_id not in admitted_content_ids:
                raise ComponentCoverageReductionError(
                    f"semantic observation ref {obs_ref.observation_id} cites unadmitted content ref "
                    f"{content_ref_id}"
                )
        cited_evidence_refs.extend(_text_list(admission.get("evidence_refs")))
        admitted_observation_inputs.append(
            {
                "observation_id": obs_ref.observation_id,
                "answer_component_id": record.answer_component_id,
                "component_revision": record.component_revision,
                "component_contract_digest": record.component_digest,
            }
        )

    admitted_content_inputs: list[dict[str, Any]] = []
    allowed_evidence_refs = _evidence_custody_refs(_safe_mapping(evidence_ledger_projection))

    for binding in record.content_reference_bindings:
        owner_ids = _content_ref_owner_observation_ids(
            record.accepted_observation_refs,
            binding.content_ref_id,
        )
        if not owner_ids:
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} is not cited by any accepted observation ref"
            )
        backing_admissions = [
            admission_by_id[owner_id]
            for owner_id in owner_ids
            if owner_id in admission_by_id
        ]
        if len(backing_admissions) != len(owner_ids):
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} is not backed by an admitted SemanticObservation"
            )
        admitted_digest = None
        for admission in backing_admissions:
            digest = _admitted_content_digest(admission, binding.content_ref_id)
            if digest is None:
                raise ComponentCoverageReductionError(
                    f"content ref {binding.content_ref_id} is not backed by admitted content ref records"
                )
            if admitted_digest is None:
                admitted_digest = digest
            elif admitted_digest != digest:
                raise ComponentCoverageReductionError(
                    f"content ref {binding.content_ref_id} has conflicting admitted content digests"
                )
        if admitted_digest != binding.content_digest:
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} content digest does not match admitted content"
            )
        if not _clean_token(binding.evidence_ref_id):
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} requires evidence_ref_id"
            )
        normalized_evidence = _normalize_evidence_ref(binding.evidence_ref_id)
        if not normalized_evidence or normalized_evidence not in allowed_evidence_refs:
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} cites evidence absent from EvidenceLedger custody"
            )
        evidence_bound = False
        for admission in backing_admissions:
            admission_evidence = {
                _normalize_evidence_ref(item)
                for item in _text_list(admission.get("evidence_refs"))
            }
            if normalized_evidence in admission_evidence:
                evidence_bound = True
                break
        if not evidence_bound:
            raise ComponentCoverageReductionError(
                f"content ref {binding.content_ref_id} evidence_ref_id is not bound through "
                "the admitting SemanticObservation"
            )
        admitted_content_inputs.append(
            {
                "content_ref_id": binding.content_ref_id,
                "answer_component_id": record.answer_component_id,
                "component_revision": record.component_revision,
                "component_contract_digest": record.component_digest,
            }
        )

    _validate_evidence_ledger_binding(
        record.evidence_ledger_binding,
        evidence_ledger_projection=_safe_mapping(evidence_ledger_projection),
        run_id=clean_run_id,
        cited_evidence_refs=cited_evidence_refs,
        coverage_state=record.coverage_state
        if isinstance(record.coverage_state, CoverageState)
        else CoverageState(str(record.coverage_state)),
    )

    validation = record.validate(
        observations=admitted_observation_inputs,
        content_references=admitted_content_inputs,
    )
    if not validation.ok:
        raise ComponentCoverageReductionError(
            "component coverage record failed validation: " + "; ".join(validation.errors)
        )

    if record.record_id in {_clean_token(item) for item in existing_coverage_record_ids if item}:
        raise ComponentCoverageReductionError(
            f"component coverage record {record.record_id} is already reduced"
        )
    if recomputed_digest in {
        _clean_token(item, limit=128) for item in existing_coverage_record_digests if item
    }:
        raise ComponentCoverageReductionError("component coverage record digest is already reduced")

    record_safe = record.to_dict(include_validation=False)
    lineage = {
        "created_by": COMPONENT_COVERAGE_REDUCTION_OWNER,
        "created_from": [
            "passive_component_coverage_record",
            "accepted_initial_answer_contract",
            "admitted_semantic_observation",
        ],
        "reducer_action_id": clean_action_id,
        "parent_coverage_record_digest": recomputed_digest,
        "accepted_contract_digest": accepted_contract_digest,
    }
    state_core: dict[str, Any] = {
        "schema_version": COMPONENT_COVERAGE_REDUCTION_SCHEMA_VERSION,
        "owner": COMPONENT_COVERAGE_REDUCTION_OWNER,
        "trace_key": COMPONENT_COVERAGE_REDUCTION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "coverage_record_id": record.record_id,
        "coverage_record_digest": recomputed_digest,
        "accepted_contract_version": accepted_contract_version,
        "accepted_contract_digest": accepted_contract_digest,
        "answer_component_id": record.answer_component_id,
        "component_revision": record.component_revision,
        "component_digest": record.component_digest,
        "coverage_state": record_safe.get("coverage_state"),
        "semantic_support_status": record_safe.get("semantic_support_status"),
        "support_posture": record_safe.get("support_posture"),
        "derived_support_status": record_safe.get("derived_support_status"),
        "source_obligation_status": record_safe.get("source_obligation_status"),
        "content_availability_status": record_safe.get("content_availability_status"),
        "evidence_custody_status": record_safe.get("evidence_custody_status"),
        "version_validity": record_safe.get("version_validity"),
        "accepted_observation_refs": record_safe.get("accepted_observation_refs", []),
        "content_reference_bindings": record_safe.get("content_reference_bindings", []),
        "evidence_basis": record_safe.get("evidence_basis", []),
        "normalization_posture": record_safe.get("normalization_posture"),
        "assumption_posture": record_safe.get("assumption_posture"),
        "conflict_posture": record_safe.get("conflict_posture"),
        "currentness_posture": record_safe.get("currentness_posture"),
        "remaining_unknowns": record_safe.get("remaining_unknowns", []),
        "required_caveats": record_safe.get("required_caveats", []),
        "prohibited_upgrades": record_safe.get("prohibited_upgrades", []),
        "followup_need": record_safe.get("followup_need"),
        "mode_budget_posture": record_safe.get("mode_budget_posture"),
        "stale": bool(record.stale),
        "evidence_ledger_binding": record_safe.get("evidence_ledger_binding", {}),
        "lineage": lineage,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "amendment_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    coverage_reduction_digest = _digest_json(_coverage_reduction_digest_payload(state_core))
    return {**state_core, "coverage_reduction_digest": coverage_reduction_digest}


def build_component_coverage_reduction_projection(
    *,
    coverage_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical coverage state with no raw or private data."""

    return {
        "owner": COMPONENT_COVERAGE_REDUCTION_OWNER,
        "schema_version": coverage_state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": coverage_state.get("run_id"),
        "request_id": coverage_state.get("request_id"),
        "authorized_action_id": coverage_state.get("authorized_action_id"),
        "coverage_record_id": coverage_state.get("coverage_record_id"),
        "coverage_record_digest": coverage_state.get("coverage_record_digest"),
        "coverage_reduction_digest": coverage_state.get("coverage_reduction_digest"),
        "accepted_contract_version": coverage_state.get("accepted_contract_version"),
        "accepted_contract_digest": coverage_state.get("accepted_contract_digest"),
        "answer_component_id": coverage_state.get("answer_component_id"),
        "component_revision": coverage_state.get("component_revision"),
        "component_digest": coverage_state.get("component_digest"),
        "coverage_state": coverage_state.get("coverage_state"),
        "semantic_support_status": coverage_state.get("semantic_support_status"),
        "support_posture": coverage_state.get("support_posture"),
        "derived_support_status": coverage_state.get("derived_support_status"),
        "source_obligation_status": coverage_state.get("source_obligation_status"),
        "content_availability_status": coverage_state.get("content_availability_status"),
        "evidence_custody_status": coverage_state.get("evidence_custody_status"),
        "version_validity": coverage_state.get("version_validity"),
        "accepted_observation_refs": list(coverage_state.get("accepted_observation_refs", [])),
        "content_reference_bindings": list(coverage_state.get("content_reference_bindings", [])),
        "evidence_basis": list(coverage_state.get("evidence_basis", [])),
        "normalization_posture": coverage_state.get("normalization_posture"),
        "assumption_posture": coverage_state.get("assumption_posture"),
        "conflict_posture": coverage_state.get("conflict_posture"),
        "currentness_posture": coverage_state.get("currentness_posture"),
        "remaining_unknowns": list(coverage_state.get("remaining_unknowns", [])),
        "required_caveats": list(coverage_state.get("required_caveats", [])),
        "prohibited_upgrades": list(coverage_state.get("prohibited_upgrades", [])),
        "followup_need": coverage_state.get("followup_need"),
        "mode_budget_posture": coverage_state.get("mode_budget_posture"),
        "stale": bool(coverage_state.get("stale")),
        "evidence_ledger_binding": dict(coverage_state.get("evidence_ledger_binding") or {}),
        "lineage": dict(coverage_state.get("lineage") or {}),
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "amendment_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }


__all__ = [
    "COMPONENT_COVERAGE_REDUCTION_OWNER",
    "COMPONENT_COVERAGE_REDUCTION_REASON",
    "COMPONENT_COVERAGE_REDUCTION_SCHEMA_VERSION",
    "COMPONENT_COVERAGE_REDUCTION_STAGE",
    "COMPONENT_COVERAGE_REDUCTION_TRACE_KEY",
    "ComponentCoverageReductionError",
    "build_component_coverage_reduction_projection",
    "build_component_coverage_reduction_state",
    "evidence_ledger_projection_digest",
]
