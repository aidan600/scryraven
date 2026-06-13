from __future__ import annotations

import ast
from pathlib import Path

from core.weak_corpus_recovery_queries import weak_corpus_recovery_seed_queries

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_ADAPTER_PATHS = (
    _ROOT / "core" / "targeted_retrieval_runtime_adapter.py",
    _ROOT / "core" / "conflict_resolution_runtime_adapter.py",
    _ROOT / "core" / "retrieval_depth_policy.py",
    _ROOT / "core" / "weak_corpus_recovery_queries.py",
    _ROOT / "core" / "retrieval_authority_stage.py",
)


def test_ag95rst_pipeline_no_longer_defines_extracted_stage_islands() -> None:
    tree = ast.parse(_PIPELINE_PATH.read_text(encoding="utf-8"))
    defs = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    assert {
        "_targeted_retrieval_currentness_source_fit_facts",
        "_build_targeted_retrieval_lifecycle_from_runtime",
        "_build_conflict_resolution_lifecycle_from_runtime_answer_contract",
        "choose_retrieval_search_depth",
        "choose_supplemental_search_depth",
        "_weak_corpus_recovery_seed_queries",
    }.isdisjoint(defs)


def test_ag95rst_adapters_do_not_import_live_provider_or_model_surfaces() -> None:
    forbidden_import_prefixes = (
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "openai",
        "anthropic",
        "requests",
        "httpx",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "author_prompt",
        "citation_selection",
    )

    for path in _ADAPTER_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        violations = [
            name
            for name in imported
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        ]

        assert violations == [], path.name
        assert all(term not in source for term in forbidden_terms), path.name


def test_ag95rst_weak_corpus_seed_queries_preserve_exact_policy_order() -> None:
    queries = weak_corpus_recovery_seed_queries(
        user_query="Find official pricing policy changes for Contoso Cloud enterprise seats",
        core_topic="Contoso Cloud enterprise seat pricing policy changes",
        primary_entity="Contoso Cloud",
        canonical_subject=None,
        current_date="2026-05-06",
        previous_queries=["Contoso Cloud 2026 news"],
    )

    assert queries == [
        '"Contoso Cloud" "official pricing policy changes"',
        '"Contoso Cloud" official pricing policy changes enterprise seats',
        '"Contoso Cloud" Contoso Cloud enterprise seat pricing policy changes',
        '"Contoso Cloud" official pricing policy changes enterprise seats 2026',
    ]


def test_ag95rst_weak_corpus_seed_queries_still_skip_near_previous() -> None:
    queries = weak_corpus_recovery_seed_queries(
        user_query="What are expected numeric changes to Acme Widget in the upcoming patch notes",
        core_topic="Acme Widget expected numeric changes upcoming patch notes",
        primary_entity="Acme Widget",
        canonical_subject="Acme Widget",
        current_date="2026-05-06",
        previous_queries=["Acme Widget expected numeric changes upcoming patch notes"],
    )

    assert queries == []
