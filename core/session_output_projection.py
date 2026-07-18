"""Projection-only helpers for final runtime trace/session output assembly.

This module keeps legacy execution-trace and JSONL packaging shapes out of the
orchestrator.  It receives already-computed runtime facts and serializes the
same compatibility keys; it does not select providers, issue retrieval, choose
citations, alter prompts, or change final-answer prose.
"""

from __future__ import annotations

from typing import Any, Mapping

from core.authoritative_source_action_orchestrator_adapter import (
    authoritative_source_action_trace_fragment,
)
from core.evidence_integration_checkpoint import EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
from core.final_answer_runtime_adapter import final_answer_packet_trace_fragment
from core.ordinary_continuation_candidate import ORDINARY_CONTINUATION_TRACE_KEY
from core.outcome_persistence_packaging import build_execution_log_entry
from core.retrieval_batch_dispatch import RETRIEVAL_BATCH_DISPATCH_TRACE_KEY
from core.source_class_recovery_diagnostics import SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY

_OFFICIAL_OR_CANONICAL_SOURCE_CLASS_KEYS = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
    "primary_source_documents",
    "archival_primary_text",
)


def official_or_canonical_source_class_count(
    source_class_counts: Mapping[str, Any] | None,
) -> int | None:
    """Return the legacy max count across official/canonical source classes."""

    if not isinstance(source_class_counts, Mapping):
        return None
    counts: list[int] = []
    for key in _OFFICIAL_OR_CANONICAL_SOURCE_CLASS_KEYS:
        if key not in source_class_counts:
            continue
        try:
            counts.append(max(0, int(source_class_counts.get(key) or 0)))
        except (TypeError, ValueError):
            continue
    return max(counts) if counts else None


def _final_answer_packet_trace_fragment_from_state(
    runtime_values: Mapping[str, Any],
) -> dict[str, Any]:
    run_kernel = runtime_values.get("run_kernel")
    state = getattr(run_kernel, "state", None)
    packet_projection = getattr(state, "final_answer_packet", None) or {}
    if isinstance(packet_projection, Mapping) and packet_projection:
        payload = dict(packet_projection)
        payload["canonical_state"] = True
        payload["trace_mode"] = "run_kernel_final_answer_packet_projection"
        return {"final_answer_packet": payload}
    return final_answer_packet_trace_fragment(runtime_values["final_answer_packet"])


