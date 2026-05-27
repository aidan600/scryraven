from __future__ import annotations

import ast
from pathlib import Path

from core.authority_lifecycle_contract import (
    AuthorityEvidenceFitState,
    AuthorityExecutionState,
    AuthorityFinalPosture,
    AuthorityLifecycle,
    AuthorityLifecycleAction,
    AuthorityLifecycleBlocker,
    AuthorityLifecycleCandidateFit,
    AuthorityLifecycleExecution,
    AuthorityLifecycleProjection,
    AuthoritySatisfactionState,
    CandidateAcquisitionState,
    CandidateFitState,
    CandidateReturnStatus,
    CitationEligibilityState,
    FinalEvidenceState,
    LowerTierContextState,
    RecoveryNeededState,
    TerminalStopState,
    WeakCorpusState,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "core" / "authority_lifecycle_contract.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _codes(lifecycle: AuthorityLifecycle) -> set[str]:
    return {violation.code for violation in lifecycle.validate()}


def _requirement(**overrides: object) -> AuthorityLifecycle:
    values = {
        "requirement_id": "official-current-rate",
        "required_authority": "official_current_rules",
        "claim_type": "current_numeric_threshold",
        "recovery_needed": RecoveryNeededState.REQUIRED,
    }
    values.update(overrides)
    return AuthorityLifecycle(**values)


def _approved_action() -> AuthorityLifecycleAction:
    return AuthorityLifecycleAction.approved_recovery(
        "official-current-rate",
        recovery_queries=("agency official current rate",),
        required_source_classes=("official_current_rules",),
    )


def _executed_recovery(**overrides: object) -> AuthorityLifecycle:
    values = {
        "recovery_query_count": 1,
        "admission_used": True,
        "eligible": True,
        "recovery_action": _approved_action(),
        "execution_state": AuthorityLifecycleExecution.attempted(
            result_count=1,
            recovered_result_count=1,
            accepted_url_count=1,
        ),
        "candidate_acquisition_state": (
            CandidateAcquisitionState.PROVIDER_RESULTS_RETURNED
        ),
        "candidate_fit": AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=1,
            fit_state=CandidateFitState.MATCHED_SELECTED,
            selected_evidence_ids=("agency-source",),
        ),
        "satisfaction_state": AuthoritySatisfactionState.PARTIAL,
        "final_evidence_state": FinalEvidenceState.EXPLAINED_ABSENT,
        "final_evidence_explanation": "recovered source did not survive selection",
        "citation_eligibility_state": CitationEligibilityState.EXPLAINED_INELIGIBLE,
        "final_posture": AuthorityFinalPosture.ACTION_EXECUTED,
    }
    values.update(overrides)
    return _requirement(**values)


def test_ag69a_admitted_eligible_cannot_end_without_execution_or_blocker() -> None:
    lifecycle = _requirement(
        recovery_query_count=1,
        admission_used=True,
        eligible=True,
        recovery_action=_approved_action(),
        execution_state=AuthorityLifecycleExecution(
            state=AuthorityExecutionState.APPROVED_PENDING_EXECUTION
        ),
    )

    assert "admitted_eligible_without_execution_or_blocker" in _codes(lifecycle)

    blocked = _requirement(
        recovery_query_count=1,
        admission_used=True,
        eligible=True,
        recovery_action=_approved_action(),
        execution_state=AuthorityLifecycleExecution(
            state=AuthorityExecutionState.BLOCKED
        ),
        explicit_blockers=(
            AuthorityLifecycleBlocker.controller_hard(
                "official-current-rate",
                "controller_blocked_recovery_execution",
            ),
        ),
        final_posture=AuthorityFinalPosture.BLOCKED,
    )

    assert _codes(blocked) == set()


def test_ag69a_terminal_stop_cannot_preempt_required_recovery() -> None:
    lifecycle = _requirement(
        terminal_stop_state=TerminalStopState.APPROVED,
        final_posture=AuthorityFinalPosture.INSUFFICIENT_PARTIAL,
    )

    assert "terminal_stop_preempts_required_recovery" in _codes(lifecycle)

    blocked = _requirement(
        terminal_stop_state=TerminalStopState.APPROVED,
        explicit_blockers=(
            AuthorityLifecycleBlocker.controller_hard(
                "official-current-rate",
                "terminal_stop_requirement_bound_blocker",
            ),
        ),
        final_posture=AuthorityFinalPosture.BLOCKED,
    )

    assert _codes(blocked) == set()


def test_ag69a_weak_corpus_cannot_own_authority_path_without_blocker() -> None:
    lifecycle = _requirement(
        weak_corpus_state=WeakCorpusState.OWNS_PATH,
        final_posture=AuthorityFinalPosture.INSUFFICIENT_PARTIAL,
    )

    assert "weak_corpus_preempts_authority_recovery" in _codes(lifecycle)

    blocked = _requirement(
        weak_corpus_state=WeakCorpusState.BLOCKED_BY_CONTROLLER,
        explicit_blockers=(
            AuthorityLifecycleBlocker.controller_hard(
                "official-current-rate",
                "authoritative_recovery_blocked_before_weak_corpus",
            ),
        ),
        final_posture=AuthorityFinalPosture.BLOCKED,
    )

    assert _codes(blocked) == set()


