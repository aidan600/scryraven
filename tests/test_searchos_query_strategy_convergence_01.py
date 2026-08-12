from __future__ import annotations

import inspect
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    INITIAL_QUERY_ALLOCATION_POLICY_VERSION,
)
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import (
    QUERY_PRODUCTION_STAGE,
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
    query_plan_admission_inputs_from_query_production_projection,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_planner_runtime import SEARCH_PLANNER_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
QUERY_RUNTIME = ROOT / "core" / "query_production_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


class ResponseOnlyPlannerAdapter:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = deepcopy(dict(response))
        self.calls: list[dict[str, Any]] = []

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(planner_input)))
        return deepcopy(self.response)


def _planner_payload(
    *,
    component_count: int = 1,
    secondary: bool = False,
    duplicate_secondary: bool = False,
    immediate_secondary: bool = False,
    recon: str = "not_needed",
    required_recon: bool = False,
    planner_provider_name: str | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    for index in range(1, component_count + 1):
        component_id = f"component:{index}"
        general_id = f"obligation:{index}:general"
        official_id = f"obligation:{index}:official"
        source_ids = [general_id]
        obligations.append(
            {
                "candidate_id": general_id,
                "obligation_kind": "no_special_obligation",
                "component_candidate_ids": [component_id],
                "strictness": "required",
            }
        )
        if secondary and index == 1:
            source_ids.append(official_id)
            obligations.append(
                {
                    "candidate_id": official_id,
                    "obligation_kind": "official_current",
                    "component_candidate_ids": [component_id],
                    "strictness": "required",
                }
            )
        components.append(
            {
                "component_id": component_id,
                "component_revision": "1",
                "user_facing_label": f"Required component {index}",
                "user_facing_question": f"What is required component {index}?",
                "requirement_posture": "required",
                "acceptance_criteria": ["Direct source support."],
                "semantic_slot_ids": ["slot:subject"],
                "source_obligation_candidate_ids": source_ids,
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "materiality": "material",
            }
        )
        primary_query = f"Example required component {index} primary source"
        primary: dict[str, Any] = {
            "strategy_id": f"strategy:{index}:primary",
            "component_id": component_id,
            "candidate_kind": "primary",
            "candidate_query_text": primary_query,
            "requested_role": "initial",
            "source_obligation_candidate_ids": [general_id],
        }
        if planner_provider_name:
            primary["provider_name"] = planner_provider_name
        if recon != "not_needed" and index == 1:
            primary["recon_requirement"] = {
                "posture": recon,
                "unresolved_dimension_ids": ["dim:entity-identity"],
                "candidate_queries": [
                    {
                        "dimension_id": "dim:entity-identity",
                        "candidate_query_text": "Old Example New Example identity",
                        "query_kind": "disambiguation_probe",
                    }
                ],
                "required_for_truthful_targeting": required_recon,
            }
        strategies = [primary]
        if secondary and index == 1:
            strategies.append(
                {
                    "strategy_id": "strategy:1:secondary",
                    "component_id": component_id,
                    "candidate_kind": "secondary",
                    "candidate_query_text": (
                        primary_query if duplicate_secondary else "Example component 1 official current rule"
                    ),
                    "requested_role": "official_bias",
                    "source_obligation_candidate_ids": [official_id],
                    "official_canonical_intent": "official_source",
                    "document_family": "official current rule",
                    "distinct_need_justification": ("A separate accepted official-current obligation."),
                    "immediate_dispatch_requested": immediate_secondary,
                    "immediate_dispatch_distinct_need": immediate_secondary,
                }
            )
        requirements.append(
            {
                "component_id": component_id,
                "requirement_id": f"requirement:{index}:initial",
                "requirement_summary": f"Find component {index} support.",
                "source_obligation_candidate_ids": source_ids,
                "metadata": {
                    "query_strategy_candidates": strategies,
                    "provider_name_neutral": True,
                },
            }
        )
    return {
        "question_meaning_summary": "Answer every accepted required component.",
        "requested_output": "A source-bound multi-component answer.",
        "semantic_slots": [
            {
                "slot_id": "slot:subject",
                "slot_kind": "entity",
                "status": "explicit",
                "candidate_values": ["Example"],
                "selected_value": "Example",
                "materiality": "material",
            }
        ],
        "answer_components": components,
        "source_obligation_candidates": obligations,
        "component_search_requirements": requirements,
        "material_ambiguity_posture": ("material_ambiguity_present" if recon != "not_needed" else "none"),
        "mandatory_caveats": [],
        "prohibited_upgrades": ["Scout hints are not evidence."],
        "normalization_obligations": [],
        "assumptions": [],
        "unsupported_outputs": [],
    }


def _kernel_after_run_contract() -> RunKernel:
    kernel = RunKernel.start(run_id="run:searchos", request_id="request:searchos")
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": {
                    "contract_id": "run-contract:searchos",
                    "schema_version": "run_contract_fixture_v1",
                    "synthesis_mode": "offline_fixture",
                    "selected_depth": "balanced",
                    "source_requirements": [],
                },
                "validation": {"ok": True, "status": "ok"},
            },
        )
    )
    return kernel


