"""Pure evidence-integration checkpoint for AG-32.

The checkpoint is a shadow-only future dispatcher seam. It accepts a compact
post-retrieval snapshot and recommends exactly one AG-25 next action without
executing that action, calling providers, changing retrieval, or touching
persistence.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.controller_action_envelope import (
    ASK_USER_CLARIFICATION,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    action_can_satisfy_evidence_class,
    controller_action_names,
)
from core.controller_budget_semantics import MarginalValueLevel
from core.controller_state_reducer import (
    ControllerBudgetClass,
    ControllerEvidenceBoundary,
)

EVIDENCE_INTEGRATION_SNAPSHOT_SCHEMA_VERSION = (
    "evidence_integration_snapshot_ag32_v1"
)
EVIDENCE_INTEGRATION_DECISION_SCHEMA_VERSION = (
    "evidence_integration_decision_ag32_v1"
)
EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_SCHEMA_VERSION = (
    "evidence_integration_checkpoint_shadow_ag32_v1"
)
EVIDENCE_INTEGRATION_HANDOFF_SCHEMA_VERSION = (
    "evidence_integration_checkpoint_handoff_ag32_v1"
)
EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY = (
    "evidence_integration_checkpoint_shadow"
)

EVIDENCE_INTEGRATION_ACTION_NAMES = (
    STOP_SUFFICIENT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    RETRIEVE_TARGETED,
    RECOVER_WEAK_CORPUS,
    RECOVER_MISSING_SOURCE_CLASS,
    RESOLVE_CONFLICT,
    ASK_USER_CLARIFICATION,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RUN_SCRUTINEER_REVIEW,
)

EVIDENCE_INTEGRATION_PROMOTION_CRITERIA = (
    "promote when AG-32/next phase makes this checkpoint the active dispatcher "
    "gate after post-retrieval evidence integration",
)
EVIDENCE_INTEGRATION_DELETION_CRITERIA = (
    "delete or collapse if the next runtime-promotion phase does not consume "
    "the checkpoint as an active gate or answer-contract handoff input",
)

_SENSITIVE_KEYS = {
    "api_key",
    "cache",
    "db_row",
    "full_trace",
    "password",
    "prompt",
    "provider_payload",
    "raw_comments",
    "raw_evidence",
    "raw_handles",
    "raw_ids",
    "raw_packet",
    "raw_provider_payload",
    "raw_prompt",
    "secret",
    "token",
}
_PROTECTED_VALUE_MARKERS = (
    "raw prompt",
    "raw_provider",
    "raw evidence",
    "provider_payload",
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "economist_v1",
)
_CHECKPOINT_CONSUMERS = (
    "parity_assertion",
    "answer_contract_fulfillment_handoff",
)
_STOP_ACTIONS = {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}
_RETRIEVAL_ACTIONS = {
    RETRIEVE_TARGETED,
    RECOVER_WEAK_CORPUS,
    RECOVER_MISSING_SOURCE_CLASS,
    RESOLVE_CONFLICT,
}
_SOURCE_CLASS_BLOCKERS = {
    "already_attempted",
    "blocked_by_weak_corpus_recovery",
    "blocked_by_corpus_weak",
    "blocked_by_iteration_budget",
    "blocked_by_provider_policy_change_required",
    "blocked_by_search_depth_escalation_required",
    "blocked_by_retrieve_to_anchor_recommendation",
    "blocked_by_author_phase",
    "blocked_by_post_analyst_phase",
    "no_recovery_queries",
}
_SCRUTINEER_ALLOWED_MODES = {"deep", "scrutineer", "review"}
_SOCIAL_SATISFIED_STATUSES = {"checked", "not_applicable"}


class EvidenceIntegrationExpectedValue(str, Enum):
    """Stable qualitative expected-value vocabulary for the checkpoint."""

    NONE = MarginalValueLevel.NONE.value
    LOW = MarginalValueLevel.LOW.value
    MEDIUM = MarginalValueLevel.MEDIUM.value
    HIGH = MarginalValueLevel.HIGH.value


@dataclass(frozen=True)
class EvidenceIntegrationBudgetSnapshot:
    """Compact AG-31-shaped budget facts used by the checkpoint."""

    mode: str | None = None
    iteration: int = 0
    max_iterations: int = 0
    retrieval_action_budget_remaining: int = 0
    targeted_retrieval_remaining: int = 0
    weak_corpus_recovery_remaining: int = 0
    source_class_recovery_remaining: int = 0
    conflict_resolution_remaining: int = 0
    social_side_packet_placeholder_remaining: int = 0
    scrutineer_review_allowed: bool = False
    clarification_allowed: bool = True
    low_value_stop_recommended: bool = False
    live_call_placeholder_remaining: int = 0
    protected_provider_depth_routing_boundary: bool = True

    @classmethod
    def from_runtime(
        cls,
        *,
        mode: str | None,
        iteration: int,
        max_iterations: int,
        weak_corpus_recovery_used: bool = False,
        weak_corpus_recovery_attempted: bool = False,
        source_class_recovery_attempt_count: int = 0,
        source_class_slot_available: bool = False,
        conflict_resolution_attempt_count: int = 0,
        social_side_packet_placeholder_allowed: bool = False,
        scrutineer_review_allowed: bool = False,
        clarification_allowed: bool = True,
        low_value_stop_recommended: bool = False,
    ) -> "EvidenceIntegrationBudgetSnapshot":
        """Build budget facts from already-computed runtime counters."""

        iter_value = max(0, int(iteration or 0))
        max_iter_value = max(0, int(max_iterations or 0))
        main_remaining = max(0, max_iter_value - iter_value)
        source_remaining = (
            0
            if int(source_class_recovery_attempt_count or 0) > 0
            else 1
            if source_class_slot_available
            else main_remaining
        )
        weak_attempted = bool(weak_corpus_recovery_used or weak_corpus_recovery_attempted)
        weak_remaining = 0 if weak_attempted else main_remaining
        conflict_remaining = (
            0
            if int(conflict_resolution_attempt_count or 0) > 0
            else main_remaining
        )
        retrieval_remaining = max(main_remaining, source_remaining)
        return cls(
            mode=_clean_text(mode, limit=80),
            iteration=iter_value,
            max_iterations=max_iter_value,
            retrieval_action_budget_remaining=retrieval_remaining,
            targeted_retrieval_remaining=main_remaining,
            weak_corpus_recovery_remaining=weak_remaining,
            source_class_recovery_remaining=source_remaining,
            conflict_resolution_remaining=conflict_remaining,
            social_side_packet_placeholder_remaining=(
                1 if social_side_packet_placeholder_allowed else 0
            ),
            scrutineer_review_allowed=bool(scrutineer_review_allowed),
            clarification_allowed=bool(clarification_allowed),
            low_value_stop_recommended=bool(low_value_stop_recommended),
            live_call_placeholder_remaining=0,
        )

    def remaining_for_action(self, action_name: str) -> int:
        """Return the remaining bounded allowance for one AG-25 action."""

        if action_name == RETRIEVE_TARGETED:
            return min(
                self.retrieval_action_budget_remaining,
                self.targeted_retrieval_remaining,
            )
        if action_name == RECOVER_WEAK_CORPUS:
            return min(
                self.retrieval_action_budget_remaining,
                self.weak_corpus_recovery_remaining,
            )
        if action_name == RECOVER_MISSING_SOURCE_CLASS:
            return min(
                self.retrieval_action_budget_remaining,
                self.source_class_recovery_remaining,
            )
        if action_name == RESOLVE_CONFLICT:
            return min(
                self.retrieval_action_budget_remaining,
                self.conflict_resolution_remaining,
            )
        if action_name == REQUEST_SOCIAL_SIGNAL_CHECK:
            return self.social_side_packet_placeholder_remaining
        if action_name == RUN_SCRUTINEER_REVIEW:
            return 1 if self.scrutineer_review_allowed else 0
        if action_name == ASK_USER_CLARIFICATION:
            return 1 if self.clarification_allowed else 0
        if action_name in _STOP_ACTIONS:
            return 1
        return 0

    @property
    def retrieval_budget_exhausted(self) -> bool:
        return all(
            self.remaining_for_action(action_name) <= 0
            for action_name in _RETRIEVAL_ACTIONS
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "iteration": max(0, int(self.iteration or 0)),
            "max_iterations": max(0, int(self.max_iterations or 0)),
            "remaining": {
                "retrieval_action_budget_remaining": max(
                    0,
                    int(self.retrieval_action_budget_remaining or 0),
                ),
                "targeted_retrieval_remaining": max(
                    0,
                    int(self.targeted_retrieval_remaining or 0),
                ),
                "weak_corpus_recovery_remaining": max(
                    0,
                    int(self.weak_corpus_recovery_remaining or 0),
                ),
                "source_class_recovery_remaining": max(
                    0,
                    int(self.source_class_recovery_remaining or 0),
                ),
                "conflict_resolution_remaining": max(
                    0,
                    int(self.conflict_resolution_remaining or 0),
                ),
                "social_side_packet_placeholder_remaining": max(
                    0,
                    int(self.social_side_packet_placeholder_remaining or 0),
                ),
                "live_call_placeholder_remaining": max(
                    0,
                    int(self.live_call_placeholder_remaining or 0),
                ),
            },
            "budget_classes": [
                ControllerBudgetClass.RETRIEVAL_ITERATION.value,
                ControllerBudgetClass.WEAK_CORPUS_RECOVERY.value,
                ControllerBudgetClass.SOURCE_CLASS_RECOVERY.value,
                ControllerBudgetClass.SOCIAL_SIDE_PACKET.value,
                ControllerBudgetClass.LIVE_CALL.value,
            ],
            "scrutineer_review_allowed": bool(self.scrutineer_review_allowed),
            "clarification_allowed": bool(self.clarification_allowed),
            "low_value_stop_recommended": bool(self.low_value_stop_recommended),
            "protected_provider_depth_routing_boundary": bool(
                self.protected_provider_depth_routing_boundary
            ),
        }


@dataclass(frozen=True)
class EvidenceIntegrationSnapshot:
    """Sanitized post-retrieval evidence-integration checkpoint input."""

    contract_family: str
    contract_must_satisfy: tuple[str, ...] = ()
    contract_should_satisfy: tuple[str, ...] = ()
    required_source_classes: tuple[str, ...] = ()
    fulfilled_contract_items: tuple[str, ...] = ()
    partial_contract_items: tuple[str, ...] = ()
    unfulfilled_contract_items: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    evidence_available: bool = False
    evidence_sufficient: bool = False
    evidence_reference_count: int = 0
    source_classes_present: tuple[str, ...] = ()
    source_classes_missing: tuple[str, ...] = ()
    weak_corpus: bool = False
    weak_corpus_reason: str | None = None
    weak_corpus_recovery_used: bool = False
    weak_corpus_recovery_available: bool = False
    source_class_recovery_recommended: bool = False
    source_class_recovery_eligible: bool = False
    source_class_recovery_missing_classes: tuple[str, ...] = ()
    source_class_recovery_queries_available: bool = False
    source_class_recovery_blockers: tuple[str, ...] = ()
    conflicts_present: bool = False
    conflict_notes: tuple[str, ...] = ()
    conflict_resolution_available: bool = False
    next_queries_available: bool = False
    next_query_redundant: bool = False
    prior_query_count: int = 0
    next_query_count: int = 0
    clarification_needed: bool = False
    social_signal_requested: bool = False
    social_signal_status: str | None = None
    social_side_packet_placeholder_allowed: bool = False
    scrutineer_requested: bool = False
    scrutineer_needed: bool = False
    scrutineer_allowed_by_mode: bool = False
    scrutineer_allowed_by_contract: bool = False
    budget: EvidenceIntegrationBudgetSnapshot = field(
        default_factory=EvidenceIntegrationBudgetSnapshot
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_INTEGRATION_SNAPSHOT_SCHEMA_VERSION,
            "contract_family": _clean_text(self.contract_family, limit=80),
            "contract_must_satisfy": list(
                _copy_string_tuple(self.contract_must_satisfy)
            ),
            "contract_should_satisfy": list(
                _copy_string_tuple(self.contract_should_satisfy)
            ),
            "required_source_classes": list(
                _copy_string_tuple(self.required_source_classes)
            ),
            "contract_fulfillment": {
                "fulfilled": list(_copy_string_tuple(self.fulfilled_contract_items)),
                "partial": list(_copy_string_tuple(self.partial_contract_items)),
                "unfulfilled": list(
                    _copy_string_tuple(self.unfulfilled_contract_items)
                ),
                "missing_information": list(
                    _copy_string_tuple(self.missing_information)
                ),
            },
            "evidence": {
                "available": bool(self.evidence_available),
                "sufficient": bool(self.evidence_sufficient),
                "reference_count": max(0, int(self.evidence_reference_count or 0)),
                "source_classes_present": list(
                    _copy_string_tuple(self.source_classes_present)
                ),
                "source_classes_missing": list(
                    _copy_string_tuple(self.source_classes_missing)
                ),
            },
            "weak_corpus": {
                "active": bool(self.weak_corpus),
                "reason": _clean_text(self.weak_corpus_reason, limit=160),
                "recovery_used": bool(self.weak_corpus_recovery_used),
                "recovery_available": bool(self.weak_corpus_recovery_available),
            },
            "source_class_state": {
                "recovery_recommended": bool(
                    self.source_class_recovery_recommended
                ),
                "recovery_eligible": bool(self.source_class_recovery_eligible),
                "missing_classes": list(
                    _copy_string_tuple(self.source_class_recovery_missing_classes)
                ),
                "queries_available": bool(
                    self.source_class_recovery_queries_available
                ),
                "blockers": list(
                    _copy_string_tuple(self.source_class_recovery_blockers)
                ),
            },
            "conflicts": {
                "present": bool(self.conflicts_present),
                "notes": list(_copy_string_tuple(self.conflict_notes)),
                "resolution_available": bool(self.conflict_resolution_available),
            },
            "targeted_retrieval": {
                "next_queries_available": bool(self.next_queries_available),
                "next_query_redundant": bool(self.next_query_redundant),
                "prior_query_count": max(0, int(self.prior_query_count or 0)),
                "next_query_count": max(0, int(self.next_query_count or 0)),
            },
            "clarification_needed": bool(self.clarification_needed),
            "social_signal": {
                "requested": bool(self.social_signal_requested),
                "status": _clean_text(self.social_signal_status, limit=80),
                "side_packet_placeholder_allowed": bool(
                    self.social_side_packet_placeholder_allowed
                ),
                "ordinary_evidence_allowed": False,
                "evidence_boundary": (
                    ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value
                ),
            },
            "scrutineer": {
                "requested": bool(self.scrutineer_requested),
                "needed": bool(self.scrutineer_needed),
                "allowed_by_mode": bool(self.scrutineer_allowed_by_mode),
                "allowed_by_contract": bool(self.scrutineer_allowed_by_contract),
            },
            "budget": self.budget.to_dict(),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceIntegrationDecision:
    """Exactly one AG-25 action recommendation from the checkpoint."""

    action_name: str
    reason: str
    contract_gap_addressed: str | None
    expected_value: EvidenceIntegrationExpectedValue
    budget_rationale: str
    blocked_or_skipped_action_rationale: Mapping[str, str]
    evidence_boundary: ControllerEvidenceBoundary
    side_packet_placeholder_only: bool = False
    ordinary_evidence_allowed: bool = True
    action_executed: bool = False
    shadow_mode: bool = True
    runtime_behavior_changed: bool = False
    consumers: tuple[str, ...] = _CHECKPOINT_CONSUMERS
    promotion_criteria: tuple[str, ...] = EVIDENCE_INTEGRATION_PROMOTION_CRITERIA
    deletion_criteria: tuple[str, ...] = EVIDENCE_INTEGRATION_DELETION_CRITERIA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_INTEGRATION_DECISION_SCHEMA_VERSION,
            "action_name": self.action_name,
            "reason": _clean_text(self.reason, limit=260),
            "contract_gap_addressed": _clean_text(
                self.contract_gap_addressed,
                limit=180,
            ),
            "expected_value": self.expected_value.value,
            "budget_rationale": _clean_text(self.budget_rationale, limit=260),
            "blocked_or_skipped_action_rationale": _json_safe(
                dict(self.blocked_or_skipped_action_rationale)
            ),
            "evidence_boundary": self.evidence_boundary.value,
            "side_packet_placeholder_only": bool(self.side_packet_placeholder_only),
            "ordinary_evidence_allowed": bool(self.ordinary_evidence_allowed),
            "action_executed": bool(self.action_executed),
            "shadow_mode": bool(self.shadow_mode),
            "runtime_behavior_changed": bool(self.runtime_behavior_changed),
            "consumers": list(_copy_string_tuple(self.consumers)),
            "promotion_criteria": list(_copy_string_tuple(self.promotion_criteria)),
            "deletion_criteria": list(_copy_string_tuple(self.deletion_criteria)),
        }

    def to_handoff_reference(self) -> dict[str, Any]:
        """Return the compact answer-contract handoff reference."""

        return {
            "schema_version": EVIDENCE_INTEGRATION_HANDOFF_SCHEMA_VERSION,
            "action_name": self.action_name,
            "reason": _clean_text(self.reason, limit=180),
            "contract_gap_addressed": _clean_text(
                self.contract_gap_addressed,
                limit=140,
            ),
            "expected_value": self.expected_value.value,
            "budget_rationale": _clean_text(self.budget_rationale, limit=180),
            "side_packet_placeholder_only": bool(self.side_packet_placeholder_only),
            "ordinary_evidence_allowed": bool(self.ordinary_evidence_allowed),
            "shadow_mode": True,
            "runtime_behavior_changed": False,
            "consumer": "answer_contract_fulfillment_handoff",
            "promotion_criteria": EVIDENCE_INTEGRATION_PROMOTION_CRITERIA[0],
            "deletion_criteria": EVIDENCE_INTEGRATION_DELETION_CRITERIA[0],
        }


def decide_evidence_integration_checkpoint(
    snapshot: EvidenceIntegrationSnapshot | Mapping[str, Any],
) -> EvidenceIntegrationDecision:
    """Return exactly one shadow-only AG-25 action recommendation."""

    state = coerce_evidence_integration_snapshot(snapshot)

    if _can_stop_sufficient(state):
        return _decision(
            state,
            STOP_SUFFICIENT,
            reason="central_contract_obligations_satisfied",
            gap=None,
            expected_value=EvidenceIntegrationExpectedValue.HIGH,
            boundary=ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY,
        )

    if _budget_forces_caveat(state):
        return _decision(
            state,
            STOP_INSUFFICIENT_WITH_CAVEAT,
            reason="retrieval_budget_exhausted_or_low_value",
            gap=_central_gap_label(state),
            expected_value=EvidenceIntegrationExpectedValue.MEDIUM,
            boundary=ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY,
        )

    if state.conflicts_present and state.conflict_resolution_available:
        return _decision(
            state,
            RESOLVE_CONFLICT,
            reason="material_conflict_requires_resolution",
            gap=_first_text(state.conflict_notes, "conflicting evidence"),
            expected_value=EvidenceIntegrationExpectedValue.HIGH,
            boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
        )

    if _source_class_recovery_should_run(state):
        return _decision(
            state,
            RECOVER_MISSING_SOURCE_CLASS,
            reason="missing_required_source_class",
            gap=_first_text(
                state.source_class_recovery_missing_classes
                or state.source_classes_missing
                or state.required_source_classes,
                "required source class",
            ),
            expected_value=EvidenceIntegrationExpectedValue.HIGH,
            boundary=(
                ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE
            ),
        )

    if state.weak_corpus and state.weak_corpus_recovery_available:
        return _decision(
            state,
            RECOVER_WEAK_CORPUS,
            reason="weak_corpus_recovery_available",
            gap=state.weak_corpus_reason or "weak evidence corpus",
            expected_value=EvidenceIntegrationExpectedValue.HIGH,
            boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
        )

    if _social_signal_should_request(state):
        return _decision(
            state,
            REQUEST_SOCIAL_SIGNAL_CHECK,
            reason="social_signal_future_side_packet_only",
            gap="social_signal",
            expected_value=EvidenceIntegrationExpectedValue.MEDIUM,
            boundary=ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE,
            side_packet=True,
            ordinary_evidence_allowed=False,
        )

    if state.scrutineer_needed or state.scrutineer_requested:
        if state.scrutineer_allowed_by_mode and state.scrutineer_allowed_by_contract:
            return _decision(
                state,
                RUN_SCRUTINEER_REVIEW,
                reason="scrutineer_allowed_by_mode_and_contract",
                gap="review-sensitive answer contract",
                expected_value=EvidenceIntegrationExpectedValue.MEDIUM,
                boundary=ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY,
                ordinary_evidence_allowed=False,
            )

    if state.clarification_needed:
        return _decision(
            state,
            ASK_USER_CLARIFICATION,
            reason="clarification_needed_for_contract_fulfillment",
            gap=_central_gap_label(state),
            expected_value=EvidenceIntegrationExpectedValue.MEDIUM,
            boundary=ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY,
            ordinary_evidence_allowed=False,
        )

    if _targeted_retrieval_should_run(state):
        return _decision(
            state,
            RETRIEVE_TARGETED,
            reason="central_gap_with_targeted_queries_available",
            gap=_central_gap_label(state),
            expected_value=EvidenceIntegrationExpectedValue.MEDIUM,
            boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
        )

    return _decision(
        state,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        reason="remaining_gap_better_carried_as_caveat",
        gap=_central_gap_label(state),
        expected_value=EvidenceIntegrationExpectedValue.LOW,
        boundary=ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY,
    )


def coerce_evidence_integration_snapshot(
    snapshot: EvidenceIntegrationSnapshot | Mapping[str, Any],
) -> EvidenceIntegrationSnapshot:
    """Coerce mapping fixtures into the AG-32 snapshot shape."""

    if isinstance(snapshot, EvidenceIntegrationSnapshot):
        return snapshot
    if not isinstance(snapshot, Mapping):
        raise TypeError("evidence integration checkpoint requires a snapshot mapping")

    budget_value = snapshot.get("budget")
    if isinstance(budget_value, EvidenceIntegrationBudgetSnapshot):
        budget = budget_value
    elif isinstance(budget_value, Mapping):
        remaining = budget_value.get("remaining")
        source = remaining if isinstance(remaining, Mapping) else budget_value
        budget = EvidenceIntegrationBudgetSnapshot(
            mode=_clean_text(budget_value.get("mode"), limit=80),
            iteration=_int_value(budget_value.get("iteration")),
            max_iterations=_int_value(budget_value.get("max_iterations")),
            retrieval_action_budget_remaining=_int_value(
                source.get("retrieval_action_budget_remaining")
            ),
            targeted_retrieval_remaining=_int_value(
                source.get("targeted_retrieval_remaining")
            ),
            weak_corpus_recovery_remaining=_int_value(
                source.get("weak_corpus_recovery_remaining")
            ),
            source_class_recovery_remaining=_int_value(
                source.get("source_class_recovery_remaining")
            ),
            conflict_resolution_remaining=_int_value(
                source.get("conflict_resolution_remaining")
            ),
            social_side_packet_placeholder_remaining=_int_value(
                source.get("social_side_packet_placeholder_remaining")
            ),
            scrutineer_review_allowed=bool(
                budget_value.get("scrutineer_review_allowed")
            ),
            clarification_allowed=bool(
                budget_value.get("clarification_allowed", True)
            ),
            low_value_stop_recommended=bool(
                budget_value.get("low_value_stop_recommended")
            ),
            live_call_placeholder_remaining=_int_value(
                source.get("live_call_placeholder_remaining")
            ),
            protected_provider_depth_routing_boundary=bool(
                budget_value.get("protected_provider_depth_routing_boundary", True)
            ),
        )
    else:
        budget = EvidenceIntegrationBudgetSnapshot()

    kwargs = {
        field_name: snapshot[field_name]
        for field_name in EvidenceIntegrationSnapshot.__dataclass_fields__
        if field_name in snapshot and field_name not in {"budget", "metadata"}
    }
    return EvidenceIntegrationSnapshot(
        **kwargs,
        budget=budget,
        metadata=_mapping(snapshot.get("metadata")),
    )


def build_evidence_integration_checkpoint_trace(
    *,
    snapshot: EvidenceIntegrationSnapshot,
    decision: EvidenceIntegrationDecision,
    legacy_runtime_branch: str | None = None,
) -> dict[str, Any]:
    """Return the compact trace packet consumed by parity assertions."""

    return {
        "schema_version": EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_SCHEMA_VERSION,
        "available": True,
        "shadow_mode": True,
        "runtime_behavior_changed": False,
        "action_executed": False,
        "legacy_runtime_branch": _clean_text(legacy_runtime_branch, limit=120),
        "snapshot": snapshot.to_dict(),
        "decision": decision.to_dict(),
        "recommended_action_name": decision.action_name,
        "consumers": list(_CHECKPOINT_CONSUMERS),
        "promotion_criteria": list(EVIDENCE_INTEGRATION_PROMOTION_CRITERIA),
        "deletion_criteria": list(EVIDENCE_INTEGRATION_DELETION_CRITERIA),
    }


def evidence_integration_checkpoint_unavailable_trace(reason: str) -> dict[str, Any]:
    """Return a compact non-fatal unavailable packet."""

    return {
        "schema_version": EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_SCHEMA_VERSION,
        "available": False,
        "shadow_mode": True,
        "runtime_behavior_changed": False,
        "action_executed": False,
        "reason": _clean_text(reason, limit=160) or "checkpoint_unavailable",
        "consumers": ["parity_assertion"],
        "promotion_criteria": list(EVIDENCE_INTEGRATION_PROMOTION_CRITERIA),
        "deletion_criteria": list(EVIDENCE_INTEGRATION_DELETION_CRITERIA),
    }


def _decision(
    state: EvidenceIntegrationSnapshot,
    action_name: str,
    *,
    reason: str,
    gap: str | None,
    expected_value: EvidenceIntegrationExpectedValue,
    boundary: ControllerEvidenceBoundary,
    side_packet: bool = False,
    ordinary_evidence_allowed: bool = True,
) -> EvidenceIntegrationDecision:
    _validate_single_action(action_name)
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=reason,
        contract_gap_addressed=gap,
        expected_value=expected_value,
        budget_rationale=_budget_rationale(state, action_name),
        blocked_or_skipped_action_rationale=_blocked_or_skipped_rationales(
            state,
            selected_action=action_name,
        ),
        evidence_boundary=boundary,
        side_packet_placeholder_only=side_packet,
        ordinary_evidence_allowed=ordinary_evidence_allowed,
    )


def _validate_single_action(action_name: str) -> None:
    if action_name not in EVIDENCE_INTEGRATION_ACTION_NAMES:
        raise ValueError(f"unsupported AG-32 evidence action: {action_name}")
    if action_name not in controller_action_names():
        raise ValueError(f"action is not registered in AG-25: {action_name}")


def _can_stop_sufficient(state: EvidenceIntegrationSnapshot) -> bool:
    return (
        state.evidence_sufficient
        and not state.unfulfilled_contract_items
        and not state.partial_contract_items
        and not state.source_classes_missing
        and not state.weak_corpus
        and not state.conflicts_present
    )


def _budget_forces_caveat(state: EvidenceIntegrationSnapshot) -> bool:
    if state.budget.low_value_stop_recommended:
        return True
    if not _has_material_gap(state):
        return False
    return state.budget.retrieval_budget_exhausted and not (
        _social_signal_should_request(state)
        or (
            state.scrutineer_needed
            and state.scrutineer_allowed_by_mode
            and state.scrutineer_allowed_by_contract
        )
        or state.clarification_needed
    )


def _source_class_recovery_should_run(state: EvidenceIntegrationSnapshot) -> bool:
    if not state.source_class_recovery_eligible:
        return False
    blockers = set(_copy_string_tuple(state.source_class_recovery_blockers))
    if blockers & _SOURCE_CLASS_BLOCKERS:
        return False
    return (
        state.budget.remaining_for_action(RECOVER_MISSING_SOURCE_CLASS) > 0
        and (
            state.source_class_recovery_queries_available
            or bool(state.source_class_recovery_missing_classes)
            or bool(state.source_classes_missing)
        )
    )


def _social_signal_should_request(state: EvidenceIntegrationSnapshot) -> bool:
    status = str(state.social_signal_status or "").casefold()
    if not state.social_signal_requested or status in _SOCIAL_SATISFIED_STATUSES:
        return False
    if not state.social_side_packet_placeholder_allowed:
        return False
    if state.budget.remaining_for_action(REQUEST_SOCIAL_SIGNAL_CHECK) <= 0:
        return False
    return action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "social_signal_side_packet",
    )


def _targeted_retrieval_should_run(state: EvidenceIntegrationSnapshot) -> bool:
    return (
        _has_material_gap(state)
        and state.next_queries_available
        and not state.next_query_redundant
        and state.budget.remaining_for_action(RETRIEVE_TARGETED) > 0
    )


def _has_material_gap(state: EvidenceIntegrationSnapshot) -> bool:
    return bool(
        state.unfulfilled_contract_items
        or state.partial_contract_items
        or state.missing_information
        or state.source_classes_missing
        or state.weak_corpus
        or state.conflicts_present
        or state.clarification_needed
        or (state.social_signal_requested and not _social_signal_satisfied(state))
        or state.scrutineer_needed
    )


def _social_signal_satisfied(state: EvidenceIntegrationSnapshot) -> bool:
    return str(state.social_signal_status or "").casefold() in _SOCIAL_SATISFIED_STATUSES


def _budget_rationale(
    state: EvidenceIntegrationSnapshot,
    action_name: str,
) -> str:
    remaining = state.budget.remaining_for_action(action_name)
    if action_name in _STOP_ACTIONS:
        if state.budget.low_value_stop_recommended:
            return (
                "AG-31-style marginal value is low; stop posture spends no "
                "retrieval reserve."
            )
        return "Stop posture spends no retrieval reserve."
    if action_name == REQUEST_SOCIAL_SIGNAL_CHECK:
        return (
            "Social signal has side-packet placeholder remaining="
            f"{remaining}; ordinary evidence merge remains blocked."
        )
    if action_name == RUN_SCRUTINEER_REVIEW:
        return (
            "Scrutineer review is allowed by supplied mode/contract flags and "
            "spends no retrieval reserve."
            if remaining > 0
            else "Scrutineer review is blocked by mode or contract flags."
        )
    if action_name == ASK_USER_CLARIFICATION:
        return "Clarification spends no retrieval reserve."
    return (
        "AG-31-style bounded allowance for "
        f"{action_name} is {remaining}; provider and depth routing remain "
        "orchestrator-owned."
    )


def _blocked_or_skipped_rationales(
    state: EvidenceIntegrationSnapshot,
    *,
    selected_action: str,
) -> dict[str, str]:
    rationales: dict[str, str] = {}
    for action_name in EVIDENCE_INTEGRATION_ACTION_NAMES:
        if action_name == selected_action:
            continue
        rationales[action_name] = _skip_reason_for_action(state, action_name)
    return rationales


def _skip_reason_for_action(
    state: EvidenceIntegrationSnapshot,
    action_name: str,
) -> str:
    remaining = state.budget.remaining_for_action(action_name)
    if action_name == STOP_SUFFICIENT:
        return (
            "selected_action_more_specific"
            if _can_stop_sufficient(state)
            else "central_gap_or_conflict_remains"
        )
    if action_name == STOP_INSUFFICIENT_WITH_CAVEAT:
        return (
            "selected_action_more_specific"
            if _has_material_gap(state)
            else "insufficient_caveat_not_needed"
        )
    if action_name == RESOLVE_CONFLICT:
        if not state.conflicts_present:
            return "no_material_conflict"
        if remaining <= 0:
            return "conflict_resolution_budget_unavailable"
        return "lower_priority_than_selected_action"
    if action_name == RECOVER_MISSING_SOURCE_CLASS:
        if not (state.source_classes_missing or state.source_class_recovery_recommended):
            return "no_missing_required_source_class"
        if state.source_class_recovery_blockers:
            return "blocked:" + ",".join(
                _copy_string_tuple(state.source_class_recovery_blockers)
            )
        if remaining <= 0:
            return "source_class_recovery_budget_unavailable"
        return "lower_priority_than_selected_action"
    if action_name == RECOVER_WEAK_CORPUS:
        if not state.weak_corpus:
            return "corpus_not_marked_weak"
        if state.weak_corpus_recovery_used:
            return "weak_corpus_recovery_already_used"
        if remaining <= 0:
            return "weak_corpus_recovery_budget_unavailable"
        return "lower_priority_than_selected_action"
    if action_name == RETRIEVE_TARGETED:
        if not state.next_queries_available:
            return "no_targeted_queries_available"
        if state.next_query_redundant:
            return "targeted_queries_redundant"
        if remaining <= 0:
            return "targeted_retrieval_budget_unavailable"
        return "lower_priority_than_selected_action"
    if action_name == ASK_USER_CLARIFICATION:
        if not state.clarification_needed:
            return "clarification_not_needed"
        if remaining <= 0:
            return "clarification_not_allowed"
        return "lower_priority_than_selected_action"
    if action_name == REQUEST_SOCIAL_SIGNAL_CHECK:
        if not state.social_signal_requested:
            return "social_signal_not_requested"
        if _social_signal_satisfied(state):
            return "social_signal_already_satisfied_or_not_applicable"
        if not state.social_side_packet_placeholder_allowed or remaining <= 0:
            return "future_side_packet_placeholder_unavailable"
        return "side_packet_only_not_ordinary_evidence"
    if action_name == RUN_SCRUTINEER_REVIEW:
        if not (state.scrutineer_needed or state.scrutineer_requested):
            return "scrutineer_not_needed"
        if not state.scrutineer_allowed_by_mode:
            return "blocked_by_mode"
        if not state.scrutineer_allowed_by_contract:
            return "blocked_by_contract"
        return "lower_priority_than_selected_action"
    return "unsupported_action"


def _central_gap_label(state: EvidenceIntegrationSnapshot) -> str | None:
    return _first_text(
        (
            state.unfulfilled_contract_items
            or state.partial_contract_items
            or state.missing_information
            or state.source_classes_missing
            or state.required_source_classes
        ),
        None,
    )


def _first_text(values: Sequence[Any], default: str | None) -> str | None:
    cleaned = _copy_string_tuple(values)
    return cleaned[0] if cleaned else default


def _copy_string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = _clean_text(item, limit=220)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_VALUE_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=260)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value, key=lambda item: str(item)):
            if _is_sensitive_key(key):
                continue
            out[str(key)] = _json_safe(value[key])
        return out
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    return _clean_text(value, limit=260)


def _mapping(value: Any) -> dict[str, Any]:
    return deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "EVIDENCE_INTEGRATION_ACTION_NAMES",
    "EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY",
    "EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_SCHEMA_VERSION",
    "EVIDENCE_INTEGRATION_DECISION_SCHEMA_VERSION",
    "EVIDENCE_INTEGRATION_DELETION_CRITERIA",
    "EVIDENCE_INTEGRATION_HANDOFF_SCHEMA_VERSION",
    "EVIDENCE_INTEGRATION_PROMOTION_CRITERIA",
    "EVIDENCE_INTEGRATION_SNAPSHOT_SCHEMA_VERSION",
    "EvidenceIntegrationBudgetSnapshot",
    "EvidenceIntegrationDecision",
    "EvidenceIntegrationExpectedValue",
    "EvidenceIntegrationSnapshot",
    "build_evidence_integration_checkpoint_trace",
    "coerce_evidence_integration_snapshot",
    "decide_evidence_integration_checkpoint",
    "evidence_integration_checkpoint_unavailable_trace",
]
