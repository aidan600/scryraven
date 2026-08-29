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
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.pipeline_orchestrator as pipeline_orchestrator
import core.quantitative_finalization_authority as quantitative_evaluator
import proplex.__main__ as compatibility_cli
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    safe_packet_digest,
)
from core.prompts import DEFAULT_SYSTEM
from core.run_kernel import ActionType, RunKernel
from core.search_planner_runtime import DeterministicSearchPlannerAdapter
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
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
    PostRetirementOrdinaryPipelineHarness,
    run_post_retirement_ordinary_pipeline,
)


def _execution_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _establish_official_current_qualification_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original = multicomponent._qualify_searchos_read_material_after_component_analyst_case

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
        "_qualify_searchos_read_material_after_component_analyst_case",
        qualify,
    )


def _make_official_current_obligation_id_opaque(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.search_planner_runtime import DeterministicSearchPlannerAdapter

    original = DeterministicSearchPlannerAdapter.produce
    source_id = "obligation:official_current"
    opaque_id = "obligation:opaque_requirement_42"

    def rewrite(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, tuple):
            return tuple(rewrite(item) for item in value)
        return opaque_id if value == source_id else value

    def produce(self: Any, planner_input: dict[str, Any]) -> dict[str, Any]:
        return rewrite(original(self, planner_input))

    monkeypatch.setattr(DeterministicSearchPlannerAdapter, "produce", produce)


def test_production_judgment_prompt_states_the_strict_validator_contract() -> None:
    normalized_prompt = " ".join(SEARCHOS_JUDGMENT_SYSTEM_PROMPT.split())
    required_instructions = (
        "Do not author judgment_request_id, judgment_request_digest, or slot_id",
        "insufficiency reason_code for every current READ custody material id",
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
        "Compact selection means emit only the current authorized identity token",
        "REQUEST_READ_PAGE selects exactly one current authorized_request.candidate_use_options[*].candidate_use_option_ref.candidate_use_option_id",
        "emits that compact candidate_use_option_id",
        "Copy the complete current token character-for-character",
        "including its searchos-option: prefix and full suffix",
        "Completed candidate option tokens are withheld from model-visible READ-custody lineage",
        "Every model-visible candidate_use_option_id belongs to the current authorized_request.candidate_use_options",
        "interpretation_binding_contract may repeat those current basis refs",
        (
            "Never substitute a normalized_url, candidate_id, title, snippet, list "
            "position, shortened token, altered token, or token remembered from an "
            "earlier decision"
        ),
        (
            "If no exact current token can be copied, choose another currently "
            "legal action instead of REQUEST_READ_PAGE"
        ),
        "Do not copy the whole option object",
        "do not copy the whole custody object",
    )

    assert all(
        instruction in normalized_prompt
        for instruction in required_instructions
    )
    assert "Never invent a URL, query" not in SEARCHOS_JUDGMENT_SYSTEM_PROMPT


def test_transient_decision_contract_describes_every_action_and_input_role() -> None:
    contract = build_searchos_judgment_decision_contract_v1()
    mechanical = {
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
    }
    shared = [
        "schema_version",
        "action",
        "reason",
    ]
    action_expectations = {
        "REQUEST_READ_PAGE": (
            [*shared, "candidate_use_option_id"],
            mechanical
            | {
                "candidate_use_option_ref",
                "read_custody_refs",
                "read_custody_material_ids",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
                "semantic_slot_id",
            },
            "required_exact_if_current_custody_else_absent",
        ),
        "PROPOSE_FOLLOWUP_QUERY": (
            [*shared, "followup_query", "discovery_job_class"],
            mechanical
            | {
                "candidate_use_option_id",
                "candidate_use_option_ref",
                "read_custody_refs",
                "read_custody_material_ids",
                "interpretation_binding",
                "semantic_slot_ref",
                "semantic_slot_id",
            },
            "required_exact_if_current_custody_else_absent",
        ),
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION": (
            [*shared, "read_custody_material_ids"],
            mechanical
            | {
                "candidate_use_option_id",
                "candidate_use_option_ref",
                "followup_query",
                "read_custody_assessments",
                "read_custody_refs",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
                "semantic_slot_id",
            },
            "forbidden",
        ),
        "HANDOFF_UNRESOLVED": (
            shared,
            mechanical
            | {
                "candidate_use_option_id",
                "candidate_use_option_ref",
                "read_custody_refs",
                "read_custody_material_ids",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
                "semantic_slot_id",
            },
            "required_exact_if_current_custody_else_absent",
        ),
        "PROPOSE_INTERPRETATION_BINDING": (
            [*shared, "interpretation_binding"],
            mechanical
            | {
                "candidate_use_option_id",
                "candidate_use_option_ref",
                "read_custody_refs",
                "read_custody_material_ids",
                "followup_query",
                "discovery_job_class",
                "read_custody_assessments",
                "semantic_slot_ref",
                "semantic_slot_id",
            },
            "forbidden",
        ),
        "REQUIRE_CLARIFICATION": (
            [*shared, "semantic_slot_id"],
            mechanical
            | {
                "candidate_use_option_id",
                "candidate_use_option_ref",
                "read_custody_refs",
                "read_custody_material_ids",
                "followup_query",
                "discovery_job_class",
                "interpretation_binding",
                "semantic_slot_ref",
            },
            "required_exact_if_current_custody_else_absent",
        ),
    }

    assert contract["schema_version"] == (
        SEARCHOS_JUDGMENT_DECISION_CONTRACT_SCHEMA_VERSION
    )
    assert contract["contract_name"] == "SearchOSJudgmentDecisionContractV4"
    assert contract["decision_schema_version"] == "searchos_judgment_decision_v1"
    assert contract["shared_required_fields"] == shared
    assert contract["copy_exactly_from_authorized_request"] == {}
    assert contract["model_must_not_author"] == [
        "judgment_request_id",
        "judgment_request_digest",
        "slot_id",
    ]
    assert contract["runtime_bound_from_authorized_request"] == {
        "judgment_request_id": "judgment_request_id",
        "judgment_request_digest": "judgment_request_digest",
        "slot_id": "slot_ref.slot_id",
    }
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
    read_contract = contract["actions"]["REQUEST_READ_PAGE"]
    assert "select exactly one current" in read_contract[
        "candidate_use_option_id_rule"
    ]
    assert "candidate_use_option_id" in read_contract[
        "candidate_use_option_id_rule"
    ]
    assert "nested lineage_snapshot_ref" in read_contract[
        "candidate_use_option_id_rule"
    ]
    assert "do not copy the whole option" in read_contract[
        "candidate_use_option_id_rule"
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
    assert "read_custody_material_id" in handoff_contract[
        "read_custody_material_ids_rule"
    ]
    assert "whole-object copies are invalid" in handoff_contract[
        "read_custody_material_ids_rule"
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
        "read_custody_material_id",
        "reason_code",
    ]
    assert assessment_contract["runtime_bound_fields"]["material_disposition"] == (
        "read_insufficient"
    )
    assert "read_custody_material_id" in (
        assessment_contract["read_custody_material_id_rule"]
    )
    assert "do not copy the whole custody object" in (
        assessment_contract["read_custody_material_id_rule"]
    )
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
            "PROPOSE_INTERPRETATION_BINDING",
            "REQUEST_READ_PAGE",
            "REQUIRE_CLARIFICATION",
        ]
        for item in harness.read_assessment_calls
    )
    assert trace["searchos_slice_a"]["all_passages_iteration_append_count"] == 0


def test_searchos_qualification_uses_exact_accepted_obligation_kind_in_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    _make_official_current_obligation_id_opaque(monkeypatch)
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response="Alpha current official operating rule is supported.",
    )

    terminal_slot = next(
        iter(harness.run_kernel.state.searchos_state["slots_by_id"].values())
    )
    obligation_id = terminal_slot["slot_ref"]["source_obligation_id"]
    assert obligation_id == "obligation:opaque_requirement_42"
    accepted_obligation = next(
        item
        for item in harness.run_kernel.state.initial_answer_contract[
            "accepted_source_obligation_refs"
        ]
        if item["source_obligation_id"] == obligation_id
    )
    assert accepted_obligation["kind"] == "official_current"
    ledger_requirements = [
        item
        for item in harness.run_kernel.state.evidence_ledger.to_projection()
        .to_dict()["source_requirements"]
        if item.get("source_obligation_id") == obligation_id
    ]
    assert len(ledger_requirements) == 1
    assert ledger_requirements[0]["requirement_kind"] == "official_current"
    assert ledger_requirements[0]["status"] == "satisfied"


@pytest.mark.parametrize(
    ("source_kind", "expected_requirement_kind"),
    (
        ("official_current", "official_current"),
        ("legal_current_primary", "legal"),
        ("canonical_documentation", "canonical"),
        ("primary_source_documents", "canonical"),
        ("source_bound_numeric", "source_bound"),
        ("peer_reviewed", "academic"),
        ("reputable_secondary", "general"),
        ("conflict_resolution", "general"),
        ("date_bound_currentness", "current"),
        ("user_document", "user_document"),
        ("no_special_obligation", "general"),
    ),
)
def test_accepted_source_obligation_kinds_have_closed_ledger_normalizations(
    source_kind: str,
    expected_requirement_kind: str,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    assert (
        multicomponent._evidence_ledger_requirement_kind_for_accepted_source_obligation(
            accepted_contract={
                "accepted_source_obligation_refs": [
                    {
                        "source_obligation_id": "obligation:opaque_requirement_42",
                        "kind": source_kind,
                    }
                ]
            },
            source_obligation_id="obligation:opaque_requirement_42",
        )
        == expected_requirement_kind
    )


def test_unknown_accepted_source_obligation_kind_fails_closed() -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    with pytest.raises(multicomponent.OrdinaryMulticomponentRuntimeError):
        multicomponent._evidence_ledger_requirement_kind_for_accepted_source_obligation(
            accepted_contract={
                "accepted_source_obligation_refs": [
                    {
                        "source_obligation_id": "obligation:opaque_requirement_42",
                        "kind": "unsupported_kind",
                    }
                ]
            },
            source_obligation_id="obligation:opaque_requirement_42",
        )


def test_readable_insufficient_read_remains_iterative_and_is_not_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import searchos_slice_a_product_runtime as searchos_runtime

    _establish_official_current_qualification_truth(monkeypatch)
    original_model_input_builder = (
        searchos_runtime._build_searchos_judgment_model_input
    )
    post_read_token_sets: list[tuple[list[str], list[str]]] = []
    model_visible_candidate_token_sets: list[tuple[set[str], set[str]]] = []

    def collect_candidate_tokens(value: Any) -> set[str]:
        if isinstance(value, dict):
            tokens = {
                str(item)
                for key, item in value.items()
                if key == "candidate_use_option_id" and isinstance(item, str)
            }
            for item in value.values():
                tokens.update(collect_candidate_tokens(item))
            return tokens
        if isinstance(value, (list, tuple)):
            tokens: set[str] = set()
            for item in value:
                tokens.update(collect_candidate_tokens(item))
            return tokens
        return set()

    def capture_model_input(**kwargs: Any) -> dict[str, Any]:
        model_input = original_model_input_builder(**kwargs)
        if model_input["read_custody_materials"]:
            authorized_ids = [
                str(
                    dict(item.get("candidate_use_option_ref") or {}).get(
                        "candidate_use_option_id"
                    )
                    or ""
                )
                for item in model_input["authorized_request"]["candidate_use_options"]
            ]
            directional_ids = [
                str(
                    dict(item.get("candidate_use_option_ref") or {}).get(
                        "candidate_use_option_id"
                    )
                    or ""
                )
                for item in model_input["candidate_directional_contexts"]
            ]
            post_read_token_sets.append((authorized_ids, directional_ids))
            model_visible_candidate_token_sets.append(
                (set(authorized_ids), collect_candidate_tokens(model_input))
            )
        return model_input

    monkeypatch.setattr(
        searchos_runtime,
        "_build_searchos_judgment_model_input",
        capture_model_input,
    )
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
    assert post_read_token_sets
    assert all(
        directional_ids == authorized_ids
        for authorized_ids, directional_ids in post_read_token_sets
    )
    assert model_visible_candidate_token_sets
    assert all(
        visible_ids == authorized_ids
        for authorized_ids, visible_ids in model_visible_candidate_token_sets
    )
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
    assert DEFAULT_SYSTEM["evaluator"] not in harness.model_system_prompts
    assert DEFAULT_SYSTEM["expander"] not in harness.model_system_prompts
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] not in (harness.model_system_prompts)
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
    [
        "MALFORMED",
        "WRAPPED_JSON",
        "INVALID_NOMINATION",
        "ALTERED_NOMINATION_REF",
    ],
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
        "stale_or_invalid"
        if decision == "INVALID_NOMINATION"
        else "judgment_failed"
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


