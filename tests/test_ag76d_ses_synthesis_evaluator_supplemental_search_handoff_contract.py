import ast
import json
from pathlib import Path

from tests.static_import_guard_utils import assert_controller_contract_imports_closed

from core.synthesis_evaluator_supplemental_search_handoff_contract import (
    SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_SCHEMA_VERSION,
    SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY,
    AnalystRerunAdmissionPosture,
    AnalystRerunDescriptor,
    AuthorNoteDescriptor,
    AuthorNoteIdentity,
    CompletenessEvaluationDescriptor,
    CompletenessPosture,
    FinalEvidenceRebuildDescriptor,
    SupplementalEvidenceDescriptor,
    SupplementalQueryDescriptor,
    SupplementalSearchAdmissionPosture,
    SupplementalSearchDescriptor,
    SynthesisEvaluatorRunEligibilityDescriptor,
    SynthesisEvaluatorSupplementalSearchHandoffState,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "core" / "synthesis_evaluator_supplemental_search_handoff_contract.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _state(**overrides):
    params = {
        "run_id": "run-ses",
        "eligibility": SynthesisEvaluatorRunEligibilityDescriptor(
            eligible=True,
            run_gate="legacy_synthesis_evaluator_gate",
            requested=True,
            sufficient_evidence_available=False,
        ),
        "completeness": CompletenessEvaluationDescriptor(
            posture=CompletenessPosture.INSUFFICIENT,
            deficiency_id="def-1",
            deficiency_text="missing official current rate data",
            evaluator_decision_ref={"decision_id": "eval-decision-1"},
            raw_evaluator_output_ref={"output_hash": "abc123"},
        ),
        "supplemental_queries": (
            SupplementalQueryDescriptor(
                query_id="sq-1",
                query_text="official current rate data",
                source_evaluator_decision="supplemental_search_needed",
                source_deficiency_id="def-1",
                evaluator_decision_ref={"decision_id": "eval-decision-1"},
            ),
            SupplementalQueryDescriptor(
                query_id="sq-2",
                query_text="agency data update",
                source_evaluator_decision="supplemental_search_needed",
                source_deficiency_id="def-1",
            ),
        ),
        "supplemental_search": SupplementalSearchDescriptor(
            admission_posture=SupplementalSearchAdmissionPosture.ADMITTED,
            admitted=True,
            admission_reason="insufficient_completeness",
            provider_role="synthesis_evaluator_supplemental",
            providers=("brave", "linkup"),
            search_depth="legacy_supplemental_depth",
            results_per_query=3,
        ),
        "supplemental_evidence": SupplementalEvidenceDescriptor(
            evidence_ids=("sev-1", "sev-2"),
            source_ids=("s1", "s2"),
            urls=("https://official.example/rate", "https://agency.example/data"),
            evidence_count=2,
            evidence_ref={"supplemental_evidence_count": 2},
        ),
        "final_evidence_rebuild": FinalEvidenceRebuildDescriptor(
            final_evidence_bundle_id="bundle-after-ses",
            final_evidence_ids=("ev-0", "sev-1", "sev-2"),
            final_source_ids=("s0", "s1", "s2"),
            final_evidence_ref={"final_evidence_count": 3},
            rebuild_reason="supplemental_evidence_added",
        ),
        "analyst_rerun": AnalystRerunDescriptor(
            posture=AnalystRerunAdmissionPosture.TRIGGERED,
            rerun_admitted=True,
            rerun_triggered=True,
            trigger_reason="final_evidence_rebuilt",
            analyst_pass_ref={"stage": "analyst_after_supplemental_search"},
        ),
        "author_notes": (
            AuthorNoteDescriptor(
                note_id="note-hedge-missing-data",
                identity=AuthorNoteIdentity.HEDGE_WHERE_DATA_MISSING,
                source_deficiency_id="def-1",
                hedge_where_data_missing=True,
                note_ref={"legacy_note_id": "author-note-1"},
            ),
        ),
        "answer_contract_ref": {"trace_key": "answer_contract_fulfillment_handoff"},
        "analyst_author_handoff_ref": {"trace_key": "analyst_author_handoff_contract"},
        "citation_source_handoff_ref": {"trace_key": "citation_source_handoff_contract"},
    }
    params.update(overrides)
    return SynthesisEvaluatorSupplementalSearchHandoffState(**params)


def test_evaluator_skipped_sufficient_insufficient_parse_failed_posture_is_represented():
    postures = []
    for posture in CompletenessPosture:
        state = _state(completeness=CompletenessEvaluationDescriptor(posture=posture))
        postures.append(state.to_controller_state()["completeness"]["posture"])
        json.dumps(state.to_controller_state())

    assert postures == ["skipped", "sufficient", "insufficient", "parse_failed"]


def test_run_gate_and_deficiency_identity_are_represented_without_evaluator_output_change():
    controller = _state().to_controller_state()

    assert controller["eligibility"]["eligible"] is True
    assert controller["eligibility"]["run_gate"] == "legacy_synthesis_evaluator_gate"
    assert controller["eligibility"]["changes_evaluator_behavior"] is False
    assert controller["completeness"]["deficiency_id"] == "def-1"
    assert controller["completeness"]["deficiency_text"] == "missing official current rate data"
    assert controller["completeness"]["evaluator_decision_ref"] == {
        "decision_id": "eval-decision-1"
    }
    assert controller["completeness"]["changes_evaluator_output"] is False


def test_supplemental_query_ids_and_source_evaluator_decision_are_preserved():
    queries = _state().to_controller_state()["supplemental_queries"]

    assert [query["query_id"] for query in queries] == ["sq-1", "sq-2"]
    assert queries[0]["query_text"] == "official current rate data"
    assert queries[0]["source_evaluator_decision"] == "supplemental_search_needed"
    assert queries[0]["source_deficiency_id"] == "def-1"
    assert queries[0]["changes_query_generation_behavior"] is False


def test_supplemental_search_admission_provider_and_depth_are_protected_legacy_posture():
    controller = _state().to_controller_state()
    search = controller["supplemental_search"]

    assert search["admission_posture"] == "admitted"
    assert search["admitted"] is True
    assert search["provider_role"] == "synthesis_evaluator_supplemental"
    assert search["providers"] == ["brave", "linkup"]
    assert search["search_depth"] == "legacy_supplemental_depth"
    assert search["protected_legacy_provider_depth_posture"] is True
    assert search["changes_provider_search_depth_behavior"] is False
    assert controller["no_behavior_change_flags"]["provider_behavior_changed"] is False
    assert controller["no_behavior_change_flags"]["search_behavior_changed"] is False
    assert controller["no_behavior_change_flags"]["retrieval_behavior_changed"] is False


def test_supplemental_evidence_identity_is_represented():
    evidence = _state().to_controller_state()["supplemental_evidence"]

    assert evidence["evidence_ids"] == ["sev-1", "sev-2"]
    assert evidence["source_ids"] == ["s1", "s2"]
    assert evidence["urls"] == ["https://official.example/rate", "https://agency.example/data"]
    assert evidence["evidence_ref"] == {"supplemental_evidence_count": 2}
    assert evidence["changes_retrieval_behavior"] is False


def test_final_evidence_rebuild_identity_is_represented_without_selection_change():
    rebuild = _state().to_controller_state()["final_evidence_rebuild"]

    assert rebuild["final_evidence_bundle_id"] == "bundle-after-ses"
    assert rebuild["final_evidence_ids"] == ["ev-0", "sev-1", "sev-2"]
    assert rebuild["final_source_ids"] == ["s0", "s1", "s2"]
    assert rebuild["final_evidence_ref"] == {"final_evidence_count": 3}
    assert rebuild["changes_final_evidence_selection_behavior"] is False


def test_analyst_rerun_admission_is_represented_without_rerunning_analyst():
    controller = _state().to_controller_state()
    rerun = controller["analyst_rerun"]

    assert rerun["posture"] == "triggered"
    assert rerun["rerun_admitted"] is True
    assert rerun["rerun_triggered"] is True
    assert rerun["analyst_pass_ref"] == {"stage": "analyst_after_supplemental_search"}
    assert rerun["changes_analyst_behavior"] is False
    assert controller["no_behavior_change_flags"]["analyst_behavior_changed"] is False


def test_author_note_identity_is_represented_without_changing_author_prose():
    controller = _state().to_controller_state()
    notes = controller["author_notes"]

    assert notes[0]["identity"] == "hedge_appropriately_where_data_is_missing"
    assert notes[0]["source_deficiency_id"] == "def-1"
    assert notes[0]["hedge_where_data_missing"] is True
    assert notes[0]["prompt_text_included"] is False
    assert notes[0]["changes_author_prompt_or_prose_behavior"] is False
    assert controller["no_behavior_change_flags"]["author_prose_behavior_changed"] is False


def test_handoff_refs_are_preserved_where_available():
    refs = _state().to_controller_state()["handoff_refs"]

    assert refs["answer_contract_ref"] == {"trace_key": "answer_contract_fulfillment_handoff"}
    assert refs["analyst_author_handoff_ref"] == {
        "trace_key": "analyst_author_handoff_contract"
    }
    assert refs["citation_source_handoff_ref"] == {"trace_key": "citation_source_handoff_contract"}


def test_json_safe_controller_and_trace_serialization_round_trip():
    state = _state()
    controller = state.to_controller_state()
    trace = state.to_trace_fragment()

    assert controller["schema_version"] == (
        SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_SCHEMA_VERSION
    )
    assert SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY in trace
    assert controller["execution_envelope"]["runtime_wiring_active"] is False
    assert not any(controller["no_behavior_change_flags"].values())
    assert json.loads(json.dumps(controller)) == controller
    assert json.loads(json.dumps(trace)) == trace


def test_static_protected_import_guard():
    assert_controller_contract_imports_closed(
        CONTRACT, allowed_core_modules={"core.controller_handoff_serialization"}
    )


def test_static_guard_pipeline_orchestrator_only_has_runtime_adapter_touch():
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    call_names: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "core.synthesis_evaluator_supplemental_search_runtime_handoff"
        ):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_names.append(node.func.id)

    assert imported_names == {"RuntimeSynthesisEvaluatorSupplementalSearchFactCollector"}
    assert call_names.count("RuntimeSynthesisEvaluatorSupplementalSearchFactCollector") == 1
    assert call_names.count("RuntimeSynthesisEvaluatorSupplementalSearchFacts") == 0
    assert call_names.count("RuntimeSupplementalQueryFact") == 0
