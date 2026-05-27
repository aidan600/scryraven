from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.canonical_technical_docs_policy import (
    is_academic_literature_domain_filter,
    is_canonical_technical_documentation_context,
    is_explicit_academic_literature_request,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.prompts import DEFAULT_SYSTEM
from core.retrieval import ACADEMIC_DOMAINS
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = _ROOT / "core" / "canonical_technical_docs_policy.py"
_EXECUTOR_PATH = _ROOT / "core" / "source_class_recovery_executor.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _recommendation(
    *,
    missing: list[str],
    queries: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": list(missing),
        "source_class_recovery_reason": reason,
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_trigger_fields": [
            "official_canonical_recovery_query_acquisition"
        ],
    }


def _record_lifecycle(recommendation: dict[str, Any]) -> tuple[RunController, dict[str, Any]]:
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
    )
    return controller, lifecycle


def _execute_and_capture_filter(
    recommendation: dict[str, Any],
    *,
    exa_domain_filter: list[str] | None = None,
) -> list[str] | None:
    controller, lifecycle = _record_lifecycle(recommendation)
    captured: dict[str, Any] = {}

    def fake_search(
        _queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        _seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured["exa_domain_filter"] = kwargs.get("exa_domain_filter")
        kwargs["provider_diagnostics"].append(
            {
                "provider": "exa",
                "provider_role": kwargs["provider_role"],
                "success": True,
                "result_count": 0,
                "accepted_url_count": 0,
                "new_source_count": 0,
            }
        )
        return []

    execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
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
        search_providers=["exa"],
        exa_domain_filter=exa_domain_filter,
        entity_hint=None,
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )
    return captured.get("exa_domain_filter")


def test_ag51c_router_prompt_distinguishes_docs_from_academic_literature() -> None:
    router_prompt = DEFAULT_SYSTEM["router"].casefold()

    assert "do not set is_academic true solely because" in router_prompt
    assert "software" in router_prompt
    assert "database" in router_prompt
    assert "api" in router_prompt
    assert "canonical/official/project documentation" in router_prompt
    assert "unless the user explicitly asks for peer-reviewed research" in router_prompt


def test_ag51c_researcher_prompt_prefers_docs_for_canonical_technical_cases() -> None:
    researcher_prompt = DEFAULT_SYSTEM["researcher"].casefold()

    assert "canonical technical docs" in researcher_prompt
    assert "official/reference/canonical documentation" in researcher_prompt
    assert "do not add paper, arxiv, or academic-literature terms" in researcher_prompt


def test_ag51c_policy_helper_classifies_canonical_docs_and_academic_controls() -> None:
    assert is_canonical_technical_documentation_context(
        "official documentation PostgreSQL MVCC concurrency tradeoffs",
        required_source_classes=("primary_source_documents",),
    )
    assert is_canonical_technical_documentation_context(
        "reference documentation SQLite WAL mode tradeoffs",
        required_source_classes=("primary_source_documents",),
    )
    assert is_canonical_technical_documentation_context(
        "official documentation Python dataclasses behavior",
        required_source_classes=("primary_source_documents",),
    )
    assert is_canonical_technical_documentation_context(
        "reference docs Fetch API credentials behavior",
        required_source_classes=("primary_source_documents",),
    )

    academic = "peer-reviewed papers about PostgreSQL MVCC performance"
    assert is_explicit_academic_literature_request(academic)
    assert not is_canonical_technical_documentation_context(
        academic,
        required_source_classes=("primary_source_documents",),
    )
    assert not is_canonical_technical_documentation_context(
        "recent arXiv papers about database concurrency",
        required_source_classes=("primary_source_documents",),
    )


def test_ag51c_recovery_queries_are_official_reference_docs_oriented() -> None:
    postgres = apply_official_canonical_recovery_query_acquisition(
        runtime_trace={
            "query_preview": (
                "Explain how PostgreSQL MVCC works, why it improves "
                "read/write concurrency, and what tradeoffs it creates."
            ),
            "core_topic": "PostgreSQL MVCC",
            "primary_entity": "PostgreSQL",
        },
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": ["canonical documentation PostgreSQL"],
        },
    ).recommendation
    sqlite = apply_official_canonical_recovery_query_acquisition(
        runtime_trace={
            "query_preview": "Explain SQLite WAL mode and its tradeoffs.",
            "core_topic": "SQLite WAL mode",
            "primary_entity": "SQLite",
        },
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    ).recommendation

    assert postgres["source_class_recovery_queries"] == [
        "canonical documentation PostgreSQL",
        "official documentation PostgreSQL MVCC",
        "reference documentation PostgreSQL MVCC",
    ]
    assert sqlite["source_class_recovery_queries"] == [
        "official documentation SQLite WAL mode",
        "reference documentation SQLite WAL mode",
    ]


def test_ag51c_canonical_docs_recovery_suppresses_academic_domain_filter() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=[
            "official documentation PostgreSQL MVCC",
            "reference documentation PostgreSQL MVCC",
        ],
        reason="official_canonical_recovery_query_acquisition:primary_source_documents",
    )

    assert is_academic_literature_domain_filter(ACADEMIC_DOMAINS)
    assert _execute_and_capture_filter(
        recommendation,
        exa_domain_filter=list(ACADEMIC_DOMAINS),
    ) is None


def test_ag51c_explicit_academic_recovery_keeps_academic_domain_filter() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["peer-reviewed papers database concurrency MVCC performance"],
        reason="missing_expected_source_class:primary_source_documents",
    )

    assert _execute_and_capture_filter(
        recommendation,
        exa_domain_filter=list(ACADEMIC_DOMAINS),
    ) == ACADEMIC_DOMAINS


def test_ag51c_nontechnical_official_current_compatibility_keeps_filter() -> None:
    recommendation = _recommendation(
        missing=["official_current_rules"],
        queries=["Care Program official current eligibility rules"],
        reason="missing_expected_source_class:official_current_rules",
    )

    assert _execute_and_capture_filter(
        recommendation,
        exa_domain_filter=list(ACADEMIC_DOMAINS),
    ) == ACADEMIC_DOMAINS


def test_ag51c_static_protected_surface_guard() -> None:
    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8").casefold()
    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()

    assert "postgresql.org" not in helper_source
    assert "sqlite.org" not in helper_source
    assert "docs.python.org" not in helper_source
    assert "developer.mozilla.org" not in helper_source
    assert "canonical_technical_docs_policy" not in orchestrator_source

    for path in (_HELPER_PATH, _EXECUTOR_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        forbidden = {
            "core.pipeline_orchestrator",
            "core.routing",
            "core.retrieval",
            "core.search_providers",
            "core.prompts",
        }
        assert imported.isdisjoint(forbidden)

    assert "select_providers" not in executor_source
    assert "search_depth = " not in helper_source
