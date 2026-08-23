"""Bounded final-answer runtime assembly helpers for AG-90B.

This module is a compatibility-shell extraction from ``pipeline_orchestrator``.
It wires already-computed runtime facts into FinalAnswerPacket, Author payload,
and legacy citation/source handoff projections.  It does not retrieve, select
providers, select evidence, format citations, call models, or change prompts
except through the existing FinalAnswerPacket Author payload adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.analyst_author_handoff_contract import build_analyst_author_handoff_state
from core.citation_source_handoff_contract import execute_citation_source_handoff
from core.final_answer_packet import (
    FinalAnswerAuthorInputPayload,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
)
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    build_packet_derived_citation_source_handoff_state,
    derive_author_input_payload,
    final_answer_packet_compatibility_refs,
    final_answer_packet_trace_fragment,
)
from core.source_class_recovery import build_source_class_observability_telemetry


@dataclass(frozen=True, slots=True)
class FinalAnswerAuthorRuntimeAssembly:
    """Pre-Author packet and payload assembly output."""

    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload | None
    author_prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_provider: str | None
    author_model: str | None
    source_obligation_projection: Any
    author_input_blocked: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FinalAnswerCitationRuntimeAssembly:
    """Post-Author packet/citation/source compatibility assembly output."""

    packet: FinalAnswerPacket
    analyst_author_handoff_state: Any
    analyst_author_handoff_trace_fragment: dict[str, Any]
    citation_source_handoff_state: Any
    citation_source_handoff_trace_fragment: dict[str, Any]
    unique_source_urls: dict[str, Any]
    ordered_sources: list[str]
    final_answer_source_telemetry: dict[str, Any]
    packet_trace_fragment: dict[str, Any]


def assemble_final_answer_author_runtime(
    *,
    run_id: str,
    query: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet_telemetry: Mapping[str, Any] | None,
    final_top_evidence: Sequence[Mapping[str, Any]],
    author_evidence: Sequence[Mapping[str, Any]],
    ordered_sources: Sequence[str],
    unique_source_urls: Mapping[str, Any],
    query_lineage_refs: Mapping[str, Any],
    corpus_weak: bool,
    failure_card_payload: Mapping[str, Any],
    conflicts_present: bool,
    synth_was_insufficient: bool,
    author_notes: str,
    author_prompt: str,
    author_system_prompt_key: str,
    author_effort: str,
    author_provider: str | None = None,
    author_model: str | None = None,
    answer_contract_projection: Any | None = None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    run_contract_projection: Mapping[str, Any] | None = None,
    sufficiency_judgment_projection: Mapping[str, Any] | None = None,
) -> FinalAnswerAuthorRuntimeAssembly:
    """Build packet and Author payload from already-computed runtime facts."""

    legacy_source_obligation_projection = build_source_class_observability_telemetry(
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet_telemetry,
        final_top_evidence=final_top_evidence,
        final_answer_source_ids=None,
    ).get("official_current_source_custody")
    source_obligation_projection = (
        evidence_ledger_projection or legacy_source_obligation_projection
    )
    packet = build_final_answer_packet(
        run_id=run_id,
        final_evidence=final_top_evidence,
        author_evidence=author_evidence,
        ordered_sources=ordered_sources,
        unique_source_urls=unique_source_urls,
        final_answer_source_telemetry=None,
        source_obligation_projection=source_obligation_projection,
        answer_contract_projection=answer_contract_projection,
        run_contract_projection=run_contract_projection,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        query_lineage_refs=query_lineage_refs,
        evidence_sufficient=None,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        conflicts_present=conflicts_present,
        synth_was_insufficient=synth_was_insufficient,
        author_notes=author_notes,
    )
    if packet.readiness_status is FinalAnswerReadinessStatus.BLOCKED:
        return FinalAnswerAuthorRuntimeAssembly(
            packet=packet,
            author_payload=None,
            author_prompt=author_prompt,
            author_system_prompt_key=author_system_prompt_key,
            author_effort=author_effort,
            author_provider=author_provider,
            author_model=author_model,
            source_obligation_projection=source_obligation_projection,
            author_input_blocked=True,
            blocked_reason="blocked_final_answer_packet",
        )
    quantitative_preflight = packet.quantitative_fap_authority_preflight()
    quantitative_diagnostic = dict(quantitative_preflight.get("diagnostic") or {})
    if quantitative_diagnostic.get("status") != "ready":
        packet = packet.with_quantitative_authority_block(quantitative_diagnostic)
        return FinalAnswerAuthorRuntimeAssembly(
            packet=packet,
            author_payload=None,
            author_prompt=author_prompt,
            author_system_prompt_key=author_system_prompt_key,
            author_effort=author_effort,
            author_provider=author_provider,
            author_model=author_model,
            source_obligation_projection=source_obligation_projection,
            author_input_blocked=True,
            blocked_reason="quantitative_fap_authority_blocked",
        )
    packet, payload = derive_author_input_payload(
        packet,
        prompt=author_prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_provider=author_provider,
        author_model=author_model,
    )
    return FinalAnswerAuthorRuntimeAssembly(
        packet=packet,
        author_payload=payload,
        author_prompt=payload.prompt,
        author_system_prompt_key=payload.author_system_prompt_key,
        author_effort=payload.author_effort,
        author_provider=payload.author_provider,
        author_model=payload.author_model,
        source_obligation_projection=source_obligation_projection,
    )


def _source_telemetry_ref(final_source_telemetry_inputs: Any) -> dict[str, Any]:
    return {
        "source_ids": list(final_source_telemetry_inputs.source_ids),
        "unique_source_url_count": (
            final_source_telemetry_inputs.unique_source_url_count
        ),
        "ordered_sources": list(final_source_telemetry_inputs.ordered_sources),
        "final_evidence_count": final_source_telemetry_inputs.final_evidence_count,
        "final_answer_source_telemetry": dict(
            final_source_telemetry_inputs.final_answer_source_telemetry
        ),
    }


def assemble_final_answer_citation_runtime(
    *,
    packet: FinalAnswerPacket,
    run_id: str,
    final_answer_source_telemetry: Mapping[str, Any],
    final_source_telemetry_inputs: Any,
    answer_contract_ref: Any,
    analyst_skipped: bool,
    analyst_skip_reason: str | None,
    post_retrieval_fast_path_used: bool,
    pre_analyst_gate_signals: Mapping[str, Any],
    analyst_skipped_after_economist: bool,
    analyst_after_economist_skip_reason: str | None,
    economist_output_used_as_analysis: bool,
    analyst_evidence: Sequence[Mapping[str, Any]],
    analyst_context_prefix: str,
    linkup_block_included: bool,
    quantitative_packet_injected: bool,
    missing_target_metric_directive_emitted: bool,
    corpus_weak: bool,
    failure_card_payload: Mapping[str, Any],
    author_notes: str,
    author_evidence: Sequence[Mapping[str, Any]],
    selected_evidence: Sequence[Mapping[str, Any]],
    final_evidence: Sequence[Mapping[str, Any]],
    ordered_sources: Sequence[str],
    unique_source_urls: Mapping[str, Any],
    author_evidence_block: str,
    author_prompt: str,
    complexity: str,
    author_system_prompt_key: str,
    author_effort: str,
    includes_analysis: bool,
    includes_recency_notes: bool,
    includes_author_notes: bool,
    image_context_active: bool,
    pre_analyst_gate_ref: Any,
    weak_failure_gate_state: Any,
    retrieval_loop_state: Any,
    router_query_preparation_state: Any,
    run_kernel_final_answer_ref: Mapping[str, Any] | None = None,
) -> FinalAnswerCitationRuntimeAssembly:
    """Refresh packet observations and build legacy Author/citation handoffs."""

    analyst_author_handoff_state = build_analyst_author_handoff_state(
        run_id=run_id,
        analyst_skipped=analyst_skipped,
        analyst_skip_reason=analyst_skip_reason,
        post_retrieval_fast_path_used=post_retrieval_fast_path_used,
        pre_analyst_gate_signals=pre_analyst_gate_signals,
        analyst_skipped_after_economist=analyst_skipped_after_economist,
        analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
        economist_output_used_as_analysis=economist_output_used_as_analysis,
        analyst_evidence=analyst_evidence,
        analyst_context_prefix=analyst_context_prefix,
        linkup_block_included=linkup_block_included,
        quantitative_packet_injected=quantitative_packet_injected,
        missing_target_metric_directive_emitted=missing_target_metric_directive_emitted,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        author_notes=author_notes,
        author_evidence=author_evidence,
        selected_evidence=selected_evidence,
        final_evidence=final_evidence,
        ordered_sources=ordered_sources,
        unique_source_urls=unique_source_urls,
        author_evidence_block=author_evidence_block,
        source_telemetry_ref=_source_telemetry_ref(final_source_telemetry_inputs),
        author_prompt=author_prompt,
        complexity=complexity,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        includes_analysis=includes_analysis,
        includes_recency_notes=includes_recency_notes,
        includes_author_notes=includes_author_notes,
        image_context_active=image_context_active,
        pre_analyst_gate_ref=pre_analyst_gate_ref,
        weak_failure_gate_state=weak_failure_gate_state,
        retrieval_loop_state=retrieval_loop_state,
        router_query_preparation_state=router_query_preparation_state,
        answer_contract_ref=answer_contract_ref,
        final_evidence_ref=final_answer_packet_compatibility_refs(packet)[
            "final_evidence_ref"
        ],
    )
    analyst_author_handoff_trace_fragment = (
        analyst_author_handoff_state.to_trace_fragment()
    )
    packet = packet.with_citation_observations(final_answer_source_telemetry)
    compatibility_refs = final_answer_packet_compatibility_refs(
        packet,
        final_evidence_snapshot_recorded=bool(
            final_source_telemetry_inputs.final_evidence_snapshot_payload
        ),
    )
    citation_source_handoff_state = build_packet_derived_citation_source_handoff_state(
        packet,
        run_id=run_id,
        ledger_ref=compatibility_refs["ledger_ref"],
        answer_contract_ref=answer_contract_ref,
        analyst_author_handoff_state=analyst_author_handoff_state,
        source_telemetry_ref=compatibility_refs["source_telemetry_ref"],
        run_kernel_final_answer_ref=run_kernel_final_answer_ref,
    )
    citation_source_handoff = execute_citation_source_handoff(
        citation_source_handoff_state
    )
    return FinalAnswerCitationRuntimeAssembly(
        packet=packet,
        analyst_author_handoff_state=analyst_author_handoff_state,
        analyst_author_handoff_trace_fragment=analyst_author_handoff_trace_fragment,
        citation_source_handoff_state=citation_source_handoff_state,
        citation_source_handoff_trace_fragment=(
            citation_source_handoff_state.to_trace_fragment()
        ),
        unique_source_urls=citation_source_handoff.unique_source_urls,
        ordered_sources=citation_source_handoff.ordered_sources,
        final_answer_source_telemetry=(
            citation_source_handoff.final_answer_source_telemetry
        ),
        packet_trace_fragment=final_answer_packet_trace_fragment(packet),
    )


def assemble_final_answer_author_runtime_from_scope(
    runtime_scope: Mapping[str, Any],
) -> FinalAnswerAuthorRuntimeAssembly:
    """Scope-based compatibility shell for the orchestrator callsite.

    Only the whitelisted keys below are consumed; the scope is not serialized or
    traced.  This keeps the orchestrator thin without moving evidence selection,
    retrieval, provider routing, prompt prose, or citation formatting authority.
    """

    return assemble_final_answer_author_runtime(
        run_id=runtime_scope["run_id"],
        query=runtime_scope["query"],
        intent=runtime_scope["intent"],
        report_type=runtime_scope["report_type"],
        query_type=runtime_scope["query_type"],
        core_topic=runtime_scope["core_topic"],
        primary_entity=runtime_scope["primary_entity"],
        anchor_packet_telemetry=runtime_scope["anchor_packet_telemetry"],
        final_top_evidence=runtime_scope["final_top_evidence"],
        author_evidence=runtime_scope["author_evidence"],
        ordered_sources=runtime_scope["ordered_sources"],
        unique_source_urls=runtime_scope["unique_source_urls"],
        query_lineage_refs=runtime_scope["query_authority"].to_trace_fragment(),
        corpus_weak=runtime_scope["corpus_weak"],
        failure_card_payload={
            "show": runtime_scope["_pre_gate_failure_card_show"],
            "reason": runtime_scope["_pre_gate_failure_card_reason"],
        },
        conflicts_present=bool(runtime_scope["scrutineer_flags"]),
        synth_was_insufficient=runtime_scope["synth_was_insufficient"],
        author_notes=runtime_scope["author_notes"],
        author_prompt=runtime_scope["author_prompt"],
        author_system_prompt_key=runtime_scope["author_system_prompt_key"],
        author_effort=runtime_scope["_author_effort"],
        author_provider=runtime_scope.get("_author_provider"),
        author_model=runtime_scope.get("_author_model"),
        answer_contract_projection=runtime_scope.get("answer_contract_projection"),
        evidence_ledger_projection=runtime_scope.get("evidence_ledger_projection"),
        run_contract_projection=runtime_scope.get("run_contract_projection"),
        sufficiency_judgment_projection=runtime_scope.get(
            "sufficiency_judgment_projection"
        ),
    )


def assemble_final_answer_citation_runtime_from_scope(
    runtime_scope: Mapping[str, Any],
    *,
    analyst_evidence: Sequence[Mapping[str, Any]],
) -> FinalAnswerCitationRuntimeAssembly:
    """Scope-based post-Author compatibility shell for the orchestrator."""

    return assemble_final_answer_citation_runtime(
        packet=runtime_scope["final_answer_packet"],
        run_id=runtime_scope["run_id"],
        final_answer_source_telemetry=runtime_scope["final_answer_source_telemetry"],
        final_source_telemetry_inputs=runtime_scope["final_source_telemetry_inputs"],
        answer_contract_ref=runtime_scope["answer_contract_runtime_result"],
        analyst_skipped=runtime_scope["analyst_skipped"],
        analyst_skip_reason=runtime_scope["analyst_skip_reason"],
        post_retrieval_fast_path_used=runtime_scope["post_retrieval_fast_path_used"],
        pre_analyst_gate_signals=runtime_scope["pre_analyst_gate_signals"],
        analyst_skipped_after_economist=runtime_scope["analyst_skipped_after_economist"],
        analyst_after_economist_skip_reason=runtime_scope[
            "analyst_after_economist_skip_reason"
        ],
        economist_output_used_as_analysis=runtime_scope[
            "economist_output_used_as_analysis"
        ],
        analyst_evidence=analyst_evidence,
        analyst_context_prefix=runtime_scope["analyst_cached_prefix"],
        linkup_block_included=bool(runtime_scope["linkup_block"]),
        quantitative_packet_injected=bool(
            runtime_scope["analyst_quant_packet_handoff_telemetry"].get(
                "analyst_quant_packet_injected"
            )
        ),
        missing_target_metric_directive_emitted=runtime_scope[
            "missing_target_metric_directive_emitted"
        ],
        corpus_weak=runtime_scope["corpus_weak"],
        failure_card_payload=runtime_scope["failure_card_payload"],
        author_notes=runtime_scope["author_notes"],
        author_evidence=runtime_scope["author_evidence"],
        selected_evidence=runtime_scope["final_top_evidence"],
        final_evidence=runtime_scope["final_top_evidence"],
        ordered_sources=runtime_scope["ordered_sources"],
        unique_source_urls=runtime_scope["unique_source_urls"],
        author_evidence_block=runtime_scope["author_evidence_block"],
        author_prompt=runtime_scope["author_prompt"],
        complexity=runtime_scope["complexity"],
        author_system_prompt_key=runtime_scope["author_system_prompt_key"],
        author_effort=runtime_scope["_author_effort"],
        includes_analysis=(
            runtime_scope["complexity"] != "low"
            and (not runtime_scope["corpus_weak"] or runtime_scope["_efp_author"])
            and not runtime_scope["_relevance_low"]
        ),
        includes_recency_notes=bool(runtime_scope["recency_notes"]),
        includes_author_notes=bool(runtime_scope["author_notes"]),
        image_context_active=bool(runtime_scope["image_context"]),
        pre_analyst_gate_ref=runtime_scope["pre_analyst_gate_contract"],
        weak_failure_gate_state=runtime_scope["weak_failure_gate_contract_state"],
        retrieval_loop_state=runtime_scope["retrieval_loop_contract_state"],
        router_query_preparation_state=runtime_scope[
            "router_query_preparation_contract"
        ],
        run_kernel_final_answer_ref=runtime_scope.get("run_kernel_final_answer_ref"),
    )


__all__ = [
    "FinalAnswerAuthorRuntimeAssembly",
    "FinalAnswerCitationRuntimeAssembly",
    "assemble_final_answer_author_runtime",
    "assemble_final_answer_author_runtime_from_scope",
    "assemble_final_answer_citation_runtime",
    "assemble_final_answer_citation_runtime_from_scope",
]
