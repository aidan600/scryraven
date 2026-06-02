from __future__ import annotations

import ast
import json
from pathlib import Path

from core.synthesis_evaluator_supplemental_search_handoff_contract import (
    SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY,
)
from core.synthesis_evaluator_supplemental_search_runtime_handoff import (
    RuntimeSupplementalQueryFact,
    RuntimeSynthesisEvaluatorSupplementalSearchFacts,
    build_runtime_synthesis_evaluator_supplemental_search_handoff,
    runtime_synthesis_evaluator_supplemental_search_trace_fragment,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "core" / "synthesis_evaluator_supplemental_search_runtime_handoff.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _payload(**overrides):
    facts = {
        "run_id": "run-ag76d-ses-r1",
        "eligible": True,
        "run_gate": "legacy_synthesis_evaluator_supplemental_search_gate",
        "completeness_posture": "insufficient",
        "requested": True,
        "sufficient_evidence_available": False,
        "deficiency_id": "synthesis-evaluator-deficiency",
        "deficiency_text": "missing official current value",
    }
    facts.update(overrides)
    state = build_runtime_synthesis_evaluator_supplemental_search_handoff(
        RuntimeSynthesisEvaluatorSupplementalSearchFacts(**facts)
    )
    return state.to_controller_state()


def test_runtime_handoff_represents_skipped_due_to_strong_retrieval() -> None:
    payload = _payload(
        eligible=True,
        completeness_posture="skipped",
        requested=True,
        sufficient_evidence_available=True,
        skip_reason="strong_retrieval_sufficient_no_supplemental_check",
        deficiency_id=None,
        deficiency_text=None,
    )

    assert payload["eligibility"]["skip_reason"] == "strong_retrieval_sufficient_no_supplemental_check"
    assert payload["completeness"]["posture"] == "skipped"
    assert payload["supplemental_search"]["admission_posture"] == "skipped"
    assert payload["supplemental_search"]["admitted"] is False
    assert payload["execution_envelope"]["runtime_wiring_active"] is True
    assert not any(payload["no_behavior_change_flags"].values())


def test_runtime_handoff_represents_sufficient_no_supplemental_search() -> None:
    payload = _payload(
        completeness_posture="sufficient",
        sufficient_evidence_available=True,
        deficiency_id=None,
        deficiency_text=None,
    )

    assert payload["completeness"]["posture"] == "sufficient"
    assert payload["supplemental_queries"] == []
    assert payload["supplemental_search"]["admission_posture"] == "skipped"
    assert payload["author_notes"] == []


def test_runtime_handoff_represents_insufficient_with_deficiency_and_queries() -> None:
    payload = _payload(
        supplemental_queries=(
            RuntimeSupplementalQueryFact(
                query_id="sq-1",
                query_text="official current value",
                source_evaluator_decision="insufficient",
                source_deficiency_id="synthesis-evaluator-deficiency",
                evaluator_decision_ref={"decision": "eval-1"},
            ),
        ),
        evaluator_decision_ref={"decision": "eval-1"},
    )

    assert payload["completeness"]["posture"] == "insufficient"
    assert payload["completeness"]["deficiency_text"] == "missing official current value"
    assert payload["supplemental_queries"][0]["query_id"] == "sq-1"
    assert payload["supplemental_queries"][0]["source_evaluator_decision"] == "insufficient"
    assert payload["supplemental_queries"][0]["source_deficiency_id"] == "synthesis-evaluator-deficiency"
    assert payload["supplemental_queries"][0]["evaluator_decision_ref"] == {"decision": "eval-1"}


def test_runtime_handoff_represents_parse_failed_without_behavior_change() -> None:
    payload = _payload(
        completeness_posture="parse_failed",
        deficiency_id=None,
        deficiency_text=None,
        parse_error_ref={"error_type": "JSONDecodeError", "behavior": "legacy_defaults_to_sufficient"},
    )

    assert payload["completeness"]["posture"] == "parse_failed"
    assert payload["completeness"]["parse_error_ref"]["error_type"] == "JSONDecodeError"
    assert payload["completeness"]["changes_evaluator_output"] is False


def test_supplemental_query_ids_and_source_refs_survive() -> None:
    payload = _payload(
        supplemental_queries=(
            RuntimeSupplementalQueryFact(
                query_text="agency update",
                evaluator_decision_ref={"decision_id": "eval-decision-1"},
            ),
        )
    )

    assert payload["supplemental_queries"][0]["query_id"] == "synthesis-evaluator-supplemental-query-1"
    assert payload["supplemental_queries"][0]["source_deficiency_id"] == "synthesis-evaluator-deficiency"
    assert payload["supplemental_queries"][0]["evaluator_decision_ref"] == {"decision_id": "eval-decision-1"}


def test_provider_list_depth_and_result_count_are_protected_legacy_posture() -> None:
    payload = _payload(
        supplemental_search_admission_posture="completed",
        supplemental_search_admitted=True,
        supplemental_search_admission_reason="insufficient_with_supplemental_queries",
        supplemental_provider_role="supplemental_search",
        supplemental_providers=("brave", "linkup", "brave"),
        supplemental_search_depth="deep",
        supplemental_results_per_query=3,
    )

    search = payload["supplemental_search"]
    assert search["admission_posture"] == "completed"
    assert search["provider_role"] == "supplemental_search"
    assert search["providers"] == ["brave", "linkup"]
    assert search["search_depth"] == "deep"
    assert search["results_per_query"] == 3
    assert search["protected_legacy_provider_depth_posture"] is True
    assert search["changes_provider_search_depth_behavior"] is False


def test_supplemental_evidence_identity_survives() -> None:
    payload = _payload(
        supplemental_evidence=(
            {"id": "sev-1", "source_id": "src-1", "url": "https://example.test/a"},
            {"id": "sev-2", "source_id": "src-2", "url": "https://example.test/b"},
        ),
        supplemental_evidence_ref={"delta_urls_supplemental": 2},
    )

    evidence = payload["supplemental_evidence"]
    assert evidence["evidence_ids"] == ["sev-1", "sev-2"]
    assert evidence["source_ids"] == ["src-1", "src-2"]
    assert evidence["urls"] == ["https://example.test/a", "https://example.test/b"]
    assert evidence["evidence_count"] == 2
    assert evidence["changes_retrieval_behavior"] is False


def test_final_evidence_rebuild_identity_survives() -> None:
    payload = _payload(
        final_evidence_bundle_id="run-ag76d-ses-r1:final_evidence",
        final_evidence=(
            {"id": "ev-1", "source_id": "src-1"},
            {"id": "ev-2", "source_id": "src-2"},
        ),
        final_evidence_ref={"final_evidence_count": 2},
        final_evidence_rebuild_reason="supplemental_evidence_added",
    )

    rebuild = payload["final_evidence_rebuild"]
    assert rebuild["final_evidence_bundle_id"] == "run-ag76d-ses-r1:final_evidence"
    assert rebuild["final_evidence_ids"] == ["ev-1", "ev-2"]
    assert rebuild["final_source_ids"] == ["src-1", "src-2"]
    assert rebuild["rebuild_reason"] == "supplemental_evidence_added"
    assert rebuild["changes_final_evidence_selection_behavior"] is False


def test_analyst_rerun_admission_is_represented_without_behavior_change() -> None:
    payload = _payload(
        analyst_rerun_posture="triggered",
        analyst_rerun_admitted=True,
        analyst_rerun_triggered=True,
        analyst_rerun_trigger_reason="supplemental_evidence_added",
        analyst_pass_ref={"stage": "analyst_supplemental"},
    )

    rerun = payload["analyst_rerun"]
    assert rerun["posture"] == "triggered"
    assert rerun["rerun_admitted"] is True
    assert rerun["rerun_triggered"] is True
    assert rerun["analyst_pass_ref"] == {"stage": "analyst_supplemental"}
    assert rerun["changes_analyst_behavior"] is False


def test_author_note_identity_is_represented_without_prompt_text() -> None:
    payload = _payload(
        author_hedge_note_emitted=True,
        author_note_ref={"source": "legacy_synthesis_evaluator_author_note"},
    )

    note = payload["author_notes"][0]
    assert note["identity"] == "hedge_appropriately_where_data_is_missing"
    assert note["hedge_where_data_missing"] is True
    assert note["prompt_text_included"] is False
    assert note["changes_author_prompt_or_prose_behavior"] is False


def test_handoff_refs_survive_where_available() -> None:
    payload = _payload(
        answer_contract_ref={"trace_key": "answer_contract_runtime_handoff"},
        analyst_author_handoff_ref={"trace_key": "analyst_author_handoff_contract"},
        citation_source_handoff_ref={"trace_key": "citation_source_handoff_contract"},
    )

    assert payload["handoff_refs"]["answer_contract_ref"] == {"trace_key": "answer_contract_runtime_handoff"}
    assert payload["handoff_refs"]["analyst_author_handoff_ref"] == {"trace_key": "analyst_author_handoff_contract"}
    assert payload["handoff_refs"]["citation_source_handoff_ref"] == {"trace_key": "citation_source_handoff_contract"}


def test_json_safe_trace_includes_stable_ses_handoff_key() -> None:
    trace = runtime_synthesis_evaluator_supplemental_search_trace_fragment(
        RuntimeSynthesisEvaluatorSupplementalSearchFacts(
            run_id="run-ag76d-ses-r1",
            eligible=True,
            run_gate="legacy_synthesis_evaluator_supplemental_search_gate",
            completeness_posture="sufficient",
        )
    )

    assert SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY in trace
    assert json.loads(json.dumps(trace)) == trace


def test_runtime_adapter_static_protected_import_guard() -> None:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    imported_modules = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    forbidden = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.model_clients",
        "core.persistence_side_effects",
    }
    assert not imported_modules.intersection(forbidden)


def test_pipeline_orchestrator_static_guard_only_tiny_adapter_trace_touch() -> None:
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    call_names: list[str] = []
    assigned_names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "core.synthesis_evaluator_supplemental_search_runtime_handoff"
        ):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.append(func.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id.startswith("synthesis_evaluator_supplemental_search")
                ):
                    assigned_names.add(target.id)

    assert imported_names == {
        "RuntimeSupplementalQueryFact",
        "RuntimeSynthesisEvaluatorSupplementalSearchFacts",
        "runtime_synthesis_evaluator_supplemental_search_trace_fragment",
    }
    assert call_names.count("runtime_synthesis_evaluator_supplemental_search_trace_fragment") == 1
    assert call_names.count("RuntimeSynthesisEvaluatorSupplementalSearchFacts") == 1
    assert call_names.count("RuntimeSupplementalQueryFact") == 1
    assert "synthesis_evaluator_supplemental_search_handoff_trace_fragment" in assigned_names
