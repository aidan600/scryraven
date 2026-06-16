"""Provider-neutral official/current result-set diagnostics for AG-96I3D.

The functions in this module inspect already-acquired, provider-shaped search
results. They do not call providers, fetch pages, read environment values, or
own answer authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from core.followup_deliberation import ProviderJobKind, clean_text, clean_token

DISCOVERY_UNCONSTRAINED = "discovery_unconstrained"
SOFT_AUTHORITY_HINT = "soft_authority_hint"
HARD_CORRIDOR_DOMAIN_CONSTRAINED = "hard_corridor_domain_constrained"

OFFICIAL_CURRENT_CANDIDATE_ACQUISITION = (
    ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
)
SCOUT_BRIDGE_JOB_KINDS = frozenset(
    {
        ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        ProviderJobKind.BRIDGE_HINT_DISCOVERY.value,
    }
)

ACQUISITION_MODES = frozenset(
    {
        DISCOVERY_UNCONSTRAINED,
        SOFT_AUTHORITY_HINT,
        HARD_CORRIDOR_DOMAIN_CONSTRAINED,
    }
)

OFFICIAL_CURRENT_SOURCE_CLASSES = frozenset(
    {"official_current_rules", "official_government", "official"}
)
CURRENTNESS_FAILURE_SIGNALS = frozenset(
    {"stale", "outdated", "historical_only", "off_topic", "not_current"}
)
CURRENTNESS_POSITIVE_SIGNALS = frozenset(
    {
        "current_candidate_signal",
        "current",
        "current_verified",
        "current_official",
        "currentness_supported",
    }
)

SANITIZED_RESULT_KEYS = frozenset(
    {
        "rank",
        "url",
        "title",
        "domain",
        "source_tier",
        "source_class",
        "currentness_signal",
        "candidate_fit_status",
        "provider_name",
        "acquisition_mode",
        "rejection_or_selection_reason",
    }
)


def build_official_current_discovery_diagnostics(
    results: Iterable[Mapping[str, Any]],
    *,
    provider_name: str,
    provider_surface_role: str,
    provider_job_kind: str,
    acquisition_mode: str = DISCOVERY_UNCONSTRAINED,
    authorized_query_ref: str | None = None,
    authorized_query: str | None = None,
    domain_constraints: Iterable[str] | None = None,
    include_domains: Iterable[str] | None = None,
    authority_decision_present: bool = False,
) -> dict[str, Any]:
    """Build a sanitized, provider-neutral diagnostic packet.

    Domain constraints are diagnostic inputs only. Discovery-unconstrained mode
    marks any source-specific domain constraint invalid; hard-corridor mode
    requires the caller to pass an explicit upstream authority-decision flag.
    """

    provider_name = clean_token(provider_name, limit=120) or "unknown_provider"
    provider_job_kind = clean_token(provider_job_kind, limit=120)
    acquisition_mode = _acquisition_mode(acquisition_mode)
    domain_constraints = _clean_domain_tuple(domain_constraints)
    include_domains = _clean_domain_tuple(include_domains)
    constraint_domains = tuple(dict.fromkeys((*domain_constraints, *include_domains)))
    authority_decision_required = acquisition_mode == HARD_CORRIDOR_DOMAIN_CONSTRAINED
    domain_constraint_status = _domain_constraint_status(
        acquisition_mode=acquisition_mode,
        constraint_domains=constraint_domains,
        authority_decision_present=authority_decision_present,
    )
    invalid_domain_constraint = domain_constraint_status in {
        "invalid_unearned_domain_constraint",
        "invalid_missing_authority_decision",
    }

    sanitized_results = [
        _sanitize_result_record(
            item,
            rank=index,
            provider_name=provider_name,
            acquisition_mode=acquisition_mode,
        )
        for index, item in enumerate(results, start=1)
    ]
    for item in sanitized_results:
        item["rejection_or_selection_reason"] = _result_reason(
            item,
            provider_job_kind=provider_job_kind,
            invalid_domain_constraint=invalid_domain_constraint,
        )

    official_current_candidates = [
        item
        for item in sanitized_results
        if item["candidate_fit_status"] == "official_current_candidate_fit"
    ]
    selected = _select_candidate(
        official_current_candidates,
        provider_job_kind=provider_job_kind,
        invalid_domain_constraint=invalid_domain_constraint,
    )
    bridge_only = _bridge_only(
        selected=selected,
        provider_job_kind=provider_job_kind,
        invalid_domain_constraint=invalid_domain_constraint,
    )
    selected_reason = _selected_candidate_reason(
        selected=selected,
        provider_job_kind=provider_job_kind,
        invalid_domain_constraint=invalid_domain_constraint,
        domain_constraint_status=domain_constraint_status,
        official_current_candidate_count=len(official_current_candidates),
    )
    if selected is not None:
        selected["rejection_or_selection_reason"] = selected_reason

    first_failure_layer = _first_failure_layer(
        selected=selected,
        sanitized_results=sanitized_results,
        provider_job_kind=provider_job_kind,
        invalid_domain_constraint=invalid_domain_constraint,
        domain_constraint_status=domain_constraint_status,
        official_current_candidate_count=len(official_current_candidates),
    )
    bridge_hint = _first_url_result(sanitized_results)

    return {
        "schema_version": "ag96i3d_provider_neutral_result_set_diagnostics_v1",
        "record_type": "provider_neutral_official_current_result_set_diagnostics",
        "owner": "FollowupProviderResultSetDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "provider_name": provider_name,
        "provider_surface_role": clean_token(provider_surface_role, limit=120)
        or "candidate_acquisition",
        "provider_job_kind": provider_job_kind,
        "acquisition_mode": acquisition_mode,
        "authorized_query_ref": clean_token(authorized_query_ref, limit=180),
        "authorized_query": clean_text(authorized_query, limit=300),
        "provider_result_count": len(sanitized_results),
        "sanitized_result_count": len(sanitized_results),
        "sanitized_results": sanitized_results,
        "official_current_candidate_count": len(official_current_candidates),
        "official_current_nonselected_count": max(
            0,
            len(official_current_candidates) - (1 if selected else 0),
        ),
        "selected_candidate_rank": selected.get("rank") if selected else None,
        "selected_candidate_domain": selected.get("domain") if selected else None,
        "selected_candidate_source_class": (
            selected.get("source_class") if selected else None
        ),
        "selected_candidate_reason": selected_reason,
        "first_failure_layer": first_failure_layer,
        "domain_constraint_status": domain_constraint_status,
        "domain_constraints": list(constraint_domains)
        if domain_constraint_status == "earned_domain_constraint"
        else [],
        "authority_decision_required": authority_decision_required,
        "authority_decision_present": bool(authority_decision_present),
        "bridge_only": bridge_only,
        "bridge_hint_rank": bridge_hint.get("rank") if bridge_hint else None,
        "bridge_hint_domain": bridge_hint.get("domain") if bridge_hint else None,
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def selected_or_bridge_result(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return the selected official/current result or first URL bridge hint."""

    source = _mapping(diagnostics)
    selected_rank = source.get("selected_candidate_rank")
    bridge_rank = source.get("bridge_hint_rank")
    for rank in (selected_rank, bridge_rank):
        if rank is None:
            continue
        for item in source.get("sanitized_results", []):
            mapped = _mapping(item)
            if mapped.get("rank") == rank:
                return dict(mapped)
    return None


