from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.run_kernel import (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE,
    SEARCH_PLANNER_PRODUCTION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_INPUT_PREVIEW_CHARS,
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    SearchPlannerRuntimeError,
    build_search_planner_observation_payload,
    contract_ref_from_contract,
    execute_search_planner_action,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "search_planner_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "roadmap" / "SEARCHOS_QUERY_STRATEGY_AND_RECON_CONVERGENCE_01.md",
)

RUN_ID = "run:ag-search-planner-runtime-01"
REQUEST_ID = "request:ag-search-planner-runtime-01"
QUERY = "What is the current official filing threshold for Example Permit in 2026?"
LONG_QUERY_PREFIX = "Q" * SEARCH_PLANNER_INPUT_PREVIEW_CHARS
LONG_QUERY_SUFFIX_A = " DISTINCT_SUFFIX_ALPHA_AFTER_PREVIEW_LIMIT"
LONG_QUERY_SUFFIX_B = " DISTINCT_SUFFIX_BETA_AFTER_PREVIEW_LIMIT"


class DeterministicPlannerAdapter:
    def __init__(self, *, extra: Mapping[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.extra = dict(extra or {})

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(dict(planner_input))
        result = _planner_result()
        result.update(self.extra)
        return result


def _planner_result() -> dict[str, Any]:
    return {
        "question_meaning_summary": (
            "Determine the official current threshold and preserve source-bound caveats."
        ),
        "requested_output": "Concise answer with official-current source support.",
        "semantic_slots": [
            {
                "slot_id": "slot:program",
                "slot_kind": "entity",
                "status": "explicit",
                "selected_value": "Example Permit",
                "materiality": "material",
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
                    "What is the official current filing threshold for the requested program?"
                ),
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "state the threshold",
                    "bind the answer to an official current source",
                ],
                "semantic_slot_ids": ["slot:program", "slot:time-period"],
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": ["Keep the answer source-bound."],
                "prohibited_upgrades": ["Do not substitute a non-official estimate."],
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
                "requirement_summary": "Find the official current source for the threshold.",
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "preferred_source_kinds": ["official"],
                "recency_requirement": "current for 2026",
            }
        ],
        "material_ambiguity_posture": "clear",
        "mandatory_caveats": ["Report only the source-bound value."],
        "prohibited_upgrades": ["Do not infer a threshold from older years."],
        "normalization_obligations": ["Normalize the effective year to 2026."],
        "assumptions": ["The user asks for the program named in the query."],
        "unsupported_outputs": ["No final answer is produced by the planner."],
    }


def _kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _planner_input(
    kernel: RunKernel,
    *,
    query: str = QUERY,
    parent_initial_ref: Mapping[str, Any] | None = None,
    parent_current_ref: Mapping[str, Any] | None = None,
) -> SearchPlannerInput:
    initial_ref = (
        dict(parent_initial_ref)
        if parent_initial_ref is not None
        else contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        )
    )
    current_ref = (
        dict(parent_current_ref)
        if parent_current_ref is not None
        else contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        )
    )
    return SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text=query,
        requested_mode="balanced",
        safe_context={"source_policy": "official-current"},
        route_context_ref={"route_ref": "safe-route-ref"},
        run_context_ref={"run_ref": "safe-run-ref"},
        parent_initial_contract_ref=initial_ref,
        parent_current_contract_ref=current_ref,
    )


def _produce(
    kernel: RunKernel,
    *,
    planner_input: SearchPlannerInput | None = None,
    adapter: DeterministicPlannerAdapter | None = None,
    reduce: bool = True,
) -> tuple[Observation, Mapping[str, Any]]:
    input_ = planner_input or _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=input_.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=input_,
        adapter=adapter or DeterministicPlannerAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    if reduce:
        kernel.reduce(observation)
    return observation, result.observation_payload


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


def test_adapter_required_and_default_fails_closed() -> None:
    kernel = _kernel()
    planner_input = _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
    )

    with pytest.raises(SearchPlannerRuntimeError, match="explicitly injected adapter"):
        execute_search_planner_action(action=action, planner_input=planner_input)

    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []


def test_planner_proposal_reduces_to_run_kernel_state_projection_and_history() -> None:
    kernel = _kernel()
    adapter = DeterministicPlannerAdapter()

    _produce(kernel, adapter=adapter)

    assert adapter.calls
    state = kernel.state.search_planner_proposal_state
    projection = kernel.state.search_planner_proposal_projection
    assert state["owner"] == "RunKernel.SearchPlannerProposal"
    assert state["canonical_state"] is True
    assert state["question_meaning_proposed"] is True
    assert state["qmr_payload_compatible_with_initial_contract_acceptance"] is True
    assert state["proposal_digest"]
    assert projection["proposal_digest"] == state["proposal_digest"]
    assert projection["question_meaning_record"]["record_digest"]
    assert kernel.state.search_planner_proposal_history[-1] == projection
    assert kernel.state.projections[SEARCH_PLANNER_PRODUCTION_STAGE] == projection
    assert kernel.state.initial_answer_contract == {}
    assert kernel.state.current_answer_contract == {}
    assert all(value is False for value in projection["closed_surface_flags"].values())


def test_planner_qmr_feeds_initial_answer_contract_acceptance() -> None:
    kernel = _kernel()
    _produce(kernel)
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]

    _accept_planner_qmr(kernel, qmr)

    initial = kernel.state.initial_answer_contract
    assert initial["parent_question_meaning_record_id"] == qmr["record_id"]
    assert initial["parent_question_meaning_record_digest"] == qmr["record_digest"]
    assert initial["accepted_answer_component_refs"][0]["component_id"] == "component:official-threshold"
    assert kernel.state.projections[INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE]


def test_adapter_receives_full_query_text_beyond_preview_limit() -> None:
    kernel = _kernel()
    adapter = DeterministicPlannerAdapter()
    query = LONG_QUERY_PREFIX + LONG_QUERY_SUFFIX_A
    planner_input = _planner_input(kernel, query=query)

    _observation, payload = _produce(
        kernel,
        planner_input=planner_input,
        adapter=adapter,
    )

    adapter_input = adapter.calls[0]
    assert LONG_QUERY_SUFFIX_A.strip() in adapter_input["user_query_text_for_planning"]
    assert adapter_input["user_query_ref"]["preview"] == LONG_QUERY_PREFIX
    assert adapter_input["user_query_ref"]["digest"] == planner_input.user_query_digest
    assert adapter_input["user_query_ref"]["raw_user_query_retained"] is False
    assert adapter_input["user_query_ref"]["user_query_text_for_planning_retained"] is False

    persisted_payload = json.dumps(payload, sort_keys=True)
    persisted_state = json.dumps(kernel.state.search_planner_proposal_state, sort_keys=True)
    persisted_projection = json.dumps(
        kernel.state.search_planner_proposal_projection,
        sort_keys=True,
    )
    persisted_history = json.dumps(
        kernel.state.search_planner_proposal_history,
        sort_keys=True,
    )
    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    for persisted in (
        persisted_payload,
        persisted_state,
        persisted_projection,
        persisted_history,
        trace_json,
    ):
        assert LONG_QUERY_SUFFIX_A.strip() not in persisted
        assert '"user_query_text_for_planning":' not in persisted
    assert kernel.state.search_planner_proposal_projection["user_query_ref"] == {
        "digest": planner_input.user_query_digest,
        "full_user_query_text_retained": False,
        "preview": LONG_QUERY_PREFIX,
        "preview_char_limit": SEARCH_PLANNER_INPUT_PREVIEW_CHARS,
        "user_query_text_for_planning_retained": False,
    }


def test_user_query_digest_uses_full_query_not_preview() -> None:
    kernel = _kernel()
    input_a = _planner_input(kernel, query=LONG_QUERY_PREFIX + LONG_QUERY_SUFFIX_A)
    input_b = _planner_input(kernel, query=LONG_QUERY_PREFIX + LONG_QUERY_SUFFIX_B)

    assert input_a.user_query_preview == LONG_QUERY_PREFIX
    assert input_b.user_query_preview == LONG_QUERY_PREFIX
    assert input_a.user_query_preview == input_b.user_query_preview
    assert input_a.user_query_digest != input_b.user_query_digest


