from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
from core.final_answer_packet import FinalAnswerReadinessStatus
from core.final_answer_packet_runtime import (
    build_safe_blocked_fap_summary,
    execute_final_answer_packet_prepare_action,
)
from core.run_authority_sufficiency_runtime import (
    execute_sufficiency_judgment_handoff_from_scope,
)
from core.run_kernel import (
    ANSWER_CONTRACT_AUTHORITY_MAP_STAGE,
    COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE,
    EVIDENCE_LEDGER_STAGE,
    FINAL_ANSWER_PACKET_STAGE,
    OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PIPELINE = CORE / "pipeline_orchestrator.py"
COMPONENT_IDS = ("PostgreSQL", "MySQL", "Redis", "MongoDB")
COMPONENT_ID_SET = set(COMPONENT_IDS)
SENTINELS = (
    "RAW_PROMPT_SHOULD_NOT_LEAK",
    "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
    "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
    "PRIVATE_LOG_SHOULD_NOT_LEAK",
    "DB_CACHE_ROW_SHOULD_NOT_LEAK",
    "FULL_TRACE_SHOULD_NOT_LEAK",
)
CHANGED_PYTHON_SURFACES = (
    ROOT / "tests" / "test_answer_contract_authority_map_ag_answer_contract_01.py",
    ROOT / "tests" / "test_component_evidence_citation_binding_ag_binding_01.py",
    ROOT / "tests" / "test_component_scoped_source_custody_ag_custody_01.py",
    ROOT / "tests" / "test_offline_search_executor_bridge_ag_search_executor_01.py",
    ROOT / "tests" / "test_sufficiency_fap_component_readiness_ag_readiness_01.py",
    Path(__file__),
)


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
        metadata={"fixture": "AG-OFFLINE-XAXIS-E2E-01"},
    )


