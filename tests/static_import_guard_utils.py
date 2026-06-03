from __future__ import annotations

import ast
from pathlib import Path

_CONTROLLER_CONTRACT_IMPORT_ROOTS = frozenset(
    {"__future__", "dataclasses", "enum", "typing"}
)
_PROTECTED_IMPORT_MODULES = frozenset(
    {
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.search",
        "core.providers",
        "core.models",
        "core.author",
        "core.session",
        "core.cache",
    }
)


def assert_controller_contract_imports_closed(
    contract_path: Path,
    *,
    allowed_core_modules: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Assert passive Controller handoff contracts only import safe helpers.

    The default import surface matches standalone passive contract modules. A
    test may allow explicitly named ``core.*`` helper modules when a cleanup
    intentionally consolidates representational scaffolding behind a shared
    helper. Protected runtime/prompt/provider/search/cache imports stay closed.
    """

    tree = ast.parse(contract_path.read_text(encoding="utf-8"))
    import_roots: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            import_roots.add(node.module.split(".")[0])
            imported_modules.add(node.module)

    allowed_roots = set(_CONTROLLER_CONTRACT_IMPORT_ROOTS)
    if allowed_core_modules:
        allowed_roots.add("core")

    allowed_modules = set(_CONTROLLER_CONTRACT_IMPORT_ROOTS) | set(allowed_core_modules)

    assert import_roots <= allowed_roots
    assert imported_modules <= allowed_modules
    assert imported_modules.isdisjoint(_PROTECTED_IMPORT_MODULES)
