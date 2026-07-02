"""PRODUCT-PATH-REGRESSION: D-prime RunKernel admission request gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_support_proposal_schema
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep while D-prime RunKernel admission requests feed the
post-request decision gate before SemanticObservation materialization is
licensed.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned D-prime schema/model-review modules, not a standalone packet.
Forbidden interpretation: an admission request and post-request decision are
not admitted semantic support, SemanticObservation admission, ComponentCoverage,
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


def test_validated_proposal_reports_request_ready_and_admitted_decision(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == (
        dprime.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
    )
    assert "D-prime assessment status: assessed" in result.output
    assert (
        "D-prime proposal validation status: "
        f"{dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED}"
    ) in result.output
    assert (
        "RunKernel support admission request status: "
        f"{dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY}"
    ) in result.output
    assert (
        "RunKernel admission decision status: "
        f"{dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED}"
    ) in result.output
    assert "RunKernel pre-decision guard status: not made" in result.output
    assert "admitted support: false" in result.output
    assert (
        "SemanticObservation admission status: "
        f"{dprime.DPRIME_SEMANTIC_OBSERVATION_NOT_MATERIALIZED}"
    ) in result.output
    assert "ComponentCoverage status: unavailable" in result.output

    dprime_status = result.payload["dprime_status"]
    request_ref = dprime_status["run_kernel_support_admission_request_ref"]
    decision_ref = dprime_status["run_kernel_admission_decision_ref"]
    proposal_ref = dprime_status["validated_support_proposal_ref"]
    validation_ref = dprime_status["support_proposal_validation_ref"]

    assert dprime_status["validated_support_proposal_available"] is True
    assert dprime_status["proposal_validation_status"] == (
        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["run_kernel_support_admission_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert dprime_status["run_kernel_decision"] == "not made"
    assert dprime_status["run_kernel_admission_decision_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert decision_ref["run_kernel_admission_decision_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert decision_ref["admission_request_ref"] == request_ref
    assert decision_ref["admitted_support"] is False
    assert decision_ref["semantic_observation_created"] is False
    assert decision_ref["component_coverage_created"] is False
    assert dprime_status["admitted_support"] is False
    assert dprime_status["semantic_observation_admission_status"] == (
        dprime.DPRIME_SEMANTIC_OBSERVATION_NOT_MATERIALIZED
    )
    assert dprime_status["component_coverage_status"] == "unavailable"
    assert dprime_status["objects_created"] == {
        "evidence_frame_preflight": True,
        "evidence_relative_support_assessment": True,
        "validated_support_proposal": True,
        "run_kernel_support_proposal_admission_request": True,
        "run_kernel_support_proposal_admission_decision": True,
        "semantic_observation": False,
        "component_coverage": False,
    }
    assert request_ref["request_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert request_ref["support_proposal_ref"] == {
        "proposal_id": proposal_ref["proposal_id"],
        "proposal_digest": proposal_ref["proposal_digest"],
    }
    assert request_ref["validation_result_ref"]["validation_status"] == (
        validation_ref["validation_status"]
    )
    assert request_ref["validation_result_ref"]["validation_result_digest"]
    assert request_ref["request_digest"]
    assert result.payload["semantic_support_source"] == (
        "unavailable; RunKernel admitted decision not materialized into SemanticObservation"
    )


def test_admission_request_ref_carries_safe_lineage_only(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    request_ref = result.payload["dprime_status"][
        "run_kernel_support_admission_request_ref"
    ]
    assert sorted(request_ref) == [
        "record_kind",
        "request_digest",
        "request_status",
        "support_proposal_ref",
        "validation_result_ref",
    ]
    assert sorted(request_ref["support_proposal_ref"]) == [
        "proposal_digest",
        "proposal_id",
    ]
    assert sorted(request_ref["validation_result_ref"]) == [
        "record_kind",
        "support_proposal_validation_passed",
        "validation_result_digest",
        "validation_status",
    ]
    serialized = json.dumps(request_ref, sort_keys=True)
    for forbidden in (
        "raw_prompt",
        "prompt",
        "raw_model_response",
        "model_response",
        "provider_payload",
        "bounded_text",
        PASSPORT_TEXT,
        "raw_page_text",
        "raw_html",
        "headers",
        "cookies",
        "api_key",
        "secret",
        "admitted_support\": true",
        "semantic_observation_created\": true",
        "component_coverage_created\": true",
        "SemanticObservation",
        "ComponentCoverage",
        "FinalAnswerPacket",
        "Author prose",
    ):
        assert forbidden not in serialized


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
        (
            "contradicts",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
        ),
    ],
)
def test_non_validated_assessments_do_not_create_admission_request(
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
    assert dprime_status["validated_support_proposal_available"] is False
    assert dprime_status["run_kernel_support_admission_request_ref"] == {}
    assert dprime_status["run_kernel_decision"] == "not made"
    assert dprime_status["run_kernel_admission_decision_status"] == "not reached"
    assert dprime_status["objects_created"][
        "run_kernel_support_proposal_admission_request"
    ] is False
    assert dprime_status["objects_created"][
        "run_kernel_support_proposal_admission_decision"
    ] is False
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False


def test_architecture_doc_records_request_gate_without_opening_downstream() -> None:
    text = Path("docs/architecture/DPRIME_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )

    assert "RunKernelSupportProposalAdmissionRequest ready" in text
    assert "RunKernelSupportProposalAdmissionDecision admitted" in text
    assert "SemanticObservation not materialized" in text
    for closed_surface in (
        "admitted `SemanticObservation`",
        "`ComponentCoverage` binding",
        "citation/source-obligation satisfaction",
        "`SufficiencyReadiness`",
        "`FinalAnswerPacket`",
        "Author/answer text",
        "product correctness",
    ):
        assert closed_surface in text


def _run_product_status_with_assessment(repo_root: Path, payload: dict[str, Any]) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )
