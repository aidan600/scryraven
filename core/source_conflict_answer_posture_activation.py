"""AG-77D Controller/AnswerContract posture activation for source conflicts.

This module consumes already-visible AG-77C source-conflict arbitration state and
maps only licensed posture effects into JSON-safe Controller / AnswerContract
posture metadata. It does not retrieve, rank, resolve, cite, prompt, persist,
call providers, alter Author inputs, or change final-answer behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from core.source_conflict_arbitration import (
    SourceConflictAnswerPosture,
    SourceConflictArbitrationDisposition,
    SourceConflictArbitrationReason,
    SourceConflictArbitrationState,
)
from core.source_conflict_arbitration_runtime_handoff import (
    SourceConflictArbitrationRuntimeHandoff,
)

SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION = (
    "AG77D.conflict_arbitration_answer_posture_activation.v1"
)
SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY = (
    "source_conflict_answer_posture_activation"
)


@dataclass(frozen=True)
class SourceConflictPostureActivationInput:
    """Pure input wrapper for AG-77D posture activation."""

    source_conflict_arbitration_runtime_state: Mapping[str, Any] | None = None
    arbitration_state: SourceConflictArbitrationState | None = None

    def __post_init__(self) -> None:
        if self.arbitration_state is not None and not isinstance(
            self.arbitration_state,
            SourceConflictArbitrationState,
        ):
            raise TypeError("arbitration_state must be SourceConflictArbitrationState")
        object.__setattr__(
            self,
            "source_conflict_arbitration_runtime_state",
            _copy_mapping(self.source_conflict_arbitration_runtime_state),
        )


@dataclass(frozen=True)
class SourceConflictPostureEffect:
    """One licensed Controller / AnswerContract posture effect."""

    effect_type: str
    conflict_id: str | None
    group_id: str | None
    obligation_impact: str | None
    answer_posture: str | None
    disposition: str | None
    reason: str | None
    authoritative_posture_blocked: bool = False
    authoritative_posture_insufficient: bool = False
    source_bound_value_unresolved: bool = False
    resolved_source_bound_scalar: bool = False
    lower_tier_non_satisfying_for_stronger_obligation: bool = False
    secondary_background_context_only: bool = False
    nonblocking: bool = False
    no_answer_impact: bool = False
    affected_claim_ids: tuple[str, ...] = ()
    non_satisfying_claim_ids: tuple[str, ...] = ()
    background_only_claim_ids: tuple[str, ...] = ()

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "effect_type": self.effect_type,
            "conflict_id": self.conflict_id,
            "group_id": self.group_id,
            "obligation_impact": self.obligation_impact,
            "answer_posture": self.answer_posture,
            "disposition": self.disposition,
            "reason": self.reason,
            "authoritative_posture_blocked": self.authoritative_posture_blocked,
            "authoritative_posture_insufficient": self.authoritative_posture_insufficient,
            "source_bound_value_unresolved": self.source_bound_value_unresolved,
            "resolved_source_bound_scalar": self.resolved_source_bound_scalar,
            "lower_tier_non_satisfying_for_stronger_obligation": (
                self.lower_tier_non_satisfying_for_stronger_obligation
            ),
            "secondary_background_context_only": self.secondary_background_context_only,
            "nonblocking": self.nonblocking,
            "no_answer_impact": self.no_answer_impact,
            "affected_claim_ids": list(self.affected_claim_ids),
            "non_satisfying_claim_ids": list(self.non_satisfying_claim_ids),
            "background_only_claim_ids": list(self.background_only_claim_ids),
        }


@dataclass(frozen=True)
class SourceConflictAnswerPostureActivation:
    """JSON-safe AG-77D posture activation state."""

    effects: tuple[SourceConflictPostureEffect, ...]
    source_conflict_arbitration_available: bool
    input_trace_key: str | None
    schema_version: str = SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION

    def to_controller_state(self) -> dict[str, Any]:
        effects = [effect.to_controller_state() for effect in self.effects]
        return {
            "schema_version": self.schema_version,
            "trace_key": SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
            "consumer": "Controller / AnswerContract posture",
            "input_trace_key": self.input_trace_key,
            "source_conflict_arbitration_available": (
                self.source_conflict_arbitration_available
            ),
            "effect_count": len(effects),
            "effects": effects,
            "authoritative_posture_blocked": any(
                effect.authoritative_posture_blocked for effect in self.effects
            ),
            "authoritative_posture_insufficient": any(
                effect.authoritative_posture_insufficient for effect in self.effects
            ),
            "source_bound_unresolved_value_count": sum(
                1 for effect in self.effects if effect.source_bound_value_unresolved
            ),
            "resolved_source_bound_scalar_count": sum(
                1 for effect in self.effects if effect.resolved_source_bound_scalar
            ),
            "lower_tier_non_satisfaction_preserved": any(
                effect.lower_tier_non_satisfying_for_stronger_obligation
                for effect in self.effects
            ),
            "secondary_background_context_only": any(
                effect.secondary_background_context_only for effect in self.effects
            ),
            "nonblocking_background_conflict_count": sum(
                1 for effect in self.effects if effect.nonblocking
            ),
            "no_answer_impact": not any(
                effect.authoritative_posture_blocked
                or effect.authoritative_posture_insufficient
                or effect.source_bound_value_unresolved
                or effect.lower_tier_non_satisfying_for_stronger_obligation
                for effect in self.effects
            ),
            "no_final_answer_prose_change": True,
            "final_answer_behavior_changed": False,
            "runtime_behavior_changed": False,
            "author_behavior_changed": False,
            "author_exposure_changed": False,
            "citation_behavior_changed": False,
            "prompt_behavior_changed": False,
            "provider_search_query_behavior_changed": False,
            "retrieval_behavior_changed": False,
            "scrutineer_behavior_changed": False,
            "economist_followup_behavior_changed": False,
            "db_session_runoutcome_behavior_changed": False,
            "cache_behavior_changed": False,
            "ag78_indirect_inference_changed": False,
            "numeric_output_behavior_changed": False,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY: (
                self.to_controller_state()
            )
        }


def build_source_conflict_answer_posture_activation(
    activation_input: SourceConflictPostureActivationInput
    | SourceConflictArbitrationRuntimeHandoff
    | SourceConflictArbitrationState
    | Mapping[str, Any]
    | None = None,
    *,
    source_conflict_arbitration_runtime_state: Mapping[str, Any] | None = None,
    arbitration_state: SourceConflictArbitrationState | None = None,
) -> SourceConflictAnswerPostureActivation:
    """Map AG-77C/AG-77B arbitration posture into licensed AG-77D effects."""

    runtime_state: Mapping[str, Any] | None = source_conflict_arbitration_runtime_state
    input_arbitration_state = arbitration_state
    if isinstance(activation_input, SourceConflictPostureActivationInput):
        runtime_state = activation_input.source_conflict_arbitration_runtime_state
        input_arbitration_state = activation_input.arbitration_state
    elif isinstance(activation_input, SourceConflictArbitrationRuntimeHandoff):
        runtime_state = activation_input.to_controller_state()
    elif isinstance(activation_input, SourceConflictArbitrationState):
        input_arbitration_state = activation_input
    elif isinstance(activation_input, Mapping):
        runtime_state = activation_input
    elif activation_input is not None:
        raise TypeError("unsupported source conflict posture activation input")

    controller_state = _controller_state_from_inputs(
        runtime_state=runtime_state,
        arbitration_state=input_arbitration_state,
    )
    effects = tuple(_effects_from_controller_state(controller_state))
    return SourceConflictAnswerPostureActivation(
        effects=effects,
        source_conflict_arbitration_available=bool(controller_state),
        input_trace_key=(
            None if not controller_state else str(controller_state.get("trace_key") or "")
        )
        or None,
    )


def source_conflict_answer_posture_activation_trace_fragment(
    activation_input: SourceConflictPostureActivationInput
    | SourceConflictArbitrationRuntimeHandoff
    | SourceConflictArbitrationState
    | Mapping[str, Any]
    | None = None,
    *,
    source_conflict_arbitration_runtime_state: Mapping[str, Any] | None = None,
    arbitration_state: SourceConflictArbitrationState | None = None,
) -> dict[str, Any]:
    """Return the stable AG-77D Controller / AnswerContract trace fragment."""

    return build_source_conflict_answer_posture_activation(
        activation_input,
        source_conflict_arbitration_runtime_state=(
            source_conflict_arbitration_runtime_state
        ),
        arbitration_state=arbitration_state,
    ).to_trace_fragment()


def _controller_state_from_inputs(
    *,
    runtime_state: Mapping[str, Any] | None,
    arbitration_state: SourceConflictArbitrationState | None,
) -> dict[str, Any]:
    if runtime_state:
        return _copy_mapping(runtime_state)
    if arbitration_state is None:
        return {}
    return {"arbitration": arbitration_state.to_controller_state(), "trace_key": None}


def _effects_from_controller_state(
    controller_state: Mapping[str, Any],
) -> list[SourceConflictPostureEffect]:
    arbitration = controller_state.get("arbitration")
    if not isinstance(arbitration, Mapping):
        return []

    effects: list[SourceConflictPostureEffect] = []
    for group in arbitration.get("groups") or []:
        if not isinstance(group, Mapping):
            continue
        for record in group.get("record_arbitrations") or []:
            if not isinstance(record, Mapping):
                continue
            effect = _effect_from_record(record)
            if effect is not None:
                effects.append(effect)
    return effects


def _effect_from_record(record: Mapping[str, Any]) -> SourceConflictPostureEffect | None:
    disposition = _string_or_none(record.get("disposition"))
    answer_posture = _string_or_none(record.get("answer_posture"))
    reason = _string_or_none(record.get("reason"))

    base = {
        "conflict_id": _string_or_none(record.get("conflict_id")),
        "group_id": _string_or_none(record.get("group_id")),
        "obligation_impact": _string_or_none(record.get("obligation_impact")),
        "answer_posture": answer_posture,
        "disposition": disposition,
        "reason": reason,
        "affected_claim_ids": _string_tuple(record.get("claim_ids_preserved")),
        "non_satisfying_claim_ids": _string_tuple(
            record.get("non_satisfying_claim_ids")
        ),
        "background_only_claim_ids": _string_tuple(
            record.get("background_only_claim_ids")
        ),
    }

    if (
        disposition == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING.value
        and answer_posture
        == SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER.value
    ):
        return SourceConflictPostureEffect(
            effect_type="authoritative_posture_blocked_insufficient",
            authoritative_posture_blocked=True,
            authoritative_posture_insufficient=True,
            **base,
        )

    if answer_posture == SourceConflictAnswerPosture.SOURCE_BOUND_VALUE_UNRESOLVED.value:
        return SourceConflictPostureEffect(
            effect_type="source_bound_value_unresolved",
            source_bound_value_unresolved=True,
            resolved_source_bound_scalar=False,
            **base,
        )

    if bool(record.get("lower_tier_cannot_satisfy_stronger_obligation")):
        return SourceConflictPostureEffect(
            effect_type="lower_tier_non_satisfaction_background_context",
            lower_tier_non_satisfying_for_stronger_obligation=True,
            secondary_background_context_only=True,
            **base,
        )

    if (
        disposition == SourceConflictArbitrationDisposition.BACKGROUND_ONLY.value
        or reason == SourceConflictArbitrationReason.PERIPHERAL_OR_BACKGROUND_ONLY.value
    ):
        return SourceConflictPostureEffect(
            effect_type="peripheral_background_nonblocking",
            nonblocking=True,
            no_answer_impact=True,
            **base,
        )

    return None


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_tuple(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(value, (list, tuple)):
        return ()
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return tuple(out)


__all__ = [
    "SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION",
    "SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY",
    "SourceConflictAnswerPostureActivation",
    "SourceConflictPostureActivationInput",
    "SourceConflictPostureEffect",
    "build_source_conflict_answer_posture_activation",
    "source_conflict_answer_posture_activation_trace_fragment",
]
