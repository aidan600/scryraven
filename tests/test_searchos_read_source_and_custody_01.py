from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.pipeline as pipeline
import core.pipeline_orchestrator as orchestrator
from core.acquisition_adapters import AcquisitionTransports
from core.acquisition_control import (
    AcquisitionControlError,
    build_acquisition_authority_snapshot,
)
from core.cap_enforcement import RunCapPolicy
from core.run_authority_search_judgment_adapter import (
    build_search_judgment_input_from_runtime,
)
from core.run_kernel import RunKernel
from core.search_judgment_read_assessment_runtime import (
    SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED,
    SEARCH_JUDGMENT_READ_TRACE_KEY,
    SearchJudgmentReadAssessmentError,
    build_full_search_judgment_containment_projection,
    execute_search_judgment_read_source_and_custody,
)
from core.search_planner_runtime import DeterministicSearchPlannerAdapter
from tests.helpers.offline_ordinary_pipeline import (
    run_post_retirement_ordinary_pipeline,
)


class _SlotFixtureSearchPlannerAdapter:
    """Offline proposal fixture with exact component/obligation membership."""

    def __init__(
        self,
        component_obligation_ids: list[list[str]],
    ) -> None:
        self.component_obligation_ids = component_obligation_ids

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        proposal = deepcopy(
            DeterministicSearchPlannerAdapter().produce(planner_input)
        )
        base_component = deepcopy(proposal["answer_components"][0])
        base_requirement = deepcopy(
            proposal["component_search_requirements"][0]
        )
        base_strategy = deepcopy(
            base_requirement["metadata"]["query_strategy_candidates"][0]
        )
        base_obligation = deepcopy(proposal["source_obligation_candidates"][0])

        components: list[dict[str, Any]] = []
        requirements: list[dict[str, Any]] = []
        components_by_obligation: dict[str, list[str]] = {}
        for index, obligation_ids in enumerate(
            self.component_obligation_ids,
            start=1,
        ):
            component_id = f"fixture-component-{index:02d}"
            for obligation_id in obligation_ids:
                components_by_obligation.setdefault(obligation_id, []).append(
                    component_id
                )
            component = deepcopy(base_component)
            component.update(
                {
                    "component_id": component_id,
                    "component_revision": "1",
                    "user_facing_label": f"Fixture component {index}",
                    "user_facing_question": (
                        f"What is the current official rule for fixture {index}?"
                    ),
                    "source_obligation_candidate_ids": list(obligation_ids),
                    "metadata": {"fixture_slot_component": True},
                }
            )
            components.append(component)

            strategy = deepcopy(base_strategy)
            strategy.update(
                {
                    "strategy_id": f"strategy:{component_id}:primary",
                    "component_id": component_id,
                    "candidate_query_text": (
                        f"fixture {index} current official rule"
                    ),
                    "source_obligation_candidate_ids": list(obligation_ids),
                }
            )
            requirement = deepcopy(base_requirement)
            requirement.update(
                {
                    "component_id": component_id,
                    "requirement_id": f"search-requirement:{component_id}",
                    "requirement_summary": (
                        f"Find current official material for fixture {index}."
                    ),
                    "source_obligation_candidate_ids": list(obligation_ids),
                    "metadata": {
                        "query_strategy_candidates": [strategy],
                        "allocation_posture": (
                            "one_primary_per_required_component"
                        ),
                        "provider_name_neutral": True,
                    },
                }
            )
            requirements.append(requirement)

        obligations: list[dict[str, Any]] = []
        for obligation_id in sorted(components_by_obligation):
            obligation = deepcopy(base_obligation)
            obligation.update(
                {
                    "candidate_id": obligation_id,
                    "component_candidate_ids": sorted(
                        components_by_obligation[obligation_id]
                    ),
                }
            )
            obligations.append(obligation)

        proposal["answer_components"] = components
        proposal["source_obligation_candidates"] = obligations
        proposal["component_search_requirements"] = requirements
        return proposal


