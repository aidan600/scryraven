from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION,
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
)
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
from core.search_planner_runtime import (
    SEARCH_PLANNER_INPUT_PREVIEW_CHARS,
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    contract_ref_from_contract,
    execute_search_planner_action,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_MODULE = ROOT / "core" / "search_planner_model_adapter.py"
PROMPT_MODULE = ROOT / "core" / "search_planner_model_prompt.py"
RUNTIME_MODULE = ROOT / "core" / "search_planner_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
)

RUN_ID = "run:ag-search-planner-model-01"
REQUEST_ID = "request:ag-search-planner-model-01"
QUERY = "What is the current official filing threshold for Example Permit in 2026?"
LONG_SUFFIX = " DISTINCT_FULL_QUERY_SUFFIX_FOR_MODEL_ADAPTER"
RAW_PROMPT_SENTINEL = "RAW_PROMPT_MODEL_ADAPTER_SENTINEL"
RAW_RESPONSE_SENTINEL = "RAW_MODEL_RESPONSE_SENTINEL"
RAW_PROVIDER_SENTINEL = "RAW_PROVIDER_PAYLOAD_SENTINEL"


class FakeAskModel:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _planner_output(*, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
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
                "component_id": "component:model-official-threshold",
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
                "source_obligation_candidate_ids": ["obligation:model-official-current"],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": ["Keep the answer source-bound."],
                "prohibited_upgrades": ["Do not substitute a non-official estimate."],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": "obligation:model-official-current",
                "obligation_kind": "official_current_source",
                "component_candidate_ids": ["component:model-official-threshold"],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": "component:model-official-threshold",
                "requirement_id": "searchreq:model-official-current-threshold",
                "requirement_summary": "Find the official current source for the threshold.",
                "source_obligation_candidate_ids": ["obligation:model-official-current"],
                "preferred_source_kinds": ["official"],
                "recency_requirement": "current for 2026",
            }
        ],
        "material_ambiguity_posture": "clear",
        "mandatory_caveats": ["Report only the source-bound value."],
        "prohibited_upgrades": ["Do not infer a threshold from older years."],
        "normalization_obligations": ["Normalize the effective year to 2026."],
        "assumptions": ["The user asks for the program named in the query."],
        "unsupported_or_deferred_outputs": ["No final answer is produced by the planner."],
    }
    if extra:
        payload.update(extra)
    return payload


def _kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _planner_input(kernel: RunKernel, *, query: str = QUERY) -> SearchPlannerInput:
    return SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text=query,
        requested_mode="balanced",
        safe_context={"source_policy": "official-current"},
        route_context_ref={"route_ref": "safe-route-ref"},
        run_context_ref={"run_ref": "safe-run-ref"},
        parent_initial_contract_ref=contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )


def _adapter(fake: FakeAskModel, *, enabled: bool = True, licensed: bool = True) -> SearchPlannerModelAdapter:
    return SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        effort="low",
        use_reasoning=False,
        enabled=enabled,
        licensed=licensed,
    )


def _produce(
    kernel: RunKernel,
    adapter: SearchPlannerModelAdapter,
    *,
    planner_input: SearchPlannerInput | None = None,
    reduce: bool = True,
) -> Mapping[str, Any]:
    input_ = planner_input or _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=input_.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(action=action, planner_input=input_, adapter=adapter)
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    if reduce:
        kernel.reduce(observation)
    return result.observation_payload


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


def test_model_adapter_requires_enabled_and_callable() -> None:
    fake = FakeAskModel(json.dumps(_planner_output()))
    disabled = SearchPlannerModelAdapter(ask_model=fake, enabled=False, licensed=True)
    unlicensed = SearchPlannerModelAdapter(ask_model=fake, enabled=True, licensed=False)
    missing_callable = SearchPlannerModelAdapter(ask_model=None, enabled=True, licensed=True)
    planner_input = _planner_input(_kernel()).to_adapter_payload()

    for adapter in (disabled, unlicensed, missing_callable):
        with pytest.raises(SearchPlannerModelAdapterError, match="explicitly enabled"):
            adapter.produce(planner_input)

    assert fake.calls == []


