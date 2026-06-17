"""Offline sanitized read-observation adapter for AG-96I3K.

The adapter turns an AG-96I3I scout-to-acquisition handoff candidate plus
caller-supplied fetch/read material into a sanitized read observation that is
suitable as AG-96I3J verifier input.

Target flow::

    scout handoff candidate
    + caller-supplied fetch/read material
    -> sanitized read observation
    -> AG-96I3J verifier input

This adapter is pure and offline. It does not fetch pages, call providers,
invoke models, admit EvidenceLedger records, activate citation, activate Author,
or change product behavior. It only normalizes caller-supplied material into a
bounded, sanitized shape and reports a conservative routing posture.

The return shape separates two concerns:

* ``verifier_input`` is ephemeral. It may contain bounded, sanitized extracted
  text so that AG-96I3J can run term/currentness checks. It exists to feed
  verification only and is directly consumable by
  ``core.followup_fetch_read_currentness_verification`` as its ``read_observation``.
* ``durable_projection`` must not retain raw page text. It preserves only bounded
  identity, status, metadata, comparison posture, counts, redaction posture, and
  diagnostic routing fields.

URL/domain comparison mirrors the conservative same-domain posture used by
AG-96I3J. It does not invent source-specific official-domain equivalence, alias
rules, redirect-trust rules, or domain-authority policy. When acceptable
equivalence cannot be established conservatively, the adapter reports a
mismatch/uncertain posture rather than silently accepting it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from core.followup_deliberation import clean_text, clean_token

SCHEMA_VERSION = "ag96i3k_read_observation_adapter_v1"
RECORD_TYPE = "sanitized_read_observation_adapter"

# Read posture (mismatch / unreadable / failed-read / ready / not-attempted).
READ_OBSERVATION_READY = "read_observation_ready"
CANDIDATE_URL_MISMATCH = "candidate_url_mismatch"
CANDIDATE_DOMAIN_MISMATCH = "candidate_domain_mismatch"
FETCH_FAILED = "fetch_failed"
READ_UNAVAILABLE = "read_unavailable"
EMPTY_EXTRACTED_TEXT = "empty_extracted_text"
NOT_ATTEMPTED = "not_attempted"

# Candidate URL/domain comparison posture.
CANDIDATE_URL_MATCH = "candidate_url_match"
CANDIDATE_DOMAIN_MATCH = "candidate_domain_match"
RESOLVED_URL_DIFFERS_SAME_DOMAIN = "resolved_url_differs_same_domain"
CANDIDATE_IDENTITY_UNVERIFIED = "candidate_identity_unverified"

# Recommended next step (verification / retry / reject / return-to-acquisition).
FETCH_READ_CURRENTNESS_VERIFICATION = "fetch_read_currentness_verification"
TARGETED_FETCH_READ_RETRY = "targeted_fetch_read_retry"
REJECT_CANDIDATE = "reject_candidate"
SCOUT_OR_QUERY_REPAIR = "scout_or_query_repair"

_ACCEPTABLE_COMPARISON_POSTURES = frozenset(
    {
        CANDIDATE_URL_MATCH,
        CANDIDATE_DOMAIN_MATCH,
        RESOLVED_URL_DIFFERS_SAME_DOMAIN,
        CANDIDATE_IDENTITY_UNVERIFIED,
    }
)
_NOT_ATTEMPTED_FETCH_STATUSES = frozenset(
    {"not_attempted", "no_attempt", "skipped", "none", "not_started"}
)
_FAILED_FETCH_STATUSES = frozenset(
    {"failed", "blocked", "error", "timeout", "refused"}
)
_READABLE_READ_STATUSES = frozenset({"readable", "partial", "ok"})

_DEFAULT_MAX_EXTRACTED_TEXT_CHARS = 8_000
_MIN_MAX_EXTRACTED_TEXT_CHARS = 200
_MAX_MAX_EXTRACTED_TEXT_CHARS = 40_000
_NORMALIZE_TEXT_LIMIT = 200_000


def build_sanitized_read_observation(
    *,
    scout_to_acquisition_handoff_diagnostics: Mapping[str, Any] | None = None,
    handoff_candidate: Mapping[str, Any] | None = None,
    fetch_read_material: Mapping[str, Any] | None = None,
    max_extracted_text_chars: int = _DEFAULT_MAX_EXTRACTED_TEXT_CHARS,
) -> dict[str, Any]:
    """Adapt a handoff candidate + fetch/read material into a sanitized observation.

    The result is a diagnostic packet with two clearly separated regions:
    ``verifier_input`` (ephemeral, may hold bounded sanitized text) and
    ``durable_projection`` (no raw page text). It is non-authoritative: it never
    asserts final evidence, citation eligibility, EvidenceLedger admission, or
    Author activation.
    """

    handoff = _mapping(scout_to_acquisition_handoff_diagnostics)
    candidate = _candidate(handoff=handoff, explicit=handoff_candidate)
    material = _mapping(fetch_read_material)
    material_supplied = isinstance(fetch_read_material, Mapping) and bool(material)

    candidate_url = _url(candidate.get("url") or candidate.get("candidate_url"))
    candidate_domain = (
        _domain(candidate.get("domain") or candidate.get("candidate_domain"))
        or _domain_from_url(candidate_url)
    )

    attempted_url = _url(material.get("attempted_url") or material.get("url"))
    resolved_url = _url(material.get("resolved_url") or material.get("final_url"))
    attempted_domain = (
        _domain(material.get("attempted_domain"))
        or _domain_from_url(attempted_url)
    )
    resolved_domain = (
        _domain(material.get("resolved_domain") or material.get("domain"))
        or _domain_from_url(resolved_url)
    )
    observation_domain = resolved_domain or attempted_domain

    comparison_posture = _comparison_posture(
        candidate_url=candidate_url,
        candidate_domain=candidate_domain,
        attempted_url=attempted_url,
        attempted_domain=attempted_domain,
        resolved_url=resolved_url,
        resolved_domain=resolved_domain,
    )

    fetch_status = clean_token(material.get("fetch_status"), limit=80) or (
        NOT_ATTEMPTED if not material_supplied else "unknown"
    )
    read_status = clean_token(material.get("read_status"), limit=80) or "unknown"

    content_type = clean_text(material.get("content_type"), limit=160)
    media_type = clean_text(material.get("media_type"), limit=120) or _media_type(
        content_type
    )
    http_status = _http_status(material.get("http_status"))
    title = clean_text(
        material.get("title") or material.get("page_title"),
        limit=300,
    )
    detected_publication_date = clean_text(
        material.get("detected_publication_date"),
        limit=80,
    )
    detected_updated_date = clean_text(
        material.get("detected_updated_date"),
        limit=80,
    )

    text_limit = _excerpt_limit(max_extracted_text_chars)
    normalized_text = _normalized_text(material)
    extracted_text_char_count = len(normalized_text)
    bounded_text = normalized_text[:text_limit]
    sanitized_text_char_count = len(bounded_text)
    extracted_text_truncated = extracted_text_char_count > sanitized_text_char_count
    extracted_text_present = bool(bounded_text)

    read_posture, recommended_next_step = _route(
        material_supplied=material_supplied,
        fetch_status=fetch_status,
        read_status=read_status,
        comparison_posture=comparison_posture,
        extracted_text_present=extracted_text_present,
    )

    verifier_input = _verifier_input(
        attempted_url=attempted_url,
        resolved_url=resolved_url,
        observation_domain=observation_domain,
        fetch_status=fetch_status,
        read_status=read_status,
        http_status=http_status,
        content_type=content_type,
        media_type=media_type,
        title=title,
        bounded_text=bounded_text,
        detected_publication_date=detected_publication_date,
        detected_updated_date=detected_updated_date,
    )
    durable_projection = _durable_projection(
        candidate_url=candidate_url,
        candidate_domain=candidate_domain,
        attempted_url=attempted_url,
        resolved_url=resolved_url,
        attempted_domain=attempted_domain,
        resolved_domain=resolved_domain,
        observation_domain=observation_domain,
        comparison_posture=comparison_posture,
        fetch_status=fetch_status,
        read_status=read_status,
        http_status=http_status,
        content_type=content_type,
        media_type=media_type,
        title=title,
        detected_publication_date=detected_publication_date,
        detected_updated_date=detected_updated_date,
        read_posture=read_posture,
        recommended_next_step=recommended_next_step,
        extracted_text_present=extracted_text_present,
        extracted_text_char_count=extracted_text_char_count,
        sanitized_text_char_count=sanitized_text_char_count,
        extracted_text_truncated=extracted_text_truncated,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "owner": "FollowupReadObservationAdapter",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "candidate_url": candidate_url,
        "candidate_domain": candidate_domain,
        "attempted_url": attempted_url,
        "resolved_url": resolved_url,
        "attempted_domain": attempted_domain,
        "resolved_domain": resolved_domain,
        "domain": observation_domain,
        "url_domain_comparison_posture": comparison_posture,
        "fetch_status": fetch_status,
        "read_status": read_status,
        "http_status": http_status,
        "content_type": content_type,
        "media_type": media_type,
        "title": title,
        "read_posture": read_posture,
        "recommended_next_step": recommended_next_step,
        "verifier_input": verifier_input,
        "durable_projection": durable_projection,
        "evidence_boundary": _evidence_boundary(),
        "final_evidence": False,
        "citation_eligible": False,
        "evidence_ledger_admitted": False,
        "author_activation_allowed": False,
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def as_fetch_read_currentness_verification_input(
    sanitized_read_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the AG-96I3J ``read_observation`` mapping for a sanitized observation.

    This is the tested conversion path into
    ``core.followup_fetch_read_currentness_verification`` and simply exposes the
    already-bounded ``verifier_input`` region as a plain mapping.
    """

    observation = _mapping(sanitized_read_observation)
    verifier_input = observation.get("verifier_input")
    return dict(verifier_input) if isinstance(verifier_input, Mapping) else {}


