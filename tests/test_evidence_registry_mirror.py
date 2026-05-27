from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.evidence_registry_mirror import record_final_evidence_snapshot
from core.run_config import RunOutcome
from core.run_controller import RunController
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
    assert_jsonl_event_controller_payload_contract,
    assert_no_top_level_controller_payload,
    assert_trace_key_delta_only_controller_diagnostics,
)
from tests.test_source_class_recovery_trace import _run_case

_ROOT = Path(__file__).resolve().parents[1]
_MIRROR_HELPER_PATH = _ROOT / "core" / "evidence_registry_mirror.py"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _run_mirror_case(
    tmp_path: Path,
    **harness_kwargs: Any,
) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    captured: dict[str, Any] = {}
    original_record = orchestrator.record_final_evidence_snapshot

    def capture_record(*args: Any, **kwargs: Any) -> Any:
        result = original_record(*args, **kwargs)
        controller = args[0]
        captured["evidence"] = controller.snapshot_evidence()
        captured["final_top_evidence"] = deepcopy(kwargs["final_top_evidence"])
        captured["seen_urls"] = deepcopy(list(kwargs["seen_urls"]))
        captured["collected_images"] = deepcopy(list(kwargs["collected_images"]))
        return result

    orchestrator.record_final_evidence_snapshot = capture_record
    try:
        outcome, harness, log_entry = _run_case(tmp_path, **harness_kwargs)
    finally:
        orchestrator.record_final_evidence_snapshot = original_record
    return outcome, harness, log_entry, captured


def test_record_final_evidence_snapshot_mirrors_exact_order_and_values() -> None:
    final_top_evidence = [
        {
            "source_id": 2,
            "title": "Second source",
            "url": "https://b.example/source",
            "text": "second",
            "metadata": {"rank": 1},
        },
        {
            "source_id": "1",
            "title": "First source",
            "url": "https://a.example/source",
            "text": "first",
            "metadata": {"rank": 2},
        },
    ]
    seen_urls = [
        "https://b.example/source",
        "https://a.example/source",
        "https://b.example/source",
    ]
    collected_images = [
        "https://img.example/2.jpg",
        "https://img.example/1.jpg",
    ]
    controller = RunController()

    returned = record_final_evidence_snapshot(
        controller,
        final_top_evidence=final_top_evidence,
        seen_urls=seen_urls,
        collected_images=collected_images,
    )

    evidence = controller.snapshot_evidence()
    assert returned is controller
    assert evidence["passages"] == final_top_evidence
    assert evidence["seen_urls"] == seen_urls
    assert evidence["collected_images"] == collected_images
    assert evidence["source_ids"] == [2, "1"]


def test_record_final_evidence_snapshot_is_mutation_safe() -> None:
    final_top_evidence = [
        {
            "source_id": 1,
            "title": "Original",
            "url": "https://example.com/source",
            "text": "original",
            "metadata": {"tags": ["initial"]},
        }
    ]
    seen_urls = ["https://example.com/source"]
    collected_images = ["https://img.example/original.jpg"]
    controller = RunController()

    record_final_evidence_snapshot(
        controller,
        final_top_evidence=final_top_evidence,
        seen_urls=seen_urls,
        collected_images=collected_images,
    )

    final_top_evidence[0]["metadata"]["tags"].append("mutated")
    seen_urls.append("https://example.com/late")
    collected_images[0] = "https://img.example/mutated.jpg"

    returned_snapshot = controller.snapshot_evidence()
    returned_snapshot["passages"][0]["metadata"]["tags"].append("returned")
    returned_snapshot["seen_urls"].append("https://example.com/returned")
    returned_snapshot["collected_images"].append("https://img.example/returned.jpg")
    returned_snapshot["source_ids"].append(99)

    assert controller.snapshot_evidence() == {
        "passages": [
            {
                "source_id": 1,
                "title": "Original",
                "url": "https://example.com/source",
                "text": "original",
                "metadata": {"tags": ["initial"]},
            }
        ],
        "seen_urls": ["https://example.com/source"],
        "collected_images": ["https://img.example/original.jpg"],
        "source_ids": [1],
        "source_tier_snapshots": [],
        "domain_snapshots": [],
        "trace_fields": {},
        "metadata": {},
    }


