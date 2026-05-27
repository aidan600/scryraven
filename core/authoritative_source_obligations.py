from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class AuthorityRequirementType(str, Enum):
    OFFICIAL_CURRENT = "official_current"
    CANONICAL_PROJECT_DOC = "canonical_project_doc"
    ACADEMIC_LITERATURE = "academic_literature"
    LEGAL_CURRENT_PRIMARY = "legal_current_primary"
    SOURCE_BOUND_NUMERIC = "source_bound_numeric"
    LOWER_TIER_CONTEXT = "lower_tier_context"
    COMPOSITE = "composite"


class AuthorityComposition(str, Enum):
    ATOMIC = "atomic"
    ALL = "all"
    ANY = "any"
    ONE_OF = "one_of"
    FALLBACK_ORDERED = "fallback_ordered"


class AuthorityStatus(str, Enum):
    FULFILLED = "fulfilled"
    PARTIAL = "partial"
    UNFULFILLED = "unfulfilled"


OFFICIAL_CURRENT_RULES = "official_current_rules"
PRIMARY_SOURCE_DOCUMENTS = "primary_source_documents"
ACADEMIC_LITERATURE = "academic_literature"
LEGAL_OR_REGULATORY_TEXT = "legal_or_regulatory_text"
SOURCED_NUMERIC_VALUES = "sourced_numeric_values"

REPUTABLE_SECONDARY = "reputable_secondary"
SECONDARY = "secondary"
TRUSTED_COMMUNITY = "trusted_community"
SOCIAL_OR_FORUM = "social_or_forum"
LOWER_TIER_CONTEXT_CLASSES = (
    REPUTABLE_SECONDARY,
    SECONDARY,
    TRUSTED_COMMUNITY,
    SOCIAL_OR_FORUM,
)

_PROTECTED_MARKERS = (
    "raw_prompt",
    "raw prompt",
    "provider_payload",
    "full_trace",
    "database",
    "db row",
    "cache",
    "secret",
    "private log",
    "prompt",
)


def _normalize_tuple(values: Sequence[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value) for value in values if str(value))


