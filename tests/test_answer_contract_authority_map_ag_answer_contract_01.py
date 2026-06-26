from __future__ import annotations

import ast
import json
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
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
from core.run_kernel import ANSWER_CONTRACT_AUTHORITY_MAP_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "answer_contract_authority_map.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"


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
        metadata={"fixture": "AG-ANSWER-CONTRACT-AUTHORITY-MAP-01"},
    )


def _blocked_sufficiency_projection() -> dict[str, Any]:
    return RunSufficiencyJudgment(
        judgment_id="ag-answer-contract-map:block",
        decision=RunSufficiencyDecision.BLOCK_FINALIZATION,
        final_answer_posture=SufficiencyPosture.BLOCKED,
        required_obligations_satisfied=False,
        final_answer_allowed=False,
        readiness_reasons=("blocked_by_sufficiency",),
        final_packet_inputs={
            "decision": "block_finalization",
            "final_answer_posture": "blocked",
            "final_answer_allowed": False,
            "required_obligations_satisfied": False,
            "readiness_status": "blocked",
            "readiness_reasons": ["blocked_by_sufficiency"],
            "mandatory_caveats": ["finalization_blocked"],
            "prohibited_upgrades": ["do_not_call_author"],
        },
    ).to_projection()


def _projection_from_contract() -> dict[str, Any]:
    contract = build_component_executor_contract_projection(_default_port_plan())
    return build_answer_contract_authority_map(
        component_executor_contract_projection=contract,
    ).to_projection()


def test_four_component_official_doc_fixture_preserved_without_readiness() -> None:
    projection = _projection_from_contract()
    boundary = projection["authority_boundary"]

    assert projection["schema_version"] == ANSWER_CONTRACT_AUTHORITY_MAP_SCHEMA_VERSION
    assert projection["owner"] == ANSWER_CONTRACT_AUTHORITY_MAP_OWNER
    assert projection["run_authority_owned"] is True
    assert projection["derived_from_canonical_state"] is True
    assert boundary["root_owner"] == "RunKernel / RunAuthority"
    assert boundary["map_owner"] == ANSWER_CONTRACT_AUTHORITY_MAP_OWNER
    assert boundary["component_plan_role"] == (
        "legacy/compat input name for subordinate component-search planning"
    )
    assert boundary["component_search_plan_role"] == (
        "preferred subordinate name for component-scoped search planning input"
    )
    assert boundary["subordinate_component_search_surfaces"] == [
        "InitialAnswerContract",
        "ComponentPlan",
        "ComponentSearchPlan",
        "SearchWork",
        "QueryPlan",
        "future SearchExecutor",
    ]
    assert "SufficiencyJudgment" in boundary["readiness_owners"]
    assert "FinalAnswerPacket" in boundary["readiness_owners"]
    assert set(boundary["plan_presence_never_satisfies"]) >= {
        "final_answer_allowed",
        "partial_user_answer_candidate",
        "source_obligation_satisfied",
        "evidence_bound",
        "citation_bound",
        "answer_value_bound",
        "author_payload_ready",
        "full_component_success",
    }
    assert [item["component_id"] for item in projection["components"]] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]
    assert projection["component_counts"]["required_component_count"] == 4
    assert projection["component_counts"]["full_component_success_count"] == 0
    assert projection["final_answer_status"]["final_answer_allowed"] is None
    assert projection["final_answer_status"]["author_handoff_status"] == "absent"

    for component in projection["components"]:
        understanding = component["understanding"]
        work = component["subordinate_work"]
        custody = component["evidence_custody"]
        binding = component["binding_status"]

        assert understanding["answer_target"] == "default port"
        assert understanding["expected_answerable"] is True
        assert understanding["source_obligations"]
        assert understanding["official_source_required"] is True
        assert work["planned"] is True
        assert work["component_plan_ref"]["source"] == "ComponentPlan"
        assert work["component_plan_ref"]["source_alias"] == "ComponentSearchPlan"
        assert work["component_plan_ref"]["authority_role"] == (
            "subordinate_component_search_planning_input"
        )
        assert work["component_plan_ref"]["authority_owner"] == (
            ANSWER_CONTRACT_AUTHORITY_MAP_OWNER
        )
        assert set(work["component_plan_ref"]["cannot_decide"]) >= {
            "final_answer_allowed",
            "partial_user_answer_candidate",
            "source_obligation_satisfied",
            "evidence_bound",
            "citation_bound",
            "answer_value_bound",
            "author_payload_ready",
            "full_component_success",
        }
        assert work["search_work_ref"]["source"] == "SearchWork"
        assert work["query_plan_ref"]["source"] == "QueryPlanWorkShadow"
        assert work["searched_status"] == "not_started"
        assert work["fetch_read_status"] == "not_started"
        assert custody["source_obligation_satisfied"] == "unknown"
        assert binding["evidence_bound"] is False
        assert binding["citation_bound"] is False
        assert binding["source_obligation_bound"] is False
        assert binding["answer_value_bound"] is False
        assert binding["full_component_success"] is False
        assert component["final_answer_status"]["author_payload_ready"] is False

    assert all(value is False for value in projection["behavior_boundary_flags"].values())


