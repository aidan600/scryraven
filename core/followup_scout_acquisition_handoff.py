"""Offline scout-to-acquisition handoff diagnostics for AG-96I3I.

The helper consumes sanitized scout/result-set diagnostics only. It does not
call providers, fetch pages, read private data, invoke models, or create final
evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.followup_deliberation import (
    ProviderJobKind,
    clean_text,
    clean_token,
)

SCHEMA_VERSION = "ag96i3i_scout_to_acquisition_handoff_diagnostics_v1"
RECORD_TYPE = "scout_to_acquisition_handoff_diagnostics"

OFFICIAL_CURRENT_CANDIDATE_FIT = "official_current_candidate_fit"
OFFICIAL_CURRENTNESS_UNVERIFIED = "official_currentness_unverified"

OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC = (
    "official_current_candidate_verified_by_diagnostic"
)
OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED = (
    "official_candidate_currentness_unverified"
)
NO_OFFICIAL_CANDIDATE_VISIBLE = "no_official_candidate_visible"
BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE = "bridge_only_no_official_candidate"

FETCH_READ_CURRENTNESS_VERIFICATION = "fetch_read_currentness_verification"
NO_VERIFIED_OFFICIAL_HANDOFF = "no_verified_official_handoff"

_OFFICIAL_SOURCE_CLASSES = frozenset(
    {"official_current_rules", "official_government", "official"}
)
_VERIFICATION_STATUSES = frozenset(
    {OFFICIAL_CURRENT_CANDIDATE_FIT, OFFICIAL_CURRENTNESS_UNVERIFIED}
)


def build_scout_to_acquisition_handoff_diagnostics(
    *,
    provider_result_set_diagnostics: Mapping[str, Any],
    freshness_policy_diagnostics: Mapping[str, Any] | None = None,
    authorized_query: str | None = None,
    query_variant_ref: str | None = None,
    query_shape_mode: str | None = None,
    provider_name: str | None = None,
    provider_surface_role: str | None = None,
    provider_job_kind: str | None = None,
    acquisition_mode: str | None = None,
    max_verification_candidates: int = 3,
) -> dict[str, Any]:
    """Build a sanitized handoff packet for the next acquisition layer."""

    diagnostics = _mapping(provider_result_set_diagnostics)
    freshness = _freshness_summary(freshness_policy_diagnostics)
    result_provider = (
        clean_token(provider_name, limit=120)
        or clean_token(diagnostics.get("provider_name"), limit=120)
        or "unknown_provider"
    )
    job_kind = (
        clean_token(provider_job_kind, limit=120)
        or clean_token(diagnostics.get("provider_job_kind"), limit=120)
        or ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    )
    surface_role = (
        clean_token(provider_surface_role, limit=120)
        or clean_token(diagnostics.get("provider_surface_role"), limit=120)
        or "candidate_acquisition"
    )
    mode = (
        clean_token(acquisition_mode, limit=120)
        or clean_token(diagnostics.get("acquisition_mode"), limit=120)
        or "discovery_unconstrained"
    )
    query_ref = (
        clean_token(query_variant_ref, limit=180)
        or clean_token(diagnostics.get("authorized_query_ref"), limit=180)
    )
    query = (
        clean_text(authorized_query, limit=500)
        or clean_text(diagnostics.get("authorized_query"), limit=500)
        or clean_text(freshness.get("original_authorized_query"), limit=500)
    )

    candidates = _verification_candidates(
        diagnostics=diagnostics,
        freshness=freshness,
        provider_name=result_provider,
        query_variant_ref=query_ref,
        limit=_candidate_limit(max_verification_candidates),
    )
    best = candidates[0] if candidates else None
    outcome = _scout_result_outcome(diagnostics, candidates)
    recommended_next_step = (
        FETCH_READ_CURRENTNESS_VERIFICATION if candidates else NO_VERIFIED_OFFICIAL_HANDOFF
    )
    priority = _handoff_priority(best)
    stop_more_scout_spending = bool(best and best.get("rank") == 1)

    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "owner": "FollowupScoutAcquisitionHandoffDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "authorized_query": query,
        "query_variant_ref": query_ref,
        "query_shape_mode": clean_token(query_shape_mode, limit=120),
        "provider_name": result_provider,
        "provider_surface_role": surface_role,
        "provider_job_kind": job_kind,
        "acquisition_mode": mode,
        "freshness_policy_diagnostics": freshness,
        "scout_result_outcome": outcome,
        "verification_candidate_count": len(candidates),
        "verification_candidates": candidates,
        "best_verification_candidate_rank": best.get("rank") if best else None,
        "best_verification_candidate_domain": best.get("domain") if best else None,
        "best_verification_candidate_url": best.get("url") if best else None,
        "recommended_next_step": recommended_next_step,
        "stop_more_scout_spending_recommended": stop_more_scout_spending,
        "handoff_priority": priority,
        "handoff_reasons": _handoff_reasons(
            outcome=outcome,
            best=best,
            stop_more_scout_spending=stop_more_scout_spending,
        ),
        "evidence_boundary": _evidence_boundary(),
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _verification_candidates(
    *,
    diagnostics: Mapping[str, Any],
    freshness: Mapping[str, Any],
    provider_name: str,
    query_variant_ref: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in diagnostics.get("sanitized_results", []):
        mapped = _mapping(item)
        if not _is_verification_candidate(mapped):
            continue
        candidate = {
            "rank": _rank(mapped.get("rank")),
            "title": clean_text(mapped.get("title"), limit=300),
            "url": clean_text(mapped.get("url"), limit=500),
            "domain": clean_text(mapped.get("domain"), limit=160),
            "source_class": clean_token(mapped.get("source_class"), limit=120),
            "source_tier": clean_token(mapped.get("source_tier"), limit=120),
            "currentness_signal": clean_token(
                mapped.get("currentness_signal"),
                limit=120,
            ),
            "candidate_fit_status": clean_token(
                mapped.get("candidate_fit_status"),
                limit=120,
            ),
            "provider_name": clean_token(
                mapped.get("provider_name") or provider_name,
                limit=120,
            ),
            "query_variant_ref": query_variant_ref,
            "freshness_intent": freshness.get("freshness_intent"),
            "freshness_window": freshness.get("freshness_window"),
            "provider_freshness_policy": freshness.get("provider_freshness_policy"),
            "over_narrow_recent_window_forbidden": bool(
                freshness.get("over_narrow_recent_window_forbidden")
            ),
            "freshness_rationale": freshness.get("freshness_rationale"),
            "required_next_step": FETCH_READ_CURRENTNESS_VERIFICATION,
            "final_evidence": False,
            "citation_eligible": False,
        }
        candidates.append(candidate)
    candidates.sort(key=lambda candidate: candidate.get("rank") or 10_000)
    return candidates[:limit]


def _is_verification_candidate(item: Mapping[str, Any]) -> bool:
    status = clean_token(item.get("candidate_fit_status"), limit=120)
    if status not in _VERIFICATION_STATUSES:
        return False
    if not clean_text(item.get("url"), limit=500):
        return False
    source_tier = clean_token(item.get("source_tier"), limit=120)
    source_class = clean_token(item.get("source_class"), limit=120)
    return source_tier == "official" or source_class in _OFFICIAL_SOURCE_CLASSES


def _scout_result_outcome(
    diagnostics: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
) -> str:
    if any(
        candidate.get("candidate_fit_status") == OFFICIAL_CURRENT_CANDIDATE_FIT
        for candidate in candidates
    ):
        return OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC
    if any(
        candidate.get("candidate_fit_status") == OFFICIAL_CURRENTNESS_UNVERIFIED
        for candidate in candidates
    ):
        return OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED
    if diagnostics.get("bridge_only") or diagnostics.get("bridge_hint_rank") is not None:
        return BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE
    return NO_OFFICIAL_CANDIDATE_VISIBLE


def _handoff_priority(best: Mapping[str, Any] | None) -> str:
    if not best:
        return "low"
    if best.get("rank") == 1:
        return "high"
    return "medium"


def _handoff_reasons(
    *,
    outcome: str,
    best: Mapping[str, Any] | None,
    stop_more_scout_spending: bool,
) -> list[str]:
    if outcome == OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC:
        reasons = ["official_current_candidate_visible_in_scout_diagnostics"]
    elif outcome == OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED:
        reasons = ["official_source_visible_currentness_requires_verification"]
    elif outcome == BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE:
        reasons = ["bridge_results_visible_no_official_verification_candidate"]
    else:
        reasons = ["no_official_candidate_visible_in_sanitized_results"]
    if best and best.get("rank") == 1:
        reasons.append("rank_one_official_candidate_should_trigger_acquisition")
    if stop_more_scout_spending:
        reasons.append("additional_scout_spending_not_recommended_before_verification")
    return reasons


def _freshness_summary(value: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(value)
    return {
        "schema_version": clean_token(source.get("schema_version"), limit=120),
        "record_type": clean_token(source.get("record_type"), limit=120),
        "original_authorized_query": clean_text(
            source.get("original_authorized_query"),
            limit=500,
        ),
        "freshness_intent": clean_token(source.get("freshness_intent"), limit=120),
        "freshness_window": clean_token(source.get("freshness_window"), limit=120),
        "provider_freshness_policy": clean_token(
            source.get("provider_freshness_policy"),
            limit=120,
        ),
        "over_narrow_recent_window_forbidden": bool(
            source.get("over_narrow_recent_window_forbidden")
        ),
        "freshness_rationale": clean_text(
            source.get("freshness_rationale"),
            limit=300,
        ),
    }


def _candidate_limit(value: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return 3
    return min(10, max(1, limit))


def _rank(value: Any) -> int | None:
    try:
        rank = int(value)
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


def _evidence_boundary() -> dict[str, bool]:
    return {
        "scout_handoff_is_final_evidence": False,
        "scout_handoff_is_citation_eligible": False,
        "verification_candidates_are_final_evidence": False,
        "verification_candidates_are_citation_eligible": False,
        "final_evidence_requires_later_fetch_read_admission": True,
        "author_or_final_answer_activation_allowed": False,
    }


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
    "BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE",
    "FETCH_READ_CURRENTNESS_VERIFICATION",
    "NO_OFFICIAL_CANDIDATE_VISIBLE",
    "OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED",
    "OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC",
    "SCHEMA_VERSION",
    "build_scout_to_acquisition_handoff_diagnostics",
]
