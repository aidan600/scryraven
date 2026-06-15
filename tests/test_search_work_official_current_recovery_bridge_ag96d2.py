from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.official_source_obligation_bridge import (
    build_search_work_official_current_obligation_bridge_trace,
)
from core.search_work_official_current_handoff import (
    build_search_work_official_current_handoff,
)
from core.search_work_official_current_recovery_bridge import (
    build_search_work_official_current_recovery_bridge,
)

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "core" / "search_work_official_current_recovery_bridge.py"
FAST_OFFICIAL_LANE = ROOT / "core" / "fast_official_lane.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _query_plan_shadow(mode: str = "balanced") -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "owner": "SearchWorkPlan.QueryPlanWorkShadowAdapter",
        "source_construction_id": f"construction:{mode}",
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
        "metadata": {"mode": mode},
    }


def _handoff(mode: str = "balanced") -> dict[str, Any]:
    return build_search_work_official_current_handoff(_query_plan_shadow(mode))


def _lane(mode: str = "balanced") -> dict[str, Any]:
    return {
        "trace_key": "search_work_shadow_lane_projection",
        "requested_mode": mode,
        "search_work_official_current_handoff": _handoff(mode),
    }


def test_d1_lane_projection_exposes_recovery_bridge_missing_classes() -> None:
    bridge = build_search_work_official_current_recovery_bridge(_lane())

    assert bridge["bridge_considered"] is True
    assert bridge["bridge_eligible"] is True
    assert bridge["bridge_used"] is True
    assert bridge["source_obligation_driven"] is True
    assert bridge["source_class_recovery_recommended"] is True
    assert bridge["missing_expected_source_classes"] == [
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "sourced_numeric_values",
    ]
    assert "search_work_handoff:source_obligation_driven" in bridge[
        "source_class_recovery_trigger_fields"
    ]
    assert "source_obligation:official_current" in bridge[
        "source_class_recovery_trigger_fields"
    ]


def test_d0_handoff_projection_uses_same_bridge_result() -> None:
    from_lane = build_search_work_official_current_recovery_bridge(_lane())
    from_handoff = build_search_work_official_current_recovery_bridge(_handoff())

    comparable = (
        "missing_expected_source_classes",
        "source_class_recovery_recommended",
        "source_class_recovery_shadow_mode",
        "source_class_recovery_queries",
        "source_class_recovery_query_count",
    )
    for field in comparable:
        assert from_handoff[field] == from_lane[field]


def test_legal_canonical_and_source_bound_numeric_needs_are_represented() -> None:
    bridge = build_search_work_official_current_recovery_bridge(_handoff())

    missing = set(bridge["missing_expected_source_classes"])
    assert {
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "sourced_numeric_values",
    }.issubset(missing)
    assert "source_obligation:legal_primary" in bridge[
        "source_class_recovery_trigger_fields"
    ]
    assert "source_obligation:canonical_docs" in bridge[
        "source_class_recovery_trigger_fields"
    ]
    assert "source_obligation:source_bound_numeric" in bridge[
        "source_class_recovery_trigger_fields"
    ]


def test_existing_blockers_prevent_recommendation_but_preserve_visibility() -> None:
    bridge = build_search_work_official_current_recovery_bridge(
        _handoff(),
        existing_blockers=(
            "blocked_by_iteration_budget",
            "terminal_stop_approved",
            "active_recovery_already_used",
            "blocked_by_provider_policy_change_required",
            "blocked_by_search_depth_escalation_required",
            "blocked_by_query_generation_change_required",
            "weak_corpus_recovery_owns_path",
        ),
    )

    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "existing_runtime_blocker"
    assert bridge["source_class_recovery_recommended"] is False
    assert "official_current_rules" in bridge["missing_expected_source_classes"]
    assert bridge["handoff_blockers"] == [
        "blocked_by_iteration_budget",
        "terminal_stop_approved",
        "active_recovery_already_used",
        "blocked_by_provider_policy_change_required",
        "blocked_by_search_depth_escalation_required",
        "blocked_by_query_generation_change_required",
        "weak_corpus_recovery_owns_path",
    ]


