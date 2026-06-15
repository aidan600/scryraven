from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    build_authoritative_source_obligation_state_and_action,
)
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.run_controller import RunController
from core.search_work_official_current_handoff import (
    build_search_work_official_current_handoff,
)
from core.search_work_official_current_recovery_activation import (
    SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY,
    activate_search_work_official_current_recovery_recommendation,
)
from core.search_work_official_current_recovery_bridge import (
    build_search_work_official_current_recovery_bridge,
)

ROOT = Path(__file__).resolve().parents[1]
ACTIVATION = ROOT / "core" / "search_work_official_current_recovery_activation.py"
FAST_OFFICIAL_LANE = ROOT / "core" / "fast_official_lane.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _query_plan_shadow() -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "owner": "SearchWorkPlan.QueryPlanWorkShadowAdapter",
        "acquisition_needs": {
            "official_current": [
                {
                    "component_id": "fees",
                    "obligation_id": "official-current",
                    "strictness": "required",
                }
            ],
            "legal_current_primary": [
                {
                    "component_id": "authority",
                    "obligation_id": "legal-primary",
                    "strictness": "required",
                }
            ],
            "canonical_documentation": [
                {
                    "component_id": "docs",
                    "obligation_id": "canonical-docs",
                    "strictness": "required",
                }
            ],
            "source_bound_numeric": [
                {
                    "component_id": "fees",
                    "obligation_id": "source-bound-numeric",
                    "strictness": "required",
                }
            ],
        },
        "provider_jobs_by_component": {
            "fees": [
                {
                    "work_id": "official-job",
                    "work_kind": "official_candidate_acquisition",
                    "source_obligation_ids": ["official-current"],
                },
                {
                    "work_id": "numeric-job",
                    "work_kind": "fetch_read_extract",
                    "source_obligation_ids": ["source-bound-numeric"],
                },
            ],
            "authority": [
                {
                    "work_id": "legal-job",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["legal-primary"],
                }
            ],
            "docs": [
                {
                    "work_id": "docs-job",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["canonical-docs"],
                }
            ],
        },
        "stop_and_follow_up_posture": {
            "stop_conditions": [
                {
                    "condition": "source_obligation_unsatisfied",
                    "outcome": "qualify",
                }
            ]
        },
    }


def _handoff() -> dict[str, Any]:
    return build_search_work_official_current_handoff(_query_plan_shadow())


def _lane() -> dict[str, Any]:
    return {
        "trace_key": "search_work_shadow_lane_projection",
        "search_work_official_current_handoff": _handoff(),
    }


def _empty_recommendation() -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": False,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [],
        "source_class_recovery_reason": None,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": [],
    }


def test_d1_lane_projection_activates_source_obligation_recommendation_visibility() -> None:
    merged = activate_search_work_official_current_recovery_recommendation(
        recommendation=_empty_recommendation(),
        search_work_lane_projection=_lane(),
    )

    assert merged["source_class_recovery_recommended"] is True
    assert merged["source_obligation_driven"] is True
    assert merged["missing_expected_source_classes"] == [
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "sourced_numeric_values",
    ]
    assert "search_work_handoff:source_obligation_driven" in merged[
        "source_class_recovery_trigger_fields"
    ]
    assert "search_work_official_current_recovery_activation" in merged[
        "source_class_recovery_trigger_fields"
    ]
    assert merged["source_class_recovery_queries"] == []
    assert merged["source_class_recovery_query_count"] == 0
    trace = merged[SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY]
    assert trace["activation_eligible"] is True
    assert trace["source_class_recovery_queries_unchanged"] is True


def test_d2_bridge_result_activates_same_visibility_input() -> None:
    bridge = build_search_work_official_current_recovery_bridge(_lane())
    merged = activate_search_work_official_current_recovery_recommendation(
        recommendation=_empty_recommendation(),
        search_work_official_current_recovery_bridge=bridge,
    )

    assert merged["source_class_recovery_recommended"] is True
    assert merged["missing_expected_source_classes"] == bridge[
        "missing_expected_source_classes"
    ]
    assert merged["source_class_recovery_queries"] == []


def test_existing_fields_are_appended_without_destructive_overwrite() -> None:
    merged = activate_search_work_official_current_recovery_recommendation(
        recommendation={
            "source_class_recovery_recommended": True,
            "source_class_recovery_shadow_mode": True,
            "missing_expected_source_classes": ["archival_primary_text"],
            "source_class_recovery_reason": "existing_reason",
            "source_class_recovery_queries": ["existing executable query"],
            "source_class_recovery_query_count": 1,
            "source_class_recovery_trigger_fields": ["existing_trigger"],
        },
        search_work_lane_projection=_lane(),
    )

    assert merged["source_class_recovery_reason"] == "existing_reason"
    assert merged["missing_expected_source_classes"][0] == "archival_primary_text"
    assert "sourced_numeric_values" in merged["missing_expected_source_classes"]
    assert "existing_trigger" in merged["source_class_recovery_trigger_fields"]
    assert merged["source_class_recovery_queries"] == ["existing executable query"]
    assert merged["source_class_recovery_query_count"] == 1


