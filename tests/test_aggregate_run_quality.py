from __future__ import annotations

import json
from pathlib import Path

from scripts import aggregate_run_quality


def _write_jsonl(path: Path, rows: list[dict[str, object] | str]) -> None:
    lines = [row if isinstance(row, str) else json.dumps(row) for row in rows]
    path.write_text("\n".join(lines), encoding="utf-8")


def _execution_row() -> dict[str, object]:
    return {"event": "execution", "query_type": "synthetic", "timing": {}}


def _controller_diagnostics_payload() -> dict[str, object]:
    return {
        "schema_version": "controller_diagnostics_v1",
        "passive_only": True,
        "diagnostic_only": True,
        "authority": "none",
        "source": "posthoc_execution_trace",
        "run_plan": {
            "stage_count": 10,
            "disposition_counts": {
                "required": 4,
                "may_run": 2,
                "shadow": 1,
                "blocked_by_mode": 2,
                "not_applicable": 1,
            },
            "items": [],
        },
        "task_ledger": {
            "record_count": 15,
            "status_counts": {
                "planned": 10,
                "completed": 4,
                "skipped": 1,
            },
        },
        "planned_vs_observed": {
            "status_counts": {
                "observed_completed": 4,
                "observed_skipped": 1,
                "may_run_not_observed": 2,
                "shadow_not_observed": 1,
                "blocked_by_mode": 2,
            },
            "failure_count": 0,
            "stages": [],
            "failures": [],
        },
        "observed_summary": {
            "observed_stage_count": 5,
            "observed_stage_ids": [
                "route_intent",
                "researcher_queries",
                "main_retrieval",
                "analyst_review",
                "author",
            ],
            "observed_status_counts": {
                "completed": 4,
                "skipped": 1,
            },
        },
    }


def _source_class_recovery_stage(
    *,
    status: str = "observed_completed",
    observed_status: object = "completed",
    disposition: str = "may_run",
) -> dict[str, object]:
    return {
        "stage_id": "source_class_recovery",
        "module_id": "source_class_recovery",
        "disposition": disposition,
        "status": status,
        "observed_status": observed_status,
        "reason": "source_class_recovery_used",
        "failure": False,
    }


