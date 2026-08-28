"""PHASE-FOCUS DURABLE REGRESSION: same-URL cross-component custody isolation.

This deterministic offline regression exercises two required
component/source-obligation slots that nominate the same normalized URL.  It
uses static judgments and an in-memory acquisition response; no model,
network, or external-provider transport is invoked.

Test classification: phase_focus.  The two-order authority assertion is a
durable regression sentinel for SearchOS custody reuse, not a bucket-wide
smoke test.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import core.searchos_slice_a_product_runtime as slice_runtime
from core.acquisition_adapters import AcquisitionTransports
from core.discovery_source_result import (
    DiscoveryResultMaterialStore,
    normalize_discovery_result_url,
)
from core.evidence_ledger_lifecycle import reduce_run_contract_requirements_into_evidence_ledger
from core.initial_query_allocation_policy import InitialQueryAllocationPolicy
from core.ordinary_discovery_candidate_handoff_runtime import (
    build_ordinary_discovery_authority_snapshot,
    build_ordinary_discovery_candidate_action_inputs,
    execute_ordinary_discovery_candidate_handoff_action,
    prepare_ordinary_discovery_selection,
)
from core.provider_plan import ProviderPlan
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_executor_handoff_runtime import contract_ref_from_contract
from core.search_judgment_read_assessment_runtime import (
    derive_selected_candidate_material_need_bindings,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from tests.test_ag_search_executor_handoff_01 import _planner_result

RUN_ID = "same-url-cross-component-custody-reuse"
REQUEST_ID = "same-url-cross-component-custody-reuse-request"
SHARED_URL = "https://example.test/shared-official-rule#discovery-fragment"
NORMALIZED_SHARED_URL = normalize_discovery_result_url(SHARED_URL)


class _TwoComponentAdapter:
    """Static legal A/B proposal; no planner/model transport is used."""

    def __init__(self, order: Sequence[str]) -> None:
        self._order = tuple(order)

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        proposal = deepcopy(_planner_result())
        base_component = deepcopy(proposal["answer_components"][0])
        base_requirement = deepcopy(proposal["component_search_requirements"][0])
        base_strategy = {
            "candidate_kind": "primary",
            "requested_role": "initial",
            "candidate_query_text": "official current rule",
            "source_obligation_candidate_ids": [
                "obligation:official-current"
            ],
        }
        base_obligation = deepcopy(proposal["source_obligation_candidates"][0])

        components: list[dict[str, Any]] = []
        requirements: list[dict[str, Any]] = []
        obligations: list[dict[str, Any]] = []
        semantic_slots: list[dict[str, Any]] = []
        for name in self._order:
            slug = name.lower()
            component_id = f"component{slug}"
            obligation_id = f"obligation{slug}"
            semantic_slot_id = f"slot{slug}"
            semantic_slots.append(
                {
                    "slot_id": semantic_slot_id,
                    "slot_kind": "entity",
                    "status": "explicit",
                    "selected_value": f"Component {name}",
                    "materiality": "material",
                }
            )
            component = deepcopy(base_component)
            component.update(
                {
                    "component_id": component_id,
                    "component_revision": "1",
                    "user_facing_label": f"Component {name}",
                    "user_facing_question": f"What is Component {name}'s official rule?",
                    "source_obligation_candidate_ids": [obligation_id],
                    "semantic_slot_ids": [semantic_slot_id],
                }
            )
            components.append(component)

            strategy = deepcopy(base_strategy)
            strategy.update(
                {
                    "strategy_id": f"strategy:{name}",
                    "component_id": component_id,
                    "candidate_query_text": f"Component {name} official rule",
                    "source_obligation_candidate_ids": [obligation_id],
                    "search_requirement_ref": {
                        "requirement_id": f"requirement{slug}",
                        "component_id": component_id,
                        "source_obligation_candidate_ids": [obligation_id],
                    },
                }
            )
            requirement = deepcopy(base_requirement)
            requirement.update(
                {
                    "component_id": component_id,
                    "requirement_id": f"requirement{slug}",
                    "requirement_summary": f"Find Component {name}'s official rule.",
                    "source_obligation_candidate_ids": [obligation_id],
                    "metadata": {"query_strategy_candidates": [strategy]},
                }
            )
            requirements.append(requirement)

            obligation = deepcopy(base_obligation)
            obligation.update(
                {
                    "candidate_id": obligation_id,
                    "component_candidate_ids": [component_id],
                }
            )
            obligations.append(obligation)

        proposal["answer_components"] = components
        proposal["component_search_requirements"] = requirements
        proposal["source_obligation_candidates"] = obligations
        proposal["semantic_slots"] = semantic_slots
        return proposal


def _accept_two_component_contract(order: Sequence[str]) -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    planner_input = SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text="Compare two independently required official rules.",
        requested_mode="fast",
        safe_context={},
        parent_initial_contract_ref={},
        parent_current_contract_ref={},
    )
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    produced = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=_TwoComponentAdapter(order),
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=produced.observation_payload,
        )
    )
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    acceptance = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=qmr["record_id"],
        parent_proposal_digest=qmr["record_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            acceptance,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": qmr},
        )
    )
    return kernel


def _ledger_requirement_projection(order: Sequence[str]) -> dict[str, Any]:
    """Static ordinary-contract requirements for the two lawful slots."""

    return {
        "contract_id": "same-url-cross-component-custody-fixture",
        "source_requirements": [
            {
                "requirement_id": f"requirement{name.lower()}",
                "requirement_kind": "official_current",
                "required_source_class": "official_current",
                "component_id": f"component{name.lower()}",
                "source_obligation_id": f"obligation{name.lower()}",
            }
            for name in order
        ],
    }


def _query_authority(kernel: RunKernel):
    accepted = kernel.state.current_answer_contract or kernel.state.initial_answer_contract
    authority = build_query_plan_runtime_adapter(
        run_id=RUN_ID,
        primary_entity="Component",
        entities_list=None,
        core_topic="official rule",
        user_query="Compare two independently required official rules.",
        intent="general",
        clean=lambda text: text,
    )
    accepted_component_refs = {
        str(component["component_id"]): dict(component)
        for component in accepted["accepted_answer_component_refs"]
    }
    strategies: list[dict[str, Any]] = []
    for requirement in kernel.state.search_planner_proposal_state[
        "component_search_requirements"
    ]:
        strategy = deepcopy(requirement["metadata"]["query_strategy_candidates"][0])
        strategy["search_requirement_ref"] = {
            "requirement_id": requirement["requirement_id"],
            "component_id": requirement["component_id"],
            "source_obligation_candidate_ids": list(
                requirement["source_obligation_candidate_ids"]
            ),
        }
        strategy["accepted_component_ref"] = accepted_component_refs[
            str(requirement["component_id"])
        ]
        strategies.append(strategy)
    admitted = authority.admit_initial_component_strategies(
        strategies,
        accepted_contract=accepted,
        policy=InitialQueryAllocationPolicy(),
    )
    authority.admit_execution_queries(
        admitted.immediate_dispatch_queries,
        iteration=1,
        recovery_active=False,
    )
    return authority


def _candidate_packet(kernel: RunKernel, query_authority: Any) -> tuple[dict[str, Any], DiscoveryResultMaterialStore]:
    provider_plan = ProviderPlan.from_available_keys(
        {"tavily": True}, plan_id=f"provider-plan:{RUN_ID}"
    )
    provider_record = provider_plan.record_main_retrieval(
        query_type="other",
        intent="general",
        complexity="low",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=1,
        primary_override=["tavily"],
        scout_override=None,
        choose_search_depth=lambda _complexity, base, _iteration: base or "basic",
    )
    retrieval = kernel.authorize_main_retrieval_pass()
    kernel.reduce(
        Observation.from_action(
            retrieval,
            observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    retrieval_ref = {
        "action_id": retrieval.action_id,
        "action_type": retrieval.action_type.value,
        "stage": retrieval.stage,
        "sequence": retrieval.sequence,
    }
    store = DiscoveryResultMaterialStore(run_id=RUN_ID, request_id=REQUEST_ID)
    items = query_authority.plan.execution_item_refs(1)
    assert len(items) == 2
    for ordinal, item in enumerate(items, start=1):
        route = provider_record.route_decision
        identity = store.admit_result(
            context={
                "run_id": RUN_ID,
                "request_id": REQUEST_ID,
                "stage": "main_retrieval",
                "iteration": 1,
                "retrieval_role": "main_retrieval",
                "query_role": item["query_plan_role"],
                "retrieval_action_ref": retrieval_ref,
                "query_plan_ref": query_authority.plan.to_ref(),
                "query_plan_item_ref": item,
                "provider_plan_ref": provider_plan.to_ref(),
                "provider_plan_record_ref": provider_record.to_ref(),
                "provider_route_ref": provider_record.route_ref(),
                "provider_capability": route.capability.value,
                "provider_qualifier": route.qualifier.value,
                "provider_operation": route.operation or "",
                "provider_variant": route.variant or "",
                "provider_output_type": route.output_type or "",
            },
            provider="tavily",
            call_ordinal=ordinal,
            result_rank=1,
            result={
                "title": "Shared official rule",
                "url": SHARED_URL,
                "domain": "example.test",
                "snippet": "Shared bounded discovery material.",
            },
            material_text="Shared bounded discovery material.",
            material_class="provider_returned_excerpt",
        )
        assert identity is not None

    snapshot = build_ordinary_discovery_authority_snapshot(
        query_plan=query_authority.plan,
        provider_plan=provider_plan,
    )
    first_identity = store.identities()[0]
    selection = prepare_ordinary_discovery_selection(
        final_top_evidence=[
            {
                "url": SHARED_URL,
                "score": 1.0,
                "rrf_score": 0.1,
                "credibility": 10,
                "chunk_digest": "a" * 64,
                "source_result_ref": first_identity.ref(),
                "source_material_ref": dict(first_identity.material_ref),
            }
        ],
        discovery_result_store=store,
        selected_candidate_cap=1,
        authority_snapshot=snapshot,
    )
    active_contract = (
        kernel.state.current_answer_contract or kernel.state.initial_answer_contract
    )
    answer_contract_ref = contract_ref_from_contract(
        active_contract,
        source=(
            "current_answer_contract"
            if kernel.state.current_answer_contract
            else "initial_answer_contract"
        ),
    )
    inputs = build_ordinary_discovery_candidate_action_inputs(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        source_result_identity_set_ref=store.identity_set_ref(),
        selection=selection,
        answer_contract_ref=answer_contract_ref,
    )
    action = kernel.authorize_ordinary_discovery_candidate_handoff(inputs=inputs)
    execution = execute_ordinary_discovery_candidate_handoff_action(
        action=action,
        selection=selection,
        discovery_result_store=store,
        authority_snapshot=snapshot,
        answer_contract_ref=answer_contract_ref,
    )
    kernel.reduce(execution.observation)
    return dict(execution.packet), store


def _deterministic_judgment(
    *,
    model_input: Mapping[str, Any],
    **_kwargs: Any,
) -> dict[str, Any]:
    """Return static legal decisions without invoking a model transport."""

    request = dict(model_input["authorized_request"])
    custody_refs = list(request.get("read_custody_refs") or ())
    options = list(request.get("candidate_use_options") or ())
    if custody_refs:
        return {
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION",
            "read_custody_material_ids": [
                item["read_custody_material_id"] for item in custody_refs
            ],
            "reason": "static custody handoff",
        }
    if not options:
        return {
            "schema_version": "searchos_judgment_decision_v1",
            "action": "HANDOFF_UNRESOLVED",
            "reason": "static fixture has no candidate option",
        }
    return {
        "schema_version": "searchos_judgment_decision_v1",
        "action": "REQUEST_READ_PAGE",
        "candidate_use_option_id": options[0][
            "candidate_use_option_ref"
        ]["candidate_use_option_id"],
        "reason": "static deterministic read",
    }


def _run_case(monkeypatch: Any, order: Sequence[str]) -> dict[str, Any]:
    kernel = _accept_two_component_contract(order)
    query_authority = _query_authority(kernel)
    packet, store = _candidate_packet(kernel, query_authority)
    binding_state = derive_selected_candidate_material_need_bindings(
        run_kernel=kernel,
        candidate_packet=packet,
        query_plan=query_authority.plan,
        discovery_result_store=store,
    )
    assert binding_state["binding_count"] == 2
    reduce_run_contract_requirements_into_evidence_ledger(
        run_kernel=kernel,
        run_id=RUN_ID,
        run_contract_projection=_ledger_requirement_projection(order),
        observation_id_suffix="same-url-cross-component-fixture",
        authorization_observation_source="same_url_cross_component_fixture",
    )
    reads: list[dict[str, Any]] = []
    monkeypatch.setattr(
        slice_runtime,
        "_invoke_judgment_model",
        _deterministic_judgment,
    )
    result = slice_runtime.execute_searchos_slice_a_iterative_judgment(
        run_kernel=kernel,
        candidate_packet=packet,
        query_authority=query_authority,
        discovery_result_store=store,
        profile_name="Fast",
        ask_model=None,
        provider=None,
        model=None,
        base_url=None,
        api_key=None,
        use_reasoning=False,
        available_providers={"tavily": True},
        acquisition_transports=AcquisitionTransports(
            tavily_extract=lambda payload: reads.append(dict(payload))
            or {
                "results": [
                    {
                        "url": SHARED_URL,
                        "raw_content": "Shared offline full-page material.",
                    }
                ],
                "failed_results": [],
            }
        ),
        execute_followup_discover=None,
    )
    slots = {
        str(slot["component_ref"]["component_id"]): dict(slot)
        for slot in kernel.state.searchos_state["slots_by_id"].values()
    }
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    custody_outcomes = {
        str(binding_id): dict(outcome)
        for binding_id, outcome in (result.reusable_read_custody_by_url or {}).items()
    }
    assert set(custody_outcomes) == {
        str(item["binding_id"]) for item in binding_state["bindings"]
    }, {
        "custody_outcome_binding_ids": list(custody_outcomes),
        "slot_postures": {
            component_id: slot["posture"] for component_id, slot in slots.items()
        },
        "slot_reasons": {
            component_id: slot["latest_reason"] for component_id, slot in slots.items()
        },
        "binding_count": binding_state["binding_count"],
        "binding_slots": [
            dict(item["component_ref"])
            | dict(item["source_obligation_ref"])
            for item in binding_state["bindings"]
        ],
    }
    return {
        "physical_read_count": len(reads),
        "provider_calls_attempted": result.provider_calls_attempted,
        "provider_calls_completed": result.provider_calls_completed,
        "slots": slots,
        "ledger": ledger,
        "kernel": kernel,
        "candidate_packet": packet,
        "bindings": tuple(binding_state["bindings"]),
        "custody_outcomes": custody_outcomes,
    }


def _assert_component_lane(case: Mapping[str, Any], name: str) -> dict[str, str]:
    slug = name.lower()
    component_id = f"component{slug}"
    source_obligation_id = f"obligation{slug}"
    slot = case["slots"][component_id]
    custody = dict(slot["custody_refs"][0])

    assert custody["same_normalized_url_reused"] is False
    assert custody["slot_ref"]["component_id"] == component_id
    assert custody["slot_ref"]["source_obligation_id"] == source_obligation_id
    assert custody["normalized_url"] == NORMALIZED_SHARED_URL
    assert "physical_evidence_ledger_custody_ref" not in custody
    assert custody["support_admitted"] is False
    assert custody["source_obligation_satisfied"] is False
    assert custody["citation_eligible"] is False

    authorization = case["kernel"].require_current_acquisition_custody_authorization(
        custody["custody_authorization_ref"]
    )
    work_order = dict(
        case["kernel"].state.acquisition_control_state["work_orders_by_id"][
            authorization["work_order_ref"]["work_order_id"]
        ]
    )
    assert work_order["component_ref"]["component_id"] == component_id
    assert (
        work_order["source_obligation_ref"]["source_obligation_id"]
        == source_obligation_id
    )

    requirements = [
        item
        for item in case["ledger"]["source_requirements"]
        if item["component_id"] == component_id
        and item["source_obligation_id"] == source_obligation_id
    ]
    assert len(requirements) == 1
    requirement_id = requirements[0]["requirement_id"]
    exact_links = [
        link
        for link in case["ledger"]["requirement_links"]
        if link["requirement_id"] == requirement_id
        and link["candidate_id"] == custody["evidence_ledger_candidate_id"]
    ]
    assert len(exact_links) == 1
    assert exact_links[0]["link_reason"] == (
        "exact_searchos_read_custody_slot_binding"
    )

    ledger_ref = custody["evidence_ledger_custody_ref"]
    assert ledger_ref["owner"] == case["ledger"]["owner"]
    assert ledger_ref["schema_version"] == case["ledger"]["schema_version"]
    records = case["ledger"]["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]
    matching_records = [
        item for item in records if item["reference_id"] == ledger_ref["reference_id"]
    ]
    assert len(matching_records) == 1
    assert matching_records[0]["reference_digest"] == ledger_ref["reference_digest"]

    binding = next(
        item
        for item in case["bindings"]
        if item["component_ref"]["component_id"] == component_id
    )
    outcome = case["custody_outcomes"][binding["binding_id"]]
    assert outcome["custody_record"]["custody_authorization_ref"] == (
        custody["custody_authorization_ref"]
    )
    assert "physical_evidence_ledger_custody_ref" not in outcome["custody_record"]
    assert outcome["custody_record"]["evidence_ledger_observation_ref"][
        "observation_id"
    ].endswith(custody["custody_authorization_ref"]["authorization_id"])

    return {
        "component_id": component_id,
        "source_obligation_id": source_obligation_id,
        "work_order_component_id": work_order["component_ref"]["component_id"],
        "work_order_source_obligation_id": work_order["source_obligation_ref"][
            "source_obligation_id"
        ],
        "ledger_schema_version": ledger_ref["schema_version"],
    }


def test_same_url_cross_component_custody_uses_independent_acquisition_lanes(
    monkeypatch: Any,
) -> None:
    """Same-URL siblings use normal A/B READ lanes and retain their own authority."""

    a_then_b = _run_case(monkeypatch, ("A", "B"))
    b_then_a = _run_case(monkeypatch, ("B", "A"))

    assert a_then_b["physical_read_count"] == 2
    assert b_then_a["physical_read_count"] == 2

    authority_shapes: dict[str, dict[str, dict[str, str]]] = {}
    for case_name, case in {
        "A_THEN_B": a_then_b,
        "B_THEN_A": b_then_a,
    }.items():
        assert case["provider_calls_attempted"] == 2
        assert case["provider_calls_completed"] == 2
        assert len(case["custody_outcomes"]) == 2

        a_custody = case["slots"]["componenta"]["custody_refs"][0]
        b_custody = case["slots"]["componentb"]["custody_refs"][0]
        assert a_custody["custody_authorization_ref"] != b_custody[
            "custody_authorization_ref"
        ]
        assert a_custody["terminal_receipt_ref"] != b_custody["terminal_receipt_ref"]

        outcomes = case["custody_outcomes"]
        a_binding = next(
            item
            for item in case["bindings"]
            if item["component_ref"]["component_id"] == "componenta"
        )
        b_binding = next(
            item
            for item in case["bindings"]
            if item["component_ref"]["component_id"] == "componentb"
        )
        assert outcomes[a_binding["binding_id"]]["custody_record"][
            "evidence_ledger_observation_ref"
        ] != outcomes[b_binding["binding_id"]]["custody_record"][
            "evidence_ledger_observation_ref"
        ]

        authority_shapes[case_name] = {
            "A": _assert_component_lane(case, "A"),
            "B": _assert_component_lane(case, "B"),
        }

    assert authority_shapes["A_THEN_B"] == authority_shapes["B_THEN_A"]
