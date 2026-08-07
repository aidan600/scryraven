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
from typing import Any

import pytest

import core.pipeline_orchestrator as pipeline_orchestrator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
)
from core.prompts import DEFAULT_SYSTEM
from core.run_kernel import ActionType
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION,
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
    build_bounded_searchos_n1_causal_projection,
    build_searchos_judgment_decision_contract_v1,
)
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _execution_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _establish_official_current_qualification_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original = multicomponent._qualify_searchos_read_material_after_component_dprime

    def qualify(*args: Any, **kwargs: Any) -> Any:
        bindable = kwargs["bindable"]
        facts = {
            "source_tier": "official",
            "source_class": "official_current_rules",
            "currentness_signal": "current",
            "eligible_for_stronger_obligation": True,
        }
        bindable.passage.update(facts)
        bindable.candidate_record.update(facts)
        candidate = kwargs["run_kernel"].state.evidence_ledger.candidates[
            bindable.evidence_ref_id
        ]
        for key, value in facts.items():
            setattr(candidate, key, value)
        lineage = dict(bindable.passage["searchos_qualification_lineage"])
        lineage["source_facts"] = {
            **dict(lineage.get("source_facts") or {}),
            **facts,
        }
        bindable.passage["searchos_qualification_lineage"] = lineage
        return original(*args, **kwargs)

    monkeypatch.setattr(
        multicomponent,
        "_qualify_searchos_read_material_after_component_dprime",
        qualify,
    )


def test_production_judgment_prompt_states_the_strict_validator_contract() -> None:
    normalized_prompt = " ".join(SEARCHOS_JUDGMENT_SYSTEM_PROMPT.split())
    required_instructions = (
        "copy judgment_request_id, judgment_request_digest, and slot_id exactly",
        "read_insufficient assessment for every current READ custody ref",
        "PROPOSE_FOLLOWUP_QUERY authors new bounded followup_query text",
        "Forbidden fields must be absent",
        "active_need",
        "candidate_directional_contexts",
        "read_custody_materials",
        "authorized_request.legal_actions",
        "authorized_request.candidate_use_options",
        "authorized_request.read_custody_refs",
        "this is the only action allowed to author",
        "QueryPlan independently validates the exact text",
        "Never invent or alter a URL, authority ref",
        "Do not treat custody-ref presence alone as readiness",
    )

    assert all(
        instruction in normalized_prompt
        for instruction in required_instructions
    )
    assert "Never invent a URL, query" not in SEARCHOS_JUDGMENT_SYSTEM_PROMPT


