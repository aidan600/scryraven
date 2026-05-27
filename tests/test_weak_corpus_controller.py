from __future__ import annotations

import ast
from pathlib import Path

from core.run_controller import RunController
from core.weak_corpus_controller import (
    WEAK_CORPUS_RECOVERY_PROVIDER_ROLE,
    WeakCorpusRecoveryControllerDecision,
    build_weak_corpus_recovery_controller_input,
    decide_weak_corpus_recovery,
    record_weak_corpus_recovery_decision,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "weak_corpus_controller.py"


def _input(
    *,
    corpus_weak: bool = True,
    max_iterations: int = 2,
    prior_attempted: bool = False,
    readable_passage_count: int = 2,
    recovery_queries: list[str] | None = None,
):
    return build_weak_corpus_recovery_controller_input(
        corpus_state="OFF_TOPIC" if corpus_weak else "HEALTHY",
        corpus_weak=corpus_weak,
        iteration=1,
        max_iterations=max_iterations,
        prior_attempted=prior_attempted,
        readable_passage_count=readable_passage_count,
        recovery_queries=recovery_queries
        if recovery_queries is not None
        else [
            "Acme Widget pricing policy deployment official",
            "Acme Widget pricing policy deployment official",
            "Acme Widget official release notes",
        ],
    )


def test_controller_approves_weak_corpus_recovery_from_compact_snapshot() -> None:
    snapshot = _input()
    decision = decide_weak_corpus_recovery(snapshot)

    assert decision.decision is (
        WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY
    )
    assert decision.to_dict()["decision"] == "run_weak_corpus_recovery"
    assert decision.reason == "weak_corpus_first_pass"
    assert decision.blockers == ()
    assert decision.queries == (
        "Acme Widget pricing policy deployment official",
        "Acme Widget official release notes",
    )

    controller = RunController()
    trace = record_weak_corpus_recovery_decision(
        controller,
        snapshot=snapshot,
        decision=decision,
    )
    ledger = controller.snapshot_ledger()
    action = ledger["retrieval_actions"][0]

    assert trace == {
        "weak_corpus_recovery_decision": "run_weak_corpus_recovery",
        "weak_corpus_recovery_reason": "weak_corpus_first_pass",
        "weak_corpus_recovery_blockers": [],
    }
    assert action["name"] == "weak_corpus_recovery"
    assert action["provider_role"] == WEAK_CORPUS_RECOVERY_PROVIDER_ROLE
    assert action["metadata"]["execution"] == (
        "controller_approved_pending_orchestrator"
    )
    assert ledger["decision_records"][0]["name"] == "run_weak_corpus_recovery"


def test_controller_returns_no_action_for_healthy_corpus() -> None:
    decision = decide_weak_corpus_recovery(_input(corpus_weak=False))

    assert decision.decision is WeakCorpusRecoveryControllerDecision.NO_ACTION
    assert decision.to_dict()["decision"] == "no_action"
    assert decision.reason == "not_weak_corpus"
    assert decision.blockers == ()
    assert decision.queries == ()


def test_controller_blocks_fast_no_budget_behavior_with_existing_reason() -> None:
    decision = decide_weak_corpus_recovery(_input(max_iterations=1))

    assert decision.decision is (
        WeakCorpusRecoveryControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.to_dict()["decision"] == "blocked_with_reason"
    assert decision.reason == "max_iterations_1"
    assert "max_iterations_1" in decision.blockers
    assert decision.queries


def test_weak_corpus_controller_static_import_guard() -> None:
    tree = ast.parse(_CONTROLLER_PATH.read_text(encoding="utf-8"))
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
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.source_class_recovery_controller",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]

    assert violations == []
