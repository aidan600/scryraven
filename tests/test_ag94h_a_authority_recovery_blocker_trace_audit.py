from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RunController

_LEGAL_PRIMARY = "legal_or_regulatory_text"
_OFFICIAL_CURRENT = "official_current_rules"
_DANISH_QUERY = (
    "What official legal or regulatory source currently lists which "
    "preservatives or additives are permitted in infant formula sold in "
    "Denmark? Answer from official/current regulatory sources if available."
)
_RECOVERY_QUERIES = (
    "infant formula additives official legal text current regulatory source "
    "competent authority",
    "infant formula additives competent authority primary legal source",
)


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=None,
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        fulfillment_handoff=SimpleNamespace(unfulfilled_items=(), partial_items=()),
    )


def _recommendation(
    *,
    missing_expected_source_classes: tuple[str, ...] = (),
    recommended: bool = True,
    queries: tuple[str, ...] | None = _RECOVERY_QUERIES,
    reason: str | None = None,
    status: dict[str, str] | None = None,
    strong_counts: dict[str, int] | None = None,
    weak_blockers: bool = True,
) -> dict[str, Any]:
    blockers = (
        [
            "weak_corpus_recovery_owns_path",
            "blocked_by_corpus_weak",
        ]
        if weak_blockers
        else []
    )
    recovery_queries = tuple(queries or ())
    status_map = (
        {
            _LEGAL_PRIMARY: "expected_but_only_secondary",
            _OFFICIAL_CURRENT: "expected_but_only_secondary",
        }
        if status is None
        else dict(status)
    )
    strong_count_map = (
        {
            _LEGAL_PRIMARY: 0,
            _OFFICIAL_CURRENT: 0,
        }
        if strong_counts is None
        else dict(strong_counts)
    )
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": list(missing_expected_source_classes),
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else "missing_expected_source_class:legal_or_regulatory_text"
            if recommended
            else None
        ),
        "source_class_recovery_queries": list(recovery_queries),
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_trigger_fields": [
            "official_source_obligation_trace",
            "source_tier_counts",
            "source_domain_counts",
        ],
        "official_canonical_acquisition_path_visible": True,
        "official_canonical_acquisition_path_visibility_source": (
            "synthetic_status_only_gap"
        ),
        "source_class_satisfaction_status": status_map,
        "source_class_strong_satisfaction_counts": strong_count_map,
        "active_source_class_recovery_blockers": list(blockers),
        "source_class_recovery_candidate_v2_blockers": list(blockers),
    }


def _orchestrator_state(
    *,
    query: str = _DANISH_QUERY,
    core_topic: str = (
        "preservatives and additives permitted in infant formula sold in Denmark"
    ),
    primary_entity: str = "infant formula sold in Denmark",
    recommendation: dict[str, Any] | None = None,
    source_class_observability: dict[str, Any] | None = None,
    corpus_weak: bool = True,
    weak_corpus_recovery_used: bool = True,
    terminal_stop_approved: bool = False,
    conflict_resolution_owns_path: bool = False,
    provider_policy_reusable: bool = True,
    search_depth_reusable: bool = True,
    search_depth_escalation_required: bool = False,
    iterations_run: int = 0,
    max_iterations: int = 1,
) -> dict[str, Any]:
    rec = recommendation if recommendation is not None else _recommendation()
    observability = (
        source_class_observability
        if source_class_observability is not None
        else {
            "source_class_satisfaction_status": rec.get(
                "source_class_satisfaction_status",
                {},
            ),
            "source_class_strong_satisfaction_counts": rec.get(
                "source_class_strong_satisfaction_counts",
                {},
            ),
        }
    )
    return {
        "query": query,
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": core_topic,
        "primary_entity": primary_entity,
        "_source_class_recovery_lifecycle_recommendation": rec,
        "_source_class_recovery_answer_contract_observability": observability,
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 3},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"trade.example": 2, "manufacturer.example": 1},
            "top_source_domains": [{"domain": "trade.example", "count": 2}],
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
        "conflict_resolution_owns_path": conflict_resolution_owns_path,
        "provider_policy_reusable": provider_policy_reusable,
        "search_depth_reusable": search_depth_reusable,
        "search_depth_escalation_required": search_depth_escalation_required,
    }


