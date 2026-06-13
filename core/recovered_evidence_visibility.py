"""Bounded visibility rule for contract-qualified recovered evidence.

This module is deliberately pure: it does not call retrieval, providers,
ranking, prompts, models, persistence, or orchestration code.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.authority_lifecycle_candidate_visibility import (
    project_authority_lifecycle_candidate_fit_visibility,
)
from core.source_class_recovery import _evidence_source_class_strengths
from core.source_class_recovery_candidate_stream import (
    runner_owned_recovered_candidate_stream,
)

ANSWER_CONTRACT_VISIBILITY_REASON_PREFIXES = (
    "answer_contract_official_gap",
    "answer_contract_legal_text_gap",
    "answer_contract_current_primary_gap",
)
OFFICIAL_CANONICAL_VISIBILITY_REASON_PREFIXES = (
    "official_canonical_recovery_query_acquisition",
)

CURRENT_PRIMARY_MATCH_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
    }
)
DIRECT_MATCH_CLASSES = {
    "official_current_rules": frozenset({"official_current_rules"}),
    "legal_or_regulatory_text": frozenset({"legal_or_regulatory_text"}),
    "current_primary_or_official": CURRENT_PRIMARY_MATCH_CLASSES,
}
HISTORICAL_OR_ARCHIVAL_CLASSES = frozenset(
    {"archival_primary_text", "historical_legal_text"}
)
CURRENT_SOURCE_CLASS_GAPS = frozenset(
    {"official_current_rules", "current_primary_or_official"}
)
LOWER_PRIORITY_PROTECTED_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "archival_primary_text",
        "historical_legal_text",
        "issuer_filings_or_company_materials",
    }
)
DISQUALIFYING_QUALITY_STATUSES = frozenset(
    {"secondary_only", "no_relevant_sources", "classification_mismatch"}
)
_ANSWER_BEARING_OBLIGATION_PATTERNS = (
    r"\b(?:filing\s+fee|fee\s+schedule|application\s+fee|fees?)\b",
    r"\b(?:rate|rates|standard\s+mileage)\b",
    r"\b(?:taxable\s+maximum|wage\s+base|contribution\s+and\s+benefit\s+base)\b",
    r"\b(?:threshold|limit|maximum)\b",
    r"\b(?:form\s+[a-z]{1,4}[-\s]?\d{2,5}[a-z]?|"
    r"[a-z]{1,4}-\d{2,5}[a-z]?)\b",
)
_FEE_PATTERNS = (
    r"\b(?:filing\s+fee|fee\s+schedule|application\s+fee|fees?)\b",
)
_RATE_PATTERNS = (
    r"\b(?:rate|rates|standard\s+mileage)\b",
)
_THRESHOLD_PATTERNS = (
    r"\b(?:taxable\s+maximum|wage\s+base|contribution\s+and\s+benefit\s+base|"
    r"threshold|limit|maximum)\b",
)
_FORM_ID_RE = re.compile(
    r"\b(?:form\s+([a-z]{1,4})[-\s]?(\d{2,5}[a-z]?)|"
    r"([a-z]{1,4})-(\d{2,5}[a-z]?))\b"
)


@dataclass(frozen=True)
class RecoveredEvidenceVisibilityDecision:
    """Compact decision payload for recovered-evidence visibility."""

    considered: bool
    eligible: bool
    used: bool
    reason: str
    blockers: tuple[str, ...] = ()
    missing_source_class: str | None = None
    recovered_source_class: str | None = None
    reserved_source_count: int = 0
    reserved_source_ids_or_urls: tuple[str, ...] = ()
    reserved_source_classes: tuple[str, ...] = ()
    dropped_source_ids_or_urls: tuple[str, ...] = ()
    drop_reason: str | None = None
    source_fit_status: str = "not_evaluated"
    source_fit_candidate_count: int = 0
    source_fit_selected_count: int = 0
    source_fit_rejection_reasons: tuple[str, ...] = ()

    def to_trace_fields(self) -> dict[str, Any]:
        """Return the stable execution_trace fragment."""
        return {
            "recovered_visibility_considered": self.considered,
            "recovered_visibility_eligible": self.eligible,
            "recovered_visibility_used": self.used,
            "recovered_visibility_reason": self.reason,
            "recovered_visibility_blockers": list(self.blockers),
            "recovered_visibility_missing_source_class": self.missing_source_class,
            "recovered_visibility_recovered_source_class": (
                self.recovered_source_class
            ),
            "recovered_visibility_reserved_count": self.reserved_source_count,
            "recovered_visibility_reserved_source_ids": list(
                self.reserved_source_ids_or_urls
            ),
            "recovered_visibility_reserved_source_classes": list(
                self.reserved_source_classes
            ),
            "recovered_visibility_dropped_source_ids": list(
                self.dropped_source_ids_or_urls
            ),
            "recovered_visibility_drop_reason": self.drop_reason,
            "recovered_visibility_source_fit_status": self.source_fit_status,
            "recovered_visibility_source_fit_candidate_count": (
                self.source_fit_candidate_count
            ),
            "recovered_visibility_source_fit_selected_count": (
                self.source_fit_selected_count
            ),
            "recovered_visibility_source_fit_rejection_reasons": list(
                self.source_fit_rejection_reasons
            ),
        }


def recovered_evidence_visibility_defaults() -> dict[str, Any]:
    """Return defaults for traces where recovered visibility is not evaluated."""
    return RecoveredEvidenceVisibilityDecision(
        considered=False,
        eligible=False,
        used=False,
        reason="not_evaluated",
        blockers=("not_evaluated",),
    ).to_trace_fields()


def recovered_evidence_selection_candidates(
    *,
    all_passages: Iterable[Mapping[str, Any]],
    lifecycle_trace: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Return Controller-authorized recovered candidates for the selector."""

    return runner_owned_recovered_candidate_stream(
        all_passages=all_passages,
        lifecycle_trace=lifecycle_trace,
    )


