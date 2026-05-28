"""AG-73D-V provider-result to represented-candidate bridge.

This module reconciles already-sanitized provider-result summaries with the
Authority Candidate Passport projection. It is passive diagnostic telemetry:
it does not retrieve, route, rank/filter, classify, fit, cite, prompt, or alter
runtime answer behavior.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.authority_candidate_passport import AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY

PROVIDER_RESULT_REPRESENTED_VISIBILITY_SCHEMA_VERSION = (
    "provider_result_represented_visibility_ag73d_v1"
)
PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY = (
    "provider_result_represented_candidate_bridge"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_LIST_ITEMS = 40
_MAX_QUERY_CHARS = 140
_MAX_TITLE_CHARS = 180
_MAX_REASON_CHARS = 160
_LOWER_TIER_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "context", "analysis"}
)
_LOWER_TIER_CLASSES = frozenset({"secondary", "secondary_only", "context"})
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
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)


def build_provider_result_represented_visibility_projection(
    *,
    runtime_trace: Mapping[str, Any] | None = None,
    provider_results: Iterable[Mapping[str, Any]] | None = None,
    passport_projection: Mapping[str, Any] | None = None,
    represented_candidates: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build bridge records for sanitized provider results."""

    trace = _safe_mapping(runtime_trace)
    results = _provider_result_records(provider_results, trace)
    passports = _passport_records(passport_projection, trace)
    represented = _represented_records(represented_candidates)
    passport_index = _records_by_identity(passports)
    represented_index = _records_by_identity(represented)

    bridge_records = [
        _bridge_record(
            provider_result=result,
            passport_index=passport_index,
            represented_index=represented_index,
        )
        for result in results
    ]
    aggregate_reconciliation = _aggregate_reconciliation(
        bridge_records=bridge_records,
        trace=trace,
    )

    return {
        "schema_version": PROVIDER_RESULT_REPRESENTED_VISIBILITY_SCHEMA_VERSION,
        "trace_key": PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
        "diagnostic_only": True,
        "sanitized": True,
        "behavior_changed": False,
        "provider_result_count": len(results),
        "represented_passport_count": len(passports),
        "bridge_record_count": len(bridge_records),
        "bridge_records": bridge_records,
        "bridge_disposition_counts": _disposition_counts(bridge_records),
        "aggregate_reconciliation": aggregate_reconciliation,
        "aggregate_reconciliation_status": aggregate_reconciliation["status"],
        "unobservable_boundary": _unobservable_boundary(
            bridge_records=bridge_records,
            aggregate_reconciliation_status=aggregate_reconciliation["status"],
        ),
        "consumer": (
            "AG-73D-V and later bounded custody validation phases that need "
            "provider-result to represented-candidate visibility."
        ),
        "decision_enabled": (
            "Determine whether sanitized provider results became represented "
            "authority candidates/passports, were not represented with durable "
            "reasons, or remain unobservable without raw/live/private data."
        ),
    }


