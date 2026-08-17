"""Ordinary product-consumed bounded multi-component synthesis lane.

The eligibility decision is made before semantic production.  A qualifying
run therefore executes only component Analyst -> component D-prime ->
RunKernel admission; it never executes the direct semantic producer and then
chooses between competing outputs.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
from threading import Lock
from typing import Any, Mapping, Sequence

from core.analyst_query_resolution_proposal import (
    ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY,
    PROPOSAL_LIFECYCLE_STATUSES,
    arbitrate_analyst_query_resolution_proposals,
    bind_analyst_query_resolution_proposal,
    selected_proposals_for_role_artifact,
)
from core.cap_enforcement import RunCapExceeded
from core.component_coverage_reduction_runtime import (
    ledger_qualification_blockers_for_satisfied_coverage,
)
from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_STAGE,
    admit_synthesis_node_via_runkernel,
    bind_inferred_resolution_proposal_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    component_work_graph_v1_resynthesis_from_cross_component_artifact,
    component_work_graph_v1_selective_resynthesis_from_cross_artifact,
    cross_component_input_packet,
    current_graph_reconciliation_input_packet,
    current_graph_reconciliation_required,
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
    build_sanitized_content_reference_from_passage,
    execute_ordinary_semantic_producer_handoff_from_scope,
    select_bindable_final_passages_for_components,
    source_requirement_ids_for_component_candidate,
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


def _component_requires_direct_work(
    component_ref: Mapping[str, Any],
) -> bool:
    return "direct" in {str(item) for item in component_ref.get("allowed_support_kinds") or ()}


def _matching_records(values: Any, **expected: Any) -> list[dict[str, Any]]:
    return [
        dict(raw)
        for raw in values or ()
        if isinstance(raw, Mapping) and all(raw.get(key) == value for key, value in expected.items())
    ]


def _one_record(values: Any, reason: str, **expected: Any) -> dict[str, Any]:
    records = _matching_records(values, **expected)
    if len(records) != 1:
        raise OrdinaryMulticomponentRuntimeError(reason)
    return records[0]


_EVIDENCE_LEDGER_REQUIREMENT_KIND_BY_SOURCE_OBLIGATION_KIND = {
    "official_current": "official_current",
    "legal_current_primary": "legal",
    "canonical_documentation": "canonical",
    "primary_source_documents": "canonical",
    "source_bound_numeric": "source_bound",
    "peer_reviewed": "academic",
    "reputable_secondary": "general",
    "conflict_resolution": "general",
    "date_bound_currentness": "current",
    "user_document": "user_document",
    "no_special_obligation": "general",
}


def _evidence_ledger_requirement_kind_for_accepted_source_obligation(
    *,
    accepted_contract: Mapping[str, Any],
    source_obligation_id: str,
) -> str:
    accepted_obligation = _one_record(
        accepted_contract.get("accepted_source_obligation_refs"),
        "SearchOS qualification source obligation is stale",
        source_obligation_id=source_obligation_id,
    )
    source_obligation_kind = str(
        accepted_obligation.get("kind")
        or accepted_obligation.get("obligation_kind")
        or ""
    ).strip().casefold()
    ledger_requirement_kind = (
        _EVIDENCE_LEDGER_REQUIREMENT_KIND_BY_SOURCE_OBLIGATION_KIND.get(
            source_obligation_kind
        )
    )
    if not ledger_requirement_kind:
        raise OrdinaryMulticomponentRuntimeError(
            "SearchOS qualification source obligation kind is unsupported"
        )
    return ledger_requirement_kind


def _candidate_ids(projection: Mapping[str, Any]) -> set[str]:
    return {str(_safe_mapping(item).get("candidate_id") or "") for item in projection.get("candidate_records") or ()}


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

    scheduler_state = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    if scheduler_state.get("status") != "active":
        # Historical/component tests without a qualifying product scheduler keep
        # their established direct RunKernel role authorization contract. A
        # completed scheduler likewise cannot lease post-recovery graph reproof.
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
        raise _ScheduledSemanticWorkBlocked("required semantic work denied by the compatibility envelope")
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
            "ordinary deterministic transition requested work other than the RunKernel-selected first ready item"
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
        scheduler = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
        if str(scheduler.get("status") or "").startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked("required scheduled semantic work did not complete") from exc
        raise


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _accepted_contract_ref(accepted: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": accepted.get("owner"),
        "canonical_state": accepted.get("canonical_state") is True,
        "run_id": accepted.get("run_id"),
        "request_id": accepted.get("request_id"),
        "accepted_contract_version": accepted.get("accepted_contract_version"),
        "accepted_contract_digest": accepted.get("accepted_contract_digest"),
        "parent_question_meaning_record_id": accepted.get("parent_question_meaning_record_id"),
        "parent_question_meaning_record_digest": accepted.get("parent_question_meaning_record_digest"),
        "accepted_answer_component_count": accepted.get("accepted_answer_component_count"),
    }


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
    canonical_provider = normalize_canonical_model_provider(runtime_scope.get("smart_provider"))
    model = str(runtime_scope.get("smart_model") or "")
    if not callable(transport):
        transport = build_strict_one_shot_smart_model_transport(
            smart_provider=canonical_provider,
            smart_model=model,
            local_url=str(runtime_scope.get("local_url") or "") or None,
            openrouter_api_key=str(runtime_scope.get("or_api_key") or "") or None,
            cap_policy=runtime_scope.get("cap_policy"),
        )
    return {
        "strict_one_shot_transport": transport,
        "clean_json_response": cleaner if callable(cleaner) else None,
        "provider": canonical_provider,
        "model": model,
        "use_reasoning": bool(runtime_scope.get("use_reasoning")),
        "effort": str(runtime_scope.get("smart_reasoning_effort") or "medium"),
    }


def _component_text_by_id(qmr: Any) -> dict[str, str]:
    return {component.component_id: component.user_facing_question for component in qmr.answer_components}


def _accepted_component_text_by_id(
    accepted: Mapping[str, Any],
) -> dict[str, str]:
    return {
        str(component["component_id"]): str(component["user_facing_question"])
        for component in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(component, Mapping) and component.get("component_id") and component.get("user_facing_question")
    }


def _selected_multicomponent_contract(
    accepted: Mapping[str, Any],
    *,
    allow_searchos_component_receiver: bool = False,
) -> bool:
    metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
    component_refs = [
        item for item in accepted.get("accepted_answer_component_refs") or () if isinstance(item, Mapping)
    ]
    if allow_searchos_component_receiver:
        return 1 <= len(component_refs) <= 5
    return (
        metadata.get("explicit_factual_component_list") is True
        and _clean_text(metadata.get("requested_synthesis_directive"), limit=360) is not None
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


def _exact_currency_fact(*, candidate: Mapping[str, Any], passage: Mapping[str, Any]) -> str | None:
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
    canonical_currency = _exact_currency_fact(candidate=candidate, passage=passage)
    conflict, contradictory = _exact_conflict_facts(candidate=candidate, passage=passage)
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
    searchos_recovery_cycle_ref: Mapping[str, Any] | None = None,
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
        raise OrdinaryMulticomponentRuntimeError("component roles claimed support without bounded evidence")
    accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    component_id = str(component_ref["component_id"])
    recovery_cycle_id = str(_safe_mapping(searchos_recovery_cycle_ref).get("cycle_id") or "")
    recovery_suffix = ":" + recovery_cycle_id if recovery_cycle_id else ""
    evidence_ref_id = _qualify_searchos_read_material_after_component_dprime(
        run_kernel=run_kernel,
        component_ref=component_ref,
        bindable=bindable,
        dprime_artifact=dprime_artifact,
    ) or str(bindable.evidence_ref_id)
    content_ref = build_sanitized_content_reference_from_passage(
        passage=bindable.passage,
        evidence_ref_id=evidence_ref_id,
        accepted_contract=accepted,
        component_ref=component_ref,
        content_ref_id=(f"content:{component_id}:{evidence_ref_id}{recovery_suffix}"),
    )
    observation = SemanticObservation(
        observation_id=(f"observation:{component_id}:{bindable.evidence_ref_id}{recovery_suffix}"),
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        contract_version=accepted["accepted_contract_version"],
        contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_id,
        component_revision=str(component_ref["component_revision"]),
        component_contract_digest=str(component_ref["component_digest"]),
        evidence_refs=(evidence_ref_id,),
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
            "searchos_recovery_cycle_ref": deepcopy(_safe_mapping(searchos_recovery_cycle_ref)),
        },
    ).require_valid()
    coverage = build_component_coverage_proposal(
        accepted_contract=accepted,
        observation=observation,
        content_ref=content_ref,
        evidence_ledger_projection=(run_kernel.state.evidence_ledger.to_projection().to_dict()),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        query=query,
        ignore_satisfied_provider_job_historical_gaps=True,
    )
    if coverage is not None and recovery_cycle_id:
        coverage = replace(
            coverage,
            record_id=(f"coverage:{component_id}:searchos-recovery:{recovery_cycle_id}"),
            metadata={
                **dict(coverage.metadata),
                "searchos_recovery_cycle_ref": deepcopy(_safe_mapping(searchos_recovery_cycle_ref)),
            },
        ).require_valid()
    if coverage is None:
        obligation_ids = list(
            component_ref.get("source_obligation_candidate_ids")
            or component_ref.get("source_obligation_candidate_refs")
            or ()
        )
        qualified_requirement_ids = source_requirement_ids_for_component_candidate(
            run_kernel.state.evidence_ledger.to_projection().to_dict(),
            evidence_ref_id=evidence_ref_id,
            component_id=component_id,
            source_obligation_candidate_ids=tuple(obligation_ids),
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            answer_contract_version=accepted["accepted_contract_version"],
            answer_contract_digest=accepted["accepted_contract_digest"],
            ignore_satisfied_provider_job_historical_gaps=True,
        )
        qualification_blockers = ledger_qualification_blockers_for_satisfied_coverage(
            coverage={
                "coverage_state": "satisfied",
                "content_reference_bindings": [{"evidence_ref_id": evidence_ref_id}],
                "evidence_ledger_binding": {"source_requirement_ids": list(qualified_requirement_ids)},
                "source_obligation_status": "satisfied",
            },
            evidence_ledger_projection=(run_kernel.state.evidence_ledger.to_projection().to_dict()),
            accepted_component=component_ref,
            extra_evidence_refs=(evidence_ref_id,),
        )
        raise OrdinaryMulticomponentRuntimeError(
            "component D-prime support could not satisfy canonical coverage for "
            + component_id
            + " (evidence_ref="
            + evidence_ref_id
            + ", obligations="
            + ",".join(str(item) for item in obligation_ids)
            + ", qualified_requirements="
            + ",".join(qualified_requirement_ids)
            + ", qualification_blockers="
            + ",".join(str(item.get("code") or "unknown") for item in qualification_blockers)
            + ")"
        )
    return observation.to_dict(), [content_ref.to_dict()], coverage.to_dict()


def _qualify_searchos_read_material_after_component_dprime(
    *,
    run_kernel: Any,
    component_ref: Mapping[str, Any],
    bindable: Any,
    dprime_artifact: Mapping[str, Any],
) -> str | None:
    """Link one exact READ-custody material only after D-prime support.

    Fetch/read custody alone remains non-supporting.  This reducer adds the
    narrow EvidenceLedger source-requirement link needed by the existing
    component coverage reducer only when the selected passage proves an exact
    SearchOS semantic handoff and the completed component D-prime artifact has
    already supported that bounded Analyst proposal.
    """

    passage = _safe_mapping(bindable.passage)
    lineage = _safe_mapping(passage.get("searchos_qualification_lineage"))
    slot_ref = _safe_mapping(lineage.get("slot_ref"))
    handoff_ref = _safe_mapping(lineage.get("semantic_handoff_ref"))
    component_id = str(component_ref.get("component_id") or "")
    current_handoff = _current_searchos_read_handoff_for_component(
        run_kernel=run_kernel,
        passage=passage,
        component_id=component_id,
    )
    if not (
        lineage
        and passage.get("material_authority") == "read_custody_material"
        and passage.get("_provider") == "searchos_read_custody"
        and current_handoff
        and slot_ref.get("source_obligation_id")
        and handoff_ref.get("semantic_handoff_id")
        and _safe_mapping(dprime_artifact.get("semantic_output")).get("validation_status")
        in {"supported", "supported_with_caveats"}
    ):
        if passage.get("_provider") == "searchos_read_custody":
            raise OrdinaryMulticomponentRuntimeError(
                "SearchOS qualification prerequisite failed "
                f"(lineage={bool(lineage)}, current_handoff={current_handoff}, "
                f"obligation={bool(slot_ref.get('source_obligation_id'))}, "
                f"handoff={bool(handoff_ref.get('semantic_handoff_id'))}, "
                "dprime=" + str(_safe_mapping(dprime_artifact.get("semantic_output")).get("validation_status")) + ")"
            )
        return None

    from core.evidence_ledger_runtime import (
        execute_evidence_ledger_reduction_action,
    )

    component_identity = {
        key: component_ref.get(key) for key in ("component_id", "component_revision", "component_digest")
    }
    navigation_ref, packet_ref, custody_ref = (
        _safe_mapping(lineage.get(key))
        for key in ("navigation_content_reference", "fetch_read_content_packet", "read_custody_ref")
    )
    evidence_ref_id = str(bindable.evidence_ref_id)
    dprime_digest = str(dprime_artifact.get("artifact_digest") or "")
    accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    accepted_component = _one_record(
        accepted.get("accepted_answer_component_refs"),
        "SearchOS qualification component is stale",
        **component_identity,
    )
    component_obligations = {
        str(_safe_mapping(item).get("candidate_id") or item)
        for item in accepted_component.get("source_obligation_candidate_ids") or ()
    }
    ref_fields = (
        (navigation_ref, ("reference_id", "reference_digest")),
        (packet_ref, ("packet_id", "packet_digest")),
        (custody_ref, ("read_custody_material_id", "read_custody_material_digest")),
        (handoff_ref, ("semantic_handoff_id", "semantic_handoff_digest")),
    )
    if (
        str(slot_ref.get("source_obligation_id") or "") not in component_obligations
        or lineage.get("canonical_candidate_id") != evidence_ref_id
        or passage.get("searchos_evidence_ledger_candidate_id") != evidence_ref_id
        or _safe_mapping(passage.get("searchos_slot_ref")) != slot_ref
        or _safe_mapping(passage.get("searchos_semantic_handoff_ref")) != handoff_ref
        or any(not all(ref.get(key) for key in keys) for ref, keys in ref_fields)
        or len(dprime_digest) != 64
        or set(dprime_digest) - set("0123456789abcdef")
    ):
        raise OrdinaryMulticomponentRuntimeError("SearchOS qualification lineage is incomplete or stale")

    slot_id = str(slot_ref["slot_id"])
    obligation_id = str(slot_ref["source_obligation_id"])
    qualification_obligation_ids = [obligation_id]
    requirement_kinds_by_obligation = {
        qualified_obligation_id: (
            _evidence_ledger_requirement_kind_for_accepted_source_obligation(
                accepted_contract=accepted,
                source_obligation_id=qualified_obligation_id,
            )
        )
        for qualified_obligation_id in qualification_obligation_ids
    }
    requirement_ids_by_obligation = {
        qualified_obligation_id: (
            "searchos_semantic_requirement:"
            + qualified_obligation_id.split(":", 1)[-1].casefold().replace("-", "_").replace(" ", "_")
            + ":"
            + safe_packet_digest(
                {
                    "slot_id": slot_id,
                    "component_id": component_id,
                    "source_obligation_id": qualified_obligation_id,
                }
            )[:24]
        )
        for qualified_obligation_id in qualification_obligation_ids
    }
    requirement_ids = list(requirement_ids_by_obligation.values())
    qualification_basis = {
        "identity_kind": "searchos_custody_qualification_v1",
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "canonical_candidate_id": evidence_ref_id,
        "navigation_content_reference": navigation_ref,
        "fetch_read_content_packet": packet_ref,
        "read_custody_ref": custody_ref,
        "component_ref": component_identity,
        "requirement_id": requirement_ids[0],
        "requirement_ids_by_obligation": requirement_ids_by_obligation,
        "slot_ref": slot_ref,
        "semantic_handoff_ref": handoff_ref,
        "component_dprime_artifact_digest": dprime_digest,
    }
    qualification_id = "searchos_custody_qualification:" + safe_packet_digest(qualification_basis)
    ledger = run_kernel.state.evidence_ledger
    before_projection = ledger.to_projection().to_dict()
    before_candidate_ids = _candidate_ids(before_projection)
    physical = ledger.to_fetch_read_candidate_custody_projection().get("fetch_read_candidate_custody_records")
    slot = _safe_mapping(_safe_mapping(run_kernel.state.searchos_state.get("slots_by_id")).get(slot_id))
    current_custody = _one_record(
        slot.get("custody_refs"),
        "SearchOS qualification lost current custody",
        evidence_ledger_candidate_id=evidence_ref_id,
        read_custody_material_id=custody_ref["read_custody_material_id"],
        read_custody_material_digest=custody_ref["read_custody_material_digest"],
    )
    physical_record = _one_record(
        physical,
        "SearchOS qualification lost physical custody",
        reference_id=navigation_ref["reference_id"],
        reference_digest=navigation_ref["reference_digest"],
        fetch_read_content_packet_id=packet_ref["packet_id"],
        fetch_read_content_packet_digest=packet_ref["packet_digest"],
    )
    ledger_candidate_id = str(physical_record["candidate_id"])
    projected_candidate_id = ledger_candidate_id if lineage.get("navigation_origin") is True else evidence_ref_id
    if (
        projected_candidate_id not in before_candidate_ids
        or len(_matching_records(physical, candidate_id=ledger_candidate_id)) != 1
        or lineage.get("navigation_origin") is True
        and ledger_candidate_id != evidence_ref_id
        or any(
            _safe_mapping(current_custody.get("evidence_ledger_custody_ref")).get(key) != value
            for key, value in navigation_ref.items()
        )
        or any(
            _safe_mapping(current_custody.get("fetch_read_content_packet_ref")).get(key) != value
            for key, value in packet_ref.items()
        )
    ):
        raise OrdinaryMulticomponentRuntimeError("SearchOS qualification lost canonical physical custody")

    candidate = _safe_mapping(bindable.candidate_record)
    lineage_facts = _safe_mapping(lineage.get("source_facts"))
    if any(key in passage and passage.get(key) != value for key, value in lineage_facts.items()):
        raise OrdinaryMulticomponentRuntimeError("SearchOS qualification source facts drifted")
    fact_passage = {**lineage_facts, **passage}
    aliases_by_key = {
        "source_class": ("source_class",),
        "source_tier": ("source_tier",),
        "currentness_signal": ("currentness_signal", "currentness"),
        "evidence_material_type": ("evidence_material_type",),
        "readable_status": ("readable_status", "readability_status"),
        "fetchable_status": ("fetchable_status", "fetch_status"),
    }
    source_facts = {
        key: value
        for key, aliases in aliases_by_key.items()
        if (
            value := _structured_evidence_fact(
                candidate=candidate, passage=fact_passage, candidate_keys=aliases, passage_keys=aliases
            )
        )
    }
    for key in ("contextual_only", "lower_tier"):
        value = fact_passage.get(key)
        if isinstance(value, bool) or candidate.get(key) is True:
            source_facts[key] = value if isinstance(value, bool) else True
    if source_facts.get("contextual_only") or source_facts.get("lower_tier"):
        source_facts["eligible_for_stronger_obligation"] = False
    elif candidate.get("eligible_for_stronger_obligation") is True:
        # Preserve established canonical truth.  Omitting a false/default value
        # lets EvidenceLedger derive eligibility from the source taxonomy.
        source_facts["eligible_for_stronger_obligation"] = True
    elif (
        source_facts.get("source_tier") == "official"
        and source_facts.get("source_class") == "official_current_rules"
        and source_facts.get("currentness_signal") == "current"
    ):
        source_facts["eligible_for_stronger_obligation"] = True
    explicit_final_eligibility = lineage_facts.get(
        "final_evidence_eligible",
        "unknown",
    )
    if explicit_final_eligibility is False:
        source_facts["final_evidence_eligible"] = False
        source_facts["final_evidence_eligibility_explicit"] = True
    elif slot_ref.get("recovery_cycle_id"):
        source_facts["final_evidence_eligible"] = True

    payload = {
        "observation_id": qualification_id,
        "observation_source": "searchos_component_dprime_material_qualification",
        "source_requirements": [
            {
                "requirement_id": requirement_ids_by_obligation[qualified_obligation_id],
                "requirement_kind": requirement_kinds_by_obligation[
                    qualified_obligation_id
                ],
                "source_obligation_id": qualified_obligation_id,
                "component_id": component_id,
                "run_id": run_kernel.state.run_id,
                "request_id": run_kernel.state.request_id,
                "answer_contract_version": accepted["accepted_contract_version"],
                "answer_contract_digest": accepted["accepted_contract_digest"],
                "origin_ref": ("RunKernel.SearchOSIterativeJudgment:" + str(handoff_ref["semantic_handoff_id"])),
                "aggregate_counts_insufficient": False,
            }
            for qualified_obligation_id in qualification_obligation_ids
        ],
        "candidates": [
            {
                "candidate_id": evidence_ref_id,
                "requirement_id": requirement_ids[0],
                "disposition": "accepted",
                "record_kind": "fact",
                "linked_requirement_ids": requirement_ids,
                "link_reason": ("exact_searchos_read_custody_component_dprime_supported"),
                **source_facts,
            }
        ],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "candidate_id": evidence_ref_id,
                "link_reason": ("exact_searchos_read_custody_component_dprime_supported"),
                "link_status": "accepted",
            }
            for requirement_id in requirement_ids
        ],
    }
    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": payload["observation_source"],
            "qualification_id": qualification_id,
            "qualification_basis": qualification_basis,
        }
    )
    result = execute_evidence_ledger_reduction_action(action, payload=payload)
    run_kernel.reduce(result.observation)
    projection = ledger.to_projection().to_dict()
    if _candidate_ids(projection) != before_candidate_ids:
        raise OrdinaryMulticomponentRuntimeError("SearchOS qualification replaced canonical candidate state")
    _one_record(
        projection.get("candidate_records"),
        "SearchOS candidate qualification missing",
        candidate_id=projected_candidate_id,
        fact_disposition="accepted",
        **source_facts,
    )
    _one_record(
        projection.get("custody_records"),
        "SearchOS qualification custody missing",
        candidate_id=projected_candidate_id,
        requirement_id=requirement_ids[0],
        observation_id=qualification_id,
        disposition="accepted",
    )
    for requirement_id in requirement_ids:
        _one_record(
            projection.get("source_requirements"),
            "SearchOS requirement missing",
            requirement_id=requirement_id,
        )
        _one_record(
            projection.get("requirement_links"),
            "SearchOS qualification link missing",
            candidate_id=projected_candidate_id,
            requirement_id=requirement_id,
            link_status="accepted",
        )
    _one_record(
        projection.get("observation_refs"),
        "SearchOS qualification observation missing",
        observation_id=qualification_id,
    )
    return evidence_ref_id


def _current_searchos_read_handoff_for_component(
    *,
    run_kernel: Any,
    passage: Mapping[str, Any],
    component_id: str,
) -> bool:
    searchos_state = _safe_mapping(run_kernel.state.searchos_state)
    slots_by_id = _safe_mapping(searchos_state.get("slots_by_id"))
    slot_ref = _safe_mapping(passage.get("searchos_slot_ref"))
    slot = _safe_mapping(slots_by_id.get(str(slot_ref.get("slot_id") or "")))
    if (
        not slot
        or not component_id
        or slot.get("posture") != "semantically_handed_off"
        or _safe_mapping(slot.get("slot_ref")) != slot_ref
        or slot_ref.get("component_id") != component_id
    ):
        return False
    handoff_ref = _safe_mapping(passage.get("searchos_semantic_handoff_ref"))
    current_handoff = any(
        _safe_mapping(item).get("semantic_handoff_id") == handoff_ref.get("semantic_handoff_id")
        and _safe_mapping(item).get("semantic_handoff_digest") == handoff_ref.get("semantic_handoff_digest")
        and _safe_mapping(_safe_mapping(item).get("slot_ref")) == slot_ref
        for item in searchos_state.get("semantic_handoff_refs") or ()
        if isinstance(item, Mapping)
    )
    evidence_ref_id = str(passage.get("searchos_evidence_ledger_candidate_id") or passage.get("source_id") or "")
    current_custody = any(
        _safe_mapping(item).get("evidence_ledger_candidate_id") == evidence_ref_id
        and _safe_mapping(_safe_mapping(item).get("slot_ref")) == slot_ref
        and _safe_mapping(item).get("material_authority") == "read_custody_material"
        and _safe_mapping(item).get("readable") is True
        and _safe_mapping(item).get("stale") is False
        for item in slot.get("custody_refs") or ()
        if isinstance(item, Mapping)
    )
    return bool(current_handoff and current_custody)


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
        _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get("component_analyst_input_packets")
    )
    if not component_packets:
        raise OrdinaryMulticomponentRuntimeError("fresh resynthesis requires current scheduler-owned component packets")
    cross_input = cross_component_input_packet(
        component_nodes=graph["component_nodes"],
        accepted_contract_ref=contract_ref,
        requested_synthesis_directive=requested_synthesis_directive,
        component_analyst_input_packets=component_packets,
        accepted_component_refs=current_contract.get("accepted_answer_component_refs") or (),
        requested_mode=str(
            _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get("requested_mode") or "Balanced"
        ),
    )
    cross_key = f"graph-v1:revision:{graph['graph_revision']}"
    cross_artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=cross_input,
        logical_evaluation_key=cross_key,
        **dict(role_kwargs),
    )
    _record_analyst_query_resolution_candidates(
        run_kernel=run_kernel,
        artifact=cross_artifact,
    )
    candidate = component_work_graph_v1_resynthesis_from_cross_component_artifact(
        graph,
        accepted_contract_ref=contract_ref,
        cross_component_artifact=cross_artifact,
        component_analyst_input_packets=component_packets,
        transient_cross_input_packet=cross_input,
        accepted_component_refs=current_contract.get("accepted_answer_component_refs") or (),
        requested_mode=str(
            _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get("requested_mode") or "Balanced"
        ),
        inferred_resolution_proposals=(
            _selected_query_resolution_proposals_for_artifact(
                run_kernel=run_kernel,
                artifact=cross_artifact,
                classification="inferred_conclusion",
            )
        ),
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
        evaluation_key = f"{synthesis_key}:graph-revision:{current['graph_revision']}"
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
        node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
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
        node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
        if node.get("status") == "validated" and current.get("scrutineer_status") in {"passed", "passed_with_caveats"}:
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
    _record_analyst_query_resolution_candidates(
        run_kernel=run_kernel,
        artifact=cross_artifact,
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
    for proposal in _selected_query_resolution_proposals_for_artifact(
        run_kernel=run_kernel,
        artifact=cross_artifact,
        classification="inferred_conclusion",
    ):
        current = bind_inferred_resolution_proposal_via_runkernel(
            run_kernel=run_kernel,
            synthesis_key=str(proposal.get("local_target_key") or ""),
            proposal=proposal,
        )
    deferred_admission_keys: list[str] = []
    for synthesis_key in closure["affected_topological_order"]:
        pending_node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
        if pending_node.get("status") != "proposed":
            continue
        dprime_input = synthesis_dprime_input_packet(
            current,
            synthesis_key=synthesis_key,
        )
        evaluation_key = f"{synthesis_key}:selective:graph-revision:{current['graph_revision']}"
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
        node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
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


def _execute_current_graph_reconciliation(
    *,
    run_kernel: Any,
    graph: Mapping[str, Any],
    role_kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one fresh Cross pass and bind only current inferred proposals."""

    current = dict(graph)
    context = _safe_mapping(run_kernel.state.multicomponent_scheduler_context)
    packet = current_graph_reconciliation_input_packet(
        current,
        component_analyst_input_packets=_safe_mapping(context.get("component_analyst_input_packets")),
        requested_mode=str(context.get("requested_mode") or "Balanced"),
    )
    evaluation_key = f"current-graph-reconciliation:graph-revision:{current['graph_revision']}"
    artifact = execute_multicomponent_role_call(
        run_kernel=run_kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=packet,
        logical_evaluation_key=evaluation_key,
        **dict(role_kwargs),
    )
    _record_analyst_query_resolution_candidates(
        run_kernel=run_kernel,
        artifact=artifact,
    )
    for proposal in _selected_query_resolution_proposals_for_artifact(
        run_kernel=run_kernel,
        artifact=artifact,
        classification="inferred_conclusion",
    ):
        current = bind_inferred_resolution_proposal_via_runkernel(
            run_kernel=run_kernel,
            synthesis_key=str(proposal.get("local_target_key") or ""),
            proposal=proposal,
        )
    return current


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
    if current_graph_reconciliation_required(current):
        current = _execute_current_graph_reconciliation(
            run_kernel=run_kernel,
            graph=current,
            role_kwargs=role_kwargs,
        )
        for synthesis_key in current.get(
            "synthesis_topological_order",
            (),
        ):
            node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
            if node.get("status") != "proposed":
                continue
            evaluation_key = f"{synthesis_key}:reconciled:graph-revision:{current['graph_revision']}"
            dprime_artifact = execute_multicomponent_role_call(
                run_kernel=run_kernel,
                role=ROLE_SYNTHESIS_DPRIME,
                input_packet=synthesis_dprime_input_packet(
                    current,
                    synthesis_key=synthesis_key,
                ),
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
            node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
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
    scrutiny_key = f"full-case:selective:graph-revision:{current['graph_revision']}"
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
        node = next(item for item in current["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
        if node.get("status") == "validated" and current.get("scrutineer_status") in {"passed", "passed_with_caveats"}:
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


def _scheduler_work_input_packet(*, run_kernel: Any, work: Mapping[str, Any]) -> dict[str, Any]:
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
        for key, value in _safe_mapping(context.get("component_analyst_input_packets")).items()
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
            run_kernel.state.projections.get(f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}")
        )
        analyst_input = analyst_inputs.get(component_id, {})
        specialist_handoff: dict[str, Any] = {}
        specialist_state = _safe_mapping(run_kernel.state.projections.get("specialist_work_plane"))
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
        graph_raw = _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
        if role == ROLE_CROSS_COMPONENT_ANALYST and not graph_raw:
            accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
            component_refs = [
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
                if _component_requires_direct_work(_safe_mapping(item))
            ]
            admissions_projection = _safe_mapping(
                run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
            )
            admissions = {
                str(_safe_mapping(item).get("component_id") or ""): _safe_mapping(item)
                for item in admissions_projection.get("component_admission_refs") or ()
            }
            if not component_refs or any(
                str(item.get("component_id") or "") not in admissions for item in component_refs
            ):
                packet = {}
            else:
                nodes = [
                    component_work_node_v1_from_admitted_component(
                        run_id=run_kernel.state.run_id,
                        request_id=run_kernel.state.request_id,
                        accepted_component_ref=component_ref,
                        component_admission_ref=admissions[str(component_ref["component_id"])],
                    )
                    for component_ref in component_refs
                ]
                packet = cross_component_input_packet(
                    component_nodes=nodes,
                    accepted_contract_ref=_accepted_contract_ref(accepted),
                    requested_synthesis_directive=str(context.get("requested_synthesis_directive") or ""),
                    component_analyst_input_packets=analyst_inputs,
                    accepted_component_refs=accepted.get("accepted_answer_component_refs") or (),
                    requested_mode=str(context.get("requested_mode") or "Balanced"),
                )
        elif graph_raw:
            graph = validate_component_work_graph_v1(graph_raw)
            if role == ROLE_CROSS_COMPONENT_ANALYST:
                if work.get("output_schema_variant") == SELECTIVE_CROSS_COMPONENT_SCHEMA:
                    closure = validate_selective_recomputation_closure(
                        _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE))
                    )
                    packet = selective_cross_component_input_packet(
                        graph,
                        closure=closure,
                    )
                else:
                    packet = current_graph_reconciliation_input_packet(
                        graph,
                        component_analyst_input_packets=analyst_inputs,
                        requested_mode=str(context.get("requested_mode") or "Balanced"),
                    )
            elif role == ROLE_SYNTHESIS_DPRIME and synthesis_key:
                specialist_handoff = {}
                specialist_state = _safe_mapping(run_kernel.state.projections.get("specialist_work_plane"))
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
        raise OrdinaryMulticomponentRuntimeError("scheduler-selected work packet could not be reconstructed exactly")
    return packet