def apply_controller_recovered_evidence_visibility(
    *,
    final_top_evidence: Iterable[Mapping[str, Any]],
    all_passages: Iterable[Mapping[str, Any]],
    lifecycle_trace: dict[str, Any],
    max_final_evidence: int,
    reserve_limit: int = 1,
) -> list[dict[str, Any]]:
    """Apply the Controller-owned recovered-evidence selection boundary."""

    recovered_passages = recovered_evidence_selection_candidates(
        all_passages=all_passages,
        lifecycle_trace=lifecycle_trace,
    )
    bounded, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=final_top_evidence,
        recovered_passages=recovered_passages,
        lifecycle_trace=lifecycle_trace,
        max_final_evidence=max_final_evidence,
        reserve_limit=reserve_limit,
    )
    lifecycle_trace.update(decision.to_trace_fields())
    return [source for source in bounded if isinstance(source, dict)]


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _source_identity(source: Mapping[str, Any]) -> str:
    for key in ("source_id", "url", "title"):
        value = _compact_text(source.get(key))
        if value:
            return value
    return ""


def _url_key(value: Any) -> str:
    raw = _compact_text(value)
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/")
    scheme = (parsed.scheme or "https").lower()
    if not host:
        return raw.lower().rstrip("/")
    return urlunparse((scheme, host, path, "", parsed.query, "")).lower()