def test_no_search_work_projection_leaves_existing_recommendation_undecorated() -> None:
    existing = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["archival_primary_text"],
        "source_class_recovery_reason": "existing_reason",
        "source_class_recovery_queries": ["existing executable query"],
        "source_class_recovery_query_count": 1,
        "source_class_recovery_trigger_fields": ["existing_trigger"],
    }

    merged = activate_search_work_official_current_recovery_recommendation(
        recommendation=existing,
    )

    assert merged == existing
    assert "search_work_official_current_recovery_activation" not in merged
    assert "source_obligation_driven" not in merged
    assert merged["missing_expected_source_classes"] == ["archival_primary_text"]
    assert merged["source_class_recovery_reason"] == "existing_reason"
    assert merged["source_class_recovery_trigger_fields"] == ["existing_trigger"]
    assert all(
        "search_work" not in field
        for field in merged["source_class_recovery_trigger_fields"]
    )


def test_existing_blockers_preserve_missing_visibility_without_activation() -> None:
    merged = activate_search_work_official_current_recovery_recommendation(
        recommendation=_empty_recommendation(),
        search_work_lane_projection=_lane(),
        existing_blockers=("blocked_by_iteration_budget",),
    )

    assert merged["source_class_recovery_recommended"] is False
    assert "official_current_rules" in merged["missing_expected_source_classes"]
    trace = merged[SEARCH_WORK_OFFICIAL_CURRENT_RECOVERY_ACTIVATION_TRACE_KEY]
    assert trace["activation_eligible"] is False
    assert trace["activation_skip_reason"] == "existing_runtime_blocker"
    assert trace["blockers"] == ["blocked_by_iteration_budget"]


def test_runtime_authoritative_action_consumes_search_work_activation() -> None:
    controller = RunController()
    result = build_authoritative_source_obligation_state_and_action(
        controller,
        facts=AuthoritativeSourceActionFacts(
            query="What is the current official filing fee?",
            intent="general",
            report_type="general_research",
            query_type="current_events",
            core_topic="current official filing fee",
            primary_entity="filing fee",
            recommendation=_empty_recommendation(),
            source_class_observability={},
            source_class_evidence_signals={
                "source_tier_counts": {"secondary": 2},
                "source_domain_counts": {"analysis.example": 2},
                "top_source_domains": [{"domain": "analysis.example", "count": 2}],
                "official_evidence_found": False,
            },
            search_work_official_current_recovery_projection=_lane(),
            corpus_state="HEALTHY",
            corpus_weak=False,
            weak_corpus_recovery_considered=False,
            weak_corpus_recovery_used=False,
            weak_corpus_recovery_skip_reason=None,
            current_search_depth="basic",
            iteration_budget_available=True,
            answer_contract_source_class_slot_available=True,
            prior_recovery_attempt_count=0,
            max_recovery_attempts=1,
            ordinary_iteration_budget_remaining=1,
        ),
    )

    recommendation = result.recommendation
    lifecycle = result.active_source_class_recovery_lifecycle
    assert "official_current_rules" in recommendation["missing_expected_source_classes"]
    assert "sourced_numeric_values" in recommendation["missing_expected_source_classes"]
    assert recommendation["source_class_recovery_recommended"] is True
    assert recommendation["source_class_recovery_query_count"] > 0
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert "official_current_rules" in lifecycle[
        "active_source_class_recovery_missing_classes"
    ]
    assert "sourced_numeric_values" in lifecycle[
        "active_source_class_recovery_missing_classes"
    ]
    assert result.trace["adapter_traces_present"][
        "search_work_official_current_recovery_activation"
    ] is True


def test_orchestrator_adapter_passes_run_kernel_search_work_lane_projection() -> None:
    controller = RunController()
    run_kernel = SimpleNamespace(
        state=SimpleNamespace(
            projections={"search_work_shadow_lane_projection": _lane()}
        )
    )
    handoff = build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state={
            "query": "What is the current official filing fee?",
            "intent": "general",
            "report_type": "general_research",
            "query_type": "current_events",
            "core_topic": "current official filing fee",
            "primary_entity": "filing fee",
            "_source_class_recovery_lifecycle_recommendation": (
                _empty_recommendation()
            ),
            "_source_class_recovery_answer_contract_observability": {},
            "_source_tier_recovery_lifecycle": {
                "source_tier_counts": {"secondary": 2},
                "official_evidence_found": False,
            },
            "_source_domain_recovery_lifecycle": {
                "source_domain_counts": {"analysis.example": 2},
                "top_source_domains": [
                    {"domain": "analysis.example", "count": 2}
                ],
            },
            "run_kernel": run_kernel,
            "corpus_state": "HEALTHY",
            "corpus_weak": False,
            "weak_corpus_recovery_considered": False,
            "weak_corpus_recovery_used": False,
            "weak_corpus_recovery_skip_reason": None,
            "current_search_depth_for_recovery": "basic",
            "iterations_run": 0,
            "max_iterations": 2,
            "waste_flags": [],
        },
    )

    recommendation = handoff.recommendation
    lifecycle = handoff.active_source_class_recovery_lifecycle
    assert recommendation["source_class_recovery_recommended"] is True
    assert "official_current_rules" in recommendation["missing_expected_source_classes"]
    assert "sourced_numeric_values" in recommendation["missing_expected_source_classes"]
    assert lifecycle["active_source_class_recovery_eligible"] is True


