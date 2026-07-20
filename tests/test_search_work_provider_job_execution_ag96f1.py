from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.query_plan import QUERY_PLAN_TRACE_KEY, QueryPlanRole
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import execute_query_plan_admission_action
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_kernel import RunKernel
from core.search_work_provider_job_execution import (
    PROVIDER_JOB_EXECUTION_TRACE_KEY,
    build_provider_job_execution_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "core" / "search_work_provider_job_execution.py"
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
                    "source_obligation_ids": ["obligation-official-fee"],
                    "executes_runtime_work": False,
                }
            ],
            "component-legal": [
                {
                    "work_id": "provider-legal-currentness",
                    "work_kind": "conflict_currentness_check",
                    "source_obligation_ids": ["obligation-legal-deadline"],
                    "executes_runtime_work": False,
                }
            ],
            "component-api": [
                {
                    "work_id": "provider-api-canonical",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["obligation-api-docs"],
                    "executes_runtime_work": False,
                }
            ],
            "component-numeric": [
                {
                    "work_id": "provider-numeric-extract",
                    "work_kind": "fetch_read_extract",
                    "source_obligation_ids": ["obligation-source-bound-numeric"],
                    "executes_runtime_work": False,
                }
            ],
        },
    }


def _active_search_work_projection() -> dict[str, Any]:
    shadow = _search_work_projection()
    components: list[dict[str, Any]] = []
    provider_jobs: list[dict[str, Any]] = []
    for component in shadow["components"]:
        component_id = component["component_id"]
        accepted_component_ref = {
            "component_id": component_id,
            "component_revision": "1",
            "component_digest": f"digest:{component_id}",
            "requirement_posture": "required",
        }
        components.append(
            {
                "component_id": component_id,
                "source_obligations": shadow["source_obligations_by_component"][
                    component_id
                ],
                "metadata": {
                    "accepted_component_ref": accepted_component_ref,
                    "search_requirement_refs": [
                        {
                            "requirement_id": f"requirement:{component_id}",
                            "component_id": component_id,
                        }
                    ],
                },
            }
        )
        for job in shadow["provider_jobs_by_component"][component_id]:
            provider_jobs.append(
                {
                    "provider_job_id": job["work_id"],
                    "provider_job_kind": job["work_kind"],
                    "component_ids": [component_id],
                    "source_obligation_ids": job["source_obligation_ids"],
                }
            )
    return {
        "trace_key": "search_work_plan",
        "passive": False,
        "runtime_consumed": True,
        "components": components,
        "provider_jobs": provider_jobs,
        "metadata": {
            "search_work_plan_id": "search-work:ag96f1-active",
            "accepted_contract_ref": {
                "contract_version": "1",
                "contract_digest": "contract-digest:ag96f1",
            },
        },
    }


def _adapter() -> Any:
    return build_query_plan_runtime_adapter(
        run_id="ag96f1",
        primary_entity="Acme Filing System",
        entities_list=["Acme Filing System"],
        core_topic="Acme Filing System fee deadline API parameter numeric rate",
        user_query=(
            "What are the current official fee, legal deadline, API parameter, "
            "and numeric rate?"
        ),
        intent="general",
        clean=_clean,
    )


def _router_state() -> Any:
    return build_router_query_preparation_state(
        query="Acme Filing System fee deadline API parameter numeric rate",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "general_research",
                "query_type": "rule",
                "core_topic": "Acme Filing System",
                "entities": ["Acme Filing System"],
                "primary_entity": "Acme Filing System",
                "is_academic": False,
            }
        ),
    )


def _route_posture() -> dict[str, Any]:
    return {
        "intent": "general",
        "report_type": "general_research",
        "query_type": "rule",
        "primary_entity": "Acme Filing System",
        "entities": ["Acme Filing System"],
        "is_academic": False,
        "routing_override_applied": False,
        "routing_override_reason": None,
        "focus_academic": False,
        "force_intent_news": False,
        "complexity": "medium",
        "results_per_query": 6,
        "search_depth": "basic",
        "top_chunks": 20,
        "max_iterations": 2,
    }


def _records(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        record["provider_job_id"]: record
        for record in handoff.get("provider_job_execution_records", [])
    }


