from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

import core.source_class_recovery_runner as runner_module
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.controller_recovery_decision import (
    CONTROLLER_RECOVERY_DECISION_TRACE_KEY,
    RETRY_RECOVERY,
    STOP_INSUFFICIENT,
    STOP_LEGACY_CUSTODY_GAP,
    STOP_SUFFICIENT,
    build_controller_recovery_decision,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RetrievalAction, RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_LEGAL_PRIMARY = "legal_or_regulatory_text"
_OFFICIAL_CURRENT = "official_current_rules"
_RECOVERY_QUERIES = [
    "Denmark infant formula additives official legal text current rules",
    "Danish competent authority infant formula permitted additives regulation",
]
_DISPATCH_NOT_AUTHORIZED = "source_class_recovery_executor_dispatch_not_authorized"


def _ledger_gap() -> dict[str, Any]:
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
        }
    }


def _approved_lifecycle(**overrides: Any) -> dict[str, Any]:
    trace = {
        "required_source_classes": [_LEGAL_PRIMARY, _OFFICIAL_CURRENT],
        "unsatisfied_required_source_classes": [_LEGAL_PRIMARY, _OFFICIAL_CURRENT],
        "source_obligation_status": "official_current_required_unmet",
        "active_source_class_recovery_considered": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": False,
        "active_source_class_recovery_execution_attempted": False,
        "active_source_class_recovery_official_canonical_admitted": False,
        "active_source_class_recovery_reason": (
            "missing_expected_source_class:legal_or_regulatory_text"
        ),
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": [
            _LEGAL_PRIMARY,
            _OFFICIAL_CURRENT,
        ],
        "active_source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_search_depth": "basic",
        "active_source_class_recovery_attempt_count": 0,
        "active_source_class_recovery_action_envelope": {
            "action_type": RECOVER_MISSING_SOURCE_CLASS,
            "required_source_class": [_LEGAL_PRIMARY, _OFFICIAL_CURRENT],
            "obligation_status": "required",
            "allowed_action": True,
            "blockers": [],
        },
        "authority_lifecycle_required_recovery_allowed": True,
        "authority_lifecycle_weak_corpus_may_own_path": False,
        "authority_lifecycle_execution_state": "approved_pending_execution",
        "authority_lifecycle_execution_attempted": False,
        "authority_lifecycle_execution_blocked": False,
        "authority_lifecycle": {
            "requirement_id": "ag94h-c-denmark-infant-formula-additives",
            "recovery_needed": "required",
            "recovery_action": {
                "action_type": RECOVER_MISSING_SOURCE_CLASS,
                "approved": True,
            },
            "execution_state": {"state": "approved_pending_execution"},
            "explicit_blockers": [],
            "final_posture": "pending_recovery",
        },
        "recovery_slot_available": True,
        "prior_recovery_attempt_count": 0,
        "max_recovery_attempts": 1,
        "candidate_return_status": "not_attempted",
        "candidate_acquisition_considered": False,
        "candidate_acquisition_eligible": False,
        "candidate_acquisition_used": False,
        "acquisition_attempted": False,
    }
    trace.update(overrides)
    return trace


def _runner_context(
    *,
    lifecycle: dict[str, Any],
    authorized_spine_action: str | None,
    controller_recovery_decision: Any | None = None,
    controller: RunController | None = None,
    process_search_queries: Any | None = None,
    all_passages: list[dict[str, Any]] | None = None,
    seen_urls: set[str] | None = None,
    provider_diagnostics: list[dict[str, Any]] | None = None,
    retrieval_pass_records: list[dict[str, Any]] | None = None,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("audit fixture must not run provider/search")

    return SourceClassRecoveryRunnerContext(
        controller=controller or RunController(),
        authorized_spine_action=authorized_spine_action,
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
        provider_diagnostics=(
            provider_diagnostics if provider_diagnostics is not None else []
        ),
        retrieval_pass_records=(
            retrieval_pass_records if retrieval_pass_records is not None else []
        ),
    )


def _controller_with_recovery_action(
    *,
    queries: list[str] | None = None,
    search_depth: str = "basic",
) -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=list(queries or _RECOVERY_QUERIES),
            provider_role="source_class_recovery",
            search_depth=search_depth,
            active=True,
            shadow=False,
            signals={
                "active_source_class_recovery_missing_classes": [
                    _LEGAL_PRIMARY,
                    _OFFICIAL_CURRENT,
                ],
            },
            metadata={
                "controller_action_envelope": {
                    "action_type": RECOVER_MISSING_SOURCE_CLASS,
                    "allowed_action": True,
                    "required_source_class": [
                        _LEGAL_PRIMARY,
                        _OFFICIAL_CURRENT,
                    ],
                }
            },
        )
    )
    return controller


