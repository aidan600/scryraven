"""Offline builders for canonical Component Analyst evidence-set fixtures."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.component_analyst_evidence_set import (
    build_component_analyst_evidence_set,
)


def component_analyst_evidence_set_fixture(
    *evidence_members: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt concise offline fixture evidence into exact canonical members."""

    sources: list[dict[str, Any]] = []
    for index, raw_evidence in enumerate(evidence_members, start=1):
        evidence = dict(raw_evidence)
        evidence_ref_id = str(evidence.get("evidence_ref_id") or f"evidence:{index}")
        bounded_text = str(evidence.get("bounded_text") or "")
        if not bounded_text:
            raise ValueError("offline component evidence fixture requires bounded_text")
        sources.append(
            {
                "evidence_ref_id": evidence_ref_id,
                "passage": {
                    "candidate_id": evidence_ref_id,
                    "title": evidence.get("source_title"),
                    "url": evidence.get("source_url"),
                    "text": bounded_text,
                    "source_class": evidence.get("source_class"),
                    "source_tier": evidence.get("source_tier"),
                    "currentness_signal": (
                        evidence.get("currentness")
                        or evidence.get("currentness_signal")
                    ),
                    "fact_disposition": evidence.get("fact_disposition"),
                    "readable_status": (
                        evidence.get("readability_posture")
                        or evidence.get("readable_status")
                    ),
                    "conflict_posture": evidence.get("conflict_posture"),
                    "contradictory": evidence.get("contradictory"),
                    "canonical_currency_unit": evidence.get(
                        "canonical_currency_unit"
                    ),
                },
                "candidate_record": {
                    "candidate_id": evidence_ref_id,
                    "source_class": evidence.get("source_class"),
                    "source_tier": evidence.get("source_tier"),
                    "currentness_signal": (
                        evidence.get("currentness")
                        or evidence.get("currentness_signal")
                    ),
                    "fact_disposition": evidence.get("fact_disposition"),
                    "readable_status": (
                        evidence.get("readability_posture")
                        or evidence.get("readable_status")
                    ),
                    "conflict_posture": evidence.get("conflict_posture"),
                    "contradictory": evidence.get("contradictory"),
                    "canonical_currency_unit": evidence.get(
                        "canonical_currency_unit"
                    ),
                },
            }
        )
    return build_component_analyst_evidence_set(sources)


def component_analyst_evidence_sets_fixture(
    members_by_component: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        str(component_id): component_analyst_evidence_set_fixture(*members)
        for component_id, members in members_by_component.items()
    }
