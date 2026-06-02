from __future__ import annotations

import pytest

from core.provider_search_final_assembly_authority_boundary import (
    AuthorityBoundaryClassification,
    AuthorityBoundaryError,
    build_final_assembly_authority_boundary,
)


def _final_evidence() -> list[dict[str, object]]:
    return [
        {
            "source_id": 1,
            "title": "Official rules",
            "url": "https://official.example/rules",
            "text": "Official current rule text.",
            "source_tier": "official",
            "source_class": "official_current_rules",
        },
        {
            "source_id": 2,
            "title": "Secondary explainer",
            "url": "https://secondary.example/explainer",
            "text": "Secondary explanation.",
            "source_tier": "secondary",
            "source_class": "secondary_analysis",
        },
    ]


def _citation_handoff() -> dict[str, object]:
    return {
        "final_evidence_identity": [
            {
                "position": 1,
                "source_id": 1,
                "url": "https://official.example/rules",
            },
            {
                "position": 2,
                "source_id": 2,
                "url": "https://secondary.example/explainer",
            },
        ],
        "ordered_sources": (
            "- [1] [Official rules](https://official.example/rules)",
            "- [2] [Secondary explainer](https://secondary.example/explainer)",
        ),
    }


def _ordered_sources() -> tuple[str, str]:
    return (
        "- [1] [Official rules](https://official.example/rules)",
        "- [2] [Secondary explainer](https://secondary.example/explainer)",
    )


def test_final_evidence_bundle_is_source_of_citation_source_list_handoff() -> None:
    boundary = build_final_assembly_authority_boundary(
        final_evidence=_final_evidence(),
        ordered_sources=_ordered_sources(),
        citation_handoff=_citation_handoff(),
    )

    assert boundary.final_evidence_source == AuthorityBoundaryClassification.CONTROLLER_OWNED
    assert boundary.citation_source_list_source == AuthorityBoundaryClassification.CONTROLLER_OWNED
    assert [(row["source_id"], row["url"]) for row in boundary.final_evidence_identity] == [
        (row["source_id"], row["url"]) for row in boundary.citation_evidence_identity
    ]
    assert boundary.ordered_sources == _ordered_sources()

    parallel = _citation_handoff()
    parallel["ordered_sources"] = ("- [9] [Parallel](https://parallel.example)",)
    with pytest.raises(AuthorityBoundaryError, match="parallel ordered source list"):
        build_final_assembly_authority_boundary(
            final_evidence=_final_evidence(),
            ordered_sources=_ordered_sources(),
            citation_handoff=parallel,
        )


def test_final_author_context_preserves_insufficiency_conflict_and_inference_labels() -> None:
    boundary = build_final_assembly_authority_boundary(
        final_evidence=_final_evidence(),
        ordered_sources=_ordered_sources(),
        citation_handoff=_citation_handoff(),
        author_handoff={
            "final_evidence_identity": list(_citation_handoff()["final_evidence_identity"]),
            "insufficiency_labels_preserved": True,
            "conflict_posture_labels_preserved": True,
            "direct_vs_inferred_labels_preserved": True,
        },
        insufficiency_labels={"evidence_sufficient": False, "label": "insufficient"},
        conflict_posture_labels={"effect_type": "source_bound_value_unresolved"},
        inference_presentation_claims=(
            {
                "presentation_label": "inferred_from_sourced_premises",
                "directly_sourced": False,
                "source_attribution_mode": "premise_or_bridge_support_only",
            },
        ),
    )

    assert boundary.author_context_source == AuthorityBoundaryClassification.CONTROLLER_OWNED
    assert boundary.insufficiency_labels_preserved is True
    assert boundary.conflict_posture_labels_preserved is True
    assert boundary.direct_vs_inferred_labels_preserved is True
    assert boundary.inferred_conclusions_not_directly_sourced is True


def test_inferred_conclusions_are_not_presented_as_directly_source_stated() -> None:
    with pytest.raises(AuthorityBoundaryError, match="inferred conclusion"):
        build_final_assembly_authority_boundary(
            final_evidence=_final_evidence(),
            ordered_sources=_ordered_sources(),
            citation_handoff=_citation_handoff(),
            inference_presentation_claims=(
                {
                    "presentation_label": "inferred_from_sourced_premises",
                    "directly_sourced": True,
                    "source_attribution_mode": "direct_source_statement",
                },
            ),
        )


def test_weak_secondary_evidence_cannot_satisfy_stronger_obligations() -> None:
    with pytest.raises(AuthorityBoundaryError, match="stronger obligation"):
        build_final_assembly_authority_boundary(
            final_evidence=_final_evidence(),
            ordered_sources=_ordered_sources(),
            citation_handoff=_citation_handoff(),
            source_obligation_results=(
                {
                    "obligation": "official_current_legal_source_bound",
                    "satisfied": True,
                    "satisfied_by_source_id": 2,
                },
            ),
        )

    boundary = build_final_assembly_authority_boundary(
        final_evidence=_final_evidence(),
        ordered_sources=_ordered_sources(),
        citation_handoff=_citation_handoff(),
        source_obligation_results=(
            {
                "obligation": "official_current_legal_source_bound",
                "satisfied": True,
                "satisfied_by_source_id": 1,
            },
        ),
    )

    assert boundary.strong_obligations_not_satisfied_by_weak_evidence is True
