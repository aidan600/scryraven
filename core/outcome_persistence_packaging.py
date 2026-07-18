"""Packaging-only helpers for final run outcome and persistence payloads.

This module receives already-computed orchestration facts and assembles the
legacy JSONL, SQLite, session, and RunOutcome compatibility shapes. It does not
choose providers, run retrieval, inspect prompts, select citations, or edit final
answer prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.db import execution_jsonl_to_run_row
from core.run_config import RunOutcome
from core.run_logging import current_code_version_metadata


@dataclass(frozen=True)
class OutcomePersistencePackagingResult:
    """Compatibility payloads handed back to the orchestrator for persistence."""

    session_payload: dict[str, Any]
    execution_log_entry: dict[str, Any]
    sqlite_row: dict[str, Any] | None
    run_outcome: RunOutcome
    final_output_metadata: dict[str, Any]


def build_pipeline_config(*, intent: str, complexity: str, search_depth: int, mode: str) -> dict[str, Any]:
    """Return the legacy pipeline_config payload shared by session and RunOutcome."""

    return {
        "intent": intent,
        "complexity": complexity,
        "search_depth": search_depth,
        "mode": mode,
    }


def build_final_output_metadata(
    *,
    report: str,
    latency_seconds: float,
    cost_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return final-output metadata fields reused by trace, JSONL, and review logs."""

    return {
        "latency_seconds": latency_seconds,
        "output_word_count": len((report or "").split()),
        "final_output_preview": (report or "")[:300],
        "cost": dict(cost_snapshot),
    }


