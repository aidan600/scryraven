"""Runtime adapter for AG-89D FinalAnswerPacket construction and projection."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.citation_source_handoff_contract import build_citation_source_handoff_state
from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_TRACE_KEY,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    ClaimPosture,
    EvidenceAuthorityStatus,
    FinalAnswerAuthorInputPayload,
    FinalAnswerPacket,
    FinalEvidenceRecord,
    SourceObligationRecord,
    SourceObligationStatus,
)
from core.official_current_source_custody import OfficialCurrentSourceCustodyState


def _hash_or_none(text: Any) -> tuple[str | None, int | None]:
    if text is None:
        return None, None
    value = str(text or "")
    if not value:
        return None, 0
    from hashlib import sha256

    return sha256(value.encode("utf-8")).hexdigest(), len(value)


def _evidence_record_from_passage(
    passage: Mapping[str, Any],
    *,
    position: int,
    packet_id: str,
    status: EvidenceAuthorityStatus = EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
    reason: str | None = None,
) -> FinalEvidenceRecord:
    text_hash, text_length = _hash_or_none(passage.get("text"))
    source_id = passage.get("source_id")
    evidence_id = f"{packet_id}:e{position}"
    return FinalEvidenceRecord(
        evidence_id=evidence_id,
        status=status,
        position=position,
        source_id=source_id,
        url=str(passage.get("url") or "") or None,
        title=str(passage.get("title") or "") or None,
        source_tier=str(passage.get("source_tier") or "") or None,
        source_class=str(passage.get("source_class") or "") or None,
        text_hash=text_hash,
        text_length=text_length,
        reason=reason,
    )


def _citation_record_for_evidence(record: FinalEvidenceRecord) -> CitationEligibilityRecord:
    if record.source_id is None:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="source_id_missing",
        )
    if not record.url:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="source_url_missing",
        )
    return CitationEligibilityRecord(
        citation_id=f"{record.evidence_id}:citation",
        evidence_id=record.evidence_id,
        source_id=record.source_id,
        status=CitationEligibilityStatus.CITATION_ELIGIBLE,
        requirement=CitationRequirementStatus.CITATION_OPTIONAL,
    )


def _custody_projection_from_any(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, OfficialCurrentSourceCustodyState):
        return value.to_dict()
    if isinstance(value, Mapping):
        if "official_current_source_custody" in value:
            nested = value.get("official_current_source_custody")
            return dict(nested) if isinstance(nested, Mapping) else {}
        return dict(value)
    return {}


def _source_obligations_from_custody(projection: Any) -> tuple[SourceObligationRecord, ...]:
    custody_projection = _custody_projection_from_any(projection)
    if not custody_projection:
        return ()
    state = OfficialCurrentSourceCustodyState.from_projection(custody_projection)
    obligations: list[SourceObligationRecord] = []
    for requirement in state.requirements():
        status = (
            SourceObligationStatus.SATISFIED
            if requirement.satisfied
            else SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
        )
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"final-answer:{requirement.requirement_id}",
                source_class=requirement.source_class,
                status=status,
                custody_requirement_id=requirement.requirement_id,
                satisfied_candidate_ids=tuple(requirement.satisfied_candidate_ids),
                reason=requirement.unsatisfied_reason,
            )
        )
    return tuple(obligations)


def _custody_summary(projection: Any) -> dict[str, Any]:
    custody_projection = _custody_projection_from_any(projection)
    if not custody_projection:
        return {"available": False, "custody_authority": "OfficialCurrentSourceCustodyState"}
    state = OfficialCurrentSourceCustodyState.from_projection(custody_projection)
    requirements = state.requirements()
    return {
        "available": True,
        "custody_authority": "OfficialCurrentSourceCustodyState",
        "requirements": [requirement.to_dict() for requirement in requirements],
        "satisfied_source_classes": [r.source_class for r in requirements if r.satisfied],
        "unsatisfied_source_classes": [r.source_class for r in requirements if not r.satisfied],
    }


def _postures(
    *,
    evidence_sufficient: bool | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    conflicts_present: bool | None,
    synth_was_insufficient: bool | None,
    source_obligations: Sequence[SourceObligationRecord],
) -> tuple[ClaimPosture, ...]:
    out: list[ClaimPosture] = []
    if evidence_sufficient is True:
        out.append(ClaimPosture.DIRECTLY_SOURCED)
    if corpus_weak:
        out.append(ClaimPosture.WEAK_CORPUS_AUTHORIZED)
    if failure_card_payload and failure_card_payload.get("show"):
        out.append(ClaimPosture.FAILURE_CARD_AUTHORIZED)
    if evidence_sufficient is False or synth_was_insufficient:
        out.append(ClaimPosture.INSUFFICIENT_EVIDENCE)
    if conflicts_present:
        out.append(ClaimPosture.CONFLICT_PRESERVED)
    if any(o.status is SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED for o in source_obligations):
        out.append(ClaimPosture.INSUFFICIENT_EVIDENCE)
    if not out:
        out.append(ClaimPosture.DIRECTLY_SOURCED)
    return tuple(dict.fromkeys(out))


def _mandatory_caveats(
    *,
    author_notes: str | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    source_obligations: Sequence[SourceObligationRecord],
    synth_was_insufficient: bool | None,
) -> tuple[str, ...]:
    caveats: list[str] = []
    if author_notes:
        caveats.append("legacy_author_notes_present")
    if corpus_weak:
        caveats.append("weak_corpus_must_be_caveated")
    if synth_was_insufficient:
        caveats.append("synthesis_insufficient_must_be_caveated")
    if failure_card_payload and failure_card_payload.get("show"):
        reason = failure_card_payload.get("reason") or "failure_card"
        caveats.append(f"failure_card_authorized:{reason}")
    for obligation in source_obligations:
        if obligation.status is SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED:
            caveats.append(f"official_current_unsatisfied:{obligation.source_class}")
    return tuple(dict.fromkeys(caveats))


def build_final_answer_packet(
    *,
    run_id: str,
    final_evidence: Sequence[Mapping[str, Any]] | None,
    author_evidence: Sequence[Mapping[str, Any]] | None = None,
    ordered_sources: Sequence[Any] | None = None,
    unique_source_urls: Mapping[str, Any] | None = None,
    final_answer_source_telemetry: Mapping[str, Any] | None = None,
    source_obligation_projection: Any | None = None,
    query_lineage_refs: Mapping[str, Any] | None = None,
    evidence_sufficient: bool | None = None,
    corpus_weak: bool | None = None,
    failure_card_payload: Mapping[str, Any] | None = None,
    conflicts_present: bool | None = None,
    synth_was_insufficient: bool | None = None,
    author_notes: str | None = None,
) -> FinalAnswerPacket:
    packet_id = f"final-answer-packet-{run_id}"
    evidence_records = tuple(
        _evidence_record_from_passage(passage, position=index, packet_id=packet_id)
        for index, passage in enumerate(final_evidence or (), start=1)
    )
    citation_records = tuple(_citation_record_for_evidence(record) for record in evidence_records)
    source_obligations = _source_obligations_from_custody(source_obligation_projection)
    author_evidence_ids = []
    author_urls = {str(p.get("url") or "") for p in (author_evidence or ())}
    for record in evidence_records:
        if not author_urls or (record.url and record.url in author_urls):
            author_evidence_ids.append(record.evidence_id)
    author_refs = {
        "status": "author_input_ready",
        "author_evidence_ids": author_evidence_ids,
        "author_evidence_count": len(author_evidence or ()),
        "ordered_sources": list(ordered_sources or ()),
        "unique_source_urls": dict(unique_source_urls or {}),
        "final_answer_source_telemetry": dict(final_answer_source_telemetry or {}),
    }
    prohibited = [
        "do_not_upgrade_citation_ineligible_evidence",
        "do_not_treat_missing_official_current_custody_as_satisfied",
    ]
    if source_obligations:
        prohibited.append("do_not_infer_source_obligation_satisfaction_from_citation_presence")
    return FinalAnswerPacket(
        packet_id=packet_id,
        evidence_records=evidence_records,
        citation_records=citation_records,
        source_obligations=source_obligations,
        official_current_custody_summary=_custody_summary(source_obligation_projection),
        claim_postures=_postures(
            evidence_sufficient=evidence_sufficient,
            corpus_weak=corpus_weak,
            failure_card_payload=failure_card_payload,
            conflicts_present=conflicts_present,
            synth_was_insufficient=synth_was_insufficient,
            source_obligations=source_obligations,
        ),
        mandatory_caveats=_mandatory_caveats(
            author_notes=author_notes,
            corpus_weak=corpus_weak,
            failure_card_payload=failure_card_payload,
            source_obligations=source_obligations,
            synth_was_insufficient=synth_was_insufficient,
        ),
        prohibited_upgrades=tuple(prohibited),
        author_input_refs=author_refs,
        query_lineage_refs=dict(query_lineage_refs or {}),
    )


def derive_author_input_payload(
    packet: FinalAnswerPacket,
    *,
    prompt: str,
    author_system_prompt_key: str,
    author_effort: str,
) -> tuple[FinalAnswerPacket, FinalAnswerAuthorInputPayload]:
    refs = packet.author_input_refs if isinstance(packet.author_input_refs, Mapping) else {}
    payload = packet.to_author_input_payload(
        prompt=prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_evidence_ids=refs.get("author_evidence_ids") if isinstance(refs.get("author_evidence_ids"), Sequence) else None,
    )
    return packet.with_author_input_payload(payload), payload


def final_answer_packet_trace_fragment(packet: FinalAnswerPacket) -> dict[str, Any]:
    return packet.to_trace_fragment()


def final_answer_packet_compatibility_refs(
    packet: FinalAnswerPacket,
    *,
    final_evidence_snapshot_recorded: bool | None = None,
) -> dict[str, Any]:
    """Return legacy final-evidence/citation refs derived from FinalAnswerPacket.

    AG-89E keeps the old handoff reference shapes only as compatibility
    projections.  Counts, source IDs, ordered sources, and source telemetry are
    read from the packet rather than reconstructed by the orchestrator.
    """

    projection = packet.to_legacy_citation_handoff_inputs()
    final_evidence_count = len(packet.evidence_allowed)
    unique_source_url_count = len(projection["unique_source_urls"])
    base_ref: dict[str, Any] = {
        "packet_id": packet.packet_id,
        "final_evidence_count": final_evidence_count,
        "authority": FINAL_ANSWER_PACKET_TRACE_KEY,
    }
    ledger_ref = dict(base_ref)
    if final_evidence_snapshot_recorded is not None:
        ledger_ref["final_evidence_snapshot_recorded"] = bool(
            final_evidence_snapshot_recorded
        )
    author_evidence_count = packet.author_input_refs.get("author_evidence_count")
    if author_evidence_count is None:
        author_evidence_count = len(packet.author_input_refs.get("author_evidence_ids", ()))
    return {
        "final_evidence_ref": {
            **base_ref,
            "author_evidence_count": int(author_evidence_count),
            "ordered_source_count": len(projection["ordered_sources"]),
            "unique_source_url_count": unique_source_url_count,
            "trace_mode": "final_answer_packet_compatibility_projection",
        },
        "ledger_ref": ledger_ref,
        "source_telemetry_ref": {
            **base_ref,
            "source_ids": [
                record.source_id
                for record in packet.evidence_allowed
                if record.source_id is not None
            ],
            "unique_source_url_count": unique_source_url_count,
            "ordered_sources": projection["ordered_sources"],
            "final_answer_source_telemetry": projection[
                "final_answer_source_telemetry"
            ],
        },
        "final_evidence_bundle_ref": {
            **base_ref,
            "citation_eligible_count": len(packet.citation_eligible),
        },
    }


def build_packet_derived_citation_source_handoff_state(
    packet: FinalAnswerPacket,
    *,
    run_id: str | None = None,
    answer_contract_ref: Any | None = None,
    analyst_author_handoff_state: Any | None = None,
    ledger_ref: Any | None = None,
    source_telemetry_ref: Mapping[str, Any] | None = None,
):
    """Demote legacy citation/source handoff inputs behind FinalAnswerPacket."""

    projection = packet.to_legacy_citation_handoff_inputs()
    compatibility_refs = final_answer_packet_compatibility_refs(packet)
    return build_citation_source_handoff_state(
        run_id=run_id,
        final_evidence=projection["final_evidence"],
        selected_evidence=projection["selected_evidence"],
        author_evidence=projection["author_evidence"],
        unique_source_urls=projection["unique_source_urls"],
        ordered_sources=projection["ordered_sources"],
        final_answer_source_telemetry=projection["final_answer_source_telemetry"],
        final_citation_observation_refs=projection["final_citation_observation_refs"],
        final_evidence_bundle_ref=compatibility_refs["final_evidence_bundle_ref"],
        ledger_ref=ledger_ref or compatibility_refs["ledger_ref"],
        answer_contract_ref=answer_contract_ref,
        analyst_author_handoff_state=analyst_author_handoff_state,
        source_telemetry_ref=source_telemetry_ref or compatibility_refs["source_telemetry_ref"],
    )


__all__ = [
    "build_final_answer_packet",
    "build_packet_derived_citation_source_handoff_state",
    "final_answer_packet_compatibility_refs",
    "derive_author_input_payload",
    "final_answer_packet_trace_fragment",
]
