"""PRODUCT-PATH-REGRESSION: D-prime assessment validation availability.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_assessment_validation availability
Why ordinary product-path work cannot be done directly: the ordinary status path
consumes validator availability; fixture records exercise the deterministic
validator without model review, live calls, support proposal packaging, or
RunKernel admission.
Integration deadline: current phase.
Exit condition: keep while D-prime assessment validation is available before
model review and assessment creation remains unlicensed.
Why this is not a shadow product path: it invokes the product status builder for
availability and the product-owned validator module for injected fixture records,
not a standalone alternate semantic-support path.
Forbidden interpretation: fixture validation is not model review, real product
assessment, semantic support, support proposal validation, RunKernel admission,
SemanticObservation admission, ComponentCoverage binding, citation eligibility,
answer text, source-obligation satisfaction, or product correctness.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import core.dprime_assessment_validation as assessment_validation
import core.dprime_negative_control_profile as profile_config
import core.dprime_support_proposal_schema as dprime
import proplex.live_semantic_coverage_status as semantic_status
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_COMPONENT_ID,
    PASSPORT_OBLIGATION_ID,
    QUERY,
    UNRELATED_SAME_LANE_TEXT,
    _passport_retained_repo,
)


def test_validator_availability_is_product_consumed_without_assessment(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "phase: DPRIME-ASSESSMENT-VALIDATION-01" in result.output
    assert "D-prime assessment validator status: available" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "D-prime assessment status: not reached" in result.output
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["assessment_validator_status"] == "available"
    assert dprime_status["objects_created"]["evidence_relative_support_assessment"] is False
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert (
        dprime_status["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is False
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False


def test_valid_fixture_assessment_schema_creates_no_support() -> None:
    payload = _assessment_payload()

    assessment = assessment_validation.EvidenceRelativeSupportAssessment.from_mapping(
        payload
    )
    result = assessment_validation.validate_evidence_relative_support_assessment(
        assessment
    )

    assert (
        result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_VALID
    ), result.errors
    assert result.schema_valid is True
    assert assessment.is_admitted_support is False
    assert result.creates_support is False
    assert result.creates_run_kernel_request is False
    result_payload = result.to_dict()
    assert result_payload["support_created"] is False
    assert result_payload["validated_support_proposal_created"] is False
    assert result_payload["run_kernel_support_admission_request_created"] is False
    assert result_payload["semantic_observation_created"] is False
    assert result_payload["component_coverage_created"] is False
    assert result_payload["answer_text_created"] is False
    assert result_payload["product_correctness_claimed"] is False


@pytest.mark.parametrize(
    ("support_relation", "expected_status"),
    [
        ("abstained", assessment_validation.ASSESSMENT_ABSTAINED),
        ("absent", assessment_validation.ASSESSMENT_NON_SUPPORT),
        ("scope_mismatch", assessment_validation.ASSESSMENT_NON_SUPPORT),
        ("currentness_mismatch", assessment_validation.ASSESSMENT_CHALLENGE_RECOMMENDED),
        ("contradicts", assessment_validation.ASSESSMENT_CHALLENGE_RECOMMENDED),
        ("missing_qualifier", assessment_validation.ASSESSMENT_NON_SUPPORT),
        (
            "weak_or_overclaim_risk",
            assessment_validation.ASSESSMENT_CHALLENGE_RECOMMENDED,
        ),
    ],
)
def test_abstention_and_non_support_relations_remain_non_support(
    support_relation: str,
    expected_status: str,
) -> None:
    payload = _assessment_payload(support_relation=support_relation)

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == expected_status, result.errors
    assert result.schema_valid is True
    assert result.creates_support is False
    assert result.to_dict()["support_created"] is False
    assert result.to_dict()["semantic_observation_created"] is False
    assert result.to_dict()["component_coverage_created"] is False


@pytest.mark.parametrize(
    "support_relation",
    [
        "yes",
        "supports",
        "support",
        "supported",
        "pass",
        "handled",
        "weak_support",
        "maybe_support",
    ],
)
def test_vague_support_relations_fail_closed(support_relation: str) -> None:
    payload = _assessment_payload(support_relation=support_relation)

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_INVALID
    assert any("vague" in error for error in result.errors)
    assert result.creates_support is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload.pop("preflight_ref"),
        lambda payload: payload.pop("preflight_digest"),
        lambda payload: payload.pop("negative_control_profile_ref"),
        lambda payload: payload.pop("negative_control_profile_digest"),
        lambda payload: payload.pop("source_proposition"),
        lambda payload: payload.pop("answer_component_claim"),
        lambda payload: payload.pop("component_ref"),
        lambda payload: payload.pop("selector_ref"),
        lambda payload: payload.pop("source_obligation_ref"),
        lambda payload: payload.pop("currentness_check"),
        lambda payload: payload.pop("contradiction_check"),
    ],
)
def test_missing_mapping_fields_fail_closed(mutator: Any) -> None:
    payload = _assessment_payload()
    mutator(payload)
    _refresh_digest(payload)

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_INVALID
    assert result.errors
    assert result.creates_support is False


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "ValidatedSupportProposal",
        "RunKernel admission request",
        "RunKernel decision",
        "SemanticObservation",
        "ComponentCoverage",
        "citation eligibility",
        "source-obligation satisfaction",
        "FAP",
        "Author",
        "answer_text",
        "product_correctness",
    ],
)
def test_authority_upgrade_fields_fail_closed(forbidden_field: str) -> None:
    payload = _assessment_payload()
    payload[forbidden_field] = True

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_INVALID
    assert result.errors
    assert result.creates_support is False


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "raw_prompt",
        "prompt",
        "raw_model_response",
        "model_response",
        "provider_payload",
        "raw_page_text",
        "raw_html",
        "headers",
        "cookies",
        "secret",
        "api_key",
        "bounded_text",
        "unbounded_text",
    ],
)
def test_raw_private_model_material_fails_closed(forbidden_field: str) -> None:
    payload = _assessment_payload()
    payload[forbidden_field] = "forbidden"

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_INVALID
    assert any("raw/private" in error for error in result.errors)
    assert result.creates_support is False


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda payload: payload.update({"negative_control_profile_status": ""}),
            "negative_control_profile_status is missing or failed",
        ),
        (
            lambda payload: payload["closed_surface_flags"].update(
                {"semantic_observation_created": True}
            ),
            "closed_surface_flags must keep semantic_observation_created false",
        ),
    ],
)
def test_negative_control_profile_ref_status_and_flags_are_required(
    mutator: Any,
    expected_error: str,
) -> None:
    payload = _assessment_payload()
    mutator(payload)

    result = assessment_validation.validate_evidence_relative_support_assessment(
        payload
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_SCHEMA_INVALID
    assert expected_error in result.errors


def test_invalid_negative_control_profile_blocks_assessment_validation() -> None:
    profile = profile_config.build_default_negative_control_profile()
    controls = tuple(
        control
        for control in profile.controls
        if control.control_id != "manual_reviewer_assertion_only_reject"
    )
    incomplete_profile = profile_config.build_negative_control_profile(
        controls=controls
    )

    result = assessment_validation.validate_evidence_relative_support_assessment(
        _assessment_payload(),
        negative_control_profile=incomplete_profile,
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_VALIDATION_BLOCKED
    assert any("missing mandatory controls" in error for error in result.errors)
    assert result.creates_support is False


def test_support_like_profile_expected_outcome_blocks_assessment_validation() -> None:
    profile = profile_config.build_default_negative_control_profile()
    controls = tuple(
        replace(control, expected_outcome="weak_support")
        if control.control_id == "same_lane_unrelated_official_text_no_support"
        else control
        for control in profile.controls
    )
    support_like_profile = profile_config.build_negative_control_profile(
        controls=controls
    )

    result = assessment_validation.validate_evidence_relative_support_assessment(
        _assessment_payload(),
        negative_control_profile=support_like_profile,
    )

    assert result.validation_status == assessment_validation.ASSESSMENT_VALIDATION_BLOCKED
    assert any("non-fail-closed expected_outcome" in error for error in result.errors)
    assert result.creates_support is False


def test_same_lane_unrelated_bounded_text_still_produces_no_assessment_or_support(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text=UNRELATED_SAME_LANE_TEXT,
    )

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "D-prime assessment validator status: available" in result.output
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["assessment_status"] == "not reached"
    assert dprime_status["objects_created"]["evidence_relative_support_assessment"] is False
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert (
        dprime_status["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is False
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert UNRELATED_SAME_LANE_TEXT not in result.output


def test_old_retained_support_consumer_not_reached_after_validator_availability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    def fail_consumer(**_kwargs: Any) -> Any:
        raise AssertionError("old retained support consumer must not be reached")

    monkeypatch.setattr(
        semantic_status,
        "build_retained_custody_semantic_coverage",
        fail_consumer,
    )

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "D-prime assessment validator status: available" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "Analyst support proposal status: not reached" in result.output


def _assessment_payload(*, support_relation: str = "directly_supports") -> dict[str, Any]:
    profile = profile_config.build_default_negative_control_profile()
    profile_ref = profile_config.negative_control_profile_ref(profile)
    payload = {
        "assessment_id": f"fixture-assessment:{support_relation}",
        "assessment_digest": "",
        "preflight_ref": {
            "frame_id": "dprime-evidence-frame-preflight:fixture",
            "frame_digest": "fixture-preflight-digest",
            "frame_eligibility_only": True,
            "model_browse_allowed": False,
        },
        "preflight_digest": "fixture-preflight-digest",
        "preflight_status": "passed",
        "negative_control_profile_ref": profile_ref,
        "negative_control_profile_digest": profile_ref["profile_digest"],
        "negative_control_profile_status": "available",
        "selector_ref": {
            "selector_kind": "bounded_digest_count_surrogate",
            "selector_digest": "fixture-selector-digest",
        },
        "component_ref": {"component_id": PASSPORT_COMPONENT_ID},
        "source_obligation_ref": {
            "source_obligation_candidate_ids": [PASSPORT_OBLIGATION_ID],
            "lane": "official_current",
        },
        "source_proposition": (
            "The structured proposition states the adult passport book renewal "
            "by mail fee as $130 for the current fee component."
        ),
        "answer_component_claim": {
            "component_id": PASSPORT_COMPONENT_ID,
            "claim": "Adult U.S. passport book renewal by mail fee is $130.",
        },
        "support_relation": support_relation,
        "required_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "observed_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The structured proposition maps to the same component and current "
            "fee claim."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "fixture_review_ref": {
            "fixture_review_id": "fixture-review:dprime-assessment-validation-01",
            "fixture_only": True,
        },
        "fixture_license_ref": {
            "fixture_license_id": "fixture-license:dprime-assessment-validation-01",
            "fixture_only": True,
        },
        "closed_surface_flags": _closed_surface_flags(),
    }
    _apply_relation_shape(payload, support_relation=support_relation)
    _refresh_digest(payload)
    return payload


def _apply_relation_shape(
    payload: dict[str, Any],
    *,
    support_relation: str,
) -> None:
    if support_relation == "abstained":
        payload["producer_abstained"] = True
        payload["observed_qualifiers"] = []
        payload["non_support_reason_when_not_direct"] = "fixture producer abstained"
    elif support_relation == "absent":
        payload["observed_qualifiers"] = []
        payload["non_support_reason_when_not_direct"] = (
            "fixture proposition is absent"
        )
    elif support_relation == "scope_mismatch":
        payload["scope_check"] = {"status": "scope_mismatch"}
        payload["non_support_reason_when_not_direct"] = "fixture scope mismatch"
    elif support_relation == "currentness_mismatch":
        payload["currentness_check"] = {"status": "wrong_effective_date"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fixture currentness mismatch"
    elif support_relation == "contradicts":
        payload["contradiction_check"] = {"status": "contradicts"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fixture contradiction"
    elif support_relation == "missing_qualifier":
        payload["missing_qualifiers"] = ["renewal by mail"]
        payload["non_support_reason_when_not_direct"] = "fixture qualifier missing"
    elif support_relation == "weak_or_overclaim_risk":
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fixture overclaim risk"
    elif support_relation != "directly_supports":
        payload["non_support_reason_when_not_direct"] = "fixture unsupported relation"


def _closed_surface_flags() -> dict[str, bool]:
    return {
        "model_review_licensed": False,
        "assessment_created": False,
        "validated_support_proposal_created": False,
        "run_kernel_support_admission_request_created": False,
        "semantic_observation_created": False,
        "component_coverage_bound": False,
        "citation_eligibility_claimed": False,
        "source_obligation_satisfaction_claimed": False,
        "answer_text_created": False,
        "product_correctness_claimed": False,
    }


def _refresh_digest(payload: dict[str, Any]) -> None:
    safe = copy.deepcopy(payload)
    safe["assessment_digest"] = ""
    payload["assessment_digest"] = assessment_validation.assessment_digest(safe)
