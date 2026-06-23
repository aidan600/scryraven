"""Passive ContractAmendmentRecord schema for AG-SEM-04.

These records describe proposed contract amendments found by semantic
observation, evidence gaps, normalization needs, conflicts, currentness, or
component coverage state. They do not mutate accepted contracts, invalidate
coverage, change runtime behavior, or create final-answer authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION = "contract_amendment_record_ag_sem_04_v1"
CONTRACT_AMENDMENT_RECORD_TRACE_KEY = "contract_amendment_record"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "logs",
        "model_response",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
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
        "author_input",
        "canonical_coverage",
        "coverage_decision",
        "final_answer",
        "final_answer_packet",
        "followup_activation",
        "query_plan_activation",
        "search_judgment_decision",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)
_MATERIAL_SLOT_KINDS = frozenset(
    {
        "configuration",
        "currency",
        "currency_basis",
        "direct_vs_computed",
        "entity",
        "geography",
        "inflation_basis",
        "load_factor",
        "metric",
        "time_period",
        "variant",
    }
)


class AmendmentOperationKind(str, Enum):
    ADD_COMPONENT = "add_component"
    REVISE_COMPONENT = "revise_component"
    RESOLVE_SLOT = "resolve_slot"
    ADD_NORMALIZATION = "add_normalization"
    ADD_ASSUMPTION = "add_assumption"
    STRENGTHEN_SOURCE_OBLIGATION = "strengthen_source_obligation"
    ADD_CAVEAT = "add_caveat"
    MARK_IRREDUCIBLE_UNKNOWN = "mark_irreducible_unknown"
    CHANGE_ANSWER_POSTURE = "change_answer_posture"
    REMOVE_OR_WEAKEN_REQUIREMENT = "remove_or_weaken_requirement"


class MaterialityPosture(str, Enum):
    NON_MATERIAL = "non_material"
    MATERIAL = "material"
    UNKNOWN = "unknown"


class UserConfirmationPosture(str, Enum):
    NOT_REQUIRED = "not_required"
    REQUIRES_USER_CONFIRMATION = "requires_user_confirmation"
    EXPLICIT_USER_CONFIRMATION = "explicit_user_confirmation"
    LABELED_SCENARIO_TREATMENT = "labeled_scenario_treatment"
    EXPLICIT_USER_AUTHORITY = "explicit_user_authority"


class MonotonicityPosture(str, Enum):
    STRENGTHENS = "strengthens"
    PRESERVES = "preserves"
    WEAKENS = "weakens"
    UNKNOWN = "unknown"


class WeakeningPosture(str, Enum):
    NONE = "none"
    REMOVES_REQUIREMENT = "removes_requirement"
    WEAKENS_REQUIREMENT = "weakens_requirement"
    WEAKENS_SOURCE_OBLIGATION = "weakens_source_obligation"
    UNKNOWN = "unknown"


class ModePermissionPosture(str, Enum):
    WITHIN_MODE = "within_mode"
    REQUIRES_MODE_ESCALATION = "requires_mode_escalation"
    BLOCKED_BY_MODE = "blocked_by_mode"
    UNKNOWN = "unknown"


class ProposalDisposition(str, Enum):
    PROPOSED = "proposed"
    REQUIRES_USER_CONFIRMATION = "requires_user_confirmation"
    ELIGIBLE_FOR_FUTURE_ACCEPTANCE = "eligible_for_future_acceptance"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class StaleCoverageCandidatePosture(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    CANDIDATE_STALE = "candidate_stale"
    CANDIDATE_INVALIDATION_REQUIRED = "candidate_invalidation_required"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ContractAmendmentValidationResult:
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise ValueError("; ".join(self.errors))

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors)}


@dataclass(frozen=True, slots=True)
class AmendmentTriggerRefs:
    semantic_observation_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    sanitized_content_refs: tuple[str, ...] = ()
    component_coverage_refs: tuple[str, ...] = ()
    gap_refs: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()
    currentness_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_observation_refs", _text_tuple(self.semantic_observation_refs))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs))
        object.__setattr__(self, "sanitized_content_refs", _text_tuple(self.sanitized_content_refs))
        object.__setattr__(self, "component_coverage_refs", _text_tuple(self.component_coverage_refs))
        object.__setattr__(self, "gap_refs", _text_tuple(self.gap_refs))
        object.__setattr__(self, "conflict_refs", _text_tuple(self.conflict_refs))
        object.__setattr__(self, "currentness_refs", _text_tuple(self.currentness_refs))

    @property
    def has_trigger(self) -> bool:
        return any(
            (
                self.semantic_observation_refs,
                self.evidence_refs,
                self.sanitized_content_refs,
                self.component_coverage_refs,
                self.gap_refs,
                self.conflict_refs,
                self.currentness_refs,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "semantic_observation_refs": list(self.semantic_observation_refs),
                "evidence_refs": list(self.evidence_refs),
                "sanitized_content_refs": list(self.sanitized_content_refs),
                "component_coverage_refs": list(self.component_coverage_refs),
                "gap_refs": list(self.gap_refs),
                "conflict_refs": list(self.conflict_refs),
                "currentness_refs": list(self.currentness_refs),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class AffectedComponentRef:
    component_id: str
    component_revision: str
    component_digest: str
    relationship: str = "affected_component"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _clean_token(self.component_id) or "")
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision) or "")
        object.__setattr__(
            self,
            "component_digest",
            _clean_token(self.component_digest, limit=128) or "",
        )
        object.__setattr__(self, "relationship", _clean_token(self.relationship) or "affected_component")

    @property
    def complete(self) -> bool:
        return bool(self.component_id and self.component_revision and self.component_digest)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "component_id": self.component_id,
                "component_revision": self.component_revision,
                "component_digest": self.component_digest,
                "relationship": self.relationship,
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class AmendmentOperation:
    operation_id: str
    operation_kind: AmendmentOperationKind | str
    before_payload: Mapping[str, Any] = field(default_factory=dict)
    after_payload: Mapping[str, Any] = field(default_factory=dict)
    operation_payload: Mapping[str, Any] = field(default_factory=dict)
    material_slot_kinds: tuple[str, ...] = ()
    component_revision_changed: bool = False
    component_digest_changed: bool = False
    user_confirmation_required: bool = False
    labeled_scenario_treatment: bool = False
    user_authority_ref: str | None = None
    notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.operation_id):
            raise ValueError("amendment operation requires operation_id")
        object.__setattr__(
            self,
            "operation_kind",
            _coerce_enum(AmendmentOperationKind, self.operation_kind, AmendmentOperationKind.ADD_CAVEAT),
        )
        object.__setattr__(self, "before_payload", _json_safe(self.before_payload))
        object.__setattr__(self, "after_payload", _json_safe(self.after_payload))
        object.__setattr__(self, "operation_payload", _json_safe(self.operation_payload))
        object.__setattr__(self, "material_slot_kinds", _text_tuple(self.material_slot_kinds))
        object.__setattr__(self, "user_authority_ref", _clean_token(self.user_authority_ref))
        object.__setattr__(self, "notes", _text_tuple(self.notes, limit=360))

    @property
    def has_typed_payload(self) -> bool:
        return bool(self.operation_payload or (self.before_payload and self.after_payload))

    @property
    def changes_component(self) -> bool:
        return self.operation_kind in {
            AmendmentOperationKind.ADD_COMPONENT,
            AmendmentOperationKind.REVISE_COMPONENT,
            AmendmentOperationKind.CHANGE_ANSWER_POSTURE,
            AmendmentOperationKind.REMOVE_OR_WEAKEN_REQUIREMENT,
        }

    @property
    def touches_material_choice(self) -> bool:
        return bool(set(self.material_slot_kinds) & _MATERIAL_SLOT_KINDS)

    @property
    def may_stale_coverage(self) -> bool:
        return (
            self.changes_component
            or self.touches_material_choice
            or self.component_revision_changed
            or self.component_digest_changed
            or self.operation_kind is AmendmentOperationKind.REMOVE_OR_WEAKEN_REQUIREMENT
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "operation_id": _clean_token(self.operation_id),
                "operation_kind": self.operation_kind.value,
                "before_payload": self.before_payload,
                "after_payload": self.after_payload,
                "operation_payload": self.operation_payload,
                "material_slot_kinds": list(self.material_slot_kinds),
                "component_revision_changed": bool(self.component_revision_changed),
                "component_digest_changed": bool(self.component_digest_changed),
                "user_confirmation_required": bool(self.user_confirmation_required),
                "labeled_scenario_treatment": bool(self.labeled_scenario_treatment),
                "user_authority_ref": self.user_authority_ref,
                "notes": list(self.notes),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class CoverageInvalidationCandidateRef:
    coverage_record_id: str
    coverage_record_digest: str | None = None
    answer_component_id: str | None = None
    reason: str | None = None
    represented_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "coverage_record_id", _clean_token(self.coverage_record_id) or "")
        object.__setattr__(
            self,
            "coverage_record_digest",
            _clean_token(self.coverage_record_digest, limit=128),
        )
        object.__setattr__(self, "answer_component_id", _clean_token(self.answer_component_id))
        object.__setattr__(self, "reason", _clean_text(self.reason, limit=360))
        object.__setattr__(self, "represented_only", True)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "coverage_record_id": self.coverage_record_id,
                "coverage_record_digest": self.coverage_record_digest,
                "answer_component_id": self.answer_component_id,
                "reason": self.reason,
                "represented_only": True,
                "coverage_invalidation_applied": False,
            }
        )


@dataclass(frozen=True, slots=True)
class AmendmentLineage:
    created_by: str = "ag-sem-04-passive-schema"
    created_from: tuple[str, ...] = ("passive_contract_amendment_record",)
    supersedes_record_id: str | None = None
    parent_record_digest: str | None = None
    runtime_consumed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_by", _clean_token(self.created_by) or "ag-sem-04-passive-schema")
        object.__setattr__(self, "created_from", _text_tuple(self.created_from, limit=180))
        object.__setattr__(self, "supersedes_record_id", _clean_token(self.supersedes_record_id))
        object.__setattr__(self, "parent_record_digest", _clean_token(self.parent_record_digest, limit=128))
        object.__setattr__(self, "runtime_consumed", False)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "created_by": self.created_by,
                "created_from": list(self.created_from),
                "supersedes_record_id": self.supersedes_record_id,
                "parent_record_digest": self.parent_record_digest,
                "runtime_consumed": False,
            }
        )


@dataclass(frozen=True, slots=True)
class ContractAmendmentRecord:
    amendment_record_id: str
    run_id: str
    request_id: str
    request_digest: str
    parent_contract_version: str
    parent_contract_digest: str
    trigger_refs: AmendmentTriggerRefs
    operations: tuple[AmendmentOperation, ...]
    parent_question_meaning_record_id: str | None = None
    parent_question_meaning_record_digest: str | None = None
    accepted_contract_ref: str | None = None
    affected_component_refs: tuple[AffectedComponentRef, ...] = ()
    materiality: MaterialityPosture | str = MaterialityPosture.UNKNOWN
    user_confirmation_posture: UserConfirmationPosture | str = UserConfirmationPosture.NOT_REQUIRED
    monotonicity: MonotonicityPosture | str = MonotonicityPosture.UNKNOWN
    weakening_posture: WeakeningPosture | str = WeakeningPosture.NONE
    mode_permission_posture: ModePermissionPosture | str = ModePermissionPosture.UNKNOWN
    disposition: ProposalDisposition | str = ProposalDisposition.PROPOSED
    user_authority_ref: str | None = None
    candidate_new_contract_version: str | None = None
    candidate_new_contract_digest: str | None = None
    candidate_invalidated_coverage_refs: tuple[CoverageInvalidationCandidateRef, ...] = ()
    stale_coverage_candidate_posture: StaleCoverageCandidatePosture | str = StaleCoverageCandidatePosture.NOT_APPLICABLE
    required_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    lineage: AmendmentLineage = field(default_factory=AmendmentLineage)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    canonical_state: bool = False
    accepted_authority: bool = False
    contract_mutation_applied: bool = False
    coverage_invalidation_applied: bool = False
    runtime_behavior_changed: bool = False
    schema_version: str = CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("amendment_record_id", "run_id", "request_id", "request_digest"):
            if not _clean_token(getattr(self, field_name), limit=128):
                raise ValueError(f"contract amendment record requires {field_name}")
        object.__setattr__(self, "parent_contract_version", _clean_token(self.parent_contract_version) or "")
        object.__setattr__(
            self,
            "parent_contract_digest",
            _clean_token(self.parent_contract_digest, limit=128) or "",
        )
        object.__setattr__(self, "operations", tuple(self.operations or ()))
        object.__setattr__(self, "affected_component_refs", tuple(self.affected_component_refs or ()))
        object.__setattr__(
            self,
            "materiality",
            _coerce_enum(MaterialityPosture, self.materiality, MaterialityPosture.UNKNOWN),
        )
        object.__setattr__(
            self,
            "user_confirmation_posture",
            _coerce_enum(
                UserConfirmationPosture,
                self.user_confirmation_posture,
                UserConfirmationPosture.NOT_REQUIRED,
            ),
        )
        object.__setattr__(
            self,
            "monotonicity",
            _coerce_enum(MonotonicityPosture, self.monotonicity, MonotonicityPosture.UNKNOWN),
        )
        object.__setattr__(
            self,
            "weakening_posture",
            _coerce_enum(WeakeningPosture, self.weakening_posture, WeakeningPosture.NONE),
        )
        object.__setattr__(
            self,
            "mode_permission_posture",
            _coerce_enum(
                ModePermissionPosture,
                self.mode_permission_posture,
                ModePermissionPosture.UNKNOWN,
            ),
        )
        object.__setattr__(
            self,
            "disposition",
            _coerce_enum(ProposalDisposition, self.disposition, ProposalDisposition.PROPOSED),
        )
        object.__setattr__(self, "user_authority_ref", _clean_token(self.user_authority_ref))
        object.__setattr__(
            self,
            "candidate_new_contract_version",
            _clean_token(self.candidate_new_contract_version),
        )
        object.__setattr__(
            self,
            "candidate_new_contract_digest",
            _clean_token(self.candidate_new_contract_digest, limit=128),
        )
        object.__setattr__(
            self,
            "candidate_invalidated_coverage_refs",
            tuple(self.candidate_invalidated_coverage_refs or ()),
        )
        object.__setattr__(
            self,
            "stale_coverage_candidate_posture",
            _coerce_enum(
                StaleCoverageCandidatePosture,
                self.stale_coverage_candidate_posture,
                StaleCoverageCandidatePosture.NOT_APPLICABLE,
            ),
        )
        object.__setattr__(self, "required_caveats", _text_tuple(self.required_caveats, limit=360))
        object.__setattr__(self, "prohibited_upgrades", _text_tuple(self.prohibited_upgrades, limit=360))
        object.__setattr__(self, "rejection_reasons", _text_tuple(self.rejection_reasons, limit=360))
        object.__setattr__(self, "blocking_reasons", _text_tuple(self.blocking_reasons, limit=360))
        object.__setattr__(self, "passive", True)
        object.__setattr__(self, "canonical_state", False)
        object.__setattr__(self, "accepted_authority", False)
        object.__setattr__(self, "contract_mutation_applied", False)
        object.__setattr__(self, "coverage_invalidation_applied", False)
        object.__setattr__(self, "runtime_behavior_changed", False)

    @property
    def record_digest(self) -> str:
        return _digest_json(self._record_digest_payload())

    def validate(self) -> ContractAmendmentValidationResult:
        errors: list[str] = []
        payload = self.to_dict(include_validation=False)
        operation_ids = [operation.operation_id for operation in self.operations]

        _add_duplicate_errors(errors, "amendment operation_id", operation_ids)
        if not self.parent_contract_version:
            errors.append("contract amendment record requires parent_contract_version")
        if not self.parent_contract_digest:
            errors.append("contract amendment record requires parent_contract_digest")
        if not self.operations:
            errors.append("contract amendment record requires at least one typed operation")
        for operation in self.operations:
            if not operation.has_typed_payload:
                errors.append(f"amendment operation {operation.operation_id} requires typed before/after or payload")
        if not self.trigger_refs.has_trigger:
            errors.append("contract amendment record requires at least one trigger ref")

        if any(operation.changes_component for operation in self.operations):
            incomplete = [ref for ref in self.affected_component_refs if not ref.complete]
            if not self.affected_component_refs:
                errors.append("component-changing amendment requires affected component refs")
            elif incomplete:
                errors.append("affected component refs require component_id, component_revision, and component_digest")

        if self._requires_user_confirmation() and not self._has_confirmation_or_scenario():
            errors.append(
                "material slot or component amendment requires user confirmation or labeled scenario treatment"
            )

        if self._is_weakening():
            if not self.user_authority_ref and not any(operation.user_authority_ref for operation in self.operations):
                errors.append("weakening or removal requires explicit user authority")
            if self.disposition is ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE:
                errors.append("weakening or removal cannot be eligible for automatic future acceptance")

        if self._requires_coverage_stale_candidate() and not self._has_coverage_stale_candidate():
            errors.append("component-changing or material amendment requires candidate stale coverage representation")

        if not payload.get("passive"):
            errors.append("contract amendment record must remain passive")
        if payload.get("canonical_state"):
            errors.append("contract amendment record cannot be canonical state")
        if payload.get("accepted_authority"):
            errors.append("contract amendment record must not be accepted authority")
        if payload.get("contract_mutation_applied"):
            errors.append("contract amendment record must not apply contract mutation")
        if payload.get("coverage_invalidation_applied"):
            errors.append("contract amendment record must not apply coverage invalidation")
        if payload.get("runtime_behavior_changed"):
            errors.append("contract amendment record must not change runtime behavior")

        forbidden_present = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
        if forbidden_present:
            errors.append("contract amendment record includes closed authority fields: " + ", ".join(forbidden_present))
        return ContractAmendmentValidationResult(errors=tuple(errors))

    def require_valid(self) -> "ContractAmendmentRecord":
        self.validate().raise_for_errors()
        return self

    def _requires_user_confirmation(self) -> bool:
        if self.materiality is MaterialityPosture.MATERIAL:
            return True
        return any(operation.touches_material_choice for operation in self.operations)

    def _has_confirmation_or_scenario(self) -> bool:
        return self.user_confirmation_posture in {
            UserConfirmationPosture.REQUIRES_USER_CONFIRMATION,
            UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
            UserConfirmationPosture.LABELED_SCENARIO_TREATMENT,
            UserConfirmationPosture.EXPLICIT_USER_AUTHORITY,
        } or any(
            operation.user_confirmation_required or operation.labeled_scenario_treatment
            for operation in self.operations
        )

    def _is_weakening(self) -> bool:
        return (
            self.weakening_posture
            in {
                WeakeningPosture.REMOVES_REQUIREMENT,
                WeakeningPosture.WEAKENS_REQUIREMENT,
                WeakeningPosture.WEAKENS_SOURCE_OBLIGATION,
            }
            or self.monotonicity is MonotonicityPosture.WEAKENS
            or any(
                operation.operation_kind is AmendmentOperationKind.REMOVE_OR_WEAKEN_REQUIREMENT
                for operation in self.operations
            )
        )

    def _requires_coverage_stale_candidate(self) -> bool:
        return (
            self.materiality is MaterialityPosture.MATERIAL
            or self._is_weakening()
            or any(operation.may_stale_coverage for operation in self.operations)
        )

    def _has_coverage_stale_candidate(self) -> bool:
        return bool(self.candidate_invalidated_coverage_refs) or self.stale_coverage_candidate_posture in {
            StaleCoverageCandidatePosture.CANDIDATE_STALE,
            StaleCoverageCandidatePosture.CANDIDATE_INVALIDATION_REQUIRED,
            StaleCoverageCandidatePosture.UNKNOWN,
        }

    def _record_digest_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "amendment_record_id": _clean_token(self.amendment_record_id),
            "record_id": _clean_token(self.amendment_record_id),
            "run_id": _clean_token(self.run_id),
            "request_id": _clean_token(self.request_id),
            "request_digest": _clean_token(self.request_digest, limit=128),
            "parent_contract_version": self.parent_contract_version,
            "parent_contract_digest": self.parent_contract_digest,
            "parent_question_meaning_record_id": _clean_token(self.parent_question_meaning_record_id),
            "parent_question_meaning_record_digest": _clean_token(
                self.parent_question_meaning_record_digest,
                limit=128,
            ),
            "accepted_contract_ref": _clean_token(self.accepted_contract_ref),
            "trigger_refs": self.trigger_refs.to_dict(),
            "affected_component_refs": [ref.to_dict() for ref in self.affected_component_refs],
            "operations": [operation.to_dict() for operation in self.operations],
            "materiality": self.materiality.value,
            "user_confirmation_posture": self.user_confirmation_posture.value,
            "monotonicity": self.monotonicity.value,
            "weakening_posture": self.weakening_posture.value,
            "mode_permission_posture": self.mode_permission_posture.value,
            "disposition": self.disposition.value,
            "user_authority_ref": self.user_authority_ref,
            "candidate_new_contract_version": self.candidate_new_contract_version,
            "candidate_new_contract_digest": self.candidate_new_contract_digest,
            "candidate_contract_is_canonical": False,
            "candidate_invalidated_coverage_refs": [ref.to_dict() for ref in self.candidate_invalidated_coverage_refs],
            "stale_coverage_candidate_posture": self.stale_coverage_candidate_posture.value,
            "required_caveats": list(self.required_caveats),
            "prohibited_upgrades": list(self.prohibited_upgrades),
            "rejection_reasons": list(self.rejection_reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "lineage": self.lineage.to_dict(),
            "metadata": _json_safe(self.metadata),
            "passive": True,
            "canonical_state": False,
            "accepted_authority": False,
            "contract_mutation_applied": False,
            "coverage_invalidation_applied": False,
            "runtime_behavior_changed": False,
            "runtime_consumed": False,
            "sufficiency_behavior_changed": False,
            "search_behavior_changed": False,
            "author_behavior_changed": False,
            "citation_behavior_changed": False,
        }

    def to_dict(self, *, include_validation: bool = True) -> dict[str, Any]:
        payload = _without_empty(
            {
                **self._record_digest_payload(),
                "trace_key": CONTRACT_AMENDMENT_RECORD_TRACE_KEY,
                "record_digest": self.record_digest,
            }
        )
        if include_validation:
            payload["validation"] = self.validate().to_dict()
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {CONTRACT_AMENDMENT_RECORD_TRACE_KEY: self.to_dict()}


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
    if depth > 5:
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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None and value != [] and value != {}}


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _coerce_enum(enum_class: type[Enum], value: Any, default: Enum) -> Enum:
    raw = _enum_value(value)
    for item in enum_class:
        if item.value == raw:
            return item
    return default


def _text_tuple(value: Sequence[Any] | None, *, limit: int = 160) -> tuple[str, ...]:
    out: list[str] = []
    for item in value or ():
        text = _clean_token(item, limit=limit)
        if text:
            out.append(text)
    return tuple(out)


def _digest_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _add_duplicate_errors(errors: list[str], label: str, values: Sequence[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        errors.append(f"duplicate {label} values are not allowed: {', '.join(duplicates)}")


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


__all__ = [
    "CONTRACT_AMENDMENT_RECORD_SCHEMA_VERSION",
    "CONTRACT_AMENDMENT_RECORD_TRACE_KEY",
    "AffectedComponentRef",
    "AmendmentLineage",
    "AmendmentOperation",
    "AmendmentOperationKind",
    "AmendmentTriggerRefs",
    "ContractAmendmentRecord",
    "ContractAmendmentValidationResult",
    "CoverageInvalidationCandidateRef",
    "MaterialityPosture",
    "ModePermissionPosture",
    "MonotonicityPosture",
    "ProposalDisposition",
    "StaleCoverageCandidatePosture",
    "UserConfirmationPosture",
    "WeakeningPosture",
]
