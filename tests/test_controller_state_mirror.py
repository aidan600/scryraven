from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_state_mirror import record_run_metadata_snapshot
from core.cost_accounting import CostAccumulator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunOutcome
from core.run_controller import RunController
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
    assert_jsonl_event_controller_payload_contract,
    assert_no_top_level_controller_payload,
    assert_session_controller_payload_contract,
    assert_trace_key_delta_only_controller_diagnostics,
)
from tests.test_source_class_recovery_trace import (
    _execution_event_from_log,
    _run_case,
    _TraceHarness,
)

_ROOT = Path(__file__).resolve().parents[1]
_MIRROR_HELPER_PATH = _ROOT / "core" / "controller_state_mirror.py"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _capture_run_metadata_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    **harness_kwargs: Any,
) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    captured: dict[str, Any] = {}
    original_record = orchestrator.record_run_metadata_snapshot

    def forbidden_trace_fragment(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("RunController.to_trace_fragment must stay unused")

    def capture_record(*args: Any, **kwargs: Any) -> Any:
        result = original_record(*args, **kwargs)
        controller = args[0]
        captured["state"] = controller.snapshot_state()
        captured["mirror_kwargs"] = deepcopy(kwargs)
        return result

    monkeypatch.setattr(
        orchestrator.RunController,
        "to_trace_fragment",
        forbidden_trace_fragment,
    )
    monkeypatch.setattr(orchestrator, "record_run_metadata_snapshot", capture_record)
    outcome, harness, log_entry = _run_case(tmp_path, **harness_kwargs)
    return outcome, harness, log_entry, captured


def test_record_run_metadata_snapshot_is_mutation_safe() -> None:
    controller = RunController()

    returned = record_run_metadata_snapshot(
        controller,
        session_id="session-1",
        run_id="run-1",
        query="synthetic question",
        mode="Balanced",
        current_date="2026-05-18",
        core_topic="synthetic topic",
        intent="general",
        complexity="medium",
    )

    returned_snapshot = controller.snapshot_state()
    returned_snapshot["query"] = "mutated question"
    returned_snapshot["run_id"] = "mutated-run"

    state = controller.snapshot_state()
    assert returned is controller
    assert state["session_id"] == "session-1"
    assert state["run_id"] == "run-1"
    assert state["query"] == "synthetic question"
    assert state["mode"] == "Balanced"
    assert state["current_date"] == "2026-05-18"
    assert state["core_topic"] == "synthetic topic"
    assert state["intent"] == "general"
    assert state["complexity"] == "medium"


def test_controller_state_runtime_capture_matches_existing_run_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, _harness, log_entry, captured = _capture_run_metadata_case(
        tmp_path,
        monkeypatch,
        query="What are the current eligibility requirements for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    state = captured["state"]
    assert state["session_id"] == outcome.session_id == outcome.new_session["id"]
    assert state["run_id"] == outcome.run_id == outcome.new_session["run_id"]
    assert state["run_id"] == log_entry["run_id"]
    assert state["query"] == outcome.query
    assert state["mode"] == outcome.pipeline_config["mode"] == "Balanced"
    assert state["mode"] == outcome.new_session["last_report_mode"]
    assert state["current_date"] == outcome.new_session["timestamp"] == "2026-05-18"
    assert state["core_topic"] == outcome.core_topic == outcome.new_session["core_topic"]
    assert state["intent"] == outcome.intent == outcome.execution_trace["intent"]
    assert state["complexity"] == outcome.complexity == outcome.execution_trace["complexity"]
    assert captured["mirror_kwargs"] == {
        "session_id": outcome.session_id,
        "run_id": outcome.run_id,
        "query": outcome.query,
        "mode": "Balanced",
        "current_date": "2026-05-18",
        "core_topic": outcome.core_topic,
        "intent": outcome.intent,
        "complexity": outcome.complexity,
    }

    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(log_entry)
    assert_session_controller_payload_contract(outcome.new_session)


def test_controller_state_mirror_handles_fallback_route_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = "What evidence exists for Fallback Program eligibility?"
    captured: dict[str, Any] = {}
    original_record = orchestrator.record_run_metadata_snapshot
    harness = _TraceHarness(
        tmp_path,
        query=query,
        core_topic="unused router topic",
        primary_entity="Fallback Program",
        researcher_query="Fallback Program eligibility evidence",
        router_query_type="other",
    )
    original_ask_model = harness.ask_model

    def fallback_ask_model(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return "{not json"
        return original_ask_model(prompt, system_prompt, **kwargs)

    def capture_record(*args: Any, **kwargs: Any) -> Any:
        result = original_record(*args, **kwargs)
        controller = args[0]
        captured["state"] = controller.snapshot_state()
        return result

    harness.ask_model = fallback_ask_model
    monkeypatch.setattr(orchestrator, "record_run_metadata_snapshot", capture_record)

    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-05-18",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")

    state = captured["state"]
    assert state["session_id"] == outcome.session_id
    assert state["run_id"] == outcome.run_id == log_entry["run_id"]
    assert state["query"] == query
    assert state["mode"] == "Balanced"
    assert state["current_date"] == "2026-05-18"
    assert state["core_topic"] == outcome.core_topic == query[:100]
    assert state["intent"] == outcome.intent == "general"
    assert state["complexity"] == outcome.complexity == "medium"
    assert harness.search_calls
    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_execution_trace_payload_contract(log_entry["execution_trace"])


def test_controller_state_mirror_noop_does_not_change_outputs_or_retrieval_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log, _captured = _capture_run_metadata_case(
        tmp_path / "active",
        monkeypatch,
        query="What are the current eligibility requirements for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    def noop_record(controller: RunController, **_kwargs: Any) -> RunController:
        return controller

    monkeypatch.setattr(orchestrator, "record_run_metadata_snapshot", noop_record)
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
    assert {field.name for field in fields(RunOutcome)} == set(active_outcome.__dict__)
    assert {field.name for field in fields(RunOutcome)} == set(baseline_outcome.__dict__)

    assert active_outcome.execution_trace["queries_per_iteration"] == (
        baseline_outcome.execution_trace["queries_per_iteration"]
    )
    assert active_outcome.execution_trace["pass_providers"] == (
        baseline_outcome.execution_trace["pass_providers"]
    )
    assert active_harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert active_harness.search_calls[0]["search_depth"] == "basic"
    assert active_harness.search_calls[0]["results_per_query"] == 6

    active_row = execution_jsonl_to_run_row(active_log)
    baseline_row = execution_jsonl_to_run_row(baseline_log)
    assert active_row is not None
    assert baseline_row is not None
    assert set(active_row) <= set(RUN_COLUMNS)
    assert set(active_row) == set(baseline_row)
    assert "execution_trace" not in active_row

    assert_execution_trace_payload_contract(active_outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(active_log)
    assert_session_controller_payload_contract(active_outcome.new_session)
    assert_no_top_level_controller_payload(active_row)


def test_controller_state_mirror_static_import_guard() -> None:
    tree = ast.parse(_MIRROR_HELPER_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "core.db",
        "core.prompts",
        "core.routing",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.search",
        "core.search_providers",
        "core.source_class_recovery",
        "core.weak_corpus",
    )
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert all(
        not name.startswith(forbidden_import_prefixes)
        for name in imports
    ), imports

    source = _MIRROR_HELPER_PATH.read_text(encoding="utf-8")
    forbidden_terms = (
        "to_trace_fragment",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "select_providers",
        "process_search_queries",
        "build_source_class_recovery_recommendation",
    )
    assert all(term not in source for term in forbidden_terms)
