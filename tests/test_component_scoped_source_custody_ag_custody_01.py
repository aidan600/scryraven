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
from core.evidence_ledger import (
    COMPONENT_SCOPED_SOURCE_CUSTODY_NEXT_CONSUMER,
    COMPONENT_SCOPED_SOURCE_CUSTODY_SCHEMA_VERSION,
)
from core.run_kernel import (
    COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE,
    EVIDENCE_LEDGER_STAGE,
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER_MODULE = ROOT / "core" / "evidence_ledger.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
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
        metadata={"fixture": "AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01"},
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


def _kernel_with_bridge(
    *,
    candidates: list[dict[str, Any]] | None = None,
) -> tuple[RunKernel, dict[str, Any]]:
    inputs = _safe_inputs()
    kernel = RunKernel.start(
        run_id="run-component-scoped-source-custody",
        request_id="request-component-scoped-source-custody",
    )
    answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=inputs["contract"],
    )
    bridge = kernel.build_offline_search_executor_bridge_projection(
        answer_contract_authority_map_projection=answer_map,
        component_executor_contract_projection=inputs["contract"],
        component_search_plan_projection=inputs["component_plan"],
        search_work_plan_projection=inputs["search_work"],
        query_plan_work_shadow_projection=inputs["query_shadow"],
        offline_candidate_observations=(
            _candidate_observations() if candidates is None else candidates
        ),
    )
    return kernel, bridge


def _custody_by_component(projection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["component_id"]: item
        for item in projection["per_component_custody"]
    }


def test_runkernel_evidenceledger_product_consumer_stores_custody_without_actions() -> None:
    kernel, bridge = _kernel_with_bridge()

    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()

    assert bridge == kernel.state.projections[OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE]
    assert projection["schema_version"] == COMPONENT_SCOPED_SOURCE_CUSTODY_SCHEMA_VERSION
    assert projection["owner"] == "RunKernel.EvidenceLedger"
    assert projection["canonical_state"] is True
    assert projection["next_consumer"] == COMPONENT_SCOPED_SOURCE_CUSTODY_NEXT_CONSUMER
    assert kernel.state.component_scoped_source_custody_projection == projection
    assert kernel.state.component_scoped_source_custody_history == [projection]
    assert kernel.state.projections[COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE] == projection
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == ledger_projection
    assert (
        ledger_projection["component_scoped_source_custody"]["per_component_custody"]
        == projection["per_component_custody"]
    )
    assert kernel.state.issued_actions == {}
    assert bridge["live_search_executed"] is False
    assert bridge["fetch_read_executed"] is False
    assert bridge["retrieval_executed"] is False


def test_four_component_custody_preserves_obligations_and_candidate_grouping() -> None:
    kernel, _bridge = _kernel_with_bridge()
    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )
    by_component = _custody_by_component(projection)

    assert projection["component_count"] == 4
    assert projection["source_obligation_count"] >= 4
    assert projection["candidate_link_count"] == 4
    assert set(by_component) == {"PostgreSQL", "MySQL", "Redis", "MongoDB"}
    for component_id, custody in by_component.items():
        obligations = custody["source_obligation_refs"]
        candidates = custody["candidate_links"]
        assert custody["component_id"] == component_id
        assert obligations
        assert all(item["component_id"] == component_id for item in obligations)
        assert any(
            item["source_obligation_id"].startswith(component_id)
            for item in obligations
        )
        assert any(
            item.get("required_source_class") == "official_docs"
            for item in obligations
        )
        assert len(candidates) == 1
        assert candidates[0]["component_id"] == component_id
        assert component_id.lower() in candidates[0]["candidate_id"]
        assert candidates[0]["source_obligation_id"].startswith(component_id)


def test_candidate_links_are_non_evidence_and_obligations_not_satisfied() -> None:
    kernel, _bridge = _kernel_with_bridge()
    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )

    assert projection["candidate_links_are_evidence"] is False
    assert projection["source_obligations_satisfied_by_candidate_presence"] is False
    for component in projection["per_component_custody"]:
        for obligation in component["source_obligation_refs"]:
            assert obligation["source_obligation_satisfied"] is False
            assert obligation["source_obligation_status"] in {
                "pending_candidate",
                "blocked_by_unfetched_or_unread_candidate",
                "missing_candidate",
            }
            assert obligation["source_obligation_status"] != "satisfied"
        for candidate in component["candidate_links"]:
            assert candidate["candidate_kind"] == "offline_bridge_candidate_observation"
            assert candidate["fetched"] is False
            assert candidate["read"] is False
            assert candidate["evidence_ledger_admitted"] is False
            assert candidate["citation_eligible"] is False
            assert candidate["source_obligation_satisfied"] is False
            assert candidate["semantic_coverage"] is False
            assert candidate["final_evidence"] is False

    ledger_requirements = (
        kernel.state.evidence_ledger.to_projection().to_dict()["source_requirements"]
    )
    assert ledger_requirements
    assert {item["status"] for item in ledger_requirements} == {"unsatisfied"}


