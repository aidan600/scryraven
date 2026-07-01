"""PRODUCT-PATH-REGRESSION: product runtime must not import AG proof scripts.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: proplex/ and core/ product/runtime imports.
Runtime consumer: ordinary python -m proplex status paths and core support modules.
Why ordinary product-path work cannot be done directly: not applicable; this
static guard protects product/runtime modules before import side effects occur.
Integration deadline: current phase.
Exit condition: keep while AG proof scripts remain outside product/runtime support.
Why this is not a shadow product path: it only parses imports and does not
execute an alternate runtime path.
Forbidden interpretation: this does not prove live validation, citation
readiness, source-obligation satisfaction, answerability, answer text, or
product correctness.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOTS = (ROOT / "proplex", ROOT / "core")
KNOWN_PRODUCT_STATUS_MODULES = (
    ROOT / "proplex" / "live_acquisition_readability_status.py",
    ROOT / "proplex" / "live_source_evidence_admission_status.py",
    ROOT / "proplex" / "live_citation_source_obligation_readiness_status.py",
    ROOT / "proplex" / "live_semantic_coverage_status.py",
)
RETAINED_PREFLIGHT_MODULE = ROOT / "core" / "retained_live_artifact_preflight.py"


def test_known_product_status_modules_do_not_import_ag_scripts() -> None:
    for path in KNOWN_PRODUCT_STATUS_MODULES:
        assert _ag_script_imports(path) == []


def test_product_runtime_modules_do_not_import_ag_scripts() -> None:
    violations: dict[str, list[str]] = {}
    for root in PRODUCT_ROOTS:
        for path in root.rglob("*.py"):
            imports = _ag_script_imports(path)
            if imports:
                violations[str(path.relative_to(ROOT))] = imports

    assert violations == {}


def test_retained_live_artifact_preflight_does_not_import_ag_scripts() -> None:
    assert _ag_script_imports(RETAINED_PREFLIGHT_MODULE) == []


def _ag_script_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_ag_script_module(alias.name):
                    imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_ag_script_module(module):
                imported.append(module)
            elif module == "scripts":
                imported.extend(
                    f"scripts.{alias.name}"
                    for alias in node.names
                    if str(alias.name).startswith("ag_")
                )
    return sorted(imported)


def _is_ag_script_module(module: str) -> bool:
    return module.startswith("scripts.ag_")
