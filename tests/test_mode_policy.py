from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.mode_policy import RunMode, mode_policy_for, normalize_mode

_ROOT = Path(__file__).resolve().parents[1]
_MODE_POLICY_PATH = _ROOT / "core" / "mode_policy.py"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            "Fast",
            {
                "mode": "Fast",
                "complexity": "low",
                "search_depth": "basic",
                "max_queries": 2,
                "results_per_query": 5,
                "top_chunks": 8,
                "max_iterations": 1,
            },
        ),
        (
            "Balanced",
            {
                "mode": "Balanced",
                "complexity": "medium",
                "search_depth": "basic",
                "max_queries": 2,
                "results_per_query": 6,
                "top_chunks": 20,
                "max_iterations": 2,
            },
        ),
        (
            "Deep",
            {
                "mode": "Deep",
                "complexity": "high",
                "search_depth": "advanced",
                "max_queries": 3,
                "results_per_query": 8,
                "top_chunks": 40,
                "max_iterations": 3,
            },
        ),
    ],
)
def test_mode_policy_parity_with_existing_mode_assignments(
    mode: str,
    expected: dict[str, object],
) -> None:
    assert mode_policy_for(mode).to_dict() == expected


def test_mode_policy_normalizes_known_ui_modes_only() -> None:
    assert normalize_mode(" fast ") is RunMode.FAST
    assert normalize_mode("BALANCED") is RunMode.BALANCED
    assert normalize_mode(RunMode.DEEP) is RunMode.DEEP

    with pytest.raises(ValueError):
        normalize_mode("Turbo")


def test_mode_policy_static_import_guard() -> None:
    tree = ast.parse(_MODE_POLICY_PATH.read_text(encoding="utf-8"))
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
