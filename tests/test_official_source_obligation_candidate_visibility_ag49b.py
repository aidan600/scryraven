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
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY,
    OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY,
    PREFERRED,
    REQUIRED,
    UNKNOWN,
    build_official_source_obligation_candidate_visibility_traces,
)
from core.official_source_survival_projection import (
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY,
    build_official_source_survival_projection_trace,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _ROOT / "core" / "official_source_obligation_candidate_visibility.py"
)
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_THIS_FILE = Path(__file__)


def _candidate(trace: dict[str, Any]) -> dict[str, Any]:
    packet = build_official_source_obligation_candidate_visibility_traces(
        runtime_trace=trace
    )[OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY]
    assert packet["trace_mode"] == "passive_runtime_visibility"
    return packet["OfficialSourceCandidateVisibility"]


def _obligation(trace: dict[str, Any]) -> dict[str, Any]:
    packet = build_official_source_obligation_candidate_visibility_traces(
        runtime_trace=trace
    )[OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY]
    assert packet["trace_mode"] == "passive_runtime_visibility"
    return packet["OfficialSourceObligation"]


def test_ag49b_detects_official_current_numeric_obligation() -> None:
    projection = _candidate(
        {
            "query_preview": (
                "What are the 2026 vs 2025 Social Security COLA, taxable "
                "maximum, earnings-test limits, and SSI federal payment amounts?"
            ),
            "query_type": "quantitative_comparison",
        }
    )

    assert projection["obligation_status"] == REQUIRED
    assert projection["obligation_required_or_preferred"] == REQUIRED
    assert projection["obligation_source"] == "sanitized_query_preview_inference"
    assert projection["obligation_detected_by_runtime"] is False
    assert projection["required_source_classes"] == ["official_current_rules"]
    assert projection["likely_visibility_gap"] == "obligation_detection_gap"
    assert projection["behavior_changed"] is False


def test_ag49b_detects_canonical_technical_obligation_without_source_specific_rule() -> None:
    projection = _candidate(
        {
            "query_preview": (
                "Explain how SQLite write-ahead logging works, why it improves "
                "concurrency, and when WAL mode is a bad idea."
            ),
            "query_type": "technical_reference",
        }
    )

    assert projection["obligation_status"] == REQUIRED
    assert (
        projection["obligation_reason"]
        == "official_agency_or_canonical_technical_behavior_request"
    )
    assert projection["required_source_classes"] == ["primary_source_documents"]
    module_text = _MODULE_PATH.read_text(encoding="utf-8").casefold()
    assert "sqlite.org" not in module_text
    assert "ssa.gov" not in module_text


def test_ag49b_does_not_require_official_source_for_conceptual_explainer() -> None:
    projection = _candidate(
        {
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        }
    )

    assert projection["obligation_status"] == NOT_REQUIRED
    assert projection["obligation_reason"] == "unclear_no_obligation_detected"
    assert projection["required_source_classes"] == []
    assert (
        projection["likely_visibility_gap"]
        == "no_official_current_canonical_obligation_visible"
    )


def test_ag49b_marks_current_event_context_as_preferred_not_required() -> None:
    projection = _candidate(
        {
            "query_preview": (
                "What happened this week in the transit strike, and what should "
                "commuters know?"
            ),
            "query_type": "current_event_context",
        }
    )

    assert projection["obligation_status"] == PREFERRED
    assert projection["obligation_required_or_preferred"] == PREFERRED
    assert projection["obligation_reason"] == "reputable_current_context_preferred"
    assert projection["required_source_classes"] == []
    assert "this week" in projection["obligation_trigger_terms"]