def _route(
    *,
    material_supplied: bool,
    fetch_status: str,
    read_status: str,
    comparison_posture: str,
    extracted_text_present: bool,
) -> tuple[str, str]:
    if not material_supplied or fetch_status in _NOT_ATTEMPTED_FETCH_STATUSES:
        return NOT_ATTEMPTED, TARGETED_FETCH_READ_RETRY
    if comparison_posture == CANDIDATE_DOMAIN_MISMATCH:
        return CANDIDATE_DOMAIN_MISMATCH, SCOUT_OR_QUERY_REPAIR
    if comparison_posture == CANDIDATE_URL_MISMATCH:
        return CANDIDATE_URL_MISMATCH, REJECT_CANDIDATE
    if fetch_status in _FAILED_FETCH_STATUSES:
        return FETCH_FAILED, TARGETED_FETCH_READ_RETRY
    if read_status not in _READABLE_READ_STATUSES:
        return READ_UNAVAILABLE, TARGETED_FETCH_READ_RETRY
    if not extracted_text_present:
        return EMPTY_EXTRACTED_TEXT, TARGETED_FETCH_READ_RETRY
    return READ_OBSERVATION_READY, FETCH_READ_CURRENTNESS_VERIFICATION


def _comparison_posture(
    *,
    candidate_url: str | None,
    candidate_domain: str | None,
    attempted_url: str | None,
    attempted_domain: str | None,
    resolved_url: str | None,
    resolved_domain: str | None,
) -> str:
    # Domain-level checks first: an off-candidate domain (attempted or resolved)
    # is a conservative mismatch. We never invent alias/redirect-trust rules.
    if candidate_domain:
        if attempted_domain and attempted_domain != candidate_domain:
            return CANDIDATE_DOMAIN_MISMATCH
        if resolved_domain and resolved_domain != candidate_domain:
            return CANDIDATE_DOMAIN_MISMATCH

    candidate_norm = _normalized_url(candidate_url)
    attempted_norm = _normalized_url(attempted_url)
    resolved_norm = _normalized_url(resolved_url)

    if candidate_norm and attempted_norm:
        if candidate_norm == attempted_norm:
            if resolved_norm and resolved_norm != attempted_norm:
                if resolved_domain and resolved_domain != attempted_domain:
                    return CANDIDATE_DOMAIN_MISMATCH
                return RESOLVED_URL_DIFFERS_SAME_DOMAIN
            return CANDIDATE_URL_MATCH
        if candidate_domain and attempted_domain and candidate_domain == attempted_domain:
            return CANDIDATE_URL_MISMATCH
        if not candidate_domain or not attempted_domain:
            return CANDIDATE_URL_MISMATCH
        return CANDIDATE_DOMAIN_MISMATCH

    observed_domain = resolved_domain or attempted_domain
    if candidate_domain and observed_domain:
        if candidate_domain == observed_domain:
            return CANDIDATE_DOMAIN_MATCH
        return CANDIDATE_DOMAIN_MISMATCH
    return CANDIDATE_IDENTITY_UNVERIFIED


