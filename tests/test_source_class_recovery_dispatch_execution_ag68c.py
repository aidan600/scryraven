from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    build_authoritative_source_obligation_state_and_action,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    build_controller_loop_spine_result,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from tests.helpers.authoritative_source_forced_corridor import (
    canonical_doc_forced_corridor_fixture,
    official_current_forced_corridor_fixture,
    run_forced_corridor_validation,
)

_ROOT = Path(__file__).resolve().parents[1]
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"

_OFFICIAL_QUERIES = (
    "IRS 2026 standard mileage rate business official notice revenue procedure",
    "IRS 2026 standard mileage rate revenue procedure official current source",
)
_CANONICAL_QUERIES = (
    "official documentation PostgreSQL MVCC",
    "reference documentation PostgreSQL MVCC",
)


def _recommendation(
    source_class: str,
    *,
    queries: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": "source_class_recovery:visible_queries",
        "source_class_recovery_trigger_fields": ["runtime_source_class_expectation"],
    }


def _observability(source_class: str, status: str) -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {source_class: status},
        "source_class_strong_satisfaction_counts": {
            source_class: 1 if status == "satisfied_strong" else 0
        },
        "source_class_gap_candidates": [source_class],
    }


def _facts(
    *,
    source_class: str = "official_current_rules",
    queries: tuple[str, ...] = _OFFICIAL_QUERIES,
    status: str = "expected_but_only_secondary",
    query: str = (
        "What is the current IRS standard mileage rate for business use of "
        "a car in 2026?"
    ),
    query_type: str = "official_current_status",
    core_topic: str = "IRS 2026 standard mileage rate business",
    primary_entity: str = "IRS",
    terminal_stop_approved: bool = False,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> AuthoritativeSourceActionFacts:
    return AuthoritativeSourceActionFacts(
        query=query,
        intent="general",
        report_type="answer",
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        recommendation=_recommendation(source_class, queries=queries),
        source_class_observability=_observability(source_class, status),
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state="OFF_TOPIC" if corpus_weak else "HEALTHY",
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_used,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        current_search_depth="basic",
        iteration_budget_available=False,
        terminal_stop_approved=terminal_stop_approved,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )


def _build_action(
    facts: AuthoritativeSourceActionFacts,
) -> tuple[RunController, Any]:
    controller = RunController()
    return controller, build_authoritative_source_obligation_state_and_action(
        controller,
        facts=facts,
    )


def _unavailable_checkpoint() -> dict[str, Any]:
    return {
        "available": False,
        "decision": None,
        "recommended_action_name": None,
        "reason": "checkpoint_unavailable",
    }


def _spine(lifecycle: dict[str, Any]) -> Any:
    return build_controller_loop_spine_result(
        checkpoint_trace=_unavailable_checkpoint(),
        source_class_lifecycle_trace=lifecycle,
    )


def _execute_fixture(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    returned_source_class: str = "official_current_rules",
) -> tuple[dict[str, int | bool], list[str]]:
    captured_queries: list[str] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        seen_urls.add("https://www.irs.gov/ag68c-offline-fixture")
        return [
            {
                "url": "https://www.irs.gov/ag68c-offline-fixture",
                "title": "AG-68C offline fixture",
                "text": "Offline source-class recovery fixture.",
                "source_class": returned_source_class,
                "source_tier": "official",
            }
        ]

    result = execute_source_class_recovery_action(
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
        search_providers=["offline-fixture"],
        exa_domain_filter=None,
        entity_hint="IRS",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )
    return result, captured_queries


def test_ag68c_forced_official_current_reproduces_pre_dispatch_failure_shape_then_executes() -> None:
    controller, result = _build_action(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle
    admission = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert admission["admission_used"] is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert len(lifecycle["active_source_class_recovery_queries"]) > 0
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False

    spine = _spine(lifecycle)
    execution, captured_queries = _execute_fixture(controller, lifecycle)

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.source_class_executor_dispatched is True
    assert spine.trace_packet["gate_reason"] == (
        "approved_by_official_canonical_admission"
    )
    assert execution["attempted"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True
    assert captured_queries == list(_OFFICIAL_QUERIES)


def test_ag68c_executor_handoff_uses_existing_source_class_recovery_action() -> None:
    controller, result = _build_action(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle
    spine = _spine(lifecycle)

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS

    execution, _captured_queries = _execute_fixture(controller, lifecycle)
    action = controller.snapshot_ledger()["retrieval_actions"][0]

    assert execution["attempted"] is True
    assert action["name"] == "source_class_recovery"
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert action["metadata"]["controller_action_envelope"]["action_type"] == (
        "recover_missing_source_class"
    )


def test_ag68c_canonical_doc_corridor_dispatches_when_admitted_and_unblocked() -> None:
    controller, result = _build_action(
        _facts(
            source_class="primary_source_documents",
            queries=_CANONICAL_QUERIES,
            query="Explain how PostgreSQL MVCC works in a database.",
            query_type="technical_reference",
            core_topic="PostgreSQL MVCC official documentation",
            primary_entity="PostgreSQL",
        )
    )
    lifecycle = result.active_source_class_recovery_lifecycle
    spine = _spine(lifecycle)
    execution, captured_queries = _execute_fixture(
        controller,
        lifecycle,
        returned_source_class="primary_source_documents",
    )

    assert result.official_canonical_recovery_execution_admitted is True
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert execution["attempted"] is True
    assert captured_queries == list(_CANONICAL_QUERIES)


def test_ag68c_terminal_stop_no_longer_preempts_required_recovery() -> None:
    _controller, result = _build_action(_facts(terminal_stop_approved=True))
    lifecycle = result.active_source_class_recovery_lifecycle
    admission = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    spine = _spine(lifecycle)

    assert admission["admission_used"] is True
    assert admission["admission_blockers"] == []
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_ag68c_weak_corpus_ownership_defers_to_required_recovery() -> None:
    _controller, result = _build_action(
        _facts(corpus_weak=True, weak_corpus_recovery_used=True)
    )
    lifecycle = result.active_source_class_recovery_lifecycle
    spine = _spine(lifecycle)

    assert result.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_ag68c_ordinary_authoritative_acquisition_stays_ordinary_only() -> None:
    _controller, result = _build_action(_facts(status="satisfied_strong"))
    lifecycle = result.active_source_class_recovery_lifecycle
    spine = _spine(lifecycle)

    assert result.official_canonical_recovery_execution_admitted is False
    assert result.action_decision.approved is False
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert spine.authorized_dispatch is None


def test_ag68c_query_strings_and_public_helper_shape_are_preserved() -> None:
    _controller, result = _build_action(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle
    admission = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    official = run_forced_corridor_validation(official_current_forced_corridor_fixture())
    canonical = run_forced_corridor_validation(canonical_doc_forced_corridor_fixture())

    expected_classification_keys = {
        "schema_version",
        "ordinary_authoritative_source_already_present",
        "ordinary_evidence_status",
        "missing_authoritative_source_state_forced",
        "authoritative_recovery_bridge_visible",
        "authoritative_recovery_query_created",
        "recovery_query_count",
        "recovery_execution_admitted",
        "recovery_dispatch_authorized",
        "recovered_evidence_visible",
        "final_answer_citation_or_use",
        "ordinary_acquisition_counted_as_recovery_success",
        "source_class_recovery_lifecycle_action_ready",
        "source_class_recovery_execution_attempted",
        "bridge_used",
        "acquisition_repair_used",
        "admission_used",
        "next_failure_layer",
        "protected_surface",
    }

    assert result.recommendation["source_class_recovery_queries"] == list(
        _OFFICIAL_QUERIES
    )
    assert admission["recovery_query_previews"] == list(_OFFICIAL_QUERIES)
    assert lifecycle["active_source_class_recovery_queries"] == list(
        _OFFICIAL_QUERIES
    )
    assert set(official.classification) == expected_classification_keys
    assert set(canonical.classification) == expected_classification_keys


def test_ag68c_static_guard_keeps_pipeline_and_protected_surfaces_closed() -> None:
    spine_source = _SPINE_PATH.read_text(encoding="utf-8")
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(_SPINE_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.source_classifier",
        "openai",
        "requests",
    }

    assert imports.isdisjoint(forbidden_imports)
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")
    assert "official_canonical_acquisition_path_visible" not in pipeline_source
    assert pipeline_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert "run_source_class_recovery_dispatch(" in pipeline_source
    assert "and checkpoint_available" not in spine_source
