from __future__ import annotations

from core.authority_custody_satisfaction import (
    CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY,
    authority_custody_satisfaction_for_source_class,
)
from core.controller_evidence_ledger import (
    LEGACY_CUSTODY_GAP_OBSERVED,
    build_controller_evidence_ledger,
)
from core.final_authority_citation_survival import (
    STATUS_CITATION_SURVIVAL_FAILED,
    STATUS_NOT_APPLICABLE,
    STATUS_SELECTED_AUTHORITY_UNCITEABLE,
    STATUS_SURVIVED,
    apply_authority_citation_survival_outcome_guard,
    build_final_authority_citation_survival_projection,
    ensure_selected_authority_evidence_visible_to_author,
)
from core.post_author_output_projection import _final_answer_source_citation_telemetry

_OFFICIAL_URL = "https://rules.example.gov/current/legal-text"
_WEAK_URL = "https://vendor.example/context"
_REQUIREMENT = "legal_or_regulatory_text"


def _official_source(**overrides: object) -> dict[str, object]:
    source = {
        "source_id": 7,
        "url": _OFFICIAL_URL,
        "title": "Current legal text",
        "text": "Synthetic current legal rule text.",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
    }
    source.update(overrides)
    return source


def _weak_source(**overrides: object) -> dict[str, object]:
    source = {
        "source_id": 2,
        "url": _WEAK_URL,
        "title": "Vendor context",
        "text": "Synthetic weak fallback context.",
        "source_tier": "secondary",
        "source_class": "secondary_analysis",
    }
    source.update(overrides)
    return source


def _selected_lifecycle(**selected_overrides: object) -> dict[str, object]:
    selected = {
        "requirement_id": _REQUIREMENT,
        "evidence_id": "7",
        "url": _OFFICIAL_URL,
        "observed_source_class": _REQUIREMENT,
        "satisfies_authority": True,
    }
    selected.update(selected_overrides)
    return {
        "source_class_recovery_used": True,
        "source_class_recovery_execution_attempted": True,
        "recovered_source_class_counts": {_REQUIREMENT: 1},
        "recovered_source_tier_counts": {"official": 1},
        "accepted_or_readable_official_or_canonical_count": 1,
        "accepted_readable_authority_evidence_count": 1,
        "final_selected_authority_evidence_count": 1,
        "final_evidence_official_or_canonical_count": 1,
        "final_citation_official_or_canonical_count": 0,
        "authority_lifecycle": {
            "citation_eligibility_state": "eligible",
            "candidate_fit": {
                "fit_state": "matched_selected",
                "selected_authority_evidence": [selected],
            },
        },
    }


def _projection_for_report(report: str, *, final_evidence=None, author_evidence=None):
    telemetry = _final_answer_source_citation_telemetry(report, {})
    return build_final_authority_citation_survival_projection(
        authority_lifecycle_trace=_selected_lifecycle(),
        final_evidence=final_evidence or [_official_source(), _weak_source()],
        author_evidence=author_evidence or [_official_source()],
        final_answer_source_ids=telemetry["final_answer_source_ids_used"],
    )


def _guarded_outcome(projection):
    return apply_authority_citation_survival_outcome_guard(
        projection=projection,
        useful_content=True,
        useful_content_reason="useful",
        response_displayable=True,
        evidence_sufficient=True,
        answer_class="answered",
        failure_card_payload={"show": False, "reason": ""},
    )


def test_ag94h_g_selected_authority_evidence_reaches_author_payload_and_final_citation() -> None:
    visibility = ensure_selected_authority_evidence_visible_to_author(
        authority_lifecycle_trace=_selected_lifecycle(),
        final_evidence=[_official_source(), _weak_source()],
        author_evidence=[_weak_source()],
    )
    projection = _projection_for_report(
        "The legal requirement is stated in the current rule [[7]]"
        f"({_OFFICIAL_URL}).",
        author_evidence=visibility.author_evidence,
    )

    assert visibility.appended_authority_evidence[0]["source_id"] == 7
    assert projection["status"] == STATUS_SURVIVED
    assert projection["final_cited_selected_authority_evidence_count"] == 1
    assert projection["final_citation_official_current_legal_count"] == 1
    assert projection["completion_blocked"] is False