def _verifier_input(
    *,
    attempted_url: str | None,
    resolved_url: str | None,
    observation_domain: str | None,
    fetch_status: str,
    read_status: str,
    http_status: int | None,
    content_type: str | None,
    media_type: str | None,
    title: str | None,
    bounded_text: str,
    detected_publication_date: str | None,
    detected_updated_date: str | None,
) -> dict[str, Any]:
    return {
        "ephemeral_verifier_input_only": True,
        "attempted_url": attempted_url,
        "resolved_url": resolved_url,
        "domain": observation_domain,
        "fetch_status": fetch_status,
        "read_status": read_status,
        "http_status": http_status,
        "content_type": content_type,
        "media_type": media_type,
        "title": title,
        "text": bounded_text,
        "detected_publication_date": detected_publication_date,
        "detected_updated_date": detected_updated_date,
    }


def _durable_projection(
    *,
    candidate_url: str | None,
    candidate_domain: str | None,
    attempted_url: str | None,
    resolved_url: str | None,
    attempted_domain: str | None,
    resolved_domain: str | None,
    observation_domain: str | None,
    comparison_posture: str,
    fetch_status: str,
    read_status: str,
    http_status: int | None,
    content_type: str | None,
    media_type: str | None,
    title: str | None,
    detected_publication_date: str | None,
    detected_updated_date: str | None,
    read_posture: str,
    recommended_next_step: str,
    extracted_text_present: bool,
    extracted_text_char_count: int,
    sanitized_text_char_count: int,
    extracted_text_truncated: bool,
) -> dict[str, Any]:
    # Durable projection deliberately omits raw/bounded page text. It keeps only
    # identity, status, metadata, comparison posture, counts, redaction posture,
    # and diagnostic routing fields.
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "candidate_url": candidate_url,
        "candidate_domain": candidate_domain,
        "attempted_url": attempted_url,
        "resolved_url": resolved_url,
        "attempted_domain": attempted_domain,
        "resolved_domain": resolved_domain,
        "domain": observation_domain,
        "url_domain_comparison_posture": comparison_posture,
        "url_domain_comparison_acceptable": comparison_posture
        in _ACCEPTABLE_COMPARISON_POSTURES,
        "fetch_status": fetch_status,
        "read_status": read_status,
        "http_status": http_status,
        "content_type": content_type,
        "media_type": media_type,
        "title": title,
        "detected_publication_date": detected_publication_date,
        "detected_updated_date": detected_updated_date,
        "read_posture": read_posture,
        "recommended_next_step": recommended_next_step,
        "extracted_text_present": extracted_text_present,
        "extracted_text_char_count": extracted_text_char_count,
        "sanitized_text_char_count": sanitized_text_char_count,
        "extracted_text_truncated": extracted_text_truncated,
        "raw_page_text_retained": False,
        "final_evidence": False,
        "citation_eligible": False,
        "evidence_ledger_admitted": False,
        "author_activation_allowed": False,
        "evidence_boundary": _evidence_boundary(),
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


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
    best_url = handoff.get("best_verification_candidate_url")
    best_domain = handoff.get("best_verification_candidate_domain")
    if best_url or best_domain:
        return {"url": best_url, "domain": best_domain}
    return {}


