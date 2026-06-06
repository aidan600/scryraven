from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import core.source_class_recovery_runner as runner_module
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    build_controller_recovery_decision,
)
from core.run_controller import RetrievalAction, RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_DECISION_PATH = _ROOT / "core" / "controller_recovery_decision.py"


def _lifecycle(**overrides: Any) -> dict[str, Any]:
    trace = {
        "required_source_classes": ["official_current_rules"],
        "unsatisfied_required_source_classes": ["official_current_rules"],
        "source_obligation_status": "official_current_required_unmet",
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "recovery_slot_available": True,
    }
    trace.update(overrides)
    return trace


def _controller_with_action() -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=["official current fixture query"],
            provider_role="source_class_recovery",
            search_depth="deep",
            active=True,
            shadow=False,
            metadata={
                "controller_action_envelope": {
                    "action_type": "recover_missing_source_class",
                    "allowed_action": True,
                    "required_source_class": ["official_current_rules"],
                }
            },
        )
    )
    return controller


def _context(**overrides: Any) -> SourceClassRecoveryRunnerContext:
    values: dict[str, Any] = {
        "controller": _controller_with_action(),
        "authorized_spine_action": RECOVER_MISSING_SOURCE_CLASS,
        "controller_recovery_decision": build_controller_recovery_decision(
            _lifecycle()
        ),
        "lifecycle_trace": _lifecycle(),
        "process_search_queries": lambda *_args, **_kwargs: [],
        "all_passages": [],
        "intent": "general",
        "complexity": "medium",
        "results_per_query": 5,
        "include_domains": ["agency.gov"],
        "exclude_domains": ["example.com"],
        "query_embedding": [1.0],
        "seen_urls": set(),
        "collected_images": set(),
        "embed_provider": "fixture-embedder",
        "embed_model": "fixture-model",
        "local_url": "http://localhost",
        "embed_texts": lambda *_args, **_kwargs: [],
        "compute_similarities": lambda *_args, **_kwargs: [],
        "status_container": object(),
        "search_providers": ["offline-fixture"],
        "exa_domain_filter": ["agency.gov"],
        "entity_hint": "Fixture Agency",
        "provider_diagnostics": [],
        "retrieval_pass_records": [],
        "error_type": RuntimeError,
    }
    values.update(overrides)
    return SourceClassRecoveryRunnerContext(**values)


def test_ag74f_pipeline_delegates_source_class_recovery_dispatch_to_runner() -> None:
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")

    assert orchestrator_source.count("run_source_class_recovery_dispatch(") == 1
    helper_source = (Path(__file__).resolve().parents[1] / "core" / "retrieval_dispatch_runtime.py").read_text(encoding="utf-8")
    assert "source_class_recovery_context_from_scope(" in orchestrator_source
    assert "SourceClassRecoveryRunnerContext(" in helper_source
    assert "execute_source_class_recovery_action(" not in orchestrator_source
    assert (
        "record_source_class_recovery_execution_blocked_if_needed("
        not in orchestrator_source
    )
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in (
        orchestrator_source
    )
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert (
        runner_source.count(
            "record_source_class_recovery_execution_blocked_if_needed("
        )
        == 1
    )


def test_ag74f_runner_passes_existing_provider_search_query_depth_routing() -> None:
    captured: dict[str, Any] = {}
    context = _context()

    def fake_executor(controller: RunController, **kwargs: Any) -> dict[str, int | bool]:
        captured["controller"] = controller
        captured.update(kwargs)
        return {"attempted": True, "result_count": 7, "new_url_count": 3}

    with patch.object(
        runner_module,
        "execute_source_class_recovery_action",
        fake_executor,
    ):
        result = run_source_class_recovery_dispatch(context)

    assert captured["controller"] is context.controller
    assert captured["lifecycle_trace"] is context.lifecycle_trace
    assert captured["process_search_queries"] is context.process_search_queries
    assert captured["all_passages"] is context.all_passages
    assert captured["include_domains"] == ["agency.gov"]
    assert captured["exclude_domains"] == ["example.com"]
    assert captured["search_providers"] == ["offline-fixture"]
    assert captured["exa_domain_filter"] == ["agency.gov"]
    assert captured["entity_hint"] == "Fixture Agency"
    assert captured["provider_diagnostics"] is context.provider_diagnostics
    assert captured["retrieval_pass_records"] is context.retrieval_pass_records
    assert result.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 7,
        "new_url_count": 3,
    }
    assert result.total_urls_delta == 3
    assert result.total_chunks_delta == 7


