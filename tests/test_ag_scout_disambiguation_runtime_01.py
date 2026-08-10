from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.cap_enforcement import ExternalCallFamily, RunCapExceeded
from core.run_kernel import (
    SCOUT_DISAMBIGUATION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.scout_disambiguation_runtime import (
    SCOUT_DISAMBIGUATION_REPORT_OWNER,
    SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION,
    ScoutDisambiguationInput,
    ScoutDisambiguationRuntimeError,
    build_scout_disambiguation_report_payload,
    contract_ref_from_contract,
    execute_scout_disambiguation_action,
    planner_ref_from_search_planner_state,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "scout_disambiguation_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "roadmap" / "SEARCHOS_QUERY_STRATEGY_AND_RECON_CONVERGENCE_01.md",
)

RUN_ID = "run:ag-scout-disambiguation-runtime-01"
REQUEST_ID = "request:ag-scout-disambiguation-runtime-01"
QUERY = "What is the current official Example Permit threshold in 2026?"


class DeterministicPlannerAdapter:
    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_result()


class FakeScoutAdapter:
    def __init__(self, result: Mapping[str, Any] | None = None) -> None:
        self.result = dict(result or _scout_result())
        self.calls: list[dict[str, Any]] = []

    def produce(self, scout_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(dict(scout_input))
        return deepcopy(self.result)


def _planner_result() -> dict[str, Any]:
    return {
        "question_meaning_summary": (
            "Determine the official current threshold while preserving material "
            "identity and jurisdiction ambiguity."
        ),
        "requested_output": "Concise answer with official-current source support.",
        "semantic_slots": [
            {
                "slot_id": "slot:program",
                "slot_kind": "entity",
                "status": "ambiguous",
                "candidate_values": ["Example Permit", "Example Permit Renewal"],
                "materiality": "material",
                "user_confirmation_required": True,
            },
            {
                "slot_id": "slot:jurisdiction",
                "slot_kind": "jurisdiction",
                "status": "unresolved",
                "candidate_values": ["State A", "State B"],
                "materiality": "material",
                "user_confirmation_required": True,
            },
            {
                "slot_id": "slot:time-period",
                "slot_kind": "time_period",
                "status": "explicit",
                "selected_value": "2026",
                "materiality": "material",
            },
        ],
        "answer_components": [
            {
                "component_id": "component:official-threshold",
                "component_revision": "1",
                "user_facing_label": "Official threshold",
                "user_facing_question": (
                    "What is the official current filing threshold for the "
                    "requested program?"
                ),
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "identify the likely program and jurisdiction",
                    "preserve official-current source obligations",
                ],
                "semantic_slot_ids": [
                    "slot:program",
                    "slot:jurisdiction",
                    "slot:time-period",
                ],
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": ["Keep ambiguity visible until resolved."],
                "prohibited_upgrades": ["Do not cite Scout hints as evidence."],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": "obligation:official-current",
                "obligation_kind": "official_current_source",
                "component_candidate_ids": ["component:official-threshold"],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": "component:official-threshold",
                "requirement_id": "searchreq:official-current-threshold",
                "requirement_summary": "Find the official current threshold source.",
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "preferred_source_kinds": ["official"],
                "recency_requirement": "current for 2026",
            }
        ],
        "material_ambiguity_posture": "material_ambiguity_present",
        "mandatory_caveats": ["Scout may only produce direction hints."],
        "prohibited_upgrades": ["Do not infer final answer from snippets."],
        "normalization_obligations": ["Normalize the effective year to 2026."],
        "assumptions": [],
        "unsupported_outputs": ["No final answer is produced by the planner."],
    }


def _kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _planner_input(kernel: RunKernel) -> SearchPlannerInput:
    return SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text=QUERY,
        requested_mode="balanced",
        safe_context={"source_policy": "official-current"},
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )


