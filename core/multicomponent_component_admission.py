"""Pure staging for RunKernel-owned multi-component component admission."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import (
    ComponentCoverageReductionError,
    build_component_coverage_reduction_projection,
    build_component_coverage_reduction_state,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    role_artifact_ref,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)
from core.quantitative_finalization_authority import (
    specialist_quantitative_authority_ref_from_handoff,
)
from core.semantic_observation_admission_runtime import (
    SemanticObservationAdmissionError,
    build_semantic_observation_admission_projection,
    build_semantic_observation_admission_state,
)

MULTICOMPONENT_COMPONENT_ADMISSION_STAGE = "multicomponent_component_admission"
MULTICOMPONENT_COMPONENT_ADMISSION_OWNER = (
    "RunKernel.MulticomponentComponentAdmission"
)


class MulticomponentComponentAdmissionError(ValueError):
    """Raised before canonical mutation when component admission is invalid."""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _accepted_component(
    accepted_contract: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    for raw in accepted_contract.get("accepted_answer_component_refs") or ():
        component = _safe_mapping(raw)
        if component.get("component_id") == component_id:
            return component
    raise MulticomponentComponentAdmissionError(
        f"component admission references unknown component {component_id!r}"
    )


def component_analyst_input_packet(
    *,
    run_id: str,
    request_id: str,
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    evidence_input: Mapping[str, Any],
) -> dict[str, Any]:
    from core.quantitative_specialist_product_activation import (
        build_component_quantitative_source_catalog,
        build_quantitative_specialist_proposal_contract,
    )

    packet = {
        "supported_query_class": (
            "ordinary-bounded-multicomponent-factual-synthesis-v1"
        ),
        "run_binding": {
            "run_id": run_id,
            "request_id": request_id,
            "accepted_contract_version": accepted_contract.get(
                "accepted_contract_version"
            ),
            "accepted_contract_digest": accepted_contract.get(
                "accepted_contract_digest"
            ),
        },
        "component_ref": {
            "component_id": component_ref.get("component_id"),
            "component_revision": component_ref.get("component_revision"),
            "component_digest": component_ref.get("component_digest"),
            "user_facing_label": component_ref.get("user_facing_label"),
            "user_facing_question": component_ref.get("user_facing_question"),
            "mandatory_caveats": list(
                component_ref.get("mandatory_caveats") or ()
            ),
            "prohibited_upgrades": list(
                component_ref.get("prohibited_upgrades") or ()
            ),
        },
        "component_evidence": _safe_mapping(evidence_input),
    }
    packet["quantitative_source_catalog"] = (
        build_component_quantitative_source_catalog(
            component_ref=packet["component_ref"],
            evidence_input=packet["component_evidence"],
        )
    )
    packet["quantitative_specialist_proposal_contract"] = (
        build_quantitative_specialist_proposal_contract(
            target_kind="component",
            target_key_or_rule=str(packet["component_ref"]["component_id"]),
            allowed_source_local_keys=("component_evidence",),
        )
    )
    return packet


def component_dprime_input_packet(
    *,
    analyst_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    specialist_need_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    analyst = validate_multicomponent_role_artifact(
        analyst_artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    exact_component_input = _safe_mapping(analyst_input_packet)
    exact_component_input.pop(
        "quantitative_specialist_proposal_contract", None
    )
    packet = {
        "supported_query_class": (
            "ordinary-bounded-multicomponent-factual-synthesis-v1"
        ),
        "analyst_artifact_ref": role_artifact_ref(analyst),
        "nominated_claim": {
            "claim_text": analyst["semantic_output"]["claim_text"],
            "support_status": analyst["semantic_output"]["support_status"],
            "caveats": list(analyst["semantic_output"].get("caveats") or ()),
            "nonclaims": list(
                analyst["semantic_output"].get("nonclaims") or ()
            ),
        },
        "exact_component_and_evidence_input": exact_component_input,
    }
    if specialist_need_handoff:
        from core.specialist_graph_runtime import (
            specialist_need_handoff_packet,
            validate_specialist_need_handoff,
        )

        handoff = validate_specialist_need_handoff(specialist_need_handoff)
        target = _safe_mapping(handoff.get("canonical_target_ref"))
        component_id = _safe_mapping(
            analyst_input_packet.get("component_ref")
        ).get("component_id")
        if (
            target.get("target_kind") != "component"
            or target.get("target_key") != component_id
        ):
            raise ValueError(
                "component D-prime Specialist handoff target mismatch"
            )
        packet["specialist_need_handoff"] = specialist_need_handoff_packet(
            handoff
        )
    return packet


def _typed_lane_custody_gap_exception_authorized(
    accepted_contract: Mapping[str, Any],
) -> bool:
    """Return True only for the exact Phase 1 typed-lane contract shape."""

    metadata = _safe_mapping(accepted_contract.get("question_meaning_metadata"))
    component_refs = [
        item
        for item in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    return (
        metadata.get("explicit_factual_component_list") is True
        and _clean_text(metadata.get("requested_synthesis_directive"), limit=360) is not None
        and 1 <= len(component_refs) <= 5
    )


def stage_multicomponent_component_admission(
    *,
    action_id: str,
    run_id: str,
    request_id: str,
    accepted_contract: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    semantic_observation_admission_history: Sequence[Mapping[str, Any]],
    component_coverage_history: Sequence[Mapping[str, Any]],
    component_id: str,
    analyst_artifact: Mapping[str, Any],
    dprime_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    semantic_observation: Mapping[str, Any] | None,
    sanitized_content_references: Sequence[Mapping[str, Any]],
    component_coverage_record: Mapping[str, Any] | None,
    specialist_need_handoff: Mapping[str, Any] | None = None,
    allow_searchos_semantic_requirement_historical_gap_exception: bool = False,
) -> dict[str, Any]:
    """Validate owner execution and stage semantic/coverage state atomically."""

    accepted = _safe_mapping(accepted_contract)
    component = _accepted_component(accepted, component_id)
    analyst = validate_multicomponent_role_artifact(
        analyst_artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    dprime = validate_multicomponent_role_artifact(
        dprime_artifact,
        expected_role=ROLE_COMPONENT_DPRIME,
    )
    if any(
        artifact.get("run_id") != run_id
        or artifact.get("request_id") != request_id
        for artifact in (analyst, dprime)
    ):
        raise MulticomponentComponentAdmissionError(
            "component semantic role artifact cross-run binding"
        )
    expected_analyst_input = component_analyst_input_packet(
        run_id=run_id,
        request_id=request_id,
        accepted_contract=accepted,
        component_ref=component,
        evidence_input=_safe_mapping(
            analyst_input_packet.get("component_evidence")
        ),
    )
    if analyst.get("input_packet_digest") != safe_packet_digest(
        expected_analyst_input
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst exact input binding mismatch"
        )
    expected_dprime_input = component_dprime_input_packet(
        analyst_artifact=analyst,
        analyst_input_packet=expected_analyst_input,
        specialist_need_handoff=specialist_need_handoff,
    )
    if dprime.get("input_packet_digest") != safe_packet_digest(
        expected_dprime_input
    ):
        raise MulticomponentComponentAdmissionError(
            "component D-prime nominated claim/input binding mismatch"
        )
    if (
        analyst.get("logical_evaluation_key") != component_id
        or dprime.get("logical_evaluation_key") != component_id
    ):
        raise MulticomponentComponentAdmissionError(
            "component role logical evaluation key mismatch"
        )

    analyst_status = analyst["semantic_output"]["support_status"]
    validation_status = dprime["semantic_output"]["validation_status"]
    supported = (
        analyst_status in {"supported", "supported_with_caveats"}
        and validation_status in {"supported", "supported_with_caveats"}
    )
    observation_payload = _safe_mapping(semantic_observation)
    content_refs = [
        _safe_mapping(item)
        for item in sanitized_content_references
        if isinstance(item, Mapping)
    ]
    coverage_payload = _safe_mapping(component_coverage_record)
    if supported and (not observation_payload or not content_refs or not coverage_payload):
        raise MulticomponentComponentAdmissionError(
            "supported component admission requires semantic observation, content refs, and coverage"
        )
    if not supported and (observation_payload or content_refs or coverage_payload):
        raise MulticomponentComponentAdmissionError(
            "blocked component admission cannot manufacture admitted semantic state"
        )
    nominated_claim = analyst["semantic_output"]["claim_text"]
    if supported and observation_payload.get("claim_or_value") != nominated_claim:
        raise MulticomponentComponentAdmissionError(
            "SemanticObservation claim must equal the Analyst-nominated claim"
        )
    evidence_input = _safe_mapping(analyst_input_packet.get("component_evidence"))
    if supported:
        expected_evidence_ref = evidence_input.get("evidence_ref_id")
        observation_evidence = [
            item for item in observation_payload.get("evidence_refs") or () if item
        ]
        if (
            not expected_evidence_ref
            or observation_evidence != [expected_evidence_ref]
            or any(
                item.get("evidence_ref_id") != expected_evidence_ref
                for item in content_refs
            )
        ):
            raise MulticomponentComponentAdmissionError(
                "component admission evidence bindings must match Analyst input evidence"
            )

    admission_state: dict[str, Any] = {}
    admission_projection: dict[str, Any] = {}
    coverage_state: dict[str, Any] = {}
    coverage_projection: dict[str, Any] = {}
    if supported:
        admission_inputs = {
            "semantic_observation_id": observation_payload.get(
                "observation_id"
            ),
            "semantic_observation_digest": observation_payload.get(
                "observation_digest"
            ),
            "accepted_contract_digest": accepted.get(
                "accepted_contract_digest"
            ),
            "accepted_contract_version": accepted.get(
                "accepted_contract_version"
            ),
            "answer_component_id": component["component_id"],
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "request_id": request_id,
        }
        try:
            admission_state = build_semantic_observation_admission_state(
                action_id=action_id,
                action_inputs=admission_inputs,
                observation_payload={
                    "semantic_observation": observation_payload,
                    "sanitized_content_references": content_refs,
                },
                accepted_contract=accepted,
                evidence_ledger_projection=evidence_ledger_projection,
                existing_observation_ids=[
                    _safe_mapping(item).get("observation_id")
                    for item in semantic_observation_admission_history
                ],
                existing_observation_digests=[
                    _safe_mapping(item).get("observation_digest")
                    for item in semantic_observation_admission_history
                ],
                run_id=run_id,
                request_id=request_id,
            )
            admission_projection = build_semantic_observation_admission_projection(
                admission_state=admission_state
            )
            coverage_inputs = {
                "coverage_record_id": coverage_payload.get("record_id"),
                "coverage_record_digest": coverage_payload.get("record_digest"),
                "accepted_contract_digest": accepted.get(
                    "accepted_contract_digest"
                ),
                "accepted_contract_version": accepted.get(
                    "accepted_contract_version"
                ),
                "answer_component_id": component["component_id"],
                "component_revision": component["component_revision"],
                "component_digest": component["component_digest"],
                "request_id": request_id,
            }
            coverage_state = build_component_coverage_reduction_state(
                action_id=action_id,
                action_inputs=coverage_inputs,
                coverage_payload={
                    "component_coverage_record": coverage_payload,
                },
                accepted_contract=accepted,
                admission_history=[
                    *[deepcopy(dict(item)) for item in semantic_observation_admission_history],
                    admission_projection,
                ],
                evidence_ledger_projection=evidence_ledger_projection,
                existing_coverage_record_ids=[
                    _safe_mapping(item).get("coverage_record_id")
                    for item in component_coverage_history
                ],
                existing_coverage_record_digests=[
                    _safe_mapping(item).get("coverage_record_digest")
                    for item in component_coverage_history
                ],
                run_id=run_id,
                request_id=request_id,
                ignore_satisfied_provider_job_historical_gaps=(
                    _typed_lane_custody_gap_exception_authorized(accepted)
                    or (
                        allow_searchos_semantic_requirement_historical_gap_exception
                        and any(
                            str(item).startswith("searchos_semantic_requirement:")
                            for item in _safe_mapping(coverage_payload.get("evidence_ledger_binding")).get(
                                "source_requirement_ids", ()
                            )
                        )
                    )
                ),
            )
            coverage_projection = build_component_coverage_reduction_projection(
                coverage_state=coverage_state
            )
        except (SemanticObservationAdmissionError, ComponentCoverageReductionError) as exc:
            raise MulticomponentComponentAdmissionError(str(exc)) from exc

    caveats = list(
        dict.fromkeys(
            [
                *analyst["semantic_output"].get("caveats", ()),
                *dprime["semantic_output"].get("caveats", ()),
            ]
        )
    )
    nonclaims = list(
        dict.fromkeys(
            [
                *analyst["semantic_output"].get("nonclaims", ()),
                *dprime["semantic_output"].get("nonclaims", ()),
            ]
        )
    )
    blockers = list(
        dict.fromkeys(
            [
                *analyst["semantic_output"].get("blockers", ()),
                *dprime["semantic_output"].get("blockers", ()),
            ]
        )
    )
    admission_status = (
        "admitted_with_caveats"
        if supported and caveats
        else "admitted"
        if supported
        else "blocked"
        if validation_status in {"challenged", "blocked"}
        else "unsupported"
    )
    claim_text = analyst["semantic_output"]["claim_text"]
    specialist_quantitative_authority_ref = (
        specialist_quantitative_authority_ref_from_handoff(
            specialist_need_handoff,
            applicable_dprime_ref=role_artifact_ref(dprime),
        )
        if supported and specialist_need_handoff
        else {}
    )
    return {
        "admission_state": admission_state,
        "admission_projection": admission_projection,
        "coverage_state": coverage_state,
        "coverage_projection": coverage_projection,
        "component_admission_ref": {
            "schema_version": "multicomponent_component_admission_ref_v1",
            "owner": MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
            "canonical_state": True,
            "run_id": run_id,
            "request_id": request_id,
            "action_id": action_id,
            "accepted_contract_version": accepted.get(
                "accepted_contract_version"
            ),
            "accepted_contract_digest": accepted.get(
                "accepted_contract_digest"
            ),
            "component_id": component["component_id"],
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "admission_status": admission_status,
            "current": True,
            "stale": False,
            "analyst_finding_ref": role_artifact_ref(analyst),
            "dprime_validation_ref": role_artifact_ref(dprime),
            "specialist_quantitative_authority_ref": (
                specialist_quantitative_authority_ref
            ),
            "admitted_claim_ref": (
                {
                    "claim_id": f"component-claim:{component['component_id']}",
                    "claim_text": claim_text,
                    "claim_digest": safe_packet_digest(
                        {"claim_text": claim_text}
                    ),
                }
                if supported
                else {}
            ),
            "semantic_observation_ref": (
                {
                    "observation_id": admission_projection.get(
                        "observation_id"
                    ),
                    "observation_digest": admission_projection.get(
                        "observation_digest"
                    ),
                }
                if admission_projection
                else {}
            ),
            "component_coverage_ref": (
                {
                    "coverage_record_id": coverage_projection.get(
                        "coverage_record_id"
                    ),
                    "coverage_record_digest": coverage_projection.get(
                        "coverage_record_digest"
                    ),
                    "coverage_state": coverage_projection.get("coverage_state"),
                }
                if coverage_projection
                else {}
            ),
            "evidence_refs": [
                {
                    "evidence_ref_id": item.get("evidence_ref_id"),
                    "content_ref_id": item.get("content_ref_id"),
                    "content_digest": item.get("content_digest"),
                }
                for item in content_refs
            ],
            "required_caveats": caveats,
            "preserved_nonclaims": nonclaims,
            "blocker_refs": [{"reason": item} for item in blockers],
            "logical_component_analyst_evaluations": 1,
            "logical_component_dprime_evaluations": 1,
            "physical_component_analyst_calls": 1,
            "physical_component_dprime_calls": 1,
        },
    }


def execute_multicomponent_component_admission(
    *,
    run_kernel: Any,
    component_id: str,
    analyst_artifact: Mapping[str, Any],
    dprime_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    semantic_observation: Mapping[str, Any] | None,
    sanitized_content_references: Sequence[Mapping[str, Any]],
    component_coverage_record: Mapping[str, Any] | None,
    specialist_need_handoff: Mapping[str, Any] | None = None,
    allow_searchos_semantic_requirement_historical_gap_exception: bool = False,
) -> dict[str, Any]:
    """Stage then atomically reduce one component through RunKernel."""

    from core.run_kernel import Observation, RunStageStatus

    analyst = validate_multicomponent_role_artifact(
        analyst_artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    dprime = validate_multicomponent_role_artifact(
        dprime_artifact,
        expected_role=ROLE_COMPONENT_DPRIME,
    )
    completed_analyst = run_kernel.state.projections.get(
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}"
    )
    completed_dprime = run_kernel.state.projections.get(
        f"multicomponent_role:{ROLE_COMPONENT_DPRIME}:{component_id}"
    )
    if (
        not isinstance(completed_analyst, Mapping)
        or not isinstance(completed_dprime, Mapping)
        or role_artifact_ref(completed_analyst) != role_artifact_ref(analyst)
        or role_artifact_ref(completed_dprime) != role_artifact_ref(dprime)
    ):
        raise MulticomponentComponentAdmissionError(
            "component admission requires exact completed RunKernel role artifacts"
        )
    action = run_kernel.authorize_multicomponent_component_admission(
        component_id=component_id,
        analyst_artifact_digest=analyst["artifact_digest"],
        dprime_artifact_digest=dprime["artifact_digest"],
    )
    accepted_contract = (
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    staged = stage_multicomponent_component_admission(
        action_id=action.action_id,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract=accepted_contract,
        evidence_ledger_projection=(
            run_kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        semantic_observation_admission_history=(
            run_kernel.state.semantic_observation_admission_history
        ),
        component_coverage_history=run_kernel.state.component_coverage_history,
        component_id=component_id,
        analyst_artifact=analyst,
        dprime_artifact=dprime,
        analyst_input_packet=analyst_input_packet,
        semantic_observation=semantic_observation,
        sanitized_content_references=sanitized_content_references,
        component_coverage_record=component_coverage_record,
        specialist_need_handoff=specialist_need_handoff,
        allow_searchos_semantic_requirement_historical_gap_exception=(
            allow_searchos_semantic_requirement_historical_gap_exception
        ),
    )
    component_ref = staged["component_admission_ref"]
    prior = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
    )
    prior_refs = [
        deepcopy(dict(item))
        for item in prior.get("component_admission_refs") or ()
        if isinstance(item, Mapping)
    ]
    if any(item.get("component_id") == component_id for item in prior_refs):
        raise MulticomponentComponentAdmissionError(
            "component admission is append-only and component is already present"
        )
    refs = [*prior_refs, component_ref]
    aggregate_core = {
        "schema_version": "multicomponent_component_admission_projection_v1",
        "owner": MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "accepted_contract_version": accepted_contract.get(
            "accepted_contract_version"
        ),
        "accepted_contract_digest": accepted_contract.get(
            "accepted_contract_digest"
        ),
        "component_admission_refs": refs,
        "component_count": len(refs),
        "admitted_component_count": sum(
            item.get("admission_status") in {"admitted", "admitted_with_caveats"}
            for item in refs
        ),
        "blocked_component_count": sum(
            item.get("admission_status") not in {"admitted", "admitted_with_caveats"}
            for item in refs
        ),
        "logical_component_analyst_evaluations": len(refs),
        "logical_component_dprime_evaluations": len(refs),
        "physical_component_analyst_calls": len(refs),
        "physical_component_dprime_calls": len(refs),
        "latest_action_id": action.action_id,
    }
    aggregate = {
        **aggregate_core,
        "projection_digest": safe_packet_digest(aggregate_core),
    }
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={
                "component_admission_projection": aggregate,
                "component_admission_ref": component_ref,
                "semantic_observation_admission_state": staged["admission_state"],
                "semantic_observation_admission_projection": staged[
                    "admission_projection"
                ],
                "component_coverage_state": staged["coverage_state"],
                "component_coverage_projection": staged["coverage_projection"],
            },
        )
    )
    return deepcopy(component_ref)


__all__ = [
    "MULTICOMPONENT_COMPONENT_ADMISSION_OWNER",
    "MULTICOMPONENT_COMPONENT_ADMISSION_STAGE",
    "MulticomponentComponentAdmissionError",
    "component_analyst_input_packet",
    "component_dprime_input_packet",
    "execute_multicomponent_component_admission",
    "stage_multicomponent_component_admission",
]