def test_ag94h_d_synthetic_live_shape_dispatches_checkpointless_recovery() -> None:
    lifecycle = _approved_lifecycle(
        **_ledger_gap(),
        final_evidence_official_or_canonical_count=1,
        final_citation_official_or_canonical_count=1,
    )
    decision = build_controller_recovery_decision(lifecycle)
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={},
            source_class_lifecycle_trace=lifecycle,
        )
    )
    search_calls: list[dict[str, Any]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    def fake_search(
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        include_domains: list[str],
        exclude_domains: list[str],
        query_embedding: Any,
        seen: set[str],
        collected_images: set[str],
        embed_provider: str,
        embed_model: str,
        local_url: str,
        embed_texts: Any,
        compute_similarities: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        seen.add("https://agency.example/current-rules")
        search_calls.append(
            {
                "queries": queries,
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "query_embedding": query_embedding,
                "collected_images": collected_images,
                "embed_provider": embed_provider,
                "embed_model": embed_model,
                "local_url": local_url,
                "embed_texts": embed_texts,
                "compute_similarities": compute_similarities,
                **kwargs,
            }
        )
        return [
            {
                "title": "Official current rules",
                "url": "https://agency.example/current-rules",
                "text": "Official current regulatory fixture.",
                "source_tier": "official",
            }
        ]

    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            authorized_spine_action=spine.authorized_dispatch,
            controller_recovery_decision=decision,
            controller=_controller_with_recovery_action(),
            process_search_queries=fake_search,
            all_passages=all_passages,
            seen_urls=seen_urls,
        )
    )

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["source_obligation_status"] == "official_current_required_unmet"
    assert lifecycle["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert decision.decision == RETRY_RECOVERY
    assert decision.retry_allowed is True
    assert decision.payload["allowed_executor_action"] == "execute_existing_recovery_action"
    assert decision.payload["legacy_gap_subordinated_for_recovery_attempt"] is True
    assert decision.payload["legacy_gap_final_success_block_preserved"] is True
    assert decision.payload["legacy_gap_observed"] is True
    assert decision.payload["candidate_state_summary"] != (
        "selected_complete_official_current_evidence_exists"
    )
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "approved_by_authority_lifecycle_required_recovery"
    )
    assert spine.source_class_checkpoint_gate_trace["spine_authorization_source"] == (
        "authority_lifecycle_required_recovery"
    )
    assert result.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 1,
        "new_url_count": 1,
    }
    assert len(search_calls) == 1
    assert search_calls[0]["queries"] == _RECOVERY_QUERIES
    assert search_calls[0]["provider_role"] == "source_class_recovery"
    assert all_passages[0]["retrieval_stage"] == "source_class_recovery"
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True
    assert lifecycle["authority_lifecycle_execution_state"] == "attempted"
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert _DISPATCH_NOT_AUTHORIZED not in str(lifecycle)


def test_ag94h_d_decision_subordinates_legacy_gap_only_for_bounded_attempt() -> None:
    retry_decision = build_controller_recovery_decision(_approved_lifecycle()).payload
    legacy_gap_decision = build_controller_recovery_decision(
        _approved_lifecycle(**_ledger_gap())
    ).payload
    unsafe_legacy_gap_decision = build_controller_recovery_decision(
        _approved_lifecycle(
            **_ledger_gap(),
            active_source_class_recovery_queries=[],
        )
    ).payload

    assert retry_decision["source_obligation_status"] == (
        "official_current_required_unmet"
    )
    assert retry_decision["decision"] == RETRY_RECOVERY
    assert retry_decision["retry_allowed"] is True
    assert retry_decision["allowed_executor_action"] == "execute_existing_recovery_action"

    assert legacy_gap_decision["source_obligation_status"] == (
        "official_current_required_unmet"
    )
    assert legacy_gap_decision["decision"] == RETRY_RECOVERY
    assert legacy_gap_decision["decision_reason"] == (
        "official_current_obligation_unmet_retry_available"
    )
    assert legacy_gap_decision["retry_allowed"] is True
    assert legacy_gap_decision["allowed_executor_action"] == (
        "execute_existing_recovery_action"
    )
    assert legacy_gap_decision["legacy_gap_subordinated_for_recovery_attempt"] is True
    assert legacy_gap_decision["legacy_gap_final_success_block_preserved"] is True

    assert unsafe_legacy_gap_decision["decision"] == STOP_LEGACY_CUSTODY_GAP
    assert unsafe_legacy_gap_decision["retry_allowed"] is False
    assert unsafe_legacy_gap_decision["legacy_gap_subordinated_for_recovery_attempt"] is False