def test_runkernel_projection_hook_owns_and_stores_map_without_actions() -> None:
    contract = build_component_executor_contract_projection(_default_port_plan())
    kernel = RunKernel.start(run_id="run-answer-map", request_id="request-answer-map")

    projection = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=contract,
    )

    assert projection["owner"] == "RunKernel.AnswerContractAuthorityMap"
    assert kernel.state.projections[ANSWER_CONTRACT_AUTHORITY_MAP_STAGE] == projection
    assert kernel.state.issued_actions == {}
    trace_projection = kernel.to_trace_fragment()["run_kernel"]["projections"][
        ANSWER_CONTRACT_AUTHORITY_MAP_STAGE
    ]
    assert trace_projection["owner"] == projection["owner"]
    assert [item["component_id"] for item in trace_projection["components"]] == [
        "PostgreSQL",
        "MySQL",
        "Redis",
        "MongoDB",
    ]


def test_component_plan_presence_is_subordinate_not_answer_authority() -> None:
    plan = _default_port_plan().to_dict()
    plan["final_answer_allowed"] = True
    plan["partial_user_answer_candidate"] = True
    plan["author_payload_ready"] = True
    plan["source_obligation_satisfied"] = True
    plan["evidence_bound"] = True
    plan["citation_bound"] = True
    plan["answer_value_bound"] = True
    plan["full_component_success"] = True
    plan["metadata"] = {
        "source_obligation_satisfied": True,
        "evidence_bound": True,
        "citation_bound": True,
        "answer_value_bound": True,
        "full_component_success": True,
    }

    projection = build_answer_contract_authority_map(
        component_plan_projection=plan,
    ).to_projection()
    component = projection["components"][0]

    assert projection["final_answer_status"]["final_answer_allowed"] is None
    assert projection["final_answer_status"]["author_payload_ready"] is False
    assert projection["final_answer_status"]["author_handoff_status"] == "absent"
    assert component["binding_status"]["evidence_bound"] is False
    assert component["binding_status"]["citation_bound"] is False
    assert component["binding_status"]["source_obligation_bound"] is False
    assert component["binding_status"]["answer_value_bound"] is False
    assert component["binding_status"]["partial_user_answer_candidate"] is False
    assert component["binding_status"]["full_component_success"] is False
    assert component["evidence_custody"]["source_obligation_satisfied"] == "unknown"