def _router_state() -> Any:
    return build_router_query_preparation_state(
        query="Compare every required Example component.",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "comparison",
                "query_type": "comparison",
                "core_topic": "Example components",
                "primary_entity": "Example",
                "entities": ["Example"],
                "is_academic": False,
            }
        ),
    )


def _converge(
    payload: Mapping[str, Any],
    *,
    run_kernel: RunKernel | None = None,
    policy=DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
):
    kernel = run_kernel if run_kernel is not None else _kernel_after_run_contract()
    result = execute_initial_query_strategy_convergence(
        run_kernel=kernel,
        router_query_preparation_contract=_router_state(),
        query="Compare every required Example component.",
        strategy="Balanced",
        current_date="2026-07-19",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        exclude_domains=[],
        news_preferred_domains=[],
        route_projection={"route_id": "route:searchos"},
        run_contract_projection=kernel.state.run_contract_projection,
        planner_adapter=ResponseOnlyPlannerAdapter(payload),
        provider_diagnostics=[],
        initial_query_allocation_policy=policy,
    )
    return kernel, result


def _admit(kernel: RunKernel, convergence):
    inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
    )
    adapter = build_query_plan_runtime_adapter(
        run_id=kernel.state.run_id,
        primary_entity="Example",
        entities_list=["Example"],
        core_topic="Example components",
        user_query="Compare every required Example component.",
        intent="general",
        clean=lambda value: " ".join(value.split()),
    )
    action = kernel.authorize_query_plan_admission(inputs={"candidate_count": len(inputs.candidate_queries)})
    result = execute_query_plan_admission_action(
        action,
        query_authority=adapter,
        router_query_preparation_contract=_router_state(),
        candidate_queries=inputs.candidate_queries,
        candidate_strategies=inputs.candidate_strategies,
        candidate_source=inputs.candidate_source,
        query_type=inputs.query_type,
        current_date="2026-07-19",
        max_queries=inputs.max_queries,
        route_runtime_posture=inputs.effective_route_posture,
        search_work_projection=convergence.search_work_plan,
        accepted_contract=(
            kernel.state.current_answer_contract
            or kernel.state.initial_answer_contract
        ),
        initial_query_allocation_policy=inputs.initial_query_allocation_policy,
    )
    kernel.reduce(result.observation)
    return adapter, result


