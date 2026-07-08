"""D-prime validation for AnalystFindingProposal support.

The artifact in this module validates an Analyst proposal against bounded
evidence and candidate/source custody before any RunKernel support admission can
be recommended. It is not evidence admission, not source-obligation
satisfaction, not citation eligibility, not ComponentCoverage, not Sufficiency,
not FAP/Author, and not product correctness.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.current_source_analyst_finding_proposal import (
    ANALYSIS_CLAIM_KIND_CAVEAT,
    ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
    ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
    ANALYSIS_CLAIM_KIND_EXCLUSION,
    ANALYSIS_CLAIM_KIND_GAP,
    ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
    ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
    MODEL_INPUT_EVIDENCE_DEPTH_BOUNDED_EXCERPT,
    MODEL_INPUT_EVIDENCE_DEPTH_LIMITED_NO_EXCERPT,
    MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY,
    MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT,
    SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED,
    AnalystFindingProposalError,
    analyst_finding_proposal_ref,
    validate_analyst_finding_proposal,
)

DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_SCHEMA_VERSION = (
    "dprime_analyst_finding_support_validation_v1"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_INPUT_SCHEMA_VERSION = (
    "dprime_analyst_finding_support_validation_input_v1"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_PHASE = (
    "DPRIME-ANALYST-FINDING-SUPPORT-VALIDATION-01"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_KIND = (
    "dprime_analyst_finding_support_validation"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE = "smart"
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROLE_SURFACE = (
    "dprime_analyst_finding_support_validation"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_RUNTIME_CONSUMER = (
    "DPrime / AnalystFindingProposalSupportValidation"
)
DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROUTE_AUTHORITY = (
    "licensed D-prime validation call"
)

DPRIME_SUPPORT_VALIDATION_SUPPORTED = "supported_by_bounded_evidence"
DPRIME_SUPPORT_VALIDATION_PARTIAL = "partially_supported"
DPRIME_SUPPORT_VALIDATION_UNSUPPORTED = "unsupported_by_bounded_evidence"
DPRIME_SUPPORT_VALIDATION_INSUFFICIENT = "insufficient_bounded_evidence"
DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM = (
    "adjacent_or_excluded_scope_overclaim"
)
DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP = "unreadable_source_gap"
DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL = "invalid_analyst_proposal"
DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_LICENSE = "not_run_missing_license"
DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_ADAPTER = "not_run_missing_adapter"
DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_BOUNDED_EVIDENCE = (
    "not_run_missing_bounded_evidence"
)

PRODUCT_PROOF_BLOCKED_VALIDATION_REQUIRED_BUT_NOT_RUN = (
    "blocked_dprime_validation_required_but_not_run"
)
PRODUCT_PROOF_BLOCKED_VALIDATION_UNSUPPORTED = (
    "blocked_dprime_validation_unsupported"
)
PRODUCT_PROOF_NOT_CLAIMED_PENDING_RUNKERNEL_ADMISSION = (
    "not_claimed_pending_runkernel_admission"
)

_SUPPORTED_STATUSES = frozenset({DPRIME_SUPPORT_VALIDATION_SUPPORTED})
_UNSUPPORTED_STATUSES = frozenset(
    {
        DPRIME_SUPPORT_VALIDATION_UNSUPPORTED,
        DPRIME_SUPPORT_VALIDATION_INSUFFICIENT,
        DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM,
        DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP,
        DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_LICENSE,
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_ADAPTER,
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_BOUNDED_EVIDENCE,
    }
)
_VALIDATION_STATUSES = frozenset(
    {
        DPRIME_SUPPORT_VALIDATION_SUPPORTED,
        DPRIME_SUPPORT_VALIDATION_PARTIAL,
        *_UNSUPPORTED_STATUSES,
    }
)
_ANSWER_CLAIM_KINDS = frozenset(
    {
        ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
        ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
    }
)
_CAVEAT_OR_RISK_KINDS = frozenset(
    {
        ANALYSIS_CLAIM_KIND_CAVEAT,
        ANALYSIS_CLAIM_KIND_EXCLUSION,
        ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
        ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
    }
)
_NON_AUTHORITY_FALSE_FLAGS = {
    "evidence_admitted": False,
    "source_obligation_satisfied": False,
    "citation_eligibility_created": False,
    "component_coverage_created": False,
    "sufficiency_readiness_created": False,
    "final_answer_packet_created": False,
    "author_output_created": False,
    "source_display_opened": False,
    "product_correctness_claimed": False,
}
_RAW_FALSE_FLAGS = {
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "raw_provider_payload_retained": False,
    "raw_source_content_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
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
        "raw_source_text",
        "raw_text",
        "secret",
        "secrets",
        "source_text",
        "token",
        "unbounded_text",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(_NON_AUTHORITY_FALSE_FLAGS) | {
    "admitted_support",
    "answer_created",
    "citation_eligible",
    "citation_rendered",
    "component_coverage_bound",
    "final_answer_packet_ready",
    "source_obligation_authority_claimed",
    "support_admitted",
    "support_claimed",
}
_VALUE_PATTERNS = (
    r"\$\s?\d{1,6}(?:\.\d{2})?",
    r"\b\d{1,3}(?:\.\d+)?%",
    r"\b(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?\b",
    r"\b\d+(?:\.\d+)?\b",
)


class DPrimeAnalystFindingSupportValidationError(ValueError):
    """Raised when D-prime AnalystFinding support validation fails closed."""


def analyst_finding_support_validation_required(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> bool:
    """Return true when a Workbench dossier carries an AnalystFinding ref."""

    dossier = _safe_mapping(workbench_dprime_dossier)
    return bool(
        _safe_mapping(dossier.get("analyst_finding_proposal"))
        or _safe_mapping(dossier.get("analyst_finding_proposal_ref"))
    )


def build_dprime_analyst_finding_support_validation_input_packet(
    *,
    analyst_finding_proposal: Mapping[str, Any] | None = None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
    fetch_read_content_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the safe bounded D-prime input packet for proposal validation."""

    dossier = _safe_mapping(workbench_dprime_dossier)
    proposal = _safe_mapping(analyst_finding_proposal) or _safe_mapping(
        dossier.get("analyst_finding_proposal")
    )
    if not proposal:
        raise DPrimeAnalystFindingSupportValidationError(
            "AnalystFindingProposal support validation requires a proposal"
        )
    try:
        proposal = validate_analyst_finding_proposal(proposal)
    except AnalystFindingProposalError as exc:
        raise DPrimeAnalystFindingSupportValidationError(
            f"AnalystFindingProposal failed custody validation: {exc}"
        ) from None
    _reject_forbidden_or_authority(
        proposal,
        context="D-prime AnalystFinding validation proposal input",
    )
    binding_ref = _safe_mapping(proposal.get("component_answer_type_binding_ref"))
    selected_refs = _safe_refs(
        proposal.get("selected_answer_bearing_candidate_refs")
        or dossier.get("selected_answer_bearing_candidate_refs")
    )
    adjacent_refs = _safe_refs(
        proposal.get("adjacent_context_candidate_refs")
        or dossier.get("adjacent_context_candidate_refs")
    )
    excluded_refs = _safe_refs(
        proposal.get("excluded_scope_candidate_refs")
        or dossier.get("excluded_scope_candidate_refs")
    )
    unreadable_refs = _safe_refs(
        proposal.get("unreadable_high_value_candidate_refs")
        or dossier.get("unreadable_high_value_candidate_refs")
    )
    overclaim_refs = _safe_refs(
        proposal.get("overclaim_risk_candidate_refs")
        or dossier.get("overclaim_risk_candidate_refs")
    )
    candidate_refs = _dedupe_refs(
        [*selected_refs, *adjacent_refs, *excluded_refs, *unreadable_refs, *overclaim_refs]
    )
    bounded_evidence_excerpts = _bounded_evidence_excerpts(
        fetch_read_content_packet,
        candidate_refs=candidate_refs,
    )
    evidence_profile = _evidence_profile(
        bounded_evidence_excerpts=bounded_evidence_excerpts,
        proposal=proposal,
    )
    packet = _without_empty(
        {
            "schema_version": (
                DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_INPUT_SCHEMA_VERSION
            ),
            "phase": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_PHASE,
            "validation_kind": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_KIND,
            "model_role": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE,
            "role_surface": (
                DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROLE_SURFACE
            ),
            "runtime_consumer": (
                DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_RUNTIME_CONSUMER
            ),
            "route_authority": (
                DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROUTE_AUTHORITY
            ),
            "component_answer_type_binding_ref": binding_ref,
            "analyst_finding_proposal_ref": analyst_finding_proposal_ref(proposal),
            "analyst_finding_proposal": _proposal_for_validation(proposal),
            "proposed_answer_claim": _safe_mapping(
                proposal.get("proposed_answer_claim")
            ),
            "analysis_claims": [
                _safe_mapping(item)
                for item in _safe_sequence(proposal.get("analysis_claims"))
            ],
            "source_support_map": _safe_mapping(proposal.get("source_support_map")),
            "caveat_refs": _safe_refs(proposal.get("caveat_refs")),
            "adjacent_claim_exclusion_refs": _safe_refs(
                proposal.get("adjacent_claim_exclusion_refs")
            ),
            "unresolved_gap_refs": _safe_refs(proposal.get("unresolved_gap_refs")),
            "conflict_or_overclaim_risk_refs": _safe_refs(
                proposal.get("conflict_or_overclaim_risk_refs")
            ),
            "candidate_triage_summary_ref": _safe_mapping(
                dossier.get("candidate_triage_summary_ref")
                or proposal.get("candidate_triage_summary_ref")
            ),
            "selected_answer_bearing_candidate_refs": selected_refs,
            "adjacent_context_candidate_refs": adjacent_refs,
            "excluded_scope_candidate_refs": excluded_refs,
            "unreadable_high_value_candidate_refs": unreadable_refs,
            "overclaim_risk_candidate_refs": overclaim_refs,
            "bounded_evidence_excerpts": bounded_evidence_excerpts,
            **evidence_profile,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "live_model_call_run": False,
            **_non_authority_posture(),
        }
    )
    for list_key in (
        "analysis_claims",
        "caveat_refs",
        "adjacent_claim_exclusion_refs",
        "unresolved_gap_refs",
        "conflict_or_overclaim_risk_refs",
        "selected_answer_bearing_candidate_refs",
        "adjacent_context_candidate_refs",
        "excluded_scope_candidate_refs",
        "unreadable_high_value_candidate_refs",
        "overclaim_risk_candidate_refs",
        "bounded_evidence_excerpts",
    ):
        packet.setdefault(list_key, [])
    _reject_forbidden_or_authority(
        _drop_bounded_excerpt_text(packet),
        context="D-prime AnalystFinding validation input packet",
    )
    digest = _digest_json(packet)
    return {
        **packet,
        "input_packet_id": f"dprime-analyst-finding-validation-input:{digest[:20]}",
        "input_packet_digest": digest,
    }


