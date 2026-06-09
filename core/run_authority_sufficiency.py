"""RunAuthority final sufficiency judgment model for AG-92C.

The sufficiency judgment is canonical RunKernel state. It decides whether the
committed run contract is fulfilled enough for final answering from compact
contract, EvidenceLedger, search-judgment, and compatibility facts. It does not
write final prose, format citations, retrieve, route providers, or store raw
prompts/model output.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION = "run_authority_sufficiency_ag92c_v1"
RUN_AUTHORITY_SUFFICIENCY_TRACE_KEY = "run_authority_sufficiency_judgment"

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


class SufficiencyJudgmentMode(str, Enum):
    DETERMINISTIC = "deterministic"
    SMART_MODEL_ADAPTED = "smart_model_adapted"
    REPAIRED = "repaired"
    FALLBACK = "fallback"


class RunSufficiencyDecision(str, Enum):
    READY_DIRECT = "ready_direct"
    READY_WITH_CAVEATS = "ready_with_caveats"
    PARTIAL_ANSWER_AUTHORIZED = "partial_answer_authorized"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BLOCK_FINALIZATION = "block_finalization"
    RECOVERY_REQUIRED_BUT_EXHAUSTED = "recovery_required_but_exhausted"
    CONFLICT_BLOCKED = "conflict_blocked"
    INFERENCE_ONLY_WITH_LABELING = "inference_only_with_labeling"
    SOURCE_BOUND_NUMERIC_UNKNOWN = "source_bound_numeric_unknown"
    DEFER_TO_LEGACY_COMPATIBILITY = "defer_to_legacy_compatibility"


class SufficiencyPosture(str, Enum):
    DIRECT_ANSWER = "direct_answer"
    ANSWER_WITH_CAVEATS = "answer_with_caveats"
    PARTIAL_ANSWER = "partial_answer"
    INSUFFICIENT_ANSWER = "insufficient_answer"
    FAILURE_CARD = "failure_card"
    BLOCKED = "blocked"


class SufficiencyValidationStatus(str, Enum):
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


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _string_tuple(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    for item in _list(value):
        token = clean_token(item, limit=180)
        if token and token not in out:
            out.append(token)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class SufficiencyRequirementAssessment:
    requirement_id: str
    requirement_kind: str
    required_source_class: str | None = None
    required_source_tier: str | None = None
    required_currentness: str | None = None
    status: str = "missing"
    reason: str | None = None
    satisfied_candidate_ids: tuple[str, ...] = ()

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
                "reason": clean_text(self.reason, limit=260),
                "satisfied_candidate_ids": list(self.satisfied_candidate_ids),
            }.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> "SufficiencyRequirementAssessment":
        return cls(
            requirement_id=str(payload.get("requirement_id") or ""),
            requirement_kind=str(payload.get("requirement_kind") or "general"),
            required_source_class=clean_token(payload.get("required_source_class")),
            required_source_tier=clean_token(payload.get("required_source_tier")),
            required_currentness=clean_token(payload.get("required_currentness")),
            status=clean_token(payload.get("status")) or "missing",
            reason=clean_text(payload.get("reason"), limit=260),
            satisfied_candidate_ids=_string_tuple(
                payload.get("satisfied_candidate_ids")
                or payload.get("linked_candidate_ids")
            ),
        )


@dataclass(frozen=True, slots=True)
class SufficiencyValidationResult:
    status: SufficiencyValidationStatus | str
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
            SufficiencyValidationStatus(self.status),
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
class RunSufficiencyJudgmentInput:
    """Compact sanitized facts consumed by the sufficiency executor."""

    contract_projection: Mapping[str, Any]
    evidence_ledger_projection: Mapping[str, Any]
    search_judgment_projection: Mapping[str, Any] = field(default_factory=dict)
    search_judgment_history: Sequence[Mapping[str, Any]] = ()
    answer_contract_projection: Mapping[str, Any] = field(default_factory=dict)
    source_obligation_projection: Mapping[str, Any] = field(default_factory=dict)
    final_evidence_facts: Mapping[str, Any] = field(default_factory=dict)
    conflict_facts: Mapping[str, Any] = field(default_factory=dict)
    indirect_inference_facts: Mapping[str, Any] = field(default_factory=dict)
    weak_failure_facts: Mapping[str, Any] = field(default_factory=dict)
    budget: Mapping[str, Any] = field(default_factory=dict)

    def to_model_payload(self) -> dict[str, Any]:
        contract = _safe_mapping(self.contract_projection)
        ledger = _safe_mapping(self.evidence_ledger_projection)
        search = _safe_mapping(self.search_judgment_projection)
        answer_contract = _safe_mapping(self.answer_contract_projection)
        source_obligation = _safe_mapping(self.source_obligation_projection)
        history = [_safe_mapping(item) for item in self.search_judgment_history]
        return {
            "schema_version": RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION,
            "contract_ref": {
                "contract_id": contract.get("contract_id"),
                "selected_template_ids": contract.get("selected_template_ids", []),
                "source_requirements": contract.get("source_requirements", []),
                "source_requirement_summary": contract.get(
                    "source_requirement_summary",
                    [],
                ),
                "inference_policy": contract.get("inference_policy", {}),
                "conflict_policy": contract.get("conflict_policy", {}),
                "numeric_policy": contract.get("numeric_policy", {}),
                "final_posture_policy": contract.get("final_posture_policy", {}),
            },
            "evidence_ledger_ref": {
                "candidate_count": ledger.get("candidate_count", 0),
                "requirement_count": ledger.get("requirement_count", 0),
                "source_requirements": ledger.get("source_requirements", []),
                "custody_gaps": ledger.get("custody_gaps", []),
                "final_evidence_compatibility_gaps": ledger.get(
                    "final_evidence_compatibility_gaps",
                    [],
                ),
                "compatibility": ledger.get("compatibility", {}),
                "candidate_records": ledger.get("candidate_records", []),
            },
            "search_judgment_ref": {
                "decision": search.get("decision"),
                "classifications": search.get("classifications", []),
                "gaps": search.get("gaps", []),
                "target_source_classes": search.get("target_source_classes", []),
                "insufficient_posture": search.get("insufficient_posture", {}),
                "history_count": len(history),
                "history_decisions": [
                    item.get("decision") for item in history[-5:] if item.get("decision")
                ],
            },
            "answer_contract_ref": {
                "fulfilled_source_classes": answer_contract.get(
                    "fulfilled_source_classes",
                    [],
                ),
                "unfulfilled_source_classes": answer_contract.get(
                    "unfulfilled_source_classes",
                    [],
                ),
                "partial_source_classes": answer_contract.get(
                    "partial_source_classes",
                    [],
                ),
                "missing_information": answer_contract.get("missing_information", []),
                "source_bound_numeric_obligations": answer_contract.get(
                    "source_bound_numeric_obligations",
                    [],
                ),
            },
            "source_obligation_ref": source_obligation,
            "final_evidence_facts": _safe_mapping(self.final_evidence_facts),
            "conflict_facts": _safe_mapping(self.conflict_facts),
            "indirect_inference_facts": _safe_mapping(self.indirect_inference_facts),
            "weak_failure_facts": _safe_mapping(self.weak_failure_facts),
            "budget": _safe_mapping(self.budget),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_model_payload()


@dataclass(frozen=True, slots=True)
class RunSufficiencyJudgment:
    judgment_id: str
    decision: RunSufficiencyDecision | str
    final_answer_posture: SufficiencyPosture | str
    mode: SufficiencyJudgmentMode | str = SufficiencyJudgmentMode.DETERMINISTIC
    contract_id: str | None = None
    selected_template_ids: tuple[str, ...] = ()
    contract_fulfilled: bool = False
    required_obligations_satisfied: bool = False
    missing_required_obligations: tuple[SufficiencyRequirementAssessment, ...] = ()
    partial_obligations: tuple[SufficiencyRequirementAssessment, ...] = ()
    satisfied_obligations: tuple[SufficiencyRequirementAssessment, ...] = ()
    unresolved_conflicts: tuple[str, ...] = ()
    indirect_inference_claims: tuple[Mapping[str, Any], ...] = ()
    source_bound_numeric_unknowns: tuple[Mapping[str, Any], ...] = ()
    weak_or_thin_evidence: tuple[str, ...] = ()
    failure_card_authorized: bool = False
    final_answer_allowed: bool = True
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    readiness_reasons: tuple[str, ...] = ()
    final_packet_inputs: Mapping[str, Any] = field(default_factory=dict)
    rationale: str | None = None
    validation: Mapping[str, Any] = field(default_factory=dict)
    prompt_hash: str | None = None
    prompt_length: int = 0
    model_identity: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        decision = (
            self.decision
            if isinstance(self.decision, RunSufficiencyDecision)
            else RunSufficiencyDecision(str(self.decision))
        )
        posture = (
            self.final_answer_posture
            if isinstance(self.final_answer_posture, SufficiencyPosture)
            else SufficiencyPosture(str(self.final_answer_posture))
        )
        mode = (
            self.mode
            if isinstance(self.mode, SufficiencyJudgmentMode)
            else SufficiencyJudgmentMode(str(self.mode))
        )
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "final_answer_posture", posture)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self,
            "selected_template_ids",
            _string_tuple(self.selected_template_ids),
        )
        object.__setattr__(
            self,
            "unresolved_conflicts",
            _string_tuple(self.unresolved_conflicts),
        )
        object.__setattr__(
            self,
            "indirect_inference_claims",
            tuple(
                _safe_mapping(item)
                for item in self.indirect_inference_claims
                if isinstance(item, Mapping)
            ),
        )
        object.__setattr__(
            self,
            "source_bound_numeric_unknowns",
            tuple(
                _safe_mapping(item)
                for item in self.source_bound_numeric_unknowns
                if isinstance(item, Mapping)
            ),
        )
        object.__setattr__(
            self,
            "weak_or_thin_evidence",
            _string_tuple(self.weak_or_thin_evidence),
        )
        object.__setattr__(
            self,
            "mandatory_caveats",
            _string_tuple(self.mandatory_caveats),
        )
        object.__setattr__(
            self,
            "prohibited_upgrades",
            _string_tuple(self.prohibited_upgrades),
        )
        object.__setattr__(
            self,
            "readiness_reasons",
            _string_tuple(self.readiness_reasons),
        )
        object.__setattr__(self, "validation", _safe_mapping(self.validation))
        object.__setattr__(self, "model_identity", _safe_mapping(self.model_identity))
        object.__setattr__(
            self,
            "final_packet_inputs",
            _safe_mapping(self.final_packet_inputs)
            or self._default_final_packet_inputs(),
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RunSufficiencyJudgment":
        def assessments(key: str) -> tuple[SufficiencyRequirementAssessment, ...]:
            return tuple(
                SufficiencyRequirementAssessment.from_mapping(item)
                for item in _list(payload.get(key))
                if isinstance(item, Mapping)
            )

        return cls(
            judgment_id=str(
                payload.get("judgment_id")
                or payload.get("sufficiency_id")
                or f"sufficiency:{stable_hash(payload)[:16]}"
            ),
            decision=payload.get("decision")
            or RunSufficiencyDecision.DEFER_TO_LEGACY_COMPATIBILITY.value,
            final_answer_posture=payload.get("final_answer_posture")
            or SufficiencyPosture.ANSWER_WITH_CAVEATS.value,
            mode=payload.get("mode") or SufficiencyJudgmentMode.SMART_MODEL_ADAPTED,
            contract_id=clean_token(payload.get("contract_id")),
            selected_template_ids=_string_tuple(payload.get("selected_template_ids")),
            contract_fulfilled=bool(payload.get("contract_fulfilled")),
            required_obligations_satisfied=bool(
                payload.get("required_obligations_satisfied")
            ),
            missing_required_obligations=assessments("missing_required_obligations"),
            partial_obligations=assessments("partial_obligations"),
            satisfied_obligations=assessments("satisfied_obligations"),
            unresolved_conflicts=_string_tuple(payload.get("unresolved_conflicts")),
            indirect_inference_claims=tuple(
                _safe_mapping(item)
                for item in _list(payload.get("indirect_inference_claims"))
                if isinstance(item, Mapping)
            ),
            source_bound_numeric_unknowns=tuple(
                _safe_mapping(item)
                for item in _list(payload.get("source_bound_numeric_unknowns"))
                if isinstance(item, Mapping)
            ),
            weak_or_thin_evidence=_string_tuple(payload.get("weak_or_thin_evidence")),
            failure_card_authorized=bool(payload.get("failure_card_authorized")),
            final_answer_allowed=bool(payload.get("final_answer_allowed", True)),
            mandatory_caveats=_string_tuple(payload.get("mandatory_caveats")),
            prohibited_upgrades=_string_tuple(payload.get("prohibited_upgrades")),
            readiness_reasons=_string_tuple(payload.get("readiness_reasons")),
            final_packet_inputs=_safe_mapping(payload.get("final_packet_inputs")),
            rationale=clean_text(payload.get("rationale"), limit=260),
            validation=_safe_mapping(payload.get("validation")),
            prompt_hash=clean_token(payload.get("prompt_hash")),
            prompt_length=int(payload.get("prompt_length") or 0),
            model_identity=_safe_mapping(payload.get("model_identity")),
        )

    def _default_final_packet_inputs(self) -> dict[str, Any]:
        claim_postures: list[str] = []
        if self.decision is RunSufficiencyDecision.INFERENCE_ONLY_WITH_LABELING:
            claim_postures.append("inferred_from_sourced_premises")
        elif self.final_answer_posture is SufficiencyPosture.DIRECT_ANSWER:
            claim_postures.append("directly_sourced")
        if self.final_answer_posture in {
            SufficiencyPosture.PARTIAL_ANSWER,
            SufficiencyPosture.INSUFFICIENT_ANSWER,
        }:
            claim_postures.append("insufficient_evidence")
        if self.failure_card_authorized or (
            self.final_answer_posture is SufficiencyPosture.FAILURE_CARD
        ):
            claim_postures.append("failure_card_authorized")
        if self.weak_or_thin_evidence:
            claim_postures.append("weak_corpus_authorized")
        if self.unresolved_conflicts:
            claim_postures.append("conflict_preserved")
            if self.decision is RunSufficiencyDecision.CONFLICT_BLOCKED:
                claim_postures.append("conflict_blocks_claim")
        if self.source_bound_numeric_unknowns:
            claim_postures.append("insufficient_evidence")

        if self.final_answer_posture is SufficiencyPosture.BLOCKED:
            readiness_status = "blocked"
        elif self.final_answer_posture in {
            SufficiencyPosture.PARTIAL_ANSWER,
            SufficiencyPosture.INSUFFICIENT_ANSWER,
            SufficiencyPosture.FAILURE_CARD,
        }:
            readiness_status = "insufficient_authorized"
        else:
            readiness_status = "author_ready"

        missing = [
            item.to_dict()
            for item in (*self.missing_required_obligations, *self.partial_obligations)
        ]
        return {
            "source": "RunKernel.RunAuthoritySufficiencyJudgment",
            "decision": self.decision.value,
            "final_answer_posture": self.final_answer_posture.value,
            "final_answer_allowed": bool(self.final_answer_allowed),
            "readiness_status": readiness_status,
            "readiness_reasons": list(self.readiness_reasons),
            "claim_postures": list(dict.fromkeys(claim_postures)),
            "missing_source_obligations": missing,
            "source_obligations": missing
            + [item.to_dict() for item in self.satisfied_obligations],
            "mandatory_caveats": list(self.mandatory_caveats),
            "prohibited_upgrades": list(self.prohibited_upgrades),
        }

    def to_projection(self) -> dict[str, Any]:
        return safe_json(
            {
                "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION,
                "judgment_id": self.judgment_id,
                "decision": self.decision.value,
                "mode": self.mode.value,
                "contract_id": clean_token(self.contract_id),
                "selected_template_ids": list(self.selected_template_ids),
                "contract_fulfilled": bool(self.contract_fulfilled),
                "required_obligations_satisfied": bool(
                    self.required_obligations_satisfied
                ),
                "missing_required_obligations": [
                    item.to_dict() for item in self.missing_required_obligations
                ],
                "partial_obligations": [
                    item.to_dict() for item in self.partial_obligations
                ],
                "satisfied_obligations": [
                    item.to_dict() for item in self.satisfied_obligations
                ],
                "unresolved_conflicts": list(self.unresolved_conflicts),
                "indirect_inference_claims": list(self.indirect_inference_claims),
                "source_bound_numeric_unknowns": list(
                    self.source_bound_numeric_unknowns
                ),
                "weak_or_thin_evidence": list(self.weak_or_thin_evidence),
                "failure_card_authorized": bool(self.failure_card_authorized),
                "final_answer_allowed": bool(self.final_answer_allowed),
                "final_answer_posture": self.final_answer_posture.value,
                "mandatory_caveats": list(self.mandatory_caveats),
                "prohibited_upgrades": list(self.prohibited_upgrades),
                "readiness_reasons": list(self.readiness_reasons),
                "final_packet_inputs": dict(self.final_packet_inputs),
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
    "RUN_AUTHORITY_SUFFICIENCY_SCHEMA_VERSION",
    "RUN_AUTHORITY_SUFFICIENCY_TRACE_KEY",
    "RunSufficiencyDecision",
    "RunSufficiencyJudgment",
    "RunSufficiencyJudgmentInput",
    "SufficiencyJudgmentMode",
    "SufficiencyPosture",
    "SufficiencyRequirementAssessment",
    "SufficiencyValidationResult",
    "SufficiencyValidationStatus",
    "clean_text",
    "clean_token",
    "safe_json",
    "stable_hash",
]
