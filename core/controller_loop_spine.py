"""Pure checkpoint promotion and compatibility dispatch authorization spine.

This module owns the AG-33 through AG-37B control-plane arbitration around the
evidence-integration checkpoint. It consumes compact, sanitized runtime facts
and returns JSON-safe trace and authorization fields. It does not execute
retrieval, choose providers, route depth, build prompts, persist data, or alter
handoffs. Source-class recovery dispatch is no longer owned here; source-class
spine fields are diagnostic compatibility traces for the canonical
AuthorityLifecycle.recovery_action -> SourceClassRecoveryRunner path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.ordinary_continuation_candidate import (
    ORDINARY_CONTINUATION_TRACE_KEY,
    bounded_continuation_authorization_reason,
    is_bounded_spine_authorized_continuation_candidate,
    mark_ordinary_continuation_candidate_spine_authorized,
    ordinary_continuation_candidate_defaults,
)

RECOVER_MISSING_SOURCE_CLASS = "recover_missing_source_class"
RECOVER_WEAK_CORPUS = "recover_weak_corpus"
RESOLVE_CONFLICT = "resolve_conflict"
STOP_INSUFFICIENT_WITH_CAVEAT = "stop_insufficient_with_caveat"
STOP_SUFFICIENT = "stop_sufficient"
SOURCE_CLASS_SPINE_TRACE_ROLE = "diagnostic_compatibility"
SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY = "authority_lifecycle.recovery_action"
_TARGETED_RETRIEVAL_ACTION_NAME = "retrieve_targeted"
_TARGETED_RUNTIME_DISPATCH_NOT_INVERTED = (
    "blocked_by_runtime_dispatch_not_inverted"
)

_TERMINAL_STOP_ACTIONS = {
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
}

_OFFICIAL_CURRENT_RECOVERY_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)


@dataclass(frozen=True)
class ControllerLoopActionCandidate:
    """Normalized checkpoint action facts consumed by the controller spine."""

    available: bool
    action_name: str | None
    checkpoint_trace: dict[str, Any]

    @classmethod
    def from_trace(
        cls,
        checkpoint_trace: Mapping[str, Any] | None,
    ) -> ControllerLoopActionCandidate:
        trace = _json_safe_mapping(checkpoint_trace)
        return cls(
            available=bool(trace.get("available")),
            action_name=checkpoint_action_name_from_trace(trace),
            checkpoint_trace=trace,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "action_name": self.action_name,
            "checkpoint_trace": _json_safe_mapping(self.checkpoint_trace),
        }


@dataclass(frozen=True)
class ControllerLoopSpineInput:
    """JSON-safe control-plane facts for one controller-loop spine decision."""

    checkpoint_action: ControllerLoopActionCandidate
    source_class_lifecycle_trace: dict[str, Any]
    weak_corpus_lifecycle_trace: dict[str, Any] | None = None
    conflict_resolution_lifecycle_trace: dict[str, Any] | None = None
    ordinary_continuation_candidate_trace: dict[str, Any] | None = None
    targeted_retrieval_lifecycle_trace: dict[str, Any] | None = None

    @classmethod
    def from_traces(
        cls,
        *,
        checkpoint_trace: Mapping[str, Any] | None,
        source_class_lifecycle_trace: Mapping[str, Any] | None = None,
        weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
        conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
        ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
        targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
    ) -> ControllerLoopSpineInput:
        return cls(
            checkpoint_action=ControllerLoopActionCandidate.from_trace(
                checkpoint_trace
            ),
            source_class_lifecycle_trace=_json_safe_mapping(
                source_class_lifecycle_trace
            ),
            weak_corpus_lifecycle_trace=(
                _json_safe_mapping(weak_corpus_lifecycle_trace)
                if weak_corpus_lifecycle_trace is not None
                else None
            ),
            conflict_resolution_lifecycle_trace=_json_safe_mapping(
                conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=(
                _json_safe_mapping(ordinary_continuation_candidate_trace)
                if ordinary_continuation_candidate_trace is not None
                else None
            ),
            targeted_retrieval_lifecycle_trace=(
                _json_safe_mapping(targeted_retrieval_lifecycle_trace)
                if targeted_retrieval_lifecycle_trace is not None
                else None
            ),
        )

    @property
    def checkpoint_trace(self) -> dict[str, Any]:
        return _json_safe_mapping(self.checkpoint_action.checkpoint_trace)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_action": self.checkpoint_action.to_dict(),
            "source_class_lifecycle_trace": _json_safe_mapping(
                self.source_class_lifecycle_trace
            ),
            "weak_corpus_lifecycle_trace": (
                _json_safe_mapping(self.weak_corpus_lifecycle_trace)
                if self.weak_corpus_lifecycle_trace is not None
                else None
            ),
            "conflict_resolution_lifecycle_trace": _json_safe_mapping(
                self.conflict_resolution_lifecycle_trace
            ),
            "ordinary_continuation_candidate_trace": (
                _json_safe_mapping(self.ordinary_continuation_candidate_trace)
                if self.ordinary_continuation_candidate_trace is not None
                else None
            ),
            "targeted_retrieval_lifecycle_trace": (
                _json_safe_mapping(self.targeted_retrieval_lifecycle_trace)
                if self.targeted_retrieval_lifecycle_trace is not None
                else None
            ),
        }


@dataclass(frozen=True)
class ControllerLoopDispatchAuthorization:
    """Explicit dispatch authorization returned by the controller spine."""

    checkpoint_action_name: str | None
    promoted_action_name: str | None
    executed_action_name: str | None
    authorized_action_name: str | None
    blocked_or_skipped_actions: dict[str, str]

    @classmethod
    def from_trace_packet(
        cls,
        trace_packet: Mapping[str, Any],
    ) -> ControllerLoopDispatchAuthorization:
        authorized_action_name = trace_packet.get("authorized_action_name")
        if not (
            authorized_action_name == _TARGETED_RETRIEVAL_ACTION_NAME
            and _trace_packet_authorizes_bounded_ordinary_retrieve_targeted(
                trace_packet
            )
        ):
            authorized_action_name = trace_packet.get("executed_action_name")
        allowed_authorized_actions = {
            RECOVER_MISSING_SOURCE_CLASS,
            RECOVER_WEAK_CORPUS,
            RESOLVE_CONFLICT,
        }
        if (
            _trace_packet_authorizes_bounded_ordinary_retrieve_targeted(
                trace_packet
            )
            and authorized_action_name == _TARGETED_RETRIEVAL_ACTION_NAME
        ):
            allowed_authorized_actions.add(_TARGETED_RETRIEVAL_ACTION_NAME)
        if authorized_action_name not in allowed_authorized_actions:
            authorized_action_name = None
        return cls(
            checkpoint_action_name=_string_or_none(
                trace_packet.get("checkpoint_action_name")
            ),
            promoted_action_name=_string_or_none(
                trace_packet.get("promoted_action_name")
            ),
            executed_action_name=_string_or_none(
                trace_packet.get("executed_action_name")
            ),
            authorized_action_name=_string_or_none(authorized_action_name),
            blocked_or_skipped_actions={
                str(action): str(reason)
                for action, reason in dict(
                    trace_packet.get("blocked_or_skipped_actions") or {}
                ).items()
            },
        )

    @property
    def source_class_executor_dispatched(self) -> bool:
        return self.authorized_action_name == RECOVER_MISSING_SOURCE_CLASS

    @property
    def weak_corpus_executor_dispatched(self) -> bool:
        return self.authorized_action_name == RECOVER_WEAK_CORPUS

    @property
    def conflict_resolution_executor_dispatched(self) -> bool:
        return self.authorized_action_name == RESOLVE_CONFLICT

    @property
    def targeted_retrieval_dispatch_authorized(self) -> bool:
        return self.authorized_action_name == _TARGETED_RETRIEVAL_ACTION_NAME

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_action_name": self.checkpoint_action_name,
            "promoted_action_name": self.promoted_action_name,
            "executed_action_name": self.executed_action_name,
            "authorized_action_name": self.authorized_action_name,
            "source_class_executor_dispatched": (
                self.source_class_executor_dispatched
            ),
            "weak_corpus_executor_dispatched": (
                self.weak_corpus_executor_dispatched
            ),
            "conflict_resolution_executor_dispatched": (
                self.conflict_resolution_executor_dispatched
            ),
            "targeted_retrieval_dispatch_authorized": (
                self.targeted_retrieval_dispatch_authorized
            ),
            "blocked_or_skipped_actions": dict(self.blocked_or_skipped_actions),
        }


@dataclass(frozen=True)
class ControllerLoopSpineResult:
    """JSON-safe dispatch decision and trace packet for the controller loop."""

    input_facts: ControllerLoopSpineInput
    dispatch_authorization: ControllerLoopDispatchAuthorization
    checkpoint_action_name: str | None
    authorized_dispatch: str | None
    terminal_stop_checkpoint_gate_trace: dict[str, Any]
    source_class_checkpoint_gate_trace: dict[str, Any]
    weak_corpus_checkpoint_gate_trace: dict[str, Any]
    conflict_resolution_checkpoint_gate_trace: dict[str, Any]
    targeted_retrieval_checkpoint_gate_trace: dict[str, Any]
    combined_checkpoint_gate_trace: dict[str, Any]
    trace_packet: dict[str, Any]

    @property
    def source_class_executor_dispatched(self) -> bool:
        return self.dispatch_authorization.source_class_executor_dispatched

    @property
    def weak_corpus_executor_dispatched(self) -> bool:
        return self.dispatch_authorization.weak_corpus_executor_dispatched

    @property
    def conflict_resolution_executor_dispatched(self) -> bool:
        return self.dispatch_authorization.conflict_resolution_executor_dispatched

    @property
    def terminal_stop_approved(self) -> bool:
        return bool(
            self.terminal_stop_checkpoint_gate_trace.get("terminal_stop_approved")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_action_name": self.checkpoint_action_name,
            "authorized_dispatch": self.authorized_dispatch,
            "input_facts": self.input_facts.to_dict(),
            "dispatch_authorization": self.dispatch_authorization.to_dict(),
            "terminal_stop_approved": self.terminal_stop_approved,
            "source_class_executor_dispatched": self.source_class_executor_dispatched,
            "weak_corpus_executor_dispatched": self.weak_corpus_executor_dispatched,
            "conflict_resolution_executor_dispatched": (
                self.conflict_resolution_executor_dispatched
            ),
            "terminal_stop_checkpoint_gate_trace": dict(
                self.terminal_stop_checkpoint_gate_trace
            ),
            "source_class_checkpoint_gate_trace": dict(
                self.source_class_checkpoint_gate_trace
            ),
            "weak_corpus_checkpoint_gate_trace": dict(
                self.weak_corpus_checkpoint_gate_trace
            ),
            "conflict_resolution_checkpoint_gate_trace": dict(
                self.conflict_resolution_checkpoint_gate_trace
            ),
            "targeted_retrieval_checkpoint_gate_trace": dict(
                self.targeted_retrieval_checkpoint_gate_trace
            ),
            "combined_checkpoint_gate_trace": dict(
                self.combined_checkpoint_gate_trace
            ),
            "trace_packet": dict(self.trace_packet),
        }


def checkpoint_action_name_from_trace(
    checkpoint_trace: Mapping[str, Any] | None,
) -> str | None:
    """Return the single checkpoint action name from a trace packet."""
    trace = dict(checkpoint_trace or {})
    decision = trace.get("decision")
    if isinstance(decision, Mapping):
        action_name = decision.get("action_name")
        if action_name:
            return str(action_name)
    action_name = trace.get("recommended_action_name")
    if action_name:
        return str(action_name)
    return None


def build_controller_loop_spine_result(
    spine_input: ControllerLoopSpineInput | None = None,
    *,
    checkpoint_trace: Mapping[str, Any] | None = None,
    source_class_lifecycle_trace: Mapping[str, Any] | None = None,
    weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
    conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
    ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
    targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
) -> ControllerLoopSpineResult:
    """Authorize at most one bounded executor from sanitized controller facts."""
    if spine_input is None:
        spine_input = ControllerLoopSpineInput.from_traces(
            checkpoint_trace=checkpoint_trace,
            source_class_lifecycle_trace=source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=(
                ordinary_continuation_candidate_trace
            ),
            targeted_retrieval_lifecycle_trace=(
                targeted_retrieval_lifecycle_trace
            ),
        )
    checkpoint = spine_input.checkpoint_trace
    source_lifecycle = _json_safe_mapping(
        spine_input.source_class_lifecycle_trace
    )
    weak_lifecycle = (
        _json_safe_mapping(spine_input.weak_corpus_lifecycle_trace)
        if spine_input.weak_corpus_lifecycle_trace is not None
        else None
    )
    conflict_lifecycle = _json_safe_mapping(
        spine_input.conflict_resolution_lifecycle_trace
    )
    ordinary_candidate = (
        _json_safe_mapping(spine_input.ordinary_continuation_candidate_trace)
        if spine_input.ordinary_continuation_candidate_trace is not None
        else ordinary_continuation_candidate_defaults()
    )
    targeted_lifecycle = (
        _json_safe_mapping(spine_input.targeted_retrieval_lifecycle_trace)
        if spine_input.targeted_retrieval_lifecycle_trace is not None
        else None
    )

    terminal_gate = _build_terminal_stop_checkpoint_gate_trace(
        checkpoint_trace=checkpoint
    )
    terminal_stop_approved = bool(terminal_gate["terminal_stop_approved"])
    source_gate = _build_source_class_checkpoint_gate_trace(
        checkpoint_trace=checkpoint,
        lifecycle_trace=source_lifecycle,
        terminal_stop_approved=terminal_stop_approved,
    )
    weak_gate: dict[str, Any] = {}
    if weak_lifecycle is not None:
        weak_gate = _build_weak_corpus_checkpoint_gate_trace(
            checkpoint_trace=checkpoint,
            lifecycle_trace=weak_lifecycle,
            terminal_stop_approved=terminal_stop_approved,
            source_class_recovery_dispatched=bool(
                source_gate["source_class_executor_dispatched"]
            ),
        )
    conflict_gate = _build_conflict_resolution_checkpoint_gate_trace(
        checkpoint_trace=checkpoint,
        lifecycle_trace=conflict_lifecycle,
        terminal_stop_approved=terminal_stop_approved,
        source_class_executor_dispatched=bool(source_gate["executor_dispatched"]),
        weak_corpus_executor_dispatched=bool(
            weak_gate.get("weak_corpus_executor_dispatched")
        ),
    )
    targeted_gate = _build_targeted_retrieval_checkpoint_gate_trace(
        checkpoint_trace=checkpoint,
        lifecycle_trace=targeted_lifecycle,
        ordinary_continuation_candidate_trace=ordinary_candidate,
        terminal_stop_approved=terminal_stop_approved,
    )
    combined = _compose_combined_checkpoint_gate_trace(
        checkpoint_trace=checkpoint,
        ordinary_continuation_candidate_trace=ordinary_candidate,
        source_class_gate_trace=source_gate,
        terminal_stop_gate_trace=terminal_gate,
        weak_corpus_gate_trace=weak_gate,
        conflict_resolution_gate_trace=conflict_gate,
        targeted_retrieval_gate_trace=targeted_gate,
    )
    combined.update(
        _build_active_checkpoint_invariant_trace(
            checkpoint_trace=checkpoint,
            gate_trace=combined,
        )
    )
    trace_packet = apply_checkpoint_gate_trace(checkpoint, combined)

    dispatch_authorization = ControllerLoopDispatchAuthorization.from_trace_packet(
        trace_packet
    )

    return ControllerLoopSpineResult(
        input_facts=spine_input,
        dispatch_authorization=dispatch_authorization,
        checkpoint_action_name=spine_input.checkpoint_action.action_name,
        authorized_dispatch=dispatch_authorization.authorized_action_name,
        terminal_stop_checkpoint_gate_trace=terminal_gate,
        source_class_checkpoint_gate_trace=source_gate,
        weak_corpus_checkpoint_gate_trace=weak_gate,
        conflict_resolution_checkpoint_gate_trace=conflict_gate,
        targeted_retrieval_checkpoint_gate_trace=targeted_gate,
        combined_checkpoint_gate_trace=combined,
        trace_packet=trace_packet,
    )


def reconcile_retrieval_dispatch_runtime_checkpoint_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    ordinary_continuation_candidate_trace: Mapping[str, Any],
    targeted_retrieval_lifecycle_trace: Mapping[str, Any],
    authorized_gate_trace: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Preserve bounded continuation authorization after runtime batch dispatch."""

    checkpoint = _json_safe_mapping(checkpoint_trace)
    ordinary_candidate = mark_ordinary_continuation_candidate_spine_authorized(
        _json_safe_mapping(ordinary_continuation_candidate_trace),
        used=True,
    )
    targeted_lifecycle = {
        **_json_safe_mapping(targeted_retrieval_lifecycle_trace),
        "targeted_retrieval_candidate_used": True,
    }
    authorized_action = authorized_gate_trace.get("authorized_action_name")
    authorized_queries = [
        str(item)
        for item in authorized_gate_trace.get("authorized_queries", [])
        if str(item).strip()
    ]
    if authorized_action:
        blocked_or_skipped = dict(checkpoint.get("blocked_or_skipped_actions") or {})
        blocked_or_skipped.pop(str(authorized_action), None)
        checkpoint.update(
            {
                "promoted_action_name": authorized_action,
                "authorized_action_name": authorized_action,
                "blocked_or_skipped_actions": blocked_or_skipped,
                "ordinary_continuation_candidate_spine_authorized": True,
                "targeted_retrieval_dispatch_authorized": True,
                "targeted_retrieval_runtime_dispatch_inverted": True,
                "targeted_retrieval_executor_dispatched": False,
                "targeted_retrieval_gate_reason": authorized_gate_trace.get("reason"),
                "targeted_retrieval_authorized_queries": authorized_queries,
                "targeted_retrieval_authorized_query_provenance": (
                    authorized_gate_trace.get("query_provenance")
                ),
            }
        )
    checkpoint[ORDINARY_CONTINUATION_TRACE_KEY] = dict(ordinary_candidate)
    return checkpoint, ordinary_candidate, targeted_lifecycle


