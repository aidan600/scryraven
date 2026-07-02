"""PRODUCT-PATH-REGRESSION: D-prime assessment-to-proposal gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_support_proposal_schema
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep while D-prime proposal candidates are pre-admission status
objects before RunKernel support admission is licensed.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned D-prime schema/model-review modules, not a standalone packet.
Forbidden interpretation: proposal validation is not RunKernel admission,
admitted semantic support, SemanticObservation admission, ComponentCoverage,
citation eligibility, source-obligation satisfaction, SufficiencyReadiness,
FinalAnswerPacket, Author/answer text, product correctness, or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

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


def test_validator_valid_assessment_reaches_proposal_candidate_status(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == dprime.BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING
    assert (
        "D-prime assessment status: assessed" in result.output
    )
    assert (
        "D-prime proposal validation status: "
        f"{dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED}"
    ) in result.output
    assert (
        "RunKernel support admission status: "
        f"{dprime.BLOCKED_DPRIME_RUN_KERNEL_ADMISSION_MISSING}"
    ) in result.output
    assert "semantic support source: unavailable; RunKernel admission not licensed" in (
        result.output
    )

    dprime_status = result.payload["dprime_status"]
    proposal_ref = dprime_status["validated_support_proposal_ref"]
    validation_ref = dprime_status["support_proposal_validation_ref"]
    assert dprime_status["validated_support_proposal_available"] is True
    assert proposal_ref["proposal_id"].startswith("dprime-support-proposal:")
    assert proposal_ref["assessment_ref"] == dprime_status["assessment_ref"]
    assert proposal_ref["input_packet_ref"]["input_packet_digest"] == (
        dprime_status["input_packet_ref"]["input_packet_digest"]
    )
    assert proposal_ref["model_review_ref"]["model_review_digest"] == (
        dprime_status["model_review_ref"]["model_review_digest"]
    )
    assert proposal_ref["prompt_license_ref"]["license_id"] == (
        dprime_status["prompt_license_ref"]["license_id"]
    )
    assert validation_ref["validation_status"] == (
        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert validation_ref["run_kernel_decision"] == "not made"
    assert dprime_status["admitted_support"] is False
    assert dprime_status["run_kernel_decision"] == "not made"
    assert dprime_status["objects_created"] == {
        "evidence_frame_preflight": True,
        "evidence_relative_support_assessment": True,
        "validated_support_proposal": True,
        "run_kernel_support_proposal_admission_request": False,
        "semantic_observation": False,
        "component_coverage": False,
    }
    assert result.payload["semantic_observation_admission_ref"] == {
        "status": "unavailable",
        "observation_ref": "unavailable",
        "reasons": [
            "D-prime proposal candidate is not admitted support",
            "RunKernel support admission is not licensed or made",
        ],
    }
    assert result.payload["component_coverage_ref"]["status"] == "unavailable"
    assert result.payload["answerability_correctness"] == "not claimed"


@pytest.mark.parametrize(
    ("support_relation", "expected_decision"),
    [
        (
            "abstained",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED,
        ),
        ("absent", dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT),
        (
            "currentness_mismatch",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
        ),
    ],
)
def test_non_support_assessments_do_not_create_proposal_or_support(
    tmp_path: Path,
    support_relation: str,
    expected_decision: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(support_relation),
    )

    dprime_status = result.payload["dprime_status"]
    assert result.decision == expected_decision
    assert dprime_status["proposal_validation_status"] == "not reached"
    assert dprime_status["validated_support_proposal_available"] is False
    assert dprime_status["admitted_support"] is False
    assert dprime_status["run_kernel_decision"] == "not made"
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False


def test_proposal_gate_output_hygiene_excludes_raw_private_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized_status = json.dumps(
        result.payload["dprime_status"],
        sort_keys=True,
    )
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["raw_prompt_retained"] is False
    assert dprime_status["raw_model_response_retained"] is False
    assert dprime_status["provider_payload_retained"] is False

    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT,
        "raw_page_text",
        "raw_html",
        "headers",
        "cookies",
        "api_key",
        "secret",
        "SemanticObservation id/ref/digest: admitted",
        "ComponentCoverage status: bound",
        "citation eligibility claimed: true",
        "source-obligation satisfaction claimed: true",
        "FinalAnswerPacket",
        "Author prose",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output
        assert forbidden not in serialized_status


def _run_product_status_with_assessment(repo_root: Path, payload: dict[str, Any]) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )
