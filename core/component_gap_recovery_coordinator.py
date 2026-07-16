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


def component_gap_recovery_policy_for_mode(
    requested_mode: str,
) -> ComponentGapRecoveryPolicy | None:
    """Select a bounded recovery policy without selecting an execution path."""

    if requested_mode != "Balanced":
        return None
    return ComponentGapRecoveryPolicy(
        policy_label="balanced_single_cycle_offline",
        requested_mode=requested_mode,
        allowed_requested_modes=("Balanced",),
        max_cycles=1,
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
    "component_gap_recovery_policy_for_mode",
    "execute_component_gap_recovery",
]
