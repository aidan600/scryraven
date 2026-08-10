from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.cap_enforcement import ExternalCallFamily, RunCapExceeded
from core.initial_query_allocation_policy import (
    DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    INITIAL_QUERY_ALLOCATION_POLICY_VERSION,
)
from core.initial_query_strategy_failure import InitialQueryStrategyFailureError
from core.ordinary_scout_disambiguation_adapter import OrdinaryScoutDisambiguationAdapter
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.query_production_runtime import (
    QUERY_PRODUCTION_STAGE,
    QueryStrategyConvergenceError,
    QueryStrategyConvergenceFailureCode,
    _recon_work_by_component,
    _strategies_with_authorized_revisions,
    execute_initial_query_strategy_convergence,
    execute_query_plan_admission_action,
    query_plan_admission_inputs_from_query_production_projection,
)
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_planner_model_adapter import accept_planner_model_output
from core.search_planner_revision_runtime import (
    SearchPlannerRevisionRuntimeError,
    SearchPlannerRevisionRuntimeSafeFailureCode,
)
from core.search_planner_runtime import SEARCH_PLANNER_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
QUERY_RUNTIME = ROOT / "core" / "query_production_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SCOUT_RUNTIME = ROOT / "core" / "scout_disambiguation_runtime.py"


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
        organic: list[dict[str, Any]] = []
        for index, raw_query in enumerate(scout_input.get("candidate_queries") or (), start=1):
            query = dict(raw_query)
            query["execution_status"] = "executed_by_fake_adapter"
            queries.append(query)
            organic.append(
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
            "organic_results": organic,
            "confidence_posture": "directional",
            "disambiguation_posture": "offline_response_only",
        }


