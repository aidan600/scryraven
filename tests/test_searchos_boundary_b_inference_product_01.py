"""PRODUCT-PATH-REGRESSION: Boundary B query-centered admitted inference."""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.analyst_query_resolution_proposal import (
    bind_analyst_query_resolution_proposal,
)
from core.component_work_graph_v1 import (
    COMPONENT_WORK_GRAPH_V1_STAGE,
    admit_synthesis_node_via_runkernel,
    bind_inferred_resolution_proposal_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    current_graph_reconciliation_input_packet,
    current_graph_reconciliation_required,
    finalize_component_work_graph_v1,
    graph_with_scrutineer,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
)
from core.component_work_node import (
    component_work_node_v1_from_admitted_component,
)
from core.final_answer_packet import FinalAnswerPacket
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


def _valid_fap_inferred_entry(*, carried: bool = False) -> dict:
    premise_ref = {
        "node_id": "node:A",
        "status": "admitted",
        "current": True,
        "stale": False,
    }
    coverage_ref = {
        "coverage_record_id": "coverage:A",
        "coverage_record_digest": "coverage-digest:A",
    }
    proposal_ref = {
        "proposal_id": "proposal:target_E",
        "proposal_digest": "proposal-digest:target_E",
        "stable_replay_key": "aqrp:target_E",
    }
    entry = {
        "entry_kind": "admitted_synthesis",
        "synthesis_key": "target_E",
        "synthesis_depth": 1,
        "claim_text": "Target E follows from exact premises A and B.",
        "claim_id": "claim:target_E",
        "claim_digest": "claim-digest:target_E",
        "relationship_type": "bounded_conjunction",
        "status": "admitted",
        "current": True,
        "stale": False,
        "input_node_refs": [],
        "dprime_validation_ref": {
            "artifact_id": "synthesis-dprime:target_E",
            "artifact_digest": "synthesis-dprime-digest:target_E",
        },
        "runkernel_admission_ref": {
            "action_id": "synthesis-admission:target_E",
        },
        "carried_semantic_lineage": {},
        "current_node_authority": {},
        "support_kind": "inferred",
        "semantic_inference_depth": 1,
        "answer_target_component_id": "component:E",
        "answer_target_ref": {"component_id": "component:E"},
        "premise_node_refs": [premise_ref],
        "premise_component_coverage_refs": [coverage_ref],
        "inferred_relationship_admission_ref": {
            "relationship_admission_id": "relationship:target_E",
            "relationship_admission_digest": ("relationship-digest:target_E"),
            "answer_target_component_id": "component:E",
            "semantic_inference_depth": 1,
            "support_kind": "inferred",
            "query_resolution_proposal_ref": dict(proposal_ref),
            "premise_node_ref_digests": [safe_packet_digest(premise_ref)],
            "premise_component_coverage_ref_digests": [safe_packet_digest(coverage_ref)],
            "synthesis_dprime_validation_ref": {
                "artifact_id": "synthesis-dprime:target_E",
                "artifact_digest": ("synthesis-dprime-digest:target_E"),
            },
            "runkernel_graph_admission_action_ref": {
                "action_id": "synthesis-admission:target_E",
            },
        },
        "query_resolution_proposal_ref": dict(proposal_ref),
        "target_fulfillment_status": "admitted_inferred",
        "target_local_semantic_observation_ref": {},
        "target_local_component_coverage_ref": {},
    }
    if carried:
        entry["dprime_validation_ref"] = {}
        entry["runkernel_admission_ref"] = {}
        entry["carried_semantic_lineage"] = {
            "prior_cross_component_analyst_ref": {
                "artifact_id": "prior-cross",
            },
            "prior_synthesis_claim_ref": {
                "claim_id": "prior-claim",
            },
            "prior_synthesis_dprime_ref": {
                "artifact_id": "prior-dprime",
            },
            "prior_synthesis_admission_ref": {
                "action_id": "prior-admission",
            },
        }
        entry["current_node_authority"] = {
            "runkernel_carry_forward_action_ref": {
                "operation": "selective_invalidation",
                "action_id": "carry:target_E",
            }
        }
        entry["inferred_relationship_admission_ref"]["synthesis_dprime_validation_ref"] = dict(
            entry["carried_semantic_lineage"]["prior_synthesis_dprime_ref"]
        )
        entry["inferred_relationship_admission_ref"]["runkernel_graph_admission_action_ref"] = dict(
            entry["carried_semantic_lineage"]["prior_synthesis_admission_ref"]
        )
    return entry


