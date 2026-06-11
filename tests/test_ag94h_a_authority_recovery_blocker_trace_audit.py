from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.controller_loop_spine import (
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
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": list(missing_expected_source_classes),
        "source_class_recovery_reason": (
            "missing_expected_source_class:legal_or_regulatory_text"
        ),
        "source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "source_class_recovery_query_count": len(_RECOVERY_QUERIES),
        "source_class_recovery_trigger_fields": [
            "official_source_obligation_trace",
            "source_tier_counts",
            "source_domain_counts",
        ],
        "official_canonical_acquisition_path_visible": True,
        "official_canonical_acquisition_path_visibility_source": (
            "synthetic_status_only_gap"
        ),
        "source_class_satisfaction_status": {
            _LEGAL_PRIMARY: "expected_but_only_secondary",
            _OFFICIAL_CURRENT: "expected_but_only_secondary",
        },
        "source_class_strong_satisfaction_counts": {
            _LEGAL_PRIMARY: 0,
            _OFFICIAL_CURRENT: 0,
        },
        "active_source_class_recovery_blockers": [
            "weak_corpus_recovery_owns_path",
            "blocked_by_corpus_weak",
        ],
        "source_class_recovery_candidate_v2_blockers": [
            "weak_corpus_recovery_owns_path",
            "blocked_by_corpus_weak",
        ],
    }


def _orchestrator_state(
    *,
    recommendation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "query": _DANISH_QUERY,
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": (
            "preservatives and additives permitted in infant formula sold in Denmark"
        ),
        "primary_entity": "infant formula sold in Denmark",
        "_source_class_recovery_lifecycle_recommendation": (
            recommendation if recommendation is not None else _recommendation()
        ),
        "_source_class_recovery_answer_contract_observability": {
            "source_class_satisfaction_status": {
                _LEGAL_PRIMARY: "expected_but_only_secondary",
                _OFFICIAL_CURRENT: "expected_but_only_secondary",
            },
            "source_class_strong_satisfaction_counts": {
                _LEGAL_PRIMARY: 0,
                _OFFICIAL_CURRENT: 0,
            },
        },
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
        "corpus_state": "OFF_TOPIC",
        "corpus_weak": True,
        "weak_corpus_recovery_considered": True,
        "weak_corpus_recovery_used": True,
        "weak_corpus_recovery_skip_reason": "weak_corpus_recovery_used",
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 1,
        "waste_flags": [],
    }


def _handoff(
    *,
    recommendation: dict[str, Any] | None = None,
) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state=_orchestrator_state(recommendation=recommendation),
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


def test_ag94h_a_full_handoff_blocks_after_admission_when_required_class_is_status_only() -> None:
    handoff = _handoff()
    admission = _admission_payload(handoff)
    acquisition = _acquisition_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={},
            source_class_lifecycle_trace=lifecycle,
        )
    )

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
    assert acquisition["acquisition_repair_skip_reason"] == "existing_runtime_blocker"
    assert acquisition["official_authority_acquisition_plan"][
        "source_classes_required"
    ] == []
    assert acquisition["official_authority_acquisition_plan"]["query_variants"] == []

    assert lifecycle["active_source_class_recovery_eligible"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "blocked_by_weak_corpus_recovery"
    )
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is False
    assert lifecycle["active_source_class_recovery_missing_classes"] == []
    assert "no_missing_expected_source_class" in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert "blocked_by_weak_corpus_recovery" in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is False
    assert lifecycle["authority_lifecycle_weak_corpus_may_own_path"] is True
    assert lifecycle["authority_lifecycle_execution_state"] == "not_requested"

    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "blocked_by_lifecycle"
    )
    assert spine.source_class_executor_dispatched is False


def test_ag94h_a_visibility_export_rehydrates_missing_classes_not_seen_by_lifecycle() -> None:
    handoff = _handoff()
    admission = _admission_payload(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    export = _visibility_export(handoff)

    assert lifecycle["active_source_class_recovery_missing_classes"] == []
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
    assert export["source_class_recovery_eligible"] is False
    assert export["source_class_recovery_execution_attempted"] is False
    assert export["candidate_return_status"] == "not_attempted"


def test_ag94h_a_populating_missing_expected_class_breaks_the_audit_cycle() -> None:
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
