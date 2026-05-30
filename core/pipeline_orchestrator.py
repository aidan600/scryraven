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
    authoritative_source_action_trace_fragment,
    build_authoritative_source_action_orchestrator_handoff,
)
from core.conflict_resolution_controller import (
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
    build_conflict_resolution_controller_input,
    build_conflict_resolution_lifecycle,
    conflict_resolution_lifecycle_defaults,
)
from core.conflict_resolution_executor import execute_conflict_resolution_action
from core.conflict_state_producer import (
    ConflictState,
    ConflictStateProducerInput,
    build_conflict_state,
    project_conflict_state_to_runtime_facts,
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
    ControllerActionAuthority,
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
from core.entity_extraction import fallback_entities_from_query, normalize_entities_list
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
    EvidenceIntegrationBudgetSnapshot,
    EvidenceIntegrationSnapshot,
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
from core.final_evidence_bundle_builder import (
    FinalEvidenceBundleInputs,
    attach_author_evidence,
    build_final_evidence_bundle,
    build_final_source_telemetry_inputs,
)
from core.nutrition_author_notes import _format_nutrition_partial_evidence_author_note
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)
from core.ordinary_continuation_candidate import (
    ORDINARY_CONTINUATION_TRACE_KEY,
    build_ordinary_continuation_candidate,
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
    build_execution_log_entry,
    build_final_output_metadata,
    build_pipeline_config,
    build_run_outcome,
    build_session_payload,
)
from core.persistence_side_effects import (
    KbReviewPersistenceContext,
    execute_persistence_side_effects,
)
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
from core.prompts import ROUTER_RETRY_USER_APPEND, SCOUT_REGISTRY
from core.protocols import StatusWriter
from core.provider_diagnostics import (
    build_provider_attempt_diagnostic,
    provider_diagnostics_payload,
    supported_diagnostic_kwargs,
)
from core.quantitative_consistency import (
    apply_quantitative_consistency_guard,
    build_two_item_normalized_consistency_diagnostic,
    is_two_item_calorie_gram_comparison_candidate,
)
from core.recovered_evidence_visibility import (
    apply_controller_recovered_evidence_visibility,
)
from core.retrieval_batch_dispatch import (
    RETRIEVAL_BATCH_DISPATCH_TRACE_KEY,
    RetrievalBatchDispatchFacts,
    build_retrieval_batch_dispatch_decision,
    retrieval_batch_dispatch_defaults,
)
from core.retrieval_quality import (
    DEFAULT_UTILIZATION_THRESHOLD,
    VERBOSITY_GATE_UTILIZATION_THRESHOLD,
    build_disambiguation_queries,
    extract_recon_context,
    finalize_retrieval_queries,
    format_quoted_anchor,
    jaccard_similarity,
    official_bias_phrase,
    should_merge_recency_queries,
    should_retry_retrieval,
    utilization_entity_anchor,
    utilization_rate,
    wants_official_source_bias,
)
from core.retrieval_stop_controller import (
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)
from core.review_flags import (
    recent_recurring_kb_hints,
)
from core.routing import is_quantitative_query, merge_search_provider_overrides, select_providers
from core.run_config import RunConfig, RunDeps, RunOutcome
from core.run_controller import RunController
from core.run_logging import (
    current_code_version_metadata,
    log_run_failed,
    log_run_started,
)
from core.runtime_trace_export_attachment import (
    attach_runtime_trace_export_compatibility_payloads,
)
from core.search_providers import brave_reconnaissance
from core.source_class_recovery import (
    build_source_class_observability_telemetry,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_controller_mirror import (
    record_source_class_recovery_recommendation,
)
from core.source_class_recovery_diagnostics import (
    SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY,
)
from core.source_class_recovery_lifecycle import (
    source_class_recovery_lifecycle_defaults,
)
from core.source_class_recovery_projection_handoff import (
    build_source_class_recovery_projection_handoff,
)
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)
from core.source_classifier import source_domain_telemetry, source_tier_telemetry
from core.source_recency import build_recency_author_notes
from core.stage_ledger_mirror import record_stage_ledger_query_provider_facts
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

logger = logging.getLogger(__name__)

DB_ENABLED = True
_RETRIEVAL_STOP_SHADOW_MODE = "shadow_only"
_RETRIEVAL_STOP_ACTIVE_MODE = "active_stop_no_queries"
_RETRIEVAL_STOP_ACTIVE_BUDGET_EXHAUSTED_MODE = "active_stop_budget_exhausted"
_RETRIEVAL_STOP_ACTIVE_FINAL_ANSWER_POSTURE = "answer with caveats"
_RETRIEVAL_STOP_ACTIVE_AG28_CANDIDATE = (
    "ag28:stop_insufficient_with_caveat:terminal_no_query_or_budget_exhausted"
)
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


def _official_or_canonical_source_class_count(
    source_class_counts: dict[str, Any] | None,
) -> int | None:
    if not isinstance(source_class_counts, dict):
        return None
    counts: list[int] = []
    for key in (
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    ):
        if key not in source_class_counts:
            continue
        try:
            counts.append(max(0, int(source_class_counts.get(key) or 0)))
        except (TypeError, ValueError):
            continue
    return max(counts) if counts else None


def _retrieval_stop_shadow_defaults() -> dict[str, Any]:
    return {
        "retrieval_stop_shadow_available": False,
        "retrieval_stop_shadow_decision": None,
        "retrieval_stop_shadow_reason": None,
        "retrieval_stop_shadow_blockers": [],
        "retrieval_stop_shadow_next_query_count": 0,
        "retrieval_stop_shadow_alignment": None,
        "retrieval_stop_shadow_stage": None,
        "retrieval_stop_shadow_mode": _RETRIEVAL_STOP_SHADOW_MODE,
    }


def _retrieval_stop_active_defaults() -> dict[str, Any]:
    return {
        "retrieval_stop_active_available": False,
        "retrieval_stop_active_action_name": None,
        "retrieval_stop_active_authority": None,
        "retrieval_stop_active_decision": None,
        "retrieval_stop_active_reason": None,
        "retrieval_stop_active_terminal_branch_reason": None,
        "retrieval_stop_active_blockers": [],
        "retrieval_stop_active_next_query_count": 0,
        "retrieval_stop_active_approved_query_count": 0,
        "retrieval_stop_active_stage": None,
        "retrieval_stop_active_mode": _RETRIEVAL_STOP_ACTIVE_MODE,
        "retrieval_stop_active_final_answer_posture": None,
        "retrieval_stop_active_ag28_candidate": None,
        "retrieval_stop_active_shadow_alignment": None,
        "retrieval_stop_active_fallback_reason": None,
    }


def _compact_shadow_strings(
    values: list[str] | tuple[str, ...],
    *,
    max_items: int = 4,
    max_len: int = 80,
) -> list[str]:
    out: list[str] = []
    for value in values[:max_items]:
        text = " ".join(str(value or "").split())[:max_len]
        if text:
            out.append(text)
    return out


def _build_retrieval_stop_shadow_telemetry(
    *,
    actual_decision: str,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    blockers: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    telemetry = _retrieval_stop_shadow_defaults()
    telemetry["retrieval_stop_shadow_stage"] = str(stage or "")[:80] or None
    try:
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
        decision = decide_retrieval_stop(snapshot)
        decision_value = decision.decision.value
        telemetry.update(
            {
                "retrieval_stop_shadow_available": True,
                "retrieval_stop_shadow_decision": decision_value,
                "retrieval_stop_shadow_reason": decision.reason,
                "retrieval_stop_shadow_blockers": _compact_shadow_strings(
                    decision.blockers
                ),
                "retrieval_stop_shadow_next_query_count": len(
                    decision.next_queries
                ),
                "retrieval_stop_shadow_alignment": (
                    "aligned" if decision_value == actual_decision else "mismatch"
                ),
            }
        )
    except Exception:
        logger.warning("Non-fatal retrieval-stop shadow telemetry omitted.")
        telemetry.update(
            {
                "retrieval_stop_shadow_reason": "shadow_unavailable",
                "retrieval_stop_shadow_blockers": ["shadow_exception"],
                "retrieval_stop_shadow_alignment": "unavailable",
            }
        )
    return telemetry


def _decide_retrieval_stop_for_active(
    snapshot: Any,
) -> Any:
    return decide_retrieval_stop(snapshot)


def _active_decision_value(decision: Any) -> str | None:
    value = getattr(getattr(decision, "decision", None), "value", None)
    if value is None:
        value = getattr(decision, "decision", None)
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())[:80]
    return text or None


def _active_decision_reason(decision: Any) -> str | None:
    value = getattr(decision, "reason", None)
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())[:80]
    return text or None


def _active_decision_next_query_count(decision: Any) -> int:
    value = getattr(decision, "next_queries", ())
    if not isinstance(value, (list, tuple)):
        return 0
    return len(value)


def _retrieval_stop_active_shadow_alignment(
    *,
    active_decision: str | None,
    shadow_telemetry: dict[str, Any],
) -> str:
    if not active_decision:
        return "not_evaluated"
    if shadow_telemetry.get("retrieval_stop_shadow_available") is not True:
        return "shadow_unavailable"
    shadow_decision = shadow_telemetry.get("retrieval_stop_shadow_decision")
    return "aligned" if shadow_decision == active_decision else "mismatch"


