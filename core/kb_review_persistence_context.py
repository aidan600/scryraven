"""Passive KB review persistence context and record builders.

This module packages already-computed pipeline facts for the persistence
side-effect layer. It does not decide whether KB review should happen, call the
KB review agent, or perform persistence writes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class KbReviewPersistenceContext:
    """Inputs needed to preserve the existing KB trigger logging side effect."""

    feedback_log_path: Path
    kb_triggers_path: Path
    session_id: str
    run_id: str
    query: str
    report_type: str
    query_type: str
    primary_entity: str | None
    entities_list: list[Any]
    empty_entity_flag: bool
    router_entity_retry_used: bool
    utilization_pre_retry: float
    utilization_rate_val: float
    retrieval_retry_used: bool
    corpus_state: str
    corpus_state_forced_flag: bool
    corpus_weak: bool
    useful_content: bool
    response_displayable: bool
    evidence_sufficient: bool
    answer_class: str
    useful_content_reason: str | None
    waste_flags: list[str]
    recon_fired: bool
    recon_confidence: float | None
    canonical_subject_resolved: str | None
    timing_payload: dict[str, Any]
    strategy: str
    fast_model: str
    smart_model: str
    complexity: str
    intent: str
    iterations_run: int
    providers_by_iteration: list[Any]
    queries_per_iter: dict[int, list[str]]
    queries_by_iteration: dict[int, list[str]]
    disambiguation_queries_per_iter: dict[int, list[str]]
    weak_corpus_recovery_considered: bool
    weak_corpus_recovery_used: bool
    weak_corpus_recovery_skip_reason: str | None
    weak_corpus_recovery_queries: list[str]
    weak_corpus_recovery_decision: str | None
    weak_corpus_recovery_reason: str | None
    weak_corpus_recovery_blockers: list[str]
    scout_fired: bool
    scout_key_used: str | None
    scout_queries: list[str]
    synth_was_insufficient: bool
    synth_sufficient_first_pass_raw: Any
    synth_sufficient_first_pass: bool
    failure_card_payload: dict[str, Any] | None
    supplemental_ran: bool
    delta_urls_supplemental: int
    total_chunks_embedded: int
    seen_urls: list[str]
    scrutineer_high_count: int
    scrutineer_flag_count: int
    synth_deficiency: str | None
    latency_seconds: float
    output_word_count: int
    report: str
    cost_snapshot: dict[str, Any]
    ask_model: Callable[..., Any]
    clean_json_response: Callable[..., Any]
    fast_provider: str
    local_url: str | None
    or_api_key: str | None
    kb_review_agent: Callable[..., Any]


_KB_CONTEXT_RUNTIME_FIELDS: tuple[str, ...] = (
    "feedback_log_path",
    "kb_triggers_path",
    "session_id",
    "run_id",
    "query",
    "report_type",
    "query_type",
    "primary_entity",
    "entities_list",
    "empty_entity_flag",
    "router_entity_retry_used",
    "utilization_pre_retry",
    "utilization_rate_val",
    "retrieval_retry_used",
    "corpus_state",
    "corpus_state_forced_flag",
    "corpus_weak",
    "useful_content",
    "response_displayable",
    "evidence_sufficient",
    "answer_class",
    "useful_content_reason",
    "waste_flags",
    "recon_fired",
    "recon_confidence",
    "canonical_subject_resolved",
    "timing_payload",
    "strategy",
    "fast_model",
    "smart_model",
    "complexity",
    "intent",
    "iterations_run",
    "providers_by_iteration",
    "queries_per_iter",
    "queries_by_iteration",
    "disambiguation_queries_per_iter",
    "weak_corpus_recovery_considered",
    "weak_corpus_recovery_used",
    "weak_corpus_recovery_skip_reason",
    "weak_corpus_recovery_queries",
    "weak_corpus_recovery_decision",
    "weak_corpus_recovery_reason",
    "weak_corpus_recovery_blockers",
    "scout_fired",
    "scout_key_used",
    "scout_queries",
    "synth_was_insufficient",
    "synth_sufficient_first_pass_raw",
    "synth_sufficient_first_pass",
    "failure_card_payload",
    "supplemental_ran",
    "delta_urls_supplemental",
    "total_chunks_embedded",
    "seen_urls",
    "scrutineer_high_count",
    "scrutineer_flag_count",
    "synth_deficiency",
    "latency_seconds",
    "output_word_count",
    "report",
    "cost_snapshot",
    "ask_model",
    "fast_provider",
    "local_url",
    "or_api_key",
)


def build_kb_review_persistence_context(
    *,
    runtime_values: Mapping[str, Any],
    clean_json_response: Callable[..., Any],
    kb_review_agent: Callable[..., Any],
) -> KbReviewPersistenceContext:
    """Package already-computed runtime facts into the KB persistence context."""

    values = {
        name: (
            runtime_values["_timing_payload"]
            if "_timing_payload" in runtime_values
            else runtime_values["timing_payload"]
        )
        if name == "timing_payload"
        else runtime_values[name]
        for name in _KB_CONTEXT_RUNTIME_FIELDS
    }
    values["seen_urls"] = list(values["seen_urls"])
    values["clean_json_response"] = clean_json_response
    values["kb_review_agent"] = kb_review_agent
    return KbReviewPersistenceContext(**values)


def flatten_providers_used(providers_by_iteration: list[Any] | None) -> list[str]:
    providers: list[str] = []
    for item in providers_by_iteration or []:
        if isinstance(item, dict):
            vals = item.get("providers") or item.get("provider") or []
            if isinstance(vals, str):
                vals = [vals]
            for provider in vals:
                if provider and str(provider) not in providers:
                    providers.append(str(provider))
        elif item and str(item) not in providers:
            providers.append(str(item))
    return providers


def build_kb_execution_record(context: KbReviewPersistenceContext) -> dict[str, Any]:
    """Build the unchanged execution record passed into review flagging/agent."""

    return {
        "run_id": context.run_id,
        "session_id": context.session_id,
        "query": context.query[:200],
        "report_type": context.report_type,
        "query_type": context.query_type,
        "primary_entity": (context.primary_entity or "")[:200],
        "entities": [str(e)[:200] for e in (context.entities_list or [])],
        "empty_entity": context.empty_entity_flag,
        "router_entity_retry_used": context.router_entity_retry_used,
        "utilization_pre_retry": context.utilization_pre_retry,
        "utilization_rate": context.utilization_rate_val,
        "retrieval_retry_used": context.retrieval_retry_used,
        "corpus_state": context.corpus_state,
        "corpus_state_forced": context.corpus_state_forced_flag,
        "corpus_weak": context.corpus_weak,
        "useful_content": context.useful_content,
        "response_displayable": context.response_displayable,
        "evidence_sufficient": context.evidence_sufficient,
        "answer_class": context.answer_class,
        "useful_content_reason": context.useful_content_reason,
        "waste_flags": list(context.waste_flags),
        "query_redundancy_skipped": "query_redundancy_skipped"
        in context.waste_flags,
        "recon_fired": context.recon_fired,
        "recon_confidence": context.recon_confidence,
        "canonical_subject_resolved": (context.canonical_subject_resolved or "")[:200]
        or None,
        "timing": dict(context.timing_payload),
        "mode": context.strategy,
        "fast_model": context.fast_model,
        "smart_model": context.smart_model,
        "complexity": context.complexity,
        "intent": context.intent,
        "iterations_run": context.iterations_run,
        "pass_providers": context.providers_by_iteration,
        "queries_per_iteration": context.queries_per_iter,
        "queries_iter1": context.queries_by_iteration.get(1, []),
        "queries_iter2": context.queries_by_iteration.get(2, []),
        "disambiguation_queries_by_iteration": context.disambiguation_queries_per_iter,
        "weak_corpus_recovery_considered": context.weak_corpus_recovery_considered,
        "weak_corpus_recovery_used": context.weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": context.weak_corpus_recovery_skip_reason,
        "weak_corpus_recovery_queries": list(context.weak_corpus_recovery_queries),
        "weak_corpus_recovery_decision": context.weak_corpus_recovery_decision,
        "weak_corpus_recovery_reason": context.weak_corpus_recovery_reason,
        "weak_corpus_recovery_blockers": list(context.weak_corpus_recovery_blockers),
        "scout_fired": context.scout_fired,
        "scout_key": context.scout_key_used,
        "scout_queries": list(context.scout_queries),
        "synth_was_insufficient": context.synth_was_insufficient,
        "synth_sufficient_first_pass_raw": context.synth_sufficient_first_pass_raw,
        "synth_sufficient_first_pass": context.synth_sufficient_first_pass,
        "failure_card": context.failure_card_payload,
        "supplemental_ran": context.supplemental_ran,
        "delta_urls_supplemental": context.delta_urls_supplemental,
        "total_chunks_embedded": context.total_chunks_embedded,
        "urls_fetched": len(context.seen_urls),
        "scrutineer_high_flags": context.scrutineer_high_count,
        "scrutineer_flag_count": context.scrutineer_flag_count,
        "synth_deficiency": context.synth_deficiency,
        "latency_seconds": context.latency_seconds,
        "output_word_count": context.output_word_count,
        "final_output_preview": (context.report or "")[:300],
        "cost": context.cost_snapshot,
    }


def build_kb_trigger_entry(
    *,
    context: KbReviewPersistenceContext,
    flags_obj: Any,
    score_val: float,
    review_f: bool,
    execution_record: Mapping[str, Any],
    timestamp_utc: str,
) -> dict[str, Any]:
    """Build the unchanged KB trigger append payload."""

    return {
        **asdict(flags_obj),
        "event": "kb_trigger",
        "run_id": context.run_id,
        "session_id": context.session_id,
        "query": context.query[:200],
        "report_type": context.report_type,
        "mode": context.strategy,
        "synth_deficiency": context.synth_deficiency,
        "score": score_val,
        "fired": review_f,
        "timestamp_utc": timestamp_utc,
        "retrieval_yield_chunks": int(context.total_chunks_embedded),
        "providers_used": flatten_providers_used(context.providers_by_iteration),
        "timing": dict(execution_record["timing"]),
    }