def test_final_evidence_mirror_runtime_capture_is_passive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_trace_fragment(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("RunController.to_trace_fragment must stay unused")

    monkeypatch.setattr(
        orchestrator.RunController,
        "to_trace_fragment",
        forbidden_trace_fragment,
    )

    outcome, harness, log_entry, captured = _run_mirror_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    evidence = captured["evidence"]
    assert evidence["passages"] == captured["final_top_evidence"]
    assert evidence["passages"] == outcome.top_passages
    assert evidence["passages"] == outcome.new_session["top_passages"]
    assert evidence["seen_urls"] == captured["seen_urls"]
    assert evidence["seen_urls"] == outcome.seen_urls
    assert evidence["seen_urls"] == outcome.new_session["seen_urls"]
    assert evidence["collected_images"] == captured["collected_images"]
    assert evidence["collected_images"] == outcome.collected_images
    assert evidence["collected_images"] == outcome.new_session["collected_images"]
    assert evidence["source_ids"] == [
        passage["source_id"] for passage in outcome.top_passages
    ]

    assert len(harness.search_calls) == 2
    search_call = harness.search_calls[0]
    assert outcome.execution_trace["queries_per_iteration"] == {
        "1": search_call["queries"]
    }
    assert outcome.execution_trace["pass_providers"] == [
        search_call["search_providers"]
    ]
    assert search_call["provider_role"] == "main_retrieval"
    assert search_call["search_depth"] == "basic"
    assert search_call["results_per_query"] == 6
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert outcome.execution_trace["active_source_class_recovery_used"] is True
    assert any(
        passage.get("retrieval_stage") == "source_class_recovery"
        for passage in evidence["passages"]
    )
    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_execution_trace_payload_contract(log_entry["execution_trace"])


def test_minimal_no_image_mirror_does_not_change_output_or_persistence_shape(
    tmp_path: Path,
) -> None:
    outcome, _harness, log_entry, captured = _run_mirror_case(
        tmp_path,
        query="Summarize available evidence for the local program.",
        core_topic="local program evidence",
        primary_entity="Local Program",
        researcher_query="Local Program evidence",
        source_tiers=["secondary"],
        domains=["local.example"],
    )

    evidence = captured["evidence"]
    assert len(evidence["passages"]) == 1
    assert evidence["source_ids"] == [1]
    assert evidence["collected_images"] == []
    assert outcome.collected_images == []
    assert outcome.new_session["collected_images"] == []

    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(log_entry)
    assert "evidence" not in outcome.new_session
    assert "controller" not in outcome.new_session

    row = execution_jsonl_to_run_row(log_entry)
    assert row is not None
    assert set(row) <= set(RUN_COLUMNS)
    assert "execution_trace" not in row
    assert_no_top_level_controller_payload(row)


def test_evidence_mirror_does_not_change_output_key_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_dir = tmp_path / "active"
    baseline_dir = tmp_path / "baseline"
    active_outcome, _active_harness, active_log = _run_case(
        active_dir,
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
        "record_final_evidence_snapshot",
        noop_record,
    )
    baseline_outcome, _baseline_harness, baseline_log = _run_case(
        baseline_dir,
        query="What are the current eligibility requirements for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

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

    active_row = execution_jsonl_to_run_row(active_log)
    baseline_row = execution_jsonl_to_run_row(baseline_log)
    assert active_row is not None
    assert baseline_row is not None
    assert set(active_row) == set(baseline_row)
    assert "execution_trace" not in active_row


def test_evidence_registry_mirror_static_import_guard() -> None:
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
        "decide_",
        "finalize_",
        "rank_",
        "recover_",
        "retrieve_",
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