def sanitize_result_set_diagnostics(
    value: Mapping[str, Any],
    *,
    provider_job_kind: str,
    provider_name: str,
    provider_surface_role: str = "candidate_acquisition",
    acquisition_mode: str = DISCOVERY_UNCONSTRAINED,
) -> dict[str, Any]:
    """Re-sanitize a diagnostic packet before exporting it from another record."""

    source = _mapping(value)
    results = []
    for index, item in enumerate(source.get("sanitized_results", []), start=1):
        mapped = _mapping(item)
        if not mapped:
            continue
        sanitized = {
            "rank": int(mapped.get("rank") or index),
            "url": clean_text(mapped.get("url"), limit=500),
            "title": clean_text(mapped.get("title"), limit=300),
            "domain": clean_text(mapped.get("domain"), limit=160),
            "source_tier": clean_token(mapped.get("source_tier")),
            "source_class": clean_token(mapped.get("source_class")) or "unknown",
            "currentness_signal": clean_token(
                mapped.get("currentness_signal") or "not_evaluated",
                limit=120,
            ),
            "candidate_fit_status": clean_token(
                mapped.get("candidate_fit_status") or "not_evaluated",
                limit=120,
            ),
            "provider_name": clean_token(
                mapped.get("provider_name") or provider_name,
                limit=120,
            ),
            "acquisition_mode": _acquisition_mode(
                mapped.get("acquisition_mode") or acquisition_mode
            ),
            "rejection_or_selection_reason": clean_token(
                mapped.get("rejection_or_selection_reason") or "not_evaluated",
                limit=180,
            ),
        }
        results.append({key: sanitized[key] for key in SANITIZED_RESULT_KEYS})

    selected_rank = source.get("selected_candidate_rank")
    return {
        "schema_version": clean_token(
            source.get("schema_version")
            or "ag96i3d_provider_neutral_result_set_diagnostics_v1",
            limit=120,
        ),
        "record_type": clean_token(
            source.get("record_type")
            or "provider_neutral_official_current_result_set_diagnostics",
            limit=120,
        ),
        "owner": clean_token(
            source.get("owner") or "FollowupProviderResultSetDiagnostics",
            limit=120,
        ),
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "provider_result_count": int(source.get("provider_result_count") or 0),
        "sanitized_result_count": int(source.get("sanitized_result_count") or 0),
        "sanitized_results": results,
        "provider_job_kind": clean_token(
            source.get("provider_job_kind") or provider_job_kind,
            limit=120,
        ),
        "provider_name": clean_token(
            source.get("provider_name") or provider_name,
            limit=120,
        ),
        "provider_surface_role": clean_token(
            source.get("provider_surface_role") or provider_surface_role,
            limit=120,
        ),
        "acquisition_mode": _acquisition_mode(
            source.get("acquisition_mode") or acquisition_mode
        ),
        "authorized_query_ref": clean_token(
            source.get("authorized_query_ref"),
            limit=180,
        ),
        "authorized_query": clean_text(source.get("authorized_query"), limit=300),
        "official_current_candidate_count": int(
            source.get("official_current_candidate_count") or 0
        ),
        "official_current_nonselected_count": int(
            source.get("official_current_nonselected_count") or 0
        ),
        "selected_candidate_rank": int(selected_rank) if selected_rank else None,
        "selected_candidate_domain": clean_text(
            source.get("selected_candidate_domain"),
            limit=160,
        ),
        "selected_candidate_source_class": clean_token(
            source.get("selected_candidate_source_class"),
            limit=120,
        ),
        "selected_candidate_reason": clean_token(
            source.get("selected_candidate_reason") or "unknown",
            limit=180,
        ),
        "first_failure_layer": clean_token(
            source.get("first_failure_layer") or "unknown",
            limit=180,
        ),
        "domain_constraint_status": clean_token(
            source.get("domain_constraint_status") or "not_present",
            limit=120,
        ),
        "domain_constraints": list(_clean_domain_tuple(source.get("domain_constraints"))),
        "authority_decision_required": bool(source.get("authority_decision_required")),
        "authority_decision_present": bool(source.get("authority_decision_present")),
        "bridge_only": bool(source.get("bridge_only")),
        "bridge_hint_rank": source.get("bridge_hint_rank"),
        "bridge_hint_domain": clean_text(source.get("bridge_hint_domain"), limit=160),
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _sanitize_result_record(
    value: Mapping[str, Any],
    *,
    rank: int,
    provider_name: str,
    acquisition_mode: str,
) -> dict[str, Any]:
    source = _mapping(value)
    url = clean_text(source.get("url"), limit=500)
    domain = clean_text(source.get("domain"), limit=160) or _domain_from_url(url)
    title = clean_text(source.get("title"), limit=300)
    source_tier, source_class = _source_fields(
        source_tier=source.get("source_tier"),
        source_class=source.get("source_class"),
        domain=domain,
    )
    currentness_signal = _currentness_signal(
        title=title,
        url=url,
        provided=source.get("currentness_signal"),
    )
    out = {
        "rank": int(rank),
        "url": url,
        "title": title,
        "domain": clean_text(domain, limit=160),
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness_signal,
        "candidate_fit_status": _candidate_fit_status(
            url=url,
            source_tier=source_tier,
            source_class=source_class,
            currentness_signal=currentness_signal,
        ),
        "provider_name": provider_name,
        "acquisition_mode": acquisition_mode,
        "rejection_or_selection_reason": "not_evaluated",
    }
    return {key: out[key] for key in SANITIZED_RESULT_KEYS}


def _source_fields(
    *,
    source_tier: Any,
    source_class: Any,
    domain: str | None,
) -> tuple[str | None, str]:
    cleaned_tier = clean_token(source_tier, limit=120)
    cleaned_class = clean_token(source_class, limit=120)
    if cleaned_tier or cleaned_class:
        return cleaned_tier, cleaned_class or "unknown"
    normalized = clean_text(domain, limit=160) or ""
    if normalized.endswith(".gov"):
        return "official", "official_government"
    if normalized.endswith(".edu"):
        return "academic", "academic_or_expert"
    return None, "unknown"


def _currentness_signal(*, title: str | None, url: str | None, provided: Any) -> str:
    cleaned = clean_token(provided, limit=120)
    if cleaned:
        return cleaned
    text = f"{title or ''} {url or ''}".casefold()
    if "current" in text or any(str(year) in text for year in range(2024, 2031)):
        return "current_candidate_signal"
    return "currentness_not_verified_by_diagnostic"


def _candidate_fit_status(
    *,
    url: str | None,
    source_tier: str | None,
    source_class: str,
    currentness_signal: str,
) -> str:
    if not url:
        return "no_url"
    if not _is_official(source_tier=source_tier, source_class=source_class):
        return "bridge_hint_only"
    if clean_token(currentness_signal) in CURRENTNESS_FAILURE_SIGNALS:
        return "official_currentness_failed"
    if clean_token(currentness_signal) in CURRENTNESS_POSITIVE_SIGNALS:
        return "official_current_candidate_fit"
    return "official_currentness_unverified"


def _is_official(*, source_tier: str | None, source_class: str | None) -> bool:
    return source_tier == "official" or source_class in OFFICIAL_CURRENT_SOURCE_CLASSES


def _result_reason(
    item: Mapping[str, Any],
    *,
    provider_job_kind: str,
    invalid_domain_constraint: bool,
) -> str:
    if invalid_domain_constraint:
        return "domain_constraint_requires_upstream_authority_decision"
    if provider_job_kind in SCOUT_BRIDGE_JOB_KINDS:
        return "scout_bridge_hint_recorded_not_official_current_satisfaction"
    status = clean_token(item.get("candidate_fit_status"))
    if status == "official_current_candidate_fit":
        return "official_current_candidate_available"
    if status == "official_currentness_unverified":
        return "official_candidate_currentness_unverified"
    if status == "official_currentness_failed":
        return "official_candidate_currentness_failed"
    if status == "no_url":
        return "rejected_missing_url"
    return "bridge_hint_only"


def _select_candidate(
    official_current_candidates: list[dict[str, Any]],
    *,
    provider_job_kind: str,
    invalid_domain_constraint: bool,
) -> dict[str, Any] | None:
    if invalid_domain_constraint or provider_job_kind in SCOUT_BRIDGE_JOB_KINDS:
        return None
    if provider_job_kind == OFFICIAL_CURRENT_CANDIDATE_ACQUISITION:
        return official_current_candidates[0] if official_current_candidates else None
    return None


def _selected_candidate_reason(
    *,
    selected: Mapping[str, Any] | None,
    provider_job_kind: str,
    invalid_domain_constraint: bool,
    domain_constraint_status: str,
    official_current_candidate_count: int,
) -> str:
    if invalid_domain_constraint:
        if domain_constraint_status == "invalid_missing_authority_decision":
            return "hard_corridor_domain_constraint_missing_authority_decision"
        return "discovery_unconstrained_refused_source_specific_domain_constraint"
    if provider_job_kind in SCOUT_BRIDGE_JOB_KINDS:
        return "scout_bridge_hint_recorded_not_official_current_satisfaction"
    if selected is not None:
        return "official_current_candidate_selected"
    if official_current_candidate_count == 0:
        return "provider_result_set_lacked_official_current_candidate"
    return "no_satisfying_official_current_candidate"


def _first_failure_layer(
    *,
    selected: Mapping[str, Any] | None,
    sanitized_results: list[dict[str, Any]],
    provider_job_kind: str,
    invalid_domain_constraint: bool,
    domain_constraint_status: str,
    official_current_candidate_count: int,
) -> str:
    if invalid_domain_constraint:
        if domain_constraint_status == "invalid_missing_authority_decision":
            return "hard_corridor_authority_decision_missing"
        return "domain_constraint_authority"
    if not sanitized_results:
        return "provider_result_set"
    if provider_job_kind in SCOUT_BRIDGE_JOB_KINDS:
        return "official_current_selection"
    if selected is None and official_current_candidate_count == 0:
        return "provider_result_set_lacked_official_current_candidate"
    if selected is None:
        return "official_current_selection"
    return "none"


def _bridge_only(
    *,
    selected: Mapping[str, Any] | None,
    provider_job_kind: str,
    invalid_domain_constraint: bool,
) -> bool:
    return selected is None or provider_job_kind in SCOUT_BRIDGE_JOB_KINDS or invalid_domain_constraint


def _domain_constraint_status(
    *,
    acquisition_mode: str,
    constraint_domains: tuple[str, ...],
    authority_decision_present: bool,
) -> str:
    if acquisition_mode == DISCOVERY_UNCONSTRAINED and constraint_domains:
        return "invalid_unearned_domain_constraint"
    if acquisition_mode == HARD_CORRIDOR_DOMAIN_CONSTRAINED:
        if not authority_decision_present:
            return "invalid_missing_authority_decision"
        if constraint_domains:
            return "earned_domain_constraint"
        return "authority_decision_present_no_domain_constraint"
    if constraint_domains:
        return "soft_hint_not_provider_filter"
    return "not_present"


def _first_url_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in results if item.get("url")), None)


