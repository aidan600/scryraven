from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor_live_classification import (
    compare_ag68d_to_prior_live_baselines,
    live_packet_header_is_safe,
)

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = (
    _ROOT
    / "tests"
    / "helpers"
    / "authoritative_source_forced_corridor_live_classification.py"
)
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def test_ag68d_comparison_marks_dispatch_movement_after_ag68c() -> None:
    comparison = compare_ag68d_to_prior_live_baselines(
        {
            "admission_used": "true",
            "source_class_recovery_used": "true",
            "source_class_recovery_execution_attempted": "true",
            "recovered_result_count": 2,
            "candidate_return_status": "candidates_returned",
            "accepted_or_readable_official_or_canonical_count": 1,
            "recovered_candidate_selected_readable_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
            "next_failure_layer": "recovery_path_succeeded",
        }
    )

    assert comparison["ag67b_admission_used"] is False
    assert comparison["ag68b_admission_used"] is True
    assert comparison["admission_used_remained_true_after_ag68a"] is True
    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true_after_ag68c"
    ] is True
    assert comparison["source_class_recovery_used_moved_false_to_true"] is True
    assert comparison["recovered_result_count_positive"] is True
    assert comparison["candidate_acquisition_return_visibility"] == (
        "candidates_returned"
    )
    assert comparison[
        "candidate_acquisition_return_visibility_moved_from_not_attempted"
    ] is True
    assert comparison["official_canonical_evidence_accepted_or_visible"] is True
    assert comparison["official_canonical_citation_survived"] is True
    assert comparison["final_answer_used_recovered_source_safely"] == "yes"
    assert comparison["provider_search_review_justified"] is False


def test_ag68d_dispatch_is_required_before_provider_review_is_justified() -> None:
    comparison = compare_ag68d_to_prior_live_baselines(
        {
            "admission_used": "true",
            "source_class_recovery_used": "false",
            "source_class_recovery_execution_attempted": "false",
            "recovered_result_count": 0,
            "candidate_return_status": "not_attempted",
            "final_evidence_official_or_canonical_count": 0,
            "final_citation_official_or_canonical_count": 0,
            "next_failure_layer": "execution_not_attempted",
        }
    )

    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true_after_ag68c"
    ] is False
    assert comparison["candidate_acquisition_return_visibility"] == "not_attempted"
    assert comparison[
        "candidate_acquisition_return_visibility_moved_from_not_attempted"
    ] is False
    assert comparison["provider_search_review_justified"] is False
    assert comparison["next_failure_layer"] == "execution_not_attempted"


def test_ag68d_provider_review_opens_only_after_executed_zero_candidate_dispatch() -> None:
    comparison = compare_ag68d_to_prior_live_baselines(
        {
            "admission_used": "true",
            "source_class_recovery_used": "true",
            "source_class_recovery_execution_attempted": "true",
            "recovered_result_count": 0,
            "candidate_return_status": "zero_candidates",
            "final_evidence_official_or_canonical_count": 0,
            "final_citation_official_or_canonical_count": 0,
            "next_failure_layer": "execution_attempted_zero_candidates",
        }
    )

    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true_after_ag68c"
    ] is True
    assert comparison["recovered_result_count_positive"] is False
    assert comparison["candidate_acquisition_return_visibility"] == "zero_candidates"
    assert comparison["provider_search_review_justified"] is True


def test_ag68d_ordinary_acquisition_remains_separate_from_recovery_success() -> None:
    comparison = compare_ag68d_to_prior_live_baselines(
        {
            "admission_used": "false",
            "admission_skip_reason": "existing_source_class_satisfied",
            "source_class_recovery_used": "false",
            "source_class_recovery_execution_attempted": "false",
            "recovered_result_count": 0,
            "final_evidence_official_or_canonical_count": 3,
            "final_citation_official_or_canonical_count": 1,
            "next_failure_layer": "ordinary_acquisition_only",
        }
    )

    assert comparison["admission_used_remained_true_after_ag68a"] is False
    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true_after_ag68c"
    ] is False
    assert comparison["ordinary_acquisition_counted_as_recovery_success"] is False
    assert comparison["official_canonical_evidence_accepted_or_visible"] is True
    assert comparison["official_canonical_citation_survived"] is True
    assert comparison["final_answer_used_recovered_source_safely"] == "no"
    assert comparison["provider_search_review_justified"] is False


def test_ag68d_packet_hygiene_marker_is_required() -> None:
    assert live_packet_header_is_safe("LOCAL/UNTRACKED — DO NOT COMMIT\n\nAG-68D")
    assert not live_packet_header_is_safe("AG-68D\nLOCAL/UNTRACKED — DO NOT COMMIT")


def test_ag68d_static_guard_prevents_protected_surface_drift() -> None:
    tree = ast.parse(_HELPER_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imported.isdisjoint(
        {
            "core.pipeline",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.source_classifier",
            "openai",
            "requests",
        }
    )

    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in helper_source

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "authoritative_source_forced_corridor_live_reclassification" not in (
        pipeline_source
    )
