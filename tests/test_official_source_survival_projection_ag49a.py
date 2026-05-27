from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any

import pytest

import core.runtime_trace_projection_assembly as projection_assembly
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_source_survival_diagnostics import (
    CANDIDATE_QUERY_GENERATION_STAGE,
    FINAL_CITATION_SURVIVAL_STAGE,
    FINAL_EVIDENCE_SOURCE_NOT_CITED,
    NOT_A_SOURCE_ACQUISITION_FAILURE,
    SOURCE_FIT_CITATION_SURVIVAL_LANE,
    SOURCE_SURVIVED_STAGE,
)
from core.official_source_survival_projection import (
    NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
    OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_SCHEMA_VERSION,
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY,
    UNKNOWN,
    build_official_source_survival_projection_trace,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_source_survival_projection.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _projection(trace: dict[str, Any]) -> dict[str, Any]:
    packet = build_official_source_survival_projection_trace(runtime_trace=trace)
    assert packet["schema_version"] == OFFICIAL_SOURCE_SURVIVAL_PROJECTION_SCHEMA_VERSION
    assert packet["trace_mode"] == "passive_runtime_visibility"
    return packet["OfficialSourceSurvivalProjection"]


def test_ag49a_unknown_candidate_query_stays_unknown_not_zero() -> None:
    projection = _projection(
        {
            "query_type": "benefit_threshold_comparison",
            "expected_source_classes_raw": ["official_current_rules"],
            "source_class_satisfaction_status": {
                "official_current_rules": "unsatisfied"
            },
        }
    )

    assert projection["source_obligation_required"] is True
    assert projection["obligation_detected"] is True
    assert projection["candidate_query_count"] == UNKNOWN
    assert projection["candidate_official_or_canonical_count"] == UNKNOWN
    assert projection["missing_stage"] == CANDIDATE_QUERY_GENERATION_STAGE
    assert projection["bottleneck_class"] == NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS
    assert (
        projection["recommended_next_lane"]
        == OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE
    )
    assert "candidate_query_count" in projection["unknown_fields"]
    assert projection["behavior_changed"] is False


def test_ag49a_infers_public_program_numeric_obligation_without_runtime_detection() -> None:
    projection = _projection(
        {
            "query_preview": (
                "What are the 2026 vs 2025 COLA, taxable maximum, "
                "earnings-test limits, and SSI federal payment amounts?"
            ),
            "query_type": "quantitative_comparison",
            "expected_source_classes_raw": ["none"],
            "source_survival_final_evidence_official_or_canonical_count": 1,
            "source_survival_final_citation_official_or_canonical_count": 1,
            "source_bound_value_count": 2,
        }
    )

    assert projection["source_obligation_required"] is True
    assert projection["obligation_detected"] is False
    assert projection["required_source_classes"] == ["official_current_rules"]
    assert projection["missing_stage"] == "source_obligation_detection"
    assert projection["bottleneck_class"] == "obligation_not_detected"
    assert projection["behavior_changed"] is False


def test_ag49a_maps_visible_final_evidence_not_cited_stage() -> None:
    projection = _projection(
        {
            "query_type": "canonical_technical_reference",
            "expected_source_classes_raw": ["primary_source_documents"],
            "active_source_class_recovery_queries": ["canonical docs query"],
            "source_survival_final_evidence_official_or_canonical_count": 1,
            "source_survival_final_citation_official_or_canonical_count": 0,
            "answer_class": "complete_answer",
        }
    )

    assert projection["final_evidence_official_or_canonical_count"] == 1
    assert projection["final_citation_official_or_canonical_count"] == 0
    assert projection["bottleneck_class"] == FINAL_EVIDENCE_SOURCE_NOT_CITED
    assert projection["missing_stage"] == FINAL_CITATION_SURVIVAL_STAGE
    assert projection["recommended_next_lane"] == SOURCE_FIT_CITATION_SURVIVAL_LANE
    assert projection["behavior_changed"] is False


def test_ag49a_clean_cited_source_bound_case_has_no_survival_failure() -> None:
    projection = _projection(
        {
            "query_type": "official_current_status",
            "expected_source_classes_raw": ["official_current_rules"],
            "active_source_class_recovery_queries": ["agency current fact sheet"],
            "source_tier_counts": {"official": 1, "secondary": 1},
            "source_survival_final_evidence_official_or_canonical_count": 1,
            "source_survival_final_citation_official_or_canonical_count": 1,
            "source_bound_value_count": 3,
            "answer_class": "complete_answer",
        }
    )

    assert projection["bottleneck_class"] == NOT_A_SOURCE_ACQUISITION_FAILURE
    assert projection["missing_stage"] == SOURCE_SURVIVED_STAGE
    assert projection["recommended_next_lane"] == "no_action"
    assert projection["source_bound_value_present"] is True
    assert projection["behavior_changed"] is False


def test_ag49a_redacts_protected_values_and_drops_sensitive_keys() -> None:
    projection = _projection(
        {
            "query_type": "raw prompt with protected_marker_value",
            "expected_source_classes_raw": ["official_current_rules"],
            "raw_provider_payload": {"body": "provider_payload protected_marker_value"},
            "raw_prompt": "raw prompt should not appear",
            "active_source_class_recovery_queries": ["safe query preview"],
        }
    )
    payload = json.dumps(projection, sort_keys=True)

    assert "protected_marker_value" not in payload
    assert "provider_payload protected_marker_value" not in payload
    assert "raw prompt should not appear" not in payload
    assert projection["question_type"] == "[redacted protected material]"
    assert projection["behavior_changed"] is False


def test_ag49a_runtime_projection_attachment_preserves_existing_trace_shape() -> None:
    execution_trace = {
        "run_id": "ag49a",
        "unrelated_trace": {"kept": True},
        "expected_source_classes_raw": ["official_current_rules"],
        "active_source_class_recovery_queries": ["agency source query"],
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 0,
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }
    unrelated = execution_trace["unrelated_trace"]

    returned = attach_passive_runtime_projection_traces(execution_trace)
    projection_trace = returned[OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY]

    assert returned is execution_trace
    assert returned["unrelated_trace"] is unrelated
    assert returned["unrelated_trace"] == {"kept": True}
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY
        ]
        == projection_trace
    )
    assert (
        projection_trace["OfficialSourceSurvivalProjection"]["bottleneck_class"]
        == FINAL_EVIDENCE_SOURCE_NOT_CITED
    )


def test_ag49a_projection_attachment_failure_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    execution_trace = {
        "run_id": "ag49a",
        "expected_source_classes_raw": ["official_current_rules"],
    }

    def _raise_projection_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("official projection boom")

    monkeypatch.setattr(
        projection_assembly,
        "build_official_source_survival_projection_trace",
        _raise_projection_error,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="core.runtime_trace_projection_assembly",
    ):
        returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY not in execution_trace
    assert "Non-fatal official-source survival projection omitted" in caplog.text


def test_ag49a_static_guards_keep_protected_surfaces_out() -> None:
    forbidden_modules = {
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
    for path in (_MODULE_PATH, _ASSEMBLY_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "source_survival_final_evidence_official_or_canonical_count" in pipeline_source