def _admit_scheduler_validated_synthesis(run_kernel: Any) -> dict[str, Any]:
    """Admit deterministic validated leaves after whole-case scrutiny."""

    graph = _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
    scrutiny_allows_admission = graph.get("scrutineer_required") is not True or graph.get("scrutineer_status") in {
        "passed",
        "passed_with_caveats",
    }
    if not scrutiny_allows_admission:
        return graph
    for synthesis_key in graph.get("synthesis_topological_order") or ():
        node = next(item for item in graph.get("synthesis_nodes") or () if item.get("synthesis_key") == synthesis_key)
        if node.get("status") == "validated":
            graph = admit_synthesis_node_via_runkernel(
                run_kernel=run_kernel,
                synthesis_key=str(synthesis_key),
            )
    return graph


def _finalize_scheduler_graph(*, run_kernel: Any, drive_context: Mapping[str, Any]) -> None:
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
    del final_graph
    run_kernel.complete_multicomponent_graph_scheduler()


def _record_analyst_query_resolution_candidates(
    *,
    run_kernel: Any,
    artifact: Mapping[str, Any],
) -> None:
    """Bind Analyst candidates and publish fail-closed arbitration state."""

    role_artifact = deepcopy(dict(artifact))
    semantic_output = deepcopy(_safe_mapping(role_artifact.get("semantic_output")))
    candidates = [
        deepcopy(_safe_mapping(item))
        for item in semantic_output.get("query_resolution_proposals") or ()
        if isinstance(item, Mapping)
    ]
    if not candidates:
        return
    contract = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    qmr_ref = {
        "question_meaning_record_id": contract.get("parent_question_meaning_record_id"),
        "question_meaning_record_digest": contract.get("parent_question_meaning_record_digest"),
    }
    parent_contract_ref = _safe_mapping(artifact.get("accepted_contract_ref"))
    parent_graph_ref = _safe_mapping(artifact.get("graph_ref"))
    bound = [
        bind_analyst_query_resolution_proposal(
            role_artifact=role_artifact,
            local_candidate=candidate,
            question_meaning_record_ref=qmr_ref,
            parent_contract_ref=parent_contract_ref,
            parent_graph_ref=parent_graph_ref,
        )
        for candidate in candidates
    ]
    projection = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    history = [deepcopy(_safe_mapping(item)) for item in projection.get("proposals") or () if isinstance(item, Mapping)]
    known = {str(item.get("proposal_id") or ""): item for item in history}
    for proposal in bound:
        known.setdefault(str(proposal["proposal_id"]), proposal)
    proposals = sorted(
        known.values(),
        key=lambda item: (
            str(item.get("proposal_digest") or ""),
            str(item.get("proposal_id") or ""),
        ),
    )
    lifecycle_history = [
        _safe_mapping(item) for item in projection.get("proposal_lifecycle_history") or () if isinstance(item, Mapping)
    ]
    latest_status = {str(item.get("proposal_id") or ""): str(item.get("status") or "") for item in lifecycle_history}
    for proposal in proposals:
        proposal_id = str(proposal.get("proposal_id") or "")
        if proposal_id not in latest_status:
            event = _proposal_lifecycle_event(
                proposal=proposal,
                status="pending",
            )
            lifecycle_history.append(event)
            latest_status[proposal_id] = "pending"
    current_contract_ref = _accepted_contract_ref(
        _safe_mapping(run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract)
    )
    for proposal in proposals:
        proposal_id = str(proposal.get("proposal_id") or "")
        if latest_status.get(proposal_id) == "pending" and proposal.get("parent_contract_ref") != current_contract_ref:
            event = _proposal_lifecycle_event(
                proposal=proposal,
                status="superseded_stale",
                reason="parent_contract_is_not_current",
            )
            lifecycle_history.append(event)
            latest_status[proposal_id] = "superseded_stale"
    arbitration_records = []
    scope_groups: dict[str, list[dict[str, Any]]] = {}
    for proposal in proposals:
        if latest_status.get(str(proposal.get("proposal_id") or "")) != ("pending"):
            continue
        scope_key = safe_packet_digest(
            {
                "run_id": proposal.get("run_id"),
                "parent_contract_ref": proposal.get("parent_contract_ref"),
                "parent_graph_ref": proposal.get("parent_graph_ref") or {"graph_absent": True},
                "target_ref_set_digest": proposal.get("target_ref_set_digest"),
            }
        )
        scope_groups.setdefault(scope_key, []).append(proposal)
    for scope_key, group in sorted(scope_groups.items()):
        arbitration = {
            "scope_key": scope_key,
            **arbitrate_analyst_query_resolution_proposals(group),
        }
        arbitration_records.append(arbitration)
        if arbitration.get("status") == "ambiguous_resolution_proposals":
            for proposal in group:
                proposal_id = str(proposal.get("proposal_id") or "")
                event = _proposal_lifecycle_event(
                    proposal=proposal,
                    status="ambiguous",
                    reason="nonidentical_current_proposals_for_exact_scope",
                )
                lifecycle_history.append(event)
                latest_status[proposal_id] = "ambiguous"
    arbitration_history = [
        _safe_mapping(item) for item in projection.get("arbitration_history") or () if isinstance(item, Mapping)
    ]
    known_arbitration_ids = {str(item.get("arbitration_identity") or "") for item in arbitration_history}
    for arbitration in arbitration_records:
        identity = str(arbitration.get("arbitration_identity") or "")
        if identity and identity not in known_arbitration_ids:
            arbitration_history.append(arbitration)
            known_arbitration_ids.add(identity)
    lifecycle_by_proposal = {
        str(item.get("proposal_id") or ""): item for item in lifecycle_history if item.get("proposal_id")
    }
    registry_payload = {
        "schema_version": "analyst_query_resolution_proposal_registry_v2",
        "owner": "RunKernel.AnalystQueryResolutionProposalRegistry",
        "canonical_state": False,
        "proposal_only": True,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "proposals": proposals,
        "proposal_lifecycle_history": lifecycle_history,
        "proposal_lifecycle": lifecycle_by_proposal,
        "arbitrations": arbitration_records,
        "arbitration_history": arbitration_history,
        "ambiguous_resolution_proposals": any(
            item.get("status") == "ambiguous_resolution_proposals" for item in arbitration_records
        ),
        "raw_private_retained": False,
    }
    run_kernel.state.projections[ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY] = deepcopy(registry_payload)


