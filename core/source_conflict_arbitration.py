"""Pure Controller-owned arbitration posture for AG-77A source conflicts.

This module consumes passive ``SourceConflictRepresentation`` objects and emits
ledger-compatible Controller state. It does not mutate the representation and it
must not retrieve, rank, resolve through search, cite, prompt, persist, call
providers, or alter runtime/final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from core.source_conflict_model import (
    SOURCE_CONFLICT_SCHEMA_VERSION,
    SourceConflictCentrality,
    SourceConflictContradictionShape,
    SourceConflictCurrentness,
    SourceConflictGroup,
    SourceConflictObligationImpact,
    SourceConflictRecord,
    SourceConflictRepresentation,
)

SOURCE_CONFLICT_ARBITRATION_SCHEMA_VERSION = (
    "AG77B.controller_owned_conflict_arbitration.v1"
)
SOURCE_CONFLICT_ARBITRATION_TRACE_KEY = "source_conflict_arbitration"


class SourceConflictArbitrationDisposition(str, Enum):
    """Deterministic Controller posture for an already-represented conflict."""

    NO_CONFLICT = "no_conflict"
    IGNORE_NON_MATERIAL_CONFLICT = "ignore_non_material_conflict"
    PREFER_CLAIM_A = "prefer_claim_a"
    PREFER_CLAIM_B = "prefer_claim_b"
    REPORT_BOTH = "report_both"
    REPORT_BOTH_BY_SCOPE = "report_both_by_scope"
    UNRESOLVED_BLOCKING = "unresolved_blocking"
    UNRESOLVED_NONBLOCKING = "unresolved_nonblocking"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    BACKGROUND_ONLY = "background_only"


class SourceConflictAnswerPosture(str, Enum):
    """Passive recommendation for later Controller/AnswerContract integration."""

    NO_ANSWER_IMPACT = "no_answer_impact"
    QUALIFIED_ANSWER = "qualified_answer"
    PARTIAL_ANSWER = "partial_answer"
    INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER = (
        "insufficient_for_authoritative_answer"
    )
    SOURCE_BOUND_VALUE_UNRESOLVED = "source_bound_value_unresolved"


class SourceConflictArbitrationReason(str, Enum):
    """Primary reason for the selected arbitration posture."""

    EQUAL_AUTHORITY_CONFLICT = "equal_authority_conflict"
    STRONGER_SOURCE_CLASS_PREFERRED = "stronger_source_class_preferred"
    CURRENT_SOURCE_PREFERRED_OVER_STALE = "current_source_preferred_over_stale"
    SCOPE_OR_JURISDICTION_SPECIFIC = "scope_or_jurisdiction_specific"
    SOURCE_BOUND_NUMERIC_UNRESOLVED = "source_bound_numeric_unresolved"
    PERIPHERAL_OR_BACKGROUND_ONLY = "peripheral_or_background_only"
    INSUFFICIENT_EVIDENCE_TO_ARBITRATE = "insufficient_evidence_to_arbitrate"
    LOWER_TIER_NOT_SATISFYING_STRONGER_OBLIGATION = (
        "lower_tier_not_satisfying_stronger_obligation"
    )
    NO_MATERIAL_CONFLICT = "no_material_conflict"


_AUTHORITY_CLASS_RANK = {
    "official": 100,
    "current_primary_or_official": 100,
    "legal_or_regulatory_text": 100,
    "official_current_rules": 100,
    "canonical": 95,
    "primary": 90,
    "primary_source_documents": 90,
    "archival_primary_text": 80,
    "academic": 70,
    "secondary": 40,
    "tertiary": 20,
    "weak": 10,
}
_AUTHORITY_TIER_RANK = {
    "official": 100,
    "primary": 90,
    "canonical": 90,
    "secondary": 40,
    "tertiary": 20,
    "weak": 10,
}
_STALE_LABELS = {
    SourceConflictCurrentness.STALE.value,
    SourceConflictCurrentness.HISTORICAL.value,
    SourceConflictCurrentness.SUPERSEDED.value,
}
_BLOCKING_IMPACTS = {
    SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT.value,
    SourceConflictObligationImpact.AFFECTS_LEGAL_CURRENT_PRIMARY.value,
    SourceConflictObligationImpact.AFFECTS_CANONICAL.value,
    SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE.value,
    SourceConflictObligationImpact.AFFECTS_FINAL_ANSWER_POSTURE.value,
}


@dataclass(frozen=True)
class SourceConflictArbitrationInput:
    """Pure input wrapper for Controller-owned conflict arbitration."""

    representation: SourceConflictRepresentation
    mode: str | None = None
    answer_contract_ref: Mapping[str, Any] | None = None
    controller_context_ref: Mapping[str, Any] | None = None
    schema_version: str = SOURCE_CONFLICT_ARBITRATION_SCHEMA_VERSION
    controller_owned: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.representation, SourceConflictRepresentation):
            raise TypeError("representation must be SourceConflictRepresentation")
        object.__setattr__(
            self,
            "answer_contract_ref",
            _copy_json_mapping(self.answer_contract_ref),
        )
        object.__setattr__(
            self,
            "controller_context_ref",
            _copy_json_mapping(self.controller_context_ref),
        )
        object.__setattr__(self, "controller_owned", True)


@dataclass(frozen=True)
class SourceConflictRecordArbitration:
    """Record-level arbitration posture that preserves both AG-77A claims."""

    conflict_id: str
    group_id: str
    disposition: SourceConflictArbitrationDisposition
    answer_posture: SourceConflictAnswerPosture
    reason: SourceConflictArbitrationReason
    claim_a_preserved: bool
    claim_b_preserved: bool
    preferred_claim_id: str | None
    non_satisfying_claim_ids: tuple[str, ...]
    background_only_claim_ids: tuple[str, ...]
    reportable_claim_ids: tuple[str, ...]
    unresolved: bool
    blocks_authoritative_posture: bool
    needs_more_evidence: bool
    obligation_impact: str
    centrality: str
    contradiction_shape: tuple[str, ...]
    source_ids_preserved: tuple[str, ...]
    claim_ids_preserved: tuple[str, ...]
    claim_a: Mapping[str, Any]
    claim_b: Mapping[str, Any]
    winner_chosen: bool
    lower_tier_cannot_satisfy_stronger_obligation: bool
    controller_visible: bool = True
    ledger_compatible: bool = True

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "group_id": self.group_id,
            "disposition": self.disposition.value,
            "answer_posture": self.answer_posture.value,
            "reason": self.reason.value,
            "claim_a_preserved": self.claim_a_preserved,
            "claim_b_preserved": self.claim_b_preserved,
            "preferred_claim_id": self.preferred_claim_id,
            "non_satisfying_claim_ids": list(self.non_satisfying_claim_ids),
            "background_only_claim_ids": list(self.background_only_claim_ids),
            "reportable_claim_ids": list(self.reportable_claim_ids),
            "unresolved": self.unresolved,
            "blocks_authoritative_posture": self.blocks_authoritative_posture,
            "needs_more_evidence": self.needs_more_evidence,
            "obligation_impact": self.obligation_impact,
            "centrality": self.centrality,
            "contradiction_shape": list(self.contradiction_shape),
            "source_ids_preserved": list(self.source_ids_preserved),
            "claim_ids_preserved": list(self.claim_ids_preserved),
            "claim_a": dict(self.claim_a),
            "claim_b": dict(self.claim_b),
            "winner_chosen": self.winner_chosen,
            "lower_tier_cannot_satisfy_stronger_obligation": (
                self.lower_tier_cannot_satisfy_stronger_obligation
            ),
            "controller_visible": self.controller_visible,
            "ledger_compatible": self.ledger_compatible,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return self.to_controller_state()


@dataclass(frozen=True)
class SourceConflictGroupArbitration:
    """Group-level aggregation of record arbitration posture."""

    group_id: str
    record_arbitrations: tuple[SourceConflictRecordArbitration, ...]
    group_disposition: SourceConflictArbitrationDisposition
    answer_posture: SourceConflictAnswerPosture
    unresolved_count: int
    blocking_count: int
    report_both_count: int
    needs_more_evidence: bool
    involved_source_ids: tuple[str, ...]
    involved_claim_ids: tuple[str, ...]
    controller_visible: bool = True
    ledger_compatible: bool = True

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "record_arbitrations": [
                record.to_controller_state() for record in self.record_arbitrations
            ],
            "group_disposition": self.group_disposition.value,
            "answer_posture": self.answer_posture.value,
            "unresolved_count": self.unresolved_count,
            "blocking_count": self.blocking_count,
            "report_both_count": self.report_both_count,
            "needs_more_evidence": self.needs_more_evidence,
            "involved_source_ids": list(self.involved_source_ids),
            "involved_claim_ids": list(self.involved_claim_ids),
            "controller_visible": self.controller_visible,
            "ledger_compatible": self.ledger_compatible,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return self.to_controller_state()


@dataclass(frozen=True)
class SourceConflictArbitrationState:
    """Top-level passive arbitration state for Controller trace/ledger storage."""

    input_representation_schema_version: str
    arbitration_schema_version: str
    group_arbitrations: tuple[SourceConflictGroupArbitration, ...]
    top_level_answer_posture: SourceConflictAnswerPosture
    unresolved_blocking_count: int
    unresolved_nonblocking_count: int
    preferred_record_count: int
    report_both_count: int
    background_only_count: int
    needs_more_evidence_count: int
    controller_visible: bool = True
    ledger_compatible: bool = True
    final_answer_behavior_changed: bool = False
    citation_behavior_changed: bool = False
    prompt_behavior_changed: bool = False
    provider_search_query_behavior_changed: bool = False
    runtime_behavior_changed: bool = False

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "schema_version": self.arbitration_schema_version,
            "input_representation_schema_version": (
                self.input_representation_schema_version
            ),
            "groups": [
                group.to_controller_state() for group in self.group_arbitrations
            ],
            "group_count": len(self.group_arbitrations),
            "top_level_answer_posture": self.top_level_answer_posture.value,
            "unresolved_blocking_count": self.unresolved_blocking_count,
            "unresolved_nonblocking_count": self.unresolved_nonblocking_count,
            "preferred_record_count": self.preferred_record_count,
            "report_both_count": self.report_both_count,
            "background_only_count": self.background_only_count,
            "needs_more_evidence_count": self.needs_more_evidence_count,
            "controller_visible": self.controller_visible,
            "ledger_compatible": self.ledger_compatible,
            "final_answer_behavior_changed": False,
            "citation_behavior_changed": False,
            "prompt_behavior_changed": False,
            "provider_search_query_behavior_changed": False,
            "runtime_behavior_changed": False,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SOURCE_CONFLICT_ARBITRATION_TRACE_KEY: self.to_controller_state()}


def arbitrate_source_conflicts(
    arbitration_input: SourceConflictArbitrationInput | SourceConflictRepresentation,
) -> SourceConflictArbitrationState:
    """Arbitrate passive Controller posture without mutating AG-77A input."""

    if isinstance(arbitration_input, SourceConflictRepresentation):
        wrapped = SourceConflictArbitrationInput(representation=arbitration_input)
    elif isinstance(arbitration_input, SourceConflictArbitrationInput):
        wrapped = arbitration_input
    else:
        raise TypeError(
            "arbitration_input must be SourceConflictArbitrationInput or "
            "SourceConflictRepresentation"
        )

    groups = tuple(_arbitrate_group(group) for group in wrapped.representation.groups)
    record_arbitrations = tuple(
        record for group in groups for record in group.record_arbitrations
    )
    blocking = sum(
        1
        for record in record_arbitrations
        if record.unresolved and record.blocks_authoritative_posture
    )
    nonblocking = sum(
        1
        for record in record_arbitrations
        if record.unresolved and not record.blocks_authoritative_posture
    )
    preferred = sum(1 for record in record_arbitrations if record.preferred_claim_id)
    report_both = sum(
        1
        for record in record_arbitrations
        if record.disposition
        in {
            SourceConflictArbitrationDisposition.REPORT_BOTH,
            SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE,
        }
    )
    background = sum(
        1
        for record in record_arbitrations
        if record.disposition
        in {
            SourceConflictArbitrationDisposition.BACKGROUND_ONLY,
            SourceConflictArbitrationDisposition.IGNORE_NON_MATERIAL_CONFLICT,
        }
    )
    needs_evidence = sum(
        1 for record in record_arbitrations if record.needs_more_evidence
    )

    return SourceConflictArbitrationState(
        input_representation_schema_version=(
            wrapped.representation.schema_version or SOURCE_CONFLICT_SCHEMA_VERSION
        ),
        arbitration_schema_version=wrapped.schema_version,
        group_arbitrations=groups,
        top_level_answer_posture=_aggregate_answer_posture(
            tuple(group.answer_posture for group in groups),
        ),
        unresolved_blocking_count=blocking,
        unresolved_nonblocking_count=nonblocking,
        preferred_record_count=preferred,
        report_both_count=report_both,
        background_only_count=background,
        needs_more_evidence_count=needs_evidence,
    )


def _arbitrate_group(group: SourceConflictGroup) -> SourceConflictGroupArbitration:
    records = tuple(_arbitrate_record(group.group_id, record) for record in group.records)
    unresolved_count = sum(1 for record in records if record.unresolved)
    blocking_count = sum(1 for record in records if record.blocks_authoritative_posture)
    report_both_count = sum(
        1
        for record in records
        if record.disposition
        in {
            SourceConflictArbitrationDisposition.REPORT_BOTH,
            SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE,
        }
    )
    return SourceConflictGroupArbitration(
        group_id=group.group_id,
        record_arbitrations=records,
        group_disposition=_aggregate_disposition(
            tuple(record.disposition for record in records),
        ),
        answer_posture=_aggregate_answer_posture(
            tuple(record.answer_posture for record in records),
        ),
        unresolved_count=unresolved_count,
        blocking_count=blocking_count,
        report_both_count=report_both_count,
        needs_more_evidence=any(record.needs_more_evidence for record in records),
        involved_source_ids=_dedupe(source for record in records for source in record.source_ids_preserved),
        involved_claim_ids=_dedupe(claim for record in records for claim in record.claim_ids_preserved),
        controller_visible=bool(group.controller_visible),
        ledger_compatible=bool(group.ledger_compatible),
    )


def _arbitrate_record(
    group_id: str,
    record: SourceConflictRecord,
) -> SourceConflictRecordArbitration:
    shapes = tuple(str(shape) for shape in record.contradiction_shape)
    claim_a = record.claim_a.to_dict()
    claim_b = record.claim_b.to_dict()
    claim_ids = record.claim_ids
    source_ids = record.source_ids
    obligation_impact = str(record.obligation_impact.impact)
    centrality = str(record.centrality)
    material = _is_material(centrality, obligation_impact)

    disposition = SourceConflictArbitrationDisposition.NEEDS_MORE_EVIDENCE
    answer_posture = SourceConflictAnswerPosture.PARTIAL_ANSWER
    reason = SourceConflictArbitrationReason.INSUFFICIENT_EVIDENCE_TO_ARBITRATE
    preferred_claim_id: str | None = None
    non_satisfying_claim_ids: tuple[str, ...] = ()
    background_only_claim_ids: tuple[str, ...] = ()
    reportable_claim_ids: tuple[str, ...] = claim_ids
    unresolved = True
    blocks = material
    needs_more_evidence = True
    lower_tier_block = bool(record.lower_tier_cannot_satisfy_stronger_obligation)

    scope_mismatch = SourceConflictContradictionShape.JURISDICTION_SCOPE_MISMATCH.value in shapes
    numeric = SourceConflictContradictionShape.SOURCE_BOUND_NUMERIC_CONFLICT.value in shapes
    stale_current = SourceConflictContradictionShape.STALE_VS_CURRENT.value in shapes
    authority_mismatch = (
        SourceConflictContradictionShape.SOURCE_CLASS_AUTHORITY_MISMATCH.value in shapes
        or _authority_rank(record.claim_a) != _authority_rank(record.claim_b)
    )

    if not shapes or record.unresolved_state == "out_of_scope":
        disposition = SourceConflictArbitrationDisposition.NO_CONFLICT
        answer_posture = SourceConflictAnswerPosture.NO_ANSWER_IMPACT
        reason = SourceConflictArbitrationReason.NO_MATERIAL_CONFLICT
        reportable_claim_ids = ()
        unresolved = False
        blocks = False
        needs_more_evidence = False
    elif not material:
        disposition = SourceConflictArbitrationDisposition.BACKGROUND_ONLY
        answer_posture = SourceConflictAnswerPosture.NO_ANSWER_IMPACT
        reason = SourceConflictArbitrationReason.PERIPHERAL_OR_BACKGROUND_ONLY
        background_only_claim_ids = claim_ids
        reportable_claim_ids = ()
        unresolved = True
        blocks = False
        needs_more_evidence = False
    elif scope_mismatch:
        disposition = SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE
        answer_posture = SourceConflictAnswerPosture.QUALIFIED_ANSWER
        reason = SourceConflictArbitrationReason.SCOPE_OR_JURISDICTION_SPECIFIC
        unresolved = False
        blocks = False
        needs_more_evidence = False
    elif numeric and _same_scope_and_period(record):
        disposition = SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING
        answer_posture = SourceConflictAnswerPosture.SOURCE_BOUND_VALUE_UNRESOLVED
        reason = SourceConflictArbitrationReason.SOURCE_BOUND_NUMERIC_UNRESOLVED
        unresolved = True
        blocks = True
        needs_more_evidence = False
    elif stale_current and _currentness_preference(record) is not None:
        preferred_claim_id = _currentness_preference(record)
        disposition = _preference_disposition(preferred_claim_id, claim_ids)
        answer_posture = SourceConflictAnswerPosture.QUALIFIED_ANSWER
        reason = SourceConflictArbitrationReason.CURRENT_SOURCE_PREFERRED_OVER_STALE
        background_only_claim_ids = tuple(
            claim_id for claim_id in claim_ids if claim_id != preferred_claim_id
        )
        unresolved = False
        blocks = False
        needs_more_evidence = False
    elif authority_mismatch and _authority_preference(record) is not None:
        preferred_claim_id = _authority_preference(record)
        disposition = _preference_disposition(preferred_claim_id, claim_ids)
        reason = SourceConflictArbitrationReason.STRONGER_SOURCE_CLASS_PREFERRED
        if lower_tier_block:
            reason = (
                SourceConflictArbitrationReason.LOWER_TIER_NOT_SATISFYING_STRONGER_OBLIGATION
            )
        answer_posture = SourceConflictAnswerPosture.QUALIFIED_ANSWER
        non_satisfying_claim_ids = tuple(
            claim_id for claim_id in claim_ids if claim_id != preferred_claim_id
        )
        background_only_claim_ids = non_satisfying_claim_ids
        unresolved = False
        blocks = False
        needs_more_evidence = False
        lower_tier_block = True
    elif _equal_current_authority(record):
        disposition = SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING
        answer_posture = (
            SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER
        )
        reason = SourceConflictArbitrationReason.EQUAL_AUTHORITY_CONFLICT
        unresolved = True
        blocks = material
        needs_more_evidence = False
    else:
        disposition = SourceConflictArbitrationDisposition.UNRESOLVED_NONBLOCKING
        answer_posture = SourceConflictAnswerPosture.PARTIAL_ANSWER
        reason = SourceConflictArbitrationReason.INSUFFICIENT_EVIDENCE_TO_ARBITRATE
        blocks = False
        needs_more_evidence = True

    return SourceConflictRecordArbitration(
        conflict_id=record.conflict_id,
        group_id=group_id,
        disposition=disposition,
        answer_posture=answer_posture,
        reason=reason,
        claim_a_preserved=True,
        claim_b_preserved=True,
        preferred_claim_id=preferred_claim_id,
        non_satisfying_claim_ids=non_satisfying_claim_ids,
        background_only_claim_ids=background_only_claim_ids,
        reportable_claim_ids=reportable_claim_ids,
        unresolved=unresolved,
        blocks_authoritative_posture=blocks,
        needs_more_evidence=needs_more_evidence,
        obligation_impact=obligation_impact,
        centrality=centrality,
        contradiction_shape=shapes,
        source_ids_preserved=source_ids,
        claim_ids_preserved=claim_ids,
        claim_a=claim_a,
        claim_b=claim_b,
        winner_chosen=preferred_claim_id is not None,
        lower_tier_cannot_satisfy_stronger_obligation=lower_tier_block,
        controller_visible=bool(record.controller_visible),
        ledger_compatible=bool(record.ledger_compatible),
    )


def _aggregate_disposition(
    dispositions: tuple[SourceConflictArbitrationDisposition, ...],
) -> SourceConflictArbitrationDisposition:
    if not dispositions:
        return SourceConflictArbitrationDisposition.NO_CONFLICT
    priority = (
        SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING,
        SourceConflictArbitrationDisposition.NEEDS_MORE_EVIDENCE,
        SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE,
        SourceConflictArbitrationDisposition.REPORT_BOTH,
        SourceConflictArbitrationDisposition.PREFER_CLAIM_A,
        SourceConflictArbitrationDisposition.PREFER_CLAIM_B,
        SourceConflictArbitrationDisposition.UNRESOLVED_NONBLOCKING,
        SourceConflictArbitrationDisposition.BACKGROUND_ONLY,
        SourceConflictArbitrationDisposition.IGNORE_NON_MATERIAL_CONFLICT,
        SourceConflictArbitrationDisposition.NO_CONFLICT,
    )
    return next(item for item in priority if item in dispositions)


def _aggregate_answer_posture(
    postures: tuple[SourceConflictAnswerPosture, ...],
) -> SourceConflictAnswerPosture:
    if not postures:
        return SourceConflictAnswerPosture.NO_ANSWER_IMPACT
    priority = (
        SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER,
        SourceConflictAnswerPosture.SOURCE_BOUND_VALUE_UNRESOLVED,
        SourceConflictAnswerPosture.PARTIAL_ANSWER,
        SourceConflictAnswerPosture.QUALIFIED_ANSWER,
        SourceConflictAnswerPosture.NO_ANSWER_IMPACT,
    )
    return next(item for item in priority if item in postures)


def _is_material(centrality: str, obligation_impact: str) -> bool:
    if centrality == SourceConflictCentrality.PERIPHERAL.value:
        return False
    return (
        centrality == SourceConflictCentrality.CENTRAL.value
        or obligation_impact in _BLOCKING_IMPACTS
    )


def _same_scope_and_period(record: SourceConflictRecord) -> bool:
    return (
        (record.claim_a.jurisdiction or record.claim_a.source_ref.jurisdiction)
        == (record.claim_b.jurisdiction or record.claim_b.source_ref.jurisdiction)
        and (record.claim_a.scope or record.claim_a.source_ref.scope)
        == (record.claim_b.scope or record.claim_b.source_ref.scope)
        and record.claim_a.effective_period_start == record.claim_b.effective_period_start
        and record.claim_a.effective_period_end == record.claim_b.effective_period_end
    )


def _equal_current_authority(record: SourceConflictRecord) -> bool:
    return (
        _authority_rank(record.claim_a) == _authority_rank(record.claim_b)
        and _is_current(record.claim_a.currentness_label)
        and _is_current(record.claim_b.currentness_label)
    )


def _currentness_preference(record: SourceConflictRecord) -> str | None:
    a_current = _is_current(record.claim_a.currentness_label)
    b_current = _is_current(record.claim_b.currentness_label)
    a_stale = str(record.claim_a.currentness_label) in _STALE_LABELS
    b_stale = str(record.claim_b.currentness_label) in _STALE_LABELS
    if a_current and b_stale and _compatible_authority_scope(record):
        return record.claim_a.claim_id
    if b_current and a_stale and _compatible_authority_scope(record):
        return record.claim_b.claim_id
    return None


def _authority_preference(record: SourceConflictRecord) -> str | None:
    a_rank = _authority_rank(record.claim_a)
    b_rank = _authority_rank(record.claim_b)
    if abs(a_rank - b_rank) < 30:
        return None
    if not _same_scope(record):
        return None
    if a_rank > b_rank:
        return record.claim_a.claim_id
    return record.claim_b.claim_id


def _compatible_authority_scope(record: SourceConflictRecord) -> bool:
    return (
        _authority_rank(record.claim_a) == _authority_rank(record.claim_b)
        and _same_scope(record)
    )


def _same_scope(record: SourceConflictRecord) -> bool:
    return (
        (record.claim_a.jurisdiction or record.claim_a.source_ref.jurisdiction)
        == (record.claim_b.jurisdiction or record.claim_b.source_ref.jurisdiction)
        and (record.claim_a.scope or record.claim_a.source_ref.scope)
        == (record.claim_b.scope or record.claim_b.source_ref.scope)
    )


def _authority_rank(claim: Any) -> int:
    source_class = str(
        claim.source_class or claim.source_ref.source_class or "",
    ).casefold()
    source_tier = str(
        claim.source_tier or claim.source_ref.source_tier or "",
    ).casefold()
    return max(
        _AUTHORITY_CLASS_RANK.get(source_class, 0),
        _AUTHORITY_TIER_RANK.get(source_tier, 0),
    )


def _is_current(value: Any) -> bool:
    return str(value) == SourceConflictCurrentness.CURRENT.value


def _preference_disposition(
    preferred_claim_id: str | None,
    claim_ids: tuple[str, str],
) -> SourceConflictArbitrationDisposition:
    if preferred_claim_id == claim_ids[0]:
        return SourceConflictArbitrationDisposition.PREFER_CLAIM_A
    if preferred_claim_id == claim_ids[1]:
        return SourceConflictArbitrationDisposition.PREFER_CLAIM_B
    return SourceConflictArbitrationDisposition.NEEDS_MORE_EVIDENCE


def _dedupe(values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _copy_json_mapping(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {str(key): _json_safe(item) for key, item in value.items()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
