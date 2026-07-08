"""Injected D-prime model-review assessment slice.

This module is default-disabled and test/fake-callable only. It builds a
sanitized assessment input packet, passes one transient bounded evidence window
to an injected callable, parses the returned structure into
``EvidenceRelativeSupportAssessment``, and validates it with the existing
assessment validator. It does not import a provider client, call a real model,
retry, browse, search, retrieve, fetch/read, create support proposals, request
RunKernel admission, admit SemanticObservation, bind ComponentCoverage, create
citations, write answer text, or claim product correctness.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

import core.dprime_assessment_validation as assessment_validation
import core.dprime_negative_control_profile as negative_controls
from core.analyst_workbench_runtime import workbench_dprime_dossier_ref
from core.current_source_component_answer_type_binding import (
    maybe_current_source_component_answer_type_binding_ref,
)
from core.dprime_model_review_prompt import (
    DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION,
    DPRIME_MODEL_REVIEW_SYSTEM_PROMPT,
    build_dprime_model_review_prompt,
    prompt_metadata,
)
from core.dprime_one_shot_model_review_adapter import (
    DPrimeOneShotModelReviewAdapter,
    DPrimeOneShotModelReviewAdapterValidation,
    invoke_dprime_one_shot_model_review_adapter,
    validate_dprime_one_shot_model_review_adapter,
)
from core.dprime_one_shot_provider_boundary import (
    DPrimeOneShotProviderBoundary,
    DPrimeOneShotProviderBoundaryValidation,
    validate_dprime_one_shot_provider_boundary,
)
from core.dprime_support_proposal_schema import (
    BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED,
    BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
    BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT,
    BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
    BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID,
    BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED,
    BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID,
    BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING,
    BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING,
    DPRIME_MODEL_REVIEW_TRANSPORT_BLOCKERS,
    DPRIME_STATUS_NOT_REACHED,
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
    DPrimeSupportProposalSchemaError,
    build_run_kernel_support_proposal_admission_request,
    build_validated_support_proposal_from_assessment,
)

DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE = (
    "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
)
DPRIME_MODEL_REVIEW_INPUT_SCHEMA_VERSION = (
    "dprime_model_review_assessment_input_slice_01_v1"
)

MODEL_REVIEW_STATUS_NOT_LICENSED = "not licensed"
MODEL_REVIEW_STATUS_LICENSED = "licensed"
MODEL_REVIEW_STATUS_ATTEMPTED = "attempted"
MODEL_REVIEW_STATUS_COMPLETED = "completed"
MODEL_REVIEW_STATUS_ABSTAINED = "abstained"
MODEL_REVIEW_STATUS_BLOCKED = "blocked"

MODEL_REVIEW_CALLABLE_KIND_FAKE_TEST = "fake_test"
MODEL_REVIEW_CALLABLE_KIND_REAL_ONE_SHOT = "real_one_shot"
_MODEL_REVIEW_CALLABLE_KINDS = frozenset(
    {
        MODEL_REVIEW_CALLABLE_KIND_FAKE_TEST,
        MODEL_REVIEW_CALLABLE_KIND_REAL_ONE_SHOT,
    }
)

ASSESSMENT_STATUS_NOT_REACHED = "not reached"
ASSESSMENT_STATUS_ASSESSED = "assessed"
ASSESSMENT_STATUS_ABSTAINED = "abstained"
ASSESSMENT_STATUS_NON_SUPPORT = "non-support"
ASSESSMENT_STATUS_CHALLENGE_RECOMMENDED = "challenge-recommended"
ASSESSMENT_STATUS_INVALID = "invalid"
ASSESSMENT_STATUS_BLOCKED = "blocked"

MAX_TRANSIENT_EVIDENCE_WINDOW_CHARS = 2_000

_CLOSED_SURFACE_FLAGS = {
    "model_review_licensed": True,
    "assessment_created": False,
    "validated_support_proposal_created": False,
    "run_kernel_support_admission_request_created": False,
    "semantic_observation_created": False,
    "component_coverage_bound": False,
    "citation_eligibility_claimed": False,
    "source_obligation_satisfaction_claimed": False,
    "answer_text_created": False,
    "product_correctness_claimed": False,
}
_ASSESSMENT_CLOSED_SURFACE_FLAGS = {
    **_CLOSED_SURFACE_FLAGS,
    "model_review_licensed": False,
}
_FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
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
_FORBIDDEN_OUTPUT_KEYS = _FORBIDDEN_INPUT_KEYS | {
    "analysis_gap_search_proposal",
    "bounded_text",
}
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "answer_text_created",
        "citation_eligibility_claimed",
        "component_coverage_bound",
        "component_coverage_created",
        "final_answer_packet_created",
        "product_correctness_claimed",
        "run_kernel_support_admission_request_created",
        "semantic_observation_created",
        "source_obligation_satisfaction_claimed",
        "validated_support_proposal_created",
    }
)
class DPrimeModelReviewAssessmentError(ValueError):
    """Raised when the D-prime assessment slice must fail closed."""


ModelReviewCallable = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class DPrimeModelReviewLicense:
    """Explicit license for one gated model-review attempt."""

    license_id: str = "dprime-model-review-assessment-slice-01:test-only"
    enabled: bool = False
    test_only: bool = True
    callable_kind: str = MODEL_REVIEW_CALLABLE_KIND_FAKE_TEST
    max_model_review_calls: int = 1
    retry_policy: str = "forbidden"
    timeout_policy: str = "fail_closed"
    one_shot_adapter_ref: str | None = None
    provider: str | None = None
    model: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> DPrimeModelReviewLicense:
        test_only = value.get("test_only", True) is True
        callable_kind = _clean_text(
            value.get("callable_kind") or value.get("adapter_kind"),
            limit=80,
        ) or (
            MODEL_REVIEW_CALLABLE_KIND_FAKE_TEST
            if test_only
            else MODEL_REVIEW_CALLABLE_KIND_REAL_ONE_SHOT
        )
        return cls(
            license_id=_clean_text(value.get("license_id"), limit=260)
            or cls().license_id,
            enabled=value.get("enabled") is True,
            test_only=test_only,
            callable_kind=callable_kind,
            max_model_review_calls=_bounded_int(
                value.get("max_model_review_calls"),
                default=1,
            ),
            retry_policy=_clean_text(value.get("retry_policy"), limit=80)
            or "forbidden",
            timeout_policy=_clean_text(value.get("timeout_policy"), limit=80)
            or "fail_closed",
            one_shot_adapter_ref=_clean_text(
                value.get("one_shot_adapter_ref"),
                limit=320,
            ),
            provider=_clean_text(value.get("provider"), limit=120),
            model=_clean_text(value.get("model"), limit=160),
        )

    @property
    def is_fake_test(self) -> bool:
        return (
            self.test_only is True
            and _normalize_key(self.callable_kind)
            == MODEL_REVIEW_CALLABLE_KIND_FAKE_TEST
        )

    @property
    def is_real_one_shot(self) -> bool:
        return (
            self.test_only is not True
            or _normalize_key(self.callable_kind)
            == MODEL_REVIEW_CALLABLE_KIND_REAL_ONE_SHOT
        )

    def to_ref(self) -> dict[str, Any]:
        return _without_empty(
            {
                "license_id": self.license_id,
                "phase": DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
                "test_only": self.test_only,
                "enabled": self.enabled,
                "callable_kind": self.callable_kind,
                "fake_test_callable_only": self.is_fake_test,
                "max_model_review_calls": self.max_model_review_calls,
                "retry_policy": self.retry_policy,
                "timeout_policy": self.timeout_policy,
                "one_shot_adapter_ref": self.one_shot_adapter_ref,
                "provider_model_selection_status": "unresolved",
                "real_provider_selected": False,
                "real_model_call_authorized": self.is_real_one_shot,
            }
        )


@dataclass(frozen=True, slots=True)
class DPrimeModelReviewInputPacket:
    """Safe retained packet plus transient evidence window kept out of output."""

    safe_packet: Mapping[str, Any]
    transient_bounded_evidence_window: str
    input_packet_digest: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.safe_packet)

    def ref(self) -> dict[str, Any]:
        ref = {
            "input_packet_schema_version": DPRIME_MODEL_REVIEW_INPUT_SCHEMA_VERSION,
            "input_packet_digest": self.input_packet_digest,
            "phase": DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
        }
        evidence_window_ref = _safe_mapping(self.safe_packet.get("evidence_window_ref"))
        if evidence_window_ref:
            ref["evidence_window_ref"] = evidence_window_ref
        selected_window_diagnostic_ref = _safe_mapping(
            self.safe_packet.get("selected_window_diagnostic_ref")
        )
        if selected_window_diagnostic_ref:
            ref["selected_window_diagnostic_ref"] = selected_window_diagnostic_ref
        workbench_ref = _safe_mapping(
            self.safe_packet.get("workbench_dprime_dossier_ref")
        )
        workbench_ref = _support_assessment_safe_workbench_dossier_ref(workbench_ref)
        if workbench_ref:
            ref["workbench_dprime_dossier_ref"] = workbench_ref
        binding_ref = _safe_mapping(
            self.safe_packet.get("component_answer_type_binding_ref")
        )
        if binding_ref:
            ref["component_answer_type_binding_ref"] = binding_ref
        return ref


@dataclass(frozen=True, slots=True)
class DPrimeModelReviewAssessmentResult:
    """Assessment-only review result for product/status consumption."""

    decision: str
    model_review_status: str
    assessment_status: str
    blocker_detail: str
    input_packet_ref: Mapping[str, Any] = field(default_factory=dict)
    model_review_ref: Mapping[str, Any] = field(default_factory=dict)
    prompt_license_ref: Mapping[str, Any] = field(default_factory=dict)
    assessment_ref: Mapping[str, Any] = field(default_factory=dict)
    assessment_material_ref: Mapping[str, Any] = field(default_factory=dict)
    assessment_validation_status: str = "not reached"
    support_relation: str | None = None
    proposal_validation_status: str = DPRIME_STATUS_NOT_REACHED
    support_proposal_validation_ref: Mapping[str, Any] = field(default_factory=dict)
    validated_support_proposal_ref: Mapping[str, Any] = field(default_factory=dict)
    validated_support_proposal_available: bool = False
    run_kernel_support_admission_status: str = DPRIME_STATUS_NOT_REACHED
    run_kernel_support_admission_request_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    run_kernel_decision: str = "not made"
    admitted_support: bool = False
    call_count: int = 0
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    provider_payload_retained: bool = False

    @property
    def return_code(self) -> int:
        return 2

    @property
    def objects_created(self) -> dict[str, bool]:
        assessment_created = bool(self.assessment_ref) and self.assessment_status in {
            ASSESSMENT_STATUS_ASSESSED,
            ASSESSMENT_STATUS_ABSTAINED,
            ASSESSMENT_STATUS_NON_SUPPORT,
            ASSESSMENT_STATUS_CHALLENGE_RECOMMENDED,
        }
        return {
            "evidence_relative_support_assessment": assessment_created,
            "validated_support_proposal": self.validated_support_proposal_available,
            "run_kernel_support_proposal_admission_request": bool(
                self.run_kernel_support_admission_request_ref
            ),
            "semantic_observation": False,
            "component_coverage": False,
        }

    def to_status_overlay(self) -> dict[str, Any]:
        return _without_empty(
            {
                "model_review_status": self.model_review_status,
                "assessment_status": self.assessment_status,
                "assessment_validation_status": self.assessment_validation_status,
                "decision": self.decision,
                "blocker_detail": self.blocker_detail,
                "model_review_ref": dict(self.model_review_ref),
                "prompt_license_ref": dict(self.prompt_license_ref),
                "input_packet_ref": dict(self.input_packet_ref),
                "assessment_ref": dict(self.assessment_ref),
                "assessment_material_ref": dict(self.assessment_material_ref),
                "support_relation": self.support_relation,
                "proposal_validation_status": self.proposal_validation_status,
                "support_proposal_validation_ref": dict(
                    self.support_proposal_validation_ref
                ),
                "validated_support_proposal_ref": dict(
                    self.validated_support_proposal_ref
                ),
                "validated_support_proposal_available": (
                    self.validated_support_proposal_available
                ),
                "run_kernel_support_admission_status": (
                    self.run_kernel_support_admission_status
                ),
                "run_kernel_support_admission_request_ref": dict(
                    self.run_kernel_support_admission_request_ref
                ),
                "run_kernel_decision": "not made",
                "admitted_support": False,
                "model_review_call_count": self.call_count,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "provider_payload_retained": False,
            }
        )


def run_dprime_model_review_assessment(
    *,
    evidence_frame_preflight: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    source_evidence_admission_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    negative_control_profile_ref: Mapping[str, Any],
    assessment_validator_status: str,
    license: Mapping[str, Any] | DPrimeModelReviewLicense | None,
    model_review_callable: ModelReviewCallable | None,
    one_shot_provider_boundary: (
        Mapping[str, Any] | DPrimeOneShotProviderBoundary | None
    ) = None,
    one_shot_model_review_adapter: (
        Mapping[str, Any] | DPrimeOneShotModelReviewAdapter | None
    ) = None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
) -> DPrimeModelReviewAssessmentResult:
    """Run the single-call injected model-review assessment slice."""

    license_obj = _coerce_license(license)
    provider_boundary_validation = validate_dprime_one_shot_provider_boundary(
        one_shot_provider_boundary
    )
    provider_boundary_status_ref = provider_boundary_validation.to_status_ref()
    adapter_validation = validate_dprime_one_shot_model_review_adapter(
        one_shot_model_review_adapter
    )
    adapter_status_ref = adapter_validation.to_status_ref()
    license_blocker = _license_blocker(
        license_obj,
        model_review_callable,
        provider_boundary_validation=provider_boundary_validation,
        adapter_validation=adapter_validation,
    )
    if license_blocker:
        status = (
            MODEL_REVIEW_STATUS_NOT_LICENSED
            if not license_obj.enabled
            else MODEL_REVIEW_STATUS_BLOCKED
        )
        decision = (
            BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
            if status == MODEL_REVIEW_STATUS_NOT_LICENSED
            else BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
        )
        return _blocked_result(
            decision=decision,
            model_review_status=status,
            assessment_status=ASSESSMENT_STATUS_NOT_REACHED,
            blocker_detail=license_blocker,
            prompt_license_ref=license_obj.to_ref(),
        )

    try:
        packet = build_dprime_model_review_input_packet(
            evidence_frame_preflight=evidence_frame_preflight,
            fetch_read_content_packet=fetch_read_content_packet,
            source_evidence_admission_ref=source_evidence_admission_ref,
            citation_source_obligation_readiness_ref=(
                citation_source_obligation_readiness_ref
            ),
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            negative_control_profile_ref=negative_control_profile_ref,
            assessment_validator_status=assessment_validator_status,
            one_shot_provider_boundary_ref=provider_boundary_status_ref,
            one_shot_model_review_adapter_ref=adapter_status_ref,
            workbench_dprime_dossier=workbench_dprime_dossier,
        )
    except DPrimeModelReviewAssessmentError as exc:
        return _blocked_result(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID,
            model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
            assessment_status=ASSESSMENT_STATUS_BLOCKED,
            blocker_detail=str(exc),
            prompt_license_ref=license_obj.to_ref(),
        )

    prompt = build_dprime_model_review_prompt(
        input_packet=packet.to_dict(),
        transient_bounded_evidence_window=packet.transient_bounded_evidence_window,
    )
    prompt_meta = prompt_metadata(prompt)
    model_review_ref = _model_review_ref(
        input_packet_ref=packet.ref(),
        prompt_meta=prompt_meta,
        provider_boundary_ref=provider_boundary_status_ref,
        adapter_ref=adapter_status_ref,
        call_count=1,
    )
    prompt_license_ref = license_obj.to_ref()
    call_count = 0
    if license_obj.is_fake_test:
        try:
            call_count = _consume_model_review_call(call_count, limit=1)
            if model_review_callable is None:
                raise DPrimeModelReviewAssessmentError(
                    "D-prime fake/test review requires an injected callable"
                )
            raw_output = model_review_callable(
                prompt,
                input_packet=packet.to_dict(),
                system_prompt=DPRIME_MODEL_REVIEW_SYSTEM_PROMPT,
                license_ref=prompt_license_ref,
                one_shot_provider_boundary_ref=provider_boundary_status_ref,
            )
        except TimeoutError:
            return _blocked_result(
                decision=BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
                model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
                assessment_status=ASSESSMENT_STATUS_BLOCKED,
                blocker_detail="D-prime model review timed out and failed closed",
                input_packet_ref=packet.ref(),
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                call_count=call_count,
            )
        except Exception as exc:
            return _blocked_result(
                decision=BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
                model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
                assessment_status=ASSESSMENT_STATUS_BLOCKED,
                blocker_detail=(
                    "D-prime model review callable failed closed: "
                    f"{type(exc).__name__}"
                ),
                input_packet_ref=packet.ref(),
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                call_count=call_count,
            )
    else:
        invocation = invoke_dprime_one_shot_model_review_adapter(
            one_shot_model_review_adapter,
            prompt=prompt,
            input_packet=packet.to_dict(),
            system_prompt=DPRIME_MODEL_REVIEW_SYSTEM_PROMPT,
            license_ref=prompt_license_ref,
            one_shot_provider_boundary_ref=provider_boundary_status_ref,
            one_shot_model_review_adapter_ref=adapter_status_ref,
        )
        call_count = invocation.call_count
        if invocation.timed_out:
            return _blocked_result(
                decision=BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
                model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
                assessment_status=ASSESSMENT_STATUS_BLOCKED,
                blocker_detail="D-prime model review timed out and failed closed",
                input_packet_ref=packet.ref(),
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                call_count=call_count,
            )
        if not invocation.ok:
            decision = (
                invocation.error_type
                if invocation.error_type in DPRIME_MODEL_REVIEW_TRANSPORT_BLOCKERS
                else BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED
            )
            return _blocked_result(
                decision=decision,
                model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
                assessment_status=ASSESSMENT_STATUS_BLOCKED,
                blocker_detail=(
                    "D-prime model review adapter failed closed: "
                    f"{invocation.error_type or 'unknown'}"
                ),
                input_packet_ref=packet.ref(),
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                call_count=call_count,
            )
        raw_output = invocation.transient_model_review_output

    try:
        assessment_payload = _normalized_assessment_payload(
            raw_output,
            packet=packet,
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
        )
    except (
        DPrimeModelReviewAssessmentError,
        assessment_validation.DPrimeAssessmentValidationError,
    ) as exc:
        return _blocked_result(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID,
            model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
            assessment_status=ASSESSMENT_STATUS_INVALID,
            blocker_detail=_model_review_output_invalid_blocker_detail(exc),
            input_packet_ref=packet.ref(),
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            call_count=call_count,
        )

    try:
        validation = assessment_validation.validate_evidence_relative_support_assessment(
            assessment_payload,
        )
    except assessment_validation.DPrimeAssessmentValidationError as exc:
        return _blocked_result(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID,
            model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
            assessment_status=ASSESSMENT_STATUS_INVALID,
            blocker_detail=_model_review_output_invalid_blocker_detail(exc),
            input_packet_ref=packet.ref(),
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            call_count=call_count,
        )
    assessment_ref = dict(validation.assessment_ref)
    return _result_from_validation(
        validation=validation,
        input_packet_ref=packet.ref(),
        model_review_ref=model_review_ref,
        prompt_license_ref=prompt_license_ref,
        call_count=call_count,
        assessment_ref=assessment_ref,
        assessment_material_ref=_assessment_material_ref(assessment_payload),
    )


def build_dprime_model_review_input_packet(
    *,
    evidence_frame_preflight: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    source_evidence_admission_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    negative_control_profile_ref: Mapping[str, Any],
    assessment_validator_status: str,
    one_shot_provider_boundary_ref: Mapping[str, Any] | None = None,
    one_shot_model_review_adapter_ref: Mapping[str, Any] | None = None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
) -> DPrimeModelReviewInputPacket:
    """Build safe retained input plus a transient bounded evidence window."""

    preflight = _preflight_payload(evidence_frame_preflight)
    if preflight.get("preflight_status") != "passed":
        raise DPrimeModelReviewAssessmentError("D-prime preflight is not passed")
    frame_ref = _safe_mapping(preflight.get("frame_ref"))
    preflight_digest = _clean_text(frame_ref.get("frame_digest"), limit=128)
    if not preflight_digest:
        raise DPrimeModelReviewAssessmentError("D-prime preflight digest is missing")

    profile_ref = _safe_mapping(negative_control_profile_ref)
    profile_digest = _clean_text(profile_ref.get("profile_digest"), limit=128)
    if not profile_digest:
        raise DPrimeModelReviewAssessmentError(
            "D-prime negative-control profile digest is missing"
        )
    profile_validation = negative_controls.validate_negative_control_profile(
        negative_controls.build_default_negative_control_profile()
    )
    if not profile_validation.passed:
        raise DPrimeModelReviewAssessmentError(
            profile_validation.blocker_detail
            or "D-prime negative-control profile failed validation"
        )
    expected_profile_ref = _safe_mapping(profile_validation.profile_ref)
    if profile_ref.get("profile_id") != expected_profile_ref.get("profile_id"):
        raise DPrimeModelReviewAssessmentError(
            "D-prime negative-control profile ref does not match default profile"
        )
    if profile_digest != expected_profile_ref.get("profile_digest"):
        raise DPrimeModelReviewAssessmentError(
            "D-prime negative-control profile digest does not match default profile"
        )
    if assessment_validator_status != "available":
        raise DPrimeModelReviewAssessmentError(
            "D-prime assessment validator is not available"
        )

    admission = _safe_mapping(source_evidence_admission_ref)
    reference = _matching_readable_reference(
        fetch_read_content_packet,
        expected_candidate_id=_clean_text(admission.get("candidate_id"), limit=320),
        expected_reference_id=_clean_text(admission.get("reference_id"), limit=320),
    )
    if not reference:
        raise DPrimeModelReviewAssessmentError(
            "matching readable sanitized content reference is missing"
        )
    window = _transient_evidence_window(reference)
    selector_ref = _selector_ref(reference, frame_ref=frame_ref)
    workbench_dossier = _workbench_dprime_dossier_packet(workbench_dprime_dossier)
    workbench_ref = (
        _support_assessment_safe_workbench_dossier_ref(
            workbench_dprime_dossier_ref(workbench_dossier)
        )
        if workbench_dossier
        else {}
    )
    component_lineage_ref = _component_ref(component_ref, reference)
    binding_ref = _component_answer_type_binding_ref(
        component_ref=component_lineage_ref,
        workbench_dprime_dossier=workbench_dossier,
    )
    safe_packet = _without_empty(
        {
            "schema_version": DPRIME_MODEL_REVIEW_INPUT_SCHEMA_VERSION,
            "phase": DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
            "preflight_ref": frame_ref,
            "preflight_digest": preflight_digest,
            "negative_control_profile_ref": profile_ref,
            "negative_control_profile_digest": profile_digest,
            "assessment_validator_ref": {
                "status": assessment_validator_status,
                "module": "core.dprime_assessment_validation",
            },
            "one_shot_provider_boundary_ref": _one_shot_provider_boundary_ref(
                one_shot_provider_boundary_ref
            ),
            "one_shot_model_review_adapter_ref": (
                _one_shot_model_review_adapter_ref(one_shot_model_review_adapter_ref)
            ),
            "source_evidence_custody_ref": _source_evidence_custody_ref(admission),
            "content_reference_ref": _content_reference_ref(reference),
            "selector_ref": selector_ref,
            "component_ref": _component_ref_with_binding(
                component_lineage_ref,
                binding_ref,
            ),
            "source_obligation_ref": _source_obligation_ref(source_obligation_ref),
            "component_answer_type_binding_ref": binding_ref,
            "current_answer_contract_ref": _safe_mapping(
                reference.get("current_answer_contract_ref")
            ),
            "current_answer_contract_digest": reference.get(
                "current_answer_contract_digest"
            ),
            "evidence_window_ref": _evidence_window_ref(reference),
            "selected_window_diagnostic_ref": _selected_window_diagnostic_ref(
                reference,
                transient_bounded_evidence_window=window,
            ),
            "workbench_dprime_dossier": workbench_dossier,
            "workbench_dprime_dossier_ref": workbench_ref,
            "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
            "forbidden_surfaces": [
                "ValidatedSupportProposal",
                "EvidenceRelativeAnalysisPacket",
                "RunKernel support admission request",
                "SemanticObservation",
                "ComponentCoverage",
                "citation eligibility",
                "source-obligation satisfaction",
                "SufficiencyReadiness",
                "FinalAnswerPacket",
                "Author",
                "answer text",
                "product correctness",
                "analysis_gap_search_proposal",
            ],
        }
    )
    _reject_forbidden_payload(
        safe_packet,
        forbidden_keys=_FORBIDDEN_INPUT_KEYS,
        context="D-prime model-review input packet",
    )
    digest = _digest_json(safe_packet)
    return DPrimeModelReviewInputPacket(
        safe_packet={**safe_packet, "input_packet_digest": digest},
        transient_bounded_evidence_window=window,
        input_packet_digest=digest,
    )


def _result_from_validation(
    *,
    validation: assessment_validation.AssessmentValidationResult,
    input_packet_ref: Mapping[str, Any],
    model_review_ref: Mapping[str, Any],
    prompt_license_ref: Mapping[str, Any],
    call_count: int,
    assessment_ref: Mapping[str, Any],
    assessment_material_ref: Mapping[str, Any],
) -> DPrimeModelReviewAssessmentResult:
    status = validation.validation_status
    relation = validation.support_relation
    if status == assessment_validation.ASSESSMENT_SCHEMA_VALID:
        try:
            proposal = build_validated_support_proposal_from_assessment(
                assessment_ref=assessment_ref,
                input_packet_ref=input_packet_ref,
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                assessment_validation_status=status,
                support_relation=relation,
            )
        except DPrimeSupportProposalSchemaError as exc:
            return DPrimeModelReviewAssessmentResult(
                decision=BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING,
                model_review_status=MODEL_REVIEW_STATUS_COMPLETED,
                assessment_status=ASSESSMENT_STATUS_ASSESSED,
                blocker_detail=str(exc),
                input_packet_ref=input_packet_ref,
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                assessment_ref=assessment_ref,
                assessment_material_ref=assessment_material_ref,
                assessment_validation_status=status,
                support_relation=relation,
                proposal_validation_status=(
                    BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING
                ),
                run_kernel_support_admission_status=DPRIME_STATUS_NOT_REACHED,
                call_count=call_count,
            )
        try:
            admission_request = build_run_kernel_support_proposal_admission_request(
                proposal
            )
        except DPrimeSupportProposalSchemaError as exc:
            return DPrimeModelReviewAssessmentResult(
                decision=BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING,
                model_review_status=MODEL_REVIEW_STATUS_COMPLETED,
                assessment_status=ASSESSMENT_STATUS_ASSESSED,
                blocker_detail=str(exc),
                input_packet_ref=input_packet_ref,
                model_review_ref=model_review_ref,
                prompt_license_ref=prompt_license_ref,
                assessment_ref=assessment_ref,
                assessment_material_ref=assessment_material_ref,
                assessment_validation_status=status,
                support_relation=relation,
                proposal_validation_status=(
                    BLOCKED_DPRIME_SUPPORT_PROPOSAL_PACKAGING
                ),
                run_kernel_support_admission_status=DPRIME_STATUS_NOT_REACHED,
                call_count=call_count,
            )
        admission_request_ref = _run_kernel_admission_request_ref(
            admission_request.to_dict()
        )
        return DPrimeModelReviewAssessmentResult(
            decision=BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING,
            model_review_status=MODEL_REVIEW_STATUS_COMPLETED,
            assessment_status=ASSESSMENT_STATUS_ASSESSED,
            blocker_detail=(
                "D-prime support proposal validated; RunKernel admission request "
                "is ready and RunKernel decision is not made"
            ),
            input_packet_ref=input_packet_ref,
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            assessment_ref=assessment_ref,
            assessment_material_ref=assessment_material_ref,
            assessment_validation_status=status,
            support_relation=relation,
            proposal_validation_status=DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            support_proposal_validation_ref=proposal.validation_result.to_dict(),
            validated_support_proposal_ref=proposal.proposal_ref,
            validated_support_proposal_available=True,
            run_kernel_support_admission_status=admission_request.request_status,
            run_kernel_support_admission_request_ref=admission_request_ref,
            call_count=call_count,
        )
    if status == assessment_validation.ASSESSMENT_ABSTAINED:
        return DPrimeModelReviewAssessmentResult(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED,
            model_review_status=MODEL_REVIEW_STATUS_ABSTAINED,
            assessment_status=ASSESSMENT_STATUS_ABSTAINED,
            blocker_detail="D-prime model review abstained and failed closed",
            input_packet_ref=input_packet_ref,
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            assessment_ref=assessment_ref,
            assessment_material_ref=assessment_material_ref,
            assessment_validation_status=status,
            support_relation=relation,
            call_count=call_count,
        )
    if status == assessment_validation.ASSESSMENT_NON_SUPPORT:
        return DPrimeModelReviewAssessmentResult(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT,
            model_review_status=MODEL_REVIEW_STATUS_COMPLETED,
            assessment_status=ASSESSMENT_STATUS_NON_SUPPORT,
            blocker_detail="D-prime model review returned non-support",
            input_packet_ref=input_packet_ref,
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            assessment_ref=assessment_ref,
            assessment_material_ref=assessment_material_ref,
            assessment_validation_status=status,
            support_relation=relation,
            call_count=call_count,
        )
    if status == assessment_validation.ASSESSMENT_CHALLENGE_RECOMMENDED:
        return DPrimeModelReviewAssessmentResult(
            decision=BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
            model_review_status=MODEL_REVIEW_STATUS_COMPLETED,
            assessment_status=ASSESSMENT_STATUS_CHALLENGE_RECOMMENDED,
            blocker_detail=(
                "D-prime model review recommends challenge; RunKernel challenge "
                "is not licensed"
            ),
            input_packet_ref=input_packet_ref,
            model_review_ref=model_review_ref,
            prompt_license_ref=prompt_license_ref,
            assessment_ref=assessment_ref,
            assessment_material_ref=assessment_material_ref,
            assessment_validation_status=status,
            support_relation=relation,
            call_count=call_count,
        )
    return _blocked_result(
        decision=BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID,
        model_review_status=MODEL_REVIEW_STATUS_BLOCKED,
        assessment_status=ASSESSMENT_STATUS_INVALID,
        blocker_detail=(
            "D-prime model review assessment failed validation: "
            + "; ".join(validation.errors or validation.blockers or ())
        ),
        input_packet_ref=input_packet_ref,
        model_review_ref=model_review_ref,
        prompt_license_ref=prompt_license_ref,
        assessment_ref=assessment_ref,
        assessment_material_ref=assessment_material_ref,
        assessment_validation_status=status,
        support_relation=relation,
        call_count=call_count,
    )


def _normalized_assessment_payload(
    raw_output: Any,
    *,
    packet: DPrimeModelReviewInputPacket,
    model_review_ref: Mapping[str, Any],
    prompt_license_ref: Mapping[str, Any],
) -> dict[str, Any]:
    parsed = _parse_output_mapping(raw_output)
    _reject_forbidden_payload(
        parsed,
        forbidden_keys=_FORBIDDEN_OUTPUT_KEYS,
        context="D-prime model-review output",
    )
    input_packet = packet.to_dict()
    payload = dict(parsed)
    support_relation = _clean_text(payload.get("support_relation"), limit=160)
    challenge_normalization_ref = _challenge_relation_normalization_ref(payload)
    payload.setdefault(
        "assessment_id",
        "dprime-assessment:"
        f"{packet.input_packet_digest[:16]}:{support_relation or 'unknown'}",
    )
    payload["record_kind"] = "EvidenceRelativeSupportAssessment"
    payload["preflight_ref"] = _safe_mapping(input_packet.get("preflight_ref"))
    payload["preflight_digest"] = input_packet["preflight_digest"]
    payload["preflight_status"] = "passed"
    payload["negative_control_profile_ref"] = _safe_mapping(
        input_packet.get("negative_control_profile_ref")
    )
    payload["negative_control_profile_digest"] = input_packet[
        "negative_control_profile_digest"
    ]
    payload["negative_control_profile_status"] = "available"
    payload["selector_ref"] = _safe_mapping(input_packet.get("selector_ref"))
    payload["component_ref"] = _safe_mapping(input_packet.get("component_ref"))
    payload["source_obligation_ref"] = _safe_mapping(
        input_packet.get("source_obligation_ref")
    )
    payload["model_review_ref"] = dict(model_review_ref)
    payload["prompt_license_ref"] = dict(prompt_license_ref)
    payload.setdefault(
        "closed_surface_flags",
        dict(_ASSESSMENT_CLOSED_SURFACE_FLAGS),
    )
    payload["assessment_digest"] = ""
    payload["assessment_digest"] = assessment_validation.assessment_digest(payload)
    if challenge_normalization_ref:
        payload["challenge_relation_normalization_ref"] = challenge_normalization_ref
    return payload


def _challenge_relation_normalization_ref(payload: dict[str, Any]) -> dict[str, Any]:
    relation = _normalize_key(payload.get("support_relation"))
    if relation not in assessment_validation.CHALLENGE_RELATIONS:
        return {}

    model_provided = payload.get("challenge_recommended") is True
    derived = not model_provided
    if derived:
        payload["challenge_recommended"] = True
    return {
        "challenge_recommended_model_provided": model_provided,
        "challenge_recommended_derived_from_support_relation": derived,
        "challenge_relation": relation,
        "normalization_is_conservative": True,
        "support_not_created": True,
    }


def _assessment_material_ref(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(payload)
    return _without_empty(
        {
            "record_kind": safe.get("record_kind"),
            "assessment_id": safe.get("assessment_id"),
            "assessment_digest": safe.get("assessment_digest"),
            "preflight_digest": safe.get("preflight_digest"),
            "negative_control_profile_digest": safe.get(
                "negative_control_profile_digest"
            ),
            "selector_ref": _safe_mapping(safe.get("selector_ref")),
            "component_ref": _safe_mapping(safe.get("component_ref")),
            "source_obligation_ref": _safe_mapping(safe.get("source_obligation_ref")),
            "source_proposition": safe.get("source_proposition"),
            "answer_component_claim": _safe_mapping(
                safe.get("answer_component_claim")
            ),
            "support_relation": safe.get("support_relation"),
            "required_qualifiers": _text_tuple(safe.get("required_qualifiers")),
            "observed_qualifiers": _text_tuple(safe.get("observed_qualifiers")),
            "missing_qualifiers": _text_tuple(safe.get("missing_qualifiers")),
            "scope_check": _safe_mapping(safe.get("scope_check")),
            "currentness_check": _safe_mapping(safe.get("currentness_check")),
            "contradiction_check": _safe_mapping(safe.get("contradiction_check")),
            "challenge_relation_normalization_ref": _safe_mapping(
                safe.get("challenge_relation_normalization_ref")
            ),
            "closed_surface_flags": _safe_mapping(safe.get("closed_surface_flags")),
            "support_assessment_only": True,
            "admitted_support": False,
        }
    )


def _parse_output_mapping(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, Mapping):
        return dict(raw_output)
    if isinstance(raw_output, str):
        try:
            parsed = json.loads(raw_output)
        except Exception as exc:
            raise DPrimeModelReviewAssessmentError(
                "D-prime model-review output was not valid JSON"
            ) from exc
        if isinstance(parsed, Mapping):
            return dict(parsed)
    raise DPrimeModelReviewAssessmentError(
        "D-prime model-review output must be a JSON object"
    )


def _model_review_output_invalid_blocker_detail(exc: Exception) -> str:
    if isinstance(exc, assessment_validation.DPrimeAssessmentValidationError):
        return "D-prime model review output failed deterministic assessment validation"
    return str(exc)


def _blocked_result(
    *,
    decision: str,
    model_review_status: str,
    assessment_status: str,
    blocker_detail: str,
    input_packet_ref: Mapping[str, Any] | None = None,
    model_review_ref: Mapping[str, Any] | None = None,
    prompt_license_ref: Mapping[str, Any] | None = None,
    assessment_ref: Mapping[str, Any] | None = None,
    assessment_material_ref: Mapping[str, Any] | None = None,
    assessment_validation_status: str = "not reached",
    support_relation: str | None = None,
    call_count: int = 0,
) -> DPrimeModelReviewAssessmentResult:
    return DPrimeModelReviewAssessmentResult(
        decision=decision,
        model_review_status=model_review_status,
        assessment_status=assessment_status,
        blocker_detail=blocker_detail,
        input_packet_ref=dict(input_packet_ref or {}),
        model_review_ref=dict(model_review_ref or {}),
        prompt_license_ref=dict(prompt_license_ref or {}),
        assessment_ref=dict(assessment_ref or {}),
        assessment_material_ref=dict(assessment_material_ref or {}),
        assessment_validation_status=assessment_validation_status,
        support_relation=support_relation,
        call_count=call_count,
    )


def _license_blocker(
    license_obj: DPrimeModelReviewLicense,
    model_review_callable: ModelReviewCallable | None,
    *,
    provider_boundary_validation: DPrimeOneShotProviderBoundaryValidation,
    adapter_validation: DPrimeOneShotModelReviewAdapterValidation,
) -> str | None:
    if not license_obj.enabled:
        return "D-prime model review is not licensed in this phase"
    callable_kind = _normalize_key(license_obj.callable_kind)
    if callable_kind not in _MODEL_REVIEW_CALLABLE_KINDS:
        return "D-prime model review callable kind is unsupported"
    if license_obj.provider or license_obj.model:
        return "provider/model selection is not licensed for this phase"
    if license_obj.max_model_review_calls != 1:
        return "D-prime model review requires exactly one-call cap"
    if license_obj.retry_policy != "forbidden":
        return "D-prime model review retries are forbidden"
    if license_obj.timeout_policy != "fail_closed":
        return "D-prime model review timeout policy must fail closed"
    if license_obj.is_fake_test:
        if model_review_callable is None:
            return "D-prime fake/test review requires an injected review callable"
        if license_obj.one_shot_adapter_ref:
            return "D-prime fake/test review cannot carry a real adapter ref"
        return None
    if not license_obj.is_real_one_shot:
        return "D-prime model review license must be fake/test or real_one_shot"

    if model_review_callable is not None:
        return (
            "D-prime real model review requires the product-owned one-shot "
            "adapter contract, not a bare callable"
        )
    if not license_obj.one_shot_adapter_ref:
        return "D-prime real model review requires a proven one-shot adapter ref"
    if not provider_boundary_validation.approved:
        return "D-prime real model review requires approved one-shot provider boundary"
    boundary_ref = _safe_mapping(provider_boundary_validation.boundary_ref)
    if boundary_ref.get("test_only") is True:
        return "D-prime real model review cannot use a test-only provider boundary"
    if (
        _clean_text(boundary_ref.get("one_shot_adapter_ref"), limit=320)
        != license_obj.one_shot_adapter_ref
    ):
        return "D-prime real model review adapter ref does not match boundary"
    if not adapter_validation.configured:
        return "D-prime real model review requires configured adapter contract"
    adapter_ref = _safe_mapping(adapter_validation.adapter_ref)
    if _clean_text(adapter_ref.get("adapter_ref"), limit=320) != (
        license_obj.one_shot_adapter_ref
    ):
        return "D-prime real model review adapter contract ref does not match license"
    if _clean_text(adapter_ref.get("provider_boundary_ref"), limit=320) != (
        _clean_text(boundary_ref.get("boundary_id"), limit=320)
    ):
        return "D-prime real model review adapter boundary ref does not match boundary"
    if _clean_text(adapter_ref.get("provider_model_approval_ref"), limit=320) != (
        _clean_text(boundary_ref.get("provider_model_approval_ref"), limit=320)
    ):
        return (
            "D-prime real model review adapter approval ref does not match boundary"
        )
    return None


def _coerce_license(
    value: Mapping[str, Any] | DPrimeModelReviewLicense | None,
) -> DPrimeModelReviewLicense:
    if isinstance(value, DPrimeModelReviewLicense):
        return value
    if isinstance(value, Mapping):
        return DPrimeModelReviewLicense.from_mapping(value)
    return DPrimeModelReviewLicense()


def _consume_model_review_call(call_count: int, *, limit: int) -> int:
    if call_count >= limit:
        raise DPrimeModelReviewAssessmentError("D-prime one-call cap exceeded")
    return call_count + 1


def _model_review_ref(
    *,
    input_packet_ref: Mapping[str, Any],
    prompt_meta: Mapping[str, Any],
    provider_boundary_ref: Mapping[str, Any],
    adapter_ref: Mapping[str, Any],
    call_count: int,
) -> dict[str, Any]:
    payload = {
        "model_review_id": (
            "dprime-model-review:"
            f"{input_packet_ref.get('input_packet_digest', '')[:16]}"
        ),
        "phase": DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
        "input_packet_ref": dict(input_packet_ref),
        "one_shot_provider_boundary_ref": _one_shot_provider_boundary_ref(
            provider_boundary_ref
        ),
        "one_shot_model_review_adapter_ref": _one_shot_model_review_adapter_ref(
            adapter_ref
        ),
        "prompt_schema_version": DPRIME_MODEL_REVIEW_PROMPT_SCHEMA_VERSION,
        "prompt_hash": prompt_meta.get("prompt_hash"),
        "prompt_length": prompt_meta.get("prompt_length"),
        "call_count": call_count,
        "max_model_review_calls": 1,
        "retry_count": 0,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
        "real_provider_selected": False,
        "real_model_call_authorized": False,
    }
    return {**payload, "model_review_digest": _digest_json(payload)}


def _preflight_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise DPrimeModelReviewAssessmentError(
            "D-prime preflight must be a mapping"
        )
    safe = dict(value)
    if "frame_ref" not in safe and safe.get("record_kind") != "EvidenceFramePreflight":
        safe = {"preflight_status": "passed", "frame_ref": safe}
    return safe


def _matching_readable_reference(
    packet: Mapping[str, Any],
    *,
    expected_candidate_id: str | None,
    expected_reference_id: str | None,
) -> dict[str, Any]:
    if not expected_candidate_id or not expected_reference_id:
        return {}
    for item in _safe_sequence(packet.get("reference_records")):
        reference = _safe_mapping(item)
        if reference.get("fetch_read_status") != "readable":
            continue
        if reference.get("candidate_id") != expected_candidate_id:
            continue
        if reference.get("reference_id") != expected_reference_id:
            continue
        return reference
    return {}


def _transient_evidence_window(reference: Mapping[str, Any]) -> str:
    text = _clean_raw_text(reference.get("bounded_text"))
    if not text:
        raise DPrimeModelReviewAssessmentError(
            "transient bounded sanitized evidence window is missing"
        )
    if reference.get("bounded_text_sanitized") is not True:
        raise DPrimeModelReviewAssessmentError(
            "transient evidence window is not marked sanitized"
        )
    if reference.get("bounded_text_bounded") is not True:
        raise DPrimeModelReviewAssessmentError(
            "transient evidence window is not marked bounded"
        )
    if len(text) > MAX_TRANSIENT_EVIDENCE_WINDOW_CHARS:
        raise DPrimeModelReviewAssessmentError(
            "transient evidence window exceeds D-prime model-review limit"
        )
    count = _bounded_int(reference.get("bounded_character_count"), default=0)
    if count != len(text):
        raise DPrimeModelReviewAssessmentError(
            "transient evidence window count mismatch"
        )
    if reference.get("excerpt_digest") != _digest_json({"bounded_text": text}):
        raise DPrimeModelReviewAssessmentError(
            "transient evidence window digest mismatch"
        )
    return text


def _selector_ref(
    reference: Mapping[str, Any],
    *,
    frame_ref: Mapping[str, Any],
) -> dict[str, Any]:
    selector = _safe_mapping(reference.get("bounded_text_selection"))
    if selector:
        if selector.get("bounded_text_digest") != reference.get("excerpt_digest"):
            raise DPrimeModelReviewAssessmentError("selector digest mismatch")
        if _bounded_int(selector.get("bounded_text_char_count"), default=-1) != (
            reference.get("bounded_character_count")
        ):
            raise DPrimeModelReviewAssessmentError("selector count mismatch")
        return {
            "selector_kind": "bounded_selection_metadata",
            "bounded_content_digest": reference.get("excerpt_digest"),
            "bounded_character_count": reference.get("bounded_character_count"),
            "selected_window_start_offset": selector.get(
                "selected_window_start_offset"
            ),
            "selected_window_end_offset": selector.get("selected_window_end_offset"),
            "selector_not_semantic_support": True,
        }
    frame_selector = _safe_mapping(frame_ref.get("selector_ref"))
    if frame_selector:
        return frame_selector
    return {
        "selector_kind": "bounded_digest_count_surrogate",
        "bounded_content_digest": reference.get("excerpt_digest"),
        "bounded_character_count": reference.get("bounded_character_count"),
        "selector_not_semantic_support": True,
    }


def _source_evidence_custody_ref(admission: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "status": admission.get("status"),
            "owner": admission.get("owner"),
            "schema_version": admission.get("schema_version"),
            "custody_ref_digest": admission.get("ref_digest"),
            "ledger_observation_id": admission.get("observation_id"),
            "fetch_read_packet_id": admission.get("fetch_read_content_packet_id"),
            "fetch_read_packet_digest": admission.get(
                "fetch_read_content_packet_digest"
            ),
            "candidate_id": admission.get("candidate_id"),
            "reference_id": admission.get("reference_id"),
            "reference_digest": admission.get("reference_digest"),
            "custody_record_count": admission.get("custody_record_count"),
            "readable_record_count": admission.get("readable_record_count"),
            "custody_is_not_semantic_support": True,
        }
    )


def _run_kernel_admission_request_ref(request: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(request)
    return _without_empty(
        {
            "record_kind": safe.get("record_kind"),
            "request_status": safe.get("request_status"),
            "request_digest": _digest_json(safe),
            "support_proposal_ref": _safe_mapping(
                safe.get("support_proposal_ref")
            ),
            "validation_result_ref": _safe_mapping(
                safe.get("validation_result_ref")
            ),
        }
    )


def _content_reference_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "bounded_content_digest": reference.get("excerpt_digest"),
            "bounded_character_count": reference.get("bounded_character_count"),
            "fetch_read_status": reference.get("fetch_read_status"),
            "content_ref_is_not_semantic_support": True,
        }
    )


def _component_ref(
    component_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(component_ref)
    binding_ref = _support_assessment_safe_component_answer_type_binding_ref(
        maybe_current_source_component_answer_type_binding_ref(
            _safe_mapping(safe.get("component_answer_type_binding"))
        )
        or _safe_mapping(safe.get("component_answer_type_binding_ref"))
    )
    return _without_empty(
        {
            "component_id": safe.get("component_id") or reference.get("component_id"),
            "component_digest": safe.get("component_digest")
            or binding_ref.get("component_digest"),
            "current_answer_contract_digest": safe.get(
                "current_answer_contract_digest"
            )
            or reference.get("current_answer_contract_digest"),
            "component_text": safe.get("component_text")
            or binding_ref.get("component_text"),
            "fact_kind": safe.get("fact_kind") or binding_ref.get("fact_kind"),
            "requested_answer_type": safe.get("requested_answer_type")
            or binding_ref.get("requested_answer_type"),
            "expected_value_shape": safe.get("expected_value_shape")
            or binding_ref.get("expected_value_shape"),
            "claim_under_test": safe.get("claim_under_test")
            or binding_ref.get("claim_under_test"),
            "component_answer_type_binding_ref": binding_ref,
            "component_coverage_bound": False,
            "lineage_only": True,
        }
    )


def _component_answer_type_binding_ref(
    *,
    component_ref: Mapping[str, Any],
    workbench_dprime_dossier: Mapping[str, Any],
) -> dict[str, Any]:
    component = _safe_mapping(component_ref)
    dossier = _safe_mapping(workbench_dprime_dossier)
    return _support_assessment_safe_component_answer_type_binding_ref(
        maybe_current_source_component_answer_type_binding_ref(
            _safe_mapping(component.get("component_answer_type_binding"))
        )
        or _safe_mapping(component.get("component_answer_type_binding_ref"))
        or maybe_current_source_component_answer_type_binding_ref(
            _safe_mapping(dossier.get("component_answer_type_binding"))
        )
        or _safe_mapping(dossier.get("component_answer_type_binding_ref"))
    )


def _component_ref_with_binding(
    component_ref: Mapping[str, Any],
    binding_ref: Mapping[str, Any],
) -> dict[str, Any]:
    component = dict(component_ref)
    binding = _support_assessment_safe_component_answer_type_binding_ref(binding_ref)
    if not binding:
        return component
    component["component_answer_type_binding_ref"] = binding
    for target_key in (
        "component_text",
        "fact_kind",
        "requested_answer_type",
        "expected_value_shape",
        "claim_under_test",
    ):
        if component.get(target_key) in (None, "", [], {}):
            component[target_key] = binding.get(target_key)
    if not component.get("component_digest"):
        component["component_digest"] = binding.get("component_digest")
    return _without_empty(component)


def _support_assessment_safe_component_answer_type_binding_ref(
    binding_ref: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(binding_ref)
    if not safe:
        return {}
    return _without_empty(
        {
            "schema_version": safe.get("schema_version"),
            "binding_kind": safe.get("binding_kind"),
            "binding_id": safe.get("binding_id"),
            "binding_digest": safe.get("binding_digest"),
            "component_id": safe.get("component_id"),
            "component_digest": safe.get("component_digest"),
            "current_answer_contract_digest": safe.get(
                "current_answer_contract_digest"
            ),
            "component_text": safe.get("component_text"),
            "source_obligation_id": safe.get("source_obligation_id"),
            "source_obligation_text": safe.get("source_obligation_text"),
            "fact_kind": safe.get("fact_kind"),
            "requested_answer_type": safe.get("requested_answer_type"),
            "claim_under_test": safe.get("claim_under_test"),
            "expected_value_shape": safe.get("expected_value_shape"),
            "expected_value_token_kinds": list(
                _safe_sequence(safe.get("expected_value_token_kinds"))
            ),
            "adjacent_claim_exclusions": list(
                _safe_sequence(safe.get("adjacent_claim_exclusions"))
            ),
            "adjacent_claims_do_not_satisfy_requested_answer_type": (
                safe.get("adjacent_claims_do_not_satisfy_requested_answer_type")
                is True
            ),
            "lineage_only": safe.get("lineage_only") is True,
            "binding_is_contract_lineage": (
                safe.get("binding_is_contract_lineage") is True
            ),
            "binding_is_not_evidence": safe.get("binding_is_not_evidence") is True,
            "binding_is_not_answer_authority": (
                safe.get("binding_is_not_answer_authority") is True
            ),
        }
    )


def _support_assessment_safe_workbench_dossier_ref(
    dossier_ref: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(dossier_ref)
    if not safe:
        return {}
    out = dict(safe)
    binding = _support_assessment_safe_component_answer_type_binding_ref(
        _safe_mapping(out.get("component_answer_type_binding_ref"))
    )
    if binding:
        out["component_answer_type_binding_ref"] = binding
    else:
        out.pop("component_answer_type_binding_ref", None)
    return _without_empty(out)


def _source_obligation_ref(source_obligation_ref: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(source_obligation_ref)
    return {
        "source_obligation_candidate_ids": _text_tuple(
            safe.get("source_obligation_candidate_ids"),
            limit=260,
        ),
        "satisfaction_claimed": False,
        "lineage_only": True,
    }


def _one_shot_provider_boundary_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(value)
    boundary = _safe_mapping(safe.get("boundary_ref"))
    return _without_empty(
        {
            "status": safe.get("status"),
            "blocker_count": len(_text_tuple(safe.get("blockers"), limit=260)),
            "warning_count": len(_text_tuple(safe.get("warnings"), limit=260)),
            "provider_boundary_approved_is_not_semantic_support": (
                safe.get("provider_boundary_approved_is_not_semantic_support")
                is True
            ),
            "real_provider_call_performed": False,
            "real_model_call_performed": False,
            "boundary_ref": _without_empty(
                {
                    "schema_version": boundary.get("schema_version"),
                    "boundary_id": boundary.get("boundary_id"),
                    "phase": boundary.get("phase"),
                    "enabled": boundary.get("enabled"),
                    "default_disabled": boundary.get("default_disabled"),
                    "test_only": boundary.get("test_only"),
                    "provider_model_selection_status": boundary.get(
                        "provider_model_selection_status"
                    ),
                    "provider_model_approval_ref": boundary.get(
                        "provider_model_approval_ref"
                    ),
                    "max_provider_attempts": boundary.get("max_provider_attempts"),
                    "retry_policy": boundary.get("retry_policy"),
                    "fallback_policy": boundary.get("fallback_policy"),
                    "timeout_policy": boundary.get("timeout_policy"),
                    "raw_prompt_retention": boundary.get("raw_prompt_retention"),
                    "raw_model_response_retention": boundary.get(
                        "raw_model_response_retention"
                    ),
                    "provider_payload_retention": boundary.get(
                        "provider_payload_retention"
                    ),
                    "real_call_authorized": boundary.get("real_call_authorized"),
                    "call_count": boundary.get("call_count"),
                    "provider_model_selection_detail_present": boundary.get(
                        "provider_model_selection_detail_present"
                    ),
                    "provider_switching_allowed": boundary.get(
                        "provider_switching_allowed"
                    ),
                    "one_shot_adapter_proven": boundary.get(
                        "one_shot_adapter_proven"
                    ),
                    "one_shot_adapter_ref": boundary.get("one_shot_adapter_ref"),
                    "closed_surface_flags": _safe_mapping(
                        boundary.get("closed_surface_flags")
                    ),
                }
            ),
        }
    )


def _one_shot_model_review_adapter_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    safe = _safe_mapping(value)
    adapter = _safe_mapping(safe.get("adapter_ref"))
    return _without_empty(
        {
            "status": safe.get("status"),
            "blocker_count": len(_text_tuple(safe.get("blockers"), limit=260)),
            "warning_count": len(_text_tuple(safe.get("warnings"), limit=260)),
            "adapter_contract_valid_is_not_semantic_support": (
                safe.get("adapter_contract_valid_is_not_semantic_support") is True
            ),
            "real_provider_call_performed": False,
            "real_model_call_performed": False,
            "adapter_ref": _without_empty(
                {
                    "schema_version": adapter.get("schema_version"),
                    "adapter_ref": adapter.get("adapter_ref"),
                    "phase": DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
                    "adapter_kind": adapter.get("adapter_kind"),
                    "one_shot_adapter_proven": adapter.get(
                        "one_shot_adapter_proven"
                    ),
                    "provider_model_approval_ref": adapter.get(
                        "provider_model_approval_ref"
                    ),
                    "provider_boundary_ref": adapter.get("provider_boundary_ref"),
                    "max_provider_attempts": adapter.get("max_provider_attempts"),
                    "retry_policy": adapter.get("retry_policy"),
                    "fallback_policy": adapter.get("fallback_policy"),
                    "provider_switching_allowed": adapter.get(
                        "provider_switching_allowed"
                    ),
                    "timeout_policy": adapter.get("timeout_policy"),
                    "call_count": adapter.get("call_count"),
                    "raw_prompt_retained": adapter.get("raw_prompt_retained"),
                    "raw_model_response_retained": adapter.get(
                        "raw_model_response_retained"
                    ),
                    "provider_payload_retained": adapter.get(
                        "provider_payload_retained"
                    ),
                    "real_provider_call_performed": False,
                    "real_model_call_performed": False,
                    "provider_model_selection_detail_present": adapter.get(
                        "provider_model_selection_detail_present"
                    ),
                    "candidate_helper": adapter.get("candidate_helper"),
                    "closed_surface_flags": _safe_mapping(
                        adapter.get("closed_surface_flags")
                    ),
                }
            ),
        }
    )


def _evidence_window_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "window_kind": "transient_retained_sanitized_bounded_window",
        "bounded_content_digest": reference.get("excerpt_digest"),
        "bounded_character_count": reference.get("bounded_character_count"),
        "max_window_characters": MAX_TRANSIENT_EVIDENCE_WINDOW_CHARS,
        "passed_in_memory_only": True,
        "window_text_retained": False,
        "window_text_printed": False,
    }


def _selected_window_diagnostic_ref(
    reference: Mapping[str, Any],
    *,
    transient_bounded_evidence_window: str,
) -> dict[str, Any]:
    selection = _safe_mapping(reference.get("bounded_text_selection"))
    required_anchor_count = _bounded_int(
        selection.get("required_anchor_count"),
        default=0,
    )
    matched_anchor_count = _bounded_int(
        selection.get("matched_anchor_count"),
        default=0,
    )
    missing_anchor_count = len(_text_tuple(selection.get("missing_anchors")))
    if required_anchor_count <= 0:
        anchor_match_status = "no_anchor_requirements"
    elif matched_anchor_count == required_anchor_count:
        anchor_match_status = "all_required_anchors_matched"
    elif matched_anchor_count == 0:
        anchor_match_status = "no_required_anchors_matched"
    else:
        anchor_match_status = "partial_required_anchor_match"
    value_token_kind_counts = _value_token_kind_counts(
        transient_bounded_evidence_window
    )
    value_token_count = sum(value_token_kind_counts.values())
    return _without_empty(
        {
            "diagnostic_kind": "selected_transient_evidence_window",
            "diagnostic_only": True,
            "not_semantic_support": True,
            "not_model_decision": True,
            "not_source_obligation_satisfaction": True,
            "not_citation_eligibility": True,
            "bounded_content_digest": reference.get("excerpt_digest"),
            "bounded_character_count": reference.get("bounded_character_count"),
            "selection_strategy": selection.get("selection_strategy"),
            "required_anchor_count": required_anchor_count,
            "matched_anchor_count": matched_anchor_count,
            "missing_anchor_count": missing_anchor_count,
            "anchor_match_status": anchor_match_status,
            "value_token_kind_counts": value_token_kind_counts,
            "value_token_count": value_token_count,
            "value_token_observed": value_token_count > 0,
            "window_text_retained": False,
            "window_text_printed": False,
        }
    )


def _workbench_dprime_dossier_packet(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    dossier = _safe_mapping(value)
    if not dossier:
        return {}
    return _without_empty(
        {
            "schema_version": dossier.get("schema_version"),
            "phase": dossier.get("phase"),
            "dossier_kind": dossier.get("dossier_kind"),
            "dossier_id": dossier.get("dossier_id"),
            "dossier_digest": dossier.get("dossier_digest"),
            "runtime_consumer": dossier.get("runtime_consumer"),
            "dprime_consumer": dossier.get("dprime_consumer"),
            "candidate_evidence_triage_ref": _safe_mapping(
                dossier.get("candidate_evidence_triage_ref")
            ),
            "analyst_workbench_ref": _safe_mapping(
                dossier.get("analyst_workbench_ref")
            ),
            "selected_candidate_ref": _safe_mapping(
                dossier.get("selected_candidate_ref")
            ),
            "top_candidate_ref": _safe_mapping(dossier.get("top_candidate_ref")),
            "dprime_review_candidate_ref": _safe_mapping(
                dossier.get("dprime_review_candidate_ref")
            ),
            "component_answer_type_binding": _safe_mapping(
                dossier.get("component_answer_type_binding")
            ),
            "component_answer_type_binding_ref": (
                maybe_current_source_component_answer_type_binding_ref(
                    _safe_mapping(dossier.get("component_answer_type_binding"))
                )
                or _safe_mapping(dossier.get("component_answer_type_binding_ref"))
            ),
            "strict_answer_support_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(
                    dossier.get("strict_answer_support_candidate_refs")
                )
            ],
            "contextual_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(dossier.get("contextual_candidate_refs"))
            ],
            "overclaim_risk_candidate_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(
                    dossier.get("overclaim_risk_candidate_refs")
                )
            ],
            "role_proposal_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(dossier.get("role_proposal_refs"))
            ],
            "analyst_finding_proposal_refs": [
                _safe_mapping(item)
                for item in _safe_sequence(
                    dossier.get("analyst_finding_proposal_refs")
                )
            ],
            "scrutineer_lane_ref": _safe_mapping(
                dossier.get("scrutineer_lane_ref")
            ),
            "specialist_lane_ref": _safe_mapping(dossier.get("specialist_lane_ref")),
            "economist_lane_ref": _safe_mapping(dossier.get("economist_lane_ref")),
            "analysis_gap_search_proposal_ref": _safe_mapping(
                dossier.get("analysis_gap_search_proposal_ref")
            ),
            "gap_proposal_status": dossier.get("gap_proposal_status"),
            "strict_answer_support_candidate_count": _bounded_int(
                dossier.get("strict_answer_support_candidate_count"),
                default=0,
            ),
            "contextual_candidate_count": _bounded_int(
                dossier.get("contextual_candidate_count"),
                default=0,
            ),
            "overclaim_risk_candidate_count": _bounded_int(
                dossier.get("overclaim_risk_candidate_count"),
                default=0,
            ),
            "source_text_retained": False,
            "product_correctness_claimed": False,
        }
    )


def _value_token_kind_counts(text: str) -> dict[str, int]:
    patterns = {
        "currency": r"\$\s?\d{1,4}(?:\.\d{2})?",
        "percent": r"\b\d{1,3}(?:\.\d+)?%",
        "date_like": r"\b(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?\b",
        "number": r"\b\d+(?:\.\d+)?\b",
    }
    counts: dict[str, int] = {}
    for kind, pattern in patterns.items():
        values = {match.group(0) for match in re.finditer(pattern, text)}
        if values:
            counts[kind] = len(values)
    return counts


def _reject_forbidden_payload(
    value: Any,
    *,
    forbidden_keys: frozenset[str],
    context: str,
) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & forbidden_keys)
    if forbidden:
        raise DPrimeModelReviewAssessmentError(
            f"{context} includes forbidden material"
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeModelReviewAssessmentError(
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


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
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


def _clean_raw_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _bounded_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    return value


__all__ = [
    "ASSESSMENT_STATUS_ABSTAINED",
    "ASSESSMENT_STATUS_ASSESSED",
    "ASSESSMENT_STATUS_BLOCKED",
    "ASSESSMENT_STATUS_CHALLENGE_RECOMMENDED",
    "ASSESSMENT_STATUS_INVALID",
    "ASSESSMENT_STATUS_NON_SUPPORT",
    "DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE",
    "DPRIME_MODEL_REVIEW_INPUT_SCHEMA_VERSION",
    "DPrimeModelReviewAssessmentError",
    "DPrimeModelReviewAssessmentResult",
    "DPrimeModelReviewInputPacket",
    "DPrimeModelReviewLicense",
    "MAX_TRANSIENT_EVIDENCE_WINDOW_CHARS",
    "MODEL_REVIEW_STATUS_BLOCKED",
    "MODEL_REVIEW_STATUS_COMPLETED",
    "MODEL_REVIEW_STATUS_NOT_LICENSED",
    "build_dprime_model_review_input_packet",
    "run_dprime_model_review_assessment",
]
