"""Deterministic D-prime assessment schema validation.

This module validates injected or fixture ``EvidenceRelativeSupportAssessment``
records only. It does not call models, parse live provider responses, create
support proposals, ask RunKernel for admission, admit SemanticObservation, bind
ComponentCoverage, create answer text, or claim product correctness.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

import core.dprime_negative_control_profile as negative_controls

ASSESSMENT_VALIDATOR_STATUS_AVAILABLE = "available"
ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED = "not reached"
ASSESSMENT_VALIDATOR_STATUS_UNAVAILABLE = "unavailable"

ASSESSMENT_SCHEMA_VALID = "assessment_schema_valid"
ASSESSMENT_SCHEMA_INVALID = "assessment_schema_invalid"
ASSESSMENT_ABSTAINED = "assessment_abstained"
ASSESSMENT_NON_SUPPORT = "assessment_non_support"
ASSESSMENT_CHALLENGE_RECOMMENDED = "assessment_challenge_recommended"
ASSESSMENT_VALIDATION_BLOCKED = "assessment_validation_blocked"

ASSESSMENT_VALIDATION_STATUSES = frozenset(
    {
        ASSESSMENT_SCHEMA_VALID,
        ASSESSMENT_SCHEMA_INVALID,
        ASSESSMENT_ABSTAINED,
        ASSESSMENT_NON_SUPPORT,
        ASSESSMENT_CHALLENGE_RECOMMENDED,
        ASSESSMENT_VALIDATION_BLOCKED,
    }
)

DIRECT_SUPPORT_RELATION = "directly_supports"
PARTIAL_SUPPORT_RELATION = "partially_supports"
SUPPORT_RELATIONS = frozenset(
    {
        DIRECT_SUPPORT_RELATION,
        PARTIAL_SUPPORT_RELATION,
        "absent",
        "scope_mismatch",
        "currentness_mismatch",
        "contradicts",
        "missing_qualifier",
        "weak_or_overclaim_risk",
        "abstained",
    }
)
VAGUE_SUPPORT_RELATIONS = frozenset(
    {
        "handled",
        "maybe_support",
        "ok",
        "pass",
        "passed",
        "support",
        "supported",
        "supports",
        "weak_support",
        "yes",
    }
)
NON_SUPPORT_RELATIONS = SUPPORT_RELATIONS - {
    DIRECT_SUPPORT_RELATION,
    PARTIAL_SUPPORT_RELATION,
}
CHALLENGE_RELATIONS = frozenset(
    {"currentness_mismatch", "contradicts", "weak_or_overclaim_risk"}
)


class DPrimeAssessmentValidationError(ValueError):
    """Raised when assessment material cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class EvidenceRelativeSupportAssessment:
    """Assessment-only fixture/injected record, never admitted support."""

    assessment_id: str
    assessment_digest: str
    preflight_ref: Mapping[str, Any]
    preflight_digest: str
    negative_control_profile_ref: Mapping[str, Any]
    negative_control_profile_digest: str
    source_proposition: str
    answer_component_claim: Mapping[str, Any]
    support_relation: str
    required_qualifiers: Sequence[str]
    observed_qualifiers: Sequence[str]
    missing_qualifiers: Sequence[str]
    scope_check: Mapping[str, Any]
    currentness_check: Mapping[str, Any]
    contradiction_check: Mapping[str, Any]
    evidential_adequacy_notes: str
    non_support_reason_when_not_direct: str
    producer_abstained: bool
    challenge_recommended: bool
    closed_surface_flags: Mapping[str, Any]
    preflight_status: str = "passed"
    negative_control_profile_status: str = (
        negative_controls.NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE
    )
    selector_ref: Mapping[str, Any] = field(default_factory=dict)
    component_ref: Mapping[str, Any] = field(default_factory=dict)
    source_obligation_ref: Mapping[str, Any] = field(default_factory=dict)
    model_review_ref: Mapping[str, Any] = field(default_factory=dict)
    fixture_review_ref: Mapping[str, Any] = field(default_factory=dict)
    prompt_license_ref: Mapping[str, Any] = field(default_factory=dict)
    fixture_license_ref: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _reject_forbidden_payload(
            self.to_dict(include_nonclaims=False),
            context="EvidenceRelativeSupportAssessment",
        )

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> EvidenceRelativeSupportAssessment:
        safe = _required_mapping(payload, "EvidenceRelativeSupportAssessment")
        return cls(
            assessment_id=_clean_text(safe.get("assessment_id"), limit=260) or "",
            assessment_digest=_clean_text(
                safe.get("assessment_digest"),
                limit=128,
            )
            or "",
            preflight_ref=_safe_mapping(safe.get("preflight_ref")),
            preflight_digest=_clean_text(safe.get("preflight_digest"), limit=128)
            or "",
            negative_control_profile_ref=_safe_mapping(
                safe.get("negative_control_profile_ref")
            ),
            negative_control_profile_digest=_clean_text(
                safe.get("negative_control_profile_digest"),
                limit=128,
            )
            or "",
            source_proposition=_clean_text(
                safe.get("source_proposition"),
                limit=1000,
            )
            or "",
            answer_component_claim=_safe_mapping(safe.get("answer_component_claim")),
            support_relation=_clean_token(safe.get("support_relation")) or "",
            required_qualifiers=_text_tuple(safe.get("required_qualifiers")),
            observed_qualifiers=_text_tuple(safe.get("observed_qualifiers")),
            missing_qualifiers=_text_tuple(safe.get("missing_qualifiers")),
            scope_check=_safe_mapping(safe.get("scope_check")),
            currentness_check=_safe_mapping(safe.get("currentness_check")),
            contradiction_check=_safe_mapping(safe.get("contradiction_check")),
            evidential_adequacy_notes=_clean_text(
                safe.get("evidential_adequacy_notes"),
                limit=1000,
            )
            or "",
            non_support_reason_when_not_direct=_clean_text(
                safe.get("non_support_reason_when_not_direct"),
                limit=1000,
            )
            or "",
            producer_abstained=safe.get("producer_abstained") is True,
            challenge_recommended=safe.get("challenge_recommended") is True,
            model_review_ref=_safe_mapping(safe.get("model_review_ref")),
            fixture_review_ref=_safe_mapping(safe.get("fixture_review_ref")),
            prompt_license_ref=_safe_mapping(safe.get("prompt_license_ref")),
            fixture_license_ref=_safe_mapping(safe.get("fixture_license_ref")),
            closed_surface_flags=_safe_mapping(safe.get("closed_surface_flags")),
            preflight_status=_clean_token(safe.get("preflight_status")) or "",
            negative_control_profile_status=(
                _clean_token(safe.get("negative_control_profile_status")) or ""
            ),
            selector_ref=_safe_mapping(safe.get("selector_ref")),
            component_ref=_safe_mapping(safe.get("component_ref")),
            source_obligation_ref=_safe_mapping(safe.get("source_obligation_ref")),
        )

    @property
    def is_admitted_support(self) -> bool:
        return False

    def to_dict(self, *, include_nonclaims: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "record_kind": "EvidenceRelativeSupportAssessment",
            "assessment_id": self.assessment_id,
            "assessment_digest": self.assessment_digest,
            "preflight_ref": dict(self.preflight_ref),
            "preflight_digest": self.preflight_digest,
            "preflight_status": self.preflight_status,
            "negative_control_profile_ref": dict(self.negative_control_profile_ref),
            "negative_control_profile_digest": self.negative_control_profile_digest,
            "negative_control_profile_status": self.negative_control_profile_status,
            "selector_ref": dict(self.selector_ref),
            "component_ref": dict(self.component_ref),
            "source_obligation_ref": dict(self.source_obligation_ref),
            "source_proposition": self.source_proposition,
            "answer_component_claim": dict(self.answer_component_claim),
            "support_relation": self.support_relation,
            "required_qualifiers": list(_text_tuple(self.required_qualifiers)),
            "observed_qualifiers": list(_text_tuple(self.observed_qualifiers)),
            "missing_qualifiers": list(_text_tuple(self.missing_qualifiers)),
            "scope_check": dict(self.scope_check),
            "currentness_check": dict(self.currentness_check),
            "contradiction_check": dict(self.contradiction_check),
            "evidential_adequacy_notes": self.evidential_adequacy_notes,
            "non_support_reason_when_not_direct": (
                self.non_support_reason_when_not_direct
            ),
            "producer_abstained": self.producer_abstained,
            "challenge_recommended": self.challenge_recommended,
            "model_review_ref": dict(self.model_review_ref),
            "fixture_review_ref": dict(self.fixture_review_ref),
            "prompt_license_ref": dict(self.prompt_license_ref),
            "fixture_license_ref": dict(self.fixture_license_ref),
            "closed_surface_flags": dict(self.closed_surface_flags),
        }
        if include_nonclaims:
            payload.update(
                {
                    "support_assessment_only": True,
                    "admitted_support": False,
                    "validated_support_proposal_created": False,
                    "run_kernel_support_admission_request_created": False,
                    "semantic_observation_created": False,
                    "component_coverage_created": False,
                    "answer_text_created": False,
                    "product_correctness_claimed": False,
                }
            )
        return _without_empty(payload)


