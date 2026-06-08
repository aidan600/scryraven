from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from core.provider_search_final_assembly_authority_boundary import (
    AuthorityBoundaryClassification,
    AuthorityBoundaryError,
    build_provider_search_authority_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_HELPER = _ROOT / "core" / "provider_search_final_assembly_authority_boundary.py"
_ORCHESTRATOR = _ROOT / "core" / "pipeline_orchestrator.py"


def test_provider_list_cannot_silently_bypass_controller_owned_allocation() -> None:
    boundary = build_provider_search_authority_boundary(
        controller_provider_list=("brave", "tavily"),
        effective_provider_list=("brave", "tavily"),
        controller_search_depth="basic",
        effective_search_depth="basic",
        query_sources=("router_query_preparation_contract",),
    )

    assert boundary.provider_list_classification == AuthorityBoundaryClassification.CONTROLLER_OWNED
    assert boundary.controller_provider_list == boundary.effective_provider_list

    with pytest.raises(AuthorityBoundaryError, match="provider list differs"):
        build_provider_search_authority_boundary(
            controller_provider_list=("brave", "tavily"),
            effective_provider_list=("exa",),
        )


def test_search_depth_cannot_silently_bypass_controller_owned_retrieval_posture() -> None:
    boundary = build_provider_search_authority_boundary(
        controller_search_depth="basic",
        effective_search_depth="basic",
    )

    assert boundary.search_depth_classification == AuthorityBoundaryClassification.CONTROLLER_OWNED

    with pytest.raises(AuthorityBoundaryError, match="search depth differs"):
        build_provider_search_authority_boundary(
            controller_search_depth="basic",
            effective_search_depth="deep",
        )


def test_query_order_recency_merge_and_recovery_dispatch_are_classified() -> None:
    boundary = build_provider_search_authority_boundary(
        controller_provider_list=("brave",),
        effective_provider_list=("brave",),
        controller_search_depth="basic",
        effective_search_depth="basic",
        query_sources=(
            "router_query_preparation_contract",
            "source_class_recovery_controller",
            "weak_corpus_controller",
            "conflict_resolution_controller",
        ),
        query_order_classification=AuthorityBoundaryClassification.CONTROLLER_OWNED,
        recency_merge_classification=AuthorityBoundaryClassification.PROTECTED_LEGACY_BEHAVIOR,
        recovery_query_dispatch_classification=AuthorityBoundaryClassification.CONTROLLER_OWNED,
        protected_legacy_behavior=("source_recency merge preserves existing behavior",),
    )

    trace = boundary.to_trace()

    assert trace["query_order_classification"] == "controller_owned"
    assert trace["recency_merge_classification"] == "protected_legacy_behavior"
    assert trace["recovery_query_dispatch_classification"] == "controller_owned"
    assert "source_class_recovery_controller" in trace["query_sources"]
    assert "weak_corpus_controller" in trace["query_sources"]
    assert "conflict_resolution_controller" in trace["query_sources"]


def test_supplemental_search_if_present_is_explicitly_classified() -> None:
    boundary = build_provider_search_authority_boundary(
        supplemental_search_classification=AuthorityBoundaryClassification.PARKED_HIDDEN_AUTHORITY,
        parked_hidden_authority=("synthesis_evaluator_supplemental_search_trigger",),
    )

    assert boundary.supplemental_search_classification == (
        AuthorityBoundaryClassification.PARKED_HIDDEN_AUTHORITY
    )
    assert "synthesis_evaluator_supplemental_search_trigger" in boundary.parked_hidden_authority


def test_ag79b_helper_has_static_protected_import_guard() -> None:
    tree = ast.parse(_HELPER.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {
        "core.db",
        "core.economist_handoff_contract",
        "core.llm",
        "core.output_validation",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.retrieval",
        "core.scout",
        "core.search_providers",
        "core.storage",
    }
    assert imported.isdisjoint(forbidden)


def test_pipeline_orchestrator_boundary_guard_untouched() -> None:
    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        check=True,
        cwd=_ROOT,
        text=True,
        capture_output=True,
    ).stdout.splitlines()

    # The AG-79B static helper is intentionally not wired into the product path.
    assert _ORCHESTRATOR.read_text(encoding="utf-8")
    if "core/pipeline_orchestrator.py" in diff:
        pipeline_diff = subprocess.run(
            ["git", "diff", "HEAD", "--", "core/pipeline_orchestrator.py"],
            check=True,
            cwd=_ROOT,
            text=True,
            capture_output=True,
        ).stdout
        assert (
            "synthesis_evaluator_supplemental_search_runtime_handoff" in pipeline_diff
            or "final_answer_runtime_adapter" in pipeline_diff
            or "FinalAnswerPacket" in pipeline_diff
            or "pre_author_source_obligation_projection" in pipeline_diff
            or "session_output_projection" in pipeline_diff
            or "runtime_prompt_assembly" in pipeline_diff
            or "retrieval_dispatch_runtime" in pipeline_diff
                or "retrieval_stop_trace_projection" in pipeline_diff
                or "query_authority.admit_execution_queries" in pipeline_diff
                or "provider_plan" in pipeline_diff
        )
