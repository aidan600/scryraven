from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.searchos_iterative_judgment_runtime import (
    SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED,
)
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

RAW_AUTHOR_RESPONSE = (
    "AG_GAP_01_FINAL_REPORT: The retrieved official fee evidence is available, "
    "while the deadline component remains unresolved under the offline fixture."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(
        monkeypatch,
        available_search_providers=("linkup",),
    )


class _GapHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=(
                "What is the current official filing fee and how is the "
                "appeal deadline calculated?"
            ),
            core_topic="official filing fee and appeal deadline",
            primary_entity="Example Filing Program",
            researcher_queries=(
                "current official filing fee",
                "appeal deadline legal rule",
            ),
            raw_author_response=RAW_AUTHOR_RESPONSE,
            analyst_response="Analysis is limited to the retrieved fee evidence.",
            logger_name="test_ag_gap_01_offline_product_path",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 1,
                "title": "Example Filing Program current official filing fee",
                "url": "https://official.example/fee",
                "text": (
                    "The Example Filing Program current official filing fee is "
                    "$120 for 2026."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            }
        ]


def test_ag_gap_01_offline_path_stops_at_searchos_slice_a_required_needs_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _GapHarness(tmp_path)

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-gap-01-session",
            run_id="ag-gap-01-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    terminal = (outcome.execution_trace or {}).get("blocked_fap_terminal") or {}
    assert terminal.get("blocked_fap") is True
    assert terminal.get("author_called") is False

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 1
    trace = outcome.execution_trace or {}
    searchos = trace["searchos_slice_a"]
    assert searchos["required_needs_block_ref"]["block_type"] == (
        SEARCHOS_SLICE_A_REQUIRED_NEEDS_UNRESOLVED
    )
    assert searchos["readiness_projection"]["all_required_slots_slice_a_ready"] is False
    assert searchos["iteration_candidate_set_refs"] == []
    assert searchos["readiness_projection"]["unresolved_required_slots"]
    assert searchos["evaluator_invoked_after_first_wave"] is False
    assert searchos["expander_invoked_after_first_wave"] is False
    assert searchos["disambiguation_invoked_after_first_wave"] is False
    assert searchos["weak_corpus_recovery_invoked_after_first_wave"] is False
