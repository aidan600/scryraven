"""Passive source-conflict representation contracts for Controller-visible state.

This module defines inert data shapes for preserving source conflicts without
arbitration. It does not retrieve, rank, resolve, cite, prompt, persist, call
providers, run search, or alter final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

SOURCE_CONFLICT_SCHEMA_VERSION = "AG77A.source_conflict_representation.v1"
SOURCE_CONFLICT_TRACE_KEY = "source_conflict_representation"


class SourceConflictCurrentness(str, Enum):
    """Observed source currentness label carried without authority decisions."""

    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"


class SourceConflictContradictionShape(str, Enum):
    """Non-exclusive contradiction shapes preserved for later arbitration."""

    DIRECT_VALUE_CONFLICT = "direct_value_conflict"
    EFFECTIVE_DATE_TENSION = "effective_date_tension"
    STALE_VS_CURRENT = "stale_vs_current"
    JURISDICTION_SCOPE_MISMATCH = "jurisdiction_scope_mismatch"
    SOURCE_CLASS_AUTHORITY_MISMATCH = "source_class_authority_mismatch"
    SOURCE_BOUND_NUMERIC_CONFLICT = "source_bound_numeric_conflict"
    AMBIGUOUS_OR_PARTIAL_CONFLICT = "ambiguous_or_partial_conflict"


class SourceConflictCentrality(str, Enum):
    """How central the unresolved tension appears to the controller contract."""

    CENTRAL = "central"
    SUPPORTING = "supporting"
    PERIPHERAL = "peripheral"
    UNKNOWN = "unknown"


class SourceConflictUnresolvedState(str, Enum):
    """Explicit unresolved posture; none of these values chooses a source."""

    UNRESOLVED = "unresolved"
    NEEDS_ARBITRATION = "needs_arbitration"
    CANNOT_CHOOSE_WINNER = "cannot_choose_winner"
    OUT_OF_SCOPE = "out_of_scope"


class SourceConflictObligationImpact(str, Enum):
    """Contract obligation affected by an unresolved source conflict."""

    NO_OBLIGATION_IMPACT = "no_obligation_impact"
    AFFECTS_OFFICIAL_CURRENT = "affects_official_current"
    AFFECTS_LEGAL_CURRENT_PRIMARY = "affects_legal_current_primary"
    AFFECTS_CANONICAL = "affects_canonical"
    AFFECTS_ACADEMIC = "affects_academic"
    AFFECTS_SOURCE_BOUND_QUANTITATIVE = "affects_source_bound_quantitative"
    AFFECTS_FINAL_ANSWER_POSTURE = "affects_final_answer_posture"


_IMPACT_PRIORITY: dict[SourceConflictObligationImpact, int] = {
    SourceConflictObligationImpact.NO_OBLIGATION_IMPACT: 0,
    SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE: 1,
    SourceConflictObligationImpact.AFFECTS_ACADEMIC: 2,
    SourceConflictObligationImpact.AFFECTS_CANONICAL: 3,
    SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT: 4,
    SourceConflictObligationImpact.AFFECTS_LEGAL_CURRENT_PRIMARY: 5,
    SourceConflictObligationImpact.AFFECTS_FINAL_ANSWER_POSTURE: 6,
}


@dataclass(frozen=True)
class SourceConflictScope:
    """Jurisdiction and scope facts carried with a source or claim."""

    jurisdiction: str | None = None
    scope: str | None = None
    audience: str | None = None
    geography: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "jurisdiction": _clean_optional_text(self.jurisdiction, limit=120),
            "scope": _clean_optional_text(self.scope, limit=160),
            "audience": _clean_optional_text(self.audience, limit=120),
            "geography": _clean_optional_text(self.geography, limit=120),
        }


@dataclass(frozen=True)
class SourceConflictValue:
    """Observed claim value preserved as source-bound evidence."""

    value: str | int | float | bool | None
    unit: str | None = None
    value_kind: str = "text"
    normalized: str | int | float | bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": _json_scalar(self.value),
            "unit": _clean_optional_text(self.unit, limit=60),
            "value_kind": _clean_text(self.value_kind, limit=60, default="text"),
            "normalized": _json_scalar(self.normalized),
        }


@dataclass(frozen=True)
class SourceConflictSourceRef:
    """Identity and provenance for one source participating in a conflict."""

    source_id: str
    url: str | None = None
    title: str | None = None
    domain: str | None = None
    source_class: str | None = None
    source_tier: str | None = None
    publisher: str | None = None
    issuer: str | None = None
    retrieved_at: str | None = None
    observed_at: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    effective_date: str | None = None
    currentness_label: SourceConflictCurrentness | str = SourceConflictCurrentness.UNKNOWN
    jurisdiction: str | None = None
    scope: str | None = None
    evidence_position: int | None = None
    evidence_hash: str | None = None
    text_hash: str | None = None
    authority_weight_hint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _clean_text(self.source_id, limit=100))
        domain = self.domain or _domain_from_url(self.url)
        object.__setattr__(self, "domain", _clean_optional_text(domain, limit=160))
        object.__setattr__(
            self,
            "currentness_label",
            _enum_value(
                self.currentness_label,
                SourceConflictCurrentness,
                SourceConflictCurrentness.UNKNOWN,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": _clean_optional_text(self.url, limit=500),
            "title": _clean_optional_text(self.title, limit=240),
            "domain": self.domain,
            "source_class": _clean_optional_text(self.source_class, limit=80),
            "source_tier": _clean_optional_text(self.source_tier, limit=80),
            "publisher": _clean_optional_text(self.publisher, limit=160),
            "issuer": _clean_optional_text(self.issuer, limit=160),
            "retrieved_at": _clean_optional_text(self.retrieved_at, limit=80),
            "observed_at": _clean_optional_text(self.observed_at, limit=80),
            "published_at": _clean_optional_text(self.published_at, limit=80),
            "updated_at": _clean_optional_text(self.updated_at, limit=80),
            "effective_date": _clean_optional_text(self.effective_date, limit=80),
            "currentness_label": _enum_value(
                self.currentness_label,
                SourceConflictCurrentness,
                SourceConflictCurrentness.UNKNOWN,
            ),
            "jurisdiction": _clean_optional_text(self.jurisdiction, limit=120),
            "scope": _clean_optional_text(self.scope, limit=160),
            "evidence_position": _positive_int_or_none(self.evidence_position),
            "evidence_hash": _clean_optional_text(self.evidence_hash, limit=128),
            "text_hash": _clean_optional_text(self.text_hash, limit=128),
            "authority_weight_hint": _clean_optional_text(
                self.authority_weight_hint,
                limit=120,
            ),
            "authority_weight_hint_is_non_arbitrating": bool(
                self.authority_weight_hint
            ),
        }


@dataclass(frozen=True)
class SourceConflictClaim:
    """One source-bound claim participating in an unresolved conflict."""

    claim_id: str
    normalized_claim_key: str
    source_ref: SourceConflictSourceRef
    claim_text: str | None = None
    claim_summary: str | None = None
    observed_value: SourceConflictValue | str | int | float | bool | None = None
    observed_unit: str | None = None
    date_or_period: str | None = None
    effective_period_start: str | None = None
    effective_period_end: str | None = None
    jurisdiction: str | None = None
    scope: str | None = None
    source_class: str | None = None
    source_tier: str | None = None
    currentness_label: SourceConflictCurrentness | str | None = None
    confidence_label: str | None = None
    posture_label: str | None = None
    source_bound: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _clean_text(self.claim_id, limit=100))
        object.__setattr__(
            self,
            "normalized_claim_key",
            _clean_text(self.normalized_claim_key, limit=180),
        )
        if not isinstance(self.source_ref, SourceConflictSourceRef):
            raise TypeError("source_ref must be SourceConflictSourceRef")
        object.__setattr__(
            self,
            "currentness_label",
            _enum_value(
                self.currentness_label or self.source_ref.currentness_label,
                SourceConflictCurrentness,
                SourceConflictCurrentness.UNKNOWN,
            ),
        )

    def value(self) -> SourceConflictValue:
        if isinstance(self.observed_value, SourceConflictValue):
            return self.observed_value
        return SourceConflictValue(
            value=self.observed_value,
            unit=self.observed_unit,
            value_kind="number" if isinstance(self.observed_value, (int, float)) else "text",
        )

    def to_dict(self) -> dict[str, Any]:
        source = self.source_ref.to_dict()
        return {
            "claim_id": self.claim_id,
            "claim_text": _clean_optional_text(self.claim_text, limit=500),
            "claim_summary": _clean_optional_text(self.claim_summary, limit=240),
            "normalized_claim_key": self.normalized_claim_key,
            "observed_value": self.value().to_dict(),
            "observed_unit": _clean_optional_text(self.observed_unit, limit=60),
            "date_or_period": _clean_optional_text(self.date_or_period, limit=120),
            "effective_period_start": _clean_optional_text(
                self.effective_period_start,
                limit=80,
            ),
            "effective_period_end": _clean_optional_text(
                self.effective_period_end,
                limit=80,
            ),
            "jurisdiction": _clean_optional_text(
                self.jurisdiction or self.source_ref.jurisdiction,
                limit=120,
            ),
            "scope": _clean_optional_text(self.scope or self.source_ref.scope, limit=160),
            "source_ref": source,
            "source_class": _clean_optional_text(
                self.source_class or self.source_ref.source_class,
                limit=80,
            ),
            "source_tier": _clean_optional_text(
                self.source_tier or self.source_ref.source_tier,
                limit=80,
            ),
            "currentness_label": _enum_value(
                self.currentness_label,
                SourceConflictCurrentness,
                SourceConflictCurrentness.UNKNOWN,
            ),
            "confidence_label": _clean_optional_text(self.confidence_label, limit=80),
            "posture_label": _clean_optional_text(self.posture_label, limit=80),
            "source_bound": bool(self.source_bound),
        }


@dataclass(frozen=True)
class SourceConflictObligationImpactDetail:
    """Obligation metadata that cannot be satisfied by flattening weaker evidence."""

    impact: SourceConflictObligationImpact | str
    obligation_key: str | None = None
    required_source_class: str | None = None
    required_source_tier: str | None = None
    lower_tier_cannot_satisfy_stronger_obligation: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "impact",
            _enum_value(
                self.impact,
                SourceConflictObligationImpact,
                SourceConflictObligationImpact.NO_OBLIGATION_IMPACT,
            ),
        )
        object.__setattr__(self, "notes", _copy_string_tuple(self.notes, cap=6, limit=180))

    def to_dict(self) -> dict[str, Any]:
        return {
            "impact": _enum_value(
                self.impact,
                SourceConflictObligationImpact,
                SourceConflictObligationImpact.NO_OBLIGATION_IMPACT,
            ),
            "obligation_key": _clean_optional_text(self.obligation_key, limit=160),
            "required_source_class": _clean_optional_text(
                self.required_source_class,
                limit=80,
            ),
            "required_source_tier": _clean_optional_text(
                self.required_source_tier,
                limit=80,
            ),
            "lower_tier_cannot_satisfy_stronger_obligation": bool(
                self.lower_tier_cannot_satisfy_stronger_obligation
            ),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class SourceConflictRecord:
    """A pairwise unresolved conflict record; it never chooses a source."""

    conflict_id: str
    contradiction_shape: SourceConflictContradictionShape | str | Sequence[SourceConflictContradictionShape | str]
    claim_a: SourceConflictClaim
    claim_b: SourceConflictClaim
    centrality: SourceConflictCentrality | str = SourceConflictCentrality.UNKNOWN
    unresolved_state: SourceConflictUnresolvedState | str = SourceConflictUnresolvedState.UNRESOLVED
    obligation_impact: SourceConflictObligationImpactDetail | SourceConflictObligationImpact | str = (
        SourceConflictObligationImpact.NO_OBLIGATION_IMPACT
    )
    lower_tier_cannot_satisfy_stronger_obligation: bool = False
    controller_visible: bool = True
    ledger_compatible: bool = True
    winner_chosen: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "conflict_id", _clean_text(self.conflict_id, limit=120))
        if not isinstance(self.claim_a, SourceConflictClaim) or not isinstance(
            self.claim_b,
            SourceConflictClaim,
        ):
            raise TypeError("claim_a and claim_b must be SourceConflictClaim")
        object.__setattr__(
            self,
            "contradiction_shape",
            _copy_enum_tuple(
                self.contradiction_shape,
                SourceConflictContradictionShape,
                SourceConflictContradictionShape.AMBIGUOUS_OR_PARTIAL_CONFLICT,
            ),
        )
        object.__setattr__(
            self,
            "centrality",
            _enum_value(
                self.centrality,
                SourceConflictCentrality,
                SourceConflictCentrality.UNKNOWN,
            ),
        )
        object.__setattr__(
            self,
            "unresolved_state",
            _enum_value(
                self.unresolved_state,
                SourceConflictUnresolvedState,
                SourceConflictUnresolvedState.UNRESOLVED,
            ),
        )
        impact = self.obligation_impact
        if not isinstance(impact, SourceConflictObligationImpactDetail):
            impact = SourceConflictObligationImpactDetail(impact=impact)
        if self.lower_tier_cannot_satisfy_stronger_obligation and not (
            impact.lower_tier_cannot_satisfy_stronger_obligation
        ):
            impact = SourceConflictObligationImpactDetail(
                impact=impact.impact,
                obligation_key=impact.obligation_key,
                required_source_class=impact.required_source_class,
                required_source_tier=impact.required_source_tier,
                lower_tier_cannot_satisfy_stronger_obligation=True,
                notes=impact.notes,
            )
        object.__setattr__(self, "obligation_impact", impact)
        object.__setattr__(
            self,
            "lower_tier_cannot_satisfy_stronger_obligation",
            bool(impact.lower_tier_cannot_satisfy_stronger_obligation),
        )
        object.__setattr__(self, "winner_chosen", False)

    @property
    def source_ids(self) -> tuple[str, str]:
        return (self.claim_a.source_ref.source_id, self.claim_b.source_ref.source_id)

    @property
    def claim_ids(self) -> tuple[str, str]:
        return (self.claim_a.claim_id, self.claim_b.claim_id)

    def to_dict(self) -> dict[str, Any]:
        impact = self.obligation_impact
        return {
            "conflict_id": self.conflict_id,
            "contradiction_shape": list(self.contradiction_shape),
            "claim_a": self.claim_a.to_dict(),
            "claim_b": self.claim_b.to_dict(),
            "centrality": _enum_value(
                self.centrality,
                SourceConflictCentrality,
                SourceConflictCentrality.UNKNOWN,
            ),
            "unresolved_state": _enum_value(
                self.unresolved_state,
                SourceConflictUnresolvedState,
                SourceConflictUnresolvedState.UNRESOLVED,
            ),
            "obligation_impact": impact.to_dict(),
            "lower_tier_cannot_satisfy_stronger_obligation": bool(
                self.lower_tier_cannot_satisfy_stronger_obligation
            ),
            "controller_visible": bool(self.controller_visible),
            "ledger_compatible": bool(self.ledger_compatible),
            "winner_chosen": False,
            "involved_source_ids": list(self.source_ids),
            "involved_claim_ids": list(self.claim_ids),
        }


@dataclass(frozen=True)
class SourceConflictGroup:
    """A Controller-visible group of unresolved conflict records."""

    group_id: str
    records: tuple[SourceConflictRecord, ...]
    controller_visible: bool = True
    ledger_compatible: bool = True
    arbitration_ready: bool = True
    final_answer_behavior_changed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_id", _clean_text(self.group_id, limit=120))
        object.__setattr__(self, "records", tuple(self.records or ()))
        if not all(isinstance(record, SourceConflictRecord) for record in self.records):
            raise TypeError("records must contain SourceConflictRecord values")
        object.__setattr__(self, "final_answer_behavior_changed", False)

    @property
    def involved_source_ids(self) -> tuple[str, ...]:
        return _dedupe_tuple(source_id for record in self.records for source_id in record.source_ids)

    @property
    def involved_source_classes(self) -> tuple[str, ...]:
        return _dedupe_tuple(
            value
            for record in self.records
            for value in (
                record.claim_a.source_class or record.claim_a.source_ref.source_class,
                record.claim_b.source_class or record.claim_b.source_ref.source_class,
            )
            if value
        )

    @property
    def involved_claim_keys(self) -> tuple[str, ...]:
        return _dedupe_tuple(
            key
            for record in self.records
            for key in (
                record.claim_a.normalized_claim_key,
                record.claim_b.normalized_claim_key,
            )
        )

    @property
    def unresolved_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.unresolved_state
            != SourceConflictUnresolvedState.OUT_OF_SCOPE.value
        )

    @property
    def highest_obligation_impact(self) -> str:
        impacts = [
            SourceConflictObligationImpact(record.obligation_impact.impact)
            for record in self.records
        ]
        if not impacts:
            return SourceConflictObligationImpact.NO_OBLIGATION_IMPACT.value
        return max(impacts, key=lambda item: _IMPACT_PRIORITY[item]).value

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_CONFLICT_SCHEMA_VERSION,
            "group_id": self.group_id,
            "records": [record.to_dict() for record in self.records],
            "involved_source_ids": list(self.involved_source_ids),
            "involved_source_classes": list(self.involved_source_classes),
            "involved_claim_keys": list(self.involved_claim_keys),
            "unresolved_count": self.unresolved_count,
            "highest_obligation_impact": self.highest_obligation_impact,
            "controller_visible": bool(self.controller_visible),
            "ledger_compatible": bool(self.ledger_compatible),
            "arbitration_ready": bool(self.arbitration_ready),
            "final_answer_behavior_changed": False,
            "winner_chosen": False,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SOURCE_CONFLICT_TRACE_KEY: self.to_controller_state()}


@dataclass(frozen=True)
class SourceConflictRepresentation:
    """Top-level passive representation suitable for controller trace storage."""

    groups: tuple[SourceConflictGroup, ...]
    schema_version: str = SOURCE_CONFLICT_SCHEMA_VERSION
    controller_visible: bool = True
    ledger_compatible: bool = True
    runtime_behavior_changed: bool = False
    final_answer_behavior_changed: bool = False
    winner_chosen: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", tuple(self.groups or ()))
        if not all(isinstance(group, SourceConflictGroup) for group in self.groups):
            raise TypeError("groups must contain SourceConflictGroup values")
        object.__setattr__(self, "runtime_behavior_changed", False)
        object.__setattr__(self, "final_answer_behavior_changed", False)
        object.__setattr__(self, "winner_chosen", False)

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "groups": [group.to_controller_state() for group in self.groups],
            "group_count": len(self.groups),
            "unresolved_count": sum(group.unresolved_count for group in self.groups),
            "controller_visible": bool(self.controller_visible),
            "ledger_compatible": bool(self.ledger_compatible),
            "runtime_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "winner_chosen": False,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {SOURCE_CONFLICT_TRACE_KEY: self.to_controller_state()}


# Fixture/static construction helpers. These preserve inputs; they do not
# inspect external sources or make authority decisions.
def build_source_conflict_record(
    *,
    conflict_id: str,
    contradiction_shape: SourceConflictContradictionShape | str | Sequence[SourceConflictContradictionShape | str],
    claim_a: SourceConflictClaim,
    claim_b: SourceConflictClaim,
    centrality: SourceConflictCentrality | str = SourceConflictCentrality.UNKNOWN,
    unresolved_state: SourceConflictUnresolvedState | str = SourceConflictUnresolvedState.UNRESOLVED,
    obligation_impact: SourceConflictObligationImpactDetail | SourceConflictObligationImpact | str = SourceConflictObligationImpact.NO_OBLIGATION_IMPACT,
    lower_tier_cannot_satisfy_stronger_obligation: bool = False,
) -> SourceConflictRecord:
    return SourceConflictRecord(
        conflict_id=conflict_id,
        contradiction_shape=contradiction_shape,
        claim_a=claim_a,
        claim_b=claim_b,
        centrality=centrality,
        unresolved_state=unresolved_state,
        obligation_impact=obligation_impact,
        lower_tier_cannot_satisfy_stronger_obligation=(
            lower_tier_cannot_satisfy_stronger_obligation
        ),
    )


def build_source_conflict_group(
    *,
    group_id: str,
    records: Sequence[SourceConflictRecord],
) -> SourceConflictGroup:
    return SourceConflictGroup(group_id=group_id, records=tuple(records))


def build_source_conflict_representation(
    groups: Sequence[SourceConflictGroup],
) -> SourceConflictRepresentation:
    return SourceConflictRepresentation(groups=tuple(groups))


def source_ref_from_evidence(
    evidence: Mapping[str, Any],
    *,
    fallback_source_id: str | None = None,
    evidence_position: int | None = None,
) -> SourceConflictSourceRef:
    """Create a source ref from already-sanitized evidence mapping fields."""

    source_id = evidence.get("source_id") or fallback_source_id or evidence.get("id")
    text = str(evidence.get("text") or evidence.get("excerpt") or "")
    return SourceConflictSourceRef(
        source_id=str(source_id or "unknown_source"),
        url=_optional_str(evidence.get("url")),
        title=_optional_str(evidence.get("title")),
        domain=_optional_str(evidence.get("domain")),
        source_class=_optional_str(evidence.get("source_class")),
        source_tier=_optional_str(evidence.get("source_tier")),
        publisher=_optional_str(evidence.get("publisher")),
        issuer=_optional_str(evidence.get("issuer")),
        retrieved_at=_optional_str(evidence.get("retrieved_at")),
        observed_at=_optional_str(evidence.get("observed_at")),
        published_at=_optional_str(evidence.get("published_at")),
        updated_at=_optional_str(evidence.get("updated_at")),
        effective_date=_optional_str(evidence.get("effective_date")),
        currentness_label=_optional_str(evidence.get("currentness_label"))
        or SourceConflictCurrentness.UNKNOWN,
        jurisdiction=_optional_str(evidence.get("jurisdiction")),
        scope=_optional_str(evidence.get("scope")),
        evidence_position=evidence_position,
        evidence_hash=_hash_mapping(evidence),
        text_hash=sha256(text.encode("utf-8")).hexdigest() if text else None,
        authority_weight_hint=_optional_str(evidence.get("authority_weight_hint")),
    )


def _clean_text(value: Any, *, limit: int, default: str = "unknown") -> str:
    text = " ".join(str(value or "").split())
    if not text:
        text = default
    return text[:limit]


def _clean_optional_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] if text else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _positive_int_or_none(value: Any) -> int | None:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None
    return integer if integer > 0 else None


def _domain_from_url(url: Any) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    without_scheme = text.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0].split("?", 1)[0].lower() or None


def _enum_value(value: Any, enum_type: type[Enum], default: Enum) -> str:
    if isinstance(value, enum_type):
        return str(value.value)
    text = str(value or "").strip()
    allowed = {str(item.value): str(item.value) for item in enum_type}
    return allowed.get(text, str(default.value))


def _copy_enum_tuple(value: Any, enum_type: type[Enum], default: Enum) -> tuple[str, ...]:
    values = value if isinstance(value, (list, tuple, set, frozenset)) else (value,)
    out: list[str] = []
    for item in values:
        enum_value = _enum_value(item, enum_type, default)
        if enum_value not in out:
            out.append(enum_value)
    return tuple(out or (str(default.value),))


def _copy_string_tuple(value: Sequence[Any], *, cap: int, limit: int) -> tuple[str, ...]:
    out: list[str] = []
    for item in value or ():
        text = _clean_optional_text(item, limit=limit)
        if text and text not in out:
            out.append(text)
        if len(out) >= cap:
            break
    return tuple(out)


def _dedupe_tuple(values: Any) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        text = _clean_optional_text(value, limit=180)
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _hash_mapping(value: Mapping[str, Any]) -> str:
    pieces = [f"{key}={value.get(key)!r}" for key in sorted(str(k) for k in value.keys())]
    return sha256("|".join(pieces).encode("utf-8")).hexdigest()


__all__ = [
    "SOURCE_CONFLICT_SCHEMA_VERSION",
    "SOURCE_CONFLICT_TRACE_KEY",
    "SourceConflictCentrality",
    "SourceConflictClaim",
    "SourceConflictContradictionShape",
    "SourceConflictCurrentness",
    "SourceConflictGroup",
    "SourceConflictObligationImpact",
    "SourceConflictObligationImpactDetail",
    "SourceConflictRecord",
    "SourceConflictRepresentation",
    "SourceConflictScope",
    "SourceConflictSourceRef",
    "SourceConflictUnresolvedState",
    "SourceConflictValue",
    "build_source_conflict_group",
    "build_source_conflict_record",
    "build_source_conflict_representation",
    "source_ref_from_evidence",
]
