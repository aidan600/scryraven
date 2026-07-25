"""PRODUCT-PATH-REGRESSION: Boundary B query-centered admitted inference."""

from __future__ import annotations

from copy import deepcopy

from core.analyst_query_resolution_proposal import (
    bind_analyst_query_resolution_proposal,
)
from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_STAGE,
    admit_synthesis_node_via_runkernel,
    bind_inferred_resolution_proposal_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    finalize_component_work_graph_v1,
    graph_with_scrutineer,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
)
from core.component_work_node import (
    component_work_node_v1_from_admitted_component,
)
from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    safe_packet_digest,
)
from core.multicomponent_sufficiency_consumption_runtime import (
    build_multicomponent_graph_consumption,
)
from core.run_kernel import RunKernel
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    ComponentPurpose,
    SupportKind,
)
from tests.test_multicomponent_component_work_graph_v1 import (
    REQUEST_ID,
    RUN_ID,
    _role_artifact,
    _seed_role_artifact,
    _validate_synthesis,
)


def _direct(component_id: str) -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_purpose=ComponentPurpose.SUPPORTING_PREMISE,
        user_facing_label=component_id,
        user_facing_question=f"What establishes {component_id}?",
        acceptance_criteria=("Bind the direct premise to current evidence.",),
        source_obligation_candidate_ids=(f"obligation:{component_id}",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
    )


def _inferred(
    component_id: str,
    *,
    purpose: ComponentPurpose,
    dependencies: tuple[str, ...],
    depth: int,
) -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_purpose=purpose,
        user_facing_label=component_id,
        user_facing_question=f"What follows for {component_id}?",
        acceptance_criteria=("Use only the admitted relationship.",),
        allowed_support_kinds=(SupportKind.INFERRED,),
        max_inference_depth=depth,
        dependency_component_ids=dependencies,
    )


def _node(component: AnswerComponentContract, index: int) -> dict:
    accepted = component.to_dict()
    claim = f"{component.component_id} is directly established."
    analyst_ref = {
        "role": "component_analyst",
        "artifact_id": f"analyst:{index}",
        "artifact_digest": f"analyst-digest-{index}",
    }
    dprime_ref = {
        "role": "component_dprime",
        "artifact_id": f"dprime:{index}",
        "artifact_digest": f"dprime-digest-{index}",
    }
    admission = {
        "schema_version": "multicomponent_component_admission_ref_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "action_id": f"component-admission-action:{index}",
        "accepted_contract_version": "1",
        "accepted_contract_digest": "boundary-b-contract-digest",
        "component_id": accepted["component_id"],
        "component_revision": accepted["component_revision"],
        "component_digest": accepted["component_digest"],
        "admission_status": "admitted",
        "current": True,
        "stale": False,
        "analyst_finding_ref": analyst_ref,
        "dprime_validation_ref": dprime_ref,
        "admitted_claim_ref": {
            "claim_id": f"claim:{index}",
            "claim_text": claim,
            "claim_digest": safe_packet_digest({"claim_text": claim}),
        },
        "semantic_observation_ref": {
            "observation_id": f"observation:{index}",
            "observation_digest": f"observation-digest-{index}",
        },
        "component_coverage_ref": {
            "coverage_record_id": f"coverage:{index}",
            "coverage_record_digest": f"coverage-digest-{index}",
            "coverage_state": "satisfied",
        },
        "evidence_refs": [
            {
                "evidence_ref_id": f"evidence:{index}",
                "citation_ref": f"citation:{index}",
            }
        ],
        "required_caveats": [],
        "preserved_nonclaims": [],
        "blocker_refs": [],
    }
    return component_work_node_v1_from_admitted_component(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_component_ref=accepted,
        component_admission_ref=admission,
    )


def _contract_ref(components: list[AnswerComponentContract]) -> dict:
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "1",
        "accepted_contract_digest": "boundary-b-contract-digest",
        "parent_question_meaning_record_id": "qmr:boundary-b",
        "parent_question_meaning_record_digest": "qmr-digest:boundary-b",
        "accepted_answer_component_refs": [component.to_dict() for component in components],
        "accepted_answer_component_count": len(components),
    }


def _proposal(
    *,
    artifact: dict,
    contract: dict,
    graph_ref: dict,
    target: AnswerComponentContract,
    target_key: str,
    premises: list[dict],
    conclusion: str,
    relationship: str,
    depth: int,
) -> dict:
    return bind_analyst_query_resolution_proposal(
        role_artifact=artifact,
        local_candidate={
            "classification": "inferred_conclusion",
            "local_proposal_key": f"infer:{target_key}",
            "local_target_key": target_key,
            "answer_target_ref": target.to_dict(),
            "current_admitted_premise_node_refs": sorted(
                premises,
                key=safe_packet_digest,
            ),
            "relationship_type": relationship,
            "proposed_conclusion": conclusion,
            "support_kind": "inferred",
            "proposed_semantic_inference_depth": depth,
            "current_graph_ref": graph_ref,
            "existing_specialist_handoff_refs": [],
            "assumptions": [],
            "caveats": ["Inference is limited to the admitted premises."],
            "prohibited_upgrades": ["Do not say a premise source directly states the conclusion."],
        },
        question_meaning_record_ref={
            "record_id": "qmr:boundary-b",
            "record_digest": "qmr-digest:boundary-b",
        },
        parent_contract_ref=contract,
        parent_graph_ref=graph_ref or None,
    )


