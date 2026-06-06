from __future__ import annotations

from pathlib import Path
from typing import Any

from core.retrieval_loop_contract import (
    RETRIEVAL_LOOP_SCHEMA_VERSION,
    RETRIEVAL_LOOP_TRACE_KEY,
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
    execute_retrieval_pass_handoff,
    summarize_retrieval_pass_result,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
    with_router_query_runtime_posture,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SESSION_OUTPUT_PROJECTION = ROOT / "core" / "session_output_projection.py"
CONTRACT = ROOT / "core" / "retrieval_loop_contract.py"


def _router_state():
    state = build_router_query_preparation_state(
        router_text='{"intent":"news","report_type":"general_research","query_type":"news","core_topic":"Acme earnings","entities":["Acme"],"primary_entity":"Acme"}',
        query="latest Acme earnings",
    )
    return with_router_query_runtime_posture(
        state,
        intent="news",
        report_type="general_research",
        query_type="news",
        primary_entity="Acme",
        entities=["Acme"],
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
        recency_merge_used=False,
        recency_query=None,
        official_bias_requested=False,
        official_bias_phrase=None,
        finalized_queries=["Acme earnings", "Acme revenue"],
        current_queries=["Acme earnings", "Acme revenue"],
        query_source="researcher",
    )


def _state():
    descriptor = build_retrieval_pass_descriptor(
        iteration=1,
        query_source="researcher",
        current_queries=["Acme earnings", "Acme revenue"],
        provider_list=["tavily", "exa"],
        search_depth="basic",
        results_per_query=6,
        top_chunks=20,
        max_iterations=2,
        intent="news",
        complexity="medium",
        provider_role="main_retrieval",
        retrieval_budget_facts={"iteration": 1, "max_iterations": 2},
        batch_dispatch_authorization_ref={"dispatch_authorized": True},
    )
    envelope = build_retrieval_execution_envelope(
        descriptor,
        include_domains=["example.com"],
        exclude_domains=["spam.example"],
        exa_domain_filter=None,
        entity_hint="Acme",
    )
    stop_input = build_retrieval_stop_controller_input(
        evaluator_sufficient=False,
        iteration=1,
        max_iterations=2,
        prior_queries=[],
        next_queries=["Acme earnings"],
        query_source="researcher",
    )
    stop_decision = decide_retrieval_stop(stop_input)
    return build_retrieval_loop_state(
        router_query_preparation_state=_router_state(),
        pass_descriptor=descriptor,
        execution_envelope=envelope,
        retrieval_stop_decision=stop_decision,
        run_id="run-1",
        retrieval_budget_facts=descriptor.retrieval_budget_facts,
    )


def test_contract_ownership_and_descriptor_are_controller_owned():
    state = _state()
    trace = state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]

    assert state.schema_version == RETRIEVAL_LOOP_SCHEMA_VERSION
    assert trace["controller_owned"] is True
    assert trace["pass_descriptor"]["controller_owned"] is True
    assert trace["execution_envelope"]["controller_owned"] is True
    assert trace["controller_visibility"]["owned_by"] == "Controller"


def test_provider_depth_query_budget_parity_is_copied_not_recomputed():
    state = _state()
    trace = state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]

    assert trace["current_queries"] == ["Acme earnings", "Acme revenue"]
    assert trace["pass_descriptor"]["current_queries"] == [
        "Acme earnings",
        "Acme revenue",
    ]
    assert trace["provider_list"] == ["tavily", "exa"]
    assert trace["search_depth"] == "basic"
    assert trace["results_per_query"] == 6
    assert trace["top_chunks"] == 20
    assert trace["max_iterations"] == 2
    assert trace["query_order_unchanged"] is True
    assert trace["provider_selection_unchanged"] is True
    assert trace["search_depth_unchanged"] is True


def test_mechanical_runner_handoff_uses_descriptor_without_selecting_policy():
    state = _state()
    calls: list[dict[str, Any]] = []

    def fake_process_search_queries(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append({"args": args, "kwargs": kwargs})
        return [{"url": "https://example.com/1"}]

    results = execute_retrieval_pass_handoff(
        state.execution_envelope,
        process_search_queries=fake_process_search_queries,
        query_embedding=[0.1],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="fake-embed",
        embed_model="fake-model",
        local_url=None,
        embed_texts=lambda *a, **k: [],
        compute_similarities=lambda *a, **k: [],
        status_container=None,
        provider_diagnostics=[],
    )

    assert results == [{"url": "https://example.com/1"}]
    assert calls[0]["args"][:5] == (
        ["Acme earnings", "Acme revenue"],
        "news",
        "medium",
        "basic",
        6,
    )
    assert calls[0]["kwargs"]["search_providers"] == ["tavily", "exa"]
    assert calls[0]["kwargs"]["provider_role"] == "main_retrieval"
    assert state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]["execution_envelope"][
        "runner_selects_providers"
    ] is False