def _safe_label(value: str | None, *, limit: int = 80) -> str | None:
    if value is None:
        return None
    compact = " ".join(str(value).split())
    if any(marker in compact.casefold() for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    if len(compact) > limit:
        return f"{compact[: limit - 3]}..."
    return compact


def _merge_unique(items: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            merged.append(item)
    return tuple(merged)


@dataclass(frozen=True, slots=True)
class AuthorityRequirement:
    requirement_id: str
    requirement_type: AuthorityRequirementType
    required_authority_classes: tuple[str, ...] = ()
    allowed_context_classes: tuple[str, ...] = LOWER_TIER_CONTEXT_CLASSES
    composition: AuthorityComposition = AuthorityComposition.ATOMIC
    children: tuple["AuthorityRequirement", ...] = ()
    current_anchor: str | None = None
    temporal_anchor: str | None = None
    jurisdiction: str | None = None
    subject: str | None = None
    source_binding_id: str | None = None
    fallback_posture: str | None = None

    @classmethod
    def official_current(
        cls,
        requirement_id: str,
        *,
        current_anchor: str | None = None,
        temporal_anchor: str | None = None,
        subject: str | None = None,
        fallback_posture: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.OFFICIAL_CURRENT,
            required_authority_classes=(OFFICIAL_CURRENT_RULES,),
            current_anchor=current_anchor,
            temporal_anchor=temporal_anchor,
            subject=subject,
            fallback_posture=fallback_posture,
        )

    @classmethod
    def canonical_project_doc(
        cls,
        requirement_id: str,
        *,
        subject: str | None = None,
        fallback_posture: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.CANONICAL_PROJECT_DOC,
            required_authority_classes=(PRIMARY_SOURCE_DOCUMENTS,),
            subject=subject,
            fallback_posture=fallback_posture,
        )

    @classmethod
    def academic_literature(
        cls,
        requirement_id: str,
        *,
        subject: str | None = None,
        fallback_posture: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.ACADEMIC_LITERATURE,
            required_authority_classes=(ACADEMIC_LITERATURE,),
            subject=subject,
            fallback_posture=fallback_posture,
        )

    @classmethod
    def legal_current_primary(
        cls,
        requirement_id: str,
        *,
        jurisdiction: str | None = None,
        current_anchor: str | None = None,
        temporal_anchor: str | None = None,
        subject: str | None = None,
        fallback_posture: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.LEGAL_CURRENT_PRIMARY,
            required_authority_classes=(LEGAL_OR_REGULATORY_TEXT, OFFICIAL_CURRENT_RULES),
            current_anchor=current_anchor,
            temporal_anchor=temporal_anchor,
            jurisdiction=jurisdiction,
            subject=subject,
            fallback_posture=fallback_posture,
        )

    @classmethod
    def source_bound_numeric(
        cls,
        requirement_id: str,
        *,
        source_binding_id: str | None = None,
        subject: str | None = None,
        fallback_posture: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.SOURCE_BOUND_NUMERIC,
            required_authority_classes=(SOURCED_NUMERIC_VALUES,),
            source_binding_id=source_binding_id,
            subject=subject,
            fallback_posture=fallback_posture,
        )

    @classmethod
    def lower_tier_context(
        cls,
        requirement_id: str,
        *,
        allowed_context_classes: Sequence[str] | None = None,
        subject: str | None = None,
    ) -> "AuthorityRequirement":
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.LOWER_TIER_CONTEXT,
            required_authority_classes=(),
            allowed_context_classes=_normalize_tuple(allowed_context_classes)
            or LOWER_TIER_CONTEXT_CLASSES,
            subject=subject,
        )

    @classmethod
    def compose(
        cls,
        requirement_id: str,
        composition: AuthorityComposition,
        children: Sequence["AuthorityRequirement"],
        *,
        fallback_posture: str | None = None,
        subject: str | None = None,
    ) -> "AuthorityRequirement":
        if composition is AuthorityComposition.ATOMIC:
            raise ValueError("composite requirements must use a non-atomic composition")
        child_tuple = tuple(children)
        if not child_tuple:
            raise ValueError("composite requirements require at least one child")
        return cls(
            requirement_id=requirement_id,
            requirement_type=AuthorityRequirementType.COMPOSITE,
            composition=composition,
            children=child_tuple,
            subject=subject,
            fallback_posture=fallback_posture,
        )

    def leaf_requirements(self) -> tuple["AuthorityRequirement", ...]:
        if not self.children:
            return (self,)
        leaves: list[AuthorityRequirement] = []
        for child in self.children:
            leaves.extend(child.leaf_requirements())
        return tuple(leaves)

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": _safe_label(self.requirement_id),
            "requirement_type": self.requirement_type.value,
            "required_authority_classes": list(self.required_authority_classes),
            "allowed_context_classes": list(self.allowed_context_classes),
            "composition": self.composition.value,
            "child_requirement_ids": [
                _safe_label(child.requirement_id) for child in self.children
            ],
            "current_anchor": _safe_label(self.current_anchor, limit=40),
            "temporal_anchor": _safe_label(self.temporal_anchor, limit=40),
            "jurisdiction": _safe_label(self.jurisdiction, limit=40),
            "subject": _safe_label(self.subject),
            "source_binding_id": _safe_label(self.source_binding_id, limit=60),
            "fallback_posture": _safe_label(self.fallback_posture),
        }


@dataclass(frozen=True, slots=True)
class AuthorityEvidenceFit:
    requirement_id: str | None
    evidence_id: str
    candidate_exists: bool
    observed_source_class: str | None = None
    observed_source_tier: str | None = None
    context_allowed: bool = False
    satisfies_authority: bool = False
    mismatch_reason: str | None = None
    insufficiency_reason: str | None = None

    @classmethod
    def authoritative(
        cls,
        requirement_id: str,
        evidence_id: str,
        observed_source_class: str,
        *,
        observed_source_tier: str | None = None,
    ) -> "AuthorityEvidenceFit":
        return cls(
            requirement_id=requirement_id,
            evidence_id=evidence_id,
            candidate_exists=True,
            observed_source_class=observed_source_class,
            observed_source_tier=observed_source_tier,
            context_allowed=True,
            satisfies_authority=True,
        )

    @classmethod
    def lower_tier_context(
        cls,
        requirement_id: str | None,
        evidence_id: str,
        observed_source_class: str = REPUTABLE_SECONDARY,
        *,
        mismatch_reason: str = "lower_tier_context_only",
    ) -> "AuthorityEvidenceFit":
        return cls(
            requirement_id=requirement_id,
            evidence_id=evidence_id,
            candidate_exists=True,
            observed_source_class=observed_source_class,
            observed_source_tier=observed_source_class,
            context_allowed=True,
            satisfies_authority=False,
            mismatch_reason=mismatch_reason,
        )

    @classmethod
    def missing(
        cls,
        requirement_id: str,
        *,
        evidence_id: str = "missing",
        insufficiency_reason: str = "no_candidate_source_observed",
    ) -> "AuthorityEvidenceFit":
        return cls(
            requirement_id=requirement_id,
            evidence_id=evidence_id,
            candidate_exists=False,
            context_allowed=False,
            satisfies_authority=False,
            insufficiency_reason=insufficiency_reason,
        )

    def applies_to(self, requirement: AuthorityRequirement) -> bool:
        return self.requirement_id in (None, requirement.requirement_id)

    def to_projection(self) -> dict[str, Any]:
        return {
            "evidence_id": _safe_label(self.evidence_id, limit=60),
            "requirement_id": _safe_label(self.requirement_id, limit=60),
            "candidate_exists": self.candidate_exists,
            "observed_source_class": _safe_label(self.observed_source_class, limit=60),
            "observed_source_tier": _safe_label(self.observed_source_tier, limit=60),
            "context_allowed": self.context_allowed,
            "satisfies_authority": self.satisfies_authority,
            "mismatch_reason": _safe_label(self.mismatch_reason),
            "insufficiency_reason": _safe_label(self.insufficiency_reason),
        }