def _candidate_observations(
    *,
    include_private_sentinels: bool = False,
) -> list[dict[str, Any]]:
    domains = {
        "PostgreSQL": "postgresql.org",
        "MySQL": "dev.mysql.com",
        "Redis": "redis.io",
        "MongoDB": "mongodb.com",
    }
    candidates = [
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
    if include_private_sentinels:
        candidates[0]["metadata"] = {
            "raw_prompt": SENTINELS[0],
            "raw_provider_payload": SENTINELS[1],
            "raw_model_response": SENTINELS[2],
            "private_logs": SENTINELS[3],
            "db_cache_rows": SENTINELS[4],
            "full_trace": SENTINELS[5],
        }
    return candidates


def _run_contract_projection() -> dict[str, Any]:
    return {
        "contract_id": "run-contract:offline-xaxis-default-ports",
        "schema_version": "test_run_contract_offline_xaxis_e2e_v1",
        "selected_template_ids": [],
        "source_requirements": [],
        "source_requirement_summary": [],
        "inference_policy": {},
        "conflict_policy": {},
        "numeric_policy": {},
        "final_posture_policy": {"partial_allowed_if": []},
    }


def _runtime_scope(
    *,
    run_contract: dict[str, Any],
    ledger_projection: dict[str, Any],
    answer_map: dict[str, Any],
) -> dict[str, Any]:
    return {
        "evidence_ledger_projection": ledger_projection,
        "search_judgment_projection": {
            "owner": "RunKernel.RunAuthoritySearchJudgment",
            "canonical_state": True,
            "trace_only": False,
            "decision": "stop_insufficient",
        },
        "run_contract_projection": run_contract,
        "final_top_evidence": [],
        "scrutineer_flags": [],
        "corpus_weak": False,
        "answer_contract_projection": answer_map,
        "author_evidence": [],
        "unique_source_urls": {},
        "weak_corpus_recovery_skip_reason": None,
        "corpus_state": "healthy",
        "synth_was_insufficient": False,
        "_pre_gate_failure_card_show": False,
        "_pre_gate_failure_card_reason": None,
        "iterations_run": 1,
        "max_iterations": 1,
        "_run_controller_mirror": SimpleNamespace(
            state=SimpleNamespace(active_source_class_recovery_attempt_count=0)
        ),
    }


def _prepare_packet(
    kernel: RunKernel,
    *,
    ledger_projection: dict[str, Any],
    answer_map: dict[str, Any],
    sufficiency_projection: dict[str, Any],
):
    action = kernel.authorize_final_answer_packet_prepare(inputs={})
    result = execute_final_answer_packet_prepare_action(
        action,
        run_id=kernel.state.run_id,
        query="What are the default ports for PostgreSQL, MySQL, Redis, and MongoDB?",
        intent="research",
        report_type="general",
        query_type="general",
        core_topic="default ports",
        primary_entity="database systems",
        anchor_packet_telemetry={},
        final_top_evidence=[],
        author_evidence=[],
        ordered_sources=[],
        unique_source_urls={},
        query_lineage_refs={"query_plan": {"plan_id": "component-default-ports"}},
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=False,
        synth_was_insufficient=False,
        author_notes="",
        author_prompt="BASE AUTHOR PROMPT",
        default_system={"author": "AUTHOR SYSTEM"},
        analyst_effort="medium",
        estimate_from_priors_author=False,
        relevance_low=False,
        strategy="Balanced",
        fast_provider="fast-provider",
        fast_model="fast-model",
        smart_provider="smart-provider",
        smart_model="smart-model",
        evidence_ledger_projection=ledger_projection,
        answer_contract_projection=answer_map,
        sufficiency_judgment_projection=sufficiency_projection,
    )
    kernel.reduce(result.observation)
    return result


def _run_offline_xaxis_path(
    *,
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    component_contract = build_component_executor_contract_projection(
        _default_port_plan()
    )
    run_contract = _run_contract_projection()
    kernel = RunKernel.start(
        run_id="run-ag-offline-xaxis-e2e-01",
        request_id="request-ag-offline-xaxis-e2e-01",
    )
    kernel.state.run_contract_projection = run_contract
    initial_answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=component_contract,
    )
    bridge = kernel.build_offline_search_executor_bridge_projection(
        answer_contract_authority_map_projection=initial_answer_map,
        component_executor_contract_projection=component_contract,
        component_search_plan_projection=component_contract["component_plan"],
        search_work_plan_projection=component_contract["search_work_plan"],
        query_plan_work_shadow_projection=component_contract[
            "query_plan_work_shadow_projection"
        ],
        offline_candidate_observations=(
            _candidate_observations() if candidates is None else candidates
        ),
    )
    custody = (
        kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    )
    refreshed_answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=component_contract,
    )
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    sufficiency = execute_sufficiency_judgment_handoff_from_scope(
        kernel,
        _runtime_scope(
            run_contract=run_contract,
            ledger_projection=ledger_projection,
            answer_map=refreshed_answer_map,
        ),
        smart_model_enabled=False,
    )
    packet_result = _prepare_packet(
        kernel,
        ledger_projection=ledger_projection,
        answer_map=refreshed_answer_map,
        sufficiency_projection=sufficiency.projection,
    )
    blocked_summary = build_safe_blocked_fap_summary(
        kernel.state.final_answer_authority_projection
    )
    return {
        "kernel": kernel,
        "component_contract": component_contract,
        "run_contract": run_contract,
        "initial_answer_map": initial_answer_map,
        "bridge": bridge,
        "custody": custody,
        "ledger_projection": ledger_projection,
        "refreshed_answer_map": refreshed_answer_map,
        "sufficiency": sufficiency.projection,
        "packet_result": packet_result,
        "blocked_summary": blocked_summary,
    }


def _components_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["component_id"]: item for item in items}