def _produce_planner(kernel: RunKernel) -> Mapping[str, Any]:
    planner_input = _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=DeterministicPlannerAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)
    return kernel.state.search_planner_proposal_projection["question_meaning_record"]


def _accept_planner_qmr(kernel: RunKernel, qmr_payload: Mapping[str, Any]) -> None:
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr_payload["record_id"]),
        parent_proposal_digest=str(qmr_payload["record_digest"]),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        status=RunStageStatus.COMPLETED,
        payload={"question_meaning_record": dict(qmr_payload)},
    )
    kernel.reduce(observation)


def _dimensions(count: int = 2) -> list[dict[str, Any]]:
    base = [
        {
            "dimension_id": "dim:entity",
            "dimension_kind": "entity_identity",
            "summary": "Which Example Permit identity is likely?",
            "related_semantic_slot_ids": ["slot:program"],
            "priority": 1,
            "status": "open",
            "materiality": "material",
        },
        {
            "dimension_id": "dim:jurisdiction",
            "dimension_kind": "jurisdiction",
            "summary": "Which jurisdiction is likely?",
            "related_semantic_slot_ids": ["slot:jurisdiction"],
            "priority": 2,
            "status": "open",
            "materiality": "material",
        },
        {
            "dimension_id": "dim:currentness",
            "dimension_kind": "time_version_currentness",
            "summary": "Whether current means 2026-effective or most recent.",
            "related_semantic_slot_ids": ["slot:time-period"],
            "priority": 3,
            "status": "open",
            "materiality": "material",
        },
        {
            "dimension_id": "dim:alias",
            "dimension_kind": "rename_alias",
            "summary": "Whether the permit was renamed.",
            "related_semantic_slot_ids": ["slot:program"],
            "priority": 4,
            "status": "open",
            "materiality": "material",
        },
        {
            "dimension_id": "dim:official",
            "dimension_kind": "official_target_direction",
            "summary": "Which official target is likely.",
            "related_semantic_slot_ids": ["slot:program"],
            "priority": 5,
            "status": "open",
            "materiality": "material",
        },
    ]
    if count <= len(base):
        return deepcopy(base[:count])
    out = deepcopy(base)
    out.append(
        {
            "dimension_id": "dim:extra",
            "dimension_kind": "unknown_or_other",
            "summary": "Extra dimension that exceeds the cap.",
            "related_semantic_slot_ids": ["slot:program"],
            "priority": 6,
            "status": "open",
            "materiality": "material",
        }
    )
    return out


def _scout_input(
    kernel: RunKernel,
    *,
    dimensions: list[dict[str, Any]] | None = None,
    parent_ref: Mapping[str, Any] | None = None,
    initial_ref: Mapping[str, Any] | None = None,
    current_ref: Mapping[str, Any] | None = None,
    query_budget: Mapping[str, Any] | None = None,
) -> ScoutDisambiguationInput:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    component = qmr["answer_components"][0]
    dims = dimensions or _dimensions()
    return ScoutDisambiguationInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        parent_search_planner_proposal_ref=(
            parent_ref
            or planner_ref_from_search_planner_state(
                kernel.state.search_planner_proposal_state
            )
        ),
        parent_initial_contract_ref=(
            initial_ref
            if initial_ref is not None
            else contract_ref_from_contract(
                kernel.state.initial_answer_contract,
                source="initial_answer_contract",
            )
        ),
        parent_current_contract_ref=(
            current_ref
            if current_ref is not None
            else contract_ref_from_contract(
                kernel.state.current_answer_contract,
                source="current_answer_contract",
            )
        ),
        component_id=component["component_id"],
        answer_component_ref={
            "component_id": component["component_id"],
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "user_facing_label": component["user_facing_label"],
        },
        ambiguity_dimensions=dims,
        query_budget=dict(query_budget or {}),
        candidate_queries=[
            {
                "query_id": "scout-query:official",
                "safe_query_text": "Example Permit official 2026 threshold",
                "query_kind": "official_domain_probe",
                "priority": 1,
                "related_dimension_ids": [dims[0]["dimension_id"]],
            },
            {
                "query_id": "scout-query:recent",
                "safe_query_text": "Example Permit current threshold 2026",
                "query_kind": "recent_current",
                "priority": 2,
                "related_dimension_ids": [dims[-1]["dimension_id"]],
            },
        ],
        safe_context={"adapter_policy": "fake-injected-only"},
    )


