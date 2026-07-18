from __future__ import annotations

from core.session_output_projection import (
    build_execution_log_entry_projection,
    build_execution_trace_projection,
    official_or_canonical_source_class_count,
)


class _Traceable:
    def __init__(self, payload):
        self.payload = payload

    def to_trace_fragment(self):
        return dict(self.payload)


class _ContextMeasurement:
    def payload(self):
        return {"token_budget": 123}


def _runtime_values():
    return {
        "run_id": "run-1",
        "ts_utc": "2026-06-06T00:00:00+00:00",
        "current_date": "2026-06-06",
        "session_id": "session-1",
        "query": "What changed?",
        "intent": "research",
        "query_type": "general",
        "primary_entity": "Example Entity",
        "entities_list": ["Example Entity"],
        "empty_entity_flag": False,
        "router_entity_retry_used": False,
        "utilization_pre_retry": 0.2,
        "utilization_rate_val": 0.3,
        "retrieval_retry_used": False,
        "corpus_state": "healthy",
        "corpus_state_forced_flag": False,
        "corpus_weak": False,
        "useful_content": True,
        "response_displayable": True,
        "evidence_sufficient": True,
        "answer_class": "sourced",
        "useful_content_reason": "sufficient",
        "waste_flags": ["query_redundancy_skipped"],
        "recon_fired": False,
        "recon_confidence": None,
        "canonical_subject_resolved": "Example Entity",
        "_timing_payload": {"latency_seconds": 1.2},
        "router_original_report_type": "normal",
        "router_original_query_type": "general",
        "routing_override_applied": False,
        "routing_override_reason": None,
        "report_type": "normal",
        "anchor_packet_telemetry": {"anchor_packet_available": True},
        "nutrition_lookup_telemetry": {"nutrition_lookup_detected": False},
        "router_query_preparation_contract": _Traceable({"router_query_preparation": {"ok": True}}),
        "query_authority": _Traceable({"query_plan": {"authority": "QueryPlan"}}),
        "retrieval_loop_contract_state": None,
        "complexity": "low",
        "strategy": "fast",
        "fast_model": "fast-model",
        "smart_model": "smart-model",
        "scout_fired": False,
        "scout_key_used": None,
        "scout_queries": [],
        "scout_skip_reason": "not_needed",
        "iterations_run": 1,
        "providers_by_iteration": [["exa"]],
        "_provider_diagnostics_payload": {"provider_diagnostics": []},
        "queries_per_iter": {"1": ["What changed?"]},
        "disambiguation_queries_per_iter": {},
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": "not_weak_corpus",
        "weak_corpus_recovery_queries": [],
        "weak_corpus_recovery_decision": None,
        "weak_corpus_recovery_reason": None,
        "weak_corpus_recovery_blockers": [],
        "retrieval_stop_shadow_telemetry": {"retrieval_stop_shadow_available": False},
        "retrieval_stop_active_telemetry": {"retrieval_stop_active_available": False},
        "active_source_class_recovery_lifecycle": {"active_source_class_recovery": False},
        "active_conflict_resolution_lifecycle": {"active_conflict_resolution": False},
        "ordinary_continuation_candidate_trace": {"available": False},
        "targeted_retrieval_lifecycle_trace": {"targeted_retrieval": False},
        "evaluator_continuation_spine_gate_trace": {"available": False},
        "expander_continuation_spine_gate_trace": {"available": False},
        "scout_continuation_spine_gate_trace": {"available": False},
        "retrieval_batch_dispatch_trace": {"available": False},
        "evidence_integration_checkpoint_trace": {"available": False},
        "authoritative_source_action_trace": {"available": False},
        "official_source_obligation_bridge_trace": {"available": False},
        "official_canonical_recovery_query_acquisition_trace": {"available": False},
        "official_canonical_recovery_execution_admission_trace": {"available": False},
        "answer_contract_runtime_trace_fragment": {"answer_contract_runtime_handoff": {"available": True}},
        "analyst_author_handoff_trace_fragment": {"analyst_author_handoff_contract": {"available": True}},
        "final_answer_packet": _Traceable({"final_answer_packet": {"packet_id": "p1"}}),
        "citation_source_handoff_trace_fragment": {"citation_source_handoff_contract": {"available": True}},
        "economist_handoff_trace_fragment": {"economist_handoff_contract": {"available": True}},
        "synthesis_evaluator_supplemental_search_handoff_trace_fragment": {"ses_handoff": {"available": True}},
        "scrutineer_remediation_handoff_trace_fragment": {"scrutineer_remediation_handoff": {"available": True}},
        "discover_candidate_urls_admitted": 2,
        "urls_fetched": 0,
        "total_chunks_embedded": 3,
        "_source_tier_exec": {
            "source_tier_counts": {"official_current_rules": 2},
            "official_evidence_found": True,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_exec": {
            "source_domain_counts": {"example.com": 1},
            "top_source_domains": ["example.com"],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 1,
            "off_domain_source_count": 0,
        },
        "source_class_recovery_telemetry": {"source_class_recovery_recommended": False},
        "source_class_observability_telemetry": {
            "source_class_strong_satisfaction_counts": {"primary_source_documents": 4}
        },
        "source_class_evidence_bundle_observability_telemetry": {
            "source_class_strong_satisfaction_counts": {"official_current_rules": 2}
        },
        "estimate_from_priors_requested": False,
        "estimate_from_priors_blocked_by_pre_analyst_gate": False,
        "economist_ran": False,
        "economist_preflight_allowed": False,
        "economist_preflight_block_reason": "not_quant",
        "economist_preflight_missing_entities": [],
        "economist_safety_telemetry": {"economist_safety": True},
        "quant_retrieval_sufficiency_telemetry": {"quant_retrieval": False},
        "quantitative_consistency_telemetry": {"quantitative_consistency": "ok"},
        "quantitative_consistency_guard_telemetry": {"quantitative_guard": "ok"},
        "missing_target_metric_directive_emitted": False,
        "economist_pre_analyst_skip_candidate_telemetry": {"economist_skip_candidate": False},
        "analyst_quant_packet_handoff_telemetry": {"analyst_quant_packet_present": False},
        "author_quant_source_telemetry": {"author_quant_source_count": 0},
        "author_system_prompt_key": "normal",
        "final_answer_source_telemetry": {"final_answer_source_ids_used": ["s1"]},
        "economist_skip_eligibility_shadow_telemetry": {"economist_skip_shadow": False},
        "economist_skip_shadow_alignment": "aligned",
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": None,
        "economist_output_used_as_analysis": False,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": [],
        "scrutineer_ran": False,
        "scrutineer_flag_count": 0,
        "synth_was_insufficient": False,
        "synth_sufficient_first_pass_raw": True,
        "synth_sufficient_first_pass": True,
        "supplemental_ran": False,
        "context_measurement": _ContextMeasurement(),
        "latency_seconds": 1.2,
        "output_word_count": 3,
        "report": "A short answer.",
        "cost_snapshot": {"total": 0},
        "failure_card_payload": {"show": False},
        "weak_failure_gate_trace_fragment": {"weak_failure_gate": {"available": True}},
    }