def test_retrieval_stop_decision_remains_active_owner():
    stop_input = build_retrieval_stop_controller_input(
        evaluator_sufficient=True,
        iteration=1,
        max_iterations=2,
        prior_queries=["Acme earnings"],
        next_queries=["Acme revenue"],
        query_source="evaluator",
    )
    stop_decision = decide_retrieval_stop(stop_input)
    descriptor = build_retrieval_pass_descriptor(
        iteration=1,
        query_source="evaluator",
        current_queries=["Acme revenue"],
        provider_list=["tavily"],
        search_depth="basic",
        results_per_query=6,
        top_chunks=20,
        max_iterations=2,
        intent="news",
        complexity="medium",
    )
    envelope = build_retrieval_execution_envelope(descriptor)
    state = build_retrieval_loop_state(
        router_query_preparation_state=None,
        pass_descriptor=descriptor,
        execution_envelope=envelope,
        retrieval_stop_decision=stop_decision,
    )

    trace = state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]
    assert stop_decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS
    assert trace["retrieval_stop_decision_ref"]["owner"] == "RetrievalStopDecision"
    assert trace["retrieval_stop_decision_ref"]["decision"] == "proceed_to_synthesis"
    assert trace["did_generate_queries"] is False


def test_router_query_preparation_state_feeds_contract_queries():
    state = _state()
    trace = state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]

    assert trace["router_query_preparation_ref"]["available"] is True
    assert trace["router_query_preparation_ref"]["controller_owned"] is True
    assert trace["router_query_preparation_ref"]["query_source"] == "researcher"
    assert trace["finalized_queries"] == ["Acme earnings", "Acme revenue"]


def test_pass_result_summary_is_additive_controller_visible_trace():
    state = _state()
    state = state.with_pass_result(
        summarize_retrieval_pass_result(
            descriptor=state.pass_descriptor,
            result_count=3,
            seen_url_delta=2,
        )
    )
    trace = state.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]

    assert trace["pass_result_summaries"] == [
        {
            "iteration": 1,
            "query_count": 2,
            "provider_count": 2,
            "result_count": 3,
            "seen_url_delta": 2,
            "provider_role": "main_retrieval",
        }
    ]


def test_orchestrator_handoff_static_guard():
    text = PIPELINE.read_text()
    loop_section = text[text.index("# Main retrieval loop") : text.index("if iteration == 1:", text.index("# Main retrieval loop"))]

    helper_text = (ROOT / "core" / "retrieval_dispatch_runtime.py").read_text()
    assert "execute_main_retrieval_pass_from_scope" in loop_section
    assert "build_retrieval_pass_descriptor" in helper_text
    assert "build_retrieval_loop_state" in helper_text
    assert "execute_retrieval_pass_handoff" in helper_text
    assert "select_providers(" in loop_section  # still precomputed legacy policy
    assert "process_search_queries(" not in loop_section
    assert "retrieval_loop_contract_state.to_trace_fragment()" in text


def test_protected_surface_guard_no_live_or_prompt_surfaces_opened():
    contract_text = CONTRACT.read_text()

    forbidden = [
        "ask_model",
        "brave_reconnaissance",
        "fetch_linkup",
        "execute_persistence_side_effects",
        "build_session_payload",
        "DEFAULT_SYSTEM",
        "Author",
        "citation",
        "openai",
        "requests.",
    ]
    for token in forbidden:
        assert token not in contract_text
    assert "did_change_prompt_behavior: bool = False" in contract_text
    assert "did_rank_or_filter_sources: bool = False" in contract_text


def test_trace_compatibility_adds_contract_without_removing_existing_fields():
    text = PIPELINE.read_text() + SESSION_OUTPUT_PROJECTION.read_text()

    for existing in [
        '"pass_providers"',
        '"queries_per_iteration"',
        "RETRIEVAL_BATCH_DISPATCH_TRACE_KEY",
        "router_query_preparation_contract.to_trace_fragment()",
        "retrieval_stop_active_telemetry",
        "retrieval_stop_shadow_telemetry",
    ]:
        assert existing in text
    assert "retrieval_loop_contract_state.to_trace_fragment()" in text
    trace = _state().to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]
    assert trace["final_answer_behavior_unchanged"] is True
    assert trace["mechanical_runner_boundary"] is True


def test_offline_fake_loop_parity_first_and_continuation_passes():
    seen_calls: list[tuple[Any, ...]] = []

    def fake_process_search_queries(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        seen_calls.append((*args[:5], tuple(kwargs["search_providers"])))
        return []

    for iteration, queries, providers, depth in [
        (1, ["q1", "q2"], ["tavily", "exa"], "basic"),
        (2, ["q3"], ["linkup"], "advanced"),
    ]:
        descriptor = build_retrieval_pass_descriptor(
            iteration=iteration,
            query_source="researcher" if iteration == 1 else "evaluator",
            current_queries=queries,
            provider_list=providers,
            search_depth=depth,
            results_per_query=8,
            top_chunks=40,
            max_iterations=3,
            intent="general",
            complexity="high",
        )
        execute_retrieval_pass_handoff(
            build_retrieval_execution_envelope(descriptor),
            process_search_queries=fake_process_search_queries,
            query_embedding=[],
            seen_urls=set(),
            collected_images=set(),
            embed_provider="fake",
            embed_model="fake",
            local_url=None,
            embed_texts=lambda *a, **k: [],
            compute_similarities=lambda *a, **k: [],
            status_container=None,
            provider_diagnostics=[],
        )

    assert seen_calls == [
        (["q1", "q2"], "general", "high", "basic", 8, ("tavily", "exa")),
        (["q3"], "general", "high", "advanced", 8, ("linkup",)),
    ]
