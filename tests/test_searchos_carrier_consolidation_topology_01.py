"""Durable ordinary-path topology after SearchWorkPlan/QueryProduction retirement."""

from __future__ import annotations

import ast
import inspect
from dataclasses import fields
from pathlib import Path

from core.query_plan import QueryPlan, QueryPlanRole, QueryPlanStatus
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.query_production_runtime import (
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
)
from core.run_config import RunDeps
from core.run_kernel import ActionType, KernelTraceProjection, ObservationType, RunKernel, RunState

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PIPELINE = CORE / "pipeline_orchestrator.py"
QUERY_RUNTIME = CORE / "query_production_runtime.py"
QUERY_PLAN = CORE / "query_plan.py"
QUERY_PLAN_ADAPTER = CORE / "query_plan_runtime_adapter.py"
RUN_KERNEL = CORE / "run_kernel.py"
PRODUCER = CORE / "ordinary_semantic_producer_runtime.py"
MULTICOMPONENT = CORE / "ordinary_multicomponent_synthesis_runtime.py"

_DELETED_PRODUCTION_MODULES = (
    "core.search_work_plan",
    "core.search_work_plan_construction",
    "core.search_work_plan_query_plan_shadow",
    "core.search_work_plan_shadow_runtime",
    "core.search_work_shadow_lane_runtime",
    "core.scout_disambiguation_runtime",
    "core.ordinary_scout_disambiguation_adapter",
    "core.search_planner_revision_runtime",
    "core.search_planner_revision_model_adapter",
    "core.search_planner_revision_model_prompt",
    "core.search_planner_revision_model_output_contract",
    "core.scout",
    "core.search_work_official_current_handoff",
    "core.search_work_official_current_recovery_bridge",
    "core.search_work_official_current_recovery_activation",
)

_DELETED_PRODUCTION_FILES = (
    CORE / "search_work_plan.py",
    CORE / "search_work_plan_construction.py",
    CORE / "search_work_plan_query_plan_shadow.py",
    CORE / "search_work_plan_shadow_runtime.py",
    CORE / "search_work_shadow_lane_runtime.py",
    CORE / "scout_disambiguation_runtime.py",
    CORE / "ordinary_scout_disambiguation_adapter.py",
    CORE / "search_planner_revision_runtime.py",
    CORE / "search_planner_revision_model_adapter.py",
    CORE / "search_planner_revision_model_prompt.py",
    CORE / "search_planner_revision_model_output_contract.py",
    CORE / "scout.py",
    CORE / "search_work_official_current_handoff.py",
    CORE / "search_work_official_current_recovery_bridge.py",
    CORE / "search_work_official_current_recovery_activation.py",
)

_ORDINARY_COMPOSITION_FILES = (
    PIPELINE,
    QUERY_RUNTIME,
    QUERY_PLAN,
    QUERY_PLAN_ADAPTER,
    RUN_KERNEL,
    PRODUCER,
    MULTICOMPONENT,
)

