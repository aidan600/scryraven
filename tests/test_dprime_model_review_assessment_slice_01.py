"""PRODUCT-PATH-REGRESSION: D-prime injected model-review assessment slice.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming the default-disabled D-prime model-review assessment slice
Why ordinary product-path work cannot be done directly: real model review is not
licensed; this phase permits only an injected fake callable to exercise the
assessment-only seam while the ordinary CLI remains blocked by default.
Integration deadline: current phase.
Exit condition: keep while D-prime model review remains default-disabled and
assessment-only before any proposal/admission phase is licensed.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned D-prime model-review adapter with an injected fake callable,
not a standalone script or live provider path.
Forbidden interpretation: fake assessment review is not a real model call,
semantic support, support proposal validation, RunKernel admission,
SemanticObservation admission, ComponentCoverage binding, citation eligibility,
answer text, source-obligation satisfaction, or product correctness.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Callable

import pytest

import core.dprime_assessment_validation as assessment_validation
import core.dprime_one_shot_provider_boundary as provider_boundary
import core.dprime_support_proposal_schema as dprime
import proplex.live_semantic_coverage_status as semantic_status
from core.dprime_model_review_assessment import (
    DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE,
    DPrimeModelReviewLicense,
    build_dprime_model_review_input_packet,
)
from core.dprime_model_review_prompt import (
    AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS,
    CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS,
    DPRIME_MODEL_REVIEW_CANONICAL_OUTPUT_SKELETON,
    DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA,
    DPRIME_MODEL_REVIEW_RELATION_CHECK_STATUS_CONSISTENCY_MATRIX,
    MODEL_FILLABLE_ASSESSMENT_FIELDS,
    RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS,
    build_dprime_model_review_prompt,
    prompt_metadata,
)
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_COMPONENT_ID,
    PASSPORT_TEXT,
    QUERY,
    UNRELATED_SAME_LANE_TEXT,
    _passport_retained_repo,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_REVIEW_MODULE = ROOT / "core" / "dprime_model_review_assessment.py"
MODEL_REVIEW_PROMPT_MODULE = ROOT / "core" / "dprime_model_review_prompt.py"
ADAPTER_REF = "fixture-one-shot-adapter-ref:dprime-adapter-contract-01"


def test_default_ordinary_cli_remains_blocked_without_model_review_license(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert f"phase: {dprime.DPRIME_PHASE}" in result.output
    assert "D-prime one-shot provider boundary status: not approved" in result.output
    assert (
        "D-prime one-shot model-review adapter status: not configured"
        in result.output
    )
    assert "D-prime model review status: not licensed" in result.output
    assert "D-prime model review call count: 0" in result.output
    assert "D-prime assessment status: not reached" in result.output
    assert (
        f"decision: {dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED}"
        in result.output
    )


def test_model_review_prompt_schema_names_exact_model_fillable_allowlist() -> None:
    schema = DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA

    assert schema["model_fillable_allowed_fields"] == (
        MODEL_FILLABLE_ASSESSMENT_FIELDS
    )
    assert schema["required_fields"] == MODEL_FILLABLE_ASSESSMENT_FIELDS
    assert set(schema["model_fillable_allowed_fields"]) == {
        "source_proposition",
        "answer_component_claim",
        "support_relation",
        "required_qualifiers",
        "observed_qualifiers",
        "missing_qualifiers",
        "scope_check",
        "currentness_check",
        "contradiction_check",
        "evidential_adequacy_notes",
        "non_support_reason_when_not_direct",
        "producer_abstained",
        "challenge_recommended",
        "closed_surface_flags",
    }
    assert (
        "top-level keys are exactly model_fillable_allowed_fields"
        in schema["model_output_contract"]
    )


def test_model_review_prompt_schema_includes_canonical_output_skeleton() -> None:
    schema = DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA
    skeleton = schema["canonical_output_skeleton"]

    assert skeleton == DPRIME_MODEL_REVIEW_CANONICAL_OUTPUT_SKELETON
    assert list(skeleton) == MODEL_FILLABLE_ASSESSMENT_FIELDS
    assert set(skeleton) == set(schema["model_fillable_allowed_fields"])
    assert set(skeleton).isdisjoint(
        schema["forbidden_runtime_filled_fields"]
        + schema["forbidden_authority_object_created_fields"]
    )
    assert "assessment_digest" not in skeleton
    assert set(skeleton["closed_surface_flags"]) == set(
        CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS
    )
    assert all(value is False for value in skeleton["closed_surface_flags"].values())


def test_model_review_prompt_schema_includes_required_mapping_shapes() -> None:
    schema = DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA
    skeleton = schema["canonical_output_skeleton"]
    requirements = schema["field_level_requirements"]

    assert set(skeleton["answer_component_claim"]) == {"component_id", "claim"}
    assert requirements["answer_component_claim"]["required_keys"] == [
        "component_id",
        "claim",
    ]
    assert set(skeleton["scope_check"]) == {"status"}
    assert requirements["scope_check"]["required_keys"] == ["status"]
    assert set(skeleton["currentness_check"]) == {"status"}
    assert requirements["currentness_check"]["required_keys"] == ["status"]
    assert set(skeleton["contradiction_check"]) == {"status"}
    assert requirements["contradiction_check"]["required_keys"] == ["status"]
    for field in (
        "required_qualifiers",
        "observed_qualifiers",
        "missing_qualifiers",
    ):
        assert skeleton[field] == []
    assert skeleton["producer_abstained"] is False
    assert skeleton["challenge_recommended"] is False


def test_model_review_prompt_schema_includes_relation_check_matrix() -> None:
    matrix = DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA[
        "relation_check_status_consistency_matrix"
    ]

    assert matrix == DPRIME_MODEL_REVIEW_RELATION_CHECK_STATUS_CONSISTENCY_MATRIX
    assert matrix["directly_supports"]["scope_check.status"] == [
        "passed",
        "in_scope",
        "matched",
    ]
    assert matrix["partially_supports"]["currentness_check.status"] == [
        "passed",
        "current",
        "current_passed",
    ]
    assert matrix["directly_supports"]["contradiction_check.status"] == [
        "absent",
        "none",
        "not_contradicted",
    ]
    assert matrix["scope_mismatch"]["scope_check.status"] == [
        "failed",
        "scope_mismatch",
    ]
    assert matrix["currentness_mismatch"]["currentness_check.status"] == [
        "failed",
        "stale",
        "wrong_effective_date",
        "currentness_mismatch",
    ]
    assert matrix["contradicts"]["contradiction_check.status"] == [
        "contradicts",
        "contradicted",
        "failed",
    ]
    assert matrix["weak_or_overclaim_risk"][
        "must_not_have_contradiction_check.status"
    ] == ["contradicts", "contradicted"]
    assert matrix["abstained"]["producer_abstained"] is True


def test_model_review_prompt_schema_forbids_runtime_filled_model_keys() -> None:
    forbidden = set(DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA["forbidden_runtime_filled_fields"])

    assert forbidden == set(RUNTIME_FILLED_FORBIDDEN_MODEL_OUTPUT_FIELDS)
    for field in (
        "assessment_id",
        "assessment_digest",
        "preflight_ref",
        "preflight_digest",
        "negative_control_profile_ref",
        "negative_control_profile_digest",
        "selector_ref",
        "component_ref",
        "source_obligation_ref",
        "model_review_ref",
        "prompt_license_ref",
    ):
        assert field in forbidden


def test_model_review_prompt_schema_forbids_authority_created_model_keys() -> None:
    schema = DPRIME_MODEL_REVIEW_OUTPUT_SCHEMA
    forbidden = set(schema["forbidden_authority_object_created_fields"])

    assert forbidden == set(AUTHORITY_OBJECT_FORBIDDEN_MODEL_OUTPUT_FIELDS)
    for field in (
        "assessment_created",
        "validated_support_proposal_created",
        "run_kernel_support_admission_request_created",
        "semantic_observation_created",
        "component_coverage_created",
        "citation_eligibility_claimed",
        "source_obligation_satisfaction_claimed",
        "answer_text_created",
        "product_correctness_claimed",
        "analysis_gap_search_proposal",
    ):
        assert field in forbidden
        assert field in schema["forbidden_top_level_fields"]
    assert schema["closed_surface_flags_required_false_keys"] == (
        CLOSED_SURFACE_FLAGS_REQUIRED_FALSE_KEYS
    )
    assert "component_coverage_bound" in (
        schema["closed_surface_flags_required_false_keys"]
    )


def test_model_review_prompt_metadata_retains_no_raw_prompt() -> None:
    prompt = build_dprime_model_review_prompt(
        input_packet={"safe": "packet"},
        transient_bounded_evidence_window="sanitized bounded evidence",
    )
    metadata = prompt_metadata(prompt)

    assert "output_schema.model_fillable_allowed_fields" in prompt
    assert "output_schema.canonical_output_skeleton" in prompt
    assert "Missing fields are never allowed" in prompt
    assert "answer_component_claim.component_id must equal" in prompt
    assert "scope_check, currentness_check, and contradiction_check" in prompt
    assert "Never include assessment_digest" in prompt
    assert "output_schema.runtime_filled_fields" in prompt
    assert "output_schema.forbidden_authority_object_created_fields" in prompt
    assert "output_schema.relation_check_status_consistency_matrix" in prompt
    assert "weak_or_overclaim_risk must not be used for an actual contradiction" in prompt
    assert metadata["raw_prompt_retained"] is False
    assert "prompt" not in metadata


def test_injected_fake_direct_support_assessment_validates_proposal_then_blocks_before_run_kernel(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls: list[dict[str, Any]] = []

    def fake_review(prompt: str, **kwargs: Any) -> dict[str, Any]:
        calls.append(
            {
                "prompt": prompt,
                "input_packet": kwargs["input_packet"],
                "boundary_ref": kwargs["one_shot_provider_boundary_ref"],
            }
        )
        assert "EvidenceRelativeSupportAssessment" in prompt
        assert "bounded_text" not in json.dumps(kwargs["input_packet"])
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )

    assert calls and len(calls) == 1
    assert calls[0]["input_packet"]["one_shot_provider_boundary_ref"]["status"] == (
        "not approved"
    )
    assert calls[0]["input_packet"]["one_shot_model_review_adapter_ref"][
        "status"
    ] == "not configured"
    assert calls[0]["boundary_ref"]["status"] == "not approved"
    assert result.decision == (
        dprime.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
    )
    assert result.return_code == 2
    assert "D-prime model review status: completed" in result.output
    assert "D-prime assessment status: assessed" in result.output
    assert (
        "D-prime assessment validation status: "
        f"{assessment_validation.ASSESSMENT_SCHEMA_VALID}"
    ) in result.output
    assert (
        "D-prime proposal validation status: "
        f"{dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED}"
    ) in result.output
    assert (
        "RunKernel support admission status: "
        f"{dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY}"
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
    assert dprime_status["phase"] == dprime.DPRIME_PHASE
    assert dprime_status["prompt_license_ref"]["phase"] == (
        DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE
    )
    assert dprime_status["input_packet_ref"]["phase"] == (
        DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE
    )
    assert dprime_status["model_review_ref"]["phase"] == (
        DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE
    )
    assert calls[0]["input_packet"]["phase"] == DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE
    assert dprime_status["model_review_ref"]["input_packet_ref"]["phase"] == (
        DPRIME_MODEL_REVIEW_ASSESSMENT_PHASE
    )
    assert dprime_status["prompt_license_ref"]["fake_test_callable_only"] is True
    assert dprime_status["prompt_license_ref"]["callable_kind"] == "fake_test"
    assert dprime_status["model_review_call_count"] == 1
    assert (
        dprime_status["proposal_validation_status"]
        == dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["run_kernel_admission_decision_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert dprime_status["run_kernel_admission_decision_ref"][
        "admitted_support"
    ] is False
    assert (
        dprime_status["run_kernel_support_admission_status"]
        == dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    request_ref = dprime_status["run_kernel_support_admission_request_ref"]
    assert request_ref["request_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert request_ref["support_proposal_ref"] == {
        "proposal_id": dprime_status["validated_support_proposal_ref"][
            "proposal_id"
        ],
        "proposal_digest": dprime_status["validated_support_proposal_ref"][
            "proposal_digest"
        ],
    }
    assert request_ref["validation_result_ref"]["validation_status"] == (
        dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["run_kernel_decision"] == "not made"
    assert dprime_status["admitted_support"] is False
    assert dprime_status["validated_support_proposal_available"] is True
    assert dprime_status["validated_support_proposal_ref"]["proposal_id"]
    assert dprime_status["validated_support_proposal_ref"]["proposal_digest"]
    assert (
        dprime_status["validated_support_proposal_ref"]["assessment_ref"]
        == dprime_status["assessment_ref"]
    )
    assert (
        dprime_status["validated_support_proposal_ref"]["input_packet_ref"][
            "input_packet_digest"
        ]
        == dprime_status["input_packet_ref"]["input_packet_digest"]
    )
    assert (
        dprime_status["validated_support_proposal_ref"]["model_review_ref"][
            "model_review_digest"
        ]
        == dprime_status["model_review_ref"]["model_review_digest"]
    )
    assert (
        dprime_status["support_proposal_validation_ref"]["run_kernel_decision"]
        == "not made"
    )
    assert dprime_status["objects_created"]["evidence_relative_support_assessment"] is True
    assert dprime_status["objects_created"]["validated_support_proposal"] is True
    assert (
        dprime_status["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is True
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert result.decision != "PASS"


def test_real_call_style_without_approved_boundary_blocks_before_callable(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_real_license(),
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert "approved one-shot provider boundary" in result.output


def test_test_only_boundary_cannot_authorize_real_call_style(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_fixture_boundary(),
        dprime_model_review_license=_real_license(),
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert "test-only provider boundary" in result.output


def test_real_call_style_rejects_bare_callable_even_with_approved_boundary(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def future_adapter(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_model_review_license=_real_license(),
        dprime_model_review_callable=future_adapter,
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert "not a bare callable" in result.output


def test_one_call_cap_and_no_retries_on_timeout(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def fake_timeout(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise TimeoutError("fake timeout")

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_timeout,
    )

    assert calls == 1
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED
    assert result.payload["dprime_status"]["model_review_call_count"] == 1
    assert "D-prime model review status: blocked" in result.output


def test_license_cannot_expand_model_review_call_cap(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=DPrimeModelReviewLicense(
            enabled=True,
            max_model_review_calls=2,
        ),
        dprime_model_review_callable=fake_review,
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert "D-prime model review status: blocked" in result.output
    assert result.payload["dprime_status"]["model_review_call_count"] == 0


def test_malformed_output_fails_closed_without_retry(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def fake_malformed(*_args: Any, **_kwargs: Any) -> str:
        nonlocal calls
        calls += 1
        return "not json"

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_malformed,
    )

    assert calls == 1
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert "D-prime assessment status: invalid" in result.output
    assert result.payload["dprime_status"]["objects_created"][
        "evidence_relative_support_assessment"
    ] is False


def test_analysis_gap_search_proposal_output_fails_closed_without_echo(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    payload["analysis_gap_search_proposal"] = {
        "proposal_text": "search again for broader evidence",
    }

    result = _run_with_payload(repo_root, payload)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert result.payload["dprime_status"]["objects_created"][
        "evidence_relative_support_assessment"
    ] is False
    assert result.payload["dprime_status"]["objects_created"][
        "validated_support_proposal"
    ] is False
    assert (
        result.payload["dprime_status"]["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is False
    )
    assert result.payload["dprime_status"]["objects_created"]["semantic_observation"] is False
    assert result.payload["dprime_status"]["objects_created"]["component_coverage"] is False
    assert "analysis_gap_search_proposal" not in result.output
    assert "search again for broader evidence" not in result.output


def test_authority_upgrade_output_validation_error_fails_closed_without_traceback(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    payload["assessment_created"] = True

    result = _run_with_payload(repo_root, payload)
    dprime_status = result.payload["dprime_status"]

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert dprime_status["model_review_status"] == "blocked"
    assert dprime_status["assessment_status"] == "invalid"
    assert dprime_status["model_review_call_count"] == 1
    assert dprime_status["raw_prompt_retained"] is False
    assert dprime_status["raw_model_response_retained"] is False
    assert dprime_status["provider_payload_retained"] is False
    assert dprime_status["objects_created"][
        "evidence_relative_support_assessment"
    ] is False
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert (
        dprime_status["objects_created"][
            "run_kernel_support_proposal_admission_request"
        ]
        is False
    )
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert "DPrimeAssessmentValidationError" not in result.output
    assert "Traceback" not in result.output
    assert "assessment_created" not in result.output
    assert PASSPORT_TEXT not in result.output


@pytest.mark.parametrize(
    ("support_relation", "expected_decision", "expected_status"),
    [
        (
            "abstained",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_ABSTAINED,
            "abstained",
        ),
        (
            "absent",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT,
            "non-support",
        ),
        (
            "scope_mismatch",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT,
            "non-support",
        ),
        (
            "currentness_mismatch",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
            "challenge-recommended",
        ),
        (
            "contradicts",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
            "challenge-recommended",
        ),
        (
            "missing_qualifier",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT,
            "non-support",
        ),
        (
            "weak_or_overclaim_risk",
            dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_CHALLENGE_RECOMMENDED,
            "challenge-recommended",
        ),
    ],
)
def test_abstention_and_non_support_relations_fail_closed(
    tmp_path: Path,
    support_relation: str,
    expected_decision: str,
    expected_status: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_with_payload(repo_root, _assessment_payload(support_relation))

    assert result.decision == expected_decision
    assert result.payload["dprime_status"]["assessment_status"] == expected_status
    assert result.payload["dprime_status"]["objects_created"][
        "validated_support_proposal"
    ] is False
    assert result.payload["dprime_status"]["objects_created"]["semantic_observation"] is False
    assert result.payload["dprime_status"]["objects_created"]["component_coverage"] is False


def test_same_lane_unrelated_official_text_does_not_create_support(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text=UNRELATED_SAME_LANE_TEXT,
    )

    result = _run_with_payload(repo_root, _assessment_payload("absent"))

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_ASSESSMENT_NON_SUPPORT
    assert result.payload["dprime_status"]["objects_created"][
        "validated_support_proposal"
    ] is False
    assert result.payload["dprime_status"]["objects_created"]["semantic_observation"] is False
    assert result.payload["dprime_status"]["objects_created"]["component_coverage"] is False
    assert UNRELATED_SAME_LANE_TEXT not in result.output


def test_custody_lineage_only_rationale_fails_closed(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    payload["evidential_adequacy_notes"] = (
        "The custody lineage, URL, domain, snippet, and source class look right."
    )

    result = _run_with_payload(repo_root, payload)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert "D-prime assessment status: invalid" in result.output
    assert result.payload["dprime_status"]["objects_created"][
        "evidence_relative_support_assessment"
    ] is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload["answer_component_claim"].update(
            {"component_id": "component:wrong"}
        ),
        lambda payload: payload.update(
            {"currentness_check": {"status": "wrong_effective_date"}}
        ),
        lambda payload: payload.update(
            {
                "support_relation": "weak_or_overclaim_risk",
                "contradiction_check": {"status": "contradicts"},
                "challenge_recommended": True,
                "non_support_reason_when_not_direct": "fake contradiction",
            }
        ),
    ],
)
def test_wrong_component_currentness_and_contradiction_fail_closed(
    tmp_path: Path,
    mutator: Callable[[dict[str, Any]], object],
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    mutator(payload)

    result = _run_with_payload(repo_root, payload)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert result.payload["dprime_status"]["assessment_status"] == "invalid"
    assert result.payload["dprime_status"]["objects_created"][
        "validated_support_proposal"
    ] is False


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "raw_prompt",
        "prompt",
        "raw_model_response",
        "model_response",
        "provider_payload",
        "raw_page_text",
        "raw_html",
        "headers",
        "cookies",
        "secret",
        "api_key",
        "bounded_text",
        "unbounded_text",
    ],
)
def test_raw_private_output_material_fails_closed(
    tmp_path: Path,
    forbidden_field: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    payload[forbidden_field] = "forbidden"

    result = _run_with_payload(repo_root, payload)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert forbidden_field not in result.output
    assert result.payload["dprime_status"]["objects_created"][
        "evidence_relative_support_assessment"
    ] is False


def test_prompt_and_model_response_are_not_retained_or_printed(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    captured: dict[str, str] = {}

    def fake_review(prompt: str, **_kwargs: Any) -> dict[str, Any]:
        captured["prompt"] = prompt
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )

    assert captured["prompt"]
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["raw_prompt_retained"] is False
    assert dprime_status["raw_model_response_retained"] is False
    assert "raw_prompt" not in result.output
    assert "raw_model_response" not in result.output
    assert PASSPORT_TEXT not in result.output


def test_old_retained_support_consumer_not_reached_with_injected_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    def fail_consumer(**_kwargs: Any) -> Any:
        raise AssertionError("old retained support consumer must not be reached")

    monkeypatch.setattr(
        semantic_status,
        "build_retained_custody_semantic_coverage",
        fail_consumer,
    )

    result = _run_with_payload(repo_root, _assessment_payload())

    assert result.decision == (
        dprime.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
    )
    assert (
        "D-prime proposal validation status: "
        f"{dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED}"
    ) in result.output
    assert (
        "Analyst support proposal status: "
        f"{dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED}"
    ) in result.output


def test_bounded_evidence_window_count_mismatch_fails_closed(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    inputs = _model_review_input_args(repo_root)
    reference = inputs["fetch_read_content_packet"]["reference_records"][0]
    reference["bounded_character_count"] += 1

    with pytest.raises(Exception, match="count mismatch"):
        build_dprime_model_review_input_packet(**inputs)


def test_model_review_modules_avoid_live_provider_and_ag_script_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    for path in (MODEL_REVIEW_MODULE, MODEL_REVIEW_PROMPT_MODULE):
        imported = _imports(path)
        assert imported.isdisjoint(forbidden_imports)
        assert not any(name == "scripts" or name.startswith("scripts.") for name in imported)


def test_cli_output_hygiene_excludes_private_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_with_payload(repo_root, _assessment_payload())

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


def _run_with_payload(repo_root: Path, payload: dict[str, Any]) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )


def _license() -> DPrimeModelReviewLicense:
    return DPrimeModelReviewLicense(enabled=True)


def _real_license() -> DPrimeModelReviewLicense:
    return DPrimeModelReviewLicense(
        license_id="fixture-license:dprime-real-model-review-adapter-contract-01",
        enabled=True,
        test_only=False,
        callable_kind="real_one_shot",
        one_shot_adapter_ref=ADAPTER_REF,
    )


def _approved_fixture_boundary() -> dict[str, Any]:
    return {
        "boundary_id": "dprime-one-shot-provider-boundary:fixture-approval-ref",
        "phase": provider_boundary.DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
        "enabled": True,
        "default_disabled": False,
        "test_only": True,
        "provider_model_selection_status": "approval_ref_present",
        "provider_model_approval_ref": (
            "fixture-approval-ref:dprime-one-shot-provider-boundary-01"
        ),
        "max_provider_attempts": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "raw_prompt_retention": False,
        "raw_model_response_retention": False,
        "provider_payload_retention": False,
        "real_call_authorized": True,
        "call_count": 0,
        "provider_switching_allowed": False,
        "closed_surface_flags": provider_boundary.default_closed_surface_flags(),
    }


def _approved_real_protocol_boundary() -> dict[str, Any]:
    boundary = _approved_fixture_boundary()
    boundary.update(
        {
            "boundary_id": (
                "dprime-one-shot-provider-boundary:fixture-real-protocol-ref"
            ),
            "test_only": False,
            "one_shot_adapter_proven": True,
            "one_shot_adapter_ref": ADAPTER_REF,
        }
    )
    return boundary


def _assessment_payload(support_relation: str = "directly_supports") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_proposition": (
            "The structured proposition states the adult passport book renewal "
            "by mail fee as $130 for the current fee component."
        ),
        "answer_component_claim": {
            "component_id": PASSPORT_COMPONENT_ID,
            "claim": "Adult U.S. passport book renewal by mail fee is $130.",
        },
        "support_relation": support_relation,
        "required_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "observed_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The structured proposition maps to the same component and current "
            "fee claim."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "closed_surface_flags": _closed_surface_flags(),
    }
    _apply_relation_shape(payload, support_relation=support_relation)
    return payload


def _apply_relation_shape(
    payload: dict[str, Any],
    *,
    support_relation: str,
) -> None:
    if support_relation == "abstained":
        payload["producer_abstained"] = True
        payload["observed_qualifiers"] = []
        payload["non_support_reason_when_not_direct"] = "fake producer abstained"
    elif support_relation == "absent":
        payload["observed_qualifiers"] = []
        payload["non_support_reason_when_not_direct"] = "fake proposition absent"
    elif support_relation == "scope_mismatch":
        payload["scope_check"] = {"status": "scope_mismatch"}
        payload["non_support_reason_when_not_direct"] = "fake scope mismatch"
    elif support_relation == "currentness_mismatch":
        payload["currentness_check"] = {"status": "wrong_effective_date"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fake currentness mismatch"
    elif support_relation == "contradicts":
        payload["contradiction_check"] = {"status": "contradicts"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fake contradiction"
    elif support_relation == "missing_qualifier":
        payload["missing_qualifiers"] = ["renewal by mail"]
        payload["non_support_reason_when_not_direct"] = "fake qualifier missing"
    elif support_relation == "weak_or_overclaim_risk":
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fake overclaim risk"


def _closed_surface_flags() -> dict[str, bool]:
    return {
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
    }


def _model_review_input_args(repo_root: Path) -> dict[str, Any]:
    status = semantic_status.build_live_citation_source_obligation_readiness_status(
        query=QUERY,
        repo_root=repo_root,
    )
    fetch_packet = json.loads(
        (
            repo_root
            / "output"
            / "ag_live_source_survival_fetch_read_01"
            / "fetch_read_content_packet.json"
        ).read_text(encoding="utf-8")
    )
    readiness_payload = status.payload
    preflight = semantic_status.build_evidence_frame_preflight(
        fetch_read_content_packet=fetch_packet,
        source_evidence_admission_ref=readiness_payload[
            "source_evidence_admission_ref"
        ],
        citation_source_obligation_readiness_ref=readiness_payload[
            "citation_source_obligation_readiness_ref"
        ],
        component_ref=readiness_payload["component_ref"],
        source_obligation_ref=readiness_payload["source_obligation_ref"],
    )
    dprime_status = dprime.build_dprime_status_payload(
        evidence_frame_preflight=preflight
    )
    return {
        "evidence_frame_preflight": preflight.to_dict(),
        "fetch_read_content_packet": fetch_packet,
        "source_evidence_admission_ref": readiness_payload[
            "source_evidence_admission_ref"
        ],
        "citation_source_obligation_readiness_ref": readiness_payload[
            "citation_source_obligation_readiness_ref"
        ],
        "component_ref": readiness_payload["component_ref"],
        "source_obligation_ref": readiness_payload["source_obligation_ref"],
        "negative_control_profile_ref": dprime_status.negative_control_profile_ref,
        "assessment_validator_status": dprime_status.assessment_validator_status,
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
