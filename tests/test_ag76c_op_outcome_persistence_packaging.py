from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from core.db import RUN_COLUMNS
from core.run_config import RunOutcome

HELPER_PATH = Path("core/outcome_persistence_packaging.py")
ORCHESTRATOR_PATH = Path("core/pipeline_orchestrator.py")
RT_HELPER_PATH = Path("core/runtime_trace_export_attachment.py")


def _sample_execution_facts() -> dict[str, Any]:
    execution_trace = {
        "analyst_skipped": True,
        "analyst_skip_reason": "trace reason",
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": None,
        "economist_output_used_as_analysis": True,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": ["trace-signal"],
        "timing": {"author_seconds": 1.2},
    }
    return {
        "current_date": "2026-05-30",
        "ts_utc": "2026-05-30T00:00:00+00:00",
        "run_id": "run-1",
        "session_id": "session-1",
        "query": "What happened in a very long query?" * 8,
        "intent": "informational",
        "query_type": "general",
        "primary_entity": "Primary Entity" * 30,
        "entities_list": ["Entity A", "Entity B"],
        "empty_entity_flag": False,
        "router_entity_retry_used": True,
        "utilization_pre_retry": 0.1,
        "utilization_rate_val": 0.6,
        "retrieval_retry_used": False,
        "corpus_state": "strong",
        "corpus_state_forced_flag": False,
        "corpus_weak": False,
        "useful_content": True,
        "response_displayable": True,
        "evidence_sufficient": True,
        "answer_class": "answer",
        "useful_content_reason": "enough",
        "waste_flags": ["query_redundancy_skipped"],
        "recon_fired": True,
        "recon_confidence": "high",
        "canonical_subject_resolved": "Canonical Subject",
        "timing_payload": {"author_seconds": 1.2},
        "router_original_report_type": "brief",
        "router_original_query_type": "original",
        "routing_override_applied": False,
        "routing_override_reason": None,
        "report_type": "brief",
        "nutrition_lookup_telemetry": {"nutrition_lookup_used": False},
        "complexity": "medium",
        "mode": "Balanced",
        "fast_model": "fast",
        "smart_model": "smart",
        "scout_fired": False,
        "scout_key_used": None,
        "scout_queries": ["q1"],
        "scout_skip_reason": "not_needed",
        "iterations_run": 2,
        "total_chunks_embedded": 3,
        "total_urls_fetched": 4,
        "providers_by_iteration": ["provider-a"],
        "provider_diagnostics_payload": {"provider_diagnostics": []},
        "queries_per_iter": {"1": ["q1"]},
        "disambiguation_queries_per_iter": {"1": []},
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": "not_weak_corpus",
        "weak_corpus_recovery_queries": [],
        "weak_corpus_recovery_decision": None,
        "weak_corpus_recovery_reason": None,
        "weak_corpus_recovery_blockers": [],
        "synth_sufficient_first_pass_raw": True,
        "synth_sufficient_first_pass": True,
        "scrutineer_flag_count": 0,
        "estimate_from_priors_requested": False,
        "estimate_from_priors_blocked_by_pre_analyst_gate": False,
        "economist_ran": False,
        "economist_preflight_allowed": False,
        "economist_preflight_block_reason": "not_quant",
        "economist_preflight_missing_entities": [],
        "economist_safety_telemetry": {"economist_safe": True},
        "quant_retrieval_sufficiency_telemetry": {"quant_ok": True},
        "missing_target_metric_directive_emitted": False,
        "economist_pre_analyst_skip_candidate_telemetry": {"skip_candidate": False},
        "analyst_quant_packet_handoff_telemetry": {"analyst_packet": None},
        "author_quant_source_telemetry": {"author_quant_sources": []},
        "author_system_prompt_key": "default",
        "final_answer_source_telemetry": {"final_answer_source_ids_used": ["s1"]},
        "economist_skip_eligibility_shadow_telemetry": {"economist_skip_shadow": False},
        "economist_skip_shadow_alignment": "aligned",
        "analyst_skipped": False,
        "analyst_skip_reason": "local reason",
        "analyst_skipped_after_economist": True,
        "analyst_after_economist_skip_reason": "local post reason",
        "economist_output_used_as_analysis": False,
        "post_retrieval_fast_path_used": True,
        "pre_analyst_gate_signals": ["local-signal"],
        "scrutineer_ran": True,
        "synth_was_insufficient": False,
        "supplemental_ran": False,
        "report": "Final answer body with citations.",
        "latency_seconds": 9.5,
        "cost_snapshot": {"total_cost": 0.12},
        "source_class_recovery_validation_trace_key": "source_class_recovery_validation",
        "source_class_recovery_validation_packet": {"valid": True},
        "execution_trace": execution_trace,
    }