def test_five_required_components_reach_first_wave_without_global_truncation() -> None:
    kernel, convergence = _converge(_planner_payload(component_count=5))
    adapter, admission = _admit(kernel, convergence)

    assert len(kernel.state.initial_answer_contract["accepted_answer_component_refs"]) == 5
    assert len(convergence.query_production_result.candidate_queries) == 5
    assert len(admission.current_queries) == 5
    assert len(set(admission.current_queries)) == 5
    assert admission.observation.payload["small_global_initial_query_cap_applied"] is False
    assert admission.observation.payload["required_component_globally_truncated"] is False
    assert admission.router_query_preparation_contract.retrieval_budget_seed_facts["max_queries"] == 2
    adapter.admit_execution_queries(
        admission.current_queries,
        iteration=1,
        recovery_active=False,
    )
    ordered = [
        item for item in adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]["items"] if item.get("status") == "ordered"
    ]
    assert [item["authorized_query"] for item in ordered] == admission.current_queries
    assert [item["order"] for item in ordered] == [1, 2, 3, 4, 5]
    assert {item["iteration"] for item in ordered} == {1}
    assert all(item["metadata"]["accepted_component_ref"] for item in ordered)


def test_search_work_plan_carries_refs_but_never_complete_query_text() -> None:
    kernel, convergence = _converge(_planner_payload(component_count=2))
    plan = convergence.search_work_plan
    serialized = json.dumps(plan, sort_keys=True)

    assert plan["passive"] is False
    assert plan["runtime_consumed"] is True
    assert len(plan["components"]) == 2
    assert all(item["metadata"]["accepted_component_ref"] for item in plan["components"])
    assert all(item["metadata"]["search_requirement_refs"] for item in plan["components"])
    for query in convergence.query_production_result.candidate_queries:
        assert query not in serialized
    assert "candidate_query_text" not in serialized
    assert kernel.state.search_work_plan == plan


def test_second_primary_cannot_bypass_distinct_need_requirement() -> None:
    payload = _planner_payload()
    strategies = payload["component_search_requirements"][0]["metadata"]["query_strategy_candidates"]
    strategies.append(
        {
            "strategy_id": "strategy:1:extra-primary",
            "component_id": "component:1",
            "candidate_kind": "primary",
            "candidate_query_text": "Example component 1 separate broad search",
            "requested_role": "initial",
            "source_obligation_candidate_ids": ["obligation:1:general"],
        }
    )

    kernel, convergence = _converge(payload)
    _, admission = _admit(kernel, convergence)

    assert admission.current_queries == ["Example required component 1 primary source"]
    assert len(admission.initial_query_admission.unjustified_secondary_candidates_rejected) == 1


def test_policy_is_versioned_tunable_and_not_a_schema_contract() -> None:
    policy = DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY
    tuned = policy.with_tuning(
        initial_candidate_ceiling_per_required_component=3,
        recon_candidate_ceiling_per_affected_component=4,
    )

    assert policy.policy_version == INITIAL_QUERY_ALLOCATION_POLICY_VERSION
    assert policy.primary_query_target_per_required_component == 1
    assert policy.initial_candidate_ceiling_per_required_component == 2
    assert policy.immediate_dispatch_target_per_required_component == 1
    assert policy.recon_candidate_ceiling_per_affected_component == 5
    assert tuned.policy_version == policy.policy_version
    assert tuned.initial_candidate_ceiling_per_required_component == 3
    assert SEARCH_PLANNER_SCHEMA_VERSION not in tuned.to_dict().values()
    with pytest.raises(ValueError, match="positive integer"):
        policy.with_tuning(initial_candidate_ceiling_per_required_component=2.5)


