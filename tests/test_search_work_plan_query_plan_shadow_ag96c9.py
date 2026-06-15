from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.search_work_plan import (
    AuditJob,
    AuditScope,
    EffectiveContractDescriptor,
    EffectiveContractKind,
    FollowUpAuthority,
    FollowUpPermission,
    ProviderJob,
    ProviderJobKind,
    QuantWorkUnit,
    QueryShapeDescriptor,
    QueryShapeKind,
    RemediationPermission,
    RequestedModeDescriptor,
    SearchMode,
    SearchWorkComponent,
    SearchWorkPlan,
    SourceObligation,
    SourceObligationKind,
    SourceObligationStrictness,
    StopCondition,
    StopConditionKind,
    StopOutcome,
    SynthesisJob,
    SynthesisScope,
)
from core.search_work_plan_query_plan_shadow import (
    build_query_plan_work_shadow_projection,
)

ROOT = Path(__file__).resolve().parents[1]
SHADOW_ADAPTER = ROOT / "core" / "search_work_plan_query_plan_shadow.py"


def _representative_search_work_plan_projection() -> dict[str, Any]:
    plan = SearchWorkPlan(
        requested_mode=RequestedModeDescriptor(
            mode=SearchMode.BALANCED,
            source="unit_test",
        ),
        effective_contract=EffectiveContractDescriptor(
            contract_kind=EffectiveContractKind.EXPLANATORY,
            depth_allowance="moderate",
            follow_up_posture=FollowUpPermission.CONDITIONAL,
        ),
        query_shape=QueryShapeDescriptor(
            kinds=(
                QueryShapeKind.OFFICIAL_CURRENT_LOOKUP,
                QueryShapeKind.LEGAL_CURRENT_PRIMARY,
                QueryShapeKind.CANONICAL_DOCUMENTATION,
                QueryShapeKind.SOURCE_BOUND_NUMERIC,
            ),
            component_count_hint=2,
        ),
        components=(
            SearchWorkComponent(
                component_id="fees",
                user_facing_subquestion="Find current official fee facts.",
                source_obligations=(
                    SourceObligation(
                        obligation_id="official-current",
                        kind=SourceObligationKind.OFFICIAL_CURRENT,
                        strictness=SourceObligationStrictness.REQUIRED,
                        currentness_requirement="current at answer time",
                        satisfaction_rule="official custody required",
                    ),
                    SourceObligation(
                        obligation_id="source-bound-numeric",
                        kind=SourceObligationKind.SOURCE_BOUND_NUMERIC,
                        strictness=SourceObligationStrictness.REQUIRED,
                        satisfaction_rule="numeric value must be source-bound",
                    ),
                ),
                required_provider_jobs=(
                    ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
                    ProviderJobKind.FETCH_READ_EXTRACT,
                ),
                stop_conditions=(
                    StopCondition(
                        condition=StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,
                        outcome=StopOutcome.QUALIFY,
                        component_id="fees",
                    ),
                ),
            ),
            SearchWorkComponent(
                component_id="authority",
                user_facing_subquestion="Identify governing authority.",
                source_obligations=(
                    SourceObligation(
                        obligation_id="legal-primary",
                        kind=SourceObligationKind.LEGAL_CURRENT_PRIMARY,
                        strictness=SourceObligationStrictness.REQUIRED,
                    ),
                    SourceObligation(
                        obligation_id="canonical-docs",
                        kind=SourceObligationKind.CANONICAL_DOCUMENTATION,
                        strictness=SourceObligationStrictness.PREFERRED,
                    ),
                ),
                required_provider_jobs=(ProviderJobKind.CANONICAL_EXTRACTION,),
            ),
        ),
        provider_jobs=(
            ProviderJob(
                provider_job_id="official-job",
                job_kind=ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION,
                component_ids=("fees",),
                source_obligation_ids=("official-current",),
                job_posture="planned_passive_not_executed",
                metadata={"executes_search": False},
            ),
            ProviderJob(
                provider_job_id="numeric-job",
                job_kind=ProviderJobKind.FETCH_READ_EXTRACT,
                component_ids=("fees",),
                source_obligation_ids=("source-bound-numeric",),
                job_posture="planned_passive_not_executed",
                metadata={"executes_search": False},
            ),
            ProviderJob(
                provider_job_id="canonical-job",
                job_kind=ProviderJobKind.CANONICAL_EXTRACTION,
                component_ids=("authority",),
                source_obligation_ids=("legal-primary", "canonical-docs"),
                job_posture="planned_passive_not_executed",
                metadata={"executes_search": False},
            ),
        ),
        quant_work_units=(
            QuantWorkUnit(
                quant_unit_id="fee-delta",
                component_ids=("fees",),
                target_metric="fee delta",
                source_bound_values_needed=("current fee", "prior fee"),
            ),
        ),
        synthesis_jobs=(
            SynthesisJob(
                synthesis_job_id="authority-summary",
                component_ids=("authority",),
                synthesis_scope=SynthesisScope.EVIDENCE_BASIS_SUMMARY,
            ),
        ),
        audit_jobs=(
            AuditJob(
                audit_job_id="currentness-audit",
                component_ids=("fees", "authority"),
                audit_scope=AuditScope.CURRENTNESS_AUDIT,
                remediation_permission=RemediationPermission.CONDITIONAL_PASSIVE,
            ),
        ),
        follow_up_authority=FollowUpAuthority(
            permission=FollowUpPermission.CONDITIONAL,
            authorizers=("RunAuthority", "SearchJudgment", "SufficiencyJudgment"),
        ),
        stop_conditions=(
            StopCondition(
                condition=StopConditionKind.SOURCE_OBLIGATION_UNSATISFIED,
                outcome=StopOutcome.QUALIFY,
            ),
        ),
        metadata={"construction_id": "construction:ag96c9"},
    ).require_valid()
    return plan.to_dict()


