"""Default-off ordinary main RunKernel coverage integration.

This repair keeps ordinary live source coverage on the main ``RunKernel``.  It
reuses the existing candidate handoff and source-custody helpers for bounded
offline inputs, then admits one SemanticObservation and reduces one
ComponentCoverage record through RunKernel authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.acquisition_adapters import AcquisitionTransports
from core.cap_enforcement import RunCapPolicy

from core.component_coverage_record import (
    ComponentCoverageRecord,
    ConflictPosture,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageLineage,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
)
from core.component_coverage_reduction_runtime import (
    evidence_ledger_projection_digest,
)
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.evidence_relative_analysis_packet import (
    EvidenceRelativeAnalysisPacketError,
    build_evidence_relative_analysis_packet,
    evidence_relative_analysis_packet_ref_from_packet,
)
from core.live_ordinary_candidate_handoff_runtime import (
    OrdinaryLiveCandidateHandoffResult,
    execute_ordinary_live_candidate_handoff,
)
from core.ordinary_live_source_custody_runtime import (
    OrdinaryLiveSourceCustodyResult,
    execute_ordinary_live_source_custody,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_observation_admission_bridge import (
    SemanticObservationAdmissionBridgeError,
    SemanticObservationAdmissionBridgeResult,
    admit_semantic_observations_from_analysis_support_findings,
)

ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY = (
    "ordinary_live_main_runkernel_coverage"
)
ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE = (
    "AG-ORDINARY-LIVE-MAIN-RUNKERNEL-COVERAGE-INTEGRATION-01"
)
ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_MODE = "REPAIR"

_MAIN_COMPONENT_ID = "component:ordinary-live-main-answer-primary"
_MAIN_SOURCE_OBLIGATION_ID = "obligation:ordinary-live-main-answer-source"
_MAIN_SEARCH_REQUIREMENT_ID = "searchreq:ordinary-live-main-answer-primary"
_DEMONSTRATION_INPUT = (
    "What is the official current permit threshold for the example program?"
)
_NEXT_PRODUCT_CHECKPOINT = "AG-ORDINARY-LIVE-ENTRYPOINT-VISIBILITY-01"
_READINESS_COMPATIBILITY_STATUS = "main_component_coverage_available"

_DIAGNOSTIC_AUTHORITY_KEYS = frozenset(
    {
        "ordinary_retrieval_results",
        "provider_diagnostic",
        "provider_diagnostics",
        "retrieval_diagnostic",
        "retrieval_diagnostics",
        "retrieval_result",
        "retrieval_results",
        "search_diagnostic",
        "search_diagnostics",
        "top_passage",
        "top_passages",
    }
)
_FORBIDDEN_TRACE_KEYS = frozenset(
    {
        "answer",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "body",
        "bounded_text",
        "citation",
        "citation_record",
        "citation_records",
        "citations",
        "cookie",
        "cookies",
        "fap",
        "final_answer",
        "final_answer_packet",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_obligation_satisfaction",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_CLOSED_FALSE_FLAGS = {
    "main_run_kernel_consumed": True,
    "child_kernel_used": False,
    "child_acquisition_only": False,
    "projection_to_runkernel_rehydration": False,
    "direct_runkernel_mutation": False,
    "product_code_imports_scripts_ag": False,
    "retrieval_diagnostics_used_as_authority": False,
    "sufficiency_readiness_reduced": False,
    "fap_created": False,
    "author_invoked": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "citation_rendered_or_eligible": False,
    "answer_text_created": False,
    "product_correctness_claimed": False,
}
_NON_PROOFS = (
    "no live provider/search/broker/fetch/model call",
    "no retrieval diagnostics promoted into authority",
    "no projection-to-RunKernel rehydration",
    "no direct RunKernel state mutation outside RunKernel.reduce",
    "no source-obligation satisfaction",
    "no citation eligibility or citation rendering",
    "no SufficiencyReadiness reduction",
    "no FinalAnswerPacket creation",
    "no Author or AuthorProse invocation",
    "no answer text or product correctness claim",
)
_FORBIDDEN_SUBSTITUTES = (
    "child-only ComponentCoverage",
    "projection rehydration into RunKernel state",
    "retrieval diagnostics as authority",
    "direct RunKernel state mutation",
    "phase-only harness imports",
)


class OrdinaryLiveMainRunKernelCoverageError(ValueError):
    """Raised internally when the main RunKernel repair must fail closed."""

    def __init__(self, first_failed_seam: str, message: str) -> None:
        super().__init__(message)
        self.first_failed_seam = first_failed_seam


@dataclass(frozen=True, slots=True)
class OrdinaryLiveMainRunKernelCoverageResult:
    projection: dict[str, Any]
    candidate_handoff_result: OrdinaryLiveCandidateHandoffResult | None = None
    source_custody_result: OrdinaryLiveSourceCustodyResult | None = None
    evidence_relative_analysis_packet: dict[str, Any] | None = None
    semantic_observation_admission_result: (
        SemanticObservationAdmissionBridgeResult | None
    ) = None
    component_coverage_projection: dict[str, Any] | None = None


def ordinary_live_main_runkernel_coverage_disabled_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
        "phase": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE,
        "mode": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_MODE,
        "enabled": False,
        "ran": False,
        "failed_closed": False,
        "status": "disabled",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
    }


def execute_ordinary_live_main_runkernel_coverage(
    *,
    main_run_kernel: RunKernel | None,
    query: str,
    requested_mode: str,
    run_contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None = None,
    core_topic: str | None = None,
    candidate_results: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    provider_authorized: str = "offline-fake-search",
    fetch_read: Callable[..., Mapping[str, Any]] | None = None,
    available_providers: Mapping[str, object] | None = None,
    acquisition_transports: AcquisitionTransports | None = None,
    cap_policy: RunCapPolicy | None = None,
    required_or_preferred_anchors: Sequence[Any] = (),
) -> OrdinaryLiveMainRunKernelCoverageResult:
    """Reduce one ordinary source into main-owned semantic coverage."""

    base = _base_projection()
    candidate_result: OrdinaryLiveCandidateHandoffResult | None = None
    source_result: OrdinaryLiveSourceCustodyResult | None = None
    analysis_packet: dict[str, Any] | None = None
    bridge_result: SemanticObservationAdmissionBridgeResult | None = None
    coverage_projection: dict[str, Any] | None = None
    source_refs: dict[str, Any] = {}
    component_ref: dict[str, Any] = {}
    counts = {
        "candidate_handoff_attempted_count": 0,
        "candidate_handoff_completed_count": 0,
        "source_custody_attempted_count": 0,
        "source_custody_completed_count": 0,
        "evidence_relative_analysis_packet_attempted_count": 0,
        "evidence_relative_analysis_packet_built_count": 0,
        "semantic_observation_attempted_count": 0,
        "semantic_observation_admitted_count": 0,
        "component_coverage_attempted_count": 0,
        "component_coverage_reduced_count": 0,
    }

    try:
        if main_run_kernel is None:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "main_run_kernel_missing",
                "ordinary main RunKernel coverage requires the main RunKernel",
            )

        component_id = _main_component_id(main_run_kernel)
        counts["candidate_handoff_attempted_count"] = 1
        candidate_result = execute_ordinary_live_candidate_handoff(
            run_kernel=main_run_kernel,
            query=query,
            requested_mode=requested_mode,
            run_contract_projection=run_contract_projection,
            route_projection=route_projection,
            core_topic=core_topic,
            candidate_results=candidate_results,
            provider_authorized=provider_authorized,
            component_id=component_id,
            source_obligation_id=_MAIN_SOURCE_OBLIGATION_ID,
            search_requirement_id=_MAIN_SEARCH_REQUIREMENT_ID,
            planner_purpose="main_answer_coverage",
        )
        if _safe_mapping(candidate_result.projection).get("failed_closed") is True:
            raise OrdinaryLiveMainRunKernelCoverageError(
                str(
                    _safe_mapping(candidate_result.projection).get(
                        "first_failed_seam"
                    )
                    or "ordinary_live_candidate_handoff_failed_closed"
                ),
                "ordinary main RunKernel coverage requires candidate handoff success",
            )
        if not candidate_result.candidate_packet:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "search_result_candidate_packet_missing",
                "ordinary main RunKernel coverage requires a candidate packet",
            )
        counts["candidate_handoff_completed_count"] = 1
        component_ref = _component_ref(main_run_kernel, component_id)

        counts["source_custody_attempted_count"] = 1
        source_result = execute_ordinary_live_source_custody(
            run_kernel=main_run_kernel,
            parent_run_id=main_run_kernel.state.run_id,
            parent_request_id=main_run_kernel.state.request_id,
            candidate_packet=candidate_result.candidate_packet,
            fetch_read=fetch_read,
            available_providers=available_providers,
            acquisition_transports=acquisition_transports,
            cap_policy=cap_policy,
            required_or_preferred_anchors=required_or_preferred_anchors,
            component_text=core_topic,
            claim_under_test=None,
        )
        if _safe_mapping(source_result.projection).get("failed_closed") is True:
            raise OrdinaryLiveMainRunKernelCoverageError(
                str(
                    _safe_mapping(source_result.projection).get("first_failed_seam")
                    or "ordinary_live_source_custody_failed_closed"
                ),
                "ordinary main RunKernel coverage requires source custody success",
            )
        source_refs = _source_refs(source_result)
        fetch_read_content_packet = _safe_mapping(
            source_result.fetch_read_content_packet
        )
        sanitized_content_reference = _safe_mapping(
            source_result.sanitized_content_reference
        )
        evidence_ledger_projection = _safe_mapping(
            source_result.evidence_ledger_projection
        )
        if not fetch_read_content_packet:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "fetch_read_content_packet_missing",
                "ordinary main RunKernel coverage requires FetchReadContentPacket",
            )
        if not sanitized_content_reference:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "sanitized_content_reference_missing",
                "ordinary main RunKernel coverage requires SanitizedContentReference",
            )
        if not evidence_ledger_projection:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "evidence_ledger_projection_missing",
                "ordinary main RunKernel coverage requires EvidenceLedger projection",
            )
        counts["source_custody_completed_count"] = 1
        analysis_ledger_projection = _analysis_ledger_projection(
            evidence_ledger_projection
        )

        proposal = _source_bound_support_proposal(
            run_kernel=main_run_kernel,
            sanitized_content_reference=sanitized_content_reference,
            evidence_ledger_projection=analysis_ledger_projection,
            component_id=component_ref["component_id"],
        )
        counts["evidence_relative_analysis_packet_attempted_count"] = 1
        analysis_packet = build_evidence_relative_analysis_packet(
            evidence_ledger_projection=analysis_ledger_projection,
            analyst_proposal_records=[proposal],
            run_id=main_run_kernel.state.run_id,
            request_id=main_run_kernel.state.request_id,
            current_answer_contract_ref=sanitized_content_reference.get(
                "current_answer_contract_ref"
            ),
            current_answer_contract_digest=sanitized_content_reference.get(
                "current_answer_contract_digest"
            ),
        )
        counts["evidence_relative_analysis_packet_built_count"] = 1
        findings = _safe_list(
            _safe_mapping(analysis_packet.get("analyst_report")).get("findings")
        )
        if len(findings) != 1:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "evidence_relative_analysis_packet_finding_count_invalid",
                "ordinary main RunKernel coverage expects one support finding",
            )

        counts["semantic_observation_attempted_count"] = 1
        admitted = admit_semantic_observations_from_analysis_support_findings(
            run_kernel=main_run_kernel,
            evidence_relative_analysis_packet=analysis_packet,
            fetch_read_content_packet=fetch_read_content_packet,
            finding_ids=(str(findings[0]["finding_id"]),),
        )
        if len(admitted) != 1:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "semantic_observation_admission_count_invalid",
                "ordinary main RunKernel coverage expects one admission",
            )
        bridge_result = admitted[0]
        counts["semantic_observation_admitted_count"] = 1
        component_ref = _component_ref(
            main_run_kernel,
            bridge_result.semantic_observation.answer_component_id,
        )
        if not _component_match(component_ref, bridge_result.semantic_observation):
            raise OrdinaryLiveMainRunKernelCoverageError(
                "semantic_observation_component_binding_mismatch",
                "SemanticObservation must exactly match the main accepted component",
            )

        counts["component_coverage_attempted_count"] = 1
        coverage_projection = _reduce_component_coverage(
            run_kernel=main_run_kernel,
            admission_result=bridge_result,
        )
        counts["component_coverage_reduced_count"] = 1
        exact_match = _coverage_matches_component(
            coverage_projection=coverage_projection,
            component_ref=component_ref,
        )
        if not exact_match:
            raise OrdinaryLiveMainRunKernelCoverageError(
                "component_coverage_component_binding_mismatch",
                "ComponentCoverage must exactly match the main accepted component",
            )

        projection = _success_projection(
            base=base,
            counts=counts,
            source_refs=source_refs,
            component_ref=component_ref,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
            run_kernel=main_run_kernel,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveMainRunKernelCoverageResult(
            projection=projection,
            candidate_handoff_result=candidate_result,
            source_custody_result=source_result,
            evidence_relative_analysis_packet=analysis_packet,
            semantic_observation_admission_result=bridge_result,
            component_coverage_projection=coverage_projection,
        )
    except OrdinaryLiveMainRunKernelCoverageError as exc:
        projection = _fail_projection(
            base,
            exc.first_failed_seam,
            str(exc),
            counts=counts,
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=main_run_kernel,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveMainRunKernelCoverageResult(
            projection=projection,
            candidate_handoff_result=candidate_result,
            source_custody_result=source_result,
        )
    except (
        EvidenceRelativeAnalysisPacketError,
        SemanticObservationAdmissionBridgeError,
        RunKernelTransitionError,
        ValueError,
    ) as exc:
        seam = _known_exception_seam(
            exc,
            analysis_built=counts["evidence_relative_analysis_packet_built_count"],
            semantic_admitted=counts["semantic_observation_admitted_count"],
            coverage_attempted=counts["component_coverage_attempted_count"],
        )
        projection = _fail_projection(
            base,
            seam,
            str(exc),
            counts=counts,
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=main_run_kernel,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveMainRunKernelCoverageResult(
            projection=projection,
            candidate_handoff_result=candidate_result,
            source_custody_result=source_result,
        )
    except Exception as exc:
        projection = _fail_projection(
            base,
            "ordinary_live_main_runkernel_coverage_exception",
            str(exc),
            counts=counts,
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=main_run_kernel,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveMainRunKernelCoverageResult(
            projection=projection,
            candidate_handoff_result=candidate_result,
            source_custody_result=source_result,
        )


def _source_bound_support_proposal(
    *,
    run_kernel: RunKernel,
    sanitized_content_reference: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    if sanitized_content_reference.get("fetch_read_status") != "readable":
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_content_not_readable",
            "ordinary main RunKernel coverage requires readable source content",
        )
    if sanitized_content_reference.get("bounded_text_sanitized") is not True:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_content_not_sanitized",
            "ordinary main RunKernel coverage requires sanitized bounded content",
        )
    if sanitized_content_reference.get("bounded_text_bounded") is not True:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_content_not_bounded",
            "ordinary main RunKernel coverage requires explicitly bounded content",
        )
    if not _clean_text(sanitized_content_reference.get("bounded_text"), limit=20_000):
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_content_empty",
            "ordinary main RunKernel coverage requires non-empty bounded content",
        )
    selection = _safe_mapping(sanitized_content_reference.get("bounded_text_selection"))
    required_count = _bounded_int(selection.get("required_anchor_count"))
    matched_count = _bounded_int(selection.get("matched_anchor_count"))
    missing_anchors = _safe_list(selection.get("missing_anchors"))
    if required_count > 0 and (missing_anchors or matched_count < required_count):
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_anchor_precondition_unmet",
            "ordinary main RunKernel coverage requires matched source anchors",
        )
    record = _custody_record_for_reference(
        evidence_ledger_projection=evidence_ledger_projection,
        reference_id=str(sanitized_content_reference.get("reference_id") or ""),
    )
    for key in (
        "reference_id",
        "reference_digest",
        "candidate_id",
        "candidate_digest",
        "search_result_candidate_packet_digest",
    ):
        if _clean_text(record.get(key), limit=320) != _clean_text(
            sanitized_content_reference.get(key),
            limit=320,
        ):
            raise OrdinaryLiveMainRunKernelCoverageError(
                "source_custody_reference_mismatch",
                f"ordinary main RunKernel coverage source-custody {key} mismatch",
            )
    for record_key, reference_key in (
        ("fetch_read_content_packet_id", "packet_id"),
        ("fetch_read_content_packet_digest", "packet_digest"),
    ):
        if _clean_text(record.get(record_key), limit=320) != _clean_text(
            sanitized_content_reference.get(reference_key),
            limit=320,
        ):
            raise OrdinaryLiveMainRunKernelCoverageError(
                "source_custody_reference_mismatch",
                "ordinary main RunKernel coverage source-custody "
                f"{record_key} mismatch",
            )
    record_component_id = _clean_text(record.get("component_id"), limit=260)
    if record_component_id != component_id:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_component_not_main_answer_component",
            "ordinary main RunKernel coverage requires main component custody",
        )
    _component_ref(run_kernel, record_component_id)
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_id": record.get("fetch_read_content_packet_id"),
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_id": record.get(
            "search_result_candidate_packet_id"
        ),
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "search_result_candidate_record_digest": record.get(
            "search_result_candidate_record_digest"
        ),
        "component_id": record_component_id,
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "proposal_summary": (
            "Bounded ordinary source-custody content supports the main accepted "
            "answer component."
        ),
        "reason": (
            "Readable bounded sanitized source-custody content matched the "
            "configured source-custody selection preconditions."
        ),
    }


def _reduce_component_coverage(
    *,
    run_kernel: RunKernel,
    admission_result: SemanticObservationAdmissionBridgeResult,
) -> dict[str, Any]:
    observation = admission_result.semantic_observation
    content_ref = admission_result.sanitized_content_reference
    component_ref = _component_ref(run_kernel, observation.answer_component_id)
    record = ComponentCoverageRecord(
        record_id=(
            "coverage:ordinary-live-main-runkernel:"
            f"{observation.observation_digest[:16]}"
        ),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=run_kernel.state.initial_answer_contract[
            "parent_question_meaning_record_digest"
        ],
        accepted_contract_version=run_kernel.state.initial_answer_contract[
            "accepted_contract_version"
        ],
        accepted_contract_digest=run_kernel.state.initial_answer_contract[
            "accepted_contract_digest"
        ],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(run_kernel),
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(
            SemanticObservationCoverageRef.from_observation(observation),
        ),
        content_reference_bindings=(
            ContentReferenceCoverageBinding.from_content_reference(content_ref),
        ),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        conflict_posture=ConflictPosture.UNKNOWN,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=(
            "source obligation remains unsatisfied and lineage-only",
            "coverage is structural readiness input only",
        ),
        required_caveats=(
            "Do not upgrade ComponentCoverage to source-obligation satisfaction.",
            "Do not upgrade semantic support to citation eligibility or rendering.",
        ),
        prohibited_upgrades=(
            "Do not create Sufficiency, FAP, Author, citation, answer, or "
            "product-correctness claims.",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        lineage=CoverageLineage(
            created_by=ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE,
            created_from=(
                "ordinary_live_main_runkernel_candidate_handoff",
                "ordinary_live_source_custody_result",
                "evidence_relative_analysis_packet",
                "admitted_semantic_observation",
            ),
        ),
        metadata={
            "phase": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE,
            "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
            "coverage_is_main_runkernel_answer_component_support": True,
            "source_obligation_satisfied": False,
            "readiness_input_compatibility": True,
        },
    ).require_valid()
    action = run_kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={"phase": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE},
    )
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": payload},
        )
    )
    return dict(run_kernel.state.component_coverage_projection)


def _component_ref(run_kernel: RunKernel, component_id: str) -> dict[str, Any]:
    for ref in run_kernel.state.initial_answer_contract.get(
        "accepted_answer_component_refs",
        [],
    ):
        if isinstance(ref, Mapping) and ref.get("component_id") == component_id:
            return dict(ref)
    raise OrdinaryLiveMainRunKernelCoverageError(
        "coverage_component_missing_from_main_accepted_contract",
        "ordinary main RunKernel coverage requires a main accepted component",
    )


def _main_component_id(run_kernel: RunKernel) -> str:
    for ref in run_kernel.state.initial_answer_contract.get(
        "accepted_answer_component_refs",
        [],
    ):
        if isinstance(ref, Mapping) and ref.get("component_id"):
            return str(ref["component_id"])
    return _MAIN_COMPONENT_ID


def _ledger_binding(run_kernel: RunKernel) -> EvidenceLedgerSnapshotBinding:
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        str(ref["observation_id"])
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{run_kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _custody_record_for_reference(
    *,
    evidence_ledger_projection: Mapping[str, Any],
    reference_id: str,
) -> dict[str, Any]:
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    records = [
        _safe_mapping(item)
        for item in _safe_list(custody.get("fetch_read_candidate_custody_records"))
        if isinstance(item, Mapping)
    ]
    for record in records:
        if record.get("reference_id") == reference_id:
            if record.get("fetch_read_status") != "readable":
                raise OrdinaryLiveMainRunKernelCoverageError(
                    "source_custody_record_not_readable",
                    "ordinary main RunKernel coverage requires readable custody",
                )
            return record
    raise OrdinaryLiveMainRunKernelCoverageError(
        "source_custody_record_missing",
        "ordinary main RunKernel coverage requires matching EvidenceLedger custody",
    )


def _analysis_ledger_projection(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    records = [
        _safe_mapping(item)
        for item in _safe_list(custody.get("fetch_read_candidate_custody_records"))
        if isinstance(item, Mapping)
    ]
    if not records:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "source_custody_record_missing",
            "ordinary main RunKernel coverage requires fetch/read custody records",
        )
    return {
        "fetch_read_candidate_custody": {
            key: custody.get(key)
            for key in (
                "trace_key",
                "custody_record_count",
                "readable_record_count",
                "fetch_read_candidate_custody_records",
            )
            if key in custody
        }
    }


def _source_refs(source_result: OrdinaryLiveSourceCustodyResult) -> dict[str, Any]:
    source_projection = _safe_mapping(source_result.projection)
    fetch_read_content_packet = _safe_mapping(source_result.fetch_read_content_packet)
    sanitized_content_reference = _safe_mapping(source_result.sanitized_content_reference)
    evidence_ledger_projection = _safe_mapping(source_result.evidence_ledger_projection)
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    return _without_empty(
        {
            "source_custody_result_object_consumed": True,
            "source_custody_projection_only_consumed": False,
            "source_custody_authority_owner": "main_run_kernel",
            "source_custody_status": source_projection.get("status"),
            "search_result_candidate_packet_ref": _candidate_packet_ref(
                fetch_read_content_packet,
                sanitized_content_reference,
            ),
            "fetch_read_content_packet_ref": {
                "packet_id": fetch_read_content_packet.get("packet_id"),
                "packet_digest": fetch_read_content_packet.get("packet_digest"),
                "reference_count": fetch_read_content_packet.get("reference_count"),
            },
            "sanitized_content_reference_ref": {
                "reference_id": sanitized_content_reference.get("reference_id"),
                "reference_digest": sanitized_content_reference.get(
                    "reference_digest"
                ),
                "candidate_id": sanitized_content_reference.get("candidate_id"),
                "candidate_digest": sanitized_content_reference.get(
                    "candidate_digest"
                ),
                "bounded_content_digest": sanitized_content_reference.get(
                    "excerpt_digest"
                ),
                "bounded_content_char_count": sanitized_content_reference.get(
                    "bounded_character_count"
                ),
            },
            "evidence_ledger_custody_ref": source_projection.get(
                "evidence_ledger_custody_ref"
            ),
            "evidence_ledger_custody_count": custody.get("custody_record_count", 0),
            "evidence_ledger_readable_custody_count": custody.get(
                "readable_record_count",
                0,
            ),
        }
    )


def _candidate_packet_ref(
    fetch_read_content_packet: Mapping[str, Any],
    sanitized_content_reference: Mapping[str, Any],
) -> dict[str, Any]:
    return _without_empty(
        {
            "packet_id": sanitized_content_reference.get(
                "search_result_candidate_packet_id"
            ),
            "packet_digest": sanitized_content_reference.get(
                "search_result_candidate_packet_digest"
            ),
            "candidate_id": sanitized_content_reference.get("candidate_id"),
            "candidate_digest": sanitized_content_reference.get("candidate_digest"),
            "reference_count": fetch_read_content_packet.get("reference_count"),
        }
    )


def _base_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
        "phase": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE,
        "mode": ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_MODE,
        "repair_verdict_target": "YES",
        "enabled": True,
        "ran": False,
        "failed_closed": False,
        "first_failed_seam": None,
        "status": "not_run",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "ordinary_entrypoint": "core.pipeline_orchestrator.run_pipeline",
        "product_path_affected": "ordinary run_pipeline",
        "default_disabled": True,
        "user_style_demonstration_input": _DEMONSTRATION_INPUT,
        "main_run_kernel_consumed": True,
        "child_kernel_used": False,
        "child_acquisition_only": False,
        "retrieval_diagnostics_used_as_authority": False,
        "projection_to_runkernel_rehydration": False,
        "direct_runkernel_mutation": False,
        "product_code_imports_scripts_ag": False,
        **_zero_call_counts(),
        **_closed_surface_counts(),
        **_CLOSED_FALSE_FLAGS,
    }


def _success_projection(
    *,
    base: Mapping[str, Any],
    counts: Mapping[str, int],
    source_refs: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    bridge_result: SemanticObservationAdmissionBridgeResult,
    coverage_projection: Mapping[str, Any],
    run_kernel: RunKernel,
) -> dict[str, Any]:
    analysis_ref = evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
    semantic_ref = _semantic_ref(bridge_result)
    coverage_ref = _coverage_ref(coverage_projection)
    exact_match = _coverage_matches_component(
        coverage_projection=coverage_projection,
        component_ref=component_ref,
    )
    return _without_empty(
        {
            **dict(base),
            "ran": True,
            "failed_closed": False,
            "status": "main_runkernel_semantic_observation_and_component_coverage_reduced",
            "first_failed_seam": None,
            **dict(source_refs),
            **dict(counts),
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "semantic_observation_authority_owner": "main_run_kernel",
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_authority_owner": "main_run_kernel",
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get(
                "coverage_record_digest"
            ),
            "component_coverage_ref": coverage_ref,
            "main_accepted_answer_component_exists": bool(component_ref),
            "main_accepted_answer_component_ref": _accepted_component_ref(
                component_ref,
                run_kernel,
            ),
            "main_semantic_observation_admitted_count": len(
                run_kernel.state.semantic_observation_admission_history
            ),
            "main_component_coverage_reduced_count": len(
                run_kernel.state.component_coverage_history
            ),
            "exact_component_id_revision_digest_match_with_main_contract": (
                exact_match
            ),
            "legacy_365_blocker_resolved": exact_match,
            "legacy_readiness_blocker": None,
            "readiness_blocker_if_any": None,
            "structural_readiness_input_compatibility": exact_match,
            "readiness_input_compatibility_status": (
                _READINESS_COMPATIBILITY_STATUS if exact_match else "not_met"
            ),
            "main_answer_component_binding_missing": False,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            "forbidden_substitute_outputs_ruled_out": list(
                _FORBIDDEN_SUBSTITUTES
            ),
            "explicit_non_proofs": list(_NON_PROOFS),
            "next_product_path_checkpoint": _NEXT_PRODUCT_CHECKPOINT,
        }
    )


def _fail_projection(
    base: Mapping[str, Any],
    first_failed_seam: str,
    reason: str,
    *,
    counts: Mapping[str, int],
    source_refs: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    run_kernel: RunKernel | None,
    analysis_packet: Mapping[str, Any] | None,
    bridge_result: SemanticObservationAdmissionBridgeResult | None,
    coverage_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    analysis_ref = evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
    semantic_ref = _semantic_ref(bridge_result)
    coverage_ref = _coverage_ref(coverage_projection)
    exact_match = (
        _coverage_matches_component(
            coverage_projection=coverage_projection,
            component_ref=component_ref,
        )
        if component_ref and coverage_projection
        else False
    )
    return _without_empty(
        {
            **dict(base),
            "ran": False,
            "failed_closed": True,
            "status": "failed_closed",
            "first_failed_seam": first_failed_seam,
            "failure_reason": _clean_text(reason, limit=420),
            **dict(source_refs),
            **dict(counts),
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "semantic_observation_authority_owner": "main_run_kernel",
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_authority_owner": "main_run_kernel",
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get(
                "coverage_record_digest"
            ),
            "component_coverage_ref": coverage_ref,
            "main_accepted_answer_component_exists": bool(component_ref),
            "main_accepted_answer_component_ref": (
                _accepted_component_ref(component_ref, run_kernel)
                if run_kernel is not None
                else {}
            ),
            "main_semantic_observation_admitted_count": (
                len(run_kernel.state.semantic_observation_admission_history)
                if run_kernel is not None
                else 0
            ),
            "main_component_coverage_reduced_count": (
                len(run_kernel.state.component_coverage_history)
                if run_kernel is not None
                else 0
            ),
            "exact_component_id_revision_digest_match_with_main_contract": (
                exact_match
            ),
            "legacy_365_blocker_resolved": exact_match,
            "structural_readiness_input_compatibility": exact_match,
            "readiness_input_compatibility_status": "failed_closed",
            "main_answer_component_binding_missing": not bool(component_ref),
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            "forbidden_substitute_outputs_ruled_out": list(
                _FORBIDDEN_SUBSTITUTES
            ),
            "explicit_non_proofs": list(_NON_PROOFS),
            "next_product_path_checkpoint": _NEXT_PRODUCT_CHECKPOINT,
        }
    )


def _accepted_component_ref(
    component_ref: Mapping[str, Any],
    run_kernel: RunKernel | None,
) -> dict[str, Any]:
    accepted = _safe_mapping(
        run_kernel.state.initial_answer_contract if run_kernel is not None else {}
    )
    return _without_empty(
        {
            "component_id": component_ref.get("component_id"),
            "component_revision": component_ref.get("component_revision"),
            "component_digest": component_ref.get("component_digest"),
            "accepted_contract_version": accepted.get("accepted_contract_version"),
            "accepted_contract_digest": accepted.get("accepted_contract_digest"),
        }
    )


def _semantic_ref(
    result: SemanticObservationAdmissionBridgeResult | None,
) -> dict[str, Any]:
    if result is None:
        return {}
    observation = result.semantic_observation
    return {
        "observation_id": observation.observation_id,
        "observation_digest": observation.observation_digest,
        "answer_component_id": observation.answer_component_id,
        "component_revision": observation.component_revision,
        "component_digest": observation.component_contract_digest,
        "content_ref_ids": list(observation.content_refs),
        "evidence_ref_ids": list(observation.evidence_refs),
    }


def _coverage_ref(coverage_projection: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(coverage_projection)
    if not safe:
        return {}
    return _without_empty(
        {
            "coverage_record_id": safe.get("coverage_record_id"),
            "coverage_record_digest": safe.get("coverage_record_digest"),
            "coverage_reduction_digest": safe.get("coverage_reduction_digest"),
            "answer_component_id": safe.get("answer_component_id"),
            "component_revision": safe.get("component_revision"),
            "component_digest": safe.get("component_digest"),
            "coverage_state": safe.get("coverage_state"),
            "semantic_support_status": safe.get("semantic_support_status"),
            "source_obligation_status": safe.get("source_obligation_status"),
        }
    )


def _component_match(component_ref: Mapping[str, Any], observation: Any) -> bool:
    return (
        component_ref.get("component_id") == observation.answer_component_id
        and component_ref.get("component_revision") == observation.component_revision
        and component_ref.get("component_digest")
        == observation.component_contract_digest
    )


def _coverage_matches_component(
    *,
    coverage_projection: Mapping[str, Any] | None,
    component_ref: Mapping[str, Any],
) -> bool:
    safe = _safe_mapping(coverage_projection)
    return (
        bool(safe)
        and safe.get("answer_component_id") == component_ref.get("component_id")
        and safe.get("component_revision")
        == component_ref.get("component_revision")
        and safe.get("component_digest") == component_ref.get("component_digest")
    )


def _known_exception_seam(
    exc: Exception,
    *,
    analysis_built: int,
    semantic_admitted: int,
    coverage_attempted: int,
) -> str:
    if isinstance(exc, EvidenceRelativeAnalysisPacketError) or analysis_built == 0:
        return "evidence_relative_analysis_packet_rejected"
    if (
        isinstance(exc, SemanticObservationAdmissionBridgeError)
        or semantic_admitted == 0
    ):
        return "semantic_observation_admission_rejected"
    if coverage_attempted > 0:
        return "component_coverage_reduction_rejected"
    return "ordinary_live_main_runkernel_coverage_rejected"


def _assert_safe_projection(projection: Mapping[str, Any]) -> None:
    forbidden = sorted(_collect_keys(projection) & _FORBIDDEN_TRACE_KEYS)
    if forbidden:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "ordinary_live_main_runkernel_coverage_projection_unsafe",
            "ordinary main RunKernel coverage projection includes forbidden fields: "
            + ", ".join(forbidden),
        )


def _reject_diagnostic_authority_keys(value: Any, *, context: str) -> None:
    diagnostic = sorted(_collect_keys(value) & _DIAGNOSTIC_AUTHORITY_KEYS)
    if diagnostic:
        raise OrdinaryLiveMainRunKernelCoverageError(
            "diagnostic_main_runkernel_coverage_authority_rejected",
            f"{context} includes diagnostic-shaped authority fields: "
            + ", ".join(diagnostic),
        )


def _zero_call_counts() -> dict[str, int]:
    return {
        "provider_search_calls": 0,
        "search_calls": 0,
        "broker_calls": 0,
        "fetch_read_calls": 0,
        "model_calls": 0,
        "retrieval_calls": 0,
    }


def _closed_surface_counts() -> dict[str, int]:
    return {
        "source_obligation_satisfaction_decisions": 0,
        "citation_eligibility_decisions": 0,
        "citation_rendering_decisions": 0,
        "sufficiency_readiness_reductions": 0,
        "final_answer_packet_creations": 0,
        "author_authorprose_invocations": 0,
        "answer_text_creations": 0,
        "product_correctness_claims": 0,
    }


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


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


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


__all__ = [
    "ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_MODE",
    "ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_PHASE",
    "ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY",
    "OrdinaryLiveMainRunKernelCoverageResult",
    "execute_ordinary_live_main_runkernel_coverage",
    "ordinary_live_main_runkernel_coverage_disabled_projection",
]
