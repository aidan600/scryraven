from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.query_production_runtime import (
    QueryStrategyConvergenceError,
    execute_query_production_action,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
    RunKernel,
)
from core.search_work_plan_shadow_runtime import (
    RuntimeShadowSearchWorkPlanInput,
    observe_runtime_shadow_search_work_plan_construction,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SHADOW_RUNTIME = ROOT / "core" / "search_work_plan_shadow_runtime.py"
ROUTE_PROJECTION = {
    "intent": "general",
    "report_type": "general_research",
    "query_type": "rule",
    "core_topic": "official filing fee",
    "primary_entity": "Form I-130",
}


class _Status:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, message: str) -> None:
        self.steps.append(message)


class _Logger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, Exception]] = []

    def warning(self, message: str, error: Exception) -> None:
        self.warnings.append((message, error))


def _clean_query(value: str) -> str:
    return " ".join(str(value or "").split())[:300]


def _router_state(query: str) -> Any:
    return build_router_query_preparation_state(
        query=query,
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "general_research",
                "query_type": "rule",
                "core_topic": "official filing fee",
                "primary_entity": "Form I-130",
                "entities": ["Form I-130"],
                "is_academic": False,
            }
        ),
    )


def _run_contract_projection() -> dict[str, Any]:
    query = "What is the current official filing fee for Form I-130?"
    kernel = RunKernel.start(run_id="ag96c8-contract", request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={"query_length": len(query)})
    result = execute_run_contract_synthesis_action(
        action,
        query=query,
        mode="Balanced",
        current_date="June 14, 2026",
        route_projection=ROUTE_PROJECTION,
    )
    kernel.reduce(result.observation)
    return dict(kernel.state.run_contract_projection)


def _query_production_result(
    kernel: RunKernel,
    *,
    run_contract_projection: dict[str, Any],
) -> Any:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return '{"queries":["current official filing fee","effective filing fee"]}'

    query = "What is the current official filing fee for Form I-130?"
    action = kernel.authorize_query_production(
        inputs={
            "strategy": "Balanced",
            "run_contract_id": run_contract_projection["contract_id"],
        }
    )
    return execute_query_production_action(
        action,
        router_query_preparation_contract=_router_state(query),
        query=query,
        strategy="Balanced",
        current_date="June 14, 2026",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        news_preferred_domains=["reuters.com"],
        ask_model=ask_model,
        clean_json_response=lambda text: text,
        default_system={
            "researcher": "researcher-system",
            "recon_query_rewriter": "recon-system",
        },
        fast_provider="fast-provider",
        fast_model="fast-model",
        local_url="http://local",
        api_key=None,
        use_reasoning=True,
        measure_context_stage=lambda *_args, **_kwargs: None,
        clean_query=_clean_query,
        cost_accumulator=object(),
        status=_Status(),
        provider_diagnostics=[],
        run_log=_Logger(),
        brave_api_key_available=False,
        run_contract_projection=run_contract_projection,
    )


def test_runtime_shadow_callsite_sequence_reduces_projection_after_contract() -> None:
    query = "What is the current official filing fee for Form I-130?"
    kernel = RunKernel.start(run_id="ag96c8-runtime", request_id="request")
    contract_action = kernel.authorize_run_contract_synthesis(
        inputs={"query_length": len(query)}
    )
    contract_result = execute_run_contract_synthesis_action(
        contract_action,
        query=query,
        mode="Balanced",
        current_date="June 14, 2026",
        route_projection=ROUTE_PROJECTION,
    )
    kernel.reduce(contract_result.observation)
    contract_projection = dict(kernel.state.run_contract_projection)

    action = kernel.authorize_search_work_plan_construction(
        inputs={"callsite": "pipeline_orchestrator.after_run_contract_synthesis"}
    )
    observation = observe_runtime_shadow_search_work_plan_construction(
        action,
        RuntimeShadowSearchWorkPlanInput(
            run_contract_projection=contract_projection,
            route_projection=ROUTE_PROJECTION,
            requested_mode="Balanced",
            selected_depth=contract_projection.get("selected_depth"),
            current_date_ref={"id": "current-date:test"},
        ),
    )
    state = kernel.reduce(observation)
    trace = kernel.to_trace_fragment()["run_kernel"]
    projection = state.search_work_plan_projection

    assert projection["owner"] == "RunKernel.SearchWorkPlan"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["runtime_consumed_by_query_plan"] is False
    assert projection["provider_search_behavior_changed"] is False
    assert projection["query_plan_behavior_changed"] is False
    assert trace["search_work_plan_projection"] == projection
    assert trace["projections"][SEARCH_WORK_PLAN_CONSTRUCTION_STAGE] == projection
    assert QUERY_PRODUCTION_STAGE not in state.stage_statuses
    assert QUERY_PLAN_ADMISSION_STAGE not in state.stage_statuses


