"""Focused offline proof for PlannerRevision failure-cause projection.

Mode: REPAIR.
Test class: phase_focus / offline_product_path_proof.
No test in this file is integration-, provider-, or secrets-backed.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import proplex.__main__ as compatibility_cli
from core.cap_enforcement import ExternalCallFamily, RunCapExceeded
from core.initial_query_strategy_failure import (
    INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY,
    project_initial_query_strategy_failure_for_terminal,
    search_planner_revision_runtime_failure,
)
from core.run_config import RunConfig
from core.search_planner_revision_model_adapter import (
    SearchPlannerRevisionModelAdapter,
    SearchPlannerRevisionModelAdapterError,
)
from core.search_planner_revision_runtime import (
    SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION,
    SearchPlannerRevisionInput,
    SearchPlannerRevisionRuntimeError,
    SearchPlannerRevisionRuntimeSafeFailureCode,
    _call_adapter,
    execute_search_planner_revision_action,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PRIVATE_SENTINEL = "fixture-private-plannerrevision-detail"


class _FakeModelFailure(RuntimeError):
    pass


def _model_input() -> dict[str, Any]:
    return {
        "run_id": "run:failure-projection",
        "request_id": "request:failure-projection",
        "component_id": "component:1",
        "consumed_ambiguity_dimension_ids": ["dimension:1"],
        "consumed_scout_hint_ids": ["hint:1"],
        "scout_directional_context": {},
        "safe_revision_context": {},
        "closed_surface_flags": {},
    }


def _valid_model_output() -> dict[str, Any]:
    return {
        "revised_question_meaning_summary": "Preserve non-evidence direction.",
        "semantic_slot_updates": [],
        "answer_component_updates": [],
        "component_search_requirement_updates": [],
        "mandatory_caveats": [],
        "prohibited_upgrades": [],
        "normalization_obligations": [],
        "assumptions": [],
        "unresolved_ambiguities": [],
        "consumed_ambiguity_dimension_ids": ["dimension:1"],
        "consumed_scout_hint_ids": ["hint:1"],
        "amendment_candidates": [],
        "closed_surface_flags": {},
    }


def _model_adapter(model_callable: Callable[..., Any]) -> SearchPlannerRevisionModelAdapter:
    return SearchPlannerRevisionModelAdapter(
        revision_model_callable=model_callable,
        enabled=True,
        licensed=True,
    )


def _response_model(response: Any) -> Callable[..., Any]:
    def produce(*_args: Any, **_kwargs: Any) -> Any:
        return response

    return produce


def _adapter_error_for_response(response: Any) -> SearchPlannerRevisionModelAdapterError:
    with pytest.raises(SearchPlannerRevisionModelAdapterError) as captured:
        _model_adapter(_response_model(response)).produce(_model_input())
    return captured.value


def _projection_for(exc: BaseException) -> dict[str, str]:
    projection = project_initial_query_strategy_failure_for_terminal(exc)
    assert projection is not None
    return projection


def _assert_projection_code(exc: BaseException, code: SearchPlannerRevisionRuntimeSafeFailureCode) -> None:
    projection = _projection_for(exc)
    assert projection == {
        "schema_version": "initial_query_strategy_failure_v1",
        "boundary": "initial_query_strategy",
        "failure_origin": "search_planner_revision_runtime",
        "failure_code": code.value,
    }


def test_model_call_failure_has_closed_cause_without_exception_detail() -> None:
    def fail_model(*_args: Any, **_kwargs: Any) -> Any:
        raise _FakeModelFailure(_PRIVATE_SENTINEL)

    with pytest.raises(SearchPlannerRevisionModelAdapterError) as captured:
        _model_adapter(fail_model).produce(_model_input())

    assert captured.value.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_CALL_FAILED
    _assert_projection_code(
        captured.value,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_CALL_FAILED,
    )


def test_invalid_json_has_a_distinct_closed_cause_and_no_raw_terminal_material() -> None:
    error = _adapter_error_for_response("not-json: " + _PRIVATE_SENTINEL)

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_JSON
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_JSON,
    )
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=error,
        config=RunConfig(query="offline PlannerRevision failure projection"),
    )
    terminal = payload["terminal"]
    assert terminal[INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY] == {
        "schema_version": "initial_query_strategy_failure_v1",
        "boundary": "initial_query_strategy",
        "failure_origin": "search_planner_revision_runtime",
        "failure_code": "model_output_invalid_json",
    }
    assert _PRIVATE_SENTINEL not in json.dumps(payload, sort_keys=True)


def test_non_object_model_json_has_a_distinct_closed_cause() -> None:
    error = _adapter_error_for_response("[]")

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_NOT_OBJECT
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_NOT_OBJECT,
    )


def test_missing_required_model_fields_have_a_closed_cause() -> None:
    error = _adapter_error_for_response(json.dumps({"revised_question_meaning_summary": "bounded"}))

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_MISSING_REQUIRED_FIELDS
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_MISSING_REQUIRED_FIELDS,
    )


def test_invalid_model_field_shape_has_a_closed_cause() -> None:
    payload = _valid_model_output()
    payload["semantic_slot_updates"] = {"not": "an array"}
    error = _adapter_error_for_response(json.dumps(payload))

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_FIELD_SHAPE
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_FIELD_SHAPE,
    )


def test_unsafe_model_authority_claim_has_a_closed_cause() -> None:
    payload = _valid_model_output()
    payload["citation_eligible"] = True
    error = _adapter_error_for_response(json.dumps(payload))

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_UNSAFE_OR_CLOSED_AUTHORITY
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_UNSAFE_OR_CLOSED_AUTHORITY,
    )


def test_invalid_model_amendment_has_a_closed_cause() -> None:
    payload = _valid_model_output()
    payload["amendment_candidates"] = [{"operation_kind": "resolve_slot"}]
    error = _adapter_error_for_response(json.dumps(payload))

    assert error.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_AMENDMENT
    _assert_projection_code(
        error,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_AMENDMENT,
    )


def test_stale_scout_direction_has_a_distinct_runtime_cause() -> None:
    planner_ref = {
        "proposal_id": "planner:1",
        "proposal_digest": "planner-digest",
        "question_meaning_record_id": "qmr:1",
        "question_meaning_record_digest": "qmr-digest",
    }
    parent_scout_ref = {
        "report_id": "scout:1",
        "report_digest": "scout-digest",
        "component_id": "component:1",
        "parent_search_planner_proposal_ref": planner_ref,
    }
    stale_scout_ref = {**parent_scout_ref, "report_digest": "stale-scout-digest"}
    revision_input = SearchPlannerRevisionInput(
        run_id="run:failure-projection",
        request_id="request:failure-projection",
        parent_search_planner_proposal_ref=planner_ref,
        parent_scout_disambiguation_report_ref=parent_scout_ref,
        parent_initial_contract_ref={},
        component_id="component:1",
        consumed_ambiguity_dimension_ids=["dimension:1"],
        consumed_scout_hint_ids=["hint:1"],
        scout_directional_context={
            "schema_version": SCOUT_DIRECTIONAL_CONTEXT_SCHEMA_VERSION,
            "parent_scout_disambiguation_report_ref": stale_scout_ref,
            "component_id": "component:1",
            "consumed_ambiguity_dimension_ids": ["dimension:1"],
            "consumed_scout_hint_ids": ["hint:1"],
            "directional_hints": [],
            "non_evidence": True,
            "scout_hints_are_evidence": False,
            "evidence_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
        },
    )

    with pytest.raises(SearchPlannerRevisionRuntimeError) as captured:
        revision_input.to_adapter_payload()

    assert captured.value.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.SCOUT_DIRECTIONAL_CONTEXT_INVALID
    _assert_projection_code(
        captured.value,
        SearchPlannerRevisionRuntimeSafeFailureCode.SCOUT_DIRECTIONAL_CONTEXT_INVALID,
    )


def test_invalid_revision_action_binding_has_a_distinct_runtime_cause() -> None:
    invalid_action = SimpleNamespace(
        action_type="wrong-action",
        expected_observation_type="search_planner_revised",
        inputs={},
    )
    revision_input = SearchPlannerRevisionInput(
        run_id="",
        request_id="",
        parent_search_planner_proposal_ref={},
        parent_scout_disambiguation_report_ref={},
        parent_initial_contract_ref={},
    )

    with pytest.raises(SearchPlannerRevisionRuntimeError) as captured:
        execute_search_planner_revision_action(
            action=invalid_action,
            revision_input=revision_input,
            adapter=lambda _input: {},
        )

    assert captured.value.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.REVISION_ACTION_BINDING_INVALID
    _assert_projection_code(
        captured.value,
        SearchPlannerRevisionRuntimeSafeFailureCode.REVISION_ACTION_BINDING_INVALID,
    )


def test_untyped_injected_adapter_failure_uses_only_the_historic_generic_code() -> None:
    def untyped_adapter(_input: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(_PRIVATE_SENTINEL)

    with pytest.raises(SearchPlannerRevisionRuntimeError) as captured:
        _call_adapter(untyped_adapter, {})

    assert (
        captured.value.failure_code is SearchPlannerRevisionRuntimeSafeFailureCode.SEARCH_PLANNER_REVISION_RUNTIME_ERROR
    )
    projection = _projection_for(captured.value)
    assert projection["failure_code"] == "search_planner_revision_runtime_error"
    assert _PRIVATE_SENTINEL not in json.dumps(projection, sort_keys=True)
    assert search_planner_revision_runtime_failure().failure_code == projection["failure_code"]


def test_model_run_cap_exceeded_propagates_unchanged() -> None:
    cap = RunCapExceeded(
        "model_attempt_cap",
        family=ExternalCallFamily.MODEL,
        internal_message=_PRIVATE_SENTINEL,
    )

    def exhaust_cap(*_args: Any, **_kwargs: Any) -> Any:
        raise cap

    with pytest.raises(RunCapExceeded) as captured:
        _model_adapter(exhaust_cap).produce(_model_input())

    assert captured.value is cap


def test_valid_model_adapter_path_retains_the_existing_sanitized_proposal_shape() -> None:
    expected = _valid_model_output()
    result = _model_adapter(_response_model(json.dumps(expected))).produce(_model_input())

    for key, value in expected.items():
        assert result[key] == value
    assert result["planner_revision_model_metadata"]["raw_prompt_retained"] is False
    assert result["planner_revision_model_metadata"]["raw_model_response_retained"] is False
    assert result["planner_revision_model_metadata"]["provider_payload_retained"] is False


def _raise_failure_codes(path: Path, exception_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        function = node.exc.func
        name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)
        if name != exception_name:
            continue
        code_keyword = next(
            (keyword for keyword in node.exc.keywords if keyword.arg == "failure_code"),
            None,
        )
        assert code_keyword is not None, f"{path.name}:{node.lineno} lacks failure_code="
        value = code_keyword.value
        if isinstance(value, ast.Name):
            assert value.id == "failure_code"
            continue
        assert isinstance(value, ast.Attribute)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "SearchPlannerRevisionRuntimeSafeFailureCode"
        codes.add(value.attr)
    return codes


def test_every_reachable_plannerrevision_raise_uses_the_closed_owner_enum() -> None:
    runtime_codes = _raise_failure_codes(
        _REPO_ROOT / "core" / "search_planner_revision_runtime.py",
        "SearchPlannerRevisionRuntimeError",
    )
    adapter_codes = _raise_failure_codes(
        _REPO_ROOT / "core" / "search_planner_revision_model_adapter.py",
        "SearchPlannerRevisionModelAdapterError",
    )

    assert runtime_codes | adapter_codes == {member.name for member in SearchPlannerRevisionRuntimeSafeFailureCode}
