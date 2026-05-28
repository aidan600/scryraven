"""AG-73A Authority Candidate Passport diagnostic projection.

This module is a passive, trace-safe custody view over already-sanitized
candidate lifecycle facts. It does not retrieve, route providers, rank/filter,
classify, fit, preserve, cite, prompt, or alter final-answer behavior.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

AUTHORITY_CANDIDATE_PASSPORT_SCHEMA_VERSION = (
    "authority_candidate_passport_ag73a_v1"
)
AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY = "authority_candidate_passport_projection"

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_LIST_ITEMS = 20
_MAX_QUERY_CHARS = 140
_MAX_TITLE_CHARS = 180
_MAX_REASON_CHARS = 160
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
_LOWER_TIER_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "context", "analysis"}
)
_LOWER_TIER_CLASSES = frozenset({"secondary", "secondary_only", "context"})
_SURFACE_KEYS = (
    "controller_visible",
    "answer_contract_visible",
    "context_packet_visible",
    "analyst_visible",
    "author_visible",
    "citation_eligible",
    "cited_in_final_answer",
)
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


def build_authority_candidate_passport_projection(
    *,
    lifecycle_trace: Mapping[str, Any] | None,
    recovered_passages: Iterable[Mapping[str, Any]] | None = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    visibility_export: Mapping[str, Any] | None = None,
    surface_visibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build candidate-level custody passports from existing diagnostic facts."""

    trace = _safe_mapping(lifecycle_trace)
    authority = _safe_mapping(trace.get("authority_lifecycle"))
    candidate_fit = _safe_mapping(authority.get("candidate_fit"))
    requirement_id = _requirement_id(trace, authority)
    required_source_class = _required_source_class(trace, authority)
    required_authority = (
        _clean_text(authority.get("required_authority"), limit=80)
        or required_source_class
        or requirement_id
    )
    query_preview = _query_preview(trace)
    surface_sets = _surface_sets(surface_visibility)

    selected_records = _record_list(
        candidate_fit.get("selected_authority_evidence")
        or trace.get("authority_lifecycle_selected_authority_evidence")
    )
    rejection_records = _record_list(
        candidate_fit.get("structured_rejections")
        or trace.get("authority_lifecycle_candidate_rejections")
    )
    selected_by_key = _records_by_identity(selected_records)
    rejected_by_key = _records_by_identity(rejection_records)
    candidates = _candidate_sources(
        trace=trace,
        candidate_fit=candidate_fit,
        recovered_passages=recovered_passages,
        final_top_evidence=final_top_evidence,
        selected_records=selected_records,
        rejection_records=rejection_records,
    )

    passports: list[dict[str, Any]] = []
    for source in candidates:
        identity_keys = _identity_keys(source)
        selected = _first_identity_record(identity_keys, selected_by_key)
        rejection = _first_identity_record(identity_keys, rejected_by_key)
        passports.append(
            _build_passport(
                source=source,
                selected=selected,
                rejection=rejection,
                trace=trace,
                authority=authority,
                requirement_id=requirement_id,
                required_authority=required_authority,
                required_source_class=required_source_class,
                query_preview=query_preview,
                surface_sets=surface_sets,
            )
        )

    aggregate_counts = _aggregate_counts(passports)
    aggregate_reconciliation = _aggregate_reconciliation(
        aggregate_counts=aggregate_counts,
        trace=trace,
        visibility_export=_safe_mapping(visibility_export),
    )
    silent_drop_ids = [
        passport["candidate_id"]
        for passport in passports
        if not _has_durable_disposition(passport)
    ]

    return {
        "schema_version": AUTHORITY_CANDIDATE_PASSPORT_SCHEMA_VERSION,
        "trace_key": AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
        "diagnostic_only": True,
        "sanitized": True,
        "consumer": (
            "AG-73A authority custody review and future AG-73B/AG-74 repair gates"
        ),
        "decision_enabled": (
            "Identify the first visible custody stage where a represented "
            "official/current authority candidate is rejected, hidden, lost, "
            "or promoted."
        ),
        "deletion_or_promotion_criterion": (
            "Promote into the runtime visibility export if future live "
            "validation requires report-visible per-candidate custody; delete "
            "or fold into lifecycle visibility tests once downstream custody "
            "exports expose equivalent durable dispositions."
        ),
        "requirement_id": requirement_id,
        "required_source_class": required_source_class,
        "passport_count": len(passports),
        "passports": passports,
        "aggregate_counts": aggregate_counts,
        "aggregate_reconciliation": aggregate_reconciliation,
        "passport_counts_reconcile": aggregate_reconciliation["reconciled"],
        "silent_drop_candidate_ids": silent_drop_ids,
        "passport_integrity_status": (
            "complete" if not silent_drop_ids else "silent_drop_detected"
        ),
        "behavior_changed": False,
    }


