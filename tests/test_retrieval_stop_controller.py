from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "retrieval_stop_controller.py"
_WEAK_CORPUS_CONTROLLER_PATH = _ROOT / "core" / "weak_corpus_controller.py"
_SOURCE_CLASS_CONTROLLER_PATH = _ROOT / "core" / "source_class_recovery_controller.py"


def _input(
    *,
    evaluator_sufficient: bool | None = False,
    iteration: int = 1,
    max_iterations: int = 2,
    prior_queries: list[str] | None = None,
    next_queries: list[str] | None = None,
    query_source: str | None = "evaluator",
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
) -> Any:
    return build_retrieval_stop_controller_input(
        evaluator_sufficient=evaluator_sufficient,
        iteration=iteration,
        max_iterations=max_iterations,
        prior_queries=prior_queries
        if prior_queries is not None
        else ["Acme Widget pricing policy deployment official"],
        next_queries=next_queries
        if next_queries is not None
        else ["Acme Widget official release notes"],
        query_source=query_source,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_completed=weak_corpus_recovery_completed,
    )


def test_evaluator_sufficient_proceeds_to_synthesis() -> None:
    decision = decide_retrieval_stop(
        _input(evaluator_sufficient=True, next_queries=["unused follow-up query"])
    )

    assert decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS
    assert decision.to_dict()["decision"] == "proceed_to_synthesis"
    assert decision.reason == "evaluator_sufficient"
    assert decision.next_queries == ()
    assert decision.blockers == ()


def test_evaluator_insufficient_with_new_nonredundant_queries_continues() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=False,
            next_queries=[
                "Acme Widget enterprise deployment migration timeline",
                "Acme Widget support lifecycle documentation",
            ],
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
    assert decision.should_continue is True
    assert decision.reason == "candidate_queries_available"
    assert decision.next_queries == (
        "Acme Widget enterprise deployment migration timeline",
        "Acme Widget support lifecycle documentation",
    )
    assert decision.query_source == "evaluator"


def test_evaluator_insufficient_with_no_new_queries_stops_no_queries() -> None:
    decision = decide_retrieval_stop(
        _input(evaluator_sufficient=False, next_queries=[])
    )

    assert decision.decision is RetrievalStopControllerDecision.STOP_NO_QUERIES
    assert decision.should_stop is True
    assert decision.reason == "no_new_queries"
    assert "no_new_queries" in decision.blockers
    assert decision.next_queries == ()


def test_redundant_queries_stop_retrieval() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=False,
            next_queries=["Acme Widget pricing policy deployment official docs"],
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
    assert decision.reason == "redundant_with_prior_queries"
    assert "redundant_queries" in decision.blockers
    assert decision.redundancy_score is not None
    assert decision.redundancy_score > 0.7
    assert decision.next_queries == ("Acme Widget pricing policy deployment official docs",)


def test_budget_exhausted_stops_retrieval() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=False,
            iteration=2,
            max_iterations=2,
            next_queries=["Acme Widget enterprise deployment migration timeline"],
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED
    assert decision.reason == "iteration_budget_exhausted"
    assert "iteration_budget_exhausted" in decision.blockers
    assert decision.next_queries == ("Acme Widget enterprise deployment migration timeline",)


def test_weak_corpus_recovery_completed_stops_after_recovery() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=None,
            iteration=2,
            max_iterations=3,
            next_queries=["Acme Widget extra post recovery query"],
            weak_corpus_recovery_used=True,
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.STOP_AFTER_RECOVERY
    assert decision.reason == "weak_corpus_recovery_completed"
    assert "weak_corpus_recovery_completed" in decision.blockers
    assert decision.next_queries == ()


def test_scout_directed_queries_remain_continue_candidates() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=None,
            prior_queries=["Northwind revenue outlook"],
            next_queries=[
                "Northwind segment margin bridge filings",
                "Northwind pricing volume mix disclosure",
            ],
            query_source="scout",
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
    assert decision.query_source == "scout"
    assert decision.next_queries == (
        "Northwind segment margin bridge filings",
        "Northwind pricing volume mix disclosure",
    )


def test_expander_component_queries_remain_continue_candidates() -> None:
    decision = decide_retrieval_stop(
        _input(
            evaluator_sufficient=None,
            prior_queries=["Fabrikam data center buildout"],
            next_queries=[
                "Fabrikam power purchase agreement terms",
                "Fabrikam GPU cluster capex disclosures",
            ],
            query_source="expander",
        )
    )

    assert decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
    assert decision.query_source == "expander"
    assert decision.reason == "candidate_queries_available"


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_retrieval_stop_controller_static_import_guard() -> None:
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_quality",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.source_class_recovery_controller",
        "core.weak_corpus_controller",
        "core.weak_corpus_recovery",
    )
    forbidden_terms = (
        "process_search_queries",
        "select_providers",
        "choose_retrieval_search_depth",
        "DEFAULT_SYSTEM",
        "ask_model",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "run_source_class_recovery",
        "run_weak_corpus_recovery",
        "SOURCE_CLASS_RECOVERY_PROVIDER_ROLE",
        "WEAK_CORPUS_RECOVERY_PROVIDER_ROLE",
    )

    violations = [
        name
        for name in _imported_names(_CONTROLLER_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]

    source = _CONTROLLER_PATH.read_text(encoding="utf-8")
    assert violations == []
    assert all(term not in source for term in forbidden_terms)


def test_recovery_controllers_do_not_import_retrieval_stop_controller() -> None:
    forbidden = "core.retrieval_stop_controller"

    assert forbidden not in _imported_names(_WEAK_CORPUS_CONTROLLER_PATH)
    assert forbidden not in _imported_names(_SOURCE_CLASS_CONTROLLER_PATH)
