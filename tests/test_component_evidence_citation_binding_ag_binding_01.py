from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.answer_contract_authority_map import (
    ANSWER_CONTRACT_AUTHORITY_MAP_OWNER,
    ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION,
    build_answer_contract_authority_map,
)
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
from core.run_kernel import (
    ANSWER_CONTRACT_AUTHORITY_MAP_STAGE,
    COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE,
    EVIDENCE_LEDGER_STAGE,
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]
ANSWER_MAP_MODULE = ROOT / "core" / "answer_contract_authority_map.py"
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
        metadata={"fixture": "AG-COMPONENT-EVIDENCE-CITATION-BINDING-01"},
    )


def _safe_inputs() -> dict[str, Any]:
    contract = build_component_executor_contract_projection(_default_port_plan())
    return {
        "contract": contract,
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


def _kernel_with_custody(
    *,
    candidates: list[dict[str, Any]] | None = None,
) -> tuple[RunKernel, dict[str, Any]]:
    inputs = _safe_inputs()
    kernel = RunKernel.start(
        run_id="run-component-evidence-citation-binding",
        request_id="request-component-evidence-citation-binding",
    )
    answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=inputs["contract"],
    )
    kernel.build_offline_search_executor_bridge_projection(
        answer_contract_authority_map_projection=answer_map,
        component_executor_contract_projection=inputs["contract"],
        component_search_plan_projection=inputs["component_plan"],
        search_work_plan_projection=inputs["search_work"],
        query_plan_work_shadow_projection=inputs["query_shadow"],
        offline_candidate_observations=(
            _candidate_observations() if candidates is None else candidates
        ),
    )
    kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    refreshed = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=inputs["contract"],
    )
    return kernel, refreshed


def _components_by_id(projection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["component_id"]: item for item in projection["components"]}


def test_runkernel_refreshes_existing_answer_contract_binding_consumer() -> None:
    kernel, projection = _kernel_with_custody()

    assert projection["schema_version"] == ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION
    assert projection["owner"] == ANSWER_CONTRACT_AUTHORITY_MAP_OWNER
    assert projection["authority_boundary"]["map_owner"] == (
        "RunKernel.AnswerContractAuthorityMap"
    )
    assert kernel.state.projections[ANSWER_CONTRACT_AUTHORITY_MAP_STAGE] == projection
    assert kernel.state.projections[COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE]
    assert kernel.state.projections[OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE]
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE]
    assert kernel.state.issued_actions == {}
    assert projection["behavior_boundary_flags"]["provider_selected"] is False
    assert projection["behavior_boundary_flags"]["fetch_read_executed"] is False
    assert projection["behavior_boundary_flags"]["retrieval_executed"] is False


def test_four_component_binding_preserves_custody_obligations_candidates_and_gaps() -> None:
    _kernel, projection = _kernel_with_custody()
    by_component = _components_by_id(projection)

    assert set(by_component) == {"PostgreSQL", "MySQL", "Redis", "MongoDB"}
    assert projection["component_counts"]["required_component_count"] == 4
    assert projection["component_counts"]["full_component_success_count"] == 0
    for component_id, component in by_component.items():
        custody = component["evidence_custody"]
        binding = component["binding_status"]

        assert custody["component_scoped_source_custody_ref"]["available"] is True
        assert custody["component_source_obligation_refs"]
        assert custody["component_candidate_link_refs"]
        assert custody["component_custody_gap_refs"]
        assert custody["component_candidate_link_refs"][0]["component_id"] == component_id
        assert custody["component_candidate_link_refs"][0]["candidate_id"].startswith(
            f"candidate:{component_id.lower()}"
        )
        assert binding["component_candidate_link_refs"] == (
            custody["component_candidate_link_refs"]
        )
        assert binding["component_custody_gap_refs"] == (
            custody["component_custody_gap_refs"]
        )
        assert "candidate_not_fetched" in binding["blocker_reasons"]
        assert "candidate_not_read" in binding["blocker_reasons"]
        assert "candidate_not_admitted_by_evidenceledger" in binding["blocker_reasons"]


def test_offline_custody_candidates_remain_unbound_in_answer_contract_map() -> None:
    _kernel, projection = _kernel_with_custody()

    assert projection["final_answer_status"]["final_answer_allowed"] is None
    assert projection["final_answer_status"]["author_payload_ready"] is False
    for component in projection["components"]:
        custody = component["evidence_custody"]
        binding = component["binding_status"]

        assert custody["source_obligation_satisfied"] == "unsatisfied"
        assert binding["evidence_bound"] is False
        assert binding["citation_bound"] is False
        assert binding["source_obligation_bound"] is False
        assert binding["answer_value_bound"] is False
        assert binding["full_component_success"] is False
        assert binding["partial_user_answer_candidate"] is False
        assert binding["source_obligation_satisfied_from_ledger"] is False
        assert component["final_answer_status"]["final_answer_allowed"] is None
        assert component["final_answer_status"]["author_payload_ready"] is False
        assert all(
            candidate[field] is False
            for candidate in custody["component_candidate_link_refs"]
            for field in (
                "fetched",
                "read",
                "evidence_ledger_admitted",
                "citation_eligible",
                "source_obligation_satisfied",
                "semantic_coverage",
                "final_evidence",
                "evidence_bound",
                "citation_bound",
                "answer_value_bound",
                "full_component_success",
                "partial_user_answer_candidate",
                "final_answer_allowed",
                "author_payload_ready",
            )
        )


