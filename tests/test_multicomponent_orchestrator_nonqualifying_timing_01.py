"""Orchestrator-level regression: nonqualifying direct-producer timing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.legacy_review_runtime_stage as legacy_review_runtime_stage
import core.ordinary_multicomponent_synthesis_runtime as multicomponent_runtime
import core.ordinary_semantic_producer_runtime as semantic_producer_runtime
import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

ONE_COMPONENT_QUERY = "What is the Example Program current official rule?"

SIX_COMPONENT_QUERY = """For the fictional Example Program:
- What is the base rebate amount?
- What is the application deadline?
- Who qualifies for the income-based bonus?
- Must bonus applicants use the paper application?
- Can ordinary applicants file online?
- What agency publishes the official rule?

Then explain how these facts relate for an eligible applicant."""


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _TimingHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path, *, query: str, component_count: int) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=query,
            core_topic="Example Program",
            primary_entity="Example Program",
            researcher_queries=tuple(
                f"Example Program fact {index}" for index in range(1, component_count + 1)
            ),
            raw_author_response=(
                "Example Program remains governed by the retrieved official rule."
            ),
            logger_name=f"test_multicomponent_orchestrator_timing_{component_count}",
        )
        self.component_count = component_count

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": index,
                "title": f"Example Program fact {index}",
                "url": f"https://official.example/fact-{index}",
                "text": (
                    f"Example Program official current rule fact {index} "
                    "remains in effect for eligible applicants."
                ),
                "score": 1.0 - (index * 0.01),
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "readable_status": "readable",
                "_provider": "offline_fake_search",
            }
            for index in range(1, self.component_count + 1)
        ]


@pytest.mark.parametrize(
    ("component_count", "query"),
    [
        (1, ONE_COMPONENT_QUERY),
        (6, SIX_COMPONENT_QUERY),
    ],
)
def test_orchestrator_nonqualifying_defers_direct_producer_until_post_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component_count: int,
    query: str,
) -> None:
    harness = _TimingHarness(
        tmp_path,
        query=query,
        component_count=component_count,
    )
    producer_calls: list[dict[str, Any]] = []
    handoff_calls: list[dict[str, Any]] = []
    review_completed = {"value": False}
    post_review_evidence_marker = {"marker": f"post-review-{component_count}"}

    real_producer = (
        multicomponent_runtime.execute_ordinary_semantic_producer_handoff_from_scope
    )

    def tracked_producer(run_kernel: Any, runtime_scope: Any) -> Any:
        evidence = runtime_scope.get("final_top_evidence")
        producer_calls.append(
            {
                "review_completed": review_completed["value"],
                "final_top_evidence": evidence,
                "sees_post_review_marker": (
                    isinstance(evidence, list)
                    and post_review_evidence_marker in evidence
                ),
            }
        )
        return real_producer(run_kernel, runtime_scope)

    monkeypatch.setattr(
        multicomponent_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        tracked_producer,
    )
    monkeypatch.setattr(
        semantic_producer_runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        tracked_producer,
    )

    real_handoff = (
        orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
    )

    def tracked_handoff(
        run_kernel: Any,
        runtime_scope: Any,
        *,
        execute_selected_lane: bool = True,
    ) -> Any:
        if not execute_selected_lane:
            seam = "early_selection"
        elif review_completed["value"]:
            seam = "post_review"
        else:
            seam = "pre_analyst"
        before = len(producer_calls)
        result = real_handoff(
            run_kernel,
            runtime_scope,
            execute_selected_lane=execute_selected_lane,
        )
        handoff_calls.append(
            {
                "seam": seam,
                "execute_selected_lane": execute_selected_lane,
                "producer_calls": len(producer_calls) - before,
                "path_selected": multicomponent_runtime.ordinary_multicomponent_path_selected(
                    run_kernel
                ),
            }
        )
        return result

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
        tracked_handoff,
    )

    real_review = (
        legacy_review_runtime_stage.execute_legacy_review_runtime_stage_from_scope
    )

    def tracked_review(*args: Any, **kwargs: Any) -> Any:
        outcome = real_review(*args, **kwargs)
        review_completed["value"] = True
        return outcome

    monkeypatch.setattr(
        legacy_review_runtime_stage,
        "execute_legacy_review_runtime_stage_from_scope",
        tracked_review,
    )

    from dataclasses import replace

    real_evidence_handoff = orchestrator.final_evidence_handoff_from_legacy_review

    def tracked_evidence_handoff(*args: Any, **kwargs: Any) -> Any:
        handoff = real_evidence_handoff(*args, **kwargs)
        stamped = list(handoff.final_top_evidence or ())
        stamped.append(post_review_evidence_marker)
        return replace(handoff, final_top_evidence=stamped)

    monkeypatch.setattr(
        orchestrator,
        "final_evidence_handoff_from_legacy_review",
        tracked_evidence_handoff,
    )

    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-10",
            session_id=f"timing-session-{component_count}",
            run_id=f"timing-run-{component_count}",
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.report
    assert harness.forbidden_live_calls == []

    early = [item for item in handoff_calls if item["seam"] == "early_selection"]
    pre_analyst = [item for item in handoff_calls if item["seam"] == "pre_analyst"]
    post_review = [item for item in handoff_calls if item["seam"] == "post_review"]

    assert early, "expected early selection-only handoff"
    assert all(item["producer_calls"] == 0 for item in early)
    assert all(item["execute_selected_lane"] is False for item in early)

    # Nonqualifying runs must not invoke the combined handoff (and therefore
    # must not invoke the direct producer) at the pre-Analyst seam.
    assert pre_analyst == []
    assert sum(item["producer_calls"] for item in pre_analyst) == 0

    assert len(post_review) >= 1
    assert sum(item["producer_calls"] for item in post_review) == 1
    assert len(producer_calls) == 1
    assert producer_calls[0]["review_completed"] is True
    assert producer_calls[0]["sees_post_review_marker"] is True
