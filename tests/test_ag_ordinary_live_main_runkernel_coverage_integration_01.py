"""Main-RunKernel coverage cannot reacquire after a candidate nontrigger.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.ordinary_live_main_runkernel_coverage_runtime import (
    ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
    execute_ordinary_live_main_runkernel_coverage,
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


def test_main_coverage_does_not_reacquire_selected_candidate(
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
        consolidation_enabled=True,
        main_coverage_enabled=True,
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    source = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert source["status"] == "not_needed"
    assert source["exact_url_cap_charged"] is False
    assert source["exact_url_transport_attempted"] is False
    assert (
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY
        not in outcome.execution_trace
    )
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_direct_main_coverage_still_fails_closed_without_main_kernel() -> None:
    result = execute_ordinary_live_main_runkernel_coverage(
        main_run_kernel=None,
        query="offline question",
        requested_mode="Balanced",
        run_contract_projection={},
    )

    assert result.projection["failed_closed"] is True
    assert result.projection["first_failed_seam"] == "main_run_kernel_missing"
    assert result.projection["candidate_handoff_attempted_count"] == 0
    assert result.projection["source_custody_attempted_count"] == 0
    assert result.projection["semantic_observation_admitted_count"] == 0
    assert result.projection["component_coverage_reduced_count"] == 0


def test_main_coverage_helper_consumes_prior_custody_without_reacquisition() -> None:
    path = ROOT / "core" / "ordinary_live_main_runkernel_coverage_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    source_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "execute_ordinary_live_source_custody"
    ]
    assert source_calls == []
    assert all(
        not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "dispatch_acquisition"
        )
        for node in ast.walk(tree)
    )
    orchestrator_source = (
        ROOT / "core" / "pipeline_orchestrator.py"
    ).read_text(encoding="utf-8")
    assert "source_custody_result=ordinary_live_source_custody" in orchestrator_source