_FORBIDDEN_ACTION_VALUES = {
    "scout_disambiguate",
    "search_planner_revise",
    "search_work_plan_construct",
    "query_production",
}
_FORBIDDEN_OBSERVATION_VALUES = {
    "scout_disambiguation_reported",
    "search_planner_revised",
    "search_work_plan_constructed",
    "query_candidates_produced",
}
_FORBIDDEN_AUTHORIZE_METHODS = {
    "authorize_scout_disambiguation",
    "authorize_search_planner_revision",
    "authorize_search_work_plan_construction",
    "authorize_query_production",
}
_FORBIDDEN_CALL_NAMES = {
    "execute_query_production_action",
    "query_plan_admission_inputs_from_query_production_projection",
    "build_search_work_plan",
    "construct_search_work_plan",
    "consume_search_work_for_existing_queries",
    "allocate_existing_queries_by_search_work",
    "initial_strategy_search_work_bindings",
    "build_ordinary_scout_disambiguation_adapter",
    "build_search_work_official_current_handoff",
    "activate_search_work_official_current_recovery_recommendation",
    "run_scout",
    "should_skip_quant_scout",
    "admit_recon_candidates",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(_source(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(_source(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _function_arg_names(fn: object) -> set[str]:
    return set(inspect.signature(fn).parameters)


def test_deleted_carrier_modules_are_physically_absent() -> None:
    for path in _DELETED_PRODUCTION_FILES:
        assert not path.exists(), path


def test_ordinary_composition_does_not_import_deleted_carriers() -> None:
    for path in _ORDINARY_COMPOSITION_FILES:
        imported = _imported_modules(path)
        assert imported.isdisjoint(_DELETED_PRODUCTION_MODULES), (path, imported)


def test_ordinary_composition_does_not_call_retired_carrier_constructors() -> None:
    for path in _ORDINARY_COMPOSITION_FILES:
        called = _called_names(path)
        assert called.isdisjoint(_FORBIDDEN_CALL_NAMES), (path, called)


def test_pipeline_composes_answer_contract_then_query_plan() -> None:
    pipeline_source = _source(PIPELINE)
    runtime_source = _source(QUERY_RUNTIME)
    assert "execute_initial_query_strategy_convergence(" in pipeline_source
    assert "execute_query_plan_admission_action(" in pipeline_source
    assert "convergence.candidate_queries" in pipeline_source
    assert "convergence.candidate_strategies" in pipeline_source
    assert "query_production_result" not in pipeline_source
    assert "search_work_plan=" not in pipeline_source
    assert "QUERY_PRODUCTION_STAGE" not in pipeline_source
    assert "QUERY_PRODUCTION_STAGE" not in runtime_source
    assert "class QueryProductionResult" not in runtime_source
    assert "def execute_query_production_action" not in runtime_source
    assert "query_plan_admission_inputs_from_query_production_projection" not in (
        runtime_source
    )


def test_query_plan_admits_from_accepted_contract_not_search_work_plan() -> None:
    parameters = _function_arg_names(QueryPlan.admit_initial_component_strategies)
    assert "accepted_contract" in parameters
    assert "search_work_projection" not in parameters
    assert "search_work_plan" not in parameters
    admission_parameters = _function_arg_names(execute_query_plan_admission_action)
    assert "accepted_contract" in admission_parameters
    assert "candidate_strategies" in admission_parameters
    assert "search_work_projection" not in admission_parameters
    assert "query_production_projection" not in admission_parameters
    convergence_parameters = _function_arg_names(
        execute_initial_query_strategy_convergence
    )
    assert "scout_adapter" not in convergence_parameters
    assert "revision_adapter" not in convergence_parameters


def test_run_kernel_has_no_retired_carrier_actions_or_authorizers() -> None:
    action_values = {member.value for member in ActionType}
    observation_values = {member.value for member in ObservationType}
    assert action_values.isdisjoint(_FORBIDDEN_ACTION_VALUES)
    assert observation_values.isdisjoint(_FORBIDDEN_OBSERVATION_VALUES)
    for method_name in _FORBIDDEN_AUTHORIZE_METHODS:
        assert not hasattr(RunKernel, method_name)
    kernel_source = _source(RUN_KERNEL)
    assert "SEARCH_WORK_PLAN_CONSTRUCTION_STAGE" not in kernel_source
    assert "QUERY_PRODUCTION_STAGE" not in kernel_source
    assert "SCOUT_DISAMBIGUATION_STAGE" not in kernel_source
    assert "SEARCH_PLANNER_REVISION_STAGE" not in kernel_source


def test_ordinary_producer_does_not_require_search_work_plan() -> None:
    producer_source = _source(PRODUCER)
    assert "SKIP_REASON_SEARCH_WORK_PLAN_MISSING" not in producer_source
    assert "accepted_answer_contract_missing" in producer_source
    assert "run_kernel.state.search_work_plan" not in producer_source
    multicomponent_source = _source(MULTICOMPONENT)
    assert "build_question_meaning_record_from_search_work_plan(" not in (
        multicomponent_source
    )
    assert "run_kernel.state.search_work_plan" not in multicomponent_source


def test_rundeps_has_no_retired_scout_or_plannerrevision_injection_fields() -> None:
    names = {item.name for item in fields(RunDeps)}
    assert "run_scout" not in names
    assert "should_skip_quant_scout" not in names
    assert "scout_disambiguation_adapter" not in names
    assert "search_planner_revision_adapter" not in names
    assert "search_planner_adapter" in names


def test_runkernel_has_no_retired_scout_revision_or_searchworkplan_canonical_state() -> None:
    state_names = {item.name for item in fields(RunState)}
    trace_names = {item.name for item in fields(KernelTraceProjection)}
    retired = {
        "scout_disambiguation_report_state",
        "scout_disambiguation_report_projection",
        "scout_disambiguation_report_history",
        "search_planner_revision_state",
        "search_planner_revision_projection",
        "search_planner_revision_history",
        "search_work_plan",
        "search_work_plan_projection",
        "search_work_plan_validation",
    }
    assert state_names.isdisjoint(retired)
    assert trace_names.isdisjoint(retired)


def test_search_executor_accepts_no_impossible_scout_revision_ancestry() -> None:
    parameters = _function_arg_names(RunKernel.authorize_search_executor_handoff)
    assert "scout_direction_hint_ids" not in parameters
    assert "parent_search_planner_revision_id" not in parameters
    kernel_source = _source(RUN_KERNEL)
    assert "revision_ref_from_revision_state" not in kernel_source
    assert "scout_ref_from_scout_report_state" not in kernel_source
    handoff_source = _source(CORE / "search_executor_handoff_runtime.py")
    assert "def revision_ref_from_revision_state" not in handoff_source
    assert "def scout_ref_from_scout_report_state" not in handoff_source


def test_query_plan_has_no_dead_recon_rewrite_vocabulary() -> None:
    assert not hasattr(QueryPlanStatus, "OBSERVED_RECON_REWRITE")
    assert not hasattr(QueryPlanRole, "RECON_REWRITE")
    assert not hasattr(QueryPlanRuntimeAdapter, "admit_recon_candidates")
    role_values = {member.value for member in QueryPlanRole}
    status_values = {member.value for member in QueryPlanStatus}
    assert "recon_rewrite" not in role_values
    assert "observed_recon_rewrite" not in status_values
