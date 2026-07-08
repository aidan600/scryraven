"""PRODUCT-PATH-REGRESSION: ComponentWorkNode V0 single-relation projection.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run
Why ordinary product-path work cannot be done directly: offline unit validation
exercises the typed ComponentWorkNode projection over product packet refs without
making live provider, model, search, fetch/read, retrieval, or source calls.
Integration deadline: current phase.
Exit condition: keep while ComponentWorkNode V0 remains the typed contract for
the generic single-relation lane, or replace with a product-path guard when the
runtime consumer moves to a first-class component-work executor.
Why this is not a shadow product path: tests validate refs built from the
ordinary generic relation-plan packet shape; they do not answer, schedule,
aggregate, render citations, or create alternate evidence/support authority.
Forbidden interpretation: ComponentWorkNode V0 is not product correctness,
source-obligation satisfaction, citation rendering, FAP/Author creation,
component graph scheduling, multi-component planning, or live validation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import pytest

from core.component_work_node import (
    ComponentWorkNodeError,
    component_work_node_v0_refs_from_product_packet,
    validate_component_work_node_v0_input_ref,
    validate_component_work_node_v0_output_ref,
    validate_component_work_node_v0_refs,
)
from core.generic_query_to_relation_planning import build_generic_query_relation_plan

N400_QUERY = "What is the current USCIS Form N-400 paper filing fee?"


def test_component_work_node_refs_preserve_single_relation_contract() -> None:
    packet = _product_packet()

    refs = component_work_node_v0_refs_from_product_packet(packet)

    assert validate_component_work_node_v0_refs(refs) == refs
    input_ref = refs["component_work_node_v0_input_ref"]
    output_ref = refs["component_work_node_v0_output_ref"]
    assert input_ref["component_ids"] == [packet["component_id"]]
    assert input_ref["source_obligation_lane_ids"] == [
        packet["source_obligation_id"]
    ]
    assert input_ref["relation_plan_ref"]["relation_plan_id"] == (
        packet["relation_plan_id"]
    )
    assert input_ref["component_answer_type_binding_ref"] == (
        packet["component_answer_type_binding_ref"]
    )
    assert input_ref["budget_lease_created"] is False
    assert output_ref["node_status"] == "consumed"
    assert output_ref["source_obligation_authority_consumed"] is True
    assert output_ref["citation_source_handoff_authority_consumed"] is True
    assert output_ref["source_obligation_satisfaction_claimed"] is False
    assert output_ref["component_work_node_created_fap"] is False
    assert output_ref["component_work_node_created_author"] is False
    assert output_ref["component_work_node_rendered_citations"] is False
    assert output_ref["component_work_node_claimed_product_correctness"] is False
    assert output_ref["candidate_fetch_read_refs_treated_as_semantic_support"] is False
    assert output_ref[
        "component_coverage_treated_as_source_obligation_satisfaction"
    ] is False


def test_component_work_node_rejects_multiple_components() -> None:
    refs = component_work_node_v0_refs_from_product_packet(_product_packet())
    input_ref = deepcopy(refs["component_work_node_v0_input_ref"])
    output_ref = deepcopy(refs["component_work_node_v0_output_ref"])

    input_ref["component_ids"].append("component:second")
    output_ref["component_ids"].append("component:second")

    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_input_ref(input_ref)
    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(output_ref)


def test_component_work_node_rejects_multiple_source_obligation_lanes() -> None:
    refs = component_work_node_v0_refs_from_product_packet(_product_packet())
    input_ref = deepcopy(refs["component_work_node_v0_input_ref"])
    output_ref = deepcopy(refs["component_work_node_v0_output_ref"])

    input_ref["source_obligation_lane_ids"].append("obligation:second")
    output_ref["source_obligation_lane_ids"].append("obligation:second")

    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_input_ref(input_ref)
    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(output_ref)


@pytest.mark.parametrize(
    "flag",
    [
        "component_work_node_claimed_product_correctness",
        "component_work_node_created_fap",
        "component_work_node_created_author",
        "component_work_node_created_source_display",
        "component_work_node_rendered_citations",
        "product_correctness_claimed",
    ],
)
def test_component_work_node_cannot_open_downstream_or_correctness(flag: str) -> None:
    refs = component_work_node_v0_refs_from_product_packet(_product_packet())
    output_ref = deepcopy(refs["component_work_node_v0_output_ref"])

    output_ref[flag] = True

    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(output_ref)


@pytest.mark.parametrize(
    "flag",
    [
        "candidate_fetch_read_refs_treated_as_semantic_support",
        "component_coverage_treated_as_source_obligation_satisfaction",
        "source_obligation_satisfaction_claimed",
    ],
)
def test_component_work_node_rejects_ref_laundering(flag: str) -> None:
    packet = _product_packet(
        source_obligation_authority_consumed=False,
        citation_source_handoff_authority_consumed=False,
    )
    refs = component_work_node_v0_refs_from_product_packet(packet)
    output_ref = deepcopy(refs["component_work_node_v0_output_ref"])

    output_ref[flag] = True

    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(output_ref)


@pytest.mark.parametrize(
    "flag",
    [
        "multi_component_planning_opened",
        "component_work_graph_scheduling_opened",
        "parallel_component_execution_opened",
        "budget_lease_created",
        "final_analyst_aggregation_created",
    ],
)
def test_component_work_node_rejects_scheduler_graph_and_budget_claims(
    flag: str,
) -> None:
    refs = component_work_node_v0_refs_from_product_packet(_product_packet())
    output_ref = deepcopy(refs["component_work_node_v0_output_ref"])

    output_ref[flag] = True

    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(output_ref)


def test_component_work_node_preserves_multi_source_shape() -> None:
    packet = _product_packet()
    semantic = deepcopy(packet["semantic_status_payload"])
    semantic.update(
        {
            "dprime_multi_source_relation_count": 2,
            "dprime_multi_source_source_count": 2,
            "dprime_multi_source_relation_set_ref": {
                "status": "created",
                "relation_count": 2,
                "source_count": 2,
                "relation_intake_refs": [
                    _relation_ref(packet, suffix="primary"),
                    _relation_ref(packet, suffix="secondary"),
                ],
                "evidence_source_refs": [
                    _source_ref(suffix="primary"),
                    _source_ref(suffix="secondary"),
                ],
            },
            "dprime_multi_source_support_posture_ref": {
                "status": "consumed",
                "source_count": 2,
                "source_display_candidate_refs": [
                    _source_ref(suffix="primary"),
                    _source_ref(suffix="secondary"),
                ],
                "currentness_posture": "current",
                "conflict_posture": "no_conflict_detected",
                "answer_path_allowed": True,
            },
        }
    )
    packet["semantic_status_payload"] = semantic

    refs = component_work_node_v0_refs_from_product_packet(packet)
    output_ref = refs["component_work_node_v0_output_ref"]
    shape = output_ref["multi_source_shape_ref"]

    assert shape["status"] == "preserved"
    assert shape["relation_count"] >= 2
    assert shape["source_count"] >= 2
    assert shape["relation_ref_count"] >= 2
    assert shape["source_ref_count"] >= 2
    assert len(shape["relation_refs"]) >= 2
    assert len(shape["source_refs"]) >= 2
    assert shape["best_source_collapse_created"] is False
    assert shape["single_undifferentiated_source_output_created"] is False

    collapsed = deepcopy(output_ref)
    collapsed["multi_source_shape_ref"]["relation_count"] = 2
    collapsed["multi_source_shape_ref"]["relation_refs"] = (
        collapsed["multi_source_shape_ref"]["relation_refs"][:1]
    )
    with pytest.raises(ComponentWorkNodeError):
        validate_component_work_node_v0_output_ref(collapsed)


def test_component_work_node_preserves_duplicate_source_shape() -> None:
    packet = _product_packet()
    shared_source = _source_ref(suffix="duplicate")
    shared_source["candidate_id"] = "candidate:n400"
    shared_source["candidate_digest"] = "candidate-digest:n400"
    shared_source["reference_id"] = "reference:n400"
    shared_source["reference_digest"] = "reference-digest:n400"
    shared_source["url"] = "https://www.uscis.gov/forms/filing-fees"
    shared_source["domain"] = "www.uscis.gov"
    semantic = deepcopy(packet["semantic_status_payload"])
    semantic.update(
        {
            "dprime_multi_source_relation_count": 2,
            "dprime_multi_source_source_count": 1,
            "dprime_multi_source_relation_set_ref": {
                "status": "created",
                "relation_count": 2,
                "source_count": 1,
                "relation_intake_refs": [
                    _relation_ref(packet, suffix="primary"),
                    _relation_ref(packet, suffix="duplicate"),
                ],
                "evidence_source_refs": [shared_source, shared_source],
            },
            "dprime_multi_source_support_posture_ref": {
                "status": "blocked",
                "source_count": 1,
                "source_display_candidate_refs": [shared_source],
                "currentness_posture": "current",
                "conflict_posture": "duplicate_source",
                "challenge_kind": "source_laundering_risk",
                "answer_path_allowed": False,
            },
            "dprime_scrutineer_challenge_ref": {
                "status": "created",
                "challenge_kind": "source_laundering_risk",
            },
        }
    )
    packet["semantic_status_payload"] = semantic

    refs = component_work_node_v0_refs_from_product_packet(packet)
    shape = refs["component_work_node_v0_output_ref"]["multi_source_shape_ref"]

    assert shape["relation_count"] == 2
    assert shape["source_count"] == 1
    assert shape["relation_ref_count"] >= 2
    assert shape["source_ref_count"] >= 1
    assert shape["challenge_kind"] == "source_laundering_risk"
    assert shape["answer_path_allowed"] is False
    assert shape["best_source_collapse_created"] is False
    assert shape["single_undifferentiated_source_output_created"] is False


def test_component_work_node_preserves_followup_recovery_refs() -> None:
    packet = _product_packet(
        workbench_gap_reentry_ref={
            "schema_version": "workbench_gap_reentry_ref_v1",
            "status": "authorized",
            "packet_digest": "gap-reentry-digest:n400",
            "followup_search_intent_ref": {
                "packet_digest": "followup-intent-digest:n400",
                "status": "created",
            },
            "runkernel_followup_authorization_ref": {
                "authorization_digest": "followup-auth-digest:n400",
                "status": "authorized",
            },
        },
        source_obligation_recovery_authorization={
            "status": "authorized",
            "authorization_digest": "source-recovery-auth-digest:n400",
        },
        source_challenge_recovery_plan={
            "status": "planned",
            "plan_digest": "source-challenge-recovery-plan-digest:n400",
        },
    )

    refs = component_work_node_v0_refs_from_product_packet(packet)
    recovery_refs = refs["component_work_node_v0_output_ref"][
        "followup_recovery_refs"
    ]

    assert len(recovery_refs) >= 3
    assert any(ref.get("packet_digest") == "gap-reentry-digest:n400" for ref in recovery_refs)
    assert any(
        ref.get("authorization_digest") == "source-recovery-auth-digest:n400"
        for ref in recovery_refs
    )
    assert any(
        ref.get("plan_digest") == "source-challenge-recovery-plan-digest:n400"
        for ref in recovery_refs
    )


def _product_packet(**overrides: Any) -> dict[str, Any]:
    plan = build_generic_query_relation_plan(N400_QUERY)
    source_url = "https://www.uscis.gov/forms/filing-fees"
    semantic = {
        "decision": "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED",
        "dprime_relation_intake_ref": {
            "status": "consumed",
            "component_id": plan["component_id"],
            "source_obligation_candidate_ids": [plan["source_obligation_id"]],
            "source_title": "USCIS Form N-400 Filing Fee",
            "source_url": source_url,
            "source_domain": "www.uscis.gov",
            "candidate_id": "candidate:n400",
            "candidate_digest": "candidate-digest:n400",
            "reference_id": "reference:n400",
            "reference_digest": "reference-digest:n400",
        },
        "source_evidence_admission_ref": {
            "status": "custody_created",
            "candidate_id": "candidate:n400",
            "candidate_digest": "candidate-digest:n400",
            "reference_id": "reference:n400",
            "reference_digest": "reference-digest:n400",
        },
        "source_obligation_authority_ref": {
            "status": "consumed",
            "authority_consumed": True,
            "owner": "RunKernel.DPrimeSourceObligationAuthority",
            "source_obligation_authority_id": "source-authority:n400",
        },
        "citation_eligibility_authority_ref": {
            "status": "consumed",
            "authority_consumed": True,
            "owner": "RunKernel.DPrimeCitationSourceHandoffAuthority",
            "citation_source_handoff_id": "citation-handoff:n400",
            "citation_source_handoff_consumed": True,
            "citation_source_records": [
                {
                    "source_id": "source:n400",
                    "candidate_id": "candidate:n400",
                    "candidate_digest": "candidate-digest:n400",
                    "reference_id": "reference:n400",
                    "reference_digest": "reference-digest:n400",
                    "title": "USCIS Form N-400 Filing Fee",
                    "url": source_url,
                    "domain": "www.uscis.gov",
                    "source_obligation_id": plan["source_obligation_id"],
                    "citation_rendering_created": False,
                }
            ],
        },
        "dprime_status": {
            "assessment_status": "assessed",
            "support_relation": "directly_supports",
            "proposal_validation_status": "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED",
            "run_kernel_admission_decision_status": "admitted",
            "semantic_observation_admission_status": "materialized",
            "source_obligation_authority_consumed": True,
            "citation_eligibility_or_source_handoff_authority_consumed": True,
            "objects_created": {
                "semantic_observation": True,
                "component_coverage": True,
                "final_answer_packet": False,
                "author_answer": False,
                "citation_source_display": False,
            },
            "run_kernel_support_admission_ref": {
                "admission_id": "support-admission:n400",
                "admission_digest": "support-admission-digest:n400",
            },
            "semantic_observation_ref": {
                "observation_id": "semantic-observation:n400",
                "observation_digest": "semantic-observation-digest:n400",
            },
            "analyst_finding_component_coverage_ref": {
                "coverage_id": "component-coverage:n400",
                "coverage_digest": "component-coverage-digest:n400",
            },
        },
    }
    packet = {
        "mode": "BUILD",
        "ordinary_entrypoint": "python -m proplex",
        "command_flag": "--mvp-single-relation-live-dogfood-run",
        "run_id": "component-work-node-test",
        "packet_id": "packet:component-work-node-test",
        "decision": semantic["decision"],
        "status_decision": semantic["decision"],
        "blocker_code": semantic["decision"],
        "blocker_detail": "Generic dogfood stops before source/citation display.",
        "failure_attribution_bucket": "closed_phase_surface",
        "relation_plan_consumed": True,
        "relation_plan_id": plan["plan_id"],
        "relation_plan_packet_id": plan["packet_id"],
        "relation_plan_packet_digest": plan["packet_digest"],
        "supported_query_class_id": plan["supported_query_class_id"],
        "source_authority_posture_requirement": (
            plan["source_authority_posture_requirement"]
        ),
        "source_authority_posture_requirement_ref": (
            plan["source_authority_posture_requirement"]["requirement_id"]
        ),
        "component_id": plan["component_id"],
        "component_text": plan["component_text"],
        "requested_answer_type": plan["requested_answer_type"],
        "expected_value_shape": plan["expected_value_shape"],
        "component_answer_type_binding_ref": plan[
            "component_answer_type_binding_ref"
        ],
        "source_obligation_id": plan["source_obligation_id"],
        "source_obligation_text": plan["source_obligation_text"],
        "search_requirement_id": plan["search_requirement_id"],
        "search_requirement_text": plan["search_requirement_text"],
        "relation_plan_dprime_relation_intake_candidate": plan[
            "dprime_relation_intake_candidate"
        ],
        "dprime_relation_intake_ref": semantic["dprime_relation_intake_ref"],
        "selected_answer_bearing_candidate_refs": [
            {
                "candidate_id": "candidate:n400",
                "candidate_digest": "candidate-digest:n400",
                "url": source_url,
                "domain": "www.uscis.gov",
            }
        ],
        "semantic_status_payload": semantic,
        "source_obligation_authority_consumed": True,
        "citation_source_handoff_authority_consumed": True,
        "source_obligation_satisfaction_claimed": False,
        "explicit_non_proofs": [
            "offline ComponentWorkNode test does not claim product correctness"
        ],
        "product_correctness_claimed": False,
    }
    packet.update(overrides)
    return packet


def _relation_ref(packet: Mapping[str, Any], *, suffix: str) -> dict[str, Any]:
    return {
        "relation_intake_id": f"relation:{suffix}",
        "status": "consumed",
        "component_id": packet["component_id"],
        "source_obligation_candidate_ids": [packet["source_obligation_id"]],
        "candidate_id": f"candidate:n400-{suffix}",
        "candidate_digest": f"candidate-digest:n400-{suffix}",
        "reference_id": f"reference:n400-{suffix}",
        "reference_digest": f"reference-digest:n400-{suffix}",
        "source_title": f"USCIS Form N-400 Filing Fee {suffix}",
        "source_url": f"https://www.uscis.gov/{suffix}/n-400-fee",
        "source_domain": "www.uscis.gov",
    }


def _source_ref(*, suffix: str) -> dict[str, Any]:
    return {
        "candidate_id": f"candidate:n400-{suffix}",
        "candidate_digest": f"candidate-digest:n400-{suffix}",
        "reference_id": f"reference:n400-{suffix}",
        "reference_digest": f"reference-digest:n400-{suffix}",
        "title": f"USCIS Form N-400 Filing Fee {suffix}",
        "url": f"https://www.uscis.gov/{suffix}/n-400-fee",
        "domain": "www.uscis.gov",
    }
