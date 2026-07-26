"""PRODUCT-PATH-REGRESSION: SearchOS/AnalystOS ordinary offline gate."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.searchos_analystos_offline_scenarios import (
    AIRCRAFT_RESULT,
    BOUNDED_LIMIT,
    CASE_1,
    CASE_2,
    CASE_3,
    CASE_4,
    CASE_5,
    CASE_6,
    CASE_7,
    DEPTH_TWO_RESULT,
    DIRECT_RESULT,
    FUEL_RESULT,
    NESTED_CLASS_RESULT,
    NESTED_RESULT,
    PASS,
    SCENARIOS,
    SEARCHED_RESULT,
    ScenarioExecution,
    run_offline_integration_scenario,
)


def _target(execution: ScenarioExecution, component_id: str) -> dict[str, Any]:
    return next(
        dict(item)
        for item in execution.observation_packet["sufficiency"]["answer_target_fulfillments"]
        if dict(item).get("component_id") == component_id
    )


def _supporting(execution: ScenarioExecution, component_id: str) -> dict[str, Any]:
    return next(
        dict(item)
        for item in execution.observation_packet["sufficiency"]["supporting_premise_readiness"]
        if dict(item).get("component_id") == component_id
    )


def _synthesis(execution: ScenarioExecution, key: str) -> dict[str, Any]:
    return next(
        dict(item)
        for item in execution.observation_packet["graph_v1"]["synthesis_proposals"]
        if dict(item).get("synthesis_key") == key
    )


def _assert_trace(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert set(packet) == {
        "scenario_id",
        "mode",
        "root_query",
        "question_meaning_record",
        "initial_answer_contract_ref",
        "answer_contract_history",
        "components",
        "search_work_and_query_plan",
        "component_analyst",
        "cross_component_analyst",
        "proposal_registry",
        "contract_amendment",
        "searchos",
        "direct_support",
        "graph_v1",
        "whole_case_analyst_rerun",
        "sufficiency",
        "final_answer_packet",
        "author",
        "unexpected_calls_or_mutations",
        "status",
    }
    assert packet["root_query"] == execution.scenario.root_query
    assert packet["mode"] == execution.scenario.mode
    assert packet["question_meaning_record"]["ref"]
    assert packet["initial_answer_contract_ref"]
    assert packet["answer_contract_history"]["current_ref"]
    assert packet["components"]
    assert packet["component_analyst"]["input_context"]
    assert packet["direct_support"]["semantic_observation_refs"]
    assert packet["direct_support"]["component_coverage_refs"]
    assert packet["graph_v1"]["ref"]
    assert packet["sufficiency"]["decision"]
    unexpected = packet["unexpected_calls_or_mutations"]
    assert unexpected["forbidden_live_calls"] == []
    assert unexpected["unexpected_model_calls"] == []
    assert unexpected["legacy_recovery_projection_present"] is False
    assert execution.harness.graph_reproof_failures == [], execution.harness.graph_reproof_failures
    serialized = repr(packet).casefold()
    for forbidden in (
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "api_key",
        "database_row",
        "private_log",
    ):
        assert forbidden not in serialized


def _assert_case_1(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert packet["contract_amendment"]["record_refs"] == []
    assert packet["searchos"]["cycle_admissions"] == []
    assert packet["proposal_registry"]["proposals"] == []
    assert packet["cross_component_analyst"]["output_refs"] == []
    assert packet["graph_v1"]["synthesis_proposals"] == []
    target = _target(execution, "harbor_filing_route")
    assert target["fulfillment_status"] == "fulfilled_direct"
    assert target["selected_support_kind"] == "direct"
    assert packet["final_answer_packet"]["direct_entries"]
    assert packet["final_answer_packet"]["admitted_synthesis_entries"] == []
    assert packet["author"]["call_count"] == 1
    assert DIRECT_RESULT in execution.outcome.report
    assert packet["status"] == PASS


def _assert_case_2(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert len(packet["contract_amendment"]["record_refs"]) == 1
    assert len(packet["contract_amendment"]["admission_refs"]) == 1
    assert len(packet["contract_amendment"]["application_refs"]) == 1
    assert len(packet["searchos"]["cycle_admissions"]) == 1
    assert packet["searchos"]["cycle_admissions"][0]["generation_depth"] == 1
    assert packet["searchos"]["cycle_terminals"][0]["terminal_status"] == "recovered"
    assert len(execution.harness.search_calls) == 2
    target = _target(execution, "harbor_route_target")
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert target["inferred_fulfillment_ref"]["semantic_inference_depth"] == 1
    assert _synthesis(execution, "harbor_route_target")["relationship_admission_ref"]
    assert packet["final_answer_packet"]["admitted_synthesis_entries"]
    assert packet["author"]["call_count"] == 1
    assert SEARCHED_RESULT in execution.outcome.report
    assert packet["status"] == PASS


def _assert_case_3(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert packet["searchos"]["cycle_admissions"] == []
    assert packet["contract_amendment"]["record_refs"] == []
    intermediate = _supporting(execution, "compliance_class")
    target = _target(execution, "meridian_route_target")
    assert intermediate["fulfillment_status"] == "fulfilled_inferred"
    assert intermediate["inferred_fulfillment_ref"]["semantic_inference_depth"] == 1
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert target["inferred_fulfillment_ref"]["semantic_inference_depth"] == 2
    assert _synthesis(execution, "compliance_class")["semantic_inference_depth"] == 1
    assert _synthesis(execution, "meridian_route_target")["semantic_inference_depth"] == 2
    assert packet["whole_case_analyst_rerun"]["rerun_count"] >= 1
    assert packet["author"]["call_count"] == 1
    assert DEPTH_TWO_RESULT in execution.outcome.report
    assert packet["status"] == PASS


def _assert_case_4(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert len(packet["searchos"]["cycle_admissions"]) == 1
    assert packet["searchos"]["cycle_terminals"][0]["terminal_status"] == "recovered"
    intermediate = _supporting(execution, "nested_compliance_class")
    target = _target(execution, "nested_route_target")
    assert intermediate["fulfillment_status"] == "fulfilled_inferred"
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert target["inferred_fulfillment_ref"]["semantic_inference_depth"] == 2
    assert packet["whole_case_analyst_rerun"]["rerun_count"] >= 2
    assert NESTED_CLASS_RESULT in repr(packet["final_answer_packet"])
    assert NESTED_RESULT in execution.outcome.report
    assert packet["author"]["call_count"] == 1
    assert packet["status"] == PASS


def _assert_case_5(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert len(packet["searchos"]["cycle_admissions"]) == 1
    assert packet["searchos"]["cycle_admissions"][0]["generation_depth"] == 1
    searched = [
        item for item in packet["proposal_registry"]["proposals"] if item.get("classification") == "searched_premise"
    ]
    assert len(searched) == 2
    statuses = {
        item.get("status") for item in packet["proposal_registry"]["lifecycle"].values() if isinstance(item, dict)
    }
    assert {"consumed", "rejected"} <= statuses
    assert _target(execution, "solace_route_target")["fulfillment_status"] == ("unfulfilled")
    assert packet["graph_v1"]["runkernel_relationship_admission_refs"] == []
    assert packet["sufficiency"]["final_answer_allowed"] is False
    assert packet["final_answer_packet"]["admitted_synthesis_entries"] == []
    assert packet["author"]["called"] is False
    assert len(packet["searchos"]["cycle_admissions"]) == len(packet["searchos"]["cycle_terminals"])
    assert packet["status"] == BOUNDED_LIMIT


def _assert_case_6(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert len(packet["searchos"]["cycle_admissions"]) == 1
    assert packet["searchos"]["cycle_terminals"][0]["terminal_status"] == "recovered"
    assert not execution.harness.distractor_urls.intersection(execution.harness.read_transport_calls)
    assert execution.harness.correct_recovery_urls.intersection(execution.harness.read_transport_calls)
    contexts = packet["cross_component_analyst"]["input_context"]
    assert contexts
    assert all(item["requested_synthesis_directive"] == execution.scenario.root_query for item in contexts)
    parent_context = next(
        item
        for context in contexts
        for item in context["accepted_component_context"]
        if item.get("component_id") == "fuel_expense_parent"
    )
    assert parent_context["component_purpose"] == "supporting_premise"
    assert parent_context["user_facing_question"]
    assert parent_context["acceptance_criteria"]
    assert "fuel_use_basis" in parent_context["dependency_component_ids"]
    assert _supporting(execution, "fuel_expense_parent")["fulfillment_status"] == "fulfilled_inferred"
    target = _target(execution, "aircraft_cost_target")
    assert target["fulfillment_status"] == "fulfilled_inferred"
    assert target["inferred_fulfillment_ref"]["semantic_inference_depth"] == 2
    assert packet["whole_case_analyst_rerun"]["rerun_count"] >= 2
    assert FUEL_RESULT in repr(packet["final_answer_packet"])
    assert AIRCRAFT_RESULT in execution.outcome.report
    assert packet["author"]["call_count"] == 1
    assert packet["status"] == PASS


def _assert_case_7(execution: ScenarioExecution) -> None:
    packet = execution.observation_packet
    assert len(packet["searchos"]["cycle_admissions"]) == 1
    assert packet["searchos"]["cycle_terminals"][0]["terminal_status"] in {
        "exhausted_insufficient",
        "failed",
    }
    assert _target(execution, "nonclosure_route_target")["fulfillment_status"] == "unfulfilled"
    assert _supporting(execution, "nonclosure_compliance_class")["fulfillment_status"] == "unfulfilled"
    assert packet["graph_v1"]["runkernel_relationship_admission_refs"] == []
    assert packet["sufficiency"]["final_answer_posture"] in {
        "partial_answer",
        "insufficient",
        "blocked",
        "blocked_required_needs",
        "blocked_before_author",
    }, packet["sufficiency"]
    assert packet["final_answer_packet"]["admitted_synthesis_entries"] == []
    assert packet["author"]["call_count"] == 1
    assert "no compliance class or filing route is warranted" in (execution.outcome.report)
    assert packet["status"] == PASS


ASSERTIONS = {
    CASE_1: _assert_case_1,
    CASE_2: _assert_case_2,
    CASE_3: _assert_case_3,
    CASE_4: _assert_case_4,
    CASE_5: _assert_case_5,
    CASE_6: _assert_case_6,
    CASE_7: _assert_case_7,
}


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[item.scenario_id for item in SCENARIOS],
)
def test_searchos_analystos_offline_integration_scenario(
    scenario,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution = run_offline_integration_scenario(
        scenario,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    _assert_trace(execution)
    ASSERTIONS[scenario.scenario_id](execution)


def test_integration_gate_has_no_low_level_authority_bypass() -> None:
    """The gate may inspect canonical state but may not manufacture it."""

    test_path = Path(__file__)
    fixture_path = test_path.parent / "fixtures" / "searchos_analystos_offline_scenarios.py"
    forbidden = {
        "AnalystQueryResolutionProposalV1",
        "ContractAmendmentRecord",
        "admit_synthesis_node_via_runkernel",
        "authorize_contract_amendment_admission",
        "authorize_contract_amendment_application",
        "authorize_searchos_recovery_admission",
        "authorize_searchos_recovery_terminal",
        "authorize_searched_premise_recovery_from_analyst_proposals",
        "bind_analyst_query_resolution_proposal",
        "bind_inferred_resolution_proposal_via_runkernel",
        "component_work_graph_v1_from_cross_component_artifact",
        "execute_searchos_recovery_cycle",
        "prepare_final_answer_packet_author_handoff_from_scope",
        "reduce_component_work_graph_v1",
        "reduce_selective_invalidation_via_runkernel",
    }
    called, imported = set(), set()
    for path in (test_path, fixture_path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
            elif isinstance(node, ast.ImportFrom):
                imported.update(alias.name for alias in node.names)
    assert not forbidden.intersection(called)
    assert not forbidden.intersection(imported)
    fixture_source = fixture_path.read_text(encoding="utf-8")
    assert "orchestrator.run_pipeline(" in fixture_source
    assert "install_handoff_capture(" in fixture_source
    assert '"raw_prompt_retained": False' in fixture_source