def _controller_execution_row(
    payload: dict[str, object],
    *,
    trace_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    row = _execution_row()
    trace: dict[str, object] = {"controller_diagnostics": payload}
    if trace_updates:
        trace.update(trace_updates)
    row["execution_trace"] = trace
    return row


def _retrieval_stop_execution_row(
    *,
    decision: object = "proceed_to_synthesis",
    reason: object = "evaluator_sufficient",
    alignment: object = "aligned",
    stage: object = "evaluator",
    next_query_count: object = 0,
    available: object = True,
    trace_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    row = _execution_row()
    trace: dict[str, object] = {
        "retrieval_stop_shadow_available": available,
        "retrieval_stop_shadow_decision": decision,
        "retrieval_stop_shadow_reason": reason,
        "retrieval_stop_shadow_blockers": [],
        "retrieval_stop_shadow_next_query_count": next_query_count,
        "retrieval_stop_shadow_alignment": alignment,
        "retrieval_stop_shadow_stage": stage,
        "retrieval_stop_shadow_mode": "shadow_only",
    }
    if trace_updates:
        trace.update(trace_updates)
    row["execution_trace"] = trace
    return row


def _retrieval_stop_active_execution_row(
    *,
    decision: object = "stop_no_queries",
    reason: object = "no_new_queries",
    stage: object = "evaluator_no_queries",
    mode: object = "active_stop_no_queries",
    shadow_alignment: object = "aligned",
    fallback_reason: object = None,
    next_query_count: object = 0,
    available: object = True,
    blockers: object = ("no_new_queries",),
    trace_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    row = _execution_row()
    trace: dict[str, object] = {
        "retrieval_stop_active_available": available,
        "retrieval_stop_active_decision": decision,
        "retrieval_stop_active_reason": reason,
        "retrieval_stop_active_blockers": list(blockers)
        if isinstance(blockers, tuple)
        else blockers,
        "retrieval_stop_active_next_query_count": next_query_count,
        "retrieval_stop_active_stage": stage,
        "retrieval_stop_active_mode": mode,
        "retrieval_stop_active_shadow_alignment": shadow_alignment,
        "retrieval_stop_active_fallback_reason": fallback_reason,
    }
    if trace_updates:
        trace.update(trace_updates)
    row["execution_trace"] = trace
    return row


def _retrieval_budget_pressure_payload(
    *,
    malformed_marker: object | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "retrieval_budget_pressure_shadow_v1",
        "shadow_mode": True,
        "hard_mode_budget": {
            "mode": "Fast",
            "iteration": 1,
            "max_iterations": 1,
            "iterations_run": 1,
            "budget_stop_triggered": True,
            "budget_stop_reason": "iteration_budget_exhausted",
            "budget_pressure_bucket": "exhausted",
        },
        "cost_state": {
            "estimated_cost_usd": 0.01,
            "estimated_cost_available": True,
            "estimated_cost_source": "cost_accumulator_snapshot",
            "estimated_cost_confidence_bucket": "directional_partial",
            "cost_budget_soft_cap_usd": None,
            "cost_budget_hard_cap_usd": None,
            "cost_budget_spent_ratio": None,
        },
        "last_pass_marginal_yield": {
            "new_source_count_last_pass": 2,
            "new_domain_count_last_pass": 1,
            "new_accepted_source_count_last_pass": 2,
            "accepted_overlap_last_pass": 0,
            "query_novelty_score": 0.9,
            "provider_attempts_last_pass": 1,
            "new_official_source_count_last_pass": None,
            "new_primary_source_count_last_pass": None,
        },
        "remaining_evidence_gaps": {
            "evaluator_sufficient": None,
            "next_query_count": 2,
            "next_query_source": "source_class_recovery",
            "missing_expected_source_classes": ["official_current_rules"],
            "official_evidence_found": False,
            "community_signal_found": True,
            "quant_metric_coverage_valid": False,
            "corpus_state": "HEALTHY",
            "pre_analyst_gate_signals": ["missing_expected_official_evidence"],
        },
        "extra_pass_judgment": {
            "extra_pass_candidate_shadow": True,
            "extra_pass_candidate_reasons": [
                "budget_exhausted",
                "missing_expected_source_class",
                "nonredundant_next_queries",
            ],
            "extra_pass_candidate_blockers": [],
            "extra_pass_candidate_query_count": 2,
            "extra_pass_candidate_query_source": "source_class_recovery",
            "extra_pass_budget_class": "exhausted",
        },
        "answer_quality_impact": {
            "budget_limited_answer_shadow": True,
            "budget_limited_answer_reason": (
                "budget_exhausted_with_unresolved_gaps"
            ),
            "unresolved_gap_count_at_synthesis": 1,
            "author_budget_caveat_present": None,
            "answer_outcome": "partial_answer",
            "review_flags": None,
            "final_answer_source_count": 1,
            "final_answer_official_source_count": 0,
            "final_answer_missing_expected_source_class": True,
            "user_feedback_rating": None,
            "manual_eval_score_if_available": None,
        },
    }
    if malformed_marker is not None:
        payload["hard_mode_budget"] = {
            "budget_pressure_bucket": malformed_marker,
            "budget_stop_reason": malformed_marker,
        }
    return payload


def _retrieval_budget_pressure_execution_row(
    payload: object,
) -> dict[str, object]:
    row = _execution_row()
    row["execution_trace"] = {"retrieval_budget_pressure_shadow": payload}
    return row


def _source_class_observability_execution_row(
    *,
    trace_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    row = _execution_row()
    trace: dict[str, object] = {
        "expected_source_classes_raw": [
            "legal_or_regulatory_text",
            "archival_primary_text",
        ],
        "source_class_gap_candidates": ["legal_or_regulatory_text"],
        "source_class_satisfaction_basis": {
            "archival_primary_text": ["archival_primary_signal"]
        },
        "source_class_underfire_shadow": True,
        "source_class_underfire_reasons": ["missing_expected_source_class"],
        "source_class_underfire_blockers": [],
        "final_official_source_count": 0,
        "final_primary_source_count": 1,
        "final_archival_source_count": 1,
        "final_legal_or_regulatory_source_count": 0,
        "source_class_satisfaction_counts": {
            "primary_source_documents": 1,
            "archival_primary_text": 1,
        },
        "source_class_satisfaction_status": {
            "legal_or_regulatory_text": "unsatisfied",
            "archival_primary_text": "satisfied_strong",
        },
        "source_class_satisfaction_strength_counts": {
            "satisfied_strong": 1,
            "unsatisfied": 1,
        },
        "source_class_strong_satisfaction_counts": {
            "primary_source_documents": 1,
            "archival_primary_text": 1,
        },
        "source_class_weak_satisfaction_counts": {},
        "source_class_secondary_only_counts": {},
    }
    if trace_updates:
        trace.update(trace_updates)
    row["execution_trace"] = trace
    return row


def _source_class_candidate_v2_execution_row(
    *,
    payload_updates: dict[str, object] | None = None,
    trace_updates: dict[str, object] | None = None,
) -> dict[str, object]:
    row = _execution_row()
    payload: dict[str, object] = {
        "schema_version": "source_class_recovery_candidate_v2",
        "shadow_mode": True,
        "source_class_recovery_candidate_v2_shadow": True,
        "source_class_recovery_candidate_v2_classes": [
            "legal_or_regulatory_text"
        ],
        "source_class_recovery_candidate_v2_reasons": [
            "expected_source_class_unsatisfied",
            "final_answer_lacks_legal_or_regulatory_source",
        ],
        "source_class_recovery_candidate_v2_blockers": [
            "existing_active_recovery_blocked_by_budget"
        ],
        "source_class_recovery_candidate_v2_status_by_class": {
            "legal_or_regulatory_text": "unsatisfied",
            "archival_primary_text": "satisfied_strong",
        },
        "source_class_recovery_candidate_v2_query_count": 1,
        "source_class_recovery_candidate_v2_query_source": "class_intent_catalog",
        "source_class_recovery_candidate_v2_budget_context": "at_cap",
        "source_class_recovery_candidate_v2_blocked_by_weak_corpus": False,
        "source_class_recovery_candidate_v2_blocked_by_budget": True,
    }
    if payload_updates:
        payload.update(payload_updates)
    trace: dict[str, object] = {
        "answer_class": "partial_answer",
        "source_class_recovery_candidate_v2": payload,
    }
    if trace_updates:
        trace.update(trace_updates)
    row["execution_trace"] = trace
    return row


def _source_class_recovery_validation_packet() -> dict[str, object]:
    return {
        "schema_version": "source_class_recovery_validation_l1",
        "diagnostic_only": True,
        "sanitized": True,
        "ag25_action": {
            "name": "recover_missing_source_class",
            "status": "approved",
            "authority": "active",
            "side_effect_class": "retrieval",
            "handoff_boundary": "ordinary_evidence_eligible",
        },
        "recovery_considered": True,
        "recovery_recommended": True,
        "recovery_eligible": True,
        "recovery_used": True,
        "missing_source_classes": ["legal_or_regulatory_text"],
        "recovery_query_previews": ["Care Program official legal text"],
        "official_domain_constraints": ["ecfr.gov"],
        "jurisdiction_constraints": ["us"],
        "provider_attempts": [
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "depth": "basic",
                "max_results": 6,
                "result_count": 2,
                "accepted_url_count": 2,
            }
        ],
        "accepted_url_count": 2,
        "recovery_source_quality_status": "official_or_primary_found",
        "recovered_visibility_decision": {
            "used": True,
            "reason": "reserved_replace",
        },
        "evidence_bundle_official_legal_current_primary_counts": {
            "legal_or_regulatory_text": 1,
            "current_primary_or_official_proxy": 1,
        },
        "final_cited_counts_available": True,
        "final_cited_official_legal_current_primary_counts": {
            "legal_or_regulatory_text": 0,
            "current_primary_or_official_proxy": 0,
        },
        "recovery_bottleneck_status": "visible_not_final_cited",
    }


def _run_summary(log_path: Path, capsys) -> str:
    aggregate_run_quality.LOG = log_path
    aggregate_run_quality.KB_TRIGGERS = log_path.parent / "missing_kb_triggers.jsonl"
    aggregate_run_quality.main()
    return capsys.readouterr().out


def test_followup_diagnostics_summary_counts_synthetic_cases(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "followup_route_observed": "answer_from_existing_context",
                    "followup_route_shadow": "would_search",
                    "followup_route_reason": "existing_context_sufficient",
                    "freshness_cue_detected": False,
                    "source_constraint_detected": False,
                    "contradiction_cue_detected": False,
                    "ambiguity_cue_detected": False,
                    "source_card_parity_status": "ok",
                    "cited_ids_without_cards": [],
                    "card_ids_not_cited": [],
                    "cards_from_error_response": False,
                    "needs_search": False,
                    "query_count": 0,
                    "search_ran": False,
                    "search_skip_reason": "existing_context_sufficient",
                    "new_passage_count": 0,
                    "no_results": False,
                    "retrieval_error": False,
                    "source_card_count": 1,
                    "synthesis_error": False,
                },
            },
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "followup_route_observed": "search",
                    "followup_route_shadow": "search",
                    "followup_route_reason": "freshness_cue",
                    "freshness_cue_detected": True,
                    "freshness_cue_type": "latest",
                    "source_constraint_detected": True,
                    "source_constraint_type": "named_source",
                    "contradiction_cue_detected": False,
                    "ambiguity_cue_detected": True,
                    "source_card_parity_status": "cited_ids_without_cards",
                    "cited_ids_without_cards": ["src-hidden-1", "src-hidden-2"],
                    "card_ids_not_cited": [],
                    "cards_from_error_response": False,
                    "needs_search": True,
                    "query_count": 1,
                    "search_ran": True,
                    "search_skip_reason": None,
                    "new_passage_count": 3,
                    "no_results": False,
                    "retrieval_error": False,
                    "source_card_count": 3,
                    "synthesis_error": False,
                },
            },
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "followup_route_observed": "search",
                    "followup_route_shadow": "answer_from_existing_context",
                    "followup_route_reason": "source_constraint",
                    "freshness_cue_detected": False,
                    "source_constraint_detected": True,
                    "source_constraint_type": "source_only",
                    "contradiction_cue_detected": True,
                    "ambiguity_cue_detected": False,
                    "source_card_parity_status": "card_ids_not_cited",
                    "cited_ids_without_cards": [],
                    "card_ids_not_cited": ["card-unused-1"],
                    "cards_from_error_response": False,
                    "needs_search": True,
                    "query_count": 2,
                    "search_ran": True,
                    "search_skip_reason": None,
                    "new_passage_count": 0,
                    "no_results": True,
                    "retrieval_error": False,
                    "source_card_count": 0,
                    "synthesis_error": False,
                },
            },
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "followup_route_observed": "search",
                    "followup_route_shadow": "search",
                    "followup_route_reason": "freshness_cue",
                    "freshness_cue_detected": True,
                    "freshness_cue_type": "recency",
                    "source_constraint_detected": False,
                    "contradiction_cue_detected": False,
                    "ambiguity_cue_detected": False,
                    "source_card_parity_status": "cards_from_error_response",
                    "cited_ids_without_cards": [],
                    "card_ids_not_cited": ["card-unused-2", "card-unused-3"],
                    "cards_from_error_response": True,
                    "needs_search": True,
                    "query_count": 1,
                    "search_ran": True,
                    "search_skip_reason": None,
                    "new_passage_count": 0,
                    "no_results": False,
                    "retrieval_error": True,
                    "retrieval_error_preview": "SECRET RETRIEVAL BODY",
                    "source_card_count": 0,
                    "synthesis_error": False,
                },
            },
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "needs_search": False,
                    "query_count": 0,
                    "search_ran": False,
                    "search_skip_reason": "existing_context_sufficient",
                    "new_passage_count": 0,
                    "no_results": False,
                    "retrieval_error": False,
                    "source_card_count": 1,
                    "synthesis_error": True,
                },
            },
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parse_failed",
                    "needs_search": True,
                    "query_count": 0,
                    "search_ran": False,
                    "search_skip_reason": "missing_followup_queries",
                    "new_passage_count": 0,
                    "no_results": False,
                    "retrieval_error": False,
                    "source_card_count": 0,
                    "synthesis_error": False,
                },
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Chat follow-up diagnostics (last 6 rows) ===" in out
    assert "chat_followup_rows: 6" in out
    assert "chat_followup_missing_diagnostics: 0" in out
    assert "needs_search_true: 4" in out
    assert "needs_search_false: 2" in out
    assert "search_ran_true: 3" in out
    assert "search_ran_false: 3" in out
    assert "'existing_context_sufficient': 2" in out
    assert "'missing_followup_queries': 1" in out
    assert "'parsed': 5" in out
    assert "'parse_failed': 1" in out
    assert "'0': 3" in out
    assert "'1': 2" in out
    assert "'2-3': 1" in out
    assert "no_results_count: 1" in out
    assert "retrieval_error_count: 1" in out
    assert "synthesis_error_count: 1" in out
    assert "followup_route_observed:" in out
    assert "'search': 3" in out
    assert "'answer_from_existing_context': 1" in out
    assert "followup_route_shadow:" in out
    assert "'would_search': 1" in out
    assert "followup_route_reason:" in out
    assert "'freshness_cue': 2" in out
    assert "'source_constraint': 1" in out
    assert "freshness_cue_detected:" in out
    assert "'true': 2" in out
    assert "freshness_cue_type:" in out
    assert "'latest': 1" in out
    assert "'recency': 1" in out
    assert "source_constraint_detected:" in out
    assert "source_constraint_type:" in out
    assert "'named_source': 1" in out
    assert "'source_only': 1" in out
    assert "contradiction_cue_detected:" in out
    assert "ambiguity_cue_detected:" in out
    assert "source_card_parity_status:" in out
    assert "'cited_ids_without_cards': 1" in out
    assert "'card_ids_not_cited': 1" in out
    assert "'cards_from_error_response': 1" in out
    assert "cited_ids_without_cards_present: 1" in out
    assert "cited_ids_without_cards_total: 2" in out
    assert "card_ids_not_cited_present: 2" in out
    assert "card_ids_not_cited_total: 3" in out
    assert "cards_from_error_response:" in out
    assert "'parse_failed': 1" in out
    assert "'retrieval_error': 1" in out
    assert "'synthesis_error': 1" in out


