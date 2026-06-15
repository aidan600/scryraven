from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.query_plan import QUERY_PLAN_TRACE_KEY, QueryPlan, QueryPlanRole, authorize_retrieval_queries
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.search_work_query_plan_consumption import allocate_existing_queries_by_search_work

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "core" / "search_work_query_plan_consumption.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _clean(value: str) -> str:
    return " ".join(str(value or "").split())[:300]


def _search_work_projection() -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "components": [
            {"component_id": "component-fee"},
            {"component_id": "component-legal"},
            {"component_id": "component-api"},
            {"component_id": "component-numeric"},
        ],
        "source_obligations_by_component": {
            "component-fee": [
                {
                    "obligation_id": "obligation-official-fee",
                    "kind": "official_current",
                    "strictness": "required",
                    "required_source_class": "official_current_rules",
                }
            ],
            "component-legal": [
                {
                    "obligation_id": "obligation-legal-deadline",
                    "kind": "legal_current_primary",
                    "strictness": "required",
                    "required_source_class": "legal_or_regulatory_text",
                }
            ],
            "component-api": [
                {
                    "obligation_id": "obligation-api-docs",
                    "kind": "canonical_documentation",
                    "strictness": "required",
                    "required_source_class": "primary_source_documents",
                }
            ],
            "component-numeric": [
                {
                    "obligation_id": "obligation-source-bound-numeric",
                    "kind": "source_bound_numeric",
                    "strictness": "required",
                    "required_source_class": "sourced_numeric_values",
                }
            ],
        },
        "provider_jobs_by_component": {
            "component-fee": [
                {
                    "work_id": "provider-official-fee",
                    "work_kind": "official_candidate_acquisition",
                    "executes_runtime_work": False,
                }
            ],
            "component-legal": [
                {
                    "work_id": "provider-legal-currentness",
                    "work_kind": "conflict_currentness_check",
                    "executes_runtime_work": False,
                }
            ],
            "component-api": [
                {
                    "work_id": "provider-api-canonical",
                    "work_kind": "canonical_extraction",
                    "executes_runtime_work": False,
                }
            ],
            "component-numeric": [
                {
                    "work_id": "provider-numeric-extract",
                    "work_kind": "fetch_read_extract",
                    "executes_runtime_work": False,
                }
            ],
        },
    }


def _adapter() -> Any:
    return build_query_plan_runtime_adapter(
        run_id="ag96e2",
        primary_entity="Acme Filing System",
        entities_list=["Acme Filing System"],
        core_topic="Acme Filing System fee deadline API parameter numeric rate",
        user_query="What are the current official fee, legal deadline, API parameter, and numeric rate?",
        intent="general",
        clean=_clean,
    )


def test_no_searchwork_projection_keeps_authorize_retrieval_queries_byte_equivalent() -> None:
    queries = ["fee update", "legal deadline", "API parameter docs", "fee duplicate"]
    baseline = authorize_retrieval_queries(
        queries,
        primary_entity="Acme Filing System",
        entities_list=["Acme Filing System"],
        core_topic="Acme Filing System",
        user_query="Acme Filing System fee deadline API parameter",
        intent="general",
        clean=_clean,
        include_official_bias=False,
        max_len=3,
    )
    repeated = authorize_retrieval_queries(
        queries,
        primary_entity="Acme Filing System",
        entities_list=["Acme Filing System"],
        core_topic="Acme Filing System",
        user_query="Acme Filing System fee deadline API parameter",
        intent="general",
        clean=_clean,
        include_official_bias=False,
        max_len=3,
    )

    assert repeated[1] == baseline[1]
    assert repeated[0].to_dict() == baseline[0].to_dict()


def test_invalid_searchwork_projection_falls_back_without_reordering() -> None:
    plan = QueryPlan(plan_id="ag96e2-invalid")
    queries = ["fee update", "legal deadline", "API parameter docs"]

    plan, admitted = plan.consume_search_work_for_existing_queries(
        queries,
        search_work_projection={"schema_version": "bad"},
        max_len=2,
        origin="unit",
        role=QueryPlanRole.INITIAL,
    )

    trace = plan.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert admitted == queries
    assert trace["search_work_consumption"]["search_work_consumed_by_query_plan"] is False
    assert (
        trace["search_work_consumption"]["fallback_reason"]
        == "search_work_projection_missing_query_plan_or_plan_components"
    )


