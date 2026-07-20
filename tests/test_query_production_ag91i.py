from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import (
    QueryStrategyConvergenceError,
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
    execute_query_production_action,
    query_plan_admission_inputs_from_query_production_projection,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
)
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_planner_runtime import DeterministicSearchPlannerAdapter

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
QUERY_RUNTIME = ROOT / "core" / "query_production_runtime.py"


def _router_state():
    return build_router_query_preparation_state(
        query="Compare Acme deployment and support.",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "comparison",
                "query_type": "comparison",
                "core_topic": "Acme deployment and support",
                "primary_entity": "Acme",
                "entities": ["Acme"],
                "is_academic": False,
            }
        ),
    )


def _kernel_after_contract() -> RunKernel:
    kernel = RunKernel.start(run_id="run-ag91i", request_id="request-ag91i")
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": {
                    "contract_id": "contract:ag91i",
                    "schema_version": "fixture-v1",
                    "synthesis_mode": "fixture",
                    "selected_depth": "balanced",
                    "source_requirements": [],
                },
                "validation": {"ok": True, "status": "ok"},
            },
        )
    )
    return kernel


def _convergence():
    kernel = _kernel_after_contract()
    result = execute_initial_query_strategy_convergence(
        run_kernel=kernel,
        router_query_preparation_contract=_router_state(),
        query="Compare Acme deployment and support.",
        strategy="Balanced",
        current_date="2026-07-19",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        exclude_domains=[],
        news_preferred_domains=[],
        route_projection={"route_id": "route:ag91i"},
        run_contract_projection=kernel.state.run_contract_projection,
        planner_adapter=DeterministicSearchPlannerAdapter(),
        provider_diagnostics=[],
    )
    return kernel, result


def test_run_kernel_emits_query_production_authorized_action() -> None:
    kernel = RunKernel.start(run_id="run-action", request_id="request-action")
    action = kernel.authorize_query_production(inputs={"planner_ref": "planner-1"})

    assert action.action_type is ActionType.QUERY_PRODUCTION
    assert action.stage == QUERY_PRODUCTION_STAGE
    assert action.expected_observation_type is ObservationType.QUERY_CANDIDATES_PRODUCED
    assert action.inputs["planner_ref"] == "planner-1"


def test_missing_converged_strategies_fail_without_legacy_fallback() -> None:
    kernel = RunKernel.start(run_id="run-fail", request_id="request-fail")
    action = kernel.authorize_query_production()

    with pytest.raises(QueryStrategyConvergenceError, match="legacy.*fallback is retired"):
        execute_query_production_action(
            action,
            router_query_preparation_contract=_router_state(),
            query="Compare Acme deployment and support.",
            strategy="Balanced",
            current_date="2026-07-19",
            focus_academic=False,
            force_intent_news=False,
            include_domains=[],
            news_preferred_domains=[],
            provider_diagnostics=[],
        )

    assert kernel.state.projections.get(QUERY_PRODUCTION_STAGE) is None


def test_converged_production_reduces_planner_strategies_and_retirement_flags() -> None:
    kernel, convergence = _convergence()
    result = convergence.query_production_result
    projection = kernel.state.projections[QUERY_PRODUCTION_STAGE]

    assert result.candidate_source == "search_planner"
    assert result.candidate_queries
    assert projection["candidate_query_projection"] == result.candidate_queries
    assert projection["candidate_strategy_projection"] == result.candidate_strategies
    assert projection["initial_query_allocation_policy"][
        "primary_query_target_per_required_component"
    ] == 1
    assert projection["diagnostics"]["small_global_initial_query_cap_applied"] is False
    assert all(
        value is False
        for value in projection["legacy_initial_producer_execution"].values()
    )
    assert projection["researcher_fallback_status"] == "retired_not_reachable"


def test_queryplan_admission_consumes_only_reduced_exact_strategy_projection() -> None:
    kernel, convergence = _convergence()
    inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
    )
    adapter = build_query_plan_runtime_adapter(
        run_id=kernel.state.run_id,
        primary_entity="Acme",
        entities_list=["Acme"],
        core_topic="Acme deployment and support",
        user_query="Compare Acme deployment and support.",
        intent="general",
        clean=lambda value: " ".join(value.split()),
    )
    action = kernel.authorize_query_plan_admission(
        inputs={"candidate_count": len(inputs.candidate_queries)}
    )
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
        initial_query_allocation_policy=inputs.initial_query_allocation_policy,
    )
    kernel.reduce(result.observation)

    assert result.current_queries == inputs.candidate_queries
    assert result.observation.payload["query_order_owner"] == "QueryPlan"
    assert result.observation.payload["post_result_followup_dispatched"] is False
    assert kernel.state.projections[QUERY_PLAN_ADMISSION_STAGE]
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    finalized = [item for item in trace["items"] if item.get("status") == "finalized"]
    assert len(finalized) == len(result.current_queries)
    assert all(item["metadata"]["search_work_plan_ref"] for item in finalized)


def test_queryplan_rejects_projection_strategy_text_mismatch() -> None:
    kernel, convergence = _convergence()
    inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
    )
    action = kernel.authorize_query_plan_admission()
    adapter = build_query_plan_runtime_adapter(
        run_id="mismatch",
        primary_entity="Acme",
        entities_list=["Acme"],
        core_topic="Acme",
        user_query="Acme",
        intent="general",
        clean=lambda value: value,
    )

    with pytest.raises(ValueError, match="exact SearchPlanner strategy/query order"):
        execute_query_plan_admission_action(
            action,
            query_authority=adapter,
            router_query_preparation_contract=_router_state(),
            candidate_queries=["tampered query"],
            candidate_strategies=inputs.candidate_strategies,
            candidate_source=inputs.candidate_source,
            query_type=inputs.query_type,
            current_date="2026-07-19",
            max_queries=inputs.max_queries,
            route_runtime_posture=inputs.effective_route_posture,
            search_work_projection=convergence.search_work_plan,
            initial_query_allocation_policy=inputs.initial_query_allocation_policy,
        )


def test_static_ordinary_chain_has_no_reachable_legacy_initial_producers() -> None:
    runtime_source = QUERY_RUNTIME.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    for token in (
        "def _build_researcher_prompt",
        "def _build_recon_rewriter_prompt",
        "brave_reconnaissance_func",
        "candidate_source = \"researcher\"",
        "candidate_source = \"fallback\"",
        "core_topic[:300]",
    ):
        assert token not in runtime_source
    assert "execute_initial_query_strategy_convergence(" in pipeline_source
    assert "execute_query_production_action(" not in pipeline_source
    assert "run_search_work_shadow_lane(" not in pipeline_source
