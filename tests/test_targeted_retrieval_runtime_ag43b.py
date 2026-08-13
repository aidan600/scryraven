from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_SUFFICIENT,
)
from core.controller_loop_spine import (
    ControllerLoopDispatchAuthorization,
)
from core.cost_accounting import CostAccumulator
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig
from core.targeted_retrieval_controller import TARGETED_RETRIEVAL_TRACE_FIELDS
from tests.test_retrieval_stop_shadow import _ShadowHarness
from tests.test_source_class_recovery_trace import _run_case as _run_source_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


class _PassiveTargetedHarness(_ShadowHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        router_report_type: str = "general_research",
        scout_queries: tuple[str, ...] = (),
        expander_queries: tuple[str, ...] = (),
        evaluator_responses: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            tmp_path,
            evaluator_responses=evaluator_responses,
        )
        self.router_report_type = router_report_type
        self.scout_queries = tuple(scout_queries)
        self.expander_queries = tuple(expander_queries)

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        stage = self._stage_for(system_prompt, kwargs)
        self.model_stage_calls.append(stage)
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": self.router_report_type,
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": "product",
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if "research gap detector" in system_prompt:
            return json.dumps(
                {
                    "component_queries": list(self.expander_queries),
                    "reasoning": "ordinary component gap",
                }
            )
        return super().ask_model(prompt, system_prompt, **kwargs)

    def deps(self) -> Any:
        deps = super().deps()
        deps.QUANT_REPORT_TYPES = {"benchmark", "legal_analysis"}
        return deps


def _run_passive_case(
    tmp_path: Path,
    **harness_kwargs: Any,
) -> tuple[Any, _PassiveTargetedHarness]:
    harness = _PassiveTargetedHarness(tmp_path, **harness_kwargs)
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-05-20",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, harness


