from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_loop_spine import build_controller_loop_spine_result
from core.controller_provider_search_allocation import (
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    build_controller_recovery_decision,
)
from core.official_canonical_recovery_visibility_export import (
    NOT_OBSERVABLE,
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RunController
from core.source_class_recovery import build_source_class_recovery_recommendation
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)


_QUERY = (
    "Do people need REAL ID or other acceptable identification for domestic "
    "flights now, and when did enforcement start?"
)
_CORE_TOPIC = "acceptable identification for domestic flights"
_PRIMARY_ENTITY = "domestic flight identification requirements"
_MISSING_CLASS = "official_current_rules"


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=None,
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        fulfillment_handoff=SimpleNamespace(unfulfilled_items=(), partial_items=()),
    )


def _secondary_signals(*, official_found: bool = False) -> dict[str, Any]:
    return {
        "source_tier_counts": (
            {"official": 1, "secondary": 2} if official_found else {"secondary": 3}
        ),
        "official_evidence_found": official_found,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _domain_signals(*, official_found: bool = False) -> dict[str, Any]:
    return {
        "source_domain_counts": (
            {"agency.example": 1, "news.example": 2}
            if official_found
            else {"news.example": 2, "analysis.example": 1}
        ),
        "top_source_domains": [{"domain": "news.example", "count": 2}],
        "unique_source_domain_count": 2,
        "on_domain_source_count": 0,
        "off_domain_source_count": 2,
    }


def _observability() -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            _MISSING_CLASS: "expected_but_only_secondary"
        },
        "source_class_strong_satisfaction_counts": {_MISSING_CLASS: 0},
        "source_class_gap_candidates": [_MISSING_CLASS],
    }


def _ag93e4_recommendation() -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query=_QUERY,
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic=_CORE_TOPIC,
        primary_entity=_PRIMARY_ENTITY,
        anchor_packet=None,
        source_tier_counts={"secondary": 3},
        source_domain_counts={"news.example": 2, "analysis.example": 1},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )


def _empty_recommendation() -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": False,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [],
        "source_class_recovery_reason": None,
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": [],
    }


def _orchestrator_state(
    *,
    recommendation: dict[str, Any],
    official_found: bool = False,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = False,
    iterations_run: int = 0,
    max_iterations: int = 1,
) -> dict[str, Any]:
    return {
        "query": _QUERY,
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": _CORE_TOPIC,
        "primary_entity": _PRIMARY_ENTITY,
        "_source_class_recovery_lifecycle_recommendation": recommendation,
        "_source_class_recovery_answer_contract_observability": _observability(),
        "_source_tier_recovery_lifecycle": _secondary_signals(
            official_found=official_found
        ),
        "_source_domain_recovery_lifecycle": _domain_signals(
            official_found=official_found
        ),
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "OFF_TOPIC" if corpus_weak else "HEALTHY",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_considered": corpus_weak,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": (
            "weak_corpus_recovery_used"
            if weak_corpus_recovery_used
            else "blocked_by_weak_corpus_recovery"
            if corpus_weak
            else None
        ),
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": iterations_run,
        "max_iterations": max_iterations,
        "waste_flags": [],
    }


def _handoff(
    controller: RunController,
    *,
    recommendation: dict[str, Any],
    official_found: bool = False,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = False,
    iterations_run: int = 0,
    max_iterations: int = 1,
) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state=_orchestrator_state(
            recommendation=recommendation,
            official_found=official_found,
            corpus_weak=corpus_weak,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            iterations_run=iterations_run,
            max_iterations=max_iterations,
        ),
    )


def _visibility_export(handoff: Any, lifecycle: dict[str, Any]) -> dict[str, Any]:
    trace = dict(lifecycle)
    if handoff.official_canonical_recovery_execution_admission_trace:
        trace.update(handoff.official_canonical_recovery_execution_admission_trace)
    return build_official_canonical_recovery_visibility_export(trace)


