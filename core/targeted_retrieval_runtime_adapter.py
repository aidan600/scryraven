"""Deterministic adapters for passive targeted-retrieval lifecycle traces."""

from __future__ import annotations

from typing import Any

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
)
from core.ordinary_continuation_candidate import source_path_from_runtime_source
from core.source_class_authority_runtime_adapter import (
    source_class_recovery_action_approved,
    source_class_recovery_action_attempted,
    source_class_recovery_authority_action,
    source_class_recovery_authority_blocker_reasons,
)
from core.targeted_retrieval_controller import (
    build_targeted_retrieval_controller_input,
    build_targeted_retrieval_lifecycle,
    targeted_retrieval_lifecycle_defaults,
)


def compact_runtime_strings(
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


def targeted_query_provenance_from_runtime(source: str | None) -> str | None:
    return source_path_from_runtime_source(source)


def targeted_retrieval_currentness_source_fit_facts(
    *,
    evidence_state: Any,
    source_class_recovery_telemetry: dict[str, Any],
    active_source_class_recovery_lifecycle: dict[str, Any],
) -> dict[str, bool]:
    missing_classes = set(
        compact_runtime_strings(getattr(evidence_state, "source_classes_missing", ()))
    )
    missing_classes.update(
        compact_runtime_strings(
            source_class_recovery_telemetry.get("missing_expected_source_classes")
        )
    )
    missing_classes.update(
        compact_runtime_strings(
            source_class_recovery_authority_action(
                active_source_class_recovery_lifecycle
            ).get("required_source_classes")
        )
    )
    gap_candidates = set(
        compact_runtime_strings(
            source_class_recovery_telemetry.get("source_class_gap_candidates")
        )
    )
    source_fit_gaps = missing_classes | gap_candidates
    official_current_source_gap = "official_current_rules" in source_fit_gaps
    legal_or_regulatory_gap = "legal_or_regulatory_text" in source_fit_gaps

    text_facts = " ".join(
        compact_runtime_strings(getattr(evidence_state, "missing_information", ()))
        + compact_runtime_strings(getattr(evidence_state, "partial_obligations", ()))
        + compact_runtime_strings(
            getattr(evidence_state, "unfulfilled_obligations", ())
        )
        + compact_runtime_strings(
            source_class_recovery_authority_blocker_reasons(
                active_source_class_recovery_lifecycle
            )
        )
        + compact_runtime_strings(
            [
                source_class_recovery_authority_action(
                    active_source_class_recovery_lifecycle
                ).get("reason")
            ]
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


def build_targeted_retrieval_lifecycle_from_runtime(
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
    candidate_queries = compact_runtime_strings(
        ordinary_candidate.get("ordinary_next_queries")
    )
    prior_queries = compact_runtime_strings(ordinary_candidate.get("prior_queries"))
    if not candidate_queries:
        candidate_queries = compact_runtime_strings(
            getattr(evidence_state, "next_queries", ())
        )
    if not prior_queries:
        prior_queries = compact_runtime_strings(
            getattr(evidence_state, "prior_queries", ())
        )
    material_gap_facts = (
        compact_runtime_strings(getattr(evidence_state, "missing_information", ()))
        + compact_runtime_strings(getattr(evidence_state, "partial_obligations", ()))
        + compact_runtime_strings(
            getattr(evidence_state, "unfulfilled_obligations", ())
        )
        + compact_runtime_strings(getattr(evidence_state, "source_classes_missing", ()))
    )
    retrieval_continue_gap = (
        retrieval_stop_shadow_telemetry.get("retrieval_stop_shadow_decision")
        == "continue_retrieval"
        and bool(candidate_queries)
    )
    source_fit_facts = targeted_retrieval_currentness_source_fit_facts(
        evidence_state=evidence_state,
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        active_source_class_recovery_lifecycle=(
            active_source_class_recovery_lifecycle
        ),
    )
    weak_corpus_dispatched = bool(
        controller_loop_spine_result.weak_corpus_executor_dispatched
    )
    conflict_dispatched = bool(
        controller_loop_spine_result.conflict_resolution_executor_dispatched
    )
    terminal_stop_approved = bool(controller_loop_spine_result.terminal_stop_approved)
    source_class_owns = bool(
        source_class_recovery_action_attempted(
            active_source_class_recovery_lifecycle
        )
        or source_class_recovery_action_approved(
            active_source_class_recovery_lifecycle
        )
        or checkpoint_action == RECOVER_MISSING_SOURCE_CLASS
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
    conflict_resolving_queries = compact_runtime_strings(
        ordinary_candidate.get("conflict_resolving_queries")
    )
    if not conflict_resolving_queries:
        conflict_resolving_queries = compact_runtime_strings(
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
        query_provenance=targeted_query_provenance_from_runtime(
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
        source_class_blockers=source_class_recovery_authority_blocker_reasons(
            active_source_class_recovery_lifecycle
        ),
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