def apply_checkpoint_gate_trace(
    checkpoint_trace: Mapping[str, Any] | None,
    gate_trace: Mapping[str, Any],
) -> dict[str, Any]:
    active_trace = dict(checkpoint_trace or {})
    active_trace.update(dict(gate_trace))
    active_trace["shadow_mode"] = False
    active_trace["runtime_behavior_changed"] = True
    decision = active_trace.get("decision")
    if isinstance(decision, Mapping):
        active_decision = dict(decision)
        active_decision["shadow_mode"] = False
        active_decision["runtime_behavior_changed"] = True
        active_trace["decision"] = active_decision
    return active_trace


def _json_safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(_json_safe_value(dict(value or {})))


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe_value(item) for item in sorted(value, key=str)]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _build_source_class_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any],
    terminal_stop_approved: bool = False,
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    required_recovery_allowed = _authority_lifecycle_required_recovery_allowed(
        lifecycle_trace
    )
    authority_lifecycle_present = _authority_lifecycle_controls_recovery(
        lifecycle_trace
    )
    non_lifecycle_blocked = _non_lifecycle_source_class_blocker_present(
        lifecycle_trace
    )
    lifecycle_eligible = (
        required_recovery_allowed and not non_lifecycle_blocked
        if authority_lifecycle_present
        else bool(lifecycle_trace.get("active_source_class_recovery_eligible"))
    )
    official_canonical_admitted = (
        required_recovery_allowed and not non_lifecycle_blocked
        if authority_lifecycle_present
        else bool(
            lifecycle_trace.get(
                "active_source_class_recovery_official_canonical_admitted"
            )
        )
    )
    envelope_approved = (
        _authority_lifecycle_recovery_action_approved(lifecycle_trace)
        if authority_lifecycle_present
        else _source_class_action_envelope_approved(lifecycle_trace)
    )
    authority_execution_blocked = bool(
        lifecycle_trace.get("authority_lifecycle_execution_blocked")
    )
    checkpoint_available = bool(checkpoint_trace.get("available"))
    checkpoint_action_overridden = _authority_lifecycle_overrides_checkpoint_action(
        checkpoint_action_name,
        lifecycle_trace,
    )
    official_canonical_fallback_dispatch = (
        official_canonical_admitted
        and envelope_approved
        and (
            checkpoint_available
            or _official_canonical_unavailable_checkpoint_allows_fallback(
                checkpoint_trace
            )
        )
        and (checkpoint_action_name is None or checkpoint_action_overridden)
    )
    checkpointless_authority_lifecycle_dispatch = (
        _authority_lifecycle_approved_checkpointless_source_class_dispatch(
            checkpoint_trace=checkpoint_trace,
            lifecycle_trace=lifecycle_trace,
            lifecycle_eligible=lifecycle_eligible,
            required_recovery_allowed=required_recovery_allowed,
            envelope_approved=envelope_approved,
            non_lifecycle_blocked=non_lifecycle_blocked,
            authority_execution_blocked=authority_execution_blocked,
            checkpoint_action_name=checkpoint_action_name,
        )
    )
    terminal_stop_blocks_source_class = (
        terminal_stop_approved and not required_recovery_allowed
    )
    executor_dispatched = (
        not authority_execution_blocked
        and not terminal_stop_blocks_source_class
        and lifecycle_eligible
        and (
            (
                checkpoint_available
                and checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS
            )
            or official_canonical_fallback_dispatch
            or checkpointless_authority_lifecycle_dispatch
        )
    )
    if executor_dispatched and checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS:
        gate_reason = "approved"
    elif executor_dispatched and checkpointless_authority_lifecycle_dispatch:
        gate_reason = "approved_by_authority_lifecycle_required_recovery"
    elif executor_dispatched:
        gate_reason = "approved_by_official_canonical_admission"
    elif terminal_stop_blocks_source_class:
        gate_reason = "blocked_by_terminal_stop"
    elif authority_execution_blocked:
        gate_reason = "blocked_by_authority_lifecycle_execution_blocker"
    elif terminal_stop_approved and required_recovery_allowed:
        gate_reason = "authority_lifecycle_preserved_required_recovery"
    elif not lifecycle_eligible:
        gate_reason = "blocked_by_lifecycle"
    elif not checkpoint_available:
        gate_reason = "checkpoint_unavailable"
    else:
        gate_reason = "checkpoint_action_not_approved"

    return {
        "controller_gate_active": True,
        "source_class_spine_trace_role": SOURCE_CLASS_SPINE_TRACE_ROLE,
        "source_class_spine_dispatch_authority": False,
        "source_class_runner_dispatch_authority": (
            SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY
        ),
        "gated_action": RECOVER_MISSING_SOURCE_CLASS,
        "checkpoint_action_name": checkpoint_action_name,
        "lifecycle_eligible": lifecycle_eligible,
        "official_canonical_admitted": official_canonical_admitted,
        "official_canonical_dispatch_fallback": official_canonical_fallback_dispatch,
        "authority_lifecycle_checkpointless_dispatch": (
            checkpointless_authority_lifecycle_dispatch
        ),
        "spine_authorization_source": (
            "authority_lifecycle_required_recovery"
            if executor_dispatched and checkpointless_authority_lifecycle_dispatch
            else (
                "official_canonical_admission"
                if executor_dispatched and official_canonical_fallback_dispatch
                else (
                    "checkpoint_action"
                    if executor_dispatched
                    and checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS
                    else None
                )
            )
        ),
        "controller_action_envelope_approved": envelope_approved,
        "authority_lifecycle_required_recovery_allowed": (
            required_recovery_allowed
        ),
        "authority_lifecycle_checkpoint_action_overridden": (
            checkpoint_action_overridden
        ),
        "authority_lifecycle_execution_blocked": authority_execution_blocked,
        "lifecycle_blockers": list(
            lifecycle_trace.get("active_source_class_recovery_blockers") or []
        ),
        "executor_dispatched": executor_dispatched,
        "source_class_executor_dispatched": executor_dispatched,
        "gate_reason": gate_reason,
        "runtime_behavior_changed": True,
    }


