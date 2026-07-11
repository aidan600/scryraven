"""PRODUCT-PATH-REGRESSION: selective recovery recomputation authority."""

from __future__ import annotations

from copy import deepcopy

import pytest

from core.component_work_graph_v1 import (
    MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
    ComponentWorkGraphV1Error,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    derive_selective_recomputation_closure,
    reduce_component_work_graph_v1,
    reduce_selective_recomputation_closure,
)
from core.multicomponent_role_runtime import (
    ROLE_CROSS_COMPONENT_ANALYST,
    safe_packet_digest,
)
from core.run_kernel import (
    MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE,
    RunKernel,
    RunKernelTransitionError,
)
from tests.test_multicomponent_component_work_graph_v1 import (
    REQUEST_ID,
    RUN_ID,
    _component_node,
    _role_artifact,
    _seed_component_admission,
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
    current_contract = {
        "owner": "RunKernel.CurrentAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.2-recovery",
        "accepted_contract_digest": "accepted-contract-digest-recovery",
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
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "component_id": "component:recovered:test",
        "accepted_contract_digest": current_contract["accepted_contract_digest"],
        "admission_status": "admitted",
        "action_id": "component-admission-action:recovered",
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
            )
        },
        contract_amendment_admission_ref=amendment_admission,
        contract_amendment_application_ref=amendment_application,
        recovered_component_admission_ref=recovered_admission,
    )
    return kernel, graph, closure


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
