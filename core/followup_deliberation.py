"""Passive bounded follow-up deliberation records for AG-96I1.

The records in this module are offline authority grammar only. They do not call
providers, search, retrieval, fetch/read, prompts, models, citations, final
answer writers, process spawning, or arbitrary code execution. A follow-up
authorization candidate is not runtime permission to execute search in AG-96I1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

FOLLOWUP_DELIBERATION_SCHEMA_VERSION = "followup_deliberation_ag96i1_v1"
FOLLOWUP_DELIBERATION_TRACE_KEY = "followup_deliberation_checkpoint"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_text",
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
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_text",
        "text",
        "token",
    }
)


class FollowupMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class GapType(str, Enum):
    COMPONENT_COVERAGE_GAP = "component_coverage_gap"
    SOURCE_CLASS_GAP = "source_class_gap"
    OFFICIAL_CURRENT_GAP = "official_current_gap"
    LEGAL_CURRENT_PRIMARY_GAP = "legal_current_primary_gap"
    CANONICAL_DOC_GAP = "canonical_doc_gap"
    SOURCE_BOUND_NUMERIC_GAP = "source_bound_numeric_gap"
    CURRENTNESS_GAP = "currentness_gap"
    CONFLICT_RECONCILIATION_GAP = "conflict_reconciliation_gap"
    ENTITY_AMBIGUITY_GAP = "entity_ambiguity_gap"
    WEAK_CORPUS_GAP = "weak_corpus_gap"
    CITATION_FINAL_ANSWER_POSTURE_GAP = "citation_final_answer_posture_gap"
    CONTRACT_SHAPE_GAP = "contract_shape_gap"


class ReasoningHopType(str, Enum):
    MICRO_VERIFICATION = "micro_verification"
    MESO_TARGETED_REPAIR = "meso_targeted_repair"
    MACRO_RUN_DIAGNOSIS = "macro_run_diagnosis"


class FollowupDecision(str, Enum):
    AUTHORIZE_CANDIDATE = "authorize_candidate"
    RECOMMEND = "recommend"
    DENY = "deny"
    STOP = "stop"
    CAVEAT = "caveat"
    REFUSE = "refuse"
    NEEDS_DEEP = "needs_deep"
    INSUFFICIENT_BUDGET = "insufficient_budget"
    DECORATIVE_SEARCH_BLOCKED = "decorative_search_blocked"


class ProviderJobKind(str, Enum):
    SCOUT_DISAMBIGUATION = "scout_disambiguation"
    DIRECT_CANDIDATE_SEARCH = "direct_candidate_search"
    OFFICIAL_CURRENT_CANDIDATE_ACQUISITION = (
        "official_current_candidate_acquisition"
    )
    LEGAL_CURRENT_PRIMARY_ACQUISITION = "legal_current_primary_acquisition"
    CANONICAL_DOC_ACQUISITION = "canonical_doc_acquisition"
    SEMANTIC_RECALL = "semantic_recall"
    FETCH_READ_EXTRACT = "fetch_read_extract"
    CONFLICT_CURRENTNESS_CHECK = "conflict_currentness_check"
    SOURCE_BOUND_NUMERIC_EXTRACTION_CALCULATION_SUPPORT = (
        "source_bound_numeric_extraction_calculation_support"
    )
    RECONCILIATION_SUPPORT = "reconciliation_support"
    BRIDGE_HINT_DISCOVERY = "bridge_hint_discovery"
    PROVIDER_ANSWER_CONTEXT = "provider_answer_context"


class StopPosture(str, Enum):
    RETURN_TO_EVIDENCE_LEDGER = "return_to_evidence_ledger"
    ANSWER_WITH_CAVEATS = "answer_with_caveats"
    PARTIAL_ANSWER = "partial_answer"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSE_OR_BLOCK = "refuse_or_block"
    NEEDS_DEEP = "needs_deep"


def clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = clean_text(value, limit=limit)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def stable_hash(value: Any) -> str:
    return hashlib.sha256(repr(safe_json(value)).encode("utf-8")).hexdigest()


def safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            key_text = clean_token(key, limit=120)
            if not key_text or _is_sensitive_key(key_text):
                continue
            safe = safe_json(item, depth=depth + 1)
            if safe not in (None, ""):
                out[key_text] = safe
        return out
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [safe_json(item, depth=depth + 1) for item in list(value)[:120]]
    if hasattr(value, "to_dict"):
        return safe_json(value.to_dict(), depth=depth + 1)
    return clean_text(value, limit=300)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


def _coerce_enum(enum_class: type[Enum], value: Any, default: Enum) -> Enum:
    raw = value.value if isinstance(value, Enum) else value
    for item in enum_class:
        if item.value == raw:
            return item
    return default


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if value is None:
        values: Sequence[Any] = ()
    elif isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        text = clean_token(item, limit=limit)
        if text and text not in out:
            out.append(text)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    cost_points_remaining: int = 0
    provider_calls_remaining: int = 0
    fetches_remaining: int = 0
    read_units_remaining: int = 0
    followup_rounds_remaining: int = 0
    meso_authorizations_remaining: int = 0
    macro_hops_remaining: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "cost_points_remaining": int(self.cost_points_remaining),
            "provider_calls_remaining": int(self.provider_calls_remaining),
            "fetches_remaining": int(self.fetches_remaining),
            "read_units_remaining": int(self.read_units_remaining),
            "followup_rounds_remaining": int(self.followup_rounds_remaining),
            "meso_authorizations_remaining": int(self.meso_authorizations_remaining),
            "macro_hops_remaining": int(self.macro_hops_remaining),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any] | None) -> "BudgetSnapshot":
        source = dict(payload or {})
        return cls(
            cost_points_remaining=_int(source.get("cost_points_remaining")),
            provider_calls_remaining=_int(source.get("provider_calls_remaining")),
            fetches_remaining=_int(source.get("fetches_remaining")),
            read_units_remaining=_int(source.get("read_units_remaining")),
            followup_rounds_remaining=_int(source.get("followup_rounds_remaining")),
            meso_authorizations_remaining=_int(
                source.get("meso_authorizations_remaining")
            ),
            macro_hops_remaining=_int(source.get("macro_hops_remaining")),
        )


@dataclass(frozen=True, slots=True)
class BudgetDebit:
    cost_points: int = 0
    provider_calls: int = 0
    fetches_reserved: int = 0
    read_units_reserved: int = 0
    followup_rounds: int = 0
    meso_authorizations: int = 0
    macro_hops: int = 0
    budget_bucket: str = "targeted_repair"

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "cost_points": int(self.cost_points),
                "provider_calls": int(self.provider_calls),
                "fetches_reserved": int(self.fetches_reserved),
                "read_units_reserved": int(self.read_units_reserved),
                "followup_rounds": int(self.followup_rounds),
                "meso_authorizations": int(self.meso_authorizations),
                "macro_hops": int(self.macro_hops),
                "budget_bucket": clean_token(self.budget_bucket),
            }
        )


@dataclass(frozen=True, slots=True)
class GapAssessment:
    gap_id: str
    gap_type: GapType | str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...] = ()
    severity: str = "central_required"
    evidence_indicators: tuple[str, ...] = ()
    recommended_hop_type: ReasoningHopType | str = ReasoningHopType.MESO_TARGETED_REPAIR
    repairability: str = "repairable_with_targeted_job"
    balanced_eligible: bool = True
    deep_eligible: bool = True
    deep_only_reconciliation: bool = False
    bridge_only_provider_output_present: bool = False
    must_not_upgrade_final_claim: bool = True
    non_repair_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "gap_type", _coerce_enum(GapType, self.gap_type, GapType.SOURCE_CLASS_GAP)
        )
        object.__setattr__(
            self,
            "recommended_hop_type",
            _coerce_enum(
                ReasoningHopType,
                self.recommended_hop_type,
                ReasoningHopType.MESO_TARGETED_REPAIR,
            ),
        )
        object.__setattr__(self, "requirement_ids", _text_tuple(self.requirement_ids))
        object.__setattr__(
            self, "evidence_indicators", _text_tuple(self.evidence_indicators, limit=260)
        )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "record_type": "gap_assessment",
                "gap_id": clean_token(self.gap_id),
                "gap_type": self.gap_type.value,
                "component_id": clean_token(self.component_id),
                "source_obligation_id": clean_token(self.source_obligation_id),
                "requirement_ids": list(self.requirement_ids),
                "severity": clean_token(self.severity),
                "evidence_indicators": list(self.evidence_indicators),
                "recommended_hop_type": self.recommended_hop_type.value,
                "repairability": clean_token(self.repairability),
                "balanced_eligible": bool(self.balanced_eligible),
                "deep_eligible": bool(self.deep_eligible),
                "deep_only_reconciliation": bool(self.deep_only_reconciliation),
                "bridge_only_provider_output_present": bool(
                    self.bridge_only_provider_output_present
                ),
                "must_not_upgrade_final_claim": bool(self.must_not_upgrade_final_claim),
                "non_repair_reason": clean_text(self.non_repair_reason, limit=240),
            }
        )


@dataclass(frozen=True, slots=True)
class ReasoningHop:
    hop_id: str
    hop_type: ReasoningHopType | str
    gap_id: str
    mode: FollowupMode | str
    purpose: str
    may_request_followup: bool
    inspection_refs: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hop_type",
            _coerce_enum(
                ReasoningHopType,
                self.hop_type,
                ReasoningHopType.MICRO_VERIFICATION,
            ),
        )
        object.__setattr__(
            self, "mode", _coerce_enum(FollowupMode, self.mode, FollowupMode.BALANCED)
        )
        object.__setattr__(self, "inspection_refs", _text_tuple(self.inspection_refs))
        object.__setattr__(
            self, "stop_conditions", _text_tuple(self.stop_conditions, limit=260)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "reasoning_hop",
            "hop_id": clean_token(self.hop_id),
            "hop_type": self.hop_type.value,
            "gap_id": clean_token(self.gap_id),
            "mode": self.mode.value,
            "purpose": clean_text(self.purpose, limit=300),
            "may_request_followup": bool(self.may_request_followup),
            "inspection_refs": list(self.inspection_refs),
            "stop_conditions": list(self.stop_conditions),
            "may_directly_browse": False,
            "may_directly_fetch": False,
            "may_run_code": False,
            "may_select_citations": False,
            "may_override_final_sufficiency": False,
        }


@dataclass(frozen=True, slots=True)
class EvidenceLedgerCustodyUpdate:
    custody_update_expected: tuple[str, ...]
    source_classes: tuple[str, ...] = ()
    currentness_required: bool = False
    answer_bearing_required: bool = True
    underlying_sources_required_for_bridge: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "custody_update_expected",
            _text_tuple(self.custody_update_expected, limit=160),
        )
        object.__setattr__(self, "source_classes", _text_tuple(self.source_classes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "custody_update_expected": list(self.custody_update_expected),
            "source_classes": list(self.source_classes),
            "currentness_required": bool(self.currentness_required),
            "answer_bearing_required": bool(self.answer_bearing_required),
            "underlying_sources_required_for_bridge": bool(
                self.underlying_sources_required_for_bridge
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupRecommendation:
    recommendation_id: str
    gap_id: str
    gap_type: GapType | str
    decision: FollowupDecision | str
    hop_type: ReasoningHopType | str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...] = ()
    provider_job_kind: ProviderJobKind | str | None = None
    query_intent: str | None = None
    expected_custody_update: EvidenceLedgerCustodyUpdate | None = None
    budget_requested: BudgetDebit = field(default_factory=BudgetDebit)
    fallback_posture: StopPosture | str = StopPosture.ANSWER_WITH_CAVEATS
    bridge_only_provider_output: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "gap_type", _coerce_enum(GapType, self.gap_type, GapType.SOURCE_CLASS_GAP)
        )
        object.__setattr__(
            self,
            "decision",
            _coerce_enum(FollowupDecision, self.decision, FollowupDecision.RECOMMEND),
        )
        object.__setattr__(
            self,
            "hop_type",
            _coerce_enum(
                ReasoningHopType,
                self.hop_type,
                ReasoningHopType.MESO_TARGETED_REPAIR,
            ),
        )
        if self.provider_job_kind is not None:
            object.__setattr__(
                self,
                "provider_job_kind",
                _coerce_enum(
                    ProviderJobKind,
                    self.provider_job_kind,
                    ProviderJobKind.DIRECT_CANDIDATE_SEARCH,
                ),
            )
        object.__setattr__(self, "requirement_ids", _text_tuple(self.requirement_ids))
        object.__setattr__(
            self,
            "fallback_posture",
            _coerce_enum(StopPosture, self.fallback_posture, StopPosture.ANSWER_WITH_CAVEATS),
        )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "record_type": "followup_recommendation",
                "recommendation_id": clean_token(self.recommendation_id),
                "gap_id": clean_token(self.gap_id),
                "gap_type": self.gap_type.value,
                "decision": self.decision.value,
                "hop_type": self.hop_type.value,
                "component_id": clean_token(self.component_id),
                "source_obligation_id": clean_token(self.source_obligation_id),
                "requirement_ids": list(self.requirement_ids),
                "provider_job_kind": (
                    self.provider_job_kind.value
                    if isinstance(self.provider_job_kind, ProviderJobKind)
                    else None
                ),
                "query_intent": clean_text(self.query_intent, limit=300),
                "expected_custody_update": (
                    self.expected_custody_update.to_dict()
                    if self.expected_custody_update
                    else None
                ),
                "budget_requested": self.budget_requested.to_dict(),
                "fallback_posture": self.fallback_posture.value,
                "bridge_only_provider_output": bool(self.bridge_only_provider_output),
                "reason": clean_text(self.reason, limit=300),
            }
        )


@dataclass(frozen=True, slots=True)
class FollowupAuthorizationCandidate:
    authorization_id: str
    recommendation_id: str
    decision: FollowupDecision | str
    mode: FollowupMode | str
    hop_type: ReasoningHopType | str
    provider_job_kind: ProviderJobKind | str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    budget_debit: BudgetDebit
    expected_evidence_ledger_custody_update: EvidenceLedgerCustodyUpdate
    fallback_stop_posture: StopPosture | str
    fallback_caveat_refuse_posture: StopPosture | str
    retry_allowed: bool = False
    requires_runauthority_seal: bool = True
    bridge_only_provider_output: bool = False
    rationale: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision",
            _coerce_enum(
                FollowupDecision,
                self.decision,
                FollowupDecision.AUTHORIZE_CANDIDATE,
            ),
        )
        object.__setattr__(
            self, "mode", _coerce_enum(FollowupMode, self.mode, FollowupMode.BALANCED)
        )
        object.__setattr__(
            self,
            "hop_type",
            _coerce_enum(
                ReasoningHopType,
                self.hop_type,
                ReasoningHopType.MESO_TARGETED_REPAIR,
            ),
        )
        object.__setattr__(
            self,
            "provider_job_kind",
            _coerce_enum(
                ProviderJobKind,
                self.provider_job_kind,
                ProviderJobKind.DIRECT_CANDIDATE_SEARCH,
            ),
        )
        object.__setattr__(self, "requirement_ids", _text_tuple(self.requirement_ids))
        object.__setattr__(
            self,
            "fallback_stop_posture",
            _coerce_enum(
                StopPosture,
                self.fallback_stop_posture,
                StopPosture.ANSWER_WITH_CAVEATS,
            ),
        )
        object.__setattr__(
            self,
            "fallback_caveat_refuse_posture",
            _coerce_enum(
                StopPosture,
                self.fallback_caveat_refuse_posture,
                StopPosture.INSUFFICIENT_EVIDENCE,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "followup_authorization_candidate",
            "authorization_id": clean_token(self.authorization_id),
            "recommendation_id": clean_token(self.recommendation_id),
            "decision": self.decision.value,
            "mode": self.mode.value,
            "hop_type": self.hop_type.value,
            "provider_job_kind": self.provider_job_kind.value,
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": list(self.requirement_ids),
            "budget_debit": self.budget_debit.to_dict(),
            "expected_evidence_ledger_custody_update": (
                self.expected_evidence_ledger_custody_update.to_dict()
            ),
            "fallback_stop_posture": self.fallback_stop_posture.value,
            "fallback_caveat_refuse_posture": self.fallback_caveat_refuse_posture.value,
            "retry_allowed": bool(self.retry_allowed),
            "requires_runauthority_seal": bool(self.requires_runauthority_seal),
            "bridge_only_provider_output": bool(self.bridge_only_provider_output),
            "rationale": clean_text(self.rationale, limit=300),
            "may_directly_browse": False,
            "may_directly_fetch": False,
            "may_run_code": False,
            "may_select_citations": False,
            "may_override_final_sufficiency": False,
            "runtime_permission_to_execute_in_ag96i1": False,
        }


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    budget_decision_id: str
    mode: FollowupMode | str
    decision: FollowupDecision | str
    budget_before: BudgetSnapshot
    debit: BudgetDebit
    budget_after: BudgetSnapshot
    starvation_check_passed: bool
    protected_components: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "mode", _coerce_enum(FollowupMode, self.mode, FollowupMode.BALANCED)
        )
        object.__setattr__(
            self,
            "decision",
            _coerce_enum(FollowupDecision, self.decision, FollowupDecision.DENY),
        )
        object.__setattr__(
            self, "protected_components", _text_tuple(self.protected_components)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "budget_decision",
            "budget_decision_id": clean_token(self.budget_decision_id),
            "mode": self.mode.value,
            "decision": self.decision.value,
            "budget_before": self.budget_before.to_dict(),
            "debit": self.debit.to_dict(),
            "budget_after": self.budget_after.to_dict(),
            "starvation_check": {
                "passed": bool(self.starvation_check_passed),
                "protected_components": list(self.protected_components),
            },
            "reason": clean_text(self.reason, limit=300),
        }


@dataclass(frozen=True, slots=True)
class StopDecision:
    stop_id: str
    decision: FollowupDecision | str
    stop_reason: str
    component_id: str | None = None
    source_obligation_id: str | None = None
    final_answer_posture: StopPosture | str = StopPosture.ANSWER_WITH_CAVEATS
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision", _coerce_enum(FollowupDecision, self.decision, FollowupDecision.STOP)
        )
        object.__setattr__(
            self,
            "final_answer_posture",
            _coerce_enum(
                StopPosture,
                self.final_answer_posture,
                StopPosture.ANSWER_WITH_CAVEATS,
            ),
        )
        object.__setattr__(
            self, "mandatory_caveats", _text_tuple(self.mandatory_caveats, limit=260)
        )
        object.__setattr__(
            self, "prohibited_upgrades", _text_tuple(self.prohibited_upgrades, limit=260)
        )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "record_type": "stop_decision",
                "stop_id": clean_token(self.stop_id),
                "decision": self.decision.value,
                "stop_reason": clean_token(self.stop_reason),
                "component_id": clean_token(self.component_id),
                "source_obligation_id": clean_token(self.source_obligation_id),
                "final_answer_posture": self.final_answer_posture.value,
                "mandatory_caveats": list(self.mandatory_caveats),
                "prohibited_upgrades": list(self.prohibited_upgrades),
            }
        )


@dataclass(frozen=True, slots=True)
class CaveatRefuseDecision:
    decision_id: str
    decision: FollowupDecision | str
    reason: str
    safe_output_allowed: bool
    allowed_posture: StopPosture | str
    blocked_posture: str
    mandatory_language_intent: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision",
            _coerce_enum(FollowupDecision, self.decision, FollowupDecision.CAVEAT),
        )
        object.__setattr__(
            self,
            "allowed_posture",
            _coerce_enum(StopPosture, self.allowed_posture, StopPosture.ANSWER_WITH_CAVEATS),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "caveat_refuse_decision",
            "decision_id": clean_token(self.decision_id),
            "decision": self.decision.value,
            "reason": clean_token(self.reason),
            "safe_output_allowed": bool(self.safe_output_allowed),
            "allowed_posture": self.allowed_posture.value,
            "blocked_posture": clean_token(self.blocked_posture),
            "mandatory_language_intent": clean_text(
                self.mandatory_language_intent, limit=300
            ),
        }


@dataclass(frozen=True, slots=True)
class SufficiencyHandoff:
    handoff_id: str
    ready_for_sufficiency_judgment: bool
    satisfied_obligations: tuple[str, ...] = ()
    partial_obligations: tuple[str, ...] = ()
    missing_obligations: tuple[str, ...] = ()
    unresolved_conflicts: tuple[str, ...] = ()
    source_bound_numeric_unknowns: tuple[str, ...] = ()
    source_bound_numeric_resolutions: tuple[str, ...] = ()
    recommended_final_posture: StopPosture | str = StopPosture.ANSWER_WITH_CAVEATS
    must_preserve_prohibited_upgrades: bool = True
    bridge_only_provider_outputs_satisfy_final_evidence: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "satisfied_obligations",
            "partial_obligations",
            "missing_obligations",
            "unresolved_conflicts",
            "source_bound_numeric_unknowns",
            "source_bound_numeric_resolutions",
        ):
            object.__setattr__(self, field_name, _text_tuple(getattr(self, field_name)))
        object.__setattr__(
            self,
            "recommended_final_posture",
            _coerce_enum(
                StopPosture,
                self.recommended_final_posture,
                StopPosture.ANSWER_WITH_CAVEATS,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "sufficiency_handoff",
            "handoff_id": clean_token(self.handoff_id),
            "ready_for_sufficiency_judgment": bool(self.ready_for_sufficiency_judgment),
            "satisfied_obligations": list(self.satisfied_obligations),
            "partial_obligations": list(self.partial_obligations),
            "missing_obligations": list(self.missing_obligations),
            "unresolved_conflicts": list(self.unresolved_conflicts),
            "source_bound_numeric_unknowns": list(self.source_bound_numeric_unknowns),
            "source_bound_numeric_resolutions": list(
                self.source_bound_numeric_resolutions
            ),
            "recommended_final_posture": self.recommended_final_posture.value,
            "must_preserve_prohibited_upgrades": bool(
                self.must_preserve_prohibited_upgrades
            ),
            "bridge_only_provider_outputs_satisfy_final_evidence": bool(
                self.bridge_only_provider_outputs_satisfy_final_evidence
            ),
        }


@dataclass(frozen=True, slots=True)
class DeepAssumptionAudit:
    audit_id: str
    mode: FollowupMode | str
    assumptions: tuple[Mapping[str, Any], ...] = ()
    source_family_gaps: tuple[Mapping[str, Any], ...] = ()
    conflict_summary: tuple[Mapping[str, Any], ...] = ()
    sensitivity: tuple[Mapping[str, Any], ...] = ()
    followup_allowed: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _coerce_enum(FollowupMode, self.mode, FollowupMode.DEEP))
        object.__setattr__(
            self,
            "assumptions",
            tuple(safe_json(item) for item in self.assumptions if isinstance(item, Mapping)),
        )
        object.__setattr__(
            self,
            "source_family_gaps",
            tuple(
                safe_json(item)
                for item in self.source_family_gaps
                if isinstance(item, Mapping)
            ),
        )
        object.__setattr__(
            self,
            "conflict_summary",
            tuple(
                safe_json(item)
                for item in self.conflict_summary
                if isinstance(item, Mapping)
            ),
        )
        object.__setattr__(
            self,
            "sensitivity",
            tuple(safe_json(item) for item in self.sensitivity if isinstance(item, Mapping)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "deep_assumption_audit",
            "audit_id": clean_token(self.audit_id),
            "mode": self.mode.value,
            "assumptions": list(self.assumptions),
            "source_family_gaps": list(self.source_family_gaps),
            "conflict_summary": list(self.conflict_summary),
            "sensitivity": list(self.sensitivity),
            "followup_allowed": bool(self.followup_allowed),
            "reason": clean_text(self.reason, limit=300),
        }


@dataclass(frozen=True, slots=True)
class FollowupDeliberationCheckpoint:
    checkpoint_id: str
    run_id: str
    mode: FollowupMode | str
    gap_assessments: tuple[GapAssessment, ...] = ()
    reasoning_hops: tuple[ReasoningHop, ...] = ()
    followup_recommendations: tuple[FollowupRecommendation, ...] = ()
    followup_authorization_candidates: tuple[FollowupAuthorizationCandidate, ...] = ()
    budget_decisions: tuple[BudgetDecision, ...] = ()
    stop_decisions: tuple[StopDecision, ...] = ()
    caveat_refuse_decisions: tuple[CaveatRefuseDecision, ...] = ()
    sufficiency_handoff: SufficiencyHandoff = field(
        default_factory=lambda: SufficiencyHandoff(
            handoff_id="sufficiency_handoff",
            ready_for_sufficiency_judgment=True,
            recommended_final_posture=StopPosture.ANSWER_WITH_CAVEATS,
        )
    )
    deep_assumption_audit: DeepAssumptionAudit | None = None
    input_state_refs: Mapping[str, Any] = field(default_factory=dict)
    human_review_summary: tuple[str, ...] = ()
    schema_version: str = FOLLOWUP_DELIBERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "mode", _coerce_enum(FollowupMode, self.mode, FollowupMode.BALANCED)
        )
        object.__setattr__(self, "gap_assessments", tuple(self.gap_assessments))
        object.__setattr__(self, "reasoning_hops", tuple(self.reasoning_hops))
        object.__setattr__(
            self, "followup_recommendations", tuple(self.followup_recommendations)
        )
        object.__setattr__(
            self,
            "followup_authorization_candidates",
            tuple(self.followup_authorization_candidates),
        )
        object.__setattr__(self, "budget_decisions", tuple(self.budget_decisions))
        object.__setattr__(self, "stop_decisions", tuple(self.stop_decisions))
        object.__setattr__(
            self, "caveat_refuse_decisions", tuple(self.caveat_refuse_decisions)
        )
        object.__setattr__(
            self, "human_review_summary", _text_tuple(self.human_review_summary, limit=260)
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "trace_key": FOLLOWUP_DELIBERATION_TRACE_KEY,
            "record_type": "followup_deliberation_checkpoint",
            "checkpoint_id": clean_token(self.checkpoint_id),
            "run_id": clean_token(self.run_id),
            "mode": self.mode.value,
            "passive_offline_only": True,
            "input_state_refs": safe_json(self.input_state_refs),
            "capabilities": {
                "may_directly_browse": False,
                "may_directly_fetch": False,
                "may_run_code": False,
                "may_authorize_provider_jobs": False,
                "may_recommend_provider_jobs": True,
                "requires_future_runkernel_execution": True,
                "may_select_citations": False,
                "may_override_final_sufficiency": False,
            },
            "records": {
                "gap_assessments": [item.to_dict() for item in self.gap_assessments],
                "reasoning_hops": [item.to_dict() for item in self.reasoning_hops],
                "followup_recommendations": [
                    item.to_dict() for item in self.followup_recommendations
                ],
                "followup_authorization_candidates": [
                    item.to_dict() for item in self.followup_authorization_candidates
                ],
                "budget_decisions": [item.to_dict() for item in self.budget_decisions],
                "stop_decisions": [item.to_dict() for item in self.stop_decisions],
                "caveat_refuse_decisions": [
                    item.to_dict() for item in self.caveat_refuse_decisions
                ],
                "sufficiency_handoff": self.sufficiency_handoff.to_dict(),
                "deep_assumption_audit": (
                    self.deep_assumption_audit.to_dict()
                    if self.deep_assumption_audit
                    else None
                ),
            },
            "human_review_summary": list(self.human_review_summary),
            "behavior_boundary_flags": {
                "provider_search_behavior_changed": False,
                "provider_selected": False,
                "search_executed": False,
                "retrieval_executed": False,
                "fetch_executed": False,
                "model_called": False,
                "prompt_behavior_changed": False,
                "citation_behavior_changed": False,
                "author_prose_behavior_changed": False,
                "final_answer_behavior_changed": False,
                "arbitrary_code_execution_used": False,
                "pipeline_orchestrator_domain_logic_changed": False,
            },
        }
        return safe_json(payload)

    def to_trace_fragment(self) -> dict[str, Any]:
        return {FOLLOWUP_DELIBERATION_TRACE_KEY: self.to_dict()}


def build_followup_deliberation_checkpoint(
    fixture_projection: Mapping[str, Any],
) -> FollowupDeliberationCheckpoint:
    """Build a deterministic offline checkpoint from sanitized fixture facts."""

    fixture = dict(fixture_projection or {})
    mode = _coerce_enum(FollowupMode, fixture.get("mode"), FollowupMode.BALANCED)
    budget_before = BudgetSnapshot.from_mapping(fixture.get("budget_ledger"))
    components = _components(fixture.get("components"))
    prior_attempts = _prior_attempts(fixture.get("prior_failed_followup_attempts"))
    gaps = tuple(
        _gap_from_fixture(item, index=index)
        for index, item in enumerate(_sequence_of_mappings(fixture.get("gaps")), start=1)
    )
    if not gaps:
        gaps = tuple(_gaps_from_obligations(fixture.get("source_obligations")))

    recommendations: list[FollowupRecommendation] = []
    authorizations: list[FollowupAuthorizationCandidate] = []
    budgets: list[BudgetDecision] = []
    stops: list[StopDecision] = []
    caveats: list[CaveatRefuseDecision] = []
    hops: list[ReasoningHop] = []
    remaining = budget_before

    for index, gap in enumerate(gaps, start=1):
        hop_type = _hop_for_gap(gap, mode)
        hops.append(
            ReasoningHop(
                hop_id=f"hop.{index:03d}",
                hop_type=hop_type,
                gap_id=gap.gap_id,
                mode=mode,
                purpose=_hop_purpose(gap, hop_type),
                may_request_followup=hop_type
                is not ReasoningHopType.MICRO_VERIFICATION,
                inspection_refs=(
                    gap.component_id,
                    gap.source_obligation_id,
                    *gap.requirement_ids,
                ),
                stop_conditions=(
                    "budget_exhausted",
                    "repeated_failed_recovery",
                    "decorative_search_blocked",
                ),
            )
        )
        job_kind = _provider_job_for_gap(gap)
        debit = _debit_for_job(job_kind, hop_type)
        decision, denial_reason, protected = _decision_for_gap(
            gap=gap,
            mode=mode,
            hop_type=hop_type,
            debit=debit,
            budget=remaining,
            components=components,
            prior_attempts=prior_attempts,
        )
        expected = _expected_custody_update(gap, job_kind)
        recommendation = FollowupRecommendation(
            recommendation_id=f"rec.{index:03d}",
            gap_id=gap.gap_id,
            gap_type=gap.gap_type,
            decision=(
                FollowupDecision.RECOMMEND
                if decision is FollowupDecision.AUTHORIZE_CANDIDATE
                else decision
            ),
            hop_type=hop_type,
            component_id=gap.component_id,
            source_obligation_id=gap.source_obligation_id,
            requirement_ids=gap.requirement_ids,
            provider_job_kind=job_kind,
            query_intent=_query_intent(gap, job_kind),
            expected_custody_update=expected,
            budget_requested=debit,
            fallback_posture=_fallback_for_gap(gap, mode),
            bridge_only_provider_output=gap.bridge_only_provider_output_present,
            reason=denial_reason
            or "concrete gap has bounded provider-job recommendation",
        )
        recommendations.append(recommendation)

        budget_after = _subtract_budget(remaining, debit)
        approve = decision is FollowupDecision.AUTHORIZE_CANDIDATE
        budgets.append(
            BudgetDecision(
                budget_decision_id=f"budget.decision.{index:03d}",
                mode=mode,
                decision=decision if not approve else FollowupDecision.AUTHORIZE_CANDIDATE,
                budget_before=remaining,
                debit=debit,
                budget_after=budget_after if approve else remaining,
                starvation_check_passed=not protected,
                protected_components=tuple(protected),
                reason=denial_reason
                or "budget debit preserves mode and component minimums",
            )
        )
        if approve:
            authorizations.append(
                FollowupAuthorizationCandidate(
                    authorization_id=f"auth.candidate.{index:03d}",
                    recommendation_id=recommendation.recommendation_id,
                    decision=FollowupDecision.AUTHORIZE_CANDIDATE,
                    mode=mode,
                    hop_type=hop_type,
                    provider_job_kind=job_kind,
                    component_id=gap.component_id,
                    source_obligation_id=gap.source_obligation_id,
                    requirement_ids=gap.requirement_ids,
                    budget_debit=debit,
                    expected_evidence_ledger_custody_update=expected,
                    fallback_stop_posture=_fallback_for_gap(gap, mode),
                    fallback_caveat_refuse_posture=StopPosture.INSUFFICIENT_EVIDENCE,
                    retry_allowed=False,
                    bridge_only_provider_output=gap.bridge_only_provider_output_present,
                    rationale="passive candidate requires a future RunAuthority seal",
                )
            )
            remaining = budget_after
        else:
            posture = _fallback_for_gap(gap, mode)
            stops.append(
                StopDecision(
                    stop_id=f"stop.{index:03d}",
                    decision=_stop_decision_for_denial(decision),
                    stop_reason=denial_reason or decision.value,
                    component_id=gap.component_id,
                    source_obligation_id=gap.source_obligation_id,
                    final_answer_posture=posture,
                    mandatory_caveats=(
                        "follow_up_not_authorized_within_selected_mode",
                    ),
                    prohibited_upgrades=(
                        "do_not_upgrade_missing_or_bridge_only_evidence",
                        "do_not_treat_followup_candidate_as_executed_search",
                    ),
                )
            )
            caveats.append(
                CaveatRefuseDecision(
                    decision_id=f"caveat.{index:03d}",
                    decision=(
                        FollowupDecision.REFUSE
                        if posture is StopPosture.REFUSE_OR_BLOCK
                        else FollowupDecision.CAVEAT
                    ),
                    reason=denial_reason or decision.value,
                    safe_output_allowed=posture is not StopPosture.REFUSE_OR_BLOCK,
                    allowed_posture=posture,
                    blocked_posture="unsupported_final_claim_upgrade",
                    mandatory_language_intent=(
                        "Expose the unresolved source obligation without "
                        "claiming follow-up search ran."
                    ),
                )
            )

    handoff = _sufficiency_handoff(fixture, gaps=gaps)
    audit = _deep_audit(fixture, mode=mode, gaps=gaps)
    summary = _summary(gaps, authorizations, stops)
    return FollowupDeliberationCheckpoint(
        checkpoint_id=clean_token(fixture.get("checkpoint_id"))
        or f"checkpoint:{stable_hash(fixture)[:12]}",
        run_id=clean_token(fixture.get("run_id")) or "run.fixture",
        mode=mode,
        gap_assessments=gaps,
        reasoning_hops=tuple(hops),
        followup_recommendations=tuple(recommendations),
        followup_authorization_candidates=tuple(authorizations),
        budget_decisions=tuple(budgets),
        stop_decisions=tuple(stops),
        caveat_refuse_decisions=tuple(caveats),
        sufficiency_handoff=handoff,
        deep_assumption_audit=audit,
        input_state_refs=safe_json(fixture.get("input_state_refs") or {}),
        human_review_summary=summary,
    )


def _gap_from_fixture(payload: Mapping[str, Any], *, index: int) -> GapAssessment:
    gap_type = _coerce_enum(GapType, payload.get("gap_type"), GapType.SOURCE_CLASS_GAP)
    hop = _coerce_enum(
        ReasoningHopType,
        payload.get("recommended_hop_type") or payload.get("hop_type"),
        _default_hop(gap_type),
    )
    return GapAssessment(
        gap_id=clean_token(payload.get("gap_id")) or f"gap.{index:03d}",
        gap_type=gap_type,
        component_id=clean_token(payload.get("component_id")) or "component_unknown",
        source_obligation_id=clean_token(payload.get("source_obligation_id"))
        or "obligation_unknown",
        requirement_ids=_text_tuple(payload.get("requirement_ids")),
        severity=clean_token(payload.get("severity")) or "central_required",
        evidence_indicators=_text_tuple(payload.get("evidence_indicators"), limit=260),
        recommended_hop_type=hop,
        repairability=clean_token(payload.get("repairability"))
        or "repairable_with_targeted_job",
        balanced_eligible=bool(payload.get("balanced_eligible", True)),
        deep_eligible=bool(payload.get("deep_eligible", True)),
        deep_only_reconciliation=bool(
            payload.get("deep_only_reconciliation")
            or gap_type
            in {
                GapType.CONFLICT_RECONCILIATION_GAP,
                GapType.CONTRACT_SHAPE_GAP,
            }
        ),
        bridge_only_provider_output_present=bool(
            payload.get("bridge_only_provider_output_present")
        ),
        non_repair_reason=clean_text(payload.get("non_repair_reason"), limit=240),
    )


def _gaps_from_obligations(value: Any) -> tuple[GapAssessment, ...]:
    gaps: list[GapAssessment] = []
    for index, obligation in enumerate(_sequence_of_mappings(value), start=1):
        status = clean_token(obligation.get("status")) or "missing"
        if status in {"satisfied", "resolved"}:
            continue
        kind = clean_token(obligation.get("kind")) or "source_class"
        gap_type = _gap_type_for_obligation(kind)
        gaps.append(
            GapAssessment(
                gap_id=f"gap.{index:03d}",
                gap_type=gap_type,
                component_id=clean_token(obligation.get("component_id"))
                or "component_unknown",
                source_obligation_id=clean_token(obligation.get("obligation_id"))
                or "obligation_unknown",
                requirement_ids=_text_tuple(obligation.get("requirement_ids")),
                evidence_indicators=(f"{status}_source_obligation",),
                recommended_hop_type=_default_hop(gap_type),
            )
        )
    return tuple(gaps)


def _gap_type_for_obligation(kind: str) -> GapType:
    mapping = {
        "official_current": GapType.OFFICIAL_CURRENT_GAP,
        "legal_current_primary": GapType.LEGAL_CURRENT_PRIMARY_GAP,
        "legal_primary": GapType.LEGAL_CURRENT_PRIMARY_GAP,
        "canonical_documentation": GapType.CANONICAL_DOC_GAP,
        "canonical_docs": GapType.CANONICAL_DOC_GAP,
        "source_bound_numeric": GapType.SOURCE_BOUND_NUMERIC_GAP,
        "date_bound_currentness": GapType.CURRENTNESS_GAP,
        "conflict_resolution": GapType.CONFLICT_RECONCILIATION_GAP,
    }
    return mapping.get(kind, GapType.SOURCE_CLASS_GAP)


def _default_hop(gap_type: GapType) -> ReasoningHopType:
    if gap_type in {
        GapType.CONFLICT_RECONCILIATION_GAP,
        GapType.CONTRACT_SHAPE_GAP,
    }:
        return ReasoningHopType.MACRO_RUN_DIAGNOSIS
    if gap_type is GapType.CITATION_FINAL_ANSWER_POSTURE_GAP:
        return ReasoningHopType.MICRO_VERIFICATION
    return ReasoningHopType.MESO_TARGETED_REPAIR


def _hop_for_gap(gap: GapAssessment, mode: FollowupMode) -> ReasoningHopType:
    if mode is FollowupMode.BALANCED and gap.deep_only_reconciliation:
        return ReasoningHopType.MACRO_RUN_DIAGNOSIS
    return gap.recommended_hop_type


def _hop_purpose(gap: GapAssessment, hop_type: ReasoningHopType) -> str:
    if hop_type is ReasoningHopType.MACRO_RUN_DIAGNOSIS:
        return f"Diagnose bounded Deep-only topology for {gap.gap_type.value}"
    if hop_type is ReasoningHopType.MICRO_VERIFICATION:
        return f"Verify custody/final-answer posture for {gap.gap_type.value}"
    return f"Recommend targeted repair for {gap.gap_type.value}"


def _provider_job_for_gap(gap: GapAssessment) -> ProviderJobKind:
    mapping = {
        GapType.COMPONENT_COVERAGE_GAP: ProviderJobKind.DIRECT_CANDIDATE_SEARCH,
        GapType.SOURCE_CLASS_GAP: ProviderJobKind.DIRECT_CANDIDATE_SEARCH,
        GapType.OFFICIAL_CURRENT_GAP: ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION,
        GapType.LEGAL_CURRENT_PRIMARY_GAP: ProviderJobKind.LEGAL_CURRENT_PRIMARY_ACQUISITION,
        GapType.CANONICAL_DOC_GAP: ProviderJobKind.CANONICAL_DOC_ACQUISITION,
        GapType.SOURCE_BOUND_NUMERIC_GAP: (
            ProviderJobKind.SOURCE_BOUND_NUMERIC_EXTRACTION_CALCULATION_SUPPORT
        ),
        GapType.CURRENTNESS_GAP: ProviderJobKind.CONFLICT_CURRENTNESS_CHECK,
        GapType.CONFLICT_RECONCILIATION_GAP: ProviderJobKind.RECONCILIATION_SUPPORT,
        GapType.ENTITY_AMBIGUITY_GAP: ProviderJobKind.SCOUT_DISAMBIGUATION,
        GapType.WEAK_CORPUS_GAP: ProviderJobKind.SEMANTIC_RECALL,
        GapType.CITATION_FINAL_ANSWER_POSTURE_GAP: ProviderJobKind.FETCH_READ_EXTRACT,
        GapType.CONTRACT_SHAPE_GAP: ProviderJobKind.RECONCILIATION_SUPPORT,
    }
    return mapping[gap.gap_type]


def _debit_for_job(
    job_kind: ProviderJobKind,
    hop_type: ReasoningHopType,
) -> BudgetDebit:
    if hop_type is ReasoningHopType.MACRO_RUN_DIAGNOSIS:
        return BudgetDebit(
            cost_points=3,
            provider_calls=1,
            fetches_reserved=1,
            read_units_reserved=1,
            followup_rounds=1,
            macro_hops=1,
            budget_bucket="deep_reconciliation",
        )
    if job_kind is ProviderJobKind.FETCH_READ_EXTRACT:
        return BudgetDebit(
            cost_points=1,
            fetches_reserved=1,
            read_units_reserved=1,
            followup_rounds=1,
            meso_authorizations=1,
            budget_bucket="fetch_read_repair",
        )
    return BudgetDebit(
        cost_points=2,
        provider_calls=1,
        fetches_reserved=1,
        read_units_reserved=1,
        followup_rounds=1,
        meso_authorizations=1,
        budget_bucket="targeted_repair",
    )


def _decision_for_gap(
    *,
    gap: GapAssessment,
    mode: FollowupMode,
    hop_type: ReasoningHopType,
    debit: BudgetDebit,
    budget: BudgetSnapshot,
    components: Mapping[str, Mapping[str, Any]],
    prior_attempts: Mapping[tuple[str, str], int],
) -> tuple[FollowupDecision, str | None, tuple[str, ...]]:
    if gap.gap_type is GapType.CITATION_FINAL_ANSWER_POSTURE_GAP and clean_token(
        gap.repairability
    ) == "decorative_only":
        return (
            FollowupDecision.DECORATIVE_SEARCH_BLOCKED,
            "decorative_search_blocked",
            (),
        )
    if (
        mode is FollowupMode.BALANCED
        and hop_type is ReasoningHopType.MACRO_RUN_DIAGNOSIS
    ):
        return (
            FollowupDecision.NEEDS_DEEP,
            "balanced_cannot_authorize_macro_run_diagnosis",
            (),
        )
    if mode is FollowupMode.BALANCED and gap.deep_only_reconciliation:
        return (
            FollowupDecision.NEEDS_DEEP,
            "balanced_cannot_authorize_deep_only_reconciliation",
            (),
        )
    key = (gap.gap_id, gap.source_obligation_id)
    if prior_attempts.get(key, 0) >= (2 if mode is FollowupMode.DEEP else 1):
        return (
            FollowupDecision.STOP,
            "repeated_failed_recovery",
            (),
        )
    protected = _starved_components_after_debit(
        gap=gap,
        budget=budget,
        debit=debit,
        components=components,
    )
    if protected:
        return (
            FollowupDecision.INSUFFICIENT_BUDGET,
            "budget_debit_would_starve_unserved_central_component",
            protected,
        )
    if not _budget_covers(budget, debit):
        return (
            FollowupDecision.INSUFFICIENT_BUDGET,
            "multidimensional_budget_exhausted",
            (),
        )
    if (
        gap.gap_type is GapType.SOURCE_BOUND_NUMERIC_GAP
        and any("unresolved" in item for item in gap.evidence_indicators)
    ):
        return (
            FollowupDecision.STOP,
            "source_bound_numeric_unresolved_remains_unknown",
            (),
        )
    return FollowupDecision.AUTHORIZE_CANDIDATE, None, ()


def _expected_custody_update(
    gap: GapAssessment,
    job_kind: ProviderJobKind,
) -> EvidenceLedgerCustodyUpdate:
    classes = {
        GapType.OFFICIAL_CURRENT_GAP: ("official_government", "official_current_rules"),
        GapType.LEGAL_CURRENT_PRIMARY_GAP: ("primary_legal", "legal_or_regulatory_text"),
        GapType.CANONICAL_DOC_GAP: ("canonical", "primary_source_documents"),
        GapType.SOURCE_BOUND_NUMERIC_GAP: ("sourced_numeric_values",),
        GapType.CURRENTNESS_GAP: ("current_primary_or_official",),
        GapType.CONFLICT_RECONCILIATION_GAP: ("source_family_map",),
        GapType.CITATION_FINAL_ANSWER_POSTURE_GAP: ("answer_bearing_extract",),
    }.get(gap.gap_type, ("answer_bearing_candidate",))
    required = (
        "candidate_identity",
        "source_class",
        "currentness_signal",
        "readable_answer_bearing_extract",
        "requirement_link",
    )
    if job_kind is ProviderJobKind.FETCH_READ_EXTRACT:
        required = (
            "readable_answer_bearing_extract",
            "metadata_or_date_signal",
            "requirement_link",
        )
    return EvidenceLedgerCustodyUpdate(
        custody_update_expected=required,
        source_classes=classes,
        currentness_required=gap.gap_type
        in {
            GapType.OFFICIAL_CURRENT_GAP,
            GapType.LEGAL_CURRENT_PRIMARY_GAP,
            GapType.CURRENTNESS_GAP,
        },
        answer_bearing_required=True,
    )


def _query_intent(gap: GapAssessment, job_kind: ProviderJobKind) -> str:
    return (
        f"Find a bounded {job_kind.value} result for {gap.component_id} "
        f"and {gap.source_obligation_id}; admit only through EvidenceLedger."
    )


def _fallback_for_gap(gap: GapAssessment, mode: FollowupMode) -> StopPosture:
    if mode is FollowupMode.BALANCED and gap.deep_only_reconciliation:
        return StopPosture.NEEDS_DEEP
    if gap.gap_type is GapType.LEGAL_CURRENT_PRIMARY_GAP:
        return StopPosture.REFUSE_OR_BLOCK
    if gap.gap_type in {
        GapType.SOURCE_BOUND_NUMERIC_GAP,
        GapType.CONFLICT_RECONCILIATION_GAP,
    }:
        return StopPosture.INSUFFICIENT_EVIDENCE
    return StopPosture.ANSWER_WITH_CAVEATS


def _stop_decision_for_denial(decision: FollowupDecision) -> FollowupDecision:
    if decision is FollowupDecision.NEEDS_DEEP:
        return FollowupDecision.NEEDS_DEEP
    if decision is FollowupDecision.INSUFFICIENT_BUDGET:
        return FollowupDecision.INSUFFICIENT_BUDGET
    if decision is FollowupDecision.DECORATIVE_SEARCH_BLOCKED:
        return FollowupDecision.DECORATIVE_SEARCH_BLOCKED
    return FollowupDecision.STOP


def _sufficiency_handoff(
    fixture: Mapping[str, Any],
    *,
    gaps: Sequence[GapAssessment],
) -> SufficiencyHandoff:
    raw = dict(fixture.get("sufficiency_handoff") or {})
    satisfied = _text_tuple(raw.get("satisfied_obligations"))
    partial = list(_text_tuple(raw.get("partial_obligations")))
    missing = list(_text_tuple(raw.get("missing_obligations")))
    numeric_unknowns = list(_text_tuple(raw.get("source_bound_numeric_unknowns")))
    numeric_resolutions = list(_text_tuple(raw.get("source_bound_numeric_resolutions")))
    for gap in gaps:
        obligation_id = clean_token(gap.source_obligation_id)
        if not obligation_id:
            continue
        if gap.gap_type is GapType.SOURCE_BOUND_NUMERIC_GAP:
            if any("unresolved" in item for item in gap.evidence_indicators):
                if obligation_id not in numeric_unknowns:
                    numeric_unknowns.append(obligation_id)
            elif any("resolved" in item for item in gap.evidence_indicators):
                if obligation_id not in numeric_resolutions:
                    numeric_resolutions.append(obligation_id)
            elif obligation_id not in numeric_unknowns:
                numeric_unknowns.append(obligation_id)
        elif obligation_id not in satisfied and obligation_id not in missing:
            missing.append(obligation_id)
    return SufficiencyHandoff(
        handoff_id=clean_token(raw.get("handoff_id")) or "sufficiency.handoff.001",
        ready_for_sufficiency_judgment=bool(
            raw.get("ready_for_sufficiency_judgment", True)
        ),
        satisfied_obligations=satisfied,
        partial_obligations=tuple(partial),
        missing_obligations=tuple(missing),
        unresolved_conflicts=_text_tuple(raw.get("unresolved_conflicts")),
        source_bound_numeric_unknowns=tuple(numeric_unknowns),
        source_bound_numeric_resolutions=tuple(numeric_resolutions),
        recommended_final_posture=raw.get("recommended_final_posture")
        or StopPosture.ANSWER_WITH_CAVEATS.value,
        must_preserve_prohibited_upgrades=bool(
            raw.get("must_preserve_prohibited_upgrades", True)
        ),
        bridge_only_provider_outputs_satisfy_final_evidence=bool(
            raw.get("bridge_only_provider_outputs_satisfy_final_evidence", False)
        ),
    )


def _deep_audit(
    fixture: Mapping[str, Any],
    *,
    mode: FollowupMode,
    gaps: Sequence[GapAssessment],
) -> DeepAssumptionAudit | None:
    if mode is not FollowupMode.DEEP:
        return None
    raw = dict(fixture.get("deep_assumption_audit") or {})
    assumptions = tuple(_sequence_of_mappings(raw.get("assumptions")))
    if not assumptions:
        assumptions = (
            {
                "assumption_id": "assumption.scope.001",
                "statement": "Fixture scope, jurisdiction, and time window are the intended answer frame.",
                "support": "Sanitized fixture projection.",
                "fragility": "medium",
                "what_would_change_answer": "Different jurisdiction, version, or effective date.",
            },
        )
    conflict_summary = tuple(_sequence_of_mappings(raw.get("conflict_summary")))
    if not conflict_summary and any(
        gap.gap_type is GapType.CONFLICT_RECONCILIATION_GAP for gap in gaps
    ):
        conflict_summary = (
            {
                "conflict_id": "conflict.fixture.001",
                "type": "currentness_or_scope",
                "status": "bounded_reconciliation_candidate_only",
                "final_posture_effect": "caveat_required_if_unresolved",
            },
        )
    return DeepAssumptionAudit(
        audit_id=clean_token(raw.get("audit_id")) or "audit.deep.001",
        mode=mode,
        assumptions=assumptions,
        source_family_gaps=tuple(_sequence_of_mappings(raw.get("source_family_gaps"))),
        conflict_summary=conflict_summary,
        sensitivity=tuple(_sequence_of_mappings(raw.get("sensitivity"))),
        followup_allowed=bool(raw.get("followup_allowed", False)),
        reason=clean_text(raw.get("reason"), limit=300)
        or "Deep audit is passive in AG-96I1",
    )


def _summary(
    gaps: Sequence[GapAssessment],
    authorizations: Sequence[FollowupAuthorizationCandidate],
    stops: Sequence[StopDecision],
) -> tuple[str, ...]:
    return (
        f"typed_gap_count={len(gaps)}",
        f"authorization_candidate_count={len(authorizations)}",
        f"stop_decision_count={len(stops)}",
        "passive_only_no_search_executed",
    )


def _components(value: Any) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for item in _sequence_of_mappings(value):
        component_id = clean_token(item.get("component_id"))
        if component_id:
            out[component_id] = safe_json(item)
    return out


def _prior_attempts(value: Any) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for item in _sequence_of_mappings(value):
        gap_id = clean_token(item.get("gap_id")) or ""
        obligation_id = clean_token(item.get("source_obligation_id")) or ""
        if not gap_id or not obligation_id:
            continue
        out[(gap_id, obligation_id)] = out.get((gap_id, obligation_id), 0) + 1
    return out


def _starved_components_after_debit(
    *,
    gap: GapAssessment,
    budget: BudgetSnapshot,
    debit: BudgetDebit,
    components: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    after = _subtract_budget(budget, debit)
    protected: list[str] = []
    for component_id, component in components.items():
        if component_id == clean_token(gap.component_id):
            continue
        if not bool(component.get("central", True)):
            continue
        if bool(component.get("served_minimum", False)):
            continue
        min_provider = _int(component.get("minimum_provider_calls", 1))
        min_fetch = _int(component.get("minimum_fetches", 1))
        min_read = _int(component.get("minimum_read_units", 1))
        if (
            after.provider_calls_remaining < min_provider
            or after.fetches_remaining < min_fetch
            or after.read_units_remaining < min_read
        ):
            protected.append(component_id)
    return tuple(protected)


def _budget_covers(budget: BudgetSnapshot, debit: BudgetDebit) -> bool:
    return (
        budget.cost_points_remaining >= debit.cost_points
        and budget.provider_calls_remaining >= debit.provider_calls
        and budget.fetches_remaining >= debit.fetches_reserved
        and budget.read_units_remaining >= debit.read_units_reserved
        and budget.followup_rounds_remaining >= debit.followup_rounds
        and budget.meso_authorizations_remaining >= debit.meso_authorizations
        and budget.macro_hops_remaining >= debit.macro_hops
    )


def _subtract_budget(budget: BudgetSnapshot, debit: BudgetDebit) -> BudgetSnapshot:
    return BudgetSnapshot(
        cost_points_remaining=max(0, budget.cost_points_remaining - debit.cost_points),
        provider_calls_remaining=max(
            0, budget.provider_calls_remaining - debit.provider_calls
        ),
        fetches_remaining=max(0, budget.fetches_remaining - debit.fetches_reserved),
        read_units_remaining=max(
            0, budget.read_units_remaining - debit.read_units_reserved
        ),
        followup_rounds_remaining=max(
            0, budget.followup_rounds_remaining - debit.followup_rounds
        ),
        meso_authorizations_remaining=max(
            0,
            budget.meso_authorizations_remaining - debit.meso_authorizations,
        ),
        macro_hops_remaining=max(0, budget.macro_hops_remaining - debit.macro_hops),
    )


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None or isinstance(value, str | bytes):
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "FOLLOWUP_DELIBERATION_SCHEMA_VERSION",
    "FOLLOWUP_DELIBERATION_TRACE_KEY",
    "BudgetDebit",
    "BudgetDecision",
    "BudgetSnapshot",
    "CaveatRefuseDecision",
    "DeepAssumptionAudit",
    "EvidenceLedgerCustodyUpdate",
    "FollowupAuthorizationCandidate",
    "FollowupDecision",
    "FollowupDeliberationCheckpoint",
    "FollowupMode",
    "FollowupRecommendation",
    "GapAssessment",
    "GapType",
    "ProviderJobKind",
    "ReasoningHop",
    "ReasoningHopType",
    "StopDecision",
    "StopPosture",
    "SufficiencyHandoff",
    "build_followup_deliberation_checkpoint",
    "clean_text",
    "clean_token",
    "safe_json",
    "stable_hash",
]
