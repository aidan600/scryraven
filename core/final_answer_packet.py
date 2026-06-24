"""Authoritative final-answer evidence/citation packet for AG-89D.

The packet is intentionally narrow: it serializes final evidence identity,
citation eligibility, source-obligation visibility, answer posture, mandatory
caveats, prohibited upgrades, and Author input references without changing
provider, search, query, prompt prose, citation formatting, or final answer
style behavior.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

FINAL_ANSWER_PACKET_SCHEMA_VERSION = "final_answer_packet_ag89d_v1"
FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION = (
    "final_answer_semantic_authority_ref_v1"
)
FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_REF_SCHEMA_VERSION = (
    "final_answer_author_payload_semantic_ref_v1"
)
FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_EVIDENCE_MANIFEST_REF_SCHEMA_VERSION = (
    "final_answer_author_payload_semantic_evidence_manifest_ref_v1"
)
FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION = (
    "final_answer_author_payload_semantic_content_coverage_ref_envelope_ag_sem_authenv_01_v1"
)
FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_SCHEMA_VERSION = (
    "final_answer_author_payload_semantic_content_coverage_ref_envelope_trace_ag_sem_authenv_01_v1"
)
FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION = (
    "final_answer_semantic_evidence_authority_manifest_v1"
)
FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION = (
    "final_answer_packet_semantic_content_coverage_ref_projection_ag_sem_fap_01_v1"
)
FINAL_ANSWER_PACKET_TRACE_KEY = "final_answer_packet"


class EvidenceAuthorityStatus(str, Enum):
    EVIDENCE_ALLOWED = "evidence_allowed"
    EVIDENCE_EXCLUDED = "evidence_excluded"


class CitationEligibilityStatus(str, Enum):
    CITATION_ELIGIBLE = "citation_eligible"
    CITATION_INELIGIBLE = "citation_ineligible"


class CitationRequirementStatus(str, Enum):
    CITATION_REQUIRED = "citation_required"
    CITATION_OPTIONAL = "citation_optional"


class SourceObligationStatus(str, Enum):
    SATISFIED = "source_obligation_satisfied"
    PARTIAL = "source_obligation_partial"
    MISSING_REQUIRED_SOURCE = "missing_required_source"
    OFFICIAL_CURRENT_UNSATISFIED = "official_current_unsatisfied"
    SOURCE_BOUND_VALUE_MISSING = "source_bound_value_missing"
    NOT_AVAILABLE = "source_obligation_state_unavailable"


class ClaimPosture(str, Enum):
    DIRECTLY_SOURCED = "directly_sourced"
    INFERRED_FROM_SOURCED_PREMISES = "inferred_from_sourced_premises"
    UNSUPPORTED = "unsupported"
    CONFLICT_PRESERVED = "conflict_preserved"
    CONFLICT_BLOCKS_CLAIM = "conflict_blocks_claim"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WEAK_CORPUS_AUTHORIZED = "weak_corpus_authorized"
    FAILURE_CARD_AUTHORIZED = "failure_card_authorized"


class AuthorInputStatus(str, Enum):
    AUTHOR_INPUT_READY = "author_input_ready"


class FinalAnswerReadinessStatus(str, Enum):
    AUTHOR_READY = "author_ready"
    INSUFFICIENT_AUTHORIZED = "insufficient_authorized"
    BLOCKED = "blocked"


_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)
_PUBLIC_RAW_BOOLEAN_KEYS = frozenset(
    {
        "raw_content_included",
        "raw_prompt_included",
    }
)
_PROTECTED_MARKERS = ("raw prompt", "raw_provider", "provider_payload", "secret")
_AUTHOR_SEMANTIC_TRACE_REF_KEYS = (
    "schema_version",
    "available",
    "source_packet_id",
    "source_packet_schema_version",
    "semantic_authority_ref_schema_version",
    "authority_owner",
    "semantic_state_facts_digest",
    "ref_digest",
    "prompt_visible",
    "final_text_included",
    "raw_content_included",
)
_AUTHOR_SEMANTIC_TRACE_REF_BOOL_KEYS = frozenset(
    {
        "available",
        "prompt_visible",
        "final_text_included",
        "raw_content_included",
    }
)
_AUTHOR_SEMANTIC_EVIDENCE_MANIFEST_TRACE_REF_KEYS = (
    "schema_version",
    "available",
    "source_packet_id",
    "source_packet_schema_version",
    "semantic_evidence_authority_manifest_schema_version",
    "semantic_evidence_authority_manifest_digest",
    "semantic_authority_ref_digest",
    "semantic_state_facts_digest",
    "content_refs_available",
    "coverage_refs_available",
    "prompt_visible",
    "author_payload_content_included",
    "model_request_visible",
    "final_text_included",
    "raw_content_included",
    "bounded_text_included",
    "raw_prompt_included",
    "provider_payload_included",
)
_AUTHOR_SEMANTIC_EVIDENCE_MANIFEST_TRACE_REF_BOOL_KEYS = frozenset(
    {
        "available",
        "content_refs_available",
        "coverage_refs_available",
        "prompt_visible",
        "author_payload_content_included",
        "model_request_visible",
        "final_text_included",
        "raw_content_included",
        "bounded_text_included",
        "raw_prompt_included",
        "provider_payload_included",
    }
)
_AUTHOR_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_KEYS = (
    "schema_version",
    "available",
    "source_packet_id",
    "source_packet_schema_version",
    "source_projection_schema_version",
    "source_projection_digest",
    "envelope_digest",
    "semantic_state_facts_digest",
    "content_refs_available",
    "coverage_refs_available",
    "component_ref_count",
    "coverage_record_ref_count",
    "semantic_observation_ref_count",
    "sanitized_content_ref_count",
    "content_ref_digest_count",
    "semantic_ref_evidence_id_count",
    "source_obligation_ref_count",
    "author_payload_visible",
    "authority_payload_visible",
    "authority_block_visible",
    "prompt_visible",
    "model_request_visible",
    "final_text_included",
    "raw_content_included",
    "bounded_text_included",
    "raw_prompt_included",
    "provider_payload_included",
)
_AUTHOR_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_BOOL_KEYS = frozenset(
    {
        "available",
        "content_refs_available",
        "coverage_refs_available",
        "author_payload_visible",
        "authority_payload_visible",
        "authority_block_visible",
        "prompt_visible",
        "model_request_visible",
        "final_text_included",
        "raw_content_included",
        "bounded_text_included",
        "raw_prompt_included",
        "provider_payload_included",
    }
)


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _stable_safe_json_digest(value: Any) -> str:
    canonical_json = json.dumps(
        _safe_json(value),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return text[:limit]


def _domain_from_url(url: Any) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    without_scheme = text.split("://", 1)[-1]
    domain = without_scheme.split("/", 1)[0].split("?", 1)[0].strip().lower()
    return domain or None


def _citation_ineligible_prompt_ref(ref: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, label in (
        ("evidence_position", "evidence_position"),
        ("source_id", "source_id"),
        ("domain", "domain"),
        ("title", "title"),
        ("reason", "reason"),
    ):
        value = _safe_json(ref.get(key))
        if value in (None, "", [], {}):
            continue
        parts.append(f"{label}={value}")
    return ", ".join(parts) if parts else "reason=citation_ineligible"


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return (
        normalized in _SENSITIVE_KEYS
        or (
            normalized.startswith("raw_")
            and normalized not in _PUBLIC_RAW_BOOLEAN_KEYS
        )
    )


def _safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=500)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            clean_key = _clean_token(key, limit=100)
            if not clean_key:
                continue
            out[clean_key] = "[redacted]" if _is_sensitive_key(key) else _safe_json(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe_json(item, depth=depth + 1) for item in list(value)[:50]]
    return _clean_text(value, limit=300)


def _safe_author_semantic_trace_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _AUTHOR_SEMANTIC_TRACE_REF_KEYS:
        if key not in value:
            continue
        item = value[key]
        out[key] = (
            bool(item)
            if key in _AUTHOR_SEMANTIC_TRACE_REF_BOOL_KEYS
            else _safe_json(item)
        )
    return out


def _safe_author_semantic_evidence_manifest_trace_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _AUTHOR_SEMANTIC_EVIDENCE_MANIFEST_TRACE_REF_KEYS:
        if key not in value:
            continue
        item = value[key]
        out[key] = (
            bool(item)
            if key in _AUTHOR_SEMANTIC_EVIDENCE_MANIFEST_TRACE_REF_BOOL_KEYS
            else _safe_json(item)
        )
    return out


def _sequence_count(value: Any) -> int:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return 0
    return len(value)


def _safe_author_semantic_content_coverage_ref_envelope_trace_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _AUTHOR_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_KEYS:
        if key not in value:
            continue
        item = value[key]
        out[key] = (
            bool(item)
            if key in _AUTHOR_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_BOOL_KEYS
            else _safe_json(item)
        )
    return out


@dataclass(frozen=True, slots=True)
class FinalEvidenceRecord:
    evidence_id: str
    status: EvidenceAuthorityStatus | str
    position: int | None = None
    source_id: Any | None = None
    url: str | None = None
    title: str | None = None
    domain: str | None = None
    source_tier: str | None = None
    source_class: str | None = None
    text_hash: str | None = None
    text_length: int | None = None
    reason: str | None = None
    query_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, EvidenceAuthorityStatus) else str(self.status)
        if status not in {item.value for item in EvidenceAuthorityStatus}:
            raise ValueError(f"unknown final evidence status: {status}")
        if not _clean_token(self.evidence_id, limit=120):
            raise ValueError("final evidence records require an evidence_id")
        if status == EvidenceAuthorityStatus.EVIDENCE_EXCLUDED.value and not _clean_text(self.reason, limit=200):
            raise ValueError("excluded final evidence requires a reason")
        object.__setattr__(self, "status", EvidenceAuthorityStatus(status))
        if self.domain is None and self.url:
            object.__setattr__(self, "domain", _domain_from_url(self.url))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "evidence_id": _clean_token(self.evidence_id, limit=120),
            "status": self.status.value,
            "position": self.position,
            "source_id": _safe_json(self.source_id),
            "url": _clean_text(self.url, limit=500),
            "title": _clean_text(self.title, limit=300),
            "domain": _clean_text(self.domain, limit=200),
            "source_tier": _clean_text(self.source_tier, limit=100),
            "source_class": _clean_text(self.source_class, limit=100),
            "text_hash": _clean_text(self.text_hash, limit=80),
            "text_length": self.text_length,
            "reason": _clean_text(self.reason, limit=220),
            "query_refs": list(self.query_refs),
        }
        return {key: value for key, value in payload.items() if value not in (None, [], {})}

    def to_legacy_passage_ref(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "source_tier": self.source_tier,
            "source_class": self.source_class,
            "text": "",
        }


@dataclass(frozen=True, slots=True)
class CitationEligibilityRecord:
    citation_id: str
    evidence_id: str
    status: CitationEligibilityStatus | str
    requirement: CitationRequirementStatus | str = CitationRequirementStatus.CITATION_OPTIONAL
    source_id: Any | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, CitationEligibilityStatus) else str(self.status)
        requirement = self.requirement.value if isinstance(self.requirement, CitationRequirementStatus) else str(self.requirement)
        if status not in {item.value for item in CitationEligibilityStatus}:
            raise ValueError(f"unknown citation eligibility status: {status}")
        if requirement not in {item.value for item in CitationRequirementStatus}:
            raise ValueError(f"unknown citation requirement status: {requirement}")
        if not _clean_token(self.citation_id, limit=120) or not _clean_token(self.evidence_id, limit=120):
            raise ValueError("citation eligibility records require citation_id and evidence_id")
        if status == CitationEligibilityStatus.CITATION_INELIGIBLE.value and not _clean_text(self.reason, limit=200):
            raise ValueError("citation-ineligible evidence requires a reason")
        object.__setattr__(self, "status", CitationEligibilityStatus(status))
        object.__setattr__(self, "requirement", CitationRequirementStatus(requirement))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "citation_id": _clean_token(self.citation_id, limit=120),
            "evidence_id": _clean_token(self.evidence_id, limit=120),
            "status": self.status.value,
            "requirement": self.requirement.value,
            "source_id": _safe_json(self.source_id),
            "reason": _clean_text(self.reason, limit=220),
        }
        return {key: value for key, value in payload.items() if value not in (None, [], {})}


@dataclass(frozen=True, slots=True)
class SourceObligationRecord:
    obligation_id: str
    source_class: str
    status: SourceObligationStatus | str
    custody_requirement_id: str | None = None
    satisfied_candidate_ids: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, SourceObligationStatus) else str(self.status)
        if status not in {item.value for item in SourceObligationStatus}:
            raise ValueError(f"unknown source obligation status: {status}")
        if not _clean_token(self.obligation_id, limit=120) or not _clean_token(self.source_class, limit=120):
            raise ValueError("source obligations require obligation_id and source_class")
        object.__setattr__(self, "status", SourceObligationStatus(status))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "obligation_id": _clean_token(self.obligation_id, limit=120),
            "source_class": _clean_token(self.source_class, limit=120),
            "status": self.status.value,
            "custody_requirement_id": _clean_token(self.custody_requirement_id, limit=160),
            "satisfied_candidate_ids": list(self.satisfied_candidate_ids),
            "reason": _clean_text(self.reason, limit=240),
        }
        return {key: value for key, value in payload.items() if value not in (None, [], {})}


@dataclass(frozen=True, slots=True)
class FinalAnswerAuthorInputPayload:
    packet_id: str
    prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_provider: str | None = None
    author_model: str | None = None
    status: AuthorInputStatus | str = AuthorInputStatus.AUTHOR_INPUT_READY
    author_evidence_ids: tuple[str, ...] = ()
    citation_source_ids: tuple[Any, ...] = ()
    citation_ineligible_refs: tuple[Mapping[str, Any], ...] = ()
    missing_source_obligations: tuple[Mapping[str, Any], ...] = ()
    partial_source_obligations: tuple[Mapping[str, Any], ...] = ()
    satisfied_source_obligations: tuple[Mapping[str, Any], ...] = ()
    source_bound_numeric_unknowns: tuple[Mapping[str, Any], ...] = ()
    source_bound_numeric_resolutions: tuple[Mapping[str, Any], ...] = ()
    readiness_status: str | None = None
    final_answer_posture: str | None = None
    sufficiency_decision: str | None = None
    claim_postures: tuple[str, ...] = ()
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    authority_payload: Mapping[str, Any] = field(default_factory=dict)
    authority_block: str = ""
    semantic_authority_trace_ref: Mapping[str, Any] = field(default_factory=dict)
    semantic_evidence_authority_manifest_trace_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    semantic_content_coverage_ref_envelope: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, AuthorInputStatus) else str(self.status)
        if status not in {item.value for item in AuthorInputStatus}:
            raise ValueError(f"unknown author input status: {status}")
        object.__setattr__(self, "status", AuthorInputStatus(status))

    def to_trace_ref(self) -> dict[str, Any]:
        payload = {
            "packet_id": self.packet_id,
            "status": self.status.value,
            "prompt_hash": _hash_text(self.prompt),
            "prompt_length": len(self.prompt),
            "prompt_text_included": False,
            "author_system_prompt_key": self.author_system_prompt_key,
            "author_effort": self.author_effort,
            "author_provider": self.author_provider,
            "author_model": self.author_model,
            "author_evidence_ids": list(self.author_evidence_ids),
            "citation_source_ids": list(self.citation_source_ids),
            "citation_ineligible_refs": _safe_json(self.citation_ineligible_refs),
            "missing_source_obligations": _safe_json(self.missing_source_obligations),
            "partial_source_obligations": _safe_json(self.partial_source_obligations),
            "satisfied_source_obligations": _safe_json(self.satisfied_source_obligations),
            "source_bound_numeric_unknowns": _safe_json(self.source_bound_numeric_unknowns),
            "source_bound_numeric_resolutions": _safe_json(self.source_bound_numeric_resolutions),
            "readiness_status": _clean_text(self.readiness_status, limit=120),
            "final_answer_posture": _clean_text(self.final_answer_posture, limit=120),
            "sufficiency_decision": _clean_text(self.sufficiency_decision, limit=120),
            "claim_postures": list(self.claim_postures),
            "mandatory_caveat_count": len(self.mandatory_caveats),
            "prohibited_upgrade_count": len(self.prohibited_upgrades),
            "authority_payload": _safe_json(self.authority_payload),
            "authority_block_hash": _hash_text(self.authority_block) if self.authority_block else None,
            "authority_block_length": len(self.authority_block),
        }
        if self.semantic_authority_trace_ref:
            payload["semantic_authority_trace_ref"] = _safe_author_semantic_trace_ref(
                self.semantic_authority_trace_ref
            )
        if self.semantic_evidence_authority_manifest_trace_ref:
            payload["semantic_evidence_authority_manifest_trace_ref"] = (
                _safe_author_semantic_evidence_manifest_trace_ref(
                    self.semantic_evidence_authority_manifest_trace_ref
                )
            )
        if self.semantic_content_coverage_ref_envelope:
            envelope = dict(self.semantic_content_coverage_ref_envelope)
            trace_ref = {
                "schema_version": (
                    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_SCHEMA_VERSION
                ),
                "available": True,
                "source_packet_id": envelope.get("source_packet_id"),
                "source_packet_schema_version": envelope.get(
                    "source_packet_schema_version"
                ),
                "source_projection_schema_version": envelope.get(
                    "source_projection_schema_version"
                ),
                "source_projection_digest": envelope.get(
                    "source_projection_digest"
                ),
                "envelope_digest": _stable_safe_json_digest(envelope),
                "semantic_state_facts_digest": envelope.get(
                    "semantic_state_facts_digest"
                ),
                "content_refs_available": bool(
                    envelope.get("content_refs_available")
                ),
                "coverage_refs_available": bool(
                    envelope.get("coverage_refs_available")
                ),
                "component_ref_count": _sequence_count(
                    envelope.get("component_refs")
                ),
                "coverage_record_ref_count": _sequence_count(
                    envelope.get("coverage_record_refs")
                ),
                "semantic_observation_ref_count": _sequence_count(
                    envelope.get("semantic_observation_refs")
                ),
                "sanitized_content_ref_count": _sequence_count(
                    envelope.get("sanitized_content_ref_ids")
                ),
                "content_ref_digest_count": _sequence_count(
                    envelope.get("content_ref_digests")
                ),
                "semantic_ref_evidence_id_count": _sequence_count(
                    envelope.get("semantic_ref_evidence_ids")
                ),
                "source_obligation_ref_count": _sequence_count(
                    envelope.get("source_obligation_refs")
                ),
                "author_payload_visible": True,
                "authority_payload_visible": False,
                "authority_block_visible": False,
                "prompt_visible": False,
                "model_request_visible": False,
                "final_text_included": False,
                "raw_content_included": False,
                "bounded_text_included": False,
                "raw_prompt_included": False,
                "provider_payload_included": False,
            }
            payload["semantic_content_coverage_ref_envelope_trace_ref"] = (
                _safe_author_semantic_content_coverage_ref_envelope_trace_ref(
                    trace_ref
                )
            )
        return payload


@dataclass(frozen=True, slots=True)
class FinalAnswerPacket:
    packet_id: str
    evidence_records: tuple[FinalEvidenceRecord, ...] = ()
    citation_records: tuple[CitationEligibilityRecord, ...] = ()
    source_obligations: tuple[SourceObligationRecord, ...] = ()
    official_current_custody_summary: Mapping[str, Any] = field(default_factory=dict)
    sufficiency_decision: str | None = None
    final_answer_posture: str | None = None
    final_answer_allowed: bool = True
    required_obligations_satisfied: bool | None = None
    missing_required_obligations: tuple[Mapping[str, Any], ...] = ()
    partial_obligations: tuple[Mapping[str, Any], ...] = ()
    satisfied_obligations: tuple[Mapping[str, Any], ...] = ()
    source_bound_numeric_unknowns: tuple[Mapping[str, Any], ...] = ()
    source_bound_numeric_resolutions: tuple[Mapping[str, Any], ...] = ()
    behavior_boundary_flags: Mapping[str, Any] = field(default_factory=dict)
    claim_postures: tuple[ClaimPosture | str, ...] = ()
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    author_input_refs: Mapping[str, Any] = field(default_factory=dict)
    query_lineage_refs: Mapping[str, Any] = field(default_factory=dict)
    readiness_status: FinalAnswerReadinessStatus | str = (
        FinalAnswerReadinessStatus.AUTHOR_READY
    )
    readiness_reasons: tuple[str, ...] = ()
    semantic_authority_ref: Mapping[str, Any] = field(default_factory=dict)
    semantic_content_coverage_ref_projection: Mapping[str, Any] = field(
        default_factory=dict
    )
    schema_version: str = FINAL_ANSWER_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        raw_status = (
            self.readiness_status.value
            if isinstance(self.readiness_status, FinalAnswerReadinessStatus)
            else str(self.readiness_status)
        )
        if raw_status not in {item.value for item in FinalAnswerReadinessStatus}:
            raise ValueError(f"unknown final answer readiness status: {raw_status}")
        if self.final_answer_allowed is False and raw_status != FinalAnswerReadinessStatus.BLOCKED.value:
            raise ValueError("disallowed FinalAnswerPacket must be blocked")
        object.__setattr__(
            self,
            "readiness_status",
            FinalAnswerReadinessStatus(raw_status),
        )

    @property
    def evidence_allowed(self) -> tuple[FinalEvidenceRecord, ...]:
        return tuple(record for record in self.evidence_records if record.status is EvidenceAuthorityStatus.EVIDENCE_ALLOWED)

    @property
    def evidence_excluded(self) -> tuple[FinalEvidenceRecord, ...]:
        return tuple(record for record in self.evidence_records if record.status is EvidenceAuthorityStatus.EVIDENCE_EXCLUDED)

    @property
    def citation_eligible(self) -> tuple[CitationEligibilityRecord, ...]:
        return tuple(record for record in self.citation_records if record.status is CitationEligibilityStatus.CITATION_ELIGIBLE)

    @property
    def citation_ineligible(self) -> tuple[CitationEligibilityRecord, ...]:
        return tuple(record for record in self.citation_records if record.status is CitationEligibilityStatus.CITATION_INELIGIBLE)

    @property
    def semantic_evidence_authority_manifest(self) -> dict[str, Any]:
        source_ref = dict(self.semantic_authority_ref or {})
        if not source_ref:
            return {}
        source_schema = _clean_text(source_ref.get("schema_version"), limit=120)
        semantic_digest = _clean_text(
            source_ref.get("semantic_state_facts_digest"),
            limit=128,
        )
        if not source_schema or not semantic_digest:
            return {}

        status_summary = {item.value: 0 for item in SourceObligationStatus}
        for record in self.source_obligations:
            status_summary[record.status.value] = (
                status_summary.get(record.status.value, 0) + 1
            )

        manifest: dict[str, Any] = {
            "schema_version": (
                FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION
            ),
            "available": True,
            "source_packet_id": _clean_token(self.packet_id, limit=120),
            "source_packet_schema_version": self.schema_version,
            "semantic_authority_ref_schema_version": source_schema,
            "semantic_authority_ref_digest": _stable_safe_json_digest(source_ref),
            "semantic_state_facts_digest": semantic_digest,
            "evidence_ids": [
                record.evidence_id
                for record in self.evidence_allowed
                if _clean_token(record.evidence_id, limit=120)
            ],
            "citation_source_ids": [
                _safe_json(record.source_id)
                for record in self.citation_eligible
                if record.source_id is not None
            ],
            "source_obligation_status_summary": status_summary,
            "content_refs_available": False,
            "coverage_refs_available": False,
            "deferred_ref_fields": [
                "sanitized_content_ref_ids",
                "content_ref_digests",
                "coverage_record_ids",
                "coverage_record_digests",
            ],
            "prompt_visible": False,
            "author_payload_visible": False,
            "author_payload_ref_envelope_available": False,
            "model_request_visible": False,
        }
        ref_projection = dict(self.semantic_content_coverage_ref_projection or {})
        if ref_projection.get("available") is True:
            manifest[
                "semantic_content_coverage_ref_projection_schema_version"
            ] = _clean_text(ref_projection.get("schema_version"), limit=160)
            manifest["source_projection_digest"] = _clean_text(
                ref_projection.get("source_projection_digest"),
                limit=128,
            )
            for key in (
                "component_refs",
                "coverage_record_refs",
                "semantic_observation_refs",
                "sanitized_content_ref_ids",
                "content_ref_digests",
                "semantic_ref_evidence_ids",
                "source_obligation_refs",
            ):
                value = _safe_json(ref_projection.get(key))
                if value not in (None, "", [], {}):
                    manifest[key] = value

            content_refs_available = bool(
                ref_projection.get("content_refs_available")
                and ref_projection.get("sanitized_content_ref_ids")
                and ref_projection.get("content_ref_digests")
            )
            coverage_refs_available = bool(
                ref_projection.get("coverage_refs_available")
                and ref_projection.get("coverage_record_refs")
            )
            manifest["content_refs_available"] = content_refs_available
            manifest["coverage_refs_available"] = coverage_refs_available
            deferred_fields = [
                field_name
                for field_name, available in (
                    ("sanitized_content_ref_ids", content_refs_available),
                    ("content_ref_digests", content_refs_available),
                    ("coverage_record_refs", coverage_refs_available),
                )
                if not available
            ]
            if deferred_fields:
                manifest["deferred_ref_fields"] = deferred_fields
            else:
                manifest.pop("deferred_ref_fields", None)
            manifest["raw_content_included"] = False
            manifest["bounded_text_included"] = False
            manifest["prompt_visible"] = False
            manifest["author_payload_visible"] = False
            manifest["author_payload_ref_envelope_available"] = bool(
                content_refs_available and coverage_refs_available
            )
            manifest["model_request_visible"] = False
            manifest["final_text_included"] = False
        excluded_evidence_ids = [
            record.evidence_id
            for record in self.evidence_excluded
            if _clean_token(record.evidence_id, limit=120)
        ]
        if excluded_evidence_ids:
            manifest["excluded_evidence_ids"] = excluded_evidence_ids
        for key in (
            "required_component_count",
            "covered_component_count",
            "missing_component_count",
        ):
            if key in source_ref:
                value = _safe_json(source_ref[key])
                if value not in (None, "", [], {}):
                    manifest[key] = value
        return manifest

    def with_author_input_payload(self, payload: FinalAnswerAuthorInputPayload) -> "FinalAnswerPacket":
        return replace(
            self,
            author_input_refs={**dict(self.author_input_refs), **payload.to_trace_ref()},
        )

    def with_citation_observations(
        self, final_answer_source_telemetry: Mapping[str, Any] | None
    ) -> "FinalAnswerPacket":
        return replace(
            self,
            author_input_refs={
                **dict(self.author_input_refs),
                "final_answer_source_telemetry": dict(
                    final_answer_source_telemetry or {}
                ),
            },
        )

    def to_authority_payload(
        self,
        *,
        citation_source_ids: Sequence[Any],
        citation_ineligible_refs: Sequence[Mapping[str, Any]],
        missing_source_obligations: Sequence[Mapping[str, Any]],
        partial_source_obligations: Sequence[Mapping[str, Any]],
        satisfied_source_obligations: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        postures = [
            item.value if isinstance(item, ClaimPosture) else str(item)
            for item in self.claim_postures
        ]
        return {
            "packet_id": self.packet_id,
            "readiness_status": self.readiness_status.value,
            "readiness_reasons": list(self.readiness_reasons),
            "sufficiency_decision": _clean_text(self.sufficiency_decision, limit=120),
            "final_answer_posture": _clean_text(self.final_answer_posture, limit=120),
            "final_answer_allowed": bool(self.final_answer_allowed),
            "required_obligations_satisfied": self.required_obligations_satisfied,
            "claim_postures": postures,
            "citation_eligible_source_ids": list(citation_source_ids),
            "citation_ineligible_refs": _safe_json(citation_ineligible_refs),
            "missing_source_obligations": _safe_json(missing_source_obligations),
            "partial_source_obligations": _safe_json(partial_source_obligations),
            "satisfied_source_obligations": _safe_json(satisfied_source_obligations),
            "source_bound_numeric_unknowns": _safe_json(self.source_bound_numeric_unknowns),
            "source_bound_numeric_resolutions": _safe_json(self.source_bound_numeric_resolutions),
            "mandatory_caveats": [_clean_text(item, limit=300) for item in self.mandatory_caveats],
            "prohibited_upgrades": [_clean_text(item, limit=300) for item in self.prohibited_upgrades],
            "behavior_boundary_flags": _safe_json(self.behavior_boundary_flags),
        }

    def to_author_input_payload(
        self,
        *,
        prompt: str,
        author_system_prompt_key: str,
        author_effort: str,
        author_provider: str | None = None,
        author_model: str | None = None,
        author_evidence_ids: Sequence[str] | None = None,
    ) -> FinalAnswerAuthorInputPayload:
        if self.readiness_status is FinalAnswerReadinessStatus.BLOCKED:
            raise ValueError("blocked FinalAnswerPacket cannot produce Author input")
        insufficient_authorized = self.readiness_status is (
            FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
        )
        if self.evidence_records and not self.citation_records and not insufficient_authorized:
            raise ValueError(
                "FinalAnswerPacket with evidence requires citation eligibility records"
            )
        allowed_ids = tuple(record.evidence_id for record in self.evidence_allowed)
        citation_source_ids = tuple(record.source_id for record in self.citation_eligible if record.source_id is not None)
        evidence_by_id = {record.evidence_id: record for record in self.evidence_records}
        citation_ineligible_refs = tuple(
            {
                "evidence_id": record.evidence_id,
                "evidence_position": (
                    evidence_by_id[record.evidence_id].position
                    if record.evidence_id in evidence_by_id
                    else None
                ),
                "source_id": record.source_id,
                "url": (
                    evidence_by_id[record.evidence_id].url
                    if record.evidence_id in evidence_by_id
                    else None
                ),
                "domain": (
                    evidence_by_id[record.evidence_id].domain
                    if record.evidence_id in evidence_by_id
                    else None
                ),
                "title": (
                    evidence_by_id[record.evidence_id].title
                    if record.evidence_id in evidence_by_id
                    else None
                ),
                "reason": record.reason,
            }
            for record in self.citation_ineligible
        )
        missing_source_obligations = tuple(
            self.missing_required_obligations
            or tuple(
                record.to_dict()
                for record in self.source_obligations
                if record.status is not SourceObligationStatus.SATISFIED
            )
        )
        partial_source_obligations = tuple(self.partial_obligations)
        satisfied_source_obligations = tuple(
            self.satisfied_obligations
            or tuple(
                record.to_dict()
                for record in self.source_obligations
                if record.status is SourceObligationStatus.SATISFIED
            )
        )
        authority_payload = self.to_authority_payload(
            citation_source_ids=citation_source_ids,
            citation_ineligible_refs=citation_ineligible_refs,
            missing_source_obligations=missing_source_obligations,
            partial_source_obligations=partial_source_obligations,
            satisfied_source_obligations=satisfied_source_obligations,
        )
        authority_block = self.to_author_authority_block(
            citation_source_ids=citation_source_ids,
            citation_ineligible_refs=citation_ineligible_refs,
            missing_source_obligations=missing_source_obligations,
            partial_source_obligations=partial_source_obligations,
            satisfied_source_obligations=satisfied_source_obligations,
            authority_payload=authority_payload,
        )
        payload = FinalAnswerAuthorInputPayload(
            packet_id=self.packet_id,
            prompt=(prompt + authority_block if authority_block else prompt),
            author_system_prompt_key=author_system_prompt_key,
            author_effort=author_effort,
            author_provider=author_provider,
            author_model=author_model,
            author_evidence_ids=tuple(author_evidence_ids or allowed_ids),
            citation_source_ids=citation_source_ids,
            citation_ineligible_refs=citation_ineligible_refs,
            missing_source_obligations=missing_source_obligations,
            partial_source_obligations=partial_source_obligations,
            satisfied_source_obligations=satisfied_source_obligations,
            source_bound_numeric_unknowns=tuple(self.source_bound_numeric_unknowns),
            source_bound_numeric_resolutions=tuple(self.source_bound_numeric_resolutions),
            readiness_status=self.readiness_status.value,
            final_answer_posture=self.final_answer_posture,
            sufficiency_decision=self.sufficiency_decision,
            claim_postures=tuple(authority_payload["claim_postures"]),
            mandatory_caveats=self.mandatory_caveats,
            prohibited_upgrades=self.prohibited_upgrades,
            authority_payload=authority_payload,
            authority_block=authority_block,
            semantic_authority_trace_ref=self._semantic_authority_trace_ref(),
            semantic_evidence_authority_manifest_trace_ref=(
                self._semantic_evidence_authority_manifest_trace_ref()
            ),
            semantic_content_coverage_ref_envelope=(
                self._semantic_content_coverage_ref_envelope()
            ),
        )
        return payload

    def _semantic_authority_trace_ref(self) -> dict[str, Any]:
        source_ref = dict(self.semantic_authority_ref or {})
        if not source_ref:
            return {}
        source_schema = _clean_text(source_ref.get("schema_version"), limit=120)
        authority_owner = _clean_text(source_ref.get("authority_owner"), limit=160)
        semantic_digest = _clean_text(
            source_ref.get("semantic_state_facts_digest"),
            limit=128,
        )
        if not source_schema or not authority_owner or not semantic_digest:
            return {}
        return {
            "schema_version": FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_REF_SCHEMA_VERSION,
            "available": True,
            "source_packet_id": self.packet_id,
            "source_packet_schema_version": self.schema_version,
            "semantic_authority_ref_schema_version": source_schema,
            "authority_owner": authority_owner,
            "semantic_state_facts_digest": semantic_digest,
            "ref_digest": _stable_safe_json_digest(source_ref),
            "prompt_visible": False,
            "final_text_included": False,
            "raw_content_included": False,
        }

    def _semantic_evidence_authority_manifest_trace_ref(self) -> dict[str, Any]:
        manifest = self.semantic_evidence_authority_manifest
        if not manifest:
            return {}
        return {
            "schema_version": (
                FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_EVIDENCE_MANIFEST_REF_SCHEMA_VERSION
            ),
            "available": True,
            "source_packet_id": self.packet_id,
            "source_packet_schema_version": self.schema_version,
            "semantic_evidence_authority_manifest_schema_version": manifest[
                "schema_version"
            ],
            "semantic_evidence_authority_manifest_digest": _stable_safe_json_digest(
                manifest
            ),
            "semantic_authority_ref_digest": manifest["semantic_authority_ref_digest"],
            "semantic_state_facts_digest": manifest["semantic_state_facts_digest"],
            "content_refs_available": bool(manifest.get("content_refs_available")),
            "coverage_refs_available": bool(manifest.get("coverage_refs_available")),
            "prompt_visible": False,
            "author_payload_content_included": False,
            "model_request_visible": False,
            "final_text_included": False,
            "raw_content_included": False,
            "bounded_text_included": False,
            "raw_prompt_included": False,
            "provider_payload_included": False,
        }

    def _semantic_content_coverage_ref_envelope(self) -> dict[str, Any]:
        ref_projection = dict(self.semantic_content_coverage_ref_projection or {})
        if ref_projection.get("available") is not True:
            return {}

        source_projection_schema = _clean_text(
            ref_projection.get("schema_version"),
            limit=160,
        )
        source_projection_digest = _clean_text(
            ref_projection.get("source_projection_digest"),
            limit=128,
        )
        semantic_state_digest = _clean_text(
            ref_projection.get("semantic_state_facts_digest"),
            limit=128,
        )
        accepted_contract_digest = _clean_text(
            ref_projection.get("accepted_contract_digest"),
            limit=128,
        )
        component_refs = _safe_json(ref_projection.get("component_refs")) or []
        coverage_record_refs = (
            _safe_json(ref_projection.get("coverage_record_refs")) or []
        )
        semantic_observation_refs = (
            _safe_json(ref_projection.get("semantic_observation_refs")) or []
        )
        sanitized_content_ref_ids = (
            _safe_json(ref_projection.get("sanitized_content_ref_ids")) or []
        )
        content_ref_digests = (
            _safe_json(ref_projection.get("content_ref_digests")) or []
        )
        semantic_ref_evidence_ids = (
            _safe_json(ref_projection.get("semantic_ref_evidence_ids")) or []
        )
        source_obligation_refs = (
            _safe_json(ref_projection.get("source_obligation_refs")) or []
        )
        content_refs_available = bool(
            ref_projection.get("content_refs_available")
            and sanitized_content_ref_ids
            and content_ref_digests
        )
        coverage_refs_available = bool(
            ref_projection.get("coverage_refs_available")
            and coverage_record_refs
        )
        if (
            not source_projection_schema
            or not source_projection_digest
            or not semantic_state_digest
            or not accepted_contract_digest
            or not content_refs_available
            or not coverage_refs_available
        ):
            return {}

        return {
            "schema_version": (
                FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION
            ),
            "available": True,
            "source_packet_id": self.packet_id,
            "source_packet_schema_version": self.schema_version,
            "source_projection_schema_version": source_projection_schema,
            "source_projection_digest": source_projection_digest,
            "envelope_source": "FinalAnswerPacket.semantic_content_coverage_ref_projection",
            "semantic_state_facts_digest": semantic_state_digest,
            "accepted_contract_digest": accepted_contract_digest,
            "component_refs": component_refs,
            "coverage_record_refs": coverage_record_refs,
            "semantic_observation_refs": semantic_observation_refs,
            "sanitized_content_ref_ids": sanitized_content_ref_ids,
            "content_ref_digests": content_ref_digests,
            "semantic_ref_evidence_ids": semantic_ref_evidence_ids,
            "source_obligation_refs": source_obligation_refs,
            "content_refs_available": True,
            "coverage_refs_available": True,
            "author_payload_visible": True,
            "authority_payload_visible": False,
            "authority_block_visible": False,
            "prompt_visible": False,
            "model_request_visible": False,
            "final_text_included": False,
            "raw_content_included": False,
            "bounded_text_included": False,
            "raw_prompt_included": False,
            "provider_payload_included": False,
        }

    def to_author_authority_block(
        self,
        *,
        citation_source_ids: Sequence[Any],
        citation_ineligible_refs: Sequence[Mapping[str, Any]],
        missing_source_obligations: Sequence[Mapping[str, Any]],
        partial_source_obligations: Sequence[Mapping[str, Any]],
        satisfied_source_obligations: Sequence[Mapping[str, Any]],
        authority_payload: Mapping[str, Any],
    ) -> str:
        lines: list[str] = [
            "",
            "",
            "FINAL ANSWER PACKET AUTHORITY (mandatory; do not mention this block):",
            "- Use only these citation-eligible Source IDs for citations: "
            + (", ".join(str(item) for item in citation_source_ids) if citation_source_ids else "none"),
            "- Final-answer readiness: "
            + str(authority_payload.get("readiness_status") or self.readiness_status.value),
        ]
        if authority_payload.get("claim_postures"):
            lines.append(
                "- Claim posture: "
                + ", ".join(str(item) for item in authority_payload["claim_postures"])
            )
        if citation_ineligible_refs:
            rendered = []
            for ref in citation_ineligible_refs:
                rendered.append(_citation_ineligible_prompt_ref(ref))
            lines.append(
                "- Do not cite citation-ineligible evidence: " + "; ".join(rendered)
            )
        if missing_source_obligations:
            rendered = [
                f"{item.get('source_class')}={item.get('status')}"
                for item in missing_source_obligations
            ]
            lines.append(
                "- Missing or unsatisfied source obligations to caveat: "
                + "; ".join(rendered)
            )
        if partial_source_obligations:
            rendered = [
                f"{item.get('required_source_class') or item.get('source_class') or item.get('requirement_kind')}={item.get('status')}"
                for item in partial_source_obligations
            ]
            lines.append(
                "- Partial source obligations to caveat: "
                + "; ".join(rendered)
            )
        if satisfied_source_obligations:
            rendered = [
                f"{item.get('required_source_class') or item.get('source_class') or item.get('requirement_kind')}={item.get('status')}"
                for item in satisfied_source_obligations
            ]
            lines.append(
                "- Satisfied source obligations: "
                + "; ".join(rendered)
            )
        if self.source_bound_numeric_unknowns:
            rendered = [
                f"{item.get('requirement_id') or item.get('source_class') or 'source_bound_numeric'}:{item.get('reason') or 'unknown'}"
                for item in self.source_bound_numeric_unknowns
            ]
            lines.append(
                "- Source-bound numeric unknowns: "
                + "; ".join(rendered)
            )
        if self.source_bound_numeric_resolutions:
            rendered = [
                f"{item.get('quant_unit_id') or item.get('requirement_id') or 'source_bound_numeric'}={item.get('calculation_result') or item.get('extracted_values')}"
                for item in self.source_bound_numeric_resolutions
            ]
            lines.append(
                "- Source-bound numeric resolved values: "
                + "; ".join(str(item) for item in rendered)
            )
        final_answer_posture = _clean_text(
            self.final_answer_posture
            or self.author_input_refs.get("final_answer_posture"),
            limit=120,
        )
        sufficiency_decision = _clean_text(
            self.sufficiency_decision
            or self.author_input_refs.get("sufficiency_decision"),
            limit=120,
        )
        if final_answer_posture:
            line = "- Final answer posture: " + final_answer_posture
            if sufficiency_decision:
                line += f" ({sufficiency_decision})"
            lines.append(line)
        if self.mandatory_caveats:
            lines.append(
                "- Mandatory caveats to reflect: "
                + "; ".join(str(item) for item in self.mandatory_caveats)
            )
        if self.prohibited_upgrades:
            lines.append(
                "- Prohibited upgrades: "
                + "; ".join(str(item) for item in self.prohibited_upgrades)
            )
        return "\n".join(lines) + "\n"

    def to_legacy_citation_handoff_inputs(self) -> dict[str, Any]:
        allowed = [record.to_legacy_passage_ref() for record in self.evidence_allowed]
        unique_source_urls: dict[str, Any] = {}
        for record in self.evidence_allowed:
            if record.url and record.source_id is not None:
                unique_source_urls[str(record.url)] = record.source_id
        return {
            "final_evidence": allowed,
            "selected_evidence": allowed,
            "author_evidence": allowed,
            "unique_source_urls": unique_source_urls,
            "ordered_sources": list(_safe_json(self.author_input_refs.get("ordered_sources", ())) or ()),
            "final_answer_source_telemetry": dict(_safe_json(self.author_input_refs.get("final_answer_source_telemetry", {})) or {}),
            "final_citation_observation_refs": [record.source_id for record in self.citation_eligible if record.source_id is not None],
        }

    def to_dict(self) -> dict[str, Any]:
        postures = [item.value if isinstance(item, ClaimPosture) else str(item) for item in self.claim_postures]
        payload = {
            "schema_version": self.schema_version,
            "packet_id": _clean_token(self.packet_id, limit=120),
            "evidence_allowed": [record.to_dict() for record in self.evidence_allowed],
            "evidence_excluded": [record.to_dict() for record in self.evidence_excluded],
            "citation_eligible": [record.to_dict() for record in self.citation_eligible],
            "citation_ineligible": [record.to_dict() for record in self.citation_ineligible],
            "source_obligations": [record.to_dict() for record in self.source_obligations],
            "official_current_custody_summary": _safe_json(self.official_current_custody_summary),
            "sufficiency_decision": _clean_text(self.sufficiency_decision, limit=120),
            "final_answer_posture": _clean_text(self.final_answer_posture, limit=120),
            "final_answer_allowed": bool(self.final_answer_allowed),
            "required_obligations_satisfied": self.required_obligations_satisfied,
            "missing_required_obligations": _safe_json(self.missing_required_obligations),
            "partial_obligations": _safe_json(self.partial_obligations),
            "satisfied_obligations": _safe_json(self.satisfied_obligations),
            "source_bound_numeric_unknowns": _safe_json(self.source_bound_numeric_unknowns),
            "source_bound_numeric_resolutions": _safe_json(self.source_bound_numeric_resolutions),
            "behavior_boundary_flags": _safe_json(self.behavior_boundary_flags),
            "claim_postures": postures,
            "mandatory_caveats": [_clean_text(item, limit=300) for item in self.mandatory_caveats],
            "prohibited_upgrades": [_clean_text(item, limit=300) for item in self.prohibited_upgrades],
            "author_input_refs": _safe_json(self.author_input_refs),
            "query_lineage_refs": _safe_json(self.query_lineage_refs),
            "readiness_status": self.readiness_status.value,
            "readiness_reasons": [
                _clean_text(item, limit=220) for item in self.readiness_reasons
            ],
            "trace_mode": "final_answer_packet_authority_projection",
        }
        if self.semantic_authority_ref:
            payload["semantic_authority_ref"] = _safe_json(self.semantic_authority_ref)
        if self.semantic_content_coverage_ref_projection:
            payload["semantic_content_coverage_ref_projection"] = _safe_json(
                self.semantic_content_coverage_ref_projection
            )
        manifest = self.semantic_evidence_authority_manifest
        if manifest:
            payload["semantic_evidence_authority_manifest"] = _safe_json(manifest)
        return payload

    def to_trace_fragment(self) -> dict[str, Any]:
        return {FINAL_ANSWER_PACKET_TRACE_KEY: self.to_dict()}


__all__ = [
    "FINAL_ANSWER_PACKET_SCHEMA_VERSION",
    "FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_REF_SCHEMA_VERSION",
    "FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_EVIDENCE_MANIFEST_REF_SCHEMA_VERSION",
    "FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_SCHEMA_VERSION",
    "FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_CONTENT_COVERAGE_REF_ENVELOPE_TRACE_SCHEMA_VERSION",
    "FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION",
    "FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION",
    "FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION",
    "FINAL_ANSWER_PACKET_TRACE_KEY",
    "AuthorInputStatus",
    "CitationEligibilityRecord",
    "CitationEligibilityStatus",
    "CitationRequirementStatus",
    "ClaimPosture",
    "EvidenceAuthorityStatus",
    "FinalAnswerAuthorInputPayload",
    "FinalAnswerPacket",
    "FinalAnswerReadinessStatus",
    "FinalEvidenceRecord",
    "SourceObligationRecord",
    "SourceObligationStatus",
]
