"""Controller-owned provider/search allocation review gate for AG-75A."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    ControllerRecoveryDecision,
)

PROVIDER_SEARCH_ALLOCATION_TRACE_KEY = "provider_search_allocation_trace"
PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION = (
    "controller_provider_search_allocation_gate_ag75a_v1"
)
PROVIDER_SEARCH_ALLOCATION_ACTION = "record_provider_search_review_request"

_NO_CANDIDATE_REASON = "no_candidate_acquired_provider_search_review_needed"
_NO_CANDIDATE_STATE = "no_plausible_official_current_candidate_acquired"


@dataclass(frozen=True)
class ProviderSearchAllocationGateResult:
    """Mechanical result for the AG-75A provider/search allocation gate."""

    allocated: bool
    reason: str
    trace: dict[str, Any] | None = None


def build_provider_search_allocation_record(
    decision: ControllerRecoveryDecision | None,
) -> dict[str, Any] | None:
    """Return a bounded allocation-review record only for Controller approval."""

    if decision is None:
        return None
    payload = decision.payload
    decision_reason = str(payload.get("decision_reason") or "")
    candidate_state = str(payload.get("candidate_state_summary") or "")
    if decision.decision != REQUEST_PROVIDER_SEARCH_REVIEW:
        return None
    if decision.provider_search_review_requested is not True:
        return None
    if payload.get("allowed_executor_action") != PROVIDER_SEARCH_ALLOCATION_ACTION:
        return None
    if decision_reason != _NO_CANDIDATE_REASON and candidate_state != _NO_CANDIDATE_STATE:
        return None

    return {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "allocation_owner": "ControllerRecoveryDecision",
        "mechanical_owner": "source_class_recovery_runner",
        "decision": REQUEST_PROVIDER_SEARCH_REVIEW,
        "decision_reason": decision_reason,
        "candidate_state_summary": candidate_state,
        "allocation_action": PROVIDER_SEARCH_ALLOCATION_ACTION,
        "allocation_shape": "bounded_record_only_provider_search_review",
        "execution_mode": "record_only_no_provider_call",
        "provider_search_review_requested": True,
        "provider_policy_unchanged": True,
        "provider_selection_unchanged": True,
        "search_depth_policy_unchanged": True,
        "query_strategy_unchanged": True,
        "new_provider_added": False,
        "provider_swap": False,
        "unbounded_depth": False,
        "live_validation_used": False,
        "final_answer_behavior_unchanged": True,
        "citation_behavior_unchanged": True,
    }


def record_provider_search_allocation_if_controller_authorized(
    lifecycle_trace: dict[str, Any],
    decision: ControllerRecoveryDecision | None,
) -> ProviderSearchAllocationGateResult:
    """Record a provider/search allocation review request if Controller-approved."""

    record = build_provider_search_allocation_record(decision)
    if record is None:
        return ProviderSearchAllocationGateResult(
            allocated=False,
            reason="controller_recovery_decision_did_not_request_provider_search_review",
        )

    lifecycle_trace.update(decision.to_executor_trace_fields())
    lifecycle_trace[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY] = {
        "schema_version": PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION,
        "trace_mode": "controller_authorized_provider_search_allocation_record",
        "ProviderSearchAllocation": dict(record),
    }
    lifecycle_trace["active_source_class_recovery_skip_reason"] = (
        "controller_recovery_decision_requested_provider_search_review"
    )
    lifecycle_trace["active_source_class_recovery_blockers"] = list(
        lifecycle_trace.get("active_source_class_recovery_blockers") or []
    ) + [REQUEST_PROVIDER_SEARCH_REVIEW]

    return ProviderSearchAllocationGateResult(
        allocated=True,
        reason=PROVIDER_SEARCH_ALLOCATION_ACTION,
        trace=dict(record),
    )


__all__ = [
    "PROVIDER_SEARCH_ALLOCATION_ACTION",
    "PROVIDER_SEARCH_ALLOCATION_SCHEMA_VERSION",
    "PROVIDER_SEARCH_ALLOCATION_TRACE_KEY",
    "ProviderSearchAllocationGateResult",
    "build_provider_search_allocation_record",
    "record_provider_search_allocation_if_controller_authorized",
]
