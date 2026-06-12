from __future__ import annotations

from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    _build_authoritative_obligation_state,
    _evidence_fits_for_source_classes,
    build_authoritative_source_obligation_state_and_action,
)
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.controller_recovery_decision import (
    STOP_LEGACY_CUSTODY_GAP,
    build_controller_recovery_decision,
)
from core.run_controller import RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_LEGAL_PRIMARY = "legal_or_regulatory_text"
_OFFICIAL_CURRENT = "official_current_rules"
_SOURCE_CLASSES = [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
_RECOVERY_QUERIES = [
    "Denmark infant formula additives official legal text current rules",
    "Danish competent authority infant formula permitted additives regulation",
]
_DISPATCH_NOT_AUTHORIZED = "source_class_recovery_executor_dispatch_not_authorized"


def _recommendation(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": list(_SOURCE_CLASSES),
        "source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "source_class_recovery_query_count": len(_RECOVERY_QUERIES),
        "source_class_recovery_reason": (
            "missing_expected_source_class:legal_or_regulatory_text"
        ),
        "source_class_recovery_trigger_fields": [
            "runtime_source_class_expectation",
            "official_source_obligation_trace",
        ],
    }
    payload.update(overrides)
    return payload


def _legacy_aggregate_observability(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_satisfaction_status": {
            _LEGAL_PRIMARY: "satisfied_strong",
            _OFFICIAL_CURRENT: "satisfied_strong",
        },
        "source_class_strong_satisfaction_counts": {
            _LEGAL_PRIMARY: 1,
            _OFFICIAL_CURRENT: 1,
        },
        "source_class_gap_candidates": list(_SOURCE_CLASSES),
    }
    payload.update(overrides)
    return payload


def _facts() -> AuthoritativeSourceActionFacts:
    return AuthoritativeSourceActionFacts(
        query=(
            "What official legal or regulatory source currently lists which "
            "preservatives or additives are permitted in infant formula sold "
            "in Denmark?"
        ),
        intent="general",
        report_type="answer",
        query_type="food_regulatory_non_us",
        core_topic="Denmark infant formula additives permitted preservatives",
        primary_entity="Danish food authority",
        recommendation=_recommendation(),
        source_class_observability=_legacy_aggregate_observability(),
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"example.org": 2},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        current_search_depth="basic",
        iteration_budget_available=True,
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )


def _handoff() -> Any:
    return build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(),
    )


def _legacy_gap_trace() -> dict[str, Any]:
    return {
        CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY: {
            "ControllerEvidenceLedger": {
                "final_evidence_citation_custody": {
                    "owner": "ControllerEvidenceLedger",
                    "status": "legacy_gap_observed",
                    "custody_complete": False,
                    "legacy_gap_types": [
                        "final_evidence_or_citation_without_candidate_passport_custody",
                        "final_evidence_or_citation_without_final_selected_authority_evidence",
                        "provider_result_to_final_evidence_custody_parallel_path",
                    ],
                }
            }
        },
        "final_evidence_citation_custody_status": "legacy_gap_observed",
        "final_evidence_citation_custody_complete": False,
        "ledger_legacy_gap_types": [
            "final_evidence_or_citation_without_candidate_passport_custody",
            "final_evidence_or_citation_without_final_selected_authority_evidence",
            "provider_result_to_final_evidence_custody_parallel_path",
        ],
    }


def _live_contradiction_trace() -> dict[str, Any]:
    lifecycle = dict(_handoff().active_source_class_recovery_lifecycle)
    lifecycle.update(
        {
            "required_source_classes": list(_SOURCE_CLASSES),
            "unsatisfied_required_source_classes": list(_SOURCE_CLASSES),
            "source_obligation_status": "official_current_required_unmet",
            "recovery_slot_available": True,
            "max_recovery_attempts": 1,
            "candidate_return_status": "not_attempted",
            "candidate_acquisition_considered": False,
            "candidate_acquisition_eligible": False,
            "candidate_acquisition_used": False,
            "acquisition_attempted": False,
            **_legacy_gap_trace(),
        }
    )
    return lifecycle