def test_ag94h_d_candidate_state_does_not_trust_legacy_final_counts() -> None:
    export = build_official_canonical_recovery_visibility_export(
        _approved_lifecycle(
            **_ledger_gap(),
            source_survival_final_evidence_official_or_canonical_count=1,
            source_survival_final_citation_official_or_canonical_count=1,
        )
    )
    decision = export[CONTROLLER_RECOVERY_DECISION_TRACE_KEY][
        "ControllerRecoveryDecision"
    ]

    assert export["source_obligation_status"] == "official_current_required_unmet"
    assert export["source_class_recovery_execution_attempted"] is False
    assert export["candidate_return_status"] == "not_attempted"
    assert export["candidate_acquisition_considered"] is False
    assert export["candidate_acquisition_eligible"] is False
    assert export["candidate_acquisition_used"] is False
    assert export["acquisition_attempted"] is False
    assert decision["candidate_state_summary"] != (
        "selected_complete_official_current_evidence_exists"
    )
    assert decision["decision"] == RETRY_RECOVERY
    assert decision["allowed_executor_action"] == "execute_existing_recovery_action"
    assert decision["legacy_gap_subordinated_for_recovery_attempt"] is True
    assert decision["legacy_gap_final_success_block_preserved"] is True


def test_ag94h_d_runner_executes_only_with_recover_missing_source_class_spine() -> None:
    allowed_lifecycle = _approved_lifecycle()
    blocked_lifecycle = _approved_lifecycle()
    decision = build_controller_recovery_decision(allowed_lifecycle)
    calls: list[dict[str, Any]] = []

    def fake_executor(controller: RunController, **kwargs: Any) -> dict[str, int | bool]:
        calls.append({"controller": controller, **kwargs})
        return {"attempted": True, "result_count": 2, "new_url_count": 1}

    with patch.object(
        runner_module,
        "execute_source_class_recovery_action",
        fake_executor,
    ):
        allowed = run_source_class_recovery_dispatch(
            _runner_context(
                lifecycle=allowed_lifecycle,
                authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS,
                controller_recovery_decision=decision,
            )
        )
        blocked = run_source_class_recovery_dispatch(
            _runner_context(
                lifecycle=blocked_lifecycle,
                authorized_spine_action=None,
                controller_recovery_decision=decision,
            )
        )

    assert decision.decision == RETRY_RECOVERY
    assert allowed.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 2,
        "new_url_count": 1,
    }
    assert calls[0]["lifecycle_trace"] is allowed_lifecycle

    assert blocked.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert len(calls) == 1
    assert blocked_lifecycle["active_source_class_recovery_skip_reason"] == (
        _DISPATCH_NOT_AUTHORIZED
    )