def build_provider_result_represented_visibility_trace(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a runtime trace envelope for the passive AG-73D-V bridge."""

    return {
        "schema_version": PROVIDER_RESULT_REPRESENTED_VISIBILITY_SCHEMA_VERSION,
        "trace_mode": "passive_runtime_visibility",
        "ProviderResultRepresentedCandidateBridge": (
            build_provider_result_represented_visibility_projection(
                runtime_trace=runtime_trace
            )
        ),
    }


def _bridge_record(
    *,
    provider_result: Mapping[str, Any],
    passport_index: Mapping[str, Mapping[str, Any]],
    represented_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    provider_result_id = _provider_result_id(provider_result)
    source_url = _clean_text(
        provider_result.get("source_url")
        or provider_result.get("url")
        or provider_result.get("accepted_url"),
        limit=240,
    )
    normalized_url = _normalize_url(source_url)
    identities = _identity_keys(provider_result, normalized_url=normalized_url)
    passport = _first_identity_record(identities, passport_index)
    represented = _first_identity_record(identities, represented_index)
    lower_tier = _is_lower_tier(provider_result, passport)
    non_representation_reason = _non_representation_reason(
        provider_result,
        passport=passport,
        represented=represented,
        lower_tier=lower_tier,
    )
    disposition = _bridge_disposition(
        passport=passport,
        represented=represented,
        lower_tier=lower_tier,
        non_representation_reason=non_representation_reason,
    )

    return {
        "bridge_schema_version": PROVIDER_RESULT_REPRESENTED_VISIBILITY_SCHEMA_VERSION,
        "provider_result_id": provider_result_id,
        "provider_name": _clean_text(provider_result.get("provider_name"), limit=80)
        or _clean_text(provider_result.get("provider"), limit=80)
        or UNKNOWN,
        "provider_role": _clean_text(provider_result.get("provider_role"), limit=80)
        or UNKNOWN,
        "retrieval_pass_id": _clean_text(
            provider_result.get("retrieval_pass_id")
            or provider_result.get("retrieval_stage"),
            limit=80,
        )
        or UNKNOWN,
        "query_preview": _clean_text(
            provider_result.get("query_preview") or provider_result.get("query"),
            limit=_MAX_QUERY_CHARS,
        )
        or UNKNOWN,
        "provider_rank_or_position": _safe_position(provider_result),
        "source_url": source_url,
        "normalized_domain": _clean_text(
            provider_result.get("normalized_domain"),
            limit=120,
        )
        or _normalized_domain(source_url),
        "title": _clean_text(provider_result.get("title"), limit=_MAX_TITLE_CHARS),
        "source_tier": _clean_token(
            (passport or {}).get("source_tier") or provider_result.get("source_tier")
        )
        or UNKNOWN,
        "source_class": _clean_token(
            (passport or {}).get("source_class") or provider_result.get("source_class")
        )
        or UNKNOWN,
        "provider_returned": _bool_or_true(provider_result.get("provider_returned")),
        "represented_candidate_id": _clean_text(
            (represented or passport or {}).get("candidate_id"),
            limit=160,
        ),
        "passport_candidate_id": _clean_text((passport or {}).get("candidate_id"), limit=160),
        "represented_candidate_visible": represented is not None or passport is not None,
        "passport_visible": passport is not None,
        "bridge_disposition": disposition,
        "non_representation_reason": non_representation_reason,
        "first_missing_stage": _first_missing_stage(
            disposition=disposition,
            reason=non_representation_reason,
            passport=passport,
        ),
        "aggregate_reconciliation_status": UNKNOWN,
        "diagnostic_only": True,
        "sanitized": True,
        "behavior_changed": False,
    }


def _bridge_disposition(
    *,
    passport: Mapping[str, Any] | None,
    represented: Mapping[str, Any] | None,
    lower_tier: bool,
    non_representation_reason: str | None,
) -> str:
    if lower_tier:
        return "lower_tier_not_authority_satisfying"
    if passport is not None:
        return "represented_passport_matched"
    if represented is not None:
        return "represented_candidate_without_passport"
    if non_representation_reason:
        return "not_represented_with_reason"
    return "unobservable_without_raw_or_live_data"


def _non_representation_reason(
    provider_result: Mapping[str, Any],
    *,
    passport: Mapping[str, Any] | None,
    represented: Mapping[str, Any] | None,
    lower_tier: bool,
) -> str | None:
    if lower_tier:
        return "lower_tier_or_secondary_not_satisfying_official_current_obligation"
    if passport is not None or represented is not None:
        return None
    reason = _clean_text(
        provider_result.get("non_representation_reason")
        or provider_result.get("drop_reason")
        or provider_result.get("rejection_reason"),
        limit=_MAX_REASON_CHARS,
    )
    return reason or None


def _first_missing_stage(
    *,
    disposition: str,
    reason: str | None,
    passport: Mapping[str, Any] | None,
) -> str | None:
    passport_stage = _clean_text((passport or {}).get("first_missing_stage"), limit=80)
    if passport_stage:
        return passport_stage
    if disposition == "represented_passport_matched":
        return None
    if disposition == "represented_candidate_without_passport":
        return "passport_projection"
    if disposition == "lower_tier_not_authority_satisfying":
        return "source_class_or_tier"
    text = (reason or "").casefold()
    if "duplicate" in text:
        return "dedupe"
    if "plausible" in text or "url" in text:
        return "provider_result_acceptance"
    if disposition == "not_represented_with_reason":
        return "provider_result_acceptance"
    return "provider_result_to_representation"


def _provider_result_records(
    provider_results: Iterable[Mapping[str, Any]] | None,
    trace: Mapping[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in provider_results or ():
        if isinstance(item, Mapping):
            _append_unique(records, _safe_mapping(item))
    for attempt in _iter_mappings(trace.get("provider_diagnostics")):
        for item in _iter_mappings(attempt.get("provider_result_summaries")):
            merged = {
                "provider_name": attempt.get("provider"),
                "provider_role": attempt.get("provider_role"),
                "query_preview": attempt.get("query_preview"),
                **item,
            }
            _append_unique(records, _safe_mapping(merged))
    return records[:_MAX_LIST_ITEMS]


def _passport_records(
    passport_projection: Mapping[str, Any] | None,
    trace: Mapping[str, Any],
) -> list[dict[str, Any]]:
    projection = _safe_mapping(passport_projection) or _passport_projection(trace)
    return [
        _safe_mapping(item)
        for item in _iter_mappings(projection.get("passports"))
    ]


def _passport_projection(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("AuthorityCandidatePassportProjection")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    projection = trace.get("authority_candidate_passport_projection")
    if isinstance(projection, Mapping):
        return _safe_mapping(projection)
    return {}


def _represented_records(
    represented_candidates: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    return [
        _safe_mapping(item)
        for item in represented_candidates or ()
        if isinstance(item, Mapping)
    ]


def _aggregate_reconciliation(
    *,
    bridge_records: list[Mapping[str, Any]],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    observed_count = _first_known_int(
        trace.get("provider_result_summary_count"),
        _provider_result_summary_count(trace),
        trace.get("candidate_acquisition_provider_result_count"),
        trace.get("active_source_class_recovery_result_count"),
        trace.get("recovered_result_count"),
    )
    bridge_count = len(bridge_records)
    if observed_count == UNKNOWN:
        status = NOT_OBSERVABLE if bridge_count == 0 else "summary_count_not_observable"
        reconciled = bridge_count == 0
    elif observed_count == bridge_count:
        status = "reconciled"
        reconciled = True
    elif observed_count > bridge_count:
        status = "aggregate_provider_count_exceeds_visible_bridge_records"
        reconciled = False
    else:
        status = "bridge_records_exceed_aggregate_provider_count"
        reconciled = False
    return {
        "status": status,
        "reconciled": reconciled,
        "aggregate_provider_result_count": observed_count,
        "bridge_record_count": bridge_count,
    }


def _provider_result_summary_count(trace: Mapping[str, Any]) -> int | str:
    count = 0
    observed = False
    for attempt in _iter_mappings(trace.get("provider_diagnostics")):
        parsed = _optional_int(attempt.get("provider_result_summary_count"))
        if parsed is not None:
            count += parsed
            observed = True
    return count if observed else UNKNOWN


def _unobservable_boundary(
    *,
    bridge_records: list[Mapping[str, Any]],
    aggregate_reconciliation_status: str,
) -> str | None:
    if any(
        record.get("bridge_disposition") == "unobservable_without_raw_or_live_data"
        for record in bridge_records
    ):
        return "provider-result to represented authority candidate"
    if aggregate_reconciliation_status in {
        NOT_OBSERVABLE,
        "aggregate_provider_count_exceeds_visible_bridge_records",
    }:
        return "provider-result to represented authority candidate"
    return None


def _disposition_counts(records: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        disposition = _clean_text(record.get("bridge_disposition"), limit=80) or UNKNOWN
        counts[disposition] = counts.get(disposition, 0) + 1
    return dict(sorted(counts.items()))


def _is_lower_tier(
    provider_result: Mapping[str, Any],
    passport: Mapping[str, Any] | None,
) -> bool:
    source_tier = _clean_token((passport or {}).get("source_tier") or provider_result.get("source_tier"))
    source_class = _clean_token(
        (passport or {}).get("source_class") or provider_result.get("source_class")
    )
    satisfies = (passport or {}).get("satisfies_authority")
    return (
        source_tier in _LOWER_TIER_TIERS
        or source_class in _LOWER_TIER_CLASSES
        or (
            passport is not None
            and satisfies is False
            and source_tier in _LOWER_TIER_TIERS
        )
    )


def _records_by_identity(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        safe = _safe_mapping(record)
        source_url = _clean_text(
            safe.get("source_url") or safe.get("url") or safe.get("accepted_url"),
            limit=240,
        )
        for key in _identity_keys(safe, normalized_url=_normalize_url(source_url)):
            by_key.setdefault(key, safe)
    return by_key


def _identity_keys(
    record: Mapping[str, Any],
    *,
    normalized_url: str,
) -> set[str]:
    keys: set[str] = set()
    for key in ("candidate_id", "provider_result_id"):
        text = _clean_text(record.get(key), limit=240)
        if text:
            keys.add(f"id:{text.casefold()}")
    if normalized_url:
        keys.add(f"url:{normalized_url}")
    for key in ("source_url", "url", "accepted_url"):
        normalized = _normalize_url(record.get(key))
        if normalized:
            keys.add(f"url:{normalized}")
    return keys


def _first_identity_record(
    keys: set[str],
    records_by_identity: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for key in keys:
        record = records_by_identity.get(key)
        if record is not None:
            return record
    return None


def _append_unique(records: list[dict[str, Any]], record: dict[str, Any]) -> None:
    identity = _provider_result_id(record)
    if any(_provider_result_id(existing) == identity for existing in records):
        return
    records.append(record)


def _provider_result_id(record: Mapping[str, Any]) -> str:
    explicit = _clean_text(record.get("provider_result_id"), limit=160)
    if explicit:
        return explicit
    source_url = _clean_text(record.get("source_url") or record.get("url"), limit=240)
    query = _clean_text(record.get("query_preview") or record.get("query"), limit=80)
    provider = _clean_text(record.get("provider_name") or record.get("provider"), limit=80)
    digest = hashlib.sha1(
        "|".join((provider or "", query or "", _normalize_url(source_url))).encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    return f"provider-result-{digest}"


def _safe_position(record: Mapping[str, Any]) -> int | str:
    parsed = _optional_int(
        record.get("provider_rank_or_position")
        or record.get("rank")
        or record.get("position")
    )
    return parsed if parsed is not None else UNKNOWN


def _first_known_int(*values: Any) -> int | str:
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None:
            return parsed
    return UNKNOWN


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or value in {UNKNOWN, NOT_OBSERVABLE}:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _bool_or_true(value: Any) -> bool:
    return value if isinstance(value, bool) else True


def _iter_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


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
        return _clean_text(value, limit=240)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value, limit=240)


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").casefold()
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _clean_text(value: Any, *, limit: int) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split())
    if not text:
        return ""
    if any(pattern.search(text) for pattern in _SECRET_VALUE_PATTERNS):
        return ""
    return text[:limit]


def _clean_token(value: Any) -> str:
    text = _clean_text(value, limit=80).casefold()
    return text.replace("-", "_").replace(" ", "_")


def _normalize_url(value: Any) -> str:
    text = _clean_text(value, limit=240)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return text.casefold().rstrip("/")
    path = (parsed.path or "").rstrip("/")
    return urlunparse(("https", host, path, "", parsed.query, "")).casefold()


def _normalized_domain(value: Any) -> str:
    text = _clean_text(value, limit=240)
    if not text:
        return UNKNOWN
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or UNKNOWN


__all__ = [
    "PROVIDER_RESULT_REPRESENTED_VISIBILITY_SCHEMA_VERSION",
    "PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY",
    "build_provider_result_represented_visibility_projection",
    "build_provider_result_represented_visibility_trace",
]
