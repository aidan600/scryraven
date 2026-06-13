"""Final selected authority evidence citation-survival guard for AG-94H-G.

This module consumes already-sanitized authority lifecycle, final evidence, and
post-Author citation observations. It does not retrieve, rank, classify, alter
queries, call providers, or rewrite final prose.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlunparse

FINAL_AUTHORITY_CITATION_SURVIVAL_SCHEMA_VERSION = (
    "final_authority_citation_survival_ag94h_g_v1"
)

STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_SURVIVED = "survived"
STATUS_CITATION_SURVIVAL_FAILED = "citation_survival_failed"
STATUS_SELECTED_AUTHORITY_UNCITEABLE = "selected_authority_evidence_unciteable"

REASON_NO_SELECTED_AUTHORITY_EVIDENCE = "no_final_selected_authority_evidence"
REASON_NOT_CITATION_ELIGIBLE = "selected_authority_evidence_not_citation_eligible"
REASON_SELECTED_AUTHORITY_CITED = "selected_authority_evidence_cited"
REASON_SELECTED_AUTHORITY_NOT_CITED = "selected_authority_evidence_not_cited"
REASON_SELECTED_AUTHORITY_UNCITEABLE = "selected_authority_evidence_missing_source_identity"

_OFFICIAL_OR_CANONICAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_CURRENT_LEGAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
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
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "token",
)
_PROTECTED_MARKERS = ("raw prompt", "raw_provider", "provider_payload", "secret")


@dataclass(frozen=True, slots=True)
class AuthorEvidenceVisibilityResult:
    """Author evidence with selected authority evidence appended when needed."""

    author_evidence: tuple[dict[str, Any], ...]
    appended_authority_evidence: tuple[dict[str, Any], ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FinalAuthorityCitationSurvivalObservation:
    """Packet/bundle-derived final authority citation-survival observation."""

    projection: dict[str, Any]
    final_answer_source_telemetry: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FinalAuthorityAuthorEvidenceHandoff:
    """Author evidence values after selected-authority visibility repair."""

    author_evidence: list[dict[str, Any]]
    author_evidence_block: str
    diagnostics: dict[str, Any]


def attach_selected_authority_evidence_to_final_bundle(
    bundle: Any,
    *,
    precision_count: int,
) -> AuthorEvidenceVisibilityResult:
    """Attach Author evidence from bundle-owned authority visibility state."""

    from core.final_evidence_bundle_builder import (
        attach_author_evidence,
        build_author_evidence_block,
    )

    attach_author_evidence(bundle, precision_count=precision_count)
    visibility = ensure_selected_authority_evidence_visible_to_author(
        authority_lifecycle_trace=bundle.authority_visibility_trace,
        final_evidence=bundle.final_top_evidence,
        author_evidence=bundle.author_evidence,
    )
    bundle.author_evidence = list(visibility.author_evidence)
    bundle.author_evidence_block = build_author_evidence_block(bundle.author_evidence)
    return visibility


def attach_selected_authority_evidence_handoff(
    bundle: Any,
    *,
    precision_count: int,
    active_source_class_recovery_lifecycle: dict[str, Any],
) -> FinalAuthorityAuthorEvidenceHandoff:
    """Attach selected authority evidence and record the existing lifecycle trace."""

    visibility = attach_selected_authority_evidence_to_final_bundle(
        bundle,
        precision_count=precision_count,
    )
    active_source_class_recovery_lifecycle[
        "final_authority_author_evidence_visibility"
    ] = dict(visibility.diagnostics)
    return FinalAuthorityAuthorEvidenceHandoff(
        author_evidence=list(bundle.author_evidence),
        author_evidence_block=str(bundle.author_evidence_block or ""),
        diagnostics=dict(visibility.diagnostics),
    )


def ensure_selected_authority_evidence_visible_to_author(
    *,
    authority_lifecycle_trace: Mapping[str, Any] | None,
    final_evidence: Sequence[Mapping[str, Any]],
    author_evidence: Sequence[Mapping[str, Any]],
) -> AuthorEvidenceVisibilityResult:
    """Append selected citeable authority evidence to Author evidence if absent."""

    lifecycle = _safe_mapping(authority_lifecycle_trace)
    selected_records = _selected_authority_records(lifecycle)
    existing = [_safe_mapping(item) for item in author_evidence if isinstance(item, Mapping)]
    final_records = [_safe_mapping(item) for item in final_evidence if isinstance(item, Mapping)]
    existing_keys = set().union(*(_identity_keys(item) for item in existing)) if existing else set()
    appended: list[dict[str, Any]] = []

    for selected in selected_records:
        if _citation_state(lifecycle) != "eligible":
            continue
        matched = _matching_final_evidence(selected, final_records)
        if not matched or not _official_or_canonical(selected, matched):
            continue
        if _identity_keys(matched) & existing_keys:
            continue
        existing.append(dict(matched))
        existing_keys.update(_identity_keys(matched))
        appended.append(dict(matched))

    diagnostics = {
        "schema_version": FINAL_AUTHORITY_CITATION_SURVIVAL_SCHEMA_VERSION,
        "selected_authority_evidence_count": len(selected_records),
        "appended_authority_evidence_count": len(appended),
        "author_evidence_authority_visibility_repaired": bool(appended),
    }
    return AuthorEvidenceVisibilityResult(
        author_evidence=tuple(existing),
        appended_authority_evidence=tuple(appended),
        diagnostics=diagnostics,
    )


def build_post_author_citation_survival_handoff(
    *,
    report: str,
    economist_safety_telemetry: Mapping[str, Any] | None,
    final_evidence_bundle: Any,
) -> FinalAuthorityCitationSurvivalObservation:
    """Build final-answer source telemetry and selected-authority survival facts."""

    from core.post_author_output_projection import _final_answer_source_citation_telemetry

    final_answer_source_telemetry = _final_answer_source_citation_telemetry(
        report,
        dict(economist_safety_telemetry or {}),
    )
    return build_final_authority_citation_survival_observation_from_bundle(
        final_evidence_bundle,
        final_answer_source_telemetry=final_answer_source_telemetry,
    )


def build_final_authority_citation_survival_projection(
    *,
    authority_lifecycle_trace: Mapping[str, Any] | None,
    final_evidence: Sequence[Mapping[str, Any]],
    author_evidence: Sequence[Mapping[str, Any]] | None,
    final_answer_source_ids: Sequence[Any] | None,
) -> dict[str, Any]:
    """Return citation-survival diagnostics for final selected authority evidence."""

    lifecycle = _safe_mapping(authority_lifecycle_trace)
    selected_records = _selected_authority_records(lifecycle)
    citation_state = _citation_state(lifecycle)
    final_records = [_safe_mapping(item) for item in final_evidence if isinstance(item, Mapping)]
    author_records = [_safe_mapping(item) for item in (author_evidence or ()) if isinstance(item, Mapping)]
    cited_ids = {_clean_token(item) for item in final_answer_source_ids or () if _clean_token(item)}

    citeable: list[dict[str, Any]] = []
    unciteable: list[dict[str, Any]] = []
    cited: list[dict[str, Any]] = []
    author_visible: list[dict[str, Any]] = []
    official_current_legal_cited = 0

    for selected in selected_records:
        matched = _matching_final_evidence(selected, final_records)
        official_or_canonical = _official_or_canonical(selected, matched)
        if citation_state != "eligible" or not official_or_canonical:
            continue
        source_id = _first_text((matched or selected), "source_id")
        url = _first_text((matched or selected), "url", "source_url", "accepted_url")
        resolved = _compact(
            {
                "evidence_id": _first_text(selected, "evidence_id", "candidate_id"),
                "candidate_id": _first_text(selected, "candidate_id"),
                "source_id": source_id,
                "url": url,
                "source_class": _source_class(selected, matched),
                "source_tier": _source_tier(selected, matched),
                "requirement_id": _first_text(selected, "requirement_id"),
            }
        )
        if not source_id or not url:
            unciteable.append(resolved or dict(selected))
            continue
        citeable.append(resolved)
        if _record_visible_in(resolved, author_records):
            author_visible.append(resolved)
        if _clean_token(source_id) in cited_ids:
            cited.append(resolved)
            if _source_class(selected, matched) in _OFFICIAL_CURRENT_LEGAL_CLASSES:
                official_current_legal_cited += 1

    if not selected_records:
        status = STATUS_NOT_APPLICABLE
        reason = REASON_NO_SELECTED_AUTHORITY_EVIDENCE
    elif citation_state != "eligible":
        status = STATUS_NOT_APPLICABLE
        reason = REASON_NOT_CITATION_ELIGIBLE
    elif unciteable and not citeable:
        status = STATUS_SELECTED_AUTHORITY_UNCITEABLE
        reason = REASON_SELECTED_AUTHORITY_UNCITEABLE
    elif cited:
        status = STATUS_SURVIVED
        reason = REASON_SELECTED_AUTHORITY_CITED
    else:
        status = STATUS_CITATION_SURVIVAL_FAILED
        reason = REASON_SELECTED_AUTHORITY_NOT_CITED

    completion_blocked = status in {
        STATUS_CITATION_SURVIVAL_FAILED,
        STATUS_SELECTED_AUTHORITY_UNCITEABLE,
    }
    return {
        "schema_version": FINAL_AUTHORITY_CITATION_SURVIVAL_SCHEMA_VERSION,
        "status": status,
        "reason": reason,
        "completion_blocked": completion_blocked,
        "selected_authority_evidence_count": len(selected_records),
        "citation_eligible_selected_authority_evidence_count": (
            len(selected_records) if citation_state == "eligible" else 0
        ),
        "citeable_selected_authority_evidence_count": len(citeable),
        "unciteable_selected_authority_evidence_count": len(unciteable),
        "author_visible_selected_authority_evidence_count": len(author_visible),
        "final_cited_selected_authority_evidence_count": len(cited),
        "final_citation_official_current_legal_count": official_current_legal_cited,
        "final_answer_source_ids_used": sorted(cited_ids),
        "citeable_selected_authority_source_ids": [
            item["source_id"] for item in citeable if item.get("source_id")
        ],
        "missing_selected_authority_source_ids": [
            item["source_id"]
            for item in citeable
            if item.get("source_id") and _clean_token(item.get("source_id")) not in cited_ids
        ],
        "unciteable_selected_authority_evidence": unciteable,
        "weak_fallback_masking_guard_triggered": completion_blocked and bool(cited_ids),
        "aggregate_counts_used_as_proof": False,
        "diagnostic_only": False,
    }


def build_final_authority_citation_survival_observation_from_bundle(
    bundle: Any,
    *,
    final_answer_source_telemetry: Mapping[str, Any],
) -> FinalAuthorityCitationSurvivalObservation:
    """Return citation-survival projection and flattened telemetry from bundle state."""

    projection = build_final_authority_citation_survival_projection(
        authority_lifecycle_trace=bundle.authority_visibility_trace,
        final_evidence=bundle.final_top_evidence,
        author_evidence=bundle.author_evidence,
        final_answer_source_ids=final_answer_source_telemetry.get(
            "final_answer_source_ids_used"
        ),
    )
    return FinalAuthorityCitationSurvivalObservation(
        projection=projection,
        final_answer_source_telemetry={
            **dict(final_answer_source_telemetry),
            **final_authority_citation_survival_trace_fields(projection),
        },
    )


def apply_authority_citation_survival_outcome_guard(
    *,
    projection: Mapping[str, Any],
    useful_content: bool,
    useful_content_reason: str,
    response_displayable: bool,
    evidence_sufficient: bool,
    answer_class: str,
    failure_card_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Downgrade answer-ready posture when selected authority citation fails."""

    if not projection.get("completion_blocked"):
        return {
            "useful_content": useful_content,
            "useful_content_reason": useful_content_reason,
            "response_displayable": response_displayable,
            "evidence_sufficient": evidence_sufficient,
            "answer_class": answer_class,
            "failure_card_payload": dict(failure_card_payload),
        }
    reason = str(projection.get("reason") or REASON_SELECTED_AUTHORITY_NOT_CITED)
    payload = dict(failure_card_payload or {})
    payload.update(
        {
            "show": True,
            "reason": reason,
            "authority_citation_survival_status": projection.get("status"),
            "authority_citation_survival_failed": True,
        }
    )
    return {
        "useful_content": False,
        "useful_content_reason": reason,
        "response_displayable": bool(response_displayable),
        "evidence_sufficient": False,
        "answer_class": "partial_answer",
        "failure_card_payload": payload,
    }


