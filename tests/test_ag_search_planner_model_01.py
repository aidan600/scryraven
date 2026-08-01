from __future__ import annotations

import ast
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

import core.search_planner_model_adapter as search_planner_model_adapter
import core.search_planner_model_prompt as search_planner_model_prompt
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION,
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
    SearchPlannerModelAdapterFailureStage,
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
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "roadmap" / "SEARCHOS_QUERY_STRATEGY_AND_RECON_CONVERGENCE_01.md",
)

RUN_ID = "run:ag-search-planner-model-01"
REQUEST_ID = "request:ag-search-planner-model-01"
QUERY = "What is the current official filing threshold for Example Permit in 2026?"
LONG_SUFFIX = " DISTINCT_FULL_QUERY_SUFFIX_FOR_MODEL_ADAPTER"
RAW_PROMPT_SENTINEL = "RAW_PROMPT_MODEL_ADAPTER_SENTINEL"
RAW_RESPONSE_SENTINEL = "RAW_MODEL_RESPONSE_SENTINEL"
RAW_PROVIDER_SENTINEL = "RAW_PROVIDER_PAYLOAD_SENTINEL"

_STRICT_JSON_WRONG_TEXT_TYPES: tuple[tuple[str, Any], ...] = (
    ("null", None),
    ("true", True),
    ("false", False),
    ("integer", 7),
    ("finite_decimal", 1.5),
    ("object", {"fictional": "value"}),
    ("array", ["fictional"]),
)

_STRICT_TYPE_PREDICATE_MATRIX: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "direct_optional_enum_text",
        (
            "ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM",
            "SOURCE_OBLIGATION_STRICTNESS_ENUM",
        ),
    ),
    (
        "required_text",
        (
            "QUESTION_MEANING_SUMMARY_TEXT_OVER_MAX",
            "REQUESTED_OUTPUT_TEXT_OVER_MAX",
            "MATERIAL_AMBIGUITY_POSTURE_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_OVER_MAX",
            "RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_OVER_MAX",
            "COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_OVER_MAX",
            "SEMANTIC_SLOT_STATUS_TEXT_OVER_MAX",
            "SEMANTIC_SLOT_MATERIALITY_TEXT_OVER_MAX",
            "SEMANTIC_SLOT_KIND_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_MATERIALITY_TEXT_OVER_MAX",
            "SOURCE_OBLIGATION_KIND_TEXT_OVER_MAX",
        ),
    ),
    (
        "required_enum_empty_text",
        (
            "SEMANTIC_SLOT_STATUS_TEXT_EMPTY",
            "SEMANTIC_SLOT_MATERIALITY_TEXT_EMPTY",
            "SEMANTIC_SLOT_KIND_TEXT_EMPTY",
            "ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_EMPTY",
            "ANSWER_COMPONENT_MATERIALITY_TEXT_EMPTY",
            "SOURCE_OBLIGATION_KIND_TEXT_EMPTY",
        ),
    ),
    (
        "required_enum_value_membership",
        (
            "SEMANTIC_SLOT_STATUS_VALUE_NOT_ALLOWED",
            "SEMANTIC_SLOT_MATERIALITY_VALUE_NOT_ALLOWED",
            "SEMANTIC_SLOT_KIND_VALUE_NOT_ALLOWED",
            "ANSWER_COMPONENT_REQUIREMENT_POSTURE_VALUE_NOT_ALLOWED",
            "ANSWER_COMPONENT_MATERIALITY_VALUE_NOT_ALLOWED",
            "SOURCE_OBLIGATION_KIND_VALUE_NOT_ALLOWED",
        ),
    ),
    (
        "text_array_items",
        (
            "TOP_LEVEL_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX",
            "TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX",
            "NORMALIZATION_OBLIGATION_ITEM_TEXT_OVER_MAX",
            "ASSUMPTION_ITEM_TEXT_OVER_MAX",
            "UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_ITEM_TEXT_OVER_MAX",
            "SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_TEXT_OVER_MAX",
            "SEMANTIC_SLOT_NORMALIZATION_NOTE_ITEM_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX",
            "ANSWER_COMPONENT_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX",
            "COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KIND_ITEM_TEXT_OVER_MAX",
        ),
    ),
)


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
                "component_purpose": "user_facing_answer_target",
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
                "obligation_kind": "official_current",
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
                "metadata": {
                    "query_strategy_candidates": [
                        {
                            "strategy_id": "strategy:model-official-threshold:primary",
                            "component_id": "component:model-official-threshold",
                            "candidate_kind": "primary",
                            "candidate_query_text": (
                                "Example Permit official filing threshold 2026"
                            ),
                            "requested_role": "official_bias",
                            "source_obligation_candidate_ids": [
                                "obligation:model-official-current"
                            ],
                            "distinct_need_justification": (
                                "Primary query for the accepted threshold component."
                            ),
                            "recon_requirement": {
                                "posture": "not_needed",
                                "unresolved_dimension_ids": [],
                                "candidate_queries": [],
                                "required_for_truthful_targeting": False,
                            },
                        }
                    ]
                },
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


def _adapter(
    fake: FakeAskModel,
    *,
    clean_json_response: Callable[[str], str] | None = None,
    enabled: bool = True,
    licensed: bool = True,
) -> SearchPlannerModelAdapter:
    return SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=clean_json_response or (lambda text: text),
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


def _model_output_error(
    model_output: Mapping[str, Any],
    *,
    kernel: RunKernel | None = None,
) -> SearchPlannerModelAdapterError:
    target_kernel = kernel or _kernel()
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(
            target_kernel,
            _adapter(FakeAskModel(json.dumps(model_output))),
        )
    return caught.value


def _strict_text_type_error(
    mutate: Callable[[dict[str, Any], Any], None],
    wrong_value: Any,
    *,
    kernel: RunKernel | None = None,
) -> SearchPlannerModelAdapterError:
    model_output = _planner_output()
    mutate(model_output, deepcopy(wrong_value))
    target_kernel = kernel or _kernel()
    error = _model_output_error(model_output, kernel=target_kernel)
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE
    assert error.mechanical_rule_id == "M02"
    assert target_kernel.state.search_planner_proposal_state == {}
    assert target_kernel.state.search_planner_proposal_projection == {}
    assert target_kernel.state.search_planner_proposal_history == []
    return error


def _assert_support_kind_rejection(
    support_kinds: Any,
    *,
    expected_code: SearchPlannerModelAdapterFailureCode,
    expected_rule: str,
    configure_component: Callable[[dict[str, Any]], None] | None = None,
    forbidden_fragments: tuple[str, ...] = (),
) -> SearchPlannerModelAdapterError:
    kernel = _kernel()
    model_output = _planner_output()
    component = model_output["answer_components"][0]
    component["allowed_support_kinds"] = deepcopy(support_kinds)
    if configure_component is not None:
        configure_component(component)

    error = _model_output_error(model_output, kernel=kernel)

    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == expected_code
    assert error.mechanical_rule_id == expected_rule
    assert error.__cause__ is None
    assert error.__context__ is None
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []
    for fragment in forbidden_fragments:
        assert fragment not in str(error)
        assert fragment not in repr(error)
        assert fragment not in repr(kernel.state)
    return error


