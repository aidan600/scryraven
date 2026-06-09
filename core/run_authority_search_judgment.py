"""RunAuthority iterative search judgment model for AG-92B.

The judgment is canonical RunKernel state. It decides continuation, recovery,
redundancy blocking, and insufficient-stop posture against an active
RunAuthority contract plus EvidenceLedger projection without executing search.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION = (
    "run_authority_search_judgment_ag92b_v1"
)
RUN_AUTHORITY_SEARCH_JUDGMENT_TRACE_KEY = "run_authority_search_judgment"

_MAX_LIST_ITEMS = 80
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


class SearchJudgmentMode(str, Enum):
    DETERMINISTIC = "deterministic"
    SMART_MODEL_ADAPTED = "smart_model_adapted"
    REPAIRED = "repaired"
    FALLBACK = "fallback"


class RunSearchJudgmentDecision(str, Enum):
    STOP_SATISFIED = "stop_satisfied"
    CONTINUE_TARGETED_SEARCH = "continue_targeted_search"
    RECOVER_MISSING_OFFICIAL_CURRENT = "recover_missing_official_current"
    RECOVER_MISSING_LEGAL_PRIMARY = "recover_missing_legal_primary"
    RECOVER_MISSING_CANONICAL = "recover_missing_canonical"
    RECOVER_MISSING_SOURCE_BOUND_NUMERIC = "recover_missing_source_bound_numeric"
    ESCALATE_EXISTING_PROVIDER_OR_DEPTH = "escalate_existing_provider_or_depth"
    BLOCK_REDUNDANT_QUERY = "block_redundant_query"
    STOP_INSUFFICIENT = "stop_insufficient"
    DEFER_TO_EXISTING_LEGACY_COMPATIBILITY = "defer_to_existing_legacy_compatibility"


class SearchJudgmentClassification(str, Enum):
    CONTRACT_SATISFIED = "contract_satisfied"
    ACTIVE_REQUIRED_GAP = "active_required_gap"
    LOWER_TIER_LEAD_ONLY = "lower_tier_lead_only"
    STALE_OR_OFF_TOPIC_ONLY = "stale_or_off_topic_only"
    USEFUL_LEAD_NEEDS_TARGETED_RECOVERY = "useful_lead_needs_targeted_recovery"
    REDUNDANT_QUERY_BLOCKED = "redundant_query_blocked"
    NEW_SOURCE_CLASS_TARGET_ALLOWED = "new_source_class_target_allowed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INSUFFICIENT_BUT_ANSWERABLE_WITH_CAVEATS = (
        "insufficient_but_answerable_with_caveats"
    )
    HELPER_ASSESSMENT_REJECTED = "helper_assessment_rejected"
    HELPER_ASSESSMENT_PROMOTED = "helper_assessment_promoted"


class SearchJudgmentValidationStatus(str, Enum):
    VALID = "valid"
    REPAIRED = "repaired"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


def clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def clean_token(value: Any, *, limit: int = 160) -> str | None:
    return clean_text(value, limit=limit)


def safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            clean_key = clean_token(key, limit=100)
            if not clean_key:
                continue
            key_folded = clean_key.casefold()
            if key_folded in _SENSITIVE_KEYS or key_folded.startswith("raw_"):
                out[clean_key] = "[redacted]"
            else:
                out[clean_key] = safe_json(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        ordered = list(value)
        if isinstance(value, (set, frozenset)):
            ordered = sorted(ordered, key=str)
        return [safe_json(item, depth=depth + 1) for item in ordered[:_MAX_LIST_ITEMS]]
    return clean_text(value, limit=300)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(repr(safe_json(value)).encode("utf-8")).hexdigest()


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = safe_json(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        candidates = list(value)
    else:
        candidates = [value]
    out: list[str] = []
    for item in candidates:
        token = clean_token(item, limit=160)
        if token and token not in out:
            out.append(token)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class SearchGapAssessment:
    requirement_id: str
    requirement_kind: str
    required_source_class: str | None = None
    required_source_tier: str | None = None
    required_currentness: str | None = None
    status: str = "unsatisfied"
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "requirement_id": clean_token(self.requirement_id),
                "requirement_kind": clean_token(self.requirement_kind),
                "required_source_class": clean_token(self.required_source_class),
                "required_source_tier": clean_token(self.required_source_tier),
                "required_currentness": clean_token(self.required_currentness),
                "status": clean_token(self.status),
                "reason": clean_text(self.reason, limit=220),
            }.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SearchGapAssessment":
        return cls(
            requirement_id=str(payload.get("requirement_id") or ""),
            requirement_kind=str(payload.get("requirement_kind") or "general"),
            required_source_class=clean_token(payload.get("required_source_class")),
            required_source_tier=clean_token(payload.get("required_source_tier")),
            required_currentness=clean_token(payload.get("required_currentness")),
            status=clean_token(payload.get("status")) or "unsatisfied",
            reason=clean_text(payload.get("reason"), limit=220),
        )


@dataclass(frozen=True, slots=True)
class SearchContinuationProposal:
    proposed_query_signature: str | None = None
    proposed_query_preview: str | None = None
    query_role: str | None = None
    target_source_classes: tuple[str, ...] = ()
    targets_new_gap: bool = False
    allowed: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "proposed_query_signature": clean_token(
                    self.proposed_query_signature
                ),
                "proposed_query_preview": clean_text(
                    self.proposed_query_preview,
                    limit=220,
                ),
                "query_role": clean_token(self.query_role),
                "target_source_classes": list(self.target_source_classes),
                "targets_new_gap": bool(self.targets_new_gap),
                "allowed": bool(self.allowed),
                "reason": clean_text(self.reason, limit=220),
            }.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SearchContinuationProposal":
        return cls(
            proposed_query_signature=clean_token(
                payload.get("proposed_query_signature")
                or payload.get("query_signature")
            ),
            proposed_query_preview=clean_text(
                payload.get("proposed_query_preview")
                or payload.get("query_preview"),
                limit=220,
            ),
            query_role=clean_token(payload.get("query_role")),
            target_source_classes=_string_tuple(payload.get("target_source_classes")),
            targets_new_gap=bool(payload.get("targets_new_gap")),
            allowed=bool(payload.get("allowed")),
            reason=clean_text(payload.get("reason"), limit=220),
        )


@dataclass(frozen=True, slots=True)
class SearchRedundancyAssessment:
    proposed_query_signature: str | None = None
    duplicate_of: str | None = None
    targets_new_gap: bool = False
    target_source_classes: tuple[str, ...] = ()
    redundant: bool = False
    blocked: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "proposed_query_signature": clean_token(
                    self.proposed_query_signature
                ),
                "duplicate_of": clean_token(self.duplicate_of),
                "targets_new_gap": bool(self.targets_new_gap),
                "target_source_classes": list(self.target_source_classes),
                "redundant": bool(self.redundant),
                "blocked": bool(self.blocked),
                "reason": clean_text(self.reason, limit=220),
            }.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SearchRedundancyAssessment":
        return cls(
            proposed_query_signature=clean_token(
                payload.get("proposed_query_signature")
                or payload.get("query_signature")
            ),
            duplicate_of=clean_token(payload.get("duplicate_of")),
            targets_new_gap=bool(payload.get("targets_new_gap")),
            target_source_classes=_string_tuple(payload.get("target_source_classes")),
            redundant=bool(payload.get("redundant")),
            blocked=bool(payload.get("blocked")),
            reason=clean_text(payload.get("reason"), limit=220),
        )


@dataclass(frozen=True, slots=True)
class SearchSatisfactionAssessment:
    contract_satisfied: bool = False
    satisfied_requirement_ids: tuple[str, ...] = ()
    unsatisfied_requirement_ids: tuple[str, ...] = ()
    lower_tier_only_requirement_ids: tuple[str, ...] = ()
    stale_or_off_topic_requirement_ids: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "contract_satisfied": bool(self.contract_satisfied),
                "satisfied_requirement_ids": list(self.satisfied_requirement_ids),
                "unsatisfied_requirement_ids": list(self.unsatisfied_requirement_ids),
                "lower_tier_only_requirement_ids": list(
                    self.lower_tier_only_requirement_ids
                ),
                "stale_or_off_topic_requirement_ids": list(
                    self.stale_or_off_topic_requirement_ids
                ),
                "reason": clean_text(self.reason, limit=260),
            }.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SearchSatisfactionAssessment":
        return cls(
            contract_satisfied=bool(payload.get("contract_satisfied")),
            satisfied_requirement_ids=_string_tuple(
                payload.get("satisfied_requirement_ids")
            ),
            unsatisfied_requirement_ids=_string_tuple(
                payload.get("unsatisfied_requirement_ids")
            ),
            lower_tier_only_requirement_ids=_string_tuple(
                payload.get("lower_tier_only_requirement_ids")
            ),
            stale_or_off_topic_requirement_ids=_string_tuple(
                payload.get("stale_or_off_topic_requirement_ids")
            ),
            reason=clean_text(payload.get("reason"), limit=260),
        )


@dataclass(frozen=True, slots=True)
class SearchJudgmentValidationResult:
    status: SearchJudgmentValidationStatus | str
    reasons: tuple[str, ...] = ()
    fallback_used: bool = False
    model_attempted: bool = False
    deterministic_decision: str | None = None
    prompt_hash: str | None = None
    prompt_length: int = 0
    provider: str | None = None
    model: str | None = None
    effort: str | None = None
    use_reasoning: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            SearchJudgmentValidationStatus(self.status),
        )
        object.__setattr__(self, "reasons", _string_tuple(self.reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reasons": list(self.reasons),
            "fallback_used": bool(self.fallback_used),
            "model_attempted": bool(self.model_attempted),
            "deterministic_decision": clean_token(self.deterministic_decision),
            "prompt_hash": clean_token(self.prompt_hash),
            "prompt_length": int(self.prompt_length or 0),
            "provider": clean_token(self.provider),
            "model": clean_token(self.model),
            "effort": clean_token(self.effort),
            "use_reasoning": self.use_reasoning,
        }


@dataclass(frozen=True, slots=True)
class RunSearchJudgmentInput:
    """Compact sanitized facts consumed by the search-judgment executor."""

    contract_projection: Mapping[str, Any]
    evidence_ledger_projection: Mapping[str, Any]
    query_facts: Mapping[str, Any] = field(default_factory=dict)
    retrieval_observations: Mapping[str, Any] = field(default_factory=dict)
    helper_proposals: Mapping[str, Any] = field(default_factory=dict)
    budget: Mapping[str, Any] = field(default_factory=dict)

    def to_model_payload(self) -> dict[str, Any]:
        contract = _safe_mapping(self.contract_projection)
        ledger = _safe_mapping(self.evidence_ledger_projection)
        return {
            "schema_version": RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION,
            "contract_ref": {
                "contract_id": contract.get("contract_id"),
                "selected_template_ids": contract.get("selected_template_ids", []),
                "source_requirement_summary": contract.get(
                    "source_requirement_summary",
                    [],
                ),
                "source_requirements": contract.get("source_requirements", []),
                "final_posture_policy": contract.get("final_posture_policy", {}),
                "recovery_policy": contract.get("recovery_policy", {}),
            },
            "evidence_ledger_ref": {
                "candidate_count": ledger.get("candidate_count", 0),
                "requirement_count": ledger.get("requirement_count", 0),
                "source_requirements": ledger.get("source_requirements", []),
                "requirement_summaries": ledger.get("requirement_summaries", []),
                "custody_gaps": ledger.get("custody_gaps", []),
                "final_evidence_compatibility_gaps": ledger.get(
                    "final_evidence_compatibility_gaps",
                    [],
                ),
                "candidate_records": ledger.get("candidate_records", []),
            },
            "query_ref_facts": _safe_mapping(self.query_facts),
            "retrieval_observation_facts": _safe_mapping(
                self.retrieval_observations
            ),
            "helper_proposals": _safe_mapping(self.helper_proposals),
            "budget": _safe_mapping(self.budget),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_model_payload()


@dataclass(frozen=True, slots=True)
class RunSearchJudgment:
    judgment_id: str
    decision: RunSearchJudgmentDecision | str
    mode: SearchJudgmentMode | str = SearchJudgmentMode.DETERMINISTIC
    classifications: tuple[str, ...] = ()
    contract_id: str | None = None
    selected_template_ids: tuple[str, ...] = ()
    satisfaction: SearchSatisfactionAssessment = field(
        default_factory=SearchSatisfactionAssessment
    )
    gaps: tuple[SearchGapAssessment, ...] = ()
    redundancy: SearchRedundancyAssessment = field(
        default_factory=SearchRedundancyAssessment
    )
    continuation: SearchContinuationProposal = field(
        default_factory=SearchContinuationProposal
    )
    target_source_classes: tuple[str, ...] = ()
    recommended_queries: tuple[str, ...] = ()
    helper_assessments: Mapping[str, Any] = field(default_factory=dict)
    insufficient_posture: Mapping[str, Any] = field(default_factory=dict)
    rationale: str | None = None
    validation: Mapping[str, Any] = field(default_factory=dict)
    prompt_hash: str | None = None
    prompt_length: int = 0
    model_identity: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        decision = (
            self.decision
            if isinstance(self.decision, RunSearchJudgmentDecision)
            else RunSearchJudgmentDecision(str(self.decision))
        )
        mode = (
            self.mode
            if isinstance(self.mode, SearchJudgmentMode)
            else SearchJudgmentMode(str(self.mode))
        )
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "classifications", _string_tuple(self.classifications))
        object.__setattr__(
            self,
            "selected_template_ids",
            _string_tuple(self.selected_template_ids),
        )
        object.__setattr__(
            self,
            "target_source_classes",
            _string_tuple(self.target_source_classes),
        )
        object.__setattr__(
            self,
            "recommended_queries",
            _string_tuple(self.recommended_queries),
        )
        object.__setattr__(self, "helper_assessments", _safe_mapping(self.helper_assessments))
        object.__setattr__(
            self,
            "insufficient_posture",
            _safe_mapping(self.insufficient_posture),
        )
        object.__setattr__(self, "validation", _safe_mapping(self.validation))
        object.__setattr__(self, "model_identity", _safe_mapping(self.model_identity))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RunSearchJudgment":
        raw_gaps = payload.get("gaps") or payload.get("gap_assessments") or ()
        gaps = tuple(
            SearchGapAssessment.from_mapping(item)
            for item in raw_gaps
            if isinstance(item, Mapping)
        )
        return cls(
            judgment_id=str(
                payload.get("judgment_id")
                or f"search-judgment:{stable_hash(payload)[:16]}"
            ),
            decision=payload.get("decision")
            or RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY,
            mode=payload.get("mode") or SearchJudgmentMode.SMART_MODEL_ADAPTED,
            classifications=_string_tuple(payload.get("classifications")),
            contract_id=clean_token(payload.get("contract_id")),
            selected_template_ids=_string_tuple(payload.get("selected_template_ids")),
            satisfaction=SearchSatisfactionAssessment.from_mapping(
                payload.get("satisfaction") if isinstance(payload.get("satisfaction"), Mapping) else {}
            ),
            gaps=gaps,
            redundancy=SearchRedundancyAssessment.from_mapping(
                payload.get("redundancy") if isinstance(payload.get("redundancy"), Mapping) else {}
            ),
            continuation=SearchContinuationProposal.from_mapping(
                payload.get("continuation")
                if isinstance(payload.get("continuation"), Mapping)
                else {}
            ),
            target_source_classes=_string_tuple(payload.get("target_source_classes")),
            recommended_queries=_string_tuple(payload.get("recommended_queries")),
            helper_assessments=_safe_mapping(payload.get("helper_assessments")),
            insufficient_posture=_safe_mapping(payload.get("insufficient_posture")),
            rationale=clean_text(payload.get("rationale"), limit=260),
            validation=_safe_mapping(payload.get("validation")),
            prompt_hash=clean_token(payload.get("prompt_hash")),
            prompt_length=int(payload.get("prompt_length") or 0),
            model_identity=_safe_mapping(payload.get("model_identity")),
        )

    def to_projection(self) -> dict[str, Any]:
        return safe_json(
            {
                "owner": "RunKernel.RunAuthoritySearchJudgment",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION,
                "judgment_id": self.judgment_id,
                "decision": self.decision.value,
                "mode": self.mode.value,
                "classifications": list(self.classifications),
                "contract_id": self.contract_id,
                "selected_template_ids": list(self.selected_template_ids),
                "satisfaction": self.satisfaction.to_dict(),
                "gaps": [gap.to_dict() for gap in self.gaps],
                "redundancy": self.redundancy.to_dict(),
                "continuation": self.continuation.to_dict(),
                "target_source_classes": list(self.target_source_classes),
                "recommended_queries": list(self.recommended_queries),
                "helper_assessments": dict(self.helper_assessments),
                "insufficient_posture": dict(self.insufficient_posture),
                "rationale": clean_text(self.rationale, limit=260),
                "validation": dict(self.validation),
                "prompt_hash": clean_token(self.prompt_hash),
                "prompt_length": int(self.prompt_length or 0),
                "model_identity": dict(self.model_identity),
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
        )


__all__ = [
    "RUN_AUTHORITY_SEARCH_JUDGMENT_SCHEMA_VERSION",
    "RUN_AUTHORITY_SEARCH_JUDGMENT_TRACE_KEY",
    "RunSearchJudgment",
    "RunSearchJudgmentDecision",
    "RunSearchJudgmentInput",
    "SearchContinuationProposal",
    "SearchGapAssessment",
    "SearchJudgmentClassification",
    "SearchJudgmentMode",
    "SearchJudgmentValidationResult",
    "SearchJudgmentValidationStatus",
    "SearchRedundancyAssessment",
    "SearchSatisfactionAssessment",
    "clean_text",
    "clean_token",
    "safe_json",
    "stable_hash",
]