@dataclass(frozen=True, slots=True)
class AssessmentValidationResult:
    """Deterministic assessment validation result, not support authority."""

    validation_status: str
    assessment_ref: Mapping[str, Any] = field(default_factory=dict)
    support_relation: str | None = None
    schema_valid: bool = False
    errors: Sequence[str] = field(default_factory=tuple)
    blockers: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    producer_abstained: bool = False
    challenge_recommended: bool = False

    def __post_init__(self) -> None:
        if self.validation_status not in ASSESSMENT_VALIDATION_STATUSES:
            raise DPrimeAssessmentValidationError(
                f"unsupported assessment validation status: {self.validation_status}"
            )
        _reject_forbidden_payload(
            self.assessment_ref,
            context="AssessmentValidationResult.assessment_ref",
        )

    @property
    def creates_support(self) -> bool:
        return False

    @property
    def creates_run_kernel_request(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "record_kind": "AssessmentValidationResult",
                "validation_status": self.validation_status,
                "assessment_ref": dict(self.assessment_ref),
                "support_relation": self.support_relation,
                "schema_valid": self.schema_valid,
                "errors": list(_text_tuple(self.errors, limit=500)),
                "blockers": list(_text_tuple(self.blockers, limit=500)),
                "warnings": list(_text_tuple(self.warnings, limit=500)),
                "producer_abstained": self.producer_abstained,
                "challenge_recommended": self.challenge_recommended,
                "validator_challenge_recommendation_only": (
                    self.challenge_recommended
                ),
                "support_created": False,
                "validated_support_proposal_created": False,
                "run_kernel_support_admission_request_created": False,
                "run_kernel_decision": "not made",
                "semantic_observation_created": False,
                "component_coverage_created": False,
                "citation_eligibility_claimed": False,
                "source_obligation_satisfaction_claimed": False,
                "answer_text_created": False,
                "product_correctness_claimed": False,
            }
        )