def _cross_artifact(
    *,
    packet: dict,
    contract: dict,
    graph_ref: dict,
    proposals: list[dict],
) -> dict:
    artifact = _role_artifact(
        ROLE_CROSS_COMPONENT_ANALYST,
        {"synthesis_proposals": proposals},
        packet,
    )
    core = {key: deepcopy(value) for key, value in artifact.items() if key != "artifact_digest"}
    core["accepted_contract_ref"] = deepcopy(contract)
    core["graph_ref"] = deepcopy(graph_ref)
    return {**core, "artifact_digest": safe_packet_digest(core)}


def _node_ref(node: dict) -> dict:
    return {
        "node_kind": node.get("node_kind"),
        "node_id": node.get("node_id"),
        "node_revision": node.get("node_revision"),
        "node_digest": node.get("node_digest"),
        "component_id": node.get("component_id"),
        "synthesis_key": node.get("synthesis_key"),
        "status": node.get("status") or node.get("admission_status"),
        "current": node.get("current") is True,
        "stale": node.get("stale") is True,
    }


def test_fast_depth_one_inference_fulfills_target_without_searchos_recovery() -> None:
    premise_a = _direct("component:A")
    premise_b = _direct("component:B")
    target_e = _inferred(
        "component:E",
        purpose=ComponentPurpose.USER_FACING_ANSWER_TARGET,
        dependencies=("component:A", "component:B"),
        depth=1,
    )
    components = [premise_a, premise_b, target_e]
    contract = _contract_ref(components)
    nodes = [_node(premise_a, 1), _node(premise_b, 2)]
    packet = cross_component_input_packet(
        component_nodes=nodes,
        accepted_contract_ref=contract,
        accepted_component_refs=contract["accepted_answer_component_refs"],
        requested_synthesis_directive="Answer target E.",
        requested_mode="Fast",
    )
    conclusion = "Premises A and B establish target E."
    cross = _cross_artifact(
        packet=packet,
        contract=contract,
        graph_ref={},
        proposals=[
            {
                "synthesis_key": "target_E",
                "claim_text": conclusion,
                "relationship_type": "bounded_conjunction",
                "component_inputs": ["component:A", "component:B"],
                "synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ],
    )
    proposal = _proposal(
        artifact=cross,
        contract=contract,
        graph_ref={},
        target=target_e,
        target_key="target_E",
        premises=[_node_ref(node) for node in nodes],
        conclusion=conclusion,
        relationship="bounded_conjunction",
        depth=1,
    )
    graph = component_work_graph_v1_from_cross_component_artifact(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_contract_ref=contract,
        accepted_component_refs=contract["accepted_answer_component_refs"],
        requested_mode="Fast",
        requested_synthesis_directive="Answer target E.",
        component_nodes=nodes,
        cross_component_artifact=cross,
        transient_cross_input_packet=packet,
        inferred_resolution_proposals=[proposal],
    )
    assert graph["synthesis_nodes"][0]["query_resolution_proposal"] == proposal
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    kernel.state.projections[COMPONENT_WORK_GRAPH_V1_STAGE] = graph
    graph = _validate_synthesis(kernel, graph, "target_E")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="target_E",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    consumption = build_multicomponent_graph_consumption(graph)

    target = consumption["answer_target_fulfillments"][0]
    inferred = consumption["admitted_synthesis_entries"][0]
    assert target["component_id"] == "component:E"
    assert target["selected_support_kind"] == "inferred"
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert inferred["semantic_inference_depth"] == 1
    assert inferred["premise_node_refs"] == [_node_ref(node) for node in nodes]
    assert inferred["premise_component_coverage_refs"]
    assert consumption["sufficient_with_admitted_inference"] is True
    assert graph["inferred_relationship_admission_history"]
    assert not kernel.state.searchos_state
    assert not kernel.state.contract_amendment_application_projection


def test_deep_depth_two_reuses_inferred_supporting_premise_without_fake_coverage() -> None:
    premise_a = _direct("component:A")
    premise_b = _direct("component:B")
    premise_d = _direct("component:D")
    inferred_c = _inferred(
        "component:C",
        purpose=ComponentPurpose.SUPPORTING_PREMISE,
        dependencies=("component:A", "component:B"),
        depth=1,
    )
    target_e = _inferred(
        "component:E",
        purpose=ComponentPurpose.USER_FACING_ANSWER_TARGET,
        dependencies=("component:C", "component:D"),
        depth=2,
    )
    components = [premise_a, premise_b, premise_d, inferred_c, target_e]
    contract = _contract_ref(components)
    nodes = [
        _node(premise_a, 1),
        _node(premise_b, 2),
        _node(premise_d, 3),
    ]
    packet = cross_component_input_packet(
        component_nodes=nodes,
        accepted_contract_ref=contract,
        accepted_component_refs=contract["accepted_answer_component_refs"],
        requested_synthesis_directive="Establish premise C and answer target E.",
        requested_mode="Deep",
    )
    c_conclusion = "Premises A and B establish supporting premise C."
    e_conclusion = "Premise C and premise D establish answer target E."
    cross = _cross_artifact(
        packet=packet,
        contract=contract,
        graph_ref={},
        proposals=[
            {
                "synthesis_key": "premise_C",
                "claim_text": c_conclusion,
                "relationship_type": "bounded_conjunction",
                "component_inputs": ["component:A", "component:B"],
                "synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            },
            {
                "synthesis_key": "target_E",
                "claim_text": e_conclusion,
                "relationship_type": "bounded_implication",
                "component_inputs": ["component:D"],
                "synthesis_inputs": ["premise_C"],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            },
        ],
    )
    proposal_c = _proposal(
        artifact=cross,
        contract=contract,
        graph_ref={},
        target=inferred_c,
        target_key="premise_C",
        premises=[_node_ref(nodes[0]), _node_ref(nodes[1])],
        conclusion=c_conclusion,
        relationship="bounded_conjunction",
        depth=1,
    )
    graph = component_work_graph_v1_from_cross_component_artifact(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_contract_ref=contract,
        accepted_component_refs=contract["accepted_answer_component_refs"],
        requested_mode="Deep",
        requested_synthesis_directive="Establish premise C and answer target E.",
        component_nodes=nodes,
        cross_component_artifact=cross,
        transient_cross_input_packet=packet,
        inferred_resolution_proposals=[proposal_c],
    )
    assert graph["synthesis_nodes"][0]["query_resolution_proposal"] == proposal_c
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    kernel.state.projections[COMPONENT_WORK_GRAPH_V1_STAGE] = graph
    graph = _validate_synthesis(kernel, graph, "premise_C")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="premise_C",
    )
    c_node = next(item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "premise_C")
    d_node = next(item for item in graph["component_nodes"] if item["component_id"] == "component:D")
    proposal_e_artifact = deepcopy(cross)
    proposal_e_core = {key: deepcopy(value) for key, value in proposal_e_artifact.items() if key != "artifact_digest"}
    proposal_e_core["graph_ref"] = {
        "graph_id": graph["graph_id"],
        "graph_revision": graph["graph_revision"],
        "graph_digest": graph["graph_digest"],
    }
    proposal_e_core["logical_evaluation_key"] = "depth-two-current-graph"
    proposal_e_artifact = {
        **proposal_e_core,
        "artifact_digest": safe_packet_digest(proposal_e_core),
    }
    proposal_e = _proposal(
        artifact=proposal_e_artifact,
        contract=contract,
        graph_ref=proposal_e_core["graph_ref"],
        target=target_e,
        target_key="target_E",
        premises=[_node_ref(d_node), _node_ref(c_node)],
        conclusion=e_conclusion,
        relationship="bounded_implication",
        depth=2,
    )
    graph = bind_inferred_resolution_proposal_via_runkernel(
        run_kernel=kernel,
        synthesis_key="target_E",
        proposal=proposal_e,
    )
    graph = _validate_synthesis(kernel, graph, "target_E")
    scrutiny_input = scrutineer_input_packet(graph)
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed",
            "reasons": ["The depth-two relationship remains within admitted premises."],
            "challenged_synthesis_keys": [],
            "caveats": [],
            "nonclaims": [],
        },
        scrutiny_input,
        logical_evaluation_key="deep-full-case",
    )
    _seed_role_artifact(
        kernel,
        scrutiny,
        logical_evaluation_key="deep-full-case",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        role_evaluation_key="deep-full-case",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=scrutiny,
        ),
    )
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="target_E",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    consumption = build_multicomponent_graph_consumption(graph)
    by_key = {item["synthesis_key"]: item for item in consumption["admitted_synthesis_entries"]}

    assert set(by_key) == {"premise_C", "target_E"}, {
        "entries": by_key,
        "graph_status": graph["graph_status"],
        "suppressed": graph["graph_output_suppressed"],
        "nodes": [(item["synthesis_key"], item["status"]) for item in graph["synthesis_nodes"]],
    }
    assert by_key["premise_C"]["semantic_inference_depth"] == 1
    assert by_key["target_E"]["semantic_inference_depth"] == 2
    assert by_key["premise_C"]["answer_target_component_id"] == "component:C"
    assert by_key["target_E"]["answer_target_component_id"] == "component:E"
    assert by_key["premise_C"].get("component_coverage_ref") in (None, {})
    premise_readiness = {item["component_id"]: item for item in consumption["supporting_premise_readiness"]}
    assert premise_readiness["component:C"]["fulfillment_status"] == ("fulfilled_inferred")
    assert consumption["answer_target_fulfillments"][0]["fulfillment_status"] == "fulfilled_inferred"
    assert consumption["sufficient_with_admitted_inference"] is True
