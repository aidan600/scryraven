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

from core.semantic_observation_foundation import SanitizedContentReference

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
FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION = (
    "final_answer_packet_semantic_packet_evidence_binding_ag_sem_evid_bind_01_v1"
)
FINAL_ANSWER_SEMANTIC_AUTHOR_MATERIALIZATION_SCHEMA_VERSION = (
    "final_answer_semantic_author_materialization_ag_auth_mat_01_v1"
)
FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_MATERIALIZATION_TRACE_SCHEMA_VERSION = (
    "final_answer_author_payload_semantic_materialization_trace_ag_auth_mat_01_v1"
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
    "semantic_packet_evidence_binding_available",
    "semantic_packet_evidence_binding_count",
    "semantic_packet_evidence_binding_digest",
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
        "semantic_packet_evidence_binding_available",
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
    "semantic_packet_evidence_binding_available",
    "semantic_packet_evidence_binding_count",
    "semantic_packet_evidence_binding_digest",
    "author_materialization_content_ref_count",
    "author_materialization_content_ref_digest",
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
        "semantic_packet_evidence_binding_available",
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
_AUTHOR_SEMANTIC_MATERIALIZATION_TRACE_REF_KEYS = (
    "schema_version",
    "available",
    "source",
    "source_packet_id",
    "source_packet_schema_version",
    "materialization_digest",
    "semantic_materialization_block_hash",
    "semantic_materialization_block_length",
    "component_count",
    "excerpt_count",
    "bounded_material_component_count",
    "bounded_material_digest",
    "bounded_material_complete",
    "accepted_contract_version",
    "accepted_contract_digest",
    "semantic_packet_evidence_binding_count",
    "semantic_packet_evidence_binding_digest",
    "prompt_visible",
    "model_request_visible",
    "bounded_text_included",
    "bounded_text_retained",
    "raw_content_included",
    "raw_prompt_included",
    "raw_prompt_retained",
    "provider_payload_included",
    "provider_payload_retained",
    "final_text_included",
    "unavailable_reason",
)
_AUTHOR_SEMANTIC_MATERIALIZATION_TRACE_BOOL_KEYS = frozenset(
    {
        "available",
        "prompt_visible",
        "model_request_visible",
        "bounded_text_included",
        "bounded_text_retained",
        "bounded_material_complete",
        "raw_content_included",
        "raw_prompt_included",
        "raw_prompt_retained",
        "provider_payload_included",
        "provider_payload_retained",
        "final_text_included",
    }
)
_SEMANTIC_MATERIALIZATION_BOUNDED_REF_KEYS = (
    "author_materialization_content_refs",
    "semantic_author_materialization_content_refs",
    "bounded_content_refs",
)
_SEMANTIC_MATERIALIZATION_EXCERPT_CHAR_LIMIT = 600
_SEMANTIC_MATERIALIZATION_DIGEST_TEXT_LIMIT = 2000


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _stable_safe_json_digest(value: Any) -> str:
    canonical_json = json.dumps(
        _safe_json(value),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def semantic_packet_evidence_binding_digest(row: Mapping[str, Any]) -> str:
    digest_row = dict(row)
    digest_row.pop("binding_digest", None)
    return _stable_safe_json_digest(digest_row)


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


def _safe_author_semantic_materialization_trace_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _AUTHOR_SEMANTIC_MATERIALIZATION_TRACE_REF_KEYS:
        if key not in value:
            continue
        item = value[key]
        out[key] = (
            bool(item)
            if key in _AUTHOR_SEMANTIC_MATERIALIZATION_TRACE_BOOL_KEYS
            else _safe_json(item)
        )
    return out


def _safe_semantic_content_coverage_projection_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    out = {
        "schema_version": _clean_text(value.get("schema_version"), limit=160),
        "available": bool(value.get("available")),
        "source_authority": _clean_text(value.get("source_authority"), limit=160),
        "source_schema_version": _clean_text(
            value.get("source_schema_version"),
            limit=160,
        ),
        "source_projection_digest": _clean_text(
            value.get("source_projection_digest"),
            limit=128,
        ),
        "semantic_state_facts_digest": _clean_text(
            value.get("semantic_state_facts_digest"),
            limit=128,
        ),
        "accepted_contract_digest": _clean_text(
            value.get("accepted_contract_digest"),
            limit=128,
        ),
        "content_refs_available": bool(value.get("content_refs_available")),
        "coverage_refs_available": bool(value.get("coverage_refs_available")),
        "component_ref_count": _sequence_count(value.get("component_refs")),
        "coverage_record_ref_count": _sequence_count(
            value.get("coverage_record_refs")
        ),
        "semantic_observation_ref_count": _sequence_count(
            value.get("semantic_observation_refs")
        ),
        "sanitized_content_ref_count": _sequence_count(
            value.get("sanitized_content_ref_ids")
        ),
        "content_ref_digest_count": _sequence_count(value.get("content_ref_digests")),
        "semantic_ref_evidence_id_count": _sequence_count(
            value.get("semantic_ref_evidence_ids")
        ),
        "semantic_source_ref_binding_count": _sequence_count(
            value.get("semantic_source_ref_bindings")
        ),
        "author_materialization_content_ref_count": _sequence_count(
            value.get("author_materialization_content_refs")
        ),
        "author_materialization_content_ref_digest": (
            _stable_safe_json_digest(value.get("author_materialization_content_refs"))
            if value.get("author_materialization_content_refs")
            else None
        ),
        "source_obligation_ref_count": _sequence_count(
            value.get("source_obligation_refs")
        ),
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    return {key: item for key, item in out.items() if item not in (None, "", [], {})}


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
    origin_evidence_ref_id: str | None = None
    origin_evidence_ref_kind: str | None = None

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
            "origin_evidence_ref_id": _clean_token(
                self.origin_evidence_ref_id,
                limit=200,
            ),
            "origin_evidence_ref_kind": _clean_token(
                self.origin_evidence_ref_kind,
                limit=120,
            ),
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
    semantic_author_materialization: Mapping[str, Any] = field(
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
                "author_materialization_content_ref_count": int(
                    envelope.get("author_materialization_content_ref_count") or 0
                ),
                "author_materialization_content_ref_digest": envelope.get(
                    "author_materialization_content_ref_digest"
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
            if envelope.get("semantic_packet_evidence_binding_available"):
                trace_ref["semantic_packet_evidence_binding_available"] = True
                trace_ref["semantic_packet_evidence_binding_count"] = envelope.get(
                    "semantic_packet_evidence_binding_count"
                )
                trace_ref["semantic_packet_evidence_binding_digest"] = envelope.get(
                    "semantic_packet_evidence_binding_digest"
                )
            payload["semantic_content_coverage_ref_envelope_trace_ref"] = (
                _safe_author_semantic_content_coverage_ref_envelope_trace_ref(
                    trace_ref
                )
            )
        if self.semantic_author_materialization:
            materialization_trace_ref = dict(self.semantic_author_materialization)
            materialization_trace_ref["schema_version"] = (
                FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_MATERIALIZATION_TRACE_SCHEMA_VERSION
            )
            payload["semantic_author_materialization_trace_ref"] = (
                _safe_author_semantic_materialization_trace_ref(
                    materialization_trace_ref
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
    semantic_packet_evidence_bindings: tuple[Mapping[str, Any], ...] = ()
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
        self._validate_semantic_packet_evidence_bindings()

    def _validate_semantic_packet_evidence_bindings(self) -> None:
        if not self.semantic_packet_evidence_bindings:
            return
        allowed_ids = {record.evidence_id for record in self.evidence_allowed}
        required = {
            "schema_version",
            "origin_evidence_ref_id",
            "origin_evidence_ref_kind",
            "packet_evidence_id",
            "content_ref_id",
            "content_digest",
            "coverage_record_id",
            "coverage_record_digest",
            "component_id",
            "component_digest",
            "binding_digest",
        }
        for raw_row in self.semantic_packet_evidence_bindings:
            row = dict(raw_row)
            if row.get("schema_version") != (
                FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION
            ):
                raise ValueError(
                    "semantic packet evidence binding schema_version is invalid"
                )
            missing = [
                key
                for key in sorted(required)
                if _safe_json(row.get(key)) in (None, "", [], {})
            ]
            if missing:
                raise ValueError(
                    "semantic packet evidence binding missing required fields: "
                    + ", ".join(missing)
                )
            if row.get("packet_evidence_id") not in allowed_ids:
                raise ValueError(
                    "semantic packet evidence binding packet_evidence_id is not allowed"
                )
            if row.get("binding_digest") != semantic_packet_evidence_binding_digest(
                row
            ):
                raise ValueError(
                    "semantic packet evidence binding_digest does not match row"
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
            manifest["component_ref_count"] = _sequence_count(
                ref_projection.get("component_refs")
            )
            manifest["coverage_record_ref_count"] = _sequence_count(
                ref_projection.get("coverage_record_refs")
            )
            manifest["semantic_observation_ref_count"] = _sequence_count(
                ref_projection.get("semantic_observation_refs")
            )
            manifest["sanitized_content_ref_count"] = _sequence_count(
                ref_projection.get("sanitized_content_ref_ids")
            )
            manifest["content_ref_digest_count"] = _sequence_count(
                ref_projection.get("content_ref_digests")
            )
            manifest["semantic_ref_evidence_id_count"] = _sequence_count(
                ref_projection.get("semantic_ref_evidence_ids")
            )
            manifest["semantic_source_ref_binding_count"] = _sequence_count(
                ref_projection.get("semantic_source_ref_bindings")
            )
            material_refs = ref_projection.get("author_materialization_content_refs")
            if material_refs:
                manifest["author_materialization_content_ref_count"] = (
                    _sequence_count(material_refs)
                )
                manifest["author_materialization_content_ref_digest"] = (
                    _stable_safe_json_digest(material_refs)
                )
            manifest["source_obligation_ref_count"] = _sequence_count(
                ref_projection.get("source_obligation_refs")
            )

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
        binding_rows = _safe_json(self.semantic_packet_evidence_bindings) or []
        if binding_rows:
            manifest["semantic_packet_evidence_binding_available"] = True
            manifest["semantic_packet_evidence_binding_count"] = len(binding_rows)
            manifest["semantic_packet_evidence_binding_digest"] = (
                _stable_safe_json_digest(binding_rows)
            )
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
        semantic_author_materialization = self._semantic_author_materialization()
        authority_block = self.to_author_authority_block(
            citation_source_ids=citation_source_ids,
            citation_ineligible_refs=citation_ineligible_refs,
            missing_source_obligations=missing_source_obligations,
            partial_source_obligations=partial_source_obligations,
            satisfied_source_obligations=satisfied_source_obligations,
            authority_payload=authority_payload,
            semantic_author_materialization=semantic_author_materialization,
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
            semantic_author_materialization=semantic_author_materialization,
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
        trace_ref = {
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
        if manifest.get("semantic_packet_evidence_binding_available"):
            trace_ref["semantic_packet_evidence_binding_available"] = True
            trace_ref["semantic_packet_evidence_binding_count"] = manifest.get(
                "semantic_packet_evidence_binding_count"
            )
            trace_ref["semantic_packet_evidence_binding_digest"] = manifest.get(
                "semantic_packet_evidence_binding_digest"
            )
        return trace_ref

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

        envelope: dict[str, Any] = {
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
        material_refs = _safe_json(
            ref_projection.get("author_materialization_content_refs")
        ) or []
        if material_refs:
            envelope["author_materialization_content_ref_count"] = len(material_refs)
            envelope["author_materialization_content_ref_digest"] = (
                _stable_safe_json_digest(material_refs)
            )
        binding_rows = _safe_json(self.semantic_packet_evidence_bindings) or []
        if binding_rows:
            envelope["semantic_packet_evidence_binding_available"] = True
            envelope["semantic_packet_evidence_binding_count"] = len(binding_rows)
            envelope["semantic_packet_evidence_binding_digest"] = (
                _stable_safe_json_digest(binding_rows)
            )
        return envelope

    def _semantic_author_materialization(self) -> dict[str, Any]:
        ref_projection = dict(self.semantic_content_coverage_ref_projection or {})
        if ref_projection.get("available") is not True:
            return {}
        binding_rows = _safe_json(self.semantic_packet_evidence_bindings) or []
        if not binding_rows:
            return {}

        component_count = _sequence_count(ref_projection.get("component_refs"))
        if not component_count:
            component_count = int(
                _safe_json(self.semantic_authority_ref.get("required_component_count"))
                or 0
            )
        if not component_count:
            return {}

        materials, unavailable_reason = (
            self._semantic_author_materialization_materials(
                component_count=component_count
            )
        )
        bounded_material_component_count = len(
            {item.get("component_id") for item in materials if item.get("component_id")}
        )
        bounded_material_complete = bool(
            materials and bounded_material_component_count == component_count
        )
        prompt_materials = materials if bounded_material_complete else ()
        block_text = self._semantic_author_materialization_block(
            component_count=component_count,
            materials=prompt_materials,
        )
        block_hash = _hash_text(block_text)
        bounded_material_digest = (
            _stable_safe_json_digest(materials) if materials else None
        )
        materialization: dict[str, Any] = {
            "schema_version": FINAL_ANSWER_SEMANTIC_AUTHOR_MATERIALIZATION_SCHEMA_VERSION,
            "available": True,
            "source": "FinalAnswerPacket.semantic_content_coverage_ref_projection",
            "source_packet_id": self.packet_id,
            "source_packet_schema_version": self.schema_version,
            "accepted_contract_version": _clean_token(
                ref_projection.get("accepted_contract_version"), limit=160
            ),
            "accepted_contract_digest": _clean_token(
                ref_projection.get("accepted_contract_digest"), limit=128
            ),
            "component_count": component_count,
            "excerpt_count": len(prompt_materials),
            "bounded_material_component_count": bounded_material_component_count,
            "bounded_material_digest": bounded_material_digest,
            "bounded_material_complete": bounded_material_complete,
            "semantic_packet_evidence_binding_count": len(binding_rows),
            "semantic_packet_evidence_binding_digest": _stable_safe_json_digest(
                binding_rows
            ),
            "semantic_materialization_block_hash": block_hash,
            "semantic_materialization_block_length": len(block_text),
            "prompt_visible": True,
            "model_request_visible": True,
            "bounded_text_included": bool(prompt_materials),
            "bounded_text_retained": False,
            "raw_content_included": False,
            "raw_prompt_included": False,
            "raw_prompt_retained": False,
            "provider_payload_included": False,
            "provider_payload_retained": False,
            "final_text_included": False,
            "block_text": block_text,
        }
        if materials:
            materialization["bounded_material_refs"] = materials
        if not prompt_materials:
            materialization["unavailable_reason"] = _clean_token(
                unavailable_reason or "bounded_excerpt_not_packet_owned",
                limit=160,
            )
        materialization["materialization_digest"] = _stable_safe_json_digest(
            {
                key: value
                for key, value in materialization.items()
                if key not in {"materialization_digest", "block_text"}
            }
        )
        return materialization

    def _semantic_author_materialization_block(
        self,
        *,
        component_count: int,
        materials: Sequence[Mapping[str, Any]],
    ) -> str:
        source_obligation_posture = self._semantic_materialization_source_obligation_posture()
        component_phrase = (
            "1 required component is"
            if component_count == 1
            else f"{component_count} required components are"
        )
        lines = [
            "",
            "CONTROLLED SEMANTIC CONTEXT (do not mention this block):",
            "- Covered components: "
            + component_phrase
            + " supported by packet-owned semantic evidence.",
            "- Support posture: supported; source obligation: "
            + source_obligation_posture
            + "; custody: custodied.",
        ]
        for index, material in enumerate(materials, start=1):
            excerpt_text = _clean_text(
                material.get("bounded_text"),
                limit=_SEMANTIC_MATERIALIZATION_EXCERPT_CHAR_LIMIT,
            )
            if not excerpt_text:
                continue
            safe_excerpt = excerpt_text.replace('"', "'")
            lines.append(
                "- Packet-owned bounded support "
                + str(index)
                + " for component "
                + str(material.get("component_id"))
                + " from citation-eligible Source ID "
                + str(material.get("source_id"))
                + ': "'
                + safe_excerpt
                + '"'
            )
        if self.mandatory_caveats:
            lines.append(
                "- Caveats to preserve: preserve the packet-required caveats; "
                "do not strengthen caveated claims."
            )
        if self.prohibited_upgrades:
            lines.append(
                "- Prohibited upgrades: obey the packet's prohibited upgrades; "
                "do not strengthen or replace evidence-bound claims."
            )
        lines.append(
            "- Boundary: this block supports drafting only. It does not add "
            "citation authority, select evidence, judge sufficiency, or satisfy "
            "missing obligations. Cite only packet-eligible Source IDs."
        )
        return "\n".join(lines) + "\n"

    def _semantic_materialization_source_obligation_posture(self) -> str:
        if not self.source_obligations:
            return "unavailable"
        if all(
            record.status is SourceObligationStatus.SATISFIED
            for record in self.source_obligations
        ):
            return "satisfied"
        if any(
            record.status is SourceObligationStatus.SATISFIED
            for record in self.source_obligations
        ):
            return "partially satisfied"
        return "caveated"

    def _semantic_author_materialization_materials(
        self,
        *,
        component_count: int,
    ) -> tuple[tuple[Mapping[str, Any], ...], str | None]:
        ref_projection = dict(self.semantic_content_coverage_ref_projection or {})
        content_refs = self._semantic_materialization_bounded_content_refs(
            ref_projection
        )
        if not content_refs:
            return (), "bounded_excerpt_not_packet_owned"

        eligible_citations = {
            record.evidence_id: record
            for record in self.citation_eligible
            if record.source_id is not None
        }
        binding_by_content_ref = {
            _clean_token(row.get("content_ref_id"), limit=160): dict(row)
            for row in self.semantic_packet_evidence_bindings
            if _clean_token(row.get("content_ref_id"), limit=160)
        }
        expected_contract_version = _clean_token(
            ref_projection.get("accepted_contract_version"), limit=160
        )
        expected_contract_digest = _clean_token(
            ref_projection.get("accepted_contract_digest"), limit=128
        )
        component_ids = {
            _clean_token(ref.get("component_id"), limit=160)
            for ref in _safe_json(ref_projection.get("component_refs")) or ()
            if isinstance(ref, Mapping)
            and _clean_token(ref.get("component_id"), limit=160)
        }
        unavailable_reason = "bounded_excerpt_not_packet_owned"
        materials: list[Mapping[str, Any]] = []
        seen_components: set[str] = set()
        for raw_ref in content_refs:
            ref = dict(raw_ref)
            if not self._semantic_materialization_content_ref_is_safe(ref):
                unavailable_reason = "bounded_excerpt_not_safe"
                continue
            content_ref_id = _clean_token(ref.get("content_ref_id"), limit=160)
            if not content_ref_id:
                unavailable_reason = "bounded_excerpt_missing_content_ref"
                continue
            binding = binding_by_content_ref.get(content_ref_id)
            if not binding:
                unavailable_reason = "bounded_excerpt_unbound_to_packet_evidence"
                continue
            component_id = _clean_token(binding.get("component_id"), limit=160)
            if (
                not component_id
                or (component_ids and component_id not in component_ids)
                or component_id in seen_components
            ):
                unavailable_reason = "bounded_excerpt_component_mismatch"
                continue
            if _clean_token(ref.get("component_id"), limit=160) and (
                _clean_token(ref.get("component_id"), limit=160) != component_id
            ):
                unavailable_reason = "bounded_excerpt_component_mismatch"
                continue
            if _clean_token(ref.get("answer_component_id"), limit=160) and (
                _clean_token(ref.get("answer_component_id"), limit=160) != component_id
            ):
                unavailable_reason = "bounded_excerpt_component_mismatch"
                continue
            if _clean_token(ref.get("component_digest"), limit=128) and (
                _clean_token(ref.get("component_digest"), limit=128)
                != _clean_token(binding.get("component_digest"), limit=128)
            ):
                unavailable_reason = "bounded_excerpt_component_digest_mismatch"
                continue
            if _clean_token(ref.get("component_contract_digest"), limit=128) and (
                _clean_token(ref.get("component_contract_digest"), limit=128)
                != _clean_token(binding.get("component_digest"), limit=128)
            ):
                unavailable_reason = "bounded_excerpt_component_digest_mismatch"
                continue
            if expected_contract_version and (
                _clean_token(ref.get("accepted_contract_version"), limit=160)
                != expected_contract_version
            ):
                unavailable_reason = "bounded_excerpt_contract_digest_mismatch"
                continue
            if expected_contract_digest and (
                _clean_token(ref.get("accepted_contract_digest"), limit=128)
                != expected_contract_digest
            ):
                unavailable_reason = "bounded_excerpt_contract_digest_mismatch"
                continue
            if _clean_token(ref.get("coverage_record_id"), limit=160) and (
                _clean_token(ref.get("coverage_record_id"), limit=160)
                != _clean_token(binding.get("coverage_record_id"), limit=160)
            ):
                unavailable_reason = "bounded_excerpt_coverage_mismatch"
                continue
            if _clean_token(ref.get("coverage_record_digest"), limit=128) and (
                _clean_token(ref.get("coverage_record_digest"), limit=128)
                != _clean_token(binding.get("coverage_record_digest"), limit=128)
            ):
                unavailable_reason = "bounded_excerpt_coverage_mismatch"
                continue
            if _clean_token(ref.get("packet_evidence_id"), limit=160) and (
                _clean_token(ref.get("packet_evidence_id"), limit=160)
                != _clean_token(binding.get("packet_evidence_id"), limit=160)
            ):
                unavailable_reason = "bounded_excerpt_packet_evidence_mismatch"
                continue
            if _clean_token(ref.get("origin_evidence_ref_id"), limit=200) and (
                _clean_token(ref.get("origin_evidence_ref_id"), limit=200)
                != _clean_token(binding.get("origin_evidence_ref_id"), limit=200)
            ):
                unavailable_reason = "bounded_excerpt_origin_evidence_mismatch"
                continue
            citation = eligible_citations.get(str(binding.get("packet_evidence_id")))
            if citation is None:
                unavailable_reason = "bounded_excerpt_evidence_not_citation_eligible"
                continue
            bounded_text = _clean_text(
                ref.get("bounded_text"),
                limit=_SEMANTIC_MATERIALIZATION_DIGEST_TEXT_LIMIT,
            )
            if not bounded_text:
                unavailable_reason = "bounded_excerpt_text_unavailable"
                continue
            expected_digest = _clean_token(binding.get("content_digest"), limit=128)
            supplied_digest = _clean_token(ref.get("content_digest"), limit=128)
            recomputed_digest = self._semantic_materialization_content_digest(
                ref,
                binding=binding,
                bounded_text=bounded_text,
            )
            if (
                not expected_digest
                or (supplied_digest and supplied_digest != expected_digest)
                or recomputed_digest != expected_digest
            ):
                unavailable_reason = "bounded_excerpt_digest_mismatch"
                continue
            material = {
                "component_id": component_id,
                "component_digest": binding.get("component_digest"),
                "accepted_contract_version": expected_contract_version,
                "accepted_contract_digest": expected_contract_digest,
                "coverage_record_id": binding.get("coverage_record_id"),
                "coverage_record_digest": binding.get("coverage_record_digest"),
                "content_ref_id": content_ref_id,
                "content_digest": expected_digest,
                "origin_evidence_ref_id": binding.get("origin_evidence_ref_id"),
                "origin_evidence_ref_kind": binding.get("origin_evidence_ref_kind"),
                "packet_evidence_id": binding.get("packet_evidence_id"),
                "source_id": citation.source_id,
                "citation_eligibility_posture": "citation_eligible_packet_evidence",
                "source_obligation_posture": (
                    self._semantic_materialization_source_obligation_posture()
                ),
                "sanitized": True,
                "bounded": True,
                "bounded_text": _clean_text(
                    bounded_text,
                    limit=_SEMANTIC_MATERIALIZATION_EXCERPT_CHAR_LIMIT,
                ),
                "raw_content_retained": False,
                "raw_provider_payload_retained": False,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "private_logs_retained": False,
                "db_cache_rows_retained": False,
                "full_trace_retained": False,
                "secrets_returned": False,
                "raw_content_included": False,
                "raw_prompt_included": False,
                "provider_payload_included": False,
                "final_text_included": False,
            }
            material["bounded_material_digest"] = _stable_safe_json_digest(material)
            materials.append(material)
            seen_components.add(component_id)
        if len(seen_components) != component_count:
            return tuple(materials), unavailable_reason
        return tuple(materials), None

    def _semantic_materialization_bounded_content_refs(
        self,
        ref_projection: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], ...]:
        refs: list[Mapping[str, Any]] = []
        for key in _SEMANTIC_MATERIALIZATION_BOUNDED_REF_KEYS:
            value = ref_projection.get(key)
            if isinstance(value, Mapping):
                if "content_ref_id" in value:
                    refs.append(value)
                else:
                    refs.extend(
                        item for item in value.values() if isinstance(item, Mapping)
                    )
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                refs.extend(item for item in value if isinstance(item, Mapping))
        return tuple(refs)

    def _semantic_materialization_content_ref_is_safe(
        self,
        ref: Mapping[str, Any],
    ) -> bool:
        if ref.get("sanitized") is False or ref.get("bounded") is False:
            return False
        if ref.get("accepted_authority"):
            return False
        forbidden_truthy = (
            "raw_content_retained",
            "raw_provider_payload_retained",
            "raw_prompt_retained",
            "raw_model_response_retained",
            "private_logs_retained",
            "db_cache_rows_retained",
            "full_trace_retained",
            "secrets_returned",
            "raw_content_included",
            "raw_prompt_included",
            "provider_payload_included",
            "final_text_included",
        )
        if any(bool(ref.get(key)) for key in forbidden_truthy):
            return False
        forbidden_keys = {
            "raw_content",
            "raw_source_text",
            "text_excerpts",
            "prompt_text",
            "raw_prompt",
            "provider_payload",
            "raw_provider_payload",
            "model_response",
            "raw_model_response",
            "final_prose",
            "final_text",
            "db_row",
            "cache",
            "full_trace",
            "logs",
        }
        return not any(key in ref for key in forbidden_keys)

    def _semantic_materialization_content_digest(
        self,
        ref: Mapping[str, Any],
        *,
        binding: Mapping[str, Any],
        bounded_text: str,
    ) -> str | None:
        try:
            content_ref = SanitizedContentReference(
                content_ref_id=str(ref.get("content_ref_id") or ""),
                evidence_ref_id=str(
                    ref.get("evidence_ref_id")
                    or binding.get("origin_evidence_ref_id")
                    or binding.get("packet_evidence_id")
                    or ""
                ),
                answer_component_id=str(
                    ref.get("answer_component_id")
                    or binding.get("component_id")
                    or ""
                ),
                content_kind=ref.get("content_kind") or "bounded_excerpt",
                bounded_text=bounded_text,
                structured_value=ref.get("structured_value"),
                admitted_evidence_ref=ref.get("admitted_evidence_ref"),
            )
        except ValueError:
            return None
        return content_ref.content_digest

    def to_author_authority_block(
        self,
        *,
        citation_source_ids: Sequence[Any],
        citation_ineligible_refs: Sequence[Mapping[str, Any]],
        missing_source_obligations: Sequence[Mapping[str, Any]],
        partial_source_obligations: Sequence[Mapping[str, Any]],
        satisfied_source_obligations: Sequence[Mapping[str, Any]],
        authority_payload: Mapping[str, Any],
        semantic_author_materialization: Mapping[str, Any] | None = None,
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
        if semantic_author_materialization:
            block_text = str(semantic_author_materialization.get("block_text") or "")
            if block_text:
                lines.append(block_text.rstrip("\n"))
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
            payload["semantic_content_coverage_ref_projection"] = (
                _safe_semantic_content_coverage_projection_ref(
                    self.semantic_content_coverage_ref_projection
                )
            )
        if self.semantic_packet_evidence_bindings:
            binding_rows = _safe_json(self.semantic_packet_evidence_bindings) or []
            payload["semantic_packet_evidence_binding_ref"] = {
                "available": True,
                "semantic_packet_evidence_binding_count": len(binding_rows),
                "semantic_packet_evidence_binding_digest": (
                    _stable_safe_json_digest(binding_rows)
                ),
            }
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
    "FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION",
    "FINAL_ANSWER_SEMANTIC_AUTHOR_MATERIALIZATION_SCHEMA_VERSION",
    "FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_MATERIALIZATION_TRACE_SCHEMA_VERSION",
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
    "semantic_packet_evidence_binding_digest",
]