def final_authority_citation_survival_trace_fields(
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Flatten survival diagnostics for existing execution-trace consumers."""

    return {
        "final_authority_citation_survival": dict(projection),
        "final_authority_citation_survival_status": projection.get("status"),
        "final_authority_citation_survival_reason": projection.get("reason"),
        "final_authority_citation_survival_completion_blocked": bool(
            projection.get("completion_blocked")
        ),
        "final_authority_citation_survival_weak_fallback_masking_guard": bool(
            projection.get("weak_fallback_masking_guard_triggered")
        ),
        "final_citation_official_current_legal_count": projection.get(
            "final_citation_official_current_legal_count",
            0,
        ),
    }


def _selected_authority_records(trace: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    authority = _safe_mapping(trace.get("authority_lifecycle"))
    candidate_fit = _safe_mapping(authority.get("candidate_fit"))
    for source in (
        candidate_fit.get("selected_authority_evidence"),
        trace.get("authority_lifecycle_selected_authority_evidence"),
        trace.get("selected_authority_evidence"),
    ):
        records.extend(_record_list(source))
    return tuple(_dedupe_records(records))


def _citation_state(trace: Mapping[str, Any]) -> str:
    authority = _safe_mapping(trace.get("authority_lifecycle"))
    return _clean_token(
        authority.get("citation_eligibility_state")
        or trace.get("citation_eligibility_state")
    )


def _matching_final_evidence(
    selected: Mapping[str, Any],
    final_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected_keys = _identity_keys(selected)
    for record in final_records:
        if selected_keys & _identity_keys(record):
            return dict(record)
    return {}


def _record_visible_in(
    record: Mapping[str, Any],
    surfaces: Sequence[Mapping[str, Any]],
) -> bool:
    keys = _identity_keys(record)
    return any(keys & _identity_keys(surface) for surface in surfaces)


def _identity_keys(record: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("candidate_id", "evidence_id", "source_id"):
        value = _clean_text(record.get(key), limit=240)
        if value:
            keys.add(f"id:{value.casefold()}")
    url = _normalize_url(record.get("url") or record.get("source_url") or record.get("accepted_url"))
    if url:
        keys.add(f"url:{url}")
    title = _clean_text(record.get("title"), limit=180)
    if title and not url:
        keys.add(f"title:{title.casefold()}")
    return keys


def _official_or_canonical(
    selected: Mapping[str, Any],
    final_record: Mapping[str, Any] | None,
) -> bool:
    return (
        _source_class(selected, final_record) in _OFFICIAL_OR_CANONICAL_CLASSES
        or _source_tier(selected, final_record) in _OFFICIAL_OR_CANONICAL_TIERS
    )


def _source_class(
    selected: Mapping[str, Any],
    final_record: Mapping[str, Any] | None,
) -> str:
    final = final_record or {}
    return _clean_token(
        selected.get("source_class")
        or selected.get("observed_source_class")
        or final.get("source_class")
        or selected.get("required_source_class")
        or selected.get("required_authority")
    )


def _source_tier(
    selected: Mapping[str, Any],
    final_record: Mapping[str, Any] | None,
) -> str:
    final = final_record or {}
    return _clean_token(selected.get("source_tier") or final.get("source_tier"))


def _first_text(source: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = _clean_text(source.get(key), limit=300)
        if text:
            return text
    return ""


def _record_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            out.append(_safe_mapping(item))
    return out


def _dedupe_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        keys = sorted(_identity_keys(record))
        key = "|".join(keys) or repr(sorted(record.items()))
        if key in seen:
            continue
        out.append(dict(record))
        seen.add(key)
    return out


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
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=500)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in list(value)[:50]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:50]]
    return _clean_text(value, limit=300)


def _safe_url(value: Any) -> str:
    return _clean_text(value, limit=500)


def _normalize_url(value: Any) -> str:
    raw = _safe_url(value)
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return raw.casefold().rstrip("/")
    path = (parsed.path or "").rstrip("/")
    return urlunparse(("https", host, path, "", parsed.query, "")).casefold()


def _clean_text(value: Any, *, limit: int) -> str:
    if value is None:
        return ""
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any) -> str:
    text = _clean_text(value, limit=120)
    return text.casefold().replace("-", "_").replace(" ", "_") if text else ""


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").strip().casefold()
    return text.startswith("raw_") or any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "FINAL_AUTHORITY_CITATION_SURVIVAL_SCHEMA_VERSION",
    "STATUS_CITATION_SURVIVAL_FAILED",
    "STATUS_NOT_APPLICABLE",
    "STATUS_SELECTED_AUTHORITY_UNCITEABLE",
    "STATUS_SURVIVED",
    "AuthorEvidenceVisibilityResult",
    "FinalAuthorityAuthorEvidenceHandoff",
    "FinalAuthorityCitationSurvivalObservation",
    "apply_authority_citation_survival_outcome_guard",
    "attach_selected_authority_evidence_handoff",
    "attach_selected_authority_evidence_to_final_bundle",
    "build_final_authority_citation_survival_observation_from_bundle",
    "build_final_authority_citation_survival_projection",
    "build_post_author_citation_survival_handoff",
    "ensure_selected_authority_evidence_visible_to_author",
    "final_authority_citation_survival_trace_fields",
]
