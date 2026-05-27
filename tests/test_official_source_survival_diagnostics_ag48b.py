from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.official_source_survival_diagnostics import (
    ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE,
    ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
    CANDIDATE_ACCEPTANCE_STAGE,
    CANDIDATE_ACQUISITION_STAGE,
    CANDIDATE_QUERY_GENERATION_STAGE,
    CAVEAT_ABSENT,
    CAVEAT_PRESENT,
    CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
    CITED_VALUE_EXTRACTION_STAGE,
    FINAL_CITATION_SURVIVAL_STAGE,
    FINAL_EVIDENCE_SOURCE_NOT_CITED,
    FINAL_EVIDENCE_SURVIVAL_STAGE,
    NO_ACTION_LANE,
    NO_CANDIDATE_QUERY,
    NO_OFFICIAL_CANDIDATES_RETURNED,
    NOT_A_SOURCE_ACQUISITION_FAILURE,
    NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
    OBLIGATION_NOT_DETECTED,
    OFFICIAL_CANDIDATE_MISCLASSIFIED,
    OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE,
    SOURCE_ACQUISITION_SURVIVAL_LANE,
    SOURCE_CLASS_CANONICAL_CLASSIFICATION_LANE,
    SOURCE_FIT_CITATION_SURVIVAL_LANE,
    SOURCE_OBLIGATION_DETECTION_STAGE,
    SOURCE_SURVIVED_STAGE,
    OfficialSourceSurvivalDiagnostic,
    classify_official_source_survival,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_source_survival_diagnostics.py"


def _classify(**overrides: object) -> tuple[str, str, str, str, bool]:
    base = {
        "question_type": "official_current_status",
        "source_obligation_required": True,
        "required_source_obligation": "official mission/status source",
        "obligation_detected": True,
        "candidate_query_count": 1,
        "candidate_official_or_canonical_count": 1,
        "accepted_official_or_canonical_count": 1,
        "final_evidence_official_or_canonical_count": 1,
        "final_citation_official_or_canonical_count": 1,
        "candidate_misclassified": False,
        "caveat_present": False,
        "numeric_value_mismatch": False,
    }
    base.update(overrides)
    result = classify_official_source_survival(
        OfficialSourceSurvivalDiagnostic.from_mapping(base)
    )
    return (
        result.bottleneck_class,
        result.source_survival_stage,
        result.recommended_next_lane,
        result.caveat_status,
        result.behavior_changed,
    )


@pytest.mark.parametrize(
    ("overrides", "bottleneck", "stage", "lane"),
    [
        (
            {"obligation_detected": False},
            OBLIGATION_NOT_DETECTED,
            SOURCE_OBLIGATION_DETECTION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"candidate_query_count": 0},
            NO_CANDIDATE_QUERY,
            CANDIDATE_QUERY_GENERATION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"candidate_official_or_canonical_count": 0},
            NO_OFFICIAL_CANDIDATES_RETURNED,
            CANDIDATE_ACQUISITION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"accepted_official_or_canonical_count": 0},
            OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE,
            CANDIDATE_ACCEPTANCE_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {
                "accepted_official_or_canonical_count": 0,
                "candidate_misclassified": True,
            },
            OFFICIAL_CANDIDATE_MISCLASSIFIED,
            CANDIDATE_ACCEPTANCE_STAGE,
            SOURCE_CLASS_CANONICAL_CLASSIFICATION_LANE,
        ),
        (
            {"final_evidence_official_or_canonical_count": 0},
            ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE,
            FINAL_EVIDENCE_SURVIVAL_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
        ),
        (
            {"final_citation_official_or_canonical_count": 0},
            FINAL_EVIDENCE_SOURCE_NOT_CITED,
            FINAL_CITATION_SURVIVAL_STAGE,
            SOURCE_FIT_CITATION_SURVIVAL_LANE,
        ),
        (
            {"numeric_value_mismatch": True},
            CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
            CITED_VALUE_EXTRACTION_STAGE,
            NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
        ),
    ],
)
def test_ag48b_classifies_source_disappearance_stage(
    overrides: dict[str, object],
    bottleneck: str,
    stage: str,
    lane: str,
) -> None:
    assert _classify(**overrides) == (
        bottleneck,
        stage,
        lane,
        CAVEAT_ABSENT,
        False,
    )


