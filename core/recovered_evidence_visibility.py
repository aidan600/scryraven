"""Bounded visibility rule for contract-qualified recovered evidence.

This module is deliberately pure: it does not call retrieval, providers,
ranking, prompts, models, persistence, or orchestration code.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.allocation_candidate_selection_activation import (
    allocation_result_candidates_for_existing_selection_corridor,
)
from core.authority_lifecycle_candidate_visibility import (
    project_authority_lifecycle_candidate_fit_visibility,
)
from core.source_class_recovery import _evidence_source_class_strengths

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

    recovered_passages = [
        passage
        for passage in all_passages or ()
        if isinstance(passage, Mapping)
        and passage.get("retrieval_stage") == "source_class_recovery"
    ]
    recovered_passages.extend(
        allocation_result_candidates_for_existing_selection_corridor(lifecycle_trace)
    )
    return recovered_passages


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
        if visible_duplicate_reason:
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

        if _historical_or_archival_blocks_current_gap(
            source=source,
            missing_source_class=missing_source_class,
            strong_classes=strong_classes,
        ):
            if identity:
                dropped.append(identity)
            drop_reasons.append("historical_or_archival_not_current")
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
        selected = selected[:room]
        for source, identity, missing_source_class, recovered_source_class in selected:
            updated.append(source)
            reserved.append((identity, missing_source_class, recovered_source_class))
    else:
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