def test_ag94h_g_selected_authority_evidence_unciteable_blocks_completion() -> None:
    projection = build_final_authority_citation_survival_projection(
        authority_lifecycle_trace=_selected_lifecycle(evidence_id="unciteable"),
        final_evidence=[_official_source(source_id=None)],
        author_evidence=[_official_source(source_id=None)],
        final_answer_source_ids=[],
    )
    guarded = _guarded_outcome(projection)

    assert projection["status"] == STATUS_SELECTED_AUTHORITY_UNCITEABLE
    assert projection["completion_blocked"] is True
    assert guarded["evidence_sufficient"] is False
    assert guarded["answer_class"] == "partial_answer"
    assert guarded["failure_card_payload"]["authority_citation_survival_failed"] is True


def test_ag94h_g_weak_fallback_citation_cannot_mask_missing_authority_citation() -> None:
    projection = _projection_for_report(
        "A vendor summary says the rule exists [[2]]"
        f"({_WEAK_URL}).",
    )
    guarded = _guarded_outcome(projection)

    assert projection["status"] == STATUS_CITATION_SURVIVAL_FAILED
    assert projection["missing_selected_authority_source_ids"] == ["7"]
    assert projection["weak_fallback_masking_guard_triggered"] is True
    assert projection["final_citation_official_current_legal_count"] == 0
    assert guarded["evidence_sufficient"] is False
    assert guarded["failure_card_payload"]["show"] is True


def test_ag94h_g_legacy_aggregate_counts_alone_do_not_satisfy_custody() -> None:
    projection = build_final_authority_citation_survival_projection(
        authority_lifecycle_trace={
            "accepted_readable_authority_evidence_count": 1,
            "final_selected_authority_evidence_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        },
        final_evidence=[_official_source()],
        author_evidence=[_official_source()],
        final_answer_source_ids=["7"],
    )
    satisfaction = authority_custody_satisfaction_for_source_class(
        _REQUIREMENT,
        {
            "final_selected_authority_evidence_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        },
    )

    assert projection["status"] == STATUS_NOT_APPLICABLE
    assert projection["aggregate_counts_used_as_proof"] is False
    assert satisfaction.category == CATEGORY_LEGACY_AGGREGATE_OBSERVABILITY
    assert satisfaction.authority_satisfied is False


def test_ag94h_g_controller_ledger_requires_selected_authority_citation_identity() -> None:
    passport = {
        "schema_version": "authority_candidate_passport_ag73a_v1",
        "passport_count": 1,
        "passports": [
            {
                "candidate_id": "7",
                "source_url": _OFFICIAL_URL,
                "source_tier": "official",
                "source_class": _REQUIREMENT,
                "fit_state": "matched_selected",
                "final_disposition": "promoted_final_authority_evidence",
                "satisfies_authority": True,
                "readable_text_available": True,
            }
        ],
    }
    weakly_cited = build_controller_evidence_ledger(
        runtime_trace={"active_source_class_recovery_missing_classes": [_REQUIREMENT]},
        passport_projection=passport,
        visibility_export={
            "final_selected_authority_evidence_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 0,
        },
        final_top_evidence=[_official_source()],
        final_citations=[{"citation_id": "2", "source_id": "2", "url": _WEAK_URL}],
    )
    authority_cited = build_controller_evidence_ledger(
        runtime_trace={"active_source_class_recovery_missing_classes": [_REQUIREMENT]},
        passport_projection=passport,
        visibility_export={
            "final_selected_authority_evidence_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        },
        final_top_evidence=[_official_source()],
        final_citations=[{"citation_id": "7", "source_id": "7", "url": _OFFICIAL_URL}],
    )
    gap_types = {
        event["gap_type"]
        for event in weakly_cited["events"]
        if event["event_type"] == LEGACY_CUSTODY_GAP_OBSERVED
    }

    assert (
        "final_evidence_or_citation_selected_authority_evidence_not_cited"
        in gap_types
    )
    assert weakly_cited["final_evidence_citation_custody"]["status"] == (
        "legacy_gap_observed"
    )
    assert authority_cited["final_evidence_citation_custody"]["status"] == (
        "controller_complete"
    )
