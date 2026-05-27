from __future__ import annotations

import ast
from pathlib import Path

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.module_registry import get_module_registry
from core.run_plan import PlanDisposition, RunPlan, build_run_plan
from tests.controller_diagnostics_contract_utils import (
    assert_trace_key_delta_only_controller_diagnostics,
)
from tests.test_pre_analyst_gate import (
    _execution_event_from_log as _pre_analyst_execution_event_from_log,
)
from tests.test_pre_analyst_gate import _run_pipeline_harness

_ROOT = Path(__file__).resolve().parents[1]
_RUN_PLAN_PATH = _ROOT / "core" / "run_plan.py"

RAW_AUTHOR_MARKERS = (
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "QUANTITATIVE FRAMEWORK",
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _dispositions(plan: RunPlan) -> dict[str, str]:
    return {
        item.stage_id: item.disposition.value
        for item in plan.items
    }


def test_run_plan_checklist_shape_by_mode() -> None:
    fast = build_run_plan(
        mode="Fast",
        routing_metadata={
            "intent": "general",
            "report_type": "general_research",
            "query_type": "product",
        },
    )
    balanced = build_run_plan(
        mode="Balanced",
        routing_metadata={
            "intent": "general",
            "report_type": "quantitative_comparison",
            "query_type": "quantitative_comparison",
        },
    )
    deep = build_run_plan(
        mode="Deep",
        routing_metadata={
            "intent": "general",
            "report_type": "general_research",
            "query_type": "other",
        },
    )

    assert _dispositions(fast) == {
        "route_intent": "required",
        "researcher_queries": "required",
        "main_retrieval": "required",
        "weak_corpus_recovery": "blocked_by_mode",
        "source_class_recovery": "may_run",
        "analyst_review": "blocked_by_mode",
        "economist_preflight": "not_applicable",
        "supplemental_retrieval": "blocked_by_mode",
        "scrutineer": "blocked_by_mode",
        "author": "required",
    }
    assert balanced.item("source_class_recovery").disposition is (
        PlanDisposition.MAY_RUN
    )
    assert balanced.item("weak_corpus_recovery").disposition is (
        PlanDisposition.MAY_RUN
    )
    assert balanced.item("economist_preflight").disposition is (
        PlanDisposition.SHADOW
    )
    assert balanced.item("scrutineer").disposition is (
        PlanDisposition.BLOCKED_BY_MODE
    )
    assert deep.item("scrutineer").disposition is PlanDisposition.REQUIRED
    assert deep.item("source_class_recovery").disposition is PlanDisposition.MAY_RUN


def test_run_plan_module_ids_resolve_to_registry_entries() -> None:
    registry_module_ids = {
        entry.module_id for entry in get_module_registry()
    }

    for mode in ("Fast", "Balanced", "Deep"):
        plan = build_run_plan(
            mode=mode,
            routing_metadata={
                "intent": "general",
                "report_type": "quantitative_comparison",
                "query_type": "quantitative_comparison",
            },
        )
        assert {
            item.module_id for item in plan.items
        } <= registry_module_ids


def test_balanced_source_class_missing_plan_marks_recovery_may_run() -> None:
    plan = build_run_plan(
        mode="Balanced",
        routing_metadata={
            "intent": "general",
            "report_type": "general_research",
            "query_type": "other",
        },
    )
    payload = plan.to_dict()

    source_class_item = plan.item("source_class_recovery")
    assert source_class_item.disposition is PlanDisposition.MAY_RUN
    assert "existing lifecycle facts" in source_class_item.reason
    assert payload["mode_policy"]["mode"] == "Balanced"
    assert payload["routing_metadata"] == {
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
    }


def test_fast_weak_corpus_negative_control_keeps_existing_runtime_shape(
    tmp_path: Path,
) -> None:
    plan = build_run_plan(
        mode="Fast",
        routing_metadata={
            "intent": "general",
            "report_type": "general_research",
            "query_type": "product",
        },
    )
    assert plan.item("weak_corpus_recovery").disposition is (
        PlanDisposition.BLOCKED_BY_MODE
    )
    assert plan.item("source_class_recovery").disposition is (
        PlanDisposition.MAY_RUN
    )
    assert "existing lifecycle eligibility" in plan.item(
        "source_class_recovery"
    ).reason

    passive_outcome, passive_harness = _run_pipeline_harness(
        tmp_path / "passive",
        healthy=False,
        mode="Fast",
    )
    baseline_outcome, baseline_harness = _run_pipeline_harness(
        tmp_path / "baseline",
        healthy=False,
        mode="Fast",
    )
    passive_log = _pre_analyst_execution_event_from_log(
        tmp_path / "passive" / "execution.jsonl"
    )
    baseline_log = _pre_analyst_execution_event_from_log(
        tmp_path / "baseline" / "execution.jsonl"
    )

    trace = passive_outcome.execution_trace
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == "max_iterations_1"
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_provider_role"] is None
    assert passive_harness.analyst_calls == baseline_harness.analyst_calls == 0
    assert passive_outcome.report == baseline_outcome.report
    assert_trace_key_delta_only_controller_diagnostics(
        passive_outcome.execution_trace,
        baseline_outcome.execution_trace,
    )
    assert_trace_key_delta_only_controller_diagnostics(
        passive_log["execution_trace"],
        baseline_log["execution_trace"],
    )

    passive_row = execution_jsonl_to_run_row(passive_log)
    baseline_row = execution_jsonl_to_run_row(baseline_log)
    assert passive_row is not None
    assert baseline_row is not None
    assert set(passive_row) == set(RUN_COLUMNS)
    assert set(passive_row) == set(baseline_row)
    assert "execution_trace" not in passive_row
    assert passive_harness.author_prompts
    for marker in RAW_AUTHOR_MARKERS:
        assert marker not in passive_harness.author_prompts[-1]


def test_run_plan_static_import_guard() -> None:
    tree = ast.parse(_RUN_PLAN_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.routing",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_function_prefixes = (
        "dispatch",
        "execute",
        "recover",
        "retry",
        "route",
        "select",
    )
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    active_function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_function_prefixes)
    ]
    violations = [
        name
        for name in imports
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    assert violations == []
    assert active_function_names == []