def test_ag49b_preserves_unknown_when_candidate_stage_is_unavailable() -> None:
    projection = _candidate({})

    assert projection["obligation_status"] == UNKNOWN
    assert projection["candidate_query_visibility_status"] == UNKNOWN
    assert projection["candidate_query_count"] == UNKNOWN
    assert projection["candidate_official_source_visibility_status"] == UNKNOWN
    assert projection["candidate_official_source_count"] == UNKNOWN
    assert projection["accepted_or_readable_visibility_status"] == UNKNOWN
    assert projection["accepted_or_readable_official_source_count"] == UNKNOWN
    assert projection["likely_visibility_gap"] == "obligation_visibility_unknown"
    assert "candidate_query_count" in projection["unknown_fields"]


def test_ag49b_candidate_query_intent_uses_visible_sanitized_previews() -> None:
    projection = _candidate(
        {
            "expected_source_classes_raw": ["official_current_rules"],
            "active_source_class_recovery_queries": [
                "official agency fact sheet 2026 taxable maximum",
                "retirement earnings test official source",
            ],
        }
    )

    assert projection["obligation_status"] == REQUIRED
    assert projection["obligation_detected_by_runtime"] is True
    assert projection["candidate_query_visibility_status"] == "visible"
    assert projection["candidate_query_count"] == 2
    assert projection["candidate_query_previews"] == [
        "official agency fact sheet 2026 taxable maximum",
        "retirement earnings test official source",
    ]
    assert projection["candidate_query_official_intent_status"] == "visible"
    assert projection["likely_visibility_gap"] == "official_candidate_visibility_unknown"


def test_ag49b_candidate_official_sources_count_only_when_directly_visible() -> None:
    projection = _candidate(
        {
            "expected_source_classes_raw": ["official_current_rules"],
            "active_source_class_recovery_queries": ["official source query"],
            "candidate_official_source_count": 2,
            "candidate_official_source_domains": [
                "https://agency.example/facts",
                "www.rules.example",
            ],
        }
    )

    assert projection["candidate_official_source_visibility_status"] == "visible"
    assert projection["candidate_official_source_count"] == 2
    assert projection["candidate_official_source_domain_previews"] == [
        "agency.example",
        "rules.example",
    ]
    assert projection["accepted_or_readable_visibility_status"] == UNKNOWN
    assert projection["likely_visibility_gap"] == "accepted_or_readable_visibility_unknown"


def test_ag49b_acceptance_readability_remains_unknown_without_direct_fact() -> None:
    projection = _candidate(
        {
            "expected_source_classes_raw": ["official_current_rules"],
            "active_source_class_recovery_queries": ["official source query"],
            "candidate_official_source_count": 1,
            "active_source_class_recovery_used": False,
            "recovered_official_or_primary_count": 0,
            "source_survival_final_evidence_official_or_canonical_count": 1,
            "source_survival_final_citation_official_or_canonical_count": 1,
        }
    )

    assert projection["candidate_official_source_visibility_status"] == "visible"
    assert projection["accepted_or_readable_visibility_status"] == UNKNOWN
    assert projection["accepted_or_readable_official_source_count"] == UNKNOWN
    assert projection["final_evidence_survival_status"] == "visible"
    assert projection["final_citation_survival_status"] == "visible"
    assert projection["likely_visibility_gap"] == "accepted_or_readable_visibility_unknown"


def test_ag49b_acceptance_readability_uses_recovered_count_only_after_active_recovery() -> None:
    projection = _candidate(
        {
            "expected_source_classes_raw": ["official_current_rules"],
            "active_source_class_recovery_queries": ["official source query"],
            "candidate_official_source_count": 1,
            "active_source_class_recovery_used": True,
            "recovered_official_or_primary_count": 1,
        }
    )

    assert projection["accepted_or_readable_visibility_status"] == "visible"
    assert projection["accepted_or_readable_official_source_count"] == 1


