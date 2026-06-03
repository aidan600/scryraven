from __future__ import annotations

import ast
from pathlib import Path

from ui.demo_fixtures import (
    DEMO_FIXTURE_KIND,
    DEMO_SESSION_MARKER,
    build_demo_session,
    get_demo_scenario,
    is_demo_session,
    list_demo_scenarios,
    load_demo_fixture_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "demo" / "fixtures" / "offline_ux_scenarios.json"
DEMO_HELPER_PATHS = [
    ROOT / "ui" / "demo_fixtures.py",
    ROOT / "ui" / "pages_demo.py",
    ROOT / "ui" / "source_display.py",
]
FORBIDDEN_IMPORTS = {
    "core.llm",
    "core.pipeline",
    "core.pipeline_orchestrator",
    "core.prompts",
    "core.retrieval",
    "core.search",
    "core.search_providers",
    "core.providers",
    "core.models",
    "core.cache",
    "core.storage",
}
FORBIDDEN_UI_IMPORTS = {
    "ui.pages_thread",
}

FORBIDDEN_CALL_NAMES = {
    "ask_model",
    "compute_similarities",
    "embed_texts",
    "fetch_linkup_precision_block",
    "filter_top_evidence",
    "process_search_queries",
    "run_economist_step",
    "run_pipeline",
    "run_scout",
}


def test_demo_fixture_catalog_is_deterministic_and_labeled_offline() -> None:
    first = load_demo_fixture_catalog(FIXTURE_PATH)
    second = load_demo_fixture_catalog(FIXTURE_PATH)

    assert first == second
    assert first["fixture_kind"] == DEMO_FIXTURE_KIND
    assert "Offline demo fixture" in first["offline_notice"]
    assert {item["id"] for item in first["scenarios"]} >= {
        "ordinary_success",
        "insufficient_evidence",
        "source_conflict",
        "inferred_claim",
        "document_review_preview",
        "error_or_no_result",
        "mode_comparison",
    }


def test_build_demo_session_projects_review_safe_thread_shape() -> None:
    session = build_demo_session("source_conflict", FIXTURE_PATH)

    assert is_demo_session(session)
    assert session["id"] == "demo-source_conflict"
    assert session["run_id"] == "demo-source_conflict"
    assert session["demo_fixture"]["marker"] == DEMO_SESSION_MARKER
    assert session["demo_fixture"]["fixture_kind"] == DEMO_FIXTURE_KIND
    assert session["top_passages"]
    assert "fixture" in session["report"].casefold()


def test_demo_scenario_returns_deep_copy() -> None:
    scenario = get_demo_scenario("ordinary_success", FIXTURE_PATH)
    scenario["top_passages"].append({"source_id": 99})

    fresh = get_demo_scenario("ordinary_success", FIXTURE_PATH)
    assert all(passage.get("source_id") != 99 for passage in fresh["top_passages"])


def test_sidebar_scenario_metadata_is_stable_and_compact() -> None:
    scenarios = list_demo_scenarios(FIXTURE_PATH)

    assert scenarios == list_demo_scenarios(FIXTURE_PATH)
    assert all(set(item) == {"id", "title", "state_label"} for item in scenarios)


def test_demo_helpers_do_not_import_live_runtime_paths() -> None:
    for path in DEMO_HELPER_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        assert imported_modules.isdisjoint(FORBIDDEN_IMPORTS), path


def test_demo_page_does_not_import_live_thread_module() -> None:
    tree = ast.parse((ROOT / "ui" / "pages_demo.py").read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert imported_modules.isdisjoint(FORBIDDEN_UI_IMPORTS)


def test_demo_helpers_do_not_call_live_provider_model_search_functions() -> None:
    for path in DEMO_HELPER_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called_names.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called_names.add(func.attr)

        assert called_names.isdisjoint(FORBIDDEN_CALL_NAMES), path
