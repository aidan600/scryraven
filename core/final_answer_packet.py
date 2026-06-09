"""Authoritative final-answer evidence/citation packet for AG-89D.

The packet is intentionally narrow: it serializes final evidence identity,
citation eligibility, source-obligation visibility, answer posture, mandatory
caveats, prohibited upgrades, and Author input references without changing
provider, search, query, prompt prose, citation formatting, or final answer
style behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

FINAL_ANSWER_PACKET_SCHEMA_VERSION = "final_answer_packet_ag89d_v1"
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
_PROTECTED_MARKERS = ("raw prompt", "raw_provider", "provider_payload", "secret")


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


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


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


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
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    authority_block: str = ""

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, AuthorInputStatus) else str(self.status)
        if status not in {item.value for item in AuthorInputStatus}:
            raise ValueError(f"unknown author input status: {status}")
        object.__setattr__(self, "status", AuthorInputStatus(status))

    def to_trace_ref(self) -> dict[str, Any]:
        return {
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
            "mandatory_caveat_count": len(self.mandatory_caveats),
            "prohibited_upgrade_count": len(self.prohibited_upgrades),
            "authority_block_hash": _hash_text(self.authority_block) if self.authority_block else None,
            "authority_block_length": len(self.authority_block),
        }


@dataclass(frozen=True, slots=True)
class FinalAnswerPacket:
    packet_id: str
    evidence_records: tuple[FinalEvidenceRecord, ...] = ()
    citation_records: tuple[CitationEligibilityRecord, ...] = ()
    source_obligations: tuple[SourceObligationRecord, ...] = ()
    official_current_custody_summary: Mapping[str, Any] = field(default_factory=dict)
    claim_postures: tuple[ClaimPosture | str, ...] = ()
    mandatory_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    author_input_refs: Mapping[str, Any] = field(default_factory=dict)
    query_lineage_refs: Mapping[str, Any] = field(default_factory=dict)
    readiness_status: FinalAnswerReadinessStatus | str = (
        FinalAnswerReadinessStatus.AUTHOR_READY
    )
    readiness_reasons: tuple[str, ...] = ()
    schema_version: str = FINAL_ANSWER_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        raw_status = (
            self.readiness_status.value
            if isinstance(self.readiness_status, FinalAnswerReadinessStatus)
            else str(self.readiness_status)
        )
        if raw_status not in {item.value for item in FinalAnswerReadinessStatus}:
            raise ValueError(f"unknown final answer readiness status: {raw_status}")
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
        citation_ineligible_refs = tuple(
            {
                "evidence_id": record.evidence_id,
                "source_id": record.source_id,
                "reason": record.reason,
            }
            for record in self.citation_ineligible
        )
        missing_source_obligations = tuple(
            record.to_dict()
            for record in self.source_obligations
            if record.status is not SourceObligationStatus.SATISFIED
        )
        authority_block = self.to_author_authority_block(
            citation_source_ids=citation_source_ids,
            citation_ineligible_refs=citation_ineligible_refs,
            missing_source_obligations=missing_source_obligations,
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
            mandatory_caveats=self.mandatory_caveats,
            prohibited_upgrades=self.prohibited_upgrades,
            authority_block=authority_block,
        )
        return payload


    def to_author_authority_block(
        self,
        *,
        citation_source_ids: Sequence[Any],
        citation_ineligible_refs: Sequence[Mapping[str, Any]],
        missing_source_obligations: Sequence[Mapping[str, Any]],
    ) -> str:
        lines: list[str] = [
            "",
            "",
            "FINAL ANSWER PACKET AUTHORITY (mandatory; do not mention this block):",
            "- Use only these citation-eligible Source IDs for citations: "
            + (", ".join(str(item) for item in citation_source_ids) if citation_source_ids else "none"),
        ]
        if citation_ineligible_refs:
            rendered = []
            for ref in citation_ineligible_refs:
                rendered.append(
                    f"{ref.get('evidence_id')}"
                    f"(source_id={ref.get('source_id')}, reason={ref.get('reason')})"
                )
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
        return {
            "schema_version": self.schema_version,
            "packet_id": _clean_token(self.packet_id, limit=120),
            "evidence_allowed": [record.to_dict() for record in self.evidence_allowed],
            "evidence_excluded": [record.to_dict() for record in self.evidence_excluded],
            "citation_eligible": [record.to_dict() for record in self.citation_eligible],
            "citation_ineligible": [record.to_dict() for record in self.citation_ineligible],
            "source_obligations": [record.to_dict() for record in self.source_obligations],
            "official_current_custody_summary": _safe_json(self.official_current_custody_summary),
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

    def to_trace_fragment(self) -> dict[str, Any]:
        return {FINAL_ANSWER_PACKET_TRACE_KEY: self.to_dict()}


__all__ = [
    "FINAL_ANSWER_PACKET_SCHEMA_VERSION",
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