@pytest.mark.parametrize(
    ("name", "harness_kwargs", "expected_provenance"),
    [
        (
            "evaluator",
            {
                "evaluator_responses": [
                    {
                        "is_sufficient": False,
                        "new_queries": [
                            "Acme Widget migration timeline",
                            "Acme Widget support matrix",
                        ],
                    }
                ],
            },
            "evaluator_next_queries",
        ),
        (
            "expander",
            {
                "expander_queries": (
                    "Acme Widget component warranty evidence",
                    "Acme Widget component rollout evidence",
                ),
            },
            "expander_component_queries",
        ),
        (
            "scout",
            {
                "router_report_type": "quantitative_comparison",
                "scout_queries": (
                    "Acme Widget benchmark adoption data",
                    "Acme Widget benchmark support matrix",
                ),
            },
            "scout_directed_queries",
        ),
    ],
)
def test_ag43b_runtime_observes_ordinary_next_queries_passively(
    tmp_path: Path,
    name: str,
    harness_kwargs: dict[str, Any],
    expected_provenance: str,
) -> None:
    outcome, harness = _run_passive_case(tmp_path / name, **harness_kwargs)
    trace = outcome.execution_trace

    assert trace["targeted_retrieval_candidate_considered"] is True
    assert trace["targeted_retrieval_candidate_used"] is (
        expected_provenance
        in {
            "evaluator_next_queries",
            "expander_component_queries",
            "scout_directed_queries",
        }
    )
    assert trace["targeted_retrieval_candidate_query_provenance"] == (
        expected_provenance
    )
    assert trace["targeted_retrieval_candidate_queries"] == harness.search_calls[1][
        "queries"
    ]
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == []
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]
    assert trace["queries_per_iteration"]["2"] == harness.search_calls[1]["queries"]
    assert set(TARGETED_RETRIEVAL_TRACE_FIELDS) <= set(trace)
    if expected_provenance == "evaluator_next_queries":
        assert trace["evaluator_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
    elif expected_provenance == "expander_component_queries":
        assert trace["expander_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
    else:
        assert trace["scout_continuation_spine_gate_trace"][
            "targeted_retrieval_dispatch_authorized"
        ] is True
        assert trace["evaluator_continuation_spine_gate_trace"]["available"] is False
        assert trace["expander_continuation_spine_gate_trace"]["available"] is False


def test_ag43b_expander_gate_blocks_when_targeted_lifecycle_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness_kwargs = {
        "expander_queries": ("Acme Widget migration timeline",),
    }
    active_outcome, active_harness = _run_passive_case(
        tmp_path / "active",
        **harness_kwargs,
    )
    monkeypatch.setattr(
        orchestrator,
        "_build_targeted_retrieval_lifecycle_from_runtime",
        lambda **_kwargs: orchestrator.targeted_retrieval_lifecycle_defaults(),
    )
    baseline_outcome, baseline_harness = _run_passive_case(
        tmp_path / "baseline",
        **harness_kwargs,
    )

    assert len(active_harness.search_calls) == 2
    assert len(baseline_harness.search_calls) == 1
    assert active_outcome.execution_trace["targeted_retrieval_candidate_used"] is True
    assert (
        baseline_outcome.execution_trace["targeted_retrieval_candidate_used"]
        is False
    )
    assert baseline_outcome.execution_trace[
        "expander_continuation_spine_gate_trace"
    ]["targeted_retrieval_dispatch_authorized"] is False
    assert "2" not in baseline_outcome.execution_trace["queries_per_iteration"]


def test_ag43b_source_class_currentness_gap_blocks_passive_targeted_lifecycle(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_source_case(
        tmp_path,
        query=(
            "What are the current eligibility requirements and official rules "
            "for the care program?"
        ),
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )
    trace = outcome.execution_trace

    assert trace["targeted_retrieval_candidate_used"] is False
    assert trace["targeted_retrieval_candidate_eligible"] is False
    assert "blocked_by_source_class_recovery" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert trace["targeted_retrieval_candidate_currentness_gap_detected"] is True
    assert trace["targeted_retrieval_candidate_official_current_source_gap"] is True
    assert (
        trace[
            "targeted_retrieval_candidate_reputable_news_or_primary_update_needed"
        ]
        is True
    )
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag43b_weak_corpus_blocks_passive_targeted_lifecycle(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_weak_corpus_case(tmp_path)
    trace = outcome.execution_trace

    assert trace["weak_corpus_recovery_used"] is True
    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_weak_corpus_recovery" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_call_details
    ]


def test_ag43b_terminal_stop_blocks_passive_targeted_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_evidence_integration_conflict_gate_ag37b import _decision

    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(STOP_SUFFICIENT),
    )
    outcome, harness = _run_passive_case(
        tmp_path,
        evaluator_responses=[
            {
                "is_sufficient": False,
                "new_queries": ["Acme Widget migration timeline"],
            }
        ],
    )
    trace = outcome.execution_trace

    assert trace["targeted_retrieval_candidate_used"] is False
    assert "blocked_by_terminal_stop" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag43d_forced_retrieve_targeted_checkpoint_does_not_dispatch_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_evidence_integration_conflict_gate_ag37b import _decision

    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(RETRIEVE_TARGETED),
    )
    outcome, harness = _run_passive_case(
        tmp_path,
        expander_queries=("Acme Widget migration timeline",),
    )
    trace = outcome.execution_trace
    checkpoint_packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    authorization = ControllerLoopDispatchAuthorization.from_trace_packet(
        checkpoint_packet
    )

    assert authorization.authorized_action_name == RETRIEVE_TARGETED
    assert checkpoint_packet["promoted_action_name"] == RETRIEVE_TARGETED
    assert checkpoint_packet["executed_action_name"] is None
    assert checkpoint_packet["targeted_retrieval_gate_active"] is True
    assert checkpoint_packet["targeted_retrieval_lifecycle_eligible"] is True
    assert checkpoint_packet["targeted_retrieval_gate_reason"] == (
        "bounded_expander_continuation_authorized"
    )
    assert checkpoint_packet["targeted_retrieval_dispatch_authorized"] is True
    assert checkpoint_packet["targeted_retrieval_executor_dispatched"] is False
    assert trace["targeted_retrieval_candidate_used"] is True
    assert trace["active_source_class_recovery_used"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["active_conflict_resolution_used"] is False
    assert len(harness.search_calls) == 2
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag43b_conflict_resolution_blocks_without_mixing_query_lanes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_evidence_integration_conflict_gate_ag37b import (
        _inject_conflict_evidence_state,
    )

    _inject_conflict_evidence_state(
        monkeypatch,
        resolving_queries=("Care Program official corrected date",),
        ordinary_next_queries=(),
    )
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: __import__(
            "tests.test_evidence_integration_conflict_gate_ag37b",
            fromlist=["_decision"],
        )._decision(RESOLVE_CONFLICT),
    )
    outcome, harness, _log_entry = _run_source_case(
        tmp_path,
        query="Care Program current official dates conflict",
        core_topic="Care Program current official dates conflict",
        primary_entity="Care Program",
        researcher_query="Care Program current official dates",
    )
    trace = outcome.execution_trace

    assert trace["active_conflict_resolution_used"] is True
    assert "blocked_by_conflict_resolution" in trace[
        "targeted_retrieval_candidate_blockers"
    ]
    assert trace["targeted_retrieval_candidate_queries"] == []
    assert trace["targeted_retrieval_candidate_conflict_resolving_queries"] == [
        "Care Program official corrected date"
    ]
    assert "conflict_resolution" in [
        call["provider_role"] for call in harness.search_calls
    ]
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


def test_ag43b_static_guards_keep_retrieve_targeted_unpromoted() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    spine_source = _SPINE_PATH.read_text(encoding="utf-8")
    spine_tree = ast.parse(spine_source)

    assert "execute_retrieve_targeted_action" not in pipeline_source
    assert 'provider_role == "retrieve_targeted"' not in pipeline_source
    assert "provider_role == 'retrieve_targeted'" not in pipeline_source
    assert ControllerLoopDispatchAuthorization.from_trace_packet(
        {"executed_action_name": "retrieve_targeted"}
    ).authorized_action_name is None
    assert all(
        not (
            isinstance(node, ast.Constant)
            and node.value == "retrieve_targeted"
            and isinstance(getattr(node, "parent", None), ast.Set)
        )
        for node in ast.walk(spine_tree)
    )