def _authorize_scout(
    kernel: RunKernel,
    scout_input: ScoutDisambiguationInput,
    *,
    max_queries_per_component: int = 5,
    max_dimensions_per_component: int = 5,
):
    return kernel.authorize_scout_disambiguation(
        component_id=scout_input.component_id,
        ambiguity_dimension_ids=[
            item["dimension_id"] for item in scout_input.ambiguity_dimensions
        ],
        max_queries_per_component=max_queries_per_component,
        max_dimensions_per_component=max_dimensions_per_component,
    )


def _reduce_scout(
    kernel: RunKernel,
    *,
    scout_input: ScoutDisambiguationInput | None = None,
    adapter: FakeScoutAdapter | None = None,
):
    input_ = scout_input or _scout_input(kernel)
    action = _authorize_scout(kernel, input_)
    result = execute_scout_disambiguation_action(
        action=action,
        scout_input=input_,
        adapter=adapter or FakeScoutAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)
    return action, result.observation_payload


def _scout_result(
    *,
    queries: list[dict[str, Any]] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scout_queries": queries
        or [
            {
                "query_id": "scout-query:official",
                "safe_query_text": "Example Permit official 2026 threshold",
                "query_kind": "official_domain_probe",
                "priority": 1,
                "related_dimension_ids": ["dim:entity"],
                "execution_status": "executed_by_fake_adapter",
                "search_vertical": "search",
                "provider_hint": "serper",
                "not_live": True,
                "provider_payload_retained": False,
            }
        ],
        "organic_results": [
            {
                "query_id": "scout-query:official",
                "related_dimension_ids": ["dim:entity"],
                "title": "Example Permit - Official Threshold",
                "link": "https://official.example.gov/permit/threshold",
                "snippet": "Official current threshold information.",
                "position": 1,
                "date": "2026-01-01",
                "source": "Official Example",
                "attributes": {"Agency": "Example Department"},
                "sitelinks": [
                    {
                        "title": "Threshold table",
                        "link": "https://official.example.gov/permit/table",
                    }
                ],
                "official_target_hint": "Likely official permit threshold page.",
            }
        ],
        "candidate_interpretations": [
            {
                "interpretation_id": "interp:official-permit",
                "summary": "The user likely means Example Permit.",
                "related_dimension_ids": ["dim:entity"],
                "supporting_hint_ids": ["hint:scout-query:official:organic:1"],
            }
        ],
        "recommended_planner_revision_inputs": {
            "resolved_candidate_interpretations": ["interp:official-permit"],
            "unresolved_ambiguity_dimensions": ["dim:jurisdiction"],
            "suggested_slot_updates": [
                {"slot_id": "slot:program", "candidate_value": "Example Permit"}
            ],
            "suggested_component_search_requirement_adjustments": [],
            "suggested_source_obligation_focus": ["official_current_source"],
            "suggested_caveats": ["Jurisdiction remains unresolved."],
            "candidate_official_target_hints": [
                {"domain": "official.example.gov", "hint_id": "official:1"}
            ],
        },
        "unresolved_ambiguities": [
            {
                "unresolved_id": "unresolved:jurisdiction",
                "summary": "Jurisdiction still needs planner handling.",
                "related_dimension_ids": ["dim:jurisdiction"],
            }
        ],
        "confidence_posture": "directional",
        "disambiguation_posture": "partially_resolved_report_only",
    }
    if extra:
        payload.update(extra)
    return payload


