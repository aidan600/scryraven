"""Fast-mode recipe bounds for hard-corridor official acquisition.

This helper is intentionally narrow: it plans and records budgeted provider-job
sequencing around the existing source-class recovery executor. It does not
authorize the need for recovery, call providers by itself, fetch pages, rank
sources, admit final evidence, certify citations, decide sufficiency, or change
Author behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

FAST_OFFICIAL_LANE_TRACE_KEY = "fast_official_lane"
FAST_OFFICIAL_LANE_SCHEMA_VERSION = "ag96b1_fast_official_lane_v1"

_OFFICIAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }
)
_DIRECT_PROVIDER_JOBS = {
    "tavily": "direct_official_candidate_search",
    "linkup": "direct_official_candidate_search",
    "exa": "semantic_recall_or_constrained_candidate_search",
}
_BRIDGE_HINT_KEYS = (
    "official_url",
    "official_title",
    "document_id",
    "agency_subpath",
    "query_term",
    "authority_candidate",
    "effective_date_hint",
)
_MAX_TEXT = 180


@dataclass(frozen=True)
class OfficialBridgeHint:
    """Concrete bridge-only lead toward a canonical official source."""

    official_url: str | None = None
    official_title: str | None = None
    document_id: str | None = None
    agency_subpath: str | None = None
    query_term: str | None = None
    authority_candidate: str | None = None
    effective_date_hint: str | None = None
    provider: str | None = None
    provider_job: str = "bridge_hint"
    source: str = "provider_result_summary"

    def retry_query(self) -> str | None:
        for value in (
            self.query_term,
            self.official_title,
            self.document_id,
            self.official_url,
            self.authority_candidate,
            self.agency_subpath,
        ):
            text = _clean_text(value)
            if text:
                return text
        return None

    def as_trace(self) -> dict[str, Any]:
        payload = {
            key: getattr(self, key)
            for key in _BRIDGE_HINT_KEYS
            if _clean_text(getattr(self, key))
        }
        payload.update(
            {
                "provider": _clean_text(self.provider) or None,
                "provider_job": self.provider_job,
                "source": self.source,
                "bridge_only": True,
                "citation_eligible": False,
                "final_evidence_eligible": False,
            }
        )
        return payload


@dataclass(frozen=True)
class FastOfficialLanePlan:
    """Runtime-consumed Fast hard-corridor official acquisition recipe."""

    used: bool
    skip_reason: str | None
    corridor: str
    provider_jobs: tuple[dict[str, Any], ...]
    scout_job_planned: bool = False
    direct_attempt_budget: int = 1
    bridge_retry_budget: int = 1

    def as_trace(self) -> dict[str, Any]:
        return {
            "schema_version": FAST_OFFICIAL_LANE_SCHEMA_VERSION,
            "used": self.used,
            "skip_reason": self.skip_reason,
            "corridor": self.corridor,
            "scout_job_planned": self.scout_job_planned,
            "scout_job_attempted": False,
            "provider_jobs_planned": [dict(job) for job in self.provider_jobs],
            "provider_jobs_attempted": [],
            "direct_attempt_budget": self.direct_attempt_budget,
            "direct_attempt_used": 0,
            "bridge_retry_budget": self.bridge_retry_budget,
            "bridge_retry_used": 0,
            "retry_posture": "not_evaluated",
            "candidate_fit_status": "not_evaluated",
            "candidate_fit_rejection_reasons": [],
            "bridge_hints": [],
            "bridge_hint_count": 0,
            "lane_completion_posture": "not_evaluated",
            "linkup_sourced_answer_selected": False,
            "linkup_search_results_candidate_surface": (
                any(job.get("provider") == "linkup" for job in self.provider_jobs)
            ),
            "brave_bridge_only": True,
            "exa_selected_by_job_capability": (
                any(job.get("provider") == "exa" for job in self.provider_jobs)
            ),
            "soft_corridor_hard_forced": False,
            "discovery_corridor_us_shortcut": False,
        }


def fast_official_lane_defaults() -> dict[str, Any]:
    """Return skipped trace defaults for runs outside the Fast official lane."""

    return FastOfficialLanePlan(
        used=False,
        skip_reason="not_evaluated",
        corridor="unknown",
        provider_jobs=(),
    ).as_trace()


def build_fast_official_lane_plan(
    *,
    lifecycle_trace: Mapping[str, Any],
    complexity: str,
    search_providers: Iterable[str],
    official_domain_constraints: Iterable[str],
) -> FastOfficialLanePlan:
    """Plan the Fast official lane from existing runtime facts."""

    corridor = "hard_corridor" if list(official_domain_constraints or ()) else "unknown"
    if str(complexity or "").casefold() != "low":
        return FastOfficialLanePlan(
            used=False,
            skip_reason="not_fast_mode",
            corridor=corridor_or_unknown(corridor),
            provider_jobs=(),
        )
    missing = {
        _clean_token(item)
        for item in lifecycle_trace.get("active_source_class_recovery_missing_classes")
        or ()
    }
    if not missing & _OFFICIAL_CLASSES:
        return FastOfficialLanePlan(
            used=False,
            skip_reason="not_official_obligation",
            corridor=corridor_or_unknown(corridor),
            provider_jobs=(),
        )
    if corridor != "hard_corridor":
        return FastOfficialLanePlan(
            used=False,
            skip_reason="not_hard_corridor",
            corridor=corridor_or_unknown(corridor),
            provider_jobs=(),
        )
    if lifecycle_trace.get("active_source_class_recovery_provider_role") != (
        "source_class_recovery"
    ):
        return FastOfficialLanePlan(
            used=False,
            skip_reason="provider_role_unavailable",
            corridor=corridor,
            provider_jobs=(),
        )

    jobs = []
    for provider in _clean_provider_list(search_providers):
        job = _DIRECT_PROVIDER_JOBS.get(provider, "direct_official_candidate_search")
        output_type = "searchResults" if provider == "linkup" else None
        jobs.append(
            {
                "provider": provider,
                "job": job,
                "bridge_only": False,
                "candidate_surface": True,
                "output_type": output_type,
                "answer_endpoint_used": False,
            }
        )
    return FastOfficialLanePlan(
        used=True,
        skip_reason=None,
        corridor=corridor,
        provider_jobs=tuple(jobs),
    )


def record_direct_attempt(
    trace: dict[str, Any],
    *,
    plan: FastOfficialLanePlan,
) -> None:
    lane = _ensure_lane_trace(trace, plan=plan)
    if not plan.used:
        return
    lane["direct_attempt_used"] = 1
    lane["provider_jobs_attempted"] = [dict(job) for job in plan.provider_jobs]


def record_candidate_fit(
    trace: dict[str, Any],
    *,
    status: str,
    rejection_reasons: Iterable[str],
) -> None:
    lane = _ensure_lane_trace(trace)
    lane["candidate_fit_status"] = _clean_token(status) or "unknown"
    lane["candidate_fit_rejection_reasons"] = [
        reason for reason in (_clean_token(item) for item in rejection_reasons) if reason
    ]
    if lane["candidate_fit_status"] == "matched_selected":
        lane["retry_posture"] = "skipped_candidate_fit_passed"
        lane["lane_completion_posture"] = "candidate_fit_passed_no_retry_requested"


def retry_authorized_after_fit_rejection(
    trace: Mapping[str, Any],
    *,
    plan: FastOfficialLanePlan,
) -> bool:
    if not plan.used:
        return False
    lane = trace.get(FAST_OFFICIAL_LANE_TRACE_KEY)
    if not isinstance(lane, Mapping):
        return False
    if int(lane.get("direct_attempt_used") or 0) != 1:
        return False
    if int(lane.get("bridge_retry_used") or 0) >= plan.bridge_retry_budget:
        return False
    reasons = {
        _clean_token(item)
        for item in lane.get("candidate_fit_rejection_reasons") or ()
    }
    return "official_candidate_not_answer_bearing" in reasons


def concrete_bridge_hints_from_diagnostics(
    provider_diagnostics: Iterable[Mapping[str, Any]],
    *,
    known_urls: Iterable[str] = (),
) -> list[OfficialBridgeHint]:
    """Extract citation-ineligible official URL/title hints from sanitized diagnostics."""

    known = {_url_key(url) for url in known_urls if _url_key(url)}
    hints: list[OfficialBridgeHint] = []
    seen: set[tuple[str, str]] = set()
    for attempt in provider_diagnostics or ():
        if not isinstance(attempt, Mapping):
            continue
        role = _clean_token(attempt.get("provider_role"))
        if role not in {"source_class_recovery", "official_scout", "bridge_scout"}:
            continue
        provider = _clean_token(attempt.get("provider")) or None
        provider_job = (
            "early_scout_disambiguation"
            if provider == "brave"
            else "bridge_hint"
        )
        for summary in attempt.get("provider_result_summaries") or ():
            if not isinstance(summary, Mapping):
                continue
            url = _clean_text(summary.get("url"))
            title = _clean_text(summary.get("title"))
            if not (url or title):
                continue
            if url and _url_key(url) in known:
                continue
            key = (_url_key(url), title.casefold())
            if key in seen:
                continue
            seen.add(key)
            hints.append(
                OfficialBridgeHint(
                    official_url=url or None,
                    official_title=title or None,
                    query_term=title or url or None,
                    provider=provider,
                    provider_job=provider_job,
                )
            )
    return hints


def record_bridge_hints(
    trace: dict[str, Any],
    *,
    hints: Iterable[OfficialBridgeHint],
) -> None:
    lane = _ensure_lane_trace(trace)
    hint_payloads = [hint.as_trace() for hint in hints]
    lane["bridge_hints"] = hint_payloads
    lane["bridge_hint_count"] = len(hint_payloads)
    if not hint_payloads and lane.get("retry_posture") == "not_evaluated":
        lane["retry_posture"] = "skipped_no_concrete_bridge_hint"


def record_retry_attempt(
    trace: dict[str, Any],
    *,
    hint: OfficialBridgeHint,
    retry_query: str,
) -> None:
    lane = _ensure_lane_trace(trace)
    lane["bridge_retry_used"] = 1
    lane["retry_posture"] = "used"
    lane["retry_query_preview"] = _clean_text(retry_query, limit=120)
    lane["retry_bridge_hint"] = hint.as_trace()


def record_retry_skipped(
    trace: dict[str, Any],
    *,
    reason: str,
) -> None:
    lane = _ensure_lane_trace(trace)
    if lane.get("retry_posture") in {"used", "skipped_candidate_fit_passed"}:
        return
    lane["retry_posture"] = _clean_token(reason) or "skipped"


def record_retry_fit_result(
    trace: dict[str, Any],
    *,
    status: str,
    rejection_reasons: Iterable[str],
) -> None:
    lane = _ensure_lane_trace(trace)
    lane["retry_candidate_fit_status"] = _clean_token(status) or "unknown"
    lane["retry_candidate_fit_rejection_reasons"] = [
        reason for reason in (_clean_token(item) for item in rejection_reasons) if reason
    ]
    lane["lane_completion_posture"] = (
        "candidate_fit_passed_after_retry"
        if lane["retry_candidate_fit_status"] == "matched_selected"
        else "recipe_exhausted_fail_closed"
    )


def corridor_or_unknown(value: str) -> str:
    text = _clean_token(value)
    return text or "unknown"


def _ensure_lane_trace(
    trace: dict[str, Any],
    *,
    plan: FastOfficialLanePlan | None = None,
) -> dict[str, Any]:
    lane = trace.get(FAST_OFFICIAL_LANE_TRACE_KEY)
    if not isinstance(lane, dict):
        lane = (plan.as_trace() if plan is not None else fast_official_lane_defaults())
        trace[FAST_OFFICIAL_LANE_TRACE_KEY] = lane
    return lane


def _clean_provider_list(values: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values or ():
        provider = _clean_token(value)
        if provider and provider not in out:
            out.append(provider)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = _MAX_TEXT) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text[:limit]


def _clean_token(value: Any) -> str:
    return _clean_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")


def _url_key(value: Any) -> str:
    text = _clean_text(value, limit=240).casefold().rstrip("/")
    text = re.sub(r"^https?://", "", text)
    if text.startswith("www."):
        text = text[4:]
    return text


__all__ = [
    "FAST_OFFICIAL_LANE_SCHEMA_VERSION",
    "FAST_OFFICIAL_LANE_TRACE_KEY",
    "FastOfficialLanePlan",
    "OfficialBridgeHint",
    "build_fast_official_lane_plan",
    "concrete_bridge_hints_from_diagnostics",
    "fast_official_lane_defaults",
    "record_bridge_hints",
    "record_candidate_fit",
    "record_direct_attempt",
    "record_retry_attempt",
    "record_retry_fit_result",
    "record_retry_skipped",
    "retry_authorized_after_fit_rejection",
]
