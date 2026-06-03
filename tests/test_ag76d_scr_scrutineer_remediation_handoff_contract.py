from __future__ import annotations

import ast
import json
from pathlib import Path

from core.scrutineer_remediation_handoff_contract import (
    SCRUTINEER_REMEDIATION_HANDOFF_SCHEMA_VERSION,
    SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY,
    AuthorDirectiveKind,
    RemediationDispatchDescriptor,
    RemediationDispatchPosture,
    RemediationEvidenceDescriptor,
    RemediationFilterPosture,
    RemediationQueryDescriptor,
    RemediationResynthesisDescriptor,
    ResynthesisAdmissionPosture,
    ScrutineerAdmissionDescriptor,
    ScrutineerAuthorDirectiveDescriptor,
    ScrutineerFlagDescriptor,
    ScrutineerRemediationHandoffState,
    ScrutineerRunPosture,
)
from tests.static_import_guard_utils import assert_controller_contract_imports_closed

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "core" / "scrutineer_remediation_handoff_contract.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _state(**overrides):
    params = {
        "run_id": "run-scr",
        "admission": ScrutineerAdmissionDescriptor(
            eligible=True,
            run_gate="complexity_high_legacy_gate",
            complexity="high",
            mode_allowed=True,
            contract_allowed=True,
            requested=True,
            needed=True,
        ),
        "run_posture": ScrutineerRunPosture.COMPLETED,
        "flags": (
            ScrutineerFlagDescriptor(
                flag_id="flag-1",
                category="SINGLE-SOURCE",
                severity="high",
                challenge="Only one source supports the claim.",
                searchable=True,
                source_ids=("s1",),
            ),
            ScrutineerFlagDescriptor(
                flag_id="flag-2",
                category="STYLE",
                severity="medium",
                challenge="The claim needs a caveat.",
                searchable=False,
                source_ids=("s2",),
            ),
        ),
        "high_severity_flag_threshold": 5,
        "searchable_categories": ("SINGLE-SOURCE", "TEMPORAL DRIFT"),
        "non_searchable_categories": ("STYLE", "SCOPE"),
        "remediation_queries": (
            RemediationQueryDescriptor(
                query_id="rq-1",
                query_text="official topic update",
                source_flag_ids=("flag-1",),
                filter_posture=RemediationFilterPosture.ADMITTED,
                novelty_score=0.9,
            ),
            RemediationQueryDescriptor(
                query_id="rq-2",
                query_text="old searched topic",
                source_flag_ids=("flag-1",),
                filter_posture=RemediationFilterPosture.REJECTED_DUPLICATE,
                novelty_score=0.2,
                rejection_reason="overlap_gt_0_6",
            ),
        ),
        "dispatch": RemediationDispatchDescriptor(
            dispatch_posture=RemediationDispatchPosture.AUTHORIZED,
            authorized=True,
            provider_role="scrutineer_remediation",
            providers=("brave", "linkup"),
            search_depth="legacy_search_depth",
            linkup_depth_override="deep",
            results_per_query=5,
        ),
        "remediation_evidence": RemediationEvidenceDescriptor(
            evidence_ids=("ev-1", "ev-2"),
            source_ids=("s3", "s4"),
            urls=("https://official.example/rule", "https://news.example/context"),
            final_evidence_bundle_id="bundle-after-remediation",
            final_evidence_ref={"final_evidence_count": 4},
            evidence_count=2,
        ),
        "resynthesis": RemediationResynthesisDescriptor(
            posture=ResynthesisAdmissionPosture.TRIGGERED,
            reanalysis_triggered=True,
            trigger_reason="remediation_passages_added",
            analyst_pass_ref={"stage": "analyst_scrutineer_remediation"},
        ),
        "author_directives": (
            ScrutineerAuthorDirectiveDescriptor(
                directive_id="dir-hedge",
                kind=AuthorDirectiveKind.HEDGE,
                source_flag_ids=("flag-1",),
                hedge=True,
                metadata={"severity": "high"},
            ),
            ScrutineerAuthorDirectiveDescriptor(
                directive_id="dir-caveat",
                kind=AuthorDirectiveKind.CAVEAT,
                source_flag_ids=("flag-2",),
                caveat=True,
            ),
            ScrutineerAuthorDirectiveDescriptor(
                directive_id="dir-omit",
                kind=AuthorDirectiveKind.OMIT,
                source_flag_ids=("flag-2",),
                omit=True,
            ),
        ),
        "answer_contract_ref": {"trace_key": "answer_contract_fulfillment_handoff"},
        "analyst_author_handoff_ref": {"trace_key": "analyst_author_handoff_contract"},
        "citation_source_handoff_ref": {"trace_key": "citation_source_handoff_contract"},
    }
    params.update(overrides)
    return ScrutineerRemediationHandoffState(**params)


