"""PRODUCT-PATH-REGRESSION: selective recovery recomputation authority."""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.component_work_graph_v1 import (
    MULTICOMPONENT_CARRY_FORWARD_STAGE,
    MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
    ComponentWorkGraphV1Error,
    admit_synthesis_node_via_runkernel,
    build_synthesis_carry_forward_projection,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    derive_selective_recomputation_closure,
    graph_with_selective_invalidation,
    reduce_component_work_graph_v1,
    reduce_selective_invalidation_via_runkernel,
    reduce_selective_recomputation_closure,
    runkernel_canonical_graph,
    validate_component_work_graph_v1,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    safe_packet_digest,
)
from core.run_kernel import (
    MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from tests.test_multicomponent_component_work_graph_v1 import (
    REQUEST_ID,
    RUN_ID,
    _component_node,
    _role_artifact,
    _seed_component_admission,
    _validate_synthesis,
)


def _closure_core(closure: dict) -> dict:
    return {
        key: deepcopy(value)
        for key, value in closure.items()
        if key not in {"closure_id", "closure_digest"}
    }


def _redigest_closure(closure: dict) -> dict:
    updated = _closure_core(closure)
    digest = safe_packet_digest(updated)
    updated["closure_id"] = f"selective-closure:{digest[:20]}"
    updated["closure_digest"] = digest
    return updated


def _selective_source_graph() -> tuple[RunKernel, dict]:
    nodes = [_component_node(index) for index in range(1, 5)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain benefits, filing route, and applicant guidance."
    cross_input = cross_component_input_packet(
        component_nodes=nodes,
        accepted_contract_ref=accepted_ref,
        requested_synthesis_directive=directive,
    )
    cross = _role_artifact(
        ROLE_CROSS_COMPONENT_ANALYST,
        {
            "synthesis_proposals": [
                {
                    "synthesis_key": "benefit_summary",
                    "claim_text": "The rebate and income threshold define the benefit.",
                    "relationship_type": "benefit_conjunction",
                    "component_inputs": [
                        "component:component-1",
                        "component:component-2",
                    ],
                    "synthesis_inputs": [],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
                {
                    "synthesis_key": "filing_route",
                    "claim_text": "The ordinary filing inputs define the route.",
                    "relationship_type": "filing_conjunction",
                    "component_inputs": [
                        "component:component-3",
                        "component:component-4",
                    ],
                    "synthesis_inputs": [],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
                {
                    "synthesis_key": "applicant_guidance",
                    "claim_text": "The benefit and filing route determine guidance.",
                    "relationship_type": "guided_conjunction",
                    "component_inputs": [],
                    "synthesis_inputs": ["benefit_summary", "filing_route"],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
            ]
        },
        cross_input,
    )
    candidate = component_work_graph_v1_from_cross_component_artifact(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_contract_ref=accepted_ref,
        requested_synthesis_directive=directive,
        component_nodes=nodes,
        cross_component_artifact=cross,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(kernel, nodes, cross_artifact=cross)
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    graph = _validate_synthesis(kernel, graph, "benefit_summary")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="benefit_summary",
    )
    return kernel, graph


def _node_ref(node: dict) -> dict:
    return {
        "node_kind": node["node_kind"],
        "node_id": node["node_id"],
        "node_revision": node["node_revision"],
        "node_digest": node["node_digest"],
        "component_id": node.get("component_id"),
        "synthesis_key": node["synthesis_key"],
        "status": node["status"],
        "current": True,
        "stale": False,
    }


def _closure_fixture() -> tuple[RunKernel, dict, dict]:
    kernel, graph = _selective_source_graph()
    filing = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "filing_route"
    )
    authorization_core = {
        "schema_version": "multicomponent_missing_component_recovery_authorization_v1",
        "owner": "RunKernel.MulticomponentRecoveryAuthorization",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "authorization_id": "recovery-authorization:test",
        "authorized_action_id": "recovery-action:test",
        "target_kind": "synthesis",
        "target_key": "synthesis_02",
        "resolved_target": _node_ref(filing),
        "graph_id": graph["graph_id"],
        "graph_revision": graph["graph_revision"],
        "graph_digest": graph["graph_digest"],
    }
    authorization = {
        **authorization_core,
        "authorization_digest": safe_packet_digest(authorization_core),
    }
    recovered_node = _component_node(
        5,
        admission_overrides={
            "accepted_contract_version": "0.2-recovery",
            "accepted_contract_digest": "accepted-contract-digest-recovery",
        },
    )
    accepted_refs = [
        {
            "component_id": item["component_id"],
            "component_revision": item["component_revision"],
            "component_digest": item["component_digest"],
            "user_facing_label": item["component_label"],
            "user_facing_question": item["component_question"],
        }
        for item in [*graph["component_nodes"], recovered_node]
    ]
    current_contract = {
        "owner": "RunKernel.CurrentAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.2-recovery",
        "accepted_contract_digest": "accepted-contract-digest-recovery",
        "parent_question_meaning_record_id": None,
        "parent_question_meaning_record_digest": None,
        "accepted_answer_component_refs": accepted_refs,
        "accepted_answer_component_count": len(accepted_refs),
    }
    amendment_admission = {
        "amendment_record_id": "amendment:test",
        "amendment_record_digest": "amendment-record-digest",
        "authorized_action_id": "amendment-admission-action:test",
        "admission_digest": "amendment-admission-digest",
    }
    amendment_application = {
        "amendment_record_id": "amendment:test",
        "authorized_action_id": "amendment-application-action:test",
        "application_digest": "amendment-application-digest",
    }
    recovered_admission = {
        "schema_version": "multicomponent_component_admission_ref_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "component_id": recovered_node["component_id"],
        "component_revision": recovered_node["component_revision"],
        "component_digest": recovered_node["component_digest"],
        "accepted_contract_version": current_contract[
            "accepted_contract_version"
        ],
        "accepted_contract_digest": current_contract["accepted_contract_digest"],
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "action_id": recovered_node["component_admission_action_ref"]["action_id"],
        "analyst_finding_ref": recovered_node["analyst_finding_ref"],
        "dprime_validation_ref": recovered_node["dprime_validation_ref"],
        "admitted_claim_ref": recovered_node["admitted_claim_ref"],
        "semantic_observation_ref": recovered_node["semantic_observation_ref"],
        "component_coverage_ref": recovered_node["component_coverage_ref"],
        "evidence_refs": recovered_node["evidence_refs"],
        "required_caveats": recovered_node["required_caveats"],
        "preserved_nonclaims": recovered_node["preserved_nonclaims"],
        "blocker_refs": recovered_node["blocker_refs"],
    }
    kernel.state.projections[MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE] = authorization
    kernel.state.current_answer_contract = current_contract
    kernel.state.contract_amendment_admission_projection = amendment_admission
    kernel.state.contract_amendment_application_projection = amendment_application
    component_projection = kernel.state.projections["multicomponent_component_admission"]
    component_projection["component_admission_refs"].append(recovered_admission)
    closure = derive_selective_recomputation_closure(
        graph,
        recovery_authorization_ref=authorization,
        current_contract_ref={
            key: current_contract[key]
            for key in (
                "owner",
                "canonical_state",
                "run_id",
                "request_id",
                "accepted_contract_version",
                "accepted_contract_digest",
                "parent_question_meaning_record_id",
                "parent_question_meaning_record_digest",
            )
        }
        | {"accepted_answer_component_count": len(accepted_refs)},
        contract_amendment_admission_ref=amendment_admission,
        contract_amendment_application_ref=amendment_application,
        recovered_component_admission_ref=recovered_admission,
    )
    return kernel, graph, closure


def _transition_inputs(kernel: RunKernel, closure: dict) -> dict:
    accepted_component = kernel.state.current_answer_contract[
        "accepted_answer_component_refs"
    ][-1]
    recovered_admission = kernel.state.projections[
        "multicomponent_component_admission"
    ]["component_admission_refs"][-1]
    return {
        "closure": closure,
        "recovered_component_node": component_work_node_v1_from_admitted_component(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_component_ref=accepted_component,
            component_admission_ref=recovered_admission,
        ),
        "current_contract_ref": closure["current_contract_ref"],
        "recovery_authorization_ref": kernel.state.projections[
            MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
        ],
        "contract_amendment_admission_ref": closure[
            "contract_amendment_admission_ref"
        ],
        "amendment_application_ref": closure[
            "contract_amendment_application_ref"
        ],
    }


def test_runkernel_derives_exact_pretransition_selective_closure() -> None:
    kernel, graph, closure = _closure_fixture()

    canonical = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )

    assert canonical["source_graph_ref"] == {
        "graph_id": graph["graph_id"],
        "graph_revision": graph["graph_revision"],
        "graph_digest": graph["graph_digest"],
    }
    assert canonical["directly_affected_synthesis_keys"] == ["filing_route"]
    assert canonical["transitively_affected_synthesis_keys"] == [
        "applicant_guidance"
    ]
    assert canonical["affected_synthesis_keys"] == [
        "filing_route",
        "applicant_guidance",
    ]
    assert canonical["unaffected_active_synthesis_keys"] == ["benefit_summary"]
    assert kernel.state.projections[f"{MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE}_history"][
        "closures"
    ] == [canonical]


@pytest.mark.parametrize("mutation", ["omit_transitive", "add_independent"])
def test_runkernel_rejects_candidate_authored_closure_sets(mutation: str) -> None:
    kernel, _graph, closure = _closure_fixture()
    forged = deepcopy(closure)
    if mutation == "omit_transitive":
        forged["transitively_affected_synthesis_keys"] = []
        forged["affected_synthesis_keys"] = ["filing_route"]
        forged["affected_topological_order"] = ["filing_route"]
        forged["unaffected_active_synthesis_keys"] = [
            "benefit_summary",
            "applicant_guidance",
        ]
    else:
        forged["transitively_affected_synthesis_keys"] = [
            "benefit_summary",
            "applicant_guidance",
        ]
        forged["affected_synthesis_keys"] = [
            "benefit_summary",
            "filing_route",
            "applicant_guidance",
        ]
        forged["affected_topological_order"] = list(forged["affected_synthesis_keys"])
        forged["unaffected_active_synthesis_keys"] = []
    forged = _redigest_closure(forged)

    with pytest.raises(
        RunKernelTransitionError,
        match="does not equal RunKernel derivation",
    ):
        reduce_selective_recomputation_closure(
            run_kernel=kernel,
            closure_candidate=forged,
        )


def test_selective_closure_rejects_forged_digest() -> None:
    kernel, _graph, closure = _closure_fixture()
    closure["closure_digest"] = "forged"

    with pytest.raises(ComponentWorkGraphV1Error, match="digest mismatch"):
        reduce_selective_recomputation_closure(
            run_kernel=kernel,
            closure_candidate=closure,
        )


def test_selective_closure_rejects_wrong_source_graph_binding() -> None:
    kernel, _graph, _closure = _closure_fixture()
    authorization = kernel.state.projections[
        MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
    ]
    authorization["graph_revision"] += 1

    with pytest.raises(
        RunKernelTransitionError,
        match="authorization-bound graph snapshot",
    ):
        kernel.authorize_multicomponent_selective_recomputation_closure()


def test_selective_invalidation_carries_only_unaffected_synthesis() -> None:
    kernel, source, closure = _closure_fixture()
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    prior_benefit = next(
        item
        for item in source["synthesis_nodes"]
        if item["synthesis_key"] == "benefit_summary"
    )

    amended = reduce_selective_invalidation_via_runkernel(
        run_kernel=kernel,
        graph=source,
        **_transition_inputs(kernel, canonical_closure),
    )

    assert amended["graph_id"] == source["graph_id"]
    assert amended["graph_revision"] == source["graph_revision"] + 1
    assert amended["previous_graph_digest"] == source["graph_digest"]
    assert amended["accepted_contract_ref"] == canonical_closure[
        "current_contract_ref"
    ]
    assert [item["synthesis_key"] for item in amended["synthesis_nodes"]] == [
        "benefit_summary"
    ]
    carried = amended["synthesis_nodes"][0]
    assert carried["node_id"] == prior_benefit["node_id"]
    assert carried["node_revision"] == str(
        int(prior_benefit["node_revision"]) + 1
    )
    assert carried["node_digest"] != prior_benefit["node_digest"]
    assert carried["claim_text"] == prior_benefit["claim_text"]
    assert carried["input_node_refs"] == prior_benefit["input_node_refs"]
    assert carried["dprime_validation_ref"] == {}
    assert carried["runkernel_admission_ref"] == {}
    assert carried["carried_semantic_lineage"] == {
        "prior_cross_component_analyst_ref": prior_benefit["proposal_ref"][
            "cross_component_analyst_ref"
        ],
        "prior_synthesis_claim_ref": prior_benefit["synthesis_claim_ref"],
        "prior_synthesis_dprime_ref": prior_benefit["dprime_validation_ref"],
        "prior_synthesis_admission_ref": prior_benefit[
            "runkernel_admission_ref"
        ],
    }
    action_ref = carried["current_node_authority"][
        "runkernel_carry_forward_action_ref"
    ]
    assert action_ref["operation"] == "selective_invalidation"
    assert "graph_digest" not in action_ref
    assert "carry_forward_projection_digest" not in action_ref
    assert {
        item["superseded_node_ref"]["synthesis_key"]
        for item in amended["stale_synthesis_history"]
    } == {"filing_route", "applicant_guidance"}
    assert amended["whole_graph_resynthesis_rounds"] == 0
    assert amended["selective_recomputation_rounds"] == 1
    assert amended["affected_synthesis_count"] == 2
    assert amended["preserved_synthesis_count"] == 1
    assert amended["carry_forward_count"] == 1
    projection = kernel.state.projections[MULTICOMPONENT_CARRY_FORWARD_STAGE]
    assert projection["final_graph_ref"] == {
        "graph_id": amended["graph_id"],
        "graph_revision": amended["graph_revision"],
        "graph_digest": amended["graph_digest"],
    }
    assert projection["carry_forward_records"][0]["new_node_ref"][
        "node_digest"
    ] == carried["node_digest"]
    assert kernel.state.projections[
        f"{MULTICOMPONENT_CARRY_FORWARD_STAGE}_history"
    ]["carry_forward_projections"] == [projection]


def test_selective_carry_forward_rejects_changed_input_ref() -> None:
    kernel, source, closure = _closure_fixture()
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    transition_inputs = _transition_inputs(kernel, canonical_closure)
    action = kernel.authorize_multicomponent_selective_invalidation()
    action_ref = {
        "action_id": action.action_id,
        "action_type": action.action_type.value,
        "stage": action.stage,
        "sequence": action.sequence,
        "operation": "selective_invalidation",
    }
    candidate = graph_with_selective_invalidation(
        source,
        carry_forward_action_ref=action_ref,
        **transition_inputs,
    )
    carried = candidate["synthesis_nodes"][0]
    carried["input_node_refs"][0]["node_revision"] = "forged"
    carried["node_digest"] = safe_packet_digest(
        {
            key: value
            for key, value in carried.items()
            if key
            not in {
                "node_digest",
                "dprime_validated_node_revision",
                "dprime_validated_node_digest",
            }
        }
    )
    candidate["graph_digest"] = safe_packet_digest(
        {key: value for key, value in candidate.items() if key != "graph_digest"}
    )
    forged = runkernel_canonical_graph(candidate, action_ref=action_ref)

    with pytest.raises(
        RunKernelTransitionError,
        match="candidate does not equal the exact rederived transition",
    ):
        kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"component_work_graph_v1": forged},
            )
        )


