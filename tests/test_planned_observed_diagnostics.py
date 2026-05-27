from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.planned_observed_diagnostics import (
    PlannedObservedDiagnostics,
    build_controller_diagnostics_payload,
    build_task_ledger_from_trace,
    compare_run_plan_to_observed_trace,
)
from core.run_plan import build_run_plan
from core.task_ledger import TaskStatus
from tests.controller_diagnostics_contract_utils import (
    ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY,
    assert_execution_trace_payload_contract,
    assert_jsonl_event_controller_payload_contract,
    assert_no_top_level_controller_payload,
    assert_trace_key_delta_only_controller_diagnostics,
    trace_key_delta,
)
from tests.test_source_class_recovery_trace import _run_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = _ROOT / "core" / "planned_observed_diagnostics.py"

RAW_AUTHOR_MARKERS = (
    "quantitative_packet",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "QUANTITATIVE FRAMEWORK",
    "ECONOMIST FRAMEWORK",
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
)

RAW_PAYLOAD_LEAK_MARKERS = (
    "RAW_PROMPT_SHOULD_NOT_LEAK_19C",
    "RAW_EVIDENCE_SHOULD_NOT_LEAK_19C",
    "PROVIDER_DIAGNOSTICS_LIST_SHOULD_NOT_LEAK_19C",
    "FULL_CONTEXT_MEASUREMENT_SHOULD_NOT_LEAK_19C",
    "QUANT_PACKET_SHOULD_NOT_LEAK_19C",
    "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_19C",
    "FINAL_OUTPUT_PREVIEW_SHOULD_NOT_LEAK_19C",
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _trace(
    *,
    mode: str = "Balanced",
    complexity: str = "medium",
    report_type: str = "general_research",
    query_type: str = "other",
    analyst_model_called: bool = True,
    analyst_skipped: bool = False,
    context_stages: tuple[str, ...] = ("router", "researcher", "analyst", "author"),
    **overrides: Any,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "mode": mode,
        "complexity": complexity,
        "intent": "general",
        "report_type": report_type,
        "query_type": query_type,
        "primary_entity": "Care Program",
        "entities": ["Care Program"],
        "routing_override_applied": False,
        "router_entity_retry_used": False,
        "queries_per_iteration": {"1": ["Care Program eligibility"]},
        "iterations_run": 1,
        "pass_providers": [["tavily"]],
        "provider_diagnostics": [
            {
                "schema_version": "provider_diagnostics_v1",
                "provider": "tavily",
                "provider_role": "main_retrieval",
                "success": True,
                "result_count": 4,
            }
        ],
        "provider_attempts_by_role": {"main_retrieval": 1},
        "urls_fetched": 4,
        "total_chunks": 4,
        "corpus_weak": False,
        "analyst_model_called": analyst_model_called,
        "analyst_skipped": analyst_skipped,
        "analyst_skip_reason": "corpus_off_topic" if analyst_skipped else None,
        "analyst_skipped_after_economist": False,
        "economist_output_used_as_analysis": False,
        "economist_ran": False,
        "economist_preflight_allowed": None,
        "supplemental_ran": False,
        "synth_was_insufficient": False,
        "synth_sufficient_first_pass": True,
        "scrutineer_ran": False,
        "scrutineer_flag_count": 0,
        "author_system_prompt_key": "author",
        "author_quant_content_source": "none",
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
        "author_quant_handoff_gate_reason": "no_quantitative_author_handoff_detected",
        "output_word_count": 24,
        "final_output_preview": "Care Program answer.",
        "context_measurement": {
            "available": True,
            "stages": {name: {"prompt_hash": "a" * 16} for name in context_stages},
        },
    }
    trace.update(overrides)
    return trace


def _plan_for(trace: dict[str, Any]):
    return build_run_plan(
        mode=trace["mode"],
        routing_metadata={
            "intent": trace.get("intent"),
            "report_type": trace.get("report_type"),
            "query_type": trace.get("query_type"),
        },
    )


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") == "execution":
            return row
    raise AssertionError("execution event not found")


def _stage(
    diagnostics: PlannedObservedDiagnostics,
    stage_id: str,
) -> dict[str, Any]:
    return {
        stage["stage_id"]: stage
        for stage in diagnostics.to_dict()["stages"]
    }[stage_id]


def _payload_stage(payload: dict[str, Any], stage_id: str) -> dict[str, Any]:
    return {
        stage["stage_id"]: stage
        for stage in payload["planned_vs_observed"]["stages"]
    }[stage_id]


def _payload_size_bytes(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8"))


def _assert_controller_payload_base_contract(payload: dict[str, Any]) -> None:
    assert payload["schema_version"] == "controller_diagnostics_v1"
    assert payload["passive_only"] is True
    assert payload["diagnostic_only"] is True
    assert payload["authority"] == "none"
    assert payload["source"] == "posthoc_execution_trace"
    assert _payload_size_bytes(payload) < 8 * 1024


def test_planned_observed_static_import_guard() -> None:
    tree = ast.parse(_HELPER_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.pipeline_orchestrator",
        "core.db",
        "core.prompts",
        "core.routing",
        "core.storage",
        "core.ui",
        "ui",
        "replay",
        "summarizer",
        "aggregate",
        "core.provider_diagnostics",
        "core.search_providers",
        "core.retrieval",
        "core.source_class_recovery",
        "core.source_class_recovery_lifecycle",
        "core.source_class_recovery_executor",
        "core.weak_corpus_recovery",
    )
    forbidden_function_prefixes = (
        "dispatch",
        "execute",
        "recover",
        "retry",
        "route",
        "select",
        "loop",
    )

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    violations = [
        name
        for name in imports
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    active_function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_function_prefixes)
    ]
    assert violations == []
    assert active_function_names == []


def test_controller_diagnostics_payload_shape_schema_and_authority() -> None:
    payload = build_controller_diagnostics_payload(_trace())

    _assert_controller_payload_base_contract(payload)
    assert payload["mode_policy"]["mode"] == "Balanced"
    assert payload["run_plan"]["stage_count"] == 10
    assert payload["run_plan"]["items"][0] == {
        "stage_id": "route_intent",
        "module_id": "router",
        "disposition": "required",
        "dependencies": [],
    }
    assert payload["task_ledger"]["record_count"] > 0
    assert payload["planned_vs_observed"]["failure_count"] == 0
    assert payload["observed_summary"]["observed_stage_count"] > 0


def test_controller_diagnostics_payload_is_compact_and_omits_raw_material() -> None:
    trace = _trace(
        provider_diagnostics=[
            {
                "schema_version": "provider_diagnostics_v1",
                "provider": "tavily",
                "provider_role": "main_retrieval",
                "query_preview": "PROVIDER_DIAGNOSTICS_LIST_SHOULD_NOT_LEAK_19C",
                "success": True,
            }
        ],
        context_measurement={
            "available": True,
            "stages": {
                "router": {
                    "prompt_hash": "FULL_CONTEXT_MEASUREMENT_SHOULD_NOT_LEAK_19C"
                },
                "researcher": {"prompt_hash": "b" * 64},
                "analyst": {"prompt_hash": "c" * 64},
                "author": {"prompt_hash": "d" * 64},
            },
        },
        raw_prompt="RAW_PROMPT_SHOULD_NOT_LEAK_19C",
        evidence=[{"text": "RAW_EVIDENCE_SHOULD_NOT_LEAK_19C"}],
        passages=[{"text": "RAW_EVIDENCE_SHOULD_NOT_LEAK_19C"}],
        top_passages=[{"text": "RAW_EVIDENCE_SHOULD_NOT_LEAK_19C"}],
        quantitative_packet={"marker": "QUANT_PACKET_SHOULD_NOT_LEAK_19C"},
        economist_v1={"marker": "ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_19C"},
        economist_framework="ECONOMIST_FRAMEWORK_SHOULD_NOT_LEAK_19C",
        final_output_preview=(
            "FINAL_OUTPUT_PREVIEW_SHOULD_NOT_LEAK_19C" + ("x" * 2000)
        ),
    )

    payload = build_controller_diagnostics_payload(trace)
    encoded = json.dumps(payload, sort_keys=True)

    assert _payload_size_bytes(payload) < 8 * 1024
    assert _payload_size_bytes(payload) < 12 * 1024
    for forbidden_key in (
        "raw_prompt",
        "evidence",
        "passages",
        "top_passages",
        "provider_diagnostics",
        "context_measurement",
        "quantitative_packet",
        "economist_v1",
        "economist_framework",
        "final_output_preview",
    ):
        assert forbidden_key not in encoded
    for marker in RAW_PAYLOAD_LEAK_MARKERS:
        assert marker not in encoded


def test_controller_diagnostics_size_guard_falls_back_to_stage_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_build_payload(
        _trace_payload: dict[str, Any],
        *,
        include_stage_items: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        calls.append(include_stage_items)
        if include_stage_items:
            return {
                "schema_version": "controller_diagnostics_v1",
                "run_plan": {"items": [{"stage_id": "x" * 9000}]},
                "planned_vs_observed": {"stages": [{"stage_id": "y" * 9000}]},
            }
        return {
            "schema_version": "controller_diagnostics_v1",
            "run_plan": {"items": []},
            "planned_vs_observed": {"stages": []},
        }

    monkeypatch.setattr(
        orchestrator,
        "build_controller_diagnostics_payload",
        fake_build_payload,
    )

    payload = orchestrator._build_controller_diagnostics_payload_with_size_guard({})

    assert calls == [True, False]
    assert payload is not None
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    assert payload["run_plan"]["items"] == []
    assert payload["planned_vs_observed"]["stages"] == []
    assert len(encoded) <= 12 * 1024


def test_controller_diagnostics_size_guard_omits_oversized_compact_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_build_payload(
        _trace_payload: dict[str, Any],
        *,
        include_stage_items: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        calls.append(include_stage_items)
        return {
            "schema_version": "controller_diagnostics_v1",
            "oversized": "z" * (13 * 1024),
        }

    monkeypatch.setattr(
        orchestrator,
        "build_controller_diagnostics_payload",
        fake_build_payload,
    )

    assert orchestrator._build_controller_diagnostics_payload_with_size_guard({}) is None
    assert calls == [True, False]


def test_controller_diagnostics_size_guard_omits_builder_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_build_payload(
        _trace_payload: dict[str, Any],
        *,
        include_stage_items: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        calls.append(include_stage_items)
        raise RuntimeError("synthetic controller diagnostics failure")

    monkeypatch.setattr(
        orchestrator,
        "build_controller_diagnostics_payload",
        fake_build_payload,
    )

    assert orchestrator._build_controller_diagnostics_payload_with_size_guard({}) is None
    assert calls == [True]


def test_controller_diagnostics_oversized_payload_is_not_written_to_runtime_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_build_payload(
        _trace_payload: dict[str, Any],
        *,
        include_stage_items: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "schema_version": "controller_diagnostics_v1",
            "oversized": "z" * (13 * 1024),
            "include_stage_items": include_stage_items,
        }

    monkeypatch.setattr(
        orchestrator,
        "build_controller_diagnostics_payload",
        fake_build_payload,
    )

    outcome, _harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in outcome.execution_trace
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in log_entry
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in log_entry["execution_trace"]
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in outcome.new_session
    assert (
        ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY
        not in outcome.new_session["execution_trace"]
    )


def test_controller_diagnostics_payload_is_mutation_safe() -> None:
    trace = _trace()
    plan = _plan_for(trace)
    ledger = build_task_ledger_from_trace(trace, run_plan=plan)
    payload = build_controller_diagnostics_payload(
        trace,
        run_plan=plan,
        task_ledger=ledger,
    )
    snapshot = deepcopy(payload)

    trace["queries_per_iteration"]["1"].append("late mutation")
    trace["provider_diagnostics"][0]["provider_role"] = "mutated"
    object.__setattr__(plan, "routing_metadata", (("intent", "mutated"),))
    object.__setattr__(ledger, "records", ())

    assert payload == snapshot


def test_controller_payload_representative_trace_quality_matrix() -> None:
    cases = (
        (
            "fast_direct_to_author",
            _trace(
                mode="Fast",
                complexity="low",
                analyst_model_called=False,
                context_stages=("router", "researcher", "author"),
            ),
            {
                "author": "observed_completed",
                "analyst_review": "blocked_by_mode",
                "weak_corpus_recovery": "blocked_by_mode",
                "source_class_recovery": "may_run_not_observed",
                "economist_preflight": "not_applicable",
                "scrutineer": "blocked_by_mode",
            },
        ),
        (
            "balanced_healthy",
            _trace(),
            {
                "route_intent": "observed_completed",
                "researcher_queries": "observed_completed",
                "main_retrieval": "observed_completed",
                "weak_corpus_recovery": "may_run_not_observed",
                "source_class_recovery": "may_run_not_observed",
                "supplemental_retrieval": "optional_not_observed",
                "economist_preflight": "not_applicable",
                "scrutineer": "blocked_by_mode",
            },
        ),
        (
            "fast_weak_corpus_budget_blocked",
            _trace(
                mode="Fast",
                complexity="low",
                analyst_model_called=False,
                context_stages=("router", "researcher", "author"),
                corpus_weak=True,
                weak_corpus_recovery_considered=True,
                weak_corpus_recovery_used=False,
                weak_corpus_recovery_skip_reason="max_iterations_1",
                weak_corpus_recovery_queries=[],
                active_source_class_recovery_considered=True,
                active_source_class_recovery_eligible=False,
                active_source_class_recovery_used=False,
                active_source_class_recovery_skip_reason=(
                    "blocked_by_weak_corpus_recovery"
                ),
                active_source_class_recovery_blockers=[
                    "blocked_by_weak_corpus_recovery"
                ],
                active_source_class_recovery_queries=[],
                active_source_class_recovery_result_count=0,
                active_source_class_recovery_new_url_count=0,
                active_source_class_recovery_provider_role=None,
                active_source_class_recovery_attempt_count=0,
            ),
            {
                "weak_corpus_recovery": "observed_blocked",
                "source_class_recovery": "may_run_not_observed",
                "analyst_review": "blocked_by_mode",
                "scrutineer": "blocked_by_mode",
            },
        ),
        (
            "balanced_source_class_recovery",
            _trace(
                active_source_class_recovery_considered=True,
                active_source_class_recovery_eligible=True,
                active_source_class_recovery_used=True,
                active_source_class_recovery_skip_reason=None,
                active_source_class_recovery_blockers=[],
                active_source_class_recovery_missing_classes=[
                    "official_current_rules"
                ],
                active_source_class_recovery_queries=[
                    "Care Program official rules"
                ],
                active_source_class_recovery_result_count=1,
                active_source_class_recovery_new_url_count=1,
                active_source_class_recovery_provider_role="source_class_recovery",
                active_source_class_recovery_search_depth="basic",
                active_source_class_recovery_attempt_count=1,
                source_class_recovery_recommended=True,
                source_class_recovery_shadow_mode=True,
                missing_expected_source_classes=["official_current_rules"],
                source_class_recovery_queries=["Care Program official rules"],
                source_class_recovery_query_count=1,
                provider_attempts_by_role={
                    "main_retrieval": 1,
                    "source_class_recovery": 1,
                },
                provider_diagnostics=[
                    {
                        "provider": "tavily",
                        "provider_role": "main_retrieval",
                        "success": True,
                    },
                    {
                        "provider": "tavily",
                        "provider_role": "source_class_recovery",
                        "success": True,
                    },
                ],
            ),
            {
                "weak_corpus_recovery": "may_run_not_observed",
                "source_class_recovery": "observed_completed",
            },
        ),
        (
            "balanced_quantitative_economist_shadow",
            _trace(
                report_type="quantitative_comparison",
                query_type="quantitative_comparison",
                economist_ran=True,
                economist_preflight_allowed=True,
                economist_safety_status="code_execution_disabled",
                economist_schema_version="economist_v1",
                economist_schema_valid=True,
                economist_pre_analyst_skip_candidate_shadow=True,
                economist_pre_analyst_skip_candidate_gate_reason=(
                    "candidate_shadow_only"
                ),
                analyst_model_called=True,
                analyst_skipped=False,
                analyst_skipped_after_economist=False,
                economist_output_used_as_analysis=False,
                author_quant_content_source="analyst_reviewed",
                author_received_raw_quant_packet=False,
                author_received_economist_framework=False,
                author_received_analyst_packet_marker=False,
                author_quant_handoff_gate_reason=(
                    "author_received_analyst_reviewed_quantitative_synthesis"
                ),
                context_stages=(
                    "router",
                    "researcher",
                    "economist_preflight",
                    "analyst",
                    "author",
                ),
            ),
            {
                "economist_preflight": "observed_completed",
                "analyst_review": "observed_completed",
                "source_class_recovery": "may_run_not_observed",
            },
        ),
        (
            "deep_scrutineer_dependency_blocked",
            _trace(
                mode="Deep",
                complexity="high",
                analyst_model_called=False,
                analyst_skipped=True,
                post_retrieval_fast_path_used=True,
                context_stages=("router", "researcher", "author"),
            ),
            {
                "analyst_review": "observed_skipped",
                "scrutineer": "dependency_blocked",
                "source_class_recovery": "may_run_not_observed",
            },
        ),
    )
    non_failure_statuses = {
        "optional_not_observed",
        "may_run_not_observed",
        "shadow_not_observed",
        "not_applicable",
        "blocked_by_mode",
        "dependency_blocked",
    }

    for case_id, trace, expected_statuses in cases:
        payload = build_controller_diagnostics_payload(trace)
        stages = {
            stage["stage_id"]: stage
            for stage in payload["planned_vs_observed"]["stages"]
        }

        _assert_controller_payload_base_contract(payload)
        assert payload["planned_vs_observed"]["failure_count"] == 0, case_id
        assert payload["planned_vs_observed"]["failures"] == [], case_id
        for stage_id, expected_status in expected_statuses.items():
            assert stages[stage_id]["status"] == expected_status, case_id
        for stage in stages.values():
            if stage["status"] in non_failure_statuses:
                assert stage["failure"] is False, case_id
        if case_id == "fast_weak_corpus_budget_blocked":
            assert stages["weak_corpus_recovery"]["status"] == "observed_blocked"
            assert stages["source_class_recovery"]["status"] == (
                "may_run_not_observed"
            )
        if case_id == "balanced_quantitative_economist_shadow":
            assert trace["analyst_skipped_after_economist"] is False
            assert trace["economist_output_used_as_analysis"] is False


def test_fast_direct_path_blocks_deep_stages_without_failures() -> None:
    trace = _trace(
        mode="Fast",
        complexity="low",
        analyst_model_called=False,
        context_stages=("router", "researcher", "author"),
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    assert _stage(diagnostics, "author")["status"] == "observed_completed"
    assert _stage(diagnostics, "analyst_review")["status"] == "blocked_by_mode"
    assert _stage(diagnostics, "weak_corpus_recovery")["status"] == "blocked_by_mode"
    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert diagnostics.to_dict()["failure_count"] == 0


def test_balanced_healthy_optional_absence_is_not_failure() -> None:
    trace = _trace()
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    assert _stage(diagnostics, "route_intent")["status"] == "observed_completed"
    assert _stage(diagnostics, "researcher_queries")["status"] == (
        "observed_completed"
    )
    assert _stage(diagnostics, "main_retrieval")["status"] == "observed_completed"
    assert _stage(diagnostics, "weak_corpus_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert _stage(diagnostics, "supplemental_retrieval")["status"] == (
        "optional_not_observed"
    )
    assert _stage(diagnostics, "economist_preflight")["status"] == "not_applicable"
    assert diagnostics.to_dict()["failure_count"] == 0


def test_balanced_weak_corpus_skip_is_observed_without_source_class_merge() -> None:
    trace = _trace(
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="no_recovery_queries",
        weak_corpus_recovery_queries=[],
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)
    ledger = build_task_ledger_from_trace(trace, run_plan=_plan_for(trace))

    weak = _stage(diagnostics, "weak_corpus_recovery")
    assert weak["status"] == "observed_skipped"
    assert weak["observed_status"] == "skipped"
    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert diagnostics.to_dict()["failure_count"] == 0
    assert [
        record.status for record in ledger.records_for("weak_corpus_recovery")
    ] == [TaskStatus.PLANNED, TaskStatus.SKIPPED]


def test_source_class_recovery_used_is_completed_and_distinct_from_weak_corpus() -> None:
    trace = _trace(
        active_source_class_recovery_considered=True,
        active_source_class_recovery_eligible=True,
        active_source_class_recovery_used=True,
        active_source_class_recovery_skip_reason=None,
        active_source_class_recovery_blockers=[],
        active_source_class_recovery_missing_classes=["official_current_rules"],
        active_source_class_recovery_queries=["Care Program official rules"],
        active_source_class_recovery_result_count=1,
        active_source_class_recovery_new_url_count=1,
        active_source_class_recovery_provider_role="source_class_recovery",
        active_source_class_recovery_search_depth="basic",
        active_source_class_recovery_attempt_count=1,
        source_class_recovery_recommended=True,
        source_class_recovery_shadow_mode=True,
        missing_expected_source_classes=["official_current_rules"],
        source_class_recovery_queries=["Care Program official rules"],
        source_class_recovery_query_count=1,
        provider_attempts_by_role={
            "main_retrieval": 1,
            "source_class_recovery": 1,
        },
        provider_diagnostics=[
            {
                "provider": "tavily",
                "provider_role": "main_retrieval",
                "success": True,
            },
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "success": True,
            },
        ],
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)
    ledger = build_task_ledger_from_trace(trace, run_plan=_plan_for(trace))

    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "observed_completed"
    )
    assert _stage(diagnostics, "weak_corpus_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert [
        record.status for record in ledger.records_for("source_class_recovery")
    ] == [TaskStatus.PLANNED, TaskStatus.COMPLETED]
    assert diagnostics.to_dict()["failure_count"] == 0


def test_quantitative_shadow_economist_does_not_imply_analyst_skip() -> None:
    trace = _trace(
        report_type="quantitative_comparison",
        query_type="quantitative_comparison",
        economist_ran=True,
        economist_preflight_allowed=True,
        economist_safety_status="code_execution_disabled",
        economist_schema_version="economist_v1",
        economist_schema_valid=True,
        economist_pre_analyst_skip_candidate_shadow=True,
        economist_pre_analyst_skip_candidate_gate_reason="candidate_shadow_only",
        analyst_model_called=True,
        analyst_skipped=False,
        analyst_skipped_after_economist=False,
        economist_output_used_as_analysis=False,
        author_quant_content_source="analyst_reviewed",
        author_received_raw_quant_packet=False,
        author_received_economist_framework=False,
        author_received_analyst_packet_marker=False,
        author_quant_handoff_gate_reason=(
            "author_received_analyst_reviewed_quantitative_synthesis"
        ),
        context_stages=(
            "router",
            "researcher",
            "economist_preflight",
            "analyst",
            "author",
        ),
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    assert _stage(diagnostics, "economist_preflight")["disposition"] == "shadow"
    assert _stage(diagnostics, "economist_preflight")["status"] == (
        "observed_completed"
    )
    assert _stage(diagnostics, "analyst_review")["status"] == "observed_completed"
    assert trace["analyst_skipped_after_economist"] is False
    assert trace["economist_output_used_as_analysis"] is False
    assert diagnostics.to_dict()["failure_count"] == 0


def test_quantitative_shadow_economist_absence_is_not_failure() -> None:
    trace = _trace(
        report_type="quantitative_comparison",
        query_type="quantitative_comparison",
        economist_ran=False,
        economist_preflight_allowed=None,
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    economist = _stage(diagnostics, "economist_preflight")
    assert economist["disposition"] == "shadow"
    assert economist["status"] == "shadow_not_observed"
    assert economist["failure"] is False
    assert diagnostics.to_dict()["failure_count"] == 0


def test_deep_scrutineer_absence_is_dependency_blocked_without_real_analyst() -> None:
    trace = _trace(
        mode="Deep",
        complexity="high",
        analyst_model_called=False,
        analyst_skipped=True,
        post_retrieval_fast_path_used=True,
        context_stages=("router", "researcher", "author"),
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    analyst = _stage(diagnostics, "analyst_review")
    scrutineer = _stage(diagnostics, "scrutineer")
    assert analyst["status"] == "observed_skipped"
    assert scrutineer["status"] == "dependency_blocked"
    assert scrutineer["failure"] is False
    assert scrutineer["metadata"]["blocked_dependencies"] == ["analyst_review"]
    assert diagnostics.to_dict()["failure_count"] == 0


def test_required_absence_fails_only_when_dependencies_are_satisfied() -> None:
    trace = _trace(queries_per_iteration={})
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    researcher = _stage(diagnostics, "researcher_queries")
    main_retrieval = _stage(diagnostics, "main_retrieval")
    assert researcher["status"] == "missing_required"
    assert researcher["failure"] is True
    assert main_retrieval["status"] == "observed_completed"
    assert diagnostics.to_dict()["failure_count"] == 1

    blocked_trace = _trace(queries_per_iteration={}, iterations_run=0, pass_providers=[])
    blocked_trace["provider_diagnostics"] = []
    blocked_trace["provider_attempts_by_role"] = {}
    blocked_diagnostics = compare_run_plan_to_observed_trace(
        _plan_for(blocked_trace),
        blocked_trace,
    )
    assert _stage(blocked_diagnostics, "researcher_queries")["status"] == (
        "missing_required"
    )
    assert _stage(blocked_diagnostics, "main_retrieval")["status"] == (
        "dependency_blocked"
    )


def test_fast_weak_corpus_budget_block_is_observed_without_activation() -> None:
    trace = _trace(
        mode="Fast",
        complexity="low",
        analyst_model_called=False,
        context_stages=("router", "researcher", "author"),
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="max_iterations_1",
        weak_corpus_recovery_queries=[],
    )
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)

    assert _stage(diagnostics, "weak_corpus_recovery")["status"] == (
        "observed_blocked"
    )
    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "may_run_not_observed"
    )
    assert diagnostics.to_dict()["failure_count"] == 0


def test_diagnostics_and_ledger_are_mutation_safe() -> None:
    trace = _trace()
    trace["provider_attempts_by_role"] = {"main_retrieval": 1}
    diagnostics = compare_run_plan_to_observed_trace(_plan_for(trace), trace)
    ledger = build_task_ledger_from_trace(trace, run_plan=_plan_for(trace))

    trace["provider_attempts_by_role"]["main_retrieval"] = 99
    trace["queries_per_iteration"]["1"].append("late mutation")

    main_stage = _stage(diagnostics, "main_retrieval")
    assert main_stage["metadata"]["provider_attempts_by_role"] == {
        "main_retrieval": 1
    }
    researcher_records = [
        record.to_dict() for record in ledger.records_for("researcher_queries")
    ]
    assert researcher_records[-1]["metadata"]["query_count"] == 1


def test_helper_noop_after_offline_harness_preserves_runtime_contracts(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    trace_before = deepcopy(outcome.execution_trace)
    log_keys_before = set(log_entry)
    log_trace_keys_before = set(log_entry["execution_trace"])
    report_before = outcome.report
    search_calls_before = deepcopy(harness.search_calls)
    author_prompts_before = list(harness.author_prompts)
    row_before = execution_jsonl_to_run_row(log_entry)

    payload = outcome.execution_trace[ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY]
    trace_without_payload = deepcopy(outcome.execution_trace)
    trace_without_payload.pop(ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY)
    plan = build_run_plan(
        mode=outcome.execution_trace["mode"],
        routing_metadata={
            "intent": outcome.execution_trace["intent"],
            "report_type": outcome.execution_trace["report_type"],
            "query_type": outcome.execution_trace["query_type"],
        },
    )
    diagnostics = compare_run_plan_to_observed_trace(plan, outcome.execution_trace)
    ledger = build_task_ledger_from_trace(outcome.execution_trace, run_plan=plan)

    _assert_controller_payload_base_contract(payload)
    assert trace_key_delta(
        outcome.execution_trace,
        trace_without_payload,
    ) == {ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY}
    assert diagnostics.to_dict()["failure_count"] == 0
    assert _stage(diagnostics, "source_class_recovery")["status"] == (
        "observed_completed"
    )
    payload_source_recovery = _payload_stage(payload, "source_class_recovery")
    assert payload_source_recovery["disposition"] == "may_run"
    assert payload_source_recovery["status"] == "observed_completed"
    assert payload_source_recovery["observed_status"] == "completed"
    assert [
        record.status for record in ledger.records_for("source_class_recovery")
    ] == [TaskStatus.PLANNED, TaskStatus.COMPLETED]
    assert outcome.execution_trace == trace_before
    assert set(outcome.execution_trace) == set(trace_before)
    assert set(log_entry) == log_keys_before
    assert set(log_entry["execution_trace"]) == log_trace_keys_before
    assert outcome.report == report_before
    assert harness.search_calls == search_calls_before
    assert harness.author_prompts == author_prompts_before
    assert harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["results_per_query"] == 6
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert harness.search_calls[1]["results_per_query"] == 6
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in log_entry
    assert log_entry["execution_trace"][ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY] == (
        payload
    )
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in outcome.new_session
    assert outcome.new_session["execution_trace"][
        ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY
    ] == payload

    row_after = execution_jsonl_to_run_row(log_entry)
    assert row_before is not None
    assert row_after is not None
    assert row_before == row_after
    assert set(row_after) == set(RUN_COLUMNS)
    assert "execution_trace" not in row_after
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in row_after
    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(log_entry)
    assert_no_top_level_controller_payload(row_after)

    assert harness.author_prompts
    for marker in RAW_AUTHOR_MARKERS:
        assert marker not in harness.author_prompts[-1]


def test_controller_payload_fast_weak_corpus_negative_control_preserves_runtime_contracts(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path / "passive", mode="Fast")
    baseline_outcome, baseline_harness = _run_weak_corpus_case(
        tmp_path / "baseline",
        mode="Fast",
    )
    log_entry = _execution_event_from_log(tmp_path / "passive" / "execution.jsonl")
    baseline_log = _execution_event_from_log(
        tmp_path / "baseline" / "execution.jsonl"
    )
    trace_before = deepcopy(outcome.execution_trace)
    log_keys_before = set(log_entry)
    log_trace_keys_before = set(log_entry["execution_trace"])
    report_before = outcome.report
    search_calls_before = deepcopy(harness.search_calls)
    search_call_details_before = deepcopy(harness.search_call_details)
    row_before = execution_jsonl_to_run_row(log_entry)

    payload = outcome.execution_trace[ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY]
    trace_without_payload = deepcopy(outcome.execution_trace)
    trace_without_payload.pop(ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY)
    weak = _payload_stage(payload, "weak_corpus_recovery")
    source_recovery = _payload_stage(payload, "source_class_recovery")

    _assert_controller_payload_base_contract(payload)
    assert payload["planned_vs_observed"]["failure_count"] == 0
    assert trace_key_delta(
        outcome.execution_trace,
        trace_without_payload,
    ) == {ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY}
    assert weak["disposition"] == "blocked_by_mode"
    assert weak["status"] == "observed_blocked"
    assert weak["observed_status"] == "blocked"
    assert weak["reason"] == "max_iterations_1"
    assert source_recovery["disposition"] == "may_run"
    assert source_recovery["status"] == "may_run_not_observed"
    assert source_recovery["observed_status"] is None
    assert outcome.execution_trace["weak_corpus_recovery_used"] is False
    assert outcome.execution_trace["weak_corpus_recovery_skip_reason"] == (
        "max_iterations_1"
    )
    assert outcome.execution_trace["active_source_class_recovery_used"] is False
    assert outcome.execution_trace["active_source_class_recovery_attempt_count"] == 0
    assert outcome.execution_trace == trace_before
    assert set(outcome.execution_trace) == set(trace_before)
    assert_trace_key_delta_only_controller_diagnostics(
        outcome.execution_trace,
        baseline_outcome.execution_trace,
    )
    assert set(log_entry) == log_keys_before
    assert set(log_entry) == set(baseline_log)
    assert set(log_entry["execution_trace"]) == log_trace_keys_before
    assert_trace_key_delta_only_controller_diagnostics(
        log_entry["execution_trace"],
        baseline_log["execution_trace"],
    )
    assert outcome.report == report_before
    assert outcome.report == baseline_outcome.report
    assert harness.search_calls == search_calls_before
    assert harness.search_calls == baseline_harness.search_calls
    assert harness.search_call_details == search_call_details_before
    assert harness.search_call_details == baseline_harness.search_call_details
    assert all(
        detail["provider_role"] != "source_class_recovery"
        for detail in harness.search_call_details
    )
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in log_entry
    assert log_entry["execution_trace"][ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY] == (
        payload
    )
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in outcome.new_session
    assert outcome.new_session["execution_trace"][
        ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY
    ] == payload

    row_after = execution_jsonl_to_run_row(log_entry)
    baseline_row = execution_jsonl_to_run_row(baseline_log)
    assert row_before is not None
    assert row_after is not None
    assert baseline_row is not None
    assert row_before == row_after
    assert set(row_after) == set(RUN_COLUMNS)
    assert set(row_after) == set(baseline_row)
    assert "execution_trace" not in row_after
    assert ALLOWED_CONTROLLER_DIAGNOSTICS_TRACE_KEY not in row_after
    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_jsonl_event_controller_payload_contract(log_entry)
    assert_no_top_level_controller_payload(row_after)
    assert harness.author_prompts
    for marker in RAW_AUTHOR_MARKERS:
        assert marker not in harness.author_prompts[-1]
