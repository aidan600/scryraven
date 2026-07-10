"""PRODUCT-PATH-REGRESSION: bounded ordinary ComponentWorkGraph V1 authority."""

from __future__ import annotations

from copy import deepcopy

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
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    MulticomponentRoleRuntimeError,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import RunKernel, RunKernelTransitionError

RUN_ID = "run:multicomponent-graph-v1-test"
REQUEST_ID = "request:multicomponent-graph-v1-test"
COMPONENT_ADMISSION_STAGE = "multicomponent_component_admission"
COMPONENT_ADMISSION_OWNER = "RunKernel.MulticomponentComponentAdmission"


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


def _component_node(
    index: int,
    *,
    admission_overrides: dict | None = None,
) -> dict:
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
        "schema_version": "multicomponent_component_admission_ref_v1",
        "owner": "RunKernel.MulticomponentComponentAdmission",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "action_id": f"component-admission-action:{index}",
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
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
    admission.update(admission_overrides or {})
    return component_work_node_v1_from_admitted_component(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_component_ref=accepted,
        component_admission_ref=admission,
    )


def _seed_component_admission(
    kernel: RunKernel,
    nodes: list[dict],
    *,
    cross_artifact: dict | None = None,
) -> None:
    accepted_refs = []
    admission_refs = []
    for node in nodes:
        accepted_refs.append(
            {
                "component_id": node["component_id"],
                "component_revision": node["component_revision"],
                "component_digest": node["component_digest"],
                "user_facing_label": node["component_label"],
                "user_facing_question": node["component_question"],
            }
        )
        admission_refs.append(
            {
                "schema_version": "multicomponent_component_admission_ref_v1",
                "owner": COMPONENT_ADMISSION_OWNER,
                "canonical_state": True,
                "run_id": RUN_ID,
                "request_id": REQUEST_ID,
                "action_id": node["component_admission_action_ref"]["action_id"],
                "accepted_contract_version": "0.1-passive",
                "accepted_contract_digest": "accepted-contract-digest",
                "component_id": node["component_id"],
                "component_revision": node["component_revision"],
                "component_digest": node["component_digest"],
                "admission_status": node["admission_status"],
                "current": node["current"],
                "stale": node["stale"],
                "analyst_finding_ref": node["analyst_finding_ref"],
                "dprime_validation_ref": node["dprime_validation_ref"],
                "admitted_claim_ref": node["admitted_claim_ref"],
                "semantic_observation_ref": node["semantic_observation_ref"],
                "component_coverage_ref": node["component_coverage_ref"],
                "evidence_refs": node["evidence_refs"],
                "required_caveats": node["required_caveats"],
                "preserved_nonclaims": node["preserved_nonclaims"],
                "blocker_refs": node["blocker_refs"],
            }
        )
    kernel.state.initial_answer_contract = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
        "accepted_answer_component_refs": accepted_refs,
    }
    kernel.state.projections[COMPONENT_ADMISSION_STAGE] = {
        "owner": COMPONENT_ADMISSION_OWNER,
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
        "component_admission_refs": admission_refs,
    }
    if cross_artifact is not None:
        kernel.state.projections[
            f"multicomponent_role:{ROLE_CROSS_COMPONENT_ANALYST}:graph-v1"
        ] = cross_artifact


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
    _seed_component_admission(kernel, nodes, cross_artifact=cross)
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    return kernel, graph


def _flat_graph(*, caveats: tuple[str, ...] = ()) -> tuple[RunKernel, dict]:
    nodes = [_component_node(1), _component_node(2)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain the combined result."
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
                    "claim_text": "E combines component 1 and component 2.",
                    "relationship_type": "conjunction",
                    "component_inputs": [
                        "component:component-1",
                        "component:component-2",
                    ],
                    "synthesis_inputs": [],
                    "caveats": list(caveats),
                    "nonclaims": [],
                    "blockers": [],
                }
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


def _blocked_component_node(index: int) -> dict:
    return _component_node(
        index,
        admission_overrides={
            "admission_status": "blocked",
            "admitted_claim_ref": {},
            "semantic_observation_ref": {},
            "component_coverage_ref": {},
            "blocker_refs": [{"reason": "component evidence was not admitted"}],
        },
    )


def _single_synthesis_candidate(
    nodes: list[dict],
    *,
    component_inputs: list[str],
) -> tuple[dict, dict, str]:
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain the combined result."
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
                    "claim_text": "E combines the admitted component facts.",
                    "relationship_type": "conjunction",
                    "component_inputs": component_inputs,
                    "synthesis_inputs": [],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            ]
        },
        cross_input,
    )
    return accepted_ref, cross, directive


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


