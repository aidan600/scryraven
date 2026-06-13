from __future__ import annotations

from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.official_canonical_recovery_visibility_export import (
    NOT_OBSERVABLE,
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY,
    append_official_canonical_recovery_diagnostics_section,
)
from core.run_controller import RunController
from core.runtime_trace_export_attachment import (
    attach_runtime_trace_export_compatibility_payloads,
)
from core.session_output_projection import build_execution_trace_projection
from tests.test_ag93e8_r1_weak_corpus_official_acquisition_handoff import (
    _handoff,
    _orchestrator_state,
)
from tests.test_session_output_projection_ag90a import _runtime_values

_OFFICIAL_CURRENT = "official_current_rules"
_WEAK_CORPUS_BLOCKERS = {
    "weak_corpus_recovery_owns_path",
    "blocked_by_corpus_weak",
    "blocked_by_weak_corpus_recovery",
}


def _cli_shaped_final_projection(handoff: Any) -> tuple[dict[str, Any], dict[str, Any], str]:
    runtime = _runtime_values()
    runtime.update(
        {
            "query": (
                "Do U.S. air travelers need a REAL ID or other acceptable "
                "identification for domestic flights now, and when did "
                "enforcement start? Use current official sources."
            ),
            "core_topic": "REAL ID or other acceptable identification for domestic flights",
            "primary_entity": "domestic air traveler identification requirements",
            "corpus_state": "OFF_TOPIC",
            "corpus_weak": True,
            "weak_corpus_recovery_considered": True,
            "weak_corpus_recovery_used": True,
            "weak_corpus_recovery_skip_reason": "weak_corpus_recovery_used",
            "active_source_class_recovery_lifecycle": (
                handoff.active_source_class_recovery_lifecycle
            ),
            "authoritative_source_action_trace": handoff.authoritative_source_action_trace,
            "official_source_obligation_bridge_trace": (
                handoff.official_source_obligation_bridge_trace or {}
            ),
            "official_canonical_recovery_query_acquisition_trace": (
                handoff.official_canonical_recovery_query_acquisition_trace or {}
            ),
            "official_canonical_recovery_execution_admission_trace": (
                handoff.official_canonical_recovery_execution_admission_trace or {}
            ),
            "source_class_recovery_telemetry": handoff.recommendation,
            "source_class_observability_telemetry": {
                "source_class_strong_satisfaction_counts": {_OFFICIAL_CURRENT: 0}
            },
            "source_class_evidence_bundle_observability_telemetry": {
                "source_class_strong_satisfaction_counts": {_OFFICIAL_CURRENT: 0}
            },
            "_source_tier_exec": {
                "source_tier_counts": {"secondary": 3},
                "official_evidence_found": False,
                "community_signal_found": False,
                "low_trust_sources_found": False,
                "pollution_detected": False,
            },
            "_source_domain_exec": {
                "source_domain_counts": {"news.example": 2, "analysis.example": 1},
                "top_source_domains": [{"domain": "news.example", "count": 2}],
                "unique_source_domain_count": 2,
                "on_domain_source_count": 0,
                "off_domain_source_count": 2,
            },
        }
    )
    execution_trace = build_execution_trace_projection(runtime)
    attach_runtime_trace_export_compatibility_payloads(
        execution_trace,
        recovered_passages=[],
        final_top_evidence=[],
        max_iterations=1,
        evidence_bundle_source_class_counts={_OFFICIAL_CURRENT: 0},
    )
    export = execution_trace[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY][
        "OfficialCanonicalRecoveryVisibility"
    ]
    rendered = append_official_canonical_recovery_diagnostics_section(
        "Final answer body.",
        execution_trace,
    )
    return execution_trace, export, rendered


def _handoff_from_state(**updates: Any) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        RunController(),
        orchestrator_state={**_orchestrator_state(), **updates},
    )


