"""Passive ComponentCoverageRecord schema for AG-SEM-03.

These records are future scoreboard entries for per-answer-component semantic
support. They do not reduce canonical coverage, update runtime state, consume
SufficiencyJudgment, trigger follow-up behavior, or create Author input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION = "component_coverage_record_ag_sem_03_v1"
COMPONENT_COVERAGE_RECORD_TRACE_KEY = "component_coverage_record"

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
_FORBIDDEN_RUNTIME_FIELDS = frozenset(
    {
        "author_input",
        "canonical_reducer",
        "final_answer",
        "final_answer_packet",
        "followup_loop_active",
        "query_plan_activation",
        "search_judgment_consumer",
        "support_reducer",
    }
)
_SATISFIED_STATES = frozenset({"satisfied"})
_NON_SATISFYING_EVIDENCE_BASIS = frozenset(
    {
        "candidate_discovery",
        "evidence_ledger_custody",
        "search_result_snippet",
        "provider_answer_product",
        "work_attempted",
        "work_completed",
        "ids_or_digests_only",
    }
)


class CoverageState(str, Enum):
    UNASSESSED = "unassessed"
    UNSUPPORTED = "unsupported"
    PARTIAL = "partial"
    SUPPORTED_WITH_CAVEATS = "supported_with_caveats"
    SATISFIED = "satisfied"
    CONFLICTED = "conflicted"
    BLOCKED = "blocked"
    STALE = "stale"


class EvidenceBasis(str, Enum):
    SEMANTIC_OBSERVATION = "semantic_observation"
    ANSWER_BEARING_CONTENT = "answer_bearing_content"
    EVIDENCE_LEDGER_CUSTODY = "evidence_ledger_custody"
    CANDIDATE_DISCOVERY = "candidate_discovery"
    SEARCH_RESULT_SNIPPET = "search_result_snippet"
    PROVIDER_ANSWER_PRODUCT = "provider_answer_product"
    WORK_ATTEMPTED = "work_attempted"
    WORK_COMPLETED = "work_completed"
    IDS_OR_DIGESTS_ONLY = "ids_or_digests_only"


class EvidenceCustodyStatus(str, Enum):
    UNBOUND = "unbound"
    SNAPSHOT_BOUND = "snapshot_bound"
    CUSTODIED = "custodied"
    PARTIAL = "partial"
    REJECTED = "rejected"
    STALE = "stale"
    UNKNOWN = "unknown"


class ContentAvailabilityStatus(str, Enum):
    MISSING = "missing"
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNREADABLE = "unreadable"
    STALE = "stale"
    UNKNOWN = "unknown"


class SourceObligationStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    UNSATISFIED = "unsatisfied"
    PARTIAL = "partial"
    SATISFIED = "satisfied"
    STALE = "stale"
    UNKNOWN = "unknown"


class SemanticSupportStatus(str, Enum):
    UNASSESSED = "unassessed"
    UNSUPPORTED = "unsupported"
    PARTIAL = "partial"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class SupportPosture(str, Enum):
    DIRECT = "direct"
    INFERRED = "inferred"
    COMPUTED = "computed"


class DerivedSupportStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"
    PREMISES_SUPPORTED = "premises_supported"
    COMPUTATION_SUPPORTED = "computation_supported"
    UNKNOWN = "unknown"


class ExplicitnessPosture(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class ConflictPosture(str, Enum):
    NONE = "none"
    RESOLVED = "resolved"
    PRESENT = "present"
    UNKNOWN = "unknown"


class CurrentnessPosture(str, Enum):
    CURRENT = "current"
    NOT_TIME_SENSITIVE = "not_time_sensitive"
    STALE = "stale"
    UNKNOWN = "unknown"


class FollowupNeed(str, Enum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ModeBudgetPosture(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    AVAILABLE = "available"
    EXHAUSTED = "exhausted"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class VersionValidity(str, Enum):
    VALID = "valid"
    STALE_CONTRACT = "stale_contract"
    STALE_EVIDENCE_LEDGER = "stale_evidence_ledger"
    COMPONENT_REVISION_MISMATCH = "component_revision_mismatch"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ComponentCoverageValidationResult:
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
class EvidenceLedgerSnapshotBinding:
    ledger_snapshot_id: str
    ledger_schema_version: str
    ledger_digest: str
    custody_status: EvidenceCustodyStatus | str = EvidenceCustodyStatus.UNKNOWN
    source_requirement_ids: tuple[str, ...] = ()
    ledger_observation_refs: tuple[str, ...] = ()
    version_validity: VersionValidity | str = VersionValidity.VALID

    def __post_init__(self) -> None:
        if not _clean_token(self.ledger_snapshot_id):
            raise ValueError("evidence ledger binding requires ledger_snapshot_id")
        if not _clean_token(self.ledger_schema_version):
            raise ValueError("evidence ledger binding requires ledger_schema_version")
        if not _clean_token(self.ledger_digest, limit=128):
            raise ValueError("evidence ledger binding requires ledger_digest")
        object.__setattr__(
            self,
            "custody_status",
            _coerce_enum(EvidenceCustodyStatus, self.custody_status, EvidenceCustodyStatus.UNKNOWN),
        )
        object.__setattr__(
            self,
            "source_requirement_ids",
            _text_tuple(self.source_requirement_ids),
        )
        object.__setattr__(
            self,
            "ledger_observation_refs",
            _text_tuple(self.ledger_observation_refs),
        )
        object.__setattr__(
            self,
            "version_validity",
            _coerce_enum(VersionValidity, self.version_validity, VersionValidity.VALID),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "ledger_snapshot_id": _clean_token(self.ledger_snapshot_id),
                "ledger_schema_version": _clean_token(self.ledger_schema_version),
                "ledger_digest": _clean_token(self.ledger_digest, limit=128),
                "custody_status": self.custody_status.value,
                "source_requirement_ids": list(self.source_requirement_ids),
                "ledger_observation_refs": list(self.ledger_observation_refs),
                "version_validity": self.version_validity.value,
            }
        )


@dataclass(frozen=True, slots=True)
class SemanticObservationCoverageRef:
    observation_id: str
    observation_digest: str
    answer_component_id: str
    component_revision: str
    component_contract_digest: str
    support_status: str
    support_posture: SupportPosture | str
    content_refs: tuple[str, ...] = ()
    accepted: bool = True
    semantic_observation_schema_version: str | None = None

    def __post_init__(self) -> None:
        if not _clean_token(self.observation_id):
            raise ValueError("semantic observation ref requires observation_id")
        if not _clean_token(self.observation_digest, limit=128):
            raise ValueError("semantic observation ref requires observation_digest")
        if not _clean_token(self.answer_component_id):
            raise ValueError("semantic observation ref requires answer_component_id")
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision) or "")
        object.__setattr__(
            self,
            "component_contract_digest",
            _clean_token(self.component_contract_digest, limit=128) or "",
        )
        object.__setattr__(
            self,
            "support_posture",
            _coerce_enum(SupportPosture, self.support_posture, SupportPosture.DIRECT),
        )
        object.__setattr__(self, "content_refs", _text_tuple(self.content_refs))

    @classmethod
    def from_observation(cls, observation: Mapping[str, Any] | Any) -> "SemanticObservationCoverageRef":
        payload = _record_mapping(observation)
        return cls(
            observation_id=str(payload.get("observation_id") or ""),
            observation_digest=str(payload.get("observation_digest") or ""),
            answer_component_id=str(payload.get("answer_component_id") or ""),
            component_revision=str(payload.get("component_revision") or ""),
            component_contract_digest=str(payload.get("component_contract_digest") or ""),
            support_status=str(payload.get("support_status") or "unknown"),
            support_posture=str(payload.get("directness") or payload.get("support_kind") or "direct"),
            content_refs=tuple(payload.get("content_refs") or ()),
            accepted=bool(payload.get("accepted", True)),
            semantic_observation_schema_version=_clean_token(payload.get("schema_version")),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "observation_id": _clean_token(self.observation_id),
                "observation_digest": _clean_token(self.observation_digest, limit=128),
                "answer_component_id": _clean_token(self.answer_component_id),
                "component_revision": self.component_revision,
                "component_contract_digest": self.component_contract_digest,
                "support_status": _clean_token(self.support_status),
                "support_posture": self.support_posture.value,
                "content_refs": list(self.content_refs),
                "accepted": bool(self.accepted),
                "semantic_observation_schema_version": _clean_token(self.semantic_observation_schema_version),
            }
        )


@dataclass(frozen=True, slots=True)
class ContentReferenceCoverageBinding:
    content_ref_id: str
    content_digest: str
    evidence_ref_id: str
    answer_component_id: str
    component_revision: str
    component_contract_digest: str
    answer_bearing: bool = True
    availability_status: ContentAvailabilityStatus | str = ContentAvailabilityStatus.AVAILABLE
    content_reference_schema_version: str | None = None

    def __post_init__(self) -> None:
        if not _clean_token(self.content_ref_id):
            raise ValueError("content reference binding requires content_ref_id")
        if not _clean_token(self.content_digest, limit=128):
            raise ValueError("content reference binding requires content_digest")
        if not _clean_token(self.evidence_ref_id):
            raise ValueError("content reference binding requires evidence_ref_id")
        if not _clean_token(self.answer_component_id):
            raise ValueError("content reference binding requires answer_component_id")
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision) or "")
        object.__setattr__(
            self,
            "component_contract_digest",
            _clean_token(self.component_contract_digest, limit=128) or "",
        )
        object.__setattr__(
            self,
            "availability_status",
            _coerce_enum(
                ContentAvailabilityStatus,
                self.availability_status,
                ContentAvailabilityStatus.UNKNOWN,
            ),
        )

    @classmethod
    def from_content_reference(
        cls,
        content_reference: Mapping[str, Any] | Any,
        *,
        answer_bearing: bool = True,
    ) -> "ContentReferenceCoverageBinding":
        payload = _record_mapping(content_reference)
        return cls(
            content_ref_id=str(payload.get("content_ref_id") or ""),
            content_digest=str(payload.get("content_digest") or ""),
            evidence_ref_id=str(payload.get("evidence_ref_id") or payload.get("admitted_evidence_ref") or ""),
            answer_component_id=str(payload.get("answer_component_id") or ""),
            component_revision=str(payload.get("component_revision") or ""),
            component_contract_digest=str(payload.get("component_contract_digest") or ""),
            answer_bearing=answer_bearing,
            availability_status=ContentAvailabilityStatus.AVAILABLE,
            content_reference_schema_version=_clean_token(payload.get("schema_version")),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "content_ref_id": _clean_token(self.content_ref_id),
                "content_digest": _clean_token(self.content_digest, limit=128),
                "evidence_ref_id": _clean_token(self.evidence_ref_id),
                "answer_component_id": _clean_token(self.answer_component_id),
                "component_revision": self.component_revision,
                "component_contract_digest": self.component_contract_digest,
                "answer_bearing": bool(self.answer_bearing),
                "availability_status": self.availability_status.value,
                "content_reference_schema_version": _clean_token(self.content_reference_schema_version),
            }
        )


@dataclass(frozen=True, slots=True)
class CoverageLineage:
    created_by: str = "ag-sem-03-passive-schema"
    created_from: tuple[str, ...] = ("passive_component_coverage_record",)
    supersedes_record_id: str | None = None
    parent_record_digest: str | None = None
    reducer_consumed: bool = False
    runtime_consumed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_by", _clean_token(self.created_by) or "ag-sem-03-passive-schema")
        object.__setattr__(self, "created_from", _text_tuple(self.created_from, limit=180))
        object.__setattr__(self, "supersedes_record_id", _clean_token(self.supersedes_record_id))
        object.__setattr__(self, "parent_record_digest", _clean_token(self.parent_record_digest, limit=128))
        object.__setattr__(self, "reducer_consumed", False)
        object.__setattr__(self, "runtime_consumed", False)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "created_by": self.created_by,
                "created_from": list(self.created_from),
                "supersedes_record_id": self.supersedes_record_id,
                "parent_record_digest": self.parent_record_digest,
                "reducer_consumed": False,
                "runtime_consumed": False,
            }
        )


@dataclass(frozen=True, slots=True)
class ComponentCoverageRecord:
    record_id: str
    run_id: str
    request_id: str
    request_digest: str
    accepted_contract_version: str
    accepted_contract_digest: str
    answer_component_id: str
    component_revision: str
    component_digest: str
    evidence_ledger_binding: EvidenceLedgerSnapshotBinding
    coverage_state: CoverageState | str = CoverageState.UNASSESSED
    semantic_support_status: SemanticSupportStatus | str = SemanticSupportStatus.UNASSESSED
    support_posture: SupportPosture | str = SupportPosture.DIRECT
    derived_support_status: DerivedSupportStatus | str = DerivedSupportStatus.NOT_APPLICABLE
    source_obligation_status: SourceObligationStatus | str = SourceObligationStatus.UNKNOWN
    content_availability_status: ContentAvailabilityStatus | str = ContentAvailabilityStatus.UNKNOWN
    evidence_custody_status: EvidenceCustodyStatus | str = EvidenceCustodyStatus.UNKNOWN
    version_validity: VersionValidity | str = VersionValidity.VALID
    accepted_observation_refs: tuple[SemanticObservationCoverageRef, ...] = ()
    content_reference_bindings: tuple[ContentReferenceCoverageBinding, ...] = ()
    evidence_basis: tuple[EvidenceBasis | str, ...] = ()
    normalization_posture: ExplicitnessPosture | str = ExplicitnessPosture.NOT_APPLICABLE
    assumption_posture: ExplicitnessPosture | str = ExplicitnessPosture.NOT_APPLICABLE
    conflict_posture: ConflictPosture | str = ConflictPosture.UNKNOWN
    currentness_posture: CurrentnessPosture | str = CurrentnessPosture.UNKNOWN
    remaining_unknowns: tuple[str, ...] = ()
    required_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    followup_need: FollowupNeed | str = FollowupNeed.UNKNOWN
    mode_budget_posture: ModeBudgetPosture | str = ModeBudgetPosture.UNKNOWN
    stale: bool = False
    diagnostic_score: float | None = None
    lineage: CoverageLineage = field(default_factory=CoverageLineage)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    canonical_state: bool = False
    runtime_behavior_changed: bool = False
    schema_version: str = COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "record_id",
            "run_id",
            "request_id",
            "request_digest",
            "accepted_contract_version",
            "accepted_contract_digest",
            "answer_component_id",
            "component_revision",
            "component_digest",
        ):
            if not _clean_token(getattr(self, field_name), limit=128):
                raise ValueError(f"component coverage record requires {field_name}")
        object.__setattr__(
            self,
            "coverage_state",
            _coerce_enum(CoverageState, self.coverage_state, CoverageState.UNASSESSED),
        )
        object.__setattr__(
            self,
            "semantic_support_status",
            _coerce_enum(SemanticSupportStatus, self.semantic_support_status, SemanticSupportStatus.UNASSESSED),
        )
        object.__setattr__(
            self,
            "support_posture",
            _coerce_enum(SupportPosture, self.support_posture, SupportPosture.DIRECT),
        )
        object.__setattr__(
            self,
            "derived_support_status",
            _coerce_enum(DerivedSupportStatus, self.derived_support_status, DerivedSupportStatus.NOT_APPLICABLE),
        )
        object.__setattr__(
            self,
            "source_obligation_status",
            _coerce_enum(SourceObligationStatus, self.source_obligation_status, SourceObligationStatus.UNKNOWN),
        )
        object.__setattr__(
            self,
            "content_availability_status",
            _coerce_enum(
                ContentAvailabilityStatus,
                self.content_availability_status,
                ContentAvailabilityStatus.UNKNOWN,
            ),
        )
        object.__setattr__(
            self,
            "evidence_custody_status",
            _coerce_enum(EvidenceCustodyStatus, self.evidence_custody_status, EvidenceCustodyStatus.UNKNOWN),
        )
        object.__setattr__(
            self,
            "version_validity",
            _coerce_enum(VersionValidity, self.version_validity, VersionValidity.VALID),
        )
        object.__setattr__(
            self,
            "accepted_observation_refs",
            tuple(self.accepted_observation_refs or ()),
        )
        object.__setattr__(
            self,
            "content_reference_bindings",
            tuple(self.content_reference_bindings or ()),
        )
        object.__setattr__(
            self,
            "evidence_basis",
            _enum_tuple(EvidenceBasis, self.evidence_basis, EvidenceBasis.IDS_OR_DIGESTS_ONLY),
        )
        object.__setattr__(
            self,
            "normalization_posture",
            _coerce_enum(ExplicitnessPosture, self.normalization_posture, ExplicitnessPosture.NOT_APPLICABLE),
        )
        object.__setattr__(
            self,
            "assumption_posture",
            _coerce_enum(ExplicitnessPosture, self.assumption_posture, ExplicitnessPosture.NOT_APPLICABLE),
        )
        object.__setattr__(
            self,
            "conflict_posture",
            _coerce_enum(ConflictPosture, self.conflict_posture, ConflictPosture.UNKNOWN),
        )
        object.__setattr__(
            self,
            "currentness_posture",
            _coerce_enum(CurrentnessPosture, self.currentness_posture, CurrentnessPosture.UNKNOWN),
        )
        object.__setattr__(self, "remaining_unknowns", _text_tuple(self.remaining_unknowns, limit=360))
        object.__setattr__(self, "required_caveats", _text_tuple(self.required_caveats, limit=360))
        object.__setattr__(self, "prohibited_upgrades", _text_tuple(self.prohibited_upgrades, limit=360))
        object.__setattr__(
            self,
            "followup_need",
            _coerce_enum(FollowupNeed, self.followup_need, FollowupNeed.UNKNOWN),
        )
        object.__setattr__(
            self,
            "mode_budget_posture",
            _coerce_enum(ModeBudgetPosture, self.mode_budget_posture, ModeBudgetPosture.UNKNOWN),
        )
        object.__setattr__(self, "passive", True)
        object.__setattr__(self, "canonical_state", False)
        object.__setattr__(self, "runtime_behavior_changed", False)

    @property
    def record_digest(self) -> str:
        return _digest_json(self._record_digest_payload())

    def validate(
        self,
        *,
        content_references: Sequence[Mapping[str, Any] | Any] | None = None,
        observations: Sequence[Mapping[str, Any] | Any] | None = None,
    ) -> ComponentCoverageValidationResult:
        errors: list[str] = []
        payload = self.to_dict(include_validation=False)
        _add_duplicate_errors(
            errors,
            "accepted observation refs",
            [ref.observation_id for ref in self.accepted_observation_refs],
        )
        _add_duplicate_errors(
            errors,
            "content reference bindings",
            [ref.content_ref_id for ref in self.content_reference_bindings],
        )
        if self.diagnostic_score is not None and not 0 <= self.diagnostic_score <= 1:
            errors.append("diagnostic_score must be between 0 and 1")
        if self.diagnostic_score is not None and self.coverage_state is CoverageState.SATISFIED:
            errors.append("diagnostic_score is non-authoritative and cannot justify satisfied coverage")
        if not payload.get("passive"):
            errors.append("component coverage record must remain passive")
        if payload.get("canonical_state"):
            errors.append("component coverage record cannot be canonical state in AG-SEM-03")
        if payload.get("runtime_behavior_changed"):
            errors.append("component coverage record cannot change runtime behavior in AG-SEM-03")
        if self.lineage.reducer_consumed or self.lineage.runtime_consumed:
            errors.append("component coverage lineage must not be reducer or runtime consumed in AG-SEM-03")
        if self.coverage_state is CoverageState.STALE and not self.stale:
            errors.append("stale coverage state requires stale=True")
        if self.stale and self.coverage_state is CoverageState.SATISFIED:
            errors.append("stale coverage cannot present as satisfied")
        if self.coverage_state is CoverageState.CONFLICTED and self.conflict_posture in {
            ConflictPosture.NONE,
            ConflictPosture.RESOLVED,
        }:
            errors.append("conflicted coverage requires present or unknown conflict posture")
        if self.coverage_state is CoverageState.SATISFIED:
            errors.extend(self._validate_satisfied_requirements())
        errors.extend(self._validate_component_bindings())
        if content_references is not None:
            errors.extend(self._validate_content_reference_inputs(content_references))
        if observations is not None:
            errors.extend(self._validate_observation_inputs(observations))
        forbidden_present = sorted(_collect_keys(payload) & _FORBIDDEN_RUNTIME_FIELDS)
        if forbidden_present:
            errors.append("component coverage record includes closed runtime fields: " + ", ".join(forbidden_present))
        return ComponentCoverageValidationResult(errors=tuple(errors))

    def require_valid(
        self,
        *,
        content_references: Sequence[Mapping[str, Any] | Any] | None = None,
        observations: Sequence[Mapping[str, Any] | Any] | None = None,
    ) -> "ComponentCoverageRecord":
        self.validate(content_references=content_references, observations=observations).raise_for_errors()
        return self

    def _validate_satisfied_requirements(self) -> list[str]:
        errors: list[str] = []
        basis = {item.value for item in self.evidence_basis}
        if not self.accepted_contract_version or not self.accepted_contract_digest:
            errors.append("satisfied coverage requires accepted contract version and digest")
        if not self.component_revision or not self.component_digest:
            errors.append("satisfied coverage requires component revision and digest")
        if not self.accepted_observation_refs:
            errors.append("satisfied coverage requires accepted SemanticObservation refs")
        if not self.content_reference_bindings:
            errors.append("satisfied coverage requires answer-bearing content reference bindings")
        if not any(ref.answer_bearing for ref in self.content_reference_bindings):
            errors.append("satisfied coverage requires at least one answer-bearing content reference")
        if EvidenceBasis.SEMANTIC_OBSERVATION.value not in basis:
            errors.append("satisfied coverage requires semantic_observation evidence basis")
        if EvidenceBasis.ANSWER_BEARING_CONTENT.value not in basis:
            errors.append("satisfied coverage requires answer_bearing_content evidence basis")
        if basis and basis <= _NON_SATISFYING_EVIDENCE_BASIS:
            errors.append(
                "satisfied coverage cannot be based solely on identities, discovery, snippets, provider products, or work status"
            )
        if self.semantic_support_status is not SemanticSupportStatus.SUPPORTED:
            errors.append("satisfied coverage requires supported semantic support status")
        if self.content_availability_status is not ContentAvailabilityStatus.AVAILABLE:
            errors.append("satisfied coverage requires available answer-bearing content")
        if self.evidence_custody_status is not EvidenceCustodyStatus.CUSTODIED:
            errors.append("satisfied coverage requires EvidenceLedger custody")
        if self.evidence_ledger_binding.custody_status is not EvidenceCustodyStatus.CUSTODIED:
            errors.append("satisfied coverage requires custodied EvidenceLedger snapshot binding")
        if self.source_obligation_status not in {
            SourceObligationStatus.SATISFIED,
            SourceObligationStatus.NOT_APPLICABLE,
        }:
            errors.append("satisfied coverage requires satisfied or not-applicable source obligations")
        if self.version_validity is not VersionValidity.VALID:
            errors.append("satisfied coverage requires valid contract, component, and EvidenceLedger versions")
        if self.evidence_ledger_binding.version_validity is not VersionValidity.VALID:
            errors.append("satisfied coverage requires a non-stale EvidenceLedger version")
        if self.support_posture in {SupportPosture.INFERRED, SupportPosture.COMPUTED}:
            if self.derived_support_status not in {
                DerivedSupportStatus.PREMISES_SUPPORTED,
                DerivedSupportStatus.COMPUTATION_SUPPORTED,
            }:
                errors.append("satisfied inferred or computed coverage requires supported premises or computation")
            if self.assumption_posture is not ExplicitnessPosture.EXPLICIT:
                errors.append("satisfied inferred or computed coverage requires explicit assumptions")
        if (
            self.support_posture is SupportPosture.COMPUTED
            and self.normalization_posture is not ExplicitnessPosture.EXPLICIT
        ):
            errors.append("satisfied computed coverage requires explicit normalization")
        if self.conflict_posture not in {ConflictPosture.NONE, ConflictPosture.RESOLVED}:
            errors.append("satisfied coverage requires no unresolved conflict")
        if self.currentness_posture not in {
            CurrentnessPosture.CURRENT,
            CurrentnessPosture.NOT_TIME_SENSITIVE,
        }:
            errors.append("satisfied coverage requires current or not-time-sensitive currentness posture")
        if self.remaining_unknowns:
            errors.append("satisfied coverage cannot carry remaining unknowns")
        if self.followup_need is not FollowupNeed.NONE:
            errors.append("satisfied coverage cannot require follow-up")
        if self.mode_budget_posture in {ModeBudgetPosture.EXHAUSTED, ModeBudgetPosture.BLOCKED}:
            errors.append("satisfied coverage cannot depend on exhausted or blocked mode budget")
        return errors

    def _validate_component_bindings(self) -> list[str]:
        errors: list[str] = []
        for ref in self.accepted_observation_refs:
            if not ref.accepted:
                errors.append(f"semantic observation ref {ref.observation_id} is not accepted")
            if ref.answer_component_id != self.answer_component_id:
                errors.append(f"semantic observation ref {ref.observation_id} is bound to another component")
            if ref.component_revision and ref.component_revision != self.component_revision:
                errors.append(f"semantic observation ref {ref.observation_id} is bound to another component revision")
            if ref.component_contract_digest and ref.component_contract_digest != self.component_digest:
                errors.append(f"semantic observation ref {ref.observation_id} component digest mismatch")
            if ref.support_status not in {"supports", "qualifies"} and self.coverage_state in _SATISFIED_STATES:
                errors.append(f"semantic observation ref {ref.observation_id} does not support satisfied coverage")
        content_by_id = {binding.content_ref_id: binding for binding in self.content_reference_bindings}
        content_ids = set(content_by_id)
        for ref in self.accepted_observation_refs:
            missing_refs = [content_ref for content_ref in ref.content_refs if content_ref not in content_ids]
            if missing_refs and self.coverage_state is CoverageState.SATISFIED:
                errors.append(
                    f"semantic observation ref {ref.observation_id} has unbound content refs: "
                    + ", ".join(missing_refs)
                )
            if (
                self.coverage_state is CoverageState.SATISFIED
                and ref.support_status in {"supports", "qualifies"}
                and not any(
                    (binding := content_by_id.get(content_ref))
                    and binding.answer_bearing
                    and binding.availability_status is ContentAvailabilityStatus.AVAILABLE
                    for content_ref in ref.content_refs
                )
            ):
                errors.append(
                    f"semantic observation ref {ref.observation_id} requires at least one "
                    "answer-bearing available content ref for satisfied coverage"
                )
        for binding in self.content_reference_bindings:
            if binding.answer_component_id != self.answer_component_id:
                errors.append(f"content ref {binding.content_ref_id} is bound to another component")
            if binding.component_revision and binding.component_revision != self.component_revision:
                errors.append(f"content ref {binding.content_ref_id} is bound to another component revision")
            if binding.component_contract_digest and binding.component_contract_digest != self.component_digest:
                errors.append(f"content ref {binding.content_ref_id} component digest mismatch")
            if (
                self.coverage_state is CoverageState.SATISFIED
                and binding.availability_status is not ContentAvailabilityStatus.AVAILABLE
            ):
                errors.append(f"content ref {binding.content_ref_id} is not available for satisfied coverage")
        return errors

    def _validate_content_reference_inputs(self, content_references: Sequence[Mapping[str, Any] | Any]) -> list[str]:
        errors: list[str] = []
        by_id = {_record_mapping(ref).get("content_ref_id"): _record_mapping(ref) for ref in content_references}
        for binding in self.content_reference_bindings:
            payload = by_id.get(binding.content_ref_id)
            if payload is None:
                errors.append(f"component coverage references missing content ref {binding.content_ref_id}")
                continue
            if payload.get("answer_component_id") != self.answer_component_id:
                errors.append(f"content ref {binding.content_ref_id} input component does not match coverage record")
            if payload.get("component_revision") and payload.get("component_revision") != self.component_revision:
                errors.append(f"content ref {binding.content_ref_id} input revision does not match coverage record")
            if (
                payload.get("component_contract_digest")
                and payload.get("component_contract_digest") != self.component_digest
            ):
                errors.append(
                    f"content ref {binding.content_ref_id} input component digest does not match coverage record"
                )
        return errors

    def _validate_observation_inputs(self, observations: Sequence[Mapping[str, Any] | Any]) -> list[str]:
        errors: list[str] = []
        by_id = {_record_mapping(ref).get("observation_id"): _record_mapping(ref) for ref in observations}
        for ref in self.accepted_observation_refs:
            payload = by_id.get(ref.observation_id)
            if payload is None:
                errors.append(f"component coverage references missing SemanticObservation {ref.observation_id}")
                continue
            if payload.get("answer_component_id") != self.answer_component_id:
                errors.append(
                    f"SemanticObservation {ref.observation_id} input component does not match coverage record"
                )
            if payload.get("component_revision") and payload.get("component_revision") != self.component_revision:
                errors.append(f"SemanticObservation {ref.observation_id} input revision does not match coverage record")
            if (
                payload.get("component_contract_digest")
                and payload.get("component_contract_digest") != self.component_digest
            ):
                errors.append(
                    f"SemanticObservation {ref.observation_id} input component digest does not match coverage record"
                )
        return errors

    def _record_digest_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": _clean_token(self.record_id),
            "run_id": _clean_token(self.run_id),
            "request_id": _clean_token(self.request_id),
            "request_digest": _clean_token(self.request_digest, limit=128),
            "accepted_contract_version": _clean_token(self.accepted_contract_version),
            "accepted_contract_digest": _clean_token(self.accepted_contract_digest, limit=128),
            "answer_component_id": _clean_token(self.answer_component_id),
            "component_revision": _clean_token(self.component_revision),
            "component_digest": _clean_token(self.component_digest, limit=128),
            "evidence_ledger_binding": self.evidence_ledger_binding.to_dict(),
            "coverage_state": self.coverage_state.value,
            "semantic_support_status": self.semantic_support_status.value,
            "support_posture": self.support_posture.value,
            "derived_support_status": self.derived_support_status.value,
            "source_obligation_status": self.source_obligation_status.value,
            "content_availability_status": self.content_availability_status.value,
            "evidence_custody_status": self.evidence_custody_status.value,
            "version_validity": self.version_validity.value,
            "accepted_observation_refs": [ref.to_dict() for ref in self.accepted_observation_refs],
            "content_reference_bindings": [ref.to_dict() for ref in self.content_reference_bindings],
            "evidence_basis": [item.value for item in self.evidence_basis],
            "normalization_posture": self.normalization_posture.value,
            "assumption_posture": self.assumption_posture.value,
            "conflict_posture": self.conflict_posture.value,
            "currentness_posture": self.currentness_posture.value,
            "remaining_unknowns": list(self.remaining_unknowns),
            "required_caveats": list(self.required_caveats),
            "prohibited_upgrades": list(self.prohibited_upgrades),
            "followup_need": self.followup_need.value,
            "mode_budget_posture": self.mode_budget_posture.value,
            "stale": bool(self.stale),
            "diagnostic_score": self.diagnostic_score,
            "lineage": self.lineage.to_dict(),
            "metadata": _json_safe(self.metadata),
            "passive": True,
            "canonical_state": False,
            "runtime_behavior_changed": False,
            "accepted_authority": False,
        }

    def to_dict(self, *, include_validation: bool = True) -> dict[str, Any]:
        payload = _without_empty(
            {
                **self._record_digest_payload(),
                "trace_key": COMPONENT_COVERAGE_RECORD_TRACE_KEY,
                "record_digest": self.record_digest,
            }
        )
        if include_validation:
            payload["validation"] = self.validate().to_dict()
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {COMPONENT_COVERAGE_RECORD_TRACE_KEY: self.to_dict()}


def _record_mapping(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        mapped = value.to_dict(include_validation=False)
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return dict(value) if isinstance(value, Mapping) else {}


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


def _enum_tuple(
    enum_class: type[Enum],
    value: Sequence[Any] | None,
    default: Enum,
) -> tuple[Enum, ...]:
    return tuple(_coerce_enum(enum_class, item, default) for item in value or ())


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
    "COMPONENT_COVERAGE_RECORD_SCHEMA_VERSION",
    "COMPONENT_COVERAGE_RECORD_TRACE_KEY",
    "ComponentCoverageRecord",
    "ComponentCoverageValidationResult",
    "ConflictPosture",
    "ContentAvailabilityStatus",
    "ContentReferenceCoverageBinding",
    "CoverageLineage",
    "CoverageState",
    "CurrentnessPosture",
    "DerivedSupportStatus",
    "EvidenceBasis",
    "EvidenceCustodyStatus",
    "EvidenceLedgerSnapshotBinding",
    "ExplicitnessPosture",
    "FollowupNeed",
    "ModeBudgetPosture",
    "SemanticObservationCoverageRef",
    "SemanticSupportStatus",
    "SourceObligationStatus",
    "SupportPosture",
    "VersionValidity",
]
