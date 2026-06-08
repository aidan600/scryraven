"""Streamlit-free orchestration of the core research pipeline.

run_pipeline() is the single public entry-point.  It contains zero Streamlit
imports; all UI coupling is expressed through the StatusWriter protocol and
the RunConfig / RunDeps / RunOutcome dataclasses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from core import (
    analyst_runtime_stage,
    legacy_review_runtime_stage,
    post_analyst_handoff_packaging,
)
from core.anchor_resolution import (
    build_shadow_anchor_packet,
    format_anchor_context_for_researcher,
)
from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.answer_outcome import classify_answer_outcome
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.conflict_resolution_controller import (
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
    build_conflict_resolution_controller_input,
    build_conflict_resolution_lifecycle,
    conflict_resolution_lifecycle_defaults,
)
from core.context_measurement import (
    ContextMeasurementCollector,
    evidence_texts_from_passages,
    source_ids_from_passages,
)
from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
    checkpoint_action_name_from_trace,
)
from core.controller_recovery_decision import build_controller_recovery_decision
from core.controller_state_mirror import record_run_metadata_snapshot
from core.corpus_state import (
    CorpusState,
    classify_corpus_state,
    is_weak_corpus_state,
)
from core.cost_accounting import CostAccumulator
from core.entity_extraction import fallback_entities_from_query
from core.evidence_integration_checkpoint import (
    build_evidence_integration_checkpoint_trace,
    decide_evidence_integration_checkpoint,
    evidence_integration_checkpoint_unavailable_trace,
)
from core.evidence_registry_mirror import record_final_evidence_snapshot
from core.failure_card import (
    failure_card_reason,
    failure_card_should_show,
    normalize_force_corpus_state,
)
from core.final_answer_runtime_assembly import (
    assemble_final_answer_author_runtime_from_scope,
)
from core.final_evidence_bundle_builder import (
    FinalEvidenceBundleInputs,
    attach_author_evidence,
    build_final_evidence_bundle,
    build_final_source_telemetry_inputs,
)
from core.kb_review_persistence_context import build_kb_review_persistence_context

# AG-90K lifecycle projection sits beside retrieval_stop_trace_projection seams.
from core.lifecycle_trace_projection import (
    build_evidence_integration_snapshot_from_runtime as _build_evidence_integration_snapshot_from_runtime,
)
from core.lifecycle_trace_projection import (
    conflict_resolution_lifecycle_facts as _conflict_resolution_lifecycle_facts,
)
from core.lifecycle_trace_projection import (
    weak_corpus_lifecycle_facts as _weak_corpus_lifecycle_facts,
)
from core.nutrition_author_notes import (
    _format_nutrition_partial_evidence_author_note as _format_nutrition_partial_evidence_author_note,  # noqa: F401
)
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)
from core.ordinary_continuation_candidate import (
    ORDINARY_CONTINUATION_TRACE_KEY,
    mark_ordinary_continuation_candidate_spine_authorized,
    ordinary_continuation_candidate_defaults,
    source_path_from_runtime_source,
)
from core.ordinary_continuation_spine_gate import (
    EvaluatorContinuationSpineGateFacts,
    ExpanderContinuationSpineGateFacts,
    ScoutContinuationSpineGateFacts,
    authorize_evaluator_continuation_spine_gate,
    authorize_expander_continuation_spine_gate,
    authorize_scout_continuation_spine_gate,
    build_evaluator_continuation_candidate,
    build_evaluator_continuation_spine_pregate,
    build_expander_continuation_candidate,
    build_expander_continuation_spine_pregate,
    build_scout_continuation_candidate,
    build_scout_continuation_spine_pregate,
    evaluator_continuation_spine_gate_defaults,
    evaluator_continuation_spine_gate_exception_trace,
    expander_continuation_spine_gate_defaults,
    expander_continuation_spine_gate_exception_trace,
    scout_continuation_spine_gate_defaults,
    scout_continuation_spine_gate_exception_trace,
)
from core.outcome_persistence_packaging import (
    build_pipeline_config,
    build_session_payload,
)
from core.persistence_side_effects import execute_persistence_side_effects
from core.pipeline import (
    _quant_retrieval_sufficiency_shadow_telemetry,
    detect_nutrition_lookup_telemetry,
    economist_schema_telemetry_defaults,
    kb_review_agent,
    nutrition_lookup_telemetry_defaults,
    quant_retrieval_sufficiency_telemetry_defaults,
    thin_quant_preflight_missing_entities,
    validate_high_stakes_quantitative_query_shadow,
)
from core.policy import apply_policy_to_run_config, load_policy_state
from core.post_author_output_projection import (
    _build_runtime_conflict_state_projection,
    build_post_author_output_packaging_from_scope,
    build_post_author_trace_packaging_from_scope,
    build_run_outcome_from_scope,
)
from core.prompts import ROUTER_RETRY_USER_APPEND, SCOUT_REGISTRY
from core.protocols import StatusWriter
from core.provider_diagnostics import (
    build_provider_attempt_diagnostic,
    supported_diagnostic_kwargs,
)
from core.provider_plan import ProviderPlan
from core.quantitative_consistency import (
    apply_quantitative_consistency_guard,
    build_two_item_normalized_consistency_diagnostic,
    is_two_item_calorie_gram_comparison_candidate,
)
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.recovered_evidence_visibility import (
    apply_controller_recovered_evidence_visibility,
)
from core.retrieval_batch_dispatch import (
    RETRIEVAL_BATCH_DISPATCH_TRACE_KEY,
    RetrievalBatchDispatchFacts,
    build_retrieval_batch_dispatch_decision,
    retrieval_batch_dispatch_defaults,
)
from core.retrieval_dispatch_runtime import (
    execute_conflict_resolution_from_scope,
    execute_disambiguation_retry_from_scope,
    execute_main_retrieval_pass_from_scope,
    source_class_recovery_context_from_scope,
)
from core.retrieval_loop_contract import RETRIEVAL_LOOP_TRACE_KEY
from core.retrieval_quality import (
    DEFAULT_UTILIZATION_THRESHOLD,
    VERBOSITY_GATE_UTILIZATION_THRESHOLD,
    build_disambiguation_queries,
    extract_recon_context,
    format_quoted_anchor,
    official_bias_phrase,
    should_merge_recency_queries,
    should_retry_retrieval,
    utilization_entity_anchor,
    utilization_rate,
    wants_official_source_bias,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)
from core.retrieval_stop_trace_projection import (
    build_ordinary_continuation_trace_projection,
    build_retrieval_stop_active_stop_budget_exhausted_telemetry,
    build_retrieval_stop_active_stop_no_queries_telemetry,
    build_retrieval_stop_shadow_telemetry,
    build_retrieval_stop_trace_projection,
    retrieval_stop_active_defaults,
    retrieval_stop_shadow_defaults,
)
from core.review_flags import recent_recurring_kb_hints
from core.router_query_preparation_contract import (
    build_router_query_preparation_state,
    with_router_query_runtime_posture,
)
from core.routing import is_quantitative_query, merge_search_provider_overrides, select_providers
from core.run_config import RunConfig, RunDeps, RunOutcome
from core.run_controller import RunController
from core.run_logging import (
    current_code_version_metadata,
    log_run_failed,
    log_run_started,
)
from core.runtime_prompt_assembly import (
    build_analyst_cached_prefix_from_scope,
    build_author_prompt_from_scope,
    build_economist_preflight_prompt,
    build_expander_prompt,
    build_image_context,
    evidence_slice_for_analyst,
    select_author_system_prompt,
)
from core.search_providers import brave_reconnaissance
from core.source_class_recovery import (
    build_source_class_observability_telemetry,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_controller_mirror import (
    record_source_class_recovery_recommendation,
)
from core.source_class_recovery_lifecycle import (
    source_class_recovery_lifecycle_defaults,
)
from core.source_class_recovery_projection_handoff import (
    build_source_class_recovery_projection_handoff,
)
from core.source_class_recovery_runner import run_source_class_recovery_dispatch
from core.source_classifier import source_domain_telemetry, source_tier_telemetry
from core.source_recency import build_recency_author_notes
from core.stage_ledger_mirror import record_stage_ledger_query_provider_facts
from core.synthesis_evaluator_supplemental_search_runtime_handoff import (
    RuntimeSynthesisEvaluatorSupplementalSearchFactCollector,
)
from core.targeted_retrieval_controller import (
    build_targeted_retrieval_controller_input,
    build_targeted_retrieval_lifecycle,
    targeted_retrieval_lifecycle_defaults,
)
from core.useful_content import evaluate_useful_content
from core.weak_corpus_controller import (
    WeakCorpusRecoveryDecision,
    build_weak_corpus_recovery_controller_input,
    decide_weak_corpus_recovery,
    record_weak_corpus_recovery_decision,
    weak_corpus_recovery_trace_fields,
)
from core.weak_failure_gate_contract import (
    build_weak_failure_gate_state,
    execute_weak_failure_gate_handoff,
)

logger = logging.getLogger(__name__)

_author_quant_source_telemetry_defaults = (
    post_analyst_handoff_packaging._author_quant_source_telemetry_defaults
)
_economist_skip_eligibility_shadow_defaults = (
    post_analyst_handoff_packaging._economist_skip_eligibility_shadow_defaults
)
_economist_skip_eligibility_shadow_telemetry = (
    post_analyst_handoff_packaging._economist_skip_eligibility_shadow_telemetry
)
_economist_skip_shadow_alignment = (
    post_analyst_handoff_packaging._economist_skip_shadow_alignment
)
_scan_author_quant_source_telemetry = (
    post_analyst_handoff_packaging._scan_author_quant_source_telemetry
)


DB_ENABLED = True
_SOURCE_CLASS_RECOVERY_ORDINARY_BLOCK_REASONS = frozenset(
    {
        "blocked_by_currentness_gap",
        "blocked_by_official_current_source_gap",
        "blocked_by_legal_or_regulatory_current_event_gap",
        "blocked_by_reputable_news_or_primary_update_needed",
        "blocked_by_source_class_recovery",
    }
)

class PipelineError(RuntimeError):
    """Raised by run_pipeline() for expected failure conditions (empty query, no passages, …)."""

# ---------------------------------------------------------------------------
# Module-level helpers (moved from ui/pages.py inner functions)
# ---------------------------------------------------------------------------

def _clean_query(q: str) -> str:
    """Normalize query text and drop likely trailing token truncation."""
    q2 = " ".join((q or "").strip().split())
    if not q2:
        return ""
    words = q2.split(" ")
    last = words[-1]
    if len(last) < 3 and last.isalpha() and "." not in last:
        words = words[:-1]
    return " ".join(words)[:300]

_retrieval_stop_shadow_defaults = retrieval_stop_shadow_defaults
_retrieval_stop_active_defaults = retrieval_stop_active_defaults
_build_retrieval_stop_shadow_telemetry = build_retrieval_stop_shadow_telemetry
_build_retrieval_stop_active_stop_no_queries_telemetry = (
    build_retrieval_stop_active_stop_no_queries_telemetry
)
_build_retrieval_stop_active_stop_budget_exhausted_telemetry = (
    build_retrieval_stop_active_stop_budget_exhausted_telemetry
)

def _decide_retrieval_stop_for_active(
    snapshot: Any,
) -> Any:
    return decide_retrieval_stop(snapshot)

def _compact_runtime_strings(
    values: Any,
    *,
    max_items: int = 8,
    max_len: int = 180,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    iterable = values if isinstance(values, (list, tuple, set, frozenset)) else []
    for item in iterable:
        text = " ".join(str(item or "").strip().split())[:max_len]
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if len(out) >= max_items:
            break
    return out

def _targeted_query_provenance_from_runtime(source: str | None) -> str | None:
    return source_path_from_runtime_source(source)

def _targeted_retrieval_currentness_source_fit_facts(
    *,
    evidence_state: Any,
    source_class_recovery_telemetry: dict[str, Any],
    active_source_class_recovery_lifecycle: dict[str, Any],
) -> dict[str, bool]:
    missing_classes = set(
        _compact_runtime_strings(getattr(evidence_state, "source_classes_missing", ()))
    )
    missing_classes.update(
        _compact_runtime_strings(
            source_class_recovery_telemetry.get("missing_expected_source_classes")
        )
    )
    missing_classes.update(
        _compact_runtime_strings(
            active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_missing_classes"
            )
        )
    )
    gap_candidates = set(
        _compact_runtime_strings(
            source_class_recovery_telemetry.get("source_class_gap_candidates")
        )
    )
    source_fit_gaps = missing_classes | gap_candidates
    official_current_source_gap = "official_current_rules" in source_fit_gaps
    legal_or_regulatory_gap = "legal_or_regulatory_text" in source_fit_gaps

    text_facts = " ".join(
        _compact_runtime_strings(getattr(evidence_state, "missing_information", ()))
        + _compact_runtime_strings(
            getattr(evidence_state, "partial_obligations", ())
        )
        + _compact_runtime_strings(
            getattr(evidence_state, "unfulfilled_obligations", ())
        )
        + _compact_runtime_strings(
            active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_blockers"
            )
        )
        + _compact_runtime_strings(
            [active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_reason"
            )]
        )
    ).casefold()
    current_terms = (
        "current",
        "latest",
        "deadline",
        "injunction",
        "lawsuit",
        "enforcement",
        "policy change",
        "agency action",
        "regulatory event",
    )
    legal_terms = ("legal", "regulatory", "rule", "agency", "court")
    text_current_gap = any(term in text_facts for term in current_terms)
    text_legal_gap = any(term in text_facts for term in legal_terms)
    legal_or_regulatory_current_event_gap = bool(
        legal_or_regulatory_gap
        or (text_current_gap and text_legal_gap)
    )
    currentness_gap_detected = bool(
        official_current_source_gap
        or legal_or_regulatory_current_event_gap
        or text_current_gap
    )
    reputable_news_or_primary_update_needed = bool(
        currentness_gap_detected
        and (
            official_current_source_gap
            or legal_or_regulatory_current_event_gap
            or "reputable_news" in source_fit_gaps
            or "reputable_secondary" in source_fit_gaps
        )
    )
    final_answer_should_caveat_missing_current_source = bool(
        currentness_gap_detected
        and (official_current_source_gap or legal_or_regulatory_current_event_gap)
    )
    return {
        "currentness_gap_detected": currentness_gap_detected,
        "official_current_source_gap": official_current_source_gap,
        "legal_or_regulatory_current_event_gap": (
            legal_or_regulatory_current_event_gap
        ),
        "reputable_news_or_primary_update_needed": (
            reputable_news_or_primary_update_needed
        ),
        "final_answer_should_caveat_missing_current_source": (
            final_answer_should_caveat_missing_current_source
        ),
    }

def _build_ordinary_continuation_candidate_from_runtime(
    *,
    existing_candidate_trace: dict[str, Any],
    evidence_state: Any,
    conflict_resolving_queries: list[str] | tuple[str, ...] = (),
    current_iteration: int = 0,
    max_iterations: int = 0,
) -> dict[str, Any]:
    return build_ordinary_continuation_trace_projection(
        existing_candidate_trace=existing_candidate_trace,
        evidence_state=evidence_state,
        compact_runtime_strings_fn=_compact_runtime_strings,
        conflict_resolving_queries=conflict_resolving_queries,
        current_iteration=current_iteration,
        max_iterations=max_iterations,
    )

def _build_targeted_retrieval_lifecycle_from_runtime(
    *,
    answer_contract_result: Any,
    source_class_recovery_telemetry: dict[str, Any],
    active_source_class_recovery_lifecycle: dict[str, Any],
    weak_corpus_lifecycle_trace: dict[str, Any] | None,
    active_conflict_resolution_lifecycle: dict[str, Any],
    retrieval_stop_shadow_telemetry: dict[str, Any],
    retrieval_stop_active_telemetry: dict[str, Any],
    controller_loop_spine_result: Any,
    ordinary_continuation_candidate_trace: dict[str, Any],
    max_iterations: int,
) -> dict[str, Any]:
    state = getattr(answer_contract_result, "state", None)
    evidence_state = getattr(state, "evidence_state_summary", None)
    if evidence_state is None:
        return targeted_retrieval_lifecycle_defaults()

    checkpoint_action = getattr(
        controller_loop_spine_result,
        "checkpoint_action_name",
        None,
    )
    spine_authorization = getattr(
        controller_loop_spine_result,
        "dispatch_authorization",
        None,
    )
    blocked_actions = (
        getattr(spine_authorization, "blocked_or_skipped_actions", {}) or {}
    )
    ordinary_candidate = dict(ordinary_continuation_candidate_trace or {})
    candidate_queries = _compact_runtime_strings(
        ordinary_candidate.get("ordinary_next_queries")
    )
    prior_queries = _compact_runtime_strings(ordinary_candidate.get("prior_queries"))
    if not candidate_queries:
        candidate_queries = _compact_runtime_strings(
            getattr(evidence_state, "next_queries", ())
        )
    if not prior_queries:
        prior_queries = _compact_runtime_strings(
            getattr(evidence_state, "prior_queries", ())
        )
    material_gap_facts = (
        _compact_runtime_strings(getattr(evidence_state, "missing_information", ()))
        + _compact_runtime_strings(
            getattr(evidence_state, "partial_obligations", ())
        )
        + _compact_runtime_strings(
            getattr(evidence_state, "unfulfilled_obligations", ())
        )
        + _compact_runtime_strings(
            getattr(evidence_state, "source_classes_missing", ())
        )
    )
    retrieval_continue_gap = (
        retrieval_stop_shadow_telemetry.get("retrieval_stop_shadow_decision")
        == "continue_retrieval"
        and bool(candidate_queries)
    )
    source_fit_facts = _targeted_retrieval_currentness_source_fit_facts(
        evidence_state=evidence_state,
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        active_source_class_recovery_lifecycle=(
            active_source_class_recovery_lifecycle
        ),
    )
    source_class_dispatched = bool(
        controller_loop_spine_result.source_class_executor_dispatched
    )
    weak_corpus_dispatched = bool(
        controller_loop_spine_result.weak_corpus_executor_dispatched
    )
    conflict_dispatched = bool(
        controller_loop_spine_result.conflict_resolution_executor_dispatched
    )
    terminal_stop_approved = bool(controller_loop_spine_result.terminal_stop_approved)
    source_class_owns = bool(
        active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_used"
        )
        or active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_eligible"
        )
        or checkpoint_action == RECOVER_MISSING_SOURCE_CLASS
        or source_class_dispatched
    )
    weak_corpus_owns = bool(
        (weak_corpus_lifecycle_trace or {}).get("approved")
        or checkpoint_action == RECOVER_WEAK_CORPUS
        or weak_corpus_dispatched
    )
    conflict_owns = bool(
        active_conflict_resolution_lifecycle.get(
            "active_conflict_resolution_used"
        )
        or active_conflict_resolution_lifecycle.get(
            "active_conflict_resolution_eligible"
        )
        or checkpoint_action == RESOLVE_CONFLICT
        or conflict_dispatched
    )
    terminal_stop_owns = bool(
        terminal_stop_approved
        or checkpoint_action
        in {"stop_insufficient_with_caveat", "stop_sufficient"}
        or retrieval_stop_active_telemetry.get("retrieval_stop_active_available")
    )
    targeted_iteration = max(
        0,
        int(
            ordinary_candidate.get("current_iteration")
            or ordinary_candidate.get("iteration")
            or 0
        ),
    )
    conflict_resolving_queries = _compact_runtime_strings(
        ordinary_candidate.get("conflict_resolving_queries")
    )
    if not conflict_resolving_queries:
        conflict_resolving_queries = _compact_runtime_strings(
            getattr(evidence_state, "resolving_queries", ())
        )
    snapshot = build_targeted_retrieval_controller_input(
        material_contract_gap_remaining=bool(
            material_gap_facts or retrieval_continue_gap
        ),
        material_contract_gap=(
            material_gap_facts[0]
            if material_gap_facts
            else "ordinary continuation gap"
            if retrieval_continue_gap
            else None
        ),
        approved_ordinary_next_queries=candidate_queries,
        query_provenance=_targeted_query_provenance_from_runtime(
            ordinary_candidate.get("source_path")
            or ordinary_candidate.get("query_provenance")
        ),
        query_generation_complete=bool(candidate_queries),
        prior_queries=prior_queries,
        next_queries_redundant=bool(
            getattr(evidence_state, "next_query_redundant", False)
            or retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_decision"
            )
            == "stop_redundant_queries"
        ),
        redundancy_status=(
            "redundant"
            if retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_decision"
            )
            == "stop_redundant_queries"
            else "non_redundant"
            if candidate_queries
            else None
        ),
        iteration=targeted_iteration,
        max_iterations=max_iterations,
        targeted_budget_remaining=max(0, int(max_iterations - targeted_iteration)),
        prior_attempted_for_gap=False,
        source_class_recovery_owns_path=source_class_owns,
        weak_corpus_recovery_owns_path=weak_corpus_owns,
        conflict_resolution_owns_path=conflict_owns,
        terminal_stop_owns_path=terminal_stop_owns,
        source_class_blockers=active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_blockers"
        )
        or (),
        weak_corpus_blockers=(weak_corpus_lifecycle_trace or {}).get("blockers")
        or (),
        conflict_blockers=active_conflict_resolution_lifecycle.get(
            "active_conflict_resolution_blockers"
        )
        or (),
        provider_policy_reusable=True,
        provider_policy_change_required=False,
        provider_swap_required=False,
        search_depth_reusable=True,
        search_depth_policy_change_required=False,
        search_depth_escalation_required=False,
        legal_source_repair_required=False,
        conflict_resolving_queries=conflict_resolving_queries,
        metadata={
            "source": "runtime_passive_lifecycle",
            "ordinary_continuation_candidate": ordinary_candidate,
            "retrieval_stop_shadow_stage": retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_stage"
            ),
            "retrieval_stop_shadow_decision": retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_decision"
            ),
            "checkpoint_action_name": checkpoint_action,
            "blocked_or_skipped_actions": dict(blocked_actions),
        },
        **source_fit_facts,
    )
    return build_targeted_retrieval_lifecycle(snapshot).to_trace_fields()

def _authoritative_source_checkpoint_refresh_allowed(
    *,
    checkpoint_trace: dict[str, Any],
    official_canonical_recovery_execution_admitted: bool,
    active_source_class_recovery_lifecycle: dict[str, Any],
) -> bool:
    """Return whether a stale non-terminal checkpoint may be refreshed."""

    envelope = active_source_class_recovery_lifecycle.get(
        "active_source_class_recovery_action_envelope"
    )
    required_classes = (
        envelope.get("required_source_class") if isinstance(envelope, dict) else None
    )
    envelope_approved = bool(
        isinstance(envelope, dict)
        and envelope.get("action_type") == RECOVER_MISSING_SOURCE_CLASS
        and envelope.get("allowed_action") is True
        and isinstance(required_classes, list)
        and required_classes
    )
    checkpoint_action = checkpoint_action_name_from_trace(checkpoint_trace)
    blockers = set(
        active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_blockers"
        )
        or ()
    )
    return bool(
        official_canonical_recovery_execution_admitted
        and active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_eligible"
        )
        and envelope_approved
        and checkpoint_action
        not in {STOP_INSUFFICIENT_WITH_CAVEAT, STOP_SUFFICIENT}
        and not blockers
        & {
            "blocked_by_weak_corpus_recovery",
            "blocked_by_corpus_weak",
            "terminal_stop" + "_approved",
        }
    )

def _build_conflict_resolution_lifecycle_from_runtime_answer_contract(
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

def _extract_year(text: str) -> str:
    m = re.search(r"\b(19|20)\d{2}\b", text or "")
    return m.group(0) if m else "2026"

def _acc_iter_time(iter_idx: int, started_at: float, acc: dict[int, float]) -> None:
    elapsed = max(0.0, time.monotonic() - started_at)
    acc[iter_idx] = float(acc.get(iter_idx, 0.0)) + elapsed

def _has_explicit_retrieval_escalation(explicit_escalation_reason: str | None) -> bool:
    return bool(str(explicit_escalation_reason or "").strip())

def choose_retrieval_search_depth(
    complexity: str,
    base_search_depth: str | None,
    iteration: int,
    explicit_escalation_reason: str | None = None,
) -> str:
    """Choose main-loop retrieval depth without implicit medium second-pass escalation."""
    base_depth = str(base_search_depth or "basic").strip().lower() or "basic"
    if _has_explicit_retrieval_escalation(explicit_escalation_reason):
        return "advanced"
    if str(complexity or "").strip().lower() == "high":
        return "advanced"
    return base_depth

def choose_supplemental_search_depth(
    complexity: str,
    base_search_depth: str | None,
    explicit_escalation_reason: str | None = None,
) -> str:
    """Choose synthesis-gap supplemental retrieval depth from the same base policy."""
    base_depth = str(base_search_depth or "basic").strip().lower() or "basic"
    if _has_explicit_retrieval_escalation(explicit_escalation_reason):
        return "advanced"
    if str(complexity or "").strip().lower() == "high":
        return "advanced"
    return base_depth

def _weak_corpus_recovery_seed_queries(
    *,
    user_query: str,
    core_topic: str,
    primary_entity: str,
    canonical_subject: str | None,
    current_date: str,
    previous_queries: list[str] | None = None,
) -> list[str]:
    """Small deterministic query seed set for one bounded weak-corpus recovery pass."""
    anchor = (canonical_subject or primary_entity or core_topic or "").strip()
    uq = _clean_query(user_query)
    topic = _clean_query(core_topic)
    year = _extract_year(current_date)
    anchor_tokens = set(re.findall(r"[a-z0-9]+", anchor.casefold()))
    stop = {
        "about",
        "after",
        "and",
        "are",
        "before",
        "does",
        "expected",
        "find",
        "for",
        "give",
        "have",
        "into",
        "latest",
        "need",
        "show",
        "tell",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "what",
        "when",
        "where",
        "which",
        "with",
    }

    def _intent_terms(*texts: str, cap: int = 6) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for text in texts:
            for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]*", text or ""):
                key = tok.casefold().strip(".-")
                if len(key) < 3 or key in stop or key in anchor_tokens or key in seen:
                    continue
                seen.add(key)
                out.append(tok.strip(".-"))
                if len(out) >= cap:
                    return out
        return out

    def _sig(q: str) -> set[str]:
        return {
            t
            for t in re.findall(r"[a-z0-9]+", (q or "").casefold())
            if len(t) >= 3 and t not in stop
        }

    previous_sigs = [_sig(q) for q in (previous_queries or []) if q]

    def _is_near_previous(q: str) -> bool:
        s = _sig(q)
        if not s:
            return False
        for prev in previous_sigs:
            if not prev:
                continue
            overlap = len(s & prev) / max(1, len(s))
            if (s == prev) or (overlap >= 0.85 and len(s) <= len(prev) + 1):
                return True
        return False

    terms = _intent_terms(uq, topic)
    term_tail = " ".join(terms)
    compact_tail = " ".join(terms[:4])
    quoted_anchor = format_quoted_anchor(anchor)
    raw: list[str] = []

    if anchor and compact_tail:
        raw.append(f"{quoted_anchor} \"{compact_tail}\"")
    if anchor and wants_official_source_bias(user_query, "general"):
        phrase = official_bias_phrase(user_query)
        raw.append(f"{quoted_anchor} {phrase} {compact_tail}".strip())
    if anchor and term_tail:
        raw.append(f"{quoted_anchor} {term_tail}")
    if anchor and topic and topic.casefold() != anchor.casefold():
        raw.append(f"{quoted_anchor} {topic}")
    if anchor and term_tail and year:
        raw.append(f"{quoted_anchor} {term_tail} {year}")
    if not anchor and uq:
        raw.append(uq)

    seen: set[str] = set()
    seen_signatures: set[frozenset[str]] = set()
    out: list[str] = []
    for q in raw:
        q2 = _clean_query(q)
        k = q2.casefold()
        sig = frozenset(_sig(q2))
        if q2 and k not in seen and sig not in seen_signatures and not _is_near_previous(q2):
            seen.add(k)
            seen_signatures.add(sig)
            out.append(q2)
    return out[:4]

GENERIC_NEWS_DOMAINS = analyst_runtime_stage.GENERIC_NEWS_DOMAINS
_query_expects_official_evidence = analyst_runtime_stage.query_expects_official_evidence
_query_expects_community_evidence = analyst_runtime_stage.query_expects_community_evidence
_query_requires_clinical_trial_comparative_caution = (
    analyst_runtime_stage.query_requires_clinical_trial_comparative_caution
)


def _nutrition_macro_per_unit_lookup(query: str) -> bool:
    return bool(detect_nutrition_lookup_telemetry(query)["nutrition_lookup_detected"])


_pre_analyst_retrieval_gate = analyst_runtime_stage.pre_analyst_retrieval_gate
_post_economist_analyst_gate = analyst_runtime_stage.post_economist_analyst_gate



ANALYST_QUANT_PACKET_STRING_LIMIT = 200
ANALYST_QUANT_PACKET_SOURCE_VALUE_LIMIT = 12
ANALYST_QUANT_PACKET_CALCULATION_LIMIT = 8
ANALYST_QUANT_PACKET_REF_LIMIT = 12
MISSING_TARGET_METRIC_NOTE_LIMIT = 12


def _analyst_quant_packet_telemetry_defaults() -> dict[str, Any]:
    return {
        "analyst_quant_packet_present": False,
        "analyst_quant_packet_review_requested": False,
        "analyst_quant_packet_injected": False,
        "analyst_quant_packet_reviewed_by_model": False,
        "analyst_quant_packet_direct_use_eligible": False,
        "analyst_quant_packet_requires_analyst": True,
        "analyst_quant_packet_source": None,
        "analyst_quant_packet_gate_reason": "no_packet_for_analyst",
        "analyst_model_called": False,
    }


def _query_allows_proxy_or_qualitative_metric_framing(query: str) -> bool:
    text = str(query or "").replace("_", " ").replace("-", " ").casefold()
    return bool(
        re.search(
            r"\b("
            r"proxy|proxies|proxy only|proxy metric|indirect|directional|"
            r"qualitative|qualitatively"
            r")\b",
            text,
        )
    )


def _format_missing_target_metric_fallback_directive(
    *,
    query: str = "",
    report_type: str,
    quant_report_types: Any,
    economist_safety_telemetry: dict[str, Any],
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None = None,
    estimate_from_priors: bool = False,
) -> str:
    normalized_report_type = str(report_type or "").strip().lower()
    normalized_quant_types = {
        str(rt).strip().lower()
        for rt in (quant_report_types or [])
        if str(rt).strip()
    }
    bounded_quantitative_report = normalized_report_type in normalized_quant_types
    validation_errors = {
        str(error).strip()
        for error in (
            economist_safety_telemetry.get("quantitative_packet_validation_errors")
            or []
        )
        if str(error).strip()
    }
    missing_metrics = [
        str(metric).strip()[:ANALYST_QUANT_PACKET_STRING_LIMIT]
        for metric in (economist_safety_telemetry.get("target_metric_missing") or [])
        if str(metric).strip()
    ][:MISSING_TARGET_METRIC_NOTE_LIMIT]
    packet_missing_target = bool(
        bounded_quantitative_report
        and bool(economist_safety_telemetry.get("quantitative_packet_present"))
        and not bool(economist_safety_telemetry.get("quantitative_packet_valid"))
        and "target_metric_evidence_missing" in validation_errors
        and missing_metrics
    )

    retrieval_missing_metrics: list[str] = []
    if (
        bounded_quantitative_report
        and not estimate_from_priors
        and not bool(economist_safety_telemetry.get("quantitative_packet_valid"))
        and not _query_allows_proxy_or_qualitative_metric_framing(query)
        and isinstance(quant_retrieval_sufficiency_telemetry, dict)
        and bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_target_detected"
            )
        )
        and not bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_metric_coverage_valid"
            )
        )
        and bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_proxy_metric_detected"
            )
        )
    ):
        blockers = {
            str(blocker).strip()
            for blocker in (
                quant_retrieval_sufficiency_telemetry.get(
                    "quant_retrieval_sufficiency_blockers"
                )
                or []
            )
            if str(blocker).strip()
        }
        if "proxy_metric_only" in blockers and "missing_metric_coverage" in blockers:
            retrieval_missing_metrics = [
                str(metric).strip()[:ANALYST_QUANT_PACKET_STRING_LIMIT]
                for metric in (
                    quant_retrieval_sufficiency_telemetry.get(
                        "quant_retrieval_metrics"
                    )
                    or []
                )
                if str(metric).strip()
                and str(metric).strip() != "comparative_terms"
            ][:MISSING_TARGET_METRIC_NOTE_LIMIT]

    if retrieval_missing_metrics:
        for metric in retrieval_missing_metrics:
            if metric not in missing_metrics:
                missing_metrics.append(metric)
        missing_metrics = missing_metrics[:MISSING_TARGET_METRIC_NOTE_LIMIT]

    if not (packet_missing_target or retrieval_missing_metrics):
        return ""

    metric_list = ", ".join(missing_metrics)
    return (
        "\n\nNOTE FOR DOWNSTREAM SYNTHESIS - MISSING TARGET METRIC EVIDENCE:\n"
        "The requested quantitative target metric was not source-bound. "
        f"Missing metric evidence: {metric_list}. "
        "Available quantitative evidence may be adjacent or proxy-only; treat proxy "
        "evidence as proxy-only unless explicitly labeled that way. "
        "Do not present model-derived numeric estimates, ranges, or percent advantages "
        "for the missing metric. Answer qualitatively from available sourced evidence "
        "and explicitly state that direct evidence for the requested metric is missing.\n"
    )


def _extract_final_answer_source_ids(report: str) -> list[str]:
    return sorted({match for match in re.findall(r"\[\[(\d+)\]\]\(", str(report or ""))})


def _final_answer_source_citation_telemetry(
    report: str,
    economist_safety_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    final_source_ids = set(_extract_final_answer_source_ids(report))
    packet_source_ids: set[str] = set()
    packet = (
        economist_safety_telemetry.get("quantitative_packet")
        if isinstance(economist_safety_telemetry, dict)
        else None
    )
    if isinstance(packet, dict):
        packet_source_ids = {
            str(source_id).strip()
            for source_id in (packet.get("source_ids_used") or [])
            if str(source_id).strip()
        }

    return {
        "final_answer_source_ids_used": sorted(final_source_ids),
        "final_answer_source_ids_not_in_packet": sorted(final_source_ids - packet_source_ids),
        "packet_source_ids_not_in_final_answer": sorted(packet_source_ids - final_source_ids),
        "final_answer_packet_source_ids_diverged": bool(final_source_ids ^ packet_source_ids),
        "final_answer_source_telemetry_shadow_mode": True,
    }


def _economist_pre_analyst_skip_candidate_defaults() -> dict[str, Any]:
    return {
        "economist_pre_analyst_skip_candidate_shadow": False,
        "economist_pre_analyst_skip_candidate_reasons": [],
        "economist_pre_analyst_skip_candidate_blockers": [],
        "economist_pre_analyst_skip_candidate_gate_reason": "not_evaluated",
        "economist_pre_analyst_skip_candidate_shadow_mode": True,
    }


def _economist_pre_analyst_skip_candidate_telemetry(
    *,
    report_type: str,
    complexity: str,
    mode: str,
    economist_safety_telemetry: dict[str, Any],
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Diagnostic-only pre-Analyst skip candidate telemetry.

    This reports whether a future policy might consider a clean Economist packet
    reviewable. It is not runtime control flow and must not skip Analyst.
    """
    telemetry = _economist_pre_analyst_skip_candidate_defaults()
    reasons: list[str] = []
    blockers: list[str] = []

    bounded_quantitative = str(report_type).lower() in {
        "quantitative_comparison",
        "benchmark",
    }
    if bounded_quantitative:
        reasons.append("bounded_quantitative_report")
    else:
        blockers.append("non_bounded_quantitative_report")

    if str(complexity).lower() == "medium":
        reasons.append("medium_complexity")
    else:
        blockers.append("non_medium_complexity")

    packet_valid = bool(economist_safety_telemetry.get("quantitative_packet_valid"))
    packet_direct_use = bool(
        economist_safety_telemetry.get("quantitative_packet_direct_use_eligible")
    )
    packet_requires_analyst = bool(
        economist_safety_telemetry.get("quantitative_packet_requires_analyst")
    )
    if packet_valid:
        reasons.append("packet_valid")
    else:
        blockers.append("packet_invalid_or_missing")
    if packet_direct_use:
        reasons.append("packet_direct_use_eligible")
    else:
        blockers.append("packet_not_direct_use_eligible")
    if packet_requires_analyst:
        blockers.append("packet_requires_analyst")
    else:
        reasons.append("packet_does_not_require_analyst")

    if bool(economist_safety_telemetry.get("high_stakes_quant_detected")):
        blockers.append("high_stakes_requires_analyst")
    else:
        reasons.append("non_high_stakes")

    if bool(economist_safety_telemetry.get("economist_code_execution_requested")):
        blockers.append("economist_code_execution_requested")
    else:
        reasons.append("no_economist_code_request")

    if bounded_quantitative:
        quant_retrieval_sufficiency_telemetry = (
            quant_retrieval_sufficiency_telemetry or {}
        )
        retrieval_target_detected = bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_target_detected"
            )
        )
        retrieval_sufficiency_valid = bool(
            quant_retrieval_sufficiency_telemetry.get(
                "quant_retrieval_sufficiency_valid"
            )
        )
        if retrieval_target_detected and retrieval_sufficiency_valid:
            reasons.append("retrieval_sufficiency_valid")
        elif not retrieval_target_detected:
            blockers.append("retrieval_sufficiency_missing")
        else:
            blockers.append("retrieval_sufficiency_failed")

    candidate = not blockers
    if candidate:
        gate_reason = "candidate_shadow_only"
    elif "high_stakes_requires_analyst" in blockers:
        gate_reason = "blocked_by_high_stakes"
    elif "packet_invalid_or_missing" in blockers:
        gate_reason = "blocked_by_invalid_packet"
    elif (
        "retrieval_sufficiency_failed" in blockers
        or "retrieval_sufficiency_missing" in blockers
    ):
        gate_reason = "blocked_by_retrieval_sufficiency"
    elif "non_bounded_quantitative_report" in blockers:
        gate_reason = "blocked_by_report_type"
    elif "non_medium_complexity" in blockers:
        gate_reason = "blocked_by_complexity"
    elif "economist_code_execution_requested" in blockers:
        gate_reason = "blocked_by_code_request"
    else:
        gate_reason = "blocked_by_multiple_reasons"

    telemetry.update(
        {
            "economist_pre_analyst_skip_candidate_shadow": candidate,
            "economist_pre_analyst_skip_candidate_reasons": reasons,
            "economist_pre_analyst_skip_candidate_blockers": blockers,
            "economist_pre_analyst_skip_candidate_gate_reason": gate_reason,
            "economist_pre_analyst_skip_candidate_shadow_mode": True,
        }
    )
    return telemetry


