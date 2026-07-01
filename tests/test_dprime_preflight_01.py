"""PRODUCT-PATH-REGRESSION: D-prime preflight product consumption.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_evidence_frame_preflight
Why ordinary product-path work cannot be done directly: not applicable; the
ordinary dry-run status builder consumes the preflight and this test uses
fixture-sized retained artifacts to avoid private local output.
Integration deadline: current phase.
Exit condition: keep while D-prime preflight is consumed before model review.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned preflight module, not a standalone script.
Forbidden interpretation: this is not model review, support assessment,
support proposal validation, RunKernel admission, SemanticObservation admission,
ComponentCoverage binding, citation eligibility, answer text, source-obligation
satisfaction, or product correctness.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest

import core.dprime_support_proposal_schema as dprime
import proplex.live_semantic_coverage_status as semantic_status
from core.dprime_evidence_frame_preflight import build_evidence_frame_preflight
from proplex.live_citation_source_obligation_readiness_status import (
    build_live_citation_source_obligation_readiness_status,
)
from proplex.live_semantic_coverage_status import (
    build_live_semantic_coverage_status,
    output_hygiene_passes,
)
from proplex.live_source_evidence_admission_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
    PASS_DECISION,
)
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    UNRELATED_SAME_LANE_TEXT,
    _passport_retained_repo,
)


def test_preflight_builder_happy_path_creates_frame_without_support(
    tmp_path: Path,
) -> None:
    inputs = _preflight_inputs(tmp_path)

    preflight = build_evidence_frame_preflight(**inputs)

    payload = preflight.to_dict()
    frame = payload["frame_ref"]
    assert payload["preflight_status"] == "passed"
    assert frame["frame_digest"]
    assert frame["fetch_read_packet_ref"]["packet_digest"]
    assert frame["source_evidence_custody_ref"]["reference_digest"]
    assert frame["content_reference_ref"]["bounded_content_digest"]
    assert frame["component_binding_ref"]["component_id"]
    assert frame["source_obligation_lane_ref"]["source_obligation_candidate_ids"]
    assert frame["component_binding_ref"]["current_contract_digest"]
    assert frame["selector_ref"]["selector_kind"] == "bounded_digest_count_surrogate"
    assert frame["model_browse_allowed"] is False
    assert payload["semantic_support_created"] is False
    assert payload["semantic_observation_created"] is False
    assert payload["component_coverage_created"] is False

    serialized = json.dumps(payload, sort_keys=True).casefold()
    for forbidden in (
        "support_relation",
        "evidencerelativesupportassessment",
        "validatedsupportproposal",
        "run_kernel_support_proposal_admission_request",
        "bounded_text",
        "answer_text",
        "finalanswerpacket",
        "author prose",
    ):
        assert forbidden not in serialized


def test_ordinary_cli_consumes_preflight_and_blocks_at_model_review(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert result.return_code == 2
    assert "D-prime preflight status: passed" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert (
        f"decision: {dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED}"
        in result.output
    )
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["objects_created"] == {
        "evidence_frame_preflight": True,
        "evidence_relative_support_assessment": False,
        "validated_support_proposal": False,
        "run_kernel_support_proposal_admission_request": False,
        "semantic_observation": False,
        "component_coverage": False,
    }


def test_old_retained_support_consumer_not_reached_after_preflight_pass(
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

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "D-prime preflight status: passed" in result.output
    assert "Analyst support proposal status: not reached" in result.output


def test_same_lane_unrelated_text_preflight_passes_but_creates_no_support(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(
        tmp_path,
        bounded_text=UNRELATED_SAME_LANE_TEXT,
    )

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["preflight_status"] == "passed"
    assert dprime_status["objects_created"]["evidence_frame_preflight"] is True
    assert dprime_status["objects_created"]["evidence_relative_support_assessment"] is False
    assert dprime_status["objects_created"]["validated_support_proposal"] is False
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert "Analyst support proposal ref/digest: unavailable" in result.output
    assert "SemanticObservation id/ref/digest: unavailable" in result.output
    assert "ComponentCoverage id/ref/digest: unavailable" in result.output
    assert UNRELATED_SAME_LANE_TEXT not in result.output


@pytest.mark.parametrize(
    ("mutator", "expected_detail"),
    [
        (
            lambda inputs: inputs["fetch_read_content_packet"]["reference_records"][
                0
            ].pop("bounded_text"),
            "bounded sanitized content is missing",
        ),
        (
            lambda inputs: inputs["component_ref"].update(
                {"component_id": "component:wrong"}
            ),
            "component ref does not match retained content component",
        ),
        (
            lambda inputs: inputs["source_obligation_ref"].update(
                {"source_obligation_candidate_ids": ["obligation:wrong"]}
            ),
            "source-obligation ref does not match retained content lane",
        ),
        (
            lambda inputs: inputs["component_ref"].update(
                {"current_answer_contract_digest": "wrong-contract-digest"}
            ),
            "current answer contract digest/ref mismatches component ref",
        ),
        (
            lambda inputs: inputs["fetch_read_content_packet"]["reference_records"][
                0
            ].update({"raw_page_content_retained": True}),
            "raw/private retained flag true",
        ),
    ],
)
def test_preflight_failures_block_before_downstream_objects(
    tmp_path: Path,
    mutator: Callable[[dict[str, Any]], object],
    expected_detail: str,
) -> None:
    inputs = _preflight_inputs(tmp_path)
    mutator(inputs)

    preflight = build_evidence_frame_preflight(**inputs)
    status = dprime.build_dprime_status_payload(evidence_frame_preflight=preflight)
    payload = status.to_dict()

    assert status.decision == dprime.BLOCKED_DPRIME_PREFLIGHT_FAILED
    assert preflight.preflight_status == "failed"
    assert expected_detail in status.blocker_detail
    assert payload["objects_created"]["evidence_relative_support_assessment"] is False
    assert payload["objects_created"]["validated_support_proposal"] is False
    assert payload["objects_created"]["run_kernel_support_proposal_admission_request"] is False
    assert payload["objects_created"]["semantic_observation"] is False
    assert payload["objects_created"]["component_coverage"] is False


def test_cli_output_hygiene_excludes_raw_private_and_answer_material(
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


def _preflight_inputs(tmp_path: Path) -> dict[str, Any]:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    readiness = build_live_citation_source_obligation_readiness_status(
        query=QUERY,
        repo_root=repo_root,
    )
    assert readiness.decision == PASS_DECISION
    fetch_packet = json.loads(
        (
            repo_root / FETCH_READ_ARTIFACT_DIR / FETCH_READ_CONTENT_PACKET_NAME
        ).read_text(encoding="utf-8")
    )
    payload = readiness.payload
    return {
        "fetch_read_content_packet": copy.deepcopy(fetch_packet),
        "source_evidence_admission_ref": copy.deepcopy(
            payload["source_evidence_admission_ref"]
        ),
        "citation_source_obligation_readiness_ref": copy.deepcopy(
            payload["citation_source_obligation_readiness_ref"]
        ),
        "component_ref": copy.deepcopy(payload["component_ref"]),
        "source_obligation_ref": copy.deepcopy(payload["source_obligation_ref"]),
    }
