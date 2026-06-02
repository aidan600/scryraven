"""Author-presentation handoff for AG-78D indirect-inference posture metadata.

This module converts already-activated AG-78D AnswerContract posture effects into
JSON-safe Author/final-answer presentation labels. It does not infer new facts,
re-evaluate paths, alter prompts, choose citations, call providers, touch
retrieval, persist state, change caches, or orchestrate runtime behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.indirect_inference_answer_posture_activation import (
    INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
    IndirectInferenceAnswerPostureActivation,
    IndirectInferencePostureEffect,
)
from core.indirect_inference_contract import PROTECTED_SURFACE_FLAGS

INDIRECT_INFERENCE_AUTHOR_PRESENTATION_SCHEMA_VERSION = (
    "AG78E.indirect_inference_author_presentation_handoff.v1"
)
INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY = (
    "indirect_inference_author_presentation_handoff"
)
INDIRECT_INFERENCE_AUTHOR_PRESENTATION_CONSUMER = "author_final_answer_presentation"

DIRECTLY_SOURCED_LABEL = "directly sourced"
INFERRED_FROM_SOURCED_PREMISES_LABEL = "inferred from sourced premises"
SPECULATIVE_OR_UNSUPPORTED_LABEL = "speculative or unsupported"
BLOCKED_BY_PREMISE_CONFLICT_LABEL = "blocked by premise conflict"
RANGE_BOUND_OR_SOURCE_BOUND_LABEL = "range-bound or source-bound numeric"

_BEHAVIOR_FLAGS: Mapping[str, bool] = {
    "provider_behavior_changed": False,
    "search_behavior_changed": False,
    "query_behavior_changed": False,
    "retrieval_behavior_changed": False,
    "db_session_runoutcome_behavior_changed": False,
    "cache_behavior_changed": False,
    "scrutineer_behavior_changed": False,
    "remediation_behavior_changed": False,
    "economist_followup_behavior_changed": False,
    "pipeline_orchestrator_behavior_changed": False,
    "citation_selection_ordering_behavior_changed": False,
    "runtime_inference_detection_changed": False,
    "runtime_inference_execution_changed": False,
    "live_validation_behavior_changed": False,
}

_ATTRIBUTION_BOUNDARY = (
    "Premise and bridge source IDs support the sourced premises and bridge "
    "relationships only; they do not mean the inferred conclusion was directly "
    "source-stated unless the claim is labeled directly_sourced."
)


class IndirectInferenceAuthorPresentationLabel(str, Enum):
    """Stable claim-level Author/final-answer presentation labels."""

    DIRECTLY_SOURCED = "directly_sourced"
    INFERRED_FROM_SOURCED_PREMISES = "inferred_from_sourced_premises"
    SPECULATIVE_OR_UNSUPPORTED = "speculative_or_unsupported"
    BLOCKED_BY_PREMISE_CONFLICT = "blocked_by_premise_conflict"
    RANGE_BOUND_OR_SOURCE_BOUND = "range_bound_or_source_bound"


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


def _presentation_label(effect: IndirectInferencePostureEffect) -> IndirectInferenceAuthorPresentationLabel:
    if effect.blocked_by_premise_conflict:
        return IndirectInferenceAuthorPresentationLabel.BLOCKED_BY_PREMISE_CONFLICT
    if effect.range_bound_or_source_bound:
        return IndirectInferenceAuthorPresentationLabel.RANGE_BOUND_OR_SOURCE_BOUND
    if effect.speculative_or_unsupported:
        return IndirectInferenceAuthorPresentationLabel.SPECULATIVE_OR_UNSUPPORTED
    if effect.requires_inference_label:
        return IndirectInferenceAuthorPresentationLabel.INFERRED_FROM_SOURCED_PREMISES
    if effect.directly_sourced:
        return IndirectInferenceAuthorPresentationLabel.DIRECTLY_SOURCED
    return IndirectInferenceAuthorPresentationLabel.SPECULATIVE_OR_UNSUPPORTED


def _human_label(label: IndirectInferenceAuthorPresentationLabel) -> str:
    if label is IndirectInferenceAuthorPresentationLabel.DIRECTLY_SOURCED:
        return DIRECTLY_SOURCED_LABEL
    if label is IndirectInferenceAuthorPresentationLabel.INFERRED_FROM_SOURCED_PREMISES:
        return INFERRED_FROM_SOURCED_PREMISES_LABEL
    if label is IndirectInferenceAuthorPresentationLabel.BLOCKED_BY_PREMISE_CONFLICT:
        return BLOCKED_BY_PREMISE_CONFLICT_LABEL
    if label is IndirectInferenceAuthorPresentationLabel.RANGE_BOUND_OR_SOURCE_BOUND:
        return RANGE_BOUND_OR_SOURCE_BOUND_LABEL
    return SPECULATIVE_OR_UNSUPPORTED_LABEL


@dataclass(frozen=True)
class IndirectInferenceAuthorPresentationClaim:
    """Per-claim Author/final-answer labeling derived from an AG-78D effect."""

    path_id: str
    target_claim_id: str
    target_claim_text: str
    presentation_label: IndirectInferenceAuthorPresentationLabel
    human_label: str
    directly_sourced: bool
    inference_label_required: bool
    conclusion_direct_source_ids: tuple[str, ...] = ()
    premise_ids: tuple[str, ...] = ()
    premise_source_ids: tuple[str, ...] = ()
    bridge_ids: tuple[str, ...] = ()
    bridge_types: tuple[str, ...] = ()
    bridge_relationship_source_ids: tuple[str, ...] = ()
    premise_bridge_sources_support_direct_conclusion: bool = False
    premise_bridge_source_attribution_boundary: str = _ATTRIBUTION_BOUNDARY
    speculative_or_unsupported: bool = False
    blocked_by_premise_conflict: bool = False
    range_bound_or_source_bound: bool = False
    resolved_scalar: bool = False
    lower_tier_non_satisfaction: bool = False
    stronger_obligation_satisfied: bool = False
    source_attribution_mode: str = "premise_or_bridge_support_only"

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "path_id": self.path_id,
                "target_claim_id": self.target_claim_id,
                "target_claim_text": self.target_claim_text,
                "presentation_label": self.presentation_label,
                "human_label": self.human_label,
                "directly_sourced": self.directly_sourced,
                "inference_label_required": self.inference_label_required,
                "conclusion_direct_source_ids": list(self.conclusion_direct_source_ids),
                "premise_ids": list(self.premise_ids),
                "premise_source_ids": list(self.premise_source_ids),
                "bridge_ids": list(self.bridge_ids),
                "bridge_types": list(self.bridge_types),
                "bridge_relationship_source_ids": list(self.bridge_relationship_source_ids),
                "premise_bridge_sources_support_direct_conclusion": (
                    self.premise_bridge_sources_support_direct_conclusion
                ),
                "premise_bridge_source_attribution_boundary": (
                    self.premise_bridge_source_attribution_boundary
                ),
                "speculative_or_unsupported": self.speculative_or_unsupported,
                "blocked_by_premise_conflict": self.blocked_by_premise_conflict,
                "range_bound_or_source_bound": self.range_bound_or_source_bound,
                "resolved_scalar": self.resolved_scalar,
                "lower_tier_non_satisfaction": self.lower_tier_non_satisfaction,
                "stronger_obligation_satisfied": self.stronger_obligation_satisfied,
                "source_attribution_mode": self.source_attribution_mode,
            }
        )


@dataclass(frozen=True)
class IndirectInferenceAuthorPresentationFacts:
    """Aggregate presentation facts for Author/final-answer consumers."""

    claims: tuple[IndirectInferenceAuthorPresentationClaim, ...] = ()

    @property
    def directly_sourced_claim_count(self) -> int:
        return sum(claim.directly_sourced for claim in self.claims)

    @property
    def inferred_claim_count(self) -> int:
        return sum(claim.inference_label_required for claim in self.claims)

    @property
    def speculative_or_unsupported_claim_count(self) -> int:
        return sum(claim.speculative_or_unsupported for claim in self.claims)

    @property
    def blocked_by_premise_conflict_claim_count(self) -> int:
        return sum(claim.blocked_by_premise_conflict for claim in self.claims)

    @property
    def range_bound_or_source_bound_claim_count(self) -> int:
        return sum(claim.range_bound_or_source_bound for claim in self.claims)

    @property
    def lower_tier_non_satisfaction_claim_count(self) -> int:
        return sum(claim.lower_tier_non_satisfaction for claim in self.claims)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "claims": [claim.to_dict() for claim in self.claims],
                "directly_sourced_claim_count": self.directly_sourced_claim_count,
                "inferred_claim_count": self.inferred_claim_count,
                "speculative_or_unsupported_claim_count": (
                    self.speculative_or_unsupported_claim_count
                ),
                "blocked_by_premise_conflict_claim_count": (
                    self.blocked_by_premise_conflict_claim_count
                ),
                "range_bound_or_source_bound_claim_count": (
                    self.range_bound_or_source_bound_claim_count
                ),
                "lower_tier_non_satisfaction_claim_count": (
                    self.lower_tier_non_satisfaction_claim_count
                ),
            }
        )


@dataclass(frozen=True)
class IndirectInferenceAuthorPresentationHandoff:
    """JSON-safe Author/final-answer handoff derived only from AG-78D activation."""

    facts: IndirectInferenceAuthorPresentationFacts = field(
        default_factory=IndirectInferenceAuthorPresentationFacts
    )
    activation_state_present: bool = False

    def to_controller_state(self) -> dict[str, Any]:
        state = {
            "schema_version": INDIRECT_INFERENCE_AUTHOR_PRESENTATION_SCHEMA_VERSION,
            "state_key": INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY,
            "ag78d_state_key": INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
            "consumer": INDIRECT_INFERENCE_AUTHOR_PRESENTATION_CONSUMER,
            "activation_state_present": self.activation_state_present,
            "author_presentation_labeling_enabled": True,
            "citation_laundering_guard_enabled": True,
            "source_attribution_boundary": _ATTRIBUTION_BOUNDARY,
            "presentation_facts": self.facts.to_dict(),
            "protected_surface_flags": dict(PROTECTED_SURFACE_FLAGS),
            **dict(_BEHAVIOR_FLAGS),
        }
        return _json_safe(state)

    def to_trace_fragment(self) -> dict[str, Any]:
        return {INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY: self.to_controller_state()}

    def execution_trace_fragment(self) -> dict[str, Any]:
        return self.to_trace_fragment()


def _claim_from_effect(effect: IndirectInferencePostureEffect) -> IndirectInferenceAuthorPresentationClaim:
    label = _presentation_label(effect)
    directly_sourced = label is IndirectInferenceAuthorPresentationLabel.DIRECTLY_SOURCED
    inference_label_required = (
        label is IndirectInferenceAuthorPresentationLabel.INFERRED_FROM_SOURCED_PREMISES
    )
    conclusion_direct_source_ids = tuple(effect.direct_source_ids) if directly_sourced else ()
    return IndirectInferenceAuthorPresentationClaim(
        path_id=effect.path_id,
        target_claim_id=effect.target_claim_id,
        target_claim_text=effect.target_claim_text,
        presentation_label=label,
        human_label=_human_label(label),
        directly_sourced=directly_sourced,
        inference_label_required=inference_label_required,
        conclusion_direct_source_ids=conclusion_direct_source_ids,
        premise_ids=tuple(effect.premise_ids),
        premise_source_ids=tuple(effect.premise_source_ids),
        bridge_ids=tuple(effect.bridge_ids),
        bridge_types=tuple(effect.bridge_types),
        bridge_relationship_source_ids=tuple(effect.relationship_source_ids),
        premise_bridge_sources_support_direct_conclusion=False,
        speculative_or_unsupported=label
        is IndirectInferenceAuthorPresentationLabel.SPECULATIVE_OR_UNSUPPORTED,
        blocked_by_premise_conflict=label
        is IndirectInferenceAuthorPresentationLabel.BLOCKED_BY_PREMISE_CONFLICT,
        range_bound_or_source_bound=label
        is IndirectInferenceAuthorPresentationLabel.RANGE_BOUND_OR_SOURCE_BOUND,
        resolved_scalar=effect.resolved_scalar
        and label is not IndirectInferenceAuthorPresentationLabel.RANGE_BOUND_OR_SOURCE_BOUND,
        lower_tier_non_satisfaction=effect.lower_tier_non_satisfaction,
        stronger_obligation_satisfied=effect.stronger_obligation_satisfied
        and not effect.lower_tier_non_satisfaction,
        source_attribution_mode=(
            "direct_source_statement" if directly_sourced else "premise_or_bridge_support_only"
        ),
    )


def build_indirect_inference_author_presentation_handoff(
    activation: IndirectInferenceAnswerPostureActivation | None,
) -> IndirectInferenceAuthorPresentationHandoff | None:
    """Build Author presentation labels from AG-78D activation, if present."""
    if activation is None:
        return None
    return IndirectInferenceAuthorPresentationHandoff(
        facts=IndirectInferenceAuthorPresentationFacts(
            claims=tuple(_claim_from_effect(effect) for effect in activation.effects)
        ),
        activation_state_present=True,
    )


def indirect_inference_author_presentation_trace_fragment(
    activation: IndirectInferenceAnswerPostureActivation | None,
) -> dict[str, Any]:
    """Return AG-78E trace only when AG-78D activation exists."""
    handoff = build_indirect_inference_author_presentation_handoff(activation)
    if handoff is None:
        return {}
    return handoff.to_trace_fragment()


__all__ = [
    "BLOCKED_BY_PREMISE_CONFLICT_LABEL",
    "DIRECTLY_SOURCED_LABEL",
    "INDIRECT_INFERENCE_AUTHOR_PRESENTATION_CONSUMER",
    "INDIRECT_INFERENCE_AUTHOR_PRESENTATION_SCHEMA_VERSION",
    "INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY",
    "INFERRED_FROM_SOURCED_PREMISES_LABEL",
    "RANGE_BOUND_OR_SOURCE_BOUND_LABEL",
    "SPECULATIVE_OR_UNSUPPORTED_LABEL",
    "IndirectInferenceAuthorPresentationClaim",
    "IndirectInferenceAuthorPresentationFacts",
    "IndirectInferenceAuthorPresentationHandoff",
    "IndirectInferenceAuthorPresentationLabel",
    "build_indirect_inference_author_presentation_handoff",
    "indirect_inference_author_presentation_trace_fragment",
]
