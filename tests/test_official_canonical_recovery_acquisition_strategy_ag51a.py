from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RunController
from core.source_class_recovery import build_recovery_source_quality_diagnostics
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_QUERY_ACQUISITION_PATH = (
    _ROOT / "core" / "official_canonical_recovery_query_acquisition.py"
)
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _runtime_trace(**overrides: Any) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "query_preview": (
            "Explain how PostgreSQL MVCC works, why it improves read/write "
            "concurrency, and what tradeoffs it creates."
        ),
        "query_type": "technical_reference",
        "core_topic": "PostgreSQL MVCC",
        "primary_entity": "PostgreSQL",
        "missing_expected_source_classes": ["primary_source_documents"],
    }
    trace.update(overrides)
    return trace


def _base_recommendation(**overrides: Any) -> dict[str, Any]:
    recommendation: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": ["primary_source_documents"],
        "source_class_recovery_queries": ["canonical documentation PostgreSQL"],
    }
    recommendation.update(overrides)
    return recommendation


def _apply_strategy(
    *,
    trace: dict[str, Any] | None = None,
    recommendation: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_canonical_recovery_query_acquisition(
        runtime_trace=trace or _runtime_trace(),
        recommendation=recommendation or _base_recommendation(),
    )
    return (
        result.recommendation,
        result.trace["OfficialCanonicalRecoveryQueryAcquisition"],
    )


def _record_lifecycle(
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
        source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth=current_search_depth,
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=admitted,
    )


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


def _execute_fixture(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    returned_when_official_query: list[dict[str, Any]],
    returned_otherwise: list[dict[str, Any]],
    search_depth_calls: list[str] | None = None,
    query_calls: list[list[str]] | None = None,
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
        if query_calls is not None:
            query_calls.append(list(captured_queries))
        query_text = " ".join(captured_queries).casefold()
        returned = (
            returned_when_official_query
            if "official documentation" in query_text and "mvcc" in query_text
            else returned_otherwise
        )
        for passage in returned:
            seen_urls.add(str(passage.get("url") or ""))
        kwargs["provider_diagnostics"].append(
            {
                "provider": "fixture_provider",
                "provider_role": kwargs["provider_role"],
                "success": True,
                "result_count": len(returned),
                "accepted_url_count": len(returned),
                "new_source_count": len(returned),
                "query_count": len(captured_queries),
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
        search_providers=["tavily", "linkup"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )
    return result, all_passages, provider_diagnostics


def test_ag51a_admitted_canonical_slot_adds_official_reference_query_variants() -> None:
    recommendation, trace = _apply_strategy()

    assert trace["acquisition_repair_used"] is True
    assert trace["generic_query_intent"] == "canonical_documentation"
    assert trace["added_recovery_query_count"] == 2
    assert recommendation["source_class_recovery_queries"] == [
        "canonical documentation PostgreSQL",
        "official documentation PostgreSQL MVCC",
        "reference documentation PostgreSQL MVCC",
    ]
    assert "source_class_recovery_queries" in recommendation
    assert "provider" not in recommendation
    assert "search_depth" not in recommendation


def test_ag51a_existing_full_variant_profile_is_not_duplicated() -> None:
    recommendation, trace = _apply_strategy(
        recommendation=_base_recommendation(
            source_class_recovery_queries=[
                "official documentation database wal mode",
                "reference documentation database wal mode",
            ]
        ),
        trace=_runtime_trace(
            query_preview="Explain how a database WAL mode works.",
            core_topic="database WAL mode",
            primary_entity="database",
        ),
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "existing_query_satisfies_intent"
    assert recommendation["source_class_recovery_queries"] == [
        "official documentation database wal mode",
        "reference documentation database wal mode",
    ]


def test_ag51a_strategy_can_move_fixture_domains_to_official_canonical_docs() -> None:
    recommendation, _trace = _apply_strategy()
    admission = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=_runtime_trace(),
    )
    controller = RunController()
    lifecycle = _record_lifecycle(
        controller,
        recommendation,
        admitted=admission.source_class_recovery_execution_admitted,
    )
    query_calls: list[list[str]] = []
    search_depth_calls: list[str] = []

    result, all_passages, _diagnostics = _execute_fixture(
        controller,
        lifecycle,
        returned_when_official_query=[
            {
                "url": "https://www.postgresql.org/docs/current/mvcc-intro.html",
                "title": "PostgreSQL official MVCC documentation",
                "text": (
                    "Official documentation and reference manual for database "
                    "MVCC concurrency behavior."
                ),
                "source_tier": "unknown",
            }
        ],
        returned_otherwise=[
            {
                "url": "https://arxiv.org/pdf/1201.0228",
                "title": "Academic MVCC paper",
                "text": "Secondary academic analysis of MVCC.",
                "source_tier": "secondary",
            }
        ],
        query_calls=query_calls,
        search_depth_calls=search_depth_calls,
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle}
    )

    assert admission.source_class_recovery_execution_admitted is True
    assert result["attempted"] is True
    assert query_calls == [
        [
            "canonical documentation PostgreSQL",
            "official documentation PostgreSQL MVCC",
        ]
    ]
    assert search_depth_calls == ["basic"]
    assert [source["url"] for source in all_passages] == [
        "https://www.postgresql.org/docs/current/mvcc-intro.html"
    ]
    assert lifecycle["recovered_candidate_domain_preview"] == ["postgresql.org"]
    assert lifecycle["official_canonical_candidate_visible"] is True
    assert export["candidate_official_or_canonical_count"] == 1
    assert export["official_canonical_candidate_visible"] is True


def test_ag51a_secondary_only_recovered_set_remains_acquisition_failure() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(
        controller,
        _base_recommendation(),
        admitted=True,
    )

    _execute_fixture(
        controller,
        lifecycle,
        returned_when_official_query=[],
        returned_otherwise=[
            {
                "url": "https://arxiv.org/pdf/1201.0228",
                "title": "Academic MVCC paper",
                "text": "Secondary academic analysis of MVCC.",
                "source_tier": "secondary",
            }
        ],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle}
    )

    assert lifecycle["recovered_candidate_domain_preview"] == ["arxiv.org"]
    assert lifecycle["recovery_source_quality_status"] == "secondary_only"
    assert lifecycle["official_canonical_candidate_visible"] is False
    assert export["candidate_official_or_canonical_count"] == 0
    assert export["likely_next_failure_layer"] == (
        "candidate_returned_no_official_canonical_visible"
    )


def test_ag51a_no_official_canonical_obligation_does_not_change_strategy() -> None:
    recommendation, trace = _apply_strategy(
        trace={
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
            "core_topic": "compound interest",
            "primary_entity": "compound interest",
        },
        recommendation={"source_class_recovery_recommended": False},
    )

    assert recommendation == {"source_class_recovery_recommended": False}
    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "obligation_not_required"


def test_ag51a_source_class_fit_sanity_guard_recognizes_canonical_docs() -> None:
    diagnostics = build_recovery_source_quality_diagnostics(
        [
            {
                "url": "https://docs.python.org/3/reference/datamodel.html",
                "title": "Python official reference documentation",
                "text": (
                    "Official documentation and reference manual for software "
                    "library behavior and API semantics."
                ),
                "source_tier": "unknown",
            }
        ]
    )

    assert diagnostics["recovered_candidate_domain_preview"] == ["docs.python.org"]
    assert diagnostics["recovered_source_class_counts"] == {
        "primary_source_documents": 1
    }
    assert diagnostics["recovery_source_quality_status"] == (
        "official_or_primary_found"
    )


def test_ag51a_provider_and_protected_surface_guard() -> None:
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
    for path in (_QUERY_ACQUISITION_PATH, _EXECUTOR_PATH):
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
        violations = [
            f"{path.name}:{name}"
            for name in imported
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        ]
        assert violations == []

    query_acquisition_text = _QUERY_ACQUISITION_PATH.read_text(
        encoding="utf-8"
    ).casefold()
    assert "postgresql.org" not in query_acquisition_text
    assert "serper" not in query_acquisition_text
    assert "serpapi" not in query_acquisition_text
    assert "firecrawl" not in query_acquisition_text
    assert "jina" not in query_acquisition_text
    assert "dataforseo" not in query_acquisition_text
    assert "bright data" not in query_acquisition_text

    payload = json.dumps(
        _apply_strategy()[1],
        sort_keys=True,
    ).casefold()
    assert "provider_role" not in payload
    assert "search_depth" not in payload
    assert "final_answer_behavior_unchanged" in payload
    assert "ag51a" not in _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
