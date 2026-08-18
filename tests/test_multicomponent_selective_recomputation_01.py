"""PRODUCT-PATH-REGRESSION: selective recovery recomputation authority."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from core.component_work_graph_v1 import (
    MULTICOMPONENT_CARRY_FORWARD_STAGE,
    MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
    ComponentWorkGraphV1Error,
    admit_synthesis_node_via_runkernel,
    build_synthesis_carry_forward_projection,
    component_work_graph_v1_from_cross_component_artifact,
    component_work_graph_v1_selective_resynthesis_from_cross_artifact,
    cross_component_input_packet,
    derive_selective_recomputation_closure,
    finalize_component_work_graph_v1,
    graph_with_scrutineer,
    graph_with_selective_invalidation,
    reduce_component_work_graph_v1,
    reduce_selective_invalidation_via_runkernel,
    reduce_selective_recomputation_closure,
    runkernel_canonical_graph,
    scrutineer_input_packet,
    selective_cross_component_input_packet,
    validate_component_work_graph_v1,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
    SELECTIVE_CROSS_COMPONENT_SCHEMA,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    _execute_selective_reconstruction,
)
from core.run_kernel import (
    Observation,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
    contract_amendment_graph_transition_authority,
)
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.test_multicomponent_component_work_graph_v1 import (
    REQUEST_ID,
    RUN_ID,
    _component_node,
    _role_artifact,
    _seed_component_admission,
    _seed_role_artifact,
    _validate_synthesis,
)

GRAPH_TRANSITION_AUTHORITY_STAGE = (
    "contract_amendment_graph_transition_authority"
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
                    "claim_text": (
                        "The rebate and income threshold define the verified "
                        "two-part Northstar benefit."
                    ),
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
        transient_cross_input_packet=cross_input,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(
        kernel,
        nodes,
        cross_artifact=cross,
        requested_synthesis_directive=directive,
    )
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
    amendment_admission = {
        "amendment_record_id": "amendment:test",
        "amendment_record_digest": "amendment-record-digest",
        "authorized_action_id": "amendment-admission-action:test",
        "admission_digest": "amendment-admission-digest",
        "analyst_query_resolution_proposal_ref": {
            "local_target_key": "filing_route",
        },
    }
    amendment_application = {
        "amendment_record_id": "amendment:test",
        "authorized_action_id": "amendment-application-action:test",
        "application_digest": "amendment-application-digest",
        "operations": [
                {
                    "operation_kind": "revise_component",
                    "component_id": "component:component-4",
                }
            ],
        }
    authorization = contract_amendment_graph_transition_authority(
        graph=graph,
        amendment_application=amendment_application,
        amendment_admission=amendment_admission,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
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
            "component_purpose": "user_facing_answer_target",
            "user_facing_label": item["component_label"],
            "user_facing_question": item["component_question"],
            "allowed_support_kinds": ["direct"],
            "max_inference_depth": 0,
            "source_obligation_candidate_ids": [
                f"obligation:{item['component_id']}:direct"
            ],
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
        "component_analyst_case_ref": recovered_node["component_analyst_case_ref"],
        "analyst_finding_ref": recovered_node["analyst_finding_ref"],
        "admitted_claim_ref": recovered_node["admitted_claim_ref"],
        "semantic_observation_ref": recovered_node["semantic_observation_ref"],
        "component_coverage_ref": recovered_node["component_coverage_ref"],
        "evidence_refs": recovered_node["evidence_refs"],
        "required_caveats": recovered_node["required_caveats"],
        "preserved_nonclaims": recovered_node["preserved_nonclaims"],
        "blocker_refs": recovered_node["blocker_refs"],
    }
    kernel.state.projections[GRAPH_TRANSITION_AUTHORITY_STAGE] = authorization
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
        contract_amendment_admission_ref={
            key: amendment_admission[key]
            for key in (
                "amendment_record_id",
                "amendment_record_digest",
                "authorized_action_id",
                "admission_digest",
            )
        },
        contract_amendment_application_ref={
            key: amendment_application[key]
            for key in (
                "amendment_record_id",
                "authorized_action_id",
                "application_digest",
            )
        },
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
            GRAPH_TRANSITION_AUTHORITY_STAGE
        ],
        "contract_amendment_admission_ref": closure[
            "contract_amendment_admission_ref"
        ],
        "amendment_application_ref": closure[
            "contract_amendment_application_ref"
        ],
        "accepted_component_refs": kernel.state.current_answer_contract[
            "accepted_answer_component_refs"
        ],
    }


def _selectively_invalidated_graph() -> tuple[RunKernel, dict, dict, dict]:
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
    return kernel, source, canonical_closure, amended


def _selective_response(packet: dict) -> dict:
    recovered_id = packet["current_recovered_component_ref"]["component_id"]
    other_ids = [
        item["component_id"]
        for item in packet["licensed_current_component_refs"]
    ]
    boundary_by_key = {
        item["synthesis_key"]: item
        for item in packet["preserved_boundary_synthesis_catalog"]
    }
    benefit_claim = boundary_by_key["benefit_summary"]["claim_text"]
    if "verified two-part Northstar benefit" not in benefit_claim:
        raise AssertionError("selective fixture did not receive preserved semantics")
    applicant_guidance_claim = (
        f"Using {benefit_claim}, applicants should follow the fresh filing route."
    )
    return {
        "synthesis_proposals": [
            {
                "synthesis_key": "filing_route",
                "claim_text": (
                    "The ordinary inputs permit online filing, while income-bonus "
                    "claimants must use the paper application."
                ),
                "relationship_type": "conditional_filing_route",
                "component_inputs": [*other_ids, recovered_id],
                "affected_synthesis_inputs": [],
                "preserved_synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            },
            {
                "synthesis_key": "applicant_guidance",
                "claim_text": applicant_guidance_claim,
                "relationship_type": "guided_conjunction",
                "component_inputs": [],
                "affected_synthesis_inputs": ["filing_route"],
                "preserved_synthesis_inputs": ["benefit_summary"],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            },
        ]
    }


def _execute_selective_cross(
    kernel: RunKernel,
    graph: dict,
    closure: dict,
    response: dict,
) -> tuple[dict, dict]:
    packet = selective_cross_component_input_packet(graph, closure=closure)
    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=packet,
        strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
            lambda *_args, **_kwargs: json.dumps(response),
            canonical_provider="OpenAI",
            model="gpt-5.4",
        ),
        clean_json_response=lambda value: value,
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
        logical_evaluation_key=f"selective:graph-revision:{graph['graph_revision']}",
        output_schema_variant=SELECTIVE_CROSS_COMPONENT_SCHEMA,
    )
    return packet, artifact


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
    kernel, graph, closure = _closure_fixture()
    authorization = deepcopy(kernel.state.projections[
        GRAPH_TRANSITION_AUTHORITY_STAGE
    ])
    authorization["graph_revision"] += 1

    with pytest.raises(
        ComponentWorkGraphV1Error,
        match="authorization-bound source graph",
    ):
        derive_selective_recomputation_closure(
            graph,
            recovery_authorization_ref=authorization,
            current_contract_ref=closure["current_contract_ref"],
            contract_amendment_admission_ref=closure[
                "contract_amendment_admission_ref"
            ],
            contract_amendment_application_ref=closure[
                "contract_amendment_application_ref"
            ],
            recovered_component_admission_ref=closure[
                "recovered_component_admission_ref"
            ],
        )


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


def test_selective_cross_reconstructs_only_affected_synthesis_namespaces() -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    packet = selective_cross_component_input_packet(amended, closure=closure)
    response = _selective_response(packet)
    _packet, artifact = _execute_selective_cross(
        kernel,
        amended,
        closure,
        response,
    )
    candidate = component_work_graph_v1_selective_resynthesis_from_cross_artifact(
        amended,
        closure=closure,
        cross_component_artifact=artifact,
    )
    evaluation_key = artifact["logical_evaluation_key"]
    rebuilt = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="selective_resynthesis_structure",
        graph_candidate=candidate,
        role_evaluation_key=evaluation_key,
    )

    assert packet["affected_synthesis_key_catalog"] == [
        "filing_route",
        "applicant_guidance",
    ]
    assert packet["prohibited_unaffected_synthesis_keys"] == ["benefit_summary"]
    catalog = packet["preserved_boundary_synthesis_catalog"]
    assert [item["synthesis_key"] for item in catalog] == ["benefit_summary"]
    boundary = catalog[0]
    carried = amended["synthesis_nodes"][0]
    assert boundary["node_id"] == carried["node_id"]
    assert boundary["node_revision"] == carried["node_revision"]
    assert boundary["node_digest"] == carried["node_digest"]
    assert boundary["claim_text"] == carried["claim_text"]
    assert "verified two-part Northstar benefit" in boundary["claim_text"]
    assert boundary["claim_id"] == carried["synthesis_claim_ref"]["claim_id"]
    assert boundary["claim_digest"] == carried["synthesis_claim_ref"]["claim_digest"]
    assert boundary["synthesis_claim_ref"]["claim_digest"] == carried[
        "synthesis_claim_ref"
    ]["claim_digest"]
    assert boundary["required_caveats"] == list(carried.get("required_caveats") or ())
    assert boundary["preserved_nonclaims"] == list(
        carried.get("preserved_nonclaims") or ()
    )
    assert "blocker_refs" in boundary
    assert boundary["carry_forward_action_ref"] == carried["current_node_authority"][
        "runkernel_carry_forward_action_ref"
    ]
    assert boundary["carried_semantic_lineage"] == carried["carried_semantic_lineage"]
    assert boundary["status"] == "admitted"
    assert boundary["current"] is True
    assert boundary["stale"] is False
    assert [
        item["synthesis_key"]
        for item in artifact["semantic_output"]["synthesis_proposals"]
    ] == ["filing_route", "applicant_guidance"]
    assert (
        "verified two-part Northstar benefit"
        in artifact["semantic_output"]["synthesis_proposals"][1]["claim_text"]
    )
    by_key = {item["synthesis_key"]: item for item in rebuilt["synthesis_nodes"]}
    assert set(by_key) == {
        "benefit_summary",
        "filing_route",
        "applicant_guidance",
    }
    assert by_key["benefit_summary"] == amended["synthesis_nodes"][0]
    assert by_key["applicant_guidance"]["input_namespaces"] == {
        "component_inputs": [],
        "affected_synthesis_inputs": ["filing_route"],
        "preserved_synthesis_inputs": ["benefit_summary"],
    }
    input_by_key = {
        item.get("synthesis_key"): item
        for item in by_key["applicant_guidance"]["input_node_refs"]
        if item.get("node_kind") == "synthesis"
    }
    assert input_by_key["filing_route"]["node_digest"] == by_key[
        "filing_route"
    ]["node_digest"]
    assert input_by_key["benefit_summary"]["node_digest"] == by_key[
        "benefit_summary"
    ]["node_digest"]
    assert by_key["filing_route"]["superseded_node_ref"]["synthesis_key"] == (
        "filing_route"
    )
    assert by_key["applicant_guidance"]["superseded_node_ref"][
        "synthesis_key"
    ] == "applicant_guidance"
    assert rebuilt["whole_graph_resynthesis_rounds"] == 0
    assert rebuilt["selective_recomputation_rounds"] == 1
    assert rebuilt["recomputed_synthesis_count"] == 2


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("preserved_as_fresh", "exactly the affected topological order"),
        ("affected_as_preserved", "unlicensed input namespace"),
        ("unknown_preserved", "unlicensed input namespace"),
        ("omit_affected", "exactly the affected topological order"),
        ("changed_dependency", "changed an unlicensed dependency"),
    ],
)
def test_selective_cross_rejects_unlicensed_proposal_shapes(
    mutation: str,
    message: str,
) -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    packet = selective_cross_component_input_packet(amended, closure=closure)
    response = _selective_response(packet)
    proposals = response["synthesis_proposals"]
    if mutation == "preserved_as_fresh":
        proposals.append(
            {
                **deepcopy(proposals[0]),
                "synthesis_key": "benefit_summary",
            }
        )
    elif mutation == "affected_as_preserved":
        proposals[1]["affected_synthesis_inputs"] = []
        proposals[1]["preserved_synthesis_inputs"] = [
            "benefit_summary",
            "filing_route",
        ]
    elif mutation == "unknown_preserved":
        proposals[1]["preserved_synthesis_inputs"] = ["unknown_boundary"]
    elif mutation == "omit_affected":
        proposals.pop()
    else:
        proposals[0]["component_inputs"] = proposals[0]["component_inputs"][:-1]
    _packet, artifact = _execute_selective_cross(
        kernel,
        amended,
        closure,
        response,
    )

    with pytest.raises(ComponentWorkGraphV1Error, match=message):
        component_work_graph_v1_selective_resynthesis_from_cross_artifact(
            amended,
            closure=closure,
            cross_component_artifact=artifact,
        )


def test_selective_cross_schema_rejects_overlapping_synthesis_namespaces() -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    packet = selective_cross_component_input_packet(amended, closure=closure)
    response = _selective_response(packet)
    response["synthesis_proposals"][1]["preserved_synthesis_inputs"].append(
        "filing_route"
    )

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="namespaces must be disjoint",
    ):
        _execute_selective_cross(kernel, amended, closure, response)


def test_selective_reconstruction_calls_cross_and_dprime_only_for_affected_keys() -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    carried_before = deepcopy(amended["synthesis_nodes"][0])

    def ask_model(prompt: str, system_prompt: str, **_kwargs):
        import json

        packet = json.loads(prompt)
        if system_prompt == SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT:
            return json.dumps(_selective_response(packet))
        if system_prompt == ROLE_SYSTEM_PROMPTS["synthesis_dprime"]:
            return json.dumps(
                {
                    "validation_status": "supported",
                    "reasons": ["The exact current inputs support the proposal."],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        raise AssertionError(f"unexpected selective role prompt: {system_prompt}")

    rebuilt, deferred = _execute_selective_reconstruction(
        run_kernel=kernel,
        graph=amended,
        closure=closure,
        role_kwargs={
            "strict_one_shot_transport": wrap_text_callable_as_strict_one_shot_transport(
                ask_model,
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            "clean_json_response": lambda value: value,
            "provider": "OpenAI",
            "model": "gpt-5.4",
            "use_reasoning": False,
        },
    )

    by_key = {item["synthesis_key"]: item for item in rebuilt["synthesis_nodes"]}
    assert by_key["benefit_summary"] == carried_before
    assert by_key["filing_route"]["status"] == "admitted"
    assert by_key["applicant_guidance"]["status"] == "validated"
    assert deferred == ["applicant_guidance"]
    selective_role_actions = [
        item
        for item in kernel.state.issued_actions.values()
        if item.inputs.get("logical_evaluation_key")
        and (
            ":selective:" in item.inputs["logical_evaluation_key"]
            or item.inputs["logical_evaluation_key"].startswith("selective:")
        )
    ]
    assert [item.inputs["role"] for item in selective_role_actions] == [
        "cross_component_analyst",
        "synthesis_dprime",
        "synthesis_dprime",
    ]
    dprime_keys = [
        item.inputs["logical_evaluation_key"]
        for item in selective_role_actions
        if item.inputs["role"] == "synthesis_dprime"
    ]
    assert len(dprime_keys) == 2
    assert all("graph-revision:" in item for item in dprime_keys)
    assert any(item.startswith("filing_route:") for item in dprime_keys)
    assert any(item.startswith("applicant_guidance:") for item in dprime_keys)
    assert all(not item.startswith("benefit_summary:") for item in dprime_keys)


def test_boundary_b_product_path_selectively_reproves_and_finalizes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime
    import core.pipeline_orchestrator as orchestrator
    from core.cost_accounting import CostAccumulator
    from core.protocols import NullStatusWriter
    from tests.helpers.offline_ordinary_pipeline import (
        HANDOFF_AUTHOR,
        HANDOFF_PACKET,
        HANDOFF_SEMANTIC,
        HANDOFF_SUFFICIENCY,
        install_handoff_capture,
        offline_balanced_run_config,
        scrub_offline_runtime,
    )
    from tests.test_searchos_boundary_b_ordinary_product_01 import (
        UNIQUE_RECOVERED_RESULT,
        BoundaryBOrdinaryHarness,
    )

    def forbidden_whole_graph_rebuild(**_kwargs):
        raise AssertionError("ordinary successful recovery invoked whole-graph rebuild")

    monkeypatch.setattr(
        runtime,
        "_execute_fresh_resynthesis",
        forbidden_whole_graph_rebuild,
    )
    scrub_offline_runtime(monkeypatch)

    def forbidden_direct_semantic_producer(*_args, **_kwargs):
        raise AssertionError(
            "qualifying multicomponent run cannot use direct semantic authority"
        )

    monkeypatch.setattr(
        runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        forbidden_direct_semantic_producer,
    )
    harness = BoundaryBOrdinaryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="selective-northstar-session",
            run_id="selective-northstar-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    graph = kernel.state.projections["multicomponent_component_work_graph_v1"]
    closure = kernel.state.projections[MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE]
    carry = kernel.state.projections[MULTICOMPONENT_CARRY_FORWARD_STAGE]
    assert closure["directly_affected_synthesis_keys"] == ["target_E"]
    assert closure["transitively_affected_synthesis_keys"] == []
    assert closure["affected_synthesis_keys"] == ["target_E"]
    assert closure["unaffected_active_synthesis_keys"] == []
    closure_action = next(
        item
        for item in kernel.state.issued_actions.values()
        if item.inputs.get("operation") == "selective_closure"
    )
    invalidation_action = next(
        item
        for item in kernel.state.issued_actions.values()
        if item.inputs.get("operation") == "selective_invalidation"
    )
    assert closure_action.sequence < invalidation_action.sequence
    by_key = {item["synthesis_key"]: item for item in graph["synthesis_nodes"]}
    assert set(by_key) == {"target_E"}
    assert carry["carry_forward_count"] == 0
    assert carry["carry_forward_records"] == []
    assert carry["final_graph_ref"]["graph_digest"] != graph["graph_digest"]
    stale_keys = {
        item["superseded_node_ref"]["synthesis_key"]
        for item in graph["stale_synthesis_history"]
    }
    assert stale_keys == {"target_E"}
    assert by_key["target_E"]["superseded_node_ref"]["synthesis_key"] == (
        "target_E"
    )
    recovered_component_ids = {
        item["component_id"]
        for item in graph["component_nodes"]
        if item["component_id"] != "premise_D"
    }
    assert len(recovered_component_ids) == 1
    assert by_key["target_E"]["input_namespaces"] == {
        "component_inputs": [
            *sorted(recovered_component_ids),
            "premise_D",
        ],
        "affected_synthesis_inputs": [],
        "preserved_synthesis_inputs": [],
    }
    selective_cross = next(
        item
        for stage, item in kernel.state.projections.items()
        if stage.startswith("multicomponent_role:cross_component_analyst:selective:")
    )
    assert [
        item["synthesis_key"]
        for item in selective_cross["semantic_output"]["synthesis_proposals"]
    ] == ["target_E"]
    selective_dprime_actions = [
        item
        for item in kernel.state.issued_actions.values()
        if item.inputs.get("role") == "synthesis_dprime"
        and ":selective:" in str(item.inputs.get("logical_evaluation_key"))
    ]
    assert len(selective_dprime_actions) == 1
    assert str(
        selective_dprime_actions[0].inputs["logical_evaluation_key"]
    ).startswith("target_E:")
    scrutineer_actions = [
        item
        for item in kernel.state.issued_actions.values()
        if item.inputs.get("role") == "scrutineer"
    ]
    assert len(scrutineer_actions) == 2
    assert str(scrutineer_actions[-1].inputs["logical_evaluation_key"]).startswith(
        "full-case:selective:graph-revision:"
    )
    assert graph["graph_status"] == "ready"
    assert graph["whole_graph_resynthesis_rounds"] == 0
    assert graph["selective_recomputation_rounds"] == 1
    assert graph["logical_accounting"] == {
        "component_analyst_evaluations": 2,
        "cross_component_analyst_evaluations": 2,
        "synthesis_dprime_evaluations": 2,
        "scrutineer_evaluations": 2,
    }
    sufficiency = captured["sufficiency_projection"]
    assert sufficiency["final_answer_allowed"] is True
    packet = captured["packet_handoff"].packet
    assert len(packet.direct_component_entries) == 2
    assert {
        item["synthesis_key"] for item in packet.admitted_synthesis_entries
    } == {"target_E"}
    assert captured["author_handoff_called"] is True
    normalized = " ".join(outcome.report.split())
    assert UNIQUE_RECOVERED_RESULT in normalized
    assert any(
        UNIQUE_RECOVERED_RESULT in str(item.get("claim_text") or "")
        for item in packet.admitted_synthesis_entries
    )
    assert harness.forbidden_live_calls == []


def test_closure_cannot_be_derived_after_selective_topology_replacement() -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()

    with pytest.raises(
        ComponentWorkGraphV1Error,
        match="authorization-bound source graph",
    ):
        derive_selective_recomputation_closure(
            amended,
            recovery_authorization_ref=kernel.state.projections[
                GRAPH_TRANSITION_AUTHORITY_STAGE
            ],
            current_contract_ref=closure["current_contract_ref"],
            contract_amendment_admission_ref=closure[
                "contract_amendment_admission_ref"
            ],
            contract_amendment_application_ref=closure[
                "contract_amendment_application_ref"
            ],
            recovered_component_admission_ref=closure[
                "recovered_component_admission_ref"
            ],
        )


def test_selective_packet_rejects_stale_preserved_boundary() -> None:
    _kernel, _source, closure, amended = _selectively_invalidated_graph()
    carried = amended["synthesis_nodes"][0]
    carried["current"] = False
    carried["stale"] = True
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
        selective_cross_component_input_packet(amended, closure=closure)


@pytest.mark.parametrize(
    "mutation",
    [
        "forged_claim_text",
        "forged_claim_digest",
        "forged_claim_ref",
        "stale_identity",
        "missing_lineage",
        "wrong_carry_forward",
    ],
)
def test_selective_rejects_tampered_preserved_boundary_packet(mutation: str) -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    packet = selective_cross_component_input_packet(amended, closure=closure)
    response = _selective_response(packet)
    tampered = deepcopy(packet)
    boundary = tampered["preserved_boundary_synthesis_catalog"][0]
    if mutation == "forged_claim_text":
        boundary["claim_text"] = "Forged preserved benefit claim text."
        boundary["synthesis_claim_ref"] = {
            **dict(boundary.get("synthesis_claim_ref") or {}),
            "claim_text": boundary["claim_text"],
        }
    elif mutation == "forged_claim_digest":
        boundary["claim_digest"] = "forged-claim-digest"
        boundary["synthesis_claim_ref"] = {
            **dict(boundary.get("synthesis_claim_ref") or {}),
            "claim_digest": "forged-claim-digest",
        }
    elif mutation == "forged_claim_ref":
        boundary["synthesis_claim_ref"] = {
            **dict(boundary.get("synthesis_claim_ref") or {}),
            "claim_id": "forged-claim-id",
        }
    elif mutation == "stale_identity":
        boundary["node_revision"] = "0"
        boundary["node_digest"] = "stale-node-digest"
    elif mutation == "missing_lineage":
        boundary.pop("carried_semantic_lineage", None)
    else:
        boundary["carry_forward_action_ref"] = {
            **dict(boundary.get("carry_forward_action_ref") or {}),
            "action_id": "wrong-carry-forward-action",
        }

    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=ROLE_CROSS_COMPONENT_ANALYST,
        input_packet=tampered,
        strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
            lambda *_args, **_kwargs: json.dumps(response),
            canonical_provider="OpenAI",
            model="gpt-5.4",
        ),
        clean_json_response=lambda value: value,
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
        logical_evaluation_key=(
            f"selective-tamper:graph-revision:{amended['graph_revision']}"
        ),
        output_schema_variant=SELECTIVE_CROSS_COMPONENT_SCHEMA,
    )

    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        component_work_graph_v1_selective_resynthesis_from_cross_artifact(
            amended,
            closure=closure,
            cross_component_artifact=artifact,
        )


def test_unrelated_carried_synthesis_is_excluded_from_preserved_boundary() -> None:
    nodes = [_component_node(index) for index in range(1, 5)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain benefits, filing route, applicant guidance, and a side note."
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
                    "claim_text": (
                        "The rebate and income threshold define the verified "
                        "two-part Northstar benefit."
                    ),
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
                    "synthesis_key": "unrelated_note",
                    "claim_text": "An independent unrelated note stays aside.",
                    "relationship_type": "independent_note",
                    "component_inputs": ["component:component-1"],
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
        transient_cross_input_packet=cross_input,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(
        kernel,
        nodes,
        cross_artifact=cross,
        requested_synthesis_directive=directive,
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    for key in ("benefit_summary", "unrelated_note"):
        graph = _validate_synthesis(kernel, graph, key)
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="benefit_summary",
    )
    scrutiny_input = scrutineer_input_packet(graph)
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed",
            "reasons": ["Independent unrelated note is coherent with the graph."],
            "challenged_synthesis_keys": [],
            "caveats": [],
            "nonclaims": [],
        },
        scrutiny_input,
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(
        kernel,
        scrutiny,
        logical_evaluation_key="full-case",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=scrutiny,
        ),
    )
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="unrelated_note",
    )

    amendment_admission = {
        "amendment_record_id": "amendment:unrelated",
        "amendment_record_digest": "amendment-record-digest-unrelated",
        "authorized_action_id": "amendment-admission-action:unrelated",
        "admission_digest": "amendment-admission-digest-unrelated",
        "analyst_query_resolution_proposal_ref": {
            "local_target_key": "filing_route",
        },
    }
    amendment_application = {
        "amendment_record_id": "amendment:unrelated",
        "authorized_action_id": "amendment-application-action:unrelated",
        "application_digest": "amendment-application-digest-unrelated",
        "operations": [
                {
                    "operation_kind": "revise_component",
                    "component_id": "component:component-4",
                }
            ],
        }
    authorization = contract_amendment_graph_transition_authority(
        graph=graph,
        amendment_application=amendment_application,
        amendment_admission=amendment_admission,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
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
            "component_purpose": "user_facing_answer_target",
            "user_facing_label": item["component_label"],
            "user_facing_question": item["component_question"],
            "allowed_support_kinds": ["direct"],
            "max_inference_depth": 0,
            "source_obligation_candidate_ids": [
                f"obligation:{item['component_id']}:direct"
            ],
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
    recovered_admission = {
        "schema_version": "multicomponent_component_admission_ref_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "component_id": recovered_node["component_id"],
        "component_revision": recovered_node["component_revision"],
        "component_digest": recovered_node["component_digest"],
        "accepted_contract_version": current_contract["accepted_contract_version"],
        "accepted_contract_digest": current_contract["accepted_contract_digest"],
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "action_id": recovered_node["component_admission_action_ref"]["action_id"],
        "component_analyst_case_ref": recovered_node["component_analyst_case_ref"],
        "analyst_finding_ref": recovered_node["analyst_finding_ref"],
        "admitted_claim_ref": recovered_node["admitted_claim_ref"],
        "semantic_observation_ref": recovered_node["semantic_observation_ref"],
        "component_coverage_ref": recovered_node["component_coverage_ref"],
        "evidence_refs": recovered_node["evidence_refs"],
        "required_caveats": recovered_node["required_caveats"],
        "preserved_nonclaims": recovered_node["preserved_nonclaims"],
        "blocker_refs": recovered_node["blocker_refs"],
    }
    kernel.state.projections[GRAPH_TRANSITION_AUTHORITY_STAGE] = authorization
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
        contract_amendment_admission_ref={
            key: amendment_admission[key]
            for key in (
                "amendment_record_id",
                "amendment_record_digest",
                "authorized_action_id",
                "admission_digest",
            )
        },
        contract_amendment_application_ref={
            key: amendment_application[key]
            for key in (
                "amendment_record_id",
                "authorized_action_id",
                "application_digest",
            )
        },
        recovered_component_admission_ref=recovered_admission,
    )
    canonical_closure = reduce_selective_recomputation_closure(
        run_kernel=kernel,
        closure_candidate=closure,
    )
    amended = reduce_selective_invalidation_via_runkernel(
        run_kernel=kernel,
        graph=graph,
        **_transition_inputs(kernel, canonical_closure),
    )

    assert canonical_closure["unaffected_active_synthesis_keys"] == [
        "benefit_summary",
        "unrelated_note",
    ]
    assert {item["synthesis_key"] for item in amended["synthesis_nodes"]} == {
        "benefit_summary",
        "unrelated_note",
    }
    packet = selective_cross_component_input_packet(amended, closure=canonical_closure)
    assert [
        item["synthesis_key"] for item in packet["preserved_boundary_synthesis_catalog"]
    ] == ["benefit_summary"]
    assert packet["prohibited_unaffected_synthesis_keys"] == [
        "benefit_summary",
        "unrelated_note",
    ]


def test_selective_finalization_rejects_prior_scrutineer_authority() -> None:
    kernel, _source, closure, amended = _selectively_invalidated_graph()
    packet = selective_cross_component_input_packet(amended, closure=closure)
    _packet, artifact = _execute_selective_cross(
        kernel,
        amended,
        closure,
        _selective_response(packet),
    )
    candidate = component_work_graph_v1_selective_resynthesis_from_cross_artifact(
        amended,
        closure=closure,
        cross_component_artifact=artifact,
    )
    rebuilt = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="selective_resynthesis_structure",
        graph_candidate=candidate,
        role_evaluation_key=artifact["logical_evaluation_key"],
    )
    rebuilt["scrutineer_status"] = "passed"
    rebuilt["scrutineer_ref"] = {
        "artifact_id": "prior-scrutineer",
        "artifact_digest": "prior-scrutineer-digest",
        "logical_evaluation_key": "full-case",
    }
    rebuilt["graph_digest"] = safe_packet_digest(
        {key: value for key, value in rebuilt.items() if key != "graph_digest"}
    )

    finalized = finalize_component_work_graph_v1(rebuilt)

    assert finalized["graph_status"] == "missing_required_scrutiny"
    assert finalized["graph_output_suppressed"] is True


def test_second_selective_recomputation_round_is_rejected() -> None:
    kernel, _source, _closure, _amended = _selectively_invalidated_graph()

    with pytest.raises(RunKernelTransitionError):
        kernel.authorize_multicomponent_selective_invalidation()


def test_selective_failure_blocks_without_whole_graph_fallback(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.ordinary_multicomponent_synthesis_runtime as runtime
    import core.pipeline_orchestrator as orchestrator
    from core.cost_accounting import CostAccumulator
    from core.protocols import NullStatusWriter
    from tests.helpers.offline_ordinary_pipeline import (
        HANDOFF_AUTHOR,
        HANDOFF_SEMANTIC,
        install_handoff_capture,
        offline_balanced_run_config,
        scrub_offline_runtime,
    )
    from tests.test_searchos_boundary_b_ordinary_product_01 import (
        BoundaryBOrdinaryHarness,
    )

    whole_graph_called = False

    def fail_selective(*_args, **_kwargs):
        raise ComponentWorkGraphV1Error("forced selective proof failure")

    def observe_whole_graph(**_kwargs):
        nonlocal whole_graph_called
        whole_graph_called = True
        raise AssertionError("whole-graph fallback is forbidden")

    monkeypatch.setattr(
        runtime,
        "component_work_graph_v1_selective_resynthesis_from_cross_artifact",
        fail_selective,
    )
    monkeypatch.setattr(runtime, "_execute_fresh_resynthesis", observe_whole_graph)
    scrub_offline_runtime(monkeypatch)

    def forbid_direct_semantic_producer(*_args, **_kwargs):
        raise AssertionError("direct semantic fallback is forbidden")

    monkeypatch.setattr(
        runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        forbid_direct_semantic_producer,
    )
    harness = BoundaryBOrdinaryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SEMANTIC, HANDOFF_AUTHOR),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-11",
            session_id="selective-failure-session",
            run_id="selective-failure-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["semantic_run_kernel"]
    terminals = kernel.state.searchos_state["recovery_cycle_terminal_history"]
    assert len(terminals) == 1
    assert terminals[0]["terminal_status"] == "failed"
    assert "multicomponent_dynamic_recovery" not in kernel.state.projections
    assert whole_graph_called is False
    assert captured["author_handoff_called"] is False
    assert "could not produce a supported answer" in outcome.report.casefold()
