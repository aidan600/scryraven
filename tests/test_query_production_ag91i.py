from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import (
    _build_recon_rewriter_prompt,
    _build_researcher_prompt,
    execute_query_plan_admission_action,
    execute_query_production_action,
    query_plan_admission_inputs_from_query_production_projection,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    ActionType,
    ObservationType,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
QUERY_RUNTIME = ROOT / "core" / "query_production_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"


def _clean(value: str) -> str:
    value = " ".join((value or "").strip().split())
    if not value:
        return ""
    words = value.split(" ")
    last = words[-1]
    if len(last) < 3 and last.isalpha() and "." not in last:
        words = words[:-1]
    return " ".join(words)[:300]


class _Status:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, message: str) -> None:
        self.steps.append(message)


class _Logger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, Exception]] = []

    def warning(self, message: str, error: Exception) -> None:
        self.warnings.append((message, error))


def _router_state(
    *,
    query: str = "Acme Widget deployment",
    intent: str = "general",
    report_type: str = "general_research",
    query_type: str = "product",
    core_topic: str = "Acme Widget deployment",
    primary_entity: str = "Acme Widget",
    entities: list[str] | None = None,
    is_academic: bool = False,
) -> Any:
    entities = [primary_entity] if entities is None else entities
    return build_router_query_preparation_state(
        query=query,
        router_text=json.dumps(
            {
                "intent": intent,
                "report_type": report_type,
                "query_type": query_type,
                "core_topic": core_topic,
                "primary_entity": primary_entity,
                "entities": entities,
                "is_academic": is_academic,
            }
        ),
    )


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    calls = overrides.pop("calls", [])
    ask_response = overrides.pop(
        "ask_response",
        '{"queries":["deployment status","support policy"]}',
    )

    def ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return ask_response

    values: dict[str, Any] = {
        "router_query_preparation_contract": _router_state(),
        "query": "Acme Widget deployment",
        "strategy": "Balanced",
        "current_date": "June 8, 2026",
        "focus_academic": False,
        "force_intent_news": False,
        "include_domains": [],
        "news_preferred_domains": ["reuters.com", "apnews.com"],
        "ask_model": ask_model,
        "clean_json_response": lambda text: text,
        "default_system": {
            "researcher": "researcher-system",
            "recon_query_rewriter": "recon-system",
        },
        "fast_provider": "fast-provider",
        "fast_model": "fast-model",
        "local_url": "http://local",
        "api_key": None,
        "use_reasoning": True,
        "measure_context_stage": lambda *_args, **_kwargs: None,
        "clean_query": _clean,
        "cost_accumulator": object(),
        "status": _Status(),
        "provider_diagnostics": [],
        "run_log": _Logger(),
        "waste_flags": [],
        "brave_api_key_available": False,
        "brave_reconnaissance_func": lambda *_args, **_kwargs: [],
    }
    values.update(overrides)
    return values


def _adapter(*, primary_entity: str = "Acme Widget", intent: str = "general") -> Any:
    return build_query_plan_runtime_adapter(
        run_id="ag91i",
        primary_entity=primary_entity,
        entities_list=[primary_entity] if primary_entity else [],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent=intent,
        clean=_clean,
    )


def test_run_kernel_emits_query_production_authorized_action() -> None:
    kernel = RunKernel.start(run_id="run-ag91i", request_id="request-ag91i")

    action = kernel.authorize_query_production(inputs={"route_action_id": "route-1"})

    assert action.action_type is ActionType.QUERY_PRODUCTION
    assert action.stage == QUERY_PRODUCTION_STAGE
    assert action.expected_observation_type is ObservationType.QUERY_CANDIDATES_PRODUCED
    assert action.inputs["route_action_id"] == "route-1"


def test_query_production_executor_rejects_missing_or_wrong_authorized_action() -> None:
    kernel = RunKernel.start(run_id="run-reject", request_id="request-reject")
    wrong_action = kernel.authorize_query_plan_admission(inputs={})

    with pytest.raises(ValueError, match="AuthorizedAction"):
        execute_query_production_action(None, **_base_kwargs())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="authorized action type"):
        execute_query_production_action(wrong_action, **_base_kwargs())


