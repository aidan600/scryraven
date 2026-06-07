from __future__ import annotations

import ast
import json
from pathlib import Path

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    ControllerActionAuthority,
)
from core.controller_runtime_promotion_readiness import (
    assess_runtime_promotion_candidate,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _assert_terminal_stop_promotion(payload: dict[str, object], *, reason: str) -> None:
    assert payload["retrieval_stop_active_available"] is True
    assert payload["retrieval_stop_active_action_name"] == (
        STOP_INSUFFICIENT_WITH_CAVEAT
    )
    assert payload["retrieval_stop_active_authority"] == (
        ControllerActionAuthority.ACTIVE.value
    )
    assert payload["retrieval_stop_active_terminal_branch_reason"] == reason
    assert payload["retrieval_stop_active_approved_query_count"] == 0
    assert payload["retrieval_stop_active_final_answer_posture"] == (
        "answer with caveats"
    )
    assert payload["retrieval_stop_active_ag28_candidate"] == (
        "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
    )
    encoded = json.dumps(payload, sort_keys=True)
    for protected_marker in (
        "raw_prompt",
        "provider_payload",
        "full_trace",
        "db_row",
        "cache",
        "Author handoff",
        "Analyst prompt",
        "Economist packet",
        "Scrutineer rewrite",
    ):
        assert protected_marker not in encoded


def test_ag29_active_no_query_promotes_only_terminal_stop_posture() -> None:
    telemetry = orchestrator._build_retrieval_stop_active_stop_no_queries_telemetry(
        stage="evaluator_no_queries",
        evaluator_sufficient=False,
        iteration=1,
        max_iterations=3,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=[],
        query_source="evaluator",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_no_queries",
        },
    )

    _assert_terminal_stop_promotion(telemetry, reason="no_new_queries")
    assert telemetry["retrieval_stop_active_decision"] == "stop_no_queries"
    assert telemetry["retrieval_stop_active_next_query_count"] == 0
    assert telemetry["retrieval_stop_active_shadow_alignment"] == "aligned"


def test_ag29_active_budget_exhausted_does_not_approve_pending_queries() -> None:
    telemetry = orchestrator._build_retrieval_stop_active_stop_budget_exhausted_telemetry(
        stage="iteration_budget_exhausted",
        evaluator_sufficient=False,
        iteration=2,
        max_iterations=2,
        prior_queries=["Acme Widget rollout evidence"],
        next_queries=["Acme Widget official follow up"],
        query_source="evaluator",
        shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "stop_budget_exhausted",
        },
    )

    _assert_terminal_stop_promotion(
        telemetry,
        reason="iteration_budget_exhausted",
    )
    assert telemetry["retrieval_stop_active_decision"] == "stop_budget_exhausted"
    assert telemetry["retrieval_stop_active_next_query_count"] == 1
    assert telemetry["retrieval_stop_active_approved_query_count"] == 0
    assert telemetry["retrieval_stop_active_shadow_alignment"] == "aligned"


def test_ag29_negative_promotion_blockers_remain_for_unpromoted_actions() -> None:
    blocked_actions = {
        RETRIEVE_TARGETED: "requires_retrieval_continuation_authority",
        STOP_SUFFICIENT: "sufficient_synthesis_branch_is_shadow",
        RECOVER_WEAK_CORPUS: "weak_corpus_executor_not_factored_out",
        RECOVER_MISSING_SOURCE_CLASS: "ordinary_evidence_admission_path",
        REQUEST_SOCIAL_SIGNAL_CHECK: "future_placeholder_no_provider_integration",
    }

    for action_name, blocker in blocked_actions.items():
        assessment = assess_runtime_promotion_candidate(action_name)
        assert assessment.plausible_first_promotion_candidate is False
        assert blocker in assessment.blockers


def test_ag29_runtime_patch_is_limited_to_terminal_active_helpers() -> None:
    tree = ast.parse(_ORCHESTRATOR_PATH.read_text(encoding="utf-8"))
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and "retrieval_stop_active" in node.name
    }

    assert function_names == set()
    source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    assert "retrieval_stop_trace_projection" in source
    assert "REQUEST_SOCIAL_SIGNAL_CHECK" not in source
