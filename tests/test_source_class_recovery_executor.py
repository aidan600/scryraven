from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.run_controller import RunController
from core.source_class_recovery_executor import (
    _source_class_recovery_action,
    execute_source_class_recovery_action,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_EXECUTOR_HELPER_PATH = _ROOT / "core" / "source_class_recovery_executor.py"


def _recommendation(
    *,
    recommended: bool = True,
    missing: list[str] | None = None,
    queries: list[str] | None = None,
) -> dict[str, Any]:
    missing_classes = list(
        missing if missing is not None else ["official_current_rules"]
    )
    recovery_queries = list(
        queries if queries is not None else ["Care Program official rules"]
    )
    return {
        "source_class_recovery_recommended": recommended,
        "missing_expected_source_classes": missing_classes if recommended else [],
        "source_class_recovery_queries": recovery_queries if recommended else [],
        "source_class_recovery_reason": (
            "missing_expected_source_class:" + ",".join(missing_classes)
            if recommended
            else None
        ),
    }


def _record_lifecycle(
    controller: RunController,
    *,
    recommendation: dict[str, Any] | None = None,
    current_search_depth: str = "basic",
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_considered: bool = False,
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=(
            recommendation if recommendation is not None else _recommendation()
        ),
        recommendation_evaluated=True,
        source_class_evidence_signals={},
        corpus_state="OFF_TOPIC" if weak_corpus_recovery_used else "HEALTHY",
        corpus_weak=weak_corpus_recovery_used,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=(
            None if weak_corpus_recovery_used else "not_weak_corpus"
        ),
        current_search_depth=current_search_depth,
        iteration_budget_available=True,
    )


def _eligible_controller_with_lifecycle(
    *,
    current_search_depth: str = "basic",
    queries: list[str] | None = None,
) -> tuple[RunController, dict[str, Any]]:
    controller = RunController()
    lifecycle = _record_lifecycle(
        controller,
        recommendation=_recommendation(queries=queries),
        current_search_depth=current_search_depth,
    )
    return controller, lifecycle


def _eligible_controller() -> RunController:
    controller, _lifecycle = _eligible_controller_with_lifecycle()
    return controller


def _execute_with_defaults(
    controller: RunController,
    lifecycle: dict[str, Any],
    fake_search: Any,
    **overrides: Any,
) -> dict[str, int | bool]:
    kwargs: dict[str, Any] = {
        "all_passages": [],
        "intent": "general",
        "complexity": "medium",
        "results_per_query": 6,
        "include_domains": [],
        "exclude_domains": [],
        "query_embedding": [1.0],
        "seen_urls": set(),
        "collected_images": set(),
        "embed_provider": "OpenAI",
        "embed_model": "text-embedding-3-small",
        "local_url": "http://localhost",
        "embed_texts": lambda *_args, **_kwargs: [],
        "compute_similarities": lambda *_args, **_kwargs: [],
        "status_container": object(),
        "search_providers": ["tavily"],
        "exa_domain_filter": None,
        "entity_hint": "Care Program",
        "provider_diagnostics": [],
        "retrieval_pass_records": [],
    }
    kwargs.update(overrides)
    return execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        **kwargs,
    )


def _forbidden_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    raise AssertionError("source_class_recovery search should not run")


def test_source_class_recovery_executor_static_import_guard() -> None:
    tree = ast.parse(_EXECUTOR_HELPER_PATH.read_text(encoding="utf-8"))
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
        "core.weak_corpus_recovery",
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

    assert violations == []


def test_source_class_recovery_executor_uses_injected_exception_type() -> None:
    class AdapterError(RuntimeError):
        pass

    controller = _eligible_controller()
    action = controller.state.recovery_action_records[0]
    action.active = False
    action.shadow = True

    with pytest.raises(
        AdapterError,
        match="source_class_recovery action must be controller-approved",
    ):
        _source_class_recovery_action(controller, error_type=AdapterError)


@pytest.mark.parametrize(
    ("envelope_update", "message"),
    [
        ({"action_type": "recover_weak_corpus"}, "unexpected action envelope"),
        ({"allowed_action": False}, "envelope is not approved"),
        ({"required_source_class": []}, "has no required class"),
    ],
)
def test_source_class_recovery_executor_rejects_invalid_controller_envelope(
    envelope_update: dict[str, Any],
    message: str,
) -> None:
    controller, lifecycle = _eligible_controller_with_lifecycle()
    action = controller.state.recovery_action_records[0]
    envelope = dict(action.metadata["controller_action_envelope"])
    envelope.update(envelope_update)
    action.metadata["controller_action_envelope"] = envelope
    controller.ledger.retrieval_actions[0].metadata[
        "controller_action_envelope"
    ] = envelope

    with pytest.raises(RuntimeError, match=message):
        _execute_with_defaults(controller, lifecycle, _forbidden_search)


