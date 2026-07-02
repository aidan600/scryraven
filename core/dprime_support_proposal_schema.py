"""D-prime schema and status vocabulary for support-proposal admission.

This module is product-owned schema/status infrastructure. It does not create
evidence-frame preflight results from retained content, does not call models, and
does not admit support. RunKernel remains the only owner of support-bearing
admission decisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

import core.dprime_negative_control_profile as dprime_negative_controls
from core.dprime_assessment_validation import (
    ASSESSMENT_SCHEMA_VALID,
    ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED,
    assessment_validator_availability_status,
)
from core.dprime_one_shot_model_review_adapter import (
    ADAPTER_STATUS_NOT_CONFIGURED,
    DPrimeOneShotModelReviewAdapter,
    validate_dprime_one_shot_model_review_adapter,
)
from core.dprime_one_shot_provider_boundary import (
    PROVIDER_BOUNDARY_STATUS_NOT_APPROVED,
    DPrimeOneShotProviderBoundary,
    validate_dprime_one_shot_provider_boundary,
)

DPRIME_PHASE = "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
DPRIME_SCHEMA_VERSION = "dprime_support_proposal_schema_v1"

BLOCKED_DPRIME_PREFLIGHT_MISSING = "BLOCKED_DPRIME_PREFLIGHT_MISSING"
BLOCKED_DPRIME_PREFLIGHT_FAILED = "BLOCKED_DPRIME_PREFLIGHT_FAILED"
BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING = (
    "BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING"
)
BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED = (
    "BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED"
)
BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED = (
    "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED"
)
BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID = (
    "BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID"
)
BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED = (
    "BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED"
)
BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID = (
    "BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID"
)
BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED = (
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED"
)
BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT = (
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT"
)
BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED = (
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED"
)
BLOCKED_DPRIME_ASSESSMENT_ONLY_PROPOSAL_NOT_LICENSED = (
    "BLOCKED_DPRIME_ASSESSMENT_ONLY_PROPOSAL_NOT_LICENSED"
)
BLOCKED_APPROVED_MODEL_UNAVAILABLE = "BLOCKED_APPROVED_MODEL_UNAVAILABLE"
BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE = "BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE"
BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE = (
    "BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE"
)
BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT = (
    "BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT"
)
BLOCKED_DPRIME_SUPPORT_ASSESSMENT_MISSING = (
    "BLOCKED_DPRIME_SUPPORT_ASSESSMENT_MISSING"
)
BLOCKED_DPRIME_SUPPORT_ASSESSMENT_ABSTAINED = (
    "BLOCKED_DPRIME_SUPPORT_ASSESSMENT_ABSTAINED"
)
BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED = (
    "BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED"
)
DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED = (
    "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
)
DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED = (
    "DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED"
)
BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING = (
    "BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING"
)
BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING = (
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING"
)

DPRIME_SUPPORT_PROPOSAL_REJECTED = "DPRIME_SUPPORT_PROPOSAL_REJECTED"
DPRIME_SUPPORT_PROPOSAL_CHALLENGED = "DPRIME_SUPPORT_PROPOSAL_CHALLENGED"
DPRIME_SEMANTIC_OBSERVATION_ADMITTED = "DPRIME_SEMANTIC_OBSERVATION_ADMITTED"
DPRIME_COMPONENT_COVERAGE_BOUND = "DPRIME_COMPONENT_COVERAGE_BOUND"

DPRIME_SCHEMA_STATUS_AVAILABLE = "available"
DPRIME_STATUS_MISSING = "missing"
DPRIME_STATUS_NOT_REACHED = "not reached"
DPRIME_STATUS_UNAVAILABLE = "unavailable"

EVIDENCE_FRAME_PREFLIGHT_STATUSES = frozenset(
    {"passed", "failed", "blocked"}
)
SUPPORT_ASSESSMENT_STATUSES = frozenset(
    {
        "assessed",
        "abstained",
        "missing",
        BLOCKED_DPRIME_SUPPORT_ASSESSMENT_MISSING,
        BLOCKED_DPRIME_SUPPORT_ASSESSMENT_ABSTAINED,
    }
)
SUPPORT_PROPOSAL_VALIDATOR_STATUSES = frozenset(
    {
        DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
        BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED,
        DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED,
        BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING,
        BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING,
    }
)
LATER_PHASE_STATUSES = frozenset(
    {
        DPRIME_SUPPORT_PROPOSAL_REJECTED,
        DPRIME_SUPPORT_PROPOSAL_CHALLENGED,
        DPRIME_SEMANTIC_OBSERVATION_ADMITTED,
        DPRIME_COMPONENT_COVERAGE_BOUND,
    }
)
DPRIME_MODEL_REVIEW_TRANSPORT_BLOCKERS = frozenset(
    {
        BLOCKED_APPROVED_MODEL_UNAVAILABLE,
        BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE,
        BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE,
        BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
    }
)

AUTHORITY_BOUNDARY_NONCLAIMS = (
    "preflight pass != semantic support",
    "negative-control profile available != semantic support",
    "assessment validator available != semantic support",
    "provider boundary approved != semantic support",
    "adapter contract valid != semantic support",
    "model-reviewed assessment != proposal",
    "assessment != proposal",
    "proposal != admitted support",
    "validation pass != RunKernel admission",
    "validator challenge recommendation != RunKernel challenge",
    "directly_supports != RunKernel admission",
    "SemanticObservation admission != ComponentCoverage binding",
    "ComponentCoverage != citation eligibility",
    "citation eligibility != answer correctness",
)


class DPrimeSupportProposalSchemaError(ValueError):
    """Raised when D-prime schema material attempts an authority upgrade."""


@dataclass(frozen=True, slots=True)
class EvidenceFramePreflight:
    """Deterministic preflight record shape, not semantic support."""

    frame_ref: Mapping[str, Any] = field(default_factory=dict)
    preflight_status: str = "passed"
    blockers: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_status(
            self.preflight_status,
            EVIDENCE_FRAME_PREFLIGHT_STATUSES,
            context="EvidenceFramePreflight.preflight_status",
        )
        _reject_forbidden_payload(
            self.frame_ref,
            context="EvidenceFramePreflight.frame_ref",
            extra_forbidden_keys=_PREFLIGHT_FORBIDDEN_KEYS,
        )
        _reject_forbidden_payload(
            self.metadata,
            context="EvidenceFramePreflight.metadata",
            extra_forbidden_keys=_PREFLIGHT_FORBIDDEN_KEYS,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> EvidenceFramePreflight:
        safe = _required_mapping(payload, "EvidenceFramePreflight")
        return cls(
            frame_ref=_safe_mapping(safe.get("frame_ref")),
            preflight_status=_clean_token(safe.get("preflight_status")) or "passed",
            blockers=_text_tuple(safe.get("blockers")),
            warnings=_text_tuple(safe.get("warnings")),
            metadata=_safe_mapping(safe.get("metadata")),
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "EvidenceFramePreflight",
                "preflight_status": self.preflight_status,
                "frame_ref": dict(self.frame_ref),
                "blockers": list(_text_tuple(self.blockers)),
                "warnings": list(_text_tuple(self.warnings)),
                "metadata": dict(self.metadata),
                "semantic_support_created": False,
                "semantic_observation_created": False,
                "component_coverage_created": False,
            }
        )


@dataclass(frozen=True, slots=True)
class EvidenceRelativeSupportAssessment:
    """Assessment-only support posture; not a proposal and not admitted support."""

    assessment_ref: Mapping[str, Any] = field(default_factory=dict)
    assessment_status: str = "assessed"
    support_assessment_only: bool = True
    admitted_support: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_status(
            self.assessment_status,
            SUPPORT_ASSESSMENT_STATUSES,
            context="EvidenceRelativeSupportAssessment.assessment_status",
        )
        if self.support_assessment_only is not True:
            raise DPrimeSupportProposalSchemaError(
                "EvidenceRelativeSupportAssessment must remain assessment-only"
            )
        if self.admitted_support is not False:
            raise DPrimeSupportProposalSchemaError(
                "EvidenceRelativeSupportAssessment cannot admit support"
            )
        _reject_forbidden_payload(
            self.assessment_ref,
            context="EvidenceRelativeSupportAssessment.assessment_ref",
            extra_forbidden_keys=_ASSESSMENT_FORBIDDEN_KEYS,
        )
        _reject_forbidden_payload(
            self.metadata,
            context="EvidenceRelativeSupportAssessment.metadata",
            extra_forbidden_keys=_ASSESSMENT_FORBIDDEN_KEYS,
        )

    @property
    def is_admitted_support(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "EvidenceRelativeSupportAssessment",
                "assessment_status": self.assessment_status,
                "assessment_ref": dict(self.assessment_ref),
                "support_assessment_only": True,
                "admitted_support": False,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class SupportProposalValidationResult:
    """Deterministic validator result; it is not a RunKernel decision."""

    validation_status: str
    blockers: Sequence[str] = field(default_factory=tuple)
    errors: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)
    challenge_recommended: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _reject_run_kernel_decision_status(
            self.validation_status,
            context="SupportProposalValidationResult.validation_status",
        )
        _require_status(
            self.validation_status,
            SUPPORT_PROPOSAL_VALIDATOR_STATUSES,
            context="SupportProposalValidationResult.validation_status",
        )
        if (
            self.validation_status == DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED
            and self.challenge_recommended is not True
        ):
            raise DPrimeSupportProposalSchemaError(
                "challenge recommendation status requires challenge_recommended true"
            )
        _reject_forbidden_payload(
            self.metadata,
            context="SupportProposalValidationResult.metadata",
            extra_forbidden_keys=_VALIDATION_RESULT_FORBIDDEN_KEYS,
        )

    @property
    def run_kernel_decision(self) -> str:
        return "not made"

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "SupportProposalValidationResult",
                "validation_status": self.validation_status,
                "blockers": list(_text_tuple(self.blockers)),
                "errors": list(_text_tuple(self.errors)),
                "warnings": list(_text_tuple(self.warnings)),
                "challenge_recommended": self.challenge_recommended,
                "validator_challenge_recommendation_only": (
                    self.challenge_recommended
                ),
                "run_kernel_decision": "not made",
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class ValidatedSupportProposal:
    """Validated proposal package; validation pass is not admission."""

    proposal_ref: Mapping[str, Any]
    validation_result: SupportProposalValidationResult
    proposal_status: str = DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    admitted_support: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _reject_run_kernel_decision_status(
            self.proposal_status,
            context="ValidatedSupportProposal.proposal_status",
        )
        _require_status(
            self.proposal_status,
            SUPPORT_PROPOSAL_VALIDATOR_STATUSES,
            context="ValidatedSupportProposal.proposal_status",
        )
        if self.validation_result.validation_status not in SUPPORT_PROPOSAL_VALIDATOR_STATUSES:
            raise DPrimeSupportProposalSchemaError(
                "ValidatedSupportProposal requires a deterministic validation result"
            )
        if self.admitted_support is not False:
            raise DPrimeSupportProposalSchemaError(
                "ValidatedSupportProposal cannot admit support"
            )
        _reject_forbidden_payload(
            self.proposal_ref,
            context="ValidatedSupportProposal.proposal_ref",
            extra_forbidden_keys=_VALIDATED_PROPOSAL_FORBIDDEN_KEYS,
        )
        _reject_forbidden_payload(
            self.metadata,
            context="ValidatedSupportProposal.metadata",
            extra_forbidden_keys=_VALIDATED_PROPOSAL_FORBIDDEN_KEYS,
        )

    @property
    def is_admitted_support(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "ValidatedSupportProposal",
                "proposal_status": self.proposal_status,
                "proposal_ref": dict(self.proposal_ref),
                "validation_result": self.validation_result.to_dict(),
                "admitted_support": False,
                "run_kernel_admission_status": "not made",
                "metadata": dict(self.metadata),
            }
        )


def build_validated_support_proposal_from_assessment(
    *,
    assessment_ref: Mapping[str, Any],
    input_packet_ref: Mapping[str, Any],
    model_review_ref: Mapping[str, Any],
    prompt_license_ref: Mapping[str, Any],
    assessment_validation_status: str,
    support_relation: str | None,
) -> ValidatedSupportProposal:
    """Build a pre-admission D-prime proposal candidate from a valid assessment."""

    if assessment_validation_status != ASSESSMENT_SCHEMA_VALID:
        raise DPrimeSupportProposalSchemaError(
            "support proposal requires a validator-valid assessment"
        )
    assessment = _safe_mapping(assessment_ref)
    assessment_id = _clean_token(assessment.get("assessment_id"), limit=320)
    assessment_digest = _clean_token(assessment.get("assessment_digest"), limit=128)
    if not assessment_id or not assessment_digest:
        raise DPrimeSupportProposalSchemaError(
            "support proposal requires assessment id and digest lineage"
        )
    relation = _clean_token(support_relation, limit=160)
    if relation not in {"directly_supports", "partially_supports"}:
        raise DPrimeSupportProposalSchemaError(
            "support proposal requires direct or partial support relation"
        )
    proposal_ref = _support_proposal_ref(
        assessment_ref=assessment,
        input_packet_ref=_safe_mapping(input_packet_ref),
        model_review_ref=_safe_mapping(model_review_ref),
        prompt_license_ref=_safe_mapping(prompt_license_ref),
        assessment_validation_status=assessment_validation_status,
        support_relation=relation,
    )
    validation_result = SupportProposalValidationResult(
        validation_status=DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
        blockers=(BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING,),
        warnings=(
            "proposal candidate is not admitted support",
            "RunKernel support admission is not licensed in this phase",
        ),
        metadata={
            "assessment_validation_status": assessment_validation_status,
            "support_relation": relation,
            "lineage_only": True,
        },
    )
    return ValidatedSupportProposal(
        proposal_ref=proposal_ref,
        validation_result=validation_result,
        metadata={
            "pre_admission_candidate": True,
            "lineage_only": True,
        },
    )


@dataclass(frozen=True, slots=True)
class RunKernelSupportProposalAdmissionRequest:
    """Request shape for a future RunKernel admission decision."""

    support_proposal_ref: Mapping[str, Any]
    validation_result_ref: Mapping[str, Any]
    request_status: str = "ready for RunKernel"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _reject_forbidden_payload(
            self.support_proposal_ref,
            context="RunKernelSupportProposalAdmissionRequest.support_proposal_ref",
            extra_forbidden_keys=_RUN_KERNEL_REQUEST_FORBIDDEN_KEYS,
        )
        _reject_forbidden_payload(
            self.validation_result_ref,
            context="RunKernelSupportProposalAdmissionRequest.validation_result_ref",
            extra_forbidden_keys=_RUN_KERNEL_REQUEST_FORBIDDEN_KEYS,
        )
        _reject_forbidden_payload(
            self.metadata,
            context="RunKernelSupportProposalAdmissionRequest.metadata",
            extra_forbidden_keys=_RUN_KERNEL_REQUEST_FORBIDDEN_KEYS,
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "RunKernelSupportProposalAdmissionRequest",
                "request_status": self.request_status,
                "support_proposal_ref": dict(self.support_proposal_ref),
                "validation_result_ref": dict(self.validation_result_ref),
                "run_kernel_decision": "not made",
                "semantic_observation_created": False,
                "component_coverage_created": False,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class NegativeControlProfile:
    """Validator negative control; cannot claim product or model success."""

    profile_id: str
    product_correctness_claimed: bool = False
    model_success_claimed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.product_correctness_claimed is not False:
            raise DPrimeSupportProposalSchemaError(
                "NegativeControlProfile cannot claim product correctness"
            )
        if self.model_success_claimed is not False:
            raise DPrimeSupportProposalSchemaError(
                "NegativeControlProfile cannot claim model success"
            )
        _reject_forbidden_payload(
            self.metadata,
            context="NegativeControlProfile.metadata",
            extra_forbidden_keys=_NEGATIVE_CONTROL_FORBIDDEN_KEYS,
        )

    def to_dict(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": DPRIME_SCHEMA_VERSION,
                "record_kind": "NegativeControlProfile",
                "profile_id": _clean_token(self.profile_id),
                "product_correctness_claimed": False,
                "model_success_claimed": False,
                "metadata": dict(self.metadata),
            }
        )


@dataclass(frozen=True, slots=True)
class DPrimeStatusPayload:
    """CLI-safe D-prime status projection."""

    schema_status: str = DPRIME_SCHEMA_STATUS_AVAILABLE
    preflight_status: str = DPRIME_STATUS_MISSING
    negative_control_profile_status: str = DPRIME_STATUS_NOT_REACHED
    assessment_validator_status: str = ASSESSMENT_VALIDATOR_STATUS_NOT_REACHED
    model_review_status: str = DPRIME_STATUS_NOT_REACHED
    model_review_call_count: int = 0
    assessment_status: str = DPRIME_STATUS_NOT_REACHED
    proposal_validation_status: str = DPRIME_STATUS_NOT_REACHED
    run_kernel_support_admission_status: str = DPRIME_STATUS_NOT_REACHED
    run_kernel_decision: str = "not made"
    admitted_support: bool = False
    semantic_observation_admission_status: str = DPRIME_STATUS_UNAVAILABLE
    component_coverage_status: str = DPRIME_STATUS_UNAVAILABLE
    semantic_support_source: str = "unavailable; D-prime preflight missing"
    decision: str = BLOCKED_DPRIME_PREFLIGHT_MISSING
    blocker_detail: str = "D-prime EvidenceFramePreflight is not implemented"
    evidence_frame_preflight_ref: Mapping[str, Any] = field(default_factory=dict)
    evidence_frame_preflight_created: bool = False
    negative_control_profile_ref: Mapping[str, Any] = field(default_factory=dict)
    negative_control_profile_consumed: bool = False
    one_shot_provider_boundary_status: str = PROVIDER_BOUNDARY_STATUS_NOT_APPROVED
    one_shot_provider_boundary_ref: Mapping[str, Any] = field(default_factory=dict)
    one_shot_provider_boundary_consumed: bool = False
    one_shot_model_review_adapter_status: str = ADAPTER_STATUS_NOT_CONFIGURED
    one_shot_model_review_adapter_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    one_shot_model_review_adapter_consumed: bool = False
    product_model_route_ref: Mapping[str, Any] = field(default_factory=dict)
    support_proposal_validation_ref: Mapping[str, Any] = field(default_factory=dict)
    validated_support_proposal_ref: Mapping[str, Any] = field(default_factory=dict)
    validated_support_proposal_available: bool = False

    def __post_init__(self) -> None:
        if self.schema_status != DPRIME_SCHEMA_STATUS_AVAILABLE:
            raise DPrimeSupportProposalSchemaError(
                "D-prime schema status must be available for this phase"
            )
        _reject_run_kernel_decision_status(
            self.decision,
            context="DPrimeStatusPayload.decision",
        )
        _reject_run_kernel_decision_status(
            self.run_kernel_decision,
            context="DPrimeStatusPayload.run_kernel_decision",
        )
        if self.admitted_support is not False:
            raise DPrimeSupportProposalSchemaError(
                "DPrimeStatusPayload cannot admit support"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DPRIME_SCHEMA_VERSION,
            "phase": DPRIME_PHASE,
            "schema_status": self.schema_status,
            "preflight_status": self.preflight_status,
            "negative_control_profile_status": self.negative_control_profile_status,
            "negative_control_profile_ref": dict(self.negative_control_profile_ref),
            "negative_control_profile_consumed": (
                self.negative_control_profile_consumed
            ),
            "assessment_validator_status": self.assessment_validator_status,
            "one_shot_provider_boundary_status": (
                self.one_shot_provider_boundary_status
            ),
            "one_shot_provider_boundary_ref": dict(
                self.one_shot_provider_boundary_ref
            ),
            "one_shot_provider_boundary_consumed": (
                self.one_shot_provider_boundary_consumed
            ),
            "one_shot_model_review_adapter_status": (
                self.one_shot_model_review_adapter_status
            ),
            "one_shot_model_review_adapter_ref": dict(
                self.one_shot_model_review_adapter_ref
            ),
            "one_shot_model_review_adapter_consumed": (
                self.one_shot_model_review_adapter_consumed
            ),
            "product_model_route_ref": dict(self.product_model_route_ref),
            "model_review_status": self.model_review_status,
            "model_review_call_count": self.model_review_call_count,
            "assessment_status": self.assessment_status,
            "proposal_validation_status": self.proposal_validation_status,
            "run_kernel_support_admission_status": (
                self.run_kernel_support_admission_status
            ),
            "run_kernel_decision": self.run_kernel_decision,
            "admitted_support": False,
            "support_proposal_validation_ref": dict(
                self.support_proposal_validation_ref
            ),
            "validated_support_proposal_ref": dict(
                self.validated_support_proposal_ref
            ),
            "validated_support_proposal_available": (
                self.validated_support_proposal_available
            ),
            "semantic_observation_admission_status": (
                self.semantic_observation_admission_status
            ),
            "component_coverage_status": self.component_coverage_status,
            "semantic_support_source": self.semantic_support_source,
            "decision": self.decision,
            "blocker_detail": self.blocker_detail,
            "evidence_frame_preflight_ref": dict(self.evidence_frame_preflight_ref),
            "authority_boundary_nonclaims": list(AUTHORITY_BOUNDARY_NONCLAIMS),
            "objects_created": {
                "evidence_frame_preflight": self.evidence_frame_preflight_created,
                "evidence_relative_support_assessment": False,
                "validated_support_proposal": (
                    self.validated_support_proposal_available
                ),
                "run_kernel_support_proposal_admission_request": False,
                "semantic_observation": False,
                "component_coverage": False,
            },
        }


_DEFAULT_NEGATIVE_CONTROL_PROFILE_SENTINEL = object()


def build_dprime_status_payload(
    *,
    evidence_frame_preflight: Mapping[str, Any] | EvidenceFramePreflight | None = None,
    negative_control_profile: Any = _DEFAULT_NEGATIVE_CONTROL_PROFILE_SENTINEL,
    one_shot_provider_boundary: (
        Mapping[str, Any] | DPrimeOneShotProviderBoundary | None
    ) = None,
    one_shot_model_review_adapter: (
        Mapping[str, Any] | DPrimeOneShotModelReviewAdapter | None
    ) = None,
    product_model_route_ref: Mapping[str, Any] | None = None,
) -> DPrimeStatusPayload:
    """Return the earliest D-prime blocker known in this phase."""

    route_ref = _safe_mapping(product_model_route_ref)
    if evidence_frame_preflight is None:
        return DPrimeStatusPayload(product_model_route_ref=route_ref)
    preflight = (
        evidence_frame_preflight
        if isinstance(evidence_frame_preflight, EvidenceFramePreflight)
        else EvidenceFramePreflight.from_mapping(evidence_frame_preflight)
    )
    if preflight.preflight_status != "passed":
        blocker_detail = (
            "; ".join(_text_tuple(preflight.blockers))
            or "D-prime EvidenceFramePreflight failed validation"
        )
        return DPrimeStatusPayload(
            preflight_status=preflight.preflight_status,
            semantic_support_source="unavailable; D-prime preflight failed",
            decision=BLOCKED_DPRIME_PREFLIGHT_FAILED,
            blocker_detail=blocker_detail,
            evidence_frame_preflight_ref=_safe_mapping(preflight.frame_ref),
            evidence_frame_preflight_created=True,
            product_model_route_ref=route_ref,
        )
    profile = (
        dprime_negative_controls.build_default_negative_control_profile()
        if negative_control_profile is _DEFAULT_NEGATIVE_CONTROL_PROFILE_SENTINEL
        else negative_control_profile
    )
    profile_validation = dprime_negative_controls.validate_negative_control_profile(
        profile
    )
    profile_ref = _safe_mapping(profile_validation.profile_ref)
    if (
        profile_validation.profile_status
        == dprime_negative_controls.NEGATIVE_CONTROL_PROFILE_STATUS_MISSING
    ):
        return DPrimeStatusPayload(
            preflight_status="passed",
            negative_control_profile_status="missing",
            semantic_support_source=(
                "unavailable; D-prime negative-control profile missing"
            ),
            decision=BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING,
            blocker_detail=(
                profile_validation.blocker_detail
                or "D-prime negative-control profile is missing"
            ),
            evidence_frame_preflight_ref=_safe_mapping(preflight.frame_ref),
            evidence_frame_preflight_created=True,
            negative_control_profile_ref=profile_ref,
            product_model_route_ref=route_ref,
        )
    if not profile_validation.passed:
        return DPrimeStatusPayload(
            preflight_status="passed",
            negative_control_profile_status="failed",
            semantic_support_source=(
                "unavailable; D-prime negative-control profile failed"
            ),
            decision=BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED,
            blocker_detail=(
                profile_validation.blocker_detail
                or "D-prime negative-control profile failed validation"
            ),
            evidence_frame_preflight_ref=_safe_mapping(preflight.frame_ref),
            evidence_frame_preflight_created=True,
            negative_control_profile_ref=profile_ref,
            negative_control_profile_consumed=True,
            product_model_route_ref=route_ref,
        )
    provider_boundary_validation = validate_dprime_one_shot_provider_boundary(
        one_shot_provider_boundary
    )
    adapter_validation = validate_dprime_one_shot_model_review_adapter(
        one_shot_model_review_adapter
    )
    return DPrimeStatusPayload(
        preflight_status="passed",
        negative_control_profile_status="available",
        assessment_validator_status=assessment_validator_availability_status(
            profile_validation
        ),
        model_review_status="not licensed",
        semantic_support_source="unavailable; D-prime model review not licensed",
        decision=BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED,
        blocker_detail="D-prime model review is not licensed in this phase",
        evidence_frame_preflight_ref=_safe_mapping(preflight.frame_ref),
        evidence_frame_preflight_created=True,
        negative_control_profile_ref=profile_ref,
        negative_control_profile_consumed=True,
        one_shot_provider_boundary_status=provider_boundary_validation.status,
        one_shot_provider_boundary_ref=provider_boundary_validation.to_status_ref(),
        one_shot_provider_boundary_consumed=True,
        one_shot_model_review_adapter_status=adapter_validation.status,
        one_shot_model_review_adapter_ref=adapter_validation.to_status_ref(),
        one_shot_model_review_adapter_consumed=True,
        product_model_route_ref=route_ref,
    )


_PREFLIGHT_FORBIDDEN_KEYS = frozenset(
    {
        "answer",
        "answer_text",
        "claim_or_value",
        "component_coverage",
        "component_coverage_record",
        "componentcoverage",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "semanticobservation",
        "source_obligation_satisfaction",
        "support_relation",
        "support_relations",
    }
)
_AUTHORITY_FORBIDDEN_KEYS = frozenset(
    {
        "admit",
        "admitted",
        "admitted_support",
        "admitted_semantic_observation",
        "analysis_gap_search_proposal",
        "answer",
        "answer_prose",
        "answer_text",
        "author_input",
        "author_prose",
        "challenge",
        "challenged",
        "citation",
        "citation_eligible",
        "citation_rendered",
        "component_coverage",
        "component_coverage_bound",
        "component_coverage_record",
        "componentcoverage",
        "coverage_bound",
        "coverage_record",
        "final_answer",
        "final_answer_packet",
        "product_correctness",
        "product_correctness_claimed",
        "reject",
        "rejected",
        "run_kernel_admission",
        "run_kernel_decision",
        "run_kernel_rejection",
        "semantic_observation",
        "semantic_observation_admitted",
        "semanticobservation",
        "source_obligation_satisfaction",
        "source_obligation_satisfied",
    }
)
_ASSESSMENT_FORBIDDEN_KEYS = _AUTHORITY_FORBIDDEN_KEYS | {
    "validated_support_proposal",
}
_VALIDATION_RESULT_FORBIDDEN_KEYS = _AUTHORITY_FORBIDDEN_KEYS | {
    "run_kernel_challenge",
}
_VALIDATED_PROPOSAL_FORBIDDEN_KEYS = _AUTHORITY_FORBIDDEN_KEYS | {
    "semantic_observation_ref",
    "component_coverage_ref",
}
_RUN_KERNEL_REQUEST_FORBIDDEN_KEYS = _AUTHORITY_FORBIDDEN_KEYS | {
    "precreated_semantic_observation",
    "precreated_component_coverage",
    "semantic_observation_ref",
    "component_coverage_ref",
}
_NEGATIVE_CONTROL_FORBIDDEN_KEYS = _AUTHORITY_FORBIDDEN_KEYS | {
    "model_success",
    "model_success_claimed",
}
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
        "author_input_ready",
        "component_satisfied",
        "evidence_admitted",
        "final_answer_ready",
        "model_success",
        "model_success_claimed",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)
_RUN_KERNEL_DECISION_STATUSES = frozenset(
    {
        "admit",
        "admitted",
        "reject",
        "rejected",
        "challenge",
        "challenged",
        "block",
        "blocked",
        DPRIME_SUPPORT_PROPOSAL_REJECTED,
        DPRIME_SUPPORT_PROPOSAL_CHALLENGED,
        DPRIME_SEMANTIC_OBSERVATION_ADMITTED,
        DPRIME_COMPONENT_COVERAGE_BOUND,
    }
)


def _reject_forbidden_payload(
    value: Any,
    *,
    context: str,
    extra_forbidden_keys: frozenset[str] = frozenset(),
) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & (_AUTHORITY_FORBIDDEN_KEYS | extra_forbidden_keys))
    if forbidden:
        raise DPrimeSupportProposalSchemaError(
            f"{context} includes forbidden authority fields: "
            + ", ".join(forbidden)
        )
    raw_private = sorted(keys & _RAW_PRIVATE_KEYS)
    if raw_private:
        raise DPrimeSupportProposalSchemaError(
            f"{context} includes raw/private fields: " + ", ".join(raw_private)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeSupportProposalSchemaError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _reject_run_kernel_decision_status(value: Any, *, context: str) -> None:
    status = _normalize_key(value)
    if status in {_normalize_key(item) for item in _RUN_KERNEL_DECISION_STATUSES}:
        raise DPrimeSupportProposalSchemaError(
            f"{context} cannot represent a RunKernel admission decision"
        )


def _require_status(value: Any, allowed: frozenset[str], *, context: str) -> None:
    if str(value or "") not in allowed:
        raise DPrimeSupportProposalSchemaError(
            f"{context} has unsupported status: {value!s}"
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
        raise DPrimeSupportProposalSchemaError(f"{label} must be a mapping")
    return dict(value)


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _text_tuple(value: Any, *, limit: int = 220) -> tuple[str, ...]:
    if isinstance(value, str):
        token = _clean_token(value, limit=limit)
        return (token,) if token else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _clean_token(item, limit=limit)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return tuple(out)


def _clean_token(value: Any, *, limit: int = 220) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _support_proposal_ref(
    *,
    assessment_ref: Mapping[str, Any],
    input_packet_ref: Mapping[str, Any],
    model_review_ref: Mapping[str, Any],
    prompt_license_ref: Mapping[str, Any],
    assessment_validation_status: str,
    support_relation: str,
) -> dict[str, Any]:
    lineage = _without_empty(
        {
            "assessment_ref": dict(assessment_ref),
            "input_packet_ref": _ref_subset(
                input_packet_ref,
                (
                    "input_packet_schema_version",
                    "input_packet_digest",
                    "phase",
                ),
            ),
            "model_review_ref": _ref_subset(
                model_review_ref,
                (
                    "model_review_id",
                    "model_review_digest",
                    "phase",
                ),
            ),
            "prompt_license_ref": _ref_subset(
                prompt_license_ref,
                (
                    "license_id",
                    "phase",
                    "test_only",
                    "enabled",
                    "callable_kind",
                    "fake_test_callable_only",
                ),
            ),
            "assessment_validation_status": assessment_validation_status,
            "support_relation": support_relation,
            "lineage_only": True,
            "pre_admission_candidate": True,
        }
    )
    proposal_digest = _digest_json(lineage)
    return {
        "proposal_id": f"dprime-support-proposal:{proposal_digest[:16]}",
        "proposal_digest": proposal_digest,
        **lineage,
    }


def _ref_subset(value: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    safe = _safe_mapping(value)
    return _without_empty({key: safe.get(key) for key in keys})


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


__all__ = [
    "AUTHORITY_BOUNDARY_NONCLAIMS",
    "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED",
    "BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID",
    "BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED",
    "BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID",
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED",
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT",
    "BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED",
    "BLOCKED_APPROVED_MODEL_UNAVAILABLE",
    "BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE",
    "BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT",
    "BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED",
    "BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING",
    "BLOCKED_DPRIME_PREFLIGHT_FAILED",
    "BLOCKED_DPRIME_PREFLIGHT_MISSING",
    "BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING",
    "BLOCKED_DPRIME_ASSESSMENT_ONLY_PROPOSAL_NOT_LICENSED",
    "BLOCKED_DPRIME_SUPPORT_ASSESSMENT_ABSTAINED",
    "BLOCKED_DPRIME_SUPPORT_ASSESSMENT_MISSING",
    "BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING",
    "BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED",
    "DPRIME_COMPONENT_COVERAGE_BOUND",
    "DPRIME_MODEL_REVIEW_TRANSPORT_BLOCKERS",
    "DPRIME_PHASE",
    "DPRIME_SCHEMA_STATUS_AVAILABLE",
    "DPRIME_SCHEMA_VERSION",
    "DPRIME_SEMANTIC_OBSERVATION_ADMITTED",
    "DPRIME_STATUS_MISSING",
    "DPRIME_STATUS_NOT_REACHED",
    "DPRIME_STATUS_UNAVAILABLE",
    "DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED",
    "DPRIME_SUPPORT_PROPOSAL_CHALLENGED",
    "DPRIME_SUPPORT_PROPOSAL_REJECTED",
    "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED",
    "DPrimeStatusPayload",
    "DPrimeSupportProposalSchemaError",
    "EvidenceFramePreflight",
    "EvidenceRelativeSupportAssessment",
    "LATER_PHASE_STATUSES",
    "NegativeControlProfile",
    "RunKernelSupportProposalAdmissionRequest",
    "SUPPORT_PROPOSAL_VALIDATOR_STATUSES",
    "SupportProposalValidationResult",
    "ValidatedSupportProposal",
    "build_validated_support_proposal_from_assessment",
    "build_dprime_status_payload",
]
