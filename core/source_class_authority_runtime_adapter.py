"""Bounded runtime reads for source-class AuthorityLifecycle state.

This adapter normalizes canonical source-class recovery authority projections
for pipeline callsites. It does not schedule retrieval, mutate traces, call
providers or models, generate queries, rank evidence, or alter Author/citation
behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)
from core.controller_loop_spine import checkpoint_action_name_from_trace

_CHECKPOINT_REFRESH_BLOCKER_REASONS = frozenset(
    {
        "blocked_by_weak_corpus_recovery",
        "blocked_by_corpus_weak",
        "terminal_stop" + "_approved",
    }
)
_TERMINAL_STOP_ACTIONS = frozenset(
    {
        STOP_INSUFFICIENT_WITH_CAVEAT,
        STOP_SUFFICIENT,
    }
)


def source_class_recovery_authority_projection(
    lifecycle_trace: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Return the canonical AuthorityLifecycle projection if present."""

    trace = lifecycle_trace if isinstance(lifecycle_trace, Mapping) else {}
    authority = trace.get("authority_lifecycle")
    return authority if isinstance(authority, Mapping) else {}


def source_class_recovery_authority_action(
    lifecycle_trace: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Return the canonical recovery action projection if present."""

    action = source_class_recovery_authority_projection(lifecycle_trace).get(
        "recovery_action"
    )
    return action if isinstance(action, Mapping) else {}


def source_class_recovery_execution_state(
    lifecycle_trace: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Return the canonical recovery execution-state projection if present."""

    execution = source_class_recovery_authority_projection(lifecycle_trace).get(
        "execution_state"
    )
    return execution if isinstance(execution, Mapping) else {}


def source_class_recovery_action_approved(
    lifecycle_trace: Mapping[str, Any] | None,
) -> bool:
    """Return whether canonical recovery action approves source-class recovery."""

    action = source_class_recovery_authority_action(lifecycle_trace)
    return bool(
        action.get("action_type") == RECOVER_MISSING_SOURCE_CLASS
        and action.get("approved") is True
    )


def source_class_recovery_action_pending(
    lifecycle_trace: Mapping[str, Any] | None,
) -> bool:
    """Return whether canonical recovery execution is still pending."""

    execution = source_class_recovery_execution_state(lifecycle_trace)
    return execution.get("state") in {"approved_pending_execution", None}


def source_class_recovery_action_attempted(
    lifecycle_trace: Mapping[str, Any] | None,
) -> bool:
    """Return whether canonical recovery execution has been attempted."""

    return source_class_recovery_execution_state(lifecycle_trace).get(
        "state"
    ) == "attempted"


def source_class_recovery_authority_blocker_reasons(
    lifecycle_trace: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Return canonical explicit blocker reasons as normalized text."""

    blockers = source_class_recovery_authority_projection(lifecycle_trace).get(
        "explicit_blockers"
    )
    if not isinstance(blockers, (list, tuple)):
        return ()
    out: list[str] = []
    for item in blockers:
        if not isinstance(item, Mapping):
            continue
        reason = item.get("blocker_reason") or item.get("reason") or item.get("kind")
        text = " ".join(str(reason or "").strip().split())
        if text:
            out.append(text)
    return tuple(out)


def source_class_recovery_checkpoint_refresh_allowed(
    *,
    checkpoint_trace: Mapping[str, Any] | None,
    active_source_class_recovery_lifecycle: Mapping[str, Any] | None,
) -> bool:
    """Return whether a stale non-terminal checkpoint may be refreshed."""

    action = source_class_recovery_authority_action(
        active_source_class_recovery_lifecycle
    )
    required_classes = action.get("required_source_classes")
    recovery_action_approved = bool(
        source_class_recovery_action_approved(
            active_source_class_recovery_lifecycle
        )
        and isinstance(required_classes, list)
        and required_classes
        and source_class_recovery_action_pending(
            active_source_class_recovery_lifecycle
        )
    )
    checkpoint_action = checkpoint_action_name_from_trace(checkpoint_trace)
    blockers = set(
        source_class_recovery_authority_blocker_reasons(
            active_source_class_recovery_lifecycle
        )
    )
    return bool(
        recovery_action_approved
        and checkpoint_action not in _TERMINAL_STOP_ACTIONS
        and not blockers & _CHECKPOINT_REFRESH_BLOCKER_REASONS
    )


__all__ = [
    "source_class_recovery_action_approved",
    "source_class_recovery_action_attempted",
    "source_class_recovery_action_pending",
    "source_class_recovery_authority_action",
    "source_class_recovery_authority_blocker_reasons",
    "source_class_recovery_authority_projection",
    "source_class_recovery_checkpoint_refresh_allowed",
    "source_class_recovery_execution_state",
]