def _stage_component_table(result: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    contract = result["component_contract"]
    summary = result["blocked_summary"]["component_blocked_summary"]
    payload_ref = result["packet_result"].author_payload_ref
    return {
        "component_plan": tuple(
            item["component_id"] for item in contract["component_plan"]["components"]
        ),
        "search_work": tuple(
            item["component_id"] for item in contract["search_work_plan"]["components"]
        ),
        "query_plan": tuple(
            item["component_id"]
            for item in contract["query_plan_work_shadow_projection"]["components"]
        ),
        "initial_answer_map": tuple(
            item["component_id"] for item in result["initial_answer_map"]["components"]
        ),
        "offline_bridge": tuple(
            item["component_id"] for item in result["bridge"]["component_observations"]
        ),
        "custody": tuple(
            item["component_id"] for item in result["custody"]["per_component_custody"]
        ),
        "ledger_custody": tuple(
            item["component_id"]
            for item in result["ledger_projection"]["component_scoped_source_custody"][
                "per_component_custody"
            ]
        ),
        "refreshed_answer_map": tuple(
            item["component_id"] for item in result["refreshed_answer_map"]["components"]
        ),
        "sufficiency": tuple(
            item["component_id"]
            for item in result["sufficiency"]["component_readiness"]["components"]
        ),
        "fap_author_payload_ref": tuple(
            item["component_id"]
            for item in payload_ref["component_readiness"]["components"]
        ),
        "blocked_fap_summary": tuple(
            item["component_id"] for item in summary["components"]
        ),
    }


def test_offline_xaxis_preserves_four_components_across_product_spine() -> None:
    result = _run_offline_xaxis_path()
    stage_table = _stage_component_table(result)

    assert set(stage_table) == {
        "component_plan",
        "search_work",
        "query_plan",
        "initial_answer_map",
        "offline_bridge",
        "custody",
        "ledger_custody",
        "refreshed_answer_map",
        "sufficiency",
        "fap_author_payload_ref",
        "blocked_fap_summary",
    }
    for stage, component_ids in stage_table.items():
        assert len(component_ids) == len(COMPONENT_IDS), stage
        assert set(component_ids) == COMPONENT_ID_SET, stage
    for ordered_stage in (
        "component_plan",
        "search_work",
        "query_plan",
        "initial_answer_map",
        "offline_bridge",
        "refreshed_answer_map",
        "sufficiency",
        "fap_author_payload_ref",
        "blocked_fap_summary",
    ):
        assert stage_table[ordered_stage] == COMPONENT_IDS, ordered_stage

    assert result["kernel"].state.projections[ANSWER_CONTRACT_AUTHORITY_MAP_STAGE] == (
        result["refreshed_answer_map"]
    )
    assert result["kernel"].state.projections[OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE] == (
        result["bridge"]
    )
    assert result["kernel"].state.projections[COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE] == (
        result["custody"]
    )
    assert result["kernel"].state.projections[EVIDENCE_LEDGER_STAGE] == (
        result["ledger_projection"]
    )
    assert result["kernel"].state.projections[FINAL_ANSWER_PACKET_STAGE][
        "author_payload_ref"
    ]["status"] == "blocked"


def test_offline_xaxis_preserves_source_obligations_candidates_custody_binding_and_readiness() -> None:
    result = _run_offline_xaxis_path()
    bridge = _components_by_id(result["bridge"]["component_observations"])
    custody = _components_by_id(result["custody"]["per_component_custody"])
    answer_map = _components_by_id(result["refreshed_answer_map"]["components"])
    readiness = _components_by_id(
        result["sufficiency"]["component_readiness"]["components"]
    )
    fap_summary = _components_by_id(
        result["blocked_summary"]["component_blocked_summary"]["components"]
    )

    assert set(bridge) == COMPONENT_ID_SET
    assert set(custody) == COMPONENT_ID_SET
    assert set(answer_map) == COMPONENT_ID_SET
    assert set(readiness) == COMPONENT_ID_SET
    assert set(fap_summary) == COMPONENT_ID_SET
    for component_id in COMPONENT_IDS:
        bridge_component = bridge[component_id]
        custody_component = custody[component_id]
        map_component = answer_map[component_id]
        evidence_custody = map_component["evidence_custody"]
        binding = map_component["binding_status"]
        readiness_component = readiness[component_id]
        fap_component = fap_summary[component_id]

        assert bridge_component["source_obligation_refs"]
        assert bridge_component["candidate_observation_refs"]
        assert custody_component["source_obligation_refs"]
        assert custody_component["candidate_links"]
        assert custody_component["custody_gaps"]
        assert evidence_custody["component_source_obligation_refs"]
        assert evidence_custody["component_candidate_link_refs"]
        assert evidence_custody["component_custody_gap_refs"]
        assert binding["component_candidate_link_refs"] == (
            evidence_custody["component_candidate_link_refs"]
        )
        assert binding["component_custody_gap_refs"] == (
            evidence_custody["component_custody_gap_refs"]
        )
        assert set(binding["blocker_reasons"]) >= {
            "candidate_not_fetched",
            "candidate_not_read",
            "candidate_not_admitted_by_evidenceledger",
        }
        assert readiness_component["component_source_obligation_refs"]
        assert readiness_component["component_candidate_link_refs"]
        assert readiness_component["component_custody_gap_refs"]
        assert "component_candidate_or_custody_presence_is_not_support" in (
            readiness_component["blocker_reasons"]
        )
        assert fap_component["component_source_obligation_refs"]
        assert fap_component["component_candidate_link_refs"]
        assert fap_component["component_custody_gap_refs"]
        assert set(fap_component["blocker_reason_codes"]) >= {
            "candidate_not_fetched",
            "candidate_not_read",
            "candidate_not_admitted_by_evidenceledger",
            "component_candidate_or_custody_presence_is_not_support",
        }


def test_offline_xaxis_keeps_unready_candidates_blocked_through_fap() -> None:
    result = _run_offline_xaxis_path()
    bridge = result["bridge"]
    custody = result["custody"]
    answer_map = result["refreshed_answer_map"]
    sufficiency = result["sufficiency"]
    packet_result = result["packet_result"]
    fap_summary = result["blocked_summary"]["component_blocked_summary"]

    assert bridge["source_obligation_satisfied"] is False
    assert bridge["evidence_bound"] is False
    assert bridge["citation_bound"] is False
    assert bridge["answer_value_bound"] is False
    assert bridge["full_component_success"] is False
    assert bridge["partial_user_answer_candidate"] is False
    assert bridge["author_payload_ready"] is False
    assert bridge["final_answer_allowed"] is None
    assert custody["source_obligations_satisfied_by_candidate_presence"] is False
    assert custody["source_obligation_satisfied"] is False
    assert custody["evidence_bound"] is False
    assert custody["citation_bound"] is False
    assert custody["answer_value_bound"] is False
    assert custody["partial_user_answer_candidate"] is False
    assert custody["author_payload_ready"] is False
    assert custody["final_answer_allowed"] is False
    assert answer_map["component_counts"]["full_component_success_count"] == 0
    assert answer_map["final_answer_status"]["author_payload_ready"] is False
    assert sufficiency["final_answer_allowed"] is False
    assert sufficiency["component_readiness"]["blocked_component_count"] == 4
    assert sufficiency["component_readiness"]["author_payload_ready"] is False
    assert packet_result.packet.final_answer_allowed is False
    assert packet_result.packet.readiness_status is FinalAnswerReadinessStatus.BLOCKED
    assert packet_result.author_input_blocked is True
    assert packet_result.author_payload is None
    assert packet_result.author_payload_ref["status"] == "blocked"
    assert fap_summary["hard_block_candidate"] is True
    assert fap_summary["full_component_success"] is False

    for component in answer_map["components"]:
        binding = component["binding_status"]
        assert binding["evidence_bound"] is False
        assert binding["citation_bound"] is False
        assert binding["source_obligation_bound"] is False
        assert binding["answer_value_bound"] is False
        assert binding["full_component_success"] is False
        assert binding["partial_user_answer_candidate"] is False


def test_offline_xaxis_missing_candidate_survives_end_to_end_as_missing_component() -> None:
    candidates = [
        item
        for item in _candidate_observations()
        if item["component_id"] != "MongoDB"
    ]
    result = _run_offline_xaxis_path(candidates=candidates)
    stage_table = _stage_component_table(result)
    custody = _components_by_id(result["custody"]["per_component_custody"])
    answer_map = _components_by_id(result["refreshed_answer_map"]["components"])
    readiness = _components_by_id(
        result["sufficiency"]["component_readiness"]["components"]
    )
    fap_summary = _components_by_id(
        result["blocked_summary"]["component_blocked_summary"]["components"]
    )

    for stage, component_ids in stage_table.items():
        assert len(component_ids) == len(COMPONENT_IDS), stage
        assert set(component_ids) == COMPONENT_ID_SET, stage

    mongodb_custody = custody["MongoDB"]
    mongodb_map = answer_map["MongoDB"]
    mongodb_readiness = readiness["MongoDB"]
    mongodb_fap = fap_summary["MongoDB"]
    assert mongodb_custody["candidate_links"] == []
    assert mongodb_custody["custody_gaps"][0]["gap_type"] == (
        "missing_component_source_candidate"
    )
    assert mongodb_map["evidence_custody"]["component_candidate_link_refs"] == []
    assert mongodb_map["binding_status"]["component_candidate_link_refs"] == []
    assert "no_candidate" in mongodb_map["binding_status"]["blocker_reasons"]
    assert "missing_component_source_candidate" in (
        mongodb_map["binding_status"]["blocker_reasons"]
    )
    assert mongodb_readiness["status"] == "missing_component"
    assert "missing_component_source_candidate" in mongodb_readiness[
        "blocker_reasons"
    ]
    assert mongodb_fap["status"] == "missing_component"
    assert "missing_component_source_candidate" in mongodb_fap[
        "blocker_reason_codes"
    ]
    assert result["custody"]["candidate_link_count"] == 3
    assert result["blocked_summary"]["component_blocked_summary"][
        "candidate_observed_component_count"
    ] == 3
    assert result["blocked_summary"]["component_blocked_summary"][
        "missing_component_count"
    ] == 1


def test_offline_xaxis_owner_boundaries_have_no_competing_authority() -> None:
    result = _run_offline_xaxis_path()
    kernel = result["kernel"]
    initial_map = result["initial_answer_map"]
    refreshed_map = result["refreshed_answer_map"]
    custody = result["custody"]
    sufficiency = result["sufficiency"]
    packet_result = result["packet_result"]
    fap_summary = result["blocked_summary"]["component_blocked_summary"]

    assert initial_map["authority_boundary"]["root_owner"] == "RunKernel / RunAuthority"
    assert initial_map["owner"] == "RunKernel.AnswerContractAuthorityMap"
    assert refreshed_map["owner"] == "RunKernel.AnswerContractAuthorityMap"
    assert refreshed_map["schema_or_passive_record"] is True
    assert result["bridge"]["owner"] == "RunKernel.OfflineSearchExecutorBridge"
    assert custody["owner"] == "RunKernel.EvidenceLedger"
    assert result["ledger_projection"]["owner"] == "RunKernel.EvidenceLedger"
    assert sufficiency["owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert sufficiency["component_readiness"]["readiness_owner"] == (
        "RunKernel.RunAuthoritySufficiencyJudgment"
    )
    assert sufficiency["component_readiness"]["binding_input_owner"] == (
        "RunKernel.AnswerContractAuthorityMap"
    )
    assert sufficiency["component_readiness"]["binding_input_passive"] is True
    assert sufficiency["component_readiness"]["custody_owner"] == (
        "RunKernel.EvidenceLedger"
    )
    assert sufficiency["component_readiness"]["custody_canonical_state"] is True
    assert packet_result.author_payload_ref["authority_payload"][
        "component_readiness"
    ]["final_packet_owner"] == "RunKernel.FinalAnswerPacket"
    assert kernel.state.final_answer_authority_projection["owner"] == (
        "RunKernel.FinalAnswerPacket"
    )
    assert fap_summary["readiness_owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert fap_summary["final_packet_owner"] == "RunKernel.FinalAnswerPacket"
    assert "component_readiness" not in kernel.state.projections
    assert "component_binding" not in kernel.state.projections
    assert "component_binding_status" not in kernel.state.projections
    assert "component_evidence_citation_binding" not in kernel.state.projections


def test_offline_xaxis_does_not_enable_partial_answers_or_author_payload() -> None:
    result = _run_offline_xaxis_path()
    sufficiency = result["sufficiency"]
    packet_result = result["packet_result"]
    fap_summary = result["blocked_summary"]["component_blocked_summary"]

    assert result["bridge"]["partial_user_answer_candidate"] is False
    assert result["custody"]["partial_user_answer_candidate"] is False
    assert result["refreshed_answer_map"]["component_counts"][
        "partial_user_answer_candidate_count"
    ] == 0
    assert sufficiency["component_readiness"]["partial_component_count"] == 0
    assert sufficiency["component_readiness"]["partial_user_answer_candidate"] is False
    assert sufficiency["component_readiness"][
        "user_facing_partial_answer_enabled"
    ] is False
    assert sufficiency["component_readiness"]["final_answer_allowed"] is False
    assert sufficiency["component_readiness"]["author_payload_ready"] is False
    assert packet_result.author_payload is None
    assert packet_result.author_input_blocked is True
    assert packet_result.author_payload_ref["author_input_deferred"] is True
    assert packet_result.author_payload_ref["blocked_before_author_input"] is True
    assert packet_result.author_payload_ref["authority_payload"][
        "final_answer_allowed"
    ] is False
    assert packet_result.author_payload_ref["authority_payload"][
        "component_readiness"
    ]["user_facing_partial_answer_enabled"] is False
    assert fap_summary["partial_component_count"] == 0
    assert fap_summary["partial_user_answer_candidate"] is False
    assert fap_summary["user_facing_partial_answer_enabled"] is False
    assert fap_summary["citation_bound_component_count"] == 0
    assert fap_summary["evidence_bound_component_count"] == 0
    assert fap_summary["source_obligation_satisfied_component_count"] == 0


def test_offline_xaxis_excludes_raw_private_sentinels() -> None:
    result = _run_offline_xaxis_path(
        candidates=_candidate_observations(include_private_sentinels=True)
    )
    rendered = json.dumps(
        {
            "component_contract": result["component_contract"],
            "initial_answer_map": result["initial_answer_map"],
            "bridge": result["bridge"],
            "custody": result["custody"],
            "ledger_projection": result["ledger_projection"],
            "refreshed_answer_map": result["refreshed_answer_map"],
            "sufficiency": result["sufficiency"],
            "packet": result["packet_result"].packet.to_dict(),
            "author_payload_ref": result["packet_result"].author_payload_ref,
            "blocked_summary": result["blocked_summary"],
            "trace": result["kernel"].to_trace_fragment(),
        },
        sort_keys=True,
    )

    for sentinel in SENTINELS:
        assert sentinel not in rendered


def test_offline_xaxis_static_closed_surface_guard() -> None:
    forbidden_import_roots = {
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.fetch",
        "core.prompts",
        "core.runtime_prompt_assembly",
        "core.author_execution_runtime",
        "core.private_broker",
        "core.live_adapter",
        "core.followup_author_execution_runtime",
        "core.followup_author_payload_construction",
        "core.followup_provider_job_execution_runtime",
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
        "format_citation",
        "render_citations",
    }

    for path in CHANGED_PYTHON_SURFACES:
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
        assert imported_names.isdisjoint(forbidden_import_roots), path
        assert called_names.isdisjoint(forbidden_calls), path

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", "core/pipeline_orchestrator.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout.strip() == ""


def test_docs_use_merge_stable_offline_xaxis_posture() -> None:
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

    assert "pr #322" in normalized
    assert "ag-sufficiency-fap-component-readiness-01" in normalized
    assert "ag-offline-xaxis-e2e-01" in normalized
    assert "offline x-axis end-to-end" in normalized
    assert "blocked fap / author handoff" in normalized
    assert "does not enable partial answers" in normalized
    assert "does not enable live validation" in normalized
    assert (
        "post-merge next gate is bounded live multi-component validation planning "
        "or execution"
    ) in normalized

    forbidden_stale_phrases = {
        "next gate is ag-offline-xaxis-e2e-01",
        "current next implementation target is offline x-axis",
        "post-merge next gate is ag-offline-xaxis-e2e-01",
        "post-merge next gate is ag-partial-answer-readiness-01",
    }
    for phrase in forbidden_stale_phrases:
        assert phrase not in normalized