@pytest.mark.parametrize(
    ("name", "overrides", "expected_decision"),
    [
        (
            "conflict ownership",
            {"active_source_class_recovery_blockers": ["conflict_resolution_owns_path"]},
            STOP_INSUFFICIENT,
        ),
        (
            "provider policy",
            {
                "active_source_class_recovery_blockers": [
                    "blocked_by_provider_policy_change_required"
                ]
            },
            STOP_INSUFFICIENT,
        ),
        (
            "search depth",
            {
                "active_source_class_recovery_blockers": [
                    "blocked_by_search_depth_escalation_required"
                ]
            },
            STOP_INSUFFICIENT,
        ),
        (
            "hard recovery cap",
            {
                "recovery_slot_available": False,
                "prior_recovery_attempt_count": 1,
                "max_recovery_attempts": 1,
            },
            STOP_LEGACY_CUSTODY_GAP,
        ),
        (
            "no recovery queries",
            {"active_source_class_recovery_queries": []},
            STOP_LEGACY_CUSTODY_GAP,
        ),
        (
            "missing action envelope",
            {"active_source_class_recovery_action_envelope": {}},
            STOP_LEGACY_CUSTODY_GAP,
        ),
        (
            "unsupported source class",
            {
                "required_source_classes": ["social_media_posts"],
                "unsatisfied_required_source_classes": ["social_media_posts"],
                "active_source_class_recovery_missing_classes": [
                    "social_media_posts"
                ],
                "active_source_class_recovery_action_envelope": {
                    "action_type": RECOVER_MISSING_SOURCE_CLASS,
                    "required_source_class": ["social_media_posts"],
                    "obligation_status": "required",
                    "allowed_action": True,
                    "blockers": [],
                },
            },
            STOP_LEGACY_CUSTODY_GAP,
        ),
        (
            "obligation already satisfied",
            {
                "source_obligation_status": "not_required_or_satisfied",
                "unsatisfied_required_source_classes": [],
                "active_source_class_recovery_missing_classes": [],
            },
            STOP_SUFFICIENT,
        ),
        (
            "candidate acquisition already failed",
            {
                "candidate_return_status": "zero_candidates",
                "candidate_acquisition_considered": True,
                "acquisition_attempted": True,
                "active_source_class_recovery_execution_attempted": True,
                "active_source_class_recovery_result_count": 0,
            },
            STOP_LEGACY_CUSTODY_GAP,
        ),
    ],
)
def test_ag94h_d_checkpointless_dispatch_preserves_negative_controls(
    name: str,
    overrides: dict[str, Any],
    expected_decision: str,
) -> None:
    lifecycle = _approved_lifecycle(**_ledger_gap(), **overrides)
    decision = build_controller_recovery_decision(lifecycle)
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={},
            source_class_lifecycle_trace=lifecycle,
        )
    )

    assert decision.decision == expected_decision, name
    assert decision.retry_allowed is False, name
    assert decision.payload["legacy_gap_subordinated_for_recovery_attempt"] is False
    assert spine.authorized_dispatch is None, name
    assert spine.source_class_executor_dispatched is False, name


def test_ag94h_d_terminal_stop_without_required_recovery_override_still_blocks() -> None:
    lifecycle = _approved_lifecycle(
        authority_lifecycle_required_recovery_allowed=False,
        authority_lifecycle={
            "requirement_id": "ag94h-d-terminal-control",
            "recovery_needed": "not_required",
            "recovery_action": {
                "action_type": RECOVER_MISSING_SOURCE_CLASS,
                "approved": False,
            },
            "execution_state": {"state": "not_requested"},
            "explicit_blockers": [],
            "final_posture": "terminal",
        },
    )
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={
                "available": True,
                "decision": {"action_name": "stop_sufficient"},
                "recommended_action_name": "stop_sufficient",
            },
            source_class_lifecycle_trace=lifecycle,
        )
    )

    assert spine.terminal_stop_approved is True
    assert spine.authorized_dispatch is None
    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "blocked_by_terminal_stop"
    )


def test_ag94h_d_executor_does_not_deny_positive_shape_for_legacy_gap() -> None:
    lifecycle = _approved_lifecycle(**_ledger_gap())
    calls: list[list[str]] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls.append(queries)
        return []

    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS,
            controller_recovery_decision=build_controller_recovery_decision(lifecycle),
            controller=_controller_with_recovery_action(),
            process_search_queries=fake_search,
        )
    )

    assert result.source_class_recovery_execution["attempted"] is True
    assert calls == [_RECOVERY_QUERIES]
    assert lifecycle["recovery_decision"] == RETRY_RECOVERY
    assert lifecycle["active_source_class_recovery_skip_reason"] is None


def test_ag94h_d_executor_blocks_when_controller_decision_has_true_hard_blocker() -> None:
    lifecycle = _approved_lifecycle(
        **_ledger_gap(),
        active_source_class_recovery_blockers=[
            "blocked_by_provider_policy_change_required"
        ],
    )
    calls: list[list[str]] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls.append(queries)
        return []

    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            authorized_spine_action=RECOVER_MISSING_SOURCE_CLASS,
            controller_recovery_decision=build_controller_recovery_decision(lifecycle),
            controller=_controller_with_recovery_action(),
            process_search_queries=fake_search,
        )
    )

    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert calls == []
    assert lifecycle["recovery_decision"] == STOP_INSUFFICIENT
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        "controller_recovery_decision_denied_executor_action"
    )
