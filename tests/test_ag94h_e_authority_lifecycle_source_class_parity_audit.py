from __future__ import annotations

from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    _build_authoritative_obligation_state,
    _evidence_fits_for_source_classes,
    build_authoritative_source_obligation_state_and_action,
)
from core.authority_custody_satisfaction import (
    CATEGORY_LOWER_TIER_CONTEXT,
    REASON_AGGREGATE_COUNT_DEMOTED,
    REASON_AGGREGATE_STATUS_DEMOTED,
    REASON_LEGACY_GAP_BLOCKS_AGGREGATE,
    REASON_SELECTED_AUTHORITY_EVIDENCE_SATISFIED,
    authority_custody_satisfaction_for_source_class,
)
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.controller_recovery_decision import (
    RETRY_RECOVERY,
    build_controller_recovery_decision,
)
from core.run_controller import RetrievalAction, RunController
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
    controller_recovery_decision: Any,
    controller: RunController | None = None,
    process_search_queries: Any | None = None,
    all_passages: list[dict[str, Any]] | None = None,
    seen_urls: set[str] | None = None,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("audit fixture must not run provider/search")

    return SourceClassRecoveryRunnerContext(
        controller=controller or RunController(),
        controller_recovery_decision=controller_recovery_decision,
        lifecycle_trace=lifecycle,
        process_search_queries=process_search_queries or fail_search,
        all_passages=all_passages if all_passages is not None else [],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[],
        seen_urls=seen_urls if seen_urls is not None else set(),
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


def _controller_with_recovery_action() -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=list(_RECOVERY_QUERIES),
            provider_role="source_class_recovery",
            search_depth="basic",
            active=True,
            shadow=False,
            signals={
                "active_source_class_recovery_missing_classes": list(_SOURCE_CLASSES),
            },
            metadata={
                "controller_action_envelope": {
                    "action_type": RECOVER_MISSING_SOURCE_CLASS,
                    "allowed_action": True,
                    "required_source_class": list(_SOURCE_CLASSES),
                }
            },
        )
    )
    return controller


def _selected_authority_custody(source_class: str = _OFFICIAL_CURRENT) -> dict[str, Any]:
    return {
        "authority_lifecycle": {
            "candidate_fit": {
                "fit_state": "matched_selected",
                "selected_authority_evidence": [
                    {
                        "requirement_id": source_class,
                        "evidence_id": "agency-current-rule-candidate",
                        "url": "https://agency.example/current-rule",
                        "required_authority": source_class,
                        "observed_source_class": source_class,
                        "satisfies_authority": True,
                    }
                ],
            }
        }
    }


def test_ag94h_f_legacy_aggregate_fit_no_longer_satisfies_authority() -> None:
    observability = _legacy_aggregate_observability()
    status_only = {
        "source_class_satisfaction_status": {
            _LEGAL_PRIMARY: "satisfied_strong",
        },
        "source_class_gap_candidates": [_LEGAL_PRIMARY],
    }

    fits = _evidence_fits_for_source_classes(
        _SOURCE_CLASSES,
        observability,
        recommendation=_recommendation(),
        custody_sources=(_legacy_gap_trace(),),
    )
    state = _build_authoritative_obligation_state(
        recommendation=_recommendation(),
        observability=observability,
        legal_projection=None,
        custody_sources=(_legacy_gap_trace(),),
    )
    status_result = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        status_only,
    )
    gap_result = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        observability,
        _legacy_gap_trace(),
    )
    count_only = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        {"source_class_strong_satisfaction_counts": {_LEGAL_PRIMARY: 1}},
    )
    final_count_only = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        {"final_evidence_official_or_canonical_count": 1},
    )
    survival_count_only = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        {"source_survival_final_citation_official_or_canonical_count": 1},
    )
    weak_context = authority_custody_satisfaction_for_source_class(
        _LEGAL_PRIMARY,
        {
            "source_class_satisfaction_status": {
                _LEGAL_PRIMARY: "expected_but_only_secondary"
            }
        },
    )

    assert fits == ()
    assert status_result.authority_satisfied is False
    assert status_result.reason == REASON_AGGREGATE_STATUS_DEMOTED
    assert gap_result.authority_satisfied is False
    assert gap_result.reason == REASON_LEGACY_GAP_BLOCKS_AGGREGATE
    assert count_only.reason == REASON_AGGREGATE_COUNT_DEMOTED
    assert final_count_only.reason == REASON_AGGREGATE_COUNT_DEMOTED
    assert survival_count_only.reason == REASON_AGGREGATE_COUNT_DEMOTED
    assert weak_context.authority_satisfied is False
    assert weak_context.category == CATEGORY_LOWER_TIER_CONTEXT
    assert {
        requirement.requirement_id
        for requirement in state.missing_authority_requirements()
    } == set(_SOURCE_CLASSES)
    assert {
        satisfaction.requirement_id: satisfaction.status.value
        for satisfaction in state.satisfactions.values()
    } == {
        _LEGAL_PRIMARY: "unfulfilled",
        _OFFICIAL_CURRENT: "unfulfilled",
    }


