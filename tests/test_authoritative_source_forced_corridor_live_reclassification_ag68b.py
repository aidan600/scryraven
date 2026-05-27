from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor_live_classification import (
    compare_ag68b_to_ag67b_live_baseline,
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


def test_ag68b_comparison_marks_admission_and_dispatch_movement() -> None:
    comparison = compare_ag68b_to_ag67b_live_baseline(
        {
            "admission_used": "true",
            "admission_skip_reason": None,
            "source_class_recovery_execution_attempted": "true",
            "recovered_result_count": 1,
            "accepted_or_readable_official_or_canonical_count": 1,
            "recovered_candidate_selected_readable_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        }
    )

    assert comparison["ag67b_admission_used"] is False
    assert comparison["ag68b_admission_used"] is True
    assert comparison["admission_used_moved_false_to_true"] is True
    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true"
    ] is True
    assert comparison["recovered_result_count_positive"] is True
    assert comparison["official_canonical_evidence_visible"] is True
    assert comparison["official_canonical_citation_survived"] is True
    assert comparison["final_answer_used_recovered_source_safely"] == "yes"


def test_ag68b_comparison_preserves_ag67b_admission_failure_shape() -> None:
    comparison = compare_ag68b_to_ag67b_live_baseline(
        {
            "admission_used": "false",
            "admission_skip_reason": (
                "official_canonical_acquisition_path_not_visible"
            ),
            "source_class_recovery_execution_attempted": "false",
            "recovered_result_count": 0,
            "final_evidence_official_or_canonical_count": 0,
            "final_citation_official_or_canonical_count": 0,
        }
    )

    assert comparison["admission_used_moved_false_to_true"] is False
    assert comparison["admission_skip_reason_changed"] is False
    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true"
    ] is False
    assert comparison["official_canonical_evidence_visible"] is False
    assert comparison["official_canonical_citation_survived"] is False


def test_ag68b_ordinary_acquisition_still_does_not_count_as_recovery() -> None:
    comparison = compare_ag68b_to_ag67b_live_baseline(
        {
            "admission_used": "false",
            "admission_skip_reason": "existing_source_class_satisfied",
            "source_class_recovery_execution_attempted": "false",
            "recovered_result_count": 0,
            "final_evidence_official_or_canonical_count": 4,
            "final_citation_official_or_canonical_count": 2,
        }
    )

    assert comparison["admission_used_moved_false_to_true"] is False
    assert comparison[
        "source_class_recovery_execution_attempted_moved_false_to_true"
    ] is False
    assert comparison["recovered_result_count_positive"] is False
    assert comparison["official_canonical_evidence_visible"] is True
    assert comparison["official_canonical_citation_survived"] is True
    assert comparison["final_answer_used_recovered_source_safely"] == "no"


def test_ag68b_packet_hygiene_marker_is_required() -> None:
    assert live_packet_header_is_safe("LOCAL/UNTRACKED — DO NOT COMMIT\n\nAG-68B")
    assert not live_packet_header_is_safe("AG-68B\nLOCAL/UNTRACKED — DO NOT COMMIT")


def test_ag68b_static_guard_prevents_protected_surface_drift() -> None:
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
