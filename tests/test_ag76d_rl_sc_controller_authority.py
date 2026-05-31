from __future__ import annotations

import ast
from pathlib import Path

from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
CONTROLLER = ROOT / "core" / "retrieval_stop_controller.py"


def _decision(**overrides: object) -> RetrievalStopControllerDecision:
    base = {
        "evaluator_sufficient": False,
        "iteration": 1,
        "max_iterations": 2,
        "prior_queries": ["Acme Widget pricing policy deployment official"],
        "next_queries": ["Acme Widget migration support lifecycle"],
        "query_source": "evaluator",
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_completed": False,
    }
    base.update(overrides)
    return decide_retrieval_stop(
        build_retrieval_stop_controller_input(**base)  # type: ignore[arg-type]
    ).decision


def test_ag76d_rl_sc_retrieval_stop_decision_parity_table() -> None:
    cases = [
        (
            "evaluator_sufficient",
            {"evaluator_sufficient": True, "next_queries": ["unused query"]},
            RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS,
        ),
        (
            "no next queries",
            {"next_queries": []},
            RetrievalStopControllerDecision.STOP_NO_QUERIES,
        ),
        (
            "iteration >= max_iterations",
            {"iteration": 2, "max_iterations": 2},
            RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED,
        ),
        (
            "redundant next queries",
            {"next_queries": ["Acme Widget pricing policy deployment official docs"]},
            RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES,
        ),
        (
            "weak-corpus recovery completed",
            {
                "evaluator_sufficient": None,
                "iteration": 2,
                "max_iterations": 3,
                "next_queries": ["post recovery query"],
                "weak_corpus_recovery_used": True,
            },
            RetrievalStopControllerDecision.STOP_AFTER_RECOVERY,
        ),
        (
            "viable next queries under budget",
            {"next_queries": ["Acme Widget migration support lifecycle"]},
            RetrievalStopControllerDecision.CONTINUE_RETRIEVAL,
        ),
    ]

    for _label, overrides, expected in cases:
        assert _decision(**overrides) is expected


def test_ag76d_rl_sc_orchestrator_target_branches_consume_controller_decision() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    assert "RetrievalStopControllerDecision" in source
    assert "evaluator_stop_decision = _decide_retrieval_stop_for_active" in source
    assert "budget_stop_decision = _decide_retrieval_loop_stop_continue" in source
    assert "pre_search_stop_decision = _decide_retrieval_loop_stop_continue" in source
    assert "recovery_stop_decision = _decide_retrieval_loop_stop_continue" in source

    old_local_decision_fragments = (
        "if not evaluator_next_queries:",
        "and jaccard_similarity(\n                            queries_by_iteration.get(1, []),",
        "actual_decision=\"stop_no_queries\"",
        "actual_decision=\"stop_redundant_queries\"",
        "actual_decision=\"stop_budget_exhausted\"",
        "actual_decision=\"stop_after_recovery\"",
    )
    for fragment in old_local_decision_fragments:
        assert fragment not in source


def _fake_loop_action(
    *,
    evaluator_sufficient: bool | None = False,
    iteration: int = 1,
    max_iterations: int = 2,
    prior_queries: list[str] | None = None,
    next_queries: list[str] | None = None,
    weak_corpus_recovery_used: bool = False,
) -> str:
    decision = decide_retrieval_stop(
        build_retrieval_stop_controller_input(
            evaluator_sufficient=evaluator_sufficient,
            iteration=iteration,
            max_iterations=max_iterations,
            prior_queries=prior_queries or ["Acme Widget pricing policy deployment official"],
            next_queries=next_queries or [],
            query_source="evaluator",
            weak_corpus_recovery_used=weak_corpus_recovery_used,
        )
    )
    if decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL:
        return f"schedule:{'|'.join(decision.next_queries)}"
    if decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS:
        return "synthesize"
    return f"stop:{decision.decision.value}"


def test_ag76d_rl_sc_offline_fake_loop_uses_controller_for_terminal_and_continue_paths() -> None:
    assert _fake_loop_action(next_queries=[]) == "stop:stop_no_queries"
    assert _fake_loop_action(
        next_queries=["Acme Widget pricing policy deployment official docs"]
    ) == "stop:stop_redundant_queries"
    assert _fake_loop_action(
        evaluator_sufficient=True,
        next_queries=["unused follow-up"],
    ) == "synthesize"
    assert _fake_loop_action(
        iteration=2,
        max_iterations=2,
        next_queries=["Acme Widget migration support lifecycle"],
    ) == "stop:stop_budget_exhausted"
    assert _fake_loop_action(
        next_queries=["Acme Widget migration support lifecycle"]
    ) == "schedule:Acme Widget migration support lifecycle"


def test_ag76d_rl_sc_protected_surface_guardrails() -> None:
    controller_source = CONTROLLER.read_text(encoding="utf-8")
    forbidden_controller_terms = (
        "select_providers",
        "choose_retrieval_search_depth",
        "process_search_queries",
        "ask_model",
        "DEFAULT_SYSTEM",
        "author",
        "citation",
        "provider=",
        "search_depth",
    )
    for term in forbidden_controller_terms:
        assert term not in controller_source

    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))
    controller_adapter_functions = {
        "_record_retrieval_stop_shadow_once",
        "_decide_retrieval_loop_stop_continue",
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in controller_adapter_functions:
            adapter_source = ast.get_source_segment(
                PIPELINE.read_text(encoding="utf-8"), node
            ) or ""
            for term in (
                "select_providers(",
                "choose_retrieval_search_depth(",
                "process_search_queries(",
                "ask_model(",
                "DEFAULT_SYSTEM",
            ):
                assert term not in adapter_source
