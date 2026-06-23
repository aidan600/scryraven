"""Runtime input adapter for RunAuthority sufficiency judgment.

This module assembles compact, already-computed finalization facts into the
``RunSufficiencyJudgmentInput`` consumed by the bounded sufficiency executor. It
does not authorize actions, call models, reduce state, or decide sufficiency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
)


def build_sufficiency_judgment_input_from_runtime(
    *,
    contract_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    search_judgment_projection: Mapping[str, Any],
    search_judgment_history: Sequence[Mapping[str, Any]],
    answer_contract_projection: Mapping[str, Any],
    final_evidence_count: int,
    author_evidence_count: int,
    citation_eligible_candidate_count: int,
    conflicts_present: bool,
    scrutineer_flag_count: int,
    corpus_weak: bool,
    weak_corpus_reason: str | None,
    synth_was_insufficient: bool,
    failure_card_show: bool,
    failure_card_reason: str | None,
    iterations_run: int,
    max_iterations: int,
    recovery_attempt_count: int,
    initial_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    contract_amendment_admission_history: Sequence[Mapping[str, Any]] = (),
) -> RunSufficiencyJudgmentInput:
    """Build the AG-92C sufficiency input from runtime facts."""

    semantic_state_facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=initial_answer_contract or {},
        component_coverage_history=component_coverage_history,
        contract_amendment_admission_history=contract_amendment_admission_history,
    )

    return RunSufficiencyJudgmentInput(
        contract_projection=contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        search_judgment_projection=search_judgment_projection,
        search_judgment_history=search_judgment_history,
        answer_contract_projection=answer_contract_projection,
        source_obligation_projection=evidence_ledger_projection,
        final_evidence_facts={
            "final_evidence_count": final_evidence_count,
            "author_evidence_count": author_evidence_count,
            "citation_eligible_candidate_count": citation_eligible_candidate_count,
        },
        conflict_facts={
            "conflicts_present": bool(conflicts_present),
            "scrutineer_flag_count": scrutineer_flag_count,
            "conflict_posture": "unresolved" if conflicts_present else "none",
        },
        indirect_inference_facts={},
        weak_failure_facts={
            "corpus_weak": bool(corpus_weak),
            "weak_corpus_reason": weak_corpus_reason if corpus_weak else None,
            "synth_was_insufficient": bool(synth_was_insufficient),
            "failure_card": {
                "show": failure_card_show,
                "reason": failure_card_reason,
            },
        },
        budget={
            "iteration": iterations_run,
            "max_iterations": max_iterations,
            "remaining_budget": max(0, max_iterations - iterations_run),
            "recovery_attempts": recovery_attempt_count,
            "budget_exhausted": iterations_run >= max_iterations,
        },
        semantic_state_facts=semantic_state_facts,
    )


__all__ = ["build_sufficiency_judgment_input_from_runtime"]
