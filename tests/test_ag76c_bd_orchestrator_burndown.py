from __future__ import annotations

import ast
from pathlib import Path

from core.pipeline_decision_registry import (
    AG76C_BD_COMPLETED_POST_BURN_DOWN_PHASES,
    AG76C_BD_ORCHESTRATOR_SEAM_LEDGER,
    AG76C_BD_PHASE_NAME,
    AG76C_BD_SELECTED_NEXT_EXTRACTION_PHASE,
    AG76C_BD_SELECTED_NEXT_PHASE,
    ORCHESTRATOR_BURN_DOWN_CLASSIFICATIONS,
)

_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY_PATH = _ROOT / "core" / "pipeline_decision_registry.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _seam(name_fragment: str):
    for seam in AG76C_BD_ORCHESTRATOR_SEAM_LEDGER:
        if name_fragment in seam.seam_name:
            return seam
    raise AssertionError(f"missing seam containing {name_fragment!r}")


def test_ag76c_bd_ledger_marks_completed_ag76c_seams_extracted_complete() -> None:
    assert AG76C_BD_COMPLETED_POST_BURN_DOWN_PHASES == (
        "AG-76C-RT",
        "AG-76C-RT-C",
        "AG-76C-OP",
        "AG-76C-PE",
        "AG-76C-KB-C",
    )
    completed = {
        "AG-76C-FE": _seam("AG-76C-FE"),
        "AG-76C-CS": _seam("AG-76C-CS"),
        "AG-76C-DP": _seam("AG-76C-DP"),
        "AG-76C-RT": _seam("runtime trace projection/export attachment"),
        "AG-76C-OP/PE": _seam("JSONL/SQLite/persistence/outcome packaging"),
        "AG-76C-KB-C": _seam("KB review persistence context handoff"),
    }

    for seam in completed.values():
        assert seam.classification == "extracted_complete"
        assert seam.current_location.startswith("core/")
        assert seam.current_owner.startswith("core.")
        assert seam.target_owner.startswith("core.")
        assert seam.current_tests
        assert seam.missing_parity_tests == ()


def test_ag76c_bd_ledger_uses_all_required_classification_categories() -> None:
    expected = set(ORCHESTRATOR_BURN_DOWN_CLASSIFICATIONS)
    observed = {seam.classification for seam in AG76C_BD_ORCHESTRATOR_SEAM_LEDGER}

    assert expected == {
        "extracted_complete",
        "pure_plumbing",
        "decision_authority_still_local",
        "protected_behavior_surface",
        "defer_until_controller_state_ready",
        "intentionally_remaining_for_now",
    }
    assert expected <= observed


def test_ag76c_bd_ledger_includes_every_required_remaining_seam() -> None:
    required_fragments = (
        "router/researcher/query preparation handoff",
        "source obligation / AnswerContract initialization and handoff",
        "source-class recovery runner dispatch handoff",
        "provider/retrieval execution loop",
        "source-class recovery lifecycle / projection handoff",
        "recovered evidence visibility boundary",
        "final evidence bundle builder handoff",
        "final evidence/source telemetry and persistence handoff",
        "runtime trace projection/export attachment",
        "controller evidence ledger projection/handoff",
        "Analyst prompt/context handoff",
        "Author prompt/evidence handoff",
        "citation/source-list handoff",
        "weak-corpus/off-topic/failure-card gates",
        "Scrutineer/remediation handoff",
        "Economist preflight / Economist handoff",
        "follow-up/session state handoff",
        "KB review persistence context handoff",
        "JSONL/SQLite/persistence/outcome packaging",
    )

    names = {seam.seam_name for seam in AG76C_BD_ORCHESTRATOR_SEAM_LEDGER}
    for fragment in required_fragments:
        assert any(fragment in name for name in names), fragment


def test_ag76c_bd_selects_exactly_one_next_extraction_phase_with_required_contract() -> None:
    selected = AG76C_BD_SELECTED_NEXT_PHASE

    assert AG76C_BD_PHASE_NAME == "AG-76C-BD"
    assert AG76C_BD_SELECTED_NEXT_EXTRACTION_PHASE == "AG-77A"
    assert selected.phase_name == "AG-77A"
    assert "AG-76C-KB-C" in AG76C_BD_COMPLETED_POST_BURN_DOWN_PHASES
    assert "KbReviewPersistenceContext construction" in selected.old_orchestrator_block
    assert "core.kb_review_persistence_context" in selected.replacement_owner
    assert selected.protected_surfaces
    assert selected.required_parity_tests
    assert selected.stop_conditions
    assert "provider, retrieval, citation, AnswerContract" in selected.why_next
    assert "runtime cache implementation" in selected.why_next

    selected_seams = [
        seam
        for seam in AG76C_BD_ORCHESTRATOR_SEAM_LEDGER
        if seam.recommended_next_action.startswith("AG-76C-KB-C complete")
    ]
    assert [seam.seam_name for seam in selected_seams] == [
        "KB review persistence context handoff"
    ]


def test_ag76c_bd_selected_phase_names_old_block_owner_surfaces_and_parity_tests() -> None:
    selected = AG76C_BD_SELECTED_NEXT_PHASE
    protected = " ".join(selected.protected_surfaces)
    tests = " ".join(selected.required_parity_tests)

    assert "KbReviewPersistenceContext" in selected.old_orchestrator_block
    assert "core.kb_review_persistence_context" in selected.replacement_owner
    assert "KB execution-record payload" in protected
    assert "provider/search/routing/prompt/Author" in protected
    assert "LLM workflow caching implementation" in protected
    assert "KB execution-record exact parity" in tests
    assert "KB trigger-entry exact parity" in tests
    assert "ordering parity" in tests
    assert "no schema drift guard" in tests


def test_ag76c_bd_runtime_wires_completed_rt_helper_not_registry() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    post_author_source = (_ORCHESTRATOR_PATH.parent / "post_author_output_projection.py").read_text(encoding="utf-8")

    assert "pipeline_decision_registry" not in orchestrator_source
    assert "runtime_trace_export_attachment_handoff" not in orchestrator_source
    assert "attach_runtime_trace_export_compatibility_payloads(" in post_author_source
    assert "attach_passive_runtime_projection_traces(" not in orchestrator_source


def test_ag76c_bd_registry_code_does_not_call_protected_runtime_surfaces() -> None:
    tree = ast.parse(_REGISTRY_PATH.read_text(encoding="utf-8"))
    protected_import_fragments = (
        "author",
        "citation",
        "provider",
        "query",
        "classifier",
        "fit",
        "pipeline_orchestrator",
    )
    protected_call_names = {
        "ask_model",
        "build_final_answer",
        "select_providers",
        "process_search_queries",
        "source_classifier",
        "candidate_fit",
        "author_prompt",
        "citation_format",
        "citation_selection",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    fragment in alias.name.casefold()
                    for fragment in protected_import_fragments
                )
        if isinstance(node, ast.ImportFrom):
            module = (node.module or "").casefold()
            assert not any(fragment in module for fragment in protected_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in protected_call_names
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in protected_call_names
