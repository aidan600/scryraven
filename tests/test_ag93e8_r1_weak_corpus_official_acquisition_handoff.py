from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    RETRY_RECOVERY,
    STOP_INSUFFICIENT,
    build_controller_recovery_decision,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    NOT_OBSERVABLE,
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController

_OFFICIAL_CURRENT = "official_current_rules"
_LIVE_SHAPED_QUERY = (
    "Do U.S. air travelers need a REAL ID or other acceptable identification "
    "for domestic flights now, and when did enforcement start? Use current "
    "official sources."
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


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=None,
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        fulfillment_handoff=SimpleNamespace(unfulfilled_items=(), partial_items=()),
    )


def _orchestrator_state(
    *,
    query: str = _LIVE_SHAPED_QUERY,
    core_topic: str = "REAL ID or other acceptable identification for domestic flights",
    primary_entity: str = "domestic air traveler identification requirements",
    recommendation: dict[str, Any] | None = None,
    source_class_observability: dict[str, Any] | None = None,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = True,
    terminal_stop_approved: bool = False,
    iterations_run: int = 0,
    max_iterations: int = 1,
) -> dict[str, Any]:
    return {
        "query": query,
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": core_topic,
        "primary_entity": primary_entity,
        "_source_class_recovery_lifecycle_recommendation": (
            _empty_recommendation() if recommendation is None else recommendation
        ),
        "_source_class_recovery_answer_contract_observability": (
            {} if source_class_observability is None else source_class_observability
        ),
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 3},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"news.example": 2, "analysis.example": 1},
            "top_source_domains": [{"domain": "news.example", "count": 2}],
            "unique_source_domain_count": 2,
            "on_domain_source_count": 0,
            "off_domain_source_count": 2,
        },
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
        "evidence_integration_checkpoint_trace": (
            {"terminal_stop_approved": True} if terminal_stop_approved else {}
        ),
        "current_search_depth_for_recovery": "basic",
        "iterations_run": iterations_run,
        "max_iterations": max_iterations,
        "waste_flags": [],
    }


def _handoff(**overrides: Any) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state=_orchestrator_state(**overrides),
    )


def _export(handoff: Any) -> dict[str, Any]:
    trace = dict(handoff.active_source_class_recovery_lifecycle)
    if handoff.official_canonical_recovery_query_acquisition_trace:
        trace[OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY] = (
            handoff.official_canonical_recovery_query_acquisition_trace
        )
    if handoff.official_canonical_recovery_execution_admission_trace:
        trace[OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY] = (
            handoff.official_canonical_recovery_execution_admission_trace
        )
    return build_official_canonical_recovery_visibility_export(trace)


def _acquisition(handoff: Any) -> dict[str, Any]:
    return handoff.official_canonical_recovery_query_acquisition_trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]


def _admission(handoff: Any) -> dict[str, Any]:
    return handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]


def test_ag93e8_r1_live_shaped_weak_corpus_runs_official_acquisition() -> None:
    handoff = _handoff()
    acquisition = _acquisition(handoff)
    admission = _admission(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    export = _export(handoff)

    assert handoff.recommendation["missing_expected_source_classes"] == [
        _OFFICIAL_CURRENT
    ]
    assert acquisition["acquisition_repair_considered"] is True
    assert acquisition["acquisition_repair_eligible"] is True
    assert acquisition["acquisition_repair_used"] is True
    assert "airport_screening_identity_access_rule" in acquisition[
        "official_authority_acquisition_plan"
    ]["venue_families"]
    assert acquisition["official_authority_acquisition_plan"]["hard_domains"] == []
    assert handoff.recommendation["source_class_recovery_query_count"] > 0
    assert all(
        marker not in " ".join(
            acquisition["official_authority_acquisition_plan"]["query_variants"]
        ).casefold()
        for marker in ("tsa.gov", "dhs.gov")
    )

    assert admission["admission_acquisition_path_visible"] is True
    assert admission["admission_eligible"] is True
    assert admission["admission_used"] is True
    assert admission["recovery_query_count"] > 0
    assert "weak_corpus_recovery_owns_path" not in admission["admission_blockers"]
    assert "blocked_by_corpus_weak" not in admission["admission_blockers"]

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert lifecycle["active_source_class_recovery_queries"]
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]

    assert export["acquisition_repair_used"] is True
    assert export["official_authority_acquisition_plan"] != NOT_OBSERVABLE
    assert export["admission_eligible"] is True
    assert export["admission_used"] is True
    assert export["weak_corpus_coexistence_reason"] == (
        "unsatisfied_official_current_recovery_lane"
    )


