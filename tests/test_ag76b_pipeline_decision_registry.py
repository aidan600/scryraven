from __future__ import annotations

import ast
from pathlib import Path

from core.pipeline_decision_registry import (
    FINAL_EVIDENCE_BUNDLE_DECISION,
    FINAL_EVIDENCE_REPLACEMENT_CONTRACT,
    NEXT_EXTRACTION_PHASE,
    NEXT_EXTRACTION_RECOMMENDATION,
    PIPELINE_DECISION_REGISTRY,
    PROTECTED_FINAL_EVIDENCE_SURFACES,
    SOURCE_ID_ASSIGNMENT_DECISION,
    registry_entry,
)

_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY_PATH = _ROOT / "core" / "pipeline_decision_registry.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def test_ag76b_registry_includes_final_evidence_bundle_construction() -> None:
    entry = registry_entry(FINAL_EVIDENCE_BUNDLE_DECISION)

    assert entry.decision_name == "final_evidence_bundle_construction"
    assert "pipeline_orchestrator.py" in entry.current_location
    assert entry.current_owner
    assert entry.target_owner == "core.final_evidence_bundle_builder"
    assert entry.priority == "P0"


def test_ag76b_registry_includes_source_id_assignment_owner_map() -> None:
    entry = registry_entry(SOURCE_ID_ASSIGNMENT_DECISION)

    assert entry.decision_name == "source_id_assignment"
    assert "source ID" in entry.current_owner
    assert entry.target_owner == "core.final_evidence_bundle_builder"
    assert "assign_stable_source_ids" in entry.executor_helper
    assert entry.current_test_coverage


def test_ag76b_registry_marks_final_answer_author_and_citation_surfaces_protected() -> None:
    protected = set(PROTECTED_FINAL_EVIDENCE_SURFACES)
    final_entry = registry_entry(FINAL_EVIDENCE_BUNDLE_DECISION)
    source_id_entry = registry_entry(SOURCE_ID_ASSIGNMENT_DECISION)

    assert "final_answer_prose" in protected
    assert "Author_behavior" in protected
    assert "citation_formatting" in protected
    assert "citation_selection" in protected
    assert "final_answer_prose" in final_entry.protected_surface_risk
    assert "Author_behavior" in source_id_entry.protected_surface_risk
    assert "citation_formatting" in source_id_entry.protected_surface_risk
    assert "citation_selection" in source_id_entry.protected_surface_risk


def test_ag76b_registry_recommends_ag76c_fe_as_next_extraction() -> None:
    assert NEXT_EXTRACTION_PHASE == "AG-76C-FE"
    assert NEXT_EXTRACTION_RECOMMENDATION == (
        "AG-76C-FE - Final Evidence Bundle / Source-ID Assignment Replacement Extraction"
    )
    assert all(
        NEXT_EXTRACTION_PHASE in entry.next_action
        or entry.deletion_or_extraction_status != "blueprint_only_ag76b_extract_next"
        for entry in PIPELINE_DECISION_REGISTRY
    )
    assert FINAL_EVIDENCE_REPLACEMENT_CONTRACT.replacement_owner_module == (
        "core.final_evidence_bundle_builder"
    )


def test_ag76b_replacement_contract_names_required_parity_surfaces() -> None:
    contract = FINAL_EVIDENCE_REPLACEMENT_CONTRACT
    required = set(contract.required_parity_tests)

    assert any("source ID parity" in item for item in required)
    assert any("ordered_sources parity" in item for item in required)
    assert any("evidence_block" in item for item in required)
    assert any("author_evidence" in item for item in required)
    assert any("runtime trace projection/export parity" in item for item in required)
    assert "Author prompt placement" in contract.author_handoff_boundary
    assert "do not select final evidence" in contract.trace_export_observer_boundary
    assert "change citation behavior" in contract.trace_export_observer_boundary


def test_ag76b_registry_code_does_not_import_or_call_protected_runtime_surfaces() -> None:
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


def test_ag76b_does_not_wire_registry_into_pipeline_orchestrator_runtime() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "pipeline_decision_registry" not in orchestrator_source
    assert "build_final_evidence_bundle" in orchestrator_source
