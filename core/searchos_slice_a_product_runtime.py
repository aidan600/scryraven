"""Ordinary-product SearchOS Slice A judgment and acquisition composition."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.acquisition_adapters import AcquisitionTransports
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_judgment_read_assessment_runtime import (
    SelectedCandidateMaterialNeedBindingV1,
    derive_selected_candidate_material_need_bindings,
    execute_searchos_candidate_read_to_custody,
)
from core.search_result_candidate_packet import (
    search_result_candidate_packet_ref_from_packet,
)
from core.searchos_iterative_judgment_runtime import (
    SearchOSJudgmentAction,
    SearchOSRuntimeError,
    SearchOSSlotPosture,
    build_candidate_use_options_v1,
    build_candidate_use_window_v1,
    build_searchos_iteration_candidate_set_v1,
    build_searchos_policy_snapshot,
    build_searchos_read_custody_material_ref,
    build_searchos_revision_1_candidate_state_v1,
    candidate_use_option_ref,
    searchos_revision_1_candidate_state_ref,
    validate_searchos_append_only_lineage,
    validate_searchos_judgment_model_output,
)

SEARCHOS_JUDGMENT_SYSTEM_PROMPT = """You are the neutral SearchOS SearchJudgment.
Return exactly one JSON object matching searchos_judgment_decision_v1.
Choose exactly one action:
- HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION
- REQUEST_READ_PAGE
- PROPOSE_FOLLOWUP_QUERY
- HANDOFF_UNRESOLVED
Use only the exact slot, candidate-use options, and READ custody refs supplied.
DISCOVER material is directional_candidate_context and cannot support an answer.
Only read_custody_material may be handed to semantic evaluation.
Never invent a URL, query, custody ref, component, obligation, or fallback.
"""
SEARCHOS_SLICE_A_TRACE_KEY = "searchos_slice_a"
TERMINAL_CANDIDATE_OPTION_DISPOSITIONS = frozenset(
    {"read_insufficient", "invalid", "declined"}
)


@dataclass(frozen=True, slots=True)
class SearchOSSliceAProductResult:
    revision_1: Mapping[str, Any]
    iteration_candidate_sets: tuple[Mapping[str, Any], ...]
    semantic_handoffs: tuple[Mapping[str, Any], ...]
    searchos_semantic_material: tuple[Mapping[str, Any], ...]
    projection: Mapping[str, Any]
    provider_calls_attempted: int = 0
    provider_calls_completed: int = 0


FollowupDiscover = Callable[[str, int, Mapping[str, Any]], Mapping[str, Any]]


def execute_searchos_slice_a_iterative_judgment(
    *,
    run_kernel: RunKernel,
    candidate_packet: Mapping[str, Any],
    query_authority: QueryPlanRuntimeAdapter,
    discovery_result_store: Any,
    profile_name: str,
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    available_providers: Mapping[str, object],
    acquisition_transports: AcquisitionTransports | None,
    execute_followup_discover: FollowupDiscover | None,
    before_transport: Callable[[], Any] | None = None,
    measure_context_stage: Callable[..., Any] | None = None,
) -> SearchOSSliceAProductResult:
    """Run the canonical post-first-wave Slice A loop under RunKernel."""

    initial_packet = dict(candidate_packet)
    initial_packet_ref = search_result_candidate_packet_ref_from_packet(initial_packet)
    if not initial_packet_ref:
        raise SearchOSRuntimeError("SearchOS Slice A requires revision-1 candidates")
    initial_query_items = [item.to_dict() for item in query_authority.plan.items]
    initial_identities = [item.ref() for item in discovery_result_store.identities()]
    initial_binding_state = derive_selected_candidate_material_need_bindings(
        run_kernel=run_kernel,
        candidate_packet=initial_packet,
        query_plan=query_authority.plan,
        discovery_result_store=discovery_result_store,
    )
    bindings = _bindings_from_state(initial_binding_state)
    revision_1 = build_searchos_revision_1_candidate_state_v1(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        candidate_packet_ref=initial_packet_ref,
        initial_query_plan_ref=query_authority.plan.to_ref(),
        initial_query_plan_items=initial_query_items,
        initial_identity_set_ref=discovery_result_store.identity_set_ref(),
        initial_identity_refs=initial_identities,
        selected_candidate_refs=_candidate_refs(initial_packet),
        bounded_candidate_material_refs=_material_refs(bindings),
        selection_facts={
            "selected_candidate_count": len(initial_packet.get("candidate_records") or ()),
            "first_admitted_discover_wave_count": 1,
        },
        overflow_facts={
            "selection_overflow_count": int(initial_packet.get("selection_overflow_count") or 0),
            "contributor_overflow_count": sum(
                int(item.get("contributor_overflow_count") or 0)
                for item in initial_packet.get("candidate_records") or ()
                if isinstance(item, Mapping)
            ),
        },
    )
    revision_ref = searchos_revision_1_candidate_state_ref(revision_1)
    active_slots = _active_slots(run_kernel)
    policy = build_searchos_policy_snapshot(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        profile_name=_profile_name(profile_name),
    )
    initialize = run_kernel.authorize_searchos_initialization(
        answer_contract_ref=revision_1_answer_contract_ref(initial_packet),
        policy_snapshot=policy,
        active_slots=active_slots,
        initial_candidate_state_ref=revision_ref,
    )
    run_kernel.reduce(
        Observation.from_action(
            initialize,
            observation_type=ObservationType.SEARCHOS_INITIALIZED,
            status=RunStageStatus.COMPLETED,
            payload={"searchos_state": initialize.inputs["searchos_state"]},
        )
    )

    packets_by_id = {initial_packet_ref["packet_id"]: initial_packet}
    binding_candidate_states = {binding.binding_id: revision_ref for binding in bindings}
    binding_iteration_refs: dict[str, Mapping[str, Any]] = {}
    iteration_sets: list[Mapping[str, Any]] = []
    identity_deltas_by_digest: dict[str, Sequence[Mapping[str, Any]]] = {}
    custody_by_url: dict[str, dict[str, Any]] = {}
    packet_by_custody_id: dict[str, Mapping[str, Any]] = {}
    dispositions: dict[str, str] = {}
    semantic_handoffs: list[Mapping[str, Any]] = []
    attempted = 0
    completed = 0

    while True:
        state = run_kernel.state.searchos_state
        participating = [
            slot_id
            for slot_id in state["active_slot_ids"]
            if state["slots_by_id"][slot_id]["posture"] == SearchOSSlotPosture.ACTIVE_UNJUDGED.value
        ]
        if not participating:
            break
        try:
            reservation = run_kernel.reserve_searchos_judgment_round(
                slot_ids=participating
            )
        except ValueError:
            for slot_id in participating:
                _mark_budget_exhausted(run_kernel, slot_id)
            break

        for slot_id in participating:
            slot = run_kernel.state.searchos_state["slots_by_id"][slot_id]
            try:
                options, window, exhaustion_reason = _prepare_candidate_window(
                    slot=slot,
                    bindings=bindings,
                    binding_candidate_states=binding_candidate_states,
                    binding_iteration_refs=binding_iteration_refs,
                    discovery_result_store=discovery_result_store,
                    policy_snapshot=run_kernel.state.searchos_state["policy_snapshot"],
                    dispositions=dispositions,
                )
            except Exception as exc:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason="candidate_window_preparation_rejected",
                )
                run_kernel.mark_searchos_slot_stale_or_invalid(
                    slot_id=slot_id,
                    reason=f"candidate_window_preparation_failed:{type(exc).__name__}",
                )
                continue
            if exhaustion_reason:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason=exhaustion_reason,
                )
                run_kernel.mark_searchos_slot_unresolved(
                    slot_id=slot_id,
                    reason=exhaustion_reason,
                )
                continue
            run_kernel.expose_searchos_candidate_window(window=window)
            current_slot = run_kernel.state.searchos_state["slots_by_id"][slot_id]
            try:
                action = run_kernel.authorize_searchos_judgment(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    candidate_window=window,
                    read_custody_refs=current_slot["custody_refs"],
                )
            except Exception as exc:
                run_kernel.return_searchos_pre_call_reservation(
                    reservation_ref=reservation,
                    slot_id=slot_id,
                    reason="judgment_authorization_rejected",
                )
                run_kernel.mark_searchos_slot_stale_or_invalid(
                    slot_id=slot_id,
                    reason=f"judgment_authorization_rejected:{type(exc).__name__}",
                )
                continue
            request = action.inputs["judgment_request"]
            try:
                raw = _invoke_judgment_model(
                    request=request,
                    ask_model=ask_model,
                    provider=provider,
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    use_reasoning=use_reasoning,
                    measure_context_stage=measure_context_stage,
                )
                parsed = _strict_json_object(raw)
                validate_searchos_judgment_model_output(
                    request=request,
                    model_output=parsed,
                )
            except Exception as exc:
                failure_reason = _failure_reason(exc)
                run_kernel.reduce(
                    Observation.from_action(
                        action,
                        observation_type=ObservationType.SEARCHOS_JUDGMENT_DECIDED,
                        status=RunStageStatus.FAILED,
                        payload={
                            "failure_reason": failure_reason,
                            "raw_model_response_retained": False,
                        },
                    )
                )
                if _invalid_or_stale_nomination(exc):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=failure_reason,
                    )
                continue
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=ObservationType.SEARCHOS_JUDGMENT_DECIDED,
                    status=RunStageStatus.COMPLETED,
                    payload={"model_output": parsed},
                )
            )
            decision = deepcopy(run_kernel.state.projections["searchos_iterative_judgment"])
            decision_action = SearchOSJudgmentAction(decision["action"])
            if decision_action is SearchOSJudgmentAction.REQUEST_READ_PAGE:
                option_ref = dict(decision["candidate_use_option_ref"])
                option_id = option_ref["candidate_use_option_id"]
                if (
                    dispositions.get(option_id)
                    in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
                ):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason="read_nomination_already_disposed",
                    )
                    continue
                binding = _binding_for_option(
                    bindings=bindings,
                    slot_id=slot_id,
                    option_ref=option_ref,
                    options=options,
                )
                prior = custody_by_url.get(binding.normalized_url)
                if prior:
                    custody_outcome = prior
                    reused = True
                else:
                    packet_id = binding.candidate_packet_ref["packet_id"]
                    packet = packets_by_id.get(packet_id)
                    if not packet:
                        run_kernel.mark_searchos_slot_stale_or_invalid(
                            slot_id=slot_id,
                            reason="candidate_packet_stale",
                        )
                        continue
                    before_attempted, before_completed = (
                        _acquisition_provider_call_totals(run_kernel)
                    )
                    try:
                        custody_outcome = execute_searchos_candidate_read_to_custody(
                            run_kernel=run_kernel,
                            candidate_packet=packet,
                            binding=binding,
                            available_providers=available_providers,
                            acquisition_transports=acquisition_transports,
                            before_transport=before_transport,
                        )
                    except Exception as exc:
                        after_attempted, after_completed = (
                            _acquisition_provider_call_totals(run_kernel)
                        )
                        attempted += max(0, after_attempted - before_attempted)
                        completed += max(0, after_completed - before_completed)
                        dispositions[option_id] = "read_insufficient"
                        run_kernel.mark_searchos_slot_stale_or_invalid(
                            slot_id=slot_id,
                            reason=_read_failure_reason(exc),
                        )
                        continue
                    after_attempted, after_completed = (
                        _acquisition_provider_call_totals(run_kernel)
                    )
                    attempt_delta = max(0, after_attempted - before_attempted)
                    completion_delta = max(0, after_completed - before_completed)
                    if attempt_delta != int(
                        custody_outcome.get("provider_calls_attempted") or 0
                    ) or completion_delta != int(
                        custody_outcome.get("provider_calls_completed") or 0
                    ):
                        raise SearchOSRuntimeError(
                            "SearchOS READ provider-call accounting is stale"
                        )
                    attempted += attempt_delta
                    completed += completion_delta
                    custody_by_url[binding.normalized_url] = custody_outcome
                    reused = False
                custody_ref = build_searchos_read_custody_material_ref(
                    slot_ref=run_kernel.state.searchos_state["slots_by_id"][slot_id]["slot_ref"],
                    candidate_use_option_ref=option_ref,
                    custody_record=custody_outcome["custody_record"],
                    same_normalized_url_reused=reused,
                )
                custody_action = run_kernel.authorize_searchos_read_custody_admission(custody_material_ref=custody_ref)
                run_kernel.reduce(
                    Observation.from_action(
                        custody_action,
                        observation_type=(ObservationType.SEARCHOS_READ_CUSTODY_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"custody_material_ref": custody_ref},
                    )
                )
                dispositions[option_id] = "custodied"
                packet_by_custody_id[custody_ref["read_custody_material_id"]] = custody_outcome[
                    "fetch_read_content_packet"
                ]
            elif decision_action is SearchOSJudgmentAction.PROPOSE_FOLLOWUP_QUERY:
                if execute_followup_discover is None:
                    run_kernel.mark_searchos_slot_unresolved(
                        slot_id=slot_id,
                        reason="followup_discover_executor_unavailable",
                    )
                    continue
                iteration = len(iteration_sets) + 2
                try:
                    query_plan_action = run_kernel.authorize_query_plan_admission(
                        inputs={
                            "authority": "SearchOSJudgment",
                            "judgment_decision_ref": _decision_ref(decision),
                            "iteration": iteration,
                        }
                    )
                    query_admission = query_authority.admit_searchos_followup_query(
                        judgment_decision=decision,
                        iteration=iteration,
                    )
                    run_kernel.reduce(
                        Observation.from_action(
                            query_plan_action,
                            observation_type=ObservationType.QUERY_PLAN_ADMITTED,
                            status=RunStageStatus.COMPLETED,
                            payload=query_admission,
                        )
                    )
                except Exception as exc:
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=f"followup_query_admission_rejected:{type(exc).__name__}",
                    )
                    continue
                before_identities = list(discovery_result_store.identities())
                parent_ref = deepcopy(run_kernel.state.searchos_state["current_candidate_state_ref"])
                wave = dict(
                    execute_followup_discover(
                        decision["followup_query"],
                        iteration,
                        query_admission,
                    )
                )
                after_identities = list(discovery_result_store.identities())
                delta_identities = [item.ref() for item in after_identities[len(before_identities) :]]
                delta_ref = _identity_delta_ref(
                    run_id=run_kernel.state.run_id,
                    iteration=iteration,
                    identity_refs=delta_identities,
                )
                identity_deltas_by_digest[str(delta_ref["identity_set_delta_digest"])] = delta_identities
                wave_packet = dict(wave.get("candidate_packet") or {})
                if wave_packet:
                    wave_packet_ref = search_result_candidate_packet_ref_from_packet(wave_packet)
                    packets_by_id[wave_packet_ref["packet_id"]] = wave_packet
                    selected_refs = _candidate_refs(wave_packet)
                    wave_binding_state = derive_selected_candidate_material_need_bindings(
                        run_kernel=run_kernel,
                        candidate_packet=wave_packet,
                        query_plan=query_authority.plan,
                        discovery_result_store=discovery_result_store,
                    )
                    wave_bindings = _bindings_from_state(wave_binding_state)
                    material_refs = _material_refs(wave_bindings)
                else:
                    selected_refs = []
                    wave_bindings = []
                    material_refs = []
                candidate_set = build_searchos_iteration_candidate_set_v1(
                    run_id=run_kernel.state.run_id,
                    request_id=run_kernel.state.request_id,
                    iteration=iteration,
                    parent_candidate_state_ref=parent_ref,
                    slot_ref=run_kernel.state.searchos_state["slots_by_id"][slot_id]["slot_ref"],
                    query_plan_item_ref=query_admission["query_plan_item_ref"],
                    provider_plan_ref=dict(wave["provider_plan_ref"]),
                    route_refs=list(wave.get("route_refs") or ()),
                    retrieval_action_refs=list(wave.get("retrieval_action_refs") or ()),
                    ordered_provider_result_occurrence_refs=delta_identities,
                    identity_set_delta_ref=delta_ref,
                    selected_candidate_refs=selected_refs,
                    bounded_candidate_material_refs=material_refs,
                    selection_facts=dict(wave.get("selection_facts") or {}),
                    overflow_facts=dict(wave.get("overflow_facts") or {}),
                    zero_useful_result=not bool(selected_refs),
                )
                candidate_action = run_kernel.authorize_searchos_iteration_candidate_admission(
                    candidate_set=candidate_set
                )
                run_kernel.reduce(
                    Observation.from_action(
                        candidate_action,
                        observation_type=(ObservationType.SEARCHOS_ITERATION_CANDIDATES_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"candidate_set": candidate_set},
                    )
                )
                iteration_sets.append(candidate_set)
                iteration_ref = deepcopy(run_kernel.state.searchos_state["current_candidate_state_ref"])
                bindings.extend(wave_bindings)
                for binding in bindings:
                    binding_candidate_states[binding.binding_id] = iteration_ref
                for binding in wave_bindings:
                    binding_iteration_refs[binding.binding_id] = iteration_ref
                if wave.get("followup_failure_reason"):
                    run_kernel.mark_searchos_slot_stale_or_invalid(
                        slot_id=slot_id,
                        reason=(
                            "followup_discover_failed:"
                            + str(wave["followup_failure_reason"])
                        )[:240],
                    )
            elif decision_action is (SearchOSJudgmentAction.HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION):
                handoff_action = run_kernel.authorize_searchos_semantic_handoff(
                    slot_id=slot_id,
                    judgment_decision_ref=decision,
                    read_custody_material_refs=decision["read_custody_refs"],
                )
                run_kernel.reduce(
                    Observation.from_action(
                        handoff_action,
                        observation_type=(ObservationType.SEARCHOS_SEMANTIC_HANDOFF_ADMITTED),
                        status=RunStageStatus.COMPLETED,
                        payload={"semantic_handoff": handoff_action.inputs["semantic_handoff"]},
                    )
                )
                semantic_handoffs.append(deepcopy(handoff_action.inputs["semantic_handoff"]))

    semantic_material = _semantic_passages(
        semantic_handoffs=semantic_handoffs,
        packet_by_custody_id=packet_by_custody_id,
    )
    append_only_proof = validate_searchos_append_only_lineage(
        revision_1=revision_1,
        initial_query_plan_items=initial_query_items,
        current_query_plan_items=[item.to_dict() for item in query_authority.plan.items],
        initial_identity_refs=initial_identities,
        iteration_candidate_sets=iteration_sets,
        identity_deltas_by_digest=identity_deltas_by_digest,
        current_identity_refs=[item.ref() for item in discovery_result_store.identities()],
    )
    final_state = run_kernel.state.searchos_state
    projection = {
        "schema_version": "searchos_slice_a_product_runtime_v1",
        "owner": "RunKernel.SearchOSIterativeJudgment",
        "revision_1_ref": revision_ref,
        "iteration_candidate_set_refs": deepcopy(final_state["iteration_candidate_set_refs"]),
        "append_only_lineage_proof_ref": {
            "lineage_proof_id": append_only_proof["lineage_proof_id"],
            "lineage_proof_digest": append_only_proof["lineage_proof_digest"],
        },
        "semantic_handoff_refs": deepcopy(final_state["semantic_handoff_refs"]),
        "semantic_material_refs": [
            {
                "source_id": item.get("source_id"),
                "url": item.get("url"),
                "bounded_character_count": len(str(item.get("text") or "")),
                "slot_ref": deepcopy(item.get("searchos_slot_ref")),
            }
            for item in semantic_material
        ],
        "slot_postures": {
            slot_id: final_state["slots_by_id"][slot_id]["posture"] for slot_id in final_state["active_slot_ids"]
        },
        "directional_candidate_context_support_eligible": False,
        "read_custody_is_only_support_proposal_eligible_material": True,
        "all_passages_iteration_append_count": 0,
        "standalone_read_assessment_invoked": False,
        "evaluator_invoked_after_first_wave": False,
        "expander_invoked_after_first_wave": False,
        "disambiguation_invoked_after_first_wave": False,
        "weak_corpus_recovery_invoked_after_first_wave": False,
        "ag92b_full_search_judgment_invoked": False,
        "provider_calls_attempted": attempted,
        "provider_calls_completed": completed,
    }
    return SearchOSSliceAProductResult(
        revision_1=revision_1,
        iteration_candidate_sets=tuple(iteration_sets),
        semantic_handoffs=tuple(semantic_handoffs),
        searchos_semantic_material=tuple(semantic_material),
        projection=projection,
        provider_calls_attempted=attempted,
        provider_calls_completed=completed,
    )


def revision_1_answer_contract_ref(
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    ref = candidate_packet.get("answer_contract_ref")
    if not isinstance(ref, Mapping) or not ref:
        raise SearchOSRuntimeError("revision 1 lacks accepted AnswerContract ref")
    contract = dict(ref)
    digest = str(contract.get("contract_digest") or "")
    version = str(contract.get("contract_version") or "")
    if len(digest) != 64 or not version:
        raise SearchOSRuntimeError("revision 1 AnswerContract ref is incomplete")
    return {
        "answer_contract_id": f"accepted-answer-contract:{digest[:24]}",
        "answer_contract_digest": digest,
        "contract_version": version,
        "source": contract.get("source"),
    }


def _active_slots(run_kernel: RunKernel) -> list[dict[str, Any]]:
    snapshot = run_kernel.acquisition_authority_snapshot()
    components = dict(snapshot.get("components_by_id") or {})
    obligations = dict(snapshot.get("source_obligations_by_id") or {})
    work_components = list(run_kernel.state.search_work_plan.get("components") or ())
    slots: list[dict[str, Any]] = []
    for work_component in work_components:
        if not isinstance(work_component, Mapping):
            continue
        component_id = str(work_component.get("component_id") or "")
        component_ref = dict(components.get(component_id) or {})
        requirement = work_component.get("requirement_posture")
        if requirement not in {"required", "optional"}:
            accepted_component = next(
                (
                    dict(item)
                    for item in (run_kernel.state.initial_answer_contract.get("accepted_answer_component_refs") or ())
                    if isinstance(item, Mapping) and item.get("component_id") == component_id
                ),
                {},
            )
            requirement = accepted_component.get("requirement_posture")
        if requirement not in {"required", "optional"}:
            raise SearchOSRuntimeError("accepted component required-versus-optional posture is ambiguous")
        for raw_obligation in work_component.get("source_obligations") or ():
            obligation = dict(raw_obligation) if isinstance(raw_obligation, Mapping) else {}
            obligation_id = str(obligation.get("obligation_id") or obligation.get("source_obligation_id") or "")
            obligation_ref = dict(obligations.get(obligation_id) or {})
            strictness = str(obligation.get("strictness") or "")
            if strictness not in {"required", "preferred", "contextual"}:
                raise SearchOSRuntimeError("source-obligation strictness is ambiguous")
            slot_requirement = "required" if requirement == "required" and strictness == "required" else "optional"
            slots.append(
                {
                    "slot_id": (f"search-judgment-read-slot:{component_id}:{obligation_id}"),
                    "component_ref": component_ref,
                    "source_obligation_ref": obligation_ref,
                    "requirement_posture": slot_requirement,
                }
            )
    if not slots:
        raise SearchOSRuntimeError("SearchOS Slice A has no active component slots")
    return slots


def _bindings_from_state(
    binding_state: Mapping[str, Any],
) -> list[SelectedCandidateMaterialNeedBindingV1]:
    return [
        SelectedCandidateMaterialNeedBindingV1.from_dict(item)
        for item in binding_state.get("bindings") or ()
        if isinstance(item, Mapping)
    ]


def _candidate_refs(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    packet_ref = search_result_candidate_packet_ref_from_packet(packet)
    return [
        {
            "packet_id": packet_ref["packet_id"],
            "packet_digest": packet_ref["packet_digest"],
            "candidate_id": item.get("candidate_id"),
            "candidate_digest": item.get("candidate_digest"),
            "record_digest": item.get("record_digest"),
            "normalized_url": item.get("normalized_url"),
        }
        for item in packet.get("candidate_records") or ()
        if isinstance(item, Mapping)
    ]


def _material_refs(
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for binding in bindings:
        ref = dict(binding.source_material_ref)
        if ref not in refs:
            refs.append(ref)
    return refs


def _candidate_option_inputs(
    *,
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    slot_ref: Mapping[str, Any],
    binding_candidate_states: Mapping[str, Mapping[str, Any]],
    binding_iteration_refs: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
) -> list[dict[str, Any]]:
    slot_id = slot_ref.get("slot_id")
    rows: list[dict[str, Any]] = []
    for binding in bindings:
        if binding.slot_id() != slot_id:
            continue
        material = discovery_result_store.material_for_ref(binding.source_material_ref)
        if material is None:
            continue
        rows.append(
            {
                "slot_ref": dict(slot_ref),
                "normalized_url": binding.normalized_url,
                "candidate_state_ref": dict(binding_candidate_states[binding.binding_id]),
                "candidate_ref": dict(binding.candidate_ref),
                "query_plan_item_ref": dict(binding.query_plan_item_ref),
                "iteration_set_ref": dict(binding_iteration_refs.get(binding.binding_id) or {}),
                "provider_result_occurrence_ref": dict(binding.contributing_source_result_ref),
                "source_material_ref": dict(binding.source_material_ref),
                "title": str(material.title or "")[:220],
                "snippet": str(material.snippet or "")[:500],
            }
        )
    return rows


def _prepare_candidate_window(
    *,
    slot: Mapping[str, Any],
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    binding_candidate_states: Mapping[str, Mapping[str, Any]],
    binding_iteration_refs: Mapping[str, Mapping[str, Any]],
    discovery_result_store: Any,
    policy_snapshot: Mapping[str, Any],
    dispositions: Mapping[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    option_inputs = _candidate_option_inputs(
        bindings=bindings,
        slot_ref=dict(slot["slot_ref"]),
        binding_candidate_states=binding_candidate_states,
        binding_iteration_refs=binding_iteration_refs,
        discovery_result_store=discovery_result_store,
    )
    options = build_candidate_use_options_v1(option_inputs)
    window_ordinal = max(1, int(slot.get("candidate_window_count") or 0))
    window_dispositions = {
        option_id: disposition
        for option_id, disposition in dispositions.items()
        if disposition in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
    }
    window = build_candidate_use_window_v1(
        slot_ref=dict(slot["slot_ref"]),
        ordered_options=options,
        window_ordinal=window_ordinal,
        policy_snapshot=policy_snapshot,
        option_dispositions=window_dispositions,
    )
    while (
        window["ordered_candidate_use_option_refs"]
        and all(
            dispositions.get(ref["candidate_use_option_id"])
            in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
            for ref in window["ordered_candidate_use_option_refs"]
        )
        and window["next_window_available"]
    ):
        window_ordinal += 1
        window = build_candidate_use_window_v1(
            slot_ref=dict(slot["slot_ref"]),
            ordered_options=options,
            window_ordinal=window_ordinal,
            policy_snapshot=policy_snapshot,
            option_dispositions=window_dispositions,
        )
    exhausted = bool(
        window["ordered_candidate_use_option_refs"]
        and all(
            dispositions.get(ref["candidate_use_option_id"])
            in TERMINAL_CANDIDATE_OPTION_DISPOSITIONS
            for ref in window["ordered_candidate_use_option_refs"]
        )
        and not window["next_window_available"]
    )
    reason = None
    if exhausted:
        reason = (
            "candidate_window_budget_exhausted"
            if window["remaining_option_count"] > 0
            else "candidate_options_exhausted"
        )
    return options, window, reason


def _binding_for_option(
    *,
    bindings: Sequence[SelectedCandidateMaterialNeedBindingV1],
    slot_id: str,
    option_ref: Mapping[str, Any],
    options: Sequence[Mapping[str, Any]],
) -> SelectedCandidateMaterialNeedBindingV1:
    option = next(
        (item for item in options if item.get("candidate_use_option_id") == option_ref.get("candidate_use_option_id")),
        None,
    )
    if option is None or candidate_use_option_ref(option) != dict(option_ref):
        raise SearchOSRuntimeError("READ option is stale")
    candidate_ids = {
        str(item.get("candidate_id") or "") for item in option.get("candidate_refs") or () if isinstance(item, Mapping)
    }
    binding = next(
        (
            item
            for item in bindings
            if item.slot_id() == slot_id
            and item.normalized_url == option_ref.get("normalized_url")
            and item.candidate_ref.get("candidate_id") in candidate_ids
        ),
        None,
    )
    if binding is None:
        raise SearchOSRuntimeError("READ option has no current admitted binding")
    return binding


def _invoke_judgment_model(
    *,
    request: Mapping[str, Any],
    ask_model: Callable[..., Any] | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    measure_context_stage: Callable[..., Any] | None,
) -> Any:
    if ask_model is None:
        raise SearchOSRuntimeError("model_unavailable")
    prompt = json.dumps(request, sort_keys=True, ensure_ascii=False)
    if measure_context_stage is not None:
        measure_context_stage(
            "searchos_iterative_judgment",
            prompt=prompt,
            system_prompt=SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
            evidence_texts=[],
        )
    return ask_model(
        prompt,
        SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
        provider=provider,
        model=model,
        effort="high",
        base_url=base_url,
        api_key=api_key,
        require_json=True,
        use_reasoning=use_reasoning,
    )


def _strict_json_object(raw: Any) -> dict[str, Any]:
    parsed = raw if isinstance(raw, Mapping) else json.loads(str(raw))
    if not isinstance(parsed, Mapping):
        raise SearchOSRuntimeError("model_output_not_object")
    return dict(parsed)


def _failure_reason(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "model_output_malformed"
    if isinstance(exc, SearchOSRuntimeError):
        detail = str(exc).strip().casefold().replace(" ", "_")
        return ("model_output_invalid:" + detail)[:240]
    return f"model_transport_failed:{type(exc).__name__}"


def _invalid_or_stale_nomination(exc: Exception) -> bool:
    if not isinstance(exc, SearchOSRuntimeError):
        return False
    detail = str(exc).casefold()
    return any(
        token in detail
        for token in (
            "nomination",
            "outside current candidate window",
            "stale or altered",
        )
    )


def _read_failure_reason(exc: Exception) -> str:
    raw_code = getattr(exc, "code", None)
    code = str(raw_code) if raw_code else type(exc).__name__
    if "transport" in code.casefold():
        posture = "read_transport_failure"
    elif any(
        token in code.casefold()
        for token in ("unreadable", "empty", "content", "material")
    ):
        posture = "read_source_insufficient"
    else:
        posture = "read_authority_or_route_blocked"
    return f"{posture}:{code}"[:240]


def _profile_name(value: str) -> str:
    token = str(value or "").strip().casefold()
    return {"fast": "Fast", "balanced": "Balanced", "deep": "Deep"}.get(
        token,
        "Balanced",
    )


def _identity_delta_ref(*, run_id: str, iteration: int, identity_refs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    refs = [deepcopy(dict(item)) for item in identity_refs]
    refs_digest = _digest(refs)
    core = {
        "run_id": run_id,
        "iteration": iteration,
        "identity_count": len(refs),
        "identity_refs_digest": refs_digest,
    }
    digest = _digest(core)
    return {
        "identity_set_delta_id": f"searchos-identity-delta:{digest[:24]}",
        "identity_set_delta_digest": digest,
        **core,
    }


def _decision_ref(decision: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "judgment_decision_id": decision.get("judgment_decision_id"),
        "judgment_decision_digest": decision.get("judgment_decision_digest"),
    }


def _mark_budget_exhausted(run_kernel: RunKernel, slot_id: str) -> None:
    run_kernel.mark_searchos_slot_budget_exhausted(
        slot_id=slot_id,
        reason="judgment_call_budget_exhausted",
    )


def build_searchos_semantic_outcomes_by_slot(
    *,
    searchos_state: Mapping[str, Any],
    semantic_handoffs: Sequence[Mapping[str, Any]],
    searchos_semantic_material: Sequence[Mapping[str, Any]],
    component_admission_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bind each slot to the exact installed component semantic chain."""

    handoffs = {
        str(dict(item.get("slot_ref") or {}).get("slot_id") or ""): dict(item)
        for item in semantic_handoffs
        if isinstance(item, Mapping)
    }
    admissions = {
        str(item.get("component_id") or ""): dict(item)
        for item in component_admission_projection.get("component_admission_refs") or ()
        if isinstance(item, Mapping)
    }
    material_source_ids_by_slot: dict[str, set[str]] = {}
    for item in searchos_semantic_material:
        if not isinstance(item, Mapping):
            continue
        slot_ref = dict(item.get("searchos_slot_ref") or item.get("slot_ref") or {})
        slot_id = str(slot_ref.get("slot_id") or "")
        source_id = str(item.get("searchos_evidence_ledger_candidate_id") or item.get("source_id") or "")
        if slot_id and source_id:
            material_source_ids_by_slot.setdefault(slot_id, set()).add(source_id)

    outcomes: dict[str, dict[str, Any]] = {}
    slots_by_id = dict(searchos_state.get("slots_by_id") or {})
    for slot_id in searchos_state.get("active_slot_ids") or ():
        slot = dict(slots_by_id.get(slot_id) or {})
        slot_ref = dict(slot.get("slot_ref") or {})
        component_id = str(
            slot_ref.get("component_id") or dict(slot_ref.get("component_ref") or {}).get("component_id") or ""
        )
        handoff = handoffs.get(str(slot_id), {})
        admission = admissions.get(component_id, {})
        evidence_ids = {
            str(item.get("evidence_ref_id") or "")
            for item in admission.get("evidence_refs") or ()
            if isinstance(item, Mapping)
        }
        material_consumed = bool(material_source_ids_by_slot.get(str(slot_id), set()) & evidence_ids)
        admitted = bool(
            admission.get("admission_status") in {"admitted", "admitted_with_caveats"} and material_consumed and handoff
        )
        outcomes[str(slot_id)] = {
            "semantic_handoff_ref": (
                {
                    "semantic_handoff_id": handoff.get("semantic_handoff_id"),
                    "semantic_handoff_digest": handoff.get("semantic_handoff_digest"),
                }
                if handoff
                else {}
            ),
            "component_analyst_proposal_ref": (
                dict(admission.get("analyst_finding_ref") or {}) if material_consumed else {}
            ),
            "component_analyst_proposal_status": ("proposed" if material_consumed else "not_proposed"),
            "component_dprime_validation_ref": (
                dict(admission.get("dprime_validation_ref") or {}) if material_consumed else {}
            ),
            "component_dprime_validation_status": ("accepted" if admitted else "not_accepted"),
            "semantic_admission_outcome_ref": (
                {
                    "action_id": admission.get("action_id"),
                    "component_id": admission.get("component_id"),
                    "component_revision": admission.get("component_revision"),
                    "component_digest": admission.get("component_digest"),
                    "admission_status": admission.get("admission_status"),
                }
                if admitted
                else {}
            ),
            "semantic_admission_status": "admitted" if admitted else "not_admitted",
            "material_authority": "read_custody_material",
            "searchos_handoff_material_consumed": material_consumed,
        }
    return outcomes


def build_searchos_required_needs_blocked_fap_projection(
    *,
    required_needs_block: Mapping[str, Any],
    readiness_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt the canonical SearchOS block to the installed safe FAP terminal."""

    unresolved = [
        dict(item) for item in required_needs_block.get("unresolved_required_slots") or () if isinstance(item, Mapping)
    ]
    reasons = [
        "SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED:"
        + str(dict(item.get("slot_ref") or {}).get("slot_id") or "unknown-slot")
        + ":"
        + str(item.get("reason") or "unresolved")
        for item in unresolved
    ]
    authority_payload = {
        "status": "blocked",
        "readiness_status": "required_needs_unresolved",
        "readiness_reasons": reasons,
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "final_answer_posture": "blocked_searchos_required_needs_unresolved",
        "missing_source_obligation_count": len(unresolved),
        "satisfied_source_obligation_count": int(readiness_projection.get("required_ready_count") or 0),
        "final_answer_allowed": False,
        "author_execution_allowed": False,
        "safe_blocked_non_author_terminal": True,
        "searchos_required_needs_block_ref": {
            "block_id": required_needs_block.get("block_id"),
            "block_digest": required_needs_block.get("block_digest"),
            "block_type": required_needs_block.get("block_type"),
        },
    }
    return {
        "schema_version": "searchos_slice_a_blocked_fap_adapter_v1",
        **authority_payload,
        "author_payload_ref": {
            "schema_version": "searchos_slice_a_blocked_author_payload_ref_v1",
            **authority_payload,
            "authority_payload": dict(authority_payload),
        },
    }


def _semantic_passages(
    *,
    semantic_handoffs: Sequence[Mapping[str, Any]],
    packet_by_custody_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for handoff in semantic_handoffs:
        for custody in handoff.get("read_custody_material_refs") or ():
            if not isinstance(custody, Mapping):
                continue
            custody_id = str(custody.get("read_custody_material_id") or "")
            packet = packet_by_custody_id.get(custody_id) or {}
            for reference in packet.get("reference_records") or ():
                if not isinstance(reference, Mapping):
                    continue
                key = (
                    str(reference.get("reference_id") or ""),
                    str(handoff.get("semantic_handoff_id") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                passages.append(
                    {
                        "candidate_id": custody.get("evidence_ledger_candidate_id"),
                        "source_id": custody.get("evidence_ledger_candidate_id"),
                        "searchos_evidence_ledger_candidate_id": custody.get("evidence_ledger_candidate_id"),
                        "url": reference.get("canonical_url")
                        or reference.get("final_url")
                        or reference.get("resolved_url")
                        or reference.get("provider_reported_url")
                        or reference.get("attempted_url"),
                        "title": reference.get("content_title") or "Read source",
                        "text": reference.get("bounded_text") or "",
                        "score": 1.0,
                        "credibility": 3,
                        "_provider": "searchos_read_custody",
                        "material_authority": "read_custody_material",
                        "searchos_semantic_handoff_ref": {
                            "semantic_handoff_id": handoff.get("semantic_handoff_id"),
                            "semantic_handoff_digest": handoff.get("semantic_handoff_digest"),
                        },
                        "searchos_slot_ref": deepcopy(handoff.get("slot_ref")),
                        "support_admitted": False,
                    }
                )
    return passages


def _acquisition_provider_call_totals(run_kernel: RunKernel) -> tuple[int, int]:
    control = dict(run_kernel.state.acquisition_control_state or {})
    observations = list(
        dict(control.get("execution_observations_by_id") or {}).values()
    )
    return (
        sum(
            int(dict(item).get("provider_calls_attempted") or 0)
            for item in observations
            if isinstance(item, Mapping)
        ),
        sum(
            int(dict(item).get("provider_calls_completed") or 0)
            for item in observations
            if isinstance(item, Mapping)
        ),
    )


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "SEARCHOS_JUDGMENT_SYSTEM_PROMPT",
    "SEARCHOS_SLICE_A_TRACE_KEY",
    "SearchOSSliceAProductResult",
    "build_searchos_required_needs_blocked_fap_projection",
    "build_searchos_semantic_outcomes_by_slot",
    "execute_searchos_slice_a_iterative_judgment",
]
