"""Runtime/AnswerContract visibility handoff for AG-78B inference paths.

This module only serializes already-built AG-78B ``InferencePath`` objects for
Controller and AnswerContract trace consumers. It does not infer facts, call
providers, alter prompts, choose citations, touch retrieval, persist state, or
change final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.indirect_inference_contract import (
    INDIRECT_INFERENCE_TRACE_KEY,
    PROTECTED_SURFACE_FLAGS,
    InferencePath,
    InferencePosture,
    PremiseConflictImpact,
)

INDIRECT_INFERENCE_RUNTIME_HANDOFF_SCHEMA_VERSION = (
    "AG78C.indirect_inference_runtime_answercontract_visibility.v1"
)
INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY = "indirect_inference_runtime_handoff"
INDIRECT_INFERENCE_RUNTIME_HANDOFF_CONSUMER = "answer_contract_runtime_handoff"

_INFERRED_POSTURES = {
    InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
    InferencePosture.CAVEATED_INFERENCE,
    InferencePosture.RANGE_BOUND_INFERENCE,
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


def _copy_controller_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return _json_safe(deepcopy(dict(value or {})))


def _unique_strings(values: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(_json_safe(value) or "").strip()
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _support_marker(path: InferencePath) -> str:
    if path.directly_sourced_target:
        return "direct"
    if path.posture in _INFERRED_POSTURES:
        return "inferred"
    if path.posture == InferencePosture.SPECULATIVE:
        return "speculative"
    if path.posture == InferencePosture.BLOCKED_BY_PREMISE_CONFLICT:
        return "blocked"
    if path.posture == InferencePosture.DECLINED:
        return "declined"
    return "unsupported"


def _numeric_resolution_marker(path: InferencePath) -> str:
    source_bound = any(premise.source_bound_numeric for premise in path.premises)
    if path.posture == InferencePosture.RANGE_BOUND_INFERENCE:
        return "range_bound"
    if bool(path.target_claim.resolved_scalar) and not source_bound:
        return "resolved_scalar"
    if bool(path.target_claim.resolved_scalar):
        return "source_bound_resolved_scalar"
    if source_bound:
        return "source_bound_unresolved"
    return "not_source_bound_numeric"


def _lower_tier_non_satisfaction(path: InferencePath) -> bool:
    return any(
        premise.conflict_impact
        == PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION
        or not premise.satisfies_required_source_obligation
        for premise in path.premises
    )


def _path_visibility(path: InferencePath) -> dict[str, Any]:
    premise_conflict_impacts = _unique_strings(
        [premise.conflict_impact for premise in path.premises]
    )
    bridge_source_ids = [
        source_id for bridge in path.bridges for source_id in bridge.relationship_source_ids
    ]
    protected_surface_flags = dict(PROTECTED_SURFACE_FLAGS)
    protected_surface_flags.update(
        {str(key): bool(value) for key, value in path.protected_surface_flags.items()}
    )
    return _json_safe(
        {
            "path_id": path.path_id,
            "target_claim_id": path.target_claim.claim_id,
            "target_claim_text": path.target_claim.claim_text,
            "target_claim_posture": path.target_claim.posture,
            "path_posture": path.posture,
            "support_marker": _support_marker(path),
            "directly_sourced_target": path.directly_sourced_target,
            "inferred_target": path.posture in _INFERRED_POSTURES,
            "speculative_target": path.posture == InferencePosture.SPECULATIVE,
            "unsupported_target": path.posture == InferencePosture.UNSUPPORTED,
            "inference_mode": path.mode,
            "depth": path.depth,
            "path_recommendation": path.recommendation,
            "premise_ids": [premise.premise_id for premise in path.premises],
            "premise_source_ids": path.premise_source_ids,
            "bridge_ids": [bridge.bridge_id for bridge in path.bridges],
            "bridge_types": [bridge.bridge_type for bridge in path.bridges],
            "relationship_source_ids": bridge_source_ids,
            "bridge_source_ids": bridge_source_ids,
            "premise_conflict_impacts": premise_conflict_impacts,
            "ag77_premise_conflict_impact": premise_conflict_impacts,
            "source_bound_numeric_present": any(
                premise.source_bound_numeric for premise in path.premises
            ),
            "source_bound_numeric_marker": _numeric_resolution_marker(path),
            "resolved_scalar": bool(path.target_claim.resolved_scalar)
            and path.posture != InferencePosture.RANGE_BOUND_INFERENCE,
            "lower_tier_non_satisfaction": _lower_tier_non_satisfaction(path),
            "evaluator_authoritative_posture_recommendation": True,
            "protected_surface_flags": protected_surface_flags,
        }
    )


@dataclass(frozen=True)
class IndirectInferenceRuntimeFacts:
    """Optional AG-78B inputs already available to runtime handoff code."""

    paths: Sequence[InferencePath] = ()
    controller_state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndirectInferenceRuntimeState:
    """JSON-safe Controller/AnswerContract-visible AG-78C state."""

    paths: tuple[InferencePath, ...] = ()
    controller_state: Mapping[str, Any] = field(default_factory=dict)

    def to_controller_state(self) -> dict[str, Any]:
        path_states = [_path_visibility(path) for path in self.paths]
        state = {
            "schema_version": INDIRECT_INFERENCE_RUNTIME_HANDOFF_SCHEMA_VERSION,
            "state_key": INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY,
            "ag78b_state_key": INDIRECT_INFERENCE_TRACE_KEY,
            "consumer": INDIRECT_INFERENCE_RUNTIME_HANDOFF_CONSUMER,
            "inference_available": bool(path_states),
            "no_inference_input": not bool(path_states),
            "answer_behavior_changed": False,
            "no_answer_impact": True,
            "evaluator_authoritative_posture_recommendation": True,
            "protected_surface_flags": dict(PROTECTED_SURFACE_FLAGS),
            "paths": path_states,
            "primary_path": path_states[0] if path_states else None,
            "controller_state_input": _copy_controller_mapping(self.controller_state),
        }
        return _json_safe(state)

    def to_trace_fragment(self) -> dict[str, Any]:
        return {INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY: self.to_controller_state()}


@dataclass(frozen=True)
class IndirectInferenceRuntimeHandoff:
    """Small handoff wrapper for AG-78C Controller/trace consumers."""

    state: IndirectInferenceRuntimeState

    def to_controller_state(self) -> dict[str, Any]:
        return self.state.to_controller_state()

    def to_trace_fragment(self) -> dict[str, Any]:
        return self.state.to_trace_fragment()

    def execution_trace_fragment(self) -> dict[str, Any]:
        return self.to_trace_fragment()


def build_indirect_inference_runtime_handoff(
    paths: InferencePath | Sequence[InferencePath] | None = None,
    *,
    controller_state: Mapping[str, Any] | None = None,
) -> IndirectInferenceRuntimeHandoff:
    """Build a JSON-safe, visibility-only handoff from AG-78B path objects."""
    if paths is None:
        normalized_paths: tuple[InferencePath, ...] = ()
    elif isinstance(paths, InferencePath):
        normalized_paths = (paths,)
    else:
        normalized_paths = tuple(paths)
    if any(not isinstance(path, InferencePath) for path in normalized_paths):
        raise TypeError("paths must be InferencePath objects")
    return IndirectInferenceRuntimeHandoff(
        state=IndirectInferenceRuntimeState(
            paths=normalized_paths,
            controller_state=_copy_controller_mapping(controller_state),
        )
    )


def indirect_inference_runtime_trace_fragment(
    paths: InferencePath | Sequence[InferencePath] | None = None,
    *,
    controller_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the AG-78C trace fragment for optional AG-78B inputs."""
    return build_indirect_inference_runtime_handoff(
        paths,
        controller_state=controller_state,
    ).to_trace_fragment()


__all__ = [
    "INDIRECT_INFERENCE_RUNTIME_HANDOFF_CONSUMER",
    "INDIRECT_INFERENCE_RUNTIME_HANDOFF_SCHEMA_VERSION",
    "INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY",
    "IndirectInferenceRuntimeFacts",
    "IndirectInferenceRuntimeHandoff",
    "IndirectInferenceRuntimeState",
    "build_indirect_inference_runtime_handoff",
    "indirect_inference_runtime_trace_fragment",
]