@dataclass(frozen=True, slots=True)
class AuthoritySatisfaction:
    requirement_id: str
    status: AuthorityStatus
    composition: AuthorityComposition = AuthorityComposition.ATOMIC
    satisfied_by_evidence_ids: tuple[str, ...] = ()
    context_evidence_ids: tuple[str, ...] = ()
    candidate_exists_count: int = 0
    authority_satisfying_count: int = 0
    mismatch_reasons: tuple[str, ...] = ()
    child_statuses: Mapping[str, AuthorityStatus] = field(default_factory=dict)
    selected_child_requirement_id: str | None = None

    @property
    def fulfilled(self) -> bool:
        return self.status is AuthorityStatus.FULFILLED

    @property
    def partial(self) -> bool:
        return self.status is AuthorityStatus.PARTIAL

    @property
    def unfulfilled(self) -> bool:
        return self.status is AuthorityStatus.UNFULFILLED

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": _safe_label(self.requirement_id),
            "status": self.status.value,
            "composition": self.composition.value,
            "satisfied_by_count": len(self.satisfied_by_evidence_ids),
            "context_evidence_count": len(self.context_evidence_ids),
            "candidate_exists_count": self.candidate_exists_count,
            "authority_satisfying_count": self.authority_satisfying_count,
            "mismatch_reasons": [_safe_label(reason) for reason in self.mismatch_reasons],
            "child_statuses": {
                _safe_label(requirement_id): status.value
                for requirement_id, status in self.child_statuses.items()
            },
            "selected_child_requirement_id": _safe_label(
                self.selected_child_requirement_id
            ),
        }


@dataclass(frozen=True, slots=True)
class AuthorityRecoveryPlan:
    missing_requirement_ids: tuple[str, ...] = ()
    target_authority_classes: tuple[str, ...] = ()
    temporal_anchors: tuple[str, ...] = ()
    jurisdiction_anchors: tuple[str, ...] = ()
    generic_recovery_intents: tuple[str, ...] = ()
    provider_agnostic: bool = True
    execution_free: bool = True

    @classmethod
    def from_state(
        cls, state: "AuthoritativeSourceObligationState"
    ) -> "AuthorityRecoveryPlan":
        missing = state.missing_authority_requirements()
        target_classes: list[str] = []
        temporal_anchors: list[str] = []
        jurisdiction_anchors: list[str] = []
        intents: list[str] = []
        for requirement in missing:
            target_classes.extend(requirement.required_authority_classes)
            if requirement.current_anchor:
                temporal_anchors.append(requirement.current_anchor)
            if requirement.temporal_anchor:
                temporal_anchors.append(requirement.temporal_anchor)
            if requirement.jurisdiction:
                jurisdiction_anchors.append(requirement.jurisdiction)
            intents.append(f"recover_authoritative_source:{requirement.requirement_type.value}")
        return cls(
            missing_requirement_ids=_merge_unique(
                [requirement.requirement_id for requirement in missing]
            ),
            target_authority_classes=_merge_unique(target_classes),
            temporal_anchors=_merge_unique(temporal_anchors),
            jurisdiction_anchors=_merge_unique(jurisdiction_anchors),
            generic_recovery_intents=_merge_unique(intents),
        )

    def to_projection(self) -> dict[str, Any]:
        return {
            "missing_requirement_ids": [
                _safe_label(item) for item in self.missing_requirement_ids
            ],
            "target_authority_classes": list(self.target_authority_classes),
            "temporal_anchors": [_safe_label(item, limit=40) for item in self.temporal_anchors],
            "jurisdiction_anchors": [
                _safe_label(item, limit=40) for item in self.jurisdiction_anchors
            ],
            "generic_recovery_intents": list(self.generic_recovery_intents),
            "provider_agnostic": self.provider_agnostic,
            "execution_free": self.execution_free,
        }


