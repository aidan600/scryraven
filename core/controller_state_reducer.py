"""Pure offline controller-state reducer and contracts for AG-27.

This module applies AG-25 controller action envelopes to JSON-safe
controller-state snapshots. It is descriptive only: it does not execute
retrieval, call providers, alter prompts, persist data, or drive runtime
controller authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from core.controller_action_envelope import (
    ASK_USER_CLARIFICATION,
    DECOMPOSE_QUANTITATIVE_QUESTION,
    DIAGNOSE_QUESTION,
    GENERATE_TARGETED_QUERIES,
    HANDOFF_TO_ANALYST,
    IDENTIFY_MISSING_INFORMATION,
    INSPECT_EVIDENCE_STATE,
    OFFICIAL_OR_LEGAL_SOURCE_CLASSES,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    SET_OR_UPDATE_ANSWER_CONTRACT,
    SOCIAL_SIGNAL_SIDE_PACKET_CLASSES,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    ControllerActionEnvelope,
    ControllerActionHandoffBoundary,
    ControllerActionSideEffectClass,
    action_can_enter_ordinary_evidence,
    controller_action_names,
    get_controller_action_descriptor,
)

CONTROLLER_STATE_SNAPSHOT_SCHEMA_VERSION = "controller_state_snapshot_ag27_v1"
CONTROLLER_STATE_REDUCER_RESULT_SCHEMA_VERSION = (
    "controller_state_reducer_result_ag27_v1"
)
CONTROLLER_EXECUTOR_DESCRIPTOR_SCHEMA_VERSION = (
    "controller_executor_descriptor_ag27_v1"
)
CONTROLLER_BUDGET_DESCRIPTOR_SCHEMA_VERSION = "controller_budget_descriptor_ag27_v1"
CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION = (
    "controller_evidence_boundary_ag27_v1"
)

OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE_CLASSES = (
    *OFFICIAL_OR_LEGAL_SOURCE_CLASSES,
    "primary_source_documents",
    "archival_primary_text",
    "primary_or_archival",
    "current_primary_or_official_proxy",
)

_ACTIVE_STATUSES = {"approved", "completed"}
_PASSIVE_RECORDABLE_STATUSES = {"approved", "completed", "informational"}
_HANDOFF_ONLY_ACTIONS = {
    SET_OR_UPDATE_ANSWER_CONTRACT,
    IDENTIFY_MISSING_INFORMATION,
    DECOMPOSE_QUANTITATIVE_QUESTION,
    HANDOFF_TO_ANALYST,
    ASK_USER_CLARIFICATION,
}
_PASSIVE_ACTIONS = {
    DIAGNOSE_QUESTION,
    SET_OR_UPDATE_ANSWER_CONTRACT,
    INSPECT_EVIDENCE_STATE,
    IDENTIFY_MISSING_INFORMATION,
    GENERATE_TARGETED_QUERIES,
    RETRIEVE_TARGETED,
    RESOLVE_CONFLICT,
    DECOMPOSE_QUANTITATIVE_QUESTION,
    RUN_SCRUTINEER_REVIEW,
    HANDOFF_TO_ANALYST,
    ASK_USER_CLARIFICATION,
}
_SENSITIVE_KEYS = {
    "api_key",
    "cache",
    "db_row",
    "full_trace",
    "password",
    "prompt",
    "provider_payload",
    "raw_comments",
    "raw_evidence",
    "raw_handles",
    "raw_ids",
    "raw_packet",
    "raw_provider_payload",
    "raw_prompt",
    "secret",
    "token",
}


class ControllerBudgetClass(str, Enum):
    """Budget classes represented by the offline reducer."""

    RETRIEVAL_ITERATION = "retrieval_iteration_budget"
    WEAK_CORPUS_RECOVERY = "weak_corpus_recovery_budget"
    SOURCE_CLASS_RECOVERY = "source_class_recovery_budget"
    ANSWER_CONTRACT_RECOVERY_ACTION = "answer_contract_recovery_action_budget"
    SOCIAL_SIDE_PACKET = "social_side_packet_budget_placeholder"
    LIVE_CALL = "live_call_budget_placeholder"


class ControllerExecutorMode(str, Enum):
    """How an executor descriptor relates to current runtime authority."""

    ACTIVE_RUNTIME_OWNED = "active_runtime_owned"
    ACTIVE_TERMINAL_RUNTIME_OWNED = "active_terminal_runtime_owned"
    PASSIVE_DESCRIPTOR = "passive_descriptor"
    SHADOW_DESCRIPTOR = "shadow_descriptor"
    FUTURE_PLACEHOLDER = "future_placeholder"


class ControllerEvidenceBoundary(str, Enum):
    """Evidence and handoff boundaries asserted by the reducer."""

    ORDINARY_EVIDENCE_ELIGIBILITY = "ordinary_evidence_eligibility"
    OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE = (
        "official_legal_current_primary_evidence"
    )
    SOCIAL_SIDE_PACKET_EVIDENCE = "social_side_packet_evidence"
    FINAL_ANSWER_POSTURE_ONLY = "final_answer_posture_only"
    SANITIZED_HANDOFF_ONLY = "sanitized_handoff_only"


@dataclass(frozen=True)
class ControllerExecutorDescriptor:
    """Descriptor for the current, passive, or future executor boundary."""

    action_name: str
    current_authority: str
    executor_mode: ControllerExecutorMode
    side_effect_class: str
    executor: str | None
    handoff_boundary: str
    descriptor_only: bool = True
    runtime_behavior_changed: bool = False
    promotion_blockers: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_EXECUTOR_DESCRIPTOR_SCHEMA_VERSION,
            "action_name": self.action_name,
            "current_authority": self.current_authority,
            "executor_mode": self.executor_mode.value,
            "side_effect_class": self.side_effect_class,
            "executor": self.executor,
            "handoff_boundary": self.handoff_boundary,
            "descriptor_only": self.descriptor_only,
            "runtime_behavior_changed": self.runtime_behavior_changed,
            "promotion_blockers": list(self.promotion_blockers),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerBudgetDescriptor:
    """Descriptor for a budget class without runtime ownership changes."""

    budget_class: ControllerBudgetClass
    owner: str
    scope: str
    applies_to_actions: tuple[str, ...]
    limit_source: str
    descriptor_only: bool = True
    runtime_behavior_changed: bool = False
    promotion_notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_BUDGET_DESCRIPTOR_SCHEMA_VERSION,
            "budget_class": self.budget_class.value,
            "owner": self.owner,
            "scope": self.scope,
            "applies_to_actions": list(self.applies_to_actions),
            "limit_source": self.limit_source,
            "descriptor_only": self.descriptor_only,
            "runtime_behavior_changed": self.runtime_behavior_changed,
            "promotion_notes": list(self.promotion_notes),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerBudgetEffect:
    """One offline budget effect from reducing an action envelope."""

    budget_class: ControllerBudgetClass
    action_name: str
    effect: str
    usage_delta: int = 0
    descriptor_only: bool = True
    runtime_behavior_changed: bool = False
    reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_class": self.budget_class.value,
            "action_name": self.action_name,
            "effect": self.effect,
            "usage_delta": self.usage_delta,
            "descriptor_only": self.descriptor_only,
            "runtime_behavior_changed": self.runtime_behavior_changed,
            "reason": self.reason,
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerEvidenceBoundaryAssertion:
    """One evidence-boundary assertion for a reduced action."""

    boundary: ControllerEvidenceBoundary
    action_name: str
    allowed: bool
    reason: str
    evidence_classes: tuple[str, ...] = ()
    state_field: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": self.boundary.value,
            "action_name": self.action_name,
            "allowed": self.allowed,
            "reason": self.reason,
            "evidence_classes": list(self.evidence_classes),
            "state_field": self.state_field,
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerStateSnapshot:
    """JSON-safe offline snapshot of controller-state effects."""

    iteration: int = 0
    action_history: tuple[Mapping[str, Any], ...] = ()
    recovery_attempts: Mapping[str, int] = field(default_factory=dict)
    budget_counters: Mapping[str, int] = field(default_factory=dict)
    budget_events: tuple[Mapping[str, Any], ...] = ()
    pending_queries: tuple[str, ...] = ()
    ordinary_evidence_action_names: tuple[str, ...] = ()
    ordinary_evidence_candidate_count: int = 0
    official_legal_current_primary_action_names: tuple[str, ...] = ()
    social_side_packet_action_names: tuple[str, ...] = ()
    social_side_packet_status: str | None = None
    sanitized_handoff_action_names: tuple[str, ...] = ()
    stopped: bool = False
    stop_reason: str | None = None
    final_answer_posture: str | None = None
    executor_events: tuple[Mapping[str, Any], ...] = ()
    evidence_boundary_events: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_STATE_SNAPSHOT_SCHEMA_VERSION,
            "iteration": max(0, int(self.iteration or 0)),
            "action_history": _json_safe(self.action_history),
            "recovery_attempts": _int_mapping(self.recovery_attempts),
            "budget_counters": _int_mapping(self.budget_counters),
            "budget_events": _json_safe(self.budget_events),
            "pending_queries": list(_copy_string_tuple(self.pending_queries)),
            "ordinary_evidence_action_names": list(
                _copy_string_tuple(self.ordinary_evidence_action_names)
            ),
            "ordinary_evidence_candidate_count": max(
                0,
                int(self.ordinary_evidence_candidate_count or 0),
            ),
            "official_legal_current_primary_action_names": list(
                _copy_string_tuple(
                    self.official_legal_current_primary_action_names
                )
            ),
            "social_side_packet_action_names": list(
                _copy_string_tuple(self.social_side_packet_action_names)
            ),
            "social_side_packet_status": self.social_side_packet_status,
            "sanitized_handoff_action_names": list(
                _copy_string_tuple(self.sanitized_handoff_action_names)
            ),
            "stopped": bool(self.stopped),
            "stop_reason": self.stop_reason,
            "final_answer_posture": self.final_answer_posture,
            "executor_events": _json_safe(self.executor_events),
            "evidence_boundary_events": _json_safe(self.evidence_boundary_events),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerStateReducerResult:
    """JSON-safe result from applying one or more AG-25 envelopes."""

    before: ControllerStateSnapshot
    after: ControllerStateSnapshot
    applied_actions: tuple[Mapping[str, Any], ...]
    budget_effects: tuple[ControllerBudgetEffect, ...] = ()
    evidence_boundary_assertions: tuple[ControllerEvidenceBoundaryAssertion, ...] = ()
    executor_effects: tuple[Mapping[str, Any], ...] = ()
    state_delta: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_STATE_REDUCER_RESULT_SCHEMA_VERSION,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "applied_actions": _json_safe(self.applied_actions),
            "budget_effects": [effect.to_dict() for effect in self.budget_effects],
            "evidence_boundary_assertions": [
                assertion.to_dict()
                for assertion in self.evidence_boundary_assertions
            ],
            "executor_effects": _json_safe(self.executor_effects),
            "state_delta": _json_safe(self.state_delta),
            "warnings": list(self.warnings),
            "metadata": _json_safe(self.metadata),
        }


def controller_executor_descriptors() -> dict[str, dict[str, Any]]:
    """Return executor descriptors for current active, passive, and future actions."""

    return {
        action_name: _executor_descriptor_for_action(action_name).to_dict()
        for action_name in controller_action_names()
    }


def controller_budget_descriptors() -> dict[str, dict[str, Any]]:
    """Return budget descriptors without changing runtime budget ownership."""

    descriptors = (
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.RETRIEVAL_ITERATION,
            owner="current retrieval loop",
            scope="offline representation of targeted retrieval iteration pressure",
            applies_to_actions=(
                RETRIEVE_TARGETED,
                RECOVER_WEAK_CORPUS,
                RECOVER_MISSING_SOURCE_CLASS,
                RESOLVE_CONFLICT,
            ),
            limit_source="iteration and max_iterations facts already present in snapshots",
            promotion_notes=(
                "exact runtime timing remains owned by existing retrieval control flow",
            ),
        ),
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.WEAK_CORPUS_RECOVERY,
            owner="weak-corpus controller decision plus current runtime branch",
            scope="one represented weak-corpus recovery attempt",
            applies_to_actions=(RECOVER_WEAK_CORPUS,),
            limit_source="WeakCorpusRecoveryControllerInput.prior_attempted",
            promotion_notes=(
                "executor abstraction is descriptive; runtime timing is unchanged",
            ),
        ),
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.SOURCE_CLASS_RECOVERY,
            owner="source-class recovery controller and executor boundary",
            scope="one represented source-class recovery attempt",
            applies_to_actions=(RECOVER_MISSING_SOURCE_CLASS,),
            limit_source="SourceClassRecoveryControllerInput.prior_attempt_count",
            promotion_notes=(
                "official/legal slot remains bounded and does not tune providers",
            ),
        ),
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.ANSWER_CONTRACT_RECOVERY_ACTION,
            owner="answer-contract controller state",
            scope="offline answer-contract action and recovery attempt accounting",
            applies_to_actions=tuple(controller_action_names()),
            limit_source="AnswerControllerCaps and already-produced action history",
            promotion_notes=(
                "answer-contract loop remains passive unless a later phase promotes it",
            ),
        ),
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.SOCIAL_SIDE_PACKET,
            owner="future social side-packet action slot",
            scope="placeholder only; no provider integration or ordinary evidence merge",
            applies_to_actions=(REQUEST_SOCIAL_SIGNAL_CHECK,),
            limit_source="future policy/API gates; unavailable in AG-27",
            promotion_notes=("must remain Author-safe side-packet evidence only",),
        ),
        ControllerBudgetDescriptor(
            budget_class=ControllerBudgetClass.LIVE_CALL,
            owner="not owned by AG-27 reducer",
            scope="placeholder showing that the reducer allocates no live calls",
            applies_to_actions=tuple(controller_action_names()),
            limit_source="always zero in this offline reducer",
            promotion_notes=("runtime promotion requires a separate live-call policy",),
        ),
    )
    return {item.budget_class.value: item.to_dict() for item in descriptors}


def controller_evidence_boundary_descriptors() -> dict[str, dict[str, Any]]:
    """Return the evidence-boundary contract asserted by the reducer."""

    ordinary_actions = tuple(
        action
        for action in controller_action_names()
        if action_can_enter_ordinary_evidence(action)
    )
    return {
        ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY.value: {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY.value,
            "allowed_actions": list(ordinary_actions),
            "required_handoff_boundary": (
                ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE.value
            ),
            "social_side_packet_excluded": True,
        },
        ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE.value: {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": (
                ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE.value
            ),
            "allowed_actions": list(ordinary_actions),
            "requires_explicit_evidence_class": True,
            "evidence_classes": list(OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE_CLASSES),
            "social_side_packet_excluded": True,
        },
        ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value: {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value,
            "allowed_actions": [REQUEST_SOCIAL_SIGNAL_CHECK],
            "evidence_classes": list(SOCIAL_SIGNAL_SIDE_PACKET_CLASSES)
            + ["social_signal_perception"],
            "ordinary_evidence_registry_merge_allowed": False,
        },
        ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY.value: {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY.value,
            "allowed_actions": [STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT],
            "allowed_state_fields": ["stopped", "stop_reason", "final_answer_posture"],
        },
        ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY.value: {
            "schema_version": CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION,
            "boundary": ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY.value,
            "allowed_actions": sorted(
                _HANDOFF_ONLY_ACTIONS | {RUN_SCRUTINEER_REVIEW, REQUEST_SOCIAL_SIGNAL_CHECK}
            ),
            "raw_packet_allowed": False,
            "raw_prompt_allowed": False,
            "provider_payload_allowed": False,
        },
    }


def reduce_controller_state(
    snapshot: ControllerStateSnapshot | Mapping[str, Any] | None,
    envelopes: Sequence[ControllerActionEnvelope | Mapping[str, Any]],
) -> ControllerStateReducerResult:
    """Apply AG-25 envelopes to an offline controller-state snapshot."""

    before = coerce_controller_state_snapshot(snapshot)
    current = before
    applied: list[Mapping[str, Any]] = []
    budget_effects: list[ControllerBudgetEffect] = []
    boundary_assertions: list[ControllerEvidenceBoundaryAssertion] = []
    executor_effects: list[Mapping[str, Any]] = []
    warnings: list[str] = []

    for envelope in envelopes:
        payload = _envelope_payload(envelope)
        action_name = _action_name(payload)
        applied.append(_action_history_item(payload))
        try:
            executor_descriptor = _executor_descriptor_for_action(action_name)
        except KeyError:
            warnings.append(f"unknown_action:{action_name}")
            continue

        action_budget_effects = _budget_effects_for_envelope(payload)
        action_boundary_assertions = evidence_boundary_assertions_for_envelope(payload)
        executor_effect = _executor_effect(payload, executor_descriptor)

        current = _apply_payload_to_snapshot(
            current,
            payload,
            budget_effects=action_budget_effects,
            boundary_assertions=action_boundary_assertions,
            executor_effect=executor_effect,
        )
        budget_effects.extend(action_budget_effects)
        boundary_assertions.extend(action_boundary_assertions)
        executor_effects.append(executor_effect)

    after = current
    return ControllerStateReducerResult(
        before=before,
        after=after,
        applied_actions=tuple(applied),
        budget_effects=tuple(budget_effects),
        evidence_boundary_assertions=tuple(boundary_assertions),
        executor_effects=tuple(executor_effects),
        state_delta=_snapshot_delta(before, after),
        warnings=tuple(warnings),
        metadata={
            "offline_only": True,
            "uses_ag25_action_envelope": True,
            "runtime_behavior_changed": False,
            "live_side_effects": False,
            "controller_drives_runtime": False,
        },
    )


def apply_controller_action_envelope(
    snapshot: ControllerStateSnapshot | Mapping[str, Any] | None,
    envelope: ControllerActionEnvelope | Mapping[str, Any],
) -> ControllerStateReducerResult:
    """Apply one AG-25 envelope to an offline controller-state snapshot."""

    return reduce_controller_state(snapshot, (envelope,))


def coerce_controller_state_snapshot(
    snapshot: ControllerStateSnapshot | Mapping[str, Any] | None,
) -> ControllerStateSnapshot:
    """Return a ControllerStateSnapshot from an existing snapshot or mapping."""

    if isinstance(snapshot, ControllerStateSnapshot):
        return snapshot
    if snapshot is None:
        return ControllerStateSnapshot()
    source = dict(snapshot)
    return ControllerStateSnapshot(
        iteration=max(0, int(source.get("iteration") or 0)),
        action_history=tuple(_mapping_tuple(source.get("action_history"))),
        recovery_attempts=_int_mapping(source.get("recovery_attempts")),
        budget_counters=_int_mapping(source.get("budget_counters")),
        budget_events=tuple(_mapping_tuple(source.get("budget_events"))),
        pending_queries=_copy_string_tuple(source.get("pending_queries")),
        ordinary_evidence_action_names=_copy_string_tuple(
            source.get("ordinary_evidence_action_names")
        ),
        ordinary_evidence_candidate_count=max(
            0,
            int(source.get("ordinary_evidence_candidate_count") or 0),
        ),
        official_legal_current_primary_action_names=_copy_string_tuple(
            source.get("official_legal_current_primary_action_names")
        ),
        social_side_packet_action_names=_copy_string_tuple(
            source.get("social_side_packet_action_names")
        ),
        social_side_packet_status=_optional_string(
            source.get("social_side_packet_status")
        ),
        sanitized_handoff_action_names=_copy_string_tuple(
            source.get("sanitized_handoff_action_names")
        ),
        stopped=bool(source.get("stopped")),
        stop_reason=_optional_string(source.get("stop_reason")),
        final_answer_posture=_optional_string(source.get("final_answer_posture")),
        executor_events=tuple(_mapping_tuple(source.get("executor_events"))),
        evidence_boundary_events=tuple(
            _mapping_tuple(source.get("evidence_boundary_events"))
        ),
        metadata=_mapping(source.get("metadata")),
    )


def evidence_boundary_assertions_for_envelope(
    envelope: ControllerActionEnvelope | Mapping[str, Any],
) -> tuple[ControllerEvidenceBoundaryAssertion, ...]:
    """Return evidence-boundary assertions for one AG-25 envelope."""

    payload = _envelope_payload(envelope)
    action_name = _action_name(payload)
    status = _status(payload)
    side_effect = _side_effect_class(payload)
    handoff_boundary = _handoff_boundary(payload)
    active = status in _PASSIVE_RECORDABLE_STATUSES
    ordinary_allowed = (
        active
        and action_name != REQUEST_SOCIAL_SIGNAL_CHECK
        and handoff_boundary
        == ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE.value
        and action_can_enter_ordinary_evidence(action_name)
    )
    official_classes = _official_evidence_classes(payload)
    official_allowed = bool(ordinary_allowed and official_classes)
    social_action = (
        action_name == REQUEST_SOCIAL_SIGNAL_CHECK
        or side_effect == ControllerActionSideEffectClass.SOCIAL_SIDE_PACKET.value
    )
    final_posture_allowed = (
        active
        and handoff_boundary
        == ControllerActionHandoffBoundary.FINAL_ANSWER_POSTURE_ONLY.value
    )
    sanitized_allowed = (
        active
        and (
            handoff_boundary
            == ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY.value
            or action_name in _HANDOFF_ONLY_ACTIONS
            or side_effect
            in {
                ControllerActionSideEffectClass.HANDOFF_ONLY.value,
                ControllerActionSideEffectClass.REVIEW_ONLY.value,
            }
        )
    )

    return (
        ControllerEvidenceBoundaryAssertion(
            boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
            action_name=action_name,
            allowed=ordinary_allowed,
            reason=(
                "ordinary evidence boundary is available"
                if ordinary_allowed
                else "action output is not ordinary evidence eligible"
            ),
            state_field="ordinary_evidence_action_names",
        ),
        ControllerEvidenceBoundaryAssertion(
            boundary=(
                ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE
            ),
            action_name=action_name,
            allowed=official_allowed,
            reason=(
                "action explicitly references official/legal/current-primary evidence"
                if official_allowed
                else "action does not repair official/legal/current-primary evidence"
            ),
            evidence_classes=official_classes,
            state_field="official_legal_current_primary_action_names",
        ),
        ControllerEvidenceBoundaryAssertion(
            boundary=ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE,
            action_name=action_name,
            allowed=social_action,
            reason=(
                "social signal is represented only as a side packet"
                if social_action
                else "action is not a social side-packet action"
            ),
            evidence_classes=(
                (*SOCIAL_SIGNAL_SIDE_PACKET_CLASSES, "social_signal_perception")
                if social_action
                else ()
            ),
            state_field="social_side_packet_action_names",
            metadata={
                "ordinary_evidence_registry_merge_allowed": False,
                "may_support_factual_claims": False,
            }
            if social_action
            else {},
        ),
        ControllerEvidenceBoundaryAssertion(
            boundary=ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY,
            action_name=action_name,
            allowed=final_posture_allowed,
            reason=(
                "action may update only final answer posture and stop state"
                if final_posture_allowed
                else "action is not a final-answer posture boundary"
            ),
            state_field="final_answer_posture",
        ),
        ControllerEvidenceBoundaryAssertion(
            boundary=ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY,
            action_name=action_name,
            allowed=sanitized_allowed,
            reason=(
                "action may expose sanitized summary or handoff state only"
                if sanitized_allowed
                else "action is not a sanitized handoff boundary"
            ),
            state_field="sanitized_handoff_action_names",
            metadata={
                "raw_packet_allowed": False,
                "raw_prompt_allowed": False,
                "provider_payload_allowed": False,
            }
            if sanitized_allowed
            else {},
        ),
    )


def _apply_payload_to_snapshot(
    snapshot: ControllerStateSnapshot,
    payload: Mapping[str, Any],
    *,
    budget_effects: Sequence[ControllerBudgetEffect],
    boundary_assertions: Sequence[ControllerEvidenceBoundaryAssertion],
    executor_effect: Mapping[str, Any],
) -> ControllerStateSnapshot:
    before = snapshot.to_dict()
    action_name = _action_name(payload)
    status = _status(payload)
    output_delta = _mapping(payload.get("output_delta"))
    approved_work = _mapping(payload.get("approved_work"))

    action_history = [*before["action_history"], _action_history_item(payload)]
    recovery_attempts = dict(before["recovery_attempts"])
    budget_counters = dict(before["budget_counters"])
    budget_events = [*before["budget_events"]]
    pending_queries = list(before["pending_queries"])
    ordinary_actions = list(before["ordinary_evidence_action_names"])
    official_actions = list(before["official_legal_current_primary_action_names"])
    social_actions = list(before["social_side_packet_action_names"])
    sanitized_actions = list(before["sanitized_handoff_action_names"])
    executor_events = [*before["executor_events"], _json_safe(executor_effect)]
    boundary_events = [*before["evidence_boundary_events"]]
    stopped = bool(before["stopped"])
    stop_reason = before["stop_reason"]
    final_answer_posture = before["final_answer_posture"]
    social_side_packet_status = before["social_side_packet_status"]
    evidence_candidate_count = int(before["ordinary_evidence_candidate_count"])

    if status in _ACTIVE_STATUSES:
        if action_name == RECOVER_WEAK_CORPUS:
            _increment(recovery_attempts, RECOVER_WEAK_CORPUS)
        elif action_name == RECOVER_MISSING_SOURCE_CLASS:
            _increment(recovery_attempts, RECOVER_MISSING_SOURCE_CLASS)

    for effect in budget_effects:
        effect_payload = effect.to_dict()
        budget_events.append(effect_payload)
        if effect.usage_delta:
            _increment(
                budget_counters,
                effect.budget_class.value,
                amount=effect.usage_delta,
            )

    queries = _copy_string_tuple(approved_work.get("queries"))
    if queries and status in _PASSIVE_RECORDABLE_STATUSES:
        pending_queries = _dedupe_strings((*pending_queries, *queries))

    for assertion in boundary_assertions:
        assertion_payload = assertion.to_dict()
        boundary_events.append(assertion_payload)
        if not assertion.allowed:
            continue
        if (
            assertion.boundary
            is ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY
        ):
            ordinary_actions = _dedupe_strings((*ordinary_actions, action_name))
            if status in _ACTIVE_STATUSES:
                evidence_candidate_count += 1
        elif (
            assertion.boundary
            is ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE
        ):
            official_actions = _dedupe_strings((*official_actions, action_name))
        elif assertion.boundary is ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE:
            social_actions = _dedupe_strings((*social_actions, action_name))
            social_side_packet_status = _social_status(payload)
        elif assertion.boundary is ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY:
            stop_state = _mapping(output_delta.get("stop_state"))
            stopped = True
            stop_reason = _optional_string(
                stop_state.get("reason") or payload.get("reason")
            )
            fallback_posture = None
            if action_name == STOP_INSUFFICIENT_WITH_CAVEAT:
                fallback_posture = "answer with caveats"
            elif action_name == STOP_SUFFICIENT:
                fallback_posture = "answer from sufficient evidence"
            final_answer_posture = _optional_string(
                stop_state.get("final_answer_posture") or fallback_posture
            )
        elif assertion.boundary is ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY:
            sanitized_actions = _dedupe_strings((*sanitized_actions, action_name))

    next_iteration = max(
        int(before["iteration"] or 0),
        _safe_int(_mapping(payload.get("input_summary")).get("iteration")),
    )

    return ControllerStateSnapshot(
        iteration=next_iteration,
        action_history=tuple(action_history),
        recovery_attempts=recovery_attempts,
        budget_counters=budget_counters,
        budget_events=tuple(budget_events),
        pending_queries=tuple(pending_queries),
        ordinary_evidence_action_names=tuple(ordinary_actions),
        ordinary_evidence_candidate_count=evidence_candidate_count,
        official_legal_current_primary_action_names=tuple(official_actions),
        social_side_packet_action_names=tuple(social_actions),
        social_side_packet_status=social_side_packet_status,
        sanitized_handoff_action_names=tuple(sanitized_actions),
        stopped=stopped,
        stop_reason=stop_reason,
        final_answer_posture=final_answer_posture,
        executor_events=tuple(executor_events),
        evidence_boundary_events=tuple(boundary_events),
        metadata={
            **before["metadata"],
            "offline_only": True,
            "runtime_behavior_changed": False,
        },
    )


def _budget_effects_for_envelope(
    payload: Mapping[str, Any],
) -> tuple[ControllerBudgetEffect, ...]:
    action_name = _action_name(payload)
    status = _status(payload)
    reason = _optional_string(payload.get("reason") or payload.get("skip_reason"))
    effects: list[ControllerBudgetEffect] = [
        ControllerBudgetEffect(
            budget_class=ControllerBudgetClass.LIVE_CALL,
            action_name=action_name,
            effect="no_live_call_allocated",
            usage_delta=0,
            reason="AG-27 reducer is offline-only",
        )
    ]

    if action_name == RECOVER_WEAK_CORPUS:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.WEAK_CORPUS_RECOVERY,
                action_name=action_name,
                effect=(
                    "represented_attempt"
                    if status in _ACTIVE_STATUSES
                    else "no_attempt"
                ),
                usage_delta=1 if status in _ACTIVE_STATUSES else 0,
                reason=reason,
                metadata={"one_attempt_only": True},
            )
        )
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.RETRIEVAL_ITERATION,
                action_name=action_name,
                effect="orchestrator_owned_retrieval_timing_descriptor",
                usage_delta=0,
                reason=reason,
            )
        )
    elif action_name == RECOVER_MISSING_SOURCE_CLASS:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.SOURCE_CLASS_RECOVERY,
                action_name=action_name,
                effect=(
                    "represented_attempt"
                    if status in _ACTIVE_STATUSES
                    else "no_attempt"
                ),
                usage_delta=1 if status in _ACTIVE_STATUSES else 0,
                reason=reason,
                metadata={"one_bounded_attempt": True},
            )
        )
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.RETRIEVAL_ITERATION,
                action_name=action_name,
                effect="source_class_recovery_timing_descriptor",
                usage_delta=0,
                reason=reason,
            )
        )
    elif action_name in {RETRIEVE_TARGETED, RESOLVE_CONFLICT}:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.RETRIEVAL_ITERATION,
                action_name=action_name,
                effect=(
                    "represented_targeted_retrieval"
                    if status in _ACTIVE_STATUSES
                    else "retrieval_not_dispatched"
                ),
                usage_delta=1 if status in _ACTIVE_STATUSES else 0,
                reason=reason,
            )
        )
    elif action_name == REQUEST_SOCIAL_SIGNAL_CHECK:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.SOCIAL_SIDE_PACKET,
                action_name=action_name,
                effect="placeholder_only_no_provider_budget",
                usage_delta=0,
                reason=reason,
                metadata={"ordinary_evidence_registry_merge_allowed": False},
            )
        )
    elif action_name in {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.RETRIEVAL_ITERATION,
                action_name=action_name,
                effect="terminal_posture_no_new_retrieval_budget",
                usage_delta=0,
                reason=reason,
            )
        )

    if action_name in _PASSIVE_ACTIONS or action_name in {
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        REQUEST_SOCIAL_SIGNAL_CHECK,
    }:
        effects.append(
            ControllerBudgetEffect(
                budget_class=ControllerBudgetClass.ANSWER_CONTRACT_RECOVERY_ACTION,
                action_name=action_name,
                effect="action_recorded_offline",
                usage_delta=1 if status in _PASSIVE_RECORDABLE_STATUSES else 0,
                reason=reason,
            )
        )

    return tuple(effects)


def _executor_descriptor_for_action(action_name: str) -> ControllerExecutorDescriptor:
    descriptor = get_controller_action_descriptor(action_name)
    authority = descriptor.authority.value
    side_effect = descriptor.side_effect_class.value
    if authority == "future":
        mode = ControllerExecutorMode.FUTURE_PLACEHOLDER
    elif authority == "shadow":
        mode = ControllerExecutorMode.SHADOW_DESCRIPTOR
    elif side_effect == ControllerActionSideEffectClass.STOP.value:
        mode = ControllerExecutorMode.ACTIVE_TERMINAL_RUNTIME_OWNED
    elif authority == "active":
        mode = ControllerExecutorMode.ACTIVE_RUNTIME_OWNED
    else:
        mode = ControllerExecutorMode.PASSIVE_DESCRIPTOR

    blockers: list[str] = []
    if mode in {
        ControllerExecutorMode.PASSIVE_DESCRIPTOR,
        ControllerExecutorMode.SHADOW_DESCRIPTOR,
    }:
        blockers.append("not_runtime_controller_loop_authority")
    if mode is ControllerExecutorMode.FUTURE_PLACEHOLDER:
        blockers.append("future_placeholder_no_runtime_provider")
    if action_name == RECOVER_WEAK_CORPUS:
        blockers.append("weak_corpus_executor_not_factored_out")
    if action_name in {RETRIEVE_TARGETED, STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}:
        blockers.append("retrieval_loop_timing_remains_runtime_owned")

    return ControllerExecutorDescriptor(
        action_name=action_name,
        current_authority=authority,
        executor_mode=mode,
        side_effect_class=side_effect,
        executor=descriptor.executor,
        handoff_boundary=descriptor.handoff_boundary.value,
        promotion_blockers=tuple(blockers),
        metadata={
            "owner": descriptor.owner,
            "known_limitations": list(descriptor.known_limitations),
        },
    )


def _executor_effect(
    payload: Mapping[str, Any],
    descriptor: ControllerExecutorDescriptor,
) -> dict[str, Any]:
    return {
        "action_name": descriptor.action_name,
        "status": _status(payload),
        "executor_mode": descriptor.executor_mode.value,
        "executor": descriptor.executor,
        "descriptor_only": True,
        "runtime_behavior_changed": False,
        "side_effect_class": _side_effect_class(payload),
        "handoff_boundary": _handoff_boundary(payload),
    }


def _envelope_payload(
    envelope: ControllerActionEnvelope | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(envelope, ControllerActionEnvelope):
        return envelope.to_dict()
    to_dict = getattr(envelope, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    if isinstance(envelope, Mapping):
        return _json_safe(envelope)
    raise TypeError("controller state reducer requires AG-25 envelope mappings")


def _action_history_item(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": _action_name(payload),
        "status": _status(payload),
        "authority": _optional_string(payload.get("authority")),
        "side_effect_class": _side_effect_class(payload),
        "reason": _optional_string(payload.get("reason")),
        "skip_reason": _optional_string(payload.get("skip_reason")),
        "handoff_boundary": _handoff_boundary(payload),
        "executor": _optional_string(payload.get("executor")),
    }


def _snapshot_delta(
    before: ControllerStateSnapshot,
    after: ControllerStateSnapshot,
) -> dict[str, Any]:
    before_payload = before.to_dict()
    after_payload = after.to_dict()
    delta: dict[str, Any] = {}
    for key, value in after_payload.items():
        if key == "schema_version":
            continue
        if before_payload.get(key) != value:
            delta[key] = value
    return delta


def _official_evidence_classes(payload: Mapping[str, Any]) -> tuple[str, ...]:
    encoded = " ".join(
        str(item)
        for item in (
            payload.get("reason"),
            payload.get("input_summary"),
            payload.get("approved_work"),
            payload.get("output_delta"),
        )
    ).casefold()
    return tuple(
        source_class
        for source_class in OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE_CLASSES
        if source_class.casefold() in encoded
    )


def _social_status(payload: Mapping[str, Any]) -> str:
    output_delta = _mapping(payload.get("output_delta"))
    status = _optional_string(output_delta.get("social_signal_status"))
    return status or "placeholder_future_action"


def _action_name(payload: Mapping[str, Any]) -> str:
    return str(payload.get("name") or "")


def _status(payload: Mapping[str, Any]) -> str:
    return str(payload.get("status") or "")


def _side_effect_class(payload: Mapping[str, Any]) -> str | None:
    return _optional_string(payload.get("side_effect_class"))


def _handoff_boundary(payload: Mapping[str, Any]) -> str | None:
    return _optional_string(payload.get("handoff_boundary"))


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            if _is_sensitive_key(key):
                continue
            out[str(key)] = _json_safe(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    return str(value)


def _mapping(value: Any) -> dict[str, Any]:
    return deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _mapping_tuple(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(_mapping(item) for item in value if isinstance(item, Mapping))


def _int_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): max(0, int(item or 0))
        for key, item in value.items()
        if not isinstance(item, bool)
    }


def _safe_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _copy_string_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple, set)):
        return ()
    return tuple(_dedupe_strings(str(value or "") for value in values))


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _increment(mapping: dict[str, int], key: str, *, amount: int = 1) -> None:
    mapping[key] = max(0, int(mapping.get(key, 0) or 0)) + max(0, int(amount or 0))


__all__ = [
    "CONTROLLER_BUDGET_DESCRIPTOR_SCHEMA_VERSION",
    "CONTROLLER_EVIDENCE_BOUNDARY_SCHEMA_VERSION",
    "CONTROLLER_EXECUTOR_DESCRIPTOR_SCHEMA_VERSION",
    "CONTROLLER_STATE_REDUCER_RESULT_SCHEMA_VERSION",
    "CONTROLLER_STATE_SNAPSHOT_SCHEMA_VERSION",
    "OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE_CLASSES",
    "ControllerBudgetClass",
    "ControllerBudgetDescriptor",
    "ControllerBudgetEffect",
    "ControllerEvidenceBoundary",
    "ControllerEvidenceBoundaryAssertion",
    "ControllerExecutorDescriptor",
    "ControllerExecutorMode",
    "ControllerStateReducerResult",
    "ControllerStateSnapshot",
    "apply_controller_action_envelope",
    "coerce_controller_state_snapshot",
    "controller_budget_descriptors",
    "controller_evidence_boundary_descriptors",
    "controller_executor_descriptors",
    "evidence_boundary_assertions_for_envelope",
    "reduce_controller_state",
]
