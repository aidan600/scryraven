"""RunKernel-owned D-prime follow-up search re-entry through ordinary search.

This BUILD runtime consumes a D-prime follow-up need, authorizes it through the
existing follow-up authorization reducer, re-enters ordinary SearchPlanner,
SearchExecutorHandoff, live-search-validation, SearchResultCandidatePacket, and
fetch/read packet seams, then feeds the re-entered bounded evidence back into
the existing D-prime second-pass support/answer path.

It does not let D-prime dispatch search, create a new search subsystem, run
live/provider/model/search/fetch/read/retrieval calls, retain raw/private
payloads, or claim product correctness.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.analysis_gap_followup_search_packet import (
    build_followup_search_intent_packet,
    followup_search_intent_packet_ref_from_packet,
)
from core.dprime_evidence_frame_preflight import build_evidence_frame_preflight
from core.dprime_evidence_support_bundle_runtime import (
    DPrimeEvidenceSupportBundleError,
    build_dprime_evidence_support_bundle,
)
from core.dprime_model_review_assessment import run_dprime_model_review_assessment
from core.dprime_ordinary_contract_authority_runtime import (
    DPrimeOrdinaryContractAuthorityError,
    build_dprime_ordinary_contract_authority,
)
from core.dprime_runkernel_admission_runtime import (
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    build_run_kernel_dprime_admission_decision,
)
from core.dprime_semantic_observation_materialization_runtime import (
    DPrimeSemanticObservationMaterializationError,
    materialize_dprime_semantic_observation_from_admitted_decision,
)
from core.dprime_single_lane_answer_path_runtime import (
    DPrimeSingleLaneAnswerPathError,
    build_dprime_single_lane_answer_path,
)
from core.dprime_support_proposal_schema import (
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
    build_dprime_status_payload,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (
    build_evidence_relative_analysis_packet,
    evidence_relative_analysis_packet_ref_from_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)
from core.followup_search_authorization_runtime import (
    build_followup_search_authorization_observation_payload,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    build_live_search_validation_observation_payload,
)
from core.live_search_validation_runtime import (
    contract_ref_from_contract as live_contract_ref_from_contract,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (
    SearchExecutorHandoffInput,
    execute_search_executor_handoff_action,
    handoff_ref_from_handoff_state,
    planner_ref_from_search_planner_state,
)
from core.search_executor_handoff_runtime import (
    contract_ref_from_contract as handoff_contract_ref_from_contract,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)
from core.search_result_candidate_packet import (
    build_search_result_candidate_packet_from_live_validation_state,
    search_result_candidate_packet_ref_from_packet,
    validate_search_result_candidate_packet,
)

RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_PHASE = (
    "RUN-KERNEL-FOLLOWUP-SEARCH-REENTRY-USING-ORDINARY-SEARCH-01"
)
RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_MODE = "BUILD"
RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_TRACE_KEY = (
    "runkernel_followup_search_reentry_ordinary_search"
)
RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_OWNER = (
    "RunKernel.FollowupSearchReentryOrdinarySearch"
)

PASS_DECISION = "PASS"
BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING = (
    "BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING"
)
BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH = (
    "BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH"
)
BLOCKED_DPRIME_SECOND_PASS_REEVALUATION = "BLOCKED_DPRIME_SECOND_PASS_REEVALUATION"
BLOCKED_DPRIME_FOLLOWUP_ANSWER_PATH = "BLOCKED_DPRIME_FOLLOWUP_ANSWER_PATH"

DEFAULT_PROVIDER_AUTHORIZED = "fixture_followup_search"
_MAX_RESULTS_PER_TASK = 5

_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
_SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"
_SEARCH_REQUIREMENT_ID = "searchreq:dprime-followup-reentry-current-source"

_FALSE_SURFACES = {
    "dprime_dispatched_search": False,
    "new_search_subsystem_created": False,
    "provider_called": False,
    "broker_called": False,
    "live_provider_called": False,
    "model_called_by_followup_loop": False,
    "live_search_called": False,
    "fetch_read_executed": False,
    "read_executed": False,
    "retrieval_executed": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_page_content_retained": False,
    "raw_page_text_retained": False,
    "raw_prompt_retained": False,
    "product_correctness_claimed": False,
}


class RunKernelFollowupSearchReentryError(ValueError):
    """Raised when the follow-up re-entry loop fails closed."""

    def __init__(
        self,
        blocker: str,
        detail: str,
        *,
        first_failed_seam: str,
        next_surface: str = "RunKernel follow-up search re-entry",
    ) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail
        self.first_failed_seam = first_failed_seam
        self.next_surface = next_surface


@dataclass(frozen=True, slots=True)
class RunKernelFollowupSearchReentryResult:
    """Product-status data for the follow-up search re-entry loop."""

    decision: str
    blocker_detail: str | None
    next_blocked_surface: str | None
    projection: Mapping[str, Any]
    dprime_status: Mapping[str, Any]
    support_ref: Mapping[str, Any]
    semantic_ref: Mapping[str, Any]
    coverage_ref: Mapping[str, Any]
    source_obligation_authority_ref: Mapping[str, Any]
    citation_eligibility_authority_ref: Mapping[str, Any]
    answer_path_ref: Mapping[str, Any]
    semantic_support_source: str
    contract_authority_ref: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return self.decision == PASS_DECISION


@dataclass(frozen=True, slots=True)
class _FollowupPlannerAdapter:
    """Deterministic adapter that converts authorized follow-up work into planner refs."""

    query_text: str
    component_id: str
    source_obligation_id: str
    search_requirement_id: str
    followup_authorization_ref: Mapping[str, Any]

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        query_ref = _safe_mapping(planner_input.get("user_query_ref"))
        return {
            "question_meaning_summary": (
                "Prepare one ordinary search handoff for a RunKernel-authorized "
                "D-prime follow-up evidence need."
            ),
            "requested_output": (
                "SearchResultCandidate records for second-pass D-prime review; "
                "no answer text."
            ),
            "semantic_slots": [
                {
                    "slot_id": "slot:dprime-followup-official-current-source",
                    "slot_kind": "source_basis",
                    "status": "explicit",
                    "selected_value": "RunKernel-authorized follow-up source candidate",
                    "materiality": "material",
                }
            ],
            "answer_components": [
                {
                    "component_id": self.component_id,
                    "component_revision": "dprime-followup-1",
                    "user_facing_label": "Adult U.S. passport book renewal fee",
                    "user_facing_question": self.query_text,
                    "requirement_posture": "required",
                    "acceptance_criteria": [
                        "discover a bounded source candidate for second-pass D-prime support review",
                        "do not answer from search snippets or candidates",
                    ],
                    "semantic_slot_ids": [
                        "slot:dprime-followup-official-current-source"
                    ],
                    "source_obligation_candidate_ids": [self.source_obligation_id],
                    "allowed_support_kinds": ["direct"],
                    "max_inference_depth": 0,
                    "mandatory_caveats": [
                        "Follow-up search candidates are not semantic support."
                    ],
                    "prohibited_upgrades": [
                        "Do not claim source-obligation satisfaction, citations, sufficiency, answer text, or product correctness from candidate records."
                    ],
                    "materiality": "material",
                }
            ],
            "source_obligation_candidates": [
                {
                    "candidate_id": self.source_obligation_id,
                    "obligation_kind": "official_current_source_support",
                    "component_candidate_ids": [self.component_id],
                    "strictness": "required",
                }
            ],
            "component_search_requirements": [
                {
                    "component_id": self.component_id,
                    "requirement_id": self.search_requirement_id,
                    "requirement_summary": self.query_text,
                    "source_obligation_candidate_ids": [self.source_obligation_id],
                    "preferred_source_kinds": ["official", "primary", "canonical"],
                    "recency_requirement": "current official source required",
                    "metadata": {
                        "followup_authorization_ref": dict(
                            self.followup_authorization_ref
                        ),
                        "run_kernel_followup_owner": True,
                    },
                }
            ],
            "material_ambiguity_posture": "clear",
            "mandatory_caveats": [
                "RunKernel owns follow-up search authorization and re-entry."
            ],
            "prohibited_upgrades": [
                "D-prime follow-up needs cannot dispatch search.",
                "No live provider, fetch/read, retrieval, citation, FAP, Author, or product-correctness claim is made here.",
            ],
            "normalization_obligations": [
                "Treat the authorized follow-up query as ordinary search direction only."
            ],
            "unsupported_outputs": [
                "The planner does not create support, citations, answer text, or correctness."
            ],
            "planner_model_metadata": {
                "provider": "deterministic_runkernel_followup_search_reentry_adapter",
                "model_adapter_enabled": False,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "provider_payload_retained": False,
                "prompt_hash": query_ref.get("digest"),
                "front_half_source": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_PHASE,
            },
        }


def run_dprime_followup_search_reentry_using_ordinary_search(
    *,
    query: str,
    readiness_payload: Mapping[str, Any],
    original_fetch_read_content_packet: Mapping[str, Any],
    original_source_evidence_admission_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    first_model_review_result: Any,
    followup_candidate_results: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
    followup_fetch_read_materials: Sequence[Mapping[str, Any]],
    dprime_model_review_license: Mapping[str, Any] | None,
    second_pass_model_review_callable: Callable[..., Any] | None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None = None,
    dprime_one_shot_model_review_adapter: Any | None = None,
    run_kernel_admission_decision_status: str = (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    ),
    provider_authorized: str = DEFAULT_PROVIDER_AUTHORIZED,
) -> RunKernelFollowupSearchReentryResult:
    """Run one default-off D-prime follow-up loop through ordinary search."""

    base = _base_projection()
    try:
        if second_pass_model_review_callable is None:
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up re-entry requires an injected second-pass D-prime review callable",
                first_failed_seam="second_pass_model_review_callable_missing",
                next_surface="D-prime second-pass model review",
            )
        normalized_results = _normalize_candidate_results(followup_candidate_results)
        if not followup_fetch_read_materials:
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up re-entry requires sanitized fetch/read material for candidate re-entry",
                first_failed_seam="followup_fetch_read_materials_missing",
                next_surface="fetch/read content packet re-entry",
            )

        contract_authority = build_dprime_ordinary_contract_authority(
            fetch_read_content_packet=original_fetch_read_content_packet,
            source_evidence_admission_ref=_materialization_ref(
                original_source_evidence_admission_ref
            ),
            component_ref=_materialization_ref(component_ref),
            source_obligation_ref=_materialization_ref(source_obligation_ref),
        )
        run_kernel = contract_authority.run_kernel
        current_contract = run_kernel.state.current_answer_contract
        contract_ref = planner_contract_ref_from_contract(
            current_contract,
            source="current_answer_contract",
        )
        if not contract_ref:
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH,
                "D-prime contract authority did not create current answer contract",
                first_failed_seam="dprime_contract_authority_missing_current_contract",
            )

        initial_ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
            run_kernel=run_kernel,
            fetch_read_content_packet=original_fetch_read_content_packet,
            observation_id=(
                f"{run_kernel.state.run_id}:evidence-ledger:dprime-followup-trigger"
            ),
        )
        analysis_packet = build_evidence_relative_analysis_packet(
            evidence_ledger_projection=initial_ledger_projection,
            analyst_proposal_records=[
                _dprime_gap_proposal(
                    first_model_review_result=first_model_review_result,
                    query=query,
                    fetch_read_content_packet=original_fetch_read_content_packet,
                    component_ref=component_ref,
                    source_obligation_ref=source_obligation_ref,
                )
            ],
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            current_answer_contract_ref=contract_ref,
            current_answer_contract_digest=contract_ref.get("contract_digest"),
        )
        followup_intent_packet = build_followup_search_intent_packet(
            evidence_relative_analysis_packet=analysis_packet,
            current_answer_contract_ref=contract_ref,
            current_answer_contract_digest=contract_ref.get("contract_digest"),
            mode_budget_hints={"mode": "Balanced", "max_loops": 1},
        )
        authorization_action = run_kernel.authorize_followup_search(
            followup_search_intent_packet=followup_intent_packet,
            mode="Balanced",
            logical_depth=1,
            new_evidence_expected=True,
        )
        authorization_payload = build_followup_search_authorization_observation_payload(
            action_id=authorization_action.action_id,
            action_inputs=authorization_action.inputs,
        )
        run_kernel.reduce(
            Observation.from_action(
                authorization_action,
                observation_type=ObservationType.FOLLOWUP_SEARCH_AUTHORIZED,
                status=RunStageStatus.COMPLETED,
                payload=authorization_payload,
            )
        )
        authorization_projection = _safe_mapping(
            run_kernel.state.projections.get("followup_search_authorization")
        )
        query_text = _authorized_query_text(authorization_action.inputs)

        _reduce_followup_search_planner(
            run_kernel=run_kernel,
            query_text=query_text,
            component_id=_component_id(component_ref),
            source_obligation_id=_source_obligation_id(source_obligation_ref),
            followup_authorization_ref=_authorization_ref(authorization_action.inputs),
        )
        _reduce_followup_search_executor_handoff(
            run_kernel=run_kernel,
            provider_authorized=provider_authorized,
            results_per_task_cap=len(normalized_results),
        )
        selected_task_ids = _selected_task_ids(run_kernel.state.search_executor_handoff_state)
        live_action = run_kernel.authorize_live_search_validation(
            selected_search_task_ids=selected_task_ids,
            provider_authorized=provider_authorized,
            provider_call_cap=1,
            results_per_task_cap=min(_MAX_RESULTS_PER_TASK, len(normalized_results)),
            parent_current_contract_version=current_contract[
                "accepted_contract_version"
            ],
            parent_current_contract_digest=current_contract[
                "accepted_contract_digest"
            ],
            handoff_id=run_kernel.state.search_executor_handoff_state["handoff_id"],
            handoff_digest=run_kernel.state.search_executor_handoff_state[
                "handoff_digest"
            ],
        )
        live_payload = build_live_search_validation_observation_payload(
            action=live_action,
            current_answer_contract=current_contract,
            search_executor_handoff_state=run_kernel.state.search_executor_handoff_state,
            provider_used=provider_authorized,
            provider_results_by_task={selected_task_ids[0]: normalized_results},
            execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
            broker_invoked=False,
            live_provider_called=False,
        )
        run_kernel.reduce(
            Observation.from_action(
                live_action,
                observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
                status=RunStageStatus.COMPLETED,
                payload=live_payload,
            )
        )
        candidate_packet = validate_search_result_candidate_packet(
            build_search_result_candidate_packet_from_live_validation_state(
                run_kernel.state.live_search_validation_state
            )
        )
        followup_fetch_packet = validate_fetch_read_content_packet(
            build_fetch_read_content_packet_from_candidate_packet(
                candidate_packet,
                _bind_fetch_read_materials(
                    followup_fetch_read_materials,
                    candidate_packet=candidate_packet,
                ),
            )
        )
        followup_admission_ref = _source_evidence_admission_ref(followup_fetch_packet)
        followup_preflight = build_evidence_frame_preflight(
            fetch_read_content_packet=followup_fetch_packet,
            source_evidence_admission_ref=followup_admission_ref,
            citation_source_obligation_readiness_ref=(
                citation_source_obligation_readiness_ref
            ),
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
        )
        second_dprime_status = build_dprime_status_payload(
            evidence_frame_preflight=followup_preflight,
            one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        )
        second_result = run_dprime_model_review_assessment(
            evidence_frame_preflight=followup_preflight.to_dict(),
            fetch_read_content_packet=followup_fetch_packet,
            source_evidence_admission_ref=followup_admission_ref,
            citation_source_obligation_readiness_ref=(
                citation_source_obligation_readiness_ref
            ),
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            negative_control_profile_ref=(
                second_dprime_status.negative_control_profile_ref
            ),
            assessment_validator_status=(
                second_dprime_status.assessment_validator_status
            ),
            license=dprime_model_review_license,
            model_review_callable=second_pass_model_review_callable,
            one_shot_provider_boundary=dprime_one_shot_provider_boundary,
            one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
        )

        return _finish_second_pass(
            base={
                **base,
                "ran": True,
                "status": "ordinary_search_reentry_consumed",
                "failed_closed": False,
                "accepted_current_answer_contract_authority_ref": dict(
                    contract_authority.authority_ref
                ),
                "initial_evidence_relative_analysis_packet_ref": (
                    evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
                ),
                "followup_search_intent_packet_ref": (
                    followup_search_intent_packet_ref_from_packet(
                        followup_intent_packet
                    )
                ),
                "followup_search_authorization_ref": _authorization_ref(
                    authorization_action.inputs
                ),
                "followup_search_authorization_status": "consumed",
                "followup_authorization_projection_ref": _authorization_projection_ref(
                    authorization_projection
                ),
                "ordinary_search_planner_status": "consumed",
                "search_planner_proposal_ref": planner_ref_from_search_planner_state(
                    run_kernel.state.search_planner_proposal_state
                ),
                "ordinary_search_executor_handoff_status": "consumed",
                "search_executor_handoff_ref": handoff_ref_from_handoff_state(
                    run_kernel.state.search_executor_handoff_state
                ),
                "ordinary_live_search_validation_status": "consumed",
                "live_search_validation_ref": _live_search_validation_ref(
                    run_kernel.state.live_search_validation_state
                ),
                "search_result_candidate_packet_status": "created",
                "search_result_candidate_packet_ref": (
                    search_result_candidate_packet_ref_from_packet(candidate_packet)
                ),
                "fetch_read_content_packet_status": "created",
                "fetch_read_content_packet_ref": fetch_read_content_packet_ref_from_packet(
                    followup_fetch_packet
                ),
                "followup_source_evidence_admission_status": (
                    followup_admission_ref.get("status")
                ),
                "followup_source_evidence_admission_ref": _admission_public_ref(
                    followup_admission_ref
                ),
                "evidence_reentry_status": "consumed",
                "second_dprime_pass_status": "consumed",
                "second_dprime_preflight_status": (
                    followup_preflight.preflight_status
                ),
                "selected_search_task_ids": selected_task_ids,
                "provider_authorized": provider_authorized,
                "structured_candidate_input_count": len(normalized_results),
                **_FALSE_SURFACES,
            },
            second_dprime_status=second_dprime_status.to_dict(),
            second_model_review_result=second_result,
            followup_fetch_packet=followup_fetch_packet,
            followup_admission_ref=followup_admission_ref,
            component_ref=component_ref,
            source_obligation_ref=source_obligation_ref,
            citation_source_obligation_readiness_ref=(
                citation_source_obligation_readiness_ref
            ),
            run_kernel=run_kernel,
            contract_authority_ref=contract_authority.authority_ref,
            run_kernel_admission_decision_status=(
                run_kernel_admission_decision_status
            ),
        )
    except RunKernelFollowupSearchReentryError as exc:
        return _failed_result(base, exc)
    except (
        DPrimeOrdinaryContractAuthorityError,
        DPrimeEvidenceSupportBundleError,
        DPrimeSemanticObservationMaterializationError,
        DPrimeSingleLaneAnswerPathError,
        RunKernelTransitionError,
        TypeError,
        ValueError,
        KeyError,
    ) as exc:
        return _failed_result(
            base,
            RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH,
                str(exc),
                first_failed_seam="ordinary_search_reentry_exception",
            ),
        )


def _finish_second_pass(
    *,
    base: Mapping[str, Any],
    second_dprime_status: Mapping[str, Any],
    second_model_review_result: Any,
    followup_fetch_packet: Mapping[str, Any],
    followup_admission_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    citation_source_obligation_readiness_ref: Mapping[str, Any],
    run_kernel: Any,
    contract_authority_ref: Mapping[str, Any],
    run_kernel_admission_decision_status: str,
) -> RunKernelFollowupSearchReentryResult:
    dprime = dict(second_dprime_status)
    dprime.update(second_model_review_result.to_status_overlay())
    objects_created = dict(dprime.get("objects_created") or {})
    objects_created.update(second_model_review_result.objects_created)
    dprime["objects_created"] = objects_created
    proposal_validated = (
        dprime.get("proposal_validation_status")
        == DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    support_ref = _support_ref(dprime, proposal_validated)
    if not proposal_validated:
        projection = {
            **dict(base),
            "status": "second_dprime_pass_blocked",
            "failed_closed": True,
            "first_failed_seam": "dprime_second_pass_support_not_validated",
            "second_dprime_pass_status": "blocked",
        }
        return RunKernelFollowupSearchReentryResult(
            decision=second_model_review_result.decision,
            blocker_detail=second_model_review_result.blocker_detail,
            next_blocked_surface="D-prime second-pass support validation",
            projection=_without_empty(projection),
            dprime_status=dprime,
            support_ref=support_ref,
            semantic_ref=_unavailable_semantic_ref(
                second_model_review_result.blocker_detail
            ),
            coverage_ref=_unavailable_coverage_ref(component_ref),
            source_obligation_authority_ref={"status": "not reached"},
            citation_eligibility_authority_ref={"status": "not reached"},
            answer_path_ref={"status": "not reached"},
            semantic_support_source=(
                "unavailable; D-prime second-pass assessment is not support"
            ),
            contract_authority_ref=contract_authority_ref,
        )

    decision = build_run_kernel_dprime_admission_decision(
        _safe_mapping(dprime.get("run_kernel_support_admission_request_ref")),
        decision_status=run_kernel_admission_decision_status,
        rationale=(
            "RunKernel-owned follow-up search re-entry consumed ordinary search "
            "before second-pass D-prime support admission"
        ),
    )
    dprime.update(decision.to_status_overlay())
    objects_created["run_kernel_admission_decision"] = True
    dprime["objects_created"] = objects_created
    if decision.decision_status != DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED:
        return RunKernelFollowupSearchReentryResult(
            decision=decision.blocker,
            blocker_detail=decision.blocker_detail,
            next_blocked_surface="D-prime RunKernel support admission decision",
            projection=_without_empty(
                {
                    **dict(base),
                    "status": "second_dprime_pass_admission_blocked",
                    "failed_closed": True,
                    "first_failed_seam": "dprime_run_kernel_admission_decision",
                }
            ),
            dprime_status=dprime,
            support_ref=support_ref,
            semantic_ref=_unavailable_semantic_ref(decision.blocker_detail),
            coverage_ref=_unavailable_coverage_ref(component_ref),
            source_obligation_authority_ref={"status": "not reached"},
            citation_eligibility_authority_ref={"status": "not reached"},
            answer_path_ref={"status": "not reached"},
            semantic_support_source="unavailable; D-prime support was not admitted",
            contract_authority_ref=contract_authority_ref,
        )

    try:
        semantic_materialization = (
            materialize_dprime_semantic_observation_from_admitted_decision(
                decision=decision,
                assessment_material_ref=_safe_mapping(
                    dprime.get("assessment_material_ref")
                ),
                validated_support_proposal_ref=_safe_mapping(
                    dprime.get("validated_support_proposal_ref")
                ),
                fetch_read_content_packet=followup_fetch_packet,
                source_evidence_admission_ref=_materialization_ref(
                    followup_admission_ref
                ),
                component_ref=_materialization_ref(component_ref),
                source_obligation_ref=_materialization_ref(source_obligation_ref),
                run_kernel=run_kernel,
            )
        )
        dprime.update(semantic_materialization.to_status_overlay())
        objects_created["semantic_observation"] = True
        support_bundle = build_dprime_evidence_support_bundle(
            semantic_materialization=semantic_materialization,
            run_kernel=run_kernel,
            source_obligation_ref=_materialization_ref(source_obligation_ref),
            citation_source_obligation_readiness_ref=_materialization_ref(
                citation_source_obligation_readiness_ref
            ),
        )
        dprime.update(support_bundle.to_status_overlay())
        objects_created["component_coverage"] = True
        answer_path = build_dprime_single_lane_answer_path(
            support_bundle=support_bundle,
            run_kernel=run_kernel,
        )
        dprime.update(answer_path.to_status_overlay())
        objects_created["sufficiency_readiness"] = True
        objects_created["final_answer_packet"] = True
        objects_created["author_answer"] = True
        objects_created["citation_source_display"] = True
        dprime["objects_created"] = objects_created
        answer_path_ref = dict(answer_path.to_status_overlay())
        answer_path_ref["status"] = "consumed"
        return RunKernelFollowupSearchReentryResult(
            decision=PASS_DECISION,
            blocker_detail=None,
            next_blocked_surface=None,
            projection=_without_empty(
                {
                    **dict(base),
                    "status": "ordinary_search_reentry_to_answer_path_consumed",
                    "second_pass_answer_path_status": "consumed",
                    "semantic_observation_status": "consumed",
                    "component_coverage_status": "consumed",
                    "source_obligation_authority_status": (
                        support_bundle.source_obligation_authority_ref.get("status")
                    ),
                    "citation_eligibility_authority_status": (
                        support_bundle.citation_eligibility_authority_ref.get(
                            "status"
                        )
                    ),
                }
            ),
            dprime_status=dprime,
            support_ref=support_ref,
            semantic_ref=semantic_materialization.semantic_status_ref(),
            coverage_ref=support_bundle.component_coverage_ref,
            source_obligation_authority_ref=(
                support_bundle.source_obligation_authority_ref
            ),
            citation_eligibility_authority_ref=(
                support_bundle.citation_eligibility_authority_ref
            ),
            answer_path_ref=answer_path_ref,
            semantic_support_source=(
                "available from D-prime second-pass SemanticObservation and "
                "bound ComponentCoverage after RunKernel-owned follow-up "
                "ordinary search re-entry; source-obligation and "
                "citation-source handoff authority consumed; single-lane answer "
                "path consumed"
            ),
            contract_authority_ref=contract_authority_ref,
        )
    except (
        DPrimeSemanticObservationMaterializationError,
        DPrimeEvidenceSupportBundleError,
        DPrimeSingleLaneAnswerPathError,
    ) as exc:
        blocker = getattr(exc, "blocker", BLOCKED_DPRIME_FOLLOWUP_ANSWER_PATH)
        detail = getattr(exc, "detail", str(exc))
        next_surface = getattr(exc, "next_surface", "D-prime follow-up answer path")
        return RunKernelFollowupSearchReentryResult(
            decision=blocker,
            blocker_detail=detail,
            next_blocked_surface=next_surface,
            projection=_without_empty(
                {
                    **dict(base),
                    "status": "second_pass_answer_path_blocked",
                    "failed_closed": True,
                    "first_failed_seam": "dprime_followup_answer_path",
                }
            ),
            dprime_status=dprime,
            support_ref=support_ref,
            semantic_ref=_unavailable_semantic_ref(detail),
            coverage_ref=_unavailable_coverage_ref(component_ref),
            source_obligation_authority_ref={"status": "not reached"},
            citation_eligibility_authority_ref={"status": "not reached"},
            answer_path_ref={"status": "blocked", "blocker": blocker},
            semantic_support_source="unavailable; D-prime follow-up answer path blocked",
            contract_authority_ref=contract_authority_ref,
        )


def _reduce_followup_search_planner(
    *,
    run_kernel: Any,
    query_text: str,
    component_id: str,
    source_obligation_id: str,
    followup_authorization_ref: Mapping[str, Any],
) -> None:
    planner_input = SearchPlannerInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        user_query_text=query_text,
        requested_mode="balanced",
        safe_context={
            "phase": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_PHASE,
            "mode": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_MODE,
            "followup_loop_owner": "RunKernel/product",
            "dprime_dispatch_owner": False,
            "live_calls": 0,
        },
        route_context_ref={
            "route_ref": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_TRACE_KEY,
        },
        run_context_ref={
            "run_kernel_consumer": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_OWNER,
        },
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            run_kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    action = run_kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=_FollowupPlannerAdapter(
            query_text=query_text,
            component_id=component_id,
            source_obligation_id=source_obligation_id,
            search_requirement_id=_SEARCH_REQUIREMENT_ID,
            followup_authorization_ref=followup_authorization_ref,
        ),
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _reduce_followup_search_executor_handoff(
    *,
    run_kernel: Any,
    provider_authorized: str,
    results_per_task_cap: int,
) -> None:
    handoff_input = SearchExecutorHandoffInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        parent_current_contract_ref=handoff_contract_ref_from_contract(
            run_kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
        parent_initial_contract_ref=handoff_contract_ref_from_contract(
            run_kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        contract_parent_kind="current_answer_contract",
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            run_kernel.state.search_planner_proposal_state
        ),
        answer_component_refs=run_kernel.state.current_answer_contract.get(
            "accepted_answer_component_refs",
            [],
        ),
        source_obligation_candidate_refs=_source_refs_from_contract(
            run_kernel.state.current_answer_contract
        ),
        component_search_requirements=run_kernel.state.search_planner_proposal_state.get(
            "component_search_requirements",
            [],
        ),
        required_caveats=run_kernel.state.current_answer_contract.get(
            "mandatory_caveats",
            [],
        ),
        prohibited_upgrades=run_kernel.state.current_answer_contract.get(
            "prohibited_upgrades",
            [],
        ),
        query_budget={
            "max_search_tasks": 1,
            "max_results_per_task": min(_MAX_RESULTS_PER_TASK, results_per_task_cap),
        },
        allowed_verticals=["search"],
        provider_preference_hint=provider_authorized,
    )
    action = run_kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=handoff_input,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _dprime_gap_proposal(
    *,
    first_model_review_result: Any,
    query: str,
    fetch_read_content_packet: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
) -> dict[str, Any]:
    reference = _first_readable_reference(fetch_read_content_packet)
    relation = _first_pass_support_relation(first_model_review_result)
    gap_kind = _gap_kind_from_relation(relation)
    query_hint = _clean_text(query, limit=300) or (
        "official current passport fee source"
    )
    reason = _first_pass_blocker_detail(first_model_review_result) or (
        f"D-prime first pass identified follow-up need: {relation or 'non_support'}"
    )
    return {
        "proposal_kind": "analysis_gap",
        "gap_kind": gap_kind,
        "reference_id": reference.get("reference_id"),
        "candidate_id": reference.get("candidate_id"),
        "candidate_digest": reference.get("candidate_digest"),
        "reference_digest": reference.get("reference_digest"),
        "component_id": _component_id(component_ref),
        "source_obligation_candidate_ids": _source_obligation_ids(
            source_obligation_ref
        ),
        "reason": reason,
        "information_needed": (
            "Find a bounded official/current source that can resolve the "
            f"D-prime {relation or 'non-support'} judgment."
        ),
        "proposed_search_direction": (
            "Search for an official/current source for the D-prime follow-up "
            "need; return candidate records only."
        ),
        "proposed_query_hint": query_hint,
        "required_source_class_hint": _source_class_hint(gap_kind),
        "required_source_tier_hint": "primary_or_official",
        "required_currentness_hint": "current",
        "priority_hint": "high",
        "budget_hint": {"max_search_tasks": 1, "max_results_per_task": 1},
    }


def _failed_result(
    base: Mapping[str, Any],
    exc: RunKernelFollowupSearchReentryError,
) -> RunKernelFollowupSearchReentryResult:
    projection = {
        **dict(base),
        "ran": True,
        "status": "failed_closed",
        "failed_closed": True,
        "first_failed_seam": exc.first_failed_seam,
        "failure_reason": _clean_text(exc.detail, limit=360),
        **_FALSE_SURFACES,
    }
    return RunKernelFollowupSearchReentryResult(
        decision=exc.blocker,
        blocker_detail=exc.detail,
        next_blocked_surface=exc.next_surface,
        projection=_without_empty(projection),
        dprime_status={},
        support_ref={"status": "not reached", "proposal_ref": "unavailable"},
        semantic_ref=_unavailable_semantic_ref(exc.detail),
        coverage_ref=_unavailable_coverage_ref({}),
        source_obligation_authority_ref={"status": "not reached"},
        citation_eligibility_authority_ref={"status": "not reached"},
        answer_path_ref={"status": "not reached"},
        semantic_support_source="unavailable; follow-up search re-entry failed closed",
        contract_authority_ref={},
    )


def _base_projection() -> dict[str, Any]:
    return {
        "trace_key": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_TRACE_KEY,
        "phase": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_PHASE,
        "mode": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_MODE,
        "owner": RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_OWNER,
        "enabled": True,
        "ran": False,
        "failed_closed": False,
        "status": "not_run",
        "product_path_affected": (
            "python -m proplex --live-semantic-coverage-status-dry-run"
        ),
        "followup_loop_owner": "RunKernel/product",
        "dprime_followup_need_owner": "D-prime",
        "dprime_dispatch_owner": False,
        "ordinary_search_path_reused": True,
        "new_search_subsystem_created": False,
        "followup_search_authorization_consumed": True,
        "ordinary_search_planner_consumed": True,
        "ordinary_search_executor_handoff_consumed": True,
        "ordinary_live_search_validation_consumed": True,
        "search_result_candidate_packet_consumed": True,
        "fetch_read_content_packet_consumed": True,
        "dprime_second_pass_consumed": True,
        "answer_path_consumed_when_second_pass_supports": True,
        "live_execution_closed": True,
        "fixture_or_offline_reentry_only": True,
        "explicit_non_claim": (
            "No live/product correctness claim is made by follow-up search re-entry."
        ),
        "closed_surface_flags": dict(_FALSE_SURFACES),
        **_FALSE_SURFACES,
    }


def _support_ref(dprime: Mapping[str, Any], proposal_validated: bool) -> dict[str, Any]:
    proposal_ref = _safe_mapping(dprime.get("validated_support_proposal_ref"))
    if proposal_validated:
        return {
            "status": DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            "proposal_ref": _id_digest_ref(
                proposal_ref.get("proposal_id"),
                proposal_ref.get("proposal_digest"),
            ),
            "reasons": [
                "D-prime second-pass proposal validated after follow-up ordinary search re-entry"
            ],
        }
    return {
        "status": "not reached",
        "proposal_ref": "unavailable",
        "reasons": [_clean_text(dprime.get("blocker_detail"), limit=500)],
    }


def _unavailable_semantic_ref(detail: str | None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "observation_ref": "unavailable",
        "reasons": [
            _clean_text(detail, limit=500)
            or "D-prime follow-up did not produce admitted semantic support"
        ],
    }


def _unavailable_coverage_ref(component_ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "coverage_ref": "unavailable",
        "component_id": _component_id(component_ref),
        "reasons": ["ComponentCoverage requires admitted SemanticObservation"],
    }


def _normalize_candidate_results(
    value: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    if value is None:
        raise RunKernelFollowupSearchReentryError(
            BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
            "follow-up re-entry enabled without structured candidate results",
            first_failed_seam="followup_candidate_results_missing",
        )
    raw_results: Any = value.get("results") if isinstance(value, Mapping) else value
    if isinstance(raw_results, str | bytes) or not isinstance(raw_results, Sequence):
        raise RunKernelFollowupSearchReentryError(
            BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
            "follow-up candidate results must be a sequence of mappings",
            first_failed_seam="followup_candidate_results_invalid",
        )
    if not raw_results:
        raise RunKernelFollowupSearchReentryError(
            BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
            "follow-up candidate results are empty",
            first_failed_seam="followup_candidate_results_empty",
        )
    out: list[dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, Mapping):
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up candidate result must be a mapping",
                first_failed_seam="followup_candidate_results_invalid",
            )
        result = _safe_mapping(raw)
        if not _clean_text(result.get("title"), limit=220):
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up candidate result requires title",
                first_failed_seam="followup_candidate_result_title_missing",
            )
        if not _clean_text(result.get("url") or result.get("link"), limit=700):
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up candidate result requires url",
                first_failed_seam="followup_candidate_result_url_missing",
            )
        out.append(result)
    if len(out) > _MAX_RESULTS_PER_TASK:
        raise RunKernelFollowupSearchReentryError(
            BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
            "follow-up candidate result count exceeds offline validation cap",
            first_failed_seam="followup_candidate_result_count_exceeds_cap",
        )
    return tuple(out)


def _bind_fetch_read_materials(
    materials: Sequence[Mapping[str, Any]],
    *,
    candidate_packet: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    candidate_records = [
        _safe_mapping(item)
        for item in candidate_packet.get("candidate_records", [])
        if isinstance(item, Mapping)
    ]
    if len(materials) != len(candidate_records):
        raise RunKernelFollowupSearchReentryError(
            BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
            "follow-up fetch/read material count must match candidate count",
            first_failed_seam="followup_fetch_read_material_count_mismatch",
            next_surface="fetch/read content packet re-entry",
        )
    out: list[dict[str, Any]] = []
    for material, candidate in zip(materials, candidate_records, strict=True):
        safe = _safe_mapping(material)
        if not (
            _clean_text(safe.get("bounded_text"), limit=20_000)
            or _clean_text(safe.get("bounded_excerpt"), limit=20_000)
        ):
            raise RunKernelFollowupSearchReentryError(
                BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
                "follow-up fetch/read material requires bounded sanitized text",
                first_failed_seam="followup_fetch_read_bounded_text_missing",
                next_surface="fetch/read content packet re-entry",
            )
        out.append(
            {
                **safe,
                "candidate_id": safe.get("candidate_id")
                or candidate.get("candidate_id"),
                "candidate_digest": safe.get("candidate_digest")
                or candidate.get("candidate_digest"),
                "fetch_read_status": safe.get("fetch_read_status") or "readable",
                "attempted_url": safe.get("attempted_url") or candidate.get("url"),
                "resolved_url": safe.get("resolved_url") or candidate.get("url"),
                "final_url": safe.get("final_url") or candidate.get("url"),
                "canonical_url": safe.get("canonical_url") or candidate.get("url"),
                "resolved_domain": safe.get("resolved_domain")
                or candidate.get("domain"),
                "content_type": safe.get("content_type") or "text/html",
                "http_status": safe.get("http_status") or 200,
                "retrieved_or_observed_at": safe.get("retrieved_or_observed_at")
                or "offline-followup-reentry",
                "published_or_observed_date": safe.get("published_or_observed_date")
                or candidate.get("published_or_observed_date"),
                "content_title": safe.get("content_title")
                or safe.get("title")
                or candidate.get("title"),
                "bounded_text_sanitized": safe.get("bounded_text_sanitized", True),
                "bounded_text_bounded": safe.get("bounded_text_bounded", True),
            }
        )
    return tuple(out)


def _source_evidence_admission_ref(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
    references = [
        _safe_mapping(item)
        for item in fetch_packet.get("reference_records", [])
        if isinstance(item, Mapping)
    ]
    readable = [item for item in references if item.get("fetch_read_status") == "readable"]
    first = readable[0] if readable else references[0] if references else {}
    ref = _without_empty(
        {
            "status": "custody_created" if first else "not_admitted",
            "owner": "RunKernel.EvidenceLedger",
            "schema_version": "source_evidence_admission_ref_followup_reentry_v1",
            "trace_key": "source_evidence_admission",
            "observation_id": (
                f"source-evidence-admission:{fetch_packet.get('packet_digest', '')[:16]}"
            ),
            "observation_source": "fetch_read_candidate_custody",
            "fetch_read_content_packet_id": fetch_packet.get("packet_id"),
            "fetch_read_content_packet_digest": fetch_packet.get("packet_digest"),
            "custody_record_count": len(references),
            "readable_record_count": len(readable),
            "candidate_content_custody_visible": bool(first),
            "candidate_id": first.get("candidate_id"),
            "reference_id": first.get("reference_id"),
            "reference_digest": first.get("reference_digest"),
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
            "behavior_boundary_flags": {
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
            },
        }
    )
    ref["ref_digest"] = _digest_json(ref)
    return ref


def _admission_public_ref(admission_ref: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "status": admission_ref.get("status"),
            "fetch_read_content_packet_id": admission_ref.get(
                "fetch_read_content_packet_id"
            ),
            "fetch_read_content_packet_digest": admission_ref.get(
                "fetch_read_content_packet_digest"
            ),
            "candidate_id": admission_ref.get("candidate_id"),
            "reference_id": admission_ref.get("reference_id"),
            "reference_digest": admission_ref.get("reference_digest"),
            "custody_record_count": admission_ref.get("custody_record_count"),
            "readable_record_count": admission_ref.get("readable_record_count"),
            "candidate_content_custody_is_semantic_support": False,
            "product_correctness_claimed": False,
        }
    )


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs", []) or []:
        safe = _safe_mapping(component)
        component_id = safe.get("component_id")
        for candidate_id in safe.get("source_obligation_candidate_ids", []) or []:
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "component_candidate_ids": [component_id],
                    "obligation_kind": "official_current_source_support",
                    "strictness": "required",
                }
            )
    return refs


def _selected_task_ids(handoff_state: Mapping[str, Any]) -> list[str]:
    return [
        str(task["search_task_id"])
        for task in handoff_state.get("search_task_records", [])
        if isinstance(task, Mapping) and task.get("search_task_id")
    ][:1]


def _authorized_query_text(action_inputs: Mapping[str, Any]) -> str:
    bundle = _safe_mapping(action_inputs.get("query_bundle"))
    for query in bundle.get("queries", []) or []:
        safe = _safe_mapping(query)
        text = _clean_text(safe.get("query_text"), limit=420)
        if text:
            return text
    raise RunKernelFollowupSearchReentryError(
        BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH,
        "follow-up authorization did not produce query text",
        first_failed_seam="followup_authorization_query_missing",
    )


def _authorization_ref(action_inputs: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "authorization_id": action_inputs.get("authorization_id"),
            "authorization_digest": action_inputs.get("authorization_digest"),
            "schema_version": action_inputs.get("schema_version"),
            "query_bundle_id": _safe_mapping(action_inputs.get("query_bundle")).get(
                "query_bundle_id"
            ),
            "query_bundle_digest": _safe_mapping(action_inputs.get("query_bundle")).get(
                "query_bundle_digest"
            ),
            "authorized": action_inputs.get("followup_search_authorized") is True,
            "live_dispatch_allowed": False,
            "fixture_reentry_only": True,
        }
    )


def _authorization_projection_ref(projection: Mapping[str, Any]) -> dict[str, Any]:
    latest = _safe_mapping(projection.get("latest_authorization"))
    return _without_empty(
        {
            "authorization_id": latest.get("authorization_id"),
            "authorization_digest": latest.get("authorization_digest"),
            "authorized_loop_count": projection.get("authorized_loop_count"),
            "fixture_reentry_only": projection.get("fixture_reentry_only") is True,
            "live_dispatch_allowed": False,
        }
    )


def _live_search_validation_ref(state: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "validation_id": state.get("validation_id"),
            "validation_digest": state.get("validation_digest"),
            "schema_version": state.get("schema_version"),
            "candidate_count": state.get("candidate_count"),
            "current_answer_contract_ref": live_contract_ref_from_contract(
                state.get("parent_current_contract_ref"),
                source="current_answer_contract",
            )
            if state.get("parent_current_contract_ref", {}).get(
                "accepted_contract_version"
            )
            else state.get("parent_current_contract_ref"),
            "live_provider_called": False,
            "broker_invoked": False,
        }
    )


def _first_readable_reference(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
    for item in fetch_packet.get("reference_records", []) or []:
        reference = _safe_mapping(item)
        if reference.get("fetch_read_status") == "readable":
            return reference
    raise RunKernelFollowupSearchReentryError(
        BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING,
        "initial fetch/read packet has no readable reference for follow-up trigger",
        first_failed_seam="initial_fetch_read_reference_missing",
    )


def _first_pass_support_relation(first_model_review_result: Any) -> str | None:
    if hasattr(first_model_review_result, "support_relation"):
        return _clean_text(first_model_review_result.support_relation, limit=120)
    overlay = (
        first_model_review_result.to_status_overlay()
        if hasattr(first_model_review_result, "to_status_overlay")
        else _safe_mapping(first_model_review_result)
    )
    return _clean_text(_safe_mapping(overlay).get("support_relation"), limit=120)


def _first_pass_blocker_detail(first_model_review_result: Any) -> str | None:
    if hasattr(first_model_review_result, "blocker_detail"):
        return _clean_text(first_model_review_result.blocker_detail, limit=500)
    overlay = (
        first_model_review_result.to_status_overlay()
        if hasattr(first_model_review_result, "to_status_overlay")
        else _safe_mapping(first_model_review_result)
    )
    return _clean_text(_safe_mapping(overlay).get("blocker_detail"), limit=500)


def _gap_kind_from_relation(relation: str | None) -> str:
    if relation == "currentness_mismatch":
        return "currentness_concern"
    if relation == "scope_mismatch":
        return "scope_mismatch"
    if relation == "contradicts":
        return "possible_contradiction"
    return "missing_fact"


def _source_class_hint(gap_kind: str) -> str:
    if gap_kind == "currentness_concern":
        return "current_primary_or_official"
    if gap_kind == "possible_contradiction":
        return "comparison_or_reconciliation_source"
    if gap_kind == "scope_mismatch":
        return "scope_disambiguating_source"
    return "official_current_or_primary_source"


def _component_id(component_ref: Mapping[str, Any]) -> str:
    return (
        _clean_text(component_ref.get("component_id"), limit=260)
        or _COMPONENT_ID
    )


def _source_obligation_id(source_obligation_ref: Mapping[str, Any]) -> str:
    ids = _source_obligation_ids(source_obligation_ref)
    return ids[0] if ids else _SOURCE_OBLIGATION_ID


def _source_obligation_ids(source_obligation_ref: Mapping[str, Any]) -> list[str]:
    return _text_list(source_obligation_ref.get("source_obligation_candidate_ids"))


def _materialization_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    downstream_fields = {
        "answer_text",
        "author_answer",
        "author_input",
        "citation",
        "citation_eligibility",
        "citation_eligible",
        "component_coverage",
        "coverage",
        "final_answer_packet",
        "product_correctness",
        "semantic_observation",
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


def _digest_json(payload: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "BLOCKED_DPRIME_FOLLOWUP_ANSWER_PATH",
    "BLOCKED_DPRIME_SECOND_PASS_REEVALUATION",
    "BLOCKED_FOLLOWUP_SEARCH_REENTRY_INPUT_MISSING",
    "BLOCKED_FOLLOWUP_SEARCH_REENTRY_ORDINARY_SEARCH",
    "RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_MODE",
    "RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_OWNER",
    "RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_PHASE",
    "RUNKERNEL_FOLLOWUP_SEARCH_REENTRY_TRACE_KEY",
    "RunKernelFollowupSearchReentryResult",
    "run_dprime_followup_search_reentry_using_ordinary_search",
]
