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
    QUERY_PRODUCTION_STAGE,
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
    query_plan_admission_inputs_from_query_production_projection,
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
    ) -> str:
        kwargs = {
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
        }
        if system_prompt == SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
            self._record_model_call(system_prompt, kwargs)
            self.planner_prompts.append(prompt)
            self.planner_kwargs.append(dict(kwargs))
            if provider == "OpenRouter" and not api_key:
                raise ValueError("OpenRouter API key is missing")
            if provider == "Local (LM Studio)" and not str(base_url or "").startswith(
                ("http://", "https://")
            ):
                raise ValueError("Local model endpoint is missing or invalid")
            if isinstance(self.planner_response, Exception):
                raise self.planner_response
            if isinstance(self.planner_response, str):
                response = self.planner_response
            else:
                response = json.dumps(self.planner_response)
            if cost_accumulator is not None:
                cost_accumulator.record_model_call(
                    phase=cost_phase,
                    model=model,
                    input_tokens=11,
                    output_tokens=7,
                )
            return response
        return super().ask_model(prompt, system_prompt, **kwargs)


class ResponseOnlyPlannerAdapter:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = deepcopy(dict(response))
        self.calls: list[dict[str, Any]] = []

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(planner_input)))
        return deepcopy(self.response)


class ResponseOnlyScoutAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def produce(self, scout_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(scout_input)))
        queries: list[dict[str, Any]] = []
        organic_results: list[dict[str, Any]] = []
        for index, raw_query in enumerate(
            scout_input.get("candidate_queries") or (),
            start=1,
        ):
            query = dict(raw_query)
            query["execution_status"] = "executed_by_fake_adapter"
            queries.append(query)
            organic_results.append(
                {
                    "query_id": query["query_id"],
                    "related_dimension_ids": query["related_dimension_ids"],
                    "title": f"Offline direction hint {index}",
                    "link": f"https://example.invalid/hint-{index}",
                    "snippet": "Sanitized response-only identity direction.",
                    "position": index,
                }
            )
        return {
            "scout_queries": queries,
            "organic_results": organic_results,
            "confidence_posture": "directional",
            "disambiguation_posture": "offline_response_only",
        }


class ResponseOnlyRevisionAdapter:
    def __init__(self, *, query_text: str) -> None:
        self.query_text = query_text
        self.calls: list[dict[str, Any]] = []

    def produce(self, revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(revision_input)))
        return {
            "revised_question_meaning_summary": (
                "Use the bounded response-only identity direction for targeting."
            ),
            "component_search_requirement_updates": [
                {
                    "component_id": "component:model:1",
                    "requirement_id": "requirement:model:1:revised",
                    "requirement_summary": "Target the resolved official name.",
                    "source_obligation_candidate_ids": ["obligation:model:1"],
                    "metadata": {
                        "query_strategy_candidates": [
                            {
                                "strategy_id": "strategy:model:1:revised",
                                "component_id": "component:model:1",
                                "candidate_kind": "primary",
                                "candidate_query_text": self.query_text,
                                "requested_role": "official_bias",
                                "source_obligation_candidate_ids": [
                                    "obligation:model:1"
                                ],
                                "official_canonical_intent": "official_source",
                                "distinct_need_justification": (
                                    "Scout resolved the bounded identity target."
                                ),
                            }
                        ]
                    },
                }
            ],
            "consumed_ambiguity_dimension_ids": list(
                revision_input["consumed_ambiguity_dimension_ids"]
            ),
            "consumed_scout_hint_ids": list(
                revision_input["consumed_scout_hint_ids"]
            ),
            "amendment_candidates": [],
            "mandatory_caveats": ["Scout hints remain non-evidence."],
            "prohibited_upgrades": ["Do not cite Scout hints."],
            "normalization_obligations": [],
            "assumptions": [],
            "unresolved_ambiguities": [],
            "confidence_posture": "directional",
            "revision_posture": "proposal_only",
        }


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
    obligations: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    for index in range(1, component_count + 1):
        component_id = f"component:model:{index}"
        obligation_id = f"obligation:model:{index}"
        query_text = (
            queries[index - 1]
            if index <= len(queries)
            else f"Model owned exact query for component {index}"
        )
        components.append(
            {
                "component_id": component_id,
                "component_revision": "1",
                "component_purpose": "user_facing_answer_target",
                "user_facing_label": f"Model component {index}",
                "user_facing_question": f"What is model-owned need {index}?",
                "requirement_posture": "required",
                "acceptance_criteria": ["Direct source support."],
                "semantic_slot_ids": ["slot:model-subject"],
                "source_obligation_candidate_ids": [obligation_id],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "dependency_component_ids": (
                    [f"component:model:{index - 1}"] if index > 1 else []
                ),
                "materiality": "material",
            }
        )
        obligations.append(
            {
                "candidate_id": obligation_id,
                "obligation_kind": "no_special_obligation",
                "component_candidate_ids": [component_id],
                "strictness": "required",
            }
        )
        strategy: dict[str, Any] = {
            "strategy_id": f"strategy:model:{index}:primary",
            "component_id": component_id,
            "candidate_kind": "primary",
            "candidate_query_text": query_text,
            "requested_role": "initial",
            "source_obligation_candidate_ids": [obligation_id],
            "distinct_need_justification": (
                "Primary query for this model-proposed accepted component."
            ),
            "recon_requirement": {
                "posture": "not_needed",
                "unresolved_dimension_ids": [],
                "candidate_queries": [],
                "required_for_truthful_targeting": False,
            },
        }
        if index == 1 and recon_posture != "not_needed":
            strategy["recon_requirement"] = {
                "posture": recon_posture,
                "unresolved_dimension_ids": ["dimension:model:entity-identity"],
                "candidate_queries": [
                    {
                        "dimension_id": "dimension:model:entity-identity",
                        "candidate_query_text": "Old Example New Example identity",
                        "query_kind": "disambiguation_probe",
                    }
                ],
                "required_for_truthful_targeting": recon_posture == "required",
            }
        requirements.append(
            {
                "component_id": component_id,
                "requirement_id": f"requirement:model:{index}:initial",
                "requirement_summary": f"Find support for model need {index}.",
                "source_obligation_candidate_ids": [obligation_id],
                "metadata": {
                    "query_strategy_candidates": [strategy],
                    "provider_name_neutral": True,
                },
            }
        )
    return {
        "question_meaning_summary": (
            "Use exactly the warranted component structure in this model proposal."
        ),
        "requested_output": "A source-bound answer for every warranted component.",
        "semantic_slots": [
            {
                "slot_id": "slot:model-subject",
                "slot_kind": "entity",
                "status": "explicit",
                "candidate_values": ["Example"],
                "selected_value": "Example",
                "materiality": "material",
            }
        ],
        "answer_components": components,
        "source_obligation_candidates": obligations,
        "component_search_requirements": requirements,
        "material_ambiguity_posture": (
            "directional_recon_optional"
            if recon_posture == "optional"
            else "none"
        ),
        "mandatory_caveats": [],
        "prohibited_upgrades": ["Do not treat planning material as evidence."],
        "normalization_obligations": [],
        "assumptions": [],
        "unsupported_or_deferred_outputs": [
            "Later Analyst discoveries remain governed by amendment admission."
        ],
    }


