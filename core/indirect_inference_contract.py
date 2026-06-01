"""Inert indirect-inference representation contracts for Controller-visible state.

This module represents direct, inferred, caveated, range-bound, unsupported, and
speculative target-claim postures without executing inference, retrieval,
citation selection, prompt changes, provider calls, persistence, cache behavior,
or final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

INDIRECT_INFERENCE_SCHEMA_VERSION = "AG78B.minimal_indirect_inference_contract.v1"
INDIRECT_INFERENCE_TRACE_KEY = "indirect_inference_contract"


class InferencePosture(str, Enum):
    """How the target claim is supported or blocked."""

    DIRECTLY_SOURCED = "directly_sourced"
    INFERRED_FROM_SOURCED_PREMISES = "inferred_from_sourced_premises"
    CAVEATED_INFERENCE = "caveated_inference"
    RANGE_BOUND_INFERENCE = "range_bound_inference"
    BLOCKED_BY_PREMISE_CONFLICT = "blocked_by_premise_conflict"
    UNSUPPORTED = "unsupported"
    SPECULATIVE = "speculative"
    DECLINED = "declined"


class InferenceBridgeType(str, Enum):
    """Taxonomy for the relationship connecting premises to a target claim."""

    MATHEMATICAL = "mathematical"
    DEFINITIONAL = "definitional"
    LEGAL_STATUTORY = "legal_statutory"
    DOMAIN_STANDARD = "domain_standard"
    SOURCE_STATED_RELATIONSHIP = "source_stated_relationship"
    MODEL_ASSUMED_SPECULATIVE = "model_assumed_speculative"


class InferenceModePolicy(str, Enum):
    """Controller mode whose inference posture is being represented."""

    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"


class PremiseConflictImpact(str, Enum):
    """AG-77-derived impact of conflict posture on premise usability."""

    NONE = "none"
    WEAKENS = "weakens"
    RANGE_BOUNDS = "range_bounds"
    BLOCKS = "blocks"
    BACKGROUND_ONLY = "background_only"
    NON_SATISFYING_FOR_OBLIGATION = "non_satisfying_for_obligation"


class BridgeStrength(str, Enum):
    """Strength label for a bridge; never upgrades unusable premises."""

    EXACT = "exact"
    HIGH_CONFIDENCE = "high_confidence"
    DOMAIN_CONDITIONED = "domain_conditioned"
    ASSUMPTION_DEPENDENT = "assumption_dependent"
    SPECULATIVE = "speculative"


class PathRecommendation(str, Enum):
    """Recommended Controller-visible posture outcome for the path."""

    MAY_STATE = "may_state"
    STATE_WITH_CAVEAT = "state_with_caveat"
    RANGE_BOUND = "range_bound"
    DECLINE = "decline"
    UNSUPPORTED = "unsupported"


PROTECTED_SURFACE_FLAGS: Mapping[str, bool] = {
    "final_answer_behavior_changed": False,
    "author_behavior_changed": False,
    "author_exposure_changed": False,
    "citation_behavior_changed": False,
    "provider_behavior_changed": False,
    "search_behavior_changed": False,
    "query_behavior_changed": False,
    "retrieval_behavior_changed": False,
    "db_session_runoutcome_behavior_changed": False,
    "cache_behavior_changed": False,
    "scrutineer_behavior_changed": False,
    "economist_followup_behavior_changed": False,
    "orchestrator_behavior_changed": False,
    "runtime_inference_execution_changed": False,
    "live_validation_behavior_changed": False,
}


@dataclass(frozen=True)
class InferenceSourceAttribution:
    """Source identity attached to a premise or bridge relationship."""

    source_id: str
    source_class: str | None = None
    source_tier: str | None = None
    title: str | None = None
    url: str | None = None
    publisher: str | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    effective_period_start: str | None = None
    effective_period_end: str | None = None
    jurisdiction: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _clean_text(self.source_id, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_class": _clean_optional_text(self.source_class, limit=80),
            "source_tier": _clean_optional_text(self.source_tier, limit=80),
            "title": _clean_optional_text(self.title, limit=240),
            "url": _clean_optional_text(self.url, limit=500),
            "publisher": _clean_optional_text(self.publisher, limit=160),
            "retrieved_at": _clean_optional_text(self.retrieved_at, limit=80),
            "published_at": _clean_optional_text(self.published_at, limit=80),
            "updated_at": _clean_optional_text(self.updated_at, limit=80),
            "effective_period_start": _clean_optional_text(self.effective_period_start, limit=80),
            "effective_period_end": _clean_optional_text(self.effective_period_end, limit=80),
            "jurisdiction": _clean_optional_text(self.jurisdiction, limit=120),
            "scope": _clean_optional_text(self.scope, limit=160),
        }


@dataclass(frozen=True)
class TargetClaim:
    """A target answer claim and the posture under which it may be represented."""

    claim_id: str
    claim_text: str
    posture: InferencePosture | str
    directly_sourced: bool = False
    source_attributions: tuple[InferenceSourceAttribution, ...] = ()
    value: str | int | float | bool | None = None
    unit: str | None = None
    jurisdiction: str | None = None
    scope: str | None = None
    date_or_period: str | None = None
    resolved_scalar: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", _clean_text(self.claim_id, limit=120))
        posture = _enum_value(self.posture, InferencePosture, InferencePosture.UNSUPPORTED)
        object.__setattr__(self, "posture", posture)
        object.__setattr__(self, "source_attributions", _copy_sources(self.source_attributions))
        if posture != InferencePosture.DIRECTLY_SOURCED:
            object.__setattr__(self, "directly_sourced", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": _clean_text(self.claim_text, limit=600),
            "posture": self.posture,
            "directly_sourced": bool(self.directly_sourced),
            "source_attributions": [source.to_dict() for source in self.source_attributions],
            "source_ids": [source.source_id for source in self.source_attributions],
            "value": _json_scalar(self.value),
            "unit": _clean_optional_text(self.unit, limit=60),
            "jurisdiction": _clean_optional_text(self.jurisdiction, limit=120),
            "scope": _clean_optional_text(self.scope, limit=160),
            "date_or_period": _clean_optional_text(self.date_or_period, limit=120),
            "resolved_scalar": bool(self.resolved_scalar),
        }


@dataclass(frozen=True)
class SourcedPremise:
    """A premise with preserved source, scope, dates, units, and conflict impact."""

    premise_id: str
    claim_text: str
    source_attribution: InferenceSourceAttribution
    value: str | int | float | bool | None = None
    unit: str | None = None
    date_or_period: str | None = None
    effective_period_start: str | None = None
    effective_period_end: str | None = None
    jurisdiction: str | None = None
    scope: str | None = None
    conflict_impact: PremiseConflictImpact | str = PremiseConflictImpact.NONE
    required_for_inference: bool = True
    source_bound_numeric: bool = False
    satisfies_required_source_obligation: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "premise_id", _clean_text(self.premise_id, limit=120))
        if not isinstance(self.source_attribution, InferenceSourceAttribution):
            raise TypeError("source_attribution must be InferenceSourceAttribution")
        object.__setattr__(
            self,
            "conflict_impact",
            _enum_value(self.conflict_impact, PremiseConflictImpact, PremiseConflictImpact.NONE),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "premise_id": self.premise_id,
            "claim_text": _clean_text(self.claim_text, limit=600),
            "source_attribution": self.source_attribution.to_dict(),
            "source_id": self.source_attribution.source_id,
            "source_class": self.source_attribution.source_class,
            "source_tier": self.source_attribution.source_tier,
            "value": _json_scalar(self.value),
            "unit": _clean_optional_text(self.unit, limit=60),
            "date_or_period": _clean_optional_text(self.date_or_period, limit=120),
            "effective_period_start": _clean_optional_text(self.effective_period_start, limit=80),
            "effective_period_end": _clean_optional_text(self.effective_period_end, limit=80),
            "jurisdiction": _clean_optional_text(self.jurisdiction or self.source_attribution.jurisdiction, limit=120),
            "scope": _clean_optional_text(self.scope or self.source_attribution.scope, limit=160),
            "conflict_impact": self.conflict_impact,
            "required_for_inference": bool(self.required_for_inference),
            "source_bound_numeric": bool(self.source_bound_numeric),
            "satisfies_required_source_obligation": bool(self.satisfies_required_source_obligation),
        }


@dataclass(frozen=True)
class InferenceBridge:
    """Explicit bridge connecting sourced premises to a target claim."""

    bridge_id: str
    bridge_type: InferenceBridgeType | str
    description: str
    strength: BridgeStrength | str
    allowed_modes: tuple[InferenceModePolicy | str, ...] = (InferenceModePolicy.BALANCED, InferenceModePolicy.DEEP)
    source_attributions: tuple[InferenceSourceAttribution, ...] = ()
    assumption_labels: tuple[str, ...] = ()
    valid: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "bridge_id", _clean_text(self.bridge_id, limit=120))
        object.__setattr__(
            self,
            "bridge_type",
            _enum_value(self.bridge_type, InferenceBridgeType, InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE),
        )
        object.__setattr__(self, "strength", _enum_value(self.strength, BridgeStrength, BridgeStrength.SPECULATIVE))
        object.__setattr__(
            self,
            "allowed_modes",
            tuple(_enum_value(mode, InferenceModePolicy, InferenceModePolicy.BALANCED) for mode in self.allowed_modes),
        )
        object.__setattr__(self, "source_attributions", _copy_sources(self.source_attributions))
        object.__setattr__(self, "assumption_labels", _copy_string_tuple(self.assumption_labels, cap=12, limit=180))

    @property
    def relationship_source_ids(self) -> list[str]:
        return [source.source_id for source in self.source_attributions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge_id": self.bridge_id,
            "bridge_type": self.bridge_type,
            "description": _clean_text(self.description, limit=800),
            "strength": self.strength,
            "allowed_modes": list(self.allowed_modes),
            "source_attributions": [source.to_dict() for source in self.source_attributions],
            "relationship_source_ids": self.relationship_source_ids,
            "assumption_labels": list(self.assumption_labels),
            "valid": bool(self.valid),
        }


@dataclass(frozen=True)
class InferencePath:
    """A Controller-visible, non-executing path from premises through bridges to target."""

    path_id: str
    target_claim: TargetClaim
    premises: tuple[SourcedPremise, ...] = ()
    bridges: tuple[InferenceBridge, ...] = ()
    mode: InferenceModePolicy | str = InferenceModePolicy.BALANCED
    depth: int = 1
    posture: InferencePosture | str | None = None
    recommendation: PathRecommendation | str | None = None
    controller_visible: bool = True
    trace_visible: bool = True
    notes: tuple[str, ...] = ()
    protected_surface_flags: Mapping[str, bool] = field(default_factory=lambda: dict(PROTECTED_SURFACE_FLAGS))

    def __post_init__(self) -> None:
        object.__setattr__(self, "path_id", _clean_text(self.path_id, limit=120))
        if not isinstance(self.target_claim, TargetClaim):
            raise TypeError("target_claim must be TargetClaim")
        object.__setattr__(self, "premises", _copy_premises(self.premises))
        object.__setattr__(self, "bridges", _copy_bridges(self.bridges))
        object.__setattr__(self, "mode", _enum_value(self.mode, InferenceModePolicy, InferenceModePolicy.BALANCED))
        object.__setattr__(self, "depth", max(0, int(self.depth)))
        posture, recommendation = _evaluate_path(self)
        object.__setattr__(self, "posture", posture)
        object.__setattr__(self, "recommendation", recommendation)
        object.__setattr__(self, "notes", _copy_string_tuple(self.notes, cap=12, limit=220))
        flags = dict(PROTECTED_SURFACE_FLAGS)
        flags.update({key: bool(value) for key, value in dict(self.protected_surface_flags).items()})
        object.__setattr__(self, "protected_surface_flags", flags)

    @property
    def allowed_by_mode_policy(self) -> bool:
        return self.recommendation in {
            PathRecommendation.MAY_STATE,
            PathRecommendation.STATE_WITH_CAVEAT,
            PathRecommendation.RANGE_BOUND,
        }

    @property
    def directly_sourced_target(self) -> bool:
        return self.target_claim.posture == InferencePosture.DIRECTLY_SOURCED and self.target_claim.directly_sourced

    @property
    def premise_source_ids(self) -> list[str]:
        return [premise.source_attribution.source_id for premise in self.premises]

    @property
    def bridge_source_ids(self) -> list[str]:
        return [source_id for bridge in self.bridges for source_id in bridge.relationship_source_ids]

    def to_controller_state(self) -> dict[str, Any]:
        return {
            "schema_version": INDIRECT_INFERENCE_SCHEMA_VERSION,
            "state_key": INDIRECT_INFERENCE_TRACE_KEY,
            "path_id": self.path_id,
            "controller_visible": bool(self.controller_visible),
            "target_claim": self.target_claim.to_dict(),
            "premises": [premise.to_dict() for premise in self.premises],
            "bridges": [bridge.to_dict() for bridge in self.bridges],
            "mode": self.mode,
            "depth": self.depth,
            "posture": self.posture,
            "recommendation": self.recommendation,
            "allowed_by_mode_policy": self.allowed_by_mode_policy,
            "directly_sourced_target": self.directly_sourced_target,
            "inferred_target": self.posture
            in {InferencePosture.INFERRED_FROM_SOURCED_PREMISES, InferencePosture.CAVEATED_INFERENCE},
            "premise_ids": [premise.premise_id for premise in self.premises],
            "premise_source_ids": self.premise_source_ids,
            "bridge_ids": [bridge.bridge_id for bridge in self.bridges],
            "bridge_source_ids": self.bridge_source_ids,
            "resolved_scalar": bool(self.target_claim.resolved_scalar)
            and self.posture != InferencePosture.RANGE_BOUND_INFERENCE,
            "notes": list(self.notes),
            "protected_surface_flags": dict(self.protected_surface_flags),
            **dict(self.protected_surface_flags),
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            INDIRECT_INFERENCE_TRACE_KEY: {
                "schema_version": INDIRECT_INFERENCE_SCHEMA_VERSION,
                "path_id": self.path_id,
                "trace_visible": bool(self.trace_visible),
                "target_claim_id": self.target_claim.claim_id,
                "posture": self.posture,
                "recommendation": self.recommendation,
                "mode": self.mode,
                "depth": self.depth,
                "premise_ids": [premise.premise_id for premise in self.premises],
                "premise_source_ids": self.premise_source_ids,
                "bridge_ids": [bridge.bridge_id for bridge in self.bridges],
                "bridge_source_ids": self.bridge_source_ids,
                "protected_surface_flags": dict(self.protected_surface_flags),
            }
        }


def _evaluate_path(path: InferencePath) -> tuple[InferencePosture, PathRecommendation]:
    target_posture = path.target_claim.posture
    if target_posture == InferencePosture.DIRECTLY_SOURCED:
        return InferencePosture.DIRECTLY_SOURCED, PathRecommendation.MAY_STATE

    required_premises = [premise for premise in path.premises if premise.required_for_inference]
    bridges = list(path.bridges)
    impacts = {premise.conflict_impact for premise in required_premises}

    if PremiseConflictImpact.BLOCKS in impacts:
        return InferencePosture.BLOCKED_BY_PREMISE_CONFLICT, PathRecommendation.DECLINE
    if PremiseConflictImpact.RANGE_BOUNDS in impacts:
        return InferencePosture.RANGE_BOUND_INFERENCE, PathRecommendation.RANGE_BOUND
    if PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION in impacts:
        return InferencePosture.UNSUPPORTED, PathRecommendation.UNSUPPORTED

    if not required_premises or not bridges:
        return InferencePosture.UNSUPPORTED, PathRecommendation.UNSUPPORTED
    if any(not premise.satisfies_required_source_obligation for premise in required_premises):
        return InferencePosture.UNSUPPORTED, PathRecommendation.UNSUPPORTED
    if any(not bridge.valid for bridge in bridges):
        return InferencePosture.UNSUPPORTED, PathRecommendation.UNSUPPORTED
    if any(bridge.bridge_type == InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE for bridge in bridges):
        return InferencePosture.SPECULATIVE, PathRecommendation.UNSUPPORTED
    if any(bridge.strength == BridgeStrength.SPECULATIVE for bridge in bridges):
        return InferencePosture.SPECULATIVE, PathRecommendation.UNSUPPORTED
    if path.mode == InferenceModePolicy.FAST and (len(required_premises) > 1 or path.depth > 1):
        return InferencePosture.DECLINED, PathRecommendation.DECLINE
    if path.mode == InferenceModePolicy.BALANCED and path.depth > 1:
        return InferencePosture.DECLINED, PathRecommendation.DECLINE
    if any(path.mode not in bridge.allowed_modes for bridge in bridges):
        return InferencePosture.UNSUPPORTED, PathRecommendation.UNSUPPORTED
    if PremiseConflictImpact.BACKGROUND_ONLY in impacts:
        return InferencePosture.CAVEATED_INFERENCE, PathRecommendation.STATE_WITH_CAVEAT
    if PremiseConflictImpact.WEAKENS in impacts:
        return InferencePosture.CAVEATED_INFERENCE, PathRecommendation.STATE_WITH_CAVEAT
    if any(bridge.strength in {BridgeStrength.DOMAIN_CONDITIONED, BridgeStrength.ASSUMPTION_DEPENDENT} for bridge in bridges):
        return InferencePosture.CAVEATED_INFERENCE, PathRecommendation.STATE_WITH_CAVEAT
    return InferencePosture.INFERRED_FROM_SOURCED_PREMISES, PathRecommendation.MAY_STATE


def _copy_sources(sources: Sequence[InferenceSourceAttribution]) -> tuple[InferenceSourceAttribution, ...]:
    copied = tuple(sources)
    if any(not isinstance(source, InferenceSourceAttribution) for source in copied):
        raise TypeError("source attributions must be InferenceSourceAttribution")
    return copied


def _copy_premises(premises: Sequence[SourcedPremise]) -> tuple[SourcedPremise, ...]:
    copied = tuple(premises)
    if any(not isinstance(premise, SourcedPremise) for premise in copied):
        raise TypeError("premises must be SourcedPremise")
    return copied


def _copy_bridges(bridges: Sequence[InferenceBridge]) -> tuple[InferenceBridge, ...]:
    copied = tuple(bridges)
    if any(not isinstance(bridge, InferenceBridge) for bridge in copied):
        raise TypeError("bridges must be InferenceBridge")
    return copied


def _enum_value(value: Any, enum_cls: type[Enum], default: Enum) -> str:
    if isinstance(value, enum_cls):
        return str(value.value)
    if isinstance(value, str):
        try:
            return str(enum_cls(value).value)
        except ValueError:
            return str(default.value)
    return str(default.value)


def _copy_string_tuple(values: Sequence[str], *, cap: int, limit: int) -> tuple[str, ...]:
    return tuple(_clean_text(value, limit=limit) for value in tuple(values)[:cap] if _clean_text(value, limit=limit))


def _clean_text(value: Any, *, limit: int, default: str = "") -> str:
    text = str(default if value is None else value).strip()
    if len(text) > limit:
        return text[:limit]
    return text


def _clean_optional_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = _clean_text(value, limit=limit)
    return text or None


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
