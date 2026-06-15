from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

from core.query_production_runtime import execute_query_production_action
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    RunKernel,
)
from core.search_work_shadow_lane_runtime import (
    SEARCH_WORK_SHADOW_LANE_TRACE_KEY,
    run_search_work_shadow_lane,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SHADOW_LANE = ROOT / "core" / "search_work_shadow_lane_runtime.py"
ROUTE_PROJECTION = {
    "intent": "general",
    "report_type": "general_research",
    "query_type": "rule",
    "core_topic": "official filing fee",
    "primary_entity": "Form I-130",
}


class _Status:
    def step(self, _message: str) -> None:
        return None


class _Logger:
    def warning(self, _message: str, _error: Exception) -> None:
        return None


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


def _kernel_with_contract(run_id: str) -> tuple[RunKernel, dict[str, Any]]:
    query = "What is the current official filing fee for Form I-130?"
    kernel = RunKernel.start(run_id=run_id, request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={"query_length": len(query)})
    result = execute_run_contract_synthesis_action(
        action,
        query=query,
        mode="Balanced",
        current_date="June 14, 2026",
        route_projection=ROUTE_PROJECTION,
    )
    kernel.reduce(result.observation)
    return kernel, dict(kernel.state.run_contract_projection)


def _run_lane(
    kernel: RunKernel,
    contract_projection: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return run_search_work_shadow_lane(
        run_kernel=kernel,
        run_contract_projection=contract_projection,
        route_projection=ROUTE_PROJECTION,
        requested_mode="Balanced",
        selected_depth=contract_projection.get("selected_depth"),
        current_date_ref={"id": "current-date:test"},
        safe_user_domain_hints={},
        metadata={"callsite": "unit-test", **dict(metadata or {})},
    )


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


def test_lane_constructs_searchwork_and_queryplan_work_projection() -> None:
    kernel, contract_projection = _kernel_with_contract("ag96c10-lane")

    lane = _run_lane(kernel, contract_projection)
    query_plan_projection = lane["query_plan_work_shadow_projection"]

    assert lane["shadow_lane_ran"] is True
    assert lane["search_work_plan_projection_present"] is True
    assert lane["query_plan_work_shadow_projection_present"] is True
    assert kernel.state.search_work_plan
    assert kernel.state.search_work_plan_projection["owner"] == "RunKernel.SearchWorkPlan"
    assert kernel.state.projections[SEARCH_WORK_SHADOW_LANE_TRACE_KEY] == lane
    assert query_plan_projection["owner"] == "SearchWorkPlan.QueryPlanWorkShadowAdapter"
    assert query_plan_projection["derived_from"] == "RunKernel.SearchWorkPlan"
    assert query_plan_projection["work_counts"]["component_count"] >= 1
    assert QUERY_PRODUCTION_STAGE not in kernel.state.stage_statuses
    assert QUERY_PLAN_ADMISSION_STAGE not in kernel.state.stage_statuses


def test_lane_preserves_query_production_output() -> None:
    baseline_kernel, baseline_contract = _kernel_with_contract("ag96c10-baseline")
    shadow_kernel, shadow_contract = _kernel_with_contract("ag96c10-shadow")

    baseline = _query_production_result(
        baseline_kernel,
        run_contract_projection=baseline_contract,
    )
    _run_lane(shadow_kernel, shadow_contract)
    with_lane = _query_production_result(
        shadow_kernel,
        run_contract_projection=shadow_contract,
    )

    assert with_lane.candidate_queries == baseline.candidate_queries
    assert with_lane.candidate_source == baseline.candidate_source
    assert with_lane.effective_route_posture == baseline.effective_route_posture
    assert (
        with_lane.contract_source_requirement_hints
        == baseline.contract_source_requirement_hints
    )
    assert shadow_kernel.state.search_work_plan_projection[
        "runtime_consumed_by_query_plan"
    ] is False


def test_lane_generates_no_query_text_or_admission_and_flags_no_behavior_change() -> None:
    kernel, contract_projection = _kernel_with_contract("ag96c10-flags")

    lane = _run_lane(kernel, contract_projection)
    encoded = json.dumps(lane, sort_keys=True)

    for key in (
        "runtime_consumed_by_query_plan",
        "query_plan_behavior_changed",
        "query_text_generated",
        "query_admission_changed",
        "query_order_changed",
        "provider_search_behavior_changed",
        "search_depth_changed",
        "retrieval_behavior_changed",
        "prompt_behavior_changed",
        "citation_behavior_changed",
        "final_answer_behavior_changed",
    ):
        assert lane[key] is False
    assert "candidate_queries" not in encoded
    assert "finalized_queries" not in encoded
    assert "current_queries" not in encoded
    assert '"query_text"' not in encoded
    assert QUERY_PRODUCTION_STAGE not in kernel.state.stage_statuses
    assert QUERY_PLAN_ADMISSION_STAGE not in kernel.state.stage_statuses


def test_lane_redacts_raw_private_fields() -> None:
    kernel, contract_projection = _kernel_with_contract("ag96c10-redaction")
    tainted_contract = {
        **contract_projection,
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
    }

    lane = run_search_work_shadow_lane(
        run_kernel=kernel,
        run_contract_projection=tainted_contract,
        route_projection={
            **ROUTE_PROJECTION,
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
        },
        requested_mode="Balanced",
        selected_depth=contract_projection.get("selected_depth"),
        current_date_ref={"id": "current-date:test"},
        metadata={
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "TRACE_SENTINEL",
            "safe_note": "visible-safe-note",
        },
    )
    encoded = json.dumps(
        {"lane": lane, "trace": kernel.to_trace_fragment()},
        sort_keys=True,
    )

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


def test_pipeline_uses_one_pass_through_lane_call_after_contract_synthesis() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_search_work_shadow_lane"
    ]
    contract_reduce = source.index("run_kernel.reduce(run_contract_result.observation)")
    lane_call = source.index("run_search_work_shadow_lane", contract_reduce)
    query_authorize = source.index(
        "query_production_action = run_kernel.authorize_query_production",
        lane_call,
    )

    assert len(calls) == 1
    assert contract_reduce < lane_call < query_authorize
    for forbidden in (
        "RuntimeShadowSearchWorkPlanInput",
        "observe_runtime_shadow_search_work_plan_construction",
        "SearchWorkPlanConstructionInput",
        "QueryShapeAssessment",
        "ContractResolutionRecord",
        "ComponentCandidate",
        "ProviderJobCandidate",
        "SourceObligationCandidate",
        "build_query_plan_work_shadow_projection",
        "construct_search_work_plan_from_records",
        "observe_search_work_plan_construction",
    ):
        assert forbidden not in source


def test_closed_runtime_modules_do_not_import_shadow_lane() -> None:
    forbidden_modules = {
        "core.search_work_shadow_lane_runtime",
        "search_work_shadow_lane_runtime",
    }
    paths = (
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "retrieval_scheduler.py",
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


def test_shadow_lane_keeps_provider_retrieval_prompt_boundary() -> None:
    source = SHADOW_LANE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
        "core.query_production_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
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
        "authorize_query_production",
        "authorize_query_plan_admission",
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
