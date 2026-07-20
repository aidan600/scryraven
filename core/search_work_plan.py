"""Passive SearchWorkPlan contract for AG-96C2.

The model in this module is representational only. It defines JSON-safe,
component-aware search-work planning objects without constructing prompts,
calling providers, executing retrieval, mutating RunKernel state, or wiring any
runtime consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

SEARCH_WORK_PLAN_SCHEMA_VERSION = "search_work_plan_ag96c2_v1"
SEARCH_WORK_PLAN_TRACE_KEY = "search_work_plan"

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


class ModeDepthAllowance(str, Enum):
    SHALLOW = "shallow"
    MODERATE = "moderate"
    DEEP = "deep"
    UNRESOLVED = "unresolved"


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


class SourceObligationKind(str, Enum):
    OFFICIAL_CURRENT = "official_current"
    LEGAL_CURRENT_PRIMARY = "legal_current_primary"
    CANONICAL_DOCUMENTATION = "canonical_documentation"
    SOURCE_BOUND_NUMERIC = "source_bound_numeric"
    PEER_REVIEWED = "peer_reviewed"
    REPUTABLE_SECONDARY = "reputable_secondary"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DATE_BOUND_CURRENTNESS = "date_bound_currentness"
    USER_DOCUMENT = "user_document"
    NO_SPECIAL_OBLIGATION = "no_special_obligation"


class SourceObligationStrictness(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    CONTEXTUAL = "contextual"


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


class BudgetValuePosture(str, Enum):
    NOT_NUMERIC = "not_numeric"
    MODE_DERIVED = "mode_derived"
    COMPONENT_MINIMUM = "component_minimum"
    COMPONENT_CAP = "component_cap"
    GLOBAL_CAP = "global_cap"


class RebalancingPolicy(str, Enum):
    NONE = "none"
    COMPONENT_FAIRNESS_FIRST = "component_fairness_first"
    REALLOCATE_UNUSED_TO_CENTRAL_GAPS = "reallocate_unused_to_central_gaps"
    MODE_BOUND_GAP_DRIVEN = "mode_bound_gap_driven"


class BudgetExhaustedPosture(str, Enum):
    STOP = "stop"
    QUALIFY = "qualify"
    ESCALATE_SUGGESTION = "escalate_suggestion"
    REFUSE_WHEN_UNSAFE = "refuse_when_unsafe"


class FollowUpPermission(str, Enum):
    NOT_ALLOWED = "not_allowed"
    CONDITIONAL = "conditional"
    ALLOWED = "allowed"


class StopConditionKind(str, Enum):
    COMPONENT_SUFFICIENT = "component_sufficient"
    SOURCE_OBLIGATION_UNSATISFIED = "source_obligation_unsatisfied"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MODE_MISMATCH = "mode_mismatch"
    REQUIRED_INFERENCE_EXCEEDS_SELECTED_MODE = "required_inference_exceeds_selected_mode"
    MISSING_SOURCE_BOUND_NUMERIC_VALUES = "missing_source_bound_numeric_values"
    UNRESOLVED_CONFLICT_CURRENTNESS = "unresolved_conflict_currentness"
    LIVE_VALIDATION_NOT_AUTHORIZED = "live_validation_not_authorized"


class StopOutcome(str, Enum):
    STOP = "stop"
    FAIL_CLOSED = "fail_closed"
    QUALIFY = "qualify"
    ESCALATE_SUGGESTION = "escalate_suggestion"
    REFUSE = "refuse"


class SynthesisScope(str, Enum):
    COMPONENT_SYNTHESIS = "component_synthesis"
    CROSS_COMPONENT_COMPARISON = "cross_component_comparison"
    EVIDENCE_BASIS_SUMMARY = "evidence_basis_summary"
    GAP_VISIBILITY = "gap_visibility"


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


class FinalSufficiencyPosture(str, Enum):
    ALL_REQUIRED_COMPONENTS = "all_required_components"
    QUALIFY_UNRESOLVED_OPTIONAL_COMPONENTS = "qualify_unresolved_optional_components"
    REFUSE_UNSATISFIED_REQUIRED_OBLIGATIONS = "refuse_unsatisfied_required_obligations"
    DEFER_TO_AUTHORITY_CHAIN = "defer_to_authority_chain"


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


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


@dataclass(frozen=True, slots=True)
class RequestedModeDescriptor:
    mode: SearchMode | str
    source: str = "user_or_ui"
    mode_mismatch_posture: ModeMismatchPosture | str = ModeMismatchPosture.NONE
    rationale: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _coerce_enum(SearchMode, self.mode, SearchMode.UNRESOLVED))
        object.__setattr__(
            self,
            "mode_mismatch_posture",
            _coerce_enum(
                ModeMismatchPosture,
                self.mode_mismatch_posture,
                ModeMismatchPosture.NONE,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "mode": self.mode.value,
                "source": _clean_token(self.source),
                "mode_mismatch_posture": self.mode_mismatch_posture.value,
                "rationale": _clean_text(self.rationale, limit=260),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RequestedModeDescriptor":
        return cls(
            mode=payload.get("mode") or SearchMode.UNRESOLVED.value,
            source=str(payload.get("source") or "user_or_ui"),
            mode_mismatch_posture=payload.get("mode_mismatch_posture")
            or ModeMismatchPosture.NONE.value,
            rationale=_clean_text(payload.get("rationale"), limit=260),
        )


@dataclass(frozen=True, slots=True)
class EffectiveContractDescriptor:
    contract_kind: EffectiveContractKind | str
    governing_authority: str = "RunKernel.RunAuthority"
    depth_allowance: ModeDepthAllowance | str = ModeDepthAllowance.SHALLOW
    follow_up_posture: FollowUpPermission | str = FollowUpPermission.NOT_ALLOWED
    budget_posture: str = "mode_bound"
    output_depth_target: str = "direct"
    mismatch_posture: ModeMismatchPosture | str = ModeMismatchPosture.NONE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "contract_kind",
            _coerce_enum(
                EffectiveContractKind,
                self.contract_kind,
                EffectiveContractKind.AUTO_UNRESOLVED,
            ),
        )
        object.__setattr__(
            self,
            "depth_allowance",
            _coerce_enum(ModeDepthAllowance, self.depth_allowance, ModeDepthAllowance.UNRESOLVED),
        )
        object.__setattr__(
            self,
            "follow_up_posture",
            _coerce_enum(FollowUpPermission, self.follow_up_posture, FollowUpPermission.NOT_ALLOWED),
        )
        object.__setattr__(
            self,
            "mismatch_posture",
            _coerce_enum(ModeMismatchPosture, self.mismatch_posture, ModeMismatchPosture.NONE),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "contract_kind": self.contract_kind.value,
                "governing_authority": _clean_token(self.governing_authority),
                "depth_allowance": self.depth_allowance.value,
                "follow_up_posture": self.follow_up_posture.value,
                "budget_posture": _clean_token(self.budget_posture),
                "output_depth_target": _clean_token(self.output_depth_target),
                "mismatch_posture": self.mismatch_posture.value,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EffectiveContractDescriptor":
        return cls(
            contract_kind=payload.get("contract_kind") or EffectiveContractKind.AUTO_UNRESOLVED.value,
            governing_authority=str(payload.get("governing_authority") or "RunKernel.RunAuthority"),
            depth_allowance=payload.get("depth_allowance") or ModeDepthAllowance.UNRESOLVED.value,
            follow_up_posture=payload.get("follow_up_posture") or FollowUpPermission.NOT_ALLOWED.value,
            budget_posture=str(payload.get("budget_posture") or "mode_bound"),
            output_depth_target=str(payload.get("output_depth_target") or "direct"),
            mismatch_posture=payload.get("mismatch_posture") or ModeMismatchPosture.NONE.value,
        )


@dataclass(frozen=True, slots=True)
class QueryShapeDescriptor:
    kinds: tuple[QueryShapeKind | str, ...]
    component_count_hint: int | None = None
    normalization_notes: tuple[str, ...] = ()
    ambiguity_notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "kinds",
            _enum_tuple(QueryShapeKind, self.kinds, QueryShapeKind.SIMPLE_LOOKUP),
        )
        object.__setattr__(self, "normalization_notes", _text_tuple(self.normalization_notes, limit=260))
        object.__setattr__(self, "ambiguity_notes", _text_tuple(self.ambiguity_notes, limit=260))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "kinds": [item.value for item in self.kinds],
                "component_count_hint": self.component_count_hint,
                "normalization_notes": list(self.normalization_notes),
                "ambiguity_notes": list(self.ambiguity_notes),
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QueryShapeDescriptor":
        return cls(
            kinds=tuple(payload.get("kinds") or ()),
            component_count_hint=payload.get("component_count_hint"),
            normalization_notes=tuple(payload.get("normalization_notes") or ()),
            ambiguity_notes=tuple(payload.get("ambiguity_notes") or ()),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SourceObligation:
    obligation_id: str
    kind: SourceObligationKind | str
    strictness: SourceObligationStrictness | str = SourceObligationStrictness.REQUIRED
    search_constraint: str | None = None
    currentness_requirement: str | None = None
    satisfaction_rule: str | None = None
    lower_tier_use: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.obligation_id):
            raise ValueError("source obligation requires obligation_id")
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

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "obligation_id": _clean_token(self.obligation_id),
                "kind": self.kind.value,
                "strictness": self.strictness.value,
                "search_constraint": _clean_text(self.search_constraint, limit=240),
                "currentness_requirement": _clean_text(self.currentness_requirement, limit=160),
                "satisfaction_rule": _clean_text(self.satisfaction_rule, limit=300),
                "lower_tier_use": _clean_text(self.lower_tier_use, limit=220),
                "official_current_is_source_obligation": (
                    self.kind is SourceObligationKind.OFFICIAL_CURRENT
                ),
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceObligation":
        return cls(
            obligation_id=str(payload.get("obligation_id") or ""),
            kind=payload.get("kind") or SourceObligationKind.NO_SPECIAL_OBLIGATION.value,
            strictness=payload.get("strictness") or SourceObligationStrictness.CONTEXTUAL.value,
            search_constraint=_clean_text(payload.get("search_constraint"), limit=240),
            currentness_requirement=_clean_text(payload.get("currentness_requirement"), limit=160),
            satisfaction_rule=_clean_text(payload.get("satisfaction_rule"), limit=300),
            lower_tier_use=_clean_text(payload.get("lower_tier_use"), limit=220),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class BudgetValue:
    value: int | float | str | None = None
    posture: BudgetValuePosture | str = BudgetValuePosture.NOT_NUMERIC
    unit: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "posture",
            _coerce_enum(BudgetValuePosture, self.posture, BudgetValuePosture.NOT_NUMERIC),
        )

    @property
    def numeric_value(self) -> float | None:
        return _numeric(self.value)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "value": _json_safe(self.value),
                "posture": self.posture.value,
                "unit": _clean_token(self.unit, limit=80),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "BudgetValue":
        if not isinstance(payload, Mapping):
            return cls()
        return cls(
            value=payload.get("value"),
            posture=payload.get("posture") or BudgetValuePosture.NOT_NUMERIC.value,
            unit=_clean_token(payload.get("unit"), limit=80),
        )


@dataclass(frozen=True, slots=True)
class ComponentBudget:
    minimum_viable: BudgetValue = field(default_factory=BudgetValue)
    cap: BudgetValue = field(default_factory=BudgetValue)
    budget_exhausted_posture: BudgetExhaustedPosture | str = BudgetExhaustedPosture.QUALIFY

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "budget_exhausted_posture",
            _coerce_enum(
                BudgetExhaustedPosture,
                self.budget_exhausted_posture,
                BudgetExhaustedPosture.QUALIFY,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum_viable": self.minimum_viable.to_dict(),
            "cap": self.cap.to_dict(),
            "budget_exhausted_posture": self.budget_exhausted_posture.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "ComponentBudget":
        if not isinstance(payload, Mapping):
            return cls()
        return cls(
            minimum_viable=BudgetValue.from_dict(payload.get("minimum_viable")),
            cap=BudgetValue.from_dict(payload.get("cap")),
            budget_exhausted_posture=payload.get("budget_exhausted_posture")
            or BudgetExhaustedPosture.QUALIFY.value,
        )


@dataclass(frozen=True, slots=True)
class StopCondition:
    condition: StopConditionKind | str
    outcome: StopOutcome | str
    description: str | None = None
    component_id: str | None = None
    authority: str = "RunAuthority/SearchJudgment/SufficiencyJudgment"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "condition",
            _coerce_enum(StopConditionKind, self.condition, StopConditionKind.BUDGET_EXHAUSTED),
        )
        object.__setattr__(
            self,
            "outcome",
            _coerce_enum(StopOutcome, self.outcome, StopOutcome.QUALIFY),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "condition": self.condition.value,
                "outcome": self.outcome.value,
                "description": _clean_text(self.description, limit=300),
                "component_id": _clean_token(self.component_id),
                "authority": _clean_text(self.authority, limit=160),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StopCondition":
        return cls(
            condition=payload.get("condition") or StopConditionKind.BUDGET_EXHAUSTED.value,
            outcome=payload.get("outcome") or StopOutcome.QUALIFY.value,
            description=_clean_text(payload.get("description"), limit=300),
            component_id=_clean_token(payload.get("component_id")),
            authority=str(payload.get("authority") or "RunAuthority/SearchJudgment/SufficiencyJudgment"),
        )


@dataclass(frozen=True, slots=True)
class SearchWorkComponent:
    component_id: str
    user_facing_subquestion: str
    entities: tuple[str, ...] = ()
    anchors: tuple[str, ...] = ()
    source_obligations: tuple[SourceObligation, ...] = ()
    required_provider_jobs: tuple[ProviderJobKind | str, ...] = ()
    per_component_budget: ComponentBudget = field(default_factory=ComponentBudget)
    mode_depth_allowance: ModeDepthAllowance | str = ModeDepthAllowance.SHALLOW
    stop_conditions: tuple[StopCondition, ...] = ()
    depends_on: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.component_id):
            raise ValueError("search work component requires component_id")
        object.__setattr__(self, "entities", _text_tuple(self.entities))
        object.__setattr__(self, "anchors", _text_tuple(self.anchors))
        object.__setattr__(self, "source_obligations", tuple(self.source_obligations or ()))
        object.__setattr__(
            self,
            "required_provider_jobs",
            _enum_tuple(ProviderJobKind, self.required_provider_jobs, ProviderJobKind.DIRECT_CANDIDATE_SEARCH),
        )
        object.__setattr__(
            self,
            "mode_depth_allowance",
            _coerce_enum(
                ModeDepthAllowance,
                self.mode_depth_allowance,
                ModeDepthAllowance.UNRESOLVED,
            ),
        )
        object.__setattr__(self, "stop_conditions", tuple(self.stop_conditions or ()))
        object.__setattr__(self, "depends_on", _text_tuple(self.depends_on))

    def source_obligation_ids(self) -> tuple[str, ...]:
        return tuple(item.obligation_id for item in self.source_obligations)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "component_id": _clean_token(self.component_id),
                "user_facing_subquestion": _clean_text(self.user_facing_subquestion, limit=500),
                "entities": list(self.entities),
                "anchors": list(self.anchors),
                "source_obligations": [item.to_dict() for item in self.source_obligations],
                "required_provider_jobs": [item.value for item in self.required_provider_jobs],
                "per_component_budget": self.per_component_budget.to_dict(),
                "mode_depth_allowance": self.mode_depth_allowance.value,
                "stop_conditions": [item.to_dict() for item in self.stop_conditions],
                "depends_on": list(self.depends_on),
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SearchWorkComponent":
        return cls(
            component_id=str(payload.get("component_id") or ""),
            user_facing_subquestion=str(payload.get("user_facing_subquestion") or ""),
            entities=tuple(payload.get("entities") or ()),
            anchors=tuple(payload.get("anchors") or ()),
            source_obligations=tuple(
                SourceObligation.from_dict(item)
                for item in payload.get("source_obligations") or ()
                if isinstance(item, Mapping)
            ),
            required_provider_jobs=tuple(payload.get("required_provider_jobs") or ()),
            per_component_budget=ComponentBudget.from_dict(payload.get("per_component_budget")),
            mode_depth_allowance=payload.get("mode_depth_allowance") or ModeDepthAllowance.UNRESOLVED.value,
            stop_conditions=tuple(
                StopCondition.from_dict(item)
                for item in payload.get("stop_conditions") or ()
                if isinstance(item, Mapping)
            ),
            depends_on=tuple(payload.get("depends_on") or ()),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class ProviderJob:
    provider_job_id: str
    job_kind: ProviderJobKind | str
    component_ids: tuple[str, ...]
    source_obligation_ids: tuple[str, ...] = ()
    job_posture: str = "planned_passive"
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.provider_job_id):
            raise ValueError("provider job requires provider_job_id")
        object.__setattr__(
            self,
            "job_kind",
            _coerce_enum(ProviderJobKind, self.job_kind, ProviderJobKind.DIRECT_CANDIDATE_SEARCH),
        )
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(self, "source_obligation_ids", _text_tuple(self.source_obligation_ids))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "provider_job_id": _clean_token(self.provider_job_id),
                "job_kind": self.job_kind.value,
                "component_ids": list(self.component_ids),
                "source_obligation_ids": list(self.source_obligation_ids),
                "job_posture": _clean_token(self.job_posture),
                "provider_name_neutral": True,
                "provider_metadata": _json_safe(self.provider_metadata),
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProviderJob":
        return cls(
            provider_job_id=str(payload.get("provider_job_id") or ""),
            job_kind=payload.get("job_kind") or ProviderJobKind.DIRECT_CANDIDATE_SEARCH.value,
            component_ids=tuple(payload.get("component_ids") or ()),
            source_obligation_ids=tuple(payload.get("source_obligation_ids") or ()),
            job_posture=str(payload.get("job_posture") or "planned_passive"),
            provider_metadata=dict(payload.get("provider_metadata") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class QuantWorkUnit:
    quant_unit_id: str
    component_ids: tuple[str, ...]
    target_metric: str
    required_variables: tuple[str, ...] = ()
    source_bound_values_needed: tuple[str, ...] = ()
    unsupported_values: tuple[str, ...] = ()
    allowed_calculations: tuple[str, ...] = ()
    assumptions_needed: tuple[str, ...] = ()
    high_stakes_quant: bool = False
    direct_use_eligible: bool = False
    requires_synthesis: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.quant_unit_id):
            raise ValueError("quant work unit requires quant_unit_id")
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(self, "required_variables", _text_tuple(self.required_variables))
        object.__setattr__(
            self,
            "source_bound_values_needed",
            _text_tuple(self.source_bound_values_needed),
        )
        object.__setattr__(self, "unsupported_values", _text_tuple(self.unsupported_values))
        object.__setattr__(self, "allowed_calculations", _text_tuple(self.allowed_calculations))
        object.__setattr__(self, "assumptions_needed", _text_tuple(self.assumptions_needed))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "quant_unit_id": _clean_token(self.quant_unit_id),
                "component_ids": list(self.component_ids),
                "target_metric": _clean_text(self.target_metric, limit=240),
                "required_variables": list(self.required_variables),
                "source_bound_values_needed": list(self.source_bound_values_needed),
                "unsupported_values": list(self.unsupported_values),
                "allowed_calculations": list(self.allowed_calculations),
                "assumptions_needed": list(self.assumptions_needed),
                "high_stakes_quant": self.high_stakes_quant,
                "direct_use_eligible": self.direct_use_eligible,
                "requires_synthesis": self.requires_synthesis,
                "source_bound_and_passive": True,
                "executes_calculations": False,
                "executes_code": False,
                "calls_models_or_providers": False,
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QuantWorkUnit":
        return cls(
            quant_unit_id=str(payload.get("quant_unit_id") or ""),
            component_ids=tuple(payload.get("component_ids") or ()),
            target_metric=str(payload.get("target_metric") or ""),
            required_variables=tuple(payload.get("required_variables") or ()),
            source_bound_values_needed=tuple(payload.get("source_bound_values_needed") or ()),
            unsupported_values=tuple(payload.get("unsupported_values") or ()),
            allowed_calculations=tuple(payload.get("allowed_calculations") or ()),
            assumptions_needed=tuple(payload.get("assumptions_needed") or ()),
            high_stakes_quant=bool(payload.get("high_stakes_quant")),
            direct_use_eligible=bool(payload.get("direct_use_eligible")),
            requires_synthesis=bool(payload.get("requires_synthesis", True)),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SynthesisJob:
    synthesis_job_id: str
    component_ids: tuple[str, ...]
    synthesis_scope: SynthesisScope | str
    allowed_inputs: tuple[str, ...] = ()
    unresolved_gaps_visible: bool = True
    output_contract: str = "bounded_synthesis_summary"
    advisory_gap_signal_allowed: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.synthesis_job_id):
            raise ValueError("synthesis job requires synthesis_job_id")
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(
            self,
            "synthesis_scope",
            _coerce_enum(SynthesisScope, self.synthesis_scope, SynthesisScope.COMPONENT_SYNTHESIS),
        )
        object.__setattr__(self, "allowed_inputs", _text_tuple(self.allowed_inputs))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "synthesis_job_id": _clean_token(self.synthesis_job_id),
                "component_ids": list(self.component_ids),
                "synthesis_scope": self.synthesis_scope.value,
                "allowed_inputs": list(self.allowed_inputs),
                "unresolved_gaps_visible": self.unresolved_gaps_visible,
                "output_contract": _clean_text(self.output_contract, limit=240),
                "advisory_gap_signal_allowed": self.advisory_gap_signal_allowed,
                "owns_source_gap_search_remediation_authority": False,
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SynthesisJob":
        return cls(
            synthesis_job_id=str(payload.get("synthesis_job_id") or ""),
            component_ids=tuple(payload.get("component_ids") or ()),
            synthesis_scope=payload.get("synthesis_scope") or SynthesisScope.COMPONENT_SYNTHESIS.value,
            allowed_inputs=tuple(payload.get("allowed_inputs") or ()),
            unresolved_gaps_visible=bool(payload.get("unresolved_gaps_visible", True)),
            output_contract=str(payload.get("output_contract") or "bounded_synthesis_summary"),
            advisory_gap_signal_allowed=bool(payload.get("advisory_gap_signal_allowed", True)),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class AuditJob:
    audit_job_id: str
    component_ids: tuple[str, ...]
    audit_scope: AuditScope | str
    claim_types: tuple[str, ...] = ()
    assumptions_to_test: tuple[str, ...] = ()
    source_conflict_checks: tuple[str, ...] = ()
    mode_allowed: tuple[SearchMode | str, ...] = (SearchMode.DEEP,)
    remediation_permission: RemediationPermission | str = RemediationPermission.CONDITIONAL_PASSIVE
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _clean_token(self.audit_job_id):
            raise ValueError("audit job requires audit_job_id")
        object.__setattr__(self, "component_ids", _text_tuple(self.component_ids))
        object.__setattr__(
            self,
            "audit_scope",
            _coerce_enum(AuditScope, self.audit_scope, AuditScope.CLAIM_CHALLENGE),
        )
        object.__setattr__(self, "claim_types", _text_tuple(self.claim_types))
        object.__setattr__(self, "assumptions_to_test", _text_tuple(self.assumptions_to_test))
        object.__setattr__(self, "source_conflict_checks", _text_tuple(self.source_conflict_checks))
        object.__setattr__(self, "mode_allowed", _enum_tuple(SearchMode, self.mode_allowed, SearchMode.DEEP))
        object.__setattr__(
            self,
            "remediation_permission",
            _coerce_enum(
                RemediationPermission,
                self.remediation_permission,
                RemediationPermission.CONDITIONAL_PASSIVE,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "audit_job_id": _clean_token(self.audit_job_id),
                "component_ids": list(self.component_ids),
                "audit_scope": self.audit_scope.value,
                "claim_types": list(self.claim_types),
                "assumptions_to_test": list(self.assumptions_to_test),
                "source_conflict_checks": list(self.source_conflict_checks),
                "mode_allowed": [item.value for item in self.mode_allowed],
                "remediation_permission": self.remediation_permission.value,
                "bounded": True,
                "passive": True,
                "open_ended_loop": False,
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuditJob":
        return cls(
            audit_job_id=str(payload.get("audit_job_id") or ""),
            component_ids=tuple(payload.get("component_ids") or ()),
            audit_scope=payload.get("audit_scope") or AuditScope.CLAIM_CHALLENGE.value,
            claim_types=tuple(payload.get("claim_types") or ()),
            assumptions_to_test=tuple(payload.get("assumptions_to_test") or ()),
            source_conflict_checks=tuple(payload.get("source_conflict_checks") or ()),
            mode_allowed=tuple(payload.get("mode_allowed") or (SearchMode.DEEP.value,)),
            remediation_permission=payload.get("remediation_permission")
            or RemediationPermission.CONDITIONAL_PASSIVE.value,
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SearchWorkBudget:
    base_mode_budget_posture: str
    per_component_minimum_viable_budget: BudgetValue = field(default_factory=BudgetValue)
    per_component_cap: BudgetValue = field(default_factory=BudgetValue)
    global_cap: BudgetValue = field(default_factory=BudgetValue)
    rebalancing_policy: RebalancingPolicy | str = RebalancingPolicy.COMPONENT_FAIRNESS_FIRST
    budget_exhausted_posture: BudgetExhaustedPosture | str = BudgetExhaustedPosture.QUALIFY
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rebalancing_policy",
            _coerce_enum(
                RebalancingPolicy,
                self.rebalancing_policy,
                RebalancingPolicy.COMPONENT_FAIRNESS_FIRST,
            ),
        )
        object.__setattr__(
            self,
            "budget_exhausted_posture",
            _coerce_enum(
                BudgetExhaustedPosture,
                self.budget_exhausted_posture,
                BudgetExhaustedPosture.QUALIFY,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "base_mode_budget_posture": _clean_text(self.base_mode_budget_posture, limit=240),
                "per_component_minimum_viable_budget": self.per_component_minimum_viable_budget.to_dict(),
                "per_component_cap": self.per_component_cap.to_dict(),
                "global_cap": self.global_cap.to_dict(),
                "rebalancing_policy": self.rebalancing_policy.value,
                "budget_exhausted_posture": self.budget_exhausted_posture.value,
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SearchWorkBudget":
        return cls(
            base_mode_budget_posture=str(payload.get("base_mode_budget_posture") or "mode_bound"),
            per_component_minimum_viable_budget=BudgetValue.from_dict(
                payload.get("per_component_minimum_viable_budget")
            ),
            per_component_cap=BudgetValue.from_dict(payload.get("per_component_cap")),
            global_cap=BudgetValue.from_dict(payload.get("global_cap")),
            rebalancing_policy=payload.get("rebalancing_policy")
            or RebalancingPolicy.COMPONENT_FAIRNESS_FIRST.value,
            budget_exhausted_posture=payload.get("budget_exhausted_posture")
            or BudgetExhaustedPosture.QUALIFY.value,
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class FollowUpAuthority:
    permission: FollowUpPermission | str
    authorizers: tuple[str, ...] = ("RunAuthority", "SearchJudgment", "SufficiencyJudgment")
    allow_conditions: tuple[str, ...] = ()
    block_conditions: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permission",
            _coerce_enum(FollowUpPermission, self.permission, FollowUpPermission.NOT_ALLOWED),
        )
        object.__setattr__(self, "authorizers", _text_tuple(self.authorizers, limit=120))
        object.__setattr__(self, "allow_conditions", _text_tuple(self.allow_conditions, limit=260))
        object.__setattr__(self, "block_conditions", _text_tuple(self.block_conditions, limit=260))

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "permission": self.permission.value,
                "authorizers": list(self.authorizers),
                "allow_conditions": list(self.allow_conditions),
                "block_conditions": list(self.block_conditions),
                "notes": _clean_text(self.notes, limit=300),
                "executor_authority_allowed": False,
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FollowUpAuthority":
        return cls(
            permission=payload.get("permission") or FollowUpPermission.NOT_ALLOWED.value,
            authorizers=tuple(payload.get("authorizers") or ()),
            allow_conditions=tuple(payload.get("allow_conditions") or ()),
            block_conditions=tuple(payload.get("block_conditions") or ()),
            notes=_clean_text(payload.get("notes"), limit=300),
        )


@dataclass(frozen=True, slots=True)
class FinalSufficiencyPolicy:
    posture: FinalSufficiencyPosture | str = FinalSufficiencyPosture.DEFER_TO_AUTHORITY_CHAIN
    required_component_policy: str = "required_components_must_be_sufficient_or_qualified"
    source_obligation_policy: str = "required_source_obligations_must_be_satisfied_or_fail_closed"
    budget_exhaustion_policy: str = "do_not_upgrade_beyond_supported_evidence"
    final_authority_chain: tuple[str, ...] = (
        "RunAuthorityContract",
        "EvidenceLedger",
        "SearchJudgment",
        "SufficiencyJudgment",
        "FinalAnswerPacket",
        "AuthorExecutor",
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "posture",
            _coerce_enum(
                FinalSufficiencyPosture,
                self.posture,
                FinalSufficiencyPosture.DEFER_TO_AUTHORITY_CHAIN,
            ),
        )
        object.__setattr__(self, "final_authority_chain", _text_tuple(self.final_authority_chain))

    def to_dict(self) -> dict[str, Any]:
        return {
            "posture": self.posture.value,
            "required_component_policy": _clean_text(self.required_component_policy, limit=260),
            "source_obligation_policy": _clean_text(self.source_obligation_policy, limit=260),
            "budget_exhaustion_policy": _clean_text(self.budget_exhaustion_policy, limit=260),
            "final_authority_chain": list(self.final_authority_chain),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> "FinalSufficiencyPolicy":
        if not isinstance(payload, Mapping):
            return cls()
        return cls(
            posture=payload.get("posture") or FinalSufficiencyPosture.DEFER_TO_AUTHORITY_CHAIN.value,
            required_component_policy=str(
                payload.get("required_component_policy")
                or "required_components_must_be_sufficient_or_qualified"
            ),
            source_obligation_policy=str(
                payload.get("source_obligation_policy")
                or "required_source_obligations_must_be_satisfied_or_fail_closed"
            ),
            budget_exhaustion_policy=str(
                payload.get("budget_exhaustion_policy")
                or "do_not_upgrade_beyond_supported_evidence"
            ),
            final_authority_chain=tuple(payload.get("final_authority_chain") or ()),
        )


@dataclass(frozen=True, slots=True)
class AuthorityRef:
    authority_id: str
    authority_name: str
    role: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "authority_id": _clean_token(self.authority_id),
                "authority_name": _clean_token(self.authority_name),
                "role": _clean_text(self.role, limit=240),
                "metadata": _json_safe(self.metadata),
            }
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityRef":
        return cls(
            authority_id=str(payload.get("authority_id") or ""),
            authority_name=str(payload.get("authority_name") or ""),
            role=str(payload.get("role") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class SearchWorkPlanValidationResult:
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
class SearchWorkPlan:
    requested_mode: RequestedModeDescriptor
    effective_contract: EffectiveContractDescriptor
    query_shape: QueryShapeDescriptor
    components: tuple[SearchWorkComponent, ...]
    provider_jobs: tuple[ProviderJob, ...] = ()
    quant_work_units: tuple[QuantWorkUnit, ...] = ()
    synthesis_jobs: tuple[SynthesisJob, ...] = ()
    audit_jobs: tuple[AuditJob, ...] = ()
    budget: SearchWorkBudget = field(default_factory=lambda: SearchWorkBudget("mode_bound"))
    follow_up_authority: FollowUpAuthority = field(
        default_factory=lambda: FollowUpAuthority(FollowUpPermission.NOT_ALLOWED)
    )
    final_sufficiency_policy: FinalSufficiencyPolicy = field(default_factory=FinalSufficiencyPolicy)
    stop_conditions: tuple[StopCondition, ...] = ()
    authority_refs: tuple[AuthorityRef, ...] = ()
    planning_posture: str = "passive_contract_only"
    passive: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SEARCH_WORK_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", tuple(self.components or ()))
        object.__setattr__(self, "provider_jobs", tuple(self.provider_jobs or ()))
        object.__setattr__(self, "quant_work_units", tuple(self.quant_work_units or ()))
        object.__setattr__(self, "synthesis_jobs", tuple(self.synthesis_jobs or ()))
        object.__setattr__(self, "audit_jobs", tuple(self.audit_jobs or ()))
        object.__setattr__(self, "stop_conditions", tuple(self.stop_conditions or ()))
        object.__setattr__(self, "authority_refs", tuple(self.authority_refs or ()))

    def validate(self) -> SearchWorkPlanValidationResult:
        errors: list[str] = []
        component_ids = [component.component_id for component in self.components]
        component_id_set = set(component_ids)
        if len(component_ids) != len(component_id_set):
            errors.append("duplicate component_id values are not allowed")
        if not component_ids:
            errors.append("at least one component is required")

        obligation_ids_by_component = {
            component.component_id: set(component.source_obligation_ids())
            for component in self.components
        }
        all_obligation_ids = set().union(*obligation_ids_by_component.values()) if obligation_ids_by_component else set()

        for component in self.components:
            for dependency in component.depends_on:
                if dependency not in component_id_set:
                    errors.append(f"component {component.component_id} depends on missing component {dependency}")
                if dependency == component.component_id:
                    errors.append(f"component {component.component_id} cannot depend on itself")
            min_budget = component.per_component_budget.minimum_viable.numeric_value
            cap_budget = component.per_component_budget.cap.numeric_value
            if min_budget is not None and cap_budget is not None and min_budget > cap_budget:
                errors.append(
                    f"component {component.component_id} minimum viable budget exceeds component cap"
                )

        for job in self.provider_jobs:
            errors.extend(
                _missing_component_errors("provider job", job.provider_job_id, job.component_ids, component_id_set)
            )
            for obligation_id in job.source_obligation_ids:
                if obligation_id not in all_obligation_ids:
                    errors.append(
                        f"provider job {job.provider_job_id} references missing source obligation {obligation_id}"
                    )

        for unit in self.quant_work_units:
            errors.extend(_missing_component_errors("quant work unit", unit.quant_unit_id, unit.component_ids, component_id_set))

        for job in self.synthesis_jobs:
            errors.extend(
                _missing_component_errors("synthesis job", job.synthesis_job_id, job.component_ids, component_id_set)
            )

        for job in self.audit_jobs:
            errors.extend(_missing_component_errors("audit job", job.audit_job_id, job.component_ids, component_id_set))

        invalid_authorizers = [
            item
            for item in self.follow_up_authority.authorizers
            if item not in _VALID_FOLLOW_UP_AUTHORIZERS
        ]
        forbidden_authorizers = [
            item
            for item in self.follow_up_authority.authorizers
            if item in _FORBIDDEN_EXECUTOR_AUTHORIZERS
        ]
        if invalid_authorizers:
            errors.append(
                "follow-up authorizers must be RunAuthority/SearchJudgment/SufficiencyJudgment posture: "
                + ", ".join(invalid_authorizers)
            )
        if forbidden_authorizers:
            errors.append(
                "bounded executors cannot authorize follow-up: "
                + ", ".join(forbidden_authorizers)
            )

        return SearchWorkPlanValidationResult(errors=tuple(errors))

    def require_valid(self) -> "SearchWorkPlan":
        self.validate().raise_for_errors()
        return self

    def to_dict(self) -> dict[str, Any]:
        runtime_consumed = not bool(self.passive)
        return {
            "schema_version": self.schema_version,
            "trace_key": SEARCH_WORK_PLAN_TRACE_KEY,
            "planning_posture": _clean_token(self.planning_posture),
            "passive": bool(self.passive),
            "runtime_consumed": runtime_consumed,
            "prompt_behavior_changed": False,
            "provider_search_behavior_changed": False,
            "query_plan_behavior_changed": runtime_consumed,
            "requested_mode": self.requested_mode.to_dict(),
            "effective_contract": self.effective_contract.to_dict(),
            "query_shape": self.query_shape.to_dict(),
            "components": [component.to_dict() for component in self.components],
            "provider_jobs": [job.to_dict() for job in self.provider_jobs],
            "quant_work_units": [unit.to_dict() for unit in self.quant_work_units],
            "synthesis_jobs": [job.to_dict() for job in self.synthesis_jobs],
            "audit_jobs": [job.to_dict() for job in self.audit_jobs],
            "budget": self.budget.to_dict(),
            "follow_up_authority": self.follow_up_authority.to_dict(),
            "final_sufficiency_policy": self.final_sufficiency_policy.to_dict(),
            "stop_conditions": [condition.to_dict() for condition in self.stop_conditions],
            "authority_refs": [ref.to_dict() for ref in self.authority_refs],
            "metadata": _json_safe(self.metadata),
            "validation": self.validate().to_dict(),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SEARCH_WORK_PLAN_TRACE_KEY: self.to_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SearchWorkPlan":
        return cls(
            requested_mode=RequestedModeDescriptor.from_dict(dict(payload.get("requested_mode") or {})),
            effective_contract=EffectiveContractDescriptor.from_dict(
                dict(payload.get("effective_contract") or {})
            ),
            query_shape=QueryShapeDescriptor.from_dict(dict(payload.get("query_shape") or {})),
            components=tuple(
                SearchWorkComponent.from_dict(item)
                for item in payload.get("components") or ()
                if isinstance(item, Mapping)
            ),
            provider_jobs=tuple(
                ProviderJob.from_dict(item)
                for item in payload.get("provider_jobs") or ()
                if isinstance(item, Mapping)
            ),
            quant_work_units=tuple(
                QuantWorkUnit.from_dict(item)
                for item in payload.get("quant_work_units") or ()
                if isinstance(item, Mapping)
            ),
            synthesis_jobs=tuple(
                SynthesisJob.from_dict(item)
                for item in payload.get("synthesis_jobs") or ()
                if isinstance(item, Mapping)
            ),
            audit_jobs=tuple(
                AuditJob.from_dict(item)
                for item in payload.get("audit_jobs") or ()
                if isinstance(item, Mapping)
            ),
            budget=SearchWorkBudget.from_dict(dict(payload.get("budget") or {})),
            follow_up_authority=FollowUpAuthority.from_dict(
                dict(payload.get("follow_up_authority") or {})
            ),
            final_sufficiency_policy=FinalSufficiencyPolicy.from_dict(
                payload.get("final_sufficiency_policy")
            ),
            stop_conditions=tuple(
                StopCondition.from_dict(item)
                for item in payload.get("stop_conditions") or ()
                if isinstance(item, Mapping)
            ),
            authority_refs=tuple(
                AuthorityRef.from_dict(item)
                for item in payload.get("authority_refs") or ()
                if isinstance(item, Mapping)
            ),
            planning_posture=str(payload.get("planning_posture") or "passive_contract_only"),
            passive=bool(payload.get("passive", True)),
            metadata=dict(payload.get("metadata") or {}),
            schema_version=str(payload.get("schema_version") or SEARCH_WORK_PLAN_SCHEMA_VERSION),
        )


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
    "SEARCH_WORK_PLAN_SCHEMA_VERSION",
    "SEARCH_WORK_PLAN_TRACE_KEY",
    "AuditJob",
    "AuditScope",
    "AuthorityRef",
    "BudgetExhaustedPosture",
    "BudgetValue",
    "BudgetValuePosture",
    "ComponentBudget",
    "EffectiveContractDescriptor",
    "EffectiveContractKind",
    "FinalSufficiencyPolicy",
    "FinalSufficiencyPosture",
    "FollowUpAuthority",
    "FollowUpPermission",
    "ModeDepthAllowance",
    "ModeMismatchPosture",
    "ProviderJob",
    "ProviderJobKind",
    "QuantWorkUnit",
    "QueryShapeDescriptor",
    "QueryShapeKind",
    "RebalancingPolicy",
    "RemediationPermission",
    "RequestedModeDescriptor",
    "SearchMode",
    "SearchWorkBudget",
    "SearchWorkComponent",
    "SearchWorkPlan",
    "SearchWorkPlanValidationResult",
    "SourceObligation",
    "SourceObligationKind",
    "SourceObligationStrictness",
    "StopCondition",
    "StopConditionKind",
    "StopOutcome",
    "SynthesisJob",
    "SynthesisScope",
]
