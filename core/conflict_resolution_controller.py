"""Pure passive controller shapes for conflict-resolution retrieval.

The controller owns only the bounded decision contract for a future
conflict-resolution executor. It does not retrieve, route providers, choose
providers, alter prompts, persist data, or call models.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

CONFLICT_RESOLUTION_PROVIDER_ROLE = "conflict_resolution"
CONFLICT_RESOLUTION_STAGE = "conflict_resolution"

_MAX_CONFLICT_RESOLUTION_QUERIES = 2
_SKIP_REASON_PRIORITY = (
    "not_evaluated",
    "no_conflict",
    "blocked_by_wrong_phase",
    "blocked_by_author_phase",
    "blocked_by_post_analyst_phase",
    "already_attempted",
    "blocked_by_iteration_budget",
    "blocked_by_provider_policy_change_required",
    "blocked_by_search_depth_policy_change_required",
    "no_resolving_queries",
)
_NO_ACTION_REASONS = {"no_conflict"}
_ALLOWED_PHASE = "pre_analyst"
_AUTHOR_PHASE = "author"
_POST_ANALYST_PHASE = "post_analyst"
_SENSITIVE_METADATA_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "password",
        "prompt",
        "provider_payload",
        "raw_provider_payload",
        "raw_prompt",
        "raw_trace",
        "secret",
        "token",
    }
)


class ConflictResolutionControllerDecision(str, Enum):
    """Stable conflict-resolution decision values."""

    NO_ACTION = "no_action"
    BLOCKED_WITH_REASON = "blocked_with_reason"
    RUN_CONFLICT_RESOLUTION = "run_conflict_resolution"


@dataclass(frozen=True)
class ConflictResolutionControllerInput:
    """Compact post-retrieval snapshot for conflict-resolution decisions."""

    conflicts_present: bool
    conflict_notes: tuple[str, ...] = ()
    resolving_queries: tuple[str, ...] = ()
    ordinary_next_queries: tuple[str, ...] = ()
    current_search_depth: str | None = None
    iteration_budget_available: bool = False
    prior_attempt_count: int = 0
    provider_policy_reusable: bool = True
    provider_swap_required: bool = False
    search_depth_reusable: bool = True
    search_depth_escalation_required: bool = False
    lifecycle_phase: str = _ALLOWED_PHASE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflicts_present": bool(self.conflicts_present),
            "conflict_notes": list(self.conflict_notes),
            "resolving_queries": list(self.resolving_queries),
            "ordinary_next_query_count": len(self.ordinary_next_queries),
            "current_search_depth": self.current_search_depth,
            "iteration_budget_available": bool(self.iteration_budget_available),
            "prior_attempt_count": max(0, int(self.prior_attempt_count or 0)),
            "provider_policy_reusable": bool(self.provider_policy_reusable),
            "provider_swap_required": bool(self.provider_swap_required),
            "search_depth_reusable": bool(self.search_depth_reusable),
            "search_depth_escalation_required": bool(
                self.search_depth_escalation_required
            ),
            "lifecycle_phase": self.lifecycle_phase,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class ConflictResolutionDecision:
    """Controller-owned decision and approved conflict-resolution parameters."""

    decision: ConflictResolutionControllerDecision
    reason: str | None
    blockers: tuple[str, ...] = ()
    conflict_notes: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()
    provider_role: str | None = None
    search_depth: str | None = None
    attempt_count: int = 0
    stage: str = CONFLICT_RESOLUTION_STAGE

    @property
    def approved(self) -> bool:
        return self.decision is (
            ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "conflict_notes": list(self.conflict_notes),
            "queries": list(self.queries),
            "provider_role": self.provider_role,
            "search_depth": self.search_depth,
            "attempt_count": max(0, int(self.attempt_count or 0)),
            "stage": self.stage,
        }


@dataclass(frozen=True)
class ConflictResolutionLifecycle:
    """Trace-friendly passive lifecycle object for a conflict decision."""

    snapshot: ConflictResolutionControllerInput
    decision: ConflictResolutionDecision

    def to_trace_fields(self) -> dict[str, Any]:
        approved = self.decision.approved
        considered = bool(self.snapshot.conflicts_present)
        return _trace_payload(
            considered=considered,
            eligible=approved,
            used=False,
            reason=self.decision.reason,
            skip_reason=None if approved else self.decision.reason,
            blockers=list(self.decision.blockers),
            conflict_notes=list(self.decision.conflict_notes),
            queries=list(self.decision.queries),
            provider_role=self.decision.provider_role,
            search_depth=self.decision.search_depth,
            attempt_count=self.decision.attempt_count,
            stage=self.decision.stage if approved else None,
        )


def _copy_string_list(value: Any, *, cap: int | None = None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if cap is not None and len(out) >= cap:
            break
    return tuple(out)


def _clean_phase(value: Any) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    return text or _ALLOWED_PHASE


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").strip().casefold()
    return text.startswith("raw_") or text in _SENSITIVE_METADATA_KEYS


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _json_safe_metadata(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return str(value)


def _json_safe_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in dict(metadata or {}).items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _json_safe_value(value)
    return out


def _first_skip_reason(blockers: tuple[str, ...]) -> str | None:
    for reason in _SKIP_REASON_PRIORITY:
        if reason in blockers:
            return reason
    return blockers[0] if blockers else None


def _trace_payload(
    *,
    considered: bool,
    eligible: bool,
    used: bool,
    reason: str | None,
    skip_reason: str | None,
    blockers: list[str],
    conflict_notes: list[str],
    queries: list[str],
    provider_role: str | None,
    search_depth: str | None,
    attempt_count: int,
    stage: str | None,
) -> dict[str, Any]:
    return {
        "active_conflict_resolution_considered": bool(considered),
        "active_conflict_resolution_eligible": bool(eligible),
        "active_conflict_resolution_used": bool(used),
        "active_conflict_resolution_reason": reason,
        "active_conflict_resolution_skip_reason": skip_reason,
        "active_conflict_resolution_blockers": list(blockers),
        "active_conflict_resolution_conflict_notes": list(conflict_notes),
        "active_conflict_resolution_queries": list(queries),
        "active_conflict_resolution_result_count": 0,
        "active_conflict_resolution_new_url_count": 0,
        "active_conflict_resolution_provider_role": provider_role,
        "active_conflict_resolution_search_depth": search_depth,
        "active_conflict_resolution_attempt_count": max(
            0,
            int(attempt_count or 0),
        ),
        "active_conflict_resolution_stage": stage,
    }


def build_conflict_resolution_controller_input(
    *,
    conflicts_present: bool,
    conflict_notes: list[str] | tuple[str, ...] = (),
    resolving_queries: list[str] | tuple[str, ...] = (),
    ordinary_next_queries: list[str] | tuple[str, ...] = (),
    current_search_depth: str | None,
    iteration_budget_available: bool,
    prior_attempt_count: int,
    provider_policy_reusable: bool = True,
    provider_swap_required: bool = False,
    search_depth_reusable: bool = True,
    search_depth_escalation_required: bool = False,
    lifecycle_phase: str = _ALLOWED_PHASE,
    metadata: Mapping[str, Any] | None = None,
) -> ConflictResolutionControllerInput:
    """Build a sanitized conflict-resolution snapshot from known facts."""
    return ConflictResolutionControllerInput(
        conflicts_present=bool(conflicts_present),
        conflict_notes=_copy_string_list(conflict_notes),
        resolving_queries=_copy_string_list(
            resolving_queries,
            cap=_MAX_CONFLICT_RESOLUTION_QUERIES,
        ),
        ordinary_next_queries=_copy_string_list(ordinary_next_queries),
        current_search_depth=(
            str(current_search_depth) if current_search_depth is not None else None
        ),
        iteration_budget_available=bool(iteration_budget_available),
        prior_attempt_count=max(0, int(prior_attempt_count or 0)),
        provider_policy_reusable=bool(provider_policy_reusable),
        provider_swap_required=bool(provider_swap_required),
        search_depth_reusable=bool(search_depth_reusable),
        search_depth_escalation_required=bool(search_depth_escalation_required),
        lifecycle_phase=_clean_phase(lifecycle_phase),
        metadata=deepcopy(dict(metadata or {})),
    )


def decide_conflict_resolution(
    snapshot: ConflictResolutionControllerInput,
) -> ConflictResolutionDecision:
    """Return no_action, blocked_with_reason, or run_conflict_resolution."""
    blockers: list[str] = []

    if not snapshot.conflicts_present:
        blockers.append("no_conflict")
    if snapshot.lifecycle_phase != _ALLOWED_PHASE:
        blockers.append("blocked_by_wrong_phase")
        if snapshot.lifecycle_phase == _AUTHOR_PHASE:
            blockers.append("blocked_by_author_phase")
        elif snapshot.lifecycle_phase == _POST_ANALYST_PHASE:
            blockers.append("blocked_by_post_analyst_phase")
    if snapshot.prior_attempt_count > 0:
        blockers.append("already_attempted")
    if not snapshot.iteration_budget_available:
        blockers.append("blocked_by_iteration_budget")
    if not snapshot.provider_policy_reusable or snapshot.provider_swap_required:
        blockers.append("blocked_by_provider_policy_change_required")
    if (
        not snapshot.search_depth_reusable
        or snapshot.search_depth_escalation_required
    ):
        blockers.append("blocked_by_search_depth_policy_change_required")
    if snapshot.conflicts_present and not snapshot.resolving_queries:
        blockers.append("no_resolving_queries")

    blocker_tuple = tuple(blockers)
    eligible = snapshot.conflicts_present and not blocker_tuple
    attempt_count = snapshot.prior_attempt_count + (1 if eligible else 0)
    reason = None if eligible else _first_skip_reason(blocker_tuple)

    if eligible:
        return ConflictResolutionDecision(
            decision=ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION,
            reason="material_conflict_resolution_available",
            conflict_notes=snapshot.conflict_notes,
            queries=snapshot.resolving_queries,
            provider_role=CONFLICT_RESOLUTION_PROVIDER_ROLE,
            search_depth=snapshot.current_search_depth,
            attempt_count=attempt_count,
        )
    if reason in _NO_ACTION_REASONS:
        decision = ConflictResolutionControllerDecision.NO_ACTION
    else:
        decision = ConflictResolutionControllerDecision.BLOCKED_WITH_REASON
    return ConflictResolutionDecision(
        decision=decision,
        reason=reason,
        blockers=blocker_tuple,
        conflict_notes=snapshot.conflict_notes,
        queries=snapshot.resolving_queries,
        attempt_count=attempt_count,
    )


def build_conflict_resolution_lifecycle(
    snapshot: ConflictResolutionControllerInput,
) -> ConflictResolutionLifecycle:
    """Return the passive lifecycle object for a conflict-resolution decision."""
    return ConflictResolutionLifecycle(
        snapshot=snapshot,
        decision=decide_conflict_resolution(snapshot),
    )


def conflict_resolution_lifecycle_defaults() -> dict[str, Any]:
    """Return default active_conflict_resolution_* trace fields."""
    return _trace_payload(
        considered=False,
        eligible=False,
        used=False,
        reason="not_evaluated",
        skip_reason="not_evaluated",
        blockers=["not_evaluated"],
        conflict_notes=[],
        queries=[],
        provider_role=None,
        search_depth=None,
        attempt_count=0,
        stage=None,
    )


__all__ = [
    "CONFLICT_RESOLUTION_PROVIDER_ROLE",
    "CONFLICT_RESOLUTION_STAGE",
    "ConflictResolutionControllerDecision",
    "ConflictResolutionControllerInput",
    "ConflictResolutionDecision",
    "ConflictResolutionLifecycle",
    "build_conflict_resolution_controller_input",
    "build_conflict_resolution_lifecycle",
    "conflict_resolution_lifecycle_defaults",
    "decide_conflict_resolution",
]
