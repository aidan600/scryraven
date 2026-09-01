"""PRODUCT-PATH-REGRESSION: bounded ordinary ComponentWorkGraph V1 authority."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from core.component_analyst_evidence_set import (
    build_component_analyst_evidence_set,
    validate_component_analyst_evidence_set,
)
from core.component_work_graph_v1 import (
    ComponentWorkGraphV1Error,
    admit_synthesis_node_via_runkernel,
    component_work_graph_v1_from_cross_component_artifact,
    cross_component_input_packet,
    derive_multicomponent_role_call_accounting,
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
from core.evidence_ledger import EvidenceCandidate
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
from core.multicomponent_component_admission import component_analyst_input_packet
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    MulticomponentRoleRuntimeError,
    _normalize_semantic_output,
    execute_multicomponent_role_call,
    safe_packet_digest,
)
from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import (
    ActionType,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunState,
)
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.fixtures.component_analyst_evidence_sets import (
    component_analyst_evidence_set_fixture,
)

RUN_ID = "run:multicomponent-graph-v1-test"
REQUEST_ID = "request:multicomponent-graph-v1-test"
COMPONENT_ADMISSION_STAGE = "multicomponent_component_admission"
COMPONENT_ADMISSION_OWNER = "RunKernel.MulticomponentComponentAdmission"


def _fixture_component_evidence(index: int) -> dict:
    return {
        "evidence_status": "available",
        "evidence_ref_id": f"evidence:{index}",
        "bounded_text": f"Evidence {index} reports {index * 10} USD.",
        "currentness_signal": "current",
        "source_class": "current_primary_or_official",
        "source_tier": "official",
        "fact_disposition": "supported",
        "readability_posture": "readable",
        "conflict_posture": "none",
        "contradictory": False,
    }


def _component_packets_and_evidence_sets(
    *,
    accepted_contract: dict,
    component_refs: list[dict],
) -> tuple[dict[str, dict], dict[str, dict]]:
    evidence_sets: dict[str, dict] = {}
    packets: dict[str, dict] = {}
    for index, component_ref in enumerate(component_refs, start=1):
        component_id = str(component_ref["component_id"])
        evidence_set = component_analyst_evidence_set_fixture(
            _fixture_component_evidence(index)
        )
        evidence_sets[component_id] = evidence_set
        packets[component_id] = component_analyst_input_packet(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract=accepted_contract,
            component_ref=component_ref,
            component_evidence_set=evidence_set,
        )
    return packets, evidence_sets


def _component_refs_from_nodes(nodes: list[dict]) -> list[dict]:
    return [
        {
            "component_id": str(node["component_id"]),
            "component_revision": node["component_revision"],
            "component_digest": node["component_digest"],
            "user_facing_label": node["component_label"],
            "user_facing_question": node["component_question"],
            "mandatory_caveats": list(node.get("required_caveats") or ()),
            "prohibited_upgrades": [],
        }
        for node in nodes
    ]


def _cross_input_with_exact_evidence(
    *,
    nodes: list[dict],
    accepted_contract_ref: dict,
    directive: str,
) -> tuple[dict, dict[str, dict], dict[str, dict]]:
    packets, evidence_sets = _component_packets_and_evidence_sets(
        accepted_contract=accepted_contract_ref,
        component_refs=_component_refs_from_nodes(nodes),
    )
    return (
        cross_component_input_packet(
            component_nodes=nodes,
            accepted_contract_ref=accepted_contract_ref,
            requested_synthesis_directive=directive,
            component_analyst_input_packets=packets,
            component_analyst_evidence_sets=evidence_sets,
        ),
        packets,
        evidence_sets,
    )


def _role_artifact(
    role: str,
    semantic_output: dict,
    input_packet: dict,
    *,
    logical_evaluation_key: str | None = None,
) -> dict:
    if role == ROLE_CROSS_COMPONENT_ANALYST and "self_audit" not in semantic_output:
        semantic_output = {
            **semantic_output,
            "self_audit": (
                "The offline fixture stays within its supplied current components "
                "and retains its declared caveats, nonclaims, and blockers."
            ),
        }
    core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": role,
        "artifact_id": f"artifact:{role}:{safe_packet_digest(input_packet)[:12]}",
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "input_packet_digest": safe_packet_digest(input_packet),
        "logical_evaluation_key": logical_evaluation_key or role,
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


def _seed_role_artifact(
    kernel: RunKernel,
    artifact: dict,
    *,
    logical_evaluation_key: str,
) -> None:
    kernel.state.projections[
        f"multicomponent_role:{artifact['role']}:{logical_evaluation_key}"
    ] = artifact


def _accounted_graph(kernel: RunKernel, graph: dict) -> dict:
    logical, physical = derive_multicomponent_role_call_accounting(
        kernel.state.projections,
        issued_actions=kernel.state.issued_actions,
    )
    return reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="accounting",
        graph_candidate=graph_with_accounting(
            graph,
            logical_accounting=logical,
            physical_call_accounting=physical,
        ),
    )


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
        "case_posture": "supported",
        "component_analyst_case_ref": analyst_ref,
        "analyst_finding_ref": deepcopy(analyst_ref),
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
    requested_synthesis_directive: str = "Explain the combined result.",
    component_packets: dict[str, dict] | None = None,
    component_evidence_sets: dict[str, dict] | None = None,
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
                "case_posture": node.get("case_posture") or "supported",
                "component_analyst_case_ref": node["component_analyst_case_ref"],
                "analyst_finding_ref": node["analyst_finding_ref"],
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
    default_packets, default_evidence_sets = _component_packets_and_evidence_sets(
        accepted_contract=kernel.state.initial_answer_contract,
        component_refs=accepted_refs,
    )
    packets = component_packets or default_packets
    evidence_sets = component_evidence_sets or default_evidence_sets
    kernel.state.multicomponent_scheduler_context = {
        "requested_synthesis_directive": requested_synthesis_directive,
        "component_analyst_input_packets": deepcopy(packets),
        "component_analyst_evidence_sets": deepcopy(evidence_sets),
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
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
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
        transient_cross_input_packet=cross_input,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(
        kernel,
        nodes,
        cross_artifact=cross,
        requested_synthesis_directive=directive,
        component_packets=component_packets,
        component_evidence_sets=component_evidence_sets,
    )
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
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
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
        transient_cross_input_packet=cross_input,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(
        kernel,
        nodes,
        cross_artifact=cross,
        requested_synthesis_directive=directive,
        component_packets=component_packets,
        component_evidence_sets=component_evidence_sets,
    )
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
) -> tuple[dict, dict, str, dict]:
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain the combined result."
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
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
    return (
        accepted_ref,
        cross,
        directive,
        cross_input,
        component_packets,
        component_evidence_sets,
    )


def _cross_input_reproof_fixture() -> tuple[
    list[dict], dict, str, dict[str, dict], dict[str, dict], dict, dict
]:
    nodes = [
        _component_node(
            index,
            admission_overrides={
                "evidence_refs": [
                    {
                        "evidence_ref_id": f"evidence:{index}",
                        "content_ref_id": f"content:{index}",
                        "content_digest": safe_packet_digest(
                            {"evidence_ref_id": f"evidence:{index}"}
                        ),
                    }
                ]
            },
        )
        for index in (1, 2)
    ]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Reprove the exact combined result."
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
    )
    cross = _role_artifact(
        ROLE_CROSS_COMPONENT_ANALYST,
        {
            "synthesis_proposals": [
                {
                    "synthesis_key": "exact_total",
                    "claim_text": "The exact inputs combine to 30 USD.",
                    "relationship_type": "quantitative_conjunction",
                    "component_inputs": [node["component_id"] for node in nodes],
                    "synthesis_inputs": [],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            ]
        },
        cross_input,
    )
    return (
        nodes,
        accepted_ref,
        directive,
        component_packets,
        component_evidence_sets,
        cross_input,
        cross,
    )


def _redigest_role_artifact(artifact: dict) -> dict:
    updated = deepcopy(artifact)
    updated.pop("artifact_digest", None)
    updated["artifact_digest"] = safe_packet_digest(updated)
    return updated


def test_cross_input_reproof_accepts_both_exact_authority_routes() -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    assert all("quantitative_source_catalog" not in packet for packet in packets.values())
    supplied = component_work_graph_v1_from_cross_component_artifact(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_contract_ref=accepted_ref,
        requested_synthesis_directive=directive,
        component_nodes=nodes,
        cross_component_artifact=cross,
        transient_cross_input_packet=cross_input,
    )
    reconstructed = component_work_graph_v1_from_cross_component_artifact(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        accepted_contract_ref=accepted_ref,
        requested_synthesis_directive=directive,
        component_nodes=nodes,
        cross_component_artifact=cross,
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
    )
    assert supplied == reconstructed


@pytest.mark.parametrize("authority", ["supplied", "reconstructed"])
def test_cross_input_reproof_rejects_forged_artifact_digest(authority: str) -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    forged = deepcopy(cross)
    forged["input_packet_digest"] = "0" * 64
    forged = _redigest_role_artifact(forged)
    kwargs = (
        {"transient_cross_input_packet": cross_input}
        if authority == "supplied"
        else {
            "component_analyst_input_packets": packets,
            "component_analyst_evidence_sets": evidence_sets,
        }
    )
    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=forged,
            **kwargs,
        )


def test_cross_input_reproof_rejects_missing_or_incomplete_authority() -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, _cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    with pytest.raises(ComponentWorkGraphV1Error, match="authority is missing"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=cross,
        )
    packets.pop(nodes[-1]["component_id"])
    with pytest.raises(ComponentWorkGraphV1Error, match="one current packet"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=cross,
            component_analyst_input_packets=packets,
            component_analyst_evidence_sets=evidence_sets,
        )


@pytest.mark.parametrize(
    "stale_input",
    ["contract", "directive", "component", "proposal_contract"],
)
def test_supplied_cross_input_reproof_rejects_stale_structure(
    stale_input: str,
) -> None:
    nodes, accepted_ref, directive, _packets, _evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    supplied = deepcopy(cross_input)
    current_nodes = nodes
    current_ref = accepted_ref
    current_directive = directive
    if stale_input == "contract":
        current_ref = {**accepted_ref, "accepted_contract_digest": "stale-contract"}
    elif stale_input == "directive":
        current_directive = "A stale synthesis directive."
    elif stale_input == "component":
        current_nodes = [nodes[0], _component_node(3)]
    else:
        supplied["quantitative_specialist_proposal_contract"][
            "contract_digest"
        ] = "stale-proposal-contract"
    with pytest.raises(ComponentWorkGraphV1Error, match="structure"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=current_ref,
            requested_synthesis_directive=current_directive,
            component_nodes=current_nodes,
            cross_component_artifact=cross,
            transient_cross_input_packet=supplied,
        )


@pytest.mark.parametrize("catalog_mutation", ["alias", "posture", "digest", "material"])
def test_supplied_cross_input_reproof_rejects_malformed_catalog(
    catalog_mutation: str,
) -> None:
    nodes, accepted_ref, directive, _packets, _evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    supplied = deepcopy(cross_input)
    catalog = supplied["quantitative_source_catalog"]
    if catalog_mutation == "alias":
        catalog["component_01"]["source_local_key"] = "component_99"
    elif catalog_mutation == "posture":
        catalog["component_01"]["source_quality_posture"] = "unknown"
    elif catalog_mutation == "digest":
        catalog["posture_digest"] = "0" * 64
    else:
        catalog["component_01"]["source_material"] = {
            "claim_text": "must not be retained"
        }
    with pytest.raises(ComponentWorkGraphV1Error, match="catalog is malformed"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=cross,
            transient_cross_input_packet=supplied,
        )


def test_runkernel_reproof_uses_only_current_scheduler_packets() -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
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
        component_packets=packets,
        component_evidence_sets=evidence_sets,
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    assert kernel.state.projections["multicomponent_component_work_graph_v1"] == graph
    retained = json.dumps(graph, sort_keys=True)
    assert "quantitative_specialist_proposal_contract" not in retained
    assert "quantitative_source_catalog" not in retained
    assert "Evidence 1 reports" not in retained


def test_scheduler_reproof_rejects_recomputed_retained_evidence_set_digest() -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
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
        component_packets=packets,
        component_evidence_sets=evidence_sets,
    )
    kernel.state.initial_answer_contract["question_meaning_metadata"] = {
        "requested_synthesis_directive": directive,
    }
    for evidence_set in evidence_sets.values():
        for member in evidence_set["members"]:
            evidence_ref_id = member["code_binding"]["evidence_ref_id"]
            kernel.state.evidence_ledger.candidates[evidence_ref_id] = EvidenceCandidate(
                candidate_id=evidence_ref_id,
                readable_status="readable",
            )
    kernel.initialize_multicomponent_graph_scheduler(
        component_analyst_input_packets=packets,
        component_analyst_evidence_sets=evidence_sets,
        requested_synthesis_directive=directive,
    )

    component_id = nodes[1]["component_id"]
    original_set = evidence_sets[component_id]
    replacement_sources = []
    for index, member in enumerate(original_set["members"]):
        candidate_record = deepcopy(member["candidate_record"])
        if index == 0:
            candidate_record["eligible_for_stronger_obligation"] = True
        replacement_sources.append(
            {
                "evidence_ref_id": member["code_binding"]["evidence_ref_id"],
                "passage": deepcopy(member["passage"]),
                "candidate_record": candidate_record,
            }
        )
    replacement_set = build_component_analyst_evidence_set(replacement_sources)
    assert validate_component_analyst_evidence_set(replacement_set) == replacement_set
    assert replacement_set["evidence_set_digest"] != original_set["evidence_set_digest"]

    kernel.state.multicomponent_scheduler_context[
        "component_analyst_evidence_sets"
    ][component_id] = replacement_set
    with pytest.raises(
        RunKernelTransitionError,
        match="Graph V1 structure reproof component packets do not match scheduler authority",
    ):
        reduce_component_work_graph_v1(
            run_kernel=kernel,
            operation="structure",
            graph_candidate=candidate,
        )
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections


@pytest.mark.parametrize("corruption", ["missing", "cross_run"])
def test_runkernel_reproof_fails_without_exact_scheduler_packets(
    corruption: str,
) -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, cross_input, cross = (
        _cross_input_reproof_fixture()
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
        component_packets=packets,
        component_evidence_sets=evidence_sets,
    )
    if corruption == "missing":
        kernel.state.multicomponent_scheduler_context.pop(
            "component_analyst_input_packets"
        )
    else:
        packet = kernel.state.multicomponent_scheduler_context[
            "component_analyst_input_packets"
        ][nodes[0]["component_id"]]
        packet["run_binding"]["run_id"] = "run:stale"
    prior_observation_count = len(kernel.state.observations)
    with pytest.raises(RunKernelTransitionError):
        reduce_component_work_graph_v1(
            run_kernel=kernel,
            operation="structure",
            graph_candidate=candidate,
        )
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections
    assert len(kernel.state.observations) == prior_observation_count


def test_forged_cross_input_fails_before_graph_reduction_authority() -> None:
    nodes, accepted_ref, directive, packets, evidence_sets, _cross_input, cross = (
        _cross_input_reproof_fixture()
    )
    forged = deepcopy(cross)
    forged["input_packet_digest"] = "f" * 64
    forged = _redigest_role_artifact(forged)
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    issued_action_count = len(kernel.state.issued_actions)
    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        component_work_graph_v1_from_cross_component_artifact(
            run_id=RUN_ID,
            request_id=REQUEST_ID,
            accepted_contract_ref=accepted_ref,
            requested_synthesis_directive=directive,
            component_nodes=nodes,
            cross_component_artifact=forged,
            component_analyst_input_packets=packets,
            component_analyst_evidence_sets=evidence_sets,
        )
    assert len(kernel.state.issued_actions) == issued_action_count
    assert kernel.state.observations == []
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections


def test_cross_input_reproof_adds_no_runkernel_authority_surface() -> None:
    assert "component_analyst_input_packets" not in RunState.__dataclass_fields__
    assert all("reproof" not in action.value for action in ActionType)
    assert all("reproof" not in observation.value for observation in ObservationType)


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
        logical_evaluation_key=key,
    )
    _seed_role_artifact(kernel, artifact, logical_evaluation_key=key)
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
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
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
    graph = _accounted_graph(kernel, graph)
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
    for node in graph["synthesis_nodes"]:
        assert node["dprime_validated_node_revision"]
        assert node["dprime_validated_node_digest"]
        assert node["runkernel_admission_ref"]


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
    (
        accepted_ref,
        cross,
        directive,
        cross_input,
        _component_packets,
        _component_evidence_sets,
    ) = _single_synthesis_candidate(
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
            transient_cross_input_packet=cross_input,
        )


def test_graph_with_admitted_synthesis_but_blocked_component_is_partial() -> None:
    nodes = [_component_node(1), _component_node(2), _blocked_component_node(3)]
    (
        accepted_ref,
        cross,
        directive,
        cross_input,
        component_packets,
        component_evidence_sets,
    ) = _single_synthesis_candidate(
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
        transient_cross_input_packet=cross_input,
    )
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _seed_component_admission(
        kernel,
        nodes,
        cross_artifact=cross,
        requested_synthesis_directive=directive,
        component_packets=component_packets,
        component_evidence_sets=component_evidence_sets,
    )
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
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_args, **_kwargs: json.dumps(
                    {
                        "case_posture": "supported",
                        "claim_text": "The evidence supports the component.",
                        "evidence_analysis": "The exact bounded evidence supports the component.",
                        "self_audit": "The case does not extend beyond the supplied evidence.",
                        "supporting_evidence_aliases": ["component_evidence_01"],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                        "artifact_digest": "transport-must-not-assign-this",
                    }
                ),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
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


def test_component_analyst_resume_cannot_reopen_specialist_need() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="resume cannot propose another Specialist need",
    ):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=ROLE_COMPONENT_ANALYST_RESUME,
            input_packet={"prior_component_case": {}, "specialist_need_handoff": {}},
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_args, **_kwargs: json.dumps(
                    {
                        "case_posture": "supported",
                        "claim_text": "A resumed bounded claim.",
                        "evidence_analysis": "The exact specialist handoff was reassessed.",
                        "self_audit": "The resumed case makes no unsupported extension.",
                        "supporting_evidence_aliases": ["component_evidence_01"],
                        "caveats": [],
                        "nonclaims": [],
                        "blockers": [],
                        "specialist_need_proposal": {},
                    }
                ),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
            logical_evaluation_key="component:1",
        )

    assert kernel.state.reduced_action_ids == set()


_THIN_SUPPORT_STATUS_ONLY_ANALYST_OUTPUT = {
    "claim_text": "Legacy thin claim.",
    "support_status": "supported",
    "caveats": [],
    "nonclaims": [],
    "blockers": [],
}
_SUPPORTING_CASE_MISSING_ANALYSIS = {
    "case_posture": "supported",
    "claim_text": "Claim.",
    "self_audit": "I checked for overreach.",
    "caveats": [],
    "nonclaims": [],
    "contradictions": [],
    "blockers": [],
}
_SUPPORTING_CASE_MISSING_SELF_AUDIT = {
    "case_posture": "supported",
    "claim_text": "Claim.",
    "evidence_analysis": "The exact bounded evidence supports the claim.",
    "caveats": [],
    "nonclaims": [],
    "contradictions": [],
    "blockers": [],
}
_MODERN_SUPPORTING_ANALYST_CASE = {
    "case_posture": "supported",
    "claim_text": "A bounded claim.",
    "evidence_analysis": "The bounded evidence directly supports the claim.",
    "self_audit": "The claim stays within the bounded evidence.",
    "caveats": [],
    "nonclaims": [],
    "contradictions": [],
    "blockers": [],
    "supporting_evidence_aliases": ["component_evidence_01"],
}


@pytest.mark.parametrize(
    "role",
    [ROLE_COMPONENT_ANALYST, ROLE_COMPONENT_ANALYST_RESUME],
)
@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            _THIN_SUPPORT_STATUS_ONLY_ANALYST_OUTPUT,
            "requires a valid case_posture",
        ),
        (
            _SUPPORTING_CASE_MISSING_ANALYSIS,
            "requires evidence_analysis or warrant",
        ),
        (
            _SUPPORTING_CASE_MISSING_SELF_AUDIT,
            "requires self_audit",
        ),
    ],
)
def test_component_analyst_raw_output_rejects_thin_or_incomplete_case(
    role: str,
    payload: dict,
    match: str,
) -> None:
    with pytest.raises(MulticomponentRoleRuntimeError, match=match):
        _normalize_semantic_output(role, payload)

    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    with pytest.raises(MulticomponentRoleRuntimeError, match=match):
        execute_multicomponent_role_call(
            run_kernel=kernel,
            role=role,
            input_packet={"component_ref": {"component_id": "component:1"}},
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_args, **_kwargs: json.dumps(payload),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
            logical_evaluation_key="component:1",
        )
    assert kernel.state.reduced_action_ids == set()
    assert kernel.state.observations == []
    role_stage = next(
        (
            stage
            for stage, projection in kernel.state.projections.items()
            if str(stage).startswith(f"multicomponent_role:{role}:")
        ),
        None,
    )
    if role_stage is not None:
        assert kernel.state.projections[role_stage].get(
            "semantic_artifact_admitted"
        ) is not True


def test_runtime_legacy_fixture_marker_cannot_waive_case_posture() -> None:
    marked = {
        **_THIN_SUPPORT_STATUS_ONLY_ANALYST_OUTPUT,
        "_runtime_legacy_fixture_compatibility": True,
    }
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="requires a valid case_posture",
    ):
        _normalize_semantic_output(ROLE_COMPONENT_ANALYST, marked)
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="claimed repository authority or unsafe material",
    ):
        execute_multicomponent_role_call(
            run_kernel=RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID),
            role=ROLE_COMPONENT_ANALYST,
            input_packet={"component_ref": {"component_id": "component:1"}},
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_args, **_kwargs: json.dumps(marked),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
            logical_evaluation_key="component:1",
        )


def test_component_analyst_modern_case_emits_code_derived_support_status() -> None:
    for role in (ROLE_COMPONENT_ANALYST, ROLE_COMPONENT_ANALYST_RESUME):
        normalized = _normalize_semantic_output(role, _MODERN_SUPPORTING_ANALYST_CASE)
        assert normalized["case_posture"] == "supported"
        assert normalized["support_status"] == "supported"
        assert normalized["evidence_analysis"]
        assert normalized["self_audit"]
        assert "_runtime_legacy_fixture_compatibility" not in normalized


def test_component_analyst_resume_rejects_support_status_only_raw_output() -> None:
    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="requires a valid case_posture",
    ):
        _normalize_semantic_output(
            ROLE_COMPONENT_ANALYST_RESUME,
            _THIN_SUPPORT_STATUS_ONLY_ANALYST_OUTPUT,
        )


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
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
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
            transient_cross_input_packet=cross_input,
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
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
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
    graph = _accounted_graph(kernel, graph)
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


def test_clean_scrutineer_does_not_bump_validated_node_revision() -> None:
    kernel, graph = _flat_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    before = {
        node["synthesis_key"]: (node["node_revision"], node["node_digest"])
        for node in graph["synthesis_nodes"]
    }
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed",
            "reasons": ["Clean full-case review."],
            "challenged_synthesis_keys": [],
            "caveats": [],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(graph, scrutineer_artifact=scrutiny),
    )
    after = {
        node["synthesis_key"]: (node["node_revision"], node["node_digest"])
        for node in graph["synthesis_nodes"]
    }
    assert after == before
    assert graph["scrutineer_status"] == "passed"


def test_scrutineer_material_caveats_invalidate_prior_validation() -> None:
    kernel, graph = _flat_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed_with_caveats",
            "reasons": ["Material caveat remains."],
            "challenged_synthesis_keys": [],
            "caveats": ["Material caveat remains."],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
        logical_evaluation_key="full-case",
    )
    mutated = graph_with_scrutineer(graph, scrutineer_artifact=scrutiny)
    node = next(item for item in mutated["synthesis_nodes"] if item["synthesis_key"] == "E")
    assert node["status"] == "proposed"
    assert not node.get("dprime_validation_ref")
    with pytest.raises(ComponentWorkGraphV1Error, match="validated node"):
        graph_with_synthesis_admission(
            mutated,
            synthesis_key="E",
            action_ref={"action_id": "should-fail"},
        )


def test_scrutineer_challenge_against_admitted_upstream_is_governed() -> None:
    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(run_kernel=kernel, synthesis_key="E")
    graph = _validate_synthesis(kernel, graph, "S")
    e_before = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "E"
    )
    s_before = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "S"
    )
    assert e_before["status"] == "admitted"
    assert s_before["status"] == "validated"
    assert e_before.get("runkernel_admission_ref")
    assert s_before.get("dprime_validation_ref")

    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "challenged",
            "reasons": ["Upstream E is not supported by the admitted inputs."],
            "challenged_synthesis_keys": ["E"],
            "caveats": [],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=scrutiny,
        ),
    )
    e_node = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "E"
    )
    s_node = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "S"
    )
    assert e_node["status"] == "challenged"
    assert not e_node.get("runkernel_admission_ref")
    assert not e_node.get("dprime_validation_ref")
    assert e_node.get("dprime_validated_node_revision") is None
    assert e_node.get("dprime_validated_node_digest") is None
    assert int(e_node["node_revision"]) > int(e_before["node_revision"])
    assert s_node["status"] == "blocked_dependency"
    assert not s_node.get("dprime_validation_ref")
    assert not s_node.get("runkernel_admission_ref")
    challenge_ref = next(
        ref
        for ref in graph.get("challenge_refs") or ()
        if ref.get("synthesis_key") == "E"
    )
    assert challenge_ref["target_kind"] == "synthesis"
    assert challenge_ref["target_key"].startswith("synthesis_")
    assert challenge_ref["resolved_target"]["synthesis_key"] == "E"
    assert challenge_ref["resolved_target"]["node_id"] == e_before["node_id"]
    assert challenge_ref["resolved_target"]["node_revision"] == e_before["node_revision"]
    assert challenge_ref["resolved_target"]["node_digest"] == e_before["node_digest"]

    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    assert graph["graph_status"] == "challenged_synthesis"

    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 5},
            multicomponent_graph_state=graph,
        )
    )
    assert judgment.final_packet_inputs["admitted_synthesis_entries"] == []
    assert len(judgment.final_packet_inputs["direct_component_entries"]) == 5
    assert judgment.multicomponent_graph_consumption[
        "graph_readiness_status"
    ] == "challenged_synthesis"


def test_scrutineer_material_caveat_against_admitted_upstream_is_governed() -> None:
    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(run_kernel=kernel, synthesis_key="E")
    graph = _validate_synthesis(kernel, graph, "S")
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "passed_with_caveats",
            "reasons": ["Late material caveat against admitted E."],
            "challenged_synthesis_keys": [],
            "caveats": ["Late material caveat against admitted E."],
            "nonclaims": ["Do not treat E as unconditionally settled."],
        },
        scrutineer_input_packet(graph),
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=scrutiny,
        ),
    )
    e_node = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "E"
    )
    s_node = next(
        item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "S"
    )
    assert e_node["status"] == "proposed"
    assert not e_node.get("runkernel_admission_ref")
    assert not e_node.get("dprime_validation_ref")
    assert "Late material caveat against admitted E." in e_node["required_caveats"]
    assert s_node["status"] in {"proposed", "blocked_dependency"}
    assert not s_node.get("dprime_validation_ref")
    assert not s_node.get("runkernel_admission_ref")

    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    assert graph["graph_status"] in {
        "missing_component_or_dependency",
        "partial_independent_direct_output",
        "unsupported_graph_posture",
        "blocked_synthesis",
    }
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 5},
            multicomponent_graph_state=graph,
        )
    )
    assert judgment.final_packet_inputs["admitted_synthesis_entries"] == []
    assert len(judgment.final_packet_inputs["direct_component_entries"]) == 5


def test_synthesis_dprime_and_scrutineer_packets_carry_bounded_admitted_claims() -> None:
    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(run_kernel=kernel, synthesis_key="E")

    s_packet = synthesis_dprime_input_packet(graph, synthesis_key="S")
    admitted_by_kind = {
        item["node_kind"]: item for item in s_packet["current_admitted_inputs"]
    }
    component_input = next(
        item
        for item in s_packet["current_admitted_inputs"]
        if item["node_kind"] == "component"
    )
    synthesis_input = admitted_by_kind["synthesis"]
    assert component_input["claim_text"] == "Fact 5 is supported."
    assert component_input["claim_id"] == "claim:5"
    assert component_input["claim_digest"]
    assert synthesis_input["claim_text"] == "E combines component 3 and component 4."
    assert synthesis_input["synthesis_key"] == "E"
    assert synthesis_input["claim_id"]
    assert synthesis_input["claim_digest"]
    assert synthesis_input["node_revision"]
    assert synthesis_input["node_digest"]

    scrutiny_packet = scrutineer_input_packet(graph)
    component_claims = {
        item["component_id"]: item["claim_text"]
        for item in scrutiny_packet["component_refs"]
    }
    assert component_claims["component:component-3"] == "Fact 3 is supported."
    assert component_claims["component:component-4"] == "Fact 4 is supported."
    assert component_claims["component:component-5"] == "Fact 5 is supported."
    synthesis_claims = {
        item["synthesis_key"]: item["claim_text"]
        for item in scrutiny_packet["synthesis_refs"]
    }
    assert synthesis_claims["E"] == "E combines component 3 and component 4."
    assert synthesis_claims["S"] == "S combines E and component 5."

    forbidden_markers = (
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "OPENAI_API_KEY",
        "https://northstar.example",
        "system_prompt",
    )
    encoded = json.dumps(scrutiny_packet) + json.dumps(s_packet)
    assert not any(marker in encoded for marker in forbidden_markers)

    intact_digest = safe_packet_digest(s_packet)
    tampered = deepcopy(s_packet)
    tampered["current_admitted_inputs"][0]["claim_text"] = "Tampered claim text."
    assert safe_packet_digest(tampered) != intact_digest

    stale_artifact = _role_artifact(
        ROLE_SYNTHESIS_DPRIME,
        {
            "validation_status": "supported",
            "reasons": ["Stale packet must not apply."],
            "caveats": [],
            "nonclaims": [],
            "blockers": [],
        },
        tampered,
        logical_evaluation_key="S",
    )
    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        graph_with_synthesis_validation(
            graph,
            synthesis_key="S",
            dprime_artifact=stale_artifact,
        )

    removed = deepcopy(s_packet)
    removed["current_admitted_inputs"] = removed["current_admitted_inputs"][1:]
    assert safe_packet_digest(removed) != intact_digest


def test_graph_validation_rejects_unrelated_synthesis_mutation() -> None:
    import core.component_work_graph_v1 as graph_v1

    kernel, graph = _structured_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    graph = admit_synthesis_node_via_runkernel(run_kernel=kernel, synthesis_key="E")
    input_packet = synthesis_dprime_input_packet(graph, synthesis_key="S")
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
        logical_evaluation_key="S",
    )
    _seed_role_artifact(kernel, artifact, logical_evaluation_key="S")
    candidate = deepcopy(
        graph_with_synthesis_validation(
            graph,
            synthesis_key="S",
            dprime_artifact=artifact,
        )
    )
    synthesis_target = next(
        item
        for item in scrutineer_input_packet(graph)["challenge_target_catalog"]
        if item["target_kind"] == "synthesis"
        and item["canonical_target_ref"]["synthesis_key"] == "E"
    )
    candidate["challenge_refs"] = [
        {
            "target_kind": "synthesis",
            "target_key": synthesis_target["target_key"],
            "synthesis_key": "E",
            "resolved_target": synthesis_target["canonical_target_ref"],
            "resolution_graph_id": graph["graph_id"],
            "resolution_graph_revision": graph["graph_revision"],
            "resolution_graph_digest": graph["graph_digest"],
            "run_id": graph["run_id"],
            "request_id": graph["request_id"],
            "scrutineer_ref": {
                "role": ROLE_SCRUTINEER,
                "artifact_id": "artifact:forged-but-structured",
                "artifact_digest": "artifact-digest:forged-but-structured",
            },
            "challenge_status": "challenged",
            "reasons": ["Schema-valid unauthorized transition mutation."],
            "caveats": [],
            "nonclaims": [],
        }
    ]
    candidate["graph_digest"] = graph_v1._digest(
        graph_v1._without_graph_digest(candidate)
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="exact rederived transition",
    ):
        reduce_component_work_graph_v1(
            run_kernel=kernel,
            operation="synthesis_validation",
            synthesis_key="S",
            graph_candidate=candidate,
        )


def test_forged_accounting_is_rejected() -> None:
    kernel, graph = _flat_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    with pytest.raises(
        (ComponentWorkGraphV1Error, RunKernelTransitionError),
        match="accounting|role-call|exact",
    ):
        reduce_component_work_graph_v1(
            run_kernel=kernel,
            operation="accounting",
            graph_candidate=graph_with_accounting(
                graph,
                logical_accounting={
                    "component_analyst_evaluations": 99,
                    "cross_component_analyst_evaluations": 99,
                    "synthesis_dprime_evaluations": 99,
                    "scrutineer_evaluations": 99,
                },
                physical_call_accounting={
                    "component_analyst_calls": 99,
                    "cross_component_analyst_calls": 99,
                    "synthesis_dprime_calls": 99,
                    "scrutineer_calls": 99,
                },
            ),
        )


def test_admitted_synthesis_preserves_dprime_validated_revision_proof() -> None:
    kernel, graph = _flat_graph()
    graph = _validate_synthesis(kernel, graph, "E")
    validated = next(item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "E")
    validated_revision = validated["dprime_validated_node_revision"]
    validated_digest = validated["dprime_validated_node_digest"]
    assert validated_revision == validated["node_revision"]
    assert validated_digest == validated["node_digest"]
    graph = admit_synthesis_node_via_runkernel(run_kernel=kernel, synthesis_key="E")
    admitted = next(item for item in graph["synthesis_nodes"] if item["synthesis_key"] == "E")
    assert admitted["status"] == "admitted"
    assert admitted["dprime_validated_node_revision"] == validated_revision
    assert admitted["dprime_validated_node_digest"] == validated_digest
    assert admitted["runkernel_admission_ref"]


def _independent_admitted_graph() -> tuple[RunKernel, dict]:
    nodes = [_component_node(index) for index in range(1, 5)]
    accepted_ref = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": RUN_ID,
        "request_id": REQUEST_ID,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": "accepted-contract-digest",
    }
    directive = "Explain two independent combined results."
    cross_input, component_packets, component_evidence_sets = (
        _cross_input_with_exact_evidence(
            nodes=nodes,
            accepted_contract_ref=accepted_ref,
            directive=directive,
        )
    )
    proposals = []
    for key, component_ids in (
        ("E", ["component:component-1", "component:component-2"]),
        ("F", ["component:component-3", "component:component-4"]),
    ):
        proposals.append(
            {
                "synthesis_key": key,
                "claim_text": f"{key} combines its two component facts.",
                "relationship_type": "conjunction",
                "component_inputs": component_ids,
                "synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        )
    cross = _role_artifact(
        ROLE_CROSS_COMPONENT_ANALYST,
        {"synthesis_proposals": proposals},
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
        component_packets=component_packets,
        component_evidence_sets=component_evidence_sets,
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="structure",
        graph_candidate=candidate,
    )
    for key in ("E", "F"):
        graph = _validate_synthesis(kernel, graph, key)
        graph = admit_synthesis_node_via_runkernel(
            run_kernel=kernel,
            synthesis_key=key,
        )
    return kernel, graph


def _catalog_target(graph: dict, kind: str, *, meaning: str | None = None) -> dict:
    targets = [
        item
        for item in scrutineer_input_packet(graph)["challenge_target_catalog"]
        if item["target_kind"] == kind
    ]
    if meaning is None:
        return targets[0]
    for target in targets:
        encoded = json.dumps(target, sort_keys=True)
        if meaning in encoded:
            return target
    raise AssertionError(f"No {kind} target contains {meaning}")


def _apply_typed_scrutiny(
    kernel: RunKernel,
    graph: dict,
    *,
    target: dict,
    status: str = "challenged",
) -> dict:
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": status,
            "reasons": [f"Targeted {target['target_kind']} challenge."],
            "challenge_targets": [
                {
                    "target_kind": target["target_kind"],
                    "target_key": target["target_key"],
                }
            ],
            "caveats": [],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
        logical_evaluation_key="full-case",
    )
    _seed_role_artifact(kernel, scrutiny, logical_evaluation_key="full-case")
    return reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=scrutiny,
        ),
    )


def _finalize_and_consume(kernel: RunKernel, graph: dict):
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="finalize",
        graph_candidate=finalize_component_work_graph_v1(graph),
    )
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            final_evidence_facts={"final_evidence_count": 4},
            multicomponent_graph_state=graph,
        )
    )
    return graph, judgment


def test_scrutineer_typed_component_target_suppresses_direct_and_dependents() -> None:
    kernel, graph = _independent_admitted_graph()
    target = _catalog_target(graph, "component", meaning="component:component-1")
    graph = _apply_typed_scrutiny(kernel, graph, target=target)
    graph, judgment = _finalize_and_consume(kernel, graph)
    packet = judgment.final_packet_inputs
    assert graph["graph_status"] == "challenged_component"
    assert {item["component_id"] for item in packet["direct_component_entries"]} == {
        "component:component-2",
        "component:component-3",
        "component:component-4",
    }
    assert {
        item["synthesis_key"]
        for item in judgment.multicomponent_graph_consumption[
            "admitted_synthesis_entries"
        ]
    } == {"F"}
    assert packet["admitted_synthesis_entries"] == []


def test_scrutineer_typed_synthesis_target_preserves_independent_branch() -> None:
    kernel, graph = _independent_admitted_graph()
    target = _catalog_target(graph, "synthesis", meaning='"synthesis_key": "E"')
    graph = _apply_typed_scrutiny(kernel, graph, target=target)
    graph, judgment = _finalize_and_consume(kernel, graph)
    packet = judgment.final_packet_inputs
    assert graph["graph_status"] == "challenged_synthesis"
    assert {
        item["synthesis_key"]
        for item in judgment.multicomponent_graph_consumption[
            "admitted_synthesis_entries"
        ]
    } == {"F"}
    assert packet["admitted_synthesis_entries"] == []


def test_scrutineer_typed_edge_target_invalidates_exact_downstream_branch() -> None:
    kernel, graph = _independent_admitted_graph()
    target = _catalog_target(graph, "edge", meaning='"synthesis_key": "E"')
    graph = _apply_typed_scrutiny(kernel, graph, target=target)
    graph, judgment = _finalize_and_consume(kernel, graph)
    packet = judgment.final_packet_inputs
    assert graph["graph_status"] == "challenged_edge"
    assert {
        item["synthesis_key"]
        for item in judgment.multicomponent_graph_consumption[
            "admitted_synthesis_entries"
        ]
    } == {"F"}
    assert packet["admitted_synthesis_entries"] == []
    assert len(packet["direct_component_entries"]) == 4


def test_scrutineer_typed_subgraph_target_preserves_independent_branch() -> None:
    kernel, graph = _independent_admitted_graph()
    target = _catalog_target(graph, "subgraph", meaning='"synthesis_key": "E"')
    graph = _apply_typed_scrutiny(kernel, graph, target=target)
    graph, judgment = _finalize_and_consume(kernel, graph)
    packet = judgment.final_packet_inputs
    assert graph["graph_status"] == "challenged_subgraph"
    assert {
        item["synthesis_key"]
        for item in judgment.multicomponent_graph_consumption[
            "admitted_synthesis_entries"
        ]
    } == {"F"}
    assert packet["admitted_synthesis_entries"] == []


def test_scrutineer_typed_graph_target_suppresses_all_output() -> None:
    kernel, graph = _independent_admitted_graph()
    target = _catalog_target(graph, "graph")
    graph = _apply_typed_scrutiny(kernel, graph, target=target, status="blocked")
    graph, judgment = _finalize_and_consume(kernel, graph)
    packet = judgment.final_packet_inputs
    assert graph["graph_status"] == "blocked_graph"
    assert graph["graph_output_suppressed"] is True
    assert packet["direct_component_entries"] == []
    assert packet["admitted_synthesis_entries"] == []


@pytest.mark.parametrize(
    ("kind", "key", "message"),
    [
        ("component", "missing_target", "unknown target key"),
        ("edge", "component_01", "wrong target kind"),
    ],
)
def test_scrutineer_rejects_unknown_or_wrong_kind_target(
    kind: str,
    key: str,
    message: str,
) -> None:
    _, graph = _independent_admitted_graph()
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "challenged",
            "reasons": ["Invalid target."],
            "challenge_targets": [{"target_kind": kind, "target_key": key}],
            "caveats": [],
            "nonclaims": [],
        },
        scrutineer_input_packet(graph),
    )
    with pytest.raises(ComponentWorkGraphV1Error, match=message):
        graph_with_scrutineer(graph, scrutineer_artifact=scrutiny)


@pytest.mark.parametrize("target_kind", ["component", "edge", "subgraph", "graph"])
def test_scrutineer_rejects_tampered_catalog_binding(target_kind: str) -> None:
    _, graph = _independent_admitted_graph()
    packet = scrutineer_input_packet(graph)
    target = next(
        item
        for item in packet["challenge_target_catalog"]
        if item["target_kind"] == target_kind
    )
    target["canonical_target_ref"] = {
        **target["canonical_target_ref"],
        "tampered_digest": "forged",
    }
    scrutiny = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "challenged",
            "reasons": ["Tampered binding."],
            "challenge_targets": [
                {
                    "target_kind": target["target_kind"],
                    "target_key": target["target_key"],
                }
            ],
            "caveats": [],
            "nonclaims": [],
        },
        packet,
    )
    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        graph_with_scrutineer(graph, scrutineer_artifact=scrutiny)


def test_scrutineer_catalog_digest_and_stale_graph_binding_are_exact() -> None:
    _, graph = _independent_admitted_graph()
    packet = scrutineer_input_packet(graph)
    changed = deepcopy(packet)
    changed["challenge_target_catalog"][0]["label"] = "Changed bounded label"
    assert safe_packet_digest(packet) != safe_packet_digest(changed)
    changed["graph_ref"]["request_id"] = "request:other"
    target = changed["challenge_target_catalog"][0]
    artifact = _role_artifact(
        ROLE_SCRUTINEER,
        {
            "challenge_status": "challenged",
            "reasons": ["Stale or cross-request binding."],
            "challenge_targets": [
                {
                    "target_kind": target["target_kind"],
                    "target_key": target["target_key"],
                }
            ],
            "caveats": [],
            "nonclaims": [],
        },
        changed,
    )
    with pytest.raises(ComponentWorkGraphV1Error, match="input binding mismatch"):
        graph_with_scrutineer(graph, scrutineer_artifact=artifact)


@pytest.mark.parametrize(
    "semantic_output",
    [
        {
            "challenge_status": "challenged",
            "reasons": [],
            "challenge_targets": [
                {"target_kind": "component", "target_key": "component_01"},
                {"target_kind": "component", "target_key": "component_01"},
            ],
            "caveats": [],
            "nonclaims": [],
        },
        {
            "challenge_status": "challenged",
            "reasons": [],
            "challenge_targets": [
                {
                    "target_kind": "component",
                    "target_key": "component_01",
                    "node_id": "forged",
                }
            ],
            "caveats": [],
            "nonclaims": [],
        },
        {
            "challenge_status": "passed",
            "reasons": [],
            "challenge_targets": [
                {"target_kind": "component", "target_key": "component_01"}
            ],
            "caveats": [],
            "nonclaims": [],
        },
    ],
)
def test_scrutineer_rejects_duplicate_authority_or_malformed_selection(
    semantic_output: dict,
) -> None:
    _, graph = _independent_admitted_graph()
    artifact = _role_artifact(
        ROLE_SCRUTINEER,
        semantic_output,
        scrutineer_input_packet(graph),
    )
    with pytest.raises(MulticomponentRoleRuntimeError):
        graph_with_scrutineer(graph, scrutineer_artifact=artifact)
