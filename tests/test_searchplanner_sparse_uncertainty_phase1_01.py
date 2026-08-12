"""Offline product-path proof for sparse uncertainty-aware SearchPlanner Phase 1."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
    accept_planner_model_output,
    validate_and_sanitize_model_output,
)
from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
    build_search_planner_model_prompt,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_semantic_compiler import (
    SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA,
    SearchPlannerSemanticProposalError,
    compile_semantic_planner_proposal,
    count_model_authored_mechanical_identity_keys,
    validate_semantic_planner_proposal,
)
from tests.fixtures.search_planner_sparse_semantic_corpus import (
    INVALID_SPARSE_PLANNER_CASES,
    VALID_SPARSE_PLANNER_CASES,
    valid_case,
)

RUN_ID = "run:sparse-phase-1"
REQUEST_ID = "request:sparse-phase-1"
PROMPT_MARKER = "Sanitized planner input JSON:\n"


class _FakeAskModel:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append((args, kwargs))
        return json.dumps(self.response)


def _accept(case: dict[str, Any]) -> dict[str, Any]:
    return accept_planner_model_output(
        deepcopy(case["proposal"]),
        user_query_text=str(case["query"]),
        requested_mode=str(case["mode"]),
    )


def _all_recon_requirements(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        strategy["recon_requirement"]
        for requirement in proposal["component_search_requirements"]
        for strategy in requirement["metadata"]["query_strategy_candidates"]
    ]


def _run_to_initial_answer_contract(
    case: dict[str, Any],
) -> tuple[RunKernel, _FakeAskModel]:
    fake = _FakeAskModel(case["proposal"])
    adapter = SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="offline-test-provider",
        model="offline-test-model",
        effort="low",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )
    case_id = str(case["case_id"])
    run_id = f"{RUN_ID}:{case_id}"
    request_id = f"{REQUEST_ID}:{case_id}"
    kernel = RunKernel.start(run_id=run_id, request_id=request_id)
    planner_input = SearchPlannerInput(
        run_id=run_id,
        request_id=request_id,
        user_query_text=str(case["query"]),
        requested_mode=str(case["mode"]),
        safe_context={"current_date": "2026-08-11"},
    )
    planner_action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=planner_action,
        planner_input=planner_input,
        adapter=adapter,
    )
    kernel.reduce(
        Observation.from_action(
            planner_action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )
    qmr = kernel.state.search_planner_proposal_state["question_meaning_record"]
    acceptance_action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=qmr["record_id"],
        parent_proposal_digest=qmr["record_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            acceptance_action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": qmr},
        )
    )
    return kernel, fake


def test_prompt_uses_one_shared_sparse_contract_and_clears_budget_gate() -> None:
    planner_input = {
        "run_id": "must-not-be-model-visible",
        "request_id": "must-not-be-model-visible",
        "requested_mode": "Balanced",
        "user_query_text_for_planning": "official Python math.isclose default values",
        "safe_context": {
            "current_date": "2026-08-11",
            "include_domains": [],
            "exclude_domains": [],
        },
        "route_context_ref": {"must": "not appear"},
        "parent_contract_refs": {"must": "not appear"},
    }

    prompt = build_search_planner_model_prompt(planner_input)
    packet = json.loads(prompt.split(PROMPT_MARKER, 1)[1])

    assert packet["output_schema"] == SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA
    assert set(packet["planner_input"]) == {
        "requested_mode",
        "user_query_text_for_planning",
        "safe_context",
    }
    assert "answer_components" not in prompt
    assert "component_search_requirements" not in prompt
    assert "run_id" not in prompt
    assert "request_id" not in prompt
    assert "recon_requirement" not in prompt
    assert "primary_query" not in prompt
    assert len(SEARCH_PLANNER_MODEL_SYSTEM_PROMPT) + len(prompt) == 2509
    assert 1 - (2509 / 15705) >= 0.84


@pytest.mark.parametrize(
    "case",
    VALID_SPARSE_PLANNER_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_valid_sparse_corpus_compiles_deterministically(case: dict[str, Any]) -> None:
    assert count_model_authored_mechanical_identity_keys(case["proposal"]) == 0
    first = _accept(case)
    second = _accept(case)

    assert first == second
    assert validate_and_sanitize_model_output(first) == first
    assert 1 <= len(first["answer_components"]) <= 5
    assert all(
        requirement
        == {
            "posture": "not_needed",
            "unresolved_dimension_ids": [],
            "candidate_queries": [],
            "required_for_truthful_targeting": False,
        }
        for requirement in _all_recon_requirements(first)
    )
    serialized = json.dumps(first, sort_keys=True)
    assert '"provider"' not in serialized
    assert '"model"' not in serialized

    kernel, fake = _run_to_initial_answer_contract(case)
    assert len(fake.calls) == 1
    accepted = kernel.state.initial_answer_contract
    assert accepted["accepted_answer_component_count"] == len(first["answer_components"])
    assert [item["component_id"] for item in accepted["accepted_answer_component_refs"]] == [
        item["component_id"] for item in first["answer_components"]
    ]
    for compiled_component, accepted_component in zip(
        first["answer_components"],
        accepted["accepted_answer_component_refs"],
        strict=True,
    ):
        for field in (
            "allowed_support_kinds",
            "dependency_component_ids",
            "mandatory_caveats",
            "prohibited_upgrades",
        ):
            assert accepted_component.get(field, []) == compiled_component.get(field, [])
        for field in (
            "max_inference_depth",
            "normalization_policy",
            "calculation_policy",
        ):
            assert accepted_component.get(field) == compiled_component.get(field)
    accepted_slots = {item["slot_id"]: item for item in accepted["accepted_semantic_slot_refs"]}
    for slot in first["semantic_slots"]:
        preserved = accepted_slots[slot["slot_id"]]
        assert preserved["status"] == slot["status"]
        assert preserved["candidate_values"] == slot.get("candidate_values", [])
        assert preserved.get("selected_value") == slot.get("selected_value")
        assert preserved["user_confirmation_required"] is bool(slot.get("user_confirmation_required", False))


@pytest.mark.parametrize(
    "case",
    INVALID_SPARSE_PLANNER_CASES,
    ids=lambda case: str(case["case_id"]),
)
def test_invalid_sparse_corpus_fails_closed_without_rich_fallback(
    case: dict[str, Any],
) -> None:
    with pytest.raises(SearchPlannerSemanticProposalError):
        validate_semantic_planner_proposal(deepcopy(case["proposal"]))
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(
            deepcopy(case["proposal"]),
            user_query_text="bounded offline query",
            requested_mode="Balanced",
        )
    assert caught.value.failure_code is (SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL)


def test_direct_simple_and_mode_defaults_are_deterministic() -> None:
    official = _accept(valid_case("official_source_direct_simple"))
    fresh = _accept(valid_case("freshness_direct_simple"))
    base = valid_case("supporting_premise_and_inferred_target")

    assert official["source_obligation_candidates"][0]["obligation_kind"] == ("canonical_documentation")
    assert fresh["component_search_requirements"][0]["recency_requirement"] == ("current as of 2026-08-11")
    for mode, expected_depth in (("Fast", 1), ("Balanced", 1), ("Deep", 2)):
        case = deepcopy(base)
        case["mode"] = mode
        target = _accept(case)["answer_components"][1]
        assert target["max_inference_depth"] == expected_depth


def test_local_keys_are_only_proposal_local_and_compile_to_owned_identity() -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {"key": "stable-component-id", "need": "Establish the signed premise"},
            {"key": "component:01", "need": "Verify the governing rule"},
            {
                "key": "run-123-component-2",
                "need": "Infer the filing route",
                "support": "inferred",
                "depends_on": ["stable-component-id", "component:01"],
            },
        ],
    }
    compiled = compile_semantic_planner_proposal(
        proposal,
        user_query_text="Determine the filing route from the premises.",
        requested_mode="Deep",
    )

    assert [item["component_id"] for item in compiled["answer_components"]] == [
        "component:01",
        "component:02",
        "component:03",
    ]
    assert compiled["answer_components"][1]["component_id"] == "component:02"
    assert compiled["answer_components"][2]["dependency_component_ids"] == [
        "component:01",
        "component:02",
    ]
    serialized = json.dumps(compiled, sort_keys=True)
    assert "stable-component-id" not in serialized
    assert "run-123-component-2" not in serialized
    assert all("key" not in component for component in compiled["answer_components"])


def test_factual_uncertainty_survives_initial_answer_contract_acceptance() -> None:
    case = valid_case("factual_identity_uncertainty")
    kernel, fake = _run_to_initial_answer_contract(case)

    assert len(fake.calls) == 1
    assert kernel.state.search_planner_proposal_state["material_ambiguity_posture"] == "factual_uncertainty_declared"
    accepted_slot = kernel.state.initial_answer_contract_projection["accepted_semantic_slot_refs"][0]
    assert accepted_slot["status"] == "unresolved"
    assert accepted_slot["candidate_values"] == [
        "Scott Galloway",
        "George Galloway",
    ]
    assert accepted_slot["selected_value"] is None
    assert accepted_slot["user_confirmation_required"] is False
    assert kernel.state.initial_answer_contract_projection["material_ambiguity_preserved"] is True
    trace = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert '"scout_runtime_activated": true' not in trace
    assert '"query_plan_activated": true' not in trace
    assert '"search_work_plan_activated": true' not in trace


def test_true_user_intent_ambiguity_preserves_confirmation_requirement() -> None:
    compiled = _accept(valid_case("true_user_intent_ambiguity"))
    slot = compiled["semantic_slots"][0]

    assert compiled["material_ambiguity_posture"] == "user_confirmation_required"
    assert slot["candidate_values"] == ["planet", "element", "automobile brand"]
    assert slot["user_confirmation_required"] is True
    assert _all_recon_requirements(compiled)[0]["posture"] == "not_needed"
