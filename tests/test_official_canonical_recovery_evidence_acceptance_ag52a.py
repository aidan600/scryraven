from __future__ import annotations

from pathlib import Path
from typing import Any

from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.source_class_recovery import build_recovery_source_quality_diagnostics

_ROOT = Path(__file__).resolve().parents[1]
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"
_SOURCE_CLASS_PATH = _ROOT / "core" / "source_class_recovery.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _source(
    url: str,
    *,
    title: str = "Secondary analysis",
    text: str = "Secondary analysis of the topic.",
    source_tier: str = "secondary",
    score: float = 0.5,
) -> dict[str, Any]:
    return {
        "url": url,
        "title": title,
        "text": text,
        "source_tier": source_tier,
        "score": score,
    }


def _recovered(
    url: str,
    *,
    title: str = "Canonical reference documentation",
    text: str = (
        "Canonical reference documentation for database concurrency behavior "
        "and software configuration."
    ),
    source_tier: str = "unknown",
    score: float = 0.01,
) -> dict[str, Any]:
    source = _source(
        url,
        title=title,
        text=text,
        source_tier=source_tier,
        score=score,
    )
    source["_provider_role"] = "source_class_recovery"
    source["retrieval_stage"] = "source_class_recovery"
    return source


def _admitted_lifecycle(
    *,
    missing: str = "primary_source_documents",
    reason: str = "official_canonical_recovery_query_acquisition:canonical_documentation",
    admitted: bool = True,
    used: bool = True,
) -> dict[str, Any]:
    return {
        "active_source_class_recovery_used": used,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_official_canonical_admitted": admitted,
        "active_source_class_recovery_reason": reason,
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": [missing],
        "active_source_class_recovery_attempt_count": 1,
        "recovery_source_quality_status": "official_or_primary_found",
    }


def test_ag52a_admitted_canonical_documentation_candidate_is_accepted_readable() -> None:
    recovered = _recovered("https://docs.example.com/docs/current/concurrency")
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/concurrency")],
        recovered_passages=[recovered],
        lifecycle_trace=_admitted_lifecycle(),
        max_final_evidence=4,
    )

    trace = decision.to_trace_fields()
    assert final[-1]["url"] == recovered["url"]
    assert trace["recovered_visibility_used"] is True
    assert trace["recovered_visibility_source_fit_status"] == "matched_selected"
    assert trace["recovered_visibility_source_fit_candidate_count"] == 1
    assert trace["recovered_visibility_source_fit_selected_count"] == 1
    assert trace["recovered_visibility_reserved_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag52a_source_fit_candidate_replaces_weaker_secondary_at_cap() -> None:
    recovered = _recovered("https://docs.example.com/docs/current/reference")
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/high-score", score=0.99)],
        recovered_passages=[recovered],
        lifecycle_trace=_admitted_lifecycle(),
        max_final_evidence=1,
    )

    assert [source["url"] for source in final] == [recovered["url"]]
    assert decision.used is True
    assert decision.reason == "reserved_replace"
    assert decision.source_fit_candidate_count == 1


def test_ag52a_no_admitted_obligation_leaves_ordinary_acceptance_unchanged() -> None:
    recovered = _recovered("https://docs.example.com/docs/current/reference")
    existing = _source("https://analysis.example/high-score", score=0.99)
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[existing],
        recovered_passages=[recovered],
        lifecycle_trace=_admitted_lifecycle(admitted=False),
        max_final_evidence=1,
    )

    assert final == [existing]
    assert decision.used is False
    assert "reason_not_answer_contract_gap" in decision.blockers


def test_ag52a_zero_candidates_preserve_no_success_telemetry() -> None:
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/high-score")],
        recovered_passages=[],
        lifecycle_trace=_admitted_lifecycle(),
        max_final_evidence=4,
    )

    assert len(final) == 1
    assert decision.used is False
    assert decision.reason == "no_recovered_sources"
    assert decision.source_fit_status == "no_candidates"
    assert decision.source_fit_candidate_count == 0
    assert decision.source_fit_selected_count == 0


def test_ag52a_mirror_or_unofficial_docs_are_not_promoted_as_canonical() -> None:
    recovered = _recovered(
        "https://mirror.example/docs/current/concurrency",
        title="Unofficial mirror of reference documentation",
        text=(
            "Unofficial mirror and rehosted copy of canonical database "
            "documentation."
        ),
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/concurrency")],
        recovered_passages=[recovered],
        lifecycle_trace=_admitted_lifecycle(),
        max_final_evidence=4,
    )

    assert [source["url"] for source in final] == [
        "https://analysis.example/concurrency"
    ]
    assert decision.used is False
    assert decision.reason == "not_strong_source_class"
    assert decision.source_fit_status == "no_matching_source_fit"


def test_ag52a_secondary_only_recovered_candidates_do_not_fabricate_success() -> None:
    recovered = _recovered(
        "https://analysis.example/docs/current/concurrency",
        title="Analysis article about reference documentation",
        text="Secondary analysis discusses official documentation.",
        source_tier="secondary",
    )
    quality = build_recovery_source_quality_diagnostics([recovered])
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/concurrency")],
        recovered_passages=[recovered],
        lifecycle_trace={
            **_admitted_lifecycle(),
            **quality,
        },
        max_final_evidence=4,
    )

    assert final == [_source("https://analysis.example/concurrency")]
    assert quality["recovery_source_quality_status"] == "secondary_only"
    assert decision.used is False
    assert decision.reason == "secondary_only"
    assert decision.source_fit_candidate_count == 0


def test_ag52a_visibility_export_exposes_sanitized_source_fit_fields() -> None:
    recovered = _recovered("https://docs.example.com/docs/current/concurrency")
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/concurrency")],
        recovered_passages=[recovered],
        lifecycle_trace=_admitted_lifecycle(),
        max_final_evidence=4,
    )
    export = build_official_canonical_recovery_visibility_export(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_result_count": 1,
            "recovered_source_class_counts": {"primary_source_documents": 1},
            **decision.to_trace_fields(),
        }
    )

    assert export["candidate_official_or_canonical_count"] == 1
    assert export["accepted_or_readable_official_or_canonical_count"] == 1
    assert export["recovered_candidate_source_fit_status"] == "matched_selected"
    assert export["recovered_candidate_source_fit_count"] == 1
    assert export["recovered_candidate_selected_readable_count"] == 1


def test_ag52a_does_not_touch_closed_protected_surfaces_or_source_specific_rules() -> None:
    visibility_source = _VISIBILITY_PATH.read_text(encoding="utf-8").casefold()
    source_class_source = _SOURCE_CLASS_PATH.read_text(encoding="utf-8").casefold()
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()

    forbidden_terms = {
        "postgresql",
        "postgresql.org",
        "explain how postgresql mvcc works",
        "author_prompt",
        "select_providers",
        "choose_supplemental_search_depth",
    }
    assert all(term not in visibility_source for term in forbidden_terms)
    assert all(term not in source_class_source for term in forbidden_terms)
    assert "apply_recovered_evidence_visibility_boundary" in orchestrator_source
