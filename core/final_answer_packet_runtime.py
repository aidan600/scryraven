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

SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION = "blocked_final_answer_packet_safe_summary_v1"


def _safe_text(value: Any, *, limit: int = 240) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:limit]


def _safe_text_list(value: Any, *, limit: int = 240) -> list[str]:
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = ()
    result: list[str] = []
    for item in values:
        clean = _safe_text(item, limit=limit)
        if clean and clean not in result:
            result.append(clean)
    return result


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _count_from_sources(
    *,
    key: str,
    sequence_key: str,
    projection: Mapping[str, Any],
    payload_ref: Mapping[str, Any],
    authority_payload: Mapping[str, Any],
) -> int:
    for source in (projection, payload_ref, authority_payload):
        value = _optional_int(source.get(key))
        if value is not None:
            return value
    sequence = payload_ref.get(sequence_key)
    if isinstance(sequence, Sequence) and not isinstance(sequence, (str, bytes)):
        return len(sequence)
    return 0


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def build_safe_blocked_fap_summary(
    final_answer_authority_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return compact no-raw blocked-FAP details for failure observability."""

    projection = _safe_mapping(final_answer_authority_projection)
    payload_ref = _safe_mapping(projection.get("author_payload_ref"))
    if not payload_ref and projection.get("status") == "blocked":
        payload_ref = projection
        projection = {}
    if payload_ref.get("status") != "blocked":
        return {}
    authority_payload = _safe_mapping(payload_ref.get("authority_payload"))
    final_answer_allowed = authority_payload.get("final_answer_allowed")
    if not isinstance(final_answer_allowed, bool):
        final_answer_allowed = None
    return _without_empty(
        {
            "schema_version": SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION,
            "blocked_fap": True,
            "packet_id": _safe_text(
                payload_ref.get("packet_id")
                or projection.get("packet_id")
                or authority_payload.get("packet_id"),
                limit=160,
            ),
            "status": "blocked",
            "readiness_status": _safe_text(
                payload_ref.get("readiness_status")
                or projection.get("readiness_status")
                or authority_payload.get("readiness_status"),
                limit=120,
            ),
            "readiness_reasons": _safe_text_list(
                payload_ref.get("readiness_reasons")
                or projection.get("readiness_reasons")
                or authority_payload.get("readiness_reasons"),
                limit=160,
            ),
            "author_input_deferred": bool(payload_ref.get("author_input_deferred")),
            "blocked_before_author_input": bool(
                payload_ref.get("blocked_before_author_input")
            ),
            "final_answer_allowed": final_answer_allowed,
            "final_answer_posture": _safe_text(
                payload_ref.get("final_answer_posture")
                or authority_payload.get("final_answer_posture"),
                limit=120,
            ),
            "sufficiency_decision": _safe_text(
                payload_ref.get("sufficiency_decision")
                or authority_payload.get("sufficiency_decision"),
                limit=120,
            ),
            "missing_source_obligation_count": _count_from_sources(
                key="missing_source_obligation_count",
                sequence_key="missing_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "partial_source_obligation_count": _count_from_sources(
                key="partial_source_obligation_count",
                sequence_key="partial_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "satisfied_source_obligation_count": _count_from_sources(
                key="satisfied_source_obligation_count",
                sequence_key="satisfied_source_obligations",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "source_bound_numeric_unknown_count": _count_from_sources(
                key="source_bound_numeric_unknown_count",
                sequence_key="source_bound_numeric_unknowns",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "mandatory_caveat_count": _count_from_sources(
                key="mandatory_caveat_count",
                sequence_key="mandatory_caveats",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "prohibited_upgrade_count": _count_from_sources(
                key="prohibited_upgrade_count",
                sequence_key="prohibited_upgrades",
                projection=projection,
                payload_ref=payload_ref,
                authority_payload=authority_payload,
            ),
            "claim_postures": _safe_text_list(
                payload_ref.get("claim_postures")
                or authority_payload.get("claim_postures"),
                limit=160,
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class FinalAnswerPacketPreparationResult:
    """Packet, optional Author payload, and observation from the bounded executor."""

    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload | None
    author_payload_ref: Mapping[str, Any]
    author_prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_system_prompt: str
    observation: Observation
    author_provider: str | None
    author_model: str | None
    author_input_blocked: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FinalAnswerPacketAuthorHandoff:
    """RunKernel-reduced FinalAnswerPacket and optional Author payload handoff."""

    action: AuthorizedAction
    preparation: FinalAnswerPacketPreparationResult
    packet: FinalAnswerPacket
    author_payload: FinalAnswerAuthorInputPayload | None
    author_payload_ref: Mapping[str, Any]
    author_prompt: str
    author_system_prompt_key: str
    author_effort: str
    author_provider: str | None
    author_model: str | None
    author_system_prompt: str
    author_input_blocked: bool = False
    blocked_reason: str | None = None


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


def _safe_mapping_sequence(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in values if isinstance(item, Mapping)]


def _blocked_author_payload_ref(packet: FinalAnswerPacket) -> dict[str, Any]:
    readiness_status = packet.readiness_status.value
    readiness_reasons = list(packet.readiness_reasons)
    missing_source_obligations = _safe_mapping_sequence(
        packet.missing_required_obligations
    )
    partial_source_obligations = _safe_mapping_sequence(packet.partial_obligations)
    satisfied_source_obligations = _safe_mapping_sequence(packet.satisfied_obligations)
    source_bound_numeric_unknowns = _safe_mapping_sequence(
        packet.source_bound_numeric_unknowns
    )
    source_bound_numeric_resolutions = _safe_mapping_sequence(
        packet.source_bound_numeric_resolutions
    )
    claim_postures = [
        item.value if hasattr(item, "value") else str(item)
        for item in packet.claim_postures
    ]
    authority_payload = {
        "packet_id": packet.packet_id,
        "readiness_status": readiness_status,
        "readiness_reasons": readiness_reasons,
        "sufficiency_decision": packet.sufficiency_decision,
        "final_answer_posture": packet.final_answer_posture,
        "final_answer_allowed": bool(packet.final_answer_allowed),
        "required_obligations_satisfied": packet.required_obligations_satisfied,
        "claim_postures": claim_postures,
        "missing_source_obligation_count": len(missing_source_obligations),
        "partial_source_obligation_count": len(partial_source_obligations),
        "satisfied_source_obligation_count": len(satisfied_source_obligations),
        "source_bound_numeric_unknown_count": len(source_bound_numeric_unknowns),
        "mandatory_caveat_count": len(packet.mandatory_caveats),
        "prohibited_upgrade_count": len(packet.prohibited_upgrades),
        "author_input_deferred": True,
    }
    return {
        "packet_id": packet.packet_id,
        "status": "blocked",
        "prompt_text_included": False,
        "author_input_deferred": True,
        "blocked_before_author_input": True,
        "readiness_status": readiness_status,
        "readiness_reasons": readiness_reasons,
        "author_evidence_ids": [],
        "citation_source_ids": [],
        "citation_ineligible_refs": [],
        "missing_source_obligations": missing_source_obligations,
        "partial_source_obligations": partial_source_obligations,
        "satisfied_source_obligations": satisfied_source_obligations,
        "source_bound_numeric_unknowns": source_bound_numeric_unknowns,
        "source_bound_numeric_resolutions": source_bound_numeric_resolutions,
        "final_answer_posture": packet.final_answer_posture,
        "sufficiency_decision": packet.sufficiency_decision,
        "claim_postures": claim_postures,
        "mandatory_caveat_count": len(packet.mandatory_caveats),
        "prohibited_upgrade_count": len(packet.prohibited_upgrades),
        "authority_payload": authority_payload,
        "raw_prompt_included": False,
        "provider_payload_included": False,
        "raw_content_included": False,
        "final_text_included": False,
        "model_request_visible": False,
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
    sufficiency_judgment_projection: Mapping[str, Any] | None = None,
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
        sufficiency_judgment_projection=sufficiency_judgment_projection,
    )
    packet_projection = assembly.packet.to_dict()
    if assembly.author_payload is None:
        payload_ref = _blocked_author_payload_ref(assembly.packet)
    else:
        payload_ref = assembly.author_payload.to_trace_ref()
    observation_payload = {
        "owner": "RunKernel.FinalAnswerPacket",
        "packet_projection": packet_projection,
        "author_payload_ref": payload_ref,
        "author_input_blocked": assembly.author_input_blocked,
        "blocked_reason": assembly.blocked_reason,
        "readiness_status": packet_projection.get("readiness_status"),
        "readiness_reasons": packet_projection.get("readiness_reasons", []),
        "citation_authority_available": "citation_eligible" in packet_projection
        and "citation_ineligible" in packet_projection,
        "missing_source_obligation_count": len(
            payload_ref.get("missing_source_obligations", []) or []
        ),
        "partial_source_obligation_count": len(
            payload_ref.get("partial_source_obligations", []) or []
        ),
        "satisfied_source_obligation_count": len(
            payload_ref.get("satisfied_source_obligations", []) or []
        ),
        "source_bound_numeric_unknown_count": len(
            payload_ref.get("source_bound_numeric_unknowns", []) or []
        ),
        "mandatory_caveat_count": payload_ref.get("mandatory_caveat_count", 0),
        "prohibited_upgrade_count": payload_ref.get("prohibited_upgrade_count", 0),
        "author_authority_payload_ref": payload_ref.get("authority_payload", {}),
        "sufficiency_judgment_consumed": bool(sufficiency_judgment_projection),
        "sufficiency_decision": (
            sufficiency_judgment_projection.get("decision")
            if isinstance(sufficiency_judgment_projection, Mapping)
            else None
        ),
        **_ledger_summary(evidence_ledger_projection),
    }
    return FinalAnswerPacketPreparationResult(
        packet=assembly.packet,
        author_payload=assembly.author_payload,
        author_payload_ref=payload_ref,
        author_prompt=assembly.author_prompt,
        author_system_prompt_key=assembly.author_system_prompt_key,
        author_effort=assembly.author_effort,
        author_system_prompt=author_system_prompt,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
            status=RunStageStatus.COMPLETED,
            payload=observation_payload,
        ),
        author_provider=author_provider,
        author_model=author_model,
        author_input_blocked=assembly.author_input_blocked,
        blocked_reason=assembly.blocked_reason,
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
        sufficiency_judgment_projection=runtime_scope.get(
            "sufficiency_judgment_projection"
        ),
    )


def prepare_final_answer_packet_author_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
    *,
    default_system: Mapping[str, str],
) -> FinalAnswerPacketAuthorHandoff:
    """Authorize, execute, and reduce the FinalAnswerPacket Author handoff."""

    action = run_kernel.authorize_final_answer_packet_prepare(
        inputs={
            "candidate_count": len(runtime_scope["final_top_evidence"]),
            "author_evidence_count": len(runtime_scope["author_evidence"]),
            "evidence_ledger_available": bool(
                runtime_scope.get("evidence_ledger_projection")
            ),
            "run_contract_available": bool(runtime_scope.get("run_contract_projection")),
            "run_contract_id": runtime_scope["run_contract_projection"].get(
                "contract_id"
            ),
            "sufficiency_judgment_available": bool(
                runtime_scope.get("sufficiency_judgment_projection")
            ),
            "sufficiency_decision": runtime_scope[
                "sufficiency_judgment_projection"
            ].get("decision"),
        }
    )
    preparation = execute_final_answer_packet_prepare_action_from_scope(
        action,
        runtime_scope,
        default_system=default_system,
    )
    run_kernel.reduce(preparation.observation)
    payload = preparation.author_payload
    if preparation.author_input_blocked:
        return FinalAnswerPacketAuthorHandoff(
            action=action,
            preparation=preparation,
            packet=preparation.packet,
            author_payload=None,
            author_payload_ref=preparation.author_payload_ref,
            author_prompt=preparation.author_prompt,
            author_system_prompt_key=preparation.author_system_prompt_key,
            author_effort=preparation.author_effort,
            author_provider=preparation.author_provider,
            author_model=preparation.author_model,
            author_system_prompt=preparation.author_system_prompt,
            author_input_blocked=True,
            blocked_reason=preparation.blocked_reason,
        )
    if payload is None:
        raise ValueError("FinalAnswerPacket preparation did not produce Author input")
    return FinalAnswerPacketAuthorHandoff(
        action=action,
        preparation=preparation,
        packet=preparation.packet,
        author_payload=payload,
        author_payload_ref=preparation.author_payload_ref,
        author_prompt=payload.prompt,
        author_system_prompt_key=payload.author_system_prompt_key,
        author_effort=payload.author_effort,
        author_provider=payload.author_provider,
        author_model=payload.author_model,
        author_system_prompt=preparation.author_system_prompt,
    )


__all__ = [
    "FinalAnswerPacketAuthorHandoff",
    "FinalAnswerPacketPreparationResult",
    "SAFE_BLOCKED_FAP_SUMMARY_SCHEMA_VERSION",
    "build_safe_blocked_fap_summary",
    "execute_final_answer_packet_prepare_action",
    "execute_final_answer_packet_prepare_action_from_scope",
    "prepare_final_answer_packet_author_handoff_from_scope",
]