def test_query_production_observation_reduces_effective_route_posture() -> None:
    kernel = RunKernel.start(run_id="run-posture", request_id="request-posture")
    action = kernel.authorize_query_production(inputs={"route_action_id": "route-1"})

    result = execute_query_production_action(
        action,
        **_base_kwargs(
            router_query_preparation_contract=_router_state(
                query="salmon calories per 100g latest",
                intent="general",
                query_type="nutrition",
                core_topic="salmon calories",
                primary_entity="salmon",
                entities=["salmon"],
            ),
            query="salmon calories per 100g latest",
            focus_academic=True,
            force_intent_news=True,
            strategy="Deep",
            include_domains=["example.com"],
            news_preferred_domains=["news.example"],
        ),
    )

    assert result.observation.observation_type is ObservationType.QUERY_CANDIDATES_PRODUCED
    kernel.reduce(result.observation)
    projection = kernel.state.projections[QUERY_PRODUCTION_STAGE]
    posture = projection["effective_route_posture"]
    assert posture["intent"] == "news"
    assert posture["report_type"] == "quantitative_comparison"
    assert posture["query_type"] == "nutrition"
    assert posture["primary_entity"] == "salmon"
    assert posture["entities_list"] == ["salmon"]
    assert posture["is_academic"] is True
    assert posture["routing_override_applied"] is True
    assert posture["routing_override_reason"] == "nutrition_macro_per_100g_lookup"
    assert posture["focus_academic"] is True
    assert posture["force_intent_news"] is True
    assert posture["complexity"] == "high"
    assert posture["max_queries"] == 3
    assert posture["results_per_query"] == 8
    assert posture["search_depth"] == "advanced"
    assert posture["top_chunks"] == 40
    assert posture["max_iterations"] == 3
    assert set(result.include_domains) == {"example.com", "news.example"}


def test_query_plan_admission_consumes_reduced_query_production_projection() -> None:
    kernel = RunKernel.start(run_id="run-consume", request_id="request-consume")
    production_action = kernel.authorize_query_production(inputs={})
    production = execute_query_production_action(
        production_action,
        **_base_kwargs(ask_response='{"queries":["beta query","alpha query"]}'),
    )
    kernel.reduce(production.observation)
    admission_inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
    )
    stale_local_candidates = ["stale local candidate"]
    action = kernel.authorize_query_plan_admission(
        inputs={
            "query_production_action_id": production_action.action_id,
            "candidate_count": len(admission_inputs.candidate_queries),
        }
    )
    adapter = _adapter()

    result = execute_query_plan_admission_action(
        action,
        query_authority=adapter,
        router_query_preparation_contract=_router_state(),
        candidate_queries=admission_inputs.candidate_queries,
        candidate_source=admission_inputs.candidate_source,
        query_type=admission_inputs.query_type,
        current_date="June 8, 2026",
        max_queries=admission_inputs.max_queries,
        route_runtime_posture=admission_inputs.effective_route_posture,
    )

    assert stale_local_candidates != result.current_queries
    assert result.queries[:2] == ['"Acme Widget" beta query', '"Acme Widget" alpha query']
    assert result.observation.payload["query_order_owner"] == "QueryPlan"
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert trace["items"][0]["origin"] == "researcher"
    kernel.reduce(result.observation)
    assert kernel.state.projections[QUERY_PLAN_ADMISSION_STAGE]["query_order_owner"] == "QueryPlan"


