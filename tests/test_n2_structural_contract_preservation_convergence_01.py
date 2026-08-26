from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

import pytest

from core.run_authority_contract_templates import build_deterministic_contract
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    contract_ref_from_contract,
    execute_search_planner_action,
)
from core.search_planner_semantic_compiler import SearchPlannerSemanticValidationRuleId

RUN_ID = "run:n2-structural-contract-preservation"
REQUEST_ID = "request:n2-structural-contract-preservation"
Q1 = (
    "1. Report the overall length of the Boeing 777-9 using only Boeing's official "
    "published specifications. 2. Report the overall length of the Airbus A350-1000 "
    "using only Airbus's official published specifications. Then compare the two stated "
    "lengths and say which aircraft is longer. Cite the official manufacturer source for "
    "each value. Do not calculate a difference, ratio, percentage, or converted value."
)


class _FakeAskModel:
    def __init__(self, proposal: Mapping[str, Any]) -> None:
        self.proposal = deepcopy(dict(proposal))

    def __call__(self, _prompt: str, _system_prompt: str, **_kwargs: Any) -> str:
        return json.dumps(self.proposal)


def _kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _planner_input(
    kernel: RunKernel,
    *,
    query: str = Q1,
) -> SearchPlannerInput:
    return SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text=query,
        requested_mode="balanced",
        safe_context={
            "route_facts": {
                "intent": "general",
                "report_type": "general_research",
                "query_type": "factual",
                "core_topic": query,
                "primary_entity": "bounded-fixture",
                "is_academic": False,
            },
            "run_contract_projection": {
                "contract_id": "contract:n2-structural-contract-preservation",
                "selected_depth": "balanced",
            },
            "current_date": "2026-08-25",
        },
        route_context_ref={"route_id": "route:n2-structural-contract-preservation"},
        run_context_ref={"run_contract_id": "contract:n2-structural-contract-preservation"},
        parent_initial_contract_ref=contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )


def _adapter(proposal: Mapping[str, Any]) -> SearchPlannerModelAdapter:
    return SearchPlannerModelAdapter(
        ask_model=_FakeAskModel(proposal),
        clean_json_response=lambda value: value,
        provider="fixture-provider",
        model="fixture-model",
        effort="low",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )


def _execute(
    planner_input: SearchPlannerInput,
    proposal: Mapping[str, Any],
) -> tuple[RunKernel, Mapping[str, Any]]:
    kernel = _kernel()
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=_adapter(proposal),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)
    return kernel, result.observation_payload


def _qualified_slots(planner_input: SearchPlannerInput) -> list[dict[str, Any]]:
    payload = planner_input.to_adapter_payload()
    structure = payload["qualified_multicomponent_structure_for_planning"]
    return list(structure["component_slots"])


def _components_proposal(
    questions: list[str],
    *,
    source_kind: str = "official_current",
    calculation: str | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    for question in questions:
        component: dict[str, Any] = {
            "need": question,
            "source": {"kind": source_kind, "strictness": "required"},
        }
        if calculation:
            component["calculation"] = calculation
        components.append(component)
    return {"disposition": "components", "components": components}


def test_q1_structure_binds_two_required_components_and_one_directive() -> None:
    kernel = _kernel()
    planner_input = _planner_input(kernel)
    slots = _qualified_slots(planner_input)

    reduced_kernel, observation_payload = _execute(
        planner_input,
        _components_proposal([str(slot["user_facing_question"]) for slot in slots]),
    )
    qmr = observation_payload["question_meaning_record"]
    structure = planner_input.to_adapter_payload()[
        "qualified_multicomponent_structure_for_planning"
    ]

    assert [item["component_id"] for item in qmr["answer_components"]] == [
        slot["component_id"] for slot in slots
    ]
    assert [item["user_facing_question"] for item in qmr["answer_components"]] == [
        slot["user_facing_question"] for slot in slots
    ]
    assert qmr["metadata"]["explicit_factual_component_list"] is True
    assert qmr["metadata"]["requested_synthesis_directive"] == structure[
        "requested_synthesis_directive"
    ]
    assert qmr["metadata"]["qualified_multicomponent_structure_bound"] is True
    assert all(
        item["component_purpose"] == "user_facing_answer_target"
        and item["requirement_posture"] == "required"
        for item in qmr["answer_components"]
    )
    assert not any(
        item["obligation_kind"] == "source_bound_numeric"
        for item in qmr["source_obligation_candidate_refs"]
    )

    acceptance = reduced_kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr["record_id"]),
        parent_proposal_digest=str(qmr["record_digest"]),
    )
    reduced_kernel.reduce(
        Observation.from_action(
            acceptance,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": qmr},
        )
    )
    accepted = reduced_kernel.state.initial_answer_contract
    assert accepted is not None
    assert [item["component_id"] for item in accepted["accepted_answer_component_refs"]] == [
        slot["component_id"] for slot in slots
    ]


