from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_SUFFICIENT,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.ordinary_continuation_candidate import (
    ORDINARY_CONTINUATION_TRACE_KEY,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
    is_bounded_evaluator_continuation_candidate,
    is_bounded_expander_continuation_candidate,
    is_bounded_scout_continuation_candidate,
)
from core.ordinary_continuation_spine_gate import (
    ScoutContinuationSpineGateFacts,
    authorize_scout_continuation_spine_gate,
    build_scout_continuation_spine_pregate,
)
from tests.test_evidence_integration_conflict_gate_ag37b import _decision
from tests.test_expander_continuation_spine_gate_ag45a import (
    _checkpoint,
    _targeted_lifecycle,
)
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _candidate(
    *,
    queries: tuple[str, ...] = ("Acme Widget benchmark adoption data",),
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=SCOUT_DIRECTED_QUERIES,
        ordinary_next_queries=queries,
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
    ).to_dict()


def _blocked_lifecycle(reason: str) -> dict[str, Any]:
    return {
        "targeted_retrieval_candidate_considered": True,
        "targeted_retrieval_candidate_eligible": False,
        "targeted_retrieval_candidate_used": False,
        "targeted_retrieval_candidate_reason": reason,
        "targeted_retrieval_candidate_skip_reason": reason,
        "targeted_retrieval_candidate_blockers": [reason],
        "targeted_retrieval_candidate_queries": [
            "Acme Widget benchmark adoption data"
        ],
        "targeted_retrieval_candidate_query_provenance": SCOUT_DIRECTED_QUERIES,
        "targeted_retrieval_candidate_conflict_resolving_queries": [],
    }


def test_ag45c_scout_candidate_is_bounded_without_relabeling_other_lanes() -> None:
    scout = _candidate()

    assert is_bounded_scout_continuation_candidate(scout) is True
    assert is_bounded_evaluator_continuation_candidate(scout) is False
    assert is_bounded_expander_continuation_candidate(scout) is False


def test_ag45c_spine_authorizes_bounded_scout_retrieve_targeted() -> None:
    facts = ScoutContinuationSpineGateFacts.from_traces(
        scout_queries=("Acme Widget benchmark adoption data",),
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
        targeted_retrieval_lifecycle_trace=_targeted_lifecycle(
            queries=("Acme Widget benchmark adoption data",)
        ),
    )

    output = authorize_scout_continuation_spine_gate(facts)

    assert output.authorized is True
    assert output.authorized_queries == ["Acme Widget benchmark adoption data"]
    assert output.scout_continuation_spine_gate_trace["reason"] == (
        "bounded_scout_continuation_authorized"
    )
    assert output.scout_continuation_spine_gate_trace[
        "targeted_retrieval_executor_dispatched"
    ] is False
    assert output.ordinary_continuation_candidate_trace["source_path"] == (
        SCOUT_DIRECTED_QUERIES
    )
    assert output.ordinary_continuation_candidate_trace["used"] is True


def test_ag45c_scout_pregate_keeps_lifecycle_required() -> None:
    facts = ScoutContinuationSpineGateFacts.from_traces(
        scout_queries=("Acme Widget benchmark adoption data",),
        prior_queries=("Acme Widget overview",),
        current_iteration=1,
        max_iterations=2,
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        checkpoint_handoff={"action_name": RETRIEVE_TARGETED},
        source_class_lifecycle_trace={},
    )

    pregate = build_scout_continuation_spine_pregate(facts)

    assert pregate.ordinary_continuation_candidate_trace["source_path"] == (
        SCOUT_DIRECTED_QUERIES
    )
    assert (
        pregate.controller_loop_spine_result.dispatch_authorization.authorized_action_name
        is None
    )


