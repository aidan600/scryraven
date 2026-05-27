"""Sanitized L1 validation packet for source-class recovery diagnostics.

This module is pure/offline telemetry construction. It does not retrieve,
route providers, choose search depth, alter prompts, rank sources, persist data,
or affect controller authority.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from core.controller_action_envelope import (
    CONTROLLER_ACTION_ENVELOPE_SCHEMA_VERSION,
    RECOVER_MISSING_SOURCE_CLASS,
    ControllerActionSideEffectClass,
    ControllerActionStatus,
    get_controller_action_descriptor,
)

SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION = (
    "source_class_recovery_validation_l1"
)
SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY = "source_class_recovery_validation_l1"

SOURCE_CLASS_RECOVERY_BOTTLENECK_STATUSES = (
    "not_triggered",
    "triggered_no_candidates",
    "candidates_not_accepted",
    "accepted_not_visible",
    "visible_not_final_cited",
    "satisfied",
    "unknown",
)

_SOURCE_CLASS_RECOVERY_PROVIDER_ROLE = "source_class_recovery"
_MAX_QUERY_PREVIEWS = 2
_MAX_QUERY_PREVIEW_CHARS = 180
_MAX_TEXT_CHARS = 160
_MAX_PROVIDER_ATTEMPTS = 8
_SAFE_SOURCE_CLASS_KEYS = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
    "primary_source_documents",
    "archival_primary_text",
    "historical_legal_text",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
)
_QUALITY_STATUSES = (
    "official_or_primary_found",
    "secondary_only",
    "no_relevant_sources",
    "classification_mismatch",
    "promoted_but_not_final",
    "unknown",
)
_VISIBILITY_REASONS = (
    "not_evaluated",
    "reserved_append",
    "reserved_replace",
    "source_class_recovery_not_used",
    "no_recovered_sources",
    "missing_source_class_unavailable",
    "already_visible",
    "not_strong_source_class",
    "secondary_only",
    "source_class_mismatch",
    "historical_or_archival_not_current",
    "reservation_limit_zero",
    "final_evidence_cap_no_replaceable_source",
    "final_evidence_cap_no_room",
)
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "db_row",
    "full_trace",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)
_DOMAIN_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or any(
        marker in normalized for marker in _SENSITIVE_KEY_MARKERS
    )


def _redact_sensitive_text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def _bounded_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _optional_bounded_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _bool_or_false(value: Any) -> bool:
    return value is True


def _safe_list(
    value: Any,
    *,
    allowed: Sequence[str] | None = None,
    limit: int = 20,
    text_limit: int = _MAX_TEXT_CHARS,
) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    allowed_set = set(allowed or ())
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = _redact_sensitive_text(item, limit=text_limit)
        if not clean:
            continue
        if allowed is not None and clean not in allowed_set:
            continue
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
        if len(out) >= limit:
            break
    return out


def _query_previews(trace: Mapping[str, Any]) -> list[str]:
    queries = trace.get("active_source_class_recovery_queries")
    if not queries:
        queries = trace.get("source_class_recovery_queries")
    return _safe_list(
        queries,
        limit=_MAX_QUERY_PREVIEWS,
        text_limit=_MAX_QUERY_PREVIEW_CHARS,
    )


def _safe_count_map(
    value: Any,
    *,
    allowed: Sequence[str] | None = None,
) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    allowed_set = set(allowed or ())
    out: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        if _is_sensitive_key(raw_key):
            continue
        key = _redact_sensitive_text(raw_key, limit=80)
        if not key:
            continue
        if allowed is not None and key not in allowed_set:
            continue
        count = _bounded_int(raw_count)
        if count > 0:
            out[key] = count
    return dict(sorted(out.items()))


def _normalize_domain(value: Any) -> str:
    domain = _redact_sensitive_text(value, limit=120).casefold()
    if not domain:
        return ""
    domain = re.sub(r"^https?://", "", domain).split("/", 1)[0].rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if not _DOMAIN_PATTERN.fullmatch(domain):
        return ""
    return domain if "." in domain else ""


def _domain_constraints(trace: Mapping[str, Any]) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for item in trace.get("source_class_recovery_official_domains") or []:
        domain = _normalize_domain(item)
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains


def _jurisdiction_constraints(domains: Sequence[str]) -> list[str]:
    jurisdictions: list[str] = []

    def add(value: str) -> None:
        if value not in jurisdictions:
            jurisdictions.append(value)

    for domain in domains:
        if domain in {
            "federalregister.gov",
            "ecfr.gov",
            "govinfo.gov",
            "regulations.gov",
            "congress.gov",
        } or domain.endswith(".gov"):
            add("us")
        elif domain == "eur-lex.europa.eu" or domain.endswith(".europa.eu"):
            add("eu")
        elif domain in {"legislation.gov.uk", "ofcom.org.uk"} or domain.endswith(
            ".gov.uk"
        ):
            add("uk")
    return jurisdictions


def _safe_provider_attempts(trace: Mapping[str, Any]) -> list[dict[str, Any]]:
    attempts = trace.get("provider_diagnostics")
    if not isinstance(attempts, list):
        return []
    out: list[dict[str, Any]] = []
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            continue
        if str(attempt.get("provider_role") or "") != _SOURCE_CLASS_RECOVERY_PROVIDER_ROLE:
            continue
        clean = {
            "provider": _redact_sensitive_text(attempt.get("provider"), limit=80)
            or "unknown",
            "provider_role": _SOURCE_CLASS_RECOVERY_PROVIDER_ROLE,
            "depth": (
                _redact_sensitive_text(attempt.get("depth"), limit=80)
                if attempt.get("depth") is not None
                else None
            ),
            "max_results": _optional_bounded_int(attempt.get("max_results")),
            "query_count": _bounded_int(attempt.get("query_count")),
            "success": attempt.get("success") is not False,
            "failure_type": (
                _redact_sensitive_text(attempt.get("failure_type"), limit=120)
                if attempt.get("failure_type")
                else None
            ),
            "result_count": _bounded_int(attempt.get("result_count")),
            "new_url_count": _bounded_int(attempt.get("new_url_count")),
            "accepted_url_count": _bounded_int(attempt.get("accepted_url_count")),
            "logical_attempt_count": _bounded_int(
                attempt.get("logical_attempt_count")
            )
            or 1,
        }
        out.append(clean)
        if len(out) >= _MAX_PROVIDER_ATTEMPTS:
            break
    return out


def _provider_attempt_totals(
    attempts: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    return {
        "attempt_count": sum(_bounded_int(item.get("logical_attempt_count")) or 1 for item in attempts),
        "result_count": sum(_bounded_int(item.get("result_count")) for item in attempts),
        "new_url_count": sum(_bounded_int(item.get("new_url_count")) for item in attempts),
        "accepted_url_count": sum(_bounded_int(item.get("accepted_url_count")) for item in attempts),
    }


def _unavailable_source_class_counts() -> dict[str, int | None]:
    return {
        "official_current_rules": None,
        "legal_or_regulatory_text": None,
        "primary_source_documents": None,
        "archival_primary_text": None,
        "current_primary_or_official_proxy": None,
    }


def _source_class_counts_from_trace(
    trace: Mapping[str, Any],
    *,
    missing_default: int | None = None,
) -> dict[str, int | None]:
    official = _optional_bounded_int(trace.get("final_official_source_count"))
    legal = _optional_bounded_int(trace.get("final_legal_or_regulatory_source_count"))
    primary = _optional_bounded_int(trace.get("final_primary_source_count"))
    archival = _optional_bounded_int(trace.get("final_archival_source_count"))
    if official is None:
        official = missing_default
    if legal is None:
        legal = missing_default
    if primary is None:
        primary = missing_default
    if archival is None:
        archival = missing_default
    current_primary_direct = _optional_bounded_int(
        trace.get("final_current_primary_or_official_source_count")
    )
    current_primary_proxy: int | None = current_primary_direct
    if current_primary_proxy is None and any(
        item is not None for item in (official, legal, primary)
    ):
        current_primary_proxy = max(official or 0, legal or 0, primary or 0)
    if current_primary_proxy is None:
        current_primary_proxy = missing_default
    return {
        "official_current_rules": official,
        "legal_or_regulatory_text": legal,
        "primary_source_documents": primary,
        "archival_primary_text": archival,
        "current_primary_or_official_proxy": current_primary_proxy,
    }


def _source_class_counts_from_mapping(
    counts: Mapping[str, Any] | None,
) -> dict[str, int | None]:
    if not isinstance(counts, Mapping):
        return _unavailable_source_class_counts()
    official = _optional_bounded_int(counts.get("official_current_rules"))
    legal = _optional_bounded_int(counts.get("legal_or_regulatory_text"))
    primary = _optional_bounded_int(counts.get("primary_source_documents"))
    archival = _optional_bounded_int(counts.get("archival_primary_text"))
    return {
        "official_current_rules": official,
        "legal_or_regulatory_text": legal,
        "primary_source_documents": primary,
        "archival_primary_text": archival,
        "current_primary_or_official_proxy": max(
            official or 0,
            legal or 0,
            primary or 0,
        )
        if any(item is not None for item in (official, legal, primary))
        else None,
    }


def _count_sum(counts: Mapping[str, int | None]) -> int:
    return sum(int(value or 0) for value in counts.values())


def _action_status(
    *,
    considered: bool,
    eligible: bool,
    skip_reason: str | None,
) -> str:
    if eligible:
        return ControllerActionStatus.APPROVED.value
    if not considered or skip_reason in {
        "not_evaluated",
        "not_recommended",
        "no_missing_expected_source_class",
    }:
        return ControllerActionStatus.SKIPPED.value
    return ControllerActionStatus.BLOCKED.value


def _quality_status(value: Any) -> str:
    status = _redact_sensitive_text(value, limit=80)
    return status if status in set(_QUALITY_STATUSES) else "unknown"


def _visibility_decision(trace: Mapping[str, Any]) -> dict[str, Any]:
    reason = _redact_sensitive_text(trace.get("recovered_visibility_reason"), limit=80)
    if reason not in set(_VISIBILITY_REASONS):
        reason = "unknown" if reason else "not_evaluated"
    return {
        "considered": _bool_or_false(trace.get("recovered_visibility_considered")),
        "eligible": _bool_or_false(trace.get("recovered_visibility_eligible")),
        "used": _bool_or_false(trace.get("recovered_visibility_used")),
        "reason": reason,
        "reserved_count": _bounded_int(
            trace.get("recovered_visibility_reserved_count")
        ),
        "drop_reason": _redact_sensitive_text(
            trace.get("recovered_visibility_drop_reason"),
            limit=80,
        )
        or None,
        "source_fit_status": _redact_sensitive_text(
            trace.get("recovered_visibility_source_fit_status"),
            limit=80,
        )
        or None,
        "source_fit_candidate_count": _bounded_int(
            trace.get("recovered_visibility_source_fit_candidate_count")
        ),
        "source_fit_selected_count": _bounded_int(
            trace.get("recovered_visibility_source_fit_selected_count")
        ),
        "source_fit_rejection_reasons": _safe_list(
            trace.get("recovered_visibility_source_fit_rejection_reasons"),
            limit=8,
            text_limit=80,
        ),
    }


def _bottleneck_status(
    *,
    considered: bool,
    recommended: bool,
    eligible: bool,
    used: bool,
    active_result_count: int,
    provider_totals: Mapping[str, int],
    accepted_url_count: int,
    recovered_quality_count: int,
    recovered_promoted_count: int,
    visibility: Mapping[str, Any],
    final_cited_counts_available: bool,
    final_cited_counts: Mapping[str, int | None],
    quality_status: str,
) -> str:
    if final_cited_counts_available and _count_sum(final_cited_counts) > 0:
        return "satisfied"
    if not considered or not recommended:
        return "not_triggered"
    if not eligible:
        return "unknown"
    if used and active_result_count <= 0 and provider_totals.get("result_count", 0) <= 0:
        return "triggered_no_candidates"
    if (
        used
        and accepted_url_count <= 0
        and provider_totals.get("result_count", 0) > 0
    ):
        return "candidates_not_accepted"
    if used and accepted_url_count > 0 and visibility.get("used") is not True:
        return "accepted_not_visible"
    visible = (
        visibility.get("used") is True
        or recovered_promoted_count > 0
        or quality_status == "promoted_but_not_final"
    )
    if (
        used
        and visible
        and final_cited_counts_available
        and _count_sum(final_cited_counts) == 0
    ):
        return "visible_not_final_cited"
    if used and recovered_quality_count > 0 and not final_cited_counts_available:
        return "unknown"
    return "unknown"


def build_source_class_recovery_validation_packet(
    trace: Mapping[str, Any] | None,
    *,
    evidence_bundle_source_class_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact validation-visible source-class recovery packet."""
    source = trace if isinstance(trace, Mapping) else {}
    descriptor = get_controller_action_descriptor(RECOVER_MISSING_SOURCE_CLASS)
    considered = _bool_or_false(
        source.get("active_source_class_recovery_considered")
    )
    eligible = _bool_or_false(source.get("active_source_class_recovery_eligible"))
    used = _bool_or_false(source.get("active_source_class_recovery_used"))
    recommended = _bool_or_false(source.get("source_class_recovery_recommended")) or (
        bool(source.get("active_source_class_recovery_missing_classes"))
        and considered
    )
    skip_reason = (
        _redact_sensitive_text(
            source.get("active_source_class_recovery_skip_reason"),
            limit=80,
        )
        or None
    )
    reason = (
        _redact_sensitive_text(
            source.get("active_source_class_recovery_reason")
            or source.get("source_class_recovery_reason"),
            limit=120,
        )
        or None
    )
    blockers = _safe_list(
        source.get("active_source_class_recovery_blockers"),
        limit=12,
        text_limit=80,
    )
    missing_classes = _safe_list(
        source.get("active_source_class_recovery_missing_classes")
        or source.get("missing_expected_source_classes")
        or source.get("source_class_gap_candidates"),
        allowed=_SAFE_SOURCE_CLASS_KEYS,
        limit=12,
    )
    domains = _domain_constraints(source)
    provider_attempts = _safe_provider_attempts(source)
    provider_totals = _provider_attempt_totals(provider_attempts)
    recovered_tier_counts = _safe_count_map(
        source.get("recovered_source_tier_counts")
    )
    recovered_source_class_counts = _safe_count_map(
        source.get("recovered_source_class_counts"),
        allowed=_SAFE_SOURCE_CLASS_KEYS,
    )
    accepted_url_count = _bounded_int(source.get("recovered_accepted_url_count"))
    if accepted_url_count <= 0:
        accepted_url_count = provider_totals.get("accepted_url_count", 0)
    quality_status = _quality_status(source.get("recovery_source_quality_status"))
    visibility = _visibility_decision(source)
    final_answer_source_ids = source.get("final_answer_source_ids_used")
    final_cited_counts_available = (
        "final_answer_source_ids_used" in source
        and isinstance(final_answer_source_ids, (list, tuple, set))
    )
    final_cited_counts = (
        _source_class_counts_from_trace(source, missing_default=0)
        if final_cited_counts_available
        else _unavailable_source_class_counts()
    )
    evidence_bundle_counts = _source_class_counts_from_mapping(
        evidence_bundle_source_class_counts
    )
    action_status = _action_status(
        considered=considered,
        eligible=eligible,
        skip_reason=skip_reason,
    )
    side_effect_class = (
        descriptor.side_effect_class.value
        if action_status == ControllerActionStatus.APPROVED.value
        else ControllerActionSideEffectClass.NONE.value
    )

    bottleneck = _bottleneck_status(
        considered=considered,
        recommended=recommended,
        eligible=eligible,
        used=used,
        active_result_count=_bounded_int(
            source.get("active_source_class_recovery_result_count")
        ),
        provider_totals=provider_totals,
        accepted_url_count=accepted_url_count,
        recovered_quality_count=_bounded_int(
            source.get("recovered_official_or_primary_count")
        ),
        recovered_promoted_count=_bounded_int(
            source.get("recovered_promoted_source_count")
        ),
        visibility=visibility,
        final_cited_counts_available=final_cited_counts_available,
        final_cited_counts=final_cited_counts,
        quality_status=quality_status,
    )

    return {
        "schema_version": SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION,
        "diagnostic_only": True,
        "sanitized": True,
        "ag25_action": {
            "envelope_schema_version": CONTROLLER_ACTION_ENVELOPE_SCHEMA_VERSION,
            "name": RECOVER_MISSING_SOURCE_CLASS,
            "status": action_status,
            "authority": descriptor.authority.value,
            "side_effect_class": side_effect_class,
            "handoff_boundary": descriptor.handoff_boundary.value,
            "executor": (
                descriptor.executor
                if action_status == ControllerActionStatus.APPROVED.value
                else None
            ),
        },
        "recovery_considered": considered,
        "recovery_recommended": recommended,
        "recovery_eligible": eligible,
        "recovery_used": used,
        "trigger_reason": reason,
        "skip_reason": skip_reason,
        "blockers": blockers,
        "missing_source_classes": missing_classes,
        "recovery_query_previews": _query_previews(source),
        "official_domain_constraints": domains,
        "jurisdiction_constraints": _jurisdiction_constraints(domains),
        "domain_constraint_source": (
            _redact_sensitive_text(
                source.get("source_class_recovery_domain_constraint_source"),
                limit=80,
            )
            or None
        ),
        "provider_attempts": provider_attempts,
        "provider_attempt_totals": provider_totals,
        "active_result_count": _bounded_int(
            source.get("active_source_class_recovery_result_count")
        ),
        "active_new_url_count": _bounded_int(
            source.get("active_source_class_recovery_new_url_count")
        ),
        "accepted_url_count": accepted_url_count,
        "recovered_source_tier_counts": recovered_tier_counts,
        "recovered_source_class_counts": recovered_source_class_counts,
        "recovered_official_or_primary_count": _bounded_int(
            source.get("recovered_official_or_primary_count")
        ),
        "recovered_promoted_source_count": _bounded_int(
            source.get("recovered_promoted_source_count")
        ),
        "recovery_source_quality_status": quality_status,
        "recovered_visibility_decision": visibility,
        "evidence_bundle_official_legal_current_primary_counts": (
            evidence_bundle_counts
        ),
        "final_cited_counts_available": final_cited_counts_available,
        "final_cited_official_legal_current_primary_counts": final_cited_counts,
        "recovery_bottleneck_status": bottleneck,
        "blind_spots": [
            "current_primary_or_official uses a source-class proxy count unless a direct field is present",
            "final cited counts require parseable final answer citation source ids",
            "provider candidate counts are limited to existing provider diagnostics fields",
        ],
    }


__all__ = [
    "SOURCE_CLASS_RECOVERY_BOTTLENECK_STATUSES",
    "SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION",
    "SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY",
    "build_source_class_recovery_validation_packet",
]