def test_search_work_and_query_plan_refs_cannot_satisfy_binding_or_readiness() -> None:
    contract = build_component_executor_contract_projection(_default_port_plan())
    search_work = dict(contract["search_work_plan"])
    query_shadow = dict(contract["query_plan_work_shadow_projection"])
    search_work["metadata"] = {
        **dict(search_work.get("metadata") or {}),
        "evidence_bound": True,
        "citation_bound": True,
        "source_obligation_satisfied": True,
        "answer_value_bound": True,
        "full_component_success": True,
        "final_answer_allowed": True,
        "partial_user_answer_candidate": True,
        "author_payload_ready": True,
    }
    query_shadow["runtime_consumed_by_query_plan"] = True
    query_shadow["final_answer_allowed"] = True
    query_shadow["partial_user_answer_candidate"] = True
    query_shadow["source_obligation_satisfied"] = True
    query_shadow["evidence_bound"] = True
    query_shadow["citation_bound"] = True
    query_shadow["answer_value_bound"] = True
    query_shadow["author_payload_ready"] = True
    query_shadow["full_component_success"] = True

    projection = build_answer_contract_authority_map(
        search_work_plan_projection=search_work,
        query_plan_work_shadow_projection=query_shadow,
    ).to_projection()
    postgresql = projection["components"][0]

    assert postgresql["subordinate_work"]["search_work_ref"]["source"] == "SearchWork"
    assert postgresql["subordinate_work"]["query_plan_ref"]["source"] == (
        "QueryPlanWorkShadow"
    )
    assert postgresql["binding_status"]["evidence_bound"] is False
    assert postgresql["binding_status"]["citation_bound"] is False
    assert postgresql["binding_status"]["source_obligation_bound"] is False
    assert postgresql["binding_status"]["answer_value_bound"] is False
    assert postgresql["binding_status"]["full_component_success"] is False
    assert postgresql["binding_status"]["partial_user_answer_candidate"] is False
    assert postgresql["evidence_custody"]["source_obligation_satisfied"] == "unknown"
    assert projection["final_answer_status"]["final_answer_allowed"] is None
    assert projection["final_answer_status"]["author_payload_ready"] is False


def test_citation_binding_does_not_cross_component_from_unrelated_citation() -> None:
    packet = {
        "packet_id": "packet:cross-component-citation",
        "semantic_packet_evidence_bindings": [
            {
                "component_id": "PostgreSQL",
                "component_digest": "digest:postgresql",
                "packet_evidence_id": "packet-evidence:postgresql",
                "origin_evidence_ref_id": "candidate:postgresql",
                "content_ref_id": "content:postgresql",
                "coverage_record_id": "coverage:postgresql",
            }
        ],
        "evidence_allowed": [
            {
                "evidence_id": "packet-evidence:mysql",
                "status": "evidence_allowed",
                "source_id": "source:mysql",
                "origin_evidence_ref_id": "candidate:mysql",
            }
        ],
        "citation_eligible": [
            {
                "citation_id": "citation:mysql",
                "evidence_id": "packet-evidence:mysql",
                "status": "citation_eligible",
                "source_id": "source:mysql",
                "component_id": "MySQL",
            }
        ],
        "source_obligations": [
            {
                "obligation_id": "PostgreSQL:source-requirement",
                "source_class": "official_docs",
                "status": "satisfied",
            }
        ],
    }
    projection = build_answer_contract_authority_map(
        component_plan_projection=_default_port_plan().to_dict(),
        final_answer_packet_projection=packet,
        component_coverage_projection={
            "answer_component_id": "PostgreSQL",
            "coverage_record_id": "coverage:postgresql",
            "coverage_record_digest": "digest:coverage:postgresql",
            "coverage_state": "satisfied",
            "ledger_custody_status": "satisfied",
            "semantic_support_status": "supports",
        },
    ).to_projection()
    postgresql = next(
        item for item in projection["components"] if item["component_id"] == "PostgreSQL"
    )

    assert postgresql["binding_status"]["evidence_bound"] is True
    assert postgresql["binding_status"]["source_obligation_bound"] is True
    assert postgresql["binding_status"]["answer_value_bound"] is True
    assert postgresql["binding_status"]["citation_bound"] is False
    assert postgresql["binding_status"]["citation_binding_refs"] == []
    assert postgresql["binding_status"]["full_component_success"] is False