@dataclass(frozen=True, slots=True)
class AuthorityProjection:
    requirements: tuple[dict[str, Any], ...]
    satisfactions: tuple[dict[str, Any], ...]
    evidence_summary: Mapping[str, Any]
    recovery_plan: Mapping[str, Any]
    projection_version: str = "authority_projection_v1"
    trace_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_version": self.projection_version,
            "trace_safe": self.trace_safe,
            "requirements": list(self.requirements),
            "satisfactions": list(self.satisfactions),
            "evidence_summary": dict(self.evidence_summary),
            "recovery_plan": dict(self.recovery_plan),
        }


@dataclass(frozen=True, slots=True)
class AuthoritativeSourceObligationState:
    requirements: tuple[AuthorityRequirement, ...]
    evidence_fits: tuple[AuthorityEvidenceFit, ...] = ()
    satisfactions: Mapping[str, AuthoritySatisfaction] = field(default_factory=dict)

    @classmethod
    def evaluate(
        cls,
        requirements: Sequence[AuthorityRequirement],
        evidence_fits: Sequence[AuthorityEvidenceFit] | None = None,
    ) -> "AuthoritativeSourceObligationState":
        requirement_tuple = tuple(requirements)
        fit_tuple = tuple(evidence_fits or ())
        satisfactions: dict[str, AuthoritySatisfaction] = {}
        for requirement in requirement_tuple:
            _evaluate_requirement(requirement, fit_tuple, satisfactions)
        return cls(
            requirements=requirement_tuple,
            evidence_fits=fit_tuple,
            satisfactions=satisfactions,
        )

    def satisfaction_for(self, requirement_id: str) -> AuthoritySatisfaction:
        return self.satisfactions[requirement_id]

    def missing_authority_requirements(self) -> tuple[AuthorityRequirement, ...]:
        missing: list[AuthorityRequirement] = []
        for requirement in self.requirements:
            missing.extend(_missing_leaf_requirements(requirement, self.satisfactions))
        return tuple(missing)

    def recovery_plan(self) -> AuthorityRecoveryPlan:
        return AuthorityRecoveryPlan.from_state(self)

    def projection(self) -> AuthorityProjection:
        evidence_summary = _build_evidence_summary(self.evidence_fits)
        return AuthorityProjection(
            requirements=tuple(
                requirement.to_projection() for requirement in self.requirements
            ),
            satisfactions=tuple(
                satisfaction.to_projection()
                for satisfaction in self.satisfactions.values()
            ),
            evidence_summary=evidence_summary,
            recovery_plan=self.recovery_plan().to_projection(),
        )


def _evaluate_requirement(
    requirement: AuthorityRequirement,
    evidence_fits: tuple[AuthorityEvidenceFit, ...],
    satisfactions: dict[str, AuthoritySatisfaction],
) -> AuthoritySatisfaction:
    if requirement.requirement_id in satisfactions:
        return satisfactions[requirement.requirement_id]
    if requirement.composition is AuthorityComposition.ATOMIC:
        satisfaction = _evaluate_atomic_requirement(requirement, evidence_fits)
    else:
        satisfaction = _evaluate_composite_requirement(
            requirement, evidence_fits, satisfactions
        )
    satisfactions[requirement.requirement_id] = satisfaction
    return satisfaction