def test_ag74f_runner_actual_executor_path_preserves_dispatch_parity() -> None:
    calls: list[dict[str, Any]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        include_domains: list[str],
        exclude_domains: list[str],
        query_embedding: Any,
        seen: set[str],
        collected_images: set[str],
        embed_provider: str,
        embed_model: str,
        local_url: str,
        embed_texts: Any,
        compute_similarities: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        seen.add("https://agency.gov/current-rule")
        kwargs["provider_diagnostics"].append(
            {
                "provider": "offline-fixture",
                "provider_role": kwargs["provider_role"],
                "depth": search_depth,
            }
        )
        calls.append(
            {
                "queries": queries,
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "query_embedding": query_embedding,
                "collected_images": collected_images,
                "embed_provider": embed_provider,
                "embed_model": embed_model,
                "local_url": local_url,
                "embed_texts": embed_texts,
                "compute_similarities": compute_similarities,
                **kwargs,
            }
        )
        return [
            {
                "title": "Official current rule",
                "url": "https://agency.gov/current-rule",
                "text": "Current official fixture.",
                "score": 0.42,
                "source_tier": "official",
            }
        ]

    context = _context(
        process_search_queries=fake_search,
        all_passages=all_passages,
        seen_urls=seen_urls,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )

    result = run_source_class_recovery_dispatch(context)

    assert result.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 1,
        "new_url_count": 1,
    }
    assert result.total_urls_delta == 1
    assert result.total_chunks_delta == 1
    assert calls[0]["queries"] == ["official current fixture query"]
    assert calls[0]["search_depth"] == "deep"
    assert calls[0]["search_providers"] == ["offline-fixture"]
    assert calls[0]["provider_role"] == "source_class_recovery"
    assert calls[0]["include_domains"] == ["agency.gov"]
    assert calls[0]["exclude_domains"] == ["example.com"]
    assert calls[0]["exa_domain_filter"] == ["agency.gov"]
    assert provider_diagnostics[0]["provider_role"] == "source_class_recovery"
    assert retrieval_pass_records == [
        {
            "stage": "source_class_recovery",
            "iteration": None,
            "queries": ["official current fixture query"],
            "providers": ["offline-fixture"],
            "provider_role": "source_class_recovery",
            "search_depth": "deep",
            "results_per_query": 5,
        }
    ]
    assert all_passages[0]["retrieval_stage"] == "source_class_recovery"
    assert context.lifecycle_trace["recovery_decision"] == "retry_recovery"
    assert "recovery_decision_trace" in context.lifecycle_trace
    assert not [
        key for key in context.lifecycle_trace if key.startswith("controller_")
    ]


def test_ag74f_request_provider_search_review_spine_value_alone_does_not_search() -> None:
    decision = build_controller_recovery_decision(
        _lifecycle(
            active_source_class_recovery_execution_attempted=True,
            active_source_class_recovery_result_count=0,
            candidate_return_status="zero_candidates",
            recovery_slot_available=False,
        )
    ).payload
    captured_queries: list[str] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return []

    result = run_source_class_recovery_dispatch(
        _context(
            authorized_spine_action=REQUEST_PROVIDER_SEARCH_REVIEW,
            controller_recovery_decision=None,
            process_search_queries=fake_search,
        )
    )

    assert decision["decision"] == REQUEST_PROVIDER_SEARCH_REVIEW
    assert decision["provider_search_review_requested"] is True
    assert decision["allowed_executor_action"] == "record_provider_search_review_request"
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert captured_queries == []


def test_ag74f_controller_decision_ownership_and_protected_surfaces() -> None:
    decision_source = _DECISION_PATH.read_text(encoding="utf-8")
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")

    assert "build_controller_recovery_decision(" in executor_source
    assert "controller_recovery_executor_allows_attempt(" in executor_source
    assert "request_provider_search_review" in decision_source
    assert "request_provider_search_review" not in executor_source
    assert "request_provider_search_review" not in orchestrator_source
    assert "record_provider_search_allocation_if_controller_authorized(" in (
        runner_source
    )
    assert "build_controller_recovery_decision(" not in runner_source
    assert "controller_recovery_executor_allows_attempt(" not in runner_source

    for source in (runner_source,):
        for forbidden in (
            "select_providers",
            "provider_depth",
            "provider_escalation",
            "provider_routing",
            "linkup",
            "source_classifier",
            "candidate_fit",
            "author_prompt",
            "ask_model",
            "final_answer(",
            "raw_provider_payload",
            "raw_prompt",
        ):
            assert forbidden not in source.casefold()
