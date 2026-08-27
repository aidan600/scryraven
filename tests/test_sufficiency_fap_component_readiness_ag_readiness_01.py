import ast
import json
from copy import deepcopy
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
    FINAL_ANSWER_PACKET_STAGE,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PIPELINE = CORE / "pipeline_orchestrator.py"
CHANGED_MODULES = (
    CORE / "run_authority_sufficiency.py",
    CORE / "run_authority_sufficiency_adapter.py",
    CORE / "run_authority_sufficiency_validation.py",
    CORE / "run_authority_sufficiency_runtime.py",
    CORE / "final_answer_packet.py",
    CORE / "final_answer_packet_runtime.py",
    CORE / "final_answer_runtime_adapter.py",
    CORE / "run_kernel.py",
)
COMPONENT_IDS = {"PostgreSQL", "MySQL", "Redis", "MongoDB"}
SENTINELS = (
    "RAW_PROMPT_SHOULD_NOT_LEAK",
    "RAW_PROVIDER_PAYLOAD_SHOULD_NOT_LEAK",
    "RAW_MODEL_RESPONSE_SHOULD_NOT_LEAK",
    "PRIVATE_LOG_SHOULD_NOT_LEAK",
    "DB_CACHE_ROW_SHOULD_NOT_LEAK",
    "FULL_TRACE_SHOULD_NOT_LEAK",
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
        metadata={"fixture": "AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01"},
    )


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


def _run_contract_projection() -> dict[str, Any]:
    return {
        "contract_id": "run-contract:component-default-ports",
        "schema_version": "test_run_contract_component_readiness_v1",
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


def _run_component_readiness_path(
    *,
    candidates: list[dict[str, Any]] | None = None,
    mutate_answer_map: bool = False,
    mutate_ledger_projection: bool = False,
):
    component_contract = build_component_executor_contract_projection(
        _default_port_plan()
    )
    run_contract = _run_contract_projection()
    kernel = RunKernel.start(
        run_id="run-ag-readiness-01",
        request_id="request-ag-readiness-01",
    )
    kernel.state.run_contract_projection = run_contract
    answer_map = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=component_contract,
    )
    kernel.build_offline_search_executor_bridge_projection(
        answer_contract_authority_map_projection=answer_map,
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
    kernel.record_component_scoped_source_custody_from_offline_search_executor_bridge()
    refreshed = kernel.build_answer_contract_authority_map_projection(
        component_executor_contract_projection=component_contract,
    )
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    if mutate_answer_map:
        tempting = _tempting_true_fields()
        refreshed = deepcopy(refreshed)
        refreshed["components"][0]["binding_status"].update(tempting)
        kernel.state.projections[ANSWER_CONTRACT_AUTHORITY_MAP_STAGE] = refreshed
    if mutate_ledger_projection:
        tempting = _tempting_true_fields()
        ledger_projection = deepcopy(ledger_projection)
        component_custody = ledger_projection["component_scoped_source_custody"]
        component_custody.update(tempting)
        component_custody["per_component_custody"][0].update(tempting)
        component_custody["per_component_custody"][0]["candidate_links"][0].update(
            tempting
        )
    handoff = execute_sufficiency_judgment_handoff_from_scope(
        kernel,
        _runtime_scope(
            run_contract=run_contract,
            ledger_projection=ledger_projection,
            answer_map=refreshed,
        ),
        smart_model_enabled=False,
    )
    packet_result = _prepare_packet(
        kernel,
        ledger_projection=ledger_projection,
        answer_map=refreshed,
        sufficiency_projection=handoff.projection,
    )
    blocked_summary = build_safe_blocked_fap_summary(
        kernel.state.final_answer_authority_projection
    )
    return kernel, refreshed, handoff.projection, packet_result, blocked_summary


def _component_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["component_id"]: item
        for item in summary["component_blocked_summary"]["components"]
    }


def _tempting_true_fields() -> dict[str, bool]:
    return {
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


def test_existing_sufficiency_and_fap_owners_consume_component_readiness() -> None:
    kernel, _answer_map, sufficiency, packet_result, summary = (
        _run_component_readiness_path()
    )

    assert sufficiency["owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert sufficiency["component_readiness"]["readiness_owner"] == (
        "RunKernel.RunAuthoritySufficiencyJudgment"
    )
    assert kernel.state.final_answer_authority_projection["owner"] == (
        "RunKernel.FinalAnswerPacket"
    )
    assert packet_result.author_input_blocked is True
    assert packet_result.author_payload is None
    assert packet_result.author_payload_ref["component_readiness"]
    assert summary["component_blocked_summary"]["final_packet_owner"] == (
        "RunKernel.FinalAnswerPacket"
    )
    assert not any("component_readiness" == key for key in kernel.state.projections)
    assert {
        action.action_type.value for action in kernel.state.issued_actions.values()
    } == {"sufficiency_judgment_decide", "final_answer_packet_prepare"}
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE][
        "author_payload_ref"
    ]["status"] == "blocked"


