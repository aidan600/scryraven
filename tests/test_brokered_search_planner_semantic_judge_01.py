from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from scripts.evaluation.brokered_search_planner_semantic_judge import (
    BrokeredSearchPlannerSemanticJudge,
    BrokeredSemanticJudgeError,
    parse_semantic_pass_judgment,
    validate_semantic_result_execution_pair,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SemanticJudgmentContractError,
    build_semantic_judgment_request,
)
from tests.helpers.search_planner_owner_specific_fakes import (
    FakeOwnerSpecificBrokerFactory,
    authorization_bundle,
    requirement_packet,
)

REPOSITORY_SHA = "3a76a3a24efef5ee4bec2d43e301463b671f0d80"


def _semantic_request():
    proposed_plan = {
        "answer_components": [
            {
                "component_id": "component:fictional-threshold",
                "component_purpose": "user_facing_answer_target",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": "obligation:official-current",
                "obligation_kind": "official_current",
            }
        ],
    }
    proposal_digest = sha256(
        json.dumps(
            proposed_plan,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    mechanical_ref = "mechanical-result:" + sha256(
        b"synthetic-mechanical-result"
    ).hexdigest()
    requirements = requirement_packet()
    return build_semantic_judgment_request(
        normalized_user_request=(
            "What is the fictional Alder threshold?"
        ),
        planner_input={
            "requested_mode": "Balanced",
            "safe_context": {"fictional": True},
        },
        essential_requirements=requirements.essential_requirements,
        proposed_plan=proposed_plan,
        mechanical_validation_summary={
            "owner": "CanonicalSearchPlannerMechanicalAuthority",
            "overall_posture": "PASS",
            "result_id": mechanical_ref,
            "product_proposal_digest": proposal_digest,
        },
        evaluation_budget_identity="synthetic-budget:v1",
        essential_architecture_constraints=(
            requirements.essential_architecture_constraints
        ),
        prohibited_upgrades_or_shortcuts=(
            requirements.prohibited_upgrades_or_shortcuts
        ),
    )


def _adapter(tmp_path, factory=None):
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    selected_factory = factory or FakeOwnerSpecificBrokerFactory()
    transport = selected_factory(
        type(
            "Route",
            (),
            {
                "provider": authorization.semantic_judge_route.provider,
                "model": authorization.semantic_judge_route.model,
                "reasoning_effort": (
                    authorization.semantic_judge_route.reasoning_effort
                ),
                "allowed_model_roles": (
                    authorization.semantic_judge_route.role,
                ),
                "require_observed_usage": True,
            },
        )()
    )
    return (
        BrokeredSearchPlannerSemanticJudge(
            transport=transport,
            route=authorization.semantic_judge_route,
        ),
        selected_factory,
    )


def _met_pass(request) -> str:
    return json.dumps(
        {
            "status": "MET",
            "requirement_mappings": [
                {
                    "requirement_id": item.requirement_id,
                    "proposal_paths": ["/answer_components/0"],
                    "bounded_explanation": (
                        "The canonical proposal contains bounded material."
                    ),
                }
                for item in request.essential_requirements
            ],
            "issues": [],
            "ambiguities": [],
        }
    )


def _not_met_pass(request) -> str:
    return json.dumps(
        {
            "status": "NOT_MET",
            "requirement_mappings": [],
            "issues": [
                {
                    "requirement_id": (
                        request.essential_requirements[0].requirement_id
                    ),
                    "issue_kind": "MISSING",
                    "proposal_paths": ["/answer_components/0"],
                    "answer_blocking": True,
                    "bounded_explanation": (
                        "The plan does not fully represent the requirement."
                    ),
                }
            ],
            "ambiguities": [],
        }
    )


def test_two_live_shaped_passes_return_provider_neutral_result_and_observation(
    tmp_path,
) -> None:
    adapter, factory = _adapter(tmp_path)
    request = _semantic_request()

    outcome = adapter.judge(
        request,
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )

    assert outcome.semantic_result is not None
    assert outcome.semantic_result.final_status == "MET"
    assert outcome.semantic_result.provider_selected is False
    assert outcome.semantic_result.model_selected is False
    assert outcome.semantic_result.live_call_count == 0
    observation = outcome.execution_observation
    assert observation.reconciliation_posture == "PASS"
    assert observation.semantic_judge_call_cap_consumption == {
        "primary_calls": 1,
        "adversarial_calls": 1,
        "total_calls": 2,
    }
    assert observation.primary_pass.call_id != (
        observation.adversarial_pass.call_id
    )
    assert observation.primary_pass.execution_identity_digest != (
        observation.adversarial_pass.execution_identity_digest
    )
    assert len(factory.calls) == 2
    validate_semantic_result_execution_pair(
        outcome.semantic_result,
        observation,
    )


def test_two_pass_disagreement_remains_review_required(
    tmp_path,
) -> None:
    request = _semantic_request()
    factory = FakeOwnerSpecificBrokerFactory(
        semantic_outputs=[
            _met_pass(request),
            _not_met_pass(request),
        ]
    )
    adapter, _ = _adapter(tmp_path, factory)

    outcome = adapter.judge(
        request,
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )

    assert outcome.semantic_result is not None
    assert outcome.semantic_result.final_status == "REVIEW_REQUIRED"
    assert outcome.execution_observation.reconciliation_posture == "PASS"


def test_malformed_primary_pass_cannot_produce_semantic_met(
    tmp_path,
) -> None:
    factory = FakeOwnerSpecificBrokerFactory(
        semantic_outputs=["not-json"]
    )
    adapter, _ = _adapter(tmp_path, factory)

    outcome = adapter.judge(
        _semantic_request(),
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )

    assert outcome.semantic_result is None
    assert outcome.execution_observation.reconciliation_posture == "NOT_RUN"
    assert (
        outcome.execution_observation.primary_pass.parse_posture
        == "FAIL"
    )
    assert (
        outcome.execution_observation.adversarial_pass.response_presence_posture
        == "PRESENT"
    )
    assert (
        outcome.execution_observation.adversarial_pass.contract_validation_posture
        == "PASS"
    )
    assert outcome.execution_observation.semantic_judge_call_cap_consumption == {
        "primary_calls": 1,
        "adversarial_calls": 1,
        "total_calls": 2,
    }
    assert len(factory.calls) == 2


def test_malformed_adversarial_pass_cannot_produce_semantic_met(
    tmp_path,
) -> None:
    request = _semantic_request()
    factory = FakeOwnerSpecificBrokerFactory(
        semantic_outputs=[_met_pass(request), "{}"]
    )
    adapter, _ = _adapter(tmp_path, factory)

    outcome = adapter.judge(
        request,
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )

    assert outcome.semantic_result is None
    assert outcome.execution_observation.reconciliation_posture == "NOT_RUN"
    assert (
        outcome.execution_observation.primary_pass.contract_validation_posture
        == "PASS"
    )
    assert (
        outcome.execution_observation.adversarial_pass.contract_validation_posture
        == "FAIL"
    )
    assert len(factory.calls) == 2


def test_judge_prompts_and_execution_observation_are_arm_blind(
    tmp_path,
) -> None:
    adapter, factory = _adapter(tmp_path)
    request = _semantic_request()
    sentinels = (
        "CONTROL_ONLY_SENTINEL",
        "VARIANT_ONLY_SENTINEL",
        "ARM_ID_SENTINEL",
        "TRIAL_ORDER_SENTINEL",
        "INSTRUCTION_DIGEST_SENTINEL",
    )

    outcome = adapter.judge(
        request,
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )

    sent_material = "\n".join(
        call["prompt"] + call["system_prompt"]
        for call in factory.calls
    )
    observation_packet = json.dumps(
        outcome.execution_observation.to_packet(),
        sort_keys=True,
    )
    for sentinel in sentinels:
        assert sentinel not in sent_material
        assert sentinel not in observation_packet
    forbidden_keys = {
        "arm_id",
        "trial_order",
        "variant",
        "control",
        "instruction_digest",
    }
    assert not forbidden_keys.intersection(
        outcome.execution_observation.to_packet()
    )


def test_semantic_result_requires_one_exact_matching_observation(
    tmp_path,
) -> None:
    adapter, _ = _adapter(tmp_path)
    outcome = adapter.judge(
        _semantic_request(),
        primary_call_id="primary-call",
        adversarial_call_id="adversarial-call",
    )
    assert outcome.semantic_result is not None
    mismatched = replace(
        outcome.execution_observation,
        proposal_digest="0" * 64,
    )

    with pytest.raises(
        BrokeredSemanticJudgeError,
        match="do not bind exactly",
    ):
        validate_semantic_result_execution_pair(
            outcome.semantic_result,
            mismatched,
        )


def test_pass_parser_rejects_unknown_fields_and_nonfinite_json() -> None:
    with pytest.raises(
        BrokeredSemanticJudgeError,
        match="fields differ",
    ):
        parse_semantic_pass_judgment(
            json.dumps(
                {
                    "status": "MET",
                    "requirement_mappings": [],
                    "issues": [],
                    "ambiguities": [],
                    "unknown": True,
                }
            )
        )
    with pytest.raises(
        BrokeredSemanticJudgeError,
        match="non-finite",
    ):
        parse_semantic_pass_judgment(
            (
                '{"status":"MET","requirement_mappings":[],'
                '"issues":[],"ambiguities":[],"x":NaN}'
            )
        )


def test_semantic_owner_still_rejects_mechanical_nonpass() -> None:
    request = _semantic_request()
    with pytest.raises(
        SemanticJudgmentContractError,
        match="requires mechanical PASS",
    ):
        replace(
            request,
            mechanical_validation_summary={
                **request.mechanical_validation_summary,
                "overall_posture": "FAIL",
            },
        )