def _planner_output_with_support_kind_variant(
    support_kinds: list[str],
) -> tuple[dict[str, Any], int]:
    model_output = _planner_output()
    if support_kinds == ["direct"]:
        return model_output, 0

    support_component = deepcopy(model_output["answer_components"][0])
    support_component.update(
        {
            "component_id": "component:model-derived-threshold",
            "user_facing_label": "Derived threshold result",
            "user_facing_question": "What threshold follows from the direct official result?",
            "requirement_posture": "optional",
            "allowed_support_kinds": support_kinds,
            "max_inference_depth": 1,
            "dependency_component_ids": ["component:model-official-threshold"],
        }
    )
    if support_kinds == ["inferred"]:
        support_component["source_obligation_candidate_ids"] = []
    elif support_kinds == ["direct", "inferred"]:
        support_component["source_obligation_candidate_ids"] = [
            "obligation:model-derived-current"
        ]
        model_output["source_obligation_candidates"].append(
            {
                "candidate_id": "obligation:model-derived-current",
                "obligation_kind": "official_current",
                "component_candidate_ids": ["component:model-derived-threshold"],
                "strictness": "required",
            }
        )
    else:
        raise AssertionError(f"unsupported test support-kind variant: {support_kinds!r}")

    model_output["answer_components"].append(support_component)
    return model_output, 1


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


def _schema_path(schema: Mapping[str, Any], *path: str) -> Any:
    value: Any = schema
    for key in path:
        value = value[key]
    return value


def test_model_adapter_requires_enabled_and_callable() -> None:
    fake = FakeAskModel(json.dumps(_planner_output()))
    disabled = SearchPlannerModelAdapter(ask_model=fake, enabled=False, licensed=True)
    unlicensed = SearchPlannerModelAdapter(ask_model=fake, enabled=True, licensed=False)
    missing_callable = SearchPlannerModelAdapter(ask_model=None, enabled=True, licensed=True)
    planner_input = _planner_input(_kernel()).to_adapter_payload()

    for adapter, expected_code in (
        (disabled, SearchPlannerModelAdapterFailureCode.ADAPTER_DISABLED),
        (unlicensed, SearchPlannerModelAdapterFailureCode.ADAPTER_DISABLED),
        (missing_callable, SearchPlannerModelAdapterFailureCode.ROUTE_UNAVAILABLE),
    ):
        with pytest.raises(
            SearchPlannerModelAdapterError,
            match="explicitly enabled",
        ) as caught:
            adapter.produce(planner_input)
        assert (
            caught.value.failure_stage
            == SearchPlannerModelAdapterFailureStage.INPUT
        )
        assert caught.value.failure_code == expected_code
        assert caught.value.mechanical_rule_id is None

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


def test_model_adapter_input_construction_failure_is_typed_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_failure = "private-input-construction-sentinel"

    def fail_prompt_construction(_planner_input: Mapping[str, Any]) -> str:
        raise RuntimeError(raw_failure)

    monkeypatch.setattr(
        search_planner_model_adapter,
        "build_search_planner_model_prompt",
        fail_prompt_construction,
    )
    fake = FakeAskModel(json.dumps(_planner_output()))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="model input failed closed: RuntimeError",
    ) as caught:
        _adapter(fake).produce(_planner_input(_kernel()).to_adapter_payload())

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.INPUT
    assert (
        caught.value.failure_code
        == SearchPlannerModelAdapterFailureCode.INPUT_CONSTRUCTION_FAILED
    )
    assert caught.value.mechanical_rule_id is None
    assert raw_failure not in str(caught.value)
    assert fake.calls == []


def test_model_adapter_model_call_failure_is_typed_and_sanitized() -> None:
    raw_failure = "private-model-call-sentinel"
    fake = FakeAskModel(RuntimeError(raw_failure))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="model call failed closed: RuntimeError",
    ) as caught:
        _adapter(fake).produce(_planner_input(_kernel()).to_adapter_payload())

    assert (
        caught.value.failure_stage
        == SearchPlannerModelAdapterFailureStage.MODEL_CALL
    )
    assert (
        caught.value.failure_code
        == SearchPlannerModelAdapterFailureCode.MODEL_CALL_FAILED
    )
    assert caught.value.mechanical_rule_id is None
    assert raw_failure not in str(caught.value)
    assert len(fake.calls) == 1


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

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="valid JSON",
    ) as caught:
        _produce(kernel, _adapter(fake))

    assert (
        caught.value.failure_stage
        == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    )
    assert (
        caught.value.failure_code
        == SearchPlannerModelAdapterFailureCode.INVALID_JSON
    )
    assert caught.value.mechanical_rule_id == "M01"
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []


def _assert_strict_json_parsing_failure(
    raw: str,
    *,
    clean_json_response: Callable[[str], str] | None = None,
    forbidden_fragments: tuple[str, ...] = (),
) -> None:
    kernel = _kernel()
    fake = FakeAskModel(raw)

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(fake, clean_json_response=clean_json_response))

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_JSON
    assert caught.value.mechanical_rule_id == "M01"
    assert caught.value.failure_stage != SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    for fragment in forbidden_fragments:
        assert fragment not in str(caught.value)
    assert len(fake.calls) == 1
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []


@pytest.mark.parametrize(
    ("token", "raw"),
    (
        (
            "NaN",
            '{"raw-input-sentinel": "raw-input-value", "nonfinite-member": NaN}',
        ),
        (
            "Infinity",
            '{"outer": {"raw-input-sentinel": "raw-input-value", "nonfinite-member": Infinity}}',
        ),
        (
            "-Infinity",
            '{"items": [{"raw-input-sentinel": "raw-input-value", "nonfinite-member": -Infinity}]}',
        ),
    ),
    ids=("top_level", "nested_object", "array_object"),
)
def test_nonfinite_json_constants_fail_at_the_parser_boundary(
    token: str,
    raw: str,
) -> None:
    _assert_strict_json_parsing_failure(
        raw,
        forbidden_fragments=(token, "raw-input-sentinel", "raw-input-value"),
    )


def _top_level_duplicate_output(first: str, second: str) -> str:
    raw = json.dumps(_planner_output())
    original = '"material_ambiguity_posture": "clear"'
    replacement = (
        '"raw-input-sentinel": "raw-input-value", '
        f'"material_ambiguity_posture": {json.dumps(first)}, '
        f'"material_ambiguity_posture": {json.dumps(second)}'
    )
    assert original in raw
    return raw.replace(original, replacement, 1)


@pytest.mark.parametrize(
    ("first", "second"),
    (
        ("clear", "synthetic-invalid-value"),
        ("synthetic-invalid-value", "clear"),
    ),
    ids=("valid_then_invalid", "invalid_then_valid"),
)
def test_top_level_duplicate_members_fail_before_validation_in_both_orders(
    first: str,
    second: str,
) -> None:
    _assert_strict_json_parsing_failure(
        _top_level_duplicate_output(first, second),
        forbidden_fragments=(
            "raw-input-sentinel",
            "raw-input-value",
            "synthetic-invalid-value",
        ),
    )


def test_nested_duplicate_member_fails_at_the_parser_boundary() -> None:
    _assert_strict_json_parsing_failure(
        '{"outer": {"duplicate-member-sentinel": "first-value", '
        '"duplicate-member-sentinel": "second-value"}}',
        forbidden_fragments=(
            "duplicate-member-sentinel",
            "first-value",
            "second-value",
        ),
    )


def test_duplicate_member_inside_array_object_fails_at_the_parser_boundary() -> None:
    _assert_strict_json_parsing_failure(
        '{"items": [{"duplicate-member-sentinel": "first-value", '
        '"duplicate-member-sentinel": "second-value"}]}',
        forbidden_fragments=(
            "duplicate-member-sentinel",
            "first-value",
            "second-value",
        ),
    )


