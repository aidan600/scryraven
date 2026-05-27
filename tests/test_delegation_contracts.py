from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from core.delegation_contracts import (
    DelegationAction,
    DelegationMode,
    TaskResult,
    TaskResultStatus,
)

_ROOT = Path(__file__).resolve().parents[1]
_DELEGATION_CONTRACTS_PATH = _ROOT / "core" / "delegation_contracts.py"


def test_delegation_action_is_shadow_and_inert_by_default() -> None:
    action = DelegationAction(
        action_id="action-1",
        task_id="source_class_recovery",
        target_module_id="source_class_recovery",
    )
    payload = action.to_dict()

    assert action.mode is DelegationMode.SHADOW
    assert action.active is False
    assert payload == {
        "action_id": "action-1",
        "task_id": "source_class_recovery",
        "target_module_id": "source_class_recovery",
        "reason": None,
        "mode": "shadow",
        "active": False,
        "metadata": {},
    }
    assert not hasattr(action, "execute")
    assert not hasattr(action, "dispatch")
    assert not hasattr(action, "executor")


def test_task_result_is_structured_but_not_control_flow() -> None:
    result = TaskResult(
        task_id="weak_corpus_recovery",
        module_id="weak_corpus_recovery",
        status=TaskResultStatus.SKIPPED,
        reason="max_iterations_1",
        metadata={"queries": []},
    )

    assert result.to_dict() == {
        "task_id": "weak_corpus_recovery",
        "module_id": "weak_corpus_recovery",
        "status": "skipped",
        "summary": None,
        "reason": "max_iterations_1",
        "metadata": {"queries": []},
    }


def test_delegation_contracts_have_no_callable_fields_or_runtime_hooks() -> None:
    action = DelegationAction(
        action_id="action-1",
        task_id="analyst_review",
        target_module_id="analyst",
    )
    result = TaskResult(task_id="analyst_review", module_id="analyst")

    for record in (action, result):
        for field in fields(record):
            assert not callable(getattr(record, field.name)), field.name
        assert not hasattr(record, "run")
        assert not hasattr(record, "retry")
        assert not hasattr(record, "schedule")


def test_delegation_contracts_static_import_guard() -> None:
    tree = ast.parse(_DELEGATION_CONTRACTS_PATH.read_text(encoding="utf-8"))
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
        "core.routing",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_function_prefixes = (
        "dispatch",
        "execute",
        "recover",
        "retry",
        "route",
        "select",
        "schedule",
    )
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    active_function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_function_prefixes)
    ]
    violations = [
        name
        for name in imports
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    assert violations == []
    assert active_function_names == []