def _handoff(
    *,
    controller: RunController | None = None,
    recommendation: dict[str, Any] | None = None,
    **state_overrides: Any,
) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        controller or RunController(),
        orchestrator_state=_orchestrator_state(
            recommendation=recommendation,
            **state_overrides,
        ),
    )


def _admission_payload(handoff: Any) -> dict[str, Any]:
    return handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]


def _acquisition_payload(handoff: Any) -> dict[str, Any]:
    return handoff.official_canonical_recovery_query_acquisition_trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]


def _visibility_export(handoff: Any) -> dict[str, Any]:
    trace = dict(handoff.active_source_class_recovery_lifecycle)
    trace[OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY] = (
        handoff.official_canonical_recovery_query_acquisition_trace
    )
    trace[OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY] = (
        handoff.official_canonical_recovery_execution_admission_trace
    )
    return build_official_canonical_recovery_visibility_export(trace)


def test_ag94h_b_status_only_required_classes_approve_lifecycle_before_weak_arbitration() -> None:
    controller = RunController()
    handoff = _handoff(controller=controller)
    admission = _admission_payload(handoff)
    acquisition = _acquisition_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={
                "available": True,
                "decision": {"action_name": RECOVER_MISSING_SOURCE_CLASS},
                "recommended_action_name": RECOVER_MISSING_SOURCE_CLASS,
            },
            source_class_lifecycle_trace=lifecycle,
        )
    )
    recorded_actions = controller.snapshot_ledger()["retrieval_actions"]

    assert admission["admission_considered"] is True
    assert admission["admission_acquisition_path_visible"] is True
    assert admission["required_source_classes"] == [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
    assert admission["unsatisfied_required_source_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert admission["admission_used"] is True
    assert admission["weak_corpus_coexistence_reason"] == (
        "unsatisfied_official_current_recovery_lane"
    )

    assert acquisition["acquisition_repair_considered"] is True
    assert acquisition["acquisition_repair_eligible"] is False
    assert acquisition["acquisition_repair_used"] is False
    assert acquisition["acquisition_repair_skip_reason"] == (
        "required_source_class_not_visible_or_supported_for_query"
    )
    assert acquisition["official_authority_acquisition_plan"][
        "source_classes_required"
    ] == []
    assert acquisition["official_authority_acquisition_plan"]["query_variants"] == []

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert lifecycle["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert "no_missing_expected_source_class" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert lifecycle["authority_lifecycle_execution_state"] == (
        "approved_pending_execution"
    )

    assert spine.source_class_executor_dispatched is True
    assert recorded_actions[0]["name"] == "source_class_recovery"
    assert recorded_actions[0]["metadata"]["execution"] == (
        "controller_approved_pending_executor"
    )


def test_ag94h_b_visibility_export_matches_lifecycle_normalized_missing_classes() -> None:
    handoff = _handoff()
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    export = _visibility_export(handoff)

    assert lifecycle["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert admission["required_source_classes"] == [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
    assert export["required_source_classes"] == [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
    assert export["unsatisfied_required_source_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert export["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert export["source_obligation_status"] == "official_current_required_unmet"
    assert export["source_class_recovery_eligible"] is True
    assert export["source_class_recovery_execution_attempted"] is False
    assert export["candidate_return_status"] == "not_attempted"


def test_ag94h_b_observability_only_status_maps_feed_lifecycle_control_input() -> None:
    recommendation = _recommendation(status={}, strong_counts={})
    handoff = _handoff(
        recommendation=recommendation,
        source_class_observability={
            "source_class_satisfaction_status": {
                _LEGAL_PRIMARY: "unsatisfied",
                _OFFICIAL_CURRENT: "expected_but_only_secondary",
            },
            "source_class_strong_satisfaction_counts": {
                _LEGAL_PRIMARY: 0,
                _OFFICIAL_CURRENT: 0,
            },
        },
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]


def test_ag94h_b_existing_explicit_missing_classes_still_approve() -> None:
    handoff = _handoff(
        recommendation=_recommendation(
            missing_expected_source_classes=(_LEGAL_PRIMARY, _OFFICIAL_CURRENT)
        )
    )
    admission = _admission_payload(handoff)
    acquisition = _acquisition_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is True
    assert acquisition["official_authority_acquisition_plan"][
        "source_classes_required"
    ] == [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is True
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is False
    assert not (
        {"weak_corpus_recovery_owns_path", "blocked_by_corpus_weak"}
        & set(admission["admission_blockers"])
    )


def test_ag94h_b_ordinary_weak_corpus_without_strong_status_still_blocks() -> None:
    handoff = _handoff(
        query="Explain why coffee tastes bitter in simple terms.",
        core_topic="coffee bitterness explainer",
        primary_entity="coffee bitterness",
        recommendation=_recommendation(
            recommended=False,
            queries=(),
            status={},
            strong_counts={},
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_missing_classes"] == []
    assert "blocked_by_weak_corpus_recovery" in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_ag94h_b_unsupported_status_only_class_is_not_promoted() -> None:
    handoff = _handoff(
        query="Find an academic explainer about a research topic.",
        core_topic="academic explainer",
        primary_entity="research topic",
        recommendation=_recommendation(
            reason="missing_expected_source_class:peer_reviewed_paper",
            status={"peer_reviewed_paper": "unsatisfied"},
            strong_counts={"peer_reviewed_paper": 0},
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_missing_classes"] == []
    assert "no_missing_expected_source_class" in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_ag94h_b_satisfied_strong_or_positive_count_is_not_promoted() -> None:
    handoff = _handoff(
        recommendation=_recommendation(
            status={
                _LEGAL_PRIMARY: "satisfied_strong",
                _OFFICIAL_CURRENT: "satisfied_strong",
            },
            strong_counts={
                _LEGAL_PRIMARY: 1,
                _OFFICIAL_CURRENT: 1,
            },
        )
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_missing_classes"] == []
    assert "no_missing_expected_source_class" in lifecycle[
        "active_source_class_recovery_blockers"
    ]


def test_ag94h_b_status_only_class_without_recovery_queries_remains_ineligible() -> None:
    handoff = _handoff(recommendation=_recommendation(queries=()))
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is False
    assert admission["recovery_query_available"] is False
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_missing_classes"] == []
    assert "no_recovery_queries" in lifecycle["active_source_class_recovery_blockers"]


def test_ag94h_b_terminal_stop_still_blocks_status_only_recovery() -> None:
    handoff = _handoff(terminal_stop_approved=True)
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is False
    assert "terminal_stop_approved" in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "blocked_by_terminal_stop"
    )


def test_ag94h_b_conflict_resolution_still_blocks_status_only_recovery() -> None:
    handoff = _handoff(conflict_resolution_owns_path=True)
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is False
    assert "conflict_resolution_owns_path" in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "conflict_resolution_owns_path"
    )


def test_ag94h_b_provider_and_depth_blockers_still_block_status_only_recovery() -> None:
    provider_handoff = _handoff(provider_policy_reusable=False)
    depth_handoff = _handoff(
        search_depth_reusable=False,
        search_depth_escalation_required=True,
    )
    provider_lifecycle = provider_handoff.active_source_class_recovery_lifecycle
    depth_lifecycle = depth_handoff.active_source_class_recovery_lifecycle

    assert provider_lifecycle["active_source_class_recovery_eligible"] is False
    assert "blocked_by_provider_policy_change_required" in (
        provider_lifecycle["active_source_class_recovery_blockers"]
    )
    assert depth_lifecycle["active_source_class_recovery_eligible"] is False
    assert "blocked_by_search_depth_escalation_required" in (
        depth_lifecycle["active_source_class_recovery_blockers"]
    )


def test_ag94h_b_prior_attempt_cap_still_blocks_status_only_recovery() -> None:
    controller = RunController()
    controller.state.active_source_class_recovery_attempt_count = 1
    handoff = _handoff(controller=controller)
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert admission["admission_used"] is False
    assert "budget_hard_exhausted" in admission["admission_blockers"]
    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == "already_attempted"