def _identity_keys(source: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    url = _url_key(source.get("url"))
    if url:
        keys.add(f"url:{url}")
    source_id = _compact_text(source.get("source_id"))
    if source_id:
        keys.add(f"id:{source_id}")
    title = _compact_text(source.get("title")).casefold()
    if title and not url:
        keys.add(f"title:{title}")
    return keys


def _strong_source_classes(source: Mapping[str, Any]) -> tuple[str, ...]:
    signals = _evidence_source_class_strengths(source)
    return tuple(
        source_class
        for source_class, class_signals in signals.items()
        if class_signals.get("strong")
    )


def _source_class_match(
    *,
    strong_classes: Iterable[str],
    missing_classes: Iterable[str],
) -> tuple[str | None, str | None]:
    strong = tuple(str(source_class or "").strip() for source_class in strong_classes)
    for missing in (str(item or "").strip() for item in missing_classes):
        if not missing:
            continue
        allowed = DIRECT_MATCH_CLASSES.get(missing, frozenset({missing}))
        for source_class in strong:
            if source_class in allowed:
                return missing, source_class
    first_missing = next(
        (str(item or "").strip() for item in missing_classes if str(item or "").strip()),
        None,
    )
    return first_missing, None


def _historical_or_archival_blocks_current_gap(
    *,
    source: Mapping[str, Any],
    missing_source_class: str | None,
    strong_classes: Iterable[str],
) -> bool:
    if missing_source_class not in CURRENT_SOURCE_CLASS_GAPS:
        return False
    if set(strong_classes) & HISTORICAL_OR_ARCHIVAL_CLASSES:
        return True
    text = (
        f"{source.get('title', '')} {source.get('url', '')} {source.get('text', '')}"
    ).casefold()
    historical_markers = (
        "archival",
        "archive",
        "archives",
        "historical",
        "history",
        "sourcebook",
        "original text",
        "translated text",
    )
    current_markers = ("current", "as of", "effective", "2025", "2026")
    return any(marker in text for marker in historical_markers) and not any(
        marker in text for marker in current_markers
    )


def _lifecycle_obligation_text(lifecycle_trace: Mapping[str, Any]) -> str:
    values: list[str] = []
    for key in (
        "active_source_class_recovery_queries",
        "query",
        "query_preview",
        "core_topic",
        "primary_entity",
    ):
        value = lifecycle_trace.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(_compact_text(item) for item in value)
        else:
            values.append(_compact_text(value))
    authority = _authority_lifecycle(lifecycle_trace)
    if authority is not None:
        action = authority.get("recovery_action")
        if isinstance(action, Mapping):
            queries = action.get("queries")
            if isinstance(queries, (list, tuple, set)):
                values.extend(_compact_text(item) for item in queries)
    return " ".join(value for value in values if value).casefold()


def _source_search_text(source: Mapping[str, Any]) -> str:
    return " ".join(
        _compact_text(source.get(key))
        for key in ("url", "title", "text", "snippet")
        if _compact_text(source.get(key))
    ).casefold()


def _matches_any_pattern(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _normalized_form_ids(text: str) -> tuple[str, ...]:
    out: list[str] = []
    for explicit_prefix, explicit_number, hyphen_prefix, hyphen_number in (
        _FORM_ID_RE.findall(text)
    ):
        prefix = explicit_prefix or hyphen_prefix
        number = explicit_number or hyphen_number
        form_id = f"{prefix}-{number}".casefold()
        if form_id not in out:
            out.append(form_id)
    return tuple(out)


def _contains_form_id(text: str, form_id: str) -> bool:
    prefix, _, number = form_id.partition("-")
    if not prefix or not number:
        return False
    return bool(
        re.search(
            rf"\b(?:form\s+)?{re.escape(prefix)}[-\s]?{re.escape(number)}\b",
            text,
        )
    )


def _specific_answer_bearing_required(
    *,
    lifecycle_trace: Mapping[str, Any],
    missing_source_class: str | None,
) -> bool:
    specific_classes = CURRENT_SOURCE_CLASS_GAPS | {"legal_or_regulatory_text"}
    if missing_source_class not in specific_classes:
        return False
    obligation_text = _lifecycle_obligation_text(lifecycle_trace)
    return _matches_any_pattern(obligation_text, _ANSWER_BEARING_OBLIGATION_PATTERNS)


def _source_is_answer_bearing_for_obligation(
    source: Mapping[str, Any],
    *,
    lifecycle_trace: Mapping[str, Any],
    missing_source_class: str | None,
) -> bool:
    if not _specific_answer_bearing_required(
        lifecycle_trace=lifecycle_trace,
        missing_source_class=missing_source_class,
    ):
        return True
    if (
        source.get("answer_bearing") is True
        or source.get("satisfies_authority") is True
    ):
        return True

    obligation_text = _lifecycle_obligation_text(lifecycle_trace)
    source_text = _source_search_text(source)
    if not source_text:
        return False

    form_ids = _normalized_form_ids(obligation_text)
    fee_required = _matches_any_pattern(obligation_text, _FEE_PATTERNS)
    rate_required = _matches_any_pattern(obligation_text, _RATE_PATTERNS)
    threshold_required = _matches_any_pattern(obligation_text, _THRESHOLD_PATTERNS)

    form_ok = not form_ids or any(
        _contains_form_id(source_text, form_id) for form_id in form_ids
    )
    fee_ok = not fee_required or _matches_any_pattern(source_text, _FEE_PATTERNS)
    rate_ok = not rate_required or _matches_any_pattern(source_text, _RATE_PATTERNS)
    threshold_ok = not threshold_required or _matches_any_pattern(
        source_text,
        _THRESHOLD_PATTERNS,
    )
    if form_ids and fee_required:
        return form_ok and fee_ok
    return form_ok and fee_ok and rate_ok and threshold_ok


def _visible_identity_keys(sources: Iterable[Mapping[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for source in sources:
        keys.update(_identity_keys(source))
    return keys


def _visible_identity_matches(
    final_evidence: Iterable[Mapping[str, Any]],
    source_keys: set[str],
) -> list[Mapping[str, Any]]:
    if not source_keys:
        return []
    return [
        source
        for source in final_evidence
        if isinstance(source, Mapping) and _identity_keys(source) & source_keys
    ]


def _source_satisfies_missing_authority(
    source: Mapping[str, Any],
    missing_classes: Iterable[str],
) -> bool:
    strong_classes = _strong_source_classes(source)
    missing_source_class, recovered_source_class = _source_class_match(
        strong_classes=strong_classes,
        missing_classes=missing_classes,
    )
    if recovered_source_class is None:
        return False
    return not _historical_or_archival_blocks_current_gap(
        source=source,
        missing_source_class=missing_source_class,
        strong_classes=strong_classes,
    )


def _lower_tier_context_duplicate(source: Mapping[str, Any]) -> bool:
    source_tier = _compact_text(source.get("source_tier")).casefold()
    source_class = _compact_text(source.get("source_class")).casefold()
    if source_tier in {"secondary", "context", "analysis"}:
        return True
    return source_class in {"secondary", "secondary_only", "context"}


def _visible_duplicate_drop_reason(
    *,
    source: Mapping[str, Any],
    final_evidence: Iterable[Mapping[str, Any]],
    source_keys: set[str],
    visible_keys: set[str],
    missing_classes: Iterable[str],
) -> str | None:
    if not source_keys or not source_keys & visible_keys:
        return None
    exact_visible = source_keys <= visible_keys
    matches = _visible_identity_matches(final_evidence, source_keys)
    prefix = "already_visible" if exact_visible else "duplicate_visible"
    if any(
        _source_satisfies_missing_authority(match, missing_classes)
        for match in matches
    ):
        return f"{prefix}_authority_satisfying"
    if any(_lower_tier_context_duplicate(match) for match in matches):
        return (
            "already_visible_duplicate_lower_tier_context"
            if exact_visible
            else "duplicate_visible_lower_tier_context_source"
        )
    return (
        "already_visible_not_authority_satisfying"
        if exact_visible
        else "duplicate_visible_not_authority_satisfying"
    )


def _visible_duplicate_should_block_candidate(
    reason: str,
    source: Mapping[str, Any],
) -> bool:
    if reason in {
        "already_visible_authority_satisfying",
        "duplicate_visible_authority_satisfying",
    }:
        return True
    return not bool(_strong_source_classes(source))


def _non_authority_visible_duplicate_index(
    final_evidence: list[Mapping[str, Any]],
    source: Mapping[str, Any],
    missing_classes: Iterable[str],
) -> int | None:
    source_keys = _identity_keys(source)
    if not source_keys:
        return None
    for index, existing in enumerate(final_evidence):
        if not isinstance(existing, Mapping):
            continue
        if not (_identity_keys(existing) & source_keys):
            continue
        if _source_satisfies_missing_authority(existing, missing_classes):
            continue
        return index
    return None


def _is_lower_priority_replaceable(source: Mapping[str, Any]) -> bool:
    if source.get("retrieval_stage") == "source_class_recovery":
        return False
    return not (set(_strong_source_classes(source)) & LOWER_PRIORITY_PROTECTED_CLASSES)


def _replaceable_index(final_evidence: list[Mapping[str, Any]]) -> int | None:
    for index in range(len(final_evidence) - 1, -1, -1):
        if _is_lower_priority_replaceable(final_evidence[index]):
            return index
    return None


def _bounded_reserve_limit(value: int) -> int:
    return max(0, min(2, int(value or 0)))


def _initial_blockers(lifecycle_trace: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    authority = _authority_lifecycle(lifecycle_trace)
    if authority is not None:
        if not _authority_execution_attempted(authority):
            blockers.append("source_class_recovery_not_used")
        if not _authority_recovery_action_approved(authority):
            blockers.append("provider_role_not_source_class_recovery")
    else:
        if lifecycle_trace.get("active_source_class_recovery_used") is not True:
            blockers.append("source_class_recovery_not_used")
        if lifecycle_trace.get("active_source_class_recovery_provider_role") != (
            "source_class_recovery"
        ):
            blockers.append("provider_role_not_source_class_recovery")
    reason = _compact_text(
        lifecycle_trace.get("active_source_class_recovery_reason")
    )
    missing = [
        _compact_text(item)
        for item in (
            lifecycle_trace.get("active_source_class_recovery_missing_classes") or []
        )
        if _compact_text(item)
    ]
    if authority is not None:
        missing = list(_authority_required_source_classes(authority))
    official_canonical_admitted = (
        lifecycle_trace.get("active_source_class_recovery_official_canonical_admitted")
        is True
    )
    official_canonical_reason = reason.startswith(
        OFFICIAL_CANONICAL_VISIBILITY_REASON_PREFIXES
    )
    official_canonical_lifecycle = (
        official_canonical_admitted
        and bool(missing)
        and _approved_recover_missing_source_class_envelope(lifecycle_trace)
    )
    answer_contract_reason = reason.startswith(
        ANSWER_CONTRACT_VISIBILITY_REASON_PREFIXES
    )
    if not (
        authority is not None
        or answer_contract_reason
        or (official_canonical_admitted and official_canonical_reason)
        or official_canonical_lifecycle
    ):
        blockers.append("reason_not_answer_contract_gap")
    if authority is None:
        active_blockers = {
            _compact_text(blocker)
            for blocker in (
                lifecycle_trace.get("active_source_class_recovery_blockers") or []
            )
        }
        if "blocked_by_weak_corpus_recovery" in active_blockers:
            blockers.append("blocked_by_weak_corpus_recovery")
        skip_reason = _compact_text(
            lifecycle_trace.get("active_source_class_recovery_skip_reason")
        )
        if skip_reason == "already_attempted":
            blockers.append("duplicate_attempt_blocked")
        try:
            attempt_count = int(
                lifecycle_trace.get("active_source_class_recovery_attempt_count") or 0
            )
        except (TypeError, ValueError):
            attempt_count = 0
        if attempt_count > 1:
            blockers.append("duplicate_attempt_blocked")
    if not missing:
        blockers.append("missing_source_class_unavailable")
    if authority is None:
        quality_status = _compact_text(
            lifecycle_trace.get("recovery_source_quality_status")
        )
        if quality_status in DISQUALIFYING_QUALITY_STATUSES:
            blockers.append(quality_status)
    return blockers


def _authority_lifecycle(lifecycle_trace: Mapping[str, Any]) -> Mapping[str, Any] | None:
    authority = lifecycle_trace.get("authority_lifecycle")
    return authority if isinstance(authority, Mapping) else None


def _authority_execution_attempted(authority: Mapping[str, Any]) -> bool:
    execution = authority.get("execution_state")
    return isinstance(execution, Mapping) and execution.get("state") == "attempted"


def _authority_recovery_action_approved(authority: Mapping[str, Any]) -> bool:
    action = authority.get("recovery_action")
    return bool(
        isinstance(action, Mapping)
        and action.get("action_type") == "recover_missing_source_class"
        and action.get("approved") is True
    )


def _authority_required_source_classes(authority: Mapping[str, Any]) -> tuple[str, ...]:
    action = authority.get("recovery_action")
    if not isinstance(action, Mapping):
        return ()
    values = action.get("required_source_classes")
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(_compact_text(item) for item in values if _compact_text(item))


def _non_authority_source_fit_reason(source: Mapping[str, Any]) -> str:
    source_tier = _compact_text(source.get("source_tier")).casefold()
    source_class = _compact_text(source.get("source_class")).casefold()
    if source_tier == "secondary" or source_class in {"secondary", "secondary_only"}:
        return "secondary_only"
    return "not_strong_source_class"


def _bool_or_unknown(value: Any) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _explicit_unreadability_reason(source: Mapping[str, Any]) -> str | None:
    explicit = _bool_or_unknown(source.get("readable_text_available"))
    if explicit is False:
        return "readability_failed"
    status = _compact_text(source.get("readability_status")).casefold()
    if status in {"unreadable", "readability_failed", "failed"}:
        return "readability_failed"
    return None


def _approved_recover_missing_source_class_envelope(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    envelope = lifecycle_trace.get("active_source_class_recovery_action_envelope")
    if not isinstance(envelope, Mapping):
        return False
    required_classes = envelope.get("required_source_class")
    if not isinstance(required_classes, list) or not required_classes:
        return False
    return bool(
        envelope.get("action_type") == "recover_missing_source_class"
        and envelope.get("allowed_action") is True
    )


def apply_recovered_evidence_visibility_boundary(
    *,
    final_top_evidence: Iterable[Mapping[str, Any]],
    recovered_passages: Iterable[Mapping[str, Any]],
    lifecycle_trace: Mapping[str, Any],
    max_final_evidence: int,
    reserve_limit: int = 1,
) -> tuple[list[Mapping[str, Any]], RecoveredEvidenceVisibilityDecision]:
    """Reserve at most one qualifying recovered source into final evidence."""
    final_evidence = [
        source for source in final_top_evidence or [] if isinstance(source, Mapping)
    ]
    recovered = [
        source for source in recovered_passages or [] if isinstance(source, Mapping)
    ]
    considered = bool(
        lifecycle_trace.get("active_source_class_recovery_used") is True
        or recovered
    )
    missing_classes = [
        _compact_text(item)
        for item in (
            lifecycle_trace.get("active_source_class_recovery_missing_classes") or []
        )
        if _compact_text(item)
    ]

    def _finalize(
        evidence: list[Mapping[str, Any]],
        decision: RecoveredEvidenceVisibilityDecision,
    ) -> tuple[list[Mapping[str, Any]], RecoveredEvidenceVisibilityDecision]:
        projection = project_authority_lifecycle_candidate_fit_visibility(
            lifecycle_trace=lifecycle_trace,
            final_top_evidence=evidence,
            recovered_passages=recovered,
            visibility_decision=decision.to_trace_fields(),
        )
        if projection:
            decision = replace(
                decision,
                source_fit_status=str(
                    projection.get(
                        "recovered_visibility_source_fit_status",
                        decision.source_fit_status,
                    )
                ),
                source_fit_candidate_count=int(
                    projection.get(
                        "recovered_visibility_source_fit_candidate_count",
                        decision.source_fit_candidate_count,
                    )
                    or 0
                ),
                source_fit_selected_count=int(
                    projection.get(
                        "recovered_visibility_source_fit_selected_count",
                        decision.source_fit_selected_count,
                    )
                    or 0
                ),
                source_fit_rejection_reasons=tuple(
                    projection.get(
                        "recovered_visibility_source_fit_rejection_reasons",
                        decision.source_fit_rejection_reasons,
                    )
                    or ()
                ),
            )
        return evidence, decision

    blockers = _initial_blockers(lifecycle_trace)
    if blockers:
        return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
            considered=considered,
            eligible=False,
            used=False,
            reason=blockers[0],
            blockers=tuple(blockers),
            missing_source_class=missing_classes[0] if missing_classes else None,
            dropped_source_ids_or_urls=tuple(
                identity
                for identity in (_source_identity(source) for source in recovered)
                if identity
            ),
            drop_reason=blockers[0],
            source_fit_status="not_evaluated",
        ))

    if not recovered:
        return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
            considered=considered,
            eligible=False,
            used=False,
            reason="no_recovered_sources",
            blockers=("no_recovered_sources",),
            missing_source_class=missing_classes[0] if missing_classes else None,
            drop_reason="no_recovered_sources",
            source_fit_status="no_candidates",
        ))

    visible_keys = _visible_identity_keys(final_evidence)
    dropped: list[str] = []
    drop_reasons: list[str] = []
    candidates: list[tuple[Mapping[str, Any], str, str, str]] = []
    seen_candidate_keys: set[str] = set()

    for source in recovered:
        identity = _source_identity(source)
        source_keys = _identity_keys(source)
        visible_duplicate_reason = _visible_duplicate_drop_reason(
            source=source,
            final_evidence=final_evidence,
            source_keys=source_keys,
            visible_keys=visible_keys,
            missing_classes=missing_classes,
        )
        if visible_duplicate_reason and _visible_duplicate_should_block_candidate(
            visible_duplicate_reason,
            source,
        ):
            if identity:
                dropped.append(identity)
            drop_reasons.append(visible_duplicate_reason)
            continue
        if source_keys & seen_candidate_keys:
            if identity:
                dropped.append(identity)
            drop_reasons.append("duplicate_recovered_source")
            continue
        strong_classes = _strong_source_classes(source)
        if not strong_classes:
            if identity:
                dropped.append(identity)
            drop_reasons.append(_non_authority_source_fit_reason(source))
            continue

        missing_source_class, recovered_source_class = _source_class_match(
            strong_classes=strong_classes,
            missing_classes=missing_classes,
        )
        if recovered_source_class is None:
            if identity:
                dropped.append(identity)
            drop_reasons.append("source_class_mismatch")
            continue

        unreadability_reason = _explicit_unreadability_reason(source)
        if unreadability_reason:
            if identity:
                dropped.append(identity)
            drop_reasons.append(unreadability_reason)
            continue

        if _historical_or_archival_blocks_current_gap(
            source=source,
            missing_source_class=missing_source_class,
            strong_classes=strong_classes,
        ):
            if identity:
                dropped.append(identity)
            drop_reasons.append("historical_or_archival_not_current")
            continue

        if not _source_is_answer_bearing_for_obligation(
            source,
            lifecycle_trace=lifecycle_trace,
            missing_source_class=missing_source_class,
        ):
            if identity:
                dropped.append(identity)
            drop_reasons.append("official_candidate_not_answer_bearing")
            continue

        candidates.append(
            (source, identity, missing_source_class or "", recovered_source_class)
        )
        seen_candidate_keys.update(source_keys)

    if not candidates:
        drop_reason = drop_reasons[0] if drop_reasons else "no_matching_recovered_source"
        return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
            considered=considered,
            eligible=False,
            used=False,
            reason=drop_reason,
            blockers=(drop_reason,),
            missing_source_class=missing_classes[0] if missing_classes else None,
            dropped_source_ids_or_urls=tuple(dropped),
            drop_reason=drop_reason,
            source_fit_status="no_matching_source_fit",
            source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
        ))

    limit = _bounded_reserve_limit(reserve_limit)
    if limit < 1:
        return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
            considered=considered,
            eligible=True,
            used=False,
            reason="reservation_limit_zero",
            blockers=("reservation_limit_zero",),
            missing_source_class=candidates[0][2],
            recovered_source_class=candidates[0][3],
            dropped_source_ids_or_urls=tuple(dropped),
            drop_reason="reservation_limit_zero",
            source_fit_status="matched_not_selected",
            source_fit_candidate_count=len(candidates),
            source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
        ))

    cap = max(0, int(max_final_evidence or 0))
    selected = candidates[:limit]
    updated = list(final_evidence)
    reserved: list[tuple[str, str, str]] = []
    reason = "reserved_append"

    if len(updated) < cap:
        room = cap - len(updated)
        for source, identity, missing_source_class, recovered_source_class in selected:
            duplicate_index = _non_authority_visible_duplicate_index(
                updated,
                source,
                missing_classes,
            )
            if duplicate_index is not None:
                updated[duplicate_index] = source
                reserved.append((identity, missing_source_class, recovered_source_class))
                reason = "reserved_replace_non_authority_duplicate"
                continue
            if room <= 0:
                continue
            updated.append(source)
            reserved.append((identity, missing_source_class, recovered_source_class))
            room -= 1
    else:
        duplicate_index = _non_authority_visible_duplicate_index(
            updated,
            selected[0][0],
            missing_classes,
        )
        if duplicate_index is not None:
            source, identity, missing_source_class, recovered_source_class = selected[0]
            updated[duplicate_index] = source
            reserved.append((identity, missing_source_class, recovered_source_class))
            reason = "reserved_replace_non_authority_duplicate"
            return _finalize(updated, RecoveredEvidenceVisibilityDecision(
                considered=considered,
                eligible=True,
                used=True,
                reason=reason,
                blockers=(),
                missing_source_class=reserved[0][1],
                recovered_source_class=reserved[0][2],
                reserved_source_count=len(reserved),
                reserved_source_ids_or_urls=tuple(identity for identity, _, _ in reserved),
                reserved_source_classes=tuple(source_class for _, _, source_class in reserved),
                dropped_source_ids_or_urls=tuple(dropped),
                drop_reason=None,
                source_fit_status="matched_selected",
                source_fit_candidate_count=len(candidates),
                source_fit_selected_count=len(reserved),
                source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
            ))
        replace_at = _replaceable_index(updated)
        if replace_at is None:
            return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
                considered=considered,
                eligible=True,
                used=False,
                reason="final_evidence_cap_no_replaceable_source",
                blockers=("final_evidence_cap_no_replaceable_source",),
                missing_source_class=candidates[0][2],
                recovered_source_class=candidates[0][3],
                dropped_source_ids_or_urls=tuple(dropped),
                drop_reason="final_evidence_cap_no_replaceable_source",
                source_fit_status="matched_not_selected",
                source_fit_candidate_count=len(candidates),
                source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
            ))
        source, identity, missing_source_class, recovered_source_class = selected[0]
        updated[replace_at] = source
        reserved.append((identity, missing_source_class, recovered_source_class))
        reason = "reserved_replace"

    if not reserved:
        return _finalize(final_evidence, RecoveredEvidenceVisibilityDecision(
            considered=considered,
            eligible=True,
            used=False,
            reason="final_evidence_cap_no_room",
            blockers=("final_evidence_cap_no_room",),
            missing_source_class=candidates[0][2],
            recovered_source_class=candidates[0][3],
            dropped_source_ids_or_urls=tuple(dropped),
            drop_reason="final_evidence_cap_no_room",
            source_fit_status="matched_not_selected",
            source_fit_candidate_count=len(candidates),
            source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
        ))

    return _finalize(updated, RecoveredEvidenceVisibilityDecision(
        considered=considered,
        eligible=True,
        used=True,
        reason=reason,
        blockers=(),
        missing_source_class=reserved[0][1],
        recovered_source_class=reserved[0][2],
        reserved_source_count=len(reserved),
        reserved_source_ids_or_urls=tuple(identity for identity, _, _ in reserved),
        reserved_source_classes=tuple(source_class for _, _, source_class in reserved),
        dropped_source_ids_or_urls=tuple(dropped),
        drop_reason=None,
        source_fit_status="matched_selected",
        source_fit_candidate_count=len(candidates),
        source_fit_selected_count=len(reserved),
        source_fit_rejection_reasons=tuple(dict.fromkeys(drop_reasons)),
    ))


__all__ = [
    "ANSWER_CONTRACT_VISIBILITY_REASON_PREFIXES",
    "RecoveredEvidenceVisibilityDecision",
    "apply_controller_recovered_evidence_visibility",
    "apply_recovered_evidence_visibility_boundary",
    "recovered_evidence_visibility_defaults",
    "recovered_evidence_selection_candidates",
]
