from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any, Mapping

import pytest

import core.pipeline as pipeline
from core.acquisition_adapters import AcquisitionTransports
from core.acquisition_control import (
    build_acquisition_authority_snapshot,
)
from core.cap_enforcement import RunCapPolicy
from core.run_kernel import RunKernel
from core.search_judgment_read_assessment_runtime import (
    execute_search_judgment_read_source_and_custody,
)
from core.search_planner_runtime import (
    DeterministicSearchPlannerAdapter,
    SearchPlannerRuntimeError,
)
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


def _searchos_slots(harness: Any) -> list[dict[str, Any]]:
    state = _kernel_trace(harness)["searchos_state"]
    return [
        state["slots_by_id"][slot_id]
        for slot_id in state["active_slot_ids"]
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
    projection = trace["searchos_slice_a"]
    slots = _searchos_slots(harness)
    assert len(harness.read_assessment_calls) == len(slots)
    assert len({item["slot_id"] for item in harness.read_assessment_calls}) == len(
        harness.read_assessment_calls
    )
    assert all(slot["posture"] == "unresolved_handoff" for slot in slots)
    assert all(slot["latest_reason"] == "offline_no_read" for slot in slots)
    assert all(slot["read_nomination_count"] == 0 for slot in slots)
    assert projection["provider_calls_attempted"] == 0
    assert projection["provider_calls_completed"] == 0
    assert projection["standalone_read_assessment_invoked"] is False
    assert _read_actions(harness) == []
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
    ("decision", "expected_failure", "expected_posture"),
    [
        ("MODEL_FAILURE", "model_transport_failed:AssertionError", "judgment_failed"),
        ("MALFORMED", "model_output_malformed", "judgment_failed"),
        ("WRAPPED_JSON", "model_output_malformed", "judgment_failed"),
        (
            "INVALID_NOMINATION",
            "model_output_invalid:read_nomination_is_outside_current_candidate_window",
            "stale_or_invalid",
        ),
    ],
)
def test_assessment_failure_is_typed_closed_without_fallback_or_acquisition(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    expected_failure: str,
    expected_posture: str,
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
    projection = trace["searchos_slice_a"]
    state = _kernel_trace(harness)["searchos_state"]
    slots = _searchos_slots(harness)
    assert len(harness.read_assessment_calls) == len(slots)
    assert state["budget"]["failed_logical_judgment_calls"] == len(slots)
    assert all(slot["posture"] == expected_posture for slot in slots)
    assert all(slot["latest_reason"] == expected_failure for slot in slots)
    assert all(slot["custody_refs"] == [] for slot in slots)
    assert projection["provider_calls_attempted"] == 0
    assert projection["provider_calls_completed"] == 0
    assert projection["standalone_read_assessment_invoked"] is False
    assert _acquisition_actions(harness) == []


def test_duplicate_url_contributors_preserve_occurrences_in_one_component_slot(
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
    assert harness.searchos_product_result is not None
    revision_1 = harness.searchos_product_result.revision_1
    assert revision_1["initial_identity_count"] == 2
    assert len(revision_1["bounded_candidate_material_refs"]) == 2
    assert revision_1["selection_facts"]["selected_candidate_count"] == 1
    slots = _searchos_slots(harness)
    assert len(slots) == 1
    assert all(len(slot["candidate_use_option_refs"]) == 1 for slot in slots)
    assert len(harness.read_assessment_calls) == len(slots)


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

    projection = outcome.execution_trace["searchos_slice_a"]
    assert projection["owner"] == "RunKernel.SearchOSIterativeJudgment"
    state = _kernel_trace(harness)["searchos_state"]
    assert state, projection
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
    slots = _searchos_slots(harness)
    assert len(slots) == 2
    assert {slot["component_ref"]["component_id"] for slot in slots} == set(
        obligation_ref["component_ids"]
    )
    assert all(
        slot["source_obligation_ref"] == obligation_ref for slot in slots
    )
    assert len(set(state["active_slot_ids"])) == 2
    assert len(harness.read_assessment_calls) == 2
    assert state["budget"]["charged_logical_judgment_calls"] == 2


def test_shared_obligation_descriptor_uses_accepted_contract_not_search_work_plan(
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
    baseline = build_acquisition_authority_snapshot(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        current_answer_contract=kernel.state.current_answer_contract,
        initial_answer_contract=kernel.state.initial_answer_contract,
        search_executor_handoff_state=(
            kernel.state.search_executor_handoff_state
        ),
    )
    obligation_ref = baseline["source_obligations_by_id"][shared_obligation_id]
    assert obligation_ref["component_ids"] == [
        "fixture-component-01",
        "fixture-component-02",
    ]
    assert not hasattr(kernel.state, "search_work_plan")


def test_five_product_slots_are_all_assessed_once(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    obligation_ids = [
        f"fixture-obligation-{index:02d}" for index in range(1, 6)
    ]
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What are Alpha's five current official rule dimensions?",
        core_topic="Alpha current official rule dimensions",
        primary_entity="Alpha",
        read_assessment_decision="NO_READ",
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                [[obligation_id] for obligation_id in obligation_ids]
            ),
        },
        environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
    )

    state = _kernel_trace(harness)["searchos_state"]
    assert len(state["active_slot_ids"]) == 5
    assert len(harness.read_assessment_calls) == 5
    assert len(
        {call["slot_id"] for call in harness.read_assessment_calls}
    ) == 5
    projection = outcome.execution_trace["searchos_slice_a"]
    assert state["budget"]["charged_logical_judgment_calls"] == 5
    assert set(projection["slot_postures"].values()) == {
        "unresolved_handoff"
    }
    assert projection["provider_calls_attempted"] == 0


def test_sixth_product_component_is_rejected_before_any_assessment(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response_only_discovery(monkeypatch)
    obligation_ids = [
        f"fixture-obligation-{index:02d}" for index in range(1, 7)
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

    with pytest.raises(
        SearchPlannerRuntimeError,
        match="five-component acceptance ceiling",
    ):
        run_post_retirement_ordinary_pipeline(
            tmp_path,
            monkeypatch,
            mode="Fast",
            query="What are Alpha's six current official rule dimensions?",
            core_topic="Alpha current official rule dimensions",
            primary_entity="Alpha",
            read_assessment_decision="NO_READ",
            deps_overrides={
                "process_search_queries": record_process_search_queries,
                "search_planner_adapter": _SlotFixtureSearchPlannerAdapter(
                    [[obligation_id] for obligation_id in obligation_ids]
                ),
                "searchos_read_acquisition_transports": AcquisitionTransports(
                    tavily_extract=lambda payload: provider_calls.append(payload)
                    or {}
                ),
            },
            environment_overrides={"TAVILY_API_KEY": "offline-placeholder"},  # pragma: allowlist secret
            harness_sink=harnesses,
        )

    assert len(harnesses) == 1
    harness = harnesses[0]
    assert harness.run_kernel is None
    assert harness.read_assessment_calls == []
    assert provider_calls == []
    assert search_dispatches == []
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
    projection = trace["searchos_slice_a"]
    kernel_trace = _kernel_trace(harness)
    state = kernel_trace["searchos_state"]
    slots = _searchos_slots(harness)
    assert len(harness.read_assessment_calls) == len(slots) * 2
    assert len(calls) == 1, json.dumps(
        {
            "projection": projection,
            "searchos_state": state,
            "acquisition_actions": _acquisition_actions(harness),
            "acquisition_control": kernel_trace["acquisition_control_state"],
        },
        sort_keys=True,
    )
    assert cap_policy.fetch_read_operations == 1
    assert projection["provider_calls_attempted"] == 1
    assert projection["provider_calls_completed"] == 1
    assert len(projection["semantic_handoff_refs"]) == len(slots)
    assert all(len(slot["custody_refs"]) == 1 for slot in slots)
    assert all(len(slot["semantic_handoff_refs"]) == 1 for slot in slots)
    custody_refs = [slot["custody_refs"][0] for slot in slots]
    assert sum(bool(item["same_normalized_url_reused"]) for item in custody_refs) == (
        len(slots) - 1
    )
    assert all(item["bounded_retention"] is True for item in custody_refs)
    assert all(item["source_obligation_satisfied"] is False for item in custody_refs)
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
    assert record["attempted_url"] == "https://alpha.example/official-rule"
    assert record["provider_reported_url"] == (
        "https://provider.example/reported-page"
    )
    assert record["final_url"] == "https://final.example/redirected-page"
    assert record["canonical_url"] == (
        "https://canonical.example/canonical-page"
    )
    assert record["semantic_support_created"] is False
    assert record["source_obligation_satisfied"] is False
    assert projection["standalone_read_assessment_invoked"] is False
def test_successful_read_uses_only_searchos_read_custody(
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
    no_read_projection = no_read_outcome.execution_trace["searchos_slice_a"]
    read_projection = read_outcome.execution_trace["searchos_slice_a"]
    assert no_read_projection["semantic_handoff_refs"] == []
    assert read_projection["semantic_handoff_refs"]
    assert no_read_projection["all_passages_iteration_append_count"] == 0
    assert read_projection["all_passages_iteration_append_count"] == 0
    assert read_projection["read_custody_is_only_support_proposal_eligible_material"] is True


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

    projection = outcome.execution_trace["searchos_slice_a"]
    kernel_trace = _kernel_trace(harness)
    slots = _searchos_slots(harness)
    assert len(calls) == 1
    assert projection["provider_calls_attempted"] == 1
    assert projection["provider_calls_completed"] == 0
    assert sum(slot["read_nomination_count"] for slot in slots) == 1
    failed_read_slot = next(
        slot for slot in slots if slot["read_nomination_count"] == 1
    )
    assert failed_read_slot["latest_reason"] == (
        "read_transport_failure:selected_provider_transport_failed"
    )
    assert all(slot["custody_refs"] == [] for slot in slots)
    assert projection["semantic_handoff_refs"] == []
    assert projection["standalone_read_assessment_invoked"] is False
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
