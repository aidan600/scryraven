"""PRODUCT-PATH-REGRESSION: D-prime one-shot model-review adapter contract.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_one_shot_model_review_adapter
Why ordinary product-path work cannot be done directly: real model review is not
licensed; this phase permits only fixture transports behind the product-owned
one-shot adapter contract to prove future real-run shape without provider calls.
Integration deadline: current phase.
Exit condition: keep while D-prime real model review requires a product-owned
one-shot adapter contract before any human-approved real model run.
Why this is not a shadow product path: it invokes the ordinary product status
builder and the same product-owned runner path that a future provider adapter
must use, not a standalone proof script or side harness.
Forbidden interpretation: configured adapter metadata or fixture invocation is
not a real model call, semantic support, support proposal validation, RunKernel
admission, SemanticObservation admission, ComponentCoverage binding, citation
eligibility, answer text, source-obligation satisfaction, or product correctness.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Callable

import pytest

import core.dprime_assessment_validation as assessment_validation
import core.dprime_one_shot_model_review_adapter as adapter_contract
import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import (
    ADAPTER_REF,
    _approved_real_protocol_boundary,
    _assessment_payload,
    _real_license,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_MODULE = ROOT / "core" / "dprime_one_shot_model_review_adapter.py"


def test_default_adapter_status_is_product_consumed_and_not_configured(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert f"phase: {dprime.DPRIME_PHASE}" in result.output
    assert (
        "D-prime one-shot model-review adapter status: not configured"
        in result.output
    )
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["one_shot_model_review_adapter_status"] == "not configured"
    assert dprime_status["one_shot_model_review_adapter_consumed"] is True
    assert dprime_status["model_review_call_count"] == 0


def test_real_one_shot_license_and_boundary_without_adapter_blocks_before_invocation(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_model_review_license=_real_license(),
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert (
        result.payload["dprime_status"]["one_shot_model_review_adapter_status"]
        == "not configured"
    )
    assert "configured adapter contract" in result.output


def test_real_one_shot_bare_callable_is_rejected_even_with_boundary(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def bare_callable(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_model_review_license=_real_license(),
        dprime_model_review_callable=bare_callable,
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert "not a bare callable" in result.output


def test_matching_adapter_contract_invokes_once_through_product_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls: list[dict[str, Any]] = []

    def transport(prompt: str, **kwargs: Any) -> dict[str, Any]:
        calls.append(
            {
                "prompt": prompt,
                "input_packet": kwargs["input_packet"],
                "boundary_ref": kwargs["one_shot_provider_boundary_ref"],
                "adapter_ref": kwargs["one_shot_model_review_adapter_ref"],
            }
        )
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(transport),
        dprime_model_review_license=_real_license(),
    )

    assert len(calls) == 1
    assert "EvidenceRelativeSupportAssessment" in calls[0]["prompt"]
    assert calls[0]["boundary_ref"]["status"] == "approved"
    assert calls[0]["adapter_ref"]["status"] == "configured"
    assert calls[0]["input_packet"]["one_shot_model_review_adapter_ref"][
        "status"
    ] == "configured"
    assert result.decision == (
        dprime.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
    )
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["model_review_call_count"] == 1
    assert (
        dprime_status["proposal_validation_status"]
        == dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert (
        dprime_status["run_kernel_support_admission_status"]
        == dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert dprime_status["run_kernel_admission_decision_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert dprime_status["run_kernel_support_admission_request_ref"][
        "request_status"
    ] == dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    assert dprime_status["model_review_status"] == "completed"
    assert (
        dprime_status["assessment_validation_status"]
        == assessment_validation.ASSESSMENT_SCHEMA_VALID
    )
    assert dprime_status["objects_created"]["validated_support_proposal"] is True
    assert dprime_status["objects_created"][
        "run_kernel_support_proposal_admission_request"
    ] is True
    model_review_ref = dprime_status["model_review_ref"]
    adapter_ref = model_review_ref["one_shot_model_review_adapter_ref"]
    assert adapter_ref["status"] == "configured"
    assert adapter_ref["adapter_ref"]["adapter_ref"] == ADAPTER_REF


def test_adapter_ref_mismatch_blocks_before_invocation(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def transport(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(
            transport,
            adapter_ref="fixture-one-shot-adapter-ref:mismatch",
        ),
        dprime_model_review_license=_real_license(),
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert "adapter contract ref does not match license" in result.output


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_provider_attempts": 2},
        {"retry_policy": "retry"},
        {"fallback_policy": "fallback"},
        {"provider_switching_allowed": True},
        {"timeout_policy": "retry_then_fail"},
        {"call_count": 1},
        {"raw_prompt_retained": True},
        {"raw_model_response_retained": True},
        {"provider_payload_retained": True},
        {"real_provider_call_performed": True},
        {"real_model_call_performed": True},
        {"provider_model_selection_detail_present": True},
    ],
)
def test_adapter_policy_and_retention_violations_fail_closed(
    tmp_path: Path,
    overrides: dict[str, Any],
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def transport(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(transport, **overrides),
        dprime_model_review_license=_real_license(),
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert result.payload["dprime_status"]["model_review_call_count"] == 0
    assert (
        result.payload["dprime_status"]["one_shot_model_review_adapter_status"]
        == "rejected"
    )


def test_broad_helper_shape_is_rejected_fail_closed(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def transport(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _assessment_payload()

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(
            transport,
            candidate_helper="core.llm.ask_model",
        ),
        dprime_model_review_license=_real_license(),
    )

    assert calls == 0
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_INPUT_INVALID
    assert "broad model helper candidate is unsafe" in " ".join(
        result.payload["dprime_status"]["one_shot_model_review_adapter_ref"][
            "blockers"
        ]
    )


@pytest.mark.parametrize("exc", [TimeoutError("fake timeout"), RuntimeError("boom")])
def test_adapter_timeout_or_error_invokes_at_most_once_without_retry(
    tmp_path: Path,
    exc: Exception,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    calls = 0

    def transport(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise exc

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(transport),
        dprime_model_review_license=_real_license(),
    )

    assert calls == 1
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED
    assert result.payload["dprime_status"]["model_review_call_count"] == 1
    assert "D-prime model review status: blocked" in result.output


def test_analysis_gap_search_proposal_remains_forbidden_through_adapter(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    payload = _assessment_payload()
    payload["analysis_gap_search_proposal"] = {
        "proposal_text": "search again for broader evidence",
    }

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(lambda *_a, **_k: payload),
        dprime_model_review_license=_real_license(),
    )

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID
    assert "analysis_gap_search_proposal" not in result.output
    assert "search again for broader evidence" not in result.output


def test_adapter_product_output_hygiene_excludes_raw_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(
            lambda *_args, **_kwargs: _assessment_payload()
        ),
        dprime_model_review_license=_real_license(),
    )

    for forbidden in (
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "bounded_text",
        PASSPORT_TEXT,
        "raw page text",
        "answer prose",
        "citation-ready material",
        "FAP",
        "Author prose",
        "product correctness",
    ):
        assert forbidden not in result.output


def test_no_new_durable_proplex_dprime_module_added() -> None:
    assert list((ROOT / "proplex").glob("dprime_*.py")) == []


def test_adapter_module_avoids_live_provider_imports() -> None:
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

    assert _imports(ADAPTER_MODULE).isdisjoint(forbidden_imports)


def test_current_phase_metadata_on_product_and_adapter_refs(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=_adapter(
            lambda *_args, **_kwargs: _assessment_payload()
        ),
        dprime_model_review_license=_real_license(),
    )

    dprime_status = result.payload["dprime_status"]
    model_review_ref = dprime_status["model_review_ref"]
    adapter_ref = model_review_ref["one_shot_model_review_adapter_ref"][
        "adapter_ref"
    ]
    assert dprime_status["phase"] == dprime.DPRIME_PHASE
    assert f"phase: {dprime.DPRIME_PHASE}" in result.output
    assert dprime_status["prompt_license_ref"]["phase"] == dprime.DPRIME_PHASE
    assert dprime_status["input_packet_ref"]["phase"] == dprime.DPRIME_PHASE
    assert model_review_ref["phase"] == dprime.DPRIME_PHASE
    assert adapter_ref["phase"] == dprime.DPRIME_PHASE


def test_product_path_consumes_safe_adapter_metadata(tmp_path: Path) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    adapter = _adapter(lambda *_args, **_kwargs: _assessment_payload())

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_real_protocol_boundary(),
        dprime_one_shot_model_review_adapter=adapter,
        dprime_model_review_license=_real_license(),
    )

    dprime_status = result.payload["dprime_status"]
    status_ref = dprime_status["one_shot_model_review_adapter_ref"]
    assert dprime_status["one_shot_model_review_adapter_status"] == "configured"
    assert dprime_status["one_shot_model_review_adapter_consumed"] is True
    assert status_ref["adapter_ref"]["adapter_ref"] == ADAPTER_REF
    assert status_ref["adapter_ref"]["provider_model_approval_ref"] == (
        _approved_real_protocol_boundary()["provider_model_approval_ref"]
    )
    assert status_ref["adapter_ref"]["provider_boundary_ref"] == (
        _approved_real_protocol_boundary()["boundary_id"]
    )
    assert status_ref["adapter_contract_valid_is_not_semantic_support"] is True


def _adapter(
    transport: Callable[..., Any],
    **overrides: Any,
) -> adapter_contract.DPrimeOneShotModelReviewAdapter:
    boundary = _approved_real_protocol_boundary()
    values = {
        "adapter_ref": ADAPTER_REF,
        "provider_model_approval_ref": boundary["provider_model_approval_ref"],
        "provider_boundary_ref": boundary["boundary_id"],
        "transport": transport,
        "closed_surface_flags": adapter_contract.default_closed_surface_flags(),
    }
    values.update(overrides)
    return adapter_contract.DPrimeOneShotModelReviewAdapter(**values)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
