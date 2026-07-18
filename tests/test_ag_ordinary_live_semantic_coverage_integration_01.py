"""Semantic continuation stays inert when discovery creates no material need.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
    execute_ordinary_live_semantic_coverage,
)
from core.ordinary_live_source_custody_runtime import (
    ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
)
from tests.helpers.offline_ordinary_pipeline import scrub_offline_runtime
from tests.test_ag_ordinary_live_source_custody_integration_01 import (
    FakeSourceFetchRead,
    _candidate_results,
    _run_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch, available_search_providers=("tavily",))


def test_semantic_continuation_skips_after_selected_candidate_nontrigger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetcher = FakeSourceFetchRead()
    _captured, harness, outcome = _run_pipeline(
        tmp_path,
        monkeypatch,
        candidate_enabled=True,
        source_enabled=True,
        semantic_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    source = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert source["status"] == "not_needed"
    assert source["acquisition_need_proposal_created"] is False
    assert source["exact_url_transport_attempted"] is False
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_direct_semantic_runtime_still_fails_closed_without_custody() -> None:
    result = execute_ordinary_live_semantic_coverage(
        run_kernel=None,
        parent_run_id="parent-run",
        parent_request_id="parent-request",
        source_custody_result=None,
    )

    assert result.projection["failed_closed"] is True
    assert result.projection["first_failed_seam"] == (
        "ordinary_live_source_custody_result_missing"
    )
    assert result.projection["semantic_observation_admitted_count"] == 0
    assert result.projection["component_coverage_reduced_count"] == 0


def test_semantic_runtime_has_no_network_or_acquisition_dispatch() -> None:
    path = ROOT / "core" / "ordinary_live_semantic_coverage_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "dispatch_acquisition" not in call_names
    assert "urlopen" not in call_names
    assert "fetch_page" not in call_names