def test_adapter_emits_query_plan_work_hints_without_runtime_behavior() -> None:
    projection = build_query_plan_work_shadow_projection(
        _representative_search_work_plan_projection()
    )

    assert projection["owner"] == "SearchWorkPlan.QueryPlanWorkShadowAdapter"
    assert projection["shadow_only"] is True
    assert projection["runtime_consumed_by_query_plan"] is False
    assert projection["query_plan_behavior_changed"] is False
    assert projection["query_text_generated"] is False
    assert projection["query_admission_changed"] is False
    assert projection["query_order_changed"] is False
    assert projection["provider_search_behavior_changed"] is False
    assert projection["search_depth_changed"] is False
    assert projection["retrieval_behavior_changed"] is False
    assert projection["prompt_behavior_changed"] is False
    assert projection["citation_behavior_changed"] is False
    assert projection["final_answer_behavior_changed"] is False

    assert projection["work_counts"] == {
        "component_count": 2,
        "source_obligation_count": 4,
        "provider_job_count": 3,
        "quant_work_unit_count": 1,
        "synthesis_job_count": 1,
        "audit_job_count": 1,
        "official_current_need_count": 1,
        "legal_current_primary_need_count": 1,
        "canonical_documentation_need_count": 1,
        "source_bound_numeric_need_count": 1,
    }
    assert projection["components"][0]["component_id"] == "fees"
    assert projection["components"][0]["source_obligation_count"] == 2
    assert projection["components"][0]["provider_job_count"] == 2
    assert projection["components"][0]["quant_work_count"] == 1
    assert projection["components"][0]["audit_work_count"] == 1
    assert projection["source_obligations_by_component"]["fees"][0]["kind"] == "official_current"
    assert projection["provider_jobs_by_component"]["fees"][0]["executes_runtime_work"] is False
    assert projection["acquisition_needs"]["official_current"] == [
        {
            "component_id": "fees",
            "obligation_id": "official-current",
            "strictness": "required",
            "shadow_hint_only": True,
        }
    ]
    assert projection["candidate_work_groups"][0]["contains_executable_query_text"] is False
    assert projection["candidate_work_groups"][0]["admits_query_candidates"] is False


def test_adapter_accepts_run_kernel_trace_shaped_projection() -> None:
    plan = _representative_search_work_plan_projection()
    projection = build_query_plan_work_shadow_projection(
        {
            "search_work_plan": plan,
            "search_work_plan_projection": {
                "owner": "RunKernel.SearchWorkPlan",
                "construction_id": "construction:trace-shaped",
                "schema_version": plan["schema_version"],
            },
        }
    )

    assert projection["source_owner"] == "RunKernel.SearchWorkPlan"
    assert projection["source_construction_id"] == "construction:trace-shaped"
    assert projection["work_counts"]["official_current_need_count"] == 1


def test_adapter_projection_excludes_query_text_and_user_facing_component_text() -> None:
    projection = build_query_plan_work_shadow_projection(
        _representative_search_work_plan_projection()
    )
    encoded = json.dumps(projection, sort_keys=True)

    assert "Find current official fee facts" not in encoded
    assert "Identify governing authority" not in encoded
    assert "user_facing_subquestion" not in encoded
    assert "candidate_queries" not in encoded
    assert "finalized_queries" not in encoded
    assert "current_queries" not in encoded
    assert "queries_by_iteration" not in encoded
    assert '"query_text"' not in encoded


def test_official_current_obligations_are_shadow_hints_only() -> None:
    projection = build_query_plan_work_shadow_projection(
        _representative_search_work_plan_projection()
    )

    assert projection["acquisition_needs"]["official_current"]
    assert all(
        item["shadow_hint_only"]
        for item in projection["acquisition_needs"]["official_current"]
    )
    assert projection["provider_search_behavior_changed"] is False
    assert all(
        job["executes_runtime_work"] is False
        for jobs in projection["provider_jobs_by_component"].values()
        for job in jobs
    )
    assert projection["validation"]["executes_provider_calls"] is False


def test_query_plan_shadow_redacts_sensitive_fields() -> None:
    source = {
        "search_work_plan": {
            **_representative_search_work_plan_projection(),
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
            "token": "TOKEN_SENTINEL",
            "db_row": "DB_ROW_SENTINEL",
            "full_trace": "TRACE_SENTINEL",
        },
        "search_work_plan_projection": {
            "owner": "RunKernel.SearchWorkPlan",
            "construction_id": "construction:redaction",
        },
    }
    encoded = json.dumps(
        build_query_plan_work_shadow_projection(source),
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


def test_runtime_modules_do_not_import_or_call_query_plan_shadow_helper() -> None:
    forbidden_modules = {
        "core.search_work_plan_query_plan_shadow",
        "search_work_plan_query_plan_shadow",
    }
    forbidden_calls = {
        "build_query_plan_work_shadow_projection",
    }
    paths = (
        ROOT / "core" / "pipeline_orchestrator.py",
        ROOT / "core" / "run_kernel.py",
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_work_plan_shadow_runtime.py",
    )

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
        assert imported_names.isdisjoint(forbidden_modules), path
        assert called_names.isdisjoint(forbidden_calls), path


def test_query_plan_shadow_helper_keeps_closed_surface_boundary() -> None:
    source = SHADOW_ADAPTER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
        "core.query_production_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.runtime_prompt_assembly",
        "core.prompts",
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