def test_multipart_searchwork_allocates_component_coverage_before_duplicate_fee() -> None:
    adapter = _adapter()
    candidates = [
        "official current filing fee",
        "fee amount update",
        "legal deadline appeal rule",
        "API parameter documentation",
    ]

    allocated = adapter.consume_search_work_for_existing_queries(
        candidates,
        search_work_projection=_search_work_projection(),
        max_len=3,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    assert allocated == [
        "official current filing fee",
        "legal deadline appeal rule",
        "API parameter documentation",
    ]
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    consumption = trace["search_work_consumption"]
    assert consumption["search_work_consumed_by_query_plan"] is True
    assert consumption["rejected_over_budget_queries"] == ["fee amount update"]
    assert "component-numeric" in consumption["unfilled_component_ids"]
    finalized = [
        item for item in trace["items"]
        if item.get("phase") == "search_work_component_allocation"
        and item["status"] == "finalized"
    ]
    assert [item["authorized_query"] for item in finalized] == allocated
    assert finalized[0]["metadata"]["search_work_component_id"] == "component-fee"
    assert finalized[0]["metadata"]["source_obligation_candidate_ids"] == [
        "obligation-official-fee"
    ]
    assert finalized[0]["metadata"]["provider_job_candidate_ids"] == [
        "provider-official-fee"
    ]


def test_multipart_max_len_two_records_unfilled_without_generating_query() -> None:
    result = allocate_existing_queries_by_search_work(
        candidate_queries=[
            "official current filing fee",
            "legal deadline appeal rule",
            "API parameter documentation",
        ],
        query_plan_context={},
        search_work_projection=_search_work_projection(),
        max_len=2,
        origin="unit",
        role="initial",
        phase="unit",
    )

    payload = result.to_dict()
    assert payload["admitted_query_order"] == [
        "official current filing fee",
        "legal deadline appeal rule",
    ]
    assert payload["rejected_over_budget_queries"] == ["API parameter documentation"]
    assert "component-api" in payload["unfilled_component_ids"]
    assert payload["behavior_boundary_flags"]["new_executable_query_text_generated"] is False


def test_official_legal_canonical_and_numeric_components_are_tagged_independently() -> None:
    adapter = _adapter()

    allocated = adapter.consume_search_work_for_existing_queries(
        [
            "legal deadline appeal rule",
            "API parameter documentation",
            "numeric rate amount source",
            "official current filing fee",
        ],
        search_work_projection=_search_work_projection(),
        max_len=4,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    assert allocated == [
        "official current filing fee",
        "legal deadline appeal rule",
        "API parameter documentation",
        "numeric rate amount source",
    ]
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    metadata_by_query = {
        item["authorized_query"]: item["metadata"]
        for item in trace["items"]
        if item.get("phase") == "search_work_component_allocation"
        and item["status"] == "finalized"
    }
    assert metadata_by_query["official current filing fee"]["search_work_component_id"] == "component-fee"
    assert metadata_by_query["legal deadline appeal rule"]["search_work_component_id"] == "component-legal"
    assert metadata_by_query["API parameter documentation"]["search_work_component_id"] == "component-api"
    assert metadata_by_query["numeric rate amount source"]["search_work_component_id"] == "component-numeric"
    assert "custody_satisfied" not in metadata_by_query["official current filing fee"]
    assert "calculation_executed" not in metadata_by_query["numeric rate amount source"]
    assert trace["search_work_consumption"]["behavior_boundary_flags"][
        "source_obligations_marked_satisfied"
    ] is False


def test_provider_job_hints_remain_non_executing_metadata_and_execution_gets_strings() -> None:
    adapter = _adapter()
    allocated = adapter.consume_search_work_for_existing_queries(
        [
            "official current filing fee",
            "legal deadline appeal rule",
            "API parameter documentation",
        ],
        search_work_projection=_search_work_projection(),
        max_len=3,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    executed = adapter.admit_execution_queries(
        allocated,
        iteration=1,
        recovery_active=False,
    )
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]

    assert executed == allocated
    assert trace["authorized_queries_by_iteration"]["1"] == allocated
    assert all(isinstance(query, str) for query in executed)
    assert trace["search_work_consumption"]["behavior_boundary_flags"][
        "provider_job_hints_executed"
    ] is False
    assert trace["search_work_consumption"]["behavior_boundary_flags"][
        "retrieval_behavior_changed"
    ] is False


def test_consumption_trace_redacts_sensitive_projection_fields() -> None:
    projection = {
        **_search_work_projection(),
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "FULL_TRACE_SENTINEL",
    }
    result = allocate_existing_queries_by_search_work(
        candidate_queries=["official current filing fee"],
        query_plan_context={},
        search_work_projection=projection,
        max_len=1,
        origin="unit",
        role="initial",
        phase="unit",
    )
    encoded = json.dumps(result.to_dict(), sort_keys=True)

    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_for_ag96e2_consumption_boundary() -> None:
    helper_imports = _imports(HELPER)
    assert not any(module.startswith("core.") for module in helper_imports)
    helper_source = HELPER.read_text(encoding="utf-8")
    for token in (
        "ask_model",
        "brave_reconnaissance",
        "search_web_results",
        "fetch_page",
        "process_search_queries",
        "format_citation",
        "FinalAnswerPacket",
    ):
        assert token not in helper_source

    forbidden_imports = {
        "core.search_work_query_plan_consumption",
        "search_work_query_plan_consumption",
    }
    for path in (
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "retrieval_scheduler.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "runtime_prompt_assembly.py",
        ROOT / "core" / "final_answer_packet.py",
        ROOT / "core" / "final_answer_runtime_assembly.py",
        ROOT / "core" / "author_execution_runtime.py",
    ):
        assert _imports(path).isdisjoint(forbidden_imports), path

    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "allocate_existing_queries_by_search_work" not in pipeline_source
    assert "source_obligations_by_component" not in pipeline_source
    assert "provider_jobs_by_component" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
