"""AG-50E official/canonical recovery candidate-acquisition trace.

This helper consumes already-sanitized source-class recovery lifecycle fields
and provider diagnostics. It does not call providers, route providers, choose
depth, rank/filter sources, classify returned sources, alter prompts, or affect
final-answer behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_SCHEMA_VERSION = (
    "official_canonical_recovery_candidate_acquisition_ag50e_v1"
)

UNKNOWN = "unknown"
SOURCE_CLASS_RECOVERY_PROVIDER_ROLE = "source_class_recovery"

_MAX_QUERY_PREVIEWS = 3
_MAX_LIST_ITEMS = 8
_MAX_QUERY_CHARS = 140
_MAX_TEXT_CHARS = 120
_OFFICIAL_OR_CANONICAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_OR_CANONICAL_TIERS = frozenset({"official", "primary", "canonical"})
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
_HARD_BLOCKERS = frozenset(
    {
        "blocked_by_conflict_resolution",
        "blocked_by_corpus_weak",
        "blocked_by_provider_policy_change_required",
        "blocked_by_retrieve_to_anchor_recommendation",
        "blocked_by_search_depth_escalation_required",
        "blocked_by_terminal_stop",
        "blocked_by_weak_corpus_recovery",
        "budget_hard_exhausted",
        "conflict_resolution_owns_path",
        "terminal_stop_approved",
        "weak_corpus_recovery_owns_path",
    }
)


def official_canonical_recovery_candidate_acquisition_defaults() -> dict[str, Any]:
    """Return AG-50E candidate-acquisition default trace fields."""
    return {
        "candidate_acquisition_schema_version": (
            OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_SCHEMA_VERSION
        ),
        "candidate_acquisition_considered": False,
        "candidate_acquisition_eligible": False,
        "candidate_acquisition_used": False,
        "candidate_acquisition_skip_reason": "not_evaluated",
        "candidate_acquisition_blockers": ["not_evaluated"],
        "acquisition_provider_role": UNKNOWN,
        "acquisition_query_count": 0,
        "acquisition_query_previews": [],
        "acquisition_attempted": False,
        "candidate_acquisition_provider_attempt_count": 0,
        "candidate_acquisition_provider_success_count": 0,
        "candidate_acquisition_provider_failure_count": 0,
        "candidate_acquisition_provider_result_count": 0,
        "candidate_acquisition_provider_accepted_url_count": 0,
        "candidate_acquisition_provider_new_source_count": UNKNOWN,
        "candidate_acquisition_result_status": UNKNOWN,
        "candidate_visibility_export_status": UNKNOWN,
        "candidate_visibility_blocker_kind": UNKNOWN,
        "recovered_result_count": UNKNOWN,
        "accepted_url_count": UNKNOWN,
        "candidate_return_status": UNKNOWN,
        "zero_candidate_blocker": UNKNOWN,
        "zero_candidate_blocker_kind": UNKNOWN,
        "official_canonical_candidate_visible": UNKNOWN,
        "likely_next_failure_layer": UNKNOWN,
        "behavior_changed": False,
    }


def build_official_canonical_recovery_candidate_acquisition_trace(
    *,
    lifecycle_trace: Mapping[str, Any] | None,
    provider_diagnostics: Iterable[Mapping[str, Any]] | None = None,
    execution_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build compact candidate-acquisition fields for the admitted recovery slot."""
    lifecycle = _safe_mapping(lifecycle_trace)
    execution = _safe_mapping(execution_result)
    provider_role = _optional_text(
        lifecycle.get("active_source_class_recovery_provider_role")
    )
    queries = _safe_list(
        lifecycle.get("active_source_class_recovery_queries"),
        limit=_MAX_QUERY_PREVIEWS,
        text_limit=_MAX_QUERY_CHARS,
    )
    blockers = _string_list(lifecycle.get("active_source_class_recovery_blockers"))
    hard_blockers = [item for item in blockers if item in _HARD_BLOCKERS]
    considered = bool(
        lifecycle.get("active_source_class_recovery_official_canonical_admitted")
        or lifecycle.get("active_source_class_recovery_eligible")
        or provider_role == SOURCE_CLASS_RECOVERY_PROVIDER_ROLE
    )
    eligible = bool(
        considered
        and lifecycle.get("active_source_class_recovery_eligible") is True
        and provider_role == SOURCE_CLASS_RECOVERY_PROVIDER_ROLE
        and queries
        and not hard_blockers
    )
    attempted = bool(
        lifecycle.get("active_source_class_recovery_execution_attempted") is True
        or lifecycle.get("active_source_class_recovery_used") is True
        or execution.get("attempted") is True
    )
    used = bool(eligible and attempted)

    attempts = _provider_attempts(provider_diagnostics)
    provider_attempt_count = len(attempts)
    provider_success_count = sum(1 for attempt in attempts if attempt.get("success") is True)
    provider_failure_count = sum(1 for attempt in attempts if attempt.get("success") is False)
    provider_result_count = sum(_non_negative_int(attempt.get("result_count")) for attempt in attempts)
    provider_accepted_url_count = sum(
        _non_negative_int(attempt.get("accepted_url_count")) for attempt in attempts
    )
    provider_new_source_count = _optional_sum(
        attempt.get("new_source_count") for attempt in attempts
    )

    recovered_result_count = _first_known_int(
        lifecycle.get("active_source_class_recovery_result_count"),
        lifecycle.get("recovered_result_count"),
        execution.get("result_count"),
    )
    accepted_url_count = _first_known_int(
        lifecycle.get("recovered_accepted_url_count"),
        lifecycle.get("accepted_url_count"),
        provider_accepted_url_count if attempts else UNKNOWN,
    )
    class_counts = _safe_count_map(
        lifecycle.get("recovered_source_class_counts"),
        allowed=_OFFICIAL_OR_CANONICAL_CLASSES,
    )
    tier_counts = _safe_count_map(
        lifecycle.get("recovered_source_tier_counts"),
        allowed=_OFFICIAL_OR_CANONICAL_TIERS,
    )
    official_candidate_visible = _official_candidate_visible(
        recovered_result_count=recovered_result_count,
        class_counts=class_counts,
        tier_counts=tier_counts,
    )
    candidate_acquisition_result_status = _candidate_acquisition_result_status(
        attempted=attempted,
        provider_attempt_count=provider_attempt_count,
        provider_failure_count=provider_failure_count,
        provider_success_count=provider_success_count,
        provider_result_count=provider_result_count,
    )
    candidate_visibility_export_status = _candidate_visibility_export_status(
        attempted=attempted,
        recovered_result_count=recovered_result_count,
        accepted_url_count=accepted_url_count,
        official_candidate_visible=official_candidate_visible,
        candidate_acquisition_result_status=candidate_acquisition_result_status,
    )
    candidate_visibility_blocker_kind = _candidate_visibility_blocker_kind(
        candidate_visibility_export_status
    )
    candidate_return_status = _candidate_return_status(
        attempted=attempted,
        recovered_result_count=recovered_result_count,
        candidate_visibility_export_status=candidate_visibility_export_status,
    )
    zero_blocker_kind = _zero_candidate_blocker_kind(
        considered=considered,
        eligible=eligible,
        attempted=attempted,
        provider_role=provider_role,
        queries=queries,
        hard_blockers=hard_blockers,
        provider_attempt_count=provider_attempt_count,
        provider_failure_count=provider_failure_count,
        provider_success_count=provider_success_count,
        provider_result_count=provider_result_count,
        recovered_result_count=recovered_result_count,
    )

    return {
        "candidate_acquisition_schema_version": (
            OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_SCHEMA_VERSION
        ),
        "candidate_acquisition_considered": considered,
        "candidate_acquisition_eligible": eligible,
        "candidate_acquisition_used": used,
        "candidate_acquisition_skip_reason": _skip_reason(
            considered=considered,
            eligible=eligible,
            attempted=attempted,
            provider_role=provider_role,
            queries=queries,
            hard_blockers=hard_blockers,
        ),
        "candidate_acquisition_blockers": _blockers(
            provider_role=provider_role,
            queries=queries,
            hard_blockers=hard_blockers,
            zero_blocker_kind=zero_blocker_kind,
            candidate_visibility_blocker_kind=candidate_visibility_blocker_kind,
        ),
        "acquisition_provider_role": provider_role,
        "acquisition_query_count": len(queries),
        "acquisition_query_previews": queries,
        "acquisition_attempted": attempted,
        "candidate_acquisition_provider_attempt_count": provider_attempt_count,
        "candidate_acquisition_provider_success_count": provider_success_count,
        "candidate_acquisition_provider_failure_count": provider_failure_count,
        "candidate_acquisition_provider_result_count": provider_result_count,
        "candidate_acquisition_provider_accepted_url_count": (
            provider_accepted_url_count
        ),
        "candidate_acquisition_provider_new_source_count": (
            provider_new_source_count
        ),
        "candidate_acquisition_result_status": candidate_acquisition_result_status,
        "candidate_visibility_export_status": candidate_visibility_export_status,
        "candidate_visibility_blocker_kind": candidate_visibility_blocker_kind,
        "recovered_result_count": recovered_result_count,
        "accepted_url_count": accepted_url_count,
        "candidate_return_status": candidate_return_status,
        "zero_candidate_blocker": (
            zero_blocker_kind if zero_blocker_kind != UNKNOWN else UNKNOWN
        ),
        "zero_candidate_blocker_kind": zero_blocker_kind,
        "official_canonical_candidate_visible": official_candidate_visible,
        "likely_next_failure_layer": _likely_next_failure_layer(
            attempted=attempted,
            recovered_result_count=recovered_result_count,
            official_candidate_visible=official_candidate_visible,
            zero_blocker_kind=zero_blocker_kind,
            candidate_visibility_export_status=candidate_visibility_export_status,
        ),
        "behavior_changed": used,
    }


