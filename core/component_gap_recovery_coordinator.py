"""Product-path coordinator for canonical component-gap recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.component_gap_recovery_runtime import (
    ComponentGapRecoveryPolicy,
    ComponentGapRecoveryResult,
    build_component_gap_recovery_handoff,
    execute_authorized_component_gap_recovery,
)
from core.final_authority_citation_survival import (
    attach_selected_authority_evidence_handoff,
)
from core.final_evidence_bundle_builder import (
    FinalEvidenceRuntimeHandoff,
    build_final_evidence_runtime_handoff_from_scope,
)
from core.runtime_prompt_assembly import (
    AuthorPromptAssembly,
    build_author_prompt_from_scope,
)


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryPipelineHandoff:
    """Recovered evidence handoff consumed by the ordinary product path."""

    result: ComponentGapRecoveryResult
    recovered: bool
    all_passages: list[dict[str, Any]] | None = None
    final_evidence_handoff: FinalEvidenceRuntimeHandoff | None = None
    final_top_evidence: list[dict[str, Any]] | None = None
    unique_source_urls: Mapping[str, Any] | None = None
    ordered_sources: list[str] | None = None
    evidence_ledger_projection: Mapping[str, Any] | None = None
    evidence_block: str | None = None
    cached_prefix: str | None = None
    author_evidence: list[dict[str, Any]] | None = None
    author_evidence_block: str | None = None
    author_prompt: str | None = None
    author_notes: str | None = None


def balanced_component_gap_recovery_policy(
    *,
    requested_mode: str,
) -> ComponentGapRecoveryPolicy:
    """Return the bounded Balanced policy for one offline recovery cycle."""

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


def execute_balanced_component_gap_recovery_from_scope(
    *,
    runtime_scope: Mapping[str, Any],
    offline_recovery_adapter: Callable[..., Any] | None,
    seen_urls: set[str] | None,
    filter_top_evidence: Callable[..., Any],
    is_plausible_domain: Callable[..., Any],
    recovered_evidence_visibility: Callable[..., Any] | None,
) -> ComponentGapRecoveryPipelineHandoff:
    """Execute the one-cycle recovery seam and rebuild canonical product handoff."""

    run_kernel = runtime_scope["run_kernel"]
    result = execute_authorized_component_gap_recovery(
        run_kernel=run_kernel,
        policy=balanced_component_gap_recovery_policy(
            requested_mode=str(runtime_scope["strategy"])
        ),
        query_plan_trace=runtime_scope["query_authority"].to_trace_fragment(),
        search_judgment_projection=runtime_scope["search_judgment_projection"],
        evidence_ledger_projection=runtime_scope["evidence_ledger_projection"],
        search_work_projection=runtime_scope.get("search_work_projection"),
        offline_recovery_adapter=offline_recovery_adapter,
        runtime_context={
            "query": runtime_scope["query"],
            "intent": runtime_scope["intent"],
            "complexity": runtime_scope["complexity"],
            "search_depth": runtime_scope["search_depth"],
            "results_per_query": runtime_scope["results_per_query"],
        },
        seen_urls=seen_urls,
    )
    if not result.recovered:
        return ComponentGapRecoveryPipelineHandoff(
            result=result,
            recovered=False,
        )

    recovery_handoff = build_component_gap_recovery_handoff(
        result=result,
        all_passages=runtime_scope["all_passages"],
    )
    refreshed_scope = {
        **dict(runtime_scope),
        "all_passages": list(recovery_handoff.all_passages),
        "evidence_ledger_projection": dict(
            recovery_handoff.evidence_ledger_projection
            or runtime_scope["evidence_ledger_projection"]
        ),
    }
    final_handoff = build_final_evidence_runtime_handoff_from_scope(
        refreshed_scope,
        filter_top_evidence=filter_top_evidence,
        is_plausible_domain=is_plausible_domain,
        recovered_evidence_visibility=recovered_evidence_visibility,
    )
    refreshed_scope.update(
        {
            "final_evidence_bundle": final_handoff.bundle,
            "final_top_evidence": final_handoff.final_top_evidence,
            "unique_source_urls": final_handoff.unique_source_urls,
            "ordered_sources": final_handoff.ordered_sources,
            "evidence_ledger_projection": final_handoff.evidence_ledger_projection,
            "evidence_block": final_handoff.evidence_block,
            "cached_prefix": final_handoff.cached_prefix,
        }
    )
    authority_author_evidence = attach_selected_authority_evidence_handoff(
        final_handoff.bundle,
        precision_count=int(runtime_scope["precision_count"]),
        active_source_class_recovery_lifecycle=runtime_scope[
            "active_source_class_recovery_lifecycle"
        ],
    )
    refreshed_scope.update(
        {
            "author_evidence": authority_author_evidence.author_evidence,
            "author_evidence_block": (
                authority_author_evidence.author_evidence_block
            ),
        }
    )
    author_prompt_assembly: AuthorPromptAssembly = build_author_prompt_from_scope(
        refreshed_scope
    )
    return ComponentGapRecoveryPipelineHandoff(
        result=result,
        recovered=True,
        all_passages=list(recovery_handoff.all_passages),
        final_evidence_handoff=final_handoff,
        final_top_evidence=final_handoff.final_top_evidence,
        unique_source_urls=final_handoff.unique_source_urls,
        ordered_sources=final_handoff.ordered_sources,
        evidence_ledger_projection=final_handoff.evidence_ledger_projection,
        evidence_block=final_handoff.evidence_block,
        cached_prefix=final_handoff.cached_prefix,
        author_evidence=authority_author_evidence.author_evidence,
        author_evidence_block=authority_author_evidence.author_evidence_block,
        author_prompt=author_prompt_assembly.prompt,
        author_notes=author_prompt_assembly.author_notes,
    )


__all__ = [
    "ComponentGapRecoveryPipelineHandoff",
    "balanced_component_gap_recovery_policy",
    "execute_balanced_component_gap_recovery_from_scope",
]
