"""Offline product-path proof for sparse uncertainty-aware SearchPlanner Phase 1."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.searchos_iterative_judgment_runtime as searchos_runtime
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
    SEARCH_PLANNER_MODEL_VISIBLE_SCHEMA,
    SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA,
    SearchPlannerBranchFieldSetDetail,
    SearchPlannerSemanticProposalError,
    SearchPlannerSemanticProposalSubtype,
    compile_semantic_planner_proposal,
    count_model_authored_mechanical_identity_keys,
    validate_semantic_planner_proposal,
)
from core.searchos_iterative_judgment_runtime import (
    SearchOSRuntimeError,
    build_searchos_effective_semantic_slot_view,
    record_searchos_interpretation_binding,
    validate_searchos_interpretation_binding,
)
from tests.fixtures.search_planner_sparse_semantic_corpus import (
    INVALID_SPARSE_PLANNER_CASES,
    VALID_SPARSE_PLANNER_CASES,
    valid_case,
)
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)

RUN_ID = "run:sparse-phase-1"
REQUEST_ID = "request:sparse-phase-1"
PROMPT_MARKER = "Sanitized planner input JSON:\n"
_CLEAR_DIRECT_HISTORICAL_BASELINE_CHARS = 15705
_PHASE1_PROMPT_SCENARIOS = (
    (
        "clear_direct",
        "official Python math.isclose default values",
        15705,
        2509,
    ),
    (
        "clear_multi",
        "Using the fictional Northstar certificate and registry records, report both current facts.",
        15827,
        2576,
    ),
    (
        "factual_uncertainty",
        "recent Galloway controversy",
        15677,
        2493,
    ),
    (
        "true_ambiguity",
        "Tell me about Mercury",
        15613,
        2487,
    ),
)


def _prompt_planner_input(query: str) -> dict[str, Any]:
    return {
        "run_id": "must-not-be-model-visible",
        "request_id": "must-not-be-model-visible",
        "requested_mode": "Balanced",
        "user_query_text_for_planning": query,
        "safe_context": {
            "current_date": "2026-08-11",
            "include_domains": [],
            "exclude_domains": [],
        },
        "route_context_ref": {"must": "not appear"},
        "parent_contract_refs": {"must": "not appear"},
    }


def _prompt_request_chars(query: str) -> int:
    prompt = build_search_planner_model_prompt(_prompt_planner_input(query))
    return len(SEARCH_PLANNER_MODEL_SYSTEM_PROMPT) + len(prompt)


class _FakeAskModel:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append((args, kwargs))
        return json.dumps(self.response)


class _SparseProposalAdapter:
    """Inject one accepted sparse proposal through the ordinary product seam."""

    def __init__(self, proposal: Mapping[str, Any]) -> None:
        self.proposal = deepcopy(dict(proposal))

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return accept_planner_model_output(
            deepcopy(self.proposal),
            user_query_text=str(
                planner_input["user_query_text_for_planning"]
            ),
            requested_mode=str(planner_input["requested_mode"]),
        )


def _product_deps(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "search_planner_adapter": _SparseProposalAdapter(proposal),
        "provider_availability": {
            "tavily": True,
            "serper": True,
        },
    }


def _ordered_query_plan_items(outcome: Any) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in outcome.execution_trace["query_plan"]["items"]
        if item["status"] == "ordered"
    ]


def _evidence_row(name: str, *, suffix: str) -> dict[str, Any]:
    return {
        "title": f"{name} bounded offline source",
        "url": f"https://alpha.example/{suffix}",
        "text": f"Bounded directional material about {name}.",
        "source_tier": "official",
        "source_class": "primary_source_documents",
        "currentness_signal": "current",
        "readable_status": "readable",
        "disposition": "accepted",
    }


def _reenvelope_binding(
    binding: Mapping[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    core = {
        key: deepcopy(value)
        for key, value in binding.items()
        if key
        not in {
            "interpretation_binding_id",
            "interpretation_binding_digest",
            "replay_identity",
        }
    }
    core.update(deepcopy(updates))
    digest = searchos_runtime._digest(core)
    return {
        **core,
        "interpretation_binding_id": (
            f"searchos-interpretation-binding:{digest[:24]}"
        ),
        "interpretation_binding_digest": digest,
        "replay_identity": f"searchos-interpretation-binding:{digest}",
    }


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
        if "recon_requirement" in strategy
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


def test_prompt_uses_compact_sparse_contract_and_phase1_budget_gate() -> None:
    planner_input = _prompt_planner_input(
        "official Python math.isclose default values"
    )
    prompt = build_search_planner_model_prompt(planner_input)
    packet = json.loads(prompt.split(PROMPT_MARKER, 1)[1])
    schema = packet["output_schema"]

    assert schema == SEARCH_PLANNER_MODEL_VISIBLE_SCHEMA
    assert schema != SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA
    assert "empty_vs_omitted" not in json.dumps(schema, sort_keys=True)
    assert schema["direct_simple"] == [
        "disposition",
        "source",
        "freshness",
        "caveat",
    ]
    assert schema["components"] == ["disposition", "components"]
    assert schema["limits"]["components"] == [1, 5]
    assert "1-5 objects" in prompt
    assert schema["component"]["required"] == ["need"]
    assert set(packet["planner_input"]) == {
        "requested_mode",
        "user_query_text_for_planning",
        "safe_context",
    }
    assert "never fallback" in prompt
    assert "no depends_on" in prompt
    assert "needs depends_on" in prompt
    assert "no source/freshness" in prompt
    assert "no selected" in prompt
    assert "selected in candidates" in prompt
    assert "confirm=true only if material unresolved|ambiguous" in prompt
    assert "omit empty optionals" in prompt
    assert "answer_components" not in prompt
    assert "component_search_requirements" not in prompt
    assert "run_id" not in prompt
    assert "request_id" not in prompt
    assert "recon_requirement" not in prompt
    assert "primary_query" not in prompt
    prompt_chars = _prompt_request_chars(
        "official Python math.isclose default values"
    )
    assert prompt_chars < _CLEAR_DIRECT_HISTORICAL_BASELINE_CHARS
    assert 1 - (prompt_chars / _CLEAR_DIRECT_HISTORICAL_BASELINE_CHARS) >= 0.84


def test_compact_model_visible_schema_is_derived_from_validator_constants() -> None:
    exhaustive = SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA
    visible = SEARCH_PLANNER_MODEL_VISIBLE_SCHEMA

    assert visible["format"] == exhaustive["format"]
    assert visible["disposition"] == exhaustive["disposition"]["enum"]
    assert visible["direct_simple"] == exhaustive["branches"]["direct_simple"]["allowed_fields"]
    assert visible["components"] == exhaustive["branches"]["components"]["allowed_fields"]
    assert visible["component"]["required"] == exhaustive["component"]["required"]
    assert visible["component"]["optional"] == exhaustive["component"]["optional"]
    assert visible["source"]["kind"] == exhaustive["source"]["kind"]["enum"]
    assert visible["uncertainty"]["kind"] == exhaustive["uncertainty"]["kind"]["enum"]
    assert visible["limits"]["components"] == [
        exhaustive["components"]["min_items"],
        exhaustive["components"]["max_items"],
    ]
    assert visible["limits"]["components"][0] == 1
    assert visible["limits"]["need_chars"] == exhaustive["limits"]["need_chars"]
    assert exhaustive["branches"]["direct_simple"]["forbidden_fields"] == ["components"]
    assert exhaustive["branches"]["components"]["forbidden_fields"] == [
        "source",
        "freshness",
        "caveat",
    ]


@pytest.mark.parametrize(
    ("case_id", "query", "baseline_chars", "_phase1_chars"),
    _PHASE1_PROMPT_SCENARIOS,
    ids=[item[0] for item in _PHASE1_PROMPT_SCENARIOS],
)
def test_phase1_prompt_scenarios_keep_historical_reduction_envelope(
    case_id: str,
    query: str,
    baseline_chars: int,
    _phase1_chars: int,
) -> None:
    prompt_chars = _prompt_request_chars(query)
    reduction = 1 - (prompt_chars / baseline_chars)
    assert prompt_chars < baseline_chars
    if case_id == "clear_direct":
        assert reduction >= 0.84
    else:
        assert reduction >= 0.83


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
        "recon_requirement" not in strategy
        for requirement in first["component_search_requirements"]
        for strategy in requirement["metadata"]["query_strategy_candidates"]
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
    with pytest.raises(SearchPlannerSemanticProposalError) as semantic:
        validate_semantic_planner_proposal(deepcopy(case["proposal"]))
    assert semantic.value.subtype is SearchPlannerSemanticProposalSubtype(
        case["expected_subtype"]
    )
    expected_detail = case.get("expected_branch_field_set_detail")
    assert semantic.value.branch_field_set_detail is (
        SearchPlannerBranchFieldSetDetail(expected_detail)
        if expected_detail is not None
        else None
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(
            deepcopy(case["proposal"]),
            user_query_text="bounded offline query",
            requested_mode="Balanced",
        )
    assert caught.value.failure_code is (SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL)
    assert caught.value.semantic_proposal_subtype is semantic.value.subtype
    assert caught.value.branch_field_set_detail is semantic.value.branch_field_set_detail
    assert caught.value.predicate_id is not None
    assert str(caught.value) == "search planner semantic proposal failed closed"


def test_branch_field_set_detail_inventory_is_closed_and_value_free() -> None:
    assert {item.value for item in SearchPlannerBranchFieldSetDetail} == {
        "direct_simple_with_components",
        "direct_simple_disallowed_top_level",
        "components_disallowed_top_level",
        "components_required_nonempty",
        "nested_disallowed_field",
    }
    assert len(SearchPlannerBranchFieldSetDetail.__members__) == len(
        SearchPlannerBranchFieldSetDetail
    )

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
    assert accepted_slot.get("selected_value") is None
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
    assert _all_recon_requirements(compiled) == []


def test_case_a_stable_component_dispatches_standard_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("official_source_direct_simple")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="Python math.isclose defaults",
        primary_entity="Python",
        evidence_rows=[_evidence_row("Python", suffix="case-a")],
        deps_overrides=_product_deps(case["proposal"]),
    )

    ordered = _ordered_query_plan_items(outcome)
    assert {item["discovery_job_class"] for item in ordered} == {
        "standard_discovery"
    }
    assert len(harness.search_calls) == 1
    assert harness.search_calls[0]["search_providers"] == ["tavily"]
    [route] = outcome.execution_trace["provider_plan"]["records"]
    assert route["selection_inputs"]["discovery_job_class"] == (
        "standard_discovery"
    )
    assert route["route_decision"]["derivation_reason"] == (
        "query_plan_standard_discovery_job"
    )


def test_case_b_factual_uncertainty_binds_then_runs_standard_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("factual_identity_uncertainty")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="recent Galloway controversy",
        primary_entity="Galloway",
        evidence_rows=[
            _evidence_row("Scott Galloway", suffix="case-b-orientation")
        ],
        followup_evidence_rows=[
            _evidence_row("Scott Galloway", suffix="case-b-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(case["proposal"]),
    )

    assert [
        item["discovery_job_class"]
        for item in _ordered_query_plan_items(outcome)
    ] == ["orientation", "standard_discovery"]
    assert [call["search_providers"] for call in harness.search_calls] == [
        ["serper"],
        ["tavily"],
    ]
    accepted_slot = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ][0]
    assert accepted_slot["status"] == "unresolved"
    assert accepted_slot.get("selected_value") is None
    [binding] = harness.run_kernel.state.searchos_state[
        "interpretation_binding_history"
    ]
    assert binding["resolved_value"] == "Scott Galloway"
    assert binding["base_answer_contract_mutated"] is False
    assert binding["evidence_admitted"] is False
    assert binding["support_admitted"] is False
    assert binding["source_obligation_satisfied"] is False
    effective = build_searchos_effective_semantic_slot_view(
        state=harness.run_kernel.state.searchos_state,
        semantic_slot_id=accepted_slot["slot_id"],
        accepted_contract=harness.run_kernel.state.initial_answer_contract,
    )
    assert effective["effective_value"] == "Scott Galloway"
    assert effective["resolution_source"] == "interpretation_binding"
    assert effective["base_answer_contract_mutated"] is False


def test_unclassified_factual_term_uses_orientation_and_bounded_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Identify the externally verifiable Acme term",
                "uncertainties": [
                    {
                        "kind": "unknown_or_other",
                        "status": "unresolved",
                        "candidates": ["Acme Alpha", "Acme Beta"],
                    }
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="Which externally verifiable Acme term applies?",
        core_topic="applicable Acme term",
        primary_entity="Acme",
        evidence_rows=[_evidence_row("Acme Alpha", suffix="term-orientation")],
        followup_evidence_rows=[
            _evidence_row("Acme Alpha", suffix="term-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )

    assert [
        item["discovery_job_class"]
        for item in _ordered_query_plan_items(outcome)
    ] == ["orientation", "standard_discovery"]
    [binding] = harness.run_kernel.state.searchos_state[
        "interpretation_binding_history"
    ]
    assert binding["binding_category"] == (
        "externally_verifiable_terminology"
    )
    assert binding["base_answer_contract_mutated"] is False


def test_one_component_preserves_and_binds_two_factual_uncertainties(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": (
                    "Report the current policy for the intended Acme "
                    "product version"
                ),
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": [
                            "Acme Legacy",
                            "Acme Current",
                        ],
                    },
                    {
                        "kind": "variant",
                        "status": "unresolved",
                        "candidates": ["v2", "v3"],
                    },
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What is the current policy for the intended Acme version?",
        core_topic="Acme current product policy and version",
        primary_entity="Acme",
        evidence_rows=[
            _evidence_row("Acme Current v3", suffix="multi-slot-orientation")
        ],
        followup_evidence_rows=[
            _evidence_row("Acme Current v3", suffix="multi-slot-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )

    accepted_contract = (
        harness.run_kernel.state.initial_answer_contract
    )
    accepted_slots = list(
        accepted_contract["accepted_semantic_slot_refs"]
    )
    assert len(accepted_slots) == 2
    assert len(
        {
            item["slot_id"]
            for item in accepted_slots
            if item["materiality"] == "material"
            and item["unresolved_material"] is True
        }
    ) == 2
    initial_items = [
        item
        for item in _ordered_query_plan_items(outcome)
        if item["iteration"] == 1
    ]
    assert len(initial_items) == 1
    assert initial_items[0]["discovery_job_class"] == "orientation"
    assert {
        item["slot_id"]
        for item in initial_items[0]["semantic_slot_refs"]
    } == {item["slot_id"] for item in accepted_slots}
    state = harness.run_kernel.state.searchos_state
    obligations = list(state["semantic_obligations_by_id"].values())
    assert len(obligations) == 2
    assert {
        item["semantic_slot_ref"]["slot_id"]
        for item in obligations
    } == {item["slot_id"] for item in accepted_slots}
    bindings = list(state["interpretation_binding_history"])
    assert len(bindings) == 2
    assert len(
        {
            item["semantic_slot_ref"]["slot_id"]
            for item in bindings
        }
    ) == 2
    first_bound_request = next(
        item
        for item in harness.read_assessment_calls
        if len(item["interpretation_binding_refs"]) == 1
    )
    assert (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
        not in first_bound_request["legal_actions"]
    )
    assert first_bound_request["component_semantic_handoff_gate"][
        "all_relevant_material_semantic_obligations_satisfied"
    ] is False
    assert len(
        first_bound_request["component_semantic_handoff_gate"][
            "blocking_semantic_obligation_refs"
        ]
    ) == 1
    assert sorted(
        first_bound_request[
            "semantic_obligation_binding_postures"
        ].values()
    ) == ["bound", "unbound_required"]
    assert sorted(
        first_bound_request[
            "semantic_obligation_effective_statuses"
        ].values()
    ) == ["resolved_for_search_planning", "unresolved"]
    all_bound_request = next(
        item
        for item in harness.read_assessment_calls
        if len(item["interpretation_binding_refs"]) == 2
    )
    assert all_bound_request["component_semantic_handoff_gate"][
        "all_relevant_material_semantic_obligations_satisfied"
    ] is True
    assert all_bound_request["semantic_obligation_count"] == 2
    assert len(state["semantic_handoff_refs"]) == 1
    assert len(harness.search_calls) == 2
    assert all(
        item.get("selected_value") is None
        and item["status"] == "unresolved"
        for item in accepted_contract[
            "accepted_semantic_slot_refs"
        ]
    )
    assert all(
        item["base_answer_contract_mutated"] is False
        and item["evidence_admitted"] is False
        for item in bindings
    )


def test_case_c_deep_escalation_is_typed_blocked_without_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("minimal_direct_simple")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="capital of France",
        primary_entity="France",
        evidence_rows=[_evidence_row("France", suffix="case-c-standard")],
        read_assessment_decision="STANDARD_TO_DEEP_BLOCK",
        deps_overrides=_product_deps(case["proposal"]),
    )

    assert [
        item["discovery_job_class"]
        for item in _ordered_query_plan_items(outcome)
    ] == ["standard_discovery", "deep_discovery"]
    assert len(harness.search_calls) == 1
    records = outcome.execution_trace["provider_plan"]["records"]
    assert records[-1]["selection_inputs"]["discovery_job_class"] == (
        "deep_discovery"
    )
    assert records[-1]["route_decision"]["fidelity"] == "blocked"
    assert records[-1]["route_decision"]["block_reason"] == (
        "general_deep_authorization_required"
    )
    assert records[-1]["route_decision"][
        "general_deep_requested"
    ] is True


def test_resolved_semantic_peers_are_preserved_but_only_unresolved_drives_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Report Acme Current v3 policy",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "explicit",
                        "candidates": [
                            "Acme Legacy",
                            "Acme Current",
                        ],
                        "selected": "Acme Current",
                    },
                    {
                        "kind": "variant",
                        "status": "implied",
                        "candidates": ["v2", "v3"],
                        "selected": "v3",
                    },
                    {
                        "kind": "time_period",
                        "status": "unresolved",
                        "candidates": ["2025 policy", "2026 policy"],
                    },
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="Report Acme Current v3 policy for the intended year.",
        core_topic="Acme Current v3 policy year",
        primary_entity="Acme",
        evidence_rows=[
            _evidence_row("Acme Current v3 2026", suffix="resolved-peers")
        ],
        followup_evidence_rows=[
            _evidence_row(
                "Acme Current v3 2026",
                suffix="resolved-peers-standard",
            )
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )

    accepted_slots = list(
        harness.run_kernel.state.initial_answer_contract[
            "accepted_semantic_slot_refs"
        ]
    )
    assert len(accepted_slots) == 3
    unresolved_slot = next(
        item
        for item in accepted_slots
        if item["unresolved_material"] is True
    )
    stable_slot_ids = {
        item["slot_id"]
        for item in accepted_slots
        if item["unresolved_material"] is False
    }
    assert len(stable_slot_ids) == 2
    ordered = _ordered_query_plan_items(outcome)
    assert all(
        {
            item["slot_id"]
            for item in query_item["semantic_slot_refs"]
        }
        == {unresolved_slot["slot_id"]}
        for query_item in ordered
    )
    state = harness.run_kernel.state.searchos_state
    obligations = list(state["semantic_obligations_by_id"].values())
    assert len(obligations) == 3
    by_slot_id = {
        item["semantic_slot_ref"]["slot_id"]: item
        for item in obligations
    }
    assert {
        by_slot_id[slot_id]["binding_posture"]
        for slot_id in stable_slot_ids
    } == {"not_required"}
    assert all(
        by_slot_id[slot_id]["acquisition_driving"] is False
        for slot_id in stable_slot_ids
    )
    assert by_slot_id[unresolved_slot["slot_id"]][
        "acquisition_driving"
    ] is True
    assert by_slot_id[unresolved_slot["slot_id"]][
        "binding_posture"
    ] == "bound"
    [binding] = state["interpretation_binding_history"]
    assert binding["semantic_slot_ref"]["slot_id"] == (
        unresolved_slot["slot_id"]
    )
    after_binding = next(
        item
        for item in harness.read_assessment_calls
        if item["interpretation_binding_refs"]
    )
    assert after_binding["component_semantic_handoff_gate"][
        "all_relevant_material_semantic_obligations_satisfied"
    ] is True
    assert len(state["semantic_handoff_refs"]) == 1


def test_one_component_factual_and_clarification_postures_are_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Report the intended Acme policy",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": [
                            "Acme Legacy",
                            "Acme Current",
                        ],
                    },
                    {
                        "kind": "variant",
                        "status": "ambiguous",
                        "candidates": [
                            "consumer policy",
                            "enterprise policy",
                        ],
                        "user_confirmation_required": True,
                    },
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="Report the intended Acme policy.",
        core_topic="intended Acme policy",
        primary_entity="Acme",
        evidence_rows=[
            _evidence_row("Acme Current", suffix="mixed-slot-orientation")
        ],
        followup_evidence_rows=[
            _evidence_row("Acme Current", suffix="mixed-slot-standard")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )

    accepted_slots = list(
        harness.run_kernel.state.initial_answer_contract[
            "accepted_semantic_slot_refs"
        ]
    )
    factual_slot = next(
        item
        for item in accepted_slots
        if item["user_confirmation_required"] is False
    )
    clarification_slot = next(
        item
        for item in accepted_slots
        if item["user_confirmation_required"] is True
    )
    ordered = _ordered_query_plan_items(outcome)
    assert ordered
    assert all(
        {
            item["slot_id"]
            for item in query_item["semantic_slot_refs"]
        }
        == {factual_slot["slot_id"]}
        for query_item in ordered
    )
    assert clarification_slot["slot_id"] not in {
        item["slot_id"]
        for query_item in ordered
        for item in query_item["semantic_slot_refs"]
    }
    state = harness.run_kernel.state.searchos_state
    obligations_by_slot_id = {
        item["semantic_slot_ref"]["slot_id"]: item
        for item in state["semantic_obligations_by_id"].values()
    }
    factual_obligation = obligations_by_slot_id[
        factual_slot["slot_id"]
    ]
    clarification_obligation = obligations_by_slot_id[
        clarification_slot["slot_id"]
    ]
    assert factual_obligation["binding_posture"] == "bound"
    assert factual_obligation["clarification_posture"][
        "clarification_required"
    ] is False
    assert clarification_obligation["binding_posture"] == "not_required"
    assert clarification_obligation["clarification_posture"][
        "clarification_required"
    ] is True
    [binding] = state["interpretation_binding_history"]
    assert binding["semantic_slot_ref"]["slot_id"] == (
        factual_slot["slot_id"]
    )
    after_binding = next(
        item
        for item in harness.read_assessment_calls
        if item["interpretation_binding_refs"]
    )
    assert after_binding["component_semantic_handoff_gate"][
        "all_relevant_material_semantic_obligations_satisfied"
    ] is False
    assert (
        "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"
        not in after_binding["legal_actions"]
    )
    assert state["semantic_handoff_refs"] == []
    assert harness.search_calls
    assert all(
        item["base_answer_contract_mutated"] is False
        for item in state["interpretation_binding_history"]
    )


def test_candidate_less_factual_uncertainty_never_advertises_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "need": "Identify the current Acme designation",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                    }
                ],
            }
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query="What is the current Acme designation?",
        core_topic="current Acme designation",
        primary_entity="Acme",
        evidence_rows=[
            _evidence_row("Acme", suffix="candidate-less-orientation")
        ],
        read_assessment_decision="NO_READ",
        deps_overrides=_product_deps(proposal),
    )

    [accepted_slot] = harness.run_kernel.state.initial_answer_contract[
        "accepted_semantic_slot_refs"
    ]
    assert accepted_slot["status"] == "unresolved"
    assert accepted_slot["candidate_values"] == []
    [initial_item] = [
        item
        for item in _ordered_query_plan_items(outcome)
        if item["iteration"] == 1
    ]
    assert initial_item["discovery_job_class"] == "orientation"
    [request] = harness.read_assessment_calls
    assert request["binding_eligible_semantic_slot_ids"] == []
    assert (
        "PROPOSE_INTERPRETATION_BINDING"
        not in request["legal_actions"]
    )
    assert harness.run_kernel.state.searchos_state[
        "interpretation_binding_history"
    ] == []


def test_case_d_user_confirmation_requires_typed_clarification_no_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("true_user_intent_ambiguity")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="Mercury",
        primary_entity="Mercury",
        deps_overrides=_product_deps(case["proposal"]),
    )

    assert harness.search_calls == []
    assert outcome.execution_trace["provider_plan"]["records"] == []
    assert _ordered_query_plan_items(outcome) == []
    searchos = outcome.execution_trace["searchos_slice_a"]
    assert searchos["clarification_required"] is True
    assert searchos["clarification_only_no_dispatch"] is True
    assert searchos["provider_calls_attempted"] == 0
    [clarification] = searchos[
        "semantic_obligation_clarification_postures"
    ].values()
    assert clarification["clarification_required"] is True
    assert clarification["declared_candidates"] == [
        "planet",
        "element",
        "automobile brand",
    ]


def test_mixed_stable_factual_and_true_ambiguity_progress_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "disposition": "components",
        "components": [
            {
                "key": "stable",
                "need": "Report Alpha's current operating rule",
            },
            {
                "key": "identity",
                "need": "Identify the relevant Galloway controversy",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "unresolved",
                        "candidates": ["Scott Galloway", "George Galloway"],
                    }
                ],
            },
            {
                "key": "ambiguous",
                "need": "Explain the intended Mercury subject",
                "uncertainties": [
                    {
                        "kind": "entity",
                        "status": "ambiguous",
                        "candidates": [
                            "planet",
                            "element",
                            "automobile brand",
                        ],
                        "user_confirmation_required": True,
                    }
                ],
            },
        ],
    }
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=(
            "Report Alpha's rule, identify the relevant Galloway "
            "controversy, and explain Mercury."
        ),
        core_topic="Alpha rule, Galloway controversy, and Mercury",
        primary_entity="Alpha",
        evidence_rows=[_evidence_row("Alpha", suffix="mixed-standard")],
        followup_evidence_rows=[
            _evidence_row("Scott Galloway", suffix="mixed-orientation")
        ],
        read_assessment_decision="BIND_THEN_FOLLOWUP_THEN_READ",
        deps_overrides=_product_deps(proposal),
    )

    initial = [
        item
        for item in _ordered_query_plan_items(outcome)
        if item["iteration"] == 1
    ]
    assert [item["discovery_job_class"] for item in initial] == [
        "standard_discovery",
        "orientation",
    ]
    assert [call["search_providers"] for call in harness.search_calls[:2]] == [
        ["tavily"],
        ["serper"],
    ]
    state = harness.run_kernel.state.searchos_state
    assert len(state["active_slot_ids"]) == 3
    clarification_slots = [
        slot
        for slot in state["slots_by_id"].values()
        if slot["posture"] == "clarification_required"
    ]
    assert len(clarification_slots) == 1
    assert clarification_slots[0]["current_discovery_job_class"] is None
    clarification_obligations = [
        state["semantic_obligations_by_id"][semantic_obligation_id]
        for semantic_obligation_id in clarification_slots[0][
            "semantic_obligation_ids"
        ]
        if state["semantic_obligations_by_id"][
            semantic_obligation_id
        ]["clarification_posture"]["clarification_required"]
        is True
    ]
    assert len(clarification_obligations) == 1
    assert clarification_obligations[0]["clarification_posture"][
        "declared_candidates"
    ] == ["planet", "element", "automobile brand"]
    searchos = outcome.execution_trace["searchos_slice_a"]
    assert searchos["slot_local_candidate_ancestry_proven"] is True
    assert searchos["peer_slot_cursors_preserved"] is True
    assert len(searchos["interpretation_binding_refs"]) == 1
    assert sum(
        posture.get("clarification_required") is True
        for posture in searchos[
            "semantic_obligation_clarification_postures"
        ].values()
    ) == 1
    assert searchos["provider_calls_attempted"] == 2


def test_zero_result_orientation_refines_once_then_stops_unresolved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("factual_identity_uncertainty")
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="recent Galloway controversy",
        primary_entity="Galloway",
        evidence_rows=[],
        followup_evidence_rows=[],
        read_assessment_decision="ZERO_ORIENTATION_REFINE",
        deps_overrides=_product_deps(case["proposal"]),
    )

    ordered = _ordered_query_plan_items(outcome)
    assert [item["discovery_job_class"] for item in ordered] == [
        "orientation",
        "orientation",
    ]
    assert [item["iteration"] for item in ordered] == [1, 2]
    assert len(harness.search_calls) == 2
    assert all(
        call["search_providers"] == ["serper"]
        for call in harness.search_calls
    )
    [slot] = harness.run_kernel.state.searchos_state["slots_by_id"].values()
    assert slot["orientation_refinement_count"] == 1
    assert slot["posture"] in {
        "unresolved_handoff",
        "budget_exhausted",
    }
    assert harness.searchos_product_result is not None
    assert len(harness.searchos_product_result.iteration_candidate_sets) == 1
    assert harness.searchos_product_result.revision_1[
        "zero_result_discover_wave_ref"
    ]


def test_binding_replay_conflict_and_exact_field_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = valid_case("factual_identity_uncertainty")
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        query=case["query"],
        core_topic="recent Galloway controversy",
        primary_entity="Galloway",
        evidence_rows=[
            _evidence_row("Scott Galloway", suffix="binding-replay")
        ],
        deps_overrides=_product_deps(case["proposal"]),
    )
    state = harness.run_kernel.state.searchos_state
    [binding] = state["interpretation_binding_history"]
    accepted = harness.run_kernel.state.initial_answer_contract

    assert record_searchos_interpretation_binding(
        state,
        accepted_contract=accepted,
        binding=binding,
    ) == state
    conflict = _reenvelope_binding(
        binding,
        resolved_value="George Galloway",
    )
    with pytest.raises(
        SearchOSRuntimeError,
        match="conflicting interpretation binding",
    ):
        record_searchos_interpretation_binding(
            state,
            accepted_contract=accepted,
            binding=conflict,
        )
    unexpected = _reenvelope_binding(binding, evidence={"forbidden": True})
    with pytest.raises(
        SearchOSRuntimeError,
        match="fields are not exact",
    ):
        validate_searchos_interpretation_binding(unexpected)

    wrong_semantic = _reenvelope_binding(
        binding,
        semantic_slot_ref={
            **dict(binding["semantic_slot_ref"]),
            "slot_id": "semantic-slot:foreign",
        },
    )
    with pytest.raises(
        SearchOSRuntimeError,
        match="semantic obligation ref is stale or altered",
    ):
        validate_searchos_interpretation_binding(
            wrong_semantic,
            state=state,
            accepted_contract=accepted,
        )

    foreign_component = _reenvelope_binding(
        binding,
        component_ref={
            **dict(binding["component_ref"]),
            "component_id": "component:foreign",
        },
    )
    with pytest.raises(
        SearchOSRuntimeError,
        match="active-slot lineage is stale",
    ):
        validate_searchos_interpretation_binding(
            foreign_component,
            state=state,
            accepted_contract=accepted,
        )

    changed_source_scope = _reenvelope_binding(
        binding,
        component_ref={
            **dict(binding["component_ref"]),
            "source_obligation_candidate_ids": [
                "source-obligation:foreign"
            ],
        },
    )
    with pytest.raises(
        SearchOSRuntimeError,
        match="active-slot lineage is stale",
    ):
        validate_searchos_interpretation_binding(
            changed_source_scope,
            state=state,
            accepted_contract=accepted,
        )

    for authority_field in (
        "base_answer_contract_mutated",
        "evidence_admitted",
        "support_admitted",
        "source_obligation_satisfied",
        "coverage_created",
        "citation_eligible",
    ):
        authority_claim = _reenvelope_binding(
            binding,
            **{authority_field: True},
        )
        with pytest.raises(
            SearchOSRuntimeError,
            match=f"authority field {authority_field} is invalid",
        ):
            validate_searchos_interpretation_binding(authority_claim)