def test_selective_invalidation_rejects_carrying_affected_node() -> None:
    kernel, source, closure = _closure_fixture()
    forged = deepcopy(closure)
    forged["directly_affected_synthesis_keys"] = ["benefit_summary"]
    forged["transitively_affected_synthesis_keys"] = ["applicant_guidance"]
    forged["affected_synthesis_keys"] = [
        "benefit_summary",
        "applicant_guidance",
    ]
    forged["affected_topological_order"] = list(forged["affected_synthesis_keys"])
    forged["unaffected_active_synthesis_keys"] = ["filing_route"]
    forged = _redigest_closure(forged)
    transition_inputs = _transition_inputs(kernel, forged)

    with pytest.raises(
        ComponentWorkGraphV1Error,
        match="admitted independent semantic lineage",
    ):
        graph_with_selective_invalidation(
            source,
            carry_forward_action_ref={
                "action_id": "forged",
                "operation": "selective_invalidation",
            },
            **transition_inputs,
        )


@pytest.mark.parametrize("direct_field", ["dprime_validation_ref", "runkernel_admission_ref"])
def test_carried_node_rejects_prior_authority_as_direct_current_authority(
    direct_field: str,
) -> None:
    kernel, source, closure = _closure_fixture()
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    amended = reduce_selective_invalidation_via_runkernel(
        run_kernel=kernel,
        graph=source,
        **_transition_inputs(kernel, canonical_closure),
    )
    carried = amended["synthesis_nodes"][0]
    lineage_key = (
        "prior_synthesis_dprime_ref"
        if direct_field == "dprime_validation_ref"
        else "prior_synthesis_admission_ref"
    )
    carried[direct_field] = deepcopy(
        carried["carried_semantic_lineage"][lineage_key]
    )
    carried["node_digest"] = safe_packet_digest(
        {
            key: value
            for key, value in carried.items()
            if key
            not in {
                "node_digest",
                "dprime_validated_node_revision",
                "dprime_validated_node_digest",
            }
        }
    )
    amended["graph_digest"] = safe_packet_digest(
        {key: value for key, value in amended.items() if key != "graph_digest"}
    )

    with pytest.raises(
        ComponentWorkGraphV1Error,
        match="separate semantic lineage from current authority",
    ):
        validate_component_work_graph_v1(amended)


def test_carry_forward_projection_rejects_action_or_final_graph_mismatch() -> None:
    kernel, source, closure = _closure_fixture()
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    amended = reduce_selective_invalidation_via_runkernel(
        run_kernel=kernel,
        graph=source,
        **_transition_inputs(kernel, canonical_closure),
    )
    action_ref = amended["synthesis_nodes"][0]["current_node_authority"][
        "runkernel_carry_forward_action_ref"
    ]

    with pytest.raises(ComponentWorkGraphV1Error, match="not produced by the action"):
        build_synthesis_carry_forward_projection(
            prior_graph=source,
            final_graph=amended,
            closure=canonical_closure,
            carry_forward_action_ref={**action_ref, "action_id": "wrong"},
        )
    with pytest.raises(ComponentWorkGraphV1Error):
        build_synthesis_carry_forward_projection(
            prior_graph=source,
            final_graph=source,
            closure=canonical_closure,
            carry_forward_action_ref=action_ref,
        )