def test_ag49b_reuses_ag49a_final_survival_without_backfilling_candidates() -> None:
    trace = {
        "query_preview": (
            "What are the 2026 vs 2025 COLA and federal payment amounts?"
        ),
        "query_type": "quantitative_comparison",
        "expected_source_classes_raw": ["none"],
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
        "source_bound_value_count": 2,
    }
    survival_trace = build_official_source_survival_projection_trace(
        runtime_trace=trace
    )
    trace[OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY] = survival_trace
    projection = _candidate(trace)
    survival_projection = survival_trace["OfficialSourceSurvivalProjection"]

    assert survival_projection["final_evidence_official_or_canonical_count"] == 1
    assert survival_projection["final_citation_official_or_canonical_count"] == 1
    assert projection["final_evidence_official_or_canonical_count"] == 1
    assert projection["final_citation_official_or_canonical_count"] == 1
    assert projection["candidate_query_count"] == UNKNOWN
    assert projection["candidate_official_source_count"] == UNKNOWN
    assert projection["accepted_or_readable_official_source_count"] == UNKNOWN
    assert projection["behavior_changed"] is False


def test_ag49b_obligation_trace_is_compact_subset() -> None:
    projection = _obligation(
        {
            "expected_source_classes_raw": ["primary_source_documents"],
            "active_source_class_recovery_queries": ["canonical documentation"],
        }
    )

    assert projection["obligation_status"] == REQUIRED
    assert projection["required_source_classes"] == ["primary_source_documents"]
    assert "candidate_query_previews" not in projection
    assert projection["behavior_changed"] is False


def test_ag49b_redacts_protected_values_and_drops_sensitive_keys() -> None:
    projection = _candidate(
        {
            "query_preview": "raw prompt protected_marker_value",
            "expected_source_classes_raw": ["official_current_rules"],
            "raw_provider_payload": {"body": "provider_payload protected_marker_value"},
            "active_source_class_recovery_queries": [
                "raw prompt protected_marker_value"
            ],
        }
    )
    payload = json.dumps(projection, sort_keys=True)

    assert "protected_marker_value" not in payload
    assert "provider_payload protected_marker_value" not in payload
    assert projection["candidate_query_previews"] == [
        "[redacted protected material]"
    ]


def test_ag49b_runtime_attachment_preserves_existing_trace_shape() -> None:
    execution_trace = {
        "run_id": "ag49b",
        "unrelated_trace": {"kept": True},
        "expected_source_classes_raw": ["official_current_rules"],
        "active_source_class_recovery_queries": ["official source query"],
        "candidate_official_source_count": 1,
        "accepted_or_readable_official_source_count": 1,
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 0,
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }
    unrelated = execution_trace["unrelated_trace"]

    returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert returned["unrelated_trace"] is unrelated
    assert OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY in returned
    assert OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY in returned
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY
        ]
        == returned[OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY]
    )
    projection = returned[OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY][
        "OfficialSourceCandidateVisibility"
    ]
    assert projection["final_citation_survival_status"] == "not_visible"
    assert projection["likely_visibility_gap"] == "final_citation_survival_gap"


def test_ag49b_attachment_failure_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    execution_trace = {"run_id": "ag49b"}

    def _raise_projection_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("ag49b projection boom")

    monkeypatch.setattr(
        projection_assembly,
        "build_official_source_obligation_candidate_visibility_traces",
        _raise_projection_error,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="core.runtime_trace_projection_assembly",
    ):
        returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY not in execution_trace
    assert "official-source obligation/candidate projection omitted" in caplog.text


def test_ag49b_static_guards_keep_protected_surfaces_out() -> None:
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
    assert OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY not in pipeline_source


def test_ag49b_tests_do_not_inspect_raw_or_generated_artifacts() -> None:
    tree = ast.parse(_THIS_FILE.read_text(encoding="utf-8"))
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    forbidden_path_fragments = {
        "out" + "put/ag49b",
        "execution_log" + ".jsonl",
        "provider" + "_payload.json",
        "raw" + "_trace",
        "db" + "_row",
        "." + "env",
        "cache" + "/",
        "prompt" + "." + "md",
    }

    assert all(
        fragment not in value
        for fragment in forbidden_path_fragments
        for value in string_constants
    )
