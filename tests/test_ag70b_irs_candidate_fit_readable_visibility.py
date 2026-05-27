from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_forced_corridor_classification import (
    classify_authority_lifecycle_forced_corridor,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"
_LIFECYCLE_VISIBILITY_PATH = (
    _ROOT / "core" / "authority_lifecycle_candidate_visibility.py"
)
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=("official current agency source for 2026 rate",),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "official_canonical_candidate_visible": False,
            "source_survival_final_evidence_official_or_canonical_count": 0,
            "source_survival_final_citation_official_or_canonical_count": 0,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": ["official_current_rules"],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    return trace


def _official_source(
    url: str = "https://agency.example/current-2026-rate",
) -> dict[str, Any]:
    return {
        "title": "Official current 2026 rate",
        "url": url,
        "text": "Official current agency guidance for the 2026 rate.",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }


def _secondary_source(
    url: str = "https://analysis.example/current-2026-rate",
) -> dict[str, Any]:
    return {
        "title": "Secondary 2026 rate analysis",
        "url": url,
        "text": "Secondary discussion of the 2026 rate.",
        "source_tier": "secondary",
        "source_class": "secondary_only",
    }


def _run_visibility(
    *,
    final: list[dict[str, Any]],
    recovered: list[dict[str, Any]],
    max_final_evidence: int = 4,
    trace: dict[str, Any] | None = None,
) -> tuple[list[Any], Any, dict[str, Any], dict[str, Any]]:
    lifecycle = trace or _trace(result_count=len(recovered))
    final_evidence, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=final,
        recovered_passages=recovered,
        lifecycle_trace=lifecycle,
        max_final_evidence=max_final_evidence,
    )
    lifecycle.update(decision.to_trace_fields())
    export = build_official_canonical_recovery_visibility_export(lifecycle)
    return final_evidence, decision, lifecycle, export


def test_ag70b_counted_but_not_readable_candidate_is_structured_absent() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, decision, lifecycle, export = _run_visibility(
        final=[_secondary_source(shared_url)],
        recovered=[_official_source(shared_url)],
    )

    assert export["returned_or_evaluated_official_or_canonical_count"] > 0
    assert export["candidate_official_or_canonical_count"] > 0
    assert export["accepted_or_readable_official_or_canonical_count"] == 0
    assert export["accepted_readable_authority_evidence_count"] == 0
    assert export["official_canonical_candidate_visible"] is False
    assert lifecycle["recovered_visibility_source_fit_status"] == (
        "no_matching_source_fit"
    )
    assert decision.source_fit_selected_count == 0
    assert lifecycle["authority_lifecycle"]["final_evidence_state"] == (
        "explained_absent"
    )
    assert export["final_evidence_official_or_canonical_count"] == 0
    assert export["final_citation_official_or_canonical_count"] == 0


def test_ag70b_already_visible_lower_tier_duplicate_is_precise_rejection() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, _decision, lifecycle, export = _run_visibility(
        final=[_secondary_source(shared_url)],
        recovered=[_official_source(shared_url)],
    )
    rejection = lifecycle["authority_lifecycle"]["candidate_fit"][
        "structured_rejections"
    ][0]

    assert rejection["rejection_reason"] == (
        "already_visible_duplicate_lower_tier_context"
    )
    assert rejection["lower_tier_context_allowed"] is True
    assert export["recovered_candidate_rejection_reasons"] == [
        "already_visible_duplicate_lower_tier_context"
    ]
    assert export["candidate_official_or_canonical_count_basis"] == (
        "authority_lifecycle_rejected_candidate_fit"
    )
    assert export["accepted_readable_authority_evidence_count"] == 0


def test_ag70b_rejected_lifecycle_count_is_not_accepted_readable_evidence() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, _decision, _lifecycle, export = _run_visibility(
        final=[_secondary_source(shared_url)],
        recovered=[_official_source(shared_url)],
    )

    assert export["returned_or_evaluated_official_or_canonical_count"] == 1
    assert export["rejected_official_or_canonical_candidate_count"] == 1
    assert export["accepted_or_readable_official_or_canonical_count"] == 0
    assert export["accepted_readable_authority_evidence_count"] == 0
    assert export["final_selected_authority_evidence_count"] == 0


