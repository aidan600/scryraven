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
from core.dprime_evidence_support_bundle_runtime import (
    BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_NOT_LICENSED,
    BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED,
)
from proplex.live_semantic_coverage_status import (
    BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION,
    build_live_semantic_coverage_status,
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
from tests.test_dprime_model_review_assessment_slice_01 import (
    _assessment_payload,
    _license,
)

SMALL_CLAIMS_COMPONENT_ID = "component:example-county-small-claims-fee"
SMALL_CLAIMS_OBLIGATION_ID = "obligation:example-county-small-claims-fee-source"


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


def test_product_grade_supported_analyst_finding_reaches_runkernel_authority_stop_point(
    tmp_path: Path,
) -> None:
    bundle = _answer_bearing_bundle()
    finding = _product_grade_model_assisted_finding(bundle)
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text="The current standard paper small claims filing fee is 54 dollars.",
        title="Official Current Standard Filing Fee",
        url="https://example-county.gov/courts/current-filing-fee",
        domain="example-county.gov",
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        component_id=SMALL_CLAIMS_COMPONENT_ID,
        source_obligation_id=SMALL_CLAIMS_OBLIGATION_ID,
        snippet="Official current standard small claims filing fee.",
    )

    result = _run_product_status_for_analyst_finding(
        repo_root=repo_root,
        finding=finding,
        bundle=bundle,
        assessment_payload=_small_claims_assessment_payload(),
    )

    assert result.decision == BLOCKED_DPRIME_SOURCE_OBLIGATION_AUTHORITY_NOT_LICENSED
    dprime = result.payload["dprime_status"]
    validation = dprime["dprime_analyst_finding_support_validation"]
    assert validation["dprime_validation_status"] == DPRIME_SUPPORT_VALIDATION_SUPPORTED
    assert support_validation_allows_runkernel_admission(validation) is True
    assert validation["runkernel_admission_created"] is False
    assert dprime["dprime_analyst_finding_validation_satisfied"] is True
    assert dprime["runkernel_analyst_finding_admission_required"] is True
    assert dprime["runkernel_analyst_finding_admission_attempted"] is True
    assert dprime["runkernel_analyst_finding_admission_satisfied"] is True
    assert dprime["runkernel_analyst_finding_admission_ref"]
    assert dprime["analyst_finding_semantic_observation_ref"]["status"] == "admitted"
    assert dprime["analyst_finding_component_coverage_ref"]["status"] == "bound"
    assert dprime["objects_created"]["run_kernel_admission_decision"] is True
    assert dprime["objects_created"]["semantic_observation"] is True
    assert dprime["objects_created"]["component_coverage"] is True
    assert dprime["component_coverage_stop_point_reached"] is True
    assert dprime["support_bundle_completed"] is False
    assert dprime["legacy_candidate_level_dprime_review_treated_as_answer_authority"] is False
    assert dprime["source_obligation_authority_consumed"] is False
    assert (
        dprime["citation_eligibility_or_source_handoff_authority_consumed"]
        is False
    )
    assert dprime["source_obligation_satisfied"] is False
    assert dprime["citation_eligibility_created"] is False
    assert dprime["sufficiency_readiness_created"] is False
    assert dprime["final_answer_packet_created"] is False
    assert dprime["author_output_created"] is False
    assert dprime["source_display_opened"] is False
    assert dprime["product_correctness_claimed"] is False
    assert result.payload["component_coverage_ref"]["status"] == "bound"
    assert result.payload["source_obligation_authority_ref"]["authority_consumed"] is False
    assert (
        result.payload["citation_eligibility_authority_ref"]["authority_consumed"]
        is False
    )
    assert result.payload["source_obligation_satisfied"] is False
    assert result.payload["citation_eligibility_created"] is False
    assert result.payload["sufficiency_readiness_created"] is False
    assert result.payload["final_answer_packet_created"] is False
    assert result.payload["author_output_created"] is False
    assert result.payload["source_display_opened"] is False
    assert result.payload["product_correctness_claimed"] is False


