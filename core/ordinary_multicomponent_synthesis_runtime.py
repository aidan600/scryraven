"""Ordinary product-consumed bounded multi-component synthesis lane.

The eligibility decision is made before semantic production.  A qualifying
run therefore executes only component Analyst -> component D-prime ->
RunKernel admission; it never executes the direct semantic producer and then
chooses between competing outputs.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any, Mapping, Sequence

from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_STAGE,
    admit_synthesis_node_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    component_work_graph_v1_resynthesis_from_cross_component_artifact,
    component_work_graph_v1_selective_resynthesis_from_cross_artifact,
    cross_component_input_packet,
    derive_multicomponent_role_call_accounting,
    derive_selective_recomputation_closure,
    finalize_component_work_graph_v1,
    graph_with_accounting,
    graph_with_scrutineer,
    graph_with_synthesis_validation,
    reduce_component_work_graph_v1,
    reduce_selective_invalidation_via_runkernel,
    reduce_selective_recomputation_closure,
    scrutineer_input_packet,
    selective_cross_component_input_packet,
    synthesis_dprime_input_packet,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.multicomponent_component_admission import (
    component_analyst_input_packet,
    component_dprime_input_packet,
    execute_multicomponent_component_admission,
)
from core.multicomponent_dynamic_recovery_runtime import (
    MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
    RECOVERY_DISPOSITION_ACQUIRED,
    RECOVERY_DISPOSITION_BLOCKED_COMPONENT_ADMISSION,
    RECOVERY_DISPOSITION_BLOCKED_REQUIRES_CONFIRMATION,
    RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS,
    RECOVERY_STATUS_BLOCKED,
    apply_recovered_component_amendment,
    execute_recovery_acquisition,
    reduce_recovery_outcome,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    SELECTIVE_CROSS_COMPONENT_SCHEMA,
    SafeMulticomponentWorkerResult,
    execute_prepared_multicomponent_transport,
    failed_unstarted_multicomponent_worker_result,
    prepare_multicomponent_transport_call,
    reduce_multicomponent_worker_result,
    safe_packet_digest,
)
from core.multicomponent_role_runtime import (
    execute_multicomponent_role_call as _execute_multicomponent_role_transport,
)
from core.ordinary_semantic_producer_runtime import (
    OrdinarySemanticProducerHandoffResult,
    build_component_coverage_proposal,
    build_question_meaning_record_from_search_work_plan,
    build_sanitized_content_reference_from_passage,
    execute_ordinary_semantic_producer_handoff_from_scope,
    select_bindable_final_passages_for_components,
    source_requirement_ids_for_component_candidate,
)
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)
from core.semantic_observation_foundation import (
    ObservationKind,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)


class OrdinaryMulticomponentStatus(str, Enum):
    NOT_QUALIFIED = "not_qualified"
    SELECTED_PENDING = "selected_pending"
    COMPLETED = "completed"
    ALREADY_COMPLETED = "already_completed"


@dataclass(frozen=True, slots=True)
class OrdinaryMulticomponentResult:
    status: OrdinaryMulticomponentStatus
    direct_handoff: OrdinarySemanticProducerHandoffResult | None = None


class OrdinaryMulticomponentRuntimeError(RuntimeError):
    """Raised when a selected typed lane cannot complete without fallback."""


class _ScheduledSemanticWorkBlocked(RuntimeError):
    """Internal control transfer from canonical scheduler blockage to FAP."""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def execute_multicomponent_role_call(
    *,
    run_kernel: Any,
    role: str,
    input_packet: Mapping[str, Any],
    logical_evaluation_key: str,
    output_schema_variant: str | None = None,
    **runtime_kwargs: Any,
) -> dict[str, Any]:
    """Consume only the first exact RunKernel-ready work item and its lease."""

    from core.multicomponent_graph_scheduling import (
        LEASE_DENIED_EXHAUSTED,
        MULTICOMPONENT_SCHEDULER_STAGE,
    )

    if not run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE):
        # Historical/component tests without a qualifying product scheduler keep
        # their established direct RunKernel role authorization contract.
        return _execute_multicomponent_role_transport(
            run_kernel=run_kernel,
            role=role,
            input_packet=input_packet,
            logical_evaluation_key=logical_evaluation_key,
            output_schema_variant=output_schema_variant,
            **runtime_kwargs,
        )
    lease = run_kernel.grant_next_multicomponent_work_lease()
    work = _safe_mapping(lease.get("work"))
    if lease.get("status") == LEASE_DENIED_EXHAUSTED:
        raise _ScheduledSemanticWorkBlocked(
            "required semantic work denied by the compatibility envelope"
        )
    if (
        work.get("role") != role
        or work.get("logical_evaluation_key") != logical_evaluation_key
        or work.get("input_packet_digest") != safe_packet_digest(input_packet)
        or work.get("output_schema_variant") != output_schema_variant
    ):
        run_kernel.cancel_multicomponent_work_lease(
            lease_id=str(lease.get("lease_id") or ""),
            reason="deterministic_consumer_did_not_match_scheduler_ready_work",
        )
        raise OrdinaryMulticomponentRuntimeError(
            "ordinary deterministic transition requested work other than the "
            "RunKernel-selected first ready item"
        )
    try:
        return _execute_multicomponent_role_transport(
            run_kernel=run_kernel,
            role=role,
            input_packet=input_packet,
            logical_evaluation_key=logical_evaluation_key,
            output_schema_variant=output_schema_variant,
            lease_id=str(lease["lease_id"]),
            **runtime_kwargs,
        )
    except Exception as exc:
        scheduler = _safe_mapping(
            run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        if str(scheduler.get("status") or "").startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked(
                "required scheduled semantic work did not complete"
            ) from exc
        raise


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _real_query_shape_plan(search_work_plan: Mapping[str, Any]) -> bool:
    metadata = _safe_mapping(search_work_plan.get("metadata"))
    construction = _safe_mapping(metadata.get("construction_metadata"))
    if construction.get("runtime_shadow_scaffolding") is True:
        return False
    if _clean_text(construction.get("fallback_reason")):
        return False
    return (
        construction.get("implements_query_shape_classifier") is True
        or metadata.get("implements_query_shape_classifier") is True
    )


def _accepted_contract_ref(accepted: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": accepted.get("owner"),
        "canonical_state": accepted.get("canonical_state") is True,
        "run_id": accepted.get("run_id"),
        "request_id": accepted.get("request_id"),
        "accepted_contract_version": accepted.get("accepted_contract_version"),
        "accepted_contract_digest": accepted.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": accepted.get(
            "parent_question_meaning_record_id"
        ),
        "parent_question_meaning_record_digest": accepted.get(
            "parent_question_meaning_record_digest"
        ),
        "accepted_answer_component_count": accepted.get(
            "accepted_answer_component_count"
        ),
    }


def _accept_question_meaning_record(run_kernel: Any, qmr: Any) -> None:
    from core.run_kernel import Observation, ObservationType, RunStageStatus

    action = run_kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=qmr.record_id,
        parent_proposal_digest=qmr.record_digest,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": qmr.to_dict()},
        )
    )


def _role_runtime_kwargs(runtime_scope: Mapping[str, Any]) -> dict[str, Any]:
    from core.strict_one_shot_model_transport import (
        build_strict_one_shot_smart_model_transport,
        normalize_canonical_model_provider,
    )

    deps = runtime_scope.get("deps")
    cleaner = getattr(deps, "clean_json_response", None)
    transport = runtime_scope.get("strict_one_shot_smart_model_transport")
    if not callable(transport) and deps is not None:
        transport = getattr(deps, "strict_one_shot_smart_model_transport", None)
    canonical_provider = normalize_canonical_model_provider(
        runtime_scope.get("smart_provider")
    )
    model = str(runtime_scope.get("smart_model") or "")
    if not callable(transport):
        transport = build_strict_one_shot_smart_model_transport(
            smart_provider=canonical_provider,
            smart_model=model,
            local_url=str(runtime_scope.get("local_url") or "") or None,
            openrouter_api_key=str(runtime_scope.get("or_api_key") or "") or None,
        )
    return {
        "strict_one_shot_transport": transport,
        "clean_json_response": cleaner if callable(cleaner) else None,
        "provider": canonical_provider,
        "model": model,
        "use_reasoning": bool(runtime_scope.get("use_reasoning")),
    }


def _component_text_by_id(qmr: Any) -> dict[str, str]:
    return {
        component.component_id: component.user_facing_question
        for component in qmr.answer_components
    }


def _accepted_component_text_by_id(
    accepted: Mapping[str, Any],
) -> dict[str, str]:
    return {
        str(component["component_id"]): str(component["user_facing_question"])
        for component in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(component, Mapping)
        and component.get("component_id")
        and component.get("user_facing_question")
    }


def _selected_multicomponent_contract(
    accepted: Mapping[str, Any],
) -> bool:
    metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
    component_refs = [
        item
        for item in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    return (
        metadata.get("explicit_factual_component_list") is True
        and _clean_text(metadata.get("requested_synthesis_directive"), limit=360)
        is not None
        and 2 <= len(component_refs) <= 5
    )


def _structured_evidence_fact(
    *,
    candidate: Mapping[str, Any],
    passage: Mapping[str, Any],
    candidate_keys: Sequence[str],
    passage_keys: Sequence[str],
    limit: int = 120,
) -> str | None:
    """Prefer one exact candidate fact, then an uncontradicted passage fact."""

    for owner, keys in ((candidate, candidate_keys), (passage, passage_keys)):
        for key in keys:
            value = _clean_text(owner.get(key), limit=limit)
            if value and value.casefold() != "unknown":
                return value
    return None


def _exact_conflict_facts(
    *, candidate: Mapping[str, Any], passage: Mapping[str, Any]
) -> tuple[str | None, bool | None]:
    for owner in (candidate, passage):
        conflict = _clean_text(owner.get("conflict_posture"), limit=80)
        if conflict and conflict.casefold() != "unknown":
            return conflict, conflict.casefold() == "present"
        contradictory = owner.get("contradictory")
        if isinstance(contradictory, bool):
            return ("present" if contradictory else "none"), contradictory
        disposition = _clean_text(
            owner.get("fact_disposition") or owner.get("disposition"),
            limit=80,
        )
        if disposition and disposition.casefold() in {"contradicted", "contested"}:
            return "present", True
    return None, None


def _exact_currency_fact(
    *, candidate: Mapping[str, Any], passage: Mapping[str, Any]
) -> str | None:
    for owner in (candidate, passage):
        value = owner.get("canonical_currency_unit")
        if isinstance(value, str):
            token = value.strip()
            if len(token) == 3 and token.isascii() and token.isalpha():
                return token.upper()
    return None


def _evidence_input(bindable: Any | None) -> dict[str, Any]:
    if bindable is None:
        return {
            "evidence_status": "missing",
            "bounded_text": None,
            "candidate_custody_ref": {},
        }
    passage = bindable.passage
    candidate = _safe_mapping(bindable.candidate_record)
    source_class = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("source_class",),
        passage_keys=("source_class",),
    )
    source_tier = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("source_tier",),
        passage_keys=("source_tier",),
    )
    currentness = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("currentness_signal", "currentness"),
        passage_keys=("currentness_signal", "currentness"),
    )
    fact_disposition = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("fact_disposition", "disposition"),
        passage_keys=("fact_disposition", "disposition"),
        limit=80,
    )
    readability = _structured_evidence_fact(
        candidate=candidate,
        passage=passage,
        candidate_keys=("readable_status", "readability_status"),
        passage_keys=("readable_status", "readability_status"),
        limit=80,
    )
    canonical_currency = _exact_currency_fact(
        candidate=candidate, passage=passage
    )
    conflict, contradictory = _exact_conflict_facts(
        candidate=candidate, passage=passage
    )
    custody = {
        key: candidate.get(key)
        for key in (
            "candidate_id",
            "source_class",
            "source_tier",
            "fact_disposition",
            "readable_status",
            "currentness_signal",
            "conflict_posture",
            "contradictory",
            "canonical_currency_unit",
        )
        if candidate.get(key) is not None
    }
    result = {
        "evidence_status": "available",
        "evidence_ref_id": bindable.evidence_ref_id,
        "source_title": _clean_text(passage.get("title"), limit=240),
        "source_url": _clean_text(passage.get("url"), limit=500),
        "bounded_text": _clean_text(passage.get("text"), limit=6000),
        "currentness": currentness,
        "source_class": source_class,
        "source_tier": source_tier,
        "fact_disposition": fact_disposition,
        "readability_posture": readability,
        "conflict_posture": conflict,
        "canonical_currency_unit": canonical_currency,
        "candidate_custody_ref": custody,
    }
    if contradictory is not None:
        result["contradictory"] = contradictory
    return result


def _semantic_material(
    *,
    run_kernel: Any,
    component_ref: Mapping[str, Any],
    bindable: Any | None,
    analyst_artifact: Mapping[str, Any],
    dprime_artifact: Mapping[str, Any],
    query: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any] | None]:
    analyst_output = _safe_mapping(analyst_artifact.get("semantic_output"))
    dprime_output = _safe_mapping(dprime_artifact.get("semantic_output"))
    supported = analyst_output.get("support_status") in {
        "supported",
        "supported_with_caveats",
    } and dprime_output.get("validation_status") in {
        "supported",
        "supported_with_caveats",
    }
    if not supported:
        return None, [], None
    if bindable is None:
        raise OrdinaryMulticomponentRuntimeError(
            "component roles claimed support without bounded evidence"
        )
    accepted = (
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    component_id = str(component_ref["component_id"])
    content_ref = build_sanitized_content_reference_from_passage(
        passage=bindable.passage,
        evidence_ref_id=bindable.evidence_ref_id,
        accepted_contract=accepted,
        component_ref=component_ref,
        content_ref_id=f"content:{component_id}:{bindable.evidence_ref_id}",
    )
    observation = SemanticObservation(
        observation_id=f"observation:{component_id}:{bindable.evidence_ref_id}",
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted[
            "parent_question_meaning_record_id"
        ],
        question_meaning_record_digest=accepted[
            "parent_question_meaning_record_digest"
        ],
        contract_version=accepted["accepted_contract_version"],
        contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_id,
        component_revision=str(component_ref["component_revision"]),
        component_contract_digest=str(component_ref["component_digest"]),
        evidence_refs=(bindable.evidence_ref_id,),
        content_refs=(content_ref.content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value=str(analyst_output["claim_text"]),
        normalization_fit="component Analyst nominated claim",
        scope_fit="accepted answer component",
        assumption_fit="bounded selected evidence excerpt",
        inference_depth=0,
        metadata={
            "phase": "AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01",
            "producer_lane": "component_analyst_then_component_dprime",
            "analyst_artifact_digest": analyst_artifact.get("artifact_digest"),
            "dprime_artifact_digest": dprime_artifact.get("artifact_digest"),
            "direct_semantic_producer_used": False,
        },
    ).require_valid()
    coverage = build_component_coverage_proposal(
        accepted_contract=accepted,
        observation=observation,
        content_ref=content_ref,
        evidence_ledger_projection=(
            run_kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        query=query,
        ignore_satisfied_provider_job_historical_gaps=True,
    )
    if coverage is None:
        obligation_ids = list(
            component_ref.get("source_obligation_candidate_ids")
            or component_ref.get("source_obligation_candidate_refs")
            or ()
        )
        raise OrdinaryMulticomponentRuntimeError(
            "component D-prime support could not satisfy canonical coverage for "
            + component_id
            + " (evidence_ref="
            + str(bindable.evidence_ref_id)
            + ", obligations="
            + ",".join(str(item) for item in obligation_ids)
            + ")"
        )
    return observation.to_dict(), [content_ref.to_dict()], coverage.to_dict()


def _execute_fresh_resynthesis(
    *,
    run_kernel: Any,
    graph: Mapping[str, Any],
    requested_synthesis_directive: str,
    role_kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute the one serial whole-graph pass after recovered admission."""

    current_contract = run_kernel.state.current_answer_contract
    contract_ref = _accepted_contract_ref(current_contract)
    component_packets = _safe_mapping(
        _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get(
            "component_analyst_input_packets"
        )
    )
    if not component_packets:
        raise OrdinaryMulticomponentRuntimeError(
            "fresh resynthesis requires current scheduler-owned component packets"
        )
    cross_input = cross_component_input_packet(
        component_nodes=graph["component_nodes"],
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=requested_synthesis_directive,
        component_analyst_input_packets=component_packets,
    )
    cross_key = f"graph-v1:revision:{graph['graph_revision']}"
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key=cross_key,
        **dict(role_kwargs),
    )
    candidate = component_work_graph_v1_resynthesis_from_cross_component_artifact(
        graph,
        accepted_contract_ref=contract_ref,
        cross_component_artifact=cross_artifact,
        component_analyst_input_packets=component_packets,
        transient_cross_input_packet=cross_input,
    )
    current = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="resynthesis_structure",
        graph_candidate=candidate,
        role_evaluation_key=cross_key,
    )
    deferred_admission_keys: list[str] = []
    for synthesis_key in list(current["synthesis_topological_order"]):
        dprime_input = synthesis_dprime_input_packet(
            current,
            synthesis_key=synthesis_key,
        )
        evaluation_key = (
            f"{synthesis_key}:graph-revision:{current['graph_revision']}"
        )
        dprime_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_SYNTHESIS_DPRIME,
            input_packet=dprime_input,
            logical_evaluation_key=evaluation_key,
            **dict(role_kwargs),
        )
        current = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="synthesis_validation",
            synthesis_key=synthesis_key,
            role_evaluation_key=evaluation_key,
            graph_candidate=graph_with_synthesis_validation(
                current,
                synthesis_key=synthesis_key,
                dprime_artifact=dprime_artifact,
            ),
        )
        node = next(
            item
            for item in current["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        if node.get("status") != "validated":
            break
        node_is_upstream = any(
            ref.get("node_id") == node.get("node_id")
            for candidate_node in current["synthesis_nodes"]
            if candidate_node.get("synthesis_key") != synthesis_key
            for ref in candidate_node.get("input_node_refs") or ()
        )
        if node_is_upstream:
            current = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )
        else:
            deferred_admission_keys.append(synthesis_key)

    if current.get("scrutineer_required") is True:
        scrutiny_key = f"full-case:graph-revision:{current['graph_revision']}"
        scrutineer_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_SCRUTINEER,
            input_packet=scrutineer_input_packet(current),
            logical_evaluation_key=scrutiny_key,
            **dict(role_kwargs),
        )
        current = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="scrutiny",
            role_evaluation_key=scrutiny_key,
            graph_candidate=graph_with_scrutineer(
                current,
                scrutineer_artifact=scrutineer_artifact,
            ),
        )

    for synthesis_key in deferred_admission_keys:
        node = next(
            item
            for item in current["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        if node.get("status") == "validated" and current.get(
            "scrutineer_status"
        ) in {"passed", "passed_with_caveats"}:
            current = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )

    logical, physical = derive_multicomponent_role_call_accounting(
        run_kernel.state.projections,
        issued_actions=run_kernel.state.issued_actions,
    )
    current = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            current,
            logical_accounting=logical,
            physical_call_accounting=physical,
        ),
    )
    return reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(current),
    )