def test_ag76c_op_session_payload_shape_matches_legacy_keys() -> None:
    from core.outcome_persistence_packaging import build_pipeline_config, build_session_payload

    pipeline_config = build_pipeline_config(
        intent="informational", complexity="medium", search_depth=2, mode="Balanced"
    )
    payload = build_session_payload(
        session_id="session-1",
        run_id="run-1",
        session_title="Title",
        current_date="2026-05-30",
        query="Query",
        core_topic="Topic",
        report="Report",
        final_top_evidence=[{"id": "p1"}],
        seen_urls=["https://example.test"],
        collected_images=["image.png"],
        mode="Balanced",
        pipeline_config=pipeline_config,
        run_history_out=[{"run": 1}],
        failure_card_payload={"show": False},
    )

    assert list(payload) == [
        "id",
        "run_id",
        "title",
        "timestamp",
        "query",
        "core_topic",
        "report",
        "top_passages",
        "chat_messages",
        "seen_urls",
        "collected_images",
        "last_report_mode",
        "pipeline_config",
        "run_history",
        "failure_card",
    ]
    assert payload["pipeline_config"] == {
        "intent": "informational",
        "complexity": "medium",
        "search_depth": 2,
        "mode": "Balanced",
    }


def test_ag76c_op_execution_jsonl_and_sqlite_row_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.outcome_persistence_packaging as helper

    monkeypatch.setattr(
        helper,
        "current_code_version_metadata",
        lambda: {"code_version": "test-version", "git_commit": "abc123"},
    )
    entry = helper.build_execution_log_entry(**_sample_execution_facts())

    assert entry["event"] == "execution"
    assert entry["query"] == _sample_execution_facts()["query"][:100]
    assert entry["output_word_count"] == 5
    assert entry["final_output_preview"] == "Final answer body with citations."
    assert entry["source_class_recovery_validation"] == {"valid": True}
    assert entry["analyst_skipped"] is True
    assert entry["analyst_skip_reason"] == "trace reason"
    assert entry["pre_analyst_gate_signals"] == ["trace-signal"]
    assert entry["code_version"] == "test-version"
    assert entry["git_commit"] == "abc123"

    row = helper.build_sqlite_row_payload(entry)
    assert row is not None
    assert set(row) == set(RUN_COLUMNS)
    assert row["run_id"] == "run-1"
    assert row["session_id"] == "session-1"
    assert row["output_word_count"] == 5
    assert row["final_output_preview"] == "Final answer body with citations."


def test_ag76c_op_run_outcome_fields_and_final_metadata() -> None:
    from core.outcome_persistence_packaging import build_final_output_metadata, build_run_outcome

    session = {"id": "session-1"}
    trace = {"trace": True}
    metadata = build_final_output_metadata(
        report="one two three", latency_seconds=1.5, cost_snapshot={"total_cost": 0.01}
    )
    outcome = build_run_outcome(
        session_id="session-1",
        run_id="run-1",
        session_title="Title",
        query="Query",
        core_topic="Topic",
        report="one two three",
        final_top_evidence=[{"id": "p1"}],
        seen_urls=["u"],
        collected_images=["i"],
        execution_trace=trace,
        failure_card_payload={"show": False},
        session_payload=session,
        cost_snapshot={"total_cost": 0.01},
        latency_seconds=1.5,
        intent="informational",
        complexity="medium",
        corpus_state="strong",
        pipeline_config={"intent": "informational", "complexity": "medium", "search_depth": 2, "mode": "Balanced"},
        kb_instrumentation={"fired": False},
        kb_warning="warning",
        author_streamed=True,
    )

    assert metadata == {
        "latency_seconds": 1.5,
        "output_word_count": 3,
        "final_output_preview": "one two three",
        "cost": {"total_cost": 0.01},
    }
    assert isinstance(outcome, RunOutcome)
    assert {field.name for field in fields(RunOutcome)} == set(outcome.__dict__)
    assert outcome.new_session is session
    assert outcome.execution_trace is trace
    assert outcome.pipeline_config["mode"] == "Balanced"
    assert outcome.author_streamed is True


def test_ag76c_op_helper_has_no_protected_behavior_imports() -> None:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    banned_fragments = (
        "core.search_providers",
        "core.provider_diagnostics",
        "core.prompts",
        "core.routing",
        "core.run_author",
        "core.answer_contract_runtime_handoff",
        "core.final_evidence_bundle_builder",
        "core.source_class_recovery",
        "core.candidate_fit",
    )
    assert not [
        module
        for module in sorted(imported_modules)
        if any(fragment in module for fragment in banned_fragments)
    ]


def test_ag76c_op_orchestrator_delegates_packaging_and_rt_attachment() -> None:
    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    rt_helper_source = RT_HELPER_PATH.read_text(encoding="utf-8")

    assert "build_session_payload(" in source
    assert "build_execution_log_entry(" in source
    assert "build_sqlite_row_payload(" in source
    assert "build_run_outcome(" in source
    assert "return RunOutcome(" not in source
    assert '"event": "execution"' not in source
    assert "execution_jsonl_to_run_row(" not in source
    assert "attach_runtime_trace_export_compatibility_payloads(" in source
    assert "attach_passive_runtime_projection_traces(" not in source
    assert "build_retrieval_budget_pressure_shadow(" not in source
    assert "build_source_class_recovery_candidate_v2(" not in source
    assert "def attach_runtime_trace_export_compatibility_payloads" in rt_helper_source
    assert "execution_jsonl_to_run_row" in helper_source
