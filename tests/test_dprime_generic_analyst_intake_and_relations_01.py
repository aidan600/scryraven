"""PRODUCT-PATH-REGRESSION: generic D-prime Analyst relation intake.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_analyst_relation_intake_runtime
Why ordinary product-path work cannot be done directly: live/model/provider/
search/fetch/read/retrieval calls are closed, so the ordinary status path uses
retained offline artifacts and injected fake D-prime review callables.
Integration deadline: current phase.
Exit condition: keep as the regression guard for generic single-relation intake
being consumed by the D-prime support bundle, answer path, and follow-up re-entry.
Why this is not a shadow product path: it invokes the ordinary product status
builder and existing RunKernel/product reducers, not a detached intake helper.
Forbidden interpretation: generic relation intake alone is not support, answer
text, source-obligation authority, citation authority, live validation, product
correctness, multi-source synthesis, or Scrutineer/Economist/Specialist review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_COMPONENT_ID,
    PASSPORT_OBLIGATION_ID,
    PASSPORT_TEXT,
    PASSPORT_URL,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import _license

GENERIC_QUERY = "What is the filing fee for Example County small-claims case type?"
GENERIC_COMPONENT_ID = "component:example-county-small-claims-filing-fee"
GENERIC_OBLIGATION_ID = "obligation:example-county-official-fee-schedule"
GENERIC_TITLE = "Example County Fee Schedule"
GENERIC_DOMAIN = "example-county.invalid"
GENERIC_URL = "https://example-county.invalid/small-claims-fees"
GENERIC_TEXT = (
    "The Example County official fee schedule states that the small-claims "
    "filing fee for the example case type is $42."
)
GENERIC_FOLLOWUP_TEXT = (
    "The Example County updated fee schedule states the small-claims filing "
    "fee for the example case type is $42."
)


def test_generic_direct_relation_reaches_single_lane_answer_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
    )

    assert result.decision == "PASS", result.payload.get("blocker_detail")
    relation = result.payload["dprime_relation_intake_ref"]
    assert relation["status"] == "consumed"
    assert relation["component_id"] == GENERIC_COMPONENT_ID
    assert relation["component_label"] == "example county small claims filing fee"
    assert relation["source_obligation_candidate_ids"] == [GENERIC_OBLIGATION_ID]
    assert relation["single_lane_only"] is True
    assert relation["support_claimed"] is False
    assert relation["answer_created"] is False
    assert relation["source_obligation_authority_claimed"] is False
    assert relation["citation_authority_claimed"] is False
    assert relation["product_correctness_claimed"] is False
    assert relation["live_calls_run"] is False
    assert result.payload["generic_relation_intake_consumed_by_product_status"] is True

    dprime_status = result.payload["dprime_status"]
    preflight_relation = dprime_status["evidence_frame_preflight_ref"][
        "relation_intake_ref"
    ]
    assert preflight_relation["component_id"] == GENERIC_COMPONENT_ID
    assert preflight_relation["source_obligation_candidate_ids"] == [
        GENERIC_OBLIGATION_ID
    ]
    assert dprime_status["generic_relation_intake_ref"]["relation_intake_digest"]
    assert result.payload["component_ref"]["component_id"] == GENERIC_COMPONENT_ID
    assert result.payload["source_obligation_ref"][
        "source_obligation_candidate_ids"
    ] == [GENERIC_OBLIGATION_ID]
    assert result.payload["dprime_answer_path_ref"]["status"] == "consumed"
    assert result.payload["dprime_answer_path_ref"]["single_lane_only"] is True
    assert result.payload["answerability_correctness"] == "not claimed"
    assert "D-prime generic relation intake status: consumed" in result.output
    assert "D-prime generic relation single-lane only: true" in result.output
    _assert_no_passport_runtime_dependency(result)


def test_generic_followup_relation_reuses_ordinary_search_reentry(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_generic_followup_candidates(),
        dprime_followup_fetch_read_materials=_generic_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert result.decision == "PASS", result.payload.get("blocker_detail")
    relation = result.payload["dprime_relation_intake_ref"]
    assert relation["component_id"] == GENERIC_COMPONENT_ID
    assert relation["source_obligation_candidate_ids"] == [GENERIC_OBLIGATION_ID]
    followup = result.payload["dprime_followup_search_reentry_ref"]
    assert followup["followup_loop_owner"] == "RunKernel/product"
    assert followup["dprime_followup_need_owner"] == "D-prime"
    assert followup["ordinary_search_path_reused"] is True
    assert followup["followup_search_authorization_status"] == "consumed"
    assert followup["ordinary_search_planner_status"] == "consumed"
    assert followup["ordinary_search_executor_handoff_status"] == "consumed"
    assert followup["ordinary_live_search_validation_status"] == "consumed"
    assert followup["search_result_candidate_packet_status"] == "created"
    assert followup["fetch_read_content_packet_status"] == "created"
    assert followup["evidence_reentry_status"] == "consumed"
    assert followup["second_dprime_pass_status"] == "consumed"
    assert followup["second_pass_answer_path_status"] == "consumed"
    assert followup["provider_called"] is False
    assert followup["live_provider_called"] is False
    assert followup["live_search_called"] is False
    assert followup["fetch_read_executed"] is False
    assert followup["read_executed"] is False
    assert followup["retrieval_executed"] is False
    assert followup["product_correctness_claimed"] is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "consumed"
    _assert_no_passport_runtime_dependency(result)


def test_generic_intake_alone_is_not_pass(tmp_path: Path) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
    )

    assert result.decision != "PASS"
    assert result.payload["dprime_relation_intake_ref"]["status"] == "consumed"
    assert result.payload["dprime_relation_intake_ref"]["component_id"] == (
        GENERIC_COMPONENT_ID
    )
    assert result.payload["generic_relation_intake_consumed_by_product_status"] is True
    assert result.payload["dprime_status"]["objects_created"][
        "validated_support_proposal"
    ] is False
    assert result.payload["dprime_status"]["objects_created"][
        "semantic_observation"
    ] is False
    assert result.payload["dprime_status"]["objects_created"][
        "component_coverage"
    ] is False


def test_active_generic_dprime_runtime_files_do_not_require_passport_lane() -> None:
    root = Path(__file__).resolve().parents[1]
    active_runtime_files = [
        root / "core" / "dprime_analyst_relation_intake_runtime.py",
        root / "core" / "dprime_evidence_frame_preflight.py",
        root / "core" / "dprime_ordinary_contract_authority_runtime.py",
        root / "core" / "dprime_semantic_observation_materialization_runtime.py",
        root / "core" / "runkernel_followup_search_reentry_ordinary_search_runtime.py",
    ]
    forbidden = (
        PASSPORT_COMPONENT_ID,
        PASSPORT_OBLIGATION_ID,
        "searchreq:dprime-followup-reentry-current-source",
        "travel.state.gov",
        PASSPORT_URL,
        "$130",
    )

    for path in active_runtime_files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} still contains {token}"


def _generic_retained_repo(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    return _passport_retained_repo(
        tmp_path,
        bounded_text=GENERIC_TEXT,
        component_id=GENERIC_COMPONENT_ID,
        source_obligation_id=GENERIC_OBLIGATION_ID,
        title=GENERIC_TITLE,
        url=GENERIC_URL,
        domain=GENERIC_DOMAIN,
        candidate_id="search-result-candidate:example-county-small-claims-fee",
        candidate_digest="candidate-digest-example-county-small-claims-fee",
        snippet="Example County official fee schedule lists a $42 filing fee.",
        published_or_observed_date="2026-06-30",
    )


def _fake_review(support_relation: str) -> Any:
    payload = _generic_assessment_payload(support_relation)

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return fake_review


def _generic_assessment_payload(support_relation: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_proposition": (
            "The structured proposition states the Example County small-claims "
            "filing fee for the example case type as $42."
        ),
        "answer_component_claim": {
            "component_id": GENERIC_COMPONENT_ID,
            "claim": (
                "Example County small-claims filing fee for the example case type "
                "is $42."
            ),
        },
        "support_relation": support_relation,
        "required_qualifiers": [
            "Example County",
            "small-claims",
            "filing fee",
            "example case type",
        ],
        "observed_qualifiers": [
            "Example County",
            "small-claims",
            "filing fee",
            "example case type",
        ],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The structured proposition maps to the same generic component and "
            "fee claim."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "closed_surface_flags": _closed_surface_flags(),
    }
    if support_relation == "currentness_mismatch":
        payload["currentness_check"] = {"status": "wrong_effective_date"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = (
            "fake currentness mismatch"
        )
    elif support_relation == "absent":
        payload["observed_qualifiers"] = []
        payload["non_support_reason_when_not_direct"] = "fake proposition absent"
    return payload


def _generic_followup_candidates() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Updated Fee Schedule",
            "url": GENERIC_URL,
            "domain": GENERIC_DOMAIN,
            "snippet": "Example County lists the small-claims filing fee as $42.",
            "published_or_observed_date": "2026-07-01",
        }
    ]


def _generic_followup_materials() -> list[dict[str, Any]]:
    return [
        {
            "bounded_text": GENERIC_FOLLOWUP_TEXT,
            "bounded_text_sanitized": True,
            "bounded_text_bounded": True,
            "content_title": "Example County Updated Fee Schedule",
            "content_type": "text/html",
            "http_status": 200,
            "retrieved_or_observed_at": "offline-followup-reentry",
            "published_or_observed_date": "2026-07-01",
        }
    ]


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


def _assert_no_passport_runtime_dependency(result: Any) -> None:
    serialized = json.dumps(result.payload, sort_keys=True)
    output = result.output
    for forbidden in (
        PASSPORT_COMPONENT_ID,
        PASSPORT_OBLIGATION_ID,
        PASSPORT_TEXT,
        "travel.state.gov",
        PASSPORT_URL,
        "adult passport",
        "passport book",
    ):
        assert forbidden not in serialized
        assert forbidden not in output
    assert "bounded_text" not in serialized
    assert "bounded_text" not in output
    assert "raw_provider_payload" not in output
    assert "raw_model_response" not in output
    assert "product correctness claimed: true" not in output.casefold()