def test_researcher_prompt_bytes_and_ask_model_kwargs_are_preserved() -> None:
    kernel = RunKernel.start(run_id="run-researcher", request_id="request-researcher")
    action = kernel.authorize_query_production(inputs={})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    measured: list[dict[str, Any]] = []
    router_state = _router_state(
        query="Annie Case podcast background",
        query_type="person",
        core_topic="Annie Case podcast background",
        primary_entity="Annie Case",
        entities=["Annie Case"],
    )

    execute_query_production_action(
        action,
        **_base_kwargs(
            calls=calls,
            router_query_preparation_contract=router_state,
            query="Annie Case podcast background",
            strategy="Fast",
            measure_context_stage=lambda name, **kwargs: measured.append(
                {"name": name, **kwargs}
            ),
            brave_api_key_available=False,
        ),
    )

    expected_prompt = (
        "Today is June 8, 2026.\n"
        "Original Prompt: Annie Case podcast background\n"
        "Core Topic: Annie Case podcast background\n"
        "Intent: general\n"
        "query_type: person\n"
        "entities: ['Annie Case']\n"
        "primary_entity: Annie Case\n"
        "If query_type is person, each search query must include a disambiguating term "
        "(role, employer, 'NYU', podcast, etc.) so results are not confused with other people. "
        "Return JSON with a queries array."
    )
    assert _build_researcher_prompt(
        current_date="June 8, 2026",
        query="Annie Case podcast background",
        core_topic="Annie Case podcast background",
        intent="general",
        query_type="person",
        entities_list=["Annie Case"],
        primary_entity="Annie Case",
        anchor_packet_telemetry={},
        strategy="Fast",
    ) == expected_prompt
    assert calls[0][0][:2] == (expected_prompt, "researcher-system")
    assert calls[0][1] == {
        "provider": "fast-provider",
        "model": "fast-model",
        "effort": "low",
        "base_url": "http://local",
        "api_key": None,
        "require_json": True,
        "use_reasoning": True,
    }
    assert measured[0]["name"] == "researcher"
    assert measured[0]["prompt"] == expected_prompt


