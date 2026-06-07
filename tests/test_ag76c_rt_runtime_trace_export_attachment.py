from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.source_class_recovery_diagnostics import SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "core" / "runtime_trace_export_attachment.py"
ORCHESTRATOR_PATH = ROOT / "core" / "pipeline_orchestrator.py"


def _legacy_inline_attachment(
    helper: Any,
    execution_trace: dict[str, Any],
    *,
    recovered_passages: list[dict[str, Any]],
    final_top_evidence: list[dict[str, Any]],
    max_iterations: int,
    evidence_bundle_source_class_counts: dict[str, Any],
    session_payload: dict[str, Any],
) -> dict[str, Any] | None:
    helper.attach_passive_runtime_projection_traces(
        execution_trace,
        recovered_passages=recovered_passages,
        final_top_evidence=final_top_evidence,
        logger=None,
    )
    execution_trace["retrieval_budget_pressure_shadow"] = (
        helper.build_retrieval_budget_pressure_shadow(
            trace=execution_trace,
            max_iterations=max_iterations,
            final_top_evidence=final_top_evidence,
        )
    )
    execution_trace["source_class_recovery_candidate_v2"] = (
        helper.build_source_class_recovery_candidate_v2(execution_trace)
    )
    source_class_recovery_validation_packet = (
        helper._build_source_class_recovery_validation_packet_safe(
            execution_trace,
            evidence_bundle_source_class_counts=evidence_bundle_source_class_counts,
            logger=None,
        )
    )
    if source_class_recovery_validation_packet is not None:
        execution_trace[SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY] = (
            source_class_recovery_validation_packet
        )
    controller_diagnostics_payload = (
        helper._build_controller_diagnostics_payload_with_size_guard(
            execution_trace,
            logger=None,
        )
    )
    if controller_diagnostics_payload is not None:
        execution_trace["controller_diagnostics"] = controller_diagnostics_payload
    session_payload["execution_trace"] = execution_trace
    return source_class_recovery_validation_packet


@pytest.fixture()
def deterministic_attachment_builders(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.runtime_trace_export_attachment as helper

    def fake_projection(
        execution_trace: dict[str, Any],
        *,
        recovered_passages: list[dict[str, Any]],
        final_top_evidence: list[dict[str, Any]],
        logger: Any,
    ) -> dict[str, Any]:
        execution_trace["projection_marker"] = {
            "recovered_count": len(recovered_passages),
            "final_count": len(final_top_evidence),
        }
        checkpoint = execution_trace.get("evidence_integration_checkpoint_trace")
        if isinstance(checkpoint, dict):
            checkpoint["projection_marker"] = execution_trace["projection_marker"]
        return execution_trace

    monkeypatch.setattr(helper, "attach_passive_runtime_projection_traces", fake_projection)
    monkeypatch.setattr(
        helper,
        "build_retrieval_budget_pressure_shadow",
        lambda *, trace, max_iterations, final_top_evidence: {
            "max_iterations": max_iterations,
            "trace_keys_after_projection": tuple(trace.keys()),
            "final_ids": tuple(item.get("id") for item in final_top_evidence),
        },
    )
    monkeypatch.setattr(
        helper,
        "build_source_class_recovery_candidate_v2",
        lambda trace: {
            "candidate_trace_keys": tuple(trace.keys()),
            "projection_seen": trace.get("projection_marker"),
        },
    )
    monkeypatch.setattr(
        helper,
        "build_source_class_recovery_validation_packet",
        lambda trace, *, evidence_bundle_source_class_counts: {
            "validation_counts": dict(evidence_bundle_source_class_counts),
            "candidate_v2_seen": trace["source_class_recovery_candidate_v2"],
        },
    )
    monkeypatch.setattr(
        helper,
        "build_controller_diagnostics_payload",
        lambda trace, *, include_stage_items: {
            "include_stage_items": include_stage_items,
            "validation_seen": trace[SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY],
        },
    )


def test_ag76c_rt_helper_matches_legacy_inline_attachment_sequence(
    deterministic_attachment_builders: None,
) -> None:
    import core.runtime_trace_export_attachment as helper

    recovered_passages = [{"id": "r1"}, {"id": "r2"}]
    final_top_evidence = [{"id": "f1"}]
    counts = {"official_current_rules": 1}
    legacy_trace = {"evidence_integration_checkpoint_trace": {}, "seed": "same"}
    helper_trace = {"evidence_integration_checkpoint_trace": {}, "seed": "same"}
    legacy_session: dict[str, Any] = {}
    helper_session: dict[str, Any] = {}

    legacy_validation = _legacy_inline_attachment(
        helper,
        legacy_trace,
        recovered_passages=recovered_passages,
        final_top_evidence=final_top_evidence,
        max_iterations=4,
        evidence_bundle_source_class_counts=counts,
        session_payload=legacy_session,
    )
    result = helper.attach_runtime_trace_export_compatibility_payloads(
        helper_trace,
        recovered_passages=recovered_passages,
        final_top_evidence=final_top_evidence,
        max_iterations=4,
        evidence_bundle_source_class_counts=counts,
        session_payload=helper_session,
        logger=None,
    )

    assert result.source_class_recovery_validation_packet == legacy_validation
    assert result.execution_trace == legacy_trace
    assert helper_trace == legacy_trace
    assert helper_session == legacy_session
    assert helper_session["execution_trace"] is helper_trace


def test_ag76c_rt_helper_preserves_legacy_field_aliases(
    deterministic_attachment_builders: None,
) -> None:
    import core.runtime_trace_export_attachment as helper

    trace = {"evidence_integration_checkpoint_trace": {}}
    session: dict[str, Any] = {}

    helper.attach_runtime_trace_export_compatibility_payloads(
        trace,
        recovered_passages=[],
        final_top_evidence=[],
        max_iterations=2,
        evidence_bundle_source_class_counts={},
        session_payload=session,
        logger=None,
    )

    assert "retrieval_budget_pressure_shadow" in trace
    assert "source_class_recovery_candidate_v2" in trace
    assert SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY in trace
    assert "controller_diagnostics" in trace
    assert session["execution_trace"] is trace


def test_ag76c_rt_helper_has_no_protected_behavior_imports() -> None:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    banned_fragments = (
        "core.search_providers",
        "core.provider_diagnostics",
        "core.prompts",
        "core.answer_contract",
        "core.answer_contract_runtime_handoff",
        "core.final_evidence_bundle_builder",
        "core.routing",
        "core.retrieval_quality",
        "core.run_author",
    )
    assert not [
        module
        for module in sorted(imported_modules)
        if any(fragment in module for fragment in banned_fragments)
    ]


def test_ag76c_rt_orchestrator_delegates_attachment_tail() -> None:
    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    post_author_source = (ORCHESTRATOR_PATH.parent / "post_author_output_projection.py").read_text(encoding="utf-8")

    assert "attach_runtime_trace_export_compatibility_payloads(" in post_author_source
    assert "attach_passive_runtime_projection_traces(" not in source
    assert "build_retrieval_budget_pressure_shadow(" not in source
    assert "build_source_class_recovery_candidate_v2(" not in source
    assert "_build_controller_diagnostics_payload_with_size_guard" not in source
    assert "_build_source_class_recovery_validation_packet_safe" not in source