def _evaluate_atomic_requirement(
    requirement: AuthorityRequirement,
    evidence_fits: tuple[AuthorityEvidenceFit, ...],
) -> AuthoritySatisfaction:
    applicable = tuple(fit for fit in evidence_fits if fit.applies_to(requirement))
    candidate_exists_count = sum(1 for fit in applicable if fit.candidate_exists)
    context_ids = tuple(
        fit.evidence_id
        for fit in applicable
        if fit.context_allowed and fit.candidate_exists
    )
    mismatch_reasons = _mismatch_reasons(requirement, applicable)
    if requirement.requirement_type is AuthorityRequirementType.LOWER_TIER_CONTEXT:
        satisfying_context = tuple(
            fit.evidence_id
            for fit in applicable
            if fit.context_allowed
            and fit.candidate_exists
            and fit.observed_source_class in requirement.allowed_context_classes
        )
        status = (
            AuthorityStatus.FULFILLED
            if satisfying_context
            else AuthorityStatus.UNFULFILLED
        )
        return AuthoritySatisfaction(
            requirement_id=requirement.requirement_id,
            status=status,
            satisfied_by_evidence_ids=satisfying_context,
            context_evidence_ids=context_ids,
            candidate_exists_count=candidate_exists_count,
            authority_satisfying_count=0,
            mismatch_reasons=mismatch_reasons,
        )

    satisfying_authority = tuple(
        fit.evidence_id
        for fit in applicable
        if _fit_satisfies_requirement(requirement, fit)
    )
    if satisfying_authority:
        status = AuthorityStatus.FULFILLED
    elif candidate_exists_count or context_ids:
        status = AuthorityStatus.PARTIAL
    else:
        status = AuthorityStatus.UNFULFILLED
    return AuthoritySatisfaction(
        requirement_id=requirement.requirement_id,
        status=status,
        satisfied_by_evidence_ids=satisfying_authority,
        context_evidence_ids=context_ids,
        candidate_exists_count=candidate_exists_count,
        authority_satisfying_count=len(satisfying_authority),
        mismatch_reasons=mismatch_reasons,
    )


def _evaluate_composite_requirement(
    requirement: AuthorityRequirement,
    evidence_fits: tuple[AuthorityEvidenceFit, ...],
    satisfactions: dict[str, AuthoritySatisfaction],
) -> AuthoritySatisfaction:
    child_satisfactions = tuple(
        _evaluate_requirement(child, evidence_fits, satisfactions)
        for child in requirement.children
    )
    child_statuses = {
        child.requirement_id: child_satisfaction.status
        for child, child_satisfaction in zip(requirement.children, child_satisfactions)
    }
    selected_child = _selected_child(requirement.composition, child_satisfactions)
    if requirement.composition is AuthorityComposition.ALL:
        status = (
            AuthorityStatus.FULFILLED
            if all(child.status is AuthorityStatus.FULFILLED for child in child_satisfactions)
            else AuthorityStatus.UNFULFILLED
            if all(child.status is AuthorityStatus.UNFULFILLED for child in child_satisfactions)
            else AuthorityStatus.PARTIAL
        )
    elif requirement.composition in {
        AuthorityComposition.ANY,
        AuthorityComposition.ONE_OF,
        AuthorityComposition.FALLBACK_ORDERED,
    }:
        if any(child.status is AuthorityStatus.FULFILLED for child in child_satisfactions):
            status = AuthorityStatus.FULFILLED
        elif any(child.status is AuthorityStatus.PARTIAL for child in child_satisfactions):
            status = AuthorityStatus.PARTIAL
        else:
            status = AuthorityStatus.UNFULFILLED
    else:
        status = AuthorityStatus.UNFULFILLED
    return AuthoritySatisfaction(
        requirement_id=requirement.requirement_id,
        status=status,
        composition=requirement.composition,
        satisfied_by_evidence_ids=_merge_unique(
            [
                evidence_id
                for child in child_satisfactions
                for evidence_id in child.satisfied_by_evidence_ids
            ]
        ),
        context_evidence_ids=_merge_unique(
            [
                evidence_id
                for child in child_satisfactions
                for evidence_id in child.context_evidence_ids
            ]
        ),
        candidate_exists_count=sum(
            child.candidate_exists_count for child in child_satisfactions
        ),
        authority_satisfying_count=sum(
            child.authority_satisfying_count for child in child_satisfactions
        ),
        mismatch_reasons=_merge_unique(
            [
                reason
                for child in child_satisfactions
                for reason in child.mismatch_reasons
            ]
        ),
        child_statuses=child_statuses,
        selected_child_requirement_id=selected_child,
    )


def _fit_satisfies_requirement(
    requirement: AuthorityRequirement, fit: AuthorityEvidenceFit
) -> bool:
    if not fit.candidate_exists or not fit.satisfies_authority:
        return False
    return fit.observed_source_class in requirement.required_authority_classes