def test_ag48b_reputable_news_can_be_enough_for_context_but_not_exact_effect() -> None:
    context_result = _classify(
        question_type="current_event_context",
        source_obligation_required=False,
        required_source_obligation="reputable news/current-event context",
        candidate_query_count=1,
        candidate_official_or_canonical_count=0,
        accepted_official_or_canonical_count=0,
        final_evidence_official_or_canonical_count=0,
        final_citation_official_or_canonical_count=0,
    )
    exact_effect_result = _classify(
        question_type="exact_current_legal_status",
        source_obligation_required=True,
        required_source_obligation="official/current government/legal source",
        candidate_query_count=1,
        candidate_official_or_canonical_count=0,
        accepted_official_or_canonical_count=0,
        final_evidence_official_or_canonical_count=0,
        final_citation_official_or_canonical_count=0,
    )

    assert context_result[0:3] == (
        NOT_A_SOURCE_ACQUISITION_FAILURE,
        SOURCE_SURVIVED_STAGE,
        NO_ACTION_LANE,
    )
    assert exact_effect_result[0:3] == (
        NO_OFFICIAL_CANDIDATES_RETURNED,
        CANDIDATE_ACQUISITION_STAGE,
        SOURCE_ACQUISITION_SURVIVAL_LANE,
    )
    assert context_result[-1] is False
    assert exact_effect_result[-1] is False


def test_ag48b_answer_correctly_caveats_missing_official_source() -> None:
    assert _classify(
        candidate_official_or_canonical_count=0,
        accepted_official_or_canonical_count=0,
        final_evidence_official_or_canonical_count=0,
        final_citation_official_or_canonical_count=0,
        caveat_present=True,
    ) == (
        ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
        CANDIDATE_ACQUISITION_STAGE,
        SOURCE_ACQUISITION_SURVIVAL_LANE,
        CAVEAT_PRESENT,
        False,
    )


def test_ag48b_clean_case_has_no_source_acquisition_failure() -> None:
    assert _classify() == (
        NOT_A_SOURCE_ACQUISITION_FAILURE,
        SOURCE_SURVIVED_STAGE,
        NO_ACTION_LANE,
        CAVEAT_ABSENT,
        False,
    )


def test_ag48b_mapping_helpers_round_trip_sanitized_fields() -> None:
    diagnostic = OfficialSourceSurvivalDiagnostic.from_mapping(
        {
            "question_type": "canonical_technical_reference",
            "source_obligation_required": True,
            "required_source_obligation": "canonical technical documentation",
            "candidate_query_count": "2",
            "candidate_official_or_canonical_count": "1",
            "metadata": {"case": "fixture"},
        }
    )
    classification = classify_official_source_survival(diagnostic)

    assert diagnostic.to_dict()["candidate_query_count"] == 2
    assert diagnostic.to_dict()["metadata"] == {"case": "fixture"}
    assert classification.to_dict()["behavior_changed"] is False


def test_ag48b_behavior_changed_is_always_false() -> None:
    cases = [
        {"obligation_detected": False},
        {"candidate_query_count": 0},
        {"candidate_official_or_canonical_count": 0},
        {"accepted_official_or_canonical_count": 0},
        {"final_evidence_official_or_canonical_count": 0},
        {"final_citation_official_or_canonical_count": 0},
        {"numeric_value_mismatch": True},
        {},
    ]

    for overrides in cases:
        assert _classify(**overrides)[-1] is False


def test_ag48b_static_guard_has_no_runtime_provider_prompt_or_classifier_imports() -> None:
    forbidden_modules = {
        "core.answer_contract_controller",
        "core.answer_contract_runtime_handoff",
        "core.db",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_class_recovery",
        "core.source_class_recovery_lifecycle",
        "core.source_classifier",
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
