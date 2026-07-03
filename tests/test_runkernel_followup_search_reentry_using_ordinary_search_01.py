"""PRODUCT-PATH-REGRESSION: RunKernel D-prime follow-up ordinary search re-entry.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.runkernel_followup_search_reentry_ordinary_search_runtime
Why ordinary product-path work cannot be done directly: live/provider/search/
fetch/read/retrieval/model calls are closed in this phase, so the product status
path uses structured offline candidate/read material and injected fake D-prime
review callables.
Integration deadline: current phase.
Exit condition: keep as the regression guard for D-prime follow-up needs that
must re-enter the ordinary SearchPlanner/SearchExecutorHandoff/live-validation
path before second-pass D-prime support and answer-path consumption.
Why this is not a shadow product path: it invokes the product status builder and
RunKernel-owned ordinary reducers, not a detached follow-up search subsystem.
Forbidden interpretation: this does not claim live validation, product
correctness, generic D-prime analyst intake, or answer quality.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core import runkernel_followup_search_reentry_ordinary_search_runtime as followup_runtime
from core.dprime_support_proposal_schema import (
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
)
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    PASSPORT_URL,
    QUERY,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import (
    _assessment_payload,
    _license,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "core" / "runkernel_followup_search_reentry_ordinary_search_runtime.py"
STATUS = ROOT / "proplex" / "live_semantic_coverage_status.py"

FOLLOWUP_TEXT = (
    "The U.S. Department of State passport fees schedule states the adult "
    "passport book renewal by mail fee is $130."
)


def test_dprime_followup_need_reenters_ordinary_search_then_answer_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert result.decision == "PASS", result.payload.get("blocker_detail")
    followup = result.payload["dprime_followup_search_reentry_ref"]
    assert followup["followup_loop_owner"] == "RunKernel/product"
    assert followup["dprime_followup_need_owner"] == "D-prime"
    assert followup["dprime_dispatch_owner"] is False
    assert followup["new_search_subsystem_created"] is False
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
    admission_ref = followup["followup_source_evidence_admission_ref"]
    packet_ref = followup["fetch_read_content_packet_ref"]
    assert admission_ref["status"] == "custody_created"
    assert admission_ref["owner"] == "RunKernel.EvidenceLedger"
    assert admission_ref["reducer_backed"] is True
    assert admission_ref["fetch_read_content_packet_id"] == packet_ref["packet_id"]
    assert (
        admission_ref["fetch_read_content_packet_digest"]
        == packet_ref["packet_digest"]
    )
    assert admission_ref["observation_id"] == (
        admission_ref["evidence_ledger_reducer_observation_id"]
    )
    assert "dprime_followup_reentry" in (
        admission_ref["evidence_ledger_reducer_observation_id"]
    )
    assert len(admission_ref["evidence_ledger_projection_digest"]) == 64
    assert len(admission_ref["fetch_read_candidate_custody_projection_digest"]) == 64
    assert followup["provider_called"] is False
    assert followup["live_provider_called"] is False
    assert followup["live_search_called"] is False
    assert followup["fetch_read_executed"] is False
    assert followup["read_executed"] is False
    assert followup["retrieval_executed"] is False
    assert followup["product_correctness_claimed"] is False

    dprime_status = result.payload["dprime_status"]
    assert (
        dprime_status["proposal_validation_status"]
        == DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert dprime_status["objects_created"]["semantic_observation"] is True
    assert dprime_status["objects_created"]["component_coverage"] is True
    assert dprime_status["objects_created"]["sufficiency_readiness"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is True
    assert result.payload["dprime_answer_path_ref"]["status"] == "consumed"
    assert "ordinary follow-up SearchExecutorHandoff status: consumed" in (
        result.output
    )


def test_second_pass_non_support_is_named_blocker_after_search_reentry(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review("absent"),
    )

    assert result.decision != "PASS"
    followup = result.payload["dprime_followup_search_reentry_ref"]
    assert followup["status"] == "second_dprime_pass_blocked"
    assert followup["ordinary_search_executor_handoff_status"] == "consumed"
    assert followup["search_result_candidate_packet_status"] == "created"
    assert followup["fetch_read_content_packet_status"] == "created"
    assert followup["evidence_reentry_status"] == "consumed"
    assert followup["second_dprime_pass_status"] == "blocked"
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"
    assert result.payload["semantic_support_source"] == (
        "unavailable; D-prime second-pass assessment is not support"
    )


def test_followup_fetch_packet_is_reduced_through_existing_evidence_ledger_reducer(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    original_reduce = (
        followup_runtime.reduce_fetch_read_content_packet_into_evidence_ledger
    )
    calls: list[dict[str, Any]] = []

    def spy_reduce(**kwargs: Any) -> dict[str, Any]:
        projection = original_reduce(**kwargs)
        packet = kwargs["fetch_read_content_packet"]
        calls.append(
            {
                "packet_id": packet.get("packet_id"),
                "packet_digest": packet.get("packet_digest"),
                "observation_id": kwargs.get("observation_id"),
            }
        )
        return projection

    monkeypatch.setattr(
        followup_runtime,
        "reduce_fetch_read_content_packet_into_evidence_ledger",
        spy_reduce,
    )

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert result.decision == "PASS"
    followup = result.payload["dprime_followup_search_reentry_ref"]
    packet_ref = followup["fetch_read_content_packet_ref"]
    admission_ref = followup["followup_source_evidence_admission_ref"]
    matching_followup_calls = [
        call
        for call in calls
        if call["packet_id"] == packet_ref["packet_id"]
        and call["packet_digest"] == packet_ref["packet_digest"]
    ]
    assert len(calls) >= 2
    assert matching_followup_calls
    assert _ledger_observation_token(matching_followup_calls[0]["observation_id"]) == (
        admission_ref["evidence_ledger_reducer_observation_id"]
    )
    assert "dprime_followup_reentry" in matching_followup_calls[0]["observation_id"]
    assert any(call["packet_id"] != packet_ref["packet_id"] for call in calls)


def test_followup_reentry_fails_closed_without_reducer_backed_followup_custody(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    original_reduce = (
        followup_runtime.reduce_fetch_read_content_packet_into_evidence_ledger
    )
    preflight_calls = 0

    def fake_reduce(**kwargs: Any) -> dict[str, Any]:
        observation_id = kwargs.get("observation_id")
        if observation_id and "dprime_followup_reentry" in observation_id:
            return {
                "owner": "RunKernel.EvidenceLedger",
                "observation_refs": [
                    {
                        "observation_id": observation_id,
                        "source": "fetch_read_content_packet_candidate_custody",
                    }
                ],
                "fetch_read_candidate_custody": {
                    "owner": "RunKernel.EvidenceLedger",
                    "fetch_read_candidate_custody_records": [],
                    "candidate_content_custody_visible": False,
                    "custody_record_count": 0,
                    "readable_record_count": 0,
                },
            }
        return original_reduce(**kwargs)

    def fail_if_preflight_reached(**_kwargs: Any) -> Any:
        nonlocal preflight_calls
        preflight_calls += 1
        raise AssertionError("second-pass D-prime preflight should not be reached")

    monkeypatch.setattr(
        followup_runtime,
        "reduce_fetch_read_content_packet_into_evidence_ledger",
        fake_reduce,
    )
    monkeypatch.setattr(
        followup_runtime,
        "build_evidence_frame_preflight",
        fail_if_preflight_reached,
    )

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert result.decision == (
        followup_runtime.BLOCKED_FOLLOWUP_FETCH_READ_LEDGER_REENTRY_MISSING
    )
    followup = result.payload["dprime_followup_search_reentry_ref"]
    assert followup["status"] == "failed_closed"
    assert followup["first_failed_seam"] == "followup_fetch_read_ledger_reentry_missing"
    assert "evidence_reentry_status" not in followup
    assert "second_dprime_pass_status" not in followup
    assert preflight_calls == 0


def test_followup_reentry_fails_closed_when_followup_reducer_raises(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    original_reduce = (
        followup_runtime.reduce_fetch_read_content_packet_into_evidence_ledger
    )
    preflight_calls = 0

    def fake_reduce(**kwargs: Any) -> dict[str, Any]:
        observation_id = kwargs.get("observation_id")
        if observation_id and "dprime_followup_reentry" in observation_id:
            raise ValueError("follow-up reducer unavailable")
        return original_reduce(**kwargs)

    def fail_if_preflight_reached(**_kwargs: Any) -> Any:
        nonlocal preflight_calls
        preflight_calls += 1
        raise AssertionError("second-pass D-prime preflight should not be reached")

    monkeypatch.setattr(
        followup_runtime,
        "reduce_fetch_read_content_packet_into_evidence_ledger",
        fake_reduce,
    )
    monkeypatch.setattr(
        followup_runtime,
        "build_evidence_frame_preflight",
        fail_if_preflight_reached,
    )

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert result.decision == (
        followup_runtime.BLOCKED_FOLLOWUP_FETCH_READ_LEDGER_REENTRY_MISSING
    )
    followup = result.payload["dprime_followup_search_reentry_ref"]
    assert followup["status"] == "failed_closed"
    assert followup["first_failed_seam"] == "followup_fetch_read_ledger_reentry_failed"
    assert "evidence_reentry_status" not in followup
    assert "second_dprime_pass_status" not in followup
    assert preflight_calls == 0


def test_followup_reentry_output_hygiene_excludes_reentered_bounded_text(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_followup_candidates(),
        dprime_followup_fetch_read_materials=_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    serialized = json.dumps(result.payload, sort_keys=True).casefold()
    output = result.output.casefold()
    for forbidden in (
        FOLLOWUP_TEXT.casefold(),
        PASSPORT_TEXT.casefold(),
        "bounded_text",
        "raw page text",
        "provider payload",
        "product correctness claimed: true",
    ):
        assert forbidden not in output
        assert forbidden not in serialized


def test_followup_reentry_is_status_consumed_not_new_search_subsystem() -> None:
    runtime_imports, runtime_calls = _imports_and_calls(RUNTIME)
    status_imports, status_calls = _imports_and_calls(STATUS)

    assert "core.runkernel_followup_search_reentry_ordinary_search_runtime" in (
        status_imports
    )
    assert "run_dprime_followup_search_reentry_using_ordinary_search" in (
        status_calls
    )
    assert "execute_search_planner_action" in runtime_calls
    assert "execute_search_executor_handoff_action" in runtime_calls
    assert "build_live_search_validation_observation_payload" in runtime_calls
    assert "build_search_result_candidate_packet_from_live_validation_state" in (
        runtime_calls
    )
    assert "build_fetch_read_content_packet_from_candidate_packet" in runtime_calls
    assert "reduce_fetch_read_content_packet_into_evidence_ledger" in runtime_calls
    assert "_source_evidence_admission_ref_from_reducer" in runtime_calls
    assert "_source_evidence_admission_ref" not in runtime_calls
    assert "run_dprime_model_review_assessment" in runtime_calls
    assert "build_dprime_single_lane_answer_path" in runtime_calls
    for forbidden_call in (
        "run_pipeline",
        "run_fixture_followup_search_reentry_loop",
        "build_fixture_search_result_candidate_packet",
    ):
        assert forbidden_call not in runtime_calls


def _fake_review(support_relation: str) -> Any:
    payload = _assessment_payload(support_relation)

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return fake_review


def _followup_candidates() -> list[dict[str, Any]]:
    return [
        {
            "title": "Passport Fees",
            "url": PASSPORT_URL,
            "domain": "travel.state.gov",
            "snippet": "Adult passport book renewal by mail fee is listed as $130.",
            "published_or_observed_date": "2026-01-01",
        }
    ]


def _followup_materials() -> list[dict[str, Any]]:
    return [
        {
            "bounded_text": FOLLOWUP_TEXT,
            "bounded_text_sanitized": True,
            "bounded_text_bounded": True,
            "content_title": "Passport Fees",
            "content_type": "text/html",
            "http_status": 200,
            "retrieved_or_observed_at": "offline-followup-reentry",
            "published_or_observed_date": "2026-01-01",
        }
    ]


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    return imported, called


def _ledger_observation_token(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text.casefold().replace("-", "_").replace(" ", "_")[:160]