def _install_chain_capture(monkeypatch: Any) -> dict[str, Any]:
    captured: dict[str, Any] = {"query_plan_admission_calls": 0}
    original_convergence = orchestrator.execute_initial_query_strategy_convergence
    original_admission = orchestrator.execute_query_plan_admission_action

    def convergence_wrapper(**kwargs: Any) -> Any:
        result = original_convergence(**kwargs)
        kernel = kwargs["run_kernel"]
        captured["run_kernel"] = kernel
        captured["convergence"] = result
        captured["initial_contract_at_convergence"] = deepcopy(
            kernel.state.initial_answer_contract
        )
        captured["planner_projection_at_convergence"] = deepcopy(
            kernel.state.search_planner_proposal_projection
        )
        captured["scout_projection_at_convergence"] = deepcopy(
            kernel.state.scout_disambiguation_report_projection
        )
        captured["revision_projection_at_convergence"] = deepcopy(
            kernel.state.search_planner_revision_projection
        )
        captured["evidence_at_convergence"] = deepcopy(
            kernel.state.evidence_ledger.to_projection().to_dict()
        )
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
            "The retrieved source supports the bounded answer. "
            "[[1]](https://example.example/report-1)"
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
        return any(
            _contains_object_identity(item, target) for item in value.values()
        )
    if isinstance(value, list | tuple):
        return any(_contains_object_identity(item, target) for item in value)
    return False


def test_rundeps_declares_typed_planner_scout_and_revision_seams() -> None:
    declared = {item.name: item for item in fields(RunDeps)}

    for name in (
        "search_planner_adapter",
        "scout_disambiguation_adapter",
        "search_planner_revision_adapter",
    ):
        assert name in declared
        assert declared[name].default is None

    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert "planner_adapter = deps.search_planner_adapter" in source
    assert "scout_adapter = deps.scout_disambiguation_adapter" in source
    assert "revision_adapter = deps.search_planner_revision_adapter" in source
    assert "getattr(deps, \"search_planner_adapter\"" not in source
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
    assert planner_kwargs["effort"] == "low"
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
        "search_work_plan": kernel.state.search_work_plan,
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
    assert [
        item["component_id"]
        for item in initial["accepted_answer_component_refs"]
    ] == ["component:model:1"]
    planner_metadata = capture["planner_projection_at_convergence"][
        "question_meaning_record"
    ]["metadata"]
    assert planner_metadata["semantic_planning_owner"] == (
        "selected fast-model SearchPlanner"
    )
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
        "summaries": [
            "The notes discuss an older Example alias and warn that the name changed."
        ],
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
        ({}, "missing required fields"),
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


