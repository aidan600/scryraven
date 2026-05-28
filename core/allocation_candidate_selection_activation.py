"""AG-75A-Z allocation-candidate downstream disposition activation.

This helper reads already-sanitized AG-75A-Y custody, Authority Candidate
Passport, and ControllerEvidenceLedger facts. It does not retrieve, classify,
fit, rank, prompt, cite, write final prose, or mutate final evidence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.allocation_result_candidate_custody import (
    ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
    allocation_result_candidate_custody_payload,
)
from core.authority_candidate_passport import AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY
from core.controller_evidence_ledger import (
    AUTHORITY_EVIDENCE_SELECTED,
    CANDIDATE_DISPOSITIONED,
    CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
)

ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION = (
    "allocation_candidate_selection_activation_ag75a_z_v1"
)
ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY = (
    "allocation_candidate_selection_activation"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_LIST_ITEMS = 40
_MAX_TEXT_CHARS = 240
_LOWER_TIER_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "context", "analysis"}
)
_LOWER_TIER_CLASSES = frozenset({"secondary", "secondary_only", "context"})
_MISSING_CLASSIFICATION_VALUES = frozenset({"", UNKNOWN, NOT_OBSERVABLE})
_MISSING_CURRENTNESS_VALUES = frozenset({"", UNKNOWN, NOT_OBSERVABLE})
_MISSING_FIT_VALUES = frozenset({"", UNKNOWN, NOT_OBSERVABLE, "not_evaluated"})
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_trace",
    "key",
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "snippet",
    "text",
    "token",
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)


def build_allocation_candidate_selection_activation_trace(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the runtime trace envelope for AG-75A-Z activation state."""

    return {
        "schema_version": ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION,
        "trace_key": ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY,
        "trace_mode": "controller_ledger_allocation_candidate_selection_activation",
        "diagnostic_only": False,
        "sanitized": True,
        "behavior_changed": False,
        "AllocationCandidateSelectionActivation": (
            build_allocation_candidate_selection_activation_projection(runtime_trace)
        ),
    }