def build_dprime_analyst_finding_support_validation(
    *,
    analyst_finding_proposal: Mapping[str, Any] | None = None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
    fetch_read_content_packet: Mapping[str, Any] | None = None,
    model_output: Mapping[str, Any] | None = None,
    model_calls_attempted: int = 0,
    model_calls_completed: int = 0,
    live_model_call_run: bool = False,
) -> dict[str, Any]:
    """Validate an AnalystFindingProposal and return a non-authority artifact."""

    try:
        input_packet = build_dprime_analyst_finding_support_validation_input_packet(
            analyst_finding_proposal=analyst_finding_proposal,
            workbench_dprime_dossier=workbench_dprime_dossier,
            fetch_read_content_packet=fetch_read_content_packet,
        )
    except DPrimeAnalystFindingSupportValidationError as exc:
        return _blocked_validation(
            status=DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
            reason_codes=("analyst_finding_proposal_invalid",),
            summary=str(exc),
            model_calls_attempted=model_calls_attempted,
            model_calls_completed=model_calls_completed,
            live_model_call_run=live_model_call_run,
        )

    if model_output:
        try:
            validation = _validation_from_model_output(
                input_packet=input_packet,
                model_output=model_output,
                model_calls_attempted=model_calls_attempted,
                model_calls_completed=model_calls_completed,
                live_model_call_run=live_model_call_run,
            )
        except DPrimeAnalystFindingSupportValidationError as exc:
            return _blocked_validation(
                status=DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
                reason_codes=("dprime_model_output_invalid",),
                summary=str(exc),
                analyst_finding_proposal_ref=_safe_mapping(
                    input_packet.get("analyst_finding_proposal_ref")
                ),
                proposed_answer_claim_ref=_proposed_answer_claim_ref(input_packet),
                input_packet_ref=_input_packet_ref(input_packet),
                model_calls_attempted=model_calls_attempted,
                model_calls_completed=model_calls_completed,
                live_model_call_run=live_model_call_run,
            )
    else:
        validation = _deterministic_validation(
            input_packet=input_packet,
            model_calls_attempted=model_calls_attempted,
            model_calls_completed=model_calls_completed,
            live_model_call_run=live_model_call_run,
        )
    return validate_dprime_analyst_finding_support_validation(
        validation,
        input_packet=input_packet,
    )