def test_ag94h_f_action_approved_and_authority_lifecycle_allows_recovery() -> None:
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
        "official_canonical_admitted": True,
        "skip_reason": None,
        "blockers": [],
    }
    assert lifecycle["active_source_class_recovery_missing_classes"] == _SOURCE_CLASSES
    assert lifecycle["active_source_class_recovery_queries"] == _RECOVERY_QUERIES

    assert {
        requirement.requirement_id
        for requirement in handoff.obligation_state.missing_authority_requirements()
    } == set(_SOURCE_CLASSES)
    assert lifecycle["authority_lifecycle_recovery_needed"] == "required"
    assert lifecycle["authority_lifecycle"]["recovery_action"]["action_type"] == (
        RECOVER_MISSING_SOURCE_CLASS
    )
    assert action_trace["authority_lifecycle_arbitration"][
        "authority_lifecycle_recovery_needed"
    ] == "required"

    assert admission["required_source_classes"] == _SOURCE_CLASSES
    assert admission["unsatisfied_required_source_classes"] == _SOURCE_CLASSES
    assert admission["admission_used"] is True
    assert admission["admission_skip_reason"] is None


def test_ag94h_f_downstream_decision_spine_and_runner_dispatch_once() -> None:
    lifecycle = _live_contradiction_trace()

    decision = build_controller_recovery_decision(lifecycle)
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={},
            source_class_lifecycle_trace=lifecycle,
        )
    )
    search_calls: list[list[str]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    def fake_search(
        queries: list[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        search_calls.append(list(queries))
        seen_urls.add("https://agency.example/current-rule")
        return [
            {
                "title": "Official current rule",
                "url": "https://agency.example/current-rule",
                "text": "Offline official current rule fixture.",
                "source_tier": "official",
                "source_class": _OFFICIAL_CURRENT,
            }
        ]

    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            controller_recovery_decision=decision,
            controller=_controller_with_recovery_action(),
            process_search_queries=fake_search,
            all_passages=all_passages,
            seen_urls=seen_urls,
        )
    )

    assert lifecycle["source_obligation_status"] == "official_current_required_unmet"
    assert lifecycle["authority_lifecycle_recovery_needed"] == "required"
    assert lifecycle["authority_lifecycle"]["recovery_action"]["approved"] is True

    assert decision.decision == RETRY_RECOVERY
    assert decision.retry_allowed is True
    assert decision.payload["legacy_gap_observed"] is True
    assert (
        decision.payload["legacy_gap_subordinated_for_recovery_attempt"]
        is True
    )
    assert decision.payload["allowed_executor_action"] == (
        "execute_existing_recovery_action"
    )

    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "approved_by_authority_lifecycle_required_recovery"
    )

    assert result.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 1,
        "new_url_count": 1,
    }
    assert search_calls == [_RECOVERY_QUERIES]
    assert all_passages[0]["retrieval_stage"] == "source_class_recovery"
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert lifecycle["authority_lifecycle"]["execution_state"]["state"] == "attempted"


def test_ag94h_f_true_selected_authority_custody_still_satisfies() -> None:
    observability = _legacy_aggregate_observability(
        source_class_gap_candidates=[_OFFICIAL_CURRENT],
    )
    custody = _selected_authority_custody()

    result = authority_custody_satisfaction_for_source_class(
        _OFFICIAL_CURRENT,
        observability,
        custody,
    )
    fits = _evidence_fits_for_source_classes(
        [_OFFICIAL_CURRENT],
        observability,
        recommendation=_recommendation(
            missing_expected_source_classes=[_OFFICIAL_CURRENT]
        ),
        custody_sources=(custody,),
    )
    state = _build_authoritative_obligation_state(
        recommendation=_recommendation(
            missing_expected_source_classes=[_OFFICIAL_CURRENT]
        ),
        observability=observability,
        legal_projection=None,
        custody_sources=(custody,),
    )

    assert result.authority_satisfied is True
    assert result.reason == REASON_SELECTED_AUTHORITY_EVIDENCE_SATISFIED
    assert [fit.satisfies_authority for fit in fits] == [True]
    assert state.missing_authority_requirements() == ()