def _execute_selective_reconstruction(
    *,
    run_kernel: Any,
    graph: Mapping[str, Any],
    closure: Mapping[str, Any],
    role_kwargs: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Execute one selective Cross pass and validate only affected synthesis."""

    cross_input = selective_cross_component_input_packet(
        graph,
        closure=closure,
    )
    cross_key = f"selective:graph-revision:{graph['graph_revision']}"
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key=cross_key,
        output_schema_variant=SELECTIVE_CROSS_COMPONENT_SCHEMA,
        **dict(role_kwargs),
    )
    candidate = component_work_graph_v1_selective_resynthesis_from_cross_artifact(
        graph,
        closure=closure,
        cross_component_artifact=cross_artifact,
    )
    current = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="selective_resynthesis_structure",
        graph_candidate=candidate,
        role_evaluation_key=cross_key,
    )
    deferred_admission_keys: list[str] = []
    for synthesis_key in closure["affected_topological_order"]:
        dprime_input = synthesis_dprime_input_packet(
            current,
            synthesis_key=synthesis_key,
        )
        evaluation_key = (
            f"{synthesis_key}:selective:graph-revision:"
            f"{current['graph_revision']}"
        )
        dprime_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_SYNTHESIS_DPRIME,
            input_packet=dprime_input,
            logical_evaluation_key=evaluation_key,
            **dict(role_kwargs),
        )
        current = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="synthesis_validation",
            synthesis_key=synthesis_key,
            role_evaluation_key=evaluation_key,
            graph_candidate=graph_with_synthesis_validation(
                current,
                synthesis_key=synthesis_key,
                dprime_artifact=dprime_artifact,
            ),
        )
        node = next(
            item
            for item in current["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        if node.get("status") != "validated":
            break
        node_is_upstream = any(
            ref.get("node_id") == node.get("node_id")
            for candidate_node in current["synthesis_nodes"]
            if candidate_node.get("synthesis_key") != synthesis_key
            for ref in candidate_node.get("input_node_refs") or ()
        )
        if node_is_upstream:
            current = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )
        else:
            deferred_admission_keys.append(synthesis_key)
    return current, deferred_admission_keys


def _execute_selective_resynthesis(
    *,
    run_kernel: Any,
    graph: Mapping[str, Any],
    closure: Mapping[str, Any],
    role_kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    """Complete affected reconstruction with one fresh whole-case scrutiny."""

    current, deferred_admission_keys = _execute_selective_reconstruction(
        run_kernel=run_kernel,
        graph=graph,
        closure=closure,
        role_kwargs=role_kwargs,
    )
    scrutiny_key = (
        f"full-case:selective:graph-revision:{current['graph_revision']}"
    )
    scrutineer_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_SCRUTINEER,
        input_packet=scrutineer_input_packet(current),
        logical_evaluation_key=scrutiny_key,
        **dict(role_kwargs),
    )
    current = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="scrutiny",
        role_evaluation_key=scrutiny_key,
        graph_candidate=graph_with_scrutineer(
            current,
            scrutineer_artifact=scrutineer_artifact,
        ),
    )
    for synthesis_key in deferred_admission_keys:
        node = next(
            item
            for item in current["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        if node.get("status") == "validated" and current.get(
            "scrutineer_status"
        ) in {"passed", "passed_with_caveats"}:
            current = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )
    logical, physical = derive_multicomponent_role_call_accounting(
        run_kernel.state.projections,
        issued_actions=run_kernel.state.issued_actions,
    )
    current = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            current,
            logical_accounting=logical,
            physical_call_accounting=physical,
        ),
    )
    return reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(current),
    )


def _attempt_dynamic_recovery(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    graph: Mapping[str, Any],
    scrutineer_artifact: Mapping[str, Any],
    requested_synthesis_directive: str,
    role_kwargs: Mapping[str, Any],
    query: str,
) -> dict[str, Any] | None:
    output = _safe_mapping(scrutineer_artifact.get("semantic_output"))
    proposals = [
        _safe_mapping(item)
        for item in output.get("missing_component_proposals") or ()
        if isinstance(item, Mapping)
    ]
    if not proposals:
        return None
    if len(proposals) != 1:
        raise OrdinaryMulticomponentRuntimeError(
            "ordinary dynamic recovery can consume exactly one proposal"
        )
    from core.run_kernel import Observation, RunStageStatus

    authorization_action = (
        run_kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key=str(proposals[0]["proposal_key"])
        )
    )
    run_kernel.reduce(
        Observation.from_action(
            authorization_action,
            observation_type=authorization_action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    authorization = run_kernel.state.projections[authorization_action.stage]
    if authorization.get("search_authorized") is not True:
        blocker = "missing component proposal requires user confirmation"
        run_kernel.state.projections[MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE] = {
            "schema_version": "multicomponent_dynamic_recovery_v1",
            "owner": "OrdinaryMulticomponent.DynamicRecoveryAdapter",
            "trace_only": True,
            "canonical_state": False,
            "final_answer_authority": False,
            "run_id": run_kernel.state.run_id,
            "request_id": run_kernel.state.request_id,
            "status": RECOVERY_STATUS_BLOCKED,
            "blocker": blocker,
            "requires_user_confirmation": True,
            "ordinary_acquisition_attempt_count": 0,
            "direct_semantic_producer_used": False,
            "runtime_parallelism": False,
            "pending_recovery_disposition": (
                RECOVERY_DISPOSITION_BLOCKED_REQUIRES_CONFIRMATION
            ),
        }
        return None
    amendment = apply_recovered_component_amendment(run_kernel=run_kernel)
    acquisition = execute_recovery_acquisition(
        run_kernel=run_kernel,
        runtime_scope=runtime_scope,
        component_ref=amendment.component_ref,
    )
    if not acquisition.acquired or acquisition.bindable is None:
        return None

    component_ref = amendment.component_ref
    component_id = str(component_ref["component_id"])
    analyst_input = component_analyst_input_packet(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract=run_kernel.state.current_answer_contract,
        component_ref=component_ref,
        evidence_input=_evidence_input(acquisition.bindable),
    )
    authorization = run_kernel.state.projections[authorization_action.stage]
    application = run_kernel.state.contract_amendment_application_projection
    application_ref = {
        "application_digest": application.get("application_digest"),
        "authorized_action_id": application.get("authorized_action_id"),
        "amendment_record_id": application.get("amendment_record_id"),
    }
    amendment_admission = run_kernel.state.contract_amendment_admission_projection
    amendment_admission_ref = {
        "amendment_record_id": amendment_admission.get("amendment_record_id"),
        "amendment_record_digest": amendment_admission.get(
            "amendment_record_digest"
        ),
        "authorized_action_id": amendment_admission.get("authorized_action_id"),
        "admission_digest": amendment_admission.get("admission_digest"),
    }
    run_kernel.register_multicomponent_recovery_scheduler_context(
        component_id=component_id,
        analyst_input_packet=analyst_input,
        recovery_authorization_ref={
            "authorization_id": authorization.get("authorization_id"),
            "authorization_digest": authorization.get("authorization_digest"),
        },
        contract_amendment_admission_ref=amendment_admission_ref,
        contract_amendment_application_ref=application_ref,
    )
    analyst_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_COMPONENT_ANALYST,
        input_packet=analyst_input,
        logical_evaluation_key=component_id,
        **dict(role_kwargs),
    )
    dprime_input = component_dprime_input_packet(
        analyst_artifact=analyst_artifact,
        analyst_input_packet=analyst_input,
    )
    dprime_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_COMPONENT_DPRIME,
        input_packet=dprime_input,
        logical_evaluation_key=component_id,
        **dict(role_kwargs),
    )
    observation, content_refs, coverage = _semantic_material(
        run_kernel=run_kernel,
        component_ref=component_ref,
        bindable=acquisition.bindable,
        analyst_artifact=analyst_artifact,
        dprime_artifact=dprime_artifact,
        query=query,
    )
    component_admission_ref = execute_multicomponent_component_admission(
        run_kernel=run_kernel,
        component_id=component_id,
        analyst_artifact=analyst_artifact,
        dprime_artifact=dprime_artifact,
        analyst_input_packet=analyst_input,
        semantic_observation=observation,
        sanitized_content_references=content_refs,
        component_coverage_record=coverage,
    )
    if component_admission_ref.get("admission_status") not in {
        "admitted",
        "admitted_with_caveats",
    }:
        recovery_projection = dict(
            run_kernel.state.projections.get(
                MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
                {},
            )
        )
        recovery_projection.update(
            {
                "status": RECOVERY_STATUS_BLOCKED,
                "blocker": "recovered component did not pass typed admission",
                "pending_recovery_disposition": (
                    RECOVERY_DISPOSITION_BLOCKED_COMPONENT_ADMISSION
                ),
            }
        )
        run_kernel.state.projections[
            MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE
        ] = recovery_projection
        return None
    recovered_node = component_work_node_v1_from_admitted_component(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_component_ref=component_ref,
        component_admission_ref=component_admission_ref,
    )
    current_contract_ref = _accepted_contract_ref(
        run_kernel.state.current_answer_contract
    )
    closure_candidate = derive_selective_recomputation_closure(
        graph,
        recovery_authorization_ref=authorization,
        current_contract_ref=current_contract_ref,
        contract_amendment_admission_ref=amendment_admission_ref,
        contract_amendment_application_ref=application_ref,
        recovered_component_admission_ref=component_admission_ref,
    )
    closure = reduce_selective_recomputation_closure(
        run_kernel=run_kernel,
        closure_candidate=closure_candidate,
    )
    amended = reduce_selective_invalidation_via_runkernel(
        run_kernel=run_kernel,
        graph=graph,
        closure=closure,
        recovered_component_node=recovered_node,
        current_contract_ref=current_contract_ref,
        recovery_authorization_ref=authorization,
        contract_amendment_admission_ref=amendment_admission_ref,
        amendment_application_ref=application_ref,
    )
    try:
        final_graph = _execute_selective_resynthesis(
            run_kernel=run_kernel,
            graph=amended,
            closure=closure,
            role_kwargs=role_kwargs,
        )
    except Exception as exc:
        recovery_projection = dict(
            run_kernel.state.projections.get(
                MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
                {},
            )
        )
        recovery_projection.update(
            {
                "status": RECOVERY_STATUS_BLOCKED,
                "blocker": "selective recomputation authority could not be proven",
                "selective_failure_type": type(exc).__name__,
                "pending_recovery_disposition": (
                    RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS
                ),
                "whole_graph_fallback_invoked": False,
            }
        )
        run_kernel.state.projections[
            MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE
        ] = recovery_projection
        pending_actions = [
            item
            for item in run_kernel.state.issued_actions.values()
            if item.action_id not in run_kernel.state.reduced_action_ids
        ]
        if not pending_actions:
            reduce_recovery_outcome(
                run_kernel=run_kernel,
                disposition=RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS,
                observed_provider_identities=(
                    acquisition.observed_provider_identities
                ),
                blocker_reason=str(recovery_projection["blocker"]),
            )
        if not isinstance(exc, _ScheduledSemanticWorkBlocked):
            # A deterministic graph/authority defect is not an ordinary
            # scheduler blockage and must retain the installed fail-closed
            # invariant behavior.
            raise
        return amended
    if final_graph.get("graph_status") not in {"ready", "ready_with_caveats"}:
        recovery_projection = dict(
            run_kernel.state.projections.get(
                MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
                {},
            )
        )
        recovery_projection.update(
            {
                "status": RECOVERY_STATUS_BLOCKED,
                "blocker": "selective recomputation did not reach ready posture",
            }
        )
        run_kernel.state.projections[
            MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE
        ] = recovery_projection
        reduce_recovery_outcome(
            run_kernel=run_kernel,
            disposition=RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS,
            observed_provider_identities=(
                acquisition.observed_provider_identities
            ),
            blocker_reason=str(recovery_projection["blocker"]),
        )
    else:
        reduce_recovery_outcome(
            run_kernel=run_kernel,
            disposition=RECOVERY_DISPOSITION_ACQUIRED,
            observed_provider_identities=(
                acquisition.observed_provider_identities
            ),
        )
    run_kernel.complete_multicomponent_graph_scheduler()
    return final_graph


def _reduce_pending_recovery_outcome(run_kernel: Any) -> None:
    """Commit a trace-reported terminal fact after the graph reaches final revision."""

    from core.run_kernel import MULTICOMPONENT_RECOVERY_OUTCOME_STAGE

    if run_kernel.state.projections.get(MULTICOMPONENT_RECOVERY_OUTCOME_STAGE):
        return
    trace = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE)
    )
    disposition = _clean_text(
        trace.get("pending_recovery_disposition"), limit=100
    )
    if not disposition:
        return
    reduce_recovery_outcome(
        run_kernel=run_kernel,
        disposition=disposition,
        observed_provider_identities=tuple(
            str(item)
            for item in trace.get("observed_provider_identities") or ()
            if str(item or "").strip()
        ),
        blocker_reason=_clean_text(trace.get("blocker"), limit=300),
    )


def _scheduler_work_input_packet(
    *, run_kernel: Any, work: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct the exact canonical packet named by scheduler-selected work."""

    from core.component_work_graph_v1 import (
        COMPONENT_WORK_GRAPH_V1_STAGE,
        MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
        validate_component_work_graph_v1,
        validate_selective_recomputation_closure,
    )
    from core.multicomponent_component_admission import (
        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
    )

    role = str(work.get("role") or "")
    component_id = _clean_text(work.get("component_id"), limit=180)
    synthesis_key = _clean_text(work.get("synthesis_key"), limit=180)
    context = _safe_mapping(run_kernel.state.multicomponent_scheduler_context)
    analyst_inputs = {
        str(key): _safe_mapping(value)
        for key, value in _safe_mapping(
            context.get("component_analyst_input_packets")
        ).items()
    }
    if work.get("work_kind") == "specialist_capability":
        from core.multicomponent_graph_scheduling import (
            reconstruct_specialist_input_for_work,
        )

        packet = reconstruct_specialist_input_for_work(
            state=run_kernel.state,
            work=work,
        )
    elif role == ROLE_COMPONENT_ANALYST and component_id:
        packet = analyst_inputs.get(component_id, {})
    elif role == ROLE_COMPONENT_DPRIME and component_id:
        analyst = _safe_mapping(
            run_kernel.state.projections.get(
                f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}"
            )
        )
        analyst_input = analyst_inputs.get(component_id, {})
        specialist_handoff: dict[str, Any] = {}
        specialist_state = _safe_mapping(
            run_kernel.state.projections.get("specialist_work_plane")
        )
        if specialist_state:
            from core.specialist_graph_runtime import handoff_for_target

            specialist_handoff = handoff_for_target(
                specialist_state,
                target_kind="component",
                target_key=component_id,
            )
        packet = (
            component_dprime_input_packet(
                analyst_artifact=analyst,
                analyst_input_packet=analyst_input,
                specialist_need_handoff=specialist_handoff or None,
            )
            if analyst and analyst_input
            else {}
        )
    else:
        graph_raw = _safe_mapping(
            run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
        )
        if role == ROLE_CROSS_COMPONENT_ANALYST and not graph_raw:
            accepted = (
                run_kernel.state.current_answer_contract
                or run_kernel.state.initial_answer_contract
            )
            component_refs = [
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
            ]
            admissions_projection = _safe_mapping(
                run_kernel.state.projections.get(
                    MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                )
            )
            admissions = {
                str(_safe_mapping(item).get("component_id") or ""): _safe_mapping(
                    item
                )
                for item in admissions_projection.get("component_admission_refs")
                or ()
            }
            if not component_refs or any(
                str(item.get("component_id") or "") not in admissions
                for item in component_refs
            ):
                packet = {}
            else:
                nodes = [
                    component_work_node_v1_from_admitted_component(
                        run_id=run_kernel.state.run_id,
                        request_id=run_kernel.state.request_id,
                        accepted_component_ref=component_ref,
                        component_admission_ref=admissions[
                            str(component_ref["component_id"])
                        ],
                    )
                    for component_ref in component_refs
                ]
                packet = cross_component_input_packet(
                    component_nodes=nodes,
                    accepted_contract_ref=_accepted_contract_ref(accepted),
                    requested_synthesis_directive=str(
                        context.get("requested_synthesis_directive") or ""
                    ),
                    component_analyst_input_packets=analyst_inputs,
                )
        elif graph_raw:
            graph = validate_component_work_graph_v1(graph_raw)
            if role == ROLE_CROSS_COMPONENT_ANALYST:
                closure = validate_selective_recomputation_closure(
                    _safe_mapping(
                        run_kernel.state.projections.get(
                            MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE
                        )
                    )
                )
                packet = selective_cross_component_input_packet(
                    graph,
                    closure=closure,
                )
            elif role == ROLE_SYNTHESIS_DPRIME and synthesis_key:
                specialist_handoff = {}
                specialist_state = _safe_mapping(
                    run_kernel.state.projections.get("specialist_work_plane")
                )
                if specialist_state:
                    from core.specialist_graph_runtime import (
                        handoff_for_target,
                    )

                    specialist_handoff = handoff_for_target(
                        specialist_state,
                        target_kind="synthesis",
                        target_key=synthesis_key,
                    )
                packet = synthesis_dprime_input_packet(
                    graph,
                    synthesis_key=synthesis_key,
                    specialist_need_handoff=specialist_handoff or None,
                )
            elif role == ROLE_SCRUTINEER:
                packet = scrutineer_input_packet(graph)
            else:
                packet = {}
        else:
            packet = {}
    packet_digest = safe_packet_digest(packet)
    if work.get("work_kind") == "specialist_capability":
        from core.specialist_graph_runtime import specialist_digest

        packet_digest = specialist_digest(packet)
    if not packet or packet_digest != work.get("input_packet_digest"):
        raise OrdinaryMulticomponentRuntimeError(
            "scheduler-selected work packet could not be reconstructed exactly"
        )
    return packet


