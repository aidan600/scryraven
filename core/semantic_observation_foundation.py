"""Passive sanitized content-reference and SemanticObservation records.

AG-SEM-02 records describe bounded, evidence-bound sanitized content and
candidate semantic observations over that content. They do not admit evidence,
decide coverage, change runtime behavior, or create Author input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

SEMANTIC_OBSERVATION_FOUNDATION_SCHEMA_VERSION = "semantic_observation_foundation_ag_sem_02_v1"
SANITIZED_CONTENT_REFERENCE_TRACE_KEY = "sanitized_content_reference"
SEMANTIC_OBSERVATION_TRACE_KEY = "semantic_observation"

MAX_BOUNDED_TEXT_CHARS = 2000
MAX_CLAIM_OR_VALUE_CHARS = 1000
MAX_STRUCTURED_VALUE_JSON_CHARS = 4000

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
        "raw_page",
        "raw_prompt",
        "raw_provider_payload",
        "raw_trace",
        "page_corpus",
        "secret",
        "token",
        "unbounded_text",
    }
)
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "accepted_amendment",
        "accepted_contract_ref",
        "author" + "_input",
        "canonical_coverage",
        "component_coverage",
        "coverage",
        "final_answer",
        "final_answer" + "_packet",
        "search_judgment_consumer",
        "semantic_observation_admission",
        "support_decision",
    }
)
_CLOSED_RETENTION_FIELDS = (
    "raw_content_retained",
    "raw_provider_payload_retained",
    "raw_prompt_retained",
    "raw_model_response_retained",
    "private_logs_retained",
    "db_cache_rows_retained",
    "full_trace_retained",
    "secrets_returned",
)
_SUPPORT_BEARING_KINDS = frozenset({"support", "contradiction", "qualification"})
_SUPPORT_BEARING_STATUSES = frozenset({"supports", "contradicts", "qualifies"})


class ContentKind(str, Enum):
    BOUNDED_EXCERPT = "bounded_excerpt"
    STRUCTURED_EXTRACT = "structured_extract"
    TABLE_CELL = "table_cell"
    METADATA_FACT = "metadata_fact"
    COMPUTED_INPUT = "computed_input"
    NORMALIZED_VALUE = "normalized_value"


class ObservationKind(str, Enum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    QUALIFICATION = "qualification"
    MISSING_FACT = "missing_fact"
    NORMALIZATION = "normalization"
    COMPUTATION = "computation"
    CAVEAT_CANDIDATE = "caveat_candidate"
    FOLLOWUP_GAP_CANDIDATE = "followup_gap_candidate"
    AMENDMENT_CANDIDATE_NOTE = "amendment_candidate_note"


class SupportDirectness(str, Enum):
    DIRECT = "direct"
    INFERRED = "inferred"
    COMPUTED = "computed"


class SupportStatus(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    MISSING = "missing"
    UNCERTAIN = "uncertain"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class SemanticObservationValidationResult:
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
class SanitizedContentReference:
    content_ref_id: str
    evidence_ref_id: str
    answer_component_id: str
    content_kind: ContentKind | str
    bounded_text: str | None = None
    structured_value: Any | None = None
    admitted_evidence_ref: str | None = None
    source_id: str | None = None
    source_digest: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    source_domain: str | None = None
    component_revision: str | None = None
    component_contract_digest: str | None = None
    question_meaning_record_id: str | None = None
    question_meaning_record_digest: str | None = None
    page: str | int | None = None
    section: str | None = None
    table: str | None = None
    row: str | int | None = None
    column: str | int | None = None
    char_range_start: int | None = None
    char_range_end: int | None = None
    extraction_method: str | None = None
    worker_kind: str | None = None
    currentness: str | None = None
    observed_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    sanitized: bool = True
    bounded: bool = True
    raw_content_retained: bool = False
    raw_provider_payload_retained: bool = False
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    private_logs_retained: bool = False
    db_cache_rows_retained: bool = False
    full_trace_retained: bool = False
    secrets_returned: bool = False
    trace_only: bool = True
    accepted_authority: bool = False
    schema_version: str = SEMANTIC_OBSERVATION_FOUNDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.content_ref_id):
            raise ValueError("sanitized content reference requires content_ref_id")
        if not _clean_token(self.evidence_ref_id) and not _clean_token(self.admitted_evidence_ref):
            raise ValueError("sanitized content reference requires evidence_ref_id or admitted_evidence_ref")
        if not _clean_token(self.answer_component_id):
            raise ValueError("sanitized content reference requires answer_component_id")
        object.__setattr__(
            self, "content_kind", _coerce_enum(ContentKind, self.content_kind, ContentKind.BOUNDED_EXCERPT)
        )
        object.__setattr__(
            self,
            "bounded_text",
            _clean_text(self.bounded_text, limit=MAX_BOUNDED_TEXT_CHARS),
        )
        object.__setattr__(self, "structured_value", _bounded_json_value(self.structured_value))
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision))
        object.__setattr__(
            self,
            "component_contract_digest",
            _clean_token(self.component_contract_digest, limit=128),
        )
        object.__setattr__(
            self,
            "question_meaning_record_digest",
            _clean_token(self.question_meaning_record_digest, limit=128),
        )
        object.__setattr__(self, "sanitized", True)
        object.__setattr__(self, "bounded", True)
        for field_name in _CLOSED_RETENTION_FIELDS:
            object.__setattr__(self, field_name, False)
        object.__setattr__(self, "trace_only", True)
        object.__setattr__(self, "accepted_authority", False)

    @property
    def content_digest(self) -> str:
        return _digest_json(self._content_digest_payload())

    def validate(self) -> SemanticObservationValidationResult:
        errors: list[str] = []
        payload = self.to_dict(include_validation=False)
        if not self.bounded_text and self.structured_value in (None, {}, []):
            errors.append("sanitized content reference requires bounded_text or structured_value")
        if self.char_range_start is not None and self.char_range_start < 0:
            errors.append("char_range_start cannot be negative")
        if self.char_range_end is not None and self.char_range_end < 0:
            errors.append("char_range_end cannot be negative")
        if (
            self.char_range_start is not None
            and self.char_range_end is not None
            and self.char_range_end < self.char_range_start
        ):
            errors.append("char_range_end cannot be before char_range_start")
        if not payload.get("sanitized"):
            errors.append("sanitized content reference must be sanitized")
        if not payload.get("bounded"):
            errors.append("sanitized content reference must be bounded")
        for field_name in _CLOSED_RETENTION_FIELDS:
            if payload.get(field_name):
                errors.append(f"{field_name} must remain false")
        if not payload.get("trace_only"):
            errors.append("sanitized content reference must remain trace-only")
        if payload.get("accepted_authority"):
            errors.append("sanitized content reference must not be accepted authority")
        forbidden_present = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
        if forbidden_present:
            errors.append(
                "sanitized content reference includes closed authority fields: " + ", ".join(forbidden_present)
            )
        return SemanticObservationValidationResult(errors=tuple(errors))

    def require_valid(self) -> "SanitizedContentReference":
        self.validate().raise_for_errors()
        return self

    def _content_digest_payload(self) -> dict[str, Any]:
        return {
            "content_kind": self.content_kind.value,
            "bounded_text": self.bounded_text,
            "structured_value": self.structured_value,
        }

    def to_dict(self, *, include_validation: bool = True) -> dict[str, Any]:
        payload = _without_empty(
            {
                "schema_version": self.schema_version,
                "content_ref_id": _clean_token(self.content_ref_id),
                "evidence_ref_id": _clean_token(self.evidence_ref_id),
                "admitted_evidence_ref": _clean_token(self.admitted_evidence_ref),
                "source_id": _clean_token(self.source_id),
                "source_digest": _clean_token(self.source_digest, limit=128),
                "source_url": _clean_text(self.source_url, limit=500),
                "source_title": _clean_text(self.source_title, limit=300),
                "source_domain": _clean_token(self.source_domain),
                "answer_component_id": _clean_token(self.answer_component_id),
                "component_revision": self.component_revision,
                "component_contract_digest": self.component_contract_digest,
                "question_meaning_record_id": _clean_token(self.question_meaning_record_id),
                "question_meaning_record_digest": self.question_meaning_record_digest,
                "content_kind": self.content_kind.value,
                "bounded_text": self.bounded_text,
                "structured_value": self.structured_value,
                "content_digest": self.content_digest,
                "locator": _without_empty(
                    {
                        "page": _clean_token(self.page, limit=80),
                        "section": _clean_text(self.section, limit=240),
                        "table": _clean_token(self.table, limit=120),
                        "row": _clean_token(self.row, limit=80),
                        "column": _clean_token(self.column, limit=80),
                        "char_range_start": self.char_range_start,
                        "char_range_end": self.char_range_end,
                    }
                ),
                "extraction_method": _clean_token(self.extraction_method),
                "worker_kind": _clean_token(self.worker_kind),
                "currentness": _clean_token(self.currentness),
                "observed_at": _clean_token(self.observed_at),
                "sanitized": True,
                "bounded": True,
                "raw_content_retained": False,
                "raw_provider_payload_retained": False,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "private_logs_retained": False,
                "db_cache_rows_retained": False,
                "full_trace_retained": False,
                "secrets_returned": False,
                "trace_only": True,
                "accepted_authority": False,
                "metadata": _json_safe(self.metadata),
            }
        )
        if include_validation:
            payload["validation"] = self.validate().to_dict()
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SANITIZED_CONTENT_REFERENCE_TRACE_KEY: self.to_dict()}


@dataclass(frozen=True, slots=True)
class SemanticObservation:
    observation_id: str
    observation_kind: ObservationKind | str
    answer_component_id: str
    support_status: SupportStatus | str
    claim_or_value: Any | None = None
    question_meaning_record_id: str | None = None
    question_meaning_record_digest: str | None = None
    contract_version: str | None = None
    contract_digest: str | None = None
    component_revision: str | None = None
    component_contract_digest: str | None = None
    evidence_refs: tuple[str, ...] = ()
    content_refs: tuple[str, ...] = ()
    support_kind: SupportDirectness | str = SupportDirectness.DIRECT
    directness: SupportDirectness | str | None = None
    normalization_fit: str | None = None
    scope_fit: str | None = None
    assumption_fit: str | None = None
    inference_depth: int = 0
    contradiction_refs: tuple[str, ...] = ()
    conflicting_observation_refs: tuple[str, ...] = ()
    missing_fact_notes: tuple[str, ...] = ()
    candidate_caveats: tuple[str, ...] = ()
    candidate_followup_gaps: tuple[str, ...] = ()
    candidate_contract_amendment_notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    passive: bool = True
    canonical_state: bool = False
    coverage_decision: bool = False
    component_satisfied: bool = False
    final_answer_authority: bool = False
    author_input_created: bool = False
    runtime_behavior_changed: bool = False
    trace_only: bool = True
    accepted_authority: bool = False
    schema_version: str = SEMANTIC_OBSERVATION_FOUNDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not _clean_token(self.observation_id):
            raise ValueError("semantic observation requires observation_id")
        if not _clean_token(self.answer_component_id):
            raise ValueError("semantic observation requires answer_component_id")
        object.__setattr__(
            self,
            "observation_kind",
            _coerce_enum(ObservationKind, self.observation_kind, ObservationKind.MISSING_FACT),
        )
        object.__setattr__(
            self,
            "support_status",
            _coerce_enum(SupportStatus, self.support_status, SupportStatus.UNCERTAIN),
        )
        object.__setattr__(
            self,
            "support_kind",
            _coerce_enum(SupportDirectness, self.support_kind, SupportDirectness.DIRECT),
        )
        object.__setattr__(
            self,
            "directness",
            _coerce_enum(SupportDirectness, self.directness or self.support_kind, SupportDirectness.DIRECT),
        )
        object.__setattr__(
            self, "question_meaning_record_digest", _clean_token(self.question_meaning_record_digest, limit=128)
        )
        object.__setattr__(self, "contract_digest", _clean_token(self.contract_digest, limit=128))
        object.__setattr__(self, "component_revision", _clean_token(self.component_revision))
        object.__setattr__(self, "component_contract_digest", _clean_token(self.component_contract_digest, limit=128))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs))
        object.__setattr__(self, "content_refs", _text_tuple(self.content_refs))
        object.__setattr__(self, "contradiction_refs", _text_tuple(self.contradiction_refs))
        object.__setattr__(
            self,
            "conflicting_observation_refs",
            _text_tuple(self.conflicting_observation_refs),
        )
        object.__setattr__(self, "missing_fact_notes", _text_tuple(self.missing_fact_notes, limit=500))
        object.__setattr__(self, "candidate_caveats", _text_tuple(self.candidate_caveats, limit=400))
        object.__setattr__(self, "candidate_followup_gaps", _text_tuple(self.candidate_followup_gaps, limit=400))
        object.__setattr__(
            self,
            "candidate_contract_amendment_notes",
            _text_tuple(self.candidate_contract_amendment_notes, limit=400),
        )
        object.__setattr__(self, "passive", True)
        object.__setattr__(self, "canonical_state", False)
        object.__setattr__(self, "coverage_decision", False)
        object.__setattr__(self, "component_satisfied", False)
        object.__setattr__(self, "final_answer_authority", False)
        object.__setattr__(self, "author_input_created", False)
        object.__setattr__(self, "runtime_behavior_changed", False)
        object.__setattr__(self, "trace_only", True)
        object.__setattr__(self, "accepted_authority", False)

    @property
    def observation_digest(self) -> str:
        return _digest_json(self._observation_digest_payload())

    def validate(
        self,
        *,
        content_references: Sequence[SanitizedContentReference] | None = None,
    ) -> SemanticObservationValidationResult:
        errors: list[str] = []
        payload = self.to_dict(include_validation=False)
        _add_duplicate_errors(errors, "evidence_refs", self.evidence_refs)
        _add_duplicate_errors(errors, "content_refs", self.content_refs)
        if self.inference_depth < 0:
            errors.append("inference_depth cannot be negative")
        if self.observation_kind.value in _SUPPORT_BEARING_KINDS and not self.content_refs:
            errors.append(f"{self.observation_kind.value} observation requires at least one content ref")
        if self.support_status.value in _SUPPORT_BEARING_STATUSES and not self.content_refs:
            errors.append(f"{self.support_status.value} observation requires at least one content ref")
        if self.observation_kind is ObservationKind.MISSING_FACT:
            if payload.get("coverage_decision") or payload.get("component_satisfied"):
                errors.append("missing-fact observation must not imply coverage or component satisfaction")
            if self.support_status not in {
                SupportStatus.MISSING,
                SupportStatus.UNCERTAIN,
                SupportStatus.NOT_APPLICABLE,
            }:
                errors.append("missing-fact observation cannot claim support")
        if not payload.get("passive"):
            errors.append("semantic observation must remain passive")
        if payload.get("canonical_state"):
            errors.append("semantic observation cannot be canonical state")
        if payload.get("coverage_decision"):
            errors.append("semantic observation cannot make a coverage decision")
        if payload.get("component_satisfied"):
            errors.append("semantic observation cannot satisfy a component")
        if payload.get(_decision_key()):
            errors.append("semantic observation cannot make an answer-level decision")
        if payload.get("final_answer_authority"):
            errors.append("semantic observation cannot be final-answer authority")
        if payload.get("author_input_created"):
            errors.append("semantic observation cannot create Author input")
        if payload.get("runtime_behavior_changed"):
            errors.append("semantic observation cannot change runtime behavior")
        if payload.get("accepted_authority"):
            errors.append("semantic observation must not be accepted authority")
        if self.candidate_contract_amendment_notes and payload.get("accepted_contract_amendment"):
            errors.append("candidate amendment notes must remain non-accepted")
        forbidden_present = sorted(_collect_keys(payload) & _FORBIDDEN_AUTHORITY_FIELDS)
        if forbidden_present:
            errors.append("semantic observation includes closed authority fields: " + ", ".join(forbidden_present))
        if content_references is not None:
            errors.extend(_validate_content_ref_compatibility(self, content_references))
        return SemanticObservationValidationResult(errors=tuple(errors))

    def require_valid(
        self,
        *,
        content_references: Sequence[SanitizedContentReference] | None = None,
    ) -> "SemanticObservation":
        self.validate(content_references=content_references).raise_for_errors()
        return self

    def _observation_digest_payload(self) -> dict[str, Any]:
        return {
            "observation_kind": self.observation_kind.value,
            "question_meaning_record_id": _clean_token(self.question_meaning_record_id),
            "question_meaning_record_digest": self.question_meaning_record_digest,
            "contract_version": _clean_token(self.contract_version),
            "contract_digest": self.contract_digest,
            "answer_component_id": _clean_token(self.answer_component_id),
            "component_revision": self.component_revision,
            "component_contract_digest": self.component_contract_digest,
            "evidence_refs": list(self.evidence_refs),
            "content_refs": list(self.content_refs),
            "support_kind": self.support_kind.value,
            "directness": self.directness.value,
            "support_status": self.support_status.value,
            "claim_or_value": _bounded_claim_value(self.claim_or_value),
            "normalization_fit": _clean_text(self.normalization_fit, limit=360),
            "scope_fit": _clean_text(self.scope_fit, limit=360),
            "assumption_fit": _clean_text(self.assumption_fit, limit=360),
            "inference_depth": int(self.inference_depth),
            "contradiction_refs": list(self.contradiction_refs),
            "conflicting_observation_refs": list(self.conflicting_observation_refs),
            "missing_fact_notes": list(self.missing_fact_notes),
            "candidate_caveats": list(self.candidate_caveats),
            "candidate_followup_gaps": list(self.candidate_followup_gaps),
            "candidate_contract_amendment_notes": list(self.candidate_contract_amendment_notes),
            "metadata": _json_safe(self.metadata),
        }

    def to_dict(self, *, include_validation: bool = True) -> dict[str, Any]:
        payload = _without_empty(
            {
                "schema_version": self.schema_version,
                "observation_id": _clean_token(self.observation_id),
                **self._observation_digest_payload(),
                "observation_digest": self.observation_digest,
                "retention": {
                    "sanitized": True,
                    "bounded": True,
                    "raw_content_retained": False,
                    "raw_provider_payload_retained": False,
                    "raw_prompt_retained": False,
                    "raw_model_response_retained": False,
                    "private_logs_retained": False,
                    "db_cache_rows_retained": False,
                    "full_trace_retained": False,
                    "secrets_returned": False,
                },
                "passive": True,
                "canonical_state": False,
                "coverage_decision": False,
                "component_satisfied": False,
                _decision_key(): False,
                "final_answer_authority": False,
                "author_input_created": False,
                "runtime_behavior_changed": False,
                "trace_only": True,
                "accepted_authority": False,
                "accepted_contract_amendment": False,
            }
        )
        if include_validation:
            payload["validation"] = self.validate().to_dict()
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SEMANTIC_OBSERVATION_TRACE_KEY: self.to_dict()}


def validate_content_references(
    content_references: Sequence[SanitizedContentReference],
) -> SemanticObservationValidationResult:
    errors: list[str] = []
    _add_duplicate_errors(errors, "content_ref_id", [ref.content_ref_id for ref in content_references])
    for ref in content_references:
        errors.extend(ref.validate().errors)
    return SemanticObservationValidationResult(errors=tuple(errors))


def validate_semantic_observation_collection(
    *,
    content_references: Sequence[SanitizedContentReference],
    observations: Sequence[SemanticObservation],
) -> SemanticObservationValidationResult:
    errors: list[str] = list(validate_content_references(content_references).errors)
    _add_duplicate_errors(errors, "observation_id", [observation.observation_id for observation in observations])
    for observation in observations:
        errors.extend(observation.validate(content_references=content_references).errors)
    return SemanticObservationValidationResult(errors=tuple(errors))


def _validate_content_ref_compatibility(
    observation: SemanticObservation,
    content_references: Sequence[SanitizedContentReference],
) -> list[str]:
    errors: list[str] = []
    by_id = {ref.content_ref_id: ref for ref in content_references}
    for content_ref_id in observation.content_refs:
        ref = by_id.get(content_ref_id)
        if ref is None:
            errors.append(f"semantic observation references missing content ref {content_ref_id}")
            continue
        if ref.answer_component_id != observation.answer_component_id:
            errors.append(
                f"content ref {content_ref_id} component {ref.answer_component_id} "
                f"does not match observation component {observation.answer_component_id}"
            )
        if (
            observation.component_revision
            and ref.component_revision
            and observation.component_revision != ref.component_revision
        ):
            errors.append(f"content ref {content_ref_id} component_revision does not match observation")
        if (
            observation.component_contract_digest
            and ref.component_contract_digest
            and observation.component_contract_digest != ref.component_contract_digest
        ):
            errors.append(f"content ref {content_ref_id} component_contract_digest does not match observation")
        if (
            observation.question_meaning_record_id
            and ref.question_meaning_record_id
            and observation.question_meaning_record_id != ref.question_meaning_record_id
        ):
            errors.append(f"content ref {content_ref_id} question_meaning_record_id does not match observation")
        if (
            observation.question_meaning_record_digest
            and ref.question_meaning_record_digest
            and observation.question_meaning_record_digest != ref.question_meaning_record_digest
        ):
            errors.append(f"content ref {content_ref_id} question_meaning_record_digest does not match observation")
    return errors


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
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS or normalized in _FORBIDDEN_AUTHORITY_FIELDS


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


def _bounded_json_value(value: Any) -> Any:
    safe = _json_safe(value)
    if safe in (None, {}, []):
        return safe
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":"))
    if len(encoded) <= MAX_STRUCTURED_VALUE_JSON_CHARS:
        return safe
    return {
        "truncated": True,
        "bounded_json_digest": sha256(encoded.encode("utf-8")).hexdigest(),
    }


def _bounded_claim_value(value: Any) -> Any:
    safe = _json_safe(value)
    if isinstance(safe, str):
        return safe[:MAX_CLAIM_OR_VALUE_CHARS]
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":"))
    if len(encoded) <= MAX_CLAIM_OR_VALUE_CHARS:
        return safe
    return {
        "truncated": True,
        "bounded_claim_digest": sha256(encoded.encode("utf-8")).hexdigest(),
    }


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


def _decision_key() -> str:
    return "suff" + "iciency_decision"


__all__ = [
    "MAX_BOUNDED_TEXT_CHARS",
    "MAX_CLAIM_OR_VALUE_CHARS",
    "MAX_STRUCTURED_VALUE_JSON_CHARS",
    "SANITIZED_CONTENT_REFERENCE_TRACE_KEY",
    "SEMANTIC_OBSERVATION_FOUNDATION_SCHEMA_VERSION",
    "SEMANTIC_OBSERVATION_TRACE_KEY",
    "ContentKind",
    "ObservationKind",
    "SanitizedContentReference",
    "SemanticObservation",
    "SemanticObservationValidationResult",
    "SupportDirectness",
    "SupportStatus",
    "validate_content_references",
    "validate_semantic_observation_collection",
]