def test_model_adapter_calls_injected_model_with_json_requirement() -> None:
    query = "Q" * SEARCH_PLANNER_INPUT_PREVIEW_CHARS + LONG_SUFFIX
    fake = FakeAskModel(json.dumps(_planner_output()))
    adapter = _adapter(fake)

    adapter.produce(_planner_input(_kernel(), query=query).to_adapter_payload())

    assert len(fake.calls) == 1
    args, kwargs = fake.calls[0]
    prompt = args[0]
    system_prompt = args[1]
    assert "You are SearchPlanner, not Author" in prompt
    assert "Do not answer the user" in prompt
    assert "Do not cite sources" in prompt
    assert "Do not invoke Scout" in prompt
    assert LONG_SUFFIX.strip() in prompt
    assert "SearchPlanner" in system_prompt
    assert kwargs["require_json"] is True
    assert kwargs["provider"] == "FakeProvider"
    assert kwargs["model"] == "fake-fast-model"


def test_valid_fake_model_json_flows_through_search_planner_runtime_and_initial_contract_acceptance() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_planner_output()))

    _produce(kernel, _adapter(fake))
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    _accept_planner_qmr(kernel, qmr)

    initial = kernel.state.initial_answer_contract
    assert initial["accepted_answer_component_refs"][0]["component_id"] == "component:model-official-threshold"
    assert kernel.state.search_planner_proposal_state["owner"] == "RunKernel.SearchPlannerProposal"
    assert kernel.state.search_planner_proposal_state["initial_answer_contract_mutated"] is False
    assert initial["owner"] == "RunKernel.InitialAnswerContract"
    assert kernel.state.current_answer_contract == {}
    metadata = kernel.state.search_planner_proposal_projection["planner_model_metadata"]
    assert metadata["planner_model_adapter_schema_version"] == SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION
    assert metadata["planner_model_prompt_schema_version"] == SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
    assert metadata["prompt_hash"]
    assert metadata["prompt_length"] > 0
    assert metadata["require_json"] is True
    assert metadata["raw_prompt_retained"] is False
    assert metadata["raw_model_response_retained"] is False
    assert metadata["provider_payload_retained"] is False