def _begin_scheduler_dynamic_recovery(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    graph: Mapping[str, Any],
    scrutineer_artifact: Mapping[str, Any],
    drive_context: dict[str, Any],
) -> bool:
    """Apply deterministic recovery authority and expose its next scheduler work."""

    output = _safe_mapping(scrutineer_artifact.get("semantic_output"))
    proposals = [
        _safe_mapping(item)
        for item in output.get("missing_component_proposals") or ()
        if isinstance(item, Mapping)
    ]
    if not proposals:
        return False
    if len(proposals) != 1:
        raise OrdinaryMulticomponentRuntimeError(
            "ordinary dynamic recovery can consume exactly one proposal"
        )
    from core.run_kernel import Observation, RunStageStatus

    authorization_action = (
        run_kernel.authorize_multicomponent_missing_component_recovery(
            proposal_key=str(proposals[0]["proposal_key"])
        )
    )
    run_kernel.reduce(
        Observation.from_action(
            authorization_action,
            observation_type=authorization_action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    authorization = run_kernel.state.projections[authorization_action.stage]
    if authorization.get("search_authorized") is not True:
        blocker = "missing component proposal requires user confirmation"
        run_kernel.state.projections[MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE] = {
            "schema_version": "multicomponent_dynamic_recovery_v1",
            "owner": "OrdinaryMulticomponent.DynamicRecoveryAdapter",
            "trace_only": True,
            "canonical_state": False,
            "final_answer_authority": False,
            "run_id": run_kernel.state.run_id,
            "request_id": run_kernel.state.request_id,
            "status": RECOVERY_STATUS_BLOCKED,
            "blocker": blocker,
            "requires_user_confirmation": True,
            "ordinary_acquisition_attempt_count": 0,
            "direct_semantic_producer_used": False,
            "runtime_parallelism": False,
            "pending_recovery_disposition": (
                RECOVERY_DISPOSITION_BLOCKED_REQUIRES_CONFIRMATION
            ),
        }
        return False
    amendment = apply_recovered_component_amendment(run_kernel=run_kernel)
    acquisition = execute_recovery_acquisition(
        run_kernel=run_kernel,
        runtime_scope=runtime_scope,
        component_ref=amendment.component_ref,
    )
    if not acquisition.acquired or acquisition.bindable is None:
        return False
    component_ref = amendment.component_ref
    component_id = str(component_ref["component_id"])
    analyst_input = component_analyst_input_packet(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract=run_kernel.state.current_answer_contract,
        component_ref=component_ref,
        evidence_input=_evidence_input(acquisition.bindable),
    )
    application = run_kernel.state.contract_amendment_application_projection
    application_ref = {
        "application_digest": application.get("application_digest"),
        "authorized_action_id": application.get("authorized_action_id"),
        "amendment_record_id": application.get("amendment_record_id"),
    }
    amendment_admission = run_kernel.state.contract_amendment_admission_projection
    amendment_admission_ref = {
        "amendment_record_id": amendment_admission.get("amendment_record_id"),
        "amendment_record_digest": amendment_admission.get(
            "amendment_record_digest"
        ),
        "authorized_action_id": amendment_admission.get("authorized_action_id"),
        "admission_digest": amendment_admission.get("admission_digest"),
    }
    run_kernel.register_multicomponent_recovery_scheduler_context(
        component_id=component_id,
        analyst_input_packet=analyst_input,
        recovery_authorization_ref={
            "authorization_id": authorization.get("authorization_id"),
            "authorization_digest": authorization.get("authorization_digest"),
        },
        contract_amendment_admission_ref=amendment_admission_ref,
        contract_amendment_application_ref=application_ref,
    )
    drive_context["selected_bindables"][component_id] = acquisition.bindable
    drive_context["recovery_graph"] = dict(graph)
    drive_context["recovery_authorization_ref"] = dict(authorization)
    drive_context["contract_amendment_admission_ref"] = amendment_admission_ref
    drive_context["contract_amendment_application_ref"] = application_ref
    drive_context["observed_provider_identities"] = tuple(
        acquisition.observed_provider_identities
    )
    return True


def _admit_scheduler_validated_synthesis(run_kernel: Any) -> dict[str, Any]:
    """Admit deterministic validated leaves after whole-case scrutiny."""

    graph = _safe_mapping(
        run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
    )
    scrutiny_allows_admission = (
        graph.get("scrutineer_required") is not True
        or graph.get("scrutineer_status") in {"passed", "passed_with_caveats"}
    )
    if not scrutiny_allows_admission:
        return graph
    for synthesis_key in graph.get("synthesis_topological_order") or ():
        node = next(
            item
            for item in graph.get("synthesis_nodes") or ()
            if item.get("synthesis_key") == synthesis_key
        )
        if node.get("status") == "validated":
            graph = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=str(synthesis_key),
            )
    return graph


def _finalize_scheduler_graph(
    *, run_kernel: Any, drive_context: Mapping[str, Any]
) -> None:
    graph = _admit_scheduler_validated_synthesis(run_kernel)
    logical, physical = derive_multicomponent_role_call_accounting(
        run_kernel.state.projections,
        issued_actions=run_kernel.state.issued_actions,
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            graph,
            logical_accounting=logical,
            physical_call_accounting=physical,
        ),
    )
    final_graph = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    if drive_context.get("recovery_graph"):
        if final_graph.get("graph_status") in {"ready", "ready_with_caveats"}:
            disposition = RECOVERY_DISPOSITION_ACQUIRED
            blocker = None
        else:
            disposition = RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS
            blocker = "selective recomputation did not reach ready posture"
        reduce_recovery_outcome(
            run_kernel=run_kernel,
            disposition=disposition,
            observed_provider_identities=tuple(
                drive_context.get("observed_provider_identities") or ()
            ),
            blocker_reason=blocker,
        )
    run_kernel.complete_multicomponent_graph_scheduler()
    _reduce_pending_recovery_outcome(run_kernel)


