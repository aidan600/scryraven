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
from dataclasses import replace
from typing import Any, Mapping, Sequence

import pytest

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
    SearchJudgmentReadAssessmentError,
    SelectedCandidateMaterialNeedBindingV1,
    derive_selected_candidate_material_need_bindings,
    rebind_searchos_physical_read_material_to_custody,
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
    assert NORMALIZED_SHARED_URL in (result.reusable_read_custody_by_url or {}), {
        "reusable_urls": list((result.reusable_read_custody_by_url or {}).keys()),
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
        "reusable_physical_read_material": dict(
            (result.reusable_read_custody_by_url or {})[NORMALIZED_SHARED_URL]
        ),
    }


def test_same_url_reuse_isolates_custody_authority_per_component_in_both_orders(
    monkeypatch: Any,
) -> None:
    """One physical page may be reused, but A/B ledger authority may not."""

    a_then_b = _run_case(monkeypatch, ("A", "B"))
    b_then_a = _run_case(monkeypatch, ("B", "A"))

    assert a_then_b["physical_read_count"] == 1
    assert b_then_a["physical_read_count"] == 1

    cases = {
        "A_THEN_B": (a_then_b, ("A", "B")),
        "B_THEN_A": (b_then_a, ("B", "A")),
    }
    missing_requirement_links: list[str] = []
    authorities_by_case: dict[str, dict[str, Mapping[str, Any]]] = {}
    for case_name, (case, order) in cases.items():
        first_name, second_name = order
        first_custody = case["slots"][
            f"component{first_name.lower()}"
        ]["custody_refs"][0]
        second_custody = case["slots"][
            f"component{second_name.lower()}"
        ]["custody_refs"][0]
        assert first_custody["same_normalized_url_reused"] is False
        assert second_custody["same_normalized_url_reused"] is True
        assert case["provider_calls_attempted"] == 1
        assert case["provider_calls_completed"] == 1
        assert (
            second_custody["evidence_ledger_custody_ref"]["reference_id"]
            != first_custody["evidence_ledger_custody_ref"]["reference_id"]
        )
        assert (
            second_custody["physical_evidence_ledger_custody_ref"]
            == first_custody["physical_evidence_ledger_custody_ref"]
        )
        assert (
            second_custody["fetch_read_content_packet_ref"]
            == first_custody["fetch_read_content_packet_ref"]
        )

        physical_cache = case["reusable_physical_read_material"]
        assert physical_cache["normalized_url"] == NORMALIZED_SHARED_URL
        assert "custody_record" not in physical_cache
        assert "candidate_id" not in physical_cache["sanitized_read_material"]
        assert "candidate_digest" not in physical_cache["sanitized_read_material"]
        physical_records = case["ledger"]["fetch_read_candidate_custody"][
            "fetch_read_candidate_custody_records"
        ]
        assert len(physical_records) == 1

        authorities_by_case[case_name] = {}
        for name in ("A", "B"):
            slug = name.lower()
            slot = case["slots"][f"component{slug}"]
            custody = slot["custody_refs"][0]
            authorities_by_case[case_name][name] = dict(
                custody["evidence_ledger_custody_ref"]
            )
            assert custody["slot_ref"]["component_id"] == f"component{slug}"
            assert (
                custody["slot_ref"]["source_obligation_id"]
                == f"obligation{slug}"
            )
            assert custody["evidence_ledger_custody_ref"]["schema_version"] == (
                "searchos_evidence_ledger_binding_custody_ref_v1"
            )
            assert custody["evidence_ledger_custody_ref"] != custody[
                "physical_evidence_ledger_custody_ref"
            ]
            assert custody["support_admitted"] is False
            assert custody["source_obligation_satisfied"] is False
            assert custody["citation_eligible"] is False
            requirements = [
                item
                for item in case["ledger"]["source_requirements"]
                if item["component_id"] == f"component{slug}"
                and item["source_obligation_id"] == f"obligation{slug}"
            ]
            assert len(requirements) == 1
            requirement_id = requirements[0]["requirement_id"]
            linked_candidate_ids = [
                link["candidate_id"]
                for link in case["ledger"]["requirement_links"]
                if link["requirement_id"] == requirement_id
            ]
            exact_links = [
                link
                for link in case["ledger"]["requirement_links"]
                if link["requirement_id"] == requirement_id
                and link["candidate_id"]
                == custody["evidence_ledger_candidate_id"]
            ]
            assert len(exact_links) == 1
            assert exact_links[0]["link_reason"] == (
                "exact_searchos_read_custody_slot_binding"
            )
            if custody["evidence_ledger_candidate_id"] not in linked_candidate_ids:
                missing_requirement_links.append(
                    f"{case_name}/{name}: "
                    "custody.evidence_ledger_custody_ref.reference_id="
                    f"{custody['evidence_ledger_custody_ref']['reference_id']}; "
                    f"requirement_id={requirement_id}; "
                    f"linked_candidate_ids={linked_candidate_ids}"
                )

    assert not missing_requirement_links, "\n".join(missing_requirement_links)
    assert authorities_by_case["A_THEN_B"]["A"] == authorities_by_case[
        "B_THEN_A"
    ]["A"]
    assert authorities_by_case["A_THEN_B"]["B"] == authorities_by_case[
        "B_THEN_A"
    ]["B"]


