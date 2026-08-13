from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.entity_extraction import fallback_entities_from_query, normalize_entities_list
from core.retrieval_quality import (
    finalize_retrieval_queries,
    official_bias_phrase,
    should_merge_recency_queries,
    wants_official_source_bias,
)
from core.router_query_preparation_contract import (
    ROUTER_QUERY_PREPARATION_SCHEMA_VERSION,
    ROUTER_QUERY_PREPARATION_TRACE_KEY,
    build_router_query_preparation_state,
    with_router_query_runtime_posture,
)
from core.routing import merge_search_provider_overrides
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "core" / "router_query_preparation_contract.py"
ORCHESTRATOR_PATH = ROOT / "core" / "pipeline_orchestrator.py"


def _legacy_router_normalization(router_text: str, query: str) -> dict[str, Any]:
    entities_list: list[str] = []
    try:
        intent_data = json.loads(router_text)
        intent = intent_data.get("intent", "general").lower()
        report_type = intent_data.get("report_type", "general_research").lower()
        image_mode = intent_data.get("image_mode", "contextual").lower()
        core_topic = intent_data.get("core_topic", query[:100])
        is_academic = intent_data.get("is_academic", False)
        query_type = str(intent_data.get("query_type") or "other").lower().strip() or "other"
        primary_entity = str(intent_data.get("primary_entity") or "").strip()[:200]
        entities_list = normalize_entities_list(intent_data.get("entities"))
        if entities_list:
            primary_entity = entities_list[0][:200]
        elif primary_entity:
            entities_list = [primary_entity]
    except Exception:
        intent = "general"
        report_type = "general_research"
        image_mode = "contextual"
        core_topic = query[:100]
        is_academic = False
        query_type = "other"
        primary_entity = ""
        entities_list = []
    return {
        "intent": intent,
        "report_type": report_type,
        "image_mode": image_mode,
        "core_topic": core_topic,
        "is_academic": is_academic,
        "query_type": query_type,
        "primary_entity": primary_entity,
        "entities": entities_list,
    }


def test_router_json_normalization_parity() -> None:
    query = "Compare RTX 4090 pricing policy updates"
    router_text = json.dumps(
        {
            "intent": "GENERAL",
            "report_type": "Comparative_Analysis",
            "image_mode": "Contextual",
            "core_topic": "RTX 4090 pricing policy",
            "is_academic": False,
            "query_type": "Product",
            "primary_entity": "ignored because entities wins",
            "entities": ["RTX 4090", "NVIDIA"],
        }
    )

    state = build_router_query_preparation_state(
        query=query,
        router_text=router_text,
        fallback_entities=fallback_entities_from_query(query),
    )
    legacy = _legacy_router_normalization(router_text, query)

    assert state.intent == legacy["intent"]
    assert state.report_type == legacy["report_type"]
    assert state.query_type == legacy["query_type"]
    assert state.image_mode == legacy["image_mode"]
    assert state.core_topic == legacy["core_topic"]
    assert state.is_academic == legacy["is_academic"]
    assert state.primary_entity == legacy["primary_entity"]
    assert state.entities_list == legacy["entities"]
    assert state.router_original_report_type == legacy["report_type"]
    assert state.router_original_query_type == legacy["query_type"]


def test_entity_fallback_and_router_retry_parity() -> None:
    fallback_state = build_router_query_preparation_state(
        query="What changed in GPT-4 pricing?",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "general_research",
                "core_topic": "GPT-4 pricing",
                "query_type": "product",
                "entities": [],
                "primary_entity": "",
            }
        ),
        fallback_entities=fallback_entities_from_query("What changed in GPT-4 pricing?"),
    )
    assert fallback_state.entities_list == ["GPT-4"]
    assert fallback_state.primary_entity == "GPT-4"
    assert fallback_state.entity_fallback_provenance == {
        "fallback_considered": True,
        "fallback_used": True,
        "fallback_entity_count": 1,
        "source": "core.entity_extraction.fallback_entities_from_query",
    }
    assert fallback_state.router_entity_retry_used is False

    retry_state = build_router_query_preparation_state(
        query="Is this a good idea?",
        router_text="{}",
        fallback_entities=fallback_entities_from_query("Is this a good idea?"),
        retry_router_text=json.dumps({"primary_entity": "Acme Widget"}),
        retry_attempted=True,
    )
    assert retry_state.entities_list == ["Acme Widget"]
    assert retry_state.primary_entity == "Acme Widget"
    assert retry_state.router_entity_retry_used is True
    assert retry_state.router_retry_provenance["retry_attempted"] is True
    assert retry_state.router_retry_provenance["retry_entities_used"] is True