def _proposal_lifecycle_event(
    *,
    proposal: Mapping[str, Any],
    status: str,
    downstream_refs: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    if status not in PROPOSAL_LIFECYCLE_STATUSES:
        raise OrdinaryMulticomponentRuntimeError("query-resolution proposal lifecycle status is invalid")
    core = {
        "schema_version": "analyst_query_resolution_proposal_lifecycle_v1",
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "stable_replay_key": proposal.get("stable_replay_key"),
        "status": status,
        "downstream_refs": _safe_mapping(downstream_refs),
        "reason": _clean_text(reason, limit=240),
        "append_only": True,
    }
    digest = safe_packet_digest(core)
    return {
        **core,
        "lifecycle_event_id": f"aqrp-lifecycle:{digest[:24]}",
        "lifecycle_event_digest": digest,
    }


def _append_proposal_lifecycle_event(
    *,
    run_kernel: Any,
    proposal: Mapping[str, Any],
    status: str,
    downstream_refs: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    registry = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    event = _proposal_lifecycle_event(
        proposal=proposal,
        status=status,
        downstream_refs=downstream_refs,
        reason=reason,
    )
    history = [
        _safe_mapping(item) for item in registry.get("proposal_lifecycle_history") or () if isinstance(item, Mapping)
    ]
    if not any(item.get("lifecycle_event_digest") == event["lifecycle_event_digest"] for item in history):
        history.append(event)
    lifecycle = {str(item.get("proposal_id") or ""): item for item in history if item.get("proposal_id")}
    registry["schema_version"] = "analyst_query_resolution_proposal_registry_v2"
    registry["proposal_lifecycle_history"] = history
    registry["proposal_lifecycle"] = lifecycle
    run_kernel.state.projections[ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY] = registry
    return event


def record_analyst_query_resolution_candidates(
    *,
    run_kernel: Any,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish candidates through the ordinary RunKernel-owned registry."""

    _record_analyst_query_resolution_candidates(
        run_kernel=run_kernel,
        artifact=artifact,
    )
    return _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))


def record_analyst_query_resolution_downstream_refs(
    *,
    run_kernel: Any,
    proposal_ref: Mapping[str, Any],
    downstream_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Append exact downstream lineage for a consumed proposal."""

    registry = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    proposal = next(
        (
            _safe_mapping(item)
            for item in registry.get("proposals") or ()
            if _safe_mapping(item).get("proposal_id") == proposal_ref.get("proposal_id")
            and _safe_mapping(item).get("proposal_digest") == proposal_ref.get("proposal_digest")
        ),
        {},
    )
    if not proposal:
        raise OrdinaryMulticomponentRuntimeError("cannot record downstream refs for an unknown Analyst proposal")
    prior = _safe_mapping(_safe_mapping(registry.get("proposal_lifecycle")).get(str(proposal.get("proposal_id") or "")))
    merged = {
        **_safe_mapping(prior.get("downstream_refs")),
        **_safe_mapping(downstream_refs),
    }
    return _append_proposal_lifecycle_event(
        run_kernel=run_kernel,
        proposal=proposal,
        status="consumed",
        downstream_refs=merged,
    )


def _selected_query_resolution_proposals_for_artifact(
    *,
    run_kernel: Any,
    artifact: Mapping[str, Any],
    classification: str | None = None,
) -> list[dict[str, Any]]:
    registry = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    return selected_proposals_for_role_artifact(
        registry=registry,
        role_artifact=artifact,
        classification=classification,
    )


def _current_pending_searched_premise_proposals(
    *,
    run_kernel: Any,
) -> list[dict[str, Any]]:
    registry = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    lifecycle = _safe_mapping(registry.get("proposal_lifecycle"))
    selected = [
        _safe_mapping(_safe_mapping(item).get("selected_proposal"))
        for item in registry.get("arbitrations") or ()
        if _safe_mapping(item).get("mutation_permitted") is True
        and _safe_mapping(_safe_mapping(item).get("selected_proposal")).get("classification") == "searched_premise"
        and _safe_mapping(
            lifecycle.get(str(_safe_mapping(_safe_mapping(item).get("selected_proposal")).get("proposal_id") or ""))
        ).get("status")
        == "pending"
    ]
    return sorted(
        [item for item in selected if item],
        key=lambda item: (
            str(item.get("proposal_digest") or ""),
            str(item.get("proposal_id") or ""),
        ),
    )


def resolve_next_searched_premise_recovery_posture(
    *,
    run_kernel: Any,
) -> dict[str, Any]:
    """Resolve whether the sole current proposal may become another generation."""

    from core.searchos_existing_gap_recovery_runtime import (
        SearchOSExistingGapRecoveryError,
        validate_searched_premise_generation_prework,
    )

    selected = _current_pending_searched_premise_proposals(run_kernel=run_kernel)
    if not selected:
        return {
            "status": "no_current_pending_searched_premise",
            "lawful_selected_recovery_work_remains": False,
            "proposal_ref": {},
        }
    if len(selected) != 1:
        raise OrdinaryMulticomponentRuntimeError(
            "ambiguous_resolution_proposals: one recovery generation cannot "
            "mechanically select among multiple searched-premise proposals"
        )
    proposal = selected[0]
    depth = int(
        _safe_mapping(_safe_mapping(proposal.get("variant_payload")).get("recovery_generation")).get("depth") or 0
    )
    try:
        eligibility = validate_searched_premise_generation_prework(
            run_kernel.state.searchos_state,
            generation_depth=depth,
        )
    except SearchOSExistingGapRecoveryError as exc:
        _append_proposal_lifecycle_event(
            run_kernel=run_kernel,
            proposal=proposal,
            status="rejected",
            reason=str(exc),
        )
        return {
            "status": "rejected_before_amendment_mutation_or_work",
            "lawful_selected_recovery_work_remains": False,
            "proposal_ref": {
                "proposal_id": proposal.get("proposal_id"),
                "proposal_digest": proposal.get("proposal_digest"),
                "stable_replay_key": proposal.get("stable_replay_key"),
            },
            "reason": str(exc),
        }
    return {
        "status": "current_pending_generation_eligible",
        "lawful_selected_recovery_work_remains": True,
        "proposal_ref": {
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "stable_replay_key": proposal.get("stable_replay_key"),
        },
        "eligibility": eligibility,
    }


def authorize_searched_premise_recovery_from_analyst_proposals(
    *,
    run_kernel: Any,
    requested_mode: str,
    proposal_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Atomically amend for one selected searched premise and admit its cycle."""

    from core.acquisition_control import (
        build_pre_acquisition_source_obligation_ref,
    )
    from core.contract_amendment_record import (
        build_contract_amendment_v2_from_analyst_proposal,
    )
    from core.run_kernel import Observation, RunStageStatus

    registry = _safe_mapping(run_kernel.state.projections.get(ANALYST_QUERY_RESOLUTION_PROPOSAL_TRACE_KEY))
    lifecycle = _safe_mapping(registry.get("proposal_lifecycle"))
    requested_proposal_ref = _safe_mapping(proposal_ref)
    if requested_proposal_ref:
        requested = next(
            (
                _safe_mapping(item)
                for item in registry.get("proposals") or ()
                if _safe_mapping(item).get("proposal_id") == requested_proposal_ref.get("proposal_id")
                and _safe_mapping(item).get("proposal_digest") == requested_proposal_ref.get("proposal_digest")
            ),
            {},
        )
        if not requested:
            raise OrdinaryMulticomponentRuntimeError("requested searched-premise proposal replay is unknown")
        prior_lifecycle = _safe_mapping(lifecycle.get(str(requested.get("proposal_id") or "")))
        if prior_lifecycle.get("status") in {
            "consumed",
            "exact_replay",
        }:
            downstream_refs = _safe_mapping(prior_lifecycle.get("downstream_refs"))
            amendment_replay = _safe_mapping(
                run_kernel.contract_amendment_replay_for_analyst_proposal(
                    proposal_ref={
                        key: requested.get(key)
                        for key in (
                            "proposal_id",
                            "proposal_digest",
                            "stable_replay_key",
                        )
                    }
                )
            )
            _append_proposal_lifecycle_event(
                run_kernel=run_kernel,
                proposal=requested,
                status="exact_replay",
                downstream_refs=downstream_refs,
            )
            return {
                "status": "exact_replay",
                "work_authorized": False,
                "proposal": requested,
                "downstream_refs": downstream_refs,
                **amendment_replay,
                **downstream_refs,
            }
        if prior_lifecycle.get("status") != "pending":
            raise OrdinaryMulticomponentRuntimeError("requested searched-premise proposal is not executable")
    selected = _current_pending_searched_premise_proposals(run_kernel=run_kernel)
    if requested_proposal_ref:
        selected = [
            item
            for item in selected
            if item.get("proposal_id") == requested_proposal_ref.get("proposal_id")
            and item.get("proposal_digest") == requested_proposal_ref.get("proposal_digest")
        ]
    if not selected:
        consumed = [
            _safe_mapping(item)
            for item in registry.get("proposals") or ()
            if _safe_mapping(item).get("classification") == "searched_premise"
            and _safe_mapping(lifecycle.get(str(_safe_mapping(item).get("proposal_id") or ""))).get("status")
            in {"consumed", "exact_replay"}
        ]
        if len(consumed) == 1:
            prior = _safe_mapping(lifecycle.get(str(consumed[0].get("proposal_id") or "")))
            downstream_refs = _safe_mapping(prior.get("downstream_refs"))
            amendment_replay = _safe_mapping(
                run_kernel.contract_amendment_replay_for_analyst_proposal(
                    proposal_ref={
                        key: consumed[0].get(key)
                        for key in (
                            "proposal_id",
                            "proposal_digest",
                            "stable_replay_key",
                        )
                    }
                )
            )
            _append_proposal_lifecycle_event(
                run_kernel=run_kernel,
                proposal=consumed[0],
                status="exact_replay",
                downstream_refs=downstream_refs,
            )
            return {
                **amendment_replay,
                "proposal": consumed[0],
            }
        return {
            "status": "no_selected_searched_premise",
            "work_authorized": False,
        }
    if len(selected) != 1:
        raise OrdinaryMulticomponentRuntimeError(
            "ambiguous_resolution_proposals: one recovery generation cannot "
            "mechanically select among multiple searched-premise proposals"
        )
    proposal = selected[0]
    replay = run_kernel.contract_amendment_replay_for_analyst_proposal(
        proposal_ref={
            key: proposal.get(key)
            for key in (
                "proposal_id",
                "proposal_digest",
                "stable_replay_key",
            )
        }
    )
    if replay:
        downstream_refs = _safe_mapping(replay.get("downstream_refs") or replay)
        _append_proposal_lifecycle_event(
            run_kernel=run_kernel,
            proposal=proposal,
            status="exact_replay",
            downstream_refs=downstream_refs,
        )
        return {
            **replay,
            "proposal": proposal,
        }
    from core.searchos_existing_gap_recovery_runtime import (
        SearchOSExistingGapRecoveryError,
        validate_searched_premise_generation_prework,
    )

    generation_depth = int(
        _safe_mapping(_safe_mapping(proposal.get("variant_payload")).get("recovery_generation")).get("depth") or 0
    )
    try:
        validate_searched_premise_generation_prework(
            run_kernel.state.searchos_state,
            generation_depth=generation_depth,
        )
    except SearchOSExistingGapRecoveryError as exc:
        _append_proposal_lifecycle_event(
            run_kernel=run_kernel,
            proposal=proposal,
            status="rejected",
            reason=str(exc),
        )
        return {
            "status": "rejected_before_amendment_mutation_or_work",
            "work_authorized": False,
            "proposal": proposal,
            "reason": str(exc),
        }
    current_contract = _safe_mapping(
        run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    )
    source_graph = _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
    proposal_artifact_ref = _safe_mapping(proposal.get("role_artifact_ref"))
    graph_created_by_proposal_artifact = any(
        _safe_mapping(_safe_mapping(item).get("proposal_ref")).get("cross_component_analyst_ref", {}).get("artifact_id")
        == proposal_artifact_ref.get("artifact_id")
        and _safe_mapping(_safe_mapping(item).get("proposal_ref"))
        .get("cross_component_analyst_ref", {})
        .get("artifact_digest")
        == proposal_artifact_ref.get("artifact_digest")
        for item in source_graph.get("synthesis_nodes") or ()
        if isinstance(item, Mapping)
    )
    graph_advanced_by_proposal_artifact = _safe_mapping(source_graph.get("selective_cross_component_analyst_ref")).get(
        "artifact_id"
    ) == proposal_artifact_ref.get("artifact_id") and _safe_mapping(
        source_graph.get("selective_cross_component_analyst_ref")
    ).get("artifact_digest") == proposal_artifact_ref.get("artifact_digest")
    recorded_parent_graph_ref = _safe_mapping(proposal.get("parent_graph_ref"))
    current_source_graph_ref = {
        "graph_id": source_graph.get("graph_id"),
        "graph_revision": source_graph.get("graph_revision"),
        "graph_digest": source_graph.get("graph_digest"),
        "run_id": source_graph.get("run_id"),
        "request_id": source_graph.get("request_id"),
    }
    if (
        not current_contract
        or not source_graph
        or proposal.get("parent_contract_ref") != _accepted_contract_ref(current_contract)
        or not (
            recorded_parent_graph_ref == current_source_graph_ref
            or (
                proposal.get("parent_graph_explicitly_absent") is True
                and not recorded_parent_graph_ref
                and graph_created_by_proposal_artifact
            )
            or graph_advanced_by_proposal_artifact
        )
    ):
        raise OrdinaryMulticomponentRuntimeError(
            "selected searched-premise proposal is stale against current contract or graph"
        )
    variant = _safe_mapping(proposal.get("variant_payload"))
    proposal_digest = str(proposal.get("proposal_digest") or "")
    component_id = f"component:searched-premise:{proposal_digest[:16]}"
    record = build_contract_amendment_v2_from_analyst_proposal(
        proposal=proposal,
        current_contract=current_contract,
        new_component_spec={
            "component_id": component_id,
        },
        request_digest=safe_packet_digest(
            {
                "run_id": run_kernel.state.run_id,
                "request_id": run_kernel.state.request_id,
                "proposal_digest": proposal_digest,
            }
        ),
        requested_mode=requested_mode,
    )
    record_payload = record.to_dict()
    admission_action = run_kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        parent_contract_digest=record.parent_contract_digest,
        parent_contract_version=record.parent_contract_version,
        inputs={
            "analyst_query_resolution_proposal_ref": {
                "proposal_id": proposal.get("proposal_id"),
                "proposal_digest": proposal_digest,
                "stable_replay_key": proposal.get("stable_replay_key"),
            },
            "requested_mode": requested_mode,
        },
    )
    if isinstance(admission_action, Mapping):
        amendment_admission = _safe_mapping(admission_action.get("contract_amendment_admission"))
    else:
        run_kernel.reduce(
            Observation.from_action(
                admission_action,
                observation_type=admission_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"contract_amendment_record": record_payload},
            )
        )
        amendment_admission = _safe_mapping(run_kernel.state.contract_amendment_admission_projection)
    application_action = run_kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(amendment_admission["admission_digest"]),
        parent_contract_digest=record.parent_contract_digest,
        parent_contract_version=record.parent_contract_version,
        inputs={"requested_mode": requested_mode},
    )
    if isinstance(application_action, Mapping):
        amendment_application = _safe_mapping(application_action.get("contract_amendment_application"))
    else:
        run_kernel.reduce(
            Observation.from_action(
                application_action,
                observation_type=application_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        amendment_application = _safe_mapping(run_kernel.state.contract_amendment_application_projection)
    amended_contract = _safe_mapping(run_kernel.state.current_answer_contract)
    component_ref = next(
        (
            _safe_mapping(item)
            for item in amended_contract.get("accepted_answer_component_refs") or ()
            if _safe_mapping(item).get("component_id") == component_id
        ),
        {},
    )
    if not component_ref:
        raise OrdinaryMulticomponentRuntimeError("searched-premise amendment did not atomically add its component")
    target_ids = {
        str(_safe_mapping(item).get("component_id") or "") for item in variant.get("answer_target_refs") or ()
    }
    target_refs = sorted(
        [
            _safe_mapping(item)
            for item in amended_contract.get("accepted_answer_component_refs") or ()
            if str(_safe_mapping(item).get("component_id") or "") in target_ids
        ],
        key=safe_packet_digest,
    )
    source_candidate_id = str(component_ref.get("source_obligation_candidate_ids", [""])[0])
    obligation_specification = _safe_mapping(variant.get("source_obligation_specification"))
    source_obligation_ref = build_pre_acquisition_source_obligation_ref(
        answer_contract_ref={
            "source": "current_answer_contract",
            "contract_version": amended_contract.get("accepted_contract_version"),
            "contract_digest": amended_contract.get("accepted_contract_digest"),
        },
        source_obligation_id=source_candidate_id,
        source_obligation_descriptor={
            "obligation_id": source_candidate_id,
            "kind": str(obligation_specification["obligation_kind"]),
            "strictness": str(obligation_specification["strictness"]),
        },
        component_refs=[
            {
                key: component_ref.get(key)
                for key in (
                    "component_id",
                    "component_revision",
                    "component_digest",
                )
            }
        ],
    )
    lease = run_kernel.ensure_searchos_whole_run_recovery_lease()
    del lease
    searchos_parent_state_ref = {
        "state_id": run_kernel.state.searchos_state.get("state_id"),
        "state_digest": run_kernel.state.searchos_state.get("state_digest"),
    }
    terminal_history = [
        _safe_mapping(item) for item in run_kernel.state.searchos_state.get("recovery_cycle_terminal_history") or ()
    ]
    generation_parent_ref = searchos_parent_state_ref
    if generation_depth > 1:
        prior = terminal_history[-1] if terminal_history else {}
        generation_parent_ref = {
            key: prior.get(key)
            for key in (
                "schema_version",
                "cycle_id",
                "cycle_terminal_id",
                "cycle_terminal_digest",
                "terminal_status",
            )
        }
    record_ref = {
        "amendment_record_id": record.amendment_record_id,
        "amendment_record_digest": record.record_digest,
    }
    admission_ref = {
        key: amendment_admission.get(key)
        for key in (
            "amendment_record_id",
            "amendment_record_digest",
            "authorized_action_id",
            "admission_digest",
        )
    }
    application_ref = {
        key: amendment_application.get(key)
        for key in (
            "amendment_record_id",
            "authorized_action_id",
            "application_digest",
        )
    }
    cycle_result = run_kernel.authorize_searchos_recovery_admission(
        stable_replay_key=str(proposal.get("stable_replay_key") or ""),
        recovery_classification="searched_premise",
        proposal_ref={
            key: proposal.get(key)
            for key in (
                "schema_version",
                "proposal_id",
                "proposal_digest",
                "stable_replay_key",
                "classification",
            )
        },
        current_contract_ref=_accepted_contract_ref(amended_contract),
        current_graph_ref={
            "graph_id": source_graph.get("graph_id"),
            "graph_revision": source_graph.get("graph_revision"),
            "graph_digest": source_graph.get("graph_digest"),
        },
        component_ref=component_ref,
        source_obligation_ref=source_obligation_ref,
        answer_target_refs=target_refs,
        dependency_component_refs=[
            _safe_mapping(item) for item in variant.get("current_dependency_component_refs") or ()
        ],
        generation_parent_ref=generation_parent_ref,
        generation_depth=generation_depth,
        contract_amendment_record_ref=record_ref,
        contract_amendment_admission_ref=admission_ref,
        contract_amendment_application_ref=application_ref,
        expected_parent_state_ref=searchos_parent_state_ref,
    )
    if isinstance(cycle_result, Mapping):
        cycle_admission = _safe_mapping(cycle_result)
    else:
        run_kernel.reduce(
            Observation.from_action(
                cycle_result,
                observation_type=cycle_result.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload=cycle_result.inputs["recovery_admission_observation"],
            )
        )
        cycle_admission = _safe_mapping(run_kernel.state.projections["searchos_recovery_cycle_admission"])
    result = {
        **cycle_admission,
        "proposal": proposal,
        "component_ref": component_ref,
        "source_graph_ref": {
            "graph_id": source_graph.get("graph_id"),
            "graph_revision": source_graph.get("graph_revision"),
            "graph_digest": source_graph.get("graph_digest"),
        },
        "contract_amendment_record_ref": record_ref,
        "contract_amendment_admission_ref": admission_ref,
        "contract_amendment_application_ref": application_ref,
    }
    downstream_refs = {
        "contract_amendment_record_ref": record_ref,
        "contract_amendment_admission_ref": admission_ref,
        "contract_amendment_application_ref": application_ref,
        "answer_contract_ref": _accepted_contract_ref(amended_contract),
        "searchos_cycle_admission_ref": _safe_mapping(cycle_admission.get("cycle_admission_ref")),
        "searchos_recovery_slot_ref": _safe_mapping(cycle_admission.get("recovery_slot_ref")),
    }
    _append_proposal_lifecycle_event(
        run_kernel=run_kernel,
        proposal=proposal,
        status="consumed",
        downstream_refs=downstream_refs,
    )
    return result


def execute_searchos_recovery_graph_reproof_from_scope(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    component_admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Advance the same Graph V1 identity through exact selective reproof."""

    from core.component_work_graph_v1 import (
        validate_component_work_graph_v1,
    )
    from core.run_kernel import (
        contract_amendment_graph_transition_authority,
    )

    source_graph = validate_component_work_graph_v1(
        _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
    )
    current_contract = _safe_mapping(run_kernel.state.current_answer_contract)
    current_contract_ref = _accepted_contract_ref(current_contract)
    amendment_admission = _safe_mapping(run_kernel.state.contract_amendment_admission_projection)
    amendment_application = _safe_mapping(run_kernel.state.contract_amendment_application_projection)
    graph_transition_authority = contract_amendment_graph_transition_authority(
        graph=source_graph,
        amendment_application=amendment_application,
        amendment_admission=amendment_admission,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
    )
    admission_ref = {
        key: amendment_admission.get(key)
        for key in (
            "amendment_record_id",
            "amendment_record_digest",
            "authorized_action_id",
            "admission_digest",
        )
    }
    application_ref = {
        key: amendment_application.get(key)
        for key in (
            "amendment_record_id",
            "authorized_action_id",
            "application_digest",
        )
    }
    recovered_admission = _safe_mapping(component_admission_ref)
    closure_candidate = derive_selective_recomputation_closure(
        source_graph,
        recovery_authorization_ref=graph_transition_authority,
        current_contract_ref=current_contract_ref,
        contract_amendment_admission_ref=admission_ref,
        contract_amendment_application_ref=application_ref,
        recovered_component_admission_ref=recovered_admission,
    )
    closure = reduce_selective_recomputation_closure(
        run_kernel=run_kernel,
        closure_candidate=closure_candidate,
    )
    component_id = str(recovered_admission.get("component_id") or "")
    component_ref = next(
        _safe_mapping(item)
        for item in current_contract.get("accepted_answer_component_refs") or ()
        if _safe_mapping(item).get("component_id") == component_id
    )
    recovered_node = component_work_node_v1_from_admitted_component(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_component_ref=component_ref,
        component_admission_ref=recovered_admission,
    )
    invalidated = reduce_selective_invalidation_via_runkernel(
        run_kernel=run_kernel,
        graph=source_graph,
        closure=closure,
        recovered_component_node=recovered_node,
        current_contract_ref=current_contract_ref,
        recovery_authorization_ref=graph_transition_authority,
        contract_amendment_admission_ref=admission_ref,
        amendment_application_ref=application_ref,
        accepted_component_refs=current_contract.get("accepted_answer_component_refs") or (),
    )
    return _execute_selective_resynthesis(
        run_kernel=run_kernel,
        graph=invalidated,
        closure=closure,
        role_kwargs=_role_runtime_kwargs(runtime_scope),
    )


def _consume_scheduler_selected_artifact(
    *,
    run_kernel: Any,
    work: Mapping[str, Any],
    artifact: Mapping[str, Any],
    input_packet: Mapping[str, Any],
    specialist_need_proposal_present: bool,
    specialist_need_proposal_candidate: Mapping[str, Any] | None,
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
        _record_analyst_query_resolution_candidates(
            run_kernel=run_kernel,
            artifact=artifact,
        )
        if specialist_need_proposal_present:
            accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
            component_ref = next(
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
                if _safe_mapping(item).get("component_id") == component_id
            )
            deps = drive_context["runtime_scope"].get("deps")
            run_kernel.bind_specialist_need_from_role_artifact(
                role_artifact=artifact,
                proposal_candidate=_safe_mapping(specialist_need_proposal_candidate),
                role_input_packet=input_packet,
                canonical_target_ref={
                    "target_kind": "component",
                    "target_key": component_id,
                    "target_revision": component_ref.get("component_revision"),
                    "target_digest": component_ref.get("component_digest"),
                },
                specialist_capability_registry=getattr(deps, "specialist_capability_registry", None),
                specialist_execution_policy=getattr(deps, "specialist_execution_policy", None),
            )
        return
    if role == ROLE_COMPONENT_DPRIME and component_id:
        accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
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
            run_kernel.state.projections.get(f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}")
        )
        specialist_handoff: dict[str, Any] = {}
        specialist_state = _safe_mapping(run_kernel.state.projections.get("specialist_work_plane"))
        if specialist_state:
            from core.multicomponent_role_runtime import role_artifact_ref
            from core.specialist_graph_runtime import handoff_for_target

            specialist_handoff = handoff_for_target(
                specialist_state,
                target_kind="component",
                target_key=component_id,
            )
            if specialist_handoff:
                specialist_state = run_kernel.consume_specialist_handoff_by_dprime(
                    handoff_id=str(specialist_handoff.get("handoff_id") or ""),
                    dprime_artifact_ref=role_artifact_ref(artifact),
                )
                consumed_handoff = handoff_for_target(
                    specialist_state,
                    target_kind="component",
                    target_key=component_id,
                    include_consumed=True,
                )
                if not consumed_handoff:
                    raise OrdinaryMulticomponentRuntimeError(
                        "component D-prime consumption lost the Specialist handoff"
                    )
                specialist_handoff = consumed_handoff
        bindable = drive_context["selected_bindables"].get(component_id)
        if bindable is None:
            raise OrdinaryMulticomponentRuntimeError("scheduler-selected component lost its evidence binding")
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
            allow_searchos_semantic_requirement_historical_gap_exception=(
                _safe_mapping(bindable.passage).get("material_authority") == "read_custody_material"
                and _safe_mapping(bindable.passage).get("_provider") == "searchos_read_custody"
            ),
        )
        if work.get("recovery_authorization_ref"):
            if component_admission_ref.get("admission_status") not in {
                "admitted",
                "admitted_with_caveats",
            }:
                raise _ScheduledSemanticWorkBlocked("recovered component did not pass typed admission")
            source_graph = validate_component_work_graph_v1(_safe_mapping(drive_context.get("recovery_graph")))
            recovered_node = component_work_node_v1_from_admitted_component(
                run_id=run_kernel.state.run_id,
                request_id=run_kernel.state.request_id,
                accepted_component_ref=component_ref,
                component_admission_ref=component_admission_ref,
            )
            current_contract_ref = _accepted_contract_ref(run_kernel.state.current_answer_contract)
            closure_candidate = derive_selective_recomputation_closure(
                source_graph,
                recovery_authorization_ref=drive_context["recovery_authorization_ref"],
                current_contract_ref=current_contract_ref,
                contract_amendment_admission_ref=drive_context["contract_amendment_admission_ref"],
                contract_amendment_application_ref=drive_context["contract_amendment_application_ref"],
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
                recovery_authorization_ref=drive_context["recovery_authorization_ref"],
                contract_amendment_admission_ref=drive_context["contract_amendment_admission_ref"],
                amendment_application_ref=drive_context["contract_amendment_application_ref"],
                accepted_component_refs=(
                    _safe_mapping(run_kernel.state.current_answer_contract).get("accepted_answer_component_refs") or ()
                ),
            )
        return
    if role == ROLE_CROSS_COMPONENT_ANALYST:
        _record_analyst_query_resolution_candidates(
            run_kernel=run_kernel,
            artifact=artifact,
        )
        graph_raw = _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
        if not graph_raw:
            from core.multicomponent_component_admission import (
                MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
            )

            packet = _safe_mapping(input_packet)
            accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
            component_refs = [
                _safe_mapping(item)
                for item in accepted.get("accepted_answer_component_refs") or ()
                if _component_requires_direct_work(_safe_mapping(item))
            ]
            admissions = {
                str(_safe_mapping(item).get("component_id") or ""): _safe_mapping(item)
                for item in _safe_mapping(
                    run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
                ).get("component_admission_refs")
                or ()
            }
            component_nodes = [
                component_work_node_v1_from_admitted_component(
                    run_id=run_kernel.state.run_id,
                    request_id=run_kernel.state.request_id,
                    accepted_component_ref=component_ref,
                    component_admission_ref=admissions[str(component_ref["component_id"])],
                )
                for component_ref in component_refs
            ]
            candidate = component_work_graph_v1_from_cross_component_artifact(
                run_id=run_kernel.state.run_id,
                request_id=run_kernel.state.request_id,
                accepted_contract_ref=_safe_mapping(packet.get("accepted_contract_ref")),
                requested_synthesis_directive=str(packet.get("requested_synthesis_directive") or ""),
                component_nodes=component_nodes,
                cross_component_artifact=artifact,
                component_analyst_input_packets=_safe_mapping(drive_context.get("component_analyst_input_packets")),
                transient_cross_input_packet=packet,
                additional_scrutineer_trigger_reasons=tuple(
                    drive_context.get("additional_scrutineer_trigger_reasons") or ()
                ),
                accepted_component_refs=accepted.get("accepted_answer_component_refs") or (),
                requested_mode=str(
                    _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get("requested_mode") or "Balanced"
                ),
                inferred_resolution_proposals=(
                    _selected_query_resolution_proposals_for_artifact(
                        run_kernel=run_kernel,
                        artifact=artifact,
                        classification="inferred_conclusion",
                    )
                ),
            )
            reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="structure",
                graph_candidate=candidate,
            )
            if specialist_need_proposal_present:
                target = _safe_mapping(_safe_mapping(specialist_need_proposal_candidate).get("target"))
                graph = validate_component_work_graph_v1(
                    _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
                )
                node = next(
                    (
                        _safe_mapping(item)
                        for item in graph.get("synthesis_nodes") or ()
                        if _safe_mapping(item).get("synthesis_key") == target.get("target_key")
                    ),
                    {},
                )
                deps = drive_context["runtime_scope"].get("deps")
                run_kernel.bind_specialist_need_from_role_artifact(
                    role_artifact=artifact,
                    proposal_candidate=_safe_mapping(specialist_need_proposal_candidate),
                    role_input_packet=input_packet,
                    canonical_target_ref={
                        "target_kind": "synthesis",
                        "target_key": (node.get("synthesis_key") or "unsupported-cross-component-target"),
                        "target_revision": node.get("node_revision"),
                        "target_digest": node.get("node_digest"),
                    },
                    specialist_capability_registry=getattr(deps, "specialist_capability_registry", None),
                    specialist_execution_policy=getattr(deps, "specialist_execution_policy", None),
                )
        elif work.get("output_schema_variant") == SELECTIVE_CROSS_COMPONENT_SCHEMA:
            graph = validate_component_work_graph_v1(graph_raw)
            closure = validate_selective_recomputation_closure(
                _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE))
            )
            candidate = component_work_graph_v1_selective_resynthesis_from_cross_artifact(
                graph,
                closure=closure,
                cross_component_artifact=artifact,
            )
            reduce_component_work_graph_v1(
                run_kernel=run_kernel,
                operation="selective_resynthesis_structure",
                graph_candidate=candidate,
                role_evaluation_key=evaluation_key,
            )
        elif evaluation_key.startswith("current-graph-reconciliation:"):
            for proposal in _selected_query_resolution_proposals_for_artifact(
                run_kernel=run_kernel,
                artifact=artifact,
                classification="inferred_conclusion",
            ):
                bind_inferred_resolution_proposal_via_runkernel(
                    run_kernel=run_kernel,
                    synthesis_key=str(proposal.get("local_target_key") or ""),
                    proposal=proposal,
                )
        else:
            graph = validate_component_work_graph_v1(graph_raw)
            component_packets = _safe_mapping(
                _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get("component_analyst_input_packets")
            )
            candidate = component_work_graph_v1_resynthesis_from_cross_component_artifact(
                graph,
                accepted_contract_ref=_accepted_contract_ref(run_kernel.state.current_answer_contract),
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
        specialist_state = _safe_mapping(run_kernel.state.projections.get("specialist_work_plane"))
        if specialist_state:
            from core.multicomponent_role_runtime import role_artifact_ref
            from core.specialist_graph_runtime import handoff_for_target

            specialist_handoff = handoff_for_target(
                specialist_state,
                target_kind="synthesis",
                target_key=synthesis_key,
            )
            if specialist_handoff:
                specialist_state = run_kernel.consume_specialist_handoff_by_dprime(
                    handoff_id=str(specialist_handoff.get("handoff_id") or ""),
                    dprime_artifact_ref=role_artifact_ref(artifact),
                )
                consumed_handoff = handoff_for_target(
                    specialist_state,
                    target_kind="synthesis",
                    target_key=synthesis_key,
                    include_consumed=True,
                )
                if not consumed_handoff:
                    raise OrdinaryMulticomponentRuntimeError(
                        "synthesis D-prime consumption lost the Specialist handoff"
                    )
                specialist_handoff = consumed_handoff
        graph = validate_component_work_graph_v1(
            _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
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
        node = next(item for item in graph["synthesis_nodes"] if item["synthesis_key"] == synthesis_key)
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
            _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
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
        if specialist_need_proposal_present:
            target = _safe_mapping(_safe_mapping(specialist_need_proposal_candidate).get("target"))
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
                    _safe_mapping(ref).get("node_id") == target_node.get("node_id")
                    for ref in _safe_mapping(item).get("input_node_refs") or ()
                )
            ]
            leaf_authorized = target_kind == "synthesis" and bool(target_node) and not descendants
            deps = drive_context["runtime_scope"].get("deps")
            run_kernel.bind_specialist_need_from_role_artifact(
                role_artifact=artifact,
                proposal_candidate=_safe_mapping(specialist_need_proposal_candidate),
                role_input_packet=input_packet,
                canonical_target_ref={
                    "target_kind": target_kind,
                    "target_key": target_key,
                    "target_revision": target_node.get("node_revision"),
                    "target_digest": target_node.get("node_digest"),
                },
                specialist_capability_registry=getattr(deps, "specialist_capability_registry", None),
                specialist_execution_policy=getattr(deps, "specialist_execution_policy", None),
                scrutineer_leaf_target_authorized=leaf_authorized,
            )
            if leaf_authorized:
                return
        _finalize_scheduler_graph(
            run_kernel=run_kernel,
            drive_context=drive_context,
        )
        return
    raise OrdinaryMulticomponentRuntimeError("scheduler selected unsupported semantic work descriptor")


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
        ((action, result) for action, result in zip(actions, results, strict=True) if result is not None),
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
        raise _ScheduledSemanticWorkBlocked("required semantic work denied by the compatibility envelope")
    scheduler = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    leases_by_id = {
        str(_safe_mapping(item).get("lease_id") or ""): _safe_mapping(item)
        for item in scheduler.get("lease_history") or ()
    }
    leases = [
        leases_by_id[str(_safe_mapping(ref).get("lease_id") or "")] for ref in batch.get("ordered_lease_refs") or ()
    ]
    works = [_safe_mapping(lease.get("work")) for lease in leases]
    try:
        packets = [_scheduler_work_input_packet(run_kernel=run_kernel, work=work) for work in works]
    except Exception as exc:
        run_kernel.cancel_multicomponent_work_batch(
            batch_id=str(batch.get("batch_id") or ""),
            reason="exact_batch_packet_reconstruction_failed",
        )
        if len(works) == 1 and works[0].get("work_kind") == "specialist_capability":
            proposal_posture = _safe_mapping(works[0].get("specialist_proposal_ref")).get("posture")
            run_kernel.dispose_failed_specialist_reconstruction(work=works[0])
            if proposal_posture == "optional":
                return
            current = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
            if proposal_posture == "required" and current.get("status") == "blocked_required_specialist_work":
                raise _ScheduledSemanticWorkBlocked(
                    "required Specialist input reconstruction failed before dispatch"
                ) from exc
            raise OrdinaryMulticomponentRuntimeError(
                "required Specialist reconstruction failure did not reach its scheduler blocked terminal"
            ) from exc
        raise
    from core.specialist_graph_runtime import specialist_digest

    packet_digests = [
        (specialist_digest(packet) if work.get("work_kind") == "specialist_capability" else safe_packet_digest(packet))
        for work, packet in zip(works, packets, strict=True)
    ]
    actions = run_kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=packet_digests,
    )
    if works and works[0].get("work_kind") == "specialist_capability":
        if len(works) != 1 or len(actions) != 1:
            raise OrdinaryMulticomponentRuntimeError("Specialist execution must remain serial width one")
        from core.specialist_graph_runtime import (
            SpecialistCapabilityRegistry,
            build_specialist_terminal_result,
            execute_specialist_capability,
        )

        deps = _safe_mapping(drive_context.get("runtime_scope")).get("deps")
        registry = getattr(deps, "specialist_capability_registry", None)
        if not isinstance(registry, SpecialistCapabilityRegistry):
            raise OrdinaryMulticomponentRuntimeError("Specialist execution lost its injected registry")
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
            plane = _safe_mapping(run_kernel.state.projections.get("specialist_work_plane"))
            proposal_id = _safe_mapping(result.get("proposal_ref")).get("proposal_id")
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
                    _safe_mapping(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
                )
                remediated = graph_with_specialist_leaf_remediation(
                    graph,
                    specialist_result_artifact=result,
                )
                reduce_component_work_graph_v1(
                    run_kernel=run_kernel,
                    operation="specialist_remediation",
                    synthesis_key=str(_safe_mapping(result.get("canonical_target_ref")).get("target_key") or ""),
                    graph_candidate=remediated,
                )
        current = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
        if str(current.get("status") or "").startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked("required scheduled Specialist work did not complete")
        return
    try:
        prepared_calls = [
            prepare_multicomponent_transport_call(
                action=action,
                input_packet=packet,
                **{
                    **dict(role_kwargs),
                    "provider": str(scheduler.get("configured_provider_class") or role_kwargs.get("provider") or ""),
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
        raise _ScheduledSemanticWorkBlocked("committed batch transport preparation failed") from exc

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

    results: list[SafeMulticomponentWorkerResult | None] = [None for _ in prepared_calls]
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
                    except RunCapExceeded:
                        raise
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
        raise OrdinaryMulticomponentRuntimeError("committed batch did not produce one safe outcome per child")
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
    for work, artifact, input_packet, result in zip(works, artifacts, packets, results, strict=True):
        if artifact is not None:
            assert result is not None
            try:
                _consume_scheduler_selected_artifact(
                    run_kernel=run_kernel,
                    work=work,
                    artifact=artifact,
                    input_packet=input_packet,
                    specialist_need_proposal_present=(result.specialist_need_proposal_present),
                    specialist_need_proposal_candidate=(result.specialist_need_proposal_candidate),
                    drive_context=drive_context,
                )
            except Exception:
                raise
    current = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
    if str(current.get("status") or "").startswith("blocked_"):
        raise _ScheduledSemanticWorkBlocked("required scheduled semantic work did not complete")


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
            str(key): _safe_mapping(value) for key, value in component_analyst_input_packets.items()
        },
        "query": query,
        "cost_recorded_child_action_ids": set(),
        "additional_scrutineer_trigger_reasons": (
            *(("deep_mode",) if mode.casefold() == "deep" else ()),
            *(
                ("high_stakes_quantitative_posture",)
                if _safe_mapping(runtime_scope.get("economist_safety_telemetry")).get("high_stakes_quant_detected")
                is True
                else ()
            ),
        ),
    }
    role_kwargs = _role_runtime_kwargs(runtime_scope)
    while True:
        scheduler = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
        status = str(scheduler.get("status") or "")
        if status == "completed":
            return
        if status.startswith("blocked_"):
            raise _ScheduledSemanticWorkBlocked("required scheduled semantic work did not complete")
        run_kernel.dispose_exhausted_optional_specialist_proposals()
        ready = run_kernel.derive_current_multicomponent_ready_work()
        if not ready:
            if not run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE):
                accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
                component_refs = [
                    _safe_mapping(item)
                    for item in accepted.get("accepted_answer_component_refs") or ()
                    if isinstance(item, Mapping) and _component_requires_direct_work(_safe_mapping(item))
                ]
                if len(component_refs) == 1 and len(accepted.get("accepted_answer_component_refs") or ()) == 1:
                    from core.component_work_graph_v1 import (
                        component_work_graph_v1_from_single_component_admission,
                    )
                    from core.component_work_node import (
                        component_work_node_v1_from_admitted_component,
                    )
                    from core.multicomponent_component_admission import (
                        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
                    )

                    aggregate = _safe_mapping(
                        run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
                    )
                    admissions = [
                        _safe_mapping(item)
                        for item in aggregate.get("component_admission_refs") or ()
                        if isinstance(item, Mapping)
                    ]
                    if len(admissions) != 1:
                        raise OrdinaryMulticomponentRuntimeError("N=1 receiver lacks its canonical component admission")
                    if admissions[0].get("admission_status") not in {
                        "admitted",
                        "admitted_with_caveats",
                    }:
                        raise _ScheduledSemanticWorkBlocked(
                            "N=1 existing component completed analysis without admitted support"
                        )
                    component_node = component_work_node_v1_from_admitted_component(
                        run_id=run_kernel.state.run_id,
                        request_id=run_kernel.state.request_id,
                        accepted_component_ref=component_refs[0],
                        component_admission_ref=admissions[0],
                    )
                    single_graph = component_work_graph_v1_from_single_component_admission(
                        run_id=run_kernel.state.run_id,
                        request_id=run_kernel.state.request_id,
                        accepted_contract_ref={
                            "owner": accepted.get("owner"),
                            "canonical_state": accepted.get("canonical_state"),
                            "run_id": run_kernel.state.run_id,
                            "request_id": run_kernel.state.request_id,
                            "accepted_contract_version": accepted.get("accepted_contract_version"),
                            "accepted_contract_digest": accepted.get("accepted_contract_digest"),
                        },
                        requested_synthesis_directive=str(
                            _safe_mapping(run_kernel.state.multicomponent_scheduler_context).get(
                                "requested_synthesis_directive"
                            )
                            or ""
                        ),
                        component_node=component_node,
                    )
                    reduce_component_work_graph_v1(
                        run_kernel=run_kernel,
                        operation="structure",
                        graph_candidate=single_graph,
                    )
                    continue
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
            current = _safe_mapping(run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE))
            if str(current.get("status") or "").startswith("blocked_"):
                raise _ScheduledSemanticWorkBlocked("required scheduled semantic work did not complete") from exc
            raise


