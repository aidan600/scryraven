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
from core.searchos_slice_a_product_runtime import SEARCHOS_JUDGMENT_SYSTEM_PROMPT
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _execution_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_offline_judgment_fixture_uses_need_and_read_text_not_custody_presence(
    tmp_path: Path,
) -> None:
    harness = OfflineOrdinaryPipelineHarness(
        tmp_path=tmp_path,
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        raw_author_response="unused",
    )
    authorized = {
        "schema_version": "searchos_judgment_request_v2",
        "judgment_request_id": "searchos-judgment-request:fixture",
        "judgment_request_digest": "a" * 64,
        "slot_ref": {"slot_id": "slot-1", "slot_digest": "b" * 64},
        "candidate_use_options": [],
        "read_custody_refs": [
            {
                "read_custody_material_id": "searchos-read-custody:fixture",
                "read_custody_material_digest": "c" * 64,
            }
        ],
        "legal_actions": [
            "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "PROPOSE_FOLLOWUP_QUERY",
            "HANDOFF_UNRESOLVED",
        ],
    }
    base = {
        "schema_version": "searchos_judgment_model_input_v1",
        "authorized_request": authorized,
        "active_need": {
            "component": {
                "user_facing_question": "What is Alpha's current official operating rule?"
            },
            "source_obligation": {
                "kind": "official_current",
                "strictness": "required",
            },
        },
    }
    useful = {
        **base,
        "read_custody_materials": [
            {
                "read_custody_ref": authorized["read_custody_refs"][0],
                "bounded_text": "Alpha's current official operating rule is Rule 17.",
            }
        ],
    }
    insufficient = {
        **base,
        "read_custody_materials": [
            {
                "read_custody_ref": authorized["read_custody_refs"][0],
                "bounded_text": "This page contains only a general company history.",
            }
        ],
    }

    useful_decision = json.loads(
        harness.ask_model(
            json.dumps(useful),
            SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
        )
    )
    insufficient_decision = json.loads(
        harness.ask_model(
            json.dumps(insufficient),
            SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
        )
    )

    assert useful_decision["action"] == (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    )
    assert insufficient_decision["action"] != useful_decision["action"]


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
    post_read_calls = [
        item
        for item in harness.read_assessment_calls
        if item["bounded_read_character_count"] > 0
    ]
    assert post_read_calls
    assert all(
        item["component_question"]
        == "What is Alpha's current official operating rule?"
        and item["source_obligation_kind"]
        in {"official_current", "source_bound_numeric"}
        and item["source_obligation_strictness"] == "required"
        and item["search_work_plan_ref"]
        and item["search_requirement_ref"]
        and item["answer_contract_ref"]
        for item in post_read_calls
    )
    assert harness.full_search_judgment_inputs == []
    assert trace["searchos_slice_a"]["all_passages_iteration_append_count"] == 0


def test_readable_insufficient_read_remains_iterative_and_is_not_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_url = "https://alpha.example/insufficient"
    second_url = "https://alpha.example/useful"
    transient_sentinel = "TRANSIENT_READ_JUDGMENT_SENTINEL_513"
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        evidence_rows=[
            {
                "title": "Alpha general history",
                "url": first_url,
                "text": "Directional candidate one.",
            },
            {
                "title": "Alpha official rule",
                "url": second_url,
                "text": "Directional candidate two.",
            },
        ],
        read_content_by_url={
            first_url: (
                transient_sentinel
                + " This page contains only a general company history."
            ),
            second_url: "Alpha's current official operating rule is Rule 17.",
        },
    )

    state = harness.run_kernel.state.searchos_state
    dispositions = [
        record
        for slot in state["slots_by_id"].values()
        for record in dict(slot.get("candidate_option_dispositions") or {}).values()
    ]
    assert any(item["disposition"] == "read_insufficient" for item in dispositions)
    assert all(
        item.get("reason_code") == "required_information_absent"
        for item in dispositions
        if item["disposition"] == "read_insufficient"
    )
    assert harness.read_transport_calls == [first_url, second_url]
    assert any(
        item["bounded_read_character_count"] > 0
        for item in harness.read_assessment_calls
    )
    assert outcome.execution_trace["searchos_slice_a"]["readiness_projection"][
        "all_required_slots_slice_a_ready"
    ] is True
    assert not any(
        "transport_failure" in str(slot.get("latest_reason") or "")
        for slot in state["slots_by_id"].values()
    )

    durable_surfaces = {
        "searchos_state": state,
        "authorized_action_inputs": {
            action_id: action.inputs
            for action_id, action in harness.run_kernel.state.issued_actions.items()
        },
        "projections": harness.run_kernel.state.projections,
        "execution_trace": outcome.execution_trace,
        "execution_jsonl": (tmp_path / "execution.jsonl").read_text(
            encoding="utf-8"
        ),
    }
    assert transient_sentinel not in json.dumps(
        durable_surfaces,
        sort_keys=True,
        default=str,
    )
    assert harness.full_search_judgment_inputs == []


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