def test_model_authored_recon_metadata_is_not_an_ordinary_controller() -> None:
    payload = _planner_payload(recon="optional")
    recon = payload["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0]["recon_requirement"]
    recon["unresolved_dimension_ids"] = [f"dim:need-{index}" for index in range(6)]
    recon["candidate_queries"] = [
        {
            "dimension_id": dimension_id,
            "candidate_query_text": f"Example clarification {dimension_id}",
            "query_kind": "disambiguation_probe",
        }
        for dimension_id in recon["unresolved_dimension_ids"]
    ]

    kernel, convergence = _converge(payload)

    assert convergence.query_production_result.candidate_queries == [
        "Example required component 1 primary source"
    ]
    assert convergence.recon_summary == ()
    assert convergence.revision_projections == ()
    assert kernel.state.scout_disambiguation_report_history == []
    assert kernel.state.search_planner_revision_history == []


def test_planner_provider_identity_is_ignored_before_queryplan() -> None:
    kernel, convergence = _converge(_planner_payload(planner_provider_name="untrusted-provider"))
    strategy = convergence.query_production_result.candidate_strategies[0]
    _, admission = _admit(kernel, convergence)

    assert "provider_name" not in strategy
    assert strategy["planner_provider_identity_ignored"] is True
    assert admission.current_queries == ["Example required component 1 primary source"]
    assert (
        admission.observation.payload["provider_job_execution_handoff"]["behavior_boundary_flags"]["provider_selected"]
        is False
    )


def test_ordinary_convergence_has_no_legacy_adapter_injection_surface() -> None:
    parameters = inspect.signature(
        execute_initial_query_strategy_convergence
    ).parameters
    runtime_source = QUERY_RUNTIME.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    assert "scout_adapter" not in parameters
    assert "revision_adapter" not in parameters
    assert "from core.scout_disambiguation_runtime import" not in runtime_source
    assert "from core.search_planner_revision_runtime import" not in runtime_source
    assert "def _execute_recon_and_revisions" not in runtime_source
    assert "def _admit_and_apply_revision_amendment" not in runtime_source
    assert "build_ordinary_scout_disambiguation_adapter" not in pipeline_source
    assert "SearchPlannerRevisionModelAdapter" not in pipeline_source


def test_required_recon_metadata_cannot_reach_retired_authorities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel_after_run_contract()

    def reject_old_authority(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("retired initial-planning authority was reached")

    for method_name in (
        "authorize_scout_disambiguation",
        "authorize_search_planner_revision",
        "authorize_contract_amendment_admission",
        "authorize_contract_amendment_application",
    ):
        monkeypatch.setattr(RunKernel, method_name, reject_old_authority)

    _, convergence = _converge(
        _planner_payload(recon="required", required_recon=True),
        run_kernel=kernel,
    )

    assert convergence.recon_summary == ()
    assert convergence.revision_projections == ()
    issued_action_types = {
        action.action_type.value
        for action in kernel.state.issued_actions.values()
    }
    assert issued_action_types.isdisjoint(
        {
            "scout_disambiguate",
            "search_planner_revise",
            "contract_amendment_admit",
            "contract_amendment_apply",
        }
    )
    assert kernel.state.scout_disambiguation_report_history == []
    assert kernel.state.search_planner_revision_history == []
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_application_history == []


def test_malformed_planner_has_no_dispatch_and_no_legacy_fallback() -> None:
    kernel = _kernel_after_run_contract()

    with pytest.raises(ValueError):
        execute_initial_query_strategy_convergence(
            run_kernel=kernel,
            router_query_preparation_contract=_router_state(),
            query="Compare every required Example component.",
            strategy="Balanced",
            current_date="2026-07-19",
            focus_academic=False,
            force_intent_news=False,
            include_domains=[],
            exclude_domains=[],
            news_preferred_domains=[],
            route_projection={},
            run_contract_projection=kernel.state.run_contract_projection,
            planner_adapter=ResponseOnlyPlannerAdapter({}),
            provider_diagnostics=[],
        )

    assert QUERY_PRODUCTION_STAGE not in kernel.state.projections
    runtime_source = QUERY_RUNTIME.read_text(encoding="utf-8")
    assert "def _build_researcher_prompt" not in runtime_source
    assert "def _build_recon_rewriter_prompt" not in runtime_source
    assert "brave_reconnaissance_func" not in runtime_source
    assert "core_topic[:300]" not in runtime_source


def test_ordinary_pipeline_consumes_convergence_before_queryplan_and_discover() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    convergence_index = source.index("execute_initial_query_strategy_convergence(")
    admission_index = source.index("execute_query_plan_admission_action(")
    execution_index = source.index("current_queries = query_authority.admit_execution_queries")

    assert convergence_index < admission_index < execution_index
    assert "run_search_work_shadow_lane(" not in source
    assert "execute_query_production_action(" not in source
    assert "search_work_projection=run_kernel.state.search_work_plan" in source
