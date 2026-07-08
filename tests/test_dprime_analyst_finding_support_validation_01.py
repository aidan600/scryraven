"""PRODUCT-PATH-REGRESSION: D-prime validates AnalystFindingProposal support.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: Workbench AnalystFindingProposal consumed
by proplex.live_semantic_coverage_status before RunKernel D-prime admission.
Runtime consumer: core.dprime_analyst_finding_support_validation ->
proplex.live_semantic_coverage_status -> D-prime answer path.
Why ordinary product-path work cannot be done directly: offline tests must not
run live provider, search, fetch/read, retrieval, or model calls; these tests
reuse the Workbench builder, sanitized fetch/read packet, and existing fake
D-prime model-review product-status seam.
Integration deadline: current phase.
Exit condition: keep while AnalystFindingProposal is the Workbench-to-D-prime
analysis custody contract, or replace with broader product-path regression.
Why this is not a shadow product path: tests call the product validation and
semantic-status builders; they do not create an alternate answer formatter.
Forbidden interpretation: AnalystFinding support validation is not evidence
admission, source-obligation satisfaction, citation eligibility,
ComponentCoverage, SufficiencyReadiness, FAP/Author, source display, live
validation correctness, or product correctness.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from core.current_source_analyst_finding_proposal import (
    build_model_assisted_analyst_finding_proposal,
    build_model_assisted_analyst_license,
)
from core.dprime_analyst_finding_support_validation import (
    DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE,
    DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM,
    DPRIME_SUPPORT_VALIDATION_INSUFFICIENT,
    DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
    DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_MODEL_ASSISTED_ANALYST,
    DPRIME_SUPPORT_VALIDATION_SUPPORTED,
    DPRIME_SUPPORT_VALIDATION_UNSUPPORTED,
    analyst_finding_support_validation_required,
    build_dprime_analyst_finding_support_validation,
    dprime_analyst_finding_support_validation_ref,
    support_validation_allows_runkernel_admission,
)
from proplex.live_semantic_coverage_status import (
    BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    _passport_retained_repo,
)
from tests.test_current_source_analyst_finding_proposal_01 import (
    _answer_bearing_bundle,
    _finding,
    _refs_only_fetch_read_packet_for_direct_candidate,
    _safe_fetch_read_packet_for_direct_candidate,
)
from tests.test_dprime_evidence_support_bundle_01 import (
    _run_product_status_with_assessment,
    _workbench_dossier,
)
from tests.test_dprime_model_review_assessment_slice_01 import _assessment_payload


def test_deterministic_analyst_finding_cannot_recommend_runkernel_admission() -> None:
    bundle = _answer_bearing_bundle()
    finding = _finding(bundle)

    validation = _validate_finding(finding, bundle)

    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_MODEL_ASSISTED_ANALYST
    )
    assert validation["structural_dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    )
    assert validation["structural_validation_supported_by_bounded_evidence"] is True
    assert support_validation_allows_runkernel_admission(validation) is False
    assert validation["dprime_model_role"] == (
        DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION_MODEL_ROLE
    )
    assert validation["proposed_answer_claim_validation"][
        "dprime_support_validation_status"
    ] == DPRIME_SUPPORT_VALIDATION_SUPPORTED
    assert validation["source_support_map_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    )
    assert validation["bounded_evidence_excerpt_available"] is True
    assert validation["analyst_finding_product_grade_ref"][
        "blocked_non_product_grade_analyst_finding"
    ] is True
    assert validation["model_assisted_analysis_run"] is False
    assert validation["model_assisted_analyst_requirement_satisfied"] is False
    assert validation["model_assisted_analyst_product_grade_analysis"] is False
    assert validation["analyst_finding_proposal_ref"][
        "requires_runkernel_admission"
    ] is False
    assert validation["proposed_answer_claim_ref"][
        "requires_runkernel_admission"
    ] is False
    assert validation["runkernel_support_admission_recommended"] is False
    assert validation["requires_runkernel_admission"] is False
    assert validation["runkernel_admission_created"] is False
    assert validation["evidence_admitted"] is False
    assert validation["source_obligation_satisfied"] is False
    assert validation["citation_eligibility_created"] is False
    assert validation["product_correctness_claimed"] is False
    serialized = json.dumps(validation, sort_keys=True).casefold()
    assert '"requires_runkernel_admission": true' not in serialized
    assert "bounded excerpt text" not in serialized
    assert '"dprime_model_role": "fast"' not in serialized
    assert "embed" not in serialized


def test_product_grade_model_assisted_analyst_finding_may_recommend_future_admission() -> None:
    bundle = _answer_bearing_bundle()
    finding = _product_grade_model_assisted_finding(bundle)

    validation = _validate_finding(finding, bundle)

    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    )
    assert validation["structural_dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    )
    assert validation["model_assisted_analysis_run"] is True
    assert validation["model_assisted_analyst_requirement_satisfied"] is True
    assert validation["model_assisted_analyst_product_grade_analysis"] is True
    assert validation["analyst_finding_product_grade_ref"][
        "product_grade_analyst_finding"
    ] is True
    assert validation["runkernel_support_admission_recommended"] is True
    assert validation["requires_runkernel_admission"] is True
    assert validation["analyst_finding_proposal_ref"][
        "requires_runkernel_admission"
    ] is False
    assert validation["proposed_answer_claim_ref"][
        "requires_runkernel_admission"
    ] is False
    assert support_validation_allows_runkernel_admission(validation) is True
    assert validation["runkernel_admission_created"] is False
    assert validation["product_correctness_claimed"] is False


def test_adjacent_source_support_map_edge_rejected_as_answer_support() -> None:
    bundle = _answer_bearing_bundle()
    finding = copy.deepcopy(_finding(bundle))
    adjacent_ref = finding["adjacent_context_candidate_refs"][0]

    for edge in finding["source_support_map"]["analysis_claim_support_edges"]:
        if edge.get("edge_kind") == "candidate_supports_analysis_claim":
            edge["candidate_ref"] = adjacent_ref
            break

    validation = _validate_finding(finding, bundle)

    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM
    )
    assert validation["adjacent_as_answer_edge_refs"]
    assert support_validation_allows_runkernel_admission(validation) is False


def test_refs_only_fetch_read_packet_blocks_support_validation() -> None:
    bundle = _answer_bearing_bundle()
    finding = _finding(bundle)

    validation = build_dprime_analyst_finding_support_validation(
        workbench_dprime_dossier=_dossier_with_finding(bundle, finding),
        fetch_read_content_packet=_refs_only_fetch_read_packet_for_direct_candidate(
            candidate_id="direct-candidate-2",
            candidate_digest="direct-digest-2",
        ),
    )

    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_INSUFFICIENT
    )
    assert validation["bounded_evidence_excerpt_available"] is False
    assert support_validation_allows_runkernel_admission(validation) is False


def test_model_output_validating_invented_claim_fails_closed() -> None:
    bundle = _answer_bearing_bundle()
    finding = _finding(bundle)

    validation = build_dprime_analyst_finding_support_validation(
        workbench_dprime_dossier=_dossier_with_finding(bundle, finding),
        fetch_read_content_packet=_bounded_fetch_packet(),
        model_output={
            "dprime_validation_status": DPRIME_SUPPORT_VALIDATION_SUPPORTED,
            "analysis_claim_validations": [
                {
                    "analysis_claim_id": "invented-analysis-claim",
                    "analysis_claim_kind": "proposed_answer",
                    "dprime_support_validation_status": (
                        DPRIME_SUPPORT_VALIDATION_SUPPORTED
                    ),
                    "supporting_bounded_evidence_excerpt_refs": [
                        {"candidate_id": "direct-candidate-2"}
                    ],
                }
            ],
        },
        model_calls_attempted=1,
        model_calls_completed=1,
    )

    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL
    )
    assert "dprime_model_output_invalid" in validation[
        "dprime_support_validation_reason_codes"
    ]
    assert validation["model_calls_attempted"] == 1
    assert validation["model_calls_completed"] == 1
    assert validation["live_model_call_run"] is False
    assert support_validation_allows_runkernel_admission(validation) is False


def test_requested_answer_type_shape_change_blocks_validation() -> None:
    bundle = _answer_bearing_bundle()
    finding = copy.deepcopy(_finding(bundle))
    finding["proposed_answer_claim"]["requested_answer_type"] = "adjacent_note"
    finding["proposed_answer_claim"]["expected_value_shape"] = "free_text"

    validation = _validate_finding(finding, bundle)
    answer_validation = validation["proposed_answer_claim_validation"]

    assert validation["dprime_validation_status"] in {
        DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
        DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM,
        DPRIME_SUPPORT_VALIDATION_UNSUPPORTED,
    }
    assert support_validation_allows_runkernel_admission(validation) is False
    if answer_validation:
        assert answer_validation["claim_within_requested_answer_type"] is False


def test_validation_ref_is_required_when_dossier_carries_finding_ref() -> None:
    dossier = {
        "analyst_finding_proposal_ref": {
            "finding_id": "analyst-finding-proposal:missing-full-proposal"
        }
    }

    assert analyst_finding_support_validation_required(dossier) is True
    validation = build_dprime_analyst_finding_support_validation(
        workbench_dprime_dossier=dossier,
        fetch_read_content_packet=_bounded_fetch_packet(),
    )
    ref = dprime_analyst_finding_support_validation_ref(validation)

    assert ref["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL
    )
    assert ref["runkernel_support_admission_recommended"] is False


def test_legacy_candidate_dprime_pass_cannot_open_answer_path_without_validation(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _passport_retained_repo(tmp_path)
    dossier = _workbench_dossier(candidate)
    dossier["analyst_finding_proposal_ref"] = {
        "finding_id": "analyst-finding-proposal:missing-full-proposal"
    }

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(),
        workbench_dprime_dossier=dossier,
    )

    assert result.decision == BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION
    dprime = result.payload["dprime_status"]
    assert dprime["proposal_validation_status"] == (
        "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
    )
    assert dprime["dprime_analyst_finding_validation_required_for_product_path"] is True
    assert dprime["dprime_analyst_finding_validation_satisfied"] is False
    assert dprime["objects_created"]["semantic_observation"] is False
    assert dprime["objects_created"]["component_coverage"] is False
    assert dprime["objects_created"]["final_answer_packet"] is False
    assert dprime["objects_created"]["author_answer"] is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"


def test_legacy_candidate_dprime_pass_cannot_bypass_deterministic_analyst_finding(
    tmp_path: Path,
) -> None:
    bundle = _answer_bearing_bundle()
    finding = _finding(bundle)
    repo_root, candidate = _passport_retained_repo(
        tmp_path,
        bounded_text="The current standard paper small claims filing fee is 54 dollars.",
        title="Official Current Standard Filing Fee",
        url="https://example-county.gov/courts/current-filing-fee",
        domain="example-county.gov",
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        snippet="Official current standard small claims filing fee.",
    )
    dossier = _workbench_dossier(candidate)
    dossier["analyst_finding_proposal"] = finding

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(),
        workbench_dprime_dossier=dossier,
    )

    assert result.decision == BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION
    dprime = result.payload["dprime_status"]
    validation = dprime["dprime_analyst_finding_support_validation"]
    assert dprime["proposal_validation_status"] == (
        "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
    )
    assert validation["dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_NOT_RUN_MISSING_MODEL_ASSISTED_ANALYST
    )
    assert validation["structural_dprime_validation_status"] == (
        DPRIME_SUPPORT_VALIDATION_SUPPORTED
    )
    assert validation["structural_validation_supported_by_bounded_evidence"] is True
    assert validation["runkernel_support_admission_recommended"] is False
    assert validation["requires_runkernel_admission"] is False
    assert support_validation_allows_runkernel_admission(validation) is False
    assert dprime["dprime_analyst_finding_validation_satisfied"] is False
    assert dprime["objects_created"]["run_kernel_admission_decision"] is False
    assert dprime["objects_created"]["semantic_observation"] is False
    assert dprime["objects_created"]["component_coverage"] is False
    assert dprime["objects_created"]["sufficiency_readiness"] is False
    assert dprime["objects_created"]["final_answer_packet"] is False
    assert dprime["objects_created"]["author_answer"] is False
    assert dprime["objects_created"]["citation_source_display"] is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"


def _validate_finding(
    finding: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    return build_dprime_analyst_finding_support_validation(
        workbench_dprime_dossier=_dossier_with_finding(bundle, finding),
        fetch_read_content_packet=_bounded_fetch_packet(),
    )


def _dossier_with_finding(
    bundle: Mapping[str, Any],
    finding: Mapping[str, Any],
) -> dict[str, Any]:
    dossier = dict(bundle["workbench_dprime_dossier"])
    dossier["analyst_finding_proposal"] = finding
    dossier["analyst_finding_proposal_ref"] = finding.get(
        "analyst_finding_proposal_ref",
        {},
    )
    return dossier


def _product_grade_model_assisted_finding(
    bundle: Mapping[str, Any],
) -> Mapping[str, Any]:
    deterministic = _finding(bundle)

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"analyst_finding_proposal": deterministic}

    return build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        fetch_read_content_packet=_bounded_fetch_packet(),
        model_assisted_analyst_license=build_model_assisted_analyst_license(
            license_id="dprime-product-grade-analyst:test",
        ),
        model_assisted_analyst_adapter=fake_adapter,
    )


def _bounded_fetch_packet() -> dict[str, Any]:
    return _safe_fetch_read_packet_for_direct_candidate(
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        bounded_text="The current standard paper small claims filing fee is 54 dollars.",
    )
