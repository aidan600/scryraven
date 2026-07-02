"""PRODUCT-PATH-REGRESSION: D-prime RunKernel admission decision gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_support_proposal_schema
Why ordinary product-path work cannot be done directly: the product status path
is exercised in adjacent tests with retained fixture-sized artifacts and an
injected fake model-review callable because live/model/provider/search/fetch/
read/retrieval calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep while D-prime RunKernel admission decisions are reported
before SemanticObservation materialization is licensed.
Why this is not a shadow product path: the helper is consumed by the product
D-prime model-review/status path and does not create alternate downstream
support objects.
Forbidden interpretation: a post-request RunKernel decision is not admitted
semantic support, SemanticObservation admission, ComponentCoverage, citation
eligibility, source-obligation satisfaction, SufficiencyReadiness,
FinalAnswerPacket, Author/answer text, product correctness, or a live call.
"""

from __future__ import annotations

import pytest

import core.dprime_support_proposal_schema as dprime


def test_admitted_decision_preserves_closed_downstream_surfaces() -> None:
    decision = dprime.build_run_kernel_support_proposal_admission_decision(
        _request_ref()
    )

    payload = decision.to_dict()

    assert payload["run_kernel_admission_decision_status"] == "admitted"
    assert payload["admitted_support"] is False
    assert payload["semantic_observation_created"] is False
    assert payload["component_coverage_created"] is False
    assert payload["semantic_observation_admission_status"] == (
        dprime.DPRIME_SEMANTIC_OBSERVATION_NOT_MATERIALIZED
    )
    assert payload["component_coverage_status"] == dprime.DPRIME_STATUS_UNAVAILABLE
    assert payload["admission_request_ref"] == _request_ref()
    assert payload["decision_digest"]


@pytest.mark.parametrize("decision_status", ["rejected", "challenged"])
def test_reject_and_challenge_decisions_do_not_create_support(
    decision_status: str,
) -> None:
    decision = dprime.build_run_kernel_support_proposal_admission_decision(
        _request_ref(),
        decision_status=decision_status,
        decision_reason=f"deterministic fixture {decision_status} request",
    )

    payload = decision.to_dict()

    assert payload["run_kernel_admission_decision_status"] == decision_status
    assert payload["admitted_support"] is False
    assert payload["semantic_observation_created"] is False
    assert payload["component_coverage_created"] is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda ref: ref["support_proposal_ref"].pop("proposal_id"),
        lambda ref: ref["support_proposal_ref"].pop("proposal_digest"),
        lambda ref: ref["validation_result_ref"].pop("validation_result_digest"),
        lambda ref: ref["validation_result_ref"].update(
            {"validation_status": dprime.BLOCKED_DPRIME_SUPPORT_PROPOSAL_VALIDATION_FAILED}
        ),
        lambda ref: ref.update({"run_kernel_decision": "admitted"}),
        lambda ref: ref.update({"raw_prompt": "private"}),
        lambda ref: ref.update({"semantic_observation_ref": "obs:forbidden"}),
        lambda ref: ref.update({"component_coverage_ref": "coverage:forbidden"}),
        lambda ref: ref.update({"admitted_support": True}),
    ],
)
def test_decision_helper_rejects_unsafe_request_material(mutator: object) -> None:
    request_ref = _request_ref()
    mutator(request_ref)

    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.build_run_kernel_support_proposal_admission_decision(request_ref)


@pytest.mark.parametrize("status", ["admitted", "rejected", "challenged"])
def test_validation_result_still_rejects_decision_language(status: str) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.SupportProposalValidationResult(validation_status=status)


@pytest.mark.parametrize("status", ["admitted", "rejected", "challenged"])
def test_validated_support_proposal_still_rejects_decision_language(
    status: str,
) -> None:
    validation = dprime.SupportProposalValidationResult(
        validation_status=dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )

    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.ValidatedSupportProposal(
            proposal_ref={"proposal_id": "proposal:ok"},
            validation_result=validation,
            proposal_status=status,
        )


@pytest.mark.parametrize("status", ["admitted", "rejected", "challenged"])
def test_admission_request_still_rejects_decision_language(status: str) -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.RunKernelSupportProposalAdmissionRequest(
            support_proposal_ref={
                "proposal_id": "proposal:ok",
                "proposal_digest": "proposal-digest",
            },
            validation_result_ref={
                "validation_status": (
                    dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
                ),
                "validation_result_digest": "validation-digest",
                "support_proposal_validation_passed": True,
            },
            request_status=status,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"support_proposal_ref": {"run_kernel_decision": "admitted"}},
        {"validation_result_ref": {"run_kernel_decision": "rejected"}},
        {"metadata": {"run_kernel_decision": "challenged"}},
    ],
)
def test_admission_request_refs_and_metadata_cannot_smuggle_decision(
    payload: dict[str, object],
) -> None:
    base = {
        "support_proposal_ref": {
            "proposal_id": "proposal:ok",
            "proposal_digest": "proposal-digest",
        },
        "validation_result_ref": {
            "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            "validation_result_digest": "validation-digest",
            "support_proposal_validation_passed": True,
        },
    }
    base.update(payload)

    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.RunKernelSupportProposalAdmissionRequest(**base)


def _request_ref() -> dict[str, object]:
    return {
        "record_kind": "RunKernelSupportProposalAdmissionRequest",
        "request_status": dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY,
        "request_digest": "request-digest",
        "support_proposal_ref": {
            "proposal_id": "dprime-support-proposal:ok",
            "proposal_digest": "proposal-digest",
        },
        "validation_result_ref": {
            "record_kind": "SupportProposalValidationResultRef",
            "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
            "validation_result_digest": "validation-digest",
            "support_proposal_validation_passed": True,
        },
    }