def test_product_grade_supported_analyst_finding_consumes_source_citation_authority(
    tmp_path: Path,
) -> None:
    bundle = _answer_bearing_bundle()
    finding = _product_grade_model_assisted_finding(bundle)
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text="The current standard paper small claims filing fee is 54 dollars.",
        title="Official Current Standard Filing Fee",
        url="https://example-county.gov/courts/current-filing-fee",
        domain="example-county.gov",
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        component_id=SMALL_CLAIMS_COMPONENT_ID,
        source_obligation_id=SMALL_CLAIMS_OBLIGATION_ID,
        snippet="Official current standard small claims filing fee.",
    )

    result = _run_product_status_for_analyst_finding(
        repo_root=repo_root,
        finding=finding,
        bundle=bundle,
        assessment_payload=_small_claims_assessment_payload(),
        dprime_source_citation_authority_enabled=True,
    )

    assert result.decision == BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED
    dprime = result.payload["dprime_status"]
    assert dprime["dprime_analyst_finding_validation_satisfied"] is True
    assert dprime["runkernel_analyst_finding_admission_satisfied"] is True
    assert dprime["objects_created"]["semantic_observation"] is True
    assert dprime["objects_created"]["component_coverage"] is True
    assert dprime["support_bundle_completed"] is True
    assert dprime["dprime_source_citation_stoppoint_status"] == "consumed"
    assert dprime["source_obligation_authority_consumed"] is True
    assert (
        dprime["citation_eligibility_or_source_handoff_authority_consumed"]
        is True
    )
    source_ref = result.payload["source_obligation_authority_ref"]
    citation_ref = result.payload["citation_eligibility_authority_ref"]
    assert source_ref["owner"] == "RunKernel.DPrimeSourceObligationAuthority"
    assert citation_ref["owner"] == "RunKernel.DPrimeCitationSourceHandoffAuthority"
    assert source_ref["runtime_surface"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert citation_ref["runtime_surface"] == (
        "core.dprime_source_obligation_citation_authority_runtime"
    )
    assert source_ref["authority_consumed"] is True
    assert source_ref["source_obligation_status"] == "satisfied"
    assert citation_ref["authority_consumed"] is True
    assert citation_ref["citation_source_handoff_consumed"] is True
    assert citation_ref["citation_rendering_created"] is False
    assert citation_ref["citations_rendered"] is False
    assert dprime["objects_created"]["sufficiency_readiness"] is False
    assert dprime["objects_created"]["final_answer_packet"] is False
    assert dprime["objects_created"]["author_answer"] is False
    assert dprime["objects_created"]["citation_source_display"] is False
    assert dprime["sufficiency_readiness_created"] is False
    assert dprime["final_answer_packet_created"] is False
    assert dprime["author_output_created"] is False
    assert dprime["source_display_opened"] is False
    assert dprime["product_correctness_claimed"] is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"
    assert result.payload["citation_eligibility_created"] is False
    assert result.payload["final_answer_packet_created"] is False
    assert result.payload["author_output_created"] is False
    assert result.payload["source_display_opened"] is False
    assert result.payload["product_correctness_claimed"] is False


def test_product_grade_unsupported_analyst_finding_validation_blocks_admission(
    tmp_path: Path,
) -> None:
    bundle = _answer_bearing_bundle()
    finding = _product_grade_model_assisted_unsupported_edge_finding(bundle)
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text="This page lists courthouse parking rules and holiday hours.",
        title="Official Courthouse Hours",
        url="https://example-county.gov/courts/hours",
        domain="example-county.gov",
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        component_id=SMALL_CLAIMS_COMPONENT_ID,
        source_obligation_id=SMALL_CLAIMS_OBLIGATION_ID,
        snippet="Official courthouse hours information.",
    )

    result = _run_product_status_for_analyst_finding(
        repo_root=repo_root,
        finding=finding,
        bundle=bundle,
        assessment_payload=_small_claims_assessment_payload(),
    )

    assert result.decision == BLOCKED_DPRIME_ANALYST_FINDING_SUPPORT_VALIDATION
    dprime = result.payload["dprime_status"]
    validation = dprime["dprime_analyst_finding_support_validation"]
    assert validation["dprime_validation_status"] in {
        DPRIME_SUPPORT_VALIDATION_ADJACENT_OVERCLAIM,
        DPRIME_SUPPORT_VALIDATION_INVALID_PROPOSAL,
        DPRIME_SUPPORT_VALIDATION_UNSUPPORTED,
        DPRIME_SUPPORT_VALIDATION_INSUFFICIENT,
    }
    assert support_validation_allows_runkernel_admission(validation) is False
    assert dprime["runkernel_analyst_finding_admission_required"] is True
    assert dprime["runkernel_analyst_finding_admission_attempted"] is False
    assert dprime["runkernel_analyst_finding_admission_satisfied"] is False
    assert dprime["runkernel_analyst_finding_admission_ref"] == {}
    assert dprime["objects_created"]["run_kernel_admission_decision"] is False
    assert dprime["objects_created"]["semantic_observation"] is False
    assert dprime["objects_created"]["component_coverage"] is False
    assert dprime["source_obligation_satisfied"] is False
    assert dprime["citation_eligibility_created"] is False
    assert dprime["sufficiency_readiness_created"] is False
    assert dprime["final_answer_packet_created"] is False
    assert dprime["author_output_created"] is False
    assert dprime["source_display_opened"] is False
    assert dprime["product_correctness_claimed"] is False


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
    assert dprime["legacy_candidate_level_dprime_review_treated_as_answer_authority"] is False
    assert dprime["runkernel_analyst_finding_admission_attempted"] is False
    assert dprime["source_obligation_satisfied"] is False
    assert dprime["citation_eligibility_created"] is False
    assert dprime["author_output_created"] is False
    assert dprime["source_display_opened"] is False
    assert dprime["product_correctness_claimed"] is False
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
    assert dprime["legacy_candidate_level_dprime_review_treated_as_answer_authority"] is False
    assert dprime["source_obligation_satisfied"] is False
    assert dprime["citation_eligibility_created"] is False
    assert dprime["author_output_created"] is False
    assert dprime["source_display_opened"] is False
    assert dprime["product_correctness_claimed"] is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"