def test_routing_override_parity_and_provenance() -> None:
    merged = merge_search_provider_overrides(
        ["tavily", "linkup"],
        ["exa", "linkup"],
        {"tavily": True, "linkup": True, "exa": True},
        complexity="medium",
    )
    state = build_router_query_preparation_state(
        query="compare apple and banana calories per 100g",
        router_text=json.dumps({"query_type": "comparison", "primary_entity": "apple"}),
    )
    state = with_router_query_runtime_posture(
        state,
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        primary_entity="apple",
        entities=["apple"],
        is_academic=False,
        routing_override_applied=True,
        routing_override_reason="nutrition_macro_per_100g_lookup",
        focus_academic=False,
        force_intent_news=False,
        complexity="medium",
        max_queries=2,
        results_per_query=6,
        search_depth="basic",
        top_chunks=20,
        max_iterations=2,
        recency_merge_used=False,
        recency_query=None,
        official_bias_requested=False,
        official_bias_phrase=None,
        finalized_queries=["apple banana calories per 100g"],
        current_queries=["apple banana calories per 100g"],
        query_source="researcher",
    )

    assert merged == ["tavily", "linkup", "exa"]
    assert state.routing_override_provenance["routing_override_applied"] is True
    assert state.routing_override_provenance["routing_override_reason"] == (
        "nutrition_macro_per_100g_lookup"
    )
    assert state.routing_override_provenance["provider_override_semantics_unchanged"] is True


def test_query_text_order_and_official_recency_parity() -> None:
    query = "latest Diablo 4 patch notes pricing today"
    primary = "Diablo 4"
    raw_queries = ["patch notes", "pricing"]
    finalized = finalize_retrieval_queries(
        raw_queries,
        primary_entity=primary,
        entities_list=[primary],
        core_topic="Diablo 4 patch notes",
        user_query=query,
        intent="news",
    )
    current_queries = finalized[:2]
    if should_merge_recency_queries(query, "news", "product"):
        recq = f"{primary} 2026 news"
        current_queries = ([recq] + [q for q in current_queries if q != recq])[:2]
    current_queries = finalize_retrieval_queries(
        current_queries,
        primary_entity=primary,
        entities_list=[primary],
        core_topic="Diablo 4 patch notes",
        user_query=query,
        intent="news",
        include_official_bias=False,
    )[:2]

    state = with_router_query_runtime_posture(
        build_router_query_preparation_state(
            query=query,
            router_text=json.dumps({"intent": "news", "primary_entity": primary}),
        ),
        intent="news",
        report_type="general_research",
        query_type="product",
        primary_entity=primary,
        entities=[primary],
        is_academic=False,
        routing_override_applied=False,
        routing_override_reason=None,
        focus_academic=False,
        force_intent_news=False,
        complexity="medium",
        max_queries=2,
        results_per_query=6,
        search_depth="basic",
        top_chunks=20,
        max_iterations=2,
        recency_merge_used=True,
        recency_query="Diablo 4 2026 news",
        official_bias_requested=wants_official_source_bias(query, "news"),
        official_bias_phrase=official_bias_phrase(query),
        finalized_queries=finalized,
        current_queries=current_queries,
        query_source="researcher",
    )

    assert state.query_text_order_facts["finalized_queries"] == finalized
    assert state.query_text_order_facts["current_queries"] == current_queries
    assert finalized[0] == '"Diablo 4" official pricing'
    assert state.recency_query_merge_posture["recency_merge_used"] is True
    assert state.official_source_bias_posture["official_bias_requested"] is True
    assert state.official_source_bias_posture["official_bias_phrase"] == "official pricing"


