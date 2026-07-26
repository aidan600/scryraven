"""Canonical ContractAmendmentRecord admission runtime for AG-SEM-08.

This module is the fourth canonical semantic authority bridge. It provides the
bounded, pure helpers a RunKernel/RunAuthority-authorized reducer uses to admit
exactly one validated passive ``ContractAmendmentRecord`` proposal into canonical
RunKernel-owned contract-amendment admission state.

It admits amendment candidates only. It does not mutate the accepted initial
answer contract, mark coverage stale, apply coverage invalidation, consume
coverage in Sufficiency, decide SearchJudgment, activate QueryPlan/SearchWorkPlan,
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

from core.contract_amendment_record import (
    CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION,
    AffectedComponentRef,
    AmendmentLineage,
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    CoverageInvalidationCandidateRef,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    StaleCoverageCandidatePosture,
    UserConfirmationPosture,
    WeakeningPosture,
)

CONTRACT_AMENDMENT_ADMISSION_SCHEMA_VERSION = "contract_amendment_admission_ag_sem_08_v1"
CONTRACT_AMENDMENT_ADMISSION_STAGE = "contract_amendment_admission"
CONTRACT_AMENDMENT_ADMISSION_REASON = (
    "contract_amendment_admission_from_authorized_passive_record"
)
CONTRACT_AMENDMENT_ADMISSION_TRACE_KEY = "contract_amendment_admission"
CONTRACT_AMENDMENT_ADMISSION_OWNER = "RunKernel.ContractAmendmentAdmission"

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
        "component_coverage_record",
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

_AMENDMENT_UNSAFE_IF_TRUE = (
    "accepted_authority",
    "canonical_state",
    "contract_mutation_applied",
    "coverage_invalidation_applied",
    "runtime_behavior_changed",
    "coverage_decision",
    "component_satisfied",
    "final_answer_authority",
    "author_input_created",
    "accepted_contract_amendment",
    "final_answer_decision",
    "answer_decision",
    "sufficiency_decision",
    "sufficiency_judgment",
    "final_answer_packet",
    "author_input",
    "canonical_coverage",
    "component_coverage_record",
    "amendment_applied",
    "citation_eligible",
    "evidence_admitted",
    "followup_authorized",
    "search_judgment_decided",
    "query_plan_activated",
    "search_work_plan_activated",
    "scout_hints_are_evidence",
    "source_obligation_satisfied",
    "coverage_marked_stale",
    "initial_answer_contract_mutated",
)

_AMENDMENT_UNSAFE_IF_FALSE = ("passive",)

_LINEAGE_UNSAFE_IF_TRUE = ("runtime_consumed", "reducer_consumed")

_REQUIRED_INPUT_KEYS = (
    "amendment_record_id",
    "amendment_record_digest",
    "parent_contract_digest",
    "parent_contract_version",
    "accepted_contract_digest",
    "accepted_contract_version",
)

_REVISION_LINEAGE_FALSE_FLAGS = (
    "scout_hints_are_evidence",
    "citation_eligible",
    "source_obligation_satisfied",
    "evidence_admitted",
    "contract_mutation_applied",
)
_REVISION_FORBIDDEN_OPERATION_KINDS = (
    "mark_requirement_satisfied",
    "mark_source_obligation_satisfied",
    "resolve_slot",
)
_REVISION_ALLOWED_OPERATION_KINDS = (
    "add_caveat",
    "strengthen_source_obligation",
)


class ContractAmendmentAdmissionError(ValueError):
    """Raised when a passive amendment record cannot be admitted as canonical state."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


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
        raise ContractAmendmentAdmissionError(message)


def _coerce_enum(enum_class: type[Enum], value: Any, default: Enum) -> Enum:
    raw = value.value if isinstance(value, Enum) else value
    for item in enum_class:
        if item.value == raw:
            return item
    return default


def _reject_unsafe_amendment_posture(raw_record: Mapping[str, Any]) -> None:
    """Reject authority-tainted payloads before reconstruction normalizes them away."""

    if raw_record.get("passive") is False:
        raise ContractAmendmentAdmissionError(
            "passive contract amendment record must remain passive"
        )
    if raw_record.get("canonical_state") is True:
        raise ContractAmendmentAdmissionError(
            "passive amendment record cannot already be canonical state"
        )
    if raw_record.get("contract_mutation_applied") is True:
        raise ContractAmendmentAdmissionError(
            "passive amendment record must not have applied contract mutation"
        )
    if raw_record.get("coverage_invalidation_applied") is True:
        raise ContractAmendmentAdmissionError(
            "passive amendment record must not have applied coverage invalidation"
        )
    if raw_record.get("runtime_behavior_changed") is True:
        raise ContractAmendmentAdmissionError(
            "passive amendment record must not have changed runtime behavior"
        )
    for key in _AMENDMENT_UNSAFE_IF_FALSE:
        if key in raw_record and raw_record.get(key) is False:
            raise ContractAmendmentAdmissionError(
                f"passive amendment record has unsafe posture: {key}=False"
            )
    for key in _AMENDMENT_UNSAFE_IF_TRUE:
        if raw_record.get(key) is True:
            raise ContractAmendmentAdmissionError(
                f"passive amendment record has closed authority posture: {key}"
            )
    lineage = raw_record.get("lineage")
    if isinstance(lineage, Mapping):
        for key in _LINEAGE_UNSAFE_IF_TRUE:
            if lineage.get(key) is True:
                raise ContractAmendmentAdmissionError(
                    f"passive amendment record lineage has unsafe consumption posture: {key}"
                )
    for candidate in raw_record.get("candidate_invalidated_coverage_refs") or ():
        if not isinstance(candidate, Mapping):
            continue
        if candidate.get("represented_only") is False:
            raise ContractAmendmentAdmissionError(
                "candidate invalidated coverage refs must remain represented_only"
            )
        if candidate.get("coverage_invalidation_applied") is True:
            raise ContractAmendmentAdmissionError(
                "candidate invalidated coverage refs must not apply invalidation"
            )