def test_citation_binding_accepts_component_specific_packet_evidence_relation() -> None:
    packet = {
        "packet_id": "packet:component-specific-citation",
        "semantic_packet_evidence_bindings": [
            {
                "component_id": "PostgreSQL",
                "component_digest": "digest:postgresql",
                "packet_evidence_id": "packet-evidence:postgresql",
                "origin_evidence_ref_id": "candidate:postgresql",
                "content_ref_id": "content:postgresql",
                "coverage_record_id": "coverage:postgresql",
            }
        ],
        "evidence_allowed": [
            {
                "evidence_id": "packet-evidence:postgresql",
                "status": "evidence_allowed",
                "source_id": "source:postgresql",
                "origin_evidence_ref_id": "candidate:postgresql",
            }
        ],
        "citation_eligible": [
            {
                "citation_id": "citation:postgresql",
                "evidence_id": "packet-evidence:postgresql",
                "status": "citation_eligible",
                "source_id": "source:postgresql",
            },
            {
                "citation_id": "citation:mysql",
                "evidence_id": "packet-evidence:mysql",
                "status": "citation_eligible",
                "source_id": "source:mysql",
                "component_id": "MySQL",
            },
        ],
        "source_obligations": [
            {
                "obligation_id": "PostgreSQL:source-requirement",
                "source_class": "official_docs",
                "status": "satisfied",
            }
        ],
    }
    projection = build_answer_contract_authority_map(
        component_plan_projection=_default_port_plan().to_dict(),
        final_answer_packet_projection=packet,
        component_coverage_projection={
            "answer_component_id": "PostgreSQL",
            "coverage_record_id": "coverage:postgresql",
            "coverage_record_digest": "digest:coverage:postgresql",
            "coverage_state": "satisfied",
            "ledger_custody_status": "satisfied",
            "semantic_support_status": "supports",
        },
    ).to_projection()
    postgresql = next(
        item for item in projection["components"] if item["component_id"] == "PostgreSQL"
    )
    mysql = next(item for item in projection["components"] if item["component_id"] == "MySQL")

    assert postgresql["binding_status"]["evidence_bound"] is True
    assert postgresql["binding_status"]["source_obligation_bound"] is True
    assert postgresql["binding_status"]["answer_value_bound"] is True
    assert postgresql["binding_status"]["citation_bound"] is True
    assert postgresql["binding_status"]["citation_binding_refs"] == [
        {
            "citation_id": "citation:postgresql",
            "evidence_id": "packet-evidence:postgresql",
            "source_id": "source:postgresql",
            "relation": "component_evidence_ref",
        }
    ]
    assert postgresql["binding_status"]["full_component_success"] is True
    assert mysql["binding_status"]["citation_bound"] is False


def test_sufficiency_and_blocked_fap_own_final_answer_and_author_block() -> None:
    final_authority = {
        "owner": "RunKernel.FinalAnswerPacket",
        "canonical_state": True,
        "packet_id": "packet:block",
        "readiness_status": "blocked",
        "readiness_reasons": ["blocked_by_sufficiency"],
        "author_payload_ref": {
            "status": "blocked",
            "packet_id": "packet:block",
            "readiness_status": "blocked",
            "author_input_deferred": True,
            "blocked_before_author_input": True,
            "authority_payload": {
                "packet_id": "packet:block",
                "final_answer_allowed": False,
                "final_answer_posture": "blocked",
            },
        },
        "missing_source_obligation_count": 0,
        "mandatory_caveat_count": 1,
        "prohibited_upgrade_count": 1,
    }
    blocked_summary = {
        "schema_version": "blocked_final_answer_packet_safe_summary_v1",
        "blocked_fap": True,
        "packet_id": "packet:block",
        "status": "blocked",
        "readiness_status": "blocked",
        "final_answer_allowed": False,
    }

    projection = build_answer_contract_authority_map(
        component_plan_projection=_default_port_plan().to_dict(),
        sufficiency_judgment_projection=_blocked_sufficiency_projection(),
        final_answer_authority_projection=final_authority,
        blocked_final_answer_packet_summary=blocked_summary,
    ).to_projection()

    assert projection["sufficiency_status"]["status"] == "blocked"
    assert projection["sufficiency_status"]["final_answer_allowed"] is False
    assert projection["final_answer_status"]["final_answer_allowed"] is False
    assert projection["final_answer_status"]["author_handoff_status"] == "blocked"
    assert projection["final_answer_status"]["author_payload_ready"] is False
    assert projection["final_answer_status"]["blocked_fap_summary_ref"]["available"] is True
    assert all(
        component["final_answer_status"]["author_payload_ready"] is False
        for component in projection["components"]
    )


