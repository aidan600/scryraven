"""Source-class recovery lifecycle records.

This module records the minimal active controller decision for source-class
recovery. It does not call retrieval, providers, prompts, routing, models,
storage, or orchestration code.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from core.official_canonical_recovery_candidate_acquisition import (
    official_canonical_recovery_candidate_acquisition_defaults,
)
from core.recovered_evidence_visibility import recovered_evidence_visibility_defaults
from core.run_controller import ControllerDecision, RetrievalAction, RunController
from core.source_class_recovery import recovery_source_quality_defaults
from core.source_class_recovery_controller import (
    SOURCE_CLASS_CONTROLLER_EVIDENCE_SIGNAL_KEYS,
    SourceClassRecoveryControllerDecision,
    build_source_class_recovery_controller_input,
    decide_source_class_recovery,
)

ACTIVE_SOURCE_CLASS_RECOVERY_TRACE_FIELDS = (
    "active_source_class_recovery_considered",
    "active_source_class_recovery_eligible",
    "active_source_class_recovery_used",
    "active_source_class_recovery_execution_attempted",
    "active_source_class_recovery_official_canonical_admitted",
    "active_source_class_recovery_reason",
    "active_source_class_recovery_skip_reason",
    "active_source_class_recovery_blockers",
    "active_source_class_recovery_missing_classes",
    "active_source_class_recovery_queries",
    "active_source_class_recovery_result_count",
    "active_source_class_recovery_new_url_count",
    "active_source_class_recovery_provider_role",
    "active_source_class_recovery_search_depth",
    "active_source_class_recovery_attempt_count",
    "active_source_class_recovery_action_envelope",
    "recovered_candidate_domain_preview",
    "recovered_source_tier_counts",
    "recovered_source_class_counts",
    "recovered_official_or_primary_count",
    "recovered_accepted_url_count",
    "recovered_promoted_source_count",
    "recovery_source_quality_status",
    "recovered_visibility_considered",
    "recovered_visibility_eligible",
    "recovered_visibility_used",
    "recovered_visibility_reason",
    "recovered_visibility_blockers",
    "recovered_visibility_missing_source_class",
    "recovered_visibility_recovered_source_class",
    "recovered_visibility_reserved_count",
    "recovered_visibility_reserved_source_ids",
    "recovered_visibility_reserved_source_classes",
    "recovered_visibility_dropped_source_ids",
    "recovered_visibility_drop_reason",
    "recovered_visibility_source_fit_status",
    "recovered_visibility_source_fit_candidate_count",
    "recovered_visibility_source_fit_selected_count",
    "recovered_visibility_source_fit_rejection_reasons",
    "candidate_acquisition_schema_version",
    "candidate_acquisition_considered",
    "candidate_acquisition_eligible",
    "candidate_acquisition_used",
    "candidate_acquisition_skip_reason",
    "candidate_acquisition_blockers",
    "acquisition_provider_role",
    "acquisition_query_count",
    "acquisition_query_previews",
    "acquisition_attempted",
    "candidate_acquisition_provider_attempt_count",
    "candidate_acquisition_provider_success_count",
    "candidate_acquisition_provider_failure_count",
    "candidate_acquisition_provider_result_count",
    "candidate_acquisition_provider_accepted_url_count",
    "candidate_acquisition_provider_new_source_count",
    "candidate_acquisition_result_status",
    "candidate_visibility_export_status",
    "candidate_visibility_blocker_kind",
    "recovered_result_count",
    "accepted_url_count",
    "candidate_return_status",
    "zero_candidate_blocker",
    "zero_candidate_blocker_kind",
    "official_canonical_candidate_visible",
    "likely_next_failure_layer",
    "behavior_changed",
)

SOURCE_CLASS_LIFECYCLE_EVIDENCE_SIGNAL_KEYS = SOURCE_CLASS_CONTROLLER_EVIDENCE_SIGNAL_KEYS


def _copy_evidence_signals(signals: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(signals[key])
        for key in SOURCE_CLASS_LIFECYCLE_EVIDENCE_SIGNAL_KEYS
        if key in signals
    }


def _copy_domain_constraints(value: Any) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        domain = " ".join(str(item or "").strip().casefold().split())
        if not domain:
            continue
        if domain.startswith("www."):
            domain = domain[4:]
        if domain and domain not in seen:
            domains.append(domain)
            seen.add(domain)
    return domains


def _prior_attempt_count(controller: RunController) -> int:
    count = int(controller.state.active_source_class_recovery_attempt_count or 0)
    if count > 0:
        return count
    action_records = (
        list(controller.state.recovery_action_records)
        + list(controller.ledger.retrieval_actions)
    )
    for action in action_records:
        if action.name == "source_class_recovery":
            return 1
    return 0


def _trace_payload(
    *,
    considered: bool,
    eligible: bool,
    used: bool,
    execution_attempted: bool,
    official_canonical_admitted: bool,
    reason: str | None,
    skip_reason: str | None,
    blockers: list[str],
    missing_classes: list[str],
    queries: list[str],
    provider_role: str | None,
    search_depth: str | None,
    attempt_count: int,
    action_envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "active_source_class_recovery_considered": considered,
        "active_source_class_recovery_eligible": eligible,
        "active_source_class_recovery_used": used,
        "active_source_class_recovery_execution_attempted": execution_attempted,
        "active_source_class_recovery_official_canonical_admitted": (
            official_canonical_admitted
        ),
        "active_source_class_recovery_reason": reason,
        "active_source_class_recovery_skip_reason": skip_reason,
        "active_source_class_recovery_blockers": list(blockers),
        "active_source_class_recovery_missing_classes": list(missing_classes),
        "active_source_class_recovery_queries": list(queries),
        "active_source_class_recovery_result_count": 0,
        "active_source_class_recovery_new_url_count": 0,
        "active_source_class_recovery_provider_role": provider_role,
        "active_source_class_recovery_search_depth": search_depth,
        "active_source_class_recovery_attempt_count": attempt_count,
        "active_source_class_recovery_action_envelope": dict(
            action_envelope or {}
        ),
        **recovery_source_quality_defaults(),
        **recovered_evidence_visibility_defaults(),
        **official_canonical_recovery_candidate_acquisition_defaults(),
    }


def record_source_class_recovery_lifecycle(
    controller: RunController,
    *,
    recommendation: Mapping[str, Any] | None,
    recommendation_evaluated: bool,
    source_class_evidence_signals: Mapping[str, Any],
    corpus_state: str | None,
    corpus_weak: bool,
    weak_corpus_recovery_considered: bool,
    weak_corpus_recovery_used: bool,
    weak_corpus_recovery_skip_reason: str | None,
    current_search_depth: str | None,
    iteration_budget_available: bool,
    answer_contract_source_class_slot_available: bool = False,
    official_canonical_source_class_slot_available: bool = False,
    provider_policy_reusable: bool = True,
    provider_swap_required: bool = False,
    search_depth_reusable: bool = True,
    search_depth_escalation_required: bool = False,
    retrieve_to_anchor_recommended: bool = False,
    pre_analyst_phase: bool = True,
    author_phase: bool = False,
) -> dict[str, Any]:
    """Record the source-class recovery controller lifecycle."""
    controller_input = build_source_class_recovery_controller_input(
        recommendation=recommendation,
        recommendation_evaluated=recommendation_evaluated,
        source_class_evidence_signals=source_class_evidence_signals,
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth=current_search_depth,
        iteration_budget_available=iteration_budget_available,
        prior_attempt_count=_prior_attempt_count(controller),
        answer_contract_source_class_slot_available=(
            answer_contract_source_class_slot_available
        ),
        official_canonical_source_class_slot_available=(
            official_canonical_source_class_slot_available
        ),
        provider_policy_reusable=provider_policy_reusable,
        provider_swap_required=provider_swap_required,
        search_depth_reusable=search_depth_reusable,
        search_depth_escalation_required=search_depth_escalation_required,
        retrieve_to_anchor_recommended=retrieve_to_anchor_recommended,
        pre_analyst_phase=pre_analyst_phase,
        author_phase=author_phase,
    )
    controller_decision = decide_source_class_recovery(controller_input)
    considered = controller_input.recommendation_evaluated
    eligible = controller_decision.approved
    missing_classes = list(controller_decision.missing_expected_source_classes)
    queries = list(controller_decision.queries)
    blockers = list(controller_decision.blockers)
    official_domains = _copy_domain_constraints(
        (recommendation or {}).get("source_class_recovery_official_domains")
    )
    attempt_count = controller_decision.attempt_count
    provider_role = controller_decision.provider_role
    search_depth = controller_decision.search_depth
    reason = controller_decision.reason
    skip_reason = None if eligible else controller_decision.reason
    trace_fields = _trace_payload(
        considered=considered,
        eligible=eligible,
        used=False,
        execution_attempted=False,
        official_canonical_admitted=bool(
            official_canonical_source_class_slot_available and eligible
        ),
        reason=reason,
        skip_reason=skip_reason,
        blockers=blockers,
        missing_classes=missing_classes,
        queries=queries,
        provider_role=provider_role,
        search_depth=search_depth,
        attempt_count=attempt_count,
        action_envelope=(
            controller_decision.action_envelope.to_dict()
            if controller_decision.action_envelope is not None
            else None
        ),
    )

    state = controller.state
    state.active_source_class_recovery_considered = considered
    state.active_source_class_recovery_eligible = eligible
    state.active_source_class_recovery_used = False
    state.active_source_class_recovery_execution_attempted = False
    state.active_source_class_recovery_reason = reason
    state.active_source_class_recovery_skip_reason = skip_reason
    state.active_source_class_recovery_blockers = list(blockers)
    state.active_source_class_recovery_missing_classes = list(missing_classes)
    state.active_source_class_recovery_queries = list(queries)
    state.active_source_class_recovery_result_count = 0
    state.active_source_class_recovery_new_url_count = 0
    state.active_source_class_recovery_provider_role = provider_role
    state.active_source_class_recovery_search_depth = search_depth
    state.active_source_class_recovery_attempt_count = attempt_count

    evidence_signals = _copy_evidence_signals(source_class_evidence_signals)
    state.corpus.state = corpus_state
    state.corpus.weak = bool(corpus_weak)
    state.corpus.signals.update(deepcopy(evidence_signals))
    state.corpus.metadata["source_class_recovery"] = {
        "missing_expected_source_classes": list(missing_classes),
        "source_class_recovery_queries": list(queries),
        "blockers": list(blockers),
    }

    signals = {
        "active_source_class_recovery_considered": considered,
        "active_source_class_recovery_eligible": eligible,
        "active_source_class_recovery_blockers": list(blockers),
        "active_source_class_recovery_missing_classes": list(missing_classes),
        "active_source_class_recovery_queries": list(queries),
        "weak_corpus_recovery_considered": bool(weak_corpus_recovery_considered),
        "weak_corpus_recovery_used": bool(weak_corpus_recovery_used),
        "weak_corpus_recovery_skip_reason": weak_corpus_recovery_skip_reason,
        "corpus_state": corpus_state,
        "corpus_weak": bool(corpus_weak),
        **evidence_signals,
    }
    if official_domains:
        signals["source_class_recovery_official_domains"] = list(official_domains)

    action: RetrievalAction | None = None
    if eligible:
        action_metadata: dict[str, Any] = {
            "execution": "controller_approved_pending_executor",
            "controller_decision": controller_decision.decision.value,
            "controller_action_envelope": trace_fields[
                "active_source_class_recovery_action_envelope"
            ],
            "result_count": 0,
            "new_url_count": 0,
        }
        if official_domains:
            action_metadata["official_domain_constraints"] = list(official_domains)
            action_metadata["official_domain_constraint_source"] = (
                "official_source_recovery_lane"
            )
        action = RetrievalAction(
            name="source_class_recovery",
            queries=list(queries),
            provider=None,
            provider_role=provider_role,
            search_depth=search_depth,
            results_per_query=None,
            active=True,
            shadow=False,
            reason=controller_decision.reason,
            signals=signals,
            metadata=action_metadata,
        )
        state.record_recovery_action(action)
        controller.record_retrieval_action(action)

    decision = ControllerDecision(
        name=controller_decision.decision.value,
        active=True,
        shadow=False,
        reason=controller_decision.reason,
        signals=signals,
        recommended_actions=[action] if action is not None else [],
        metadata={
            "execution": "minimal_active_controller",
            "decision": controller_decision.decision.value,
            "decision_contract": [
                item.value for item in SourceClassRecoveryControllerDecision
            ],
        },
    )
    controller.record_decision(decision)
    controller.ledger.record_fact(
        stage="source_class_recovery",
        name="skip_reason",
        value=skip_reason,
        metadata={
            "eligible": eligible,
            "blockers": list(blockers),
            "attempt_count": attempt_count,
        },
    )
    controller.ledger.record_fact(
        stage="source_class_recovery",
        name="attempt_count",
        value=attempt_count,
        metadata={"eligible": eligible},
    )

    return trace_fields


def source_class_recovery_lifecycle_defaults() -> dict[str, Any]:
    """Return the compact default execution_trace payload."""
    return _trace_payload(
        considered=False,
        eligible=False,
        used=False,
        execution_attempted=False,
        official_canonical_admitted=False,
        reason="not_evaluated",
        skip_reason="not_evaluated",
        blockers=["not_evaluated"],
        missing_classes=[],
        queries=[],
        provider_role=None,
        search_depth=None,
        attempt_count=0,
        action_envelope={
            "action_type": "recover_missing_source_class",
            "required_source_class": [],
            "obligation_status": "unknown",
            "recovery_reason": "not_evaluated",
            "current_evidence_status": "unknown",
            "allowed_action": False,
            "budget_attempt_context": {
                "attempt_count": 0,
                "current_search_depth": None,
                "provider_role": None,
                "iteration_budget_available": False,
                "answer_contract_source_class_slot_available": False,
                "official_canonical_source_class_slot_available": False,
            },
            "blockers": ["not_evaluated"],
            "stop_posture_if_unmet": None,
            "trace_safe_summary": (
                "Controller did not evaluate missing-source-class recovery."
            ),
        },
    )


__all__ = [
    "ACTIVE_SOURCE_CLASS_RECOVERY_TRACE_FIELDS",
    "SOURCE_CLASS_LIFECYCLE_EVIDENCE_SIGNAL_KEYS",
    "record_source_class_recovery_lifecycle",
    "source_class_recovery_lifecycle_defaults",
]
