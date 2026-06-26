from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.answer_contract_authority_map import build_answer_contract_authority_map
from core.component_executor_contract import (
    AmbiguityStatus,
    ComponentPlan,
    ComponentPlanComponent,
    FreshnessKind,
    FreshnessPolicy,
    PlannerSource,
    SearchIntent,
    SearchIntentPurpose,
    SourceClass,
    SourceRequirement,
    SuccessCriteria,
    build_component_executor_contract_projection,
)
from core.offline_search_executor_bridge import (
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER,
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_PROOF_CLASS,
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_SCHEMA_VERSION,
    build_offline_search_executor_bridge_projection,
)
from core.run_kernel import OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "offline_search_executor_bridge.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


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
        metadata={"fixture": "AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01"},
    )


def _safe_inputs() -> dict[str, Any]:
    contract = build_component_executor_contract_projection(_default_port_plan())
    answer_map = build_answer_contract_authority_map(
        component_executor_contract_projection=contract,
    ).to_projection()
    return {
        "contract": contract,
        "answer_map": answer_map,
        "component_plan": contract["component_plan"],
        "search_work": contract["search_work_plan"],
        "query_shadow": contract["query_plan_work_shadow_projection"],
    }


def _candidate_observations() -> list[dict[str, Any]]:
    domains = {
        "PostgreSQL": "postgresql.org",
        "MySQL": "dev.mysql.com",
        "Redis": "redis.io",
        "MongoDB": "mongodb.com",
    }
    return [
        {
            "candidate_id": f"candidate:{component.lower()}:default-port",
            "component_id": component,
            "url": f"https://{domain}/docs/default-port",
            "domain": domain,
            "title": f"{component} default port documentation",
            "source_class_hint": "official_docs",
            "source_obligation_id": f"{component}:source-requirement",
        }
        for component, domain in domains.items()
    ]


def _bridge(**overrides: Any) -> dict[str, Any]:
    inputs = _safe_inputs()
    params = {
        "answer_contract_authority_map_projection": inputs["answer_map"],
        "component_executor_contract_projection": inputs["contract"],
        "component_search_plan_projection": inputs["component_plan"],
        "search_work_plan_projection": inputs["search_work"],
        "query_plan_work_shadow_projection": inputs["query_shadow"],
        "offline_candidate_observations": _candidate_observations(),
    }
    params.update(overrides)
    return build_offline_search_executor_bridge_projection(**params).to_projection()