def _evidence_boundary() -> dict[str, bool]:
    return {
        "read_observation_is_final_evidence": False,
        "read_observation_is_citation_eligible": False,
        "evidence_ledger_admission_performed": False,
        "evidence_ledger_admission_review_performed": False,
        "verifier_input_is_for_currentness_verification_only": True,
        "author_or_final_answer_activation_allowed": False,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_read_observation_only": True,
        "verifier_input_text_is_ephemeral": True,
        "durable_projection_retains_raw_page_text": False,
        "extracted_text_bounded": True,
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


def _normalized_text(material: Mapping[str, Any]) -> str:
    for key in ("text", "extracted_text", "page_text", "body", "content"):
        text = clean_text(material.get(key), limit=_NORMALIZE_TEXT_LIMIT)
        if text:
            return text
    return ""


def _media_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    media = content_type.split(";", 1)[0].strip()
    return media or None


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
    parsed = urlparse(value if "://" in value else f"https://{value}")
    domain = _domain(parsed.netloc)
    if not domain:
        return None
    path = parsed.path or ""
    path = path.rstrip("/")
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
        return _DEFAULT_MAX_EXTRACTED_TEXT_CHARS
    return min(_MAX_MAX_EXTRACTED_TEXT_CHARS, max(_MIN_MAX_EXTRACTED_TEXT_CHARS, limit))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "CANDIDATE_DOMAIN_MATCH",
    "CANDIDATE_DOMAIN_MISMATCH",
    "CANDIDATE_IDENTITY_UNVERIFIED",
    "CANDIDATE_URL_MATCH",
    "CANDIDATE_URL_MISMATCH",
    "EMPTY_EXTRACTED_TEXT",
    "FETCH_FAILED",
    "FETCH_READ_CURRENTNESS_VERIFICATION",
    "NOT_ATTEMPTED",
    "READ_OBSERVATION_READY",
    "READ_UNAVAILABLE",
    "RECORD_TYPE",
    "REJECT_CANDIDATE",
    "RESOLVED_URL_DIFFERS_SAME_DOMAIN",
    "SCHEMA_VERSION",
    "SCOUT_OR_QUERY_REPAIR",
    "TARGETED_FETCH_READ_RETRY",
    "as_fetch_read_currentness_verification_input",
    "build_sanitized_read_observation",
]