def test_ag69a_candidate_returned_cannot_vanish_without_fit_or_rejection() -> None:
    lifecycle = _executed_recovery(
        candidate_fit=AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=10,
            fit_state=CandidateFitState.NOT_EVALUATED,
        )
    )

    assert "candidate_returned_without_fit_or_rejection" in _codes(lifecycle)

    rejected = _executed_recovery(
        candidate_fit=AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=10,
            fit_state=CandidateFitState.REJECTED_WITH_REASON,
            rejection_reasons=("source_class_mismatch",),
        )
    )

    assert _codes(rejected) == set()


def test_ag69a_accepted_url_is_not_authority_evidence_fit() -> None:
    lifecycle = _requirement(
        candidate_fit=AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=1,
            fit_state=CandidateFitState.NOT_EVALUATED,
        ),
        satisfaction_state=AuthoritySatisfactionState.SATISFIED,
        final_evidence_state=FinalEvidenceState.VISIBLE,
        citation_eligibility_state=CitationEligibilityState.ELIGIBLE,
        final_posture=AuthorityFinalPosture.SATISFIED,
    )

    codes = _codes(lifecycle)
    assert "satisfaction_without_authority_evidence_fit" in codes
    assert "candidate_returned_without_fit_or_rejection" in codes

    fitted = _requirement(
        candidate_fit=AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=1,
            fit_state=CandidateFitState.MATCHED_SELECTED,
            selected_evidence_ids=("agency-source",),
        ),
        satisfaction_state=AuthoritySatisfactionState.SATISFIED,
        final_evidence_state=FinalEvidenceState.VISIBLE,
        citation_eligibility_state=CitationEligibilityState.ELIGIBLE,
        final_posture=AuthorityFinalPosture.SATISFIED,
    )

    assert _codes(fitted) == set()


def test_ag69a_trace_projection_fields_are_not_control_inputs() -> None:
    lifecycle = _requirement(
        final_posture=AuthorityFinalPosture.INSUFFICIENT_PARTIAL,
        projections=(
            AuthorityLifecycleProjection(
                name="candidate_visibility_export",
                fields={"candidate_return_status": "candidates_returned"},
                trace_safe=True,
                control_input=True,
            ),
        ),
    )

    assert "projection_used_as_control_input" in _codes(lifecycle)


def test_ag69a_ordinary_acquisition_success_is_not_recovery_success() -> None:
    lifecycle = _requirement(
        candidate_acquisition_state=CandidateAcquisitionState.PROVIDER_RESULTS_RETURNED,
        candidate_fit=AuthorityLifecycleCandidateFit(
            candidate_return_status=CandidateReturnStatus.CANDIDATES_RETURNED,
            accepted_url_count=2,
            fit_state=CandidateFitState.MATCHED_SELECTED,
            selected_evidence_ids=("ordinary-source",),
        ),
    )

    codes = _codes(lifecycle)
    assert "missing_terminal_path" in codes
    assert "approved_action_executed" not in lifecycle.terminal_path_names()


def test_ag69a_lower_tier_context_is_not_official_current_satisfaction() -> None:
    lifecycle = _requirement(
        existing_evidence_fit=AuthorityEvidenceFitState.LOWER_TIER_CONTEXT_ONLY,
        lower_tier_context_state=LowerTierContextState.USED_AS_CONTEXT,
        satisfaction_state=AuthoritySatisfactionState.SATISFIED,
        final_evidence_state=FinalEvidenceState.VISIBLE,
        citation_eligibility_state=CitationEligibilityState.ELIGIBLE,
        final_posture=AuthorityFinalPosture.SATISFIED,
    )

    assert "lower_tier_context_not_authority_satisfaction" in _codes(lifecycle)

    partial = _requirement(
        existing_evidence_fit=AuthorityEvidenceFitState.LOWER_TIER_CONTEXT_ONLY,
        lower_tier_context_state=LowerTierContextState.USED_AS_CONTEXT,
        satisfaction_state=AuthoritySatisfactionState.PARTIAL,
        final_posture=AuthorityFinalPosture.INSUFFICIENT_PARTIAL,
    )

    assert _codes(partial) == set()


def test_ag69a_irs_style_recovered_results_need_visibility_or_explanation() -> None:
    lifecycle = _executed_recovery(
        final_evidence_state=FinalEvidenceState.NOT_VISIBLE,
        final_evidence_explanation=None,
        citation_eligibility_state=CitationEligibilityState.INELIGIBLE,
    )

    assert "recovered_results_not_visible_without_explanation" in _codes(lifecycle)


def test_ag69a_lifecycle_projection_covers_required_contract_fields() -> None:
    projection = _executed_recovery().to_projection()

    assert {
        "requirement_id",
        "required_authority",
        "claim_type",
        "existing_evidence_fit",
        "lower_tier_context_state",
        "recovery_needed",
        "recovery_action",
        "terminal_stop_state",
        "weak_corpus_state",
        "execution_state",
        "candidate_acquisition_state",
        "candidate_return_status",
        "candidate_fit_state",
        "satisfaction_state",
        "final_evidence_state",
        "citation_eligibility_state",
        "final_posture",
        "explicit_blockers",
    } <= set(projection)


def test_ag69a_static_guard_keeps_contract_pure_and_pipeline_closed() -> None:
    tree = ast.parse(_CONTRACT_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imports == {
        "__future__",
        "dataclasses",
        "enum",
        "typing",
    }
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    assert "authority_lifecycle_contract" not in pipeline_source