def build_execution_trace_projection(runtime_values: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the legacy execution_trace from already-computed run facts."""

    v = runtime_values
    retrieval_loop_contract_state = v.get("retrieval_loop_contract_state")
    source_tier_exec = v["_source_tier_exec"]
    source_domain_exec = v["_source_domain_exec"]
    source_class_evidence_counts = v[
        "source_class_evidence_bundle_observability_telemetry"
    ].get("source_class_strong_satisfaction_counts")
    source_class_citation_counts = v["source_class_observability_telemetry"].get(
        "source_class_strong_satisfaction_counts"
    )
    context_measurement = v["context_measurement"]

    return {
        "run_id": v["run_id"],
        "timestamp_utc": v["ts_utc"],
        "query_preview": (v.get("query") or "")[:200],
        "intent": v["intent"],
        "query_type": v["query_type"],
        "primary_entity": (v.get("primary_entity") or "")[:200],
        "entities": [str(e)[:200] for e in (v.get("entities_list") or [])],
        "empty_entity": v["empty_entity_flag"],
        "router_entity_retry_used": v["router_entity_retry_used"],
        "utilization_pre_retry": v["utilization_pre_retry"],
        "utilization_rate": v["utilization_rate_val"],
        "retrieval_retry_used": v["retrieval_retry_used"],
        "cap_enforcement_trace": dict(v.get("cap_enforcement_trace") or {}),
        "corpus_state": v["corpus_state"],
        "corpus_state_forced": v["corpus_state_forced_flag"],
        "corpus_weak": v["corpus_weak"],
        "useful_content": v["useful_content"],
        "response_displayable": v["response_displayable"],
        "evidence_sufficient": v["evidence_sufficient"],
        "provider_job_evidence_ledger_bridge_projection": dict(
            v.get("provider_job_evidence_ledger_bridge_projection") or {}
        ),
        "answer_class": v["answer_class"],
        "useful_content_reason": v["useful_content_reason"],
        "waste_flags": list(v["waste_flags"]),
        "query_redundancy_skipped": ("query_redundancy_skipped" in v["waste_flags"]),
        "recon_fired": v["recon_fired"],
        "recon_confidence": v["recon_confidence"],
        "canonical_subject_resolved": (v.get("canonical_subject_resolved") or "")[:200]
        or None,
        "timing": dict(v["_timing_payload"]),
        "router_original_report_type": v["router_original_report_type"],
        "router_original_query_type": v["router_original_query_type"],
        "routing_override_applied": v["routing_override_applied"],
        "routing_override_reason": v["routing_override_reason"],
        "report_type": v["report_type"],
        **v["anchor_packet_telemetry"],
        **v["nutrition_lookup_telemetry"],
        **v["router_query_preparation_contract"].to_trace_fragment(),
        **v["query_authority"].to_trace_fragment(),
        **(
            retrieval_loop_contract_state.to_trace_fragment()
            if retrieval_loop_contract_state is not None
            else {}
        ),
        "complexity": v["complexity"],
        "mode": v["strategy"],
        "scout_fired": v["scout_fired"],
        "scout_key": v["scout_key_used"],
        "scout_queries": list(v["scout_queries"]),
        "scout_skip_reason": v["scout_skip_reason"],
        "iterations_run": v["iterations_run"],
        "pass_providers": list(v["providers_by_iteration"]),
        **v["_provider_diagnostics_payload"],
        "queries_per_iteration": v["queries_per_iter"],
        "disambiguation_queries_by_iteration": v["disambiguation_queries_per_iter"],
        "weak_corpus_recovery_considered": v["weak_corpus_recovery_considered"],
        "weak_corpus_recovery_used": v["weak_corpus_recovery_used"],
        "weak_corpus_recovery_skip_reason": v["weak_corpus_recovery_skip_reason"],
        "weak_corpus_recovery_queries": list(v["weak_corpus_recovery_queries"]),
        "weak_corpus_recovery_decision": v["weak_corpus_recovery_decision"],
        "weak_corpus_recovery_reason": v["weak_corpus_recovery_reason"],
        "weak_corpus_recovery_blockers": list(v["weak_corpus_recovery_blockers"]),
        **v["retrieval_stop_shadow_telemetry"],
        **v["retrieval_stop_active_telemetry"],
        **v["active_source_class_recovery_lifecycle"],
        **v["active_conflict_resolution_lifecycle"],
        ORDINARY_CONTINUATION_TRACE_KEY: dict(v["ordinary_continuation_candidate_trace"]),
        **v["targeted_retrieval_lifecycle_trace"],
        "evaluator_continuation_spine_gate_trace": dict(
            v["evaluator_continuation_spine_gate_trace"]
        ),
        "expander_continuation_spine_gate_trace": dict(
            v["expander_continuation_spine_gate_trace"]
        ),
        "scout_continuation_spine_gate_trace": dict(
            v["scout_continuation_spine_gate_trace"]
        ),
        RETRIEVAL_BATCH_DISPATCH_TRACE_KEY: dict(v["retrieval_batch_dispatch_trace"]),
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: v[
            "evidence_integration_checkpoint_trace"
        ],
        **authoritative_source_action_trace_fragment(
            authoritative_source_action_trace=v["authoritative_source_action_trace"],
            official_source_obligation_bridge_trace=v[
                "official_source_obligation_bridge_trace"
            ],
            official_canonical_recovery_query_acquisition_trace=v[
                "official_canonical_recovery_query_acquisition_trace"
            ],
            official_canonical_recovery_execution_admission_trace=v[
                "official_canonical_recovery_execution_admission_trace"
            ],
        ),
        **v["answer_contract_runtime_trace_fragment"],
        **v["analyst_author_handoff_trace_fragment"],
        **_final_answer_packet_trace_fragment_from_state(v),
        **v["citation_source_handoff_trace_fragment"],
        **v["economist_handoff_trace_fragment"],
        **v["synthesis_evaluator_supplemental_search_handoff_trace_fragment"],
        **v["scrutineer_remediation_handoff_trace_fragment"],
        "discover_candidate_urls_admitted": v[
            "discover_candidate_urls_admitted"
        ],
        "urls_fetched": v["urls_fetched"],
        "total_chunks": v["total_chunks_embedded"],
        "source_tier_counts": source_tier_exec["source_tier_counts"],
        "source_domain_counts": source_domain_exec["source_domain_counts"],
        "top_source_domains": source_domain_exec["top_source_domains"],
        "unique_source_domain_count": source_domain_exec["unique_source_domain_count"],
        "on_domain_source_count": source_domain_exec["on_domain_source_count"],
        "off_domain_source_count": source_domain_exec["off_domain_source_count"],
        "official_evidence_found": source_tier_exec["official_evidence_found"],
        "community_signal_found": source_tier_exec["community_signal_found"],
        "low_trust_sources_found": source_tier_exec["low_trust_sources_found"],
        "pollution_detected": source_tier_exec["pollution_detected"],
        **v["source_class_recovery_telemetry"],
        **v["source_class_observability_telemetry"],
        "source_survival_final_evidence_official_or_canonical_count": (
            official_or_canonical_source_class_count(source_class_evidence_counts)
        ),
        "source_survival_final_citation_official_or_canonical_count": (
            official_or_canonical_source_class_count(source_class_citation_counts)
        ),
        "estimate_from_priors_requested": v["estimate_from_priors_requested"],
        "estimate_from_priors_blocked_by_pre_analyst_gate": v[
            "estimate_from_priors_blocked_by_pre_analyst_gate"
        ],
        "economist_ran": v["economist_ran"],
        "economist_preflight_allowed": v["economist_preflight_allowed"],
        "economist_preflight_block_reason": v["economist_preflight_block_reason"],
        "economist_preflight_missing_entities": list(
            v["economist_preflight_missing_entities"]
        ),
        **v["economist_safety_telemetry"],
        **v["quant_retrieval_sufficiency_telemetry"],
        **v["quantitative_consistency_telemetry"],
        **v["quantitative_consistency_guard_telemetry"],
        "missing_target_metric_directive_emitted": v[
            "missing_target_metric_directive_emitted"
        ],
        **v["economist_pre_analyst_skip_candidate_telemetry"],
        **v["analyst_quant_packet_handoff_telemetry"],
        **v["author_quant_source_telemetry"],
        "author_system_prompt_key": v["author_system_prompt_key"],
        **v["final_answer_source_telemetry"],
        **v["economist_skip_eligibility_shadow_telemetry"],
        "economist_skip_shadow_alignment": v["economist_skip_shadow_alignment"],
        "analyst_skipped": v["analyst_skipped"],
        "analyst_skip_reason": v["analyst_skip_reason"],
        "analyst_skipped_after_economist": v["analyst_skipped_after_economist"],
        "analyst_after_economist_skip_reason": v[
            "analyst_after_economist_skip_reason"
        ],
        "economist_output_used_as_analysis": v["economist_output_used_as_analysis"],
        "post_retrieval_fast_path_used": v["post_retrieval_fast_path_used"],
        "pre_analyst_gate_signals": list(v["pre_analyst_gate_signals"]),
        "thin_quant_analyst_used": False,
        "scrutineer_ran": v["scrutineer_ran"],
        "scrutineer_flag_count": v["scrutineer_flag_count"],
        "synth_was_insufficient": v["synth_was_insufficient"],
        "synth_sufficient_first_pass_raw": v["synth_sufficient_first_pass_raw"],
        "synth_sufficient_first_pass": v["synth_sufficient_first_pass"],
        "supplemental_ran": v["supplemental_ran"],
        "context_measurement": context_measurement.payload(),
        "latency_seconds": v["latency_seconds"],
        "output_word_count": v["output_word_count"],
        "final_output_preview": (v.get("report") or "")[:300],
        "cost": v["cost_snapshot"],
        "failure_card": v["failure_card_payload"],
        **v["weak_failure_gate_trace_fragment"],
    }


def build_execution_log_entry_projection(
    runtime_values: Mapping[str, Any],
    *,
    execution_trace: Mapping[str, Any],
    source_class_recovery_validation_packet: Mapping[str, Any],
    code_version_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the legacy JSONL execution entry from the runtime locals map."""

    v = runtime_values
    return build_execution_log_entry(
        current_date=v["current_date"],
        ts_utc=v["ts_utc"],
        run_id=v["run_id"],
        session_id=v["session_id"],
        query=v["query"],
        intent=v["intent"],
        query_type=v["query_type"],
        primary_entity=v.get("primary_entity"),
        entities_list=v.get("entities_list"),
        empty_entity_flag=v["empty_entity_flag"],
        router_entity_retry_used=v["router_entity_retry_used"],
        utilization_pre_retry=v["utilization_pre_retry"],
        utilization_rate_val=v["utilization_rate_val"],
        retrieval_retry_used=v["retrieval_retry_used"],
        corpus_state=v["corpus_state"],
        corpus_state_forced_flag=v["corpus_state_forced_flag"],
        corpus_weak=v["corpus_weak"],
        useful_content=v["useful_content"],
        response_displayable=v["response_displayable"],
        evidence_sufficient=v["evidence_sufficient"],
        answer_class=v["answer_class"],
        useful_content_reason=v["useful_content_reason"],
        waste_flags=v["waste_flags"],
        recon_fired=v["recon_fired"],
        recon_confidence=v["recon_confidence"],
        canonical_subject_resolved=v.get("canonical_subject_resolved"),
        timing_payload=v["_timing_payload"],
        router_original_report_type=v["router_original_report_type"],
        router_original_query_type=v["router_original_query_type"],
        routing_override_applied=v["routing_override_applied"],
        routing_override_reason=v["routing_override_reason"],
        report_type=v["report_type"],
        nutrition_lookup_telemetry=v["nutrition_lookup_telemetry"],
        complexity=v["complexity"],
        mode=v["strategy"],
        fast_model=v["fast_model"],
        smart_model=v["smart_model"],
        scout_fired=v["scout_fired"],
        scout_key_used=v["scout_key_used"],
        scout_queries=v["scout_queries"],
        scout_skip_reason=v["scout_skip_reason"],
        iterations_run=v["iterations_run"],
        total_chunks_embedded=v["total_chunks_embedded"],
        discover_candidate_urls_admitted=v[
            "discover_candidate_urls_admitted"
        ],
        urls_fetched=v["urls_fetched"],
        providers_by_iteration=v["providers_by_iteration"],
        provider_diagnostics_payload=v["_provider_diagnostics_payload"],
        queries_per_iter=v["queries_per_iter"],
        disambiguation_queries_per_iter=v["disambiguation_queries_per_iter"],
        weak_corpus_recovery_considered=v["weak_corpus_recovery_considered"],
        weak_corpus_recovery_used=v["weak_corpus_recovery_used"],
        weak_corpus_recovery_skip_reason=v["weak_corpus_recovery_skip_reason"],
        weak_corpus_recovery_queries=v["weak_corpus_recovery_queries"],
        weak_corpus_recovery_decision=v["weak_corpus_recovery_decision"],
        weak_corpus_recovery_reason=v["weak_corpus_recovery_reason"],
        weak_corpus_recovery_blockers=v["weak_corpus_recovery_blockers"],
        synth_sufficient_first_pass_raw=v["synth_sufficient_first_pass_raw"],
        synth_sufficient_first_pass=v["synth_sufficient_first_pass"],
        scrutineer_flag_count=v["scrutineer_flag_count"],
        estimate_from_priors_requested=v["estimate_from_priors_requested"],
        estimate_from_priors_blocked_by_pre_analyst_gate=v[
            "estimate_from_priors_blocked_by_pre_analyst_gate"
        ],
        economist_ran=v["economist_ran"],
        economist_preflight_allowed=v["economist_preflight_allowed"],
        economist_preflight_block_reason=v["economist_preflight_block_reason"],
        economist_preflight_missing_entities=v["economist_preflight_missing_entities"],
        economist_safety_telemetry=v["economist_safety_telemetry"],
        quant_retrieval_sufficiency_telemetry=v[
            "quant_retrieval_sufficiency_telemetry"
        ],
        missing_target_metric_directive_emitted=v[
            "missing_target_metric_directive_emitted"
        ],
        economist_pre_analyst_skip_candidate_telemetry=v[
            "economist_pre_analyst_skip_candidate_telemetry"
        ],
        analyst_quant_packet_handoff_telemetry=v[
            "analyst_quant_packet_handoff_telemetry"
        ],
        author_quant_source_telemetry=v["author_quant_source_telemetry"],
        author_system_prompt_key=v["author_system_prompt_key"],
        final_answer_source_telemetry=v["final_answer_source_telemetry"],
        economist_skip_eligibility_shadow_telemetry=v[
            "economist_skip_eligibility_shadow_telemetry"
        ],
        economist_skip_shadow_alignment=v["economist_skip_shadow_alignment"],
        analyst_skipped=v["analyst_skipped"],
        analyst_skip_reason=v["analyst_skip_reason"],
        analyst_skipped_after_economist=v["analyst_skipped_after_economist"],
        analyst_after_economist_skip_reason=v["analyst_after_economist_skip_reason"],
        economist_output_used_as_analysis=v["economist_output_used_as_analysis"],
        post_retrieval_fast_path_used=v["post_retrieval_fast_path_used"],
        pre_analyst_gate_signals=v["pre_analyst_gate_signals"],
        scrutineer_ran=v["scrutineer_ran"],
        synth_was_insufficient=v["synth_was_insufficient"],
        supplemental_ran=v["supplemental_ran"],
        report=v["report"],
        latency_seconds=v["latency_seconds"],
        cost_snapshot=v["cost_snapshot"],
        source_class_recovery_validation_trace_key=SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY,
        source_class_recovery_validation_packet=source_class_recovery_validation_packet,
        execution_trace=dict(execution_trace),
        code_version_metadata=code_version_metadata,
    )


__all__ = [
    "build_execution_log_entry_projection",
    "build_execution_trace_projection",
    "official_or_canonical_source_class_count",
]