def test_four_component_work_survives_into_offline_executor_observations() -> None:
    projection = _bridge()

    assert projection["schema_version"] == OFFLINE_SEARCH_EXECUTOR_BRIDGE_SCHEMA_VERSION
    assert projection["owner"] == OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER
    assert projection["proof_class"] == OFFLINE_SEARCH_EXECUTOR_BRIDGE_PROOF_CLASS
    assert projection["proof_class"] == "offline_product_path_projection_proof"
    assert projection["offline_only"] is True
    assert projection["live_search_executed"] is False
    assert projection["provider_selected"] is False
    assert projection["provider_called"] is False
    assert projection["model_called"] is False
    assert projection["fetch_read_executed"] is False
    assert projection["retrieval_executed"] is False
    assert projection["evidence_ledger_admission_performed"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["evidence_bound"] is False
    assert projection["citation_bound"] is False
    assert projection["answer_value_bound"] is False
    assert projection["partial_user_answer_candidate"] is False
    assert projection["author_payload_ready"] is False
    assert projection["final_answer_allowed"] is None

    components = projection["component_observations"]
    assert [item["component_id"] for item in components] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    for component in components:
        assert component["answer_target"] == "default port"
        assert component["execution_status"] == "offline_observed"
        assert component["source_obligation_refs"]
        assert component["provider_work_refs"]
        assert component["component_search_plan_ref"]["source"] == "ComponentPlan"
        assert (
            component["component_search_plan_ref"]["source_alias"]
            == "ComponentSearchPlan"
        )
        assert component["search_work_ref"]["source"] == "SearchWork"
        assert component["query_plan_ref"]["source"] == "QueryPlanWorkShadow"
        assert component["source_obligation_satisfied"] is False
        assert component["evidence_bound"] is False
        assert component["citation_bound"] is False
        assert component["citation_eligible"] is False
        assert component["answer_value_bound"] is False
        assert component["semantic_coverage"] is False
        assert component["full_component_success"] is False
        assert component["author_payload_ready"] is False
        assert component["final_answer_allowed"] is None


def test_candidate_observations_are_grouped_and_shaped_for_future_ledger_intake() -> None:
    projection = _bridge()

    for component in projection["component_observations"]:
        refs = component["candidate_observation_refs"]
        assert len(refs) == 1
        candidate = refs[0]
        assert candidate["component_id"] == component["component_id"]
        assert candidate["candidate_input_kind"] == "offline_candidate_observation"
        assert candidate["future_evidence_ledger_intake_shape"] is True
        ledger_shape = candidate["evidence_ledger_candidate_observation"]
        assert ledger_shape["candidate_id"] == candidate["candidate_id"]
        assert ledger_shape["component_id"] == component["component_id"]
        assert ledger_shape["admission_status"] == (
            "not_admitted_offline_bridge_only"
        )
        assert candidate["fetched"] is False
        assert candidate["read"] is False
        assert candidate["evidence_ledger_admitted"] is False
        assert candidate["source_obligation_satisfied"] is False
        assert candidate["citation_eligible"] is False
        assert candidate["semantic_coverage"] is False
        assert candidate["final_evidence"] is False
        assert component["offline_candidate_observation_refs_are_evidence"] is False


def test_spoofed_readiness_fields_are_rejected_without_authority_upgrade() -> None:
    inputs = _safe_inputs()
    component_plan = deepcopy(inputs["component_plan"])
    search_work = deepcopy(inputs["search_work"])
    query_shadow = deepcopy(inputs["query_shadow"])
    candidates = deepcopy(_candidate_observations())
    tempting = {
        "final_answer_allowed": True,
        "partial_user_answer_candidate": True,
        "source_obligation_satisfied": True,
        "evidence_bound": True,
        "citation_bound": True,
        "answer_value_bound": True,
        "author_payload_ready": True,
        "full_component_success": True,
    }
    component_plan.update(tempting)
    component_plan["components"][0].update(tempting)
    search_work.update(tempting)
    search_work["components"][0].update(tempting)
    query_shadow.update(tempting)
    query_shadow["components"][0].update(tempting)
    candidates[0].update(tempting)

    projection = _bridge(
        component_search_plan_projection=component_plan,
        search_work_plan_projection=search_work,
        query_plan_work_shadow_projection=query_shadow,
        offline_candidate_observations=candidates,
    )
    encoded_claims = json.dumps(
        projection["rejected_authority_claims"],
        sort_keys=True,
    )

    assert projection["final_answer_allowed"] is None
    assert projection["source_obligation_satisfied"] is False
    assert projection["evidence_bound"] is False
    assert projection["citation_bound"] is False
    assert projection["answer_value_bound"] is False
    assert projection["partial_user_answer_candidate"] is False
    assert projection["author_payload_ready"] is False
    assert projection["full_component_success"] is False
    for field in tempting:
        assert field in encoded_claims
    postgresql = projection["component_observations"][0]
    assert postgresql["source_obligation_satisfied"] is False
    assert postgresql["evidence_bound"] is False
    assert postgresql["citation_bound"] is False
    assert postgresql["answer_value_bound"] is False
    assert postgresql["full_component_success"] is False


def test_runkernel_stores_bridge_projection_without_actions() -> None:
    inputs = _safe_inputs()
    kernel = RunKernel.start(
        run_id="run-offline-search-executor-bridge",
        request_id="request-offline-search-executor-bridge",
    )
    answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=inputs["contract"],
    )

    projection = kernel.build_offline_search_executor_bridge_projection(
        answer_contract_authority_map_projection=answer_map,
        component_executor_contract_projection=inputs["contract"],
        component_search_plan_projection=inputs["component_plan"],
        search_work_plan_projection=inputs["search_work"],
        query_plan_work_shadow_projection=inputs["query_shadow"],
        offline_candidate_observations=_candidate_observations(),
    )

    assert projection["owner"] == OFFLINE_SEARCH_EXECUTOR_BRIDGE_OWNER
    assert projection["proof_class"] == "offline_product_path_projection_proof"
    assert kernel.state.offline_search_executor_bridge_projection == projection
    assert kernel.state.offline_search_executor_bridge_history == [projection]
    assert kernel.state.projections[OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE] == projection
    assert kernel.state.issued_actions == {}
    trace_projection = kernel.to_trace_fragment()["run_kernel"]["projections"][
        OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE
    ]
    assert trace_projection["owner"] == projection["owner"]
    assert [item["component_id"] for item in trace_projection["component_observations"]] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]


