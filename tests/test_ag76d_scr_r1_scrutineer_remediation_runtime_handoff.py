from __future__ import annotations

import ast
import json
from pathlib import Path

from core.scrutineer_remediation_handoff_contract import (
    SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY,
)
from core.scrutineer_remediation_runtime_handoff import (
    RuntimeRemediationQueryFact,
    RuntimeScrutineerRemediationFacts,
    build_runtime_scrutineer_remediation_handoff,
    runtime_scrutineer_remediation_trace_fragment,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
LEGACY_REVIEW_STAGE = ROOT / "core" / "legacy_review_runtime_stage.py"


def _payload(**overrides):
    facts = {
        "run_id": "run-ag76d-scr-r1",
        "eligible": True,
        "run_gate": "legacy_complexity_high_gate",
        "run_posture": "completed",
        "complexity": "high",
        "mode_allowed": True,
        "contract_allowed": True,
        "requested": True,
        "needed": True,
        "flags": (),
    }
    facts.update(overrides)
    state = build_runtime_scrutineer_remediation_handoff(
        RuntimeScrutineerRemediationFacts(**facts)
    )
    return state.to_controller_state()


def test_scrutineer_skipped_not_eligible_populates_passive_handoff() -> None:
    payload = _payload(
        eligible=False,
        run_posture="skipped",
        complexity="balanced",
        mode_allowed=False,
        contract_allowed=True,
        requested=False,
        needed=False,
        skip_reason="legacy_complexity_gate_not_high",
    )

    assert payload["admission"]["eligible"] is False
    assert payload["admission"]["skip_reason"] == "legacy_complexity_gate_not_high"
    assert payload["run_posture"] == "skipped"
    assert payload["flag_posture"]["flag_count"] == 0
    assert payload["remediation_dispatch"]["dispatch_posture"] == "skipped"
    assert payload["execution_envelope"]["runtime_wiring_active"] is True
    assert not any(payload["no_behavior_change_flags"].values())


def test_scrutineer_ran_with_no_flags_preserves_completed_no_remediation_posture() -> None:
    payload = _payload(flags=())

    assert payload["run_posture"] == "completed"
    assert payload["flag_posture"]["flag_count"] == 0
    assert payload["flag_posture"]["high_severity_flag_count"] == 0
    assert payload["remediation_queries"] == []
    assert payload["author_directives"] == []


def test_too_many_flags_pass_flags_directly_to_author_identity_only() -> None:
    flags = tuple(
        {"category": "SINGLE-SOURCE", "severity": "high", "challenge": f"gap {i}"}
        for i in range(5)
    )
    payload = _payload(flags=flags, pass_flags_directly_to_author=True)

    assert payload["flag_posture"]["flag_count"] == 5
    assert payload["flag_posture"]["high_severity_flag_threshold"] == 5
    assert payload["author_directives"][0]["kind"] == "pass_flags_directly"
    assert payload["author_directives"][0]["source_flag_ids"] == [
        "scrutineer-flag-1",
        "scrutineer-flag-2",
        "scrutineer-flag-3",
        "scrutineer-flag-4",
        "scrutineer-flag-5",
    ]
    assert payload["author_directives"][0]["prompt_text_included"] is False
    assert payload["author_directives"][0]["changes_author_prompt_or_prose_behavior"] is False


def test_searchable_high_severity_flags_admitted_for_remediation_are_represented() -> None:
    payload = _payload(
        flags=(
            {"id": "flag-a", "category": "SINGLE-SOURCE", "severity": "high"},
            {"id": "flag-b", "category": "TEMPORAL DRIFT", "severity": "high"},
        ),
        remediation_queries=(
            RuntimeRemediationQueryFact(
                query_id="rq-1",
                query_text="official update",
                source_flag_ids=("flag-a", "flag-b"),
                filter_posture="admitted",
            ),
        ),
        dispatch_authorized=True,
        dispatch_posture="authorized",
    )

    assert payload["flag_posture"]["searchable_categories"] == [
        "SINGLE-SOURCE",
        "TEMPORAL DRIFT",
    ]
    assert all(flag["searchable"] is True for flag in payload["flag_posture"]["flags"])
    assert payload["remediation_queries"][0]["source_flag_ids"] == ["flag-a", "flag-b"]
    assert payload["remediation_queries"][0]["filter_posture"] == "admitted"
    assert payload["remediation_dispatch"]["authorized"] is True


def test_non_searchable_flags_are_represented_but_not_admitted() -> None:
    payload = _payload(
        flags=(
            {"id": "flag-style", "category": "STYLE", "severity": "high"},
            {"id": "flag-medium", "category": "SINGLE-SOURCE", "severity": "medium"},
        )
    )

    assert payload["flag_posture"]["searchable_categories"] == []
    assert payload["flag_posture"]["non_searchable_categories"] == [
        "SINGLE-SOURCE",
        "STYLE",
    ]
    assert [flag["searchable"] for flag in payload["flag_posture"]["flags"]] == [False, False]
    assert payload["remediation_queries"] == []


def test_duplicate_and_non_novel_remediation_queries_are_rejected_without_policy_change() -> None:
    payload = _payload(
        remediation_queries=(
            RuntimeRemediationQueryFact(
                query_id="rq-dup",
                query_text="prior query",
                source_flag_ids=("flag-1",),
                filter_posture="rejected_duplicate",
                rejection_reason="overlap_gt_0_6",
            ),
            RuntimeRemediationQueryFact(
                query_id="rq-filtered",
                query_text="filtered query",
                source_flag_ids=("flag-1",),
                filter_posture="rejected_not_novel",
                rejection_reason="final_query_filter",
            ),
        )
    )

    assert [query["filter_posture"] for query in payload["remediation_queries"]] == [
        "rejected_duplicate",
        "rejected_not_novel",
    ]
    assert all(
        query["changes_query_filtering_behavior"] is False
        for query in payload["remediation_queries"]
    )


def test_provider_depth_and_linkup_override_facts_are_represented_only() -> None:
    payload = _payload(
        dispatch_authorized=True,
        dispatch_posture="completed",
        provider_role="scrutineer_remediation",
        providers=("brave", "linkup"),
        search_depth="standard",
        linkup_depth_override="deep",
    )

    dispatch = payload["remediation_dispatch"]
    assert dispatch["dispatch_posture"] == "completed"
    assert dispatch["provider_role"] == "scrutineer_remediation"
    assert dispatch["providers"] == ["brave", "linkup"]
    assert dispatch["search_depth"] == "standard"
    assert dispatch["linkup_depth_override"] == "deep"
    assert dispatch["protected_legacy_provider_depth_posture"] is True
    assert dispatch["changes_provider_search_depth_behavior"] is False


def test_remediation_evidence_and_resynthesis_admission_are_represented() -> None:
    payload = _payload(
        remediation_evidence=(
            {"id": "ev-1", "source_id": "src-1", "url": "https://example.test/a"},
            {"id": "ev-2", "source_id": "src-2", "url": "https://example.test/b"},
        ),
        final_evidence_bundle_id="run-ag76d-scr-r1:final_evidence",
        final_evidence_ref={"final_evidence_count": 4},
        resynthesis_posture="triggered",
        reanalysis_triggered=True,
        resynthesis_trigger_reason="remediation_passages_added",
        analyst_pass_ref={"stage": "analyst_scrutineer_remediation"},
    )

    evidence = payload["remediation_evidence"]
    assert evidence["evidence_ids"] == ["ev-1", "ev-2"]
    assert evidence["source_ids"] == ["src-1", "src-2"]
    assert evidence["final_evidence_bundle_id"] == "run-ag76d-scr-r1:final_evidence"
    assert payload["resynthesis"]["posture"] == "triggered"
    assert payload["resynthesis"]["reanalysis_triggered"] is True
    assert payload["resynthesis"]["changes_analyst_behavior"] is False


def test_author_directive_and_handoff_refs_are_identity_only() -> None:
    payload = _payload(
        flags=({"id": "flag-1", "category": "STYLE", "severity": "high"},),
        pass_flags_directly_to_author=True,
        answer_contract_ref={"trace_key": "answer_contract_runtime_handoff"},
        analyst_author_handoff_ref={"trace_key": "analyst_author_handoff_contract"},
        citation_source_handoff_ref={"trace_key": "citation_source_handoff_contract"},
    )

    assert payload["author_directives"][0]["kind"] == "pass_flags_directly"
    assert payload["author_directives"][0]["changes_author_prompt_or_prose_behavior"] is False
    assert payload["handoff_refs"]["answer_contract_ref"] == {
        "trace_key": "answer_contract_runtime_handoff"
    }
    assert payload["handoff_refs"]["analyst_author_handoff_ref"] == {
        "trace_key": "analyst_author_handoff_contract"
    }
    assert payload["handoff_refs"]["citation_source_handoff_ref"] == {
        "trace_key": "citation_source_handoff_contract"
    }


def test_json_safe_trace_includes_stable_scrutineer_remediation_handoff_key() -> None:
    trace = runtime_scrutineer_remediation_trace_fragment(
        RuntimeScrutineerRemediationFacts(
            run_id="run-ag76d-scr-r1",
            eligible=True,
            run_gate="legacy_complexity_high_gate",
            run_posture="completed",
        )
    )

    assert SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY in trace
    assert json.loads(json.dumps(trace)) == trace


def test_pipeline_orchestrator_static_guard_only_tiny_runtime_handoff_touch() -> None:
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8") + (PIPELINE.parent / "post_author_output_projection.py").read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    call_names: list[str] = []
    assigned_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.scrutineer_remediation_runtime_handoff":
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.append(func.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("scrutineer_remediation"):
                    assigned_names.add(target.id)

    helper_tree = ast.parse(LEGACY_REVIEW_STAGE.read_text(encoding="utf-8"))
    helper_call_names = [node.func.id for node in ast.walk(helper_tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert imported_names == {
        "RuntimeScrutineerRemediationFacts",
        "runtime_scrutineer_remediation_trace_fragment",
    }
    assert call_names.count("runtime_scrutineer_remediation_trace_fragment") == 1
    assert call_names.count("RuntimeScrutineerRemediationFacts") == 1
    assert helper_call_names.count("RuntimeRemediationQueryFact") == 1
    assert "scrutineer_remediation_handoff_trace_fragment" in assigned_names