def test_direct_legacy_query_production_fails_closed_with_or_without_shadow() -> None:
    contract_projection = _run_contract_projection()
    baseline_kernel = RunKernel.start(run_id="ag96c8-baseline", request_id="request")
    shadow_kernel = RunKernel.start(run_id="ag96c8-shadow", request_id="request")

    with pytest.raises(
        QueryStrategyConvergenceError,
        match="legacy initial producer fallback is retired",
    ):
        _query_production_result(
            baseline_kernel,
            run_contract_projection=contract_projection,
        )
    action = shadow_kernel.authorize_run_contract_synthesis(inputs={"fixture": True})
    shadow_kernel.reduce(
        contract_projection_observation := execute_run_contract_synthesis_action(
            action,
            query="What is the current official filing fee for Form I-130?",
            mode="Balanced",
            current_date="June 14, 2026",
            route_projection=ROUTE_PROJECTION,
        ).observation
    )
    shadow_contract_projection = dict(shadow_kernel.state.run_contract_projection)
    shadow_action = shadow_kernel.authorize_search_work_plan_construction()
    shadow_kernel.reduce(
        observe_runtime_shadow_search_work_plan_construction(
            shadow_action,
                RuntimeShadowSearchWorkPlanInput(
                    run_contract_projection=shadow_contract_projection,
                    route_projection=ROUTE_PROJECTION,
                requested_mode="Balanced",
                selected_depth=shadow_contract_projection.get("selected_depth"),
            ),
        )
    )
    with pytest.raises(
        QueryStrategyConvergenceError,
        match="legacy initial producer fallback is retired",
    ):
        _query_production_result(
            shadow_kernel,
            run_contract_projection=shadow_contract_projection,
        )

    assert contract_projection_observation.observation_type.value == "run_contract_synthesized"
    assert shadow_kernel.state.search_work_plan_projection["runtime_consumed_by_query_plan"] is False
    assert QUERY_PLAN_ADMISSION_STAGE not in shadow_kernel.state.stage_statuses


def test_sensitive_fields_are_not_serialized_by_runtime_shadow_helper() -> None:
    kernel = RunKernel.start(run_id="ag96c8-sensitive", request_id="request")
    contract = _run_contract_projection()
    action = kernel.authorize_run_contract_synthesis(inputs={"fixture": True})
    kernel.reduce(
        execute_run_contract_synthesis_action(
            action,
            query="What is the current official filing fee for Form I-130?",
            mode="Balanced",
            current_date="June 14, 2026",
            route_projection={"query_type": "rule"},
        ).observation
    )
    shadow_action = kernel.authorize_search_work_plan_construction()
    kernel.reduce(
        observe_runtime_shadow_search_work_plan_construction(
            shadow_action,
            RuntimeShadowSearchWorkPlanInput(
                run_contract_projection={
                    **contract,
                    "raw_prompt": "RAW_PROMPT_SENTINEL",
                    "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
                    "raw_model_response": "RAW_MODEL_SENTINEL",
                },
                route_projection={
                    "query_type": "rule",
                    "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
                    "token": "TOKEN_SENTINEL",
                },
                requested_mode="Balanced",
                metadata={
                    "db_row": "DB_ROW_SENTINEL",
                    "full_trace": "TRACE_SENTINEL",
                    "safe_note": "visible-safe-note",
                },
            ),
        )
    )
    encoded = json.dumps(kernel.to_trace_fragment(), sort_keys=True)

    for field_name in (
        "raw_prompt",
        "raw_provider_payload",
        "raw_model_response",
        "secret",
        "token",
        "db_row",
        "full_trace",
    ):
        assert field_name not in encoded
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "TRACE_SENTINEL",
    ):
        assert sentinel not in encoded
    assert "visible-safe-note" in encoded


def test_pipeline_retires_shadow_callsite_before_converged_planning() -> None:
    source = PIPELINE.read_text(encoding="utf-8")

    contract_reduce = source.index("run_kernel.reduce(run_contract_result.observation)")
    convergence_call = source.index(
        "convergence = execute_initial_query_strategy_convergence(",
        contract_reduce,
    )

    assert contract_reduce < convergence_call
    assert "run_search_work_shadow_lane" not in source
    assert "RuntimeShadowSearchWorkPlanInput" not in source
    assert "observe_runtime_shadow_search_work_plan_construction" not in source
    assert "SearchWorkPlanConstructionInput" not in source
    assert "QueryShapeAssessment" not in source
    assert "ContractResolutionRecord" not in source
    assert "ComponentCandidate" not in source
    assert "ProviderJobCandidate" not in source
    assert "SourceObligationCandidate" not in source
    assert "construct_search_work_plan_from_records" not in source
    assert "observe_search_work_plan_construction" not in source


def test_query_plan_provider_prompt_modules_do_not_import_runtime_shadow_helper() -> None:
    forbidden_modules = {
        "core.search_work_plan_shadow_runtime",
        "search_work_plan_shadow_runtime",
    }
    paths = (
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
    )

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        assert imported_names.isdisjoint(forbidden_modules), path


def test_runtime_shadow_helper_keeps_closed_surface_boundary() -> None:
    source = SHADOW_RUNTIME.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
        "core.query_production_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.runtime_prompt_assembly",
        "core.prompts",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "fetch_page",
        "process_search_queries",
    }
    imported_names: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(forbidden_calls)