def test_source_class_recovery_executor_skips_ineligible_without_search() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(
        controller,
        recommendation=_recommendation(recommended=False, missing=[], queries=[]),
    )
    lifecycle_before = dict(lifecycle)
    state_before = controller.snapshot_state()

    result = _execute_with_defaults(controller, lifecycle, _forbidden_search)

    assert result == {"attempted": False, "result_count": 0, "new_url_count": 0}
    assert lifecycle == lifecycle_before
    assert controller.snapshot_state() == state_before
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_used"] is False
    assert lifecycle["active_source_class_recovery_result_count"] == 0
    assert lifecycle["active_source_class_recovery_new_url_count"] == 0


def test_source_class_recovery_executor_preserves_already_used_counts() -> None:
    controller, lifecycle = _eligible_controller_with_lifecycle()
    controller.state.active_source_class_recovery_used = True
    controller.state.active_source_class_recovery_result_count = 7
    controller.state.active_source_class_recovery_new_url_count = 3
    lifecycle["active_source_class_recovery_used"] = True
    lifecycle["active_source_class_recovery_result_count"] = 7
    lifecycle["active_source_class_recovery_new_url_count"] = 3
    lifecycle_before = dict(lifecycle)
    state_before = controller.snapshot_state()

    result = _execute_with_defaults(controller, lifecycle, _forbidden_search)

    assert result == {"attempted": False, "result_count": 7, "new_url_count": 3}
    assert lifecycle == lifecycle_before
    assert controller.snapshot_state() == state_before


