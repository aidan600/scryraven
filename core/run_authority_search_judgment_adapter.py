"""Runtime input adapter for RunAuthority search judgment.

This module assembles compact, already-sanitized runtime facts into the
``RunSearchJudgmentInput`` consumed by the bounded judgment executor. It does
not authorize actions, execute providers/search, reduce state, or decide policy.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.run_authority_search_judgment import RunSearchJudgmentInput
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
    evaluate_semantic_sufficiency_overlay,
)


def build_search_judgment_input_from_runtime(
    *,
    contract_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    query_authority_trace: Mapping[str, Any],
    core_topic: str,
    primary_entity: str,
    result_count: int,
    iterations_run: int,
    source_tier_counts: Mapping[str, Any],
    source_domain_counts: Mapping[str, Any],
    top_source_domains: Any,
    provider_diagnostic_count: int,
    source_class_recovery_recommendation: Mapping[str, Any],
    source_class_observability: Mapping[str, Any],
    retrieval_stop_shadow_telemetry: Mapping[str, Any],
    retrieval_stop_active_telemetry: Mapping[str, Any],
    answer_contract_projection: Mapping[str, Any],
    max_iterations: int,
    recovery_attempt_count: int,
    initial_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_history: Any = (),
    contract_amendment_admission_history: Any = (),
) -> RunSearchJudgmentInput:
    """Build the AG-92B search-judgment input from runtime facts."""

    source_class_recovery = {
        **dict(source_class_recovery_recommendation),
        **dict(source_class_observability),
    }
    semantic_state_facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=initial_answer_contract or {},
        component_coverage_history=component_coverage_history or (),
        contract_amendment_admission_history=contract_amendment_admission_history
        or (),
        evidence_ledger_projection=evidence_ledger_projection,
    )
    semantic_overlay = evaluate_semantic_sufficiency_overlay(semantic_state_facts)
    return RunSearchJudgmentInput(
        contract_projection=contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        query_facts={
            **dict(query_authority_trace),
            "query_role": "post_retrieval_recovery",
            "core_topic": core_topic,
            "primary_entity": primary_entity,
        },
        retrieval_observations={
            "result_count": result_count,
            "iterations_run": iterations_run,
            "source_tier_counts": dict(source_tier_counts),
            "source_domain_counts": dict(source_domain_counts),
            "top_source_domains": top_source_domains,
            "provider_diagnostic_count": provider_diagnostic_count,
        },
        helper_proposals={
            "source_class_recovery": source_class_recovery,
            "retrieval_stop": {
                "shadow": retrieval_stop_shadow_telemetry,
                "active": retrieval_stop_active_telemetry,
            },
            "answer_contract": answer_contract_projection,
            "semantic_state_facts": semantic_state_facts,
            "semantic_missing_assessments": [
                dict(item) for item in semantic_overlay.missing_assessments
            ],
        },
        budget={
            "iteration": iterations_run,
            "max_iterations": max_iterations,
            "remaining_budget": max(0, max_iterations - iterations_run),
            "recovery_attempts": recovery_attempt_count,
            "budget_exhausted": iterations_run >= max_iterations,
            "source_class_recovery_slot_available": max_iterations > 1,
        },
    )


__all__ = ["build_search_judgment_input_from_runtime"]
