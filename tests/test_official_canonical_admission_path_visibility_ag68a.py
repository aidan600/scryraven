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
from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from tests.helpers.authoritative_source_forced_corridor import (
    canonical_doc_forced_corridor_fixture,
    official_current_forced_corridor_fixture,
    run_forced_corridor_validation,
)

_ROOT = Path(__file__).resolve().parents[1]
_ACTION_PATH = _ROOT / "core" / "authoritative_source_action.py"
_ADMISSION_PATH = _ROOT / "core" / "official_canonical_recovery_execution_admission.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

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
    reason: str = "source_class_recovery:visible_queries",
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": reason,
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
    query: str = "What is the current IRS standard mileage rate for business use of a car in 2026?",
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


def _admission_payload(
    recommendation: dict[str, Any],
    facts: AuthoritativeSourceActionFacts,
) -> dict[str, Any]:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace={
            "query_preview": facts.query,
            "query_type": facts.query_type,
            "core_topic": facts.core_topic,
            "primary_entity": facts.primary_entity,
            **dict(facts.source_class_observability or {}),
        },
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    return result.trace["OfficialCanonicalRecoveryExecutionAdmission"]


def _run_action(facts: AuthoritativeSourceActionFacts) -> tuple[RunController, Any]:
    controller = RunController()
    return controller, build_authoritative_source_obligation_state_and_action(
        controller,
        facts=facts,
    )


def _spine(lifecycle: dict[str, Any]) -> Any:
    return build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=lifecycle,
    )