def _build_retrieval_stop_active_telemetry(
    *,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    expected_decision: str,
    active_mode: str,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    shadow_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    telemetry = _retrieval_stop_active_defaults()
    telemetry["retrieval_stop_active_stage"] = str(stage or "")[:80] or None
    telemetry["retrieval_stop_active_mode"] = str(active_mode or "")[:80] or None
    shadow = shadow_telemetry if isinstance(shadow_telemetry, dict) else {}
    try:
        snapshot = build_retrieval_stop_controller_input(
            evaluator_sufficient=evaluator_sufficient,
            iteration=iteration,
            max_iterations=max_iterations,
            prior_queries=prior_queries,
            next_queries=next_queries,
            query_source=query_source,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            weak_corpus_recovery_completed=weak_corpus_recovery_completed,
        )
        decision = _decide_retrieval_stop_for_active(snapshot)
        decision_value = _active_decision_value(decision)
        telemetry.update(
            {
                "retrieval_stop_active_decision": decision_value,
                "retrieval_stop_active_reason": _active_decision_reason(decision),
                "retrieval_stop_active_blockers": _compact_shadow_strings(
                    getattr(decision, "blockers", ())
                ),
                "retrieval_stop_active_next_query_count": (
                    _active_decision_next_query_count(decision)
                ),
                "retrieval_stop_active_shadow_alignment": (
                    _retrieval_stop_active_shadow_alignment(
                        active_decision=decision_value,
                        shadow_telemetry=shadow,
                    )
                ),
            }
        )
        if decision_value == expected_decision:
            telemetry.update(
                {
                    "retrieval_stop_active_available": True,
                    "retrieval_stop_active_action_name": (
                        STOP_INSUFFICIENT_WITH_CAVEAT
                    ),
                    "retrieval_stop_active_authority": (
                        ControllerActionAuthority.ACTIVE.value
                    ),
                    "retrieval_stop_active_terminal_branch_reason": (
                        _active_decision_reason(decision)
                    ),
                    "retrieval_stop_active_final_answer_posture": (
                        _RETRIEVAL_STOP_ACTIVE_FINAL_ANSWER_POSTURE
                    ),
                    "retrieval_stop_active_approved_query_count": 0,
                    "retrieval_stop_active_ag28_candidate": (
                        _RETRIEVAL_STOP_ACTIVE_AG28_CANDIDATE
                    ),
                }
            )
        else:
            telemetry["retrieval_stop_active_fallback_reason"] = (
                "unexpected_controller_decision"
            )
    except Exception:
        logger.warning("Non-fatal active retrieval-stop handoff fell back.")
        telemetry.update(
            {
                "retrieval_stop_active_reason": "active_controller_unavailable",
                "retrieval_stop_active_blockers": ["active_controller_exception"],
                "retrieval_stop_active_shadow_alignment": "not_evaluated",
                "retrieval_stop_active_fallback_reason": "controller_exception",
            }
        )
    return telemetry


def _build_retrieval_stop_active_stop_no_queries_telemetry(
    *,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    shadow_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_retrieval_stop_active_telemetry(
        stage=stage,
        evaluator_sufficient=evaluator_sufficient,
        iteration=iteration,
        max_iterations=max_iterations,
        expected_decision="stop_no_queries",
        active_mode=_RETRIEVAL_STOP_ACTIVE_MODE,
        prior_queries=prior_queries,
        next_queries=next_queries,
        query_source=query_source,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_completed=weak_corpus_recovery_completed,
        shadow_telemetry=shadow_telemetry,
    )


def _build_retrieval_stop_active_stop_budget_exhausted_telemetry(
    *,
    stage: str,
    evaluator_sufficient: bool | None,
    iteration: int,
    max_iterations: int,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries: list[str] | tuple[str, ...] = (),
    query_source: str | None = None,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_completed: bool = False,
    shadow_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_retrieval_stop_active_telemetry(
        stage=stage,
        evaluator_sufficient=evaluator_sufficient,
        iteration=iteration,
        max_iterations=max_iterations,
        expected_decision="stop_budget_exhausted",
        active_mode=_RETRIEVAL_STOP_ACTIVE_BUDGET_EXHAUSTED_MODE,
        prior_queries=prior_queries,
        next_queries=next_queries,
        query_source=query_source,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_completed=weak_corpus_recovery_completed,
        shadow_telemetry=shadow_telemetry,
    )


def _social_signal_requested_from_contract(contract: Any) -> bool:
    relevance = getattr(getattr(contract, "social_signal_relevance", None), "value", None)
    return str(relevance or "").casefold() == "central"


def _scrutineer_allowed_by_contract(contract: Any) -> bool:
    relevance = getattr(
        getattr(contract, "scrutineer_relevance", None),
        "value",
        None,
    )
    return str(relevance or "").casefold() in {"central", "relevant_optional"}


def _scrutineer_allowed_by_mode(mode: str | None) -> bool:
    return str(mode or "").strip().casefold() in {"deep", "scrutineer", "review"}


def _weak_corpus_lifecycle_facts(
    decision: WeakCorpusRecoveryDecision | None,
) -> dict[str, Any] | None:
    if decision is None:
        return None
    return {
        "approved": bool(decision.approved),
        "reason": decision.reason,
        "blockers": list(decision.blockers),
    }


def _conflict_resolution_lifecycle_facts(
    *,
    decision: ConflictResolutionDecision | None,
    lifecycle_trace: dict[str, Any],
) -> dict[str, Any]:
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
    """Attach post-retrieval answer-contract facts to the passive seam."""
    existing = dict(existing_candidate_trace or {})
    ordinary_queries = _compact_runtime_strings(
        existing.get("ordinary_next_queries")
    )
    if not ordinary_queries:
        ordinary_queries = _compact_runtime_strings(
            getattr(evidence_state, "next_queries", ())
        )
    prior_queries = _compact_runtime_strings(existing.get("prior_queries"))
    if not prior_queries:
        prior_queries = _compact_runtime_strings(
            getattr(evidence_state, "prior_queries", ())
        )
    resolving_queries = _compact_runtime_strings(conflict_resolving_queries)
    if not resolving_queries:
        resolving_queries = _compact_runtime_strings(
            existing.get("conflict_resolving_queries")
        )
    if not resolving_queries:
        resolving_queries = _compact_runtime_strings(
            getattr(evidence_state, "resolving_queries", ())
        )
    source_path = existing.get("source_path") or existing.get("query_provenance")
    blockers = [
        blocker
        for blocker in (existing.get("blockers") or [])
        if blocker
        not in {
            "not_evaluated",
            "no_ordinary_next_queries",
            "source_path_not_ordinary_continuation",
        }
    ]
    candidate = build_ordinary_continuation_candidate(
        source_path=str(source_path) if source_path else None,
        ordinary_next_queries=ordinary_queries,
        query_provenance=str(source_path) if source_path else None,
        prior_queries=prior_queries,
        prior_query_count=existing.get("prior_query_count"),
        conflict_resolving_queries=resolving_queries,
        current_iteration=(
            int(existing.get("current_iteration") or current_iteration or 0)
        ),
        max_iterations=(
            int(existing.get("max_iterations") or max_iterations or 0)
        ),
        next_queries_redundant=(
            "redundant_with_prior_queries" in set(existing.get("blockers") or [])
        ),
        budget_exhausted=(
            "blocked_by_iteration_budget" in set(existing.get("blockers") or [])
        ),
        considered=bool(existing.get("considered") or ordinary_queries),
        extra_blockers=blockers,
    )
    return candidate.to_dict()


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


def _build_evidence_integration_snapshot_from_runtime(
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
    source_missing = tuple(evidence_state.source_classes_missing) + tuple(
        source_class_recovery_recommendation.get("missing_expected_source_classes")
        or ()
    ) + tuple(
        active_source_class_recovery_lifecycle.get(
            "active_source_class_recovery_missing_classes"
        )
        or ()
    )
    source_queries = active_source_class_recovery_lifecycle.get(
        "active_source_class_recovery_queries"
    ) or source_class_recovery_recommendation.get(
        "source_class_recovery_queries"
    )
    missing_information = tuple(answer_contract_result.state.missing_information)
    if (
        retrieval_stop_shadow_telemetry.get("retrieval_stop_shadow_decision")
        == "continue_retrieval"
        and retrieval_stop_shadow_telemetry.get(
            "retrieval_stop_shadow_next_query_count"
        )
    ):
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
            (weak_corpus_recovery_skip_reason or corpus_state)
            if corpus_weak
            else None
        ),
        weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
        weak_corpus_recovery_available=bool(
            corpus_weak
            and not weak_corpus_recovery_used
            and not weak_corpus_recovery_attempted
            and weak_corpus_recovery_skip_reason in {None, "not_weak_corpus"}
        ),
        source_class_recovery_recommended=bool(
            source_class_recovery_recommendation.get(
                "source_class_recovery_recommended"
            )
        ),
        source_class_recovery_eligible=bool(
            active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_eligible"
            )
        ),
        source_class_recovery_missing_classes=source_missing,
        source_class_recovery_queries_available=bool(source_queries),
        source_class_recovery_blockers=tuple(
            active_source_class_recovery_lifecycle.get(
                "active_source_class_recovery_blockers"
            )
            or ()
        ),
        conflicts_present=bool(evidence_state.conflicts_present),
        conflict_notes=evidence_state.conflict_notes,
        conflict_resolution_available=bool(evidence_state.resolving_queries),
        next_queries_available=bool(
            retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_next_query_count"
            )
        ),
        next_query_redundant=(
            retrieval_stop_shadow_telemetry.get("retrieval_stop_shadow_decision")
            == "stop_redundant_queries"
        ),
        prior_query_count=len(evidence_state.prior_queries),
        next_query_count=int(
            retrieval_stop_shadow_telemetry.get(
                "retrieval_stop_shadow_next_query_count"
            )
            or 0
        ),
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
            source_class_slot_available=(
                max_iterations > 1
                or bool(
                    active_source_class_recovery_lifecycle.get(
                        "active_source_class_recovery_eligible"
                    )
                )
            ),
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


def _build_runtime_conflict_state_projection(
    *,
    query: str,
    core_topic: str | None,
    primary_entity: str | None,
    current_date: str | None,
    final_top_evidence: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    source_tier_counts: dict[str, Any],
    source_domain_telemetry: dict[str, Any],
    source_class_observability: dict[str, Any],
    ordinary_next_queries: list[str] | tuple[str, ...] = (),
) -> tuple[ConflictState, dict[str, Any]]:
    conflict_state = build_conflict_state(
        ConflictStateProducerInput(
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            current_date=current_date,
            final_top_evidence=final_top_evidence,
            source_tier_counts=source_tier_counts,
            source_domain_telemetry=source_domain_telemetry,
            source_class_observability=source_class_observability,
            ordinary_next_queries=ordinary_next_queries,
        )
    )
    return conflict_state, project_conflict_state_to_runtime_facts(conflict_state)


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


GENERIC_NEWS_DOMAINS = frozenset(
    {
        "abcnews.go.com",
        "apnews.com",
        "axios.com",
        "bbc.com",
        "bbc.co.uk",
        "cbsnews.com",
        "cnn.com",
        "forbes.com",
        "foxnews.com",
        "msnbc.com",
        "nbcnews.com",
        "newsweek.com",
        "nytimes.com",
        "reuters.com",
        "theguardian.com",
        "usatoday.com",
        "washingtonpost.com",
        "yahoo.com",
    }
)


def _query_expects_official_evidence(query: str, report_type: str, query_type: str) -> bool:
    text = f"{query} {report_type} {query_type}".casefold()
    primary_source_request = bool(
        re.search(
            r"\bprimary[-\s]+"
            r"(?:sources?|documents?|evidence|records?|materials?)\b",
            text,
        )
    )
    official_source_request = bool(
        re.search(
            r"\b(?:company|corporate|issuer|reported\s+company)[-\s]+"
            r"(?:filings?|materials?|reports?|records?)\b",
            text,
        )
        or re.search(r"\beligibility[-\s]+requirements?\b", text)
    )
    if primary_source_request or official_source_request:
        return True

    return bool(
        re.search(
            r"\b("
            r"official|patch\s*notes?|release\s*notes?|changelog|pricing|prices?|"
            r"policy|policies|terms|rate\s*card|fees?|tariffs?|developer|dev\s*notes?|"
            r"filings?|regulatory|sec|announcement|roadmap"
            r")\b",
            text,
        )
    )


def _query_expects_community_evidence(query: str, report_type: str, query_type: str) -> bool:
    text = f"{query} {report_type} {query_type}".casefold()
    return bool(
        re.search(
            r"\b("
            r"community|forum|forums|reddit|users?|players?|reviews?|discussion|"
            r"github|gitlab|stackoverflow|stack\s*overflow|issues?|pull\s*requests?|discord"
            r")\b",
            text,
        )
    )


def _nutrition_macro_per_unit_lookup(query: str) -> bool:
    return bool(detect_nutrition_lookup_telemetry(query)["nutrition_lookup_detected"])


def _pre_analyst_retrieval_gate(
    *,
    query: str,
    report_type: str,
    query_type: str,
    corpus_state: str,
    corpus_weak: bool,
    failure_card_show: bool,
    utilization_rate_val: float | None,
    utilization_threshold: float,
    source_tier_counts: dict[str, int],
    source_domain_counts: dict[str, int],
    top_source_domains: list[dict[str, Any]],
    on_domain_source_count: int,
    official_evidence_found: bool,
    community_signal_found: bool,
) -> dict[str, Any]:
    """Decide whether post-retrieval evidence is too weak for Analyst spend."""
    signals: list[str] = []
    total_sources = max(0, sum(int(v or 0) for v in source_domain_counts.values()))
    total_tiered = max(0, sum(int(v or 0) for v in source_tier_counts.values()))
    unknown_count = int(source_tier_counts.get("unknown", 0) or 0)
    unknown_ratio = (unknown_count / max(1, total_tiered)) if total_tiered else 0.0
    generic_news_count = sum(
        int(count or 0)
        for domain, count in source_domain_counts.items()
        if str(domain).lower() in GENERIC_NEWS_DOMAINS
    )
    generic_news_ratio = (generic_news_count / max(1, total_sources)) if total_sources else 0.0
    top_domain = ""
    top_count = 0
    if top_source_domains:
        top_domain = str(top_source_domains[0].get("domain") or "").lower()
        top_count = int(top_source_domains[0].get("count") or 0)
    top_generic_dominates = (
        top_domain in GENERIC_NEWS_DOMAINS
        and total_sources > 0
        and (top_count / max(1, total_sources)) >= 0.5
    )
    generic_news_dominated = generic_news_ratio >= 0.6 or top_generic_dominates
    mostly_unknown_sources = total_tiered > 0 and unknown_ratio >= 0.8
    all_unknown_sources = total_tiered > 0 and unknown_count == total_tiered
    expected_official = _query_expects_official_evidence(query, report_type, query_type)
    expected_community = _query_expects_community_evidence(query, report_type, query_type)
    low_utilization = (
        utilization_rate_val is not None
        and float(utilization_rate_val) <= max(float(utilization_threshold) + 0.10, 0.35)
    )
    no_domain_relevant_source = total_sources > 0 and int(on_domain_source_count or 0) <= 0

    if generic_news_dominated:
        signals.append("generic_news_dominated")
    if mostly_unknown_sources:
        signals.append("mostly_unknown_sources")
    if all_unknown_sources:
        signals.append("all_unknown_sources")
    if expected_official and not official_evidence_found:
        signals.append("missing_expected_official_evidence")
    if expected_community and not community_signal_found:
        signals.append("missing_expected_community_signal")
    if low_utilization:
        signals.append("low_utilization_near_threshold")
    if no_domain_relevant_source:
        signals.append("no_domain_relevant_source")

    reason: str | None = None
    if corpus_state == CorpusState.OFF_TOPIC.value:
        reason = "corpus_off_topic"
    elif corpus_weak:
        reason = "corpus_weak"
    elif failure_card_show:
        reason = "failure_card_shown"
    elif (
        "missing_expected_official_evidence" in signals
        and mostly_unknown_sources
        and (generic_news_dominated or no_domain_relevant_source or low_utilization)
    ):
        reason = "missing_expected_official_evidence"
    elif mostly_unknown_sources and low_utilization and (generic_news_dominated or no_domain_relevant_source):
        reason = "low_utilization_unknown_sources"
    elif generic_news_dominated and no_domain_relevant_source and len(signals) >= 3:
        reason = "unsupported_off_domain_retrieval"

    return {
        "analyst_skipped": bool(reason),
        "analyst_skip_reason": reason,
        "post_retrieval_fast_path_used": bool(reason),
        "pre_analyst_gate_signals": signals,
    }


def _post_economist_analyst_gate(
    *,
    query: str,
    report_type: str,
    complexity: str,
    economist_ran: bool,
    economist_block: str,
    corpus_state: str,
    corpus_weak: bool,
    failure_card_show: bool,
    pre_analyst_gate_skipped: bool,
    economist_schema_valid: bool = False,
) -> dict[str, Any]:
    """Telemetry-only reason labels for the disabled post-Economist skip path.

    Policy: Economist output must not skip Analyst and must not become Author-facing
    analysis directly. The returned skip/use flags therefore remain hard-disabled;
    only the reason string is retained for historical diagnostics and calibration.
    """
    normalized_report_type = str(report_type or "").strip().lower()
    normalized_complexity = str(complexity or "").strip().lower()
    block = str(economist_block or "").strip()
    if normalized_report_type not in {"quantitative_comparison", "benchmark"}:
        reason = "report_type_not_bounded_quant"
    elif economist_schema_valid:
        reason = "economist_shadow_mode_no_framework"
    elif not economist_ran or not block:
        reason = "economist_empty_or_failed"
    elif corpus_state == CorpusState.OFF_TOPIC.value:
        reason = "corpus_off_topic"
    elif corpus_weak:
        reason = "corpus_weak"
    elif failure_card_show:
        reason = "failure_card_shown"
    elif pre_analyst_gate_skipped:
        reason = "pre_analyst_gate_skipped"
    elif normalized_complexity == "high":
        reason = "deep_mode_requires_scrutineer_path"
    elif _query_requires_clinical_trial_comparative_caution(query):
        reason = "clinical_randomized_trial_comparative_effect_guardrail"
    else:
        reason = "economist_shadow_mode_no_framework"

    return {
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": reason,
        "economist_output_used_as_analysis": False,
    }


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


def _author_quant_source_telemetry_defaults() -> dict[str, Any]:
    return {
        "author_quant_content_source": "none",
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
        "author_quant_handoff_gate_reason": "no_quantitative_author_handoff_detected",
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


def _economist_skip_eligibility_shadow_defaults() -> dict[str, Any]:
    return {
        "economist_skip_eligible_shadow": False,
        "economist_skip_eligibility_reasons": [],
        "economist_skip_eligibility_blockers": [],
        "economist_skip_eligibility_gate_reason": "not_evaluated",
        "economist_skip_eligibility_shadow_mode": True,
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


def _economist_skip_shadow_alignment(
    *,
    pre_analyst_candidate_telemetry: dict[str, Any] | None,
    posthoc_skip_eligibility_telemetry: dict[str, Any] | None,
) -> str:
    """Compare shadow candidate signals without changing runtime behavior."""
    if not isinstance(pre_analyst_candidate_telemetry, dict) or not isinstance(
        posthoc_skip_eligibility_telemetry, dict
    ):
        return "not_evaluated"
    pre_candidate = bool(
        pre_analyst_candidate_telemetry.get(
            "economist_pre_analyst_skip_candidate_shadow"
        )
    )
    posthoc_eligible = bool(
        posthoc_skip_eligibility_telemetry.get("economist_skip_eligible_shadow")
    )
    if pre_candidate and posthoc_eligible:
        return "candidate_and_posthoc_eligible"
    if pre_candidate:
        return "candidate_only"
    if posthoc_eligible:
        return "posthoc_only"
    return "neither"


def _economist_skip_eligibility_shadow_telemetry(
    *,
    report_type: str,
    complexity: str,
    mode: str,
    economist_safety_telemetry: dict[str, Any],
    analyst_quant_packet_handoff_telemetry: dict[str, Any],
    author_quant_source_telemetry: dict[str, Any],
    analyst_skipped_after_economist: bool,
    economist_output_used_as_analysis: bool,
    pre_analyst_gate_skipped: bool | None = None,
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnostic-only posthoc skip eligibility telemetry.

    The computed ``economist_skip_eligible_shadow`` value is for readiness
    analysis and log summarization only. It must not enable Analyst skip or pass
    raw Economist/quantitative packet content to Author.
    """
    telemetry = _economist_skip_eligibility_shadow_defaults()
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
    if packet_valid and packet_direct_use and not packet_requires_analyst:
        reasons.append("valid_direct_use_packet")
    else:
        if not packet_valid:
            blockers.append("packet_invalid_or_missing")
        if not packet_direct_use:
            blockers.append("packet_not_direct_use_eligible")
        if packet_requires_analyst:
            blockers.append("packet_requires_analyst")

    if bool(economist_safety_telemetry.get("high_stakes_quant_detected")):
        blockers.append("high_stakes_requires_analyst")
    else:
        reasons.append("non_high_stakes")

    if bool(economist_safety_telemetry.get("economist_code_execution_requested")):
        blockers.append("economist_code_execution_requested")

    analyst_reviewed_packet = bool(
        analyst_quant_packet_handoff_telemetry.get("analyst_quant_packet_reviewed_by_model")
    )
    analyst_model_called = bool(
        analyst_quant_packet_handoff_telemetry.get("analyst_model_called")
    )
    if analyst_reviewed_packet and analyst_model_called:
        reasons.append("analyst_reviewed_packet")
    else:
        if not analyst_reviewed_packet:
            blockers.append("packet_not_reviewed_by_analyst")
        if not analyst_model_called:
            blockers.append("analyst_model_not_called")

    if author_quant_source_telemetry.get("author_quant_content_source") == "analyst_reviewed":
        reasons.append("author_received_analyst_reviewed_synthesis")
    else:
        blockers.append("author_not_analyst_reviewed")

    author_received_raw_packet = bool(
        author_quant_source_telemetry.get("author_received_raw_quant_packet")
    )
    author_received_framework = bool(
        author_quant_source_telemetry.get("author_received_economist_framework")
    )
    author_received_analyst_marker = bool(
        author_quant_source_telemetry.get("author_received_analyst_packet_marker")
    )
    if not (
        author_received_raw_packet
        or author_received_framework
        or author_received_analyst_marker
    ):
        reasons.append("no_author_marker_leak")
    else:
        if author_received_raw_packet:
            blockers.append("author_raw_packet_marker_detected")
        if author_received_framework:
            blockers.append("author_framework_marker_detected")
        if author_received_analyst_marker:
            blockers.append("author_analyst_packet_marker_detected")

    if economist_output_used_as_analysis:
        blockers.append("economist_output_used_as_analysis")
    else:
        reasons.append("economist_not_used_as_analysis")

    if analyst_skipped_after_economist:
        blockers.append("analyst_already_skipped")
    else:
        reasons.append("analyst_not_skipped")

    if pre_analyst_gate_skipped is True:
        blockers.append("pre_analyst_gate_skipped")

    eligible = not blockers
    if eligible:
        gate_reason = "eligible_shadow_only"
    elif "high_stakes_requires_analyst" in blockers:
        gate_reason = "blocked_by_high_stakes"
    elif "packet_invalid_or_missing" in blockers:
        gate_reason = "blocked_by_invalid_packet"
    elif (
        "packet_not_reviewed_by_analyst" in blockers
        or "analyst_model_not_called" in blockers
    ):
        gate_reason = "blocked_by_missing_analyst_review"
    elif (
        "author_raw_packet_marker_detected" in blockers
        or "author_framework_marker_detected" in blockers
        or "author_analyst_packet_marker_detected" in blockers
    ):
        gate_reason = "blocked_by_author_marker_leak"
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
    elif "pre_analyst_gate_skipped" in blockers:
        gate_reason = "blocked_by_pre_analyst_gate"
    else:
        gate_reason = "blocked_by_multiple_reasons"

    telemetry.update(
        {
            "economist_skip_eligible_shadow": eligible,
            "economist_skip_eligibility_reasons": reasons,
            "economist_skip_eligibility_blockers": blockers,
            "economist_skip_eligibility_gate_reason": gate_reason,
            "economist_skip_eligibility_shadow_mode": True,
        }
    )
    return telemetry


def _scan_author_quant_source_telemetry(
    author_prompt: str,
    *,
    analyst_quant_packet_reviewed_by_model: bool,
    analysis: str | None,
) -> dict[str, Any]:
    telemetry = _author_quant_source_telemetry_defaults()
    prompt = str(author_prompt or "")
    has_raw_packet = (
        "quantitative_packet" in prompt
        or "quantitative_packet_v1" in prompt
    )
    has_analyst_packet_marker = "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in prompt
    has_economist_framework = _author_prompt_contains_raw_economist_framework(prompt)
    telemetry.update(
        {
            "author_received_raw_quant_packet": has_raw_packet,
            "author_received_analyst_packet_marker": has_analyst_packet_marker,
            "author_received_economist_framework": has_economist_framework,
        }
    )

    if has_raw_packet:
        telemetry["author_quant_content_source"] = "raw_quant_packet_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_raw_quant_packet"
    elif has_analyst_packet_marker:
        telemetry["author_quant_content_source"] = "analyst_packet_marker_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_analyst_packet_marker"
    elif has_economist_framework:
        telemetry["author_quant_content_source"] = "raw_economist_block_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_economist_framework"
    elif analyst_quant_packet_reviewed_by_model and str(analysis or "").strip():
        telemetry["author_quant_content_source"] = "analyst_reviewed"
        telemetry["author_quant_handoff_gate_reason"] = (
            "author_received_analyst_reviewed_quantitative_synthesis"
        )

    return telemetry


def _author_prompt_contains_raw_economist_framework(prompt: str) -> bool:
    text = str(prompt or "")
    heading_pattern = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:LEGACY\s+)?QUANTITATIVE FRAMEWORK\b[^\n]*"
    )
    payload_markers = (
        "MODEL-DERIVED",
        "Normalization approach",
        "Computed results",
        "computed value",
        "Numeric rendering",
        "central",
        "range",
    )
    for match in heading_pattern.finditer(text):
        heading = match.group(0)
        normalized_heading = heading.casefold()
        if re.search(r"\bnot\s+(?:run|shown)\b", normalized_heading):
            continue
        window = text[match.start() : match.start() + 1600]
        if any(marker.casefold() in window.casefold() for marker in payload_markers):
            return True
    return False


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


def _query_requires_clinical_trial_comparative_caution(query: str) -> bool:
    text = str(query or "").casefold()
    clinical_context = bool(re.search(r"\b(clinical|patients?|treatments?|therap(?:y|ies))\b", text))
    randomized_trial = bool(re.search(r"\b(rct|randomi[sz]ed|randomi[sz]ed controlled trial)\b", text))
    comparative_effect = bool(re.search(r"\b(vs\.?|versus|compare[sd]?|comparative|effect|efficacy)\b", text))
    return clinical_context and randomized_trial and comparative_effect


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

    entities_list: list[str] = []
    router_entity_retry_used = False

    try:
        intent_data = json.loads(router_text)
        intent = intent_data.get("intent", "general").lower()
        report_type = intent_data.get("report_type", "general_research").lower()
        image_mode = intent_data.get("image_mode", "contextual").lower()
        core_topic = intent_data.get("core_topic", query[:100])
        is_academic = intent_data.get("is_academic", False)
        query_type = str(intent_data.get("query_type") or "other").lower().strip() or "other"
        primary_entity = str(intent_data.get("primary_entity") or "").strip()[:200]
        entities_list = normalize_entities_list(intent_data.get("entities"))
        if entities_list:
            primary_entity = entities_list[0][:200]
        elif primary_entity:
            entities_list = [primary_entity]
    except Exception:
        intent, report_type, image_mode, core_topic = "general", "general_research", "contextual", query[:100]
        is_academic = False
        query_type, primary_entity = "other", ""
        entities_list = []

    if not entities_list:
        fb_ent = fallback_entities_from_query(query)
        if fb_ent:
            entities_list = list(fb_ent)
            primary_entity = entities_list[0][:200]

    if not entities_list:
        router_entity_retry_used = True
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
        try:
            intent_data_retry = json.loads(retry_router_text)
            rl = normalize_entities_list(intent_data_retry.get("entities"))
            pe_retry = str(intent_data_retry.get("primary_entity") or "").strip()
            if rl:
                entities_list = rl
                primary_entity = entities_list[0][:200]
            elif pe_retry:
                entities_list = [pe_retry[:200]]
                primary_entity = pe_retry[:200]
        except Exception:
            pass

    router_original_report_type = report_type
    router_original_query_type = query_type
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

    def _finalize_retrieval_queries(
        qs: list[str],
        *,
        max_len: int | None = None,
        include_official_bias: bool = True,
    ) -> list[str]:
        out = finalize_retrieval_queries(
            qs,
            primary_entity=primary_entity,
            entities_list=entities_list,
            core_topic=core_topic,
            user_query=query,
            intent=intent,
            clean=_clean_query,
            include_official_bias=include_official_bias,
        )
        return out[:max_len] if max_len is not None else out

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

    queries = _finalize_retrieval_queries(queries, include_official_bias=True)
    current_queries = queries[:max_queries]
    if should_merge_recency_queries(query, intent, query_type) and current_queries is not None:
        y = _extract_year(current_date)
        _anchor = (primary_entity or core_topic or "")[:200]
        if _anchor and max_queries:
            recq = _clean_query(f"{_anchor} {y} news")
            current_queries = ([recq] + [q for q in current_queries if q and q != recq])[: max_queries or 1]
    current_queries = _finalize_retrieval_queries(
        current_queries, max_len=max_queries, include_official_bias=False
    )

    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    collected_images: set[str] = set()
    past_searches: list[str] = []
    iteration = 1
    iterations_run = 0
    is_sufficient = False
    scout_context = None
    suppress_tavily = False
    synth_was_insufficient = False
    supplemental_ran = False
    delta_urls_supplemental = 0
    scrutineer_high_count = 0
    queries_by_iteration: dict[int, list[str]] = {}
    synth_deficiency: str | None = None
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
    available_keys = {
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "linkup": bool(os.getenv("LINKUP_API_KEY")),
        "exa": bool(os.getenv("EXA_API_KEY")),
    }
    current_search_depth_for_recovery = search_depth

    pre_retrieval_seconds = max(0.0, time.monotonic() - _bucket_pre_retrieval_t0)

    force_component_providers: list[str] = []

    def _record_retrieval_stop_shadow_once(
        *,
        actual_decision: str,
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
        retrieval_stop_shadow_telemetry = _build_retrieval_stop_shadow_telemetry(
            actual_decision=actual_decision,
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
        )
        is_continue_retrieval = actual_decision == "continue_retrieval"
        ordinary_continuation_candidate_trace = (
            build_ordinary_continuation_candidate(
                source_path=source_path_from_runtime_source(query_source),
                ordinary_next_queries=next_queries,
                query_provenance=source_path_from_runtime_source(query_source),
                prior_queries=prior_queries,
                conflict_resolving_queries=(),
                current_iteration=iteration,
                max_iterations=max_iterations,
                next_queries_redundant=(
                    (not is_continue_retrieval)
                    and actual_decision == "stop_redundant_queries"
                ),
                budget_exhausted=(
                    (not is_continue_retrieval)
                    and actual_decision == "stop_budget_exhausted"
                ),
                considered=True,
                extra_blockers=blockers,
            ).to_dict()
        )

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
            if jaccard_similarity(queries_by_iteration[1], current_queries) > 0.7:
                _record_retrieval_stop_shadow_once(
                    actual_decision="stop_redundant_queries",
                    stage="pre_search_redundant_queries",
                    evaluator_sufficient=None,
                    prior_queries=queries_by_iteration.get(1, []),
                    next_queries=current_queries,
                    query_source="pre_search",
                )
                waste_flags.append("query_redundancy_skipped")
                break
        queries_by_iteration[iteration] = list(current_queries)
        current_search_depth = choose_retrieval_search_depth(
            complexity,
            search_depth,
            iteration,
        )
        current_search_depth_for_recovery = current_search_depth
        status.step(f"--- **Iteration {iteration}/{max_iterations}** ---")
        status.step(f"Executing Searches: {current_queries} ({current_search_depth} depth)")
        past_searches.extend(current_queries)

        scout_override = list(force_component_providers) if force_component_providers else None
        override_list = merge_search_provider_overrides(
            a5_provider_override, scout_override, available_keys, complexity=complexity
        )
        loop_providers = select_providers(
            query_type, intent, complexity, available_keys,
            report_type=report_type, is_academic=is_academic,
            suppress_tavily=suppress_tavily, override=override_list,
        )
        force_component_providers = []
        status.step(f"Providers this pass: {', '.join(loop_providers)}")
        providers_by_iteration.append(list(loop_providers))
        seen_before = len(seen_urls)
        similarity_prior_queries = (
            queries_by_iteration.get(iteration - 1, []) if iteration > 1 else None
        )
        retrieval_provider_role = (
            "weak_corpus_recovery"
            if weak_corpus_recovery_used and iteration > 1
            else "main_retrieval"
        )
        new_passages = process_search_queries(
            current_queries, intent, complexity, current_search_depth, results_per_query,
            include_domains, exclude_domains, query_embedding, seen_urls, collected_images,
            embed_provider, embed_model, local_url, embed_texts, deps.compute_similarities,
            status_container=status,
            search_providers=loop_providers,
            exa_domain_filter=ACADEMIC_DOMAINS if is_academic else None,
            entity_hint=entity_hint_for_retrieval,
            provider_diagnostics=provider_diagnostics,
            provider_role=retrieval_provider_role,
            iteration=iteration,
            prior_queries_for_similarity=similarity_prior_queries,
            query_similarity_basis=(
                "previous_main_retrieval_iteration" if similarity_prior_queries else None
            ),
        )
        retrieval_pass_records.append(
            {
                "stage": "main_retrieval",
                "iteration": iteration,
                "queries": list(current_queries),
                "providers": list(loop_providers),
                "provider_role": retrieval_provider_role,
                "search_depth": current_search_depth,
                "results_per_query": results_per_query,
            }
        )
        total_urls_fetched += max(0, len(seen_urls) - seen_before)
        total_chunks_embedded += len(new_passages)
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
                rqs = _finalize_retrieval_queries(rqs, include_official_bias=False)
                if rqs:
                    disambiguation_queries_by_iteration[iteration] = list(rqs)
                    status.step("Low match to the main subject; trying disambiguation searches\u2026")
                    retrieval_retry_used = True
                    rseen = len(seen_urls)
                    retry_passages = process_search_queries(
                        rqs, intent, complexity, current_search_depth, results_per_query,
                        include_domains, exclude_domains, query_embedding, seen_urls, collected_images,
                        embed_provider, embed_model, local_url, embed_texts, deps.compute_similarities,
                        status_container=status,
                        search_providers=loop_providers,
                        exa_domain_filter=ACADEMIC_DOMAINS if is_academic else None,
                        entity_hint=entity_hint_for_retrieval,
                        provider_diagnostics=provider_diagnostics,
                        provider_role="disambiguation_retry",
                        iteration=iteration,
                    )
                    retrieval_pass_records.append(
                        {
                            "stage": "disambiguation_retry",
                            "iteration": iteration,
                            "queries": list(rqs),
                            "providers": list(loop_providers),
                            "provider_role": "disambiguation_retry",
                            "search_depth": current_search_depth,
                            "results_per_query": results_per_query,
                        }
                    )
                    total_urls_fetched += max(0, len(seen_urls) - rseen)
                    total_chunks_embedded += len(retry_passages)
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
                recovery_queries = _finalize_retrieval_queries(
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
            _record_retrieval_stop_shadow_once(
                actual_decision="stop_after_recovery",
                stage="weak_corpus_recovery_completed",
                evaluator_sufficient=None,
                prior_queries=queries_by_iteration.get(iteration - 1, []),
                next_queries=[],
                query_source="weak_corpus_recovery",
                weak_corpus_recovery_completed=True,
            )
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
                            finalized_scout_queries = _finalize_retrieval_queries(
                                [
                                    str(q)[:300]
                                    for q in directed[:scout_query_cap]
                                    if str(q).strip()
                                ],
                                max_len=scout_query_cap,
                                include_official_bias=False,
                            )
                            scout_queries = list(finalized_scout_queries)
                            _record_retrieval_stop_shadow_once(
                                actual_decision="continue_retrieval",
                                stage="scout_directed_continuation",
                                evaluator_sufficient=None,
                                prior_queries=queries_by_iteration.get(
                                    iteration, []
                                ),
                                next_queries=finalized_scout_queries,
                                query_source="scout",
                            )
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
                chunk_summaries = "\n".join(
                    f"- [{p['title']}]: {p['text'][:200]}"
                    for p in diverse_top_evidence[:12]
                )
                expander_prompt = (
                    f"User query: {query}\n"
                    f"Core topic: {core_topic}\n\n"
                    f"Initial evidence chunks (summaries):\n{chunk_summaries}\n\n"
                    "Identify the most critical component data that is missing."
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
                    component_queries = _finalize_retrieval_queries(
                        raw_component_queries,
                        max_len=max_queries,
                        include_official_bias=False,
                    )
                    expander_reasoning = expander_data.get("reasoning", "")
                    if component_queries:
                        if len(component_queries) > max_queries:
                            run_log.warning(
                                "Expander returned %d queries despite prompt cap of %d. Truncating.",
                                len(component_queries), max_queries,
                            )
                        component_queries = component_queries[:max_queries]
                        _record_retrieval_stop_shadow_once(
                            actual_decision="continue_retrieval",
                            stage="expander_component_queries",
                            evaluator_sufficient=None,
                            prior_queries=queries_by_iteration.get(iteration, []),
                            next_queries=component_queries,
                            query_source="expander",
                        )
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
                    evaluator_next_queries = _finalize_retrieval_queries(
                        evaluator_next_queries,
                        max_len=2,
                        include_official_bias=False,
                    )
                    if evaluator_sufficient_for_shadow:
                        _record_retrieval_stop_shadow_once(
                            actual_decision="proceed_to_synthesis",
                            stage="evaluator",
                            evaluator_sufficient=True,
                            prior_queries=queries_by_iteration.get(iteration, []),
                            next_queries=evaluator_next_queries,
                            query_source="evaluator",
                        )
                    if (
                        not is_sufficient
                        and iteration == 1
                        and evaluator_next_queries
                        and jaccard_similarity(
                            queries_by_iteration.get(1, []),
                            evaluator_next_queries,
                        ) > 0.7
                    ):
                        _record_retrieval_stop_shadow_once(
                            actual_decision="stop_redundant_queries",
                            stage="evaluator_redundant_queries",
                            evaluator_sufficient=False,
                            prior_queries=queries_by_iteration.get(1, []),
                            next_queries=evaluator_next_queries,
                            query_source="evaluator",
                        )
                        waste_flags.append("query_redundancy_skipped")
                        is_sufficient = True
                    if not evaluator_next_queries:
                        if not evaluator_sufficient_for_shadow:
                            _record_retrieval_stop_shadow_once(
                                actual_decision="stop_no_queries",
                                stage="evaluator_no_queries",
                                evaluator_sufficient=False,
                                prior_queries=queries_by_iteration.get(
                                    iteration, []
                                ),
                                next_queries=[],
                                query_source="evaluator",
                            )
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
                    elif not evaluator_sufficient_for_shadow and not is_sufficient:
                        _record_retrieval_stop_shadow_once(
                            actual_decision="continue_retrieval",
                            stage="evaluator",
                            evaluator_sufficient=False,
                            prior_queries=queries_by_iteration.get(iteration, []),
                            next_queries=evaluator_next_queries,
                            query_source="evaluator",
                        )
                        (
                            evaluator_continuation_authorized,
                            authorized_evaluator_queries,
                        ) = _authorize_evaluator_continuation_before_scheduling(
                            evaluator_queries=evaluator_next_queries,
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
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    run_log.warning("Evaluator JSON parse failed: %s", e)
                    is_sufficient = True

        if iteration >= max_iterations and not is_sufficient:
            _record_retrieval_stop_shadow_once(
                actual_decision="stop_budget_exhausted",
                stage="iteration_budget_exhausted",
                evaluator_sufficient=None,
                prior_queries=queries_by_iteration.get(iteration, []),
                next_queries=[],
                query_source="budget",
            )
            if (
                retrieval_stop_shadow_telemetry.get(
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
        SourceClassRecoveryRunnerContext(
            controller=_run_controller_mirror,
            authorized_spine_action=authorized_spine_action,
            controller_recovery_decision=build_controller_recovery_decision(
                active_source_class_recovery_lifecycle
            ),
            lifecycle_trace=active_source_class_recovery_lifecycle,
            process_search_queries=process_search_queries,
            all_passages=all_passages,
            intent=intent,
            complexity=complexity,
            results_per_query=results_per_query,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            query_embedding=query_embedding,
            seen_urls=seen_urls,
            collected_images=collected_images,
            embed_provider=embed_provider,
            embed_model=embed_model,
            local_url=local_url,
            embed_texts=embed_texts,
            compute_similarities=deps.compute_similarities,
            status_container=status,
            search_providers=(
                list(providers_by_iteration[-1]) if providers_by_iteration else []
            ),
            exa_domain_filter=ACADEMIC_DOMAINS if is_academic else None,
            entity_hint=entity_hint_for_retrieval,
            provider_diagnostics=provider_diagnostics,
            retrieval_pass_records=retrieval_pass_records,
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
        conflict_resolution_execution = execute_conflict_resolution_action(
            conflict_resolution_decision_for_checkpoint_gate,
            lifecycle_trace=active_conflict_resolution_lifecycle,
            process_conflict_resolution_queries=process_search_queries,
            all_passages=all_passages,
            intent=intent,
            complexity=complexity,
            results_per_query=results_per_query,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            query_embedding=query_embedding,
            seen_urls=seen_urls,
            collected_images=collected_images,
            embed_provider=embed_provider,
            embed_model=embed_model,
            local_url=local_url,
            embed_texts=embed_texts,
            compute_similarities=deps.compute_similarities,
            status_container=status,
            search_providers=(
                list(providers_by_iteration[-1]) if providers_by_iteration else []
            ),
            exa_domain_filter=ACADEMIC_DOMAINS if is_academic else None,
            entity_hint=entity_hint_for_retrieval,
            provider_diagnostics=provider_diagnostics,
            retrieval_pass_records=retrieval_pass_records,
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
        _pf_entities = [str(e).strip() for e in (entities_list or []) if str(e).strip()]
        if not _pf_entities and primary_entity:
            _pf_entities = [primary_entity.strip()]
        if not _pf_entities and core_topic:
            _pf_entities = [str(core_topic).strip()[:200]]
        if not _pf_entities:
            return (True, [], None)
        _pf_evidence_corpus = "\n\n".join(
            f"[Source {p.get('source_id', '?')}] {p.get('title', '')}\n"
            f"URL: {p.get('url', '')}\n"
            f"Excerpt: {(p.get('text', '') or '')[:1200]}"
            for p in final_top_evidence
        )
        _pf_system = (
            "You classify evidence only. Respond with one JSON object only, no markdown or prose. "
            "Keys must match the entity names provided by the user. "
            "Decisions must be based only on the evidence text in the user message — never on recalled facts."
        )
        _pf_user = (
            "For each entity listed, decide whether a numerical anchor exists for that entity "
            "in the evidence below.\n\n"
            "A numerical anchor does NOT need to come from a formal dataset or financial filing. "
            "Any specific figure (e.g., '$4,500/hour', '10 cents per seat mile', '207 MWh per day') "
            "appearing explicitly in the evidence text qualifies as true. "
            "Do not recall figures from your training data — only evaluate what is present in the provided evidence.\n\n"
            "Examples of qualifying anchors when explicitly in the text: dollar amounts, cents per unit, percentages, "
            "hourly rates, energy per day, seat-mile costs, and similar concrete numbers tied to the entity or its context.\n"
            "Map to `true` only if such a figure appears verbatim in the excerpts below for that entity (or clear same-sentence "
            "attribution). Map to `false` if no specific number appears in the evidence for that entity, or if you would be "
            "relying on memory rather than the text.\n\n"
            "CRITICAL: You must evaluate cross-entity anchor coverage strictly. Map an entity to `true` ONLY if the evidence contains an independent, explicitly stated numerical anchor that applies SPECIFICALLY to that asset at its declared capacity. Do NOT map an entity to `true` if the only available numbers belong to a different capacity tier or a different model within the same family.\n\n"
            'Answer with a JSON object (one key per entity, boolean values only):\n{"<entity_name>": true/false, ...}\n'
            "Return JSON only, no prose.\n\n"
            "Entities:\n"
            + "\n".join(f"- {e}" for e in _pf_entities)
            + "\n\nEvidence:\n"
            + (_pf_evidence_corpus if _pf_evidence_corpus.strip() else "(none)")
        )
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
        # Bug: report_type is a plain lowercase string (from router JSON + .lower()), but
        # QUANT_REPORT_TYPES may contain Enum members in some invocation paths (e.g. via
        # proplex/__main__.py). A direct `in` check silently returns False on an Enum set,
        # so the 40-chunk cap never triggers. Normalize both sides to str.lower() to fix.
        if not economist_ran and str(report_type).lower() in {
            str(rt).lower() for rt in QUANT_REPORT_TYPES
        }:
            return final_top_evidence[:40]
        return final_top_evidence

    def _build_analyst_cached_prefix() -> str:
        # Rebuild the analyst context prefix from scratch rather than splicing the full
        # cached string by character length (which is fragile against unicode and any
        # whitespace drift in the reconstructed base_head).
        sliced = _evidence_slice_for_analyst()
        run_log.info("Analyst corpus capped to %d chunks", len(sliced))
        slim_block = "\n\n".join(
            f"[Source {p['source_id']}] {p['title']}\nURL: {p['url']}\nExcerpt: {p['text'][:1200]}"
            for p in sliced
        )
        prefix = (
            f"<evidence_block>\n{slim_block}\n</evidence_block>\n\n"
            f"Today is {current_date}.\nUser's Original Prompt: {query}\n"
        )
        if linkup_block:
            prefix += linkup_block
        analyst_quant_packet_section, analyst_quant_packet_handoff = (
            _format_analyst_quant_packet_section(economist_safety_telemetry)
        )
        analyst_quant_packet_handoff_telemetry.update(analyst_quant_packet_handoff)
        if analyst_quant_packet_section:
            prefix += analyst_quant_packet_section
        if missing_target_metric_fallback_directive:
            prefix += missing_target_metric_fallback_directive
        return prefix

    analyst_cached_prefix = _build_analyst_cached_prefix()

    def _record_analyst_model_call(prompt: str) -> None:
        analyst_quant_packet_handoff_telemetry["analyst_model_called"] = True
        if (
            analyst_quant_packet_handoff_telemetry.get("analyst_quant_packet_injected") is True
            and "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in str(prompt or "")
        ):
            analyst_quant_packet_handoff_telemetry[
                "analyst_quant_packet_reviewed_by_model"
            ] = True

    # --- ANALYST ---
    scrutineer_flags: list[dict[str, Any]] = []
    _source_tier_pre_analyst = source_tier_telemetry(all_passages)
    _source_domain_pre_analyst = source_domain_telemetry(
        all_passages,
        domain_anchor=primary_entity or core_topic,
    )
    _pre_gate_total_chunks = max(0, int(total_chunks_embedded))
    _pre_gate_utilization = float(utilization_rate_val or 0.0)
    _pre_gate_chunks_with_entity = (
        min(
            _pre_gate_total_chunks,
            max(0, int(round(_pre_gate_utilization * max(1, _pre_gate_total_chunks)))),
        )
        if _pre_gate_total_chunks
        else 0
    )
    _pre_gate_failure_card_show = failure_card_should_show(
        corpus_state=corpus_state,
        retrieval_retry_used=retrieval_retry_used,
        empty_entity=empty_entity_flag,
        scrutineer_high_count=0,
        useful_content=True,
    )
    _pre_gate_failure_card_reason = failure_card_reason(
        corpus_state=corpus_state,
        retrieval_retry_used=retrieval_retry_used,
        empty_entity=empty_entity_flag,
        scrutineer_high_count=0,
        useful_content=True,
        chunks_with_entity=_pre_gate_chunks_with_entity,
        total_chunks_embedded=_pre_gate_total_chunks,
    )
    pre_analyst_gate = _pre_analyst_retrieval_gate(
        query=query,
        report_type=report_type,
        query_type=query_type,
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        failure_card_show=_pre_gate_failure_card_show,
        utilization_rate_val=utilization_rate_val,
        utilization_threshold=utilization_threshold,
        source_tier_counts=_source_tier_pre_analyst["source_tier_counts"],
        source_domain_counts=_source_domain_pre_analyst["source_domain_counts"],
        top_source_domains=_source_domain_pre_analyst["top_source_domains"],
        on_domain_source_count=_source_domain_pre_analyst["on_domain_source_count"],
        official_evidence_found=_source_tier_pre_analyst["official_evidence_found"],
        community_signal_found=_source_tier_pre_analyst["community_signal_found"],
    )
    analyst_skipped = bool(pre_analyst_gate["analyst_skipped"])
    analyst_skip_reason = pre_analyst_gate["analyst_skip_reason"]
    post_retrieval_fast_path_used = bool(pre_analyst_gate["post_retrieval_fast_path_used"])
    pre_analyst_gate_signals = list(pre_analyst_gate["pre_analyst_gate_signals"])
    post_economist_gate = _post_economist_analyst_gate(
        query=query,
        report_type=report_type,
        complexity=complexity,
        economist_ran=economist_ran,
        economist_block="",
        economist_schema_valid=bool(economist_safety_telemetry.get("economist_schema_valid")),
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        failure_card_show=_pre_gate_failure_card_show,
        pre_analyst_gate_skipped=analyst_skipped,
    )
    analyst_skipped_after_economist = bool(
        post_economist_gate["analyst_skipped_after_economist"]
    )
    analyst_after_economist_skip_reason = post_economist_gate[
        "analyst_after_economist_skip_reason"
    ]
    economist_output_used_as_analysis = bool(
        post_economist_gate["economist_output_used_as_analysis"]
    )
    estimate_from_priors_blocked_by_pre_analyst_gate = bool(
        estimate_from_priors_requested
        and analyst_skipped
        and post_retrieval_fast_path_used
        and analyst_skip_reason == "corpus_weak"
    )
    # These post-Economist fields are telemetry tripwires only. Analyst skip is
    # disabled by policy; Economist output is never used as direct analysis.

    if analyst_skipped:
        status.step("Retrieval quality gate skipped Analyst; sending unsupported-evidence directive to Author.")
        analysis = (
            "UNSUPPORTED_RETRIEVAL_DIRECTIVE:\n"
            f"- Skip reason: {analyst_skip_reason}.\n"
            "- The retrieved corpus does not plausibly support the requested claim.\n"
            "- Do not infer, estimate, or invent missing facts, numeric changes, patch notes, "
            "pricing details, policy details, or release details.\n"
            "- Author should give a concise no-evidence or unsupported-evidence answer using only "
            "the precision evidence and should explicitly name the retrieval limitation."
        )
        _signal_text = ", ".join(pre_analyst_gate_signals) if pre_analyst_gate_signals else "none"
        author_notes += (
            "\n\nNOTE FOR AUTHOR - UNSUPPORTED RETRIEVAL FAST PATH:\n"
            f"Analyst was skipped before expensive analysis because: {analyst_skip_reason}. "
            f"Gate signals: {_signal_text}. "
            "Write a concise no-evidence / unsupported-evidence answer. Use the retrieved "
            "precision evidence only to explain the limit; do not invent missing facts, numeric "
            "changes, patch notes, pricing details, or policy details.\n"
        )
        if _pre_gate_failure_card_reason:
            author_notes += f"Failure-card context: {_pre_gate_failure_card_reason}\n"
    elif complexity == "low":
        status.step("Skipping deep analysis (Fast mode)...")
        analysis = "DIRECT_TO_AUTHOR"
    elif corpus_weak and complexity in ("medium", "high"):
        if corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value:
            status.step("Thin corpus vs anchors \u2014 running analyst pass with estimation framing\u2026")
            _an_t0 = time.monotonic()
            _analyst_prompt = (
                analyst_cached_prefix + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\n"
                "Produce structured bullets per system prompt."
            )
            _measure_context_stage(
                "analyst_estimate_from_priors",
                prompt=_analyst_prompt,
                system_prompt=DEFAULT_SYSTEM["analyst_estimate_from_priors"],
                stable_prefix=DEFAULT_SYSTEM["analyst_estimate_from_priors"],
                evidence_passages=_evidence_slice_for_analyst(),
            )
            _record_analyst_model_call(_analyst_prompt)
            analysis = ask_model(
                _analyst_prompt,
                DEFAULT_SYSTEM["analyst_estimate_from_priors"],
                provider=smart_provider, model=smart_model, effort=analyst_effort,
                base_url=local_url, api_key=or_api_key, use_reasoning=use_reasoning,
            )
            analyst_seconds += max(0.0, time.monotonic() - _an_t0)
        else:
            status.step("Source match is low for the main subject; keeping the answer short.")
            analysis = "DIRECT_TO_AUTHOR"
    else:
        status.step(f"Analyzing and compressing evidence (Effort: {analyst_effort})...")
        _an_t0 = time.monotonic()
        _analyst_prompt = (
            analyst_cached_prefix
            + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\nExecute the Evaluation Process."
        )
        _measure_context_stage(
            "analyst",
            prompt=_analyst_prompt,
            system_prompt=DEFAULT_SYSTEM["analyst"],
            stable_prefix=DEFAULT_SYSTEM["analyst"],
            evidence_passages=_evidence_slice_for_analyst(),
        )
        _record_analyst_model_call(_analyst_prompt)
        analysis = ask_model(
            _analyst_prompt,
            DEFAULT_SYSTEM["analyst"],
            provider=smart_provider, model=smart_model, effort=analyst_effort,
            base_url=local_url, api_key=or_api_key, use_reasoning=use_reasoning,
        )
        analyst_seconds += max(0.0, time.monotonic() - _an_t0)

    # --- SYNTHESIZER EVALUATOR & SCRUTINEER ---
    if (
        complexity in ("medium", "high")
        and analysis != "DIRECT_TO_AUTHOR"
        and not post_retrieval_fast_path_used
        and not economist_output_used_as_analysis
    ):
        strong_retrieval = (
            not corpus_weak
            and bool(entity_hint_for_retrieval)
            and (utilization_rate_val is not None)
            and utilization_rate_val >= synth_skip_utilization_threshold
        )
        if strong_retrieval:
            status.step(
                "Retrieval already matches the main subject well; "
                "skipping synthesis completeness re-check and supplemental search."
            )
            if complexity in ("medium", "high"):
                first_synth_sufficient = True
        else:
            status.step("Checking synthesis completeness...")
            synth_eval_prompt = (
                f"Original query: {query}\n\nAnalyst synthesis:\n{analysis}\n\n"
                "Execute the synthesis evaluation."
            )
            _measure_context_stage(
                "synth_evaluator",
                prompt=synth_eval_prompt,
                system_prompt=DEFAULT_SYSTEM["synth_evaluator"],
            )
            _se_t0 = time.monotonic()
            synth_eval_text = deps.clean_json_response(
                ask_model(
                    synth_eval_prompt, DEFAULT_SYSTEM["synth_evaluator"],
                    provider=fast_provider, model=fast_model, effort="low",
                    base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=use_reasoning,
                )
            )
            synth_evaluator_seconds += max(0.0, time.monotonic() - _se_t0)

            synth_is_sufficient = True
            synth_queries: list[str] = []
            deficiency = "Missing key specifics."
            try:
                synth_eval_data = json.loads(synth_eval_text)
                synth_is_sufficient = synth_eval_data.get("is_sufficient", True)
                synth_queries = [
                    str(q)[:300] for q in synth_eval_data.get("supplemental_queries", [])
                ][:2]
                deficiency = synth_eval_data.get("deficiency", "Missing key specifics.")
                if not synth_is_sufficient:
                    synth_was_insufficient = True
                    synth_deficiency = str(deficiency) if deficiency is not None else "Missing key specifics."
            except Exception as e:
                run_log.warning("Synth Evaluator JSON parse failed: %s", e)
            if complexity in ("medium", "high"):
                first_synth_sufficient = bool(synth_is_sufficient)

            if not synth_is_sufficient and synth_queries:
                synth_queries = _finalize_retrieval_queries(
                    synth_queries, max_len=2, include_official_bias=False
                )
                author_notes = (
                    f"\n\n\u26a0\ufe0f NOTE FOR AUTHOR: Synthesis quality check flagged: '{deficiency}'. "
                    "Hedge appropriately where data is missing."
                )
                status.step(f"Completeness gap detected: {deficiency}. Running supplemental searches...")
                supp_search_depth = choose_supplemental_search_depth(complexity, search_depth)
                supp_providers = select_providers(
                    query_type, intent, complexity, available_keys,
                    report_type=report_type, is_academic=is_academic,
                    suppress_tavily=suppress_tavily, override=None,
                )
                seen_before_supp = len(seen_urls)
                supplemental_ran = True
                supp_passages = process_search_queries(
                    synth_queries, intent, complexity, supp_search_depth, results_per_query,
                    include_domains, exclude_domains, query_embedding, seen_urls, collected_images,
                    embed_provider, embed_model, local_url, embed_texts, deps.compute_similarities,
                    status_container=status,
                    search_providers=supp_providers,
                    entity_hint=entity_hint_for_retrieval,
                    provider_diagnostics=provider_diagnostics,
                    provider_role="supplemental_search",
                )
                delta_urls_supplemental = max(0, len(seen_urls) - seen_before_supp)

                if supp_passages:
                    all_passages.extend(supp_passages)
                    final_evidence_bundle = build_final_evidence_bundle(
                        _final_evidence_bundle_inputs(),
                        linkup_block=(
                            linkup_block
                            if complexity == "high"
                            and os.getenv("LINKUP_API_KEY")
                            and linkup_block
                            else ""
                        ),
                    )
                    final_top_evidence = final_evidence_bundle.final_top_evidence
                    unique_source_urls = final_evidence_bundle.unique_source_urls
                    ordered_sources = final_evidence_bundle.ordered_sources
                    evidence_block = final_evidence_bundle.evidence_block
                    cached_prefix = final_evidence_bundle.cached_prefix
                    status.step("Re-analyzing with supplemental evidence...")
                    analyst_cached_prefix = _build_analyst_cached_prefix()
                    _an_t0 = time.monotonic()
                    _analyst_prompt = (
                        analyst_cached_prefix
                        + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\nExecute the Evaluation Process."
                    )
                    _measure_context_stage(
                        "analyst_supplemental",
                        prompt=_analyst_prompt,
                        system_prompt=DEFAULT_SYSTEM["analyst"],
                        stable_prefix=DEFAULT_SYSTEM["analyst"],
                        evidence_passages=_evidence_slice_for_analyst(),
                    )
                    _record_analyst_model_call(_analyst_prompt)
                    analysis = ask_model(
                        _analyst_prompt,
                        DEFAULT_SYSTEM["analyst"],
                        provider=smart_provider, model=smart_model, effort=analyst_effort,
                        base_url=local_url, api_key=or_api_key, use_reasoning=use_reasoning,
                    )
                    analyst_seconds += max(0.0, time.monotonic() - _an_t0)
                else:
                    status.step("Supplemental search yielded no new results. Passing gap directly to author.")

        # --- SCRUTINEER (Deep only) ---
        if complexity == "high":
            scrutineer_ran = True
            status.step("Running adversarial review (Scrutineer)...")
            flag_limit = 8 if intent == "news" else 6
            scrutineer_sys_prompt = DEFAULT_SYSTEM["scrutineer"].replace("{flag_limit}", str(flag_limit))
            scrutineer_input = (
                f"This synthesis was produced from a corpus of {len(final_top_evidence)} source chunks "
                f"drawn from {len(unique_source_urls)} unique URLs. Attribution in the synthesis reflects "
                f"editorial choices about what to cite, not the total available evidence.\n\n"
                f"Analyst synthesis to audit:\n\n{analysis}"
            )
            _measure_context_stage(
                "scrutineer",
                prompt=scrutineer_input,
                system_prompt=scrutineer_sys_prompt,
            )
            _sc_t0 = time.monotonic()
            scrutineer_text = deps.clean_json_response(
                ask_model(
                    scrutineer_input, scrutineer_sys_prompt,
                    provider=smart_provider, model=smart_model, effort="medium",
                    base_url=local_url, api_key=or_api_key, require_json=True, use_reasoning=False,
                )
            )
            scrutineer_seconds += max(0.0, time.monotonic() - _sc_t0)
            try:
                scrutineer_data = json.loads(scrutineer_text)
                scrutineer_flags = scrutineer_data.get("flags", [])
                scrutineer_high_count = len(
                    [f for f in scrutineer_flags if str(f.get("severity", "")).lower() == "high"]
                )
                scrutineer_verdict = scrutineer_data.get("verdict", "clean")
                run_log.info(
                    "Scrutineer verdict: %s | Flags: %d", scrutineer_verdict, len(scrutineer_flags)
                )

                HIGH_FLAG_THRESHOLD = 5
                if scrutineer_flags and len(scrutineer_flags) >= HIGH_FLAG_THRESHOLD:
                    run_log.warning(
                        "Scrutineer returned %d flags — evidence base too thin for remediation. "
                        "Passing flags as author context instead.",
                        len(scrutineer_flags),
                    )
                    status.step(
                        f"Scrutineer raised {len(scrutineer_flags)} issues. "
                        "Evidence base too thin for remediation; passing flags directly to author."
                    )
                else:
                    SEARCHABLE = {"SINGLE-SOURCE", "TEMPORAL DRIFT"}
                    search_flags = [
                        f for f in scrutineer_flags
                        if f.get("severity", "").lower() == "high" and f.get("category") in SEARCHABLE
                    ]
                    if search_flags:
                        status.step(
                            f"Scrutineer raised {len(search_flags)} high-severity issue(s). "
                            "Generating remediation queries..."
                        )
                        flag_lines = "\n".join(
                            f"- [{f.get('category')}] {f.get('challenge')}" for f in search_flags
                        )
                        remed_prompt = (
                            f"Today is {current_date}.\nCore topic: {core_topic}\n\n"
                            "ALREADY SEARCHED (do not repeat or paraphrase these):\n"
                            + "\n".join(f"- {q}" for q in past_searches)
                            + f"\n\nAn auditor flagged these specific concerns in a research synthesis:\n{flag_lines}\n\n"
                            "Generate 1-2 targeted search queries to find evidence that would resolve these concerns.\n"
                            "These queries MUST be meaningfully different from the already-searched list above.\n"
                            "If the flagged concern cannot be resolved with a novel query, return an empty array.\n"
                            "Queries must be under 10 words. Terse keywords only. No natural language.\n"
                            'Return JSON: {"queries": ["query1"]}'
                        )
                        _measure_context_stage(
                            "scrutineer_remediation_researcher",
                            prompt=remed_prompt,
                            system_prompt=DEFAULT_SYSTEM["researcher"],
                        )
                        _rem_t0 = time.monotonic()
                        remed_raw = deps.clean_json_response(
                            ask_model(
                                remed_prompt, DEFAULT_SYSTEM["researcher"],
                                provider=fast_provider, model=fast_model, effort="low",
                                base_url=local_url, api_key=or_api_key,
                                require_json=True, use_reasoning=use_reasoning,
                            )
                        )
                        scrutineer_seconds += max(0.0, time.monotonic() - _rem_t0)
                        remed_queries: list[str] = []
                        try:
                            remed_queries = [
                                str(q)[:300] for q in json.loads(remed_raw).get("queries", [])
                            ][:2]
                        except Exception as e:
                            run_log.warning("Remediation query parse failed: %s", e)

                        if remed_queries:
                            novel_queries = []
                            for rq in remed_queries:
                                is_novel = True
                                rq_tokens = set(rq.lower().split())
                                for pq in past_searches:
                                    pq_tokens = set(pq.lower().split())
                                    if not rq_tokens or not pq_tokens:
                                        continue
                                    overlap = len(rq_tokens & pq_tokens) / max(len(rq_tokens), 1)
                                    if overlap > 0.6:
                                        is_novel = False
                                        break
                                if is_novel:
                                    novel_queries.append(rq)

                            novel_queries = _finalize_retrieval_queries(
                                novel_queries, max_len=2, include_official_bias=False
                            )

                            if not novel_queries:
                                run_log.info(
                                    "Scrutineer remediation: all generated queries too similar to prior searches. Skipping."
                                )
                                status.step("Remediation searches skipped (duplicate queries).")
                            else:
                                status.step(f"Remediation searches: {novel_queries}")
                                remed_providers = select_providers(
                                    query_type, intent, complexity, available_keys,
                                    report_type=report_type, is_academic=is_academic,
                                    suppress_tavily=suppress_tavily, override=None,
                                )
                                remed_passages = process_search_queries(
                                    novel_queries, intent, complexity, search_depth, results_per_query,
                                    include_domains, exclude_domains, query_embedding, seen_urls, collected_images,
                                    embed_provider, embed_model, local_url, embed_texts, deps.compute_similarities,
                                    status_container=status,
                                    search_providers=remed_providers,
                                    linkup_depth_override="deep",
                                    entity_hint=entity_hint_for_retrieval,
                                    provider_diagnostics=provider_diagnostics,
                                    provider_role="scrutineer_remediation",
                                )
                                if remed_passages:
                                    all_passages.extend(remed_passages)
                                    final_evidence_bundle = build_final_evidence_bundle(
                                        _final_evidence_bundle_inputs(),
                                        linkup_block=(
                                            linkup_block
                                            if complexity == "high"
                                            and os.getenv("LINKUP_API_KEY")
                                            and linkup_block
                                            else ""
                                        ),
                                    )
                                    final_top_evidence = final_evidence_bundle.final_top_evidence
                                    unique_source_urls = final_evidence_bundle.unique_source_urls
                                    ordered_sources = final_evidence_bundle.ordered_sources
                                    evidence_block = final_evidence_bundle.evidence_block
                                    cached_prefix = final_evidence_bundle.cached_prefix
                                    status.step("Re-synthesizing with remediation evidence...")
                                    analyst_cached_prefix = _build_analyst_cached_prefix()
                                    _an_t0 = time.monotonic()
                                    _remed_analyst_prompt = (
                                        analyst_cached_prefix
                                        + f"Context: '{intent}' search requiring '{analyst_effort}' depth.\nExecute the Evaluation Process."
                                    )
                                    _measure_context_stage(
                                        "analyst_scrutineer_remediation",
                                        prompt=_remed_analyst_prompt,
                                        system_prompt=DEFAULT_SYSTEM["analyst"],
                                        stable_prefix=DEFAULT_SYSTEM["analyst"],
                                        evidence_passages=_evidence_slice_for_analyst(),
                                    )
                                    analysis = ask_model(
                                        _remed_analyst_prompt,
                                        DEFAULT_SYSTEM["analyst"],
                                        provider=smart_provider, model=smart_model, effort=analyst_effort,
                                        base_url=local_url, api_key=or_api_key, use_reasoning=use_reasoning,
                                    )
                                    analyst_seconds += max(0.0, time.monotonic() - _an_t0)
                                else:
                                    status.step("Remediation search yielded no new results.")
            except Exception as e:
                run_log.warning("Scrutineer JSON parse failed: %s", e)
                scrutineer_flags = []

    # ------------------------------------------------------------------
    # Build author prompt and generate final report
    # ------------------------------------------------------------------
    image_context = ""
    if image_mode in ("required", "contextual") and collected_images:
        valid_images = [
            url for url in collected_images
            if url.startswith("http")
            and any(
                ext in url.lower()
                for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif",
                            "images?", "format=jpg", "format=png")
            )
            and len(url) < 600
        ]
        if valid_images:
            image_list = list(valid_images)[:5]
            image_block = "\n".join(f"- {url}" for url in image_list)
            if image_mode == "required":
                image_context = (
                    f"\n\nAVAILABLE IMAGES:\n{image_block}\n\n"
                    "IMAGE RULES: The user explicitly requested visual content. Embed 2-3 of the best "
                    "images prominently near the beginning of your report using markdown: "
                    "![description](url). Ensure they are central to the answer. "
                    "Only embed an image if the URL or source indicates it is highly relevant to the "
                    "specific subject. Do not use generic or unrelated images."
                )
            else:
                image_context = (
                    f"\n\nAVAILABLE IMAGES:\n{image_block}\n\n"
                    "IMAGE RULES: Embed 1-2 contextually relevant images using markdown: "
                    "![description](url). Place images near the content they illustrate. "
                    "Only embed an image if the URL or source indicates it is highly relevant to "
                    "the specific subject. Do not use generic or unrelated images."
                )
    if corpus_weak and corpus_state != CorpusState.ESTIMATE_FROM_PRIORS.value:
        image_context = ""

    _efp_author = corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value

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

    tier_instructions = {
        "low": (
            "TIER: FAST. You are working from unanalyzed search snippets. Do not synthesize competing "
            "claims into a single assertion \u2014 present them as reported. Cap confidence language. "
            "Prefer \u2018reportedly,\u2019 \u2018according to,\u2019 \u2018as of [date]\u2019 over "
            "declarative present-tense claims. The absence of an analyst pass means unresolved "
            "conflicts in the evidence should remain visible rather than being collapsed into a single "
            "verdict. Provide a direct opening answer followed by no more than 3-4 short supporting "
            "sentences. No headers. No sources section at the end (use inline citations only). "
            "Tone: direct answer, not a report."
        ),
        "medium": (
            "TIER: BALANCED. Write a structured brief. Use H3 headers for sections, narrative "
            "paragraphs, and a Sources list at the end. For queries that compare two or more entities "
            "across measurable dimensions, include a markdown table summarizing the key metrics before "
            "the narrative sections."
        ),
        "high": (
            "TIER: DEEP. Write a dense, detailed intelligence report. Match the density of the "
            "analysis. Use H3 headers for multiple subsections, detailed cross-source synthesis, and "
            "a Sources list at the end. Use markdown tables to effectively structure comparative data "
            "or dense metrics."
        ),
    }
    if _thin_body:
        _thin = (
            "TIER: THIN \u2014 Retrieved pages are a poor match to the user\u2019s main subject. "
            "Entire output under ~200 words, at most 2-3 short paragraphs, no H3, no table, "
            "no long digests of off-topic material."
        )
        if _relevance_low and not (corpus_weak and not _efp_author):
            _thin = (
                "TIER: THIN \u2014 Source–topic match is weak (low utilization). Use Fast-style brevity even though "
                "the run is Balanced/Deep: at most 2-3 short paragraphs, no H3, no table, no long structured report. "
                "State limits clearly; do not pad with generic sections."
            )
        tier_instructions = {"low": _thin, "medium": _thin, "high": _thin}

    precision_count = 4 if _thin_body else (10 if complexity == "high" else 8)
    final_evidence_bundle = attach_author_evidence(
        final_evidence_bundle,
        precision_count=precision_count,
    )
    author_evidence = final_evidence_bundle.author_evidence
    author_evidence_block = final_evidence_bundle.author_evidence_block

    author_prompt = f"Today is {current_date}.\nUser's Original Prompt: {query}\n\n{tier_instructions[complexity]}\n\n"
    if recency_notes:
        author_prompt += recency_notes + "\n\n"
    if complexity != "low" and (not corpus_weak or _efp_author) and not _relevance_low:
        author_prompt += f"Analysis:\n{analysis}\n\n"
    if (corpus_weak and not _efp_author) or _relevance_low:
        author_prompt += f"Main subject (target): {primary_entity or core_topic}\n"

    author_prompt += f"Precision Evidence (for accurate citations):\n{author_evidence_block}\n\n"

    if complexity != "low" and (not corpus_weak or _efp_author) and not _relevance_low:
        author_prompt += f"Sources:\n{chr(10).join(ordered_sources)}\n\n"

    nutrition_partial_note = _format_nutrition_partial_evidence_author_note(
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
        final_top_evidence=author_evidence,
    )
    if nutrition_partial_note:
        author_notes += nutrition_partial_note

    if author_notes:
        author_prompt += f"{author_notes}\n\n"

    if complexity == "high" and scrutineer_flags and (not corpus_weak or _efp_author) and not _relevance_low:
        high_ct = len([f for f in scrutineer_flags if f.get("severity", "").lower() == "high"])
        med_ct = len([f for f in scrutineer_flags if f.get("severity", "").lower() == "medium"])
        scrutineer_block = (
            f"SCRUTINEER AUDIT \u2014 {len(scrutineer_flags)} flag(s) "
            f"({high_ct} high, {med_ct} medium):\n"
        )
        for i, flag in enumerate(scrutineer_flags, 1):
            scrutineer_block += (
                f"\n[{i}] {flag.get('severity', '').upper()} | {flag.get('category', '')}\n"
                f"  Passage: \"{flag.get('passage', '')}\"\n"
                f"  Challenge: {flag.get('challenge', '')}\n"
            )
        scrutineer_block += (
            "\n\nAUTHOR DIRECTIVE: For HIGH flags \u2014 hedge, omit, or explicitly note uncertainty. "
            "For MEDIUM flags \u2014 add a caveat. LOW flags are advisory. "
            "Do not reference an 'audit', 'scrutineer', or 'reviewer' in your output. "
            "Resolve the flag in the prose silently.\n\n"
        )
        author_prompt += scrutineer_block

    author_prompt += f"Write the final markdown report based on the adaptive guidelines.{image_context}"
    author_quant_source_telemetry = _scan_author_quant_source_telemetry(
        author_prompt,
        analyst_quant_packet_reviewed_by_model=bool(
            analyst_quant_packet_handoff_telemetry.get(
                "analyst_quant_packet_reviewed_by_model"
            )
        ),
        analysis=analysis,
    )
    economist_skip_eligibility_shadow_telemetry = (
        _economist_skip_eligibility_shadow_telemetry(
            report_type=report_type,
            complexity=complexity,
            mode=strategy,
            economist_safety_telemetry=economist_safety_telemetry,
            analyst_quant_packet_handoff_telemetry=analyst_quant_packet_handoff_telemetry,
            author_quant_source_telemetry=author_quant_source_telemetry,
            quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
            analyst_skipped_after_economist=analyst_skipped_after_economist,
            economist_output_used_as_analysis=economist_output_used_as_analysis,
            pre_analyst_gate_skipped=analyst_skipped,
        )
    )
    economist_skip_shadow_alignment = _economist_skip_shadow_alignment(
        pre_analyst_candidate_telemetry=economist_pre_analyst_skip_candidate_telemetry,
        posthoc_skip_eligibility_telemetry=economist_skip_eligibility_shadow_telemetry,
    )

    status.update("Writing final report...")

    _author_system = DEFAULT_SYSTEM["author"]
    author_system_prompt_key = "author"
    if corpus_weak:
        if _efp_author:
            _candidate_author_key = "author_estimate_from_priors"
            _author_system = DEFAULT_SYSTEM.get(
                _candidate_author_key,
                DEFAULT_SYSTEM["author"],
            )
            author_system_prompt_key = (
                _candidate_author_key
                if _candidate_author_key in DEFAULT_SYSTEM
                else "author"
            )
        else:
            _candidate_author_key = "author_corpus_weak"
            _author_system = DEFAULT_SYSTEM.get(
                _candidate_author_key,
                DEFAULT_SYSTEM["author"],
            )
            author_system_prompt_key = (
                _candidate_author_key
                if _candidate_author_key in DEFAULT_SYSTEM
                else "author"
            )
    _author_effort = (
        analyst_effort if ((not corpus_weak or _efp_author) and not _relevance_low) else "low"
    )
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

    final_output_metadata = build_final_output_metadata(
        report=report,
        latency_seconds=0.0,
        cost_snapshot={},
    )
    output_word_count = final_output_metadata["output_word_count"]
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
    answer_contract_runtime_trace_fragment: dict[str, Any] = {}
    try:
        (
            _runtime_conflict_state,
            runtime_conflict_projection,
        ) = _build_runtime_conflict_state_projection(
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            current_date=current_date,
            final_top_evidence=final_top_evidence,
            source_tier_counts=_source_tier_exec["source_tier_counts"],
            source_domain_telemetry=_source_domain_exec,
            source_class_observability=runtime_source_class_recovery_telemetry,
        )
        answer_contract_runtime_result = build_runtime_answer_contract_handoff(
            RuntimeAnswerContractFacts(
                query=query,
                intent=intent,
                report_type=report_type,
                query_type=query_type,
                mode=strategy,
                current_date=current_date,
                core_topic=core_topic,
                evidence_available=bool(final_top_evidence),
                evidence_sufficient=bool(evidence_sufficient),
                source_tier_counts=_source_tier_exec["source_tier_counts"],
                source_class_recovery_telemetry=(
                    runtime_source_class_recovery_telemetry
                ),
                active_source_class_recovery_lifecycle=(
                    runtime_active_source_class_recovery_lifecycle
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
                conflicts_present=runtime_conflict_projection["conflicts_present"],
                conflict_notes=runtime_conflict_projection["conflict_notes"],
                resolving_queries=runtime_conflict_projection["resolving_queries"],
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                queries_by_iteration=queries_per_iter,
                final_top_evidence=final_top_evidence,
                evidence_integration_checkpoint=(
                    evidence_integration_checkpoint_handoff
                ),
                iteration=iterations_run,
                max_iterations=max_iterations,
                max_recovery_attempts=1,
            ),
            controller=_run_controller_mirror,
        )
        answer_contract_runtime_trace_fragment = (
            answer_contract_runtime_result.execution_trace_fragment()
        )
    except Exception as exc:
        logger.warning("Non-fatal answer-contract handoff omitted: %s", exc)
    _provider_diagnostics_payload = provider_diagnostics_payload(provider_diagnostics)
    execution_trace: dict[str, Any] = {
        "run_id": run_id,
        "timestamp_utc": ts_utc,
        "query_preview": (query or "")[:200],
        "intent": intent,
        "query_type": query_type,
        "primary_entity": (primary_entity or "")[:200],
        "entities": [str(e)[:200] for e in (entities_list or [])],
        "empty_entity": empty_entity_flag,
        "router_entity_retry_used": router_entity_retry_used,
        "utilization_pre_retry": utilization_pre_retry,
        "utilization_rate": utilization_rate_val,
        "retrieval_retry_used": retrieval_retry_used,
        "corpus_state": corpus_state,
        "corpus_state_forced": corpus_state_forced_flag,
        "corpus_weak": corpus_weak,
        "useful_content": useful_content,
        "response_displayable": response_displayable,
        "evidence_sufficient": evidence_sufficient,
        "answer_class": answer_class,
        "useful_content_reason": useful_content_reason,
        "waste_flags": list(waste_flags),
        "query_redundancy_skipped": ("query_redundancy_skipped" in waste_flags),
        "recon_fired": recon_fired,
        "recon_confidence": recon_confidence,
        "canonical_subject_resolved": (canonical_subject_resolved or "")[:200] or None,
        "timing": dict(_timing_payload),
        "router_original_report_type": router_original_report_type,
        "router_original_query_type": router_original_query_type,
        "routing_override_applied": routing_override_applied,
        "routing_override_reason": routing_override_reason,
        "report_type": report_type,
        **anchor_packet_telemetry,
        **nutrition_lookup_telemetry,
        "complexity": complexity,
        "mode": strategy,
        "scout_fired": scout_fired,
        "scout_key": scout_key_used,
        "scout_queries": list(scout_queries),
        "scout_skip_reason": scout_skip_reason,
        "iterations_run": iterations_run,
        "pass_providers": list(providers_by_iteration),
        **_provider_diagnostics_payload,
        "queries_per_iteration": queries_per_iter,
        "disambiguation_queries_by_iteration": disambiguation_queries_per_iter,
        "weak_corpus_recovery_considered": weak_corpus_recovery_considered,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": weak_corpus_recovery_skip_reason,
        "weak_corpus_recovery_queries": list(weak_corpus_recovery_queries),
        "weak_corpus_recovery_decision": weak_corpus_recovery_decision,
        "weak_corpus_recovery_reason": weak_corpus_recovery_reason,
        "weak_corpus_recovery_blockers": list(weak_corpus_recovery_blockers),
        **retrieval_stop_shadow_telemetry,
        **retrieval_stop_active_telemetry,
        **active_source_class_recovery_lifecycle,
        **active_conflict_resolution_lifecycle,
        ORDINARY_CONTINUATION_TRACE_KEY: dict(
            ordinary_continuation_candidate_trace
        ),
        **targeted_retrieval_lifecycle_trace,
        "evaluator_continuation_spine_gate_trace": dict(
            evaluator_continuation_spine_gate_trace
        ),
        "expander_continuation_spine_gate_trace": dict(
            expander_continuation_spine_gate_trace
        ),
        "scout_continuation_spine_gate_trace": dict(
            scout_continuation_spine_gate_trace
        ),
        RETRIEVAL_BATCH_DISPATCH_TRACE_KEY: dict(retrieval_batch_dispatch_trace),
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: (
            evidence_integration_checkpoint_trace
        ),
        **authoritative_source_action_trace_fragment(
            authoritative_source_action_trace=authoritative_source_action_trace,
            official_source_obligation_bridge_trace=(
                official_source_obligation_bridge_trace
            ),
            official_canonical_recovery_query_acquisition_trace=(
                official_canonical_recovery_query_acquisition_trace
            ),
            official_canonical_recovery_execution_admission_trace=(
                official_canonical_recovery_execution_admission_trace
            ),
        ),
        **answer_contract_runtime_trace_fragment,
        "urls_fetched": total_urls_fetched,
        "total_chunks": total_chunks_embedded,
        "source_tier_counts": _source_tier_exec["source_tier_counts"],
        "source_domain_counts": _source_domain_exec["source_domain_counts"],
        "top_source_domains": _source_domain_exec["top_source_domains"],
        "unique_source_domain_count": _source_domain_exec["unique_source_domain_count"],
        "on_domain_source_count": _source_domain_exec["on_domain_source_count"],
        "off_domain_source_count": _source_domain_exec["off_domain_source_count"],
        "official_evidence_found": _source_tier_exec["official_evidence_found"],
        "community_signal_found": _source_tier_exec["community_signal_found"],
        "low_trust_sources_found": _source_tier_exec["low_trust_sources_found"],
        "pollution_detected": _source_tier_exec["pollution_detected"],
        **source_class_recovery_telemetry,
        **source_class_observability_telemetry,
        "source_survival_final_evidence_official_or_canonical_count": (
            _official_or_canonical_source_class_count(
                source_class_evidence_bundle_observability_telemetry.get(
                    "source_class_strong_satisfaction_counts"
                )
            )
        ),
        "source_survival_final_citation_official_or_canonical_count": (
            _official_or_canonical_source_class_count(
                source_class_observability_telemetry.get(
                    "source_class_strong_satisfaction_counts"
                )
            )
        ),
        "estimate_from_priors_requested": estimate_from_priors_requested,
        "estimate_from_priors_blocked_by_pre_analyst_gate": (
            estimate_from_priors_blocked_by_pre_analyst_gate
        ),
        "economist_ran": economist_ran,
        "economist_preflight_allowed": economist_preflight_allowed,
        "economist_preflight_block_reason": economist_preflight_block_reason,
        "economist_preflight_missing_entities": list(
            economist_preflight_missing_entities
        ),
        **economist_safety_telemetry,
        **quant_retrieval_sufficiency_telemetry,
        **quantitative_consistency_telemetry,
        **quantitative_consistency_guard_telemetry,
        "missing_target_metric_directive_emitted": (
            missing_target_metric_directive_emitted
        ),
        **economist_pre_analyst_skip_candidate_telemetry,
        **analyst_quant_packet_handoff_telemetry,
        **author_quant_source_telemetry,
        "author_system_prompt_key": author_system_prompt_key,
        **final_answer_source_telemetry,
        **economist_skip_eligibility_shadow_telemetry,
        "economist_skip_shadow_alignment": economist_skip_shadow_alignment,
        "analyst_skipped": analyst_skipped,
        "analyst_skip_reason": analyst_skip_reason,
        "analyst_skipped_after_economist": analyst_skipped_after_economist,
        "analyst_after_economist_skip_reason": analyst_after_economist_skip_reason,
        "economist_output_used_as_analysis": economist_output_used_as_analysis,
        "post_retrieval_fast_path_used": post_retrieval_fast_path_used,
        "pre_analyst_gate_signals": list(pre_analyst_gate_signals),
        "thin_quant_analyst_used": False,
        "scrutineer_ran": scrutineer_ran,
        "scrutineer_flag_count": scrutineer_flag_count,
        "synth_was_insufficient": synth_was_insufficient,
        "synth_sufficient_first_pass_raw": synth_sufficient_first_pass_raw,
        "synth_sufficient_first_pass": synth_sufficient_first_pass,
        "supplemental_ran": supplemental_ran,
        "context_measurement": context_measurement.payload(),
        "latency_seconds": latency_seconds,
        "output_word_count": output_word_count,
        "final_output_preview": (report or "")[:300],
        "cost": cost_snapshot,
        "failure_card": failure_card_payload,
    }
    runtime_trace_export_attachment = (
        attach_runtime_trace_export_compatibility_payloads(
            execution_trace,
            recovered_passages=(
                source_class_projection_handoff.recovered_source_class_passages
            ),
            final_top_evidence=final_top_evidence,
            max_iterations=max_iterations,
            evidence_bundle_source_class_counts=(
                source_class_evidence_bundle_observability_telemetry.get(
                    "source_class_strong_satisfaction_counts"
                )
            ),
            session_payload=new_session,
            logger=run_log,
        )
    )
    source_class_recovery_validation_packet = (
        runtime_trace_export_attachment.source_class_recovery_validation_packet
    )

    # --- Execution log ---
    final_output_metadata = build_final_output_metadata(
        report=report,
        latency_seconds=latency_seconds,
        cost_snapshot=cost_snapshot,
    )
    output_word_count = final_output_metadata["output_word_count"]
    execution_log_entry = build_execution_log_entry(
        current_date=current_date,
        ts_utc=ts_utc,
        run_id=run_id,
        session_id=session_id,
        query=query,
        intent=intent,
        query_type=query_type,
        primary_entity=primary_entity,
        entities_list=entities_list,
        empty_entity_flag=empty_entity_flag,
        router_entity_retry_used=router_entity_retry_used,
        utilization_pre_retry=utilization_pre_retry,
        utilization_rate_val=utilization_rate_val,
        retrieval_retry_used=retrieval_retry_used,
        corpus_state=corpus_state,
        corpus_state_forced_flag=corpus_state_forced_flag,
        corpus_weak=corpus_weak,
        useful_content=useful_content,
        response_displayable=response_displayable,
        evidence_sufficient=evidence_sufficient,
        answer_class=answer_class,
        useful_content_reason=useful_content_reason,
        waste_flags=waste_flags,
        recon_fired=recon_fired,
        recon_confidence=recon_confidence,
        canonical_subject_resolved=canonical_subject_resolved,
        timing_payload=_timing_payload,
        router_original_report_type=router_original_report_type,
        router_original_query_type=router_original_query_type,
        routing_override_applied=routing_override_applied,
        routing_override_reason=routing_override_reason,
        report_type=report_type,
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        complexity=complexity,
        mode=strategy,
        fast_model=fast_model,
        smart_model=smart_model,
        scout_fired=scout_fired,
        scout_key_used=scout_key_used,
        scout_queries=scout_queries,
        scout_skip_reason=scout_skip_reason,
        iterations_run=iterations_run,
        total_chunks_embedded=total_chunks_embedded,
        total_urls_fetched=total_urls_fetched,
        providers_by_iteration=providers_by_iteration,
        provider_diagnostics_payload=_provider_diagnostics_payload,
        queries_per_iter=queries_per_iter,
        disambiguation_queries_per_iter=disambiguation_queries_per_iter,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        weak_corpus_recovery_queries=weak_corpus_recovery_queries,
        weak_corpus_recovery_decision=weak_corpus_recovery_decision,
        weak_corpus_recovery_reason=weak_corpus_recovery_reason,
        weak_corpus_recovery_blockers=weak_corpus_recovery_blockers,
        synth_sufficient_first_pass_raw=synth_sufficient_first_pass_raw,
        synth_sufficient_first_pass=synth_sufficient_first_pass,
        scrutineer_flag_count=scrutineer_flag_count,
        estimate_from_priors_requested=estimate_from_priors_requested,
        estimate_from_priors_blocked_by_pre_analyst_gate=(
            estimate_from_priors_blocked_by_pre_analyst_gate
        ),
        economist_ran=economist_ran,
        economist_preflight_allowed=economist_preflight_allowed,
        economist_preflight_block_reason=economist_preflight_block_reason,
        economist_preflight_missing_entities=economist_preflight_missing_entities,
        economist_safety_telemetry=economist_safety_telemetry,
        quant_retrieval_sufficiency_telemetry=quant_retrieval_sufficiency_telemetry,
        missing_target_metric_directive_emitted=missing_target_metric_directive_emitted,
        economist_pre_analyst_skip_candidate_telemetry=(
            economist_pre_analyst_skip_candidate_telemetry
        ),
        analyst_quant_packet_handoff_telemetry=analyst_quant_packet_handoff_telemetry,
        author_quant_source_telemetry=author_quant_source_telemetry,
        author_system_prompt_key=author_system_prompt_key,
        final_answer_source_telemetry=final_answer_source_telemetry,
        economist_skip_eligibility_shadow_telemetry=(
            economist_skip_eligibility_shadow_telemetry
        ),
        economist_skip_shadow_alignment=economist_skip_shadow_alignment,
        analyst_skipped=analyst_skipped,
        analyst_skip_reason=analyst_skip_reason,
        analyst_skipped_after_economist=analyst_skipped_after_economist,
        analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
        economist_output_used_as_analysis=economist_output_used_as_analysis,
        post_retrieval_fast_path_used=post_retrieval_fast_path_used,
        pre_analyst_gate_signals=pre_analyst_gate_signals,
        scrutineer_ran=scrutineer_ran,
        synth_was_insufficient=synth_was_insufficient,
        supplemental_ran=supplemental_ran,
        report=report,
        latency_seconds=latency_seconds,
        cost_snapshot=cost_snapshot,
        source_class_recovery_validation_trace_key=(
            SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY
        ),
        source_class_recovery_validation_packet=(
            source_class_recovery_validation_packet
        ),
        execution_trace=execution_trace,
        code_version_metadata=current_code_version_metadata(),
    )
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
        kb_context=KbReviewPersistenceContext(
            feedback_log_path=feedback_log_path,
            kb_triggers_path=kb_triggers_path,
            session_id=session_id,
            run_id=run_id,
            query=query,
            report_type=report_type,
            query_type=query_type,
            primary_entity=primary_entity,
            entities_list=entities_list,
            empty_entity_flag=empty_entity_flag,
            router_entity_retry_used=router_entity_retry_used,
            utilization_pre_retry=utilization_pre_retry,
            utilization_rate_val=utilization_rate_val,
            retrieval_retry_used=retrieval_retry_used,
            corpus_state=corpus_state,
            corpus_state_forced_flag=corpus_state_forced_flag,
            corpus_weak=corpus_weak,
            useful_content=useful_content,
            response_displayable=response_displayable,
            evidence_sufficient=evidence_sufficient,
            answer_class=answer_class,
            useful_content_reason=useful_content_reason,
            waste_flags=waste_flags,
            recon_fired=recon_fired,
            recon_confidence=recon_confidence,
            canonical_subject_resolved=canonical_subject_resolved,
            timing_payload=_timing_payload,
            strategy=strategy,
            fast_model=fast_model,
            smart_model=smart_model,
            complexity=complexity,
            intent=intent,
            iterations_run=iterations_run,
            providers_by_iteration=providers_by_iteration,
            queries_per_iter=queries_per_iter,
            queries_by_iteration=queries_by_iteration,
            disambiguation_queries_per_iter=disambiguation_queries_per_iter,
            weak_corpus_recovery_considered=weak_corpus_recovery_considered,
            weak_corpus_recovery_used=weak_corpus_recovery_used,
            weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
            weak_corpus_recovery_queries=weak_corpus_recovery_queries,
            weak_corpus_recovery_decision=weak_corpus_recovery_decision,
            weak_corpus_recovery_reason=weak_corpus_recovery_reason,
            weak_corpus_recovery_blockers=weak_corpus_recovery_blockers,
            scout_fired=scout_fired,
            scout_key_used=scout_key_used,
            scout_queries=scout_queries,
            synth_was_insufficient=synth_was_insufficient,
            synth_sufficient_first_pass_raw=synth_sufficient_first_pass_raw,
            synth_sufficient_first_pass=synth_sufficient_first_pass,
            failure_card_payload=failure_card_payload,
            supplemental_ran=supplemental_ran,
            delta_urls_supplemental=delta_urls_supplemental,
            total_chunks_embedded=total_chunks_embedded,
            seen_urls=list(seen_urls),
            scrutineer_high_count=scrutineer_high_count,
            scrutineer_flag_count=scrutineer_flag_count,
            synth_deficiency=synth_deficiency,
            latency_seconds=latency_seconds,
            output_word_count=output_word_count,
            report=report,
            cost_snapshot=cost_snapshot,
            ask_model=ask_model,
            clean_json_response=deps.clean_json_response,
            fast_provider=fast_provider,
            local_url=local_url,
            or_api_key=or_api_key,
            kb_review_agent=kb_review_agent,
        ),
        db_enabled=DB_ENABLED,
    )
    kb_instrumentation = persistence_side_effect_result.kb_instrumentation
    kb_warning = persistence_side_effect_result.kb_warning

    return build_run_outcome(
        session_id=session_id,
        run_id=run_id,
        session_title=session_title,
        query=query,
        core_topic=core_topic,
        report=report,
        final_top_evidence=final_top_evidence,
        seen_urls=list(seen_urls),
        collected_images=list(collected_images),
        execution_trace=execution_trace,
        failure_card_payload=failure_card_payload,
        session_payload=new_session,
        cost_snapshot=cost_snapshot,
        latency_seconds=latency_seconds,
        intent=intent,
        complexity=complexity,
        corpus_state=corpus_state,
        pipeline_config=pipeline_config_payload,
        kb_instrumentation=kb_instrumentation,
        kb_warning=kb_warning,
        author_streamed=bool(config.author_stream_display)
        and not quantitative_guard_stream_buffered,
    )