def _clean_domain_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [value]
    else:
        try:
            items = list(value)
        except TypeError:
            items = []
    cleaned = []
    for item in items:
        domain = clean_text(item, limit=160)
        if domain:
            cleaned.append(domain.casefold())
    return tuple(dict.fromkeys(cleaned))


def _acquisition_mode(value: Any) -> str:
    cleaned = clean_token(value, limit=120)
    return cleaned if cleaned in ACQUISITION_MODES else DISCOVERY_UNCONSTRAINED


def _domain_from_url(url: str | None) -> str | None:
    parsed = urlparse(url or "")
    domain = parsed.netloc.casefold()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_ranked_results_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_snippets_retained": False,
        "raw_page_text_retained": False,
        "raw_text_retained": False,
        "raw_prompts_retained": False,
        "raw_prompt_retained": False,
        "model_outputs_retained": False,
        "model_response_text_retained": False,
        "api_keys_retained": False,
        "env_values_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_traces_retained": False,
        "full_trace_retained": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "DISCOVERY_UNCONSTRAINED",
    "HARD_CORRIDOR_DOMAIN_CONSTRAINED",
    "SANITIZED_RESULT_KEYS",
    "SOFT_AUTHORITY_HINT",
    "build_official_current_discovery_diagnostics",
    "sanitize_result_set_diagnostics",
    "selected_or_bridge_result",
]
