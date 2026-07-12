from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.query_plan import QUERY_PLAN_TRACE_KEY
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

RAW_AUTHOR_RESPONSE = (
    "AG_GAP_01_FINAL_REPORT: The retrieved official fee evidence is available, "
    "while the deadline component remains unresolved under the offline fixture."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


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


def test_ag_gap_01_offline_path_records_one_gap_authorized_query_without_execution_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _GapHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SEMANTIC, HANDOFF_PACKET),
    )

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
    assert harness.search_calls[0]["queries"] == [
        "current official filing fee",
        "appeal deadline legal rule",
    ]

    state = captured["run_kernel"].state
    assert captured["packet_handoff"].author_input_blocked is True
    assert captured["packet_handoff"].author_payload is None
    assert state.final_answer_authority_projection["author_payload_ref"]["status"] == (
        "blocked"
    )
    assert state.search_judgment_projection["owner"] == (
        "RunKernel.RunAuthoritySearchJudgment"
    )
    semantic_gaps = [
        gap for gap in state.search_judgment_projection["gaps"]
        if gap.get("semantic_gap_code") == "missing_required_component_coverage"
    ]
    assert len(semantic_gaps) == 1

    query_authority = captured["packet_runtime_scope"]["query_authority"]
    query_plan_trace = query_authority.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    consumption = query_plan_trace["search_work_consumption"]
    assert consumption["version_bound_component_gap_authority_consumed"] is True
    assert (
        consumption["version_bound_component_gap_authorized_query"]
        == "appeal deadline legal rule"
    )
    assert consumption["behavior_boundary_flags"][
        "new_executable_query_text_generated"
    ] is False
    assert consumption["behavior_boundary_flags"][
        "component_gap_authority_changed_retrieval_queries"
    ] is False
    assert query_plan_trace["authorized_queries_by_iteration"]["1"] == [
        "current official filing fee",
        "appeal deadline legal rule",
    ]
