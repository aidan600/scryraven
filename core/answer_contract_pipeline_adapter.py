"""Passive pipeline-facts adapter for the answer-contract controller.

AG-2 keeps this module intentionally offline: it accepts already-shaped facts or
synthetic fixtures and converts them into AG-1 answer-contract records. It does
not call providers, models, prompts, retrieval, persistence, or orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Sequence

from core.answer_contract_controller import (
    AnswerContract,
    AnswerContractFulfillment,
    AnswerControllerActionResult,
    AnswerControllerCaps,
    AnswerControllerState,
    EvidenceReference,
    EvidenceStateSummary,
    apply_answer_controller_action_result,
    build_answer_contract_fulfillment,
    build_answer_controller_state,
    controller_action_from_retrieval_stop_decision,
    controller_action_from_source_class_recovery_decision,
    controller_action_from_weak_corpus_recovery_decision,
    draft_answer_contract_from_router_metadata,
)
from core.retrieval_stop_controller import RetrievalStopDecision
from core.source_class_recovery_controller import SourceClassRecoveryDecision
from core.weak_corpus_controller import WeakCorpusRecoveryDecision


def _copy_string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _merge_string_tuples(*values: Sequence[Any] | None) -> tuple[str, ...]:
    merged: list[Any] = []
    for value in values:
        merged.extend(value or ())
    return _copy_string_tuple(merged)


@dataclass(frozen=True)
class PipelineRouterFacts:
    """Router-shaped facts already produced elsewhere in the pipeline."""

    query: str
    intent: str | None = None
    report_type: str | None = None
    query_type: str | None = None
    mode: str | None = None
    current_date: str | None = None
    core_topic: str | None = None
    answer_goal: str | None = None


@dataclass(frozen=True)
class PipelineEvidenceReferenceFact:
    """Compact evidence reference safe enough to consider for handoff."""

    reference: str
    source_class: str | None = None
    summary: str | None = None
    supports: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineEvidenceFacts:
    """Pipeline-shaped evidence facts consumed passively by AG-2."""

    evidence_available: bool = False
    evidence_sufficient: bool = False
    source_classes_present: tuple[str, ...] = ()
    source_classes_missing: tuple[str, ...] = ()
    derive_missing_source_classes: bool = False
    fulfilled_obligations: tuple[str, ...] = ()
    partial_obligations: tuple[str, ...] = ()
    unfulfilled_obligations: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    approved_targeted_queries: tuple[str, ...] = ()
    prior_queries: tuple[str, ...] = ()
    next_queries: tuple[str, ...] = ()
    next_query_redundant: bool = False
    weak_corpus: bool = False
    weak_corpus_reason: str | None = None
    conflicts_present: bool = False
    conflict_notes: tuple[str, ...] = ()
    resolving_queries: tuple[str, ...] = ()
    quantitative_variables_needed: tuple[str, ...] = ()
    quantitative_assumptions_needed: tuple[str, ...] = ()
    social_provider_configured: bool = False
    social_signal_status: str | None = None
    scrutineer_requested: bool = False
    scrutineer_needed: bool = False
    evidence_references: tuple[PipelineEvidenceReferenceFact, ...] = ()
    warnings_to_analyst_or_author: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineControllerDecisionFacts:
    """Existing passive controller decisions that may be replayed as history."""

    source_class_recovery_decisions: tuple[SourceClassRecoveryDecision, ...] = ()
    weak_corpus_recovery_decisions: tuple[WeakCorpusRecoveryDecision, ...] = ()
    retrieval_stop_decisions: tuple[RetrievalStopDecision, ...] = ()


@dataclass(frozen=True)
class PipelineAnswerContractFacts:
    """All passive facts needed to build an AG-2 controller snapshot."""

    router: PipelineRouterFacts
    evidence: PipelineEvidenceFacts = PipelineEvidenceFacts()
    decisions: PipelineControllerDecisionFacts = PipelineControllerDecisionFacts()
    caps: AnswerControllerCaps | None = None
    iteration: int = 1


@dataclass(frozen=True)
class PipelineAnswerContractAdapterResult:
    """Complete passive adapter output for tests and offline harnesses."""

    contract: AnswerContract
    evidence_state_summary: EvidenceStateSummary
    state: AnswerControllerState
    evidence_used: tuple[EvidenceReference, ...]
    fulfillment_handoff: AnswerContractFulfillment


def build_answer_contract_from_pipeline_facts(facts: PipelineAnswerContractFacts) -> AnswerContract:
    """Draft an AnswerContract from router-shaped facts without touching Router."""
    router = facts.router
    contract = draft_answer_contract_from_router_metadata(
        query=router.query,
        intent=router.intent,
        report_type=router.report_type,
        query_type=router.query_type,
        mode=router.mode,
        core_topic=router.core_topic,
    )

    intent_parts = [contract.user_intent_interpretation]
    if router.current_date:
        intent_parts.append(f"Current date: {router.current_date}")

    answer_goal = router.answer_goal or contract.answer_goal
    return replace(
        contract,
        user_intent_interpretation="; ".join(intent_parts),
        answer_goal=answer_goal,
    )


def _derive_missing_source_classes(
    contract: AnswerContract,
    evidence: PipelineEvidenceFacts,
) -> tuple[str, ...]:
    explicit_missing = _copy_string_tuple(evidence.source_classes_missing)
    if evidence.evidence_sufficient or not evidence.derive_missing_source_classes:
        return explicit_missing

    present = {item.casefold() for item in evidence.source_classes_present}
    derived = [
        source_class
        for source_class in contract.evidence_classes_needed
        if source_class.casefold() not in present
    ]
    return _merge_string_tuples(explicit_missing, derived)


def build_evidence_state_summary_from_pipeline_facts(
    facts: PipelineAnswerContractFacts,
    *,
    contract: AnswerContract | None = None,
) -> EvidenceStateSummary:
    """Convert compact pipeline evidence facts into EvidenceStateSummary."""
    active_contract = contract or build_answer_contract_from_pipeline_facts(facts)
    evidence = facts.evidence
    missing_source_classes = _derive_missing_source_classes(active_contract, evidence)

    return EvidenceStateSummary(
        evidence_available=bool(evidence.evidence_available),
        evidence_sufficient=bool(evidence.evidence_sufficient),
        source_classes_present=_copy_string_tuple(evidence.source_classes_present),
        source_classes_missing=missing_source_classes,
        fulfilled_obligations=_copy_string_tuple(evidence.fulfilled_obligations),
        partial_obligations=_copy_string_tuple(evidence.partial_obligations),
        unfulfilled_obligations=_copy_string_tuple(evidence.unfulfilled_obligations),
        missing_information=_copy_string_tuple(evidence.missing_information),
        approved_targeted_queries=_copy_string_tuple(evidence.approved_targeted_queries),
        prior_queries=_copy_string_tuple(evidence.prior_queries),
        next_queries=_copy_string_tuple(evidence.next_queries),
        next_query_redundant=bool(evidence.next_query_redundant),
        weak_corpus=bool(evidence.weak_corpus),
        weak_corpus_reason=evidence.weak_corpus_reason,
        conflicts_present=bool(evidence.conflicts_present),
        conflict_notes=_copy_string_tuple(evidence.conflict_notes),
        resolving_queries=_copy_string_tuple(evidence.resolving_queries),
        quantitative_variables_needed=_copy_string_tuple(evidence.quantitative_variables_needed),
        quantitative_assumptions_needed=_copy_string_tuple(evidence.quantitative_assumptions_needed),
        social_provider_configured=bool(evidence.social_provider_configured),
        social_signal_status=evidence.social_signal_status,
        scrutineer_requested=bool(evidence.scrutineer_requested),
        scrutineer_needed=bool(evidence.scrutineer_needed),
    )


def build_evidence_references_from_pipeline_facts(
    facts: PipelineAnswerContractFacts,
) -> tuple[EvidenceReference, ...]:
    """Build compact handoff-safe evidence references from fixture facts."""
    return tuple(
        EvidenceReference(
            reference=item.reference,
            source_class=item.source_class,
            summary=item.summary,
            supports=_copy_string_tuple(item.supports),
        )
        for item in facts.evidence.evidence_references
        if str(item.reference or "").strip()
    )


def _decision_actions_from_pipeline_facts(
    facts: PipelineAnswerContractFacts,
    contract: AnswerContract,
) -> tuple[AnswerControllerActionResult, ...]:
    actions: list[AnswerControllerActionResult] = []
    iteration = max(1, int(facts.iteration or 1))

    for decision in facts.decisions.source_class_recovery_decisions:
        actions.append(
            controller_action_from_source_class_recovery_decision(
                decision,
                iteration=iteration,
                contract_items_affected=contract.evidence_classes_needed,
            )
        )
        iteration += 1

    for decision in facts.decisions.weak_corpus_recovery_decisions:
        actions.append(
            controller_action_from_weak_corpus_recovery_decision(
                decision,
                iteration=iteration,
                contract_items_affected=contract.evidence_classes_needed,
            )
        )
        iteration += 1

    for decision in facts.decisions.retrieval_stop_decisions:
        actions.append(controller_action_from_retrieval_stop_decision(decision, iteration=iteration))
        iteration += 1

    return tuple(actions)


def build_answer_controller_state_from_pipeline_facts(
    facts: PipelineAnswerContractFacts,
) -> AnswerControllerState:
    """Build an AnswerControllerState and passively replay existing decisions."""
    contract = build_answer_contract_from_pipeline_facts(facts)
    evidence_state = build_evidence_state_summary_from_pipeline_facts(
        facts,
        contract=contract,
    )
    state = build_answer_controller_state(
        contract,
        evidence_state_summary=evidence_state,
        caps=facts.caps,
        iteration=facts.iteration,
    )

    for action in _decision_actions_from_pipeline_facts(facts, contract):
        state = apply_answer_controller_action_result(state, action)

    return state


def adapt_pipeline_facts_to_answer_contract_controller(
    facts: PipelineAnswerContractFacts,
) -> PipelineAnswerContractAdapterResult:
    """Return contract, evidence summary, controller state, and safe handoff."""
    state = build_answer_controller_state_from_pipeline_facts(facts)
    evidence_used = build_evidence_references_from_pipeline_facts(facts)
    fulfillment = build_answer_contract_fulfillment(
        state,
        evidence_used=evidence_used,
        warnings_to_Analyst_or_Author=facts.evidence.warnings_to_analyst_or_author,
    )
    state.fulfillment_handoff_draft = fulfillment

    return PipelineAnswerContractAdapterResult(
        contract=state.active_contract,
        evidence_state_summary=state.evidence_state_summary,
        state=state,
        evidence_used=evidence_used,
        fulfillment_handoff=fulfillment,
    )


__all__ = [
    "PipelineAnswerContractAdapterResult",
    "PipelineAnswerContractFacts",
    "PipelineControllerDecisionFacts",
    "PipelineEvidenceFacts",
    "PipelineEvidenceReferenceFact",
    "PipelineRouterFacts",
    "adapt_pipeline_facts_to_answer_contract_controller",
    "build_answer_contract_from_pipeline_facts",
    "build_answer_controller_state_from_pipeline_facts",
    "build_evidence_references_from_pipeline_facts",
    "build_evidence_state_summary_from_pipeline_facts",
]