def _consume_scheduler_selected_artifact(
    *,
    run_kernel: Any,
    work: Mapping[str, Any],
    artifact: Mapping[str, Any],
    input_packet: Mapping[str, Any],
    drive_context: dict[str, Any],
) -> None:
    """Route one selected artifact to its installed deterministic owner."""

    from core.component_work_graph_v1 import (
        MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
        validate_component_work_graph_v1,
        validate_selective_recomputation_closure,
    )

    role = str(work.get("role") or "")
    component_id = _clean_text(work.get("component_id"), limit=180)
    synthesis_key = _clean_text(work.get("synthesis_key"), limit=180)
    evaluation_key = str(work.get("logical_evaluation_key") or "")
    if role == ROLE_COMPONENT_ANALYST:
        output = _safe_mapping(artifact.get("semantic_output"))
        if output.get("specialist_need_proposal"):
            accepted = (
                run_kernel.state.current_answer_contract
                or run_kernel.state.initial_answer_contract
            )
            component_ref = next(
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
                if _safe_mapping(item).get("component_id") == component_id
            )
            deps = drive_context["runtime_scope"].get("deps")
            run_kernel.bind_specialist_need_from_role_artifact(
                role_artifact=artifact,
                canonical_target_ref={
                    "target_kind": "component",
                    "target_key": component_id,
                    "target_revision": component_ref.get("component_revision"),
                    "target_digest": component_ref.get("component_digest"),
                },
                specialist_capability_registry=getattr(
                    deps, "specialist_capability_registry", None
                ),
                specialist_execution_policy=getattr(
                    deps, "specialist_execution_policy", None
                ),
            )
        return
    if role == ROLE_COMPONENT_DPRIME and component_id:
        accepted = (
            run_kernel.state.current_answer_contract
            or run_kernel.state.initial_answer_contract
        )
        component_ref = next(
            _safe_mapping(item)
            for item in accepted.get("accepted_answer_component_refs") or ()
            if _safe_mapping(item).get("component_id") == component_id
        )
        analyst_input = _safe_mapping(
            _safe_mapping(run_kernel.state.multicomponent_scheduler_context)
            .get("component_analyst_input_packets", {})
            .get(component_id)
        )
        analyst_artifact = _safe_mapping(
            run_kernel.state.projections.get(
                f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}"
            )
        )
        specialist_handoff: dict[str, Any] = {}
        specialist_state = _safe_mapping(
            run_kernel.state.projections.get("specialist_work_plane")
        )
        if specialist_state:
            from core.multicomponent_role_runtime import role_artifact_ref
            from core.specialist_graph_runtime import handoff_for_target

            specialist_handoff = handoff_for_target(
                specialist_state,
                target_kind="component",
                target_key=component_id,
            )
            if specialist_handoff:
                run_kernel.consume_specialist_handoff_by_dprime(
                    handoff_id=str(specialist_handoff.get("handoff_id") or ""),
                    dprime_artifact_ref=role_artifact_ref(artifact),
                )
        bindable = drive_context["selected_bindables"].get(component_id)
        if bindable is None:
            raise OrdinaryMulticomponentRuntimeError(
                "scheduler-selected component lost its evidence binding"
            )
        observation, content_refs, coverage = _semantic_material(
            run_kernel=run_kernel,
            component_ref=component_ref,
            bindable=bindable,
            analyst_artifact=analyst_artifact,
            dprime_artifact=artifact,
            query=str(drive_context["query"]),
        )
        component_admission_ref = execute_multicomponent_component_admission(
            run_kernel=run_kernel,
            component_id=component_id,
            analyst_artifact=analyst_artifact,
            dprime_artifact=artifact,
            analyst_input_packet=analyst_input,
            semantic_observation=observation,
            sanitized_content_references=content_refs,
            component_coverage_record=coverage,
            specialist_need_handoff=specialist_handoff or None,
        )
        if work.get("recovery_authorization_ref"):
            if component_admission_ref.get("admission_status") not in {
                "admitted",
                "admitted_with_caveats",
            }:
                raise _ScheduledSemanticWorkBlocked(
                    "recovered component did not pass typed admission"
                )
            source_graph = validate_component_work_graph_v1(
                _safe_mapping(drive_context.get("recovery_graph"))
            )
            recovered_node = component_work_node_v1_from_admitted_component(
                run_id=run_kernel.state.run_id,
                request_id=run_kernel.state.request_id,
                accepted_component_ref=component_ref,
                component_admission_ref=component_admission_ref,
            )
            current_contract_ref = _accepted_contract_ref(
                run_kernel.state.current_answer_contract
            )
            closure_candidate = derive_selective_recomputation_closure(
                source_graph,
                recovery_authorization_ref=drive_context[
                    "recovery_authorization_ref"
                ],
                current_contract_ref=current_contract_ref,
                contract_amendment_admission_ref=drive_context[
                    "contract_amendment_admission_ref"
                ],
                contract_amendment_application_ref=drive_context[
                    "contract_amendment_application_ref"
                ],
                recovered_component_admission_ref=component_admission_ref,
            )
            closure = reduce_selective_recomputation_closure(
                run_kernel=run_kernel,
                closure_candidate=closure_candidate,
            )
            reduce_selective_invalidation_via_runkernel(
                run_kernel=run_kernel,
                graph=source_graph,
                closure=closure,
                recovered_component_node=recovered_node,
                current_contract_ref=current_contract_ref,
                recovery_authorization_ref=drive_context[
                    "recovery_authorization_ref"
                ],
                contract_amendment_admission_ref=drive_context[
                    "contract_amendment_admission_ref"
                ],
                amendment_application_ref=drive_context[
                    "contract_amendment_application_ref"
                ],
            )
        return
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        graph_raw = _safe_mapping(
            run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
        )
        if not graph_raw:
            from core.multicomponent_component_admission import (
                MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
            )

            packet = _safe_mapping(input_packet)
            accepted = (
                run_kernel.state.current_answer_contract
                or run_kernel.state.initial_answer_contract
            )
            component_refs = [
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
            ]
            admissions = {
                str(_safe_mapping(item).get("component_id") or ""): _safe_mapping(
                    item
                )
                for item in _safe_mapping(
                    run_kernel.state.projections.get(
                        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                    )
                ).get("component_admission_refs")
                or ()
            }
            component_nodes = [
                component_work_node_v1_from_admitted_component(
                    run_id=run_kernel.state.run_id,
                    request_id=run_kernel.state.request_id,
                    accepted_component_ref=component_ref,
                    component_admission_ref=admissions[
                        str(component_ref["component_id"])
                    ],
                )
                for component_ref in component_refs
            ]
            candidate = component_work_graph_v1_from_cross_component_artifact(
                run_id=run_kernel.state.run_id,
                request_id=run_kernel.state.request_id,
                accepted_contract_ref=_safe_mapping(
                    packet.get("accepted_contract_ref")
                ),
                requested_synthesis_directive=str(
                    packet.get("requested_synthesis_directive") or ""
                ),
                component_nodes=component_nodes,
                cross_component_artifact=artifact,
                component_analyst_input_packets=_safe_mapping(
                    drive_context.get("component_analyst_input_packets")
                ),
                transient_cross_input_packet=packet,
                additional_scrutineer_trigger_reasons=tuple(
                    drive_context.get("additional_scrutineer_trigger_reasons")
                    or ()
                ),
            )
            reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="structure",
                graph_candidate=candidate,
            )
            output = _safe_mapping(artifact.get("semantic_output"))
            if output.get("specialist_need_proposal"):
                target = _safe_mapping(
                    _safe_mapping(output.get("specialist_need_proposal")).get(
                        "target"
                    )
                )
                graph = validate_component_work_graph_v1(
                    _safe_mapping(
                        run_kernel.state.projections.get(
                            COMPONENT_WORK_GRAPH_V1_STAGE
                        )
                    )
                )
                node = next(
                    (
                        _safe_mapping(item)
                        for item in graph.get("synthesis_nodes") or ()
                        if _safe_mapping(item).get("synthesis_key")
                        == target.get("target_key")
                    ),
                    {},
                )
                deps = drive_context["runtime_scope"].get("deps")
                run_kernel.bind_specialist_need_from_role_artifact(
                    role_artifact=artifact,
                    canonical_target_ref={
                        "target_kind": "synthesis",
                        "target_key": (
                            node.get("synthesis_key")
                            or "unsupported-cross-component-target"
                        ),
                        "target_revision": node.get("node_revision"),
                        "target_digest": node.get("node_digest"),
                    },
                    specialist_capability_registry=getattr(
                        deps, "specialist_capability_registry", None
                    ),
                    specialist_execution_policy=getattr(
                        deps, "specialist_execution_policy", None
                    ),
                )
        elif work.get("output_schema_variant") == SELECTIVE_CROSS_COMPONENT_SCHEMA:
            graph = validate_component_work_graph_v1(graph_raw)
            closure = validate_selective_recomputation_closure(
                _safe_mapping(
                    run_kernel.state.projections.get(
                        MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE
                    )
                )
            )
            candidate = (
                component_work_graph_v1_selective_resynthesis_from_cross_artifact(
                    graph,
                    closure=closure,
                    cross_component_artifact=artifact,
                )
            )
            reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="selective_resynthesis_structure",
                graph_candidate=candidate,
                role_evaluation_key=evaluation_key,
            )
        else:
            graph = validate_component_work_graph_v1(graph_raw)
            component_packets = _safe_mapping(
                _safe_mapping(
                    run_kernel.state.multicomponent_scheduler_context
                ).get("component_analyst_input_packets")
            )
            candidate = component_work_graph_v1_resynthesis_from_cross_component_artifact(
                graph,
                accepted_contract_ref=_accepted_contract_ref(
                    run_kernel.state.current_answer_contract
                ),
                cross_component_artifact=artifact,
                component_analyst_input_packets=component_packets,
                transient_cross_input_packet=input_packet,
            )
            reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="resynthesis_structure",
                graph_candidate=candidate,
                role_evaluation_key=evaluation_key,
            )
        return
    if role == ROLE_SYNTHESIS_DPRIME and synthesis_key:
        specialist_handoff: dict[str, Any] = {}
        specialist_state = _safe_mapping(
            run_kernel.state.projections.get("specialist_work_plane")
        )
        if specialist_state:
            from core.multicomponent_role_runtime import role_artifact_ref
            from core.specialist_graph_runtime import handoff_for_target

            specialist_handoff = handoff_for_target(
                specialist_state,
                target_kind="synthesis",
                target_key=synthesis_key,
            )
            if specialist_handoff:
                run_kernel.consume_specialist_handoff_by_dprime(
                    handoff_id=str(specialist_handoff.get("handoff_id") or ""),
                    dprime_artifact_ref=role_artifact_ref(artifact),
                )
        graph = validate_component_work_graph_v1(
            _safe_mapping(
                run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
            )
        )
        graph = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="synthesis_validation",
            synthesis_key=synthesis_key,
            role_evaluation_key=evaluation_key,
            graph_candidate=graph_with_synthesis_validation(
                graph,
                synthesis_key=synthesis_key,
                dprime_artifact=artifact,
                specialist_need_handoff=specialist_handoff or None,
            ),
        )
        node = next(
            item
            for item in graph["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        node_is_upstream = any(
            ref.get("node_id") == node.get("node_id")
            for candidate in graph["synthesis_nodes"]
            if candidate.get("synthesis_key") != synthesis_key
            for ref in candidate.get("input_node_refs") or ()
        )
        if node.get("status") == "validated" and node_is_upstream:
            admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )
        return
    if role == ROLE_SCRUTINEER:
        graph = validate_component_work_graph_v1(
            _safe_mapping(
                run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
            )
        )
        graph = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="scrutiny",
            role_evaluation_key=evaluation_key,
            graph_candidate=graph_with_scrutineer(
                graph,
                scrutineer_artifact=artifact,
            ),
        )
        output = _safe_mapping(artifact.get("semantic_output"))
        if output.get("specialist_need_proposal"):
            target = _safe_mapping(
                _safe_mapping(output.get("specialist_need_proposal")).get(
                    "target"
                )
            )
            target_kind = str(target.get("target_kind") or "")
            target_key = str(target.get("target_key") or "")
            target_node = next(
                (
                    _safe_mapping(item)
                    for item in graph.get("synthesis_nodes") or ()
                    if _safe_mapping(item).get("synthesis_key") == target_key
                ),
                {},
            )
            descendants = [
                _safe_mapping(item)
                for item in graph.get("synthesis_nodes") or ()
                if any(
                    _safe_mapping(ref).get("node_id")
                    == target_node.get("node_id")
                    for ref in _safe_mapping(item).get("input_node_refs") or ()
                )
            ]
            leaf_authorized = (
                target_kind == "synthesis"
                and bool(target_node)
                and not descendants
            )
            deps = drive_context["runtime_scope"].get("deps")
            run_kernel.bind_specialist_need_from_role_artifact(
                role_artifact=artifact,
                canonical_target_ref={
                    "target_kind": target_kind,
                    "target_key": target_key,
                    "target_revision": target_node.get("node_revision"),
                    "target_digest": target_node.get("node_digest"),
                },
                specialist_capability_registry=getattr(
                    deps, "specialist_capability_registry", None
                ),
                specialist_execution_policy=getattr(
                    deps, "specialist_execution_policy", None
                ),
                scrutineer_leaf_target_authorized=leaf_authorized,
            )
            if leaf_authorized:
                return
        if _begin_scheduler_dynamic_recovery(
            run_kernel=run_kernel,
            runtime_scope=drive_context["runtime_scope"],
            graph=graph,
            scrutineer_artifact=artifact,
            drive_context=drive_context,
        ):
            return
        _finalize_scheduler_graph(
            run_kernel=run_kernel,
            drive_context=drive_context,
        )
        return
    raise OrdinaryMulticomponentRuntimeError(
        "scheduler selected unsupported semantic work descriptor"
    )


