from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
)
from core.controller_loop_spine import build_controller_loop_spine_result
from core.evidence_integration_checkpoint import (
    build_evidence_integration_checkpoint_trace,
    decide_evidence_integration_checkpoint,
)
from core.pipeline_orchestrator import (
    _authoritative_source_checkpoint_refresh_allowed,
    _build_evidence_integration_snapshot_from_runtime,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from tests.helpers.authoritative_source_forced_corridor import (
    canonical_doc_forced_corridor_fixture,
    official_current_forced_corridor_fixture,
    run_forced_corridor_validation,
)

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"

_SSA_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
)
_SSA_RECOVERY_QUERIES = (
    "SSA 2026 Social Security taxable maximum wage base official contribution "
    "benefit base",
    "official current source Social Security taxable maximum wage base for 2026 "
    "and official supporting source",
)


def _recommendation(
    *,
    recommended: bool = True,
    queries: tuple[str, ...] = _SSA_RECOVERY_QUERIES,
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": (
            ["official_current_rules"] if recommended else []
        ),
        "source_class_recovery_queries": list(queries) if recommended else [],
        "source_class_recovery_query_count": len(queries) if recommended else 0,
        "source_class_recovery_reason": (
            "source_class_recovery:ssa_official_current_gap"
            if recommended
            else None
        ),
        "source_class_recovery_trigger_fields": (
            ["runtime_source_class_expectation"] if recommended else []
        ),
    }


def _observability(*, satisfied: bool = False) -> dict[str, Any]:
    status = "satisfied_strong" if satisfied else "expected_but_only_secondary"
    return {
        "source_class_satisfaction_status": {"official_current_rules": status},
        "source_class_strong_satisfaction_counts": {
            "official_current_rules": 1 if satisfied else 0
        },
        "source_class_gap_candidates": (
            [] if satisfied else ["official_current_rules"]
        ),
    }


def _answer_contract_result() -> SimpleNamespace:
    contract = SimpleNamespace(
        family=SimpleNamespace(value="current_official_rules"),
        must_satisfy=("official current source",),
        should_satisfy=(),
        evidence_classes_needed=("official_current_rules",),
    )
    evidence_state = SimpleNamespace(
        evidence_available=True,
        evidence_sufficient=False,
        source_classes_present=("reputable_secondary",),
        source_classes_missing=("official_current_rules",),
        conflicts_present=False,
        conflict_notes=(),
        resolving_queries=(),
        prior_queries=("ssa wage base payroll secondary source",),
        next_queries=("official SSA taxable maximum wage base",),
        next_query_redundant=False,
        social_signal_status=None,
        scrutineer_requested=False,
        scrutineer_needed=False,
    )
    return SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=contract,
            evidence_used=("secondary-payroll-evidence",),
        ),
        state=SimpleNamespace(
            evidence_state_summary=evidence_state,
            missing_information=("official current source missing",),
        ),
        fulfillment_handoff=SimpleNamespace(
            fulfilled_items=(),
            partial_items=("secondary source found",),
            unfulfilled_items=("official current source",),
        ),
    )


def _ordinary_answer_contract_result() -> SimpleNamespace:
    contract = SimpleNamespace(
        family=SimpleNamespace(value="current_official_rules"),
        must_satisfy=("official current source",),
        should_satisfy=(),
        evidence_classes_needed=("official_current_rules",),
    )
    evidence_state = SimpleNamespace(
        evidence_available=True,
        evidence_sufficient=True,
        source_classes_present=("official_current_rules",),
        source_classes_missing=(),
        conflicts_present=False,
        conflict_notes=(),
        resolving_queries=(),
        prior_queries=("ssa official wage base",),
        next_queries=(),
        next_query_redundant=False,
        social_signal_status=None,
        scrutineer_requested=False,
        scrutineer_needed=False,
    )
    return SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=contract,
            evidence_used=("official-evidence",),
        ),
        state=SimpleNamespace(
            evidence_state_summary=evidence_state,
            missing_information=(),
        ),
        fulfillment_handoff=SimpleNamespace(
            fulfilled_items=("official current source",),
            partial_items=(),
            unfulfilled_items=(),
        ),
    )


