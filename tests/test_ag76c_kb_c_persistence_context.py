from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.review_flags import ReviewFlags

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "core" / "kb_review_persistence_context.py"
PERSISTENCE_PATH = ROOT / "core" / "persistence_side_effects.py"
ORCHESTRATOR_PATH = ROOT / "core" / "pipeline_orchestrator.py"
DB_PATH = ROOT / "core" / "db.py"
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


def _sentinel(*_args: Any, **_kwargs: Any) -> None:
    return None


def _kb_context(helper: Any, tmp_path: Path, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "feedback_log_path": tmp_path / "feedback.jsonl",
        "kb_triggers_path": tmp_path / "kb.jsonl",
        "session_id": "sess-1",
        "run_id": "run-1",
        "query": "Q" * 250,
        "report_type": "standard",
        "query_type": "news",
        "primary_entity": "E" * 250,
        "entities_list": ["Entity", "X" * 250, 7],
        "empty_entity_flag": False,
        "router_entity_retry_used": True,
        "utilization_pre_retry": 0.2,
        "utilization_rate_val": 0.4,
        "retrieval_retry_used": True,
        "corpus_state": "HEALTHY",
        "corpus_state_forced_flag": False,
        "corpus_weak": False,
        "useful_content": True,
        "response_displayable": True,
        "evidence_sufficient": True,
        "answer_class": "answer",
        "useful_content_reason": "ok",
        "waste_flags": ["query_redundancy_skipped", "other"],
        "recon_fired": True,
        "recon_confidence": 0.8,
        "canonical_subject_resolved": "C" * 250,
        "timing_payload": {"total": 1.5, "nested": {"kept": True}},
        "strategy": "Balanced",
        "fast_model": "fast-model",
        "smart_model": "smart-model",
        "complexity": "medium",
        "intent": "news",
        "iterations_run": 2,
        "providers_by_iteration": [
            {"providers": ["provider-a", "provider-b"]},
            {"provider": "provider-a"},
            "provider-c",
        ],
        "queries_per_iter": {1: ["q1"], 2: ["q2"]},
        "queries_by_iteration": {1: ["q1", "q1b"], 2: ["q2"]},
        "disambiguation_queries_per_iter": {1: ["dq1"]},
        "weak_corpus_recovery_considered": True,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": "not-needed",
        "weak_corpus_recovery_queries": ["wq"],
        "weak_corpus_recovery_decision": "skip",
        "weak_corpus_recovery_reason": "healthy",
        "weak_corpus_recovery_blockers": ["budget"],
        "scout_fired": True,
        "scout_key_used": "scout-key",
        "scout_queries": ["sq"],
        "synth_was_insufficient": False,
        "synth_sufficient_first_pass_raw": "yes",
        "synth_sufficient_first_pass": True,
        "failure_card_payload": {"show": False},
        "supplemental_ran": True,
        "delta_urls_supplemental": 3,
        "total_chunks_embedded": 21,
        "seen_urls": ["https://one.test", "https://two.test"],
        "scrutineer_high_count": 0,
        "scrutineer_flag_count": 1,
        "synth_deficiency": "none",
        "latency_seconds": 2.5,
        "output_word_count": 42,
        "report": "R" * 350,
        "cost_snapshot": {"total": 0.01, "by_model": {"fast": 0.01}},
        "ask_model": _sentinel,
        "clean_json_response": _sentinel,
        "fast_provider": "provider-a",
        "local_url": "http://local.test",
        "or_api_key": "api-key",
        "kb_review_agent": _sentinel,
    }
    values.update(overrides)
    return helper.KbReviewPersistenceContext(**values)


def test_kb_c_orchestrator_delegates_context_construction_without_registry_import() -> None:
    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "build_kb_review_persistence_context(" in source
    assert "KbReviewPersistenceContext(" not in source
    assert "feedback_log_path=feedback_log_path" not in source
    assert "kb_review_agent=kb_review_agent" in source
    assert "pipeline_decision_registry" not in source