def test_ag70b_valid_authority_blocked_by_capacity_is_matched_not_selected() -> None:
    trace = _trace()
    _final, decision, lifecycle, export = _run_visibility(
        final=[_official_source("https://agency.example/existing-protected")],
        recovered=[_official_source("https://agency.example/new-current-rate")],
        max_final_evidence=1,
        trace=trace,
    )
    packet = classify_authority_lifecycle_forced_corridor(
        lifecycle,
        corridor_name="ag70b_capacity_blocked_valid_authority",
    )

    assert decision.source_fit_status == "matched_not_selected"
    assert lifecycle["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "matched_not_selected"
    )
    assert export["rejected_official_or_canonical_candidate_count"] == 0
    assert export["returned_or_evaluated_official_or_canonical_count"] == 1
    assert export["accepted_readable_authority_evidence_count"] == 0
    assert packet["remaining_failure_layer"] == "final_evidence_visibility_layer"
    assert packet["candidate_fit_state"] != "no_matching_source_fit"


def test_ag70b_citation_eligibility_remains_explained_ineligible_when_absent() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, _decision, lifecycle, export = _run_visibility(
        final=[_secondary_source(shared_url)],
        recovered=[_official_source(shared_url)],
    )

    assert lifecycle["authority_lifecycle"]["final_evidence_state"] == (
        "explained_absent"
    )
    assert lifecycle["authority_lifecycle"]["citation_eligibility_state"] == (
        "explained_ineligible"
    )
    assert export["citation_eligibility_state"] == "explained_ineligible"


def test_ag70b_legacy_export_fields_project_lifecycle_not_independent_truth() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, _decision, lifecycle, export = _run_visibility(
        final=[_secondary_source(shared_url)],
        recovered=[_official_source(shared_url)],
    )
    lifecycle["candidate_official_or_canonical_count"] = 99
    projected = build_official_canonical_recovery_visibility_export(lifecycle)

    assert export["candidate_official_or_canonical_count"] == (
        lifecycle["recovered_visibility_source_fit_candidate_count"]
    )
    assert projected["candidate_official_or_canonical_count"] != 99
    assert projected["accepted_readable_authority_evidence_count"] == (
        lifecycle[
            "recovered_visibility_accepted_readable_authority_evidence_count"
        ]
    )
    assert projected["final_selected_authority_evidence_count"] == (
        lifecycle["recovered_visibility_final_selected_authority_evidence_count"]
    )


def test_ag70b_already_visible_authority_satisfying_is_distinct_from_lower_tier() -> None:
    shared_url = "https://agency.example/current-2026-rate"
    _final, _decision, lifecycle, export = _run_visibility(
        final=[_official_source(shared_url)],
        recovered=[_official_source(shared_url)],
        max_final_evidence=1,
    )

    assert lifecycle["recovered_visibility_source_fit_rejection_reasons"] == [
        "already_visible_authority_satisfying"
    ]
    assert export["recovered_candidate_rejection_reasons"] == [
        "already_visible_authority_satisfying"
    ]


def test_ag70b_ag70a_ssa_admission_query_surfacing_remains_untouched() -> None:
    ag70a_source = (
        _ROOT
        / "tests"
        / "test_ag70a_live_failure_split_diagnosis_ssa_admission.py"
    ).read_text(encoding="utf-8")
    visibility_source = _LIFECYCLE_VISIBILITY_PATH.read_text(encoding="utf-8")

    assert "test_ssa_shaped_required_recovery_promotes_upstream_query_candidate" in (
        ag70a_source
    )
    assert "answer_contract_recovery_query_candidates" not in visibility_source
    assert "official_canonical_recovery_query_acquisition" not in visibility_source


def test_ag70b_static_guard_keeps_protected_surfaces_closed() -> None:
    forbidden_imports = {
        "openai",
        "requests",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.source_classifier",
        "core.author",
        "core.economist",
        "core.final_answer",
    }
    for path in (_VISIBILITY_PATH, _LIFECYCLE_VISIBILITY_PATH, _EXPORT_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert imported.isdisjoint(forbidden_imports)


def test_ag70b_no_broad_pipeline_or_source_specific_logic_added() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    visibility_source = _VISIBILITY_PATH.read_text(encoding="utf-8").casefold()
    lifecycle_source = _LIFECYCLE_VISIBILITY_PATH.read_text(
        encoding="utf-8"
    ).casefold()

    assert "ag70b" not in pipeline_source
    assert "standard mileage" not in visibility_source
    assert "standard mileage" not in lifecycle_source
    assert "irs.gov" not in visibility_source
    assert "irs.gov" not in lifecycle_source
