from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.run_config import RunOutcome
from core.run_controller import RunController
from core.stage_ledger_mirror import record_stage_ledger_query_provider_facts
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
    assert_jsonl_event_controller_payload_contract,
    assert_no_top_level_controller_payload,
    assert_session_controller_payload_contract,
    assert_trace_key_delta_only_controller_diagnostics,
)
from tests.test_source_class_recovery_trace import _run_case

_ROOT = Path(__file__).resolve().parents[1]
_MIRROR_HELPER_PATH = _ROOT / "core" / "stage_ledger_mirror.py"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def test_record_stage_ledger_query_provider_facts_is_mutation_safe() -> None:
    queries_by_iteration = {1: ["synthetic query 1", "synthetic query 2"]}
    disambiguation_queries_by_iteration = {1: ["synthetic disambiguation query"]}
    providers_by_iteration = [["tavily", "exa"]]
    provider_diagnostics = [
        {
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "success": True,
            "result_count": 3,
            "nested": {"queries": ["synthetic query 1"]},
        }
    ]
    retrieval_pass_records = [
        {
            "stage": "main_retrieval",
            "iteration": 1,
            "queries": ["synthetic query 1", "synthetic query 2"],
            "providers": ["tavily", "exa"],
            "provider_role": "main_retrieval",
            "search_depth": "basic",
            "results_per_query": 6,
        }
    ]
    controller = RunController()

    returned = record_stage_ledger_query_provider_facts(
        controller,
        queries_by_iteration=queries_by_iteration,
        disambiguation_queries_by_iteration=disambiguation_queries_by_iteration,
        providers_by_iteration=providers_by_iteration,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )

    queries_by_iteration[1].append("late query")
    disambiguation_queries_by_iteration[1].append("late disambiguation")
    providers_by_iteration[0].append("late-provider")
    provider_diagnostics[0]["nested"]["queries"].append("late diagnostic")
    retrieval_pass_records[0]["queries"].append("late pass query")

    returned_snapshot = controller.snapshot_ledger()
    returned_snapshot["query_records"][0]["query"] = "mutated snapshot"
    returned_snapshot["provider_records"][0]["metadata"]["providers"].append(
        "mutated-provider"
    )

    ledger = controller.snapshot_ledger()
    assert returned is controller
    assert [record["query"] for record in ledger["query_records"]] == [
        "synthetic query 1",
        "synthetic query 2",
        "synthetic disambiguation query",
    ]
    assert ledger["query_records"][0]["metadata"] == {
        "source": "queries_by_iteration",
        "query_index": 0,
    }

    pass_records = [
        record
        for record in ledger["provider_records"]
        if record["stage"] == "main_retrieval"
    ]
    assert [record["provider"] for record in pass_records] == ["tavily", "exa"]
    assert pass_records[0]["provider_role"] == "main_retrieval"
    assert pass_records[0]["metadata"]["queries"] == [
        "synthetic query 1",
        "synthetic query 2",
    ]
    assert pass_records[0]["metadata"]["search_depth"] == "basic"
    assert pass_records[0]["metadata"]["results_per_query"] == 6

    diagnostic_records = [
        record
        for record in ledger["provider_records"]
        if record["stage"] == "provider_diagnostic"
    ]
    assert diagnostic_records[0]["metadata"]["diagnostic"]["nested"] == {
        "queries": ["synthetic query 1"]
    }


def test_stage_ledger_runtime_capture_matches_existing_query_provider_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    original_record = orchestrator.record_stage_ledger_query_provider_facts

    def forbidden_trace_fragment(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("RunController.to_trace_fragment must stay unused")

    def capture_record(*args: Any, **kwargs: Any) -> Any:
        result = original_record(*args, **kwargs)
        controller = args[0]
        captured["ledger"] = controller.snapshot_ledger()
        captured["mirror_kwargs"] = deepcopy(kwargs)
        return result

    monkeypatch.setattr(
        orchestrator.RunController,
        "to_trace_fragment",
        forbidden_trace_fragment,
    )
    monkeypatch.setattr(
        orchestrator,
        "record_stage_ledger_query_provider_facts",
        capture_record,
    )

    outcome, harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    ledger = captured["ledger"]
    search_call = harness.search_calls[0]
    query_records = [
        record
        for record in ledger["query_records"]
        if record["stage"] == "queries_by_iteration"
    ]
    assert [record["query"] for record in query_records] == search_call["queries"]
    assert outcome.execution_trace["queries_per_iteration"] == {
        "1": search_call["queries"]
    }
    assert captured["mirror_kwargs"]["queries_by_iteration"] == {
        1: search_call["queries"]
    }

    pass_provider_records = [
        record
        for record in ledger["provider_records"]
        if record["stage"] == "providers_by_iteration"
    ]
    assert [record["provider"] for record in pass_provider_records] == [
        "tavily"
    ]
    assert outcome.execution_trace["pass_providers"] == [
        search_call["search_providers"]
    ]

    retrieval_records = [
        record
        for record in ledger["provider_records"]
        if record["stage"] == "main_retrieval"
    ]
    assert len(retrieval_records) == 1
    assert retrieval_records[0]["provider"] == "tavily"
    assert retrieval_records[0]["provider_role"] == search_call["provider_role"]
    assert retrieval_records[0]["metadata"]["queries"] == search_call["queries"]
    assert retrieval_records[0]["metadata"]["providers"] == search_call[
        "search_providers"
    ]
    assert retrieval_records[0]["metadata"]["search_depth"] == search_call[
        "search_depth"
    ]
    assert retrieval_records[0]["metadata"]["results_per_query"] == search_call[
        "results_per_query"
    ]
    assert search_call["provider_role"] == "main_retrieval"
    assert search_call["search_depth"] == "basic"
    assert search_call["results_per_query"] == 6

    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(log_entry)
    assert_session_controller_payload_contract(outcome.new_session)


def test_stage_ledger_mirror_noop_does_not_change_outputs_or_retrieval_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        query="What are the current eligibility requirements for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    def noop_record(controller: RunController, **_kwargs: Any) -> RunController:
        return controller

    monkeypatch.setattr(
        orchestrator,
        "record_stage_ledger_query_provider_facts",
        noop_record,
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        query="What are the current eligibility requirements for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    assert active_harness.search_calls == baseline_harness.search_calls
    assert_trace_key_delta_only_controller_diagnostics(
        active_outcome.execution_trace,
        baseline_outcome.execution_trace,
    )
    assert set(active_log) == set(baseline_log)
    assert_trace_key_delta_only_controller_diagnostics(
        active_log["execution_trace"],
        baseline_log["execution_trace"],
    )
    assert set(active_outcome.new_session) == set(baseline_outcome.new_session)
    assert {field.name for field in fields(RunOutcome)} == set(
        active_outcome.__dict__
    )

    active_row = execution_jsonl_to_run_row(active_log)
    baseline_row = execution_jsonl_to_run_row(baseline_log)
    assert active_row is not None
    assert baseline_row is not None
    assert set(active_row) == set(RUN_COLUMNS)
    assert set(active_row) == set(baseline_row)
    assert "execution_trace" not in active_row
    assert_no_top_level_controller_payload(active_row)


def test_stage_ledger_mirror_static_import_guard() -> None:
    tree = ast.parse(_MIRROR_HELPER_PATH.read_text(encoding="utf-8"))
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
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_function_prefixes = (
        "build_author",
        "choose_",
        "decide_",
        "finalize_",
        "rank_",
        "recover_",
        "retrieve_",
        "route_",
        "run_",
        "select_",
        "should_",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    active_function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_function_prefixes)
    ]

    assert violations == []
    assert active_function_names == []