def _six_executed_queries() -> list[dict[str, Any]]:
    return [
        {
            "query_id": f"scout-query:{index}",
            "safe_query_text": f"Example Permit probe {index}",
            "query_kind": "all_time",
            "priority": index,
            "related_dimension_ids": ["dim:entity"],
            "execution_status": "executed_by_fake_adapter",
            "search_vertical": "search",
            "provider_hint": "serper",
            "not_live": True,
            "provider_payload_retained": False,
        }
        for index in range(1, 7)
    ]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_text(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_scout_disambiguation_requires_adapter_and_fails_closed_without_one() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = _authorize_scout(kernel, scout_input)

    with pytest.raises(ScoutDisambiguationRuntimeError, match="injected adapter"):
        execute_scout_disambiguation_action(action=action, scout_input=scout_input)

    assert kernel.state.scout_disambiguation_report_state == {}
    assert kernel.state.scout_disambiguation_report_projection == {}
    assert kernel.state.scout_disambiguation_report_history == []


def test_unexpected_scout_adapter_failure_is_wrapped_without_raw_detail() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = _authorize_scout(kernel, scout_input)

    def failing_adapter(_: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RuntimeError("private-provider-detail")

    with pytest.raises(ScoutDisambiguationRuntimeError) as captured:
        execute_scout_disambiguation_action(
            action=action,
            scout_input=scout_input,
            adapter=failing_adapter,
        )

    assert str(captured.value) == "Scout disambiguation adapter failed closed"
    assert "private-provider-detail" not in str(captured.value)
    assert kernel.state.scout_disambiguation_report_state == {}
    assert kernel.state.scout_disambiguation_report_projection == {}
    assert kernel.state.scout_disambiguation_report_history == []


def test_scout_adapter_cap_terminal_propagates_unchanged() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = _authorize_scout(kernel, scout_input)
    terminal = RunCapExceeded(
        "search_attempt_cap",
        family=ExternalCallFamily.SEARCH,
    )

    def exhausted_adapter(_: Mapping[str, Any]) -> Mapping[str, Any]:
        raise terminal

    with pytest.raises(RunCapExceeded) as captured:
        execute_scout_disambiguation_action(
            action=action,
            scout_input=scout_input,
            adapter=exhausted_adapter,
        )

    assert captured.value is terminal
    assert kernel.state.scout_disambiguation_report_projection == {}


def test_scout_disambiguation_report_reduces_to_run_kernel_state_projection_history() -> None:
    kernel = _kernel()
    _produce_planner(kernel)

    action, _payload = _reduce_scout(kernel)

    state = kernel.state.scout_disambiguation_report_state
    projection = kernel.state.scout_disambiguation_report_projection
    assert state["owner"] == SCOUT_DISAMBIGUATION_REPORT_OWNER
    assert state["schema_version"] == SCOUT_DISAMBIGUATION_REPORT_SCHEMA_VERSION
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"] == action.action_id
    assert state["report_digest"]
    assert state["parent_search_planner_proposal_ref"]["proposal_digest"]
    assert state["component_id"] == "component:official-threshold"
    assert state["query_budget"]["max_queries_per_component"] == 5
    assert state["query_budget"]["executed_query_count"] == 1
    assert all(value is False for value in state["closed_surface_flags"].values())
    assert projection["report_digest"] == state["report_digest"]
    assert kernel.state.scout_disambiguation_report_history[-1] == projection
    assert kernel.state.projections[SCOUT_DISAMBIGUATION_STAGE] == projection



def test_scout_report_truthfully_projects_ordinary_live_execution() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    live_query = deepcopy(_scout_result()["scout_queries"][0])
    live_query["execution_status"] = "executed"
    live_query["not_live"] = False

    _reduce_scout(
        kernel,
        adapter=FakeScoutAdapter(
            _scout_result(
                queries=[live_query],
                extra={
                    "scout_execution_posture": "executed",
                    "route_available": True,
                },
            )
        ),
    )

    report = kernel.state.scout_disambiguation_report_state
    assert report["scout_execution_posture"] == "executed"
    assert report["route_available"] is True
    assert report["live_provider_calls_executed"] is True
    assert report["scout_queries"][0]["execution_status"] == "executed"
    assert report["scout_queries"][0]["not_live"] is False
    assert "live_provider_calls_executed" not in report["closed_surface_flags"]
    assert report["evidence_admitted"] is False
    assert report["citation_eligible"] is False




def test_scout_report_rejects_execution_posture_that_hides_executed_work() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    live_query = deepcopy(_scout_result()["scout_queries"][0])
    live_query["execution_status"] = "executed"
    live_query["not_live"] = False

    with pytest.raises(RunKernelTransitionError, match="omits executed query work"):
        _reduce_scout(
            kernel,
            adapter=FakeScoutAdapter(
                _scout_result(
                    queries=[live_query],
                    extra={"scout_execution_posture": "deferred"},
                )
            ),
        )


def test_scout_report_binds_to_parent_planner_proposal_and_qmr() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = _authorize_scout(kernel, scout_input)
    payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(),
        scout_input=scout_input.to_adapter_payload(),
        authorized_action_id=action.action_id,
    )

    report_ref = payload["disambiguation_report"]["parent_search_planner_proposal_ref"]
    assert report_ref["proposal_id"]
    assert report_ref["proposal_digest"]
    assert report_ref["question_meaning_record_id"]
    assert report_ref["question_meaning_record_digest"]

    stale_parent = deepcopy(scout_input.to_adapter_payload())
    stale_parent["parent_search_planner_proposal_ref"]["proposal_digest"] = "stale"
    stale_payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(),
        scout_input=stale_parent,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=stale_payload,
    )
    with pytest.raises(RunKernelTransitionError, match="stale parent planner"):
        kernel.reduce(observation)

    qmr_kernel = _kernel()
    _produce_planner(qmr_kernel)
    qmr_input = _scout_input(qmr_kernel)
    qmr_action = _authorize_scout(qmr_kernel, qmr_input)
    stale_qmr = deepcopy(qmr_input.to_adapter_payload())
    stale_qmr["parent_search_planner_proposal_ref"][
        "question_meaning_record_digest"
    ] = "stale-qmr"
    qmr_payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(),
        scout_input=stale_qmr,
        authorized_action_id=qmr_action.action_id,
    )
    qmr_observation = Observation.from_action(
        qmr_action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=qmr_payload,
    )
    with pytest.raises(RunKernelTransitionError, match="stale parent planner"):
        qmr_kernel.reduce(qmr_observation)