def test_analyst_finding_admission_reuses_existing_authority_surfaces() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "core" / "runkernel_analyst_finding_admission_bridge.py").exists()
    status_runtime = (root / "proplex" / "live_semantic_coverage_status.py").read_text(
        encoding="utf-8"
    )
    bundle_runtime = (
        root / "core" / "dprime_evidence_support_bundle_runtime.py"
    ).read_text(encoding="utf-8")

    assert "build_run_kernel_dprime_admission_decision(" in status_runtime
    assert (
        "materialize_dprime_semantic_observation_from_admitted_decision("
        in status_runtime
    )
    assert "bind_dprime_component_coverage_from_semantic_observation(" in (
        status_runtime
    )
    assert "class RunKernelAnalystFinding" not in status_runtime
    assert "DPrimeComponentCoverageBindingResult" in bundle_runtime
    assert "RunKernel.ComponentCoverageReduction" in bundle_runtime


def _run_product_status_for_analyst_finding(
    *,
    repo_root: Path,
    finding: Mapping[str, Any],
    bundle: Mapping[str, Any],
    assessment_payload: dict[str, Any],
    dprime_source_citation_authority_enabled: bool = False,
) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return assessment_payload

    return build_live_semantic_coverage_status(
        query="What is the current filing fee for small claims in Example County?",
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
        dprime_source_citation_authority_enabled=(
            dprime_source_citation_authority_enabled
        ),
        dprime_single_lane_answer_path_enabled=False,
        workbench_dprime_dossier=_dossier_with_finding(bundle, finding),
    )


def _small_claims_assessment_payload() -> dict[str, Any]:
    return {
        "source_proposition": (
            "The retained source states the current standard paper small "
            "claims filing fee is 54 dollars."
        ),
        "answer_component_claim": {
            "component_id": SMALL_CLAIMS_COMPONENT_ID,
            "claim": "The current standard paper small claims filing fee is $54.",
        },
        "support_relation": "directly_supports",
        "required_qualifiers": [
            "current",
            "standard",
            "paper",
            "small claims filing fee",
        ],
        "observed_qualifiers": [
            "current",
            "standard",
            "paper",
            "small claims filing fee",
        ],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The fake review maps the retained proposition to the same "
            "small-claims fee component."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "closed_surface_flags": {
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
        },
    }


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


def _product_grade_model_assisted_unsupported_edge_finding(
    bundle: Mapping[str, Any],
) -> Mapping[str, Any]:
    deterministic = copy.deepcopy(_finding(bundle))
    for edge in deterministic["source_support_map"]["analysis_claim_support_edges"]:
        if edge.get("edge_kind") == "candidate_supports_analysis_claim":
            edge["candidate_ref"] = {
                "candidate_id": "unknown-nonselected-candidate",
                "candidate_digest": "unknown-nonselected-digest",
            }
            break

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"analyst_finding_proposal": deterministic}

    return build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        fetch_read_content_packet=_bounded_fetch_packet(),
        model_assisted_analyst_license=build_model_assisted_analyst_license(
            license_id="dprime-product-grade-unsupported-edge:test",
        ),
        model_assisted_analyst_adapter=fake_adapter,
    )


def _bounded_fetch_packet() -> dict[str, Any]:
    return _safe_fetch_read_packet_for_direct_candidate(
        candidate_id="direct-candidate-2",
        candidate_digest="direct-digest-2",
        bounded_text="The current standard paper small claims filing fee is 54 dollars.",
    )