def _skip_reason(
    *,
    considered: bool,
    eligible: bool,
    attempted: bool,
    provider_role: str,
    queries: list[str],
    hard_blockers: list[str],
) -> str | None:
    if not considered:
        return "not_official_canonical_recovery_slot"
    if provider_role != SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
        return "provider_role_unavailable"
    if not queries:
        return "no_query_available"
    if hard_blockers:
        return "hard_blocker_present"
    if not eligible:
        return "not_eligible"
    if not attempted:
        return "execution_not_attempted"
    return None


def _blockers(
    *,
    provider_role: str,
    queries: list[str],
    hard_blockers: list[str],
    zero_blocker_kind: str,
    candidate_visibility_blocker_kind: str = UNKNOWN,
) -> list[str]:
    blockers = list(hard_blockers)
    if provider_role != SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
        _append_one(blockers, "provider_role_unavailable")
    if not queries:
        _append_one(blockers, "no_query_available")
    if zero_blocker_kind != UNKNOWN:
        _append_one(blockers, zero_blocker_kind)
    if candidate_visibility_blocker_kind != UNKNOWN:
        _append_one(blockers, candidate_visibility_blocker_kind)
    return blockers


def _candidate_return_status(
    *,
    attempted: bool,
    recovered_result_count: Any,
    candidate_visibility_export_status: str,
) -> str:
    if not attempted:
        return "not_attempted"
    if candidate_visibility_export_status == "candidate_visibility_not_exported":
        return "candidate_visibility_not_exported"
    if candidate_visibility_export_status == "acquisition_result_not_observable":
        return "candidate_return_unknown"
    if recovered_result_count == UNKNOWN:
        return UNKNOWN
    if _is_zero(recovered_result_count):
        return "zero_candidates"
    if _positive_int(recovered_result_count):
        return "candidates_returned"
    return UNKNOWN


