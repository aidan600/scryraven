"""Controller-owned authority requirement lifecycle contract.

This module is a pure model/validation surface for authority requirements. It
does not retrieve, rank, route providers, build prompts, cite sources, or
change final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class AuthorityLifecycleContractError(ValueError):
    """Raised when a lifecycle violates the controller-owned contract."""


class AuthorityLifecycleState(str, Enum):
    OPEN = "open"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    ACTION_EXECUTED = "action_executed"
    INSUFFICIENT_PARTIAL = "insufficient_partial"
    INVALID = "invalid"


class AuthorityEvidenceFitState(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    MISSING = "missing"
    LOWER_TIER_CONTEXT_ONLY = "lower_tier_context_only"
    AUTHORITY_SATISFYING = "authority_satisfying"


class LowerTierContextState(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    USED_AS_CONTEXT = "used_as_context"


class RecoveryNeededState(str, Enum):
    NOT_NEEDED = "not_needed"
    REQUIRED = "required"
    OPTIONAL = "optional"


class TerminalStopState(str, Enum):
    NOT_APPROVED = "not_approved"
    APPROVED = "approved"
    BLOCKED_BY_REQUIREMENT = "blocked_by_requirement"


class WeakCorpusState(str, Enum):
    NOT_PRESENT = "not_present"
    CONTEXT_ONLY = "context_only"
    OWNS_PATH = "owns_path"
    BLOCKED_BY_CONTROLLER = "blocked_by_controller"


class AuthorityExecutionState(str, Enum):
    NOT_REQUESTED = "not_requested"
    APPROVED_PENDING_EXECUTION = "approved_pending_execution"
    ATTEMPTED = "attempted"
    BLOCKED = "blocked"


class CandidateAcquisitionState(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    ATTEMPTED = "attempted"
    PROVIDER_RESULTS_RETURNED = "provider_results_returned"
    NO_RESULTS = "no_results"


class CandidateReturnStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    NO_CANDIDATES = "no_candidates"
    CANDIDATES_RETURNED = "candidates_returned"


class CandidateFitState(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    MATCHED_SELECTED = "matched_selected"
    MATCHED_NOT_SELECTED = "matched_not_selected"
    REJECTED_WITH_REASON = "rejected_with_reason"
    NO_MATCHING_SOURCE_FIT = "no_matching_source_fit"


class AuthoritySatisfactionState(str, Enum):
    UNSATISFIED = "unsatisfied"
    PARTIAL = "partial"
    SATISFIED = "satisfied"


class FinalEvidenceState(str, Enum):
    NOT_VISIBLE = "not_visible"
    VISIBLE = "visible"
    EXPLAINED_ABSENT = "explained_absent"


class CitationEligibilityState(str, Enum):
    INELIGIBLE = "ineligible"
    ELIGIBLE = "eligible"
    EXPLAINED_INELIGIBLE = "explained_ineligible"


class AuthorityFinalPosture(str, Enum):
    OPEN = "open"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    ACTION_EXECUTED = "action_executed"
    INSUFFICIENT_PARTIAL = "insufficient_partial"


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleBlocker:
    requirement_id: str
    kind: str
    reason: str
    owner: str = "controller"
    hard: bool = True
    recovery_may_be_retried: bool = False
    final_posture_must_be_insufficient_partial: bool = True

    @classmethod
    def controller_hard(
        cls,
        requirement_id: str,
        kind: str,
        reason: str | None = None,
        *,
        recovery_may_be_retried: bool = False,
        final_posture_must_be_insufficient_partial: bool = True,
    ) -> "AuthorityLifecycleBlocker":
        return cls(
            requirement_id=requirement_id,
            kind=kind,
            reason=reason or kind,
            owner="controller",
            hard=True,
            recovery_may_be_retried=recovery_may_be_retried,
            final_posture_must_be_insufficient_partial=(
                final_posture_must_be_insufficient_partial
            ),
        )

    @classmethod
    def controller_lifecycle_execution(
        cls,
        requirement_id: str,
        blocker_reason: str,
        *,
        recovery_may_be_retried: bool = False,
        final_posture_must_be_insufficient_partial: bool = True,
    ) -> "AuthorityLifecycleBlocker":
        return cls(
            requirement_id=requirement_id,
            kind="recovery_execution_blocked",
            reason=blocker_reason,
            owner="controller/lifecycle",
            hard=True,
            recovery_may_be_retried=recovery_may_be_retried,
            final_posture_must_be_insufficient_partial=(
                final_posture_must_be_insufficient_partial
            ),
        )

    def is_controller_hard_for(self, requirement_id: str) -> bool:
        return (
            self.owner in {"controller", "controller/lifecycle"}
            and self.hard
            and self.requirement_id == requirement_id
        )

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "kind": self.kind,
            "reason": self.reason,
            "owner": self.owner,
            "hard": self.hard,
            "blocker_reason": self.reason,
            "blocker_owner": self.owner,
            "recovery_may_be_retried": self.recovery_may_be_retried,
            "final_posture_must_be_insufficient_partial": (
                self.final_posture_must_be_insufficient_partial
            ),
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleAction:
    requirement_id: str
    action_type: str
    approved: bool
    owner: str = "controller"
    recovery_queries: tuple[str, ...] = ()
    required_source_classes: tuple[str, ...] = ()
    reason: str | None = None

    @classmethod
    def approved_recovery(
        cls,
        requirement_id: str,
        *,
        recovery_queries: Sequence[str] = (),
        required_source_classes: Sequence[str] = (),
        reason: str | None = None,
    ) -> "AuthorityLifecycleAction":
        return cls(
            requirement_id=requirement_id,
            action_type="recover_missing_source_class",
            approved=True,
            recovery_queries=tuple(recovery_queries),
            required_source_classes=tuple(required_source_classes),
            reason=reason,
        )

    def controller_approved_for(self, requirement_id: str) -> bool:
        return (
            self.owner == "controller"
            and self.approved
            and self.requirement_id == requirement_id
        )

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "action_type": self.action_type,
            "approved": self.approved,
            "owner": self.owner,
            "recovery_query_count": len(self.recovery_queries),
            "required_source_classes": list(self.required_source_classes),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleExecution:
    state: AuthorityExecutionState = AuthorityExecutionState.NOT_REQUESTED
    result_count: int = 0
    recovered_result_count: int = 0
    accepted_url_count: int = 0
    explanation: str | None = None

    @classmethod
    def attempted(
        cls,
        *,
        result_count: int = 0,
        recovered_result_count: int = 0,
        accepted_url_count: int = 0,
        explanation: str | None = None,
    ) -> "AuthorityLifecycleExecution":
        return cls(
            state=AuthorityExecutionState.ATTEMPTED,
            result_count=max(0, int(result_count)),
            recovered_result_count=max(0, int(recovered_result_count)),
            accepted_url_count=max(0, int(accepted_url_count)),
            explanation=explanation,
        )

    @classmethod
    def blocked(
        cls,
        *,
        explanation: str,
    ) -> "AuthorityLifecycleExecution":
        return cls(
            state=AuthorityExecutionState.BLOCKED,
            explanation=explanation,
        )

    @property
    def attempted_execution(self) -> bool:
        return self.state is AuthorityExecutionState.ATTEMPTED

    def to_projection(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "result_count": self.result_count,
            "recovered_result_count": self.recovered_result_count,
            "accepted_url_count": self.accepted_url_count,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleCandidateFit:
    candidate_return_status: CandidateReturnStatus = (
        CandidateReturnStatus.NOT_ATTEMPTED
    )
    accepted_url_count: int = 0
    fit_state: CandidateFitState = CandidateFitState.NOT_EVALUATED
    rejection_reasons: tuple[str, ...] = ()
    structured_rejections: tuple["AuthorityLifecycleCandidateRejection", ...] = ()
    selected_evidence_ids: tuple[str, ...] = ()
    selected_evidence_records: tuple[Mapping[str, Any], ...] = ()

    def has_fit_or_rejection(self) -> bool:
        if self.fit_state in {
            CandidateFitState.MATCHED_SELECTED,
            CandidateFitState.MATCHED_NOT_SELECTED,
            CandidateFitState.NO_MATCHING_SOURCE_FIT,
        }:
            return True
        return (
            self.fit_state is CandidateFitState.REJECTED_WITH_REASON
            and (bool(self.structured_rejections) or bool(self.rejection_reasons))
        )

    def selected_authority_evidence(self) -> bool:
        return (
            self.fit_state is CandidateFitState.MATCHED_SELECTED
            and bool(self.selected_evidence_ids)
        )

    def to_projection(self) -> dict[str, Any]:
        return {
            "candidate_return_status": self.candidate_return_status.value,
            "accepted_url_count": self.accepted_url_count,
            "fit_state": self.fit_state.value,
            "rejection_reasons": [
                rejection.rejection_reason
                for rejection in self.structured_rejections
            ]
            or list(self.rejection_reasons),
            "structured_rejections": [
                rejection.to_projection()
                for rejection in self.structured_rejections
            ],
            "selected_evidence_ids": list(self.selected_evidence_ids),
            "selected_authority_evidence": [
                dict(record) for record in self.selected_evidence_records
            ],
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleCandidateRejection:
    requirement_id: str
    candidate_id: str | None
    url: str | None
    required_authority: str
    observed_source_class: str | None
    rejection_reason: str
    rejection_owner: str = "controller/lifecycle"
    lower_tier_context_allowed: bool = False
    final_evidence_must_be_explained_absent: bool = True

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "candidate_id": self.candidate_id,
            "url": self.url,
            "required_authority": self.required_authority,
            "observed_source_class": self.observed_source_class,
            "rejection_reason": self.rejection_reason,
            "rejection_owner": self.rejection_owner,
            "lower_tier_context_allowed": self.lower_tier_context_allowed,
            "final_evidence_must_be_explained_absent": (
                self.final_evidence_must_be_explained_absent
            ),
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleProjection:
    name: str
    fields: Mapping[str, Any] = field(default_factory=dict)
    trace_safe: bool = True
    control_input: bool = False

    def to_projection(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": dict(self.fields),
            "trace_safe": self.trace_safe,
            "control_input": self.control_input,
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleStep:
    name: str
    state: AuthorityLifecycleState
    reason: str | None = None

    def to_projection(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleViolation:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AuthorityLifecycle:
    requirement_id: str
    required_authority: str
    claim_type: str
    existing_evidence_fit: AuthorityEvidenceFitState = (
        AuthorityEvidenceFitState.NOT_EVALUATED
    )
    lower_tier_context_state: LowerTierContextState = LowerTierContextState.ABSENT
    recovery_needed: RecoveryNeededState = RecoveryNeededState.NOT_NEEDED
    recovery_query_count: int = 0
    admission_used: bool = False
    eligible: bool = False
    recovery_action: AuthorityLifecycleAction | None = None
    terminal_stop_state: TerminalStopState = TerminalStopState.NOT_APPROVED
    weak_corpus_state: WeakCorpusState = WeakCorpusState.NOT_PRESENT
    execution_state: AuthorityLifecycleExecution = field(
        default_factory=AuthorityLifecycleExecution
    )
    candidate_acquisition_state: CandidateAcquisitionState = (
        CandidateAcquisitionState.NOT_ATTEMPTED
    )
    candidate_fit: AuthorityLifecycleCandidateFit = field(
        default_factory=AuthorityLifecycleCandidateFit
    )
    satisfaction_state: AuthoritySatisfactionState = (
        AuthoritySatisfactionState.UNSATISFIED
    )
    final_evidence_state: FinalEvidenceState = FinalEvidenceState.NOT_VISIBLE
    final_evidence_explanation: str | None = None
    citation_eligibility_state: CitationEligibilityState = (
        CitationEligibilityState.INELIGIBLE
    )
    final_posture: AuthorityFinalPosture = AuthorityFinalPosture.OPEN
    explicit_blockers: tuple[AuthorityLifecycleBlocker, ...] = ()
    projections: tuple[AuthorityLifecycleProjection, ...] = ()
    steps: tuple[AuthorityLifecycleStep, ...] = ()
    required: bool = True

    @property
    def candidate_return_status(self) -> CandidateReturnStatus:
        return self.candidate_fit.candidate_return_status

    @property
    def accepted_url_count(self) -> int:
        return max(
            int(self.candidate_fit.accepted_url_count or 0),
            int(self.execution_state.accepted_url_count or 0),
        )

    @property
    def is_satisfied_by_existing_evidence(self) -> bool:
        return (
            self.satisfaction_state is AuthoritySatisfactionState.SATISFIED
            and self.existing_evidence_fit
            is AuthorityEvidenceFitState.AUTHORITY_SATISFYING
        )

    @property
    def has_controller_hard_blocker(self) -> bool:
        return any(
            blocker.is_controller_hard_for(self.requirement_id)
            for blocker in self.explicit_blockers
        )

    @property
    def has_controller_approved_action(self) -> bool:
        return bool(
            self.recovery_action
            and self.recovery_action.controller_approved_for(self.requirement_id)
        )

    @property
    def has_executed_controller_action(self) -> bool:
        return (
            self.has_controller_approved_action
            and self.execution_state.attempted_execution
        )

    @property
    def has_controller_insufficient_posture(self) -> bool:
        return self.final_posture is AuthorityFinalPosture.INSUFFICIENT_PARTIAL

    def terminal_path_names(self) -> tuple[str, ...]:
        paths: list[str] = []
        if self.is_satisfied_by_existing_evidence:
            paths.append("satisfied_by_existing_evidence")
        if self.has_controller_hard_blocker:
            paths.append("controller_hard_blocker")
        if self.has_executed_controller_action:
            paths.append("approved_action_executed")
        if self.has_controller_insufficient_posture and not self.has_controller_hard_blocker:
            paths.append("controller_insufficient_partial_posture")
        return tuple(paths)

    def validate(self) -> tuple[AuthorityLifecycleViolation, ...]:
        violations: list[AuthorityLifecycleViolation] = []
        paths = self.terminal_path_names()

        if self.required and self.satisfaction_state is not AuthoritySatisfactionState.SATISFIED:
            if len(paths) == 0:
                violations.append(
                    AuthorityLifecycleViolation(
                        "missing_terminal_path",
                        "unmet required authority has no controller terminal path",
                    )
                )
            elif len(paths) > 1:
                violations.append(
                    AuthorityLifecycleViolation(
                        "multiple_terminal_paths",
                        "unmet required authority has multiple terminal paths",
                    )
                )

        if self.recovery_query_count > 0 and not (
            self.recovery_action or self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "queries_without_action_or_blocker",
                    "recovery queries exist without action or hard blocker",
                )
            )

        if (
            self.has_controller_approved_action
            and self.execution_state.state
            is AuthorityExecutionState.APPROVED_PENDING_EXECUTION
            and not self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "approved_action_without_execution_or_blocker",
                    "approved action ended without execution or blocker",
                )
            )

        if (
            self.admission_used
            and self.eligible
            and self.execution_state.state is not AuthorityExecutionState.ATTEMPTED
            and not self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "admitted_eligible_without_execution_or_blocker",
                    "admitted eligible recovery did not execute and has no blocker",
                )
            )

        if (
            self.recovery_action is not None
            and self.recovery_action.approved
            and not (self.admission_used and self.eligible)
            and self.execution_state.state is not AuthorityExecutionState.ATTEMPTED
            and not self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "admitted_eligible_without_execution_or_blocker",
                    "admitted eligible recovery did not execute and has no blocker",
                )
            )

        if (
            self.terminal_stop_state is TerminalStopState.APPROVED
            and self.recovery_needed is RecoveryNeededState.REQUIRED
            and not self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "terminal_stop_preempts_required_recovery",
                    "terminal stop approved while required recovery lacks blocker",
                )
            )

        if (
            self.weak_corpus_state is WeakCorpusState.OWNS_PATH
            and self.recovery_needed is RecoveryNeededState.REQUIRED
            and not self.has_controller_hard_blocker
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "weak_corpus_preempts_authority_recovery",
                    "weak corpus owns path without requirement-bound blocker",
                )
            )

        candidate_returned = (
            self.candidate_return_status is CandidateReturnStatus.CANDIDATES_RETURNED
            or self.accepted_url_count > 0
        )
        if candidate_returned and not self.candidate_fit.has_fit_or_rejection():
            violations.append(
                AuthorityLifecycleViolation(
                    "candidate_returned_without_fit_or_rejection",
                    "returned candidate lacks source fit or rejection reason",
                )
            )

        if (
            self.execution_state.recovered_result_count > 0
            and self.final_evidence_state is FinalEvidenceState.NOT_VISIBLE
            and not self.final_evidence_explanation
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "recovered_results_not_visible_without_explanation",
                    "recovered results lack final evidence visibility/explanation",
                )
            )

        if any(projection.control_input for projection in self.projections):
            violations.append(
                AuthorityLifecycleViolation(
                    "projection_used_as_control_input",
                    "trace/projection fields cannot be authority control inputs",
                )
            )

        if (
            self.satisfaction_state is AuthoritySatisfactionState.SATISFIED
            and not (
                self.is_satisfied_by_existing_evidence
                or self.candidate_fit.selected_authority_evidence()
            )
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "satisfaction_without_authority_evidence_fit",
                    "accepted URLs or context alone cannot satisfy authority",
                )
            )

        if (
            self.lower_tier_context_state is not LowerTierContextState.ABSENT
            and self.existing_evidence_fit
            is AuthorityEvidenceFitState.LOWER_TIER_CONTEXT_ONLY
            and self.satisfaction_state is AuthoritySatisfactionState.SATISFIED
        ):
            violations.append(
                AuthorityLifecycleViolation(
                    "lower_tier_context_not_authority_satisfaction",
                    "lower-tier context cannot satisfy required authority",
                )
            )

        return tuple(violations)

    def assert_valid(self) -> None:
        violations = self.validate()
        if violations:
            codes = ", ".join(violation.code for violation in violations)
            raise AuthorityLifecycleContractError(codes)

    def to_projection(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "required_authority": self.required_authority,
            "claim_type": self.claim_type,
            "existing_evidence_fit": self.existing_evidence_fit.value,
            "lower_tier_context_state": self.lower_tier_context_state.value,
            "recovery_needed": self.recovery_needed.value,
            "recovery_query_count": self.recovery_query_count,
            "admission_used": self.admission_used,
            "eligible": self.eligible,
            "recovery_action": (
                self.recovery_action.to_projection()
                if self.recovery_action is not None
                else None
            ),
            "terminal_stop_state": self.terminal_stop_state.value,
            "weak_corpus_state": self.weak_corpus_state.value,
            "execution_state": self.execution_state.to_projection(),
            "candidate_acquisition_considered": (
                self.candidate_acquisition_state
                is not CandidateAcquisitionState.NOT_ATTEMPTED
            ),
            "candidate_acquisition_state": self.candidate_acquisition_state.value,
            "acquisition_attempted": (
                self.candidate_acquisition_state
                is not CandidateAcquisitionState.NOT_ATTEMPTED
            ),
            "candidate_return_status": self.candidate_return_status.value,
            "accepted_url_count": self.accepted_url_count,
            "candidate_fit": self.candidate_fit.to_projection(),
            "candidate_fit_state": self.candidate_fit.fit_state.value,
            "satisfaction_state": self.satisfaction_state.value,
            "final_evidence_state": self.final_evidence_state.value,
            "final_evidence_explanation": self.final_evidence_explanation,
            "citation_eligibility_state": self.citation_eligibility_state.value,
            "final_posture": self.final_posture.value,
            "explicit_blockers": [
                blocker.to_projection() for blocker in self.explicit_blockers
            ],
            "terminal_paths": list(self.terminal_path_names()),
            "projections": [
                projection.to_projection() for projection in self.projections
            ],
            "steps": [step.to_projection() for step in self.steps],
            "required": self.required,
        }


__all__ = [
    "AuthorityEvidenceFitState",
    "AuthorityExecutionState",
    "AuthorityFinalPosture",
    "AuthorityLifecycle",
    "AuthorityLifecycleAction",
    "AuthorityLifecycleBlocker",
    "AuthorityLifecycleCandidateFit",
    "AuthorityLifecycleCandidateRejection",
    "AuthorityLifecycleContractError",
    "AuthorityLifecycleProjection",
    "AuthorityLifecycleState",
    "AuthorityLifecycleStep",
    "AuthorityLifecycleViolation",
    "AuthoritySatisfactionState",
    "CandidateAcquisitionState",
    "CandidateFitState",
    "CandidateReturnStatus",
    "CitationEligibilityState",
    "FinalEvidenceState",
    "LowerTierContextState",
    "RecoveryNeededState",
    "TerminalStopState",
    "WeakCorpusState",
]