def test_serialized_map_does_not_retain_raw_or_private_sentinels() -> None:
    plan = _default_port_plan().to_dict()
    plan["metadata"] = {
        "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK",
        "raw_provider_payload": "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
        "raw_model_response": "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
        "private_logs": "PRIVATE_LOG_SHOULD_NOT_LEAK",
        "safe_note": "visible-safe-note",
    }
    projection = build_answer_contract_authority_map(
        component_plan_projection=plan,
        evidence_ledger_projection={
            "owner": "RunKernel.EvidenceLedger",
            "schema_version": "evidence_ledger_ag91j_v1",
            "source_requirements": [],
            "candidate_records": [],
            "private_logs": "PRIVATE_LOG_SHOULD_NOT_LEAK",
        },
    ).to_projection()
    encoded = json.dumps(projection, sort_keys=True)

    assert "RAW_PROMPT_SHOULD_NOT_LEAK" not in encoded
    assert "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK" not in encoded
    assert "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK" not in encoded
    assert "PRIVATE_LOG_SHOULD_NOT_LEAK" not in encoded
    assert projection["behavior_boundary_flags"]["raw_prompt_retained"] is False
    assert projection["behavior_boundary_flags"]["full_trace_retained"] is False


def test_answer_contract_authority_map_static_boundary_guard() -> None:
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
    run_kernel_source = RUN_KERNEL.read_text(encoding="utf-8")
    run_kernel_tree = ast.parse(run_kernel_source)
    action_attrs = {
        item.attr for item in ast.walk(run_kernel_tree) if isinstance(item, ast.Attribute)
    }
    assert "ANSWER_CONTRACT_AUTHORITY_MAP_STAGE" in run_kernel_source
    assert "ANSWER_CONTRACT_AUTHORITY_MAP" not in action_attrs


def test_component_search_plan_docs_keep_answer_authority_subordinate() -> None:
    doc_paths = [
        ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
        ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
        ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
        ROOT / "docs" / "architecture" / "AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in doc_paths)
    normalized = " ".join(combined.casefold().replace("`", "").split())

    assert "answercontractauthoritymap owns answer-component authority mapping" in normalized
    assert "componentplan is legacy/compat input terminology" in normalized
    assert "componentsearchplan is the preferred subordinate" in normalized
    assert "they do not decide answerability" in normalized
    assert "post-ag-component-searchplan-subordination-01" in normalized
    assert "completed componentsearchplan naming / subordination cleanup" in normalized
    assert "complete in pr #318" in normalized
    assert "next productization gate is the offline searchexecutor bridge" in normalized
    assert "offline searchexecutor bridge. this is the next gate" in normalized
    assert "runtime searchexecutor wiring is still not part of pr #318" in normalized
    assert "no live validation" in normalized

    forbidden_claims = {
        "componentplan owns answer authority",
        "componentplan owns answer-component authority",
        "componentplan is root authority",
        "componentplan is top-level answer authority",
        "componentsearchplan owns answer authority",
        "componentsearchplan is root authority",
        "componentsearchplan is top-level answer authority",
        "searchexecutor decides answerability",
        "current productization cleanup is componentsearchplan",
        "current next implementation target is componentsearchplan naming",
    }
    for claim in forbidden_claims:
        assert claim not in normalized