def test_ag45c_runtime_scout_uses_authorized_queries_only(
    tmp_path: Path,
) -> None:
    scout_queries = (
        "Acme Widget benchmark adoption data",
        "Acme Widget benchmark support matrix",
    )
    outcome, harness = _run_passive_case(
        tmp_path,
        router_report_type="quantitative_comparison",
        scout_queries=scout_queries,
    )
    trace = outcome.execution_trace
    gate_trace = trace["scout_continuation_spine_gate_trace"]
    checkpoint_packet = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == list(scout_queries)
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert trace["queries_per_iteration"]["2"] == list(scout_queries)
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["source_path"] == (
        SCOUT_DIRECTED_QUERIES
    )
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is True
    assert gate_trace["targeted_retrieval_dispatch_authorized"] is True
    assert gate_trace["targeted_retrieval_executor_dispatched"] is False
    assert gate_trace["authorized_queries"] == list(scout_queries)
    assert gate_trace["authorized_action_name"] == RETRIEVE_TARGETED
    assert checkpoint_packet["scout_continuation_spine_gate_trace"] == gate_trace
    assert checkpoint_packet["targeted_retrieval_authorized_queries"] == list(
        scout_queries
    )
    assert checkpoint_packet["targeted_retrieval_authorized_query_provenance"] == (
        SCOUT_DIRECTED_QUERIES
    )
    assert trace["targeted_retrieval_candidate_used"] is True
    assert "retrieve_targeted" not in [
        call["provider_role"] for call in harness.search_calls
    ]


@pytest.mark.parametrize(
    "checkpoint_action",
    [
        STOP_SUFFICIENT,
        RECOVER_MISSING_SOURCE_CLASS,
        RECOVER_WEAK_CORPUS,
        RESOLVE_CONFLICT,
    ],
)
def test_ag45c_runtime_checkpoint_precedence_blocks_scout_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_action: str,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _decision(checkpoint_action),
    )

    outcome, harness = _run_passive_case(
        tmp_path / checkpoint_action,
        router_report_type="quantitative_comparison",
        scout_queries=("Acme Widget benchmark adoption data",),
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 1
    assert "2" not in trace["queries_per_iteration"]
    assert trace["targeted_retrieval_candidate_used"] is False
    assert trace["scout_continuation_spine_gate_trace"][
        "targeted_retrieval_dispatch_authorized"
    ] is False
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["ordinary_next_queries"] == [
        "Acme Widget benchmark adoption data"
    ]
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is False


def test_ag45c_runtime_lifecycle_blocker_blocks_scout_without_substitute_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "_build_targeted_retrieval_lifecycle_from_runtime",
        lambda **_kwargs: _blocked_lifecycle("blocked_by_source_class_recovery"),
    )

    outcome, harness = _run_passive_case(
        tmp_path,
        router_report_type="quantitative_comparison",
        scout_queries=("Acme Widget benchmark adoption data",),
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 1
    assert "2" not in trace["queries_per_iteration"]
    assert trace["scout_continuation_spine_gate_trace"]["reason"] == (
        "blocked_by_source_class_recovery"
    )
    assert trace["targeted_retrieval_candidate_used"] is False
    assert trace[ORDINARY_CONTINUATION_TRACE_KEY]["used"] is False


def test_ag45c_runtime_absent_scout_directed_queries_do_not_dispatch(
    tmp_path: Path,
) -> None:
    outcome, harness = _run_passive_case(
        tmp_path,
        router_report_type="quantitative_comparison",
        scout_queries=(),
    )
    trace = outcome.execution_trace

    assert len(harness.search_calls) == 1
    assert trace["scout_fired"] is True
    assert trace["scout_queries"] == []
    assert trace["scout_continuation_spine_gate_trace"]["available"] is False
    assert "2" not in trace["queries_per_iteration"]


def test_ag45c_static_protected_surfaces_remain_unpromoted() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")

    assert "execute_retrieve_targeted_action" not in pipeline_source
    assert 'provider_role == "retrieve_targeted"' not in pipeline_source
    assert "provider_role == 'retrieve_targeted'" not in pipeline_source
    assert "ordinary_next_queries=conflict_resolving_queries" not in pipeline_source
    assert "approved_ordinary_next_queries=conflict_resolving_queries" not in (
        pipeline_source
    )