def test_kb_execution_record_exact_parity_for_legacy_fields_and_copies(tmp_path: Path) -> None:
    import core.kb_review_persistence_context as helper

    context = _kb_context(helper, tmp_path)
    record = helper.build_kb_execution_record(context)

    expected = {
        "run_id": "run-1",
        "session_id": "sess-1",
        "query": "Q" * 200,
        "report_type": "standard",
        "query_type": "news",
        "primary_entity": "E" * 200,
        "entities": ["Entity", "X" * 200, "7"],
        "empty_entity": False,
        "router_entity_retry_used": True,
        "utilization_pre_retry": 0.2,
        "utilization_rate": 0.4,
        "retrieval_retry_used": True,
        "corpus_state": "HEALTHY",
        "corpus_state_forced": False,
        "corpus_weak": False,
        "useful_content": True,
        "response_displayable": True,
        "evidence_sufficient": True,
        "answer_class": "answer",
        "useful_content_reason": "ok",
        "waste_flags": ["query_redundancy_skipped", "other"],
        "query_redundancy_skipped": True,
        "recon_fired": True,
        "recon_confidence": 0.8,
        "canonical_subject_resolved": "C" * 200,
        "timing": {"total": 1.5, "nested": {"kept": True}},
        "mode": "Balanced",
        "fast_model": "fast-model",
        "smart_model": "smart-model",
        "complexity": "medium",
        "intent": "news",
        "iterations_run": 2,
        "pass_providers": context.providers_by_iteration,
        "queries_per_iteration": context.queries_per_iter,
        "queries_iter1": ["q1", "q1b"],
        "queries_iter2": ["q2"],
        "disambiguation_queries_by_iteration": {1: ["dq1"]},
        "weak_corpus_recovery_considered": True,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": "not-needed",
        "weak_corpus_recovery_queries": ["wq"],
        "weak_corpus_recovery_decision": "skip",
        "weak_corpus_recovery_reason": "healthy",
        "weak_corpus_recovery_blockers": ["budget"],
        "scout_fired": True,
        "scout_key": "scout-key",
        "scout_queries": ["sq"],
        "synth_was_insufficient": False,
        "synth_sufficient_first_pass_raw": "yes",
        "synth_sufficient_first_pass": True,
        "failure_card": {"show": False},
        "supplemental_ran": True,
        "delta_urls_supplemental": 3,
        "total_chunks_embedded": 21,
        "urls_fetched": 2,
        "scrutineer_high_flags": 0,
        "scrutineer_flag_count": 1,
        "synth_deficiency": "none",
        "latency_seconds": 2.5,
        "output_word_count": 42,
        "final_output_preview": "R" * 300,
        "cost": {"total": 0.01, "by_model": {"fast": 0.01}},
    }
    assert record == expected
    assert record["waste_flags"] is not context.waste_flags
    assert record["timing"] is not context.timing_payload
    assert record["weak_corpus_recovery_queries"] is not context.weak_corpus_recovery_queries


def test_kb_trigger_entry_exact_parity_with_frozen_timestamp(tmp_path: Path) -> None:
    import core.kb_review_persistence_context as helper

    context = _kb_context(helper, tmp_path)
    execution_record = helper.build_kb_execution_record(context)
    flags = ReviewFlags(synth_insufficient=True, high_scrutineer_severity=True)
    entry = helper.build_kb_trigger_entry(
        context=context,
        flags_obj=flags,
        score_val=0.3,
        review_f=True,
        execution_record=execution_record,
        timestamp_utc="2026-05-30T00:00:00+00:00",
    )

    expected = {
        "synth_insufficient": True,
        "low_user_rating": False,
        "scout_misfire": False,
        "remediation_ineffective": False,
        "linkup_tavily_misroute_news": False,
        "query_redundancy": False,
        "low_evidence_yield": False,
        "high_scrutineer_severity": True,
        "synth_declined_with_evidence": False,
        "weak_retrieval_failure_card": False,
        "event": "kb_trigger",
        "run_id": "run-1",
        "session_id": "sess-1",
        "query": "Q" * 200,
        "report_type": "standard",
        "mode": "Balanced",
        "synth_deficiency": "none",
        "score": 0.3,
        "fired": True,
        "timestamp_utc": "2026-05-30T00:00:00+00:00",
        "retrieval_yield_chunks": 21,
        "providers_used": ["provider-a", "provider-b", "provider-c"],
        "timing": {"total": 1.5, "nested": {"kept": True}},
    }
    assert entry == expected
    assert entry["timing"] is not execution_record["timing"]


