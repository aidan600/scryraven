"""Offline provider-neutral scout/search freshness policy diagnostics.

Freshness here is a retrieval prior, not evidence. The helper classifies the
authorized query and emits sanitized policy fields a search caller may consume.
It does not call providers, fetch/read pages, inspect private payloads, or alter
product routing.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from core.followup_deliberation import ProviderJobKind, clean_text, clean_token

FRESHNESS_NONE = "none"
LATEST_BREAKING = "latest_breaking"
RECENT_DAYS = "recent_days"
RECENT_WEEKS = "recent_weeks"
RECENT_MONTHS = "recent_months"
CURRENT_YEAR = "current_year"
KNOWN_YEAR = "known_year"
CURRENT_OR_STABLE = "current_or_stable"
HISTORICAL_OR_STABLE = "historical_or_stable"
MIXED_PROBE = "mixed_probe"

SCOUT_JOB_KINDS = frozenset(
    {
        ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        ProviderJobKind.BRIDGE_HINT_DISCOVERY.value,
    }
)

OFFICIAL_CURRENT_JOB_KINDS = frozenset(
    {
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        ProviderJobKind.LEGAL_CURRENT_PRIMARY_ACQUISITION.value,
        ProviderJobKind.CANONICAL_DOC_ACQUISITION.value,
    }
)

FRESHNESS_INTENTS = frozenset(
    {
        FRESHNESS_NONE,
        LATEST_BREAKING,
        RECENT_DAYS,
        RECENT_WEEKS,
        RECENT_MONTHS,
        CURRENT_YEAR,
        KNOWN_YEAR,
        CURRENT_OR_STABLE,
        HISTORICAL_OR_STABLE,
        MIXED_PROBE,
    }
)

_RECENT_BREAKING_RE = re.compile(
    r"\b(today|breaking|live|right now|this morning|this afternoon|this evening)\b",
    re.IGNORECASE,
)
_THIS_WEEK_RE = re.compile(r"\bthis\s+week\b", re.IGNORECASE)
_LATEST_RELEASE_RE = re.compile(
    r"\blatest\b.*\b(patch|update|release|release notes?|patch notes?)\b|"
    r"\b(patch|update|release|release notes?|patch notes?)\b.*\blatest\b",
    re.IGNORECASE,
)
_EXPLICIT_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
_OFFICIAL_CURRENT_ARTIFACT_RE = re.compile(
    r"\b("
    r"official|current|notice|announcement|newsroom|bulletin|rule|guidance|"
    r"form|instructions|fee|fees|rate|rates|standard mileage|filing|final rule|"
    r"release|table|irs|uscis|sec|fda|dol|osha|ftc"
    r")\b",
    re.IGNORECASE,
)
_CURRENT_STABLE_RE = re.compile(
    r"\bcurrent\b.*\b(fees?|rules?|rates?|forms?|guidance|instructions?|"
    r"thresholds?|limits?|requirements?)\b|"
    r"\b(fees?|rules?|rates?|forms?|guidance|instructions?|thresholds?|limits?|"
    r"requirements?)\b.*\bcurrent\b",
    re.IGNORECASE,
)
_HISTORICAL_RE = re.compile(
    r"\b(historical|history|when was|who invented|founded|born|died|origin|"
    r"ancient|timeline)\b",
    re.IGNORECASE,
)


def build_search_freshness_policy_diagnostics(
    *,
    authorized_query: str,
    provider_job_kind: str,
    query_shape_mode: str | None = None,
    acquisition_mode: str | None = None,
    canonical_subject_status: str | None = None,
    freshness_intent: str | None = None,
    current_date: date | str | None = None,
    current_year: int | None = None,
    max_probe_horizons: int | None = None,
) -> dict[str, Any]:
    """Build a sanitized offline freshness policy packet.

    Provider freshness values are provider-specific translations of the policy.
    ``None`` means the provider call should omit a freshness filter.
    """

    query = clean_text(authorized_query, limit=500) or ""
    job_kind = _provider_job_kind(provider_job_kind)
    shape_mode = clean_token(query_shape_mode, limit=120) or "unspecified"
    acquisition = clean_token(acquisition_mode, limit=120) or "unspecified"
    canonical_status = (
        clean_token(canonical_subject_status, limit=120) or "unspecified"
    )
    year = _current_year(current_date=current_date, current_year=current_year)
    explicit_years = _explicit_years(query)
    intent = _freshness_intent(
        query=query,
        provider_job_kind=job_kind,
        canonical_subject_status=canonical_status,
        explicit_years=explicit_years,
        current_year=year,
        override=freshness_intent,
    )
    policy = _provider_freshness_policy(intent)
    provider_values = _provider_freshness_value_by_provider(intent)

    return {
        "schema_version": "ag96i3g_provider_neutral_search_freshness_policy_v1",
        "record_type": "provider_neutral_search_freshness_policy_diagnostics",
        "owner": "FollowupSearchFreshnessPolicyDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "original_authorized_query": query,
        "provider_job_kind": job_kind,
        "query_shape_mode": shape_mode,
        "acquisition_mode": acquisition,
        "canonical_subject_status": canonical_status,
        "current_year": year,
        "explicit_years": explicit_years,
        "freshness_intent": intent,
        "freshness_window": _freshness_window(intent),
        "provider_freshness_policy": policy,
        "provider_freshness_value_by_provider": provider_values,
        "freshness_rationale": _freshness_rationale(intent),
        "over_narrow_recent_window_forbidden": _over_narrow_forbidden(intent),
        "mixed_probe_allowed": intent == MIXED_PROBE,
        "max_probe_horizons": _bounded_probe_horizons(max_probe_horizons),
        "live_call_authorized": False,
        "provider_called": False,
        "fetch_read_invoked": False,
        "model_called": False,
        "author_executor_invoked": False,
        "evidence_boundary": {
            "freshness_policy_is_final_evidence": False,
            "freshness_policy_is_citation_eligible": False,
            "selected_candidates_are_final_evidence": False,
            "selected_candidates_are_citation_eligible": False,
            "final_evidence_requires_later_fetch_read_admission": True,
            "author_or_final_answer_activation_allowed": False,
        },
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _freshness_intent(
    *,
    query: str,
    provider_job_kind: str,
    canonical_subject_status: str,
    explicit_years: list[int],
    current_year: int,
    override: str | None,
) -> str:
    override_intent = clean_token(override, limit=80)
    if override_intent in FRESHNESS_INTENTS:
        return override_intent

    if _RECENT_BREAKING_RE.search(query):
        return LATEST_BREAKING
    if _THIS_WEEK_RE.search(query):
        return RECENT_WEEKS
    if _LATEST_RELEASE_RE.search(query):
        if provider_job_kind in SCOUT_JOB_KINDS or canonical_subject_status == "unresolved":
            return MIXED_PROBE
        return RECENT_MONTHS
    if explicit_years and _OFFICIAL_CURRENT_ARTIFACT_RE.search(query):
        if current_year in explicit_years and "current" in query.casefold():
            return CURRENT_YEAR
        return KNOWN_YEAR
    if _CURRENT_STABLE_RE.search(query):
        return CURRENT_OR_STABLE
    if provider_job_kind in SCOUT_JOB_KINDS:
        return MIXED_PROBE
    if _HISTORICAL_RE.search(query):
        return HISTORICAL_OR_STABLE
    return HISTORICAL_OR_STABLE


def _provider_freshness_policy(intent: str) -> str:
    if intent in {LATEST_BREAKING, RECENT_DAYS, RECENT_WEEKS}:
        return "apply_narrow_recent_filter"
    if intent == RECENT_MONTHS:
        return "apply_broad_recent_filter"
    if intent == MIXED_PROBE:
        return "allow_mixed_probe_horizons_without_forcing_recent_only"
    return "omit_provider_freshness_filter"


def _provider_freshness_value_by_provider(intent: str) -> dict[str, str | None]:
    brave_value = {
        LATEST_BREAKING: "pd",
        RECENT_DAYS: "pd",
        RECENT_WEEKS: "pw",
        RECENT_MONTHS: "pm",
    }.get(intent)
    serper_value = {
        LATEST_BREAKING: "qdr:d",
        RECENT_DAYS: "qdr:d",
        RECENT_WEEKS: "qdr:w",
        RECENT_MONTHS: "qdr:m",
    }.get(intent)
    return {
        "brave": brave_value,
        "serper": serper_value,
        "tavily": None,
        "linkup": None,
        "exa": None,
    }


def _freshness_window(intent: str) -> str:
    return {
        FRESHNESS_NONE: "absent",
        LATEST_BREAKING: "same_day_or_last_day",
        RECENT_DAYS: "recent_days",
        RECENT_WEEKS: "recent_weeks",
        RECENT_MONTHS: "recent_months",
        CURRENT_YEAR: "current_year_or_broad",
        KNOWN_YEAR: "known_year_or_broad",
        CURRENT_OR_STABLE: "current_authoritative_or_broad",
        HISTORICAL_OR_STABLE: "absent",
        MIXED_PROBE: "mixed_absent_and_broad_recent",
    }.get(intent, "absent")


def _freshness_rationale(intent: str) -> str:
    return {
        FRESHNESS_NONE: "no freshness prior was requested or inferred",
        LATEST_BREAKING: "query asks for today/breaking/live information",
        RECENT_DAYS: "query asks for a very recent event window",
        RECENT_WEEKS: "query asks for this-week recency",
        RECENT_MONTHS: "latest release or patch may be weeks or months old",
        CURRENT_YEAR: (
            "current-year official artifacts may remain authoritative after "
            "their publication week"
        ),
        KNOWN_YEAR: (
            "known-year official/current artifacts may be older than recent SEO "
            "summaries while still canonical"
        ),
        CURRENT_OR_STABLE: (
            "current official rules, fees, rates, forms, or guidance often mean "
            "still authoritative rather than newly published"
        ),
        HISTORICAL_OR_STABLE: (
            "historical or stable facts usually should not use provider freshness"
        ),
        MIXED_PROBE: (
            "ambiguous scout work may compare absent and broad recency probes "
            "without promoting a canonical subject"
        ),
    }.get(intent, "no freshness prior was requested or inferred")


def _over_narrow_forbidden(intent: str) -> bool:
    return intent in {
        CURRENT_YEAR,
        KNOWN_YEAR,
        CURRENT_OR_STABLE,
        HISTORICAL_OR_STABLE,
        MIXED_PROBE,
    }


def _explicit_years(query: str) -> list[int]:
    return list(dict.fromkeys(int(match.group(1)) for match in _EXPLICIT_YEAR_RE.finditer(query)))


def _current_year(*, current_date: date | str | None, current_year: int | None) -> int:
    if current_year is not None:
        return int(current_year)
    if isinstance(current_date, date):
        return current_date.year
    if isinstance(current_date, str):
        match = re.match(r"(\d{4})-\d{2}-\d{2}$", current_date.strip())
        if match:
            return int(match.group(1))
    return date.today().year


def _bounded_probe_horizons(value: int | None) -> int:
    if value is None:
        return 2
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 2
    return min(4, max(1, count))


def _provider_job_kind(value: Any) -> str:
    cleaned = clean_token(value, limit=120)
    valid = {item.value for item in ProviderJobKind}
    if cleaned in valid:
        return cleaned
    return ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_freshness_policy_only": True,
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


__all__ = [
    "CURRENT_OR_STABLE",
    "CURRENT_YEAR",
    "FRESHNESS_NONE",
    "HISTORICAL_OR_STABLE",
    "KNOWN_YEAR",
    "LATEST_BREAKING",
    "MIXED_PROBE",
    "RECENT_DAYS",
    "RECENT_MONTHS",
    "RECENT_WEEKS",
    "build_search_freshness_policy_diagnostics",
]
