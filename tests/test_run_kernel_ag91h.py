from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.analyst_quant_packet_runtime import _format_analyst_quant_packet_section
from core.prompts import ROUTER_RETRY_USER_APPEND
from core.provider_plan import ProviderPlan
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import execute_query_plan_admission_action
from core.retrieval_dispatch_runtime import execute_main_retrieval_pass_from_scope
from core.retrieval_scheduler import (
    RetrievalScheduleInput,
    schedule_main_retrieval_action,
    schedule_main_retrieval_from_kernel_action,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop_with_kernel_action,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.routing_runtime import execute_route_request_action
from core.run_kernel import (
    MAIN_RETRIEVAL_STAGE,
    QUERY_PLAN_ADMISSION_STAGE,
    RETRIEVAL_STOP_CHECKPOINT_STAGE,
    ROUTE_REQUEST_STAGE,
    RUN_KERNEL_TRACE_KEY,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
ROUTING_RUNTIME = ROOT / "core" / "routing_runtime.py"
QUERY_RUNTIME = ROOT / "core" / "query_production_runtime.py"
DISPATCH_RUNTIME = ROOT / "core" / "retrieval_dispatch_runtime.py"
SCHEDULER = ROOT / "core" / "retrieval_scheduler.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"


def _clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def _query_adapter():
    return build_query_plan_runtime_adapter(
        run_id="ag91h",
        primary_entity="Acme Widget",
        entities_list=["Acme Widget"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
    )


def test_moved_analyst_quant_packet_section_is_byte_for_byte_guarded() -> None:
    telemetry = {
        "quantitative_packet_present": True,
        "quantitative_packet_valid": True,
        "quantitative_packet_direct_use_eligible": False,
        "quantitative_packet_requires_analyst": True,
        "quantitative_packet_gate_reason": "valid_packet_for_analyst_review",
        "quantitative_packet_validation_errors": [],
        "quantitative_packet": {
            "schema_version": "quant_packet_v1",
            "target_metric_names": ["margin"],
            "source_bound_values": [{"metric": "margin", "value": "12%"}],
            "unsupported_values": [],
            "calculation_results": [],
            "target_metric_bound_value_refs": ["s1"],
            "target_metric_calculation_refs": [],
            "high_stakes_quant_detected": False,
            "high_stakes_quant_domain": None,
            "direct_use_eligible": False,
            "requires_analyst": True,
            "validation_errors": [],
            "gate_reason": "valid_packet_for_analyst_review",
        },
    }

    section, _handoff = _format_analyst_quant_packet_section(telemetry)

    assert section == (
        "\n\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n"
        "Instructions:\n"
        "- Treat this as structured evidence, not as a final conclusion.\n"
        "- Verify that the packet supports the user's requested metric.\n"
        "- Keep source_bound_values distinct from unsupported_values; unsupported_values are not sourced facts.\n"
        "- Check whether validation_errors is empty.\n"
        "- If direct_use_eligible is false, do not present it as a settled quantitative conclusion.\n"
        "- If high_stakes_quant_detected is true, apply extra caution and state limitations.\n"
        "- You may accept, reject, or qualify the packet.\n"
        "- Do not invent calculations or unstated values; do not cite unsupported_values as source-bound.\n"
        "Packet JSON:\n"
        '{"calculation_results":[],"direct_use_eligible":false,'
        '"gate_reason":"valid_packet_for_analyst_review",'
        '"high_stakes_quant_detected":false,"high_stakes_quant_domain":null,'
        '"requires_analyst":true,"schema_version":"quant_packet_v1",'
        '"source_bound_values":[{"metric":"margin","value":"12%"}],'
        '"target_metric_bound_value_refs":["s1"],'
        '"target_metric_calculation_refs":[],"target_metric_names":["margin"],'
        '"unsupported_values":[],"validation_errors":[]}\n'
    )


def test_run_kernel_start_creates_run_state_with_request_identity() -> None:
    kernel = RunKernel.start(
        run_id="run-1",
        request_id="request-1",
        request={"mode": "Balanced", "raw_prompt": "redact me"},
    )

    assert kernel.state.run_id == "run-1"
    assert kernel.state.request_id == "request-1"
    assert kernel.state.request["mode"] == "Balanced"
    assert kernel.state.request["raw_prompt"] == "[redacted]"
    assert kernel.state.next_action_sequence == 1
    assert kernel.state.next_observation_sequence == 1


def test_kernel_emits_required_authorized_actions() -> None:
    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    actions = [
        kernel.authorize_route_request(inputs={"query_length": 12}),
        kernel.authorize_query_plan_admission(inputs={"candidate_count": 2}),
        kernel.authorize_main_retrieval_pass(inputs={"iteration": 1}),
        kernel.authorize_retrieval_stop_checkpoint(inputs={"checkpoint_stage": "evaluator"}),
    ]

    assert [action.action_type for action in actions] == [
        ActionType.ROUTE_REQUEST,
        ActionType.QUERY_PLAN_ADMISSION,
        ActionType.MAIN_RETRIEVAL_PASS,
        ActionType.RETRIEVAL_STOP_CHECKPOINT,
    ]
    assert [action.stage for action in actions] == [
        ROUTE_REQUEST_STAGE,
        QUERY_PLAN_ADMISSION_STAGE,
        MAIN_RETRIEVAL_STAGE,
        RETRIEVAL_STOP_CHECKPOINT_STAGE,
    ]
    assert [action.sequence for action in actions] == [1, 2, 3, 4]
    for action in actions:
        payload = action.to_dict()
        assert payload["action_id"]
        assert payload["run_id"] == "run-1"
        assert payload["stage"]
        assert payload["action_type"]
        assert payload["reason"]
        assert "inputs" in payload
        assert payload["expected_observation_type"]
        assert payload["sequence"]


def test_route_executor_consumes_action_and_preserves_prompt_bytes() -> None:
    kernel = RunKernel.start(run_id="run-route", request_id="request-route")
    action = kernel.authorize_route_request(inputs={"query_length": 2})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    measured: list[dict[str, str]] = []
    responses = iter(
        [
            '{"intent":"general","report_type":"general_research","query_type":"other","core_topic":"??","entities":[]}',
            '{"intent":"general","report_type":"general_research","query_type":"other","core_topic":"Acme","entities":["Acme"],"primary_entity":"Acme"}',
        ]
    )

    def fake_ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return next(responses)

    def measure(name: str, **kwargs: str) -> None:
        measured.append({"name": name, **kwargs})

    result = execute_route_request_action(
        action,
        query="??",
        current_date="June 8, 2026",
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        default_system={"router": "router-system"},
        fast_provider="fast-provider",
        fast_model="fast-model",
        local_url="http://local",
        api_key=None,
        use_reasoning=True,
        measure_context_stage=measure,
    )

    expected_router_prompt = "Today is June 8, 2026.\nUser Topic: ??"
    expected_retry_prompt = f"{expected_router_prompt}\n\n{ROUTER_RETRY_USER_APPEND}"
    assert calls[0][0][:2] == (expected_router_prompt, "router-system")
    assert calls[1][0][:2] == (expected_retry_prompt, "router-system")
    assert calls[0][1] == {
        "provider": "fast-provider",
        "model": "fast-model",
        "effort": "low",
        "base_url": "http://local",
        "api_key": None,
        "require_json": True,
        "use_reasoning": True,
    }
    assert measured[0]["prompt"] == expected_router_prompt
    assert measured[1]["prompt"] == expected_retry_prompt
    assert result.observation.action_id == action.action_id
    assert result.observation.observation_type is ObservationType.ROUTE_RESULT
    kernel.reduce(result.observation)
    assert kernel.state.projections[ROUTE_REQUEST_STAGE]["primary_entity"] == "Acme"


def test_query_plan_admission_consumes_action_and_keeps_queryplan_as_order_owner() -> None:
    kernel = RunKernel.start(run_id="run-query", request_id="request-query")
    action = kernel.authorize_query_plan_admission(
        inputs={"candidate_source": "researcher", "candidate_count": 2}
    )
    adapter = _query_adapter()

    result = execute_query_plan_admission_action(
        action,
        query_authority=adapter,
        router_query_preparation_contract=build_router_query_preparation_state(
            query="Acme Widget deployment",
            router_text='{"intent":"general","report_type":"general_research","query_type":"product","core_topic":"Acme Widget","entities":["Acme Widget"],"primary_entity":"Acme Widget"}',
        ),
        candidate_queries=["deployment status", "support policy"],
        candidate_source="researcher",
        query_type="product",
        current_date="June 8, 2026",
        max_queries=2,
        route_runtime_posture={
            "intent": "general",
            "report_type": "general_research",
            "primary_entity": "Acme Widget",
            "entities": ["Acme Widget"],
            "is_academic": False,
            "routing_override_applied": False,
            "routing_override_reason": None,
            "focus_academic": False,
            "force_intent_news": False,
            "complexity": "medium",
            "results_per_query": 6,
            "search_depth": "basic",
            "top_chunks": 20,
            "max_iterations": 2,
        },
    )

    assert result.observation.action_id == action.action_id
    assert result.observation.observation_type is ObservationType.QUERY_PLAN_ADMITTED
    assert result.current_queries == [
        '"Acme Widget" deployment status',
        '"Acme Widget" support policy',
    ]
    assert result.observation.payload["query_order_owner"] == "QueryPlan"
    query_plan_ref = result.observation.payload["query_plan_ref"]
    assert query_plan_ref["plan_id"] == adapter.plan.plan_id
    assert QUERY_PLAN_TRACE_KEY in adapter.to_trace_fragment()
    kernel.reduce(result.observation)
    assert kernel.state.projections[QUERY_PLAN_ADMISSION_STAGE]["query_plan_ref"] == query_plan_ref


def test_stop_checkpoint_consumes_action_and_reduces_decision() -> None:
    kernel = RunKernel.start(run_id="run-stop", request_id="request-stop")
    action = kernel.authorize_retrieval_stop_checkpoint(
        inputs={"checkpoint_stage": "evaluator", "next_query_count": 1}
    )
    snapshot = build_retrieval_stop_controller_input(
        evaluator_sufficient=True,
        iteration=1,
        max_iterations=2,
        prior_queries=["Acme earnings"],
        next_queries=["Acme revenue"],
        query_source="evaluator",
    )

    result = decide_retrieval_stop_with_kernel_action(action, snapshot, stage="evaluator")

    assert result.decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS
    assert result.observation.action_id == action.action_id
    assert result.observation.observation_type is ObservationType.RETRIEVAL_STOP_DECISION
    kernel.reduce(result.observation)
    assert kernel.state.projections[RETRIEVAL_STOP_CHECKPOINT_STAGE]["decision"]["decision"] == "proceed_to_synthesis"
    assert kernel.state.projections[RETRIEVAL_STOP_CHECKPOINT_STAGE]["next_stage_ready"] is True


def test_main_retrieval_schedule_dispatch_consumes_kernel_action_and_scheduled_action() -> None:
    kernel = RunKernel.start(run_id="run-retrieval", request_id="request-retrieval")
    action = kernel.authorize_main_retrieval_pass(inputs={"iteration": 1, "query_count": 1})
    provider_plan = ProviderPlan.from_available_keys({"tavily": True, "linkup": True, "exa": True})
    scheduler_scope = {
        "provider_plan": provider_plan,
        "query_type": "other",
        "intent": "research",
        "complexity": "medium",
        "report_type": "general_research",
        "is_academic": False,
        "suppress_tavily": False,
        "search_depth": "basic",
        "iteration": 1,
        "a5_provider_override": None,
        "force_component_providers": [],
        "merge_provider_overrides": lambda primary, scout, _available, **_kwargs: primary or scout,
        "select_provider_list": lambda *_args, **kwargs: list(kwargs.get("override") or ["scheduled-provider"]),
    }
    scheduled_action = schedule_main_retrieval_from_kernel_action(
        action,
        scheduler_scope,
        current_queries=["scheduled query"],
        recovery_active=False,
        choose_search_depth=lambda _complexity, base_depth, _iteration: base_depth or "basic",
    )

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    seen_urls: set[str] = set()

    def fake_process(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append((args, kwargs))
        args[8].add("https://scheduled.example")
        return [{"url": "https://scheduled.example", "text": "scheduled"}]

    class _Deps:
        @staticmethod
        def compute_similarities(*_args: Any, **_kwargs: Any) -> list[Any]:
            return []

    dispatch_scope = {
        "iteration": 1,
        "router_query_preparation_contract": build_router_query_preparation_state(
            query="topic",
            router_text=None,
        ),
        "main_retrieval_kernel_action": action,
        "retrieval_scheduled_action": scheduled_action,
        "results_per_query": 4,
        "top_chunks": 8,
        "max_iterations": 2,
        "intent": "research",
        "complexity": "medium",
        "include_domains": [],
        "exclude_domains": [],
        "ACADEMIC_DOMAINS": [],
        "is_academic": False,
        "entity_hint_for_retrieval": "Acme",
        "retrieval_stop_active_telemetry": {},
        "run_id": "run-retrieval",
        "retrieval_batch_dispatch_trace": {"authorized": True},
        "active_source_class_recovery_lifecycle": {},
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_attempted": False,
        "weak_corpus_recovery_decision": None,
        "retrieval_loop_contract_state": None,
        "similarity_prior_queries": None,
        "query_similarity_basis": None,
        "process_search_queries": fake_process,
        "query_embedding": [0.1],
        "seen_urls": seen_urls,
        "collected_images": set(),
        "embed_provider": "embed-provider",
        "embed_model": "embed-model",
        "local_url": None,
        "embed_texts": lambda *_args, **_kwargs: [],
        "deps": _Deps(),
        "status": object(),
        "provider_diagnostics": [],
    }
    records: list[dict[str, Any]] = []

    outcome = execute_main_retrieval_pass_from_scope(
        dispatch_scope,
        retrieval_pass_records=records,
    )

    assert calls[0][0][:4] == (["scheduled query"], "research", "medium", "basic")
    assert calls[0][1]["search_providers"] == ["scheduled-provider"]
    assert outcome.observation.action_id == action.action_id
    assert outcome.observation.observation_type is ObservationType.RETRIEVAL_PASS_RESULT
    assert records[0]["queries"] == ["scheduled query"]
    kernel.reduce(outcome.observation)
    assert kernel.state.projections[MAIN_RETRIEVAL_STAGE]["chunk_delta"] == 1


def test_adapters_reject_missing_or_wrong_authorized_actions() -> None:
    kernel = RunKernel.start(run_id="run-reject", request_id="request-reject")
    wrong_action = kernel.authorize_query_plan_admission(inputs={})

    with pytest.raises(ValueError, match="AuthorizedAction"):
        execute_route_request_action(  # type: ignore[arg-type]
            None,
            query="Acme",
            current_date="June 8, 2026",
            ask_model=lambda *_args, **_kwargs: "{}",
            clean_json_response=lambda text: text,
            default_system={"router": "router"},
            fast_provider="p",
            fast_model="m",
            local_url=None,
            api_key=None,
            use_reasoning=False,
            measure_context_stage=lambda *_args, **_kwargs: None,
        )
    with pytest.raises(ValueError, match="authorized action type"):
        execute_route_request_action(
            wrong_action,
            query="Acme",
            current_date="June 8, 2026",
            ask_model=lambda *_args, **_kwargs: "{}",
            clean_json_response=lambda text: text,
            default_system={"router": "router"},
            fast_provider="p",
            fast_model="m",
            local_url=None,
            api_key=None,
            use_reasoning=False,
            measure_context_stage=lambda *_args, **_kwargs: None,
        )

    retrieval_action = kernel.authorize_main_retrieval_pass(inputs={})
    with pytest.raises(ValueError, match="authorized action type"):
        schedule_main_retrieval_from_kernel_action(
            wrong_action,
            {},
            current_queries=["q"],
            recovery_active=False,
            choose_search_depth=lambda *_args: "basic",
        )
    with pytest.raises(KeyError, match="main_retrieval_kernel_action"):
        execute_main_retrieval_pass_from_scope(
            {"retrieval_scheduled_action": schedule_main_retrieval_action(
                RetrievalScheduleInput(
                    stage="main_retrieval",
                    current_queries=["q"],
                    search_depth="basic",
                    providers=["p"],
                )
            )},
            retrieval_pass_records=[],
        )
    with pytest.raises(ValueError, match="authorized action type"):
        decide_retrieval_stop_with_kernel_action(
            retrieval_action,
            build_retrieval_stop_controller_input(
                evaluator_sufficient=False,
                iteration=1,
                max_iterations=2,
                next_queries=["q"],
            ),
            stage="evaluator",
        )


def _observation_for(action: AuthorizedAction) -> Observation:
    return Observation.from_action(
        action,
        observation_type=action.expected_observation_type,
        status=RunStageStatus.COMPLETED,
        payload={"ok": True},
    )


def test_reduce_rejects_invalid_transitions() -> None:
    kernel = RunKernel.start(run_id="run-invalid", request_id="request-invalid")
    action = kernel.authorize_route_request(inputs={})
    foreign_action = AuthorizedAction(
        action_id="foreign-action",
        run_id="run-invalid",
        stage=ROUTE_REQUEST_STAGE,
        action_type=ActionType.ROUTE_REQUEST,
        reason="foreign",
        inputs={},
        expected_observation_type=ObservationType.ROUTE_RESULT,
        sequence=1,
    )
    with pytest.raises(RunKernelTransitionError, match="no matching issued action"):
        kernel.reduce(_observation_for(foreign_action))

    second_action = kernel.authorize_query_plan_admission(inputs={})
    wrong_action_id = Observation(
        observation_id="wrong-action-id",
        run_id="run-invalid",
        action_id=second_action.action_id,
        stage=ROUTE_REQUEST_STAGE,
        observation_type=ObservationType.ROUTE_RESULT,
        status=RunStageStatus.COMPLETED,
        payload={},
        sequence=second_action.sequence,
    )
    with pytest.raises(RunKernelTransitionError, match="stage"):
        kernel.reduce(wrong_action_id)

    wrong_stage = Observation(
        observation_id="wrong-stage",
        run_id="run-invalid",
        action_id=action.action_id,
        stage=QUERY_PLAN_ADMISSION_STAGE,
        observation_type=ObservationType.ROUTE_RESULT,
        status=RunStageStatus.COMPLETED,
        payload={},
        sequence=action.sequence,
    )
    with pytest.raises(RunKernelTransitionError, match="stage"):
        kernel.reduce(wrong_stage)

    wrong_type = Observation(
        observation_id="wrong-type",
        run_id="run-invalid",
        action_id=action.action_id,
        stage=action.stage,
        observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload={},
        sequence=action.sequence,
    )
    with pytest.raises(RunKernelTransitionError, match="observation type"):
        kernel.reduce(wrong_type)

    out_of_order_kernel = RunKernel.start(run_id="run-order", request_id="request-order")
    first = out_of_order_kernel.authorize_route_request(inputs={})
    second = out_of_order_kernel.authorize_query_plan_admission(inputs={})
    assert first.sequence == 1
    with pytest.raises(RunKernelTransitionError, match="out of order"):
        out_of_order_kernel.reduce(_observation_for(second))

    duplicate_kernel = RunKernel.start(run_id="run-dup", request_id="request-dup")
    duplicate_action = duplicate_kernel.authorize_route_request(inputs={})
    duplicate_observation = _observation_for(duplicate_action)
    duplicate_kernel.reduce(duplicate_observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        duplicate_kernel.reduce(duplicate_observation)


def test_kernel_trace_projection_derives_from_run_state() -> None:
    kernel = RunKernel.start(run_id="run-trace", request_id="request-trace")
    action = kernel.authorize_route_request(inputs={"query_length": 4})
    kernel.reduce(_observation_for(action))

    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]

    assert trace["run_id"] == kernel.state.run_id
    assert trace["stage_statuses"][ROUTE_REQUEST_STAGE] == "completed"
    assert trace["action_statuses"][action.action_id] == "completed"
    assert trace["actions"][0]["action_id"] == action.action_id
    assert trace["observations"][0]["action_id"] == action.action_id
    assert trace["projections"][ROUTE_REQUEST_STAGE] == {"ok": True}


def test_pipeline_orchestrator_consumes_run_kernel_for_migrated_stages() -> None:
    source = PIPELINE.read_text()
    assert "from core.run_kernel import RunKernel" in source
    assert "run_kernel = RunKernel.start(" in source
    assert "run_kernel.authorize_route_request(" in source
    assert "execute_route_request_action(" in source
    assert "run_kernel.reduce(route_result.observation)" in source
    assert "run_kernel.authorize_query_plan_admission(" in source
    assert "execute_query_plan_admission_action(" in source
    assert "run_kernel.reduce(query_admission_result.observation)" in source
    assert "run_kernel.authorize_main_retrieval_pass(" in source
    assert "schedule_main_retrieval_from_kernel_action(" in source
    assert "main_retrieval_kernel_action" in source
    assert "run_kernel.reduce(main_retrieval_outcome.observation)" in source
    assert "run_kernel.authorize_retrieval_stop_checkpoint(" in source
    assert "decide_retrieval_stop_with_kernel_action(" in source
    assert "run_kernel.to_trace_fragment()" in source


def test_migrated_stages_are_not_purely_orchestrator_local() -> None:
    source = PIPELINE.read_text()
    assert "router_prompt = f\"Today is {current_date}" not in source
    assert "router_text = ask_model(" not in source
    assert "queries = query_authority.admit_researcher_candidates" not in source
    assert "queries = query_authority.admit_recon_candidates" not in source
    assert "recency_projection = query_authority.apply_initial_recency_merge" not in source
    assert "retrieval_scheduled_action = schedule_main_retrieval_from_pipeline_scope" not in source
    assert "_decide_retrieval_stop_for_active" not in source


def test_static_guards_for_authority_boundaries_and_closed_surfaces() -> None:
    routing_source = ROUTING_RUNTIME.read_text()
    query_source = QUERY_RUNTIME.read_text()
    dispatch_source = DISPATCH_RUNTIME.read_text()
    scheduler_source = SCHEDULER.read_text()
    kernel_source = RUN_KERNEL.read_text()

    assert "validate_authorized_action(" in routing_source
    assert "ActionType.ROUTE_REQUEST" in routing_source
    assert "validate_authorized_action(" in query_source
    assert "ActionType.QUERY_PLAN_ADMISSION" in query_source
    assert '"query_order_owner": "QueryPlan"' in query_source
    assert "scheduled_action: RetrievalScheduledAction" in dispatch_source
    assert "main_retrieval_kernel_action" in dispatch_source
    assert "ActionType.MAIN_RETRIEVAL_PASS" in scheduler_source
    assert "ProviderPlan" not in kernel_source
    assert "QueryPlan" not in kernel_source
    assert "process_search_queries" not in kernel_source
    assert "ask_model" not in kernel_source
    assert "DEFAULT_SYSTEM" not in kernel_source
    for forbidden in ("requests.", "openai", "brave_reconnaissance", ".env"):
        assert forbidden not in kernel_source
