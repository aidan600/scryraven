"""Offline EvidenceLedger admission-review diagnostics for AG-96I3L.

This helper consumes an AG-96I3J fetch/read currentness verification packet plus
an AG-96I3K durable sanitized read-observation projection and produces a
non-authoritative admission-review candidate.

It is diagnostic only. It does not reduce an EvidenceLedger observation, mutate
canonical custody state, activate citation eligibility, activate Author-facing
authority, call providers, fetch/read pages, invoke models, or change product
behavior. Actual EvidenceLedger intake remains deferred to a later licensed
phase.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.followup_deliberation import clean_text, clean_token

SCHEMA_VERSION = "ag96i3l_evidence_ledger_admission_review_diagnostics_v1"
RECORD_TYPE = "evidence_ledger_admission_review_candidate_diagnostics"

VERIFIED_OFFICIAL_CURRENT_RELEVANCE = "verified_official_current_relevance"
OFFICIAL_BUT_CURRENTNESS_UNCLEAR = "official_but_currentness_unclear"
OFFICIAL_BUT_REQUIRED_TERMS_MISSING = "official_but_required_terms_missing"
OFFICIAL_BUT_VALUE_TERMS_MISSING = "official_but_value_terms_missing"

READ_OBSERVATION_READY = "read_observation_ready"
CANDIDATE_URL_MATCH = "candidate_url_match"
CANDIDATE_DOMAIN_MATCH = "candidate_domain_match"
RESOLVED_URL_DIFFERS_SAME_DOMAIN = "resolved_url_differs_same_domain"
CANDIDATE_IDENTITY_UNVERIFIED = "candidate_identity_unverified"
CANDIDATE_URL_MISMATCH = "candidate_url_mismatch"
CANDIDATE_DOMAIN_MISMATCH = "candidate_domain_mismatch"

OFFICIAL_SOURCE_SUPPORTED = "official_source_supported"

_ACCEPTABLE_IDENTITY_STATUSES = frozenset(
    {
        CANDIDATE_URL_MATCH,
        CANDIDATE_DOMAIN_MATCH,
        RESOLVED_URL_DIFFERS_SAME_DOMAIN,
        "official_equivalent_url_same_domain",
    }
)
_TEXT_RETENTION_KEYS = frozenset(
    {
        "text",
        "page_text",
        "raw_text",
        "source_text",
        "extracted_text",
        "supported_excerpt_fragments",
    }
)


class AdmissionReviewStatus(str, Enum):
    ADMISSION_REVIEW_CANDIDATE_READY = "admission_review_candidate_ready"
    VERIFIED_BUT_CUSTODY_METADATA_INCOMPLETE = (
        "verified_but_custody_metadata_incomplete"
    )
    VERIFICATION_NOT_SUCCESSFUL = "verification_not_successful"
    READ_OBSERVATION_UNAVAILABLE = "read_observation_unavailable"
    READ_OBSERVATION_UNREADABLE = "read_observation_unreadable"
    CANDIDATE_IDENTITY_UNVERIFIED = "candidate_identity_unverified"
    CANDIDATE_URL_MISMATCH = "candidate_url_mismatch"
    CANDIDATE_DOMAIN_MISMATCH = "candidate_domain_mismatch"
    CURRENTNESS_UNCLEAR = "currentness_unclear"
    RELEVANCE_UNCLEAR = "relevance_unclear"
    SOURCE_CLASS_UNCLEAR = "source_class_unclear"
    NOT_ATTEMPTED = "not_attempted"


class AdmissionReviewBlockerCode(str, Enum):
    MISSING_VERIFICATION_PACKET = "missing_verification_packet"
    MISSING_DURABLE_READ_PROJECTION = "missing_durable_read_projection"
    READ_OBSERVATION_NOT_READY = "read_observation_not_ready"
    READ_OBSERVATION_UNREADABLE = "read_observation_unreadable"
    VERIFICATION_NOT_SUCCESSFUL = "verification_not_successful"
    CANDIDATE_IDENTITY_UNVERIFIED = "candidate_identity_unverified"
    CANDIDATE_URL_MISMATCH = "candidate_url_mismatch"
    CANDIDATE_DOMAIN_MISMATCH = "candidate_domain_mismatch"
    CURRENTNESS_UNCLEAR = "currentness_unclear"
    RELEVANCE_UNCLEAR = "relevance_unclear"
    SOURCE_CLASS_UNCLEAR = "source_class_unclear"
    CUSTODY_METADATA_INCOMPLETE = "custody_metadata_incomplete"
    RAW_TEXT_RETENTION_BLOCKED = "raw_text_retention_blocked"


class RecommendedNextStep(str, Enum):
    EVIDENCE_LEDGER_INTAKE_REVIEW_LATER = "evidence_ledger_intake_review_later"
    REACQUIRE_CANDIDATE = "reacquire_candidate"
    RERUN_FETCH_READ_VERIFICATION = "rerun_fetch_read_verification"
    REQUIRE_STRONGER_IDENTITY_CHECK = "require_stronger_identity_check"
    REJECT_CANDIDATE = "reject_candidate"
    NOT_ATTEMPTED = "not_attempted"


@dataclass(frozen=True, slots=True)
class NonAuthoritativeBoundaryFlags:
    final_evidence: bool = False
    citation_eligible: bool = False
    evidence_ledger_admitted: bool = False
    author_activation_allowed: bool = False
    evidence_ledger_intake_performed: bool = False
    evidence_ledger_canonical_state_mutated: bool = False
    sufficiency_judgment_rechecked: bool = False
    final_answer_packet_updated: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "final_evidence": self.final_evidence,
            "citation_eligible": self.citation_eligible,
            "evidence_ledger_admitted": self.evidence_ledger_admitted,
            "author_activation_allowed": self.author_activation_allowed,
            "evidence_ledger_intake_performed": self.evidence_ledger_intake_performed,
            "evidence_ledger_canonical_state_mutated": (
                self.evidence_ledger_canonical_state_mutated
            ),
            "sufficiency_judgment_rechecked": self.sufficiency_judgment_rechecked,
            "final_answer_packet_updated": self.final_answer_packet_updated,
        }


@dataclass(frozen=True, slots=True)
class CustodyMetadataSummary:
    candidate_url_present: bool
    candidate_domain_present: bool
    observation_url_present: bool
    observation_domain_present: bool
    source_identity_present: bool
    source_class_or_official_posture_present: bool
    read_status_present: bool
    extracted_text_presence_recorded: bool
    durable_projection_omits_raw_text: bool
    non_authoritative_flags_present: bool

    @property
    def complete(self) -> bool:
        return all(self.to_dict().values())

    def to_dict(self) -> dict[str, bool]:
        return {
            "candidate_url_present": self.candidate_url_present,
            "candidate_domain_present": self.candidate_domain_present,
            "observation_url_present": self.observation_url_present,
            "observation_domain_present": self.observation_domain_present,
            "source_identity_present": self.source_identity_present,
            "source_class_or_official_posture_present": (
                self.source_class_or_official_posture_present
            ),
            "read_status_present": self.read_status_present,
            "extracted_text_presence_recorded": self.extracted_text_presence_recorded,
            "durable_projection_omits_raw_text": self.durable_projection_omits_raw_text,
            "non_authoritative_flags_present": self.non_authoritative_flags_present,
        }


@dataclass(frozen=True, slots=True)
class AdmissionReviewInput:
    verification_packet: Mapping[str, Any]
    durable_read_observation_projection: Mapping[str, Any]
    review_requirements: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AdmissionReviewCandidate:
    status: AdmissionReviewStatus
    blocker_codes: tuple[AdmissionReviewBlockerCode, ...]
    recommended_next_step: RecommendedNextStep
    candidate_identity_summary: Mapping[str, Any]
    verification_summary: Mapping[str, Any]
    read_observation_summary: Mapping[str, Any]
    custody_metadata_summary: CustodyMetadataSummary
    boundary_flags: NonAuthoritativeBoundaryFlags

    def to_dict(self) -> dict[str, Any]:
        blockers = [item.value for item in self.blocker_codes]
        boundary = self.boundary_flags.to_dict()
        payload = {
            "schema_version": SCHEMA_VERSION,
            "record_type": RECORD_TYPE,
            "owner": "EvidenceLedgerAdmissionReviewDiagnostics",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "diagnostic_only": True,
            "admission_review_status": self.status.value,
            "admission_review_candidate_ready": (
                self.status
                is AdmissionReviewStatus.ADMISSION_REVIEW_CANDIDATE_READY
            ),
            "blocker_codes": blockers,
            "reason_codes": blockers,
            "recommended_next_step": self.recommended_next_step.value,
            "candidate_identity_summary": dict(self.candidate_identity_summary),
            "verification_summary": dict(self.verification_summary),
            "read_observation_summary": dict(self.read_observation_summary),
            "custody_metadata_summary": self.custody_metadata_summary.to_dict(),
            "custody_metadata_complete": self.custody_metadata_summary.complete,
            "non_authoritative_boundary_flags": boundary,
            "evidence_boundary": _evidence_boundary(),
            "raw_private_payload_redaction_posture": _redaction_posture(),
            "durable_projection": {
                "schema_version": SCHEMA_VERSION,
                "record_type": RECORD_TYPE,
                "admission_review_status": self.status.value,
                "admission_review_candidate_ready": (
                    self.status
                    is AdmissionReviewStatus.ADMISSION_REVIEW_CANDIDATE_READY
                ),
                "blocker_codes": blockers,
                "recommended_next_step": self.recommended_next_step.value,
                "candidate_identity_summary": dict(self.candidate_identity_summary),
                "verification_summary": dict(self.verification_summary),
                "read_observation_summary": dict(self.read_observation_summary),
                "custody_metadata_summary": self.custody_metadata_summary.to_dict(),
                "custody_metadata_complete": self.custody_metadata_summary.complete,
                "non_authoritative_boundary_flags": boundary,
                "raw_page_text_retained": False,
            },
            "final_evidence": boundary["final_evidence"],
            "citation_eligible": boundary["citation_eligible"],
            "evidence_ledger_admitted": boundary["evidence_ledger_admitted"],
            "author_activation_allowed": boundary["author_activation_allowed"],
        }
        return payload


def build_evidence_ledger_admission_review_candidate(
    *,
    fetch_read_currentness_verification: Mapping[str, Any] | None = None,
    durable_read_observation_projection: Mapping[str, Any] | None = None,
    sanitized_read_observation: Mapping[str, Any] | None = None,
    review_requirements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a non-authoritative admission-review candidate diagnostic.

    ``sanitized_read_observation`` is accepted only as a convenience conversion
    path. When supplied, only its ``durable_projection`` region is consumed; the
    ephemeral verifier text is ignored and never copied.
    """

    inputs = AdmissionReviewInput(
        verification_packet=_mapping(fetch_read_currentness_verification),
        durable_read_observation_projection=_durable_projection(
            durable_read_observation_projection,
            sanitized_read_observation=sanitized_read_observation,
        ),
        review_requirements=_mapping(review_requirements),
    )
    candidate = _review(inputs)
    return candidate.to_dict()


