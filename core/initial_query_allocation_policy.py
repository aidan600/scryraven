"""Versioned SearchOS policy for ordinary initial-query allocation.

The policy is deliberately provider-, mode-, evidence-, and transport-neutral.
It controls only how many bounded initial candidates may be prepared for each
accepted required AnswerContract component and how many are eligible for the
immediate first DISCOVER wave.  Later SearchJudgment/recovery owners decide
whether a prepared secondary query may run after results are inspected.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

INITIAL_QUERY_ALLOCATION_POLICY_VERSION = "searchos_initial_query_allocation_policy_v1"


@dataclass(frozen=True, slots=True)
class InitialQueryAllocationPolicy:
    """One code-owned tuning surface for component-aware initial planning."""

    policy_version: str = INITIAL_QUERY_ALLOCATION_POLICY_VERSION
    primary_query_target_per_required_component: int = 1
    initial_candidate_ceiling_per_required_component: int = 2
    immediate_dispatch_target_per_required_component: int = 1
    # Provisional tuning default.  It preserves the existing Scout-shaped
    # per-component cardinality while removing any small global recon total.
    recon_candidate_ceiling_per_affected_component: int = 5
    redundancy_rejection_enabled: bool = True
    required_component_floor_enabled: bool = True

    def __post_init__(self) -> None:
        if not str(self.policy_version or "").strip():
            raise ValueError("initial-query allocation policy requires a version")
        numeric_fields = {
            "primary_query_target_per_required_component": (self.primary_query_target_per_required_component),
            "initial_candidate_ceiling_per_required_component": (self.initial_candidate_ceiling_per_required_component),
            "immediate_dispatch_target_per_required_component": (self.immediate_dispatch_target_per_required_component),
            "recon_candidate_ceiling_per_affected_component": (self.recon_candidate_ceiling_per_affected_component),
        }
        for name, value in numeric_fields.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.primary_query_target_per_required_component > self.initial_candidate_ceiling_per_required_component:
            raise ValueError("primary query target cannot exceed candidate ceiling")
        if (
            self.immediate_dispatch_target_per_required_component
            > self.initial_candidate_ceiling_per_required_component
        ):
            raise ValueError("immediate dispatch target cannot exceed candidate ceiling")

    def with_tuning(self, **changes: Any) -> "InitialQueryAllocationPolicy":
        """Return an explicitly composed policy variant for tests/calibration.

        No environment or user-input override path is provided.  Future policy
        calibration changes this owner without changing planner or QueryPlan
        schemas.
        """

        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "primary_query_target_per_required_component": (self.primary_query_target_per_required_component),
            "initial_candidate_ceiling_per_required_component": (self.initial_candidate_ceiling_per_required_component),
            "immediate_dispatch_target_per_required_component": (self.immediate_dispatch_target_per_required_component),
            "recon_candidate_ceiling_per_affected_component": (self.recon_candidate_ceiling_per_affected_component),
            "redundancy_rejection_enabled": self.redundancy_rejection_enabled,
            "required_component_floor_enabled": (self.required_component_floor_enabled),
            "mode_specific_followup_budget_finalized": False,
            "provider_policy_changed": False,
            "post_result_followup_dispatched": False,
        }


DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY = InitialQueryAllocationPolicy()


__all__ = [
    "DEFAULT_INITIAL_QUERY_ALLOCATION_POLICY",
    "INITIAL_QUERY_ALLOCATION_POLICY_VERSION",
    "InitialQueryAllocationPolicy",
]
