"""Runtime fact adapter for conflict-resolution lifecycle traces."""

from __future__ import annotations

from typing import Any

from core.conflict_resolution_controller import (
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
    build_conflict_resolution_controller_input,
    build_conflict_resolution_lifecycle,
)


def build_conflict_resolution_lifecycle_from_runtime_answer_contract(
    *,
    answer_contract_result: Any,
    current_search_depth: str | None,
    iteration_budget_available: bool,
    active_conflict_resolution_lifecycle: dict[str, Any],
    provider_policy_reusable: bool = True,
    provider_swap_required: bool = False,
    search_depth_reusable: bool = True,
    search_depth_escalation_required: bool = False,
    lifecycle_phase: str = "pre_analyst",
) -> tuple[dict[str, Any], ConflictResolutionDecision]:
    state = getattr(answer_contract_result, "state", None)
    evidence_state = getattr(state, "evidence_state_summary", None)
    if evidence_state is None:
        return dict(active_conflict_resolution_lifecycle), ConflictResolutionDecision(
            decision=ConflictResolutionControllerDecision.BLOCKED_WITH_REASON,
            reason="conflict_state_unavailable",
            blockers=("conflict_state_unavailable",),
            conflict_notes=(),
            queries=(),
            attempt_count=0,
        )

    state_attempts = getattr(state, "recovery_attempts", {})
    prior_attempt_count = max(
        int(state_attempts.get("resolve_conflict", 0) or 0),
        int(
            active_conflict_resolution_lifecycle.get(
                "active_conflict_resolution_attempt_count"
            )
            or 0
        ),
    )
    snapshot = build_conflict_resolution_controller_input(
        conflicts_present=bool(evidence_state.conflicts_present),
        conflict_notes=evidence_state.conflict_notes,
        resolving_queries=evidence_state.resolving_queries,
        ordinary_next_queries=evidence_state.next_queries,
        current_search_depth=current_search_depth,
        iteration_budget_available=bool(iteration_budget_available),
        prior_attempt_count=prior_attempt_count,
        provider_policy_reusable=provider_policy_reusable,
        provider_swap_required=provider_swap_required,
        search_depth_reusable=search_depth_reusable,
        search_depth_escalation_required=search_depth_escalation_required,
        lifecycle_phase=lifecycle_phase,
        metadata={
            "source": "runtime_answer_contract_evidence_state",
            "ordinary_next_query_count": len(evidence_state.next_queries),
        },
    )
    lifecycle = build_conflict_resolution_lifecycle(snapshot)
    return lifecycle.to_trace_fields(), lifecycle.decision
