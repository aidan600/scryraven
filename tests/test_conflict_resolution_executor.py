from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.conflict_resolution_controller import (
    ConflictResolutionDecision,
    build_conflict_resolution_controller_input,
    build_conflict_resolution_lifecycle,
    conflict_resolution_lifecycle_defaults,
)
from core.conflict_resolution_executor import execute_conflict_resolution_action

_ROOT = Path(__file__).resolve().parents[1]
_EXECUTOR_PATH = _ROOT / "core" / "conflict_resolution_executor.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _approved_decision() -> ConflictResolutionDecision:
    lifecycle = build_conflict_resolution_lifecycle(
        build_conflict_resolution_controller_input(
            conflicts_present=True,
            conflict_notes=("official date conflicts with media date",),
            resolving_queries=(
                "Acme official corrected launch date",
                "Acme regulator launch date filing",
                "Acme newsroom launch date correction",
            ),
            ordinary_next_queries=("Acme ordinary launch date background",),
            current_search_depth="basic",
            iteration_budget_available=True,
            prior_attempt_count=0,
        )
    )
    assert lifecycle.decision.approved is True
    return lifecycle.decision


def _execute_with_defaults(
    decision: ConflictResolutionDecision,
    lifecycle_trace: dict[str, Any],
    fake_search: Any,
    **overrides: Any,
) -> dict[str, int | bool]:
    kwargs: dict[str, Any] = {
        "all_passages": [],
        "intent": "general",
        "complexity": "medium",
        "results_per_query": 6,
        "include_domains": ["official.gov"],
        "exclude_domains": ["social.example"],
        "query_embedding": [1.0],
        "seen_urls": set(),
        "collected_images": set(),
        "embed_provider": "OpenAI",
        "embed_model": "text-embedding-3-small",
        "local_url": "http://localhost",
        "embed_texts": object(),
        "compute_similarities": object(),
        "status_container": object(),
        "search_providers": ["tavily", "linkup"],
        "exa_domain_filter": ["official.gov"],
        "entity_hint": "Acme",
        "provider_diagnostics": [],
        "retrieval_pass_records": [],
    }
    kwargs.update(overrides)
    return execute_conflict_resolution_action(
        decision,
        lifecycle_trace=lifecycle_trace,
        process_conflict_resolution_queries=fake_search,
        **kwargs,
    )


def _forbidden_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    raise AssertionError("conflict-resolution search should not run")


def test_conflict_resolution_executor_runs_only_controller_approved_work() -> None:
    decision = _approved_decision()
    lifecycle_trace = conflict_resolution_lifecycle_defaults()
    all_passages = [
        {
            "title": "Existing report",
            "url": "https://media.example/acme",
            "text": "Media reported a conflicting date.",
            "retrieval_stage": "main_retrieval",
            "_provider_role": "main_retrieval",
        }
    ]
    seen_urls = {"https://media.example/acme"}
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []
    captured_calls: list[dict[str, Any]] = []
    include_domains = ["official.gov"]
    exclude_domains = ["social.example"]
    search_providers = ["tavily", "linkup"]
    exa_domain_filter = ["official.gov"]

    def fake_conflict_search(
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        captured_include_domains: list[str],
        captured_exclude_domains: list[str],
        query_embedding: Any,
        captured_seen_urls: set[str],
        collected_images: set[str],
        embed_provider: str,
        embed_model: str,
        local_url: str,
        embed_texts: Any,
        compute_similarities: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "include_domains": captured_include_domains,
                "exclude_domains": captured_exclude_domains,
                "query_embedding": query_embedding,
                "seen_urls": captured_seen_urls,
                "collected_images": collected_images,
                "embed_provider": embed_provider,
                "embed_model": embed_model,
                "local_url": local_url,
                "embed_texts": embed_texts,
                "compute_similarities": compute_similarities,
                "kwargs": kwargs,
            }
        )
        captured_seen_urls.add("https://official.gov/acme-correction")
        kwargs["provider_diagnostics"].append(
            {
                "provider": "tavily",
                "provider_role": kwargs["provider_role"],
                "success": True,
            }
        )
        return [
            {
                "title": "Official correction",
                "url": "https://official.gov/acme-correction",
                "text": "The official launch date is corrected.",
            }
        ]

    result = _execute_with_defaults(
        decision,
        lifecycle_trace,
        fake_conflict_search,
        all_passages=all_passages,
        seen_urls=seen_urls,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        search_providers=search_providers,
        exa_domain_filter=exa_domain_filter,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )

    assert result == {"attempted": True, "result_count": 1, "new_url_count": 1}
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["queries"] == [
        "Acme official corrected launch date",
        "Acme regulator launch date filing",
    ]
    assert call["search_depth"] == "basic"
    assert call["include_domains"] is include_domains
    assert call["exclude_domains"] is exclude_domains
    assert call["kwargs"]["search_providers"] == search_providers
    assert call["kwargs"]["exa_domain_filter"] == exa_domain_filter
    assert call["kwargs"]["provider_role"] == "conflict_resolution"
    assert provider_diagnostics[-1]["provider_role"] == "conflict_resolution"
    assert all_passages[0]["retrieval_stage"] == "main_retrieval"
    assert all_passages[1]["retrieval_stage"] == "conflict_resolution"
    assert all_passages[1]["_provider_role"] == "conflict_resolution"
    assert lifecycle_trace["active_conflict_resolution_used"] is True
    assert lifecycle_trace["active_conflict_resolution_attempt_count"] == 1
    assert retrieval_pass_records == [
        {
            "stage": "conflict_resolution",
            "iteration": None,
            "queries": [
                "Acme official corrected launch date",
                "Acme regulator launch date filing",
            ],
            "providers": search_providers,
            "provider_role": "conflict_resolution",
            "search_depth": "basic",
            "results_per_query": 6,
        }
    ]


