from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.official_numeric_source_grounding import (
    ANSWER_CAVEATED_MISSING_EVIDENCE,
    AUTHOR_SYNTHESIS_LANE,
    CITATION_SOURCE_FIT_LANE,
    ECONOMIST_CORRECT_DISTORTED_DOWNSTREAM,
    ECONOMIST_ELIGIBLE_NOT_INVOKED,
    ECONOMIST_HANDOFF_LANE,
    ECONOMIST_INVOCATION_LANE,
    ECONOMIST_INVOKED_WEAK_EVIDENCE,
    FINAL_SYNTHESIS_DISTORTION,
    NO_ACTION_LANE,
    NO_BOTTLENECK_DETECTED,
    NUMERIC_EXTRACTION_LANE,
    NUMERIC_VALUE_NOT_SOURCE_BOUND,
    OFFICIAL_SOURCE_ACQUIRED_NOT_ACCEPTED,
    OFFICIAL_SOURCE_NOT_ACQUIRED,
    OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE,
    OFFICIAL_SOURCE_NOT_REQUIRED,
    OFFICIAL_SOURCE_VISIBLE_NOT_CITED,
    SOURCE_ACQUISITION_SURVIVAL_LANE,
    SOURCE_NEED_NOT_DETECTED,
    WRONG_NUMBER_EXTRACTED,
    OfficialNumericGroundingDiagnostic,
    classify_official_numeric_grounding,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_numeric_source_grounding.py"


def _classify(**overrides: object) -> tuple[str, str, bool]:
    base = {
        "question_type": "government_program_amount",
        "official_source_required": True,
        "source_need_detected": True,
        "official_source_acquired": True,
        "official_source_accepted": True,
        "official_source_in_final_evidence": True,
        "official_source_cited": True,
        "numeric_values_extracted": True,
        "numeric_values_source_bound": True,
        "economist_eligible": False,
        "economist_ran": False,
        "economist_source_bound_values_present": False,
        "final_answer_value_mismatch": False,
        "caveat_present": False,
    }
    base.update(overrides)
    result = classify_official_numeric_grounding(
        OfficialNumericGroundingDiagnostic.from_mapping(base)
    )
    return result.bottleneck_class, result.next_recommended_lane, result.behavior_changed


@pytest.mark.parametrize(
    ("overrides", "bottleneck", "lane"),
    [
        (
            {"official_source_required": False},
            OFFICIAL_SOURCE_NOT_REQUIRED,
            NO_ACTION_LANE,
        ),
        (
            {"source_need_detected": False},
            SOURCE_NEED_NOT_DETECTED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"official_source_acquired": False},
            OFFICIAL_SOURCE_NOT_ACQUIRED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"official_source_accepted": False},
            OFFICIAL_SOURCE_ACQUIRED_NOT_ACCEPTED,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"official_source_in_final_evidence": False},
            OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"official_source_cited": False},
            OFFICIAL_SOURCE_VISIBLE_NOT_CITED,
            CITATION_SOURCE_FIT_LANE,
        ),
        (
            {"numeric_values_extracted": False},
            WRONG_NUMBER_EXTRACTED,
            NUMERIC_EXTRACTION_LANE,
        ),
        (
            {"numeric_values_source_bound": False},
            NUMERIC_VALUE_NOT_SOURCE_BOUND,
            NUMERIC_EXTRACTION_LANE,
        ),
        (
            {"final_answer_value_mismatch": True},
            FINAL_SYNTHESIS_DISTORTION,
            AUTHOR_SYNTHESIS_LANE,
        ),
    ],
)
def test_ag48a_classifies_official_source_and_value_layers(
    overrides: dict[str, object],
    bottleneck: str,
    lane: str,
) -> None:
    assert _classify(**overrides) == (bottleneck, lane, False)


def test_ag48a_safe_caveat_for_missing_source_is_not_hallucination_failure() -> None:
    bottleneck, lane, behavior_changed = _classify(
        official_source_acquired=False,
        numeric_values_extracted=False,
        numeric_values_source_bound=False,
        caveat_present=True,
    )

    assert bottleneck == ANSWER_CAVEATED_MISSING_EVIDENCE
    assert lane == SOURCE_ACQUISITION_SURVIVAL_LANE
    assert behavior_changed is False


def test_ag48a_roth_style_case_maps_to_numeric_extraction_not_dispatch() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="tax_retirement_threshold",
        numeric_values_extracted=False,
        numeric_values_source_bound=False,
        final_answer_value_mismatch=True,
    )

    assert bottleneck == WRONG_NUMBER_EXTRACTED
    assert lane == NUMERIC_EXTRACTION_LANE
    assert behavior_changed is False


def test_ag48a_ssa_style_caveated_case_maps_to_source_survival() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="government_program_amount",
        official_source_acquired=True,
        official_source_accepted=True,
        official_source_in_final_evidence=False,
        official_source_cited=False,
        numeric_values_extracted=False,
        numeric_values_source_bound=False,
        caveat_present=True,
    )

    assert bottleneck == OFFICIAL_SOURCE_NOT_IN_FINAL_EVIDENCE
    assert lane == SOURCE_ACQUISITION_SURVIVAL_LANE
    assert behavior_changed is False


def test_ag48a_nasa_status_visible_uncited_maps_to_source_fit() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="current_mission_status",
        official_source_in_final_evidence=True,
        official_source_cited=False,
        numeric_values_extracted=False,
        numeric_values_source_bound=False,
    )

    assert bottleneck == OFFICIAL_SOURCE_VISIBLE_NOT_CITED
    assert lane == CITATION_SOURCE_FIT_LANE
    assert behavior_changed is False


def test_ag48a_economist_eligible_but_skipped_maps_to_preflight_lane() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="cost_tco_comparison",
        economist_eligible=True,
        economist_ran=False,
    )

    assert bottleneck == ECONOMIST_ELIGIBLE_NOT_INVOKED
    assert lane == ECONOMIST_INVOCATION_LANE
    assert behavior_changed is False


def test_ag48a_economist_runs_without_source_bound_values_maps_to_handoff_lane() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="cost_tco_comparison",
        economist_eligible=True,
        economist_ran=True,
        economist_source_bound_values_present=False,
    )

    assert bottleneck == ECONOMIST_INVOKED_WEAK_EVIDENCE
    assert lane == ECONOMIST_HANDOFF_LANE
    assert behavior_changed is False


def test_ag48a_economist_values_distorted_downstream_maps_to_author_lane() -> None:
    bottleneck, lane, behavior_changed = _classify(
        question_type="cost_tco_comparison",
        economist_eligible=True,
        economist_ran=True,
        economist_source_bound_values_present=True,
        final_answer_value_mismatch=True,
    )

    assert bottleneck == ECONOMIST_CORRECT_DISTORTED_DOWNSTREAM
    assert lane == AUTHOR_SYNTHESIS_LANE
    assert behavior_changed is False


def test_ag48a_clean_sanitized_case_has_no_bottleneck() -> None:
    bottleneck, lane, behavior_changed = _classify()

    assert bottleneck == NO_BOTTLENECK_DETECTED
    assert lane == NO_ACTION_LANE
    assert behavior_changed is False


def test_ag48a_static_guard_has_no_runtime_or_provider_imports() -> None:
    forbidden_modules = {
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.provider",
        "core.providers",
        "core.prompts",
        "core.retrieval_batch_dispatch",
        "core.retrieval_batch_projection",
        "core.source_classifier",
        "core.source_class_recovery",
    }
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
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

    assert imported.isdisjoint(forbidden_modules)