def test_existing_recovery_recommendation_fields_append_safely() -> None:
    bridge = build_search_work_official_current_recovery_bridge(
        _handoff(),
        existing_recovery_recommendation={
            "source_class_recovery_recommended": True,
            "source_class_recovery_shadow_mode": True,
            "source_class_recovery_reason": "existing_reason",
            "missing_expected_source_classes": ["archival_primary_text"],
            "source_class_recovery_trigger_fields": ["existing_trigger"],
            "source_class_recovery_queries": ["executable text omitted"],
        },
    )

    assert bridge["source_class_recovery_reason"] == "existing_reason"
    assert bridge["missing_expected_source_classes"][0] == "archival_primary_text"
    assert "official_current_rules" in bridge["missing_expected_source_classes"]
    assert "existing_trigger" in bridge["source_class_recovery_trigger_fields"]
    assert bridge["source_class_recovery_queries"] == []
    assert bridge["existing_recovery_recommendation"][
        "query_text_omitted_by_bridge_boundary"
    ] is True


def test_lower_tier_observed_material_is_diagnostic_only() -> None:
    bridge = build_search_work_official_current_recovery_bridge(
        _handoff(),
        observed_material_diagnostics=(
            {
                "material_id": "community-summary",
                "source_class": "community",
                "source_tier": "secondary",
            },
            {
                "material_id": "social-post",
                "source_class": "social",
                "source_tier": "social",
            },
        ),
    )

    assert bridge["lower_tier_material_satisfies_required_official_current"] is False
    rejected = bridge["observed_material_diagnostics"]["rejected_material"]
    assert {item["material_id"] for item in rejected} == {
        "community_summary",
        "social_post",
    }
    assert all(item["satisfies_required_official_current"] is False for item in rejected)
    assert bridge["subordinate_recovery_ownership"][
        "lower_tier_bridge_material_can_satisfy"
    ] is False


def test_bridge_output_has_no_queries_or_execution_flags() -> None:
    bridge = build_search_work_official_current_recovery_bridge(_handoff())
    encoded = json.dumps(bridge, sort_keys=True)

    assert bridge["source_class_recovery_queries"] == []
    assert bridge["source_class_recovery_query_count"] == 0
    for key in (
        "recovery_execution_authorized",
        "provider_selected",
        "query_text_generated",
        "search_executed",
        "retrieval_executed",
        "final_answer_behavior_changed",
    ):
        assert bridge[key] is False
    assert "executable text" not in encoded
    assert '"query_text"' not in encoded


def test_bridge_is_mode_neutral_for_matching_obligations() -> None:
    bridges = [
        build_search_work_official_current_recovery_bridge(_lane(mode))
        for mode in ("fast", "balanced", "deep")
    ]

    comparable = (
        "missing_expected_source_classes",
        "source_class_recovery_trigger_fields",
        "source_class_recovery_queries",
        "provider_selected",
        "query_text_generated",
        "search_executed",
        "retrieval_executed",
    )
    for field in comparable:
        assert bridges[0][field] == bridges[1][field] == bridges[2][field]


def test_official_source_obligation_bridge_wrapper_is_explicit_compatibility() -> None:
    direct = build_search_work_official_current_recovery_bridge(_lane())
    wrapped = build_search_work_official_current_obligation_bridge_trace(
        search_work_lane_projection=_lane()
    )

    assert wrapped["missing_expected_source_classes"] == direct[
        "missing_expected_source_classes"
    ]
    assert wrapped["source_class_recovery_queries"] == []


def test_bridge_redacts_sensitive_fields() -> None:
    tainted = {
        **_handoff(),
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "TRACE_SENTINEL",
    }
    encoded = json.dumps(
        build_search_work_official_current_recovery_bridge(tainted),
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


def test_fast_lane_runtime_behavior_unchanged_and_bridge_has_no_dependency() -> None:
    before = FAST_OFFICIAL_LANE.read_text(encoding="utf-8")
    bridge_source = BRIDGE.read_text(encoding="utf-8")
    tree = ast.parse(bridge_source)
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
    assert "build_fast_official_lane_plan" in before
    assert "FastOfficialLanePlan" in before
    assert "build_fast_official_lane_plan(" not in bridge_source


def test_pipeline_has_no_local_official_current_bridge_planning_logic() -> None:
    source = PIPELINE.read_text(encoding="utf-8")

    assert "search_work_official_current_recovery_bridge" not in source
    assert "build_search_work_official_current_recovery_bridge" not in source


def test_closed_runtime_modules_do_not_import_recovery_bridge() -> None:
    forbidden_modules = {
        "core.search_work_official_current_recovery_bridge",
        "search_work_official_current_recovery_bridge",
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


def test_bridge_imports_no_provider_retrieval_prompt_or_final_answer_modules() -> None:
    tree = ast.parse(BRIDGE.read_text(encoding="utf-8"))
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
