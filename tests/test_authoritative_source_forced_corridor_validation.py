from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor import (
    canonical_doc_forced_corridor_fixture,
    official_current_forced_corridor_fixture,
    run_forced_corridor_validation,
)

_ROOT = Path(__file__).resolve().parents[1]
_HARNESS_PATH = _ROOT / "tests" / "helpers" / "authoritative_source_forced_corridor.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SESSION_OUTPUT_PROJECTION_PATH = _ROOT / "core" / "session_output_projection.py"


def test_forced_official_current_corridor_distinguishes_secondary_ordinary_evidence() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )
    classification = result.classification

    assert classification["ordinary_authoritative_source_already_present"] is False
    assert classification["ordinary_evidence_status"] == "expected_but_only_secondary"
    assert classification["missing_authoritative_source_state_forced"] is True
    assert classification["authoritative_recovery_bridge_visible"] is True
    assert classification["authoritative_recovery_query_created"] is True
    assert classification["recovery_query_count"] > 0
    assert classification["recovery_execution_admitted"] is True
    assert classification["source_class_recovery_lifecycle_action_ready"] is True
    assert classification["recovery_dispatch_authorized"] is True
    assert classification["source_class_recovery_execution_attempted"] is True
    assert classification["recovered_evidence_visible"] is True
    assert classification["final_answer_citation_or_use"] == "not_applicable_offline"
    assert classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert classification["ordinary_acquisition_counted_as_recovery_success"] is False


def test_aggregate_only_ordinary_official_current_status_still_forces_custody() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture(
            ordinary_evidence_status="satisfied_strong",
            execute_dispatch_fixture=True,
        )
    )
    classification = result.classification

    assert classification["ordinary_authoritative_source_already_present"] is True
    assert classification["missing_authoritative_source_state_forced"] is True
    assert classification["authoritative_recovery_bridge_visible"] is True
    assert classification["authoritative_recovery_query_created"] is False
    assert classification["recovery_execution_admitted"] is False
    assert classification["recovery_dispatch_authorized"] is False
    assert classification["source_class_recovery_execution_attempted"] is False
    assert classification["recovered_evidence_visible"] == "not_applicable_offline"
    assert classification["next_failure_layer"] == "recovery_query_not_created"
    assert classification["ordinary_acquisition_counted_as_recovery_success"] is False


def test_forced_canonical_doc_corridor_reaches_recovery_path() -> None:
    result = run_forced_corridor_validation(canonical_doc_forced_corridor_fixture())
    classification = result.classification

    assert classification["ordinary_authoritative_source_already_present"] is False
    assert classification["missing_authoritative_source_state_forced"] is True
    assert classification["authoritative_recovery_bridge_visible"] is True
    assert classification["authoritative_recovery_query_created"] is True
    assert classification["recovery_execution_admitted"] is True
    assert classification["recovery_dispatch_authorized"] is True
    assert classification["recovered_evidence_visible"] is True
    assert classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert any(
        "documentation" in query.casefold()
        for query in result.dispatch_trace["captured_queries"]
    )


def test_dispatch_fixture_uses_existing_source_class_executor_path() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )
    action = result.controller_snapshot["retrieval_actions"][0]

    assert action["name"] == "source_class_recovery"
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert action["metadata"]["execution"] == "orchestrator_adapter_executed"
    assert result.dispatch_trace["dispatch_fixture_attempted"] is True
    assert result.dispatch_trace["executor_attempted"] is True
    assert result.dispatch_trace["recovered_passage_stages"] == [
        "source_class_recovery"
    ]


def test_forced_corridor_classifies_pre_admission_blocker() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture(
            ordinary_evidence_status="unsatisfied",
            execute_dispatch_fixture=False,
        )
    )
    classification = result.classification

    assert classification["missing_authoritative_source_state_forced"] is True
    assert classification["recovery_execution_admitted"] is True
    assert classification["recovery_dispatch_authorized"] is True
    assert classification["source_class_recovery_execution_attempted"] is False
    assert classification["recovered_evidence_visible"] == "not_applicable_offline"
    assert classification["next_failure_layer"] == "executor_not_attempted"


def test_lower_tier_laundering_remains_blocked_in_forced_corridor() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )
    projection = result.action_result.trace["obligation_projection"]

    assert projection["source_obligation_status"] == "partial"
    assert projection["source_class_satisfaction_status"][
        "official_current_rules"
    ] == "expected_but_only_secondary"
    assert result.classification["missing_authoritative_source_state_forced"] is True


def test_validation_classification_includes_next_failure_layer() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )

    assert "next_failure_layer" in result.classification
    assert result.classification["next_failure_layer"]


def test_compatibility_fields_are_retained_for_named_consumers() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )

    recommendation = result.action_result.recommendation
    lifecycle = result.action_result.active_source_class_recovery_lifecycle
    trace = result.action_result.trace

    assert "missing_expected_source_classes" in recommendation
    assert "source_class_recovery_queries" in recommendation
    assert "source_class_recovery_query_count" in recommendation
    assert "active_source_class_recovery_missing_classes" in lifecycle
    assert "active_source_class_recovery_queries" in lifecycle
    assert "active_source_class_recovery_action_envelope" in lifecycle
    assert "adapter_traces_present" in trace


def test_trace_projection_fields_do_not_feed_control_decisions() -> None:
    result = run_forced_corridor_validation(
        official_current_forced_corridor_fixture()
    )

    trace = result.action_result.trace
    assert trace["protected_surface"]["projection_used_as_control_input"] is False
    assert "obligation_projection" in trace["control_inputs_exclude"]
    assert trace["action_decision"]["approved"] is True


def test_forced_corridor_static_guard_keeps_protected_surfaces_closed() -> None:
    tree = ast.parse(_HARNESS_PATH.read_text(encoding="utf-8"))
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
    forbidden_imports = {
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.source_classifier",
        "openai",
        "requests",
    }

    assert imported.isdisjoint(forbidden_imports)
    source = _HARNESS_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in source


def test_pipeline_orchestrator_stays_unchanged_by_ag67a() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    projection_source = _SESSION_OUTPUT_PROJECTION_PATH.read_text(encoding="utf-8")

    assert "authoritative_source_forced_corridor" not in pipeline_source
    assert pipeline_source.count(
        "build_authoritative_source_action_orchestrator_handoff("
    ) == 1
    assert projection_source.count("authoritative_source_action_trace_fragment(") == 1
