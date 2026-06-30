"""Default-off ordinary run_pipeline live candidate handoff glue.

This module deliberately reuses the existing RunKernel-owned planner, contract,
SearchExecutorHandoff, live-search-validation, and SearchResultCandidatePacket
reducers. It performs no provider, broker, retrieval, fetch/read, model, FAP,
Author, citation, or source-obligation work.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.contract_amendment_record import (
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    UserConfirmationPosture,
    WeakeningPosture,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP,
    build_live_search_validation_observation_payload,
)
from core.live_search_validation_runtime import (
    contract_ref_from_contract as live_contract_ref_from_contract,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
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

ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY = "ordinary_live_candidate_handoff"
ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE = (
    "AG-ORDINARY-LIVE-CANDIDATE-HANDOFF-REPAIR-01"
)
ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE = "REPAIR"
DEFAULT_MAX_SEARCH_TASKS = 1
DEFAULT_PROVIDER_CALL_CAP = 1

_COMPONENT_ID = "component:ordinary-live-candidate-handoff-primary"
_SOURCE_OBLIGATION_ID = "obligation:ordinary-live-candidate-handoff-source"
_SEARCH_REQUIREMENT_ID = "searchreq:ordinary-live-candidate-handoff-primary"

_ALLOWED_CANDIDATE_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_ALLOWED_CANDIDATE_ENVELOPE_KEYS = frozenset(
    {
        "results",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)

_FALSE_CLOSED_SURFACES = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "read_executed": False,
    "retrieval_executed": False,
    "evidence_ledger_admitted": False,
    "evidence_created": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

_NON_PROOFS = (
    "no live provider/search/broker/fetch/model call",
    "no retrieval diagnostics promoted into source-candidate authority",
    "no fetch/read or source survival proof",
    "no EvidenceLedger custody from candidate results",
    "no citation eligibility or citation rendering",
    "no source-obligation satisfaction",
    "no SufficiencyReadiness or FinalAnswerPacket proof",
    "no Author or AuthorProse behavior",
    "no answer text or product correctness claim",
)


class OrdinaryLiveCandidateHandoffError(ValueError):
    """Raised internally when the default-off ordinary handoff fails closed."""

    def __init__(self, first_failed_seam: str, message: str) -> None:
        super().__init__(message)
        self.first_failed_seam = first_failed_seam


@dataclass(frozen=True, slots=True)
class OrdinaryLiveCandidateHandoffResult:
    projection: dict[str, Any]
    candidate_packet: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class _OrdinaryPlannerAdapter:
    query: str
    core_topic: str | None = None
    component_id: str = _COMPONENT_ID
    source_obligation_id: str = _SOURCE_OBLIGATION_ID
    search_requirement_id: str = _SEARCH_REQUIREMENT_ID
    planner_purpose: str = "candidate_handoff"

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_adapter_result(
            planner_input,
            query=self.query,
            core_topic=self.core_topic,
            component_id=self.component_id,
            source_obligation_id=self.source_obligation_id,
            search_requirement_id=self.search_requirement_id,
            planner_purpose=self.planner_purpose,
        )


def ordinary_live_candidate_handoff_disabled_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY,
        "phase": ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE,
        "mode": ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE,
        "enabled": False,
        "ran": False,
        "failed_closed": False,
        "status": "disabled",
        "run_pipeline_consumer": False,
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
    }


def execute_ordinary_live_candidate_handoff(
    *,
    run_kernel: RunKernel,
    query: str,
    requested_mode: str,
    run_contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None = None,
    core_topic: str | None = None,
    candidate_results: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
    provider_authorized: str,
    component_id: str | None = None,
    source_obligation_id: str | None = None,
    search_requirement_id: str | None = None,
    planner_purpose: str = "candidate_handoff",
) -> OrdinaryLiveCandidateHandoffResult:
    """Reduce structured offline candidate inputs through the ordinary RunKernel."""

    base = _base_projection(enabled=True)
    try:
        component_id = _clean_text(component_id, limit=160) or _COMPONENT_ID
        source_obligation_id = (
            _clean_text(source_obligation_id, limit=160) or _SOURCE_OBLIGATION_ID
        )
        search_requirement_id = (
            _clean_text(search_requirement_id, limit=160) or _SEARCH_REQUIREMENT_ID
        )
        planner_purpose = _clean_text(planner_purpose, limit=120) or "candidate_handoff"
        normalized_results = _normalize_candidate_results(candidate_results)
        results_per_task_cap = _results_per_task_cap(normalized_results)
        _ensure_front_half_state(
            run_kernel=run_kernel,
            query=query,
            requested_mode=requested_mode,
            run_contract_projection=run_contract_projection,
            route_projection=route_projection,
            core_topic=core_topic,
            provider_authorized=provider_authorized,
            results_per_task_cap=results_per_task_cap,
            component_id=component_id,
            source_obligation_id=source_obligation_id,
            search_requirement_id=search_requirement_id,
            planner_purpose=planner_purpose,
        )
        current_contract = run_kernel.state.current_answer_contract
        if not current_contract:
            raise OrdinaryLiveCandidateHandoffError(
                "accepted_current_answer_contract_missing",
                "ordinary live candidate handoff requires accepted current_answer_contract",
            )
        handoff_state = run_kernel.state.search_executor_handoff_state
        if not handoff_state:
            raise OrdinaryLiveCandidateHandoffError(
                "search_executor_handoff_missing",
                "ordinary live candidate handoff requires SearchExecutorHandoff",
            )
        selected_task_ids = _selected_task_ids(handoff_state)
        if not selected_task_ids:
            raise OrdinaryLiveCandidateHandoffError(
                "search_executor_handoff_task_missing",
                "ordinary live candidate handoff requires SearchExecutorHandoff task ids",
            )
        provider = _required_text(
            provider_authorized,
            seam="provider_authorization_missing",
            message="ordinary live candidate handoff requires provider_authorized",
        )
        action = run_kernel.authorize_live_search_validation(
            selected_search_task_ids=selected_task_ids,
            provider_authorized=provider,
            provider_call_cap=DEFAULT_PROVIDER_CALL_CAP,
            results_per_task_cap=results_per_task_cap,
            parent_current_contract_version=current_contract[
                "accepted_contract_version"
            ],
            parent_current_contract_digest=current_contract[
                "accepted_contract_digest"
            ],
            handoff_id=handoff_state["handoff_id"],
            handoff_digest=handoff_state["handoff_digest"],
        )
        payload = build_live_search_validation_observation_payload(
            action=action,
            current_answer_contract=current_contract,
            search_executor_handoff_state=handoff_state,
            provider_used=provider,
            provider_results_by_task={selected_task_ids[0]: normalized_results},
            execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
            broker_invoked=False,
            live_provider_called=False,
        )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
                status=RunStageStatus.COMPLETED,
                payload=payload,
            )
        )
        candidate_packet = validate_search_result_candidate_packet(
            build_search_result_candidate_packet_from_live_validation_state(
                run_kernel.state.live_search_validation_state
            )
        )
        projection = {
            **base,
            "ran": True,
            "failed_closed": False,
            "status": "search_result_candidate_packet_built",
            "first_failed_seam": None,
            "run_pipeline_consumer": True,
            "current_answer_contract_ref": live_contract_ref_from_contract(
                current_contract,
                source="current_answer_contract",
            ),
            "current_answer_contract_version": current_contract.get(
                "accepted_contract_version"
            ),
            "current_answer_contract_digest": current_contract.get(
                "accepted_contract_digest"
            ),
            "search_executor_handoff_ref": handoff_ref_from_handoff_state(
                handoff_state
            ),
            "search_executor_handoff_id": handoff_state.get("handoff_id"),
            "search_executor_handoff_digest": handoff_state.get("handoff_digest"),
            "selected_search_task_ids": selected_task_ids,
            "live_search_validation_ref": _live_search_validation_ref(
                run_kernel.state.live_search_validation_state
            ),
            "live_search_validation_state_source": "RunKernel.live_search_validation_state",
            "search_result_candidate_packet_status": "built_from_live_search_validation_state",
            "search_result_candidate_packet_ref": (
                search_result_candidate_packet_ref_from_packet(candidate_packet)
            ),
            "search_result_candidate_packet_id": candidate_packet.get("packet_id"),
            "search_result_candidate_packet_digest": candidate_packet.get(
                "packet_digest"
            ),
            "search_result_candidate_packet_candidate_count": candidate_packet.get(
                "candidate_count"
            ),
            "structured_candidate_input_count": len(normalized_results),
            "retrieval_diagnostics_used_as_candidate_authority": False,
            "candidate_authority_source": "structured_offline_candidate_inputs",
            **_zero_call_counts(),
            "live_search_validation_provider_calls_attempted": (
                run_kernel.state.live_search_validation_state.get(
                    "provider_calls_attempted"
                )
            ),
            "explicit_non_proofs": list(_NON_PROOFS),
            "closed_surface_flags": dict(_FALSE_CLOSED_SURFACES),
            **_FALSE_CLOSED_SURFACES,
        }
        return OrdinaryLiveCandidateHandoffResult(
            projection=_without_empty(projection),
            candidate_packet=candidate_packet,
        )
    except OrdinaryLiveCandidateHandoffError as exc:
        return OrdinaryLiveCandidateHandoffResult(
            projection=_fail_projection(base, exc.first_failed_seam, str(exc))
        )
    except RunKernelTransitionError as exc:
        return OrdinaryLiveCandidateHandoffResult(
            projection=_fail_projection(
                base,
                "runkernel_reducer_rejected_handoff",
                str(exc),
            )
        )
    except Exception as exc:
        return OrdinaryLiveCandidateHandoffResult(
            projection=_fail_projection(
                base,
                "ordinary_live_candidate_handoff_exception",
                str(exc),
            )
        )


def _ensure_front_half_state(
    *,
    run_kernel: RunKernel,
    query: str,
    requested_mode: str,
    run_contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None,
    core_topic: str | None,
    provider_authorized: str,
    results_per_task_cap: int,
    component_id: str,
    source_obligation_id: str,
    search_requirement_id: str,
    planner_purpose: str,
) -> None:
    if run_kernel.state.current_answer_contract:
        if not run_kernel.state.search_executor_handoff_state:
            _reduce_search_executor_handoff(
                run_kernel,
                provider_authorized=provider_authorized,
                results_per_task_cap=results_per_task_cap,
            )
        return
    if run_kernel.state.initial_answer_contract:
        if planner_purpose == "main_answer_coverage":
            _ensure_existing_component_ref(
                run_kernel.state.initial_answer_contract,
                component_id=component_id,
            )
            _reduce_search_planner(
                run_kernel=run_kernel,
                query=query,
                requested_mode=requested_mode,
                run_contract_projection=run_contract_projection,
                route_projection=route_projection,
                core_topic=core_topic,
                component_id=component_id,
                source_obligation_id=source_obligation_id,
                search_requirement_id=search_requirement_id,
                planner_purpose=planner_purpose,
            )
            _apply_current_contract_candidate_caveat(
                run_kernel,
                query=query,
                component_id=component_id,
                planner_purpose=planner_purpose,
            )
            if not run_kernel.state.current_answer_contract:
                raise OrdinaryLiveCandidateHandoffError(
                    "accepted_current_answer_contract_missing",
                    "ordinary live main coverage did not create current contract",
                )
            _reduce_search_executor_handoff(
                run_kernel,
                provider_authorized=provider_authorized,
                results_per_task_cap=results_per_task_cap,
            )
            return
        raise OrdinaryLiveCandidateHandoffError(
            "accepted_current_answer_contract_missing",
            "ordinary live candidate handoff found initial contract without current contract",
        )
    _reduce_search_planner(
        run_kernel=run_kernel,
        query=query,
        requested_mode=requested_mode,
        run_contract_projection=run_contract_projection,
        route_projection=route_projection,
        core_topic=core_topic,
        component_id=component_id,
        source_obligation_id=source_obligation_id,
        search_requirement_id=search_requirement_id,
        planner_purpose=planner_purpose,
    )
    _accept_initial_contract(run_kernel)
    _apply_current_contract_candidate_caveat(
        run_kernel,
        query=query,
        component_id=component_id,
        planner_purpose=planner_purpose,
    )
    if not run_kernel.state.current_answer_contract:
        raise OrdinaryLiveCandidateHandoffError(
            "accepted_current_answer_contract_missing",
            "ordinary live candidate handoff did not create current_answer_contract",
        )
    _reduce_search_executor_handoff(
        run_kernel,
        provider_authorized=provider_authorized,
        results_per_task_cap=results_per_task_cap,
    )


def _ensure_existing_component_ref(
    accepted_contract: Mapping[str, Any],
    *,
    component_id: str,
) -> None:
    for ref in accepted_contract.get("accepted_answer_component_refs", []):
        if isinstance(ref, Mapping) and ref.get("component_id") == component_id:
            return
    raise OrdinaryLiveCandidateHandoffError(
        "main_answer_component_binding_missing",
        "ordinary live main coverage requires an existing accepted component",
    )


def _reduce_search_planner(
    *,
    run_kernel: RunKernel,
    query: str,
    requested_mode: str,
    run_contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None,
    core_topic: str | None,
    component_id: str,
    source_obligation_id: str,
    search_requirement_id: str,
    planner_purpose: str,
) -> None:
    normalized_query = _clean_text(query, limit=500) or "ordinary user query"
    planner_input = SearchPlannerInput(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        user_query_text=normalized_query,
        requested_mode=_clean_text(requested_mode, limit=80) or "balanced",
        safe_context={
            "phase": ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE,
            "mode": ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE,
            "front_half_source": "ordinary_run_pipeline_default_disabled_repair",
            "product_path": True,
            "live_calls": 0,
        },
        route_context_ref={
            "route_ref": _clean_text(
                _safe_mapping(route_projection).get("route_id"),
                limit=160,
            )
            or "ordinary_run_pipeline_route",
        },
        run_context_ref={
            "run_contract_id": _clean_text(
                _safe_mapping(run_contract_projection).get("contract_id"),
                limit=160,
            )
            or run_kernel.state.run_id,
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
        adapter=_OrdinaryPlannerAdapter(
            query=normalized_query,
            core_topic=core_topic,
            component_id=component_id,
            source_obligation_id=source_obligation_id,
            search_requirement_id=search_requirement_id,
            planner_purpose=planner_purpose,
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


def _accept_initial_contract(run_kernel: RunKernel) -> None:
    qmr = _safe_mapping(
        run_kernel.state.search_planner_proposal_projection.get(
            "question_meaning_record"
        )
    )
    if not qmr:
        raise OrdinaryLiveCandidateHandoffError(
            "search_planner_question_meaning_record_missing",
            "ordinary live candidate handoff requires SearchPlanner QMR",
        )
    action = run_kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr["record_id"]),
        parent_proposal_digest=str(qmr["record_digest"]),
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": dict(qmr)},
        )
    )


def _apply_current_contract_candidate_caveat(
    run_kernel: RunKernel,
    *,
    query: str,
    component_id: str,
    planner_purpose: str,
) -> None:
    accepted = run_kernel.state.initial_answer_contract
    if not accepted:
        raise OrdinaryLiveCandidateHandoffError(
            "initial_answer_contract_missing",
            "ordinary live candidate handoff requires initial answer contract",
        )
    record = _candidate_caveat_record(
        run_kernel,
        accepted,
        query=query,
        component_id=component_id,
        planner_purpose=planner_purpose,
    )
    action = run_kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": record.to_dict()},
        )
    )
    admission = run_kernel.state.contract_amendment_admission_projection
    apply_action = run_kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
    )
    run_kernel.reduce(
        Observation.from_action(
            apply_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )


def _reduce_search_executor_handoff(
    run_kernel: RunKernel,
    *,
    provider_authorized: str,
    results_per_task_cap: int,
) -> None:
    contract = run_kernel.state.current_answer_contract
    if not contract:
        raise OrdinaryLiveCandidateHandoffError(
            "accepted_current_answer_contract_missing",
            "ordinary live candidate handoff requires current contract before handoff",
        )
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
        answer_component_refs=contract.get("accepted_answer_component_refs", []),
        source_obligation_candidate_refs=_source_refs_from_contract(contract),
        component_search_requirements=(
            run_kernel.state.search_planner_proposal_state.get(
                "component_search_requirements",
                [],
            )
        ),
        required_caveats=contract.get("mandatory_caveats", []),
        prohibited_upgrades=contract.get("prohibited_upgrades", []),
        query_budget={
            "max_search_tasks": DEFAULT_MAX_SEARCH_TASKS,
            "max_results_per_task": results_per_task_cap,
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


def _planner_adapter_result(
    planner_input: Mapping[str, Any],
    *,
    query: str,
    core_topic: str | None,
    component_id: str,
    source_obligation_id: str,
    search_requirement_id: str,
    planner_purpose: str,
) -> dict[str, Any]:
    query_ref = _safe_mapping(planner_input.get("user_query_ref"))
    label = _clean_text(core_topic, limit=160) or _clean_text(query, limit=160) or "Primary source candidate"
    question = _clean_text(query, limit=300) or label
    main_answer_component = planner_purpose == "main_answer_coverage"
    if main_answer_component:
        summary = (
            "Prepare one main ordinary answer component for bounded source "
            "custody, SemanticObservation admission, and ComponentCoverage."
        )
        requested_output = (
            "Readiness-compatible ComponentCoverage input for the main answer "
            "component; no answer text."
        )
        component_criteria = [
            "bind bounded sanitized source content to the accepted answer component",
            "do not create readiness, citations, source-obligation satisfaction, or answer text",
        ]
        component_caveats = [
            "ComponentCoverage is structural readiness input only."
        ]
        component_prohibited = [
            "Do not claim SufficiencyReadiness, FinalAnswerPacket, Author, citations, source-obligation satisfaction, answer text, or product correctness."
        ]
        planner_caveats = [
            "This ordinary repair seam validates main RunKernel source coverage only and does not answer."
        ]
        planner_prohibited = [
            "No SufficiencyReadiness, FAP, Author, citation rendering, source-obligation satisfaction, or product-correctness claim."
        ]
        slot_id = "slot:ordinary-live-main-answer-source"
        obligation_kind = "ordinary_live_main_answer_source"
        model_adapter_name = "deterministic_ordinary_live_main_runkernel_coverage_adapter"
    else:
        summary = (
            "Prepare one ordinary product-path search candidate handoff for the "
            "current user query."
        )
        requested_output = "Sanitized SearchResultCandidate records only; no answer."
        component_criteria = [
            "discover structured source candidate records",
            "do not answer from snippets or search candidates",
        ]
        component_caveats = ["SearchResultCandidate records are non-evidence."]
        component_prohibited = [
            "Do not claim source-obligation satisfaction from search snippets."
        ]
        planner_caveats = [
            "This ordinary repair seam validates search candidates only and does not answer."
        ]
        planner_prohibited = [
            "No fetch/read, EvidenceLedger, citations, Sufficiency, FAP, Author, or product-correctness claim."
        ]
        slot_id = "slot:ordinary-live-candidate-source"
        obligation_kind = "ordinary_structured_source_candidate"
        model_adapter_name = "deterministic_ordinary_live_candidate_handoff_adapter"
    return {
        "question_meaning_summary": summary,
        "requested_output": requested_output,
        "semantic_slots": [
            {
                "slot_id": slot_id,
                "slot_kind": "source_basis",
                "status": "explicit",
                "selected_value": "structured offline source candidate input",
                "materiality": "material",
            }
        ],
        "answer_components": [
            {
                "component_id": component_id,
                "component_revision": "1",
                "user_facing_label": label,
                "user_facing_question": question,
                "requirement_posture": "required",
                "acceptance_criteria": component_criteria,
                "semantic_slot_ids": [slot_id],
                "source_obligation_candidate_ids": [source_obligation_id],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": component_caveats,
                "prohibited_upgrades": component_prohibited,
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": source_obligation_id,
                "obligation_kind": obligation_kind,
                "component_candidate_ids": [component_id],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": component_id,
                "requirement_id": search_requirement_id,
                "requirement_summary": question,
                "source_obligation_candidate_ids": [source_obligation_id],
                "preferred_source_kinds": ["official", "primary", "canonical"],
                "recency_requirement": "current_if_user_question_requires_currentness",
            }
        ],
        "material_ambiguity_posture": "clear",
        "mandatory_caveats": planner_caveats,
        "prohibited_upgrades": planner_prohibited,
        "normalization_obligations": [
            "Treat the query as source-candidate discovery only."
        ],
        "assumptions": [
            "Tests or explicit product config supply structured offline candidate records."
        ],
        "unsupported_outputs": [
            "Final answer creation is outside ordinary live candidate handoff repair."
        ],
        "planner_model_metadata": {
            "provider": model_adapter_name,
            "model_adapter_enabled": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "provider_payload_retained": False,
            "prompt_hash": query_ref.get("digest"),
            "front_half_source": planner_purpose,
        },
    }


def _candidate_caveat_record(
    run_kernel: RunKernel,
    accepted: Mapping[str, Any],
    *,
    query: str,
    component_id: str,
    planner_purpose: str,
) -> ContractAmendmentRecord:
    main_answer_component = planner_purpose == "main_answer_coverage"
    caveat = (
        "Ordinary live main RunKernel coverage records source coverage only; "
        "coverage is not readiness, citation rendering, source-obligation "
        "satisfaction, answer text, or product correctness."
        if main_answer_component
        else (
            "Ordinary live candidate handoff records search candidates only; "
            "candidates are not evidence."
        )
    )
    amendment_id = (
        "amendment:ordinary-live-main-runkernel-coverage-integration-01"
        if main_answer_component
        else "amendment:ordinary-live-candidate-handoff-repair-01"
    )
    operation_id = (
        "operation:add-ordinary-live-main-coverage-caveat"
        if main_answer_component
        else "operation:add-ordinary-live-candidate-caveat"
    )
    phase = (
        "AG-ORDINARY-LIVE-MAIN-RUNKERNEL-COVERAGE-INTEGRATION-01"
        if main_answer_component
        else ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE
    )
    operation = AmendmentOperation(
        operation_id=operation_id,
        operation_kind=AmendmentOperationKind.ADD_CAVEAT,
        operation_payload={
            "caveat": caveat,
            "component_id": component_id,
        },
    )
    return ContractAmendmentRecord(
        amendment_record_id=amendment_id,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=_digest_text(query),
        parent_contract_version=str(accepted["accepted_contract_version"]),
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=accepted.get(
            "parent_question_meaning_record_id"
        ),
        parent_question_meaning_record_digest=accepted.get(
            "parent_question_meaning_record_digest"
        ),
        accepted_contract_ref=f"contract:{accepted['accepted_contract_version']}:accepted",
        trigger_refs=AmendmentTriggerRefs(
            gap_refs=(f"repair:{planner_purpose}",),
            currentness_refs=("repair:source-candidate-authority-before-retrieval",),
        ),
        operations=(operation,),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture=UserConfirmationPosture.NOT_REQUIRED,
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        required_caveats=(caveat,),
        prohibited_upgrades=(
            "Do not use provider_preference_hint as live provider authority.",
        ),
        metadata={
            "phase": phase,
            "mode": ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE,
            "front_half_source": planner_purpose,
        },
    )


def _normalize_candidate_results(
    value: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    if value is None:
        raise OrdinaryLiveCandidateHandoffError(
            "structured_candidate_inputs_missing",
            "ordinary live candidate handoff enabled without structured candidate inputs",
        )
    raw_results: Any
    if isinstance(value, Mapping):
        unknown = sorted(set(value) - _ALLOWED_CANDIDATE_ENVELOPE_KEYS)
        if unknown:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff candidate envelope has unsupported "
                "fields: " + ", ".join(unknown),
            )
        if value.get("raw_provider_payload_retained") is True:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff rejects raw provider retention",
            )
        if value.get("raw_search_response_retained") is True:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff rejects raw search retention",
            )
        raw_results = value.get("results")
    else:
        raw_results = value
    if isinstance(raw_results, str | bytes) or not isinstance(raw_results, Sequence):
        raise OrdinaryLiveCandidateHandoffError(
            "structured_candidate_inputs_invalid",
            "ordinary live candidate handoff candidate inputs must be a sequence",
        )
    if not raw_results:
        raise OrdinaryLiveCandidateHandoffError(
            "structured_candidate_inputs_missing",
            "ordinary live candidate handoff enabled without structured candidate inputs",
        )
    normalized: list[dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, Mapping):
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff candidate input must be a mapping",
            )
        unknown = sorted(set(raw) - _ALLOWED_CANDIDATE_RESULT_KEYS)
        if unknown:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff candidate input has unsupported fields: "
                + ", ".join(unknown),
            )
        if raw.get("raw_provider_payload_retained") is True:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff rejects raw provider retention",
            )
        if raw.get("raw_search_response_retained") is True:
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff rejects raw search retention",
            )
        if not _clean_text(raw.get("title"), limit=220):
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff candidate requires title",
            )
        if not _clean_text(raw.get("url") or raw.get("link"), limit=700):
            raise OrdinaryLiveCandidateHandoffError(
                "structured_candidate_inputs_invalid",
                "ordinary live candidate handoff candidate requires url",
            )
        normalized.append({key: raw[key] for key in _ALLOWED_CANDIDATE_RESULT_KEYS if key in raw})
    return tuple(normalized)


def _results_per_task_cap(results: Sequence[Mapping[str, Any]]) -> int:
    count = len(results)
    if count > LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP:
        raise OrdinaryLiveCandidateHandoffError(
            "structured_candidate_inputs_invalid",
            "ordinary live candidate handoff candidate count exceeds explicit cap",
        )
    return max(1, min(LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP, count))


def _selected_task_ids(handoff_state: Mapping[str, Any]) -> list[str]:
    tasks = handoff_state.get("search_task_records", [])
    if not isinstance(tasks, Sequence) or isinstance(tasks, str | bytes):
        return []
    return [
        str(task["search_task_id"])
        for task in tasks
        if isinstance(task, Mapping) and task.get("search_task_id")
    ][:DEFAULT_MAX_SEARCH_TASKS]


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs", []) or []:
        if not isinstance(component, Mapping):
            continue
        component_id = component.get("component_id")
        for candidate_id in component.get("source_obligation_candidate_ids", []) or []:
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "component_candidate_ids": [component_id],
                    "obligation_kind": "ordinary_structured_source_candidate",
                    "strictness": "required",
                }
            )
    return refs


def _base_projection(*, enabled: bool) -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY,
        "phase": ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE,
        "mode": ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE,
        "repair_verdict_target": "YES",
        "enabled": enabled,
        "ran": False,
        "failed_closed": False,
        "first_failed_seam": None,
        "status": "not_run",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "product_path_affected": "ordinary run_pipeline",
        "default_disabled": True,
        "old_path_treatment": (
            "phase scripts remain proof-only; retrieval diagnostics remain non-authority"
        ),
        "retrieval_diagnostics_used_as_candidate_authority": False,
        "current_path_timing": "before ordinary retrieval/provider result dispatch",
        **_zero_call_counts(),
    }


def _fail_projection(
    base: Mapping[str, Any],
    first_failed_seam: str,
    reason: str,
) -> dict[str, Any]:
    return {
        **dict(base),
        "ran": False,
        "failed_closed": True,
        "status": "failed_closed",
        "first_failed_seam": first_failed_seam,
        "failure_reason": _clean_text(reason, limit=360),
        "run_pipeline_consumer": True,
        "candidate_authority_source": "none",
        "retrieval_diagnostics_used_as_candidate_authority": False,
        "search_result_candidate_packet_status": "not_built",
        "search_result_candidate_packet_ref": {},
        "explicit_non_proofs": list(_NON_PROOFS),
        "closed_surface_flags": dict(_FALSE_CLOSED_SURFACES),
        **_FALSE_CLOSED_SURFACES,
        **_zero_call_counts(),
    }


def _zero_call_counts() -> dict[str, int]:
    return {
        "provider_search_calls": 0,
        "broker_calls": 0,
        "fetch_read_calls": 0,
        "model_calls": 0,
        "retrieval_calls": 0,
    }


def _live_search_validation_ref(state: Mapping[str, Any]) -> dict[str, Any]:
    validation_id = _clean_text(state.get("validation_id"), limit=260)
    validation_digest = _clean_text(state.get("validation_digest"), limit=128)
    if not validation_id or not validation_digest:
        return {}
    return {
        "validation_id": validation_id,
        "validation_digest": validation_digest,
        "schema_version": _clean_text(state.get("schema_version"), limit=160),
        "candidate_count": _bounded_int(state.get("candidate_count")),
    }


def _required_text(value: Any, *, seam: str, message: str) -> str:
    text = _clean_text(value, limit=120)
    if not text:
        raise OrdinaryLiveCandidateHandoffError(seam, message)
    return text


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _digest_text(value: str) -> str:
    return hashlib.sha256((_clean_text(value, limit=500) or "").encode("utf-8")).hexdigest()


__all__ = [
    "ORDINARY_LIVE_CANDIDATE_HANDOFF_MODE",
    "ORDINARY_LIVE_CANDIDATE_HANDOFF_PHASE",
    "ORDINARY_LIVE_CANDIDATE_HANDOFF_TRACE_KEY",
    "OrdinaryLiveCandidateHandoffResult",
    "execute_ordinary_live_candidate_handoff",
    "ordinary_live_candidate_handoff_disabled_projection",
]