def test_ag93e8_r1_no_initial_queries_are_created_before_admission() -> None:
    handoff = _handoff(recommendation=_empty_recommendation())
    acquisition = _acquisition(handoff)
    admission = _admission(handoff)

    assert acquisition["existing_recovery_query_count"] == 0
    assert acquisition["executable_recovery_query_count"] > 0
    assert handoff.recommendation["source_class_recovery_queries"]
    assert admission["recovery_query_available"] is True
    assert admission["admission_skip_reason"] is None


def test_ag93e8_r1_controller_keeps_official_obligation_unmet() -> None:
    handoff = _handoff()
    decision = build_controller_recovery_decision(
        handoff.active_source_class_recovery_lifecycle
    )

    assert decision.payload["source_obligation_status"] == (
        "official_current_required_unmet"
    )
    assert decision.payload["required_source_class"] == [_OFFICIAL_CURRENT]
    assert decision.decision == RETRY_RECOVERY
    assert decision.payload["allowed_executor_action"] == (
        "execute_existing_recovery_action"
    )
    assert decision.decision != REQUEST_PROVIDER_SEARCH_REVIEW


def test_ag93e8_r1_no_official_obligation_remains_blocked_by_weak_corpus() -> None:
    handoff = _handoff(
        query="Summarize news commentary about why private gyms ask for ID.",
        core_topic="private gym identification explainer",
        primary_entity="private gym membership",
    )
    acquisition = _acquisition(handoff)
    admission = _admission(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert handoff.recommendation["missing_expected_source_classes"] == []
    assert acquisition["acquisition_repair_used"] is False
    assert acquisition["acquisition_repair_skip_reason"] in {
        "obligation_not_required",
        "preferred_obligation_advisory_only",
    }
    assert admission["admission_eligible"] is False
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert "blocked_by_weak_corpus_recovery" in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_ag93e8_r1_terminal_stop_still_blocks() -> None:
    handoff = _handoff(terminal_stop_approved=True)
    admission = _admission(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_eligible"] is False
    assert "terminal_stop_approved" in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_blockers"]


def test_ag93e8_r1_hard_cap_still_blocks() -> None:
    controller = RunController()
    controller.state.active_source_class_recovery_attempt_count = 1
    handoff = build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state=_orchestrator_state(),
    )
    admission = _admission(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_eligible"] is False
    assert "budget_hard_exhausted" in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert "already_attempted" in lifecycle["active_source_class_recovery_blockers"]


def test_ag93e8_r1_conflict_and_policy_blockers_remain_authoritative() -> None:
    base_state = _orchestrator_state()
    conflict_state = {
        **base_state,
        "conflict_resolution_owns_path": True,
    }
    policy_handoff = build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state=base_state,
    )
    conflict_admission = _admission(
        build_authoritative_source_action_orchestrator_handoff(
            RunController(),
            orchestrator_state=conflict_state,
        )
    )

    policy_result = build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state={
            **base_state,
            "provider_policy_reusable": False,
        },
    )

    assert policy_handoff.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] is True
    assert "conflict_resolution_owns_path" in conflict_admission[
        "admission_blockers"
    ]
    assert policy_result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] is False
    policy_blockers = policy_result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert "blocked_by_provider_policy_change_required" in policy_blockers


def test_ag93e8_r1_news_and_unreadable_official_do_not_satisfy() -> None:
    handoff = _handoff()
    lifecycle = dict(handoff.active_source_class_recovery_lifecycle)
    lifecycle.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_result_count": 1,
            "recovered_accepted_url_count": 1,
        }
    )
    lifecycle.pop("authority_lifecycle", None)
    news_candidate = {
        "candidate_id": "news-id-explainer",
        "title": "News explainer about airport IDs",
        "url": "https://news.example/airport-id",
        "text": "News context about identification requirements.",
        "source_tier": "secondary",
        "source_class": "secondary_only",
    }
    unreadable_official = {
        "candidate_id": "official-unreadable",
        "title": "Official accepted ID guidance",
        "url": "https://agency.example/id-guidance",
        "source_tier": "official",
        "source_class": _OFFICIAL_CURRENT,
        "readable_text_available": False,
        "readability_status": "readability_failed",
    }

    news_final, news_decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[news_candidate],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )
    unreadable_final, unreadable_decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[unreadable_official],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )

    assert news_final == []
    assert news_decision.source_fit_status == "no_matching_source_fit"
    assert "secondary_only" in news_decision.source_fit_rejection_reasons
    assert unreadable_final == []
    assert unreadable_decision.source_fit_status == "no_matching_source_fit"
    assert "readability_failed" in unreadable_decision.source_fit_rejection_reasons
