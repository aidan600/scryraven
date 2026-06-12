from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
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
_PURE_HELPERS = (
    _ROOT / "core" / "official_canonical_recovery_execution_admission.py",
    _ROOT / "core" / "official_canonical_recovery_visibility_export.py",
    _ROOT / "core" / "source_class_recovery_lifecycle.py",
)


def _checkpoint(action_name: str, *, available: bool = True) -> dict[str, Any]:
    return {
        "available": available,
        "decision": {"action_name": action_name} if available else None,
        "recommended_action_name": action_name if available else None,
    }


def _recommendation(
    *,
    missing: list[str],
    queries: list[str] | None = None,
    reason: str = "official_canonical_recovery_query_acquisition:gap",
) -> dict[str, Any]:
    recovery_queries = (
        list(queries)
        if queries is not None
        else ["canonical documentation database MVCC"]
    )
    return {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": list(missing),
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_reason": reason,
        "source_class_recovery_trigger_fields": [
            "official_canonical_recovery_query_acquisition"
        ],
    }


def _admit(
    recommendation: dict[str, Any],
    *,
    trace: dict[str, Any] | None = None,
    existing_blockers: tuple[str, ...] = (),
    prior_attempts: int = 0,
) -> bool:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=trace
        or {
            "query_preview": "Explain how database MVCC works.",
            "query_type": "technical_reference",
        },
        existing_blockers=existing_blockers,
        prior_recovery_attempt_count=prior_attempts,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    return result.source_class_recovery_execution_admitted


def _record(
    controller: RunController,
    recommendation: dict[str, Any],
    *,
    admitted: bool,
    iteration_budget_available: bool = False,
    corpus_state: str = "HEALTHY",
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 1}},
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_used,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        official_canonical_source_class_slot_available=admitted,
    )


def _execute(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    returned: list[dict[str, Any]] | None = None,
) -> dict[str, int | bool]:
    def fake_search(
        _queries: list[str],
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
        passages = returned or []
        for passage in passages:
            seen_urls.add(str(passage.get("url") or ""))
        return passages

    return execute_source_class_recovery_action(
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
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )


def test_required_canonical_ag50b_slot_dispatches_existing_executor() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation PostgreSQL MVCC"],
    )
    admitted = _admit(recommendation)
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=admitted)
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(RECOVER_MISSING_SOURCE_CLASS),
        source_class_lifecycle_trace=lifecycle,
    )

    assert admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert spine.source_class_executor_dispatched is True
    assert spine.trace_packet["gate_reason"] == "approved"

    result = _execute(
        controller,
        lifecycle,
        returned=[
            {
                "url": "https://example.test/mvcc",
                "title": "Canonical MVCC docs",
                "text": "MVCC documentation",
            }
        ],
    )

    assert result["attempted"] is True
    assert lifecycle["active_source_class_recovery_used"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True


def test_required_official_current_ag50b_slot_dispatches_existing_executor() -> None:
    recommendation = _recommendation(
        missing=["official_current_rules"],
        queries=["official current source federal benefit 2026"],
    )
    admitted = _admit(
        recommendation,
        trace={
            "query_preview": "What are the current official rules for a federal benefit in 2026?",
            "query_type": "official_current_status",
        },
    )
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=admitted)
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(RECOVER_MISSING_SOURCE_CLASS),
        source_class_lifecycle_trace=lifecycle,
    )

    assert admitted is True
    assert spine.source_class_executor_dispatched is True


def test_preferred_and_unknown_obligations_do_not_force_execution() -> None:
    preferred = build_official_canonical_recovery_execution_admission(
        recommendation={"source_class_recovery_recommended": False},
        runtime_trace={"query_preview": "What happened this week in transit news?"},
    )
    unknown = build_official_canonical_recovery_execution_admission(
        recommendation={"source_class_recovery_recommended": False},
        runtime_trace={},
    )

    assert preferred.source_class_recovery_execution_admitted is False
    assert unknown.source_class_recovery_execution_admitted is False


def test_aggregate_satisfied_source_class_still_allows_execution() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])

    admitted = _admit(
        recommendation,
        trace={
            "query_preview": "Explain how database MVCC works.",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
        },
    )

    assert admitted is True