def validate_dprime_analyst_finding_support_validation(
    value: Mapping[str, Any],
    *,
    input_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a D-prime AnalystFinding support-validation artifact."""

    safe = _safe_mapping(value)
    _reject_forbidden_or_authority(
        safe,
        context="D-prime AnalystFinding support validation",
    )
    if (
        safe.get("schema_version")
        != DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_SCHEMA_VERSION
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation schema mismatch"
        )
    if safe.get("phase") != DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_PHASE:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation phase mismatch"
        )
    if safe.get("validation_kind") != DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_KIND:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation kind mismatch"
        )
    status = _clean_text(safe.get("dprime_validation_status"), limit=120)
    if status not in _VALIDATION_STATUSES:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation status invalid"
        )
    if safe.get("dprime_model_role") != (
        DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation must use SmartModel role"
        )
    if safe.get("role_surface") != (
        DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROLE_SURFACE
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation role surface mismatch"
        )
    if safe.get("runtime_consumer") != (
        DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_RUNTIME_CONSUMER
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation runtime consumer mismatch"
        )
    _validate_boolean_flags(safe)
    _validate_validation_refs(safe, input_packet=input_packet)
    normalized = _json_safe(safe)
    digest_payload = _without_digest(normalized)
    digest = _digest_json(digest_payload)
    declared = _clean_text(safe.get("validation_digest"), limit=128)
    if declared and declared != digest:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation digest mismatch"
        )
    normalized["validation_digest"] = digest
    normalized.setdefault(
        "validation_id",
        f"dprime-analyst-finding-support-validation:{digest[:20]}",
    )
    return normalized


def dprime_analyst_finding_support_validation_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the durable safe validation ref for reports and D-prime status."""

    validation = _safe_mapping(value)
    if not validation:
        return {}
    return _without_empty(
        {
            "schema_version": validation.get("schema_version"),
            "phase": validation.get("phase"),
            "validation_kind": validation.get("validation_kind"),
            "validation_id": validation.get("validation_id"),
            "validation_digest": validation.get("validation_digest"),
            "analyst_finding_proposal_ref": _safe_mapping(
                validation.get("analyst_finding_proposal_ref")
            ),
            "proposed_answer_claim_ref": _safe_mapping(
                validation.get("proposed_answer_claim_ref")
            ),
            "proposed_answer_claim_validation_ref": _safe_mapping(
                validation.get("proposed_answer_claim_validation_ref")
            ),
            "source_support_map_validation_ref": _safe_mapping(
                validation.get("source_support_map_validation_ref")
            ),
            "analysis_claim_validation_refs": _safe_refs(
                validation.get("analysis_claim_validation_refs")
            ),
            "dprime_validation_status": validation.get("dprime_validation_status"),
            "dprime_validation_summary_ref": _safe_mapping(
                validation.get("dprime_validation_summary_ref")
            ),
            "dprime_model_role": validation.get("dprime_model_role"),
            "role_surface": validation.get("role_surface"),
            "runtime_consumer": validation.get("runtime_consumer"),
            "model_calls_attempted": _bounded_int(
                validation.get("model_calls_attempted")
            ),
            "model_calls_completed": _bounded_int(
                validation.get("model_calls_completed")
            ),
            "live_model_call_run": validation.get("live_model_call_run") is True,
            "bounded_evidence_excerpt_available": (
                validation.get("bounded_evidence_excerpt_available") is True
            ),
            "bounded_evidence_excerpt_count": _bounded_int(
                validation.get("bounded_evidence_excerpt_count")
            ),
            "model_assisted_analysis_evidence_depth": validation.get(
                "model_assisted_analysis_evidence_depth"
            ),
            "runkernel_support_admission_recommended": (
                validation.get("runkernel_support_admission_recommended") is True
            ),
            "requires_runkernel_admission": (
                validation.get("requires_runkernel_admission") is True
            ),
            "runkernel_admission_created": False,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "component_coverage_created": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "source_display_opened": False,
            "product_correctness_claimed": False,
        }
    )


def support_validation_allows_runkernel_admission(
    value: Mapping[str, Any] | None,
) -> bool:
    """Return true only for bounded-evidence-supported validation artifacts."""

    validation = _safe_mapping(value)
    return (
        validation.get("dprime_validation_status")
        == DPRIME_SUPPORT_VALIDATION_SUPPORTED
        and validation.get("runkernel_support_admission_recommended") is True
        and validation.get("requires_runkernel_admission") is True
        and validation.get("runkernel_admission_created") is False
    )


def _deterministic_validation(
    *,
    input_packet: Mapping[str, Any],
    model_calls_attempted: int,
    model_calls_completed: int,
    live_model_call_run: bool,
) -> dict[str, Any]:
    proposal = _safe_mapping(input_packet.get("analyst_finding_proposal"))
    claims = [_safe_mapping(item) for item in input_packet.get("analysis_claims") or []]
    claim_validations = [
        _claim_validation(claim, input_packet=input_packet) for claim in claims
    ]
    proposed_answer_validation = _proposed_answer_claim_validation(
        input_packet=input_packet
    )
    support_map_validation = _source_support_map_validation(
        input_packet=input_packet,
        claim_validations=claim_validations,
    )
    status = _overall_status(
        proposed_answer_validation=proposed_answer_validation,
        claim_validations=claim_validations,
        support_map_validation=support_map_validation,
        input_packet=input_packet,
    )
    reason_codes = _overall_reason_codes(
        proposed_answer_validation=proposed_answer_validation,
        claim_validations=claim_validations,
        support_map_validation=support_map_validation,
    )
    summary = _summary_text(status=status, reason_codes=reason_codes)
    return _validation_artifact(
        analyst_finding_proposal_ref=_safe_mapping(
            input_packet.get("analyst_finding_proposal_ref")
        ),
        proposed_answer_claim_ref=_proposed_answer_claim_ref(input_packet),
        proposed_answer_claim_validation=proposed_answer_validation,
        analysis_claim_validations=claim_validations,
        source_support_map_validation=support_map_validation,
        caveat_validation_refs=_validation_refs_by_kind(
            claim_validations,
            {ANALYSIS_CLAIM_KIND_CAVEAT},
        ),
        adjacent_claim_exclusion_validation_refs=_validation_refs_by_kind(
            claim_validations,
            {ANALYSIS_CLAIM_KIND_EXCLUSION},
        ),
        unresolved_gap_validation_refs=_validation_refs_by_kind(
            claim_validations,
            {ANALYSIS_CLAIM_KIND_GAP},
        ),
        conflict_or_overclaim_risk_validation_refs=_validation_refs_by_kind(
            claim_validations,
            {ANALYSIS_CLAIM_KIND_CONFLICT_RISK, ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK},
        ),
        bounded_evidence_excerpt_available=(
            input_packet.get("bounded_evidence_excerpt_available") is True
        ),
        bounded_evidence_excerpt_count=_bounded_int(
            input_packet.get("bounded_evidence_excerpt_count")
        ),
        model_assisted_analysis_evidence_depth=input_packet.get(
            "model_assisted_analysis_evidence_depth"
        ),
        model_input_evidence_limitation=input_packet.get(
            "model_input_evidence_limitation"
        ),
        status=status,
        summary=summary,
        reason_codes=reason_codes,
        input_packet_ref=_input_packet_ref(input_packet),
        source_support_map_validation_ref=_support_map_validation_ref(
            support_map_validation
        ),
        model_calls_attempted=model_calls_attempted,
        model_calls_completed=model_calls_completed,
        live_model_call_run=live_model_call_run,
        proposal_generation_mode=proposal.get("finding_generation_mode"),
        model_assisted_analyst_product_grade_analysis=(
            proposal.get("model_assisted_analyst_product_grade_analysis") is True
        ),
    )


def _validation_from_model_output(
    *,
    input_packet: Mapping[str, Any],
    model_output: Mapping[str, Any],
    model_calls_attempted: int,
    model_calls_completed: int,
    live_model_call_run: bool,
) -> dict[str, Any]:
    output = _safe_mapping(model_output)
    _reject_forbidden_or_authority(
        output,
        context="D-prime AnalystFinding model output",
    )
    base = _deterministic_validation(
        input_packet=input_packet,
        model_calls_attempted=model_calls_attempted,
        model_calls_completed=model_calls_completed,
        live_model_call_run=live_model_call_run,
    )
    model_status = _clean_text(output.get("dprime_validation_status"), limit=120)
    if model_status and model_status not in _VALIDATION_STATUSES:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output validation status invalid"
        )
    claim_validations = _model_claim_validations(output, input_packet=input_packet)
    source_map_validation = _safe_mapping(
        output.get("source_support_map_validation")
    ) or _safe_mapping(base.get("source_support_map_validation"))
    proposed_validation = _safe_mapping(
        output.get("proposed_answer_claim_validation")
    ) or _safe_mapping(base.get("proposed_answer_claim_validation"))
    status = model_status or base["dprime_validation_status"]
    if status == DPRIME_SUPPORT_VALIDATION_SUPPORTED:
        _require_supported_model_output(
            claim_validations=claim_validations,
            proposed_answer_validation=proposed_validation,
            source_support_map_validation=source_map_validation,
        )
    reason_codes = tuple(
        _text_tuple(output.get("dprime_support_validation_reason_codes"), limit=120)
        or _text_tuple(base.get("dprime_support_validation_reason_codes"), limit=120)
    )
    summary = (
        _clean_text(output.get("validation_summary"), limit=700)
        or _safe_mapping(base.get("dprime_validation_summary_ref")).get(
            "validation_summary"
        )
        or _summary_text(status=status, reason_codes=reason_codes)
    )
    updated = {
        **base,
        "dprime_validation_status": status,
        "dprime_support_validation_reason_codes": list(reason_codes),
        "proposed_answer_claim_validation": proposed_validation,
        "proposed_answer_claim_validation_ref": _claim_validation_ref(
            proposed_validation
        ),
        "analysis_claim_validations": claim_validations,
        "analysis_claim_validation_refs": [
            _claim_validation_ref(item) for item in claim_validations
        ],
        "source_support_map_validation": source_map_validation,
        "source_support_map_validation_ref": _support_map_validation_ref(
            source_map_validation
        ),
        "dprime_validation_summary_ref": _summary_ref(
            status=status,
            summary=summary,
            reason_codes=reason_codes,
        ),
        "model_calls_attempted": _bounded_int(model_calls_attempted),
        "model_calls_completed": _bounded_int(model_calls_completed),
        "live_model_call_run": bool(live_model_call_run),
    }
    updated.update(_product_policy(status))
    updated["validation_digest"] = _digest_json(_without_digest(updated))
    updated["validation_id"] = (
        "dprime-analyst-finding-support-validation:"
        f"{updated['validation_digest'][:20]}"
    )
    return updated


def _model_claim_validations(
    output: Mapping[str, Any],
    *,
    input_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    claim_ids = _known_claim_ids(input_packet)
    deterministic_by_id = {
        _clean_text(item.get("analysis_claim_id"), limit=260): item
        for item in _safe_sequence(
            _deterministic_validation(
                input_packet=input_packet,
                model_calls_attempted=0,
                model_calls_completed=0,
                live_model_call_run=False,
            ).get("analysis_claim_validations")
        )
    }
    raw_validations = _safe_sequence(output.get("analysis_claim_validations")) or (
        _safe_sequence(output.get("analysis_claim_validation_refs"))
    )
    if not raw_validations:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output omitted analysis claim validations"
        )
    validations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_validations:
        item = _safe_mapping(raw)
        claim_id = _clean_text(item.get("analysis_claim_id"), limit=260)
        if not claim_id or claim_id not in claim_ids:
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime model output validated a claim outside the proposal"
            )
        status = _clean_text(
            item.get("dprime_support_validation_status"),
            limit=120,
        )
        if status not in _VALIDATION_STATUSES:
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime model output claim validation status invalid"
            )
        deterministic = _safe_mapping(deterministic_by_id.get(claim_id))
        merged = {
            **deterministic,
            **item,
            "analysis_claim_id": claim_id,
            "evidence_admitted": False,
            "citation_eligibility_created": False,
            "product_correctness_claimed": False,
        }
        _validate_claim_validation(merged, input_packet=input_packet)
        validations.append(_claim_validation_digest(merged))
        seen.add(claim_id)
    if seen != claim_ids:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output did not validate every proposal claim"
        )
    return validations


def _require_supported_model_output(
    *,
    claim_validations: Sequence[Mapping[str, Any]],
    proposed_answer_validation: Mapping[str, Any],
    source_support_map_validation: Mapping[str, Any],
) -> None:
    if not proposed_answer_validation:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output claimed support without answer validation"
        )
    if proposed_answer_validation.get("dprime_support_validation_status") != (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output claimed support but answer claim is unsupported"
        )
    for validation in claim_validations:
        status = validation.get("dprime_support_validation_status")
        kind = validation.get("analysis_claim_kind")
        if kind in _ANSWER_CLAIM_KINDS and status != DPRIME_SUPPORT_VALIDATION_SUPPORTED:
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime model output claimed support with unsupported answer claim"
            )
        if kind in _ANSWER_CLAIM_KINDS and not _safe_refs(
            validation.get("supporting_bounded_evidence_excerpt_refs")
        ):
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime model output claimed support without excerpt refs"
            )
    if source_support_map_validation.get("source_support_map_validation_status") != (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    ):
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime model output claimed support without valid support map"
        )