def test_same_prefix_different_suffix_stale_query_is_rejected() -> None:
    kernel = _kernel()
    action_input = _planner_input(kernel, query=LONG_QUERY_PREFIX + LONG_QUERY_SUFFIX_A)
    action = kernel.authorize_search_planner_production(
        user_query_digest=action_input.user_query_digest,
    )
    stale_input = _planner_input(kernel, query=LONG_QUERY_PREFIX + LONG_QUERY_SUFFIX_B)
    assert action_input.user_query_preview == stale_input.user_query_preview
    assert action_input.user_query_digest != stale_input.user_query_digest
    payload = build_search_planner_observation_payload(
        adapter_result=_planner_result(),
        planner_input=stale_input.to_adapter_payload(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="stale query digest"):
        kernel.reduce(observation)


def test_stale_query_digest_is_rejected() -> None:
    kernel = _kernel()
    action_input = _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=action_input.user_query_digest,
    )
    stale_input = _planner_input(kernel, query="Different query text")
    payload = build_search_planner_observation_payload(
        adapter_result=_planner_result(),
        planner_input=stale_input.to_adapter_payload(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="stale query digest"):
        kernel.reduce(observation)


def test_stale_parent_contract_digest_is_rejected() -> None:
    kernel = _kernel()
    _produce(kernel)
    _accept_planner_qmr(
        kernel,
        kernel.state.search_planner_proposal_projection["question_meaning_record"],
    )
    stale_parent_ref = {
        "source": "initial_answer_contract",
        "contract_version": kernel.state.initial_answer_contract["accepted_contract_version"],
        "contract_digest": "stale-parent-digest",
    }
    planner_input = _planner_input(kernel, parent_initial_ref=stale_parent_ref)

    observation, _payload = _produce(kernel, planner_input=planner_input, reduce=False)

    with pytest.raises(RunKernelTransitionError, match="stale parent digest"):
        kernel.reduce(observation)


def test_duplicate_proposal_for_same_query_parent_context_is_rejected() -> None:
    kernel = _kernel()
    _produce(kernel)

    observation, _payload = _produce(kernel, reduce=False)

    with pytest.raises(RunKernelTransitionError, match="duplicate search planner proposal"):
        kernel.reduce(observation)


def test_component_search_requirements_are_subordinate_and_non_executing() -> None:
    kernel = _kernel()
    _produce(kernel)

    projection = kernel.state.search_planner_proposal_projection
    requirements = projection["component_search_requirements"]
    assert requirements
    requirement = requirements[0]
    assert requirement["component_id"] == "component:official-threshold"
    assert requirement["must_not_execute"] is True
    assert requirement["subordinate_to_answer_contract"] is True
    assert requirement["search_executed"] is False
    assert projection["component_search_requirements_executed"] is False
    assert projection["source_obligation_satisfied"] is False
    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_work_plan_projection == {}


def test_amendment_candidates_are_deferred_not_admitted_or_applied() -> None:
    kernel = _kernel()
    adapter = DeterministicPlannerAdapter(
        extra={
            "contract_amendment_candidates": [
                {
                    "candidate_id": "deferred:caveat",
                    "operation_kind": "add_caveat",
                    "summary": "May require a caveat after evidence is read.",
                }
            ]
        }
    )

    _produce(kernel, adapter=adapter)

    projection = kernel.state.search_planner_proposal_projection
    assert projection["amendment_path"]["status"] == "deferred"
    assert projection["amendment_path"]["candidate_count"] == 1
    assert projection["contract_amendments_applied"] is False
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_application_history == []
    assert kernel.state.current_answer_contract == {}


def test_projection_excludes_raw_private_sentinels() -> None:
    kernel = _kernel()
    result = _planner_result()
    result["raw_prompt"] = "RAW_PRIVATE_SENTINEL"
    result["semantic_slots"] = deepcopy(result["semantic_slots"])
    result["semantic_slots"][0]["metadata"] = {"safe_note": "RAW_PRIVATE_SENTINEL"}
    adapter = DeterministicPlannerAdapter(extra=result)

    _produce(kernel, adapter=adapter)

    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert "RAW_PRIVATE_SENTINEL" not in trace_json
    assert '"raw_prompt":' not in trace_json
    assert '"provider_payload":' not in trace_json


def test_static_closed_surface_guard_and_ordinary_pipeline_consumption() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(RUNTIME_MODULE).isdisjoint(forbidden_imports)
    source = _text(RUNTIME_MODULE)
    for token in (
        "ask_model(",
        "brave_reconnaissance",
        "search_scout_results",
        "fetch_linkup_precision_block",
        "run_scout(",
        "SearchExecutor(",
    ):
        assert token not in source
    assert "SEARCH_PLANNER_PRODUCE" in _text(RUN_KERNEL)
    assert "SEARCH_PLANNER_PRODUCED" in _text(RUN_KERNEL)

    pipeline_source = _text(PIPELINE)
    assert "execute_initial_query_strategy_convergence(" in pipeline_source
    assert "query_plan_admission_inputs_from_query_production_projection(" not in pipeline_source
    assert "execute_query_production_action(" not in pipeline_source


def test_docs_record_converged_planner_runtime_posture() -> None:
    for path in DOCS:
        text = " ".join(_text(path).split())
        assert "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01" in text, path
        assert "SearchPlanner proposals remain passive" in text, path
        assert "RunKernel initial AnswerContract acceptance" in text, path
        assert "legacy Brave/recon-rewriter/researcher" in text, path
