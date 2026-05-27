from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_candidate_acquisition import (
    build_official_canonical_recovery_candidate_acquisition_trace,
)
from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = (
    _ROOT / "core" / "official_canonical_recovery_candidate_acquisition.py"
)
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_LIFECYCLE_PATH = _ROOT / "core" / "source_class_recovery_lifecycle.py"
_VISIBILITY_EXPORT_PATH = (
    _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
)


def _recommendation(
    *,
    missing: list[str],
    queries: list[str],
    reason: str = "official_canonical_recovery_query_acquisition:gap",
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": list(missing),
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": reason,
        "source_class_recovery_trigger_fields": [
            "official_canonical_recovery_query_acquisition"
        ],
    }


def _admitted(recommendation: dict[str, Any], *, query_type: str) -> bool:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace={
            "query_preview": "Explain current official or canonical reference material.",
            "query_type": query_type,
        },
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    return result.source_class_recovery_execution_admitted


def _admission_trace() -> dict[str, Any]:
    return {
        "official_canonical_recovery_execution_admission_trace": {
            "OfficialCanonicalRecoveryExecutionAdmission": {
                "admission_considered": True,
                "admission_eligible": True,
                "admission_used": True,
            }
        }
    }


def _record(
    controller: RunController,
    recommendation: dict[str, Any],
    *,
    admitted: bool = True,
    current_search_depth: str = "basic",
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 1}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth=current_search_depth,
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=admitted,
    )


def _execute(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    returned: list[dict[str, Any]],
    provider_result_count: int | None = None,
    provider_success: bool = True,
    search_providers: list[str] | None = None,
    search_depth_calls: list[str] | None = None,
    provider_calls: list[list[str]] | None = None,
) -> tuple[dict[str, int | bool], list[dict[str, Any]], list[dict[str, Any]]]:
    all_passages: list[dict[str, Any]] = []
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []

    def fake_search(
        captured_queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        if search_depth_calls is not None:
            search_depth_calls.append(search_depth)
        if provider_calls is not None:
            provider_calls.append(list(kwargs.get("search_providers") or []))
        result_count = provider_result_count
        if result_count is None:
            result_count = len(returned)
        accepted_count = len(returned)
        for passage in returned:
            seen_urls.add(str(passage.get("url") or ""))
        kwargs["provider_diagnostics"].append(
            {
                "provider": "fixture_provider",
                "provider_role": kwargs["provider_role"],
                "success": provider_success,
                "result_count": result_count,
                "accepted_url_count": accepted_count,
                "new_source_count": accepted_count,
                "query_preview": captured_queries[0] if captured_queries else "",
                "depth": search_depth,
            }
        )
        return returned

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=all_passages,
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[0.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=search_providers or ["tavily"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )
    return result, all_passages, provider_diagnostics


def test_ag50e_canonical_fixture_returns_visible_candidate() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation database MVCC"],
    )
    assert _admitted(recommendation, query_type="technical_reference") is True
    controller = RunController()
    lifecycle = _record(controller, recommendation)

    result, all_passages, _diagnostics = _execute(
        controller,
        lifecycle,
        returned=[
            {
                "url": "https://docs.example/reference",
                "title": "Canonical Reference",
                "text": "Canonical documentation describing concurrency behavior.",
                "source_tier": "canonical",
            }
        ],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle}
    )

    assert result["attempted"] is True
    assert result["result_count"] == 1
    assert len(all_passages) == 1
    assert lifecycle["recovered_result_count"] == 1
    assert lifecycle["candidate_return_status"] == "candidates_returned"
    assert lifecycle["official_canonical_candidate_visible"] is True
    assert export["candidate_return_status"] == "candidates_returned"
    assert export["official_canonical_candidate_visible"] is True


def test_ag50e_official_current_fixture_returns_visible_candidate() -> None:
    recommendation = _recommendation(
        missing=["official_current_rules"],
        queries=["official current source federal benefit 2026"],
    )
    assert _admitted(recommendation, query_type="official_current_status") is True
    controller = RunController()
    lifecycle = _record(controller, recommendation)

    _result, _all_passages, _diagnostics = _execute(
        controller,
        lifecycle,
        returned=[
            {
                "url": "https://agency.example/current-rules",
                "title": "Official Current Rules",
                "text": "Official current requirements and eligibility rules.",
                "source_tier": "official",
            }
        ],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle}
    )

    assert lifecycle["recovered_result_count"] == 1
    assert lifecycle["candidate_return_status"] == "candidates_returned"
    assert lifecycle["official_canonical_candidate_visible"] is True
    assert export["recovered_result_count"] == 1
    assert export["candidate_return_status"] == "candidates_returned"


