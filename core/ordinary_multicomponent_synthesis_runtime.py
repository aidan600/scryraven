"""Ordinary product-consumed bounded multi-component synthesis lane.

The eligibility decision is made before semantic production.  A qualifying
run therefore executes only component Analyst -> component D-prime ->
RunKernel admission; it never executes the direct semantic producer and then
chooses between competing outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_STAGE,
    admit_synthesis_node_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    finalize_component_work_graph_v1,
    graph_with_accounting,
    graph_with_scrutineer,
    graph_with_synthesis_validation,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
    synthesis_dprime_input_packet,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.multicomponent_component_admission import (
    component_analyst_input_packet,
    component_dprime_input_packet,
    execute_multicomponent_component_admission,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    execute_multicomponent_role_call,
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


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
    deps = runtime_scope.get("deps")
    cleaner = getattr(deps, "clean_json_response", None)
    ask_model = runtime_scope.get("ask_model")
    if not callable(ask_model):
        raise OrdinaryMulticomponentRuntimeError(
            "qualifying multi-component lane requires ordinary model transport"
        )
    return {
        "ask_model": ask_model,
        "clean_json_response": cleaner if callable(cleaner) else None,
        "provider": str(runtime_scope.get("smart_provider") or ""),
        "model": str(runtime_scope.get("smart_model") or ""),
        "base_url": str(runtime_scope.get("local_url") or ""),
        "api_key": str(runtime_scope.get("or_api_key") or ""),
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


def _evidence_input(bindable: Any | None) -> dict[str, Any]:
    if bindable is None:
        return {
            "evidence_status": "missing",
            "bounded_text": None,
            "candidate_custody_ref": {},
        }
    passage = bindable.passage
    candidate = bindable.candidate_record
    return {
        "evidence_status": "available",
        "evidence_ref_id": bindable.evidence_ref_id,
        "source_title": _clean_text(passage.get("title"), limit=240),
        "source_url": _clean_text(passage.get("url"), limit=500),
        "bounded_text": _clean_text(passage.get("text"), limit=6000),
        "currentness": _clean_text(
            passage.get("currentness_signal") or passage.get("currentness"),
            limit=120,
        ),
        "candidate_custody_ref": {
            key: candidate.get(key)
            for key in (
                "candidate_id",
                "fact_disposition",
                "readable_status",
                "currentness_signal",
            )
            if candidate.get(key) is not None
        },
    }


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
    accepted = run_kernel.state.initial_answer_contract
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


def _execute_selected_lane(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    requested_synthesis_directive: str,
) -> None:
    accepted = run_kernel.state.initial_answer_contract
    metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
    if (
        metadata.get("explicit_factual_component_list") is not True
        or _clean_text(metadata.get("requested_synthesis_directive"), limit=360)
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
            )
        )
    ]
    if missing_component_ids:
        raise OrdinaryMulticomponentRuntimeError(
            "selected multi-component lane lacks legitimate current evidence custody "
            "for: " + ",".join(missing_component_ids)
        )
    role_kwargs = _role_runtime_kwargs(runtime_scope)
    query = str(runtime_scope.get("query") or "")
    component_admission_refs: list[dict[str, Any]] = []
    for component_ref in component_refs:
        component_id = str(component_ref["component_id"])
        bindable = selected.get(component_id)
        analyst_input = component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=accepted,
            component_ref=component_ref,
            evidence_input=_evidence_input(bindable),
        )
        analyst_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_COMPONENT_ANALYST,
            input_packet=analyst_input,
            logical_evaluation_key=component_id,
            **role_kwargs,
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
            **role_kwargs,
        )
        observation, content_refs, coverage = _semantic_material(
            run_kernel=run_kernel,
            component_ref=component_ref,
            bindable=bindable,
            analyst_artifact=analyst_artifact,
            dprime_artifact=dprime_artifact,
            query=query,
        )
        component_admission_refs.append(
            execute_multicomponent_component_admission(
                run_kernel=run_kernel,
                component_id=component_id,
                analyst_artifact=analyst_artifact,
                dprime_artifact=dprime_artifact,
                analyst_input_packet=analyst_input,
                semantic_observation=observation,
                sanitized_content_references=content_refs,
                component_coverage_record=coverage,
            )
        )

    admission_by_id = {
        item["component_id"]: item for item in component_admission_refs
    }
    component_nodes = [
        component_work_node_v1_from_admitted_component(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_component_ref=component_ref,
            component_admission_ref=admission_by_id[component_ref["component_id"]],
        )
        for component_ref in component_refs
    ]
    contract_ref = _accepted_contract_ref(accepted)
    cross_input = cross_component_input_packet(
        component_nodes=component_nodes,
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=requested_synthesis_directive,
    )
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key="graph-v1",
        **role_kwargs,
    )
    graph_candidate = component_work_graph_v1_from_cross_component_artifact(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=requested_synthesis_directive,
        component_nodes=component_nodes,
        cross_component_artifact=cross_artifact,
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="structure",
        graph_candidate=graph_candidate,
    )

    scrutineer_ran = False
    for synthesis_key in list(graph["synthesis_topological_order"]):
        dprime_input = synthesis_dprime_input_packet(
            graph,
            synthesis_key=synthesis_key,
        )
        dprime_artifact = execute_multicomponent_role_call(
            run_kernel=run_kernel,
            role=ROLE_SYNTHESIS_DPRIME,
            input_packet=dprime_input,
            logical_evaluation_key=synthesis_key,
            **role_kwargs,
        )
        graph = reduce_component_work_graph_v1(
            run_kernel=run_kernel,
            operation="synthesis_validation",
            synthesis_key=synthesis_key,
            graph_candidate=graph_with_synthesis_validation(
                graph,
                synthesis_key=synthesis_key,
                dprime_artifact=dprime_artifact,
            ),
        )
        node = next(
            item
            for item in graph["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        has_synthesis_input = any(
            item.get("node_kind") == "synthesis"
            for item in node.get("input_node_refs") or ()
        )
        if has_synthesis_input and graph.get("scrutineer_required") is True:
            if scrutineer_ran:
                raise OrdinaryMulticomponentRuntimeError(
                    "Phase 1 permits exactly one full-case Scrutineer evaluation"
                )
            scrutineer_artifact = execute_multicomponent_role_call(
                run_kernel=run_kernel,
                role=ROLE_SCRUTINEER,
                input_packet=scrutineer_input_packet(graph),
                logical_evaluation_key="full-case",
                **role_kwargs,
            )
            graph = reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="scrutiny",
                graph_candidate=graph_with_scrutineer(
                    graph,
                    scrutineer_artifact=scrutineer_artifact,
                ),
            )
            scrutineer_ran = True
        node = next(
            item
            for item in graph["synthesis_nodes"]
            if item["synthesis_key"] == synthesis_key
        )
        if node.get("status") == "validated":
            graph = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=synthesis_key,
            )

    logical = {
        "component_analyst_evaluations": len(component_refs),
        "component_dprime_evaluations": len(component_refs),
        "cross_component_analyst_evaluations": 1,
        "synthesis_dprime_evaluations": len(graph["synthesis_nodes"]),
        "scrutineer_evaluations": 1 if scrutineer_ran else 0,
    }
    physical = {
        "component_analyst_calls": len(component_refs),
        "component_dprime_calls": len(component_refs),
        "cross_component_analyst_calls": 1,
        "synthesis_dprime_calls": len(graph["synthesis_nodes"]),
        "scrutineer_calls": 1 if scrutineer_ran else 0,
    }
    graph = reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            graph,
            logical_accounting=logical,
            physical_call_accounting=physical,
        ),
    )
    reduce_component_work_graph_v1(
        run_kernel=run_kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )


def execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
) -> OrdinaryMulticomponentResult:
    """Select the typed lane before canonical semantic production."""

    def direct_or_deferred() -> OrdinaryMulticomponentResult:
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
    if run_kernel.state.initial_answer_contract:
        accepted = run_kernel.state.initial_answer_contract
        metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
        if _selected_multicomponent_contract(accepted):
            requested_synthesis_directive = _clean_text(
                metadata.get("requested_synthesis_directive"),
                limit=360,
            )
            assert requested_synthesis_directive is not None
            _execute_selected_lane(
                run_kernel=run_kernel,
                runtime_scope=runtime_scope,
                requested_synthesis_directive=requested_synthesis_directive,
            )
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
            contract_id=str(run_contract.get("contract_id") or run_kernel.state.run_id),
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