def test_ag90a_execution_trace_projection_preserves_compatibility_keys() -> None:
    trace = build_execution_trace_projection(_runtime_values())

    assert trace["queries_per_iteration"] == {"1": ["What changed?"]}
    assert trace["query_plan"] == {"authority": "QueryPlan"}
    assert trace["final_answer_packet"] == {"packet_id": "p1"}
    assert trace["source_survival_final_evidence_official_or_canonical_count"] == 2
    assert trace["source_survival_final_citation_official_or_canonical_count"] == 4
    assert trace["discover_candidate_urls_admitted"] == 2
    assert trace["urls_fetched"] == 0
    assert trace["context_measurement"] == {"token_budget": 123}


def test_ag90a_execution_log_projection_keeps_legacy_jsonl_shape() -> None:
    runtime = _runtime_values()
    trace = build_execution_trace_projection(runtime)
    entry = build_execution_log_entry_projection(
        runtime,
        execution_trace=trace,
        source_class_recovery_validation_packet={"validated": True},
        code_version_metadata={"code_version": "test"},
    )

    assert entry["event"] == "execution"
    assert entry["queries_per_iteration"] == {"1": ["What changed?"]}
    assert entry["discover_candidate_urls_admitted"] == 2
    assert entry["urls_fetched"] == 0
    assert entry["execution_trace"] == trace
    assert entry["source_class_recovery_validation_l1"] == {"validated": True}
    assert entry["code_version"] == "test"


def test_ag90a_official_or_canonical_count_matches_legacy_max_semantics() -> None:
    assert official_or_canonical_source_class_count({"official_current_rules": "2", "primary_source_documents": 5}) == 5
    assert official_or_canonical_source_class_count({"other": 99}) is None
    assert official_or_canonical_source_class_count(None) is None
