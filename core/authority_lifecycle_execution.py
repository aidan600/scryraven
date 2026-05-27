"""AuthorityLifecycle execution-state bridge for source-class recovery.

This module observes the existing source-class recovery executor boundary. It
does not retrieve, route providers, rank/filter sources, classify returned
source fit, alter prompts, cite sources, or affect final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

AUTHORITY_LIFECYCLE_EXECUTION_SCHEMA_VERSION = (
    "authority_lifecycle_execution_ag69c_v1"
)
_EXECUTION_BLOCKER_KIND = "recovery_execution_blocked"
_OWNER = "controller/lifecycle"


def record_authority_lifecycle_executor_entrypoint_reached(
    lifecycle_trace: dict[str, Any],
    *,
    result_count: int = 0,
    recovered_result_count: int = 0,
    accepted_url_count: int = 0,
    explanation: str = "source_class_recovery_executor_entrypoint_reached",
) -> dict[str, Any]:
    """Record that the real source-class recovery executor path was entered."""

    authority = _authority_lifecycle(lifecycle_trace)
    if authority is None:
        return lifecycle_trace
    authority["execution_state"] = {
        **_mapping(authority.get("execution_state")),
        "state": "attempted",
        "result_count": _non_negative_int(result_count),
        "recovered_result_count": _non_negative_int(recovered_result_count),
        "accepted_url_count": _non_negative_int(accepted_url_count),
        "explanation": explanation,
    }
    authority["final_posture"] = "action_executed"
    authority["terminal_paths"] = ["approved_action_executed"]
    _project_execution_state(lifecycle_trace)
    return lifecycle_trace


def record_authority_lifecycle_execution_blocked(
    lifecycle_trace: dict[str, Any],
    *,
    blocker_reason: str,
    recovery_may_be_retried: bool = False,
) -> dict[str, Any]:
    """Record a requirement-bound lifecycle blocker for non-execution."""

    authority = _authority_lifecycle(lifecycle_trace)
    if authority is None or _execution_attempted(authority):
        return lifecycle_trace
    requirement_id = _text(authority.get("requirement_id"))
    if not requirement_id or not _recovery_approved(authority, lifecycle_trace):
        return lifecycle_trace
    blocker = {
        "requirement_id": requirement_id,
        "kind": _EXECUTION_BLOCKER_KIND,
        "reason": blocker_reason,
        "owner": _OWNER,
        "hard": True,
        "blocker_reason": blocker_reason,
        "blocker_owner": _OWNER,
        "recovery_may_be_retried": bool(recovery_may_be_retried),
        "final_posture_must_be_insufficient_partial": True,
    }
    blockers = [
        item
        for item in authority.get("explicit_blockers") or []
        if isinstance(item, Mapping)
        and not (
            item.get("kind") == _EXECUTION_BLOCKER_KIND
            and item.get("requirement_id") == requirement_id
        )
    ]
    blockers.append(blocker)
    authority["explicit_blockers"] = blockers
    authority["execution_state"] = {
        **_mapping(authority.get("execution_state")),
        "state": "blocked",
        "result_count": 0,
        "recovered_result_count": 0,
        "accepted_url_count": 0,
        "explanation": blocker_reason,
    }
    authority["final_posture"] = "insufficient_partial"
    authority["terminal_paths"] = ["controller_hard_blocker"]
    _project_execution_state(lifecycle_trace)
    return lifecycle_trace


def sync_authority_lifecycle_execution_from_source_class_trace(
    lifecycle_trace: dict[str, Any],
) -> dict[str, Any]:
    """Project executor/candidate observations into the lifecycle trace."""

    authority = _authority_lifecycle(lifecycle_trace)
    if authority is None:
        return lifecycle_trace
    execution = _mapping(authority.get("execution_state"))
    if execution.get("state") == "attempted":
        result_count = _non_negative_int(
            lifecycle_trace.get("active_source_class_recovery_result_count")
        )
        accepted_url_count = _non_negative_int(
            lifecycle_trace.get("accepted_url_count")
            if lifecycle_trace.get("accepted_url_count") != "unknown"
            else lifecycle_trace.get("recovered_accepted_url_count")
        )
        authority["execution_state"] = {
            **execution,
            "result_count": result_count,
            "recovered_result_count": _non_negative_int(
                lifecycle_trace.get("recovered_result_count")
                if lifecycle_trace.get("recovered_result_count") != "unknown"
                else result_count
            ),
            "accepted_url_count": accepted_url_count,
        }
        authority["candidate_acquisition_state"] = _candidate_acquisition_state(
            lifecycle_trace
        )
        candidate_fit = _mapping(authority.get("candidate_fit"))
        authority["candidate_return_status"] = _candidate_return_status_from_execution(
            result_count=result_count,
            recovered_result_count=_non_negative_int(
                authority["execution_state"].get("recovered_result_count")
            ),
            accepted_url_count=accepted_url_count,
        )
        authority["candidate_fit"] = {
            **candidate_fit,
            "candidate_return_status": authority["candidate_return_status"],
            "accepted_url_count": accepted_url_count,
            "fit_state": candidate_fit.get("fit_state", "not_evaluated"),
            "rejection_reasons": list(candidate_fit.get("rejection_reasons") or []),
            "selected_evidence_ids": list(
                candidate_fit.get("selected_evidence_ids") or []
            ),
        }
    _project_execution_state(lifecycle_trace)
    return lifecycle_trace


def source_class_recovery_execution_blocked_if_needed(
    lifecycle_trace: dict[str, Any],
    *,
    authorized_for_executor: bool,
    blocker_reason: str = "source_class_recovery_executor_dispatch_not_authorized",
) -> dict[str, Any]:
    """Block approved lifecycle recovery if the orchestrator did not dispatch it."""

    if authorized_for_executor:
        return lifecycle_trace
    authority = _authority_lifecycle(lifecycle_trace)
    if authority is None or _execution_attempted(authority) or _execution_blocked(authority):
        return lifecycle_trace
    if not _recovery_approved(authority, lifecycle_trace):
        return lifecycle_trace
    record_authority_lifecycle_execution_blocked(
        lifecycle_trace,
        blocker_reason=blocker_reason,
        recovery_may_be_retried=True,
    )
    return lifecycle_trace


def _project_execution_state(lifecycle_trace: dict[str, Any]) -> None:
    authority = _authority_lifecycle(lifecycle_trace)
    if authority is None:
        return
    execution = _mapping(authority.get("execution_state"))
    state = _text(execution.get("state")) or "not_requested"
    attempted = state == "attempted"
    blocked = state == "blocked"
    blockers = [
        dict(item)
        for item in authority.get("explicit_blockers") or []
        if isinstance(item, Mapping)
        and item.get("kind") == _EXECUTION_BLOCKER_KIND
    ]
    blocker = blockers[0] if blockers else None
    lifecycle_trace["authority_lifecycle_execution_schema_version"] = (
        AUTHORITY_LIFECYCLE_EXECUTION_SCHEMA_VERSION
    )
    lifecycle_trace["authority_lifecycle"] = authority
    lifecycle_trace["authority_lifecycle_execution_state"] = state
    lifecycle_trace["authority_lifecycle_execution_attempted"] = attempted
    lifecycle_trace["authority_lifecycle_execution_blocked"] = blocked
    lifecycle_trace["authority_lifecycle_execution_blocker"] = blocker
    lifecycle_trace["authority_lifecycle_execution_blockers"] = blockers
    lifecycle_trace["active_source_class_recovery_execution_attempted"] = attempted
    if attempted:
        lifecycle_trace["active_source_class_recovery_used"] = True
        lifecycle_trace["active_source_class_recovery_skip_reason"] = None
    elif blocked and blocker is not None:
        lifecycle_trace["active_source_class_recovery_used"] = False
        reason = _text(blocker.get("blocker_reason")) or _text(blocker.get("reason"))
        lifecycle_trace["active_source_class_recovery_skip_reason"] = reason
        _append_legacy_blocker(lifecycle_trace, reason)


def _authority_lifecycle(lifecycle_trace: dict[str, Any]) -> dict[str, Any] | None:
    authority = lifecycle_trace.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return None
    if not isinstance(authority, dict):
        authority = dict(authority)
        lifecycle_trace["authority_lifecycle"] = authority
    return authority


def _recovery_approved(
    authority: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    action = authority.get("recovery_action")
    if isinstance(action, Mapping) and action.get("approved") is True:
        return True
    return bool(
        lifecycle_trace.get("active_source_class_recovery_eligible")
        or lifecycle_trace.get("active_source_class_recovery_official_canonical_admitted")
    )


def _execution_attempted(authority: Mapping[str, Any]) -> bool:
    return _mapping(authority.get("execution_state")).get("state") == "attempted"


def _execution_blocked(authority: Mapping[str, Any]) -> bool:
    return _mapping(authority.get("execution_state")).get("state") == "blocked"


def _candidate_acquisition_state(lifecycle_trace: Mapping[str, Any]) -> str:
    if lifecycle_trace.get("candidate_acquisition_result_status") == (
        "provider_results_returned"
    ):
        return "provider_results_returned"
    if lifecycle_trace.get("acquisition_attempted") is True:
        return "attempted"
    return "not_attempted"


def _candidate_return_status_from_execution(
    *,
    result_count: int,
    recovered_result_count: int,
    accepted_url_count: int,
) -> str:
    if result_count > 0 or recovered_result_count > 0 or accepted_url_count > 0:
        return "candidates_returned"
    return "no_candidates"


def _append_legacy_blocker(lifecycle_trace: dict[str, Any], reason: str | None) -> None:
    if not reason:
        return
    blockers = list(lifecycle_trace.get("active_source_class_recovery_blockers") or [])
    if reason not in blockers:
        blockers.append(reason)
    lifecycle_trace["active_source_class_recovery_blockers"] = blockers


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text or None


def _non_negative_int(value: Any) -> int:
    if value is None or isinstance(value, bool) or value == "unknown":
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "AUTHORITY_LIFECYCLE_EXECUTION_SCHEMA_VERSION",
    "record_authority_lifecycle_execution_blocked",
    "record_authority_lifecycle_executor_entrypoint_reached",
    "source_class_recovery_execution_blocked_if_needed",
    "sync_authority_lifecycle_execution_from_source_class_trace",
]
