"""Pure legal/current-primary source-fit adapter.

This module maps sanitized legal evidence facts into the authority kernel. It
does not retrieve, route providers, choose depth, rank/filter sources, alter
prompts, change citations, or affect final-answer behavior.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.authoritative_source_obligations import (
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    REPUTABLE_SECONDARY,
    SECONDARY,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
)

LEGAL_CURRENT_AUTHORITY_FIT_SCHEMA_VERSION = "legal_current_authority_fit_v1"

LEGAL_PRIMARY_SOURCE_CLASSES = frozenset(
    {
        "court_docket_or_order",
        "government_register",
        "legal_or_regulatory_text",
        "official_eu_legal_text",
        "statutory_or_regulatory_text",
    }
)
LEGAL_OFFICIAL_AGENCY_GUIDANCE_CLASSES = frozenset(
    {
        "official_agency_guidance",
        "official_agency_page",
        "official_guidance_or_faq",
        "regulator_press_release",
    }
)
LEGAL_SECONDARY_CONTEXT_CLASSES = frozenset(
    {
        "academic_legal_commentary",
        "legal_explainer",
        "reputable_news",
        "secondary_legal_analysis",
    }
)

_LOWER_TIER_VALUES = frozenset(
    {
        "academic_legal_commentary",
        "legal_explainer",
        "news",
        "reputable_news",
        "reputable_secondary",
        "secondary",
        "secondary_legal_analysis",
        "social_or_forum",
        "trusted_community",
    }
)
_CURRENTNESS_OK = frozenset(
    {
        "active",
        "current",
        "effective",
        "in_effect",
    }
)
_CURRENTNESS_STALE = frozenset(
    {
        "archived",
        "expired",
        "stale",
        "superseded",
        "withdrawn",
    }
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "legal_text",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_legal_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "text",
        "token",
    }
)
_PROTECTED_MARKERS = (
    "cache",
    "db row",
    "full_trace",
    "legal text",
    "private log",
    "provider_payload",
    "raw prompt",
    "raw_prompt",
    "raw_provider",
    "secret",
)


class LegalCurrentAuthorityKind(str, Enum):
    PRIMARY_LEGAL_OR_REGULATORY_TEXT = "primary_legal_or_regulatory_text"
    OFFICIAL_AGENCY_GUIDANCE = "official_agency_guidance"
    SECONDARY_LEGAL_CONTEXT = "secondary_legal_context"
    GENERIC_OFFICIAL_NON_LEGAL = "generic_official_non_legal"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LegalCurrentEvidenceFact:
    """Sanitized evidence metadata used by the legal/current adapter."""

    evidence_id: str
    source_class: str | None = None
    source_tier: str | None = None
    jurisdiction: str | None = None
    currentness_status: str | None = None
    temporal_anchor: str | None = None
    official_agency_guidance: bool = False

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any]) -> "LegalCurrentEvidenceFact":
        return cls(
            evidence_id=_clean_text(source.get("evidence_id") or "evidence", limit=80)
            or "evidence",
            source_class=_clean_token(
                _first_present(
                    source.get("source_class"),
                    source.get("legal_source_class"),
                    source.get("authority_class"),
                )
            ),
            source_tier=_clean_token(source.get("source_tier")),
            jurisdiction=_clean_text(source.get("jurisdiction"), limit=80),
            currentness_status=_currentness_value(source),
            temporal_anchor=_clean_text(source.get("temporal_anchor"), limit=80),
            official_agency_guidance=bool(
                source.get("official_agency_guidance")
                or source.get("agency_guidance")
            ),
        )


@dataclass(frozen=True, slots=True)
class LegalCurrentAuthorityFitResult:
    """Kernel state plus compact legal adapter projection."""

    requirement: AuthorityRequirement
    evidence_fits: tuple[AuthorityEvidenceFit, ...]
    state: AuthoritativeSourceObligationState
    evidence_projection: tuple[dict[str, Any], ...]
    schema_version: str = LEGAL_CURRENT_AUTHORITY_FIT_SCHEMA_VERSION
    trace_safe: bool = True

    def to_projection(self) -> dict[str, Any]:
        satisfaction = self.state.satisfaction_for(self.requirement.requirement_id)
        return _safe_value(
            {
                "schema_version": self.schema_version,
                "trace_safe": self.trace_safe,
                "requirement": self.requirement.to_projection(),
                "satisfaction": satisfaction.to_projection(),
                "evidence_fits": [
                    fit.to_projection() for fit in self.evidence_fits
                ],
                "legal_evidence": list(self.evidence_projection),
                "kernel_projection": self.state.projection().to_dict(),
                "protected_surface": {
                    "provider_policy_unchanged": True,
                    "provider_selection_unchanged": True,
                    "depth_policy_unchanged": True,
                    "retrieval_ranking_filtering_unchanged": True,
                    "prompt_unchanged": True,
                    "citation_behavior_unchanged": True,
                    "final_answer_behavior_unchanged": True,
                    "followup_behavior_unchanged": True,
                    "orchestrator_unchanged": True,
                },
                "runtime_wiring": False,
            }
        )


def build_legal_current_primary_authority_fit(
    *,
    requirement_id: str,
    jurisdiction: str | None,
    current_anchor: str | None,
    temporal_anchor: str | None,
    subject: str | None = None,
    fallback_posture: str | None = None,
    evidence_facts: Sequence[LegalCurrentEvidenceFact | Mapping[str, Any]] = (),
) -> LegalCurrentAuthorityFitResult:
    """Map sanitized legal/current facts to kernel requirement and evidence fit."""

    requirement = AuthorityRequirement.legal_current_primary(
        _clean_text(requirement_id, limit=80) or "legal_current_primary",
        jurisdiction=_clean_text(jurisdiction, limit=80),
        current_anchor=_clean_text(current_anchor, limit=80),
        temporal_anchor=_clean_text(temporal_anchor, limit=80),
        subject=_clean_text(subject, limit=80),
        fallback_posture=_clean_text(fallback_posture, limit=120),
    )
    facts = tuple(_coerce_fact(item) for item in evidence_facts)
    fits = tuple(_fit_for_fact(requirement, fact) for fact in facts)
    if not fits:
        fits = (AuthorityEvidenceFit.missing(requirement.requirement_id),)
    state = AuthoritativeSourceObligationState.evaluate([requirement], fits)
    return LegalCurrentAuthorityFitResult(
        requirement=requirement,
        evidence_fits=fits,
        state=state,
        evidence_projection=tuple(
            _evidence_projection(requirement, fact, fit)
            for fact, fit in zip(facts, fits, strict=False)
        ),
    )


def _fit_for_fact(
    requirement: AuthorityRequirement,
    fact: LegalCurrentEvidenceFact,
) -> AuthorityEvidenceFit:
    kind = _authority_kind(fact)
    jurisdiction_ok = _jurisdiction_matches(requirement.jurisdiction, fact.jurisdiction)
    currentness_ok = _currentness_satisfies(fact.currentness_status)

    if kind is LegalCurrentAuthorityKind.PRIMARY_LEGAL_OR_REGULATORY_TEXT:
        authority_class = LEGAL_OR_REGULATORY_TEXT
    elif kind is LegalCurrentAuthorityKind.OFFICIAL_AGENCY_GUIDANCE:
        authority_class = OFFICIAL_CURRENT_RULES
    elif kind is LegalCurrentAuthorityKind.SECONDARY_LEGAL_CONTEXT:
        return AuthorityEvidenceFit.lower_tier_context(
            requirement.requirement_id,
            fact.evidence_id,
            _context_class_for_fact(fact),
            mismatch_reason="secondary_legal_context_only",
        )
    elif kind is LegalCurrentAuthorityKind.GENERIC_OFFICIAL_NON_LEGAL:
        return AuthorityEvidenceFit(
            requirement_id=requirement.requirement_id,
            evidence_id=fact.evidence_id,
            candidate_exists=True,
            observed_source_class=OFFICIAL_CURRENT_RULES,
            observed_source_tier=fact.source_tier,
            context_allowed=False,
            satisfies_authority=False,
            mismatch_reason="generic_official_source_not_legal_current_primary",
        )
    else:
        return AuthorityEvidenceFit.missing(
            requirement.requirement_id,
            evidence_id=fact.evidence_id,
            insufficiency_reason="unknown_legal_current_primary_authority",
        )

    mismatch = _authority_mismatch_reason(
        jurisdiction_ok=jurisdiction_ok,
        currentness_ok=currentness_ok,
    )
    return AuthorityEvidenceFit(
        requirement_id=requirement.requirement_id,
        evidence_id=fact.evidence_id,
        candidate_exists=True,
        observed_source_class=authority_class,
        observed_source_tier=fact.source_tier,
        context_allowed=True,
        satisfies_authority=mismatch is None,
        mismatch_reason=mismatch,
    )


def _authority_kind(fact: LegalCurrentEvidenceFact) -> LegalCurrentAuthorityKind:
    source_class = fact.source_class or ""
    source_tier = fact.source_tier or ""
    if source_class in LEGAL_SECONDARY_CONTEXT_CLASSES or source_tier in _LOWER_TIER_VALUES:
        return LegalCurrentAuthorityKind.SECONDARY_LEGAL_CONTEXT
    if source_class in LEGAL_PRIMARY_SOURCE_CLASSES:
        return LegalCurrentAuthorityKind.PRIMARY_LEGAL_OR_REGULATORY_TEXT
    if fact.official_agency_guidance or source_class in LEGAL_OFFICIAL_AGENCY_GUIDANCE_CLASSES:
        return LegalCurrentAuthorityKind.OFFICIAL_AGENCY_GUIDANCE
    if source_class == OFFICIAL_CURRENT_RULES or source_tier == "official":
        return LegalCurrentAuthorityKind.GENERIC_OFFICIAL_NON_LEGAL
    return LegalCurrentAuthorityKind.UNKNOWN


def _authority_mismatch_reason(
    *,
    jurisdiction_ok: bool,
    currentness_ok: bool,
) -> str | None:
    if not jurisdiction_ok:
        return "jurisdiction_anchor_mismatch"
    if not currentness_ok:
        return "temporal_currentness_anchor_not_satisfied"
    return None


def _evidence_projection(
    requirement: AuthorityRequirement,
    fact: LegalCurrentEvidenceFact,
    fit: AuthorityEvidenceFit,
) -> dict[str, Any]:
    return _safe_value(
        {
            "evidence_id": fact.evidence_id,
            "requirement_id": requirement.requirement_id,
            "legal_authority_kind": _authority_kind(fact).value,
            "source_class": fact.source_class,
            "source_tier": fact.source_tier,
            "jurisdiction_anchor": requirement.jurisdiction,
            "evidence_jurisdiction": fact.jurisdiction,
            "jurisdiction_matches": _jurisdiction_matches(
                requirement.jurisdiction,
                fact.jurisdiction,
            ),
            "current_anchor": requirement.current_anchor,
            "temporal_anchor": requirement.temporal_anchor,
            "evidence_temporal_anchor": fact.temporal_anchor,
            "currentness_status": fact.currentness_status,
            "currentness_satisfies": _currentness_satisfies(
                fact.currentness_status
            ),
            "context_allowed": fit.context_allowed,
            "satisfies_authority": fit.satisfies_authority,
            "mismatch_reason": fit.mismatch_reason,
            "insufficiency_reason": fit.insufficiency_reason,
        }
    )


def _context_class_for_fact(fact: LegalCurrentEvidenceFact) -> str:
    if fact.source_class in {"legal_explainer", "secondary_legal_analysis"}:
        return SECONDARY
    return REPUTABLE_SECONDARY


def _currentness_satisfies(value: str | None) -> bool:
    status = _clean_token(value)
    if not status or status in _CURRENTNESS_STALE:
        return False
    return status in _CURRENTNESS_OK


def _jurisdiction_matches(
    required_jurisdiction: str | None,
    evidence_jurisdiction: str | None,
) -> bool:
    required = _normalize_anchor(required_jurisdiction)
    observed = _normalize_anchor(evidence_jurisdiction)
    if not required:
        return bool(observed)
    return bool(observed and required == observed)


def _coerce_fact(
    fact: LegalCurrentEvidenceFact | Mapping[str, Any],
) -> LegalCurrentEvidenceFact:
    if isinstance(fact, LegalCurrentEvidenceFact):
        return fact
    return LegalCurrentEvidenceFact.from_mapping(fact)


def _currentness_value(source: Mapping[str, Any]) -> str | None:
    if source.get("stale") is True or source.get("stale_source_warning") is True:
        return "stale"
    if source.get("is_current") is True:
        return "current"
    if source.get("is_current") is False:
        return "stale"
    return _clean_token(
        _first_present(
            source.get("currentness_status"),
            source.get("current_status"),
            source.get("legal_currentness"),
        )
    )


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return None
    if _contains_protected_marker(text):
        return "[redacted protected material]"
    return text[:limit]


def _normalize_anchor(value: str | None) -> str:
    clean = _clean_text(value, limit=80)
    if not clean:
        return ""
    return clean.casefold().replace(".", "").replace(",", "")


def _safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            if _is_sensitive_key(text_key):
                safe[text_key] = "[redacted protected material]"
            else:
                safe[text_key] = _safe_value(item)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return "[redacted protected material]" if _contains_protected_marker(value) else value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _clean_text(value, limit=120)


def _contains_protected_marker(value: str) -> bool:
    folded = value.casefold()
    return any(marker in folded for marker in _PROTECTED_MARKERS)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "LEGAL_CURRENT_AUTHORITY_FIT_SCHEMA_VERSION",
    "LEGAL_OFFICIAL_AGENCY_GUIDANCE_CLASSES",
    "LEGAL_PRIMARY_SOURCE_CLASSES",
    "LEGAL_SECONDARY_CONTEXT_CLASSES",
    "LegalCurrentAuthorityFitResult",
    "LegalCurrentAuthorityKind",
    "LegalCurrentEvidenceFact",
    "build_legal_current_primary_authority_fit",
]
