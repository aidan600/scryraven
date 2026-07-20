from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

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
    RunKernel,
)
from core.search_work_shadow_lane_runtime import (
    SEARCH_WORK_SHADOW_LANE_TRACE_KEY,
    run_search_work_shadow_lane,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SHADOW_LANE = ROOT / "core" / "search_work_shadow_lane_runtime.py"


class _Status:
    def step(self, _message: str) -> None:
        return None


class _Logger:
    def warning(self, _message: str, _error: Exception) -> None:
        return None


def _route_projection(query: str) -> dict[str, Any]:
    return {
        "intent": "general",
        "report_type": "general_research",
        "query_type": "rule",
        "core_topic": query[:80],
        "primary_entity": "runtime-shadow-test",
        "is_academic": False,
    }


def _kernel_with_contract(
    run_id: str,
    query: str,
    *,
    mode: str = "Balanced",
) -> tuple[RunKernel, dict[str, Any], dict[str, Any]]:
    route_projection = _route_projection(query)
    kernel = RunKernel.start(run_id=run_id, request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={"query_length": len(query)})
    result = execute_run_contract_synthesis_action(
        action,
        query=query,
        mode=mode,
        current_date="June 15, 2026",
        route_projection=route_projection,
    )
    kernel.reduce(result.observation)
    return kernel, dict(kernel.state.run_contract_projection), route_projection


def _run_lane(
    kernel: RunKernel,
    contract_projection: Mapping[str, Any],
    route_projection: Mapping[str, Any],
    *,
    requested_mode: str = "Balanced",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return run_search_work_shadow_lane(
        run_kernel=kernel,
        run_contract_projection=contract_projection,
        route_projection=route_projection,
        requested_mode=requested_mode,
        selected_depth=contract_projection.get("selected_depth"),
        current_date_ref={"id": "current-date:test"},
        safe_user_domain_hints={},
        metadata={"callsite": "ag96d1-unit-test", **dict(metadata or {})},
    )


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


def _query_production_result(
    kernel: RunKernel,
    *,
    run_contract_projection: dict[str, Any],
) -> Any:
    def ask_model(*_args: Any, **_kwargs: Any) -> str:
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
        current_date="June 15, 2026",
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


def _official_query() -> str:
    return "What is the current official filing fee for Form I-130?"


def _all_need_query() -> str:
    return (
        "What is the current official filing fee, the current California legal "
        "deadline to appeal, and the current OpenAI Responses API parameter "
        "from official canonical docs?"
    )


def test_lane_output_includes_official_current_handoff_projection() -> None:
    kernel, contract, route = _kernel_with_contract("ag96d1-official", _official_query())

    lane = _run_lane(kernel, contract, route)
    handoff = lane["search_work_official_current_handoff"]

    assert lane["shadow_lane_ran"] is True
    assert lane["search_work_plan_projection_present"] is True
    assert lane["query_plan_work_shadow_projection_present"] is True
    assert lane["search_work_official_current_handoff_present"] is True
    assert lane["official_current_handoff_source_obligation_driven"] is True
    assert lane["official_current_handoff_mode_specific_official_executor"] is False
    assert lane["official_current_handoff_provider_selected"] is False
    assert lane["official_current_handoff_query_text_generated"] is False
    assert lane["official_current_handoff_search_executed"] is False
    assert lane["official_current_handoff_retrieval_executed"] is False
    assert lane["official_current_handoff_final_answer_behavior_changed"] is False
    assert lane["official_current_handoff_need_counts"]["official_current"] == 1
    assert handoff["official_current_needs"]
    assert handoff["source_obligation_driven"] is True
    assert kernel.state.projections[SEARCH_WORK_SHADOW_LANE_TRACE_KEY] == lane


def test_lane_handoff_represents_legal_canonical_and_source_bound_numeric_needs() -> None:
    kernel, contract, route = _kernel_with_contract("ag96d1-all-needs", _all_need_query())

    lane = _run_lane(kernel, contract, route)
    handoff = lane["search_work_official_current_handoff"]

    assert lane["official_current_handoff_need_counts"]["official_current"] >= 1
    assert lane["official_current_handoff_need_counts"]["legal_current_primary"] >= 1
    assert lane["official_current_handoff_need_counts"]["canonical_documentation"] >= 1
    assert lane["official_current_handoff_need_counts"]["source_bound_numeric"] >= 1
    assert handoff["legal_current_primary_needs"]
    assert handoff["canonical_documentation_needs"]
    assert handoff["source_bound_numeric_needs"]
    assert "legal_or_regulatory_text" in handoff["required_source_classes"]
    assert "primary_source_documents" in handoff["required_source_classes"]
    assert "sourced_numeric_values" in handoff["required_source_classes"]


def test_lane_handoff_is_mode_neutral_for_matching_obligations() -> None:
    handoffs: list[dict[str, Any]] = []
    for mode in ("Fast", "Balanced", "Deep"):
        kernel, contract, route = _kernel_with_contract(
            f"ag96d1-mode-{mode.casefold()}",
            _official_query(),
            mode=mode,
        )
        lane = _run_lane(kernel, contract, route, requested_mode=mode)
        handoffs.append(lane["search_work_official_current_handoff"])

    comparable_fields = (
        "official_current_needs",
        "source_bound_numeric_needs",
        "required_source_classes",
        "source_obligation_ids",
        "provider_job_kinds",
    )
    for field in comparable_fields:
        assert handoffs[0][field] == handoffs[1][field] == handoffs[2][field]
    assert all(item["source_obligation_driven"] is True for item in handoffs)
    assert all(item["mode_specific_official_executor"] is False for item in handoffs)


def test_official_shadow_handoff_cannot_restore_legacy_query_production() -> None:
    baseline_kernel, baseline_contract, _baseline_route = _kernel_with_contract(
        "ag96d1-baseline",
        _official_query(),
    )
    shadow_kernel, shadow_contract, shadow_route = _kernel_with_contract(
        "ag96d1-shadow",
        _official_query(),
    )

    with pytest.raises(
        QueryStrategyConvergenceError,
        match="legacy initial producer fallback is retired",
    ):
        _query_production_result(
            baseline_kernel,
            run_contract_projection=baseline_contract,
        )
    _run_lane(shadow_kernel, shadow_contract, shadow_route)
    with pytest.raises(
        QueryStrategyConvergenceError,
        match="legacy initial producer fallback is retired",
    ):
        _query_production_result(
            shadow_kernel,
            run_contract_projection=shadow_contract,
        )


def test_lane_and_handoff_generate_no_query_text_or_behavior_changes() -> None:
    kernel, contract, route = _kernel_with_contract("ag96d1-no-behavior", _official_query())

    lane = _run_lane(kernel, contract, route)
    handoff = lane["search_work_official_current_handoff"]
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
    for key in (
        "provider_selected",
        "query_text_generated",
        "search_executed",
        "retrieval_executed",
        "final_answer_behavior_changed",
    ):
        assert handoff[key] is False
    assert "candidate_queries" not in encoded
    assert "finalized_queries" not in encoded
    assert "current_queries" not in encoded
    assert '"query_text"' not in encoded
    assert QUERY_PRODUCTION_STAGE not in kernel.state.stage_statuses
    assert QUERY_PLAN_ADMISSION_STAGE not in kernel.state.stage_statuses


def test_lane_handoff_redacts_raw_private_fields() -> None:
    kernel, contract, route = _kernel_with_contract("ag96d1-redaction", _official_query())
    tainted_contract = {
        **contract,
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
    }

    lane = run_search_work_shadow_lane(
        run_kernel=kernel,
        run_contract_projection=tainted_contract,
        route_projection={
            **route,
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
        },
        requested_mode="Balanced",
        selected_depth=contract.get("selected_depth"),
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


def test_pipeline_has_no_passive_lane_or_official_shadow_handoff_logic() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    tree = ast.parse(source)

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_search_work_shadow_lane"
    ]
    assert calls == []
    assert "search_work_official_current_handoff" not in source
    assert "build_search_work_official_current_handoff" not in source


def test_closed_runtime_modules_do_not_import_handoff_or_lane() -> None:
    forbidden_modules = {
        "core.search_work_shadow_lane_runtime",
        "search_work_shadow_lane_runtime",
        "core.search_work_official_current_handoff",
        "search_work_official_current_handoff",
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
        ROOT / "core" / "final_answer_runtime_adapter.py",
        ROOT / "core" / "final_evidence_bundle_builder.py",
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


def test_shadow_lane_handoff_import_keeps_provider_retrieval_prompt_boundary() -> None:
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
        "core.final_answer_runtime_adapter",
        "core.final_evidence_bundle_builder",
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
