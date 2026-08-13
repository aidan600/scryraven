"""Offline product-path proof for model-owned initial semantic planning.

Test path: tests/test_searchos_model_owned_semantic_planning_01.py
Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: selected-fast-model planning, typed planner/Scout/revision seams,
bounded supplied context, accepted component lineage, and first QueryPlan dispatch.
Runtime/product path guarded: real ``run_pipeline()`` plus authorized convergence.
Expected cost: offline fakes only, under five seconds.
Promotion posture: remain phase_focus.
Why not fast_pr: this is detailed phase proof; existing broad sentinels remain cheaper.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import (
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_config import RunDeps
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
)
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from core.search_planner_runtime import DeterministicSearchPlannerAdapter
from tests.helpers.offline_ordinary_pipeline import (
    PostRetirementOrdinaryPipelineHarness,
    offline_balanced_run_config,
    scrub_offline_runtime,
)


@dataclass
class ModelOwnedPipelineHarness(PostRetirementOrdinaryPipelineHarness):
    planner_response: Any = field(default_factory=dict)
    planner_prompts: list[str] = field(default_factory=list)
    planner_kwargs: list[dict[str, Any]] = field(default_factory=list)
    revision_prompts: list[str] = field(default_factory=list)
    revision_kwargs: list[dict[str, Any]] = field(default_factory=list)

    def ask_model(
        self,
        prompt: str,
        system_prompt: str,
        provider: str = "OpenAI",
        model: str = "gpt-5.4-mini",
        effort: str = "low",
        base_url: str | None = None,
        api_key: str | None = None,
        stream: bool = False,
        require_json: bool = False,
        use_reasoning: bool = True,
        cost_accumulator: CostAccumulator | None = None,
        cost_phase: str = "model",
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        call_kwargs = {
            "provider": provider,
            "model": model,
            "effort": effort,
            "base_url": base_url,
            "api_key": api_key,
            "stream": stream,
            "require_json": require_json,
            "use_reasoning": use_reasoning,
            "cost_accumulator": cost_accumulator,
            "cost_phase": cost_phase,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if system_prompt == SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
            self._record_model_call(system_prompt, call_kwargs)
            self.planner_prompts.append(prompt)
            self.planner_kwargs.append(dict(call_kwargs))
            if provider == "OpenRouter" and not api_key:
                raise ValueError("OpenRouter API key is missing")
            if provider == "Local (LM Studio)" and not str(base_url or "").startswith(("http://", "https://")):
                raise ValueError("Local model endpoint is missing or invalid")
            if isinstance(self.planner_response, Exception):
                raise self.planner_response
            if isinstance(self.planner_response, str):
                response = self.planner_response
            else:
                response = json.dumps(self.planner_response)
            sink = kwargs.get("safe_response_envelope_sink")
            if callable(sink):
                sink({"provider_completion_posture": "completed"})
            if cost_accumulator is not None:
                cost_accumulator.record_model_call(
                    phase=cost_phase,
                    model=model,
                    input_tokens=11,
                    output_tokens=7,
                )
            return response
        return super().ask_model(prompt, system_prompt, **call_kwargs)


class ResponseOnlyPlannerAdapter:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = deepcopy(dict(response))
        self.calls: list[dict[str, Any]] = []

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(planner_input)))
        return deepcopy(self.response)


class FakePlannerModel:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = deepcopy(dict(response))
        self.calls: list[dict[str, Any]] = []

    def __call__(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "kwargs": dict(kwargs),
            }
        )
        return json.dumps(self.response)


def _planner_payload(
    *,
    component_count: int = 1,
    query_texts: Sequence[str] | None = None,
    recon_posture: str = "not_needed",
) -> dict[str, Any]:
    queries = list(query_texts or ())
    components: list[dict[str, Any]] = []
    for index in range(1, component_count + 1):
        need = queries[index - 1] if index <= len(queries) else f"Model-owned semantic need for component {index}"
        component: dict[str, Any] = {
            "key": f"component-{index}",
            "need": need,
        }
        if index == 1 and recon_posture != "not_needed":
            component["uncertainties"] = [
                {
                    "kind": "entity",
                    "status": "unresolved",
                    "candidates": ["Old Example", "New Example"],
                }
            ]
        components.append(component)
    return {"disposition": "components", "components": components}


def _install_chain_capture(monkeypatch: Any) -> dict[str, Any]:
    captured: dict[str, Any] = {"query_plan_admission_calls": 0}
    original_convergence = orchestrator.execute_initial_query_strategy_convergence
    original_admission = orchestrator.execute_query_plan_admission_action

    def convergence_wrapper(**kwargs: Any) -> Any:
        result = original_convergence(**kwargs)
        kernel = kwargs["run_kernel"]
        captured["run_kernel"] = kernel
        captured["convergence"] = result
        captured["initial_contract_at_convergence"] = deepcopy(kernel.state.initial_answer_contract)
        captured["planner_projection_at_convergence"] = deepcopy(kernel.state.search_planner_proposal_projection)
        captured["scout_projection_at_convergence"] = deepcopy(kernel.state.scout_disambiguation_report_projection)
        captured["revision_projection_at_convergence"] = deepcopy(kernel.state.search_planner_revision_projection)
        captured["evidence_at_convergence"] = deepcopy(kernel.state.evidence_ledger.to_projection().to_dict())
        return result

    def admission_wrapper(*args: Any, **kwargs: Any) -> Any:
        captured["query_plan_admission_calls"] += 1
        result = original_admission(*args, **kwargs)
        captured["query_plan_admission"] = result
        return result

    monkeypatch.setattr(
        orchestrator,
        "execute_initial_query_strategy_convergence",
        convergence_wrapper,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_query_plan_admission_action",
        admission_wrapper,
    )
    return captured


def _pipeline_fixture(
    tmp_path: Path,
    monkeypatch: Any,
    *,
    query: str,
    planner_response: Any,
    supplied_context: Mapping[str, Any] | None = None,
    planner_adapter: Any | None = None,
    scout_adapter: Any | None = None,
    revision_adapter: Any | None = None,
    use_default_model: bool = True,
) -> tuple[Any, RunDeps, ModelOwnedPipelineHarness, dict[str, Any]]:
    scrub_offline_runtime(monkeypatch)
    capture = _install_chain_capture(monkeypatch)
    harness = ModelOwnedPipelineHarness(
        tmp_path=tmp_path,
        query=query,
        core_topic="Example central requirement",
        primary_entity="Example",
        raw_author_response=(
            "The retrieved source supports the bounded answer. [[1]](https://example.example/report-1)"
        ),
        planner_response=planner_response,
        healthy=True,
    )
    config = replace(
        offline_balanced_run_config(
            query=query,
            current_date="2026-07-20",
            session_id="session:model-owned-planning",
            run_id="run:model-owned-planning",
            search_planner_supplied_context=supplied_context,
        ),
        fast_provider="selected-offline-fast-provider",
        fast_model="selected-offline-fast-model",
        use_reasoning=True,
        include_domains=["example.example"],
        exclude_domains=["blocked.example"],
    )
    deps = replace(
        harness.deps(),
        search_planner_adapter=(None if use_default_model else planner_adapter),
        scout_disambiguation_adapter=scout_adapter,
        search_planner_revision_adapter=revision_adapter,
        provider_availability={"tavily": True, "serper": True},
        logger=logging.getLogger("tests.searchos.model_owned_semantic_planning"),
    )
    return config, deps, harness, capture


def _kernel_after_run_contract() -> RunKernel:
    kernel = RunKernel.start(
        run_id="run:model-owned-five",
        request_id="request:model-owned-five",
    )
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": {
                    "contract_id": "run-contract:model-owned-five",
                    "schema_version": "run_contract_fixture_v1",
                    "synthesis_mode": "offline_fixture",
                    "selected_depth": "balanced",
                    "source_requirements": [],
                },
                "validation": {"ok": True, "status": "ok"},
            },
        )
    )
    return kernel


def _router_state() -> Any:
    return build_router_query_preparation_state(
        query="Please work out the actual multipart request from my narration.",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "comparison",
                "query_type": "comparison",
                "core_topic": "Example multipart request",
                "primary_entity": "Example",
                "entities": ["Example"],
                "is_academic": False,
            }
        ),
    )


def _contains_object_identity(value: Any, target: Any) -> bool:
    if value is target:
        return True
    if isinstance(value, Mapping):
        return any(_contains_object_identity(item, target) for item in value.values())
    if isinstance(value, list | tuple):
        return any(_contains_object_identity(item, target) for item in value)
    return False


def test_rundeps_declares_typed_planner_seam_without_scout_or_revision_consumption() -> None:
    declared = {item.name: item for item in fields(RunDeps)}

    assert "search_planner_adapter" in declared
    assert declared["search_planner_adapter"].default is None

    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert "planner_adapter = deps.search_planner_adapter" in source
    assert "scout_adapter = deps.scout_disambiguation_adapter" not in source
    assert "revision_adapter = deps.search_planner_revision_adapter" not in source
    assert "build_ordinary_scout_disambiguation_adapter" not in source
    assert "SearchPlannerRevisionModelAdapter" not in source
    assert 'getattr(deps, "search_planner_adapter"' not in source
    assert "DeterministicSearchPlannerAdapter()" not in source


@pytest.mark.parametrize(
    ("provider", "model", "local_url", "api_key"),
    (
        (
            "OpenAI",
            "gpt-5.4-mini",
            "https://openai-config.invalid/v1",
            "openai-config-key-not-for-retention",
        ),
        (
            "OpenRouter",
            "openai/gpt-5.4-mini",
            "https://openrouter-local-placeholder.invalid/v1",
            "openrouter-planner-key-not-for-retention",
        ),
        (
            "Local (LM Studio)",
            "local-planner-model",
            "http://planner-local.invalid:1234/v1",
            "local-config-key-not-for-retention",
        ),
    ),
)
def test_default_planner_receives_selected_transport_and_run_accounting(
    tmp_path: Path,
    monkeypatch: Any,
    provider: str,
    model: str,
    local_url: str,
    api_key: str,
) -> None:
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example rule?",
        planner_response=_planner_payload(),
    )
    config = replace(
        config,
        fast_provider=provider,
        fast_model=model,
        local_url=local_url,
        or_api_key=api_key,
    )
    accumulator = CostAccumulator()

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        accumulator,
    )

    assert outcome.report
    assert len(harness.planner_kwargs) == 1
    planner_kwargs = harness.planner_kwargs[0]
    assert planner_kwargs["provider"] == provider
    assert planner_kwargs["model"] == model
    assert planner_kwargs["effort"] == "medium"
    assert planner_kwargs["base_url"] == local_url
    assert planner_kwargs["api_key"] == api_key
    assert planner_kwargs["cost_accumulator"] is accumulator
    assert planner_kwargs["cost_phase"] == "search_planner"
    assert planner_kwargs["require_json"] is True
    assert planner_kwargs["use_reasoning"] is True
    assert capture["query_plan_admission_calls"] == 1
    cost_snapshot = accumulator.snapshot()
    assert cost_snapshot["calls_by_phase"] == {
        "model": 2,
        "search_planner": 1,
    }
    assert cost_snapshot["total_calls"] == 3
    assert outcome.cost_snapshot == cost_snapshot


def test_sparse_factual_uncertainty_does_not_reach_scout_or_revision(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example identity rule?",
        planner_response=_planner_payload(recon_posture="optional"),
    )

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )

    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert outcome.report
    assert "build_ordinary_scout_disambiguation_adapter" not in source
    assert harness.revision_kwargs == []
    assert harness.revision_prompts == []
    slot = capture["initial_contract_at_convergence"]["accepted_semantic_slot_refs"][0]
    assert slot["status"] == "unresolved"
    assert slot["candidate_values"] == ["Old Example", "New Example"]
    assert slot["user_confirmation_required"] is False


def test_ordinary_no_recon_makes_zero_scout_and_revision_calls(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    config, deps, harness, _capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example rule?",
        planner_response=_planner_payload(),
    )

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )

    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert outcome.report
    assert "build_ordinary_scout_disambiguation_adapter" not in source
    assert "SearchPlannerRevisionModelAdapter" not in source
    assert harness.revision_prompts == []
    assert harness.revision_kwargs == []


def test_default_planner_transport_facts_are_not_retained(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    endpoint = "http://planner-endpoint-retention-sentinel.invalid:1234/v1"
    credential = "planner-credential-retention-sentinel"
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example rule?",
        planner_response=_planner_payload(),
    )
    config = replace(
        config,
        fast_provider="OpenRouter",
        fast_model="openai/gpt-5.4-mini",
        local_url=endpoint,
        or_api_key=credential,
    )
    accumulator = CostAccumulator()

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        accumulator,
    )

    kernel = capture["run_kernel"]
    retained = {
        "planner_prompt": harness.planner_prompts[0],
        "planner_projection": capture["planner_projection_at_convergence"],
        "initial_contract": kernel.state.initial_answer_contract,
        "current_contract": kernel.state.current_answer_contract,
        "query_plan": capture["query_plan_admission"].observation.payload,
        "run_kernel_trace": kernel.trace_projection().to_dict(),
        "execution_trace": outcome.execution_trace,
        "cost_snapshot": outcome.cost_snapshot,
    }
    retained_text = json.dumps(retained, sort_keys=True)
    assert credential not in retained_text
    assert endpoint not in retained_text
    assert not _contains_object_identity(retained, accumulator)


@pytest.mark.parametrize(
    ("provider", "local_url", "api_key", "failure_kind"),
    (
        (
            "OpenRouter",
            "https://unused-local.invalid/v1",
            "",
            "OpenRouter API key is missing",
        ),
        (
            "Local (LM Studio)",
            "",
            "unused-local-key",
            "Local model endpoint is missing or invalid",
        ),
        (
            "Local (LM Studio)",
            "planner-local-endpoint-without-scheme",
            "unused-local-key",
            "Local model endpoint is missing or invalid",
        ),
    ),
)
def test_missing_planner_transport_configuration_fails_before_queryplan_and_search(
    tmp_path: Path,
    monkeypatch: Any,
    provider: str,
    local_url: str,
    api_key: str,
    failure_kind: str,
) -> None:
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example rule?",
        planner_response=_planner_payload(),
    )
    config = replace(
        config,
        fast_provider=provider,
        fast_model="configured-planner-model",
        local_url=local_url,
        or_api_key=api_key,
    )
    accumulator = CostAccumulator()

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="model call failed closed: ValueError",
    ) as caught:
        orchestrator.run_pipeline(
            config,
            deps,
            NullStatusWriter(),
            accumulator,
        )

    assert len(harness.planner_prompts) == 1
    assert capture["query_plan_admission_calls"] == 0
    assert harness.search_calls == []
    assert accumulator.snapshot()["calls_by_phase"] == {}
    assert failure_kind not in str(caught.value)
    if local_url:
        assert local_url not in harness.planner_prompts[0]
        assert local_url not in str(caught.value)
    if api_key:
        assert api_key not in harness.planner_prompts[0]
        assert api_key not in str(caught.value)


def test_default_model_planner_owns_long_narrated_request_and_first_dispatch(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    query = " ".join(
        [
            "I am trying to settle one practical question for a memo, but here is the backstory.",
            "Last year a colleague used an older Example form; that is context, not a second request.",
            "I first thought I needed a broad comparison, correction: I only need the current filing threshold.",
            "For example, a neighboring program uses a different threshold, but do not research that example.",
            "Please identify the current Example filing threshold from an appropriate source.",
        ]
        + [f"Background note {index} should remain context." for index in range(1, 45)]
        + ["END-OF-NARRATED-UTTERANCE central requirement remains singular."]
    )
    model_query = "Example current filing threshold official source"
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query=query,
        planner_response=_planner_payload(query_texts=[model_query]),
    )

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )

    assert outcome.report
    assert len(" ".join(query.split())) > 500
    assert len(harness.planner_prompts) == 1
    normalized_query = " ".join(query.split())
    assert normalized_query in harness.planner_prompts[0]
    planner_kwargs = harness.planner_kwargs[0]
    assert planner_kwargs["provider"] == "selected-offline-fast-provider"
    assert planner_kwargs["model"] == "selected-offline-fast-model"
    assert planner_kwargs["use_reasoning"] is True
    assert planner_kwargs["require_json"] is True
    initial = capture["initial_contract_at_convergence"]
    assert [item["component_id"] for item in initial["accepted_answer_component_refs"]] == ["component:01"]
    planner_metadata = capture["planner_projection_at_convergence"]["question_meaning_record"]["metadata"]
    assert planner_metadata["semantic_planning_owner"] == ("selected fast-model SearchPlanner")
    assert planner_metadata["model_proposed_component_count"] == 1
    assert capture["query_plan_admission_calls"] == 1
    assert capture["query_plan_admission"].current_queries == [model_query]
    assert harness.search_calls[0]["queries"] == [model_query]
    assert harness.forbidden_live_calls == []


def test_bounded_supplied_context_reaches_model_without_becoming_evidence(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    supplied_context = {
        "document_refs": [
            {
                "ref_id": "supplied-doc:benefits-notes",
                "kind": "future_document_summary_ref",
            }
        ],
        "summaries": ["The notes discuss an older Example alias and warn that the name changed."],
    }
    model_query = "Example current rule under renamed program"
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="Which current rule applies here?",
        supplied_context=supplied_context,
        planner_response=_planner_payload(query_texts=[model_query]),
    )

    orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )

    prompt = harness.planner_prompts[0]
    assert "supplied-doc:benefits-notes" in prompt
    assert "The notes discuss an older Example alias" in prompt
    assert '"planning_context_only":true' in prompt
    assert '"evidence_admitted":false' in prompt
    initial = capture["initial_contract_at_convergence"]
    assert len(initial["accepted_answer_component_refs"]) == 1
    assert capture["evidence_at_convergence"].get("evidence_items", []) == []
    assert capture["query_plan_admission"].current_queries == [model_query]
    assert harness.search_calls[0]["queries"] == [model_query]


@pytest.mark.parametrize(
    ("planner_response", "match"),
    [
        ({}, "semantic proposal failed closed"),
        (RuntimeError("selected model unavailable"), "model call failed closed"),
    ],
)
def test_invalid_or_unavailable_default_model_fails_before_queryplan_and_search(
    tmp_path: Path,
    monkeypatch: Any,
    planner_response: Any,
    match: str,
) -> None:
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="What is the current Example rule?",
        planner_response=planner_response,
    )

    with pytest.raises(SearchPlannerModelAdapterError, match=match):
        orchestrator.run_pipeline(
            config,
            deps,
            NullStatusWriter(),
            CostAccumulator(),
        )

    assert len(harness.planner_prompts) == 1
    assert capture["query_plan_admission_calls"] == 0
    assert harness.search_calls == []
    assert harness.forbidden_live_calls == []
    assert harness.model_system_prompts.count(SEARCH_PLANNER_MODEL_SYSTEM_PROMPT) == 1
    assert harness.model_system_prompts.count(DEFAULT_SYSTEM["researcher"]) == 0


def test_model_multipart_proposal_preserves_five_components_and_queryplan_floor() -> None:
    kernel = _kernel_after_run_contract()
    payload = _planner_payload(component_count=5)
    fake_model = FakePlannerModel(payload)
    planner = SearchPlannerModelAdapter(
        ask_model=fake_model,
        clean_json_response=lambda value: value,
        provider="selected-offline-fast-provider",
        model="selected-offline-fast-model",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )
    narrated_query = (
        "I will describe the situation conversationally rather than as a list; "
        "the model proposal identifies the five genuinely distinct answer needs."
    )
    convergence = execute_initial_query_strategy_convergence(
        run_kernel=kernel,
        router_query_preparation_contract=_router_state(),
        query=narrated_query,
        strategy="Balanced",
        current_date="2026-07-20",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        exclude_domains=[],
        news_preferred_domains=[],
        route_projection={"route_id": "route:model-owned-five"},
        run_contract_projection=kernel.state.run_contract_projection,
        planner_adapter=planner,
        provider_diagnostics=[],
    )
    query_authority = build_query_plan_runtime_adapter(
        run_id=kernel.state.run_id,
        primary_entity="Example",
        entities_list=["Example"],
        core_topic="Example multipart request",
        user_query=narrated_query,
        intent="general",
        clean=lambda value: " ".join(value.split()),
    )
    action = kernel.authorize_query_plan_admission(
        inputs={"candidate_count": len(convergence.candidate_queries)}
    )
    admission = execute_query_plan_admission_action(
        action,
        query_authority=query_authority,
        router_query_preparation_contract=_router_state(),
        candidate_queries=convergence.candidate_queries,
        candidate_strategies=convergence.candidate_strategies,
        candidate_source=convergence.candidate_source,
        query_type=convergence.query_type,
        current_date="2026-07-20",
        max_queries=convergence.max_queries,
        route_runtime_posture=convergence.effective_route_posture,
        accepted_contract=(
            kernel.state.current_answer_contract
            or kernel.state.initial_answer_contract
        ),
        initial_query_allocation_policy=convergence.initial_query_allocation_policy,
    )

    assert len(fake_model.calls) == 1
    accepted = kernel.state.initial_answer_contract["accepted_answer_component_refs"]
    assert [item["component_id"] for item in accepted] == [f"component:{index:02d}" for index in range(1, 6)]
    assert accepted[1]["dependency_component_ids"] == []
    metadata = kernel.state.search_planner_proposal_projection["question_meaning_record"]["metadata"]
    assert metadata["model_proposed_component_count"] == 5
    assert metadata["explicit_factual_component_list"] is True
    assert metadata["deterministic_component_ids_match_model"] is False
    assert metadata["deterministic_query_shape_role"] == ("compatibility_observability_only")
    assert len(admission.current_queries) == 5
    assert admission.current_queries == [f"Model-owned semantic need for component {index}" for index in range(1, 6)]


def test_model_output_above_five_component_ceiling_fails_closed() -> None:
    fake_model = FakePlannerModel(_planner_payload(component_count=6))
    planner = SearchPlannerModelAdapter(
        ask_model=fake_model,
        clean_json_response=lambda value: value,
        provider="selected-offline-fast-provider",
        model="selected-offline-fast-model",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )

    with pytest.raises(SearchPlannerModelAdapterError, match="semantic proposal failed closed"):
        planner.produce(
            {
                "user_query_text_for_planning": "A multipart request.",
                "safe_context": {},
            }
        )

    assert len(fake_model.calls) == 1


def test_deterministic_fixture_requires_explicit_direct_injection() -> None:
    adapter = DeterministicSearchPlannerAdapter()
    declared = {item.name: item for item in fields(RunDeps)}

    assert declared["search_planner_adapter"].default is None
    assert adapter.adapter_version == "searchos_deterministic_search_planner_v1"
    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert "DeterministicSearchPlannerAdapter" not in source
