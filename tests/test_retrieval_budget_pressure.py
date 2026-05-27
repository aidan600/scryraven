from __future__ import annotations

from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import execution_jsonl_to_run_row
from core.retrieval_budget_pressure import (
    SCHEMA_VERSION,
    build_retrieval_budget_pressure_shadow,
)
from tests.test_retrieval_stop_shadow import (
    _assert_active_stop_budget_exhausted,
    _assert_active_stop_no_queries,
    _run_case,
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


def _budget_trace(**updates: Any) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "mode": "Fast",
        "iterations_run": 1,
        "queries_per_iteration": {"1": ["synthetic query"]},
        "retrieval_stop_shadow_decision": "stop_budget_exhausted",
        "retrieval_stop_shadow_reason": "iteration_budget_exhausted",
        "retrieval_stop_shadow_next_query_count": 0,
        "retrieval_stop_shadow_stage": "iteration_budget_exhausted",
        "retrieval_stop_active_decision": "stop_budget_exhausted",
        "retrieval_stop_active_reason": "iteration_budget_exhausted",
        "cost": {"total_cost_usd": 0.012345, "total_calls": 3},
        "provider_diagnostics": [
            {
                "schema_version": "provider_diagnostics_v1",
                "provider": "tavily",
                "provider_role": "main_retrieval",
                "iteration": 1,
                "logical_attempt_count": 1,
                "new_source_count": 2,
                "new_domain_count": 1,
                "accepted_url_count": 2,
                "accepted_url_overlap_count": 0,
                "query_similarity_max": 0.1,
            }
        ],
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_query_count": 2,
        "official_evidence_found": False,
        "community_signal_found": False,
        "quant_retrieval_target_detected": False,
        "quant_retrieval_metric_coverage_valid": False,
        "corpus_state": "HEALTHY",
        "pre_analyst_gate_signals": ["missing_expected_official_evidence"],
        "weak_corpus_recovery_used": False,
        "final_answer_source_ids_used": ["1"],
        "answer_class": "partial_answer",
    }
    trace.update(updates)
    return trace


def test_budget_pressure_helper_marks_budget_exhausted_candidate() -> None:
    payload = build_retrieval_budget_pressure_shadow(
        trace=_budget_trace(),
        max_iterations=1,
        final_top_evidence=[
            {"source_id": 1, "source_tier": "secondary"},
        ],
    )

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["shadow_mode"] is True
    assert payload["hard_mode_budget"]["budget_stop_triggered"] is True
    assert payload["hard_mode_budget"]["budget_pressure_bucket"] == "exhausted"
    assert (
        payload["extra_pass_judgment"]["extra_pass_candidate_shadow"] is True
    )
    assert (
        payload["answer_quality_impact"]["budget_limited_answer_shadow"] is True
    )


def test_budget_pressure_helper_marks_balanced_sufficient_negative() -> None:
    trace = _budget_trace(
        mode="Balanced",
        iterations_run=1,
        retrieval_stop_shadow_decision="proceed_to_synthesis",
        retrieval_stop_shadow_reason="evaluator_sufficient",
        retrieval_stop_shadow_stage="evaluator",
        retrieval_stop_active_decision=None,
        retrieval_stop_active_reason=None,
        missing_expected_source_classes=[],
        source_class_recovery_query_count=0,
        official_evidence_found=True,
        community_signal_found=True,
        quant_retrieval_target_detected=True,
        quant_retrieval_metric_coverage_valid=True,
        answer_class="answered",
    )
    payload = build_retrieval_budget_pressure_shadow(
        trace=trace,
        max_iterations=2,
        final_top_evidence=[
            {"source_id": 1, "source_tier": "official"},
        ],
    )

    assert (
        payload["extra_pass_judgment"]["extra_pass_candidate_shadow"] is False
    )
    assert (
        payload["answer_quality_impact"]["budget_limited_answer_shadow"] is False
    )
    assert "evaluator_sufficient" in payload["extra_pass_judgment"][
        "extra_pass_candidate_blockers"
    ]


def test_budget_pressure_helper_blocks_weak_corpus_recovery_completed() -> None:
    payload = build_retrieval_budget_pressure_shadow(
        trace=_budget_trace(weak_corpus_recovery_used=True),
        max_iterations=1,
        final_top_evidence=[],
    )

    assert (
        payload["extra_pass_judgment"]["extra_pass_candidate_shadow"] is False
    )
    assert "weak_corpus_recovery_completed" in payload["extra_pass_judgment"][
        "extra_pass_candidate_blockers"
    ]


def test_budget_exhausted_without_gaps_is_not_extra_pass_candidate() -> None:
    payload = build_retrieval_budget_pressure_shadow(
        trace=_budget_trace(
            missing_expected_source_classes=[],
            source_class_recovery_query_count=0,
            official_evidence_found=True,
            community_signal_found=True,
            quant_retrieval_target_detected=False,
            quant_retrieval_metric_coverage_valid=False,
        ),
        max_iterations=1,
        final_top_evidence=[
            {"source_id": 1, "source_tier": "official"},
        ],
    )

    assert (
        payload["extra_pass_judgment"]["extra_pass_candidate_shadow"] is False
    )
    assert "no_unresolved_gaps" in payload["extra_pass_judgment"][
        "extra_pass_candidate_blockers"
    ]
    assert (
        payload["answer_quality_impact"]["budget_limited_answer_shadow"] is False
    )


def test_pipeline_budget_pressure_payload_is_nested_and_behavior_neutral(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        mode="Fast",
    )

    monkeypatch.setattr(
        orchestrator,
        "build_retrieval_budget_pressure_shadow",
        lambda **_kwargs: {
            "schema_version": "disabled_for_parity",
            "shadow_mode": True,
        },
    )
    baseline_outcome, baseline_harness, _baseline_log = _run_case(
        tmp_path / "baseline",
        mode="Fast",
    )

    assert active_harness.search_calls == baseline_harness.search_calls
    assert active_harness.model_stage_calls == baseline_harness.model_stage_calls
    assert active_harness.author_prompts == baseline_harness.author_prompts
    assert active_outcome.report == baseline_outcome.report
    assert len(active_harness.search_calls) == 1
    assert active_harness.analyst_calls == baseline_harness.analyst_calls
    _assert_active_stop_budget_exhausted(active_outcome.execution_trace)

    payload = active_outcome.execution_trace["retrieval_budget_pressure_shadow"]
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["shadow_mode"] is True
    assert "retrieval_budget_pressure_shadow" in active_log["execution_trace"]
    assert "retrieval_budget_pressure_shadow" not in active_log

    sqlite_row = execution_jsonl_to_run_row(active_log)
    assert sqlite_row is not None
    assert "retrieval_budget_pressure_shadow" not in sqlite_row

    for text in [active_outcome.report, *active_harness.author_prompts]:
        assert "retrieval_budget_pressure_shadow" not in text
        assert "extra_pass_candidate" not in text
        assert "budget_limited_answer_shadow" not in text
        assert "retrieval_budget_pressure_shadow_v1" not in text


def test_stop_no_queries_active_telemetry_unchanged_with_budget_payload(
    tmp_path,
) -> None:
    outcome, _harness, log_entry = _run_case(
        tmp_path,
        evaluator_responses=[{"is_sufficient": False, "new_queries": []}],
    )

    _assert_active_stop_no_queries(outcome.execution_trace)
    _assert_active_stop_no_queries(log_entry["execution_trace"])
    assert "retrieval_budget_pressure_shadow" in outcome.execution_trace
    assert "retrieval_budget_pressure_shadow" in log_entry["execution_trace"]