def test_scout_report_rejects_stale_initial_or_current_contract_digest() -> None:
    kernel = _kernel()
    qmr = _produce_planner(kernel)
    _accept_planner_qmr(kernel, qmr)
    stale_ref = contract_ref_from_contract(
        kernel.state.initial_answer_contract,
        source="initial_answer_contract",
    )
    stale_ref["contract_digest"] = "stale-contract"
    scout_input = _scout_input(kernel, initial_ref=stale_ref)
    action = kernel.authorize_scout_disambiguation(
        component_id=scout_input.component_id,
        ambiguity_dimension_ids=[
            item["dimension_id"] for item in scout_input.ambiguity_dimensions
        ],
    )
    payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(),
        scout_input=scout_input.to_adapter_payload(),
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="stale parent digest"):
        kernel.reduce(observation)


def test_scout_report_rejects_duplicate_context() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    _reduce_scout(kernel, scout_input=scout_input)

    action = _authorize_scout(kernel, scout_input)
    result = execute_scout_disambiguation_action(
        action=action,
        scout_input=scout_input,
        adapter=FakeScoutAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )

    with pytest.raises(RunKernelTransitionError, match="duplicate Scout"):
        kernel.reduce(observation)


def test_scout_query_budget_cap_enforced() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = _authorize_scout(kernel, scout_input)
    payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(queries=_six_executed_queries()),
        scout_input=scout_input.to_adapter_payload(),
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(
        RunKernelTransitionError,
        match="executed query count exceeds authorized budget",
    ):
        kernel.reduce(observation)

    valid_kernel = _kernel()
    _produce_planner(valid_kernel)
    queries = [
        deepcopy(_six_executed_queries()[0]),
        {
            "query_id": "scout-query:skipped",
            "safe_query_text": "Example Permit extra current probe",
            "query_kind": "recent_current",
            "priority": 2,
            "related_dimension_ids": ["dim:jurisdiction"],
            "execution_status": "skipped_budget",
            "not_live": True,
            "provider_payload_retained": False,
        },
    ]
    _reduce_scout(
        valid_kernel,
        adapter=FakeScoutAdapter(_scout_result(queries=queries, extra={"organic_results": []})),
    )
    report = valid_kernel.state.scout_disambiguation_report_projection
    assert report["query_budget"]["executed_query_count"] == 1
    assert report["query_budget"]["skipped_query_count"] == 1
    assert report["non_executed_candidate_queries"][0]["query_id"] == (
        "scout-query:skipped"
    )