def build_allocation_candidate_selection_activation_projection(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify admitted allocation-result candidates by existing custody facts."""

    trace = _mapping(runtime_trace)
    custody = allocation_result_candidate_custody_payload(trace)
    admitted_candidates = _record_list(custody.get("represented_candidate_inputs"))
    passport_payload = _nested_payload(
        trace,
        AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
        "AuthorityCandidatePassportProjection",
    )
    ledger = _nested_payload(
        trace,
        CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY,
        "ControllerEvidenceLedger",
    )
    passports = _record_list(passport_payload.get("passports"))
    dispositions = [
        event
        for event in _record_list(ledger.get("events"))
        if event.get("event_type") == CANDIDATE_DISPOSITIONED
    ]
    selected = [
        event
        for event in _record_list(ledger.get("selected_evidence"))
        or _record_list(ledger.get("events"))
        if event.get("event_type") == AUTHORITY_EVIDENCE_SELECTED
    ]

    passport_index = _records_by_identity(passports)
    disposition_index = _events_by_candidate_id(dispositions)
    selected_index = _records_by_identity(selected)

    states = [
        _candidate_activation_state(
            candidate,
            allocation_authorized=custody.get("allocation_execution_authorized")
            is True,
            custody_available=bool(custody),
            passport_index=passport_index,
            disposition_index=disposition_index,
            selected_index=selected_index,
        )
        for candidate in admitted_candidates
    ]

    blocked_reason_counts = _reason_counts(states)
    return {
        "schema_version": ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION,
        "activation_owner": "ControllerEvidenceLedger",
        "allocation_owner": "ControllerRecoveryDecision",
        "custody_source": ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
        "admitted_candidate_count": len(admitted_candidates),
        "eligible_for_existing_disposition_count": sum(
            1 for state in states if state["eligible_for_existing_disposition"]
        ),
        "activated_disposition_count": sum(
            1 for state in states if state["ledger_disposition_present"]
        ),
        "selected_evidence_candidate_count": sum(
            1
            for state in states
            if state["activation_state"]
            == "selected_by_existing_downstream_selection_corridor"
        ),
        "rejected_or_blocked_candidate_count": sum(
            1
            for state in states
            if state["activation_state"]
            != "selected_by_existing_downstream_selection_corridor"
        ),
        "blocked_reasons": sorted(blocked_reason_counts),
        "blocked_reason_counts": blocked_reason_counts,
        "candidate_activation_states": states,
        "classification_required": True,
        "fit_required": True,
        "ledger_disposition_required": True,
        "bypass_prevented": True,
        "source_obligation_satisfied_by_allocation_result_alone": False,
        "final_answer_behavior_changed": False,
        "citation_behavior_changed": False,
        "raw_payload_exposed": False,
        "behavior_changed": False,
    }


def allocation_candidate_selection_activation_payload(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Extract the nested AG-75A-Z activation projection from a runtime trace."""

    trace = _mapping(runtime_trace)
    packet = trace.get(ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("AllocationCandidateSelectionActivation")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _candidate_activation_state(
    candidate: Mapping[str, Any],
    *,
    allocation_authorized: bool,
    custody_available: bool,
    passport_index: Mapping[str, Mapping[str, Any]],
    disposition_index: Mapping[str, Mapping[str, Any]],
    selected_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    identities = _identity_keys(candidate)
    candidate_id = _candidate_id(candidate)
    passport = _first_identity_record(identities, passport_index)
    if passport is not None:
        candidate_id = _candidate_id(passport) or candidate_id
        identities = identities | _identity_keys(passport)
    disposition = disposition_index.get(candidate_id)
    selected = _first_identity_record(identities, selected_index)

    source_tier = _clean_token((passport or candidate).get("source_tier"))
    source_class = _clean_token((passport or candidate).get("source_class"))
    currentness = _clean_token((passport or candidate).get("currentness_signal"))
    fit_state = _clean_token((passport or candidate).get("fit_state"))
    final_disposition = _clean_token((passport or {}).get("final_disposition"))

    classification_present = (
        passport is not None
        and source_class not in _MISSING_CLASSIFICATION_VALUES
        and currentness not in _MISSING_CURRENTNESS_VALUES
    )
    fit_present = passport is not None and fit_state not in _MISSING_FIT_VALUES
    ledger_disposition_present = disposition is not None
    lower_tier = source_tier in _LOWER_TIER_TIERS or source_class in _LOWER_TIER_CLASSES

    state, reason = _activation_state_and_reason(
        allocation_authorized=allocation_authorized,
        custody_available=custody_available,
        passport_present=passport is not None,
        classification_present=classification_present,
        fit_present=fit_present,
        ledger_disposition_present=ledger_disposition_present,
        lower_tier=lower_tier,
        final_disposition=final_disposition,
        selected=selected,
    )
    return {
        "candidate_id": candidate_id or UNKNOWN,
        "source_url": _clean_text(
            (passport or candidate).get("source_url")
            or (passport or candidate).get("url")
        ),
        "source_tier": source_tier or UNKNOWN,
        "source_class": source_class or UNKNOWN,
        "currentness_signal": currentness or UNKNOWN,
        "fit_state": fit_state or UNKNOWN,
        "final_disposition": final_disposition or UNKNOWN,
        "classification_currentness_present": classification_present,
        "candidate_fit_present": fit_present,
        "ledger_disposition_present": ledger_disposition_present,
        "selected_by_ledger": selected is not None,
        "eligible_for_existing_disposition": (
            allocation_authorized
            and custody_available
            and not lower_tier
            and classification_present
            and fit_present
        ),
        "activation_state": state,
        "blocked_reason": reason,
        "bypass_prevented": True,
        "source_obligation_satisfied_by_allocation_result_alone": False,
        "raw_payload_exposed": False,
    }


def _activation_state_and_reason(
    *,
    allocation_authorized: bool,
    custody_available: bool,
    passport_present: bool,
    classification_present: bool,
    fit_present: bool,
    ledger_disposition_present: bool,
    lower_tier: bool,
    final_disposition: str,
    selected: Mapping[str, Any] | None,
) -> tuple[str, str]:
    if not custody_available:
        return (
            "observational_only",
            "allocation_result_candidate_custody_missing",
        )
    if not allocation_authorized:
        return (
            "blocked_by_existing_rules",
            "controller_recovery_decision_authorization_missing",
        )
    if lower_tier:
        return (
            "blocked_by_existing_rules",
            "lower_tier_or_secondary_not_satisfying_official_current_obligation",
        )
    if not passport_present or not classification_present:
        return (
            "not_yet_eligible_for_downstream_disposition",
            "missing_classifier_currentness_state",
        )
    if not fit_present:
        return (
            "not_yet_eligible_for_downstream_disposition",
            "missing_candidate_fit_state",
        )
    if not ledger_disposition_present:
        return (
            "not_yet_eligible_for_downstream_disposition",
            "missing_controller_evidence_ledger_disposition",
        )
    if selected is not None or final_disposition == "promoted_final_authority_evidence":
        return (
            "selected_by_existing_downstream_selection_corridor",
            "selected_by_controller_evidence_ledger",
        )
    if final_disposition == "rejected":
        return "rejected_by_existing_rules", "candidate_disposition_rejected"
    return (
        "observational_only",
        "controller_disposition_not_selected_for_final_evidence",
    )


def _nested_payload(
    trace: Mapping[str, Any],
    trace_key: str,
    payload_key: str,
) -> dict[str, Any]:
    packet = trace.get(trace_key)
    if isinstance(packet, Mapping):
        payload = packet.get(payload_key)
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
        return _safe_mapping(packet)
    return {}


def _records_by_identity(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record in records:
        safe = _safe_mapping(record)
        for key in _identity_keys(safe):
            out.setdefault(key, safe)
    return out


def _events_by_candidate_id(
    events: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        candidate_id = _candidate_id(event)
        if candidate_id:
            out.setdefault(candidate_id, _safe_mapping(event))
    return out


def _first_identity_record(
    keys: set[str],
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    for key in keys:
        record = index.get(key)
        if record is not None:
            return _safe_mapping(record)
    return None


def _identity_keys(record: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("candidate_id", "source_id", "evidence_id", "provider_result_id"):
        text = _clean_text(record.get(key))
        if text:
            keys.add(f"id:{text.casefold()}")
    url = _normalize_url(record.get("source_url") or record.get("url"))
    if url:
        keys.add(f"url:{url}")
    return keys


def _candidate_id(record: Mapping[str, Any]) -> str:
    for key in ("candidate_id", "source_id", "evidence_id"):
        text = _clean_text(record.get(key))
        if text:
            return text
    return ""


def _reason_counts(states: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for state in states:
        reason = _clean_text(state.get("blocked_reason")) or UNKNOWN
        if reason == "selected_by_controller_evidence_ledger":
            continue
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(_safe_mapping(item))
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        if _is_sensitive_key(key_text):
            continue
        safe = _safe_value(item)
        if safe is not None:
            out[key_text] = safe
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value)


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").casefold()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _clean_text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def _clean_token(value: Any) -> str:
    return _clean_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")


def _normalize_url(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return text.casefold().rstrip("/")
    return urlunparse(
        ("https", host, (parsed.path or "").rstrip("/"), "", parsed.query, "")
    ).casefold()


__all__ = [
    "ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_SCHEMA_VERSION",
    "ALLOCATION_CANDIDATE_SELECTION_ACTIVATION_TRACE_KEY",
    "allocation_candidate_selection_activation_payload",
    "build_allocation_candidate_selection_activation_projection",
    "build_allocation_candidate_selection_activation_trace",
]
