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
DPRIME_SCHEMA_MODULE = ROOT / "core" / "dprime_support_proposal_schema.py"
DPRIME_PREFLIGHT_MODULE = ROOT / "core" / "dprime_evidence_frame_preflight.py"
DPRIME_NEGATIVE_CONTROL_PROFILE_MODULE = (
    ROOT / "core" / "dprime_negative_control_profile.py"
)
DPRIME_ASSESSMENT_VALIDATION_MODULE = (
    ROOT / "core" / "dprime_assessment_validation.py"
)
DPRIME_MODEL_REVIEW_ASSESSMENT_MODULE = (
    ROOT / "core" / "dprime_model_review_assessment.py"
)
DPRIME_MODEL_REVIEW_PROMPT_MODULE = ROOT / "core" / "dprime_model_review_prompt.py"


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


def test_dprime_schema_module_does_not_import_ag_scripts() -> None:
    assert _ag_script_imports(DPRIME_SCHEMA_MODULE) == []


def test_dprime_preflight_module_does_not_import_ag_scripts() -> None:
    assert _ag_script_imports(DPRIME_PREFLIGHT_MODULE) == []


def test_dprime_negative_control_profile_module_does_not_import_ag_scripts() -> None:
    assert _ag_script_imports(DPRIME_NEGATIVE_CONTROL_PROFILE_MODULE) == []


def test_dprime_assessment_validation_module_does_not_import_ag_scripts() -> None:
    assert _ag_script_imports(DPRIME_ASSESSMENT_VALIDATION_MODULE) == []


def test_dprime_model_review_modules_do_not_import_ag_scripts() -> None:
    assert _ag_script_imports(DPRIME_MODEL_REVIEW_ASSESSMENT_MODULE) == []
    assert _ag_script_imports(DPRIME_MODEL_REVIEW_PROMPT_MODULE) == []


def test_dprime_preflight_module_avoids_live_provider_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    assert _imports(DPRIME_PREFLIGHT_MODULE).isdisjoint(forbidden_imports)


def test_dprime_negative_control_profile_module_avoids_live_provider_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    assert _imports(DPRIME_NEGATIVE_CONTROL_PROFILE_MODULE).isdisjoint(
        forbidden_imports
    )


def test_dprime_assessment_validation_module_avoids_live_provider_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    assert _imports(DPRIME_ASSESSMENT_VALIDATION_MODULE).isdisjoint(
        forbidden_imports
    )


def test_dprime_model_review_modules_avoid_live_provider_imports() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    assert _imports(DPRIME_MODEL_REVIEW_ASSESSMENT_MODULE).isdisjoint(
        forbidden_imports
    )
    assert _imports(DPRIME_MODEL_REVIEW_PROMPT_MODULE).isdisjoint(forbidden_imports)


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


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _is_ag_script_module(module: str) -> bool:
    return module.startswith("scripts.ag_")
