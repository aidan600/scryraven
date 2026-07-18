"""Authority consolidation cannot manufacture material after candidate selection.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.ordinary_live_authority_consolidation_runtime import (
    ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
    execute_ordinary_live_authority_consolidation,
)
from core.ordinary_live_semantic_coverage_runtime import (
    ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY,
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


def test_consolidation_skips_when_no_explicit_material_need_exists(
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
        candidate_results=_candidate_results(),
        fetcher=fetcher,
    )

    source = outcome.execution_trace[ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY]
    assert source["status"] == "not_needed"
    assert ORDINARY_LIVE_SEMANTIC_COVERAGE_TRACE_KEY not in outcome.execution_trace
    assert (
        ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY
        not in outcome.execution_trace
    )
    assert fetcher.calls == []
    assert harness.forbidden_live_calls == []


def test_direct_consolidation_still_fails_closed_without_semantic_result() -> None:
    result = execute_ordinary_live_authority_consolidation(
        main_run_kernel=None,
        child_run_kernel=None,
        semantic_coverage_result=None,
    )

    assert result.projection["failed_closed"] is True
    assert result.projection["first_failed_seam"] == (
        "ordinary_live_semantic_coverage_result_missing"
    )
    assert result.projection["fetch_read_calls"] == 0
    assert result.projection["model_calls"] == 0


def test_consolidation_runtime_has_no_network_or_acquisition_dispatch() -> None:
    path = ROOT / "core" / "ordinary_live_authority_consolidation_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "dispatch_acquisition" not in call_names
    assert "urlopen" not in call_names
    assert "fetch_page" not in call_names
