"""Pure AG-28 runtime-promotion readiness descriptors.

This module classifies controller actions for the smallest safe future runtime
promotion candidate. It is offline-only: it does not execute retrieval, choose
providers, alter prompts, persist data, call models, or drive runtime control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    get_controller_action_descriptor,
)

CONTROLLER_RUNTIME_PROMOTION_READINESS_SCHEMA_VERSION = (
    "controller_runtime_promotion_readiness_ag28_v1"
)

TERMINAL_STOP_PARITY_SCENARIOS = (
    "terminal_no_query",
    "terminal_budget_exhausted",
)

TERMINAL_STOP_ALLOWED_STATE_FIELDS = (
    "action_history",
    "budget_counters",
    "budget_events",
    "evidence_boundary_events",
    "executor_events",
    "final_answer_posture",
    "metadata",
    "stop_reason",
    "stopped",
)

TERMINAL_STOP_FORBIDDEN_EFFECTS = (
    "admit_ordinary_evidence",
    "change_source_ranking_or_filtering",
    "change_provider_behavior",
    "change_retrieval_continuation",
    "touch_legal_source_diagnostics_beyond_visibility",
    "alter_protected_handoffs",
    "allocate_live_call_budget",
)


@dataclass(frozen=True)
class RuntimePromotionCandidateDescriptor:
    """Offline descriptor for one action's runtime-promotion readiness."""

    action_name: str
    plausible_first_promotion_candidate: bool
    assessment: str
    required_parity_scenarios: tuple[str, ...] = ()
    allowed_state_fields: tuple[str, ...] = ()
    forbidden_effects: tuple[str, ...] = TERMINAL_STOP_FORBIDDEN_EFFECTS
    blockers: tuple[str, ...] = ()
    readiness_notes: tuple[str, ...] = ()
    runtime_behavior_changed: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_RUNTIME_PROMOTION_READINESS_SCHEMA_VERSION,
            "action_name": self.action_name,
            "plausible_first_promotion_candidate": (
                self.plausible_first_promotion_candidate
            ),
            "assessment": self.assessment,
            "required_parity_scenarios": list(self.required_parity_scenarios),
            "allowed_state_fields": list(self.allowed_state_fields),
            "forbidden_effects": list(self.forbidden_effects),
            "blockers": list(self.blockers),
            "readiness_notes": list(self.readiness_notes),
            "runtime_behavior_changed": self.runtime_behavior_changed,
            "metadata": dict(self.metadata),
        }


def _descriptor_metadata(action_name: str) -> dict[str, Any]:
    descriptor = get_controller_action_descriptor(action_name)
    return {
        "current_authority": descriptor.authority.value,
        "side_effect_class": descriptor.side_effect_class.value,
        "handoff_boundary": descriptor.handoff_boundary.value,
        "owner": descriptor.owner,
    }


def assess_runtime_promotion_candidate(
    action_name: str,
) -> RuntimePromotionCandidateDescriptor:
    """Return AG-28 readiness/blocker facts for one AG-25 action name."""

    name = str(action_name)
    metadata = _descriptor_metadata(name)

    if name == STOP_INSUFFICIENT_WITH_CAVEAT:
        return RuntimePromotionCandidateDescriptor(
            action_name=name,
            plausible_first_promotion_candidate=True,
            assessment="readiness_gate_candidate_not_promoted",
            required_parity_scenarios=TERMINAL_STOP_PARITY_SCENARIOS,
            allowed_state_fields=TERMINAL_STOP_ALLOWED_STATE_FIELDS,
            blockers=(
                "runtime_promotion_not_in_scope_ag28",
                "requires_final_pre_promotion_review",
                "retrieval_loop_timing_still_runtime_owned",
            ),
            readiness_notes=(
                "already terminal no-query and budget-exhausted branches have no continuation authority",
                "AG-25 boundary is stop/final-answer-posture-only",
                "AG-26 can replay both terminal branches without known gaps",
                "AG-27 reducer limits state effects to terminal stop posture",
            ),
            metadata=metadata,
        )

    blockers_by_name = {
        RETRIEVE_TARGETED: (
            "requires_retrieval_continuation_authority",
            "would_dispatch_queries",
            "provider_depth_ranking_policy_remains_runtime_owned",
        ),
        STOP_SUFFICIENT: (
            "sufficient_synthesis_branch_is_shadow",
            "protected_final_synthesis_timing_not_promoted",
        ),
        RECOVER_WEAK_CORPUS: (
            "weak_corpus_executor_not_factored_out",
            "ordinary_evidence_admission_path",
            "recovery_timing_and_budget_remain_runtime_owned",
        ),
        RECOVER_MISSING_SOURCE_CLASS: (
            "ordinary_evidence_admission_path",
            "official_legal_quality_gap_remains",
            "provider_depth_domain_ranking_policy_must_not_move_in_ag28",
        ),
        REQUEST_SOCIAL_SIGNAL_CHECK: (
            "future_placeholder_no_provider_integration",
            "side_packet_boundary_not_runtime_wired",
            "cannot_satisfy_ordinary_or_official_evidence",
        ),
    }
    blockers = blockers_by_name.get(
        name,
        ("not_selected_for_ag28_terminal_stop_readiness_gate",),
    )
    return RuntimePromotionCandidateDescriptor(
        action_name=name,
        plausible_first_promotion_candidate=False,
        assessment="blocked_or_not_first_candidate",
        blockers=blockers,
        readiness_notes=(
            "AG-28 only assesses terminal stop parity for already-terminal branches",
        ),
        metadata=metadata,
    )


def runtime_promotion_readiness_matrix() -> dict[str, dict[str, Any]]:
    """Return the compact AG-28 candidate/blocker matrix."""

    actions = (
        STOP_INSUFFICIENT_WITH_CAVEAT,
        RETRIEVE_TARGETED,
        STOP_SUFFICIENT,
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
        REQUEST_SOCIAL_SIGNAL_CHECK,
    )
    return {
        action: assess_runtime_promotion_candidate(action).to_dict()
        for action in actions
    }


__all__ = [
    "CONTROLLER_RUNTIME_PROMOTION_READINESS_SCHEMA_VERSION",
    "TERMINAL_STOP_ALLOWED_STATE_FIELDS",
    "TERMINAL_STOP_FORBIDDEN_EFFECTS",
    "TERMINAL_STOP_PARITY_SCENARIOS",
    "RuntimePromotionCandidateDescriptor",
    "assess_runtime_promotion_candidate",
    "runtime_promotion_readiness_matrix",
]