def _orchestrator_state(
    *,
    recommendation: dict[str, Any] | None = None,
    observability: dict[str, Any] | None = None,
    answer_contract_result: SimpleNamespace | None = None,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> dict[str, Any]:
    return {
        "query": _SSA_QUERY,
        "intent": "general",
        "report_type": "answer",
        "query_type": "official_current_status",
        "core_topic": "SSA 2026 Social Security taxable maximum wage base",
        "primary_entity": "SSA",
        "_source_class_recovery_lifecycle_recommendation": (
            recommendation or _recommendation()
        ),
        "_source_class_recovery_answer_contract_observability": (
            observability or _observability()
        ),
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 2},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"payroll.example": 2},
            "top_source_domains": [{"domain": "payroll.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
        },
        "_pre_recovery_answer_contract_result": (
            answer_contract_result or _answer_contract_result()
        ),
        "corpus_state": "OFF_TOPIC" if corpus_weak else "HEALTHY",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_considered": weak_corpus_recovery_used,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": (
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 1,
        "waste_flags": [],
    }


def _handoff(
    controller: RunController,
    *,
    state: dict[str, Any] | None = None,
) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state=state or _orchestrator_state(),
    )


def _checkpoint(action_name: str) -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": action_name},
        "recommended_action_name": action_name,
    }


def _refresh_checkpoint(
    *,
    handoff: Any,
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    snapshot = _build_evidence_integration_snapshot_from_runtime(
        answer_contract_result=_answer_contract_result(),
        source_class_recovery_recommendation=handoff.recommendation,
        active_source_class_recovery_lifecycle=lifecycle,
        strategy="Balanced",
        is_sufficient=False,
        corpus_weak=False,
        corpus_state="HEALTHY",
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_attempted=False,
        weak_corpus_recovery_skip_reason=None,
        retrieval_stop_shadow_telemetry={
            "retrieval_stop_shadow_decision": "continue_retrieval",
            "retrieval_stop_shadow_next_query_count": 1,
        },
        iterations_run=0,
        max_iterations=1,
    )
    decision = decide_evidence_integration_checkpoint(snapshot)
    return build_evidence_integration_checkpoint_trace(
        snapshot=snapshot,
        decision=decision,
        legacy_runtime_branch="authoritative_source_action_refresh",
    )


def _execute_product_callsite(
    controller: RunController,
    lifecycle: dict[str, Any],
    *,
    authorized_spine_action: str | None,
) -> tuple[dict[str, int | bool], list[str], list[dict[str, Any]]]:
    captured_queries: list[str] = []
    all_passages: list[dict[str, Any]] = []

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
        seen_urls.add("https://www.ssa.gov/ag68g-offline-fixture")
        return [
            {
                "url": "https://www.ssa.gov/ag68g-offline-fixture",
                "title": "SSA AG-68G offline fixture",
                "text": "Offline fixture for SSA official/current dispatch.",
                "source_class": "official_current_rules",
                "source_tier": "official",
            }
        ]

    if authorized_spine_action != RECOVER_MISSING_SOURCE_CLASS:
        return {"attempted": False, "result_count": 0, "new_url_count": 0}, [], []

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
        search_providers=["offline-fixture"],
        exa_domain_filter=None,
        entity_hint="SSA",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )
    return result, captured_queries, all_passages


def test_ag68g_ssa_fixture_reproduces_stale_checkpoint_callsite_gap() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    admission = handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    stale_spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        source_class_lifecycle_trace=lifecycle,
    )
    execution, captured_queries, _passages = _execute_product_callsite(
        controller,
        lifecycle,
        authorized_spine_action=stale_spine.authorized_dispatch,
    )

    assert admission["admission_used"] is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_queries"] == list(
        _SSA_RECOVERY_QUERIES
    )
    assert stale_spine.authorized_dispatch is None
    assert stale_spine.trace_packet["gate_reason"] == "alternate_action_not_promoted"
    assert execution["attempted"] is False
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert captured_queries == []