def test_explicit_response_only_planner_scout_and_revision_cross_real_pipeline(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    planner = ResponseOnlyPlannerAdapter(
        _planner_payload(
            query_texts=["Unresolved Example official identity"],
            recon_posture="optional",
        )
    )
    scout = ResponseOnlyScoutAdapter()
    revised_query = "Resolved Example official current rule"
    revision = ResponseOnlyRevisionAdapter(query_text=revised_query)
    config, deps, harness, capture = _pipeline_fixture(
        tmp_path,
        monkeypatch,
        query="I may have the old name; what current rule applies?",
        planner_response=_planner_payload(),
        planner_adapter=planner,
        scout_adapter=scout,
        revision_adapter=revision,
        use_default_model=False,
    )
    endpoint = "http://injected-adapter-endpoint-sentinel.invalid/v1"
    credential = "injected-adapter-credential-sentinel"
    config = replace(
        config,
        fast_provider="OpenRouter",
        local_url=endpoint,
        or_api_key=credential,
    )
    accumulator = CostAccumulator()

    orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        accumulator,
    )

    assert len(planner.calls) == 1
    assert len(scout.calls) == 1
    assert len(revision.calls) == 1
    assert harness.planner_prompts == []
    assert harness.planner_kwargs == []
    assert SEARCH_PLANNER_MODEL_SYSTEM_PROMPT not in harness.model_system_prompts
    injected_input_text = json.dumps(planner.calls[0], sort_keys=True)
    assert endpoint not in injected_input_text
    assert credential not in injected_input_text
    assert not _contains_object_identity(planner.calls[0], accumulator)
    assert accumulator.snapshot()["calls_by_phase"].get("search_planner", 0) == 0
    assert capture["query_plan_admission"].current_queries == [revised_query]
    assert harness.search_calls[0]["queries"] == [revised_query]
    scout_projection = capture["scout_projection_at_convergence"]
    for key in (
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "fetch_read_retrieval_behavior_changed",
        "search_executor_runtime_activated",
    ):
        assert scout_projection[key] is False
    for hint in scout_projection["scout_result_hints"]:
        assert hint["evidence_admitted"] is False
        assert hint["citation_eligible"] is False
        assert hint["source_obligation_satisfied"] is False
    scout_json = json.dumps(scout_projection, sort_keys=True)
    assert scout_projection["final_answer_packet_created"] is False
    assert scout_projection["author_input_created"] is False
    assert '"final_answer_packet":{' not in scout_json
    assert '"author_input":{' not in scout_json
    assert capture["evidence_at_convergence"].get("evidence_items", []) == []
    revision_projection = capture["revision_projection_at_convergence"]
    assert revision_projection["revision_effect_class"] == (
        "query_direction_only_non_contractual"
    )


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
    inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
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
        inputs={"candidate_count": len(inputs.candidate_queries)}
    )
    admission = execute_query_plan_admission_action(
        action,
        query_authority=query_authority,
        router_query_preparation_contract=_router_state(),
        candidate_queries=inputs.candidate_queries,
        candidate_strategies=inputs.candidate_strategies,
        candidate_source=inputs.candidate_source,
        query_type=inputs.query_type,
        current_date="2026-07-20",
        max_queries=inputs.max_queries,
        route_runtime_posture=inputs.effective_route_posture,
        search_work_projection=convergence.search_work_plan,
        initial_query_allocation_policy=inputs.initial_query_allocation_policy,
    )

    assert len(fake_model.calls) == 1
    accepted = kernel.state.initial_answer_contract[
        "accepted_answer_component_refs"
    ]
    assert [item["component_id"] for item in accepted] == [
        f"component:model:{index}" for index in range(1, 6)
    ]
    assert accepted[1]["dependency_component_ids"] == ["component:model:1"]
    metadata = kernel.state.search_planner_proposal_projection[
        "question_meaning_record"
    ]["metadata"]
    assert metadata["model_proposed_component_count"] == 5
    assert metadata["explicit_factual_component_list"] is True
    assert metadata["deterministic_component_ids_match_model"] is False
    assert metadata["deterministic_query_shape_role"] == (
        "compatibility_observability_only"
    )
    assert len(admission.current_queries) == 5
    assert admission.current_queries == [
        f"Model owned exact query for component {index}" for index in range(1, 6)
    ]


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

    with pytest.raises(SearchPlannerModelAdapterError, match="five-component"):
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