def build_session_payload(
    *,
    session_id: str,
    run_id: str,
    session_title: str,
    current_date: str,
    query: str,
    core_topic: str,
    report: str,
    final_top_evidence: list[dict[str, Any]],
    seen_urls: list[str],
    collected_images: list[str],
    mode: str,
    pipeline_config: Mapping[str, Any],
    run_history_out: list[dict[str, Any]],
    failure_card_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble the legacy session blob saved by UI callers."""

    return {
        "id": session_id,
        "run_id": run_id,
        "title": session_title,
        "timestamp": current_date,
        "query": query,
        "core_topic": core_topic,
        "report": report,
        "top_passages": final_top_evidence,
        "chat_messages": [],
        "seen_urls": list(seen_urls),
        "collected_images": list(collected_images),
        "last_report_mode": mode,
        "pipeline_config": dict(pipeline_config),
        "run_history": run_history_out,
        "failure_card": dict(failure_card_payload),
    }


def build_execution_log_entry(**facts: Any) -> dict[str, Any]:
    """Assemble the legacy execution JSONL payload from already-computed facts."""

    report = facts["report"]
    final_metadata = build_final_output_metadata(
        report=report,
        latency_seconds=facts["latency_seconds"],
        cost_snapshot=facts["cost_snapshot"],
    )
    validation_trace_key = facts["source_class_recovery_validation_trace_key"]
    execution_trace = facts["execution_trace"]
    entry: dict[str, Any] = {
        "event": "execution",
        "timestamp": facts["current_date"],
        "timestamp_utc": facts["ts_utc"],
        "run_id": facts["run_id"],
        "session_id": facts["session_id"],
        "query": facts["query"][:100],
        "intent": facts["intent"],
        "query_type": facts["query_type"],
        "primary_entity": (facts["primary_entity"] or "")[:200],
        "entities": [str(e)[:200] for e in (facts["entities_list"] or [])],
        "empty_entity": facts["empty_entity_flag"],
        "router_entity_retry_used": facts["router_entity_retry_used"],
        "utilization_pre_retry": facts["utilization_pre_retry"],
        "utilization_rate": facts["utilization_rate_val"],
        "retrieval_retry_used": facts["retrieval_retry_used"],
        "corpus_state": facts["corpus_state"],
        "corpus_state_forced": facts["corpus_state_forced_flag"],
        "corpus_weak": facts["corpus_weak"],
        "useful_content": facts["useful_content"],
        "response_displayable": facts["response_displayable"],
        "evidence_sufficient": facts["evidence_sufficient"],
        "answer_class": facts["answer_class"],
        "useful_content_reason": facts["useful_content_reason"],
        "waste_flags": list(facts["waste_flags"]),
        "query_redundancy_skipped": ("query_redundancy_skipped" in facts["waste_flags"]),
        "recon_fired": facts["recon_fired"],
        "recon_confidence": facts["recon_confidence"],
        "canonical_subject_resolved": (facts["canonical_subject_resolved"] or "")[:200] or None,
        "timing": dict(facts["timing_payload"]),
        "router_original_report_type": facts["router_original_report_type"],
        "router_original_query_type": facts["router_original_query_type"],
        "routing_override_applied": facts["routing_override_applied"],
        "routing_override_reason": facts["routing_override_reason"],
        "report_type": facts["report_type"],
        **facts["nutrition_lookup_telemetry"],
        "complexity": facts["complexity"],
        "mode": facts["mode"],
        "fast_model": facts["fast_model"],
        "smart_model": facts["smart_model"],
        "scout_fired": facts["scout_fired"],
        "scout_key": facts["scout_key_used"],
        "scout_queries": list(facts["scout_queries"]),
        "scout_skip_reason": facts["scout_skip_reason"],
        "iterations_run": facts["iterations_run"],
        "total_chunks_embedded": facts["total_chunks_embedded"],
        "discover_candidate_urls_admitted": facts[
            "discover_candidate_urls_admitted"
        ],
        "urls_fetched": facts["urls_fetched"],
        "providers_by_iteration": facts["providers_by_iteration"],
        **facts["provider_diagnostics_payload"],
        "queries_per_iteration": facts["queries_per_iter"],
        "disambiguation_queries_by_iteration": facts["disambiguation_queries_per_iter"],
        "weak_corpus_recovery_considered": facts["weak_corpus_recovery_considered"],
        "weak_corpus_recovery_used": facts["weak_corpus_recovery_used"],
        "weak_corpus_recovery_skip_reason": facts["weak_corpus_recovery_skip_reason"],
        "weak_corpus_recovery_queries": list(facts["weak_corpus_recovery_queries"]),
        "weak_corpus_recovery_decision": facts["weak_corpus_recovery_decision"],
        "weak_corpus_recovery_reason": facts["weak_corpus_recovery_reason"],
        "weak_corpus_recovery_blockers": list(facts["weak_corpus_recovery_blockers"]),
        "synth_sufficient_first_pass_raw": facts["synth_sufficient_first_pass_raw"],
        "synth_sufficient_first_pass": facts["synth_sufficient_first_pass"],
        "scrutineer_flag_count": facts["scrutineer_flag_count"],
        "estimate_from_priors_requested": facts["estimate_from_priors_requested"],
        "estimate_from_priors_blocked_by_pre_analyst_gate": facts["estimate_from_priors_blocked_by_pre_analyst_gate"],
        "economist_ran": facts["economist_ran"],
        "economist_preflight_allowed": facts["economist_preflight_allowed"],
        "economist_preflight_block_reason": facts["economist_preflight_block_reason"],
        "economist_preflight_missing_entities": list(facts["economist_preflight_missing_entities"]),
        **facts["economist_safety_telemetry"],
        **facts["quant_retrieval_sufficiency_telemetry"],
        "missing_target_metric_directive_emitted": facts["missing_target_metric_directive_emitted"],
        **facts["economist_pre_analyst_skip_candidate_telemetry"],
        **facts["analyst_quant_packet_handoff_telemetry"],
        **facts["author_quant_source_telemetry"],
        "author_system_prompt_key": facts["author_system_prompt_key"],
        **facts["final_answer_source_telemetry"],
        **facts["economist_skip_eligibility_shadow_telemetry"],
        "economist_skip_shadow_alignment": facts["economist_skip_shadow_alignment"],
        "analyst_skipped": facts["analyst_skipped"],
        "analyst_skip_reason": facts["analyst_skip_reason"],
        "analyst_skipped_after_economist": facts["analyst_skipped_after_economist"],
        "analyst_after_economist_skip_reason": facts["analyst_after_economist_skip_reason"],
        "economist_output_used_as_analysis": facts["economist_output_used_as_analysis"],
        "post_retrieval_fast_path_used": facts["post_retrieval_fast_path_used"],
        "pre_analyst_gate_signals": list(facts["pre_analyst_gate_signals"]),
        "thin_quant_analyst_used": False,
        "scrutineer_ran": facts["scrutineer_ran"],
        "synth_was_insufficient": facts["synth_was_insufficient"],
        "supplemental_ran": facts["supplemental_ran"],
        **final_metadata,
        validation_trace_key: facts["source_class_recovery_validation_packet"],
        "execution_trace": execution_trace,
    }
    if "code_version_metadata" in facts:
        entry.update(facts["code_version_metadata"] or {})
    else:
        entry.update(current_code_version_metadata())
    entry.update(
        {
            "analyst_skipped": execution_trace["analyst_skipped"],
            "analyst_skip_reason": execution_trace["analyst_skip_reason"],
            "analyst_skipped_after_economist": execution_trace["analyst_skipped_after_economist"],
            "analyst_after_economist_skip_reason": execution_trace[
                "analyst_after_economist_skip_reason"
            ],
            "economist_output_used_as_analysis": execution_trace["economist_output_used_as_analysis"],
            "post_retrieval_fast_path_used": execution_trace["post_retrieval_fast_path_used"],
            "pre_analyst_gate_signals": list(execution_trace["pre_analyst_gate_signals"]),
        }
    )
    return entry


def build_sqlite_row_payload(execution_log_entry: Mapping[str, Any]) -> dict[str, Any] | None:
    """Map the JSONL execution payload to the unchanged SQLite row shape."""

    return execution_jsonl_to_run_row(dict(execution_log_entry))


def build_run_outcome(
    *,
    session_id: str,
    run_id: str,
    session_title: str,
    query: str,
    core_topic: str,
    report: str,
    final_top_evidence: list[dict[str, Any]],
    seen_urls: list[str],
    collected_images: list[str],
    execution_trace: dict[str, Any],
    failure_card_payload: Mapping[str, Any],
    session_payload: dict[str, Any],
    cost_snapshot: Mapping[str, Any],
    latency_seconds: float,
    intent: str,
    complexity: str,
    corpus_state: str,
    pipeline_config: Mapping[str, Any],
    kb_instrumentation: dict[str, Any] | None = None,
    kb_warning: str | None = None,
    author_streamed: bool = False,
) -> RunOutcome:
    """Assemble the RunOutcome dataclass without changing field names."""

    return RunOutcome(
        session_id=session_id,
        run_id=run_id,
        session_title=session_title,
        query=query,
        core_topic=core_topic,
        report=report,
        top_passages=final_top_evidence,
        seen_urls=list(seen_urls),
        collected_images=list(collected_images),
        execution_trace=execution_trace,
        failure_card=dict(failure_card_payload),
        new_session=session_payload,
        cost_snapshot=dict(cost_snapshot),
        latency_seconds=latency_seconds,
        intent=intent,
        complexity=complexity,
        corpus_state=corpus_state,
        pipeline_config=dict(pipeline_config),
        kb_instrumentation=kb_instrumentation,
        kb_warning=kb_warning,
        author_streamed=author_streamed,
    )