def _execute_fixture(
    controller: RunController,
    lifecycle: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
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
        seen_urls.add("https://www.irs.gov/ag68a-offline-fixture")
        return [
            {
                "url": "https://www.irs.gov/ag68a-offline-fixture",
                "title": "IRS offline fixture",
                "text": "Offline official/current recovery fixture.",
                "source_class": "official_current_rules",
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


def test_ag68a_regression_shape_query_visible_but_path_not_visible_without_promoted_fact() -> None:
    facts = _facts()
    payload = _admission_payload(dict(facts.recommendation or {}), facts)

    assert payload["recovery_query_count"] == 2
    assert payload["admission_acquisition_path_visible"] is False
    assert payload["admission_used"] is False
    assert payload["admission_skip_reason"] == (
        "official_canonical_acquisition_path_not_visible"
    )


def test_forced_official_current_visible_queries_promote_admission_path_fact() -> None:
    _controller, result = _run_action(_facts())
    payload = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert result.recommendation["official_canonical_acquisition_path_visible"] is True
    assert result.recommendation[
        "official_canonical_acquisition_path_visibility_source"
    ] == "action_readiness_visible_recovery_queries"
    assert payload["admission_acquisition_path_visible"] is True
    assert payload["admission_used"] is True


def test_forced_official_current_lifecycle_becomes_ready_without_ordinary_budget() -> None:
    _controller, result = _run_action(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert "blocked_by_iteration_budget" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_forced_official_current_controller_spine_authorizes_dispatch() -> None:
    _controller, result = _run_action(_facts())
    spine = _spine(result.active_source_class_recovery_lifecycle)

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.source_class_executor_dispatched is True
    assert spine.trace_packet["gate_reason"] == "approved_by_official_canonical_admission"


def test_forced_official_current_dispatch_fixture_executes_existing_executor() -> None:
    controller, result = _run_action(_facts())
    spine = _spine(result.active_source_class_recovery_lifecycle)
    dispatch_result, captured_queries = _execute_fixture(
        controller,
        result.active_source_class_recovery_lifecycle,
    )

    assert spine.source_class_executor_dispatched is True
    assert dispatch_result["attempted"] is True
    assert captured_queries == list(_OFFICIAL_QUERIES)
    action = controller.snapshot_ledger()["retrieval_actions"][0]
    assert action["name"] == "source_class_recovery"
    assert action["provider_role"] == "source_class_recovery"


def test_forced_canonical_doc_visible_queries_reach_admission_lifecycle_and_dispatch() -> None:
    _controller, result = _run_action(
        _facts(
            source_class="primary_source_documents",
            queries=_CANONICAL_QUERIES,
            query="Explain how PostgreSQL MVCC works in a database.",
            query_type="technical_reference",
            core_topic="PostgreSQL MVCC official documentation",
            primary_entity="PostgreSQL",
        )
    )
    spine = _spine(result.active_source_class_recovery_lifecycle)

    assert result.official_canonical_recovery_execution_admitted is True
    assert result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] is True
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_aggregate_only_ordinary_authoritative_success_remains_insufficient_custody() -> None:
    _controller, result = _run_action(_facts(status="satisfied_strong"))
    spine = _spine(result.active_source_class_recovery_lifecycle)
    forced = run_forced_corridor_validation(
        official_current_forced_corridor_fixture(
            ordinary_evidence_status="satisfied_strong",
            execute_dispatch_fixture=True,
        )
    ).classification

    assert result.official_canonical_recovery_execution_admitted is False
    assert result.action_decision.approved is False
    assert spine.authorized_dispatch is None
    assert forced["next_failure_layer"] == "recovery_query_not_created"
    assert forced["ordinary_acquisition_counted_as_recovery_success"] is False
    assert forced["missing_authoritative_source_state_forced"] is True


def test_terminal_stop_without_lifecycle_blocker_preserves_recovery() -> None:
    _controller, result = _run_action(_facts(terminal_stop_approved=True))
    payload = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    spine = _spine(result.active_source_class_recovery_lifecycle)

    assert payload["admission_used"] is True
    assert payload["admission_skip_reason"] is None
    assert payload["admission_blockers"] == []
    assert result.active_source_class_recovery_lifecycle[
        "authority_lifecycle_required_recovery_allowed"
    ] is True
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_weak_corpus_cannot_preempt_required_recovery_without_blocker() -> None:
    _controller, result = _run_action(
        _facts(corpus_weak=True, weak_corpus_recovery_used=True)
    )
    payload = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert result.recommendation["official_canonical_acquisition_path_visible"] is True
    assert payload["admission_used"] is True
    assert payload["admission_skip_reason"] is None
    assert payload["admission_blockers"] == []
    assert result.active_source_class_recovery_lifecycle[
        "authority_lifecycle_required_recovery_allowed"
    ] is True
    assert result.active_source_class_recovery_lifecycle[
        "authority_lifecycle_weak_corpus_may_own_path"
    ] is False
    assert result.action_decision.approved is True


def test_existing_query_strings_and_previews_are_unchanged() -> None:
    _controller, result = _run_action(_facts())
    payload = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert result.recommendation["source_class_recovery_queries"] == list(
        _OFFICIAL_QUERIES
    )
    assert payload["recovery_query_previews"] == list(_OFFICIAL_QUERIES)


def test_lower_tier_evidence_remains_partial_until_recovery_execution() -> None:
    _controller, result = _run_action(_facts())
    projection = result.trace["obligation_projection"]

    assert projection["source_obligation_status"] == "partial"
    assert projection["source_class_satisfaction_status"][
        "official_current_rules"
    ] == "expected_but_only_secondary"
    assert result.official_canonical_recovery_execution_admitted is True


def test_public_forced_corridor_helper_output_shape_and_trace_keys_are_retained() -> None:
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

    assert set(official.classification) == expected_classification_keys
    assert set(canonical.classification) == expected_classification_keys
    assert "active_source_class_recovery_action_envelope" in (
        official.action_result.active_source_class_recovery_lifecycle
    )


def test_promoted_visibility_fact_is_controller_input_not_trace_projection() -> None:
    _controller, result = _run_action(_facts())

    assert result.recommendation["official_canonical_acquisition_path_visible"] is True
    assert result.trace["protected_surface"]["projection_used_as_control_input"] is False
    assert "recommendation" in result.trace["control_inputs"]
    assert "trace fields" in result.trace["control_inputs_exclude"]


def test_static_guard_keeps_provider_search_and_pipeline_surfaces_closed() -> None:
    imports: set[str] = set()
    for path in (_ACTION_PATH, _ADMISSION_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports.update(
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        imports.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )

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

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "official_canonical_acquisition_path_visible" not in pipeline_source
    assert pipeline_source.count(
        "build_authoritative_source_action_orchestrator_handoff("
    ) == 1