def test_first_wave_recoverable_post_read_rejection_can_still_handoff(
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
        read_assessment_decision="OMIT_POST_READ_ASSESSMENTS_ONCE",
        raw_author_response=(
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )

    state = harness.run_kernel.state.searchos_state
    events = [
        item.get("event")
        for slot in state["slots_by_id"].values()
        for item in slot.get("action_history") or ()
        if isinstance(item, dict)
    ]
    assert "judgment_output_rejected" in events
    assert any(
        slot.get("posture") == "semantically_handed_off"
        for slot in state["slots_by_id"].values()
    )
    assert all(
        item.get("stale") is False
        for slot in state["slots_by_id"].values()
        for item in slot.get("custody_refs") or ()
        if isinstance(item, dict)
    )
    readiness = outcome.execution_trace["searchos_slice_a"][
        "readiness_projection"
    ]
    assert readiness["all_required_slots_slice_a_ready"] is True


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


def test_failed_followup_wave_restores_searchos_without_candidate_admission(
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
    original_dispatch = pipeline_orchestrator.execute_main_retrieval_pass_from_scope
    dispatch_calls = 0

    def fail_followup_dispatch(
        scope: dict[str, Any],
        *,
        retrieval_pass_records: list[dict[str, Any]],
    ) -> Any:
        nonlocal dispatch_calls
        dispatch_calls += 1
        if dispatch_calls == 2:
            raise RuntimeError("offline follow-up acquisition failure")
        return original_dispatch(
            scope,
            retrieval_pass_records=retrieval_pass_records,
        )

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_main_retrieval_pass_from_scope",
        fail_followup_dispatch,
    )
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
        followup_evidence_rows=[],
    )

    assert dispatch_calls == 2
    assert len(harness.search_calls) == 1
    assert harness.searchos_product_result is not None
    assert harness.searchos_product_result.iteration_candidate_sets == ()
    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos["iteration_candidate_set_refs"] == []
    slot = next(
        iter(harness.run_kernel.state.searchos_state["slots_by_id"].values())
    )
    assert slot["posture"] == "semantically_handed_off"
    assert any(
        event.get("event") == "followup_acquisition_failed"
        for event in slot["action_history"]
    )
    assert not any(
        event.get("event") == "iteration_candidate_set_admitted"
        for event in slot["action_history"]
    )