def test_custody_gap_for_component_obligation_without_candidate() -> None:
    candidates = [
        item
        for item in _candidate_observations()
        if item["component_id"] != "MongoDB"
    ]
    kernel, _bridge = _kernel_with_bridge(candidates=candidates)

    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )
    mongodb = _custody_by_component(projection)["MongoDB"]

    assert mongodb["candidate_links"] == []
    assert mongodb["source_obligation_refs"][0]["source_obligation_status"] == (
        "missing_candidate"
    )
    assert mongodb["custody_gaps"][0]["gap_type"] == (
        "missing_component_source_candidate"
    )
    assert projection["candidate_link_count"] == 3
    assert projection["final_answer_allowed"] is False
    assert projection["partial_user_answer_candidate"] is False
    assert projection["evidence_bound"] is False
    assert projection["citation_bound"] is False
    assert projection["answer_value_bound"] is False
    assert projection["author_payload_ready"] is False


def test_spoofed_readiness_and_binding_fields_are_ignored() -> None:
    candidates = deepcopy(_candidate_observations())
    tempting = {
        "source_obligation_satisfied": True,
        "evidence_bound": True,
        "citation_bound": True,
        "answer_value_bound": True,
        "full_component_success": True,
        "partial_user_answer_candidate": True,
        "final_answer_allowed": True,
        "author_payload_ready": True,
    }
    candidates[0].update(tempting)
    kernel, bridge = _kernel_with_bridge(candidates=candidates)
    bridge = deepcopy(bridge)
    bridge.update(tempting)
    bridge["component_observations"][0].update(tempting)

    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge(
            bridge_projection=bridge,
        )
    )

    for field in tempting:
        assert projection[field] is False
    postgresql = _custody_by_component(projection)["PostgreSQL"]
    for field in tempting:
        assert postgresql[field] is False
    assert postgresql["source_obligation_refs"][0]["source_obligation_satisfied"] is False
    assert postgresql["source_obligation_refs"][0]["source_obligation_status"] != (
        "satisfied"
    )


def test_authority_non_upgrade_flags_remain_false() -> None:
    kernel, _bridge = _kernel_with_bridge()
    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )

    for field in (
        "final_answer_allowed",
        "partial_user_answer_candidate",
        "evidence_bound",
        "citation_bound",
        "answer_value_bound",
        "author_payload_ready",
    ):
        assert projection[field] is False
    for value in projection["behavior_boundary_flags"].values():
        assert value is False


def test_serialized_custody_projection_does_not_retain_raw_private_sentinels() -> None:
    candidates = deepcopy(_candidate_observations())
    candidates[0]["metadata"] = {
        "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK",
        "safe_marker": "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
        "raw_model_response": "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
        "private_logs": "PRIVATE_LOG_SHOULD_NOT_LEAK",
        "db_cache_rows": "DB_CACHE_ROW_SHOULD_NOT_LEAK",
        "full_trace": "FULL_TRACE_SHOULD_NOT_LEAK",
    }
    kernel, bridge = _kernel_with_bridge(candidates=candidates)
    bridge = deepcopy(bridge)
    bridge["safe_marker"] = "RAW_PROMPT_SHOULD_NOT_LEAK"

    projection = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge(
            bridge_projection=bridge,
        )
    )
    encoded = json.dumps(projection, sort_keys=True)
    ledger_encoded = json.dumps(
        kernel.state.evidence_ledger.to_projection().to_dict(),
        sort_keys=True,
    )

    for sentinel in (
        "RAW_PROMPT_SHOULD_NOT_LEAK",
        "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
        "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
        "PRIVATE_LOG_SHOULD_NOT_LEAK",
        "DB_CACHE_ROW_SHOULD_NOT_LEAK",
        "FULL_TRACE_SHOULD_NOT_LEAK",
    ):
        assert sentinel not in encoded
        assert sentinel not in ledger_encoded


def test_static_closed_surface_guard_for_component_source_custody() -> None:
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
    for path in (LEDGER_MODULE, RUN_KERNEL_MODULE):
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
        assert imported_names.isdisjoint(forbidden_import_roots)
        assert called_names.isdisjoint(forbidden_calls)

    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "component_scoped_source_custody" not in pipeline_source
    assert "COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE" not in pipeline_source


def test_docs_name_completed_bridge_and_component_custody_next_gate() -> None:
    doc_paths = [
        ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
        ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
        ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
        ROOT / "docs" / "architecture" / "AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    normalized = " ".join(combined.casefold().replace("`", "").split())

    assert "pr #319" in normalized
    assert "completed the offline runkernel-owned searchexecutor bridge" in normalized
    assert "pr #320" in normalized
    assert "ag-component-scoped-source-custody-01" in normalized
    assert "evidenceledger component-scoped source custody" in normalized
    assert "adds evidenceledger component-scoped source custody" in normalized
    assert "candidate links remain non-evidence" in normalized
    assert "until fetched/read/admitted" in normalized or (
        "until fetched, read, and admitted" in normalized
    )
    assert "unsatisfied/pending" in normalized
    assert "rather than satisfied by candidate presence" in normalized
    assert "post-merge next gate" in normalized
    assert "ag-component-evidence-citation-binding-01" in normalized
    assert "component evidence/citation binding" in normalized
    assert "merge-stable phase posture" in normalized

    forbidden_stale_phrases = {
        "next gate is ag-component-scoped-source-custody-01",
        "current next implementation target is component-scoped source custody",
        "the next gate is ag-component-scoped-source-custody-01",
        "this is the next gate: ag-component-scoped-source-custody-01",
        "should consume bridge observations for evidenceledger component-scoped",
    }
    for phrase in forbidden_stale_phrases:
        assert phrase not in normalized