def test_run_gate_facts_are_represented_without_changing_scrutineer_behavior():
    state = _state()
    admission = state.to_controller_state()["admission"]

    assert admission["eligible"] is True
    assert admission["run_gate"] == "complexity_high_legacy_gate"
    assert admission["mode_allowed"] is True
    assert admission["contract_allowed"] is True
    assert admission["changes_scrutineer_behavior"] is False


def test_skipped_running_completed_posture_values_are_stable_json_safe():
    values = []
    for posture in ScrutineerRunPosture:
        state = _state(run_posture=posture)
        values.append(state.to_controller_state()["run_posture"])
        json.dumps(state.to_controller_state())

    assert values == ["skipped", "running", "completed"]


def test_high_flag_threshold_is_posture_not_hidden_authority():
    controller = _state().to_controller_state()

    assert controller["flag_posture"]["flag_count"] == 2
    assert controller["flag_posture"]["high_severity_flag_count"] == 1
    assert controller["flag_posture"]["high_severity_flag_threshold"] == 5
    assert controller["flag_posture"]["threshold_represents_posture_only"] is True
    assert not any(controller["no_behavior_change_flags"].values())


def test_searchable_category_filter_is_represented_without_changing_category_behavior():
    posture = _state().to_controller_state()["flag_posture"]

    assert posture["searchable_categories"] == ["SINGLE-SOURCE", "TEMPORAL DRIFT"]
    assert posture["non_searchable_categories"] == ["STYLE", "SCOPE"]
    assert posture["flags"][0]["searchable"] is True
    assert posture["flags"][1]["searchable"] is False
    assert posture["category_filter_represents_posture_only"] is True


def test_remediation_query_identity_preserves_originating_scrutineer_flag_ids():
    queries = _state().to_controller_state()["remediation_queries"]

    assert queries[0]["query_id"] == "rq-1"
    assert queries[0]["query_text"] == "official topic update"
    assert queries[0]["source_flag_ids"] == ["flag-1"]


def test_novelty_filter_outcome_is_represented_without_changing_query_filtering():
    queries = _state().to_controller_state()["remediation_queries"]

    assert queries[0]["filter_posture"] == "admitted"
    assert queries[1]["filter_posture"] == "rejected_duplicate"
    assert queries[1]["rejection_reason"] == "overlap_gt_0_6"
    assert queries[1]["changes_query_filtering_behavior"] is False


def test_provider_depth_facts_are_protected_already_computed_posture():
    controller = _state().to_controller_state()
    dispatch = controller["remediation_dispatch"]

    assert dispatch["provider_role"] == "scrutineer_remediation"
    assert dispatch["providers"] == ["brave", "linkup"]
    assert dispatch["search_depth"] == "legacy_search_depth"
    assert dispatch["linkup_depth_override"] == "deep"
    assert dispatch["protected_legacy_provider_depth_posture"] is True
    assert dispatch["changes_provider_search_depth_behavior"] is False
    assert controller["no_behavior_change_flags"]["provider_behavior_changed"] is False
    assert controller["no_behavior_change_flags"]["search_behavior_changed"] is False
    assert controller["no_behavior_change_flags"]["retrieval_behavior_changed"] is False


