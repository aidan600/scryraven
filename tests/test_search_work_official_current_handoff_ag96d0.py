from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.query_shape_contract_resolution import SearchMode
from core.search_work_official_current_handoff import (
    build_search_work_official_current_handoff,
    source_class_recovery_recommendation_from_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "core" / "search_work_official_current_handoff.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _query_plan_shadow(mode: SearchMode = SearchMode.BALANCED) -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "owner": "QueryPlan",
        "source_construction_id": f"construction:{mode.value}",
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
                    "component_id": "authority",
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
                    "work_id": "canonical-job",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["legal-primary", "canonical-docs"],
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


def _handoff(mode: SearchMode = SearchMode.BALANCED) -> dict[str, Any]:
    return build_search_work_official_current_handoff(
        {"query_plan_work_shadow_projection": _query_plan_shadow(mode)}
    )


def test_handoff_exposes_official_current_acquisition_need() -> None:
    handoff = _handoff()

    assert handoff["source_obligation_driven"] is True
    assert handoff["mode_specific_official_executor"] is False
    assert handoff["official_current_needs"] == [
        {
            "need_kind": "official_current",
            "component_id": "fees",
            "obligation_id": "official-current",
            "strictness": "required",
            "required_source_classes": ["official_current_rules"],
            "provider_job_hints": [
                {
                    "work_id": "official-job",
                    "work_kind": "official_candidate_acquisition",
                    "source_obligation_ids": ["official-current"],
                    "executes_runtime_work": False,
                    "job_hint_only": True,
                }
            ],
            "stop_fail_qualify_posture_if_unsatisfied": {
                "obligations_unsatisfied": True,
                "conditions": ["source_obligation_unsatisfied"],
                "outcomes": ["qualify"],
                "posture": "qualify",
            },
            "source_obligation_driven": True,
            "satisfied": False,
        }
    ]
    assert "official_current_rules" in handoff["required_source_classes"]


def test_handoff_exposes_legal_canonical_and_source_bound_numeric_needs() -> None:
    handoff = _handoff()

    assert handoff["legal_current_primary_needs"][0]["required_source_classes"] == [
        "legal_or_regulatory_text",
        "current_primary_or_official",
    ]
    assert handoff["canonical_documentation_needs"][0]["required_source_classes"] == [
        "primary_source_documents"
    ]
    assert handoff["source_bound_numeric_needs"][0]["required_source_classes"] == [
        "sourced_numeric_values"
    ]
    assert handoff["source_class_recovery_handoff"][
        "missing_expected_source_classes"
    ] == [
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "sourced_numeric_values",
    ]
    assert source_class_recovery_recommendation_from_handoff(handoff)[
        "source_class_recovery_query_count"
    ] == 0


def test_handoff_is_mode_neutral_for_matching_obligations() -> None:
    fast = _handoff(SearchMode.FAST)
    balanced = _handoff(SearchMode.BALANCED)
    deep = _handoff(SearchMode.DEEP)

    comparable_fields = (
        "official_current_needs",
        "legal_current_primary_needs",
        "canonical_documentation_needs",
        "source_bound_numeric_needs",
        "required_source_classes",
        "source_obligation_ids",
        "provider_job_kinds",
    )
    for field in comparable_fields:
        assert fast[field] == balanced[field] == deep[field]
    assert fast["source_obligation_driven"] is True
    assert deep["mode_specific_official_executor"] is False


def test_handoff_generates_no_query_text_or_provider_search_retrieval_execution() -> None:
    handoff = _handoff()
    encoded = json.dumps(handoff, sort_keys=True)

    for key in (
        "provider_selected",
        "query_text_generated",
        "search_executed",
        "retrieval_executed",
        "final_answer_behavior_changed",
        "query_plan_behavior_changed",
        "query_admission_changed",
        "query_order_changed",
        "search_depth_changed",
        "prompt_behavior_changed",
        "citation_behavior_changed",
    ):
        assert handoff[key] is False
    assert "candidate_queries" not in encoded
    assert "finalized_queries" not in encoded
    assert '"query_text"' not in encoded


def test_lower_tier_bridge_material_cannot_satisfy_official_current_need() -> None:
    handoff = build_search_work_official_current_handoff(
        _query_plan_shadow(),
        observed_material=(
            {
                "material_id": "secondary-summary",
                "source_class": "secondary",
                "source_tier": "secondary",
            },
        ),
    )

    assert handoff["lower_tier_material_satisfies_required_official_current"] is False
    assert "official_current_rules" in handoff["unsatisfied_required_source_classes"]
    rejected = handoff["observed_material_summary"]["rejected_material"][0]
    assert rejected["satisfies_required_official_current"] is False
    assert rejected["rejection_reason"] == (
        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
    )


def test_existing_recovery_blockers_prevent_handoff_escalation() -> None:
    handoff = build_search_work_official_current_handoff(
        _query_plan_shadow(),
        existing_blockers=("blocked_by_iteration_budget", "terminal_stop_approved"),
    )
    recommendation = handoff["source_class_recovery_handoff"]

    assert handoff["recovery_handoff_blocked"] is True
    assert handoff["recovery_handoff_escalation_allowed"] is False
    assert recommendation["source_class_recovery_recommended"] is False
    assert recommendation["missing_expected_source_classes"]
    assert recommendation["handoff_blockers"] == [
        "blocked_by_iteration_budget",
        "terminal_stop_approved",
    ]


def test_handoff_redacts_sensitive_fields() -> None:
    shadow = {
        **_query_plan_shadow(),
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "TRACE_SENTINEL",
    }
    encoded = json.dumps(
        build_search_work_official_current_handoff(
            {"query_plan_work_shadow_projection": shadow}
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


def test_pipeline_does_not_gain_local_official_current_planning_logic() -> None:
    source = PIPELINE.read_text(encoding="utf-8")

    assert "search_work_official_current_handoff" not in source
    assert "build_search_work_official_current_handoff" not in source


def test_closed_runtime_modules_do_not_import_official_current_handoff() -> None:
    forbidden_modules = {
        "core.search_work_official_current_handoff",
        "search_work_official_current_handoff",
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


def test_handoff_helper_keeps_provider_retrieval_prompt_boundary() -> None:
    source = HANDOFF.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
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
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "fetch_page",
        "process_search_queries",
        "authorize_query_production",
        "authorize_query_plan_admission",
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
    assert called_names.isdisjoint(forbidden_calls)