def test_unique_member_strict_json_reaches_ordinary_adapter_validation() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps({"question_meaning_summary": "unique-member control"}))

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(fake))

    assert (
        caught.value.failure_stage
        == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    )
    assert (
        caught.value.failure_code
        == SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert caught.value.mechanical_rule_id == "M01"


def test_benign_response_cleaning_preserves_valid_strict_json() -> None:
    kernel = _kernel()
    cleaned = json.dumps(_planner_output())
    fake = FakeAskModel("prefix:" + cleaned)

    _produce(
        kernel,
        _adapter(
            fake,
            clean_json_response=lambda text: text.removeprefix("prefix:"),
        ),
    )

    assert kernel.state.search_planner_proposal_state["owner"] == "RunKernel.SearchPlannerProposal"


@pytest.mark.parametrize(
    "cleaned_output",
    (
        '{"duplicate-member-sentinel": "first-value", '
        '"duplicate-member-sentinel": "second-value"}',
        '{"nonfinite-member": NaN}',
    ),
    ids=("duplicate_member", "nonfinite_constant"),
)
def test_response_cleaning_cannot_bypass_strict_json_parsing(
    cleaned_output: str,
) -> None:
    _assert_strict_json_parsing_failure(
        "raw-cleaner-input-sentinel",
        clean_json_response=lambda _text: cleaned_output,
        forbidden_fragments=(
            "raw-cleaner-input-sentinel",
            "duplicate-member-sentinel",
            "first-value",
            "second-value",
            "NaN",
        ),
    )


def test_schema_invalid_model_output_fails_before_observation() -> None:
    kernel = _kernel()
    invalid = deepcopy(_planner_output())
    invalid.pop("answer_components")
    fake = FakeAskModel(json.dumps(invalid))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="missing required fields",
    ) as caught:
        _produce(kernel, _adapter(fake))

    assert (
        caught.value.failure_stage
        == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    )
    assert (
        caught.value.failure_code
        == SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert caught.value.mechanical_rule_id == "M01"
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


def test_model_adapter_preserves_query_strategy_and_recon_metadata() -> None:
    kernel = _kernel()
    output = _planner_output()
    strategy = output["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]
    strategy["recon_requirement"] = {
        "posture": "optional",
        "unresolved_dimension_ids": ["dimension:program-alias"],
        "candidate_queries": [
            {
                "dimension_id": "dimension:program-alias",
                "candidate_query_text": "Example Permit former current name",
                "query_kind": "disambiguation_probe",
            }
        ],
        "required_for_truthful_targeting": False,
    }
    fake = FakeAskModel(json.dumps(output))

    _produce(kernel, _adapter(fake))

    preserved = kernel.state.search_planner_proposal_projection[
        "component_search_requirements"
    ][0]["metadata"]["query_strategy_candidates"][0]
    assert preserved["candidate_query_text"] == (
        "Example Permit official filing threshold 2026"
    )
    assert preserved["recon_posture"] == "optional"
    assert preserved["recon_unresolved_dimension_ids"] == [
        "dimension:program-alias"
    ]
    assert preserved["recon_candidate_queries_by_dimension"] == {
        "dimension:program-alias": "Example Permit former current name"
    }


def test_model_output_executing_component_requirement_fails_closed() -> None:
    kernel = _kernel()
    unsafe = deepcopy(_planner_output())
    unsafe["component_search_requirements"][0]["search_executed"] = True
    fake = FakeAskModel(json.dumps(unsafe))

    with pytest.raises(SearchPlannerModelAdapterError, match="closed runtime surfaces"):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("obligation_kind", "invented_model_obligation"),
        ("strictness", "model_decides_if_needed"),
    ),
)
def test_model_output_with_invented_source_obligation_enum_fails_before_observation(
    field: str,
    value: str,
) -> None:
    kernel = _kernel()
    invalid = deepcopy(_planner_output())
    invalid["source_obligation_candidates"][0][field] = value
    fake = FakeAskModel(json.dumps(invalid))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match=f"unsupported value for {field}",
    ):
        _produce(kernel, _adapter(fake))

    assert len(fake.calls) == 1
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}


# New parity tests are phase_focus / component_harness_proof. They guard the
# current product-consumed adapter contract and remain out of fast_pr because
# they are detailed schema coverage rather than a broad execution sentinel.
def test_model_prompt_embeds_the_exact_output_contract_and_version() -> None:
    planner_input = _planner_input(_kernel()).to_adapter_payload()
    prompt = search_planner_model_prompt.build_search_planner_model_prompt(planner_input)
    prompt_packet = json.loads(prompt.split("Sanitized planner input JSON:\n", 1)[1])

    assert (
        SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
        == "search_planner_model_prompt_ag_search_planner_model_01_v2"
    )
    assert (
        SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION
        == "search_planner_model_adapter_ag_search_planner_model_01_v1"
    )
    assert prompt_packet["schema_version"] == SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
    assert (
        prompt_packet["output_schema"]
        == search_planner_model_prompt.SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA
    )
    assert (
        "Every enum field must use an exact value listed in output_schema. "
        "Every required object or array must satisfy its declared type and "
        "cardinality. Omit an optional field rather than inventing an unsupported "
        "value."
    ) in prompt