def assessment_validator_availability_status(
    negative_control_profile_validation: (
        negative_controls.NegativeControlProfileValidation | Mapping[str, Any] | None
    ),
) -> str:
    """Return CLI-safe validator availability after profile validation."""

    if negative_control_profile_validation is None:
        return ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED
    if isinstance(
        negative_control_profile_validation,
        negative_controls.NegativeControlProfileValidation,
    ):
        return (
            ASSESSMENT_VALIDATOR_STATUS_AVAILABLE
            if negative_control_profile_validation.passed
            else ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED
        )
    status = str(negative_control_profile_validation.get("profile_status") or "")
    if status == negative_controls.NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE:
        return ASSESSMENT_VALIDATOR_STATUS_AVAILABLE
    return ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED


def validate_evidence_relative_support_assessment(
    assessment: Mapping[str, Any] | EvidenceRelativeSupportAssessment,
    *,
    negative_control_profile: (
        Mapping[str, Any] | negative_controls.NegativeControlProfile | None
    ) = None,
) -> AssessmentValidationResult:
    """Validate an injected/fixture assessment and fail closed on ambiguity."""

    profile = (
        negative_controls.build_default_negative_control_profile()
        if negative_control_profile is None
        else negative_control_profile
    )
    profile_validation = negative_controls.validate_negative_control_profile(profile)
    if not profile_validation.passed:
        return AssessmentValidationResult(
            validation_status=ASSESSMENT_VALIDATION_BLOCKED,
            errors=tuple(profile_validation.errors),
            blockers=(
                profile_validation.blocker_detail
                or "D-prime negative-control profile failed validation",
            ),
        )

    try:
        if not isinstance(assessment, EvidenceRelativeSupportAssessment):
            _reject_forbidden_payload(
                assessment,
                context="EvidenceRelativeSupportAssessment",
            )
        candidate = (
            assessment
            if isinstance(assessment, EvidenceRelativeSupportAssessment)
            else EvidenceRelativeSupportAssessment.from_mapping(assessment)
        )
    except (DPrimeAssessmentValidationError, TypeError, ValueError) as exc:
        return AssessmentValidationResult(
            validation_status=ASSESSMENT_SCHEMA_INVALID,
            errors=(str(exc),),
            blockers=("EvidenceRelativeSupportAssessment failed safe coercion",),
        )

    errors = _assessment_validation_errors(
        candidate,
        profile_ref=profile_validation.profile_ref,
    )
    assessment_ref = _assessment_ref(candidate)
    if errors:
        return AssessmentValidationResult(
            validation_status=ASSESSMENT_SCHEMA_INVALID,
            assessment_ref=assessment_ref,
            support_relation=candidate.support_relation,
            schema_valid=False,
            errors=tuple(errors),
            blockers=("EvidenceRelativeSupportAssessment failed validation",),
            producer_abstained=candidate.producer_abstained,
            challenge_recommended=candidate.challenge_recommended,
        )

    status = ASSESSMENT_SCHEMA_VALID
    if candidate.producer_abstained or candidate.support_relation == "abstained":
        status = ASSESSMENT_ABSTAINED
    elif candidate.challenge_recommended:
        status = ASSESSMENT_CHALLENGE_RECOMMENDED
    elif candidate.support_relation in NON_SUPPORT_RELATIONS:
        status = ASSESSMENT_NON_SUPPORT

    return AssessmentValidationResult(
        validation_status=status,
        assessment_ref=assessment_ref,
        support_relation=candidate.support_relation,
        schema_valid=True,
        producer_abstained=candidate.producer_abstained,
        challenge_recommended=candidate.challenge_recommended,
    )