def test_ag93e5_direct_ag93e4_recommendation_survives_authoritative_handoff() -> None:
    recommendation = _ag93e4_recommendation()
    controller = RunController()
    handoff = _handoff(
        controller,
        recommendation=recommendation,
        corpus_weak=True,
        iterations_run=1,
        max_iterations=2,
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    export = _visibility_export(handoff, lifecycle)
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": False,
            "reason": "checkpoint_exception",
            "official_canonical_checkpoint_exception_fallback_allowed": True,
        },
        source_class_lifecycle_trace=lifecycle,
    )

    assert recommendation["source_class_recovery_recommended"] is True
    assert recommendation["missing_expected_source_classes"] == [_MISSING_CLASS]
    assert recommendation["source_class_recovery_query_count"] == 2
    assert handoff.recommendation["source_class_recovery_query_count"] > 0
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert lifecycle["active_source_class_recovery_queries"]
    assert _MISSING_CLASS in lifecycle["active_source_class_recovery_missing_classes"]
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert export["source_class_recovery_eligible"] is True
    assert export["recovery_query_count"] > 0
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_ag93e5_query_acquisition_for_bridge_obligation_skips_weak_corpus_block() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        recommendation=_empty_recommendation(),
        official_found=True,
        corpus_weak=True,
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    acquisition = handoff.official_canonical_recovery_query_acquisition_trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]
    export = _visibility_export(handoff, lifecycle)

    assert handoff.recommendation["source_class_recovery_recommended"] is True
    assert handoff.recommendation["missing_expected_source_classes"] == [
        _MISSING_CLASS
    ]
    assert handoff.recommendation["source_class_recovery_query_count"] > 0
    assert acquisition["acquisition_repair_used"] is True
    assert acquisition["acquisition_repair_blockers"] == []
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert export["source_class_recovery_eligible"] is True
    assert export["recovery_query_count"] > 0


def test_ag93e5_runner_allocation_trace_visible_for_existing_bounded_path() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        recommendation=_empty_recommendation(),
        official_found=True,
        corpus_weak=True,
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    lifecycle.update(
        {
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_result_count": 0,
            "candidate_return_status": "zero_candidates",
            "recovered_result_count": 0,
            "recovery_slot_available": False,
            "source_obligation_status": "official_current_required_unmet",
            "required_source_classes": [_MISSING_CLASS],
            "unsatisfied_required_source_classes": [_MISSING_CLASS],
        }
    )
    decision = build_controller_recovery_decision(lifecycle)
    captured: dict[str, Any] = {}

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured["queries"] = list(queries)
        captured["search_depth"] = search_depth
        captured["provider_role"] = kwargs["provider_role"]
        return [
            {
                "provider_name": "offline-fixture",
                "title": "Official current identification rule",
                "url": "https://agency.example/current-identification-rule",
                "source_tier": "official",
                "source_class": _MISSING_CLASS,
                "currentness_signal": "current",
            }
        ]

    result = run_source_class_recovery_dispatch(
        SourceClassRecoveryRunnerContext(
            controller=controller,
            authorized_spine_action=None,
            controller_recovery_decision=decision,
            lifecycle_trace=lifecycle,
            process_search_queries=fake_search,
            all_passages=[],
            intent="general",
            complexity="medium",
            results_per_query=5,
            include_domains=[],
            exclude_domains=[],
            query_embedding=[],
            seen_urls=set(),
            collected_images=set(),
            embed_provider="fixture",
            embed_model="fixture",
            local_url="http://localhost",
            embed_texts=lambda *_args, **_kwargs: [],
            compute_similarities=lambda *_args, **_kwargs: [],
            status_container=object(),
            search_providers=["offline-fixture"],
            exa_domain_filter=None,
            entity_hint=_PRIMARY_ENTITY,
            provider_diagnostics=[],
            retrieval_pass_records=[],
        )
    )
    export = _visibility_export(handoff, lifecycle)
    allocation = lifecycle[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY]
    allocation_execution = allocation[PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY]

    assert decision.decision == REQUEST_PROVIDER_SEARCH_REVIEW
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.executed is True
    assert captured["provider_role"] == "source_class_recovery"
    assert captured["queries"]
    assert allocation_execution["executed"] is True
    assert allocation_execution["provider_role"] == "source_class_recovery"
    assert allocation_execution["query_count"] > 0
    assert export["provider_search_allocation_trace"] != NOT_OBSERVABLE
    assert export["provider_search_allocation_execution_trace"] != NOT_OBSERVABLE
    assert export["provider_search_allocation_execution_trace"]["query_count"] > 0


def test_ag93e5_hard_budget_stop_still_blocks_active_recovery() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        recommendation=_ag93e4_recommendation(),
        corpus_weak=True,
        iterations_run=1,
        max_iterations=1,
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert handoff.recommendation["source_class_recovery_query_count"] > 0
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_provider_role"] is None
    assert "blocked_by_iteration_budget" in lifecycle[
        "active_source_class_recovery_blockers"
    ]
