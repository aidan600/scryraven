from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from core.module_registry import (
    MODULE_REGISTRY,
    ModuleKind,
    get_module_entry,
    get_module_registry,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_REGISTRY_PATH = _ROOT / "core" / "module_registry.py"


def test_module_registry_contains_expected_static_metadata() -> None:
    registry = get_module_registry()
    module_ids = {entry.module_id for entry in registry}

    assert registry == MODULE_REGISTRY
    assert {
        "router",
        "researcher",
        "retrieval",
        "weak_corpus_recovery",
        "source_class_recovery",
        "analyst",
        "economist",
        "scrutineer",
        "author",
        "persistence",
    } <= module_ids

    source_class = get_module_entry("source_class_recovery")
    economist = get_module_entry("economist")
    author = get_module_entry("author")
    persistence = get_module_entry("persistence")

    assert source_class.module_kind is ModuleKind.RECOVERY_STAGE
    assert "eligibility" in " ".join(source_class.safety_constraints)
    assert "Cannot execute code." in economist.safety_constraints
    assert "Cannot bypass Analyst." in economist.safety_constraints
    assert any("raw quantitative_packet" in item for item in author.safety_constraints)
    assert "RUN_COLUMNS" in " ".join(persistence.safety_constraints)


def test_module_registry_has_no_callables_or_runtime_hooks() -> None:
    for entry in get_module_registry():
        for field in fields(entry):
            value = getattr(entry, field.name)
            assert not callable(value), (entry.module_id, field.name)
        assert not hasattr(entry, "dispatch")
        assert not hasattr(entry, "execute")
        assert not hasattr(entry, "executor")
        assert not hasattr(entry, "scheduler")


def test_module_registry_serialization_is_static() -> None:
    payload = get_module_entry("analyst").to_dict()

    assert payload["module_id"] == "analyst"
    assert payload["module_kind"] == "model_stage"
    assert payload["future_delegation_allowed"] is True
    assert payload["allowed_side_effects"] == [
        "model_call_already_owned_by_orchestrator"
    ]


def test_module_registry_static_import_guard() -> None:
    tree = ast.parse(_MODULE_REGISTRY_PATH.read_text(encoding="utf-8"))
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
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    violations = [
        name
        for name in imports
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    assert violations == []