def _record_phase5a_model_costs_on_main_thread(
    *,
    drive_context: dict[str, Any],
    actions: list[Any],
    results: list[SafeMulticomponentWorkerResult | None],
    configured_model: str,
) -> None:
    """Record response-bearing Phase 5A SmartModel calls on the product thread.

    CostAccumulator stays out of workers, leases, prepared calls, and RunKernel.
    Recording is exactly-once per child action_id for the current drive context.
    """

    recorded = drive_context.setdefault("cost_recorded_child_action_ids", set())
    if not isinstance(recorded, set):
        recorded = set(recorded)
        drive_context["cost_recorded_child_action_ids"] = recorded
    runtime_scope = _safe_mapping(drive_context.get("runtime_scope"))
    accumulator = runtime_scope.get("accumulator")
    model = str(configured_model or runtime_scope.get("smart_model") or "")
    ordered = sorted(
        (
            (action, result)
            for action, result in zip(actions, results, strict=True)
            if result is not None
        ),
        key=lambda pair: (
            int(getattr(pair[0], "sequence", 0) or 0),
            str(getattr(pair[0], "action_id", "") or ""),
        ),
    )
    for action, result in ordered:
        action_id = str(getattr(action, "action_id", "") or "")
        if not action_id or action_id in recorded:
            continue
        recorded.add(action_id)
        if accumulator is None or not bool(result.provider_response_received):
            continue
        accumulator.record_model_call(
            phase="model",
            model=model or str(result.model or ""),
            input_tokens=max(0, int(result.input_tokens or 0)),
            output_tokens=max(0, int(result.output_tokens or 0)),
        )