def test_four_offline_components_survive_into_sufficiency_and_fap_readiness() -> None:
    _kernel, _answer_map, sufficiency, _packet_result, summary = (
        _run_component_readiness_path()
    )
    readiness = sufficiency["component_readiness"]
    fap_summary = summary["component_blocked_summary"]

    assert {item["component_id"] for item in readiness["components"]} == COMPONENT_IDS
    assert {item["component_id"] for item in fap_summary["components"]} == COMPONENT_IDS
    assert readiness["component_count"] == 4
    assert readiness["satisfied_component_count"] == 0
    assert readiness["blocked_component_count"] == 4
    assert fap_summary["expected_component_count"] == 4
    assert fap_summary["satisfied_component_count"] == 0
    assert fap_summary["blocked_component_count"] == 4
    assert fap_summary["candidate_observed_component_count"] == 4

    for component in readiness["components"]:
        assert component["component_candidate_link_refs"]
        assert component["component_custody_gap_refs"]
        assert component["component_source_obligation_refs"]
        assert component["status"] == "blocked_component"
        binding = component["binding_status"]
        assert binding["evidence_bound"] is False
        assert binding["citation_bound"] is False
        assert binding["source_obligation_bound"] is False
        assert binding["answer_value_bound"] is False
        assert binding["full_component_success"] is False
        assert binding["partial_user_answer_candidate"] is False


def test_offline_unbound_components_block_final_readiness_and_author_payload() -> None:
    _kernel, _answer_map, sufficiency, packet_result, summary = (
        _run_component_readiness_path()
    )

    assert sufficiency["final_answer_allowed"] is False
    assert sufficiency["final_packet_inputs"]["final_answer_allowed"] is False
    assert sufficiency["component_readiness"]["author_payload_ready"] is False
    assert packet_result.packet.final_answer_allowed is False
    assert packet_result.packet.readiness_status is FinalAnswerReadinessStatus.BLOCKED
    assert packet_result.author_payload_ref["status"] == "blocked"
    assert packet_result.author_payload_ref["component_readiness"][
        "author_payload_ready"
    ] is False
    fap_summary = summary["component_blocked_summary"]
    assert fap_summary["full_component_success"] is False
    assert fap_summary["partial_user_answer_candidate"] is False
    assert fap_summary["evidence_bound_component_count"] == 0
    assert fap_summary["citation_bound_component_count"] == 0
    assert fap_summary["source_obligation_satisfied_component_count"] == 0


def test_missing_candidate_component_remains_represented_with_blocker() -> None:
    candidates = [
        item for item in _candidate_observations() if item["component_id"] != "MongoDB"
    ]
    _kernel, _answer_map, sufficiency, _packet_result, summary = (
        _run_component_readiness_path(candidates=candidates)
    )
    readiness_by_id = {
        item["component_id"]: item for item in sufficiency["component_readiness"]["components"]
    }
    fap_by_id = _component_map(summary)

    assert set(readiness_by_id) == COMPONENT_IDS
    assert readiness_by_id["MongoDB"]["status"] == "missing_component"
    assert "missing_component_source_candidate" in readiness_by_id["MongoDB"][
        "blocker_reasons"
    ]
    assert fap_by_id["MongoDB"]["status"] == "missing_component"
    assert "missing_component_source_candidate" in fap_by_id["MongoDB"][
        "blocker_reason_codes"
    ]
    assert summary["component_blocked_summary"]["missing_component_count"] == 1
    assert summary["component_blocked_summary"]["hard_block_candidate"] is True


def test_partial_readiness_is_not_invented_from_offline_candidate_presence() -> None:
    _kernel, _answer_map, sufficiency, packet_result, summary = (
        _run_component_readiness_path()
    )

    assert sufficiency["component_readiness"]["partial_component_count"] == 0
    assert sufficiency["component_readiness"]["partial_user_answer_candidate"] is False
    assert sufficiency["component_readiness"]["user_facing_partial_answer_enabled"] is (
        False
    )
    assert packet_result.author_payload_ref["component_readiness"][
        "partial_user_answer_candidate"
    ] is False
    assert summary["component_blocked_summary"]["partial_user_answer_candidate"] is (
        False
    )
    assert summary["component_blocked_summary"][
        "user_facing_partial_answer_enabled"
    ] is False