class ResponseOnlyRevisionAdapter:
    def __init__(
        self,
        *,
        component_id: str = "component:1",
        source_ids: tuple[str, ...] = ("obligation:1:general",),
        query_text: str = "Renamed Example official current component 1",
        amendment: bool = False,
    ) -> None:
        self.component_id = component_id
        self.source_ids = source_ids
        self.query_text = query_text
        self.amendment = amendment
        self.calls: list[dict[str, Any]] = []

    def produce(self, revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(deepcopy(dict(revision_input)))
        amendments: list[dict[str, Any]] = []
        if self.amendment:
            amendments.append(
                {
                    "candidate_id": "candidate:recon-caveat",
                    "operation_kind": "add_caveat",
                    "component_id": self.component_id,
                    "caveat": ("Identity direction came from non-evidence Scout hints."),
                }
            )
        return {
            "revised_question_meaning_summary": ("Use the bounded offline identity direction for query targeting."),
            "component_search_requirement_updates": [
                {
                    "component_id": self.component_id,
                    "requirement_id": "requirement:1:revised",
                    "requirement_summary": "Target the resolved official name.",
                    "source_obligation_candidate_ids": list(self.source_ids),
                    "metadata": {
                        "query_strategy_candidates": [
                            {
                                "strategy_id": "strategy:1:revised-primary",
                                "component_id": self.component_id,
                                "candidate_kind": "primary",
                                "candidate_query_text": self.query_text,
                                "requested_role": "official_bias",
                                "source_obligation_candidate_ids": list(self.source_ids),
                                "official_canonical_intent": "official_source",
                                "distinct_need_justification": ("Scout resolved the bounded identity target."),
                            }
                        ]
                    },
                }
            ],
            "consumed_ambiguity_dimension_ids": list(revision_input["consumed_ambiguity_dimension_ids"]),
            "consumed_scout_hint_ids": list(revision_input["consumed_scout_hint_ids"]),
            "amendment_candidates": amendments,
            "mandatory_caveats": ["Scout hints remain non-evidence."],
            "prohibited_upgrades": ["Do not cite Scout hints."],
            "normalization_obligations": [],
            "assumptions": [],
            "unresolved_ambiguities": [],
            "confidence_posture": "directional",
            "revision_posture": "proposal_only",
        }


def _planner_payload(
    *,
    component_count: int = 1,
    secondary: bool = False,
    duplicate_secondary: bool = False,
    immediate_secondary: bool = False,
    recon: str = "not_needed",
    required_recon: bool = False,
    planner_provider_name: str | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    for index in range(1, component_count + 1):
        component_id = f"component:{index}"
        general_id = f"obligation:{index}:general"
        official_id = f"obligation:{index}:official"
        source_ids = [general_id]
        obligations.append(
            {
                "candidate_id": general_id,
                "obligation_kind": "no_special_obligation",
                "component_candidate_ids": [component_id],
                "strictness": "required",
            }
        )
        if secondary and index == 1:
            source_ids.append(official_id)
            obligations.append(
                {
                    "candidate_id": official_id,
                    "obligation_kind": "official_current",
                    "component_candidate_ids": [component_id],
                    "strictness": "required",
                }
            )
        components.append(
            {
                "component_id": component_id,
                "component_revision": "1",
                "user_facing_label": f"Required component {index}",
                "user_facing_question": f"What is required component {index}?",
                "requirement_posture": "required",
                "acceptance_criteria": ["Direct source support."],
                "semantic_slot_ids": ["slot:subject"],
                "source_obligation_candidate_ids": source_ids,
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "materiality": "material",
            }
        )
        primary_query = f"Example required component {index} primary source"
        primary: dict[str, Any] = {
            "strategy_id": f"strategy:{index}:primary",
            "component_id": component_id,
            "candidate_kind": "primary",
            "candidate_query_text": primary_query,
            "requested_role": "initial",
            "source_obligation_candidate_ids": [general_id],
        }
        if planner_provider_name:
            primary["provider_name"] = planner_provider_name
        if recon != "not_needed" and index == 1:
            primary["recon_requirement"] = {
                "posture": recon,
                "unresolved_dimension_ids": ["dim:entity-identity"],
                "candidate_queries": [
                    {
                        "dimension_id": "dim:entity-identity",
                        "candidate_query_text": "Old Example New Example identity",
                        "query_kind": "disambiguation_probe",
                    }
                ],
                "required_for_truthful_targeting": required_recon,
            }
        strategies = [primary]
        if secondary and index == 1:
            strategies.append(
                {
                    "strategy_id": "strategy:1:secondary",
                    "component_id": component_id,
                    "candidate_kind": "secondary",
                    "candidate_query_text": (
                        primary_query if duplicate_secondary else "Example component 1 official current rule"
                    ),
                    "requested_role": "official_bias",
                    "source_obligation_candidate_ids": [official_id],
                    "official_canonical_intent": "official_source",
                    "document_family": "official current rule",
                    "distinct_need_justification": ("A separate accepted official-current obligation."),
                    "immediate_dispatch_requested": immediate_secondary,
                    "immediate_dispatch_distinct_need": immediate_secondary,
                }
            )
        requirements.append(
            {
                "component_id": component_id,
                "requirement_id": f"requirement:{index}:initial",
                "requirement_summary": f"Find component {index} support.",
                "source_obligation_candidate_ids": source_ids,
                "metadata": {
                    "query_strategy_candidates": strategies,
                    "provider_name_neutral": True,
                },
            }
        )
    return {
        "question_meaning_summary": "Answer every accepted required component.",
        "requested_output": "A source-bound multi-component answer.",
        "semantic_slots": [
            {
                "slot_id": "slot:subject",
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
        "material_ambiguity_posture": ("material_ambiguity_present" if recon != "not_needed" else "none"),
        "mandatory_caveats": [],
        "prohibited_upgrades": ["Scout hints are not evidence."],
        "normalization_obligations": [],
        "assumptions": [],
        "unsupported_outputs": [],
    }


def _kernel_after_run_contract() -> RunKernel:
    kernel = RunKernel.start(run_id="run:searchos", request_id="request:searchos")
    action = kernel.authorize_run_contract_synthesis()
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
            status=RunStageStatus.COMPLETED,
            payload={
                "contract_projection": {
                    "contract_id": "run-contract:searchos",
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
        query="Compare every required Example component.",
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "comparison",
                "query_type": "comparison",
                "core_topic": "Example components",
                "primary_entity": "Example",
                "entities": ["Example"],
                "is_academic": False,
            }
        ),
    )


def _converge(
    payload: Mapping[str, Any],
    *,
    scout_adapter: Any | None = None,
    revision_adapter: Any | None = None,
    run_kernel: RunKernel | None = None,
    policy=DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
):
    kernel = run_kernel if run_kernel is not None else _kernel_after_run_contract()
    result = execute_initial_query_strategy_convergence(
        run_kernel=kernel,
        router_query_preparation_contract=_router_state(),
        query="Compare every required Example component.",
        strategy="Balanced",
        current_date="2026-07-19",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        exclude_domains=[],
        news_preferred_domains=[],
        route_projection={"route_id": "route:searchos"},
        run_contract_projection=kernel.state.run_contract_projection,
        planner_adapter=ResponseOnlyPlannerAdapter(payload),
        scout_adapter=scout_adapter,
        revision_adapter=revision_adapter,
        provider_diagnostics=[],
        initial_query_allocation_policy=policy,
    )
    return kernel, result


def _admit(kernel: RunKernel, convergence):
    inputs = query_plan_admission_inputs_from_query_production_projection(
        kernel.state.projections[QUERY_PRODUCTION_STAGE]
    )
    adapter = build_query_plan_runtime_adapter(
        run_id=kernel.state.run_id,
        primary_entity="Example",
        entities_list=["Example"],
        core_topic="Example components",
        user_query="Compare every required Example component.",
        intent="general",
        clean=lambda value: " ".join(value.split()),
    )
    action = kernel.authorize_query_plan_admission(inputs={"candidate_count": len(inputs.candidate_queries)})
    result = execute_query_plan_admission_action(
        action,
        query_authority=adapter,
        router_query_preparation_contract=_router_state(),
        candidate_queries=inputs.candidate_queries,
        candidate_strategies=inputs.candidate_strategies,
        candidate_source=inputs.candidate_source,
        query_type=inputs.query_type,
        current_date="2026-07-19",
        max_queries=inputs.max_queries,
        route_runtime_posture=inputs.effective_route_posture,
        search_work_projection=convergence.search_work_plan,
        initial_query_allocation_policy=inputs.initial_query_allocation_policy,
    )
    kernel.reduce(result.observation)
    return adapter, result


def test_five_required_components_reach_first_wave_without_global_truncation() -> None:
    kernel, convergence = _converge(_planner_payload(component_count=5))
    adapter, admission = _admit(kernel, convergence)

    assert len(kernel.state.initial_answer_contract["accepted_answer_component_refs"]) == 5
    assert len(convergence.query_production_result.candidate_queries) == 5
    assert len(admission.current_queries) == 5
    assert len(set(admission.current_queries)) == 5
    assert admission.observation.payload["small_global_initial_query_cap_applied"] is False
    assert admission.observation.payload["required_component_globally_truncated"] is False
    assert admission.router_query_preparation_contract.retrieval_budget_seed_facts["max_queries"] == 2
    adapter.admit_execution_queries(
        admission.current_queries,
        iteration=1,
        recovery_active=False,
    )
    ordered = [
        item for item in adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]["items"] if item.get("status") == "ordered"
    ]
    assert [item["authorized_query"] for item in ordered] == admission.current_queries
    assert [item["order"] for item in ordered] == [1, 2, 3, 4, 5]
    assert {item["iteration"] for item in ordered} == {1}
    assert all(item["metadata"]["accepted_component_ref"] for item in ordered)


def test_search_work_plan_carries_refs_but_never_complete_query_text() -> None:
    kernel, convergence = _converge(_planner_payload(component_count=2))
    plan = convergence.search_work_plan
    serialized = json.dumps(plan, sort_keys=True)

    assert plan["passive"] is False
    assert plan["runtime_consumed"] is True
    assert len(plan["components"]) == 2
    assert all(item["metadata"]["accepted_component_ref"] for item in plan["components"])
    assert all(item["metadata"]["search_requirement_refs"] for item in plan["components"])
    for query in convergence.query_production_result.candidate_queries:
        assert query not in serialized
    assert "candidate_query_text" not in serialized
    assert kernel.state.search_work_plan == plan


def test_secondary_is_prepared_not_dispatched_without_immediate_proof() -> None:
    kernel, convergence = _converge(_planner_payload(secondary=True))
    _, admission = _admit(kernel, convergence)

    allocation = admission.initial_query_admission
    assert len(allocation.admitted_candidate_queries) == 2
    assert len(allocation.immediate_dispatch_queries) == 1
    assert len(allocation.prepared_secondary_candidates) == 1
    prepared = allocation.prepared_secondary_candidates[0]
    assert prepared["later_authorizer"] == "SearchJudgment"
    assert prepared["distinct_need_justification"]
    assert prepared["authorized_query"] not in admission.current_queries
    assert admission.queries == admission.current_queries
    assert admission.observation.payload["post_result_followup_dispatched"] is False


def test_distinct_source_need_can_put_secondary_in_immediate_wave() -> None:
    kernel, convergence = _converge(_planner_payload(secondary=True, immediate_secondary=True))
    _, admission = _admit(kernel, convergence)

    assert len(admission.current_queries) == 2
    assert admission.initial_query_admission.prepared_secondary_candidates == ()
    assert admission.current_queries[1] == "Example component 1 official current rule"


def test_exact_duplicate_is_rejected_and_contributor_lineage_is_retained() -> None:
    kernel, convergence = _converge(_planner_payload(secondary=True, duplicate_secondary=True))
    adapter, admission = _admit(kernel, convergence)

    allocation = admission.initial_query_admission
    assert len(allocation.admitted_candidate_queries) == 1
    assert len(allocation.duplicate_candidates_rejected) == 1
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    survivor = next(
        item
        for item in trace["items"]
        if item.get("status") == "finalized" and item.get("phase") == "initial_component_query_admission"
    )
    assert survivor["metadata"]["duplicate_contributor_count"] == 1
    assert len(survivor["metadata"]["contributor_lineage"]) == 2


def test_materially_equivalent_candidate_without_distinct_need_is_rejected() -> None:
    payload = _planner_payload(secondary=True)
    secondary = payload["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][1]
    secondary["candidate_query_text"] = "Example required component 1 primary source official"
    secondary["requested_role"] = "initial"
    secondary["source_obligation_candidate_ids"] = ["obligation:1:general"]
    secondary.pop("official_canonical_intent")
    secondary.pop("document_family")

    kernel, convergence = _converge(payload)
    _, admission = _admit(kernel, convergence)

    rejected = admission.initial_query_admission.duplicate_candidates_rejected
    assert len(rejected) == 1
    assert rejected[0]["duplicate_kind"] == "materially_equivalent"
    assert admission.current_queries == ["Example required component 1 primary source"]


def test_second_primary_cannot_bypass_distinct_need_requirement() -> None:
    payload = _planner_payload()
    strategies = payload["component_search_requirements"][0]["metadata"]["query_strategy_candidates"]
    strategies.append(
        {
            "strategy_id": "strategy:1:extra-primary",
            "component_id": "component:1",
            "candidate_kind": "primary",
            "candidate_query_text": "Example component 1 separate broad search",
            "requested_role": "initial",
            "source_obligation_candidate_ids": ["obligation:1:general"],
        }
    )

    kernel, convergence = _converge(payload)
    _, admission = _admit(kernel, convergence)

    assert admission.current_queries == ["Example required component 1 primary source"]
    assert len(admission.initial_query_admission.unjustified_secondary_candidates_rejected) == 1


def test_policy_is_versioned_tunable_and_not_a_schema_contract() -> None:
    policy = DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY
    tuned = policy.with_tuning(
        initial_candidate_ceiling_per_required_component=3,
        recon_candidate_ceiling_per_affected_component=4,
    )

    assert policy.policy_version == INITIAL_QUERY_ALLOCATION_POLICY_VERSION
    assert policy.primary_query_target_per_required_component == 1
    assert policy.initial_candidate_ceiling_per_required_component == 2
    assert policy.immediate_dispatch_target_per_required_component == 1
    assert policy.recon_candidate_ceiling_per_affected_component == 5
    assert tuned.policy_version == policy.policy_version
    assert tuned.initial_candidate_ceiling_per_required_component == 3
    assert SEARCH_PLANNER_SCHEMA_VERSION not in tuned.to_dict().values()
    scout_source = SCOUT_RUNTIME.read_text(encoding="utf-8")
    assert "DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY" in scout_source
    assert "SCOUT_MAX_QUERIES_PER_COMPONENT = 5" not in scout_source
    with pytest.raises(ValueError, match="positive integer"):
        policy.with_tuning(initial_candidate_ceiling_per_required_component=2.5)


def test_recon_ceiling_is_per_affected_component_and_fails_explicitly() -> None:
    payload = _planner_payload(recon="optional")
    recon = payload["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0]["recon_requirement"]
    recon["unresolved_dimension_ids"] = [f"dim:need-{index}" for index in range(6)]
    recon["candidate_queries"] = [
        {
            "dimension_id": dimension_id,
            "candidate_query_text": f"Example clarification {dimension_id}",
            "query_kind": "disambiguation_probe",
        }
        for dimension_id in recon["unresolved_dimension_ids"]
    ]

    with pytest.raises(
        QueryStrategyConvergenceError,
        match="per-affected-component recon ceiling",
    ):
        _converge(payload)


def test_planner_provider_identity_is_ignored_before_queryplan() -> None:
    kernel, convergence = _converge(_planner_payload(planner_provider_name="untrusted-provider"))
    strategy = convergence.query_production_result.candidate_strategies[0]
    _, admission = _admit(kernel, convergence)

    assert "provider_name" not in strategy
    assert strategy["planner_provider_identity_ignored"] is True
    assert admission.current_queries == ["Example required component 1 primary source"]
    assert (
        admission.observation.payload["provider_job_execution_handoff"]["behavior_boundary_flags"]["provider_selected"]
        is False
    )


def test_optional_recon_unavailable_retains_conservative_primary() -> None:
    kernel, convergence = _converge(_planner_payload(recon="optional"))
    _, admission = _admit(kernel, convergence)

    assert convergence.recon_summary[0]["status"] == ("optional_unavailable_primary_strategy_retained")
    assert kernel.state.scout_disambiguation_report_state == {}
    assert len(admission.current_queries) == 1


def _semantic_primary_secondary_recon_proposal(
    *,
    posture: str,
    dimensions: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "interpretation": (
            "Resolve Example identity before answering the official filing threshold."
        ),
        "components": [
            {
                "purpose": "user_facing_answer_target",
                "label": "Official threshold",
                "question": (
                    "What is the official current filing threshold for the requested program?"
                ),
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "state the threshold",
                    "bind the answer to an official current source",
                ],
                "support_kinds": ["direct"],
                "materiality": "material",
                "slots": [
                    {
                        "kind": "entity",
                        "status": "explicit",
                        "selected_value": "Example Permit",
                        "materiality": "material",
                    }
                ],
                "source": {"kind": "official_current", "strictness": "required"},
                "search": {
                    "summary": "Find the official current source for the threshold.",
                    "preferred_source_kinds": ["official"],
                    "primary_query": {
                        "text": "Example Permit official filing threshold 2026",
                        "role": "official_bias",
                    },
                    "secondary_query": {
                        "text": "Example Permit official filing threshold 2026 site:gov",
                        "role": "canonical_bias",
                        "justification": (
                            "Secondary canonical-domain probe remains distinct from "
                            "the primary official threshold query."
                        ),
                    },
                    "recon": {
                        "posture": posture,
                        "dimensions": dimensions,
                    },
                },
            }
        ],
        "material_ambiguity": "directional_recon_optional",
    }


def test_semantic_primary_secondary_one_recon_aggregates_to_single_component_workload() -> None:
    rich = accept_planner_model_output(
        _semantic_primary_secondary_recon_proposal(
            posture="optional",
            dimensions=[
                {
                    "kind": "entity_identity",
                    "query": "Old Example New Example identity",
                }
            ],
        )
    )
    strategies = rich["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ]
    assert len(strategies) == 2
    work = _recon_work_by_component(
        strategies,
        policy=DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    )
    component_id = rich["answer_components"][0]["component_id"]
    assert set(work) == {component_id}
    component_work = work[component_id]
    assert component_work["posture"] == "optional"
    assert component_work["unresolved_dimension_ids"] == [
        "dimension:01:01:entity_identity"
    ]
    assert component_work["candidate_queries"] == [
        {
            "dimension_id": "dimension:01:01:entity_identity",
            "candidate_query_text": "Old Example New Example identity",
            "query_kind": "all_time",
        }
    ]

    kernel, convergence = _converge(rich)
    assert convergence.recon_summary[0]["status"] == (
        "optional_unavailable_primary_strategy_retained"
    )
    assert len(convergence.recon_summary) == 1


def test_semantic_primary_secondary_two_distinct_recon_dimensions_are_preserved() -> None:
    rich = accept_planner_model_output(
        _semantic_primary_secondary_recon_proposal(
            posture="optional",
            dimensions=[
                {
                    "kind": "entity_identity",
                    "query": "Old Example New Example identity",
                },
                {
                    "kind": "time_version_currentness",
                    "query": "Example Permit current 2026 threshold version",
                },
            ],
        )
    )
    strategies = rich["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ]
    work = _recon_work_by_component(
        strategies,
        policy=DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY,
    )
    component_id = rich["answer_components"][0]["component_id"]
    component_work = work[component_id]
    assert component_work["unresolved_dimension_ids"] == [
        "dimension:01:01:entity_identity",
        "dimension:01:02:time_version_currentness",
    ]
    assert component_work["candidate_queries"] == [
        {
            "dimension_id": "dimension:01:01:entity_identity",
            "candidate_query_text": "Old Example New Example identity",
            "query_kind": "all_time",
        },
        {
            "dimension_id": "dimension:01:02:time_version_currentness",
            "candidate_query_text": "Example Permit current 2026 threshold version",
            "query_kind": "recent_current",
        },
    ]
    kernel, convergence = _converge(rich)
    assert convergence.recon_summary[0]["status"] == (
        "optional_unavailable_primary_strategy_retained"
    )


def test_required_identity_recon_without_adapter_fails_before_query_production() -> None:
    kernel = _kernel_after_run_contract()

    with pytest.raises(QueryStrategyConvergenceError, match="requires Scout identity"):
        execute_initial_query_strategy_convergence(
            run_kernel=kernel,
            router_query_preparation_contract=_router_state(),
            query="Compare every required Example component.",
            strategy="Balanced",
            current_date="2026-07-19",
            focus_academic=False,
            force_intent_news=False,
            include_domains=[],
            exclude_domains=[],
            news_preferred_domains=[],
            route_projection={},
            run_contract_projection=kernel.state.run_contract_projection,
            planner_adapter=ResponseOnlyPlannerAdapter(
                _planner_payload(
                    recon="required",
                    required_recon=True,
                )
            ),
            provider_diagnostics=[],
        )

    assert QUERY_PRODUCTION_STAGE not in kernel.state.projections
    assert kernel.state.search_work_plan == {}



def test_required_recon_route_unavailable_fails_closed_after_scout_authorization() -> None:
    revision = ResponseOnlyRevisionAdapter()
    search_calls: list[dict[str, Any]] = []

    def blocked_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        raise AssertionError("an unavailable Scout route must not dispatch")

    blocked_scout = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": False},
        scout_search=blocked_search,
    )
    kernel = _kernel_after_run_contract()

    with pytest.raises(QueryStrategyConvergenceError) as captured:
        _converge(
            _planner_payload(recon="required", required_recon=True),
            scout_adapter=blocked_scout,
            revision_adapter=revision,
            run_kernel=kernel,
        )

    assert (
        captured.value.failure_code
        is QueryStrategyConvergenceFailureCode.REQUIRED_SCOUT_ROUTE_UNAVAILABLE
    )
    assert revision.calls == []
    assert search_calls == []
    report = kernel.state.scout_disambiguation_report_projection
    assert report["route_available"] is False
    assert report["executed_query_count"] == 0


def test_optional_recon_route_unavailable_retains_primary_without_revision() -> None:
    revision = ResponseOnlyRevisionAdapter()
    kernel, convergence = _converge(
        _planner_payload(recon="optional"),
        scout_adapter=OrdinaryScoutDisambiguationAdapter(
            available_providers={"serper": False}
        ),
        revision_adapter=revision,
    )

    assert revision.calls == []
    assert convergence.recon_summary[0]["status"] == (
        "optional_route_unavailable_primary_strategy_retained"
    )
    assert kernel.state.scout_disambiguation_report_projection["route_available"] is False


def test_required_recon_empty_executed_scout_fails_closed_without_revision() -> None:
    revision = ResponseOnlyRevisionAdapter()
    search_calls: list[dict[str, Any]] = []

    def empty_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        return []

    empty_scout = OrdinaryScoutDisambiguationAdapter(
        available_providers={"serper": True},
        scout_search=empty_search,
    )
    kernel = _kernel_after_run_contract()

    with pytest.raises(QueryStrategyConvergenceError) as captured:
        _converge(
            _planner_payload(recon="required", required_recon=True),
            scout_adapter=empty_scout,
            revision_adapter=revision,
            run_kernel=kernel,
        )

    assert (
        captured.value.failure_code
        is QueryStrategyConvergenceFailureCode.REQUIRED_SCOUT_EXECUTION_EMPTY
    )
    assert revision.calls == []
    assert len(search_calls) == 1
    assert search_calls[0]["strict_failure"] is True
    report = kernel.state.scout_disambiguation_report_projection
    assert report["route_available"] is True
    assert report["scout_execution_posture"] == "executed"
    assert report["executed_query_count"] == 1
    assert report["live_provider_calls_executed"] is True
    for key in (
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "fetch_read_retrieval_behavior_changed",
    ):
        assert report[key] is False
    assert kernel.state.evidence_ledger.to_projection().to_dict().get("evidence_items", []) == []


def test_required_recon_provider_failure_uses_safe_scout_runtime_corridor() -> None:
    revision = ResponseOnlyRevisionAdapter()
    search_calls: list[dict[str, Any]] = []
    kernel = _kernel_after_run_contract()

    def failing_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        raise RuntimeError("private-provider-detail")

    with pytest.raises(InitialQueryStrategyFailureError) as captured:
        _converge(
            _planner_payload(recon="required", required_recon=True),
            scout_adapter=OrdinaryScoutDisambiguationAdapter(
                available_providers={"serper": True},
                scout_search=failing_search,
            ),
            revision_adapter=revision,
            run_kernel=kernel,
        )

    terminal = captured.value.to_terminal_projection()
    assert terminal["failure_origin"] == "scout_disambiguation_runtime"
    assert terminal["failure_code"] == "scout_disambiguation_runtime_error"
    assert "private-provider-detail" not in str(captured.value)
    assert "private-provider-detail" not in json.dumps(terminal, sort_keys=True)
    assert "required_scout_execution_empty" not in terminal.values()
    assert "required_scout_route_unavailable" not in terminal.values()
    assert len(search_calls) == 1
    assert search_calls[0]["strict_failure"] is True
    assert revision.calls == []
    assert kernel.state.scout_disambiguation_report_state == {}
    assert kernel.state.scout_disambiguation_report_projection == {}
    assert kernel.state.scout_disambiguation_report_history == []
    assert QUERY_PRODUCTION_STAGE not in kernel.state.projections
    assert kernel.state.search_work_plan == {}
    assert kernel.state.current_answer_contract == {}
    assert kernel.state.evidence_ledger.to_projection().to_dict().get("evidence_items", []) == []


def test_required_recon_projects_exact_plannerrevision_owner_code() -> None:
    private_detail = "offline-revision-private-detail"

    class FailingRevisionAdapter:
        def produce(self, _revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
            raise SearchPlannerRevisionRuntimeError(
                private_detail,
                failure_code=(
                    SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_JSON
                ),
            )

    with pytest.raises(InitialQueryStrategyFailureError) as captured:
        _converge(
            _planner_payload(recon="required", required_recon=True),
            scout_adapter=ResponseOnlyScoutAdapter(),
            revision_adapter=FailingRevisionAdapter(),
        )

    terminal = captured.value.to_terminal_projection()
    assert terminal == {
        "schema_version": "initial_query_strategy_failure_v1",
        "boundary": "initial_query_strategy",
        "failure_origin": "search_planner_revision_runtime",
        "failure_code": "model_output_invalid_json",
    }
    assert private_detail not in json.dumps(terminal, sort_keys=True)


def test_required_recon_cap_terminal_propagates_unchanged_without_revision() -> None:
    revision = ResponseOnlyRevisionAdapter()
    search_calls: list[dict[str, Any]] = []
    terminal = RunCapExceeded(
        "search_attempt_cap",
        family=ExternalCallFamily.SEARCH,
    )
    kernel = _kernel_after_run_contract()

    def exhausted_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(dict(kwargs))
        raise terminal

    with pytest.raises(RunCapExceeded) as captured:
        _converge(
            _planner_payload(recon="required", required_recon=True),
            scout_adapter=OrdinaryScoutDisambiguationAdapter(
                available_providers={"serper": True},
                scout_search=exhausted_search,
            ),
            revision_adapter=revision,
            run_kernel=kernel,
        )

    assert captured.value is terminal
    assert len(search_calls) == 1
    assert revision.calls == []
    assert kernel.state.scout_disambiguation_report_projection == {}


def test_required_recon_posture_alone_fails_closed_without_adapter() -> None:
    kernel = _kernel_after_run_contract()

    with pytest.raises(QueryStrategyConvergenceError, match="requires Scout identity"):
        execute_initial_query_strategy_convergence(
            run_kernel=kernel,
            router_query_preparation_contract=_router_state(),
            query="Compare every required Example component.",
            strategy="Balanced",
            current_date="2026-07-19",
            focus_academic=False,
            force_intent_news=False,
            include_domains=[],
            exclude_domains=[],
            news_preferred_domains=[],
            route_projection={},
            run_contract_projection=kernel.state.run_contract_projection,
            planner_adapter=ResponseOnlyPlannerAdapter(_planner_payload(recon="required", required_recon=False)),
            provider_diagnostics=[],
        )

    assert QUERY_PRODUCTION_STAGE not in kernel.state.projections


def test_injected_recon_revises_query_direction_and_remains_non_evidence() -> None:
    scout = ResponseOnlyScoutAdapter()
    revision = ResponseOnlyRevisionAdapter()
    kernel, convergence = _converge(
        _planner_payload(recon="optional"),
        scout_adapter=scout,
        revision_adapter=revision,
    )
    _, admission = _admit(kernel, convergence)

    assert scout.calls and revision.calls
    directional = revision.calls[0]["scout_directional_context"]
    assert directional["non_evidence"] is True
    assert directional["scout_hints_are_evidence"] is False
    assert directional["evidence_admitted"] is False
    assert directional["citation_eligible"] is False
    assert directional["directional_hints"]
    assert "snippet" not in directional["directional_hints"][0]
    assert "link" not in directional["directional_hints"][0]
    assert convergence.query_production_result.candidate_queries == ["Renamed Example official current component 1"]
    assert admission.current_queries == ["Renamed Example official current component 1"]
    assert convergence.recon_summary[0]["status"] == "query_direction_revised"
    revision_projection = convergence.revision_projections[0]
    assert revision_projection["revision_effect_class"] == ("query_direction_only_non_contractual")
    assert revision_projection["answer_contract_mutated"] is False
    assert kernel.state.current_answer_contract == {}
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    assert ledger.get("evidence_items", []) == []
    assert convergence.recon_summary[0]["evidence_admitted"] is False
    assert convergence.recon_summary[0]["citation_eligible"] is False


def test_contractual_revision_is_admitted_and_applied_before_planning_use() -> None:
    kernel, convergence = _converge(
        _planner_payload(recon="optional"),
        scout_adapter=ResponseOnlyScoutAdapter(),
        revision_adapter=ResponseOnlyRevisionAdapter(amendment=True),
    )
    revision = convergence.revision_projections[0]

    assert revision["revision_effect_class"] == ("contractual_admitted_and_applied")
    assert revision["contractual_effect_admitted_and_applied"] is True
    assert revision["answer_contract_mutated"] is True
    assert kernel.state.contract_amendment_admission_history
    assert kernel.state.contract_amendment_application_history
    assert kernel.state.current_answer_contract
    assert (
        convergence.search_work_plan["metadata"]["accepted_contract_ref"]["contract_digest"]
        == kernel.state.current_answer_contract["accepted_contract_digest"]
    )


def test_pending_contractual_revision_cannot_change_query_direction() -> None:
    kernel, convergence = _converge(_planner_payload())
    pending = {
        "component_id": "component:1",
        "revision_id": "revision:pending",
        "revision_digest": "d" * 64,
        "revision_effect_class": "contractual_pending_admission",
        "query_direction_authorized_for_planning": False,
        "contractual_effect_admitted_and_applied": False,
        "component_search_requirement_updates": [
            {
                "component_id": "component:1",
                "requirement_id": "requirement:pending",
            }
        ],
    }

    with pytest.raises(QueryStrategyConvergenceError, match="before its contractual"):
        _strategies_with_authorized_revisions(
            base_strategies=(convergence.query_production_result.candidate_strategies),
            revision_projections=[pending],
            accepted_contract=kernel.state.initial_answer_contract,
        )


def test_malformed_planner_has_no_dispatch_and_no_legacy_fallback() -> None:
    kernel = _kernel_after_run_contract()

    with pytest.raises(ValueError):
        execute_initial_query_strategy_convergence(
            run_kernel=kernel,
            router_query_preparation_contract=_router_state(),
            query="Compare every required Example component.",
            strategy="Balanced",
            current_date="2026-07-19",
            focus_academic=False,
            force_intent_news=False,
            include_domains=[],
            exclude_domains=[],
            news_preferred_domains=[],
            route_projection={},
            run_contract_projection=kernel.state.run_contract_projection,
            planner_adapter=ResponseOnlyPlannerAdapter({}),
            provider_diagnostics=[],
        )

    assert QUERY_PRODUCTION_STAGE not in kernel.state.projections
    runtime_source = QUERY_RUNTIME.read_text(encoding="utf-8")
    assert "def _build_researcher_prompt" not in runtime_source
    assert "def _build_recon_rewriter_prompt" not in runtime_source
    assert "brave_reconnaissance_func" not in runtime_source
    assert "core_topic[:300]" not in runtime_source


def test_ordinary_pipeline_consumes_convergence_before_queryplan_and_discover() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    convergence_index = source.index("execute_initial_query_strategy_convergence(")
    admission_index = source.index("execute_query_plan_admission_action(")
    execution_index = source.index("current_queries = query_authority.admit_execution_queries")

    assert convergence_index < admission_index < execution_index
    assert "run_search_work_shadow_lane(" not in source
    assert "execute_query_production_action(" not in source
    assert "search_work_projection=run_kernel.state.search_work_plan" in source