def _execute_run_kernel_selected_batch(
    *,
    run_kernel: Any,
    role_kwargs: Mapping[str, Any],
    drive_context: dict[str, Any],
) -> None:
    """Execute one exact scheduler wave in canonical action order."""

    from core.multicomponent_graph_scheduling import (
        LEASE_DENIED_EXHAUSTED,
        MULTICOMPONENT_SCHEDULER_STAGE,
    )
    from core.run_kernel import Observation, RunStageStatus

    batch = run_kernel.grant_next_multicomponent_work_batch()
    if batch.get("status") == LEASE_DENIED_EXHAUSTED:
        raise _ScheduledSemanticWorkBlocked(
            "required semantic work denied by the compatibility envelope"
        )
    scheduler = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    )
    leases_by_id = {
        str(_safe_mapping(item).get("lease_id") or ""): _safe_mapping(item)
        for item in scheduler.get("lease_history") or ()
    }
    leases = [
        leases_by_id[str(_safe_mapping(ref).get("lease_id") or "")]
        for ref in batch.get("ordered_lease_refs") or ()
    ]
    works = [_safe_mapping(lease.get("work")) for lease in leases]
    try:
        packets = [
            _scheduler_work_input_packet(run_kernel=run_kernel, work=work)
            for work in works
        ]
    except Exception as exc:
        run_kernel.cancel_multicomponent_work_batch(
            batch_id=str(batch.get("batch_id") or ""),
            reason="exact_batch_packet_reconstruction_failed",
        )
        if (
            len(works) == 1
            and works[0].get("work_kind") == "specialist_capability"
        ):
            proposal_posture = _safe_mapping(
                works[0].get("specialist_proposal_ref")
            ).get("posture")
            run_kernel.dispose_failed_specialist_reconstruction(
                work=works[0]
            )
            if proposal_posture == "optional":
                return
            current = _safe_mapping(
                run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
            )
            if (
                proposal_posture == "required"
                and current.get("status") == "blocked_required_specialist_work"
            ):
                raise _ScheduledSemanticWorkBlocked(
                    "required Specialist input reconstruction failed before dispatch"
                ) from exc
            raise OrdinaryMulticomponentRuntimeError(
                "required Specialist reconstruction failure did not reach its "
                "scheduler blocked terminal"
            ) from exc
        raise
    from core.specialist_graph_runtime import specialist_digest

    packet_digests = [
        (
            specialist_digest(packet)
            if work.get("work_kind") == "specialist_capability"
            else safe_packet_digest(packet)
        )
        for work, packet in zip(works, packets, strict=True)
    ]
    actions = run_kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=packet_digests,
    )
    if works and works[0].get("work_kind") == "specialist_capability":
        if len(works) != 1 or len(actions) != 1:
            raise OrdinaryMulticomponentRuntimeError(
                "Specialist execution must remain serial width one"
            )
        from core.specialist_graph_runtime import (
            SpecialistCapabilityRegistry,
            build_specialist_terminal_result,
            execute_specialist_capability,
        )
        deps = _safe_mapping(drive_context.get("runtime_scope")).get("deps")
        registry = getattr(deps, "specialist_capability_registry", None)
        if not isinstance(registry, SpecialistCapabilityRegistry):
            raise OrdinaryMulticomponentRuntimeError(
                "Specialist execution lost its injected registry"
            )
        action = actions[0]
        work_node = _safe_mapping(action.inputs.get("specialist_work_node"))
        action_ref = {
            "action_id": action.action_id,
            "stage": action.stage,
            "sequence": action.sequence,
            "observation_type": action.expected_observation_type.value,
        }
        lease_ref = {
            "lease_id": action.inputs.get("lease_id"),
            "lease_digest": action.inputs.get("lease_digest"),
            "batch_id": action.inputs.get("batch_id"),
            "batch_digest": action.inputs.get("batch_digest"),
        }
        try:
            result = execute_specialist_capability(
                registry=registry,
                work_node=work_node,
                transient_bounded_input=packets[0],
                authorization_action_ref=action_ref,
                lease_ref=lease_ref,
            )
        except Exception as exc:  # bounded deterministic capability failure
            result = build_specialist_terminal_result(
                work_node=work_node,
                authorization_action_ref=action_ref,
                lease_ref=lease_ref,
                execution_posture="failed_spent",
                blocker=f"deterministic_capability_failure:{type(exc).__name__}",
            )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"specialist_result_artifact": result},
            )
        )
        if result.get("execution_posture") == "completed":
            plane = _safe_mapping(
                run_kernel.state.projections.get("specialist_work_plane")
            )
            proposal_id = _safe_mapping(result.get("proposal_ref")).get(
                "proposal_id"
            )
            proposal = next(
                (
                    _safe_mapping(item)
                    for item in plane.get("proposals") or ()
                    if _safe_mapping(item).get("proposal_id") == proposal_id
                ),
                {},
            )
            if proposal.get("origin_role") == ROLE_SCRUTINEER:
                from core.component_work_graph_v1 import (
                    graph_with_specialist_leaf_remediation,
                    validate_component_work_graph_v1,
                )

                graph = validate_component_work_graph_v1(
                    _safe_mapping(
                        run_kernel.state.projections.get(
                            COMPONENT_WORK_GRAPH_V1_STAGE
                        )
                    )
                )
                remediated = graph_with_specialist_leaf_remediation(
                    graph,
                    specialist_result_artifact=result,
                )
                reduce_component_work_graph_v1(
                    run_kernel=run_kernel,
                    operation="specialist_remediation",
                    synthesis_key=str(
                        _safe_mapping(result.get("canonical_target_ref")).get(
                            "target_key"
                        )
                        or ""
                    ),
                    graph_candidate=remediated,
                )
        current = _safe_mapping(
            run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        if str(current.get("status") or "").startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked(
                "required scheduled Specialist work did not complete"
            )
        return
    try:
        prepared_calls = [
            prepare_multicomponent_transport_call(
                action=action,
                input_packet=packet,
                **{
                    **dict(role_kwargs),
                    "provider": str(
                        scheduler.get("configured_provider_class")
                        or role_kwargs.get("provider")
                        or ""
                    ),
                },
            )
            for action, packet in zip(actions, packets, strict=True)
        ]
    except Exception as exc:
        for action in actions:
            run_kernel.reduce(
                Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.FAILED,
                    payload={
                        "lease_settlement": "failed_spent",
                        "failure_kind": "prepared_transport_construction_failure",
                        "transport_submitted": False,
                        "transport_started": False,
                        "transport_completed": False,
                        "provider_request_attempt_count": 0,
                        "observed_batch_max_in_flight": 0,
                    },
                )
            )
        raise _ScheduledSemanticWorkBlocked(
            "committed batch transport preparation failed"
        ) from exc

    active_count = 0
    maximum_in_flight = 0
    counter_lock = Lock()

    def execute_with_diagnostics(prepared):
        nonlocal active_count, maximum_in_flight
        with counter_lock:
            active_count += 1
            maximum_in_flight = max(maximum_in_flight, active_count)
        try:
            return execute_prepared_multicomponent_transport(prepared)
        finally:
            with counter_lock:
                active_count -= 1

    results: list[SafeMulticomponentWorkerResult | None] = [
        None for _ in prepared_calls
    ]
    effective_width = int(scheduler.get("effective_width") or 1)
    use_executor = effective_width > 1 and str(batch.get("parallel_class") or "") in {
        "parallel_initial_component_analyst",
        "parallel_initial_component_dprime",
    }
    if not use_executor:
        results[0] = execute_with_diagnostics(prepared_calls[0])
    else:
        executor: ThreadPoolExecutor | None = None
        futures: dict[int, Future[SafeMulticomponentWorkerResult]] = {}
        try:
            executor = ThreadPoolExecutor(
                max_workers=min(effective_width, len(prepared_calls)),
                thread_name_prefix="scryraven-component-wave",
            )
        except Exception:
            results = [
                failed_unstarted_multicomponent_worker_result(
                    prepared,
                    failure_kind="executor_initialization_failure",
                )
                for prepared in prepared_calls
            ]
        else:
            submission_failed = False
            for index, prepared in enumerate(prepared_calls):
                if submission_failed:
                    results[index] = failed_unstarted_multicomponent_worker_result(
                        prepared,
                        failure_kind="failed_submission",
                    )
                    continue
                try:
                    futures[index] = executor.submit(
                        execute_with_diagnostics,
                        prepared,
                    )
                except Exception:
                    submission_failed = True
                    results[index] = failed_unstarted_multicomponent_worker_result(
                        prepared,
                        failure_kind="failed_submission",
                    )
            try:
                for index, future in futures.items():
                    try:
                        results[index] = future.result()
                    except Exception:
                        results[index] = failed_unstarted_multicomponent_worker_result(
                            prepared_calls[index],
                            failure_kind="model_transport_failure",
                            transport_submitted=True,
                            transport_started=True,
                            transport_completed=True,
                        )
            finally:
                executor.shutdown(wait=True, cancel_futures=False)

    if any(result is None for result in results):
        raise OrdinaryMulticomponentRuntimeError(
            "committed batch did not produce one safe outcome per child"
        )
    _record_phase5a_model_costs_on_main_thread(
        drive_context=drive_context,
        actions=actions,
        results=results,
        configured_model=str(role_kwargs.get("model") or ""),
    )
    artifacts: list[dict[str, Any] | None] = []
    for action, result in zip(actions, results, strict=True):
        assert result is not None
        try:
            artifact = reduce_multicomponent_worker_result(
                run_kernel=run_kernel,
                action=action,
                result=result,
                observed_batch_max_in_flight=maximum_in_flight,
            )
        except Exception:
            if action.action_id not in run_kernel.state.reduced_action_ids:
                run_kernel.reduce(
                    Observation.from_action(
                        action,
                        observation_type=action.expected_observation_type,
                        status=RunStageStatus.FAILED,
                        payload={
                            "lease_settlement": "failed_spent",
                            "failure_kind": "artifact_construction_failure",
                            "transport_submitted": result.transport_submitted,
                            "transport_started": result.transport_started,
                            "transport_completed": result.transport_completed,
                            "provider_request_attempt_count": max(
                                0,
                                min(
                                    1,
                                    int(result.provider_request_attempt_count or 0),
                                ),
                            ),
                            "observed_batch_max_in_flight": maximum_in_flight,
                        },
                    )
                )
            artifact = None
        artifacts.append(artifact)
    for work, artifact, input_packet in zip(
        works, artifacts, packets, strict=True
    ):
        if artifact is not None:
            try:
                _consume_scheduler_selected_artifact(
                    run_kernel=run_kernel,
                    work=work,
                    artifact=artifact,
                    input_packet=input_packet,
                    drive_context=drive_context,
                )
            except Exception as exc:
                if drive_context.get("recovery_graph"):
                    recovery = dict(
                        run_kernel.state.projections.get(
                            MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE,
                            {},
                        )
                    )
                    recovery.update(
                        {
                            "status": RECOVERY_STATUS_BLOCKED,
                            "blocker": (
                                "selective recomputation authority could not be proven"
                            ),
                            "selective_failure_type": type(exc).__name__,
                            "pending_recovery_disposition": (
                                RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS
                            ),
                            "whole_graph_fallback_invoked": False,
                        }
                    )
                    run_kernel.state.projections[
                        MULTICOMPONENT_DYNAMIC_RECOVERY_STAGE
                    ] = recovery
                    if not run_kernel.state.projections.get(
                        "multicomponent_recovery_outcome"
                    ):
                        reduce_recovery_outcome(
                            run_kernel=run_kernel,
                            disposition=RECOVERY_DISPOSITION_BLOCKED_RESYNTHESIS,
                            observed_provider_identities=tuple(
                                drive_context.get("observed_provider_identities") or ()
                            ),
                            blocker_reason=str(recovery["blocker"]),
                        )
                raise
    current = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    )
    if str(current.get("status") or "").startswith("blocked_"):
        raise _ScheduledSemanticWorkBlocked(
            "required scheduled semantic work did not complete"
        )


