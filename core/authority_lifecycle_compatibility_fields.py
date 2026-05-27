"""Compatibility-field audit for AuthorityLifecycle projections.

This module is a pure documentation surface for legacy trace/export fields
that remain after AuthorityLifecycle became the controller-owned source of
truth. It does not participate in runtime dispatch or final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthorityLifecycleCompatibilityField:
    field_name: str
    replacement: str
    classification: str
    named_consumers: tuple[str, ...]
    deletion_or_promotion_criterion: str
    control_input: bool = False

    def to_projection(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "replacement": self.replacement,
            "classification": self.classification,
            "named_consumers": list(self.named_consumers),
            "deletion_or_promotion_criterion": self.deletion_or_promotion_criterion,
            "control_input": self.control_input,
        }


AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS = (
    AuthorityLifecycleCompatibilityField(
        field_name="terminal_stop_approved",
        replacement="authority_lifecycle.terminal_stop_state and "
        "authority_lifecycle_terminal_stop_may_preempt",
        classification="runtime fact input before lifecycle build; diagnostic after",
        named_consumers=(
            "authoritative_source_action_orchestrator_adapter",
            "authority_lifecycle_runtime_arbitration",
            "controller_loop_spine terminal checkpoint trace",
            "offline lifecycle regression tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after checkpoint stop decisions emit requirement-bound "
            "AuthorityLifecycle terminal state/blockers directly."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="weak_corpus_recovery_owns_path",
        replacement="authority_lifecycle.weak_corpus_state and "
        "authority_lifecycle_weak_corpus_may_own_path",
        classification="legacy blocker/projection for weak-corpus diagnostics",
        named_consumers=(
            "authority_lifecycle_runtime_arbitration blocker filter",
            "targeted_retrieval_controller legacy ownership diagnostics",
            "offline weak-corpus/source-class regression tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after weak-corpus recovery emits lifecycle ownership state "
            "instead of blocker strings."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="blocked_by_weak_corpus_recovery",
        replacement="authority_lifecycle.weak_corpus_state and "
        "authority_lifecycle_weak_corpus_may_own_path",
        classification="legacy blocker/projection",
        named_consumers=(
            "authority_lifecycle_runtime_arbitration blocker filter",
            "source_class_recovery_controller compatibility tests",
            "diagnostic exports that list historical blockers",
        ),
        deletion_or_promotion_criterion=(
            "Retire after all recovery blockers are emitted as lifecycle "
            "blockers with owner and requirement_id."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="active_source_class_recovery_eligible",
        replacement="authority_lifecycle.recovery_action.approved and "
        "authority_lifecycle_required_recovery_allowed",
        classification="compatibility handoff/projection",
        named_consumers=(
            "source_class_recovery_executor action lookup",
            "official_canonical_recovery_visibility_export",
            "authoritative_source_action trace summary",
            "offline source-class regression tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after executor lookup consumes the lifecycle recovery action "
            "envelope directly."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="active_source_class_recovery_used",
        replacement="authority_lifecycle.execution_state.state == attempted",
        classification="compatibility execution projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "planned_observed_diagnostics",
            "task ledger diagnostics",
            "offline source-class regression tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after exports and diagnostic ledgers read lifecycle execution "
            "state directly."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="active_source_class_recovery_execution_attempted",
        replacement="authority_lifecycle.execution_state.state == attempted",
        classification="compatibility execution projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "source_class_recovery_lifecycle trace compatibility",
            "offline AG-68/AG-69 execution tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after all execution exports consume lifecycle execution state."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="accepted_url_count",
        replacement="authority_lifecycle.execution_state.accepted_url_count and "
        "authority_lifecycle.candidate_fit.accepted_url_count",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "source_class_recovery_diagnostics_l1",
            "provider diagnostics tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after accepted/readable candidate diagnostics consume "
            "lifecycle candidate-fit projection."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="recovered_result_count",
        replacement="authority_lifecycle.execution_state.recovered_result_count",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "source_class_recovery_diagnostics_l1",
            "offline AG-50 dispatch/export tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after recovery result diagnostics consume lifecycle execution "
            "state directly."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="candidate_return_status",
        replacement="authority_lifecycle.candidate_fit.candidate_return_status",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "offline AG-50 dispatch/export tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after candidate-return exports read lifecycle candidate-fit "
            "state directly."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="recovered_visibility_source_fit_status",
        replacement="authority_lifecycle.candidate_fit.fit_state",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "AG-52 recovered evidence acceptance tests",
            "AG-69D/AG-69E lifecycle visibility tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after source-fit exports and report diagnostics read "
            "lifecycle candidate-fit state."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="recovered_visibility_source_fit_candidate_count",
        replacement="authority_lifecycle.candidate_fit selected/rejection records",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "AG-52 recovered evidence acceptance tests",
            "AG-69D/AG-69E lifecycle visibility tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after consumers use selected_authority_evidence and "
            "structured_rejections counts."
        ),
    ),
    AuthorityLifecycleCompatibilityField(
        field_name="recovered_visibility_source_fit_selected_count",
        replacement="authority_lifecycle.candidate_fit.selected_authority_evidence",
        classification="visibility/export projection",
        named_consumers=(
            "official_canonical_recovery_visibility_export",
            "AG-52 recovered evidence acceptance tests",
            "AG-69D/AG-69E lifecycle visibility tests",
        ),
        deletion_or_promotion_criterion=(
            "Retire after consumers count selected_authority_evidence directly."
        ),
    ),
)


def authority_lifecycle_compatibility_field_projection() -> tuple[dict[str, object], ...]:
    return tuple(
        field.to_projection() for field in AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS
    )


__all__ = [
    "AUTHORITY_LIFECYCLE_COMPATIBILITY_FIELDS",
    "AuthorityLifecycleCompatibilityField",
    "authority_lifecycle_compatibility_field_projection",
]
