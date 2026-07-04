"""PRODUCT-PATH-REGRESSION: generic single-relation D-prime non-support repair.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run ->
proplex.live_semantic_coverage_status -> core.dprime_model_review_assessment
Why ordinary product-path work cannot be done directly: offline tests must not
make live provider, broker, fetch/read, retrieval, or model calls; injected
provider and D-prime callables exercise the same product entrypoint and retained
artifact consumer.
Integration deadline: current phase.
Exit condition: keep while generic single-relation D-prime uses transient
bounded evidence windows, or replace with a broader product-consumed diagnostic
guard.
Why this is not a shadow product path: tests call the product entrypoint builder
and existing retained-artifact D-prime consumers.
Forbidden interpretation: diagnostic refs are not semantic support, citation
eligibility, source-obligation satisfaction, FAP/Author, product correctness, or
live validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.dprime_support_proposal_schema as dprime
from core.dprime_model_review_assessment import (
    DPrimeModelReviewAssessmentError,
    build_dprime_model_review_input_packet,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    DEFAULT_OUTPUT_DIR,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import (
    _model_review_input_args,
)
from tests.test_generic_single_relation_live_dogfood_01 import (
    N400_QUERY,
    _provider_extracted_result,
    _recording_proxy_runner,
)


def test_answer_bearing_provider_extracted_content_reaches_dprime_window_ref(
    tmp_path: Path,
) -> None:
    calls: list[Any] = []
    review_input_packets: list[Mapping[str, Any]] = []
    extracted_text = (
        "USCIS Form N-400 paper filing fee schedule. The current Form N-400 "
        "paper filing fee is $760 for this synthetic official fixture."
    )

    def fake_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        input_packet = dict(kwargs["input_packet"])
        review_input_packets.append(input_packet)
        return _assessment_payload(
            input_packet,
            support_relation="directly_supports",
            claim="USCIS Form N-400 paper filing fee is $760.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="dprime-window-diagnostic-support",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    extracted_text,
                )
            ],
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.decision == "PASS", result.packet.get("blocker_detail")
    assert len(review_input_packets) == 1
    dprime_status = result.packet["semantic_status_payload"]["dprime_status"]
    input_ref = dprime_status["input_packet_ref"]
    diagnostic = input_ref["selected_window_diagnostic_ref"]
    evidence_window = input_ref["evidence_window_ref"]
    admission = result.packet["semantic_status_payload"]["source_evidence_admission_ref"]
    content_ref = dprime_status["evidence_frame_preflight_ref"][
        "content_reference_ref"
    ]
    relation_ref = result.packet["dprime_relation_intake_ref"]

    assert diagnostic["diagnostic_only"] is True
    assert diagnostic["not_semantic_support"] is True
    assert diagnostic["anchor_match_status"] == "all_required_anchors_matched"
    assert diagnostic["value_token_observed"] is True
    assert diagnostic["value_token_kind_counts"]["currency"] == 1
    assert evidence_window["window_text_retained"] is False
    assert evidence_window["window_text_printed"] is False
    assert content_ref["reference_id"] == admission["reference_id"]
    assert content_ref["reference_digest"] == admission["reference_digest"]
    assert content_ref["candidate_id"] == admission["candidate_id"]
    assert relation_ref["source_url"] == "https://www.uscis.gov/forms/filing-fees"
    assert relation_ref["source_domain"] == "www.uscis.gov"
    assert relation_ref["source_title"] == "USCIS Form N-400 Filing Fee"
    assert result.packet["provider_extracted_original_url_bindings_preserved"] is True
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert result.packet["fap_author_opened"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["product_correctness_claimed"] is False
    assert "bounded_text" not in json.dumps(result.packet, sort_keys=True)


def test_non_support_assessment_remains_blocked_with_safe_window_diagnostic(
    tmp_path: Path,
) -> None:
    calls: list[Any] = []
    extracted_text = (
        "USCIS Form N-400 paper filing fee schedule. The current Form N-400 "
        "paper filing fee is $760 for this synthetic official fixture."
    )

    def fake_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            kwargs["input_packet"],
            support_relation="absent",
            claim="USCIS Form N-400 paper filing fee is $760.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="dprime-window-diagnostic-non-support",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    extracted_text,
                )
            ],
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    dprime_status = result.packet["semantic_status_payload"]["dprime_status"]
    diagnostic = dprime_status["input_packet_ref"]["selected_window_diagnostic_ref"]

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT
    assert dprime_status["assessment_status"] == "non-support"
    assert dprime_status["validated_support_proposal_available"] is False
    assert dprime_status["run_kernel_support_admission_request_ref"] == {}
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert diagnostic["diagnostic_only"] is True
    assert diagnostic["not_model_decision"] is True
    assert diagnostic["value_token_observed"] is True
    assert result.packet["answer_text_present"] is False
    assert result.packet["source_display_entries"] == []
    assert result.packet["raw_model_response_retained"] is False


def test_challenge_relation_with_false_flag_routes_to_challenge_blocker(
    tmp_path: Path,
) -> None:
    calls: list[Any] = []
    extracted_text = (
        "N-400 Naturalization Fee in 2026: Costs and Fee Waivers. The page says "
        "the current Form N-400 paper filing fee is $760, but it is a "
        "non-official explainer rather than source-of-record confirmation."
    )

    def fake_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        payload = _assessment_payload(
            kwargs["input_packet"],
            support_relation="weak_or_overclaim_risk",
            claim="USCIS Form N-400 paper filing fee is $760.",
        )
        payload["challenge_recommended"] = False
        payload["non_support_reason_when_not_direct"] = (
            "The answer-bearing material is not source-of-record confirmation."
        )
        payload["evidential_adequacy_notes"] = (
            "The model explicitly identified weak_or_overclaim_risk."
        )
        return payload

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="dprime-challenge-relation-derived-flag",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "N-400 Naturalization Fee in 2026: Costs and Fee Waivers",
                    "https://example-law.invalid/n-400-fee-guide",
                    extracted_text,
                )
            ],
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    dprime_status = result.packet["semantic_status_payload"]["dprime_status"]
    normalization_ref = dprime_status["assessment_material_ref"][
        "challenge_relation_normalization_ref"
    ]
    assert (
        result.decision
        == dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED
    )
    assert dprime_status["assessment_status"] == "challenge-recommended"
    assert dprime_status["support_relation"] == "weak_or_overclaim_risk"
    assert dprime_status["validated_support_proposal_available"] is False
    assert dprime_status["run_kernel_support_admission_request_ref"] == {}
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert (
        dprime_status["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is False
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert normalization_ref == {
        "challenge_recommended_model_provided": False,
        "challenge_recommended_derived_from_support_relation": True,
        "challenge_relation": "weak_or_overclaim_risk",
        "normalization_is_conservative": True,
        "support_not_created": True,
    }
    assert result.packet["answer_text_present"] is False
    assert result.packet["source_display_entries"] == []
    assert result.packet["actual_source_authority_posture_created"] is False
    assert result.packet["candidate_selection_created_source_authority"] is False
    assert result.packet["candidate_selection_citation_eligible"] is False
    assert result.packet["candidate_selection_satisfies_source_obligation"] is False
    assert result.packet["fap_author_opened"] is False
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert "bounded_text" not in json.dumps(result.packet, sort_keys=True)


def test_missing_or_mismatched_content_reference_fails_before_model_review(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    inputs = _model_review_input_args(repo_root)
    bad_admission = dict(inputs["source_evidence_admission_ref"])
    bad_admission["reference_id"] = "sanitized-content-reference:missing"
    inputs["source_evidence_admission_ref"] = bad_admission

    with pytest.raises(
        DPrimeModelReviewAssessmentError,
        match="matching readable sanitized content reference is missing",
    ):
        build_dprime_model_review_input_packet(**inputs)


def _assessment_payload(
    input_packet: Mapping[str, Any],
    *,
    support_relation: str,
    claim: str,
) -> dict[str, Any]:
    component_ref = dict(input_packet["component_ref"])
    payload = {
        "source_proposition": f"The retained material states: {claim}",
        "answer_component_claim": {
            "component_id": component_ref["component_id"],
            "claim": claim,
        },
        "support_relation": support_relation,
        "required_qualifiers": [claim],
        "observed_qualifiers": [claim] if support_relation == "directly_supports" else [],
        "missing_qualifiers": [],
        "scope_check": {
            "status": "passed"
            if support_relation == "directly_supports"
            else "scope_mismatch"
        },
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": "The fake review maps the retained material to the component.",
        "non_support_reason_when_not_direct": (
            "" if support_relation == "directly_supports" else "fake proposition absent"
        ),
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
    if support_relation != "directly_supports":
        payload["required_qualifiers"] = [claim]
    return payload