def _execute_selected_lane(
    *,
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    requested_synthesis_directive: str,
    allow_searchos_component_receiver: bool = False,
) -> None:
    accepted = run_kernel.state.initial_answer_contract
    if not _selected_multicomponent_contract(
        accepted,
        allow_searchos_component_receiver=(allow_searchos_component_receiver),
    ):
        raise OrdinaryMulticomponentRuntimeError("accepted contract lost typed multi-component qualification")
    metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
    all_component_refs = [
        dict(item) for item in accepted.get("accepted_answer_component_refs") or () if isinstance(item, Mapping)
    ]
    component_refs = [item for item in all_component_refs if _component_requires_direct_work(item)]
    single_component_direct_admission = (
        allow_searchos_component_receiver and len(all_component_refs) == 1 and len(component_refs) == 1
    )
    if _clean_text(metadata.get("requested_synthesis_directive"), limit=360) != requested_synthesis_directive and not (
        single_component_direct_admission and requested_synthesis_directive == "single_component_direct_admission"
    ):
        raise OrdinaryMulticomponentRuntimeError("accepted contract lost typed multi-component qualification")

    final_top_evidence = [
        dict(item) for item in runtime_scope.get("final_top_evidence") or () if isinstance(item, Mapping)
    ]
    selected = select_bindable_final_passages_for_components(
        final_top_evidence,
        run_kernel.state.evidence_ledger.to_projection().to_dict(),
        component_refs,
        component_text_by_id=_accepted_component_text_by_id(accepted),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        answer_contract_version=accepted["accepted_contract_version"],
        answer_contract_digest=accepted["accepted_contract_digest"],
    )
    # Custody-gap exception is authorized only for the selected typed lane.
    typed_lane_custody_exception = True

    def _searchos_read_custody_matches_component(component_id: str) -> bool:
        if not allow_searchos_component_receiver or component_id not in selected:
            return False
        passage = _safe_mapping(selected[component_id].passage)
        return (
            passage.get("material_authority") == "read_custody_material"
            and passage.get("_provider") == "searchos_read_custody"
            and _current_searchos_read_handoff_for_component(
                run_kernel=run_kernel,
                passage=passage,
                component_id=component_id,
            )
        )

    missing_component_reasons: dict[str, str] = {}
    for component_ref in component_refs:
        component_id = str(component_ref["component_id"])
        if component_id not in selected:
            missing_component_reasons[component_id] = "no_bindable_passage"
            continue
        has_obligations = bool(
            component_ref.get("source_obligation_candidate_ids")
            or component_ref.get("source_obligation_candidate_refs")
        )
        if (
            has_obligations
            and not _searchos_read_custody_matches_component(component_id)
            and not source_requirement_ids_for_component_candidate(
                run_kernel.state.evidence_ledger.to_projection().to_dict(),
                evidence_ref_id=selected[component_id].evidence_ref_id,
                component_id=component_id,
                source_obligation_candidate_ids=tuple(
                    component_ref.get("source_obligation_candidate_ids")
                    or component_ref.get("source_obligation_candidate_refs")
                    or ()
                ),
                run_id=run_kernel.state.run_id,
                request_id=run_kernel.state.request_id,
                answer_contract_version=accepted["accepted_contract_version"],
                answer_contract_digest=accepted["accepted_contract_digest"],
                ignore_satisfied_provider_job_historical_gaps=(typed_lane_custody_exception),
            )
        ):
            missing_component_reasons[component_id] = "source_obligation_custody_not_current"
    missing_component_ids = list(missing_component_reasons)
    if missing_component_ids:
        raise OrdinaryMulticomponentRuntimeError(
            "selected multi-component lane lacks legitimate current evidence custody "
            "for: "
            + ",".join(
                f"{component_id}={missing_component_reasons[component_id]}" for component_id in missing_component_ids
            )
        )
    query = str(runtime_scope.get("query") or "")
    analyst_inputs = {
        str(component_ref["component_id"]): component_analyst_input_packet(
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            accepted_contract=accepted,
            component_ref=component_ref,
            evidence_input=_evidence_input(selected.get(str(component_ref["component_id"]))),
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
        allow_single_component_direct_admission=(single_component_direct_admission),
        requested_mode=str(runtime_scope.get("mode") or runtime_scope.get("strategy") or "Balanced"),
    )
    try:
        _drive_run_kernel_selected_semantic_work(
            run_kernel=run_kernel,
            runtime_scope=runtime_scope,
            selected_bindables=selected,
            component_analyst_input_packets=analyst_inputs,
            query=query,
        )
    finally:
        run_kernel.release_multicomponent_scheduler_transient_context()


def execute_searchos_recovery_component_admission_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    recovery_cycle_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute unchanged Component Analyst -> D-prime for one recovery slot.

    This path is deliberately outside the graph scheduler.  Its authority is
    the exact active SearchOS recovery lease, and it cannot call Scrutineer,
    Specialist, cross-component analysis, graph mutation, or contract amendment.
    """

    from core.multicomponent_role_runtime import role_artifact_ref
    from core.searchos_existing_gap_recovery_runtime import (
        validate_active_searchos_generalized_recovery_cycle_ref,
    )

    cycle = validate_active_searchos_generalized_recovery_cycle_ref(
        run_kernel.state.searchos_state,
        recovery_cycle_ref,
    )
    exact_cycle_ref = deepcopy(dict(recovery_cycle_ref))
    recovery_slot_ref = _safe_mapping(cycle.get("recovery_slot_ref"))
    component_id = str(recovery_slot_ref.get("component_id") or "")
    accepted = run_kernel.state.current_answer_contract or run_kernel.state.initial_answer_contract
    components = [
        _safe_mapping(item)
        for item in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping) and item.get("component_id") == component_id
    ]
    if len(components) != 1:
        raise OrdinaryMulticomponentRuntimeError("SearchOS recovery lost its accepted component")
    component_ref = components[0]
    final_top_evidence = [
        dict(item) for item in runtime_scope.get("final_top_evidence") or () if isinstance(item, Mapping)
    ]
    selected = select_bindable_final_passages_for_components(
        final_top_evidence,
        run_kernel.state.evidence_ledger.to_projection().to_dict(),
        [component_ref],
        component_text_by_id=_accepted_component_text_by_id(accepted),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        answer_contract_version=accepted["accepted_contract_version"],
        answer_contract_digest=accepted["accepted_contract_digest"],
    )
    bindable = selected.get(component_id)
    passage = _safe_mapping(getattr(bindable, "passage", None) if bindable is not None else None)
    passage_slot_ref = _safe_mapping(
        passage.get("searchos_slot_ref") or _safe_mapping(passage.get("searchos_qualification_lineage")).get("slot_ref")
    )
    if (
        bindable is None
        or passage.get("material_authority") != "read_custody_material"
        or passage.get("_provider") != "searchos_read_custody"
        or passage_slot_ref.get("slot_id") != recovery_slot_ref.get("slot_id")
        or passage_slot_ref.get("recovery_cycle_id") != exact_cycle_ref.get("cycle_id")
    ):
        raise OrdinaryMulticomponentRuntimeError("recovery component admission requires exact cycle READ material")
    analyst_input = component_analyst_input_packet(
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract=accepted,
        component_ref=component_ref,
        evidence_input=_evidence_input(bindable),
    )
    evaluation_key = f"{component_id}@{exact_cycle_ref['cycle_id']}"
    role_kwargs = _role_runtime_kwargs(runtime_scope)
    analyst_artifact = _execute_multicomponent_role_transport(
        run_kernel=run_kernel,
        role=ROLE_COMPONENT_ANALYST,
        input_packet=analyst_input,
        logical_evaluation_key=evaluation_key,
        searchos_recovery_cycle_ref=exact_cycle_ref,
        **role_kwargs,
    )
    dprime_input = component_dprime_input_packet(
        analyst_artifact=analyst_artifact,
        analyst_input_packet=analyst_input,
    )
    dprime_artifact = _execute_multicomponent_role_transport(
        run_kernel=run_kernel,
        role=ROLE_COMPONENT_DPRIME,
        input_packet=dprime_input,
        logical_evaluation_key=evaluation_key,
        searchos_recovery_cycle_ref=exact_cycle_ref,
        **role_kwargs,
    )
    observation, content_refs, coverage = _semantic_material(
        run_kernel=run_kernel,
        component_ref=component_ref,
        bindable=bindable,
        analyst_artifact=analyst_artifact,
        dprime_artifact=dprime_artifact,
        query=str(runtime_scope.get("query") or ""),
        searchos_recovery_cycle_ref=exact_cycle_ref,
    )
    admission = execute_multicomponent_component_admission(
        run_kernel=run_kernel,
        component_id=component_id,
        analyst_artifact=analyst_artifact,
        dprime_artifact=dprime_artifact,
        analyst_input_packet=analyst_input,
        semantic_observation=observation,
        sanitized_content_references=content_refs,
        component_coverage_record=coverage,
        allow_searchos_semantic_requirement_historical_gap_exception=True,
        logical_evaluation_key=evaluation_key,
        searchos_recovery_cycle_ref=exact_cycle_ref,
    )
    return {
        "schema_version": "searchos_recovery_component_admission_result_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "recovery_cycle_ref": exact_cycle_ref,
        "component_id": component_id,
        "logical_evaluation_key": evaluation_key,
        "component_analyst_proposal_ref": role_artifact_ref(analyst_artifact),
        "component_dprime_validation_ref": role_artifact_ref(dprime_artifact),
        "component_admission_ref": admission,
        "component_analyst_prompt_contract_unchanged": True,
        "component_dprime_prompt_contract_unchanged": True,
        "scrutineer_called": False,
        "specialist_called": False,
        "derived_component_created": (cycle.get("recovery_classification") == "searched_premise"),
        "graph_mutated": False,
    }


def execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    execute_selected_lane: bool = True,
    allow_searchos_component_receiver: bool = False,
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
        return OrdinaryMulticomponentResult(status=OrdinaryMulticomponentStatus.ALREADY_COMPLETED)
    scheduler_state = _safe_mapping(run_kernel.state.projections.get("multicomponent_graph_scheduler"))
    if str(scheduler_state.get("status") or "").startswith("blocked_"):
        return OrdinaryMulticomponentResult(status=OrdinaryMulticomponentStatus.ALREADY_COMPLETED)
    if run_kernel.state.initial_answer_contract:
        accepted = run_kernel.state.initial_answer_contract
        metadata = _safe_mapping(accepted.get("question_meaning_metadata"))
        if _selected_multicomponent_contract(
            accepted,
            allow_searchos_component_receiver=(allow_searchos_component_receiver),
        ):
            if not execute_selected_lane:
                return OrdinaryMulticomponentResult(status=OrdinaryMulticomponentStatus.SELECTED_PENDING)
            requested_synthesis_directive = _clean_text(
                metadata.get("requested_synthesis_directive"),
                limit=360,
            )
            component_count = len(
                [item for item in accepted.get("accepted_answer_component_refs") or () if isinstance(item, Mapping)]
            )
            if requested_synthesis_directive is None and allow_searchos_component_receiver and component_count == 1:
                requested_synthesis_directive = "single_component_direct_admission"
            assert requested_synthesis_directive is not None
            try:
                _execute_selected_lane(
                    run_kernel=run_kernel,
                    runtime_scope=runtime_scope,
                    requested_synthesis_directive=requested_synthesis_directive,
                    allow_searchos_component_receiver=(allow_searchos_component_receiver),
                )
            except _ScheduledSemanticWorkBlocked as exc:
                # The ordinary bounded lane keeps canonical blockage as FAP
                # readiness input. The separately licensed SearchOS receiver
                # must expose the blockage at its orchestrator boundary;
                # otherwise it can report COMPLETED without Analyst origination.
                if allow_searchos_component_receiver:
                    raise OrdinaryMulticomponentRuntimeError(
                        "SearchOS component receiver did not complete: "
                        + str(exc)[:240]
                    ) from exc
            return OrdinaryMulticomponentResult(status=OrdinaryMulticomponentStatus.COMPLETED)
        return direct_or_deferred()

    return direct_or_deferred()


def ordinary_multicomponent_path_completed(run_kernel: Any) -> bool:
    return bool(run_kernel.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))


def ordinary_multicomponent_path_selected(run_kernel: Any) -> bool:
    return _selected_multicomponent_contract(run_kernel.state.initial_answer_contract)


__all__ = [
    "OrdinaryMulticomponentResult",
    "OrdinaryMulticomponentRuntimeError",
    "OrdinaryMulticomponentStatus",
    "authorize_searched_premise_recovery_from_analyst_proposals",
    "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
    "execute_searchos_recovery_component_admission_from_scope",
    "execute_searchos_recovery_graph_reproof_from_scope",
    "ordinary_multicomponent_path_completed",
    "ordinary_multicomponent_path_selected",
    "record_analyst_query_resolution_candidates",
    "record_analyst_query_resolution_downstream_refs",
    "resolve_next_searched_premise_recovery_posture",
]
