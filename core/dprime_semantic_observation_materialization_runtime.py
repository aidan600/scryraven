"""RunKernel-owned D-prime SemanticObservation materialization.

This runtime consumes a RunKernel-owned admitted D-prime decision and
materializes SemanticObservation only. It does not bind ComponentCoverage. It
does not create citations, source-obligation satisfaction, readiness, FAP,
Author output, answer text, product correctness, live calls, provider calls,
model calls, search, fetch/read, or retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.dprime_runkernel_admission_runtime import (
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE,
    RunKernelDPrimeAdmissionDecision,
)
from core.dprime_support_proposal_schema import (
    DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
)
from core.evidence_ledger_candidate_custody import EvidenceLedgerCandidateCustodyError
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_observation_foundation import (
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)

DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SCHEMA_VERSION = (
    "dprime_semantic_observation_materialization_runtime_v1"
)
DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE = (
    "core.dprime_semantic_observation_materialization_runtime"
)
DPRIME_SEMANTIC_OBSERVATION_MATERIALIZED = "materialized"
BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT = (
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT"
)
BLOCKED_DPRIME_SEMANTIC_OBSERVATION_DECISION_NOT_ADMITTED = (
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_DECISION_NOT_ADMITTED"
)
BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED = (
    "BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED"
)

_SUPPORTED_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
_SUPPORTED_SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"
_RAW_PRIVATE_KEYS = frozenset(
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
        "full_trace",
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
_CLOSED_SURFACE_KEYS = frozenset(
    {
        "answer_text_created",
        "author_answer_created",
        "author_input_created",
        "citation_eligibility_claimed",
        "citation_eligible",
        "component_coverage_bound",
        "component_coverage_created",
        "final_answer_packet_created",
        "product_correctness_claimed",
        "source_obligation_satisfaction_claimed",
        "source_obligation_satisfied",
        "sufficiency_readiness_created",
    }
)
_DOWNSTREAM_FORBIDDEN_KEYS = frozenset(
    {
        "answer_text",
        "author_answer",
        "author_input",
        "citation",
        "citation_eligibility",
        "citation_eligible",
        "component_coverage",
        "component_coverage_ref",
        "component_coverage_status",
        "coverage",
        "coverage_record",
        "coverage_ref",
        "final_answer_packet",
        "product_correctness",
        "semantic_observation",
        "semantic_observation_admission",
        "semantic_observation_ref",
        "semantic_observation_status",
        "source_obligation_satisfaction",
        "sufficiency_readiness",
    }
)
_ALLOWED_FALSE_POSTURE_KEYS = frozenset(
    {
        "citation_eligibility_claimed",
        "component_coverage_bound",
        "component_coverage_created",
        "product_correctness_claimed",
        "source_obligation_satisfied",
    }
)


class DPrimeSemanticObservationMaterializationError(ValueError):
    """Raised when D-prime material cannot become SemanticObservation safely."""

    def __init__(self, blocker: str, detail: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DPrimeSemanticObservationMaterializationResult:
    """Compact product-visible result; ComponentCoverage remains unbound."""

    semantic_observation: SemanticObservation
    sanitized_content_reference: SanitizedContentReference
    admission_projection: Mapping[str, Any]
    run_kernel_decision_ref: Mapping[str, Any]
    support_proposal_ref: Mapping[str, Any]
    assessment_material_ref: Mapping[str, Any]

    @property
    def semantic_observation_ref(self) -> dict[str, Any]:
        return {
            "observation_id": self.semantic_observation.observation_id,
            "observation_digest": self.semantic_observation.observation_digest,
            "content_refs": list(self.semantic_observation.content_refs),
            "evidence_refs": list(self.semantic_observation.evidence_refs),
        }

    def to_status_overlay(self) -> dict[str, Any]:
        ref = self.semantic_observation_ref
        return {
            "semantic_observation_admission_status": (
                DPRIME_SEMANTIC_OBSERVATION_MATERIALIZED
            ),
            "semantic_observation_ref": {
                "observation_id": ref["observation_id"],
                "observation_digest": ref["observation_digest"],
                "owner": "RunKernel.SemanticObservationAdmission",
                "runtime_surface": DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE,
            },
            "admitted_support": True,
            "component_coverage_status": "not licensed",
            "semantic_support_source": (
                "available from D-prime SemanticObservation; ComponentCoverage "
                "not licensed"
            ),
            "decision": BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED,
            "blocker_detail": (
                "D-prime SemanticObservation materialized through RunKernel-owned "
                "admission; ComponentCoverage binding is not licensed"
            ),
        }

    def semantic_status_ref(self) -> dict[str, Any]:
        ref = self.semantic_observation_ref
        return {
            "status": "admitted",
            "observation_ref": _id_digest_ref(
                ref["observation_id"],
                ref["observation_digest"],
            ),
            "observation_id": ref["observation_id"],
            "observation_digest": ref["observation_digest"],
            "content_refs": ref["content_refs"],
            "evidence_refs": ref["evidence_refs"],
            "reasons": [
                "RunKernel-owned D-prime decision admitted the proposal",
                "SemanticObservation admitted through existing RunKernel authority",
            ],
        }

    def coverage_status_ref(self, *, component_id: str | None) -> dict[str, Any]:
        return {
            "status": "not licensed",
            "coverage_ref": "unavailable",
            "component_id": component_id,
            "reasons": [
                "SemanticObservation materialization is not ComponentCoverage",
                "ComponentCoverage binding is closed in this phase",
            ],
        }


def materialize_dprime_semantic_observation_from_admitted_decision(
    *,
    decision: RunKernelDPrimeAdmissionDecision | Mapping[str, Any],
    assessment_material_ref: Mapping[str, Any],
    validated_support_proposal_ref: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    source_evidence_admission_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    run_kernel: RunKernel | None = None,
) -> DPrimeSemanticObservationMaterializationResult:
    """Materialize one admitted D-prime decision using existing contract authority."""

    decision_ref = _decision_ref(decision)
    _require_admitted_runkernel_decision(decision_ref)
    assessment = _safe_mapping(assessment_material_ref)
    proposal = _safe_mapping(validated_support_proposal_ref)
    admission = _safe_mapping(source_evidence_admission_ref)
    component = _safe_mapping(component_ref)
    source_obligation = _safe_mapping(source_obligation_ref)
    for label, value in (
        ("assessment_material_ref", assessment),
        ("validated_support_proposal_ref", proposal),
        ("source_evidence_admission_ref", admission),
        ("component_ref", component),
        ("source_obligation_ref", source_obligation),
    ):
        _reject_raw_private_and_closed_material(value, context=label)
    _require_lineage(
        decision_ref=decision_ref,
        assessment=assessment,
        proposal=proposal,
        admission=admission,
        component=component,
        source_obligation=source_obligation,
    )

    try:
        fetch_packet = validate_fetch_read_content_packet(fetch_read_content_packet)
        reference = _matching_reference(
            fetch_packet,
            expected_candidate_id=_clean_text(admission.get("candidate_id"), limit=320),
            expected_reference_id=_clean_text(admission.get("reference_id"), limit=320),
        )
        if not reference:
            _insufficient("matching readable sanitized content reference is missing")
        _require_reference_lineage(
            fetch_packet=fetch_packet,
            reference=reference,
            admission=admission,
            component=component,
            source_obligation=source_obligation,
        )
        accepted_contract = _require_existing_answer_contract_authority(
            run_kernel=run_kernel,
            fetch_packet=fetch_packet,
            reference=reference,
            component=component,
        )
        reduce_fetch_read_content_packet_into_evidence_ledger(
            run_kernel=run_kernel,
            fetch_read_content_packet=fetch_packet,
        )
        component_binding = _accepted_component_binding(accepted_contract)
        content_ref = _content_reference(
            reference=reference,
            accepted_contract=accepted_contract,
            component_binding=component_binding,
            assessment=assessment,
        )
        semantic_observation = _semantic_observation(
            assessment=assessment,
            reference=reference,
            content_ref=content_ref,
            accepted_contract=accepted_contract,
            component_binding=component_binding,
            decision_ref=decision_ref,
            proposal=proposal,
        )
        action = run_kernel.authorize_semantic_observation_admission(
            semantic_observation_id=semantic_observation.observation_id,
            semantic_observation_digest=semantic_observation.observation_digest,
            answer_component_id=str(component_binding["component_id"]),
            component_revision=str(component_binding["component_revision"]),
            component_digest=str(component_binding["component_digest"]),
            inputs={
                "dprime_semantic_observation_materialization": (
                    DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE
                ),
                "run_kernel_dprime_decision_id": decision_ref.get("decision_id"),
                "run_kernel_dprime_decision_digest": decision_ref.get(
                    "decision_digest"
                ),
                "dprime_support_proposal_id": proposal.get("proposal_id"),
                "dprime_support_proposal_digest": proposal.get("proposal_digest"),
                "dprime_assessment_id": assessment.get("assessment_id"),
                "dprime_assessment_digest": assessment.get("assessment_digest"),
                "component_coverage_bound": False,
                "source_obligation_satisfied": False,
                "citation_eligibility_claimed": False,
                "product_correctness_claimed": False,
            },
        )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
                status=RunStageStatus.COMPLETED,
                payload={
                    "semantic_observation": semantic_observation.to_dict(),
                    "sanitized_content_references": [content_ref.to_dict()],
                },
            )
        )
    except DPrimeSemanticObservationMaterializationError:
        raise
    except (
        EvidenceLedgerCandidateCustodyError,
        FetchReadContentReferenceError,
        KeyError,
        RunKernelTransitionError,
        TypeError,
        ValueError,
    ) as exc:
        _insufficient(str(exc))

    return DPrimeSemanticObservationMaterializationResult(
        semantic_observation=semantic_observation,
        sanitized_content_reference=content_ref,
        admission_projection=dict(run_kernel.state.semantic_observation_admission_projection),
        run_kernel_decision_ref=decision_ref,
        support_proposal_ref=proposal,
        assessment_material_ref=assessment,
    )


def _decision_ref(
    decision: RunKernelDPrimeAdmissionDecision | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(decision, RunKernelDPrimeAdmissionDecision):
        return decision.to_dict()
    if isinstance(decision, Mapping):
        return dict(decision)
    _insufficient("RunKernel-owned D-prime decision is missing")


def _require_admitted_runkernel_decision(decision_ref: Mapping[str, Any]) -> None:
    if decision_ref.get("owner") != "RunKernel":
        _insufficient("D-prime decision owner is not RunKernel")
    if decision_ref.get("runtime_surface") != DPRIME_RUN_KERNEL_ADMISSION_RUNTIME_SURFACE:
        _insufficient("D-prime decision surface is not RunKernel-owned")
    if decision_ref.get("decision_status") != DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
        raise DPrimeSemanticObservationMaterializationError(
            BLOCKED_DPRIME_SEMANTIC_OBSERVATION_DECISION_NOT_ADMITTED,
            "D-prime SemanticObservation requires an admitted RunKernel decision",
        )


def _require_lineage(
    *,
    decision_ref: Mapping[str, Any],
    assessment: Mapping[str, Any],
    proposal: Mapping[str, Any],
    admission: Mapping[str, Any],
    component: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
) -> None:
    request = _safe_mapping(decision_ref.get("request_ref"))
    request_support = _safe_mapping(request.get("support_proposal_ref"))
    request_validation = _safe_mapping(request.get("validation_result_ref"))
    if request.get("request_status") != DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY:
        _insufficient("RunKernel D-prime request was not ready")
    if request_validation.get("validation_status") != (
        DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    ):
        _insufficient("D-prime proposal validation did not pass")
    if request_validation.get("support_proposal_validation_passed") is not True:
        _insufficient("D-prime proposal validation passed flag is missing")
    for key in ("proposal_id", "proposal_digest"):
        if not _clean_text(proposal.get(key), limit=320):
            _insufficient(f"validated support proposal lacks {key}")
        if proposal.get(key) != request_support.get(key):
            _insufficient(f"RunKernel decision request {key} lineage mismatch")
    for key in ("assessment_id", "assessment_digest", "source_proposition"):
        if not _clean_text(assessment.get(key), limit=1000):
            _insufficient(f"assessment material lacks {key}")
    claim = _safe_mapping(assessment.get("answer_component_claim"))
    if not _clean_text(claim.get("claim"), limit=1000):
        _insufficient("assessment material lacks answer component claim")
    if claim.get("component_id") != _SUPPORTED_COMPONENT_ID:
        _insufficient("assessment answer component does not match D-prime lane")
    if assessment.get("support_relation") not in {
        "directly_supports",
        "partially_supports",
    }:
        _insufficient("assessment support relation is not support-bearing")
    if admission.get("status") != "custody_created":
        _insufficient("source/evidence custody is not created")
    if component.get("component_id") != _SUPPORTED_COMPONENT_ID:
        _insufficient("component ref does not match D-prime lane")
    if component.get("component_coverage_bound") is not False:
        _insufficient("component coverage is already bound")
    ids = _text_tuple(source_obligation.get("source_obligation_candidate_ids"))
    if _SUPPORTED_SOURCE_OBLIGATION_ID not in ids:
        _insufficient("source-obligation lineage does not match D-prime lane")
    if source_obligation.get("satisfaction_claimed") is not False:
        _insufficient("source-obligation satisfaction is already claimed")
    flags = _safe_mapping(assessment.get("closed_surface_flags"))
    for key in (
        "semantic_observation_created",
        "component_coverage_bound",
        "citation_eligibility_claimed",
        "source_obligation_satisfaction_claimed",
        "answer_text_created",
        "product_correctness_claimed",
    ):
        if flags.get(key) is not False:
            _insufficient(f"assessment closed-surface flag is not false: {key}")


def _require_reference_lineage(
    *,
    fetch_packet: Mapping[str, Any],
    reference: Mapping[str, Any],
    admission: Mapping[str, Any],
    component: Mapping[str, Any],
    source_obligation: Mapping[str, Any],
) -> None:
    if fetch_packet.get("packet_id") != admission.get("fetch_read_content_packet_id"):
        _insufficient("fetch/read packet id does not match custody")
    if fetch_packet.get("packet_digest") != admission.get(
        "fetch_read_content_packet_digest"
    ):
        _insufficient("fetch/read packet digest does not match custody")
    for key in ("candidate_id", "reference_id", "reference_digest"):
        if reference.get(key) != admission.get(key):
            _insufficient(f"reference {key} does not match custody")
    if reference.get("fetch_read_status") != "readable":
        _insufficient("D-prime materialization requires a readable reference")
    if reference.get("bounded_text_sanitized") is not True:
        _insufficient("bounded content is not marked sanitized")
    if reference.get("bounded_text_bounded") is not True:
        _insufficient("bounded content is not marked bounded")
    if not _clean_text(reference.get("bounded_text"), limit=20_000):
        _insufficient("bounded sanitized content is missing")
    if not _clean_text(reference.get("excerpt_digest"), limit=128):
        _insufficient("bounded content digest is missing")
    if reference.get("component_id") != component.get("component_id"):
        _insufficient("reference component does not match component ref")
    reference_source_ids = _text_tuple(reference.get("source_obligation_candidate_ids"))
    readiness_source_ids = _text_tuple(
        source_obligation.get("source_obligation_candidate_ids")
    )
    if reference_source_ids != readiness_source_ids:
        _insufficient("reference source-obligation lineage mismatch")
    contract_ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    contract_digest = _clean_text(
        contract_ref.get("contract_digest")
        or reference.get("current_answer_contract_digest"),
        limit=128,
    )
    if not contract_ref.get("contract_version") or not contract_digest:
        _insufficient("current answer contract ref/digest is missing")
    if component.get("current_answer_contract_digest") != contract_digest:
        _insufficient("component current contract digest mismatch")


def _require_existing_answer_contract_authority(
    *,
    run_kernel: RunKernel | None,
    fetch_packet: Mapping[str, Any],
    reference: Mapping[str, Any],
    component: Mapping[str, Any],
) -> Mapping[str, Any]:
    if run_kernel is None:
        _insufficient(
            "missing ordinary D-prime product authority surface: an in-memory "
            "RunKernel with authorized accepted/current answer-contract authority "
            "for the retained D-prime source/fetch/read packet"
        )
    if run_kernel.state.run_id != str(fetch_packet.get("run_id")):
        _insufficient("RunKernel run_id does not match fetch/read packet")
    if run_kernel.state.request_id != str(fetch_packet.get("request_id")):
        _insufficient("RunKernel request_id does not match fetch/read packet")
    accepted_contract = _safe_mapping(run_kernel.state.initial_answer_contract)
    accepted_projection = _safe_mapping(
        run_kernel.state.initial_answer_contract_projection
    )
    current_contract = _safe_mapping(run_kernel.state.current_answer_contract)
    current_projection = _safe_mapping(
        run_kernel.state.current_answer_contract_projection
    )
    if not accepted_contract or not accepted_projection:
        _insufficient("accepted answer-contract authority is unavailable")
    if not current_contract or not current_projection:
        _insufficient("current answer-contract authority is unavailable")
    contract_ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    expected_digest = _required_token(
        contract_ref.get("contract_digest")
        or reference.get("current_answer_contract_digest"),
        "retained reference lacks current contract digest",
        limit=128,
    )
    if accepted_contract.get("accepted_contract_digest") != expected_digest:
        _insufficient("accepted answer-contract digest does not match reference")
    current_digest = (
        current_projection.get("current_contract_digest")
        or current_projection.get("accepted_contract_digest")
        or current_contract.get("current_contract_digest")
        or current_contract.get("accepted_contract_digest")
    )
    if current_digest != expected_digest:
        _insufficient("current answer-contract digest does not match reference")
    component_binding = _accepted_component_binding(accepted_contract)
    if component_binding.get("component_id") != component.get("component_id"):
        _insufficient("accepted contract component does not match D-prime component")
    if not _clean_text(component_binding.get("component_digest"), limit=128):
        _insufficient("accepted contract component digest is unavailable")
    return accepted_contract


def _accepted_component_binding(
    accepted_contract: Mapping[str, Any],
) -> Mapping[str, Any]:
    for item in _safe_sequence(accepted_contract.get("accepted_answer_component_refs")):
        component = _safe_mapping(item)
        if component.get("component_id") == _SUPPORTED_COMPONENT_ID:
            return component
    _insufficient("accepted contract does not contain the D-prime answer component")


def _matching_reference(
    packet: Mapping[str, Any],
    *,
    expected_candidate_id: str | None,
    expected_reference_id: str | None,
) -> dict[str, Any]:
    for item in _safe_sequence(packet.get("reference_records")):
        reference = _safe_mapping(item)
        if reference.get("fetch_read_status") != "readable":
            continue
        if expected_candidate_id and reference.get("candidate_id") != expected_candidate_id:
            continue
        if expected_reference_id and reference.get("reference_id") != expected_reference_id:
            continue
        return reference
    return {}


def _content_reference(
    *,
    reference: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    component_binding: Mapping[str, Any],
    assessment: Mapping[str, Any],
) -> SanitizedContentReference:
    selector = _safe_mapping(assessment.get("selector_ref"))
    return SanitizedContentReference(
        content_ref_id=str(reference["reference_id"]),
        evidence_ref_id=str(reference["candidate_id"]),
        admitted_evidence_ref=str(reference["candidate_id"]),
        source_id=f"source:{reference.get('candidate_domain')}",
        source_digest=str(reference["reference_digest"]),
        source_url=(
            reference.get("resolved_url")
            or reference.get("final_url")
            or reference.get("canonical_url")
            or reference.get("candidate_url")
        ),
        source_title=reference.get("content_title") or reference.get("candidate_title"),
        source_domain=reference.get("resolved_domain") or reference.get(
            "candidate_domain"
        ),
        answer_component_id=str(component_binding["component_id"]),
        component_revision=str(component_binding["component_revision"]),
        component_contract_digest=str(component_binding["component_digest"]),
        question_meaning_record_id=str(
            accepted_contract["parent_question_meaning_record_id"]
        ),
        question_meaning_record_digest=str(
            accepted_contract["parent_question_meaning_record_digest"]
        ),
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=str(reference["bounded_text"]),
        char_range_start=selector.get("selected_window_start_offset"),
        char_range_end=selector.get("selected_window_end_offset"),
        extraction_method=DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE,
        worker_kind="dprime_runkernel_decision_materialization",
        currentness="dprime_currentness_check_passed",
        observed_at=reference.get("retrieved_or_observed_at"),
        metadata={
            "phase": "DPRIME-SEMANTIC-OBSERVATION-MATERIALIZATION-01",
            "assessment_id": assessment.get("assessment_id"),
            "assessment_digest": assessment.get("assessment_digest"),
            "support_relation": assessment.get("support_relation"),
            "component_coverage_bound": False,
            "source_obligation_satisfied": False,
        },
    ).require_valid()


def _semantic_observation(
    *,
    assessment: Mapping[str, Any],
    reference: Mapping[str, Any],
    content_ref: SanitizedContentReference,
    accepted_contract: Mapping[str, Any],
    component_binding: Mapping[str, Any],
    decision_ref: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> SemanticObservation:
    assessment_digest = _required_token(
        assessment.get("assessment_digest"),
        "assessment material requires assessment_digest",
        limit=128,
    )
    claim = _safe_mapping(assessment.get("answer_component_claim"))
    claim_text = (
        _clean_text(claim.get("claim"), limit=500)
        or _clean_text(assessment.get("source_proposition"), limit=500)
        or "D-prime support assessment admitted from bounded sanitized content."
    )
    observation_id = (
        "semantic-observation:dprime:"
        f"{assessment_digest[:16]}:{content_ref.content_digest[:16]}"
    )
    return SemanticObservation(
        observation_id=observation_id,
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=str(
            accepted_contract["parent_question_meaning_record_id"]
        ),
        question_meaning_record_digest=str(
            accepted_contract["parent_question_meaning_record_digest"]
        ),
        contract_version=str(accepted_contract["accepted_contract_version"]),
        contract_digest=str(accepted_contract["accepted_contract_digest"]),
        answer_component_id=str(component_binding["component_id"]),
        component_revision=str(component_binding["component_revision"]),
        component_contract_digest=str(component_binding["component_digest"]),
        evidence_refs=(content_ref.evidence_ref_id,),
        content_refs=(content_ref.content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value=claim_text,
        normalization_fit="D-prime evidence-relative support assessment",
        scope_fit="accepted answer contract component",
        assumption_fit="no computation; source-obligation ids remain lineage only",
        inference_depth=0,
        candidate_caveats=(
            "SemanticObservation materialization does not bind ComponentCoverage.",
            "Citation eligibility and source-obligation satisfaction remain closed.",
        ),
        candidate_followup_gaps=(
            "ComponentCoverage binding is not licensed in this phase.",
        ),
        candidate_contract_amendment_notes=(
            "No current_answer_contract mutation is created by D-prime materialization.",
        ),
        metadata={
            "phase": "DPRIME-SEMANTIC-OBSERVATION-MATERIALIZATION-01",
            "runtime_surface": DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE,
            "run_kernel_dprime_decision_id": decision_ref.get("decision_id"),
            "run_kernel_dprime_decision_digest": decision_ref.get(
                "decision_digest"
            ),
            "dprime_support_proposal_id": proposal.get("proposal_id"),
            "dprime_support_proposal_digest": proposal.get("proposal_digest"),
            "dprime_assessment_id": assessment.get("assessment_id"),
            "dprime_assessment_digest": assessment_digest,
            "dprime_support_relation": assessment.get("support_relation"),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "component_coverage_bound": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_claimed": False,
            "product_correctness_claimed": False,
        },
    ).require_valid(content_references=(content_ref,))


def _reject_raw_private_and_closed_material(value: Any, *, context: str) -> None:
    for path, key, item in _walk_mapping_items(value):
        normalized = _normalize_key(key)
        if normalized in _RAW_PRIVATE_KEYS:
            _insufficient(f"{context} includes raw/private material: {'.'.join(path)}")
        if normalized in _DOWNSTREAM_FORBIDDEN_KEYS:
            _insufficient(
                f"{context} includes downstream closed material: {'.'.join(path)}"
            )
        if normalized in _ALLOWED_FALSE_POSTURE_KEYS and item is not False:
            _insufficient(f"{context} opens closed surface: {'.'.join(path)}")
        if (
            normalized in _CLOSED_SURFACE_KEYS
            and normalized not in _ALLOWED_FALSE_POSTURE_KEYS
            and item is not False
        ):
            _insufficient(f"{context} opens closed surface: {'.'.join(path)}")


def _walk_mapping_items(
    value: Any,
    path: Sequence[str] = (),
) -> list[tuple[tuple[str, ...], str, Any]]:
    items: list[tuple[tuple[str, ...], str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            item_path = (*path, key_text)
            items.append((item_path, key_text, item))
            items.extend(_walk_mapping_items(item, item_path))
    elif isinstance(value, list | tuple | set | frozenset):
        for index, item in enumerate(value):
            items.extend(_walk_mapping_items(item, (*path, str(index))))
    return items


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    token = _clean_text(value, limit=limit)
    if not token:
        _insufficient(message)
    return token


def _insufficient(message: str) -> None:
    raise DPrimeSemanticObservationMaterializationError(
        BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT,
        message,
    )


def _id_digest_ref(identifier: Any, digest: Any) -> str:
    clean_id = _clean_text(identifier, limit=320)
    clean_digest = _clean_text(digest, limit=128)
    if clean_id and clean_digest:
        return f"{clean_id} / {clean_digest}"
    return clean_id or clean_digest or "unavailable"


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        token = _clean_text(value, limit=limit)
        return (token,) if token else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _clean_text(item, limit=limit)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED",
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_DECISION_NOT_ADMITTED",
    "BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT",
    "DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SCHEMA_VERSION",
    "DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_SURFACE",
    "DPRIME_SEMANTIC_OBSERVATION_MATERIALIZED",
    "DPrimeSemanticObservationMaterializationError",
    "DPrimeSemanticObservationMaterializationResult",
    "materialize_dprime_semantic_observation_from_admitted_decision",
]
