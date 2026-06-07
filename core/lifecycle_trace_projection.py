"""Deterministic lifecycle fact projections for orchestrator runtime traces."""

from __future__ import annotations

from typing import Any

from core.evidence_integration_checkpoint import (
    EvidenceIntegrationBudgetSnapshot,
    EvidenceIntegrationSnapshot,
)
from core.post_author_output_projection import (
    _scrutineer_allowed_by_contract,
    _scrutineer_allowed_by_mode,
)


def weak_corpus_lifecycle_facts(decision: Any | None) -> dict[str, Any] | None:
    """Serialize an already-computed weak-corpus controller decision."""
    if decision is None:
        return None
    return {
        "approved": bool(decision.approved),
        "reason": decision.reason,
        "blockers": list(decision.blockers),
    }


def conflict_resolution_lifecycle_facts(
    *,
    decision: Any | None,
    lifecycle_trace: dict[str, Any],
) -> dict[str, Any]:
    """Serialize an already-computed conflict decision or lifecycle fallback."""
    if decision is None:
        return {
            "approved": False,
            "reason": lifecycle_trace.get("active_conflict_resolution_skip_reason")
            or lifecycle_trace.get("active_conflict_resolution_reason")
            or "blocked_by_lifecycle",
            "blockers": list(
                lifecycle_trace.get("active_conflict_resolution_blockers") or []
            ),
            "active_conflict_resolution_considered": bool(
                lifecycle_trace.get("active_conflict_resolution_considered")
            ),
        }
    return {
        "approved": bool(decision.approved),
        "reason": decision.reason,
        "blockers": list(decision.blockers),
        "active_conflict_resolution_considered": bool(
            lifecycle_trace.get("active_conflict_resolution_considered")
        ),
    }


def _social_signal_requested_from_contract(contract: Any) -> bool:
    relevance = getattr(getattr(contract, "social_signal_relevance", None), "value", None)
    return str(relevance or "").casefold() == "central"


def build_evidence_integration_snapshot_from_runtime(
    *,
    answer_contract_result: Any,
    source_class_recovery_recommendation: dict[str, Any],
    active_source_class_recovery_lifecycle: dict[str, Any],
    strategy: str,
    is_sufficient: bool,
    corpus_weak: bool,
    corpus_state: str,
    weak_corpus_recovery_used: bool,
    weak_corpus_recovery_attempted: bool,
    weak_corpus_recovery_skip_reason: str | None,
    retrieval_stop_shadow_telemetry: dict[str, Any],
    iterations_run: int,
    max_iterations: int,
) -> EvidenceIntegrationSnapshot:
    """Build the compact AG-32 snapshot from already-computed runtime facts."""

    adapter = answer_contract_result.adapter_result
    contract = adapter.contract
    evidence_state = answer_contract_result.state.evidence_state_summary
    handoff = answer_contract_result.fulfillment_handoff
    source_recommendation = source_class_recovery_recommendation
    source_lifecycle = active_source_class_recovery_lifecycle
    stop_shadow = retrieval_stop_shadow_telemetry
    source_missing = (
        tuple(evidence_state.source_classes_missing)
        + tuple(source_recommendation.get("missing_expected_source_classes") or ())
        + tuple(source_lifecycle.get("active_source_class_recovery_missing_classes") or ())
    )
    source_queries = source_lifecycle.get(
        "active_source_class_recovery_queries"
    ) or source_recommendation.get("source_class_recovery_queries")
    source_class_eligible = bool(
        source_lifecycle.get("active_source_class_recovery_eligible")
    )
    next_query_count = int(stop_shadow.get("retrieval_stop_shadow_next_query_count") or 0)
    missing_information = tuple(answer_contract_result.state.missing_information)
    if stop_shadow.get("retrieval_stop_shadow_decision") == "continue_retrieval" and next_query_count:
        missing_information = missing_information + ("ordinary continuation gap",)
    social_requested = _social_signal_requested_from_contract(contract)
    scrutineer_contract_allowed = _scrutineer_allowed_by_contract(contract)
    scrutineer_mode_allowed = _scrutineer_allowed_by_mode(strategy)
    return EvidenceIntegrationSnapshot(
        contract_family=contract.family.value,
        contract_must_satisfy=contract.must_satisfy,
        contract_should_satisfy=contract.should_satisfy,
        required_source_classes=contract.evidence_classes_needed,
        fulfilled_contract_items=handoff.fulfilled_items,
        partial_contract_items=handoff.partial_items,
        unfulfilled_contract_items=handoff.unfulfilled_items,
        missing_information=missing_information,
        evidence_available=bool(evidence_state.evidence_available),
        evidence_sufficient=bool(is_sufficient and evidence_state.evidence_sufficient),
        evidence_reference_count=len(adapter.evidence_used),
        source_classes_present=evidence_state.source_classes_present,
        source_classes_missing=source_missing,
        weak_corpus=bool(corpus_weak),
        weak_corpus_reason=(
            (weak_corpus_recovery_skip_reason or corpus_state) if corpus_weak else None
        ),
        weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
        weak_corpus_recovery_available=bool(
            corpus_weak
            and not weak_corpus_recovery_used
            and not weak_corpus_recovery_attempted
            and weak_corpus_recovery_skip_reason in {None, "not_weak_corpus"}
        ),
        source_class_recovery_recommended=bool(
            source_recommendation.get("source_class_recovery_recommended")
        ),
        source_class_recovery_eligible=source_class_eligible,
        source_class_recovery_missing_classes=source_missing,
        source_class_recovery_queries_available=bool(source_queries),
        source_class_recovery_blockers=tuple(
            source_lifecycle.get("active_source_class_recovery_blockers") or ()
        ),
        conflicts_present=bool(evidence_state.conflicts_present),
        conflict_notes=evidence_state.conflict_notes,
        conflict_resolution_available=bool(evidence_state.resolving_queries),
        next_queries_available=bool(next_query_count),
        next_query_redundant=(
            stop_shadow.get("retrieval_stop_shadow_decision") == "stop_redundant_queries"
        ),
        prior_query_count=len(evidence_state.prior_queries),
        next_query_count=next_query_count,
        clarification_needed=False,
        social_signal_requested=social_requested,
        social_signal_status=evidence_state.social_signal_status,
        social_side_packet_placeholder_allowed=True,
        scrutineer_requested=bool(evidence_state.scrutineer_requested),
        scrutineer_needed=bool(evidence_state.scrutineer_needed),
        scrutineer_allowed_by_mode=scrutineer_mode_allowed,
        scrutineer_allowed_by_contract=scrutineer_contract_allowed,
        budget=EvidenceIntegrationBudgetSnapshot.from_runtime(
            mode=strategy,
            iteration=iterations_run,
            max_iterations=max_iterations,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
            source_class_recovery_attempt_count=0,
            source_class_slot_available=max_iterations > 1 or source_class_eligible,
            social_side_packet_placeholder_allowed=True,
            scrutineer_review_allowed=(
                scrutineer_mode_allowed and scrutineer_contract_allowed
            ),
        ),
        metadata={
            "stage": "post_retrieval_post_source_class_lifecycle_pre_source_class_execution",
            "shadow_only": True,
            "provider_routing_boundary": "orchestrator_owned",
            "search_depth_boundary": "orchestrator_owned",
        },
    )