def _drive_run_kernel_selected_semantic_work(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    selected_bindables: Mapping[str, Any],
    component_analyst_input_packets: Mapping[str, Mapping[str, Any]],
    query: str,
) -> None:
    """Drive qualifying semantic work exclusively from RunKernel leases."""

    from core.multicomponent_graph_scheduling import MULTICOMPONENT_SCHEDULER_STAGE

    mode = str(runtime_scope.get("strategy") or runtime_scope.get("mode") or "")
    drive_context: dict[str, Any] = {
        "runtime_scope": runtime_scope,
        "selected_bindables": dict(selected_bindables),
        "component_analyst_input_packets": {
            str(key): _safe_mapping(value)
            for key, value in component_analyst_input_packets.items()
        },
        "query": query,
        "cost_recorded_child_action_ids": set(),
        "additional_scrutineer_trigger_reasons": (
            *(("deep_mode",) if mode.casefold() == "deep" else ()),
            *(("high_stakes_quantitative_posture",) if _safe_mapping(
                runtime_scope.get("economist_safety_telemetry")
            ).get("high_stakes_quant_detected") is True else ()),
        ),
    }
    role_kwargs = _role_runtime_kwargs(runtime_scope)
    while True:
        scheduler = _safe_mapping(
            run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        status = str(scheduler.get("status") or "")
        if status == "completed":
            return
        if status.startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked(
                "required scheduled semantic work did not complete"
            )
        run_kernel.dispose_exhausted_optional_specialist_proposals()
        ready = run_kernel.derive_current_multicomponent_ready_work()
        if not ready:
            if run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE):
                _finalize_scheduler_graph(
                    run_kernel=run_kernel,
                    drive_context=drive_context,
                )
                continue
            raise OrdinaryMulticomponentRuntimeError(
                "active scheduler has no semantic work or deterministic completion"
            )
        try:
            _execute_run_kernel_selected_batch(
                run_kernel=run_kernel,
                role_kwargs=role_kwargs,
                drive_context=drive_context,
            )
        except Exception as exc:
            current = _safe_mapping(
                run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
            )
            if str(current.get("status") or "").startswith("blocked_"):
                raise _ScheduledSemanticWorkBlocked(
                    "required scheduled semantic work did not complete"
                ) from exc
            raise


