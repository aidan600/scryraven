"""Static authority-boundary helpers for AG-79B.

These helpers are deliberately behavior-preserving fixtures. They classify and
validate already-computed Controller/runtime handoff facts so tests can prove
that provider/search/depth/query selection and final assembly are subordinate to
Controller-owned posture or explicitly documented legacy/parked authority.

The module does not import provider implementations, execute search, generate
queries, rank/filter evidence, build prompts, call models, persist sessions, or
alter runtime behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class AuthorityBoundaryError(ValueError):
    """Raised when a fixture exposes a silent authority-boundary bypass."""


class AuthorityBoundaryClassification(str, Enum):
    """AG-79B authority classes for facts that may govern downstream behavior."""

    CONTROLLER_OWNED = "controller_owned"
    PROTECTED_LEGACY_BEHAVIOR = "protected_legacy_behavior"
    PARKED_HIDDEN_AUTHORITY = "parked_hidden_authority"


@dataclass(frozen=True)
class ProviderSearchAuthorityBoundary:
    """Classified provider/search/depth/query boundary facts."""

    provider_list_classification: AuthorityBoundaryClassification
    search_depth_classification: AuthorityBoundaryClassification
    query_order_classification: AuthorityBoundaryClassification
    recency_merge_classification: AuthorityBoundaryClassification
    recovery_query_dispatch_classification: AuthorityBoundaryClassification
    supplemental_search_classification: AuthorityBoundaryClassification | None = None
    controller_provider_list: tuple[str, ...] = ()
    effective_provider_list: tuple[str, ...] = ()
    controller_search_depth: str | None = None
    effective_search_depth: str | None = None
    query_sources: tuple[str, ...] = ()
    parked_hidden_authority: tuple[str, ...] = ()
    protected_legacy_behavior: tuple[str, ...] = ()

    def to_trace(self) -> dict[str, Any]:
        return {
            "provider_list_classification": self.provider_list_classification.value,
            "search_depth_classification": self.search_depth_classification.value,
            "query_order_classification": self.query_order_classification.value,
            "recency_merge_classification": self.recency_merge_classification.value,
            "recovery_query_dispatch_classification": (
                self.recovery_query_dispatch_classification.value
            ),
            "supplemental_search_classification": (
                self.supplemental_search_classification.value
                if self.supplemental_search_classification is not None
                else None
            ),
            "controller_provider_list": list(self.controller_provider_list),
            "effective_provider_list": list(self.effective_provider_list),
            "controller_search_depth": self.controller_search_depth,
            "effective_search_depth": self.effective_search_depth,
            "query_sources": list(self.query_sources),
            "parked_hidden_authority": list(self.parked_hidden_authority),
            "protected_legacy_behavior": list(self.protected_legacy_behavior),
            "behavior_preserving_static_fixture": True,
        }


@dataclass(frozen=True)
class FinalAssemblyAuthorityBoundary:
    """Classified final evidence/citation/Author assembly boundary facts."""

    final_evidence_source: AuthorityBoundaryClassification
    citation_source_list_source: AuthorityBoundaryClassification
    author_context_source: AuthorityBoundaryClassification
    insufficiency_labels_preserved: bool
    conflict_posture_labels_preserved: bool
    direct_vs_inferred_labels_preserved: bool
    inferred_conclusions_not_directly_sourced: bool
    strong_obligations_not_satisfied_by_weak_evidence: bool
    final_evidence_identity: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    citation_evidence_identity: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    ordered_sources: tuple[str, ...] = ()
    parked_hidden_authority: tuple[str, ...] = ()
    protected_legacy_behavior: tuple[str, ...] = ()

    def to_trace(self) -> dict[str, Any]:
        return {
            "final_evidence_source": self.final_evidence_source.value,
            "citation_source_list_source": self.citation_source_list_source.value,
            "author_context_source": self.author_context_source.value,
            "insufficiency_labels_preserved": self.insufficiency_labels_preserved,
            "conflict_posture_labels_preserved": self.conflict_posture_labels_preserved,
            "direct_vs_inferred_labels_preserved": self.direct_vs_inferred_labels_preserved,
            "inferred_conclusions_not_directly_sourced": (
                self.inferred_conclusions_not_directly_sourced
            ),
            "strong_obligations_not_satisfied_by_weak_evidence": (
                self.strong_obligations_not_satisfied_by_weak_evidence
            ),
            "final_evidence_identity": deepcopy(list(self.final_evidence_identity)),
            "citation_evidence_identity": deepcopy(list(self.citation_evidence_identity)),
            "ordered_sources": list(self.ordered_sources),
            "parked_hidden_authority": list(self.parked_hidden_authority),
            "protected_legacy_behavior": list(self.protected_legacy_behavior),
            "behavior_preserving_static_fixture": True,
        }


def _strings(value: Sequence[Any] | None) -> tuple[str, ...]:
    return tuple(str(item) for item in (value or ()) if str(item or "").strip())


def _classification(value: Any) -> AuthorityBoundaryClassification:
    if isinstance(value, AuthorityBoundaryClassification):
        return value
    return AuthorityBoundaryClassification(str(value))


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _evidence_identity(evidence: Sequence[Mapping[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for index, passage in enumerate(evidence or (), 1):
        rows.append(
            {
                "position": index,
                "source_id": passage.get("source_id"),
                "url": passage.get("url"),
                "title": passage.get("title"),
                "source_tier": passage.get("source_tier"),
                "source_class": passage.get("source_class"),
            }
        )
    return tuple(rows)


def _ids_and_urls(identity: Sequence[Mapping[str, Any]]) -> tuple[tuple[Any, Any], ...]:
    return tuple((row.get("source_id"), row.get("url")) for row in identity)


def _lower_tier(value: Any) -> bool:
    return str(value or "").strip().casefold() in {
        "weak",
        "secondary",
        "lower_tier",
        "low_trust",
        "community",
    }


def _strong_obligation(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    return any(token in text for token in ("official", "current", "legal", "canonical", "source-bound", "source_bound"))


def build_provider_search_authority_boundary(
    *,
    controller_provider_list: Sequence[Any] | None = None,
    effective_provider_list: Sequence[Any] | None = None,
    controller_search_depth: str | None = None,
    effective_search_depth: str | None = None,
    query_sources: Sequence[Any] | None = None,
    query_order_classification: AuthorityBoundaryClassification | str = AuthorityBoundaryClassification.CONTROLLER_OWNED,
    recency_merge_classification: AuthorityBoundaryClassification | str = AuthorityBoundaryClassification.PROTECTED_LEGACY_BEHAVIOR,
    recovery_query_dispatch_classification: AuthorityBoundaryClassification | str = AuthorityBoundaryClassification.CONTROLLER_OWNED,
    supplemental_search_classification: AuthorityBoundaryClassification | str | None = None,
    parked_hidden_authority: Sequence[Any] | None = None,
    protected_legacy_behavior: Sequence[Any] | None = None,
) -> ProviderSearchAuthorityBoundary:
    """Build a static AG-79B provider/search boundary and reject silent bypasses."""

    controller_providers = _strings(controller_provider_list)
    effective_providers = _strings(effective_provider_list)
    if controller_providers and effective_providers and controller_providers != effective_providers:
        raise AuthorityBoundaryError(
            "effective provider list differs from Controller-owned provider list"
        )
    if controller_search_depth and effective_search_depth and controller_search_depth != effective_search_depth:
        raise AuthorityBoundaryError(
            "effective search depth differs from Controller-owned retrieval/depth posture"
        )

    provider_classification = (
        AuthorityBoundaryClassification.CONTROLLER_OWNED
        if controller_providers
        else AuthorityBoundaryClassification.PROTECTED_LEGACY_BEHAVIOR
    )
    depth_classification = (
        AuthorityBoundaryClassification.CONTROLLER_OWNED
        if controller_search_depth
        else AuthorityBoundaryClassification.PROTECTED_LEGACY_BEHAVIOR
    )
    supplemental = (
        _classification(supplemental_search_classification)
        if supplemental_search_classification is not None
        else None
    )

    return ProviderSearchAuthorityBoundary(
        provider_list_classification=provider_classification,
        search_depth_classification=depth_classification,
        query_order_classification=_classification(query_order_classification),
        recency_merge_classification=_classification(recency_merge_classification),
        recovery_query_dispatch_classification=_classification(
            recovery_query_dispatch_classification
        ),
        supplemental_search_classification=supplemental,
        controller_provider_list=controller_providers,
        effective_provider_list=effective_providers,
        controller_search_depth=controller_search_depth,
        effective_search_depth=effective_search_depth,
        query_sources=_strings(query_sources),
        parked_hidden_authority=_strings(parked_hidden_authority),
        protected_legacy_behavior=_strings(protected_legacy_behavior),
    )


def build_final_assembly_authority_boundary(
    *,
    final_evidence: Sequence[Mapping[str, Any]],
    ordered_sources: Sequence[Any],
    citation_handoff: Mapping[str, Any] | None = None,
    author_handoff: Mapping[str, Any] | None = None,
    insufficiency_labels: Mapping[str, Any] | None = None,
    conflict_posture_labels: Mapping[str, Any] | None = None,
    inference_presentation_claims: Sequence[Mapping[str, Any]] | None = None,
    source_obligation_results: Sequence[Mapping[str, Any]] | None = None,
    parked_hidden_authority: Sequence[Any] | None = None,
    protected_legacy_behavior: Sequence[Any] | None = None,
) -> FinalAssemblyAuthorityBoundary:
    """Build a static AG-79B final-assembly boundary and reject laundering."""

    final_identity = _evidence_identity(final_evidence)
    citation_payload = _mapping(citation_handoff)
    citation_identity = tuple(
        _mapping(row)
        for row in citation_payload.get("final_evidence_identity", ())
    )
    if citation_identity and _ids_and_urls(citation_identity) != _ids_and_urls(final_identity):
        raise AuthorityBoundaryError(
            "citation/source-list handoff is not derived from final evidence identity"
        )

    cited_ordered_sources = tuple(citation_payload.get("ordered_sources", ()) or ())
    normalized_ordered_sources = tuple(str(line) for line in ordered_sources)
    if cited_ordered_sources and cited_ordered_sources != normalized_ordered_sources:
        raise AuthorityBoundaryError(
            "citation/source-list handoff uses a parallel ordered source list"
        )

    author_payload = _mapping(author_handoff)
    if author_payload.get("final_evidence_identity"):
        author_identity = tuple(_mapping(row) for row in author_payload["final_evidence_identity"])
        if _ids_and_urls(author_identity) != _ids_and_urls(final_identity):
            raise AuthorityBoundaryError(
                "Author handoff is not derived from final evidence identity"
            )

    inference_claims = tuple(_mapping(claim) for claim in (inference_presentation_claims or ()))
    inferred_conclusions_not_directly_sourced = True
    direct_vs_inferred_labels_preserved = bool(inference_claims) or bool(
        author_payload.get("direct_vs_inferred_labels_preserved")
    )
    for claim in inference_claims:
        label = str(claim.get("presentation_label") or "")
        directly_sourced = bool(claim.get("directly_sourced"))
        if "inferred" in label and directly_sourced:
            raise AuthorityBoundaryError(
                "inferred conclusion is presented as directly source-stated"
            )
        if not directly_sourced and claim.get("source_attribution_mode") == "direct_source_statement":
            raise AuthorityBoundaryError(
                "non-direct claim received direct-source presentation mode"
            )

    evidence_by_source_id = {row.get("source_id"): row for row in final_identity}
    for result in source_obligation_results or ():
        obligation = result.get("obligation") or result.get("source_obligation")
        if not _strong_obligation(obligation) or not bool(result.get("satisfied")):
            continue
        source_id = result.get("satisfied_by_source_id")
        evidence = evidence_by_source_id.get(source_id, {})
        if _lower_tier(evidence.get("source_tier")):
            raise AuthorityBoundaryError(
                "weak/secondary/lower-tier evidence satisfied a stronger obligation"
            )

    return FinalAssemblyAuthorityBoundary(
        final_evidence_source=AuthorityBoundaryClassification.CONTROLLER_OWNED,
        citation_source_list_source=AuthorityBoundaryClassification.CONTROLLER_OWNED,
        author_context_source=AuthorityBoundaryClassification.CONTROLLER_OWNED,
        insufficiency_labels_preserved=bool(insufficiency_labels)
        or bool(author_payload.get("insufficiency_labels_preserved")),
        conflict_posture_labels_preserved=bool(conflict_posture_labels)
        or bool(author_payload.get("conflict_posture_labels_preserved")),
        direct_vs_inferred_labels_preserved=direct_vs_inferred_labels_preserved,
        inferred_conclusions_not_directly_sourced=inferred_conclusions_not_directly_sourced,
        strong_obligations_not_satisfied_by_weak_evidence=True,
        final_evidence_identity=final_identity,
        citation_evidence_identity=citation_identity or final_identity,
        ordered_sources=normalized_ordered_sources,
        parked_hidden_authority=_strings(parked_hidden_authority),
        protected_legacy_behavior=_strings(protected_legacy_behavior),
    )


__all__ = [
    "AuthorityBoundaryClassification",
    "AuthorityBoundaryError",
    "FinalAssemblyAuthorityBoundary",
    "ProviderSearchAuthorityBoundary",
    "build_final_assembly_authority_boundary",
    "build_provider_search_authority_boundary",
]