def test_recon_rewriter_prompt_bytes_ask_kwargs_and_brave_success_diagnostics() -> None:
    kernel = RunKernel.start(run_id="run-recon", request_id="request-recon")
    action = kernel.authorize_query_production(inputs={})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    measured: list[dict[str, Any]] = []
    brave_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    provider_diagnostics: list[dict[str, Any]] = []
    accumulator = object()

    def ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return json.dumps(
            {
                "rewritten_queries": ["Acme Widget 2026 recall update"],
                "recon_confidence": "medium",
                "canonical_subject": "Acme Widget",
            }
        )

    def fake_brave(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        brave_calls.append((args, kwargs))
        return [{"title": "Title A", "url": "https://news.example/a", "snippet": "Snippet A"}]

    result = execute_query_production_action(
        action,
        **_base_kwargs(
            router_query_preparation_contract=_router_state(
                query="Acme Widget breaking news",
                intent="news",
                query_type="news",
                core_topic="Acme Widget",
                primary_entity="Acme Widget",
                entities=["Acme Widget"],
            ),
            query="Acme Widget breaking news",
            ask_model=ask_model,
            measure_context_stage=lambda name, **kwargs: measured.append(
                {"name": name, **kwargs}
            ),
            cost_accumulator=accumulator,
            provider_diagnostics=provider_diagnostics,
            brave_api_key_available=True,
            brave_reconnaissance_func=fake_brave,
        ),
    )

    expected_prompt = (
        "Today is June 8, 2026.\n"
        "Original query: Acme Widget breaking news\n"
        "Recon titles: Title A\n"
        "Recon snippets: Snippet A\n"
    )
    assert _build_recon_rewriter_prompt(
        current_date="June 8, 2026",
        query="Acme Widget breaking news",
        recon_context={"recon_titles": "Title A", "recon_snippets": "Snippet A"},
    ) == expected_prompt
    assert brave_calls[0][0] == ("Acme Widget breaking news",)
    assert brave_calls[0][1] == {
        "num_results": 5,
        "cost_accumulator": accumulator,
        "cost_phase": "recon",
    }
    assert calls[0][0][:2] == (expected_prompt, "recon-system")
    assert calls[0][1] == {
        "provider": "fast-provider",
        "model": "fast-model",
        "effort": "low",
        "base_url": "http://local",
        "api_key": None,
        "require_json": True,
        "use_reasoning": True,
    }
    assert measured[0]["name"] == "recon_rewriter"
    assert provider_diagnostics[0]["provider"] == "brave"
    assert provider_diagnostics[0]["provider_role"] == "recon"
    assert provider_diagnostics[0]["cost_phase"] == "recon"
    assert provider_diagnostics[0]["query_preview"] == "Acme Widget breaking news"
    assert provider_diagnostics[0]["max_results"] == 5
    assert provider_diagnostics[0]["success"] is True
    assert provider_diagnostics[0]["result_count"] == 1
    assert provider_diagnostics[0]["new_url_count"] == 1
    assert provider_diagnostics[0]["accepted_url_count"] == 1
    assert result.candidate_source == "recon"
    assert result.recon_fired is True
    assert result.recon_confidence == "low"


def test_brave_failure_diagnostics_are_preserved_without_live_call() -> None:
    kernel = RunKernel.start(run_id="run-recon-fail", request_id="request-recon-fail")
    action = kernel.authorize_query_production(inputs={})
    provider_diagnostics: list[dict[str, Any]] = []
    logger = _Logger()

    def fake_brave(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise RuntimeError("offline")

    result = execute_query_production_action(
        action,
        **_base_kwargs(
            router_query_preparation_contract=_router_state(
                query="Acme Widget breaking news",
                intent="news",
                query_type="news",
                core_topic="Acme Widget",
                primary_entity="Acme Widget",
                entities=["Acme Widget"],
            ),
            query="Acme Widget breaking news",
            provider_diagnostics=provider_diagnostics,
            run_log=logger,
            brave_api_key_available=True,
            brave_reconnaissance_func=fake_brave,
        ),
    )

    assert provider_diagnostics[0]["provider"] == "brave"
    assert provider_diagnostics[0]["success"] is False
    assert provider_diagnostics[0]["failure_type"] == "RuntimeError"
    assert result.candidate_source == "researcher"
    assert "recon_skipped" in result.waste_flags
    assert logger.warnings


def test_researcher_empty_or_invalid_output_uses_fallback_candidate_source() -> None:
    kernel = RunKernel.start(run_id="run-fallback", request_id="request-fallback")
    action = kernel.authorize_query_production(inputs={})

    result = execute_query_production_action(
        action,
        **_base_kwargs(ask_response='{"queries": []}'),
    )

    assert result.candidate_queries == ["Acme Widget deployment"]
    assert result.candidate_source == "fallback"
    assert result.researcher_fallback_status == "empty_researcher_output"
    assert result.observation.payload["candidate_source"] == "fallback"


def test_no_raw_prompts_model_responses_or_provider_payloads_are_stored_in_runstate() -> None:
    kernel = RunKernel.start(run_id="run-redact", request_id="request-redact")
    action = kernel.authorize_query_production(inputs={"raw_prompt": "do not store"})
    result = execute_query_production_action(action, **_base_kwargs())

    kernel.reduce(result.observation)
    serialized = json.dumps(kernel.state.projections[QUERY_PRODUCTION_STAGE], sort_keys=True)

    assert "Original Prompt:" not in serialized
    assert "Return JSON with a queries array." not in serialized
    assert '{"queries"' not in serialized
    assert "do not store" not in json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    assert result.observation.payload["provenance"]["raw_provider_payloads_retained"] is False
    assert "secret" not in serialized
    assert "candidate_query_projection" in kernel.state.projections[QUERY_PRODUCTION_STAGE]


def test_static_guards_for_ag91i_query_production_authority_transfer() -> None:
    pipeline_source = PIPELINE.read_text()
    runtime_source = QUERY_RUNTIME.read_text()
    kernel_source = RUN_KERNEL.read_text()

    assert "run_kernel.authorize_query_production(" in pipeline_source
    assert "execute_query_production_action(" in pipeline_source
    assert "run_kernel.reduce(query_production_result.observation)" in pipeline_source
    assert "query_plan_admission_inputs_from_query_production_projection(" in pipeline_source
    assert "candidate_queries=query_plan_inputs.candidate_queries" in pipeline_source
    assert "route_runtime_posture=query_plan_inputs.effective_route_posture" in pipeline_source
    assert "brave_reconnaissance(" not in pipeline_source
    assert "default_system[\"researcher\"]" not in pipeline_source
    assert "default_system[\"recon_query_rewriter\"]" not in pipeline_source
    assert "q_prompt =" not in pipeline_source
    assert "rw_in =" not in pipeline_source
    assert "ActionType.QUERY_PRODUCTION" in runtime_source
    assert "ObservationType.QUERY_CANDIDATES_PRODUCED" in runtime_source
    assert "QueryPlan" not in kernel_source
    assert "ask_model" not in kernel_source
    assert "brave_reconnaissance" not in kernel_source
