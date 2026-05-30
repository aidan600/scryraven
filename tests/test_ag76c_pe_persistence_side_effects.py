from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.review_flags import ReviewFlags

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "core" / "persistence_side_effects.py"
ORCHESTRATOR_PATH = ROOT / "core" / "pipeline_orchestrator.py"
PACKAGING_PATH = ROOT / "core" / "outcome_persistence_packaging.py"


class RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def warning(self, message: str, *args: object) -> None:
        self.warnings.append(message % args if args else message)

    def error(self, message: str, *args: object) -> None:
        self.errors.append(message % args if args else message)

    def info(self, *_args: object, **_kwargs: object) -> None:
        return None


def _kb_context(helper: Any, tmp_path: Path, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "feedback_log_path": tmp_path / "feedback.jsonl",
        "kb_triggers_path": tmp_path / "kb.jsonl",
        "session_id": "sess-1",
        "run_id": "run-1",
        "query": "What happened?",
        "report_type": "standard",
        "query_type": "news",
        "primary_entity": "Entity",
        "entities_list": ["Entity"],
        "empty_entity_flag": False,
        "router_entity_retry_used": False,
        "utilization_pre_retry": 0.2,
        "utilization_rate_val": 0.4,
        "retrieval_retry_used": False,
        "corpus_state": "HEALTHY",
        "corpus_state_forced_flag": False,
        "corpus_weak": False,
        "useful_content": True,
        "response_displayable": True,
        "evidence_sufficient": True,
        "answer_class": "answer",
        "useful_content_reason": "ok",
        "waste_flags": [],
        "recon_fired": False,
        "recon_confidence": None,
        "canonical_subject_resolved": None,
        "timing_payload": {"total": 1.5},
        "strategy": "Balanced",
        "fast_model": "fast",
        "smart_model": "smart",
        "complexity": "medium",
        "intent": "news",
        "iterations_run": 1,
        "providers_by_iteration": [{"providers": ["provider-a"]}],
        "queries_per_iter": {1: ["q1"]},
        "queries_by_iteration": {1: ["q1"], 2: ["q2"]},
        "disambiguation_queries_per_iter": {},
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": None,
        "weak_corpus_recovery_queries": [],
        "weak_corpus_recovery_decision": None,
        "weak_corpus_recovery_reason": None,
        "weak_corpus_recovery_blockers": [],
        "scout_fired": False,
        "scout_key_used": None,
        "scout_queries": [],
        "synth_was_insufficient": False,
        "synth_sufficient_first_pass_raw": True,
        "synth_sufficient_first_pass": True,
        "failure_card_payload": None,
        "supplemental_ran": False,
        "delta_urls_supplemental": 0,
        "total_chunks_embedded": 20,
        "seen_urls": ["https://example.test"],
        "scrutineer_high_count": 0,
        "scrutineer_flag_count": 0,
        "synth_deficiency": None,
        "latency_seconds": 2.5,
        "output_word_count": 42,
        "report": "final report",
        "cost_snapshot": {"total": 0.01},
        "ask_model": lambda *args, **kwargs: None,
        "clean_json_response": lambda value: value,
        "fast_provider": "provider-a",
        "local_url": None,
        "or_api_key": None,
        "kb_review_agent": lambda *args, **kwargs: None,
    }
    values.update(overrides)
    return helper.KbReviewPersistenceContext(**values)