def _claim_validation(
    claim: Mapping[str, Any],
    *,
    input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(claim)
    kind = _clean_text(safe.get("analysis_claim_kind"), limit=120)
    claim_id = _clean_text(safe.get("analysis_claim_id"), limit=260)
    selected_ids = _candidate_ids(input_packet.get("selected_answer_bearing_candidate_refs"))
    adjacent_ids = _candidate_ids(
        [
            *_safe_refs(input_packet.get("adjacent_context_candidate_refs")),
            *_safe_refs(input_packet.get("excluded_scope_candidate_refs")),
        ]
    )
    unreadable_ids = _candidate_ids(
        input_packet.get("unreadable_high_value_candidate_refs")
    )
    allowed_ids = selected_ids | adjacent_ids | unreadable_ids | _candidate_ids(
        input_packet.get("overclaim_risk_candidate_refs")
    )
    support_refs = _safe_refs(safe.get("supporting_candidate_refs"))
    support_ids = _candidate_ids(support_refs)
    adjacent_refs = _safe_refs(safe.get("adjacent_or_excluded_candidate_refs"))
    adjacent_claim_ids = _candidate_ids(adjacent_refs)
    excerpt_refs = _excerpt_refs_for_candidate_ids(input_packet, support_ids)
    reason_codes: list[str] = []
    within_requested_type = True
    uses_allowed_roles = (support_ids | adjacent_claim_ids) <= allowed_ids
    grounded = bool(excerpt_refs)
    if not claim_id:
        reason_codes.append("analysis_claim_id_missing")
    if not uses_allowed_roles:
        reason_codes.append("candidate_ref_not_in_analyst_input")
    if kind in _ANSWER_CLAIM_KINDS:
        binding = _safe_mapping(input_packet.get("component_answer_type_binding_ref"))
        proposed_answer = _safe_mapping(input_packet.get("proposed_answer_claim"))
        if proposed_answer and (
            proposed_answer.get("requested_answer_type")
            != binding.get("requested_answer_type")
            or proposed_answer.get("expected_value_shape")
            != binding.get("expected_value_shape")
        ):
            reason_codes.append("requested_answer_type_or_value_shape_changed")
            within_requested_type = False
        if not support_ids:
            reason_codes.append("answer_claim_lacks_supporting_candidate_ref")
        if support_ids - selected_ids:
            if support_ids & (adjacent_ids | unreadable_ids):
                reason_codes.append("adjacent_or_unreadable_candidate_used_as_answer_support")
            else:
                reason_codes.append("non_answer_candidate_used_as_answer_support")
        if not grounded:
            reason_codes.append("answer_claim_lacks_bounded_evidence_excerpt")
        status = (
            DPRIME_SUPPORT_VALIDATION_SUPPORTED
            if not reason_codes
            else DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM
            if any("adjacent" in code for code in reason_codes)
            else DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
            if "answer_claim_lacks_bounded_evidence_excerpt" in reason_codes
            else DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
        )
    elif kind == ANALYSIS_CLAIM_KIND_GAP:
        reason_codes.append("gap_preserved_for_future_recovery")
        status = (
            DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP
            if adjacent_claim_ids & unreadable_ids
            else DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
        )
        grounded = False
    elif kind in _CAVEAT_OR_RISK_KINDS:
        if not adjacent_claim_ids:
            reason_codes.append("caveat_or_risk_lacks_adjacent_or_excluded_ref")
        if adjacent_claim_ids - allowed_ids:
            reason_codes.append("caveat_or_risk_uses_unknown_candidate_ref")
        status = (
            DPRIME_SUPPORT_VALIDATION_PARTIAL
            if not any("unknown" in code for code in reason_codes)
            else DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
        )
        grounded = False
    else:
        reason_codes.append("analysis_claim_kind_invalid")
        status = DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL
    validation = {
        "analysis_claim_id": claim_id,
        "analysis_claim_digest": safe.get("analysis_claim_digest"),
        "analysis_claim_kind": kind,
        "analyst_support_status_proposed": safe.get("support_status_proposed"),
        "dprime_support_validation_status": status,
        "dprime_support_validation_reason_codes": reason_codes,
        "supporting_candidate_refs": support_refs,
        "supporting_bounded_evidence_excerpt_refs": excerpt_refs,
        "adjacent_or_excluded_candidate_refs": adjacent_refs,
        "unsupported_gap_refs": _gap_refs_for_claim(
            claim=safe,
            input_packet=input_packet,
        ),
        "validation_summary": _claim_summary(status, reason_codes),
        "claim_within_requested_answer_type": within_requested_type,
        "claim_uses_only_allowed_candidate_roles": uses_allowed_roles,
        "claim_grounded_in_bounded_evidence": grounded,
        "requires_scrutineer_validation": (
            safe.get("requires_scrutineer_validation") is True
        ),
        "evidence_admitted": False,
        "citation_eligibility_created": False,
        "product_correctness_claimed": False,
    }
    return _claim_validation_digest(validation)


def _proposed_answer_claim_validation(
    *,
    input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    claim = _safe_mapping(input_packet.get("proposed_answer_claim"))
    if not claim:
        return {}
    binding = _safe_mapping(input_packet.get("component_answer_type_binding_ref"))
    selected_ids = _candidate_ids(input_packet.get("selected_answer_bearing_candidate_refs"))
    adjacent_ids = _candidate_ids(
        [
            *_safe_refs(input_packet.get("adjacent_context_candidate_refs")),
            *_safe_refs(input_packet.get("excluded_scope_candidate_refs")),
            *_safe_refs(input_packet.get("unreadable_high_value_candidate_refs")),
        ]
    )
    support_refs = _safe_refs(claim.get("selected_answer_bearing_candidate_refs"))
    support_ids = _candidate_ids(support_refs)
    excerpt_refs = _excerpt_refs_for_candidate_ids(input_packet, support_ids)
    reason_codes: list[str] = []
    if claim.get("requested_answer_type") != binding.get("requested_answer_type"):
        reason_codes.append("requested_answer_type_changed")
    if claim.get("expected_value_shape") != binding.get("expected_value_shape"):
        reason_codes.append("expected_value_shape_changed")
    if not support_ids:
        reason_codes.append("proposed_answer_claim_lacks_candidate_refs")
    if support_ids - selected_ids:
        if support_ids & adjacent_ids:
            reason_codes.append("adjacent_or_excluded_candidate_used_as_answer_support")
        else:
            reason_codes.append("unknown_candidate_used_as_answer_support")
    if not excerpt_refs:
        reason_codes.append("proposed_answer_claim_lacks_bounded_evidence_excerpt")
    answer_value = _clean_text(claim.get("answer_value_candidate"), limit=200)
    if answer_value and not _value_appears_in_excerpts(answer_value, input_packet):
        reason_codes.append("answer_value_candidate_not_seen_in_bounded_evidence")
    status = (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
        if not reason_codes
        else DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM
        if any("adjacent" in code for code in reason_codes)
        else DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
        if any("bounded_evidence" in code for code in reason_codes)
        else DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
    )
    validation = {
        "analysis_claim_id": claim.get("proposed_answer_claim_id"),
        "analysis_claim_digest": claim.get("proposed_answer_claim_digest"),
        "analysis_claim_kind": ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
        "analyst_support_status_proposed": SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED,
        "dprime_support_validation_status": status,
        "dprime_support_validation_reason_codes": reason_codes,
        "supporting_candidate_refs": support_refs,
        "supporting_bounded_evidence_excerpt_refs": excerpt_refs,
        "adjacent_or_excluded_candidate_refs": [],
        "unsupported_gap_refs": [],
        "validation_summary": _claim_summary(status, reason_codes),
        "claim_within_requested_answer_type": (
            "requested_answer_type_changed" not in reason_codes
            and "expected_value_shape_changed" not in reason_codes
        ),
        "claim_uses_only_allowed_candidate_roles": not (
            support_ids - selected_ids
        ),
        "claim_grounded_in_bounded_evidence": bool(excerpt_refs),
        "requires_scrutineer_validation": False,
        "evidence_admitted": False,
        "citation_eligibility_created": False,
        "product_correctness_claimed": False,
    }
    return _claim_validation_digest(validation)


def _source_support_map_validation(
    *,
    input_packet: Mapping[str, Any],
    claim_validations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    support_map = _safe_mapping(input_packet.get("source_support_map"))
    known_claim_ids = _known_claim_ids(input_packet)
    selected_ids = _candidate_ids(input_packet.get("selected_answer_bearing_candidate_refs"))
    adjacent_ids = _candidate_ids(
        [
            *_safe_refs(input_packet.get("adjacent_context_candidate_refs")),
            *_safe_refs(input_packet.get("excluded_scope_candidate_refs")),
            *_safe_refs(input_packet.get("overclaim_risk_candidate_refs")),
        ]
    )
    unreadable_ids = _candidate_ids(
        input_packet.get("unreadable_high_value_candidate_refs")
    )
    excerpt_candidate_ids = _candidate_ids_from_excerpts(input_packet)
    invalid_edges: list[dict[str, Any]] = []
    unsupported_edges: list[dict[str, Any]] = []
    adjacent_answer_edges: list[dict[str, Any]] = []
    unreadable_support_edges: list[dict[str, Any]] = []
    validated_edges: list[dict[str, Any]] = []
    for raw in _safe_sequence(support_map.get("analysis_claim_support_edges")):
        edge = _safe_mapping(raw)
        claim_id = _clean_text(edge.get("analysis_claim_id"), limit=260)
        candidate_ref = _safe_mapping(edge.get("candidate_ref"))
        candidate_id = _clean_text(candidate_ref.get("candidate_id"), limit=320)
        edge_ref = _edge_ref(edge)
        if claim_id and claim_id not in known_claim_ids:
            invalid_edges.append(edge_ref)
            continue
        if edge.get("edge_kind") == "candidate_supports_analysis_claim":
            if candidate_id in adjacent_ids:
                adjacent_answer_edges.append(edge_ref)
            elif candidate_id in unreadable_ids:
                unreadable_support_edges.append(edge_ref)
            elif candidate_id not in selected_ids:
                unsupported_edges.append(edge_ref)
            elif candidate_id not in excerpt_candidate_ids:
                unsupported_edges.append(edge_ref)
            else:
                validated_edges.append(edge_ref)
        elif edge.get("edge_kind") in {
            "candidate_is_adjacent_context",
            "candidate_is_excluded_scope",
        }:
            if candidate_id in adjacent_ids:
                validated_edges.append(edge_ref)
            else:
                invalid_edges.append(edge_ref)
        elif edge.get("edge_kind") == "candidate_is_unreadable_gap":
            if candidate_id in unreadable_ids:
                validated_edges.append(edge_ref)
            else:
                invalid_edges.append(edge_ref)
        elif edge.get("edge_kind") == "unsupported_analysis_gap":
            validated_edges.append(edge_ref)
        else:
            invalid_edges.append(edge_ref)
    validation_status = (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
        if validated_edges
        and not (
            invalid_edges
            or unsupported_edges
            or adjacent_answer_edges
            or unreadable_support_edges
        )
        else DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM
        if adjacent_answer_edges
        else DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP
        if unreadable_support_edges
        else DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
        if invalid_edges or unsupported_edges
        else DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
    )
    result = {
        "source_support_map_validation_status": validation_status,
        "invalid_edge_refs": invalid_edges,
        "unsupported_edge_refs": unsupported_edges,
        "adjacent_as_answer_edge_refs": adjacent_answer_edges,
        "unreadable_as_support_edge_refs": unreadable_support_edges,
        "validated_support_edge_refs": validated_edges,
        "analysis_claim_count": len(known_claim_ids),
        "claim_validation_count": len(claim_validations),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "product_correctness_claimed": False,
    }
    result["source_support_map_validation_digest"] = _digest_json(result)
    result["source_support_map_validation_id"] = (
        "dprime-source-support-map-validation:"
        f"{result['source_support_map_validation_digest'][:20]}"
    )
    return result


def _overall_status(
    *,
    proposed_answer_validation: Mapping[str, Any],
    claim_validations: Sequence[Mapping[str, Any]],
    support_map_validation: Mapping[str, Any],
    input_packet: Mapping[str, Any],
) -> str:
    if input_packet.get("bounded_evidence_excerpt_available") is not True:
        return DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
    statuses = [
        _clean_text(
            proposed_answer_validation.get("dprime_support_validation_status"),
            limit=120,
        )
    ]
    statuses.extend(
        _clean_text(item.get("dprime_support_validation_status"), limit=120)
        for item in claim_validations
    )
    statuses.append(
        _clean_text(
            support_map_validation.get("source_support_map_validation_status"),
            limit=120,
        )
    )
    status_set = {status for status in statuses if status}
    if DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM in status_set:
        return DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM
    if DPRIME_SUPPORT_VALIDATION_UNSUPPORTED in status_set:
        return DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
    if DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL in status_set:
        return DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL
    if DPRIME_SUPPORT_VALIDATION_INSUFFICIENT in status_set:
        return DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
    answer_claim_statuses = [
        item.get("dprime_support_validation_status")
        for item in claim_validations
        if item.get("analysis_claim_kind") in _ANSWER_CLAIM_KINDS
    ]
    if proposed_answer_validation and all(
        status == DPRIME_SUPPORT_VALIDATION_SUPPORTED
        for status in [proposed_answer_validation.get("dprime_support_validation_status")]
        + answer_claim_statuses
    ):
        return DPRIME_SUPPORT_VALIDATION_SUPPORTED
    if DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP in status_set:
        return DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP
    return DPRIME_SUPPORT_VALIDATION_PARTIAL


def _overall_reason_codes(
    *,
    proposed_answer_validation: Mapping[str, Any],
    claim_validations: Sequence[Mapping[str, Any]],
    support_map_validation: Mapping[str, Any],
) -> tuple[str, ...]:
    codes: list[str] = []
    for source in (proposed_answer_validation, *claim_validations):
        codes.extend(
            _text_tuple(
                _safe_mapping(source).get("dprime_support_validation_reason_codes"),
                limit=120,
            )
        )
    for key in (
        "invalid_edge_refs",
        "unsupported_edge_refs",
        "adjacent_as_answer_edge_refs",
        "unreadable_as_support_edge_refs",
    ):
        if _safe_sequence(support_map_validation.get(key)):
            codes.append(key)
    return tuple(_unique(codes))


def _validation_artifact(
    *,
    analyst_finding_proposal_ref: Mapping[str, Any],
    proposed_answer_claim_ref: Mapping[str, Any],
    proposed_answer_claim_validation: Mapping[str, Any],
    analysis_claim_validations: Sequence[Mapping[str, Any]],
    source_support_map_validation: Mapping[str, Any],
    caveat_validation_refs: Sequence[Mapping[str, Any]],
    adjacent_claim_exclusion_validation_refs: Sequence[Mapping[str, Any]],
    unresolved_gap_validation_refs: Sequence[Mapping[str, Any]],
    conflict_or_overclaim_risk_validation_refs: Sequence[Mapping[str, Any]],
    bounded_evidence_excerpt_available: bool,
    bounded_evidence_excerpt_count: int,
    model_assisted_analysis_evidence_depth: Any,
    model_input_evidence_limitation: Any,
    status: str,
    summary: str,
    reason_codes: Sequence[str],
    input_packet_ref: Mapping[str, Any],
    source_support_map_validation_ref: Mapping[str, Any],
    model_calls_attempted: int,
    model_calls_completed: int,
    live_model_call_run: bool,
    proposal_generation_mode: Any,
    model_assisted_analyst_product_grade_analysis: bool,
) -> dict[str, Any]:
    artifact = {
        "schema_version": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_SCHEMA_VERSION,
        "phase": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_PHASE,
        "validation_kind": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_KIND,
        "analyst_finding_proposal_ref": _safe_mapping(
            analyst_finding_proposal_ref
        ),
        "proposed_answer_claim_ref": _safe_mapping(proposed_answer_claim_ref),
        "proposed_answer_claim_validation": _safe_mapping(
            proposed_answer_claim_validation
        ),
        "proposed_answer_claim_validation_ref": _claim_validation_ref(
            proposed_answer_claim_validation
        ),
        "analysis_claim_validations": [
            _safe_mapping(item) for item in analysis_claim_validations
        ],
        "analysis_claim_validation_refs": [
            _claim_validation_ref(item) for item in analysis_claim_validations
        ],
        "source_support_map_validation": _safe_mapping(source_support_map_validation),
        "source_support_map_validation_ref": _safe_mapping(
            source_support_map_validation_ref
        ),
        "caveat_validation_refs": [_safe_mapping(item) for item in caveat_validation_refs],
        "adjacent_claim_exclusion_validation_refs": [
            _safe_mapping(item) for item in adjacent_claim_exclusion_validation_refs
        ],
        "unresolved_gap_validation_refs": [
            _safe_mapping(item) for item in unresolved_gap_validation_refs
        ],
        "conflict_or_overclaim_risk_validation_refs": [
            _safe_mapping(item) for item in conflict_or_overclaim_risk_validation_refs
        ],
        "bounded_evidence_excerpt_available": bool(
            bounded_evidence_excerpt_available
        ),
        "bounded_evidence_excerpt_count": _bounded_int(
            bounded_evidence_excerpt_count
        ),
        "model_assisted_analysis_evidence_depth": _clean_text(
            model_assisted_analysis_evidence_depth,
            limit=120,
        ),
        "model_input_evidence_limitation": _clean_text(
            model_input_evidence_limitation,
            limit=180,
        ),
        "dprime_validation_status": status,
        "dprime_support_validation_reason_codes": list(_unique(reason_codes)),
        "dprime_validation_summary_ref": _summary_ref(
            status=status,
            summary=summary,
            reason_codes=reason_codes,
        ),
        "dprime_model_role": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE,
        "role_surface": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROLE_SURFACE,
        "runtime_consumer": (
            DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_RUNTIME_CONSUMER
        ),
        "route_authority": DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROUTE_AUTHORITY,
        "model_calls_attempted": _bounded_int(model_calls_attempted),
        "model_calls_completed": _bounded_int(model_calls_completed),
        "live_model_call_run": bool(live_model_call_run),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "input_packet_ref": _safe_mapping(input_packet_ref),
        "proposal_generation_mode": _clean_text(proposal_generation_mode, limit=120),
        "model_assisted_analyst_product_grade_analysis": bool(
            model_assisted_analyst_product_grade_analysis
        ),
        **_product_policy(status),
        **_non_authority_posture(),
    }
    artifact["source_support_map_validation_status"] = (
        source_support_map_validation.get("source_support_map_validation_status")
    )
    artifact["invalid_edge_refs"] = _safe_refs(
        source_support_map_validation.get("invalid_edge_refs")
    )
    artifact["unsupported_edge_refs"] = _safe_refs(
        source_support_map_validation.get("unsupported_edge_refs")
    )
    artifact["adjacent_as_answer_edge_refs"] = _safe_refs(
        source_support_map_validation.get("adjacent_as_answer_edge_refs")
    )
    artifact["unreadable_as_support_edge_refs"] = _safe_refs(
        source_support_map_validation.get("unreadable_as_support_edge_refs")
    )
    artifact["validated_support_edge_refs"] = _safe_refs(
        source_support_map_validation.get("validated_support_edge_refs")
    )
    artifact = _without_empty(artifact)
    artifact["validation_digest"] = _digest_json(_without_digest(artifact))
    artifact["validation_id"] = (
        "dprime-analyst-finding-support-validation:"
        f"{artifact['validation_digest'][:20]}"
    )
    return artifact


def _blocked_validation(
    *,
    status: str,
    reason_codes: Sequence[str],
    summary: str,
    analyst_finding_proposal_ref: Mapping[str, Any] | None = None,
    proposed_answer_claim_ref: Mapping[str, Any] | None = None,
    input_packet_ref: Mapping[str, Any] | None = None,
    model_calls_attempted: int = 0,
    model_calls_completed: int = 0,
    live_model_call_run: bool = False,
) -> dict[str, Any]:
    support_map = {
        "source_support_map_validation_status": status,
        "invalid_edge_refs": [],
        "unsupported_edge_refs": [],
        "adjacent_as_answer_edge_refs": [],
        "unreadable_as_support_edge_refs": [],
        "validated_support_edge_refs": [],
    }
    return validate_dprime_analyst_finding_support_validation(
        _validation_artifact(
            analyst_finding_proposal_ref=_safe_mapping(analyst_finding_proposal_ref),
            proposed_answer_claim_ref=_safe_mapping(proposed_answer_claim_ref),
            proposed_answer_claim_validation={},
            analysis_claim_validations=[],
            source_support_map_validation=support_map,
            caveat_validation_refs=[],
            adjacent_claim_exclusion_validation_refs=[],
            unresolved_gap_validation_refs=[],
            conflict_or_overclaim_risk_validation_refs=[],
            bounded_evidence_excerpt_available=False,
            bounded_evidence_excerpt_count=0,
            model_assisted_analysis_evidence_depth=MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY,
            model_input_evidence_limitation=(
                MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT
            ),
            status=status,
            summary=summary,
            reason_codes=reason_codes,
            input_packet_ref=_safe_mapping(input_packet_ref),
            source_support_map_validation_ref=_support_map_validation_ref(
                support_map
            ),
            model_calls_attempted=model_calls_attempted,
            model_calls_completed=model_calls_completed,
            live_model_call_run=live_model_call_run,
            proposal_generation_mode=None,
            model_assisted_analyst_product_grade_analysis=False,
        )
    )


def _product_policy(status: str) -> dict[str, Any]:
    supported = status in _SUPPORTED_STATUSES
    not_run = status in {
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_LICENSE,
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_ADAPTER,
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_BOUNDED_EVIDENCE,
    }
    return {
        "dprime_analyst_finding_validation_required_for_product_path": True,
        "dprime_analyst_finding_validation_required_for_product_pass": True,
        "dprime_analyst_finding_validation_satisfied": supported,
        "dprime_analyst_finding_product_grade_validation": supported,
        "product_proof_status": (
            PRODUCT_PROOF_NOT_CLAIMED_PENDING_RUNKERNEL_ADMISSION
            if supported
            else PRODUCT_PROOF_BLOCKED_VALIDATION_REQUIRED_BUT_NOT_RUN
            if not_run
            else PRODUCT_PROOF_BLOCKED_VALIDATION_UNSUPPORTED
        ),
        "product_correctness_claimed": False,
        "runkernel_support_admission_recommended": supported,
        "requires_runkernel_admission": supported,
        "runkernel_admission_created": False,
        "evidence_admitted": False,
        "source_obligation_satisfied": False,
        "citation_eligibility_created": False,
        "component_coverage_created": False,
        "sufficiency_readiness_created": False,
        "final_answer_packet_created": False,
        "author_output_created": False,
        "source_display_opened": False,
    }


def _validate_validation_refs(
    validation: Mapping[str, Any],
    *,
    input_packet: Mapping[str, Any] | None,
) -> None:
    safe_input = _safe_mapping(input_packet)
    known_claim_ids = _known_claim_ids(safe_input) if safe_input else set()
    for item in _safe_sequence(validation.get("analysis_claim_validations")):
        _validate_claim_validation(item, input_packet=safe_input)
        claim_id = _clean_text(_safe_mapping(item).get("analysis_claim_id"), limit=260)
        if known_claim_ids and claim_id not in known_claim_ids:
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime validation references a claim outside the proposal"
            )
    proposed = _safe_mapping(validation.get("proposed_answer_claim_validation"))
    if proposed:
        _validate_claim_validation(proposed, input_packet=safe_input)
        if safe_input:
            binding = _safe_mapping(
                safe_input.get("component_answer_type_binding_ref")
            )
            if proposed.get("claim_within_requested_answer_type") is not (
                proposed.get("dprime_support_validation_status")
                != DPRIME_SUPPORT_VALIDATION_UNSUPPORTED
            ) and (
                _safe_mapping(safe_input.get("proposed_answer_claim")).get(
                    "requested_answer_type"
                )
                != binding.get("requested_answer_type")
                or _safe_mapping(safe_input.get("proposed_answer_claim")).get(
                    "expected_value_shape"
                )
                != binding.get("expected_value_shape")
            ):
                raise DPrimeAnalystFindingSupportValidationError(
                    "D-prime validation changed requested answer type/value shape"
                )
    status = validation.get("dprime_validation_status")
    if status == DPRIME_SUPPORT_VALIDATION_SUPPORTED:
        if not _safe_mapping(validation.get("proposed_answer_claim_validation_ref")):
            raise DPrimeAnalystFindingSupportValidationError(
                "supported validation requires proposed answer validation ref"
            )
        if not _safe_sequence(validation.get("analysis_claim_validation_refs")):
            raise DPrimeAnalystFindingSupportValidationError(
                "supported validation requires analysis claim validation refs"
            )
        if not _safe_mapping(validation.get("source_support_map_validation_ref")):
            raise DPrimeAnalystFindingSupportValidationError(
                "supported validation requires source support map validation ref"
            )
    if validation.get("runkernel_admission_created") is not False:
        raise DPrimeAnalystFindingSupportValidationError(
            "D-prime AnalystFinding validation cannot create RunKernel admission"
        )


def _validate_claim_validation(
    validation: Mapping[str, Any],
    *,
    input_packet: Mapping[str, Any],
) -> None:
    item = _safe_mapping(validation)
    status = _clean_text(item.get("dprime_support_validation_status"), limit=120)
    if status not in _VALIDATION_STATUSES:
        raise DPrimeAnalystFindingSupportValidationError(
            "claim validation status invalid"
        )
    if not _clean_text(item.get("analysis_claim_id"), limit=260):
        raise DPrimeAnalystFindingSupportValidationError(
            "claim validation requires analysis_claim_id"
        )
    if item.get("evidence_admitted") is not False:
        raise DPrimeAnalystFindingSupportValidationError(
            "claim validation cannot admit evidence"
        )
    if item.get("citation_eligibility_created") is not False:
        raise DPrimeAnalystFindingSupportValidationError(
            "claim validation cannot create citation eligibility"
        )
    if item.get("product_correctness_claimed") is not False:
        raise DPrimeAnalystFindingSupportValidationError(
            "claim validation cannot claim product correctness"
        )
    if input_packet:
        binding = _safe_mapping(input_packet.get("component_answer_type_binding_ref"))
        proposal = _safe_mapping(input_packet.get("proposed_answer_claim"))
        if (
            item.get("analysis_claim_kind") == ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER
            and proposal
            and (
                proposal.get("requested_answer_type")
                != binding.get("requested_answer_type")
                or proposal.get("expected_value_shape")
                != binding.get("expected_value_shape")
            )
            and status == DPRIME_SUPPORT_VALIDATION_SUPPORTED
        ):
            raise DPrimeAnalystFindingSupportValidationError(
                "D-prime validation supported changed answer type/value shape"
            )


def _validate_boolean_flags(safe: Mapping[str, Any]) -> None:
    for key, expected in _NON_AUTHORITY_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            raise DPrimeAnalystFindingSupportValidationError(
                f"D-prime AnalystFinding validation authority flag invalid: {key}"
            )
    for key, expected in _RAW_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            raise DPrimeAnalystFindingSupportValidationError(
                f"D-prime AnalystFinding validation raw flag invalid: {key}"
            )
    if safe.get("live_model_call_run") is True and safe.get("model_calls_completed") != 1:
        raise DPrimeAnalystFindingSupportValidationError(
            "live D-prime AnalystFinding validation must account for one call"
        )


def _input_packet_ref(input_packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(input_packet)
    return _without_empty(
        {
            "schema_version": safe.get("schema_version"),
            "phase": safe.get("phase"),
            "input_packet_id": safe.get("input_packet_id"),
            "input_packet_digest": safe.get("input_packet_digest"),
            "analyst_finding_proposal_ref": _safe_mapping(
                safe.get("analyst_finding_proposal_ref")
            ),
            "bounded_evidence_excerpt_available": (
                safe.get("bounded_evidence_excerpt_available") is True
            ),
            "bounded_evidence_excerpt_count": _bounded_int(
                safe.get("bounded_evidence_excerpt_count")
            ),
            "model_assisted_analysis_evidence_depth": safe.get(
                "model_assisted_analysis_evidence_depth"
            ),
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
        }
    )


def _proposal_for_validation(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": proposal.get("schema_version"),
            "phase": proposal.get("phase"),
            "finding_id": proposal.get("finding_id"),
            "finding_digest": proposal.get("finding_digest"),
            "finding_kind": proposal.get("finding_kind"),
            "finding_status": proposal.get("finding_status"),
            "finding_generation_mode": proposal.get("finding_generation_mode"),
            "model_assisted_analysis_run": (
                proposal.get("model_assisted_analysis_run") is True
            ),
            "model_role": proposal.get("model_role"),
            "role_surface": proposal.get("role_surface"),
            "bounded_evidence_excerpt_available": (
                proposal.get("bounded_evidence_excerpt_available") is True
            ),
            "bounded_evidence_excerpt_count": _bounded_int(
                proposal.get("bounded_evidence_excerpt_count")
            ),
            "model_assisted_analysis_evidence_depth": proposal.get(
                "model_assisted_analysis_evidence_depth"
            ),
            "model_input_evidence_limitation": proposal.get(
                "model_input_evidence_limitation"
            ),
            "proposed_answer_claim_ref": _safe_mapping(
                proposal.get("proposed_answer_claim_ref")
            ),
            "analysis_claim_refs": _safe_refs(proposal.get("analysis_claim_refs")),
            "source_support_map_ref": _safe_mapping(
                proposal.get("source_support_map_ref")
            ),
            **_non_authority_posture(),
        }
    )


def _bounded_evidence_excerpts(
    fetch_read_content_packet: Mapping[str, Any] | None,
    *,
    candidate_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    packet = _safe_mapping(fetch_read_content_packet)
    candidate_ids = _candidate_ids(candidate_refs)
    excerpts: list[dict[str, Any]] = []
    for raw in _safe_sequence(packet.get("reference_records")):
        ref = _safe_mapping(raw)
        if ref.get("candidate_id") not in candidate_ids:
            continue
        text = _safe_bounded_excerpt_text(ref)
        if not text:
            continue
        digest = _digest_json({"bounded_text": text})
        excerpt = _without_empty(
            {
                "candidate_id": ref.get("candidate_id"),
                "candidate_digest": ref.get("candidate_digest"),
                "reference_id": ref.get("reference_id"),
                "reference_digest": ref.get("reference_digest"),
                "excerpt_digest": digest,
                "bounded_content_digest": digest,
                "bounded_excerpt_text": text,
                "bounded_character_count": len(text),
                "fetch_read_status": ref.get("fetch_read_status"),
                "bounded_text_sanitized": True,
                "bounded_text_bounded": True,
                "not_semantic_support": True,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "raw_provider_payload_retained": False,
                "raw_source_content_retained": False,
            }
        )
        _reject_forbidden_or_authority(
            _drop_bounded_excerpt_text(excerpt),
            context="D-prime AnalystFinding bounded evidence excerpt",
        )
        excerpts.append(excerpt)
    return excerpts


def _evidence_profile(
    *,
    bounded_evidence_excerpts: Sequence[Mapping[str, Any]],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    if bounded_evidence_excerpts:
        return {
            "bounded_evidence_excerpt_available": True,
            "bounded_evidence_excerpt_count": len(bounded_evidence_excerpts),
            "model_assisted_analysis_evidence_depth": (
                MODEL_INPUT_EVIDENCE_DEPTH_BOUNDED_EXCERPT
            ),
            "model_input_evidence_limitation": None,
        }
    return {
        "bounded_evidence_excerpt_available": False,
        "bounded_evidence_excerpt_count": 0,
        "model_assisted_analysis_evidence_depth": (
            proposal.get("model_assisted_analysis_evidence_depth")
            or MODEL_INPUT_EVIDENCE_DEPTH_LIMITED_NO_EXCERPT
            if _safe_sequence(proposal.get("analysis_claim_refs"))
            else MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY
        ),
        "model_input_evidence_limitation": (
            MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT
        ),
    }


def _safe_bounded_excerpt_text(ref: Mapping[str, Any]) -> str | None:
    value = ref.get("bounded_excerpt")
    if value in (None, ""):
        value = ref.get("bounded_text")
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 2_000:
        text = text[:2_000]
    return text


def _excerpt_refs_for_candidate_ids(
    input_packet: Mapping[str, Any],
    candidate_ids: set[str],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for excerpt in _safe_sequence(input_packet.get("bounded_evidence_excerpts")):
        safe = _safe_mapping(excerpt)
        if safe.get("candidate_id") not in candidate_ids:
            continue
        refs.append(
            _without_empty(
                {
                    "candidate_id": safe.get("candidate_id"),
                    "candidate_digest": safe.get("candidate_digest"),
                    "reference_id": safe.get("reference_id"),
                    "reference_digest": safe.get("reference_digest"),
                    "excerpt_digest": safe.get("excerpt_digest"),
                    "bounded_content_digest": safe.get("bounded_content_digest"),
                    "bounded_character_count": safe.get("bounded_character_count"),
                    "bounded_excerpt_text_retained": False,
                    "evidence_admitted": False,
                    "citation_eligibility_created": False,
                    "product_correctness_claimed": False,
                }
            )
        )
    return refs


def _candidate_ids(value: Any) -> set[str]:
    return {
        candidate_id
        for candidate_id in (
            _clean_text(_safe_mapping(item).get("candidate_id"), limit=320)
            for item in _safe_sequence(value)
        )
        if candidate_id
    }


def _candidate_ids_from_excerpts(input_packet: Mapping[str, Any]) -> set[str]:
    return {
        candidate_id
        for candidate_id in (
            _clean_text(_safe_mapping(item).get("candidate_id"), limit=320)
            for item in _safe_sequence(input_packet.get("bounded_evidence_excerpts"))
        )
        if candidate_id
    }


def _known_claim_ids(input_packet: Mapping[str, Any]) -> set[str]:
    return {
        claim_id
        for claim_id in (
            _clean_text(_safe_mapping(item).get("analysis_claim_id"), limit=260)
            for item in _safe_sequence(input_packet.get("analysis_claims"))
        )
        if claim_id
    }


def _gap_refs_for_claim(
    *,
    claim: Mapping[str, Any],
    input_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if claim.get("analysis_claim_kind") != ANALYSIS_CLAIM_KIND_GAP:
        return []
    refs = _safe_refs(claim.get("adjacent_or_excluded_candidate_refs"))
    if refs:
        return refs
    return _safe_refs(input_packet.get("unreadable_high_value_candidate_refs"))


def _value_appears_in_excerpts(
    answer_value: str,
    input_packet: Mapping[str, Any],
) -> bool:
    tokens = _value_tokens(answer_value)
    if not tokens:
        return True
    text = " ".join(
        _clean_text(_safe_mapping(item).get("bounded_excerpt_text"), limit=2_000)
        or ""
        for item in _safe_sequence(input_packet.get("bounded_evidence_excerpts"))
    ).casefold()
    return all(token.casefold() in text for token in tokens)


def _value_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for pattern in _VALUE_PATTERNS:
        tokens.extend(re.findall(pattern, value))
    return _unique(tokens)


def _proposed_answer_claim_ref(input_packet: Mapping[str, Any]) -> dict[str, Any]:
    claim = _safe_mapping(input_packet.get("proposed_answer_claim"))
    if not claim:
        return {}
    return _without_empty(
        {
            "proposed_answer_claim_id": claim.get("proposed_answer_claim_id"),
            "proposed_answer_claim_digest": claim.get(
                "proposed_answer_claim_digest"
            ),
            "requested_answer_type": claim.get("requested_answer_type"),
            "expected_value_shape": claim.get("expected_value_shape"),
            "requires_dprime_validation": True,
            "requires_runkernel_admission": True,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _claim_validation_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    validation = _safe_mapping(value)
    return _without_empty(
        {
            "analysis_claim_id": validation.get("analysis_claim_id"),
            "analysis_claim_digest": validation.get("analysis_claim_digest"),
            "analysis_claim_kind": validation.get("analysis_claim_kind"),
            "dprime_support_validation_status": validation.get(
                "dprime_support_validation_status"
            ),
            "claim_validation_digest": validation.get("claim_validation_digest"),
            "claim_within_requested_answer_type": validation.get(
                "claim_within_requested_answer_type"
            )
            is True,
            "claim_uses_only_allowed_candidate_roles": validation.get(
                "claim_uses_only_allowed_candidate_roles"
            )
            is True,
            "claim_grounded_in_bounded_evidence": validation.get(
                "claim_grounded_in_bounded_evidence"
            )
            is True,
            "evidence_admitted": False,
            "citation_eligibility_created": False,
            "product_correctness_claimed": False,
        }
    )


def _support_map_validation_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    validation = _safe_mapping(value)
    if not validation:
        return {}
    digest = validation.get("source_support_map_validation_digest") or _digest_json(
        validation
    )
    return _without_empty(
        {
            "source_support_map_validation_id": validation.get(
                "source_support_map_validation_id"
            )
            or f"dprime-source-support-map-validation:{str(digest)[:20]}",
            "source_support_map_validation_digest": digest,
            "source_support_map_validation_status": validation.get(
                "source_support_map_validation_status"
            ),
            "invalid_edge_count": len(
                _safe_sequence(validation.get("invalid_edge_refs"))
            ),
            "unsupported_edge_count": len(
                _safe_sequence(validation.get("unsupported_edge_refs"))
            ),
            "adjacent_as_answer_edge_count": len(
                _safe_sequence(validation.get("adjacent_as_answer_edge_refs"))
            ),
            "unreadable_as_support_edge_count": len(
                _safe_sequence(validation.get("unreadable_as_support_edge_refs"))
            ),
            "validated_support_edge_count": len(
                _safe_sequence(validation.get("validated_support_edge_refs"))
            ),
            "product_correctness_claimed": False,
        }
    )


def _edge_ref(edge: Mapping[str, Any]) -> dict[str, Any]:
    candidate_ref = _safe_mapping(edge.get("candidate_ref"))
    ref = _without_empty(
        {
            "edge_kind": edge.get("edge_kind"),
            "analysis_claim_id": edge.get("analysis_claim_id"),
            "candidate_id": candidate_ref.get("candidate_id"),
            "candidate_digest": candidate_ref.get("candidate_digest"),
            "candidate_triage_role": edge.get("candidate_triage_role"),
            "support_status_proposed": edge.get("support_status_proposed"),
        }
    )
    ref["edge_digest"] = _digest_json(ref)
    return ref


def _validation_refs_by_kind(
    claim_validations: Sequence[Mapping[str, Any]],
    kinds: set[str],
) -> list[dict[str, Any]]:
    return [
        _claim_validation_ref(item)
        for item in claim_validations
        if _safe_mapping(item).get("analysis_claim_kind") in kinds
    ]


def _claim_validation_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(value)
    safe.pop("claim_validation_digest", None)
    safe["claim_validation_digest"] = _digest_json(safe)
    return safe


def _summary_ref(
    *,
    status: str,
    summary: str,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    ref = {
        "validation_summary": _clean_text(summary, limit=700) or status,
        "dprime_validation_status": status,
        "reason_codes": list(_unique(reason_codes)),
        "product_correctness_claimed": False,
    }
    ref["validation_summary_digest"] = _digest_json(ref)
    return ref


def _summary_text(*, status: str, reason_codes: Sequence[str]) -> str:
    if status == DPRIME_SUPPORT_VALIDATION_SUPPORTED:
        return (
            "D-prime validated the AnalystFindingProposal as supported by "
            "bounded evidence and candidate custody; RunKernel admission is "
            "still required."
        )
    if status == DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM:
        return "D-prime rejected adjacent or excluded material as answer support."
    if status == DPRIME_SUPPORT_VALIDATION_INSUFFICIENT:
        return "D-prime could not validate support from available bounded evidence."
    if status == DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP:
        return "D-prime preserved an unreadable source gap instead of support."
    detail = ", ".join(_unique(reason_codes))
    return f"D-prime AnalystFinding validation failed closed: {detail or status}."


def _claim_summary(status: str, reason_codes: Sequence[str]) -> str:
    if status == DPRIME_SUPPORT_VALIDATION_SUPPORTED:
        return "Claim is supported by bounded evidence refs and allowed candidate roles."
    if not reason_codes:
        return f"Claim validation status: {status}."
    return f"Claim validation status: {status}; reasons: {', '.join(reason_codes)}."


def _dedupe_refs(refs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in refs:
        safe = _safe_mapping(item)
        identity = _clean_text(safe.get("candidate_id"), limit=320) or _digest_json(safe)
        if identity in seen:
            continue
        seen.add(identity)
        out.append(safe)
    return out


def _non_authority_posture() -> dict[str, Any]:
    return {
        **_NON_AUTHORITY_FALSE_FLAGS,
        **_RAW_FALSE_FLAGS,
        "raw_private_retention_flags": dict(_RAW_FALSE_FLAGS),
    }


def _drop_bounded_excerpt_text(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _drop_bounded_excerpt_text(item)
            for key, item in value.items()
            if _normalize_key(key) != "bounded_excerpt_text"
        }
    if isinstance(value, list | tuple | set | frozenset):
        return [_drop_bounded_excerpt_text(item) for item in value]
    return value


def _reject_forbidden_or_authority(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_KEYS)
    if forbidden:
        raise DPrimeAnalystFindingSupportValidationError(
            f"{context} includes forbidden material: {', '.join(forbidden)}"
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeAnalystFindingSupportValidationError(
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


def _without_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"validation_digest", "validation_id"}
    }


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    return [_safe_mapping(item) for item in _safe_sequence(value) if _safe_mapping(item)]


def _safe_mapping(value: Any) -> dict[str, Any]:
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


def _unique(values: Sequence[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = _clean_text(raw, limit=160)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _bounded_int(value: Any, *, default: int = 0) -> int:
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
        if value not in (None, "", [], {}, ())
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_INPUT_SCHEMA_VERSION",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_KIND",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_PHASE",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_ROLE_SURFACE",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_RUNTIME_CONSUMER",
    "DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_SCHEMA_VERSION",
    "DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM",
    "DPRIME_SUPPORT_VALIDATION_INSUFFICIENT",
    "DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL",
    "DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_ADAPTER",
    "DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_BOUNDED_EVIDENCE",
    "DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_LICENSE",
    "DPRIME_SUPPORT_VALIDATION_PARTIAL",
    "DPRIME_SUPPORT_VALIDATION_SUPPORTED",
    "DPRIME_SUPPORT_VALIDATION_UNREADABLE_GAP",
    "DPRIME_SUPPORT_VALIDATION_UNSUPPORTED",
    "DPrimeAnalystFindingSupportValidationError",
    "analyst_finding_support_validation_required",
    "build_dprime_analyst_finding_support_validation",
    "build_dprime_analyst_finding_support_validation_input_packet",
    "dprime_analyst_finding_support_validation_ref",
    "support_validation_allows_runkernel_admission",
    "validate_dprime_analyst_finding_support_validation",
]