def _reconstruct_trigger_refs(payload: Mapping[str, Any]) -> AmendmentTriggerRefs:
    return AmendmentTriggerRefs(
        semantic_observation_refs=tuple(_text_list(payload.get("semantic_observation_refs"))),
        evidence_refs=tuple(_text_list(payload.get("evidence_refs"))),
        sanitized_content_refs=tuple(_text_list(payload.get("sanitized_content_refs"))),
        component_coverage_refs=tuple(_text_list(payload.get("component_coverage_refs"))),
        gap_refs=tuple(_text_list(payload.get("gap_refs"))),
        conflict_refs=tuple(_text_list(payload.get("conflict_refs"))),
        currentness_refs=tuple(_text_list(payload.get("currentness_refs"))),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
    )


def _reconstruct_operation(payload: Mapping[str, Any]) -> AmendmentOperation:
    return AmendmentOperation(
        operation_id=str(payload.get("operation_id") or ""),
        operation_kind=_coerce_enum(
            AmendmentOperationKind,
            payload.get("operation_kind"),
            AmendmentOperationKind.ADD_CAVEAT,
        ),
        before_payload=_safe_mapping(payload.get("before_payload")),
        after_payload=_safe_mapping(payload.get("after_payload")),
        operation_payload=_safe_mapping(payload.get("operation_payload")),
        material_slot_kinds=tuple(_text_list(payload.get("material_slot_kinds"))),
        component_revision_changed=bool(payload.get("component_revision_changed")),
        component_digest_changed=bool(payload.get("component_digest_changed")),
        user_confirmation_required=bool(payload.get("user_confirmation_required")),
        labeled_scenario_treatment=bool(payload.get("labeled_scenario_treatment")),
        user_authority_ref=_clean_token(payload.get("user_authority_ref")),
        notes=tuple(_text_list(payload.get("notes"), limit=360)),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
    )


def _reconstruct_affected_component(payload: Mapping[str, Any]) -> AffectedComponentRef:
    return AffectedComponentRef(
        component_id=str(payload.get("component_id") or ""),
        component_revision=str(payload.get("component_revision") or ""),
        component_digest=str(payload.get("component_digest") or ""),
        relationship=str(payload.get("relationship") or "affected_component"),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
    )


def _reconstruct_coverage_candidate(payload: Mapping[str, Any]) -> CoverageInvalidationCandidateRef:
    return CoverageInvalidationCandidateRef(
        coverage_record_id=str(payload.get("coverage_record_id") or ""),
        coverage_record_digest=_clean_token(payload.get("coverage_record_digest"), limit=128),
        answer_component_id=_clean_token(payload.get("answer_component_id")),
        reason=_clean_text(payload.get("reason"), limit=360),
        represented_only=True,
    )


def _reconstruct_lineage(payload: Mapping[str, Any] | None) -> AmendmentLineage:
    lineage = _safe_mapping(payload)
    return AmendmentLineage(
        created_by=str(lineage.get("created_by") or "ag-sem-04-passive-schema"),
        created_from=tuple(_text_list(lineage.get("created_from"), limit=180)),
        supersedes_record_id=lineage.get("supersedes_record_id"),
        parent_record_digest=lineage.get("parent_record_digest"),
    )


def _reconstruct_amendment_record(payload: Mapping[str, Any]) -> ContractAmendmentRecord:
    trigger_dict = _safe_mapping(payload.get("trigger_refs"))
    if not trigger_dict:
        raise ContractAmendmentAdmissionError("amendment record requires trigger_refs")
    try:
        operations = tuple(
            _reconstruct_operation(_safe_mapping(item))
            for item in payload.get("operations") or ()
            if isinstance(item, Mapping)
        )
        affected_components = tuple(
            _reconstruct_affected_component(_safe_mapping(item))
            for item in payload.get("affected_component_refs") or ()
            if isinstance(item, Mapping)
        )
        coverage_candidates = tuple(
            _reconstruct_coverage_candidate(_safe_mapping(item))
            for item in payload.get("candidate_invalidated_coverage_refs") or ()
            if isinstance(item, Mapping)
        )
        return ContractAmendmentRecord(
            amendment_record_id=str(payload.get("amendment_record_id") or ""),
            run_id=str(payload.get("run_id") or ""),
            request_id=str(payload.get("request_id") or ""),
            request_digest=str(payload.get("request_digest") or ""),
            parent_contract_version=str(payload.get("parent_contract_version") or ""),
            parent_contract_digest=str(payload.get("parent_contract_digest") or ""),
            parent_question_meaning_record_id=payload.get("parent_question_meaning_record_id"),
            parent_question_meaning_record_digest=payload.get("parent_question_meaning_record_digest"),
            accepted_contract_ref=payload.get("accepted_contract_ref"),
            analyst_query_resolution_proposal_ref=_safe_mapping(
                payload.get("analyst_query_resolution_proposal_ref")
            ),
            originating_role_artifact_ref=_safe_mapping(
                payload.get("originating_role_artifact_ref")
            ),
            parent_graph_ref=_safe_mapping(payload.get("parent_graph_ref")),
            target_component_refs=tuple(
                _safe_mapping(item)
                for item in payload.get("target_component_refs") or ()
                if isinstance(item, Mapping)
            ),
            dependency_component_refs=tuple(
                _safe_mapping(item)
                for item in payload.get("dependency_component_refs") or ()
                if isinstance(item, Mapping)
            ),
            material_necessity_rationale=payload.get(
                "material_necessity_rationale"
            ),
            user_query_broadening=bool(payload.get("user_query_broadening")),
            recovery_generation_parent_ref=payload.get(
                "recovery_generation_parent_ref"
            ),
            recovery_generation_depth=payload.get("recovery_generation_depth"),
            trigger_refs=_reconstruct_trigger_refs(trigger_dict),
            affected_component_refs=affected_components,
            operations=operations,
            materiality=_coerce_enum(
                MaterialityPosture,
                payload.get("materiality"),
                MaterialityPosture.UNKNOWN,
            ),
            user_confirmation_posture=_coerce_enum(
                UserConfirmationPosture,
                payload.get("user_confirmation_posture"),
                UserConfirmationPosture.NOT_REQUIRED,
            ),
            monotonicity=_coerce_enum(
                MonotonicityPosture,
                payload.get("monotonicity"),
                MonotonicityPosture.UNKNOWN,
            ),
            weakening_posture=_coerce_enum(
                WeakeningPosture,
                payload.get("weakening_posture"),
                WeakeningPosture.NONE,
            ),
            mode_permission_posture=_coerce_enum(
                ModePermissionPosture,
                payload.get("mode_permission_posture"),
                ModePermissionPosture.UNKNOWN,
            ),
            disposition=_coerce_enum(
                ProposalDisposition,
                payload.get("disposition"),
                ProposalDisposition.PROPOSED,
            ),
            user_authority_ref=payload.get("user_authority_ref"),
            candidate_new_contract_version=payload.get("candidate_new_contract_version"),
            candidate_new_contract_digest=payload.get("candidate_new_contract_digest"),
            candidate_invalidated_coverage_refs=coverage_candidates,
            stale_coverage_candidate_posture=_coerce_enum(
                StaleCoverageCandidatePosture,
                payload.get("stale_coverage_candidate_posture"),
                StaleCoverageCandidatePosture.NOT_APPLICABLE,
            ),
            required_caveats=tuple(_text_list(payload.get("required_caveats"), limit=360)),
            prohibited_upgrades=tuple(_text_list(payload.get("prohibited_upgrades"), limit=360)),
            rejection_reasons=tuple(_text_list(payload.get("rejection_reasons"), limit=360)),
            blocking_reasons=tuple(_text_list(payload.get("blocking_reasons"), limit=360)),
            lineage=_reconstruct_lineage(
                payload.get("lineage") if isinstance(payload.get("lineage"), Mapping) else None
            ),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {},
            schema_version=str(payload.get("schema_version") or CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION),
        )
    except (ValueError, TypeError) as exc:
        raise ContractAmendmentAdmissionError(
            f"invalid contract amendment record payload: {exc}"
        ) from exc


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