def assessment_digest(
    assessment: Mapping[str, Any] | EvidenceRelativeSupportAssessment,
) -> str:
    """Return a stable digest for an assessment mapping without raw material."""

    if isinstance(assessment, EvidenceRelativeSupportAssessment):
        payload = assessment.to_dict(include_nonclaims=False)
    else:
        payload = _required_mapping(assessment, "EvidenceRelativeSupportAssessment")
    payload = dict(payload)
    payload.pop("assessment_digest", None)
    payload.setdefault("record_kind", "EvidenceRelativeSupportAssessment")
    payload = _without_empty(payload)
    _reject_forbidden_payload(
        payload,
        context="EvidenceRelativeSupportAssessment.digest_payload",
    )
    encoded = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _assessment_validation_errors(
    assessment: EvidenceRelativeSupportAssessment,
    *,
    profile_ref: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    try:
        _reject_forbidden_payload(
            assessment.to_dict(include_nonclaims=False),
            context="EvidenceRelativeSupportAssessment",
        )
    except DPrimeAssessmentValidationError as exc:
        errors.append(str(exc))

    errors.extend(_required_field_errors(assessment))
    errors.extend(_digest_errors(assessment))
    errors.extend(_profile_ref_errors(assessment, profile_ref=profile_ref))
    errors.extend(_support_relation_errors(assessment))
    errors.extend(_mapping_errors(assessment))
    errors.extend(_closed_surface_flag_errors(assessment.closed_surface_flags))
    errors.extend(_rationale_errors(assessment))
    return errors


def _required_field_errors(
    assessment: EvidenceRelativeSupportAssessment,
) -> list[str]:
    errors: list[str] = []
    for field_name, value in (
        ("assessment_id", assessment.assessment_id),
        ("assessment_digest", assessment.assessment_digest),
        ("preflight_digest", assessment.preflight_digest),
        (
            "negative_control_profile_digest",
            assessment.negative_control_profile_digest,
        ),
        ("source_proposition", assessment.source_proposition),
        ("support_relation", assessment.support_relation),
        ("evidential_adequacy_notes", assessment.evidential_adequacy_notes),
    ):
        if not _clean_text(value, limit=1000):
            errors.append(f"{field_name} is missing")

    for field_name, value in (
        ("preflight_ref", assessment.preflight_ref),
        ("negative_control_profile_ref", assessment.negative_control_profile_ref),
        ("answer_component_claim", assessment.answer_component_claim),
        ("scope_check", assessment.scope_check),
        ("currentness_check", assessment.currentness_check),
        ("contradiction_check", assessment.contradiction_check),
        ("closed_surface_flags", assessment.closed_surface_flags),
    ):
        if not _safe_mapping(value):
            errors.append(f"{field_name} is missing")

    for field_name, value in (
        ("selector_ref", assessment.selector_ref),
        ("component_ref", assessment.component_ref),
        ("source_obligation_ref", assessment.source_obligation_ref),
    ):
        if not _safe_mapping(value):
            errors.append(f"{field_name} mapping is missing")

    if not (
        _safe_mapping(assessment.model_review_ref)
        or _safe_mapping(assessment.fixture_review_ref)
    ):
        errors.append("model_review_ref or fixture_review_ref is missing")
    if not (
        _safe_mapping(assessment.prompt_license_ref)
        or _safe_mapping(assessment.fixture_license_ref)
    ):
        errors.append("prompt_license_ref or fixture_license_ref is missing")
    if not isinstance(assessment.producer_abstained, bool):
        errors.append("producer_abstained must be boolean")
    if not isinstance(assessment.challenge_recommended, bool):
        errors.append("challenge_recommended must be boolean")
    return errors


def _digest_errors(assessment: EvidenceRelativeSupportAssessment) -> list[str]:
    errors: list[str] = []
    frame_digest = _clean_text(assessment.preflight_ref.get("frame_digest"), limit=128)
    if frame_digest and frame_digest != assessment.preflight_digest:
        errors.append("preflight_digest does not match preflight_ref frame_digest")
    profile_digest = _clean_text(
        assessment.negative_control_profile_ref.get("profile_digest"),
        limit=128,
    )
    if profile_digest and profile_digest != assessment.negative_control_profile_digest:
        errors.append(
            "negative_control_profile_digest does not match profile ref digest"
        )
    if assessment.assessment_digest:
        expected_digest = assessment_digest(assessment)
        if assessment.assessment_digest != expected_digest:
            errors.append("assessment_digest mismatch")
    return errors


def _profile_ref_errors(
    assessment: EvidenceRelativeSupportAssessment,
    *,
    profile_ref: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if assessment.preflight_status != "passed":
        errors.append("preflight_status is missing or failed")
    if (
        assessment.negative_control_profile_status
        != negative_controls.NEGATIVE_CONTROL_PROFILE_STATUS_AVAILABLE
    ):
        errors.append("negative_control_profile_status is missing or failed")

    expected_profile_id = _clean_text(profile_ref.get("profile_id"), limit=260)
    expected_digest = _clean_text(profile_ref.get("profile_digest"), limit=128)
    actual_profile_id = _clean_text(
        assessment.negative_control_profile_ref.get("profile_id"),
        limit=260,
    )
    actual_digest = assessment.negative_control_profile_digest
    if not expected_profile_id or actual_profile_id != expected_profile_id:
        errors.append("negative_control_profile_ref does not match validated profile")
    if not expected_digest or actual_digest != expected_digest:
        errors.append(
            "negative_control_profile_digest does not match validated profile"
        )
    return errors


def _support_relation_errors(
    assessment: EvidenceRelativeSupportAssessment,
) -> list[str]:
    errors: list[str] = []
    relation = _normalize_key(assessment.support_relation)
    if relation in VAGUE_SUPPORT_RELATIONS:
        errors.append(f"support_relation is vague or unsupported: {relation}")
        return errors
    if relation not in SUPPORT_RELATIONS:
        errors.append(f"support_relation is unsupported: {assessment.support_relation}")
        return errors

    if assessment.producer_abstained and relation != "abstained":
        errors.append("producer abstention cannot be treated as support")
    if relation == "abstained" and assessment.producer_abstained is not True:
        errors.append("abstained relation requires producer_abstained true")
    if relation != DIRECT_SUPPORT_RELATION and not _clean_text(
        assessment.non_support_reason_when_not_direct,
        limit=1000,
    ):
        errors.append("non_support_reason_when_not_direct is missing")
    if relation == DIRECT_SUPPORT_RELATION and assessment.missing_qualifiers:
        errors.append("direct support cannot have missing qualifiers")
    if relation == "missing_qualifier" and not assessment.missing_qualifiers:
        errors.append("missing_qualifier relation requires missing_qualifiers")
    if relation in CHALLENGE_RELATIONS and assessment.challenge_recommended is not True:
        errors.append(f"{relation} requires challenge_recommended true")
    return errors


def _mapping_errors(assessment: EvidenceRelativeSupportAssessment) -> list[str]:
    errors: list[str] = []
    component_id = _clean_text(assessment.component_ref.get("component_id"), limit=260)
    claim_component_id = _clean_text(
        assessment.answer_component_claim.get("component_id"),
        limit=260,
    )
    claim_text = _clean_text(assessment.answer_component_claim.get("claim"), limit=1000)
    if not component_id:
        errors.append("component_ref component_id is missing")
    if not claim_component_id or not claim_text:
        errors.append("answer_component_claim component_id/claim mapping is missing")
    if component_id and claim_component_id and component_id != claim_component_id:
        errors.append("answer_component_claim maps to the wrong component")
    if not _clean_text(assessment.selector_ref.get("selector_kind"), limit=160):
        errors.append("selector_ref selector_kind is missing")
    if not _text_tuple(
        assessment.source_obligation_ref.get("source_obligation_candidate_ids")
    ):
        errors.append("source_obligation_ref lane mapping is missing")

    relation = assessment.support_relation
    scope_status = _normalized_status(assessment.scope_check)
    currentness_status = _normalized_status(assessment.currentness_check)
    contradiction_status = _normalized_status(assessment.contradiction_check)
    if relation in {DIRECT_SUPPORT_RELATION, PARTIAL_SUPPORT_RELATION}:
        if scope_status not in {"passed", "in_scope", "matched"}:
            errors.append("support relation requires passed scope_check")
        if currentness_status not in {"passed", "current", "current_passed"}:
            errors.append("support relation requires passed currentness_check")
        if contradiction_status not in {"absent", "none", "not_contradicted"}:
            errors.append("support relation cannot carry a contradiction")
    if relation == "scope_mismatch" and scope_status not in {"scope_mismatch", "failed"}:
        errors.append("scope_mismatch relation requires failed scope_check")
    if (
        relation == "currentness_mismatch"
        and currentness_status
        not in {"currentness_mismatch", "wrong_effective_date", "stale", "failed"}
    ):
        errors.append("currentness_mismatch relation requires failed currentness_check")
    if relation == "contradicts" and contradiction_status not in {
        "contradicts",
        "contradicted",
        "failed",
    }:
        errors.append("contradicts relation requires contradiction_check failure")
    if relation == "weak_or_overclaim_risk" and contradiction_status in {
        "contradicts",
        "contradicted",
    }:
        errors.append("contradiction cannot be treated as weak support")
    return errors


def _closed_surface_flag_errors(flags: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    safe = _safe_mapping(flags)
    for key in _MANDATORY_CLOSED_SURFACE_FLAG_KEYS:
        if key not in safe:
            errors.append(f"closed_surface_flags missing {key}")
        elif safe.get(key) is not False:
            errors.append(f"closed_surface_flags must keep {key} false")
    return errors


def _rationale_errors(assessment: EvidenceRelativeSupportAssessment) -> list[str]:
    errors: list[str] = []
    notes = _normalize_words(assessment.evidential_adequacy_notes)
    if any(term in notes for term in _RATIONALE_ONLY_TERMS):
        errors.append(
            "evidential_adequacy_notes cannot rely on custody, lineage, URL, "
            "domain, snippet, source-class, or anchor-count rationale"
        )
    if assessment.support_relation in {
        DIRECT_SUPPORT_RELATION,
        PARTIAL_SUPPORT_RELATION,
    } and any(term in notes for term in _CURRENTNESS_FAILURE_TERMS):
        errors.append("wrong effective date/currentness cannot support the component")
    return errors


def _assessment_ref(assessment: EvidenceRelativeSupportAssessment) -> dict[str, Any]:
    return _without_empty(
        {
            "assessment_id": assessment.assessment_id,
            "assessment_digest": assessment.assessment_digest,
            "preflight_digest": assessment.preflight_digest,
            "negative_control_profile_digest": (
                assessment.negative_control_profile_digest
            ),
        }
    )


def _normalized_status(value: Mapping[str, Any]) -> str:
    safe = _safe_mapping(value)
    status = safe.get("status", safe.get("result", safe.get("check_status")))
    return _normalize_key(status)


def _reject_forbidden_payload(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _AUTHORITY_FORBIDDEN_KEYS)
    if forbidden:
        raise DPrimeAssessmentValidationError(
            f"{context} includes forbidden authority fields: "
            + ", ".join(forbidden)
        )
    raw_private = sorted(keys & _RAW_PRIVATE_KEYS)
    if raw_private:
        raise DPrimeAssessmentValidationError(
            f"{context} includes raw/private fields: " + ", ".join(raw_private)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeAssessmentValidationError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise DPrimeAssessmentValidationError(f"{label} must be a mapping")
    return dict(value)


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 260) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_token(value: Any, *, limit: int = 260) -> str | None:
    text = _clean_text(value, limit=limit)
    return _normalize_key(text) if text else None


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _normalize_words(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().replace("-", " ").split())


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


_MANDATORY_CLOSED_SURFACE_FLAG_KEYS = (
    "model_review_licensed",
    "assessment_created",
    "validated_support_proposal_created",
    "run_kernel_support_admission_request_created",
    "semantic_observation_created",
    "component_coverage_bound",
    "citation_eligibility_claimed",
    "source_obligation_satisfaction_claimed",
    "answer_text_created",
    "product_correctness_claimed",
)
_AUTHORITY_FORBIDDEN_KEYS = frozenset(
    {
        "admitted_support",
        "answer",
        "answer_text",
        "author",
        "author_input",
        "author_prose",
        "authorprose",
        "citation_eligibility",
        "component_coverage",
        "component_coverage_binding",
        "componentcoverage",
        "componentcoveragerecord",
        "evidence_relative_analysis_packet",
        "evidencerelativeanalysispacket",
        "final_answer",
        "final_answer_packet",
        "finalanswerpacket",
        "fap",
        "product_correctness",
        "run_kernel_admission",
        "run_kernel_admission_request",
        "run_kernel_decision",
        "run_kernel_support_admission_request",
        "runkernel_admission_request",
        "runkernel_decision",
        "runkerneladmissionrequest",
        "runkerneldecision",
        "semantic_observation",
        "semanticobservation",
        "source_obligation_satisfaction",
        "source_obligation_satisfied",
        "sufficiency_readiness",
        "sufficiencyreadiness",
        "validated_support_proposal",
        "validatedsupportproposal",
    }
)
_RAW_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_text",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_AUTHORITY_FORBIDDEN_KEYS,
        "answer_ready",
        "answer_text_created",
        "assessment_created",
        "author_input_ready",
        "citation_eligibility_claimed",
        "component_coverage_created",
        "evidence_admitted",
        "final_answer_ready",
        "model_review_licensed",
        "product_correctness_claimed",
        "run_kernel_support_admission_request_created",
        "semantic_support_created",
        "source_obligation_satisfaction_claimed",
        "validated_support_proposal_created",
    }
)
_RATIONALE_ONLY_TERMS = frozenset(
    {
        "anchor count",
        "bounded content",
        "custody",
        "domain",
        "lineage",
        "snippet",
        "source class",
        "url",
    }
)
_CURRENTNESS_FAILURE_TERMS = frozenset(
    {
        "currentness mismatch",
        "stale",
        "wrong effective date",
    }
)

__all__ = [
    "ASSESSMENT_ABSTAINED",
    "ASSESSMENT_CHALLENGE_RECOMMENDED",
    "ASSESSMENT_NON_SUPPORT",
    "ASSESSMENT_SCHEMA_INVALID",
    "ASSESSMENT_SCHEMA_VALID",
    "ASSESSMENT_VALIDATION_BLOCKED",
    "ASSESSMENT_VALIDATION_STATUSES",
    "ASSESSMENT_VALIDATOR_STATUS_AVAILABLE",
    "ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED",
    "ASSESSMENT_VALIDATOR_STATUS_UNAVAILABLE",
    "AssessmentValidationResult",
    "DPrimeAssessmentValidationError",
    "EvidenceRelativeSupportAssessment",
    "SUPPORT_RELATIONS",
    "VAGUE_SUPPORT_RELATIONS",
    "assessment_digest",
    "assessment_validator_availability_status",
    "validate_evidence_relative_support_assessment",
]