def _install_response_only_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def response(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        body = "Alpha official current operating rule material. " * 20
        return [
            {
                "title": "Alpha official current operating rule",
                "url": "https://alpha.example/official-rule",
                "domain": "alpha.example",
                "credibility": 10,
                "snippet": body[:500],
                "raw_content": body,
            }
        ], []

    monkeypatch.setattr(pipeline, "search_web_results", response)
    monkeypatch.setattr(pipeline, "search_linkup_results", response)
    monkeypatch.setattr(pipeline, "search_exa_results", response)


def _install_duplicate_url_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def response(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        url = "https://alpha.example/shared-rule#provider-fragment"
        return [
            {
                "title": f"Alpha official rule occurrence {index}",
                "url": url,
                "domain": "alpha.example",
                "credibility": 10 - index,
                "snippet": f"Alpha rule snippet occurrence {index}.",
                "raw_content": (
                    f"Alpha full provider material occurrence {index}. " * 20
                ),
            }
            for index in (1, 2)
        ], []

    monkeypatch.setattr(pipeline, "search_web_results", response)
    monkeypatch.setattr(pipeline, "search_linkup_results", response)
    monkeypatch.setattr(pipeline, "search_exa_results", response)


def _kernel_trace(harness: Any) -> dict[str, Any]:
    assert harness.run_kernel is not None
    return harness.run_kernel.to_trace_fragment()["run_kernel"]


def _read_actions(harness: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in _kernel_trace(harness)["actions"]
        if str(item.get("action_type") or "").startswith("search_judgment_read")
    ]


def _acquisition_actions(harness: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in _kernel_trace(harness)["actions"]
        if str(item.get("action_type") or "").startswith("acquisition_")
    ]


def _difference_paths(left: Any, right: Any, path: str = "root") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        differences = [
            f"{path}.{key}: key-presence"
            for key in sorted(set(left) ^ set(right))
        ]
        for key in sorted(set(left) & set(right)):
            differences.extend(
                _difference_paths(left[key], right[key], f"{path}.{key}")
            )
        return differences
    if isinstance(left, list) and isinstance(right, list):
        differences = []
        if len(left) != len(right):
            differences.append(f"{path}: length {len(left)} != {len(right)}")
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences.extend(
                _difference_paths(left_item, right_item, f"{path}[{index}]")
            )
        return differences
    return [] if left == right else [f"{path}: value"]


def test_mandatory_no_read_call_ignores_legacy_full_judgment_flag(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="NO_READ",
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    trace = outcome.execution_trace
    projection = trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    assert len(harness.read_assessment_calls) == projection[
        "policy_admitted_slot_count"
    ]
    assert len({item["slot_id"] for item in harness.read_assessment_calls}) == len(
        harness.read_assessment_calls
    )
    assert projection["logical_assessment_count"] == len(
        harness.read_assessment_calls
    )
    assert projection["no_read_count"] == len(harness.read_assessment_calls)
    assert projection["request_read_page_count"] == 0
    assert projection["acquisition_need_proposal_count"] == 0
    assert projection["canonical_custody_count"] == 0
    assert projection["legacy_full_search_judgment_flag_consulted"] is False
    assert projection["deterministic_read_decision_used"] is False
    assert projection["deterministic_fallback_used"] is False
    assert _read_actions(harness)[0]["action_type"] == (
        "search_judgment_read_bindings_derive"
    )
    assert all(
        item["action_type"] == "search_judgment_read_assess"
        for item in _read_actions(harness)[1:]
    )
    assert _acquisition_actions(harness) == []
    packet = trace["search_result_candidate_packet"]
    assert packet["packet_revision"] == 1
    assert packet["answer_contract_ref"]["source"] == "initial_answer_contract"
    assert all("component_id" not in item for item in packet["candidate_records"])
    assert all(
        "source_obligation_candidate_ids" not in item
        for item in packet["candidate_records"]
    )


@pytest.mark.parametrize(
    ("decision", "expected_failure"),
    [
        (None, "model_transport_failed:AssertionError"),
        ("MALFORMED", "model_output_malformed"),
        ("WRAPPED_JSON", "model_output_malformed"),
        ("INVALID_NOMINATION", "invalid_binding_nomination"),
    ],
)
def test_assessment_failure_is_typed_closed_without_fallback_or_acquisition(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    decision: str | None,
    expected_failure: str,
) -> None:
    _install_response_only_discovery(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision=decision,
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    trace = outcome.execution_trace
    projection = trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    state = _kernel_trace(harness)["search_judgment_read_state"]
    assessments = list(state["assessment_records_by_slot"].values())
    assert len(harness.read_assessment_calls) == projection[
        "policy_admitted_slot_count"
    ]
    assert projection["assessment_failure_count"] == len(assessments)
    assert all(
        assessment["assessment_failure_code"] == expected_failure
        for assessment in assessments
    )
    assert all(assessment.get("decision") is None for assessment in assessments)
    assert all(
        assessment["deterministic_decision_used"] is False
        and assessment["deterministic_fallback_used"] is False
        for assessment in assessments
    )
    assert projection["acquisition_need_proposal_count"] == 0
    assert _acquisition_actions(harness) == []


def test_duplicate_url_contributors_create_distinct_bindings_one_candidate(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_duplicate_url_discovery(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="NO_READ",
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    packet = outcome.execution_trace["search_result_candidate_packet"]
    assert packet["candidate_count"] == 1
    assert packet["candidate_records"][0]["contributor_ref_count"] == 2
    state = _kernel_trace(harness)["search_judgment_read_state"]
    bindings = state["binding_state"]["bindings"]
    contributor_ids = {
        item["contributing_source_result_ref"]["source_result_id"]
        for item in bindings
    }
    assert len(contributor_ids) == 2
    assert len(bindings) == 4
    assert all(
        len(binding_ids) == 2
        for binding_ids in state["binding_state"]["bindings_by_slot"].values()
    )
    assert len(harness.read_assessment_calls) == 2


def test_shared_obligation_has_one_canonical_ref_and_two_component_slots(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    shared_obligation_id = "fixture-obligation-shared"
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What are Alpha's two current official rule dimensions?",
        core_topic="Alpha current official rule dimensions",
        primary_entity="Alpha",
        read_assessment_decision="NO_READ",
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                [[shared_obligation_id], [shared_obligation_id]]
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    projection = outcome.execution_trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    assert projection.get("failure_code") is None, projection.get("failure_code")
    assert projection["status"] == "checkpoint_completed", projection
    state = _kernel_trace(harness)["search_judgment_read_state"]
    assert state, projection
    binding_state = state["binding_state"]
    snapshot = harness.run_kernel.acquisition_authority_snapshot()
    assert list(snapshot["source_obligations_by_id"]) == [
        shared_obligation_id
    ]
    obligation_ref = snapshot["source_obligations_by_id"][
        shared_obligation_id
    ]
    assert obligation_ref["component_ids"] == [
        "fixture-component-01",
        "fixture-component-02",
    ]
    bindings = binding_state["bindings"]
    assert len(bindings) == 2
    assert {
        binding["component_ref"]["component_id"] for binding in bindings
    } == set(obligation_ref["component_ids"])
    assert all(
        binding["source_obligation_ref"] == obligation_ref
        for binding in bindings
    )
    assert len(binding_state["slot_order"]) == 2
    assert len(set(binding_state["slot_order"])) == 2
    assert len(harness.read_assessment_calls) == 2
    assert outcome.execution_trace[SEARCH_JUDGMENT_READ_TRACE_KEY][
        "logical_assessment_count"
    ] == 2


def test_shared_obligation_descriptor_conflict_is_typed_before_assessment(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    shared_obligation_id = "fixture-obligation-shared"
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What are Alpha's two current official rule dimensions?",
        core_topic="Alpha current official rule dimensions",
        primary_entity="Alpha",
        read_assessment_decision="NO_READ",
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                [[shared_obligation_id], [shared_obligation_id]]
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )
    kernel = harness.run_kernel
    conflicting_plan = deepcopy(kernel.state.search_work_plan)
    conflicting_plan["components"][1]["source_obligations"][0][
        "satisfaction_rule"
    ] = "Conflicting component-local satisfaction rule."

    with pytest.raises(AcquisitionControlError) as exc_info:
        build_acquisition_authority_snapshot(
            run_id=kernel.state.run_id,
            request_id=kernel.state.request_id,
            current_answer_contract=kernel.state.current_answer_contract,
            initial_answer_contract=kernel.state.initial_answer_contract,
            search_executor_handoff_state=(
                kernel.state.search_executor_handoff_state
            ),
            search_work_plan=conflicting_plan,
        )

    assert exc_info.value.code == (
        "shared_source_obligation_descriptor_conflict"
    )
    kernel.state.search_work_plan = conflicting_plan
    kernel.state.search_judgment_read_state = {}
    read_action_count = len(_read_actions(harness))
    conflicting_model_calls: list[str] = []

    result = execute_search_judgment_read_source_and_custody(
        run_kernel=kernel,
        candidate_packet=harness.read_candidate_packet,
        query_plan=harness.read_query_plan,
        discovery_result_store=harness.read_discovery_result_store,
        ask_model=lambda *_args, **_kwargs: conflicting_model_calls.append(
            "called"
        ),
        provider="offline-fake-provider",
        model="offline-fake-smart-model",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        available_providers={},
        acquisition_transports=None,
        before_transport=None,
        measure_context_stage=None,
    )

    assert result.projection["status"] == "binding_derivation_failed_closed"
    assert result.projection["failure_code"] == (
        "shared_source_obligation_descriptor_conflict"
    )
    assert conflicting_model_calls == []
    assert len(_read_actions(harness)) == read_action_count


def test_exactly_eight_active_slots_are_all_assessed_once(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    obligation_ids = [
        f"fixture-obligation-{index:02d}" for index in range(1, 9)
    ]
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What are Alpha's eight current official rule dimensions?",
        core_topic="Alpha current official rule dimensions",
        primary_entity="Alpha",
        read_assessment_decision="NO_READ",
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                [obligation_ids]
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    state = _kernel_trace(harness)["search_judgment_read_state"]
    binding_state = state["binding_state"]
    assert len(binding_state["slot_order"]) == 8
    assert binding_state["policy_admitted_slot_ids"] == (
        binding_state["slot_order"]
    )
    assert binding_state["policy_deferred_slot_ids"] == []
    assert len(harness.read_assessment_calls) == 8
    assert len(
        {call["slot_id"] for call in harness.read_assessment_calls}
    ) == 8
    projection = outcome.execution_trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    assert projection["logical_assessment_count"] == 8
    assert projection["no_read_count"] == 8
    assert projection["acquisition_need_proposal_count"] == 0


def test_ninth_active_slot_aborts_ordinary_run_before_any_assessment(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    obligation_ids = [
        f"fixture-obligation-{index:02d}" for index in range(1, 10)
    ]
    provider_calls: list[dict[str, Any]] = []
    search_dispatches: list[list[str]] = []
    harnesses: list[Any] = []
    original_process_search_queries = pipeline.process_search_queries

    def record_process_search_queries(
        queries: list[str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        search_dispatches.append(list(queries))
        return original_process_search_queries(queries, *args, **kwargs)

    with pytest.raises(SearchJudgmentReadAssessmentError) as exc_info:
        run_post_retirement_ordinary_pipeline(
            tmp_path,
            monkeypatch,
            mode="Fast",
            query="What are Alpha's nine current official rule dimensions?",
            core_topic="Alpha current official rule dimensions",
            primary_entity="Alpha",
            read_assessment_decision="NO_READ",
            deps_overrides={
                "process_search_queries": record_process_search_queries,
                "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                    [obligation_ids]
                ),
                "searchos_read_acquisition_transports": AcquisitionTransports(
                    tavily_extract=lambda payload: provider_calls.append(payload)
                    or {}
                ),
            },
            environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
            harness_sink=harnesses,
        )

    assert exc_info.value.code == SEARCH_JUDGMENT_READ_SLOT_BUDGET_EXCEEDED
    assert len(harnesses) == 1
    harness = harnesses[0]
    kernel = harness.run_kernel
    assert kernel is not None
    assert harness.read_assessment_calls == []
    assert _read_actions(harness) == []
    assert _acquisition_actions(harness) == []
    assert provider_calls == []
    assert kernel.state.search_judgment_read_state == {}
    custody = _kernel_trace(harness)["evidence_ledger"].get(
        "fetch_read_candidate_custody", {}
    )
    assert custody.get("fetch_read_candidate_custody_records", []) == []
    assert harness.full_search_judgment_inputs == []
    assert len(search_dispatches) == 1
    assert harness.analyst_calls == 0
    assert harness.analyst_prompts == []
    assert harness.economist_calls == []
    assert harness.author_prompts == []


def test_no_eligible_bindings_make_zero_assessment_and_acquisition_calls(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    _outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="NO_READ",
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )
    assert harness.run_kernel is not None
    assert harness.read_candidate_packet is not None
    assert harness.read_query_plan is not None
    assert harness.read_discovery_result_store is not None

    original_plan = harness.read_query_plan

    class CurrentDisambiguationOnlyPlan:
        plan_id = original_plan.plan_id
        items = tuple(
            replace(item, metadata={})
            if item.authorized_query is not None
            else item
            for item in original_plan.items
        )

        @staticmethod
        def to_ref() -> dict[str, Any]:
            return original_plan.to_ref()

        @staticmethod
        def authorized_discovery_item_refs() -> list[dict[str, Any]]:
            return original_plan.authorized_discovery_item_refs()

    model_calls: list[str] = []
    kernel = RunKernel(deepcopy(harness.run_kernel.state))
    prior_acquisition_actions = sum(
        1
        for action in kernel.state.issued_actions.values()
        if str(action.action_type.value).startswith("acquisition_")
    )
    result = execute_search_judgment_read_source_and_custody(
        run_kernel=kernel,
        candidate_packet=harness.read_candidate_packet,
        query_plan=CurrentDisambiguationOnlyPlan(),
        discovery_result_store=harness.read_discovery_result_store,
        ask_model=lambda *_args, **_kwargs: model_calls.append("called"),
        provider="offline-fake-provider",
        model="offline-fake-smart-model",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        available_providers={},
        acquisition_transports=None,
        before_transport=None,
        measure_context_stage=None,
    )

    assert result.projection["eligible_binding_count"] == 0
    assert result.projection["logical_assessment_count"] == 0
    assert result.projection["acquisition_need_proposal_count"] == 0
    assert result.provider_calls_attempted == 0
    assert result.provider_calls_completed == 0
    assert model_calls == []
    assert sum(
        1
        for action in kernel.state.issued_actions.values()
        if str(action.action_type.value).startswith("acquisition_")
    ) == prior_acquisition_actions


@pytest.mark.parametrize("selected_provider", ["linkup", "tavily"])
def test_response_only_read_reaches_main_kernel_canonical_custody(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    selected_provider: str,
) -> None:
    _install_response_only_discovery(monkeypatch)
    calls: list[dict[str, Any]] = []
    if selected_provider == "linkup":
        transports = AcquisitionTransports(
            linkup_fetch=lambda payload: calls.append(payload)
            or {
                "markdown": "Alpha official operating rule full-page material.",
                "url": "https://provider.example/reported-page",
                "final_url": "https://final.example/redirected-page",
                "canonical_url": "https://canonical.example/canonical-page",
            }
        )
    else:
        transports = AcquisitionTransports(
            tavily_extract=lambda payload: calls.append(payload)
            or {
                "results": [
                    {
                        "url": "https://provider.example/reported-page",
                        "raw_content": (
                            "Alpha official operating rule full-page material."
                        ),
                        "final_url": "https://final.example/redirected-page",
                        "canonical_url": (
                            "https://canonical.example/canonical-page"
                        ),
                    }
                ],
                "failed_results": [],
            }
        )
    availability = {
        "linkup": selected_provider == "linkup",
        "tavily": selected_provider == "tavily",
        "exa": False,
        "serper": False,
        "brave": False,
    }
    cap_policy = RunCapPolicy(
        max_search_dispatches=20,
        max_fetch_read_operations=1,
        max_author_model_calls=20,
        max_smart_search_judgment_model_calls=20,
        max_retries=0,
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="REQUEST_READ_PAGE",
        cap_policy=cap_policy,
        deps_overrides={
            "provider_availability": availability,
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": transports,
        },
        environment_overrides={
            (
                "LINKUP_API_KEY"
                if selected_provider == "linkup"
                else "TAVILY_API_KEY"
            ): "offline-placeholder"  # pragma: allowlist secret
        },
    )

    trace = outcome.execution_trace
    projection = trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    kernel_trace = _kernel_trace(harness)
    state = kernel_trace["search_judgment_read_state"]
    registry = state["custody_by_normalized_url"]
    assert len(harness.read_assessment_calls) == projection[
        "policy_admitted_slot_count"
    ]
    assert len(calls) == 1, json.dumps(
        {
            "projection": projection,
            "read_state": state,
            "acquisition_actions": _acquisition_actions(harness),
            "acquisition_control": kernel_trace["acquisition_control_state"],
        },
        sort_keys=True,
    )
    assert cap_policy.fetch_read_operations == 1
    assert projection["request_read_page_count"] == len(
        harness.read_assessment_calls
    )
    assert projection["acquisition_need_proposal_count"] == len(
        harness.read_assessment_calls
    )
    assert projection["canonical_custody_count"] == 1
    assert projection["same_url_custody_reuse_count"] == (
        len(harness.read_assessment_calls) - 1
    )
    assert len(registry) == 1
    custody = next(iter(registry.values()))
    assert custody["bounded_content_present"] is True
    assert custody["semantic_support_created"] is False
    assert custody["source_obligation_satisfied"] is False
    assert trace["urls_fetched"] == 1
    execution_actions = [
        item
        for item in _acquisition_actions(harness)
        if item["action_type"] == "acquisition_execute"
    ]
    assert len(execution_actions) == 1
    ledger = kernel_trace["evidence_ledger"]
    custody_records = ledger["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]
    assert len(custody_records) == 1
    record = custody_records[0]
    requested_url = next(iter(registry))
    assert record["attempted_url"] == requested_url
    assert record["provider_reported_url"] == (
        "https://provider.example/reported-page"
    )
    assert record["final_url"] == "https://final.example/redirected-page"
    assert record["canonical_url"] == (
        "https://canonical.example/canonical-page"
    )
    assert record["semantic_support_created"] is False
    assert record["source_obligation_satisfied"] is False
    assert projection["provider_failure_fallback_attempted"] is False
    assert projection["query_plan_continuation_created"] is False
    assert projection["citation_created"] is False
    assert projection["sufficiency_decided"] is False
    assert projection["final_answer_packet_created"] is False
    assert projection["author_input_created"] is False


def test_full_search_judgment_containment_restores_baseline_input_facts() -> None:
    baseline = {
        "schema_version": "ledger-v1",
        "owner": "RunKernel.EvidenceLedger",
        "candidate_count": 1,
        "candidate_records": [{"candidate_id": "baseline"}],
        "observation_refs": [{"observation_id": "base", "source": "baseline"}],
        "fetch_read_candidate_custody": {
            "candidate_content_custody_visible": False,
            "custody_record_count": 0,
            "readable_record_count": 0,
            "unreadable_record_count": 0,
            "fetch_read_candidate_custody_records": [],
            "custody_gaps": [],
            "custody_gap_count": 0,
        },
    }
    with_read = json.loads(json.dumps(baseline))
    with_read["candidate_count"] = 2
    with_read["candidate_records"].append({"candidate_id": "read-candidate"})
    with_read["observation_refs"].append(
        {
            "observation_id": "read-observation",
            "source": "fetch_read_content_packet_candidate_custody",
        }
    )
    with_read["fetch_read_candidate_custody"] = {
        "candidate_content_custody_visible": True,
        "custody_record_count": 1,
        "readable_record_count": 1,
        "unreadable_record_count": 0,
        "fetch_read_candidate_custody_records": [
            {
                "candidate_id": "read-candidate",
                "fetch_read_content_packet_id": "read-packet",
                "fetch_read_status": "readable",
            }
        ],
        "custody_gaps": [],
        "custody_gap_count": 0,
    }
    state = {
        "custody_by_normalized_url": {
            "https://alpha.example/report": {
                "candidate_id": "read-candidate",
                "fetch_read_content_packet_ref": {"packet_id": "read-packet"},
                "evidence_ledger_observation_ref": {
                    "observation_id": "read-observation"
                },
            }
        }
    }

    contained = build_full_search_judgment_containment_projection(
        evidence_ledger_projection=with_read,
        search_judgment_read_state=state,
    )

    assert contained == baseline
    serialized = json.dumps(contained, sort_keys=True)
    assert "read-candidate" not in serialized
    assert "read-packet" not in serialized
    assert "read-observation" not in serialized
    common = {
        "contract_projection": {"contract_id": "contract"},
        "query_authority_trace": {},
        "core_topic": "Alpha",
        "primary_entity": "Alpha",
        "result_count": 1,
        "iterations_run": 1,
        "source_tier_counts": {},
        "source_domain_counts": {},
        "top_source_domains": [],
        "provider_diagnostic_count": 0,
        "source_class_recovery_recommendation": {},
        "source_class_observability": {},
        "retrieval_stop_shadow_telemetry": {},
        "retrieval_stop_active_telemetry": {},
        "answer_contract_projection": {},
        "max_iterations": 1,
        "recovery_attempt_count": 0,
    }
    baseline_input = build_search_judgment_input_from_runtime(
        evidence_ledger_projection=baseline,
        **common,
    )
    contained_input = build_search_judgment_input_from_runtime(
        evidence_ledger_projection=contained,
        **common,
    )
    assert contained_input == baseline_input


def test_both_full_search_judgment_input_seams_apply_read_containment() -> None:
    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    assert source.count("build_full_search_judgment_containment_projection(") == 2


def test_successful_read_preserves_baseline_full_search_judgment_inputs(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    no_read_dir = tmp_path / "no_read"
    read_dir = tmp_path / "read"
    no_read_dir.mkdir()
    read_dir.mkdir()
    no_read_outcome, no_read_harness = run_post_retirement_ordinary_pipeline(
        no_read_dir,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="NO_READ",
        deps_overrides={"process_search_queries": pipeline.process_search_queries},
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )
    calls: list[dict[str, Any]] = []
    read_outcome, read_harness = run_post_retirement_ordinary_pipeline(
        read_dir,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="REQUEST_READ_PAGE",
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": AcquisitionTransports(
                tavily_extract=lambda payload: calls.append(payload)
                or {
                    "results": [
                        {
                            "url": "https://alpha.example/official-rule",
                            "raw_content": "Alpha full page material.",
                        }
                    ],
                    "failed_results": [],
                }
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    assert len(calls) == 1
    assert no_read_harness.full_search_judgment_inputs
    assert read_harness.full_search_judgment_inputs
    no_read_inputs = no_read_harness.full_search_judgment_inputs[:2]
    read_candidate_ids = [
        item.get("candidate_id")
        for item in read_harness.full_search_judgment_inputs[0][
            "evidence_ledger_ref"
        ]["candidate_records"]
    ]
    baseline_candidate_ids = [
        item.get("candidate_id")
        for item in no_read_inputs[0]["evidence_ledger_ref"]["candidate_records"]
    ]
    assert read_candidate_ids == baseline_candidate_ids, read_candidate_ids
    assert read_harness.full_search_judgment_inputs == no_read_inputs, {
        "differences": _difference_paths(
            read_harness.full_search_judgment_inputs,
            no_read_inputs,
        )[:30],
        "read_candidate_ids": read_candidate_ids,
        "baseline_candidate_ids": baseline_candidate_ids,
        "registry_candidate_ids": [
            item.get("candidate_id")
            for item in _kernel_trace(read_harness)[
                "search_judgment_read_state"
            ]["custody_by_normalized_url"].values()
        ],
    }
    assert read_outcome.report == no_read_outcome.report


def test_provider_failure_ends_after_one_attempt_without_fallback(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    calls: list[dict[str, Any]] = []

    def fail_linkup(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        raise RuntimeError("offline provider failure")

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=("Alpha current official operating rule",),
        read_assessment_decision="REQUEST_FIRST_THEN_NO_READ",
        deps_overrides={
            "provider_availability": {
                "linkup": True,
                "tavily": False,
                "exa": False,
                "serper": False,
                "brave": False,
            },
            "process_search_queries": pipeline.process_search_queries,
            "searchos_read_acquisition_transports": AcquisitionTransports(
                linkup_fetch=fail_linkup
            ),
        },
        environment_overrides={"LINKUP_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    projection = outcome.execution_trace[SEARCH_JUDGMENT_READ_TRACE_KEY]
    kernel_trace = _kernel_trace(harness)
    assert len(calls) == 1
    assert projection["request_read_page_count"] == 1
    assert projection["acquisition_need_proposal_count"] == 1
    assert projection["provider_calls_attempted"] == 1
    assert projection["provider_calls_completed"] == 0
    assert projection["acquisition_failure_count"] == 1
    assert projection["provider_failure_fallback_attempted"] is False
    assert projection["canonical_custody_count"] == 0
    execution_actions = [
        item
        for item in _acquisition_actions(harness)
        if item["action_type"] == "acquisition_execute"
    ]
    assert len(execution_actions) == 1
    control = kernel_trace["acquisition_control_state"]
    execution_observations = list(
        control["execution_observations_by_id"].values()
    )
    assert len(execution_observations) == 1
    assert execution_observations[0]["provider_calls_attempted"] == 1
    assert execution_observations[0]["provider_calls_completed"] == 0
    assert execution_observations[0][
        "provider_failure_fallback_attempted"
    ] is False
