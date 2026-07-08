"""Product-facing semantic support/component coverage status.

This module backs a default-off ordinary CLI status path. It consumes the
retained live acquisition/readability, source/evidence custody, and
citation/source-obligation readiness status chain, then reports whether the
current SemanticObservation + ComponentCoverage lane can be product-consumed.

It performs no live calls. The path may create a bounded Analyst
``possible_support_proposal`` only when a valid current-path support signal
exists; it must not infer support from URL/domain/snippet/custody/lineage or
ad hoc text matching.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.analyst_workbench_runtime import workbench_dprime_dossier_ref
from core.current_source_component_answer_type_binding import (
    maybe_current_source_component_answer_type_binding_ref,
)
from core.dprime_analyst_finding_support_validation import (
    analyst_finding_support_validation_required,
    build_dprime_analyst_finding_support_validation,
    dprime_analyst_finding_support_validation_ref,
    support_validation_allows_runkernel_admission,
)
from core.dprime_analyst_relation_intake_runtime import (
    DPrimeAnalystRelationIntakeError,
    build_dprime_analyst_relation_intake,
    component_ref_from_relation_intake,
    relation_intake_ref,
    source_obligation_ref_from_relation_intake,
)
from core.dprime_evidence_frame_preflight import build_evidence_frame_preflight
from core.dprime_evidence_support_bundle_runtime import (
    BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING,
    BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING,
    BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED,
    DPrimeEvidenceSupportBundleError,
    build_dprime_evidence_support_bundle,
)
from core.dprime_model_review_assessment import run_dprime_model_review_assessment
from core.dprime_multi_source_analyst_scrutiny_runtime import (
    BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
    BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
    DPrimeMultiSourceAnalystScrutinyError,
    build_dprime_multi_source_relation_set,
    build_dprime_multi_source_support_posture,
    build_dprime_scrutineer_challenge_gate,
)
from core.dprime_ordinary_contract_authority_runtime import (
    DPrimeOrdinaryContractAuthorityError,
    build_dprime_ordinary_contract_authority,
)
from core.dprime_product_smart_one_shot_transport import (
    product_smart_model_route_ref,
)
from core.dprime_runkernel_admission_runtime import (
    BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED,
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    build_run_kernel_dprime_admission_decision,
)
from core.dprime_semantic_observation_materialization_runtime import (
    BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED,
    BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT,
    DPrimeSemanticObservationMaterializationError,
    materialize_dprime_semantic_observation_from_admitted_decision,
)
from core.dprime_single_lane_answer_path_runtime import (
    DPrimeSingleLaneAnswerPathError,
    build_dprime_single_lane_answer_path,
)
from core.dprime_support_proposal_schema import (
    BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED,
    BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED,
    BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING,
    BLOCKED_DPRIME_PREFLIGHT_FAILED,
    BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING,
    DPRIME_PHASE,
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
    DPrimeStatusPayload,
    build_dprime_status_payload,
)
from core.retained_custody_analyst_support_proposal import (
    RetainedCustodyAnalystSupportProposalError,
    RetainedCustodySemanticCoverageResult,
    build_retained_custody_semantic_coverage,
)
from core.run_config import RunConfig
from core.runkernel_followup_search_reentry_ordinary_search_runtime import (
    run_dprime_followup_search_reentry_using_ordinary_search,
)
from proplex.live_citation_source_obligation_readiness_status import (
    PASS_DECISION,
    build_live_citation_source_obligation_readiness_status,
)
from proplex.live_source_evidence_admission_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
)

PHASE = DPRIME_PHASE
MODE = "BUILD"
USABLE_ANSWER_VERDICT_TARGET = "YES"
LIVE_SEMANTIC_COVERAGE_STATUS_FLAG = "--live-semantic-coverage-status-dry-run"

BLOCKED_ENTRYPOINT_MISSING = "BLOCKED_ENTRYPOINT_MISSING"
BLOCKED_RETAINED_ARTIFACT_PREFLIGHT = "BLOCKED_RETAINED_ARTIFACT_PREFLIGHT"
BLOCKED_FETCH_READ_ARTIFACT_MISSING = "BLOCKED_FETCH_READ_ARTIFACT_MISSING"
BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE = "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE"
BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE = "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE"
BLOCKED_FETCH_READ_ARTIFACT_LINEAGE = "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE"
BLOCKED_SOURCE_EVIDENCE_STATUS = "BLOCKED_SOURCE_EVIDENCE_STATUS"
BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS = (
    "BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS"
)
BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING = (
    "BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING"
)
BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING = (
    "BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING"
)
BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER = (
    "BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER"
)
BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING = (
    "BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING"
)
BLOCKED_SEMANTIC_OBSERVATION_ADMISSION = (
    "BLOCKED_SEMANTIC_OBSERVATION_ADMISSION"
)
BLOCKED_SEMANTIC_SUPPORT_INSUFFICIENT = "BLOCKED_SEMANTIC_SUPPORT_INSUFFICIENT"
BLOCKED_COMPONENT_COVERAGE_BINDING = "BLOCKED_COMPONENT_COVERAGE_BINDING"
BLOCKED_OUTPUT_HYGIENE = "BLOCKED_OUTPUT_HYGIENE"
BLOCKED_CLOSED_SURFACE_VIOLATION = "BLOCKED_CLOSED_SURFACE_VIOLATION"
BLOCKED_PRODUCT_IMPORT_BOUNDARY = "BLOCKED_PRODUCT_IMPORT_BOUNDARY"
BLOCKED_DPRIME_GENERIC_RELATION_INTAKE_MISSING = (
    "BLOCKED_DPRIME_GENERIC_RELATION_INTAKE_MISSING"
)
BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION = (
    "BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION"
)
BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH = (
    "BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH"
)
BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED = (
    "BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED"
)

SEMANTIC_COVERAGE_MACHINERY_FOUND = (
    "core.evidence_relative_analysis_packet.EvidenceRelativeAnalysisPacket / AnalystReport",
    "core.retained_custody_analyst_support_proposal.build_retained_custody_semantic_coverage",
    "core.semantic_observation_admission_bridge.admit_semantic_observations_from_analysis_support_findings",
    "core.semantic_observation_admission_runtime.build_semantic_observation_admission_state",
    "core.component_coverage_record.ComponentCoverageRecord",
    "core.component_coverage_reduction_runtime.build_component_coverage_reduction_state",
)
NEXT_BLOCKED_SURFACE = (
    "D-prime EvidenceFramePreflight"
)
CLOSED_DOWNSTREAM_SURFACES = (
    "product-quality correctness claim",
    "multi-component support aggregation",
    "full Scrutineer remediation",
    "Economist routing",
    "Specialist routing",
    "live/model/provider/search/fetch/read/retrieval calls",
    "old Author execution",
)
EXPLICIT_NON_CLAIM = (
    "This phase consumes generic D-prime relation intake through the existing "
    "single-lane answer-path status, with an optional narrow multi-source "
    "posture and Scrutineer gate for one component. It does not prove product "
    "correctness, multi-component intake, live validation, or final answer "
    "quality."
)

_READINESS_BLOCKER_MAP = {
    "BLOCKED_ENTRYPOINT_MISSING": BLOCKED_ENTRYPOINT_MISSING,
    "BLOCKED_RETAINED_ARTIFACT_PREFLIGHT": BLOCKED_RETAINED_ARTIFACT_PREFLIGHT,
    "BLOCKED_FETCH_READ_ARTIFACT_MISSING": BLOCKED_FETCH_READ_ARTIFACT_MISSING,
    "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE": BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
    "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE": BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE,
    "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE": BLOCKED_FETCH_READ_ARTIFACT_LINEAGE,
    "BLOCKED_SOURCE_EVIDENCE_STATUS": BLOCKED_SOURCE_EVIDENCE_STATUS,
    "BLOCKED_CITATION_SOURCE_OBLIGATION_CONSUMER_MISSING": (
        BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS
    ),
    "BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS": (
        BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS
    ),
    "BLOCKED_CITATION_SOURCE_OBLIGATION_RAW_PRIVATE": (
        BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE
    ),
    "BLOCKED_OUTPUT_HYGIENE": BLOCKED_OUTPUT_HYGIENE,
    "BLOCKED_CLOSED_SURFACE_VIOLATION": BLOCKED_CLOSED_SURFACE_VIOLATION,
    "BLOCKED_PRODUCT_IMPORT_BOUNDARY": BLOCKED_PRODUCT_IMPORT_BOUNDARY,
}
_OUTPUT_FORBIDDEN_TOKENS = frozenset(
    {
        "bounded_text",
        "raw_html",
        "raw page",
        "raw_page_text",
        "raw_page_content",
        "headers:",
        "cookies",
        "provider_payload",
        "search response payload",
        "model_response",
        "prompt:",
        "answer prose:",
        "author prose",
        "citation_ready",
        "citation ready",
        "finalanswerpacket",
    }
)


@dataclass(frozen=True, slots=True)
class LiveSemanticCoverageStatusResult:
    decision: str
    output: str
    payload: Mapping[str, Any]

    @property
    def return_code(self) -> int:
        return 0 if self.decision == PASS_DECISION else 2


class LiveSemanticCoverageStatusError(ValueError):
    """Raised for unexpected semantic coverage status failures."""


def build_live_semantic_coverage_status(
    *,
    query: str,
    repo_root: str | Path,
    smart_provider: str | None = None,
    smart_model: str | None = None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None = None,
    dprime_one_shot_model_review_adapter: Any | None = None,
    dprime_model_review_license: Any | None = None,
    dprime_model_review_callable: Callable[..., Any] | None = None,
    dprime_followup_search_reentry_enabled: bool = False,
    dprime_followup_candidate_results: (
        Sequence[Mapping[str, Any]] | Mapping[str, Any] | None
    ) = None,
    dprime_followup_fetch_read_materials: Sequence[Mapping[str, Any]] = (),
    dprime_followup_plan_builder: Callable[..., Mapping[str, Any]]
    | None = None,
    dprime_followup_authorized_execution_callback: Callable[..., Mapping[str, Any]]
    | None = None,
    dprime_followup_second_pass_model_review_callable: (
        Callable[..., Any] | None
    ) = None,
    dprime_multi_source_relation_inputs: Sequence[Mapping[str, Any]] = (),
    dprime_multi_source_scrutineer_enabled: bool = True,
    dprime_run_kernel_admission_decision_status: str = (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    ),
    dprime_downstream_authority_enabled: bool = True,
    dprime_source_citation_authority_enabled: bool | None = None,
    dprime_single_lane_answer_path_enabled: bool | None = None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
) -> LiveSemanticCoverageStatusResult:
    """Consume retained status chain and return CLI-safe semantic coverage status."""

    root = _resolve_root(repo_root)
    workbench_ref = workbench_dprime_dossier_ref(workbench_dprime_dossier)
    dprime_product_model_route_ref = _dprime_product_smart_model_route_ref(
        query=query,
        smart_provider=smart_provider,
        smart_model=smart_model,
    )
    readiness_status = build_live_citation_source_obligation_readiness_status(
        query=query,
        repo_root=root,
    )
    if readiness_status.decision != PASS_DECISION:
        readiness_payload = _safe_mapping(readiness_status.payload)
        if (
            dprime_followup_search_reentry_enabled
            and readiness_status.decision == BLOCKED_FETCH_READ_ARTIFACT_LINEAGE
            and _workbench_read_support_followup_required(workbench_dprime_dossier)
        ):
            try:
                fetch_read_content_packet = _read_json(
                    root / FETCH_READ_ARTIFACT_DIR / FETCH_READ_CONTENT_PACKET_NAME
                )
            except (
                FileNotFoundError,
                PermissionError,
                json.JSONDecodeError,
                OSError,
            ):
                return _blocked_from_readiness_status(
                    query=query,
                    readiness_decision=readiness_status.decision,
                )
            lineage_refs = _workbench_read_support_followup_lineage_refs(
                fetch_read_content_packet=fetch_read_content_packet,
                workbench_dprime_dossier=workbench_dprime_dossier,
            )
            if lineage_refs:
                admission_ref = _safe_mapping(lineage_refs.get("admission_ref"))
                readiness_ref = _safe_mapping(lineage_refs.get("readiness_ref"))
                component_ref = _safe_mapping(lineage_refs.get("component_ref"))
                source_obligation_ref = _safe_mapping(
                    lineage_refs.get("source_obligation_ref")
                )
                followup_result = _run_followup_search_reentry_status(
                    query=query,
                    readiness_payload={
                        **readiness_payload,
                        "source_evidence_admission_ref": admission_ref,
                        "citation_source_obligation_readiness_ref": readiness_ref,
                        "component_ref": component_ref,
                        "source_obligation_ref": source_obligation_ref,
                    },
                    fetch_read_content_packet=fetch_read_content_packet,
                    admission_ref=admission_ref,
                    readiness_ref=readiness_ref,
                    component_ref=component_ref,
                    source_obligation_ref=source_obligation_ref,
                    relation_ref={},
                    first_model_review_result=(
                        _workbench_read_support_followup_trigger_result(
                            workbench_dprime_dossier=workbench_dprime_dossier,
                            detail=(
                                _clean_text(
                                    readiness_payload.get("blocker_detail"),
                                    limit=500,
                                )
                                or readiness_status.decision
                            ),
                        )
                    ),
                    dprime_followup_candidate_results=(
                        dprime_followup_candidate_results
                    ),
                    dprime_followup_fetch_read_materials=(
                        dprime_followup_fetch_read_materials
                    ),
                    dprime_followup_plan_builder=dprime_followup_plan_builder,
                    dprime_followup_authorized_execution_callback=(
                        dprime_followup_authorized_execution_callback
                    ),
                    dprime_model_review_license=dprime_model_review_license,
                    dprime_followup_second_pass_model_review_callable=(
                        dprime_followup_second_pass_model_review_callable
                    ),
                    dprime_model_review_callable=dprime_model_review_callable,
                    dprime_one_shot_provider_boundary=(
                        dprime_one_shot_provider_boundary
                    ),
                    dprime_one_shot_model_review_adapter=(
                        dprime_one_shot_model_review_adapter
                    ),
                    dprime_run_kernel_admission_decision_status=(
                        dprime_run_kernel_admission_decision_status
                    ),
                    workbench_dprime_dossier=workbench_dprime_dossier,
                )
                return _followup_search_reentry_result(
                    query=query,
                    readiness_payload={
                        **readiness_payload,
                        "source_evidence_admission_ref": admission_ref,
                        "citation_source_obligation_readiness_ref": readiness_ref,
                        "component_ref": component_ref,
                        "source_obligation_ref": source_obligation_ref,
                    },
                    admission_ref=admission_ref,
                    readiness_ref=readiness_ref,
                    component_ref=component_ref,
                    source_obligation_ref=source_obligation_ref,
                    relation_ref={},
                    followup_result=followup_result,
                    workbench_dprime_dossier_ref=workbench_ref,
                )
        return _blocked_from_readiness_status(
            query=query,
            readiness_decision=readiness_status.decision,
        )

    readiness_payload = _safe_mapping(readiness_status.payload)
    admission_ref = _safe_mapping(readiness_payload.get("source_evidence_admission_ref"))
    readiness_ref = _safe_mapping(
        readiness_payload.get("citation_source_obligation_readiness_ref")
    )
    component_ref = _safe_mapping(readiness_payload.get("component_ref"))
    source_obligation_ref = _safe_mapping(readiness_payload.get("source_obligation_ref"))

    if readiness_payload.get("raw_private_retention") is not False:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE,
            detail="readiness status did not preserve raw/private false posture",
        )
    if admission_ref.get("status") != "custody_created":
        return _blocked_result(
            query=query,
            blocker=BLOCKED_SOURCE_EVIDENCE_STATUS,
            detail="source/evidence custody status is not custody_created",
        )
    if readiness_ref.get("posture") != "not_yet_semantically_supported":
        return _blocked_result(
            query=query,
            blocker=BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS,
            detail="prior readiness posture is not not_yet_semantically_supported",
        )
    if not _component_id(component_ref) or not _source_obligation_ids(
        source_obligation_ref
    ):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING,
            detail="component/source-obligation lineage is not present enough to attempt binding",
        )

    try:
        fetch_read_content_packet = _read_json(
            root / FETCH_READ_ARTIFACT_DIR / FETCH_READ_CONTENT_PACKET_NAME
        )
    except FileNotFoundError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_MISSING,
            detail=f"missing fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except PermissionError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"unreadable fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except json.JSONDecodeError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"fetch/read artifact is not JSON: {exc.msg}",
        )
    except OSError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"could not read fetch/read artifact: {exc}",
        )

    candidate_handoff = _dprime_candidate_handoff_inputs(
        fetch_read_content_packet=fetch_read_content_packet,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        workbench_dprime_dossier=workbench_dprime_dossier,
    )
    if candidate_handoff.get("status") == "blocked":
        return _blocked_candidate_handoff_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref={},
            handoff_ref=candidate_handoff,
            workbench_dprime_dossier_ref=workbench_ref,
        )
    admission_ref = _safe_mapping(candidate_handoff.get("admission_ref")) or admission_ref
    readiness_ref = _safe_mapping(candidate_handoff.get("readiness_ref")) or readiness_ref
    component_ref = _safe_mapping(candidate_handoff.get("component_ref")) or component_ref
    source_obligation_ref = (
        _safe_mapping(candidate_handoff.get("source_obligation_ref"))
        or source_obligation_ref
    )

    try:
        relation_intake = build_dprime_analyst_relation_intake(
            query=query,
            fetch_read_content_packet=fetch_read_content_packet,
            source_evidence_admission_ref=admission_ref,
            citation_source_obligation_readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
        )
    except DPrimeAnalystRelationIntakeError as exc:
        if (
            dprime_followup_search_reentry_enabled
            and _workbench_read_support_followup_required(workbench_dprime_dossier)
        ):
            followup_result = _run_followup_search_reentry_status(
                query=query,
                readiness_payload=readiness_payload,
                fetch_read_content_packet=fetch_read_content_packet,
                admission_ref=admission_ref,
                readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                relation_ref={},
                first_model_review_result=(
                    _workbench_read_support_followup_trigger_result(
                        workbench_dprime_dossier=workbench_dprime_dossier,
                        detail=str(exc),
                    )
                ),
                dprime_followup_candidate_results=(
                    dprime_followup_candidate_results
                ),
                dprime_followup_fetch_read_materials=(
                    dprime_followup_fetch_read_materials
                ),
                dprime_followup_plan_builder=dprime_followup_plan_builder,
                dprime_followup_authorized_execution_callback=(
                    dprime_followup_authorized_execution_callback
                ),
                dprime_model_review_license=dprime_model_review_license,
                dprime_followup_second_pass_model_review_callable=(
                    dprime_followup_second_pass_model_review_callable
                ),
                dprime_model_review_callable=dprime_model_review_callable,
                dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
                dprime_one_shot_model_review_adapter=(
                    dprime_one_shot_model_review_adapter
                ),
                dprime_run_kernel_admission_decision_status=(
                    dprime_run_kernel_admission_decision_status
                ),
                workbench_dprime_dossier=workbench_dprime_dossier,
            )
            return _followup_search_reentry_result(
                query=query,
                readiness_payload=readiness_payload,
                admission_ref=admission_ref,
                readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                relation_ref={},
                followup_result=followup_result,
                workbench_dprime_dossier_ref=workbench_ref,
            )
        return _blocked_result(
            query=query,
            blocker=BLOCKED_DPRIME_GENERIC_RELATION_INTAKE_MISSING,
            detail=str(exc),
        )
    generic_relation_ref = relation_intake_ref(relation_intake)
    candidate_handoff = _candidate_handoff_with_relation_ref(
        candidate_handoff,
        generic_relation_ref,
    )
    if candidate_handoff.get("status") == "blocked":
        return _blocked_candidate_handoff_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref=generic_relation_ref,
            handoff_ref=candidate_handoff,
            workbench_dprime_dossier_ref=workbench_ref,
        )
    component_ref = component_ref_from_relation_intake(relation_intake)
    source_obligation_ref = source_obligation_ref_from_relation_intake(
        relation_intake
    )

    evidence_frame_preflight = build_evidence_frame_preflight(
        fetch_read_content_packet=fetch_read_content_packet,
        source_evidence_admission_ref=admission_ref,
        citation_source_obligation_readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=generic_relation_ref,
    )
    dprime_status = build_dprime_status_payload(
        evidence_frame_preflight=evidence_frame_preflight,
        one_shot_provider_boundary=dprime_one_shot_provider_boundary,
        one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        product_model_route_ref=dprime_product_model_route_ref,
    )
    if (
        dprime_status.decision == BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
        and (
            dprime_model_review_license is not None
            or dprime_model_review_callable is not None
            or dprime_one_shot_model_review_adapter is not None
        )
    ):
        model_review_result = run_dprime_model_review_assessment(
            evidence_frame_preflight=evidence_frame_preflight.to_dict(),
            fetch_read_content_packet=fetch_read_content_packet,
            source_evidence_admission_ref=admission_ref,
            citation_source_obligation_readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            negative_control_profile_ref=dprime_status.negative_control_profile_ref,
            assessment_validator_status=dprime_status.assessment_validator_status,
            license=dprime_model_review_license,
            model_review_callable=dprime_model_review_callable,
            one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
            workbench_dprime_dossier=workbench_dprime_dossier,
        )
        workbench_followup_required = (
            _workbench_current_source_followup_required(workbench_dprime_dossier)
        )
        dprime_followup_required = (
            model_review_result.proposal_validation_status
            != DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
        )
        if (
            dprime_followup_search_reentry_enabled
            and (dprime_followup_required or workbench_followup_required)
        ):
            followup_trigger_result: Any = model_review_result
            if workbench_followup_required and not dprime_followup_required:
                followup_trigger_result = (
                    _workbench_current_source_followup_trigger_result(
                        workbench_dprime_dossier=workbench_dprime_dossier,
                        first_model_review_result=model_review_result,
                    )
                )
            followup_result = _run_followup_search_reentry_status(
                query=query,
                readiness_payload=readiness_payload,
                fetch_read_content_packet=fetch_read_content_packet,
                admission_ref=admission_ref,
                readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                relation_ref=generic_relation_ref,
                first_model_review_result=followup_trigger_result,
                dprime_followup_candidate_results=dprime_followup_candidate_results,
                dprime_followup_fetch_read_materials=(
                    dprime_followup_fetch_read_materials
                ),
                dprime_followup_plan_builder=dprime_followup_plan_builder,
                dprime_followup_authorized_execution_callback=(
                    dprime_followup_authorized_execution_callback
                ),
                dprime_model_review_license=dprime_model_review_license,
                dprime_followup_second_pass_model_review_callable=(
                    dprime_followup_second_pass_model_review_callable
                ),
                dprime_model_review_callable=dprime_model_review_callable,
                dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
                dprime_one_shot_model_review_adapter=(
                    dprime_one_shot_model_review_adapter
                ),
                dprime_run_kernel_admission_decision_status=(
                    dprime_run_kernel_admission_decision_status
                ),
                workbench_dprime_dossier=workbench_dprime_dossier,
            )
            return _followup_search_reentry_result(
                query=query,
                readiness_payload=readiness_payload,
                admission_ref=admission_ref,
                readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                relation_ref=generic_relation_ref,
                followup_result=followup_result,
                workbench_dprime_dossier_ref=workbench_ref,
            )
        return _blocked_dprime_model_review_assessment_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref=generic_relation_ref,
            dprime_status=dprime_status,
            model_review_result=model_review_result,
            fetch_read_content_packet=fetch_read_content_packet,
            dprime_model_review_license=dprime_model_review_license,
            dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            dprime_one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
            dprime_multi_source_relation_inputs=dprime_multi_source_relation_inputs,
            dprime_multi_source_scrutineer_enabled=(
                dprime_multi_source_scrutineer_enabled
            ),
            run_kernel_admission_decision_status=(
                dprime_run_kernel_admission_decision_status
            ),
            dprime_downstream_authority_enabled=dprime_downstream_authority_enabled,
            dprime_source_citation_authority_enabled=(
                dprime_source_citation_authority_enabled
            ),
            dprime_single_lane_answer_path_enabled=(
                dprime_single_lane_answer_path_enabled
            ),
            workbench_dprime_dossier=workbench_dprime_dossier,
            workbench_dprime_dossier_ref=workbench_ref,
            candidate_handoff_ref=candidate_handoff,
        )
    if dprime_status.decision != PASS_DECISION:
        return _blocked_dprime_status_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref=generic_relation_ref,
            dprime_status=dprime_status,
            workbench_dprime_dossier_ref=workbench_ref,
            candidate_handoff_ref=candidate_handoff,
        )

    try:
        semantic_result = build_retained_custody_semantic_coverage(
            fetch_read_content_packet=fetch_read_content_packet,
            expected_candidate_id=_clean_text(
                admission_ref.get("candidate_id"),
                limit=320,
            ),
            expected_reference_id=_clean_text(
                admission_ref.get("reference_id"),
                limit=320,
            ),
        )
    except FileNotFoundError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_MISSING,
            detail=f"missing fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except PermissionError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"unreadable fetch/read artifact: {Path(exc.filename or '').name}",
        )
    except json.JSONDecodeError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"fetch/read artifact is not JSON: {exc.msg}",
        )
    except OSError as exc:
        return _blocked_result(
            query=query,
            blocker=BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE,
            detail=f"could not read fetch/read artifact: {exc}",
        )
    except RetainedCustodyAnalystSupportProposalError as exc:
        payload = _blocked_semantic_payload(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            support_ref=_support_proposal_blocker_ref(
                blocker=exc.blocker,
                detail=exc.detail,
            ),
            semantic_ref=_semantic_observation_blocker_ref(
                blocker=exc.blocker,
                detail=exc.detail,
            ),
            coverage_ref=_component_coverage_blocker_ref(
                component_ref=component_ref,
                blocker=exc.blocker,
                detail=exc.detail,
            ),
            decision=exc.blocker,
            blocker_detail=exc.detail,
            next_blocked_surface=exc.next_surface,
        )
        output = format_live_semantic_coverage_status(payload)
        if not output_hygiene_passes(output):
            return _blocked_result(
                query=query,
                blocker=BLOCKED_OUTPUT_HYGIENE,
                detail="status output contained forbidden material",
            )
        return LiveSemanticCoverageStatusResult(
            decision=exc.blocker,
            output=output,
            payload=payload,
        )

    payload = _pass_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        semantic_result=semantic_result,
        candidate_handoff_ref=candidate_handoff,
    )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=PASS_DECISION,
        output=output,
        payload=payload,
    )


def format_live_semantic_coverage_status(payload: Mapping[str, Any]) -> str:
    """Format concise CLI status without raw/private or product-correctness claims."""

    selected = _safe_mapping(payload.get("selected_candidate"))
    relation = _safe_mapping(payload.get("dprime_relation_intake_ref"))
    relation_binding = _safe_mapping(
        relation.get("component_answer_type_binding_ref")
    )
    admission = _safe_mapping(payload.get("source_evidence_admission_ref"))
    readiness = _safe_mapping(payload.get("citation_source_obligation_readiness_ref"))
    support = _safe_mapping(payload.get("analyst_support_proposal_ref"))
    semantic = _safe_mapping(payload.get("semantic_observation_admission_ref"))
    coverage = _safe_mapping(payload.get("component_coverage_ref"))
    source_authority = _safe_mapping(payload.get("source_obligation_authority_ref"))
    citation_authority = _safe_mapping(
        payload.get("citation_eligibility_authority_ref")
    )
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    citation_display = _safe_mapping(answer_path.get("citation_source_display"))
    dprime = _safe_mapping(payload.get("dprime_status"))
    followup = _safe_mapping(payload.get("dprime_followup_search_reentry_ref"))
    multi_relation_set = _safe_mapping(
        payload.get("dprime_multi_source_relation_set_ref")
    )
    multi_posture = _safe_mapping(
        payload.get("dprime_multi_source_support_posture_ref")
    )
    scrutineer = _safe_mapping(payload.get("dprime_scrutineer_challenge_ref"))
    dprime_request = _safe_mapping(
        dprime.get("run_kernel_support_admission_request_ref")
    )
    dprime_decision = _safe_mapping(
        dprime.get("run_kernel_admission_decision_ref")
    )
    product_model_route = _safe_mapping(dprime.get("product_model_route_ref"))
    closed = payload.get("closed_downstream_surfaces") or CLOSED_DOWNSTREAM_SURFACES
    decision = str(payload.get("decision") or "")
    lines = [
        (
            "live semantic coverage status"
            if decision == PASS_DECISION
            else "live semantic coverage status blocked"
        ),
        f"phase: {PHASE}",
        f"mode: {MODE}",
        f"ordinary entrypoint: {payload.get('ordinary_entrypoint')}",
        f"status flag: {LIVE_SEMANTIC_COVERAGE_STATUS_FLAG}",
        f"user-style query: {payload.get('user_style_query')}",
        (
            "retained-artifact preflight status: "
            f"{payload.get('retained_artifact_preflight_status')}"
        ),
        (
            "retained search candidate status: "
            f"{payload.get('retained_search_candidate_status')}"
        ),
        f"selected candidate rank: {selected.get('rank')}",
        f"selected candidate domain: {selected.get('domain')}",
        f"selected candidate URL: {selected.get('url')}",
        f"fetch/read handoff status: {payload.get('fetch_read_handoff_status')}",
        (
            "source/evidence custody/admission status: "
            f"{admission.get('status')}"
        ),
        (
            "citation/source-obligation readiness posture before semantic support: "
            f"{readiness.get('posture')}"
        ),
        (
            "existing SemanticObservation/ComponentCoverage machinery found: "
            f"{'; '.join(payload.get('semantic_coverage_machinery_found') or [])}"
        ),
        f"D-prime schema status: {dprime.get('schema_status')}",
        f"D-prime preflight status: {dprime.get('preflight_status')}",
        (
            "D-prime negative-control profile status: "
            f"{dprime.get('negative_control_profile_status')}"
        ),
        (
            "D-prime negative-control profile ref/digest: "
            f"{_format_dprime_negative_control_profile_ref(dprime.get('negative_control_profile_ref'))}"
        ),
        (
            "D-prime assessment validator status: "
            f"{dprime.get('assessment_validator_status')}"
        ),
        (
            "D-prime generic relation intake status: "
            f"{relation.get('status', 'not reached')}"
        ),
        (
            "D-prime generic relation intake ref/digest: "
            f"{_format_relation_intake_ref(relation)}"
        ),
        (
            "D-prime generic relation component: "
            f"{relation.get('component_id')} / {relation.get('component_label')}"
        ),
        (
            "D-prime generic relation source obligations: "
            f"{', '.join(_source_obligation_ids(relation)) or 'unavailable'}"
        ),
        (
            "D-prime component answer-type binding: "
            f"{relation_binding.get('requested_answer_type') or 'unavailable'} / "
            f"{relation_binding.get('expected_value_shape') or 'unavailable'}"
        ),
        (
            "D-prime generic relation single-lane only: "
            f"{_bool_text(relation.get('single_lane_only'))}"
        ),
        (
            "D-prime product model role: "
            f"{product_model_route.get('product_model_role')}"
        ),
        (
            "D-prime product smart route provider/model: "
            f"{product_model_route.get('configured_smart_provider')} / "
            f"{product_model_route.get('configured_smart_model')}"
        ),
        (
            "D-prime product smart route approval ref: "
            f"{product_model_route.get('provider_model_approval_ref')}"
        ),
        (
            "D-prime product smart route execution policy: "
            f"{product_model_route.get('execution_policy')}"
        ),
        (
            "D-prime one-shot provider boundary status: "
            f"{dprime.get('one_shot_provider_boundary_status')}"
        ),
        (
            "D-prime one-shot model-review adapter status: "
            f"{dprime.get('one_shot_model_review_adapter_status')}"
        ),
        f"D-prime model review status: {dprime.get('model_review_status')}",
        (
            "D-prime model review ref/digest: "
            f"{_format_dprime_model_review_ref(dprime.get('model_review_ref'))}"
        ),
        f"D-prime assessment status: {dprime.get('assessment_status')}",
        (
            "D-prime assessment validation status: "
            f"{dprime.get('assessment_validation_status', 'not reached')}"
        ),
        (
            "D-prime assessment ref/digest: "
            f"{_format_dprime_assessment_ref(dprime.get('assessment_ref'))}"
        ),
        (
            "D-prime model review call count: "
            f"{dprime.get('model_review_call_count', 0)}"
        ),
        (
            "D-prime proposal validation status: "
            f"{dprime.get('proposal_validation_status')}"
        ),
        (
            "D-prime AnalystFinding validation required: "
            f"{_bool_text(dprime.get('dprime_analyst_finding_validation_required_for_product_path'))}"
        ),
        (
            "D-prime AnalystFinding validation status: "
            f"{dprime.get('dprime_analyst_finding_validation_status', 'not reached')}"
        ),
        (
            "D-prime validated proposal ref/digest: "
            f"{_format_dprime_validated_support_proposal_ref(dprime.get('validated_support_proposal_ref'))}"
        ),
        (
            "RunKernel support admission status: "
            f"{dprime.get('run_kernel_support_admission_status')}"
        ),
        (
            "RunKernel support admission request status: "
            f"{dprime_request.get('request_status', 'not reached')}"
        ),
        (
            "RunKernel admission decision status: "
            f"{dprime.get('run_kernel_admission_decision_status', 'not reached')}"
        ),
        (
            "RunKernel admission decision ref/digest: "
            f"{_format_dprime_run_kernel_decision_ref(dprime_decision)}"
        ),
        f"RunKernel decision: {dprime.get('run_kernel_decision', 'not made')}",
        f"admitted support: {_bool_text(dprime.get('admitted_support'))}",
        (
            "D-prime follow-up search re-entry status: "
            f"{followup.get('status', 'not reached')}"
        ),
        (
            "D-prime follow-up owner: "
            f"{followup.get('dprime_followup_need_owner', 'not reached')}"
        ),
        (
            "follow-up loop owner: "
            f"{followup.get('followup_loop_owner', 'not reached')}"
        ),
        (
            "D-prime dispatch owner: "
            f"{_bool_text(followup.get('dprime_dispatch_owner'))}"
        ),
        (
            "follow-up authorization status: "
            f"{followup.get('followup_search_authorization_status', 'not reached')}"
        ),
        (
            "ordinary follow-up SearchPlanner status: "
            f"{followup.get('ordinary_search_planner_status', 'not reached')}"
        ),
        (
            "ordinary follow-up SearchExecutorHandoff status: "
            f"{followup.get('ordinary_search_executor_handoff_status', 'not reached')}"
        ),
        (
            "ordinary follow-up live-search-validation status: "
            f"{followup.get('ordinary_live_search_validation_status', 'not reached')}"
        ),
        (
            "follow-up candidate packet status: "
            f"{followup.get('search_result_candidate_packet_status', 'not reached')}"
        ),
        (
            "follow-up fetch/read packet status: "
            f"{followup.get('fetch_read_content_packet_status', 'not reached')}"
        ),
        (
            "follow-up evidence re-entry status: "
            f"{followup.get('evidence_reentry_status', 'not reached')}"
        ),
        (
            "D-prime second-pass follow-up status: "
            f"{followup.get('second_dprime_pass_status', 'not reached')}"
        ),
        (
            "D-prime multi-source relation set status: "
            f"{multi_relation_set.get('status', 'not reached')}"
        ),
        (
            "D-prime multi-source relation count: "
            f"{multi_relation_set.get('relation_count', 0)}"
        ),
        (
            "D-prime multi-source source count: "
            f"{multi_posture.get('source_count', 0)}"
        ),
        (
            "D-prime multi-source conflict posture: "
            f"{multi_posture.get('conflict_posture', 'not reached')}"
        ),
        (
            "D-prime multi-source currentness posture: "
            f"{multi_posture.get('currentness_posture', 'not reached')}"
        ),
        (
            "D-prime multi-source answer path allowed: "
            f"{_bool_text(multi_posture.get('answer_path_allowed'))}"
        ),
        (
            "D-prime Scrutineer gate status: "
            f"{scrutineer.get('status', 'not reached')}"
        ),
        (
            "D-prime Scrutineer challenge kind: "
            f"{scrutineer.get('challenge_kind', 'not reached')}"
        ),
        f"Analyst support proposal status: {support.get('status')}",
        f"Analyst support proposal ref/digest: {support.get('proposal_ref')}",
        f"SemanticObservation admission status: {semantic.get('status')}",
        f"SemanticObservation id/ref/digest: {semantic.get('observation_ref')}",
        f"ComponentCoverage status: {coverage.get('status')}",
        f"ComponentCoverage id/ref/digest: {coverage.get('coverage_ref')}",
        f"component id/ref: {_format_component_ref(payload.get('component_ref'))}",
        (
            "source obligation id/ref: "
            f"{_format_source_obligation_ref(payload.get('source_obligation_ref'))}"
        ),
        (
            "semantic support source: "
            f"{payload.get('semantic_support_source')}"
        ),
        (
            "semantic support/custody distinction preserved: "
            f"{_bool_text(payload.get('semantic_support_custody_distinction_preserved'))}"
        ),
        (
            "semantic support reasons or blocker: "
            f"{'; '.join(semantic.get('reasons') or [])}"
        ),
        (
            "component coverage reasons or blocker: "
            f"{'; '.join(coverage.get('reasons') or [])}"
        ),
        (
            "source-obligation authority status: "
            f"{source_authority.get('status')}"
        ),
        (
            "source-obligation authority blocker: "
            f"{source_authority.get('blocker')}"
        ),
        (
            "citation eligibility/handoff authority status: "
            f"{citation_authority.get('status')}"
        ),
        (
            "citation eligibility/handoff authority blocker: "
            f"{citation_authority.get('blocker')}"
        ),
        (
            "SufficiencyReadiness status: "
            f"{answer_path.get('sufficiency_readiness_status')}"
        ),
        (
            "final answer packet status: "
            f"{answer_path.get('final_answer_packet_status')}"
        ),
        f"Author answer status: {answer_path.get('author_answer_status')}",
        (
            "citation/source display status: "
            f"{answer_path.get('citation_source_display_status')}"
        ),
        (
            "D-prime single-lane answer path status: "
            f"{answer_path.get('status')}"
        ),
        (
            "ad hoc semantic matcher/heuristic avoided: "
            f"{_bool_text(payload.get('ad_hoc_semantic_matcher_avoided'))}"
        ),
        f"raw/private retention: {_bool_text(payload.get('raw_private_retention'))}",
        f"closed downstream surfaces: {', '.join(str(item) for item in closed)}",
        f"usable-answer verdict target: {payload.get('usable_answer_verdict_target')}",
        "answerability/correctness: not claimed",
        (
            "current status path live calls: provider/search/broker/fetch/read/"
            "retrieval/model = 0"
        ),
        str(payload.get("non_claim")),
    ]
    answer_text = _clean_text(answer_path.get("answer_text"), limit=2_000)
    if answer_text:
        lines.append(f"Author answer text: {answer_text}")
    for entry in citation_display.get("citation_source_entries") or []:
        source = _safe_mapping(entry)
        display_text = _clean_text(source.get("display_text"), limit=700)
        if display_text:
            lines.append(f"citation/source display: {display_text}")
    if decision != PASS_DECISION:
        lines.extend(
            [
                f"blocker detail: {payload.get('blocker_detail')}",
                f"next blocked surface: {payload.get('next_blocked_surface')}",
            ]
        )
    lines.append(f"decision: {decision}")
    return "\n".join(lines)


def output_hygiene_passes(output: str) -> bool:
    lowered = output.casefold()
    return not any(token in lowered for token in _OUTPUT_FORBIDDEN_TOKENS)


def _support_proposal_blocker_ref(*, blocker: str, detail: str) -> dict[str, Any]:
    return {
        "status": blocker,
        "proposal_ref": "unavailable",
        "reasons": [detail],
    }


def _semantic_observation_blocker_ref(
    *,
    blocker: str = BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING,
    detail: str | None = None,
) -> dict[str, Any]:
    reasons = [
        "current admission bridge requires a validated EvidenceRelativeAnalysisPacket",
        "current admission bridge requires an Analyst possible_support_proposal",
        "retained status chain provides custody and lineage but no product-consumable Analyst support finding",
        "semantic support cannot be inferred from URL/domain/snippet/custody/lineage",
        "semantic support cannot be inferred by ad hoc text matching in this phase",
    ]
    if detail:
        reasons = [detail]
    return {
        "status": blocker,
        "observation_ref": "unavailable",
        "reasons": reasons,
    }


def _component_coverage_blocker_ref(
    *,
    component_ref: Mapping[str, Any],
    blocker: str = BLOCKED_SEMANTIC_COVERAGE_CONSUMER_MISSING,
    detail: str | None = None,
) -> dict[str, Any]:
    reasons = [
        "ComponentCoverage reduction requires an admitted SemanticObservation",
        "no SemanticObservation was admitted for the retained lane",
        "coverage cannot bind to custody/lineage alone",
    ]
    if detail:
        reasons = [detail]
    return {
        "status": blocker,
        "coverage_ref": "unavailable",
        "component_id": _component_id(component_ref),
        "reasons": reasons,
    }


def _pass_semantic_payload(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    semantic_result: RetainedCustodySemanticCoverageResult,
    candidate_handoff_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    support_ref = _support_proposal_ref(semantic_result)
    semantic_ref = _semantic_observation_ref(semantic_result)
    coverage_ref = _component_coverage_ref(semantic_result)
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref={
            **dict(component_ref),
            "component_coverage_bound": True,
        },
        source_obligation_ref=source_obligation_ref,
        support_ref=support_ref,
        semantic_ref=semantic_ref,
        coverage_ref=coverage_ref,
        decision=PASS_DECISION,
        blocker_detail=None,
        next_blocked_surface=None,
        candidate_handoff_ref=candidate_handoff_ref,
    )
    payload.update(
        {
            "semantic_support_source": "retained bounded sanitized content",
            "semantic_support_custody_distinction_preserved": True,
            "analyst_support_proposal_consumer": (
                "core.retained_custody_analyst_support_proposal"
            ),
            "retained_bounded_content_ref": support_ref.get(
                "retained_bounded_content_ref"
            ),
        }
    )
    return payload


def _blocked_semantic_payload(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    support_ref: Mapping[str, Any],
    semantic_ref: Mapping[str, Any],
    coverage_ref: Mapping[str, Any],
    decision: str,
    blocker_detail: str | None,
    next_blocked_surface: str | None,
) -> dict[str, Any]:
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        support_ref=support_ref,
        semantic_ref=semantic_ref,
        coverage_ref=coverage_ref,
        decision=decision,
        blocker_detail=blocker_detail,
        next_blocked_surface=next_blocked_surface or NEXT_BLOCKED_SURFACE,
    )
    payload["semantic_support_source"] = (
        "unavailable; current-path support signal missing"
    )
    return payload


def _blocked_dprime_status_result(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    dprime_status: DPrimeStatusPayload,
    workbench_dprime_dossier_ref: Mapping[str, Any] | None = None,
    candidate_handoff_ref: Mapping[str, Any] | None = None,
) -> LiveSemanticCoverageStatusResult:
    dprime = dprime_status.to_dict()
    dprime["generic_relation_intake_ref"] = dict(relation_ref)
    workbench_ref = _safe_mapping(workbench_dprime_dossier_ref)
    if workbench_ref:
        dprime["workbench_dprime_dossier_ref"] = dict(workbench_ref)
    not_reached_reason = _dprime_not_reached_reason(dprime)
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=relation_ref,
        support_ref={
            "status": dprime["assessment_status"],
            "proposal_ref": "unavailable",
            "reasons": [dprime["blocker_detail"]],
        },
        semantic_ref={
            "status": dprime["semantic_observation_admission_status"],
            "observation_ref": "unavailable",
            "reasons": [not_reached_reason],
        },
        coverage_ref={
            "status": dprime["component_coverage_status"],
            "coverage_ref": "unavailable",
            "component_id": _component_id(component_ref),
            "reasons": [not_reached_reason],
        },
        decision=dprime["decision"],
        blocker_detail=dprime["blocker_detail"],
        next_blocked_surface=_dprime_next_blocked_surface(dprime),
        workbench_dprime_dossier_ref=workbench_ref,
        candidate_handoff_ref=candidate_handoff_ref,
    )
    payload.update(
        {
            "dprime_status": dprime,
            "semantic_support_source": dprime["semantic_support_source"],
            "semantic_support_custody_distinction_preserved": (
                dprime["preflight_status"] == "passed"
            ),
            "analyst_support_proposal_consumer": (
                f"not reached; {dprime['blocker_detail']}"
            ),
        }
    )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=dprime["decision"],
        output=output,
        payload=payload,
    )


def _blocked_dprime_model_review_assessment_result(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    dprime_status: DPrimeStatusPayload,
    model_review_result: Any,
    fetch_read_content_packet: Mapping[str, Any],
    dprime_model_review_license: Any | None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None,
    dprime_one_shot_model_review_adapter: Any | None,
    dprime_multi_source_relation_inputs: Sequence[Mapping[str, Any]],
    dprime_multi_source_scrutineer_enabled: bool,
    run_kernel_admission_decision_status: str,
    dprime_downstream_authority_enabled: bool,
    dprime_source_citation_authority_enabled: bool | None,
    dprime_single_lane_answer_path_enabled: bool | None,
    workbench_dprime_dossier: Mapping[str, Any] | None = None,
    workbench_dprime_dossier_ref: Mapping[str, Any] | None = None,
    candidate_handoff_ref: Mapping[str, Any] | None = None,
) -> LiveSemanticCoverageStatusResult:
    source_citation_authority_enabled = (
        dprime_downstream_authority_enabled
        if dprime_source_citation_authority_enabled is None
        else bool(dprime_source_citation_authority_enabled)
    )
    single_lane_answer_path_enabled = (
        dprime_downstream_authority_enabled
        if dprime_single_lane_answer_path_enabled is None
        else bool(dprime_single_lane_answer_path_enabled)
    )
    dprime = dprime_status.to_dict()
    dprime["generic_relation_intake_ref"] = dict(relation_ref)
    workbench_ref = _safe_mapping(workbench_dprime_dossier_ref)
    if workbench_ref:
        dprime["workbench_dprime_dossier_ref"] = dict(workbench_ref)
    candidate_handoff = _safe_mapping(candidate_handoff_ref)
    if candidate_handoff:
        dprime["candidate_handoff_integrity_ref"] = dict(candidate_handoff)
    dprime["dprime_downstream_authority_enabled"] = bool(
        dprime_downstream_authority_enabled
    )
    dprime["dprime_source_citation_authority_enabled"] = bool(
        source_citation_authority_enabled
    )
    dprime["dprime_single_lane_answer_path_enabled"] = bool(
        single_lane_answer_path_enabled
    )
    dprime.update(model_review_result.to_status_overlay())
    objects_created = dict(dprime.get("objects_created") or {})
    objects_created.update(model_review_result.objects_created)
    dprime["objects_created"] = objects_created
    legacy_proposal_validated = (
        dprime.get("proposal_validation_status")
        == DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    workbench_gate_ref = _unresolved_workbench_followup_required_gate_ref(
        workbench_dprime_dossier
    )
    if legacy_proposal_validated and workbench_gate_ref:
        return _blocked_workbench_followup_required_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref=relation_ref,
            dprime=dprime,
            model_review_result=model_review_result,
            objects_created=objects_created,
            workbench_gate_ref=workbench_gate_ref,
            workbench_ref=workbench_ref,
            candidate_handoff_ref=candidate_handoff,
        )
    analyst_finding_validation_required = analyst_finding_support_validation_required(
        workbench_dprime_dossier
    )
    analyst_finding_validation: dict[str, Any] = {}
    analyst_finding_validation_ref: dict[str, Any] = {}
    analyst_finding_validation_satisfied = True
    if analyst_finding_validation_required:
        analyst_finding_validation = build_dprime_analyst_finding_support_validation(
            workbench_dprime_dossier=workbench_dprime_dossier,
            fetch_read_content_packet=fetch_read_content_packet,
        )
        analyst_finding_validation_ref = (
            dprime_analyst_finding_support_validation_ref(
                analyst_finding_validation
            )
        )
        analyst_finding_validation_satisfied = (
            support_validation_allows_runkernel_admission(
                analyst_finding_validation
            )
        )
        dprime["dprime_analyst_finding_support_validation"] = (
            analyst_finding_validation
        )
        dprime["dprime_analyst_finding_support_validation_ref"] = (
            analyst_finding_validation_ref
        )
        dprime["dprime_analyst_finding_validation_status"] = (
            analyst_finding_validation_ref.get("dprime_validation_status")
        )
        dprime["dprime_analyst_finding_validation_product_proof_status"] = (
            analyst_finding_validation_ref.get("product_proof_status")
        )
        dprime["dprime_analyst_finding_validation_product_proof_blocker"] = (
            analyst_finding_validation_ref.get("product_proof_blocker")
        )
    dprime["dprime_analyst_finding_validation_required_for_product_path"] = (
        analyst_finding_validation_required
    )
    dprime["dprime_analyst_finding_validation_satisfied"] = (
        analyst_finding_validation_satisfied
    )
    objects_created["dprime_analyst_finding_support_validation"] = bool(
        analyst_finding_validation_required
    )
    dprime["objects_created"] = objects_created
    proposal_validated = (
        legacy_proposal_validated and analyst_finding_validation_satisfied
    )
    analyst_finding_validation_blocked = (
        legacy_proposal_validated
        and analyst_finding_validation_required
        and not analyst_finding_validation_satisfied
    )
    if analyst_finding_validation_blocked:
        for key in (
            "run_kernel_admission_decision",
            "semantic_observation",
            "component_coverage",
            "sufficiency_readiness",
            "final_answer_packet",
            "author_answer",
            "citation_source_display",
        ):
            objects_created[key] = False
        dprime["objects_created"] = objects_created
    try:
        additional_relation_results = _additional_dprime_relation_results(
            query=query,
            relation_inputs=dprime_multi_source_relation_inputs,
            dprime_model_review_license=dprime_model_review_license,
            dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            dprime_one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        )
    except DPrimeMultiSourceAnalystScrutinyError as exc:
        additional_relation_results = []
        dprime["multi_source_relation_set_ref"] = {
            "status": "blocked",
            "blocker": exc.blocker,
            "blocker_detail": exc.detail,
        }
        dprime["objects_created"] = objects_created
        return _blocked_result(query=query, blocker=exc.blocker, detail=exc.detail)

    multi_source_enabled = bool(additional_relation_results)
    if multi_source_enabled:
        dprime["multi_source_relation_review_refs"] = [
            item["status_ref"] for item in additional_relation_results
        ]
        objects_created["multi_source_relation_set"] = False
        objects_created["multi_source_support_posture"] = False
        objects_created["multi_source_scrutineer_gate"] = False
        dprime["objects_created"] = objects_created
    decision = None
    semantic_materialization = None
    support_bundle = None
    answer_path = None
    answer_path_error = None
    support_bundle_error = None
    materialization_error = None
    contract_authority = None
    additional_semantic_materializations: list[Any] = []
    multi_source_relation_set_ref: dict[str, Any] = {}
    multi_source_support_posture_ref: dict[str, Any] = {}
    multi_source_scrutineer_ref: dict[str, Any] = {}
    multi_source_blocker: str | None = None
    multi_source_detail: str | None = None
    if proposal_validated:
        decision = build_run_kernel_dprime_admission_decision(
            _safe_mapping(dprime.get("run_kernel_support_admission_request_ref")),
            decision_status=run_kernel_admission_decision_status,
            rationale=(
                "product status consumed validator-passed D-prime admission "
                "request through RunKernel-owned decision runtime"
            ),
        )
        dprime.update(decision.to_status_overlay())
        objects_created["run_kernel_admission_decision"] = True
        dprime["objects_created"] = objects_created
        if decision.decision_status == DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
            try:
                contract_authority = build_dprime_ordinary_contract_authority(
                    fetch_read_content_packet=fetch_read_content_packet,
                    source_evidence_admission_ref=_materialization_ref(
                        admission_ref
                    ),
                    component_ref=_materialization_ref(component_ref),
                    source_obligation_ref=_materialization_ref(
                        source_obligation_ref
                    ),
                )
                semantic_materialization = (
                    materialize_dprime_semantic_observation_from_admitted_decision(
                        decision=decision,
                        assessment_material_ref=_safe_mapping(
                            dprime.get("assessment_material_ref")
                        ),
                        validated_support_proposal_ref=_safe_mapping(
                            dprime.get("validated_support_proposal_ref")
                        ),
                        fetch_read_content_packet=fetch_read_content_packet,
                        source_evidence_admission_ref=_materialization_ref(
                            admission_ref
                        ),
                        component_ref=_materialization_ref(component_ref),
                        source_obligation_ref=_materialization_ref(
                            source_obligation_ref
                        ),
                        run_kernel=contract_authority.run_kernel,
                    )
                )
                dprime.update(semantic_materialization.to_status_overlay())
                dprime["accepted_current_answer_contract_authority_ref"] = (
                    dict(contract_authority.authority_ref)
                )
                objects_created["semantic_observation"] = True
                if multi_source_enabled:
                    try:
                        relation_set = build_dprime_multi_source_relation_set(
                            relation_intake_refs=[
                                relation_ref,
                                *[
                                    item["relation_ref"]
                                    for item in additional_relation_results
                                ],
                            ],
                            assessment_material_refs=[
                                _safe_mapping(dprime.get("assessment_material_ref")),
                                *[
                                    item["assessment_material_ref"]
                                    for item in additional_relation_results
                                ],
                            ],
                        )
                        support_posture = build_dprime_multi_source_support_posture(
                            relation_set=relation_set,
                            assessment_material_refs=[
                                _safe_mapping(dprime.get("assessment_material_ref")),
                                *[
                                    item["assessment_material_ref"]
                                    for item in additional_relation_results
                                ],
                            ],
                        )
                        scrutineer_gate = build_dprime_scrutineer_challenge_gate(
                            support_posture=support_posture,
                            scrutineer_enabled=dprime_multi_source_scrutineer_enabled,
                        )
                        multi_source_relation_set_ref = (
                            relation_set.to_status_ref()
                        )
                        multi_source_support_posture_ref = (
                            support_posture.to_status_ref()
                        )
                        multi_source_scrutineer_ref = (
                            scrutineer_gate.to_status_ref()
                        )
                        objects_created["multi_source_relation_set"] = True
                        objects_created["multi_source_support_posture"] = True
                        objects_created["multi_source_scrutineer_gate"] = (
                            dprime_multi_source_scrutineer_enabled
                        )
                        if scrutineer_gate.answer_path_allowed:
                            additional_semantic_materializations = (
                                _additional_semantic_materializations(
                                    relation_results=additional_relation_results,
                                    run_kernel=contract_authority.run_kernel,
                                    run_kernel_admission_decision_status=(
                                        run_kernel_admission_decision_status
                                    ),
                                )
                            )
                            objects_created[
                                "multi_source_additional_semantic_observations"
                            ] = bool(additional_semantic_materializations)
                        else:
                            multi_source_blocker = (
                                scrutineer_gate.blocker
                                or BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED
                            )
                            multi_source_detail = (
                                scrutineer_gate.blocker_detail
                                or "multi-source Scrutineer gate blocked answer path"
                            )
                    except (
                        DPrimeMultiSourceAnalystScrutinyError,
                        DPrimeSemanticObservationMaterializationError,
                        DPrimeOrdinaryContractAuthorityError,
                    ) as exc:
                        multi_source_blocker = getattr(
                            exc,
                            "blocker",
                            BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
                        )
                        multi_source_detail = getattr(exc, "detail", str(exc))
                    dprime["multi_source_relation_set_ref"] = dict(
                        multi_source_relation_set_ref
                    )
                    dprime["multi_source_support_posture_ref"] = dict(
                        multi_source_support_posture_ref
                    )
                    dprime["multi_source_scrutineer_challenge_ref"] = dict(
                        multi_source_scrutineer_ref
                    )
                    dprime["multi_source_enabled"] = True
                    dprime["objects_created"] = objects_created
                try:
                    if not source_citation_authority_enabled:
                        dprime["downstream_authority_disabled_by_caller"] = True
                        dprime["source_citation_authority_disabled_by_caller"] = True
                        dprime["source_obligation_authority_consumed"] = False
                        dprime[
                            "citation_eligibility_or_source_handoff_authority_consumed"
                        ] = False
                        dprime["dprime_source_citation_stoppoint_status"] = (
                            "not_reached"
                        )
                        dprime["dprime_source_citation_stoppoint_blocker"] = (
                            BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED
                        )
                        dprime["sufficiency_readiness_created"] = False
                        dprime["final_answer_packet_created"] = False
                        dprime["author_answer_created"] = False
                        dprime["citation_source_display_created"] = False
                        objects_created["component_coverage"] = False
                        objects_created["sufficiency_readiness"] = False
                        objects_created["final_answer_packet"] = False
                        objects_created["author_answer"] = False
                        objects_created["citation_source_display"] = False
                        dprime["objects_created"] = objects_created
                    else:
                        if multi_source_blocker is not None:
                            raise DPrimeEvidenceSupportBundleError(
                                multi_source_blocker,
                                multi_source_detail
                                or "multi-source Scrutineer gate blocked answer path",
                            )
                        support_bundle = build_dprime_evidence_support_bundle(
                            semantic_materialization=semantic_materialization,
                            run_kernel=contract_authority.run_kernel,
                            source_obligation_ref=_materialization_ref(
                                source_obligation_ref
                            ),
                            citation_source_obligation_readiness_ref=(
                                _materialization_ref(readiness_ref)
                            ),
                            additional_semantic_materializations=(
                                additional_semantic_materializations
                            ),
                        )
                        dprime.update(support_bundle.to_status_overlay())
                        objects_created["component_coverage"] = True
                        dprime["dprime_source_citation_stoppoint_status"] = (
                            "consumed"
                        )
                        dprime["dprime_source_citation_stoppoint_blocker"] = (
                            support_bundle.decision
                        )
                        if not single_lane_answer_path_enabled:
                            dprime["single_lane_answer_path_disabled_by_caller"] = True
                            dprime["sufficiency_readiness_created"] = False
                            dprime["final_answer_packet_created"] = False
                            dprime["author_answer_created"] = False
                            dprime["citation_source_display_created"] = False
                            objects_created["sufficiency_readiness"] = False
                            objects_created["final_answer_packet"] = False
                            objects_created["author_answer"] = False
                            objects_created["citation_source_display"] = False
                        else:
                            try:
                                answer_path = build_dprime_single_lane_answer_path(
                                    support_bundle=support_bundle,
                                    run_kernel=contract_authority.run_kernel,
                                )
                                dprime.update(answer_path.to_status_overlay())
                                objects_created["sufficiency_readiness"] = True
                                objects_created["final_answer_packet"] = True
                                objects_created["author_answer"] = True
                                objects_created["citation_source_display"] = True
                            except DPrimeSingleLaneAnswerPathError as exc:
                                answer_path_error = exc
                                kernel = contract_authority.run_kernel
                                objects_created["sufficiency_readiness"] = bool(
                                    kernel.state.sufficiency_readiness_projection
                                )
                                objects_created["final_answer_packet"] = bool(
                                    kernel.state.final_answer_authority_projection
                                )
                                objects_created["author_answer"] = bool(
                                    kernel.state.author_prose_projection
                                )
                                objects_created["citation_source_display"] = bool(
                                    kernel.state.projections.get(
                                        "dprime_citation_source_display"
                                    )
                                )
                except DPrimeEvidenceSupportBundleError as exc:
                    support_bundle_error = exc
                    objects_created["component_coverage"] = False
                dprime["objects_created"] = objects_created
            except DPrimeOrdinaryContractAuthorityError as exc:
                materialization_error = DPrimeSemanticObservationMaterializationError(
                    BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT,
                    str(exc),
                )
            except DPrimeSemanticObservationMaterializationError as exc:
                materialization_error = exc
    support_ref = (
        {
            "status": DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            "proposal_ref": _id_digest_ref(
                _safe_mapping(dprime.get("validated_support_proposal_ref")).get(
                    "proposal_id"
                ),
                _safe_mapping(dprime.get("validated_support_proposal_ref")).get(
                    "proposal_digest"
                ),
            ),
            "reasons": [
                "D-prime proposal candidate validated from assessment lineage",
                "proposal candidate is not admitted support",
            ],
        }
        if proposal_validated
        else {
            "status": BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION,
            "proposal_ref": _safe_mapping(
                analyst_finding_validation_ref.get("analyst_finding_proposal_ref")
            )
            or "unavailable",
            "dprime_analyst_finding_support_validation_ref": dict(
                analyst_finding_validation_ref
            ),
            "reasons": [
                "AnalystFindingProposal D-prime support validation is required before RunKernel admission",
                _safe_mapping(
                    analyst_finding_validation_ref.get(
                        "dprime_validation_summary_ref"
                    )
                ).get("validation_summary")
                or "AnalystFindingProposal validation did not support the proposed answer from bounded evidence",
            ],
        }
        if analyst_finding_validation_blocked
        else {
            "status": "not reached",
            "proposal_ref": "unavailable",
            "reasons": [model_review_result.blocker_detail],
        }
    )
    if semantic_materialization is not None:
        semantic_ref = semantic_materialization.semantic_status_ref()
        if support_bundle is not None:
            coverage_ref = support_bundle.component_coverage_ref
            if answer_path is not None:
                payload_decision = PASS_DECISION
                payload_detail = None
                next_surface = None
            elif answer_path_error is not None:
                payload_decision = answer_path_error.blocker
                payload_detail = answer_path_error.detail
                next_surface = answer_path_error.next_surface
            else:
                payload_decision = support_bundle.decision
                payload_detail = support_bundle.blocker_detail
                next_surface = (
                    "D-prime source/citation stop point"
                    if not single_lane_answer_path_enabled
                    else "SufficiencyReadiness"
                )
        elif support_bundle_error is not None:
            if multi_source_blocker is not None:
                coverage_ref = semantic_materialization.coverage_status_ref(
                    component_id=_component_id(component_ref)
                )
                coverage_ref["status"] = "blocked_by_multi_source_scrutineer"
                coverage_ref["blocker"] = support_bundle_error.blocker
                coverage_ref["reasons"] = [
                    "multi-source posture reached Scrutineer gate",
                    support_bundle_error.detail,
                ]
                next_surface = "D-prime multi-source Scrutineer gate"
            else:
                coverage_ref = {
                    "status": "blocked",
                    "coverage_ref": "unavailable",
                    "component_id": _component_id(component_ref),
                    "reasons": [
                        "ComponentCoverage binding failed before source/citation authority",
                        support_bundle_error.detail,
                    ],
                }
                next_surface = "D-prime ComponentCoverage binding"
            payload_decision = support_bundle_error.blocker
            payload_detail = support_bundle_error.detail
        else:
            coverage_ref = semantic_materialization.coverage_status_ref(
                component_id=_component_id(component_ref)
            )
            payload_decision = BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED
            payload_detail = (
                "D-prime SemanticObservation materialized through RunKernel-owned "
                "admission; ComponentCoverage binding is not licensed"
            )
            next_surface = "D-prime ComponentCoverage binding"
    else:
        semantic_ref = {
            "status": "unavailable",
            "observation_ref": "unavailable",
            "reasons": [
                (
                    "AnalystFindingProposal D-prime support validation blocked RunKernel admission"
                    if analyst_finding_validation_blocked
                    else "D-prime proposal candidate is not admitted support"
                ),
                (
                    _safe_mapping(
                        analyst_finding_validation_ref.get(
                            "dprime_validation_summary_ref"
                        )
                    ).get("validation_summary")
                    if analyst_finding_validation_blocked
                    else
                    materialization_error.detail
                    if materialization_error is not None
                    else (
                        "RunKernel-owned D-prime admission decision made; "
                        "SemanticObservation not licensed or materialized"
                        if decision is not None
                        else (
                            "RunKernel support admission request is ready; "
                            "decision not made"
                        )
                    )
                ),
            ],
        }
        coverage_ref = {
            "status": "unavailable",
            "coverage_ref": "unavailable",
            "component_id": _component_id(component_ref),
            "reasons": [
                "ComponentCoverage requires admitted SemanticObservation",
                "D-prime proposal validation cannot bind coverage",
            ],
        }
        payload_decision = (
            BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION
            if analyst_finding_validation_blocked
            else materialization_error.blocker
            if materialization_error is not None
            else decision.blocker
            if decision is not None
            else model_review_result.decision
        )
        payload_detail = (
            (
                _safe_mapping(
                    analyst_finding_validation_ref.get(
                        "dprime_validation_summary_ref"
                    )
                ).get("validation_summary")
                or "AnalystFindingProposal D-prime support validation failed closed"
            )
            if analyst_finding_validation_blocked
            else materialization_error.detail
            if materialization_error is not None
            else decision.blocker_detail
            if decision is not None
            else model_review_result.blocker_detail
        )
        next_surface = _model_review_next_blocked_surface(payload_decision)

    answer_path_ref = _answer_path_status_ref(
        answer_path=answer_path,
        answer_path_error=answer_path_error,
        run_kernel=contract_authority.run_kernel if contract_authority else None,
    )
    candidate_handoff = _candidate_handoff_with_answer_path_refs(
        candidate_handoff,
        answer_path_ref,
    )
    if candidate_handoff.get("status") == "blocked":
        return _blocked_candidate_handoff_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            relation_ref=relation_ref,
            handoff_ref=candidate_handoff,
            workbench_dprime_dossier_ref=workbench_ref,
        )
    if candidate_handoff:
        dprime["candidate_handoff_integrity_ref"] = dict(candidate_handoff)
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=relation_ref,
        support_ref=support_ref,
        semantic_ref=semantic_ref,
        coverage_ref=coverage_ref,
        decision=payload_decision,
        blocker_detail=payload_detail,
        next_blocked_surface=next_surface,
        workbench_dprime_dossier_ref=workbench_ref,
        candidate_handoff_ref=candidate_handoff,
    )
    payload.update(
        {
            "dprime_status": dprime,
            "dprime_analyst_finding_support_validation_ref": dict(
                analyst_finding_validation_ref
            ),
            "dprime_analyst_finding_validation_status": (
                analyst_finding_validation_ref.get("dprime_validation_status")
            ),
            "dprime_analyst_finding_validation_required_for_product_path": (
                analyst_finding_validation_required
            ),
            "dprime_analyst_finding_validation_satisfied": (
                analyst_finding_validation_satisfied
            ),
            "semantic_support_source": (
                (
                    "available from D-prime SemanticObservation and bound "
                    "ComponentCoverage; source-obligation and citation-source "
                    "handoff authority consumed; single-lane answer path "
                    "consumed"
                )
                if answer_path is not None
                else (
                    "available from D-prime SemanticObservation and bound "
                    "ComponentCoverage; source-obligation and citation-source "
                    "handoff authority consumed"
                )
                if support_bundle is not None
                else semantic_materialization.to_status_overlay()["semantic_support_source"]
                if semantic_materialization is not None
                else decision.semantic_support_source
                if proposal_validated and decision is not None
                else "unavailable; D-prime assessment-only model review is not support"
            ),
            "source_obligation_authority_ref": (
                dict(support_bundle.source_obligation_authority_ref)
                if support_bundle is not None
                else {
                    "status": "not reached",
                    "authority_consumed": False,
                }
            ),
            "citation_eligibility_authority_ref": (
                dict(support_bundle.citation_eligibility_authority_ref)
                if support_bundle is not None
                else {
                    "status": "not reached",
                    "authority_consumed": False,
                }
            ),
            "dprime_answer_path_ref": answer_path_ref,
            "component_coverage_only_treated_as_pass": False,
            "detached_posture_status_packet_treated_as_authority": False,
            "semantic_support_custody_distinction_preserved": True,
            "dprime_downstream_authority_enabled": bool(
                dprime_downstream_authority_enabled
            ),
            "dprime_source_citation_authority_enabled": bool(
                source_citation_authority_enabled
            ),
            "dprime_single_lane_answer_path_enabled": bool(
                single_lane_answer_path_enabled
            ),
            "dprime_source_citation_stoppoint_status": (
                "consumed"
                if support_bundle is not None
                else "not_reached"
            ),
            "dprime_source_citation_stoppoint_blocker": (
                support_bundle.decision
                if support_bundle is not None
                else payload_decision
            ),
            "analyst_support_proposal_consumer": (
                (
                    "D-prime proposal candidate validated; RunKernel-owned "
                    "admission decision made"
                )
                if proposal_validated
                else (
                    "not reached; AnalystFindingProposal D-prime support "
                    "validation blocked RunKernel admission"
                )
                if analyst_finding_validation_blocked
                else f"not reached; {model_review_result.blocker_detail}"
            ),
        }
    )
    if multi_source_enabled:
        payload.update(
            {
                "dprime_multi_source_relation_set_ref": dict(
                    multi_source_relation_set_ref
                ),
                "dprime_multi_source_support_posture_ref": dict(
                    multi_source_support_posture_ref
                ),
                "dprime_scrutineer_challenge_ref": dict(
                    multi_source_scrutineer_ref
                ),
                "dprime_multi_source_relation_count": _bounded_int(
                    multi_source_relation_set_ref.get("relation_count")
                ),
                "dprime_multi_source_source_count": _bounded_int(
                    multi_source_support_posture_ref.get("source_count")
                ),
                "dprime_multi_source_posture_consumed_by_product_status": bool(
                    multi_source_support_posture_ref
                ),
                "dprime_multi_source_scrutineer_consumed_by_product_status": bool(
                    multi_source_scrutineer_ref
                ),
                "dprime_multi_source_answer_path_allowed": (
                    multi_source_scrutineer_ref.get("answer_path_allowed") is True
                ),
            }
        )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=payload_decision,
        output=output,
        payload=payload,
    )


def _followup_search_reentry_result(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    followup_result: Any,
    workbench_dprime_dossier_ref: Mapping[str, Any] | None = None,
) -> LiveSemanticCoverageStatusResult:
    dprime_status = dict(followup_result.dprime_status)
    dprime_status["generic_relation_intake_ref"] = dict(relation_ref)
    analyst_validation_ref = _safe_mapping(
        dprime_status.get("dprime_analyst_finding_support_validation_ref")
    )
    workbench_ref = _safe_mapping(workbench_dprime_dossier_ref)
    if workbench_ref:
        dprime_status["workbench_dprime_dossier_ref"] = dict(workbench_ref)
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=relation_ref,
        support_ref=followup_result.support_ref,
        semantic_ref=followup_result.semantic_ref,
        coverage_ref=followup_result.coverage_ref,
        decision=followup_result.decision,
        blocker_detail=followup_result.blocker_detail,
        next_blocked_surface=followup_result.next_blocked_surface,
        workbench_dprime_dossier_ref=workbench_ref,
    )
    payload.update(
        {
            "dprime_status": dprime_status,
            "dprime_analyst_finding_support_validation_ref": dict(
                analyst_validation_ref
            ),
            "dprime_analyst_finding_validation_status": (
                dprime_status.get("dprime_analyst_finding_validation_status")
            ),
            "dprime_analyst_finding_validation_required_for_product_path": (
                dprime_status.get(
                    "dprime_analyst_finding_validation_required_for_product_path"
                )
                is True
            ),
            "dprime_analyst_finding_validation_satisfied": (
                dprime_status.get("dprime_analyst_finding_validation_satisfied")
                is True
            ),
            "dprime_analyst_finding_validation_blocker": dprime_status.get(
                "dprime_analyst_finding_validation_blocker"
            ),
            "followup_analyst_finding_refresh_required": (
                dprime_status.get("followup_analyst_finding_refresh_required")
                is True
            ),
            "followup_analyst_finding_refresh_completed": (
                dprime_status.get("followup_analyst_finding_refresh_completed")
                is True
            ),
            "dprime_followup_search_reentry_ref": dict(followup_result.projection),
            "semantic_support_source": followup_result.semantic_support_source,
            "source_obligation_authority_ref": dict(
                followup_result.source_obligation_authority_ref
            ),
            "citation_eligibility_authority_ref": dict(
                followup_result.citation_eligibility_authority_ref
            ),
            "dprime_answer_path_ref": dict(followup_result.answer_path_ref),
            "accepted_current_answer_contract_authority_ref": dict(
                followup_result.contract_authority_ref
            ),
            "component_coverage_only_treated_as_pass": False,
            "detached_posture_status_packet_treated_as_authority": False,
            "semantic_support_custody_distinction_preserved": True,
            "analyst_support_proposal_consumer": (
                (
                    "D-prime follow-up need consumed by RunKernel-owned "
                    "follow-up authorization, ordinary search re-entry, and "
                    "second-pass D-prime support admission"
                )
                if followup_result.passed
                else (
                    "D-prime follow-up need reached RunKernel-owned ordinary "
                    "search re-entry but did not produce admitted support"
                )
            ),
        }
    )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=followup_result.decision,
        output=output,
        payload=payload,
    )


def _run_followup_search_reentry_status(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    first_model_review_result: Any,
    dprime_followup_candidate_results: (
        Sequence[Mapping[str, Any]] | Mapping[str, Any] | None
    ),
    dprime_followup_fetch_read_materials: Sequence[Mapping[str, Any]],
    dprime_followup_plan_builder: Callable[..., Mapping[str, Any]] | None,
    dprime_followup_authorized_execution_callback: (
        Callable[..., Mapping[str, Any]] | None
    ),
    dprime_model_review_license: Any | None,
    dprime_followup_second_pass_model_review_callable: Callable[..., Any] | None,
    dprime_model_review_callable: Callable[..., Any] | None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None,
    dprime_one_shot_model_review_adapter: Any | None,
    dprime_run_kernel_admission_decision_status: str,
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> Any:
    followup_plan_ref: Mapping[str, Any] = {}
    if dprime_followup_plan_builder is not None:
        followup_plan_ref = _safe_mapping(
            dprime_followup_plan_builder(
                query=query,
                readiness_payload=readiness_payload,
                fetch_read_content_packet=fetch_read_content_packet,
                source_evidence_admission_ref=admission_ref,
                citation_source_obligation_readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                relation_ref=relation_ref,
                first_model_review_result=first_model_review_result,
                workbench_dprime_dossier=workbench_dprime_dossier,
            )
        )
    return run_dprime_followup_search_reentry_using_ordinary_search(
        query=query,
        readiness_payload=readiness_payload,
        original_fetch_read_content_packet=fetch_read_content_packet,
        original_source_evidence_admission_ref=admission_ref,
        citation_source_obligation_readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        first_model_review_result=first_model_review_result,
        followup_plan_ref=followup_plan_ref,
        followup_candidate_results=dprime_followup_candidate_results,
        followup_fetch_read_materials=dprime_followup_fetch_read_materials,
        authorized_followup_execution_callback=(
            dprime_followup_authorized_execution_callback
        ),
        dprime_model_review_license=dprime_model_review_license,
        second_pass_model_review_callable=(
            dprime_followup_second_pass_model_review_callable
            or dprime_model_review_callable
        ),
        dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
        dprime_one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        run_kernel_admission_decision_status=(
            dprime_run_kernel_admission_decision_status
        ),
        workbench_dprime_dossier=workbench_dprime_dossier,
    )


def _workbench_read_support_followup_required(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> bool:
    dossier = _safe_mapping(workbench_dprime_dossier)
    gap = _workbench_followup_gap(dossier)
    gap_kind = _clean_text(gap.get("gap_kind"), limit=120)
    gap_reason = _clean_text(gap.get("gap_reason"), limit=300) or ""
    return bool(
        gap.get("gap_status") == "proposed"
        and gap.get("live_followup_required") is True
        and (
            gap_kind == "unreadable_high_value_candidate"
            or (
                "read support" in gap_reason.casefold()
                and "official" in gap_reason.casefold()
            )
        )
    )


def _workbench_strict_support_followup_required(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> bool:
    gap = _workbench_followup_gap(workbench_dprime_dossier)
    gap_kind = _clean_text(gap.get("gap_kind"), limit=120)
    return bool(
        gap.get("gap_status") == "proposed"
        and gap.get("live_followup_required") is True
        and gap_kind == "strict_support_missing"
    )


def _workbench_current_source_followup_required(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> bool:
    return bool(
        _workbench_strict_support_followup_required(workbench_dprime_dossier)
        or _workbench_read_support_followup_required(workbench_dprime_dossier)
    )


def _workbench_current_source_followup_trigger_result(
    *,
    workbench_dprime_dossier: Mapping[str, Any] | None,
    first_model_review_result: Any,
) -> Mapping[str, Any]:
    if _workbench_read_support_followup_required(workbench_dprime_dossier):
        return _workbench_read_support_followup_trigger_result(
            workbench_dprime_dossier=workbench_dprime_dossier,
            detail=(
                "Workbench official artifact read-support gap remains unresolved "
                "after the first D-prime pass."
            ),
            first_model_review_result=first_model_review_result,
        )
    return _workbench_strict_support_followup_trigger_result(
        workbench_dprime_dossier=workbench_dprime_dossier,
        first_model_review_result=first_model_review_result,
    )


def _workbench_strict_support_followup_trigger_result(
    *,
    workbench_dprime_dossier: Mapping[str, Any] | None,
    first_model_review_result: Any,
) -> Mapping[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    gap = _workbench_followup_gap(dossier)
    gap_ref = _safe_mapping(dossier.get("analysis_gap_search_proposal_ref"))
    first_overlay = (
        first_model_review_result.to_status_overlay()
        if hasattr(first_model_review_result, "to_status_overlay")
        else _safe_mapping(first_model_review_result)
    )
    return {
        "model_review_status": first_overlay.get("model_review_status"),
        "assessment_status": first_overlay.get("assessment_status"),
        "decision": "WORKBENCH_STRICT_SUPPORT_GAP_FOLLOWUP_REQUIRED",
        "blocker_detail": (
            _clean_text(gap.get("gap_reason"), limit=500)
            or "Workbench strict-support gap requires follow-up."
        ),
        "support_relation": "workbench_strict_support_missing",
        "proposal_validation_status": "WORKBENCH_GAP_REQUIRES_FOLLOWUP",
        "assessment_ref": {
            "source": "workbench_analysis_gap_search_proposal",
            "gap_status": gap.get("gap_status"),
            "gap_kind": gap.get("gap_kind"),
            "gap_ref": gap_ref,
            "first_dprime_assessment_ref": _safe_mapping(
                first_overlay.get("assessment_ref")
            ),
            "first_dprime_support_relation": first_overlay.get("support_relation"),
            "first_dprime_proposal_validation_status": first_overlay.get(
                "proposal_validation_status"
            ),
        },
        "objects_created": _safe_mapping(first_overlay.get("objects_created")),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
    }


def _workbench_read_support_followup_trigger_result(
    *,
    workbench_dprime_dossier: Mapping[str, Any] | None,
    detail: str,
    first_model_review_result: Any | None = None,
) -> Mapping[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    gap = _workbench_followup_gap(dossier)
    gap_ref = _safe_mapping(dossier.get("analysis_gap_search_proposal_ref"))
    first_overlay = (
        first_model_review_result.to_status_overlay()
        if hasattr(first_model_review_result, "to_status_overlay")
        else _safe_mapping(first_model_review_result)
    )
    return {
        "model_review_status": first_overlay.get("model_review_status")
        or "not_reached",
        "assessment_status": first_overlay.get("assessment_status") or "not_reached",
        "decision": "WORKBENCH_READ_SUPPORT_GAP_FOLLOWUP_REQUIRED",
        "blocker_detail": (
            _clean_text(gap.get("gap_reason"), limit=500)
            or _clean_text(detail, limit=500)
            or "Workbench official artifact read-support gap requires follow-up."
        ),
        "support_relation": "workbench_read_support_gap",
        "proposal_validation_status": "WORKBENCH_GAP_REQUIRES_FOLLOWUP",
        "assessment_ref": {
            "source": "workbench_analysis_gap_search_proposal",
            "gap_status": gap.get("gap_status"),
            "gap_kind": gap.get("gap_kind"),
            "gap_ref": gap_ref,
            "first_dprime_assessment_ref": _safe_mapping(
                first_overlay.get("assessment_ref")
            ),
            "first_dprime_support_relation": first_overlay.get("support_relation"),
            "first_dprime_proposal_validation_status": first_overlay.get(
                "proposal_validation_status"
            ),
        },
        "objects_created": _safe_mapping(first_overlay.get("objects_created")),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
    }


def _workbench_read_support_followup_lineage_refs(
    *,
    fetch_read_content_packet: Mapping[str, Any],
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reference = _first_fetch_read_reference(fetch_read_content_packet)
    if not reference:
        return {}
    gap = _workbench_followup_gap(workbench_dprime_dossier)
    proposed_query_ref = _safe_mapping(gap.get("proposed_query_ref"))
    component_id = (
        _clean_text(reference.get("component_id"), limit=260)
        or _clean_text(proposed_query_ref.get("component_id"), limit=260)
    )
    source_ids = _text_list(reference.get("source_obligation_candidate_ids"))
    if not source_ids:
        source_id = _clean_text(
            proposed_query_ref.get("source_obligation_id"),
            limit=260,
        )
        source_ids = [source_id] if source_id else []
    contract_digest = _clean_text(
        reference.get("current_answer_contract_digest"),
        limit=128,
    )
    if not component_id or not source_ids or not contract_digest:
        return {}
    behavior_flags = {
        "candidate_content_custody_is_semantic_support": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "source_obligation_candidate_ids_satisfy_requirements": False,
        "component_coverage_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
    }
    admission_ref = _without_empty(
        {
            "status": "lineage_retained_not_semantic_admission",
            "owner": "WorkbenchReadSupportFollowupLineage",
            "fetch_read_content_packet_id": fetch_read_content_packet.get("packet_id"),
            "fetch_read_content_packet_digest": fetch_read_content_packet.get(
                "packet_digest"
            ),
            "candidate_id": reference.get("candidate_id"),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            **behavior_flags,
            "behavior_boundary_flags": behavior_flags,
            "lineage_only_for_followup_authorization": True,
        }
    )
    component_ref = _without_empty(
        {
            "component_id": component_id,
            "current_answer_contract_digest": contract_digest,
            "component_coverage_bound": False,
            "lineage_only_for_followup_authorization": True,
        }
    )
    source_obligation_ref = _without_empty(
        {
            "source_obligation_candidate_ids": source_ids,
            "satisfaction_claimed": False,
            "lineage_only_for_followup_authorization": True,
        }
    )
    readiness_ref = _without_empty(
        {
            "posture": "not_yet_semantically_supported",
            "component_id": component_id,
            "source_obligation_candidate_ids": source_ids,
            "lineage_source": "workbench_unreadable_official_gap",
            "semantic_support_created": False,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
            "lineage_only_for_followup_authorization": True,
        }
    )
    return {
        "admission_ref": admission_ref,
        "component_ref": component_ref,
        "source_obligation_ref": source_obligation_ref,
        "readiness_ref": readiness_ref,
    }


def _first_fetch_read_reference(
    fetch_read_content_packet: Mapping[str, Any],
) -> dict[str, Any]:
    for item in _safe_sequence(fetch_read_content_packet.get("reference_records")):
        reference = _safe_mapping(item)
        if reference.get("candidate_id") and reference.get("reference_id"):
            return reference
    return {}


def _workbench_expected_dprime_candidate_ref(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    selected = _candidate_identity_ref(dossier.get("dprime_review_candidate_ref"))
    if selected:
        return selected
    strict_refs = [
        _candidate_identity_ref(item)
        for item in _safe_sequence(dossier.get("strict_answer_support_candidate_refs"))
    ]
    strict_refs = [item for item in strict_refs if item]
    if len(strict_refs) == 1:
        return strict_refs[0]
    return {}


def _component_answer_type_binding_ref_from_workbench(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    binding = maybe_current_source_component_answer_type_binding_ref(
        _safe_mapping(dossier.get("component_answer_type_binding"))
    ) or _safe_mapping(dossier.get("component_answer_type_binding_ref"))
    return _support_assessment_safe_component_answer_type_binding_ref(binding)


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


def _component_ref_with_binding(
    component_ref: Mapping[str, Any],
    binding_ref: Mapping[str, Any],
) -> dict[str, Any]:
    component = dict(component_ref)
    binding = _safe_mapping(binding_ref)
    if not binding:
        return component
    component["component_answer_type_binding_ref"] = binding
    for target_key, binding_key in (
        ("component_text", "component_text"),
        ("fact_kind", "fact_kind"),
        ("requested_answer_type", "requested_answer_type"),
        ("expected_value_shape", "expected_value_shape"),
        ("claim_under_test", "claim_under_test"),
    ):
        if component.get(target_key) in (None, "", [], {}):
            component[target_key] = binding.get(binding_key)
    if not component.get("component_digest"):
        component["component_digest"] = binding.get("component_digest")
    return _without_empty(component)


def _source_obligation_ref_with_binding(
    source_obligation_ref: Mapping[str, Any],
    binding_ref: Mapping[str, Any],
) -> dict[str, Any]:
    source = dict(source_obligation_ref)
    binding = _safe_mapping(binding_ref)
    if not binding:
        return source
    source["component_answer_type_binding_ref"] = binding
    if source.get("source_obligation_text") in (None, "", [], {}):
        source["source_obligation_text"] = binding.get("source_obligation_text")
    if source.get("source_obligation_id") in (None, "", [], {}):
        source["source_obligation_id"] = binding.get("source_obligation_id")
    return _without_empty(source)


def _candidate_identity_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    dprime_answer_bearing = (
        ref.get("dprime_review_candidate_answer_bearing") is True
        if "dprime_review_candidate_answer_bearing" in ref
        else None
    )
    dprime_diagnostic_only = (
        ref.get("dprime_review_selection_is_diagnostic_only") is True
        if "dprime_review_selection_is_diagnostic_only" in ref
        else None
    )
    return _without_empty(
        {
            "candidate_id": _clean_text(ref.get("candidate_id"), limit=320),
            "candidate_digest": _clean_text(ref.get("candidate_digest"), limit=128),
            "reference_id": _clean_text(ref.get("reference_id"), limit=320),
            "reference_digest": _clean_text(ref.get("reference_digest"), limit=128),
            "title": _clean_text(
                ref.get("title")
                or ref.get("candidate_title")
                or ref.get("source_title")
                or ref.get("content_title"),
                limit=220,
            ),
            "url": _clean_text(
                ref.get("url")
                or ref.get("candidate_url")
                or ref.get("source_url")
                or ref.get("resolved_url")
                or ref.get("final_url")
                or ref.get("canonical_url"),
                limit=700,
            ),
            "domain": _clean_text(
                ref.get("domain")
                or ref.get("candidate_domain")
                or ref.get("source_domain")
                or ref.get("resolved_domain"),
                limit=220,
            ),
            "bounded_content_digest": _clean_text(
                ref.get("bounded_content_digest") or ref.get("excerpt_digest"),
                limit=128,
            ),
            "proposed_candidate_role": _clean_text(
                ref.get("proposed_candidate_role"),
                limit=160,
            ),
            "requested_answer_type_match_status": _clean_text(
                ref.get("requested_answer_type_match_status"),
                limit=160,
            ),
            "expected_value_shape_match_status": _clean_text(
                ref.get("expected_value_shape_match_status"),
                limit=160,
            ),
            "dprime_review_selection_kind": _clean_text(
                ref.get("dprime_review_selection_kind"),
                limit=160,
            ),
            "dprime_review_candidate_answer_bearing": dprime_answer_bearing,
            "dprime_review_selection_is_diagnostic_only": dprime_diagnostic_only,
        }
    )


def _candidate_identity_ref_from_reference(
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    return _candidate_identity_ref(
        {
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "title": reference.get("content_title") or reference.get("candidate_title"),
            "url": (
                reference.get("resolved_url")
                or reference.get("final_url")
                or reference.get("canonical_url")
                or reference.get("candidate_url")
            ),
            "domain": reference.get("resolved_domain")
            or reference.get("candidate_domain"),
            "bounded_content_digest": reference.get("excerpt_digest"),
        }
    )


def _candidate_identity_comparison_mode(expected_ref: Mapping[str, Any]) -> str:
    expected = _candidate_identity_ref(expected_ref)
    if expected.get("candidate_id"):
        return "candidate_id"
    if expected.get("candidate_digest"):
        return "candidate_digest_fallback"
    if expected.get("reference_digest"):
        return "reference_digest_fallback"
    if expected.get("url") and expected.get("bounded_content_digest"):
        return "source_url_plus_bounded_content_digest_fallback"
    return "unavailable"


def _candidate_identity_matches(
    expected_ref: Mapping[str, Any],
    actual_ref: Mapping[str, Any],
) -> bool:
    expected = _candidate_identity_ref(expected_ref)
    actual = _candidate_identity_ref(actual_ref)
    expected_id = _clean_text(expected.get("candidate_id"), limit=320)
    if expected_id:
        return _clean_text(actual.get("candidate_id"), limit=320) == expected_id
    expected_digest = _clean_text(expected.get("candidate_digest"), limit=128)
    if expected_digest and actual.get("candidate_digest"):
        return actual.get("candidate_digest") == expected_digest
    expected_reference_digest = _clean_text(
        expected.get("reference_digest"),
        limit=128,
    )
    if expected_reference_digest and actual.get("reference_digest"):
        return actual.get("reference_digest") == expected_reference_digest
    expected_url = _clean_text(expected.get("url"), limit=700)
    expected_bounded_digest = _clean_text(
        expected.get("bounded_content_digest"),
        limit=128,
    )
    if expected_url and expected_bounded_digest:
        return (
            _clean_text(actual.get("url"), limit=700) == expected_url
            and _clean_text(actual.get("bounded_content_digest"), limit=128)
            == expected_bounded_digest
        )
    return False


def _matching_workbench_reference(
    fetch_read_content_packet: Mapping[str, Any],
    expected_ref: Mapping[str, Any],
) -> dict[str, Any]:
    expected = _candidate_identity_ref(expected_ref)
    if not expected:
        return {}
    for item in _safe_sequence(fetch_read_content_packet.get("reference_records")):
        reference = _safe_mapping(item)
        if reference.get("fetch_read_status") != "readable":
            continue
        if _candidate_identity_matches(
            expected,
            _candidate_identity_ref_from_reference(reference),
        ):
            return reference
    return {}


def _reference_required_content_blocker(reference: Mapping[str, Any]) -> str | None:
    if reference.get("fetch_read_status") != "readable":
        return "Workbench-selected candidate does not have a readable retained reference"
    if reference.get("bounded_text_sanitized") is not True:
        return "Workbench-selected candidate retained content is not marked sanitized"
    if reference.get("bounded_text_bounded") is not True:
        return "Workbench-selected candidate retained content is not marked bounded"
    if not _clean_text(reference.get("bounded_text"), limit=20_000):
        return "Workbench-selected candidate is missing retained bounded content"
    if not _clean_text(reference.get("excerpt_digest"), limit=128):
        return "Workbench-selected candidate is missing retained bounded-text digest"
    return None


def _admission_ref_for_reference(
    admission_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    ref = dict(admission_ref)
    ref.update(
        _without_empty(
            {
                "candidate_id": reference.get("candidate_id"),
                "candidate_digest": reference.get("candidate_digest"),
                "reference_id": reference.get("reference_id"),
                "reference_digest": reference.get("reference_digest"),
                "dprime_candidate_handoff_route": (
                    "workbench_dprime_review_candidate_ref"
                ),
            }
        )
    )
    ref["ref_digest"] = _digest_json(
        {key: value for key, value in ref.items() if key != "ref_digest"}
    )
    return _without_empty(ref)


def _component_ref_for_reference(
    component_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    contract_ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    return _without_empty(
        {
            **dict(component_ref),
            "component_id": reference.get("component_id")
            or component_ref.get("component_id"),
            "current_answer_contract_digest": contract_ref.get("contract_digest")
            or reference.get("current_answer_contract_digest")
            or component_ref.get("current_answer_contract_digest"),
            "component_coverage_bound": False,
            "lineage_only": True,
        }
    )


def _source_obligation_ref_for_reference(
    source_obligation_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    source_ids = _text_list(reference.get("source_obligation_candidate_ids"))
    return _without_empty(
        {
            **dict(source_obligation_ref),
            "source_obligation_candidate_ids": source_ids
            or _text_list(source_obligation_ref.get("source_obligation_candidate_ids")),
            "satisfaction_claimed": False,
            "lineage_only": True,
        }
    )


def _readiness_ref_for_routed_reference(
    readiness_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    source_ids = _text_list(reference.get("source_obligation_candidate_ids"))
    return _without_empty(
        {
            **dict(readiness_ref),
            "posture": readiness_ref.get("posture")
            or "not_yet_semantically_supported",
            "source_obligation_candidate_ids": source_ids
            or _text_list(readiness_ref.get("source_obligation_candidate_ids")),
            "lineage_only": True,
        }
    )


def _dprime_candidate_handoff_inputs(
    *,
    fetch_read_content_packet: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = _workbench_expected_dprime_candidate_ref(workbench_dprime_dossier)
    binding_ref = _component_answer_type_binding_ref_from_workbench(
        workbench_dprime_dossier
    )
    bound_component_ref = _component_ref_with_binding(component_ref, binding_ref)
    bound_source_obligation_ref = _source_obligation_ref_with_binding(
        source_obligation_ref,
        binding_ref,
    )
    if not expected:
        return {
            "status": "not_applicable",
            "match_status": "not_applicable",
            "candidate_identity_match": True,
            "comparison_mode": "not_applicable",
            "expected_workbench_candidate_ref": {},
            "source_evidence_admission_candidate_ref": _candidate_identity_ref(
                admission_ref
            ),
            "admission_ref": dict(admission_ref),
            "readiness_ref": dict(readiness_ref),
            "component_ref": bound_component_ref,
            "source_obligation_ref": bound_source_obligation_ref,
            "component_answer_type_binding_ref": binding_ref,
            "raw_private_retention": False,
        }
    current_reference = _matching_workbench_reference(
        fetch_read_content_packet,
        _candidate_identity_ref(admission_ref),
    )
    current_ref = (
        _candidate_identity_ref_from_reference(current_reference)
        if current_reference
        else _candidate_identity_ref(admission_ref)
    )
    base = {
        "schema_version": "current_source_record_dprime_candidate_handoff_integrity_v1",
        "status": "matched",
        "match_status": "match",
        "candidate_identity_match": True,
        "comparison_mode": _candidate_identity_comparison_mode(expected),
        "id_first_comparison_required": bool(expected.get("candidate_id")),
        "title_only_match_allowed": False,
        "url_only_match_allowed": False,
        "expected_workbench_candidate_ref": expected,
        "source_evidence_admission_candidate_ref": current_ref,
        "component_answer_type_binding_ref": binding_ref,
        "raw_private_retention": False,
        "product_correctness_claimed": False,
    }
    if _candidate_identity_matches(expected, current_ref):
        return {
            **base,
            "route_status": "already_matched",
            "admission_ref": dict(admission_ref),
            "readiness_ref": dict(readiness_ref),
            "component_ref": bound_component_ref,
            "source_obligation_ref": bound_source_obligation_ref,
        }

    routed_reference = _matching_workbench_reference(fetch_read_content_packet, expected)
    if not routed_reference:
        return _blocked_candidate_handoff_ref(
            base=base,
            surface="D-prime relation intake",
            detail=(
                "Workbench selected a D-prime review candidate, but the retained "
                "fetch/read packet has no readable reference for that candidate."
            ),
        )
    content_blocker = _reference_required_content_blocker(routed_reference)
    if content_blocker:
        return _blocked_candidate_handoff_ref(
            base=base,
            surface="D-prime relation intake",
            detail=content_blocker,
        )
    routed_candidate_ref = _candidate_identity_ref_from_reference(routed_reference)
    routed_admission = _admission_ref_for_reference(admission_ref, routed_reference)
    return {
        **base,
        "status": "routed",
        "match_status": "match",
        "route_status": "workbench_candidate_routed_to_dprime_intake",
        "source_evidence_admission_candidate_ref": routed_candidate_ref,
        "routed_from_candidate_ref": current_ref,
        "routed_to_candidate_ref": routed_candidate_ref,
        "admission_ref": routed_admission,
        "readiness_ref": _readiness_ref_for_routed_reference(
            readiness_ref,
            routed_reference,
        ),
        "component_ref": _component_ref_with_binding(
            _component_ref_for_reference(component_ref, routed_reference),
            binding_ref,
        ),
        "source_obligation_ref": _source_obligation_ref_with_binding(
            _source_obligation_ref_for_reference(
                source_obligation_ref,
                routed_reference,
            ),
            binding_ref,
        ),
    }


def _blocked_candidate_handoff_ref(
    *,
    base: Mapping[str, Any],
    surface: str,
    detail: str,
) -> dict[str, Any]:
    expected = _candidate_identity_ref(
        _safe_mapping(base).get("expected_workbench_candidate_ref")
    )
    actual = _candidate_identity_ref(
        _safe_mapping(base).get("source_evidence_admission_candidate_ref")
    )
    return {
        **dict(base),
        "status": "blocked",
        "match_status": "mismatch",
        "candidate_identity_match": False,
        "blocker": BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH,
        "blocker_detail": _candidate_handoff_blocker_detail(
            expected_ref=expected,
            actual_ref=actual,
            surface=surface,
            detail=detail,
        ),
        "mismatch_surface": surface,
        "admission_ref": {},
        "readiness_ref": {},
        "component_ref": {},
        "source_obligation_ref": {},
    }


def _candidate_handoff_blocker_detail(
    *,
    expected_ref: Mapping[str, Any],
    actual_ref: Mapping[str, Any],
    surface: str,
    detail: str,
) -> str:
    expected_id = expected_ref.get("candidate_id") or "unavailable"
    actual_id = actual_ref.get("candidate_id") or "unavailable"
    expected_title = expected_ref.get("title") or "unavailable"
    actual_title = actual_ref.get("title") or "unavailable"
    return (
        f"{detail} Surface: {surface}. Expected Workbench/D-prime-review "
        f"candidate id/title: {expected_id} / {expected_title}. Actual D-prime "
        f"candidate id/title: {actual_id} / {actual_title}."
    )


def _candidate_handoff_with_relation_ref(
    handoff_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
) -> dict[str, Any]:
    if not handoff_ref:
        return {}
    relation_candidate = _candidate_identity_ref(
        {
            "candidate_id": relation_ref.get("evidence_candidate_id"),
            "reference_id": relation_ref.get("evidence_reference_id"),
            "title": relation_ref.get("source_title"),
            "url": relation_ref.get("source_url"),
            "domain": relation_ref.get("source_domain"),
        }
    )
    expected = _candidate_identity_ref(
        handoff_ref.get("expected_workbench_candidate_ref")
    )
    match = (
        handoff_ref.get("candidate_identity_match") is not False
        and (
            not expected
            or _candidate_identity_matches(expected, relation_candidate)
        )
    )
    updated = {
        **dict(handoff_ref),
        "dprime_relation_intake_candidate_ref": relation_candidate,
        "dprime_intake_actual_candidate_ref": relation_candidate,
        "candidate_identity_match": match,
        "match_status": "match" if match else "mismatch",
    }
    if not match:
        updated["status"] = "blocked"
        updated["blocker"] = (
            BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH
        )
        updated["blocker_detail"] = _candidate_handoff_blocker_detail(
            expected_ref=expected,
            actual_ref=relation_candidate,
            surface="D-prime relation intake",
            detail="Workbench D-prime candidate identity diverged at relation intake.",
        )
        updated["mismatch_surface"] = "D-prime relation intake"
    return updated


def _candidate_handoff_with_answer_path_refs(
    handoff_ref: Mapping[str, Any],
    answer_path_ref: Mapping[str, Any],
) -> dict[str, Any]:
    if not handoff_ref:
        return {}
    answer_path = _safe_mapping(answer_path_ref)
    display = _safe_mapping(answer_path.get("citation_source_display"))
    display_refs = [
        _candidate_identity_ref(item)
        for item in _safe_sequence(display.get("citation_source_entries"))
    ]
    display_refs = [item for item in display_refs if item]
    selected_source = _candidate_identity_ref(answer_path.get("claim_text_source_ref"))
    if not selected_source and display_refs:
        selected_source = display_refs[0]
    expected = _candidate_identity_ref(
        handoff_ref.get("expected_workbench_candidate_ref")
    )
    refs_to_check = [item for item in (selected_source, *display_refs) if item]
    if not expected:
        match = handoff_ref.get("candidate_identity_match") is not False
    else:
        match = handoff_ref.get("candidate_identity_match") is not False and all(
            _candidate_identity_matches(expected, item) for item in refs_to_check
        )
    if expected and refs_to_check:
        status = "match" if match else "mismatch"
    else:
        status = handoff_ref.get("match_status")
    updated = {
        **dict(handoff_ref),
        "selected_source_candidate_ref": selected_source,
        "source_display_candidate_refs": display_refs,
        "source_display_candidate_ref": display_refs[0] if display_refs else {},
        "candidate_identity_match": match,
        "match_status": status,
    }
    if not match:
        updated["status"] = "blocked"
        updated["blocker"] = (
            BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH
        )
        actual = selected_source or (display_refs[0] if display_refs else {})
        updated["blocker_detail"] = _candidate_handoff_blocker_detail(
            expected_ref=expected,
            actual_ref=actual,
            surface="D-prime answer/source display",
            detail=(
                "Workbench D-prime candidate identity diverged at selected "
                "source or source display."
            ),
        )
        updated["mismatch_surface"] = "D-prime answer/source display"
    return updated


def _blocked_candidate_handoff_result(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any] | None,
    handoff_ref: Mapping[str, Any],
    workbench_dprime_dossier_ref: Mapping[str, Any] | None,
) -> LiveSemanticCoverageStatusResult:
    blocker_detail = (
        _clean_text(handoff_ref.get("blocker_detail"), limit=900)
        or "Workbench/D-prime candidate identity handoff mismatch."
    )
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=relation_ref or {},
        support_ref={
            "status": "not reached",
            "proposal_ref": "unavailable",
            "reasons": [blocker_detail],
        },
        semantic_ref={
            "status": "not reached",
            "observation_ref": "unavailable",
            "reasons": [blocker_detail],
        },
        coverage_ref={
            "status": "not reached",
            "coverage_ref": "unavailable",
            "component_id": _component_id(component_ref),
            "reasons": [blocker_detail],
        },
        decision=BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH,
        blocker_detail=blocker_detail,
        next_blocked_surface="D-prime relation-intake candidate handoff",
        workbench_dprime_dossier_ref=workbench_dprime_dossier_ref,
        candidate_handoff_ref=handoff_ref,
    )
    payload.update(
        {
            "dprime_status": _blocked_candidate_handoff_dprime_status(handoff_ref),
            "semantic_support_source": "unavailable; D-prime candidate handoff mismatch",
            "source_obligation_authority_ref": {
                "status": "not reached",
                "authority_consumed": False,
            },
            "citation_eligibility_authority_ref": {
                "status": "not reached",
                "authority_consumed": False,
            },
            "dprime_answer_path_ref": {},
            "component_coverage_only_treated_as_pass": False,
            "detached_posture_status_packet_treated_as_authority": False,
            "semantic_support_custody_distinction_preserved": True,
            "analyst_support_proposal_consumer": f"not reached; {blocker_detail}",
        }
    )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH,
        output=output,
        payload=payload,
    )


def _blocked_candidate_handoff_dprime_status(
    handoff_ref: Mapping[str, Any],
) -> dict[str, Any]:
    detail = (
        _clean_text(handoff_ref.get("blocker_detail"), limit=900)
        or "Workbench/D-prime candidate identity handoff mismatch."
    )
    return {
        "decision": BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH,
        "blocker_detail": detail,
        "candidate_handoff_integrity_ref": dict(handoff_ref),
        "generic_relation_intake_ref": {},
        "assessment_status": "not reached",
        "support_relation": None,
        "proposal_validation_status": "not reached",
        "run_kernel_admission_decision_status": "not reached",
        "semantic_observation_admission_status": "not reached",
        "component_coverage_status": "not reached",
        "source_obligation_authority_consumed": False,
        "citation_eligibility_or_source_handoff_authority_consumed": False,
        "dprime_single_lane_answer_path_status": "not reached",
        "objects_created": {
            "evidence_frame_preflight": False,
            "evidence_relative_support_assessment": False,
            "validated_support_proposal": False,
            "run_kernel_support_proposal_admission_request": False,
            "run_kernel_admission_decision": False,
            "semantic_observation": False,
            "component_coverage": False,
            "sufficiency_readiness": False,
            "final_answer_packet": False,
            "author_answer": False,
            "citation_source_display": False,
        },
    }


def _blocked_workbench_followup_required_result(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    dprime: Mapping[str, Any],
    model_review_result: Any,
    objects_created: Mapping[str, Any],
    workbench_gate_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    candidate_handoff_ref: Mapping[str, Any],
) -> LiveSemanticCoverageStatusResult:
    detail = (
        _clean_text(workbench_gate_ref.get("blocker_detail"), limit=900)
        or "Workbench follow-up-required gap is unresolved and not licensed."
    )
    blocked_objects = dict(objects_created)
    for key in (
        "run_kernel_admission_decision",
        "semantic_observation",
        "component_coverage",
        "sufficiency_readiness",
        "final_answer_packet",
        "author_answer",
        "citation_source_display",
    ):
        blocked_objects[key] = False

    blocked_dprime = dict(dprime)
    blocked_dprime.update(
        {
            "decision": BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED,
            "blocker_detail": detail,
            "workbench_followup_authority_gate_ref": dict(workbench_gate_ref),
            "workbench_gap_reentry_status": "followup_not_licensed",
            "run_kernel_decision": "not made",
            "run_kernel_admission_decision_status": "not_reached",
            "admitted_support": False,
            "semantic_observation_admission_status": "not_reached",
            "component_coverage_status": "not_reached",
            "source_obligation_authority_consumed": False,
            "citation_eligibility_or_source_handoff_authority_consumed": False,
            "dprime_source_citation_stoppoint_status": "not_reached",
            "dprime_source_citation_stoppoint_blocker": (
                BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED
            ),
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "citation_source_display_created": False,
            "objects_created": blocked_objects,
        }
    )
    support_ref = {
        "status": DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
        "proposal_ref": _id_digest_ref(
            _safe_mapping(blocked_dprime.get("validated_support_proposal_ref")).get(
                "proposal_id"
            ),
            _safe_mapping(blocked_dprime.get("validated_support_proposal_ref")).get(
                "proposal_digest"
            ),
        ),
        "reasons": [
            "D-prime proposal candidate validated from assessment lineage",
            "proposal candidate is not admitted support",
            "Workbench follow-up-required gap blocks RunKernel admission",
        ],
    }
    semantic_ref = {
        "status": "unavailable",
        "observation_ref": "unavailable",
        "reasons": [
            "RunKernel support admission decision was not created",
            detail,
        ],
    }
    coverage_ref = {
        "status": "unavailable",
        "coverage_ref": "unavailable",
        "component_id": _component_id(component_ref),
        "reasons": [
            "ComponentCoverage requires admitted SemanticObservation",
            detail,
        ],
    }
    answer_path_ref = _answer_path_status_ref(
        answer_path=None,
        answer_path_error=None,
        run_kernel=None,
    )
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        relation_intake_ref=relation_ref,
        support_ref=support_ref,
        semantic_ref=semantic_ref,
        coverage_ref=coverage_ref,
        decision=BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED,
        blocker_detail=detail,
        next_blocked_surface="Workbench follow-up-required gap resolution",
        workbench_dprime_dossier_ref=workbench_ref,
        candidate_handoff_ref=candidate_handoff_ref,
    )
    payload.update(
        {
            "dprime_status": blocked_dprime,
            "workbench_followup_authority_gate_ref": dict(workbench_gate_ref),
            "semantic_support_source": (
                "unavailable; unresolved Workbench follow-up-required gap "
                "blocked RunKernel support admission"
            ),
            "source_obligation_authority_ref": {
                "status": "not reached",
                "authority_consumed": False,
            },
            "citation_eligibility_authority_ref": {
                "status": "not reached",
                "authority_consumed": False,
            },
            "dprime_answer_path_ref": answer_path_ref,
            "component_coverage_only_treated_as_pass": False,
            "detached_posture_status_packet_treated_as_authority": False,
            "semantic_support_custody_distinction_preserved": True,
            "dprime_source_citation_stoppoint_status": "not_reached",
            "dprime_source_citation_stoppoint_blocker": (
                BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED
            ),
            "analyst_support_proposal_consumer": (
                "not reached; Workbench follow-up-required gap remains "
                "unresolved before RunKernel support admission"
            ),
            "model_review_result_blocked_before_runkernel_admission": (
                model_review_result.decision
            ),
        }
    )
    output = format_live_semantic_coverage_status(payload)
    if not output_hygiene_passes(output):
        return _blocked_result(
            query=query,
            blocker=BLOCKED_OUTPUT_HYGIENE,
            detail="status output contained forbidden material",
        )
    return LiveSemanticCoverageStatusResult(
        decision=BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED,
        output=output,
        payload=payload,
    )


def _unresolved_workbench_followup_required_gate_ref(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    gap = _workbench_followup_gap(dossier)
    gap_status = _clean_text(gap.get("gap_status"), limit=120)
    followup_required = gap.get("live_followup_required") is True
    if gap_status != "proposed" or not followup_required:
        return {}
    if _workbench_followup_resolution_present(gap):
        return {}
    gap_kind = _clean_text(gap.get("gap_kind"), limit=160)
    detail = _workbench_followup_not_licensed_detail(gap)
    gap_ref = _safe_mapping(dossier.get("analysis_gap_search_proposal_ref"))
    return _without_empty(
        {
            "schema_version": "workbench_followup_required_authority_gate_v1",
            "status": "blocked",
            "blocker": BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED,
            "blocker_detail": detail,
            "surface": "current_source_record_workbench_gap_projection_gate",
            "gap_status": gap_status,
            "gap_kind": gap_kind,
            "gap_reason": _clean_text(gap.get("gap_reason"), limit=500),
            "live_followup_required": True,
            "live_followup_licensed": gap.get("live_followup_licensed") is True,
            "followup_execution_licensed": (
                gap.get("followup_execution_licensed") is True
            ),
            "proposed_runkernel_reduction_status": gap.get(
                "proposed_runkernel_reduction_status"
            ),
            "workbench_gap_reentry_status": "followup_not_licensed",
            "runkernel_followup_authorization_created": False,
            "followup_provider_calls_attempted": 0,
            "followup_fetch_read_attempts": 0,
            "provider_called": False,
            "fetch_read_executed": False,
            "workbench_gap_proposal_ref": gap_ref,
            "run_kernel_support_admission_allowed": False,
            "semantic_observation_allowed": False,
            "component_coverage_allowed": False,
            "sufficiency_readiness_allowed": False,
            "final_answer_packet_allowed": False,
            "author_answer_allowed": False,
            "source_display_allowed": False,
            "product_correctness_claimed": False,
        }
    )


def _workbench_followup_resolution_present(gap: Mapping[str, Any]) -> bool:
    statuses = {
        _clean_text(gap.get("proposed_runkernel_reduction_status"), limit=160),
        _clean_text(gap.get("workbench_gap_reentry_status"), limit=160),
        _clean_text(gap.get("followup_execution_status"), limit=160),
    }
    return bool(
        statuses
        & {
            "runkernel_authorized_executed",
            "runkernel_authorized_exhausted",
            "executed_ordinary_search_followup",
            "exhausted",
            "answer_path_not_reached",
        }
    )


def _workbench_followup_not_licensed_detail(gap: Mapping[str, Any]) -> str:
    gap_kind = _clean_text(gap.get("gap_kind"), limit=160)
    if gap_kind == "unreadable_high_value_candidate":
        return (
            "Official source read support is needed. A high-value official "
            "artifact was found, but bounded PDF/table text support is not "
            "available in this run."
        )
    return (
        "Official strict support follow-up is needed; the Workbench gap remains "
        "proposal-only because live follow-up execution is not licensed."
    )


def _workbench_followup_gap(
    workbench_dprime_dossier: Mapping[str, Any] | None,
) -> dict[str, Any]:
    dossier = _safe_mapping(workbench_dprime_dossier)
    gap = _safe_mapping(dossier.get("analysis_gap_search_proposal"))
    if gap:
        return gap
    gap_ref = _safe_mapping(dossier.get("analysis_gap_search_proposal_ref"))
    if gap_ref:
        return _without_empty(
            {
                "gap_status": gap_ref.get("gap_status"),
                "gap_kind": gap_ref.get("gap_kind"),
                "live_followup_required": gap_ref.get("live_followup_required"),
                "live_followup_licensed": gap_ref.get("live_followup_licensed"),
                "proposed_runkernel_reduction_status": gap_ref.get(
                    "proposed_runkernel_reduction_status"
                ),
            }
        )
    return {}


def _model_review_next_blocked_surface(decision: str) -> str:
    if decision == BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION:
        return "D-prime AnalystFindingProposal support validation"
    if decision == BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED:
        return "Workbench follow-up-required gap resolution"
    if decision == BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH:
        return "D-prime relation-intake candidate handoff"
    if decision == BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED:
        return "SufficiencyReadiness"
    if decision == BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING:
        return "D-prime source-obligation authority"
    if decision == BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING:
        return "D-prime ComponentCoverage binding"
    if decision == BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED:
        return "D-prime ComponentCoverage binding"
    if decision == BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT:
        return "D-prime SemanticObservation materialization input authority"
    if decision == BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED:
        return "D-prime SemanticObservation materialization"
    if decision == BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING:
        return "D-prime RunKernel support admission decision"
    return "D-prime model-review assessment"


def _additional_dprime_relation_results(
    *,
    query: str,
    relation_inputs: Sequence[Mapping[str, Any]],
    dprime_model_review_license: Any,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None,
    dprime_one_shot_model_review_adapter: Any | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, relation_input in enumerate(relation_inputs or (), start=2):
        item = _safe_mapping(relation_input)
        fetch_packet = _safe_mapping(item.get("fetch_read_content_packet"))
        admission_ref = _safe_mapping(item.get("source_evidence_admission_ref"))
        readiness_ref = _safe_mapping(
            item.get("citation_source_obligation_readiness_ref")
        )
        component_ref = _safe_mapping(item.get("component_ref"))
        source_obligation_ref = _safe_mapping(item.get("source_obligation_ref"))
        model_review_callable = item.get("model_review_callable")
        if not fetch_packet:
            raise DPrimeMultiSourceAnalystScrutinyError(
                BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
                "additional multi-source relation lacks fetch/read packet",
            )
        if not admission_ref or not readiness_ref or not component_ref:
            raise DPrimeMultiSourceAnalystScrutinyError(
                BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
                "additional multi-source relation lacks product lineage refs",
            )
        if not source_obligation_ref or model_review_callable is None:
            raise DPrimeMultiSourceAnalystScrutinyError(
                BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
                "additional multi-source relation lacks source obligation or review callable",
            )
        try:
            relation_intake = build_dprime_analyst_relation_intake(
                query=query,
                fetch_read_content_packet=fetch_packet,
                source_evidence_admission_ref=admission_ref,
                citation_source_obligation_readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
            )
        except DPrimeAnalystRelationIntakeError as exc:
            raise DPrimeMultiSourceAnalystScrutinyError(
                BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
                str(exc),
            ) from exc
        relation_ref = relation_intake_ref(relation_intake)
        relation_component_ref = component_ref_from_relation_intake(relation_intake)
        relation_source_obligation_ref = source_obligation_ref_from_relation_intake(
            relation_intake
        )
        evidence_frame_preflight = build_evidence_frame_preflight(
            fetch_read_content_packet=fetch_packet,
            source_evidence_admission_ref=admission_ref,
            citation_source_obligation_readiness_ref=readiness_ref,
            component_ref=relation_component_ref,
            source_obligation_ref=relation_source_obligation_ref,
            relation_intake_ref=relation_ref,
        )
        dprime_status = build_dprime_status_payload(
            evidence_frame_preflight=evidence_frame_preflight,
            one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        )
        model_review_result = run_dprime_model_review_assessment(
            evidence_frame_preflight=evidence_frame_preflight.to_dict(),
            fetch_read_content_packet=fetch_packet,
            source_evidence_admission_ref=admission_ref,
            citation_source_obligation_readiness_ref=readiness_ref,
            component_ref=relation_component_ref,
            source_obligation_ref=relation_source_obligation_ref,
            negative_control_profile_ref=dprime_status.negative_control_profile_ref,
            assessment_validator_status=dprime_status.assessment_validator_status,
            license=item.get("dprime_model_review_license")
            or dprime_model_review_license,
            model_review_callable=model_review_callable,
            one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        )
        assessment_material_ref = _safe_mapping(
            model_review_result.assessment_material_ref
        )
        results.append(
            {
                "ordinal": index,
                "fetch_read_content_packet": fetch_packet,
                "source_evidence_admission_ref": admission_ref,
                "citation_source_obligation_readiness_ref": readiness_ref,
                "component_ref": relation_component_ref,
                "source_obligation_ref": relation_source_obligation_ref,
                "relation_ref": relation_ref,
                "assessment_material_ref": assessment_material_ref,
                "model_review_result": model_review_result,
                "status_ref": _additional_relation_status_ref(
                    ordinal=index,
                    relation_ref=relation_ref,
                    model_review_result=model_review_result,
                ),
            }
        )
    return results


def _additional_semantic_materializations(
    *,
    relation_results: Sequence[Mapping[str, Any]],
    run_kernel: Any,
    run_kernel_admission_decision_status: str,
) -> list[Any]:
    materializations: list[Any] = []
    for item in relation_results:
        result = item["model_review_result"]
        if (
            result.proposal_validation_status
            != DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
        ):
            raise DPrimeMultiSourceAnalystScrutinyError(
                BLOCKED_DPRIME_MULTI_SOURCE_PRODUCT_STATUS_NOT_WIRED,
                "support-bearing multi-source relation was not proposal-validated",
            )
        decision = build_run_kernel_dprime_admission_decision(
            _safe_mapping(result.run_kernel_support_admission_request_ref),
            decision_status=run_kernel_admission_decision_status,
            rationale=(
                "product status consumed additional multi-source D-prime "
                "admission request through RunKernel-owned decision runtime"
            ),
        )
        materializations.append(
            materialize_dprime_semantic_observation_from_admitted_decision(
                decision=decision,
                assessment_material_ref=_safe_mapping(result.assessment_material_ref),
                validated_support_proposal_ref=_safe_mapping(
                    result.validated_support_proposal_ref
                ),
                fetch_read_content_packet=_safe_mapping(
                    item.get("fetch_read_content_packet")
                ),
                source_evidence_admission_ref=_materialization_ref(
                    _safe_mapping(item.get("source_evidence_admission_ref"))
                ),
                component_ref=_materialization_ref(
                    _safe_mapping(item.get("component_ref"))
                ),
                source_obligation_ref=_materialization_ref(
                    _safe_mapping(item.get("source_obligation_ref"))
                ),
                run_kernel=run_kernel,
            )
        )
    return materializations


def _additional_relation_status_ref(
    *,
    ordinal: int,
    relation_ref: Mapping[str, Any],
    model_review_result: Any,
) -> dict[str, Any]:
    return _without_empty(
        {
            "ordinal": ordinal,
            "relation_ref": dict(relation_ref),
            "model_review_status": model_review_result.model_review_status,
            "assessment_status": model_review_result.assessment_status,
            "assessment_ref": dict(model_review_result.assessment_ref),
            "assessment_material_ref": dict(
                model_review_result.assessment_material_ref
            ),
            "support_relation": model_review_result.support_relation,
            "proposal_validation_status": (
                model_review_result.proposal_validation_status
            ),
            "run_kernel_support_admission_status": (
                model_review_result.run_kernel_support_admission_status
            ),
            "product_correctness_claimed": False,
            "live_calls_run": False,
        }
    )


def _answer_path_status_ref(
    *,
    answer_path: Any,
    answer_path_error: DPrimeSingleLaneAnswerPathError | None,
    run_kernel: Any,
) -> dict[str, Any]:
    if answer_path is not None:
        ref = dict(answer_path.to_status_overlay())
        ref["status"] = "consumed"
        return ref
    kernel = run_kernel
    readiness = (
        _safe_mapping(kernel.state.sufficiency_readiness_projection)
        if kernel is not None
        else {}
    )
    fap = (
        _safe_mapping(kernel.state.final_answer_authority_projection)
        if kernel is not None
        else {}
    )
    author = (
        _safe_mapping(kernel.state.author_prose_projection)
        if kernel is not None
        else {}
    )
    display = (
        _safe_mapping(kernel.state.projections.get("dprime_citation_source_display"))
        if kernel is not None
        else {}
    )
    ref = {
        "status": "blocked" if answer_path_error is not None else "not reached",
        "sufficiency_readiness_status": readiness.get("final_readiness_status"),
        "final_answer_packet_status": fap.get("fap_status"),
        "author_answer_status": author.get("author_prose_status"),
        "citation_source_display_status": display.get("status"),
        "sufficiency_readiness_ref": {
            "readiness_id": readiness.get("readiness_id"),
            "readiness_digest": readiness.get("readiness_digest"),
            "final_readiness_status": readiness.get("final_readiness_status"),
        }
        if readiness
        else {},
        "final_answer_packet_ref": {
            "packet_id": fap.get("packet_id"),
            "packet_digest": fap.get("packet_digest") or fap.get("no_packet_digest"),
            "fap_status": fap.get("fap_status"),
            "packet_created": fap.get("packet_created"),
        }
        if fap
        else {},
        "author_answer_ref": {
            "author_prose_id": author.get("author_prose_id"),
            "author_prose_digest": author.get("author_prose_digest"),
            "author_prose_status": author.get("author_prose_status"),
        }
        if author
        else {},
        "citation_source_display_ref": {
            "display_id": display.get("display_id"),
            "display_digest": display.get("display_digest"),
            "status": display.get("status"),
            "rendered_source_count": display.get("rendered_source_count"),
        }
        if display
        else {},
    }
    if answer_path_error is not None:
        ref["blocker"] = answer_path_error.blocker
        ref["blocker_detail"] = answer_path_error.detail
        ref["next_blocked_surface"] = answer_path_error.next_surface
    return ref


def _materialization_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    """Trim product status refs to the lineage fields the materializer consumes."""

    downstream_fields = {
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
    return _drop_keys(value, downstream_fields)


def _drop_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            item_key: _drop_keys(item, keys)
            for item_key, item in value.items()
            if item_key not in keys
        }
    if isinstance(value, list | tuple):
        return [_drop_keys(item, keys) for item in value]
    return value


def _dprime_not_reached_reason(dprime: Mapping[str, Any]) -> str:
    decision = str(dprime.get("decision") or "")
    if decision == BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED:
        return "D-prime model review is not licensed, so no downstream support object exists"
    if decision in {
        BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING,
        BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED,
    }:
        return "D-prime negative-control profile is unavailable, so no downstream support object exists"
    if decision == BLOCKED_DPRIME_PREFLIGHT_FAILED:
        return "D-prime preflight failed, so no downstream support object exists"
    return "D-prime preflight is missing, so no downstream support object exists"


def _dprime_next_blocked_surface(dprime: Mapping[str, Any]) -> str:
    decision = str(dprime.get("decision") or "")
    if decision == BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED:
        return "D-prime model review"
    if decision in {
        BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING,
        BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED,
    }:
        return "D-prime negative-control profile"
    if decision == BLOCKED_DPRIME_PREFLIGHT_FAILED:
        return "D-prime EvidenceFramePreflight repair"
    return NEXT_BLOCKED_SURFACE


def _base_semantic_payload(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    support_ref: Mapping[str, Any],
    semantic_ref: Mapping[str, Any],
    coverage_ref: Mapping[str, Any],
    decision: str,
    blocker_detail: str | None,
    next_blocked_surface: str | None,
    relation_intake_ref: Mapping[str, Any] | None = None,
    workbench_dprime_dossier_ref: Mapping[str, Any] | None = None,
    candidate_handoff_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected = _safe_mapping(readiness_payload.get("selected_candidate"))
    workbench_ref = _safe_mapping(workbench_dprime_dossier_ref)
    workbench_status = _clean_text(workbench_ref.get("status"), limit=80)
    workbench_consumed = bool(
        workbench_ref and workbench_status not in {"not_provided", "not_created"}
    )
    payload = {
        "phase": PHASE,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
        "user_style_query": _clean_query(query),
        "retained_artifact_preflight_status": _preflight_status(readiness_payload),
        "retained_search_candidate_status": readiness_payload.get(
            "retained_search_candidate_status",
            "preflight_passed",
        ),
        "retained_search_candidate_count": _bounded_int(
            readiness_payload.get("retained_search_candidate_count")
        ),
        "selected_candidate": {
            "rank": selected.get("rank"),
            "domain": selected.get("domain"),
            "url": selected.get("url"),
        },
        "candidate_lineage_status": readiness_payload.get(
            "candidate_lineage_status",
            "preserved",
        ),
        "fetch_read_handoff_status": readiness_payload.get("fetch_read_handoff_status"),
        "source_evidence_admission_ref": dict(admission_ref),
        "citation_source_obligation_readiness_ref": dict(readiness_ref),
        "semantic_coverage_machinery_found": list(SEMANTIC_COVERAGE_MACHINERY_FOUND),
        "analyst_support_proposal_ref": dict(support_ref),
        "semantic_observation_admission_ref": dict(semantic_ref),
        "component_coverage_ref": dict(coverage_ref),
        "component_ref": dict(component_ref),
        "source_obligation_ref": dict(source_obligation_ref),
        "dprime_relation_intake_ref": dict(relation_intake_ref or {}),
        "generic_relation_intake_consumed_by_product_status": bool(
            relation_intake_ref
        ),
        "workbench_dprime_dossier_ref": dict(workbench_ref),
        "workbench_dprime_dossier_consumed_by_product_status": workbench_consumed,
        "dprime_candidate_handoff_integrity_ref": dict(
            _safe_mapping(candidate_handoff_ref)
        ),
        "current_source_record_dprime_candidate_handoff_ref": dict(
            _safe_mapping(candidate_handoff_ref)
        ),
        "semantic_support_source": "retained bounded sanitized content",
        "semantic_support_custody_distinction_preserved": (
            decision == PASS_DECISION
        ),
        "ad_hoc_semantic_matcher_avoided": True,
        "raw_private_retention": False,
        "closed_downstream_surfaces": CLOSED_DOWNSTREAM_SURFACES,
        "next_blocked_surface": next_blocked_surface,
        "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
        "answerability_correctness": "not claimed",
        "non_claim": EXPLICIT_NON_CLAIM,
        "decision": decision,
    }
    if blocker_detail:
        payload["blocker_detail"] = blocker_detail
    return payload


def _support_proposal_ref(
    semantic_result: RetainedCustodySemanticCoverageResult,
) -> dict[str, Any]:
    finding = _safe_mapping(semantic_result.analyst_finding)
    analysis_ref = _safe_mapping(semantic_result.analysis_packet_ref)
    return _without_empty(
        {
            "status": "proposal_created",
            "proposal_ref": _id_digest_ref(
                finding.get("finding_id"),
                finding.get("finding_digest"),
            ),
            "finding_id": finding.get("finding_id"),
            "finding_digest": finding.get("finding_digest"),
            "analysis_packet_id": analysis_ref.get("packet_id"),
            "analysis_packet_digest": analysis_ref.get("packet_digest"),
            "reference_id": finding.get("reference_id"),
            "reference_digest": finding.get("reference_digest"),
            "candidate_id": finding.get("candidate_id"),
            "candidate_digest": finding.get("candidate_digest"),
            "retained_bounded_content_ref": {
                "reference_id": finding.get("reference_id"),
                "reference_digest": finding.get("reference_digest"),
                "bounded_content_digest": finding.get("excerpt_digest"),
                "bounded_character_count": finding.get("bounded_character_count"),
            },
            "reasons": [
                "proposal created from retained bounded sanitized content",
                "source/evidence custody and component lineage preserved",
            ],
        }
    )


def _semantic_observation_ref(
    semantic_result: RetainedCustodySemanticCoverageResult,
) -> dict[str, Any]:
    ref = semantic_result.semantic_observation_ref
    return _without_empty(
        {
            "status": "admitted",
            "observation_ref": _id_digest_ref(
                ref.get("observation_id"),
                ref.get("observation_digest"),
            ),
            "observation_id": ref.get("observation_id"),
            "observation_digest": ref.get("observation_digest"),
            "content_refs": ref.get("content_refs"),
            "evidence_refs": ref.get("evidence_refs"),
            "reasons": [
                "admitted through current SemanticObservation authority",
            ],
        }
    )


def _component_coverage_ref(
    semantic_result: RetainedCustodySemanticCoverageResult,
) -> dict[str, Any]:
    ref = semantic_result.component_coverage_ref
    return _without_empty(
        {
            "status": "bound",
            "coverage_ref": _id_digest_ref(
                ref.get("coverage_record_id"),
                ref.get("coverage_record_digest"),
            ),
            "coverage_record_id": ref.get("coverage_record_id"),
            "coverage_record_digest": ref.get("coverage_record_digest"),
            "coverage_state": ref.get("coverage_state"),
            "semantic_support_status": ref.get("semantic_support_status"),
            "source_obligation_status": ref.get("source_obligation_status"),
            "reasons": [
                "bound through current ComponentCoverage authority",
                "source-obligation satisfaction remains unclaimed",
            ],
        }
    )


def _blocked_from_readiness_status(
    *,
    query: str,
    readiness_decision: str,
) -> LiveSemanticCoverageStatusResult:
    blocker = _READINESS_BLOCKER_MAP.get(
        readiness_decision,
        BLOCKED_CITATION_SOURCE_OBLIGATION_READINESS,
    )
    return _blocked_result(
        query=query,
        blocker=blocker,
        detail=f"citation/source-obligation readiness decision: {readiness_decision}",
    )


def _blocked_result(
    *,
    query: str,
    blocker: str,
    detail: str,
) -> LiveSemanticCoverageStatusResult:
    payload = {
        "phase": PHASE,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
        "user_style_query": _clean_query(query),
        "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
        "answerability_correctness": "not claimed",
        "blocker_detail": detail,
        "decision": blocker,
    }
    output = "\n".join(
        (
            "live semantic coverage status blocked",
            f"phase: {PHASE}",
            f"mode: {MODE}",
            "ordinary entrypoint: python -m proplex",
            f"status flag: {LIVE_SEMANTIC_COVERAGE_STATUS_FLAG}",
            f"user-style query: {payload['user_style_query']}",
            f"usable-answer verdict target: {USABLE_ANSWER_VERDICT_TARGET}",
            "answerability/correctness: not claimed",
            f"blocker: {blocker}",
            f"blocker detail: {detail}",
            f"next blocked surface: {NEXT_BLOCKED_SURFACE}",
            f"decision: {blocker}",
        )
    )
    return LiveSemanticCoverageStatusResult(
        decision=blocker,
        output=output,
        payload=payload,
    )


def _preflight_status(readiness_payload: Mapping[str, Any]) -> str:
    status = str(readiness_payload.get("retained_search_candidate_status") or "")
    return PASS_DECISION if status == "preflight_passed" else status or "unknown"


def _format_component_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    component_id = _component_id(ref)
    if not component_id:
        return "unavailable"
    digest = _clean_text(ref.get("current_answer_contract_digest"), limit=128)
    suffix = f"; contract_digest={digest}" if digest else ""
    coverage = (
        "coverage bound"
        if ref.get("component_coverage_bound") is True
        else "coverage not bound"
    )
    return f"{component_id} (lineage present{suffix}; {coverage})"


def _format_source_obligation_ref(value: Any) -> str:
    ids = _source_obligation_ids(_safe_mapping(value))
    if not ids:
        return "unavailable"
    return ", ".join(ids) + " (lineage present; satisfaction not claimed)"


def _format_relation_intake_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    intake_id = _clean_text(ref.get("relation_intake_id"), limit=320)
    intake_digest = _clean_text(ref.get("relation_intake_digest"), limit=128)
    if intake_id and intake_digest:
        return f"{intake_id} / {intake_digest}"
    return intake_id or intake_digest or "unavailable"


def _format_dprime_negative_control_profile_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    profile_id = _clean_text(ref.get("profile_id"), limit=260)
    profile_digest = _clean_text(ref.get("profile_digest"), limit=128)
    if profile_id and profile_digest:
        return f"{profile_id} / {profile_digest}"
    return profile_id or profile_digest or "unavailable"


def _format_dprime_model_review_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    review_id = _clean_text(ref.get("model_review_id"), limit=260)
    review_digest = _clean_text(ref.get("model_review_digest"), limit=128)
    if review_id and review_digest:
        return f"{review_id} / {review_digest}"
    return review_id or review_digest or "unavailable"


def _format_dprime_assessment_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    assessment_id = _clean_text(ref.get("assessment_id"), limit=260)
    assessment_digest = _clean_text(ref.get("assessment_digest"), limit=128)
    if assessment_id and assessment_digest:
        return f"{assessment_id} / {assessment_digest}"
    return assessment_id or assessment_digest or "unavailable"


def _format_dprime_validated_support_proposal_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    proposal_id = _clean_text(ref.get("proposal_id"), limit=260)
    proposal_digest = _clean_text(ref.get("proposal_digest"), limit=128)
    if proposal_id and proposal_digest:
        return f"{proposal_id} / {proposal_digest}"
    return proposal_id or proposal_digest or "unavailable"


def _format_dprime_run_kernel_decision_ref(value: Any) -> str:
    ref = _safe_mapping(value)
    decision_id = _clean_text(ref.get("decision_id"), limit=260)
    decision_digest = _clean_text(ref.get("decision_digest"), limit=128)
    if decision_id and decision_digest:
        return f"{decision_id} / {decision_digest}"
    return decision_id or decision_digest or "unavailable"


def _dprime_product_smart_model_route_ref(
    *,
    query: str,
    smart_provider: str | None,
    smart_model: str | None,
) -> dict[str, Any]:
    defaults = RunConfig(query=query)
    return product_smart_model_route_ref(
        smart_provider=smart_provider or defaults.smart_provider,
        smart_model=smart_model or defaults.smart_model,
    )


def _component_id(component_ref: Mapping[str, Any]) -> str | None:
    return _clean_text(component_ref.get("component_id"), limit=260)


def _source_obligation_ids(source_obligation_ref: Mapping[str, Any]) -> list[str]:
    return _text_list(source_obligation_ref.get("source_obligation_candidate_ids"))


def _resolve_root(path: str | Path) -> Path:
    return Path(path).resolve()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _id_digest_ref(identifier: Any, digest: Any) -> str:
    clean_id = _clean_text(identifier, limit=320)
    clean_digest = _clean_text(digest, limit=128)
    if clean_id and clean_digest:
        return f"{clean_id} / {clean_digest}"
    return clean_id or clean_digest or "unavailable"


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _clean_query(query: str) -> str:
    return " ".join(str(query or "").strip().split())


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false"


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, (bytes, str)) or not isinstance(value, Sequence):
        return []
    return list(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "LIVE_SEMANTIC_COVERAGE_STATUS_FLAG",
    "BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH",
    "BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED",
    "LiveSemanticCoverageStatusError",
    "LiveSemanticCoverageStatusResult",
    "build_live_semantic_coverage_status",
    "format_live_semantic_coverage_status",
    "output_hygiene_passes",
]