def test_remediation_evidence_identity_and_final_bundle_identity_survive():
    evidence = _state().to_controller_state()["remediation_evidence"]

    assert evidence["evidence_ids"] == ["ev-1", "ev-2"]
    assert evidence["source_ids"] == ["s3", "s4"]
    assert evidence["urls"] == ["https://official.example/rule", "https://news.example/context"]
    assert evidence["final_evidence_bundle_id"] == "bundle-after-remediation"
    assert evidence["final_evidence_ref"] == {"final_evidence_count": 4}


def test_resynthesis_admission_is_represented_without_rerunning_analyst():
    controller = _state().to_controller_state()
    resynthesis = controller["resynthesis"]

    assert resynthesis["posture"] == "triggered"
    assert resynthesis["reanalysis_triggered"] is True
    assert resynthesis["trigger_reason"] == "remediation_passages_added"
    assert resynthesis["analyst_pass_ref"] == {"stage": "analyst_scrutineer_remediation"}
    assert resynthesis["changes_analyst_behavior"] is False
    assert controller["no_behavior_change_flags"]["analyst_behavior_changed"] is False


def test_author_directive_identity_serializes_without_author_prompt_or_prose_change():
    controller = _state().to_controller_state()
    directives = controller["author_directives"]

    assert [item["kind"] for item in directives] == ["hedge", "caveat", "omit"]
    assert directives[0]["source_flag_ids"] == ["flag-1"]
    assert directives[0]["hedge"] is True
    assert directives[1]["caveat"] is True
    assert directives[2]["omit"] is True
    assert all(item["prompt_text_included"] is False for item in directives)
    assert all(item["changes_author_prompt_or_prose_behavior"] is False for item in directives)
    assert controller["no_behavior_change_flags"]["author_behavior_changed"] is False


def test_answer_contract_analyst_author_and_citation_source_refs_are_preserved():
    refs = _state().to_controller_state()["handoff_refs"]

    assert refs["answer_contract_ref"] == {"trace_key": "answer_contract_fulfillment_handoff"}
    assert refs["analyst_author_handoff_ref"] == {
        "trace_key": "analyst_author_handoff_contract"
    }
    assert refs["citation_source_handoff_ref"] == {
        "trace_key": "citation_source_handoff_contract"
    }


def test_json_safe_controller_and_trace_serialization_round_trip():
    state = _state()
    controller = state.to_controller_state()
    trace = state.to_trace_fragment()

    assert controller["schema_version"] == SCRUTINEER_REMEDIATION_HANDOFF_SCHEMA_VERSION
    assert SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY in trace
    assert json.loads(json.dumps(controller)) == controller
    assert json.loads(json.dumps(trace)) == trace


def test_static_protected_import_guard():
    assert_controller_contract_imports_closed(
        CONTRACT, allowed_core_modules={"core.controller_handoff_serialization"}
    )


def test_pipeline_orchestrator_touch_is_limited_to_runtime_handoff_adapter():
    source = PIPELINE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_names: set[str] = set()
    call_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.scrutineer_remediation_runtime_handoff":
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_names.append(node.func.id)

    assert imported_names == {
        "RuntimeRemediationQueryFact",
        "RuntimeScrutineerRemediationFacts",
        "runtime_scrutineer_remediation_trace_fragment",
    }
    assert call_names.count("runtime_scrutineer_remediation_trace_fragment") == 1
    assert call_names.count("RuntimeScrutineerRemediationFacts") == 1
    assert call_names.count("RuntimeRemediationQueryFact") == 1
    forbidden_terms = (
        "DEFAULT_SYSTEM[\"scrutineer\"] =",
        "DEFAULT_SYSTEM['scrutineer'] =",
        "overlap > 0.6" + " =",
        "linkup_depth_override=\"standard\"",
    )
    assert all(term not in source for term in forbidden_terms)
