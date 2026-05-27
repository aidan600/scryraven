from __future__ import annotations

import ast
from pathlib import Path

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.task_ledger import TaskLedger, TaskStatus
from tests.controller_diagnostics_contract_utils import (
    assert_trace_key_delta_only_controller_diagnostics,
)
from tests.test_source_class_recovery_trace import _run_case

_ROOT = Path(__file__).resolve().parents[1]
_TASK_LEDGER_PATH = _ROOT / "core" / "task_ledger.py"


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


def test_task_ledger_status_lifecycle_and_reason_recording() -> None:
    metadata = {"queries": ["Care Program official rules"], "counts": {"new": 1}}
    ledger = (
        TaskLedger.empty()
        .record_planned(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason="eligible_may_run",
            metadata=metadata,
        )
        .record_started(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason="observed_provider_role_source_class_recovery",
        )
        .record_completed(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason="observed_result_count",
            metadata={"result_count": 1, "new_url_count": 1},
        )
        .record_skipped(
            task_id="weak_corpus_recovery",
            module_id="weak_corpus_recovery",
            reason="not_weak_corpus",
        )
        .record_blocked(
            task_id="supplemental_retrieval",
            module_id="supplemental_retrieval",
            reason="synthesis_sufficient",
        )
        .record_failed(
            task_id="synthetic_observed_failure",
            module_id="synthetic",
            reason="observed_exception",
        )
    )
    metadata["queries"].append("late mutation")
    metadata["counts"]["new"] = 99

    payload = ledger.to_dict()
    source_records = [record.to_dict() for record in ledger.records_for("source_class_recovery")]

    assert [record["status"] for record in source_records] == [
        "planned",
        "started",
        "completed",
    ]
    assert source_records[0]["reason"] == "eligible_may_run"
    assert source_records[0]["metadata"] == {
        "queries": ["Care Program official rules"],
        "counts": {"new": 1},
    }
    assert payload["status_counts"] == {
        "planned": 1,
        "started": 1,
        "completed": 1,
        "skipped": 1,
        "blocked": 1,
        "failed": 1,
    }


def test_task_ledger_records_observed_source_class_recovery_without_runtime_change(
    tmp_path: Path,
) -> None:
    passive_outcome, passive_harness, passive_log = _run_case(
        tmp_path / "passive",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    trace = passive_outcome.execution_trace
    ledger = (
        TaskLedger.empty()
        .record_planned(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason="may_run",
            metadata={
                "missing_classes": trace[
                    "active_source_class_recovery_missing_classes"
                ],
            },
        )
        .record_started(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason=trace["active_source_class_recovery_provider_role"],
        )
        .record_completed(
            task_id="source_class_recovery",
            module_id="source_class_recovery",
            reason="observed_lifecycle",
            metadata={
                "result_count": trace[
                    "active_source_class_recovery_result_count"
                ],
                "new_url_count": trace[
                    "active_source_class_recovery_new_url_count"
                ],
                "search_depth": trace[
                    "active_source_class_recovery_search_depth"
                ],
            },
        )
    )

    assert trace["active_source_class_recovery_used"] is True
    assert [record.status for record in ledger.records_for("source_class_recovery")] == [
        TaskStatus.PLANNED,
        TaskStatus.STARTED,
        TaskStatus.COMPLETED,
    ]
    assert passive_harness.search_calls == baseline_harness.search_calls
    assert passive_harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert passive_harness.search_calls[0]["search_depth"] == "basic"
    assert passive_harness.search_calls[0]["results_per_query"] == 6
    assert passive_harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert passive_harness.search_calls[1]["search_depth"] == "basic"
    assert passive_harness.search_calls[1]["results_per_query"] == 6
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
    assert passive_harness.analyst_calls == baseline_harness.analyst_calls == 1
    assert passive_harness.economist_calls == baseline_harness.economist_calls == 0
    assert passive_harness.author_calls == baseline_harness.author_calls == 1


def test_task_ledger_static_import_guard() -> None:
    tree = ast.parse(_TASK_LEDGER_PATH.read_text(encoding="utf-8"))
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
