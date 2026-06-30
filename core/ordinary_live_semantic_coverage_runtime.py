"""Default-off ordinary run_pipeline semantic coverage integration.

This helper consumes the in-memory ordinary source-custody result from
``ordinary_live_source_custody_runtime`` and reduces at most one
SemanticObservation plus at most one ComponentCoverage record through existing
RunKernel authority. It performs no provider, broker, search, retrieval,
fetch/read, model, citation, Sufficiency, FAP, Author, answer, or product
correctness work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

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

ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY = "ordinary_live_semantic_coverage"
ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE = (
    "AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01"
)
ORDINARY_LIVE_SEMANTIC_COVERAGE_MODE = "REPAIR"

_CHILD_OWNER = "ordinary_live_candidate_handoff_run_kernel"
_CHILD_LIFETIME = "in_memory_for_single_run_pipeline_invocation"
_CHILD_STATE_OWNED = (
    "SearchPlanner/current_answer_contract/SearchExecutorHandoff",
    "live_search_validation_state",
    "SearchResultCandidatePacket lineage",
    "FetchReadContentPacket/SanitizedContentReference custody lineage",
    "EvidenceLedger candidate/content custody for the selected candidate",
    "EvidenceRelativeAnalysisPacket lineage",
    "SemanticObservation admission",
    "ComponentCoverage reduction",
)
_CHILD_STATE_NOT_OWNED = (
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "citation rendering",
    "source-obligation satisfaction",
    "answer text",
    "product correctness",
)
_MAIN_KERNEL_LIMITATION = (
    "The main answer RunKernel does not yet own this source-custody component "
    "as an ordinary readiness/FAP component, so semantic coverage remains on "
    "the bounded child kernel for this repair."
)
_FUTURE_CONSOLIDATION = (
    "Temporary architecture debt: consolidate candidate handoff, source custody, "
    "SemanticObservation admission, and ComponentCoverage onto the main ordinary "
    "RunKernel in AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-"
    "PRECONDITION-01 before readiness/FAP/AuthorProse."
)
_READINESS_BLOCKER = "coverage_not_bound_to_main_answer_readiness_component"

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
    "coverage_is_final_answer_component_support": False,
    "readiness_build_precondition_met": False,
    "retrieval_diagnostics_used_as_semantic_authority": False,
    "projection_to_runkernel_rehydration": False,
    "direct_runkernel_mutation": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "citation_rendered": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "answer_text_created": False,
    "product_correctness_claimed": False,
}
_NON_PROOFS = (
    "no live provider/search/broker/fetch/model call",
    "no retrieval diagnostics promoted into semantic authority",
    "no projection-to-RunKernel rehydration",
    "no direct RunKernel state mutation",
    "no source-obligation satisfaction",
    "no citation eligibility or citation rendering",
    "no SufficiencyReadiness",
    "no FinalAnswerPacket",
    "no Author or AuthorProse behavior",
    "no answer text or product correctness claim",
    "child-component coverage is not final-answer readiness coverage",
)


class OrdinaryLiveSemanticCoverageError(ValueError):
    """Raised internally when ordinary semantic coverage must fail closed."""

    def __init__(self, first_failed_seam: str, message: str) -> None:
        super().__init__(message)
        self.first_failed_seam = first_failed_seam


@dataclass(frozen=True, slots=True)
class OrdinaryLiveSemanticCoverageResult:
    projection: dict[str, Any]
    evidence_relative_analysis_packet: dict[str, Any] | None = None
    semantic_observation_admission_result: (
        SemanticObservationAdmissionBridgeResult | None
    ) = None
    component_coverage_projection: dict[str, Any] | None = None


def ordinary_live_semantic_coverage_disabled_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
        "phase": ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE,
        "mode": ORDINARY_LIVE_SEMANTIC_COVERAGE_MODE,
        "enabled": False,
        "ran": False,
        "failed_closed": False,
        "status": "disabled",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
    }


def execute_ordinary_live_semantic_coverage(
    *,
    run_kernel: RunKernel | None,
    parent_run_id: str,
    parent_request_id: str,
    source_custody_result: Any | None,
) -> OrdinaryLiveSemanticCoverageResult:
    """Reduce one ordinary source-custody result into semantic coverage."""

    base = _base_projection(
        parent_run_id=parent_run_id,
        parent_request_id=parent_request_id,
    )
    analysis_attempted = 0
    analysis_built = 0
    semantic_attempted = 0
    semantic_admitted = 0
    coverage_attempted = 0
    coverage_reduced = 0
    analysis_packet: dict[str, Any] | None = None
    bridge_result: SemanticObservationAdmissionBridgeResult | None = None
    coverage_projection: dict[str, Any] | None = None
    source_refs: dict[str, Any] = {}
    component_ref: dict[str, Any] = {}

    try:
        if source_custody_result is None:
            raise OrdinaryLiveSemanticCoverageError(
                "ordinary_live_source_custody_result_missing",
                "ordinary semantic coverage requires the in-memory source custody result",
            )
        if isinstance(source_custody_result, Mapping):
            _reject_diagnostic_authority_keys(
                source_custody_result,
                context="ordinary semantic coverage source_custody_result",
            )
            raise OrdinaryLiveSemanticCoverageError(
                "ordinary_live_source_custody_result_object_missing",
                "ordinary semantic coverage requires the source custody result object, "
                "not a projection mapping",
            )
        if run_kernel is None:
            raise OrdinaryLiveSemanticCoverageError(
                "ordinary_candidate_handoff_run_kernel_missing",
                "ordinary semantic coverage requires the in-memory candidate RunKernel",
            )

        source_projection = _safe_mapping(
            getattr(source_custody_result, "projection", None)
        )
        if source_projection.get("failed_closed") is True:
            raise OrdinaryLiveSemanticCoverageError(
                "ordinary_live_source_custody_failed_closed",
                "ordinary semantic coverage requires successful source custody",
            )
        _reject_diagnostic_authority_keys(
            source_projection,
            context="ordinary source custody projection",
        )
        fetch_read_content_packet = _safe_mapping(
            getattr(source_custody_result, "fetch_read_content_packet", None)
        )
        sanitized_content_reference = _safe_mapping(
            getattr(source_custody_result, "sanitized_content_reference", None)
        )
        evidence_ledger_projection = _safe_mapping(
            getattr(source_custody_result, "evidence_ledger_projection", None)
        )
        if not fetch_read_content_packet:
            raise OrdinaryLiveSemanticCoverageError(
                "fetch_read_content_packet_missing",
                "ordinary semantic coverage requires FetchReadContentPacket",
            )
        if not sanitized_content_reference:
            raise OrdinaryLiveSemanticCoverageError(
                "sanitized_content_reference_missing",
                "ordinary semantic coverage requires SanitizedContentReference",
            )
        if not evidence_ledger_projection:
            raise OrdinaryLiveSemanticCoverageError(
                "evidence_ledger_projection_missing",
                "ordinary semantic coverage requires EvidenceLedger custody projection",
            )
        source_refs = _source_input_refs(
            source_projection=source_projection,
            fetch_read_content_packet=fetch_read_content_packet,
            sanitized_content_reference=sanitized_content_reference,
            evidence_ledger_projection=evidence_ledger_projection,
        )

        proposal = _source_bound_support_proposal(
            run_kernel=run_kernel,
            sanitized_content_reference=sanitized_content_reference,
            evidence_ledger_projection=evidence_ledger_projection,
        )
        analysis_attempted = 1
        analysis_packet = build_evidence_relative_analysis_packet(
            evidence_ledger_projection=evidence_ledger_projection,
            analyst_proposal_records=[proposal],
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            current_answer_contract_ref=sanitized_content_reference.get(
                "current_answer_contract_ref"
            ),
            current_answer_contract_digest=sanitized_content_reference.get(
                "current_answer_contract_digest"
            ),
        )
        analysis_built = 1

        findings = _safe_list(
            _safe_mapping(analysis_packet.get("analyst_report")).get("findings")
        )
        if len(findings) != 1:
            raise OrdinaryLiveSemanticCoverageError(
                "evidence_relative_analysis_packet_finding_count_invalid",
                "ordinary semantic coverage expects exactly one support finding",
            )
        semantic_attempted = 1
        admitted = admit_semantic_observations_from_analysis_support_findings(
            run_kernel=run_kernel,
            evidence_relative_analysis_packet=analysis_packet,
            fetch_read_content_packet=fetch_read_content_packet,
            finding_ids=(str(findings[0]["finding_id"]),),
        )
        if len(admitted) != 1:
            raise OrdinaryLiveSemanticCoverageError(
                "semantic_observation_admission_count_invalid",
                "ordinary semantic coverage expects exactly one admission",
            )
        bridge_result = admitted[0]
        semantic_admitted = 1
        component_ref = _component_ref(
            run_kernel,
            bridge_result.semantic_observation.answer_component_id,
        )

        coverage_attempted = 1
        coverage_projection = _reduce_component_coverage(
            run_kernel=run_kernel,
            admission_result=bridge_result,
        )
        coverage_reduced = 1

        projection = _success_projection(
            base=base,
            source_refs=source_refs,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
            component_ref=component_ref,
            run_kernel=run_kernel,
            analysis_attempted=analysis_attempted,
            analysis_built=analysis_built,
            semantic_attempted=semantic_attempted,
            semantic_admitted=semantic_admitted,
            coverage_attempted=coverage_attempted,
            coverage_reduced=coverage_reduced,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveSemanticCoverageResult(
            projection=projection,
            evidence_relative_analysis_packet=analysis_packet,
            semantic_observation_admission_result=bridge_result,
            component_coverage_projection=coverage_projection,
        )
    except OrdinaryLiveSemanticCoverageError as exc:
        projection = _fail_projection(
            base,
            exc.first_failed_seam,
            str(exc),
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=run_kernel,
            analysis_attempted=analysis_attempted,
            analysis_built=analysis_built,
            semantic_attempted=semantic_attempted,
            semantic_admitted=semantic_admitted,
            coverage_attempted=coverage_attempted,
            coverage_reduced=coverage_reduced,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveSemanticCoverageResult(projection=projection)
    except (
        EvidenceRelativeAnalysisPacketError,
        SemanticObservationAdmissionBridgeError,
        RunKernelTransitionError,
        ValueError,
    ) as exc:
        seam = _known_exception_seam(
            exc,
            analysis_built=analysis_built,
            semantic_admitted=semantic_admitted,
            coverage_attempted=coverage_attempted,
        )
        projection = _fail_projection(
            base,
            seam,
            str(exc),
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=run_kernel,
            analysis_attempted=analysis_attempted,
            analysis_built=analysis_built,
            semantic_attempted=semantic_attempted,
            semantic_admitted=semantic_admitted,
            coverage_attempted=coverage_attempted,
            coverage_reduced=coverage_reduced,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveSemanticCoverageResult(projection=projection)
    except Exception as exc:
        projection = _fail_projection(
            base,
            "ordinary_live_semantic_coverage_exception",
            str(exc),
            source_refs=source_refs,
            component_ref=component_ref,
            run_kernel=run_kernel,
            analysis_attempted=analysis_attempted,
            analysis_built=analysis_built,
            semantic_attempted=semantic_attempted,
            semantic_admitted=semantic_admitted,
            coverage_attempted=coverage_attempted,
            coverage_reduced=coverage_reduced,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveSemanticCoverageResult(projection=projection)


def _source_bound_support_proposal(
    *,
    run_kernel: RunKernel,
    sanitized_content_reference: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    if sanitized_content_reference.get("fetch_read_status") != "readable":
        raise OrdinaryLiveSemanticCoverageError(
            "source_custody_content_not_readable",
            "ordinary semantic coverage requires readable source-custody content",
        )
    if sanitized_content_reference.get("bounded_text_sanitized") is not True:
        raise OrdinaryLiveSemanticCoverageError(
            "source_custody_content_not_sanitized",
            "ordinary semantic coverage requires sanitized bounded content",
        )
    if sanitized_content_reference.get("bounded_text_bounded") is not True:
        raise OrdinaryLiveSemanticCoverageError(
            "source_custody_content_not_bounded",
            "ordinary semantic coverage requires explicitly bounded content",
        )
    if not _clean_text(sanitized_content_reference.get("bounded_text"), limit=20_000):
        raise OrdinaryLiveSemanticCoverageError(
            "source_custody_content_empty",
            "ordinary semantic coverage requires non-empty bounded source content",
        )
    selection = _safe_mapping(sanitized_content_reference.get("bounded_text_selection"))
    required_count = _bounded_int(selection.get("required_anchor_count"))
    matched_count = _bounded_int(selection.get("matched_anchor_count"))
    missing_anchors = _safe_list(selection.get("missing_anchors"))
    if required_count > 0 and (missing_anchors or matched_count < required_count):
        raise OrdinaryLiveSemanticCoverageError(
            "source_custody_anchor_precondition_unmet",
            "ordinary semantic coverage requires the source-custody bounded "
            "selection to satisfy configured anchors",
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
            raise OrdinaryLiveSemanticCoverageError(
                "source_custody_reference_mismatch",
                f"ordinary semantic coverage source-custody {key} mismatch",
            )
    for record_key, reference_key in (
        ("fetch_read_content_packet_id", "packet_id"),
        ("fetch_read_content_packet_digest", "packet_digest"),
    ):
        if _clean_text(record.get(record_key), limit=320) != _clean_text(
            sanitized_content_reference.get(reference_key),
            limit=320,
        ):
            raise OrdinaryLiveSemanticCoverageError(
                "source_custody_reference_mismatch",
                f"ordinary semantic coverage source-custody {record_key} mismatch",
            )
    component_id = _clean_text(record.get("component_id"), limit=260) or _first_component_id(
        run_kernel
    )
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
        "component_id": component_id,
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "proposal_summary": (
            "Bounded ordinary source-custody content supports the child "
            "candidate/source-custody component only."
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
            "coverage:ordinary-live-semantic:"
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
            "coverage is bound to the bounded child candidate/source-custody component",
            "source-obligation candidate ids remain lineage only",
        ),
        required_caveats=(
            "Do not upgrade child-component coverage to final-answer readiness.",
            "Do not upgrade semantic support to source-obligation satisfaction.",
        ),
        prohibited_upgrades=(
            "Do not create Sufficiency, FAP, Author, citation, answer, or "
            "product-correctness claims.",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        lineage=CoverageLineage(
            created_by=ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE,
            created_from=(
                "ordinary_live_source_custody_result",
                "evidence_relative_analysis_packet",
                "admitted_semantic_observation",
            ),
        ),
        metadata={
            "phase": ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE,
            "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
            "coverage_is_final_answer_component_support": False,
            "readiness_blocker": _READINESS_BLOCKER,
        },
    ).require_valid()
    action = run_kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={"phase": ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE},
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
    raise OrdinaryLiveSemanticCoverageError(
        "coverage_component_missing_from_accepted_contract",
        "ordinary semantic coverage component is missing from the accepted contract",
    )


def _first_component_id(run_kernel: RunKernel) -> str:
    refs = run_kernel.state.initial_answer_contract.get(
        "accepted_answer_component_refs",
        [],
    )
    for ref in refs:
        if isinstance(ref, Mapping) and ref.get("component_id"):
            return str(ref["component_id"])
    raise OrdinaryLiveSemanticCoverageError(
        "coverage_component_missing_from_accepted_contract",
        "ordinary semantic coverage requires an accepted answer component",
    )


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
                raise OrdinaryLiveSemanticCoverageError(
                    "source_custody_record_not_readable",
                    "ordinary semantic coverage requires readable EvidenceLedger custody",
                )
            return record
    raise OrdinaryLiveSemanticCoverageError(
        "source_custody_record_missing",
        "ordinary semantic coverage requires matching EvidenceLedger custody",
    )


def _source_input_refs(
    *,
    source_projection: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    sanitized_content_reference: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    return _without_empty(
        {
            "source_custody_result_object_consumed": True,
            "source_custody_projection_only_consumed": False,
            "source_came_from_ordinary_source_custody": True,
            "source_custody_status": source_projection.get("status"),
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
            "evidence_ledger_custody_count": custody.get(
                "custody_record_count",
                0,
            ),
            "evidence_ledger_readable_custody_count": custody.get(
                "readable_record_count",
                0,
            ),
        }
    )


def _base_projection(*, parent_run_id: str, parent_request_id: str) -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
        "phase": ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE,
        "mode": ORDINARY_LIVE_SEMANTIC_COVERAGE_MODE,
        "repair_verdict_target": "YES",
        "enabled": True,
        "ran": False,
        "failed_closed": False,
        "first_failed_seam": None,
        "status": "not_run",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "product_path_affected": "ordinary run_pipeline",
        "default_disabled": True,
        "parent_run_id": parent_run_id,
        "parent_request_id": parent_request_id,
        "source_came_from_ordinary_source_custody": False,
        "retrieval_diagnostics_used_as_semantic_authority": False,
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
    source_refs: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    bridge_result: SemanticObservationAdmissionBridgeResult,
    coverage_projection: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    run_kernel: RunKernel,
    analysis_attempted: int,
    analysis_built: int,
    semantic_attempted: int,
    semantic_admitted: int,
    coverage_attempted: int,
    coverage_reduced: int,
) -> dict[str, Any]:
    analysis_ref = evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
    semantic_ref = _semantic_ref(bridge_result)
    coverage_ref = _coverage_ref(coverage_projection)
    return _without_empty(
        {
            **dict(base),
            "ran": True,
            "failed_closed": False,
            "status": "semantic_observation_and_component_coverage_reduced",
            "first_failed_seam": None,
            **dict(source_refs),
            "evidence_relative_analysis_packet_attempted_count": analysis_attempted,
            "evidence_relative_analysis_packet_built_count": analysis_built,
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "semantic_observation_attempted_count": semantic_attempted,
            "semantic_observation_admitted_count": semantic_admitted,
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_attempted_count": coverage_attempted,
            "component_coverage_reduced_count": coverage_reduced,
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get(
                "coverage_record_digest"
            ),
            "component_coverage_ref": coverage_ref,
            **_coverage_component_projection(component_ref),
            **_readiness_projection(),
            **_child_kernel_projection(run_kernel=run_kernel),
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            "explicit_non_proofs": list(_NON_PROOFS),
        }
    )


def _fail_projection(
    base: Mapping[str, Any],
    first_failed_seam: str,
    reason: str,
    *,
    source_refs: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    run_kernel: RunKernel | None,
    analysis_attempted: int,
    analysis_built: int,
    semantic_attempted: int,
    semantic_admitted: int,
    coverage_attempted: int,
    coverage_reduced: int,
    analysis_packet: Mapping[str, Any] | None,
    bridge_result: SemanticObservationAdmissionBridgeResult | None,
    coverage_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    analysis_ref = evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
    semantic_ref = _semantic_ref(bridge_result)
    coverage_ref = _coverage_ref(coverage_projection)
    return _without_empty(
        {
            **dict(base),
            "ran": False,
            "failed_closed": True,
            "status": "failed_closed",
            "first_failed_seam": first_failed_seam,
            "failure_reason": _clean_text(reason, limit=420),
            **dict(source_refs),
            "evidence_relative_analysis_packet_attempted_count": analysis_attempted,
            "evidence_relative_analysis_packet_built_count": analysis_built,
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "semantic_observation_attempted_count": semantic_attempted,
            "semantic_observation_admitted_count": semantic_admitted,
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_attempted_count": coverage_attempted,
            "component_coverage_reduced_count": coverage_reduced,
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get(
                "coverage_record_digest"
            ),
            "component_coverage_ref": coverage_ref,
            **_coverage_component_projection(component_ref),
            **_readiness_projection(),
            **_child_kernel_projection(run_kernel=run_kernel),
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            "explicit_non_proofs": list(_NON_PROOFS),
        }
    )


def _coverage_component_projection(component_ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "coverage_component_id": component_ref.get("component_id"),
        "coverage_component_digest": component_ref.get("component_digest"),
        "coverage_component_contract_kind": (
            "bounded_child_candidate_source_custody_component"
        ),
    }


def _readiness_projection() -> dict[str, Any]:
    return {
        "coverage_is_final_answer_component_support": False,
        "readiness_build_precondition_met": False,
        "readiness_blocker_if_any": _READINESS_BLOCKER,
    }


def _child_kernel_projection(*, run_kernel: RunKernel | None) -> dict[str, Any]:
    base = {
        "child_kernel_owner": _CHILD_OWNER,
        "child_kernel_lifetime": _CHILD_LIFETIME,
        "child_kernel_state_owned": list(_CHILD_STATE_OWNED),
        "child_kernel_state_not_owned": list(_CHILD_STATE_NOT_OWNED),
        "child_kernel_main_kernel_limitation": _MAIN_KERNEL_LIMITATION,
        "child_kernel_temporary_architecture_debt": True,
        "child_kernel_future_consolidation_path": _FUTURE_CONSOLIDATION,
    }
    if run_kernel is None:
        return {"child_kernel_used": False, **base}
    return {
        "child_kernel_used": True,
        **base,
        "child_kernel_parent_lineage": {
            "parent_run_id": str(run_kernel.state.request.get("parent_run_id") or ""),
            "parent_request_id": str(
                run_kernel.state.request.get("parent_request_id") or ""
            ),
            "child_run_id": run_kernel.state.run_id,
            "child_request_id": run_kernel.state.request_id,
        },
    }


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
    return "ordinary_live_semantic_coverage_rejected"


def _reject_diagnostic_authority_keys(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    diagnostic = sorted(keys & _DIAGNOSTIC_AUTHORITY_KEYS)
    if diagnostic:
        raise OrdinaryLiveSemanticCoverageError(
            "diagnostic_semantic_authority_rejected",
            f"{context} includes diagnostic-shaped semantic authority fields: "
            + ", ".join(diagnostic),
        )


def _assert_safe_projection(projection: Mapping[str, Any]) -> None:
    forbidden = sorted(_collect_keys(projection) & _FORBIDDEN_TRACE_KEYS)
    if forbidden:
        raise OrdinaryLiveSemanticCoverageError(
            "ordinary_live_semantic_coverage_projection_unsafe",
            "ordinary semantic coverage projection includes forbidden fields: "
            + ", ".join(forbidden),
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
    "ORDINARY_LIVE_SEMANTIC_COVERAGE_MODE",
    "ORDINARY_LIVE_SEMANTIC_COVERAGE_PHASE",
    "ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY",
    "OrdinaryLiveSemanticCoverageResult",
    "execute_ordinary_live_semantic_coverage",
    "ordinary_live_semantic_coverage_disabled_projection",
]
