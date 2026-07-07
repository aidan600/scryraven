"""PRODUCT-PATH-REGRESSION: D-prime evidence support bundle feeds answer path.

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
-> citation-source handoff authority -> single-lane answer path.
Why this is not a shadow product path: it invokes the product status builder and
RunKernel-owned SemanticObservation/ComponentCoverage reducers, not a detached
packet path.
Forbidden interpretation: ComponentCoverage-only is not PASS; retained
source-obligation ids and citation/source-obligation readiness posture are not
authority until consumed by the D-prime RunKernel authority surfaces. This is
not product correctness or a live call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import core.dprime_runkernel_admission_runtime as rk_dprime
import proplex.live_semantic_coverage_status as semantic_status_runtime
from core.dprime_analyst_relation_intake_runtime import (
    build_dprime_analyst_relation_intake,
    relation_intake_ref,
)
from proplex.live_semantic_coverage_status import (
    BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH,
    build_live_semantic_coverage_status,
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


def test_product_status_consumes_support_bundle_then_answer_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == "PASS"
    coverage = result.payload["component_coverage_ref"]
    assert coverage["status"] == "bound"
    assert coverage["coverage_ref"] != "unavailable"
    assert coverage["coverage_state"] == "supported_with_caveats"
    assert coverage["semantic_support_status"] == "supported"
    assert coverage["source_obligation_status"] == "unknown"
    assert result.payload["next_blocked_surface"] is None

    dprime_status = result.payload["dprime_status"]
    assert dprime_status["objects_created"]["semantic_observation"] is True
    assert dprime_status["objects_created"]["component_coverage"] is True
    assert dprime_status["source_obligation_authority_consumed"] is True
    assert (
        dprime_status["citation_eligibility_or_source_handoff_authority_consumed"]
        is True
    )
    assert dprime_status["support_bundle_completed"] is True
    assert dprime_status["objects_created"]["sufficiency_readiness"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is True
    assert dprime_status["objects_created"]["author_answer"] is True
    assert dprime_status["objects_created"]["citation_source_display"] is True
    assert dprime_status["component_coverage_only_treated_as_pass"] is False
    answer_path = result.payload["dprime_answer_path_ref"]
    assert answer_path["sufficiency_readiness_status"] == "full_answer_ready"
    assert answer_path["final_answer_packet_status"] == "full_answer_packet_ready"
    assert answer_path["author_answer_status"] == "full_answer_prose_created"
    assert answer_path["citation_source_display_status"] == "created"


def test_workbench_dprime_candidate_routes_into_relation_intake() -> None:
    reference_b = _retained_reference(
        candidate_id="candidate:adjacent-context",
        reference_id="reference:adjacent-context",
        title="Official Reduced Fee Context",
        url="https://example.test/reduced-fee",
        bounded_text="Official adjacent context lists reduced-fee tokens.",
    )
    reference_a = _retained_reference(
        candidate_id="candidate:strict-answer",
        reference_id="reference:strict-answer",
        title="Official Filing Fee Schedule",
        url="https://example.test/filing-fee",
        bounded_text="Official filing fee schedule lists the direct paper fee.",
    )
    fetch_packet = {
        "packet_id": "fetch-read-content-packet:test",
        "packet_digest": "fetch-read-content-packet-digest:test",
        "current_answer_contract_digest": "contract-digest:test",
        "reference_records": [reference_b, reference_a],
    }
    workbench_dossier = _workbench_dossier(reference_a)

    routed = semantic_status_runtime._dprime_candidate_handoff_inputs(
        fetch_read_content_packet=fetch_packet,
        admission_ref=_admission_ref(reference_b),
        readiness_ref=_readiness_ref(reference_b),
        component_ref=_component_ref(reference_b),
        source_obligation_ref=_source_obligation_ref(reference_b),
        workbench_dprime_dossier=workbench_dossier,
    )

    assert routed["status"] == "routed"
    assert routed["route_status"] == "workbench_candidate_routed_to_dprime_intake"
    assert routed["routed_from_candidate_ref"]["candidate_id"] == (
        "candidate:adjacent-context"
    )
    assert routed["routed_to_candidate_ref"]["candidate_id"] == (
        "candidate:strict-answer"
    )
    relation = build_dprime_analyst_relation_intake(
        query=QUERY,
        fetch_read_content_packet=fetch_packet,
        source_evidence_admission_ref=routed["admission_ref"],
        citation_source_obligation_readiness_ref=routed["readiness_ref"],
        component_ref=routed["component_ref"],
        source_obligation_ref=routed["source_obligation_ref"],
    )
    relation_ref = relation_intake_ref(relation)
    assert relation_ref["evidence_candidate_id"] == "candidate:strict-answer"
    assert relation_ref["evidence_reference_id"] == "reference:strict-answer"

    strict_only_dossier = {
        key: value
        for key, value in workbench_dossier.items()
        if key != "dprime_review_candidate_ref"
    }
    strict_only_routed = semantic_status_runtime._dprime_candidate_handoff_inputs(
        fetch_read_content_packet=fetch_packet,
        admission_ref=_admission_ref(reference_b),
        readiness_ref=_readiness_ref(reference_b),
        component_ref=_component_ref(reference_b),
        source_obligation_ref=_source_obligation_ref(reference_b),
        workbench_dprime_dossier=strict_only_dossier,
    )
    assert strict_only_routed["status"] == "routed"
    assert strict_only_routed["routed_to_candidate_ref"]["candidate_id"] == (
        "candidate:strict-answer"
    )


def test_candidate_handoff_uses_id_before_title_or_url() -> None:
    expected = {
        "candidate_id": "candidate:strict",
        "title": "Same Official Title",
        "url": "https://example.test/same",
    }
    actual = {
        "candidate_id": "candidate:context",
        "title": "Same Official Title",
        "url": "https://example.test/same",
    }

    assert not semantic_status_runtime._candidate_identity_matches(
        expected,
        actual,
    )
    assert semantic_status_runtime._candidate_identity_matches(
        {"candidate_digest": "candidate-digest:strict"},
        {"candidate_digest": "candidate-digest:strict"},
    )


def test_missing_workbench_dprime_candidate_blocks_before_answer_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    missing_candidate = {
        "candidate_id": "candidate:workbench-strict-missing",
        "candidate_digest": "candidate-digest:workbench-strict-missing",
        "title": "Workbench Strict Filing Fee Candidate",
        "url": "https://example.test/workbench-strict",
    }

    def fail_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("D-prime model review opened after handoff mismatch")

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fail_review,
        workbench_dprime_dossier=_workbench_dossier(missing_candidate),
    )

    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_CURRENT_SOURCE_RECORD_DPRIME_CANDIDATE_HANDOFF_MISMATCH
    )
    handoff = result.payload["dprime_candidate_handoff_integrity_ref"]
    assert handoff["match_status"] == "mismatch"
    assert handoff["candidate_identity_match"] is False
    assert handoff["expected_workbench_candidate_ref"]["candidate_id"] == (
        "candidate:workbench-strict-missing"
    )
    assert handoff["source_evidence_admission_candidate_ref"]["candidate_id"] == (
        "search-result-candidate:adult-passport-fee"
    )
    assert handoff["mismatch_surface"] == "D-prime relation intake"
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert dprime_status["objects_created"]["sufficiency_readiness"] is False
    assert dprime_status["objects_created"]["final_answer_packet"] is False
    assert dprime_status["objects_created"]["author_answer"] is False
    assert dprime_status["objects_created"]["citation_source_display"] is False
    assert result.payload["component_coverage_ref"]["status"] == "not reached"
    assert result.payload["dprime_answer_path_ref"] == {}
    assert "full_answer_ready" not in json.dumps(result.payload, sort_keys=True)
    assert "safe_answer_claim_text" not in json.dumps(result.payload, sort_keys=True)
    assert result.payload["raw_private_retention"] is False


def test_product_status_exposes_matching_handoff_refs_on_pass(
    tmp_path: Path,
) -> None:
    repo_root, candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(),
        workbench_dprime_dossier=_workbench_dossier(candidate),
    )

    assert result.decision == "PASS"
    handoff = result.payload["dprime_candidate_handoff_integrity_ref"]
    assert handoff["match_status"] == "match"
    assert handoff["candidate_identity_match"] is True
    assert handoff["expected_workbench_candidate_ref"]["candidate_id"] == (
        candidate["candidate_id"]
    )
    assert handoff["dprime_intake_actual_candidate_ref"]["candidate_id"] == (
        candidate["candidate_id"]
    )
    assert handoff["selected_source_candidate_ref"]["candidate_id"] == (
        candidate["candidate_id"]
    )
    assert handoff["source_display_candidate_ref"]["candidate_id"] == (
        candidate["candidate_id"]
    )
    assert result.payload["dprime_status"]["objects_created"][
        "final_answer_packet"
    ] is True
    assert result.payload["dprime_status"]["objects_created"]["author_answer"] is True


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
    assert result.payload["dprime_answer_path_ref"]["citation_source_display"][
        "citations_rendered"
    ] is True
    assert citation_authority["citation_formatter_invoked"] is False
    assert result.payload["component_coverage_only_treated_as_pass"] is False
    assert result.payload["detached_posture_status_packet_treated_as_authority"] is False
    assert result.return_code == 0


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
        "product correctness claimed: true",
    ):
        assert forbidden not in result.output.casefold()
        assert forbidden not in serialized.casefold()


def _run_product_status_with_assessment(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    decision_status: str = rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    workbench_dprime_dossier: dict[str, Any] | None = None,
) -> Any:
    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=fake_review,
        dprime_run_kernel_admission_decision_status=decision_status,
        workbench_dprime_dossier=workbench_dprime_dossier,
    )


def _workbench_dossier(candidate_ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "test_workbench_dossier_v1",
        "dossier_id": "workbench-dossier:test",
        "dossier_digest": "workbench-dossier-digest:test",
        "dprime_review_candidate_ref": {
            "candidate_id": candidate_ref.get("candidate_id"),
            "candidate_digest": candidate_ref.get("candidate_digest"),
            "title": candidate_ref.get("title") or candidate_ref.get("content_title"),
            "url": candidate_ref.get("url") or candidate_ref.get("resolved_url"),
            "selected_for_dprime_review": True,
            "strict_answer_support_candidate": True,
        },
        "strict_answer_support_candidate_refs": [
            {
                "candidate_id": candidate_ref.get("candidate_id"),
                "candidate_digest": candidate_ref.get("candidate_digest"),
                "title": candidate_ref.get("title")
                or candidate_ref.get("content_title"),
                "url": candidate_ref.get("url") or candidate_ref.get("resolved_url"),
                "strict_answer_support_candidate": True,
            }
        ],
        "strict_answer_support_candidate_count": 1,
        "raw_private_retention": False,
    }


def _retained_reference(
    *,
    candidate_id: str,
    reference_id: str,
    title: str,
    url: str,
    bounded_text: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "candidate_digest": f"candidate-digest:{candidate_id}",
        "reference_id": reference_id,
        "reference_digest": f"reference-digest:{reference_id}",
        "fetch_read_status": "readable",
        "resolved_url": url,
        "resolved_domain": "example.test",
        "content_title": title,
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "excerpt_digest": f"excerpt-digest:{reference_id}",
        "component_id": "component:test-fee",
        "current_answer_contract_digest": "contract-digest:test",
        "source_obligation_candidate_ids": ["source-obligation:test-fee"],
    }


def _admission_ref(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": reference["candidate_id"],
        "candidate_digest": reference["candidate_digest"],
        "reference_id": reference["reference_id"],
        "reference_digest": reference["reference_digest"],
        "status": "admitted",
    }


def _readiness_ref(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "posture": "not_yet_semantically_supported",
        "source_obligation_candidate_ids": list(
            reference["source_obligation_candidate_ids"]
        ),
    }


def _component_ref(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "component_id": reference["component_id"],
        "current_answer_contract_digest": reference[
            "current_answer_contract_digest"
        ],
        "component_coverage_bound": False,
    }


def _source_obligation_ref(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_obligation_candidate_ids": list(
            reference["source_obligation_candidate_ids"]
        ),
        "satisfaction_claimed": False,
    }
