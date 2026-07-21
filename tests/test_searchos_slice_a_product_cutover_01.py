"""PRODUCT-PATH-REGRESSION: SearchOS Slice A ordinary cutover.

Proof class: PRODUCT. Validation bucket: phase_focus, with the required-needs
terminal and exact-follow-up nodes promoted to semantic_search_lane. Surface:
SearchOS first-wave, READ/semantic custody, N-component admission, and safe
terminal; navigation and comprehensive recovery remain closed. Runtime path:
offline ordinary product pipeline with fake model/provider responses. Expected
cost: sub-second per node. Promotion posture: durable domain-lane sentinels,
never fast_pr. Replace or narrow when Slice B or recovery/stopping changes the
state machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
)
from core.prompts import DEFAULT_SYSTEM
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
)
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)


def _execution_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_one_component_read_to_semantic_receiver_is_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response=(
            "Alpha's current official operating rule is supported. [[1]](https://alpha.example/report-1)"
        ),
    )

    trace = outcome.execution_trace
    searchos_projection = dict(trace.get("searchos_slice_a") or {})
    readiness = dict(searchos_projection["readiness_projection"])
    outcomes = dict(searchos_projection["semantic_outcomes_by_slot"])

    assert readiness["all_required_slots_slice_a_ready"] is True
    assert readiness["unresolved_required_slots"] == []
    assert readiness["required_ready_count"] == readiness["required_slot_count"]
    assert "required_needs_block_ref" not in searchos_projection
    assert searchos_projection.get("component_receiver_failure") is None
    assert all(
        outcome["component_analyst_proposal_status"] == "proposed"
        and outcome["component_dprime_validation_status"] == "accepted"
        and outcome["semantic_admission_status"] == "admitted"
        and outcome["searchos_handoff_material_consumed"] is True
        for outcome in outcomes.values()
    )
    # Slice-A-ready permits the unchanged downstream answer lifecycle to
    # continue; it does not override that lifecycle's independent FAP policy.
    assert "final_answer_packet" in trace
    assert harness.search_calls
    assert len(harness.search_calls) == 1
    assert len(harness.read_transport_calls) == 1
    assert harness.full_search_judgment_inputs == []
    assert trace["searchos_slice_a"]["all_passages_iteration_append_count"] == 0


def test_required_unresolved_slot_uses_existing_safe_non_author_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision="NO_READ",
    )

    trace = outcome.execution_trace
    searchos = dict(trace["searchos_slice_a"])
    readiness = dict(searchos["readiness_projection"])
    terminal = dict(trace["blocked_fap_terminal"])
    summary = dict(terminal["blocked_fap_summary"])

    assert readiness["all_required_slots_slice_a_ready"] is False
    assert searchos["required_needs_block_ref"]["block_type"] == (SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED)
    assert all(
        item["latest_judgment_posture"] == "unresolved_handoff" for item in readiness["unresolved_required_slots"]
    )
    assert summary["blocked_fap"] is True
    assert summary["final_answer_allowed"] is False
    assert summary["author_input_deferred"] is True
    assert summary["blocked_before_author_input"] is True
    assert terminal["author_called"] is False
    assert terminal["author_payload_derived"] is False
    assert "final_answer_packet" not in trace
    assert harness.author_prompts == []
    assert harness.read_transport_calls == []
    assert len(harness.search_calls) == 1
    assert harness.full_search_judgment_inputs == []
    assert DEFAULT_SYSTEM["evaluator"] not in harness.model_system_prompts
    assert DEFAULT_SYSTEM["expander"] not in harness.model_system_prompts
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] not in (harness.model_system_prompts)
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME] not in (harness.model_system_prompts)
    events = _execution_events(tmp_path / "execution.jsonl")
    [execution_event] = [event for event in events if event.get("event") == "execution"]
    [completed_event] = [event for event in events if event.get("event") == "run_completed"]
    persisted_trace = dict(execution_event["execution_trace"])
    persisted_searchos = dict(persisted_trace["searchos_slice_a"])
    assert execution_event["terminal_kind"] == "safe_blocked_non_author"
    assert persisted_searchos["readiness_projection_ref"] == (searchos["readiness_projection_ref"])
    assert persisted_searchos["required_needs_block_ref"] == (searchos["required_needs_block_ref"])
    assert completed_event["run_id"] == outcome.run_id


@pytest.mark.parametrize(
    "decision",
    ["MALFORMED", "WRAPPED_JSON", "INVALID_NOMINATION"],
)
def test_judgment_failure_is_typed_closed_without_read_or_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision=decision,
    )

    trace = outcome.execution_trace
    searchos = dict(trace["searchos_slice_a"])
    readiness = dict(searchos["readiness_projection"])
    assert readiness["all_required_slots_slice_a_ready"] is False
    expected_posture = (
        "stale_or_invalid" if decision == "INVALID_NOMINATION" else "judgment_failed"
    )
    assert all(
        item["latest_judgment_posture"] == expected_posture
        for item in readiness["unresolved_required_slots"]
    )
    assert searchos["required_needs_block_ref"]["block_type"] == (SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED)
    assert trace["blocked_fap_terminal"]["author_called"] is False
    assert harness.read_transport_calls == []
    assert len(harness.search_calls) == 1
    assert harness.full_search_judgment_inputs == []


def test_exact_model_followup_is_appended_and_dispatched_through_query_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_rows = [
        {
            "title": "Alpha initial directional candidate",
            "url": "https://alpha.example/initial",
            "text": "Initial directional context does not answer the current rule.",
        }
    ]
    followup_rows = [
        {
            "title": "Alpha exact follow-up source",
            "url": "https://alpha.example/followup-new",
            "text": "The exact follow-up source contains the current official rule.",
        }
    ]
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision="FOLLOWUP_THEN_READ",
        evidence_rows=initial_rows,
        followup_evidence_rows=followup_rows,
    )

    trace = outcome.execution_trace
    searchos = dict(trace["searchos_slice_a"])
    iteration_refs = list(searchos["iteration_candidate_set_refs"])
    query_plan = dict(trace["query_plan"])
    exact_query = "Alpha exact model-authored follow-up query"

    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == [exact_query]
    assert "https://alpha.example/followup-new" in harness.read_transport_calls
    assert harness.read_transport_calls[-1] == "https://alpha.example/followup-new"
    assert iteration_refs and iteration_refs[0]["iteration"] == 2
    assert searchos["append_only_lineage_proof_ref"]
    assert query_plan["items"][-1]["authorized_query"] == exact_query
    assert query_plan["items"][-1]["original_query"] == exact_query
    assert query_plan["items"][-1]["metadata"]["evaluator_authority_used"] is False
    assert query_plan["items"][-1]["metadata"]["expander_authority_used"] is False
    assert searchos["all_passages_iteration_append_count"] == 0
    assert searchos["evaluator_invoked_after_first_wave"] is False
    assert searchos["expander_invoked_after_first_wave"] is False
    assert searchos["ag92b_full_search_judgment_invoked"] is False
    assert harness.full_search_judgment_inputs == []
    assert harness.searchos_product_result is not None
    revision_1 = dict(harness.searchos_product_result.revision_1)
    [iteration_set] = harness.searchos_product_result.iteration_candidate_sets
    assert revision_1["initial_identity_count"] == 1
    assert revision_1["selected_candidate_refs"][0]["normalized_url"] == (
        "https://alpha.example/initial"
    )
    assert iteration_set["selected_candidate_refs"][0]["normalized_url"] == (
        "https://alpha.example/followup-new"
    )
    assert iteration_set["parent_candidate_state_ref"] == (
        searchos["revision_1_ref"]
    )
    assert json.dumps(revision_1, sort_keys=True) == json.dumps(
        harness.searchos_product_result.revision_1,
        sort_keys=True,
    )


def test_two_components_use_one_shared_n_component_receiver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="Compare Alpha and Beta current official operating rates.",
        core_topic="Alpha and Beta operating rates",
        primary_entity="Alpha",
        query_type="comparison",
        router_entities=("Alpha", "Beta"),
        researcher_queries=[
            "Alpha current official operating rate",
            "Beta current official operating rate",
        ],
    )

    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    readiness = dict(searchos["readiness_projection"])
    assert readiness["all_required_slots_slice_a_ready"] is True, {
        "unresolved": [
            {
                "slot_id": dict(item["slot_ref"])["slot_id"],
                "reason": item["reason"],
                "posture": item["latest_judgment_posture"],
            }
            for item in readiness["unresolved_required_slots"]
        ],
        "receiver_failure": searchos.get("component_receiver_failure"),
    }
    assert harness.run_kernel is not None
    admissions = dict(harness.run_kernel.state.projections["multicomponent_component_admission"])[
        "component_admission_refs"
    ]
    assert len(admissions) == 2
    assert {item["component_id"] for item in admissions} == {
        "component-1",
        "component-2",
    }
    assert all(item["admission_status"] == "admitted" for item in admissions)
    graph = dict(harness.run_kernel.state.projections["multicomponent_component_work_graph_v1"])
    assert graph["graph_status"] == "ready"
    prompts = harness.model_system_prompts
    assert ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST] in prompts
    assert ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME] in prompts
    assert searchos["all_passages_iteration_append_count"] == 0
    assert len(harness.search_calls) == 1
