"""RunAuthority contract model for AG-92A.

The contract is canonical RunKernel state. It names source, inference,
conflict, numeric, recovery, and final-posture obligations for one run without
calling providers, search, retrieval, prompts, or final-answer code.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION = "run_authority_contract_ag92a_v1"
RUN_AUTHORITY_CONTRACT_TRACE_KEY = "run_authority_contract"

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


class ContractSynthesisMode(str, Enum):
    DETERMINISTIC_TEMPLATE = "deterministic_template"
    SMART_MODEL_ADAPTED = "smart_model_adapted"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


class ContractSynthesisStatus(str, Enum):
    VALID = "valid"
    REPAIRED = "repaired"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


class RunContractStrictness(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    CONTEXTUAL = "contextual"


class RunContractRequirementKind(str, Enum):
    OFFICIAL_CURRENT = "official_current"
    LEGAL_PRIMARY = "legal_primary"
    CANONICAL_DOCS = "canonical_docs"
    ACADEMIC = "academic"
    REPUTABLE_SECONDARY = "reputable_secondary"
    USER_DOCUMENT = "user_document"
    SOURCE_BOUND_NUMERIC = "source_bound_numeric"
    GENERAL = "general"


_STRICTNESS_RANK = {
    RunContractStrictness.CONTEXTUAL.value: 0,
    RunContractStrictness.PREFERRED.value: 1,
    RunContractStrictness.REQUIRED.value: 2,
}


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
            if clean_key.casefold() in _SENSITIVE_KEYS or clean_key.casefold().startswith(
                "raw_"
            ):
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
    payload = repr(safe_json(value)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def query_ref(query: str) -> dict[str, Any]:
    return {
        "query_hash": hashlib.sha256(str(query or "").encode("utf-8")).hexdigest(),
        "query_length": len(str(query or "")),
        "query_text_included": False,
    }


@dataclass(frozen=True, slots=True)
class RunContractSourceRequirement:
    requirement_id: str
    requirement_kind: RunContractRequirementKind | str
    strictness: RunContractStrictness | str
    required_source_class: str | None = None
    required_source_tier: str | None = None
    required_currentness: str | None = None
    satisfaction_rule: str | None = None
    allowed_lower_tier_use: str | None = None
    cannot_satisfy_with: tuple[str, ...] = ()
    rationale: str | None = None

    def __post_init__(self) -> None:
        kind = (
            self.requirement_kind.value
            if isinstance(self.requirement_kind, RunContractRequirementKind)
            else str(self.requirement_kind or RunContractRequirementKind.GENERAL.value)
        )
        strictness = (
            self.strictness.value
            if isinstance(self.strictness, RunContractStrictness)
            else str(self.strictness or RunContractStrictness.CONTEXTUAL.value)
        )
        if kind not in {item.value for item in RunContractRequirementKind}:
            kind = RunContractRequirementKind.GENERAL.value
        if strictness not in {item.value for item in RunContractStrictness}:
            strictness = RunContractStrictness.CONTEXTUAL.value
        if not clean_token(self.requirement_id):
            raise ValueError("run contract source requirement requires requirement_id")
        object.__setattr__(self, "requirement_kind", RunContractRequirementKind(kind))
        object.__setattr__(self, "strictness", RunContractStrictness(strictness))
        object.__setattr__(
            self,
            "cannot_satisfy_with",
            tuple(
                item
                for item in (
                    clean_token(value, limit=120)
                    for value in (self.cannot_satisfy_with or ())
                )
                if item
            ),
        )

    @property
    def strictness_rank(self) -> int:
        return _STRICTNESS_RANK[self.strictness.value]

    @property
    def is_required(self) -> bool:
        return self.strictness is RunContractStrictness.REQUIRED

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "requirement_id": clean_token(self.requirement_id),
            "requirement_kind": self.requirement_kind.value,
            "strictness": self.strictness.value,
            "required_source_class": clean_token(self.required_source_class),
            "required_source_tier": clean_token(self.required_source_tier),
            "required_currentness": clean_token(self.required_currentness),
            "satisfaction_rule": clean_text(self.satisfaction_rule, limit=260),
            "allowed_lower_tier_use": clean_text(self.allowed_lower_tier_use, limit=180),
            "cannot_satisfy_with": list(self.cannot_satisfy_with),
            "rationale": clean_text(self.rationale, limit=260),
        }
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, [], {})
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RunContractSourceRequirement":
        return cls(
            requirement_id=str(payload.get("requirement_id") or ""),
            requirement_kind=payload.get("requirement_kind")
            or payload.get("kind")
            or RunContractRequirementKind.GENERAL.value,
            strictness=payload.get("strictness") or RunContractStrictness.CONTEXTUAL.value,
            required_source_class=clean_token(
                payload.get("required_source_class") or payload.get("source_class")
            ),
            required_source_tier=clean_token(payload.get("required_source_tier")),
            required_currentness=clean_token(payload.get("required_currentness")),
            satisfaction_rule=clean_text(payload.get("satisfaction_rule"), limit=260),
            allowed_lower_tier_use=clean_text(
                payload.get("allowed_lower_tier_use"), limit=180
            ),
            cannot_satisfy_with=tuple(
                str(item)
                for item in payload.get("cannot_satisfy_with", ())
                if str(item or "").strip()
            ),
            rationale=clean_text(payload.get("rationale"), limit=260),
        )


@dataclass(frozen=True, slots=True)
class RunAuthorityContract:
    contract_id: str
    synthesis_mode: ContractSynthesisMode | str
    selected_template_ids: tuple[str, ...]
    user_query_ref: Mapping[str, Any]
    selected_depth: str | None
    route_facts_used: Mapping[str, Any] = field(default_factory=dict)
    question_type: str = "ordinary_explainer"
    claim_type: str = "general"
    source_requirements: tuple[RunContractSourceRequirement, ...] = ()
    inference_policy: Mapping[str, Any] = field(default_factory=dict)
    conflict_policy: Mapping[str, Any] = field(default_factory=dict)
    numeric_policy: Mapping[str, Any] = field(default_factory=dict)
    recovery_policy: Mapping[str, Any] = field(default_factory=dict)
    final_posture_policy: Mapping[str, Any] = field(default_factory=dict)
    downstream_hints: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        mode = (
            self.synthesis_mode.value
            if isinstance(self.synthesis_mode, ContractSynthesisMode)
            else str(self.synthesis_mode or ContractSynthesisMode.DETERMINISTIC_TEMPLATE.value)
        )
        if mode not in {item.value for item in ContractSynthesisMode}:
            mode = ContractSynthesisMode.FALLBACK.value
        object.__setattr__(self, "synthesis_mode", ContractSynthesisMode(mode))
        if not clean_token(self.contract_id):
            raise ValueError("run contract requires contract_id")
        object.__setattr__(
            self,
            "selected_template_ids",
            tuple(
                item
                for item in (
                    clean_token(value, limit=120)
                    for value in (self.selected_template_ids or ())
                )
                if item
            ),
        )
        object.__setattr__(
            self,
            "source_requirements",
            tuple(self.source_requirements or ()),
        )

    def to_projection(self) -> dict[str, Any]:
        source_requirements = [item.to_dict() for item in self.source_requirements]
        required = [
            item
            for item in source_requirements
            if item.get("strictness") == RunContractStrictness.REQUIRED.value
        ]
        return {
            "schema_version": self.schema_version,
            "trace_key": RUN_AUTHORITY_CONTRACT_TRACE_KEY,
            "owner": "RunKernel.RunAuthorityContract",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "sanitized": True,
            "contract_id": clean_token(self.contract_id, limit=160),
            "synthesis_mode": self.synthesis_mode.value,
            "selected_template_ids": list(self.selected_template_ids),
            "user_query_ref": safe_json(self.user_query_ref),
            "selected_depth": clean_token(self.selected_depth),
            "route_facts_used": safe_json(self.route_facts_used),
            "question_type": clean_token(self.question_type),
            "claim_type": clean_token(self.claim_type),
            "source_requirement_count": len(source_requirements),
            "required_source_requirement_count": len(required),
            "source_requirement_summary": [
                {
                    "requirement_id": item.get("requirement_id"),
                    "requirement_kind": item.get("requirement_kind"),
                    "strictness": item.get("strictness"),
                    "required_source_class": item.get("required_source_class"),
                    "required_source_tier": item.get("required_source_tier"),
                    "required_currentness": item.get("required_currentness"),
                }
                for item in source_requirements
            ],
            "source_requirements": source_requirements,
            "inference_policy": safe_json(self.inference_policy),
            "conflict_policy": safe_json(self.conflict_policy),
            "numeric_policy": safe_json(self.numeric_policy),
            "recovery_policy": safe_json(self.recovery_policy),
            "final_posture_policy": safe_json(self.final_posture_policy),
            "downstream_hints": safe_json(self.downstream_hints),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RunAuthorityContract":
        requirements = []
        for item in payload.get("source_requirements") or ():
            if isinstance(item, Mapping):
                requirements.append(RunContractSourceRequirement.from_mapping(item))
        return cls(
            contract_id=str(payload.get("contract_id") or ""),
            synthesis_mode=payload.get("synthesis_mode")
            or ContractSynthesisMode.SMART_MODEL_ADAPTED.value,
            selected_template_ids=tuple(
                str(item)
                for item in payload.get("selected_template_ids", ())
                if str(item or "").strip()
            ),
            user_query_ref=dict(payload.get("user_query_ref") or {}),
            selected_depth=clean_token(payload.get("selected_depth")),
            route_facts_used=dict(payload.get("route_facts_used") or {}),
            question_type=clean_token(payload.get("question_type")) or "ordinary_explainer",
            claim_type=clean_token(payload.get("claim_type")) or "general",
            source_requirements=tuple(requirements),
            inference_policy=dict(payload.get("inference_policy") or {}),
            conflict_policy=dict(payload.get("conflict_policy") or {}),
            numeric_policy=dict(payload.get("numeric_policy") or {}),
            recovery_policy=dict(payload.get("recovery_policy") or {}),
            final_posture_policy=dict(payload.get("final_posture_policy") or {}),
            downstream_hints=dict(payload.get("downstream_hints") or {}),
        )


@dataclass(frozen=True, slots=True)
class RunContractValidationResult:
    status: ContractSynthesisStatus | str
    reasons: tuple[str, ...] = ()
    repaired: bool = False
    fallback_used: bool = False
    blocked: bool = False
    deterministic_template_ids: tuple[str, ...] = ()
    model_attempted: bool = False
    prompt_hash: str | None = None
    prompt_length: int = 0
    provider: str | None = None
    model: str | None = None
    effort: str | None = None
    use_reasoning: bool | None = None
    prompt_text_retained: bool = False
    model_response_text_retained: bool = False

    def __post_init__(self) -> None:
        status = (
            self.status.value
            if isinstance(self.status, ContractSynthesisStatus)
            else str(self.status or ContractSynthesisStatus.VALID.value)
        )
        if status not in {item.value for item in ContractSynthesisStatus}:
            status = ContractSynthesisStatus.FALLBACK.value
        object.__setattr__(self, "status", ContractSynthesisStatus(status))
        object.__setattr__(
            self,
            "reasons",
            tuple(
                item
                for item in (
                    clean_token(value, limit=180) for value in (self.reasons or ())
                )
                if item
            ),
        )
        object.__setattr__(
            self,
            "deterministic_template_ids",
            tuple(
                item
                for item in (
                    clean_token(value, limit=120)
                    for value in (self.deterministic_template_ids or ())
                )
                if item
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reasons": list(self.reasons),
            "repaired": bool(self.repaired),
            "fallback_used": bool(self.fallback_used),
            "blocked": bool(self.blocked),
            "deterministic_template_ids": list(self.deterministic_template_ids),
            "model_attempted": bool(self.model_attempted),
            "prompt_hash": clean_token(self.prompt_hash, limit=80),
            "prompt_length": int(self.prompt_length or 0),
            "provider": clean_token(self.provider),
            "model": clean_token(self.model),
            "effort": clean_token(self.effort),
            "use_reasoning": self.use_reasoning,
            "prompt_text_retained": False,
            "model_response_text_retained": False,
        }


def source_class_facts_from_run_contract_projection(
    projection: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Return AnswerContract-ready source classes required by the contract."""

    if not isinstance(projection, Mapping):
        return {"present": (), "missing": (), "required": ()}
    if projection.get("owner") != "RunKernel.RunAuthorityContract":
        return {"present": (), "missing": (), "required": ()}
    missing: list[str] = []
    for requirement in projection.get("source_requirements") or ():
        if not isinstance(requirement, Mapping):
            continue
        if requirement.get("strictness") != RunContractStrictness.REQUIRED.value:
            continue
        source_class = clean_token(requirement.get("required_source_class"))
        if source_class and source_class not in missing:
            missing.append(source_class)
    return {"present": (), "missing": tuple(missing), "required": tuple(missing)}


def contract_query_hints_from_projection(
    projection: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return compact pre-retrieval source-obligation hints for QueryPlan."""

    if not isinstance(projection, Mapping):
        return []
    hints = projection.get("downstream_hints", {}).get("query_strategy_hints", [])
    if isinstance(hints, Sequence) and not isinstance(hints, (str, bytes)):
        return [dict(item) for item in hints if isinstance(item, Mapping)]
    return []


__all__ = [
    "RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION",
    "RUN_AUTHORITY_CONTRACT_TRACE_KEY",
    "ContractSynthesisMode",
    "ContractSynthesisStatus",
    "RunAuthorityContract",
    "RunContractRequirementKind",
    "RunContractSourceRequirement",
    "RunContractStrictness",
    "RunContractValidationResult",
    "clean_text",
    "clean_token",
    "contract_query_hints_from_projection",
    "query_ref",
    "safe_json",
    "source_class_facts_from_run_contract_projection",
    "stable_hash",
]
