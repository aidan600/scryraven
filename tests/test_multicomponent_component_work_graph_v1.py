"""PRODUCT-PATH-REGRESSION: bounded ordinary ComponentWorkGraph V1 authority."""

from __future__ import annotations

import pytest

from core.component_work_graph_v1 import (
    ComponentWorkGraphV1Error,
    admit_synthesis_node_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    finalize_component_work_graph_v1,
    graph_with_accounting,
    graph_with_scrutineer,
    graph_with_synthesis_admission,
    graph_with_synthesis_validation,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
    synthesis_dprime_input_packet,
)
from core.component_work_node import component_work_node_v1_from_admitted_component
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    safe_packet_digest,
)
from core.run_kernel import RunKernel

RUN_ID = "run:multicomponent-graph-v1-test"
REQUEST_ID = "request:multicomponent-graph-v1-test"


def _role_artifact(role: str, semantic_output: dict, input_packet: dict) -> dict:
    core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": role,
        "artifact_id": f"artifact:{role}:{safe_packet_digest(input_packet)[:12]}",
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "input_packet_digest": safe_packet_digest(input_packet),
        "logical_evaluation_key": role,
        "logical_evaluations": 1,
        "physical_calls": 1,
        "configured_model_route": {
            "provider": "offline",
            "model": "fixture",
            "role": "SmartModel",
        },
        "authorized_action_ref": {
            "action_id": f"action:{role}",
            "stage": f"stage:{role}",
            "sequence": 1,
            "observation_type": f"{role}_completed",
        },
        "semantic_output": semantic_output,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    return {**core, "artifact_digest": safe_packet_digest(core)}


def _component_node(index: int) -> dict:
    component_id = f"component:component-{index}"
    accepted = {
        "component_id": component_id,
        "component_revision": "1",
        "component_digest": f"component-digest-{index}",
        "user_facing_label": f"Fact {index}",
        "user_facing_question": f"What is fact {index}?",
    }
    claim = f"Fact {index} is supported."
    analyst_ref = {
        "role": ROLE_COMPONENT_ANALYST,
        "artifact_id": f"analyst:{index}",
        "artifact_digest": f"analyst-digest-{index}",
    }
    dprime_ref = {
        "role": ROLE_COMPONENT_DPRIME,
        "artifact_id": f"dprime:{index}",
        "artifact_digest": f"dprime-digest-{index}",
    }
    admission = {
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "component_id": component_id,
        "component_revision": "1",
        "component_digest": f"component-digest-{index}",
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
        "evidence_refs": [],
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


def _structured_graph() -> tuple[RunKernel, dict]:
    nodes = [_component_node(index) for index in range(1, 6)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain the combined filing sequence."
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
                    "synthesis_key": "E",
                    "claim_text": "E combines component 3 and component 4.",
                    "relationship_type": "conjunction",
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
                    "synthesis_key": "S",
                    "claim_text": "S combines E and component 5.",
                    "relationship_type": "ordered_conjunction",
                    "component_inputs": ["component:component-5"],
                    "synthesis_inputs": ["E"],
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
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    return kernel, graph


def _validate_synthesis(kernel: RunKernel, graph: dict, key: str) -> dict:
    input_packet = synthesis_dprime_input_packet(graph, synthesis_key=key)
    artifact = _role_artifact(
        ROLE_SYNTHESIS_DPRIME,
        {
            "validation_status": "supported",
            "reasons": ["Inputs support the nominated relationship."],
            "caveats": [],
            "nonclaims": [],
            "blockers": [],
        },
        input_packet,
    )
    return reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="synthesis_validation",
        synthesis_key=key,
        graph_candidate=graph_with_synthesis_validation(
            graph,
            synthesis_key=key,
            dprime_artifact=artifact,
        ),
    )


def test_graph_v1_enforces_topological_admission_and_full_scrutiny() -> None:
    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="E",
    )
    graph = _validate_synthesis(kernel, graph, "S")

    with pytest.raises(ComponentWorkGraphV1Error, match="Scrutineer posture"):
        graph_with_synthesis_admission(
            graph,
            synthesis_key="S",
            action_ref={"action_id": "forbidden-direct-admission"},
        )

    scrutiny_input = scrutineer_input_packet(graph)
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed",
            "reasons": ["The full dependency case is coherent."],
            "challenged_synthesis_keys": [],
            "caveats": [],
            "nonclaims": [],
        },
        scrutiny_input,
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
        synthesis_key="S",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            graph,
            logical_accounting={"synthesis_dprime_evaluations": 2},
            physical_call_accounting={"synthesis_dprime_calls": 2},
        ),
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )

    assert graph["graph_status"] == "ready"
    assert graph["maximum_synthesis_depth"] == 2
    assert graph["scrutineer_status"] == "passed"
    assert [item["status"] for item in graph["synthesis_nodes"]] == [
        "admitted",
        "admitted",
    ]


def test_graph_v1_rejects_synthesis_cycle_before_runkernel_admission() -> None:
    nodes = [_component_node(1), _component_node(2)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain their relationship."
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
                    "synthesis_key": "E",
                    "claim_text": "E depends on S.",
                    "relationship_type": "dependency",
                    "component_inputs": [],
                    "synthesis_inputs": ["S"],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
                {
                    "synthesis_key": "S",
                    "claim_text": "S depends on E.",
                    "relationship_type": "dependency",
                    "component_inputs": [],
                    "synthesis_inputs": ["E"],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
            ]
        },
        cross_input,
    )

    with pytest.raises(ComponentWorkGraphV1Error, match="cycle"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=cross,
        )