def test_transient_decision_contract_describes_every_action_and_input_role() -> None:
    contract = build_searchos_judgment_decision_contract_v1()
    shared = [
        "schema_version",
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
        "action",
        "reason",
    ]
    action_expectations = {
        "REQUEST_READ_PAGE": (
            [*shared, "candidate_use_option_ref"],
            {"read_custody_refs", "followup_query"},
            "required_exact_if_current_custody_else_absent",
        ),
        "PROPOSE_FOLLOWUP_QUERY": (
            [*shared, "followup_query"],
            {"candidate_use_option_ref", "read_custody_refs"},
            "required_exact_if_current_custody_else_absent",
        ),
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION": (
            [*shared, "read_custody_refs"],
            {
                "candidate_use_option_ref",
                "followup_query",
                "read_custody_assessments",
            },
            "forbidden",
        ),
        "HANDOFF_UNRESOLVED": (
            shared,
            {"candidate_use_option_ref", "read_custody_refs", "followup_query"},
            "required_exact_if_current_custody_else_absent",
        ),
    }

    assert contract["schema_version"] == (
        SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION
    )
    assert contract["contract_name"] == "SearchOSJudgmentDecisionContractV1"
    assert contract["decision_schema_version"] == "searchos_judgment_decision_v1"
    assert contract["shared_required_fields"] == shared
    assert contract["unsupported_fields_forbidden"] is True
    assert set(contract["input_field_roles"]) == {
        "authorized_request",
        "active_need",
        "candidate_directional_contexts",
        "read_custody_materials",
    }
    assert set(contract["actions"]) == set(action_expectations)
    for action, (required, forbidden, assessment_mode) in action_expectations.items():
        action_contract = contract["actions"][action]
        assert action_contract["required_fields"] == required
        assert set(action_contract["forbidden_fields"]) == forbidden
        assert action_contract["read_custody_assessments_mode"] == assessment_mode
    assert "copy exactly one" in contract["actions"]["REQUEST_READ_PAGE"][
        "candidate_use_option_ref_rule"
    ]
    followup_contract = contract["actions"]["PROPOSE_FOLLOWUP_QUERY"]
    assert "accepted active need and the inspected material" in followup_contract[
        "followup_query_rule"
    ]
    assert set(followup_contract["authorship_forbidden"]) == {
        "urls",
        "authority_refs",
        "component_refs",
        "source_obligation_refs",
        "candidate_refs",
        "provider_choices",
    }
    handoff_contract = contract["actions"][
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    ]
    assert "nonempty selection of exact refs" in handoff_contract[
        "read_custody_refs_rule"
    ]
    assert "not simultaneously labeled insufficient" in handoff_contract[
        "semantic_handoff_rule"
    ]
    assert "not success" in contract["actions"]["HANDOFF_UNRESOLVED"][
        "unresolved_rule"
    ]
    assessment_contract = contract["post_read_assessment_contract"]
    assert assessment_contract["one_per_current_custody_ref"] is True
    assert assessment_contract["required_fields"] == [
        "reviewed_custody_ref",
        "material_disposition",
        "reason_code",
    ]
    assert assessment_contract["material_disposition"] == "read_insufficient"
    assert contract["durable_retention_allowed"] is False
    assert len(contract["decision_contract_digest"]) == 64


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
        "decision_contract": build_searchos_judgment_decision_contract_v1(),
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