def test_followup_historical_missing_diagnostics_is_not_suspicious(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            {"event": "chat_followup", "run_id": "historical-followup"},
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "chat_followup_rows: 1" in out
    assert "chat_followup_missing_diagnostics: 1" in out
    assert "followup_route_observed: {}" in out
    assert "freshness_cue_detected: {}" in out
    assert "cited_ids_without_cards_present: 0" in out
    assert "card_ids_not_cited_present: 0" in out
    assert "'parse_failed': 0" in out
    assert "'retrieval_error': 0" in out
    assert "'synthesis_error': 0" in out
    assert "'source_card_count_zero_with_new_passages': 0" in out


def test_followup_summary_does_not_print_raw_previews(tmp_path: Path, capsys) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            {
                "event": "chat_followup",
                "query_preview": "SECRET TOP LEVEL QUERY",
                "followup_diagnostics": {
                    "evaluator_parse_status": "parsed",
                    "needs_search": True,
                    "query_count": 1,
                    "queries_preview": ["SECRET FOLLOWUP QUERY"],
                    "cited_ids_without_cards": ["SECRET CITATION ID"],
                    "card_ids_not_cited": ["SECRET CARD ID"],
                    "search_ran": True,
                    "search_skip_reason": None,
                    "new_passage_count": 2,
                    "no_results": False,
                    "retrieval_error": True,
                    "retrieval_error_preview": "SECRET RETRIEVAL BODY",
                    "source_card_count": 0,
                    "synthesis_error": False,
                },
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "SECRET TOP LEVEL QUERY" not in out
    assert "SECRET FOLLOWUP QUERY" not in out
    assert "SECRET RETRIEVAL BODY" not in out
    assert "SECRET CITATION ID" not in out
    assert "SECRET CARD ID" not in out
    assert "cited_ids_without_cards_present: 1" in out
    assert "card_ids_not_cited_present: 1" in out
    assert "'source_card_count_zero_with_new_passages': 1" in out


def test_l1_source_class_recovery_validation_summary_counts_packets(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    row = _execution_row()
    row["source_class_recovery_validation_l1"] = (
        _source_class_recovery_validation_packet()
    )
    _write_jsonl(log_path, [row])

    out = _run_summary(log_path, capsys)

    assert "=== L1 source-class recovery validation (last 1 runs) ===" in out
    assert "source_class_recovery_validation_l1_payload_rows: 1" in out
    assert "source_class_recovery_validation_l1_malformed_rows: 0" in out
    assert (
        "source_class_recovery_validation_l1_bottleneck_status_counts: "
        "{'visible_not_final_cited': 1}"
    ) in out
    assert (
        "source_class_recovery_validation_l1_provider_counts: {'tavily': 1}"
        in out
    )
    assert (
        "source_class_recovery_validation_l1_final_cited_available_counts: "
        "{'true': 1}"
    ) in out


def test_l1_source_class_recovery_validation_summary_ignores_absent_packets(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "L1 source-class recovery validation" not in out


def test_followup_summary_ignores_malformed_jsonl_rows(tmp_path: Path, capsys) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            "{not-json",
            _execution_row(),
            {
                "event": "chat_followup",
                "followup_diagnostics": {
                    "needs_search": False,
                    "search_ran": False,
                    "search_skip_reason": "existing_context_sufficient",
                },
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "chat_followup_rows: 1" in out
    assert "chat_followup_missing_diagnostics: 0" in out
    assert "No execution events found." not in out


def test_existing_execution_summary_output_remains_available(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Timing (last 1 runs, timing available on 1) ===" in out
    assert "=== Cost (last 1 runs, cost available on 0) ===" in out
    assert "=== Efficiency ===" in out
    assert "=== Waste flags (frequency) ===" in out
    assert "=== Chat follow-up diagnostics" not in out


def test_controller_diagnostics_summary_counts_valid_v1_payload(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_controller_execution_row(_controller_diagnostics_payload())])

    out = _run_summary(log_path, capsys)

    assert "=== Controller diagnostics (last 1 runs) ===" in out
    assert "controller_diagnostics_execution_rows: 1" in out
    assert "controller_diagnostics_payload_rows: 1" in out
    assert "controller_diagnostics_legacy_missing_rows: 0" in out
    assert "controller_diagnostics_omitted_rows: 0" in out
    assert "controller_diagnostics_malformed_payload_rows: 0" in out
    assert "controller_diagnostics_missing_legacy_or_omitted: 0" in out
    assert "controller_diagnostics_omission_reason_counts: {}" in out
    assert "schema_version: {'controller_diagnostics_v1': 1}" in out
    assert "passive_only: {'true': 1}" in out
    assert "diagnostic_only: {'true': 1}" in out
    assert "authority: {'none': 1}" in out
    assert "source: {'posthoc_execution_trace': 1}" in out
    assert "run_plan_stage_count_buckets: {'6-20': 1}" in out
    assert "'required': 4" in out
    assert "'may_run': 2" in out
    assert "task_ledger_record_count_buckets: {'6-20': 1}" in out
    assert "'planned': 10" in out
    assert "'observed_completed': 4" in out
    assert "'may_run_not_observed': 2" in out
    assert "planned_vs_observed_failure_count_buckets: {'0': 1}" in out
    assert "observed_stage_count_buckets: {'2-5': 1}" in out
    assert "observed_status_counts: {'completed': 4, 'skipped': 1}" in out
    assert "controller_diagnostics_source_class_recovery_payload_rows: 0" in out
    assert "source_class_recovery_stage_present_rows: 0" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "source_class_recovery_stage_status_counts: {}" in out
    assert "source_class_recovery_observed_status_counts: {}" in out
    assert "controller_diagnostics_anomalies: {}" in out
    assert "observed_stage_ids" not in out


def test_controller_diagnostics_summary_counts_source_class_recovery_may_run_not_observed(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["planned_vs_observed"]["stages"] = [
        _source_class_recovery_stage(
            status="may_run_not_observed",
            observed_status=None,
        )
    ]
    _write_jsonl(log_path, [_controller_execution_row(payload)])

    out = _run_summary(log_path, capsys)

    assert "controller_diagnostics_payload_rows: 1" in out
    assert "controller_diagnostics_source_class_recovery_payload_rows: 1" in out
    assert "source_class_recovery_stage_present_rows: 1" in out
    assert "source_class_recovery_not_observed_rows: 1" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "source_class_recovery_stage_status_counts: {'may_run_not_observed': 1}" in out
    assert "source_class_recovery_observed_status_counts: {'missing': 1}" in out
    assert "source_class_recovery_disposition_counts: {'may_run': 1}" in out
    assert "controller_diagnostics_anomalies: {}" in out


def test_controller_diagnostics_summary_counts_source_class_recovery_observed_blocked(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["planned_vs_observed"]["stages"] = [
        _source_class_recovery_stage(
            status="observed_blocked",
            observed_status="blocked",
        )
    ]
    _write_jsonl(log_path, [_controller_execution_row(payload)])

    out = _run_summary(log_path, capsys)

    assert "controller_diagnostics_source_class_recovery_payload_rows: 1" in out
    assert "source_class_recovery_stage_present_rows: 1" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 1" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "source_class_recovery_stage_status_counts: {'observed_blocked': 1}" in out
    assert "source_class_recovery_observed_status_counts: {'blocked': 1}" in out
    assert "source_class_recovery_disposition_counts: {'may_run': 1}" in out
    assert "controller_diagnostics_anomalies: {}" in out


def test_controller_diagnostics_summary_counts_source_class_recovery_observed_completed(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["planned_vs_observed"]["stages"] = [_source_class_recovery_stage()]
    _write_jsonl(
        log_path,
        [
            _controller_execution_row(
                payload,
                trace_updates={"active_source_class_recovery_used": True},
            )
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "controller_diagnostics_source_class_recovery_payload_rows: 1" in out
    assert "source_class_recovery_stage_present_rows: 1" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 1" in out
    assert "source_class_recovery_active_used_rows: 1" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "source_class_recovery_stage_status_counts: {'observed_completed': 1}" in out
    assert "source_class_recovery_observed_status_counts: {'completed': 1}" in out
    assert "source_class_recovery_disposition_counts: {'may_run': 1}" in out
    assert "controller_diagnostics_anomalies: {}" in out


def test_controller_diagnostics_summary_counts_historical_missing_payload(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Controller diagnostics (last 1 runs) ===" in out
    assert "controller_diagnostics_payload_rows: 0" in out
    assert "controller_diagnostics_legacy_missing_rows: 1" in out
    assert "controller_diagnostics_omitted_rows: 0" in out
    assert "controller_diagnostics_malformed_payload_rows: 0" in out
    assert "controller_diagnostics_missing_legacy_or_omitted: 1" in out
    assert "schema_version: {}" in out
    assert "source_class_recovery_stage_present_rows: 0" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "controller_diagnostics_anomalies: {}" in out
    assert "size_guard" not in out
    assert "builder_exception" not in out
    assert "oversized" not in out


def test_controller_diagnostics_summary_does_not_print_raw_nested_strings(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["raw_prompt"] = "RAW_PROMPT_SHOULD_NOT_LEAK_19G"
    payload["evidence"] = [{"text": "RAW_EVIDENCE_SHOULD_NOT_LEAK_19G"}]
    payload["provider_diagnostics"] = [
        {"query_preview": "PROVIDER_DIAGNOSTICS_LIST_SHOULD_NOT_LEAK_19G"}
    ]
    payload["context_measurement"] = {
        "stages": {"author": {"prompt_hash": "CONTEXT_SHOULD_NOT_LEAK_19G"}}
    }
    payload["quantitative_packet"] = {"text": "QUANT_PACKET_SHOULD_NOT_LEAK_19G"}
    payload["economist_framework"] = "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_19G"
    payload["economist_v1"] = {"text": "ECONOMIST_V1_SHOULD_NOT_LEAK_19G"}
    payload["author_internal"] = "AUTHOR_INTERNALS_SHOULD_NOT_LEAK_19G"
    payload["run_plan"]["items"] = [
        {
            "stage_id": "RAW_STAGE_ID_SHOULD_NOT_LEAK_19G",
            "reason": "STAGE_REASON_SHOULD_NOT_LEAK_19G",
        }
    ]
    payload["planned_vs_observed"]["stages"] = [
        {
            "stage_id": "RAW_OBSERVED_STAGE_SHOULD_NOT_LEAK_19G",
            "reason": "RAW_OBSERVED_REASON_SHOULD_NOT_LEAK_19G",
            "metadata": {"prompt": "RAW_STAGE_PROMPT_SHOULD_NOT_LEAK_19G"},
        },
        {
            **_source_class_recovery_stage(
                status="RAW_SOURCE_STATUS_SHOULD_NOT_LEAK_21B",
                observed_status="RAW_OBSERVED_STATUS_SHOULD_NOT_LEAK_21B",
                disposition="RAW_DISPOSITION_SHOULD_NOT_LEAK_21B",
            ),
            "reason": "RAW_SOURCE_REASON_SHOULD_NOT_LEAK_21B",
            "metadata": {"author": "RAW_AUTHOR_INTERNAL_SHOULD_NOT_LEAK_21B"},
        },
    ]
    payload["planned_vs_observed"]["failures"] = [
        {
            "stage_id": "RAW_FAILURE_STAGE_SHOULD_NOT_LEAK_19G",
            "reason": "RAW_FAILURE_REASON_SHOULD_NOT_LEAK_19G",
        }
    ]
    payload["planned_vs_observed"]["status_counts"][
        "RAW_STATUS_KEY_SHOULD_NOT_LEAK_19G"
    ] = 2
    payload["observed_summary"]["observed_stage_ids"] = [
        "RAW_OBSERVED_STAGE_ID_SHOULD_NOT_LEAK_19G"
    ]
    _write_jsonl(log_path, [_controller_execution_row(payload)])

    out = _run_summary(log_path, capsys)

    for marker in (
        "RAW_PROMPT_SHOULD_NOT_LEAK_19G",
        "RAW_EVIDENCE_SHOULD_NOT_LEAK_19G",
        "PROVIDER_DIAGNOSTICS_LIST_SHOULD_NOT_LEAK_19G",
        "CONTEXT_SHOULD_NOT_LEAK_19G",
        "QUANT_PACKET_SHOULD_NOT_LEAK_19G",
        "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_19G",
        "ECONOMIST_V1_SHOULD_NOT_LEAK_19G",
        "AUTHOR_INTERNALS_SHOULD_NOT_LEAK_19G",
        "RAW_STAGE_ID_SHOULD_NOT_LEAK_19G",
        "STAGE_REASON_SHOULD_NOT_LEAK_19G",
        "RAW_OBSERVED_STAGE_SHOULD_NOT_LEAK_19G",
        "RAW_OBSERVED_REASON_SHOULD_NOT_LEAK_19G",
        "RAW_STAGE_PROMPT_SHOULD_NOT_LEAK_19G",
        "RAW_FAILURE_STAGE_SHOULD_NOT_LEAK_19G",
        "RAW_FAILURE_REASON_SHOULD_NOT_LEAK_19G",
        "RAW_STATUS_KEY_SHOULD_NOT_LEAK_19G",
        "RAW_OBSERVED_STAGE_ID_SHOULD_NOT_LEAK_19G",
        "RAW_SOURCE_STATUS_SHOULD_NOT_LEAK_21B",
        "RAW_OBSERVED_STATUS_SHOULD_NOT_LEAK_21B",
        "RAW_DISPOSITION_SHOULD_NOT_LEAK_21B",
        "RAW_SOURCE_REASON_SHOULD_NOT_LEAK_21B",
        "RAW_AUTHOR_INTERNAL_SHOULD_NOT_LEAK_21B",
    ):
        assert marker not in out
    assert "controller_diagnostics_payload_rows: 1" in out
    assert "controller_diagnostics_source_class_recovery_payload_rows: 1" in out
    assert "source_class_recovery_stage_present_rows: 1" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 1" in out
    assert "source_class_recovery_stage_status_counts: {'unknown': 1}" in out
    assert "source_class_recovery_observed_status_counts: {'unknown': 1}" in out
    assert "'unknown': 2" in out
    assert "'planned_vs_observed_status_counts_unknown_key': 1" in out
    assert "'source_class_recovery_status_unknown': 1" in out
    assert "'source_class_recovery_observed_status_unknown': 1" in out
    assert "'source_class_recovery_disposition_unknown': 1" in out


def test_controller_diagnostics_summary_buckets_malformed_partial_and_omitted(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    partial_payload: dict[str, object] = {
        "schema_version": "controller_diagnostics_v1",
        "passive_only": True,
        "diagnostic_only": True,
        "authority": "none",
        "source": "posthoc_execution_trace",
        "planned_vs_observed": {"stages": "not-a-list"},
        "observed_summary": "not-a-mapping",
    }
    _write_jsonl(
        log_path,
        [
            _controller_execution_row(partial_payload),
            {"event": "execution", "execution_trace": {"controller_diagnostics": "bad"}},
            {
                "event": "execution",
                "execution_trace": {
                    "controller_diagnostics_omitted": True,
                    "controller_diagnostics_omitted_reason": (
                        "builder failed RAW_OMISSION_REASON_SHOULD_NOT_LEAK_21B"
                    ),
                },
            },
            {
                "event": "execution",
                "execution_trace": {
                    "controller_diagnostics_omitted": True,
                    "controller_diagnostics_omitted_reason": "size_guard",
                },
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "controller_diagnostics_payload_rows: 1" in out
    assert "controller_diagnostics_legacy_missing_rows: 0" in out
    assert "controller_diagnostics_omitted_rows: 2" in out
    assert "controller_diagnostics_malformed_payload_rows: 1" in out
    assert "controller_diagnostics_missing_legacy_or_omitted: 3" in out
    assert "controller_diagnostics_omission_reason_counts:" in out
    assert "'size_or_oversized': 1" in out
    assert "'builder_exception': 1" in out
    assert "'controller_diagnostics_payload_not_mapping': 1" in out
    assert "'planned_vs_observed_stages_not_list': 1" in out
    assert "'observed_summary_not_mapping': 1" in out
    assert "controller_diagnostics_source_class_recovery_payload_rows: 0" in out
    assert "source_class_recovery_stage_present_rows: 0" in out
    assert "source_class_recovery_not_observed_rows: 0" in out
    assert "source_class_recovery_observed_blocked_rows: 0" in out
    assert "source_class_recovery_observed_completed_rows: 0" in out
    assert "source_class_recovery_active_used_rows: 0" in out
    assert "source_class_recovery_unknown_or_malformed_status_rows: 0" in out
    assert "RAW_OMISSION_REASON_SHOULD_NOT_LEAK_21B" not in out


def test_controller_diagnostics_summary_flags_schema_authority_anomalies(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["schema_version"] = "BAD_SCHEMA_SHOULD_NOT_LEAK_19G"
    payload["passive_only"] = False
    payload["diagnostic_only"] = False
    payload["authority"] = "CONTROL_AUTHORITY_SHOULD_NOT_LEAK_19G"
    payload["source"] = "BAD_SOURCE_SHOULD_NOT_LEAK_19G"
    _write_jsonl(log_path, [_controller_execution_row(payload)])

    out = _run_summary(log_path, capsys)

    assert "schema_version: {'unexpected_or_missing': 1}" in out
    assert "passive_only: {'false': 1}" in out
    assert "diagnostic_only: {'false': 1}" in out
    assert "authority: {'unexpected_or_missing': 1}" in out
    assert "source: {'unexpected_or_missing': 1}" in out
    assert "'schema_version_unexpected_or_missing': 1" in out
    assert "'passive_only_not_true': 1" in out
    assert "'diagnostic_only_not_true': 1" in out
    assert "'authority_not_none': 1" in out
    assert "'source_unexpected_or_missing': 1" in out
    assert "BAD_SCHEMA_SHOULD_NOT_LEAK_19G" not in out
    assert "CONTROL_AUTHORITY_SHOULD_NOT_LEAK_19G" not in out
    assert "BAD_SOURCE_SHOULD_NOT_LEAK_19G" not in out


def test_retrieval_stop_shadow_summary_counts_synthetic_available_row(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_retrieval_stop_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval-stop shadow telemetry (last 1 runs) ===" in out
    assert "retrieval_stop_shadow_available_rows: 1" in out
    assert (
        "retrieval_stop_shadow_decision_counts: {'proceed_to_synthesis': 1}"
        in out
    )
    assert "retrieval_stop_shadow_reason_counts: {'evaluator_sufficient': 1}" in out
    assert "retrieval_stop_shadow_alignment_counts: {'aligned': 1}" in out
    assert "retrieval_stop_shadow_stage_counts: {'evaluator': 1}" in out
    assert "retrieval_stop_shadow_next_query_count_buckets: {'0': 1}" in out
    assert "retrieval_stop_shadow_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_shadow_summary_counts_continue_query_bucket(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _retrieval_stop_execution_row(
                decision="continue_retrieval",
                reason="candidate_queries_available",
                next_query_count=2,
            )
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "retrieval_stop_shadow_available_rows: 1" in out
    assert "retrieval_stop_shadow_decision_counts: {'continue_retrieval': 1}" in out
    assert (
        "retrieval_stop_shadow_reason_counts: {'candidate_queries_available': 1}"
        in out
    )
    assert "retrieval_stop_shadow_next_query_count_buckets: {'2-3': 1}" in out
    assert "retrieval_stop_shadow_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_shadow_summary_counts_historical_rows_as_zero(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval-stop shadow telemetry (last 1 runs) ===" in out
    assert "retrieval_stop_shadow_available_rows: 0" in out
    assert "retrieval_stop_shadow_decision_counts: {}" in out
    assert "retrieval_stop_shadow_reason_counts: {}" in out
    assert "retrieval_stop_shadow_alignment_counts: {}" in out
    assert "retrieval_stop_shadow_stage_counts: {}" in out
    assert "retrieval_stop_shadow_next_query_count_buckets: {}" in out
    assert "retrieval_stop_shadow_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_shadow_summary_buckets_malformed_without_raw_leaks(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    row = _retrieval_stop_execution_row(
        decision="RAW_DECISION_SHOULD_NOT_LEAK_24C",
        reason="RAW_REASON_SHOULD_NOT_LEAK_24C",
        alignment="RAW_ALIGNMENT_SHOULD_NOT_LEAK_24C",
        stage={"prompt": "RAW_STAGE_NESTED_SHOULD_NOT_LEAK_24C"},
        next_query_count={"queries": ["RAW_QUERY_SHOULD_NOT_LEAK_24C"]},
        trace_updates={
            "retrieval_stop_shadow_blockers": [
                "RAW_BLOCKER_SHOULD_NOT_LEAK_24C"
            ],
            "retrieval_stop_shadow_mode": "RAW_MODE_SHOULD_NOT_LEAK_24C",
            "quantitative_packet": {
                "text": "QUANT_PACKET_SHOULD_NOT_LEAK_24C"
            },
            "economist_framework": "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_24C",
            "economist_v1": {"text": "ECONOMIST_V1_SHOULD_NOT_LEAK_24C"},
            "author_internal": "AUTHOR_INTERNALS_SHOULD_NOT_LEAK_24C",
        },
    )
    row["raw_prompt"] = "RAW_PROMPT_SHOULD_NOT_LEAK_24C"
    row["evidence"] = [{"text": "RAW_EVIDENCE_SHOULD_NOT_LEAK_24C"}]
    row["provider_diagnostics"] = [
        {
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "query_preview": "RAW_PROVIDER_INTERNAL_SHOULD_NOT_LEAK_24C",
            "logical_attempt_count": 1,
        }
    ]
    _write_jsonl(log_path, [row])

    out = _run_summary(log_path, capsys)

    assert "retrieval_stop_shadow_available_rows: 1" in out
    assert "retrieval_stop_shadow_decision_counts: {'unknown': 1}" in out
    assert "retrieval_stop_shadow_reason_counts: {'unknown': 1}" in out
    assert "retrieval_stop_shadow_alignment_counts: {'unknown': 1}" in out
    assert "retrieval_stop_shadow_stage_counts: {'unknown': 1}" in out
    assert "retrieval_stop_shadow_next_query_count_buckets: {'unknown': 1}" in out
    assert "retrieval_stop_shadow_unknown_or_malformed_rows: 1" in out
    for marker in (
        "RAW_DECISION_SHOULD_NOT_LEAK_24C",
        "RAW_REASON_SHOULD_NOT_LEAK_24C",
        "RAW_ALIGNMENT_SHOULD_NOT_LEAK_24C",
        "RAW_STAGE_NESTED_SHOULD_NOT_LEAK_24C",
        "RAW_QUERY_SHOULD_NOT_LEAK_24C",
        "RAW_BLOCKER_SHOULD_NOT_LEAK_24C",
        "RAW_MODE_SHOULD_NOT_LEAK_24C",
        "RAW_PROMPT_SHOULD_NOT_LEAK_24C",
        "RAW_EVIDENCE_SHOULD_NOT_LEAK_24C",
        "RAW_PROVIDER_INTERNAL_SHOULD_NOT_LEAK_24C",
        "QUANT_PACKET_SHOULD_NOT_LEAK_24C",
        "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_24C",
        "ECONOMIST_V1_SHOULD_NOT_LEAK_24C",
        "AUTHOR_INTERNALS_SHOULD_NOT_LEAK_24C",
    ):
        assert marker not in out


def test_retrieval_stop_shadow_summary_coexists_with_existing_aggregate_sections(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    payload = _controller_diagnostics_payload()
    payload["planned_vs_observed"]["stages"] = [_source_class_recovery_stage()]
    row = _controller_execution_row(
        payload,
        trace_updates={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_after_recovery",
            "retrieval_stop_shadow_reason": "weak_corpus_recovery_completed",
            "retrieval_stop_shadow_blockers": ["weak_corpus_recovery_completed"],
            "retrieval_stop_shadow_next_query_count": 0,
            "retrieval_stop_shadow_alignment": "aligned",
            "retrieval_stop_shadow_stage": "weak_corpus_recovery_completed",
            "retrieval_stop_shadow_mode": "shadow_only",
        },
    )
    row["corpus_state"] = "weak"
    row["provider_diagnostics"] = [
        {
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "depth": "basic",
            "output_type": "searchResults",
            "success": True,
            "logical_attempt_count": 1,
        }
    ]
    _write_jsonl(log_path, [row])

    out = _run_summary(log_path, capsys)

    assert "by corpus_state: {'weak': 1}" in out
    assert "controller_diagnostics_payload_rows: 1" in out
    assert "source_class_recovery_stage_present_rows: 1" in out
    assert "retrieval_stop_shadow_available_rows: 1" in out
    assert "retrieval_stop_shadow_decision_counts: {'stop_after_recovery': 1}" in out
    assert "=== Provider diagnostics" in out
    assert "provider_diagnostic_attempts: 1" in out


def test_retrieval_stop_active_summary_counts_stop_no_queries_row(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_retrieval_stop_active_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval-stop active telemetry (last 1 runs) ===" in out
    assert "retrieval_stop_active_available_rows: 1" in out
    assert "retrieval_stop_active_fallback_rows: 0" in out
    assert "retrieval_stop_active_decision_counts: {'stop_no_queries': 1}" in out
    assert "retrieval_stop_active_reason_counts: {'no_new_queries': 1}" in out
    assert "retrieval_stop_active_stage_counts: {'evaluator_no_queries': 1}" in out
    assert (
        "retrieval_stop_active_mode_counts: {'active_stop_no_queries': 1}"
        in out
    )
    assert (
        "retrieval_stop_active_shadow_alignment_counts: {'aligned': 1}"
        in out
    )
    assert "retrieval_stop_active_fallback_reason_counts: {}" in out
    assert "retrieval_stop_active_next_query_count_buckets: {'0': 1}" in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_active_summary_counts_stop_budget_exhausted_row(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _retrieval_stop_active_execution_row(
                decision="stop_budget_exhausted",
                reason="iteration_budget_exhausted",
                stage="iteration_budget_exhausted",
                mode="active_stop_budget_exhausted",
                blockers=("iteration_budget_exhausted",),
            )
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval-stop active telemetry (last 1 runs) ===" in out
    assert "retrieval_stop_active_available_rows: 1" in out
    assert "retrieval_stop_active_fallback_rows: 0" in out
    assert (
        "retrieval_stop_active_decision_counts: {'stop_budget_exhausted': 1}"
        in out
    )
    assert (
        "retrieval_stop_active_reason_counts: {'iteration_budget_exhausted': 1}"
        in out
    )
    assert (
        "retrieval_stop_active_stage_counts: {'iteration_budget_exhausted': 1}"
        in out
    )
    assert (
        "retrieval_stop_active_mode_counts: {'active_stop_budget_exhausted': 1}"
        in out
    )
    assert (
        "retrieval_stop_active_shadow_alignment_counts: {'aligned': 1}"
        in out
    )
    assert "retrieval_stop_active_fallback_reason_counts: {}" in out
    assert "retrieval_stop_active_next_query_count_buckets: {'0': 1}" in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_active_summary_counts_fallback_safely(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _retrieval_stop_active_execution_row(
                available=False,
                decision="continue_retrieval",
                reason="candidate_queries_available",
                shadow_alignment="mismatch",
                fallback_reason="unexpected_controller_decision",
                next_query_count=1,
            )
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "retrieval_stop_active_available_rows: 0" in out
    assert "retrieval_stop_active_fallback_rows: 1" in out
    assert (
        "retrieval_stop_active_fallback_reason_counts: "
        "{'unexpected_controller_decision': 1}"
    ) in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 1" in out


def test_retrieval_stop_active_summary_handles_historical_rows(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval-stop active telemetry (last 1 runs) ===" in out
    assert "retrieval_stop_active_available_rows: 0" in out
    assert "retrieval_stop_active_fallback_rows: 0" in out
    assert "retrieval_stop_active_decision_counts: {}" in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 0" in out


def test_retrieval_stop_active_summary_buckets_malformed_without_raw_leaks(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    row = _retrieval_stop_active_execution_row(
        decision="RAW_ACTIVE_DECISION_SHOULD_NOT_LEAK_24C",
        reason="RAW_ACTIVE_REASON_SHOULD_NOT_LEAK_24C",
        stage={"prompt": "RAW_ACTIVE_STAGE_SHOULD_NOT_LEAK_24C"},
        mode="RAW_ACTIVE_MODE_SHOULD_NOT_LEAK_24C",
        shadow_alignment="RAW_ACTIVE_ALIGNMENT_SHOULD_NOT_LEAK_24C",
        fallback_reason="RAW_ACTIVE_FALLBACK_SHOULD_NOT_LEAK_24C",
        next_query_count={"queries": ["RAW_ACTIVE_QUERY_SHOULD_NOT_LEAK_24C"]},
        trace_updates={
            "retrieval_stop_active_blockers": [
                "RAW_ACTIVE_BLOCKER_SHOULD_NOT_LEAK_24C"
            ],
            "raw_prompt": "RAW_ACTIVE_PROMPT_SHOULD_NOT_LEAK_24C",
            "quantitative_packet": {
                "text": "RAW_ACTIVE_QUANT_PACKET_SHOULD_NOT_LEAK_24C"
            },
            "economist_framework": "RAW_ACTIVE_ECON_FRAMEWORK_SHOULD_NOT_LEAK_24C",
            "economist_v1": {"text": "RAW_ACTIVE_ECON_V1_SHOULD_NOT_LEAK_24C"},
            "author_internal": "RAW_ACTIVE_AUTHOR_SHOULD_NOT_LEAK_24C",
        },
    )
    row["provider_diagnostics"] = [
        {
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "query_preview": "RAW_ACTIVE_PROVIDER_SHOULD_NOT_LEAK_24C",
            "logical_attempt_count": 1,
        }
    ]
    _write_jsonl(log_path, [row])

    out = _run_summary(log_path, capsys)

    assert "retrieval_stop_active_available_rows: 1" in out
    assert "retrieval_stop_active_decision_counts: {'unknown': 1}" in out
    assert "retrieval_stop_active_reason_counts: {'unknown': 1}" in out
    assert "retrieval_stop_active_stage_counts: {'unknown': 1}" in out
    assert "retrieval_stop_active_mode_counts: {'unknown': 1}" in out
    assert (
        "retrieval_stop_active_shadow_alignment_counts: {'unknown': 1}"
        in out
    )
    assert "retrieval_stop_active_fallback_reason_counts: {'unknown': 1}" in out
    assert "retrieval_stop_active_next_query_count_buckets: {'unknown': 1}" in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 1" in out
    for marker in (
        "RAW_ACTIVE_DECISION_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_REASON_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_STAGE_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_MODE_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_ALIGNMENT_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_FALLBACK_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_QUERY_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_BLOCKER_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_PROMPT_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_QUANT_PACKET_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_ECON_FRAMEWORK_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_ECON_V1_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_AUTHOR_SHOULD_NOT_LEAK_24C",
        "RAW_ACTIVE_PROVIDER_SHOULD_NOT_LEAK_24C",
    ):
        assert marker not in out


def test_ag30_retrieval_stop_active_aggregate_ignores_unconsumed_active_fields(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    raw_marker = "RAW_ACTIVE_APPROVED_QUERY_COUNT_SHOULD_NOT_LEAK_AG30"
    row = _retrieval_stop_active_execution_row(
        decision="stop_budget_exhausted",
        reason="iteration_budget_exhausted",
        stage="iteration_budget_exhausted",
        mode="active_stop_budget_exhausted",
        blockers=("iteration_budget_exhausted",),
        next_query_count=2,
        trace_updates={
            "retrieval_stop_active_action_name": raw_marker,
            "retrieval_stop_active_authority": raw_marker,
            "retrieval_stop_active_terminal_branch_reason": raw_marker,
            "retrieval_stop_active_approved_query_count": raw_marker,
            "retrieval_stop_active_final_answer_posture": raw_marker,
            "retrieval_stop_active_ag28_candidate": raw_marker,
            "retrieval_stop_shadow_decision": raw_marker,
        },
    )
    _write_jsonl(log_path, [row])

    out = _run_summary(log_path, capsys)

    assert "retrieval_stop_active_available_rows: 1" in out
    assert (
        "retrieval_stop_active_decision_counts: {'stop_budget_exhausted': 1}"
        in out
    )
    assert "retrieval_stop_active_next_query_count_buckets: {'2-3': 1}" in out
    assert "retrieval_stop_active_unknown_or_malformed_rows: 0" in out
    assert raw_marker not in out


def test_source_class_observability_summary_counts_buckets_and_malformed_safely(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    malformed = _source_class_observability_execution_row(
        trace_updates={
            "source_class_underfire_shadow": (
                "RAW_SOURCE_CLASS_UNDERFIRE_SHOULD_NOT_LEAK_29B"
            ),
            "expected_source_classes_raw": [
                "RAW_EXPECTED_SOURCE_CLASS_SHOULD_NOT_LEAK_29B",
                {"prompt": "RAW_EXPECTED_PROMPT_SHOULD_NOT_LEAK_29B"},
            ],
            "source_class_gap_candidates": (
                "RAW_GAP_CANDIDATES_SHOULD_NOT_LEAK_29B"
            ),
            "source_class_underfire_reasons": [
                "RAW_UNDERFIRE_REASON_SHOULD_NOT_LEAK_29B"
            ],
            "source_class_underfire_blockers": [
                "RAW_UNDERFIRE_BLOCKER_SHOULD_NOT_LEAK_29B"
            ],
            "final_official_source_count": {
                "raw": "RAW_FINAL_COUNT_SHOULD_NOT_LEAK_29B"
            },
            "source_class_satisfaction_counts": {
                "RAW_SATISFACTION_CLASS_SHOULD_NOT_LEAK_29B": 2,
                "legal_or_regulatory_text": "RAW_COUNT_SHOULD_NOT_LEAK_29B",
            },
            "source_class_satisfaction_status": {
                "RAW_STATUS_CLASS_SHOULD_NOT_LEAK_30B": (
                    "RAW_STATUS_SHOULD_NOT_LEAK_30B"
                ),
                "legal_or_regulatory_text": "RAW_STATUS_SHOULD_NOT_LEAK_30B",
            },
            "source_class_satisfaction_strength_counts": {
                "RAW_STRENGTH_STATUS_SHOULD_NOT_LEAK_30B": 2,
                "satisfied_strong": "RAW_STRENGTH_COUNT_SHOULD_NOT_LEAK_30B",
            },
            "source_class_strong_satisfaction_counts": {
                "RAW_STRONG_CLASS_SHOULD_NOT_LEAK_30B": 2,
                "legal_or_regulatory_text": (
                    "RAW_STRONG_COUNT_SHOULD_NOT_LEAK_30B"
                ),
            },
            "source_class_weak_satisfaction_counts": {
                "RAW_WEAK_CLASS_SHOULD_NOT_LEAK_30B": 2,
            },
            "source_class_secondary_only_counts": {
                "RAW_SECONDARY_CLASS_SHOULD_NOT_LEAK_30B": 2,
            },
            "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK_29B",
            "raw_evidence": "RAW_EVIDENCE_SHOULD_NOT_LEAK_29B",
            "final_report_text": "RAW_REPORT_SHOULD_NOT_LEAK_29B",
        }
    )
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            _source_class_observability_execution_row(),
            malformed,
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Source-class observability (last 3 runs) ===" in out
    assert "source_class_observability_payload_rows: 2" in out
    assert "source_class_observability_malformed_rows: 1" in out
    assert "source_class_underfire_shadow_counts: {'true': 1, 'unknown': 1}" in out
    assert "'legal_or_regulatory_text': 1" in out
    assert "'archival_primary_text': 1" in out
    assert "source_class_gap_candidate_counts:" in out
    assert "source_class_underfire_reason_counts:" in out
    assert "source_class_underfire_blocker_counts:" in out
    assert "final_official_source_count_buckets:" in out
    assert "source_class_satisfaction_count_totals:" in out
    assert "source_class_satisfaction_status_counts:" in out
    assert "'satisfied_strong': 1" in out
    assert "'unsatisfied': 1" in out
    assert "source_class_satisfaction_strength_count_totals:" in out
    assert "source_class_strong_satisfaction_count_totals:" in out
    assert "source_class_weak_satisfaction_count_totals:" in out
    assert "source_class_secondary_only_count_totals:" in out
    for marker in (
        "RAW_SOURCE_CLASS_UNDERFIRE_SHOULD_NOT_LEAK_29B",
        "RAW_EXPECTED_SOURCE_CLASS_SHOULD_NOT_LEAK_29B",
        "RAW_EXPECTED_PROMPT_SHOULD_NOT_LEAK_29B",
        "RAW_GAP_CANDIDATES_SHOULD_NOT_LEAK_29B",
        "RAW_UNDERFIRE_REASON_SHOULD_NOT_LEAK_29B",
        "RAW_UNDERFIRE_BLOCKER_SHOULD_NOT_LEAK_29B",
        "RAW_FINAL_COUNT_SHOULD_NOT_LEAK_29B",
        "RAW_SATISFACTION_CLASS_SHOULD_NOT_LEAK_29B",
        "RAW_COUNT_SHOULD_NOT_LEAK_29B",
        "RAW_STATUS_CLASS_SHOULD_NOT_LEAK_30B",
        "RAW_STATUS_SHOULD_NOT_LEAK_30B",
        "RAW_STRENGTH_STATUS_SHOULD_NOT_LEAK_30B",
        "RAW_STRENGTH_COUNT_SHOULD_NOT_LEAK_30B",
        "RAW_STRONG_CLASS_SHOULD_NOT_LEAK_30B",
        "RAW_STRONG_COUNT_SHOULD_NOT_LEAK_30B",
        "RAW_WEAK_CLASS_SHOULD_NOT_LEAK_30B",
        "RAW_SECONDARY_CLASS_SHOULD_NOT_LEAK_30B",
        "RAW_PROMPT_SHOULD_NOT_LEAK_29B",
        "RAW_EVIDENCE_SHOULD_NOT_LEAK_29B",
        "RAW_REPORT_SHOULD_NOT_LEAK_29B",
    ):
        assert marker not in out


def test_source_class_candidate_v2_summary_counts_payload_and_historical_rows(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            _source_class_candidate_v2_execution_row(),
            _source_class_candidate_v2_execution_row(
                payload_updates={
                    "source_class_recovery_candidate_v2_shadow": False,
                    "source_class_recovery_candidate_v2_classes": [],
                    "source_class_recovery_candidate_v2_reasons": [],
                    "source_class_recovery_candidate_v2_blockers": [
                        "all_expected_source_classes_satisfied_strong"
                    ],
                    "source_class_recovery_candidate_v2_query_count": 0,
                    "source_class_recovery_candidate_v2_query_source": "none",
                    "source_class_recovery_candidate_v2_budget_context": (
                        "room_remaining"
                    ),
                    "source_class_recovery_candidate_v2_status_by_class": {
                        "archival_primary_text": "satisfied_strong"
                    },
                    "source_class_recovery_candidate_v2_blocked_by_budget": False,
                },
                trace_updates={"answer_class": "answered"},
            ),
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Source-class recovery candidate v2 (last 3 runs) ===" in out
    assert "source_class_recovery_candidate_v2_payload_rows: 2" in out
    assert "source_class_recovery_candidate_v2_malformed_rows: 0" in out
    assert "source_class_recovery_candidate_v2_counts: {'true': 1, 'false': 1}" in out
    assert "'legal_or_regulatory_text': 1" in out
    assert "'expected_source_class_unsatisfied': 1" in out
    assert "'all_expected_source_classes_satisfied_strong': 1" in out
    assert "'legal_or_regulatory_text:unsatisfied': 1" in out
    assert "'archival_primary_text:satisfied_strong': 2" in out
    assert "source_class_recovery_candidate_v2_query_count_buckets:" in out
    assert "'class_intent_catalog': 1" in out
    assert "'none': 1" in out
    assert "'at_cap': 1" in out
    assert "'room_remaining': 1" in out
    assert "source_class_recovery_candidate_v2_budget_blocker_counts:" in out
    assert "'partial_answer': 1" in out


def test_source_class_candidate_v2_summary_buckets_malformed_without_raw_leaks(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    raw_marker = "RAW_CANDIDATE_V2_SHOULD_NOT_LEAK_31B"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            _source_class_candidate_v2_execution_row(
                payload_updates={
                    "schema_version": raw_marker,
                    "shadow_mode": raw_marker,
                    "source_class_recovery_candidate_v2_shadow": raw_marker,
                    "source_class_recovery_candidate_v2_classes": [raw_marker],
                    "source_class_recovery_candidate_v2_reasons": [raw_marker],
                    "source_class_recovery_candidate_v2_blockers": [raw_marker],
                    "source_class_recovery_candidate_v2_status_by_class": {
                        raw_marker: raw_marker
                    },
                    "source_class_recovery_candidate_v2_query_count": raw_marker,
                    "source_class_recovery_candidate_v2_query_source": raw_marker,
                    "source_class_recovery_candidate_v2_budget_context": raw_marker,
                    "source_class_recovery_candidate_v2_blocked_by_weak_corpus": (
                        raw_marker
                    ),
                    "source_class_recovery_candidate_v2_blocked_by_budget": (
                        raw_marker
                    ),
                },
                trace_updates={
                    "answer_class": raw_marker,
                    "raw_prompt": raw_marker,
                    "raw_evidence": raw_marker,
                    "final_report_text": raw_marker,
                },
            ),
            {
                **_execution_row(),
                "execution_trace": {
                    "source_class_recovery_candidate_v2": raw_marker
                },
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "source_class_recovery_candidate_v2_payload_rows: 1" in out
    assert "source_class_recovery_candidate_v2_malformed_rows: 2" in out
    assert "source_class_recovery_candidate_v2_counts: {'unknown': 1}" in out
    assert "source_class_recovery_candidate_v2_reason_counts: {'unknown': 1}" in out
    assert "source_class_recovery_candidate_v2_query_source_counts:" in out
    assert raw_marker not in out


def test_retrieval_budget_pressure_summary_counts_synthetic_payload(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            _retrieval_budget_pressure_execution_row(
                _retrieval_budget_pressure_payload()
            )
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval budget pressure shadow (last 1 runs) ===" in out
    assert "retrieval_budget_pressure_payload_rows: 1" in out
    assert "retrieval_budget_pressure_malformed_rows: 0" in out
    assert "budget_pressure_bucket_counts: {'exhausted': 1}" in out
    assert "budget_stop_reason_counts: {'iteration_budget_exhausted': 1}" in out
    assert "cost_availability_counts: {'true': 1}" in out
    assert "cost_source_counts: {'cost_accumulator_snapshot': 1}" in out
    assert "cost_confidence_counts: {'directional_partial': 1}" in out
    assert "last_pass_new_source_count_buckets: {'2-5': 1}" in out
    assert "last_pass_new_domain_count_buckets: {'1': 1}" in out
    assert (
        "last_pass_new_accepted_source_count_buckets: {'2-5': 1}"
        in out
    )
    assert "last_pass_accepted_overlap_buckets: {'0': 1}" in out
    assert "last_pass_provider_attempt_buckets: {'1': 1}" in out
    assert "query_novelty_buckets: {'0.76-1.00': 1}" in out
    assert "missing_source_class_counts: {'official_current_rules': 1}" in out
    assert "official_evidence_found_counts: {'false': 1}" in out
    assert "community_signal_found_counts: {'true': 1}" in out
    assert "quant_metric_coverage_valid_counts: {'false': 1}" in out
    assert "extra_pass_candidate_counts: {'true': 1}" in out
    assert (
        "extra_pass_reason_counts: {'budget_exhausted': 1, "
        "'missing_expected_source_class': 1, 'nonredundant_next_queries': 1}"
    ) in out
    assert "extra_pass_blocker_counts: {'none': 1}" in out
    assert "extra_pass_query_source_counts: {'source_class_recovery': 1}" in out
    assert "extra_pass_budget_class_counts: {'exhausted': 1}" in out
    assert "budget_limited_answer_counts: {'true': 1}" in out
    assert (
        "budget_limited_answer_reason_counts: "
        "{'budget_exhausted_with_unresolved_gaps': 1}"
    ) in out
    assert "unresolved_gap_buckets: {'1': 1}" in out
    assert "answer_outcome_counts: {'partial_answer': 1}" in out


def test_retrieval_budget_pressure_summary_ignores_historical_rows(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Retrieval budget pressure shadow (last 1 runs) ===" in out
    assert "retrieval_budget_pressure_payload_rows: 0" in out
    assert "retrieval_budget_pressure_malformed_rows: 0" in out
    assert "budget_pressure_bucket_counts: {}" in out


def test_retrieval_budget_pressure_summary_counts_malformed_without_raw_leaks(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    raw_marker = "RAW_BUDGET_PRESSURE_SHOULD_NOT_LEAK_27B"
    _write_jsonl(
        log_path,
        [
            _execution_row(),
            _retrieval_budget_pressure_execution_row(raw_marker),
            _retrieval_budget_pressure_execution_row(
                _retrieval_budget_pressure_payload(malformed_marker=raw_marker)
            ),
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "retrieval_budget_pressure_payload_rows: 1" in out
    assert "retrieval_budget_pressure_malformed_rows: 2" in out
    assert "budget_pressure_bucket_counts: {'unknown': 1}" in out
    assert "budget_stop_reason_counts: {'unknown': 1}" in out
    assert raw_marker not in out


def test_provider_diagnostics_summary_counts_synthetic_attempts(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(
        log_path,
        [
            {
                **_execution_row(),
                "provider_diagnostics": [
                    {
                        "provider": "tavily",
                        "provider_role": "main_retrieval",
                        "depth": "basic",
                        "output_type": "searchResults",
                        "success": True,
                        "logical_attempt_count": 1,
                        "provider_overlap_diagnostics_available": True,
                        "raw_url_count": 3,
                        "raw_unique_url_count": 2,
                        "raw_url_overlap_count": 1,
                        "raw_domain_count": 2,
                        "raw_domain_overlap_count": 1,
                        "accepted_url_overlap_count": 0,
                        "accepted_domain_count": 1,
                        "new_domain_count": 1,
                        "new_source_count": 1,
                        "query_similarity_max": 0.4,
                        "query_similarity_basis": "previous_main_retrieval_iteration",
                    },
                    {
                        "provider": "linkup",
                        "provider_role": "linkup_precision_sourced_answer",
                        "depth": "deep",
                        "output_type": "sourcedAnswer",
                        "success": False,
                        "logical_attempt_count": 1,
                    },
                ],
                "provider_shadow_cost_estimate_available": False,
                "provider_estimated_cost_usd": None,
            },
        ],
    )

    out = _run_summary(log_path, capsys)

    assert "=== Provider diagnostics" in out
    assert "provider_diagnostic_attempts: 2" in out
    assert "attempts_by_provider: {'tavily': 1, 'linkup': 1}" in out
    assert "successes_by_provider: {'tavily': 1}" in out
    assert "failures_by_provider: {'linkup': 1}" in out
    assert "'main_retrieval': 1" in out
    assert "'linkup_precision_sourced_answer': 1" in out
    assert "depth_buckets: {'basic': 1, 'deep': 1}" in out
    assert "output_type_buckets: {'searchResults': 1, 'sourcedAnswer': 1}" in out
    assert "cost_estimate_available_count: 0" in out
    assert "estimated_cost_null_disabled_count: 1" in out
    assert "overlap_diagnostic_attempts: 1" in out
    assert "raw_url_count_buckets: {'2-5': 1}" in out
    assert "raw_unique_url_count_buckets: {'2-5': 1}" in out
    assert "raw_url_overlap_count_buckets: {'1': 1}" in out
    assert "raw_domain_count_buckets: {'2-5': 1}" in out
    assert "raw_domain_overlap_count_buckets: {'1': 1}" in out
    assert "accepted_url_overlap_count_buckets: {'0': 1}" in out
    assert "accepted_domain_count_buckets: {'1': 1}" in out
    assert "new_domain_count_buckets: {'1': 1}" in out
    assert "new_source_count_buckets: {'1': 1}" in out
    assert "query_similarity_max_buckets: {'0.26-0.50': 1}" in out
    assert "query_similarity_basis: {'previous_main_retrieval_iteration': 1}" in out


def test_provider_diagnostics_summary_ignores_historical_rows_without_diagnostics(
    tmp_path: Path,
    capsys,
) -> None:
    log_path = tmp_path / "execution_log.jsonl"
    _write_jsonl(log_path, [_execution_row()])

    out = _run_summary(log_path, capsys)

    assert "=== Provider diagnostics" not in out
    assert "=== Timing (last 1 runs, timing available on 1) ===" in out
