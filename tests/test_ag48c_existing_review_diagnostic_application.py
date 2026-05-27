from __future__ import annotations

import ast
from pathlib import Path

from core.official_numeric_source_grounding import (
    ANSWER_CAVEATED_MISSING_EVIDENCE,
    CITATION_SOURCE_FIT_LANE,
    NUMERIC_EXTRACTION_LANE,
    NUMERIC_VALUE_NOT_SOURCE_BOUND,
    OFFICIAL_SOURCE_VISIBLE_NOT_CITED,
    WRONG_NUMBER_EXTRACTED,
    classify_official_numeric_grounding,
)
from core.official_source_survival_diagnostics import (
    ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
    CANDIDATE_ACQUISITION_STAGE,
    CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
    FINAL_CITATION_SURVIVAL_STAGE,
    FINAL_EVIDENCE_SOURCE_NOT_CITED,
    NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
    SOURCE_ACQUISITION_SURVIVAL_LANE,
    SOURCE_FIT_CITATION_SURVIVAL_LANE,
    classify_official_source_survival,
)

_ROOT = Path(__file__).resolve().parents[1]
_THIS_FILE = Path(__file__)
_DOC_PATH = (
    _ROOT / "docs" / "validation" / "AG48C_OFFICIAL_SOURCE_DIAGNOSTIC_APPLICATION.md"
)

OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION = "official_source_survival_instrumentation"
NUMERIC_EXTRACTION_ECONOMIST_DIAGNOSTICS = (
    "numeric_extraction_economist_diagnostics"
)
SOURCE_FIT_CITATION_SURVIVAL = "source_fit_citation_survival"
NO_IMPLEMENTATION_YET = "no_implementation_yet"
NOT_OBSERVABLE = "not observable from committed review doc"


def test_roth_ira_maps_to_cited_value_extraction_not_source_survival() -> None:
    numeric = classify_official_numeric_grounding(
        {
            "question_type": "tax_retirement_threshold",
            "official_source_required": True,
            "source_need_detected": True,
            "official_source_acquired": True,
            "official_source_accepted": True,
            "official_source_in_final_evidence": True,
            "official_source_cited": True,
            "numeric_values_extracted": False,
            "numeric_values_source_bound": False,
            "final_answer_value_mismatch": True,
        }
    )
    survival = classify_official_source_survival(
        {
            "question_type": "tax_retirement_threshold",
            "source_obligation_required": True,
            "required_source_obligation": "official/current government source",
            "obligation_detected": True,
            "candidate_query_count": 1,
            "candidate_official_or_canonical_count": 1,
            "accepted_official_or_canonical_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
            "numeric_value_mismatch": True,
        }
    )

    assert numeric.bottleneck_class == WRONG_NUMBER_EXTRACTED
    assert numeric.next_recommended_lane == NUMERIC_EXTRACTION_LANE
    assert survival.bottleneck_class == CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED
    assert survival.source_survival_stage == "cited_value_extraction"
    assert (
        survival.recommended_next_lane
        == NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE
    )
    assert _phase_lane(numeric.bottleneck_class, survival.bottleneck_class) == (
        NUMERIC_EXTRACTION_ECONOMIST_DIAGNOSTICS
    )
    assert numeric.behavior_changed is False
    assert survival.behavior_changed is False


def test_ssa_review_does_not_overclaim_unobservable_source_stage() -> None:
    case = {
        "review_case": "AG-47D Q1 Social Security / SSA 2026 vs 2025",
        "ag48a_bottleneck": ANSWER_CAVEATED_MISSING_EVIDENCE,
        "ag48b_stage": NOT_OBSERVABLE,
        "likely_next_lane": OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION,
    }

    assert case["ag48b_stage"] == NOT_OBSERVABLE
    assert case["likely_next_lane"] == OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    assert "no_official_candidates_returned" not in case.values()
    assert "accepted_source_dropped_before_final_evidence" not in case.values()


def test_starliner_caveat_supports_survival_instrumentation_not_exact_stage() -> None:
    caveated_missing = classify_official_source_survival(
        {
            "question_type": "official_current_status",
            "source_obligation_required": True,
            "required_source_obligation": "official mission/status source",
            "obligation_detected": True,
            "candidate_query_count": 1,
            "candidate_official_or_canonical_count": 0,
            "accepted_official_or_canonical_count": 0,
            "final_evidence_official_or_canonical_count": 0,
            "final_citation_official_or_canonical_count": 0,
            "caveat_present": True,
            "numeric_value_mismatch": False,
        }
    )
    committed_case_stage = NOT_OBSERVABLE

    assert (
        caveated_missing.bottleneck_class
        == ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE
    )
    assert caveated_missing.source_survival_stage == CANDIDATE_ACQUISITION_STAGE
    assert caveated_missing.recommended_next_lane == SOURCE_ACQUISITION_SURVIVAL_LANE
    assert committed_case_stage == NOT_OBSERVABLE
    assert (
        _phase_lane(ANSWER_CAVEATED_MISSING_EVIDENCE, committed_case_stage)
        == OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    )


