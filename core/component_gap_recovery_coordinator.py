"""Product-path coordinator for canonical component-gap recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.component_gap_recovery_runtime import (
    ComponentGapRecoveryPolicy,
    ComponentGapRecoveryResult,
    build_component_gap_recovery_handoff,
    execute_authorized_component_gap_recovery,
)


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryPipelineInputs:
    """Explicit whitelisted inputs for the bounded recovery coordinator."""

    run_kernel: Any
    query_plan_trace: Mapping[str, Any]
    search_judgment_projection: Mapping[str, Any]
    evidence_ledger_projection: Mapping[str, Any]
    search_work_projection: Mapping[str, Any] | None
    query: str
    intent: str
    complexity: str
    search_depth: str
    results_per_query: int
    all_passages: Sequence[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryPipelineHandoff:
    """Bounded recovered material returned to the ordinary product path."""

    result: ComponentGapRecoveryResult
    recovered: bool
    all_passages: tuple[dict[str, Any], ...] = ()
    evidence_ledger_projection: Mapping[str, Any] | None = None
    semantic_state_facts: Mapping[str, Any] | None = None


_RECOVERY_MODE_COMPATIBILITY_VALUES: Mapping[str, Mapping[str, Any]] = {
    "Balanced": {
        "policy_label": "balanced_single_cycle_offline",
        "recovery_eligible": True,
        "closure_reason": None,
        "max_cycles": 1,
    },
    "Fast": {
        "policy_label": "fast_recovery_closed_compatibility",
        "recovery_eligible": False,
        "closure_reason": "recovery_closed_this_phase",
        "max_cycles": 0,
    },
    "Deep": {
        "policy_label": "deep_recovery_closed_compatibility",
        "recovery_eligible": False,
        "closure_reason": (
            "recovery_closed_pending_explicit_mode_policy_decision"
        ),
        "max_cycles": 0,
    },
}


def resolve_component_gap_recovery_mode_policy(
    requested_mode: str,
) -> ComponentGapRecoveryPolicy:
    """Resolve the recovery slice of one shared temporary mode-policy shape."""

    compatibility_values = _RECOVERY_MODE_COMPATIBILITY_VALUES.get(requested_mode)
    mode_supported = compatibility_values is not None
    values = dict(
        compatibility_values
        or {
            "policy_label": "unsupported_mode_recovery_closed",
            "recovery_eligible": False,
            "closure_reason": "unsupported_mode_recovery_closed",
            "max_cycles": 0,
        }
    )
    return ComponentGapRecoveryPolicy(
        policy_label=str(values["policy_label"]),
        requested_mode=requested_mode,
        allowed_requested_modes=(requested_mode,) if mode_supported else (),
        mode_supported=mode_supported,
        recovery_eligible=bool(values["recovery_eligible"]),
        closure_reason=(
            str(values["closure_reason"])
            if values.get("closure_reason") is not None
            else None
        ),
        temporary_compatibility_values=True,
        max_cycles=int(values["max_cycles"]),
        offline_only=True,
        existing_candidate_query_only=True,
        model_generated_query_text_allowed=False,
        provider_live_calls_allowed=False,
        accepted_amendments_allowed=False,
        deep_reconciliation_allowed=False,
    )


def execute_component_gap_recovery(
    *,
    inputs: ComponentGapRecoveryPipelineInputs,
    policy: ComponentGapRecoveryPolicy,
    offline_recovery_adapter: Callable[..., Any] | None,
    seen_urls: set[str] | None,
) -> ComponentGapRecoveryPipelineHandoff:
    """Execute mode-neutral recovery and return only canonically reduced material."""

    result = execute_authorized_component_gap_recovery(
        run_kernel=inputs.run_kernel,
        policy=policy,
        query_plan_trace=inputs.query_plan_trace,
        search_judgment_projection=inputs.search_judgment_projection,
        evidence_ledger_projection=inputs.evidence_ledger_projection,
        search_work_projection=inputs.search_work_projection,
        offline_recovery_adapter=offline_recovery_adapter,
        runtime_context={
            "query": inputs.query,
            "intent": inputs.intent,
            "complexity": inputs.complexity,
            "search_depth": inputs.search_depth,
            "results_per_query": inputs.results_per_query,
        },
        seen_urls=seen_urls,
    )
    if not result.recovered:
        return ComponentGapRecoveryPipelineHandoff(
            result=result,
            recovered=False,
            evidence_ledger_projection=result.evidence_ledger_projection,
            semantic_state_facts=result.semantic_state_facts,
        )

    recovery_handoff = build_component_gap_recovery_handoff(
        result=result,
        all_passages=inputs.all_passages,
    )
    return ComponentGapRecoveryPipelineHandoff(
        result=result,
        recovered=True,
        all_passages=recovery_handoff.all_passages,
        evidence_ledger_projection=recovery_handoff.evidence_ledger_projection,
        semantic_state_facts=result.semantic_state_facts,
    )


__all__ = [
    "ComponentGapRecoveryPipelineHandoff",
    "ComponentGapRecoveryPipelineInputs",
    "execute_component_gap_recovery",
    "resolve_component_gap_recovery_mode_policy",
]