def test_scout_query_budget_cannot_exceed_action_binding() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(kernel)
    action = kernel.authorize_scout_disambiguation(
        component_id=scout_input.component_id,
        ambiguity_dimension_ids=["dim:entity", "dim:jurisdiction"],
        max_queries_per_component=1,
    )

    with pytest.raises(ScoutDisambiguationRuntimeError, match="Scout input query budget"):
        execute_scout_disambiguation_action(
            action=action,
            scout_input=scout_input,
            adapter=FakeScoutAdapter(),
        )

    reducer_kernel = _kernel()
    _produce_planner(reducer_kernel)
    bounded_input = _scout_input(
        reducer_kernel,
        query_budget={
            "max_queries_per_component": 1,
            "max_dimensions_per_component": 5,
            "authorized_query_count": 1,
        },
    )
    reducer_action = reducer_kernel.authorize_scout_disambiguation(
        component_id=bounded_input.component_id,
        ambiguity_dimension_ids=["dim:entity", "dim:jurisdiction"],
        max_queries_per_component=1,
    )
    payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(
            queries=_six_executed_queries()[:2],
            extra={
                "organic_results": [],
                "query_budget": {
                    "max_queries_per_component": 5,
                    "max_dimensions_per_component": 5,
                    "authorized_query_count": 5,
                },
            },
        ),
        scout_input=bounded_input.to_adapter_payload(),
        authorized_action_id=reducer_action.action_id,
    )
    observation = Observation.from_action(
        reducer_action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="query budget exceeds"):
        reducer_kernel.reduce(observation)


def test_scout_dimension_cap_enforced() -> None:
    kernel = _kernel()
    _produce_planner(kernel)

    with pytest.raises(ScoutDisambiguationRuntimeError, match="max 5 dimensions"):
        _scout_input(kernel, dimensions=_dimensions(6)).to_adapter_payload()

    valid_input = _scout_input(kernel, dimensions=_dimensions(5))
    _reduce_scout(kernel, scout_input=valid_input)
    assert len(kernel.state.scout_disambiguation_report_state["ambiguity_dimensions"]) == 5


def test_scout_dimension_budget_cannot_exceed_action_binding() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    scout_input = _scout_input(
        kernel,
        dimensions=_dimensions(2),
        query_budget={
            "max_queries_per_component": 5,
            "max_dimensions_per_component": 1,
            "authorized_query_count": 5,
        },
    )
    action = kernel.authorize_scout_disambiguation(
        component_id=scout_input.component_id,
        ambiguity_dimension_ids=["dim:entity"],
        max_dimensions_per_component=1,
    )
    payload = build_scout_disambiguation_report_payload(
        adapter_result=_scout_result(extra={"organic_results": []}),
        scout_input=scout_input.to_adapter_payload(),
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="dimensions exceed authorized"):
        kernel.reduce(observation)


