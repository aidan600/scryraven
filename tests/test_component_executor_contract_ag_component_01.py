from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.component_executor_contract import (
    AmbiguityStatus,
    ComponentPlan,
    ComponentPlanComponent,
    ComponentSearchPlan,
    ComponentSearchPlanComponent,
    FreshnessKind,
    FreshnessPolicy,
    PlannerSource,
    SearchIntent,
    SearchIntentPurpose,
    SourceClass,
    SourceRequirement,
    SuccessCriteria,
    build_component_executor_contract_projection,
    summarize_component_scorekeeping,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "component_executor_contract.py"


def _default_port_component(label: str, domain: str) -> ComponentPlanComponent:
    return ComponentPlanComponent(
        component_id=label,
        label=label,
        aliases=(),
        entity_type="software_project",
        answer_target="default port",
        expected_answerable=True,
        source_requirement=SourceRequirement(
            source_class=SourceClass.OFFICIAL_DOCS,
            citation_required=True,
            fetch_read_required=True,
        ),
        allowed_domains=(domain,),
        disambiguation_status=AmbiguityStatus.CLEAR,
        search_intents=(
            SearchIntent(
                query_text=f"{label} official documentation default port",
                safe_query_template="{label} official documentation default port",
                purpose=SearchIntentPurpose.OFFICIAL_DOC_LOOKUP,
                freshness_policy=FreshnessPolicy(FreshnessKind.STABLE_DOCS),
                allowed_domains=(domain,),
            ),
            SearchIntent(
                query_text=f"{label} default port official docs",
                safe_query_template="{label} default port official docs",
                purpose=SearchIntentPurpose.DEFAULT_VALUE_LOOKUP,
                freshness_policy=FreshnessPolicy(FreshnessKind.STABLE_DOCS),
                allowed_domains=(domain,),
            ),
        ),
        success_criteria=SuccessCriteria(
            evidence_required=True,
            citation_required=True,
            answer_value_required=True,
        ),
    )


def _default_port_plan() -> ComponentPlan:
    return ComponentPlan(
        plan_id="component-plan:default-ports-official-docs",
        planner_source=PlannerSource.OFFLINE_FIXTURE,
        user_query_digest="sha256:default-port-official-docs-fixture",
        ambiguity_status=AmbiguityStatus.CLEAR,
        freshness_policy=FreshnessPolicy(FreshnessKind.STABLE_DOCS),
        components=(
            _default_port_component("PostgreSQL", "postgresql.org"),
            _default_port_component("MySQL", "dev.mysql.com"),
            _default_port_component("Redis", "redis.io"),
            _default_port_component("MongoDB", "mongodb.com"),
        ),
        metadata={"fixture": "AG-COMPONENT-EXECUTOR-CONTRACT-01"},
    )


def _single_component_plan() -> ComponentPlan:
    return ComponentPlan(
        plan_id="component-plan:postgresql-default-port",
        planner_source=PlannerSource.OFFLINE_FIXTURE,
        user_query_digest="sha256:postgresql-default-port-fixture",
        ambiguity_status=AmbiguityStatus.CLEAR,
        freshness_policy=FreshnessPolicy(FreshnessKind.STABLE_DOCS),
        components=(_default_port_component("PostgreSQL", "postgresql.org"),),
    )


def _weird_entity_plan() -> ComponentPlan:
    phrase = "depleting transcendent life flask of the mixologist"
    return ComponentPlan(
        plan_id="component-plan:weird-entity",
        planner_source=PlannerSource.OFFLINE_FIXTURE,
        user_query_digest="sha256:weird-entity-fixture",
        ambiguity_status=AmbiguityStatus.NEEDS_DISAMBIGUATION,
        freshness_policy=FreshnessPolicy(FreshnessKind.UNSPECIFIED),
        components=(
            ComponentPlanComponent(
                component_id=phrase,
                label=phrase,
                aliases=(),
                entity_type="unknown_phrase",
                answer_target="identify official or primary reference",
                expected_answerable=False,
                source_requirement=SourceRequirement(
                    source_class=SourceClass.UNSPECIFIED,
                    citation_required=True,
                    fetch_read_required=False,
                ),
                allowed_domains=None,
                disambiguation_status=AmbiguityStatus.NEEDS_DISAMBIGUATION,
                search_intents=(
                    SearchIntent(
                        query_text=phrase,
                        purpose=SearchIntentPurpose.DISAMBIGUATION,
                        freshness_policy=FreshnessPolicy(FreshnessKind.UNSPECIFIED),
                    ),
                ),
            ),
        ),
    )


def test_component_plan_schema_preserves_safe_four_component_fixture() -> None:
    plan = _default_port_plan()
    payload = plan.to_dict()
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == "component_plan_executor_contract_v1"
    assert payload["planner_source"] == "offline_fixture"
    assert payload["user_query_digest"] == "sha256:default-port-official-docs-fixture"
    assert [item["component_id"] for item in payload["components"]] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert [item["label"] for item in payload["components"]] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert {item["answer_target"] for item in payload["components"]} == {"default port"}
    assert {
        tuple(item["allowed_domains"])
        for item in payload["components"]
    } == {
        ("postgresql.org",),
        ("dev.mysql.com",),
        ("redis.io",),
        ("mongodb.com",),
    }
    assert all(
        item["source_requirement"] == {
            "source_class": "official_docs",
            "citation_required": True,
            "fetch_read_required": True,
        }
        for item in payload["components"]
    )
    assert all(
        intent["freshness_policy"]["kind"] == "stable_docs"
        for component in payload["components"]
        for intent in component["search_intents"]
    )
    assert all(
        {"official_doc_lookup", "default_value_lookup"}
        == {intent["purpose"] for intent in component["search_intents"]}
        for component in payload["components"]
    )
    for forbidden in ("raw_prompt", "provider_payload", "model_response", "raw_provider_payload"):
        assert forbidden not in encoded


def test_component_search_plan_alias_serializes_without_drift() -> None:
    plan = _single_component_plan()
    alias_plan = ComponentSearchPlan.from_dict(plan.to_dict())

    assert ComponentSearchPlan is ComponentPlan
    assert ComponentSearchPlanComponent is ComponentPlanComponent
    assert isinstance(alias_plan, ComponentPlan)
    assert alias_plan.to_dict() == plan.to_dict()


def test_component_plan_maps_to_search_work_and_query_work_with_all_component_ids() -> None:
    plan = _default_port_plan()
    contract = build_component_executor_contract_projection(plan)
    component_ids = [
        item["component_id"] for item in contract["component_plan"]["components"]
    ]

    assert component_ids == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert "search_work_plan" not in contract
    assert "query_plan_work_shadow_projection" not in contract
    assert sorted(contract["planned_query_terms_by_component"]) == [
        "MongoDB",
        "MySQL",
        "PostgreSQL",
        "Redis",
    ]
    assert all(
        item["answer_target"] == "default port"
        for item in contract["component_plan"]["components"]
    )


def test_planned_query_terms_remain_component_local() -> None:
    plan = _default_port_plan()
    contract = build_component_executor_contract_projection(plan)
    terms = contract["planned_query_terms_by_component"]

    assert set(terms) == {"PostgreSQL", "MySQL", "Redis", "MongoDB"}
    assert all(terms[component_id] for component_id in terms)
    assert contract["behavior_boundary_flags"]["search_executed"] is False
    assert contract["behavior_boundary_flags"]["provider_selected"] is False


def test_stable_docs_freshness_does_not_apply_recent_only_filter() -> None:
    contract = build_component_executor_contract_projection(_default_port_plan())
    encoded = json.dumps(contract, sort_keys=True)

    for component in contract["component_plan"]["components"]:
        for intent in component["search_intents"]:
            freshness = intent["freshness_policy"]
            assert freshness["kind"] == "stable_docs"
            assert freshness["applies_recent_only_filter"] is False
            assert "recency_window" not in freshness

    assert "past-week" not in encoded
    assert '"kind": "recent"' not in encoded
    assert '"kind": "news"' not in encoded


def test_scorekeeping_counts_unsearched_unfetched_unbound_without_success_or_author() -> None:
    plan = _default_port_plan()
    summary = summarize_component_scorekeeping(plan)

    assert summary["planned_component_count"] == 4
    assert summary["searched_component_count"] == 0
    assert summary["fetched_component_count"] == 0
    assert summary["evidence_bound_component_count"] == 0
    assert summary["citation_bound_component_count"] == 0
    assert summary["source_obligation_satisfied_component_count"] == 0
    assert summary["unsearched_component_ids"] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert summary["unfetched_component_ids"] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert summary["evidence_unbound_component_ids"] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert summary["full_component_success"] is False
    assert summary["full_component_success_count"] == 0
    assert summary["semantic_partial_coverage_observed"] is False
    assert summary["planned_component_presence_is_user_safe_partial_answer"] is False
    assert summary["partial_user_answer_candidate"] is False
    assert summary["author_called"] is False


def test_scorekeeping_distinguishes_partial_semantic_coverage_from_full_success() -> None:
    plan = _default_port_plan()
    summary = summarize_component_scorekeeping(
        plan,
        searched_component_ids=("PostgreSQL",),
        fetched_component_ids=("PostgreSQL",),
    )

    assert summary["searched_component_count"] == 1
    assert summary["fetched_component_count"] == 1
    assert summary["semantic_partial_coverage_observed"] is True
    assert summary["partial_semantic_coverage_component_ids"] == ["PostgreSQL"]
    assert summary["full_component_success"] is False
    assert summary["partial_user_answer_candidate"] is False
    postgresql = summary["components"][0]
    assert postgresql["partial_semantic_coverage"] is True
    assert postgresql["full_component_success"] is False
    assert postgresql["partial_user_answer_ready"] is False


def test_single_component_plan_uses_same_mapping_and_observability_path() -> None:
    plan = _single_component_plan()
    contract = build_component_executor_contract_projection(plan)

    assert contract["component_plan"]["components"][0]["component_id"] == "PostgreSQL"
    assert "search_work_plan" not in contract
    assert len(contract["planned_query_terms_by_component"]["PostgreSQL"]) >= 1


def test_weird_entity_phrase_is_preserved_as_one_component_without_disambiguation_search() -> None:
    plan = _weird_entity_plan()
    contract = build_component_executor_contract_projection(plan)
    phrase = "depleting transcendent life flask of the mixologist"

    assert plan.ambiguity_status is AmbiguityStatus.NEEDS_DISAMBIGUATION
    assert contract["component_plan"]["components"][0]["component_id"] == phrase
    assert phrase in contract["planned_query_terms_by_component"]
    assert contract["behavior_boundary_flags"]["search_executed"] is False
    assert contract["behavior_boundary_flags"]["provider_selected"] is False


def test_component_executor_contract_module_has_offline_boundary() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.runtime_prompt_assembly",
        "core.prompts",
        "core.final_answer_packet",
        "core.author_execution_runtime",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "brave_reconnaissance",
        "fetch_page",
        "fetch_url_text",
        "format_citation",
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


def test_component_plan_projection_does_not_retain_sensitive_metadata() -> None:
    plan = ComponentPlan(
        plan_id="component-plan:redaction",
        planner_source=PlannerSource.OFFLINE_FIXTURE,
        user_query_digest="sha256:redaction-fixture",
        ambiguity_status=AmbiguityStatus.CLEAR,
        freshness_policy=FreshnessPolicy(FreshnessKind.STABLE_DOCS),
        components=(_default_port_component("PostgreSQL", "postgresql.org"),),
        metadata={
            "raw_prompt": "RAW_PROMPT_SENTINEL",
            "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
            "raw_model_response": "RAW_MODEL_SENTINEL",
            "safe_note": "visible-safe-note",
        },
    )

    payload: dict[str, Any] = build_component_executor_contract_projection(plan)
    encoded = json.dumps(payload, sort_keys=True)

    assert "visible-safe-note" in encoded
    assert "RAW_PROMPT_SENTINEL" not in encoded
    assert "RAW_PROVIDER_SENTINEL" not in encoded
    assert "RAW_MODEL_SENTINEL" not in encoded
