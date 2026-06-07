from __future__ import annotations

from pathlib import Path
from typing import Any

from core.runtime_trace_projection_assembly import attach_passive_runtime_projection_traces
from core.source_class_recovery import build_recovery_source_quality_diagnostics
from core.source_class_recovery_candidate_stream import (
    source_class_recovery_passage_candidates,
)
from core.source_class_recovery_projection_handoff import (
    build_source_class_recovery_projection_handoff,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_HANDOFF_PATH = _ROOT / "core" / "source_class_recovery_projection_handoff.py"


def _official_source(**overrides: Any) -> dict[str, Any]:
    source = {
        "source_id": "official-current-rule",
        "title": "Official current rule",
        "url": "https://agency.gov/current-rule",
        "text": "The agency current rule is in force for 2026.",
        "score": 0.87,
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "classification_reason": "declared_source_class",
        "retrieval_stage": "source_class_recovery",
    }
    source.update(overrides)
    return source


def _context_source(**overrides: Any) -> dict[str, Any]:
    source = {
        "source_id": "context-source",
        "title": "Context analysis",
        "url": "https://analysis.example/context",
        "text": "Background analysis.",
        "score": 0.99,
        "source_tier": "secondary",
        "source_class": "secondary",
    }
    source.update(overrides)
    return source


def _runtime_trace() -> dict[str, Any]:
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": "answer_contract_official_gap_missing",
        "recovered_visibility_used": True,
        "recovered_visibility_missing_source_class": "official_current_rules",
        "authority_lifecycle": {
            "execution_state": {"state": "attempted", "result_count": 1},
            "recovery_action": {
                "action_type": "recover_missing_source_class",
                "approved": True,
                "required_source_classes": ["official_current_rules"],
                "provider_role": "source_class_recovery",
            },
        },
    }


def test_ag76c_dp_handoff_matches_old_diagnostics_and_projection_inputs() -> None:
    final_top_evidence = [_context_source(), _official_source()]
    all_passages = [
        _context_source(url="https://analysis.example/background"),
        _official_source(),
        _official_source(
            source_id="official-guidance",
            title="Official guidance",
            url="https://agency.gov/guidance",
        ),
    ]
    final_source_class_counts = {"official_current_rules": 1}
    legacy_recovered = source_class_recovery_passage_candidates(
        all_passages=all_passages,
    )
    legacy_diagnostics = build_recovery_source_quality_diagnostics(
        legacy_recovered,
        final_top_evidence=final_top_evidence,
        final_source_class_counts=final_source_class_counts,
    )

    handoff = build_source_class_recovery_projection_handoff(
        all_passages=all_passages,
        final_top_evidence=final_top_evidence,
        final_source_class_counts=final_source_class_counts,
    )

    assert handoff.recovered_source_class_passages == legacy_recovered
    assert handoff.recovery_source_quality_diagnostics == legacy_diagnostics


def test_ag76c_dp_empty_handoff_preserves_old_no_update_shape() -> None:
    handoff = build_source_class_recovery_projection_handoff(
        all_passages=[_context_source()],
        final_top_evidence=[_context_source()],
        final_source_class_counts={},
    )

    assert handoff.recovered_source_class_passages == []
    assert handoff.recovery_source_quality_diagnostics == {}


def test_ag76c_dp_runtime_projection_matches_legacy_recovered_passages() -> None:
    all_passages = [_context_source(), _official_source()]
    final_top_evidence = [_official_source()]
    legacy_trace = _runtime_trace()
    handoff_trace = _runtime_trace()
    legacy_recovered = source_class_recovery_passage_candidates(
        all_passages=all_passages,
    )
    handoff = build_source_class_recovery_projection_handoff(
        all_passages=all_passages,
        final_top_evidence=final_top_evidence,
        final_source_class_counts={"official_current_rules": 1},
    )

    legacy_projected = attach_passive_runtime_projection_traces(
        legacy_trace,
        recovered_passages=legacy_recovered,
        final_top_evidence=final_top_evidence,
    )
    handoff_projected = attach_passive_runtime_projection_traces(
        handoff_trace,
        recovered_passages=handoff.recovered_source_class_passages,
        final_top_evidence=final_top_evidence,
    )

    for key in (
        "authority_candidate_passport_projection",
        "controller_evidence_ledger",
        "official_canonical_recovery_visibility_export",
    ):
        assert handoff_projected[key] == legacy_projected[key]


def test_ag76c_dp_static_orchestrator_no_longer_owns_handoff_block() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    post_author_source = (_ORCHESTRATOR_PATH.parent / "post_author_output_projection.py").read_text(encoding="utf-8")
    handoff_source = _HANDOFF_PATH.read_text(encoding="utf-8").casefold()

    assert "build_source_class_recovery_projection_handoff(" in orchestrator_source
    assert "source_class_recovery_passage_candidates(" not in orchestrator_source
    assert "build_recovery_source_quality_diagnostics(" not in orchestrator_source
    assert "recovered_source_class_passages =" not in orchestrator_source
    assert "attach_runtime_trace_export_compatibility_payloads(" in post_author_source
    assert "attach_passive_runtime_projection_traces(" not in orchestrator_source

    closed_terms = (
        "select_providers(",
        "process_search_queries(",
        "ask_model(",
        "build_final_answer(",
        "candidate_fit(",
        "author_prompt",
        "citation_format",
        "citation_selection",
        "scrutineer",
        "economist",
        "raw_provider_payload",
        "raw_prompt",
        "credential_marker",
        "secret",
    )
    for term in closed_terms:
        assert term not in handoff_source
