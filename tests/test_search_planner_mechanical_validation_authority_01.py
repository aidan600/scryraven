"""Phase-focus proof for deterministic SearchPlanner mechanical authority.

Proof class: CONTRACT-INVARIANT. Surface guarded: M01-M17 result ownership.
Runtime path guarded: typed observation of the canonical product boundary.
Expected cost: tiny deterministic unit proof. Promotion posture: phase_focus
until a durable evaluator lane exists. Fast-PR posture: not promoted because
the ordinary fast_pr sentinels already guard broader repository health.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.evaluation.search_planner_mechanical_validation import (
    MECHANICAL_RULES,
    validate_product_observation,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_REF,
    CANONICAL_PRODUCT_BOUNDARY_VERSION,
    PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION,
    AskModelArgumentShape,
    ProductBoundaryObservation,
    PromptDigestObservation,
)


def _hex(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _observation() -> ProductBoundaryObservation:
    return ProductBoundaryObservation(
        schema_version=PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION,
        owner="CanonicalProductSearchPlannerBoundary",
        boundary_ref=CANONICAL_PRODUCT_BOUNDARY_REF,
        boundary_version=CANONICAL_PRODUCT_BOUNDARY_VERSION,
        boundary_status="PASS",
        product_boundary_reached=True,
        model_call_count=1,
        prompt_identity=PromptDigestObservation(
            semantic_input_digest=_hex("input"),
            semantic_input_length=20,
            system_prompt_digest=_hex("system"),
            system_prompt_length=30,
            instruction_digest=_hex("instruction"),
            instruction_length=40,
            full_prompt_digest=_hex("full"),
            full_prompt_length=60,
            extraction_posture="PASS",
        ),
        ask_model_argument_shape=AskModelArgumentShape(
            positional_shape=("prompt:str", "system_prompt:str"),
            keyword_names=(
                "api_key",
                "cost_accumulator",
                "cost_phase",
                "effort",
                "model",
                "provider",
                "require_json",
            ),
            keyword_types={
                "api_key": "str",  # pragma: allowlist secret
                "cost_accumulator": "object",
                "cost_phase": "str",
                "effort": "str",
                "model": "str",
                "provider": "str",
                "require_json": "bool",
            },
            require_json=True,
            provider_present=True,
            model_present=True,
            reasoning_effort_present=True,
            cost_accumulator_present=True,
            cost_phase="search_planner",
            credential_argument_present=True,
        ),
        output_digest=_hex("output"),
        output_length=100,
        response_received=True,
        response_cleaning_posture=("PRODUCT_OWNED:core.text_utils.clean_json_response"),
        parser_posture="PASS",
        validator_posture="PASS",
        runtime_projection_posture="PASS",
        initial_acceptance_posture="PASS",
        search_work_plan_posture="PASS",
        incomplete_generation_posture="COMPLETE",
        canonical_failure_rule_ids=(),
        bounded_failure_reason=None,
        safe_usage_refs=(),
        safe_execution_refs=({"execution_ref": _hex("execution")},),
        proposal_digest=_hex("canonical-proposal"),
    )


def test_mechanical_registry_covers_all_seventeen_approved_rules() -> None:
    assert [rule_id for rule_id, _rule in MECHANICAL_RULES] == [f"M{index:02d}" for index in range(1, 18)]
    assert len({rule for _rule_id, rule in MECHANICAL_RULES}) == 17


def test_successful_product_observation_passes_all_mechanical_rules() -> None:
    result = validate_product_observation(_observation())
    assert result.owner == "CanonicalSearchPlannerMechanicalAuthority"
    assert result.result_id.startswith("mechanical-result:")
    assert len(result.product_observation_digest) == 64
    assert result.overall_posture == "PASS"
    assert result.semantic_judgment_allowed is True
    assert result.product_proposal_digest == _hex("canonical-proposal")


def test_mechanical_result_identity_rejects_posture_substitution() -> None:
    result = validate_product_observation(_observation())
    with pytest.raises(
        ValueError,
        match="identity does not cover",
    ):
        replace(
            result,
            result_id=f"mechanical-result:{'0' * 64}",
        )
    assert result.blocking_failure_rule_ids == ()
    assert result.review_required_rule_ids == ()
    assert [item.posture for item in result.rule_results] == ["PASS"] * 17


def test_parser_failure_blocks_semantic_success() -> None:
    observation = replace(
        _observation(),
        boundary_status="FAIL",
        parser_posture="FAIL",
        validator_posture="NOT_REACHED",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        canonical_failure_rule_ids=("M01",),
    )
    result = validate_product_observation(observation)
    rules = {item.rule_id: item for item in result.rule_results}
    assert result.overall_posture == "FAIL"
    assert result.semantic_judgment_allowed is False
    assert rules["M01"].posture == "FAIL"
    assert rules["M01"].blocks_semantic_judgment is True
    assert rules["M02"].posture == "NOT_REACHED"


def test_required_envelope_failure_is_owned_by_m01_after_parser_pass() -> None:
    observation = replace(
        _observation(),
        boundary_status="FAIL",
        validator_posture="FAIL",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        canonical_failure_rule_ids=("M01",),
    )
    result = validate_product_observation(observation)
    rules = {item.rule_id: item for item in result.rule_results}

    assert observation.parser_posture == "PASS"
    assert result.overall_posture == "FAIL"
    assert rules["M01"].posture == "FAIL"
    assert rules["M01"].observation_refs == (
        "parser_posture",
        "canonical_failure_rule:M01",
    )
    assert rules["M02"].posture == "NOT_REACHED"


def test_canonical_dependency_failure_is_owned_only_by_m04() -> None:
    observation = replace(
        _observation(),
        boundary_status="FAIL",
        validator_posture="FAIL",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        canonical_failure_rule_ids=("M04",),
        bounded_failure_reason="dependency graph is invalid",
    )
    result = validate_product_observation(observation)
    rules = {item.rule_id: item for item in result.rule_results}
    assert result.overall_posture == "FAIL"
    assert rules["M01"].posture == "PASS"
    assert rules["M04"].posture == "FAIL"
    assert rules["M03"].posture == "NOT_REACHED"
    assert rules["M04"].observation_refs == (
        "validator_posture",
        "canonical_failure_rule:M04",
    )


def test_product_boundary_not_reached_cannot_produce_mechanical_pass() -> None:
    observation = replace(
        _observation(),
        boundary_status="NOT_REACHED",
        product_boundary_reached=False,
        model_call_count=0,
        prompt_identity=None,
        ask_model_argument_shape=None,
        output_digest=None,
        output_length=0,
        response_received=False,
        response_cleaning_posture="NOT_REACHED",
        parser_posture="NOT_REACHED",
        validator_posture="NOT_REACHED",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        incomplete_generation_posture="NOT_REACHED",
    )
    result = validate_product_observation(observation)
    assert result.overall_posture == "NOT_REACHED"
    assert result.semantic_judgment_allowed is False
    assert all(item.posture != "PASS" for item in result.rule_results)


def test_incomplete_generation_blocks_parser_and_semantic_scoring() -> None:
    observation = replace(
        _observation(),
        boundary_status="FAIL",
        output_digest=None,
        output_length=0,
        response_received=False,
        parser_posture="NOT_REACHED",
        validator_posture="NOT_REACHED",
        runtime_projection_posture="NOT_REACHED",
        initial_acceptance_posture="NOT_REACHED",
        search_work_plan_posture="NOT_REACHED",
        incomplete_generation_posture="INCOMPLETE",
    )
    result = validate_product_observation(observation)
    rule = next(item for item in result.rule_results if item.rule_id == "M13")
    assert rule.posture == "FAIL"
    assert result.overall_posture == "FAIL"
    assert result.semantic_judgment_allowed is False


def test_mechanical_owner_contains_no_semantic_or_teacher_oracle() -> None:
    source = Path("scripts/evaluation/search_planner_mechanical_validation.py").read_text(encoding="utf-8").casefold()
    for forbidden in (
        "teacher_answer",
        "fixture_alias",
        "preferred_graph",
        "normalized_user_request",
        "semantic correctness",
    ):
        assert forbidden not in source
