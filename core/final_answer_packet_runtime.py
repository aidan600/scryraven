"""RunKernel-authorized FinalAnswerPacket preparation runtime for AG-91K."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.final_answer_packet import FinalAnswerAuthorInputPayload, FinalAnswerPacket
from core.final_answer_runtime_assembly import (
    FinalAnswerAuthorRuntimeAssembly,
    assemble_final_answer_author_runtime,
)
from core.run_kernel import (
    FINAL_ANSWER_PACKET_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.runtime_prompt_assembly import select_author_system_prompt


@dataclass(frozen=True, slots=True)
class FinalAnswerPacketPreparationResult:
    """Packet, payload, and observation produced by the bounded executor."""

    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload
    author_system_prompt: str
    observation: Observation
    author_provider: str | None
    author_model: str | None


def _author_effort(
    *,
    analyst_effort: str,
    corpus_weak: bool,
    estimate_from_priors_author: bool,
    relevance_low: bool,
) -> str:
    if (not corpus_weak or estimate_from_priors_author) and not relevance_low:
        return str(analyst_effort or "low")
    return "low"


def _author_provider_model(
    *,
    strategy: str,
    fast_provider: str | None,
    fast_model: str | None,
    smart_provider: str | None,
    smart_model: str | None,
) -> tuple[str | None, str | None]:
    if strategy in ("Fast", "Balanced"):
        return fast_provider, fast_model
    return smart_provider, smart_model


def _ledger_summary(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        return {"evidence_ledger_consumed": False}
    return {
        "evidence_ledger_consumed": projection.get("owner")
        == "RunKernel.EvidenceLedger",
        "evidence_ledger_candidate_count": projection.get("candidate_count", 0),
        "evidence_ledger_requirement_count": projection.get("requirement_count", 0),
        "evidence_ledger_gap_count": len(projection.get("custody_gaps") or ()),
    }


def execute_final_answer_packet_prepare_action(
    action: AuthorizedAction,
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
    default_system: Mapping[str, str],
    analyst_effort: str,
    estimate_from_priors_author: bool,
    relevance_low: bool,
    strategy: str,
    fast_provider: str | None,
    fast_model: str | None,
    smart_provider: str | None,
    smart_model: str | None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    answer_contract_projection: Any | None = None,
    run_contract_projection: Mapping[str, Any] | None = None,
) -> FinalAnswerPacketPreparationResult:
    """Build a FinalAnswerPacket and packet-derived Author payload."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FINAL_ANSWER_PACKET_PREPARE,
        stage=FINAL_ANSWER_PACKET_STAGE,
        expected_observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
    )
    if run_id != authorized.run_id:
        raise ValueError("packet preparation run_id must match AuthorizedAction")

    author_system_prompt, author_system_prompt_key = select_author_system_prompt(
        default_system=default_system,
        corpus_weak=corpus_weak,
        estimate_from_priors_author=estimate_from_priors_author,
    )
    author_effort = _author_effort(
        analyst_effort=analyst_effort,
        corpus_weak=corpus_weak,
        estimate_from_priors_author=estimate_from_priors_author,
        relevance_low=relevance_low,
    )
    author_provider, author_model = _author_provider_model(
        strategy=strategy,
        fast_provider=fast_provider,
        fast_model=fast_model,
        smart_provider=smart_provider,
        smart_model=smart_model,
    )

    assembly: FinalAnswerAuthorRuntimeAssembly = assemble_final_answer_author_runtime(
        run_id=run_id,
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet_telemetry=anchor_packet_telemetry,
        final_top_evidence=final_top_evidence,
        author_evidence=author_evidence,
        ordered_sources=ordered_sources,
        unique_source_urls=unique_source_urls,
        query_lineage_refs=query_lineage_refs,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        conflicts_present=conflicts_present,
        synth_was_insufficient=synth_was_insufficient,
        author_notes=author_notes,
        author_prompt=author_prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_provider=author_provider,
        author_model=author_model,
        answer_contract_projection=answer_contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        run_contract_projection=run_contract_projection,
    )
    packet_projection = assembly.packet.to_dict()
    payload_ref = assembly.author_payload.to_trace_ref()
    observation_payload = {
        "owner": "RunKernel.FinalAnswerPacket",
        "packet_projection": packet_projection,
        "author_payload_ref": payload_ref,
        "readiness_status": packet_projection.get("readiness_status"),
        "readiness_reasons": packet_projection.get("readiness_reasons", []),
        "citation_authority_available": "citation_eligible" in packet_projection
        and "citation_ineligible" in packet_projection,
        "missing_source_obligation_count": len(
            payload_ref.get("missing_source_obligations", []) or []
        ),
        "mandatory_caveat_count": payload_ref.get("mandatory_caveat_count", 0),
        "prohibited_upgrade_count": payload_ref.get("prohibited_upgrade_count", 0),
        **_ledger_summary(evidence_ledger_projection),
    }
    return FinalAnswerPacketPreparationResult(
        packet=assembly.packet,
        author_payload=assembly.author_payload,
        author_system_prompt=author_system_prompt,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
            status=RunStageStatus.COMPLETED,
            payload=observation_payload,
        ),
        author_provider=author_provider,
        author_model=author_model,
    )


def execute_final_answer_packet_prepare_action_from_scope(
    action: AuthorizedAction,
    runtime_scope: Mapping[str, Any],
    *,
    default_system: Mapping[str, str],
) -> FinalAnswerPacketPreparationResult:
    """Whitelisted pipeline-scope adapter for packet preparation."""

    return execute_final_answer_packet_prepare_action(
        action,
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
        default_system=default_system,
        analyst_effort=runtime_scope["analyst_effort"],
        estimate_from_priors_author=runtime_scope["_efp_author"],
        relevance_low=runtime_scope["_relevance_low"],
        strategy=runtime_scope["strategy"],
        fast_provider=runtime_scope["fast_provider"],
        fast_model=runtime_scope["fast_model"],
        smart_provider=runtime_scope["smart_provider"],
        smart_model=runtime_scope["smart_model"],
        evidence_ledger_projection=runtime_scope.get("evidence_ledger_projection"),
        answer_contract_projection=runtime_scope.get("answer_contract_projection"),
        run_contract_projection=runtime_scope.get("run_contract_projection"),
    )


__all__ = [
    "FinalAnswerPacketPreparationResult",
    "execute_final_answer_packet_prepare_action",
    "execute_final_answer_packet_prepare_action_from_scope",
]