def _candidate_acquisition_result_status(
    *,
    attempted: bool,
    provider_attempt_count: int,
    provider_failure_count: int,
    provider_success_count: int,
    provider_result_count: int,
) -> str:
    if not attempted:
        return "not_attempted"
    if provider_attempt_count <= 0:
        return "provider_execution_unavailable"
    if provider_success_count <= 0 and provider_failure_count > 0:
        return "provider_execution_unavailable"
    if provider_result_count > 0:
        return "provider_results_returned"
    if provider_result_count == 0:
        return "provider_returned_zero_results"
    return UNKNOWN


def _candidate_visibility_export_status(
    *,
    attempted: bool,
    recovered_result_count: Any,
    accepted_url_count: Any,
    official_candidate_visible: Any,
    candidate_acquisition_result_status: str,
) -> str:
    if not attempted:
        return "not_attempted"
    if _positive_int(recovered_result_count) or official_candidate_visible is True:
        return "visible"
    if (
        candidate_acquisition_result_status == "provider_results_returned"
        and _is_zero(recovered_result_count)
    ):
        if not _positive_int(accepted_url_count):
            return "candidate_visibility_not_exported"
        return "acquisition_result_not_observable"
    if recovered_result_count == UNKNOWN:
        return UNKNOWN
    if _is_zero(recovered_result_count):
        return "not_visible"
    return UNKNOWN


def _candidate_visibility_blocker_kind(
    candidate_visibility_export_status: str,
) -> str:
    if candidate_visibility_export_status in {
        "candidate_visibility_not_exported",
        "acquisition_result_not_observable",
    }:
        return candidate_visibility_export_status
    return UNKNOWN


def _zero_candidate_blocker_kind(
    *,
    considered: bool,
    eligible: bool,
    attempted: bool,
    provider_role: str,
    queries: list[str],
    hard_blockers: list[str],
    provider_attempt_count: int,
    provider_failure_count: int,
    provider_success_count: int,
    provider_result_count: int,
    recovered_result_count: Any,
) -> str:
    if recovered_result_count == UNKNOWN or _positive_int(recovered_result_count):
        return UNKNOWN
    if not considered or not eligible or not attempted:
        return UNKNOWN
    if hard_blockers:
        return "hard_blocker_present"
    if provider_role != SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
        return "provider_role_unavailable"
    if not queries:
        return "no_query_available"
    if provider_attempt_count <= 0:
        return "provider_execution_unavailable"
    if provider_success_count <= 0 and provider_failure_count > 0:
        return "provider_execution_unavailable"
    if provider_result_count <= 0:
        return "provider_returned_zero_results"
    return UNKNOWN


