"""PRODUCT-PATH-REGRESSION: D-prime one-shot provider boundary status.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_one_shot_provider_boundary validation
Why ordinary product-path work cannot be done directly: not applicable; the
ordinary status builder consumes the default-disabled provider boundary while
fixture records exercise future one-shot shape validation without real calls.
Integration deadline: current phase.
Exit condition: keep while D-prime real model review remains gated by a
product-owned one-shot provider boundary.
Why this is not a shadow product path: it invokes the product status builder and
the product-owned boundary validator, not a standalone real-provider runner.
Forbidden interpretation: boundary approval shape is not a real model call,
provider/model selection, semantic support, support proposal, RunKernel
admission, SemanticObservation admission, ComponentCoverage binding, citation
eligibility, answer text, source-obligation satisfaction, or product correctness.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import core.dprime_one_shot_provider_boundary as provider_boundary
import core.dprime_support_proposal_schema as dprime
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    PASSPORT_TEXT,
    QUERY,
    _passport_retained_repo,
)

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_MODULE = ROOT / "core" / "dprime_one_shot_provider_boundary.py"


def test_default_boundary_status_is_product_consumed_and_not_approved(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert f"phase: {dprime.DPRIME_PHASE}" in result.output
    assert "D-prime one-shot provider boundary status: not approved" in result.output
    assert "D-prime model review status: not licensed" in result.output
    assert "D-prime model review call count: 0" in result.output
    assert (
        "current status path live calls: provider/search/broker/fetch/read/"
        "retrieval/model = 0"
    ) in result.output
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["phase"] == dprime.DPRIME_PHASE
    assert dprime_status["one_shot_provider_boundary_status"] == "not approved"
    assert dprime_status["one_shot_provider_boundary_consumed"] is True
    boundary_ref = dprime_status["one_shot_provider_boundary_ref"]
    assert boundary_ref["status"] == "not approved"
    assert boundary_ref["real_provider_call_performed"] is False
    assert boundary_ref["real_model_call_performed"] is False
    assert dprime_status.get("model_review_call_count", 0) == 0


def test_fixture_one_shot_boundary_shape_validates_without_calling_provider(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    validation = provider_boundary.validate_dprime_one_shot_provider_boundary(
        _approved_fixture_boundary()
    )
    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        dprime_one_shot_provider_boundary=_approved_fixture_boundary(),
    )

    assert validation.status == "approved"
    assert validation.approved is True
    assert result.decision == dprime.BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED
    assert "D-prime one-shot provider boundary status: approved" in result.output
    assert "D-prime model review call count: 0" in result.output
    dprime_status = result.payload["dprime_status"]
    assert dprime_status["one_shot_provider_boundary_status"] == "approved"
    assert dprime_status.get("model_review_call_count", 0) == 0
    assert (
        dprime_status["one_shot_provider_boundary_ref"]["real_model_call_performed"]
        is False
    )


def test_safe_one_shot_boundary_shape_only_approves_exact_contract() -> None:
    valid = _approved_fixture_boundary()
    validation = provider_boundary.validate_dprime_one_shot_provider_boundary(valid)

    assert validation.status == "approved"

    mutators: list[tuple[str, Any]] = [
        ("max attempts", lambda payload: payload.update({"max_provider_attempts": 2})),
        ("retry", lambda payload: payload.update({"retry_policy": "retry"})),
        ("fallback", lambda payload: payload.update({"fallback_policy": "fallback"})),
        (
            "timeout",
            lambda payload: payload.update({"timeout_policy": "retry_then_fail"}),
        ),
        (
            "raw prompt",
            lambda payload: payload.update({"raw_prompt_retention": True}),
        ),
        (
            "raw model response",
            lambda payload: payload.update({"raw_model_response_retention": True}),
        ),
        (
            "provider payload",
            lambda payload: payload.update({"provider_payload_retention": True}),
        ),
        (
            "authorization",
            lambda payload: payload.update({"real_call_authorized": False}),
        ),
        (
            "approval ref",
            lambda payload: payload.update({"provider_model_approval_ref": ""}),
        ),
        (
            "provider selection",
            lambda payload: payload.update(
                {"provider": "FixtureProvider", "model": "fixture-model"}
            ),
        ),
    ]
    for label, mutate in mutators:
        candidate = dict(valid)
        candidate["closed_surface_flags"] = dict(valid["closed_surface_flags"])
        mutate(candidate)

        result = provider_boundary.validate_dprime_one_shot_provider_boundary(
            candidate
        )

        assert result.status != "approved", label


def test_real_call_boundary_requires_one_shot_adapter_ref_and_proof() -> None:
    missing_adapter = _approved_fixture_boundary()
    missing_adapter.update({"test_only": False})

    result = provider_boundary.validate_dprime_one_shot_provider_boundary(
        missing_adapter
    )

    assert result.status == "not approved"
    blocker_text = " ".join(result.blockers)
    assert "proven one-shot adapter status" in blocker_text
    assert "explicit one-shot adapter ref" in blocker_text

    approved = _approved_real_protocol_boundary()
    validation = provider_boundary.validate_dprime_one_shot_provider_boundary(
        approved
    )

    assert validation.status == "approved"
    assert validation.boundary_ref["test_only"] is False
    assert validation.boundary_ref["one_shot_adapter_proven"] is True
    assert validation.boundary_ref["one_shot_adapter_ref"] == (
        "fixture-one-shot-adapter-ref:dprime-prerun-adapter-gate-01"
    )


def test_broad_helper_shape_rejected_fail_closed() -> None:
    candidate = _approved_fixture_boundary()
    candidate.update(
        {
            "candidate_helper": "core.llm.ask_model",
            "fallback_policy": "enabled",
            "max_provider_attempts": 3,
            "provider_switching_allowed": True,
            "raw_model_response_retained": True,
            "retry_policy": "retry_with_backoff",
        }
    )
    candidate["closed_surface_flags"] = {
        **candidate["closed_surface_flags"],
        "fallback_enabled": True,
        "multi_call_review_enabled": True,
        "provider_switching_enabled": True,
        "raw_model_response_retained": True,
        "retry_loop_created": True,
    }

    result = provider_boundary.validate_dprime_one_shot_provider_boundary(
        candidate
    )

    assert result.status == "rejected"
    blocker_text = " ".join(result.blockers)
    assert "broad model helper candidate is unsafe" in blocker_text
    assert "multiple attempts" in blocker_text
    assert "fallback is forbidden" in blocker_text
    assert "retries are forbidden" in blocker_text


def test_broad_helper_declaration_remains_rejected_even_with_adapter_flag() -> None:
    candidate = _approved_real_protocol_boundary()
    candidate.update(
        {
            "candidate_helper": "core.llm.ask_model",
            "one_shot_adapter_proven": True,
        }
    )

    result = provider_boundary.validate_dprime_one_shot_provider_boundary(
        candidate
    )

    assert result.status == "rejected"
    assert "broad model helper candidate is unsafe" in " ".join(result.blockers)


def test_boundary_module_avoids_real_provider_imports() -> None:
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

    assert _imports(BOUNDARY_MODULE).isdisjoint(forbidden_imports)


def test_no_new_durable_proplex_dprime_module_added() -> None:
    assert list((ROOT / "proplex").glob("dprime_*.py")) == []


def test_boundary_status_output_hygiene_excludes_raw_and_closed_material(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)

    result = build_live_semantic_coverage_status(query=QUERY, repo_root=repo_root)

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
            "one_shot_adapter_ref": (
                "fixture-one-shot-adapter-ref:dprime-prerun-adapter-gate-01"
            ),
        }
    )
    return boundary


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
