"""PRODUCT-PATH-REGRESSION: D-prime SemanticObservation materialization.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_semantic_observation_materialization_runtime
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep as the regression guard for RunKernel-owned D-prime
decision -> SemanticObservation materialization -> ComponentCoverage not bound.
Why this is not a shadow product path: it invokes the product status builder and
the RunKernel/SemanticObservation-owned materialization runtime, not a detached
packet path.
Forbidden interpretation: SemanticObservation materialization is not
ComponentCoverage binding, citation eligibility, source-obligation satisfaction,
SufficiencyReadiness, FinalAnswerPacket, Author/answer text, product
correctness, or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.dprime_runkernel_admission_runtime as rk_dprime
import core.dprime_semantic_observation_materialization_runtime as dprime_semantic
import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from proplex.live_source_evidence_admission_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import (
    _assessment_payload,
    _license,
)


def test_product_status_materializes_semantic_observation_and_stops_before_coverage(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == (
        dprime_semantic.BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED
    )
    assert "RunKernel admission decision status: admitted" in result.output
    assert "SemanticObservation admission status: admitted" in result.output
    assert "ComponentCoverage status: not licensed" in result.output
    assert "answerability/correctness: not claimed" in result.output

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["assessment_status"] == "assessed"
    assert dprime_status["proposal_validation_status"] == (
        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["validated_support_proposal_available"] is True
    assert dprime_status["run_kernel_support_admission_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert dprime_status["run_kernel_admission_decision_status"] == "admitted"
    assert dprime_status["semantic_observation_admission_status"] == "materialized"
    assert dprime_status["semantic_observation_ref"]["observation_digest"]
    assert dprime_status["objects_created"] == {
        "evidence_frame_preflight": True,
        "evidence_relative_support_assessment": True,
        "validated_support_proposal": True,
        "run_kernel_support_proposal_admission_request": True,
        "run_kernel_admission_decision": True,
        "semantic_observation": True,
        "component_coverage": False,
    }
    semantic = result.payload["semantic_observation_admission_ref"]
    coverage = result.payload["component_coverage_ref"]
    assert semantic["status"] == "admitted"
    assert semantic["observation_digest"]
    assert coverage["status"] == "not licensed"
    assert coverage["coverage_ref"] == "unavailable"
    assert result.payload["semantic_support_source"] == (
        "available from D-prime SemanticObservation; ComponentCoverage not licensed"
    )
    assert result.payload["next_blocked_surface"] == "D-prime ComponentCoverage binding"


@pytest.mark.parametrize(
    "decision_status",
    [
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED,
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    ],
)
def test_rejected_or_challenged_decisions_do_not_materialize_observation(
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
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert result.payload["semantic_observation_admission_ref"]["status"] == (
        "unavailable"
    )
    assert result.payload["component_coverage_ref"]["status"] == "unavailable"


def test_request_ready_without_admitted_decision_cannot_materialize_directly(
    tmp_path: Path,
) -> None:
    context = _direct_materialization_context(tmp_path)

    with pytest.raises(
        dprime_semantic.DPrimeSemanticObservationMaterializationError,
        match="admitted RunKernel decision",
    ):
        dprime_semantic.materialize_dprime_semantic_observation_from_admitted_decision(
            **{
                **context,
                "decision": rk_dprime.build_run_kernel_dprime_admission_decision(
                    context["decision"].request_ref,
                    decision_status=(
                        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED
                    ),
                ),
            }
        )


def test_insufficient_safe_assessment_lineage_blocks_without_invention(
    tmp_path: Path,
) -> None:
    context = _direct_materialization_context(tmp_path)

    with pytest.raises(
        dprime_semantic.DPrimeSemanticObservationMaterializationError,
    ) as exc_info:
        dprime_semantic.materialize_dprime_semantic_observation_from_admitted_decision(
            **{**context, "assessment_material_ref": {}}
        )

    assert exc_info.value.blocker == (
        dprime_semantic.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_MATERIALIZATION_INPUT_INSUFFICIENT
    )


def test_direct_materialization_object_is_safe_and_has_no_coverage_refs(
    tmp_path: Path,
) -> None:
    result = dprime_semantic.materialize_dprime_semantic_observation_from_admitted_decision(
        **_direct_materialization_context(tmp_path)
    )

    observation = result.semantic_observation.to_dict()
    content_ref = result.sanitized_content_reference.to_dict()
    projection = dict(result.admission_projection)
    assert observation["support_status"] == "supports"
    assert observation["coverage_decision"] is False
    assert observation["component_satisfied"] is False
    assert observation["final_answer_authority"] is False
    assert content_ref["sanitized"] is True
    assert content_ref["bounded"] is True
    assert content_ref["raw_content_retained"] is False
    assert projection["coverage_created"] is False
    assert projection["component_satisfied"] is False
    assert projection["sufficiency_decided"] is False
    assert projection["final_answer_packet_created"] is False
    assert projection["author_input_created"] is False
    assert projection["live_validation_not_run"] is True
    serialized_ref = json.dumps(result.semantic_status_ref(), sort_keys=True)
    assert "component_coverage" not in serialized_ref


def test_materialization_output_hygiene_excludes_raw_private_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized = json.dumps(result.payload, sort_keys=True)

    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT,
        "secret prompt",
        "raw page text",
        "provider payload",
        "citation eligibility claimed: true",
        "source-obligation satisfaction claimed: true",
        "FinalAnswerPacket",
        "Author prose",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output
        assert forbidden not in serialized


def test_dprime_schema_objects_still_cannot_smuggle_materialization() -> None:
    with pytest.raises(dprime.DPrimeSupportProposalSchemaError):
        dprime.RunKernelSupportProposalAdmissionRequest(
            support_proposal_ref={
                "proposal_id": "dprime-support-proposal:example",
                "proposal_digest": "a" * 64,
                "semantic_observation_ref": "precreated",
            },
            validation_result_ref={
                "validation_status": dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
                "validation_result_digest": "b" * 64,
                "support_proposal_validation_passed": True,
            },
        )

    assert not hasattr(dprime, "materialize_dprime_semantic_observation")
    assert hasattr(
        dprime_semantic,
        "materialize_dprime_semantic_observation_from_admitted_decision",
    )


def test_architecture_doc_records_new_stop_and_closed_downstream_surfaces() -> None:
    text = Path("docs/architecture/DPRIME_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )

    assert "SemanticObservation materialized" in text
    assert "ComponentCoverage not bound" in text
    assert "BLOCKED_DPRIME_COMPONENT_COVERAGE_NOT_LICENSED" in text
    for closed_surface in (
        "`ComponentCoverage` binding",
        "citation/source-obligation satisfaction",
        "`SufficiencyReadiness`",
        "`FinalAnswerPacket`",
        "Author/answer text",
        "product correctness",
    ):
        assert closed_surface in text


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


def _direct_materialization_context(tmp_path: Path) -> dict[str, Any]:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    dprime_status = result.payload["dprime_status"]
    fetch_packet = json.loads(
        (
            repo_root
            / FETCH_READ_ARTIFACT_DIR
            / FETCH_READ_CONTENT_PACKET_NAME
        ).read_text(encoding="utf-8")
    )
    decision = rk_dprime.build_run_kernel_dprime_admission_decision(
        dprime_status["run_kernel_support_admission_request_ref"],
        decision_status=rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    )
    return {
        "decision": decision,
        "assessment_material_ref": dprime_status["assessment_material_ref"],
        "validated_support_proposal_ref": dprime_status[
            "validated_support_proposal_ref"
        ],
        "fetch_read_content_packet": fetch_packet,
        "source_evidence_admission_ref": result.payload["source_evidence_admission_ref"],
        "component_ref": result.payload["component_ref"],
        "source_obligation_ref": result.payload["source_obligation_ref"],
    }