def test_material_caveat_requires_scrutiny_before_flat_terminal_admission() -> None:
    kernel, graph = _flat_graph(caveats=("Material qualification remains.",))
    graph = _validate_synthesis(kernel, graph, "E")

    assert graph["scrutineer_required"] is True
    assert "material_synthesis_caveat" in graph["scrutineer_trigger_reasons"]
    with pytest.raises(ComponentWorkGraphV1Error, match="Scrutineer posture"):
        graph_with_synthesis_admission(
            graph,
            synthesis_key="E",
            action_ref={"action_id": "forbidden-pre-scrutiny-admission"},
        )


def test_synthesis_dprime_ambiguity_adds_required_scrutiny_trigger() -> None:
    _kernel, graph = _flat_graph()
    input_packet = synthesis_dprime_input_packet(graph, synthesis_key="E")
    artifact = _role_artifact(
        ROLE_SYNTHESIS_DPRIME,
        {
            "validation_status": "ambiguous",
            "reasons": ["The nominated relationship remains ambiguous."],
            "caveats": [],
            "nonclaims": [],
            "blockers": [],
        },
        input_packet,
    )
    graph = graph_with_synthesis_validation(
        graph,
        synthesis_key="E",
        dprime_artifact=artifact,
    )

    assert graph["scrutineer_required"] is True
    assert "synthesis_dprime_ambiguity" in graph["scrutineer_trigger_reasons"]


def test_component_node_v1_rejects_noncanonical_admission_projection() -> None:
    with pytest.raises(
        ValueError,
        match="canonical RunKernel component admission",
    ):
        _component_node(1, admission_overrides={"canonical_state": False})


def test_graph_rejects_synthesis_proposal_over_blocked_component() -> None:
    nodes = [_component_node(1), _blocked_component_node(2)]
    accepted_ref, cross, directive = _single_synthesis_candidate(
        nodes,
        component_inputs=[node["component_id"] for node in nodes],
    )

    with pytest.raises(ComponentWorkGraphV1Error, match="unadmitted component"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=cross,
        )


def test_graph_with_admitted_synthesis_but_blocked_component_is_partial() -> None:
    nodes = [_component_node(1), _component_node(2), _blocked_component_node(3)]
    accepted_ref, cross, directive = _single_synthesis_candidate(
        nodes,
        component_inputs=[node["component_id"] for node in nodes[:2]],
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
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="E",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )

    assert graph["graph_status"] == "partial_independent_direct_output"


def test_runkernel_rejects_graph_without_current_component_admission() -> None:
    _seeded_kernel, graph = _structured_graph()
    unadmitted_kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)

    with pytest.raises(
        ValueError,
        match="current RunKernel component admission",
    ):
        reduce_component_work_graph_v1(
            run_kernel=unadmitted_kernel,
            operation="structure",
            graph_candidate=graph,
        )


def test_role_transport_rejects_authority_claims_before_reduction() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="claimed repository authority",
    ):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=ROLE_COMPONENT_ANALYST,
            input_packet={"component_ref": {"component_id": "component:1"}},
            ask_model=lambda *_args, **_kwargs: {
                "claim_text": "The evidence supports the component.",
                "support_status": "supported",
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
                "artifact_digest": "transport-must-not-assign-this",
            },
            clean_json_response=None,
            provider="offline",
            model="fixture",
            base_url="",
            api_key="",
            use_reasoning=False,
            logical_evaluation_key="component:1",
        )

    assert kernel.state.reduced_action_ids == set()
    assert kernel.state.observations == []


def test_runkernel_enforces_role_logical_key_uniqueness_and_phase_cap() -> None:
    duplicate_kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    duplicate_kernel.authorize_multicomponent_role_call(
        role=ROLE_COMPONENT_ANALYST,
        input_packet_digest="digest-1",
        logical_evaluation_key="component:1",
    )
    with pytest.raises(RunKernelTransitionError, match="duplicate"):
        duplicate_kernel.authorize_multicomponent_role_call(
            role=ROLE_COMPONENT_ANALYST,
            input_packet_digest="digest-2",
            logical_evaluation_key="component:1",
        )

    capped_kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    for index in range(5):
        capped_kernel.authorize_multicomponent_role_call(
            role=ROLE_COMPONENT_ANALYST,
            input_packet_digest=f"digest-{index}",
            logical_evaluation_key=f"component:{index}",
        )
    with pytest.raises(RunKernelTransitionError, match="Phase 1 cap"):
        capped_kernel.authorize_multicomponent_role_call(
            role=ROLE_COMPONENT_ANALYST,
            input_packet_digest="digest-over-cap",
            logical_evaluation_key="component:over-cap",
        )


def test_component_dprime_transport_cannot_replace_analyst_claim() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="cannot create or replace",
    ):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=ROLE_COMPONENT_DPRIME,
            input_packet={"nominated_claim": "The nominated claim."},
            ask_model=lambda *_args, **_kwargs: {
                "validation_status": "supported",
                "claim_text": "A replacement claim.",
                "reasons": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            },
            clean_json_response=None,
            provider="offline",
            model="fixture",
            base_url="",
            api_key="",
            use_reasoning=False,
            logical_evaluation_key="component:1",
        )

    assert kernel.state.reduced_action_ids == set()


def test_synthesis_validation_rejects_unadmitted_upstream_synthesis() -> None:
    _kernel, graph = _structured_graph()

    with pytest.raises(ComponentWorkGraphV1Error, match="upstream synthesis admission"):
        synthesis_dprime_input_packet(graph, synthesis_key="S")


def test_partial_graph_reaches_fap_as_direct_only_with_limitations() -> None:
    kernel, graph = _structured_graph()
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 5},
            multicomponent_graph_state=graph,
        )
    )
    packet = build_final_answer_packet(
        run_id=RUN_ID,
        final_evidence=[],
        author_evidence=[],
        sufficiency_judgment_projection=judgment.to_projection(),
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="Render only approved material.",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert graph["graph_status"] == "missing_required_scrutiny"
    assert judgment.final_answer_allowed is True
    assert judgment.decision.value == "partial_answer_authorized"
    assert len(packet.direct_component_entries) == 5
    assert packet.admitted_synthesis_entries == ()
    assert packet.multicomponent_limitations
    assert "Combined synthesis is unavailable" in payload.prompt


def test_stale_synthesis_is_omitted_from_sufficiency_and_fap() -> None:
    _kernel, graph = _structured_graph()
    stale_graph = deepcopy(graph)
    stale_node = next(
        node
        for node in stale_graph["synthesis_nodes"]
        if node["synthesis_key"] == "E"
    )
    stale_node["status"] = "stale"
    stale_node["current"] = False
    stale_node["stale"] = True
    stale_node["node_digest"] = safe_packet_digest(
        {
            key: value
            for key, value in stale_node.items()
            if key != "node_digest"
        }
    )
    stale_graph["graph_digest"] = safe_packet_digest(
        {
            key: value
            for key, value in stale_graph.items()
            if key != "graph_digest"
        }
    )
    stale_graph = finalize_component_work_graph_v1(stale_graph)
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 5},
            multicomponent_graph_state=stale_graph,
        )
    )
    packet = build_final_answer_packet(
        run_id=RUN_ID,
        final_evidence=[],
        author_evidence=[],
        sufficiency_judgment_projection=judgment.to_projection(),
    )

    assert stale_graph["graph_status"] == "stale_synthesis"
    assert judgment.final_answer_allowed is True
    assert judgment.final_packet_inputs["admitted_synthesis_entries"] == []
    assert packet.admitted_synthesis_entries == ()
    assert any(
        "stale" in limitation.casefold()
        for limitation in packet.multicomponent_limitations
    )


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


def test_ordinary_sufficiency_then_fap_then_author_consumes_only_admitted_graph() -> None:
    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(
        run_kernel=kernel,
        synthesis_key="E",
    )
    graph = _validate_synthesis(kernel, graph, "S")
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed",
            "reasons": ["The full dependency case is coherent."],
            "challenged_synthesis_keys": [],
            "caveats": [],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
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

    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 5},
            multicomponent_graph_state=graph,
        )
    )
    assert judgment.final_answer_allowed is True
    assert judgment.multicomponent_graph_consumption[
        "graph_readiness_status"
    ] == "ready"
    assert len(
        judgment.final_packet_inputs["direct_component_entries"]
    ) == 5
    assert len(
        judgment.final_packet_inputs["admitted_synthesis_entries"]
    ) == 2

    passages = [
        {
            "source_id": index,
            "title": f"Fact {index}",
            "url": f"https://example.test/fact-{index}",
            "text": f"Fact {index} is supported.",
        }
        for index in range(1, 6)
    ]
    packet = build_final_answer_packet(
        run_id=RUN_ID,
        final_evidence=passages,
        author_evidence=passages,
        sufficiency_judgment_projection=judgment.to_projection(),
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="Render the answer.",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert len(packet.direct_component_entries) == 5
    assert len(packet.admitted_synthesis_entries) == 2
    assert payload.direct_component_entries == packet.direct_component_entries
    assert payload.admitted_synthesis_entries == packet.admitted_synthesis_entries
    assert "Approved direct component findings" in payload.prompt
    assert "Approved admitted synthesis" in payload.prompt