def test_no_searchwork_or_queryplan_metadata_creates_no_execution_records() -> None:
    handoff = build_provider_job_execution_handoff(
        search_work_projection=None,
        query_plan_trace={},
        current_queries=["ordinary query"],
    )

    assert handoff["trace_key"] == PROVIDER_JOB_EXECUTION_TRACE_KEY
    assert handoff["provider_job_execution_record_count"] == 0
    assert handoff["fallback_reason"] == "search_work_projection_absent"
    assert handoff["behavior_boundary_flags"]["retrieval_behavior_changed"] is False
    assert handoff["behavior_boundary_flags"]["query_text_generated"] is False


def test_ag96e2_metadata_creates_records_for_admitted_provider_jobs() -> None:
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

    handoff = build_provider_job_execution_handoff(
        search_work_projection=_search_work_projection(),
        query_plan_trace=adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY],
        current_queries=allocated,
    )
    by_job = _records(handoff)

    assert set(by_job) == {
        "provider-official-fee",
        "provider-legal-currentness",
        "provider-api-canonical",
        "provider-numeric-extract",
    }
    assert by_job["provider-official-fee"]["component_id"] == "component-fee"
    assert by_job["provider-official-fee"]["provider_job_kind"] == (
        "official_candidate_acquisition"
    )
    assert by_job["provider-official-fee"]["source_obligation_ids"] == [
        "obligation-official-fee"
    ]
    assert by_job["provider-official-fee"]["authorized_queries"] == [
        "official current filing fee"
    ]
    assert by_job["provider-official-fee"]["execution_status"] == "admitted"
    assert by_job["provider-official-fee"]["handoff_to_existing_retrieval_loop"] is True
    assert handoff["admitted_query_handoff_summary"]["authorized_queries"] == allocated


def test_rejected_over_budget_items_are_deferred_not_admitted() -> None:
    adapter = _adapter()
    allocated = adapter.consume_search_work_for_existing_queries(
        [
            "official current filing fee",
            "legal deadline appeal rule",
            "API parameter documentation",
            "numeric rate amount source",
        ],
        search_work_projection=_search_work_projection(),
        max_len=3,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    handoff = build_provider_job_execution_handoff(
        search_work_projection=_search_work_projection(),
        query_plan_trace=adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY],
        current_queries=allocated,
    )
    numeric = _records(handoff)["provider-numeric-extract"]

    assert "numeric rate amount source" not in allocated
    assert numeric["execution_status"] == "deferred"
    assert numeric["deferred_reason"] == "query_plan_item_rejected"
    assert numeric["handoff_to_existing_retrieval_loop"] is False
    assert "provider-numeric-extract" in handoff["deferred_provider_jobs"]


def test_unfilled_searchwork_components_become_deferred_without_generated_query() -> None:
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

    handoff = build_provider_job_execution_handoff(
        search_work_projection=_search_work_projection(),
        query_plan_trace=adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY],
        current_queries=allocated,
    )
    numeric = _records(handoff)["provider-numeric-extract"]

    assert numeric["execution_status"] == "deferred"
    assert numeric["authorized_queries"] == []
    assert numeric["deferred_reason"] == "search_work_component_unfilled"
    assert "component-numeric" in handoff["deferred_unfilled_work"]["component_ids"]
    assert handoff["behavior_boundary_flags"]["query_text_generated"] is False


def test_official_and_numeric_records_do_not_claim_custody_or_calculation() -> None:
    adapter = _adapter()
    allocated = adapter.consume_search_work_for_existing_queries(
        [
            "numeric rate amount source",
            "official current filing fee",
        ],
        search_work_projection=_search_work_projection(),
        max_len=2,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    handoff = build_provider_job_execution_handoff(
        search_work_projection=_search_work_projection(),
        query_plan_trace=adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY],
        current_queries=allocated,
    )
    by_job = _records(handoff)
    official = by_job["provider-official-fee"]
    numeric = by_job["provider-numeric-extract"]

    assert official["official_current_custody_satisfied"] is False
    assert official["source_obligations_satisfied"] is False
    assert official["evidence_refs"] == []
    assert numeric["quant_extraction_executed"] is False
    assert numeric["calculation_executed"] is False
    assert numeric["source_bound_numeric_evidence_phase_deferred"] is True


