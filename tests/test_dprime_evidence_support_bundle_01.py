"""PRODUCT-PATH-REGRESSION: D-prime evidence support-bundle Outcome A.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_evidence_support_bundle_runtime
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep as the regression guard for admitted D-prime
SemanticObservation -> ComponentCoverage binding -> source-obligation authority
-> citation-source handoff authority -> SufficiencyReadiness not licensed.
Why this is not a shadow product path: it invokes the product status builder and
RunKernel-owned SemanticObservation/ComponentCoverage reducers, not a detached
packet path.
Forbidden interpretation: ComponentCoverage-only is not PASS; retained
source-obligation ids and citation/source-obligation readiness posture are not
authority until consumed by the D-prime RunKernel authority surfaces. This is
not SufficiencyReadiness, FinalAnswerPacket, Author/answer text, product
correctness, citation rendering, or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import core.dprime_evidence_support_bundle_runtime as dprime_bundle
import core.dprime_runkernel_admission_runtime as rk_dprime
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


def test_product_status_consumes_support_bundle_then_blocks_sufficiency(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == (
        dprime_bundle.BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED
    )
    coverage = result.payload["component_coverage_ref"]
    assert coverage["status"] == "bound"
    assert coverage["coverage_ref"] != "unavailable"
    assert coverage["coverage_state"] == "supported_with_caveats"
    assert coverage["semantic_support_status"] == "supported"
    assert coverage["source_obligation_status"] == "unknown"
    assert result.payload["next_blocked_surface"] == "SufficiencyReadiness"

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["objects_created"]["semantic_observation"] is True
    assert dprime_status["objects_created"]["component_coverage"] is True
    assert dprime_status["source_obligation_authority_consumed"] is True
    assert (
        dprime_status["citation_eligibility_or_source_handoff_authority_consumed"]
        is True
    )
    assert dprime_status["support_bundle_completed"] is True
    assert dprime_status["objects_created"]["sufficiency_readiness"] is False
    assert dprime_status["objects_created"]["final_answer_packet"] is False
    assert dprime_status["objects_created"]["author_answer"] is False
    assert dprime_status["component_coverage_only_treated_as_pass"] is False


def test_source_and_citation_authority_are_consumed_not_detached(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    source_authority = result.payload["source_obligation_authority_ref"]
    citation_authority = result.payload["citation_eligibility_authority_ref"]
    assert source_authority["status"] == "consumed"
    assert source_authority["blocker"] is None
    assert source_authority["authority_consumed"] is True
    assert source_authority["satisfaction_claimed"] is True
    assert source_authority["retained_ids_consumed_as_lineage"] is True
    assert source_authority["retained_ids_alone_are_authority"] is False
    assert source_authority["component_coverage_only_treated_as_pass"] is False
    assert citation_authority["status"] == "consumed"
    assert citation_authority["blocker"] is None
    assert citation_authority["authority_consumed"] is True
    assert citation_authority["citation_eligibility_authority_consumed"] is True
    assert citation_authority["citation_source_handoff_consumed"] is True
    assert citation_authority["citations_rendered"] is False
    assert citation_authority["citation_formatter_invoked"] is False
    assert result.payload["component_coverage_only_treated_as_pass"] is False
    assert result.payload["detached_posture_status_packet_treated_as_authority"] is False
    assert result.return_code == 2


def test_rejected_or_challenged_decisions_still_do_not_bind_coverage(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    for decision_status in (
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED,
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    ):
        result = _run_product_status_with_assessment(
            repo_root,
            _assessment_payload(),
            decision_status=decision_status,
        )

        dprime_status = result.payload["dprime_status"]
        assert dprime_status["objects_created"]["semantic_observation"] is False
        assert dprime_status["objects_created"]["component_coverage"] is False
        assert dprime_status.get("source_obligation_authority_consumed") is not True
        assert (
            dprime_status.get(
                "citation_eligibility_or_source_handoff_authority_consumed"
            )
            is not True
        )
        assert result.payload["component_coverage_ref"]["status"] == "unavailable"


def test_support_bundle_output_hygiene_excludes_downstream_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized = json.dumps(result.payload, sort_keys=True)

    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT,
        "raw prompt",
        "raw model response",
        "provider payload",
        "citation eligibility claimed: true",
        "source-obligation satisfaction claimed: true",
        "author prose:",
        "answer text:",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output.casefold()
        assert forbidden not in serialized.casefold()


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