def test_trace_compatibility_and_controller_visibility_additive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, harness = run_post_retirement_ordinary_pipeline(tmp_path, monkeypatch)
    trace = outcome.execution_trace
    log_entry = None
    for line in (harness.tmp_path / "execution.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("event") == "execution":
            log_entry = row
            break
    assert log_entry is not None
    log_trace = log_entry["execution_trace"]

    for legacy_field in (
        "intent",
        "query_type",
        "primary_entity",
        "entities",
        "router_entity_retry_used",
        "router_original_report_type",
        "router_original_query_type",
        "routing_override_applied",
        "routing_override_reason",
        "report_type",
        "queries_per_iteration",
        "pass_providers",
    ):
        assert legacy_field in trace
        assert legacy_field in log_trace

    contract = trace[ROUTER_QUERY_PREPARATION_TRACE_KEY]
    assert contract["schema_version"] == ROUTER_QUERY_PREPARATION_SCHEMA_VERSION
    assert contract["controller_owned"] is True
    assert contract["intent"] == trace["intent"]
    assert contract["query_type"] == trace["query_type"]
    assert contract["report_type"] == trace["report_type"]
    assert contract["query_text_order_facts"]["current_queries"] == trace[
        "queries_per_iteration"
    ]["1"]
    assert log_trace[ROUTER_QUERY_PREPARATION_TRACE_KEY] == contract


def test_static_protected_import_guard() -> None:
    tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden_fragments = (
        "provider",
        "search",
        "prompts",
        "author",
        "citation",
        "economist",
        "scrutineer",
        "follow_up",
        "final_evidence",
        "answer_outcome",
        "pipeline_orchestrator",
    )
    assert not [
        name for name in imports for forbidden in forbidden_fragments if forbidden in name.lower()
    ]


def test_orchestrator_authority_guard_consumes_contract_after_router_handoff() -> None:
    text = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    route_handoff = text.index("router_query_preparation_contract = route_result.router_query_preparation_contract")
    runtime_handoff = text.index(
        "router_query_preparation_contract = (\n        query_admission_result.router_query_preparation_contract"
    )
    post_router = text[route_handoff:runtime_handoff]
    post_runtime = text[runtime_handoff:text.index("all_passages: list", runtime_handoff)]
    routing_runtime = Path("core/routing_runtime.py").read_text(encoding="utf-8")
    query_runtime = Path("core/query_production_runtime.py").read_text(encoding="utf-8")

    assert "json.loads(router_text)" not in post_router
    assert "execute_initial_query_strategy_convergence(" in post_router
    assert "execute_query_production_action(" not in post_router
    assert "query_plan_admission_inputs_from_query_production_projection(" not in post_router
    assert "candidate_queries=convergence.candidate_queries" in post_router
    assert "execute_route_request_action(" in text
    assert "run_kernel.authorize_route_request(" in text
    assert "build_router_query_preparation_state(" in routing_runtime
    assert "with_router_query_runtime_posture(" in query_runtime
    assert "intent = router_query_preparation_contract.intent" in post_runtime
    assert "primary_entity = router_query_preparation_contract.primary_entity" in post_runtime


def test_protected_surface_guard_contract_does_not_touch_closed_behaviors() -> None:
    contract_text = CONTRACT_PATH.read_text(encoding="utf-8").lower()
    forbidden_runtime_markers = (
        "ask_model(",
        "process_search_queries",
        "select_providers(",
        "merge_search_provider_overrides(",
        "finalize_retrieval_queries(",
        "default_system",
        "router_retry_user_append",
        "runoutcome",
        "sqlite",
        "cache",
    )
    assert not [marker for marker in forbidden_runtime_markers if marker in contract_text]