def _coverage_index(
    coverage_history: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for item in coverage_history:
        mapping = _safe_mapping(item)
        coverage_record_id = _clean_token(mapping.get("coverage_record_id"))
        if coverage_record_id:
            index[coverage_record_id] = mapping
    return index


def _cited_observation_content_ref_ids(
    admission_index: Mapping[str, Mapping[str, Any]],
    cited_observation_ids: Sequence[str],
) -> set[str]:
    ids: set[str] = set()
    for observation_id in cited_observation_ids:
        admission = admission_index.get(observation_id)
        if admission is None:
            continue
        ids.update(_text_list(admission.get("content_refs")))
        for record in admission.get("content_ref_records") or ():
            if isinstance(record, Mapping):
                content_ref_id = _clean_token(record.get("content_ref_id"))
                if content_ref_id:
                    ids.add(content_ref_id)
    return ids


def _validate_trigger_refs(
    trigger_refs: AmendmentTriggerRefs,
    *,
    admission_history: Sequence[Mapping[str, Any]],
    coverage_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
) -> None:
    admission_by_id = _admission_index(admission_history)
    coverage_by_id = _coverage_index(coverage_history)
    cited_content_refs = _cited_observation_content_ref_ids(
        admission_by_id,
        trigger_refs.semantic_observation_refs,
    )
    allowed_evidence_refs = _evidence_custody_refs(_safe_mapping(evidence_ledger_projection))

    coverage_digests: dict[str, str] = {}
    metadata = trigger_refs.metadata if isinstance(trigger_refs.metadata, Mapping) else {}
    raw_digests = metadata.get("component_coverage_digests")
    if isinstance(raw_digests, Mapping):
        for key, value in raw_digests.items():
            coverage_id = _clean_token(key)
            digest = _clean_token(value, limit=128)
            if coverage_id and digest:
                coverage_digests[coverage_id] = digest

    for observation_id in trigger_refs.semantic_observation_refs:
        if observation_id not in admission_by_id:
            raise ContractAmendmentAdmissionError(
                f"trigger semantic observation ref {observation_id} is not admitted"
            )
    for coverage_record_id in trigger_refs.component_coverage_refs:
        coverage_entry = coverage_by_id.get(coverage_record_id)
        if coverage_entry is None:
            raise ContractAmendmentAdmissionError(
                f"trigger component coverage ref {coverage_record_id} is not reduced"
            )
        if coverage_record_id in coverage_digests:
            expected_digest = coverage_digests[coverage_record_id]
            actual_digest = _clean_token(coverage_entry.get("coverage_record_digest"), limit=128)
            if expected_digest != actual_digest:
                raise ContractAmendmentAdmissionError(
                    f"trigger component coverage ref {coverage_record_id} has stale coverage digest"
                )
    for content_ref_id in trigger_refs.sanitized_content_refs:
        if content_ref_id not in cited_content_refs:
            raise ContractAmendmentAdmissionError(
                f"trigger sanitized content ref {content_ref_id} is not cited by admitted semantic observation refs"
            )
    foreign_evidence = sorted(
        ref
        for ref in trigger_refs.evidence_refs
        if _normalize_evidence_ref(ref) not in allowed_evidence_refs
    )
    if foreign_evidence:
        raise ContractAmendmentAdmissionError(
            "trigger evidence refs absent from EvidenceLedger custody: "
            + ", ".join(foreign_evidence)
        )


def _validate_affected_components(
    affected_component_refs: Sequence[AffectedComponentRef],
    operations: Sequence[AmendmentOperation],
    *,
    accepted_contract: Mapping[str, Any],
) -> None:
    component_index = _accepted_component_index(accepted_contract)
    for operation in operations:
        if not operation.changes_component:
            continue
        if operation.operation_kind is AmendmentOperationKind.ADD_COMPONENT:
            continue
        for ref in affected_component_refs:
            accepted = component_index.get(ref.component_id)
            if accepted is None:
                raise ContractAmendmentAdmissionError(
                    f"affected component ref {ref.component_id} is not in accepted contract"
                )
            if not operation.component_revision_changed:
                _require_match(
                    ref.component_revision
                    == _clean_token(accepted.get("component_revision")),
                    f"affected component ref {ref.component_id} revision does not match accepted component",
                )
            if not operation.component_digest_changed:
                _require_match(
                    ref.component_digest
                    == _clean_token(accepted.get("component_digest"), limit=128),
                    f"affected component ref {ref.component_id} digest does not match accepted component",
                )


def _validate_candidate_invalidated_coverage_refs(
    candidates: Sequence[CoverageInvalidationCandidateRef],
    *,
    coverage_history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    coverage_by_id = _coverage_index(coverage_history)
    represented: list[dict[str, Any]] = []
    for candidate in candidates:
        if not candidate.coverage_record_id:
            raise ContractAmendmentAdmissionError(
                "candidate invalidated coverage ref requires coverage_record_id"
            )
        coverage_entry = coverage_by_id.get(candidate.coverage_record_id)
        if coverage_entry is None:
            raise ContractAmendmentAdmissionError(
                f"candidate invalidated coverage ref {candidate.coverage_record_id} is not reduced"
            )
        if candidate.coverage_record_digest:
            history_digest = _clean_token(
                coverage_entry.get("coverage_record_digest"), limit=128
            )
            if candidate.coverage_record_digest != history_digest:
                raise ContractAmendmentAdmissionError(
                    f"candidate invalidated coverage ref {candidate.coverage_record_id} has stale coverage digest"
                )
        candidate_dict = candidate.to_dict()
        if candidate_dict.get("represented_only") is not True:
            raise ContractAmendmentAdmissionError(
                "candidate invalidated coverage refs must remain represented_only"
            )
        if candidate_dict.get("coverage_invalidation_applied") is True:
            raise ContractAmendmentAdmissionError(
                "candidate invalidated coverage refs must not apply invalidation"
            )
        represented.append(candidate_dict)
    return represented


def _record_declares_search_planner_revision_origin(
    mapping: Mapping[str, Any],
) -> bool:
    if "search_planner_revision_lineage" in mapping:
        return True
    if _normalize_key(mapping.get("origin")) == "search_planner_revision":
        return True
    if _normalize_key(mapping.get("amendment_origin")) == "search_planner_revision":
        return True
    created_by = _normalize_key(mapping.get("created_by"))
    if created_by in {
        "runkernel.searchplannerrevision",
        "runkernel_searchplannerrevision",
        "run_kernel_search_planner_revision",
    }:
        return True
    created_from = {
        _normalize_key(item)
        for item in _text_list(mapping.get("created_from"), limit=200)
    }
    return "search_planner_revision" in created_from


def _revision_lineage_containers(
    record_safe: Mapping[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    containers: list[tuple[str, dict[str, Any]]] = [
        ("record metadata", _safe_mapping(record_safe.get("metadata"))),
        ("record trigger metadata", _safe_mapping(_safe_mapping(record_safe.get("trigger_refs")).get("metadata"))),
        ("record lineage", _safe_mapping(record_safe.get("lineage"))),
    ]
    for index, operation in enumerate(record_safe.get("operations") or (), start=1):
        operation_map = _safe_mapping(operation)
        containers.append(
            (f"operation {index} metadata", _safe_mapping(operation_map.get("metadata")))
        )
        containers.append(
            (
                f"operation {index} payload",
                _safe_mapping(operation_map.get("operation_payload")),
            )
        )
    return containers


def _extract_search_planner_revision_lineage(
    *,
    record_safe: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    declared = False
    lineages: list[tuple[str, dict[str, Any]]] = []
    for label, container in _revision_lineage_containers(record_safe):
        if _record_declares_search_planner_revision_origin(container):
            declared = True
        lineage = _safe_mapping(container.get("search_planner_revision_lineage"))
        if lineage:
            declared = True
            lineages.append((label, lineage))

    if not lineages:
        return declared, {}

    first_label, first_lineage = lineages[0]
    for label, lineage in lineages[1:]:
        if lineage != first_lineage:
            raise ContractAmendmentAdmissionError(
                "search planner revision lineage mismatch between "
                f"{first_label} and {label}"
            )
    return True, first_lineage


def _require_revision_action_token(
    *,
    action_inputs: Mapping[str, Any],
    key: str,
    limit: int = 160,
) -> str:
    value = _clean_token(action_inputs.get(key), limit=limit)
    if not value:
        raise ContractAmendmentAdmissionError(
            f"search planner revision admission binding requires {key}"
        )
    return value


def _require_revision_action_list(
    *,
    action_inputs: Mapping[str, Any],
    key: str,
    allow_empty: bool = False,
) -> list[str]:
    if key not in action_inputs:
        raise ContractAmendmentAdmissionError(
            f"search planner revision admission binding requires {key}"
        )
    values = _text_list(action_inputs.get(key))
    if not values and not allow_empty:
        raise ContractAmendmentAdmissionError(
            f"search planner revision admission binding requires {key}"
        )
    return values


def _validate_revision_false_flags(
    *,
    record_safe: Mapping[str, Any],
    lineage: Mapping[str, Any],
) -> None:
    for key in _REVISION_LINEAGE_FALSE_FLAGS:
        if lineage.get(key) is not False:
            raise ContractAmendmentAdmissionError(
                f"search planner revision lineage must keep {key} false"
            )
    for label, container in _revision_lineage_containers(record_safe):
        for key in _REVISION_LINEAGE_FALSE_FLAGS:
            if key in container and container.get(key) is not False:
                raise ContractAmendmentAdmissionError(
                    f"search planner revision {label} must keep {key} false"
                )
        embedded = _safe_mapping(container.get("search_planner_revision_lineage"))
        for key in _REVISION_LINEAGE_FALSE_FLAGS:
            if key in embedded and embedded.get(key) is not False:
                raise ContractAmendmentAdmissionError(
                    f"search planner revision {label} lineage must keep {key} false"
                )


def _validate_search_planner_revision_lineage(
    *,
    record_safe: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    explicit_required = (
        action_inputs.get("search_planner_revision_lineage_required") is True
        or action_inputs.get("amendment_origin") == "search_planner_revision"
    )
    declared_by_record, lineage = _extract_search_planner_revision_lineage(
        record_safe=record_safe
    )
    if not explicit_required and not declared_by_record:
        return {}

    if not lineage:
        raise ContractAmendmentAdmissionError(
            "search planner revision amendment requires embedded revision lineage"
        )

    _validate_revision_false_flags(record_safe=record_safe, lineage=lineage)

    expected_revision_id = (
        _clean_token(action_inputs.get("planner_revision_id"))
        or _clean_token(action_inputs.get("search_planner_revision_id"))
    )
    if not expected_revision_id:
        raise ContractAmendmentAdmissionError(
            "search planner revision admission binding requires planner_revision_id"
        )
    _require_match(
        _clean_token(lineage.get("planner_revision_id")) == expected_revision_id,
        "search planner revision lineage id does not match authorization",
    )

    expected_component_id = _require_revision_action_token(
        action_inputs=action_inputs,
        key="component_id",
    )
    _require_match(
        _clean_token(lineage.get("component_id")) == expected_component_id,
        "search planner revision component lineage does not match authorization",
    )

    planner_ref = _safe_mapping(lineage.get("parent_search_planner_proposal_ref"))
    expected_planner = {
        "proposal_id": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_search_planner_proposal_id",
        ),
        "proposal_digest": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_search_planner_proposal_digest",
            limit=128,
        ),
        "question_meaning_record_id": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_question_meaning_record_id",
        ),
        "question_meaning_record_digest": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_question_meaning_record_digest",
            limit=128,
        ),
    }
    for key, expected in expected_planner.items():
        limit = 128 if key.endswith("digest") else 200
        _require_match(
            _clean_token(planner_ref.get(key), limit=limit) == expected,
            "search planner revision parent planner lineage does not match authorization",
        )

    scout_ref = _safe_mapping(lineage.get("parent_scout_disambiguation_report_ref"))
    expected_scout = {
        "report_id": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_scout_disambiguation_report_id",
        ),
        "report_digest": _require_revision_action_token(
            action_inputs=action_inputs,
            key="parent_scout_disambiguation_report_digest",
            limit=128,
        ),
    }
    for key, expected in expected_scout.items():
        limit = 128 if key.endswith("digest") else 200
        _require_match(
            _clean_token(scout_ref.get(key), limit=limit) == expected,
            "search planner revision parent Scout lineage does not match authorization",
        )
    nested_planner = _safe_mapping(
        scout_ref.get("parent_search_planner_proposal_ref")
    )
    if nested_planner:
        for key, expected in expected_planner.items():
            limit = 128 if key.endswith("digest") else 200
            _require_match(
                _clean_token(nested_planner.get(key), limit=limit) == expected,
                "search planner revision Scout lineage is not bound to parent planner/QMR",
            )

    expected_dimension_ids = _require_revision_action_list(
        action_inputs=action_inputs,
        key="consumed_ambiguity_dimension_ids",
    )
    expected_hint_ids = _require_revision_action_list(
        action_inputs=action_inputs,
        key="consumed_scout_hint_ids",
        allow_empty=True,
    )
    _require_match(
        _text_list(lineage.get("consumed_ambiguity_dimension_ids"))
        == expected_dimension_ids,
        "search planner revision consumed dimension lineage does not match authorization",
    )
    _require_match(
        _text_list(lineage.get("consumed_scout_hint_ids"))
        == expected_hint_ids,
        "search planner revision consumed Scout hint lineage does not match authorization",
    )

    _require_match(
        _clean_token(record_safe.get("parent_question_meaning_record_id"))
        == expected_planner["question_meaning_record_id"],
        "search planner revision amendment QMR id lineage does not match authorization",
    )
    _require_match(
        _clean_token(
            record_safe.get("parent_question_meaning_record_digest"),
            limit=128,
        )
        == expected_planner["question_meaning_record_digest"],
        "search planner revision amendment QMR digest lineage does not match authorization",
    )

    for operation in record_safe.get("operations") or ():
        operation_map = _safe_mapping(operation)
        payload = _safe_mapping(operation_map.get("operation_payload"))
        operation_kind = _normalize_key(
            payload.get("normalized_operation_kind")
            or payload.get("operation")
            or operation_map.get("operation_kind")
        )
        if operation_kind in _REVISION_FORBIDDEN_OPERATION_KINDS:
            raise ContractAmendmentAdmissionError(
                "search planner revision amendments cannot resolve slots or satisfy requirements"
            )
        if operation_kind not in _REVISION_ALLOWED_OPERATION_KINDS:
            raise ContractAmendmentAdmissionError(
                "search planner revision amendments must stay monotonic and non-evidence"
            )
        for key in _REVISION_LINEAGE_FALSE_FLAGS:
            if key in payload and payload.get(key) is not False:
                raise ContractAmendmentAdmissionError(
                    f"search planner revision amendment operation must keep {key} false"
                )
    return lineage


def _expected_accepted_contract_ref(accepted_contract_version: str) -> str:
    return f"contract:{accepted_contract_version}:accepted"


def _admission_digest_payload(state_core: Mapping[str, Any]) -> dict[str, Any]:
    lineage = dict(state_core.get("lineage") or {})
    lineage.pop("reducer_action_id", None)
    return {
        "schema_version": state_core.get("schema_version"),
        "run_id": state_core.get("run_id"),
        "request_id": state_core.get("request_id"),
        "amendment_record_id": state_core.get("amendment_record_id"),
        "amendment_record_digest": state_core.get("amendment_record_digest"),
        "parent_contract_version": state_core.get("parent_contract_version"),
        "parent_contract_digest": state_core.get("parent_contract_digest"),
        "accepted_contract_version": state_core.get("accepted_contract_version"),
        "accepted_contract_digest": state_core.get("accepted_contract_digest"),
        "accepted_contract_ref": state_core.get("accepted_contract_ref"),
        "analyst_query_resolution_proposal_ref": state_core.get(
            "analyst_query_resolution_proposal_ref"
        ),
        "originating_role_artifact_ref": state_core.get(
            "originating_role_artifact_ref"
        ),
        "parent_graph_ref": state_core.get("parent_graph_ref"),
        "target_component_refs": state_core.get("target_component_refs"),
        "dependency_component_refs": state_core.get(
            "dependency_component_refs"
        ),
        "material_necessity_rationale": state_core.get(
            "material_necessity_rationale"
        ),
        "recovery_generation_parent_ref": state_core.get(
            "recovery_generation_parent_ref"
        ),
        "recovery_generation_depth": state_core.get(
            "recovery_generation_depth"
        ),
        "disposition": state_core.get("disposition"),
        "materiality": state_core.get("materiality"),
        "monotonicity": state_core.get("monotonicity"),
        "weakening_posture": state_core.get("weakening_posture"),
        "trigger_refs": state_core.get("trigger_refs"),
        "affected_component_refs": state_core.get("affected_component_refs"),
        "operations": state_core.get("operations"),
        "candidate_invalidated_coverage_refs": state_core.get(
            "candidate_invalidated_coverage_refs"
        ),
        "stale_coverage_candidate_posture": state_core.get("stale_coverage_candidate_posture"),
        "required_caveats": state_core.get("required_caveats"),
        "prohibited_upgrades": state_core.get("prohibited_upgrades"),
        "rejection_reasons": state_core.get("rejection_reasons"),
        "blocking_reasons": state_core.get("blocking_reasons"),
        "amendment_record_lineage": state_core.get("amendment_record_lineage"),
        "search_planner_revision_lineage": state_core.get(
            "search_planner_revision_lineage"
        ),
        "lineage": lineage,
    }


def build_contract_amendment_admission_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    amendment_payload: Mapping[str, Any] | None,
    accepted_contract: Mapping[str, Any] | None,
    admission_history: Sequence[Mapping[str, Any]],
    coverage_history: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any] | None,
    existing_amendment_record_ids: Sequence[str] = (),
    existing_amendment_record_digests: Sequence[str] = (),
    run_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Validate one passive amendment record and build canonical admission state."""

    clean_action_id = _clean_token(action_id, limit=200)
    if not clean_action_id:
        raise ContractAmendmentAdmissionError(
            "contract amendment admission requires an authorized action id"
        )
    clean_run_id = _clean_token(run_id)
    clean_request_id = _clean_token(request_id)
    if not clean_run_id or not clean_request_id:
        raise ContractAmendmentAdmissionError(
            "contract amendment admission requires run_id and request_id"
        )

    contract = _safe_mapping(accepted_contract)
    if not contract or contract.get("canonical_state") is not True:
        raise ContractAmendmentAdmissionError(
            "contract amendment admission requires an accepted initial answer contract"
        )
    accepted_contract_version = _clean_token(contract.get("accepted_contract_version"))
    accepted_contract_digest = _clean_token(contract.get("accepted_contract_digest"), limit=128)
    parent_qmr_id = _clean_token(contract.get("parent_question_meaning_record_id"))
    parent_qmr_digest = _clean_token(contract.get("parent_question_meaning_record_digest"), limit=128)
    if not accepted_contract_version or not accepted_contract_digest:
        raise ContractAmendmentAdmissionError(
            "accepted initial answer contract is missing required version/digest bindings"
        )

    raw_payload = amendment_payload if isinstance(amendment_payload, Mapping) else {}
    raw_record_dict = raw_payload.get("contract_amendment_record")
    raw_record_dict = dict(raw_record_dict) if isinstance(raw_record_dict, Mapping) else {}
    if not raw_record_dict:
        raise ContractAmendmentAdmissionError(
            "contract amendment admission requires a contract_amendment_record proposal payload"
        )

    _reject_unsafe_amendment_posture(raw_record_dict)

    payload = _safe_mapping(raw_payload)
    record_dict = dict(raw_record_dict)
    forbidden = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
    if forbidden:
        raise ContractAmendmentAdmissionError(
            "amendment payload includes closed authority fields: " + ", ".join(forbidden)
        )

    record = _reconstruct_amendment_record(record_dict)

    if record.passive is not True or record.canonical_state is True:
        raise ContractAmendmentAdmissionError(
            "contract amendment record must be a passive, non-canonical proposal"
        )
    if record.contract_mutation_applied is True or record.coverage_invalidation_applied is True:
        raise ContractAmendmentAdmissionError(
            "contract amendment record must not have applied contract mutation or coverage invalidation"
        )
    if record.runtime_behavior_changed is True:
        raise ContractAmendmentAdmissionError(
            "contract amendment record must not have changed runtime behavior"
        )

    if record.run_id != clean_run_id:
        raise ContractAmendmentAdmissionError("amendment record run_id does not match the run")
    if record.request_id != clean_request_id:
        raise ContractAmendmentAdmissionError("amendment record request_id does not match the request")

    recomputed_digest = record.record_digest
    declared_digest = _clean_token(record_dict.get("record_digest"), limit=128)
    if declared_digest and declared_digest != recomputed_digest:
        raise ContractAmendmentAdmissionError(
            "stale amendment payload: amendment record digest does not match payload content"
        )

    inputs = dict(action_inputs or {})
    missing_inputs = [key for key in _REQUIRED_INPUT_KEYS if not _clean_token(inputs.get(key), limit=200)]
    if missing_inputs:
        raise ContractAmendmentAdmissionError(
            "authorized action must bind: " + ", ".join(missing_inputs)
        )
    bound_request_id = _clean_token(inputs.get("request_id"))
    if bound_request_id and bound_request_id != clean_request_id:
        raise ContractAmendmentAdmissionError(
            "authorized action request_id binding does not match the request"
        )

    _require_match(
        _clean_token(inputs.get("amendment_record_id")) == record.amendment_record_id,
        "action amendment_record_id binding does not match the amendment record id",
    )
    _require_match(
        _clean_token(inputs.get("amendment_record_digest"), limit=128) == recomputed_digest,
        "action amendment_record_digest binding does not match the recomputed amendment record digest",
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
        _clean_token(inputs.get("parent_contract_digest"), limit=128) == accepted_contract_digest,
        "action parent_contract_digest binding does not match the accepted contract digest",
    )
    _require_match(
        _clean_token(inputs.get("parent_contract_version")) == accepted_contract_version,
        "action parent_contract_version binding does not match the accepted contract version",
    )

    _require_match(
        record.parent_contract_version == accepted_contract_version,
        "amendment record parent_contract_version does not match the accepted contract version",
    )
    _require_match(
        record.parent_contract_digest == accepted_contract_digest,
        "amendment record parent_contract_digest does not match the accepted contract digest",
    )

    if record.parent_question_meaning_record_id and parent_qmr_id:
        _require_match(
            _clean_token(record.parent_question_meaning_record_id) == parent_qmr_id,
            "amendment record parent_question_meaning_record_id does not match the accepted parent QMR id",
        )
    if record.parent_question_meaning_record_digest and parent_qmr_digest:
        _require_match(
            _clean_token(record.parent_question_meaning_record_digest, limit=128) == parent_qmr_digest,
            "amendment record parent_question_meaning_record_digest does not match the accepted parent QMR digest",
        )

    if record.accepted_contract_ref:
        expected_ref = _expected_accepted_contract_ref(accepted_contract_version)
        _require_match(
            _clean_token(record.accepted_contract_ref) == expected_ref,
            "amendment record accepted_contract_ref does not match the accepted contract ref convention",
        )

    validation = record.validate()
    if not validation.ok:
        raise ContractAmendmentAdmissionError(
            "contract amendment record failed validation: " + "; ".join(validation.errors)
        )

    _validate_trigger_refs(
        record.trigger_refs,
        admission_history=admission_history,
        coverage_history=coverage_history,
        evidence_ledger_projection=_safe_mapping(evidence_ledger_projection),
    )

    _validate_affected_components(
        record.affected_component_refs,
        record.operations,
        accepted_contract=contract,
    )

    represented_coverage_candidates = _validate_candidate_invalidated_coverage_refs(
        record.candidate_invalidated_coverage_refs,
        coverage_history=coverage_history,
    )

    if record.amendment_record_id in {
        _clean_token(item) for item in existing_amendment_record_ids if item
    }:
        raise ContractAmendmentAdmissionError(
            f"contract amendment record {record.amendment_record_id} is already admitted"
        )
    if recomputed_digest in {
        _clean_token(item, limit=128) for item in existing_amendment_record_digests if item
    }:
        raise ContractAmendmentAdmissionError("contract amendment record digest is already admitted")

    record_safe = record.to_dict(include_validation=False)
    search_planner_revision_lineage = _validate_search_planner_revision_lineage(
        record_safe=record_safe,
        action_inputs=inputs,
    )
    lineage = {
        "created_by": CONTRACT_AMENDMENT_ADMISSION_OWNER,
        "created_from": [
            "passive_contract_amendment_record",
            "accepted_initial_answer_contract",
        ],
        "reducer_action_id": clean_action_id,
        "parent_amendment_record_digest": recomputed_digest,
        "accepted_contract_digest": accepted_contract_digest,
    }
    state_core: dict[str, Any] = {
        "schema_version": CONTRACT_AMENDMENT_ADMISSION_SCHEMA_VERSION,
        "owner": CONTRACT_AMENDMENT_ADMISSION_OWNER,
        "trace_key": CONTRACT_AMENDMENT_ADMISSION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "amendment_record_id": record.amendment_record_id,
        "amendment_record_digest": recomputed_digest,
        "parent_contract_version": accepted_contract_version,
        "parent_contract_digest": accepted_contract_digest,
        "accepted_contract_version": accepted_contract_version,
        "accepted_contract_digest": accepted_contract_digest,
        "accepted_contract_ref": record.accepted_contract_ref
        or _expected_accepted_contract_ref(accepted_contract_version),
        "analyst_query_resolution_proposal_ref": record_safe.get(
            "analyst_query_resolution_proposal_ref", {}
        ),
        "originating_role_artifact_ref": record_safe.get(
            "originating_role_artifact_ref", {}
        ),
        "parent_graph_ref": record_safe.get("parent_graph_ref", {}),
        "target_component_refs": record_safe.get("target_component_refs", []),
        "dependency_component_refs": record_safe.get(
            "dependency_component_refs", []
        ),
        "material_necessity_rationale": record_safe.get(
            "material_necessity_rationale"
        ),
        "user_query_broadening": False,
        "recovery_generation_parent_ref": record_safe.get(
            "recovery_generation_parent_ref"
        ),
        "recovery_generation_depth": record_safe.get(
            "recovery_generation_depth"
        ),
        "parent_question_meaning_record_id": parent_qmr_id,
        "parent_question_meaning_record_digest": parent_qmr_digest,
        "disposition": record_safe.get("disposition"),
        "materiality": record_safe.get("materiality"),
        "user_confirmation_posture": record_safe.get("user_confirmation_posture"),
        "monotonicity": record_safe.get("monotonicity"),
        "weakening_posture": record_safe.get("weakening_posture"),
        "mode_permission_posture": record_safe.get("mode_permission_posture"),
        "trigger_refs": record_safe.get("trigger_refs", {}),
        "affected_component_refs": record_safe.get("affected_component_refs", []),
        "operations": record_safe.get("operations", []),
        "candidate_new_contract_version": record_safe.get("candidate_new_contract_version"),
        "candidate_new_contract_digest": record_safe.get("candidate_new_contract_digest"),
        "candidate_invalidated_coverage_refs": represented_coverage_candidates,
        "stale_coverage_candidate_posture": record_safe.get("stale_coverage_candidate_posture"),
        "required_caveats": record_safe.get("required_caveats", []),
        "prohibited_upgrades": record_safe.get("prohibited_upgrades", []),
        "rejection_reasons": record_safe.get("rejection_reasons", []),
        "blocking_reasons": record_safe.get("blocking_reasons", []),
        "amendment_record_lineage": record_safe.get("lineage", {}),
        "amendment_record_metadata": record_safe.get("metadata", {}),
        "search_planner_revision_lineage": search_planner_revision_lineage,
        "lineage": lineage,
        "contract_mutation_applied": False,
        "coverage_invalidation_applied": False,
        "coverage_marked_stale": False,
        "initial_answer_contract_mutated": False,
        "amendment_applied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "search_judgment_decided": False,
        "query_plan_activated": False,
        "search_work_plan_activated": False,
        "followup_authorized": False,
        "citation_behavior_changed": False,
        "provider_search_behavior_changed": False,
        "runtime_behavior_changed": False,
        "live_validation_not_run": True,
    }
    admission_digest = _digest_json(_admission_digest_payload(state_core))
    return {**state_core, "admission_digest": admission_digest}


def build_contract_amendment_admission_projection(
    *,
    admission_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical amendment admission state with no raw or private data."""

    return {
        "owner": CONTRACT_AMENDMENT_ADMISSION_OWNER,
        "schema_version": admission_state.get("schema_version"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": admission_state.get("run_id"),
        "request_id": admission_state.get("request_id"),
        "authorized_action_id": admission_state.get("authorized_action_id"),
        "amendment_record_id": admission_state.get("amendment_record_id"),
        "amendment_record_digest": admission_state.get("amendment_record_digest"),
        "admission_digest": admission_state.get("admission_digest"),
        "parent_contract_version": admission_state.get("parent_contract_version"),
        "parent_contract_digest": admission_state.get("parent_contract_digest"),
        "accepted_contract_version": admission_state.get("accepted_contract_version"),
        "accepted_contract_digest": admission_state.get("accepted_contract_digest"),
        "accepted_contract_ref": admission_state.get("accepted_contract_ref"),
        "analyst_query_resolution_proposal_ref": dict(
            admission_state.get("analyst_query_resolution_proposal_ref") or {}
        ),
        "originating_role_artifact_ref": dict(
            admission_state.get("originating_role_artifact_ref") or {}
        ),
        "parent_graph_ref": dict(admission_state.get("parent_graph_ref") or {}),
        "target_component_refs": list(
            admission_state.get("target_component_refs") or []
        ),
        "dependency_component_refs": list(
            admission_state.get("dependency_component_refs") or []
        ),
        "material_necessity_rationale": admission_state.get(
            "material_necessity_rationale"
        ),
        "user_query_broadening": False,
        "recovery_generation_parent_ref": admission_state.get(
            "recovery_generation_parent_ref"
        ),
        "recovery_generation_depth": admission_state.get(
            "recovery_generation_depth"
        ),
        "disposition": admission_state.get("disposition"),
        "materiality": admission_state.get("materiality"),
        "user_confirmation_posture": admission_state.get("user_confirmation_posture"),
        "monotonicity": admission_state.get("monotonicity"),
        "weakening_posture": admission_state.get("weakening_posture"),
        "mode_permission_posture": admission_state.get("mode_permission_posture"),
        "trigger_refs": dict(admission_state.get("trigger_refs") or {}),
        "affected_component_refs": list(admission_state.get("affected_component_refs", [])),
        "operations": list(admission_state.get("operations", [])),
        "candidate_new_contract_version": admission_state.get("candidate_new_contract_version"),
        "candidate_new_contract_digest": admission_state.get("candidate_new_contract_digest"),
        "candidate_invalidated_coverage_refs": list(
            admission_state.get("candidate_invalidated_coverage_refs", [])
        ),
        "stale_coverage_candidate_posture": admission_state.get("stale_coverage_candidate_posture"),
        "required_caveats": list(admission_state.get("required_caveats", [])),
        "prohibited_upgrades": list(admission_state.get("prohibited_upgrades", [])),
        "rejection_reasons": list(admission_state.get("rejection_reasons", [])),
        "blocking_reasons": list(admission_state.get("blocking_reasons", [])),
        "amendment_record_lineage": dict(
            admission_state.get("amendment_record_lineage") or {}
        ),
        "amendment_record_metadata": dict(
            admission_state.get("amendment_record_metadata") or {}
        ),
        "search_planner_revision_lineage": dict(
            admission_state.get("search_planner_revision_lineage") or {}
        ),
        "lineage": dict(admission_state.get("lineage") or {}),
        "contract_mutation_applied": False,
        "coverage_invalidation_applied": False,
        "coverage_marked_stale": False,
        "initial_answer_contract_mutated": False,
        "amendment_applied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
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
    "CONTRACT_AMENDMENT_ADMISSION_OWNER",
    "CONTRACT_AMENDMENT_ADMISSION_REASON",
    "CONTRACT_AMENDMENT_ADMISSION_SCHEMA_VERSION",
    "CONTRACT_AMENDMENT_ADMISSION_STAGE",
    "CONTRACT_AMENDMENT_ADMISSION_TRACE_KEY",
    "ContractAmendmentAdmissionError",
    "build_contract_amendment_admission_projection",
    "build_contract_amendment_admission_state",
]