def test_ag94b_cli_shaped_custody_preserves_official_current_recovery_lane() -> None:
    _trace, export, rendered = _cli_shaped_final_projection(_handoff())

    assert export["required_source_class"] == [_OFFICIAL_CURRENT]
    assert export["required_source_classes"] == [_OFFICIAL_CURRENT]
    assert export["unsatisfied_required_source_classes"] == [_OFFICIAL_CURRENT]
    assert export["source_obligation_status"] == "official_current_required_unmet"
    assert "controller_recovery_decision_observed" not in export
    assert "controller_recovery_decision" not in export
    assert "controller_recovery_retry_allowed" not in export
    assert export["admission_used"] is True
    assert export["recovery_query_count"] > 0
    assert export["acquisition_repair_used"] is True
    assert export["official_authority_acquisition_plan"] != NOT_OBSERVABLE
    assert export["weak_corpus_coexistence_reason"] == (
        "unsatisfied_official_current_recovery_lane"
    )
    assert export["candidate_return_status"] == "not_attempted"
    assert "`required_source_class`: official_current_rules" in rendered
    assert "`source_obligation_status`: official_current_required_unmet" in rendered
    assert "`acquisition_repair_used`: true" in rendered


def test_ag94b_final_diagnostics_reports_absent_runtime_decision() -> None:
    handoff = _handoff()
    _trace, export, _rendered = _cli_shaped_final_projection(handoff)
    lifecycle = handoff.active_source_class_recovery_lifecycle

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert export["source_obligation_status"] == "official_current_required_unmet"
    assert "controller_recovery_decision_observed" not in export
    assert "controller_recovery_decision" not in export


def test_ag94b_final_projection_does_not_restore_weak_corpus_blockers() -> None:
    execution_trace, export, _rendered = _cli_shaped_final_projection(_handoff())

    assert export["admission_used"] is True
    assert not (_WEAK_CORPUS_BLOCKERS & set(export["admission_blockers"]))
    assert not (
        _WEAK_CORPUS_BLOCKERS
        & set(execution_trace["active_source_class_recovery_blockers"])
    )


def test_ag94b_private_gym_negative_control_has_no_official_current_action() -> None:
    handoff = _handoff(
        query=(
            "Explain why private gyms ask for identification documents when "
            "people sign up for membership."
        ),
        core_topic="private gym membership identification explainer",
        primary_entity="private gym membership",
    )
    execution_trace, export, _rendered = _cli_shaped_final_projection(handoff)

    assert export["required_source_class"] == []
    assert export["source_obligation_status"] == "not_required_or_satisfied"
    assert export["acquisition_repair_used"] is False
    assert export["admission_used"] is False
    assert "controller_recovery_decision_observed" not in export
    assert "controller_recovery_decision" not in export
    assert _WEAK_CORPUS_BLOCKERS & set(
        execution_trace["active_source_class_recovery_blockers"]
    )


def test_ag94b_hard_blockers_remain_blocking_in_final_diagnostics() -> None:
    hard_cap_controller = RunController()
    hard_cap_controller.state.active_source_class_recovery_attempt_count = 1
    cases = [
        (
            "terminal_stop",
            _handoff(terminal_stop_approved=True),
            "terminal_stop_approved",
            "terminal_stop",
        ),
        (
            "hard_cap",
            build_authoritative_source_action_orchestrator_handoff(
                hard_cap_controller,
                orchestrator_state=_orchestrator_state(),
            ),
            "budget_hard_exhausted",
            "hard_recovery_cap",
        ),
        (
            "conflict_resolution",
            _handoff_from_state(conflict_resolution_owns_path=True),
            "conflict_resolution_owns_path",
            "conflict_resolution",
        ),
        (
            "provider_policy",
            _handoff_from_state(provider_policy_reusable=False),
            "blocked_by_provider_policy_change_required",
            "provider_policy_or_depth",
        ),
        (
            "search_depth",
            _handoff_from_state(
                search_depth_reusable=False,
                search_depth_escalation_required=True,
            ),
            "blocked_by_search_depth_escalation_required",
            "provider_policy_or_depth",
        ),
    ]

    for name, handoff, blocker, _hard_blocker_state in cases:
        _trace, export, _rendered = _cli_shaped_final_projection(handoff)

        assert export["admission_used"] is False, name
        assert blocker in export["admission_blockers"], name
        assert "controller_recovery_decision_observed" not in export, name
        assert "controller_recovery_decision" not in export, name


def test_ag94b_phase_stays_offline_without_provider_or_search_execution() -> None:
    _trace, export, _rendered = _cli_shaped_final_projection(_handoff())

    assert export["source_class_recovery_execution_attempted"] is False
    assert export["candidate_return_status"] == "not_attempted"
    assert export["candidate_acquisition_used"] is False
    assert export["provider_search_allocation_trace"] == NOT_OBSERVABLE
    assert export["provider_search_allocation_execution_trace"] == NOT_OBSERVABLE
