"""Passive query-shape and contract-resolution records for AG-96C4.

The records in this module are representational only. They describe future
query-shape assessment, requested-mode contract resolution, and the future
SearchWorkPlan construction handoff without classifying queries at runtime,
constructing SearchWorkPlan, calling providers/search/retrieval, mutating
RunKernel, or changing prompt behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from core.semantic_contract_foundation import (
    SourceObligationKind,
    SourceObligationStrictness,
)


class SearchMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"
    AUTO = "auto"
    UNRESOLVED = "unresolved"


class EffectiveContractKind(str, Enum):
    DIRECT_CONSTRAINED = "direct_constrained"
    EXPLANATORY = "explanatory"
    RESEARCH_RECONCILIATION = "research_reconciliation"
    AUTO_UNRESOLVED = "auto_unresolved"


class ModeMismatchPosture(str, Enum):
    NONE = "none"
    POSSIBLE = "possible"
    SELECTED_MODE_INSUFFICIENT = "selected_mode_insufficient"
    QUALIFY_OR_REFUSE = "qualify_or_refuse"
    ESCALATE_SUGGESTED = "escalate_suggested"


class QueryShapeKind(str, Enum):
    SIMPLE_LOOKUP = "simple_lookup"
    MULTIPART = "multipart"
    COMPARATIVE = "comparative"
    QUANTITATIVE_COMPARISON = "quantitative_comparison"
    OFFICIAL_CURRENT_LOOKUP = "official_current_lookup"
    LEGAL_CURRENT_PRIMARY = "legal_current_primary"
    CANONICAL_DOCUMENTATION = "canonical_documentation"
    SOURCE_BOUND_NUMERIC = "source_bound_numeric"
    AMBIGUOUS_ENTITY = "ambiguous_entity"
    TIME_SENSITIVE = "time_sensitive"
    CONFLICT_LIKELY = "conflict_likely"
    NORMALIZATION_REQUIRED = "normalization_required"
    MODE_MISMATCH_POSSIBLE = "mode_mismatch_possible"


class ProviderJobKind(str, Enum):
    SCOUT_DISAMBIGUATION = "scout_disambiguation"
    DIRECT_CANDIDATE_SEARCH = "direct_candidate_search"
    OFFICIAL_CANDIDATE_ACQUISITION = "official_candidate_acquisition"
    SEMANTIC_RECALL = "semantic_recall"
    FETCH_READ_EXTRACT = "fetch_read_extract"
    BRIDGE_HINT_DISCOVERY = "bridge_hint_discovery"
    CONFLICT_CURRENTNESS_CHECK = "conflict_currentness_check"
    CANONICAL_EXTRACTION = "canonical_extraction"
    RECONCILIATION_SUPPORT = "reconciliation_support"


class StopConditionKind(str, Enum):
    COMPONENT_SUFFICIENT = "component_sufficient"
    SOURCE_OBLIGATION_UNSATISFIED = "source_obligation_unsatisfied"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MODE_MISMATCH = "mode_mismatch"
    REQUIRED_INFERENCE_EXCEEDS_SELECTED_MODE = "required_inference_exceeds_selected_mode"
    MISSING_SOURCE_BOUND_NUMERIC_VALUES = "missing_source_bound_numeric_values"
    UNRESOLVED_CONFLICT_CURRENTNESS = "unresolved_conflict_currentness"
    LIVE_VALIDATION_NOT_AUTHORIZED = "live_validation_not_authorized"


class AuditScope(str, Enum):
    CLAIM_CHALLENGE = "claim_challenge"
    ASSUMPTION_RED_TEAM = "assumption_red_team"
    SOURCE_CONFLICT_RECONCILIATION = "source_conflict_reconciliation"
    CURRENTNESS_AUDIT = "currentness_audit"
    QUANTITATIVE_ASSUMPTION_AUDIT = "quantitative_assumption_audit"


class RemediationPermission(str, Enum):
    NOT_ALLOWED = "not_allowed"
    CONDITIONAL_PASSIVE = "conditional_passive"
    AUTHORIZE_BY_JUDGMENT_ONLY = "authorize_by_judgment_only"


QUERY_SHAPE_CONTRACT_RESOLUTION_SCHEMA_VERSION = "query_shape_contract_resolution_ag96c4_v1"
QUERY_SHAPE_ASSESSMENT_TRACE_KEY = "query_shape_assessment"
CONTRACT_RESOLUTION_TRACE_KEY = "contract_resolution_record"
SEARCH_WORK_PLAN_CONSTRUCTION_DESIGN_TRACE_KEY = "search_work_plan_construction_design"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output",
        "output_artifact",
        "output_packet",
        "password",
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
_VALID_AUTHORITY_POSTURES = frozenset(
    {
        "RunAuthority",
        "RunAuthority chain",
        "RunKernel",
        "SearchJudgment",
        "SufficiencyJudgment",
    }
)
_VALID_FOLLOW_UP_AUTHORIZERS = frozenset(
    {
        "RunAuthority",
        "RunKernel",
        "SearchJudgment",
        "SufficiencyJudgment",
    }
)
_FORBIDDEN_EXECUTOR_AUTHORIZERS = frozenset(
    {
        "Analyst",
        "Author",
        "Economist",
        "Scout",
        "Scrutineer",
    }
)
_STRICT_SOURCE_OBLIGATION_KINDS = frozenset(
    {
        SourceObligationKind.OFFICIAL_CURRENT,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY,
        SourceObligationKind.CANONICAL_DOCUMENTATION,
        SourceObligationKind.SOURCE_BOUND_NUMERIC,
    }
)


class AssessmentPosture(str, Enum):
    PASSIVE_CANDIDATE = "passive_candidate"
    DETERMINISTIC_SIGNAL_ONLY = "deterministic_signal_only"
    MODEL_ASSISTED_CANDIDATE = "model_assisted_candidate"
    FIRST_PASS_EVIDENCE_NEEDED = "first_pass_evidence_needed"


class AssessmentConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TENTATIVE = "tentative"


class FollowUpDepthPosture(str, Enum):
    NONE_OR_MINIMAL = "none_or_minimal"
    CONDITIONAL_GAP_DRIVEN = "conditional_gap_driven"
    LARGER_BOUNDED_LOOP = "larger_bounded_loop"
    NOT_AUTHORIZED = "not_authorized"


class OutputPosture(str, Enum):
    DIRECT = "direct"
    COMPACT_EXPLANATORY = "compact_explanatory"
    RESOLVED_DEPTH = "resolved_depth"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    REFUSAL_OR_FAILURE_CARD = "refusal_or_failure_card"


class StopEscalateRefusePosture(str, Enum):
    STOP_WHEN_SUFFICIENT = "stop_when_sufficient"
    QUALIFY_IF_UNSATISFIED = "qualify_if_unsatisfied"
    ESCALATE_SUGGESTED = "escalate_suggested"
    REFUSE_OR_FAIL_CLOSED = "refuse_or_fail_closed"


class ConstructionPosture(str, Enum):
    PASSIVE_DESIGN_ONLY = "passive_design_only"


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
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


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


@dataclass(frozen=True, slots=True)
class QueryShapeContractValidationResult:
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
class ComponentCandidate:
    candidate_id: str
    component_id: str
    user_facing_subquestion: str
    entities: tuple[str, ...] = ()
    source_obligation_candidate_ids: tuple[str, ...] = ()
    provider_job_candidate_ids: tuple[str, ...] = ()
    normalization_notes: tuple[str, ...] = ()
    future_search_work_plan_field: str = "components"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("component candidate requires candidate_id")
        if not _clean_token(self.component_id):
            raise ValueError("component candidate requires component_id")
        object.__setattr__(self, "entities", _text_tuple(self.entities))
        object.__setattr__(
            self,
            "source_obligation_candidate_ids",
            _text_tuple(self.source_obligation_candidate_ids),
        )
        object.__setattr__(
            self,
            "provider_job_candidate_ids",
            _text_tuple(self.provider_job_candidate_ids),
        )
        object.__setattr__(
            self,
            "normalization_notes",
            _text_tuple(self.normalization_notes, limit=260),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "component_id": _clean_token(self.component_id),
                "user_facing_subquestion": _clean_text(
                    self.user_facing_subquestion,
                    limit=300,
                ),
                "entities": list(self.entities),
                "source_obligation_candidate_ids": list(self.source_obligation_candidate_ids),
                "provider_job_candidate_ids": list(self.provider_job_candidate_ids),
                "normalization_notes": list(self.normalization_notes),
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class SourceObligationCandidate:
    candidate_id: str
    obligation_id: str
    component_ids: tuple[str, ...]
    kind: SourceObligationKind | str
    strictness: SourceObligationStrictness | str = SourceObligationStrictness.REQUIRED
    required_source_class: str | None = None
    currentness_requirement: str | None = None
    satisfaction_rule: str | None = None
    lower_tier_use: str | None = None
    lower_tier_final_satisfaction_allowed: bool = False
    future_search_work_plan_field: str = "source_obligations"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("source obligation candidate requires candidate_id")
        if not _clean_token(self.obligation_id):
            raise ValueError("source obligation candidate requires obligation_id")
        object.__setattr__(
            self,
            "kind",
            _coerce_enum(
                SourceObligationKind,
                self.kind,
                SourceObligationKind.NO_SPECIAL_OBLIGATION,
            ),
        )
        object.__setattr__(
            self,
            "strictness",
            _coerce_enum(
                SourceObligationStrictness,
                self.strictness,
                SourceObligationStrictness.CONTEXTUAL,
            ),
        )
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "obligation_id": _clean_token(self.obligation_id),
                "component_ids": list(self.component_ids),
                "kind": self.kind.value,
                "strictness": self.strictness.value,
                "required_source_class": _clean_token(self.required_source_class),
                "currentness_requirement": _clean_text(
                    self.currentness_requirement,
                    limit=180,
                ),
                "satisfaction_rule": _clean_text(self.satisfaction_rule, limit=300),
                "lower_tier_use": _clean_text(self.lower_tier_use, limit=260),
                "lower_tier_final_satisfaction_allowed": bool(
                    self.lower_tier_final_satisfaction_allowed
                ),
                "cannot_downgrade_strong_obligation": self.kind
                in _STRICT_SOURCE_OBLIGATION_KINDS,
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class ProviderJobCandidate:
    candidate_id: str
    provider_job_id: str
    component_ids: tuple[str, ...]
    job_kind: ProviderJobKind | str
    source_obligation_candidate_ids: tuple[str, ...] = ()
    provider_name_neutral: bool = True
    future_search_work_plan_field: str = "provider_jobs"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("provider job candidate requires candidate_id")
        if not _clean_token(self.provider_job_id):
            raise ValueError("provider job candidate requires provider_job_id")
        object.__setattr__(
            self,
            "job_kind",
            _coerce_enum(ProviderJobKind, self.job_kind, ProviderJobKind.DIRECT_CANDIDATE_SEARCH),
        )
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(
            self,
            "source_obligation_candidate_ids",
            _text_tuple(self.source_obligation_candidate_ids),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "provider_job_id": _clean_token(self.provider_job_id),
                "component_ids": list(self.component_ids),
                "job_kind": self.job_kind.value,
                "source_obligation_candidate_ids": list(
                    self.source_obligation_candidate_ids
                ),
                "provider_name_neutral": bool(self.provider_name_neutral),
                "executes_search": False,
                "provider_search_behavior_changed": False,
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class QuantWorkCandidate:
    candidate_id: str
    quant_unit_id: str
    component_ids: tuple[str, ...]
    target_metric: str
    required_variables: tuple[str, ...] = ()
    source_bound_values_needed: tuple[str, ...] = ()
    allowed_calculations: tuple[str, ...] = ()
    assumptions_needed: tuple[str, ...] = ()
    future_search_work_plan_field: str = "quant_work_units"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("quant work candidate requires candidate_id")
        if not _clean_token(self.quant_unit_id):
            raise ValueError("quant work candidate requires quant_unit_id")
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(self, "required_variables", _text_tuple(self.required_variables))
        object.__setattr__(
            self,
            "source_bound_values_needed",
            _text_tuple(self.source_bound_values_needed),
        )
        object.__setattr__(
            self,
            "allowed_calculations",
            _text_tuple(self.allowed_calculations, limit=260),
        )
        object.__setattr__(
            self,
            "assumptions_needed",
            _text_tuple(self.assumptions_needed, limit=220),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "quant_unit_id": _clean_token(self.quant_unit_id),
                "component_ids": list(self.component_ids),
                "target_metric": _clean_text(self.target_metric, limit=220),
                "required_variables": list(self.required_variables),
                "source_bound_values_needed": list(self.source_bound_values_needed),
                "allowed_calculations": list(self.allowed_calculations),
                "assumptions_needed": list(self.assumptions_needed),
                "executes_calculations": False,
                "executes_code": False,
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class AuditJobCandidate:
    candidate_id: str
    audit_job_id: str
    component_ids: tuple[str, ...]
    audit_scope: AuditScope | str
    claim_types: tuple[str, ...] = ()
    assumptions_to_test: tuple[str, ...] = ()
    remediation_permission: RemediationPermission | str = RemediationPermission.CONDITIONAL_PASSIVE
    future_search_work_plan_field: str = "audit_jobs"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("audit job candidate requires candidate_id")
        if not _clean_token(self.audit_job_id):
            raise ValueError("audit job candidate requires audit_job_id")
        object.__setattr__(
            self,
            "audit_scope",
            _coerce_enum(AuditScope, self.audit_scope, AuditScope.CLAIM_CHALLENGE),
        )
        object.__setattr__(
            self,
            "remediation_permission",
            _coerce_enum(
                RemediationPermission,
                self.remediation_permission,
                RemediationPermission.CONDITIONAL_PASSIVE,
            ),
        )
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(self, "claim_types", _text_tuple(self.claim_types))
        object.__setattr__(
            self,
            "assumptions_to_test",
            _text_tuple(self.assumptions_to_test, limit=220),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "audit_job_id": _clean_token(self.audit_job_id),
                "component_ids": list(self.component_ids),
                "audit_scope": self.audit_scope.value,
                "claim_types": list(self.claim_types),
                "assumptions_to_test": list(self.assumptions_to_test),
                "remediation_permission": self.remediation_permission.value,
                "bounded": True,
                "passive": True,
                "open_ended_loop": False,
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class SocialSignalCandidate:
    candidate_id: str
    social_signal_id: str
    component_ids: tuple[str, ...]
    perception_need: str
    allowed_use: str = "directional_perception_or_community_sentiment_only"
    disallowed_satisfaction_kinds: tuple[str, ...] = (
        "official",
        "legal",
        "canonical",
        "factual",
        "medical",
        "financial",
        "source_bound_numeric",
    )
    satisfies_official_or_factual_obligations: bool = False
    future_search_work_plan_field: str = "deferred_social_signal_jobs"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.candidate_id):
            raise ValueError("social signal candidate requires candidate_id")
        if not _clean_token(self.social_signal_id):
            raise ValueError("social signal candidate requires social_signal_id")
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(
            self,
            "disallowed_satisfaction_kinds",
            _text_tuple(self.disallowed_satisfaction_kinds),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "social_signal_id": _clean_token(self.social_signal_id),
                "component_ids": list(self.component_ids),
                "perception_need": _clean_text(self.perception_need, limit=260),
                "allowed_use": _clean_text(self.allowed_use, limit=220),
                "directional_perception_evidence_only": True,
                "deferred": True,
                "satisfies_official_or_factual_obligations": bool(
                    self.satisfies_official_or_factual_obligations
                ),
                "disallowed_satisfaction_kinds": list(
                    self.disallowed_satisfaction_kinds
                ),
                "future_search_work_plan_field": _clean_token(
                    self.future_search_work_plan_field,
                ),
                "metadata": _json_safe(self.metadata),
            }
        )


PerceptionSignalCandidate = SocialSignalCandidate


@dataclass(frozen=True, slots=True)
class QueryShapeAssessment:
    assessment_id: str
    query_shape_kinds: tuple[QueryShapeKind | str, ...]
    requested_mode: SearchMode | str
    assessment_confidence: AssessmentConfidence | str = AssessmentConfidence.TENTATIVE
    assessment_posture: AssessmentPosture | str = AssessmentPosture.PASSIVE_CANDIDATE
    component_candidates: tuple[ComponentCandidate, ...] = ()
    source_obligation_candidates: tuple[SourceObligationCandidate, ...] = ()
    provider_job_candidates: tuple[ProviderJobCandidate, ...] = ()
    quant_work_candidates: tuple[QuantWorkCandidate, ...] = ()
    audit_job_candidates: tuple[AuditJobCandidate, ...] = ()
    social_signal_candidates: tuple[SocialSignalCandidate, ...] = ()
    first_pass_evidence_needed: Mapping[str, bool] = field(default_factory=dict)
    deterministic_signals: tuple[str, ...] = ()
    model_assisted_signals: tuple[str, ...] = ()
    ambiguity_notes: tuple[str, ...] = ()
    normalization_notes: tuple[str, ...] = ()
    stop_condition_candidates: tuple[StopConditionKind | str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    schema_version: str = QUERY_SHAPE_CONTRACT_RESOLUTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.assessment_id):
            raise ValueError("query shape assessment requires assessment_id")
        object.__setattr__(
            self,
            "query_shape_kinds",
            _enum_tuple(QueryShapeKind, self.query_shape_kinds, QueryShapeKind.SIMPLE_LOOKUP),
        )
        object.__setattr__(
            self,
            "requested_mode",
            _coerce_enum(SearchMode, self.requested_mode, SearchMode.UNRESOLVED),
        )
        object.__setattr__(
            self,
            "assessment_confidence",
            _coerce_enum(
                AssessmentConfidence,
                self.assessment_confidence,
                AssessmentConfidence.TENTATIVE,
            ),
        )
        object.__setattr__(
            self,
            "assessment_posture",
            _coerce_enum(
                AssessmentPosture,
                self.assessment_posture,
                AssessmentPosture.PASSIVE_CANDIDATE,
            ),
        )
        object.__setattr__(self, "component_candidates", tuple(self.component_candidates or ()))
        object.__setattr__(
            self,
            "source_obligation_candidates",
            tuple(self.source_obligation_candidates or ()),
        )
        object.__setattr__(
            self,
            "provider_job_candidates",
            tuple(self.provider_job_candidates or ()),
        )
        object.__setattr__(self, "quant_work_candidates", tuple(self.quant_work_candidates or ()))
        object.__setattr__(self, "audit_job_candidates", tuple(self.audit_job_candidates or ()))
        object.__setattr__(
            self,
            "social_signal_candidates",
            tuple(self.social_signal_candidates or ()),
        )
        object.__setattr__(
            self,
            "deterministic_signals",
            _text_tuple(self.deterministic_signals, limit=260),
        )
        object.__setattr__(
            self,
            "model_assisted_signals",
            _text_tuple(self.model_assisted_signals, limit=260),
        )
        object.__setattr__(self, "ambiguity_notes", _text_tuple(self.ambiguity_notes, limit=260))
        object.__setattr__(
            self,
            "normalization_notes",
            _text_tuple(self.normalization_notes, limit=260),
        )
        object.__setattr__(
            self,
            "stop_condition_candidates",
            _enum_tuple(
                StopConditionKind,
                self.stop_condition_candidates,
                StopConditionKind.COMPONENT_SUFFICIENT,
            ),
        )

    def validate(self) -> QueryShapeContractValidationResult:
        errors: list[str] = []
        component_ids = [item.component_id for item in self.component_candidates]
        component_id_set = set(component_ids)
        _add_duplicate_errors(errors, "component_id", component_ids)
        _add_duplicate_errors(
            errors,
            "component candidate_id",
            [item.candidate_id for item in self.component_candidates],
        )
        _add_duplicate_errors(
            errors,
            "source obligation candidate_id",
            [item.candidate_id for item in self.source_obligation_candidates],
        )
        _add_duplicate_errors(
            errors,
            "provider job candidate_id",
            [item.candidate_id for item in self.provider_job_candidates],
        )
        _add_duplicate_errors(
            errors,
            "quant work candidate_id",
            [item.candidate_id for item in self.quant_work_candidates],
        )
        _add_duplicate_errors(
            errors,
            "audit job candidate_id",
            [item.candidate_id for item in self.audit_job_candidates],
        )
        _add_duplicate_errors(
            errors,
            "social signal candidate_id",
            [item.candidate_id for item in self.social_signal_candidates],
        )

        for obligation in self.source_obligation_candidates:
            errors.extend(
                _missing_component_errors(
                    "source obligation candidate",
                    obligation.candidate_id,
                    obligation.component_ids,
                    component_id_set,
                )
            )
            if obligation.kind in _STRICT_SOURCE_OBLIGATION_KINDS:
                if obligation.strictness is not SourceObligationStrictness.REQUIRED:
                    errors.append(
                        f"source obligation candidate {obligation.candidate_id} cannot downgrade "
                        f"{obligation.kind.value} below required strictness"
                    )
                if obligation.lower_tier_final_satisfaction_allowed:
                    errors.append(
                        f"source obligation candidate {obligation.candidate_id} cannot allow lower-tier "
                        f"final satisfaction for {obligation.kind.value}"
                    )

        for candidate in self.provider_job_candidates:
            errors.extend(
                _missing_component_errors(
                    "provider job candidate",
                    candidate.candidate_id,
                    candidate.component_ids,
                    component_id_set,
                )
            )
        for candidate in self.quant_work_candidates:
            errors.extend(
                _missing_component_errors(
                    "quant work candidate",
                    candidate.candidate_id,
                    candidate.component_ids,
                    component_id_set,
                )
            )
        for candidate in self.audit_job_candidates:
            errors.extend(
                _missing_component_errors(
                    "audit job candidate",
                    candidate.candidate_id,
                    candidate.component_ids,
                    component_id_set,
                )
            )
        for candidate in self.social_signal_candidates:
            errors.extend(
                _missing_component_errors(
                    "social signal candidate",
                    candidate.candidate_id,
                    candidate.component_ids,
                    component_id_set,
                )
            )
            if candidate.satisfies_official_or_factual_obligations:
                errors.append(
                    f"social signal candidate {candidate.candidate_id} cannot satisfy "
                    "official/legal/canonical/factual/medical/financial/source-bound obligations"
                )

        if not self.passive:
            errors.append("query shape assessment must remain passive")
        return QueryShapeContractValidationResult(errors=tuple(errors))

    def require_valid(self) -> "QueryShapeAssessment":
        self.validate().raise_for_errors()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": QUERY_SHAPE_ASSESSMENT_TRACE_KEY,
            "assessment_id": _clean_token(self.assessment_id),
            "passive": bool(self.passive),
            "runtime_consumed": False,
            "constructs_search_work_plan": False,
            "prompt_behavior_changed": False,
            "provider_search_behavior_changed": False,
            "query_shape_kinds": [item.value for item in self.query_shape_kinds],
            "requested_mode": self.requested_mode.value,
            "assessment_confidence": self.assessment_confidence.value,
            "assessment_posture": self.assessment_posture.value,
            "component_candidates": [item.to_dict() for item in self.component_candidates],
            "source_obligation_candidates": [
                item.to_dict() for item in self.source_obligation_candidates
            ],
            "provider_job_candidates": [
                item.to_dict() for item in self.provider_job_candidates
            ],
            "quant_work_candidates": [item.to_dict() for item in self.quant_work_candidates],
            "audit_job_candidates": [item.to_dict() for item in self.audit_job_candidates],
            "social_signal_candidates": [
                item.to_dict() for item in self.social_signal_candidates
            ],
            "first_pass_evidence_needed": _json_safe(self.first_pass_evidence_needed),
            "deterministic_signals": list(self.deterministic_signals),
            "model_assisted_signals": list(self.model_assisted_signals),
            "ambiguity_notes": list(self.ambiguity_notes),
            "normalization_notes": list(self.normalization_notes),
            "stop_condition_candidates": [
                item.value for item in self.stop_condition_candidates
            ],
            "metadata": _json_safe(self.metadata),
            "validation": self.validate().to_dict(),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {QUERY_SHAPE_ASSESSMENT_TRACE_KEY: self.to_dict()}


@dataclass(frozen=True, slots=True)
class ContractResolutionRecord:
    resolution_id: str
    requested_mode: SearchMode | str
    effective_contract: EffectiveContractKind | str
    mode_mismatch_posture: ModeMismatchPosture | str = ModeMismatchPosture.NONE
    allowed_follow_up_depth: FollowUpDepthPosture | str = FollowUpDepthPosture.NONE_OR_MINIMAL
    output_posture: OutputPosture | str = OutputPosture.DIRECT
    stop_escalate_refuse_posture: StopEscalateRefusePosture | str = (
        StopEscalateRefusePosture.STOP_WHEN_SUFFICIENT
    )
    authority_chain_owner: str = "RunAuthority chain"
    specific_search_judgment_owner: str = "SearchJudgment"
    specific_sufficiency_judgment_owner: str = "SufficiencyJudgment"
    runtime_authorizer: str = "RunKernel"
    follow_up_authorizers: tuple[str, ...] = (
        "RunAuthority",
        "SearchJudgment",
        "SufficiencyJudgment",
    )
    rationale: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    schema_version: str = QUERY_SHAPE_CONTRACT_RESOLUTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.resolution_id):
            raise ValueError("contract resolution record requires resolution_id")
        object.__setattr__(
            self,
            "requested_mode",
            _coerce_enum(SearchMode, self.requested_mode, SearchMode.UNRESOLVED),
        )
        object.__setattr__(
            self,
            "effective_contract",
            _coerce_enum(
                EffectiveContractKind,
                self.effective_contract,
                EffectiveContractKind.AUTO_UNRESOLVED,
            ),
        )
        object.__setattr__(
            self,
            "mode_mismatch_posture",
            _coerce_enum(
                ModeMismatchPosture,
                self.mode_mismatch_posture,
                ModeMismatchPosture.NONE,
            ),
        )
        object.__setattr__(
            self,
            "allowed_follow_up_depth",
            _coerce_enum(
                FollowUpDepthPosture,
                self.allowed_follow_up_depth,
                FollowUpDepthPosture.NOT_AUTHORIZED,
            ),
        )
        object.__setattr__(
            self,
            "output_posture",
            _coerce_enum(OutputPosture, self.output_posture, OutputPosture.DIRECT),
        )
        object.__setattr__(
            self,
            "stop_escalate_refuse_posture",
            _coerce_enum(
                StopEscalateRefusePosture,
                self.stop_escalate_refuse_posture,
                StopEscalateRefusePosture.STOP_WHEN_SUFFICIENT,
            ),
        )
        object.__setattr__(self, "follow_up_authorizers", _text_tuple(self.follow_up_authorizers))

    def validate(self) -> QueryShapeContractValidationResult:
        errors: list[str] = []
        if self.requested_mode is SearchMode.FAST:
            elevated_contract = self.effective_contract in {
                EffectiveContractKind.EXPLANATORY,
                EffectiveContractKind.RESEARCH_RECONCILIATION,
            }
            elevated_follow_up = self.allowed_follow_up_depth in {
                FollowUpDepthPosture.CONDITIONAL_GAP_DRIVEN,
                FollowUpDepthPosture.LARGER_BOUNDED_LOOP,
            }
            if (elevated_contract or elevated_follow_up) and self.mode_mismatch_posture not in {
                ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT,
                ModeMismatchPosture.QUALIFY_OR_REFUSE,
                ModeMismatchPosture.ESCALATE_SUGGESTED,
            }:
                errors.append(
                    "Fast cannot silently spend Balanced/Deep budget; select "
                    "selected_mode_insufficient, qualify_or_refuse, or escalate_suggested"
                )

        authority_fields = {
            "authority_chain_owner": self.authority_chain_owner,
            "specific_search_judgment_owner": self.specific_search_judgment_owner,
            "specific_sufficiency_judgment_owner": self.specific_sufficiency_judgment_owner,
            "runtime_authorizer": self.runtime_authorizer,
        }
        for field_name, value in authority_fields.items():
            clean_value = _clean_token(value)
            if clean_value in _FORBIDDEN_EXECUTOR_AUTHORIZERS:
                errors.append(f"{field_name} cannot be bounded executor {clean_value}")
            elif clean_value not in _VALID_AUTHORITY_POSTURES:
                errors.append(
                    f"{field_name} must be RunAuthority chain / RunKernel / "
                    f"SearchJudgment / SufficiencyJudgment posture: {clean_value}"
                )

        invalid_authorizers = [
            item
            for item in self.follow_up_authorizers
            if item not in _VALID_FOLLOW_UP_AUTHORIZERS
        ]
        forbidden_authorizers = [
            item
            for item in self.follow_up_authorizers
            if item in _FORBIDDEN_EXECUTOR_AUTHORIZERS
        ]
        if invalid_authorizers:
            errors.append(
                "follow-up authorizers must be RunAuthority/SearchJudgment/"
                "SufficiencyJudgment posture: "
                + ", ".join(invalid_authorizers)
            )
        if forbidden_authorizers:
            errors.append(
                "bounded executors cannot authorize follow-up: "
                + ", ".join(forbidden_authorizers)
            )
        if not self.passive:
            errors.append("contract resolution record must remain passive")
        return QueryShapeContractValidationResult(errors=tuple(errors))

    def require_valid(self) -> "ContractResolutionRecord":
        self.validate().raise_for_errors()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": CONTRACT_RESOLUTION_TRACE_KEY,
            "resolution_id": _clean_token(self.resolution_id),
            "requested_mode": self.requested_mode.value,
            "effective_contract": self.effective_contract.value,
            "mode_mismatch_posture": self.mode_mismatch_posture.value,
            "allowed_follow_up_depth": self.allowed_follow_up_depth.value,
            "output_posture": self.output_posture.value,
            "stop_escalate_refuse_posture": self.stop_escalate_refuse_posture.value,
            "authority_chain_owner": _clean_token(self.authority_chain_owner),
            "specific_search_judgment_owner": _clean_token(
                self.specific_search_judgment_owner
            ),
            "specific_sufficiency_judgment_owner": _clean_token(
                self.specific_sufficiency_judgment_owner
            ),
            "runtime_authorizer": _clean_token(self.runtime_authorizer),
            "follow_up_authorizers": list(self.follow_up_authorizers),
            "authority_model": {
                "one_run_authority_chain": True,
                "search_judgment_subordinate_surface": True,
                "sufficiency_judgment_subordinate_surface": True,
                "bounded_executors_authorize_follow_up": False,
            },
            "rationale": _clean_text(self.rationale, limit=400),
            "metadata": _json_safe(self.metadata),
            "passive": bool(self.passive),
            "runtime_consumed": False,
            "validation": self.validate().to_dict(),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {CONTRACT_RESOLUTION_TRACE_KEY: self.to_dict()}


@dataclass(frozen=True, slots=True)
class SearchWorkPlanConstructionDesignRecord:
    design_id: str
    construction_posture: ConstructionPosture | str = ConstructionPosture.PASSIVE_DESIGN_ONLY
    future_runtime_consumer: str = "RunKernel / RunAuthority construction seam"
    future_output: str = "SearchWorkPlan"
    inputs_needed: tuple[str, ...] = (
        "QueryShapeAssessment",
        "ContractResolutionRecord",
        "RunAuthorityContract source requirements",
        "safe route facts",
    )
    fields_to_populate: tuple[str, ...] = (
        "requested_mode",
        "effective_contract",
        "query_shape",
        "components",
        "source_obligations",
        "provider_jobs",
        "quant_work_units",
        "audit_jobs",
        "follow_up_authority",
        "stop_conditions",
    )
    old_authority_paths_to_subordinate_later: tuple[str, ...] = (
        "legacy Scout/Expander/Evaluator query-shaping signals",
        "legacy Economist quantitative planning posture",
        "legacy Scrutineer remediation signal posture",
    )
    closed_surfaces: tuple[str, ...] = (
        "runtime query classification",
        "runtime ContractResolver",
        "runtime SearchWorkPlan construction",
        "QueryPlan behavior",
        "provider/search behavior",
        "prompt behavior",
        "core/pipeline_orchestrator.py",
    )
    activation_prerequisites: tuple[str, ...] = (
        "accepted SearchWorkPlan runtime construction design",
        "RunKernel/RunAuthority consumer named",
        "old authority paths subordinated or retired",
        "offline tests for behavior-preserving construction",
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    schema_version: str = QUERY_SHAPE_CONTRACT_RESOLUTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.design_id):
            raise ValueError("construction design record requires design_id")
        object.__setattr__(
            self,
            "construction_posture",
            _coerce_enum(
                ConstructionPosture,
                self.construction_posture,
                ConstructionPosture.PASSIVE_DESIGN_ONLY,
            ),
        )
        object.__setattr__(self, "inputs_needed", _text_tuple(self.inputs_needed, limit=220))
        object.__setattr__(
            self,
            "fields_to_populate",
            _text_tuple(self.fields_to_populate, limit=160),
        )
        object.__setattr__(
            self,
            "old_authority_paths_to_subordinate_later",
            _text_tuple(self.old_authority_paths_to_subordinate_later, limit=260),
        )
        object.__setattr__(self, "closed_surfaces", _text_tuple(self.closed_surfaces, limit=220))
        object.__setattr__(
            self,
            "activation_prerequisites",
            _text_tuple(self.activation_prerequisites, limit=260),
        )

    def validate(self) -> QueryShapeContractValidationResult:
        errors: list[str] = []
        if self.construction_posture is not ConstructionPosture.PASSIVE_DESIGN_ONLY:
            errors.append("construction posture must remain passive_design_only")
        if self.future_output != "SearchWorkPlan":
            errors.append("future output must be SearchWorkPlan")
        if not self.passive:
            errors.append("construction design record must remain passive")
        return QueryShapeContractValidationResult(errors=tuple(errors))

    def require_valid(self) -> "SearchWorkPlanConstructionDesignRecord":
        self.validate().raise_for_errors()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_key": SEARCH_WORK_PLAN_CONSTRUCTION_DESIGN_TRACE_KEY,
            "design_id": _clean_token(self.design_id),
            "construction_posture": self.construction_posture.value,
            "future_runtime_consumer": _clean_text(self.future_runtime_consumer, limit=220),
            "future_output": _clean_token(self.future_output),
            "inputs_needed": list(self.inputs_needed),
            "fields_to_populate": list(self.fields_to_populate),
            "old_authority_paths_to_subordinate_later": list(
                self.old_authority_paths_to_subordinate_later
            ),
            "closed_surfaces": list(self.closed_surfaces),
            "activation_prerequisites": list(self.activation_prerequisites),
            "describes_fill_path_only": True,
            "constructs_search_work_plan": False,
            "runtime_consumed": False,
            "passive": bool(self.passive),
            "metadata": _json_safe(self.metadata),
            "validation": self.validate().to_dict(),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SEARCH_WORK_PLAN_CONSTRUCTION_DESIGN_TRACE_KEY: self.to_dict()}


def _add_duplicate_errors(errors: list[str], label: str, values: Sequence[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        errors.append(f"duplicate {label} values are not allowed: {', '.join(duplicates)}")


def _missing_component_errors(
    owner_kind: str,
    owner_id: str,
    referenced_ids: Sequence[str],
    component_id_set: set[str],
) -> list[str]:
    return [
        f"{owner_kind} {owner_id} references missing component {component_id}"
        for component_id in referenced_ids
        if component_id not in component_id_set
    ]


__all__ = [
    "CONTRACT_RESOLUTION_TRACE_KEY",
    "QUERY_SHAPE_ASSESSMENT_TRACE_KEY",
    "QUERY_SHAPE_CONTRACT_RESOLUTION_SCHEMA_VERSION",
    "SEARCH_WORK_PLAN_CONSTRUCTION_DESIGN_TRACE_KEY",
    "AssessmentConfidence",
    "AssessmentPosture",
    "AuditJobCandidate",
    "AuditScope",
    "ComponentCandidate",
    "ConstructionPosture",
    "ContractResolutionRecord",
    "EffectiveContractKind",
    "FollowUpDepthPosture",
    "ModeMismatchPosture",
    "OutputPosture",
    "PerceptionSignalCandidate",
    "ProviderJobCandidate",
    "ProviderJobKind",
    "QuantWorkCandidate",
    "QueryShapeAssessment",
    "QueryShapeContractValidationResult",
    "QueryShapeKind",
    "RemediationPermission",
    "SearchMode",
    "SearchWorkPlanConstructionDesignRecord",
    "SocialSignalCandidate",
    "SourceObligationCandidate",
    "SourceObligationKind",
    "SourceObligationStrictness",
    "StopConditionKind",
    "StopEscalateRefusePosture",
]
