"""PRODUCT-PATH-REGRESSION: completed D-prime support bundle.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_evidence_support_bundle_runtime
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path is used with retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep as the regression guard for D-prime SemanticObservation ->
ComponentCoverage -> source-obligation authority -> citation-source handoff
authority -> SufficiencyReadiness not licensed.
Why this is not a shadow product path: it invokes the product status builder and
RunKernel-owned reducers, not a detached packet path.
Forbidden interpretation: this does not create SufficiencyReadiness, FAP,
Author/answer text, citation rendering, product correctness, or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import core.dprime_evidence_support_bundle_runtime as dprime_bundle
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


def test_product_status_completes_support_bundle_then_blocks_readiness(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == (
        dprime_bundle.BLOCKED_DPRIME_SUFFICIENCY_READINESS_NOT_LICENSED
    )
    assert result.payload["next_blocked_surface"] == "SufficiencyReadiness"
    assert result.payload["component_coverage_ref"]["status"] == "bound"
    source_authority = result.payload["source_obligation_authority_ref"]
    citation_authority = result.payload["citation_eligibility_authority_ref"]
    assert source_authority["owner"] == "RunKernel.DPrimeSourceObligationAuthority"
    assert source_authority["canonical_state"] is True
    assert source_authority["authority_consumed"] is True
    assert source_authority["retained_ids_alone_are_authority"] is False
    assert citation_authority["owner"] == (
        "RunKernel.DPrimeCitationSourceHandoffAuthority"
    )
    assert citation_authority["canonical_state"] is True
    assert citation_authority["authority_consumed"] is True
    assert citation_authority["citation_source_handoff_consumed"] is True
    assert citation_authority["citations_rendered"] is False

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["support_bundle_completed"] is True
    assert dprime_status["source_obligation_authority_consumed"] is True
    assert (
        dprime_status["citation_eligibility_or_source_handoff_authority_consumed"]
        is True
    )
    assert dprime_status["objects_created"]["sufficiency_readiness"] is False
    assert dprime_status["objects_created"]["final_answer_packet"] is False
    assert dprime_status["objects_created"]["author_answer"] is False
    assert result.payload["detached_posture_status_packet_treated_as_authority"] is False


def test_support_bundle_completion_output_hygiene_excludes_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized = json.dumps(result.payload, sort_keys=True).casefold()

    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT.casefold(),
        "raw prompt",
        "raw model response",
        "provider payload",
        "finalanswerpacket",
        "author prose",
        "answer text:",
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output.casefold()
        assert forbidden not in serialized


def test_support_bundle_completion_is_product_status_consumed() -> None:
    bundle_runtime = Path("core/dprime_evidence_support_bundle_runtime.py").read_text(
        encoding="utf-8"
    )
    status_runtime = Path("proplex/live_semantic_coverage_status.py").read_text(
        encoding="utf-8"
    )

    assert "consume_dprime_source_obligation_and_citation_authority(" in bundle_runtime
    assert "build_dprime_evidence_support_bundle(" in status_runtime
    assert "support_bundle.to_status_overlay()" in status_runtime


def _run_product_status_with_assessment(
    repo_root: Path,
    payload: dict[str, Any],
) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
    )
