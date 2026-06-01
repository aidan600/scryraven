"""AnswerContract posture activation for AG-78C indirect-inference handoff state.

This module turns already-visible AG-78C indirect-inference runtime handoff
state into bounded Controller/AnswerContract posture metadata. It does not infer
new facts, alter prompts, choose citations, call providers, touch retrieval,
persist state, or change final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.indirect_inference_contract import (
    PROTECTED_SURFACE_FLAGS,
    InferencePath,
    InferencePosture,
    PremiseConflictImpact,
)
from core.indirect_inference_runtime_handoff import (
    INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY,
    IndirectInferenceRuntimeHandoff,
)

INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION = (
    "AG78D.indirect_inference_answer_posture_activation.v1"
)
INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY = (
    "indirect_inference_answer_posture_activation"
)
INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_CONSUMER = (
    "answer_contract_runtime_handoff"
)

_INFERRED_POSTURES = {
    InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
    InferencePosture.CAVEATED_INFERENCE,
}
_SOURCE_BOUND_POSTURES = {InferencePosture.RANGE_BOUND_INFERENCE}
_UNSUPPORTED_POSTURES = {
    InferencePosture.UNSUPPORTED,
    InferencePosture.SPECULATIVE,
    InferencePosture.DECLINED,
}

_BEHAVIOR_FLAGS: Mapping[str, bool] = {
    "final_answer_behavior_changed": False,
    "author_behavior_changed": False,
    "citation_behavior_changed": False,
    "provider_search_retrieval_behavior_changed": False,
    "pipeline_orchestrator_behavior_changed": False,
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return _json_safe(deepcopy(dict(value or {})))


def _relationship_source_ids(path: InferencePath) -> list[str]:
    return [source_id for bridge in path.bridges for source_id in bridge.relationship_source_ids]


def _bridge_types(path: InferencePath) -> list[str]:
    return [_json_safe(bridge.bridge_type) for bridge in path.bridges]


def _premise_conflict_impacts(path: InferencePath) -> list[str]:
    seen: set[str] = set()
    impacts: list[str] = []
    for premise in path.premises:
        impact = str(_json_safe(premise.conflict_impact) or "")
        if impact and impact not in seen:
            impacts.append(impact)
            seen.add(impact)
    return impacts


def _lower_tier_non_satisfaction(path: InferencePath) -> bool:
    return any(
        premise.conflict_impact
        == PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION
        or not premise.satisfies_required_source_obligation
        for premise in path.premises
    )


def _source_bound_or_range_bound(path: InferencePath) -> bool:
    return path.posture in _SOURCE_BOUND_POSTURES or any(
        premise.source_bound_numeric for premise in path.premises
    )


def _resolved_scalar(path: InferencePath) -> bool:
    return bool(path.target_claim.resolved_scalar) and path.posture not in _SOURCE_BOUND_POSTURES


def _posture_for_activation(path: InferencePath) -> InferencePosture:
    # AG-78B evaluator-derived posture is already authoritative. AG-78D only
    # mirrors it into AnswerContract/controller posture metadata.
    return path.posture


def _answer_posture_marker(path: InferencePath) -> str:
    posture = _posture_for_activation(path)
    if posture == InferencePosture.DIRECTLY_SOURCED:
        return InferencePosture.DIRECTLY_SOURCED.value
    if posture in _INFERRED_POSTURES:
        return InferencePosture.INFERRED_FROM_SOURCED_PREMISES.value
    if posture == InferencePosture.BLOCKED_BY_PREMISE_CONFLICT:
        return InferencePosture.BLOCKED_BY_PREMISE_CONFLICT.value
    if posture == InferencePosture.RANGE_BOUND_INFERENCE:
        return InferencePosture.RANGE_BOUND_INFERENCE.value
    if posture == InferencePosture.SPECULATIVE:
        return InferencePosture.SPECULATIVE.value
    return posture.value


@dataclass(frozen=True)
class IndirectInferenceAnswerPostureActivationInput:
    """Already-visible AG-78C handoff supplied to the posture activator."""

    runtime_handoff: IndirectInferenceRuntimeHandoff | None = None
    controller_state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndirectInferencePostureEffect:
    """Per-path AnswerContract/controller posture effect."""

    path_id: str
    target_claim_id: str
    target_claim_text: str
    path_posture: InferencePosture
    answer_posture: str
    directly_sourced: bool
    requires_inference_label: bool
    premise_ids: tuple[str, ...] = ()
    premise_source_ids: tuple[str, ...] = ()
    bridge_ids: tuple[str, ...] = ()
    bridge_types: tuple[str, ...] = ()
    relationship_source_ids: tuple[str, ...] = ()
    direct_source_ids: tuple[str, ...] = ()
    premise_conflict_impacts: tuple[str, ...] = ()
    speculative_or_unsupported: bool = False
    blocked_by_premise_conflict: bool = False
    range_bound_or_source_bound: bool = False
    resolved_scalar: bool = False
    lower_tier_non_satisfaction: bool = False
    stronger_obligation_satisfied: bool = False
    evaluator_authoritative_posture_recommendation: bool = True

    def to_controller_state(self) -> dict[str, Any]:
        return _json_safe(
            {
                "path_id": self.path_id,
                "target_claim_id": self.target_claim_id,
                "target_claim_text": self.target_claim_text,
                "path_posture": self.path_posture,
                "answer_posture": self.answer_posture,
                "directly_sourced": self.directly_sourced,
                "requires_inference_label": self.requires_inference_label,
                "premise_ids": list(self.premise_ids),
                "premise_source_ids": list(self.premise_source_ids),
                "bridge_ids": list(self.bridge_ids),
                "bridge_types": list(self.bridge_types),
                "relationship_source_ids": list(self.relationship_source_ids),
                "direct_source_ids": list(self.direct_source_ids),
                "premise_conflict_impacts": list(self.premise_conflict_impacts),
                "speculative_or_unsupported": self.speculative_or_unsupported,
                "blocked_by_premise_conflict": self.blocked_by_premise_conflict,
                "range_bound_or_source_bound": self.range_bound_or_source_bound,
                "resolved_scalar": self.resolved_scalar,
                "lower_tier_non_satisfaction": self.lower_tier_non_satisfaction,
                "stronger_obligation_satisfied": self.stronger_obligation_satisfied,
                "evaluator_authoritative_posture_recommendation": (
                    self.evaluator_authoritative_posture_recommendation
                ),
            }
        )


@dataclass(frozen=True)
class IndirectInferenceAnswerPostureActivation:
    """AG-78D AnswerContract posture activation output."""

    effects: tuple[IndirectInferencePostureEffect, ...] = ()
    runtime_handoff_state: Mapping[str, Any] = field(default_factory=dict)

    @property
    def direct_claim_count(self) -> int:
        return sum(effect.directly_sourced for effect in self.effects)

    @property
    def inferred_claim_count(self) -> int:
        return sum(effect.requires_inference_label for effect in self.effects)

    @property
    def speculative_unsupported_count(self) -> int:
        return sum(effect.speculative_or_unsupported for effect in self.effects)

    @property
    def blocked_by_premise_conflict_count(self) -> int:
        return sum(effect.blocked_by_premise_conflict for effect in self.effects)

    @property
    def range_bound_source_bound_count(self) -> int:
        return sum(effect.range_bound_or_source_bound for effect in self.effects)

    @property
    def lower_tier_non_satisfaction_count(self) -> int:
        return sum(effect.lower_tier_non_satisfaction for effect in self.effects)

    def _summary(self) -> dict[str, Any]:
        if not self.effects:
            primary = "no_answer_impact"
        elif self.blocked_by_premise_conflict_count:
            primary = InferencePosture.BLOCKED_BY_PREMISE_CONFLICT.value
        elif self.inferred_claim_count:
            primary = InferencePosture.INFERRED_FROM_SOURCED_PREMISES.value
        elif self.range_bound_source_bound_count:
            primary = InferencePosture.RANGE_BOUND_INFERENCE.value
        elif self.direct_claim_count:
            primary = InferencePosture.DIRECTLY_SOURCED.value
        elif self.speculative_unsupported_count:
            primary = "unsupported_or_speculative"
        else:
            primary = "no_answer_impact"
        return {
            "primary_posture": primary,
            "has_answer_posture_effect": bool(self.effects),
            "no_answer_impact": not bool(self.effects),
        }

    def to_controller_state(self) -> dict[str, Any]:
        state = {
            "schema_version": INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION,
            "state_key": INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
            "ag78c_state_key": INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY,
            "consumer": INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_CONSUMER,
            "path_effects": [effect.to_controller_state() for effect in self.effects],
            "top_level_posture_summary": self._summary(),
            "direct_claim_count": self.direct_claim_count,
            "inferred_claim_count": self.inferred_claim_count,
            "speculative_unsupported_count": self.speculative_unsupported_count,
            "blocked_by_premise_conflict_count": self.blocked_by_premise_conflict_count,
            "range_bound_source_bound_count": self.range_bound_source_bound_count,
            "lower_tier_non_satisfaction_count": self.lower_tier_non_satisfaction_count,
            "runtime_handoff_present": bool(self.runtime_handoff_state),
            "runtime_handoff_state_key": INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY,
            "final_answer_behavior_changed": False,
            "author_behavior_changed": False,
            "citation_behavior_changed": False,
            "provider_search_retrieval_behavior_changed": False,
            "pipeline_orchestrator_behavior_changed": False,
            "protected_surface_flags": dict(PROTECTED_SURFACE_FLAGS),
            **dict(_BEHAVIOR_FLAGS),
        }
        return _json_safe(state)

    def to_trace_fragment(self) -> dict[str, Any]:
        return {INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY: self.to_controller_state()}

    def execution_trace_fragment(self) -> dict[str, Any]:
        return self.to_trace_fragment()


def _effect_from_path(path: InferencePath) -> IndirectInferencePostureEffect:
    posture = _posture_for_activation(path)
    inferred = posture in _INFERRED_POSTURES
    directly_sourced = posture == InferencePosture.DIRECTLY_SOURCED and path.directly_sourced_target
    lower_tier_non_satisfaction = _lower_tier_non_satisfaction(path)
    return IndirectInferencePostureEffect(
        path_id=path.path_id,
        target_claim_id=path.target_claim.claim_id,
        target_claim_text=path.target_claim.claim_text,
        path_posture=posture,
        answer_posture=_answer_posture_marker(path),
        directly_sourced=directly_sourced,
        requires_inference_label=inferred,
        premise_ids=tuple(premise.premise_id for premise in path.premises),
        premise_source_ids=tuple(path.premise_source_ids),
        bridge_ids=tuple(bridge.bridge_id for bridge in path.bridges),
        bridge_types=tuple(_bridge_types(path)),
        relationship_source_ids=tuple(_relationship_source_ids(path)),
        direct_source_ids=tuple(
            source.source_id for source in path.target_claim.source_attributions
        ),
        premise_conflict_impacts=tuple(_premise_conflict_impacts(path)),
        speculative_or_unsupported=posture in _UNSUPPORTED_POSTURES,
        blocked_by_premise_conflict=posture
        == InferencePosture.BLOCKED_BY_PREMISE_CONFLICT,
        range_bound_or_source_bound=_source_bound_or_range_bound(path),
        resolved_scalar=_resolved_scalar(path),
        lower_tier_non_satisfaction=lower_tier_non_satisfaction,
        stronger_obligation_satisfied=not lower_tier_non_satisfaction
        and posture not in _UNSUPPORTED_POSTURES,
    )


def build_indirect_inference_answer_posture_activation(
    runtime_handoff: IndirectInferenceRuntimeHandoff | IndirectInferenceAnswerPostureActivationInput | None,
) -> IndirectInferenceAnswerPostureActivation | None:
    """Activate bounded AnswerContract posture metadata from AG-78C state."""
    if isinstance(runtime_handoff, IndirectInferenceAnswerPostureActivationInput):
        controller_state = runtime_handoff.controller_state
        runtime_handoff = runtime_handoff.runtime_handoff
    else:
        controller_state = {}
    if runtime_handoff is None:
        return None
    runtime_state = runtime_handoff.to_controller_state()
    paths: Sequence[InferencePath] = runtime_handoff.state.paths
    return IndirectInferenceAnswerPostureActivation(
        effects=tuple(_effect_from_path(path) for path in paths),
        runtime_handoff_state={**_copy_mapping(runtime_state), **_copy_mapping(controller_state)},
    )


def indirect_inference_answer_posture_activation_trace_fragment(
    runtime_handoff: IndirectInferenceRuntimeHandoff | IndirectInferenceAnswerPostureActivationInput | None,
) -> dict[str, Any]:
    """Return AG-78D trace only when AG-78C handoff exists."""
    activation = build_indirect_inference_answer_posture_activation(runtime_handoff)
    if activation is None:
        return {}
    return activation.to_trace_fragment()


__all__ = [
    "INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_CONSUMER",
    "INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_SCHEMA_VERSION",
    "INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY",
    "IndirectInferenceAnswerPostureActivationInput",
    "IndirectInferencePostureEffect",
    "IndirectInferenceAnswerPostureActivation",
    "build_indirect_inference_answer_posture_activation",
    "indirect_inference_answer_posture_activation_trace_fragment",
]