def test_invalid_json_or_unparseable_response_fails_before_observation() -> None:
    kernel = _kernel()
    fake = FakeAskModel("not-json " + RAW_RESPONSE_SENTINEL)

    with pytest.raises(SearchPlannerModelAdapterError, match="valid JSON"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []


def test_schema_invalid_model_output_fails_before_observation() -> None:
    kernel = _kernel()
    invalid = deepcopy(_planner_output())
    invalid.pop("answer_components")
    fake = FakeAskModel(json.dumps(invalid))

    with pytest.raises(SearchPlannerModelAdapterError, match="missing required fields"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


def test_model_output_forbidden_authority_fields_fail_closed() -> None:
    kernel = _kernel()
    unsafe = _planner_output(
        extra={
            "current_answer_contract": {"mutated": True},
            "initial_answer_contract": {},
            "final_answer_packet": {},
            "author_input": {},
            "sufficiency_decision": "ready",
            "evidence_ledger_admission": {},
        }
    )
    fake = FakeAskModel(json.dumps(unsafe))

    with pytest.raises(SearchPlannerModelAdapterError, match="closed authority fields"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


def test_raw_prompt_model_response_provider_payload_not_retained() -> None:
    kernel = _kernel()
    output = _planner_output(
        extra={
            "planner_notes": [RAW_RESPONSE_SENTINEL],
            "model_confidence_posture": "low",
        }
    )
    fake = FakeAskModel(json.dumps(output))
    planner_input = _planner_input(
        kernel,
        query=f"What is this? {RAW_PROMPT_SENTINEL}",
    )

    _produce(kernel, _adapter(fake), planner_input=planner_input)

    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert RAW_PROMPT_SENTINEL not in trace_json
    assert RAW_RESPONSE_SENTINEL not in trace_json
    assert RAW_PROVIDER_SENTINEL not in trace_json
    assert '"raw_prompt":' not in trace_json
    assert '"raw_model_response":' not in trace_json
    assert '"raw_provider_payload":' not in trace_json
    assert '"provider_payload":' not in trace_json
    assert "fake-fast-model" in trace_json
    assert '"prompt_hash":' in trace_json


def test_raw_provider_payload_field_fails_closed() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_planner_output(extra={"raw_provider_payload": RAW_PROVIDER_SENTINEL})))

    with pytest.raises(SearchPlannerModelAdapterError, match="raw/private fields"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


def test_contract_amendment_candidates_remain_deferred() -> None:
    kernel = _kernel()
    fake = FakeAskModel(
        json.dumps(
            _planner_output(
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
        )
    )

    _produce(kernel, _adapter(fake))

    projection = kernel.state.search_planner_proposal_projection
    assert projection["amendment_path"]["status"] == "deferred"
    assert projection["amendment_path"]["candidate_count"] == 1
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_application_history == []
    assert kernel.state.current_answer_contract == {}


def test_model_adapter_component_search_requirements_remain_non_executing() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_planner_output()))

    _produce(kernel, _adapter(fake))

    projection = kernel.state.search_planner_proposal_projection
    requirement = projection["component_search_requirements"][0]
    assert requirement["must_not_execute"] is True
    assert requirement["subordinate_to_answer_contract"] is True
    assert requirement["search_executed"] is False
    assert projection["component_search_requirements_executed"] is False
    assert projection["source_obligation_satisfied"] is False
    assert projection["search_executor_runtime_activated"] is False
    assert projection["sufficiency_decided"] is False
    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_work_plan_projection == {}


def test_model_output_executing_component_requirement_fails_closed() -> None:
    kernel = _kernel()
    unsafe = deepcopy(_planner_output())
    unsafe["component_search_requirements"][0]["search_executed"] = True
    fake = FakeAskModel(json.dumps(unsafe))

    with pytest.raises(SearchPlannerModelAdapterError, match="closed runtime surfaces"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


def test_static_closed_surface_guard_for_search_planner_model_adapter() -> None:
    forbidden_imports = {
        "core.llm",
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.scout",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "exa_py",
    }
    assert _imports(ADAPTER_MODULE).isdisjoint(forbidden_imports)
    assert _imports(PROMPT_MODULE).isdisjoint(forbidden_imports)
    adapter_source = _text(ADAPTER_MODULE)
    prompt_source = _text(PROMPT_MODULE)
    runtime_source = _text(RUNTIME_MODULE)
    for token in (
        "from core.llm import ask_model",
        "import core.llm",
        "run_scout(",
        "SearchExecutor(",
        "brave_reconnaissance",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
        "load_dotenv",
    ):
        assert token not in adapter_source
        assert token not in prompt_source
    for token in ("run_scout(", "SearchExecutor(", "execute_author_action("):
        assert token not in runtime_source

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_docs_use_merge_stable_search_planner_model_posture() -> None:
    required = (
        "AG-SEARCH-PLANNER-RUNTIME-01",
        "AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter",
        "No live model calls or live validation were run",
        "PR #327 / AG-SEARCH-PLANNER-MODEL-01",
        "AG-SCOUT-DISAMBIGUATION-RUNTIME-01",
        "Scout hints are not evidence",
        "post-merge next gate is AG-SEARCH-PLANNER-REVISION-01",
    )
    forbidden = (
        "live validation is now next",
        "SearchPlanner executes search",
        "SearchPlanner mutates current_answer_contract",
        "model output satisfies source obligations",
        "model planner creates final answer",
        "Author is invoked by planner",
        "Scout is activated by AG-SEARCH-PLANNER-MODEL-01",
        "SearchExecutor is activated by AG-SEARCH-PLANNER-MODEL-01",
    )
    for path in DOCS:
        text = _text(path)
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
