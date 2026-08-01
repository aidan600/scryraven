"""Phase-focus proof for the canonical SearchPlanner boundary observer.

Proof class: PRODUCT-PATH-REGRESSION.
Surface guarded: ordinary SearchPlanner composition and sanitized observation.
High-custody surface: model-call prompt/response material remains transient.
Runtime path: ``core.pipeline_orchestrator.run_pipeline``.
Expected cost: bounded offline fake execution.
Promotion posture: remain phase_focus until a durable evaluator lane exists.
Retirement condition: only with a successor ordinary-boundary equivalence proof.
Fast-PR posture: not a sentinel candidate because the full ordinary fixture is
materially more expensive than the tiny fast_pr budget.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest
from pytest import MonkeyPatch

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.search_planner_model_adapter import (
    SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION,
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
    SearchPlannerModelAdapterFailureStage,
    SearchPlannerModelAdapterPredicateId,
)
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from core.text_utils import clean_json_response
from scripts.evaluation.search_planner_mechanical_validation import (
    validate_product_observation,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_REF,
    PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION,
    CanonicalProductSearchPlannerBoundaryObserver,
    ProductBoundaryObservation,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    SCENARIOS,
    SearchOSAnalystOSHarness,
    planner_payload,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_PACKET,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

SCENARIO = SCENARIOS[0]
_PROMPT_MARKER = "Sanitized planner input JSON:\n"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _model_payload() -> dict[str, Any]:
    payload = planner_payload(SCENARIO)
    payload.pop("planner_model_metadata", None)
    for obligation in payload["source_obligation_candidates"]:
        obligation["obligation_kind"] = "official_current"
        obligation["strictness"] = "required"
    return payload


def _observe_adapter_result(
    response: Any,
    *,
    cleaner: Any = clean_json_response,
    later_failure: Exception | None = None,
) -> tuple[Exception | None, ProductBoundaryObservation]:
    response_text = (
        response
        if isinstance(response, str | Exception)
        else json.dumps(response)
    )

    def synthetic_model_call(
        _prompt: str,
        _system_prompt: str,
        **_kwargs: Any,
    ) -> str:
        if isinstance(response_text, Exception):
            raise response_text
        return response_text

    observer = CanonicalProductSearchPlannerBoundaryObserver(synthetic_model_call)

    def observed_model_call(
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        kwargs["cost_accumulator"] = object()
        kwargs["cost_phase"] = "search_planner"
        return observer(prompt, system_prompt, **kwargs)

    adapter = SearchPlannerModelAdapter(
        ask_model=observed_model_call,
        clean_json_response=cleaner,
        provider="synthetic-provider",
        model="synthetic-model",
        effort="fixed",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )
    proposal: Mapping[str, Any] | None = None
    failure: Exception | None = None
    try:
        proposal = adapter.produce(
            {
                "user_query_text_for_planning": (
                    "attestation-input-private-sentinel"
                ),
                "safe_context": {},
            }
        )
    except Exception as exc:
        failure = exc
    if later_failure is not None:
        assert failure is None
        assert proposal is not None
        failure = later_failure
    kernel = SimpleNamespace(
        state=SimpleNamespace(
            search_planner_proposal_state={},
            initial_answer_contract_projection={},
            search_work_plan={},
        )
    )
    return failure, observer.finalize(
        run_kernel=kernel,
        failure=failure,
        validated_proposal_returned=proposal is not None,
    )


class _BoundaryHarness(SearchOSAnalystOSHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        observed: bool,
        invalid: bool = False,
    ) -> None:
        super().__init__(tmp_path, SCENARIO)
        self.invalid = invalid
        self.safe_direct_call: dict[str, Any] = {}
        self.observer = CanonicalProductSearchPlannerBoundaryObserver(self._scripted_model_call) if observed else None

    def deps(self):
        return replace(
            super().deps(),
            ask_model=self.observer or self._scripted_model_call,
            clean_json_response=clean_json_response,
            search_planner_adapter=None,
        )

    def _scripted_model_call(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt != SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
            return super().ask_model(prompt, system_prompt, **kwargs)
        prefix, packet_text = prompt.split(_PROMPT_MARKER, 1)
        packet = json.loads(packet_text)
        planner_input = _canonical(packet["planner_input"])
        instruction = prefix + _PROMPT_MARKER
        response = (
            "not-json"
            if self.invalid
            else "synthetic-prefix\n" + json.dumps(_model_payload(), sort_keys=True) + "\nsynthetic-suffix"
        )
        self.safe_direct_call = {
            "semantic_input_digest": _digest(planner_input),
            "semantic_input_length": len(planner_input),
            "system_prompt_digest": _digest(system_prompt),
            "system_prompt_length": len(system_prompt),
            "instruction_digest": _digest(instruction),
            "instruction_length": len(instruction),
            "full_prompt_digest": _digest(prompt),
            "full_prompt_length": len(prompt),
            "keyword_names": tuple(sorted(kwargs)),
            "keyword_types": {key: type(value).__name__ for key, value in sorted(kwargs.items())},
            "require_json": kwargs.get("require_json") is True,
            "provider_present": bool(kwargs.get("provider")),
            "model_present": bool(kwargs.get("model")),
            "cost_accumulator_present": (kwargs.get("cost_accumulator") is not None),
            "cost_phase": kwargs.get("cost_phase"),
            "output_digest": _digest(response),
            "output_length": len(response),
        }
        return response


def _run(
    tmp_path: Path,
    *,
    observed: bool,
    invalid: bool = False,
) -> tuple[_BoundaryHarness, Any, Exception | None, dict[str, str]]:
    monkeypatch = MonkeyPatch()
    tmp_path.mkdir(parents=True, exist_ok=True)
    harness = _BoundaryHarness(
        tmp_path,
        observed=observed,
        invalid=invalid,
    )
    try:
        scrub_offline_runtime(monkeypatch)
        captured = install_handoff_capture(
            monkeypatch,
            capture_stages=(HANDOFF_PACKET,),
        )
        config = replace(
            offline_balanced_run_config(
                query=SCENARIO.root_query,
                current_date="2026-07-29",
                session_id="evaluation-split-equivalence",
                run_id="evaluation-split-equivalence",
                smart_search_judgment_model=True,
            ),
            mode=SCENARIO.mode,
        )
        failure = None
        outcome = None
        try:
            outcome = orchestrator.run_pipeline(
                config,
                harness.deps(),
                NullStatusWriter(),
                CostAccumulator(),
            )
        except Exception as exc:
            failure = exc
        kernel = captured.get("run_kernel")
        state = getattr(kernel, "state", None)
        state_digests = {
            "proposal": _digest(_canonical(getattr(state, "search_planner_proposal_state", None))),
            "acceptance": _digest(
                _canonical(
                    getattr(
                        state,
                        "initial_answer_contract_projection",
                        None,
                    )
                )
            ),
            "search_work_plan": _digest(_canonical(getattr(state, "search_work_plan", None))),
            "outcome": _digest(str(getattr(outcome, "report", ""))),
        }
        return harness, kernel, failure, state_digests
    finally:
        monkeypatch.undo()


def test_observer_matches_exact_ordinary_product_boundary(
    tmp_path: Path,
) -> None:
    direct, _direct_kernel, direct_failure, direct_state = _run(
        tmp_path / "direct",
        observed=False,
    )
    observed, kernel, observed_failure, observed_state = _run(
        tmp_path / "observed",
        observed=True,
    )
    assert direct_failure is None
    assert observed_failure is None
    assert direct.safe_direct_call == observed.safe_direct_call
    assert direct_state == observed_state

    observation = observed.observer.finalize(run_kernel=kernel)
    prompt = observation.prompt_identity
    shape = observation.ask_model_argument_shape
    assert prompt is not None
    assert shape is not None
    assert asdict(prompt) == {
        "semantic_input_digest": direct.safe_direct_call["semantic_input_digest"],
        "semantic_input_length": direct.safe_direct_call["semantic_input_length"],
        "system_prompt_digest": direct.safe_direct_call["system_prompt_digest"],
        "system_prompt_length": direct.safe_direct_call["system_prompt_length"],
        "instruction_digest": direct.safe_direct_call["instruction_digest"],
        "instruction_length": direct.safe_direct_call["instruction_length"],
        "full_prompt_digest": direct.safe_direct_call["full_prompt_digest"],
        "full_prompt_length": direct.safe_direct_call["full_prompt_length"],
        "extraction_posture": "PASS",
    }
    assert shape.keyword_names == direct.safe_direct_call["keyword_names"]
    assert shape.keyword_types == direct.safe_direct_call["keyword_types"]
    assert observation.output_digest == direct.safe_direct_call["output_digest"]
    assert observation.output_length == direct.safe_direct_call["output_length"]
    assert observation.proposal_digest == observed_state["proposal"]
    assert observation.boundary_ref == CANONICAL_PRODUCT_BOUNDARY_REF
    assert observation.parser_posture == "PASS"
    assert observation.validator_posture == "PASS"
    assert observation.runtime_projection_posture == "PASS"
    assert observation.initial_acceptance_posture == "PASS"
    assert observation.search_work_plan_posture == "PASS"
    assert PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION == (
        "search_planner_product_boundary_observer_v2"
    )
    assert observation.schema_version == PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION
    assert observation.canonical_failure_predicate_registry_version is None
    assert observation.canonical_failure_predicate_id is None


def test_observer_preserves_product_fail_closed_posture(
    tmp_path: Path,
) -> None:
    direct, _direct_kernel, direct_failure, _direct_state = _run(
        tmp_path / "direct-failure",
        observed=False,
        invalid=True,
    )
    observed, kernel, observed_failure, _observed_state = _run(
        tmp_path / "observed-failure",
        observed=True,
        invalid=True,
    )
    assert direct_failure is not None
    assert observed_failure is not None
    assert type(direct_failure) is type(observed_failure)
    assert str(direct_failure) == str(observed_failure)
    assert direct.safe_direct_call == observed.safe_direct_call

    observation = observed.observer.finalize(
        run_kernel=kernel,
        failure=observed_failure,
    )
    assert observation.boundary_status == "FAIL"
    assert observation.parser_posture == "FAIL"
    assert observation.validator_posture == "NOT_REACHED"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.initial_acceptance_posture == "NOT_REACHED"


@pytest.mark.parametrize(
    ("response", "expected_code", "expected_predicate"),
    (
        (
            "not-json-private-output-sentinel",
            SearchPlannerModelAdapterFailureCode.INVALID_JSON,
            SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED,
        ),
        (
            "[]",
            SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT,
            SearchPlannerModelAdapterPredicateId.JSON_TOP_LEVEL_OBJECT_REQUIRED,
        ),
        (
            "42",
            SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT,
            SearchPlannerModelAdapterPredicateId.JSON_TOP_LEVEL_OBJECT_REQUIRED,
        ),
        (
            '"scalar-private-output-sentinel"',
            SearchPlannerModelAdapterFailureCode.JSON_VALUE_NOT_OBJECT,
            SearchPlannerModelAdapterPredicateId.JSON_TOP_LEVEL_OBJECT_REQUIRED,
        ),
    ),
)
def test_json_parse_failures_are_typed_m01_and_stop_before_runtime(
    response: str,
    expected_code: SearchPlannerModelAdapterFailureCode,
    expected_predicate: SearchPlannerModelAdapterPredicateId,
) -> None:
    failure, observation = _observe_adapter_result(response)

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert (
        failure.failure_stage
        == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    )
    assert failure.failure_code == expected_code
    assert failure.mechanical_rule_id == "M01"
    assert failure.predicate_registry_version == (
        SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    )
    assert failure.predicate_id == expected_predicate
    assert observation.parser_posture == "FAIL"
    assert observation.validator_posture == "NOT_REACHED"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.canonical_failure_rule_ids == ("M01",)
    assert observation.canonical_failure_predicate_registry_version == (
        failure.predicate_registry_version
    )
    assert observation.canonical_failure_predicate_id == (
        failure.predicate_id.value
    )
    mechanical = validate_product_observation(observation)
    rules = {item.rule_id: item for item in mechanical.rule_results}
    assert rules["M01"].posture == "FAIL"
    assert all(
        rules[f"M{index:02d}"].posture != "FAIL"
        for index in range(2, 11)
    )


def test_output_cleaner_failure_is_typed_and_never_blames_runtime() -> None:
    raw_cleaner_failure = "private-cleaner-exception-sentinel"

    def failing_cleaner(_value: str) -> str:
        raise RuntimeError(raw_cleaner_failure)

    failure, observation = _observe_adapter_result(
        _model_payload(),
        cleaner=failing_cleaner,
    )

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert (
        failure.failure_stage
        == SearchPlannerModelAdapterFailureStage.OUTPUT_CLEANING
    )
    assert (
        failure.failure_code
        == SearchPlannerModelAdapterFailureCode.OUTPUT_CLEANING_FAILED
    )
    assert failure.mechanical_rule_id is None
    assert failure.predicate_registry_version is None
    assert failure.predicate_id is None
    assert observation.parser_posture == "FAIL"
    assert observation.validator_posture == "NOT_REACHED"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.canonical_failure_rule_ids == ()
    assert observation.canonical_failure_predicate_registry_version is None
    assert observation.canonical_failure_predicate_id is None
    assert observation.bounded_failure_reason == (
        "SearchPlannerModelAdapterError:"
        "failure_stage=OUTPUT_CLEANING:"
        "failure_code=OUTPUT_CLEANING_FAILED:"
        f"message_sha256={_digest(str(failure))}"
    )
    assert raw_cleaner_failure not in json.dumps(
        observation.to_packet(),
        sort_keys=True,
    )
    rules = {
        item.rule_id: item
        for item in validate_product_observation(observation).rule_results
    }
    assert rules["M01"].posture == "FAIL"


def test_model_call_failure_is_typed_before_parser_and_runtime() -> None:
    raw_model_failure = "private-model-invocation-exception-sentinel"

    failure, observation = _observe_adapter_result(
        RuntimeError(raw_model_failure)
    )

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert (
        failure.failure_stage
        == SearchPlannerModelAdapterFailureStage.MODEL_CALL
    )
    assert (
        failure.failure_code
        == SearchPlannerModelAdapterFailureCode.MODEL_CALL_FAILED
    )
    assert failure.mechanical_rule_id is None
    assert failure.predicate_registry_version is None
    assert failure.predicate_id is None
    assert observation.response_received is False
    assert observation.parser_posture == "NOT_REACHED"
    assert observation.validator_posture == "NOT_REACHED"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.canonical_failure_rule_ids == ()
    assert observation.canonical_failure_predicate_registry_version is None
    assert observation.canonical_failure_predicate_id is None
    assert raw_model_failure not in json.dumps(
        observation.to_packet(),
        sort_keys=True,
    )


def _m02_invalid_nested_type(payload: dict[str, Any]) -> None:
    payload["semantic_slots"] = {}


def _m03_invalid_cross_reference(payload: dict[str, Any]) -> None:
    payload["answer_components"][0]["semantic_slot_ids"] = [
        "model-generated-missing-slot-sentinel"
    ]


def _m04_invalid_dependency(payload: dict[str, Any]) -> None:
    component_id = payload["answer_components"][0]["component_id"]
    payload["answer_components"][0]["dependency_component_ids"] = [
        component_id
    ]


def _m05_invalid_support_matrix(payload: dict[str, Any]) -> None:
    payload["answer_components"][0]["max_inference_depth"] = 1


def _m06_invalid_component_purpose(payload: dict[str, Any]) -> None:
    payload["answer_components"][0]["component_purpose"] = (
        "model-generated-invalid-purpose-sentinel"
    )


def _m07_invalid_query_strategy(payload: dict[str, Any]) -> None:
    payload["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ] = []


def _m08_closed_authority(payload: dict[str, Any]) -> None:
    payload["current_answer_contract"] = {
        "model-generated-authority-value-sentinel": True
    }


def _m09_raw_material(payload: dict[str, Any]) -> None:
    payload["raw_provider_payload"] = (
        "model-generated-private-payload-sentinel"
    )


def _m10_stale_binding(payload: dict[str, Any]) -> None:
    payload["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]["component_id"] = "model-generated-stale-binding-sentinel"


@pytest.mark.parametrize(
    ("rule_id", "stage", "code", "mutate"),
    (
        (
            "M02",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_NESTED_TYPE,
            _m02_invalid_nested_type,
        ),
        (
            "M03",
            SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_ID_OR_CROSS_REFERENCE,
            _m03_invalid_cross_reference,
        ),
        (
            "M04",
            SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH,
            _m04_invalid_dependency,
        ),
        (
            "M05",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_SUPPORT_MATRIX,
            _m05_invalid_support_matrix,
        ),
        (
            "M06",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION,
            _m06_invalid_component_purpose,
        ),
        (
            "M07",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.INVALID_QUERY_STRATEGY_METADATA,
            _m07_invalid_query_strategy,
        ),
        (
            "M08",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.CLOSED_AUTHORITY_VIOLATION,
            _m08_closed_authority,
        ),
        (
            "M09",
            SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
            SearchPlannerModelAdapterFailureCode.PRIVACY_OR_RAW_MATERIAL_VIOLATION,
            _m09_raw_material,
        ),
        (
            "M10",
            SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
            SearchPlannerModelAdapterFailureCode.LINEAGE_OR_BINDING_FAILURE,
            _m10_stale_binding,
        ),
    ),
)
def test_validator_failure_attestation_maps_exactly_m02_through_m10(
    rule_id: str,
    stage: SearchPlannerModelAdapterFailureStage,
    code: SearchPlannerModelAdapterFailureCode,
    mutate: Any,
) -> None:
    payload = deepcopy(_model_payload())
    mutate(payload)

    failure, observation = _observe_adapter_result(payload)

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert failure.failure_stage == stage
    assert failure.failure_code == code
    assert failure.mechanical_rule_id == rule_id
    assert failure.predicate_registry_version == (
        SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    )
    assert failure.predicate_id is not None
    assert failure.args == (str(failure),)
    assert observation.parser_posture == "PASS"
    assert observation.validator_posture == "FAIL"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.canonical_failure_rule_ids == (rule_id,)
    assert observation.canonical_failure_predicate_registry_version == (
        failure.predicate_registry_version
    )
    assert observation.canonical_failure_predicate_id == (
        failure.predicate_id.value
    )
    rules = {
        item.rule_id: item
        for item in validate_product_observation(observation).rule_results
    }
    assert rules[rule_id].posture == "FAIL"
    assert all(
        rules[f"M{index:02d}"].posture != "FAIL"
        for index in range(1, 11)
        if f"M{index:02d}" != rule_id
    )


def test_validated_proposal_followed_by_runtime_failure_is_distinct() -> None:
    misleading_later_message = (
        "search planner model output was not valid JSON but this is a later "
        "runtime failure"
    )
    failure, observation = _observe_adapter_result(
        _model_payload(),
        later_failure=RuntimeError(misleading_later_message),
    )

    assert isinstance(failure, RuntimeError)
    assert observation.parser_posture == "PASS"
    assert observation.validator_posture == "PASS"
    assert observation.runtime_projection_posture == "FAIL"
    assert observation.initial_acceptance_posture == "NOT_REACHED"
    assert observation.canonical_failure_rule_ids == ()
    assert observation.canonical_failure_predicate_registry_version is None
    assert observation.canonical_failure_predicate_id is None
    assert misleading_later_message not in json.dumps(
        observation.to_packet(),
        sort_keys=True,
    )


def test_unexpected_post_response_failure_does_not_overclaim_validation() -> None:
    observer = CanonicalProductSearchPlannerBoundaryObserver(
        lambda _prompt, _system_prompt, **_kwargs: "{}"
    )
    observer(
        "synthetic prompt",
        SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        provider="synthetic-provider",
    )
    failure = RuntimeError("unexpected-private-failure-sentinel")

    observation = observer.finalize(
        run_kernel=SimpleNamespace(
            state=SimpleNamespace(
                search_planner_proposal_state={},
                initial_answer_contract_projection={},
                search_work_plan={},
            )
        ),
        failure=failure,
    )

    assert observation.parser_posture == "REVIEW_REQUIRED"
    assert observation.validator_posture == "REVIEW_REQUIRED"
    assert observation.runtime_projection_posture == "NOT_REACHED"


def test_adapter_failure_metadata_and_packet_are_immutable_and_sanitized() -> None:
    payload = deepcopy(_model_payload())
    _m10_stale_binding(payload)
    model_component_id = payload["answer_components"][0]["component_id"]
    model_field_value = payload["answer_components"][0][
        "user_facing_question"
    ]
    model_query_text = payload["component_search_requirements"][0][
        "metadata"
    ]["query_strategy_candidates"][0]["candidate_query_text"]

    failure, observation = _observe_adapter_result(payload)

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert failure.predicate_registry_version == (
        SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    )
    assert failure.predicate_id is not None
    with pytest.raises(FrozenInstanceError):
        setattr(
            failure.failure_metadata,
            "failure_code",
            SearchPlannerModelAdapterFailureCode.INVALID_JSON,
        )
    with pytest.raises(AttributeError):
        setattr(
            failure,
            "_failure_metadata",
            failure.failure_metadata,
        )
    packet = observation.to_packet()
    serialized = json.dumps(packet, sort_keys=True)
    for forbidden in (
        "attestation-input-private-sentinel",
        "model-generated-stale-binding-sentinel",
        model_component_id,
        model_field_value,
        model_query_text,
        str(failure),
        failure.args[0],
    ):
        assert forbidden not in serialized
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    assert packet["observer_parsed_model_output"] is False
    assert packet["canonical_failure_predicate_registry_version"] == (
        SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION
    )
    assert packet["canonical_failure_predicate_id"] == failure.predicate_id.value
    assert packet["bounded_failure_reason"] == (
        "SearchPlannerModelAdapterError:"
        "failure_stage=CROSS_REFERENCE_VALIDATION:"
        "failure_code=LINEAGE_OR_BINDING_FAILURE:"
        "mechanical_rule_id=M10:"
        "predicate_registry_version="
        f"{SEARCH_PLANNER_MODEL_PREDICATE_REGISTRY_VERSION}:"
        f"predicate_id={failure.predicate_id.value}:"
        f"message_sha256={_digest(str(failure))}"
    )


def test_observer_predicate_fields_are_closed_and_paired() -> None:
    failure, observation = _observe_adapter_result(
        "not-json-private-output-sentinel"
    )

    assert isinstance(failure, SearchPlannerModelAdapterError)
    assert observation.canonical_failure_predicate_id is not None
    with pytest.raises(
        ValueError,
        match="canonical failure predicate identities must be paired",
    ):
        replace(
            observation,
            canonical_failure_predicate_id=None,
        )
    with pytest.raises(
        ValueError,
        match="canonical failure predicate identity is unsupported",
    ):
        replace(
            observation,
            canonical_failure_predicate_id="MODEL_DERIVED_PREDICATE_SENTINEL",
        )


def test_observer_stage_classification_contains_no_message_search() -> None:
    source = Path(
        "scripts/evaluation/search_planner_product_boundary_observer.py"
    ).read_text(encoding="utf-8")
    assert "str(failure).casefold()" not in source
    assert '"valid json" in reason' not in source.casefold()
    assert '"json object" in reason' not in source.casefold()


def test_observer_retains_only_safe_digest_and_shape_facts(
    tmp_path: Path,
) -> None:
    harness, kernel, failure, _state = _run(
        tmp_path / "privacy",
        observed=True,
    )
    assert failure is None
    observation = harness.observer.finalize(run_kernel=kernel)
    packet = observation.to_packet()
    serialized = json.dumps(packet, sort_keys=True).casefold()
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    assert packet["observer_parsed_model_output"] is False
    assert SCENARIO.root_query.casefold() not in serialized
    assert "synthetic-prefix" not in serialized


def test_observer_delegates_nonplanner_model_roles_without_claiming_them() -> None:
    calls: list[str] = []

    def dependency(
        prompt: str,
        system_prompt: str,
        **_kwargs: Any,
    ) -> str:
        calls.append(f"{system_prompt}:{prompt}")
        return "delegated"

    observer = CanonicalProductSearchPlannerBoundaryObserver(dependency)
    assert observer("payload", "another-role", marker=True) == "delegated"
    assert calls == ["another-role:payload"]
    result = observer.finalize(run_kernel=None)
    assert result.product_boundary_reached is False
    assert result.boundary_status == "NOT_REACHED"


def test_observer_rejects_raw_material_disguised_as_safe_refs() -> None:
    observer = CanonicalProductSearchPlannerBoundaryObserver(lambda _prompt, _system, **_kwargs: "{}")
    prompt = f'Instruction.\n{_PROMPT_MARKER}{{"planner_input":{{"safe":"value"}}}}'
    observer(
        prompt,
        SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        provider="synthetic",
        model="synthetic",
        effort="fixed",
        require_json=True,
        cost_accumulator=object(),
        cost_phase="search_planner",
    )
    with pytest.raises(ValueError, match="forbidden key: raw_prompt"):
        observer.finalize(
            run_kernel=None,
            safe_execution_refs=({"raw_prompt": "must never enter an observation"},),
        )


def test_observer_failure_reason_retains_only_type_and_digest() -> None:
    raw_exception_material = "synthetic-private-response-material"

    def failing_dependency(
        _prompt: str,
        _system_prompt: str,
        **_kwargs: Any,
    ) -> str:
        raise RuntimeError(raw_exception_material)

    observer = CanonicalProductSearchPlannerBoundaryObserver(
        failing_dependency
    )
    prompt = (
        f'Instruction.\n{_PROMPT_MARKER}'
        '{"planner_input":{"safe":"value"}}'
    )
    with pytest.raises(RuntimeError) as captured:
        observer(
            prompt,
            SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider="synthetic",
            model="synthetic",
            effort="fixed",
            require_json=True,
            cost_accumulator=object(),
            cost_phase="search_planner",
        )
    observation = observer.finalize(
        run_kernel=None,
        failure=captured.value,
    )
    assert raw_exception_material not in str(
        observation.bounded_failure_reason
    )
    assert observation.bounded_failure_reason == (
        f"RuntimeError:message_sha256={_digest(raw_exception_material)}"
    )
    assert observation.canonical_failure_predicate_registry_version is None
    assert observation.canonical_failure_predicate_id is None