@pytest.mark.parametrize("review_f, expected_calls", [(False, 0), (True, 1)])
def test_agent_call_guard_and_positional_argument_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    review_f: bool,
    expected_calls: int,
) -> None:
    import core.kb_review_persistence_context as helper
    import core.persistence_side_effects as persistence

    agent_calls: list[tuple[Any, ...]] = []

    def fake_agent(*args: Any) -> dict[str, Any]:
        agent_calls.append(args)
        return {"ok": True}

    context = _kb_context(helper, tmp_path, kb_review_agent=fake_agent)
    appended: list[dict[str, Any]] = []
    monkeypatch.setattr(persistence, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(persistence, "compute_review_flags", lambda _execution, _feedback: ReviewFlags())
    monkeypatch.setattr(persistence, "review_score", lambda _flags: 0.55)
    monkeypatch.setattr(persistence, "should_auto_review", lambda _flags: review_f)
    monkeypatch.setattr(
        persistence,
        "append_jsonl",
        lambda _path, payload, *, logger: appended.append(dict(payload)),
    )

    instrumentation, _warning = persistence._append_kb_trigger_review(
        context=context,
        run_log=RecordingLogger(),
    )

    assert len(agent_calls) == expected_calls
    assert instrumentation == {"score": 0.55, "fired": review_f, "agent_ran": review_f}
    if review_f:
        trigger_entry = appended[0]
        execution_record = agent_calls[0][3]
        assert agent_calls[0] == (
            context.ask_model,
            context.clean_json_response,
            trigger_entry,
            execution_record,
            context.report,
            context.fast_provider,
            context.fast_model,
            context.local_url,
            context.or_api_key,
        )
        assert trigger_entry["kb_review"] == {"ok": True}


def test_kb_warning_parity_truncates_likely_recurring_detail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.kb_review_persistence_context as helper
    import core.persistence_side_effects as persistence

    detail = "D" * 600
    context = _kb_context(
        helper,
        tmp_path,
        kb_review_agent=lambda *_args: {
            "recurrence_risk": "likely-recurring",
            "suggested_action": {"detail": detail},
        },
    )
    monkeypatch.setattr(persistence, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(persistence, "compute_review_flags", lambda _execution, _feedback: ReviewFlags())
    monkeypatch.setattr(persistence, "review_score", lambda _flags: 0.55)
    monkeypatch.setattr(persistence, "should_auto_review", lambda _flags: True)
    monkeypatch.setattr(persistence, "append_jsonl", lambda *_args, **_kwargs: None)

    _instrumentation, warning = persistence._append_kb_trigger_review(
        context=context,
        run_log=RecordingLogger(),
    )

    assert warning == "D" * 500


def test_kb_agent_exception_remains_non_fatal_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.kb_review_persistence_context as helper
    import core.persistence_side_effects as persistence

    logger = RecordingLogger()

    def boom(*_args: Any) -> None:
        raise RuntimeError("agent boom")

    context = _kb_context(helper, tmp_path, kb_review_agent=boom)
    monkeypatch.setattr(persistence, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(persistence, "compute_review_flags", lambda _execution, _feedback: ReviewFlags())
    monkeypatch.setattr(persistence, "review_score", lambda _flags: 0.55)
    monkeypatch.setattr(persistence, "should_auto_review", lambda _flags: True)

    instrumentation, warning = persistence._append_kb_trigger_review(
        context=context,
        run_log=logger,
    )

    assert instrumentation is None
    assert warning is None
    assert any("Non-fatal KB review logging" in item for item in logger.warnings)


def test_ordering_and_sqlite_handoff_see_kb_instrumentation_before_row_conversion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import core.kb_review_persistence_context as helper
    import core.persistence_side_effects as persistence

    calls: list[str] = []
    seen_by_sqlite: list[dict[str, Any]] = []
    logger = RecordingLogger()

    monkeypatch.setattr(
        persistence,
        "append_jsonl",
        lambda path, _payload, *, logger: calls.append(f"append:{path.name}"),
    )
    monkeypatch.setattr(
        persistence,
        "log_run_completed",
        lambda **kwargs: calls.append("completed"),
    )
    monkeypatch.setattr(persistence, "load_feedback_for_session", lambda _path, _sid: {})
    monkeypatch.setattr(persistence, "compute_review_flags", lambda _execution, _feedback: ReviewFlags())
    monkeypatch.setattr(persistence, "review_score", lambda _flags: 0.15)
    monkeypatch.setattr(persistence, "should_auto_review", lambda _flags: False)

    def fake_row(entry: dict[str, Any]) -> dict[str, Any]:
        calls.append("sqlite-row")
        seen_by_sqlite.append(dict(entry))
        return {}

    monkeypatch.setattr(persistence, "build_sqlite_row_payload", fake_row)

    execution_log_entry = {"event": "execution", "run_id": "run-1"}
    result = persistence.execute_persistence_side_effects(
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
        db_enabled=True,
    )

    assert calls == [
        "append:execution.jsonl",
        "completed",
        "append:policy.jsonl",
        "append:kb.jsonl",
        "sqlite-row",
    ]
    assert seen_by_sqlite[0]["kb_instrumentation"] == result.kb_instrumentation
    assert execution_log_entry["kb_instrumentation"] == result.kb_instrumentation


def test_kb_c_helper_has_no_protected_behavior_imports() -> None:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    banned_fragments = (
        "provider",
        "search",
        "routing",
        "prompts",
        "author",
        "final_evidence",
        "citation",
        "classifier",
        "candidate_fit",
        "pipeline",
    )
    assert not [
        module
        for module in sorted(imported_modules)
        if any(fragment in module.casefold() for fragment in banned_fragments)
    ]


def test_no_schema_drift_guard_for_db_packaging_and_persistence_surfaces() -> None:
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    persistence_source = PERSISTENCE_PATH.read_text(encoding="utf-8")
    packaging_source = PACKAGING_PATH.read_text(encoding="utf-8")
    db_source = DB_PATH.read_text(encoding="utf-8")

    assert "RUN_COLUMNS" not in helper_source
    assert "CREATE TABLE" not in helper_source
    assert "insert_run(" not in helper_source
    assert "upsert_session(" not in helper_source
    assert "build_run_outcome(" not in persistence_source
    assert "kb_instrumentation=kb_instrumentation" in packaging_source
    assert "kb_instrumentation" in db_source