def test_sqlite_canonical_docs_case_maps_to_source_fit_when_visible_uncited() -> None:
    numeric = classify_official_numeric_grounding(
        {
            "question_type": "canonical_technical_reference",
            "official_source_required": True,
            "source_need_detected": True,
            "official_source_acquired": True,
            "official_source_accepted": True,
            "official_source_in_final_evidence": True,
            "official_source_cited": False,
        }
    )
    survival = classify_official_source_survival(
        {
            "question_type": "canonical_technical_reference",
            "source_obligation_required": True,
            "required_source_obligation": "canonical technical documentation",
            "obligation_detected": True,
            "candidate_query_count": 1,
            "candidate_official_or_canonical_count": 1,
            "accepted_official_or_canonical_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 0,
        }
    )

    assert numeric.bottleneck_class == OFFICIAL_SOURCE_VISIBLE_NOT_CITED
    assert numeric.next_recommended_lane == CITATION_SOURCE_FIT_LANE
    assert survival.bottleneck_class == FINAL_EVIDENCE_SOURCE_NOT_CITED
    assert survival.source_survival_stage == FINAL_CITATION_SURVIVAL_STAGE
    assert survival.recommended_next_lane == SOURCE_FIT_CITATION_SURVIVAL_LANE
    assert _phase_lane(numeric.bottleneck_class, survival.bottleneck_class) == (
        SOURCE_FIT_CITATION_SURVIVAL
    )


def test_caveated_missing_evidence_remains_a_caveat_posture() -> None:
    numeric = classify_official_numeric_grounding(
        {
            "question_type": "multi_factor_tco_comparison",
            "official_source_required": True,
            "source_need_detected": True,
            "official_source_acquired": False,
            "official_source_in_final_evidence": False,
            "official_source_cited": False,
            "numeric_values_extracted": False,
            "numeric_values_source_bound": False,
            "final_answer_value_mismatch": False,
            "caveat_present": True,
        }
    )

    assert numeric.bottleneck_class == ANSWER_CAVEATED_MISSING_EVIDENCE
    assert (
        _phase_lane(numeric.bottleneck_class, NOT_OBSERVABLE)
        == OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    )
    assert numeric.behavior_changed is False


def test_heat_pump_cost_model_expresses_source_bound_value_gap() -> None:
    numeric = classify_official_numeric_grounding(
        {
            "question_type": "multi_factor_tco_comparison",
            "official_source_required": True,
            "source_need_detected": True,
            "official_source_acquired": True,
            "official_source_accepted": True,
            "official_source_in_final_evidence": True,
            "official_source_cited": True,
            "numeric_values_extracted": True,
            "numeric_values_source_bound": False,
            "final_answer_value_mismatch": False,
            "caveat_present": True,
        }
    )

    assert numeric.bottleneck_class == NUMERIC_VALUE_NOT_SOURCE_BOUND
    assert numeric.next_recommended_lane == NUMERIC_EXTRACTION_LANE
    assert (
        _phase_lane(numeric.bottleneck_class, NOT_OBSERVABLE)
        == OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    )


def test_application_doc_ends_with_selected_implementation_brief() -> None:
    text = _DOC_PATH.read_text(encoding="utf-8")

    assert "recommended next implementation phase:" in text.lower()
    assert "`official_source_survival_instrumentation`" in text
    assert "Phase name:\n\n`AG-49A - Official Source Survival Instrumentation`" in text
    assert text.rstrip().endswith(
        "later repair phase to choose between acquisition, acceptance, "
        "final-evidence\nsurvival, citation survival, numeric extraction, "
        "and synthesis lanes."
    )


def test_static_guard_does_not_access_generated_or_private_artifacts() -> None:
    tree = ast.parse(_THIS_FILE.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    forbidden_imports = {
        "core.db",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_classifier",
    }
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    forbidden_path_fragments = {
        "out" + "put/ag47",
        "out" + "puts/ag47",
        "provider" + "_payload",
        "raw" + "_trace",
        "db" + "_row",
        "." + "env",
        "cache" + "/",
        "prompt" + "." + "md",
    }

    assert imported_modules.isdisjoint(forbidden_imports)
    assert all(
        fragment not in value
        for fragment in forbidden_path_fragments
        for value in string_constants
    )


def _phase_lane(ag48a_bottleneck: str, ag48b_stage: str) -> str:
    if ag48b_stage == CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED:
        return NUMERIC_EXTRACTION_ECONOMIST_DIAGNOSTICS
    if ag48a_bottleneck in {WRONG_NUMBER_EXTRACTED, NUMERIC_VALUE_NOT_SOURCE_BOUND}:
        if ag48b_stage == NOT_OBSERVABLE:
            return OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
        return NUMERIC_EXTRACTION_ECONOMIST_DIAGNOSTICS
    if ag48b_stage == FINAL_EVIDENCE_SOURCE_NOT_CITED:
        return SOURCE_FIT_CITATION_SURVIVAL
    if ag48b_stage == NOT_OBSERVABLE:
        return OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    if ag48a_bottleneck == ANSWER_CAVEATED_MISSING_EVIDENCE:
        return OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION
    if ag48a_bottleneck == "no_official_numeric_grounding_bottleneck_detected":
        return NO_IMPLEMENTATION_YET
    return NO_IMPLEMENTATION_YET