def test_ag68g_refreshes_stale_checkpoint_and_product_callsite_executes_ssa() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    stale_checkpoint = _checkpoint(RETRIEVE_TARGETED)

    assert _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace=stale_checkpoint,
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=lifecycle,
    )

    refreshed_checkpoint = _refresh_checkpoint(handoff=handoff, lifecycle=lifecycle)
    refreshed_spine = build_controller_loop_spine_result(
        checkpoint_trace=refreshed_checkpoint,
        source_class_lifecycle_trace=lifecycle,
    )
    execution, captured_queries, all_passages = _execute_product_callsite(
        controller,
        lifecycle,
        authorized_spine_action=refreshed_spine.authorized_dispatch,
    )

    assert refreshed_checkpoint["recommended_action_name"] == (
        RECOVER_MISSING_SOURCE_CLASS
    )
    assert refreshed_spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert refreshed_spine.source_class_executor_dispatched is True
    assert execution["attempted"] is True
    assert lifecycle["active_source_class_recovery_used"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True
    assert captured_queries == list(_SSA_RECOVERY_QUERIES)
    assert all_passages[0]["retrieval_stage"] == "source_class_recovery"


def test_ag68g_dispatch_ignores_projection_only_envelope() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = {
        **handoff.active_source_class_recovery_lifecycle,
        "active_source_class_recovery_action_envelope": {},
    }
    projection = dict(handoff.authoritative_source_action_trace["obligation_projection"])
    projection["active_source_class_recovery_action_envelope"] = {
        "action_type": "recover_missing_source_class",
        "required_source_class": ["official_current_rules"],
        "allowed_action": True,
    }
    assert handoff.authoritative_source_action_trace["protected_surface"][
        "projection_used_as_control_input"
    ] is False
    assert projection["active_source_class_recovery_action_envelope"][
        "allowed_action"
    ] is True
    assert not _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=lifecycle,
    )


def test_ag68g_irs_weak_corpus_ownership_defers_to_authority_lifecycle() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            corpus_weak=True,
            weak_corpus_recovery_used=True,
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert handoff.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=lifecycle,
    )


def test_ag68g_terminal_stop_and_invalid_envelope_remain_fail_closed() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    terminal_checkpoint = _checkpoint(STOP_INSUFFICIENT_WITH_CAVEAT)
    invalid_lifecycle = {
        **lifecycle,
        "active_source_class_recovery_action_envelope": {
            "action_type": "recover_missing_source_class",
            "required_source_class": [],
            "allowed_action": True,
        },
    }

    assert not _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace=terminal_checkpoint,
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=lifecycle,
    )

    assert not _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=invalid_lifecycle,
    )


def test_ag68g_checkpoint_exception_refresh_allows_aggregate_gap_admission() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            recommendation=_recommendation(recommended=False),
            observability=_observability(satisfied=True),
            answer_contract_result=_ordinary_answer_contract_result(),
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert handoff.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert _authoritative_source_checkpoint_refresh_allowed(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_exception",
            "decision": None,
            "recommended_action_name": None,
        },
        official_canonical_recovery_execution_admitted=(
            handoff.official_canonical_recovery_execution_admitted
        ),
        active_source_class_recovery_lifecycle=lifecycle,
    )


def test_ag68g_aggregate_ordinary_status_no_longer_blocks_recovery_admission() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            recommendation=_recommendation(recommended=False),
            observability=_observability(satisfied=True),
            answer_contract_result=_ordinary_answer_contract_result(),
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint(RETRIEVE_TARGETED),
        source_class_lifecycle_trace=lifecycle,
    )

    assert handoff.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert spine.authorized_dispatch is None
    assert spine.source_class_executor_dispatched is False


def test_ag68g_query_strings_and_helper_shapes_are_preserved() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    official = run_forced_corridor_validation(official_current_forced_corridor_fixture())
    canonical = run_forced_corridor_validation(canonical_doc_forced_corridor_fixture())

    assert handoff.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_queries"
    ] == list(_SSA_RECOVERY_QUERIES)
    assert official.classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert canonical.classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert set(official.classification) == set(canonical.classification)


def test_ag68g_pipeline_change_is_tiny_and_protected_surfaces_remain_closed() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(pipeline_source)
    refresh_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == (
            "_authoritative_source_checkpoint_refresh_allowed"
        )
    ]

    assert pipeline_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert "run_source_class_recovery_dispatch(" in pipeline_source
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in (
        pipeline_source
    )
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source
    assert len(refresh_calls) == 1
    helper_start = pipeline_source.index(
        "def _authoritative_source_checkpoint_refresh_allowed"
    )
    helper_end = pipeline_source.index(
        "\ndef _build_conflict_resolution_lifecycle_from_runtime_answer_contract",
        helper_start,
    )
    helper_source = pipeline_source[helper_start:helper_end].casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in helper_source
