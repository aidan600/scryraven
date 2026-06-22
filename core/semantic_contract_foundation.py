"""Passive semantic-contract foundation records for AG-SEM-01.

These records describe proposed question meaning, semantic slots, and answer
component contracts. They do not promote that proposal to accepted authority,
change runtime behavior, or construct search work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

SEMANTIC_CONTRACT_FOUNDATION_SCHEMA_VERSION = "semantic_contract_foundation_ag_sem_01_v1"
QUESTION_MEANING_TRACE_KEY = "question_meaning_record"

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
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "secret",
        "token",
    }
)
_MATERIAL_CHOICE_SLOT_KINDS = frozenset(
    {
        "entity",
        "variant",
        "metric",
        "time_period",
        "geography",
        "currency_basis",
        "inflation_basis",
        "configuration",
        "load_factor",
        "direct_vs_computed",
    }
)
_NON_MATERIAL_ADDITION_KINDS = (
    "caveat_recording",
    "already_implied_normalization_note",
    "strengthening_source_obligation",
    "bounded_explanatory_label",
)
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "author_input",
        "canonical_coverage",
        "coverage",
        "coverage_state",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "sufficiency",
        "sufficiency_judgment",
    }
)


class SemanticSlotKind(str, Enum):
    ENTITY = "entity"
    VARIANT = "variant"
    METRIC = "metric"
    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"
    TIME_PERIOD = "time_period"
    GEOGRAPHY = "geography"
    CURRENCY_BASIS = "currency_basis"
    INFLATION_BASIS = "inflation_basis"
    CONFIGURATION = "configuration"
    ROUTE_PROFILE = "route_profile"
    LOAD_FACTOR = "load_factor"
    DIRECT_VS_COMPUTED = "direct_vs_computed"
    SOURCE_BASIS = "source_basis"
    UNKNOWN_OR_OTHER = "unknown_or_other"


class SemanticSlotStatus(str, Enum):
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class Materiality(str, Enum):
    MATERIAL = "material"
    NON_MATERIAL = "non_material"
    UNKNOWN = "unknown"


class RequirementPosture(str, Enum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"


class SupportKind(str, Enum):
    DIRECT = "direct"
    INFERRED = "inferred"
    COMPUTED = "computed"


class PartialAnswerPolicy(str, Enum):
    QUALIFY_VISIBLE_GAP = "qualify_visible_gap"
    BLOCK_IF_REQUIRED_UNSATISFIED = "block_if_required_unsatisfied"
    ALLOW_IF_OPTIONAL_ONLY = "allow_if_optional_only"


class ResolverKind(str, Enum):
    PASSIVE_PROPOSAL = "passive_proposal"
    QUERY_SHAPE_SEEDED = "query_shape_seeded"
    HUMAN_AUTHORED = "human_authored"


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


@dataclass(frozen=True, slots=True)
class SemanticContractValidationResult:
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
class SemanticSlot:
    slot_id: str
    slot_kind: SemanticSlotKind | str
    status: SemanticSlotStatus | str = SemanticSlotStatus.UNRESOLVED
    candidate_values: tuple[str, ...] = ()
    selected_value: str | None = None
    materiality: Materiality | str = Materiality.UNKNOWN
    user_confirmation_required: bool = False
    normalization_notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.slot_id):
            raise ValueError("semantic slot requires slot_id")
        object.__setattr__(
            self,
            "slot_kind",
            _coerce_enum(SemanticSlotKind, self.slot_kind, SemanticSlotKind.UNKNOWN_OR_OTHER),
        )
        object.__setattr__(
            self,
            "status",
            _coerce_enum(SemanticSlotStatus, self.status, SemanticSlotStatus.UNRESOLVED),
        )
        object.__setattr__(
            self,
            "materiality",
            _coerce_enum(Materiality, self.materiality, Materiality.UNKNOWN),
        )
        object.__setattr__(self, "candidate_values", _text_tuple(self.candidate_values))
        object.__setattr__(
            self,
            "selected_value",
            _clean_text(self.selected_value, limit=220),
        )
        object.__setattr__(
            self,
            "normalization_notes",
            _text_tuple(self.normalization_notes, limit=260),
        )

    @property
    def materially_unresolved(self) -> bool:
        return self.materiality is Materiality.MATERIAL and self.status in {
            SemanticSlotStatus.AMBIGUOUS,
            SemanticSlotStatus.UNRESOLVED,
        }

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "slot_id": _clean_token(self.slot_id),
                "slot_kind": self.slot_kind.value,
                "status": self.status.value,
                "candidate_values": list(self.candidate_values),
                "selected_value": self.selected_value,
                "materiality": self.materiality.value,
                "user_confirmation_required": bool(self.user_confirmation_required),
                "normalization_notes": list(self.normalization_notes),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class AnswerComponentContract:
    component_id: str
    user_facing_label: str
    user_facing_question: str
    component_revision: str = "1"
    component_digest: str | None = None
    requirement_posture: RequirementPosture | str = RequirementPosture.REQUIRED
    acceptance_criteria: tuple[str, ...] = ()
    semantic_slot_ids: tuple[str, ...] = ()
    source_obligation_candidate_ids: tuple[str, ...] = ()
    source_obligation_candidate_refs: tuple[str, ...] = ()
    allowed_support_kinds: tuple[SupportKind | str, ...] = (SupportKind.DIRECT,)
    max_inference_depth: int = 0
    normalization_policy: str | None = None
    calculation_policy: str | None = None
    dependency_component_ids: tuple[str, ...] = ()
    partial_answer_policy: PartialAnswerPolicy | str = PartialAnswerPolicy.QUALIFY_VISIBLE_GAP
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    materiality: Materiality | str = Materiality.MATERIAL
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.component_id):
            raise ValueError("answer component contract requires component_id")
        object.__setattr__(
            self,
            "requirement_posture",
            _coerce_enum(
                RequirementPosture,
                self.requirement_posture,
                RequirementPosture.REQUIRED,
            ),
        )
        object.__setattr__(
            self,
            "allowed_support_kinds",
            _enum_tuple(SupportKind, self.allowed_support_kinds, SupportKind.DIRECT),
        )
        object.__setattr__(
            self,
            "partial_answer_policy",
            _coerce_enum(
                PartialAnswerPolicy,
                self.partial_answer_policy,
                PartialAnswerPolicy.QUALIFY_VISIBLE_GAP,
            ),
        )
        object.__setattr__(
            self,
            "materiality",
            _coerce_enum(Materiality, self.materiality, Materiality.MATERIAL),
        )
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision) or "1")
        object.__setattr__(self, "acceptance_criteria", _text_tuple(self.acceptance_criteria, limit=320))
        object.__setattr__(self, "semantic_slot_ids", _text_tuple(self.semantic_slot_ids))
        object.__setattr__(
            self,
            "source_obligation_candidate_ids",
            _text_tuple(self.source_obligation_candidate_ids),
        )
        object.__setattr__(
            self,
            "source_obligation_candidate_refs",
            _text_tuple(self.source_obligation_candidate_refs),
        )
        object.__setattr__(
            self,
            "dependency_component_ids",
            _text_tuple(self.dependency_component_ids),
        )
        object.__setattr__(
            self,
            "normalization_policy",
            _clean_text(self.normalization_policy, limit=300),
        )
        object.__setattr__(
            self,
            "calculation_policy",
            _clean_text(self.calculation_policy, limit=300),
        )
        object.__setattr__(self, "mandatory_caveats", _text_tuple(self.mandatory_caveats, limit=260))
        object.__setattr__(
            self,
            "prohibited_upgrades",
            _text_tuple(self.prohibited_upgrades, limit=260),
        )
        digest = _clean_token(self.component_digest, limit=96) or _digest_json(self._digest_payload())
        object.__setattr__(self, "component_digest", digest)

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "component_id": _clean_token(self.component_id),
            "component_revision": self.component_revision,
            "user_facing_label": _clean_text(self.user_facing_label, limit=180),
            "user_facing_question": _clean_text(self.user_facing_question, limit=400),
            "requirement_posture": self.requirement_posture.value,
            "acceptance_criteria": list(self.acceptance_criteria),
            "semantic_slot_ids": list(self.semantic_slot_ids),
            "source_obligation_candidate_ids": list(self.source_obligation_candidate_ids),
            "source_obligation_candidate_refs": list(self.source_obligation_candidate_refs),
            "allowed_support_kinds": [item.value for item in self.allowed_support_kinds],
            "max_inference_depth": int(self.max_inference_depth),
            "normalization_policy": self.normalization_policy,
            "calculation_policy": self.calculation_policy,
            "dependency_component_ids": list(self.dependency_component_ids),
            "partial_answer_policy": self.partial_answer_policy.value,
            "mandatory_caveats": list(self.mandatory_caveats),
            "prohibited_upgrades": list(self.prohibited_upgrades),
            "materiality": self.materiality.value,
            "metadata": _json_safe(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                **self._digest_payload(),
                "component_digest": self.component_digest,
            }
        )


@dataclass(frozen=True, slots=True)
class SourceObligationCandidateRef:
    candidate_id: str
    obligation_kind: str
    component_candidate_ids: tuple[str, ...] = ()
    strictness: str | None = None
    trace_only: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("source obligation candidate ref requires candidate_id")
        object.__setattr__(
            self,
            "component_candidate_ids",
            _text_tuple(self.component_candidate_ids),
        )
        object.__setattr__(self, "strictness", _clean_token(self.strictness))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "obligation_kind": _clean_token(self.obligation_kind),
                "component_candidate_ids": list(self.component_candidate_ids),
                "strictness": self.strictness,
                "trace_only": bool(self.trace_only),
                "accepted_authority": False,
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class QueryShapeAssessmentRef:
    assessment_id: str
    schema_version: str
    component_candidate_ids: tuple[str, ...] = ()
    source_obligation_candidate_ids: tuple[str, ...] = ()
    trace_only: bool = True
    promoted_to_authority: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.assessment_id):
            raise ValueError("query shape assessment ref requires assessment_id")
        object.__setattr__(
            self,
            "component_candidate_ids",
            _text_tuple(self.component_candidate_ids),
        )
        object.__setattr__(
            self,
            "source_obligation_candidate_ids",
            _text_tuple(self.source_obligation_candidate_ids),
        )

    @classmethod
    def from_assessment(cls, assessment: Any) -> "QueryShapeAssessmentRef":
        payload = assessment.to_dict() if hasattr(assessment, "to_dict") else dict(assessment)
        return cls(
            assessment_id=str(payload.get("assessment_id") or ""),
            schema_version=str(payload.get("schema_version") or "unknown"),
            component_candidate_ids=tuple(
                item.get("candidate_id")
                for item in payload.get("component_candidates") or ()
                if isinstance(item, Mapping)
            ),
            source_obligation_candidate_ids=tuple(
                item.get("candidate_id")
                for item in payload.get("source_obligation_candidates") or ()
                if isinstance(item, Mapping)
            ),
            metadata={
                "relationship": (
                    "QueryShapeAssessment may seed a passive question-meaning proposal but does not accept authority."
                )
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "assessment_id": _clean_token(self.assessment_id),
                "schema_version": _clean_token(self.schema_version),
                "component_candidate_ids": list(self.component_candidate_ids),
                "source_obligation_candidate_ids": list(self.source_obligation_candidate_ids),
                "trace_only": bool(self.trace_only),
                "promoted_to_authority": bool(self.promoted_to_authority),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class SearchWorkPlanRef:
    plan_id: str
    schema_version: str
    relationship: str = (
        "SearchWorkPlan remains work planning only; answer components remain the proposed answer-authority shape."
    )
    planning_only: bool = True
    semantic_owner: bool = False
    trace_only: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.plan_id):
            raise ValueError("search work plan ref requires plan_id")

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "plan_id": _clean_token(self.plan_id),
                "schema_version": _clean_token(self.schema_version),
                "relationship": _clean_text(self.relationship, limit=320),
                "planning_only": bool(self.planning_only),
                "semantic_owner": bool(self.semantic_owner),
                "trace_only": bool(self.trace_only),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class ContractLineage:
    contract_version: str = "0.1-passive"
    parent_contract_digest: str | None = None
    proposal_digest: str | None = None
    supersedes_record_id: str | None = None
    created_from: tuple[str, ...] = ("passive_question_meaning_proposal",)
    accepted_by: str | None = None
    accepted_contract_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _clean_token(self.contract_version) or "0.1-passive")
        object.__setattr__(
            self,
            "parent_contract_digest",
            _clean_token(self.parent_contract_digest, limit=96),
        )
        object.__setattr__(
            self,
            "proposal_digest",
            _clean_token(self.proposal_digest, limit=96),
        )
        object.__setattr__(
            self,
            "supersedes_record_id",
            _clean_token(self.supersedes_record_id),
        )
        object.__setattr__(self, "created_from", _text_tuple(self.created_from, limit=180))
        object.__setattr__(self, "accepted_by", None)
        object.__setattr__(self, "accepted_contract_ref", None)

    def with_proposal_digest(self, proposal_digest: str) -> "ContractLineage":
        return ContractLineage(
            contract_version=self.contract_version,
            parent_contract_digest=self.parent_contract_digest,
            proposal_digest=proposal_digest,
            supersedes_record_id=self.supersedes_record_id,
            created_from=self.created_from,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "contract_version": self.contract_version,
                "parent_contract_digest": self.parent_contract_digest,
                "proposal_digest": self.proposal_digest,
                "supersedes_record_id": self.supersedes_record_id,
                "created_from": list(self.created_from),
                "accepted_by": self.accepted_by,
                "accepted_contract_ref": self.accepted_contract_ref,
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class MaterialityPolicy:
    material_choices_requiring_confirmation: tuple[str, ...] = (
        "entity or product variant choices",
        "metric redefinition",
        "time period",
        "geography",
        "load factor",
        "configuration",
        "currency or inflation basis",
        "direct-source-bound fact vs computed estimate",
        "weakening or removing required component or source obligation",
    )
    non_material_additions: tuple[str, ...] = _NON_MATERIAL_ADDITION_KINDS
    auto_accepts_amendments: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "material_choices_requiring_confirmation",
            _text_tuple(self.material_choices_requiring_confirmation, limit=260),
        )
        object.__setattr__(
            self,
            "non_material_additions",
            _text_tuple(self.non_material_additions, limit=220),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_choices_requiring_confirmation": list(self.material_choices_requiring_confirmation),
            "non_material_additions": list(self.non_material_additions),
            "auto_accepts_amendments": bool(self.auto_accepts_amendments),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class QuestionMeaningRecord:
    record_id: str
    request_digest: str
    requested_mode: str
    resolver_kind: ResolverKind | str
    resolver_version: str
    intent: str
    requested_output: str
    semantic_slots: tuple[SemanticSlot, ...]
    answer_components: tuple[AnswerComponentContract, ...]
    run_id: str | None = None
    request_id: str | None = None
    source_obligation_candidate_refs: tuple[SourceObligationCandidateRef, ...] = ()
    query_shape_assessment_ref: QueryShapeAssessmentRef | None = None
    search_work_plan_ref: SearchWorkPlanRef | None = None
    contract_lineage: ContractLineage = field(default_factory=ContractLineage)
    materiality_policy: MaterialityPolicy = field(default_factory=MaterialityPolicy)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    canonical_state: bool = False
    runtime_behavior_changed: bool = False
    schema_version: str = SEMANTIC_CONTRACT_FOUNDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.record_id):
            raise ValueError("question meaning record requires record_id")
        if not _clean_token(self.request_digest, limit=128):
            raise ValueError("question meaning record requires request_digest")
        object.__setattr__(
            self,
            "resolver_kind",
            _coerce_enum(ResolverKind, self.resolver_kind, ResolverKind.PASSIVE_PROPOSAL),
        )
        object.__setattr__(self, "semantic_slots", tuple(self.semantic_slots or ()))
        object.__setattr__(self, "answer_components", tuple(self.answer_components or ()))
        object.__setattr__(
            self,
            "source_obligation_candidate_refs",
            tuple(self.source_obligation_candidate_refs or ()),
        )
        object.__setattr__(self, "run_id", _clean_token(self.run_id))
        object.__setattr__(self, "request_id", _clean_token(self.request_id))
        digest = self._record_digest()
        object.__setattr__(
            self,
            "contract_lineage",
            self.contract_lineage.with_proposal_digest(digest),
        )

    @classmethod
    def from_query_shape_assessment(
        cls,
        *,
        record_id: str,
        request_digest: str,
        requested_mode: str,
        intent: str,
        requested_output: str,
        semantic_slots: Sequence[SemanticSlot],
        answer_components: Sequence[AnswerComponentContract],
        assessment: Any,
        resolver_version: str = "ag-sem-01-passive",
        **kwargs: Any,
    ) -> "QuestionMeaningRecord":
        return cls(
            record_id=record_id,
            request_digest=request_digest,
            requested_mode=requested_mode,
            resolver_kind=ResolverKind.QUERY_SHAPE_SEEDED,
            resolver_version=resolver_version,
            intent=intent,
            requested_output=requested_output,
            semantic_slots=tuple(semantic_slots),
            answer_components=tuple(answer_components),
            query_shape_assessment_ref=QueryShapeAssessmentRef.from_assessment(assessment),
            **kwargs,
        )

    @property
    def material_ambiguity_count(self) -> int:
        return sum(1 for slot in self.semantic_slots if slot.materially_unresolved)

    @property
    def user_confirmation_required(self) -> bool:
        return any(slot.user_confirmation_required for slot in self.semantic_slots) or any(
            slot.materially_unresolved for slot in self.semantic_slots
        )

    @property
    def record_digest(self) -> str:
        return self._record_digest()

    def validate(self) -> SemanticContractValidationResult:
        errors: list[str] = []
        slot_ids = [slot.slot_id for slot in self.semantic_slots]
        slot_id_set = set(slot_ids)
        component_ids = [component.component_id for component in self.answer_components]
        component_id_set = set(component_ids)

        _add_duplicate_errors(errors, "semantic slot_id", slot_ids)
        _add_duplicate_errors(errors, "answer component_id", component_ids)
        if not self.semantic_slots:
            errors.append("at least one semantic slot is required")
        if not self.answer_components:
            errors.append("at least one answer component contract is required")

        for slot in self.semantic_slots:
            if slot.materially_unresolved and not slot.user_confirmation_required:
                errors.append(
                    f"semantic slot {slot.slot_id} is material and {slot.status.value}; user confirmation is required"
                )
            if (
                slot.slot_kind.value in _MATERIAL_CHOICE_SLOT_KINDS
                and slot.status in {SemanticSlotStatus.AMBIGUOUS, SemanticSlotStatus.UNRESOLVED}
                and not slot.user_confirmation_required
            ):
                errors.append(f"semantic slot {slot.slot_id} represents a material choice requiring confirmation")

        for component in self.answer_components:
            for slot_id in component.semantic_slot_ids:
                if slot_id not in slot_id_set:
                    errors.append(
                        f"answer component {component.component_id} references missing semantic slot {slot_id}"
                    )
            for dependency in component.dependency_component_ids:
                if dependency not in component_id_set:
                    errors.append(
                        f"answer component {component.component_id} depends on missing component {dependency}"
                    )
                if dependency == component.component_id:
                    errors.append(f"answer component {component.component_id} cannot depend on itself")
            if component.max_inference_depth < 0:
                errors.append(f"answer component {component.component_id} max_inference_depth cannot be negative")

        if self.search_work_plan_ref and self.search_work_plan_ref.semantic_owner:
            errors.append("SearchWorkPlan reference must remain planning-only")
        if self.query_shape_assessment_ref and self.query_shape_assessment_ref.promoted_to_authority:
            errors.append("QueryShapeAssessment reference must not be promoted to authority")
        if not self.passive:
            errors.append("question meaning record must remain passive")
        if self.canonical_state:
            errors.append("question meaning record cannot be canonical state in AG-SEM-01")
        if self.runtime_behavior_changed:
            errors.append("question meaning record cannot change runtime behavior in AG-SEM-01")

        encoded_keys = set(_collect_keys(self.to_dict(include_validation=False)))
        forbidden_present = sorted(encoded_keys & _FORBIDDEN_AUTHORITY_FIELDS)
        if forbidden_present:
            errors.append("question meaning record includes closed authority fields: " + ", ".join(forbidden_present))
        return SemanticContractValidationResult(errors=tuple(errors))

    def require_valid(self) -> "QuestionMeaningRecord":
        self.validate().raise_for_errors()
        return self

    def _record_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": _clean_token(self.record_id),
            "run_id": self.run_id,
            "request_id": self.request_id,
            "request_digest": _clean_token(self.request_digest, limit=128),
            "requested_mode": _clean_token(self.requested_mode),
            "resolver_kind": self.resolver_kind.value,
            "resolver_version": _clean_token(self.resolver_version),
            "intent": _clean_text(self.intent, limit=360),
            "requested_output": _clean_text(self.requested_output, limit=300),
            "semantic_slots": [slot.to_dict() for slot in self.semantic_slots],
            "answer_components": [component.to_dict() for component in self.answer_components],
            "source_obligation_candidate_refs": [ref.to_dict() for ref in self.source_obligation_candidate_refs],
            "query_shape_assessment_ref": (
                self.query_shape_assessment_ref.to_dict() if self.query_shape_assessment_ref else None
            ),
            "search_work_plan_ref": (self.search_work_plan_ref.to_dict() if self.search_work_plan_ref else None),
            "material_ambiguity_count": self.material_ambiguity_count,
            "user_confirmation_required": self.user_confirmation_required,
            "contract_lineage": self.contract_lineage.to_dict(),
            "materiality_policy": self.materiality_policy.to_dict(),
            "metadata": _json_safe(self.metadata),
            "passive": bool(self.passive),
            "canonical_state": bool(self.canonical_state),
            "runtime_behavior_changed": bool(self.runtime_behavior_changed),
            "accepted_authority": False,
            "runtime_consumed": False,
            "constructs_search_work_plan": False,
            "provider_search_behavior_changed": False,
        }

    def _record_digest(self) -> str:
        payload = self._record_payload()
        lineage = dict(payload.get("contract_lineage") or {})
        lineage.pop("proposal_digest", None)
        payload["contract_lineage"] = lineage
        return _digest_json(payload)

    def to_dict(self, *, include_validation: bool = True) -> dict[str, Any]:
        payload = _without_empty(
            {
                **self._record_payload(),
                "trace_key": QUESTION_MEANING_TRACE_KEY,
                "record_digest": self.record_digest,
            }
        )
        if include_validation:
            payload["validation"] = self.validate().to_dict()
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {QUESTION_MEANING_TRACE_KEY: self.to_dict()}


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
    "QUESTION_MEANING_TRACE_KEY",
    "SEMANTIC_CONTRACT_FOUNDATION_SCHEMA_VERSION",
    "AnswerComponentContract",
    "ContractLineage",
    "Materiality",
    "MaterialityPolicy",
    "PartialAnswerPolicy",
    "QueryShapeAssessmentRef",
    "QuestionMeaningRecord",
    "RequirementPosture",
    "ResolverKind",
    "SearchWorkPlanRef",
    "SemanticContractValidationResult",
    "SemanticSlot",
    "SemanticSlotKind",
    "SemanticSlotStatus",
    "SourceObligationCandidateRef",
    "SupportKind",
]