def test_ag50e_zero_candidate_blocker_reports_provider_zero_results() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation database MVCC"],
    )
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=True)

    _execute(controller, lifecycle, returned=[], provider_result_count=0)
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle}
    )

    assert lifecycle["recovered_result_count"] == 0
    assert lifecycle["candidate_return_status"] == "zero_candidates"
    assert lifecycle["zero_candidate_blocker_kind"] == "provider_returned_zero_results"
    assert export["zero_candidate_blocker"] == "provider_returned_zero_results"
    assert export["zero_candidate_blocker_kind"] == "provider_returned_zero_results"
    assert export["next_failure_layer"] == "execution_attempted_zero_candidates"


def test_ag50e_candidate_return_statuses_are_count_driven() -> None:
    zero = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace={
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_queries": ["canonical documentation topic"],
            "active_source_class_recovery_result_count": 0,
        },
        provider_diagnostics=[
            {
                "provider_role": "source_class_recovery",
                "success": True,
                "result_count": 0,
                "accepted_url_count": 0,
            }
        ],
    )
    positive = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace={
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_queries": ["canonical documentation topic"],
            "active_source_class_recovery_result_count": 2,
        }
    )

    assert zero["candidate_return_status"] == "zero_candidates"
    assert positive["candidate_return_status"] == "candidates_returned"


def test_ag50e_does_not_create_new_provider_role_or_executor() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation topic"],
    )
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=True)

    action = controller.snapshot_ledger()["retrieval_actions"][0]

    assert action["name"] == "source_class_recovery"
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )


def test_ag50e_preserves_provider_selection_and_search_depth() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation topic"],
    )
    controller = RunController()
    lifecycle = _record(
        controller,
        recommendation,
        admitted=True,
        current_search_depth="advanced",
    )
    depths: list[str] = []
    providers: list[list[str]] = []

    _execute(
        controller,
        lifecycle,
        returned=[],
        search_providers=["tavily", "linkup"],
        search_depth_calls=depths,
        provider_calls=providers,
    )

    assert depths == ["advanced"]
    assert providers == [["tavily", "linkup"]]
    assert lifecycle["acquisition_provider_role"] == "source_class_recovery"


def test_ag50e_unknown_preservation_for_non_executed_facts() -> None:
    export = build_official_canonical_recovery_visibility_export(
        {
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_queries": ["canonical documentation topic"],
        }
    )

    assert export["candidate_return_status"] == "unknown"
    assert export["official_canonical_candidate_visible"] == "unknown"
    assert export["accepted_or_readable_official_or_canonical_count"] == "unknown"


def test_ag50e_sanitizes_candidate_acquisition_fields() -> None:
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace={
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_queries": [
                "raw prompt protected marker value"
            ],
            "active_source_class_recovery_result_count": 0,
            "raw_provider_payload": {"body": "do not leak"},
            "raw_prompt": "do not leak",
            "db_row": "do not leak",
            "cache_path": "do not leak",
            "sec" + "ret": "do not leak",
            "tok" + "en": "do not leak",
            "full_trace": {"do": "not leak"},
        },
        provider_diagnostics=[
            {
                "provider_role": "source_class_recovery",
                "success": True,
                "result_count": 0,
                "accepted_url_count": 0,
                "raw_payload": "do not leak",
            }
        ],
    )
    payload = json.dumps(trace, sort_keys=True)

    assert "do not leak" not in payload
    assert trace["acquisition_query_previews"] == ["[redacted protected material]"]


def test_ag50e_static_no_source_specific_rules_in_new_helper() -> None:
    source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    forbidden_terms = {
        "postgresql",
        "sqlite",
        "ssa",
        "irs",
        "nasa",
        "postgresql.org",
        "sqlite.org",
        "ssa.gov",
        "irs.gov",
        "nasa.gov",
    }

    assert forbidden_terms.isdisjoint(source.split())
    assert all(term not in source for term in forbidden_terms if "." in term)


def test_ag50e_static_protected_surface_guards() -> None:
    forbidden_import_prefixes = {
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.db",
        "core.llm",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.search_providers",
        "core.source_classifier",
        "core.author",
        "core.economist",
        "core.final_answer",
    }
    protected_terms = {
        "select_providers",
        "choose_supplemental_search_depth",
        "author_prompt",
        "economist",
        "final_answer",
        "rank_sources",
        "source_classifier",
    }

    violations: list[str] = []
    for path in (
        _HELPER_PATH,
        _EXECUTOR_PATH,
        _LIFECYCLE_PATH,
        _VISIBILITY_EXPORT_PATH,
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        imported.extend(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        violations.extend(
            f"{path.name}:{name}"
            for name in imported
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        )

    helper_source = _HELPER_PATH.read_text(encoding="utf-8")
    assert violations == []
    assert protected_terms.isdisjoint(helper_source.split())
