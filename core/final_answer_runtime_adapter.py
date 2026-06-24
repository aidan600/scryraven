"""Runtime adapter for AG-89D FinalAnswerPacket construction and projection."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.citation_source_handoff_contract import build_citation_source_handoff_state
from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_TRACE_KEY,
    FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    ClaimPosture,
    EvidenceAuthorityStatus,
    FinalAnswerAuthorInputPayload,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
    FinalEvidenceRecord,
    SourceObligationRecord,
    SourceObligationStatus,
)
from core.official_current_source_custody import OfficialCurrentSourceCustodyState
from core.run_authority_projection_refs import (
    RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER,
    canonical_sufficiency_judgment_projection,
    compact_sufficiency_judgment_ref,
)


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


def _citation_record_for_evidence(
    record: FinalEvidenceRecord,
    *,
    sufficiency_constrained: bool = False,
    satisfied_source_classes: frozenset[str] = frozenset(),
) -> CitationEligibilityRecord:
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
    if (
        sufficiency_constrained
        and satisfied_source_classes
        and _contract_requirement_key(record.source_class) not in satisfied_source_classes
    ):
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="not_supported_by_sufficiency_satisfied_obligation",
        )
    if sufficiency_constrained and not satisfied_source_classes:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="sufficiency_has_no_satisfied_source_obligation",
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


def _evidence_ledger_projection_from_any(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("owner") == "RunKernel.EvidenceLedger":
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


def _source_obligations_from_answer_contract(
    projection: Any,
) -> tuple[SourceObligationRecord, ...]:
    if projection is None:
        return ()
    if hasattr(projection, "fulfillment_handoff"):
        projection = getattr(projection, "fulfillment_handoff")
    if hasattr(projection, "to_dict"):
        projection = projection.to_dict()
    if hasattr(projection, "to_controller_state"):
        projection = projection.to_controller_state()
    if not isinstance(projection, Mapping):
        return ()

    satisfied_source_classes: list[str] = []
    for key in (
        "fulfilled_source_classes",
        "satisfied_source_classes",
        "source_classes_present",
    ):
        value = projection.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                text = str(item or "").strip()
                if text and text not in satisfied_source_classes:
                    satisfied_source_classes.append(text)

    source_classes: list[str] = []
    for key in (
        "unfulfilled_source_classes",
        "missing_source_classes",
        "unfulfilled_obligations",
        "missing_information",
    ):
        value = projection.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                text = str(item or "").strip()
                if text and text not in source_classes:
                    source_classes.append(text)

    obligations: list[SourceObligationRecord] = []
    for index, source_class in enumerate(satisfied_source_classes, start=1):
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"answer-contract:satisfied:{index}:{source_class}",
                source_class=source_class,
                status=SourceObligationStatus.SATISFIED,
                reason="answer_contract_fulfilled_source_obligation",
            )
        )
    for index, source_class in enumerate(source_classes, start=1):
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"answer-contract:{index}:{source_class}",
                source_class=source_class,
                status=SourceObligationStatus.MISSING_REQUIRED_SOURCE,
                reason="answer_contract_unfulfilled_source_obligation",
            )
        )
    return tuple(obligations)


def _contract_requirement_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _missing_status_for_contract_requirement(
    requirement: Mapping[str, Any],
) -> SourceObligationStatus:
    kind = str(requirement.get("requirement_kind") or "").strip()
    if kind == "official_current":
        return SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    if kind == "source_bound_numeric":
        return SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING
    return SourceObligationStatus.MISSING_REQUIRED_SOURCE


def _matching_source_obligation_records(
    requirement: Mapping[str, Any],
    obligations: Sequence[SourceObligationRecord],
) -> tuple[SourceObligationRecord, ...]:
    requirement_id = _contract_requirement_key(requirement.get("requirement_id"))
    source_class = _contract_requirement_key(requirement.get("required_source_class"))
    exact_matches: list[SourceObligationRecord] = []
    if requirement_id:
        for obligation in obligations:
            obligation_ids = (
                _contract_requirement_key(obligation.custody_requirement_id),
                _contract_requirement_key(obligation.obligation_id),
            )
            if any(
                value == requirement_id or value.endswith(f":{requirement_id}")
                for value in obligation_ids
                if value
            ):
                exact_matches.append(obligation)
    if exact_matches:
        return tuple(exact_matches)
    return tuple(
        obligation
        for obligation in obligations
        if source_class
        and _contract_requirement_key(obligation.source_class) == source_class
    )


def _source_obligations_from_run_contract(
    projection: Any,
    *,
    existing_obligations: Sequence[SourceObligationRecord] = (),
) -> tuple[SourceObligationRecord, ...]:
    if not isinstance(projection, Mapping):
        return ()
    if projection.get("owner") != "RunKernel.RunAuthorityContract":
        return ()
    obligations: list[SourceObligationRecord] = []
    for index, requirement in enumerate(projection.get("source_requirements") or (), start=1):
        if not isinstance(requirement, Mapping):
            continue
        if str(requirement.get("strictness") or "") != "required":
            continue
        source_class = str(requirement.get("required_source_class") or "").strip()
        if not source_class:
            continue
        if _matching_source_obligation_records(requirement, existing_obligations):
            continue
        obligations.append(
            SourceObligationRecord(
                obligation_id=(
                    f"run-contract:{index}:"
                    f"{requirement.get('requirement_id') or source_class}"
                ),
                source_class=source_class,
                status=_missing_status_for_contract_requirement(requirement),
                custody_requirement_id=requirement.get("requirement_id"),
                reason="run_authority_contract_required_source_obligation",
            )
        )
    return tuple(obligations)


def _dedupe_source_obligations(
    obligations: Sequence[SourceObligationRecord],
) -> tuple[SourceObligationRecord, ...]:
    out: list[SourceObligationRecord] = []
    seen: set[tuple[str, str]] = set()
    for obligation in obligations:
        key = (obligation.source_class, obligation.status.value)
        if key not in seen:
            out.append(obligation)
            seen.add(key)
    return tuple(out)


def _sufficiency_projection_from_any(value: Any) -> dict[str, Any]:
    return canonical_sufficiency_judgment_projection(value)


def _semantic_projection_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _semantic_state_facts_digest(
    *,
    summary: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> str | None:
    for source in (summary, consumption):
        digest = str(source.get("semantic_state_facts_digest") or "").strip()
        if digest:
            return digest[:128]
    return None


def _semantic_field_from_sources(
    key: str,
    *,
    consumption: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> Any | None:
    if key in consumption:
        return consumption[key]
    if consumption:
        return None
    if key in summary:
        return summary[key]
    return None


def _compact_semantic_authority_ref(projection: Any) -> dict[str, Any]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return {}

    summary = _semantic_projection_mapping(
        sufficiency.get("semantic_state_facts_summary")
    )
    consumption = _semantic_projection_mapping(sufficiency.get("semantic_consumption"))

    digest = _semantic_state_facts_digest(summary=summary, consumption=consumption)
    if not digest:
        return {}

    ref: dict[str, Any] = {
        "schema_version": FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
        "available": True,
        "sufficiency_semantic_consumed": True,
        "authority_owner": RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER,
        "semantic_state_facts_digest": digest,
    }

    summary_schema = _semantic_field_from_sources(
        "schema_version",
        consumption=consumption,
        summary=summary,
    )
    if summary_schema is not None and str(summary_schema).strip():
        ref["semantic_summary_schema_version"] = str(summary_schema).strip()

    for key in (
        "required_component_count",
        "covered_component_count",
        "satisfied_coverage_count",
        "blocker_count",
    ):
        value = _semantic_field_from_sources(
            key,
            consumption=consumption,
            summary=summary,
        )
        if value is not None:
            ref[key] = value

    required = ref.get("required_component_count")
    covered = ref.get("covered_component_count")
    if (
        "required_component_count" in ref
        and "covered_component_count" in ref
        and isinstance(required, int)
        and isinstance(covered, int)
    ):
        ref["missing_component_count"] = max(0, required - covered)

    for key in ("blocker_codes", "direct_answer_blocked", "finalization_blocked"):
        value = _semantic_field_from_sources(
            key,
            consumption=consumption,
            summary=summary,
        )
        if value is not None:
            ref[key] = value

    judgment_ref = compact_sufficiency_judgment_ref(sufficiency)
    if judgment_ref:
        ref["sufficiency_judgment_ref"] = judgment_ref

    return ref


def _status_for_sufficiency_obligation(
    obligation: Mapping[str, Any],
) -> SourceObligationStatus:
    kind = str(obligation.get("requirement_kind") or "").strip()
    if kind == "source_bound_numeric":
        return SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING
    if kind == "official_current":
        return SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    return SourceObligationStatus.MISSING_REQUIRED_SOURCE


def _source_obligations_from_sufficiency(
    projection: Any,
) -> tuple[SourceObligationRecord, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_obligations = []
    for key in (
        "missing_required_obligations",
        "partial_obligations",
        "satisfied_obligations",
        "missing_source_obligations",
        "source_obligations",
    ):
        value = packet_inputs.get(key) or sufficiency.get(key) or ()
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            raw_obligations.extend(item for item in value if isinstance(item, Mapping))
    obligations: list[SourceObligationRecord] = []
    for index, item in enumerate(raw_obligations, start=1):
        source_class = str(
            item.get("required_source_class")
            or item.get("source_class")
            or item.get("requirement_kind")
            or "required_source"
        ).strip()
        if not source_class:
            continue
        status_value = str(item.get("status") or "").strip()
        if status_value == "satisfied":
            status = SourceObligationStatus.SATISFIED
        elif status_value == "partial":
            status = SourceObligationStatus.PARTIAL
        else:
            status = _status_for_sufficiency_obligation(item)
        obligations.append(
            SourceObligationRecord(
                obligation_id=(
                    "run-sufficiency:"
                    f"{index}:{item.get('requirement_id') or source_class}"
                ),
                source_class=source_class,
                status=status,
                custody_requirement_id=item.get("requirement_id"),
                satisfied_candidate_ids=tuple(
                    str(candidate)
                    for candidate in item.get("satisfied_candidate_ids", ())
                    if str(candidate or "").strip()
                ),
                reason=str(item.get("reason") or "run_sufficiency_judgment"),
            )
        )
    return tuple(obligations)


def _claim_postures_from_sufficiency(
    projection: Any,
) -> tuple[ClaimPosture, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_postures = packet_inputs.get("claim_postures") or ()
    out: list[ClaimPosture] = []
    for item in raw_postures:
        try:
            posture = ClaimPosture(str(item))
        except ValueError:
            continue
        if posture not in out:
            out.append(posture)
    return tuple(out)


def _sufficiency_readiness(
    projection: Any,
) -> tuple[FinalAnswerReadinessStatus, tuple[str, ...]] | None:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return None
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_status = (
        "blocked"
        if packet_inputs.get("final_answer_allowed") is False
        else None
    ) or (
        packet_inputs.get("readiness_status")
        or (
            "blocked"
            if sufficiency.get("final_answer_allowed") is False
            else None
        )
        or (
            "insufficient_authorized"
            if sufficiency.get("final_answer_posture")
            in {"partial_answer", "insufficient_answer", "failure_card"}
            else "author_ready"
        )
    )
    try:
        readiness_status = FinalAnswerReadinessStatus(str(raw_status))
    except ValueError:
        readiness_status = FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    reasons = packet_inputs.get("readiness_reasons") or sufficiency.get(
        "readiness_reasons",
        (),
    )
    return readiness_status, tuple(
        dict.fromkeys(str(item) for item in reasons if str(item or "").strip())
    )


def _sufficiency_packet_inputs(projection: Any) -> dict[str, Any]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return {}
    packet_inputs = sufficiency.get("final_packet_inputs")
    return dict(packet_inputs) if isinstance(packet_inputs, Mapping) else {}


def _sufficiency_packet_items(
    projection: Any,
    key: str,
) -> tuple[str, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    value = packet_inputs.get(key) or sufficiency.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item or "").strip())
    return ()


def _sufficiency_packet_mappings(
    projection: Any,
    key: str,
) -> tuple[Mapping[str, Any], ...]:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(dict(item) for item in value if isinstance(item, Mapping))
    sufficiency = _sufficiency_projection_from_any(projection)
    fallback = sufficiency.get(key) if sufficiency else ()
    if isinstance(fallback, Sequence) and not isinstance(fallback, (str, bytes)):
        return tuple(dict(item) for item in fallback if isinstance(item, Mapping))
    return ()


def _sufficiency_packet_text(
    projection: Any,
    key: str,
) -> str | None:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if value is None:
        value = _sufficiency_projection_from_any(projection).get(key) if _sufficiency_projection_from_any(projection) else None
    text = str(value or "").strip()
    return text or None


def _sufficiency_packet_bool(
    projection: Any,
    key: str,
) -> bool | None:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if isinstance(value, bool):
        return value
    sufficiency = _sufficiency_projection_from_any(projection)
    value = sufficiency.get(key) if sufficiency else None
    return value if isinstance(value, bool) else None


def _sufficiency_packet_mapping(
    projection: Any,
    key: str,
) -> dict[str, Any]:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _sufficiency_author_ref(projection: Any) -> dict[str, Any]:
    return compact_sufficiency_judgment_ref(projection)


def _custody_summary(projection: Any) -> dict[str, Any]:
    custody_projection = _custody_projection_from_any(projection)
    evidence_ledger_projection = _evidence_ledger_projection_from_any(projection)
    custody_authority = (
        "RunKernel.EvidenceLedger"
        if evidence_ledger_projection
        else "OfficialCurrentSourceCustodyState"
    )
    if not custody_projection:
        return {"available": False, "custody_authority": custody_authority}
    state = OfficialCurrentSourceCustodyState.from_projection(custody_projection)
    requirements = state.requirements()
    summary = {
        "available": True,
        "custody_authority": custody_authority,
        "requirements": [requirement.to_dict() for requirement in requirements],
        "satisfied_source_classes": [r.source_class for r in requirements if r.satisfied],
        "unsatisfied_source_classes": [r.source_class for r in requirements if not r.satisfied],
    }
    if evidence_ledger_projection:
        custody_gaps = list(evidence_ledger_projection.get("custody_gaps") or ())
        final_gap_types = [
            gap.get("gap_type")
            for gap in custody_gaps
            if isinstance(gap, Mapping)
            and gap.get("gap_type")
            == "final_evidence_selected_without_ledger_custody"
        ]
        summary.update(
            {
                "evidence_ledger_candidate_count": evidence_ledger_projection.get(
                    "candidate_count", 0
                ),
                "evidence_ledger_requirement_count": evidence_ledger_projection.get(
                    "requirement_count", 0
                ),
                "custody_gap_types": [
                    gap.get("gap_type")
                    for gap in custody_gaps
                    if isinstance(gap, Mapping) and gap.get("gap_type")
                ],
                "final_evidence_compatibility_gap_count": len(final_gap_types),
            }
        )
    return summary


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
    if any(
        o.status
        in {
            SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED,
            SourceObligationStatus.MISSING_REQUIRED_SOURCE,
            SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING,
        }
        for o in source_obligations
    ):
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
        elif obligation.status is SourceObligationStatus.MISSING_REQUIRED_SOURCE:
            caveats.append(f"missing_required_source:{obligation.source_class}")
        elif obligation.status is SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING:
            caveats.append(f"source_bound_value_missing:{obligation.source_class}")
    return tuple(dict.fromkeys(caveats))


def _contract_final_posture_items(
    projection: Any,
    key: str,
) -> tuple[str, ...]:
    if not isinstance(projection, Mapping):
        return ()
    policy = projection.get("final_posture_policy")
    if not isinstance(policy, Mapping):
        return ()
    value = policy.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item or "").strip())
    return ()


def _is_missing_source_caveat(caveat: str) -> bool:
    lowered = caveat.casefold()
    return any(marker in lowered for marker in ("missing", "absent", "unavailable", "unknown"))


def _unresolved_contract_requirement_markers(
    projection: Any,
    source_obligations: Sequence[SourceObligationRecord],
) -> frozenset[str]:
    if not isinstance(projection, Mapping):
        return frozenset()
    markers: set[str] = set()
    for requirement in projection.get("source_requirements") or ():
        if not isinstance(requirement, Mapping):
            continue
        if str(requirement.get("strictness") or "") != "required":
            continue
        matches = _matching_source_obligation_records(requirement, source_obligations)
        if not matches:
            continue
        if any(
            obligation.status is not SourceObligationStatus.SATISFIED
            for obligation in matches
        ):
            markers.update(
                marker
                for marker in (
                    _contract_requirement_key(requirement.get("requirement_id")),
                    _contract_requirement_key(requirement.get("requirement_kind")),
                    _contract_requirement_key(requirement.get("required_source_class")),
                )
                if marker
            )
    return frozenset(markers)


def _missing_source_caveat_applies(
    caveat: str,
    *,
    unresolved_markers: frozenset[str],
) -> bool:
    if not _is_missing_source_caveat(caveat):
        return True
    if not unresolved_markers:
        return False
    lowered = caveat.casefold()
    marker_groups = (
        (
            ("official_current", "official"),
            ("official_current", "official_current_rules", "current_primary_or_official"),
        ),
        (("source_bound", "numeric"), ("source_bound_numeric",)),
        (("legal", "regulatory"), ("legal_primary", "legal_or_regulatory_text")),
        (("canonical", "docs"), ("canonical_docs", "primary_source_documents")),
        (("user_document", "document"), ("user_document",)),
        (("academic", "literature"), ("academic", "academic_primary_literature")),
    )
    for caveat_terms, related_markers in marker_groups:
        if any(term in lowered for term in caveat_terms):
            return bool(unresolved_markers.intersection(related_markers))
    return True


def _contract_mandatory_caveats(
    projection: Any,
    *,
    source_obligations: Sequence[SourceObligationRecord],
) -> tuple[str, ...]:
    caveats = _contract_final_posture_items(projection, "mandatory_caveats")
    if not caveats:
        return ()
    unresolved_markers = _unresolved_contract_requirement_markers(
        projection,
        source_obligations,
    )
    return tuple(
        caveat
        for caveat in caveats
        if _missing_source_caveat_applies(
            caveat,
            unresolved_markers=unresolved_markers,
        )
    )


def _readiness(
    *,
    evidence_records: Sequence[FinalEvidenceRecord],
    source_obligations: Sequence[SourceObligationRecord],
    evidence_sufficient: bool | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    synth_was_insufficient: bool | None,
) -> tuple[FinalAnswerReadinessStatus, tuple[str, ...]]:
    reasons: list[str] = []
    if not evidence_records:
        reasons.append("no_final_evidence_available")
    if evidence_sufficient is False:
        reasons.append("evidence_sufficient_false")
    if corpus_weak:
        reasons.append("weak_corpus_authorized")
    if synth_was_insufficient:
        reasons.append("synthesis_insufficient_authorized")
    if failure_card_payload and failure_card_payload.get("show"):
        reasons.append("failure_card_authorized")
    if any(
        obligation.status is not SourceObligationStatus.SATISFIED
        for obligation in source_obligations
    ):
        reasons.append("source_obligations_missing_or_unsatisfied")
    if reasons:
        return FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED, tuple(
            dict.fromkeys(reasons)
        )
    return FinalAnswerReadinessStatus.AUTHOR_READY, ()


def build_final_answer_packet(
    *,
    run_id: str,
    final_evidence: Sequence[Mapping[str, Any]] | None,
    author_evidence: Sequence[Mapping[str, Any]] | None = None,
    ordered_sources: Sequence[Any] | None = None,
    unique_source_urls: Mapping[str, Any] | None = None,
    final_answer_source_telemetry: Mapping[str, Any] | None = None,
    source_obligation_projection: Any | None = None,
    answer_contract_projection: Any | None = None,
    run_contract_projection: Any | None = None,
    sufficiency_judgment_projection: Any | None = None,
    query_lineage_refs: Mapping[str, Any] | None = None,
    evidence_sufficient: bool | None = None,
    corpus_weak: bool | None = None,
    failure_card_payload: Mapping[str, Any] | None = None,
    conflicts_present: bool | None = None,
    synth_was_insufficient: bool | None = None,
    author_notes: str | None = None,
) -> FinalAnswerPacket:
    packet_id = f"final-answer-packet-{run_id}"
    sufficiency_projection = _sufficiency_projection_from_any(
        sufficiency_judgment_projection
    )
    sufficiency_missing_required = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "missing_required_obligations",
    )
    sufficiency_partial = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "partial_obligations",
    )
    sufficiency_satisfied = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "satisfied_obligations",
    )
    sufficiency_constrained_citations = bool(
        sufficiency_projection and (sufficiency_missing_required or sufficiency_partial)
    )
    satisfied_source_classes = frozenset(
        _contract_requirement_key(
            item.get("required_source_class")
            or item.get("source_class")
            or item.get("requirement_kind")
        )
        for item in sufficiency_satisfied
        if isinstance(item, Mapping)
    )
    evidence_records = tuple(
        _evidence_record_from_passage(passage, position=index, packet_id=packet_id)
        for index, passage in enumerate(final_evidence or (), start=1)
    )
    citation_records = tuple(
        _citation_record_for_evidence(
            record,
            sufficiency_constrained=sufficiency_constrained_citations,
            satisfied_source_classes=satisfied_source_classes,
        )
        for record in evidence_records
    )
    custody_source_obligations = _source_obligations_from_custody(
        source_obligation_projection
    )
    answer_contract_source_obligations = _source_obligations_from_answer_contract(
        answer_contract_projection
    )
    contract_source_obligations = (
        ()
        if sufficiency_projection
        else _source_obligations_from_run_contract(
            run_contract_projection,
            existing_obligations=(
                custody_source_obligations + answer_contract_source_obligations
            ),
        )
    )
    sufficiency_source_obligations = _source_obligations_from_sufficiency(
        sufficiency_judgment_projection
    )
    source_obligations = _dedupe_source_obligations(
        custody_source_obligations
        + answer_contract_source_obligations
        + contract_source_obligations
        + sufficiency_source_obligations
    )
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
    sufficiency_ref = _sufficiency_author_ref(sufficiency_judgment_projection)
    if sufficiency_ref:
        author_refs["sufficiency_judgment_ref"] = sufficiency_ref
        author_refs["final_answer_posture"] = sufficiency_ref.get(
            "final_answer_posture"
        )
        author_refs["sufficiency_decision"] = sufficiency_ref.get("decision")
    prohibited = [
        "do_not_upgrade_citation_ineligible_evidence",
        "do_not_treat_missing_official_current_custody_as_satisfied",
    ]
    if source_obligations:
        prohibited.append("do_not_infer_source_obligation_satisfaction_from_citation_presence")
    prohibited.extend(
        _contract_final_posture_items(
            run_contract_projection,
            "prohibited_upgrades",
        )
    )
    custody_summary = _custody_summary(source_obligation_projection)
    if custody_summary.get("final_evidence_compatibility_gap_count"):
        prohibited.append("do_not_treat_uncustodied_final_evidence_as_ledger_proof")
    if not evidence_records:
        prohibited.append("do_not_present_unsourced_claims_as_supported")
    readiness_status, readiness_reasons = _readiness(
        evidence_records=evidence_records,
        source_obligations=source_obligations,
        evidence_sufficient=evidence_sufficient,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        synth_was_insufficient=synth_was_insufficient,
    )
    sufficiency_readiness = _sufficiency_readiness(sufficiency_judgment_projection)
    if sufficiency_readiness is not None:
        readiness_status, readiness_reasons = sufficiency_readiness
    sufficiency_postures = _claim_postures_from_sufficiency(
        sufficiency_judgment_projection
    )
    legacy_postures = (
        ()
        if sufficiency_postures
        else _postures(
            evidence_sufficient=evidence_sufficient,
            corpus_weak=corpus_weak,
            failure_card_payload=failure_card_payload,
            conflicts_present=conflicts_present,
            synth_was_insufficient=synth_was_insufficient,
            source_obligations=source_obligations,
        )
    )
    claim_postures = tuple(dict.fromkeys(sufficiency_postures + legacy_postures))
    sufficiency_mandatory = _sufficiency_packet_items(
        sufficiency_judgment_projection,
        "mandatory_caveats",
    )
    sufficiency_prohibited = _sufficiency_packet_items(
        sufficiency_judgment_projection,
        "prohibited_upgrades",
    )
    prohibited.extend(sufficiency_prohibited)
    final_answer_allowed = _sufficiency_packet_bool(
        sufficiency_judgment_projection,
        "final_answer_allowed",
    )
    if final_answer_allowed is None:
        final_answer_allowed = True
    sufficiency_decision = _sufficiency_packet_text(
        sufficiency_judgment_projection,
        "decision",
    )
    final_answer_posture = _sufficiency_packet_text(
        sufficiency_judgment_projection,
        "final_answer_posture",
    )
    required_satisfied = _sufficiency_packet_bool(
        sufficiency_judgment_projection,
        "required_obligations_satisfied",
    )
    missing_required = sufficiency_missing_required
    partial_obligations = sufficiency_partial
    satisfied_obligations = sufficiency_satisfied
    source_bound_unknowns = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "source_bound_numeric_unknowns",
    )
    source_bound_resolutions = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "source_bound_numeric_resolutions",
    )
    behavior_boundary_flags = _sufficiency_packet_mapping(
        sufficiency_judgment_projection,
        "behavior_boundary_flags",
    )
    if final_answer_allowed is False:
        readiness_status = FinalAnswerReadinessStatus.BLOCKED
        readiness_reasons = tuple(
            dict.fromkeys((*readiness_reasons, "final_answer_not_allowed"))
        )
    semantic_authority_ref = _compact_semantic_authority_ref(
        sufficiency_judgment_projection
    )
    return FinalAnswerPacket(
        packet_id=packet_id,
        evidence_records=evidence_records,
        citation_records=citation_records,
        source_obligations=source_obligations,
        official_current_custody_summary=custody_summary,
        sufficiency_decision=sufficiency_decision,
        final_answer_posture=final_answer_posture,
        final_answer_allowed=bool(final_answer_allowed),
        required_obligations_satisfied=required_satisfied,
        missing_required_obligations=missing_required,
        partial_obligations=partial_obligations,
        satisfied_obligations=satisfied_obligations,
        source_bound_numeric_unknowns=source_bound_unknowns,
        source_bound_numeric_resolutions=source_bound_resolutions,
        behavior_boundary_flags=behavior_boundary_flags,
        claim_postures=claim_postures,
        mandatory_caveats=tuple(
            dict.fromkeys(
                _mandatory_caveats(
                    author_notes=author_notes,
                    corpus_weak=corpus_weak,
                    failure_card_payload=failure_card_payload,
                    source_obligations=source_obligations,
                    synth_was_insufficient=synth_was_insufficient,
                )
                + _contract_mandatory_caveats(
                    run_contract_projection,
                    source_obligations=source_obligations,
                )
                + sufficiency_mandatory
            )
        ),
        prohibited_upgrades=tuple(dict.fromkeys(prohibited)),
        author_input_refs=author_refs,
        query_lineage_refs=dict(query_lineage_refs or {}),
        readiness_status=readiness_status,
        readiness_reasons=readiness_reasons,
        semantic_authority_ref=semantic_authority_ref,
    )


def derive_author_input_payload(
    packet: FinalAnswerPacket,
    *,
    prompt: str,
    author_system_prompt_key: str,
    author_effort: str,
    author_provider: str | None = None,
    author_model: str | None = None,
) -> tuple[FinalAnswerPacket, FinalAnswerAuthorInputPayload]:
    refs = packet.author_input_refs if isinstance(packet.author_input_refs, Mapping) else {}
    payload = packet.to_author_input_payload(
        prompt=prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_provider=author_provider,
        author_model=author_model,
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
    run_kernel_final_answer_ref: Mapping[str, Any] | None = None,
):
    """Demote legacy citation/source handoff inputs behind FinalAnswerPacket."""

    projection = packet.to_legacy_citation_handoff_inputs()
    compatibility_refs = final_answer_packet_compatibility_refs(packet)
    resolved_ledger_ref = ledger_ref or compatibility_refs["ledger_ref"]
    if run_kernel_final_answer_ref:
        resolved_ledger_ref = {
            **dict(resolved_ledger_ref),
            "run_kernel_final_answer_ref": dict(run_kernel_final_answer_ref),
        }
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
        ledger_ref=resolved_ledger_ref,
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