def assert_authority_candidate_passport_integrity(
    projection: Mapping[str, Any],
) -> None:
    """Raise when a represented candidate lacks a durable custody disposition."""

    silent_drop_ids = projection.get("silent_drop_candidate_ids")
    if isinstance(silent_drop_ids, list) and silent_drop_ids:
        joined = ", ".join(str(item) for item in silent_drop_ids)
        raise AssertionError(
            "Authority Candidate Passport silent-drop candidates: " + joined
        )


def _candidate_sources(
    *,
    trace: Mapping[str, Any],
    candidate_fit: Mapping[str, Any],
    recovered_passages: Iterable[Mapping[str, Any]] | None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
    selected_records: list[dict[str, Any]],
    rejection_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for source in recovered_passages or ():
        if isinstance(source, Mapping):
            _append_candidate(candidates, _safe_mapping(source))
    for source in final_top_evidence or ():
        if not isinstance(source, Mapping):
            continue
        candidate = _safe_mapping(source)
        if _matches_any_record(candidate, selected_records):
            candidate["final_top_evidence_visible"] = True
            _append_candidate(candidates, candidate)
    for record in selected_records:
        _append_candidate(candidates, _candidate_from_selected(record))
    for record in rejection_records:
        _append_candidate(candidates, _candidate_from_rejection(record))

    if not candidates and _positive_int(candidate_fit.get("accepted_url_count")):
        _append_candidate(
            candidates,
            {
                "candidate_id": "accepted-url-without-readable-candidate",
                "readability_status": "unreadable",
                "rejection_reason": "accepted_url_without_readable_candidate_data",
            },
        )
    if not candidates and _positive_int(trace.get("recovered_accepted_url_count")):
        _append_candidate(
            candidates,
            {
                "candidate_id": "accepted-url-without-readable-candidate",
                "readability_status": "unreadable",
                "rejection_reason": "accepted_url_without_readable_candidate_data",
            },
        )
    return candidates


def _append_candidate(candidates: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    keys = _identity_keys(candidate)
    for existing in candidates:
        existing_keys = _identity_keys(existing)
        if keys and existing_keys and keys & existing_keys:
            for key, value in candidate.items():
                existing.setdefault(key, value)
            return
    candidates.append(candidate)


def _candidate_from_selected(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _clean_text(record.get("candidate_id"), limit=80)
        or _clean_text(record.get("evidence_id"), limit=160),
        "source_id": _clean_text(record.get("evidence_id"), limit=160),
        "url": _clean_text(record.get("url"), limit=240),
        "source_class": _clean_text(record.get("observed_source_class"), limit=80),
        "satisfies_authority": record.get("satisfies_authority"),
        "fit_state": "matched_selected",
    }


def _candidate_from_rejection(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _clean_text(record.get("candidate_id"), limit=160),
        "url": _clean_text(record.get("url"), limit=240),
        "source_class": _clean_text(record.get("observed_source_class"), limit=80),
        "rejection_reason": _clean_text(
            record.get("rejection_reason"),
            limit=_MAX_REASON_CHARS,
        ),
        "rejection_owner": _clean_text(record.get("rejection_owner"), limit=80),
        "fit_state": "rejected_with_reason",
    }


def _build_passport(
    *,
    source: Mapping[str, Any],
    selected: Mapping[str, Any] | None,
    rejection: Mapping[str, Any] | None,
    trace: Mapping[str, Any],
    authority: Mapping[str, Any],
    requirement_id: str,
    required_authority: str,
    required_source_class: str,
    query_preview: str,
    surface_sets: Mapping[str, set[str]] | None,
) -> dict[str, Any]:
    source_url = _clean_text(source.get("url") or source.get("source_url"), limit=240)
    normalized_url = _normalize_url(source_url)
    normalized_domain = _normalized_domain(source_url)
    title = _clean_text(source.get("title"), limit=_MAX_TITLE_CHARS)
    candidate_id = _candidate_id(source, normalized_url=normalized_url, title=title)
    source_tier = _clean_token(source.get("source_tier")) or UNKNOWN
    source_class = _clean_token(
        source.get("source_class")
        or source.get("observed_source_class")
        or (selected or {}).get("observed_source_class")
        or (rejection or {}).get("observed_source_class")
    ) or UNKNOWN
    readable_text_available = _readable_text_available(source, selected=selected)
    readability_status = _readability_status(source, readable_text_available)
    provider_returned = _bool_field(source.get("provider_returned"))
    if provider_returned == UNKNOWN:
        provider_returned = True
    fit_state = _fit_state(source, selected=selected, rejection=rejection)
    surfaces = {
        key: _surface_state(
            key=key,
            source=source,
            surface_sets=surface_sets,
            candidate_id=candidate_id,
            source_url=source_url,
            selected=selected,
            rejection=rejection,
            authority=authority,
        )
        for key in _SURFACE_KEYS
    }
    rejection_reason = (
        _clean_text((rejection or {}).get("rejection_reason"), limit=_MAX_REASON_CHARS)
        or _clean_text(source.get("rejection_reason"), limit=_MAX_REASON_CHARS)
    )
    mismatch_reason = (
        _clean_text(source.get("mismatch_reason"), limit=_MAX_REASON_CHARS)
        or rejection_reason
    )
    lower_tier = _lower_tier_context(source_tier=source_tier, source_class=source_class)
    satisfies_authority = _satisfies_authority(
        source=source,
        selected=selected,
        lower_tier=lower_tier,
        source_class=source_class,
        required_source_class=required_source_class,
    )
    disposition = _final_disposition(
        source=source,
        selected=selected,
        rejection=rejection,
        source_tier=source_tier,
        source_class=source_class,
        required_source_class=required_source_class,
        readability_status=readability_status,
        readable_text_available=readable_text_available,
        fit_state=fit_state,
        rejection_reason=rejection_reason,
        lower_tier=lower_tier,
        surfaces=surfaces,
    )
    if not rejection_reason and disposition["durable_reason"]:
        rejection_reason = disposition["durable_reason"]

    return {
        "candidate_id": candidate_id,
        "requirement_id": requirement_id,
        "required_source_class": required_source_class,
        "required_authority": required_authority,
        "source_url": source_url,
        "normalized_domain": normalized_domain,
        "title": title,
        "provider_name": _clean_text(source.get("provider_name"), limit=80)
        or UNKNOWN,
        "provider_role": _clean_text(
            source.get("provider_role")
            or source.get("_provider_role")
            or trace.get("active_source_class_recovery_provider_role"),
            limit=80,
        )
        or UNKNOWN,
        "query_preview": _clean_text(
            source.get("query_preview") or source.get("query") or query_preview,
            limit=_MAX_QUERY_CHARS,
        )
        or UNKNOWN,
        "retrieval_pass_id": _clean_text(
            source.get("retrieval_pass_id") or source.get("retrieval_stage"),
            limit=80,
        )
        or UNKNOWN,
        "provider_returned": provider_returned,
        "provider_rank_or_position": _safe_position(source),
        "accepted_url": _clean_text(source.get("accepted_url"), limit=240)
        or source_url,
        "deduped_against_candidate_id": _clean_text(
            source.get("deduped_against_candidate_id"),
            limit=160,
        ),
        "readability_status": readability_status,
        "readable_text_available": readable_text_available,
        "source_tier": source_tier,
        "source_class": source_class,
        "classification_reason": _clean_text(
            source.get("classification_reason"),
            limit=_MAX_REASON_CHARS,
        )
        or UNKNOWN,
        "official_domain_signal": _official_domain_signal(
            source=source,
            source_tier=source_tier,
            normalized_domain=normalized_domain,
        ),
        "currentness_signal": _clean_text(
            source.get("currentness_signal"),
            limit=_MAX_REASON_CHARS,
        )
        or UNKNOWN,
        "temporal_anchor_required": _clean_text(
            source.get("temporal_anchor_required")
            or source.get("current_anchor_required")
            or authority.get("current_anchor")
            or authority.get("temporal_anchor"),
            limit=_MAX_REASON_CHARS,
        )
        or UNKNOWN,
        "temporal_anchor_observed": _clean_text(
            source.get("temporal_anchor_observed")
            or source.get("current_anchor_observed")
            or source.get("temporal_anchor"),
            limit=_MAX_REASON_CHARS,
        )
        or UNKNOWN,
        "claim_value_extraction_status": _clean_text(
            source.get("claim_value_extraction_status")
            or source.get("value_extraction_status"),
            limit=80,
        )
        or UNKNOWN,
        "fit_state": fit_state,
        "satisfies_authority": satisfies_authority,
        "mismatch_reason": mismatch_reason,
        "rejection_reason": rejection_reason,
        "rejection_owner": _clean_text(
            (rejection or {}).get("rejection_owner") or source.get("rejection_owner"),
            limit=80,
        ),
        "final_disposition": disposition["final_disposition"],
        "first_missing_stage": disposition["first_missing_stage"],
        **surfaces,
    }


def _final_disposition(
    *,
    source: Mapping[str, Any],
    selected: Mapping[str, Any] | None,
    rejection: Mapping[str, Any] | None,
    source_tier: str,
    source_class: str,
    required_source_class: str,
    readability_status: str,
    readable_text_available: bool,
    fit_state: str,
    rejection_reason: str | None,
    lower_tier: bool,
    surfaces: Mapping[str, Any],
) -> dict[str, str | None]:
    if selected is not None:
        if (
            surfaces["controller_visible"] is False
            or surfaces["answer_contract_visible"] is False
        ):
            return _disposition(
                "accepted_but_lost_before_controller_answer_contract",
                "controller_answer_contract",
                "accepted_candidate_not_visible_to_controller_or_answer_contract",
            )
        if surfaces["context_packet_visible"] is False:
            return _disposition(
                "final_selected_context_exposure_missing",
                "context_packet",
                "context_packet_not_visible",
            )
        if (
            surfaces["analyst_visible"] is False
            or surfaces["author_visible"] is False
            or surfaces["cited_in_final_answer"] is False
        ):
            return _disposition(
                "analyst_author_citation_surface_missing",
                "analyst_author_citation_surface",
                "analyst_author_or_citation_surface_not_visible",
            )
        return _disposition("promoted_final_authority_evidence", None, None)

    if rejection is not None or rejection_reason:
        reason = rejection_reason or "candidate_rejected_with_reason"
        return _disposition("rejected", _stage_for_reason(reason), reason)

    if readability_status in {"unreadable", "readability_failed"} or (
        readable_text_available is False
        and _official_looking(
            source=source,
            source_tier=source_tier,
            normalized_domain=_normalized_domain(source.get("url")),
        )
    ):
        return _disposition("rejected", "readability", "readability_failed")

    if lower_tier:
        return _disposition(
            "rejected",
            "source_class_or_tier",
            "secondary_or_lower_tier_not_satisfying_authority",
        )

    if _official_looking(
        source=source,
        source_tier=source_tier,
        normalized_domain=_normalized_domain(source.get("url")),
    ) and not _source_class_matches(source_class, required_source_class):
        return _disposition(
            "rejected",
            "source_class_classification",
            "source_class_mismatch",
        )

    if _source_class_matches(source_class, required_source_class) and fit_state in {
        "no_matching_source_fit",
        "rejected_with_reason",
    }:
        return _disposition(
            "rejected",
            "candidate_fit_currentness",
            rejection_reason or "candidate_fit_rejected",
        )

    if fit_state in {"matched_selected", "accepted"} or source.get("accepted_url"):
        return _disposition(
            "accepted_but_lost_before_controller_answer_contract",
            "controller_answer_contract",
            "accepted_candidate_not_visible_to_controller_or_answer_contract",
        )

    return _disposition(
        "represented_without_durable_disposition",
        UNKNOWN,
        None,
    )


def _disposition(
    final_disposition: str,
    first_missing_stage: str | None,
    durable_reason: str | None,
) -> dict[str, str | None]:
    return {
        "final_disposition": final_disposition,
        "first_missing_stage": first_missing_stage,
        "durable_reason": durable_reason,
    }


def _stage_for_reason(reason: str | None) -> str:
    text = (reason or "").casefold()
    if "read" in text:
        return "readability"
    if "class" in text or "tier" in text or "secondary" in text:
        return "source_class_or_tier"
    if "current" in text or "historical" in text or "archival" in text:
        return "candidate_fit_currentness"
    if "duplicate" in text or "dedupe" in text or "already_visible" in text:
        return "dedupe"
    if "final_evidence" in text or "cap" in text:
        return "final_evidence_selection"
    if "context" in text:
        return "context_packet"
    if "citation" in text or "author" in text or "analyst" in text:
        return "analyst_author_citation_surface"
    return "candidate_fit_currentness"


def _aggregate_counts(passports: list[Mapping[str, Any]]) -> dict[str, int]:
    returned = [
        item
        for item in passports
        if item.get("provider_returned") is True
        or item.get("fit_state") not in {UNKNOWN, "not_evaluated"}
    ]
    rejected = [
        item
        for item in passports
        if item.get("final_disposition") == "rejected"
    ]
    selected = [
        item
        for item in passports
        if item.get("fit_state") == "matched_selected"
        or item.get("final_disposition") == "promoted_final_authority_evidence"
    ]
    accepted_readable = [
        item
        for item in selected
        if item.get("satisfies_authority") is True
        and item.get("readable_text_available") is not False
    ]
    lower_tier = [
        item
        for item in passports
        if item.get("source_tier") in _LOWER_TIER_TIERS
        and item.get("satisfies_authority") is False
    ]
    official_or_canonical = [
        item
        for item in passports
        if not _lower_tier_context(
            source_tier=str(item.get("source_tier") or ""),
            source_class=str(item.get("source_class") or ""),
        )
        and (
            item.get("source_class") in _OFFICIAL_OR_CANONICAL_CLASSES
            or item.get("source_tier") in _OFFICIAL_OR_CANONICAL_TIERS
        )
    ]
    lost = [
        item
        for item in passports
        if str(item.get("final_disposition") or "").startswith("accepted_but_lost")
        or "missing" in str(item.get("final_disposition") or "")
    ]
    return {
        "represented_candidate_count": len(passports),
        "returned_or_evaluated_count": len(returned),
        "official_or_canonical_candidate_count": len(official_or_canonical),
        "rejected_candidate_count": len(rejected),
        "accepted_readable_authority_evidence_count": len(accepted_readable),
        "final_selected_authority_evidence_count": len(selected),
        "lower_tier_non_satisfying_count": len(lower_tier),
        "lost_after_acceptance_or_selection_count": len(lost),
    }


def _aggregate_reconciliation(
    *,
    aggregate_counts: Mapping[str, int],
    trace: Mapping[str, Any],
    visibility_export: Mapping[str, Any],
) -> dict[str, Any]:
    observed = {**trace, **visibility_export}
    checks = {
        "returned_or_evaluated_official_or_canonical_count": (
            "returned_or_evaluated_count",
            (
                observed.get("returned_or_evaluated_official_or_canonical_count"),
                observed.get("recovered_visibility_returned_or_evaluated_candidate_count"),
                observed.get("authority_lifecycle_returned_or_evaluated_candidate_count"),
            ),
        ),
        "candidate_official_or_canonical_count": (
            "official_or_canonical_candidate_count",
            (
                observed.get("candidate_official_or_canonical_count"),
                observed.get("recovered_visibility_source_fit_candidate_count"),
            ),
        ),
        "rejected_official_or_canonical_candidate_count": (
            "rejected_candidate_count",
            (
                observed.get("rejected_official_or_canonical_candidate_count"),
                observed.get("recovered_visibility_rejected_candidate_count"),
                observed.get("authority_lifecycle_rejected_candidate_count"),
            ),
        ),
        "accepted_readable_authority_evidence_count": (
            "accepted_readable_authority_evidence_count",
            (
                observed.get("accepted_readable_authority_evidence_count"),
                observed.get(
                    "recovered_visibility_accepted_readable_authority_evidence_count"
                ),
                observed.get(
                    "authority_lifecycle_accepted_readable_authority_evidence_count"
                ),
            ),
        ),
        "final_selected_authority_evidence_count": (
            "final_selected_authority_evidence_count",
            (
                observed.get("final_selected_authority_evidence_count"),
                observed.get(
                    "recovered_visibility_final_selected_authority_evidence_count"
                ),
                observed.get(
                    "authority_lifecycle_final_selected_authority_evidence_count"
                ),
            ),
        ),
    }
    details: dict[str, dict[str, Any]] = {}
    reconciled = True
    for export_key, (count_key, candidates) in checks.items():
        observed_count = _first_known_int(*candidates)
        passport_count = aggregate_counts[count_key]
        field_reconciled = (
            observed_count in {UNKNOWN, NOT_OBSERVABLE}
            or observed_count == passport_count
        )
        if not field_reconciled:
            reconciled = False
        details[export_key] = {
            "aggregate_count": observed_count,
            "passport_count": passport_count,
            "reconciled": field_reconciled,
        }
    return {"reconciled": reconciled, "fields": details}


def _has_durable_disposition(passport: Mapping[str, Any]) -> bool:
    disposition = _clean_text(passport.get("final_disposition"), limit=80)
    reason = _clean_text(passport.get("rejection_reason"), limit=_MAX_REASON_CHARS)
    if disposition == "promoted_final_authority_evidence":
        return True
    if disposition and disposition != "represented_without_durable_disposition":
        return True
    return bool(reason)


def _surface_state(
    *,
    key: str,
    source: Mapping[str, Any],
    surface_sets: Mapping[str, set[str]] | None,
    candidate_id: str,
    source_url: str | None,
    selected: Mapping[str, Any] | None,
    rejection: Mapping[str, Any] | None,
    authority: Mapping[str, Any],
) -> bool | str:
    explicit = _bool_field(source.get(key))
    if explicit != UNKNOWN:
        return explicit
    if key == "controller_visible" and (selected is not None or rejection is not None):
        return True
    if key == "citation_eligible" and selected is not None:
        return authority.get("citation_eligibility_state") == "eligible"
    if surface_sets is None or key not in surface_sets:
        return UNKNOWN
    identities = _surface_identities(candidate_id, source_url)
    return bool(identities & surface_sets[key])


def _surface_sets(surface_visibility: Mapping[str, Any] | None) -> dict[str, set[str]] | None:
    if not isinstance(surface_visibility, Mapping):
        return None
    out: dict[str, set[str]] = {}
    for key in _SURFACE_KEYS:
        values: list[Any] = []
        for source_key in (
            f"{key}_candidate_ids",
            f"{key}_source_ids",
            f"{key}_urls",
            key,
        ):
            raw = surface_visibility.get(source_key)
            if isinstance(raw, (list, tuple, set)):
                values.extend(raw)
        if values:
            normalized = set()
            for value in values:
                normalized.update(_surface_identities(_clean_text(value, limit=240), value))
            out[key] = normalized
    return out


def _surface_identities(candidate_id: Any, source_url: Any) -> set[str]:
    identities: set[str] = set()
    candidate_text = _clean_text(candidate_id, limit=240)
    if candidate_text:
        identities.add(f"id:{candidate_text.casefold()}")
    normalized = _normalize_url(source_url)
    if normalized:
        identities.add(f"url:{normalized}")
    raw_url = _clean_text(source_url, limit=240)
    if raw_url and not normalized:
        identities.add(f"id:{raw_url.casefold()}")
    return identities


def _records_by_identity(records: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        safe = _safe_mapping(record)
        for key in _identity_keys(safe):
            by_key.setdefault(key, safe)
    return by_key


def _first_identity_record(
    identity_keys: set[str],
    records_by_key: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for key in identity_keys:
        if key in records_by_key:
            return records_by_key[key]
    return None


def _matches_any_record(
    source: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
) -> bool:
    source_keys = _identity_keys(source)
    return any(source_keys & _identity_keys(record) for record in records)


def _identity_keys(record: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("candidate_id", "source_id", "evidence_id"):
        value = _clean_text(record.get(key), limit=240)
        if value:
            keys.add(f"id:{value.casefold()}")
    url = _normalize_url(record.get("url") or record.get("source_url"))
    if url:
        keys.add(f"url:{url}")
    title = _clean_text(record.get("title"), limit=_MAX_TITLE_CHARS)
    if title and not url:
        keys.add(f"title:{title.casefold()}")
    return keys


def _candidate_id(
    source: Mapping[str, Any],
    *,
    normalized_url: str,
    title: str | None,
) -> str:
    for key in ("candidate_id", "source_id", "evidence_id"):
        value = _clean_text(source.get(key), limit=160)
        if value:
            return value
    basis = normalized_url or _clean_text(title, limit=_MAX_TITLE_CHARS)
    if basis:
        digest = hashlib.sha256(str(basis).encode("utf-8")).hexdigest()[:12]
        return f"candidate:{digest}"
    return "candidate:unidentified"


def _requirement_id(trace: Mapping[str, Any], authority: Mapping[str, Any]) -> str:
    return (
        _clean_text(authority.get("requirement_id"), limit=80)
        or _clean_text(trace.get("requirement_id"), limit=80)
        or _required_source_class(trace, authority)
        or "authority_requirement"
    )


def _required_source_class(trace: Mapping[str, Any], authority: Mapping[str, Any]) -> str:
    action = _safe_mapping(authority.get("recovery_action"))
    for values in (
        action.get("required_source_classes"),
        trace.get("active_source_class_recovery_missing_classes"),
    ):
        if isinstance(values, (list, tuple)) and values:
            text = _clean_token(values[0])
            if text:
                return text
    return _clean_token(authority.get("required_authority")) or "official_current_rules"


def _query_preview(trace: Mapping[str, Any]) -> str:
    for key in ("active_source_class_recovery_queries", "source_class_recovery_queries"):
        values = trace.get(key)
        if isinstance(values, (list, tuple)) and values:
            text = _clean_text(values[0], limit=_MAX_QUERY_CHARS)
            if text:
                return text
    return UNKNOWN


def _readable_text_available(
    source: Mapping[str, Any],
    *,
    selected: Mapping[str, Any] | None,
) -> bool:
    explicit = _bool_field(source.get("readable_text_available"))
    if explicit != UNKNOWN:
        return bool(explicit)
    status = _clean_token(source.get("readability_status"))
    if status in {"unreadable", "readability_failed", "failed"}:
        return False
    if selected is not None:
        return True
    return bool(_clean_text(source.get("text"), limit=1))


def _readability_status(
    source: Mapping[str, Any],
    readable_text_available: bool,
) -> str:
    explicit = _clean_token(source.get("readability_status"))
    if explicit:
        return explicit
    return "readable" if readable_text_available else "unreadable"


def _fit_state(
    source: Mapping[str, Any],
    *,
    selected: Mapping[str, Any] | None,
    rejection: Mapping[str, Any] | None,
) -> str:
    explicit = _clean_token(source.get("fit_state"))
    if explicit:
        return explicit
    if selected is not None:
        return "matched_selected"
    if rejection is not None:
        return "rejected_with_reason"
    return UNKNOWN


def _satisfies_authority(
    *,
    source: Mapping[str, Any],
    selected: Mapping[str, Any] | None,
    lower_tier: bool,
    source_class: str,
    required_source_class: str,
) -> bool:
    if lower_tier:
        return False
    explicit = _bool_field(source.get("satisfies_authority"))
    if explicit != UNKNOWN:
        return bool(explicit)
    if selected is not None:
        selected_satisfies = _bool_field(selected.get("satisfies_authority"))
        return selected_satisfies is not False
    return _source_class_matches(source_class, required_source_class) and False


def _source_class_matches(source_class: str, required_source_class: str) -> bool:
    if source_class == UNKNOWN:
        return False
    if source_class == required_source_class:
        return True
    if required_source_class == "current_primary_or_official":
        return source_class in {
            "official_current_rules",
            "legal_or_regulatory_text",
            "primary_source_documents",
        }
    return False


def _lower_tier_context(*, source_tier: str, source_class: str) -> bool:
    if source_tier in _LOWER_TIER_TIERS:
        return True
    return source_tier in {"", UNKNOWN} and source_class in _LOWER_TIER_CLASSES


def _official_looking(
    *,
    source: Mapping[str, Any],
    source_tier: str,
    normalized_domain: str,
) -> bool:
    explicit = _bool_field(source.get("official_domain_signal"))
    if explicit != UNKNOWN:
        return bool(explicit)
    return source_tier in _OFFICIAL_OR_CANONICAL_TIERS or normalized_domain.endswith(
        ".gov"
    )


def _official_domain_signal(
    *,
    source: Mapping[str, Any],
    source_tier: str,
    normalized_domain: str,
) -> bool:
    return _official_looking(
        source=source,
        source_tier=source_tier,
        normalized_domain=normalized_domain,
    )


def _safe_position(source: Mapping[str, Any]) -> int | str:
    for key in ("provider_rank_or_position", "provider_rank", "position", "rank"):
        parsed = _optional_int(source.get(key))
        if parsed != UNKNOWN:
            return parsed
    return UNKNOWN


def _record_list(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(value, (list, tuple)):
        return out
    for item in value:
        if isinstance(item, Mapping):
            out.append(_safe_mapping(item))
        if len(out) >= _MAX_LIST_ITEMS:
            break
    return out


def _normalize_url(value: Any) -> str:
    raw = _clean_text(value, limit=240)
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


def _normalized_domain(value: Any) -> str:
    raw = _clean_text(value, limit=240)
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


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


def _first_known_int(*values: Any) -> int | str:
    for value in values:
        parsed = _optional_int(value)
        if parsed != UNKNOWN:
            return parsed
    return UNKNOWN


def _optional_int(value: Any) -> int | str:
    if value is None or isinstance(value, bool):
        return UNKNOWN
    if isinstance(value, str) and value in {UNKNOWN, NOT_OBSERVABLE}:
        return UNKNOWN
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return UNKNOWN


def _positive_int(value: Any) -> bool:
    parsed = _optional_int(value)
    return isinstance(parsed, int) and parsed > 0


def _bool_field(value: Any) -> bool | str:
    if isinstance(value, bool):
        return value
    return UNKNOWN


def _clean_token(value: Any) -> str:
    return _clean_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")


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


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or any(
        marker in normalized for marker in _SENSITIVE_KEY_MARKERS
    )


__all__ = [
    "AUTHORITY_CANDIDATE_PASSPORT_SCHEMA_VERSION",
    "AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY",
    "NOT_OBSERVABLE",
    "UNKNOWN",
    "assert_authority_candidate_passport_integrity",
    "build_authority_candidate_passport_projection",
]