def test_same_url_reuse_rejects_a_mismatched_consuming_binding(
    monkeypatch: Any,
) -> None:
    """Cached bytes cannot mint custody for a binding outside their URL lineage."""

    case = _run_case(monkeypatch, ("A", "B"))
    binding = SelectedCandidateMaterialNeedBindingV1.from_dict(case["bindings"][0])
    mismatched_binding = replace(
        binding,
        normalized_url="https://example.test/not-the-shared-official-rule",
    )
    ledger_before = deepcopy(
        case["kernel"].state.evidence_ledger.to_projection().to_dict()
    )

    with pytest.raises(
        SearchJudgmentReadAssessmentError,
        match="physical_read_material_url_mismatch",
    ):
        rebind_searchos_physical_read_material_to_custody(
            run_kernel=case["kernel"],
            binding=mismatched_binding,
            candidate_packet=case["candidate_packet"],
            physical_read_material=case["reusable_physical_read_material"],
        )

    assert case["physical_read_count"] == 1
    assert case["kernel"].state.evidence_ledger.to_projection().to_dict() == ledger_before


def test_same_url_reuse_rejects_a_stale_consuming_binding(
    monkeypatch: Any,
) -> None:
    """Cached material cannot mint custody through a component outside the contract."""

    case = _run_case(monkeypatch, ("A", "B"))
    binding = SelectedCandidateMaterialNeedBindingV1.from_dict(case["bindings"][0])
    stale_binding = replace(
        binding,
        component_ref={
            **dict(binding.component_ref),
            "component_id": "component-not-accepted",
        },
    )
    ledger_before = deepcopy(
        case["kernel"].state.evidence_ledger.to_projection().to_dict()
    )

    with pytest.raises(
        SearchJudgmentReadAssessmentError,
        match="proposal_component_stale",
    ):
        rebind_searchos_physical_read_material_to_custody(
            run_kernel=case["kernel"],
            binding=stale_binding,
            candidate_packet=case["candidate_packet"],
            physical_read_material=case["reusable_physical_read_material"],
        )

    assert case["physical_read_count"] == 1
    assert case["kernel"].state.evidence_ledger.to_projection().to_dict() == ledger_before


def test_same_binding_reuse_is_idempotent_without_another_physical_read(
    monkeypatch: Any,
) -> None:
    """The already-lawful component/obligation binding remains safely reusable."""

    case = _run_case(monkeypatch, ("A", "B"))
    binding = SelectedCandidateMaterialNeedBindingV1.from_dict(case["bindings"][0])
    expected_custody = case["slots"]["componenta"]["custody_refs"][0]
    ledger_before = deepcopy(
        case["kernel"].state.evidence_ledger.to_projection().to_dict()
    )

    rebound = rebind_searchos_physical_read_material_to_custody(
        run_kernel=case["kernel"],
        binding=binding,
        candidate_packet=case["candidate_packet"],
        physical_read_material=case["reusable_physical_read_material"],
    )

    assert case["physical_read_count"] == 1
    assert rebound["custody_record"]["evidence_ledger_custody_ref"] == (
        expected_custody["evidence_ledger_custody_ref"]
    )
    assert rebound["custody_record"]["fetch_read_content_packet_ref"] == (
        expected_custody["fetch_read_content_packet_ref"]
    )
    assert case["kernel"].state.evidence_ledger.to_projection().to_dict() == ledger_before