def test_runtime_admission_payload_exposes_handoff_without_changing_queries() -> None:
    kernel = RunKernel.start(run_id="ag96f1-runtime", request_id="request")
    action = kernel.authorize_query_plan_admission(
        inputs={"candidate_source": "search_planner", "candidate_count": 4}
    )
    adapter = _adapter()
    candidate_strategies = [
        {
            "strategy_id": "strategy:component-fee:primary",
            "component_id": "component-fee",
            "candidate_kind": "primary",
            "candidate_query_text": "official current filing fee",
            "requested_role": "official_bias",
            "source_obligation_candidate_ids": ["obligation-official-fee"],
        },
        {
            "strategy_id": "strategy:component-legal:primary",
            "component_id": "component-legal",
            "candidate_kind": "primary",
            "candidate_query_text": "legal deadline appeal rule",
            "requested_role": "initial",
            "source_obligation_candidate_ids": ["obligation-legal-deadline"],
        },
        {
            "strategy_id": "strategy:component-api:primary",
            "component_id": "component-api",
            "candidate_kind": "primary",
            "candidate_query_text": "API parameter documentation",
            "requested_role": "canonical_bias",
            "source_obligation_candidate_ids": ["obligation-api-docs"],
        },
        {
            "strategy_id": "strategy:component-numeric:primary",
            "component_id": "component-numeric",
            "candidate_kind": "primary",
            "candidate_query_text": "numeric rate amount source",
            "requested_role": "initial",
            "source_obligation_candidate_ids": [
                "obligation-source-bound-numeric"
            ],
        },
    ]
    candidate_queries = [
        strategy["candidate_query_text"] for strategy in candidate_strategies
    ]

    result = execute_query_plan_admission_action(
        action,
        query_authority=adapter,
        router_query_preparation_contract=_router_state(),
        candidate_queries=candidate_queries,
        candidate_strategies=candidate_strategies,
        candidate_source="search_planner",
        query_type="rule",
        current_date="June 15, 2026",
        max_queries=4,
        route_runtime_posture=_route_posture(),
        search_work_projection=_active_search_work_projection(),
    )

    payload = result.observation.payload
    handoff = payload["provider_job_execution_handoff"]

    assert payload["provider_job_execution_handoff_present"] is True
    assert result.current_queries == handoff["admitted_query_handoff_summary"][
        "authorized_queries"
    ]
    assert result.current_queries == candidate_queries
    assert all(isinstance(query, str) for query in result.current_queries)
    assert handoff["behavior_boundary_flags"]["retrieval_behavior_changed"] is False
    assert handoff["behavior_boundary_flags"]["query_plan_admission_order_changed"] is False


def test_redaction_removes_private_projection_and_trace_fields() -> None:
    projection = {
        **_search_work_projection(),
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "FULL_TRACE_SENTINEL",
    }
    adapter = _adapter()
    allocated = adapter.consume_search_work_for_existing_queries(
        ["official current filing fee"],
        search_work_projection=projection,
        max_len=1,
        origin="researcher_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )

    handoff = build_provider_job_execution_handoff(
        search_work_projection=projection,
        query_plan_trace={
            **adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY],
            "raw_model_response": "RAW_MODEL_SENTINEL",
        },
        current_queries=allocated,
    )
    encoded = json.dumps(handoff, sort_keys=True)

    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
        "RAW_MODEL_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_for_provider_job_execution_boundary() -> None:
    helper_imports = _imports(HELPER)
    assert not any(module.startswith("core.") for module in helper_imports)
    helper_source = HELPER.read_text(encoding="utf-8")
    for token in (
        "ask_model",
        "brave_reconnaissance",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "fetch_page",
        "process_search_queries",
        "format_citation",
        "FinalAnswerPacket",
        "AuthorExecutor",
    ):
        assert token not in helper_source

    forbidden_imports = {
        "core.search_work_provider_job_execution",
        "search_work_provider_job_execution",
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
    assert "build_provider_job_execution_handoff" not in pipeline_source
    assert "provider_jobs_by_component" not in pipeline_source
    assert "source_obligations_by_component" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
