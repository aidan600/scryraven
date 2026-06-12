from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRIMARY_FIXTURES = [
    ROOT / "tests" / "test_source_class_recovery_live_offline_dispatch_parity_ag68e.py",
    ROOT / "tests" / "test_source_class_recovery_live_product_dispatch_callsite_ag68g.py",
    ROOT / "tests" / "test_authority_lifecycle_execution_ag69c.py",
]

CURRENT_GUIDANCE = [
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
    ROOT / "docs" / "codex" / "CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md",
]

SUPERSEDED_DOCS = [
    ROOT / "docs" / "validation" / "AG68E_LIVE_OFFLINE_DISPATCH_PARITY_REPAIR.md",
    ROOT
    / "docs"
    / "validation"
    / "AG69F_CONTROLLER_LIFECYCLE_FORCED_CORRIDOR_VALIDATION.md",
    ROOT / "docs" / "architecture" / "AG74F_RECOVERY_RUNNER_EXTRACTION.md",
    ROOT / "docs" / "architecture" / "AG79C_ORCHESTRATOR_DECISION_AUDIT.md",
    ROOT / "docs" / "architecture" / "AG79D_TARGETED_ORCHESTRATOR_AUTHORITY_CLOSURE.md",
    ROOT
    / "docs"
    / "architecture"
    / "AG94H_C_RECOVERY_EXECUTOR_DISPATCH_AUTHORIZATION_AUDIT.md",
    ROOT
    / "docs"
    / "architecture"
    / "AG94H_D_RECOVERY_DISPATCH_AUTHORIZATION_REPAIR.md",
    ROOT
    / "docs"
    / "architecture"
    / "AG94H_E_AUTHORITY_LIFECYCLE_SOURCE_CLASS_PARITY_AUDIT.md",
    ROOT
    / "docs"
    / "architecture"
    / "AG94H_F_AUTHORITY_CUSTODY_SEMANTICS_REPAIR.md",
    ROOT
    / "docs"
    / "architecture"
    / "AG95A_AUTHORITY_SURFACE_INVENTORY_AND_DEMOLITION_PLAN.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_read(path))


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def test_ag95e_primary_fixtures_dispatch_source_class_through_runner() -> None:
    for path in PRIMARY_FIXTURES:
        source = _read(path)
        tree = _tree(path)

        assert "run_source_class_recovery_dispatch(" in source, path.name
        assert "SourceClassRecoveryRunnerContext(" in source, path.name

        direct_executor_imports = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "core.source_class_recovery_executor"
        ]
        assert direct_executor_imports == [], path.name

        direct_executor_calls = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and _call_name(node) == "execute_source_class_recovery_action"
        ]
        assert direct_executor_calls == [], path.name

        stale_helper_args = [
            (node.name, arg.arg)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            for arg in [*node.args.args, *node.args.kwonlyargs]
            if arg.arg == "authorized_spine_action"
        ]
        assert stale_helper_args == [], path.name

        source_class_spine_gates = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            left_is_spine_action = (
                isinstance(node.left, ast.Name)
                and node.left.id == "authorized_spine_action"
            )
            compares_to_source_class = any(
                isinstance(comparator, ast.Name)
                and comparator.id == "RECOVER_MISSING_SOURCE_CLASS"
                for comparator in node.comparators
            )
            if left_is_spine_action and compares_to_source_class:
                source_class_spine_gates.append(node.lineno)

        assert source_class_spine_gates == [], path.name


def test_ag95e_current_guidance_names_canonical_source_class_dispatch() -> None:
    for path in CURRENT_GUIDANCE:
        text = _read(path)

        assert "SourceClassRecoveryRunner" in text, path.name
        assert "authority_lifecycle.recovery_action" in text, path.name
        assert "diagnostic" in text, path.name
        assert "compatibility" in text, path.name


def test_ag95e_superseded_dispatch_docs_are_bannered() -> None:
    for path in SUPERSEDED_DOCS:
        text = _read(path)
        normalized = " ".join(text.replace(">", "").split())

        assert "Status note, AG-95E" in text, path.name
        assert "authority_lifecycle.recovery_action" in text, path.name
        assert "not runner" in normalized, path.name
        assert "authority" in normalized, path.name


def test_ag95e_phase_record_exists_and_records_search_classification() -> None:
    text = _read(
        ROOT
        / "docs"
        / "architecture"
        / "AG95E_STALE_DISPATCH_DOCTRINE_AND_FIXTURE_CLEANUP.md"
    )

    assert "Search Classification" in text
    assert "Stale test/fixture scaffolding" in text
    assert "Current runtime code that remains valid" in text
    assert "False positive/no matches" in text