def test_serper_shaped_result_hints_are_normalized_as_non_evidence() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    result = _scout_result(
        extra={
            "knowledgeGraph": {
                "query_id": "scout-query:official",
                "related_dimension_ids": ["dim:entity"],
                "title": "Example Permit",
                "type": "Government program",
                "website": "https://official.example.gov/permit",
                "description": "Official permit program.",
                "descriptionSource": "Official Example",
                "descriptionLink": "https://official.example.gov/about",
                "attributes": {"Agency": "Example Department"},
            },
            "peopleAlsoAsk": [
                {
                    "query_id": "scout-query:official",
                    "related_dimension_ids": ["dim:entity"],
                    "question": "Who administers Example Permit?",
                    "snippet": "The Example Department administers it.",
                    "title": "Example Permit FAQ",
                    "link": "https://official.example.gov/faq",
                }
            ],
            "relatedSearches": [
                {
                    "query_id": "scout-query:official",
                    "related_dimension_ids": ["dim:entity"],
                    "query": "Example Permit threshold 2026 official",
                }
            ],
            "news": [
                {
                    "query_id": "scout-query:official",
                    "related_dimension_ids": ["dim:entity"],
                    "title": "Example Permit threshold update",
                    "link": "https://news.example.test/update",
                    "snippet": "A threshold update was announced.",
                    "date": "2026-02-01",
                    "source": "Example News",
                    "imageUrl": "https://news.example.test/image.jpg",
                    "position": 1,
                }
            ],
        }
    )

    _reduce_scout(kernel, adapter=FakeScoutAdapter(result))

    hints = kernel.state.scout_disambiguation_report_projection["scout_result_hints"]
    kinds = {hint["hint_kind"] for hint in hints}
    assert {"organic", "knowledge_graph", "people_also_ask", "related_search", "news"} <= kinds
    organic = next(hint for hint in hints if hint["hint_kind"] == "organic")
    assert organic["title"] == "Example Permit - Official Threshold"
    assert organic["link"] == "https://official.example.gov/permit/threshold"
    assert organic["snippet"] == "Official current threshold information."
    assert organic["position"] == 1
    assert organic["date"] == "2026-01-01"
    assert organic["source"] == "Official Example"
    assert organic["domain"] == "Official Example"
    assert organic["attributes"]["Agency"] == "Example Department"
    assert organic["sitelinks"][0]["title"] == "Threshold table"
    kg = next(hint for hint in hints if hint["hint_kind"] == "knowledge_graph")
    assert kg["type"] == "Government program"
    assert kg["description"] == "Official permit program."
    assert kg["description_source"] == "Official Example"
    assert kg["description_link"] == "https://official.example.gov/about"
    paa = next(hint for hint in hints if hint["hint_kind"] == "people_also_ask")
    assert paa["question"] == "Who administers Example Permit?"
    related = next(hint for hint in hints if hint["hint_kind"] == "related_search")
    assert related["related_query"] == "Example Permit threshold 2026 official"
    news = next(hint for hint in hints if hint["hint_kind"] == "news")
    assert news["image_url"] == "https://news.example.test/image.jpg"
    for hint in hints:
        assert hint["evidence_admitted"] is False
        assert hint["citation_eligible"] is False
        assert hint["source_obligation_satisfied"] is False
        assert hint["fetch_read_retrieval_behavior_changed"] is False
    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert '"raw_provider_payload":' not in trace_json
    assert '"raw_search_response":' not in trace_json