def test_one_component_read_credits_only_exact_owned_obligation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
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
    coverage_ref = harness.run_kernel.state.projections[
        "multicomponent_component_admission"
    ]["component_admission_refs"][-1]["component_coverage_ref"]
    terminal_slot = next(
        item
        for item in harness.run_kernel.state.searchos_state[
            "slots_by_id"
        ].values()
        if item["slot_ref"]["slot_id"] in outcomes
    )
    assert coverage_ref["coverage_state"] == "satisfied"
    assert coverage_ref["answer_component_id"] == terminal_slot[
        "component_ref"
    ]["component_id"]
    assert coverage_ref["component_revision"] == terminal_slot[
        "component_ref"
    ]["component_revision"]
    assert coverage_ref["component_digest"] == terminal_slot[
        "component_ref"
    ]["component_digest"]
    assert coverage_ref["source_obligation_ids"] == [
        terminal_slot["slot_ref"]["source_obligation_id"]
    ]
    assert coverage_ref["source_requirement_ids"]
    assert coverage_ref["candidate_ids"]
    assert coverage_ref["owned_requirement_candidate_refs"]
    assert readiness["all_required_slots_slice_a_ready"] is True
    assert readiness["required_ready_count"] == 1
    assert readiness["required_slot_count"] == readiness["required_ready_count"]
    assert "existing_gap_recovery" not in searchos_projection
    assert searchos_projection.get("component_receiver_failure") is None
    exact_ready_outcomes = [
        item
        for item in outcomes.values()
        if item["semantic_admission_status"] == "admitted"
    ]
    assert len(exact_ready_outcomes) == 1
    assert exact_ready_outcomes[0][
        "searchos_handoff_material_consumed"
    ] is True
    assert all(
        item["semantic_admission_status"] == "not_admitted"
        for item in outcomes.values()
        if item not in exact_ready_outcomes
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
    assert all(
        item["decision_contract_schema_version"]
        == SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION
        and len(str(item["decision_contract_digest"])) == 64
        and item["decision_contract_actions"]
        == [
            "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "HANDOFF_UNRESOLVED",
            "PROPOSE_FOLLOWUP_QUERY",
            "REQUEST_READ_PAGE",
        ]
        for item in harness.read_assessment_calls
    )
    assert harness.full_search_judgment_inputs == []
    assert trace["searchos_slice_a"]["all_passages_iteration_append_count"] == 0


def test_readable_insufficient_read_remains_iterative_and_is_not_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    first_url = "https://alpha.example/insufficient"
    second_url = "https://alpha.example/useful"
    transient_sentinel = "TRANSIENT_READ_JUDGMENT_SENTINEL_513"
    decision_contract_sentinel = (
        "The model has inspected every existing READ material and determined "
        "that it does not satisfy the active need, so the selected non-handoff "
        "action is justified."
    )
    assert decision_contract_sentinel in json.dumps(
        build_searchos_judgment_decision_contract_v1(),
        sort_keys=True,
    )
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
    exact_readiness = outcome.execution_trace["searchos_slice_a"][
        "readiness_projection"
    ]
    assert exact_readiness[
        "all_required_slots_slice_a_ready"
    ] is True
    assert exact_readiness["required_ready_count"] == 1
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
        "run_outcome": outcome,
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
    assert decision_contract_sentinel not in json.dumps(
        durable_surfaces,
        sort_keys=True,
        default=str,
    )
    assert harness.full_search_judgment_inputs == []


def test_required_unresolved_slot_reaches_sufficiency_owned_blocked_fap(
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
    assert "final_answer_packet" in trace
    assert harness.run_kernel.state.sufficiency_judgment_history
    assert (
        harness.run_kernel.state.sufficiency_judgment_history[-1][
            "final_answer_allowed"
        ]
        is False
    )
    subordinate_block = harness.run_kernel.state.projections[
        "searchos_required_needs_block"
    ]
    assert subordinate_block["sufficiency_adjudication_required"] is True
    assert subordinate_block["subordinate_to_sufficiency"] is True
    assert {
        item["blocker_class"]
        for item in subordinate_block["blocker_facts"]
    } == {"recovery_ineligible"}
    assert {
        item["interpretation"]
        for item in subordinate_block["blocker_facts"]
    } == {"lawful_recovery_ineligible"}
    block_consumption = harness.run_kernel.state.sufficiency_judgment_history[
        -1
    ]["searchos_required_needs_block_consumption"]
    assert block_consumption["final_blocker_interpretation"] == (
        "lawful_recovery_ineligible"
    )
    assert "final_answer_packet_allowed" not in subordinate_block
    assert "author_execution_allowed" not in subordinate_block
    action_types = [
        action.action_type
        for action in harness.run_kernel.state.issued_actions.values()
    ]
    assert action_types.index(
        ActionType.SUFFICIENCY_JUDGMENT_DECIDE
    ) < action_types.index(ActionType.FINAL_ANSWER_PACKET_PREPARE)
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
    assert "terminal_kind" not in execution_event
    assert persisted_searchos["readiness_projection_ref"] == (searchos["readiness_projection_ref"])
    assert persisted_searchos["required_needs_block_ref"] == (searchos["required_needs_block_ref"])
    assert completed_event["run_id"] == outcome.run_id


def test_component_receiver_and_gap_basis_failures_reach_sufficiency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)

    def fail_component_receiver(*_args: Any, **_kwargs: Any) -> None:
        raise pipeline_orchestrator.OrdinaryMulticomponentRuntimeError(
            "forced component receiver validation failure"
        )

    def reject_gap_basis(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise pipeline_orchestrator.SearchOSExistingGapRecoveryError(
            "forced exact gap-basis rejection"
        )

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        fail_component_receiver,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "build_searchos_existing_gap_basis",
        reject_gap_basis,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
    )

    block = harness.run_kernel.state.projections[
        "searchos_required_needs_block"
    ]
    blocker_classes = {
        item["blocker_class"]
        for item in block["blocker_facts"]
    }
    assert blocker_classes == {
        "component_receiver_failure",
        "gap_basis_rejection",
    }
    assert {
        item["interpretation"]
        for item in block["blocker_facts"]
    } == {"structural_or_validation_blocker"}
    assert harness.run_kernel.state.sufficiency_judgment_history
    assert (
        harness.run_kernel.state.sufficiency_judgment_history[-1][
            "final_answer_allowed"
        ]
        is False
    )
    assert harness.run_kernel.state.sufficiency_judgment_history[-1][
        "searchos_required_needs_block_consumption"
    ]["final_blocker_interpretation"] == (
        "structural_or_validation_blocker"
    )
    action_types = [
        action.action_type
        for action in harness.run_kernel.state.issued_actions.values()
    ]
    assert action_types.index(
        ActionType.SUFFICIENCY_JUDGMENT_DECIDE
    ) < action_types.index(ActionType.FINAL_ANSWER_PACKET_PREPARE)
    assert harness.author_prompts == []
    assert outcome.execution_trace["blocked_fap_terminal"][
        "author_called"
    ] is False


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
    assert "validation_failure" in {
        item["blocker_class"]
        for item in harness.run_kernel.state.projections[
            "searchos_required_needs_block"
        ]["blocker_facts"]
    }
    assert {
        item["interpretation"]
        for item in harness.run_kernel.state.projections[
            "searchos_required_needs_block"
        ]["blocker_facts"]
        if item["blocker_class"] == "validation_failure"
    } == {"structural_or_validation_blocker"}
    assert harness.run_kernel.state.sufficiency_judgment_history
    assert (
        harness.run_kernel.state.sufficiency_judgment_history[-1][
            "final_answer_allowed"
        ]
        is False
    )
    assert harness.run_kernel.state.sufficiency_judgment_history[-1][
        "searchos_required_needs_block_consumption"
    ]["final_blocker_interpretation"] == (
        "structural_or_validation_blocker"
    )
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
    _establish_official_current_qualification_truth(monkeypatch)
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
    assert readiness["all_required_slots_slice_a_ready"] is True
    assert readiness["required_ready_count"] == 2
    assert readiness["required_slot_count"] == readiness["required_ready_count"]
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


def _required_causal_slot(projection: dict[str, Any]) -> dict[str, Any]:
    assert projection["projection_status"] == "available"
    assert projection["required_slot_count"] == 1
    assert len(projection["slots"]) == 1
    return dict(projection["slots"][0])


def test_bounded_searchos_n1_causal_projection_successful_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    outcome, _harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response=(
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
    )
    assert projection is not None
    slot = _required_causal_slot(projection)
    assert projection["all_required_slots_ready"] is True
    assert slot["semantic_handoff_present"] is True
    assert slot["handoff_material_consumed"] is True
    assert slot["component_analyst_proposal_status"] == "proposed"
    assert slot["component_dprime_validation_present"] is True
    assert slot["semantic_admission_status"] == "admitted"
    assert slot["component_coverage_satisfied"] is True
    assert slot["read_custody_observed"] is True
    assert slot["support_kind"] == "official_current"
    assert slot["final_posture"] == "semantically_handed_off"
    assert slot["safe_failure_class"] == "none"


@pytest.mark.parametrize(
    ("decision", "expected_posture", "expected_failure_class"),
    [
        ("MALFORMED", "judgment_failed", "model_output_malformed"),
        ("WRAPPED_JSON", "judgment_failed", "model_output_malformed"),
        ("INVALID_NOMINATION", "stale_or_invalid", "stale_or_invalid"),
    ],
)
def test_bounded_searchos_n1_causal_projection_judgment_failure_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    expected_posture: str,
    expected_failure_class: str,
) -> None:
    outcome, _harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision=decision,
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
    )
    assert projection is not None
    slot = _required_causal_slot(projection)
    assert slot["final_posture"] == expected_posture
    assert slot["safe_failure_class"] == expected_failure_class
    assert slot["semantic_handoff_present"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert slot["component_coverage_satisfied"] is False
    assert slot["read_custody_observed"] is False
    serialized = json.dumps(projection, sort_keys=True)
    assert "fictional-" not in serialized
    assert "Traceback" not in serialized
    assert "Exception" not in serialized


def test_bounded_searchos_n1_causal_projection_read_then_receiver_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)

    def fail_component_receiver(*_args: Any, **_kwargs: Any) -> None:
        raise pipeline_orchestrator.OrdinaryMulticomponentRuntimeError(
            "forced component receiver validation failure"
        )

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        fail_component_receiver,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
    )
    assert projection is not None
    slot = _required_causal_slot(projection)
    assert slot["read_custody_observed"] is True
    assert slot["semantic_handoff_present"] is True
    assert slot["handoff_material_consumed"] is False
    assert slot["component_analyst_proposal_status"] == "not_proposed"
    assert slot["component_dprime_validation_present"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert slot["component_coverage_satisfied"] is False
    assert projection["component_receiver_selected"] is True
    assert projection["component_receiver_failure_class"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert harness.read_transport_calls


def test_bounded_searchos_n1_causal_projection_privacy_allowlist() -> None:
    sentinels = (
        "fictional-raw-query-text-sentinel",
        "https://fixture.invalid/private-url",
        "fictional-passage-text-sentinel",
        "fictional-read-content-sentinel",
        "fictional-model-output-sentinel",
        "fictional-provider-payload-sentinel",
        "fictional-exception-text-sentinel",
        "fictional-embedding-vector-sentinel",
    )
    fixture = {
        "slot_postures": {"slot-1": "judgment_failed"},
        "component_receiver_failure": "OrdinaryMulticomponentRuntimeError",
        "component_receiver_failure_reason": sentinels[6],
        "semantic_material_refs": [
            {
                "source_id": "src-1",
                "url": sentinels[1],
                "bounded_character_count": 12,
                "slot_ref": {"slot_id": "slot-1"},
            }
        ],
        "semantic_outcomes_by_slot": {
            "slot-1": {
                "semantic_handoff_ref": {},
                "component_analyst_proposal_ref": {},
                "component_analyst_proposal_status": "not_proposed",
                "component_dprime_validation_ref": {},
                "component_dprime_validation_status": "not_accepted",
                "semantic_admission_outcome_ref": {},
                "semantic_admission_status": "not_admitted",
                "searchos_handoff_material_consumed": False,
            }
        },
        "readiness_projection": {
            "required_slot_count": 1,
            "optional_slot_count": 0,
            "all_required_slots_slice_a_ready": False,
            "slot_records": [
                {
                    "slot_ref": {
                        "slot_id": "slot-1",
                        "slot_digest": "abc",
                        "component_id": "component-1",
                        "source_obligation_id": "obligation-1",
                    },
                    "requirement_posture": "required",
                    "support_kind": "official_current",
                    "latest_judgment_posture": "judgment_failed",
                    "latest_judgment_reason": (
                        "model_transport_failed:RuntimeError:" + sentinels[6]
                    ),
                    "judgment_call_count": 1,
                    "action_history": [
                        {
                            "event": "judgment_failed",
                            "reason": sentinels[4],
                        }
                    ],
                    "custody_refs": [
                        {
                            "read_custody_material_id": "custody-1",
                            "normalized_url": sentinels[1],
                            "read_content": sentinels[3],
                        }
                    ],
                    "semantic_handoff_ref": {},
                    "slice_a_ready": False,
                }
            ],
        },
        "private_raw": {
            "query": sentinels[0],
            "passage": sentinels[2],
            "provider_payload": sentinels[5],
            "embedding": sentinels[7],
        },
    }
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
    )
    assert projection is not None
    serialized = json.dumps(projection, sort_keys=True)
    for sentinel in sentinels:
        assert sentinel not in serialized
    slot = _required_causal_slot(projection)
    assert slot["safe_failure_class"] == "model_transport_failed"
    assert slot["read_custody_observed"] is True
    assert "custody_refs" not in slot
    assert "action_history" not in slot
    assert "latest_judgment_reason" not in slot
    assert "normalized_url" not in serialized
    assert "private_raw" not in serialized


def test_bounded_searchos_n1_causal_projection_ordinary_output_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    outcome, _harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response=(
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )
    enabled = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
        enabled=True,
    )
    disabled = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
        enabled=False,
    )
    assert enabled is not None
    assert disabled is None
    assert outcome.report
    assert "searchos_n1_causal_projection" not in outcome.execution_trace
    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    assert "readiness_projection" in searchos
    assert "semantic_outcomes_by_slot" in searchos
