from __future__ import annotations

from typing import Any

from core.evidence_ledger import (
    EvidenceLedger,
    SourceRequirementStatus,
    build_evidence_ledger_observation_from_runtime,
)
from core.source_class_recovery import build_source_class_recovery_recommendation


def _requirement(
    source_class: str,
    *,
    requirement_id: str | None = None,
    requirement_kind: str = "official_current",
    required_source_tier: str | None = None,
    required_currentness: str | None = "current",
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id
        or f"official_current_source:{source_class}",
        "requirement_kind": requirement_kind,
        "origin_ref": "ag93e2_fixture",
        "required_source_class": source_class,
        "required_source_tier": required_source_tier,
        "required_currentness": required_currentness,
    }


def _projection_for_final_source(
    requirement: dict[str, Any],
    final_source: dict[str, Any] | None,
) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": "ag93e2-contract",
            "observation_source": "run_authority_contract",
            "requirements": [requirement],
        }
    )
    if final_source is not None:
        ledger.reduce_observation(
            build_evidence_ledger_observation_from_runtime(
                observation_id="ag93e2-final",
                observation_source="final_evidence_bundle",
                final_top_evidence=[final_source],
                final_evidence_selected=True,
            ).to_dict()
        )
    return ledger.to_projection().to_dict()


def _status(projection: dict[str, Any], requirement_id: str) -> str:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement["status"]
    raise AssertionError(f"missing requirement {requirement_id}")


def _source(
    *,
    source_id: str,
    url: str,
    source_tier: str,
    source_class: str,
    currentness_signal: str = "current",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "title": source_id.replace("-", " ").title(),
        "url": url,
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness_signal,
        "readability_status": "readable",
        "retrieval_stage": "source_class_recovery",
    }


def test_ag93e2_real_id_style_official_current_candidate_satisfies_ledger() -> None:
    requirement = _requirement(
        "official_current_rules",
        requirement_id="official_current_source:travel_id_rule",
        required_source_tier="official",
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="travel-id-official-current",
            url="https://example-agency.gov/current/travel-id-rule",
            source_tier="official",
            source_class="official_current_rules",
        ),
    )

    assert _status(projection, "official_current_source:travel_id_rule") == (
        SourceRequirementStatus.SATISFIED.value
    )


def test_ag93e2_different_federal_current_rule_corridor_satisfies() -> None:
    requirement = _requirement(
        "current_primary_or_official",
        requirement_id="official_current_source:federal_device_rule",
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="federal-device-rule",
            url="https://example-commission.gov/rules/current-device-rule",
            source_tier="official",
            source_class="official_current_rules",
        ),
    )

    assert _status(projection, "official_current_source:federal_device_rule") == (
        SourceRequirementStatus.SATISFIED.value
    )


def test_ag93e2_irs_style_numeric_source_remains_source_bound() -> None:
    requirement = _requirement(
        "sourced_numeric_values",
        requirement_id="source_bound:irs_numeric_rate",
        requirement_kind="source_bound",
        required_currentness=None,
    )
    official_rule_projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="irs-official-rule-not-numeric-bound",
            url="https://irs.gov/current-rule",
            source_tier="official",
            source_class="official_current_rules",
        ),
    )
    numeric_projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="irs-source-bound-rate",
            url="https://irs.gov/numeric-rate-table",
            source_tier="official",
            source_class="sourced_numeric_values",
        ),
    )

    assert _status(official_rule_projection, "source_bound:irs_numeric_rate") == (
        SourceRequirementStatus.UNSATISFIED.value
    )
    assert _status(numeric_projection, "source_bound:irs_numeric_rate") == (
        SourceRequirementStatus.SATISFIED.value
    )


def test_ag93e2_uscis_style_legal_primary_remains_primary_current_bound() -> None:
    requirement = _requirement(
        "legal_or_regulatory_text",
        requirement_id="legal_current:immigration_eligibility",
        requirement_kind="legal",
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="immigration-regulatory-text",
            url="https://uscis.example.gov/policy/current-eligibility",
            source_tier="official",
            source_class="legal_or_regulatory_text",
        ),
    )

    assert _status(projection, "legal_current:immigration_eligibility") == (
        SourceRequirementStatus.SATISFIED.value
    )


def test_ag93e2_canonical_technical_docs_are_not_government_only() -> None:
    requirement = _requirement(
        "primary_source_documents",
        requirement_id="canonical_docs:python_reference",
        requirement_kind="canonical",
        required_currentness=None,
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="python-reference-doc",
            url="https://docs.python.org/3/reference/",
            source_tier="canonical",
            source_class="primary_source_documents",
        ),
    )

    assert _status(projection, "canonical_docs:python_reference") == (
        SourceRequirementStatus.SATISFIED.value
    )


def test_ag93e2_ordinary_explainer_does_not_trigger_official_recovery() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="Explain how sourdough starters work.",
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="sourdough starters",
        primary_entity="sourdough starter",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"explainer.example": 2},
        top_source_domains=[{"domain": "explainer.example", "count": 2}],
        official_evidence_found=False,
    )

    assert recommendation["source_class_recovery_recommended"] is False
    assert recommendation["missing_expected_source_classes"] == []
    assert recommendation["source_class_recovery_query_count"] == 0


def test_ag93e2_secondary_news_context_cannot_satisfy_official_current() -> None:
    requirement = _requirement(
        "official_current_rules",
        requirement_id="official_current_source:current_rule",
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="news-context",
            url="https://news.example/current-rule-story",
            source_tier="secondary",
            source_class="reputable_secondary",
        ),
    )

    assert _status(projection, "official_current_source:current_rule") == (
        SourceRequirementStatus.UNSATISFIED.value
    )


def test_ag93e2_stale_official_page_cannot_satisfy_current_obligation() -> None:
    requirement = _requirement(
        "official_current_rules",
        requirement_id="official_current_source:current_rule",
    )
    projection = _projection_for_final_source(
        requirement,
        _source(
            source_id="stale-official",
            url="https://agency.gov/archive/rule",
            source_tier="official",
            source_class="official_current_rules",
            currentness_signal="stale",
        ),
    )

    assert _status(projection, "official_current_source:current_rule") == (
        SourceRequirementStatus.UNSATISFIED.value
    )


def test_ag93e2_unavailable_official_authority_stays_insufficient_and_bounded() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="What is the current official eligibility rule for a federal benefit?",
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="official_current_status",
        core_topic="current official eligibility rule",
        primary_entity="Federal Benefit",
        anchor_packet=None,
        source_tier_counts={"secondary": 3},
        source_domain_counts={"news.example": 3},
        top_source_domains=[{"domain": "news.example", "count": 3}],
        official_evidence_found=False,
    )
    requirement = _requirement(
        "official_current_rules",
        requirement_id="official_current_source:federal_benefit",
    )
    projection = _projection_for_final_source(requirement, None)

    assert recommendation["source_class_recovery_recommended"] is True
    assert recommendation["source_class_recovery_query_count"] <= 3
    assert _status(projection, "official_current_source:federal_benefit") == (
        SourceRequirementStatus.UNSATISFIED.value
    )
