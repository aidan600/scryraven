from __future__ import annotations

import ast
from pathlib import Path

from core.run_controller import (
    ControllerDecision,
    ControllerState,
    CorpusAssessment,
    EvidenceRegistry,
    RetrievalAction,
    RunController,
    StageLedger,
)

_ROOT = Path(__file__).resolve().parents[1]
_RUN_CONTROLLER_PATH = _ROOT / "core" / "run_controller.py"


def test_controller_state_construction_and_serialization() -> None:
    state = ControllerState(
        session_id="session-1",
        run_id="run-1",
        query="synthetic question",
        mode="Balanced",
        current_date="2026-05-18",
        core_topic="synthetic topic",
        intent="general",
        complexity="medium",
        corpus=CorpusAssessment(
            state="HEALTHY",
            weak=False,
            utilization_rate=0.82,
            utilization_threshold=0.4,
            signals={"passages_used": 4},
            trace_fields={"corpus_state": "HEALTHY"},
        ),
        route_fields={"report_type": "general_research"},
        trace_fields={"intent": "general"},
    )

    payload = state.to_dict()

    assert payload["run_id"] == "run-1"
    assert payload["corpus"]["state"] == "HEALTHY"
    assert payload["corpus"]["signals"] == {"passages_used": 4}
    assert payload["route_fields"] == {"report_type": "general_research"}
    assert state.to_trace_fragment() == {
        "intent": "general",
        "corpus_state": "HEALTHY",
    }

    payload["corpus"]["signals"]["passages_used"] = 99
    assert state.corpus.signals == {"passages_used": 4}


def test_evidence_registry_records_snapshots_without_reordering_or_filtering() -> None:
    registry = EvidenceRegistry()
    registry.record_passages(
        [
            {
                "source_id": "source-2",
                "url": "https://b.example/source",
                "source_tier": "secondary",
            },
            {
                "source_id": "source-1",
                "url": "https://a.example/source",
                "source_tier": "official",
            },
        ]
    )
    registry.record_seen_urls(
        [
            "https://b.example/source",
            "https://a.example/source",
            "https://b.example/source",
        ]
    )
    registry.record_collected_images(
        ["https://img.example/2.jpg", "https://img.example/1.jpg"]
    )
    registry.record_source_ids(["source-2", "source-1"])
    registry.record_source_tier_snapshot(
        {"source_id": "source-2", "source_tier": "secondary"}
    )
    registry.record_source_tier_snapshot(
        {"source_id": "source-1", "source_tier": "official"}
    )
    registry.record_domain_snapshot({"domain": "b.example", "count": 1})
    registry.record_domain_snapshot({"domain": "a.example", "count": 1})

    payload = registry.to_dict()

    assert [passage["source_id"] for passage in payload["passages"]] == [
        "source-2",
        "source-1",
    ]
    assert payload["seen_urls"] == [
        "https://b.example/source",
        "https://a.example/source",
        "https://b.example/source",
    ]
    assert payload["collected_images"] == [
        "https://img.example/2.jpg",
        "https://img.example/1.jpg",
    ]
    assert payload["source_ids"] == ["source-2", "source-1"]
    assert [item["source_tier"] for item in payload["source_tier_snapshots"]] == [
        "secondary",
        "official",
    ]
    assert [item["domain"] for item in payload["domain_snapshots"]] == [
        "b.example",
        "a.example",
    ]

    snapshot = registry.snapshot_passages()
    snapshot[0]["source_id"] = "changed"
    assert registry.passages[0]["source_id"] == "source-2"


def test_stage_ledger_records_query_provider_retrieval_and_decision_facts() -> None:
    ledger = StageLedger()
    retrieval = RetrievalAction(
        name="main_retrieval_record",
        queries=["synthetic query 2", "synthetic query 1"],
        provider="tavily",
        provider_role="main_retrieval",
        search_depth="basic",
        results_per_query=6,
        signals={"iteration": 1},
    )
    decision = ControllerDecision(
        name="router_fact_record",
        reason="router already produced a synthetic intent",
        signals={"intent": "general"},
    )

    ledger.record_retrieval_action(retrieval)
    ledger.record_query(stage="researcher", query="synthetic query 2", iteration=1)
    ledger.record_query(stage="researcher", query="synthetic query 1", iteration=1)
    ledger.record_provider_fact(
        stage="retrieval",
        provider="tavily",
        provider_role="main_retrieval",
        success=True,
        metadata={"result_count": 3},
    )
    ledger.record_decision(decision)
    ledger.record_fact(stage="context", name="token_budget", value=1200)

    payload = ledger.to_dict()

    assert payload["retrieval_actions"][0]["queries"] == [
        "synthetic query 2",
        "synthetic query 1",
    ]
    assert [record["query"] for record in payload["query_records"]] == [
        "synthetic query 2",
        "synthetic query 1",
    ]
    assert payload["provider_records"] == [
        {
            "stage": "retrieval",
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "success": True,
            "metadata": {"result_count": 3},
        }
    ]
    assert payload["decision_records"][0]["name"] == "router_fact_record"
    assert payload["fact_records"][0] == {
        "stage": "context",
        "name": "token_budget",
        "value": 1200,
        "metadata": {},
    }


def test_shadow_source_class_recovery_record_has_no_active_retrieval() -> None:
    action = RetrievalAction(
        name="source_class_recovery_recommendation",
        queries=["synthetic official current rules query"],
        reason="missing official_current_rules",
        trace_fields={
            "source_class_recovery_queries": [
                "synthetic official current rules query"
            ],
            "source_class_recovery_query_count": 1,
        },
    )
    decision = ControllerDecision(
        name="source_class_recovery",
        active=False,
        shadow=True,
        reason="missing official_current_rules",
        signals={
            "missing_expected_source_classes": ["official_current_rules"],
        },
        recommended_actions=[action],
        trace_fields={
            "source_class_recovery_recommended": True,
            "source_class_recovery_shadow_mode": True,
        },
    )
    controller = RunController()

    controller.record_decision(decision)
    controller.record_retrieval_action(action)

    payload = decision.to_dict()
    trace_fragment = controller.to_trace_fragment()

    assert payload["active"] is False
    assert payload["shadow"] is True
    assert payload["recommended_actions"][0]["active"] is False
    assert payload["recommended_actions"][0]["shadow"] is True
    assert trace_fragment == {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "source_class_recovery_queries": [
            "synthetic official current rules query"
        ],
        "source_class_recovery_query_count": 1,
    }


def test_default_controller_has_no_active_recovery_provider_intent_or_analyst_skip() -> None:
    controller = RunController()
    state = controller.snapshot_state()

    assert state["recovery_action_records"] == []
    assert state["provider_call_records"] == []
    assert state["analyst_skip_record"] is None
    assert "provider_call_intent" not in state
    assert controller.snapshot_ledger()["retrieval_actions"] == []
    assert controller.to_trace_fragment() == {}


def test_run_controller_static_import_and_method_name_guard() -> None:
    tree = ast.parse(_RUN_CONTROLLER_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_method_prefixes = (
        "decide_",
        "should_",
        "run_",
        "recover_",
        "select_",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    active_method_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_method_prefixes)
    ]

    assert violations == []
    assert active_method_names == []