def _likely_next_failure_layer(
    *,
    attempted: bool,
    recovered_result_count: Any,
    official_candidate_visible: Any,
    zero_blocker_kind: str,
    candidate_visibility_export_status: str,
) -> str:
    if not attempted:
        return "execution_not_attempted"
    if recovered_result_count == UNKNOWN:
        return "candidate_return_unknown"
    if candidate_visibility_export_status == "candidate_visibility_not_exported":
        return "execution_attempted_candidate_visibility_not_exported"
    if candidate_visibility_export_status == "acquisition_result_not_observable":
        return "execution_attempted_acquisition_result_not_observable"
    if _is_zero(recovered_result_count):
        if zero_blocker_kind != UNKNOWN:
            return f"execution_attempted_zero_candidates:{zero_blocker_kind}"
        return "execution_attempted_zero_candidates"
    if official_candidate_visible is True:
        return "official_canonical_candidate_visible"
    if official_candidate_visible is False:
        return "candidate_returned_no_official_canonical_visible"
    return "candidate_returned_visibility_unknown"


def _official_candidate_visible(
    *,
    recovered_result_count: Any,
    class_counts: Mapping[str, int] | str,
    tier_counts: Mapping[str, int] | str,
) -> bool | str:
    if isinstance(class_counts, Mapping) and sum(int(v or 0) for v in class_counts.values()) > 0:
        return True
    if isinstance(tier_counts, Mapping) and sum(int(v or 0) for v in tier_counts.values()) > 0:
        return True
    if _positive_int(recovered_result_count):
        return False
    return UNKNOWN


def _provider_attempts(
    provider_diagnostics: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt in provider_diagnostics or ():
        if not isinstance(attempt, Mapping):
            continue
        if str(attempt.get("provider_role") or "") != SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
            continue
        attempts.append(_safe_mapping(attempt))
        if len(attempts) >= _MAX_LIST_ITEMS:
            break
    return attempts


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
        return _clean_text(value, limit=240)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    return _clean_text(value, limit=240)


def _safe_list(
    value: Any,
    *,
    limit: int,
    text_limit: int,
) -> list[str]:
    out: list[str] = []
    for item in _iter_values(value):
        text = _clean_text(item, limit=text_limit)
        if text:
            _append_one(out, text)
        if len(out) >= limit:
            break
    return out


def _string_list(value: Any) -> list[str]:
    return _safe_list(value, limit=_MAX_LIST_ITEMS, text_limit=_MAX_TEXT_CHARS)


def _safe_count_map(value: Any, *, allowed: frozenset[str]) -> dict[str, int] | str:
    if not isinstance(value, Mapping):
        return UNKNOWN
    out: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        if _is_sensitive_key(raw_key):
            continue
        key = _clean_token(raw_key)
        if key and key in allowed:
            parsed = _optional_int(raw_count)
            if parsed != UNKNOWN:
                out[key] = parsed
    return dict(sorted(out.items()))


def _first_known_int(*values: Any) -> int | str:
    for value in values:
        parsed = _optional_int(value)
        if parsed != UNKNOWN:
            return parsed
    return UNKNOWN


def _optional_sum(values: Iterable[Any]) -> int | str:
    total = 0
    seen = False
    for value in values:
        parsed = _optional_int(value)
        if parsed == UNKNOWN:
            continue
        total += parsed
        seen = True
    return total if seen else UNKNOWN


def _optional_int(value: Any) -> int | str:
    if value is None or isinstance(value, bool) or value == UNKNOWN:
        return UNKNOWN
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return UNKNOWN


def _non_negative_int(value: Any) -> int:
    parsed = _optional_int(value)
    return 0 if parsed == UNKNOWN else parsed


def _is_zero(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _optional_text(value: Any) -> str:
    text = _clean_text(value, limit=_MAX_TEXT_CHARS)
    return text or UNKNOWN


def _iter_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.values())
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _append_one(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


def _clean_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
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


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or any(
        marker in normalized for marker in _SENSITIVE_KEY_MARKERS
    )


__all__ = [
    "OFFICIAL_CANONICAL_RECOVERY_CANDIDATE_ACQUISITION_SCHEMA_VERSION",
    "SOURCE_CLASS_RECOVERY_PROVIDER_ROLE",
    "UNKNOWN",
    "build_official_canonical_recovery_candidate_acquisition_trace",
    "official_canonical_recovery_candidate_acquisition_defaults",
]
