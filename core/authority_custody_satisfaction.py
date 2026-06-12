"""Custody-aware authority satisfaction predicates.

This module is pure control glue over already-sanitized runtime projections. It
does not retrieve, route providers, generate queries, rank/filter sources, cite
sources, build prompts, or alter final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CATEGORY_CUSTODY_BACKED_AUTHORITY = "custody_backed_authority_satisfaction"
CATEGORY_LOWER_TIER_CONTEXT = "lower_tier_context"
CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY = "legacy_aggregate_observability"
CATEGORY_NO_PROOF = "no_authority_custody_proof"

REASON_AGGREGATE_STATUS_DEMOTED = "aggregate_status_demoted_no_custody"
REASON_AGGREGATE_COUNT_DEMOTED = "aggregate_count_demoted_no_custody"
REASON_LEGACY_GAP_BLOCKS_AGGREGATE = "legacy_gap_blocks_aggregate_satisfaction"
REASON_CANDIDATE_PASSPORT_SATISFIED = "candidate_passport_custody_satisfied"
REASON_SELECTED_AUTHORITY_EVIDENCE_SATISFIED = (
    "selected_authority_evidence_satisfied"
)
REASON_OFFICIAL_CURRENT_CUSTODY_SATISFIED = "official_current_custody_satisfied"
REASON_FINAL_ANSWER_PACKET_CUSTODY_SATISFIED = (
    "final_answer_packet_custody_satisfied"
)
REASON_LOWER_TIER_CONTEXT = "weak_secondary_context_not_authority_satisfying"
REASON_NO_AUTHORITY_CUSTODY_PROOF = "no_authority_custody_proof"

_STRONG_STATUS_VALUES = frozenset({"satisfied_strong", "strongly_satisfied"})
_LOWER_TIER_STATUS_VALUES = frozenset(
    {
        "expected_but_only_secondary",
        "expected_only_secondary",
        "secondary_only",
        "satisfied_weak",
        "weakly_satisfied",
        "weak_satisfied",
    }
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
)
_CLASS_COUNT_KEYS = (
    "source_class_strong_satisfaction_counts",
    "recovered_source_class_counts",
    "source_survival_source_class_counts",
)
_AGGREGATE_COUNT_KEYS = (
    "final_evidence_official_or_canonical_count",
    "final_citation_official_or_canonical_count",
    "final_selected_authority_evidence_count",
    "source_survival_final_evidence_official_or_canonical_count",
    "source_survival_final_citation_official_or_canonical_count",
    "source_survival_final_selected_authority_evidence_count",
    "source_survival_official_or_canonical_count",
    "candidate_official_or_canonical_count",
    "candidate_official_source_count",
    "accepted_or_readable_official_source_count",
    "accepted_official_or_canonical_count",
)
_PASSPORT_SATISFYING_DISPOSITIONS = frozenset(
    {
        "promoted_final_authority_evidence",
        "accepted",
        "candidate_accepted",
        "accepted_authority_evidence",
        "requirement_satisfied",
    }
)
_OFFICIAL_CUSTODY_SATISFYING_STATUSES = frozenset(
    {
        "candidate_accepted",
        "candidate_partially_accepted",
        "requirement_satisfied",
    }
)


@dataclass(frozen=True, slots=True)
class AuthorityCustodySatisfaction:
    """Trace-safe result for one required source class."""

    source_class: str
    category: str
    reason: str
    evidence_id: str | None = None
    observed_source_class: str | None = None

    @property
    def authority_satisfied(self) -> bool:
        return self.category == CATEGORY_CUSTODY_BACKED_AUTHORITY

    @property
    def lower_tier_context(self) -> bool:
        return self.category == CATEGORY_LOWER_TIER_CONTEXT

    @property
    def legacy_aggregate_observability(self) -> bool:
        return self.category == CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_class": self.source_class,
            "category": self.category,
            "reason": self.reason,
            "evidence_id": self.evidence_id,
            "observed_source_class": self.observed_source_class,
            "authority_satisfied": self.authority_satisfied,
        }


def authority_custody_satisfaction_for_source_class(
    source_class: str,
    *sources: Mapping[str, Any] | None,
    authority_class: str | None = None,
) -> AuthorityCustodySatisfaction:
    """Return whether a required source class has custody-backed satisfaction."""

    clean_source_class = _clean_token(source_class) or ""
    aliases = _class_aliases(clean_source_class, authority_class)
    sanitized_sources = tuple(_safe_mapping(source) for source in sources if source)

    for detector in (
        _selected_authority_evidence_satisfaction,
        _candidate_passport_satisfaction,
        _official_current_custody_satisfaction,
        _final_answer_packet_custody_satisfaction,
    ):
        result = detector(clean_source_class, aliases, sanitized_sources)
        if result is not None:
            return result

    statuses = _status_values_for_class(sanitized_sources, aliases)
    lower_tier_context = bool(statuses & _LOWER_TIER_STATUS_VALUES)
    aggregate_status = bool(statuses & _STRONG_STATUS_VALUES)
    aggregate_count = _class_count_positive(sanitized_sources, aliases)
    aggregate_final_or_survival_count = _aggregate_count_positive(sanitized_sources)
    legacy_gap_observed = _legacy_gap_observed(sanitized_sources)

    if lower_tier_context:
        return AuthorityCustodySatisfaction(
            source_class=clean_source_class,
            category=CATEGORY_LOWER_TIER_CONTEXT,
            reason=REASON_LOWER_TIER_CONTEXT,
        )
    if (aggregate_status or aggregate_count or aggregate_final_or_survival_count) and (
        legacy_gap_observed
    ):
        return AuthorityCustodySatisfaction(
            source_class=clean_source_class,
            category=CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY,
            reason=REASON_LEGACY_GAP_BLOCKS_AGGREGATE,
        )
    if aggregate_status:
        return AuthorityCustodySatisfaction(
            source_class=clean_source_class,
            category=CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY,
            reason=REASON_AGGREGATE_STATUS_DEMOTED,
        )
    if aggregate_count or aggregate_final_or_survival_count:
        return AuthorityCustodySatisfaction(
            source_class=clean_source_class,
            category=CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY,
            reason=REASON_AGGREGATE_COUNT_DEMOTED,
        )
    return AuthorityCustodySatisfaction(
        source_class=clean_source_class,
        category=CATEGORY_NO_PROOF,
        reason=REASON_NO_AUTHORITY_CUSTODY_PROOF,
    )


def _selected_authority_evidence_satisfaction(
    source_class: str,
    aliases: frozenset[str],
    sources: Sequence[Mapping[str, Any]],
) -> AuthorityCustodySatisfaction | None:
    for record in _selected_authority_evidence_records(sources):
        if _aggregate_only_selected_record(record):
            continue
        if not _record_matches_class(record, aliases):
            continue
        identity = _record_identity(record)
        if not identity:
            continue
        if record.get("satisfies_authority") is False:
            continue
        return AuthorityCustodySatisfaction(
            source_class=source_class,
            category=CATEGORY_CUSTODY_BACKED_AUTHORITY,
            reason=REASON_SELECTED_AUTHORITY_EVIDENCE_SATISFIED,
            evidence_id=identity,
            observed_source_class=_observed_class(record),
        )
    return None


def _candidate_passport_satisfaction(
    source_class: str,
    aliases: frozenset[str],
    sources: Sequence[Mapping[str, Any]],
) -> AuthorityCustodySatisfaction | None:
    for passport in _candidate_passport_records(sources):
        if not _record_matches_class(passport, aliases):
            continue
        identity = _record_identity(passport)
        if not identity:
            continue
        if passport.get("satisfies_authority") is not True:
            continue
        if passport.get("readable_text_available") is False:
            continue
        if _clean_token(passport.get("readability_status")) in {
            "unreadable",
            "readability_failed",
        }:
            continue
        disposition = _clean_token(passport.get("final_disposition"))
        if disposition not in _PASSPORT_SATISFYING_DISPOSITIONS:
            continue
        return AuthorityCustodySatisfaction(
            source_class=source_class,
            category=CATEGORY_CUSTODY_BACKED_AUTHORITY,
            reason=REASON_CANDIDATE_PASSPORT_SATISFIED,
            evidence_id=identity,
            observed_source_class=_observed_class(passport),
        )
    return None


def _official_current_custody_satisfaction(
    source_class: str,
    aliases: frozenset[str],
    sources: Sequence[Mapping[str, Any]],
) -> AuthorityCustodySatisfaction | None:
    for projection in _official_current_custody_projections(sources):
        for requirement in _record_list(projection.get("requirements")):
            if not _record_matches_class(requirement, aliases):
                continue
            if _clean_token(requirement.get("status")) != "requirement_satisfied":
                continue
            identity = _first_identity(requirement.get("satisfied_candidate_ids"))
            if not identity:
                continue
            return AuthorityCustodySatisfaction(
                source_class=source_class,
                category=CATEGORY_CUSTODY_BACKED_AUTHORITY,
                reason=REASON_OFFICIAL_CURRENT_CUSTODY_SATISFIED,
                evidence_id=identity,
                observed_source_class=_observed_class(requirement),
            )
        for record in _record_list(projection.get("records")):
            if not _record_matches_class(record, aliases):
                continue
            if (
                _clean_token(record.get("status"))
                not in _OFFICIAL_CUSTODY_SATISFYING_STATUSES
            ):
                continue
            identity = _record_identity(record)
            if not identity:
                continue
            return AuthorityCustodySatisfaction(
                source_class=source_class,
                category=CATEGORY_CUSTODY_BACKED_AUTHORITY,
                reason=REASON_OFFICIAL_CURRENT_CUSTODY_SATISFIED,
                evidence_id=identity,
                observed_source_class=_observed_class(record),
            )
    return None


def _final_answer_packet_custody_satisfaction(
    source_class: str,
    aliases: frozenset[str],
    sources: Sequence[Mapping[str, Any]],
) -> AuthorityCustodySatisfaction | None:
    for packet in _final_answer_packet_payloads(sources):
        for obligation in _record_list(packet.get("source_obligations")):
            if not _record_matches_class(obligation, aliases):
                continue
            if _clean_token(obligation.get("status")) != "source_obligation_satisfied":
                continue
            identity = _first_identity(obligation.get("satisfied_candidate_ids"))
            if not identity:
                continue
            return AuthorityCustodySatisfaction(
                source_class=source_class,
                category=CATEGORY_CUSTODY_BACKED_AUTHORITY,
                reason=REASON_FINAL_ANSWER_PACKET_CUSTODY_SATISFIED,
                evidence_id=identity,
                observed_source_class=_observed_class(obligation),
            )
    return None


def _selected_authority_evidence_records(
    sources: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for source in sources:
        records.extend(_record_list(source.get("selected_authority_evidence")))
        records.extend(
            _record_list(source.get("authority_lifecycle_selected_authority_evidence"))
        )
        authority = _mapping(source.get("authority_lifecycle"))
        candidate_fit = _mapping(authority.get("candidate_fit"))
        records.extend(_record_list(candidate_fit.get("selected_authority_evidence")))
        for ledger in _ledger_payloads(source):
            records.extend(_record_list(ledger.get("selected_evidence")))
            for event in _record_list(ledger.get("events")):
                if _clean_text(event.get("event_type"), limit=80) in {
                    "AuthorityEvidenceSelected",
                    "authority_evidence_selected",
                }:
                    records.append(event)
    return tuple(records)


def _candidate_passport_records(
    sources: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    for source in sources:
        for passport in _passport_payloads(source):
            records.extend(_record_list(passport.get("passports")))
    return tuple(records)


def _official_current_custody_projections(
    sources: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    projections: list[Mapping[str, Any]] = []
    for source in sources:
        direct = _mapping(source.get("official_current_source_custody"))
        if direct:
            projections.append(direct)
        bridge = _mapping(source.get("OfficialSourceObligationBridge"))
        bridge_custody = _mapping(bridge.get("official_current_source_custody"))
        if bridge_custody:
            projections.append(bridge_custody)
        if (
            _clean_text(source.get("schema_version"), limit=80)
            == "official_current_source_custody_ag89b_v1"
        ):
            projections.append(source)
    return tuple(projections)


def _final_answer_packet_payloads(
    sources: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    packets: list[Mapping[str, Any]] = []
    for source in sources:
        for key in ("final_answer_packet", "final_answer_packet_projection"):
            packet = _mapping(source.get(key))
            if packet:
                packets.append(packet)
        if _clean_text(source.get("trace_mode"), limit=80) in {
            "final_answer_packet_authority_projection",
            "run_kernel_final_answer_packet_projection",
        }:
            packets.append(source)
    return tuple(packets)


def _ledger_payloads(source: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    payloads: list[Mapping[str, Any]] = []
    direct = _mapping(source.get("controller_evidence_ledger"))
    if direct:
        payloads.append(direct)
    if source.get("owner") == "ControllerEvidenceLedger":
        payloads.append(source)
    for payload in tuple(payloads):
        nested = _mapping(payload.get("ControllerEvidenceLedger"))
        if nested:
            payloads.append(nested)
    return tuple(payloads)


def _passport_payloads(source: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    payloads: list[Mapping[str, Any]] = []
    for key in (
        "authority_candidate_passport_projection",
        "AuthorityCandidatePassportProjection",
    ):
        payload = _mapping(source.get(key))
        if payload:
            payloads.append(payload)
    if source.get("passports") is not None:
        payloads.append(source)
    return tuple(payloads)


def _status_values_for_class(
    sources: Sequence[Mapping[str, Any]],
    aliases: frozenset[str],
) -> frozenset[str]:
    statuses: set[str] = set()
    for source in sources:
        status = source.get("source_class_satisfaction_status")
        if not isinstance(status, Mapping):
            continue
        for key, raw_value in status.items():
            if _clean_token(key) not in aliases:
                continue
            token = _clean_token(raw_value)
            if token:
                statuses.add(token)
    return frozenset(statuses)


def _class_count_positive(
    sources: Sequence[Mapping[str, Any]],
    aliases: frozenset[str],
) -> bool:
    for source in sources:
        for key in _CLASS_COUNT_KEYS:
            counts = source.get(key)
            if not isinstance(counts, Mapping):
                continue
            for alias in aliases:
                if _positive_int(counts.get(alias)):
                    return True
    return False


def _aggregate_count_positive(sources: Sequence[Mapping[str, Any]]) -> bool:
    for source in sources:
        if any(_positive_int(source.get(key)) for key in _AGGREGATE_COUNT_KEYS):
            return True
    return False


def _legacy_gap_observed(sources: Sequence[Mapping[str, Any]]) -> bool:
    for source in sources:
        if source.get("legacy_gap_observed") is True:
            return True
        if _clean_token(source.get("final_evidence_citation_custody_status")) == (
            "legacy_gap_observed"
        ):
            return True
        if _record_list(source.get("ledger_legacy_gap_types")):
            return True
        custody = _mapping(source.get("final_evidence_citation_custody"))
        if _clean_token(custody.get("status")) == "legacy_gap_observed":
            return True
        if _record_list(source.get("legacy_custody_gaps")):
            return True
        for ledger in _ledger_payloads(source):
            ledger_custody = _mapping(ledger.get("final_evidence_citation_custody"))
            if _clean_token(ledger_custody.get("status")) == "legacy_gap_observed":
                return True
            if _record_list(ledger.get("legacy_custody_gaps")):
                return True
    return False


def _aggregate_only_selected_record(record: Mapping[str, Any]) -> bool:
    selection_basis = _clean_token(record.get("selection_basis"))
    identity = _clean_text(
        record.get("evidence_id") or record.get("candidate_id"),
        limit=160,
    )
    if selection_basis == "visibility_export_aggregate":
        return True
    if identity and _legacy_or_aggregate_identity(identity):
        return True
    return False


def _record_matches_class(
    record: Mapping[str, Any],
    aliases: frozenset[str],
) -> bool:
    values = (
        record.get("source_class"),
        record.get("required_source_class"),
        record.get("observed_source_class"),
        record.get("required_authority"),
        record.get("requirement_id"),
    )
    return any((_clean_token(value) or "") in aliases for value in values)


def _observed_class(record: Mapping[str, Any]) -> str | None:
    for key in (
        "source_class",
        "observed_source_class",
        "required_source_class",
        "required_authority",
    ):
        token = _clean_token(record.get(key))
        if token:
            return token
    return None


def _record_identity(record: Mapping[str, Any]) -> str | None:
    for key in (
        "candidate_id",
        "evidence_id",
        "source_id",
        "url",
        "source_url",
        "accepted_url",
    ):
        identity = _clean_text(record.get(key), limit=160)
        if identity and not _legacy_or_aggregate_identity(identity):
            return identity
    return None


def _first_identity(value: Any) -> str | None:
    for item in _iter_values(value):
        identity = _clean_text(item, limit=160)
        if identity and not _legacy_or_aggregate_identity(identity):
            return identity
    return None


def _legacy_or_aggregate_identity(value: str) -> bool:
    normalized = value.casefold().replace("_", "-")
    return normalized.startswith("legacy-") or "visibility-export-aggregate" in normalized


def _class_aliases(source_class: str, authority_class: str | None) -> frozenset[str]:
    aliases = {source_class}
    authority = _clean_token(authority_class)
    if authority:
        aliases.add(authority)
    return frozenset(item for item in aliases if item)


def _mapping(value: Any) -> dict[str, Any]:
    return _safe_mapping(value) if isinstance(value, Mapping) else {}


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:40]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:40]]
    return _clean_text(value, limit=300)


def _record_list(value: Any) -> list[Mapping[str, Any]]:
    values = _iter_values(value)
    return [item for item in values if isinstance(item, Mapping)]


def _iter_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.values())
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _positive_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return False


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "AuthorityCustodySatisfaction",
    "CATEGORY_CUSTODY_BACKED_AUTHORITY",
    "CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY",
    "CATEGORY_LOWER_TIER_CONTEXT",
    "CATEGORY_NO_PROOF",
    "REASON_AGGREGATE_COUNT_DEMOTED",
    "REASON_AGGREGATE_STATUS_DEMOTED",
    "REASON_CANDIDATE_PASSPORT_SATISFIED",
    "REASON_FINAL_ANSWER_PACKET_CUSTODY_SATISFIED",
    "REASON_LEGACY_GAP_BLOCKS_AGGREGATE",
    "REASON_NO_AUTHORITY_CUSTODY_PROOF",
    "REASON_OFFICIAL_CURRENT_CUSTODY_SATISFIED",
    "REASON_SELECTED_AUTHORITY_EVIDENCE_SATISFIED",
    "authority_custody_satisfaction_for_source_class",
]
