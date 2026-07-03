"""PRODUCT-PATH-REGRESSION: D-prime single-lane answer path.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_single_lane_answer_path_runtime
Why ordinary product-path work cannot be done directly: the ordinary dry-run
status path uses retained fixture-sized artifacts and an injected fake
model-review callable because live/model/provider/search/fetch/read/retrieval
calls are closed in this phase.
Integration deadline: current phase.
Exit condition: keep as the regression guard for completed D-prime support
bundle -> SufficiencyReadiness -> hardened FAP -> Author answer ->
citation/source display.
Why this is not a shadow product path: it invokes the product status builder and
RunKernel-owned reducers, not a detached helper-only answer path.
Forbidden interpretation: this does not claim product correctness, generic
D-prime analyst intake, live validation, or answer quality.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

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

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "core" / "dprime_single_lane_answer_path_runtime.py"
STATUS = ROOT / "proplex" / "live_semantic_coverage_status.py"


def test_product_status_consumes_support_bundle_through_author_answer(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    assert result.decision == "PASS"
    assert result.return_code == 0
    assert result.payload["next_blocked_surface"] is None
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["objects_created"]["sufficiency_readiness"] is True
    assert dprime_status["objects_created"]["final_answer_packet"] is True
    assert dprime_status["objects_created"]["author_answer"] is True
    assert dprime_status["objects_created"]["citation_source_display"] is True

    answer_path = result.payload["dprime_answer_path_ref"]
    assert answer_path["status"] == "consumed"
    assert answer_path["single_lane_only"] is True
    assert answer_path["support_bundle_consumed_by_answer_path"] is True
    assert answer_path["sufficiency_readiness_status"] == "full_answer_ready"
    assert answer_path["final_answer_packet_status"] == "full_answer_packet_ready"
    assert answer_path["author_answer_status"] == "full_answer_prose_created"
    assert answer_path["citation_source_display_status"] == "created"
    assert answer_path["fap_consumed_dprime_source_refs"] is True
    assert answer_path["author_answer_consumed_fap"] is True
    assert answer_path["answer_text"]
    assert answer_path["product_correctness_claimed"] is False
    assert "Author answer status: full_answer_prose_created" in result.output
    assert "citation/source display:" in result.output


def test_citation_source_display_consumes_handoff_without_correctness_claim(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())

    citation_authority = result.payload["citation_eligibility_authority_ref"]
    display = result.payload["dprime_answer_path_ref"]["citation_source_display"]
    authority_record = citation_authority["citation_source_records"][0]
    display_entry = display["citation_source_entries"][0]

    assert citation_authority["citation_source_handoff_consumed"] is True
    assert citation_authority["citations_rendered"] is False
    assert display["citation_source_handoff_consumed"] is True
    assert display["citations_rendered"] is True
    assert display_entry["derived_from_citation_source_handoff"] is True
    assert display_entry["content_ref_id"] == authority_record["content_ref_id"]
    assert display_entry["evidence_id"] == authority_record["evidence_id"]
    assert display_entry["url"] == authority_record["url"]
    assert display_entry["product_correctness_claimed"] is False
    assert display["product_correctness_claimed"] is False


@pytest.mark.parametrize(
    "decision_status",
    [
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_REJECTED,
        rk_dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    ],
)
def test_rejected_or_challenged_decisions_do_not_create_answer_path(
    tmp_path: Path,
    decision_status: str,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(
        repo_root,
        _assessment_payload(),
        decision_status=decision_status,
    )

    dprime_status = result.payload["dprime_status"]
    assert result.decision != "PASS"
    assert dprime_status["run_kernel_admission_decision_status"] == decision_status
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert dprime_status["objects_created"].get("sufficiency_readiness") is not True
    assert dprime_status["objects_created"].get("final_answer_packet") is not True
    assert dprime_status["objects_created"].get("author_answer") is not True
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"


def test_output_hygiene_excludes_raw_private_and_correctness_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = _run_product_status_with_assessment(repo_root, _assessment_payload())
    serialized = json.dumps(result.payload, sort_keys=True).casefold()
    output = result.output.casefold()

    for forbidden in (
        "bounded_text",
        PASSPORT_TEXT.casefold(),
        "raw prompt",
        "raw model response",
        "provider payload",
        "raw page text",
        "secret",
        "product correctness claimed: true",
    ):
        assert forbidden not in output
        assert forbidden not in serialized
    assert "answerability/correctness: not claimed" in output
    assert result.payload["dprime_answer_path_ref"]["model_called"] is False
    assert result.payload["dprime_answer_path_ref"]["live_provider_called"] is False


def test_answer_path_is_product_status_consumed_not_detached() -> None:
    runtime_imports, runtime_calls = _imports_and_calls(RUNTIME)
    status_imports, status_calls = _imports_and_calls(STATUS)

    assert "core.dprime_single_lane_answer_path_runtime" in status_imports
    assert "build_dprime_single_lane_answer_path" in status_calls
    assert "reduce_sufficiency_readiness" in runtime_calls
    assert "reduce_hardened_final_answer_packet" in runtime_calls
    assert "reduce_author_prose_finalization" in runtime_calls
    assert "authorize_dprime_citation_source_display" in runtime_calls
    for forbidden_call in (
        "run_pipeline",
        "execute_author",
        "build_final_answer_packet",
        "run_dprime_model_review_assessment",
    ):
        assert forbidden_call not in runtime_calls


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
