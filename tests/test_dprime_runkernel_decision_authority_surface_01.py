"""PRODUCT-PATH-REGRESSION: RunKernel-owned D-prime admission decisions.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_runkernel_admission_runtime
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep as the regression guard that a RunKernel-owned D-prime
decision alone does not bypass later product authority surfaces.
Why this is not a shadow product path: it invokes the product status builder and
the RunKernel-owned D-prime decision runtime, not a standalone packet path.
Forbidden interpretation: a RunKernel-owned D-prime admitted decision by itself
is not admitted semantic support, SemanticObservation, ComponentCoverage,
citation eligibility, source-obligation satisfaction, SufficiencyReadiness,
FinalAnswerPacket, Author/answer text, product correctness, or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.dprime_runkernel_admission_runtime as rk_dprime
import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import (
    _assessment_payload,
    _license,
)


def test_runkernel_owned_runtime_consumes_full_request_and_reports_three_decisions() -> None:
    request = dprime.RunKernelSupportProposalAdmissionRequest(
        support_proposal_ref={
            "proposal_id": "dprime-support-proposal:example",
            "proposal_digest": "a" * 64,
        },
        validation_result_ref={
            "record_kind": "SupportProposalValidationResultRef",
            "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            "validation_result_digest": "b" * 64,
            "support_proposal_validation_passed": True,
        },
    )

    for status in rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_STATUSES:
        decision = rk_dprime.build_run_kernel_dprime_admission_decision(
            request,
            decision_status=status,
        )
        payload = decision.to_dict()

        assert payload["owner"] == "RunKernel"
        assert payload["runtime_surface"] == (
            "core.dprime_runkernel_admission_runtime"
        )
        assert payload["decision_status"] == status
        assert payload["run_kernel_decision"] == status
        assert payload["admitted_support"] is False
        assert payload["semantic_observation_created"] is False
        assert payload["component_coverage_created"] is False
        assert payload["citation_eligibility_claimed"] is False
        assert payload["source_obligation_satisfaction_claimed"] is False
        assert payload["sufficiency_readiness_created"] is False
        assert payload["final_answer_packet_created"] is False
        assert payload["author_answer_created"] is False
        assert payload["product_correctness_claimed"] is False


def test_product_status_reports_runkernel_admitted_decision_with_materialization(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == "PASS"
    assert "RunKernel admission decision status: admitted" in result.output
    assert "RunKernel decision: admitted" in result.output
    assert "admitted support: true" in result.output
    assert "SemanticObservation admission status: admitted" in result.output
    assert "ComponentCoverage status: bound" in result.output
    assert "source-obligation authority status: consumed" in result.output
    assert (
        "semantic support source: available from D-prime SemanticObservation and "
        "bound ComponentCoverage; source-obligation and citation-source "
        "handoff authority consumed; single-lane answer path consumed"
    ) in result.output

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["proposal_validation_status"] == (
        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["run_kernel_support_admission_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert dprime_status["run_kernel_admission_decision_status"] == "admitted"
    assert dprime_status["run_kernel_admission_decision_owner"] == "RunKernel"
    assert dprime_status["run_kernel_admission_decision_ref"]["decision_digest"]
    assert dprime_status["admitted_support"] is True
    assert dprime_status["objects_created"]["run_kernel_admission_decision"] is True
    assert dprime_status["objects_created"]["semantic_observation"] is True
    assert dprime_status["objects_created"]["component_coverage"] is True
    assert dprime_status["objects_created"]["sufficiency_readiness"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is True
    assert dprime_status["objects_created"]["author_answer"] is True
    assert dprime_status["objects_created"]["citation_source_display"] is True
    assert dprime_status["semantic_observation_admission_status"] == "materialized"
    assert dprime_status["semantic_observation_ref"]["owner"] == (
        "RunKernel.SemanticObservationAdmission"
    )
    assert result.payload["semantic_observation_admission_ref"]["status"] == "admitted"
    assert result.payload["component_coverage_ref"]["status"] == "bound"
    assert result.payload["source_obligation_authority_ref"]["status"] == "consumed"
    assert (
        result.payload["citation_eligibility_authority_ref"][
            "citation_source_handoff_consumed"
        ]
        is True
    )
    assert result.payload["answerability_correctness"] == "not claimed"


@pytest.mark.parametrize(
    "decision_status",
    [
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED,
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    ],
)
def test_rejected_and_challenged_product_status_do_not_create_support(
    tmp_path: Path,
    decision_status: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(),
        decision_status=decision_status,
    )

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["run_kernel_admission_decision_status"] == decision_status
    assert dprime_status["run_kernel_decision"] == decision_status
    assert dprime_status["admitted_support"] is False
    assert dprime_status["objects_created"]["run_kernel_admission_decision"] is True
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert result.payload["semantic_observation_admission_ref"]["status"] == (
        "unavailable"
    )
    assert result.payload["component_coverage_ref"]["status"] == "unavailable"


@pytest.mark.parametrize(
    "bad_request",
    [
        {"record_kind": "RunKernelSupportProposalAdmissionRequest"},
        {
            "record_kind": "RunKernelSupportProposalAdmissionRequest",
            "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
            "request_digest": "c" * 64,
            "support_proposal_ref": {"proposal_digest": "a" * 64},
            "validation_result_ref": {
                "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": True,
            },
        },
        {
            "record_kind": "RunKernelSupportProposalAdmissionRequest",
            "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
            "request_digest": "c" * 64,
            "support_proposal_ref": {
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
            },
            "validation_result_ref": {
                "validation_status": "failed",
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": False,
            },
        },
        {
            **{
                "record_kind": "RunKernelSupportProposalAdmissionRequest",
                "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
                "request_digest": "c" * 64,
                "support_proposal_ref": {
                    "proposal_id": "dprime-support-proposal:example",
                    "proposal_digest": "a" * 64,
                },
                "validation_result_ref": {
                    "validation_status": (
                        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
                    ),
                    "validation_result_digest": "b" * 64,
                    "support_proposal_validation_passed": True,
                },
            },
            "raw_prompt": "secret prompt",
        },
        {
            "record_kind": "RunKernelSupportProposalAdmissionRequest",
            "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
            "request_digest": "c" * 64,
            "support_proposal_ref": {
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
                "semantic_observation_ref": "precreated",
            },
            "validation_result_ref": {
                "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": True,
            },
        },
        {
            "record_kind": "RunKernelSupportProposalAdmissionRequest",
            "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
            "request_digest": "c" * 64,
            "support_proposal_ref": {
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
            },
            "validation_result_ref": {
                "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": True,
            },
            "admitted_support": True,
        },
    ],
)
def test_runtime_rejects_malformed_or_unsafe_request_material(
    bad_request: Mapping[str, Any],
) -> None:
    with pytest.raises(rk_dprime.DPrimeRunKernelAdmissionRuntimeError):
        rk_dprime.build_run_kernel_dprime_admission_decision(bad_request)


@pytest.mark.parametrize(
    "forbidden",
    [
        "run_kernel_decision",
        "run_kernel_admission_decision_status",
        "run_kernel_admission_decision_ref",
        "admitted",
        "rejected",
        "challenged",
    ],
)
def test_pre_decision_request_material_cannot_smuggle_decision_vocab(
    forbidden: str,
) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.RunKernelSupportProposalAdmissionRequest(
            support_proposal_ref={
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
            },
            validation_result_ref={
                "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": True,
            },
            metadata={forbidden: "smuggled"},
        )


@pytest.mark.parametrize(
    "status",
    [
        "admitted",
        "rejected",
        "challenged",
    ],
)
def test_pre_decision_validation_and_proposal_objects_reject_decision_statuses(
    status: str,
) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.SupportProposalValidationResult(validation_status=status)

    validation = dprime.SupportProposalValidationResult(
        validation_status=dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.ValidatedSupportProposal(
            proposal_ref={
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
            },
            validation_result=validation,
            proposal_status=status,
        )


@pytest.mark.parametrize(
    "support_relation",
    [
        "abstained",
        "absent",
        "contradicts",
        "currentness_mismatch",
        "weak_or_overclaim_risk",
    ],
)
def test_earlier_non_support_or_challenge_gates_do_not_create_decision(
    tmp_path: Path,
    support_relation: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(support_relation),
    )

    dprime_status = result.payload["dprime_status"]
    assert dprime_status.get("run_kernel_admission_decision_status") in (
        None,
        "not reached",
    )
    assert "run_kernel_admission_decision_ref" not in dprime_status
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False


def test_decision_output_hygiene_excludes_raw_private_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized = json.dumps(result.payload, sort_keys=True)

    for forbidden in (
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "bounded_text",
        PASSPORT_TEXT,
        "raw_page_text",
        "secret",
        "citation eligibility claimed: true",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output
    for forbidden in (
        PASSPORT_TEXT,
        "secret prompt",
        "raw page text",
        "provider payload",
        "citation eligibility claimed: true",
        "product correctness claimed: true",
    ):
        assert forbidden not in serialized


def test_decision_surface_lives_outside_dprime_schema_module() -> None:
    assert not hasattr(dprime, "RunKernelDPrimeAdmissionDecision")
    assert not hasattr(dprime, "build_run_kernel_dprime_admission_decision")
    assert hasattr(rk_dprime, "RunKernelDPrimeAdmissionDecision")
    assert "RunKernel-owned" in (rk_dprime.__doc__ or "")


def test_architecture_doc_records_answer_path_after_decision() -> None:
    text = Path("docs/architecture/DPRIME_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )

    assert "RunKernel-owned admission decision made" in text
    assert "SemanticObservation materialized/admitted" in text
    assert "ComponentCoverage bound through existing RunKernel coverage authority" in text
    for consumed_surface in (
        "`SufficiencyReadiness`",
        "hardened final answer packet",
        "Author/answer output",
        "citation/source display",
    ):
        assert consumed_surface in text
    assert "product correctness remains unclaimed" in text


def _run_product_status_with_assessment(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    decision_status: str = rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
        dprime_run_kernel_admission_decision_status=decision_status,
    )