def _mismatch_reasons(
    requirement: AuthorityRequirement, evidence_fits: tuple[AuthorityEvidenceFit, ...]
) -> tuple[str, ...]:
    reasons: list[str] = []
    for fit in evidence_fits:
        if fit.mismatch_reason:
            reasons.append(fit.mismatch_reason)
        if fit.insufficiency_reason:
            reasons.append(fit.insufficiency_reason)
        if (
            fit.candidate_exists
            and fit.satisfies_authority
            and fit.observed_source_class not in requirement.required_authority_classes
            and requirement.requirement_type
            is not AuthorityRequirementType.LOWER_TIER_CONTEXT
        ):
            reasons.append("observed_source_class_not_allowed_for_requirement")
        if (
            fit.context_allowed
            and not fit.satisfies_authority
            and requirement.requirement_type
            is not AuthorityRequirementType.LOWER_TIER_CONTEXT
        ):
            reasons.append("context_allowed_but_not_authority_satisfying")
    return _merge_unique(reasons)


def _selected_child(
    composition: AuthorityComposition,
    child_satisfactions: tuple[AuthoritySatisfaction, ...],
) -> str | None:
    if composition is AuthorityComposition.ALL:
        return None
    for child in child_satisfactions:
        if child.status is AuthorityStatus.FULFILLED:
            return child.requirement_id
    for child in child_satisfactions:
        if child.status is AuthorityStatus.PARTIAL:
            return child.requirement_id
    return child_satisfactions[0].requirement_id if child_satisfactions else None


def _missing_leaf_requirements(
    requirement: AuthorityRequirement,
    satisfactions: Mapping[str, AuthoritySatisfaction],
) -> tuple[AuthorityRequirement, ...]:
    satisfaction = satisfactions[requirement.requirement_id]
    if satisfaction.status is AuthorityStatus.FULFILLED:
        return ()
    if requirement.composition is AuthorityComposition.ATOMIC:
        if requirement.required_authority_classes:
            return (requirement,)
        return ()
    if requirement.composition is AuthorityComposition.FALLBACK_ORDERED:
        for child in requirement.children:
            child_satisfaction = satisfactions[child.requirement_id]
            if child_satisfaction.status is not AuthorityStatus.FULFILLED:
                return _missing_leaf_requirements(child, satisfactions)
        return ()
    if requirement.composition is AuthorityComposition.ALL:
        missing: list[AuthorityRequirement] = []
        for child in requirement.children:
            missing.extend(_missing_leaf_requirements(child, satisfactions))
        return tuple(missing)
    if requirement.composition in {AuthorityComposition.ANY, AuthorityComposition.ONE_OF}:
        missing = []
        for child in requirement.children:
            missing.extend(_missing_leaf_requirements(child, satisfactions))
        return tuple(missing)
    return ()


def _build_evidence_summary(
    evidence_fits: tuple[AuthorityEvidenceFit, ...]
) -> dict[str, Any]:
    observed_counts: dict[str, int] = {}
    for fit in evidence_fits:
        observed_class = _safe_label(fit.observed_source_class, limit=60) or "unknown"
        observed_counts[observed_class] = observed_counts.get(observed_class, 0) + 1
    return {
        "candidate_exists_count": sum(1 for fit in evidence_fits if fit.candidate_exists),
        "context_allowed_count": sum(1 for fit in evidence_fits if fit.context_allowed),
        "authority_satisfying_claim_count": sum(
            1 for fit in evidence_fits if fit.satisfies_authority
        ),
        "observed_source_class_counts": observed_counts,
        "evidence_fit_count": len(evidence_fits),
    }


__all__ = [
    "ACADEMIC_LITERATURE",
    "LEGAL_OR_REGULATORY_TEXT",
    "LOWER_TIER_CONTEXT_CLASSES",
    "OFFICIAL_CURRENT_RULES",
    "PRIMARY_SOURCE_DOCUMENTS",
    "REPUTABLE_SECONDARY",
    "SECONDARY",
    "SOCIAL_OR_FORUM",
    "SOURCED_NUMERIC_VALUES",
    "TRUSTED_COMMUNITY",
    "AuthorityComposition",
    "AuthorityEvidenceFit",
    "AuthorityProjection",
    "AuthorityRecoveryPlan",
    "AuthorityRequirement",
    "AuthorityRequirementType",
    "AuthoritySatisfaction",
    "AuthorityStatus",
    "AuthoritativeSourceObligationState",
]