@pytest.mark.parametrize(
    "proposal_builder",
    [
        lambda slots, directive: _components_proposal(
            [str(slot["user_facing_question"]) for slot in slots]
            + [directive]
        ),
        lambda slots, directive: _components_proposal(
            [str(slots[0]["user_facing_question"]), directive]
        ),
        lambda slots, _directive: _components_proposal(
            [
                str(slots[0]["user_facing_question"]),
                "A foreign replacement answer target.",
            ]
        ),
        lambda slots, directive: _components_proposal(
            [
                str(slots[1]["user_facing_question"]),
                str(slots[0]["user_facing_question"]),
            ]
        ),
    ],
    ids=(
        "third-required-component",
        "directive-promoted-to-component",
        "component-replaced",
        "component-order-reversed",
    ),
)
def test_qualified_model_structure_drift_fails_closed(
    proposal_builder: Any,
) -> None:
    kernel = _kernel()
    planner_input = _planner_input(kernel)
    payload = planner_input.to_adapter_payload()
    slots = list(payload["qualified_multicomponent_structure_for_planning"]["component_slots"])
    directive = str(
        payload["qualified_multicomponent_structure_for_planning"][
            "requested_synthesis_directive"
        ]
    )

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _execute(planner_input, proposal_builder(slots, directive))

    assert caught.value.failure_metadata.semantic_validation_rule_id is (
        SearchPlannerSemanticValidationRuleId.QUALIFIED_MULTICOMPONENT_STRUCTURE_BINDING
    )


def test_direct_source_stated_numeric_fact_does_not_create_source_bound_numeric() -> None:
    kernel = _kernel()
    planner_input = _planner_input(kernel)
    slots = _qualified_slots(planner_input)

    _, observation_payload = _execute(
        planner_input,
        _components_proposal([str(slot["user_facing_question"]) for slot in slots]),
    )
    qmr = observation_payload["question_meaning_record"]

    assert [item["obligation_kind"] for item in qmr["source_obligation_candidate_refs"]] == [
        "official_current",
        "official_current",
    ]
    assert all(
        item.get("calculation_policy") is None
        for item in qmr["answer_components"]
    )

    deterministic_contract = build_deterministic_contract(
        query=Q1,
        mode="balanced",
        route_facts={
            "query_type": "quantitative_comparison",
            "core_topic": "Boeing 777-9 and Airbus A350-1000 lengths",
        },
    ).to_projection()
    assert not any(
        item["requirement_kind"] == "source_bound_numeric"
        for item in deterministic_contract["source_requirements"]
    )
    assert deterministic_contract["numeric_policy"]["source_bound_required"] is False


def test_genuine_calculation_can_nominate_source_bound_numeric() -> None:
    query = "Calculate the difference between two source-stated annual values."
    kernel = _kernel()
    planner_input = _planner_input(kernel, query=query)
    proposal = _components_proposal(
        [query],
        source_kind="source_bound_numeric",
        calculation="derive the requested difference from the two stated source values",
    )

    _, observation_payload = _execute(planner_input, proposal)
    qmr = observation_payload["question_meaning_record"]

    assert [item["obligation_kind"] for item in qmr["source_obligation_candidate_refs"]] == [
        "source_bound_numeric"
    ]
    assert qmr["answer_components"][0]["calculation_policy"]


def test_source_bound_numeric_without_a_calculation_posture_fails_closed() -> None:
    query = "Report the source-stated annual value."
    kernel = _kernel()
    planner_input = _planner_input(kernel, query=query)

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _execute(
            planner_input,
            _components_proposal([query], source_kind="source_bound_numeric"),
        )

    assert caught.value.failure_metadata.semantic_validation_rule_id is (
        SearchPlannerSemanticValidationRuleId.SOURCE_BOUND_NUMERIC_REQUIRES_CALCULATION
    )


def test_existing_n1_direct_source_path_remains_valid() -> None:
    query = "Report the official published altitude of the Example Orbiter."
    kernel = _kernel()
    planner_input = _planner_input(kernel, query=query)

    _, observation_payload = _execute(
        planner_input,
        _components_proposal([query]),
    )
    qmr = observation_payload["question_meaning_record"]

    assert len(qmr["answer_components"]) == 1
    assert qmr["metadata"]["qualified_multicomponent_structure_bound"] is False
