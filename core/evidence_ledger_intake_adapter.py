"""AG-96I3M1 adapter from admission-review diagnostics to EvidenceLedger intake.

The adapter is deliberately pure and offline. It consumes an AG-96I3L
admission-review candidate plus an explicit caller-supplied binding object, then
emits a sanitized EvidenceLedgerObservation suitable for RunKernel reduction.

It does not call providers, search, retrieval, fetch/read, prompts, models,
citations, SufficiencyJudgment, FinalAnswerPacket, Author, or orchestration
surfaces. Runtime activation of this intake path is intentionally left to a
later phase.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.evidence_ledger import EvidenceLedgerObservation

SCHEMA_VERSION = "ag96i3m1_evidence_ledger_intake_adapter_v1"
RECORD_TYPE = "evidence_ledger_intake_adapter_result"
OBSERVATION_RECORD_TYPE = "evidence_ledger_intake_adapter_observation"
OBSERVATION_SOURCE = "ag96i3m1_admission_review_intake_adapter"

_ADMISSION_READY = "admission_review_candidate_ready"
_VERIFIED_OFFICIAL_CURRENT_RELEVANCE = "verified_official_current_relevance"
_OFFICIAL_SOURCE_SUPPORTED = "official_source_supported"
_READ_OBSERVATION_READY = "read_observation_ready"
_EVIDENCE_LEDGER_INTAKE_REVIEW_LATER = "evidence_ledger_intake_review_later"
_OFFICIAL_CURRENT = "official_current"
_OFFICIAL_CURRENT_RULES = "official_current_rules"
_SUPPORTED_SOURCE_OBLIGATIONS = frozenset({_OFFICIAL_CURRENT})
_ACCEPTABLE_IDENTITY_STATUSES = frozenset(
    {
        "candidate_url_match",
        "candidate_domain_match",
        "resolved_url_differs_same_domain",
        "official_equivalent_url_same_domain",
    }
)
_IDENTITY_MISMATCH_STATUSES = frozenset(
    {
        "candidate_url_mismatch",
        "candidate_domain_mismatch",
    }
)
_CURRENT_SOURCE_TIERS = frozenset({"official", "primary", "canonical"})
_CURRENTNESS_VALUES = frozenset({"current", "official_current"})
_PRIVATE_CONTENT_KEYS = frozenset(
    {
        "cache",
        "cache_row",
        "cache_rows",
        "db",
        "db_row",
        "db_rows",
        "excerpt",
        "excerpts",
        "extracted_text",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "model_response_text",
        "output_packet",
        "page_text",
        "private_log",
        "private_logs",
        "prompt",
        "prompts",
        "provider_payload",
        "provider_payloads",
        "raw_model_response",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_payloads",
        "raw_response",
        "raw_text",
        "raw_trace",
        "snippet",
        "snippets",
        "source_text",
        "supported_excerpt_fragments",
        "text",
        "trace",
        "verifier_text",
    }
)
_RETENTION_FLAG_SUFFIXES = (
    "_retained",
    "_retains_raw_page_text",
    "_included",
)


class EvidenceLedgerIntakeStatus(str, Enum):
    OBSERVATION_READY = "evidence_ledger_intake_observation_ready"
    BLOCKED = "evidence_ledger_intake_blocked"


class EvidenceLedgerIntakeBlockerCode(str, Enum):
    ADMISSION_REVIEW_CANDIDATE_NOT_READY = "admission_review_candidate_not_ready"
    ADMISSION_REVIEW_BLOCKERS_PRESENT = "admission_review_blockers_present"
    CANDIDATE_IDENTITY_UNVERIFIED = "candidate_identity_unverified"
    CANDIDATE_IDENTITY_MISMATCH = "candidate_identity_mismatch"
    CANDIDATE_CURRENTNESS_OR_RELEVANCE_UNCLEAR = (
        "candidate_currentness_or_relevance_unclear"
    )
    CANDIDATE_READ_OBSERVATION_INCOMPLETE = "candidate_read_observation_incomplete"
    CANDIDATE_CUSTODY_METADATA_INCOMPLETE = "candidate_custody_metadata_incomplete"
    MISSING_REQUIREMENT_ID = "missing_requirement_id"
    MISSING_CANDIDATE_ID = "missing_candidate_id"
    MISSING_OBSERVATION_ID_OR_REF = "missing_observation_id_or_ref"
    MISSING_SOURCE_OBLIGATION = "missing_source_obligation"
    UNSUPPORTED_SOURCE_OBLIGATION = "unsupported_source_obligation"
    MISSING_REQUIRED_SOURCE_CLASS = "missing_required_source_class"
    MISSING_IDEMPOTENCY_OR_DEDUP_BASIS = "missing_idempotency_or_dedup_basis"
    MISSING_ORIGIN_ACTION = "missing_origin_action"
    MISSING_OFFICIAL_CURRENT_RULES_MAPPING = (
        "missing_official_current_rules_mapping"
    )
    OFFICIAL_CURRENT_RULES_MAPPING_MISMATCH = (
        "official_current_rules_mapping_mismatch"
    )
    DOWNSTREAM_ACTIVATION_REQUESTED = "downstream_activation_requested"
    RAW_PRIVATE_PAYLOAD_RETENTION_BLOCKED = "raw_private_payload_retention_blocked"


@dataclass(frozen=True, slots=True)
class EvidenceLedgerIntakeBinding:
    """Explicit caller binding required to cross from diagnostics to intake."""

    requirement_id: str
    candidate_id: str
    observation_id: str | None = None
    observation_ref: str | None = None
    source_obligation: str = ""
    required_source_class: str = ""
    required_source_tier: str = ""
    required_currentness: str = "current"
    official_current_rules: Mapping[str, Any] = field(default_factory=dict)
    origin_phase: str = "ag96i3m1"
    origin_action: str = ""
    origin_record_type: str = "evidence_ledger_intake_binding"
    origin_schema_version: str = SCHEMA_VERSION
    idempotency_key: str | None = None
    deduplication_basis: tuple[str, ...] = ()
    final_evidence: bool = False
    citation_eligible: bool = False
    author_activation_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "requirement_id": _token(self.requirement_id),
                "candidate_id": _token(self.candidate_id),
                "observation_id": _token(self.observation_id),
                "observation_ref": _text(self.observation_ref, limit=220),
                "source_obligation": _token(self.source_obligation),
                "required_source_class": _token(self.required_source_class),
                "required_source_tier": _token(self.required_source_tier),
                "required_currentness": _token(self.required_currentness),
                "official_current_rules": _official_current_rules_projection(self),
                "origin_phase": _token(self.origin_phase),
                "origin_action": _token(self.origin_action),
                "origin_record_type": _token(self.origin_record_type),
                "origin_schema_version": _token(self.origin_schema_version),
                "idempotency_key": _text(self.idempotency_key, limit=220),
                "deduplication_basis": [
                    item for item in _string_tuple(self.deduplication_basis) if item
                ],
                "final_evidence": bool(self.final_evidence),
                "citation_eligible": bool(self.citation_eligible),
                "author_activation_allowed": bool(self.author_activation_allowed),
            }
        )


@dataclass(frozen=True, slots=True)
class EvidenceLedgerIntakeAdapterResult:
    status: EvidenceLedgerIntakeStatus
    blocker_codes: tuple[EvidenceLedgerIntakeBlockerCode, ...]
    observation: EvidenceLedgerObservation | None
    projection: Mapping[str, Any]

    @property
    def accepted(self) -> bool:
        return self.status is EvidenceLedgerIntakeStatus.OBSERVATION_READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "accepted": self.accepted,
            "blocker_codes": [item.value for item in self.blocker_codes],
            "observation": self.observation.to_dict() if self.observation else None,
            "projection": dict(self.projection),
        }


def build_evidence_ledger_intake_observation_from_admission_review(
    *,
    admission_review_candidate: Mapping[str, Any] | None,
    binding: EvidenceLedgerIntakeBinding | Mapping[str, Any],
) -> EvidenceLedgerIntakeAdapterResult:
    """Build a RunKernel/EvidenceLedger reducer payload from a ready candidate."""

    candidate = _mapping(admission_review_candidate)
    intake_binding = _coerce_binding(binding)
    blocker_codes = _dedupe_blockers(
        (
            *_admission_blockers(candidate),
            *_binding_blockers(intake_binding),
        )
    )
    projection = _result_projection(
        admission_review_candidate=candidate,
        binding=intake_binding,
        blocker_codes=blocker_codes,
    )
    if blocker_codes:
        return EvidenceLedgerIntakeAdapterResult(
            status=EvidenceLedgerIntakeStatus.BLOCKED,
            blocker_codes=tuple(blocker_codes),
            observation=None,
            projection=projection,
        )

    observation_id = _observation_id(intake_binding)
    observation = EvidenceLedgerObservation(
        observation_id=observation_id,
        source=OBSERVATION_SOURCE,
        payload=_observation_payload(
            admission_review_candidate=candidate,
            binding=intake_binding,
            observation_id=observation_id,
        ),
    )
    return EvidenceLedgerIntakeAdapterResult(
        status=EvidenceLedgerIntakeStatus.OBSERVATION_READY,
        blocker_codes=(),
        observation=observation,
        projection=projection,
    )


def _coerce_binding(
    binding: EvidenceLedgerIntakeBinding | Mapping[str, Any],
) -> EvidenceLedgerIntakeBinding:
    if isinstance(binding, EvidenceLedgerIntakeBinding):
        return binding
    value = _mapping(binding)
    return EvidenceLedgerIntakeBinding(
        requirement_id=str(value.get("requirement_id") or ""),
        candidate_id=str(value.get("candidate_id") or ""),
        observation_id=_text(value.get("observation_id"), limit=220),
        observation_ref=_text(value.get("observation_ref"), limit=220),
        source_obligation=str(value.get("source_obligation") or ""),
        required_source_class=str(
            value.get("required_source_class")
            or value.get("source_class_requirement")
            or ""
        ),
        required_source_tier=str(value.get("required_source_tier") or ""),
        required_currentness=str(value.get("required_currentness") or "current"),
        official_current_rules=_mapping(
            value.get("official_current_rules")
            or value.get("official_current_rules_mapping")
        ),
        origin_phase=str(value.get("origin_phase") or "ag96i3m1"),
        origin_action=str(value.get("origin_action") or ""),
        origin_record_type=str(
            value.get("origin_record_type") or "evidence_ledger_intake_binding"
        ),
        origin_schema_version=str(
            value.get("origin_schema_version") or SCHEMA_VERSION
        ),
        idempotency_key=_text(value.get("idempotency_key"), limit=220),
        deduplication_basis=_string_tuple(value.get("deduplication_basis")),
        final_evidence=bool(value.get("final_evidence")),
        citation_eligible=bool(value.get("citation_eligible")),
        author_activation_allowed=bool(value.get("author_activation_allowed")),
    )


def _admission_blockers(
    candidate: Mapping[str, Any],
) -> tuple[EvidenceLedgerIntakeBlockerCode, ...]:
    blockers: list[EvidenceLedgerIntakeBlockerCode] = []
    status = _token(candidate.get("admission_review_status"))
    ready = candidate.get("admission_review_candidate_ready") is True
    if not ready or status != _ADMISSION_READY:
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.ADMISSION_REVIEW_CANDIDATE_NOT_READY
        )

    if _string_tuple(candidate.get("blocker_codes")):
        blockers.append(EvidenceLedgerIntakeBlockerCode.ADMISSION_REVIEW_BLOCKERS_PRESENT)

    identity = _mapping(candidate.get("candidate_identity_summary"))
    identity_statuses = {
        _token(identity.get("source_identity_status")),
        _token(identity.get("url_domain_comparison_posture")),
    }
    if "candidate_identity_unverified" in identity_statuses:
        blockers.append(EvidenceLedgerIntakeBlockerCode.CANDIDATE_IDENTITY_UNVERIFIED)
    if identity_statuses.intersection(_IDENTITY_MISMATCH_STATUSES):
        blockers.append(EvidenceLedgerIntakeBlockerCode.CANDIDATE_IDENTITY_MISMATCH)
    if not identity_statuses.intersection(_ACCEPTABLE_IDENTITY_STATUSES):
        blockers.append(EvidenceLedgerIntakeBlockerCode.CANDIDATE_IDENTITY_MISMATCH)

    verification = _mapping(candidate.get("verification_summary"))
    if _token(verification.get("verification_status")) != (
        _VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    ):
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CURRENTNESS_OR_RELEVANCE_UNCLEAR
        )
    if _token(verification.get("official_source_status")) != _OFFICIAL_SOURCE_SUPPORTED:
        blockers.append(EvidenceLedgerIntakeBlockerCode.CANDIDATE_READ_OBSERVATION_INCOMPLETE)
    if _token(verification.get("currentness_posture")) not in {
        "",
        "currentness_supported",
    }:
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CURRENTNESS_OR_RELEVANCE_UNCLEAR
        )
    if _token(verification.get("relevance_posture")) not in {
        "",
        "relevance_supported",
    }:
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CURRENTNESS_OR_RELEVANCE_UNCLEAR
        )

    read_summary = _mapping(candidate.get("read_observation_summary"))
    if _token(read_summary.get("read_posture")) != _READ_OBSERVATION_READY:
        blockers.append(EvidenceLedgerIntakeBlockerCode.CANDIDATE_READ_OBSERVATION_INCOMPLETE)
    if read_summary.get("raw_page_text_retained") is not False:
        blockers.append(EvidenceLedgerIntakeBlockerCode.RAW_PRIVATE_PAYLOAD_RETENTION_BLOCKED)

    if candidate.get("custody_metadata_complete") is not True:
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CUSTODY_METADATA_INCOMPLETE
        )
    if _downstream_activation_requested(candidate):
        blockers.append(EvidenceLedgerIntakeBlockerCode.DOWNSTREAM_ACTIVATION_REQUESTED)
    if _contains_private_material(candidate):
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.RAW_PRIVATE_PAYLOAD_RETENTION_BLOCKED
        )
    return tuple(blockers)


def _binding_blockers(
    binding: EvidenceLedgerIntakeBinding,
) -> tuple[EvidenceLedgerIntakeBlockerCode, ...]:
    blockers: list[EvidenceLedgerIntakeBlockerCode] = []
    if not _token(binding.requirement_id):
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_REQUIREMENT_ID)
    if not _token(binding.candidate_id):
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_CANDIDATE_ID)
    if not _observation_id(binding):
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_OBSERVATION_ID_OR_REF)
    source_obligation = _token(binding.source_obligation)
    if not source_obligation:
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_SOURCE_OBLIGATION)
    elif source_obligation not in _SUPPORTED_SOURCE_OBLIGATIONS:
        blockers.append(EvidenceLedgerIntakeBlockerCode.UNSUPPORTED_SOURCE_OBLIGATION)
    if not _token(binding.required_source_class):
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_REQUIRED_SOURCE_CLASS)
    if not (_text(binding.idempotency_key, limit=220) or binding.deduplication_basis):
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.MISSING_IDEMPOTENCY_OR_DEDUP_BASIS
        )
    if not _token(binding.origin_action):
        blockers.append(EvidenceLedgerIntakeBlockerCode.MISSING_ORIGIN_ACTION)
    if binding.final_evidence or binding.citation_eligible or binding.author_activation_allowed:
        blockers.append(EvidenceLedgerIntakeBlockerCode.DOWNSTREAM_ACTIVATION_REQUESTED)
    if source_obligation == _OFFICIAL_CURRENT:
        blockers.extend(_official_current_mapping_blockers(binding))
    if _contains_private_material(binding.official_current_rules):
        blockers.append(
            EvidenceLedgerIntakeBlockerCode.RAW_PRIVATE_PAYLOAD_RETENTION_BLOCKED
        )
    return tuple(blockers)


def _official_current_mapping_blockers(
    binding: EvidenceLedgerIntakeBinding,
) -> tuple[EvidenceLedgerIntakeBlockerCode, ...]:
    mapping = _mapping(binding.official_current_rules)
    if not mapping:
        return (
            EvidenceLedgerIntakeBlockerCode.MISSING_OFFICIAL_CURRENT_RULES_MAPPING,
        )
    required_source_class = _token(
        mapping.get("required_source_class") or mapping.get("source_class")
    )
    required_tier = _token(
        mapping.get("required_source_tier") or mapping.get("source_tier")
    )
    requirement_kind = _token(mapping.get("requirement_kind") or mapping.get("kind"))
    source_obligation = _token(mapping.get("source_obligation")) or _OFFICIAL_CURRENT
    currentness = _token(
        mapping.get("required_currentness") or mapping.get("currentness")
    )
    if (
        required_source_class != _OFFICIAL_CURRENT_RULES
        or _token(binding.required_source_class) != _OFFICIAL_CURRENT_RULES
        or required_tier != "official"
        or _token(binding.required_source_tier) != "official"
        or currentness not in _CURRENTNESS_VALUES
        or _token(binding.required_currentness) not in _CURRENTNESS_VALUES
        or source_obligation != _OFFICIAL_CURRENT
        or (requirement_kind and requirement_kind != _OFFICIAL_CURRENT)
    ):
        return (
            EvidenceLedgerIntakeBlockerCode.OFFICIAL_CURRENT_RULES_MAPPING_MISMATCH,
        )
    return ()


def _observation_payload(
    *,
    admission_review_candidate: Mapping[str, Any],
    binding: EvidenceLedgerIntakeBinding,
    observation_id: str,
) -> dict[str, Any]:
    identity = _mapping(admission_review_candidate.get("candidate_identity_summary"))
    read_summary = _mapping(admission_review_candidate.get("read_observation_summary"))
    requirement_id = _token(binding.requirement_id)
    candidate_id = _token(binding.candidate_id)
    source_class = _token(binding.required_source_class)
    source_tier = _token(binding.required_source_tier)
    currentness = _token(binding.required_currentness)
    if currentness == _OFFICIAL_CURRENT:
        currentness = "current"
    origin_ref = f"{_token(binding.origin_phase)}:{_token(binding.origin_action)}"
    requirement = {
        "requirement_id": requirement_id,
        "requirement_kind": _OFFICIAL_CURRENT,
        "origin_ref": origin_ref,
        "required_source_class": source_class,
        "required_source_tier": source_tier,
        "required_currentness": currentness or "current",
        "linked_candidate_ids": [candidate_id],
    }
    candidate = {
        "candidate_id": candidate_id,
        "url": (
            _text(identity.get("resolved_url"), limit=500)
            or _text(identity.get("attempted_url"), limit=500)
            or _text(identity.get("candidate_url"), limit=500)
        ),
        "title": _text(read_summary.get("title"), limit=300),
        "domain": (
            _text(identity.get("observation_domain"), limit=160)
            or _text(identity.get("resolved_domain"), limit=160)
            or _text(identity.get("candidate_domain"), limit=160)
        ),
        "source_label": (
            "AG-96I3M1 explicit EvidenceLedger intake binding "
            f"{requirement_id} {candidate_id}"
        ),
        "provider_name": "ag96i3m1_offline_intake_adapter",
        "provider_role": "admission_review_diagnostic_intake",
        "retrieval_pass_id": _text(binding.observation_ref, limit=220),
        "action_ref": _token(binding.origin_action),
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness or "current",
        "readable_status": _token(read_summary.get("read_status")) or "readable",
        "fetchable_status": _fetchable_status(read_summary),
        "disposition": "accepted",
        "record_kind": "fact",
        "requirement_id": requirement_id,
        "eligible_for_stronger_obligation": (
            source_class == _OFFICIAL_CURRENT_RULES
            and source_tier in _CURRENT_SOURCE_TIERS
            and currentness in _CURRENTNESS_VALUES
        ),
        "final_evidence_eligible": False,
        "reason": "ag96i3m1_ready_admission_review_candidate_with_explicit_binding",
    }
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "record_type": OBSERVATION_RECORD_TYPE,
        "origin_phase": _token(binding.origin_phase),
        "origin_action": _token(binding.origin_action),
        "origin_record_type": _token(binding.origin_record_type),
        "origin_schema_version": _token(binding.origin_schema_version),
        "source_obligation": _token(binding.source_obligation),
        "idempotency_key": _text(binding.idempotency_key, limit=220),
        "deduplication_basis": list(_string_tuple(binding.deduplication_basis)),
        "observation_ref": _text(binding.observation_ref, limit=220),
        "official_current_rules": _official_current_rules_projection(binding),
        "final_evidence": False,
        "citation_eligible": False,
        "author_activation_allowed": False,
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_updated": False,
        "provider_search_fetch_read_model_behavior_changed": False,
        "live_validation_not_run": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": OBSERVATION_RECORD_TYPE,
        "observation_id": observation_id,
        "observation_source": OBSERVATION_SOURCE,
        "owner": "EvidenceLedgerIntakeAdapter",
        "requirements": [requirement],
        "candidates": [candidate],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "candidate_id": candidate_id,
                "link_reason": "ag96i3m1_explicit_intake_binding",
                "link_status": "accepted",
            }
        ],
        "ag96i3m1_intake_adapter": metadata,
    }


def _result_projection(
    *,
    admission_review_candidate: Mapping[str, Any],
    binding: EvidenceLedgerIntakeBinding,
    blocker_codes: Sequence[EvidenceLedgerIntakeBlockerCode],
) -> dict[str, Any]:
    observation_id = _observation_id(binding)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "owner": "EvidenceLedgerIntakeAdapter",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "runtime_activation": False,
        "intake_observation_created": not bool(blocker_codes),
        "intake_status": (
            EvidenceLedgerIntakeStatus.BLOCKED.value
            if blocker_codes
            else EvidenceLedgerIntakeStatus.OBSERVATION_READY.value
        ),
        "blocker_codes": [item.value for item in blocker_codes],
        "admission_review_status": _token(
            admission_review_candidate.get("admission_review_status")
        ),
        "admission_review_candidate_ready": (
            admission_review_candidate.get("admission_review_candidate_ready") is True
        ),
        "recommended_next_step": _token(
            admission_review_candidate.get("recommended_next_step")
        ),
        "requirement_id": _token(binding.requirement_id),
        "candidate_id": _token(binding.candidate_id),
        "observation_id": observation_id,
        "observation_ref": _text(binding.observation_ref, limit=220),
        "source_obligation": _token(binding.source_obligation),
        "required_source_class": _token(binding.required_source_class),
        "required_source_tier": _token(binding.required_source_tier),
        "required_currentness": _token(binding.required_currentness),
        "origin_phase": _token(binding.origin_phase),
        "origin_action": _token(binding.origin_action),
        "origin_record_type": _token(binding.origin_record_type),
        "origin_schema_version": _token(binding.origin_schema_version),
        "idempotency_key": _text(binding.idempotency_key, limit=220),
        "deduplication_basis": list(_string_tuple(binding.deduplication_basis)),
        "official_current_rules": _official_current_rules_projection(binding),
        "behavior_boundary_flags": _behavior_boundary_flags(),
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _downstream_activation_requested(candidate: Mapping[str, Any]) -> bool:
    flags = _mapping(candidate.get("non_authoritative_boundary_flags"))
    for key in (
        "final_evidence",
        "citation_eligible",
        "author_activation_allowed",
        "evidence_ledger_admitted",
        "sufficiency_judgment_rechecked",
        "final_answer_packet_updated",
    ):
        if candidate.get(key) is True or flags.get(key) is True:
            return True
    return False


def _contains_private_material(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_token = _token(key)
            if key_token in _PRIVATE_CONTENT_KEYS and _has_content(item):
                return True
            if any(key_token.endswith(suffix) for suffix in _RETENTION_FLAG_SUFFIXES):
                if item is True:
                    return True
                if key_token == "final_text_included" and item is True:
                    return True
            if _contains_private_material(item):
                return True
    elif isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_private_material(item) for item in value)
    return False


def _has_content(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return bool(value)
    return True


def _official_current_rules_projection(
    binding: EvidenceLedgerIntakeBinding,
) -> dict[str, Any]:
    mapping = _mapping(binding.official_current_rules)
    return _compact(
        {
            "source_obligation": _token(
                mapping.get("source_obligation") or binding.source_obligation
            ),
            "requirement_kind": _token(
                mapping.get("requirement_kind") or mapping.get("kind")
            ),
            "required_source_class": _token(
                mapping.get("required_source_class") or mapping.get("source_class")
            ),
            "required_source_tier": _token(
                mapping.get("required_source_tier") or mapping.get("source_tier")
            ),
            "required_currentness": _token(
                mapping.get("required_currentness") or mapping.get("currentness")
            ),
            "requirement_id": _token(
                mapping.get("requirement_id") or binding.requirement_id
            ),
        }
    )


def _fetchable_status(read_summary: Mapping[str, Any]) -> str:
    fetch_status = _token(read_summary.get("fetch_status"))
    if fetch_status in {"fetched", "fetch_success", "ok", "success"}:
        return "fetchable"
    return fetch_status or "fetchable"


def _observation_id(binding: EvidenceLedgerIntakeBinding) -> str:
    return _token(binding.observation_id) or _token(binding.observation_ref)


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        "adapter_only": True,
        "runtime_activation": False,
        "evidence_ledger_reducer_payload_created": True,
        "evidence_ledger_mutation_requires_runkernel_reducer": True,
        "final_evidence": False,
        "citation_eligible": False,
        "author_activation_allowed": False,
        "sufficiency_judgment_rechecked": False,
        "final_answer_packet_updated": False,
        "provider_routing_changed": False,
        "provider_selection_changed": False,
        "query_generation_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "search_executed": False,
        "fetch_executed": False,
        "model_called": False,
        "live_validation_not_run": True,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_admission_review_projection_only": True,
        "raw_text_retained": False,
        "verifier_text_retained": False,
        "supported_excerpts_retained": False,
        "provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "secrets_retained": False,
        "db_rows_retained": False,
        "private_logs_retained": False,
    }


def _dedupe_blockers(
    blockers: Sequence[EvidenceLedgerIntakeBlockerCode],
) -> list[EvidenceLedgerIntakeBlockerCode]:
    out: list[EvidenceLedgerIntakeBlockerCode] = []
    for blocker in blockers:
        if blocker not in out:
            out.append(blocker)
    return out


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence):
        values = tuple(str(item) for item in value)
    else:
        return ()
    out: list[str] = []
    for item in values:
        token = _token(item)
        if token and token not in out:
            out.append(token)
    return tuple(out)


def _text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _token(value: Any, *, limit: int = 160) -> str:
    text = _text(value, limit=limit)
    if not text:
        return ""
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "OBSERVATION_RECORD_TYPE",
    "OBSERVATION_SOURCE",
    "RECORD_TYPE",
    "SCHEMA_VERSION",
    "EvidenceLedgerIntakeAdapterResult",
    "EvidenceLedgerIntakeBinding",
    "EvidenceLedgerIntakeBlockerCode",
    "EvidenceLedgerIntakeStatus",
    "build_evidence_ledger_intake_observation_from_admission_review",
]