def test_missing_candidate_survives_as_component_specific_blocker() -> None:
    candidates = [
        item
        for item in _candidate_observations()
        if item["component_id"] != "MongoDB"
    ]
    _kernel, projection = _kernel_with_custody(candidates=candidates)
    mongodb = _components_by_id(projection)["MongoDB"]
    custody = mongodb["evidence_custody"]
    binding = mongodb["binding_status"]

    assert custody["component_source_obligation_refs"]
    assert custody["component_candidate_link_refs"] == []
    assert custody["component_custody_gap_refs"][0]["gap_type"] == (
        "missing_component_source_candidate"
    )
    assert binding["evidence_bound"] is False
    assert binding["citation_bound"] is False
    assert binding["source_obligation_bound"] is False
    assert binding["answer_value_bound"] is False
    assert binding["full_component_success"] is False
    assert "no_candidate" in binding["blocker_reasons"]
    assert "missing_component_source_candidate" in binding["blocker_reasons"]


def test_spoofed_binding_authority_fields_are_ignored_without_canonical_support() -> None:
    kernel, projection = _kernel_with_custody()
    ledger_projection = deepcopy(kernel.state.evidence_ledger.to_projection().to_dict())
    component_custody = ledger_projection["component_scoped_source_custody"]
    tempting = {
        "evidence_bound": True,
        "citation_bound": True,
        "source_obligation_bound": True,
        "answer_value_bound": True,
        "full_component_success": True,
        "source_obligation_satisfied": True,
        "partial_user_answer_candidate": True,
        "final_answer_allowed": True,
        "author_payload_ready": True,
    }
    component_custody.update(tempting)
    component_custody["per_component_custody"][0].update(tempting)
    component_custody["per_component_custody"][0]["candidate_links"][0].update(tempting)
    projection["components"][0]["binding_status"].update(tempting)

    refreshed = build_answer_contract_authority_map(
        component_executor_contract_projection=_safe_inputs()["contract"],
        evidence_ledger_projection=ledger_projection,
    ).to_projection()

    postgresql = _components_by_id(refreshed)["PostgreSQL"]
    for field in (
        "evidence_bound",
        "citation_bound",
        "source_obligation_bound",
        "answer_value_bound",
        "full_component_success",
        "partial_user_answer_candidate",
    ):
        assert postgresql["binding_status"][field] is False
    assert postgresql["evidence_custody"]["source_obligation_satisfied"] == (
        "unsatisfied"
    )
    assert refreshed["final_answer_status"]["final_answer_allowed"] is None
    assert refreshed["final_answer_status"]["author_payload_ready"] is False


def test_serialized_binding_path_does_not_retain_raw_private_sentinels() -> None:
    candidates = deepcopy(_candidate_observations())
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
    _kernel, projection = _kernel_with_custody(candidates=candidates)
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


def test_static_closed_surface_guard_for_answer_contract_binding_update() -> None:
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

    for path in (ANSWER_MAP_MODULE, RUN_KERNEL_MODULE):
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

    assert not (ROOT / "core" / "component_evidence_citation_binding.py").exists()
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "component_evidence_citation_binding" not in pipeline_source


def test_docs_name_binding_complete_and_next_sufficiency_fap_gate() -> None:
    doc_paths = [
        ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
        ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
        ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
        ROOT
        / "docs"
        / "architecture"
        / "AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    normalized = " ".join(combined.casefold().replace("`", "").split())

    assert "pr #320" in normalized
    assert "ag-component-scoped-source-custody-01" in normalized
    assert "candidate links remain non-evidence" in normalized
    assert "ag-component-evidence-citation-binding-01" in normalized
    assert "answercontractauthoritymap" in normalized
    assert "component evidence/citation binding" in normalized
    assert "ag-sufficiency-fap-component-readiness-01" in normalized
    assert "sufficiencyjudgment and finalanswerpacket" in normalized
    assert "pr #322" in normalized
    assert "ag-offline-xaxis-e2e-01" in normalized
    assert "offline x-axis end-to-end" in normalized
    assert "does not enable partial answers" in normalized
    assert "does not enable live validation" in normalized
    assert (
        "post-merge next gate is bounded live multi-component validation planning "
        "or execution"
    ) in normalized

    forbidden_stale_phrases = {
        "next gate is ag-component-evidence-citation-binding-01",
        "current next implementation target is component evidence/citation binding",
        "post-merge next gate is ag-component-evidence-citation-binding-01",
        "post-merge next gate is ag-sufficiency-fap-component-readiness-01",
        "post-merge next gate is ag-partial-answer-readiness-01",
    }
    for phrase in forbidden_stale_phrases:
        assert phrase not in normalized
