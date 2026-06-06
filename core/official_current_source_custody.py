"""RunAuthority-style custody for official/current source obligations.

AG-89B keeps this deliberately narrow: it records durable custody state for
required official/current/canonical source classes without changing acquisition,
provider, query, ranking, prompt, or Author behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class OfficialCurrentCustodyStatus(str, Enum):
    REQUIRED = "required"
    SEARCH_ATTEMPTED = "search_attempted"
    CANDIDATE_RETURNED = "candidate_returned"
    CANDIDATE_IDENTITY_MISSING = "candidate_identity_missing"
    CANDIDATE_AGGREGATE_ONLY = "candidate_aggregate_only"
    CANDIDATE_UNREADABLE = "candidate_unreadable"
    CANDIDATE_REJECTED = "candidate_rejected"
    CANDIDATE_ACCEPTED = "candidate_accepted"
    CANDIDATE_PARTIALLY_ACCEPTED = "candidate_partially_accepted"
    CANDIDATE_SUPERSEDED = "candidate_superseded"
    CANDIDATE_UNAVAILABLE = "candidate_unavailable"
    REQUIREMENT_SATISFIED = "requirement_satisfied"
    REQUIREMENT_UNSATISFIED = "requirement_unsatisfied"
    RETRY_AUTHORIZED = "retry_authorized"
    STOP_INSUFFICIENT_AUTHORIZED = "stop_insufficient_authorized"


_REQUIRED_STATUSES = frozenset(item.value for item in OfficialCurrentCustodyStatus)
_SATISFYING_CANDIDATE_STATUSES = frozenset(
    {
        OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED.value,
        OfficialCurrentCustodyStatus.CANDIDATE_PARTIALLY_ACCEPTED.value,
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


@dataclass(frozen=True, slots=True)
class OfficialCurrentCustodyRecord:
    requirement_id: str
    status: OfficialCurrentCustodyStatus | str
    source_class: str | None = None
    attempt_id: str | None = None
    candidate_id: str | None = None
    missing_identity_reason: str | None = None
    disposition_reason: str | None = None
    action_id: str | None = None
    sequence: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, OfficialCurrentCustodyStatus) else str(self.status)
        if status not in _REQUIRED_STATUSES:
            raise ValueError(f"unknown official/current custody status: {status}")
        if not _clean_token(self.requirement_id, limit=120):
            raise ValueError("official/current custody records require a requirement_id")
        if status in _SATISFYING_CANDIDATE_STATUSES and not _clean_token(self.candidate_id, limit=160):
            raise ValueError("accepted official/current custody records require candidate_id")
        if status == OfficialCurrentCustodyStatus.CANDIDATE_IDENTITY_MISSING.value and not _clean_token(self.missing_identity_reason, limit=160):
            raise ValueError("candidate_identity_missing requires missing_identity_reason")
        if status == OfficialCurrentCustodyStatus.CANDIDATE_AGGREGATE_ONLY.value and not _clean_token(self.disposition_reason, limit=160):
            raise ValueError("candidate_aggregate_only requires disposition_reason")
        object.__setattr__(self, "status", OfficialCurrentCustodyStatus(status))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "requirement_id": _clean_token(self.requirement_id, limit=120),
            "status": self.status.value,
            "source_class": _clean_token(self.source_class, limit=100),
            "attempt_id": _clean_token(self.attempt_id, limit=120),
            "candidate_id": _clean_token(self.candidate_id, limit=160),
            "missing_identity_reason": _clean_text(self.missing_identity_reason, limit=180),
            "disposition_reason": _clean_text(self.disposition_reason, limit=180),
            "action_id": _clean_token(self.action_id, limit=120),
            "sequence": int(self.sequence),
            "metadata": _safe_mapping(self.metadata),
        }
        return {key: value for key, value in payload.items() if value not in (None, {}, [])}


@dataclass(frozen=True, slots=True)
class OfficialCurrentCustodyRequirement:
    requirement_id: str
    source_class: str
    status: str
    satisfied_candidate_ids: tuple[str, ...] = ()
    unsatisfied_reason: str | None = None

    @property
    def satisfied(self) -> bool:
        return self.status == OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED.value

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "requirement_id": self.requirement_id,
            "source_class": self.source_class,
            "status": self.status,
            "satisfied_candidate_ids": list(self.satisfied_candidate_ids),
            "unsatisfied_reason": self.unsatisfied_reason,
        }
        return {key: value for key, value in payload.items() if value not in (None, [], {})}


@dataclass(frozen=True, slots=True)
class OfficialCurrentSourceCustodyState:
    records: tuple[OfficialCurrentCustodyRecord, ...] = ()

    @classmethod
    def for_required_source_classes(
        cls,
        source_classes: Iterable[str],
        *,
        existing_records: Sequence[OfficialCurrentCustodyRecord] | None = None,
    ) -> "OfficialCurrentSourceCustodyState":
        state = cls(tuple(existing_records or ()))
        for source_class in source_classes:
            state = state.require(source_class)
        return state.finalize_requirements()

    @classmethod
    def from_projection(
        cls,
        projection: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    ) -> "OfficialCurrentSourceCustodyState":
        if not projection:
            return cls()
        raw_records: Any
        if isinstance(projection, Mapping):
            raw_records = projection.get("records", ())
        else:
            raw_records = projection
        records: list[OfficialCurrentCustodyRecord] = []
        if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
            return cls()
        for item in raw_records:
            if not isinstance(item, Mapping):
                continue
            try:
                records.append(
                    OfficialCurrentCustodyRecord(
                        requirement_id=str(item.get("requirement_id") or ""),
                        status=str(item.get("status") or ""),
                        source_class=_clean_token(item.get("source_class"), limit=100),
                        attempt_id=_clean_token(item.get("attempt_id"), limit=120),
                        candidate_id=_clean_token(item.get("candidate_id"), limit=160),
                        missing_identity_reason=_clean_text(item.get("missing_identity_reason"), limit=180),
                        disposition_reason=_clean_text(item.get("disposition_reason"), limit=180),
                        action_id=_clean_token(item.get("action_id"), limit=120),
                        sequence=int(item.get("sequence") or len(records)),
                        metadata=_safe_mapping(item.get("metadata")),
                    )
                )
            except (TypeError, ValueError):
                continue
        return cls(tuple(records)).finalize_requirements()

    def require(self, source_class: str, *, requirement_id: str | None = None) -> "OfficialCurrentSourceCustodyState":
        clean_class = _clean_token(source_class, limit=100)
        if not clean_class:
            return self
        req_id = _clean_token(requirement_id, limit=120) or _requirement_id_for_source_class(clean_class)
        if any(record.requirement_id == req_id and record.status is OfficialCurrentCustodyStatus.REQUIRED for record in self.records):
            return self
        return self._append(
            OfficialCurrentCustodyRecord(
                requirement_id=req_id,
                source_class=clean_class,
                status=OfficialCurrentCustodyStatus.REQUIRED,
            )
        )

    def record_search_attempted(self, requirement_id: str, *, attempt_id: str, action_id: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.SEARCH_ATTEMPTED, attempt_id=attempt_id, action_id=action_id))

    def record_candidate_returned(self, requirement_id: str, *, candidate_id: str, attempt_id: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.CANDIDATE_RETURNED, candidate_id=candidate_id, attempt_id=attempt_id))

    def record_candidate_identity_missing(self, requirement_id: str, *, reason: str, attempt_id: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.CANDIDATE_IDENTITY_MISSING, missing_identity_reason=reason, attempt_id=attempt_id))

    def record_candidate_aggregate_only(self, requirement_id: str, *, reason: str, attempt_id: str | None = None, metadata: Mapping[str, Any] | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.CANDIDATE_AGGREGATE_ONLY, disposition_reason=reason, attempt_id=attempt_id, metadata=metadata or {}))

    def record_candidate_disposition(self, requirement_id: str, *, status: OfficialCurrentCustodyStatus | str, candidate_id: str | None = None, reason: str | None = None, attempt_id: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=status, candidate_id=candidate_id, disposition_reason=reason, attempt_id=attempt_id))

    def record_retry_authorized(self, requirement_id: str, *, reason: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.RETRY_AUTHORIZED, disposition_reason=reason))

    def record_stop_insufficient_authorized(self, requirement_id: str, *, reason: str | None = None) -> "OfficialCurrentSourceCustodyState":
        return self._append(OfficialCurrentCustodyRecord(requirement_id=requirement_id, status=OfficialCurrentCustodyStatus.STOP_INSUFFICIENT_AUTHORIZED, disposition_reason=reason))

    def finalize_requirements(self) -> "OfficialCurrentSourceCustodyState":
        records = list(self.records)
        for requirement_id in self.requirement_ids():
            existing_terminal = [record for record in records if record.requirement_id == requirement_id and record.status in (OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED, OfficialCurrentCustodyStatus.REQUIREMENT_UNSATISFIED)]
            status = OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED if self.satisfied_candidate_ids(requirement_id) else OfficialCurrentCustodyStatus.REQUIREMENT_UNSATISFIED
            if existing_terminal and existing_terminal[-1].status is status:
                continue
            source_class = self.source_class_for(requirement_id)
            records.append(
                OfficialCurrentCustodyRecord(
                    requirement_id=requirement_id,
                    source_class=source_class,
                    status=status,
                    disposition_reason=None if status is OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED else "no_accepted_or_partially_accepted_candidate_custody",
                    sequence=len(records),
                )
            )
        return replace(self, records=tuple(records))

    def requirement_ids(self) -> tuple[str, ...]:
        ids: list[str] = []
        for record in self.records:
            if record.status is OfficialCurrentCustodyStatus.REQUIRED and record.requirement_id not in ids:
                ids.append(record.requirement_id)
        return tuple(ids)

    def source_class_for(self, requirement_id: str) -> str | None:
        for record in self.records:
            if record.requirement_id == requirement_id and record.source_class:
                return record.source_class
        return None

    def satisfied_candidate_ids(self, requirement_id: str) -> tuple[str, ...]:
        ids: list[str] = []
        for record in self.records:
            if record.requirement_id != requirement_id or record.status.value not in _SATISFYING_CANDIDATE_STATUSES:
                continue
            if record.candidate_id and record.candidate_id not in ids:
                ids.append(record.candidate_id)
        return tuple(ids)

    def satisfaction_by_source_class(self) -> tuple[list[str], list[str]]:
        satisfied: list[str] = []
        unsatisfied: list[str] = []
        finalized = self.finalize_requirements() if not any(record.status in (OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED, OfficialCurrentCustodyStatus.REQUIREMENT_UNSATISFIED) for record in self.records) else self
        for requirement_id in finalized.requirement_ids():
            source_class = finalized.source_class_for(requirement_id)
            if not source_class:
                continue
            target = satisfied if finalized.satisfied_candidate_ids(requirement_id) else unsatisfied
            if source_class not in target:
                target.append(source_class)
        return satisfied, unsatisfied

    def requirements(self) -> tuple[OfficialCurrentCustodyRequirement, ...]:
        out: list[OfficialCurrentCustodyRequirement] = []
        finalized = self.finalize_requirements()
        for requirement_id in finalized.requirement_ids():
            candidate_ids = finalized.satisfied_candidate_ids(requirement_id)
            out.append(
                OfficialCurrentCustodyRequirement(
                    requirement_id=requirement_id,
                    source_class=finalized.source_class_for(requirement_id) or "unknown",
                    status=(OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED.value if candidate_ids else OfficialCurrentCustodyStatus.REQUIREMENT_UNSATISFIED.value),
                    satisfied_candidate_ids=candidate_ids,
                    unsatisfied_reason=None if candidate_ids else "no_accepted_or_partially_accepted_candidate_custody",
                )
            )
        return tuple(out)

    def to_dict(self) -> dict[str, Any]:
        finalized = self.finalize_requirements()
        return {
            "schema_version": "official_current_source_custody_ag89b_v1",
            "trace_mode": "runauthority_custody_projection",
            "requirements": [requirement.to_dict() for requirement in finalized.requirements()],
            "records": [record.to_dict() for record in finalized.records],
        }

    def _append(self, record: OfficialCurrentCustodyRecord) -> "OfficialCurrentSourceCustodyState":
        return replace(self, records=(*self.records, replace(record, sequence=len(self.records))))


def _requirement_id_for_source_class(source_class: str) -> str:
    return f"official_current_source:{source_class}"


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            continue
        clean_key = _clean_token(key, limit=80)
        if clean_key:
            out[clean_key] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:20]]
    return _clean_text(value, limit=300)


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


def _clean_token(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "OfficialCurrentCustodyRecord",
    "OfficialCurrentCustodyRequirement",
    "OfficialCurrentCustodyStatus",
    "OfficialCurrentSourceCustodyState",
]