def _runner_context(
    *,
    lifecycle: dict[str, Any],
    authorized_spine_action: str | None,
    controller_recovery_decision: Any,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("audit fixture must not run provider/search")

    return SourceClassRecoveryRunnerContext(
        controller=RunController(),
        authorized_spine_action=authorized_spine_action,
        controller_recovery_decision=controller_recovery_decision,
        lifecycle_trace=lifecycle,
        process_search_queries=fail_search,
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
        entity_hint="Denmark infant formula additives",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )


def test_ag94h_e_first_divergence_legacy_aggregate_fit_satisfies_authority() -> None:
    observability = _legacy_aggregate_observability()

    fits = _evidence_fits_for_source_classes(_SOURCE_CLASSES, observability)
    state = _build_authoritative_obligation_state(
        recommendation=_recommendation(),
        observability=observability,
        legal_projection=None,
    )

    assert [fit.evidence_id for fit in fits] == [
        f"{_LEGAL_PRIMARY}:satisfied_strong",
        f"{_OFFICIAL_CURRENT}:satisfied_strong",
    ]
    assert all(fit.satisfies_authority for fit in fits)
    assert state.missing_authority_requirements() == ()
    assert {
        satisfaction.requirement_id: satisfaction.status.value
        for satisfaction in state.satisfactions.values()
    } == {
        _LEGAL_PRIMARY: "fulfilled",
        _OFFICIAL_CURRENT: "fulfilled",
    }


def test_ag94h_e_action_approved_but_authority_lifecycle_says_recovery_not_needed() -> None:
    handoff = _handoff()
    lifecycle = handoff.active_source_class_recovery_lifecycle
    action_trace = handoff.trace
    admission = handoff.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert handoff.action_decision.approved is True
    assert action_trace["action_decision"]["approved"] is True
    assert action_trace["source_class_lifecycle_summary"] == {
        "eligible": True,
        "used": False,
        "execution_attempted": False,
        "official_canonical_admitted": False,
        "skip_reason": None,
        "blockers": [],
    }
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_missing_classes"] == _SOURCE_CLASSES
    assert lifecycle["active_source_class_recovery_queries"] == _RECOVERY_QUERIES
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert lifecycle["active_source_class_recovery_search_depth"] == "basic"
    assert lifecycle["active_source_class_recovery_attempt_count"] == 1

    assert handoff.obligation_state.missing_authority_requirements() == ()
    assert lifecycle["authority_lifecycle_recovery_needed"] == "not_needed"
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is False
    assert lifecycle["authority_lifecycle_execution_state"] == "not_requested"
    assert lifecycle["authority_lifecycle_execution_blocked"] is False
    assert lifecycle["authority_lifecycle"]["recovery_action"] is None
    assert action_trace["authority_lifecycle_arbitration"][
        "authority_lifecycle_recovery_needed"
    ] == "not_needed"
    assert action_trace["authority_lifecycle_arbitration"][
        "authority_lifecycle_required_recovery_allowed"
    ] is False

    assert admission["required_source_classes"] == _SOURCE_CLASSES
    assert admission["unsatisfied_required_source_classes"] == []
    assert admission["admission_used"] is False
    assert admission["admission_skip_reason"] == "existing_source_class_satisfied"


def test_ag94h_e_downstream_decision_and_spine_preserve_the_no_dispatch_block() -> None:
    lifecycle = _live_contradiction_trace()

    decision = build_controller_recovery_decision(lifecycle)
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={},
            source_class_lifecycle_trace=lifecycle,
        )
    )
    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            authorized_spine_action=spine.authorized_dispatch,
            controller_recovery_decision=decision,
        )
    )

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["source_obligation_status"] == "official_current_required_unmet"
    assert lifecycle["authority_lifecycle_required_recovery_allowed"] is False
    assert lifecycle["authority_lifecycle_recovery_needed"] == "not_needed"

    assert decision.decision == STOP_LEGACY_CUSTODY_GAP
    assert decision.retry_allowed is False
    assert decision.payload["allowed_executor_action"] == "no_recovery_executor_action"
    assert decision.payload["legacy_gap_observed"] is True
    assert (
        decision.payload["legacy_gap_subordinated_for_recovery_attempt"]
        is False
    )

    assert spine.authorized_dispatch is None
    assert spine.source_class_executor_dispatched is False
    assert spine.source_class_checkpoint_gate_trace[
        "authority_lifecycle_required_recovery_allowed"
    ] is False
    assert spine.source_class_checkpoint_gate_trace["executor_dispatched"] is False
    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "checkpoint_unavailable"
    )

    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert lifecycle["active_source_class_recovery_used"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        _DISPATCH_NOT_AUTHORIZED
    )
    assert lifecycle["authority_lifecycle_execution_state"] == "blocked"
    assert lifecycle["authority_lifecycle_execution_blocked"] is True
    assert lifecycle["authority_lifecycle_execution_blocker"]["reason"] == (
        _DISPATCH_NOT_AUTHORIZED
    )