def test_repeated_followup_nomination_budget_does_not_reenter_discover(
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
    original_model = PostRetirementOrdinaryPipelineHarness.ask_model
    judgment_calls = 0

    def repeatedly_propose_followup(
        harness: PostRetirementOrdinaryPipelineHarness,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        nonlocal judgment_calls
        if not system_prompt.startswith(SEARCHOS_JUDGMENT_SYSTEM_PROMPT):
            return original_model(harness, prompt, system_prompt, **kwargs)
        judgment_calls += 1
        original = original_model(harness, prompt, system_prompt, **kwargs)
        if judgment_calls == 1:
            return original
        payload = json.loads(prompt)
        authorized = dict(payload.get("authorized_request") or {})
        contract = dict(payload.get("decision_contract") or {})
        return json.dumps(
            {
                "schema_version": contract["decision_schema_version"],
                "action": "PROPOSE_FOLLOWUP_QUERY",
                "followup_query": "Alpha repeated follow-up query",
                "discovery_job_class": (
                    list(authorized["allowed_followup_job_classes"])[0]
                ),
                "reason": "offline repeated follow-up nomination",
            }
        )

    monkeypatch.setattr(
        PostRetirementOrdinaryPipelineHarness,
        "ask_model",
        repeatedly_propose_followup,
    )
    original_dispatch = pipeline_orchestrator.execute_main_retrieval_pass_from_scope
    dispatch_calls = 0

    def fail_every_followup_dispatch(
        scope: dict[str, Any],
        *,
        retrieval_pass_records: list[dict[str, Any]],
    ) -> Any:
        nonlocal dispatch_calls
        dispatch_calls += 1
        if dispatch_calls >= 2:
            raise RuntimeError("offline repeated follow-up acquisition failure")
        return original_dispatch(
            scope,
            retrieval_pass_records=retrieval_pass_records,
        )

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_main_retrieval_pass_from_scope",
        fail_every_followup_dispatch,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        # Fast intentionally has one follow-up nomination per slot.  After
        # the first acquisition failure the next stale PROPOSE projection
        # must terminalize at the reducer budget boundary and never re-enter
        # QueryPlan/discover scheduling.
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        read_assessment_decision="FOLLOWUP_THEN_READ",
        evidence_rows=initial_rows,
        followup_evidence_rows=[],
    )

    assert judgment_calls >= 2
    assert dispatch_calls == 2
    assert harness.searchos_product_result is not None
    assert harness.searchos_product_result.iteration_candidate_sets == ()
    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos["iteration_candidate_set_refs"] == []
    slot = next(
        iter(harness.run_kernel.state.searchos_state["slots_by_id"].values())
    )
    assert slot["posture"] == "budget_exhausted"
    assert sum(
        event.get("event") == "followup_acquisition_failed"
        for event in slot["action_history"]
    ) == 1
    assert not any(
        event.get("event") == "iteration_candidate_set_admitted"
        for event in slot["action_history"]
    )


def test_two_components_use_one_shared_n_component_receiver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent
    from core.ordinary_semantic_producer_runtime import (
        select_bindable_final_passages_for_components as legacy_selector,
    )

    original_receiver = (
        pipeline_orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    )
    original_scheduler_initialize = RunKernel.initialize_multicomponent_graph_scheduler
    packet_contexts: list[dict[str, dict[str, Any]]] = []
    receiver_contexts: list[dict[str, Any]] = []

    def capture_scheduler_initialization(self: Any, **kwargs: Any) -> Any:
        result = original_scheduler_initialize(self, **kwargs)
        packet_contexts.append(
            {
                str(key): deepcopy(dict(value))
                for key, value in kwargs["component_analyst_input_packets"].items()
            }
        )
        return result

    def capture_direct_receiver(
        run_kernel: Any,
        runtime_scope: Mapping[str, Any],
        **kwargs: Any,
    ) -> Any:
        if kwargs.get("allow_searchos_component_receiver") is not True:
            return original_receiver(run_kernel, runtime_scope, **kwargs)
        accepted = run_kernel.state.initial_answer_contract
        component_refs = [
            dict(item)
            for item in accepted["accepted_answer_component_refs"]
        ]
        canonical_materials = [
            deepcopy(dict(item))
            for item in runtime_scope["searchos_slice_a_result"].searchos_semantic_material
        ]
        component_a = component_refs[0]
        material_a = next(
            item
            for item in canonical_materials
            if dict(item["searchos_slot_ref"])["component_id"]
            == component_a["component_id"]
        )
        distractor = deepcopy(material_a)
        for key in (
            "searchos_evidence_ledger_candidate_id",
            "searchos_qualification_lineage",
            "searchos_semantic_handoff_ref",
            "searchos_slot_ref",
        ):
            distractor.pop(key, None)
        distractor.update(
            {
                "title": "Unhanded lexical distractor",
                "text": " ".join(
                    [str(component_a["user_facing_question"])] * 4
                ),
                "_provider": "generic_final_evidence",
                "material_authority": "generic_ranked_passage",
                "support_admitted": False,
            }
        )
        distractor["bounded_text_digest"] = safe_packet_digest(
            {"bounded_text": distractor["text"]}
        )
        distractor_z = deepcopy(distractor)
        distractor_z.update(
            {
                "candidate_id": "generic-final-evidence:z",
                "source_id": "generic-final-evidence:z",
                "title": "Irrelevant generic material Z",
                "text": "Generic material unrelated to either SearchOS handoff.",
            }
        )
        distractor_z["bounded_text_digest"] = safe_packet_digest(
            {"bounded_text": distractor_z["text"]}
        )
        selector_candidates = [distractor, *reversed(canonical_materials)]
        legacy_selected = legacy_selector(
            selector_candidates,
            run_kernel.state.evidence_ledger.to_projection().to_dict(),
            component_refs,
            component_text_by_id={
                str(item["component_id"]): str(item["user_facing_question"])
                for item in component_refs
            },
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            answer_contract_version=accepted["accepted_contract_version"],
            answer_contract_digest=accepted["accepted_contract_digest"],
        )
        assert (
            legacy_selected[component_a["component_id"]].passage["title"]
            == "Unhanded lexical distractor"
        )

        def forbidden_receiver_selector(*_args: Any, **_kwargs: Any) -> Any:
            raise AssertionError(
                "SearchOS component receiver called the legacy passage selector"
            )

        monkeypatch.setattr(
            multicomponent,
            "select_bindable_final_passages_for_components",
            forbidden_receiver_selector,
        )
        scoped_runtime = {
            **dict(runtime_scope),
            "final_top_evidence": [distractor],
        }
        receiver_contexts.append(
            {
                "run_kernel": run_kernel,
                "runtime_scope": scoped_runtime,
                "component_refs": component_refs,
                "canonical_materials": canonical_materials,
                "distractor": distractor,
                "distractor_z": distractor_z,
            }
        )
        return original_receiver(run_kernel, scoped_runtime, **kwargs)

    monkeypatch.setattr(
        RunKernel,
        "initialize_multicomponent_graph_scheduler",
        capture_scheduler_initialization,
    )
    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        capture_direct_receiver,
    )
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
    assert len(packet_contexts) == len(receiver_contexts) == 1

    context = receiver_contexts[0]

    def component_local_binding(
        component_refs: list[dict[str, Any]],
        presented_materials: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        selected = multicomponent._bind_searchos_handoff_materials_for_components(
            run_kernel=context["run_kernel"],
            runtime_scope={
                **context["runtime_scope"],
                "final_top_evidence": presented_materials,
            },
            accepted=context["run_kernel"].state.initial_answer_contract,
            component_refs=component_refs,
        )
        return {
            component_id: {
                "evidence_ref_id": bindable.evidence_ref_id,
                "bounded_text": bindable.passage["text"],
                "bounded_text_digest": bindable.passage["bounded_text_digest"],
                "searchos_semantic_handoff_ref": deepcopy(
                    bindable.passage["searchos_semantic_handoff_ref"]
                ),
                "searchos_slot_ref": deepcopy(
                    bindable.passage["searchos_slot_ref"]
                ),
                "read_custody_ref": deepcopy(
                    bindable.passage["searchos_qualification_lineage"][
                        "read_custody_ref"
                    ]
                ),
                "support_admitted": bindable.passage["support_admitted"],
            }
            for component_id, bindable in selected.items()
        }

    canonical_materials = context["canonical_materials"]
    assert context["runtime_scope"]["final_top_evidence"] == [
        context["distractor"]
    ]
    assert all(
        material not in context["runtime_scope"]["final_top_evidence"]
        for material in canonical_materials
    )

    final_top_evidence_variants = (
        [],
        [context["distractor"]],
        [context["distractor"], context["distractor_z"]],
        [canonical_materials[0], context["distractor"]],
        [context["distractor"], *canonical_materials],
        [*reversed(canonical_materials), context["distractor_z"]],
    )
    invariant_bindings = [
        component_local_binding(context["component_refs"], variant)
        for variant in final_top_evidence_variants
    ]
    assert all(
        binding == invariant_bindings[0]
        for binding in invariant_bindings[1:]
    )

    a_then_b = component_local_binding(context["component_refs"], [])
    b_then_a = component_local_binding(
        list(reversed(context["component_refs"])),
        [context["distractor_z"], context["distractor"]],
    )
    assert a_then_b == b_then_a
    assert set(a_then_b) == {"component-1", "component-2"}
    assert all(
        binding["searchos_slot_ref"]["component_id"] == component_id
        and binding["support_admitted"] is False
        for component_id, binding in a_then_b.items()
    )
    assert a_then_b["component-1"]["evidence_ref_id"] != (
        a_then_b["component-2"]["evidence_ref_id"]
    )
    assert a_then_b["component-1"]["bounded_text"] != (
        a_then_b["component-2"]["bounded_text"]
    )

    analyst_packets = packet_contexts[0]
    assert set(analyst_packets) == set(a_then_b)
    for component_id, binding in a_then_b.items():
        packet = analyst_packets[component_id]
        assert packet["component_ref"]["component_id"] == component_id
        assert packet["component_evidence"]["evidence_ref_id"] == (
            binding["evidence_ref_id"]
        )
        assert packet["component_evidence"]["bounded_text"] == (
            binding["bounded_text"]
        )
        assert packet["component_evidence"]["bounded_text_digest"] == (
            binding["bounded_text_digest"]
        )
        assert packet["component_evidence"]["bounded_text"] != (
            context["distractor"]["text"]
        )


@pytest.mark.parametrize(
    "failure_case",
    (
        "wrong_component",
        "foreign_handoff",
        "mismatched_handoff",
        "slot_lineage_mismatch",
        "custody_lineage_mismatch",
        "altered_bounded_digest",
        "missing_exact_material",
        "duplicate_material_identity",
    ),
)
def test_searchos_receiver_rejects_nonexact_material_before_component_analyst(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_case: str,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original_receiver = (
        pipeline_orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    )
    receiver_calls = 0

    def reject_if_selector_runs(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(
            "SearchOS component receiver called the legacy passage selector"
        )

    def mutate_receiver_input(
        run_kernel: Any,
        runtime_scope: Mapping[str, Any],
        **kwargs: Any,
    ) -> Any:
        nonlocal receiver_calls
        if kwargs.get("allow_searchos_component_receiver") is not True:
            return original_receiver(run_kernel, runtime_scope, **kwargs)
        receiver_calls += 1
        result = runtime_scope["searchos_slice_a_result"]
        materials = [
            deepcopy(dict(item)) for item in result.searchos_semantic_material
        ]
        assert len(materials) == 2
        if failure_case == "wrong_component":
            materials[0]["searchos_slot_ref"] = deepcopy(
                materials[1]["searchos_slot_ref"]
            )
        elif failure_case == "foreign_handoff":
            materials[0]["searchos_semantic_handoff_ref"] = {
                "semantic_handoff_id": "searchos-semantic-handoff:foreign",
                "semantic_handoff_digest": "f" * 64,
            }
        elif failure_case == "mismatched_handoff":
            materials[0]["searchos_semantic_handoff_ref"] = deepcopy(
                materials[1]["searchos_semantic_handoff_ref"]
            )
        elif failure_case == "slot_lineage_mismatch":
            lineage = deepcopy(materials[0]["searchos_qualification_lineage"])
            lineage["slot_ref"] = deepcopy(materials[1]["searchos_slot_ref"])
            materials[0]["searchos_qualification_lineage"] = lineage
        elif failure_case == "custody_lineage_mismatch":
            lineage = deepcopy(materials[0]["searchos_qualification_lineage"])
            lineage["read_custody_ref"]["read_custody_material_digest"] = (
                "e" * 64
            )
            materials[0]["searchos_qualification_lineage"] = lineage
        elif failure_case == "altered_bounded_digest":
            materials[0]["bounded_text_digest"] = "d" * 64
        elif failure_case == "missing_exact_material":
            materials = materials[1:]
        elif failure_case == "duplicate_material_identity":
            materials.append(deepcopy(materials[0]))
        else:  # pragma: no cover - parameter list is closed above
            raise AssertionError(f"unknown failure case {failure_case}")

        scoped_result = replace(
            result,
            searchos_semantic_material=tuple(deepcopy(materials)),
        )
        scoped_runtime = {
            **dict(runtime_scope),
            "searchos_slice_a_result": scoped_result,
            "final_top_evidence": deepcopy(materials),
        }
        monkeypatch.setattr(
            multicomponent,
            "select_bindable_final_passages_for_components",
            reject_if_selector_runs,
        )
        return original_receiver(run_kernel, scoped_runtime, **kwargs)

    monkeypatch.setattr(
        pipeline_orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        mutate_receiver_input,
    )
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

    assert receiver_calls == 1
    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos["component_receiver_failure"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert searchos["component_receiver_failure_reason"].startswith(
        "SearchOS component receiver"
    )
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] not in (
        harness.model_system_prompts
    )
    assert not harness.run_kernel.state.projections.get(
        "multicomponent_component_admission"
    )


def _required_causal_slot(projection: dict[str, Any]) -> dict[str, Any]:
    assert projection["projection_status"] == "available"
    assert projection["required_slot_count"] == 1
    assert len(projection["slots"]) == 1
    return dict(projection["slots"][0])


def test_bounded_searchos_n1_causal_projection_successful_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    def forbidden_receiver_selector(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(
            "N=1 SearchOS component receiver called the legacy passage selector"
        )

    monkeypatch.setattr(
        multicomponent,
        "select_bindable_final_passages_for_components",
        forbidden_receiver_selector,
    )
    scheduler_initializations: list[dict[str, Any]] = []
    packet_contexts: list[dict[str, Any]] = []
    original_scheduler_initialize = RunKernel.initialize_multicomponent_graph_scheduler
    original_packet_install = RunKernel.install_multicomponent_graph_reproof_packet_context

    def capture_scheduler_initialization(self: Any, **kwargs: Any) -> Any:
        result = original_scheduler_initialize(self, **kwargs)
        scheduler_initializations.append(
            {
                "packets": {
                    str(key): dict(value)
                    for key, value in kwargs["component_analyst_input_packets"].items()
                },
                "ready_work": self.derive_current_multicomponent_ready_work(),
            }
        )
        return result

    def capture_packet_install(self: Any, **kwargs: Any) -> Any:
        result = original_packet_install(self, **kwargs)
        packet_contexts.append(
            {
                "packets": {
                    str(key): dict(value)
                    for key, value in kwargs["component_analyst_input_packets"].items()
                },
                "directive": kwargs["requested_synthesis_directive"],
                "scheduler_stage": self.state.projections.get(
                    "multicomponent_graph_scheduler"
                ),
            }
        )
        return result

    monkeypatch.setattr(
        RunKernel,
        "initialize_multicomponent_graph_scheduler",
        capture_scheduler_initialization,
    )
    monkeypatch.setattr(
        RunKernel,
        "install_multicomponent_graph_reproof_packet_context",
        capture_packet_install,
    )
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
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )

    assert len(scheduler_initializations) == 0
    assert len(packet_contexts) == 1
    initialization = packet_contexts[0]
    assert initialization["directive"] == "single_component_direct_admission"
    assert initialization["scheduler_stage"] is None
    assert len(initialization["packets"]) == 1
    [analyst_packet] = initialization["packets"].values()
    assert analyst_packet["supported_query_class"] == (
        "ordinary-bounded-multicomponent-factual-synthesis-v1"
    )
    run_binding = dict(analyst_packet["run_binding"])
    contract = dict(harness.run_kernel.state.initial_answer_contract)
    assert run_binding["run_id"] == outcome.run_id
    assert run_binding["request_id"] == outcome.session_id
    assert run_binding["accepted_contract_version"] == contract["accepted_contract_version"]
    assert run_binding["accepted_contract_digest"] == contract["accepted_contract_digest"]
    evidence = dict(analyst_packet["component_evidence"])
    custody = dict(evidence["candidate_custody_ref"])
    assert evidence["evidence_status"] == "available"
    assert evidence["evidence_ref_id"]
    assert custody["candidate_id"] == evidence["evidence_ref_id"]
    assert harness.run_kernel.state.projections.get("multicomponent_graph_scheduler") is None
    graph = dict(harness.run_kernel.state.projections["multicomponent_component_work_graph_v1"])
    assert graph["dependency_posture"] == "single_component_direct_admission"
    assert graph["graph_status"] == "ready"
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] in harness.model_system_prompts

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
    )
    assert projection is not None
    slot = _required_causal_slot(projection)
    assert projection["all_required_slots_ready"] is True
    assert slot["semantic_handoff_present"] is True
    assert slot["handoff_material_consumed"] is True
    assert slot["component_analyst_case_present"] is True
    assert slot["semantic_admission_status"] == "admitted"
    assert slot["component_coverage_satisfied"] is True
    assert slot["read_custody_observed"] is True
    assert slot["support_kind"] == "official_current"
    assert slot["final_posture"] == "semantically_handed_off"
    assert slot["canonical_slot_posture"] == "semantically_handed_off"
    assert slot["last_searchjudgment_action"] == (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
    )
    assert slot["semantic_handoff_authorization_attempted"] is True
    assert slot["semantic_handoff_sealed"] is True
    assert slot["stale_or_invalid_transition_observed"] is False
    searchos = dict(outcome.execution_trace["searchos_slice_a"])
    attempted_ids = searchos["semantic_handoff_authorization_attempted_slot_ids"]
    assert isinstance(attempted_ids, list)
    assert attempted_ids
    assert set(attempted_ids) <= set(searchos["slot_postures"])
    assert "semantic_handoff_authorization_attempted_slot_ids" not in json.dumps(
        projection,
        sort_keys=True,
    )
    assert slot["safe_failure_class"] == "none"
    assert slot["safe_transport_exception_class"] == "none"
    assert slot["safe_model_output_invalid_subtype"] == "none"
    assert "component_analyst_failure" not in projection
    assert all(
        ROLE_SYSTEM_PROMPTS[role] not in harness.model_system_prompts
        for role in (
            ROLE_CROSS_COMPONENT_ANALYST,
            ROLE_SYNTHESIS_DPRIME,
        )
    )


def test_searchos_receiver_block_cannot_report_completed_or_originate_analyst(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _establish_official_current_qualification_truth(monkeypatch)
    import core.ordinary_multicomponent_synthesis_runtime as multicomponent

    def block_before_analyst_dispatch(*_args: Any, **_kwargs: Any) -> None:
        raise multicomponent._ScheduledSemanticWorkBlocked(
            "forced required scheduler block before Analyst dispatch"
        )

    monkeypatch.setattr(
        multicomponent,
        "_execute_first_pass_n1_component_analyst",
        block_before_analyst_dispatch,
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

    searchos_projection = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos_projection["component_receiver_failure"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert "forced required scheduler block" in searchos_projection[
        "component_receiver_failure_reason"
    ]
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=searchos_projection,
    )
    assert projection is not None
    assert projection["component_receiver_failure_class"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert outcome.execution_trace["analyst_skipped"] is True
    assert outcome.execution_trace["analyst_skip_reason"] == (
        "searchos_component_receiver_failure"
    )
    assert outcome.execution_trace["analyst_skipped_after_economist"] is True
    assert outcome.execution_trace["analyst_after_economist_skip_reason"] == (
        "searchos_component_receiver_failure"
    )
    assert outcome.execution_trace["post_retrieval_fast_path_used"] is False
    assert outcome.execution_trace["pre_analyst_gate_signals"] == [
        "searchos_component_receiver_failure"
    ]
    assert outcome.execution_trace["scrutineer_ran"] is False
    scrutineer_handoff = outcome.execution_trace["scrutineer_remediation_handoff"]
    assert scrutineer_handoff["remediation_dispatch"]["authorized"] is False
    assert scrutineer_handoff["remediation_dispatch"]["dispatch_posture"] == (
        "skipped_searchos_component_receiver_failure"
    )
    assert scrutineer_handoff["resynthesis"]["reanalysis_triggered"] is False
    slot = _required_causal_slot(projection)
    assert slot["component_analyst_case_present"] is False
    assert slot["handoff_material_consumed"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert harness.analyst_calls == 0
    assert DEFAULT_SYSTEM["analyst"] not in harness.model_system_prompts
    assert DEFAULT_SYSTEM["synth_evaluator"] not in harness.model_system_prompts
    assert not any(
        prompt.startswith("You are a ruthless fact-checker")
        for prompt in harness.model_system_prompts
    )
    assert not any(
        prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
        for prompt in harness.model_system_prompts
    )


def _install_q1_plural_planner_contract(
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_obligation_id: str = "obligation:official_current",
    source_obligation_kind: str = "official_current",
) -> None:
    original_produce = DeterministicSearchPlannerAdapter.produce

    def produce(self: Any, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        result = json.loads(json.dumps(original_produce(self, planner_input)))
        component = dict(result["answer_components"][0])
        component.update(
            {
                "semantic_slot_ids": ["slot:rel_tol", "slot:abs_tol"],
                "source_obligation_candidate_ids": [source_obligation_id],
                "user_facing_question": (
                    "What are the defaults for rel_tol and abs_tol in math.isclose()?"
                ),
            }
        )
        result["semantic_slots"] = [
            {
                "slot_id": "slot:rel_tol",
                "slot_kind": "parameter",
                "status": "explicit",
                "selected_value": "rel_tol",
                "materiality": "material",
            },
            {
                "slot_id": "slot:abs_tol",
                "slot_kind": "parameter",
                "status": "explicit",
                "selected_value": "abs_tol",
                "materiality": "material",
            },
        ]
        result["answer_components"] = [component]
        result["source_obligation_candidates"] = [
            {
                "candidate_id": source_obligation_id,
                "obligation_kind": source_obligation_kind,
                "component_candidate_ids": [component["component_id"]],
                "strictness": "required",
            }
        ]
        requirement = dict(result["component_search_requirements"][0])
        requirement["source_obligation_candidate_ids"] = [source_obligation_id]
        requirement_metadata = dict(requirement.get("metadata") or {})
        strategies = [
            dict(item)
            for item in requirement_metadata.get("query_strategy_candidates") or ()
        ]
        for strategy in strategies:
            strategy["source_obligation_candidate_ids"] = [source_obligation_id]
        requirement_metadata["query_strategy_candidates"] = strategies
        requirement["metadata"] = requirement_metadata
        result["component_search_requirements"] = [requirement]
        return result

    monkeypatch.setattr(DeterministicSearchPlannerAdapter, "produce", produce)


def test_n1_plural_semantic_slots_share_one_current_read_and_one_analyst(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One component may carry plural obligations without physical slot fan-out."""

    unrelated_prefix = " ".join(
        [
            "Earlier documentation section with background numeric examples 2024 and 42."
        ]
        * 70
    )
    answer_bearing_section = (
        "math.isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0) "
        "determines whether two values are close."
    )
    long_read_text = (
        f"{unrelated_prefix} {answer_bearing_section} "
        + "Later documentation notes. " * 40
    )
    packet_contexts: list[dict[str, Any]] = []
    admission_payloads: list[dict[str, Any]] = []

    original_packet_install = (
        RunKernel.install_multicomponent_graph_reproof_packet_context
    )

    def capture_packet_install(self: Any, **kwargs: Any) -> Any:
        packet_contexts.append(
            {
                str(key): dict(value)
                for key, value in kwargs[
                    "component_analyst_input_packets"
                ].items()
            }
        )
        return original_packet_install(self, **kwargs)

    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original_component_admission = (
        multicomponent.execute_multicomponent_component_admission
    )

    def capture_component_admission(**kwargs: Any) -> Any:
        admission_payloads.append(
            {
                "semantic_observation": kwargs.get("semantic_observation"),
                "sanitized_content_references": list(
                    kwargs.get("sanitized_content_references") or ()
                ),
            }
        )
        return original_component_admission(**kwargs)

    monkeypatch.setattr(
        RunKernel,
        "install_multicomponent_graph_reproof_packet_context",
        capture_packet_install,
    )
    monkeypatch.setattr(
        multicomponent,
        "execute_multicomponent_component_admission",
        capture_component_admission,
    )

    _install_q1_plural_planner_contract(monkeypatch)
    original_validator = (
        quantitative_evaluator.validate_author_output_quantitative_authority
    )

    def fail_if_product_calls_retired_validator(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-Author quantitative evaluator must not be a PRODUCT gate")

    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        fail_if_product_calls_retired_validator,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query=(
            "According to the official Python 3 documentation, what are the "
            "default values for rel_tol and abs_tol in math.isclose()?"
        ),
        core_topic="Python math.isclose rel_tol abs_tol defaults",
        primary_entity="Python math.isclose",
        researcher_queries=["Python math.isclose rel_tol abs_tol defaults"],
        raw_author_response=(
            "For math.isclose(), the default rel_tol value is 1e-09 and the "
            "default abs_tol value is 0.0. "
            "[[1]](https://docs.python.org/3/library/math.html)"
        ),
        evidence_rows=[
            {
                "title": "math.isclose documentation",
                "url": "https://docs.python.org/3/library/math.html",
                "text": (
                    "math.isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0) "
                    "determines whether two values are close."
                ),
                "credibility": 4,
                "source_tier": "official",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
            }
        ],
        read_content_by_url={
            "https://docs.python.org/3/library/math.html": long_read_text
        },
    )
    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        original_validator,
    )

    contract = harness.run_kernel.state.initial_answer_contract
    components = contract["accepted_answer_component_refs"]
    assert len(components) == 1
    assert len(components[0]["semantic_slot_ids"]) == 2
    assert len(contract["accepted_source_obligation_refs"]) == 1
    assert len(harness.run_kernel.state.searchos_state["active_slot_ids"]) == 1
    assert len(harness.read_transport_calls) == 1
    [semantic_material] = harness.searchos_semantic_material_before_pipeline_consumption
    assert answer_bearing_section in semantic_material["text"]
    bounded_digest = semantic_material["bounded_text_digest"]
    assert bounded_digest == safe_packet_digest(
        {"bounded_text": semantic_material["text"]}
    )
    post_read_call = next(
        item
        for item in reversed(harness.read_assessment_calls)
        if item["bounded_read_digests"]
    )
    assert post_read_call["bounded_read_digests"] == [bounded_digest]
    [bounded_selection] = post_read_call["bounded_read_selections"]
    assert bounded_selection["bounded_text_digest"] == bounded_digest
    [semantic_handoff] = harness.searchos_product_result.semantic_handoffs
    [handoff_custody] = semantic_handoff["read_custody_material_refs"]
    assert handoff_custody["bounded_text_digest"] == bounded_digest
    [analyst_packets] = packet_contexts
    [analyst_packet] = analyst_packets.values()
    assert analyst_packet["component_evidence"][
        "bounded_text_digest"
    ] == bounded_digest
    [admission_payload] = admission_payloads
    [content_ref] = admission_payload["sanitized_content_references"]
    assert content_ref["bounded_text"] == semantic_material["text"]
    assert content_ref["metadata"]["bounded_text_digest"] == bounded_digest
    assert admission_payload["semantic_observation"]["content_refs"] == [
        content_ref["content_ref_id"]
    ]
    assert len(harness.run_kernel.state.semantic_observation_admission_history) == 1
    admissions = harness.run_kernel.state.projections[
        "multicomponent_component_admission"
    ]
    assert admissions["physical_component_analyst_calls"] == 1
    assert admissions["admitted_component_count"] == 1
    graph = harness.run_kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ]
    assert graph["dependency_posture"] == "single_component_direct_admission"
    assert graph["physical_call_accounting"]["component_analyst_calls"] == 1
    assert graph["physical_call_accounting"]["cross_component_analyst_calls"] == 0
    assert graph["physical_call_accounting"]["synthesis_dprime_calls"] == 0
    assert graph["physical_call_accounting"]["scrutineer_calls"] == 0
    assert harness.run_kernel.state.projections.get("multicomponent_graph_scheduler") is None
    searchos = outcome.execution_trace["searchos_slice_a"]
    assert searchos["readiness_projection"]["all_required_slots_slice_a_ready"] is True
    assert searchos["n1_closure_observability"] == {
        "component_count": 1,
        "semantic_slot_count": 2,
        "source_obligation_count": 1,
        "component_analyst_calls": 1,
        "component_analyst_artifact_produced": True,
        "component_admission": True,
        "component_coverage": "supported",
        "bounded_read_selection_count": 1,
        "bounded_read_full_anchor_match_count": 0,
        "bounded_read_partial_anchor_match_count": 1,
        "bounded_read_digest_bound_count": 1,
    }
    assert harness.run_kernel.state.sufficiency_judgment_history[-1][
        "final_answer_allowed"
    ] is True
    packet = outcome.execution_trace["final_answer_packet"]
    manifest = packet["quantitative_finalization_authority_manifest"]
    assert "direct_source_numeric" not in {
        row["authority_kind"] for row in manifest["authorized_numeric_claims"]
    }
    evaluator_diagnostic = (
        quantitative_evaluator.evaluate_author_output_quantitative_authority(
            outcome.report,
            manifest=manifest,
        )
    )
    assert evaluator_diagnostic["status"] == "rejected"
    assert harness.author_prompts and len(harness.author_prompts) == 1
    assert harness.run_kernel.state.author_observation[
        "post_author_quantitative_semantic_gate_active"
    ] is False
    assert outcome.report == (
        "For math.isclose(), the default rel_tol value is 1e-09 and the "
        "default abs_tol value is 0.0. "
        "[[1]](https://docs.python.org/3/library/math.html)"
    )
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] in harness.model_system_prompts
    assert all(
        ROLE_SYSTEM_PROMPTS[role] not in harness.model_system_prompts
        for role in (
            ROLE_CROSS_COMPONENT_ANALYST,
            ROLE_SYNTHESIS_DPRIME,
        )
    )


def test_q1_provider_like_read_derives_official_current_source_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider-like result without fixture source facts still closes Q1."""

    _install_q1_plural_planner_contract(monkeypatch)
    original_validator = (
        quantitative_evaluator.validate_author_output_quantitative_authority
    )

    def fail_if_product_calls_retired_validator(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("post-Author quantitative evaluator must not be a PRODUCT gate")

    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        fail_if_product_calls_retired_validator,
    )
    unrelated_prefix = " ".join(
        [
            "Earlier documentation section with background numeric examples 2024 and 42."
        ]
        * 70
    )
    answer_bearing_section = (
        "math.isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0) "
        "determines whether two values are close."
    )
    long_read_text = (
        f"{unrelated_prefix} {answer_bearing_section} "
        + "Later documentation notes. " * 40
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query=(
            "According to the official Python 3 documentation, what are the "
            "default values for rel_tol and abs_tol in math.isclose()?"
        ),
        core_topic="Python math.isclose rel_tol abs_tol defaults",
        primary_entity="Python math.isclose",
        researcher_queries=["Python math.isclose rel_tol abs_tol defaults"],
        raw_author_response=(
            "For math.isclose(), the default rel_tol value is 1e-09 and the "
            "default abs_tol value is 0.0. "
            "[[1]](https://docs.python.org/3/library/math.html)"
        ),
        inject_default_source_qualification=False,
        evidence_rows=[
            {
                "title": "math.isclose documentation",
                "url": "https://docs.python.org/3/library/math.html",
                "text": answer_bearing_section,
                "credibility": 4,
                "source_tier": "unknown",
            }
        ],
        read_content_by_url={
            "https://docs.python.org/3/library/math.html": long_read_text
        },
    )
    monkeypatch.setattr(
        quantitative_evaluator,
        "validate_author_output_quantitative_authority",
        original_validator,
    )
    searchos = outcome.execution_trace.get("searchos_slice_a") or {}
    ledger = harness.run_kernel.state.evidence_ledger.to_projection().to_dict()
    packet = outcome.execution_trace["final_answer_packet"]
    admissions = harness.run_kernel.state.projections[
        "multicomponent_component_admission"
    ]
    graph = harness.run_kernel.state.projections[
        "multicomponent_component_work_graph_v1"
    ]
    assert admissions["physical_component_analyst_calls"] == 1
    assert admissions["admitted_component_count"] == 1
    assert graph["physical_call_accounting"]["component_analyst_calls"] == 1
    assert graph["physical_call_accounting"]["cross_component_analyst_calls"] == 0
    assert graph["physical_call_accounting"]["scrutineer_calls"] == 0
    assert graph["physical_call_accounting"]["synthesis_dprime_calls"] == 0
    assert searchos["readiness_projection"][
        "all_required_slots_slice_a_ready"
    ] is True
    assert searchos["n1_closure_observability"] == {
        "component_count": 1,
        "semantic_slot_count": 2,
        "source_obligation_count": 1,
        "component_analyst_calls": 1,
        "component_analyst_artifact_produced": True,
        "component_admission": True,
        "component_coverage": "supported",
        "bounded_read_selection_count": 1,
        "bounded_read_full_anchor_match_count": 0,
        "bounded_read_partial_anchor_match_count": 1,
        "bounded_read_digest_bound_count": 1,
    }
    candidate = next(
        item
        for item in ledger["candidate_records"]
        if item["source_class"] == "primary_source_documents"
    )
    assert candidate["source_tier"] == "official"
    assert candidate["eligible_for_stronger_obligation"] is True
    canonical_obligation = next(
        item
        for item in packet["source_obligations"]
        if item["obligation_id"] == "final-answer:run_contract:canonical_docs"
    )
    assert canonical_obligation["status"] == "source_obligation_satisfied"
    assert packet["citation_eligible"]
    assert [item["source_id"] for item in packet["citation_eligible"]] == [1]
    assert packet["citation_ineligible"] == []
    assert packet["semantic_packet_evidence_binding_ref"]["available"] is True
    assert (
        packet["semantic_packet_evidence_binding_ref"][
            "semantic_packet_evidence_binding_count"
        ]
        == 1
    )
    assert harness.run_kernel.state.sufficiency_judgment_history[-1][
        "final_answer_allowed"
    ] is True
    manifest = packet["quantitative_finalization_authority_manifest"]
    assert "direct_source_numeric" not in {
        row["authority_kind"] for row in manifest["authorized_numeric_claims"]
    }
    assert outcome.terminal_status == "completed"
    assert harness.author_prompts and len(harness.author_prompts) == 1
    assert harness.run_kernel.state.author_observation[
        "post_author_quantitative_semantic_gate_active"
    ] is False
    assert outcome.execution_trace["scrutineer_ran"] is False
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] in harness.model_system_prompts
    assert all(
        ROLE_SYSTEM_PROMPTS[role] not in harness.model_system_prompts
        for role in (
            ROLE_CROSS_COMPONENT_ANALYST,
            ROLE_SYNTHESIS_DPRIME,
        )
    )
    assert outcome.report == (
        "For math.isclose(), the default rel_tol value is 1e-09 and the "
        "default abs_tol value is 0.0. "
        "[[1]](https://docs.python.org/3/library/math.html)"
    )


@pytest.mark.parametrize(
    ("source_url", "source_tier", "currentness_signal"),
    [
        (
            "https://example.com/math-isclose-explainer",
            "secondary",
            "current",
        ),
        (
            "https://docs.python.org/3/library/math.html",
            "official",
            "stale",
        ),
    ],
)
def test_q1_nonofficial_or_stale_source_does_not_satisfy_stronger_obligation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_url: str,
    source_tier: str,
    currentness_signal: str,
) -> None:
    """Weak or stale source facts cannot be upgraded by the READ handoff."""

    _install_q1_plural_planner_contract(monkeypatch)
    answer_bearing_section = (
        "math.isclose(a, b, *, rel_tol=1e-09, abs_tol=0.0) "
        "determines whether two values are close."
    )
    long_read_text = " ".join([answer_bearing_section] * 80)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query=(
            "According to the official Python 3 documentation, what are the "
            "default values for rel_tol and abs_tol in math.isclose()?"
        ),
        core_topic="Python math.isclose rel_tol abs_tol defaults",
        primary_entity="Python math.isclose",
        researcher_queries=["Python math.isclose rel_tol abs_tol defaults"],
        raw_author_response=(
            "For math.isclose(), the default rel_tol value is 1e-09 and the "
            "default abs_tol value is 0.0. "
            f"[[1]]({source_url})"
        ),
        inject_default_source_qualification=False,
        evidence_rows=[
            {
                "title": "math.isclose explainer",
                "url": source_url,
                "text": answer_bearing_section,
                "credibility": 4,
                "source_tier": source_tier,
                "currentness_signal": currentness_signal,
            }
        ],
        read_content_by_url={source_url: long_read_text},
    )

    packet = outcome.execution_trace["final_answer_packet"]
    canonical_obligation = next(
        item
        for item in packet["source_obligations"]
        if item["obligation_id"] == "final-answer:run_contract:canonical_docs"
    )
    assert canonical_obligation["status"] != "source_obligation_satisfied"
    assert packet["citation_eligible"] == []
    assert harness.author_prompts == []
    assert outcome.terminal_status == "blocked"


def test_n1_partial_anchor_read_does_not_launder_semantic_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A topical window without both requested defaults stays unsupported."""

    _install_q1_plural_planner_contract(monkeypatch)
    long_read_text = " ".join(
        ["Earlier documentation background with numeric examples 2024 and 42."] * 70
        + [
            (
                "math.isclose is discussed with rel_tol as a configurable tolerance. "
                "The required information is absent from this section."
            )
        ]
        + ["Later documentation background notes."] * 40
    )

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query=(
            "According to the official Python 3 documentation, what are the "
            "default values for rel_tol and abs_tol in math.isclose()?"
        ),
        core_topic="Python math.isclose rel_tol abs_tol defaults",
        primary_entity="Python math.isclose",
        researcher_queries=["Python math.isclose rel_tol abs_tol defaults"],
        evidence_rows=[
            {
                "title": "math.isclose documentation",
                "url": "https://docs.python.org/3/library/math.html",
                "text": "math.isclose reference documentation.",
                "credibility": 4,
                "source_tier": "official",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
            }
        ],
        read_content_by_url={
            "https://docs.python.org/3/library/math.html": long_read_text
        },
    )

    post_read_call = next(
        item
        for item in reversed(harness.read_assessment_calls)
        if item["bounded_read_selections"]
    )
    [selection] = post_read_call["bounded_read_selections"]
    assert selection["matched_anchor_count"] < selection["required_anchor_count"]
    assert selection["missing_anchors"]
    assert selection["not_semantic_support"] is True
    assert selection["not_source_obligation_satisfied"] is True
    n1_observability = outcome.execution_trace["searchos_slice_a"][
        "n1_closure_observability"
    ]
    assert n1_observability["bounded_read_selection_count"] == 1
    assert n1_observability["bounded_read_full_anchor_match_count"] == 0
    assert n1_observability["bounded_read_partial_anchor_match_count"] == 1
    assert n1_observability["bounded_read_digest_bound_count"] == 1
    assert harness.searchos_product_result.semantic_handoffs == ()
    assert harness.run_kernel.state.semantic_observation_admission_history == []
    assert (
        harness.run_kernel.state.projections.get(
            "multicomponent_component_admission"
        )
        is None
    )
    assert ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST] not in (
        harness.model_system_prompts
    )
    assert outcome.execution_trace["blocked_fap_terminal"]["author_called"] is False
    assert (
        harness.run_kernel.state.sufficiency_judgment_history[-1][
            "final_answer_allowed"
        ]
        is False
    )


@pytest.mark.parametrize(
    ("decision", "expected_posture", "expected_failure_class", "expected_subtype"),
    [
        ("MALFORMED", "judgment_failed", "model_output_malformed", "none"),
        ("WRAPPED_JSON", "judgment_failed", "model_output_malformed", "none"),
        (
            "INVALID_NOMINATION",
            "stale_or_invalid",
            "stale_or_invalid",
            "read_nomination_outside_window",
        ),
        (
            "ALTERED_NOMINATION_REF",
            "judgment_failed",
            "model_output_invalid",
            "unsupported_fields",
        ),
    ],
)
def test_bounded_searchos_n1_causal_projection_judgment_failure_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    expected_posture: str,
    expected_failure_class: str,
    expected_subtype: str,
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
    assert slot["canonical_slot_posture"] == expected_posture
    assert slot["safe_failure_class"] == expected_failure_class
    assert slot["safe_transport_exception_class"] == "none"
    assert slot["safe_model_output_invalid_subtype"] == expected_subtype
    assert slot["semantic_handoff_sealed"] is False
    if expected_posture == "stale_or_invalid":
        assert slot["stale_or_invalid_transition_observed"] is True
    assert slot["semantic_handoff_present"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert slot["component_coverage_satisfied"] is False
    assert slot["read_custody_observed"] is False
    serialized = json.dumps(projection, sort_keys=True)
    assert "fictional-" not in serialized
    assert "Traceback" not in serialized
    assert "Exception" not in serialized
    if decision == "ALTERED_NOMINATION_REF":
        assert "f" * 64 not in serialized
        assert "candidate_use_option_ref" not in serialized
        assert "https://alpha.example/report-1" not in serialized


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
    assert slot["component_analyst_case_present"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert slot["component_coverage_satisfied"] is False
    assert projection["component_receiver_selected"] is True
    assert projection["component_receiver_failure_class"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert "component_analyst_failure" not in projection
    assert harness.read_transport_calls


@pytest.mark.parametrize(
    ("failure_mode", "expected_failure_kind"),
    [
        ("output_validation", "output_validation_failure"),
        ("forbidden_runtime_authority", "output_validation_failure"),
        ("model_transport", "model_transport_failure"),
        ("provider_mismatch", "provider_identity_mismatch"),
    ],
)
def test_bounded_searchos_n1_projects_current_component_analyst_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
    expected_failure_kind: str,
) -> None:
    from dataclasses import replace

    from core.multicomponent_graph_scheduling import (
        MULTICOMPONENT_SCHEDULER_STAGE,
        project_current_component_analyst_failure,
    )

    _establish_official_current_qualification_truth(monkeypatch)
    harness_sink: list[Any] = []

    def failing_transport(prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        harness = harness_sink[0]
        base = harness.strict_one_shot_smart_model_transport(
            prompt,
            system_prompt,
            **kwargs,
        )
        if system_prompt != ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            return base
        if failure_mode == "output_validation":
            return replace(base, output_text="not-json")
        if failure_mode == "forbidden_runtime_authority":
            malformed = json.loads(base.output_text)
            malformed["run_id"] = "model-authored"
            return replace(base, output_text=json.dumps(malformed))
        if failure_mode == "model_transport":
            return replace(base, return_code=2, output_text="")
        return replace(base, canonical_provider="OpenRouter")

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        deps_overrides={
            "strict_one_shot_smart_model_transport": failing_transport,
        },
        harness_sink=harness_sink,
    )

    searchos_trace = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos_trace["component_analyst_failure"] == {
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": expected_failure_kind,
        "settlement_posture": "failed_spent",
    }
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=searchos_trace,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
    )
    assert projection is not None
    assert projection["component_analyst_failure"] == {
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": expected_failure_kind,
        "settlement_posture": "failed_spent",
    }
    assert projection["component_receiver_selected"] is True
    assert projection["component_receiver_failure_class"] == (
        "OrdinaryMulticomponentRuntimeError"
    )
    assert outcome.terminal_status == "blocked"
    assert outcome.execution_trace["analyst_skipped"] is True
    assert outcome.execution_trace["scrutineer_ran"] is False
    scheduler = harness.run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    assert scheduler is None
    kernel = harness.run_kernel
    assert project_current_component_analyst_failure(
        state=scheduler,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
        observations=kernel.state.observations,
        kernel_request_id=kernel.state.request_id,
    ) == projection["component_analyst_failure"]
    assert project_current_component_analyst_failure(
        state=scheduler,
        expected_run_id="stale-run",
        expected_request_id=outcome.session_id,
        observations=kernel.state.observations,
        kernel_request_id=kernel.state.request_id,
    ) is None

    wrong_role = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in kernel.state.observations
    ]
    for item in wrong_role:
        if item.get("observation_type") in {
            "multicomponent_component_analyst_completed",
            "multicomponent_component_analyst_resume_completed",
        }:
            item["observation_type"] = "multicomponent_cross_component_analyst_completed"
    assert project_current_component_analyst_failure(
        state=scheduler,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
        observations=wrong_role,
        kernel_request_id=kernel.state.request_id,
    ) is None

    unrelated_work = [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in kernel.state.observations
    ]
    for item in unrelated_work:
        if item.get("status") == "failed":
            item["run_id"] = "unrelated-run"
    assert project_current_component_analyst_failure(
        state=scheduler,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
        observations=unrelated_work,
        kernel_request_id=kernel.state.request_id,
    ) is None


def test_bounded_searchos_n1_rejects_legacy_thin_component_analyst_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dataclasses import replace

    from core.multicomponent_graph_scheduling import (
        MULTICOMPONENT_SCHEDULER_STAGE,
        project_current_component_analyst_failure,
    )

    _establish_official_current_qualification_truth(monkeypatch)
    harness_sink: list[Any] = []

    def thin_analyst_transport(prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        harness = harness_sink[0]
        base = harness.strict_one_shot_smart_model_transport(
            prompt,
            system_prompt,
            **kwargs,
        )
        if system_prompt != ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            return base
        return replace(
            base,
            output_text=json.dumps(
                {
                    "claim_text": "Legacy thin claim.",
                    "support_status": "supported",
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            ),
        )

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        deps_overrides={
            "strict_one_shot_smart_model_transport": thin_analyst_transport,
        },
        harness_sink=harness_sink,
    )

    searchos_trace = dict(outcome.execution_trace["searchos_slice_a"])
    assert searchos_trace["component_analyst_failure"] == {
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "output_validation_failure",
        "settlement_posture": "failed_spent",
    }
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=searchos_trace,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
    )
    assert projection is not None
    assert projection["component_analyst_failure"] == {
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "output_validation_failure",
        "settlement_posture": "failed_spent",
    }
    slot = _required_causal_slot(projection)
    assert slot["component_analyst_case_present"] is False
    assert slot["semantic_admission_status"] != "admitted"
    assert slot["component_coverage_satisfied"] is False
    assert "multicomponent_component_admission" not in (
        harness.run_kernel.state.projections
    )
    assert not any(
        prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
        for prompt in harness.model_system_prompts
    )
    scheduler = harness.run_kernel.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
    assert scheduler is None
    kernel = harness.run_kernel
    assert project_current_component_analyst_failure(
        state=scheduler,
        expected_run_id=outcome.run_id,
        expected_request_id=outcome.session_id,
        observations=kernel.state.observations,
        kernel_request_id=kernel.state.request_id,
    ) == projection["component_analyst_failure"]
    assert kernel.state.projections[
        next(
            stage
            for stage in kernel.state.projections
            if str(stage).startswith("multicomponent_role:component_analyst:")
        )
    ]["role"] == ROLE_COMPONENT_ANALYST


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
        "SuperSecretBearerTokenClass",
        "api_key_sk-live-fixture",
        "https://fixture.invalid/private",
        "fictional-provider-message",
        "fictional-traceback",
    )
    fixture = {
        "slot_postures": {"slot-1": "judgment_failed"},
        "component_receiver_failure": "OrdinaryMulticomponentRuntimeError",
        "component_analyst_failure": {
            "role": ROLE_COMPONENT_ANALYST,
            "failure_kind": sentinels[6],
            "settlement_posture": "failed_spent",
        },
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
                "component_analyst_case_ref": {},
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
                            "action": sentinels[0],
                        }
                    ],
                    "custody_refs": [
                        {
                            "read_custody_material_id": "custody-1",
                            "normalized_url": sentinels[1],
                            "read_content": sentinels[3],
                            "candidate_context": sentinels[2],
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
        "semantic_handoff_authorization_attempted_slot_ids": [sentinels[0]],
        "candidate_context": {"text": sentinels[2], "url": sentinels[1]},
    }
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
    )
    assert projection is not None
    assert projection["component_analyst_failure"] == {
        "role": ROLE_COMPONENT_ANALYST,
        "failure_kind": "other_safe",
        "settlement_posture": "failed_spent",
    }
    serialized = json.dumps(projection, sort_keys=True)
    for sentinel in sentinels:
        assert sentinel not in serialized
    slot = _required_causal_slot(projection)
    assert slot["safe_failure_class"] == "model_transport_failed"
    assert slot["safe_transport_exception_class"] == "other_safe"
    assert slot["safe_model_output_invalid_subtype"] == "none"
    assert slot["read_custody_observed"] is False
    assert slot["last_searchjudgment_action"] == "unknown"
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert "custody_refs" not in slot
    assert "action_history" not in slot
    assert "latest_judgment_reason" not in slot
    assert "semantic_handoff_authorization_attempted_slot_ids" not in serialized
    assert "normalized_url" not in serialized
    assert "private_raw" not in serialized

    assert '"safe_transport_exception_class": "RuntimeError"' not in serialized
    assert '"safe_transport_exception_class": "other_safe"' in serialized


def test_bounded_optional_handoff_projection_fails_closed_without_canonical_readiness() -> None:
    private_sentinel = "fictional-optional-handoff-private-sentinel"
    raw_slot_digest = "fictional-optional-handoff-slot-digest-sentinel"
    handoff_ref = {
        "semantic_handoff_id": "searchos-semantic-handoff:fixture",
        "semantic_handoff_digest": "a" * 64,
    }
    fixture = {
        "slot_postures": {"slot-private": "semantically_handed_off"},
        "semantic_outcomes_by_slot": {
            "slot-private": {
                "semantic_handoff_ref": handoff_ref,
                "component_analyst_case_ref": {},
                "semantic_admission_outcome_ref": {},
                "semantic_admission_status": "not_admitted",
                "searchos_handoff_material_consumed": False,
            }
        },
        "readiness_projection": {
            "required_slot_count": 0,
            "optional_slot_count": 1,
            "all_required_slots_slice_a_ready": True,
            "slot_records": [
                {
                    "slot_ref": {
                        "slot_id": "slot-private",
                        "slot_digest": raw_slot_digest,
                        "component_id": "component-private",
                        "source_obligation_id": "obligation-private",
                    },
                    "requirement_posture": "optional",
                    "support_kind": "reputable_secondary",
                    "latest_judgment_posture": "semantically_handed_off",
                    "latest_judgment_reason": private_sentinel,
                    "judgment_call_count": 1,
                    "action_history": [
                        {"event": "judgment_decided", "reason": private_sentinel}
                    ],
                    "custody_refs": [
                        {
                            "read_custody_material_id": "custody-private",
                            "normalized_url": "https://fixture.invalid/private",
                        }
                    ],
                    "semantic_handoff_ref": handoff_ref,
                    "slice_a_ready": False,
                }
            ],
        },
    }

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
        expected_run_id="run-private",
        expected_request_id="request-private",
    )

    assert projection is not None
    assert projection["projection_status"] == "available"
    assert "searchos_exit" not in projection
    assert projection["active_slot_count"] == 1
    assert projection["required_slot_count"] == 0
    assert projection["all_required_slots_ready"] is True
    assert projection["slots"] == []
    [optional_slot] = projection["optional_slots"]
    assert optional_slot["required"] is False
    assert optional_slot["final_posture"] == "semantically_handed_off"
    assert optional_slot["semantic_handoff_present"] is False
    assert optional_slot["read_custody_observed"] is False
    serialized = json.dumps(projection, sort_keys=True)
    assert private_sentinel not in serialized
    assert raw_slot_digest not in serialized
    assert "https://fixture.invalid/private" not in serialized

    not_ready_fixture = json.loads(json.dumps(fixture))
    not_ready_fixture["readiness_projection"]["slot_records"][0][
        "latest_judgment_posture"
    ] = "ready_for_semantic_evaluation"
    not_ready_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=not_ready_fixture,
        expected_run_id="run-private",
        expected_request_id="request-private",
    )
    assert not_ready_projection is not None
    assert "searchos_exit" not in not_ready_projection

    malformed_fixture = json.loads(json.dumps(fixture))
    malformed_fixture["readiness_projection"]["slot_records"][0][
        "requirement_posture"
    ] = "unknown"
    malformed_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=malformed_fixture,
        expected_run_id="run-private",
        expected_request_id="request-private",
    )
    assert malformed_projection is not None
    assert "searchos_exit" not in malformed_projection


def test_bounded_clarification_projection_requires_closed_zero_evidence() -> None:
    private_candidate = "fictional-clarification-candidate-sentinel"
    fixture = {
        "slot_postures": {
            "slot-required": "clarification_required",
            "slot-optional": "clarification_required",
        },
        "semantic_obligation_clarification_postures": {
            "obligation-required": {
                "clarification_required": True,
                "declared_candidates": [private_candidate],
            },
            "obligation-optional": {
                "clarification_required": True,
                "declared_candidates": [private_candidate],
            },
        },
        "clarification_required": True,
        "clarification_only_no_dispatch": True,
        "clarification_acquisition_job_count": 0,
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "clarification_slot_count": 2,
        "clarification_required_slot_count": 1,
        "clarification_optional_slot_count": 1,
    }

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=fixture,
    )
    assert projection is not None
    assert projection["projection_status"] == "available"
    assert projection["searchos_exit"] == "REQUIRE_CLARIFICATION"
    assert projection["clarification_required_obligation_count"] == 2
    assert projection["clarification_acquisition_job_count"] == 0
    assert projection["provider_calls_attempted"] == 0
    assert projection["provider_calls_completed"] == 0
    assert projection["active_slot_count"] == 2
    assert projection["required_slot_count"] == 1
    assert projection["clarification_optional_slot_count"] == 1
    assert projection["all_required_slots_ready"] is False
    assert projection["slot_summary_variant"] == "clarification_no_acquisition"
    assert len(projection["slots"]) == projection["required_slot_count"]
    [required_slot] = projection["slots"]
    assert required_slot["final_posture"] == "clarification_required"
    assert required_slot["canonical_slot_posture"] == "clarification_required"
    assert required_slot["last_searchjudgment_action"] == "none"
    assert required_slot["semantic_handoff_authorization_attempted"] is False
    assert required_slot["semantic_handoff_sealed"] is False
    assert required_slot["stale_or_invalid_transition_observed"] is False
    assert required_slot["safe_transport_exception_class"] == "none"
    assert required_slot["read_custody_observed"] is False
    assert private_candidate not in json.dumps(projection, sort_keys=True)

    invalid_fixtures = (
        {**fixture, "clarification_acquisition_job_count": 1},
        {**fixture, "provider_calls_attempted": 1},
        {**fixture, "provider_calls_completed": 1},
        {**fixture, "clarification_slot_count": 3},
        {
            **fixture,
            "slot_postures": {},
            "clarification_slot_count": 0,
            "clarification_required_slot_count": 0,
            "clarification_optional_slot_count": 0,
        },
        {
            **fixture,
            "slot_postures": {
                "slot-required": "ready_for_semantic_evaluation",
                "slot-optional": "clarification_required",
            },
        },
        {
            key: value
            for key, value in fixture.items()
            if key != "clarification_acquisition_job_count"
        },
    )
    for invalid in invalid_fixtures:
        unavailable = build_bounded_searchos_n1_causal_projection(
            searchos_slice_a_projection=invalid,
        )
        assert unavailable is not None
        assert unavailable["projection_status"] == "insufficient"

    scalar_postures = {
        **fixture,
        "semantic_obligation_clarification_postures": 1,
    }
    scalar_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=scalar_postures,
    )
    assert scalar_projection is not None
    assert scalar_projection["projection_status"] == "insufficient"




def _transport_cause_fixture(*, reason: str, posture: str = "judgment_failed") -> dict[str, Any]:
    return {
        "slot_postures": {"slot-1": posture},
        "semantic_outcomes_by_slot": {
            "slot-1": {
                "semantic_handoff_ref": {},
                "component_analyst_case_ref": {},
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
                        "slot_digest": "digest-1",
                        "component_id": "component-1",
                        "source_obligation_id": "obligation-1",
                    },
                    "requirement_posture": "required",
                    "support_kind": "canonical_documentation",
                    "latest_judgment_posture": posture,
                    "latest_judgment_reason": reason,
                    "judgment_call_count": 1,
                    "action_history": [{"event": "judgment_failed"}],
                    "custody_refs": [{"read_custody_material_id": "custody-1"}],
                    "semantic_handoff_ref": {},
                    "slice_a_ready": False,
                }
            ],
        },
    }


_TERMINAL_CAUSE_HANDOFF_DIGEST = "cd" * 32
_TERMINAL_CAUSE_HANDOFF_REF = {
    "semantic_handoff_id": (
        "searchos-semantic-handoff:" + _TERMINAL_CAUSE_HANDOFF_DIGEST[:24]
    ),
    "semantic_handoff_digest": _TERMINAL_CAUSE_HANDOFF_DIGEST,
}
_HANDOFF_CURRENT_MATERIAL_ACTION = (
    "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
)
_TERMINAL_CAUSE_PRIVATE_CANARY = (
    "TERMINAL_CAUSE_PRIVATE_CANARY_MUST_NOT_SERIALIZE"
)
_ATTEMPTED_SLOT_IDS_KEY = "semantic_handoff_authorization_attempted_slot_ids"


def _terminal_cause_slice_a_fixture(
    *,
    posture: str,
    action_history: list[dict[str, Any]],
    reason: str = "none",
    attempted_slot_ids: list[str] | None = None,
    compact_handoff: bool = False,
    recorded_handoff: bool = False,
    extra_projection: dict[str, Any] | None = None,
    extra_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fixture = _transport_cause_fixture(reason=reason, posture=posture)
    record = fixture["readiness_projection"]["slot_records"][0]
    record["action_history"] = action_history
    if extra_record:
        record.update(extra_record)
    if compact_handoff:
        record["semantic_handoff_ref"] = dict(_TERMINAL_CAUSE_HANDOFF_REF)
        fixture["semantic_outcomes_by_slot"]["slot-1"]["semantic_handoff_ref"] = dict(
            _TERMINAL_CAUSE_HANDOFF_REF
        )
    if recorded_handoff:
        record["recorded_searchos_semantic_handoff_ref"] = {
            **_TERMINAL_CAUSE_HANDOFF_REF,
            "slot_ref": dict(record["slot_ref"]),
            "schema_version": SEARCHOS_SEMANTIC_HANDOFF_SCHEMA_VERSION,
        }
    if attempted_slot_ids is not None:
        fixture[_ATTEMPTED_SLOT_IDS_KEY] = list(attempted_slot_ids)
    if extra_projection:
        fixture.update(extra_projection)
    return fixture


def _required_terminal_cause(projection: dict[str, Any]) -> dict[str, Any]:
    slot = _required_causal_slot(projection)
    serialized = json.dumps(projection, sort_keys=True)
    assert _ATTEMPTED_SLOT_IDS_KEY not in serialized
    assert "action_history" not in slot
    assert "latest_judgment_reason" not in slot
    assert "custody_refs" not in slot
    return slot


@pytest.mark.parametrize(
    ("reason", "expected_failure_class", "expected_transport_class", "forbidden_tokens"),
    [
        (
            "model_transport_failed:APITimeoutError",
            "model_transport_failed",
            "APITimeoutError",
            (),
        ),
        (
            "model_transport_failed:APIConnectionError",
            "model_transport_failed",
            "APIConnectionError",
            (),
        ),
        (
            "model_transport_failed:RateLimitError",
            "model_transport_failed",
            "RateLimitError",
            (),
        ),
        (
            "model_output_malformed",
            "model_output_malformed",
            "none",
            (),
        ),
        (
            "model_transport_failed:FictionalUnknownTransportError",
            "model_transport_failed",
            "other_safe",
            ("FictionalUnknownTransportError",),
        ),
        (
            "model_transport_failed:SuperSecretBearerTokenClass:api_key_sk-live-fixture",
            "model_transport_failed",
            "other_safe",
            (
                "SuperSecretBearerTokenClass",
                "api_key_sk-live-fixture",
                "https://fixture.invalid/private",
                "fictional-provider-message",
                "fictional-traceback",
            ),
        ),
    ],
)
def test_bounded_searchos_n1_causal_projection_transport_exception_class(
    reason: str,
    expected_failure_class: str,
    expected_transport_class: str,
    forbidden_tokens: tuple[str, ...],
) -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_transport_cause_fixture(reason=reason),
    )
    assert projection is not None
    assert projection["schema_version"] == "bounded_searchos_n1_causal_projection_v1"
    slot = _required_causal_slot(projection)
    assert slot["safe_failure_class"] == expected_failure_class
    assert slot["safe_transport_exception_class"] == expected_transport_class
    assert slot["safe_model_output_invalid_subtype"] == "none"
    serialized = json.dumps(projection, sort_keys=True)
    assert "latest_judgment_reason" not in serialized
    for token in forbidden_tokens:
        assert token not in serialized


@pytest.mark.parametrize(
    (
        "reason",
        "posture",
        "expected_failure_class",
        "expected_transport_class",
        "expected_subtype",
        "forbidden_tokens",
    ),
    [
        (
            # Case A — exact post-READ assessment omission
            (
                "model_output_invalid:"
                "post-read_action_requires_exact_read_insufficient_assessments"
            ),
            "judgment_failed",
            "model_output_invalid",
            "none",
            "post_read_assessment_incomplete",
            (
                "post-read_action_requires_exact_read_insufficient_assessments",
                "post-READ action requires exact read_insufficient assessments",
            ),
        ),
        (
            # Case B — semantic handoff payload invalid
            "model_output_invalid:semantic_handoff_requires_exact_read_custody_refs",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "semantic_handoff_payload_invalid",
            ("semantic_handoff_requires_exact_read_custody_refs",),
        ),
        (
            # Case C — semantic handoff custody ref stale/altered
            (
                "model_output_invalid:"
                "semantic_handoff_nominated_stale_or_altered_read_custody"
            ),
            "judgment_failed",
            "model_output_invalid",
            "none",
            "semantic_handoff_ref_invalid",
            ("semantic_handoff_nominated_stale_or_altered_read_custody",),
        ),
        (
            # Case D — unsupported fields
            "model_output_invalid:judgment_output_contains_unsupported_fields",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "unsupported_fields",
            ("judgment_output_contains_unsupported_fields",),
        ),
        (
            # Case D2 — model-authored request identity
            "model_output_invalid:judgment_output_must_not_author_request_identity",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "request_identity_authored",
            ("judgment_output_must_not_author_request_identity",),
        ),
        (
            # Case E — non-model-output transport failure
            "model_transport_failed:APITimeoutError",
            "judgment_failed",
            "model_transport_failed",
            "APITimeoutError",
            "none",
            (),
        ),
        (
            # Case F — successful / handed-off posture
            "",
            "semantically_handed_off",
            "none",
            "none",
            "none",
            (),
        ),
        (
            # Case G — unknown future validation reason
            "model_output_invalid:some_unknown_future_rule",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "other_safe",
            ("some_unknown_future_rule",),
        ),
        (
            # Case H — private-looking suffix
            "model_output_invalid:secret_private_sentinel_value",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "other_safe",
            ("secret_private_sentinel_value",),
        ),
        (
            # Case I — malformed / empty reason under failed posture
            "",
            "judgment_failed",
            "other_safe",
            "none",
            "none",
            (),
        ),
        (
            # Case I — nonmatching reason under failed posture
            "not_a_recognized_failure_shape",
            "judgment_failed",
            "other_safe",
            "none",
            "none",
            ("not_a_recognized_failure_shape",),
        ),
        (
            # Case I — model_output_invalid with empty suffix
            "model_output_invalid:",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "other_safe",
            (),
        ),
        (
            # Case F — active unjudged posture
            "",
            "active_unjudged",
            "none",
            "none",
            "none",
            (),
        ),
        (
            # Stale posture — request identity mismatch remains visible
            "model_output_invalid:judgment_nomination_is_stale",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "request_identity_mismatch",
            ("judgment_nomination_is_stale",),
        ),
        (
            # Stale posture — slot identity mismatch remains visible
            "model_output_invalid:judgment_nomination_slot_is_stale",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "slot_identity_mismatch",
            ("judgment_nomination_slot_is_stale",),
        ),
        (
            # Stale posture — read nomination outside window remains visible
            (
                "model_output_invalid:"
                "read_nomination_is_outside_current_candidate_window"
            ),
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "read_nomination_outside_window",
            ("read_nomination_is_outside_current_candidate_window",),
        ),
        (
            # Stale posture — read nomination ref invalid remains visible
            "model_output_invalid:read_nomination_ref_is_stale_or_altered",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "read_nomination_ref_invalid",
            ("read_nomination_ref_is_stale_or_altered",),
        ),
        (
            # Stale posture — installed navigation stale-ref subtype remains allowlisted
            "model_output_invalid:navigation_nomination_ref_is_stale_or_altered",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "navigation_nomination_invalid",
            ("navigation_nomination_ref_is_stale_or_altered",),
        ),
        (
            # Authorized compact-ID collision remains visible and fail-closed
            "model_output_invalid:authorized_compact_identity_is_not_unique",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "authorized_identity_not_unique",
            ("authorized_compact_identity_is_not_unique",),
        ),
        (
            # Empty authorized compact identity remains visible and fail-closed
            "model_output_invalid:authorized_read_option_identity_is_empty",
            "judgment_failed",
            "model_output_invalid",
            "none",
            "authorized_identity_empty",
            ("authorized_read_option_identity_is_empty",),
        ),
        (
            # Stale posture — unknown model_output_invalid suffix collapses
            "model_output_invalid:some_unknown_stale_future_rule",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "other_safe",
            ("some_unknown_stale_future_rule",),
        ),
        (
            # Stale posture — non-model-output stale reason keeps subtype none
            "stale_lineage_runtime_failure",
            "stale_or_invalid",
            "stale_or_invalid",
            "none",
            "none",
            ("stale_lineage_runtime_failure",),
        ),
    ],
)
def test_bounded_searchos_n1_causal_projection_model_output_invalid_subtype(
    reason: str,
    posture: str,
    expected_failure_class: str,
    expected_transport_class: str,
    expected_subtype: str,
    forbidden_tokens: tuple[str, ...],
) -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_transport_cause_fixture(
            reason=reason,
            posture=posture,
        ),
    )
    assert projection is not None
    assert projection["schema_version"] == "bounded_searchos_n1_causal_projection_v1"
    slot = _required_causal_slot(projection)
    # Broad class preserved; subtype refines model_output_invalid reasons,
    # including when lifecycle posture collapses the class to stale_or_invalid.
    assert slot["safe_failure_class"] == expected_failure_class
    assert slot["safe_transport_exception_class"] == expected_transport_class
    assert slot["safe_model_output_invalid_subtype"] == expected_subtype
    if expected_failure_class == "model_output_invalid":
        assert expected_subtype != "none"
    if expected_subtype not in {"none", "other_safe"}:
        assert reason.casefold().startswith("model_output_invalid:")
    serialized = json.dumps(projection, sort_keys=True)
    assert "latest_judgment_reason" not in serialized
    for token in forbidden_tokens:
        assert token not in serialized


def test_bounded_searchos_n1_causal_projection_transport_field_parity(
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
    assert slot["safe_failure_class"] == "none"
    assert slot["safe_transport_exception_class"] == "none"
    assert slot["safe_model_output_invalid_subtype"] == "none"
    assert slot["semantic_handoff_present"] is True
    assert slot["handoff_material_consumed"] is True
    assert slot["component_analyst_case_present"] is True
    assert slot["semantic_admission_status"] == "admitted"
    assert slot["component_coverage_satisfied"] is True
    assert set(slot) >= {
        "safe_failure_class",
        "safe_transport_exception_class",
        "safe_model_output_invalid_subtype",
        "read_custody_observed",
        "semantic_handoff_present",
        "handoff_material_consumed",
        "component_analyst_case_present",
        "semantic_admission_status",
        "component_coverage_satisfied",
        "canonical_slot_posture",
        "last_searchjudgment_action",
        "semantic_handoff_authorization_attempted",
        "semantic_handoff_sealed",
        "stale_or_invalid_transition_observed",
    }


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


def test_bounded_searchos_n1_causal_projection_no_handoff_action() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="awaiting_read",
            action_history=[
                {
                    "action": "REQUEST_READ_PAGE",
                    "reason": _TERMINAL_CAUSE_PRIVATE_CANARY,
                }
            ],
            extra_record={
                "custody_refs": [
                    {
                        "read_content": _TERMINAL_CAUSE_PRIVATE_CANARY,
                        "candidate_context": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    }
                ]
            },
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == "awaiting_read"
    assert slot["final_posture"] == "awaiting_read"
    assert slot["last_searchjudgment_action"] == "REQUEST_READ_PAGE"
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert slot["stale_or_invalid_transition_observed"] is False
    assert _TERMINAL_CAUSE_PRIVATE_CANARY not in json.dumps(projection, sort_keys=True)


def test_bounded_searchos_n1_causal_projection_handoff_selected_and_sealed() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="semantically_handed_off",
            action_history=[
                {"action": "REQUEST_READ_PAGE"},
                {"action": _HANDOFF_CURRENT_MATERIAL_ACTION},
            ],
            attempted_slot_ids=["slot-1"],
            compact_handoff=True,
            recorded_handoff=True,
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == "semantically_handed_off"
    assert slot["final_posture"] == "semantically_handed_off"
    assert slot["last_searchjudgment_action"] == _HANDOFF_CURRENT_MATERIAL_ACTION
    assert slot["semantic_handoff_authorization_attempted"] is True
    assert slot["semantic_handoff_sealed"] is True
    assert slot["stale_or_invalid_transition_observed"] is False
    assert slot["semantic_handoff_present"] is True


def test_bounded_searchos_n1_causal_projection_handoff_selected_authorization_not_reached() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="ready_for_semantic_evaluation",
            action_history=[{"action": _HANDOFF_CURRENT_MATERIAL_ACTION}],
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["last_searchjudgment_action"] == _HANDOFF_CURRENT_MATERIAL_ACTION
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert slot["stale_or_invalid_transition_observed"] is False
    assert slot["semantic_handoff_present"] is False


def test_bounded_searchos_n1_causal_projection_handoff_authorization_attempted_not_sealed() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="ready_for_semantic_evaluation",
            action_history=[{"action": _HANDOFF_CURRENT_MATERIAL_ACTION}],
            attempted_slot_ids=["slot-1"],
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["last_searchjudgment_action"] == _HANDOFF_CURRENT_MATERIAL_ACTION
    assert slot["semantic_handoff_authorization_attempted"] is True
    assert slot["semantic_handoff_sealed"] is False
    assert slot["semantic_handoff_present"] is False
    assert slot["stale_or_invalid_transition_observed"] is False


def test_bounded_searchos_n1_causal_projection_true_stale_or_invalid() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="stale_or_invalid",
            action_history=[
                {"action": "REQUEST_READ_PAGE"},
                {"event": "stale_or_invalid"},
            ],
            reason="candidate_packet_stale:fixture",
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == "stale_or_invalid"
    assert slot["final_posture"] == "stale_or_invalid"
    assert slot["last_searchjudgment_action"] == "REQUEST_READ_PAGE"
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert slot["stale_or_invalid_transition_observed"] is True
    assert slot["semantic_handoff_present"] is False
    assert slot["safe_failure_class"] == "stale_or_invalid"


def test_bounded_searchos_n1_causal_projection_followup_acquisition_failure_stays_unjudged() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="active_unjudged",
            action_history=[
                {"action": "PROPOSE_FOLLOWUP_QUERY"},
                {
                    "event": "followup_acquisition_failed",
                    "auto_handoff": False,
                    "support_admitted": False,
                },
            ],
            reason="followup_discover_failed:provider_route_blocked",
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == "active_unjudged"
    assert slot["final_posture"] == "active_unjudged"
    assert slot["last_searchjudgment_action"] == "PROPOSE_FOLLOWUP_QUERY"
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert slot["stale_or_invalid_transition_observed"] is False
    assert slot["semantic_handoff_present"] is False
    assert slot["safe_failure_class"] == "none"


def test_bounded_searchos_n1_causal_projection_handoff_sealed_then_invalidated() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="stale_or_invalid",
            action_history=[
                {"action": _HANDOFF_CURRENT_MATERIAL_ACTION},
                {"event": "stale_or_invalid"},
            ],
            attempted_slot_ids=["slot-1"],
            compact_handoff=True,
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == "stale_or_invalid"
    assert slot["final_posture"] == "stale_or_invalid"
    assert slot["last_searchjudgment_action"] == _HANDOFF_CURRENT_MATERIAL_ACTION
    assert slot["semantic_handoff_authorization_attempted"] is True
    assert slot["semantic_handoff_sealed"] is True
    assert slot["stale_or_invalid_transition_observed"] is True
    assert slot["semantic_handoff_present"] is False


@pytest.mark.parametrize(
    "canonical_posture",
    ("clarification_required", "awaiting_interpretation_binding"),
)
def test_bounded_searchos_n1_causal_projection_pre_collapse_alias(
    canonical_posture: str,
) -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture=canonical_posture,
            action_history=[
                {
                    "action": (
                        "REQUIRE_CLARIFICATION"
                        if canonical_posture == "clarification_required"
                        else "PROPOSE_INTERPRETATION_BINDING"
                    )
                }
            ],
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    assert slot["canonical_slot_posture"] == canonical_posture
    assert slot["final_posture"] == "stale_or_invalid"
    assert slot["stale_or_invalid_transition_observed"] is False
    assert slot["semantic_handoff_sealed"] is False
    assert slot["semantic_handoff_authorization_attempted"] is False


def test_bounded_searchos_n1_causal_projection_terminal_cause_privacy_canary() -> None:
    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=_terminal_cause_slice_a_fixture(
            posture="judgment_failed",
            reason=_TERMINAL_CAUSE_PRIVATE_CANARY,
            action_history=[
                {
                    "action": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    "reason": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    "event": "judgment_failed",
                }
            ],
            attempted_slot_ids=[_TERMINAL_CAUSE_PRIVATE_CANARY],
            extra_record={
                "latest_judgment_reason": _TERMINAL_CAUSE_PRIVATE_CANARY,
                "custody_refs": [
                    {
                        "read_content": _TERMINAL_CAUSE_PRIVATE_CANARY,
                        "normalized_url": "https://fixture.invalid/private-canary",
                        "candidate_context": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    }
                ],
            },
            extra_projection={
                "private_raw": {
                    "query": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    "prompt": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    "provider_payload": _TERMINAL_CAUSE_PRIVATE_CANARY,
                    "model_response": _TERMINAL_CAUSE_PRIVATE_CANARY,
                },
                "candidate_context": {"text": _TERMINAL_CAUSE_PRIVATE_CANARY},
            },
        ),
    )
    assert projection is not None
    slot = _required_terminal_cause(projection)
    serialized = json.dumps(projection, sort_keys=True)
    assert _TERMINAL_CAUSE_PRIVATE_CANARY not in serialized
    assert "https://fixture.invalid/private-canary" not in serialized
    assert slot["last_searchjudgment_action"] == "unknown"
    assert slot["semantic_handoff_authorization_attempted"] is False
    assert slot["semantic_handoff_sealed"] is False


def test_bounded_searchos_n1_causal_projection_cli_aglive_canonical_parity() -> None:
    fixture = _terminal_cause_slice_a_fixture(
        posture="semantically_handed_off",
        action_history=[{"action": _HANDOFF_CURRENT_MATERIAL_ACTION}],
        attempted_slot_ids=["slot-1"],
        compact_handoff=True,
        recorded_handoff=True,
    )
    kwargs = {
        "searchos_slice_a_projection": fixture,
        "enabled": True,
        "expected_run_id": "run-parity",
        "expected_request_id": "request-parity",
    }
    direct = build_bounded_searchos_n1_causal_projection(**kwargs)
    cli = compatibility_cli.build_bounded_searchos_n1_causal_projection(**kwargs)
    assert compatibility_cli.build_bounded_searchos_n1_causal_projection is (
        build_bounded_searchos_n1_causal_projection
    )
    assert direct is not None
    assert cli == direct
    slot = _required_terminal_cause(direct)
    assert slot["last_searchjudgment_action"] == _HANDOFF_CURRENT_MATERIAL_ACTION
    assert slot["semantic_handoff_sealed"] is True
    assert slot["semantic_handoff_authorization_attempted"] is True
