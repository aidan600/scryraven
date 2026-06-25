from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.component_gap_recovery_runtime import COMPONENT_GAP_RECOVERY_TRACE_KEY
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.run_config import RunDeps
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

RAW_AUTHOR_RESPONSE = (
    "AG_BAL_01_FINAL_REPORT: The official fee and appeal deadline are both "
    "supported by recovered offline evidence."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _BalancedRecoveryHarness(OfflineOrdinaryPipelineHarness):
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
            analyst_response="Analysis is limited to official recovered evidence.",
            logger_name="test_ag_bal_01_component_gap_recovery",
        )

    def deps(self) -> RunDeps:
        deps = super().deps()
        deps.component_gap_recovery_adapter = self.process_search_queries
        return deps

    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) == 1:
            return [
                {
                    "source_id": 1,
                    "title": "Example Filing Program current official filing fee",
                    "url": "https://official.example/fee",
                    "text": (
                        "The Example Filing Program current official filing "
                        "fee is $120 for 2026."
                    ),
                    "score": 0.99,
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "official_current_rules",
                    "_provider": "offline_fake_search",
                }
            ]
        return [
            {
                "source_id": 2,
                "title": "Example Filing Program appeal deadline legal rule",
                "url": "https://official.example/deadline",
                "text": (
                    "The Example Filing Program appeal deadline is calculated "
                    "as 30 calendar days after the notice date."
                ),
                "score": 0.98,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "legal_or_regulatory_text",
                "currentness_signal": "current",
                "_provider": "offline_fake_search",
            }
        ]


class _AdapterAbsentHarness(_BalancedRecoveryHarness):
    def deps(self) -> RunDeps:
        return OfflineOrdinaryPipelineHarness.deps(self)


class _WeakRecoveryHarness(_BalancedRecoveryHarness):
    def build_search_passages(self) -> list[dict[str, Any]]:
        if len(self.search_calls) == 1:
            return super().build_search_passages()
        return [
            {
                "source_id": 3,
                "title": "Secondary discussion of appeal deadlines",
                "url": "https://secondary.example/deadline",
                "text": "A secondary discussion mentions possible deadline timing.",
                "score": 0.75,
                "credibility": 2,
                "source_tier": "secondary",
                "source_class": "secondary_analysis",
                "currentness_signal": "unknown",
                "eligible_for_stronger_obligation": False,
                "_provider": "offline_fake_search",
            }
        ]


def test_ag_bal_01_recovers_one_authorized_component_gap_and_regenerates_author(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _BalancedRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-06-24",
            session_id="ag-bal-01-session",
            run_id="ag-bal-01-run",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert harness.forbidden_live_calls == []
    assert len(harness.search_calls) == 2
    assert harness.search_calls[0]["queries"] == [
        "current official filing fee",
        "appeal deadline legal rule",
    ]
    assert harness.search_calls[1]["queries"] == ["appeal deadline legal rule"]
    assert harness.search_calls[1]["provider_role"] == (
        "component_gap_recovery_offline"
    )
    assert harness.search_calls[1]["search_providers"] == ["offline-fixture"]

    state = captured["run_kernel"].state
    recovery_projection = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]
    latest_recovery = recovery_projection["latest"]
    assert latest_recovery["owner"] == "ComponentGapRecoveryRuntime"
    assert latest_recovery["mode_neutral_primitive"] is True
    assert "Balanced" not in latest_recovery["owner"]
    assert latest_recovery["status"] == "recovered"
    assert latest_recovery["policy"]["policy_label"] == (
        "balanced_single_cycle_offline"
    )
    assert latest_recovery["policy"]["requested_mode"] == "Balanced"
    assert latest_recovery["policy"]["max_cycles"] == 1
    assert latest_recovery["policy"]["offline_only"] is True
    assert latest_recovery["policy"]["existing_candidate_query_only"] is True
    assert latest_recovery["policy"]["provider_live_calls_allowed"] is False
    assert latest_recovery["policy"]["model_generated_query_text_allowed"] is False
    assert latest_recovery["policy"]["accepted_amendments_allowed"] is False
    assert latest_recovery["policy"]["deep_reconciliation_allowed"] is False

    accepted_component_ids = {
        ref["component_id"]
        for ref in state.initial_answer_contract["accepted_answer_component_refs"]
    }
    covered_component_ids = {
        item["answer_component_id"] for item in state.component_coverage_history
    }
    assert covered_component_ids == accepted_component_ids

    assert len(captured["sufficiency_handoffs"]) >= 2
    sufficiency_projection = state.sufficiency_judgment_projection
    semantic_consumption = sufficiency_projection["semantic_consumption"]
    assert semantic_consumption["required_component_count"] == 2
    assert semantic_consumption["covered_component_count"] == 2
    assert semantic_consumption["missing_component_count"] == 0

    query_authority = captured["packet_runtime_scope"]["query_authority"]
    query_plan_trace = query_authority.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    consumption = query_plan_trace["search_work_consumption"]
    assert consumption["version_bound_component_gap_authority_consumed"] is True
    assert consumption["version_bound_component_gap_authorized_query"] == (
        "appeal deadline legal rule"
    )
    metadata = consumption["query_metadata"]["appeal deadline legal rule"]
    assert metadata["version_bound_component_gap_authorized"] is True
    assert not metadata.get("query_text_generated")
    assert not metadata.get("new_executable_query_text_generated")
    assert consumption["behavior_boundary_flags"][
        "new_executable_query_text_generated"
    ] is False
    assert consumption["behavior_boundary_flags"][
        "component_gap_authority_changed_retrieval_queries"
    ] is False

    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert len(harness.author_prompts) == 1
    author_prompt = harness.author_prompts[0]
    assert "appeal deadline legal rule" in author_prompt
    assert "CONTROLLED SEMANTIC CONTEXT" in author_prompt
    assert "2 required components are supported" in author_prompt


def test_ag_bal_01_fails_closed_without_offline_recovery_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _AdapterAbsentHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-06-24",
                session_id="ag-bal-01-no-adapter-session",
                run_id="ag-bal-01-no-adapter-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 1
    state = captured["run_kernel"].state
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "blocked"
    assert latest_recovery["stop_reason"] == "offline_recovery_adapter_absent"
    assert latest_recovery["policy"]["offline_only"] is True
    assert latest_recovery["policy"]["provider_live_calls_allowed"] is False


def test_ag_bal_01_fails_closed_when_recovered_evidence_cannot_cover_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _WeakRecoveryHarness(tmp_path)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )

    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        orchestrator.run_pipeline(
            offline_balanced_run_config(
                query=harness.query,
                current_date="2026-06-24",
                session_id="ag-bal-01-weak-evidence-session",
                run_id="ag-bal-01-weak-evidence-run",
            ),
            harness.deps(),
            NullStatusWriter(),
            CostAccumulator(),
        )

    assert harness.forbidden_live_calls == []
    assert harness.author_prompts == []
    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == ["appeal deadline legal rule"]
    state = captured["run_kernel"].state
    latest_recovery = state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY]["latest"]
    assert latest_recovery["status"] == "attempted_no_coverage"
    assert latest_recovery["stop_reason"] == (
        "recovered_evidence_not_semantically_covering_gap"
    )
    semantic_consumption = state.sufficiency_judgment_projection[
        "semantic_consumption"
    ]
    assert semantic_consumption["required_component_count"] == 2
    assert semantic_consumption["covered_component_count"] == 1
    assert semantic_consumption["missing_component_count"] == 1
