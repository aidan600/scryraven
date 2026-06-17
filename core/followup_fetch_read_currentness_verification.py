"""Offline fetch/read currentness verification diagnostics for AG-96I3J.

The helper consumes sanitized handoff candidates and caller-supplied read
observations only. It does not fetch pages, call providers, invoke models, admit
evidence, or make citation/final-answer eligibility decisions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from core.followup_deliberation import clean_text, clean_token

SCHEMA_VERSION = "ag96i3j_fetch_read_currentness_verification_v1"
RECORD_TYPE = "fetch_read_currentness_verification_diagnostics"

VERIFIED_OFFICIAL_CURRENT_RELEVANCE = "verified_official_current_relevance"
OFFICIAL_BUT_REQUIRED_TERMS_MISSING = "official_but_required_terms_missing"
OFFICIAL_BUT_CURRENTNESS_UNCLEAR = "official_but_currentness_unclear"
OFFICIAL_BUT_VALUE_TERMS_MISSING = "official_but_value_terms_missing"
FETCH_READ_FAILED = "fetch_read_failed"
READ_UNAVAILABLE = "read_unavailable"
CANDIDATE_URL_MISMATCH = "candidate_url_mismatch"
CANDIDATE_DOMAIN_MISMATCH = "candidate_domain_mismatch"
CANDIDATE_REJECTED = "candidate_rejected"
NOT_ATTEMPTED = "not_attempted"

USED_FOR_VERIFICATION = "used_for_verification"
REJECTED_WITH_REASON = "rejected_with_reason"
SUPERSEDED_WITH_REASON = "superseded_with_reason"
NOT_ATTEMPTED_ACCOUNTING = "not_attempted"

EVIDENCE_LEDGER_ADMISSION_REVIEW = "evidence_ledger_admission_review"
TARGETED_FETCH_READ_RETRY = "targeted_fetch_read_retry"
SCOUT_OR_QUERY_REPAIR = "scout_or_query_repair"
REJECT_CANDIDATE = "reject_candidate"
SEEK_BETTER_OFFICIAL_SOURCE = "seek_better_official_source"

_READABLE_STATUSES = frozenset({"readable", "partial"})
_FAILED_FETCH_STATUSES = frozenset({"failed", "blocked"})
_OFFICIAL_SOURCE_CLASSES = frozenset(
    {"official_current_rules", "official_government", "official"}
)
_CURRENTNESS_HINT_TERMS = frozenset(
    {
        "current",
        "latest",
        "updated",
        "effective",
        "release",
        "final rule",
        "recall",
        "safety alert",
        "version",
        "patch",
    }
)
_BLOCKED_FRAGMENT_MARKERS = (
    "raw_provider_payload",
    "raw payload",
    "raw_prompt",
    "raw prompt",
    "raw page text",
    "page_text",
    "payload_marker",
    "blocked_marker",
    "blocked raw",
    "redacted_marker",
    "env value",
    "api key",
    "secret",
    "private log",
    "full trace",
)


def build_fetch_read_currentness_verification_diagnostics(
    *,
    scout_to_acquisition_handoff_diagnostics: Mapping[str, Any] | None = None,
    verification_candidate: Mapping[str, Any] | None = None,
    read_observation: Mapping[str, Any] | None = None,
    verification_requirements: Mapping[str, Any] | None = None,
    max_supported_excerpt_chars: int = 240,
    max_missing_terms: int | None = None,
) -> dict[str, Any]:
    """Build a bounded verification packet from an offline read observation."""

    handoff = _mapping(scout_to_acquisition_handoff_diagnostics)
    candidate = _candidate(handoff=handoff, explicit=verification_candidate)
    observation = _mapping(read_observation)
    requirements = _mapping(verification_requirements)

    candidate_url = _url(candidate.get("url") or candidate.get("candidate_url"))
    candidate_domain = (
        _domain(candidate.get("domain") or candidate.get("candidate_domain"))
        or _domain_from_url(candidate_url)
    )
    attempted_url = _url(observation.get("attempted_url"))
    resolved_url = _url(observation.get("resolved_url"))
    observation_domain = (
        _domain(observation.get("domain"))
        or _domain_from_url(resolved_url)
        or _domain_from_url(attempted_url)
    )
    expected_url = _url(requirements.get("expected_url")) or candidate_url
    expected_domain = (
        _domain(requirements.get("expected_domain"))
        or candidate_domain
        or _domain_from_url(expected_url)
    )
    source_obligation = (
        clean_token(requirements.get("source_obligation"), limit=120)
        or "official_current"
    )
    source_class_required = clean_token(
        requirements.get("source_class_required"),
        limit=120,
    )

    raw_text = _read_text(observation)
    fetch_status = clean_token(observation.get("fetch_status"), limit=80) or "unknown"
    read_status = clean_token(observation.get("read_status"), limit=80) or "unknown"
    required_terms = _terms(requirements.get("required_terms"))
    required_years = _year_terms(requirements.get("required_years"))
    currentness_terms = _terms(requirements.get("currentness_terms"))
    optional_value_terms = _terms(requirements.get("optional_value_terms"))
    forbidden_stale_terms = _terms(requirements.get("forbidden_stale_terms"))

    required_found, required_missing = _presence(required_terms, raw_text)
    years_found, years_missing = _presence(required_years, raw_text)
    currentness_found, _currentness_missing = _presence(currentness_terms, raw_text)
    optional_found, optional_missing = _presence(optional_value_terms, raw_text)
    stale_found, _stale_missing = _presence(forbidden_stale_terms, raw_text)

    required_missing = _bounded_missing(required_missing, max_missing_terms)
    years_missing = _bounded_missing(years_missing, max_missing_terms)
    optional_missing = _bounded_missing(optional_missing, max_missing_terms)

    source_identity_status = _source_identity_status(
        candidate_url=candidate_url,
        candidate_domain=candidate_domain,
        expected_url=expected_url,
        expected_domain=expected_domain,
        attempted_url=attempted_url,
        resolved_url=resolved_url,
        observation_domain=observation_domain,
    )
    official_status = _official_status(
        candidate=candidate,
        expected_domain=expected_domain,
        observation_domain=observation_domain,
        source_class_required=source_class_required,
    )
    currentness_supported = _currentness_supported(
        raw_text=raw_text,
        required_terms=required_terms,
        required_years_found=years_found,
        required_years_missing=years_missing,
        currentness_terms=currentness_terms,
        currentness_terms_found=currentness_found,
        observation=observation,
    )

    status, accounting, next_step, reason = _decision(
        source_identity_status=source_identity_status,
        official_status=official_status,
        fetch_status=fetch_status,
        read_status=read_status,
        raw_text=raw_text,
        required_missing=required_missing,
        years_missing=years_missing,
        currentness_supported=currentness_supported,
        optional_terms=optional_value_terms,
        optional_missing=optional_missing,
        stale_terms_found=stale_found,
    )

    evidence_boundary = _evidence_boundary()
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "owner": "FollowupFetchReadCurrentnessVerificationDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "candidate_url": candidate_url,
        "candidate_domain": candidate_domain,
        "attempted_url": attempted_url,
        "resolved_url": resolved_url,
        "domain": observation_domain,
        "source_obligation": source_obligation,
        "verification_status": status,
        "candidate_accounting_status": accounting,
        "source_identity_status": source_identity_status,
        "official_source_status": official_status,
        "fetch_status": fetch_status,
        "read_status": read_status,
        "http_status": _http_status(observation.get("http_status")),
        "content_type": clean_text(observation.get("content_type"), limit=120),
        "required_terms_found": required_found,
        "required_terms_missing": required_missing,
        "required_years_found": years_found,
        "required_years_missing": years_missing,
        "currentness_terms_found": currentness_found,
        "stale_terms_found": stale_found,
        "optional_value_terms_found": optional_found,
        "optional_value_terms_missing": optional_missing,
        "supported_excerpt_fragments": _supported_fragments(
            raw_text=raw_text,
            terms=(*required_found, *years_found, *currentness_found, *optional_found),
            max_chars=_excerpt_limit(max_supported_excerpt_chars),
        ),
        "unsupported_reason": reason,
        "freshness_policy_context": _freshness_context(handoff, candidate),
        "recommended_next_step": next_step,
        "evidence_boundary": evidence_boundary,
        "final_evidence": False,
        "citation_eligible": False,
        "evidence_ledger_admitted": False,
        "author_activation_allowed": False,
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _decision(
    *,
    source_identity_status: str,
    official_status: str,
    fetch_status: str,
    read_status: str,
    raw_text: str,
    required_missing: list[str],
    years_missing: list[str],
    currentness_supported: bool,
    optional_terms: tuple[str, ...],
    optional_missing: list[str],
    stale_terms_found: list[str],
) -> tuple[str, str, str, str | None]:
    if fetch_status == NOT_ATTEMPTED:
        return (
            NOT_ATTEMPTED,
            NOT_ATTEMPTED_ACCOUNTING,
            TARGETED_FETCH_READ_RETRY,
            "read_observation_not_attempted",
        )
    if source_identity_status == "candidate_domain_mismatch":
        return (
            CANDIDATE_DOMAIN_MISMATCH,
            REJECTED_WITH_REASON,
            REJECT_CANDIDATE,
            "read_observation_domain_does_not_match_candidate",
        )
    if source_identity_status == "candidate_url_mismatch":
        return (
            CANDIDATE_URL_MISMATCH,
            REJECTED_WITH_REASON,
            REJECT_CANDIDATE,
            "read_observation_url_does_not_match_candidate",
        )
    if official_status != "official_source_supported":
        return (
            CANDIDATE_REJECTED,
            REJECTED_WITH_REASON,
            SEEK_BETTER_OFFICIAL_SOURCE,
            official_status,
        )
    if fetch_status in _FAILED_FETCH_STATUSES:
        return (
            FETCH_READ_FAILED,
            NOT_ATTEMPTED_ACCOUNTING,
            TARGETED_FETCH_READ_RETRY,
            "fetch_status_did_not_produce_readable_observation",
        )
    if read_status not in _READABLE_STATUSES or not raw_text:
        return (
            READ_UNAVAILABLE,
            REJECTED_WITH_REASON,
            TARGETED_FETCH_READ_RETRY,
            "read_status_unavailable_or_no_sanitized_text",
        )
    if stale_terms_found:
        return (
            OFFICIAL_BUT_CURRENTNESS_UNCLEAR,
            REJECTED_WITH_REASON,
            SEEK_BETTER_OFFICIAL_SOURCE,
            "forbidden_stale_terms_present",
        )
    if required_missing:
        return (
            OFFICIAL_BUT_REQUIRED_TERMS_MISSING,
            REJECTED_WITH_REASON,
            SEEK_BETTER_OFFICIAL_SOURCE,
            "required_terms_missing_from_read_observation",
        )
    if years_missing or not currentness_supported:
        return (
            OFFICIAL_BUT_CURRENTNESS_UNCLEAR,
            REJECTED_WITH_REASON,
            TARGETED_FETCH_READ_RETRY,
            "currentness_or_required_year_not_supported_by_read_observation",
        )
    if optional_terms and len(optional_missing) == len(optional_terms):
        return (
            OFFICIAL_BUT_VALUE_TERMS_MISSING,
            REJECTED_WITH_REASON,
            TARGETED_FETCH_READ_RETRY,
            "optional_value_terms_missing_from_read_observation",
        )
    return (
        VERIFIED_OFFICIAL_CURRENT_RELEVANCE,
        USED_FOR_VERIFICATION,
        EVIDENCE_LEDGER_ADMISSION_REVIEW,
        None,
    )


def _candidate(
    *,
    handoff: Mapping[str, Any],
    explicit: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(explicit, Mapping):
        return dict(explicit)
    for item in handoff.get("verification_candidates", []):
        if isinstance(item, Mapping):
            return dict(item)
    return {}


def _source_identity_status(
    *,
    candidate_url: str | None,
    candidate_domain: str | None,
    expected_url: str | None,
    expected_domain: str | None,
    attempted_url: str | None,
    resolved_url: str | None,
    observation_domain: str | None,
) -> str:
    observed_url = resolved_url or attempted_url
    observed_domain = observation_domain or _domain_from_url(observed_url)
    if expected_domain and observed_domain and expected_domain != observed_domain:
        return "candidate_domain_mismatch"
    if candidate_domain and observed_domain and candidate_domain != observed_domain:
        return "candidate_domain_mismatch"
    expected_normalized = _normalized_url(expected_url or candidate_url)
    observed_normalized = _normalized_url(observed_url)
    if expected_normalized and observed_normalized and expected_normalized != observed_normalized:
        if expected_domain and observed_domain and expected_domain == observed_domain:
            return "official_equivalent_url_same_domain"
        return "candidate_url_mismatch"
    if expected_normalized and observed_normalized:
        return "candidate_url_match"
    if expected_domain and observed_domain and expected_domain == observed_domain:
        return "candidate_domain_match"
    return "candidate_identity_unverified"


def _official_status(
    *,
    candidate: Mapping[str, Any],
    expected_domain: str | None,
    observation_domain: str | None,
    source_class_required: str | None,
) -> str:
    tier = clean_token(candidate.get("source_tier"), limit=120)
    source_class = clean_token(candidate.get("source_class"), limit=120)
    official_by_candidate = tier == "official" or source_class in _OFFICIAL_SOURCE_CLASSES
    official_by_expected_domain = bool(expected_domain and expected_domain == observation_domain)
    if source_class_required and source_class_required not in {
        tier,
        source_class,
        "official",
    }:
        return "source_class_requirement_not_met"
    if official_by_candidate or official_by_expected_domain:
        return "official_source_supported"
    return "official_source_not_supported_by_candidate_or_requirement"


def _currentness_supported(
    *,
    raw_text: str,
    required_terms: tuple[str, ...],
    required_years_found: list[str],
    required_years_missing: list[str],
    currentness_terms: tuple[str, ...],
    currentness_terms_found: list[str],
    observation: Mapping[str, Any],
) -> bool:
    if required_years_missing:
        return False
    if currentness_terms:
        return bool(currentness_terms_found)
    if required_years_found:
        return True
    if not currentness_terms:
        normalized_required = {term.casefold() for term in required_terms}
        if normalized_required.intersection(_CURRENTNESS_HINT_TERMS):
            return True
        if any(
            phrase in normalized_required
            for phrase in ("final rule", "release notes", "safety alert")
        ):
            return True
    detected_dates = " ".join(
        clean_text(observation.get(key), limit=80) or ""
        for key in ("detected_publication_date", "detected_updated_date")
    )
    return bool(detected_dates and re.search(r"\b(20\d{2}|19\d{2})\b", detected_dates)) or (
        "current" in raw_text.casefold()
    )


def _presence(terms: tuple[str, ...], raw_text: str) -> tuple[list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    for term in terms:
        if _contains_term(raw_text, term):
            found.append(term)
        else:
            missing.append(term)
    return found, missing


def _contains_term(raw_text: str, term: str) -> bool:
    if not raw_text or not term:
        return False
    return re.search(_term_pattern(term), raw_text, flags=re.IGNORECASE) is not None


def _term_pattern(term: str) -> str:
    escaped = re.escape(term.strip())
    escaped = re.sub(r"\\\s+", r"\\s+", escaped)
    if re.match(r"^[\w\s.-]+$", term):
        return rf"(?<!\w){escaped}(?!\w)"
    return escaped


def _supported_fragments(
    *,
    raw_text: str,
    terms: Sequence[str],
    max_chars: int,
) -> list[str]:
    fragments: list[str] = []
    sentences = _sentences(raw_text)
    for term in terms:
        for sentence in sentences:
            if not _contains_term(sentence, term):
                continue
            fragment = _clean_fragment(sentence, max_chars=max_chars)
            if fragment and fragment not in fragments:
                fragments.append(fragment)
            break
        if len(fragments) >= 5:
            break
    return fragments


def _sentences(raw_text: str) -> list[str]:
    text = clean_text(raw_text, limit=20_000) or ""
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", text) if item.strip()]


def _clean_fragment(sentence: str, *, max_chars: int) -> str | None:
    text = clean_text(sentence, limit=max_chars)
    if not text:
        return None
    folded = text.casefold()
    if any(marker in folded for marker in _BLOCKED_FRAGMENT_MARKERS):
        return None
    return text


def _freshness_context(
    handoff: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    source = _mapping(handoff.get("freshness_policy_diagnostics"))
    return {
        "schema_version": clean_token(source.get("schema_version"), limit=120),
        "record_type": clean_token(source.get("record_type"), limit=120),
        "freshness_intent": clean_token(
            candidate.get("freshness_intent") or source.get("freshness_intent"),
            limit=120,
        ),
        "freshness_window": clean_token(
            candidate.get("freshness_window") or source.get("freshness_window"),
            limit=120,
        ),
        "provider_freshness_policy": clean_token(
            candidate.get("provider_freshness_policy")
            or source.get("provider_freshness_policy"),
            limit=120,
        ),
        "over_narrow_recent_window_forbidden": bool(
            candidate.get("over_narrow_recent_window_forbidden")
            or source.get("over_narrow_recent_window_forbidden")
        ),
        "freshness_rationale": clean_text(
            candidate.get("freshness_rationale") or source.get("freshness_rationale"),
            limit=300,
        ),
    }


def _evidence_boundary() -> dict[str, bool]:
    return {
        "verification_observation_is_final_evidence": False,
        "verification_observation_is_citation_eligible": False,
        "evidence_ledger_admission_performed": False,
        "evidence_ledger_admission_review_required": True,
        "author_or_final_answer_activation_allowed": False,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_read_observation_only": True,
        "supported_excerpts_bounded": True,
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


def _terms(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, bytes):
        values: Sequence[Any] = ()
    elif isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        text = clean_text(item, limit=120)
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _year_terms(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    for term in _terms(value):
        match = re.search(r"\b(20\d{2}|19\d{2})\b", term)
        if match and match.group(1) not in out:
            out.append(match.group(1))
    return tuple(out)


def _bounded_missing(value: list[str], max_missing_terms: int | None) -> list[str]:
    if max_missing_terms is None:
        return value
    try:
        limit = max(0, int(max_missing_terms))
    except (TypeError, ValueError):
        return value
    return value[:limit]


def _read_text(observation: Mapping[str, Any]) -> str:
    return (
        clean_text(observation.get("text"), limit=20_000)
        or clean_text(observation.get("page_text"), limit=20_000)
        or clean_text(observation.get("extracted_text"), limit=20_000)
        or ""
    )


def _url(value: Any) -> str | None:
    return clean_text(value, limit=500)


def _domain(value: Any) -> str | None:
    text = clean_text(value, limit=160)
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = parsed.netloc.casefold()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return _domain(urlparse(url).netloc)


def _normalized_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    domain = _domain(parsed.netloc)
    if not domain:
        return None
    path = re.sub(r"/+$", "", parsed.path or "")
    return f"{domain}{path.casefold()}"


def _http_status(value: Any) -> int | None:
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if 100 <= status <= 599 else None


def _excerpt_limit(value: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return 240
    return min(500, max(40, limit))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "CANDIDATE_DOMAIN_MISMATCH",
    "CANDIDATE_REJECTED",
    "CANDIDATE_URL_MISMATCH",
    "FETCH_READ_FAILED",
    "NOT_ATTEMPTED",
    "OFFICIAL_BUT_CURRENTNESS_UNCLEAR",
    "OFFICIAL_BUT_REQUIRED_TERMS_MISSING",
    "OFFICIAL_BUT_VALUE_TERMS_MISSING",
    "READ_UNAVAILABLE",
    "RECORD_TYPE",
    "SCHEMA_VERSION",
    "VERIFIED_OFFICIAL_CURRENT_RELEVANCE",
    "build_fetch_read_currentness_verification_diagnostics",
]