def test_spoofed_passive_readiness_fields_do_not_satisfy_components() -> None:
    _kernel, _answer_map, sufficiency, packet_result, summary = (
        _run_component_readiness_path(
            mutate_answer_map=True,
            mutate_ledger_projection=True,
        )
    )

    postgresql = next(
        item
        for item in sufficiency["component_readiness"]["components"]
        if item["component_id"] == "PostgreSQL"
    )
    assert postgresql["status"] != "satisfied_component"
    assert "passive_binding_true_without_canonical_source_obligation" in postgresql[
        "blocker_reasons"
    ]
    assert sufficiency["final_answer_allowed"] is False
    assert packet_result.author_payload_ref["status"] == "blocked"
    assert summary["component_blocked_summary"]["full_component_success"] is False
    assert summary["component_blocked_summary"]["partial_user_answer_candidate"] is (
        False
    )


def test_sufficiency_fap_component_readiness_excludes_raw_private_sentinels() -> None:
    candidates = deepcopy(_candidate_observations())
    candidates[0].update(
        {
            "raw_prompt": SENTINELS[0],
            "raw_provider_payload": SENTINELS[1],
            "raw_model_response": SENTINELS[2],
            "private_logs": SENTINELS[3],
            "db_cache_rows": SENTINELS[4],
            "full_trace": SENTINELS[5],
        }
    )
    kernel, _answer_map, sufficiency, packet_result, summary = (
        _run_component_readiness_path(candidates=candidates)
    )
    rendered = json.dumps(
        {
            "sufficiency": sufficiency,
            "packet": packet_result.packet.to_dict(),
            "payload_ref": packet_result.author_payload_ref,
            "summary": summary,
            "trace": kernel.to_trace_fragment(),
        },
        sort_keys=True,
    )

    for sentinel in SENTINELS:
        assert sentinel not in rendered


def test_static_closed_surface_guard_for_component_readiness_phase() -> None:
    forbidden_import_roots = {
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.fetch",
        "core.author_execution_runtime",
        "core.private_broker",
        "core.live_adapter",
        "core.followup_final_answer_packet_runtime",
        "core.followup_author_payload_construction",
    }
    forbidden_calls = {
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

    guarded_modules = tuple(
        path for path in CHANGED_MODULES if path.name != "run_kernel.py"
    )
    for path in guarded_modules:
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

    orchestrator_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "if final_answer_packet_handoff.author_input_blocked:" in orchestrator_source
    assert "build_blocked_fap_terminal_report" in orchestrator_source
    assert "build_blocked_fap_terminal_trace_fragment" in orchestrator_source
    assert "execute_author_handoff_from_scope" in orchestrator_source
    assert (
        'raise PipelineError("FinalAnswerPacket did not produce Author input")'
        in orchestrator_source
    )
    # Blocked FAP must still skip Author execution; terminal packaging is the
    # licensed AG-BLOCKED-FAP-SAFE-TERMINAL-OUTCOME-01 exception to the old raise.
    blocked_branch_index = orchestrator_source.index(
        "if final_answer_packet_handoff.author_input_blocked:"
    )
    author_call_index = orchestrator_source.index(
        "execute_author_handoff_from_scope(",
        blocked_branch_index,
    )
    else_index = orchestrator_source.index(
        "else:",
        blocked_branch_index,
        author_call_index,
    )
    assert else_index < author_call_index


def test_docs_use_merge_stable_component_readiness_posture() -> None:
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

    assert "pr #321" in normalized
    assert "ag-component-evidence-citation-binding-01" in normalized
    assert "ag-sufficiency-fap-component-readiness-01" in normalized
    assert "sufficiencyjudgment and finalanswerpacket" in normalized
    assert "pr #322" in normalized
    assert "ag-offline-xaxis-e2e-01" in normalized
    assert "offline x-axis end-to-end" in normalized
    assert "does not enable partial answers" in normalized
    assert "does not enable live validation" in normalized
    assert "run_contract_semantic_loop.md" in normalized
    assert "post-merge next gate is ag-run-contract-mutation-loop-01" in normalized
    assert (
        "bounded live validation is deferred until the upstream semantic-contract/"
        "planner/scout/search-executor runtime loop exists"
    ) in normalized
    assert "passive/shadow surfaces are not product readiness" in normalized

    forbidden_stale_phrases = {
        "next gate is ag-sufficiency-fap-component-readiness-01",
        "current next implementation target is sufficiency/fap component readiness",
        "post-merge next gate is ag-sufficiency-fap-component-readiness-01",
        "post-merge next gate is bounded live multi-component validation planning or execution",
        "bounded live validation is the immediate next gate",
        "post-merge next gate is ag-partial-answer-readiness-01",
        "shadow query plan proves product readiness",
    }
    for phrase in forbidden_stale_phrases:
        assert phrase not in normalized