def test_serialized_bridge_does_not_retain_raw_private_sentinels() -> None:
    inputs = _safe_inputs()
    component_plan = deepcopy(inputs["component_plan"])
    component_plan["metadata"] = {
        "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK",
        "raw_provider_payload": "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
        "raw_model_response": "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
        "private_logs": "PRIVATE_LOG_SHOULD_NOT_LEAK",
        "db_cache_rows": "DB_CACHE_ROW_SHOULD_NOT_LEAK",
        "full_trace": "FULL_TRACE_SHOULD_NOT_LEAK",
    }
    candidates = _candidate_observations()
    candidates[0].update(
        {
            "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK",
            "raw_provider_payload": "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
            "raw_model_response": "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
            "private_logs": "PRIVATE_LOG_SHOULD_NOT_LEAK",
            "db_cache_rows": "DB_CACHE_ROW_SHOULD_NOT_LEAK",
            "full_trace": "FULL_TRACE_SHOULD_NOT_LEAK",
        }
    )

    projection = _bridge(
        component_search_plan_projection=component_plan,
        offline_candidate_observations=candidates,
    )
    encoded = json.dumps(projection, sort_keys=True)

    for sentinel in (
        "RAW_PROMPT_SHOULD_NOT_LEAK",
        "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
        "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
        "PRIVATE_LOG_SHOULD_NOT_LEAK",
        "DB_CACHE_ROW_SHOULD_NOT_LEAK",
        "FULL_TRACE_SHOULD_NOT_LEAK",
    ):
        assert sentinel not in encoded
    assert projection["raw_private_retention"]["raw_prompt_retained"] is False
    assert projection["raw_private_retention"]["full_trace_retained"] is False


def test_static_closed_surface_guard_for_offline_search_executor_bridge() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.runtime_prompt_assembly",
        "core.prompts",
        "core.final_answer_runtime_adapter",
        "core.final_answer_runtime_assembly",
        "core.author_execution_runtime",
        "core.private_broker",
        "core.live_adapter",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "brave_reconnaissance",
        "fetch_page",
        "fetch_url_text",
        "execute_author_action",
        "derive_author_input_payload",
        "format_citation",
        "render_citations",
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
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "offline_search_executor_bridge" not in pipeline_source
    assert "OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE" not in pipeline_source


def test_docs_name_offline_inert_bridge_and_next_custody_phase() -> None:
    doc_paths = [
        ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
        ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
        ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
        ROOT / "docs" / "architecture" / "AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    normalized = " ".join(combined.casefold().replace("`", "").split())

    assert "pr #319 / ag-offline-search-executor-bridge-01" in normalized
    assert (
        "completed the offline runkernel-owned searchexecutor bridge"
        in normalized
    )
    assert "completed offline searchexecutor bridge" in normalized
    assert "offline searchexecutor bridge is offline and inert" in normalized
    assert "does not perform live provider/search/fetch/read/retrieval work" in normalized
    assert "does not admit evidenceledger custody or satisfy source obligations" in normalized
    assert "keeps candidate observations non-evidence" in normalized
    assert "not user-facing runtime search" in normalized
    assert "pr #320" in normalized
    assert "ag-component-scoped-source-custody-01" in normalized
    assert "adds evidenceledger component-scoped source custody" in normalized
    assert "post-merge next gate" in normalized
    assert "ag-component-evidence-citation-binding-01" in normalized

    forbidden_stale_phrases = {
        "current next implementation target is the offline searchexecutor bridge",
        "next productization gate is the offline searchexecutor bridge",
        "next gate is ag-component-scoped-source-custody-01",
        "current next implementation target is component-scoped source custody",
    }
    for phrase in forbidden_stale_phrases:
        assert phrase not in normalized