def test_visible_output_contract_and_adapter_contract_constants_stay_in_lockstep() -> None:
    schema = search_planner_model_prompt.SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA
    top_level = schema["top_level"]

    assert top_level["required_fields"] == list(
        search_planner_model_prompt.SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert set(top_level["fields"]) == {
        *search_planner_model_prompt.SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS,
        *search_planner_model_prompt.SEARCH_PLANNER_MODEL_OPTIONAL_TOP_LEVEL_FIELDS,
    }

    enum_contracts = (
        (
            "_SEMANTIC_SLOT_KINDS",
            ("semantic_slot", "fields", "slot_kind", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
        ),
        (
            "_SEMANTIC_SLOT_STATUSES",
            ("semantic_slot", "fields", "status", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
        ),
        (
            "_MATERIALITY_VALUES",
            ("semantic_slot", "fields", "materiality", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
        ),
        (
            "_MATERIALITY_VALUES",
            ("answer_component", "fields", "materiality", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
        ),
        (
            "_REQUIREMENT_POSTURES",
            ("answer_component", "fields", "requirement_posture", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES,
        ),
        (
            "_COMPONENT_PURPOSES",
            ("answer_component", "fields", "component_purpose", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
        ),
        (
            "_SUPPORT_KINDS",
            (
                "answer_component",
                "fields",
                "allowed_support_kinds",
                "items",
                "exact_values",
            ),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
        ),
        (
            "_PARTIAL_ANSWER_POLICIES",
            ("answer_component", "fields", "partial_answer_policy", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
        ),
        (
            "_SOURCE_OBLIGATION_KINDS",
            (
                "source_obligation_candidate",
                "fields",
                "obligation_kind",
                "exact_values",
            ),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
        ),
        (
            "_SOURCE_OBLIGATION_STRICTNESSES",
            (
                "source_obligation_candidate",
                "fields",
                "strictness",
                "exact_values",
            ),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
        ),
        (
            "_QUERY_CANDIDATE_KINDS",
            ("query_strategy_candidate", "fields", "candidate_kind", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS,
        ),
        (
            "_QUERY_ROLES",
            ("query_strategy_candidate", "fields", "requested_role", "exact_values"),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_QUERY_ROLES,
        ),
        (
            "_RECON_POSTURES",
            (
                "query_strategy_candidate",
                "fields",
                "recon_requirement",
                "fields",
                "posture",
                "exact_values",
            ),
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_RECON_POSTURES,
        ),
    )
    for adapter_constant, schema_path, expected_values in enum_contracts:
        assert getattr(search_planner_model_adapter, adapter_constant) is expected_values
        assert set(_schema_path(schema, *schema_path)) == set(expected_values)

    assert (
        search_planner_model_adapter._TOP_LEVEL_REQUIRED
        is search_planner_model_prompt.SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert (
        search_planner_model_adapter.SEARCH_PLANNER_MODEL_TEXT_LIMITS
        is search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS
    )
    assert (
        _schema_path(
            schema,
            "answer_component_cross_field_conditions",
        )[3]["allowed_support_kinds"]["exact_ordered_combinations"]
        == [
            list(item)
            for item in search_planner_model_prompt.SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS
        ]
    )

    expected_required_fields = {
        "semantic_slot": ("slot_id", "slot_kind", "status", "materiality"),
        "answer_component": (
            "component_id",
            "component_revision",
            "component_purpose",
            "user_facing_label",
            "user_facing_question",
            "requirement_posture",
            "acceptance_criteria",
            "semantic_slot_ids",
            "allowed_support_kinds",
            "max_inference_depth",
            "materiality",
        ),
        "source_obligation_candidate": (
            "candidate_id",
            "obligation_kind",
            "component_candidate_ids",
        ),
        "component_search_requirement": (
            "component_id",
            "requirement_id",
            "requirement_summary",
            "source_obligation_candidate_ids",
            "metadata",
        ),
        "query_strategy_candidate": (
            "strategy_id",
            "component_id",
            "candidate_kind",
            "candidate_query_text",
            "requested_role",
            "source_obligation_candidate_ids",
            "distinct_need_justification",
            "recon_requirement",
        ),
        "recon_candidate_query": (
            "dimension_id",
            "candidate_query_text",
            "query_kind",
        ),
        "relationship_hypothesis": (
            "hypothesis_id",
            "target_component_id",
            "premise_component_ids",
            "relationship_summary",
        ),
    }
    for contract_name, required_fields in expected_required_fields.items():
        assert schema[contract_name]["required_fields"] == list(required_fields)

    assert top_level["fields"]["semantic_slots"] == {
        "json_type": "array",
        "required": True,
        "minimum_items": 1,
        "item_contract": "semantic_slot",
    }
    assert top_level["fields"]["answer_components"]["minimum_items"] == 1
    assert (
        top_level["fields"]["answer_components"]["maximum_items"]
        == search_planner_model_adapter.SEARCH_PLANNER_MAX_ANSWER_COMPONENTS
    )
    assert (
        top_level["fields"]["relationship_hypotheses"]["maximum_items"]
        == search_planner_model_adapter.SEARCH_PLANNER_MAX_ANSWER_COMPONENTS
    )
    assert (
        schema["answer_component"]["fields"]["max_inference_depth"]
        == {
            "json_type": "integer",
            "required": True,
            "minimum": 0,
            "adapter_normalization": (
                "adapter accepts integer-coercible values; emit a JSON integer"
            ),
        }
    )
    assert schema["semantic_slot_cross_field_conditions"] == [
        {
            "if": {
                "materiality": "material",
                "status": {"one_of": ["ambiguous", "unresolved"]},
            },
            "then": {"user_confirmation_required": True},
        }
    ]
    assert schema["answer_component_cross_field_conditions"][:3] == [
        {
            "if": {"allowed_support_kinds": ["direct"]},
            "then": {
                "max_inference_depth": {"equals": 0},
                "source_obligation_candidate_ids": {"exact_item_count": 1},
            },
        },
        {
            "if": {"allowed_support_kinds": ["inferred"]},
            "then": {
                "max_inference_depth": {"minimum": 1},
                "dependency_component_ids": {"minimum_nonempty_items": 1},
                "source_obligation_candidate_ids": {"exact_item_count": 0},
            },
        },
        {
            "if": {"allowed_support_kinds": ["direct", "inferred"]},
            "then": {
                "max_inference_depth": {"minimum": 1},
                "dependency_component_ids": {"minimum_nonempty_items": 1},
                "source_obligation_candidate_ids": {"exact_item_count": 1},
            },
        },
    ]
    assert schema["component_search_requirement_cross_field_conditions"] == [
        {
            "for_each_component_where": {
                "allowed_support_kinds": ["inferred"]
            },
            "then": {
                "owned_component_search_requirements": {"exact_item_count": 0}
            },
        },
        {
            "for_each_component_where": {
                "requirement_posture": "required",
                "allowed_support_kinds_contains": "direct",
            },
            "then": {
                "owned_query_strategy_candidates": {
                    "candidate_kind": "primary",
                    "exact_item_count": 1,
                }
            },
        },
    ]
    assert schema["query_strategy_candidate_cross_field_conditions"] == [
        {
            "component_id": {
                "must_equal": "parent component_search_requirement.component_id"
            }
        },
        {
            "source_obligation_candidate_ids": {
                "each_item_must_reference": "source_obligation_candidate.candidate_id"
            }
        },
    ]

    array_contracts = (
        (("top_level", "fields", "semantic_slots"), True, "minimum_items", 1),
        (("top_level", "fields", "answer_components"), True, "minimum_items", 1),
        (
            ("top_level", "fields", "source_obligation_candidates"),
            True,
            "minimum_items",
            1,
        ),
        (
            ("top_level", "fields", "component_search_requirements"),
            True,
            "minimum_items",
            1,
        ),
        (
            ("top_level", "fields", "relationship_hypotheses"),
            False,
            "minimum_items",
            0,
        ),
        (
            ("top_level", "fields", "contract_amendment_candidates"),
            False,
            "minimum_items",
            0,
        ),
        (
            ("top_level", "fields", "mandatory_caveats"),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("top_level", "fields", "prohibited_upgrades"),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("top_level", "fields", "normalization_obligations"),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("top_level", "fields", "assumptions"),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("top_level", "fields", "unsupported_or_deferred_outputs"),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("semantic_slot", "fields", "candidate_values"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("semantic_slot", "fields", "normalization_notes"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("answer_component", "fields", "acceptance_criteria"),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            ("answer_component", "fields", "semantic_slot_ids"),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            ("answer_component", "fields", "source_obligation_candidate_ids"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("answer_component", "fields", "allowed_support_kinds"),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            ("answer_component", "fields", "dependency_component_ids"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("answer_component", "fields", "mandatory_caveats"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("answer_component", "fields", "prohibited_upgrades"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            ("source_obligation_candidate", "fields", "component_candidate_ids"),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            (
                "component_search_requirement",
                "fields",
                "source_obligation_candidate_ids",
            ),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            ("component_search_requirement", "fields", "preferred_source_kinds"),
            False,
            "minimum_nonempty_items",
            0,
        ),
        (
            (
                "component_search_requirement",
                "fields",
                "metadata",
                "fields",
                "query_strategy_candidates",
            ),
            True,
            "minimum_items",
            1,
        ),
        (
            (
                "query_strategy_candidate",
                "fields",
                "source_obligation_candidate_ids",
            ),
            True,
            "minimum_nonempty_items",
            1,
        ),
        (
            (
                "query_strategy_candidate",
                "fields",
                "recon_requirement",
                "fields",
                "unresolved_dimension_ids",
            ),
            True,
            "minimum_nonempty_items",
            0,
        ),
        (
            (
                "query_strategy_candidate",
                "fields",
                "recon_requirement",
                "fields",
                "candidate_queries",
            ),
            True,
            "minimum_items",
            0,
        ),
        (
            ("relationship_hypothesis", "fields", "premise_component_ids"),
            True,
            "minimum_nonempty_items",
            1,
        ),
    )
    for schema_path, required, cardinality_key, cardinality in array_contracts:
        contract = _schema_path(schema, *schema_path)
        assert contract["json_type"] == "array"
        assert contract["required"] is required
        assert contract[cardinality_key] == cardinality
        if "items" in contract:
            assert contract["items"]["json_type"] == "string"
        else:
            assert isinstance(contract["item_contract"], str)

    object_contract_paths = (
        ("semantic_slot",),
        ("answer_component",),
        ("source_obligation_candidate",),
        ("component_search_requirement",),
        ("query_strategy_candidate",),
        ("recon_candidate_query",),
        ("relationship_hypothesis",),
        ("contract_amendment_candidate",),
        ("component_search_requirement", "fields", "metadata"),
        ("query_strategy_candidate", "fields", "recon_requirement"),
    )
    for schema_path in object_contract_paths:
        assert _schema_path(schema, *schema_path)["json_type"] == "object"

    text_limit_contracts = (
        (
            "default_text",
            ("semantic_slot", "fields", "slot_id"),
        ),
        (
            "question_meaning_summary",
            ("top_level", "fields", "question_meaning_summary"),
        ),
        (
            "requested_output",
            ("top_level", "fields", "requested_output"),
        ),
        (
            "material_ambiguity_posture",
            ("top_level", "fields", "material_ambiguity_posture"),
        ),
        (
            "top_level_text_list_item",
            ("top_level", "fields", "mandatory_caveats", "items"),
        ),
        (
            "semantic_slot_candidate_value",
            ("semantic_slot", "fields", "candidate_values", "items"),
        ),
        (
            "semantic_slot_selected_value",
            ("semantic_slot", "fields", "selected_value"),
        ),
        (
            "semantic_slot_normalization_note",
            ("semantic_slot", "fields", "normalization_notes", "items"),
        ),
        (
            "answer_component_user_facing_label",
            ("answer_component", "fields", "user_facing_label"),
        ),
        (
            "answer_component_user_facing_question",
            ("answer_component", "fields", "user_facing_question"),
        ),
        (
            "answer_component_acceptance_criterion",
            ("answer_component", "fields", "acceptance_criteria", "items"),
        ),
        (
            "answer_component_normalization_policy",
            ("answer_component", "fields", "normalization_policy"),
        ),
        (
            "answer_component_calculation_policy",
            ("answer_component", "fields", "calculation_policy"),
        ),
        (
            "answer_component_mandatory_caveat",
            ("answer_component", "fields", "mandatory_caveats", "items"),
        ),
        (
            "answer_component_prohibited_upgrade",
            ("answer_component", "fields", "prohibited_upgrades", "items"),
        ),
        (
            "relationship_hypothesis_summary",
            ("relationship_hypothesis", "fields", "relationship_summary"),
        ),
        (
            "component_search_requirement_summary",
            ("component_search_requirement", "fields", "requirement_summary"),
        ),
        (
            "component_search_requirement_recency",
            ("component_search_requirement", "fields", "recency_requirement"),
        ),
        (
            "query_strategy_candidate_query",
            ("query_strategy_candidate", "fields", "candidate_query_text"),
        ),
        (
            "query_strategy_distinct_need_justification",
            (
                "query_strategy_candidate",
                "fields",
                "distinct_need_justification",
            ),
        ),
        (
            "recon_candidate_query",
            ("recon_candidate_query", "fields", "candidate_query_text"),
        ),
        (
            "contract_amendment_candidate_summary",
            ("contract_amendment_candidate", "fields", "summary"),
        ),
    )
    for limit_key, schema_path in text_limit_contracts:
        assert _schema_path(schema, *schema_path)["max_length"] == (
            search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS[limit_key]
        )

    with pytest.raises(TypeError):
        search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"] = 0


def test_prompt_contract_preserves_sanitized_proposal_and_typed_m02_rejections() -> None:
    valid_output = _planner_output()
    expected_sanitized = search_planner_model_adapter.validate_and_sanitize_model_output(
        deepcopy(valid_output)
    )
    produced = _adapter(FakeAskModel(json.dumps(valid_output))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )
    metadata = produced.pop("planner_model_metadata")

    assert produced == expected_sanitized
    assert sha256(
        json.dumps(produced, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest() == "6d8ee61129489cd03e2c7b35d0c93f320322772929e5ebbb51d48d610aca4f90"  # pragma: allowlist secret
    assert metadata["planner_model_prompt_schema_version"] == (
        SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
    )

    invalid_cases = (
        (
            lambda output: output["answer_components"][0].pop("user_facing_label"),
            "missing required field: user_facing_label",
            SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
        ),
        (
            lambda output: output.__setitem__("semantic_slots", {}),
            "semantic_slots must be a JSON array",
            SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE,
        ),
        (
            lambda output: output["semantic_slots"][0].__setitem__(
                "status",
                "unsupported_status",
            ),
            "unsupported value for status: unsupported_status",
            SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
        ),
        (
            lambda output: output.__setitem__("answer_components", []),
            "search planner model output requires at least one answer component",
            SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_COUNT,
        ),
        (
            lambda output: output.__setitem__("question_meaning_summary", "x" * 421),
            "required field exceeds bounded length: question_meaning_summary",
            SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
        ),
    )
    for mutate, expected_message, expected_code in invalid_cases:
        invalid_output = _planner_output()
        mutate(invalid_output)
        with pytest.raises(SearchPlannerModelAdapterError) as caught:
            _adapter(FakeAskModel(json.dumps(invalid_output))).produce(
                _planner_input(_kernel()).to_adapter_payload()
            )
        assert str(caught.value) == expected_message
        assert caught.value.failure_stage == (
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
        )
        assert caught.value.failure_code == expected_code
        assert caught.value.mechanical_rule_id == "M02"


def test_strict_type_predicate_matrix_covers_the_exact_licensed_partition() -> None:
    predicate_ids = [
        predicate_id
        for _, predicate_group in _STRICT_TYPE_PREDICATE_MATRIX
        for predicate_id in predicate_group
    ]

    assert len(predicate_ids) == 39
    assert len(set(predicate_ids)) == len(predicate_ids)
    assert set(predicate_ids) == {
        "ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM",
        "SOURCE_OBLIGATION_STRICTNESS_ENUM",
        "QUESTION_MEANING_SUMMARY_TEXT_OVER_MAX",
        "REQUESTED_OUTPUT_TEXT_OVER_MAX",
        "MATERIAL_AMBIGUITY_POSTURE_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_OVER_MAX",
        "RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_OVER_MAX",
        "COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_STATUS_TEXT_EMPTY",
        "SEMANTIC_SLOT_MATERIALITY_TEXT_EMPTY",
        "SEMANTIC_SLOT_KIND_TEXT_EMPTY",
        "ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_EMPTY",
        "ANSWER_COMPONENT_MATERIALITY_TEXT_EMPTY",
        "SOURCE_OBLIGATION_KIND_TEXT_EMPTY",
        "SEMANTIC_SLOT_STATUS_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_MATERIALITY_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_KIND_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_MATERIALITY_TEXT_OVER_MAX",
        "SOURCE_OBLIGATION_KIND_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_STATUS_VALUE_NOT_ALLOWED",
        "SEMANTIC_SLOT_MATERIALITY_VALUE_NOT_ALLOWED",
        "SEMANTIC_SLOT_KIND_VALUE_NOT_ALLOWED",
        "ANSWER_COMPONENT_REQUIREMENT_POSTURE_VALUE_NOT_ALLOWED",
        "ANSWER_COMPONENT_MATERIALITY_VALUE_NOT_ALLOWED",
        "SOURCE_OBLIGATION_KIND_VALUE_NOT_ALLOWED",
        "TOP_LEVEL_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX",
        "TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX",
        "NORMALIZATION_OBLIGATION_ITEM_TEXT_OVER_MAX",
        "ASSUMPTION_ITEM_TEXT_OVER_MAX",
        "UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_ITEM_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_TEXT_OVER_MAX",
        "SEMANTIC_SLOT_NORMALIZATION_NOTE_ITEM_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX",
        "ANSWER_COMPONENT_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX",
        "COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KIND_ITEM_TEXT_OVER_MAX",
    }
    assert "ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NO_NONEMPTY_ITEMS" not in predicate_ids


@pytest.mark.parametrize(
    ("case_name", "mutate"),
    (
        (
            "required_free_text",
            lambda output, value: output.__setitem__("question_meaning_summary", value),
        ),
        (
            "required_enum_text",
            lambda output, value: output["semantic_slots"][0].__setitem__("status", value),
        ),
        (
            "optional_free_text",
            lambda output, value: output["semantic_slots"][0].__setitem__("selected_value", value),
        ),
        (
            "optional_enum_text",
            lambda output, value: output["answer_components"][0].__setitem__(
                "partial_answer_policy",
                value,
            ),
        ),
    ),
    ids=(
        "required_free_text",
        "required_enum_text",
        "optional_free_text",
        "optional_enum_text",
    ),
)
@pytest.mark.parametrize(
    ("wrong_type", "wrong_value"),
    _STRICT_JSON_WRONG_TEXT_TYPES,
    ids=tuple(name for name, _ in _STRICT_JSON_WRONG_TEXT_TYPES),
)
def test_model_visible_scalar_wrong_types_fail_before_string_validation(
    case_name: str,
    mutate: Callable[[dict[str, Any], Any], None],
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _strict_text_type_error(mutate, wrong_value)

    assert case_name
    assert wrong_type
    assert str(error) == "model-visible text value must be a JSON string"


@pytest.mark.parametrize(
    ("field_name", "mutate"),
    (
        (
            "semantic_slot.selected_value",
            lambda output, value: output["semantic_slots"][0].__setitem__("selected_value", value),
        ),
        (
            "answer_component.normalization_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "normalization_policy",
                value,
            ),
        ),
        (
            "answer_component.calculation_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "calculation_policy",
                value,
            ),
        ),
        (
            "answer_component.partial_answer_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "partial_answer_policy",
                value,
            ),
        ),
        (
            "source_obligation_candidate.strictness",
            lambda output, value: output["source_obligation_candidates"][0].__setitem__(
                "strictness",
                value,
            ),
        ),
        (
            "component_search_requirement.recency_requirement",
            lambda output, value: output["component_search_requirements"][0].__setitem__(
                "recency_requirement",
                value,
            ),
        ),
        (
            "contract_amendment_candidate.candidate_id",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "candidate_id",
                value,
            ),
        ),
        (
            "contract_amendment_candidate.operation_kind",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "operation_kind",
                value,
            ),
        ),
        (
            "contract_amendment_candidate.summary",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "summary",
                value,
            ),
        ),
    ),
    ids=(
        "selected_value",
        "normalization_policy",
        "calculation_policy",
        "partial_answer_policy",
        "strictness",
        "recency_requirement",
        "amendment_candidate_id",
        "amendment_operation_kind",
        "amendment_summary",
    ),
)
def test_every_optional_model_visible_text_call_site_rejects_present_null(
    field_name: str,
    mutate: Callable[[dict[str, Any], Any], None],
) -> None:
    error = _strict_text_type_error(mutate, None)

    assert field_name
    assert str(error) == "model-visible text value must be a JSON string"


@pytest.mark.parametrize(
    ("field_name", "mutate"),
    (
        (
            "semantic_slot.candidate_values",
            lambda output, value: output["semantic_slots"][0].__setitem__("candidate_values", value),
        ),
        (
            "semantic_slot.normalization_notes",
            lambda output, value: output["semantic_slots"][0].__setitem__(
                "normalization_notes",
                value,
            ),
        ),
        (
            "answer_component.source_obligation_candidate_ids",
            lambda output, value: output["answer_components"][0].__setitem__(
                "source_obligation_candidate_ids",
                value,
            ),
        ),
        (
            "answer_component.dependency_component_ids",
            lambda output, value: output["answer_components"][0].__setitem__(
                "dependency_component_ids",
                value,
            ),
        ),
        (
            "answer_component.mandatory_caveats",
            lambda output, value: output["answer_components"][0].__setitem__(
                "mandatory_caveats",
                value,
            ),
        ),
        (
            "answer_component.prohibited_upgrades",
            lambda output, value: output["answer_components"][0].__setitem__(
                "prohibited_upgrades",
                value,
            ),
        ),
        (
            "component_search_requirement.preferred_source_kinds",
            lambda output, value: output["component_search_requirements"][0].__setitem__(
                "preferred_source_kinds",
                value,
            ),
        ),
    ),
    ids=(
        "candidate_values",
        "normalization_notes",
        "source_obligation_candidate_ids",
        "dependency_component_ids",
        "mandatory_caveats",
        "prohibited_upgrades",
        "preferred_source_kinds",
    ),
)
def test_every_optional_text_list_call_site_rejects_present_null(
    field_name: str,
    mutate: Callable[[dict[str, Any], Any], None],
) -> None:
    error = _strict_text_type_error(mutate, None)

    assert field_name
    assert str(error) == "expected an array of strings"


@pytest.mark.parametrize(
    ("field_name", "omit", "set_value", "result_container"),
    (
        (
            "partial_answer_policy",
            lambda output: output["answer_components"][0].pop("partial_answer_policy", None),
            lambda output, value: output["answer_components"][0].__setitem__(
                "partial_answer_policy",
                value,
            ),
            lambda proposal: proposal["answer_components"][0],
        ),
        (
            "strictness",
            lambda output: output["source_obligation_candidates"][0].pop("strictness", None),
            lambda output, value: output["source_obligation_candidates"][0].__setitem__(
                "strictness",
                value,
            ),
            lambda proposal: proposal["source_obligation_candidates"][0],
        ),
    ),
    ids=("partial_answer_policy", "strictness"),
)
def test_optional_scalar_omission_empty_and_whitespace_strings_remain_omissions(
    field_name: str,
    omit: Callable[[dict[str, Any]], None],
    set_value: Callable[[dict[str, Any], str], None],
    result_container: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> None:
    omitted = _planner_output()
    omit(omitted)
    proposal = _adapter(FakeAskModel(json.dumps(omitted))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )
    assert field_name not in result_container(proposal)

    for value in ("", "   "):
        supplied = _planner_output()
        set_value(supplied, value)
        proposal = _adapter(FakeAskModel(json.dumps(supplied))).produce(
            _planner_input(_kernel()).to_adapter_payload()
        )
        assert field_name not in result_container(proposal)


def test_optional_text_list_omission_and_empty_array_remain_omissions() -> None:
    omitted = _planner_output()
    proposal = _adapter(FakeAskModel(json.dumps(omitted))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )
    assert "candidate_values" not in proposal["semantic_slots"][0]

    empty_array = _planner_output()
    empty_array["semantic_slots"][0]["candidate_values"] = []
    proposal = _adapter(FakeAskModel(json.dumps(empty_array))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )
    assert "candidate_values" not in proposal["semantic_slots"][0]


@pytest.mark.parametrize(
    ("array_kind", "mutate"),
    (
        (
            "required_top_level_text_array",
            lambda output, value: output.__setitem__("mandatory_caveats", [value]),
        ),
        (
            "optional_semantic_slot_text_array",
            lambda output, value: output["semantic_slots"][0].__setitem__(
                "candidate_values",
                [value],
            ),
        ),
    ),
    ids=("required", "optional"),
)
@pytest.mark.parametrize(
    ("wrong_type", "wrong_value"),
    _STRICT_JSON_WRONG_TEXT_TYPES,
    ids=tuple(name for name, _ in _STRICT_JSON_WRONG_TEXT_TYPES),
)
def test_model_visible_text_array_items_reject_non_string_json_values(
    array_kind: str,
    mutate: Callable[[dict[str, Any], Any], None],
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _strict_text_type_error(mutate, wrong_value)

    assert array_kind
    assert wrong_type
    assert str(error) == "model-visible text value must be a JSON string"


def test_valid_string_arrays_remain_normalized_and_ordered() -> None:
    model_output = _planner_output()
    model_output["mandatory_caveats"] = ["  first caveat ", "second   caveat"]
    model_output["semantic_slots"][0]["candidate_values"] = ["  first value ", "second   value"]

    proposal = _adapter(FakeAskModel(json.dumps(model_output))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )

    assert proposal["mandatory_caveats"] == ["first caveat", "second caveat"]
    assert proposal["semantic_slots"][0]["candidate_values"] == [
        "first value",
        "second value",
    ]


def test_valid_string_bounds_and_enum_ownership_are_preserved() -> None:
    over_limit = _planner_output()
    over_limit["mandatory_caveats"] = [
        "x" * (search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"] + 1)
    ]
    error = _model_output_error(over_limit)
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE
    assert error.mechanical_rule_id == "M02"

    invalid_enum = _planner_output()
    invalid_enum["source_obligation_candidates"][0]["strictness"] = "not-a-strictness"
    error = _model_output_error(invalid_enum)
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE
    assert error.mechanical_rule_id == "M02"


def test_shared_text_helper_spillover_uses_type_failure_before_m03_or_m07() -> None:
    id_item_type = _strict_text_type_error(
        lambda output, value: output["answer_components"][0].__setitem__(
            "source_obligation_candidate_ids",
            [value],
        ),
        7,
    )
    assert id_item_type.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE

    missing_id = _planner_output()
    missing_id["answer_components"][0]["source_obligation_candidate_ids"] = ["missing:fictional"]
    error = _model_output_error(missing_id)
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ID_OR_CROSS_REFERENCE
    assert error.mechanical_rule_id == "M03"

    metadata_enum_type = _strict_text_type_error(
        lambda output, value: output["component_search_requirements"][0]["metadata"][
            "query_strategy_candidates"
        ][0].__setitem__("candidate_kind", value),
        7,
    )
    assert metadata_enum_type.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE

    invalid_metadata_enum = _planner_output()
    invalid_metadata_enum["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]["candidate_kind"] = "not-a-candidate-kind"
    error = _model_output_error(invalid_metadata_enum)
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_QUERY_STRATEGY_METADATA
    assert error.mechanical_rule_id == "M07"


@pytest.mark.parametrize(
    ("support_kinds", "expected_message", "forbidden_fragments"),
    (
        ([], "answer component requires allowed support kinds", ()),
        ([""], "answer component has invalid allowed support kinds", ()),
        (["   "], "answer component has invalid allowed support kinds", ()),
        (["unsupported"], "answer component has invalid allowed support kinds", ("unsupported",)),
        (["direct", ""], "answer component has invalid allowed support kinds", ()),
        (["", "direct"], "answer component has invalid allowed support kinds", ()),
        (["direct", "   "], "answer component has invalid allowed support kinds", ()),
        (
            ["direct", "unsupported"],
            "answer component has invalid allowed support kinds",
            ("unsupported",),
        ),
        (
            ["FICTIONAL_SUPPORT_KIND_PRIVATE_SENTINEL"],
            "answer component has invalid allowed support kinds",
            ("FICTIONAL_SUPPORT_KIND_PRIVATE_SENTINEL",),
        ),
    ),
    ids=(
        "empty_array",
        "empty_item",
        "whitespace_item",
        "unsupported_item",
        "empty_after_direct",
        "empty_before_direct",
        "whitespace_after_direct",
        "unsupported_after_direct",
        "private_unsupported_item",
    ),
)
def test_allowed_support_kinds_rejects_every_invalid_supplied_string_item(
    support_kinds: list[str],
    expected_message: str,
    forbidden_fragments: tuple[str, ...],
) -> None:
    error = _assert_support_kind_rejection(
        support_kinds,
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
        expected_rule="M02",
        forbidden_fragments=forbidden_fragments,
    )

    assert str(error) == expected_message


@pytest.mark.parametrize(
    ("wrong_type", "wrong_value"),
    _STRICT_JSON_WRONG_TEXT_TYPES,
    ids=tuple(name for name, _ in _STRICT_JSON_WRONG_TEXT_TYPES),
)
def test_allowed_support_kinds_rejects_each_non_string_item_before_matrix_validation(
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _assert_support_kind_rejection(
        [wrong_value],
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE,
        expected_rule="M02",
    )

    assert wrong_type
    assert str(error) == "model-visible text value must be a JSON string"


@pytest.mark.parametrize(
    ("wrong_type", "wrong_value"),
    (
        ("null", None),
        ("boolean", True),
        ("integer", 7),
        ("finite_decimal", 1.5),
        ("object", {"fictional": "value"}),
        ("string", "direct"),
    ),
    ids=("null", "boolean", "integer", "finite_decimal", "object", "string"),
)
def test_allowed_support_kinds_requires_a_json_array_container(
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _assert_support_kind_rejection(
        wrong_value,
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE,
        expected_rule="M02",
    )

    assert wrong_type
    assert str(error) == "allowed_support_kinds must be a JSON array"


def test_allowed_support_kinds_missing_field_keeps_the_existing_m02_owner() -> None:
    kernel = _kernel()
    model_output = _planner_output()
    model_output["answer_components"][0].pop("allowed_support_kinds")

    error = _model_output_error(model_output, kernel=kernel)

    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD
    assert error.mechanical_rule_id == "M02"
    assert error.__cause__ is None
    assert error.__context__ is None
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []


@pytest.mark.parametrize(
    ("support_kinds", "expected_index"),
    (
        (["direct"], 0),
        (["inferred"], 1),
        (["direct", "inferred"], 1),
    ),
    ids=("direct", "inferred", "mixed"),
)
def test_allowed_support_kinds_valid_tuples_remain_accepted_in_compatible_components(
    support_kinds: list[str],
    expected_index: int,
) -> None:
    model_output, component_index = _planner_output_with_support_kind_variant(support_kinds)

    proposal = _adapter(FakeAskModel(json.dumps(model_output))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )

    assert component_index == expected_index
    assert proposal["answer_components"][component_index]["allowed_support_kinds"] == support_kinds


def test_allowed_support_kinds_preserves_existing_string_normalization_and_order() -> None:
    model_output, component_index = _planner_output_with_support_kind_variant(["direct", "inferred"])
    model_output["answer_components"][component_index]["allowed_support_kinds"] = [
        "  direct ",
        " inferred  ",
    ]

    proposal = _adapter(FakeAskModel(json.dumps(model_output))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )

    assert proposal["answer_components"][component_index]["allowed_support_kinds"] == [
        "direct",
        "inferred",
    ]


@pytest.mark.parametrize(
    "support_kinds",
    (
        ["direct", "direct"],
        ["inferred", "inferred"],
        ["inferred", "direct"],
    ),
    ids=("duplicate_direct", "duplicate_inferred", "reversed"),
)
def test_allowed_support_kinds_valid_items_with_invalid_tuples_keep_m05(
    support_kinds: list[str],
) -> None:
    _assert_support_kind_rejection(
        support_kinds,
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_SUPPORT_MATRIX,
        expected_rule="M05",
    )


def test_allowed_support_kinds_valid_tuple_with_invalid_component_matrix_keeps_m05() -> None:
    _assert_support_kind_rejection(
        ["direct"],
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_SUPPORT_MATRIX,
        expected_rule="M05",
        configure_component=lambda component: component.__setitem__("max_inference_depth", 1),
    )


def test_allowed_support_kinds_invalid_item_wins_before_component_matrix_validation() -> None:
    rejected_marker = "FICTIONAL_INVALID_SUPPORT_KIND_PRIVATE_SENTINEL"
    error = _assert_support_kind_rejection(
        ["direct", rejected_marker],
        expected_code=SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
        expected_rule="M02",
        configure_component=lambda component: component.__setitem__("max_inference_depth", 1),
        forbidden_fragments=(rejected_marker,),
    )

    assert str(error) == "answer component has invalid allowed support kinds"


def test_allowed_support_kinds_repair_preserves_unrelated_text_array_empty_item_behavior() -> None:
    model_output = _planner_output()
    model_output["mandatory_caveats"] = ["valid text", ""]

    proposal = _adapter(FakeAskModel(json.dumps(model_output))).produce(
        _planner_input(_kernel()).to_adapter_payload()
    )

    assert proposal["mandatory_caveats"] == ["valid text"]


def test_allowed_support_kinds_empty_string_item_behavior_remains_deferred() -> None:
    _strict_text_type_error(
        lambda output, value: output["answer_components"][0].__setitem__(
            "allowed_support_kinds",
            [value],
        ),
        None,
    )

    whitespace_item = _planner_output()
    whitespace_item["answer_components"][0]["allowed_support_kinds"] = ["   "]
    error = _model_output_error(whitespace_item)
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE
    assert error.mechanical_rule_id == "M02"


def test_wrong_type_errors_are_generic_and_do_not_retain_rejected_material() -> None:
    rejected_marker = "FICTIONAL_REJECTED_TYPE_PRIVATE_SENTINEL"
    kernel = _kernel()
    error = _strict_text_type_error(
        lambda output, value: output.__setitem__("question_meaning_summary", value),
        {"nested": [rejected_marker]},
        kernel=kernel,
    )

    assert rejected_marker not in str(error)
    assert rejected_marker not in repr(error)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []
    assert rejected_marker not in repr(kernel.state)


def test_model_query_strategy_cannot_select_provider_or_model() -> None:
    kernel = _kernel()
    unsafe = _planner_output()
    strategy = unsafe["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]
    strategy["provider_name"] = "untrusted-provider"
    strategy["model_selector"] = "untrusted-model"
    fake = FakeAskModel(json.dumps(unsafe))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="forbidden provider/model authority",
    ):
        _produce(kernel, _adapter(fake))

    assert kernel.state.search_planner_proposal_state == {}


def test_adapter_failure_code_inventory_is_stable_and_repository_owned() -> None:
    assert {
        item.value for item in SearchPlannerModelAdapterFailureCode
    } == {
        "ADAPTER_DISABLED",
        "ROUTE_UNAVAILABLE",
        "INPUT_CONSTRUCTION_FAILED",
        "MODEL_CALL_FAILED",
        "OUTPUT_CLEANING_FAILED",
        "INVALID_JSON",
        "JSON_VALUE_NOT_OBJECT",
        "MISSING_REQUIRED_TOP_LEVEL_FIELDS",
        "MISSING_REQUIRED_NESTED_FIELD",
        "INVALID_NESTED_TYPE",
        "INVALID_ENUM_OR_BOUNDED_VALUE",
        "INVALID_COMPONENT_COUNT",
        "INVALID_COMPONENT_SUPPORT_MATRIX",
        "INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION",
        "INVALID_ID_OR_CROSS_REFERENCE",
        "INVALID_DEPENDENCY_OR_INFERENCE_DEPTH",
        "INVALID_QUERY_STRATEGY_METADATA",
        "CLOSED_AUTHORITY_VIOLATION",
        "PRIVACY_OR_RAW_MATERIAL_VIOLATION",
        "LINEAGE_OR_BINDING_FAILURE",
    }


def test_every_adapter_error_construction_supplies_a_registered_code() -> None:
    tree = ast.parse(_text(ADAPTER_MODULE))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SearchPlannerModelAdapterError"
    ]
    assert calls
    for call in calls:
        keyword_names = {item.arg for item in call.keywords}
        assert "failure_code" in keyword_names

    expected_rules = {
        SearchPlannerModelAdapterFailureCode.INVALID_JSON: "M01",
        SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT: "M01",
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS: "M01",
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_COUNT: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_ID_OR_CROSS_REFERENCE: "M03",
        SearchPlannerModelAdapterFailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH: "M04",
        SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_SUPPORT_MATRIX: "M05",
        SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION: "M06",
        SearchPlannerModelAdapterFailureCode.INVALID_QUERY_STRATEGY_METADATA: "M07",
        SearchPlannerModelAdapterFailureCode.CLOSED_AUTHORITY_VIOLATION: "M08",
        SearchPlannerModelAdapterFailureCode.PRIVACY_OR_RAW_MATERIAL_VIOLATION: "M09",
        SearchPlannerModelAdapterFailureCode.LINEAGE_OR_BINDING_FAILURE: "M10",
    }
    for code in SearchPlannerModelAdapterFailureCode:
        error = SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=code,
        )
        assert isinstance(
            error.failure_stage,
            SearchPlannerModelAdapterFailureStage,
        )
        assert error.mechanical_rule_id == expected_rules.get(code)


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

    pipeline_source = _text(PIPELINE)
    assert "execute_initial_query_strategy_convergence(" in pipeline_source
    assert "planner_adapter = deps.search_planner_adapter" in pipeline_source
    assert "planner_adapter = SearchPlannerModelAdapter(" in pipeline_source
    assert "DeterministicSearchPlannerAdapter()" not in pipeline_source
    assert "execute_query_production_action(" not in pipeline_source


def test_docs_record_product_consumed_passive_search_planner_posture() -> None:
    required = (
        "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01",
        "SearchPlanner proposals remain passive",
        "RunKernel initial AnswerContract acceptance",
        "No live provider, model, search, recon, fetch/read, or retrieval call was made",
    )
    forbidden = (
        "live validation is now next",
        "SearchPlanner executes search",
        "SearchPlanner mutates current_answer_contract",
        "model output satisfies source obligations",
        "model planner creates final answer",
        "Author is invoked by planner",
        "SearchPlanner admits executable queries",
        "SearchPlanner selects providers",
    )
    for path in DOCS:
        text = " ".join(_text(path).split())
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