def test_scout_report_does_not_mutate_contracts_or_amendments() -> None:
    kernel = _kernel()
    qmr = _produce_planner(kernel)
    _accept_planner_qmr(kernel, qmr)
    initial_before = deepcopy(kernel.state.initial_answer_contract)
    current_before = deepcopy(kernel.state.current_answer_contract)
    admission_before = deepcopy(kernel.state.contract_amendment_admission_history)
    application_before = deepcopy(kernel.state.contract_amendment_application_history)

    _reduce_scout(kernel)

    assert kernel.state.initial_answer_contract == initial_before
    assert kernel.state.current_answer_contract == current_before
    assert kernel.state.contract_amendment_admission_history == admission_before
    assert kernel.state.contract_amendment_application_history == application_before
    report = kernel.state.scout_disambiguation_report_projection
    assert report["recommended_planner_revision_inputs"]
    assert report["contract_mutation_applied"] is False


def test_scout_report_does_not_activate_search_executor_or_retrieval() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)

    _reduce_scout(kernel)

    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_work_plan_projection == {}
    assert kernel.state.offline_search_executor_bridge_projection == {}
    assert kernel.state.offline_search_executor_bridge_history == []
    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before
    report = kernel.state.scout_disambiguation_report_projection
    for key in (
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
        "fetch_read_retrieval_behavior_changed",
        "search_executor_runtime_activated",
        "search_work_plan_constructed",
    ):
        assert report[key] is False


def test_scout_report_rejects_closed_authority_or_raw_provider_fields() -> None:
    kernel = _kernel()
    _produce_planner(kernel)
    unsafe = _scout_result(
        extra={
            "evidence_ledger_admission": {"claim": "not allowed"},
            "citation_eligible": True,
            "source_obligation_satisfied": True,
            "current_answer_contract": {"mutated": True},
            "final_answer_packet": {"created": True},
            "author_input": {"created": True},
            "raw_provider_payload": {"private": True},
            "raw_search_response": {"private": True},
        }
    )

    with pytest.raises(ScoutDisambiguationRuntimeError):
        _reduce_scout(kernel, adapter=FakeScoutAdapter(unsafe))

    assert kernel.state.scout_disambiguation_report_state == {}
    assert kernel.state.scout_disambiguation_report_projection == {}
    assert kernel.state.scout_disambiguation_report_history == []


def test_static_closed_surface_guard_for_scout_disambiguation_runtime() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.scout",
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.search_executor",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(RUNTIME_MODULE).isdisjoint(forbidden_imports)
    source = _text(RUNTIME_MODULE)
    for token in (
        "serper.dev",
        "SERPER_API_KEY",
        "run_scout(",
        "SearchExecutor(",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
    ):
        assert token not in source
    assert "SCOUT_DISAMBIGUATE" in _text(RUN_KERNEL)
    assert "SCOUT_DISAMBIGUATION_REPORTED" in _text(RUN_KERNEL)

    pipeline_source = _text(PIPELINE)
    assert "scout_adapter=scout_adapter" in pipeline_source
    assert "scout_adapter = deps.scout_disambiguation_adapter" in pipeline_source
    assert 'getattr(deps, "scout_disambiguation_adapter", None)' not in pipeline_source
    assert "brave_reconnaissance(" not in pipeline_source


def test_docs_record_product_consumed_non_evidence_scout_posture() -> None:
    required = (
        "SEARCHOS-REQUIRED-SCOUT-ORDINARY-COMPOSITION-01",
        "ordinary provider-neutral Scout adapter",
        "DISCOVER(lightweight_disambiguation)",
        "Scout reports remain non-evidence",
        "required truthful-targeting",
        "No live provider, model, search, recon, fetch/read, or retrieval call was made",
    )
    forbidden = (
        "Scout mutates contracts",
        "Scout revises planner output",
        "Scout satisfies source obligations",
        "Scout creates citations",
        "Scout admits evidence",
        "Scout executes SearchExecutor",
        "Scout fetches or reads pages",
        "Scout selects the DISCOVER provider",
        "Scout satisfies an accepted source obligation",
    )
    for path in DOCS:
        text = " ".join(_text(path).split())
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