def test_execute_persistence_side_effects_preserves_write_order_and_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.persistence_side_effects as helper

    calls: list[tuple[str, Any]] = []
    logger = RecordingLogger()
    execution_log_entry = {"event": "execution", "run_id": "run-1"}

    def fake_append(path: Path, payload: dict[str, Any], *, logger: Any) -> None:
        calls.append(("append", path.name, dict(payload)))

    monkeypatch.setattr(helper, "append_jsonl", fake_append)
    monkeypatch.setattr(
        helper,
        "log_run_completed",
        lambda **kwargs: calls.append(("completed", kwargs["path"].name, kwargs["timing"])),
    )
    monkeypatch.setattr(
        helper,
        "apply_policy_to_run_config",
        lambda config, _overrides: dict(config),
    )
    monkeypatch.setattr(helper, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(
        helper,
        "compute_review_flags",
        lambda execution, feedback: ReviewFlags(synth_insufficient=True),
    )
    monkeypatch.setattr(helper, "review_score", lambda flags: 0.15)
    monkeypatch.setattr(helper, "should_auto_review", lambda flags: False)

    result = helper.execute_persistence_side_effects(
        execution_log_path=tmp_path / "execution.jsonl",
        execution_log_entry=execution_log_entry,
        run_id="run-1",
        session_id="sess-1",
        latency_seconds=2.5,
        strategy="Balanced",
        execution_trace={"timing": {"total": 2.5}},
        run_log=logger,
        policy_journal_path=tmp_path / "policy.jsonl",
        policy_applied={"utilization_threshold": 0.25},
        default_utilization_threshold=0.25,
        ts_utc="2026-05-30T00:00:00+00:00",
        query="What happened?",
        kb_context=_kb_context(helper, tmp_path),
        db_enabled=False,
    )

    assert [call[0:2] for call in calls] == [
        ("append", "execution.jsonl"),
        ("completed", "execution.jsonl"),
        ("append", "policy.jsonl"),
        ("append", "kb.jsonl"),
    ]
    assert calls[0][2] == {"event": "execution", "run_id": "run-1"}
    assert calls[2][2]["event"] == "policy_applied"
    assert calls[3][2]["event"] == "kb_trigger"
    assert calls[3][2]["providers_used"] == ["provider-a"]
    assert result.kb_instrumentation == {
        "score": 0.15,
        "fired": False,
        "agent_ran": False,
    }
    assert execution_log_entry["kb_instrumentation"] == result.kb_instrumentation
    assert result.sqlite_row_written is False
    assert logger.warnings == []
    assert logger.errors == []


def test_execute_persistence_side_effects_preserves_non_fatal_policy_kb_and_db_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.persistence_side_effects as helper

    calls: list[str] = []
    logger = RecordingLogger()

    def fake_append(path: Path, payload: dict[str, Any], *, logger: Any) -> None:
        calls.append(path.name)
        if path.name == "policy.jsonl":
            raise RuntimeError("policy boom")

    monkeypatch.setattr(helper, "append_jsonl", fake_append)
    monkeypatch.setattr(helper, "log_run_completed", lambda **kwargs: calls.append("completed"))
    monkeypatch.setattr(helper, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(
        helper,
        "compute_review_flags",
        lambda _execution, _feedback: (_ for _ in ()).throw(RuntimeError("kb boom")),
    )
    monkeypatch.setattr(helper, "build_sqlite_row_payload", lambda entry: {"run_id": "run-1"})
    monkeypatch.setattr(helper, "ensure_telemetry_schema", lambda: tmp_path / "telemetry.db")
    monkeypatch.setattr(
        helper.sqlite3,
        "connect",
        lambda _path: (_ for _ in ()).throw(RuntimeError("db boom")),
    )

    result = helper.execute_persistence_side_effects(
        execution_log_path=tmp_path / "execution.jsonl",
        execution_log_entry={"event": "execution", "run_id": "run-1"},
        run_id="run-1",
        session_id="sess-1",
        latency_seconds=2.5,
        strategy="Balanced",
        execution_trace={"timing": {"total": 2.5}},
        run_log=logger,
        policy_journal_path=tmp_path / "policy.jsonl",
        policy_applied={"utilization_threshold": 0.3},
        default_utilization_threshold=0.25,
        ts_utc="2026-05-30T00:00:00+00:00",
        query="What happened?",
        kb_context=_kb_context(helper, tmp_path),
        db_enabled=True,
    )

    assert calls == ["execution.jsonl", "completed", "policy.jsonl"]
    assert result.kb_instrumentation is None
    assert result.kb_warning is None
    assert result.sqlite_row_written is False
    assert any("Non-fatal policy journaling failure" in item for item in logger.warnings)
    assert any("Non-fatal KB review logging" in item for item in logger.warnings)
    assert any("Failed to write telemetry to DB" in item for item in logger.errors)


def test_sqlite_writes_are_gated_and_ordered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import core.persistence_side_effects as helper

    calls: list[str] = []
    logger = RecordingLogger()

    class FakeConn:
        def commit(self) -> None:
            calls.append("commit")

        def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(helper, "build_sqlite_row_payload", lambda entry: {"session_id": "sess-1", "timestamp_utc": "ts"})
    monkeypatch.setattr(helper, "ensure_telemetry_schema", lambda: calls.append("ensure") or tmp_path / "telemetry.db")
    monkeypatch.setattr(helper.sqlite3, "connect", lambda _path: calls.append("connect") or FakeConn())
    monkeypatch.setattr(helper, "insert_run", lambda row, *, conn: calls.append("insert"))
    monkeypatch.setattr(helper, "upsert_session", lambda session_id, timestamp_utc, *, conn: calls.append("upsert"))

    assert helper._write_sqlite_telemetry(
        execution_log_entry={"event": "execution"},
        db_enabled=False,
        run_log=logger,
    ) is False
    assert calls == []

    assert helper._write_sqlite_telemetry(
        execution_log_entry={"event": "execution"},
        db_enabled=True,
        run_log=logger,
    ) is True
    assert calls == ["ensure", "connect", "insert", "upsert", "commit", "close"]


def test_ag76c_pe_helper_has_no_protected_behavior_imports() -> None:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    banned_fragments = (
        "core.search_providers",
        "core.prompts",
        "core.routing",
        "core.run_author",
        "core.answer_contract_runtime_handoff",
        "core.final_evidence_bundle_builder",
        "core.source_classifier",
        "core.candidate_fit",
        "core.pipeline",
    )
    assert not [
        module
        for module in sorted(imported_modules)
        if any(fragment in module for fragment in banned_fragments)
    ]


def test_ag76c_pe_orchestrator_delegates_side_effects_and_packaging_stays_packaging_only() -> None:
    orchestrator_source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    packaging_source = PACKAGING_PATH.read_text(encoding="utf-8")

    assert "execute_persistence_side_effects(" in orchestrator_source
    assert "build_kb_review_persistence_context(" in orchestrator_source
    assert "KbReviewPersistenceContext(" not in orchestrator_source
    assert "append_jsonl(\n        execution_log_path" not in orchestrator_source
    assert "log_run_completed(\n        run_id=run_id" not in orchestrator_source
    assert "insert_run(row" not in orchestrator_source
    assert "upsert_session(" not in orchestrator_source
    assert "sqlite3.connect" not in orchestrator_source
    assert "Non-fatal KB review logging" not in orchestrator_source
    assert "Non-fatal policy journaling failure" not in orchestrator_source

    assert "append_jsonl" not in packaging_source
    assert "log_run_completed" not in packaging_source
    assert "insert_run(" not in packaging_source
    assert "upsert_session(" not in packaging_source
    assert "sqlite3.connect" not in packaging_source