def test_conflict_resolution_executor_has_one_attempt_semantics() -> None:
    decision = _approved_decision()
    lifecycle_trace = conflict_resolution_lifecycle_defaults()
    calls = 0

    def fake_conflict_search(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        kwargs["provider_diagnostics"].append(
            {"provider": "tavily", "provider_role": kwargs["provider_role"]}
        )
        return []

    first = _execute_with_defaults(decision, lifecycle_trace, fake_conflict_search)
    second = _execute_with_defaults(decision, lifecycle_trace, _forbidden_search)

    assert first == {"attempted": True, "result_count": 0, "new_url_count": 0}
    assert second == {"attempted": False, "result_count": 0, "new_url_count": 0}
    assert calls == 1


def test_conflict_resolution_executor_skips_blocked_decision_without_search() -> None:
    lifecycle = build_conflict_resolution_lifecycle(
        build_conflict_resolution_controller_input(
            conflicts_present=True,
            resolving_queries=(),
            current_search_depth="basic",
            iteration_budget_available=True,
            prior_attempt_count=0,
        )
    )
    lifecycle_trace = lifecycle.to_trace_fields()

    result = _execute_with_defaults(
        lifecycle.decision,
        lifecycle_trace,
        _forbidden_search,
    )

    assert result == {"attempted": False, "result_count": 0, "new_url_count": 0}
    assert lifecycle_trace["active_conflict_resolution_used"] is False


def test_conflict_resolution_executor_rejects_wrong_provider_role() -> None:
    decision = _approved_decision()
    bad_decision = ConflictResolutionDecision(
        decision=decision.decision,
        reason=decision.reason,
        conflict_notes=decision.conflict_notes,
        queries=decision.queries,
        provider_role="targeted_retrieval",
        search_depth=decision.search_depth,
        attempt_count=decision.attempt_count,
    )

    with pytest.raises(
        RuntimeError,
        match="conflict_resolution action has unexpected provider role",
    ):
        _execute_with_defaults(
            bad_decision,
            conflict_resolution_lifecycle_defaults(),
            _forbidden_search,
        )


def test_resolve_conflict_runtime_dispatch_uses_bounded_executor_import() -> None:
    source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    helper_source = (_ROOT / "core" / "retrieval_dispatch_runtime.py").read_text(encoding="utf-8")

    assert "execute_conflict_resolution_from_scope" in source
    assert "execute_conflict_resolution_action" in helper_source
    assert 'process_conflict_resolution_queries=values["process_search_queries"]' in helper_source
    assert "active_conflict_resolution_used = True" not in source


def test_conflict_resolution_executor_static_import_guard() -> None:
    tree = ast.parse(_EXECUTOR_PATH.read_text(encoding="utf-8"))
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
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
    )
    forbidden_terms = (
        "retrieve_targeted",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "ask_model",
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
    source = _EXECUTOR_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
