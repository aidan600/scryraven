"""PRODUCT-PATH-REGRESSION: D-prime negative-control profile consumption.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_negative_control_profile
Why ordinary product-path work cannot be done directly: not applicable; the
ordinary status builder consumes the profile, and this test uses fixture-sized
retained artifacts to avoid private local output.
Integration deadline: current phase.
Exit condition: keep while D-prime model review is gated by the deterministic
negative-control profile.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned profile validator, not a standalone script.
Forbidden interpretation: this is not model review, support assessment,
support proposal validation, RunKernel admission, SemanticObservation admission,
ComponentCoverage binding, citation eligibility, answer text, source-obligation
satisfaction, or product correctness.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import core.dprime_negative_control_profile as profile_config
import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import (
    build_live_semantic_coverage_status,
    output_hygiene_passes,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    UNRELATED_SAME_LANE_TEXT,
    _passport_retained_repo,
)


def test_default_profile_contains_all_mandatory_controls() -> None:
    profile = profile_config.build_default_negative_control_profile()
    validation = profile_config.validate_negative_control_profile(profile)
    control_ids = {control.control_id for control in profile.controls}

    assert validation.profile_status == "available"
    assert tuple(profile.required_control_ids) == profile_config.MANDATORY_CONTROL_IDS
    assert control_ids == set(profile_config.MANDATORY_CONTROL_IDS)
    assert len(profile.controls) == 12
    for control in profile.controls:
        assert control.purpose
        assert control.risk_prevented
        assert control.input_shape_or_fixture_kind
        assert control.expected_outcome in profile_config.FAIL_CLOSED_EXPECTED_OUTCOMES
        assert control.status_owner == "deterministic_negative_control_profile_validator"
        assert control.phase_required_before == "DPRIME-MODEL-REVIEW-01"
        assert control.closed_surfaces


def test_profile_ref_and_digest_are_cli_safe() -> None:
    profile = profile_config.build_default_negative_control_profile()
    ref = profile_config.negative_control_profile_ref(profile)
    validation = profile_config.validate_negative_control_profile(profile)
    serialized = json.dumps(
        {"profile_ref": ref, "validation": validation.to_dict()},
        sort_keys=True,
    ).casefold()

    assert ref["profile_id"] == profile.profile_id
    assert ref["profile_digest"] == profile.profile_digest
    assert ref["required_control_count"] == 12
    assert "controls" not in ref
    for forbidden in (
        "bounded_text",
        "passport book renewal fee",
        PASSPORT_TEXT.casefold(),
        "raw provider",
        "raw_page",
        "model_response",
        "prompt",
        "answer prose",
        "citation eligibility claimed: true",
        "source-obligation satisfaction claimed: true",
        "finalanswerpacket",
        "author prose",
        "product correctness claimed: true",
    ):
        assert forbidden.casefold() not in serialized


def test_missing_mandatory_control_blocks_before_model_review() -> None:
    profile = profile_config.build_default_negative_control_profile()
    controls = tuple(
        control
        for control in profile.controls
        if control.control_id != "manual_reviewer_assertion_only_reject"
    )
    incomplete = profile_config.build_negative_control_profile(controls=controls)

    validation = profile_config.validate_negative_control_profile(incomplete)
    status = dprime.build_dprime_status_payload(
        evidence_frame_preflight=_passed_preflight(),
        negative_control_profile=incomplete,
    )

    assert validation.profile_status == "failed"
    assert "missing mandatory controls: manual_reviewer_assertion_only_reject" in (
        validation.blocker_detail or ""
    )
    assert status.decision == dprime.BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED
    assert status.negative_control_profile_status == "failed"
    assert status.model_review_status == "not reached"
    assert "manual_reviewer_assertion_only_reject" in status.blocker_detail


def test_support_like_expected_outcome_blocks_before_model_review() -> None:
    profile = profile_config.build_default_negative_control_profile()
    controls = tuple(
        replace(control, expected_outcome="weak_support")
        if control.control_id == "same_lane_unrelated_official_text_no_support"
        else control
        for control in profile.controls
    )
    weak = profile_config.build_negative_control_profile(controls=controls)

    validation = profile_config.validate_negative_control_profile(weak)
    status = dprime.build_dprime_status_payload(
        evidence_frame_preflight=_passed_preflight(),
        negative_control_profile=weak,
    )

    assert validation.profile_status == "failed"
    assert "non-fail-closed expected_outcome" in (validation.blocker_detail or "")
    assert status.decision == dprime.BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_FAILED
    assert status.negative_control_profile_status == "failed"
    assert status.model_review_status == "not reached"
    assert "weak_support" in status.blocker_detail


def test_missing_profile_blocks_with_precise_missing_blocker() -> None:
    status = dprime.build_dprime_status_payload(
        evidence_frame_preflight=_passed_preflight(),
        negative_control_profile=None,
    )

    assert status.decision == dprime.BLOCKED_DPRIME_NEGATIVE_CONTROL_PROFILE_MISSING
    assert status.negative_control_profile_status == "missing"
    assert status.model_review_status == "not reached"
    assert status.blocker_detail == "D-prime negative-control profile is missing"


def test_product_cli_consumes_profile_then_blocks_at_model_review(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "D-prime preflight status: passed" in result.output
    assert "D-prime negative-control profile status: available" in result.output
    assert "D-prime negative-control profile ref/digest:" in result.output
    assert "D-prime assessment validator status: available" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "D-prime assessment status: not reached" in result.output
    assert "D-prime proposal validation status: not reached" in result.output
    assert "RunKernel support admission status: not reached" in result.output
    assert "SemanticObservation admission status: unavailable" in result.output
    assert "ComponentCoverage status: unavailable" in result.output
    assert (
        "semantic support source: unavailable; D-prime model review not licensed"
        in result.output
    )
    assert (
        f"decision: {dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED}"
        in result.output
    )
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["negative_control_profile_status"] == "available"
    assert dprime_status["negative_control_profile_consumed"] is True
    assert dprime_status["negative_control_profile_ref"]["profile_digest"]
    assert dprime_status["assessment_validator_status"] == "available"


def test_same_lane_unrelated_bounded_text_remains_non_support(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text=UNRELATED_SAME_LANE_TEXT,
    )

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["preflight_status"] == "passed"
    assert dprime_status["negative_control_profile_status"] == "available"
    assert dprime_status["assessment_validator_status"] == "available"
    assert dprime_status["model_review_status"] == "not licensed"
    assert dprime_status["assessment_status"] == "not reached"
    assert dprime_status["proposal_validation_status"] == "not reached"
    assert (
        dprime_status["objects_created"]["run_kernel_support_proposal_admission_request"]
        is False
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert "Analyst support proposal ref/digest: unavailable" in result.output
    assert "SemanticObservation id/ref/digest: unavailable" in result.output
    assert "ComponentCoverage id/ref/digest: unavailable" in result.output
    assert UNRELATED_SAME_LANE_TEXT not in result.output


def test_cli_output_hygiene_excludes_raw_private_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert output_hygiene_passes(result.output)
    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT,
        "raw provider",
        "raw page",
        "provider_payload",
        "model_response",
        "prompt:",
        "answer prose",
        "citation eligibility claimed: true",
        "source-obligation satisfaction claimed: true",
        "FinalAnswerPacket",
        "Author prose",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output


def _passed_preflight() -> dprime.EvidenceFramePreflight:
    return dprime.EvidenceFramePreflight(
        frame_ref={
            "frame_kind": "dprime_evidence_frame_preflight",
            "frame_id": "dprime-evidence-frame-preflight:test",
            "frame_digest": "test-frame-digest",
            "frame_eligibility_only": True,
            "model_browse_allowed": False,
        },
        preflight_status="passed",
    )
