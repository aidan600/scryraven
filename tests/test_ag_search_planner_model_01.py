from __future__ import annotations

import ast
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

import pytest

import core.search_planner_model_adapter as search_planner_model_adapter
import core.search_planner_model_prompt as search_planner_model_prompt
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_planner_model_adapter import (
    SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION,
    SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY,
    SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION,
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
    SearchPlannerModelAdapterFailureMetadata,
    SearchPlannerModelAdapterFailureStage,
    SearchPlannerModelAdapterPredicateId,
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

_REQUIRED_NARRATIVE_TEXT_NORMALIZATION = (
    "Whitespace is normalized before validation: leading and trailing whitespace is "
    "removed, internal whitespace runs are collapsed to one space, and the normalized "
    "text must contain at least one non-whitespace character. max_length applies to the "
    "normalized text."
)
_REQUIRED_NARRATIVE_TEXT_PROMPT_RULE = (
    "The seven required narrative fields must contain meaningful non-whitespace text "
    "after whitespace normalization; never emit empty or whitespace-only values, and "
    "keep normalized text within each declared max_length."
)
_NARRATIVE_TEXT_REJECTED_SENTINEL = "FICTIONAL_NARRATIVE_TEXT_REJECTED_SENTINEL"

_NarrativeTextField = tuple[
    str,
    tuple[str | int, ...],
    tuple[str, ...],
    str,
    int,
    SearchPlannerModelAdapterFailureCode,
    str,
    str,
]

_REQUIRED_NARRATIVE_TEXT_FIELDS: tuple[_NarrativeTextField, ...] = (
    (
        "top_level.question_meaning_summary",
        ("question_meaning_summary",),
        ("top_level", "fields", "question_meaning_summary"),
        "question_meaning_summary",
        420,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS,
        "M01",
        "QUESTION_MEANING_SUMMARY_TEXT_EMPTY",
    ),
    (
        "top_level.requested_output",
        ("requested_output",),
        ("top_level", "fields", "requested_output"),
        "requested_output",
        300,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS,
        "M01",
        "REQUESTED_OUTPUT_TEXT_EMPTY",
    ),
    (
        "top_level.material_ambiguity_posture",
        ("material_ambiguity_posture",),
        ("top_level", "fields", "material_ambiguity_posture"),
        "material_ambiguity_posture",
        120,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS,
        "M01",
        "MATERIAL_AMBIGUITY_POSTURE_TEXT_EMPTY",
    ),
    (
        "answer_component.user_facing_label",
        ("answer_components", 0, "user_facing_label"),
        ("answer_component", "fields", "user_facing_label"),
        "answer_component_user_facing_label",
        180,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
        "M02",
        "ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_EMPTY",
    ),
    (
        "answer_component.user_facing_question",
        ("answer_components", 0, "user_facing_question"),
        ("answer_component", "fields", "user_facing_question"),
        "answer_component_user_facing_question",
        400,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
        "M02",
        "ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_EMPTY",
    ),
    (
        "relationship_hypothesis.relationship_summary",
        ("relationship_hypotheses", 0, "relationship_summary"),
        ("relationship_hypothesis", "fields", "relationship_summary"),
        "relationship_hypothesis_summary",
        360,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
        "M02",
        "RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_EMPTY",
    ),
    (
        "component_search_requirement.requirement_summary",
        ("component_search_requirements", 0, "requirement_summary"),
        ("component_search_requirement", "fields", "requirement_summary"),
        "component_search_requirement_summary",
        320,
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
        "M02",
        "COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_EMPTY",
    ),
)

_CONTINUITY_TAIL_PREDICATE_IDS = (
    "ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NO_NONEMPTY_ITEMS",
    "ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_NO_NONEMPTY_ITEMS",
    "SEMANTIC_SLOTS_MINIMUM_ITEMS_1",
    "RELATIONSHIP_HYPOTHESES_MAXIMUM_ITEMS_5",
    "SOURCE_OBLIGATION_CANDIDATES_MINIMUM_ITEMS_1",
    "SEMANTIC_SLOT_STATUS_MISSING",
    "SEMANTIC_SLOT_MATERIALITY_MISSING",
    "SEMANTIC_SLOT_KIND_MISSING",
    "ANSWER_COMPONENT_REQUIREMENT_POSTURE_MISSING",
    "ANSWER_COMPONENT_MATERIALITY_MISSING",
    "SOURCE_OBLIGATION_KIND_MISSING",
)
_CONTINUITY_SEED_IDS = tuple(
    SearchPlannerModelAdapterPredicateId(predicate_id)
    for predicate_id in (
        *(predicate_id for _, predicate_group in _STRICT_TYPE_PREDICATE_MATRIX for predicate_id in predicate_group),
        *(field[7] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
        *_CONTINUITY_TAIL_PREDICATE_IDS,
    )
)

_NARRATIVE_WRONG_TEXT_TYPES: tuple[tuple[str, Any], ...] = (
    ("null", None),
    ("boolean", True),
    ("integer", 7),
    ("object", {"fictional_value": _NARRATIVE_TEXT_REJECTED_SENTINEL}),
    ("array", [_NARRATIVE_TEXT_REJECTED_SENTINEL]),
)

_NARRATIVE_EMPTY_TEXT_CASES: tuple[tuple[str, str], ...] = (
    ("empty", ""),
    ("space", " "),
    ("spaces", "   "),
    ("tab", "\t"),
    ("newline", "\n"),
    ("mixed_whitespace", " \t \n "),
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
        "question_meaning_summary": ("Determine the official current threshold and preserve source-bound caveats."),
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
                "user_facing_question": ("What is the official current filing threshold for the requested program?"),
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
                            "candidate_query_text": ("Example Permit official filing threshold 2026"),
                            "requested_role": "official_bias",
                            "source_obligation_candidate_ids": ["obligation:model-official-current"],
                            "distinct_need_justification": ("Primary query for the accepted threshold component."),
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


def _sparse_planner_output() -> dict[str, Any]:
    return {
        "disposition": "components",
        "components": [
            {
                "need": "Report the official current filing threshold",
                "source": {"kind": "official_current", "strictness": "required"},
                "freshness": "current for 2026",
                "caveat": "Keep the answer source-bound.",
            }
        ],
    }


def _narrative_text_model_output(field_path: tuple[str | int, ...]) -> dict[str, Any]:
    payload = _planner_output()
    if field_path[0] == "relationship_hypotheses":
        payload["relationship_hypotheses"] = [
            {
                "hypothesis_id": "hypothesis:model-official-threshold",
                "target_component_id": "component:model-official-threshold",
                "premise_component_ids": ["component:model-official-threshold"],
                "relationship_summary": "The official source determines the answer component.",
            }
        ]
    return payload


def _narrative_text_field_container(
    payload: dict[str, Any],
    field_path: tuple[str | int, ...],
) -> dict[str, Any]:
    container: Any = payload
    for segment in field_path[:-1]:
        container = container[segment]
    assert isinstance(container, dict)
    return container


def _set_narrative_text_field(
    payload: dict[str, Any],
    field_path: tuple[str | int, ...],
    value: Any,
) -> None:
    field_name = field_path[-1]
    assert isinstance(field_name, str)
    _narrative_text_field_container(payload, field_path)[field_name] = value


def _pop_narrative_text_field(
    payload: dict[str, Any],
    field_path: tuple[str | int, ...],
) -> Any:
    field_name = field_path[-1]
    assert isinstance(field_name, str)
    return _narrative_text_field_container(payload, field_path).pop(field_name)


def _narrative_text_field_value(
    payload: Mapping[str, Any],
    field_path: tuple[str | int, ...],
) -> Any:
    value: Any = payload
    for segment in field_path:
        value = value[segment]
    return value


def _assert_rejected_narrative_text_is_not_retained(
    error: SearchPlannerModelAdapterError,
    kernel: RunKernel,
    *,
    submitted_values: tuple[str, ...] = (),
) -> None:
    assert error.__cause__ is None
    assert error.__context__ is None
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []
    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert '"raw_prompt":' not in trace_json
    assert '"raw_model_response":' not in trace_json
    assert '"raw_provider_payload":' not in trace_json
    assert '"provider_payload":' not in trace_json
    for submitted_value in submitted_values:
        assert submitted_value not in str(error)
        assert submitted_value not in repr(error)
        assert submitted_value not in repr(error.args)
        assert submitted_value not in repr(kernel.state)
        assert submitted_value not in trace_json


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
        if "answer_components" in model_output or "source_obligation_candidates" in model_output:
            # The rich contract is compiler-internal after the sparse cutover.
            search_planner_model_adapter.validate_and_sanitize_model_output(model_output)
        else:
            _produce(
                target_kernel,
                _adapter(FakeAskModel(json.dumps(model_output))),
            )
    return caught.value


def _continuity_seed_error(
    predicate_id: SearchPlannerModelAdapterPredicateId,
) -> SearchPlannerModelAdapterError:
    """Exercise one current deterministic witness for each continuity seed."""

    model_output = _planner_output()
    over_limit_text = "x" * 10_000
    component = model_output["answer_components"][0]
    semantic_slot = model_output["semantic_slots"][0]
    source_obligation = model_output["source_obligation_candidates"][0]
    requirement = model_output["component_search_requirements"][0]

    if predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM:
        component["partial_answer_policy"] = "invalid_partial_answer_policy"
    elif predicate_id == SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_STRICTNESS_ENUM:
        source_obligation["strictness"] = "invalid_strictness"
    elif predicate_id in {
        SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX,
        SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX,
        SearchPlannerModelAdapterPredicateId.NORMALIZATION_OBLIGATION_ITEM_TEXT_OVER_MAX,
        SearchPlannerModelAdapterPredicateId.ASSUMPTION_ITEM_TEXT_OVER_MAX,
        SearchPlannerModelAdapterPredicateId.UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_TEXT_OVER_MAX,
    }:
        top_level_field = {
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX: "mandatory_caveats",
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX: "prohibited_upgrades",
            SearchPlannerModelAdapterPredicateId.NORMALIZATION_OBLIGATION_ITEM_TEXT_OVER_MAX: "normalization_obligations",
            SearchPlannerModelAdapterPredicateId.ASSUMPTION_ITEM_TEXT_OVER_MAX: "assumptions",
            SearchPlannerModelAdapterPredicateId.UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_TEXT_OVER_MAX: "unsupported_or_deferred_outputs",
        }[predicate_id]
        model_output[top_level_field] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NO_NONEMPTY_ITEMS:
        component["allowed_support_kinds"] = []
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_TEXT_OVER_MAX:
        component["allowed_support_kinds"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_ITEM_TEXT_OVER_MAX:
        component["acceptance_criteria"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_NO_NONEMPTY_ITEMS:
        component["acceptance_criteria"] = []
    elif predicate_id == SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_TEXT_OVER_MAX:
        semantic_slot["candidate_values"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NORMALIZATION_NOTE_ITEM_TEXT_OVER_MAX:
        semantic_slot["normalization_notes"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX:
        component["mandatory_caveats"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX:
        component["prohibited_upgrades"] = [over_limit_text]
    elif (
        predicate_id
        == SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KIND_ITEM_TEXT_OVER_MAX
    ):
        requirement["preferred_source_kinds"] = [over_limit_text]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOTS_MINIMUM_ITEMS_1:
        model_output["semantic_slots"] = []
    elif predicate_id == SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESES_MAXIMUM_ITEMS_5:
        model_output["relationship_hypotheses"] = [
            {
                "hypothesis_id": f"hypothesis:{index}",
                "target_component_id": "component:model-official-threshold",
                "premise_component_ids": ["component:model-official-threshold"],
                "relationship_summary": "A bounded relationship proposal.",
            }
            for index in range(6)
        ]
    elif predicate_id == SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATES_MINIMUM_ITEMS_1:
        model_output["source_obligation_candidates"] = []
    else:
        enum_targets: dict[
            SearchPlannerModelAdapterPredicateId,
            tuple[dict[str, Any], str, str],
        ] = {
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_TEXT_EMPTY: (
                semantic_slot,
                "status",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_TEXT_OVER_MAX: (
                semantic_slot,
                "status",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_VALUE_NOT_ALLOWED: (
                semantic_slot,
                "status",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_MISSING: (
                semantic_slot,
                "status",
                "missing",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_TEXT_EMPTY: (
                semantic_slot,
                "materiality",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_TEXT_OVER_MAX: (
                semantic_slot,
                "materiality",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_VALUE_NOT_ALLOWED: (
                semantic_slot,
                "materiality",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_MISSING: (
                semantic_slot,
                "materiality",
                "missing",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_TEXT_EMPTY: (
                semantic_slot,
                "slot_kind",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_TEXT_OVER_MAX: (
                semantic_slot,
                "slot_kind",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_VALUE_NOT_ALLOWED: (
                semantic_slot,
                "slot_kind",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_MISSING: (
                semantic_slot,
                "slot_kind",
                "missing",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_EMPTY: (
                component,
                "requirement_posture",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_OVER_MAX: (
                component,
                "requirement_posture",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_VALUE_NOT_ALLOWED: (
                component,
                "requirement_posture",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_MISSING: (
                component,
                "requirement_posture",
                "missing",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_TEXT_EMPTY: (
                component,
                "materiality",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_TEXT_OVER_MAX: (
                component,
                "materiality",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_VALUE_NOT_ALLOWED: (
                component,
                "materiality",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_MISSING: (
                component,
                "materiality",
                "missing",
            ),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_TEXT_EMPTY: (
                source_obligation,
                "obligation_kind",
                "empty",
            ),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_TEXT_OVER_MAX: (
                source_obligation,
                "obligation_kind",
                "over",
            ),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_VALUE_NOT_ALLOWED: (
                source_obligation,
                "obligation_kind",
                "invalid",
            ),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_MISSING: (
                source_obligation,
                "obligation_kind",
                "missing",
            ),
        }
        if predicate_id in enum_targets:
            target, field_name, mode = enum_targets[predicate_id]
            if mode == "missing":
                target.pop(field_name)
            elif mode == "empty":
                target[field_name] = ""
            elif mode == "over":
                target[field_name] = over_limit_text
            else:
                target[field_name] = "invalid_enum_value"
        else:
            narrative_empty_path = next(
                (field[1] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS if field[7] == predicate_id.value),
                None,
            )
            narrative_over_paths = {
                SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_TEXT_OVER_MAX: (
                    "question_meaning_summary",
                ),
                SearchPlannerModelAdapterPredicateId.REQUESTED_OUTPUT_TEXT_OVER_MAX: ("requested_output",),
                SearchPlannerModelAdapterPredicateId.MATERIAL_AMBIGUITY_POSTURE_TEXT_OVER_MAX: (
                    "material_ambiguity_posture",
                ),
                SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_OVER_MAX: (
                    "answer_components",
                    0,
                    "user_facing_label",
                ),
                SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_OVER_MAX: (
                    "answer_components",
                    0,
                    "user_facing_question",
                ),
                SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_OVER_MAX: (
                    "relationship_hypotheses",
                    0,
                    "relationship_summary",
                ),
                SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_OVER_MAX: (
                    "component_search_requirements",
                    0,
                    "requirement_summary",
                ),
            }
            if predicate_id in {
                SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_OVER_MAX,
                SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_EMPTY,
            }:
                model_output["relationship_hypotheses"] = [
                    {
                        "hypothesis_id": "hypothesis:current",
                        "target_component_id": "component:model-official-threshold",
                        "premise_component_ids": ["component:model-official-threshold"],
                        "relationship_summary": "A bounded relationship proposal.",
                    }
                ]
            if narrative_empty_path is not None:
                _set_narrative_text_field(model_output, narrative_empty_path, "")
            elif predicate_id in narrative_over_paths:
                _set_narrative_text_field(
                    model_output,
                    narrative_over_paths[predicate_id],
                    over_limit_text,
                )
            else:
                raise AssertionError(f"missing continuity witness for {predicate_id.value}")

    return _model_output_error(model_output)


_WitnessScope = Literal["field", "universal", "dynamic"]
_WitnessMetadata = tuple[
    SearchPlannerModelAdapterFailureStage,
    SearchPlannerModelAdapterFailureCode,
    str,
]
_M01_PARSE: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.JSON_PARSING,
    SearchPlannerModelAdapterFailureCode.INVALID_JSON,
    "M01",
)
_M01_ROOT_OBJECT: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.JSON_PARSING,
    SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT,
    "M01",
)
_M01_TOP_LEVEL_MISSING: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS,
    "M01",
)
_M02_INVALID_TYPE: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE,
    "M02",
)
_M02_MISSING: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD,
    "M02",
)
_M02_VALUE: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
    "M02",
)
_M02_COMPONENT_COUNT: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_COUNT,
    "M02",
)
_M02_SEMANTIC_PROPOSAL: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL,
    "M02",
)
_M03: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_ID_OR_CROSS_REFERENCE,
    "M03",
)
_M04: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH,
    "M04",
)
_M05: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_SUPPORT_MATRIX,
    "M05",
)
_M06: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION,
    "M06",
)
_M07: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.INVALID_QUERY_STRATEGY_METADATA,
    "M07",
)
_M08: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.CLOSED_AUTHORITY_VIOLATION,
    "M08",
)
_M09: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
    SearchPlannerModelAdapterFailureCode.PRIVACY_OR_RAW_MATERIAL_VIOLATION,
    "M09",
)
_M10: _WitnessMetadata = (
    SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
    SearchPlannerModelAdapterFailureCode.LINEAGE_OR_BINDING_FAILURE,
    "M10",
)
_WITNESS_UNSET = object()


@dataclass(frozen=True)
class _FieldConditionWitness:
    """One runtime-backed, sanitized-predicate attestation witness."""

    field_path: str
    condition: str
    predicate_id: SearchPlannerModelAdapterPredicateId
    failure_stage: SearchPlannerModelAdapterFailureStage
    failure_code: SearchPlannerModelAdapterFailureCode
    mechanical_rule_id: str
    scope: _WitnessScope
    emit: Callable[[], SearchPlannerModelAdapterError]


def _set_model_output_path(
    output: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    container: Any = output
    for segment in path[:-1]:
        container = container[segment]
    container[path[-1]] = deepcopy(value)


def _pop_model_output_path(
    output: dict[str, Any],
    path: tuple[str | int, ...],
) -> None:
    container: Any = output
    for segment in path[:-1]:
        container = container[segment]
    container.pop(path[-1])


def _add_relationship_hypothesis(output: dict[str, Any]) -> None:
    output["relationship_hypotheses"] = [
        {
            "hypothesis_id": "hypothesis:current",
            "target_component_id": "component:model-official-threshold",
            "premise_component_ids": ["component:model-official-threshold"],
            "relationship_summary": "A bounded relationship proposal.",
        }
    ]


def _add_contract_amendment_candidate(output: dict[str, Any]) -> None:
    output["contract_amendment_candidates"] = [{}]


def _add_recon_candidate_query(output: dict[str, Any]) -> None:
    output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0]["recon_requirement"][
        "candidate_queries"
    ] = [
        {
            "dimension_id": "dimension:currentness",
            "candidate_query_text": "Example Permit official threshold currentness",
            "query_kind": "currentness",
        }
    ]


def _path_witness(
    *,
    field_path: str,
    path: tuple[str | int, ...],
    condition: str,
    predicate_id: SearchPlannerModelAdapterPredicateId,
    metadata: _WitnessMetadata,
    value: Any = _WITNESS_UNSET,
    remove: bool = False,
    setup: Callable[[dict[str, Any]], None] | None = None,
    scope: _WitnessScope = "field",
) -> _FieldConditionWitness:
    failure_stage, failure_code, mechanical_rule_id = metadata

    def emit() -> SearchPlannerModelAdapterError:
        output = _planner_output()
        if setup is not None:
            setup(output)
        if remove:
            _pop_model_output_path(output, path)
        else:
            _set_model_output_path(output, path, value)
        return _model_output_error(output)

    return _FieldConditionWitness(
        field_path=field_path,
        condition=condition,
        predicate_id=predicate_id,
        failure_stage=failure_stage,
        failure_code=failure_code,
        mechanical_rule_id=mechanical_rule_id,
        scope=scope,
        emit=emit,
    )


def _direct_witness(
    *,
    field_path: str,
    condition: str,
    predicate_id: SearchPlannerModelAdapterPredicateId,
    metadata: _WitnessMetadata,
    emit: Callable[[], SearchPlannerModelAdapterError],
    scope: _WitnessScope = "field",
) -> _FieldConditionWitness:
    failure_stage, failure_code, mechanical_rule_id = metadata
    return _FieldConditionWitness(
        field_path=field_path,
        condition=condition,
        predicate_id=predicate_id,
        failure_stage=failure_stage,
        failure_code=failure_code,
        mechanical_rule_id=mechanical_rule_id,
        scope=scope,
        emit=emit,
    )


def _text_field_witnesses(
    *,
    field_path: str,
    path: tuple[str | int, ...],
    invalid_type: SearchPlannerModelAdapterPredicateId,
    missing: SearchPlannerModelAdapterPredicateId,
    text_over_max: SearchPlannerModelAdapterPredicateId,
    text_empty: SearchPlannerModelAdapterPredicateId,
    field_metadata: _WitnessMetadata,
    missing_metadata: _WitnessMetadata | None = None,
    value_not_allowed: SearchPlannerModelAdapterPredicateId | None = None,
    setup: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[_FieldConditionWitness, ...]:
    witnesses = [
        _path_witness(
            field_path=field_path,
            path=path,
            condition="not_json_string",
            predicate_id=invalid_type,
            metadata=_M02_INVALID_TYPE,
            value=7,
            setup=setup,
        ),
        _path_witness(
            field_path=field_path,
            path=path,
            condition="missing",
            predicate_id=missing,
            metadata=missing_metadata or field_metadata,
            remove=True,
            setup=setup,
        ),
        _path_witness(
            field_path=field_path,
            path=path,
            condition="text_over_max",
            predicate_id=text_over_max,
            metadata=field_metadata,
            value="x" * 10_000,
            setup=setup,
        ),
        _path_witness(
            field_path=field_path,
            path=path,
            condition="text_empty",
            predicate_id=text_empty,
            metadata=field_metadata,
            value="",
            setup=setup,
        ),
    ]
    if value_not_allowed is not None:
        witnesses.append(
            _path_witness(
                field_path=field_path,
                path=path,
                condition="value_not_allowed",
                predicate_id=value_not_allowed,
                metadata=field_metadata,
                value="invalid_enum_value",
                setup=setup,
            )
        )
    return tuple(witnesses)


def _text_array_witnesses(
    *,
    field_path: str,
    path: tuple[str | int, ...],
    container_invalid_type: SearchPlannerModelAdapterPredicateId,
    item_invalid_type: SearchPlannerModelAdapterPredicateId,
    item_text_over_max: SearchPlannerModelAdapterPredicateId,
    item_metadata: _WitnessMetadata,
    missing: SearchPlannerModelAdapterPredicateId | None = None,
    missing_metadata: _WitnessMetadata | None = None,
    no_nonempty_items: SearchPlannerModelAdapterPredicateId | None = None,
    no_nonempty_items_metadata: _WitnessMetadata | None = None,
    setup: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[_FieldConditionWitness, ...]:
    witnesses = [
        _path_witness(
            field_path=field_path,
            path=path,
            condition="not_json_array",
            predicate_id=container_invalid_type,
            metadata=_M02_INVALID_TYPE,
            value={},
            setup=setup,
        ),
        _path_witness(
            field_path=field_path,
            path=path,
            condition="item_not_json_string",
            predicate_id=item_invalid_type,
            metadata=_M02_INVALID_TYPE,
            value=[7],
            setup=setup,
        ),
        _path_witness(
            field_path=field_path,
            path=path,
            condition="item_text_over_max",
            predicate_id=item_text_over_max,
            metadata=item_metadata,
            value=["x" * 10_000],
            setup=setup,
        ),
    ]
    if missing is not None:
        witnesses.append(
            _path_witness(
                field_path=field_path,
                path=path,
                condition="missing",
                predicate_id=missing,
                metadata=missing_metadata or item_metadata,
                remove=True,
                setup=setup,
            )
        )
    if no_nonempty_items is not None:
        witnesses.append(
            _path_witness(
                field_path=field_path,
                path=path,
                condition="no_nonempty_items",
                predicate_id=no_nonempty_items,
                metadata=no_nonempty_items_metadata or item_metadata,
                value=[],
                setup=setup,
            )
        )
    return tuple(witnesses)


def _raw_model_output_error(raw: str) -> SearchPlannerModelAdapterError:
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(FakeAskModel(raw)).produce(_planner_input(_kernel()).to_adapter_payload())
    return caught.value


def _semantic_proposal_validation_error() -> SearchPlannerModelAdapterError:
    """Emit canonical semantic-proposal validation failure through the adapter path."""

    proposal = {
        "interpretation": "Determine the official current threshold.",
        "components": [
            {
                "purpose": "user_facing_answer_target",
                "label": "Official threshold",
                "question": "What is the official current filing threshold?",
                "requirement_posture": "required",
                "acceptance_criteria": ["state the threshold"],
                "support_kinds": ["direct"],
                "materiality": "material",
                "slots": [],
                "source": {"kind": "official_current", "strictness": "required"},
                "search": {
                    "summary": "Find the official current source for the threshold.",
                    "primary_query": {
                        "text": "Example Permit official filing threshold",
                        "role": "official_bias",
                    },
                },
            }
        ],
    }
    return _model_output_error(proposal)


def _mutated_model_output_error(
    mutate: Callable[[dict[str, Any]], None],
) -> SearchPlannerModelAdapterError:
    output = _planner_output()
    mutate(output)
    return _model_output_error(output)


def _support_matrix_error(
    *,
    support_kinds: list[str],
    max_inference_depth: int,
    source_obligation_candidate_ids: list[str],
    dependency_component_ids: list[str] | None,
) -> SearchPlannerModelAdapterError:
    output = _planner_output()
    component = output["answer_components"][0]
    component["allowed_support_kinds"] = support_kinds
    component["max_inference_depth"] = max_inference_depth
    component["source_obligation_candidate_ids"] = source_obligation_candidate_ids
    if dependency_component_ids is None:
        component.pop("dependency_component_ids", None)
    else:
        component["dependency_component_ids"] = dependency_component_ids
    return _model_output_error(output)


def _inferred_component_requirement_error() -> SearchPlannerModelAdapterError:
    output = _planner_output()
    derived_component = deepcopy(output["answer_components"][0])
    derived_component.update(
        {
            "component_id": "component:model-derived-threshold",
            "component_revision": "2",
            "user_facing_label": "Derived threshold",
            "user_facing_question": "What follows from the official threshold?",
            "requirement_posture": "optional",
            "allowed_support_kinds": ["inferred"],
            "source_obligation_candidate_ids": [],
            "dependency_component_ids": ["component:model-official-threshold"],
            "max_inference_depth": 1,
        }
    )
    output["answer_components"].append(derived_component)
    requirement = output["component_search_requirements"][0]
    requirement["component_id"] = "component:model-derived-threshold"
    requirement["metadata"]["query_strategy_candidates"][0]["component_id"] = "component:model-derived-threshold"
    return _model_output_error(output)


def _answer_components_maximum_items_error() -> SearchPlannerModelAdapterError:
    output = _planner_output()
    output["answer_components"] = [deepcopy(output["answer_components"][0]) for _ in range(6)]
    return _model_output_error(output)


def _relationship_hypotheses_maximum_items_error() -> SearchPlannerModelAdapterError:
    output = _planner_output()
    _add_relationship_hypothesis(output)
    output["relationship_hypotheses"] = [
        {
            "hypothesis_id": f"hypothesis:{index}",
            "target_component_id": "component:model-official-threshold",
            "premise_component_ids": ["component:model-official-threshold"],
            "relationship_summary": "A bounded relationship proposal.",
        }
        for index in range(6)
    ]
    return _model_output_error(output)


def _query_strategy_primary_count_error(count: int) -> SearchPlannerModelAdapterError:
    output = _planner_output()
    candidates = output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"]
    if count == 0:
        candidates[0]["candidate_kind"] = "secondary"
    elif count == 2:
        second = deepcopy(candidates[0])
        second["strategy_id"] = "strategy:model-official-threshold:secondary-primary"
        candidates.append(second)
    else:
        raise AssertionError(f"unsupported primary count witness: {count}")
    return _model_output_error(output)


def _field_condition_witness_inventory() -> tuple[_FieldConditionWitness, ...]:
    rows: list[_FieldConditionWitness] = [
        _direct_witness(
            field_path="json_document",
            condition="strict_parse_failed",
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
            metadata=_M01_PARSE,
            emit=lambda: _raw_model_output_error("{"),
            scope="universal",
        ),
        _direct_witness(
            field_path="json_document",
            condition="top_level_object_required",
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_TOP_LEVEL_OBJECT_REQUIRED,
            metadata=_M01_ROOT_OBJECT,
            emit=lambda: _raw_model_output_error("[]"),
            scope="universal",
        ),
        _direct_witness(
            field_path="semantic_proposal",
            condition="validation_failed",
            predicate_id=(SearchPlannerModelAdapterPredicateId.SEMANTIC_PROPOSAL_VALIDATION_FAILED),
            metadata=_M02_SEMANTIC_PROPOSAL,
            emit=_semantic_proposal_validation_error,
            scope="universal",
        ),
    ]
    for field_path, field_name, predicate_id in (
        (
            "top_level.semantic_slots",
            "semantic_slots",
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_SEMANTIC_SLOTS_MISSING,
        ),
        (
            "top_level.answer_components",
            "answer_components",
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_ANSWER_COMPONENTS_MISSING,
        ),
        (
            "top_level.source_obligation_candidates",
            "source_obligation_candidates",
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_SOURCE_OBLIGATION_CANDIDATES_MISSING,
        ),
        (
            "top_level.component_search_requirements",
            "component_search_requirements",
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_COMPONENT_SEARCH_REQUIREMENTS_MISSING,
        ),
    ):
        rows.append(
            _path_witness(
                field_path=field_path,
                path=(field_name,),
                condition="missing",
                predicate_id=predicate_id,
                metadata=_M01_TOP_LEVEL_MISSING,
                remove=True,
            )
        )

    rows.extend(
        _text_field_witnesses(
            field_path="top_level.question_meaning_summary",
            path=("question_meaning_summary",),
            invalid_type=SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.TOP_LEVEL_QUESTION_MEANING_SUMMARY_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_TEXT_EMPTY,
            field_metadata=_M02_VALUE,
            missing_metadata=_M01_TOP_LEVEL_MISSING,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="top_level.requested_output",
            path=("requested_output",),
            invalid_type=SearchPlannerModelAdapterPredicateId.REQUESTED_OUTPUT_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.TOP_LEVEL_REQUESTED_OUTPUT_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.REQUESTED_OUTPUT_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.REQUESTED_OUTPUT_TEXT_EMPTY,
            field_metadata=_M02_VALUE,
            missing_metadata=_M01_TOP_LEVEL_MISSING,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="top_level.material_ambiguity_posture",
            path=("material_ambiguity_posture",),
            invalid_type=SearchPlannerModelAdapterPredicateId.MATERIAL_AMBIGUITY_POSTURE_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MATERIAL_AMBIGUITY_POSTURE_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.MATERIAL_AMBIGUITY_POSTURE_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.MATERIAL_AMBIGUITY_POSTURE_TEXT_EMPTY,
            field_metadata=_M02_VALUE,
            missing_metadata=_M01_TOP_LEVEL_MISSING,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="semantic_slot.slot_id",
            path=("semantic_slots", 0, "slot_id"),
            invalid_type=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_ID_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_ID_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_ID_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_ID_TEXT_EMPTY,
            field_metadata=_M03,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="semantic_slot.status",
            path=("semantic_slots", 0, "status"),
            invalid_type=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_TEXT_EMPTY,
            value_not_allowed=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_VALUE_NOT_ALLOWED,
            field_metadata=_M02_VALUE,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="semantic_slot.materiality",
            path=("semantic_slots", 0, "materiality"),
            invalid_type=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_TEXT_EMPTY,
            value_not_allowed=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_MATERIALITY_VALUE_NOT_ALLOWED,
            field_metadata=_M02_VALUE,
        )
    )
    rows.extend(
        _text_field_witnesses(
            field_path="semantic_slot.slot_kind",
            path=("semantic_slots", 0, "slot_kind"),
            invalid_type=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_NOT_JSON_STRING,
            missing=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_MISSING,
            text_over_max=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_TEXT_OVER_MAX,
            text_empty=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_TEXT_EMPTY,
            value_not_allowed=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_KIND_VALUE_NOT_ALLOWED,
            field_metadata=_M02_VALUE,
        )
    )

    for (
        field_path,
        path,
        invalid_type,
        missing,
        text_over_max,
        text_empty,
        field_metadata,
        value_not_allowed,
        setup,
    ) in (
        (
            "answer_component.component_id",
            ("answer_components", 0, "component_id"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ID_TEXT_EMPTY,
            _M03,
            None,
            None,
        ),
        (
            "answer_component.component_revision",
            ("answer_components", 0, "component_revision"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_REVISION_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_REVISION_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_REVISION_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_REVISION_TEXT_EMPTY,
            _M10,
            None,
            None,
        ),
        (
            "answer_component.component_purpose",
            ("answer_components", 0, "component_purpose"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_TEXT_EMPTY,
            _M06,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "answer_component.user_facing_label",
            ("answer_components", 0, "user_facing_label"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_EMPTY,
            _M02_VALUE,
            None,
            None,
        ),
        (
            "answer_component.user_facing_question",
            ("answer_components", 0, "user_facing_question"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_EMPTY,
            _M02_VALUE,
            None,
            None,
        ),
        (
            "answer_component.requirement_posture",
            ("answer_components", 0, "requirement_posture"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_TEXT_EMPTY,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIREMENT_POSTURE_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "answer_component.materiality",
            ("answer_components", 0, "materiality"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_TEXT_EMPTY,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MATERIALITY_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "relationship_hypothesis.hypothesis_id",
            ("relationship_hypotheses", 0, "hypothesis_id"),
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_ID_TEXT_EMPTY,
            _M03,
            None,
            _add_relationship_hypothesis,
        ),
        (
            "relationship_hypothesis.target_component_id",
            ("relationship_hypotheses", 0, "target_component_id"),
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_TARGET_COMPONENT_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_TARGET_COMPONENT_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_TARGET_COMPONENT_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_TARGET_COMPONENT_ID_TEXT_EMPTY,
            _M03,
            None,
            _add_relationship_hypothesis,
        ),
        (
            "relationship_hypothesis.relationship_summary",
            ("relationship_hypotheses", 0, "relationship_summary"),
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_MISSING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_EMPTY,
            _M02_VALUE,
            None,
            _add_relationship_hypothesis,
        ),
        (
            "source_obligation_candidate.candidate_id",
            ("source_obligation_candidates", 0, "candidate_id"),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_ID_TEXT_EMPTY,
            _M03,
            None,
            None,
        ),
        (
            "source_obligation_candidate.obligation_kind",
            ("source_obligation_candidates", 0, "obligation_kind"),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_MISSING,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_TEXT_EMPTY,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_KIND_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "component_search_requirement.requirement_id",
            ("component_search_requirements", 0, "requirement_id"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_ID_TEXT_EMPTY,
            _M03,
            None,
            None,
        ),
        (
            "component_search_requirement.component_id",
            ("component_search_requirements", 0, "component_id"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_COMPONENT_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_COMPONENT_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_COMPONENT_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_COMPONENT_ID_TEXT_EMPTY,
            _M03,
            None,
            None,
        ),
        (
            "component_search_requirement.requirement_summary",
            ("component_search_requirements", 0, "requirement_summary"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_MISSING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_EMPTY,
            _M02_VALUE,
            None,
            None,
        ),
        (
            "query_strategy_candidate.strategy_id",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "strategy_id",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_ID_TEXT_EMPTY,
            _M03,
            None,
            None,
        ),
        (
            "query_strategy_candidate.component_id",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "component_id",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_ID_TEXT_EMPTY,
            _M10,
            None,
            None,
        ),
        (
            "query_strategy_candidate.candidate_kind",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "candidate_kind",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_TEXT_EMPTY,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "query_strategy_candidate.candidate_query_text",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "candidate_query_text",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_QUERY_TEXT_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_QUERY_TEXT_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_QUERY_TEXT_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_QUERY_TEXT_TEXT_EMPTY,
            _M07,
            None,
            None,
        ),
        (
            "query_strategy_candidate.requested_role",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "requested_role",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_REQUESTED_ROLE_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_REQUESTED_ROLE_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_REQUESTED_ROLE_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_REQUESTED_ROLE_TEXT_EMPTY,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_REQUESTED_ROLE_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "query_strategy_candidate.distinct_need_justification",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "distinct_need_justification",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_DISTINCT_NEED_JUSTIFICATION_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_DISTINCT_NEED_JUSTIFICATION_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_DISTINCT_NEED_JUSTIFICATION_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_DISTINCT_NEED_JUSTIFICATION_TEXT_EMPTY,
            _M07,
            None,
            None,
        ),
        (
            "query_strategy_recon_requirement.posture",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "recon_requirement",
                "posture",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_POSTURE_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_POSTURE_MISSING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_POSTURE_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_POSTURE_TEXT_EMPTY,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_POSTURE_VALUE_NOT_ALLOWED,
            None,
        ),
        (
            "recon_candidate_query.dimension_id",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "recon_requirement",
                "candidate_queries",
                0,
                "dimension_id",
            ),
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_DIMENSION_ID_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_DIMENSION_ID_MISSING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_DIMENSION_ID_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_DIMENSION_ID_TEXT_EMPTY,
            _M07,
            None,
            _add_recon_candidate_query,
        ),
        (
            "recon_candidate_query.candidate_query_text",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "recon_requirement",
                "candidate_queries",
                0,
                "candidate_query_text",
            ),
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_CANDIDATE_QUERY_TEXT_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_CANDIDATE_QUERY_TEXT_MISSING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_CANDIDATE_QUERY_TEXT_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_CANDIDATE_QUERY_TEXT_TEXT_EMPTY,
            _M07,
            None,
            _add_recon_candidate_query,
        ),
        (
            "recon_candidate_query.query_kind",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "recon_requirement",
                "candidate_queries",
                0,
                "query_kind",
            ),
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_QUERY_KIND_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_QUERY_KIND_MISSING,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_QUERY_KIND_TEXT_OVER_MAX,
            SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_QUERY_KIND_TEXT_EMPTY,
            _M07,
            None,
            _add_recon_candidate_query,
        ),
    ):
        rows.extend(
            _text_field_witnesses(
                field_path=field_path,
                path=path,
                invalid_type=invalid_type,
                missing=missing,
                text_over_max=text_over_max,
                text_empty=text_empty,
                field_metadata=field_metadata,
                missing_metadata=(
                    _M02_MISSING
                    if missing
                    in {
                        SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_LABEL_MISSING,
                        SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_USER_FACING_QUESTION_MISSING,
                        SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_SUMMARY_MISSING,
                        SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUMMARY_MISSING,
                    }
                    else None
                ),
                value_not_allowed=value_not_allowed,
                setup=setup,
            )
        )

    for (
        field_path,
        path,
        container_invalid_type,
        item_invalid_type,
        item_text_over_max,
        item_metadata,
        missing,
        missing_metadata,
        no_nonempty_items,
        no_nonempty_items_metadata,
        setup,
    ) in (
        (
            "top_level.mandatory_caveats",
            ("mandatory_caveats",),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEATS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEAT_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEATS_MISSING,
            _M01_TOP_LEVEL_MISSING,
            None,
            None,
            None,
        ),
        (
            "top_level.prohibited_upgrades",
            ("prohibited_upgrades",),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADES_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_PROHIBITED_UPGRADES_MISSING,
            _M01_TOP_LEVEL_MISSING,
            None,
            None,
            None,
        ),
        (
            "top_level.normalization_obligations",
            ("normalization_obligations",),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_NORMALIZATION_OBLIGATIONS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.NORMALIZATION_OBLIGATION_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.NORMALIZATION_OBLIGATION_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_NORMALIZATION_OBLIGATIONS_MISSING,
            _M01_TOP_LEVEL_MISSING,
            None,
            None,
            None,
        ),
        (
            "top_level.assumptions",
            ("assumptions",),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_ASSUMPTIONS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ASSUMPTION_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ASSUMPTION_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_ASSUMPTIONS_MISSING,
            _M01_TOP_LEVEL_MISSING,
            None,
            None,
            None,
        ),
        (
            "top_level.unsupported_or_deferred_outputs",
            ("unsupported_or_deferred_outputs",),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_UNSUPPORTED_OR_DEFERRED_OUTPUTS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.UNSUPPORTED_OR_DEFERRED_OUTPUT_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_UNSUPPORTED_OR_DEFERRED_OUTPUTS_MISSING,
            _M01_TOP_LEVEL_MISSING,
            None,
            None,
            None,
        ),
        (
            "semantic_slot.candidate_values",
            ("semantic_slots", 0, "candidate_values"),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUES_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "semantic_slot.normalization_notes",
            ("semantic_slots", 0, "normalization_notes"),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NORMALIZATION_NOTES_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NORMALIZATION_NOTE_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NORMALIZATION_NOTE_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "answer_component.source_obligation_candidate_ids",
            ("answer_components", 0, "source_obligation_candidate_ids"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_CANDIDATE_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_CANDIDATE_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_CANDIDATE_IDS_ITEM_TEXT_OVER_MAX,
            _M03,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "answer_component.dependency_component_ids",
            ("answer_components", 0, "dependency_component_ids"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_COMPONENT_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_COMPONENT_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_COMPONENT_IDS_ITEM_TEXT_OVER_MAX,
            _M04,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "answer_component.allowed_support_kinds",
            ("answer_components", 0, "allowed_support_kinds"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KIND_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_MISSING,
            _M02_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NO_NONEMPTY_ITEMS,
            _M02_VALUE,
            None,
        ),
        (
            "answer_component.acceptance_criteria",
            ("answer_components", 0, "acceptance_criteria"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_MISSING,
            _M02_MISSING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ACCEPTANCE_CRITERIA_NO_NONEMPTY_ITEMS,
            _M02_VALUE,
            None,
        ),
        (
            "answer_component.semantic_slot_ids",
            ("answer_components", 0, "semantic_slot_ids"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_IDS_ITEM_TEXT_OVER_MAX,
            _M03,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_IDS_MISSING,
            _M03,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_IDS_NO_NONEMPTY_ITEMS,
            _M03,
            None,
        ),
        (
            "answer_component.mandatory_caveats",
            ("answer_components", 0, "mandatory_caveats"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MANDATORY_CAVEATS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MANDATORY_CAVEAT_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MANDATORY_CAVEAT_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "answer_component.prohibited_upgrades",
            ("answer_components", 0, "prohibited_upgrades"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PROHIBITED_UPGRADES_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PROHIBITED_UPGRADE_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PROHIBITED_UPGRADE_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "relationship_hypothesis.premise_component_ids",
            ("relationship_hypotheses", 0, "premise_component_ids"),
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_PREMISE_COMPONENT_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_PREMISE_COMPONENT_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_PREMISE_COMPONENT_IDS_ITEM_TEXT_OVER_MAX,
            _M03,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_PREMISE_COMPONENT_IDS_MISSING,
            _M03,
            SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_PREMISE_COMPONENT_IDS_NO_NONEMPTY_ITEMS,
            _M03,
            _add_relationship_hypothesis,
        ),
        (
            "source_obligation_candidate.component_candidate_ids",
            ("source_obligation_candidates", 0, "component_candidate_ids"),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_CANDIDATE_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_CANDIDATE_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_CANDIDATE_IDS_ITEM_TEXT_OVER_MAX,
            _M03,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_CANDIDATE_IDS_MISSING,
            _M03,
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_CANDIDATE_IDS_NO_NONEMPTY_ITEMS,
            _M03,
            None,
        ),
        (
            "component_search_requirement.source_obligation_candidate_ids",
            ("component_search_requirements", 0, "source_obligation_candidate_ids"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_CANDIDATE_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_CANDIDATE_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_CANDIDATE_IDS_ITEM_TEXT_OVER_MAX,
            _M03,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_CANDIDATE_IDS_MISSING,
            _M03,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_CANDIDATE_IDS_NO_NONEMPTY_ITEMS,
            _M03,
            None,
        ),
        (
            "component_search_requirement.preferred_source_kinds",
            ("component_search_requirements", 0, "preferred_source_kinds"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KINDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KIND_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KIND_ITEM_TEXT_OVER_MAX,
            _M02_VALUE,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "query_strategy_candidate.source_obligation_candidate_ids",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "source_obligation_candidate_ids",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_CANDIDATE_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_CANDIDATE_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_CANDIDATE_IDS_ITEM_TEXT_OVER_MAX,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_CANDIDATE_IDS_MISSING,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_CANDIDATE_IDS_NO_NONEMPTY_ITEMS,
            _M07,
            None,
        ),
        (
            "query_strategy_recon_requirement.unresolved_dimension_ids",
            (
                "component_search_requirements",
                0,
                "metadata",
                "query_strategy_candidates",
                0,
                "recon_requirement",
                "unresolved_dimension_ids",
            ),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_UNRESOLVED_DIMENSION_IDS_NOT_JSON_ARRAY,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_UNRESOLVED_DIMENSION_ID_ITEM_NOT_JSON_STRING,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_UNRESOLVED_DIMENSION_IDS_ITEM_TEXT_OVER_MAX,
            _M07,
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_UNRESOLVED_DIMENSION_IDS_MISSING,
            _M07,
            None,
            None,
            None,
        ),
    ):
        rows.extend(
            _text_array_witnesses(
                field_path=field_path,
                path=path,
                container_invalid_type=container_invalid_type,
                item_invalid_type=item_invalid_type,
                item_text_over_max=item_text_over_max,
                item_metadata=item_metadata,
                missing=missing,
                missing_metadata=missing_metadata,
                no_nonempty_items=no_nonempty_items,
                no_nonempty_items_metadata=no_nonempty_items_metadata,
                setup=setup,
            )
        )

    for field_path, path, predicate_id, setup in (
        (
            "semantic_slot.selected_value",
            ("semantic_slots", 0, "selected_value"),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_SELECTED_VALUE_NOT_JSON_STRING,
            None,
        ),
        (
            "answer_component.normalization_policy",
            ("answer_components", 0, "normalization_policy"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_NORMALIZATION_POLICY_NOT_JSON_STRING,
            None,
        ),
        (
            "answer_component.calculation_policy",
            ("answer_components", 0, "calculation_policy"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_CALCULATION_POLICY_NOT_JSON_STRING,
            None,
        ),
        (
            "answer_component.partial_answer_policy",
            ("answer_components", 0, "partial_answer_policy"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_NOT_JSON_STRING,
            None,
        ),
        (
            "source_obligation_candidate.strictness",
            ("source_obligation_candidates", 0, "strictness"),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_STRICTNESS_NOT_JSON_STRING,
            None,
        ),
        (
            "component_search_requirement.recency_requirement",
            ("component_search_requirements", 0, "recency_requirement"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_RECENCY_REQUIREMENT_NOT_JSON_STRING,
            None,
        ),
        (
            "contract_amendment_candidate.candidate_id",
            ("contract_amendment_candidates", 0, "candidate_id"),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_ID_NOT_JSON_STRING,
            _add_contract_amendment_candidate,
        ),
        (
            "contract_amendment_candidate.operation_kind",
            ("contract_amendment_candidates", 0, "operation_kind"),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_OPERATION_KIND_NOT_JSON_STRING,
            _add_contract_amendment_candidate,
        ),
        (
            "contract_amendment_candidate.summary",
            ("contract_amendment_candidates", 0, "summary"),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_SUMMARY_NOT_JSON_STRING,
            _add_contract_amendment_candidate,
        ),
    ):
        rows.append(
            _path_witness(
                field_path=field_path,
                path=path,
                condition="not_json_string",
                predicate_id=predicate_id,
                metadata=_M02_INVALID_TYPE,
                value=7,
                setup=setup,
            )
        )

    for field_path, path, predicate_id, metadata, setup in (
        (
            "semantic_slot.metadata",
            ("semantic_slots", 0, "metadata"),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_METADATA_NOT_JSON_OBJECT,
            _M02_INVALID_TYPE,
            None,
        ),
        (
            "answer_component.metadata",
            ("answer_components", 0, "metadata"),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_METADATA_NOT_JSON_OBJECT,
            _M02_INVALID_TYPE,
            None,
        ),
        (
            "source_obligation_candidate.metadata",
            ("source_obligation_candidates", 0, "metadata"),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_METADATA_NOT_JSON_OBJECT,
            _M02_INVALID_TYPE,
            None,
        ),
        (
            "component_search_requirement.metadata",
            ("component_search_requirements", 0, "metadata"),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_METADATA_NOT_OBJECT,
            _M07,
            None,
        ),
        (
            "contract_amendment_candidate.metadata",
            ("contract_amendment_candidates", 0, "metadata"),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_METADATA_NOT_JSON_OBJECT,
            _M02_INVALID_TYPE,
            _add_contract_amendment_candidate,
        ),
    ):
        rows.append(
            _path_witness(
                field_path=field_path,
                path=path,
                condition="not_json_object",
                predicate_id=predicate_id,
                metadata=metadata,
                value=[],
                setup=setup,
            )
        )

    rows.extend(
        (
            _path_witness(
                field_path="answer_component.partial_answer_policy",
                path=("answer_components", 0, "partial_answer_policy"),
                condition="value_not_allowed",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM,
                metadata=_M02_VALUE,
                value="invalid_partial_answer_policy",
            ),
            _path_witness(
                field_path="source_obligation_candidate.strictness",
                path=("source_obligation_candidates", 0, "strictness"),
                condition="value_not_allowed",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_STRICTNESS_ENUM,
                metadata=_M02_VALUE,
                value="invalid_strictness",
            ),
            _path_witness(
                field_path="answer_component.allowed_support_kinds",
                path=("answer_components", 0, "allowed_support_kinds"),
                condition="item_value_not_allowed",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_VALUE_NOT_ALLOWED,
                metadata=_M02_VALUE,
                value=["unsupported"],
            ),
            _path_witness(
                field_path="semantic_slots",
                path=("semantic_slots",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOTS_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="semantic_slot",
                path=("semantic_slots",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="answer_components",
                path=("answer_components",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENTS_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="answer_component",
                path=("answer_components",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="relationship_hypotheses",
                path=("relationship_hypotheses",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESES_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="relationship_hypothesis",
                path=("relationship_hypotheses",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="source_obligation_candidates",
                path=("source_obligation_candidates",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATES_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="source_obligation_candidate",
                path=("source_obligation_candidates",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="component_search_requirements",
                path=("component_search_requirements",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENTS_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="component_search_requirement",
                path=("component_search_requirements",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="contract_amendment_candidates",
                path=("contract_amendment_candidates",),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATES_NOT_ARRAY,
                metadata=_M02_INVALID_TYPE,
                value={},
            ),
            _path_witness(
                field_path="contract_amendment_candidate",
                path=("contract_amendment_candidates",),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_NOT_OBJECT,
                metadata=_M02_INVALID_TYPE,
                value=[7],
            ),
            _path_witness(
                field_path="semantic_slots",
                path=("semantic_slots",),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOTS_MINIMUM_ITEMS_1,
                metadata=_M02_VALUE,
                value=[],
            ),
            _path_witness(
                field_path="answer_components",
                path=("answer_components",),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENTS_MINIMUM_ITEMS_1,
                metadata=_M02_COMPONENT_COUNT,
                value=[],
            ),
            _path_witness(
                field_path="source_obligation_candidates",
                path=("source_obligation_candidates",),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATES_MINIMUM_ITEMS_1,
                metadata=_M02_VALUE,
                value=[],
            ),
        )
    )

    rows.extend(
        (
            _direct_witness(
                field_path="semantic_slot.slot_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["semantic_slots"][1].__setitem__(
                        "slot_id", output["semantic_slots"][0]["slot_id"]
                    )
                ),
            ),
            _direct_witness(
                field_path="answer_component.component_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["answer_components"].append(deepcopy(output["answer_components"][0]))
                ),
            ),
            _direct_witness(
                field_path="relationship_hypothesis.hypothesis_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESIS_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: (
                        _add_relationship_hypothesis(output),
                        output["relationship_hypotheses"].append(deepcopy(output["relationship_hypotheses"][0])),
                    )
                ),
            ),
            _direct_witness(
                field_path="source_obligation_candidate.candidate_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_CANDIDATE_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["source_obligation_candidates"].append(
                        deepcopy(output["source_obligation_candidates"][0])
                    )
                ),
            ),
            _direct_witness(
                field_path="component_search_requirement.requirement_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["component_search_requirements"].append(
                        deepcopy(output["component_search_requirements"][0])
                    )
                ),
            ),
            _direct_witness(
                field_path="query_strategy_candidate.strategy_id",
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_ID_DUPLICATE,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["component_search_requirements"][0]["metadata"][
                        "query_strategy_candidates"
                    ].append(
                        deepcopy(output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0])
                    )
                ),
            ),
            _path_witness(
                field_path="answer_component.semantic_slot_ids",
                path=("answer_components", 0, "semantic_slot_ids"),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_REFERENCE_UNRESOLVED,
                metadata=_M03,
                value=["slot:missing"],
            ),
            _path_witness(
                field_path="answer_component.source_obligation_candidate_ids",
                path=("answer_components", 0, "source_obligation_candidate_ids"),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_REFERENCE_UNRESOLVED,
                metadata=_M03,
                value=["obligation:missing"],
            ),
            _path_witness(
                field_path="source_obligation_candidate.component_candidate_ids",
                path=("source_obligation_candidates", 0, "component_candidate_ids"),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_COMPONENT_REFERENCE_UNRESOLVED,
                metadata=_M03,
                value=["component:missing"],
            ),
            _path_witness(
                field_path="component_search_requirement.source_obligation_candidate_ids",
                path=("component_search_requirements", 0, "source_obligation_candidate_ids"),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SOURCE_OBLIGATION_REFERENCE_UNRESOLVED,
                metadata=_M03,
                value=["obligation:missing"],
            ),
            _path_witness(
                field_path="query_strategy_candidate.source_obligation_candidate_ids",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                    0,
                    "source_obligation_candidate_ids",
                ),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_SOURCE_OBLIGATION_REFERENCE_UNRESOLVED,
                metadata=_M03,
                value=["obligation:missing"],
            ),
            _path_witness(
                field_path="answer_component.max_inference_depth",
                path=("answer_components", 0, "max_inference_depth"),
                condition="missing",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MAX_INFERENCE_DEPTH_MISSING,
                metadata=_M04,
                remove=True,
            ),
            _path_witness(
                field_path="answer_component.max_inference_depth",
                path=("answer_components", 0, "max_inference_depth"),
                condition="boolean_not_allowed",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MAX_INFERENCE_DEPTH_BOOLEAN_NOT_ALLOWED,
                metadata=_M04,
                value=True,
            ),
            _path_witness(
                field_path="answer_component.max_inference_depth",
                path=("answer_components", 0, "max_inference_depth"),
                condition="not_integer",
                predicate_id=SearchPlannerModelAdapterPredicateId.MAX_INFERENCE_DEPTH_NOT_INTEGER,
                metadata=_M04,
                value="not-an-integer",
            ),
            _path_witness(
                field_path="answer_component.max_inference_depth",
                path=("answer_components", 0, "max_inference_depth"),
                condition="negative",
                predicate_id=SearchPlannerModelAdapterPredicateId.MAX_INFERENCE_DEPTH_NEGATIVE,
                metadata=_M04,
                value=-1,
            ),
            _path_witness(
                field_path="answer_component.dependency_component_ids",
                path=("answer_components", 0, "dependency_component_ids"),
                condition="duplicate",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_IDS_DUPLICATE,
                metadata=_M04,
                value=["component:model-official-threshold", "component:model-official-threshold"],
            ),
            _path_witness(
                field_path="answer_component.dependency_component_ids",
                path=("answer_components", 0, "dependency_component_ids"),
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_REFERENCE_UNRESOLVED,
                metadata=_M04,
                value=["component:missing"],
            ),
            _path_witness(
                field_path="answer_component.dependency_component_ids",
                path=("answer_components", 0, "dependency_component_ids"),
                condition="self_dependency_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SELF_DEPENDENCY_FORBIDDEN,
                metadata=_M04,
                value=["component:model-official-threshold"],
            ),
        )
    )

    rows.extend(
        (
            _direct_witness(
                field_path="answer_component.allowed_support_kinds",
                condition="tuple_not_allowed",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_TUPLE_NOT_ALLOWED,
                metadata=_M05,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["answer_components"][0].__setitem__(
                        "allowed_support_kinds", ["direct", "direct"]
                    )
                ),
            ),
            _direct_witness(
                field_path="answer_component.max_inference_depth",
                condition="direct_support_not_zero",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DIRECT_SUPPORT_MAX_INFERENCE_DEPTH_NOT_ZERO,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["direct"],
                    max_inference_depth=1,
                    source_obligation_candidate_ids=["obligation:model-official-current"],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.source_obligation_candidate_ids",
                condition="direct_support_cardinality_not_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DIRECT_SUPPORT_SOURCE_OBLIGATION_CANDIDATE_IDS_CARDINALITY_NOT_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["direct"],
                    max_inference_depth=0,
                    source_obligation_candidate_ids=[],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.max_inference_depth",
                condition="inferred_support_minimum_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_INFERRED_SUPPORT_MAX_INFERENCE_DEPTH_MINIMUM_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["inferred"],
                    max_inference_depth=0,
                    source_obligation_candidate_ids=[],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.dependency_component_ids",
                condition="inferred_support_minimum_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_INFERRED_SUPPORT_DEPENDENCY_COMPONENT_IDS_MINIMUM_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["inferred"],
                    max_inference_depth=1,
                    source_obligation_candidate_ids=[],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.source_obligation_candidate_ids",
                condition="inferred_support_must_be_empty",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_INFERRED_SUPPORT_SOURCE_OBLIGATION_CANDIDATE_IDS_MUST_BE_EMPTY,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["inferred"],
                    max_inference_depth=1,
                    source_obligation_candidate_ids=["obligation:model-official-current"],
                    dependency_component_ids=["component:model-official-threshold"],
                ),
            ),
            _direct_witness(
                field_path="answer_component.max_inference_depth",
                condition="direct_or_inferred_support_minimum_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DIRECT_OR_INFERRED_SUPPORT_MAX_INFERENCE_DEPTH_MINIMUM_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["direct", "inferred"],
                    max_inference_depth=0,
                    source_obligation_candidate_ids=["obligation:model-official-current"],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.dependency_component_ids",
                condition="direct_or_inferred_support_minimum_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DIRECT_OR_INFERRED_SUPPORT_DEPENDENCY_COMPONENT_IDS_MINIMUM_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["direct", "inferred"],
                    max_inference_depth=1,
                    source_obligation_candidate_ids=["obligation:model-official-current"],
                    dependency_component_ids=None,
                ),
            ),
            _direct_witness(
                field_path="answer_component.source_obligation_candidate_ids",
                condition="direct_or_inferred_support_cardinality_not_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DIRECT_OR_INFERRED_SUPPORT_SOURCE_OBLIGATION_CANDIDATE_IDS_CARDINALITY_NOT_1,
                metadata=_M05,
                emit=lambda: _support_matrix_error(
                    support_kinds=["direct", "inferred"],
                    max_inference_depth=1,
                    source_obligation_candidate_ids=[],
                    dependency_component_ids=["component:model-official-threshold"],
                ),
            ),
            _path_witness(
                field_path="answer_components.requirement_posture",
                path=("answer_components", 0, "requirement_posture"),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_REQUIRED_POSTURE_MINIMUM_ITEMS_1,
                metadata=_M06,
                value="optional",
            ),
            _direct_witness(
                field_path="component_search_requirement.component_id",
                condition="inferred_only_component_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.INFERRED_ONLY_COMPONENT_SEARCH_REQUIREMENT_FORBIDDEN,
                metadata=_M06,
                emit=_inferred_component_requirement_error,
            ),
        )
    )

    rows.extend(
        (
            _direct_witness(
                field_path="answer_components",
                condition="maximum_items_5",
                predicate_id=SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENTS_MAXIMUM_ITEMS_5,
                metadata=_M02_COMPONENT_COUNT,
                emit=_answer_components_maximum_items_error,
            ),
            _direct_witness(
                field_path="relationship_hypotheses",
                condition="maximum_items_5",
                predicate_id=SearchPlannerModelAdapterPredicateId.RELATIONSHIP_HYPOTHESES_MAXIMUM_ITEMS_5,
                metadata=_M02_VALUE,
                emit=_relationship_hypotheses_maximum_items_error,
            ),
            _direct_witness(
                field_path="component_search_requirement.component_id",
                condition="reference_unresolved",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_COMPONENT_REFERENCE_UNRESOLVED,
                metadata=_M03,
                emit=lambda: _mutated_model_output_error(
                    lambda output: (
                        output["component_search_requirements"][0].__setitem__("component_id", "component:missing"),
                        output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][
                            0
                        ].__setitem__("component_id", "component:missing"),
                    )
                ),
            ),
            _path_witness(
                field_path="component_search_requirements",
                path=("component_search_requirements",),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENTS_MINIMUM_ITEMS_1,
                metadata=_M07,
                value=[],
            ),
            _path_witness(
                field_path="component_search_requirement.metadata.query_strategy_candidates",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                ),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATES_NOT_ARRAY,
                metadata=_M07,
                value={},
            ),
            _path_witness(
                field_path="component_search_requirement.metadata.query_strategy_candidates",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                ),
                condition="minimum_items_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATES_MINIMUM_ITEMS_1,
                metadata=_M07,
                value=[],
            ),
            _path_witness(
                field_path="query_strategy_candidate",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                ),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_NOT_OBJECT,
                metadata=_M07,
                value=[7],
            ),
            _path_witness(
                field_path="query_strategy_recon_requirement",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                    0,
                    "recon_requirement",
                ),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_REQUIREMENT_NOT_OBJECT,
                metadata=_M07,
                value=[],
            ),
            _path_witness(
                field_path="query_strategy_recon_requirement.candidate_queries",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                    0,
                    "recon_requirement",
                    "candidate_queries",
                ),
                condition="not_json_array",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_RECON_CANDIDATE_QUERIES_NOT_ARRAY,
                metadata=_M07,
                value={},
            ),
            _path_witness(
                field_path="recon_candidate_query",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                    0,
                    "recon_requirement",
                    "candidate_queries",
                ),
                condition="not_json_object",
                predicate_id=SearchPlannerModelAdapterPredicateId.RECON_CANDIDATE_QUERY_NOT_OBJECT,
                metadata=_M07,
                value=[7],
            ),
            _direct_witness(
                field_path="required_direct_component.query_strategy_candidates.primary_count",
                condition="cardinality_not_1",
                predicate_id=SearchPlannerModelAdapterPredicateId.REQUIRED_DIRECT_COMPONENT_PRIMARY_QUERY_STRATEGY_CARDINALITY_INVALID,
                metadata=_M07,
                emit=lambda: _query_strategy_primary_count_error(0),
            ),
            _path_witness(
                field_path="component_search_requirement.must_not_execute",
                path=("component_search_requirements", 0, "must_not_execute"),
                condition="not_true",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_MUST_NOT_EXECUTE_NOT_TRUE,
                metadata=_M08,
                value=False,
            ),
            _direct_witness(
                field_path="query_strategy_candidate.recursive_authority_keys",
                condition="provider_or_model_authority_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_PROVIDER_MODEL_AUTHORITY_FORBIDDEN,
                metadata=_M08,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][
                        0
                    ].__setitem__("provider_name", "untrusted-provider")
                ),
                scope="dynamic",
            ),
            _direct_witness(
                field_path="model_output.recursive_authority_keys",
                condition="closed_authority_field_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
                metadata=_M08,
                emit=lambda: _mutated_model_output_error(lambda output: output.__setitem__("answer", "forbidden")),
                scope="dynamic",
            ),
            _direct_witness(
                field_path="model_output.recursive_runtime_claims",
                condition="closed_runtime_claim_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.CLOSED_RUNTIME_CLAIM_FORBIDDEN,
                metadata=_M08,
                emit=lambda: _mutated_model_output_error(
                    lambda output: output["component_search_requirements"][0].__setitem__("search_executed", True)
                ),
                scope="dynamic",
            ),
            _direct_witness(
                field_path="model_output.recursive_private_keys",
                condition="raw_or_private_field_forbidden",
                predicate_id=SearchPlannerModelAdapterPredicateId.RAW_OR_PRIVATE_FIELD_FORBIDDEN,
                metadata=_M09,
                emit=lambda: _mutated_model_output_error(lambda output: output.__setitem__("raw_payload", "forbidden")),
                scope="dynamic",
            ),
            _path_witness(
                field_path="query_strategy_candidate.component_id",
                path=(
                    "component_search_requirements",
                    0,
                    "metadata",
                    "query_strategy_candidates",
                    0,
                    "component_id",
                ),
                condition="binding_stale",
                predicate_id=SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_BINDING_STALE,
                metadata=_M10,
                value="component:stale",
            ),
            _path_witness(
                field_path="component_search_requirement.subordinate_to_answer_contract",
                path=(
                    "component_search_requirements",
                    0,
                    "subordinate_to_answer_contract",
                ),
                condition="not_true",
                predicate_id=SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_SUBORDINATE_TO_ANSWER_CONTRACT_NOT_TRUE,
                metadata=_M10,
                value=False,
            ),
        )
    )

    return tuple(rows)


_FIELD_CONDITION_WITNESS_INVENTORY = _field_condition_witness_inventory()


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
        support_component["source_obligation_candidate_ids"] = ["obligation:model-derived-current"]
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


def _schema_paths_with_adapter_normalization(
    value: Any,
    expected_normalization: str,
    *,
    path: tuple[str | int, ...] = (),
) -> set[tuple[str | int, ...]]:
    matches: set[tuple[str | int, ...]] = set()
    if isinstance(value, Mapping):
        if value.get("adapter_normalization") == expected_normalization:
            matches.add(path)
        for key, child in value.items():
            matches.update(
                _schema_paths_with_adapter_normalization(
                    child,
                    expected_normalization,
                    path=(*path, str(key)),
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.update(
                _schema_paths_with_adapter_normalization(
                    child,
                    expected_normalization,
                    path=(*path, index),
                )
            )
    return matches


def test_model_adapter_requires_enabled_and_callable() -> None:
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))
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
        assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.INPUT
        assert caught.value.failure_code == expected_code
        assert caught.value.mechanical_rule_id is None

    assert fake.calls == []


def test_model_adapter_calls_injected_model_with_json_requirement() -> None:
    query = "Q" * SEARCH_PLANNER_INPUT_PREVIEW_CHARS + LONG_SUFFIX
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))
    adapter = _adapter(fake)

    adapter.produce(_planner_input(_kernel(), query=query).to_adapter_payload())

    assert len(fake.calls) == 1
    args, kwargs = fake.calls[0]
    prompt = args[0]
    system_prompt = args[1]
    assert "SEARCHPLANNER SEMANTIC TASK" in prompt
    assert "Never author queries/recon/Scout/PlannerRevision" in prompt
    assert "Unknown fields, old rich output" in prompt
    assert LONG_SUFFIX.strip() in prompt
    assert "semantic planning only" in system_prompt
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
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))

    with pytest.raises(
        SearchPlannerModelAdapterError,
        match="model input failed closed: RuntimeError",
    ) as caught:
        _adapter(fake).produce(_planner_input(_kernel()).to_adapter_payload())

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.INPUT
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INPUT_CONSTRUCTION_FAILED
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

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_CALL
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.MODEL_CALL_FAILED
    assert caught.value.mechanical_rule_id is None
    assert raw_failure not in str(caught.value)
    assert len(fake.calls) == 1


def test_valid_fake_model_json_flows_through_search_planner_runtime_and_initial_contract_acceptance() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))

    _produce(kernel, _adapter(fake))
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    _accept_planner_qmr(kernel, qmr)

    initial = kernel.state.initial_answer_contract
    assert initial["accepted_answer_component_refs"][0]["component_id"] == "component:01"
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

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_JSON
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
    assert caught.value.predicate_registry_version == SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    assert caught.value.predicate_id == SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED
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
        '{"outer": {"duplicate-member-sentinel": "first-value", "duplicate-member-sentinel": "second-value"}}',
        forbidden_fragments=(
            "duplicate-member-sentinel",
            "first-value",
            "second-value",
        ),
    )


def test_duplicate_member_inside_array_object_fails_at_the_parser_boundary() -> None:
    _assert_strict_json_parsing_failure(
        '{"items": [{"duplicate-member-sentinel": "first-value", "duplicate-member-sentinel": "second-value"}]}',
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

    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert caught.value.mechanical_rule_id == "M02"


def test_benign_response_cleaning_preserves_valid_strict_json() -> None:
    kernel = _kernel()
    cleaned = json.dumps(_sparse_planner_output())
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
        '{"duplicate-member-sentinel": "first-value", "duplicate-member-sentinel": "second-value"}',
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
    fake = FakeAskModel(json.dumps({"disposition": "components"}))

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(fake))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert caught.value.predicate_id is SearchPlannerModelAdapterPredicateId.SEMANTIC_PROPOSAL_VALIDATION_FAILED
    assert kernel.state.search_planner_proposal_state == {}


def test_model_output_forbidden_authority_fields_fail_closed() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["current_answer_contract"] = {"mutated": True}

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert kernel.state.search_planner_proposal_state == {}


def test_raw_prompt_model_response_provider_payload_not_retained() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))
    planner_input = _planner_input(
        kernel,
        query=f"What is this? {RAW_PROMPT_SENTINEL}",
    )

    _produce(kernel, _adapter(fake), planner_input=planner_input)

    trace_json = json.dumps(kernel.trace_projection().to_dict(), sort_keys=True)
    assert RAW_PROMPT_SENTINEL not in trace_json
    assert RAW_PROVIDER_SENTINEL not in trace_json
    assert '"raw_prompt":' not in trace_json
    assert '"raw_model_response":' not in trace_json
    assert '"raw_provider_payload":' not in trace_json
    assert '"provider_payload":' not in trace_json
    assert "fake-fast-model" in trace_json
    assert '"prompt_hash":' in trace_json


def test_raw_provider_payload_field_fails_closed() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["raw_provider_payload"] = RAW_PROVIDER_SENTINEL

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert RAW_PROVIDER_SENTINEL not in str(caught.value)
    assert kernel.state.search_planner_proposal_state == {}


def test_model_authored_contract_amendment_candidates_fail_closed() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["contract_amendment_candidates"] = [{"summary": "unaccepted"}]

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.current_answer_contract == {}


def test_model_adapter_component_search_requirements_remain_non_executing() -> None:
    kernel = _kernel()
    fake = FakeAskModel(json.dumps(_sparse_planner_output()))

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
    assert not hasattr(kernel.state, "search_work_plan")
    assert not hasattr(kernel.state, "search_work_plan_projection")


def test_model_authored_query_strategy_and_recon_fail_closed() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["components"][0]["recon"] = {"posture": "optional"}

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert kernel.state.search_planner_proposal_state == {}


def test_model_output_executing_component_requirement_fails_closed() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["components"][0]["search_executed"] = True

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
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
    invalid = _sparse_planner_output()
    invalid["components"][0]["source"][field] = value
    fake = FakeAskModel(json.dumps(invalid))

    with pytest.raises(
        SearchPlannerModelAdapterError,
    ):
        _produce(kernel, _adapter(fake))

    assert len(fake.calls) == 1
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}


# New parity tests are phase_focus / component_harness_proof. They guard the
# current product-consumed adapter contract and remain out of fast_pr because
# they are detailed schema coverage rather than a broad execution sentinel.
def test_model_prompt_embeds_the_exact_sparse_contract_and_version() -> None:
    planner_input = _planner_input(_kernel()).to_adapter_payload()
    prompt = search_planner_model_prompt.build_search_planner_model_prompt(planner_input)
    prompt_packet = json.loads(prompt.split("Sanitized planner input JSON:\n", 1)[1])

    assert SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION == "search_planner_sparse_model_prompt_v8"
    assert SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION == "search_planner_model_adapter_ag_search_planner_model_01_v2"
    assert prompt_packet["schema_version"] == SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
    assert prompt_packet["output_schema"] == search_planner_model_prompt.SEARCH_PLANNER_MODEL_OUTPUT_SCHEMA
    assert set(prompt_packet["planner_input"]) == {
        "requested_mode",
        "user_query_text_for_planning",
        "safe_context",
    }
    assert "Never author queries/recon/Scout/PlannerRevision" in prompt
    assert "runtime identity" in prompt


def test_sparse_prompt_and_parser_share_strict_json_boundary() -> None:
    planner_input = _planner_input(_kernel()).to_adapter_payload()
    prompt = search_planner_model_prompt.build_search_planner_model_prompt(planner_input)

    assert "Return one JSON object only" in prompt
    assert "duplicate keys" in prompt
    assert "nonfinite JSON fail closed" in prompt
    assert "Return one JSON object" in search_planner_model_prompt.SEARCH_PLANNER_MODEL_SYSTEM_PROMPT


def test_required_narrative_text_schema_contract_is_explicit_and_exactly_scoped() -> None:
    schema = search_planner_model_prompt.SEARCH_PLANNER_RICH_INTERNAL_OUTPUT_SCHEMA
    expected_schema_paths = {field[2] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS}

    assert len(_REQUIRED_NARRATIVE_TEXT_FIELDS) == 7
    assert {field[7] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS} == {
        "QUESTION_MEANING_SUMMARY_TEXT_EMPTY",
        "REQUESTED_OUTPUT_TEXT_EMPTY",
        "MATERIAL_AMBIGUITY_POSTURE_TEXT_EMPTY",
        "ANSWER_COMPONENT_USER_FACING_LABEL_TEXT_EMPTY",
        "ANSWER_COMPONENT_USER_FACING_QUESTION_TEXT_EMPTY",
        "RELATIONSHIP_HYPOTHESIS_SUMMARY_TEXT_EMPTY",
        "COMPONENT_SEARCH_REQUIREMENT_SUMMARY_TEXT_EMPTY",
    }
    assert (
        _schema_paths_with_adapter_normalization(
            schema,
            _REQUIRED_NARRATIVE_TEXT_NORMALIZATION,
        )
        == expected_schema_paths
    )

    for _, _, schema_path, limit_key, expected_limit, _, _, _ in _REQUIRED_NARRATIVE_TEXT_FIELDS:
        contract = _schema_path(schema, *schema_path)
        assert contract["json_type"] == "string"
        assert contract["required"] is True
        assert contract["nonempty"] is True
        assert contract["adapter_normalization"] == _REQUIRED_NARRATIVE_TEXT_NORMALIZATION
        assert contract["max_length"] == expected_limit
        assert search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS[limit_key] == expected_limit


@pytest.mark.parametrize(
    "field",
    _REQUIRED_NARRATIVE_TEXT_FIELDS,
    ids=tuple(field[0] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
)
def test_required_narrative_text_missing_field_owner_is_preserved(
    field: _NarrativeTextField,
) -> None:
    field_name, field_path, _, _, _, expected_code, expected_rule, _ = field
    model_output = _narrative_text_model_output(field_path)
    _pop_narrative_text_field(model_output, field_path)
    kernel = _kernel()

    error = _model_output_error(model_output, kernel=kernel)

    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == expected_code, field_name
    assert error.mechanical_rule_id == expected_rule, field_name
    _assert_rejected_narrative_text_is_not_retained(error, kernel)


@pytest.mark.parametrize(
    "field",
    _REQUIRED_NARRATIVE_TEXT_FIELDS,
    ids=tuple(field[0] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
)
@pytest.mark.parametrize(
    ("wrong_type", "wrong_value"),
    _NARRATIVE_WRONG_TEXT_TYPES,
    ids=tuple(name for name, _ in _NARRATIVE_WRONG_TEXT_TYPES),
)
def test_required_narrative_text_wrong_json_types_fail_before_string_validation(
    field: _NarrativeTextField,
    wrong_type: str,
    wrong_value: Any,
) -> None:
    field_name, field_path, _, _, _, _, _, _ = field
    model_output = _narrative_text_model_output(field_path)
    _set_narrative_text_field(model_output, field_path, deepcopy(wrong_value))
    kernel = _kernel()

    error = _model_output_error(model_output, kernel=kernel)

    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE
    assert error.mechanical_rule_id == "M02"
    assert str(error) == "model-visible text value must be a JSON string", f"{field_name} ({wrong_type})"
    _assert_rejected_narrative_text_is_not_retained(
        error,
        kernel,
        submitted_values=((_NARRATIVE_TEXT_REJECTED_SENTINEL,) if wrong_type in {"object", "array"} else ()),
    )


@pytest.mark.parametrize(
    "field",
    _REQUIRED_NARRATIVE_TEXT_FIELDS,
    ids=tuple(field[0] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
)
@pytest.mark.parametrize(
    ("case_name", "value"),
    _NARRATIVE_EMPTY_TEXT_CASES,
    ids=tuple(name for name, _ in _NARRATIVE_EMPTY_TEXT_CASES),
)
def test_required_narrative_text_empty_after_normalization_fails_closed(
    field: _NarrativeTextField,
    case_name: str,
    value: str,
) -> None:
    field_name, field_path, _, _, _, _, _, _ = field
    field_key = field_path[-1]
    assert isinstance(field_key, str)
    model_output = _narrative_text_model_output(field_path)
    _set_narrative_text_field(model_output, field_path, value)
    kernel = _kernel()

    error = _model_output_error(model_output, kernel=kernel)

    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE
    assert error.mechanical_rule_id == "M02"
    assert str(error) == f"required field is empty: {field_key}", f"{field_name} ({case_name})"
    _assert_rejected_narrative_text_is_not_retained(error, kernel)


@pytest.mark.parametrize(
    "field",
    _REQUIRED_NARRATIVE_TEXT_FIELDS,
    ids=tuple(field[0] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
)
def test_required_narrative_text_normalizes_before_proposal_preservation(
    field: _NarrativeTextField,
) -> None:
    field_name, field_path, _, _, _, _, _, _ = field
    model_output = _narrative_text_model_output(field_path)
    _set_narrative_text_field(model_output, field_path, "  meaningful   normalized\ntext  ")

    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(model_output)

    assert _narrative_text_field_value(proposal, field_path) == "meaningful normalized text", field_name


@pytest.mark.parametrize(
    "field",
    _REQUIRED_NARRATIVE_TEXT_FIELDS,
    ids=tuple(field[0] for field in _REQUIRED_NARRATIVE_TEXT_FIELDS),
)
def test_required_narrative_text_uses_normalized_length_boundaries(
    field: _NarrativeTextField,
) -> None:
    field_name, field_path, _, limit_key, expected_limit, _, _, _ = field
    field_key = field_path[-1]
    assert isinstance(field_key, str)
    assert search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS[limit_key] == expected_limit

    at_limit_text = "x" * expected_limit
    at_limit_output = _narrative_text_model_output(field_path)
    _set_narrative_text_field(at_limit_output, field_path, f" \t{at_limit_text}\n ")
    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(at_limit_output)
    assert len(at_limit_text) == expected_limit
    assert _narrative_text_field_value(proposal, field_path) == at_limit_text, field_name

    over_length_marker = f"{_NARRATIVE_TEXT_REJECTED_SENTINEL}_{field_name.replace('.', '_')}"
    over_length_text = (
        over_length_marker * ((expected_limit + 1 + len(over_length_marker) - 1) // len(over_length_marker))
    )[: expected_limit + 1]
    over_limit_output = _narrative_text_model_output(field_path)
    _set_narrative_text_field(over_limit_output, field_path, f"\n {over_length_text}\t ")
    kernel = _kernel()

    error = _model_output_error(over_limit_output, kernel=kernel)

    assert len(over_length_text) == expected_limit + 1
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE
    assert error.mechanical_rule_id == "M02"
    assert str(error) == f"required field exceeds bounded length: {field_key}", field_name
    _assert_rejected_narrative_text_is_not_retained(
        error,
        kernel,
        submitted_values=(over_length_marker,),
    )


def test_visible_output_contract_and_adapter_contract_constants_stay_in_lockstep() -> None:
    schema = search_planner_model_prompt.SEARCH_PLANNER_RICH_INTERNAL_OUTPUT_SCHEMA
    top_level = schema["top_level"]

    assert top_level["required_fields"] == list(
        search_planner_model_prompt.SEARCH_PLANNER_RICH_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert set(top_level["fields"]) == {
        *search_planner_model_prompt.SEARCH_PLANNER_RICH_REQUIRED_TOP_LEVEL_FIELDS,
        *search_planner_model_prompt.SEARCH_PLANNER_RICH_OPTIONAL_TOP_LEVEL_FIELDS,
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
        is search_planner_model_prompt.SEARCH_PLANNER_RICH_REQUIRED_TOP_LEVEL_FIELDS
    )
    assert (
        search_planner_model_adapter.SEARCH_PLANNER_MODEL_TEXT_LIMITS
        is search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS
    )
    assert _schema_path(
        schema,
        "answer_component_cross_field_conditions",
    )[3]["allowed_support_kinds"]["exact_ordered_combinations"] == [
        list(item) for item in search_planner_model_prompt.SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS
    ]

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
    assert schema["answer_component"]["fields"]["max_inference_depth"] == {
        "json_type": "integer",
        "required": True,
        "minimum": 0,
        "adapter_normalization": ("adapter accepts integer-coercible values; emit a JSON integer"),
    }
    assert "semantic_slot_cross_field_conditions" not in schema
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
            "for_each_component_where": {"allowed_support_kinds": ["inferred"]},
            "then": {"owned_component_search_requirements": {"exact_item_count": 0}},
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
        {"component_id": {"must_equal": "parent component_search_requirement.component_id"}},
        {"source_obligation_candidate_ids": {"each_item_must_reference": "source_obligation_candidate.candidate_id"}},
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
        assert (
            _schema_path(schema, *schema_path)["max_length"]
            == (search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS[limit_key])
        )

    with pytest.raises(TypeError):
        search_planner_model_prompt.SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"] = 0


def test_sparse_prompt_contract_and_internal_rich_validator_are_both_enforced() -> None:
    valid_output = _sparse_planner_output()
    planner_input = _planner_input(_kernel()).to_adapter_payload()
    expected_prompt = search_planner_model_prompt.build_search_planner_model_prompt(planner_input)
    expected_prompt_meta = search_planner_model_prompt.prompt_metadata(expected_prompt)
    expected_sanitized = search_planner_model_adapter.accept_planner_model_output(
        valid_output,
        user_query_text=QUERY,
        requested_mode="balanced",
    )
    produced = _adapter(FakeAskModel(json.dumps(valid_output))).produce(planner_input)
    metadata = produced.pop("planner_model_metadata")

    assert produced == expected_sanitized
    assert metadata["planner_model_prompt_schema_version"] == SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION
    assert metadata["prompt_hash"] == expected_prompt_meta["prompt_hash"]
    assert metadata["prompt_length"] == expected_prompt_meta["prompt_length"]
    assert metadata["require_json"] is True
    assert metadata["raw_prompt_retained"] is False
    assert metadata["raw_model_response_retained"] is False
    assert metadata["provider_payload_retained"] is False

    invalid_cases = (
        lambda output: output["answer_components"][0].pop("user_facing_label"),
        lambda output: output.__setitem__("semantic_slots", {}),
        lambda output: output["semantic_slots"][0].__setitem__("status", "unsupported_status"),
        lambda output: output.__setitem__("answer_components", []),
        lambda output: output.__setitem__("question_meaning_summary", "x" * 421),
    )
    for mutate in invalid_cases:
        invalid_output = _planner_output()
        mutate(invalid_output)
        with pytest.raises(SearchPlannerModelAdapterError):
            search_planner_model_adapter.validate_and_sanitize_model_output(invalid_output)


def test_strict_type_predicate_matrix_covers_the_exact_licensed_partition() -> None:
    predicate_ids = [
        predicate_id for _, predicate_group in _STRICT_TYPE_PREDICATE_MATRIX for predicate_id in predicate_group
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


def test_continuity_seed_predicate_registry_is_complete_and_closed() -> None:
    assert len(_CONTINUITY_SEED_IDS) == 57
    assert len(set(_CONTINUITY_SEED_IDS)) == 57
    assert {predicate_id.value for predicate_id in _CONTINUITY_SEED_IDS} <= {
        predicate_id.value for predicate_id in SearchPlannerModelAdapterPredicateId
    }
    assert {predicate_id.value for predicate_id in _CONTINUITY_SEED_IDS} <= {
        predicate_id.value for predicate_id in SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY
    }


@pytest.mark.parametrize(
    "predicate_id",
    _CONTINUITY_SEED_IDS,
    ids=tuple(predicate_id.value for predicate_id in _CONTINUITY_SEED_IDS),
)
def test_continuity_seed_predicates_emit_from_current_witnesses(
    predicate_id: SearchPlannerModelAdapterPredicateId,
) -> None:
    error = _continuity_seed_error(predicate_id)

    assert error.predicate_id == predicate_id
    assert error.predicate_registry_version == (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION)
    assert error.failure_metadata.predicate_id == predicate_id
    assert error.failure_metadata.predicate_registry_version == (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION)


_UNIVERSAL_OR_DYNAMIC_PREDICATE_IDS = frozenset(
    {
        SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        SearchPlannerModelAdapterPredicateId.JSON_TOP_LEVEL_OBJECT_REQUIRED,
        SearchPlannerModelAdapterPredicateId.SEMANTIC_PROPOSAL_VALIDATION_FAILED,
        SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_PROVIDER_MODEL_AUTHORITY_FORBIDDEN,
        SearchPlannerModelAdapterPredicateId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
        SearchPlannerModelAdapterPredicateId.CLOSED_RUNTIME_CLAIM_FORBIDDEN,
        SearchPlannerModelAdapterPredicateId.RAW_OR_PRIVATE_FIELD_FORBIDDEN,
    }
)


def test_field_condition_witness_inventory_is_complete_and_one_to_one() -> None:
    inventory_ids = [witness.predicate_id for witness in _FIELD_CONDITION_WITNESS_INVENTORY]
    inventory_field_pairs = [
        (witness.field_path, witness.condition)
        for witness in _FIELD_CONDITION_WITNESS_INVENTORY
        if witness.scope == "field"
    ]
    inventory_field_ids = [
        witness.predicate_id for witness in _FIELD_CONDITION_WITNESS_INVENTORY if witness.scope == "field"
    ]
    exempt_ids = {witness.predicate_id for witness in _FIELD_CONDITION_WITNESS_INVENTORY if witness.scope != "field"}

    assert len(inventory_ids) == len(set(inventory_ids))
    assert len(inventory_ids) == 304
    assert set(inventory_ids) == set(SearchPlannerModelAdapterPredicateId)
    assert set(inventory_ids) == set(SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY)
    assert Counter(
        registration.mechanical_rule_id for registration in SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY.values()
    ) == {
        "M01": 14,
        "M02": 164,
        "M03": 49,
        "M04": 8,
        "M05": 9,
        "M06": 6,
        "M07": 41,
        "M08": 4,
        "M09": 1,
        "M10": 8,
    }
    assert exempt_ids == _UNIVERSAL_OR_DYNAMIC_PREDICATE_IDS
    assert len(inventory_field_pairs) == len(set(inventory_field_pairs))
    assert len(inventory_field_ids) == len(set(inventory_field_ids))


@pytest.mark.parametrize(
    "witness",
    _FIELD_CONDITION_WITNESS_INVENTORY,
    ids=tuple(f"{witness.field_path}:{witness.condition}" for witness in _FIELD_CONDITION_WITNESS_INVENTORY),
)
def test_field_condition_witness_inventory_emits_registered_predicate(
    witness: _FieldConditionWitness,
) -> None:
    error = witness.emit()
    registration = SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY[witness.predicate_id]

    assert error.predicate_id == witness.predicate_id
    assert error.failure_stage == witness.failure_stage
    assert error.failure_code == witness.failure_code
    assert error.mechanical_rule_id == witness.mechanical_rule_id
    assert error.predicate_registry_version == SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    assert registration.failure_stage == witness.failure_stage
    assert registration.failure_code == witness.failure_code
    assert registration.mechanical_rule_id == witness.mechanical_rule_id
    assert registration.predicate_registry_version == SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION


def _inventory_witness(
    field_path: str,
    condition: str,
) -> _FieldConditionWitness:
    matches = [
        witness
        for witness in _FIELD_CONDITION_WITNESS_INVENTORY
        if (witness.field_path, witness.condition) == (field_path, condition)
    ]
    assert len(matches) == 1
    return matches[0]


def test_field_exact_collision_groups_emit_distinct_predicates() -> None:
    collision_groups = (
        (
            "wrong_string_type",
            (
                ("top_level.question_meaning_summary", "not_json_string"),
                ("answer_component.user_facing_label", "not_json_string"),
                ("query_strategy_candidate.candidate_kind", "not_json_string"),
            ),
        ),
        (
            "missing_identifier",
            (
                ("semantic_slot.slot_id", "missing"),
                ("answer_component.component_id", "missing"),
                ("relationship_hypothesis.hypothesis_id", "missing"),
                ("relationship_hypothesis.target_component_id", "missing"),
                ("component_search_requirement.requirement_id", "missing"),
                ("query_strategy_candidate.strategy_id", "missing"),
            ),
        ),
        (
            "invalid_enum_value",
            (
                ("query_strategy_candidate.candidate_kind", "value_not_allowed"),
                ("query_strategy_candidate.requested_role", "value_not_allowed"),
                ("query_strategy_recon_requirement.posture", "value_not_allowed"),
            ),
        ),
        (
            "wrong_array_container",
            (
                ("answer_component.acceptance_criteria", "not_json_array"),
                ("semantic_slot.candidate_values", "not_json_array"),
                ("component_search_requirement.preferred_source_kinds", "not_json_array"),
                ("query_strategy_candidate.source_obligation_candidate_ids", "not_json_array"),
            ),
        ),
        (
            "required_and_optional_array_item_type",
            (
                ("answer_component.acceptance_criteria", "item_not_json_string"),
                ("semantic_slot.candidate_values", "item_not_json_string"),
            ),
        ),
        (
            "m02_scalar_and_array_item_overlength",
            (
                ("top_level.question_meaning_summary", "text_over_max"),
                ("top_level.mandatory_caveats", "item_text_over_max"),
            ),
        ),
        (
            "max_inference_depth_missing_and_boolean",
            (
                ("answer_component.max_inference_depth", "missing"),
                ("answer_component.max_inference_depth", "boolean_not_allowed"),
            ),
        ),
    )

    for group_name, keys in collision_groups:
        witnesses = [_inventory_witness(*key) for key in keys]
        emitted_predicates = [witness.emit().predicate_id for witness in witnesses]

        assert group_name
        assert emitted_predicates == [witness.predicate_id for witness in witnesses]
        assert None not in emitted_predicates
        assert len(emitted_predicates) == len(set(emitted_predicates))


@pytest.mark.parametrize(
    ("case_name", "mutate", "expected_predicate_id"),
    (
        (
            "required_free_text",
            lambda output, value: output.__setitem__("question_meaning_summary", value),
            SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_NOT_JSON_STRING,
        ),
        (
            "required_enum_text",
            lambda output, value: output["semantic_slots"][0].__setitem__("status", value),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_NOT_JSON_STRING,
        ),
        (
            "optional_free_text",
            lambda output, value: output["semantic_slots"][0].__setitem__("selected_value", value),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_SELECTED_VALUE_NOT_JSON_STRING,
        ),
        (
            "optional_enum_text",
            lambda output, value: output["answer_components"][0].__setitem__(
                "partial_answer_policy",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_NOT_JSON_STRING,
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
    expected_predicate_id: SearchPlannerModelAdapterPredicateId,
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _strict_text_type_error(mutate, wrong_value)

    assert case_name
    assert wrong_type
    assert error.predicate_id == expected_predicate_id
    assert str(error) == "model-visible text value must be a JSON string"


@pytest.mark.parametrize(
    ("field_name", "mutate", "expected_predicate_id"),
    (
        (
            "semantic_slot.selected_value",
            lambda output, value: output["semantic_slots"][0].__setitem__("selected_value", value),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_SELECTED_VALUE_NOT_JSON_STRING,
        ),
        (
            "answer_component.normalization_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "normalization_policy",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_NORMALIZATION_POLICY_NOT_JSON_STRING,
        ),
        (
            "answer_component.calculation_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "calculation_policy",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_CALCULATION_POLICY_NOT_JSON_STRING,
        ),
        (
            "answer_component.partial_answer_policy",
            lambda output, value: output["answer_components"][0].__setitem__(
                "partial_answer_policy",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_NOT_JSON_STRING,
        ),
        (
            "source_obligation_candidate.strictness",
            lambda output, value: output["source_obligation_candidates"][0].__setitem__(
                "strictness",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.SOURCE_OBLIGATION_STRICTNESS_NOT_JSON_STRING,
        ),
        (
            "component_search_requirement.recency_requirement",
            lambda output, value: output["component_search_requirements"][0].__setitem__(
                "recency_requirement",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_RECENCY_REQUIREMENT_NOT_JSON_STRING,
        ),
        (
            "contract_amendment_candidate.candidate_id",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "candidate_id",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_ID_NOT_JSON_STRING,
        ),
        (
            "contract_amendment_candidate.operation_kind",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "operation_kind",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_OPERATION_KIND_NOT_JSON_STRING,
        ),
        (
            "contract_amendment_candidate.summary",
            lambda output, value: output.setdefault("contract_amendment_candidates", [{}])[0].__setitem__(
                "summary",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.CONTRACT_AMENDMENT_CANDIDATE_SUMMARY_NOT_JSON_STRING,
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
    expected_predicate_id: SearchPlannerModelAdapterPredicateId,
) -> None:
    error = _strict_text_type_error(mutate, None)

    assert field_name
    assert error.predicate_id == expected_predicate_id
    assert str(error) == "model-visible text value must be a JSON string"


@pytest.mark.parametrize(
    ("field_name", "mutate", "expected_predicate_id"),
    (
        (
            "semantic_slot.candidate_values",
            lambda output, value: output["semantic_slots"][0].__setitem__("candidate_values", value),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUES_NOT_JSON_ARRAY,
        ),
        (
            "semantic_slot.normalization_notes",
            lambda output, value: output["semantic_slots"][0].__setitem__(
                "normalization_notes",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_NORMALIZATION_NOTES_NOT_JSON_ARRAY,
        ),
        (
            "answer_component.source_obligation_candidate_ids",
            lambda output, value: output["answer_components"][0].__setitem__(
                "source_obligation_candidate_ids",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_CANDIDATE_IDS_NOT_JSON_ARRAY,
        ),
        (
            "answer_component.dependency_component_ids",
            lambda output, value: output["answer_components"][0].__setitem__(
                "dependency_component_ids",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_COMPONENT_IDS_NOT_JSON_ARRAY,
        ),
        (
            "answer_component.mandatory_caveats",
            lambda output, value: output["answer_components"][0].__setitem__(
                "mandatory_caveats",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_MANDATORY_CAVEATS_NOT_JSON_ARRAY,
        ),
        (
            "answer_component.prohibited_upgrades",
            lambda output, value: output["answer_components"][0].__setitem__(
                "prohibited_upgrades",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PROHIBITED_UPGRADES_NOT_JSON_ARRAY,
        ),
        (
            "component_search_requirement.preferred_source_kinds",
            lambda output, value: output["component_search_requirements"][0].__setitem__(
                "preferred_source_kinds",
                value,
            ),
            SearchPlannerModelAdapterPredicateId.COMPONENT_SEARCH_REQUIREMENT_PREFERRED_SOURCE_KINDS_NOT_JSON_ARRAY,
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
    expected_predicate_id: SearchPlannerModelAdapterPredicateId,
) -> None:
    error = _strict_text_type_error(mutate, None)

    assert field_name
    assert error.predicate_id == expected_predicate_id
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
    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(omitted)
    assert field_name not in result_container(proposal)

    for value in ("", "   "):
        supplied = _planner_output()
        set_value(supplied, value)
        proposal = search_planner_model_adapter.validate_and_sanitize_model_output(supplied)
        assert field_name not in result_container(proposal)


def test_optional_text_list_omission_and_empty_array_remain_omissions() -> None:
    omitted = _planner_output()
    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(omitted)
    assert "candidate_values" not in proposal["semantic_slots"][0]

    empty_array = _planner_output()
    empty_array["semantic_slots"][0]["candidate_values"] = []
    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(empty_array)
    assert "candidate_values" not in proposal["semantic_slots"][0]


@pytest.mark.parametrize(
    ("array_kind", "mutate", "expected_predicate_id"),
    (
        (
            "required_top_level_text_array",
            lambda output, value: output.__setitem__("mandatory_caveats", [value]),
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_MANDATORY_CAVEAT_ITEM_NOT_JSON_STRING,
        ),
        (
            "optional_semantic_slot_text_array",
            lambda output, value: output["semantic_slots"][0].__setitem__(
                "candidate_values",
                [value],
            ),
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_CANDIDATE_VALUE_ITEM_NOT_JSON_STRING,
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
    expected_predicate_id: SearchPlannerModelAdapterPredicateId,
    wrong_type: str,
    wrong_value: Any,
) -> None:
    error = _strict_text_type_error(mutate, wrong_value)

    assert array_kind
    assert wrong_type
    assert error.predicate_id == expected_predicate_id
    assert str(error) == "model-visible text value must be a JSON string"


def test_valid_string_arrays_remain_normalized_and_ordered() -> None:
    model_output = _planner_output()
    model_output["mandatory_caveats"] = ["  first caveat ", "second   caveat"]
    model_output["semantic_slots"][0]["candidate_values"] = ["  first value ", "second   value"]

    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(model_output)

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
    assert (
        id_item_type.predicate_id
        == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_CANDIDATE_ID_ITEM_NOT_JSON_STRING
    )

    missing_id = _planner_output()
    missing_id["answer_components"][0]["source_obligation_candidate_ids"] = ["missing:fictional"]
    error = _model_output_error(missing_id)
    assert error.failure_stage == SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION
    assert error.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_ID_OR_CROSS_REFERENCE
    assert error.mechanical_rule_id == "M03"

    metadata_enum_type = _strict_text_type_error(
        lambda output, value: output["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][
            0
        ].__setitem__("candidate_kind", value),
        7,
    )
    assert metadata_enum_type.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE
    assert (
        metadata_enum_type.predicate_id
        == SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_NOT_JSON_STRING
    )

    invalid_metadata_enum = _planner_output()
    invalid_metadata_enum["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0][
        "candidate_kind"
    ] = "not-a-candidate-kind"
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
    assert (
        error.predicate_id
        == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KIND_ITEM_NOT_JSON_STRING
    )
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
    assert (
        error.predicate_id == SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_NOT_JSON_ARRAY
    )
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

    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(model_output)

    assert component_index == expected_index
    assert proposal["answer_components"][component_index]["allowed_support_kinds"] == support_kinds


def test_allowed_support_kinds_preserves_existing_string_normalization_and_order() -> None:
    model_output, component_index = _planner_output_with_support_kind_variant(["direct", "inferred"])
    model_output["answer_components"][component_index]["allowed_support_kinds"] = [
        "  direct ",
        " inferred  ",
    ]

    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(model_output)

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

    proposal = search_planner_model_adapter.validate_and_sanitize_model_output(model_output)

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
    assert error.predicate_id == SearchPlannerModelAdapterPredicateId.QUESTION_MEANING_SUMMARY_NOT_JSON_STRING
    assert error.__cause__ is None
    assert error.__context__ is None
    assert kernel.state.search_planner_proposal_state == {}
    assert kernel.state.search_planner_proposal_projection == {}
    assert kernel.state.search_planner_proposal_history == []
    assert rejected_marker not in repr(kernel.state)


def test_model_query_strategy_cannot_select_provider_or_model() -> None:
    kernel = _kernel()
    unsafe = _sparse_planner_output()
    unsafe["components"][0]["provider_name"] = "untrusted-provider"

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _produce(kernel, _adapter(FakeAskModel(json.dumps(unsafe))))

    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert kernel.state.search_planner_proposal_state == {}


def test_adapter_failure_code_inventory_is_stable_and_repository_owned() -> None:
    assert {item.value for item in SearchPlannerModelAdapterFailureCode} == {
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
        "INVALID_SEMANTIC_PROPOSAL",
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
        assert "predicate_id" in keyword_names

    expected_rules = {
        SearchPlannerModelAdapterFailureCode.INVALID_JSON: "M01",
        SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT: "M01",
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS: "M01",
        SearchPlannerModelAdapterFailureCode.MISSING_REQUIRED_NESTED_FIELD: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_COUNT: "M02",
        SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL: "M02",
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
        matching_predicates = [
            predicate_id
            for predicate_id, registration in (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY.items())
            if registration.failure_code == code
        ]
        predicate_id = matching_predicates[0] if matching_predicates else None
        error = SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=code,
            predicate_id=predicate_id,
        )
        assert isinstance(
            error.failure_stage,
            SearchPlannerModelAdapterFailureStage,
        )
        assert error.mechanical_rule_id == expected_rules.get(code)
        if error.mechanical_rule_id is None:
            assert error.predicate_registry_version is None
            assert error.predicate_id is None
        else:
            assert error.predicate_registry_version == (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION)
            assert error.predicate_id == predicate_id


def test_predicate_registry_and_failure_metadata_are_fail_closed_and_immutable() -> None:
    registry = SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY

    assert len(SearchPlannerModelAdapterPredicateId.__members__) == len(SearchPlannerModelAdapterPredicateId)
    assert len(registry) == len(SearchPlannerModelAdapterPredicateId)
    assert set(registry) == set(SearchPlannerModelAdapterPredicateId)
    for predicate_id, registration in registry.items():
        assert predicate_id.value == predicate_id.name
        assert registration.predicate_registry_version == (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION)
        assert registration.mechanical_rule_id.startswith("M")
        assert registration.failure_code in SearchPlannerModelAdapterFailureCode
        assert registration.failure_stage in SearchPlannerModelAdapterFailureStage

    with pytest.raises(TypeError):
        registry[SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED] = registry[
            SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED
        ]

    registration = registry[SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED]
    metadata = SearchPlannerModelAdapterFailureMetadata(
        failure_stage=registration.failure_stage,
        failure_code=registration.failure_code,
        mechanical_rule_id=registration.mechanical_rule_id,
        predicate_registry_version=registration.predicate_registry_version,
        predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
    )
    assert metadata.predicate_id == SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED

    with pytest.raises(TypeError):
        SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=SearchPlannerModelAdapterFailureCode.INVALID_JSON,
        )
    with pytest.raises(ValueError, match="mechanical failures require predicate"):
        SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=SearchPlannerModelAdapterFailureCode.INVALID_JSON,
            predicate_id=None,
        )
    with pytest.raises(ValueError, match="infrastructure failures"):
        SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=SearchPlannerModelAdapterFailureCode.ADAPTER_DISABLED,
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        )
    with pytest.raises(ValueError, match="does not match its registration"):
        SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=SearchPlannerModelAdapterFailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        )
    with pytest.raises(ValueError, match="not registered"):
        SearchPlannerModelAdapterError(
            "bounded synthetic message",
            failure_code=SearchPlannerModelAdapterFailureCode.INVALID_JSON,
            predicate_id="UNREGISTERED_PREDICATE",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="registry version"):
        SearchPlannerModelAdapterFailureMetadata(
            failure_stage=registration.failure_stage,
            failure_code=registration.failure_code,
            mechanical_rule_id=registration.mechanical_rule_id,
            predicate_registry_version="wrong_registry_version",
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        )
    with pytest.raises(ValueError, match="failure_stage does not match"):
        SearchPlannerModelAdapterFailureMetadata(
            failure_stage=SearchPlannerModelAdapterFailureStage.INPUT,
            failure_code=registration.failure_code,
            mechanical_rule_id=registration.mechanical_rule_id,
            predicate_registry_version=registration.predicate_registry_version,
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        )
    with pytest.raises(ValueError, match="mechanical_rule_id does not match"):
        SearchPlannerModelAdapterFailureMetadata(
            failure_stage=registration.failure_stage,
            failure_code=registration.failure_code,
            mechanical_rule_id="M02",
            predicate_registry_version=registration.predicate_registry_version,
            predicate_id=SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        )


def test_public_message_and_digest_baselines_are_preserved_across_m01_to_m10() -> None:
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(FakeAskModel("{")).produce(_planner_input(_kernel()).to_adapter_payload())
    invalid_json = caught.value

    invalid_policy = _planner_output()
    invalid_policy["answer_components"][0]["partial_answer_policy"] = "invalid_partial_answer_policy"
    invalid_reference = _planner_output()
    invalid_reference["answer_components"][0]["source_obligation_candidate_ids"] = ["missing:obligation"]
    invalid_dependency = _planner_output()
    dependency_component = invalid_dependency["answer_components"][0]
    dependency_component["allowed_support_kinds"] = ["inferred"]
    dependency_component["source_obligation_candidate_ids"] = []
    dependency_component["max_inference_depth"] = 1
    dependency_component["dependency_component_ids"] = [
        "component:model-official-threshold",
        "component:model-official-threshold",
    ]
    invalid_support_tuple = _planner_output()
    invalid_support_tuple["answer_components"][0]["allowed_support_kinds"] = [
        "direct",
        "direct",
    ]
    invalid_purpose = _planner_output()
    invalid_purpose["answer_components"][0]["component_purpose"] = "invalid_component_purpose"
    invalid_strategy = _planner_output()
    invalid_strategy["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0][
        "candidate_kind"
    ] = "invalid_candidate_kind"
    forbidden_authority = _planner_output()
    forbidden_authority["answer"] = "forbidden"
    raw_material = _planner_output()
    raw_material["raw_payload"] = "forbidden"
    stale_binding = _planner_output()
    stale_binding["component_search_requirements"][0]["metadata"]["query_strategy_candidates"][0]["component_id"] = (
        "component:other"
    )

    expected_cases = (
        (
            invalid_json,
            SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
            "search planner model output was not valid JSON",
            "139912cee10aee310b3a5fe407c851850abb9e6894edbce6f7a3a7ad51442f47",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_policy),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM,
            "unsupported partial answer policy: invalid_partial_answer_policy",
            "a50982ae79fed002029f60411c57ec4615df17954f79f2f2ee5e8aad45440f64",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_reference),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SOURCE_OBLIGATION_REFERENCE_UNRESOLVED,
            "component component:model-official-threshold references missing source obligation missing:obligation",
            "230b18e0e8dd8434d23ff77b88f4a56700ea8f498954168f64850299cc54b9f1",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_dependency),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_DEPENDENCY_IDS_DUPLICATE,
            "component component:model-official-threshold contains duplicate component dependencies",
            "cc24aa3bb98a295251f2b9366d893d01cd9ae7745d507c9b1a8e299498e74cbd",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_support_tuple),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_TUPLE_NOT_ALLOWED,
            "answer component component:model-official-threshold has an invalid support-kind combination",
            "8c28c8d2b8020f6cc6b0f54e649feffb0da758bcf79e1779ce6fcf68f1451d31",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_purpose),
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_COMPONENT_PURPOSE_VALUE_NOT_ALLOWED,
            "unsupported value for component_purpose: invalid_component_purpose",
            "c3fcd278d63d314bf77b5da18ac89767d7d1b6b886dded45cb5bb10b2c11c640",  # pragma: allowlist secret
        ),
        (
            _model_output_error(invalid_strategy),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_CANDIDATE_KIND_VALUE_NOT_ALLOWED,
            "unsupported value for candidate_kind: invalid_candidate_kind",
            "50f83a9e60f6563be08ffe8db2ca37977a7cdbf922e87e9a4ff5671b825df30b",  # pragma: allowlist secret
        ),
        (
            _model_output_error(forbidden_authority),
            SearchPlannerModelAdapterPredicateId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
            "search planner model output contains closed authority fields: answer",
            "f13a36cc17242ff3457a7853b5dca75e5d5f3520c813b2791e5ab3a78d4c4396",  # pragma: allowlist secret
        ),
        (
            _model_output_error(raw_material),
            SearchPlannerModelAdapterPredicateId.RAW_OR_PRIVATE_FIELD_FORBIDDEN,
            "search planner model output contains raw/private fields: raw_payload",
            "4fb6ba9899d8be07aa65c8ec4a1c784a0e3a2241c5fddde4d19432c7cdcd56d8",  # pragma: allowlist secret
        ),
        (
            _model_output_error(stale_binding),
            SearchPlannerModelAdapterPredicateId.QUERY_STRATEGY_COMPONENT_BINDING_STALE,
            "query strategy strategy:model-official-threshold:primary has stale component binding",
            "a72885a78d8f74658332ac2116122871c6c92710cd099826153f0f7f83fb1b5d",  # pragma: allowlist secret
        ),
    )

    for error, predicate_id, expected_message, expected_digest in expected_cases:
        assert str(error) == expected_message
        assert error.args == (expected_message,)
        assert sha256(str(error).encode("utf-8")).hexdigest() == expected_digest
        assert error.predicate_id == predicate_id
        assert error.predicate_registry_version == (SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION)
        assert predicate_id.value not in str(error)
        assert predicate_id.value not in error.args[0]
        assert error.__cause__ is None
        assert error.__context__ is None


def test_predicate_precedence_preserves_existing_first_failure_order() -> None:
    two_missing_top_level = _planner_output()
    two_missing_top_level.pop("question_meaning_summary")
    two_missing_top_level.pop("requested_output")

    wrong_type_before_invalid_value = _planner_output()
    wrong_type_before_invalid_value["semantic_slots"][0]["status"] = 7
    wrong_type_before_invalid_value["answer_components"][0]["component_purpose"] = "invalid_component_purpose"

    invalid_support_item_before_matrix = _planner_output()
    invalid_support_item_before_matrix["answer_components"][0]["allowed_support_kinds"] = ["unsupported"]
    invalid_support_item_before_matrix["answer_components"][0]["max_inference_depth"] = 1

    invalid_reference_before_dependency = _planner_output()
    invalid_reference_before_dependency["answer_components"][0]["semantic_slot_ids"] = ["missing:slot"]
    invalid_reference_before_dependency["answer_components"][0]["dependency_component_ids"] = [
        "component:model-official-threshold",
        "component:model-official-threshold",
    ]

    forbidden_authority_before_unrelated_invalid_field = _planner_output()
    forbidden_authority_before_unrelated_invalid_field["answer"] = "forbidden"
    forbidden_authority_before_unrelated_invalid_field["answer_components"][0]["requirement_posture"] = (
        "invalid_requirement_posture"
    )

    raw_material_before_structural_failure = _planner_output()
    raw_material_before_structural_failure["raw_payload"] = "forbidden"
    raw_material_before_structural_failure["semantic_slots"] = []

    expected_cases = (
        (
            two_missing_top_level,
            SearchPlannerModelAdapterPredicateId.TOP_LEVEL_QUESTION_MEANING_SUMMARY_MISSING,
        ),
        (
            wrong_type_before_invalid_value,
            SearchPlannerModelAdapterPredicateId.SEMANTIC_SLOT_STATUS_NOT_JSON_STRING,
        ),
        (
            invalid_support_item_before_matrix,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_ALLOWED_SUPPORT_KINDS_ITEM_VALUE_NOT_ALLOWED,
        ),
        (
            invalid_reference_before_dependency,
            SearchPlannerModelAdapterPredicateId.ANSWER_COMPONENT_SEMANTIC_SLOT_REFERENCE_UNRESOLVED,
        ),
        (
            forbidden_authority_before_unrelated_invalid_field,
            SearchPlannerModelAdapterPredicateId.CLOSED_AUTHORITY_FIELD_FORBIDDEN,
        ),
        (
            raw_material_before_structural_failure,
            SearchPlannerModelAdapterPredicateId.RAW_OR_PRIVATE_FIELD_FORBIDDEN,
        ),
    )
    for model_output, expected_predicate_id in expected_cases:
        error = _model_output_error(model_output)
        assert error.predicate_id == expected_predicate_id


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