def test_runtime_blockers_prevent_lifecycle_escalation_but_preserve_visibility() -> None:
    controller = RunController()
    result = build_authoritative_source_obligation_state_and_action(
        controller,
        facts=AuthoritativeSourceActionFacts(
            query="What is the current official filing fee?",
            intent="general",
            report_type="general_research",
            query_type="current_events",
            core_topic="current official filing fee",
            primary_entity="filing fee",
            recommendation=_empty_recommendation(),
            source_class_observability={},
            source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
            search_work_official_current_recovery_projection=_lane(),
            corpus_state="HEALTHY",
            corpus_weak=False,
            weak_corpus_recovery_considered=False,
            weak_corpus_recovery_used=False,
            weak_corpus_recovery_skip_reason=None,
            current_search_depth="basic",
            iteration_budget_available=True,
            terminal_stop_approved=True,
            prior_recovery_attempt_count=0,
            max_recovery_attempts=1,
            ordinary_iteration_budget_remaining=1,
        ),
    )

    recommendation = result.recommendation
    lifecycle = result.active_source_class_recovery_lifecycle
    assert "official_current_rules" in recommendation["missing_expected_source_classes"]
    assert recommendation["source_class_recovery_recommended"] is False
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert "blocked_by_terminal_stop" in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_activation_redacts_sensitive_fields() -> None:
    tainted = {
        **_lane(),
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "TRACE_SENTINEL",
    }
    encoded = json.dumps(
        activate_search_work_official_current_recovery_recommendation(
            recommendation=_empty_recommendation(),
            search_work_lane_projection=tainted,
        ),
        sort_keys=True,
    )

    for field_name in (
        "raw_prompt",
        "raw_provider_payload",
        "raw_model_response",
        "secret",
        "token",
        "db_row",
        "full_trace",
    ):
        assert field_name not in encoded
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_fast_lane_runtime_behavior_unchanged_and_activation_has_no_dependency() -> None:
    fast_lane_source = FAST_OFFICIAL_LANE.read_text(encoding="utf-8")
    activation_source = ACTIVATION.read_text(encoding="utf-8")
    tree = ast.parse(activation_source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert "core.fast_official_lane" not in imports
    assert "build_fast_official_lane_plan" in fast_lane_source
    assert "FastOfficialLanePlan" in fast_lane_source
    assert "build_fast_official_lane_plan(" not in activation_source


def test_pipeline_has_no_local_official_current_planning_logic() -> None:
    source = PIPELINE.read_text(encoding="utf-8")

    assert "search_work_official_current_recovery_activation" not in source
    assert "activate_search_work_official_current_recovery_recommendation" not in source


def test_closed_runtime_modules_do_not_import_activation_helper() -> None:
    forbidden_modules = {
        "core.search_work_official_current_recovery_activation",
        "search_work_official_current_recovery_activation",
    }
    paths = (
        ROOT / "core" / "pipeline_orchestrator.py",
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "retrieval_scheduler.py",
        ROOT / "core" / "runtime_prompt_assembly.py",
        ROOT / "core" / "final_answer_runtime_adapter.py",
        ROOT / "core" / "final_evidence_bundle_builder.py",
        ROOT / "core" / "final_answer_packet.py",
    )

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        assert imported_names.isdisjoint(forbidden_modules), path


def test_activation_helper_imports_no_execution_or_answer_modules() -> None:
    tree = ast.parse(ACTIVATION.read_text(encoding="utf-8"))
    forbidden_import_roots = {
        "core.fast_official_lane",
        "core.pipeline_orchestrator",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
        "core.query_production_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.runtime_prompt_assembly",
        "core.prompts",
        "core.final_answer_runtime_adapter",
        "core.final_evidence_bundle_builder",
        "core.final_answer_packet",
    }
    imported_names: set[str] = set()
    called_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(
        {
            "ask_model",
            "search_web_results",
            "search_exa_results",
            "search_linkup_results",
            "fetch_page",
            "process_search_queries",
            "authorize_query_production",
            "authorize_query_plan_admission",
        }
    )