def _truncate_analyst_quant_packet_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= ANALYST_QUANT_PACKET_STRING_LIMIT:
        return value
    return value[: ANALYST_QUANT_PACKET_STRING_LIMIT - 3] + "..."


def _sanitize_analyst_quant_packet_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_analyst_quant_packet_string(value)
    if isinstance(value, dict):
        return {
            str(_truncate_analyst_quant_packet_string(k)): _sanitize_analyst_quant_packet_value(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return [_sanitize_analyst_quant_packet_value(item) for item in value]
    return value


def _bounded_analyst_quant_packet_list(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_sanitize_analyst_quant_packet_value(item) for item in value[:limit]]


def _analyst_quant_packet_payload(
    telemetry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    handoff = _analyst_quant_packet_telemetry_defaults()
    packet = telemetry.get("quantitative_packet")
    packet_present = bool(telemetry.get("quantitative_packet_present"))
    packet_valid = bool(telemetry.get("quantitative_packet_valid"))
    handoff["analyst_quant_packet_present"] = packet_present
    if packet_present:
        handoff["analyst_quant_packet_gate_reason"] = str(
            telemetry.get("quantitative_packet_gate_reason") or "packet_not_available_for_analyst"
        )[:ANALYST_QUANT_PACKET_STRING_LIMIT]

    if not (packet_present and packet_valid and isinstance(packet, dict)):
        return handoff, None

    direct_use_eligible = bool(
        telemetry.get("quantitative_packet_direct_use_eligible", packet.get("direct_use_eligible", False))
    )
    requires_analyst = bool(
        telemetry.get("quantitative_packet_requires_analyst", packet.get("requires_analyst", True))
    )
    handoff.update(
        {
            "analyst_quant_packet_review_requested": True,
            "analyst_quant_packet_injected": True,
            "analyst_quant_packet_direct_use_eligible": direct_use_eligible,
            "analyst_quant_packet_requires_analyst": requires_analyst,
            "analyst_quant_packet_source": "economist_quantitative_packet_v1",
        }
    )

    sanitized = {
        "schema_version": _truncate_analyst_quant_packet_string(packet.get("schema_version")),
        "target_metric_names": _bounded_analyst_quant_packet_list(
            packet.get("target_metric_names", telemetry.get("target_metric_names")),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "source_bound_values": _bounded_analyst_quant_packet_list(
            packet.get("source_bound_values"),
            ANALYST_QUANT_PACKET_SOURCE_VALUE_LIMIT,
        ),
        "unsupported_values": _bounded_analyst_quant_packet_list(
            packet.get("unsupported_values"),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "calculation_results": _bounded_analyst_quant_packet_list(
            packet.get("calculation_results"),
            ANALYST_QUANT_PACKET_CALCULATION_LIMIT,
        ),
        "target_metric_bound_value_refs": _bounded_analyst_quant_packet_list(
            packet.get(
                "target_metric_bound_value_refs",
                telemetry.get("target_metric_bound_value_refs"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "target_metric_calculation_refs": _bounded_analyst_quant_packet_list(
            packet.get(
                "target_metric_calculation_refs",
                telemetry.get("target_metric_calculation_refs"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "high_stakes_quant_detected": bool(
            packet.get(
                "high_stakes_quant_detected",
                telemetry.get("high_stakes_quant_detected", False),
            )
        ),
        "high_stakes_quant_domain": _truncate_analyst_quant_packet_string(
            packet.get(
                "high_stakes_quant_domain",
                telemetry.get("high_stakes_quant_domain"),
            )
        ),
        "direct_use_eligible": direct_use_eligible,
        "requires_analyst": requires_analyst,
        "validation_errors": _bounded_analyst_quant_packet_list(
            packet.get(
                "validation_errors",
                telemetry.get("quantitative_packet_validation_errors"),
            ),
            ANALYST_QUANT_PACKET_REF_LIMIT,
        ),
        "gate_reason": str(
            telemetry.get("quantitative_packet_gate_reason")
            or packet.get("gate_reason")
            or "valid_packet_for_analyst_review"
        )[:ANALYST_QUANT_PACKET_STRING_LIMIT],
    }
    return handoff, sanitized


def _format_analyst_quant_packet_section(
    telemetry: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    handoff, packet = _analyst_quant_packet_payload(telemetry)
    if packet is None:
        return "", handoff
    serialized = json.dumps(packet, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    section = (
        "\n\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\n"
        "Instructions:\n"
        "- Treat this as structured evidence, not as a final conclusion.\n"
        "- Verify that the packet supports the user's requested metric.\n"
        "- Keep source_bound_values distinct from unsupported_values; unsupported_values are not sourced facts.\n"
        "- Check whether validation_errors is empty.\n"
        "- If direct_use_eligible is false, do not present it as a settled quantitative conclusion.\n"
        "- If high_stakes_quant_detected is true, apply extra caution and state limitations.\n"
        "- You may accept, reject, or qualify the packet.\n"
        "- Do not invent calculations or unstated values; do not cite unsupported_values as source-bound.\n"
        "Packet JSON:\n"
        f"{serialized}\n"
    )
    return section, handoff



def _pipeline_timing_payload(
    *,
    latency_seconds: float,
    pre_retrieval_seconds: float,
    recon_seconds: float,
    iter_timing_seconds: dict[int, float],
    scout_llm_seconds: float,
    expander_llm_seconds: float,
    gap_evaluator_llm_seconds: float,
    economist_seconds: float,
    analyst_seconds: float,
    synth_evaluator_seconds: float,
    scrutineer_seconds: float,
    author_seconds: float,
) -> dict[str, float]:
    i1 = float(iter_timing_seconds.get(1, 0.0))
    i2 = float(iter_timing_seconds.get(2, 0.0))
    i3 = float(iter_timing_seconds.get(3, 0.0))
    retrieval_iters = i1 + i2 + i3
    post_llm = (
        float(economist_seconds)
        + float(analyst_seconds)
        + float(synth_evaluator_seconds)
        + float(scrutineer_seconds)
        + float(author_seconds)
    )
    accounted = (
        float(pre_retrieval_seconds)
        + float(recon_seconds)
        + retrieval_iters
        + post_llm
    )
    return {
        "pre_retrieval_seconds": round(pre_retrieval_seconds, 2),
        "recon_seconds": round(float(recon_seconds), 2),
        "iter1_seconds": round(i1, 2),
        "iter2_seconds": round(i2, 2),
        "iter3_seconds": round(i3, 2),
        "scout_llm_seconds": round(scout_llm_seconds, 2),
        "expander_llm_seconds": round(expander_llm_seconds, 2),
        "gap_evaluator_llm_seconds": round(gap_evaluator_llm_seconds, 2),
        "economist_seconds": round(economist_seconds, 2),
        "analyst_seconds": round(analyst_seconds, 2),
        "synth_evaluator_seconds": round(synth_evaluator_seconds, 2),
        "scrutineer_seconds": round(scrutineer_seconds, 2),
        "author_seconds": round(author_seconds, 2),
        "synthesis_seconds": round(author_seconds, 2),
        "post_retrieval_llm_seconds": round(post_llm, 2),
        "timing_accounted_seconds": round(accounted, 2),
        "unaccounted_wall_seconds": round(max(0.0, float(latency_seconds) - accounted), 2),
    }


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def run_pipeline(
    config: RunConfig,
    deps: RunDeps,
    status: StatusWriter,
    accumulator: CostAccumulator,
) -> RunOutcome:
    """Execute the full research pipeline and return a RunOutcome.

    This function has zero Streamlit imports.  All progress reporting goes
    through *status* (a StatusWriter); all cost tracking goes through
    *accumulator* (a CostAccumulator).

    Raises PipelineError for expected failure conditions (empty query, zero
    passages extracted).  All other exceptions propagate after logging a
    run_failed event.
    """
    run_log = deps.logger
    pipeline_start_time = time.time()

    # --- Identity ---
    session_id = config.session_id or str(uuid.uuid4())
    run_id = config.run_id or str(uuid.uuid4())

    log_run_started(
        run_id=run_id,
        session_id=session_id,
        phase="pipeline",
        query=config.query,
        mode=config.mode,
        path=deps.execution_log_path,
        logger=run_log,
    )

    try:
        return _run_pipeline_inner(
            config=config,
            deps=deps,
            status=status,
            accumulator=accumulator,
            session_id=session_id,
            run_id=run_id,
            pipeline_start_time=pipeline_start_time,
        )
    except PipelineError:
        # Expected failures — logged but not re-wrapped.
        log_run_failed(
            run_id=run_id,
            session_id=session_id,
            phase="pipeline",
            latency_seconds=round(time.time() - pipeline_start_time, 2),
            error="PipelineError (expected failure — see caller)",
            mode=config.mode,
            path=deps.execution_log_path,
            logger=run_log,
        )
        raise
    except Exception as exc:
        log_run_failed(
            run_id=run_id,
            session_id=session_id,
            phase="pipeline",
            latency_seconds=round(time.time() - pipeline_start_time, 2),
            error=exc,
            mode=config.mode,
            path=deps.execution_log_path,
            logger=run_log,
        )
        raise


def _run_pipeline_inner(  # noqa: C901  (complexity — this mirrors the original monolith)
    *,
    config: RunConfig,
    deps: RunDeps,
    status: StatusWriter,
    accumulator: CostAccumulator,
    session_id: str,
    run_id: str,
    pipeline_start_time: float,
) -> RunOutcome:
    # ------------------------------------------------------------------
    # Unpack config / deps for readability (mirrors original pages.py locals)
    # ------------------------------------------------------------------
    run_log = deps.logger
    query = config.query
    if not query.strip():
        raise PipelineError("Query is empty.")

    strategy = config.mode
    focus_academic = config.focus_academic
    force_intent_news = config.force_intent_news
    include_domains = list(config.include_domains)
    exclude_domains = list(config.exclude_domains)
    fast_provider = config.fast_provider
    fast_model = config.fast_model
    smart_provider = config.smart_provider
    smart_model = config.smart_model
    embed_provider = config.embed_provider
    embed_model = config.embed_model
    local_url = config.local_url
    or_api_key = config.or_api_key
    use_reasoning = config.use_reasoning
    current_date = config.current_date

    a5_provider_override: list[str] | None = None
    if config.provider_override:
        a5_provider_override = [
            str(x).strip().lower() for x in config.provider_override if str(x).strip()
        ] or None

    a5_force_state = normalize_force_corpus_state(config.forced_corpus_state)
    corpus_state_forced_flag = False

    prior_run_history: list[dict[str, Any]] = list(config.prior_run_history)
    prior_snapshot_for_history = config.prior_snapshot_for_history
    prior_title_for_thread = config.prior_title

    # Cost-tracking wrappers
    def _ask(*, phase: str = "model"):
        base = deps.ask_model
        def wrapped(*args: Any, **kw: Any) -> Any:
            kw.setdefault("cost_accumulator", accumulator)
            kw.setdefault("cost_phase", phase)
            return base(*args, **kw)
        return wrapped

    def _embed(*, phase: str = "embedding"):
        base = deps.embed_texts
        def wrapped(*args: Any, **kw: Any) -> Any:
            kw.setdefault("cost_accumulator", accumulator)
            kw.setdefault("cost_phase", phase)
            return base(*args, **kw)
        return wrapped

    def _search(*, phase: str = "retrieval"):
        base = deps.process_search_queries
        def wrapped(*args: Any, **kw: Any) -> Any:
            diagnostic_kw = {
                key: kw.pop(key)
                for key in ("provider_diagnostics", "provider_role", "iteration")
                if key in kw
            }
            kw.update(supported_diagnostic_kwargs(base, diagnostic_kw))
            kw.setdefault("cost_accumulator", accumulator)
            kw.setdefault("cost_phase", phase)
            return base(*args, **kw)
        return wrapped

    def _linkup(*, phase: str = "retrieval"):
        base = deps.fetch_linkup_precision_block
        def wrapped(*args: Any, **kw: Any) -> Any:
            diagnostic_kw = {
                key: kw.pop(key)
                for key in ("provider_diagnostics",)
                if key in kw
            }
            kw.update(supported_diagnostic_kwargs(base, diagnostic_kw))
            kw.setdefault("cost_accumulator", accumulator)
            kw.setdefault("cost_phase", phase)
            return base(*args, **kw)
        return wrapped

    ask_model = _ask()
    embed_texts = _embed()
    process_search_queries = _search()
    fetch_linkup_precision_block = _linkup()

    DEFAULT_SYSTEM = deps.DEFAULT_SYSTEM
    NEWS_PREFERRED_DOMAINS = deps.NEWS_PREFERRED_DOMAINS
    ACADEMIC_DOMAINS = deps.ACADEMIC_DOMAINS
    QUANT_REPORT_TYPES = deps.QUANT_REPORT_TYPES
    context_measurement = ContextMeasurementCollector()
    _run_controller_mirror = RunController()
    active_source_class_recovery_lifecycle = source_class_recovery_lifecycle_defaults()
    active_conflict_resolution_lifecycle = conflict_resolution_lifecycle_defaults()
    targeted_retrieval_lifecycle_trace = targeted_retrieval_lifecycle_defaults()

    def _measure_context_stage(
        name: str,
        *,
        prompt: Any,
        system_prompt: Any | None = None,
        stable_prefix: Any | None = None,
        evidence_passages: list[dict[str, Any]] | None = None,
        evidence_texts: list[Any] | None = None,
        evidence_text: Any | None = None,
        source_ids: list[Any] | None = None,
    ) -> None:
        measured_prompt = (
            f"{system_prompt}\n{prompt}" if system_prompt is not None else prompt
        )
        stage_source_ids = (
            source_ids
            if source_ids is not None
            else source_ids_from_passages(evidence_passages)
            if evidence_passages is not None
            else None
        )
        stage_evidence_texts = (
            evidence_texts
            if evidence_texts is not None
            else evidence_texts_from_passages(evidence_passages)
            if evidence_passages is not None
            else None
        )
        context_measurement.add_stage(
            name,
            prompt=measured_prompt,
            stable_prefix=stable_prefix if stable_prefix is not None else system_prompt,
            evidence_text=evidence_text,
            evidence_texts=stage_evidence_texts,
            source_ids=stage_source_ids,
        )

    execution_log_path = deps.execution_log_path
    feedback_log_path = deps.feedback_log_path
    kb_triggers_path = deps.kb_triggers_path
    policy_state_path = deps.policy_state_path
    policy_journal_path = deps.policy_journal_path

    # ------------------------------------------------------------------
    # Pre-retrieval: routing, entity extraction, title, recon
    # ------------------------------------------------------------------
    linkup_block = ""
    total_chunks_embedded = 0
    total_urls_fetched = 0
    providers_by_iteration: list[list[str]] = []
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []
    scout_fired = False
    scout_key_used = None
    scout_queries: list[str] = []
    scout_skip_reason: str | None = None
    economist_preflight_allowed: bool | None = None
    economist_preflight_block_reason: str | None = None
    economist_preflight_missing_entities: list[str] = []
    missing_target_metric_directive_emitted = False
    author_system_prompt_key: str | None = None
    estimate_from_priors_requested = False
    estimate_from_priors_blocked_by_pre_analyst_gate = False
    economist_ran = False
    economist_safety_telemetry: dict[str, Any] = {
        "economist_code_execution_requested": False,
        "economist_code_execution_blocked": False,
        "economist_safety_status": "code_execution_disabled",
        "economist_skip_reason": None,
        **economist_schema_telemetry_defaults(),
    }
    quant_retrieval_sufficiency_telemetry: dict[str, Any] = (
        quant_retrieval_sufficiency_telemetry_defaults()
    )
    nutrition_lookup_telemetry: dict[str, Any] = nutrition_lookup_telemetry_defaults()
    analyst_quant_packet_handoff_telemetry: dict[str, Any] = (
        _analyst_quant_packet_telemetry_defaults()
    )
    author_quant_source_telemetry: dict[str, Any] = (
        _author_quant_source_telemetry_defaults()
    )
    economist_skip_eligibility_shadow_telemetry: dict[str, Any] = (
        _economist_skip_eligibility_shadow_defaults()
    )
    economist_pre_analyst_skip_candidate_telemetry: dict[str, Any] = (
        _economist_pre_analyst_skip_candidate_defaults()
    )
    economist_skip_shadow_alignment = "not_evaluated"
    analyst_skipped_after_economist = False
    analyst_after_economist_skip_reason: str | None = None
    economist_output_used_as_analysis = False
    scrutineer_ran = False
    first_synth_sufficient = True

    _bucket_pre_retrieval_t0 = time.monotonic()
    status.step(f"Routing query intent using {fast_provider} ({fast_model})...")
    router_prompt = f"Today is {current_date}.\nUser Topic: {query}"
    _measure_context_stage(
        "router",
        prompt=router_prompt,
        system_prompt=DEFAULT_SYSTEM["router"],
    )

    router_text = ask_model(
        router_prompt, DEFAULT_SYSTEM["router"],
        provider=fast_provider, model=fast_model, effort="low",
        base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=use_reasoning,
    )
    router_text = deps.clean_json_response(router_text)

    router_query_preparation_contract = build_router_query_preparation_state(
        query=query,
        router_text=router_text,
        fallback_entities=fallback_entities_from_query(query),
    )

    if not router_query_preparation_contract.entities:
        router_retry_prompt = f"Today is {current_date}.\nUser Topic: {query}\n\n{ROUTER_RETRY_USER_APPEND}"
        _measure_context_stage(
            "router_retry",
            prompt=router_retry_prompt,
            system_prompt=DEFAULT_SYSTEM["router"],
        )
        retry_router_text = ask_model(
            router_retry_prompt, DEFAULT_SYSTEM["router"],
            provider=fast_provider, model=fast_model, effort="low",
            base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=use_reasoning,
        )
        retry_router_text = deps.clean_json_response(retry_router_text)
        router_query_preparation_contract = build_router_query_preparation_state(
            query=query,
            router_text=router_text,
            fallback_entities=fallback_entities_from_query(query),
            retry_router_text=retry_router_text,
            retry_attempted=True,
        )

    intent = router_query_preparation_contract.intent
    report_type = router_query_preparation_contract.report_type
    image_mode = router_query_preparation_contract.image_mode
    core_topic = router_query_preparation_contract.core_topic
    is_academic = router_query_preparation_contract.is_academic
    query_type = router_query_preparation_contract.query_type
    primary_entity = router_query_preparation_contract.primary_entity
    entities_list = router_query_preparation_contract.entities_list
    router_entity_retry_used = router_query_preparation_contract.router_entity_retry_used
    router_original_report_type = router_query_preparation_contract.router_original_report_type
    router_original_query_type = router_query_preparation_contract.router_original_query_type
    routing_override_applied = False
    routing_override_reason: str | None = None
    nutrition_lookup_telemetry = detect_nutrition_lookup_telemetry(query)
    if nutrition_lookup_telemetry["nutrition_lookup_detected"]:
        report_type = "quantitative_comparison"
        routing_override_applied = True
        routing_override_reason = "nutrition_macro_per_100g_lookup"

    if focus_academic:
        is_academic = True
    if force_intent_news:
        intent = "news"

    anchor_packet_telemetry: dict[str, Any] = {}
    if strategy == "Balanced":
        anchor_packet_telemetry = build_shadow_anchor_packet(
            mode=strategy,
            query=query,
            current_date=current_date,
            intent=intent,
            report_type=report_type,
            router_original_report_type=router_original_report_type,
            query_type=query_type,
            router_original_query_type=router_original_query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            entities=entities_list,
            router_entity_retry_used=router_entity_retry_used,
        )

    if intent == "news":
        include_domains = list(set(include_domains + NEWS_PREFERRED_DOMAINS))

    if strategy == "Fast":
        complexity = "low"
    elif strategy == "Balanced":
        complexity = "medium"
    else:
        complexity = "high"

    if complexity == "high":
        max_queries = 3
        results_per_query = 8
        search_depth = "advanced"
        top_chunks = 40
        max_iterations = 3
    elif complexity == "medium":
        max_queries = 2
        results_per_query = 6
        search_depth = "basic"
        top_chunks = 20
        max_iterations = 2
    else:
        max_queries = 2
        results_per_query = 5
        search_depth = "basic"
        top_chunks = 8
        max_iterations = 1

    policy_state = load_policy_state(policy_state_path)
    cfg = apply_policy_to_run_config(
        {
            "utilization_threshold": DEFAULT_UTILIZATION_THRESHOLD,
            "synth_skip_utilization_threshold": DEFAULT_UTILIZATION_THRESHOLD,
        },
        policy_state,
    )
    utilization_threshold = float(cfg.get("utilization_threshold", DEFAULT_UTILIZATION_THRESHOLD))
    synth_skip_utilization_threshold = float(
        cfg.get("synth_skip_utilization_threshold", DEFAULT_UTILIZATION_THRESHOLD)
    )
    policy_applied = {
        "utilization_threshold": utilization_threshold,
        "synth_skip_utilization_threshold": synth_skip_utilization_threshold,
    }
    waste_flags: list[str] = []
    recon_fired = False
    recon_confidence: str | None = None
    canonical_subject_resolved: str | None = None
    recon_seconds = 0.0
    iter_timing_seconds: dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}
    synthesis_seconds = 0.0
    scout_llm_seconds = 0.0
    expander_llm_seconds = 0.0
    gap_evaluator_llm_seconds = 0.0
    economist_seconds = 0.0
    analyst_seconds = 0.0
    synth_evaluator_seconds = 0.0
    scrutineer_seconds = 0.0
    author_seconds = 0.0
    pre_retrieval_seconds = 0.0

    status.step(f"Core Topic: **{core_topic}**")
    try:
        for hint in recent_recurring_kb_hints(kb_triggers_path, limit=20, max_display=3):
            status.step(f"\u2139\ufe0f KB (recurring): {hint[:400]}")
    except Exception:
        pass

    if prior_title_for_thread:
        session_title = prior_title_for_thread
        status.step(f"Continuing thread: **{session_title}**")
    else:
        status.step("Generating session title...")
        title_prompt = (
            f"Generate a 3-5 word professional title for a research report about: {core_topic}. "
            "Return ONLY the title, no quotes or formatting."
        )
        session_title = ask_model(
            title_prompt, "You are a concise title generator.",
            provider=fast_provider, model=fast_model, effort="low",
            base_url=local_url, api_key=or_api_key, use_reasoning=False,
        ).replace('"', "").strip()
        if not session_title:
            session_title = query[:40]

    queries: list[str] = []
    _recon_qt = (query_type or "").lower()
    _recon_t0 = time.monotonic()
    if _recon_qt in ("person", "news", "current_events", "event"):
        _well_scoped = bool(re.search(r"\b(19|20)\d{2}\b", query or "")) and len(
            (primary_entity or core_topic or "").split()
        ) >= 4
        if _well_scoped:
            recon_confidence = "low"
            waste_flags.append("recon_skipped")
        elif not os.getenv("BRAVE_API_KEY"):
            waste_flags.append("recon_skipped")
        else:
            brave_call_completed = False
            try:
                status.step("Reconnaissance search (resolving entities and terms)\u2026")
                br = brave_reconnaissance(
                    (query or core_topic)[:500],
                    num_results=5,
                    cost_accumulator=accumulator,
                    cost_phase="recon",
                )
                brave_call_completed = True
                recon_url_count = len({str(item.get("url") or "") for item in br if item.get("url")})
                provider_diagnostics.append(
                    build_provider_attempt_diagnostic(
                        provider="brave",
                        provider_role="recon",
                        cost_phase="recon",
                        query=(query or core_topic)[:500],
                        max_results=5,
                        output_type="searchResults",
                        success=True,
                        result_count=len(br),
                        new_url_count=recon_url_count,
                        accepted_url_count=recon_url_count,
                    )
                )
                rctx = extract_recon_context(br)
                if (rctx.get("recon_titles") or "").strip() or (rctx.get("recon_snippets") or "").strip():
                    rw_in = (
                        f"Today is {current_date}.\n"
                        f"Original query: {query}\n"
                        f"Recon titles: {rctx.get('recon_titles', '')}\n"
                        f"Recon snippets: {rctx.get('recon_snippets', '')}\n"
                    )
                    _measure_context_stage(
                        "recon_rewriter",
                        prompt=rw_in,
                        system_prompt=DEFAULT_SYSTEM["recon_query_rewriter"],
                    )
                    rw_text = deps.clean_json_response(
                        ask_model(
                            rw_in, DEFAULT_SYSTEM["recon_query_rewriter"],
                            provider=fast_provider, model=fast_model, effort="low",
                            base_url=local_url, api_key=or_api_key,
                            require_json=True, use_reasoning=use_reasoning,
                        )
                    )
                    rw_data = json.loads(rw_text)
                    rqq = [
                        _clean_query(str(x))
                        for x in (rw_data.get("rewritten_queries") or [])
                        if _clean_query(str(x))
                    ]
                    if rqq:
                        queries = rqq
                        recon_fired = True
                        recon_confidence = (rw_data.get("recon_confidence") or "").strip() or None
                        csub = (rw_data.get("canonical_subject") or "").strip()
                        if csub:
                            canonical_subject_resolved = csub[:200]
                        if csub and csub.lower() == (core_topic or "").strip().lower():
                            recon_confidence = "low"
                        if (recon_confidence or "") in ("high", "medium") and csub:
                            primary_entity = csub[:200]
            except Exception as e:
                if not brave_call_completed:
                    provider_diagnostics.append(
                        build_provider_attempt_diagnostic(
                            provider="brave",
                            provider_role="recon",
                            cost_phase="recon",
                            query=(query or core_topic)[:500],
                            max_results=5,
                            output_type="searchResults",
                            success=False,
                            failure_type=type(e).__name__,
                        )
                    )
                run_log.warning("Reconnaissance skipped: %s", e)
                waste_flags.append("recon_skipped")
    recon_seconds = max(0.0, time.monotonic() - _recon_t0)

    _canon_ent = (canonical_subject_resolved or "").strip()[:200]
    if _canon_ent:
        lows = {e.casefold() for e in entities_list}
        if _canon_ent.casefold() not in lows:
            entities_list = [_canon_ent] + entities_list
    if entities_list:
        primary_entity = entities_list[0][:200]
    elif primary_entity.strip():
        entities_list = [primary_entity.strip()[:200]]
        primary_entity = entities_list[0][:200]

    empty_entity_flag = len(entities_list) == 0

    query_authority = build_query_plan_runtime_adapter(
        run_id=run_id,
        primary_entity=primary_entity,
        entities_list=entities_list,
        core_topic=core_topic,
        user_query=query,
        intent=intent,
        clean=_clean_query,
    )

    if not queries:
        status.step("Generating initial search plan...")
        anchor_context_for_researcher = (
            format_anchor_context_for_researcher(anchor_packet_telemetry)
            if strategy == "Balanced"
            else ""
        )
        anchor_context_section = (
            f"{anchor_context_for_researcher}\n"
            if anchor_context_for_researcher
            else ""
        )
        q_prompt = (
            f"Today is {current_date}.\n"
            f"Original Prompt: {query}\n"
            f"Core Topic: {core_topic}\n"
            f"Intent: {intent}\n"
            f"query_type: {query_type}\n"
            f"entities: {entities_list}\n"
            f"primary_entity: {primary_entity}\n"
            f"{anchor_context_section}"
            "If query_type is person, each search query must include a disambiguating term "
            "(role, employer, 'NYU', podcast, etc.) so results are not confused with other people. "
            "Return JSON with a queries array."
        )
        _measure_context_stage(
            "researcher",
            prompt=q_prompt,
            system_prompt=DEFAULT_SYSTEM["researcher"],
        )
        q_text = deps.clean_json_response(
            ask_model(
                q_prompt, DEFAULT_SYSTEM["researcher"],
                provider=fast_provider, model=fast_model, effort="low",
                base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=use_reasoning,
            )
        )
        try:
            queries_dict = json.loads(q_text)
            queries_raw = queries_dict.get("queries", []) if isinstance(queries_dict, dict) else queries_dict
            queries = [_clean_query(str(x)) for x in queries_raw if _clean_query(str(x))]
            if not queries:
                queries = [core_topic[:300]]
        except Exception:
            queries = [core_topic[:300]]
    else:
        status.step("Using recon-informed search queries (research planner skipped for pass 1).")

    queries = query_authority.finalize(queries, include_official_bias=True)
    current_queries = queries[:max_queries]
    recency_merge_used = False
    recency_merge_query: str | None = None
    if should_merge_recency_queries(query, intent, query_type) and current_queries is not None:
        y = _extract_year(current_date)
        _anchor = (primary_entity or core_topic or "")[:200]
        if _anchor and max_queries:
            recq = _clean_query(f"{_anchor} {y} news")
            recency_merge_used = True
            recency_merge_query = recq
            current_queries = query_authority.merge_recency(
                current_queries, recency_query=recq, max_queries=max_queries
            )
    current_queries = query_authority.finalize(
        current_queries, max_len=max_queries, include_official_bias=False
    )
    router_query_preparation_contract = with_router_query_runtime_posture(
        router_query_preparation_contract,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        primary_entity=primary_entity,
        entities=entities_list,
        is_academic=is_academic,
        routing_override_applied=routing_override_applied,
        routing_override_reason=routing_override_reason,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        complexity=complexity,
        max_queries=max_queries,
        results_per_query=results_per_query,
        search_depth=search_depth,
        top_chunks=top_chunks,
        max_iterations=max_iterations,
        recency_merge_used=recency_merge_used,
        recency_query=recency_merge_query,
        official_bias_requested=wants_official_source_bias(query, intent),
        official_bias_phrase=(official_bias_phrase(query) if wants_official_source_bias(query, intent) else None),
        finalized_queries=queries,
        current_queries=current_queries,
        query_source="recon" if recon_fired else "researcher",
    )
    intent = router_query_preparation_contract.intent
    report_type = router_query_preparation_contract.report_type
    query_type = router_query_preparation_contract.query_type
    primary_entity = router_query_preparation_contract.primary_entity
    entities_list = router_query_preparation_contract.entities_list

    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    collected_images: set[str] = set()
    past_searches: list[str] = []
    iteration = 1
    iterations_run = 0
    is_sufficient = False
    scout_context = None
    suppress_tavily = False
    scrutineer_high_count = 0
    queries_by_iteration: dict[int, list[str]] = {}
    synthesis_evaluator_supplemental_search_collector = (
        RuntimeSynthesisEvaluatorSupplementalSearchFactCollector()
    )
    retrieval_retry_used = False
    disambiguation_queries_by_iteration: dict[int, list[str]] = {}
    weak_corpus_recovery_considered = False
    weak_corpus_recovery_used = False
    weak_corpus_recovery_attempted = False
    weak_corpus_recovery_skip_reason: str | None = None
    weak_corpus_recovery_queries: list[str] = []
    weak_corpus_recovery_decision = "no_action"
    weak_corpus_recovery_reason = "not_evaluated"
    weak_corpus_recovery_blockers: list[str] = []
    retrieval_stop_shadow_telemetry = _retrieval_stop_shadow_defaults()
    retrieval_stop_active_telemetry = _retrieval_stop_active_defaults()
    ordinary_continuation_candidate_trace = (
        ordinary_continuation_candidate_defaults()
    )
    evidence_integration_checkpoint_trace = (
        evidence_integration_checkpoint_unavailable_trace("not_evaluated")
    )
    evidence_integration_checkpoint_handoff: dict[str, Any] = {}
    evidence_integration_checkpoint_decided = False
    evaluator_continuation_spine_gate_trace: dict[str, Any] = (
        evaluator_continuation_spine_gate_defaults()
    )
    expander_continuation_spine_gate_trace: dict[str, Any] = (
        expander_continuation_spine_gate_defaults()
    )
    scout_continuation_spine_gate_trace: dict[str, Any] = (
        scout_continuation_spine_gate_defaults()
    )
    retrieval_batch_dispatch_trace: dict[str, Any] = (
        retrieval_batch_dispatch_defaults()
    )
    retrieval_loop_contract_state = None
    weak_failure_gate_contract_state = None
    weak_corpus_decision_for_checkpoint_gate: WeakCorpusRecoveryDecision | None = None
    conflict_resolution_decision_for_checkpoint_gate: (
        ConflictResolutionDecision | None
    ) = None
    utilization_rate_val: float | None = None
    utilization_pre_retry: float | None = None
    corpus_state = (
        CorpusState.EMPTY_ENTITY.value if empty_entity_flag else CorpusState.HEALTHY.value
    )
    corpus_weak = False

    _embed_tail = " | ".join(e for e in (entities_list or [])[:8] if e).strip()
    _embed_topic = (
        (_embed_tail if _embed_tail else ((primary_entity or core_topic) or query))[:2000]
        or core_topic
    )
    query_embedding = embed_texts([_embed_topic], provider=embed_provider, model=embed_model, base_url=local_url)[0]
    analyst_effort = {"low": "low", "medium": "medium", "high": "high"}.get(complexity, "low")
    entity_hint_for_retrieval = (primary_entity or core_topic or "").strip() or None
    provider_plan = ProviderPlan.from_available_keys(
        {
            "tavily": bool(os.getenv("TAVILY_API_KEY")),
            "linkup": bool(os.getenv("LINKUP_API_KEY")),
            "exa": bool(os.getenv("EXA_API_KEY")),
        }
    )
    available_keys = provider_plan.available_keys()
    current_search_depth_for_recovery = search_depth

    pre_retrieval_seconds = max(0.0, time.monotonic() - _bucket_pre_retrieval_t0)

    force_component_providers: list[str] = []

    def _record_retrieval_stop_shadow_once(
        *,
        decision: RetrievalStopDecision,
        stage: str,
        evaluator_sufficient: bool | None,
        prior_queries: list[str] | tuple[str, ...] = (),
        next_queries: list[str] | tuple[str, ...] = (),
        query_source: str | None = None,
        weak_corpus_recovery_completed: bool = False,
        blockers: list[str] | tuple[str, ...] = (),
    ) -> None:
        nonlocal retrieval_stop_shadow_telemetry
        nonlocal ordinary_continuation_candidate_trace
        if retrieval_stop_shadow_telemetry.get(
            "retrieval_stop_shadow_available"
        ):
            return
        projection = build_retrieval_stop_trace_projection(
            decision=decision,
            stage=stage,
            evaluator_sufficient=evaluator_sufficient,
            iteration=iteration,
            max_iterations=max_iterations,
            prior_queries=prior_queries,
            next_queries=next_queries,
            query_source=query_source,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            weak_corpus_recovery_completed=weak_corpus_recovery_completed,
            blockers=blockers,
            build_shadow_telemetry=_build_retrieval_stop_shadow_telemetry,
        )
        retrieval_stop_shadow_telemetry = projection[
            "retrieval_stop_shadow_telemetry"
        ]
        ordinary_continuation_candidate_trace = projection[
            "ordinary_continuation_candidate_trace"
        ]

    def _decide_retrieval_loop_stop_continue(
        *,
        stage: str,
        evaluator_sufficient: bool | None,
        prior_queries: list[str] | tuple[str, ...] = (),
        next_queries: list[str] | tuple[str, ...] = (),
        query_source: str | None = None,
        weak_corpus_recovery_completed: bool = False,
        blockers: list[str] | tuple[str, ...] = (),
    ) -> RetrievalStopDecision:
        snapshot = build_retrieval_stop_controller_input(
            evaluator_sufficient=evaluator_sufficient,
            iteration=iteration,
            max_iterations=max_iterations,
            prior_queries=prior_queries,
            next_queries=next_queries,
            query_source=query_source,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            weak_corpus_recovery_completed=weak_corpus_recovery_completed,
            blockers=blockers,
        )
        decision = _decide_retrieval_stop_for_active(snapshot)
        _record_retrieval_stop_shadow_once(
            decision=decision,
            stage=stage,
            evaluator_sufficient=evaluator_sufficient,
            prior_queries=prior_queries,
            next_queries=next_queries,
            query_source=query_source,
            weak_corpus_recovery_completed=weak_corpus_recovery_completed,
            blockers=blockers,
        )
        return decision

    def _ensure_checkpoint_decision_for_weak_corpus_timing(
        *,
        weak_corpus_skip_reason: str | None,
    ) -> None:
        nonlocal evidence_integration_checkpoint_trace
        nonlocal evidence_integration_checkpoint_handoff
        nonlocal evidence_integration_checkpoint_decided

        if evidence_integration_checkpoint_decided:
            return

        try:
            source_tier_snapshot = source_tier_telemetry(all_passages)
            source_domain_snapshot = source_domain_telemetry(
                all_passages,
                domain_anchor=primary_entity or core_topic,
            )
            source_class_recommendation = build_source_class_recovery_recommendation(
                query=query,
                current_date=current_date,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_counts=source_domain_snapshot["source_domain_counts"],
                top_source_domains=source_domain_snapshot["top_source_domains"],
                official_evidence_found=source_tier_snapshot[
                    "official_evidence_found"
                ],
            )
            source_class_observability = build_source_class_observability_telemetry(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                final_top_evidence=all_passages,
                final_answer_source_ids=None,
            )
            (
                _weak_checkpoint_conflict_state,
                weak_checkpoint_conflict_projection,
            ) = _build_runtime_conflict_state_projection(
                query=query,
                core_topic=core_topic,
                primary_entity=primary_entity,
                current_date=current_date,
                final_top_evidence=all_passages,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_telemetry=source_domain_snapshot,
                source_class_observability={
                    **source_class_recommendation,
                    **source_class_observability,
                },
            )
            source_class_lifecycle = source_class_recovery_lifecycle_defaults()
            answer_contract_result = build_runtime_answer_contract_handoff(
                RuntimeAnswerContractFacts(
                    query=query,
                    intent=intent,
                    report_type=report_type,
                    query_type=query_type,
                    mode=strategy,
                    current_date=current_date,
                    core_topic=core_topic,
                    evidence_available=bool(all_passages),
                    evidence_sufficient=bool(is_sufficient),
                    source_tier_counts=source_tier_snapshot["source_tier_counts"],
                    source_class_recovery_telemetry={
                        **source_class_recommendation,
                        **source_class_observability,
                    },
                    active_source_class_recovery_lifecycle=source_class_lifecycle,
                    weak_corpus=bool(corpus_weak),
                    weak_corpus_reason=(
                        (weak_corpus_skip_reason or corpus_state)
                        if corpus_weak
                        else None
                    ),
                    weak_corpus_recovery_considered=bool(
                        weak_corpus_recovery_considered
                    ),
                    weak_corpus_recovery_used=False,
                    weak_corpus_recovery_skip_reason=weak_corpus_skip_reason,
                    conflicts_present=weak_checkpoint_conflict_projection[
                        "conflicts_present"
                    ],
                    conflict_notes=weak_checkpoint_conflict_projection[
                        "conflict_notes"
                    ],
                    resolving_queries=weak_checkpoint_conflict_projection[
                        "resolving_queries"
                    ],
                    retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                    retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                    queries_by_iteration=queries_by_iteration,
                    final_top_evidence=all_passages,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    max_recovery_attempts=1,
                )
            )
            checkpoint_snapshot = _build_evidence_integration_snapshot_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_recommendation=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                strategy=strategy,
                is_sufficient=is_sufficient,
                corpus_weak=corpus_weak,
                corpus_state=corpus_state,
                weak_corpus_recovery_used=False,
                weak_corpus_recovery_attempted=False,
                weak_corpus_recovery_skip_reason=weak_corpus_skip_reason,
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                iterations_run=iteration,
                max_iterations=max_iterations,
            )
            checkpoint_decision = decide_evidence_integration_checkpoint(
                checkpoint_snapshot
            )
            evidence_integration_checkpoint_trace = (
                build_evidence_integration_checkpoint_trace(
                    snapshot=checkpoint_snapshot,
                    decision=checkpoint_decision,
                    legacy_runtime_branch="weak_corpus_recovery_gate",
                )
            )
            evidence_integration_checkpoint_handoff = (
                checkpoint_decision.to_handoff_reference()
            )
        except Exception as exc:
            run_log.warning(
                "Non-fatal weak-corpus checkpoint decision omitted: %s",
                exc,
            )
            evidence_integration_checkpoint_trace = (
                evidence_integration_checkpoint_unavailable_trace(
                    "weak_corpus_checkpoint_exception"
                )
            )
            evidence_integration_checkpoint_handoff = {}
        evidence_integration_checkpoint_decided = True

    def _authorize_retrieval_batch_dispatch_for_current_continuation(
        *,
        source_class_lifecycle_trace: dict[str, Any] | None,
        weak_corpus_lifecycle_trace: dict[str, Any] | None,
        conflict_resolution_lifecycle_trace: dict[str, Any] | None,
    ) -> tuple[bool, list[str]]:
        nonlocal retrieval_batch_dispatch_trace
        try:
            decision = build_retrieval_batch_dispatch_decision(
                RetrievalBatchDispatchFacts.from_traces(
                    checkpoint_trace=evidence_integration_checkpoint_trace,
                    ordinary_continuation_candidate_trace=(
                        ordinary_continuation_candidate_trace
                    ),
                    targeted_retrieval_lifecycle_trace=(
                        targeted_retrieval_lifecycle_trace
                    ),
                    source_class_lifecycle_trace=source_class_lifecycle_trace,
                    weak_corpus_lifecycle_trace=weak_corpus_lifecycle_trace,
                    conflict_resolution_lifecycle_trace=(
                        conflict_resolution_lifecycle_trace
                    ),
                    evaluator_continuation_spine_gate_trace=(
                        evaluator_continuation_spine_gate_trace
                    ),
                    expander_continuation_spine_gate_trace=(
                        expander_continuation_spine_gate_trace
                    ),
                    scout_continuation_spine_gate_trace=(
                        scout_continuation_spine_gate_trace
                    ),
                )
            )
            retrieval_batch_dispatch_trace = decision.to_trace()
            return decision.dispatch_authorized, list(decision.authorized_queries)
        except Exception as exc:
            run_log.warning(
                "Non-fatal retrieval batch dispatch omitted: %s",
                exc,
            )
            retrieval_batch_dispatch_trace = retrieval_batch_dispatch_defaults(
                "retrieval_batch_dispatch_exception"
            )
            return False, []

    def _authorize_evaluator_continuation_before_scheduling(
        *,
        evaluator_queries: list[str],
    ) -> tuple[bool, list[str]]:
        nonlocal evidence_integration_checkpoint_trace
        nonlocal evidence_integration_checkpoint_handoff
        nonlocal evidence_integration_checkpoint_decided
        nonlocal ordinary_continuation_candidate_trace
        nonlocal targeted_retrieval_lifecycle_trace
        nonlocal evaluator_continuation_spine_gate_trace

        ordinary_continuation_candidate_trace = (
            build_evaluator_continuation_candidate(
                evaluator_queries=evaluator_queries,
                prior_queries=queries_by_iteration.get(iteration, []),
                current_iteration=iteration,
                max_iterations=max_iterations,
            )
        )
        try:
            source_tier_snapshot = source_tier_telemetry(all_passages)
            source_domain_snapshot = source_domain_telemetry(
                all_passages,
                domain_anchor=primary_entity or core_topic,
            )
            source_class_recommendation = build_source_class_recovery_recommendation(
                query=query,
                current_date=current_date,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_counts=source_domain_snapshot["source_domain_counts"],
                top_source_domains=source_domain_snapshot["top_source_domains"],
                official_evidence_found=source_tier_snapshot[
                    "official_evidence_found"
                ],
            )
            source_class_observability = build_source_class_observability_telemetry(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                final_top_evidence=all_passages,
                final_answer_source_ids=None,
            )
            (
                _evaluator_conflict_state,
                evaluator_conflict_projection,
            ) = _build_runtime_conflict_state_projection(
                query=query,
                core_topic=core_topic,
                primary_entity=primary_entity,
                current_date=current_date,
                final_top_evidence=all_passages,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_telemetry=source_domain_snapshot,
                source_class_observability={
                    **source_class_recommendation,
                    **source_class_observability,
                },
            )
            source_class_lifecycle = source_class_recovery_lifecycle_defaults()
            answer_contract_result = build_runtime_answer_contract_handoff(
                RuntimeAnswerContractFacts(
                    query=query,
                    intent=intent,
                    report_type=report_type,
                    query_type=query_type,
                    mode=strategy,
                    current_date=current_date,
                    core_topic=core_topic,
                    evidence_available=bool(all_passages),
                    evidence_sufficient=bool(is_sufficient),
                    source_tier_counts=source_tier_snapshot["source_tier_counts"],
                    source_class_recovery_telemetry={
                        **source_class_recommendation,
                        **source_class_observability,
                    },
                    active_source_class_recovery_lifecycle=source_class_lifecycle,
                    weak_corpus=bool(corpus_weak),
                    weak_corpus_reason=(
                        (weak_corpus_recovery_skip_reason or corpus_state)
                        if corpus_weak
                        else None
                    ),
                    weak_corpus_recovery_considered=bool(
                        weak_corpus_recovery_considered
                    ),
                    weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
                    weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                    conflicts_present=evaluator_conflict_projection[
                        "conflicts_present"
                    ],
                    conflict_notes=evaluator_conflict_projection["conflict_notes"],
                    resolving_queries=evaluator_conflict_projection[
                        "resolving_queries"
                    ],
                    retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                    retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                    queries_by_iteration=queries_by_iteration,
                    final_top_evidence=all_passages,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    max_recovery_attempts=1,
                )
            )
            checkpoint_snapshot = _build_evidence_integration_snapshot_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_recommendation=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                strategy=strategy,
                is_sufficient=is_sufficient,
                corpus_weak=corpus_weak,
                corpus_state=corpus_state,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
                weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                iterations_run=iteration,
                max_iterations=max_iterations,
            )
            checkpoint_decision = decide_evidence_integration_checkpoint(
                checkpoint_snapshot
            )
            checkpoint_trace = build_evidence_integration_checkpoint_trace(
                snapshot=checkpoint_snapshot,
                decision=checkpoint_decision,
                legacy_runtime_branch="evaluator_continuation_gate",
            )
            checkpoint_handoff = checkpoint_decision.to_handoff_reference()
            weak_corpus_lifecycle_for_gate = (
                _weak_corpus_lifecycle_facts(weak_corpus_decision_for_checkpoint_gate)
                if weak_corpus_recovery_considered
                else None
            )
            conflict_resolution_lifecycle_for_gate = (
                _conflict_resolution_lifecycle_facts(
                    decision=conflict_resolution_decision_for_checkpoint_gate,
                    lifecycle_trace=active_conflict_resolution_lifecycle,
                )
            )
            gate_facts = EvaluatorContinuationSpineGateFacts.from_traces(
                evaluator_queries=evaluator_queries,
                prior_queries=queries_by_iteration.get(iteration, []),
                current_iteration=iteration,
                max_iterations=max_iterations,
                checkpoint_trace=checkpoint_trace,
                checkpoint_handoff=checkpoint_handoff,
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
            )
            pregate_result = build_evaluator_continuation_spine_pregate(gate_facts)
            ordinary_continuation_candidate_trace = (
                pregate_result.ordinary_continuation_candidate_trace
            )
            targeted_trace = _build_targeted_retrieval_lifecycle_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_telemetry=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                active_conflict_resolution_lifecycle=(
                    active_conflict_resolution_lifecycle
                ),
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                controller_loop_spine_result=(
                    pregate_result.controller_loop_spine_result
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
                max_iterations=max_iterations,
            )
            gate_output = authorize_evaluator_continuation_spine_gate(
                EvaluatorContinuationSpineGateFacts.from_traces(
                    evaluator_queries=evaluator_queries,
                    prior_queries=queries_by_iteration.get(iteration, []),
                    current_iteration=iteration,
                    max_iterations=max_iterations,
                    checkpoint_trace=checkpoint_trace,
                    checkpoint_handoff=checkpoint_handoff,
                    source_class_lifecycle_trace=source_class_lifecycle,
                    weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                    conflict_resolution_lifecycle_trace=(
                        conflict_resolution_lifecycle_for_gate
                    ),
                    ordinary_continuation_candidate_trace=(
                        ordinary_continuation_candidate_trace
                    ),
                    targeted_retrieval_lifecycle_trace=targeted_trace,
                )
            )
            evidence_integration_checkpoint_trace = gate_output.checkpoint_trace
            evidence_integration_checkpoint_handoff = gate_output.checkpoint_handoff
            evidence_integration_checkpoint_decided = gate_output.checkpoint_decided
            ordinary_continuation_candidate_trace = (
                gate_output.ordinary_continuation_candidate_trace
            )
            targeted_retrieval_lifecycle_trace = (
                gate_output.targeted_retrieval_lifecycle_trace
            )
            evaluator_continuation_spine_gate_trace = (
                gate_output.evaluator_continuation_spine_gate_trace
            )
            if not gate_output.authorized:
                return gate_output.authorized, gate_output.authorized_queries
            return _authorize_retrieval_batch_dispatch_for_current_continuation(
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
            )
        except Exception as exc:
            run_log.warning(
                "Non-fatal evaluator continuation spine gate omitted: %s",
                exc,
            )
            evaluator_continuation_spine_gate_trace = (
                evaluator_continuation_spine_gate_exception_trace()
            )
            return False, list(evaluator_queries)

    def _authorize_expander_continuation_before_scheduling(
        *,
        component_queries: list[str],
    ) -> tuple[bool, list[str]]:
        nonlocal evidence_integration_checkpoint_trace
        nonlocal evidence_integration_checkpoint_handoff
        nonlocal evidence_integration_checkpoint_decided
        nonlocal ordinary_continuation_candidate_trace
        nonlocal targeted_retrieval_lifecycle_trace
        nonlocal expander_continuation_spine_gate_trace

        ordinary_continuation_candidate_trace = (
            build_expander_continuation_candidate(
                component_queries=component_queries,
                prior_queries=queries_by_iteration.get(iteration, []),
                current_iteration=iteration,
                max_iterations=max_iterations,
            )
        )
        try:
            source_tier_snapshot = source_tier_telemetry(all_passages)
            source_domain_snapshot = source_domain_telemetry(
                all_passages,
                domain_anchor=primary_entity or core_topic,
            )
            source_class_recommendation = build_source_class_recovery_recommendation(
                query=query,
                current_date=current_date,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_counts=source_domain_snapshot["source_domain_counts"],
                top_source_domains=source_domain_snapshot["top_source_domains"],
                official_evidence_found=source_tier_snapshot[
                    "official_evidence_found"
                ],
            )
            source_class_observability = build_source_class_observability_telemetry(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                final_top_evidence=all_passages,
                final_answer_source_ids=None,
            )
            (
                _expander_conflict_state,
                expander_conflict_projection,
            ) = _build_runtime_conflict_state_projection(
                query=query,
                core_topic=core_topic,
                primary_entity=primary_entity,
                current_date=current_date,
                final_top_evidence=all_passages,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_telemetry=source_domain_snapshot,
                source_class_observability={
                    **source_class_recommendation,
                    **source_class_observability,
                },
            )
            source_class_lifecycle = source_class_recovery_lifecycle_defaults()
            answer_contract_result = build_runtime_answer_contract_handoff(
                RuntimeAnswerContractFacts(
                    query=query,
                    intent=intent,
                    report_type=report_type,
                    query_type=query_type,
                    mode=strategy,
                    current_date=current_date,
                    core_topic=core_topic,
                    evidence_available=bool(all_passages),
                    evidence_sufficient=bool(is_sufficient),
                    source_tier_counts=source_tier_snapshot["source_tier_counts"],
                    source_class_recovery_telemetry={
                        **source_class_recommendation,
                        **source_class_observability,
                    },
                    active_source_class_recovery_lifecycle=source_class_lifecycle,
                    weak_corpus=bool(corpus_weak),
                    weak_corpus_reason=(
                        (weak_corpus_recovery_skip_reason or corpus_state)
                        if corpus_weak
                        else None
                    ),
                    weak_corpus_recovery_considered=bool(
                        weak_corpus_recovery_considered
                    ),
                    weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
                    weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                    conflicts_present=expander_conflict_projection[
                        "conflicts_present"
                    ],
                    conflict_notes=expander_conflict_projection["conflict_notes"],
                    resolving_queries=expander_conflict_projection[
                        "resolving_queries"
                    ],
                    retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                    retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                    queries_by_iteration=queries_by_iteration,
                    final_top_evidence=all_passages,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    max_recovery_attempts=1,
                )
            )
            checkpoint_snapshot = _build_evidence_integration_snapshot_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_recommendation=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                strategy=strategy,
                is_sufficient=is_sufficient,
                corpus_weak=corpus_weak,
                corpus_state=corpus_state,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
                weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                iterations_run=iteration,
                max_iterations=max_iterations,
            )
            checkpoint_decision = decide_evidence_integration_checkpoint(
                checkpoint_snapshot
            )
            checkpoint_trace = build_evidence_integration_checkpoint_trace(
                snapshot=checkpoint_snapshot,
                decision=checkpoint_decision,
                legacy_runtime_branch="expander_continuation_gate",
            )
            checkpoint_handoff = checkpoint_decision.to_handoff_reference()
            weak_corpus_lifecycle_for_gate = (
                _weak_corpus_lifecycle_facts(weak_corpus_decision_for_checkpoint_gate)
                if weak_corpus_recovery_considered
                else None
            )
            conflict_resolution_lifecycle_for_gate = (
                _conflict_resolution_lifecycle_facts(
                    decision=conflict_resolution_decision_for_checkpoint_gate,
                    lifecycle_trace=active_conflict_resolution_lifecycle,
                )
            )
            gate_facts = ExpanderContinuationSpineGateFacts.from_traces(
                component_queries=component_queries,
                prior_queries=queries_by_iteration.get(iteration, []),
                current_iteration=iteration,
                max_iterations=max_iterations,
                checkpoint_trace=checkpoint_trace,
                checkpoint_handoff=checkpoint_handoff,
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
            )
            pregate_result = build_expander_continuation_spine_pregate(gate_facts)
            ordinary_continuation_candidate_trace = (
                pregate_result.ordinary_continuation_candidate_trace
            )
            targeted_trace = _build_targeted_retrieval_lifecycle_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_telemetry=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                active_conflict_resolution_lifecycle=(
                    active_conflict_resolution_lifecycle
                ),
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                controller_loop_spine_result=(
                    pregate_result.controller_loop_spine_result
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
                max_iterations=max_iterations,
            )
            gate_output = authorize_expander_continuation_spine_gate(
                ExpanderContinuationSpineGateFacts.from_traces(
                    component_queries=component_queries,
                    prior_queries=queries_by_iteration.get(iteration, []),
                    current_iteration=iteration,
                    max_iterations=max_iterations,
                    checkpoint_trace=checkpoint_trace,
                    checkpoint_handoff=checkpoint_handoff,
                    source_class_lifecycle_trace=source_class_lifecycle,
                    weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                    conflict_resolution_lifecycle_trace=(
                        conflict_resolution_lifecycle_for_gate
                    ),
                    ordinary_continuation_candidate_trace=(
                        ordinary_continuation_candidate_trace
                    ),
                    targeted_retrieval_lifecycle_trace=targeted_trace,
                )
            )
            evidence_integration_checkpoint_trace = gate_output.checkpoint_trace
            evidence_integration_checkpoint_handoff = gate_output.checkpoint_handoff
            evidence_integration_checkpoint_decided = gate_output.checkpoint_decided
            ordinary_continuation_candidate_trace = (
                gate_output.ordinary_continuation_candidate_trace
            )
            targeted_retrieval_lifecycle_trace = (
                gate_output.targeted_retrieval_lifecycle_trace
            )
            expander_continuation_spine_gate_trace = (
                gate_output.expander_continuation_spine_gate_trace
            )
            return _authorize_retrieval_batch_dispatch_for_current_continuation(
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
            )
        except Exception as exc:
            run_log.warning(
                "Non-fatal expander continuation spine gate omitted: %s",
                exc,
            )
            expander_continuation_spine_gate_trace = (
                expander_continuation_spine_gate_exception_trace()
            )
            return False, []

    def _authorize_scout_continuation_before_scheduling(
        *,
        scout_queries_for_gate: list[str],
    ) -> tuple[bool, list[str]]:
        nonlocal evidence_integration_checkpoint_trace
        nonlocal evidence_integration_checkpoint_handoff
        nonlocal evidence_integration_checkpoint_decided
        nonlocal ordinary_continuation_candidate_trace
        nonlocal targeted_retrieval_lifecycle_trace
        nonlocal scout_continuation_spine_gate_trace

        ordinary_continuation_candidate_trace = build_scout_continuation_candidate(
            scout_queries=scout_queries_for_gate,
            prior_queries=queries_by_iteration.get(iteration, []),
            current_iteration=iteration,
            max_iterations=max_iterations,
        )
        try:
            source_tier_snapshot = source_tier_telemetry(all_passages)
            source_domain_snapshot = source_domain_telemetry(
                all_passages,
                domain_anchor=primary_entity or core_topic,
            )
            source_class_recommendation = build_source_class_recovery_recommendation(
                query=query,
                current_date=current_date,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_counts=source_domain_snapshot["source_domain_counts"],
                top_source_domains=source_domain_snapshot["top_source_domains"],
                official_evidence_found=source_tier_snapshot[
                    "official_evidence_found"
                ],
            )
            source_class_observability = build_source_class_observability_telemetry(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                final_top_evidence=all_passages,
                final_answer_source_ids=None,
            )
            (
                _scout_conflict_state,
                scout_conflict_projection,
            ) = _build_runtime_conflict_state_projection(
                query=query,
                core_topic=core_topic,
                primary_entity=primary_entity,
                current_date=current_date,
                final_top_evidence=all_passages,
                source_tier_counts=source_tier_snapshot["source_tier_counts"],
                source_domain_telemetry=source_domain_snapshot,
                source_class_observability={
                    **source_class_recommendation,
                    **source_class_observability,
                },
            )
            source_class_lifecycle = source_class_recovery_lifecycle_defaults()
            answer_contract_result = build_runtime_answer_contract_handoff(
                RuntimeAnswerContractFacts(
                    query=query,
                    intent=intent,
                    report_type=report_type,
                    query_type=query_type,
                    mode=strategy,
                    current_date=current_date,
                    core_topic=core_topic,
                    evidence_available=bool(all_passages),
                    evidence_sufficient=bool(is_sufficient),
                    source_tier_counts=source_tier_snapshot["source_tier_counts"],
                    source_class_recovery_telemetry={
                        **source_class_recommendation,
                        **source_class_observability,
                    },
                    active_source_class_recovery_lifecycle=source_class_lifecycle,
                    weak_corpus=bool(corpus_weak),
                    weak_corpus_reason=(
                        (weak_corpus_recovery_skip_reason or corpus_state)
                        if corpus_weak
                        else None
                    ),
                    weak_corpus_recovery_considered=bool(
                        weak_corpus_recovery_considered
                    ),
                    weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
                    weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                    conflicts_present=scout_conflict_projection[
                        "conflicts_present"
                    ],
                    conflict_notes=scout_conflict_projection["conflict_notes"],
                    resolving_queries=scout_conflict_projection[
                        "resolving_queries"
                    ],
                    retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                    retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                    queries_by_iteration=queries_by_iteration,
                    final_top_evidence=all_passages,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    max_recovery_attempts=1,
                )
            )
            checkpoint_snapshot = _build_evidence_integration_snapshot_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_recommendation=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                strategy=strategy,
                is_sufficient=is_sufficient,
                corpus_weak=corpus_weak,
                corpus_state=corpus_state,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
                weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                iterations_run=iteration,
                max_iterations=max_iterations,
            )
            checkpoint_decision = decide_evidence_integration_checkpoint(
                checkpoint_snapshot
            )
            checkpoint_trace = build_evidence_integration_checkpoint_trace(
                snapshot=checkpoint_snapshot,
                decision=checkpoint_decision,
                legacy_runtime_branch="scout_continuation_gate",
            )
            checkpoint_handoff = checkpoint_decision.to_handoff_reference()
            weak_corpus_lifecycle_for_gate = (
                _weak_corpus_lifecycle_facts(weak_corpus_decision_for_checkpoint_gate)
                if weak_corpus_recovery_considered
                else None
            )
            conflict_resolution_lifecycle_for_gate = (
                _conflict_resolution_lifecycle_facts(
                    decision=conflict_resolution_decision_for_checkpoint_gate,
                    lifecycle_trace=active_conflict_resolution_lifecycle,
                )
            )
            gate_facts = ScoutContinuationSpineGateFacts.from_traces(
                scout_queries=scout_queries_for_gate,
                prior_queries=queries_by_iteration.get(iteration, []),
                current_iteration=iteration,
                max_iterations=max_iterations,
                checkpoint_trace=checkpoint_trace,
                checkpoint_handoff=checkpoint_handoff,
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
            )
            pregate_result = build_scout_continuation_spine_pregate(gate_facts)
            ordinary_continuation_candidate_trace = (
                pregate_result.ordinary_continuation_candidate_trace
            )
            targeted_trace = _build_targeted_retrieval_lifecycle_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_telemetry=source_class_recommendation,
                active_source_class_recovery_lifecycle=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                active_conflict_resolution_lifecycle=(
                    active_conflict_resolution_lifecycle
                ),
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                controller_loop_spine_result=(
                    pregate_result.controller_loop_spine_result
                ),
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
                max_iterations=max_iterations,
            )
            gate_output = authorize_scout_continuation_spine_gate(
                ScoutContinuationSpineGateFacts.from_traces(
                    scout_queries=scout_queries_for_gate,
                    prior_queries=queries_by_iteration.get(iteration, []),
                    current_iteration=iteration,
                    max_iterations=max_iterations,
                    checkpoint_trace=checkpoint_trace,
                    checkpoint_handoff=checkpoint_handoff,
                    source_class_lifecycle_trace=source_class_lifecycle,
                    weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                    conflict_resolution_lifecycle_trace=(
                        conflict_resolution_lifecycle_for_gate
                    ),
                    ordinary_continuation_candidate_trace=(
                        ordinary_continuation_candidate_trace
                    ),
                    targeted_retrieval_lifecycle_trace=targeted_trace,
                )
            )
            evidence_integration_checkpoint_trace = gate_output.checkpoint_trace
            evidence_integration_checkpoint_handoff = gate_output.checkpoint_handoff
            evidence_integration_checkpoint_decided = gate_output.checkpoint_decided
            ordinary_continuation_candidate_trace = (
                gate_output.ordinary_continuation_candidate_trace
            )
            targeted_retrieval_lifecycle_trace = (
                gate_output.targeted_retrieval_lifecycle_trace
            )
            scout_continuation_spine_gate_trace = (
                gate_output.scout_continuation_spine_gate_trace
            )
            return _authorize_retrieval_batch_dispatch_for_current_continuation(
                source_class_lifecycle_trace=source_class_lifecycle,
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_gate,
                conflict_resolution_lifecycle_trace=(
                    conflict_resolution_lifecycle_for_gate
                ),
            )
        except Exception as exc:
            run_log.warning(
                "Non-fatal scout continuation spine gate omitted: %s",
                exc,
            )
            scout_continuation_spine_gate_trace = (
                scout_continuation_spine_gate_exception_trace()
            )
            return False, []

    # ------------------------------------------------------------------
    # Main retrieval loop
    # ------------------------------------------------------------------
    while iteration <= max_iterations and not is_sufficient:
        _iter_t0 = time.monotonic()
        if (
            iteration == 2
            and max_iterations >= 2
            and not weak_corpus_recovery_used
            and (queries_by_iteration.get(1) or [])
            and (current_queries or [])
        ):
            pre_search_stop_decision = _decide_retrieval_loop_stop_continue(
                stage="pre_search_redundant_queries",
                evaluator_sufficient=None,
                prior_queries=queries_by_iteration.get(1, []),
                next_queries=current_queries,
                query_source="pre_search",
            )
            if (
                pre_search_stop_decision.decision
                is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
            ):
                waste_flags.append("query_redundancy_skipped")
                break
        current_queries = query_authority.admit_execution_queries(
            current_queries,
            iteration=iteration,
            recovery_active=weak_corpus_recovery_used and iteration > 1,
        )
        queries_by_iteration = query_authority.queries_by_iteration()
        scout_override = list(force_component_providers) if force_component_providers else None
        provider_plan_record = provider_plan.record_main_retrieval(
            query_type=query_type,
            intent=intent,
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            base_search_depth=search_depth,
            iteration=iteration,
            primary_override=a5_provider_override,
            scout_override=scout_override,
            choose_search_depth=choose_retrieval_search_depth,
            merge_provider_overrides=merge_search_provider_overrides,
            select_provider_list=select_providers,
        )
        current_search_depth = provider_plan_record.search_depth or "basic"
        loop_providers = provider_plan_record.providers_list()
        current_search_depth_for_recovery = current_search_depth
        status.step(f"--- **Iteration {iteration}/{max_iterations}** ---")
        status.step(f"Executing Searches: {current_queries} ({current_search_depth} depth)")
        past_searches.extend(current_queries)

        force_component_providers = []
        status.step(f"Providers this pass: {', '.join(loop_providers)}")
        providers_by_iteration.append(list(loop_providers))
        similarity_prior_queries = (
            queries_by_iteration.get(iteration - 1, []) if iteration > 1 else None
        )
        retrieval_provider_role = (
            "weak_corpus_recovery"
            if weak_corpus_recovery_used and iteration > 1
            else "main_retrieval"
        )
        query_similarity_basis = (
            "previous_main_retrieval_iteration" if similarity_prior_queries else None
        )
        main_retrieval_outcome = execute_main_retrieval_pass_from_scope(
            locals(),
            retrieval_pass_records=retrieval_pass_records,
        )
        new_passages = main_retrieval_outcome.passages
        seen_url_delta = main_retrieval_outcome.seen_url_delta
        total_urls_fetched += seen_url_delta
        total_chunks_embedded += main_retrieval_outcome.chunk_delta
        retrieval_loop_contract_state = (
            main_retrieval_outcome.retrieval_loop_contract_state
        )
        to_merge = list(new_passages)

        if iteration == 1:
            _ent = utilization_entity_anchor(
                (primary_entity or core_topic or "").strip(), query_type
            )
            utilization_pre_retry = utilization_rate(to_merge, _ent) if _ent else None
            if (
                _ent
                and should_retry_retrieval(utilization_pre_retry)
                and not retrieval_retry_used
            ):
                rqs = build_disambiguation_queries(
                    query, core_topic, primary_entity, query_type, current_date
                )
                rqs = query_authority.finalize_disambiguation(rqs)
                if rqs:
                    disambiguation_queries_by_iteration[iteration] = list(rqs)
                    status.step("Low match to the main subject; trying disambiguation searches\u2026")
                    retrieval_retry_used = True
                    retry_outcome = execute_disambiguation_retry_from_scope(
                        locals(),
                        queries=rqs,
                        retrieval_pass_records=retrieval_pass_records,
                    )
                    retry_passages = retry_outcome.passages
                    total_urls_fetched += retry_outcome.seen_url_delta
                    total_chunks_embedded += retry_outcome.chunk_delta
                    past_searches.extend(rqs)
                    to_merge = to_merge + retry_passages
            u_post = utilization_rate(to_merge, _ent) if _ent else 1.0
            utilization_rate_val = u_post
            _low_ent_match = (
                bool(_ent)
                and u_post is not None
                and float(u_post) < float(utilization_threshold)
            )
            corpus_state = classify_corpus_state(
                empty_entity=empty_entity_flag,
                utilization_rate=u_post if _ent else None,
                utilization_threshold=utilization_threshold,
                estimate_from_priors=(
                    (not empty_entity_flag)
                    and _low_ent_match
                    and is_quantitative_query(query_type, report_type)
                ),
            ).value
            corpus_weak = is_weak_corpus_state(corpus_state)
            if a5_force_state:
                corpus_state = a5_force_state
                corpus_state_forced_flag = True
                corpus_weak = is_weak_corpus_state(corpus_state)
            if _ent and corpus_state == CorpusState.OFF_TOPIC.value:
                waste_flags.append("low_entity_utilization")
        elif not utilization_rate_val and (primary_entity or core_topic or "").strip():
            _ent2 = utilization_entity_anchor(
                (primary_entity or core_topic or "").strip(), query_type
            )
            utilization_rate_val = utilization_rate(list(new_passages), _ent2)

        if iteration == 1 and intent == "general" and not is_academic and not suppress_tavily:
            specialist_hits = [
                p for p in to_merge
                if p.get("_provider") in {"exa", "linkup"} and p.get("credibility", 0) >= 3
            ]
            if len(specialist_hits) >= 10:
                suppress_tavily = True
                status.step("Strong specialist-provider evidence found - deprioritizing Tavily on later passes.")

        all_passages.extend(to_merge)
        all_passages.sort(key=lambda x: x.get("score", 0), reverse=True)
        max_domain_chunks = 4 if complexity == "high" else (3 if complexity == "medium" else 2)
        diverse_top_evidence = deps.filter_top_evidence(all_passages, top_chunks, max_domain_chunks)

        if iteration == 1:
            recovery_queries: list[str] = []
            if corpus_weak and not weak_corpus_recovery_attempted and all_passages:
                recovery_seed_queries = _weak_corpus_recovery_seed_queries(
                    user_query=query,
                    core_topic=core_topic,
                    primary_entity=primary_entity,
                    canonical_subject=canonical_subject_resolved,
                    current_date=current_date,
                    previous_queries=queries_by_iteration.get(1, []) + disambiguation_queries_by_iteration.get(1, []),
                )
                recovery_cap = min(4, max(2, max_queries or 2))
                recovery_queries = query_authority.finalize_recovery(
                    recovery_seed_queries,
                    max_len=recovery_cap,
                    include_official_bias=True,
                )

            weak_corpus_snapshot = build_weak_corpus_recovery_controller_input(
                corpus_state=corpus_state,
                corpus_weak=corpus_weak,
                iteration=iteration,
                max_iterations=max_iterations,
                prior_attempted=weak_corpus_recovery_attempted,
                readable_passage_count=len(all_passages),
                recovery_queries=recovery_queries,
            )
            weak_corpus_decision = decide_weak_corpus_recovery(
                weak_corpus_snapshot
            )
            weak_corpus_decision_for_checkpoint_gate = weak_corpus_decision
            weak_corpus_recovery_decision_fields = (
                weak_corpus_recovery_trace_fields(weak_corpus_decision)
            )
            weak_corpus_recovery_decision = str(
                weak_corpus_recovery_decision_fields[
                    "weak_corpus_recovery_decision"
                ]
            )
            weak_corpus_recovery_reason = str(
                weak_corpus_recovery_decision_fields[
                    "weak_corpus_recovery_reason"
                ]
            )
            weak_corpus_recovery_blockers = list(
                weak_corpus_recovery_decision_fields[
                    "weak_corpus_recovery_blockers"
                ]
            )

            if weak_corpus_decision.considered:
                weak_corpus_recovery_considered = True
                checkpoint_skip_reason = (
                    None if weak_corpus_decision.approved else weak_corpus_decision.reason
                )
                _ensure_checkpoint_decision_for_weak_corpus_timing(
                    weak_corpus_skip_reason=checkpoint_skip_reason,
                )
                weak_corpus_spine_result = build_controller_loop_spine_result(
                    ControllerLoopSpineInput.from_traces(
                        checkpoint_trace=evidence_integration_checkpoint_trace,
                        weak_corpus_lifecycle_trace=_weak_corpus_lifecycle_facts(
                            weak_corpus_decision
                        ),
                    )
                )
                weak_corpus_authorization = (
                    weak_corpus_spine_result.dispatch_authorization
                )
                weak_corpus_authorized_action = (
                    weak_corpus_authorization.authorized_action_name
                )
                record_weak_corpus_recovery_decision(
                    _run_controller_mirror,
                    snapshot=weak_corpus_snapshot,
                    decision=weak_corpus_decision,
                    action_promoted=(
                        weak_corpus_authorized_action == RECOVER_WEAK_CORPUS
                    ),
                )
                if weak_corpus_decision.approved:
                    if weak_corpus_authorized_action == RECOVER_WEAK_CORPUS:
                        weak_corpus_recovery_attempted = True
                        weak_corpus_recovery_queries = list(
                            weak_corpus_decision.queries
                        )
                        status.step(f"Weak first-pass corpus; running bounded recovery searches: {weak_corpus_recovery_queries}")
                        weak_corpus_recovery_used = True
                        weak_corpus_recovery_skip_reason = None
                        current_queries = weak_corpus_recovery_queries
                        _acc_iter_time(iteration, _iter_t0, iter_timing_seconds)
                        iterations_run += 1
                        iteration += 1
                        continue
                    weak_corpus_recovery_skip_reason = str(
                        weak_corpus_authorization.blocked_or_skipped_actions.get(
                            RECOVER_WEAK_CORPUS,
                            "checkpoint_action_not_approved",
                        )
                    )
                    is_sufficient = True
                else:
                    weak_corpus_recovery_skip_reason = weak_corpus_decision.reason
                    is_sufficient = True

        if weak_corpus_recovery_used and iteration > 1:
            recovery_stop_decision = _decide_retrieval_loop_stop_continue(
                stage="weak_corpus_recovery_completed",
                evaluator_sufficient=None,
                prior_queries=queries_by_iteration.get(iteration - 1, []),
                next_queries=[],
                query_source="weak_corpus_recovery",
                weak_corpus_recovery_completed=True,
            )
            if (
                recovery_stop_decision.decision
                is RetrievalStopControllerDecision.STOP_AFTER_RECOVERY
            ):
                is_sufficient = True

        if iteration < max_iterations and not (corpus_weak and iteration == 1):
            expander_fired = False

            # --- SCOUT ---
            if iteration == 1 and complexity != "low":
                scout_config = SCOUT_REGISTRY.get(report_type)
                if scout_config and scout_config.get("fires_on_iteration") == iteration:
                    scout_chunks = all_passages[:scout_config["max_input_chunks"]]
                    if deps.should_skip_quant_scout(report_type, scout_chunks):
                        status.step("Evidence quality sufficient for direct comparison - skipping scout.")
                        scout_skip_reason = "numeric_evidence_sufficient"
                        scout_config = None
                if scout_config and scout_config.get("fires_on_iteration") == iteration:
                    scout_fired = True
                    scout_key_used = scout_config.get("prompt_key")
                    status.step(f"Running {scout_config['prompt_key']} to identify evidence requirements...")
                    _scout_t0 = time.monotonic()
                    scout_context = deps.run_scout(
                        scout_key=scout_config["prompt_key"],
                        core_topic=core_topic,
                        chunks=scout_chunks,
                        ask_model=ask_model,
                        clean_json_response=deps.clean_json_response,
                        fast_provider=fast_provider,
                        fast_model=fast_model,
                        base_url=local_url,
                        api_key=or_api_key,
                        status_container=status,
                    )
                    scout_llm_seconds += max(0.0, time.monotonic() - _scout_t0)
                    if scout_context and scout_config.get("replaces_expander"):
                        directed = scout_context.get("directed_queries", [])
                        if directed:
                            status.step(f"Scout identified {len(directed)} targeted queries: {directed}")
                            scout_query_cap = 4
                            finalized_scout_queries = query_authority.finalize_scout_continuation(
                                [
                                    str(q)[:300]
                                    for q in directed[:scout_query_cap]
                                    if str(q).strip()
                                ],
                                max_len=scout_query_cap,
                            )
                            scout_queries = list(finalized_scout_queries)
                            scout_stop_decision = _decide_retrieval_loop_stop_continue(
                                stage="scout_directed_continuation",
                                evaluator_sufficient=None,
                                prior_queries=queries_by_iteration.get(
                                    iteration, []
                                ),
                                next_queries=finalized_scout_queries,
                                query_source="scout",
                            )
                            if (
                                scout_stop_decision.decision
                                is not RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
                            ):
                                is_sufficient = True
                                continue
                            (
                                scout_continuation_authorized,
                                authorized_scout_queries,
                            ) = _authorize_scout_continuation_before_scheduling(
                                scout_queries_for_gate=finalized_scout_queries,
                            )
                            expander_fired = True
                            if not scout_continuation_authorized:
                                is_sufficient = True
                                continue
                            current_queries = list(authorized_scout_queries)
                            force_component_providers = select_providers(
                                query_type, intent, complexity, available_keys,
                                report_type=report_type, is_academic=is_academic,
                                suppress_tavily=suppress_tavily, override=["exa", "linkup"],
                                override_is_user=False,
                            )
                            _acc_iter_time(iteration, _iter_t0, iter_timing_seconds)
                            iterations_run += 1
                            iteration += 1
                            continue

            # --- QUERY EXPANDER ---
            if iteration == 1 and complexity in ("medium", "high") and intent != "news":
                status.step("Analyzing evidence gaps for component data...")
                expander_prompt = build_expander_prompt(
                    query=query,
                    core_topic=core_topic,
                    diverse_top_evidence=diverse_top_evidence,
                )
                expander_sys = DEFAULT_SYSTEM["expander"].replace("{expander_max}", str(max_queries))
                _measure_context_stage(
                    "expander",
                    prompt=expander_prompt,
                    system_prompt=expander_sys,
                    evidence_texts=[
                        str(p.get("text") or "")[:200]
                        for p in diverse_top_evidence[:12]
                    ],
                )
                _exp_t0 = time.monotonic()
                expander_text = deps.clean_json_response(
                    ask_model(
                        expander_prompt, expander_sys,
                        provider=fast_provider, model=fast_model, effort="low",
                        base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=False,
                    )
                )
                expander_llm_seconds += max(0.0, time.monotonic() - _exp_t0)
                try:
                    expander_data = json.loads(expander_text)
                    raw_component_queries = [
                        str(q)[:300] for q in expander_data.get("component_queries", [])
                    ]
                    component_queries = query_authority.finalize_expander_continuation(
                        raw_component_queries, max_len=max_queries
                    )
                    expander_reasoning = expander_data.get("reasoning", "")
                    if component_queries:
                        if len(component_queries) > max_queries:
                            run_log.warning(
                                "Expander returned %d queries despite prompt cap of %d. Truncating.",
                                len(component_queries), max_queries,
                            )
                        component_queries = component_queries[:max_queries]
                        expander_stop_decision = _decide_retrieval_loop_stop_continue(
                            stage="expander_component_queries",
                            evaluator_sufficient=None,
                            prior_queries=queries_by_iteration.get(iteration, []),
                            next_queries=component_queries,
                            query_source="expander",
                        )
                        if (
                            expander_stop_decision.decision
                            is not RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
                        ):
                            is_sufficient = True
                            continue
                        (
                            expander_continuation_authorized,
                            authorized_expander_queries,
                        ) = _authorize_expander_continuation_before_scheduling(
                            component_queries=component_queries,
                        )
                        expander_fired = True
                        if not expander_continuation_authorized:
                            is_sufficient = True
                            continue
                        current_queries = list(authorized_expander_queries)
                        run_log.info(
                            "Expander generated %d component queries: %s | Reason: %s",
                            len(current_queries), current_queries, expander_reasoning,
                        )
                        status.step(f"Component gaps identified: {current_queries}")
                        force_component_providers = select_providers(
                            query_type, intent, complexity, available_keys,
                            report_type=report_type, is_academic=is_academic,
                            suppress_tavily=suppress_tavily, override=None,
                        )
                        _acc_iter_time(iteration, _iter_t0, iter_timing_seconds)
                        iterations_run += 1
                        iteration += 1
                        continue
                    else:
                        run_log.info(
                            "Expander: evidence sufficient for component data. Reason: %s",
                            expander_reasoning,
                        )
                        status.step("Component data sufficient \u2014 proceeding to evaluator.")
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    run_log.warning("Expander JSON parse failed: %s. Falling through to evaluator.", e)

            # --- GAP EVALUATOR ---
            if not expander_fired:
                status.step(f"Evaluating data gaps with {fast_provider}...")
                evidence_block = "\n\n".join(
                    f"[{p['title']}]\n{p['text'][:800]}" for p in diverse_top_evidence
                )
                eval_prompt = (
                    f"Today is {current_date}.\nTopic: {core_topic}\n\n"
                    f"Past Searches Attempted:\n{past_searches}\n\n"
                    f"Evidence gathered so far:\n{evidence_block}\n\nExecute the evaluation process."
                )
                _measure_context_stage(
                    "evaluator",
                    prompt=eval_prompt,
                    system_prompt=DEFAULT_SYSTEM["evaluator"],
                    evidence_texts=[
                        str(p.get("text") or "")[:800]
                        for p in diverse_top_evidence
                    ],
                )
                _gev_t0 = time.monotonic()
                eval_text = deps.clean_json_response(
                    ask_model(
                        eval_prompt, DEFAULT_SYSTEM["evaluator"],
                        provider=fast_provider, model=fast_model, effort="low",
                        base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=use_reasoning,
                    )
                )
                gap_evaluator_llm_seconds += max(0.0, time.monotonic() - _gev_t0)
                try:
                    eval_data = json.loads(eval_text)
                    is_sufficient = eval_data.get("is_sufficient", False)
                    evaluator_sufficient_for_shadow = bool(is_sufficient)
                    evaluator_next_queries = [
                        _clean_query(str(q)) for q in eval_data.get("new_queries", [])
                        if _clean_query(str(q))
                    ][:2]
                    if intent == "news":
                        evaluator_next_queries = [
                            q if any(ch.isdigit() for ch in q)
                            else _clean_query(f"{q} {_extract_year(current_date)}")
                            for q in evaluator_next_queries
                        ]
                    evaluator_next_queries = query_authority.finalize_evaluator_continuation(
                        evaluator_next_queries, max_len=2
                    )
                    evaluator_stop_prior_queries = (
                        queries_by_iteration.get(1, []) if iteration == 1 else []
                    )
                    evaluator_stop_snapshot = build_retrieval_stop_controller_input(
                        evaluator_sufficient=evaluator_sufficient_for_shadow,
                        iteration=iteration,
                        max_iterations=max_iterations,
                        prior_queries=evaluator_stop_prior_queries,
                        next_queries=evaluator_next_queries,
                        query_source="evaluator",
                        weak_corpus_recovery_used=weak_corpus_recovery_used,
                    )
                    evaluator_stop_decision = _decide_retrieval_stop_for_active(
                        evaluator_stop_snapshot
                    )
                    evaluator_stop_stage = {
                        RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS: (
                            "evaluator"
                        ),
                        RetrievalStopControllerDecision.STOP_NO_QUERIES: (
                            "evaluator_no_queries"
                        ),
                        RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES: (
                            "evaluator_redundant_queries"
                        ),
                    }.get(evaluator_stop_decision.decision, "evaluator")
                    _record_retrieval_stop_shadow_once(
                        decision=evaluator_stop_decision,
                        stage=evaluator_stop_stage,
                        evaluator_sufficient=evaluator_sufficient_for_shadow,
                        prior_queries=evaluator_stop_prior_queries,
                        next_queries=evaluator_next_queries,
                        query_source="evaluator",
                    )
                    if (
                        evaluator_stop_decision.decision
                        is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS
                    ):
                        is_sufficient = True
                    elif (
                        evaluator_stop_decision.decision
                        is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
                    ):
                        waste_flags.append("query_redundancy_skipped")
                        is_sufficient = True
                    elif (
                        evaluator_stop_decision.decision
                        is RetrievalStopControllerDecision.STOP_NO_QUERIES
                    ):
                        retrieval_stop_active_telemetry = (
                            _build_retrieval_stop_active_stop_no_queries_telemetry(
                                stage="evaluator_no_queries",
                                evaluator_sufficient=False,
                                iteration=iteration,
                                max_iterations=max_iterations,
                                prior_queries=queries_by_iteration.get(
                                    iteration, []
                                ),
                                next_queries=[],
                                query_source="evaluator",
                                weak_corpus_recovery_used=(
                                    weak_corpus_recovery_used
                                ),
                                shadow_telemetry=retrieval_stop_shadow_telemetry,
                            )
                        )
                        is_sufficient = True
                    elif (
                        evaluator_stop_decision.decision
                        is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL
                    ):
                        (
                            evaluator_continuation_authorized,
                            authorized_evaluator_queries,
                        ) = _authorize_evaluator_continuation_before_scheduling(
                            evaluator_queries=list(evaluator_stop_decision.next_queries),
                        )
                        if evaluator_continuation_authorized:
                            current_queries = list(authorized_evaluator_queries)
                        else:
                            current_queries = []
                            source_class_block_reasons = {
                                str(reason)
                                for reason in (
                                    [
                                        evaluator_continuation_spine_gate_trace.get(
                                            "authorized_action_name"
                                        ),
                                        evaluator_continuation_spine_gate_trace.get(
                                            "checkpoint_action_name"
                                        ),
                                        evaluator_continuation_spine_gate_trace.get(
                                            "reason"
                                        ),
                                    ]
                                    + list(
                                        targeted_retrieval_lifecycle_trace.get(
                                            "targeted_retrieval_candidate_blockers"
                                        )
                                        or []
                                    )
                                )
                                if str(reason or "").strip()
                            }
                            if not (
                                RECOVER_MISSING_SOURCE_CLASS in source_class_block_reasons
                                or (
                                    source_class_block_reasons
                                    & _SOURCE_CLASS_RECOVERY_ORDINARY_BLOCK_REASONS
                                )
                            ):
                                is_sufficient = True
                    else:
                        is_sufficient = True
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    run_log.warning("Evaluator JSON parse failed: %s", e)
                    is_sufficient = True

        if iteration >= max_iterations and not is_sufficient:
            budget_stop_decision = _decide_retrieval_loop_stop_continue(
                stage="iteration_budget_exhausted",
                evaluator_sufficient=None,
                prior_queries=queries_by_iteration.get(iteration, []),
                next_queries=[],
                query_source="budget",
            )
            if (
                budget_stop_decision.decision
                is RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED
                and retrieval_stop_shadow_telemetry.get(
                    "retrieval_stop_shadow_decision"
                )
                == "stop_budget_exhausted"
            ):
                retrieval_stop_active_telemetry = (
                    _build_retrieval_stop_active_stop_budget_exhausted_telemetry(
                        stage="iteration_budget_exhausted",
                        evaluator_sufficient=None,
                        iteration=iteration,
                        max_iterations=max_iterations,
                        prior_queries=queries_by_iteration.get(iteration, []),
                        next_queries=[],
                        query_source="budget",
                        weak_corpus_recovery_used=weak_corpus_recovery_used,
                        shadow_telemetry=retrieval_stop_shadow_telemetry,
                    )
                )

        _acc_iter_time(iteration, _iter_t0, iter_timing_seconds)
        iterations_run += 1
        iteration += 1

    # ------------------------------------------------------------------
    # Post-retrieval: synthesis
    # ------------------------------------------------------------------
    if not all_passages:
        raise PipelineError("No readable passages were extracted.")

    _source_tier_recovery_lifecycle = source_tier_telemetry(all_passages)
    _source_domain_recovery_lifecycle = source_domain_telemetry(
        all_passages,
        domain_anchor=primary_entity or core_topic,
    )
    _source_class_recovery_lifecycle_recommendation = (
        build_source_class_recovery_recommendation(
            query=query,
            current_date=current_date,
            intent=intent,
            report_type=report_type,
            query_type=query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            anchor_packet=anchor_packet_telemetry,
            source_tier_counts=_source_tier_recovery_lifecycle[
                "source_tier_counts"
            ],
            source_domain_counts=_source_domain_recovery_lifecycle[
                "source_domain_counts"
            ],
            top_source_domains=_source_domain_recovery_lifecycle[
                "top_source_domains"
            ],
            official_evidence_found=_source_tier_recovery_lifecycle[
                "official_evidence_found"
            ],
        )
    )
    official_source_obligation_bridge_trace: dict[str, Any] | None = None
    official_canonical_recovery_query_acquisition_trace: dict[str, Any] | None = None
    official_canonical_recovery_execution_admission_trace: dict[str, Any] | None = None
    official_canonical_recovery_execution_admitted = False
    try:
        _source_class_recovery_answer_contract_observability = (
            build_source_class_observability_telemetry(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                core_topic=core_topic,
                primary_entity=primary_entity,
                anchor_packet=anchor_packet_telemetry,
                final_top_evidence=all_passages,
                final_answer_source_ids=None,
            )
        )
        (
            _pre_recovery_conflict_state,
            pre_recovery_conflict_projection,
        ) = _build_runtime_conflict_state_projection(
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            current_date=current_date,
            final_top_evidence=all_passages,
            source_tier_counts=_source_tier_recovery_lifecycle[
                "source_tier_counts"
            ],
            source_domain_telemetry=_source_domain_recovery_lifecycle,
            source_class_observability={
                **_source_class_recovery_lifecycle_recommendation,
                **_source_class_recovery_answer_contract_observability,
            },
        )
        _pre_recovery_answer_contract_result = build_runtime_answer_contract_handoff(
            RuntimeAnswerContractFacts(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                mode=strategy,
                current_date=current_date,
                core_topic=core_topic,
                evidence_available=bool(all_passages),
                evidence_sufficient=bool(is_sufficient),
                source_tier_counts=_source_tier_recovery_lifecycle[
                    "source_tier_counts"
                ],
                source_class_recovery_telemetry={
                    **_source_class_recovery_lifecycle_recommendation,
                    **_source_class_recovery_answer_contract_observability,
                },
                active_source_class_recovery_lifecycle=(
                    source_class_recovery_lifecycle_defaults()
                ),
                weak_corpus=bool(corpus_weak),
                weak_corpus_reason=(
                    (weak_corpus_recovery_skip_reason or corpus_state)
                    if corpus_weak
                    else None
                ),
                weak_corpus_recovery_considered=bool(
                    weak_corpus_recovery_considered
                ),
                weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
                weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                conflicts_present=pre_recovery_conflict_projection[
                    "conflicts_present"
                ],
                conflict_notes=pre_recovery_conflict_projection["conflict_notes"],
                resolving_queries=pre_recovery_conflict_projection[
                    "resolving_queries"
                ],
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                queries_by_iteration=queries_by_iteration,
                final_top_evidence=all_passages,
                iteration=iterations_run,
                max_iterations=max_iterations,
                max_recovery_attempts=1,
            )
        )
    except Exception as exc:
        run_log.warning(
            "Non-fatal answer-contract source-class recovery trigger omitted: %s",
            exc,
        )
    _authoritative_source_action_handoff = (
        build_authoritative_source_action_orchestrator_handoff(
            _run_controller_mirror,
            orchestrator_state=locals(),
            logger=run_log,
        )
    )
    (
        _source_class_recovery_lifecycle_recommendation,
        active_source_class_recovery_lifecycle,
        official_canonical_recovery_execution_admitted,
        official_source_obligation_bridge_trace,
        official_canonical_recovery_query_acquisition_trace,
        official_canonical_recovery_execution_admission_trace,
        authoritative_source_action_trace,
    ) = _authoritative_source_action_handoff.legacy_runtime_values()
    (
        active_conflict_resolution_lifecycle,
        conflict_resolution_decision_for_checkpoint_gate,
    ) = _build_conflict_resolution_lifecycle_from_runtime_answer_contract(
        answer_contract_result=_pre_recovery_answer_contract_result,
        current_search_depth=current_search_depth_for_recovery,
        iteration_budget_available=iterations_run < max_iterations,
        active_conflict_resolution_lifecycle=active_conflict_resolution_lifecycle,
    )
    if (
        evidence_integration_checkpoint_decided
        and _authoritative_source_checkpoint_refresh_allowed(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            official_canonical_recovery_execution_admitted=(
                official_canonical_recovery_execution_admitted
            ),
            active_source_class_recovery_lifecycle=(
                active_source_class_recovery_lifecycle
            ),
        )
    ):
        evidence_integration_checkpoint_decided = False
    if not evidence_integration_checkpoint_decided:
        try:
            _evidence_integration_snapshot = (
                _build_evidence_integration_snapshot_from_runtime(
                    answer_contract_result=_pre_recovery_answer_contract_result,
                    source_class_recovery_recommendation=(
                        _source_class_recovery_lifecycle_recommendation
                    ),
                    active_source_class_recovery_lifecycle=(
                        active_source_class_recovery_lifecycle
                    ),
                    strategy=strategy,
                    is_sufficient=is_sufficient,
                    corpus_weak=corpus_weak,
                    corpus_state=corpus_state,
                    weak_corpus_recovery_used=weak_corpus_recovery_used,
                    weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
                    weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                    retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                    iterations_run=iterations_run,
                    max_iterations=max_iterations,
                )
            )
            _evidence_integration_decision = decide_evidence_integration_checkpoint(
                _evidence_integration_snapshot
            )
            evidence_integration_checkpoint_trace = (
                build_evidence_integration_checkpoint_trace(
                    snapshot=_evidence_integration_snapshot,
                    decision=_evidence_integration_decision,
                    legacy_runtime_branch="existing_source_class_lifecycle",
                )
            )
            evidence_integration_checkpoint_handoff = (
                _evidence_integration_decision.to_handoff_reference()
            )
            evidence_integration_checkpoint_decided = True
        except Exception as exc:
            run_log.warning(
                "Non-fatal evidence-integration checkpoint omitted: %s",
                exc,
            )
            evidence_integration_checkpoint_trace = (
                evidence_integration_checkpoint_unavailable_trace(
                    "checkpoint_exception"
                )
            )
            if (
                official_canonical_recovery_execution_admitted
                and getattr(
                    _pre_recovery_answer_contract_result,
                    "adapter_result",
                    None,
                )
                is not None
            ):
                evidence_integration_checkpoint_trace[
                    "official_canonical_checkpoint_exception_fallback_allowed"
                ] = True
                evidence_integration_checkpoint_trace[
                    "official_canonical_checkpoint_exception_fallback_source"
                ] = "authoritative_source_action_handoff"
            evidence_integration_checkpoint_handoff = {}
            evidence_integration_checkpoint_decided = True

    weak_corpus_lifecycle_for_checkpoint_gate = (
        _weak_corpus_lifecycle_facts(weak_corpus_decision_for_checkpoint_gate)
        if weak_corpus_recovery_considered
        else None
    )
    ordinary_continuation_candidate_trace = (
        _build_ordinary_continuation_candidate_from_runtime(
            existing_candidate_trace=ordinary_continuation_candidate_trace,
            evidence_state=(
                getattr(
                    getattr(_pre_recovery_answer_contract_result, "state", None),
                    "evidence_state_summary",
                    None,
                )
            ),
            conflict_resolving_queries=(
                pre_recovery_conflict_projection["resolving_queries"]
                if "pre_recovery_conflict_projection" in locals()
                else ()
            ),
            current_iteration=iterations_run,
            max_iterations=max_iterations,
        )
    )
    controller_loop_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            source_class_lifecycle_trace=active_source_class_recovery_lifecycle,
            weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_checkpoint_gate,
            conflict_resolution_lifecycle_trace=(
                _conflict_resolution_lifecycle_facts(
                    decision=conflict_resolution_decision_for_checkpoint_gate,
                    lifecycle_trace=active_conflict_resolution_lifecycle,
                )
            ),
            ordinary_continuation_candidate_trace=(
                ordinary_continuation_candidate_trace
            ),
        ),
    )
    evidence_integration_checkpoint_trace = controller_loop_spine_result.trace_packet
    spine_authorization = controller_loop_spine_result.dispatch_authorization
    authorized_spine_action = spine_authorization.authorized_action_name
    try:
        targeted_retrieval_lifecycle_trace = (
            _build_targeted_retrieval_lifecycle_from_runtime(
                answer_contract_result=_pre_recovery_answer_contract_result,
                source_class_recovery_telemetry=(
                    _source_class_recovery_lifecycle_recommendation
                ),
                active_source_class_recovery_lifecycle=(
                    active_source_class_recovery_lifecycle
                ),
                weak_corpus_lifecycle_trace=(
                    weak_corpus_lifecycle_for_checkpoint_gate
                ),
                active_conflict_resolution_lifecycle=(
                    active_conflict_resolution_lifecycle
                ),
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                controller_loop_spine_result=controller_loop_spine_result,
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
                max_iterations=max_iterations,
            )
        )
    except Exception as exc:
        run_log.warning(
            "Non-fatal targeted-retrieval passive lifecycle omitted: %s",
            exc,
        )
        targeted_retrieval_lifecycle_trace = targeted_retrieval_lifecycle_defaults()
    controller_loop_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            source_class_lifecycle_trace=active_source_class_recovery_lifecycle,
            weak_corpus_lifecycle_trace=weak_corpus_lifecycle_for_checkpoint_gate,
            conflict_resolution_lifecycle_trace=(
                _conflict_resolution_lifecycle_facts(
                    decision=conflict_resolution_decision_for_checkpoint_gate,
                    lifecycle_trace=active_conflict_resolution_lifecycle,
                )
            ),
            ordinary_continuation_candidate_trace=(
                ordinary_continuation_candidate_trace
            ),
            targeted_retrieval_lifecycle_trace=targeted_retrieval_lifecycle_trace,
        ),
    )
    evidence_integration_checkpoint_trace = controller_loop_spine_result.trace_packet
    spine_authorization = controller_loop_spine_result.dispatch_authorization
    authorized_spine_action = spine_authorization.authorized_action_name
    if (
        retrieval_batch_dispatch_trace.get("dispatch_authorized")
        and (
            evaluator_continuation_spine_gate_trace.get(
                "targeted_retrieval_dispatch_authorized"
            )
            or expander_continuation_spine_gate_trace.get(
                "targeted_retrieval_dispatch_authorized"
            )
            or scout_continuation_spine_gate_trace.get(
                "targeted_retrieval_dispatch_authorized"
            )
        )
    ):
        authorized_gate_trace = (
            scout_continuation_spine_gate_trace
            if scout_continuation_spine_gate_trace.get(
                "targeted_retrieval_dispatch_authorized"
            )
            else expander_continuation_spine_gate_trace
            if expander_continuation_spine_gate_trace.get(
                "targeted_retrieval_dispatch_authorized"
            )
            else evaluator_continuation_spine_gate_trace
        )
        ordinary_continuation_candidate_trace = (
            mark_ordinary_continuation_candidate_spine_authorized(
                ordinary_continuation_candidate_trace,
                used=True,
            )
        )
        targeted_retrieval_lifecycle_trace = {
            **targeted_retrieval_lifecycle_trace,
            "targeted_retrieval_candidate_used": True,
        }
        evidence_integration_checkpoint_trace[ORDINARY_CONTINUATION_TRACE_KEY] = dict(
            ordinary_continuation_candidate_trace
        )
        evidence_integration_checkpoint_trace[
            "expander_continuation_spine_gate_trace"
        ] = dict(expander_continuation_spine_gate_trace)
        evidence_integration_checkpoint_trace[
            "evaluator_continuation_spine_gate_trace"
        ] = dict(evaluator_continuation_spine_gate_trace)
        evidence_integration_checkpoint_trace[
            "scout_continuation_spine_gate_trace"
        ] = dict(scout_continuation_spine_gate_trace)
        evidence_integration_checkpoint_trace[
            "authorized_continuation_spine_gate_trace"
        ] = dict(authorized_gate_trace)
    if retrieval_batch_dispatch_trace.get("considered"):
        evidence_integration_checkpoint_trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY] = (
            dict(retrieval_batch_dispatch_trace)
        )

    source_class_recovery_result = run_source_class_recovery_dispatch(
        source_class_recovery_context_from_scope(
            locals(),
            controller_recovery_decision=build_controller_recovery_decision(
                active_source_class_recovery_lifecycle
            ),
            error_type=PipelineError,
        )
    )
    source_class_recovery_execution = (
        source_class_recovery_result.source_class_recovery_execution
    )
    total_urls_fetched += source_class_recovery_result.total_urls_delta
    total_chunks_embedded += source_class_recovery_result.total_chunks_delta

    conflict_resolution_execution: dict[str, int | bool]
    if authorized_spine_action == RESOLVE_CONFLICT:
        if conflict_resolution_decision_for_checkpoint_gate is None:
            raise PipelineError("conflict_resolution gate approved without decision")
        conflict_resolution_execution = execute_conflict_resolution_from_scope(
            locals(),
            decision=conflict_resolution_decision_for_checkpoint_gate,
            error_type=PipelineError,
        )
    else:
        conflict_resolution_execution = {
            "attempted": False,
            "result_count": 0,
            "new_url_count": 0,
        }
    if conflict_resolution_execution["attempted"]:
        total_urls_fetched += int(conflict_resolution_execution["new_url_count"])
        total_chunks_embedded += int(conflict_resolution_execution["result_count"])

    max_domain_chunks = 4 if complexity == "high" else (3 if complexity == "medium" else 2)

    def _final_evidence_bundle_inputs() -> FinalEvidenceBundleInputs:
        return FinalEvidenceBundleInputs(
            all_passages=all_passages,
            top_chunks=top_chunks,
            max_domain_chunks=max_domain_chunks,
            filter_top_evidence=deps.filter_top_evidence,
            is_plausible_domain=deps.is_plausible_domain,
            current_date=current_date,
            query=query,
            active_source_class_recovery_lifecycle=active_source_class_recovery_lifecycle,
            recovered_evidence_visibility=apply_controller_recovered_evidence_visibility,
        )

    final_evidence_bundle = build_final_evidence_bundle(_final_evidence_bundle_inputs())
    final_top_evidence = final_evidence_bundle.final_top_evidence
    unique_source_urls = final_evidence_bundle.unique_source_urls
    ordered_sources = final_evidence_bundle.ordered_sources

    status.step("--- **Final Synthesis & Reporting** ---")
    evidence_block = final_evidence_bundle.evidence_block
    cached_prefix = final_evidence_bundle.cached_prefix
    author_notes = ""

    # --- LINKUP (high tier) + QUANTITATIVE COMPONENT ---
    # When both apply, Linkup runs in parallel with the fast pre-flight gate; the economist
    # runs only after the gate passes (sequential), so we never spend smart-model time without evidence.
    _economist_allowed = (not corpus_weak) and (
        corpus_state != CorpusState.ESTIMATE_FROM_PRIORS.value
    )
    need_linkup = complexity == "high" and bool(os.getenv("LINKUP_API_KEY")) and not corpus_weak
    need_economist = (
        report_type in QUANT_REPORT_TYPES
        and bool(os.getenv("OPENAI_API_KEY"))
        and _economist_allowed
    )

    def _record_economist_preflight_result(
        allowed: bool,
        missing_entities: list[str],
        block_reason: str | None,
    ) -> None:
        nonlocal economist_preflight_allowed
        nonlocal economist_preflight_block_reason
        nonlocal economist_preflight_missing_entities
        economist_preflight_allowed = bool(allowed)
        economist_preflight_missing_entities = [
            str(entity).strip()[:200]
            for entity in (missing_entities or [])
            if str(entity).strip()
        ]
        economist_preflight_block_reason = (
            str(block_reason).strip() if (not allowed and block_reason) else None
        )

    def _economist_preflight_gate() -> tuple[bool, list[str], str | None]:
        """Return (allow_economist, missing_entities, block_reason). Fail-open when the gate cannot evaluate."""
        _pf_prompt = build_economist_preflight_prompt(
            entities_list=entities_list,
            primary_entity=primary_entity,
            core_topic=core_topic,
            final_top_evidence=final_top_evidence,
        )
        if _pf_prompt is None:
            return (True, [], None)
        _pf_entities = _pf_prompt.entities
        _pf_system = _pf_prompt.system_prompt
        _pf_user = _pf_prompt.user_prompt
        _measure_context_stage(
            "economist_preflight",
            prompt=_pf_user,
            system_prompt=_pf_system,
            evidence_passages=final_top_evidence,
        )
        try:
            _pf_raw = ask_model(
                _pf_user,
                _pf_system,
                provider=fast_provider,
                model=fast_model,
                effort="low",
                base_url=local_url,
                api_key=or_api_key,
                use_reasoning=False,
                require_json=True,
                max_tokens=100,
                temperature=0,
            )
            _pf_clean = deps.clean_json_response(_pf_raw)
            _pf_obj = json.loads(_pf_clean)
            if not isinstance(_pf_obj, dict):
                raise ValueError("pre-flight JSON root must be an object")
            _missing_ent = thin_quant_preflight_missing_entities(_pf_obj, _pf_entities)
            if _missing_ent:
                return (
                    False,
                    _missing_ent,
                    "missing_numerical_anchor_for_entities",
                )
            return (True, [], None)
        except Exception as e:
            run_log.warning("Economist pre-flight gate failed (fail-open): %s", e)
            return (True, [], None)

    def _run_economist_step() -> str | None:
        deps.run_economist_step(
            core_topic=core_topic,
            all_passages=final_top_evidence,
            current_date=current_date,
            ask_model=ask_model,
            clean_json_response=deps.clean_json_response,
            default_system=DEFAULT_SYSTEM,
            provider=smart_provider,
            model=smart_model,
            base_url=local_url,
            api_key=or_api_key,
            scout_context=scout_context,
            complexity=complexity,
            corpus_weak=corpus_weak,
            corpus_state=corpus_state,
            safety_telemetry=economist_safety_telemetry,
            user_query=query,
        )
        return None

    if need_linkup and need_economist:
        status.step("Fetching Linkup context; running quantitative evidence gate (parallel)...")
        _par_t0 = time.monotonic()

        def _linkup_job() -> str:
            return fetch_linkup_precision_block(
                core_topic,
                intent,
                complexity,
                include_domains,
                exclude_domains,
                provider_diagnostics=provider_diagnostics,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_l = pool.submit(_linkup_job)
            fut_pf = pool.submit(_economist_preflight_gate)
            linkup_block = fut_l.result() or ""
            (
                allow_economist,
                _preflight_missing,
                _preflight_block_reason,
            ) = fut_pf.result()
        _record_economist_preflight_result(
            allow_economist,
            _preflight_missing,
            _preflight_block_reason,
        )

        _gate_linkup_seconds = max(0.0, time.monotonic() - _par_t0)
        run_log.info("[STEP] linkup+economist pre-flight gate in %.2fs", _gate_linkup_seconds)
        if linkup_block:
            status.step("Integrated Linkup precision context.")
        cached_prefix += linkup_block
        if allow_economist:
            status.step("\u2699\ufe0f Building quantitative model...")
            _eco_t0 = time.monotonic()
            _run_economist_step()
            economist_ran = True
            economist_seconds = max(0.0, time.monotonic() - _eco_t0)
            run_log.info("[STEP] economist completed in %.2fs", economist_seconds)
        else:
            economist_ran = False
            run_log.info(
                "[STEP] economist skipped (pre-flight gate: missing evidence for %s)", _preflight_missing
            )
            status.step("Quantitative model skipped \u2014 insufficient cited numerical evidence in retrieval.")
            author_notes += (
                "\n\nNOTE FOR AUTHOR \u2014 QUANTITATIVE FRAMEWORK NOT RUN:\n"
                "The economist step was skipped because retrieved evidence did not contain explicit "
                "cited numerical metrics for: "
                + ", ".join(_preflight_missing)
                + ". Answer from available evidence; do not present a quantitative framework or MODEL-DERIVED tables.\n"
            )
    elif need_linkup:
        status.step("Fetching Linkup deep precision block...")
        linkup_block = fetch_linkup_precision_block(
            core_topic,
            intent,
            complexity,
            include_domains,
            exclude_domains,
            provider_diagnostics=provider_diagnostics,
        )
        if linkup_block:
            status.step("Integrated Linkup precision context.")
        cached_prefix += linkup_block
    elif need_economist:
        (
            allow_economist,
            _preflight_missing,
            _preflight_block_reason,
        ) = _economist_preflight_gate()
        _record_economist_preflight_result(
            allow_economist,
            _preflight_missing,
            _preflight_block_reason,
        )
        if not allow_economist:
            economist_ran = False
            run_log.info(
                "[STEP] economist skipped (pre-flight gate: missing evidence for %s)", _preflight_missing
            )
            status.step("Quantitative model skipped \u2014 insufficient cited numerical evidence in retrieval.")
            author_notes += (
                "\n\nNOTE FOR AUTHOR \u2014 QUANTITATIVE FRAMEWORK NOT RUN:\n"
                "The economist step was skipped because retrieved evidence did not contain explicit "
                "cited numerical metrics for: "
                + ", ".join(_preflight_missing)
                + ". Answer from available evidence; do not present a quantitative framework or MODEL-DERIVED tables.\n"
            )
        else:
            status.step("\u2699\ufe0f Building quantitative model...")
            _eco_t0 = time.monotonic()
            _run_economist_step()
            economist_ran = True
            economist_seconds = max(0.0, time.monotonic() - _eco_t0)
            run_log.info("[STEP] economist completed in %.2fs", economist_seconds)

    if (
        not economist_safety_telemetry.get("economist_schema_version")
        and not economist_safety_telemetry.get("quantitative_packet_present")
        and not economist_safety_telemetry.get("high_stakes_quant_detected")
    ):
        economist_safety_telemetry.update(
            validate_high_stakes_quantitative_query_shadow(query=query)
        )

    quant_retrieval_sufficiency_telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query=query,
        report_type=report_type,
        final_top_evidence=final_top_evidence,
        economist_safety_telemetry=economist_safety_telemetry,
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        nutrition_lookup_entity=(primary_entity or None),
        router_entities=entities_list,
    )
    economist_pre_analyst_skip_candidate_telemetry = (
        _economist_pre_analyst_skip_candidate_telemetry(
            report_type=report_type,
            complexity=complexity,
            mode=strategy,
            economist_safety_telemetry=economist_safety_telemetry,
            quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
        )
    )
    estimate_from_priors_requested = (
        corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value
    )
    missing_target_metric_fallback_directive = (
        _format_missing_target_metric_fallback_directive(
            query=query,
            report_type=report_type,
            quant_report_types=QUANT_REPORT_TYPES,
            economist_safety_telemetry=economist_safety_telemetry,
            quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
            estimate_from_priors=estimate_from_priors_requested,
        )
    )
    missing_target_metric_directive_emitted = bool(
        missing_target_metric_fallback_directive
    )
    if missing_target_metric_fallback_directive:
        author_notes += missing_target_metric_fallback_directive

    def _evidence_slice_for_analyst() -> list[Any]:
        return evidence_slice_for_analyst(
            final_top_evidence=final_top_evidence,
            economist_ran=economist_ran,
            report_type=report_type,
            quant_report_types=QUANT_REPORT_TYPES,
        )

    def _build_analyst_cached_prefix() -> str:
        assembly = build_analyst_cached_prefix_from_scope({
            "final_top_evidence": final_top_evidence,
            "economist_ran": economist_ran,
            "report_type": report_type,
            "QUANT_REPORT_TYPES": QUANT_REPORT_TYPES,
            "current_date": current_date,
            "query": query,
            "linkup_block": linkup_block,
            "economist_safety_telemetry": economist_safety_telemetry,
            "_format_analyst_quant_packet_section": _format_analyst_quant_packet_section,
            "missing_target_metric_fallback_directive": missing_target_metric_fallback_directive,
        })
        run_log.info("Analyst corpus capped to %d chunks", len(assembly.evidence_slice))
        analyst_quant_packet_handoff_telemetry.update(assembly.quant_packet_handoff)
        return assembly.prefix

    analyst_cached_prefix = _build_analyst_cached_prefix()

    _record_analyst_model_call = analyst_runtime_stage.build_analyst_model_call_recorder(
        analyst_quant_packet_handoff_telemetry
    )

    # --- ANALYST ---
    # AG-90F extracted seam preserves the former local operation order:
    # post_economist_gate = _post_economist_analyst_gate
    # economist_handoff_state = build_economist_handoff_state
    # economist_handoff = execute_economist_handoff
    # pre_analyst_gate_contract = build_analyst_gate_descriptor
    # analyst_skipped = bool(pre_analyst_gate_handoff
    # build_unsupported_retrieval_prompt_fragments
    analyst_runtime_deps = analyst_runtime_stage.AnalystRuntimeDeps(
        ask_model=ask_model,
        measure_context_stage=_measure_context_stage,
        record_analyst_model_call=_record_analyst_model_call,
        evidence_slice_for_analyst=_evidence_slice_for_analyst,
        pre_analyst_retrieval_gate=_pre_analyst_retrieval_gate,
        post_economist_analyst_gate=_post_economist_analyst_gate,
    )
    analyst_runtime_outcome = (
        analyst_runtime_stage.execute_analyst_runtime_stage_from_scope(
            locals(), deps=analyst_runtime_deps
        )
    )
    (
        analysis,
        author_notes,
        analyst_seconds,
        pre_analyst_gate,
        post_economist_gate,
        _pre_gate_failure_card_show,
        _pre_gate_failure_card_reason,
        pre_analyst_gate_contract,
        pre_analyst_gate_handoff,
        analyst_skipped,
        analyst_skip_reason,
        post_retrieval_fast_path_used,
        pre_analyst_gate_signals,
        estimate_from_priors_blocked_by_pre_analyst_gate,
        economist_ran,
        economist_preflight_allowed,
        economist_preflight_block_reason,
        economist_preflight_missing_entities,
        analyst_skipped_after_economist,
        analyst_after_economist_skip_reason,
        economist_output_used_as_analysis,
    ) = analyst_runtime_outcome.orchestrator_values()

    # --- SYNTHESIZER EVALUATOR & SCRUTINEER ---
    # Keep runtime_prompt_assembly/retrieval_dispatch_runtime call shapes inside the extracted helper.
    legacy_review_deps = legacy_review_runtime_stage.LegacyReviewRuntimeDeps(
        ask_model=ask_model,
        clean_json_response=deps.clean_json_response,
        measure_context_stage=_measure_context_stage,
        record_analyst_model_call=_record_analyst_model_call,
        build_final_evidence_bundle=build_final_evidence_bundle,
        final_evidence_bundle_inputs=_final_evidence_bundle_inputs,
        build_analyst_cached_prefix=_build_analyst_cached_prefix,
        evidence_slice_for_analyst=_evidence_slice_for_analyst,
        select_providers=select_providers,
        choose_supplemental_search_depth=choose_supplemental_search_depth,
    )
    legacy_review_outcome = legacy_review_runtime_stage.execute_legacy_review_runtime_stage_from_scope(
        locals(), deps=legacy_review_deps, default_system=DEFAULT_SYSTEM
    )
    analysis, author_notes, first_synth_sufficient, synth_was_insufficient, synth_deficiency, supplemental_ran, delta_urls_supplemental, synth_evaluator_seconds, analyst_seconds, scrutineer_ran, scrutineer_seconds, scrutineer_flags, scrutineer_high_count, scrutineer_remediation_queries, scrutineer_remediation_dispatch_authorized, scrutineer_remediation_dispatch_posture, scrutineer_remediation_provider_role, scrutineer_remediation_providers, scrutineer_remediation_linkup_depth_override, scrutineer_remediation_evidence, scrutineer_remediation_resynthesis_triggered, scrutineer_pass_flags_directly_to_author, final_top_evidence, unique_source_urls = legacy_review_outcome.orchestrator_values()
    if legacy_review_outcome.ordered_sources is not None:
        ordered_sources = legacy_review_outcome.ordered_sources
    if legacy_review_outcome.evidence_block is not None:
        evidence_block = legacy_review_outcome.evidence_block
    if legacy_review_outcome.cached_prefix is not None:
        cached_prefix = legacy_review_outcome.cached_prefix

    # ------------------------------------------------------------------
    # Build author prompt and generate final report
    # ------------------------------------------------------------------
    _efp_author = corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value

    image_context = build_image_context(image_mode=image_mode, collected_images=collected_images, corpus_weak=corpus_weak, estimate_from_priors_author=_efp_author)

    recency_notes, _recency_stale = build_recency_author_notes(
        final_top_evidence,
        query=query,
        intent=intent,
        query_type=query_type or "",
        current_date=current_date,
    )
    if _recency_stale:
        waste_flags.append("stale_corpus_for_news_query")

    _u_val = utilization_rate_val
    _relevance_low = (
        not corpus_weak
        and not _efp_author
        and _u_val is not None
        and float(_u_val) < VERBOSITY_GATE_UTILIZATION_THRESHOLD
        and complexity in ("medium", "high")
    )
    _thin_body = (corpus_weak and not _efp_author) or _relevance_low

    precision_count = 4 if _thin_body else (10 if complexity == "high" else 8)
    final_evidence_bundle = attach_author_evidence(
        final_evidence_bundle,
        precision_count=precision_count,
    )
    author_evidence = final_evidence_bundle.author_evidence
    author_evidence_block = final_evidence_bundle.author_evidence_block

    author_prompt_assembly = build_author_prompt_from_scope(locals())
    author_prompt = author_prompt_assembly.prompt
    author_notes = author_prompt_assembly.author_notes

    status.update("Writing final report...")

    _author_system, author_system_prompt_key = select_author_system_prompt(
        default_system=DEFAULT_SYSTEM,
        corpus_weak=corpus_weak,
        estimate_from_priors_author=_efp_author,
    )
    _author_effort = (
        analyst_effort
        if ((not corpus_weak or _efp_author) and not _relevance_low)
        else "low"
    )
    final_answer_author_runtime = assemble_final_answer_author_runtime_from_scope(
        locals()
    )
    final_answer_packet = final_answer_author_runtime.packet
    author_prompt = final_answer_author_runtime.author_prompt
    author_system_prompt_key = final_answer_author_runtime.author_system_prompt_key
    _author_effort = final_answer_author_runtime.author_effort

    # AG-90G: build_analyst_author_handoff_state / execute_analyst_author_handoff
    # packaging moved to the bounded post-Analyst handoff helper;
    # runtime_prompt_assembly Author/final-answer prompt construction stays local.
    post_analyst_handoff = (
        post_analyst_handoff_packaging.build_post_analyst_handoff_packaging_from_scope(
            locals(), evidence_slice_for_analyst=_evidence_slice_for_analyst
        )
    )
    (
        analyst_author_handoff_state,
        analyst_author_handoff,
        author_system_prompt_key,
        _author_effort,
        author_quant_source_telemetry,
        economist_skip_eligibility_shadow_telemetry,
        economist_skip_shadow_alignment,
    ) = post_analyst_handoff.orchestrator_values()
    _measure_context_stage(
        "author",
        prompt=author_prompt,
        system_prompt=_author_system,
        stable_prefix=_author_system,
        evidence_passages=author_evidence,
    )

    if strategy in ("Fast", "Balanced"):
        _author_provider = fast_provider
        _author_model = fast_model
    else:
        _author_provider = smart_provider
        _author_model = smart_model

    _synth_t0 = time.monotonic()
    quantitative_guard_stream_buffered = (
        config.author_stream_display is not None
        and is_two_item_calorie_gram_comparison_candidate(query)
    )
    # Streaming author: accumulate full text for execution_trace / logs / RunOutcome.report.
    _stream_out = ask_model(
        author_prompt, _author_system,
        provider=_author_provider, model=_author_model, effort=_author_effort,
        base_url=local_url, api_key=or_api_key, stream=True, use_reasoning=False,
    )
    if isinstance(_stream_out, str):
        report = str(_stream_out or "")
    else:
        _author_chunks: list[str] = []

        def _author_stream_iter():
            for ch in _stream_out:
                _author_chunks.append(ch)
                yield ch

        if config.author_stream_display is not None and not quantitative_guard_stream_buffered:
            config.author_stream_display(_author_stream_iter())
        else:
            for _ in _author_stream_iter():
                pass
        report = "".join(_author_chunks)
    report = str(report or "")
    author_seconds = max(0.0, time.monotonic() - _synth_t0)
    synthesis_seconds = author_seconds  # noqa: F841
    quantitative_consistency_telemetry = (
        build_two_item_normalized_consistency_diagnostic(
            query=query,
            final_answer=report,
            quantitative_packet=economist_safety_telemetry.get("quantitative_packet"),
            calculation_results=economist_safety_telemetry.get("calculation_results"),
        )
    )
    report, quantitative_consistency_guard_telemetry = (
        apply_quantitative_consistency_guard(
            query=query,
            final_answer=report,
            diagnostic=quantitative_consistency_telemetry,
            quantitative_packet=economist_safety_telemetry.get("quantitative_packet"),
            calculation_results=economist_safety_telemetry.get("calculation_results"),
        )
    )
    final_answer_source_telemetry = _final_answer_source_citation_telemetry(
        report,
        economist_safety_telemetry,
    )

    useful_content, useful_content_reason = evaluate_useful_content(
        report,
        query_type=query_type,
        report_type=report_type,
    )
    latency_seconds = round(time.time() - pipeline_start_time, 2)
    _timing_payload = _pipeline_timing_payload(
        latency_seconds=latency_seconds,
        pre_retrieval_seconds=pre_retrieval_seconds,
        recon_seconds=recon_seconds,
        iter_timing_seconds=iter_timing_seconds,
        scout_llm_seconds=scout_llm_seconds,
        expander_llm_seconds=expander_llm_seconds,
        gap_evaluator_llm_seconds=gap_evaluator_llm_seconds,
        economist_seconds=economist_seconds,
        analyst_seconds=analyst_seconds,
        synth_evaluator_seconds=synth_evaluator_seconds,
        scrutineer_seconds=scrutineer_seconds,
        author_seconds=author_seconds,
    )
    scrutineer_flag_count = len(scrutineer_flags)
    cost_snapshot = accumulator.snapshot()

    _tc = max(0, int(total_chunks_embedded))
    _u = float(utilization_rate_val or 0.0)
    chunks_with_entity = min(_tc, max(0, int(round(_u * max(1, _tc))))) if _tc else 0
    first_pass_providers = list(providers_by_iteration[0]) if providers_by_iteration else []
    _uc = bool(useful_content)

    fc_show = failure_card_should_show(
        corpus_state=corpus_state,
        retrieval_retry_used=retrieval_retry_used,
        empty_entity=empty_entity_flag,
        scrutineer_high_count=scrutineer_high_count,
        useful_content=_uc,
    )
    fc_reason = failure_card_reason(
        corpus_state=corpus_state,
        retrieval_retry_used=retrieval_retry_used,
        empty_entity=empty_entity_flag,
        scrutineer_high_count=scrutineer_high_count,
        useful_content=_uc,
        chunks_with_entity=chunks_with_entity,
        total_chunks_embedded=_tc,
    )
    failure_card_payload: dict[str, Any] = {
        "show": fc_show,
        "reason": fc_reason,
        "corpus_state": corpus_state,
        "empty_entity": empty_entity_flag,
        "first_pass_providers": first_pass_providers,
        "retrieval_retry_used": retrieval_retry_used,
        "scrutineer_high_count": scrutineer_high_count,
        "useful_content": useful_content,
    }

    synth_sufficient_first_pass_raw = bool(first_synth_sufficient)
    response_displayable, evidence_sufficient, answer_class = classify_answer_outcome(
        report,
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        useful_content=bool(useful_content),
        synth_was_insufficient=bool(synth_was_insufficient),
        empty_entity=bool(empty_entity_flag),
    )
    weak_failure_gate_contract_state = build_weak_failure_gate_state(
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        corpus_state_forced=corpus_state_forced_flag,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        weak_corpus_recovery_queries=weak_corpus_recovery_queries,
        weak_corpus_recovery_decision=weak_corpus_recovery_decision,
        weak_corpus_recovery_reason=weak_corpus_recovery_reason,
        weak_corpus_recovery_blockers=weak_corpus_recovery_blockers,
        useful_content=useful_content,
        useful_content_reason=useful_content_reason,
        response_displayable=response_displayable,
        evidence_sufficient=evidence_sufficient,
        answer_class=answer_class,
        failure_card_payload=failure_card_payload,
        analyst_gate=pre_analyst_gate_contract,
        run_id=run_id,
        iteration=iterations_run,
        retrieval_loop_state=retrieval_loop_contract_state,
        router_query_preparation_state=router_query_preparation_contract,
        answer_outcome_ref={
            "response_displayable": response_displayable,
            "evidence_sufficient": evidence_sufficient,
            "answer_class": answer_class,
        },
    )
    weak_failure_gate_handoff = execute_weak_failure_gate_handoff(
        weak_failure_gate_contract_state
    )
    failure_card_payload = weak_failure_gate_handoff.failure_card_payload
    useful_content = weak_failure_gate_handoff.useful_content
    useful_content_reason = weak_failure_gate_handoff.useful_content_reason
    response_displayable = weak_failure_gate_handoff.response_displayable
    evidence_sufficient = weak_failure_gate_handoff.evidence_sufficient
    answer_class = weak_failure_gate_handoff.answer_class
    synth_sufficient_first_pass = bool(synth_sufficient_first_pass_raw and evidence_sufficient)

    run_history_out = list(prior_run_history)
    if prior_snapshot_for_history:
        run_history_out = run_history_out + [prior_snapshot_for_history]

    status.done()
    final_source_telemetry_inputs = build_final_source_telemetry_inputs(
        final_top_evidence=final_top_evidence,
        unique_source_urls=unique_source_urls,
        ordered_sources=ordered_sources,
        seen_urls=list(seen_urls),
        collected_images=list(collected_images),
        final_answer_source_telemetry=final_answer_source_telemetry,
    )

    record_run_metadata_snapshot(
        _run_controller_mirror,
        session_id=session_id,
        run_id=run_id,
        query=query,
        mode=strategy,
        current_date=current_date,
        core_topic=core_topic,
        intent=intent,
        complexity=complexity,
    )
    _run_controller_mirror.state.route_fields["router_query_preparation_contract"] = (
        router_query_preparation_contract.to_controller_state()
    )
    if retrieval_loop_contract_state is not None:
        _run_controller_mirror.state.route_fields[RETRIEVAL_LOOP_TRACE_KEY] = (
            retrieval_loop_contract_state.to_controller_state()
        )
    _run_controller_mirror.state.trace_fields.update(
        router_query_preparation_contract.to_trace_fragment()
    )
    _run_controller_mirror.state.trace_fields.update(query_authority.to_trace_fragment())
    if retrieval_loop_contract_state is not None:
        _run_controller_mirror.state.trace_fields.update(
            retrieval_loop_contract_state.to_trace_fragment()
        )
    record_final_evidence_snapshot(
        _run_controller_mirror,
        **final_source_telemetry_inputs.final_evidence_snapshot_payload,
    )

    pipeline_config_payload = build_pipeline_config(
        intent=intent,
        complexity=complexity,
        search_depth=search_depth,
        mode=strategy,
    )
    new_session: dict[str, Any] = build_session_payload(
        session_id=session_id,
        run_id=run_id,
        session_title=session_title,
        current_date=current_date,
        query=query,
        core_topic=core_topic,
        report=report,
        final_top_evidence=final_top_evidence,
        seen_urls=list(seen_urls),
        collected_images=list(collected_images),
        mode=strategy,
        pipeline_config=pipeline_config_payload,
        run_history_out=run_history_out,
        failure_card_payload=failure_card_payload,
    )

    queries_by_iteration = query_authority.queries_by_iteration()
    queries_per_iter = {str(k): v for k, v in (queries_by_iteration or {}).items()}
    disambiguation_queries_per_iter = {
        str(k): v for k, v in (disambiguation_queries_by_iteration or {}).items()
    }
    record_stage_ledger_query_provider_facts(
        _run_controller_mirror,
        queries_by_iteration=queries_by_iteration,
        disambiguation_queries_by_iteration=disambiguation_queries_by_iteration,
        providers_by_iteration=providers_by_iteration,
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )
    if not weak_corpus_recovery_used and weak_corpus_recovery_skip_reason is None:
        weak_corpus_recovery_skip_reason = "not_weak_corpus"
    ts_utc = datetime.now(timezone.utc).isoformat()
    _source_tier_exec = source_tier_telemetry(all_passages)
    _source_domain_exec = source_domain_telemetry(
        all_passages,
        domain_anchor=primary_entity or core_topic,
    )
    source_class_recovery_telemetry = build_source_class_recovery_recommendation(
        query=query,
        current_date=current_date,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet_telemetry,
        source_tier_counts=_source_tier_exec["source_tier_counts"],
        source_domain_counts=_source_domain_exec["source_domain_counts"],
        top_source_domains=_source_domain_exec["top_source_domains"],
        official_evidence_found=_source_tier_exec["official_evidence_found"],
    )
    source_class_evidence_bundle_observability_telemetry = (
        build_source_class_observability_telemetry(
            query=query,
            intent=intent,
            report_type=report_type,
            query_type=query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            anchor_packet=anchor_packet_telemetry,
            final_top_evidence=final_top_evidence,
            final_answer_source_ids=None,
        )
    )
    source_class_observability_telemetry = (
        build_source_class_observability_telemetry(
            query=query,
            intent=intent,
            report_type=report_type,
            query_type=query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            anchor_packet=anchor_packet_telemetry,
            final_top_evidence=final_top_evidence,
            final_answer_source_ids=final_answer_source_telemetry.get(
                "final_answer_source_ids_used"
            ),
        )
    )
    try:
        _bridge_runtime_trace = {
            "query_preview": (query or "")[:200],
            "intent": intent,
            "query_type": query_type,
            "report_type": report_type,
            **source_class_recovery_telemetry,
            **source_class_observability_telemetry,
        }
        _bridge_result = apply_official_source_obligation_bridge(
            recommendation=source_class_recovery_telemetry,
            runtime_trace=_bridge_runtime_trace,
            existing_blockers=active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_blockers"
            )
            or (),
        )
        source_class_recovery_telemetry = _bridge_result.recommendation
        official_source_obligation_bridge_trace = _bridge_result.trace
    except Exception as exc:
        logger.warning(
            "Non-fatal official-source obligation bridge omitted: %s",
            exc,
        )
    source_class_projection_handoff = build_source_class_recovery_projection_handoff(
        all_passages=all_passages,
        final_top_evidence=final_top_evidence,
        final_source_class_counts=source_class_observability_telemetry.get(
            "source_class_strong_satisfaction_counts"
        ),
    )
    if source_class_projection_handoff.recovery_source_quality_diagnostics:
        active_source_class_recovery_lifecycle.update(
            source_class_projection_handoff.recovery_source_quality_diagnostics
        )
    record_source_class_recovery_recommendation(
        _run_controller_mirror,
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        source_class_evidence_signals={
            "source_tier_counts": _source_tier_exec["source_tier_counts"],
            "source_domain_counts": _source_domain_exec["source_domain_counts"],
            "top_source_domains": _source_domain_exec["top_source_domains"],
            "unique_source_domain_count": _source_domain_exec[
                "unique_source_domain_count"
            ],
            "on_domain_source_count": _source_domain_exec["on_domain_source_count"],
            "off_domain_source_count": _source_domain_exec[
                "off_domain_source_count"
            ],
            "official_evidence_found": _source_tier_exec["official_evidence_found"],
            "community_signal_found": _source_tier_exec["community_signal_found"],
            "low_trust_sources_found": _source_tier_exec["low_trust_sources_found"],
            "pollution_detected": _source_tier_exec["pollution_detected"],
        },
    )
    runtime_source_class_recovery_telemetry = source_class_recovery_telemetry
    runtime_active_source_class_recovery_lifecycle = (
        active_source_class_recovery_lifecycle
    )
    if active_source_class_recovery_lifecycle.get("recovered_visibility_used") is True:
        runtime_source_class_recovery_telemetry = {
            **source_class_recovery_telemetry,
            **source_class_observability_telemetry,
        }
        reserved_missing_class = active_source_class_recovery_lifecycle.get(
            "recovered_visibility_missing_source_class"
        )
        if reserved_missing_class:
            runtime_active_source_class_recovery_lifecycle = {
                **active_source_class_recovery_lifecycle,
                "active_source_class_recovery_missing_classes": [
                    source_class
                    for source_class in active_source_class_recovery_lifecycle.get(
                        "active_source_class_recovery_missing_classes"
                    )
                    or []
                    if source_class != reserved_missing_class
                ],
            }
    # Post-Author citation assembly is delegated; helper calls assemble_final_answer_citation_runtime_from_scope(...).
    post_author_trace_packaging = build_post_author_trace_packaging_from_scope(
        locals(),
        analyst_evidence=_evidence_slice_for_analyst(),
        logger=logger,
        answer_contract_handoff_builder=build_runtime_answer_contract_handoff,
    )
    for trace_field_fragment in post_author_trace_packaging.trace_field_fragments:
        _run_controller_mirror.state.trace_fields.update(trace_field_fragment)

    post_author_output_packaging = build_post_author_output_packaging_from_scope(
        locals(),
        trace_packaging=post_author_trace_packaging,
        code_version_metadata_builder=current_code_version_metadata,
    )
    execution_trace = post_author_output_packaging.execution_trace
    output_word_count = post_author_output_packaging.output_word_count
    execution_log_entry = post_author_output_packaging.execution_log_entry
    persistence_side_effect_result = execute_persistence_side_effects(
        execution_log_path=execution_log_path,
        execution_log_entry=execution_log_entry,
        run_id=run_id,
        session_id=session_id,
        latency_seconds=latency_seconds,
        strategy=strategy,
        execution_trace=execution_trace,
        run_log=run_log,
        policy_journal_path=policy_journal_path,
        policy_applied=policy_applied,
        default_utilization_threshold=DEFAULT_UTILIZATION_THRESHOLD,
        ts_utc=ts_utc,
        query=query,
        kb_context=build_kb_review_persistence_context(
            runtime_values=locals(),
            clean_json_response=deps.clean_json_response,
            kb_review_agent=kb_review_agent,
        ),
        db_enabled=DB_ENABLED,
    )
    kb_instrumentation = persistence_side_effect_result.kb_instrumentation
    kb_warning = persistence_side_effect_result.kb_warning

    return build_run_outcome_from_scope(locals())