def _fap_with_inferred(entry: dict) -> FinalAnswerPacket:
    return FinalAnswerPacket(
        packet_id="fap:boundary-b-inferred",
        admitted_synthesis_entries=(entry,),
        multicomponent_graph_readiness="ready",
    )


def test_fap_requires_base_authority_plus_exact_inferred_shape() -> None:
    fresh = _valid_fap_inferred_entry()
    carried = _valid_fap_inferred_entry(carried=True)
    assert _fap_with_inferred(fresh).admitted_synthesis_entries
    assert _fap_with_inferred(carried).admitted_synthesis_entries

    invalid_entries: list[dict] = []
    for key in ("dprime_validation_ref", "runkernel_admission_ref"):
        invalid = deepcopy(fresh)
        invalid[key] = {}
        invalid_entries.append(invalid)
    incomplete_relationship = deepcopy(fresh)
    incomplete_relationship["inferred_relationship_admission_ref"].pop("relationship_admission_digest")
    invalid_entries.append(incomplete_relationship)
    wrong_target = deepcopy(fresh)
    wrong_target["inferred_relationship_admission_ref"]["answer_target_component_id"] = "component:other"
    invalid_entries.append(wrong_target)
    wrong_depth = deepcopy(fresh)
    wrong_depth["inferred_relationship_admission_ref"]["semantic_inference_depth"] = 2
    invalid_entries.append(wrong_depth)
    wrong_support = deepcopy(fresh)
    wrong_support["inferred_relationship_admission_ref"]["support_kind"] = "direct"
    invalid_entries.append(wrong_support)
    wrong_proposal_lineage = deepcopy(fresh)
    wrong_proposal_lineage["inferred_relationship_admission_ref"]["query_resolution_proposal_ref"][
        "proposal_digest"
    ] = "proposal-digest:other"
    invalid_entries.append(wrong_proposal_lineage)
    wrong_premise_lineage = deepcopy(fresh)
    wrong_premise_lineage["inferred_relationship_admission_ref"]["premise_node_ref_digests"] = ["premise-digest:other"]
    invalid_entries.append(wrong_premise_lineage)
    target_observation = deepcopy(fresh)
    target_observation["target_local_semantic_observation_ref"] = {"observation_id": "forbidden"}
    invalid_entries.append(target_observation)
    target_coverage = deepcopy(fresh)
    target_coverage["target_local_component_coverage_ref"] = {"coverage_record_id": "forbidden"}
    invalid_entries.append(target_coverage)
    invalid_carried = deepcopy(carried)
    invalid_carried["carried_semantic_lineage"] = {}
    invalid_entries.append(invalid_carried)

    for invalid in invalid_entries:
        with pytest.raises(
            ValueError,
            match="synthesis entry is not current RunKernel-admitted state",
        ):
            _fap_with_inferred(invalid)


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
        "premise_C",
        purpose=ComponentPurpose.SUPPORTING_PREMISE,
        dependencies=("component:A", "component:B"),
        depth=1,
    )
    target_e = _inferred(
        "target_E",
        purpose=ComponentPurpose.USER_FACING_ANSWER_TARGET,
        dependencies=("premise_C", "component:D"),
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
    assert current_graph_reconciliation_required(graph) is True
    reconciliation_packet = current_graph_reconciliation_input_packet(
        graph,
        requested_mode="Deep",
    )
    assert reconciliation_packet["graph_ref"] == {
        "graph_id": graph["graph_id"],
        "graph_revision": graph["graph_revision"],
        "graph_digest": graph["graph_digest"],
    }
    assert reconciliation_packet["requested_synthesis_directive"] == ("Establish premise C and answer target E.")
    synthesis_by_key = {item["synthesis_key"]: item for item in reconciliation_packet["current_synthesis_nodes"]}
    assert synthesis_by_key["premise_C"]["status"] == "admitted"
    assert synthesis_by_key["target_E"]["status"] == "proposed"
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
    assert by_key["premise_C"]["answer_target_component_id"] == "premise_C"
    assert by_key["target_E"]["answer_target_component_id"] == "target_E"
    assert by_key["premise_C"].get("component_coverage_ref") in (None, {})
    premise_readiness = {item["component_id"]: item for item in consumption["supporting_premise_readiness"]}
    assert premise_readiness["premise_C"]["fulfillment_status"] == ("fulfilled_inferred")
    assert consumption["answer_target_fulfillments"][0]["fulfillment_status"] == "fulfilled_inferred"
    assert consumption["sufficient_with_admitted_inference"] is True