def test_source_class_recovery_executor_runs_eligible_action_equivalently() -> None:
    queries = [
        "Care Program official rules",
        "Care Program current eligibility standards",
    ]
    controller, lifecycle = _eligible_controller_with_lifecycle(
        current_search_depth="advanced",
        queries=queries,
    )
    existing_passage = {
        "title": "Existing secondary report",
        "url": "https://regionalnews.example/original",
        "text": "Secondary summary already collected.",
        "retrieval_stage": "main_retrieval",
        "_provider_role": "main_retrieval",
    }
    all_passages = [existing_passage]
    seen_urls = {"https://regionalnews.example/original"}
    collected_images = {"https://images.example/original.png"}
    include_domains = ["official.gov"]
    exclude_domains = ["social.example"]
    query_embedding = [0.1, 0.2]
    search_providers = ["tavily", "linkup"]
    provider_diagnostics = [
        {
            "provider": "tavily",
            "provider_role": "main_retrieval",
            "success": True,
        }
    ]
    existing_pass_record = {
        "stage": "main_retrieval",
        "iteration": 1,
        "queries": ["Care Program eligibility"],
        "providers": ["tavily"],
        "provider_role": "main_retrieval",
        "search_depth": "advanced",
        "results_per_query": 9,
    }
    retrieval_pass_records = [existing_pass_record]
    status_container = object()
    embed_texts = object()
    compute_similarities = object()
    captured_calls: list[dict[str, Any]] = []

    def fake_process_search_queries(
        captured_queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        captured_include_domains: list[str],
        captured_exclude_domains: list[str],
        captured_query_embedding: Any,
        captured_seen_urls: set[str],
        captured_images: set[str],
        embed_provider: str,
        embed_model: str,
        local_url: str,
        captured_embed_texts: Any,
        captured_compute_similarities: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_calls.append(
            {
                "queries": list(captured_queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "include_domains": captured_include_domains,
                "exclude_domains": captured_exclude_domains,
                "query_embedding": captured_query_embedding,
                "seen_urls": captured_seen_urls,
                "collected_images": captured_images,
                "embed_provider": embed_provider,
                "embed_model": embed_model,
                "local_url": local_url,
                "embed_texts": captured_embed_texts,
                "compute_similarities": captured_compute_similarities,
                "kwargs": kwargs,
            }
        )
        captured_seen_urls.add("https://official.gov/recovered-a")
        captured_seen_urls.add("https://official.gov/recovered-b")
        kwargs["provider_diagnostics"].append(
            {
                "provider": "tavily",
                "provider_role": kwargs["provider_role"],
                "depth": search_depth,
                "success": True,
                "logical_attempt_count": 1,
            }
        )
        return [
            {
                "title": "Recovered official rule",
                "url": "https://official.gov/recovered-a",
                "text": "Care Program current official requirements.",
                "score": 0.31,
                "source_tier": "official",
            },
            {
                "title": "Recovered official standard",
                "url": "https://official.gov/recovered-b",
                "text": "Care Program current official standards.",
                "score": 0.29,
                "source_tier": "official",
            },
        ]

    result = _execute_with_defaults(
        controller,
        lifecycle,
        fake_process_search_queries,
        all_passages=all_passages,
        intent="general",
        complexity="medium",
        results_per_query=9,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        query_embedding=query_embedding,
        seen_urls=seen_urls,
        collected_images=collected_images,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=embed_texts,
        compute_similarities=compute_similarities,
        status_container=status_container,
        search_providers=search_providers,
        exa_domain_filter=["official.gov"],
        entity_hint="Care Program",
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )

    assert result == {"attempted": True, "result_count": 2, "new_url_count": 2}
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["queries"] == queries
    assert call["intent"] == "general"
    assert call["complexity"] == "medium"
    assert call["search_depth"] == "advanced"
    assert call["results_per_query"] == 9
    assert call["include_domains"] == include_domains
    assert call["exclude_domains"] == exclude_domains
    assert call["query_embedding"] == query_embedding
    assert call["seen_urls"] is seen_urls
    assert call["collected_images"] is collected_images
    assert call["embed_texts"] is embed_texts
    assert call["compute_similarities"] is compute_similarities
    assert call["kwargs"]["status_container"] is status_container
    assert call["kwargs"]["search_providers"] == search_providers
    assert call["kwargs"]["exa_domain_filter"] == ["official.gov"]
    assert call["kwargs"]["entity_hint"] == "Care Program"
    assert call["kwargs"]["provider_diagnostics"] is provider_diagnostics
    assert call["kwargs"]["provider_role"] == "source_class_recovery"

    assert all_passages[0] is existing_passage
    recovered = all_passages[1:]
    assert [passage["url"] for passage in recovered] == [
        "https://official.gov/recovered-a",
        "https://official.gov/recovered-b",
    ]
    assert all(
        passage["retrieval_stage"] == "source_class_recovery"
        for passage in recovered
    )
    assert all(
        passage["_provider_role"] == "source_class_recovery"
        for passage in recovered
    )

    assert lifecycle["active_source_class_recovery_used"] is True
    assert lifecycle["active_source_class_recovery_result_count"] == 2
    assert lifecycle["active_source_class_recovery_new_url_count"] == 2
    assert lifecycle["active_source_class_recovery_attempt_count"] == 1
    assert controller.state.active_source_class_recovery_used is True
    assert controller.state.active_source_class_recovery_result_count == 2
    assert controller.state.active_source_class_recovery_new_url_count == 2
    assert controller.state.active_source_class_recovery_attempt_count == 1

    assert len(provider_diagnostics) == 2
    assert provider_diagnostics[-1]["provider_role"] == "source_class_recovery"
    assert retrieval_pass_records == [
        existing_pass_record,
        {
            "stage": "source_class_recovery",
            "iteration": None,
            "queries": queries,
            "providers": search_providers,
            "provider_role": "source_class_recovery",
            "search_depth": "advanced",
            "results_per_query": 9,
        },
    ]
    lifecycle_action = controller.snapshot_ledger()["retrieval_actions"][0]
    assert lifecycle_action["metadata"]["controller_action_envelope"] == (
        lifecycle["active_source_class_recovery_action_envelope"]
    )
    assert lifecycle_action["metadata"] == {
        "execution": "orchestrator_adapter_executed",
        "controller_decision": "run_source_class_recovery",
        "controller_action_envelope": lifecycle[
            "active_source_class_recovery_action_envelope"
        ],
        "result_count": 2,
        "new_url_count": 2,
    }
    adapter_facts = {
        record["name"]: record["value"]
        for record in controller.snapshot_ledger()["fact_records"]
        if record["metadata"].get("source") == "orchestrator_adapter"
    }
    assert adapter_facts == {
        "execution_attempted": True,
        "result_count": 2,
        "new_url_count": 2,
        "provider_role": "source_class_recovery",
        "search_depth": "advanced",
    }


def test_source_class_recovery_executor_stays_blocked_when_weak_corpus_owns_path() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(
        controller,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
    )
    lifecycle_before = dict(lifecycle)
    state_before = controller.snapshot_state()

    result = _execute_with_defaults(controller, lifecycle, _forbidden_search)

    assert result == {"attempted": False, "result_count": 0, "new_url_count": 0}
    assert lifecycle == lifecycle_before
    assert controller.snapshot_state() == state_before
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "blocked_by_weak_corpus_recovery"
    )