def as_admission_review_read_projection(
    sanitized_read_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the AG-96I3K durable projection for admission-review diagnostics."""

    observation = _mapping(sanitized_read_observation)
    durable = observation.get("durable_projection")
    return dict(durable) if isinstance(durable, Mapping) else {}


def _review(inputs: AdmissionReviewInput) -> AdmissionReviewCandidate:
    verification = inputs.verification_packet
    read_projection = inputs.durable_read_observation_projection
    requirements = inputs.review_requirements

    identity = _candidate_identity_summary(verification, read_projection)
    verification_summary = _verification_summary(verification, requirements)
    read_summary = _read_observation_summary(read_projection)
    custody = _custody_metadata_summary(
        verification=verification,
        read_projection=read_projection,
        identity=identity,
    )

    blockers = _blockers(
        verification=verification,
        read_projection=read_projection,
        verification_summary=verification_summary,
        read_summary=read_summary,
        custody=custody,
    )
    status = _status_for_blockers(blockers, verification=verification)
    return AdmissionReviewCandidate(
        status=status,
        blocker_codes=tuple(blockers),
        recommended_next_step=_recommended_next_step(status),
        candidate_identity_summary=identity,
        verification_summary=verification_summary,
        read_observation_summary=read_summary,
        custody_metadata_summary=custody,
        boundary_flags=NonAuthoritativeBoundaryFlags(),
    )


def _blockers(
    *,
    verification: Mapping[str, Any],
    read_projection: Mapping[str, Any],
    verification_summary: Mapping[str, Any],
    read_summary: Mapping[str, Any],
    custody: CustodyMetadataSummary,
) -> list[AdmissionReviewBlockerCode]:
    blockers: list[AdmissionReviewBlockerCode] = []
    if not verification:
        blockers.append(AdmissionReviewBlockerCode.MISSING_VERIFICATION_PACKET)
    if not read_projection:
        blockers.append(AdmissionReviewBlockerCode.MISSING_DURABLE_READ_PROJECTION)

    identity_values = {
        clean_token(verification.get("source_identity_status")),
        clean_token(read_projection.get("url_domain_comparison_posture")),
    }
    if CANDIDATE_DOMAIN_MISMATCH in identity_values:
        blockers.append(AdmissionReviewBlockerCode.CANDIDATE_DOMAIN_MISMATCH)
    if CANDIDATE_URL_MISMATCH in identity_values:
        blockers.append(AdmissionReviewBlockerCode.CANDIDATE_URL_MISMATCH)
    if CANDIDATE_IDENTITY_UNVERIFIED in identity_values:
        blockers.append(AdmissionReviewBlockerCode.CANDIDATE_IDENTITY_UNVERIFIED)

    read_posture = clean_token(read_summary.get("read_posture"))
    if read_projection and read_posture != READ_OBSERVATION_READY:
        if read_posture == "not_attempted":
            blockers.append(AdmissionReviewBlockerCode.READ_OBSERVATION_NOT_READY)
        elif read_posture not in {CANDIDATE_URL_MISMATCH, CANDIDATE_DOMAIN_MISMATCH}:
            blockers.append(AdmissionReviewBlockerCode.READ_OBSERVATION_UNREADABLE)

    verification_status = clean_token(verification_summary.get("verification_status"))
    if verification and verification_status != VERIFIED_OFFICIAL_CURRENT_RELEVANCE:
        if verification_status == OFFICIAL_BUT_CURRENTNESS_UNCLEAR:
            blockers.append(AdmissionReviewBlockerCode.CURRENTNESS_UNCLEAR)
        elif verification_status in {
            OFFICIAL_BUT_REQUIRED_TERMS_MISSING,
            OFFICIAL_BUT_VALUE_TERMS_MISSING,
        }:
            blockers.append(AdmissionReviewBlockerCode.RELEVANCE_UNCLEAR)
        elif verification_status not in {
            CANDIDATE_URL_MISMATCH,
            CANDIDATE_DOMAIN_MISMATCH,
        }:
            blockers.append(AdmissionReviewBlockerCode.VERIFICATION_NOT_SUCCESSFUL)

    official_status = clean_token(verification_summary.get("official_source_status"))
    if verification and official_status != OFFICIAL_SOURCE_SUPPORTED:
        blockers.append(AdmissionReviewBlockerCode.SOURCE_CLASS_UNCLEAR)

    if read_projection and not custody.durable_projection_omits_raw_text:
        blockers.append(AdmissionReviewBlockerCode.RAW_TEXT_RETENTION_BLOCKED)
    if verification and read_projection and not custody.complete:
        blockers.append(AdmissionReviewBlockerCode.CUSTODY_METADATA_INCOMPLETE)

    return _dedupe(blockers)


def _status_for_blockers(
    blockers: Sequence[AdmissionReviewBlockerCode],
    *,
    verification: Mapping[str, Any],
) -> AdmissionReviewStatus:
    if not blockers:
        return AdmissionReviewStatus.ADMISSION_REVIEW_CANDIDATE_READY
    if AdmissionReviewBlockerCode.MISSING_VERIFICATION_PACKET in blockers and not verification:
        return AdmissionReviewStatus.NOT_ATTEMPTED
    if AdmissionReviewBlockerCode.MISSING_DURABLE_READ_PROJECTION in blockers:
        return AdmissionReviewStatus.READ_OBSERVATION_UNAVAILABLE
    if AdmissionReviewBlockerCode.CANDIDATE_DOMAIN_MISMATCH in blockers:
        return AdmissionReviewStatus.CANDIDATE_DOMAIN_MISMATCH
    if AdmissionReviewBlockerCode.CANDIDATE_URL_MISMATCH in blockers:
        return AdmissionReviewStatus.CANDIDATE_URL_MISMATCH
    if AdmissionReviewBlockerCode.CANDIDATE_IDENTITY_UNVERIFIED in blockers:
        return AdmissionReviewStatus.CANDIDATE_IDENTITY_UNVERIFIED
    if AdmissionReviewBlockerCode.READ_OBSERVATION_UNREADABLE in blockers:
        return AdmissionReviewStatus.READ_OBSERVATION_UNREADABLE
    if AdmissionReviewBlockerCode.CURRENTNESS_UNCLEAR in blockers:
        return AdmissionReviewStatus.CURRENTNESS_UNCLEAR
    if AdmissionReviewBlockerCode.RELEVANCE_UNCLEAR in blockers:
        return AdmissionReviewStatus.RELEVANCE_UNCLEAR
    if AdmissionReviewBlockerCode.SOURCE_CLASS_UNCLEAR in blockers:
        return AdmissionReviewStatus.SOURCE_CLASS_UNCLEAR
    if AdmissionReviewBlockerCode.VERIFICATION_NOT_SUCCESSFUL in blockers:
        return AdmissionReviewStatus.VERIFICATION_NOT_SUCCESSFUL
    return AdmissionReviewStatus.VERIFIED_BUT_CUSTODY_METADATA_INCOMPLETE


def _recommended_next_step(
    status: AdmissionReviewStatus,
) -> RecommendedNextStep:
    if status is AdmissionReviewStatus.ADMISSION_REVIEW_CANDIDATE_READY:
        return RecommendedNextStep.EVIDENCE_LEDGER_INTAKE_REVIEW_LATER
    if status in {
        AdmissionReviewStatus.CANDIDATE_URL_MISMATCH,
        AdmissionReviewStatus.CANDIDATE_DOMAIN_MISMATCH,
    }:
        return RecommendedNextStep.REACQUIRE_CANDIDATE
    if status is AdmissionReviewStatus.CANDIDATE_IDENTITY_UNVERIFIED:
        return RecommendedNextStep.REQUIRE_STRONGER_IDENTITY_CHECK
    if status in {
        AdmissionReviewStatus.CURRENTNESS_UNCLEAR,
        AdmissionReviewStatus.RELEVANCE_UNCLEAR,
    }:
        return RecommendedNextStep.RERUN_FETCH_READ_VERIFICATION
    if status is AdmissionReviewStatus.SOURCE_CLASS_UNCLEAR:
        return RecommendedNextStep.REQUIRE_STRONGER_IDENTITY_CHECK
    if status is AdmissionReviewStatus.NOT_ATTEMPTED:
        return RecommendedNextStep.NOT_ATTEMPTED
    if status in {
        AdmissionReviewStatus.READ_OBSERVATION_UNAVAILABLE,
        AdmissionReviewStatus.READ_OBSERVATION_UNREADABLE,
        AdmissionReviewStatus.VERIFIED_BUT_CUSTODY_METADATA_INCOMPLETE,
    }:
        return RecommendedNextStep.RERUN_FETCH_READ_VERIFICATION
    return RecommendedNextStep.REJECT_CANDIDATE


def _candidate_identity_summary(
    verification: Mapping[str, Any],
    read_projection: Mapping[str, Any],
) -> dict[str, Any]:
    attempted_url = _text_first(read_projection, verification, "attempted_url", limit=500)
    resolved_url = _text_first(read_projection, verification, "resolved_url", limit=500)
    attempted_domain = _text_first(
        read_projection,
        verification,
        "attempted_domain",
        limit=160,
    )
    resolved_domain = _text_first(
        read_projection,
        verification,
        "resolved_domain",
        "domain",
        limit=160,
    )
    return _compact(
        {
            "candidate_url": _text_first(
                verification,
                read_projection,
                "candidate_url",
                limit=500,
            ),
            "candidate_domain": _text_first(
                verification,
                read_projection,
                "candidate_domain",
                limit=160,
            ),
            "attempted_url": attempted_url,
            "resolved_url": resolved_url,
            "attempted_domain": attempted_domain,
            "resolved_domain": resolved_domain,
            "observation_domain": resolved_domain or attempted_domain,
            "source_identity_status": clean_token(
                verification.get("source_identity_status")
            ),
            "url_domain_comparison_posture": clean_token(
                read_projection.get("url_domain_comparison_posture")
            ),
        }
    )


def _verification_summary(
    verification: Mapping[str, Any],
    requirements: Mapping[str, Any],
) -> dict[str, Any]:
    status = clean_token(verification.get("verification_status"))
    source_identity_status = clean_token(verification.get("source_identity_status"))
    official_status = clean_token(verification.get("official_source_status"))
    source_class_required = clean_token(
        requirements.get("source_class_required")
        or requirements.get("required_source_class")
    )
    source_class_posture = "source_class_or_official_posture_unclear"
    if official_status == OFFICIAL_SOURCE_SUPPORTED:
        source_class_posture = "official_source_supported"
    currentness_posture = "currentness_supported" if (
        status == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    ) else "currentness_unclear"
    relevance_posture = "relevance_supported" if (
        status == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    ) else "relevance_unclear"
    candidate_fit_posture = "candidate_fit_supported" if (
        source_identity_status in _ACCEPTABLE_IDENTITY_STATUSES
        and status == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    ) else "candidate_fit_unclear"
    return _compact(
        {
            "verification_status": status,
            "candidate_accounting_status": clean_token(
                verification.get("candidate_accounting_status")
            ),
            "source_identity_status": source_identity_status,
            "official_source_status": official_status,
            "source_obligation": clean_token(verification.get("source_obligation")),
            "source_class_required": source_class_required,
            "source_class_posture": source_class_posture,
            "currentness_posture": currentness_posture,
            "relevance_posture": relevance_posture,
            "candidate_fit_posture": candidate_fit_posture,
            "recommended_next_step_from_verification": clean_token(
                verification.get("recommended_next_step")
            ),
            "unsupported_reason": clean_token(verification.get("unsupported_reason")),
        }
    )


def _read_observation_summary(read_projection: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "schema_version": clean_token(read_projection.get("schema_version")),
            "record_type": clean_token(read_projection.get("record_type")),
            "read_posture": clean_token(read_projection.get("read_posture")),
            "fetch_status": clean_token(read_projection.get("fetch_status")),
            "read_status": clean_token(read_projection.get("read_status")),
            "http_status": _http_status(read_projection.get("http_status")),
            "content_type": clean_text(read_projection.get("content_type"), limit=120),
            "media_type": clean_text(read_projection.get("media_type"), limit=120),
            "title": clean_text(read_projection.get("title"), limit=300),
            "detected_publication_date": clean_text(
                read_projection.get("detected_publication_date"),
                limit=80,
            ),
            "detected_updated_date": clean_text(
                read_projection.get("detected_updated_date"),
                limit=80,
            ),
            "extracted_text_present": _bool_or_none(
                read_projection.get("extracted_text_present")
            ),
            "extracted_text_char_count": _nonnegative_int(
                read_projection.get("extracted_text_char_count")
            ),
            "sanitized_text_char_count": _nonnegative_int(
                read_projection.get("sanitized_text_char_count")
            ),
            "extracted_text_truncated": _bool_or_none(
                read_projection.get("extracted_text_truncated")
            ),
            "raw_page_text_retained": _bool_or_none(
                read_projection.get("raw_page_text_retained")
            ),
        }
    )


def _custody_metadata_summary(
    *,
    verification: Mapping[str, Any],
    read_projection: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> CustodyMetadataSummary:
    redaction = _mapping(read_projection.get("raw_private_payload_redaction_posture"))
    durable_omits_text = (
        read_projection.get("raw_page_text_retained") is False
        and redaction.get("raw_page_text_retained") is False
        and redaction.get("durable_projection_retains_raw_page_text") is False
        and not any(key in read_projection for key in _TEXT_RETENTION_KEYS)
    )
    return CustodyMetadataSummary(
        candidate_url_present=bool(identity.get("candidate_url")),
        candidate_domain_present=bool(identity.get("candidate_domain")),
        observation_url_present=bool(
            identity.get("attempted_url") or identity.get("resolved_url")
        ),
        observation_domain_present=bool(identity.get("observation_domain")),
        source_identity_present=bool(verification.get("source_identity_status")),
        source_class_or_official_posture_present=bool(
            verification.get("official_source_status")
        ),
        read_status_present=bool(
            read_projection.get("read_posture")
            and read_projection.get("fetch_status")
            and read_projection.get("read_status")
        ),
        extracted_text_presence_recorded=(
            read_projection.get("extracted_text_present") is not None
        ),
        durable_projection_omits_raw_text=durable_omits_text,
        non_authoritative_flags_present=all(
            read_projection.get(field) is False
            for field in (
                "final_evidence",
                "citation_eligible",
                "evidence_ledger_admitted",
                "author_activation_allowed",
            )
        ),
    )


def _durable_projection(
    durable_read_observation_projection: Mapping[str, Any] | None,
    *,
    sanitized_read_observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(durable_read_observation_projection, Mapping):
        return _without_text_fields(durable_read_observation_projection)
    if isinstance(sanitized_read_observation, Mapping):
        return _without_text_fields(
            as_admission_review_read_projection(sanitized_read_observation)
        )
    return {}


def _evidence_boundary() -> dict[str, bool]:
    return {
        "admission_review_diagnostic_performed": True,
        "evidence_ledger_admission_review_candidate_only": True,
        "evidence_ledger_admission_performed": False,
        "evidence_ledger_intake_performed": False,
        "evidence_ledger_canonical_state_mutated": False,
        "candidate_is_final_evidence": False,
        "candidate_is_citation_eligible": False,
        "author_or_final_answer_activation_allowed": False,
        "actual_evidence_ledger_intake_deferred_to_later_phase": True,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_read_observation_projection_only": True,
        "verifier_input_text_consumed": False,
        "verifier_input_text_retained": False,
        "supported_excerpts_retained": False,
        "durable_projection_retains_raw_page_text": False,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_snippets_retained": False,
        "raw_page_text_retained": False,
        "raw_text_retained": False,
        "raw_prompts_retained": False,
        "raw_prompt_retained": False,
        "model_outputs_retained": False,
        "model_response_text_retained": False,
        "api_keys_retained": False,
        "env_values_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_traces_retained": False,
        "full_trace_retained": False,
    }


def _without_text_fields(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): item
        for key, item in dict(value).items()
        if clean_token(key) not in _TEXT_RETENTION_KEYS
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text_first(*sources_and_keys: Any, limit: int) -> str | None:
    search_sources: list[Mapping[str, Any]] = []
    keys: list[str] = []
    for item in sources_and_keys:
        if isinstance(item, Mapping):
            search_sources.append(item)
        elif isinstance(item, str):
            keys.append(item)
        elif isinstance(item, Sequence) and not isinstance(item, bytes):
            keys.extend(str(value) for value in item)
    for source in search_sources:
        for key in keys:
            text = clean_text(source.get(key), limit=limit)
            if text:
                return text
    return None


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _dedupe(
    blockers: Sequence[AdmissionReviewBlockerCode],
) -> list[AdmissionReviewBlockerCode]:
    out: list[AdmissionReviewBlockerCode] = []
    for item in blockers:
        if item not in out:
            out.append(item)
    return out


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _nonnegative_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _http_status(value: Any) -> int | None:
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if 100 <= status <= 599 else None


__all__ = [
    "AdmissionReviewBlockerCode",
    "AdmissionReviewCandidate",
    "AdmissionReviewInput",
    "AdmissionReviewStatus",
    "CANDIDATE_DOMAIN_MISMATCH",
    "CANDIDATE_IDENTITY_UNVERIFIED",
    "CANDIDATE_URL_MISMATCH",
    "CustodyMetadataSummary",
    "NonAuthoritativeBoundaryFlags",
    "RECORD_TYPE",
    "RecommendedNextStep",
    "SCHEMA_VERSION",
    "as_admission_review_read_projection",
    "build_evidence_ledger_admission_review_candidate",
]
