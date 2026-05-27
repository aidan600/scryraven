"""Runtime arbitration through the controller-owned authority lifecycle.

This module is pure controller/runtime arbitration glue. It does not retrieve,
rank, route providers, build prompts, cite sources, or alter final answers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.authority_lifecycle_contract import (
    AuthorityEvidenceFitState,
    AuthorityExecutionState,
    AuthorityFinalPosture,
    AuthorityLifecycle,
    AuthorityLifecycleAction,
    AuthorityLifecycleBlocker,
    AuthorityLifecycleExecution,
    AuthoritySatisfactionState,
    RecoveryNeededState,
    TerminalStopState,
    WeakCorpusState,
)

AUTHORITY_LIFECYCLE_TRACE_KEY = "authority_lifecycle"
AUTHORITY_LIFECYCLE_ARBITRATION_SCHEMA_VERSION = (
    "authority_lifecycle_runtime_arbitration_ag69b_v1"
)

_TERMINAL_BLOCKERS = frozenset(
    {
        "blocked_by_terminal_stop",
        "terminal_stop_approved",
    }
)
_WEAK_CORPUS_BLOCKERS = frozenset(
    {
        "blocked_by_corpus_weak",
        "blocked_by_weak_corpus_recovery",
        "weak_corpus_recovery_owns_path",
    }
)


@dataclass(frozen=True, slots=True)
class AuthorityRuntimeArbitration:
    """Controller-owned arbitration result for one required authority slot."""

    lifecycle: AuthorityLifecycle
    required_recovery_allowed: bool
    terminal_stop_may_preempt: bool
    weak_corpus_may_own_path: bool
    insufficient_partial_posture_explicit: bool

    @property
    def requirement_id(self) -> str:
        return self.lifecycle.requirement_id

    def permits_blocker(self, blocker: str) -> bool:
        clean = _clean_token(blocker)
        if clean in _TERMINAL_BLOCKERS:
            return self.terminal_stop_may_preempt
        if clean in _WEAK_CORPUS_BLOCKERS:
            return self.weak_corpus_may_own_path
        return True

    def filter_blockers(self, blockers: Iterable[Any]) -> tuple[str, ...]:
        out: list[str] = []
        seen: set[str] = set()
        for blocker in blockers:
            text = _clean_text(blocker)
            if not text or not self.permits_blocker(text):
                continue
            key = text.casefold()
            if key not in seen:
                out.append(text)
                seen.add(key)
        return tuple(out)

    def to_trace_fields(self) -> dict[str, Any]:
        projection = self.lifecycle.to_projection()
        execution_state = dict(projection.get("execution_state") or {})
        execution_blockers = [
            blocker
            for blocker in projection.get("explicit_blockers") or []
            if isinstance(blocker, Mapping)
            and blocker.get("kind") == "recovery_execution_blocked"
        ]
        execution_blocker = execution_blockers[0] if execution_blockers else None
        return {
            "authority_lifecycle_schema_version": (
                AUTHORITY_LIFECYCLE_ARBITRATION_SCHEMA_VERSION
            ),
            AUTHORITY_LIFECYCLE_TRACE_KEY: projection,
            "authority_lifecycle_requirement_id": self.lifecycle.requirement_id,
            "authority_lifecycle_required_authority": (
                self.lifecycle.required_authority
            ),
            "authority_lifecycle_recovery_needed": (
                self.lifecycle.recovery_needed.value
            ),
            "authority_lifecycle_required_recovery_allowed": (
                self.required_recovery_allowed
            ),
            "authority_lifecycle_terminal_stop_may_preempt": (
                self.terminal_stop_may_preempt
            ),
            "authority_lifecycle_weak_corpus_may_own_path": (
                self.weak_corpus_may_own_path
            ),
            "authority_lifecycle_insufficient_partial_posture_explicit": (
                self.insufficient_partial_posture_explicit
            ),
            "authority_lifecycle_execution_state": execution_state.get("state"),
            "authority_lifecycle_execution_attempted": (
                execution_state.get("state") == AuthorityExecutionState.ATTEMPTED.value
            ),
            "authority_lifecycle_execution_blocked": (
                execution_state.get("state") == AuthorityExecutionState.BLOCKED.value
            ),
            "authority_lifecycle_execution_blocker": execution_blocker,
            "authority_lifecycle_execution_blockers": execution_blockers,
            "authority_lifecycle_projection_used_as_control_input": False,
            "authority_lifecycle_control_owner": "controller",
        }


def build_authority_runtime_arbitration(
    *,
    requirement_id: str,
    required_authority: str,
    claim_type: str,
    required_recovery: bool,
    recovery_queries: Sequence[str] = (),
    required_source_classes: Sequence[str] = (),
    recovery_action_allowed: bool = False,
    terminal_stop_approved: bool = False,
    weak_corpus_recovery_used: bool = False,
    corpus_weak: bool = False,
    existing_evidence_fit: AuthorityEvidenceFitState = (
        AuthorityEvidenceFitState.MISSING
    ),
    satisfaction_state: AuthoritySatisfactionState = (
        AuthoritySatisfactionState.UNSATISFIED
    ),
    explicit_blockers: Sequence[AuthorityLifecycleBlocker | Mapping[str, Any]] = (),
    insufficient_partial_posture: bool = False,
) -> AuthorityRuntimeArbitration:
    """Build the controller-owned lifecycle that arbitrates runtime gates."""

    blockers = _coerce_blockers(explicit_blockers, requirement_id=requirement_id)
    if recovery_action_allowed and not recovery_queries:
        blockers = (
            *blockers,
            AuthorityLifecycleBlocker.controller_lifecycle_execution(
                requirement_id,
                "missing_executable_recovery_query",
                recovery_may_be_retried=True,
            ),
        )
    has_hard_blocker = any(
        blocker.is_controller_hard_for(requirement_id) for blocker in blockers
    )
    has_execution_blocker = any(
        blocker.kind == "recovery_execution_blocked"
        and blocker.is_controller_hard_for(requirement_id)
        for blocker in blockers
    )
    recovery_needed = (
        RecoveryNeededState.REQUIRED if required_recovery else RecoveryNeededState.NOT_NEEDED
    )
    recovery_action = (
        AuthorityLifecycleAction.approved_recovery(
            requirement_id,
            recovery_queries=recovery_queries,
            required_source_classes=required_source_classes,
            reason="controller_required_authority_recovery_allowed",
        )
        if recovery_action_allowed
        else None
    )
    final_posture = (
        AuthorityFinalPosture.INSUFFICIENT_PARTIAL
        if insufficient_partial_posture or has_execution_blocker
        else AuthorityFinalPosture.BLOCKED
        if has_hard_blocker
        else AuthorityFinalPosture.OPEN
    )
    execution_state = AuthorityLifecycleExecution(
        state=(
            AuthorityExecutionState.BLOCKED
            if recovery_action_allowed and has_hard_blocker
            else
            AuthorityExecutionState.APPROVED_PENDING_EXECUTION
            if recovery_action_allowed
            else AuthorityExecutionState.NOT_REQUESTED
        ),
        explanation=(
            blockers[0].reason
            if recovery_action_allowed and has_hard_blocker and blockers
            else None
        ),
    )
    lifecycle = AuthorityLifecycle(
        requirement_id=requirement_id,
        required_authority=required_authority,
        claim_type=claim_type,
        existing_evidence_fit=existing_evidence_fit,
        recovery_needed=recovery_needed,
        recovery_query_count=len(tuple(recovery_queries)),
        admission_used=recovery_action_allowed,
        eligible=recovery_action_allowed,
        recovery_action=recovery_action,
        terminal_stop_state=(
            TerminalStopState.APPROVED
            if terminal_stop_approved
            else TerminalStopState.NOT_APPROVED
        ),
        weak_corpus_state=(
            WeakCorpusState.OWNS_PATH
            if weak_corpus_recovery_used or corpus_weak
            else WeakCorpusState.NOT_PRESENT
        ),
        execution_state=execution_state,
        satisfaction_state=satisfaction_state,
        final_posture=final_posture,
        explicit_blockers=blockers,
    )
    required_recovery_allowed = bool(
        required_recovery
        and recovery_action_allowed
        and recovery_queries
        and not has_hard_blocker
        and not insufficient_partial_posture
    )
    terminal_stop_may_preempt = bool(
        terminal_stop_approved and not required_recovery_allowed
    )
    weak_corpus_may_own_path = bool(
        (weak_corpus_recovery_used or corpus_weak) and not required_recovery_allowed
    )
    return AuthorityRuntimeArbitration(
        lifecycle=lifecycle,
        required_recovery_allowed=required_recovery_allowed,
        terminal_stop_may_preempt=terminal_stop_may_preempt,
        weak_corpus_may_own_path=weak_corpus_may_own_path,
        insufficient_partial_posture_explicit=insufficient_partial_posture,
    )


def _coerce_blockers(
    values: Sequence[AuthorityLifecycleBlocker | Mapping[str, Any]],
    *,
    requirement_id: str,
) -> tuple[AuthorityLifecycleBlocker, ...]:
    blockers: list[AuthorityLifecycleBlocker] = []
    for value in values:
        if isinstance(value, AuthorityLifecycleBlocker):
            blockers.append(value)
            continue
        if not isinstance(value, Mapping):
            continue
        blocker_requirement_id = _clean_text(value.get("requirement_id"))
        kind = _clean_text(value.get("kind"))
        reason = _clean_text(value.get("reason")) or kind
        owner = _clean_text(value.get("owner")) or "controller"
        hard = value.get("hard", True) is True
        recovery_may_be_retried = value.get("recovery_may_be_retried") is True
        final_posture_must_be_insufficient_partial = (
            value.get("final_posture_must_be_insufficient_partial", True) is True
        )
        if not kind:
            continue
        blockers.append(
            AuthorityLifecycleBlocker(
                requirement_id=blocker_requirement_id or requirement_id,
                kind=kind,
                reason=reason or kind,
                owner=owner,
                hard=hard,
                recovery_may_be_retried=recovery_may_be_retried,
                final_posture_must_be_insufficient_partial=(
                    final_posture_must_be_insufficient_partial
                ),
            )
        )
    return tuple(blockers)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text or None


def _clean_token(value: Any) -> str:
    return (_clean_text(value) or "").casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "AUTHORITY_LIFECYCLE_ARBITRATION_SCHEMA_VERSION",
    "AUTHORITY_LIFECYCLE_TRACE_KEY",
    "AuthorityRuntimeArbitration",
    "build_authority_runtime_arbitration",
]