def test_terminal_weak_corpus_and_conflict_blockers_are_preserved() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    terminal = _admit(recommendation, existing_blockers=("terminal_stop_approved",))
    weak = _admit(
        recommendation,
        trace={
            "query_preview": "Explain how database MVCC works.",
            "weak_corpus_recovery_used": True,
        },
    )
    conflict = _admit(
        recommendation,
        trace={
            "query_preview": "Explain how database MVCC works.",
            "conflict_resolution_owns_path": True,
        },
    )

    assert terminal is False
    assert weak is False
    assert conflict is False


def test_terminal_checkpoint_still_blocks_admitted_lifecycle() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=True)
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(STOP_INSUFFICIENT_WITH_CAVEAT),
        source_class_lifecycle_trace=lifecycle,
    )

    assert spine.source_class_executor_dispatched is False
    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "blocked_by_terminal_stop"
    )
    assert spine.trace_packet["blocked_or_skipped_actions"][
        RECOVER_MISSING_SOURCE_CLASS
    ] == "blocked_by_terminal_stop"


def test_ordinary_iteration_budget_exhaustion_does_not_block_ag50b_slot() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    controller = RunController()
    lifecycle = _record(
        controller,
        recommendation,
        admitted=True,
        iteration_budget_available=False,
    )

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert "blocked_by_iteration_budget" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_prior_attempt_cap_and_missing_query_block_execution() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    no_query = _recommendation(missing=["primary_source_documents"], queries=[])

    assert _admit(recommendation, prior_attempts=1) is False
    assert _admit(no_query) is False


def test_lifecycle_and_visibility_export_report_execution_attempt_consistently() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=True)

    _execute(controller, lifecycle, returned=[])
    export = build_official_canonical_recovery_visibility_export(
        {
            "official_canonical_recovery_execution_admission_trace": {
                "OfficialCanonicalRecoveryExecutionAdmission": {
                    "admission_used": True,
                    "admission_eligible": True,
                    "admission_considered": True,
                }
            },
            **lifecycle,
        }
    )

    assert export["source_class_recovery_used"] is True
    assert export["source_class_recovery_execution_attempted"] is True
    assert export["candidate_return_status"] == "zero_candidates"
    assert export["next_failure_layer"] == "execution_attempted_zero_candidates"


def test_visibility_preserves_unknown_candidate_and_acceptance_facts() -> None:
    export = build_official_canonical_recovery_visibility_export(
        {
            "official_canonical_recovery_execution_admission_trace": {
                "OfficialCanonicalRecoveryExecutionAdmission": {
                    "admission_used": True,
                    "admission_eligible": True,
                    "admission_considered": True,
                }
            },
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
        }
    )

    assert export["candidate_return_status"] == "unknown"
    assert export["candidate_official_or_canonical_count"] == "unknown"
    assert export["accepted_or_readable_official_or_canonical_count"] == "unknown"
    assert export["next_failure_layer"] == (
        "execution_attempted_candidate_return_unknown"
    )


def test_conflict_checkpoint_does_not_dispatch_when_admission_is_not_used() -> None:
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(RESOLVE_CONFLICT),
        source_class_lifecycle_trace={
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_official_canonical_admitted": False,
        },
        conflict_resolution_lifecycle_trace={
            "approved": True,
            "active_conflict_resolution_considered": True,
            "blockers": [],
        },
    )

    assert spine.source_class_executor_dispatched is False
    assert spine.conflict_resolution_executor_dispatched is True


def test_dispatch_uses_no_new_provider_role_or_executor() -> None:
    recommendation = _recommendation(missing=["primary_source_documents"])
    controller = RunController()
    lifecycle = _record(controller, recommendation, admitted=True)

    action = controller.snapshot_ledger()["retrieval_actions"][0]

    assert action["name"] == "source_class_recovery"
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )


def test_static_protected_surface_guard_for_ag50d_helpers() -> None:
    forbidden_import_prefixes = {
        "openai",
        "anthropic",
        "requests",
        "httpx",
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

    violations: list[str] = []
    for path in _PURE_HELPERS:
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

    assert violations == []


def test_no_provider_depth_ranking_query_prompt_or_final_answer_outputs_added() -> None:
    export = build_official_canonical_recovery_visibility_export(
        {
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_result_count": 0,
        }
    )
    closed_surface_keys = {
        "provider_selection",
        "provider_routing",
        "search_depth_policy",
        "ranking_policy",
        "query_wording",
        "prompt_behavior",
        "source_classification_policy",
        "final_answer_behavior",
    }

    assert closed_surface_keys.isdisjoint(export)