def _source_class_action_envelope_approved(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    envelope = lifecycle_trace.get("active_source_class_recovery_action_envelope")
    if not isinstance(envelope, Mapping):
        return False
    required_classes = envelope.get("required_source_class")
    return bool(
        envelope.get("action_type") == "recover_missing_source_class"
        and envelope.get("allowed_action") is True
        and isinstance(required_classes, list)
        and required_classes
    )


def _authority_lifecycle_required_recovery_allowed(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    return bool(
        lifecycle_trace.get("authority_lifecycle_required_recovery_allowed")
    )


def _authority_lifecycle_controls_recovery(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    authority = lifecycle_trace.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return False
    if lifecycle_trace.get("authority_lifecycle_required_recovery_allowed") is True:
        return True
    if authority.get("recovery_needed") == "required":
        return True
    return _authority_lifecycle_recovery_action_approved(lifecycle_trace)


def _authority_lifecycle_recovery_action_approved(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    authority = lifecycle_trace.get("authority_lifecycle")
    if not isinstance(authority, Mapping):
        return False
    action = authority.get("recovery_action")
    return bool(
        isinstance(action, Mapping)
        and action.get("action_type") == RECOVER_MISSING_SOURCE_CLASS
        and action.get("approved") is True
    )


def _authority_lifecycle_approved_checkpointless_source_class_dispatch(
    *,
    checkpoint_trace: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any],
    lifecycle_eligible: bool,
    required_recovery_allowed: bool,
    envelope_approved: bool,
    non_lifecycle_blocked: bool,
    authority_execution_blocked: bool,
    checkpoint_action_name: str | None,
) -> bool:
    if checkpoint_trace.get("available") is True:
        return False
    if checkpoint_action_name is not None and not _authority_lifecycle_overrides_checkpoint_action(
        checkpoint_action_name,
        lifecycle_trace,
    ):
        return False
    if not _authority_lifecycle_controls_recovery(lifecycle_trace):
        return False
    if not lifecycle_eligible:
        return False
    if not required_recovery_allowed:
        return False
    if not envelope_approved:
        return False
    if not _source_class_action_envelope_approved(lifecycle_trace):
        return False
    if non_lifecycle_blocked or authority_execution_blocked:
        return False
    if not _source_class_recovery_queries_available(lifecycle_trace):
        return False
    if not _source_obligation_unmet(lifecycle_trace):
        return False
    if not _supported_official_current_missing_class_present(lifecycle_trace):
        return False
    if not _source_class_recovery_slot_available(lifecycle_trace):
        return False
    if _source_class_recovery_already_attempted(lifecycle_trace):
        return False
    return True


def _source_class_recovery_queries_available(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    return bool(_string_list(lifecycle_trace.get("active_source_class_recovery_queries")))


def _supported_official_current_missing_class_present(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    classes: list[str] = []
    for key in (
        "active_source_class_recovery_missing_classes",
        "unsatisfied_required_source_classes",
        "required_source_classes",
    ):
        classes.extend(_string_list(lifecycle_trace.get(key)))
    envelope = lifecycle_trace.get("active_source_class_recovery_action_envelope")
    if isinstance(envelope, Mapping):
        classes.extend(_string_list(envelope.get("required_source_class")))
    return any(item in _OFFICIAL_CURRENT_RECOVERY_SOURCE_CLASSES for item in classes)


def _source_obligation_unmet(lifecycle_trace: Mapping[str, Any]) -> bool:
    status = str(lifecycle_trace.get("source_obligation_status") or "").strip()
    if status.endswith("_unmet"):
        return True
    return bool(_string_list(lifecycle_trace.get("unsatisfied_required_source_classes")))


def _source_class_recovery_slot_available(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    slot = lifecycle_trace.get("recovery_slot_available")
    if slot is not None:
        return slot is True
    prior = _int_or_none(
        lifecycle_trace.get("prior_recovery_attempt_count"),
        lifecycle_trace.get("active_source_class_recovery_attempt_count"),
    )
    maximum = _int_or_none(lifecycle_trace.get("max_recovery_attempts"))
    if prior is not None and maximum is not None:
        return prior < maximum
    return True


def _source_class_recovery_already_attempted(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    if lifecycle_trace.get("active_source_class_recovery_used") is True:
        return True
    if lifecycle_trace.get("active_source_class_recovery_execution_attempted") is True:
        return True
    if lifecycle_trace.get("authority_lifecycle_execution_attempted") is True:
        return True
    if lifecycle_trace.get("acquisition_attempted") is True:
        return True
    if lifecycle_trace.get("candidate_acquisition_used") is True:
        return True
    if lifecycle_trace.get("candidate_return_status") not in {
        None,
        "",
        "not_attempted",
        "unknown",
        "not_observable",
    }:
        return True
    prior = _int_or_none(lifecycle_trace.get("prior_recovery_attempt_count"))
    maximum = _int_or_none(lifecycle_trace.get("max_recovery_attempts"))
    if prior is not None and maximum is not None and prior >= maximum:
        return True
    return False


def _non_lifecycle_source_class_blocker_present(
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    retired_local_authority_blockers = {
        "blocked_by_terminal_stop",
        "terminal_stop_approved",
        "blocked_by_corpus_weak",
        "blocked_by_weak_corpus_recovery",
        "weak_corpus_recovery_owns_path",
    }
    blockers = lifecycle_trace.get("active_source_class_recovery_blockers") or []
    if isinstance(blockers, (str, bytes)) or not isinstance(blockers, (list, tuple)):
        return False
    for blocker in blockers:
        text = str(blocker or "").strip().casefold().replace("-", "_").replace(" ", "_")
        if text and text not in retired_local_authority_blockers:
            return True
    return False


def _authority_lifecycle_overrides_checkpoint_action(
    checkpoint_action_name: str | None,
    lifecycle_trace: Mapping[str, Any],
) -> bool:
    if not _authority_lifecycle_required_recovery_allowed(lifecycle_trace):
        return False
    return checkpoint_action_name in {
        RECOVER_WEAK_CORPUS,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        STOP_SUFFICIENT,
    }


def _official_canonical_unavailable_checkpoint_allows_fallback(
    checkpoint_trace: Mapping[str, Any],
) -> bool:
    checkpoint_reason = checkpoint_trace.get("reason")
    return (
        checkpoint_trace.get("available") is False
        and (
            checkpoint_reason == "checkpoint_unavailable"
            or (
                checkpoint_reason == "checkpoint_exception"
                and checkpoint_trace.get(
                    "official_canonical_checkpoint_exception_fallback_allowed"
                )
                is True
            )
        )
    )


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = []
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _int_or_none(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return max(0, int(value.strip()))
    return None


def _build_weak_corpus_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any],
    terminal_stop_approved: bool = False,
    source_class_recovery_dispatched: bool = False,
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    checkpoint_available = bool(checkpoint_trace.get("available"))
    lifecycle_eligible = bool(lifecycle_trace.get("approved"))
    lifecycle_blockers = list(lifecycle_trace.get("blockers") or [])
    executor_dispatched = (
        checkpoint_available
        and not terminal_stop_approved
        and not source_class_recovery_dispatched
        and lifecycle_eligible
        and checkpoint_action_name == RECOVER_WEAK_CORPUS
    )
    if executor_dispatched:
        gate_reason = "approved"
    elif terminal_stop_approved:
        gate_reason = "blocked_by_terminal_stop"
    elif source_class_recovery_dispatched:
        gate_reason = "blocked_by_authority_lifecycle_required_recovery"
    elif not lifecycle_eligible:
        gate_reason = str(lifecycle_trace.get("reason") or "blocked_by_lifecycle")
    elif not checkpoint_available:
        gate_reason = "checkpoint_unavailable"
    else:
        gate_reason = "checkpoint_action_not_approved"

    return {
        "weak_corpus_gate_active": True,
        "weak_corpus_gated_action": RECOVER_WEAK_CORPUS,
        "checkpoint_action_name": checkpoint_action_name,
        "weak_corpus_lifecycle_eligible": lifecycle_eligible,
        "weak_corpus_lifecycle_blockers": lifecycle_blockers,
        "weak_corpus_executor_dispatched": executor_dispatched,
        "weak_corpus_gate_reason": gate_reason,
        "runtime_behavior_changed": True,
    }


def _build_conflict_resolution_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any],
    terminal_stop_approved: bool = False,
    source_class_executor_dispatched: bool = False,
    weak_corpus_executor_dispatched: bool = False,
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    checkpoint_available = bool(checkpoint_trace.get("available"))
    lifecycle_eligible = bool(lifecycle_trace.get("approved"))
    lifecycle_blockers = list(
        lifecycle_trace.get("blockers")
        or lifecycle_trace.get("active_conflict_resolution_blockers")
        or []
    )
    other_promoted_action_selected = bool(
        source_class_executor_dispatched or weak_corpus_executor_dispatched
    )
    executor_dispatched = (
        checkpoint_available
        and not terminal_stop_approved
        and not other_promoted_action_selected
        and lifecycle_eligible
        and checkpoint_action_name == RESOLVE_CONFLICT
    )
    if executor_dispatched:
        gate_reason = "approved"
    elif terminal_stop_approved:
        gate_reason = "blocked_by_terminal_stop"
    elif other_promoted_action_selected:
        gate_reason = "blocked_by_other_promoted_action"
    elif not lifecycle_eligible:
        gate_reason = str(lifecycle_trace.get("reason") or "blocked_by_lifecycle")
    elif not checkpoint_available:
        gate_reason = "checkpoint_unavailable"
    else:
        gate_reason = "checkpoint_action_not_approved"

    return {
        "conflict_resolution_gate_active": True,
        "conflict_resolution_gated_action": RESOLVE_CONFLICT,
        "checkpoint_action_name": checkpoint_action_name,
        "conflict_resolution_lifecycle_considered": bool(
            lifecycle_trace.get("active_conflict_resolution_considered")
            or lifecycle_trace.get("considered")
        ),
        "conflict_resolution_lifecycle_eligible": lifecycle_eligible,
        "conflict_resolution_lifecycle_blockers": lifecycle_blockers,
        "conflict_resolution_executor_dispatched": executor_dispatched,
        "conflict_resolution_gate_reason": gate_reason,
        "runtime_behavior_changed": True,
    }


def _build_targeted_retrieval_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    lifecycle_trace: Mapping[str, Any] | None,
    ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
    terminal_stop_approved: bool = False,
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    checkpoint_available = bool(checkpoint_trace.get("available"))
    targeted_lifecycle_available = lifecycle_trace is not None
    safe_lifecycle_trace = _json_safe_mapping(lifecycle_trace)
    lifecycle_considered = bool(
        safe_lifecycle_trace.get("targeted_retrieval_candidate_considered")
    )
    lifecycle_eligible = bool(
        safe_lifecycle_trace.get("targeted_retrieval_candidate_eligible")
    )
    lifecycle_blockers = list(
        safe_lifecycle_trace.get("targeted_retrieval_candidate_blockers") or []
    )
    ordinary_candidate = _json_safe_mapping(ordinary_continuation_candidate_trace)
    ordinary_candidate_considered = bool(ordinary_candidate.get("considered"))
    ordinary_candidate_eligible = bool(ordinary_candidate.get("eligible"))
    ordinary_candidate_blockers = list(ordinary_candidate.get("blockers") or [])
    ordinary_candidate_reason = str(
        ordinary_candidate.get("reason") or "ordinary_continuation_not_evaluated"
    )
    bounded_candidate_reason = bounded_continuation_authorization_reason(
        ordinary_candidate
    )
    lifecycle_available = bool(
        targeted_lifecycle_available or ordinary_candidate_considered
    )
    lifecycle_reason = _targeted_retrieval_lifecycle_reason(
        safe_lifecycle_trace,
        lifecycle_blockers,
    )
    authorized_query_provenance = (
        ordinary_candidate.get("query_provenance")
        or ordinary_candidate.get("source_path")
    )

    dispatch_authorized = False
    if terminal_stop_approved:
        gate_reason = "blocked_by_terminal_stop"
    elif not targeted_lifecycle_available:
        if ordinary_candidate_considered and not ordinary_candidate_eligible:
            gate_reason = ordinary_candidate_reason
        else:
            gate_reason = "targeted_retrieval_lifecycle_not_available"
    elif not lifecycle_eligible:
        gate_reason = lifecycle_reason
    elif not checkpoint_available:
        gate_reason = "checkpoint_unavailable"
    elif checkpoint_action_name == _TARGETED_RETRIEVAL_ACTION_NAME:
        if bounded_candidate_reason:
            dispatch_authorized = True
            gate_reason = bounded_candidate_reason
        else:
            gate_reason = _TARGETED_RUNTIME_DISPATCH_NOT_INVERTED
    else:
        gate_reason = "checkpoint_action_not_approved"

    return {
        "targeted_retrieval_gate_active": lifecycle_available,
        "targeted_retrieval_gated_action": _TARGETED_RETRIEVAL_ACTION_NAME,
        "targeted_retrieval_lifecycle_considered": lifecycle_considered,
        "targeted_retrieval_lifecycle_eligible": lifecycle_eligible,
        "targeted_retrieval_lifecycle_blockers": lifecycle_blockers,
        "ordinary_continuation_candidate_considered": (
            ordinary_candidate_considered
        ),
        "ordinary_continuation_candidate_eligible": ordinary_candidate_eligible,
        "ordinary_continuation_candidate_blockers": ordinary_candidate_blockers,
        "ordinary_continuation_candidate_spine_authorized": dispatch_authorized,
        "targeted_retrieval_executor_dispatched": False,
        "targeted_retrieval_dispatch_authorized": dispatch_authorized,
        "targeted_retrieval_authorized_queries": (
            list(ordinary_candidate.get("ordinary_next_queries") or [])
            if dispatch_authorized
            else []
        ),
        "targeted_retrieval_authorized_query_provenance": (
            authorized_query_provenance if dispatch_authorized else None
        ),
        "targeted_retrieval_gate_reason": gate_reason,
        "targeted_retrieval_runtime_dispatch_inverted": dispatch_authorized,
        "runtime_behavior_changed": True,
    }


def _targeted_retrieval_lifecycle_reason(
    lifecycle_trace: Mapping[str, Any],
    lifecycle_blockers: list[Any],
) -> str:
    for key in (
        "targeted_retrieval_candidate_skip_reason",
        "targeted_retrieval_candidate_reason",
    ):
        value = lifecycle_trace.get(key)
        if value:
            return str(value)
    if lifecycle_blockers:
        return str(lifecycle_blockers[0])
    return "blocked_by_lifecycle"


def _build_terminal_stop_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    checkpoint_available = bool(checkpoint_trace.get("available"))
    terminal_stop_approved = (
        checkpoint_available and checkpoint_action_name in _TERMINAL_STOP_ACTIONS
    )
    if checkpoint_action_name == STOP_INSUFFICIENT_WITH_CAVEAT:
        final_answer_posture = "insufficient_with_caveat"
        gate_reason = "terminal_stop_insufficient_with_caveat"
    elif checkpoint_action_name == STOP_SUFFICIENT:
        final_answer_posture = "sufficient"
        gate_reason = "terminal_stop_sufficient"
    elif checkpoint_available and checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS:
        final_answer_posture = "existing_posture"
        gate_reason = "source_class_recovery_remains_promoted"
    elif checkpoint_available and checkpoint_action_name == RESOLVE_CONFLICT:
        final_answer_posture = "existing_posture"
        gate_reason = "conflict_resolution_remains_promoted"
    elif checkpoint_available:
        final_answer_posture = "existing_posture"
        gate_reason = "alternate_action_not_promoted"
    else:
        final_answer_posture = "existing_posture"
        gate_reason = "checkpoint_unavailable"

    executor_dispatch_blocked = terminal_stop_approved or (
        checkpoint_available
        and checkpoint_action_name is not None
        and checkpoint_action_name
        not in {
            RECOVER_MISSING_SOURCE_CLASS,
            RESOLVE_CONFLICT,
        }
    )
    blocked_executor_types = (
        [
            "source_class_recovery",
            "targeted_retrieval",
            "weak_corpus_recovery",
            "conflict_resolution",
        ]
        if executor_dispatch_blocked
        else []
    )
    return {
        "controller_stop_gate_active": True,
        "checkpoint_action_name": checkpoint_action_name,
        "terminal_stop_approved": terminal_stop_approved,
        "final_answer_posture": final_answer_posture,
        "executor_dispatch_blocked": executor_dispatch_blocked,
        "blocked_executor_types": blocked_executor_types,
        "runtime_behavior_changed": True,
        "gate_reason": gate_reason,
    }


def _compose_combined_checkpoint_gate_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    ordinary_continuation_candidate_trace: Mapping[str, Any],
    source_class_gate_trace: Mapping[str, Any],
    terminal_stop_gate_trace: Mapping[str, Any],
    weak_corpus_gate_trace: Mapping[str, Any],
    conflict_resolution_gate_trace: Mapping[str, Any],
    targeted_retrieval_gate_trace: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint_action_name = terminal_stop_gate_trace.get("checkpoint_action_name")
    targeted_retrieval_authorized = bool(
        targeted_retrieval_gate_trace.get("targeted_retrieval_dispatch_authorized")
    )
    ordinary_candidate = _json_safe_mapping(ordinary_continuation_candidate_trace)
    if targeted_retrieval_authorized:
        ordinary_candidate = mark_ordinary_continuation_candidate_spine_authorized(
            ordinary_candidate,
            used=True,
        )
    combined = {
        ORDINARY_CONTINUATION_TRACE_KEY: ordinary_candidate,
        **dict(source_class_gate_trace),
        **dict(terminal_stop_gate_trace),
        **dict(weak_corpus_gate_trace),
        **dict(conflict_resolution_gate_trace),
        **dict(targeted_retrieval_gate_trace),
    }
    if (
        checkpoint_action_name == RECOVER_MISSING_SOURCE_CLASS
        or not checkpoint_trace.get("available")
    ):
        combined["gate_reason"] = source_class_gate_trace["gate_reason"]
    if weak_corpus_gate_trace:
        if checkpoint_action_name == RECOVER_WEAK_CORPUS:
            combined["gated_action"] = RECOVER_WEAK_CORPUS
            combined["lifecycle_eligible"] = weak_corpus_gate_trace[
                "weak_corpus_lifecycle_eligible"
            ]
            combined["lifecycle_blockers"] = weak_corpus_gate_trace[
                "weak_corpus_lifecycle_blockers"
            ]
            combined["executor_dispatched"] = weak_corpus_gate_trace[
                "weak_corpus_executor_dispatched"
            ]
            combined["gate_reason"] = weak_corpus_gate_trace[
                "weak_corpus_gate_reason"
            ]
        if weak_corpus_gate_trace["weak_corpus_executor_dispatched"]:
            combined["executor_dispatch_blocked"] = False
            combined["blocked_executor_types"] = []
        elif checkpoint_action_name == RECOVER_WEAK_CORPUS:
            combined["executor_dispatch_blocked"] = True
            combined["blocked_executor_types"] = ["weak_corpus_recovery"]
    if checkpoint_action_name == RESOLVE_CONFLICT:
        combined["gated_action"] = RESOLVE_CONFLICT
        combined["lifecycle_eligible"] = conflict_resolution_gate_trace[
            "conflict_resolution_lifecycle_eligible"
        ]
        combined["lifecycle_blockers"] = conflict_resolution_gate_trace[
            "conflict_resolution_lifecycle_blockers"
        ]
        combined["executor_dispatched"] = conflict_resolution_gate_trace[
            "conflict_resolution_executor_dispatched"
        ]
        combined["gate_reason"] = conflict_resolution_gate_trace[
            "conflict_resolution_gate_reason"
        ]
        combined["executor_dispatch_blocked"] = not bool(
            conflict_resolution_gate_trace[
                "conflict_resolution_executor_dispatched"
            ]
        )
        combined["blocked_executor_types"] = (
            []
            if conflict_resolution_gate_trace[
                "conflict_resolution_executor_dispatched"
            ]
            else ["conflict_resolution"]
        )
    if (
        targeted_retrieval_gate_trace.get("targeted_retrieval_gate_active")
        and checkpoint_action_name == _TARGETED_RETRIEVAL_ACTION_NAME
    ):
        combined["gated_action"] = _TARGETED_RETRIEVAL_ACTION_NAME
        combined["lifecycle_eligible"] = targeted_retrieval_gate_trace[
            "targeted_retrieval_lifecycle_eligible"
        ]
        combined["lifecycle_blockers"] = targeted_retrieval_gate_trace[
            "targeted_retrieval_lifecycle_blockers"
        ]
        combined["executor_dispatched"] = False
        combined["gate_reason"] = targeted_retrieval_gate_trace[
            "targeted_retrieval_gate_reason"
        ]
        combined["executor_dispatch_blocked"] = not targeted_retrieval_authorized
        combined["blocked_executor_types"] = (
            [] if targeted_retrieval_authorized else ["targeted_retrieval"]
        )
    if source_class_gate_trace.get("source_class_executor_dispatched"):
        combined["gated_action"] = RECOVER_MISSING_SOURCE_CLASS
        combined["lifecycle_eligible"] = source_class_gate_trace[
            "lifecycle_eligible"
        ]
        combined["lifecycle_blockers"] = source_class_gate_trace[
            "lifecycle_blockers"
        ]
        combined["executor_dispatched"] = True
        combined["gate_reason"] = source_class_gate_trace["gate_reason"]
        combined["executor_dispatch_blocked"] = False
        combined["blocked_executor_types"] = []
    return combined


def _build_active_checkpoint_invariant_trace(
    *,
    checkpoint_trace: Mapping[str, Any],
    gate_trace: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint_action_name = checkpoint_action_name_from_trace(checkpoint_trace)
    checkpoint_available = bool(checkpoint_trace.get("available"))
    checkpoint_decision_count = (
        1
        if checkpoint_available
        and isinstance(checkpoint_trace.get("decision"), Mapping)
        and checkpoint_action_name is not None
        else 0
    )
    terminal_stop_approved = bool(gate_trace.get("terminal_stop_approved"))
    source_class_executor_dispatched = bool(
        gate_trace.get(
            "source_class_executor_dispatched",
            gate_trace.get("executor_dispatched"),
        )
    )
    weak_corpus_gate_active = bool(gate_trace.get("weak_corpus_gate_active"))
    weak_corpus_executor_dispatched = bool(
        gate_trace.get("weak_corpus_executor_dispatched")
    )
    conflict_resolution_gate_active = bool(
        gate_trace.get("conflict_resolution_gate_active")
    )
    conflict_resolution_executor_dispatched = bool(
        gate_trace.get("conflict_resolution_executor_dispatched")
    )
    targeted_retrieval_gate_active = bool(
        gate_trace.get("targeted_retrieval_gate_active")
    )
    targeted_retrieval_lifecycle_eligible = bool(
        gate_trace.get("targeted_retrieval_lifecycle_eligible")
    )
    targeted_retrieval_dispatch_authorized = bool(
        gate_trace.get("targeted_retrieval_dispatch_authorized")
    )
    targeted_retrieval_lifecycle_blockers = list(
        gate_trace.get("targeted_retrieval_lifecycle_blockers") or []
    )

    promoted_action_name = None
    executed_action_name = None
    if source_class_executor_dispatched:
        promoted_action_name = RECOVER_MISSING_SOURCE_CLASS
        executed_action_name = RECOVER_MISSING_SOURCE_CLASS
    elif terminal_stop_approved:
        promoted_action_name = checkpoint_action_name
    elif weak_corpus_executor_dispatched:
        promoted_action_name = RECOVER_WEAK_CORPUS
        executed_action_name = RECOVER_WEAK_CORPUS
    elif conflict_resolution_executor_dispatched:
        promoted_action_name = RESOLVE_CONFLICT
        executed_action_name = RESOLVE_CONFLICT
    elif targeted_retrieval_dispatch_authorized:
        promoted_action_name = _TARGETED_RETRIEVAL_ACTION_NAME

    blocked_or_skipped_actions: dict[str, str] = {}
    gate_reason = str(gate_trace.get("gate_reason") or "active_gate_not_approved")
    if checkpoint_available and checkpoint_action_name and promoted_action_name is None:
        blocked_or_skipped_actions[checkpoint_action_name] = gate_reason
    if terminal_stop_approved and source_class_executor_dispatched:
        if checkpoint_action_name:
            blocked_or_skipped_actions[checkpoint_action_name] = (
                "authority_lifecycle_preserved_required_recovery"
            )
        if weak_corpus_gate_active:
            blocked_or_skipped_actions[RECOVER_WEAK_CORPUS] = (
                "blocked_by_authority_lifecycle_required_recovery"
            )
        if conflict_resolution_gate_active:
            blocked_or_skipped_actions[RESOLVE_CONFLICT] = (
                "blocked_by_authority_lifecycle_required_recovery"
            )
    elif terminal_stop_approved:
        blocked_or_skipped_actions[RECOVER_MISSING_SOURCE_CLASS] = (
            "blocked_by_terminal_stop"
        )
        if weak_corpus_gate_active:
            blocked_or_skipped_actions[RECOVER_WEAK_CORPUS] = (
                "blocked_by_terminal_stop"
            )
        if conflict_resolution_gate_active:
            blocked_or_skipped_actions[RESOLVE_CONFLICT] = (
                "blocked_by_terminal_stop"
            )
    elif (
        checkpoint_available
        and checkpoint_action_name is not None
        and checkpoint_action_name != RECOVER_MISSING_SOURCE_CLASS
        and not source_class_executor_dispatched
    ):
        blocked_or_skipped_actions[RECOVER_MISSING_SOURCE_CLASS] = (
            "checkpoint_action_not_approved"
        )
    if weak_corpus_gate_active:
        weak_corpus_gate_reason = str(
            gate_trace.get("weak_corpus_gate_reason")
            or "active_gate_not_approved"
        )
        if weak_corpus_executor_dispatched:
            blocked_or_skipped_actions.pop(RECOVER_WEAK_CORPUS, None)
        elif checkpoint_action_name == RECOVER_WEAK_CORPUS:
            blocked_or_skipped_actions[RECOVER_WEAK_CORPUS] = weak_corpus_gate_reason
        elif not terminal_stop_approved:
            blocked_or_skipped_actions[RECOVER_WEAK_CORPUS] = (
                "checkpoint_action_not_approved"
            )
    if conflict_resolution_gate_active:
        conflict_resolution_considered = bool(
            gate_trace.get("conflict_resolution_lifecycle_considered")
        )
        conflict_resolution_gate_reason = str(
            gate_trace.get("conflict_resolution_gate_reason")
            or "active_gate_not_approved"
        )
        if conflict_resolution_executor_dispatched:
            blocked_or_skipped_actions.pop(RESOLVE_CONFLICT, None)
        elif checkpoint_action_name == RESOLVE_CONFLICT:
            blocked_or_skipped_actions[RESOLVE_CONFLICT] = (
                conflict_resolution_gate_reason
            )
        elif not terminal_stop_approved and conflict_resolution_considered:
            blocked_or_skipped_actions[RESOLVE_CONFLICT] = (
                "checkpoint_action_not_approved"
            )
    if targeted_retrieval_gate_active:
        targeted_gate_reason = str(
            gate_trace.get("targeted_retrieval_gate_reason")
            or "active_gate_not_approved"
        )
        if targeted_retrieval_dispatch_authorized:
            blocked_or_skipped_actions.pop(_TARGETED_RETRIEVAL_ACTION_NAME, None)
        elif terminal_stop_approved and source_class_executor_dispatched:
            blocked_or_skipped_actions[_TARGETED_RETRIEVAL_ACTION_NAME] = (
                "blocked_by_authority_lifecycle_required_recovery"
            )
        elif terminal_stop_approved:
            blocked_or_skipped_actions[_TARGETED_RETRIEVAL_ACTION_NAME] = (
                "blocked_by_terminal_stop"
            )
        elif checkpoint_action_name == _TARGETED_RETRIEVAL_ACTION_NAME:
            blocked_or_skipped_actions[_TARGETED_RETRIEVAL_ACTION_NAME] = (
                targeted_gate_reason
            )
        elif targeted_retrieval_lifecycle_eligible:
            blocked_or_skipped_actions[_TARGETED_RETRIEVAL_ACTION_NAME] = (
                "checkpoint_action_not_approved"
            )
        elif targeted_retrieval_lifecycle_blockers:
            blocked_or_skipped_actions[_TARGETED_RETRIEVAL_ACTION_NAME] = (
                targeted_gate_reason
            )

    return {
        "checkpoint_decision_count": checkpoint_decision_count,
        "promoted_action_name": promoted_action_name,
        "executed_action_name": executed_action_name,
        "authorized_action_name": promoted_action_name
        if targeted_retrieval_dispatch_authorized
        else executed_action_name,
        "blocked_or_skipped_actions": blocked_or_skipped_actions,
    }


def _trace_packet_authorizes_bounded_ordinary_retrieve_targeted(
    trace_packet: Mapping[str, Any],
) -> bool:
    packet = _json_safe_mapping(trace_packet)
    ordinary_candidate = _json_safe_mapping(
        packet.get(ORDINARY_CONTINUATION_TRACE_KEY)
    )
    bounded_candidate_reason = bounded_continuation_authorization_reason(
        ordinary_candidate
    )
    return bool(
        packet.get("targeted_retrieval_dispatch_authorized")
        and not packet.get("targeted_retrieval_executor_dispatched")
        and packet.get("targeted_retrieval_runtime_dispatch_inverted")
        and packet.get("checkpoint_action_name") == _TARGETED_RETRIEVAL_ACTION_NAME
        and packet.get("targeted_retrieval_gate_reason") == bounded_candidate_reason
        and is_bounded_spine_authorized_continuation_candidate(ordinary_candidate)
    )
