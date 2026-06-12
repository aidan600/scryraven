from __future__ import annotations

from typing import Any
from unittest.mock import patch

import core.source_class_recovery_runner as runner_module
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.controller_recovery_decision import (
    CONTINUE_DOWNSTREAM,
    CONTROLLER_RECOVERY_DECISION_TRACE_KEY,
    RETRY_RECOVERY,
    STOP_LEGACY_CUSTODY_GAP,
    build_controller_recovery_decision,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.run_controller import RunController
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


def test_ag94h_c_synthetic_live_signal_reproduces_dispatch_not_authorized() -> None:
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

    result = run_source_class_recovery_dispatch(
        _runner_context(
            lifecycle=lifecycle,
            authorized_spine_action=spine.authorized_dispatch,
            controller_recovery_decision=decision,
        )
    )

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["source_obligation_status"] == "official_current_required_unmet"
    assert lifecycle["active_source_class_recovery_missing_classes"] == [
        _LEGAL_PRIMARY,
        _OFFICIAL_CURRENT,
    ]
    assert decision.decision == STOP_LEGACY_CUSTODY_GAP
    assert decision.payload["allowed_executor_action"] == "no_recovery_executor_action"
    assert spine.authorized_dispatch is None
    assert spine.source_class_checkpoint_gate_trace["gate_reason"] == (
        "checkpoint_unavailable"
    )
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False
    assert lifecycle["active_source_class_recovery_skip_reason"] == (
        _DISPATCH_NOT_AUTHORIZED
    )
    assert lifecycle["authority_lifecycle_execution_blocked"] is True
    assert lifecycle["authority_lifecycle_execution_blocker"]["reason"] == (
        _DISPATCH_NOT_AUTHORIZED
    )


def test_ag94h_c_decision_table_legacy_gap_wins_over_unmet_retry() -> None:
    retry_decision = build_controller_recovery_decision(_approved_lifecycle()).payload
    legacy_gap_decision = build_controller_recovery_decision(
        _approved_lifecycle(**_ledger_gap())
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
    assert legacy_gap_decision["decision"] == STOP_LEGACY_CUSTODY_GAP
    assert legacy_gap_decision["decision_reason"] == "legacy_gap_observed_not_success"
    assert legacy_gap_decision["retry_allowed"] is False
    assert legacy_gap_decision["allowed_executor_action"] == "no_recovery_executor_action"


def test_ag94h_c_candidate_state_can_trust_final_counts_while_not_attempted() -> None:
    export = build_official_canonical_recovery_visibility_export(
        _approved_lifecycle(
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
    assert decision["candidate_state_summary"] == (
        "selected_complete_official_current_evidence_exists"
    )
    assert decision["decision"] == CONTINUE_DOWNSTREAM
    assert decision["allowed_executor_action"] == "no_recovery_executor_action"


def test_ag94h_c_runner_executes_only_with_recover_missing_source_class_spine() -> None:
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
