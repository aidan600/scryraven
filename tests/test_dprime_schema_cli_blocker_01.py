"""PRODUCT-PATH-REGRESSION: D-prime schema/status CLI blocker.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_support_proposal_schema
Why ordinary product-path work cannot be done directly: not applicable; the CLI
status builder is the ordinary dry-run product path and this test uses retained
fixture-sized artifacts to avoid private local output.
Integration deadline: current phase.
Exit condition: keep while the D-prime schema/status blocker is product-consumed.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned D-prime schema module, not a standalone script.
Forbidden interpretation: this is not EvidenceFramePreflight implementation,
model review, support assessment creation, support proposal validation from
source content, RunKernel admission, SemanticObservation admission,
ComponentCoverage binding, citation eligibility, answer text, or product
correctness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import (
    build_live_semantic_coverage_status,
    output_hygiene_passes,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    _passport_retained_repo,
)


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "support_relation",
        "SemanticObservation",
        "ComponentCoverage",
        "answer",
    ],
)
def test_evidence_frame_preflight_forbids_support_and_downstream_fields(
    forbidden_field: str,
) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.EvidenceFramePreflight(
            frame_ref={forbidden_field: "forbidden authority upgrade"}
        )


def test_assessment_and_validated_proposal_are_not_admitted_support() -> None:
    assessment = dprime.EvidenceRelativeSupportAssessment(
        assessment_ref={"assessment_id": "assessment:example"}
    )
    validation = dprime.SupportProposalValidationResult(
        validation_status=dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    proposal = dprime.ValidatedSupportProposal(
        proposal_ref={"proposal_id": "proposal:example"},
        validation_result=validation,
    )

    assert assessment.is_admitted_support is False
    assert assessment.to_dict()["support_assessment_only"] is True
    assert proposal.is_admitted_support is False
    assert proposal.to_dict()["admitted_support"] is False
    assert validation.run_kernel_decision == "not made"
    assert proposal.to_dict()["run_kernel_admission_status"] == "not made"


@pytest.mark.parametrize(
    "validation_status",
    [
        "admit",
        "reject",
        "challenge",
        dprime.DPRIME_SUPPORT_PROPOSAL_REJECTED,
        dprime.DPRIME_SUPPORT_PROPOSAL_CHALLENGED,
        dprime.DPRIME_SEMANTIC_OBSERVATION_ADMITTED,
        dprime.DPRIME_COMPONENT_COVERAGE_BOUND,
    ],
)
def test_validation_result_cannot_represent_run_kernel_decisions(
    validation_status: str,
) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.SupportProposalValidationResult(validation_status=validation_status)


def test_validator_vocabulary_keeps_challenge_recommendation_separate() -> None:
    result = dprime.SupportProposalValidationResult(
        validation_status=dprime.DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED,
        challenge_recommended=True,
        warnings=("validator recommends RunKernel challenge consideration",),
    )

    assert (
        dprime.BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED
        in dprime.SUPPORT_PROPOSAL_VALIDATOR_STATUSES
    )
    assert (
        dprime.DPRIME_SUPPORT_PROPOSAL_CHALLENGE_RECOMMENDED
        in dprime.SUPPORT_PROPOSAL_VALIDATOR_STATUSES
    )
    assert (
        dprime.BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING
        in dprime.SUPPORT_PROPOSAL_VALIDATOR_STATUSES
    )
    assert dprime.DPRIME_SUPPORT_PROPOSAL_REJECTED in dprime.LATER_PHASE_STATUSES
    assert dprime.DPRIME_SUPPORT_PROPOSAL_CHALLENGED in dprime.LATER_PHASE_STATUSES
    assert (
        dprime.DPRIME_SEMANTIC_OBSERVATION_ADMITTED in dprime.LATER_PHASE_STATUSES
    )
    assert dprime.DPRIME_COMPONENT_COVERAGE_BOUND in dprime.LATER_PHASE_STATUSES
    assert dprime.DPRIME_SUPPORT_PROPOSAL_REJECTED not in (
        dprime.SUPPORT_PROPOSAL_VALIDATOR_STATUSES
    )
    assert result.to_dict()["validator_challenge_recommendation_only"] is True
    assert result.to_dict()["run_kernel_decision"] == "not made"


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "semantic_observation",
        "component_coverage",
        "semantic_observation_ref",
        "component_coverage_ref",
    ],
)
def test_run_kernel_admission_request_cannot_contain_precreated_outputs(
    forbidden_field: str,
) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.RunKernelSupportProposalAdmissionRequest(
            support_proposal_ref={forbidden_field: "already-created"},
            validation_result_ref={"validation_status": "passed"},
        )


def test_negative_control_profile_cannot_claim_product_or_model_success() -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.NegativeControlProfile(
            profile_id="negative-control:product",
            product_correctness_claimed=True,
        )
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.NegativeControlProfile(
            profile_id="negative-control:model",
            metadata={"model_success": True},
        )


def test_schema_status_payload_without_preflight_reports_missing() -> None:
    payload = dprime.build_dprime_status_payload().to_dict()

    assert payload["preflight_status"] == "missing"
    assert payload["negative_control_profile_status"] == "not reached"
    assert payload["decision"] == dprime.BLOCKED_DPRIME_PREFLIGHT_MISSING
    assert payload["objects_created"]["evidence_frame_preflight"] is False
    assert (
        payload["semantic_support_source"]
        == "unavailable; D-prime preflight missing"
    )


def test_cli_status_reports_dprime_preflight_passed_model_review_blocker(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert result.return_code == 2
    assert "D-prime schema status: available" in result.output
    assert "D-prime preflight status: passed" in result.output
    assert "D-prime negative-control profile status: available" in result.output
    assert "D-prime negative-control profile ref/digest:" in result.output
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
    assert (
        result.payload["dprime_status"]["negative_control_profile_status"]
        == "available"
    )
    assert result.payload["dprime_status"]["negative_control_profile_ref"][
        "profile_digest"
    ]
    assert result.payload["dprime_status"]["objects_created"] == {
        "evidence_frame_preflight": True,
        "evidence_relative_support_assessment": False,
        "validated_support_proposal": False,
        "run_kernel_support_proposal_admission_request": False,
        "semantic_observation": False,
        "component_coverage": False,
    }


def test_cli_status_output_hygiene_excludes_private_or_closed_material(
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
