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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.dprime_evidence_frame_preflight import build_evidence_frame_preflight
from core.dprime_evidence_support_bundle_runtime import (
    BLOCKED_DPRIME_COMPONENT_COVERAGE_BINDING_MISSING,
    BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_MISSING,
    BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED,
    DPrimeEvidenceSupportBundleError,
    build_dprime_evidence_support_bundle,
)
from core.dprime_model_review_assessment import run_dprime_model_review_assessment
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
    "generic D-prime analyst intake",
    "multi-component support aggregation",
    "multi-source conflict handling",
    "live/model/provider/search/fetch/read/retrieval calls",
    "old Author execution",
)
EXPLICIT_NON_CLAIM = (
    "This phase creates a narrow single-lane D-prime answer-path status only. "
    "It does not prove product correctness, generic analyst intake, live "
    "validation, or final answer quality."
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
    dprime_model_review_license: Mapping[str, Any] | None = None,
    dprime_model_review_callable: Callable[..., Any] | None = None,
    dprime_followup_search_reentry_enabled: bool = False,
    dprime_followup_candidate_results: (
        Sequence[Mapping[str, Any]] | Mapping[str, Any] | None
    ) = None,
    dprime_followup_fetch_read_materials: Sequence[Mapping[str, Any]] = (),
    dprime_followup_second_pass_model_review_callable: (
        Callable[..., Any] | None
    ) = None,
    dprime_run_kernel_admission_decision_status: str = (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    ),
) -> LiveSemanticCoverageStatusResult:
    """Consume retained status chain and return CLI-safe semantic coverage status."""

    root = _resolve_root(repo_root)
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

    evidence_frame_preflight = build_evidence_frame_preflight(
        fetch_read_content_packet=fetch_read_content_packet,
        source_evidence_admission_ref=admission_ref,
        citation_source_obligation_readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
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
        )
        if (
            dprime_followup_search_reentry_enabled
            and model_review_result.proposal_validation_status
            != DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
        ):
            followup_result = (
                run_dprime_followup_search_reentry_using_ordinary_search(
                    query=query,
                    readiness_payload=readiness_payload,
                    original_fetch_read_content_packet=fetch_read_content_packet,
                    original_source_evidence_admission_ref=admission_ref,
                    citation_source_obligation_readiness_ref=readiness_ref,
                    component_ref=component_ref,
                    source_obligation_ref=source_obligation_ref,
                    first_model_review_result=model_review_result,
                    followup_candidate_results=dprime_followup_candidate_results,
                    followup_fetch_read_materials=(
                        dprime_followup_fetch_read_materials
                    ),
                    dprime_model_review_license=dprime_model_review_license,
                    second_pass_model_review_callable=(
                        dprime_followup_second_pass_model_review_callable
                        or dprime_model_review_callable
                    ),
                    dprime_one_shot_provider_boundary=(
                        dprime_one_shot_provider_boundary
                    ),
                    dprime_one_shot_model_review_adapter=(
                        dprime_one_shot_model_review_adapter
                    ),
                    run_kernel_admission_decision_status=(
                        dprime_run_kernel_admission_decision_status
                    ),
                )
            )
            return _followup_search_reentry_result(
                query=query,
                readiness_payload=readiness_payload,
                admission_ref=admission_ref,
                readiness_ref=readiness_ref,
                component_ref=component_ref,
                source_obligation_ref=source_obligation_ref,
                followup_result=followup_result,
            )
        return _blocked_dprime_model_review_assessment_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            dprime_status=dprime_status,
            model_review_result=model_review_result,
            fetch_read_content_packet=fetch_read_content_packet,
            run_kernel_admission_decision_status=(
                dprime_run_kernel_admission_decision_status
            ),
        )
    if dprime_status.decision != PASS_DECISION:
        return _blocked_dprime_status_result(
            query=query,
            readiness_payload=readiness_payload,
            admission_ref=admission_ref,
            readiness_ref=readiness_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            dprime_status=dprime_status,
        )

    try:
        semantic_result = build_retained_custody_semantic_coverage(
            fetch_read_content_packet=fetch_read_content_packet,
            expected_candidate_id=_clean_text(admission_ref.get("candidate_id"), limit=320),
            expected_reference_id=_clean_text(admission_ref.get("reference_id"), limit=320),
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
    dprime_status: DPrimeStatusPayload,
) -> LiveSemanticCoverageStatusResult:
    dprime = dprime_status.to_dict()
    not_reached_reason = _dprime_not_reached_reason(dprime)
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
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
    dprime_status: DPrimeStatusPayload,
    model_review_result: Any,
    fetch_read_content_packet: Mapping[str, Any],
    run_kernel_admission_decision_status: str,
) -> LiveSemanticCoverageStatusResult:
    dprime = dprime_status.to_dict()
    dprime.update(model_review_result.to_status_overlay())
    objects_created = dict(dprime.get("objects_created") or {})
    objects_created.update(model_review_result.objects_created)
    dprime["objects_created"] = objects_created
    proposal_validated = (
        dprime.get("proposal_validation_status")
        == DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    decision = None
    semantic_materialization = None
    support_bundle = None
    answer_path = None
    answer_path_error = None
    support_bundle_error = None
    materialization_error = None
    contract_authority = None
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
                try:
                    support_bundle = build_dprime_evidence_support_bundle(
                        semantic_materialization=semantic_materialization,
                        run_kernel=contract_authority.run_kernel,
                        source_obligation_ref=_materialization_ref(
                            source_obligation_ref
                        ),
                        citation_source_obligation_readiness_ref=(
                            _materialization_ref(readiness_ref)
                        ),
                    )
                    dprime.update(support_bundle.to_status_overlay())
                    objects_created["component_coverage"] = True
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
                next_surface = "SufficiencyReadiness"
        elif support_bundle_error is not None:
            coverage_ref = {
                "status": "blocked",
                "coverage_ref": "unavailable",
                "component_id": _component_id(component_ref),
                "reasons": [
                    "ComponentCoverage binding failed before source/citation authority",
                    support_bundle_error.detail,
                ],
            }
            payload_decision = support_bundle_error.blocker
            payload_detail = support_bundle_error.detail
            next_surface = "D-prime ComponentCoverage binding"
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
                "D-prime proposal candidate is not admitted support",
                (
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
            materialization_error.blocker
            if materialization_error is not None
            else decision.blocker
            if decision is not None
            else model_review_result.decision
        )
        payload_detail = (
            materialization_error.detail
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
        decision=payload_decision,
        blocker_detail=payload_detail,
        next_blocked_surface=next_surface,
    )
    payload.update(
        {
            "dprime_status": dprime,
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
            "analyst_support_proposal_consumer": (
                (
                    "D-prime proposal candidate validated; RunKernel-owned "
                    "admission decision made"
                )
                if proposal_validated
                else f"not reached; {model_review_result.blocker_detail}"
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
    followup_result: Any,
) -> LiveSemanticCoverageStatusResult:
    payload = _base_semantic_payload(
        query=query,
        readiness_payload=readiness_payload,
        admission_ref=admission_ref,
        readiness_ref=readiness_ref,
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        support_ref=followup_result.support_ref,
        semantic_ref=followup_result.semantic_ref,
        coverage_ref=followup_result.coverage_ref,
        decision=followup_result.decision,
        blocker_detail=followup_result.blocker_detail,
        next_blocked_surface=followup_result.next_blocked_surface,
    )
    payload.update(
        {
            "dprime_status": dict(followup_result.dprime_status),
            "dprime_followup_search_reentry_ref": dict(
                followup_result.projection
            ),
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


def _model_review_next_blocked_surface(decision: str) -> str:
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
) -> dict[str, Any]:
    selected = _safe_mapping(readiness_payload.get("selected_candidate"))
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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "LIVE_SEMANTIC_COVERAGE_STATUS_FLAG",
    "LiveSemanticCoverageStatusError",
    "LiveSemanticCoverageStatusResult",
    "build_live_semantic_coverage_status",
    "format_live_semantic_coverage_status",
    "output_hygiene_passes",
]