def _execute_selected_lane(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    requested_synthesis_directive: str,
) -> None:
    accepted = run_kernel.state.initial_answer_contract
    if not _selected_multicomponent_contract(accepted):
        raise OrdinaryMulticomponentRuntimeError(
            "accepted contract lost typed multi-component qualification"
        )
    metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
    if (
        _clean_text(metadata.get("requested_synthesis_directive"), limit=360)
        != requested_synthesis_directive
    ):
        raise OrdinaryMulticomponentRuntimeError(
            "accepted contract lost typed multi-component qualification"
        )

    final_top_evidence = [
        dict(item)
        for item in runtime_scope.get("final_top_evidence") or ()
        if isinstance(item, Mapping)
    ]
    component_refs = [
        dict(item)
        for item in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    selected = select_bindable_final_passages_for_components(
        final_top_evidence,
        run_kernel.state.evidence_ledger.to_projection().to_dict(),
        component_refs,
        component_text_by_id=_accepted_component_text_by_id(accepted),
    )
    # Custody-gap exception is authorized only for the selected typed lane.
    typed_lane_custody_exception = True
    missing_component_ids = [
        str(component_ref["component_id"])
        for component_ref in component_refs
        if str(component_ref["component_id"]) not in selected
        or (
            bool(
                component_ref.get("source_obligation_candidate_ids")
                or component_ref.get("source_obligation_candidate_refs")
            )
            and not source_requirement_ids_for_component_candidate(
                run_kernel.state.evidence_ledger.to_projection().to_dict(),
                evidence_ref_id=selected[
                    str(component_ref["component_id"])
                ].evidence_ref_id,
                source_obligation_candidate_ids=tuple(
                    component_ref.get("source_obligation_candidate_ids")
                    or component_ref.get("source_obligation_candidate_refs")
                    or ()
                ),
                ignore_satisfied_provider_job_historical_gaps=(
                    typed_lane_custody_exception
                ),
            )
        )
    ]
    if missing_component_ids:
        raise OrdinaryMulticomponentRuntimeError(
            "selected multi-component lane lacks legitimate current evidence custody "
            "for: " + ",".join(missing_component_ids)
        )
    query = str(runtime_scope.get("query") or "")
    analyst_inputs = {
        str(component_ref["component_id"]): component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=accepted,
            component_ref=component_ref,
            evidence_input=_evidence_input(
                selected.get(str(component_ref["component_id"]))
            ),
        )
        for component_ref in component_refs
    }
    run_kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=analyst_inputs,
        requested_synthesis_directive=requested_synthesis_directive,
        configured_provider=str(runtime_scope.get("smart_provider") or ""),
        specialist_capability_registry=getattr(
            runtime_scope.get("deps"),
            "specialist_capability_registry",
            None,
        ),
        specialist_execution_policy=getattr(
            runtime_scope.get("deps"),
            "specialist_execution_policy",
            None,
        ),
    )
    _drive_run_kernel_selected_semantic_work(
        run_kernel=run_kernel,
        runtime_scope=runtime_scope,
        selected_bindables=selected,
        component_analyst_input_packets=analyst_inputs,
        query=query,
    )


def execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    execute_selected_lane: bool = True,
) -> OrdinaryMulticomponentResult:
    """Select the typed lane before canonical semantic production."""

    def direct_or_deferred() -> OrdinaryMulticomponentResult:
        # The early scout-continuation call is selection-only. It must not
        # move the legacy direct semantic producer ahead of its established
        # later ordinary handoff for nonqualifying requests.
        if not execute_selected_lane:
            return OrdinaryMulticomponentResult(
                status=OrdinaryMulticomponentStatus.NOT_QUALIFIED,
            )
        direct = execute_ordinary_semantic_producer_handoff_from_scope(
            run_kernel,
            runtime_scope,
        )
        return OrdinaryMulticomponentResult(
            status=OrdinaryMulticomponentStatus.NOT_QUALIFIED,
            direct_handoff=direct,
        )

    if run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE):
        return OrdinaryMulticomponentResult(
            status=OrdinaryMulticomponentStatus.ALREADY_COMPLETED
        )
    scheduler_state = _safe_mapping(
        run_kernel.state.projections.get("multicomponent_graph_scheduler")
    )
    if str(scheduler_state.get("status") or "").startswith("blocked_"):
        return OrdinaryMulticomponentResult(
            status=OrdinaryMulticomponentStatus.ALREADY_COMPLETED
        )
    if run_kernel.state.initial_answer_contract:
        accepted = run_kernel.state.initial_answer_contract
        metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
        if _selected_multicomponent_contract(accepted):
            if not execute_selected_lane:
                return OrdinaryMulticomponentResult(
                    status=OrdinaryMulticomponentStatus.SELECTED_PENDING
                )
            requested_synthesis_directive = _clean_text(
                metadata.get("requested_synthesis_directive"),
                limit=360,
            )
            assert requested_synthesis_directive is not None
            try:
                _execute_selected_lane(
                    run_kernel=run_kernel,
                    runtime_scope=runtime_scope,
                    requested_synthesis_directive=requested_synthesis_directive,
                )
            except _ScheduledSemanticWorkBlocked:
                # Canonical exhaustion/failure is ordinary readiness input.  Do
                # not escape the selected lane or invoke the direct producer.
                pass
            return OrdinaryMulticomponentResult(
                status=OrdinaryMulticomponentStatus.COMPLETED
            )
        return direct_or_deferred()

    search_work_plan = _safe_mapping(run_kernel.state.search_work_plan)
    if not search_work_plan or not _real_query_shape_plan(search_work_plan):
        return direct_or_deferred()
    run_contract = _safe_mapping(runtime_scope.get("run_contract_projection"))
    route = _safe_mapping(run_kernel.state.projections.get("route_request"))
    query = str(runtime_scope.get("query") or "")
    mode = str(runtime_scope.get("strategy") or runtime_scope.get("mode") or "")
    records = build_deterministic_search_work_runtime_records(
        DeterministicSearchWorkRuntimeInput(
            contract_id=str(
                run_contract.get("contract_id") or run_kernel.state.run_id
            ),
            run_contract_projection=run_contract,
            route_facts=route,
            requested_mode=mode,
            selected_depth=run_contract.get("selected_depth"),
            safe_query_preview=query,
        )
    )
    assessment = records.query_shape_assessment
    assessment_metadata = _safe_mapping(assessment.metadata)
    requested_synthesis_directive = _clean_text(
        assessment_metadata.get("requested_synthesis_directive"),
        limit=360,
    )
    component_count = len(assessment.component_candidates)
    qualifying = (
        assessment_metadata.get("explicit_factual_component_list") is True
        and requested_synthesis_directive is not None
        and 2 <= component_count <= 5
    )
    if not qualifying:
        return direct_or_deferred()
    qmr = build_question_meaning_record_from_search_work_plan(
        assessment=assessment,
        route_facts=route,
        run_contract_projection=run_contract,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        query=query,
        requested_mode=mode,
    )
    if qmr is None:
        raise OrdinaryMulticomponentRuntimeError(
            "typed multi-component qualification could not build its answer contract"
        )
    _accept_question_meaning_record(run_kernel, qmr)
    return OrdinaryMulticomponentResult(
        status=OrdinaryMulticomponentStatus.SELECTED_PENDING
    )

def ordinary_multicomponent_path_completed(run_kernel: Any) -> bool:
    return bool(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))


def ordinary_multicomponent_path_selected(run_kernel: Any) -> bool:
    return _selected_multicomponent_contract(run_kernel.state.initial_answer_contract)


__all__ = [
    "OrdinaryMulticomponentResult",
    "OrdinaryMulticomponentRuntimeError",
    "OrdinaryMulticomponentStatus",
    "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
    "ordinary_multicomponent_path_completed",
    "ordinary_multicomponent_path_selected",
]
