"""Deterministic post-Author trace and output projection packaging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.answer_contract_runtime_handoff import RuntimeAnswerContractFacts, build_runtime_answer_contract_handoff
from core.conflict_state_producer import (
    ConflictState,
    ConflictStateProducerInput,
    build_conflict_state,
    project_conflict_state_to_runtime_facts,
)
from core.economist_handoff_contract import build_economist_handoff_state
from core.final_answer_runtime_assembly import assemble_final_answer_citation_runtime_from_scope
from core.outcome_persistence_packaging import build_final_output_metadata, build_run_outcome
from core.provider_diagnostics import provider_diagnostics_payload
from core.run_logging import current_code_version_metadata
from core.runtime_trace_export_attachment import attach_runtime_trace_export_compatibility_payloads
from core.scrutineer_remediation_runtime_handoff import (
    RuntimeScrutineerRemediationFacts,
    runtime_scrutineer_remediation_trace_fragment,
)
from core.session_output_projection import build_execution_log_entry_projection, build_execution_trace_projection
from core.weak_failure_gate_contract import WEAK_FAILURE_GATE_TRACE_KEY

_POST_AUTHOR_TRACE_SCOPE_KEYS = ('_run_controller_mirror', '_source_domain_exec', '_source_tier_exec', 'analysis', 'analyst_after_economist_skip_reason', 'analyst_cached_prefix', 'analyst_quant_packet_handoff_telemetry', 'analyst_skip_reason', 'analyst_skipped', 'analyst_skipped_after_economist', 'author_evidence', 'author_evidence_block', 'author_notes', 'author_prompt', 'author_quant_source_telemetry', 'author_system_prompt_key', 'complexity', 'core_topic', 'corpus_state', 'corpus_weak', 'current_date', 'delta_urls_supplemental', 'economist_output_used_as_analysis', 'economist_pre_analyst_skip_candidate_telemetry', 'economist_preflight_allowed', 'economist_preflight_block_reason', 'economist_preflight_missing_entities', 'economist_ran', 'economist_safety_telemetry', 'estimate_from_priors_blocked_by_pre_analyst_gate', 'estimate_from_priors_requested', 'evidence_integration_checkpoint_handoff', 'evidence_ledger_projection', 'evidence_sufficient', 'failure_card_payload', 'final_answer_packet', 'final_answer_source_telemetry', 'final_source_telemetry_inputs', 'final_top_evidence', 'image_context', 'intent', 'iterations_run', 'linkup_block', 'max_iterations', 'missing_target_metric_directive_emitted', 'need_economist', 'ordered_sources', 'post_retrieval_fast_path_used', 'pre_analyst_gate_contract', 'pre_analyst_gate_signals', 'primary_entity', 'provider_diagnostics', 'queries_per_iter', 'query', 'query_type', 'recency_notes', 'report_type', 'results_per_query', 'retrieval_loop_contract_state', 'retrieval_stop_active_telemetry', 'retrieval_stop_shadow_telemetry', 'router_query_preparation_contract', 'run_id', 'runtime_active_source_class_recovery_lifecycle', 'runtime_source_class_recovery_telemetry', 'scrutineer_flags', 'scrutineer_pass_flags_directly_to_author', 'scrutineer_ran', 'scrutineer_remediation_dispatch_authorized', 'scrutineer_remediation_dispatch_posture', 'scrutineer_remediation_evidence', 'scrutineer_remediation_linkup_depth_override', 'scrutineer_remediation_provider_role', 'scrutineer_remediation_providers', 'scrutineer_remediation_queries', 'scrutineer_remediation_resynthesis_triggered', 'search_depth', 'strategy', 'supplemental_ran', 'synth_was_insufficient', 'synthesis_evaluator_supplemental_search_collector', 'unique_source_urls', 'weak_corpus_recovery_considered', 'weak_corpus_recovery_skip_reason', 'weak_corpus_recovery_used', 'weak_failure_gate_contract_state', '_author_effort', '_efp_author', '_relevance_low')
_POST_AUTHOR_OUTPUT_SCOPE_KEYS = ('_source_domain_exec', '_source_tier_exec', '_timing_payload', 'active_conflict_resolution_lifecycle', 'active_source_class_recovery_lifecycle', 'analyst_after_economist_skip_reason', 'analyst_quant_packet_handoff_telemetry', 'analyst_skip_reason', 'analyst_skipped', 'analyst_skipped_after_economist', 'anchor_packet_telemetry', 'answer_class', 'author_quant_source_telemetry', 'author_system_prompt_key', 'authoritative_source_action_trace', 'complexity', 'context_measurement', 'corpus_state', 'corpus_state_forced_flag', 'corpus_weak', 'cost_snapshot', 'current_date', 'disambiguation_queries_per_iter', 'economist_output_used_as_analysis', 'economist_pre_analyst_skip_candidate_telemetry', 'economist_preflight_allowed', 'economist_preflight_block_reason', 'economist_preflight_missing_entities', 'economist_ran', 'economist_safety_telemetry', 'economist_skip_eligibility_shadow_telemetry', 'economist_skip_shadow_alignment', 'empty_entity_flag', 'estimate_from_priors_blocked_by_pre_analyst_gate', 'estimate_from_priors_requested', 'evaluator_continuation_spine_gate_trace', 'evidence_integration_checkpoint_trace', 'evidence_sufficient', 'expander_continuation_spine_gate_trace', 'failure_card_payload', 'fast_model', 'final_top_evidence', 'intent', 'iterations_run', 'latency_seconds', 'max_iterations', 'missing_target_metric_directive_emitted', 'new_session', 'nutrition_lookup_telemetry', 'official_canonical_recovery_execution_admission_trace', 'official_canonical_recovery_query_acquisition_trace', 'official_source_obligation_bridge_trace', 'ordinary_continuation_candidate_trace', 'post_retrieval_fast_path_used', 'pre_analyst_gate_signals', 'providers_by_iteration', 'quant_retrieval_sufficiency_telemetry', 'quantitative_consistency_guard_telemetry', 'quantitative_consistency_telemetry', 'queries_per_iter', 'query', 'query_authority', 'query_type', 'recon_confidence', 'recon_fired', 'report', 'report_type', 'response_displayable', 'retrieval_batch_dispatch_trace', 'retrieval_retry_used', 'retrieval_stop_active_telemetry', 'retrieval_stop_shadow_telemetry', 'router_entity_retry_used', 'router_original_query_type', 'router_original_report_type', 'router_query_preparation_contract', 'routing_override_applied', 'routing_override_reason', 'run_id', 'run_log', 'scout_continuation_spine_gate_trace', 'scout_fired', 'scout_key_used', 'scout_queries', 'scout_skip_reason', 'scrutineer_flag_count', 'scrutineer_ran', 'session_id', 'smart_model', 'source_class_evidence_bundle_observability_telemetry', 'source_class_observability_telemetry', 'source_class_projection_handoff', 'source_class_recovery_telemetry', 'strategy', 'supplemental_ran', 'synth_sufficient_first_pass', 'synth_sufficient_first_pass_raw', 'synth_was_insufficient', 'targeted_retrieval_lifecycle_trace', 'total_chunks_embedded', 'total_urls_fetched', 'ts_utc', 'useful_content', 'useful_content_reason', 'utilization_pre_retry', 'utilization_rate_val', 'waste_flags', 'weak_corpus_recovery_blockers', 'weak_corpus_recovery_considered', 'weak_corpus_recovery_decision', 'weak_corpus_recovery_queries', 'weak_corpus_recovery_reason', 'weak_corpus_recovery_skip_reason', 'weak_corpus_recovery_used')
_RUN_OUTCOME_SCOPE_KEYS = ('collected_images', 'complexity', 'config', 'core_topic', 'corpus_state', 'cost_snapshot', 'execution_trace', 'failure_card_payload', 'final_top_evidence', 'intent', 'kb_instrumentation', 'kb_warning', 'latency_seconds', 'new_session', 'pipeline_config_payload', 'quantitative_guard_stream_buffered', 'query', 'report', 'run_id', 'seen_urls', 'session_id', 'session_title')
@dataclass(frozen=True, slots=True)
class PostAuthorTracePackaging:
    answer_contract_runtime_result: Any
    answer_contract_runtime_trace_fragment: dict[str, Any]
    provider_diagnostics_payload: dict[str, Any]
    weak_failure_gate_trace_fragment: dict[str, Any]
    final_answer_packet: Any
    analyst_author_handoff_state: Any
    analyst_author_handoff_trace_fragment: dict[str, Any]
    citation_source_handoff_state: Any
    unique_source_urls: Mapping[str, Any]
    ordered_sources: list[str]
    final_answer_source_telemetry: dict[str, Any]
    citation_source_handoff_trace_fragment: dict[str, Any]
    economist_handoff_state: Any
    economist_handoff_trace_fragment: dict[str, Any]
    synthesis_evaluator_supplemental_search_handoff_trace_fragment: dict[str, Any]
    scrutineer_remediation_handoff_trace_fragment: dict[str, Any]
    trace_field_fragments: tuple[dict[str, Any], ...]

    def runtime_values(self) -> dict[str, Any]:
        values = {name: getattr(self, name) for name in (
            "answer_contract_runtime_result", "answer_contract_runtime_trace_fragment", "weak_failure_gate_trace_fragment",
            "final_answer_packet", "analyst_author_handoff_state", "analyst_author_handoff_trace_fragment",
            "citation_source_handoff_state", "unique_source_urls", "ordered_sources", "final_answer_source_telemetry",
            "citation_source_handoff_trace_fragment", "economist_handoff_state", "economist_handoff_trace_fragment",
            "synthesis_evaluator_supplemental_search_handoff_trace_fragment", "scrutineer_remediation_handoff_trace_fragment",
        )}
        values["_provider_diagnostics_payload"] = self.provider_diagnostics_payload
        return values

@dataclass(frozen=True, slots=True)
class PostAuthorOutputPackaging:
    execution_trace: dict[str, Any]
    output_word_count: int
    execution_log_entry: dict[str, Any]

def _scrutineer_allowed_by_contract(contract: Any) -> bool:
    relevance = getattr(getattr(contract, "scrutineer_relevance", None), "value", None)
    return str(relevance or "").casefold() in {"central", "relevant_optional"}

def _scrutineer_allowed_by_mode(mode: str | None) -> bool:
    return str(mode or "").strip().casefold() in {"deep", "scrutineer", "review"}

def _build_runtime_conflict_state_projection(
    *,
    query: str,
    core_topic: str | None,
    primary_entity: str | None,
    current_date: str | None,
    final_top_evidence: Sequence[Mapping[str, Any]],
    source_tier_counts: dict[str, Any],
    source_domain_telemetry: dict[str, Any],
    source_class_observability: dict[str, Any],
    ordinary_next_queries: Sequence[str] = (),
) -> tuple[ConflictState, dict[str, Any]]:
    conflict_state = build_conflict_state(
        ConflictStateProducerInput(
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            current_date=current_date,
            final_top_evidence=final_top_evidence,
            source_tier_counts=source_tier_counts,
            source_domain_telemetry=source_domain_telemetry,
            source_class_observability=source_class_observability,
            ordinary_next_queries=ordinary_next_queries,
        )
    )
    return conflict_state, project_conflict_state_to_runtime_facts(conflict_state)

def _post_author_citation_scope(v: Mapping[str, Any], answer_contract_runtime_result: Any) -> dict[str, Any]:
    keys = (
        "final_answer_packet", "run_id", "final_answer_source_telemetry", "final_source_telemetry_inputs",
        "analyst_skipped", "analyst_skip_reason", "post_retrieval_fast_path_used", "pre_analyst_gate_signals",
        "analyst_skipped_after_economist", "analyst_after_economist_skip_reason", "economist_output_used_as_analysis",
        "analyst_cached_prefix", "linkup_block", "analyst_quant_packet_handoff_telemetry",
        "missing_target_metric_directive_emitted", "corpus_weak", "failure_card_payload", "author_notes",
        "author_evidence", "final_top_evidence", "ordered_sources", "unique_source_urls", "author_evidence_block",
        "author_prompt", "complexity", "author_system_prompt_key", "_author_effort", "recency_notes", "image_context",
        "pre_analyst_gate_contract", "weak_failure_gate_contract_state", "retrieval_loop_contract_state",
        "router_query_preparation_contract", "_efp_author", "_relevance_low",
    )
    scoped = {key: v[key] for key in keys}
    scoped["answer_contract_runtime_result"] = answer_contract_runtime_result
    return scoped

def build_post_author_trace_packaging_from_scope(
    runtime_values: Mapping[str, Any],
    *,
    analyst_evidence: Sequence[Mapping[str, Any]],
    logger: logging.Logger,
    answer_contract_handoff_builder: Any = build_runtime_answer_contract_handoff,
) -> PostAuthorTracePackaging:
    v = {key: runtime_values[key] for key in _POST_AUTHOR_TRACE_SCOPE_KEYS}
    answer_contract_runtime_trace_fragment: dict[str, Any] = {}
    answer_contract_runtime_result = None
    try:
        _, runtime_conflict_projection = _build_runtime_conflict_state_projection(
            query=v["query"],
            core_topic=v["core_topic"],
            primary_entity=v["primary_entity"],
            current_date=v["current_date"],
            final_top_evidence=v["final_top_evidence"],
            source_tier_counts=v["_source_tier_exec"]["source_tier_counts"],
            source_domain_telemetry=v["_source_domain_exec"],
            source_class_observability=v["runtime_source_class_recovery_telemetry"],
        )
        answer_contract_runtime_result = answer_contract_handoff_builder(
            RuntimeAnswerContractFacts(
                query=v["query"], intent=v["intent"], report_type=v["report_type"], query_type=v["query_type"],
                mode=v["strategy"], current_date=v["current_date"], core_topic=v["core_topic"],
                evidence_available=bool(v["final_top_evidence"]), evidence_sufficient=bool(v["evidence_sufficient"]),
                source_tier_counts=v["_source_tier_exec"]["source_tier_counts"],
                source_class_recovery_telemetry=v["runtime_source_class_recovery_telemetry"],
                active_source_class_recovery_lifecycle=v["runtime_active_source_class_recovery_lifecycle"],
                evidence_ledger_projection=v["evidence_ledger_projection"],
                weak_corpus=bool(v["corpus_weak"]),
                weak_corpus_reason=(v["weak_corpus_recovery_skip_reason"] or v["corpus_state"]) if v["corpus_weak"] else None,
                weak_corpus_recovery_considered=bool(v["weak_corpus_recovery_considered"]),
                weak_corpus_recovery_used=bool(v["weak_corpus_recovery_used"]),
                weak_corpus_recovery_skip_reason=v["weak_corpus_recovery_skip_reason"],
                conflicts_present=runtime_conflict_projection["conflicts_present"],
                conflict_notes=runtime_conflict_projection["conflict_notes"],
                resolving_queries=runtime_conflict_projection["resolving_queries"],
                retrieval_stop_shadow_telemetry=v["retrieval_stop_shadow_telemetry"],
                retrieval_stop_active_telemetry=v["retrieval_stop_active_telemetry"],
                queries_by_iteration=v["queries_per_iter"], final_top_evidence=v["final_top_evidence"],
                evidence_integration_checkpoint=v["evidence_integration_checkpoint_handoff"],
                iteration=v["iterations_run"], max_iterations=v["max_iterations"], max_recovery_attempts=1,
            ),
            controller=v["_run_controller_mirror"],
        )
        answer_contract_runtime_trace_fragment = answer_contract_runtime_result.execution_trace_fragment()
    except Exception as exc:
        logger.warning("Non-fatal answer-contract handoff omitted: %s", exc)
    weak_state = v["weak_failure_gate_contract_state"]
    weak_failure_gate_trace_fragment = (
        weak_state.to_trace_fragment() if weak_state is not None
        else {WEAK_FAILURE_GATE_TRACE_KEY: {"controller_owned": False, "available": False}}
    )
    final_answer_citation_runtime = assemble_final_answer_citation_runtime_from_scope(
        _post_author_citation_scope(v, answer_contract_runtime_result), analyst_evidence=analyst_evidence
    )
    economist_handoff_state = build_economist_handoff_state(
        run_id=v["run_id"], need_economist=v["need_economist"], economist_ran=v["economist_ran"],
        economist_preflight_allowed=v["economist_preflight_allowed"],
        economist_preflight_block_reason=v["economist_preflight_block_reason"],
        economist_preflight_missing_entities=v["economist_preflight_missing_entities"],
        economist_safety_telemetry=v["economist_safety_telemetry"],
        economist_pre_analyst_skip_candidate_telemetry=v["economist_pre_analyst_skip_candidate_telemetry"],
        analyst_quant_packet_handoff_telemetry=v["analyst_quant_packet_handoff_telemetry"],
        author_quant_source_telemetry=v["author_quant_source_telemetry"],
        analyst_skipped_after_economist=v["analyst_skipped_after_economist"],
        analyst_after_economist_skip_reason=v["analyst_after_economist_skip_reason"],
        economist_output_used_as_analysis=v["economist_output_used_as_analysis"],
        estimate_from_priors_requested=v["estimate_from_priors_requested"],
        estimate_from_priors_blocked_by_pre_analyst_gate=v["estimate_from_priors_blocked_by_pre_analyst_gate"],
        answer_contract_ref=answer_contract_runtime_result,
        analyst_author_handoff_state=final_answer_citation_runtime.analyst_author_handoff_state,
        citation_source_handoff_state=final_answer_citation_runtime.citation_source_handoff_state,
    )
    economist_handoff_trace_fragment = economist_handoff_state.to_trace_fragment()
    scrutineer_answer_state = getattr(answer_contract_runtime_result, "state", None)
    scrutineer_evidence_state = getattr(scrutineer_answer_state, "evidence_state_summary", None)
    scrutineer_active_contract = getattr(scrutineer_answer_state, "active_contract", None)
    synthesis_evaluator_supplemental_search_handoff_trace_fragment = v["synthesis_evaluator_supplemental_search_collector"].to_trace_fragment(
        run_id=v["run_id"], synth_was_insufficient=v["synth_was_insufficient"], results_per_query=v["results_per_query"],
        delta_urls_supplemental=v["delta_urls_supplemental"], supplemental_ran=v["supplemental_ran"],
        final_evidence=v["final_top_evidence"], ordered_source_count=len(final_answer_citation_runtime.ordered_sources),
        unique_source_url_count=len(final_answer_citation_runtime.unique_source_urls),
        answer_contract_available=answer_contract_runtime_result is not None,
    )
    scrutineer_remediation_handoff_trace_fragment = runtime_scrutineer_remediation_trace_fragment(
        RuntimeScrutineerRemediationFacts(
            run_id=v["run_id"], eligible=bool(v["complexity"] == "high"), run_gate="legacy_complexity_high_gate",
            run_posture="completed" if v["scrutineer_ran"] else "skipped", complexity=v["complexity"],
            mode_allowed=_scrutineer_allowed_by_mode(v["strategy"]),
            contract_allowed=_scrutineer_allowed_by_contract(scrutineer_active_contract),
            requested=getattr(scrutineer_evidence_state, "scrutineer_requested", None),
            needed=getattr(scrutineer_evidence_state, "scrutineer_needed", None),
            skip_reason=None if v["scrutineer_ran"] else "legacy_complexity_gate_not_high",
            flags=v["scrutineer_flags"], remediation_queries=v["scrutineer_remediation_queries"],
            dispatch_authorized=v["scrutineer_remediation_dispatch_authorized"],
            dispatch_posture=v["scrutineer_remediation_dispatch_posture"],
            provider_role=v["scrutineer_remediation_provider_role"], providers=v["scrutineer_remediation_providers"],
            search_depth=v["search_depth"], linkup_depth_override=v["scrutineer_remediation_linkup_depth_override"],
            remediation_evidence=v["scrutineer_remediation_evidence"], final_evidence_bundle_id=f'{v["run_id"]}:final_evidence',
            final_evidence_ref={"final_evidence_count": len(v["final_top_evidence"]), "ordered_source_count": len(final_answer_citation_runtime.ordered_sources), "unique_source_url_count": len(final_answer_citation_runtime.unique_source_urls)},
            resynthesis_posture="triggered" if v["scrutineer_remediation_resynthesis_triggered"] else "skipped",
            reanalysis_triggered=v["scrutineer_remediation_resynthesis_triggered"],
            resynthesis_trigger_reason="remediation_passages_added" if v["scrutineer_remediation_resynthesis_triggered"] else None,
            analyst_pass_ref={"stage": "analyst_scrutineer_remediation"} if v["scrutineer_remediation_resynthesis_triggered"] else {},
            analysis_ref={"analysis_available": bool(v["analysis"])},
            pass_flags_directly_to_author=v["scrutineer_pass_flags_directly_to_author"],
            author_directive_metadata={"source": "legacy_scrutineer_author_context"},
            answer_contract_ref={"trace_key": "answer_contract_runtime_handoff", "available": answer_contract_runtime_result is not None},
            analyst_author_handoff_ref={"trace_key": "analyst_author_handoff_contract"},
            citation_source_handoff_ref={"trace_key": "citation_source_handoff_contract"},
        )
    )
    return PostAuthorTracePackaging(
        answer_contract_runtime_result=answer_contract_runtime_result,
        answer_contract_runtime_trace_fragment=answer_contract_runtime_trace_fragment,
        provider_diagnostics_payload=provider_diagnostics_payload(v["provider_diagnostics"]),
        weak_failure_gate_trace_fragment=weak_failure_gate_trace_fragment,
        final_answer_packet=final_answer_citation_runtime.packet,
        analyst_author_handoff_state=final_answer_citation_runtime.analyst_author_handoff_state,
        analyst_author_handoff_trace_fragment=final_answer_citation_runtime.analyst_author_handoff_trace_fragment,
        citation_source_handoff_state=final_answer_citation_runtime.citation_source_handoff_state,
        unique_source_urls=final_answer_citation_runtime.unique_source_urls,
        ordered_sources=final_answer_citation_runtime.ordered_sources,
        final_answer_source_telemetry=final_answer_citation_runtime.final_answer_source_telemetry,
        citation_source_handoff_trace_fragment=final_answer_citation_runtime.citation_source_handoff_trace_fragment,
        economist_handoff_state=economist_handoff_state,
        economist_handoff_trace_fragment=economist_handoff_trace_fragment,
        synthesis_evaluator_supplemental_search_handoff_trace_fragment=synthesis_evaluator_supplemental_search_handoff_trace_fragment,
        scrutineer_remediation_handoff_trace_fragment=scrutineer_remediation_handoff_trace_fragment,
        trace_field_fragments=(
            final_answer_citation_runtime.packet_trace_fragment,
            final_answer_citation_runtime.citation_source_handoff_trace_fragment,
            economist_handoff_trace_fragment,
        ),
    )

def build_post_author_output_packaging_from_scope(
    runtime_values: Mapping[str, Any],
    *,
    trace_packaging: PostAuthorTracePackaging,
    code_version_metadata_builder: Any = current_code_version_metadata,
) -> PostAuthorOutputPackaging:
    final_output_metadata = build_final_output_metadata(
        report=runtime_values["report"],
        latency_seconds=runtime_values["latency_seconds"],
        cost_snapshot=runtime_values["cost_snapshot"],
    )
    v = {
        **{key: runtime_values[key] for key in _POST_AUTHOR_OUTPUT_SCOPE_KEYS},
        **trace_packaging.runtime_values(),
        "final_output_metadata": final_output_metadata,
        "output_word_count": final_output_metadata["output_word_count"],
    }
    execution_trace = build_execution_trace_projection(v)
    runtime_trace_export_attachment = attach_runtime_trace_export_compatibility_payloads(
        execution_trace,
        recovered_passages=v["source_class_projection_handoff"].recovered_source_class_passages,
        final_top_evidence=v["final_top_evidence"],
        max_iterations=v["max_iterations"],
        evidence_bundle_source_class_counts=v["source_class_evidence_bundle_observability_telemetry"].get(
            "source_class_strong_satisfaction_counts"
        ),
        session_payload=v["new_session"],
        logger=v["run_log"],
    )
    return PostAuthorOutputPackaging(
        execution_trace=execution_trace,
        output_word_count=final_output_metadata["output_word_count"],
        execution_log_entry=build_execution_log_entry_projection(
            v,
            execution_trace=execution_trace,
            source_class_recovery_validation_packet=runtime_trace_export_attachment.source_class_recovery_validation_packet,
            code_version_metadata=code_version_metadata_builder(),
        ),
    )

def build_run_outcome_from_scope(runtime_values: Mapping[str, Any]) -> Any:
    v = {key: runtime_values[key] for key in _RUN_OUTCOME_SCOPE_KEYS}
    return build_run_outcome(
        session_id=v["session_id"], run_id=v["run_id"], session_title=v["session_title"], query=v["query"],
        core_topic=v["core_topic"], report=v["report"], final_top_evidence=v["final_top_evidence"],
        seen_urls=list(v["seen_urls"]), collected_images=list(v["collected_images"]), execution_trace=v["execution_trace"],
        failure_card_payload=v["failure_card_payload"], session_payload=v["new_session"], cost_snapshot=v["cost_snapshot"],
        latency_seconds=v["latency_seconds"], intent=v["intent"], complexity=v["complexity"], corpus_state=v["corpus_state"],
        pipeline_config=v["pipeline_config_payload"], kb_instrumentation=v["kb_instrumentation"], kb_warning=v["kb_warning"],
        author_streamed=bool(v["config"].author_stream_display) and not v["quantitative_guard_stream_buffered"],
    )
