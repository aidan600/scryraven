"""Pure offline controller budget semantics and marginal-value action gate.

AG-31 separates mode-owned hard ceilings from passive controller allocation
decisions. The gate recommends whether one more bounded AG-25 action is worth
spending, skipping, or stopping. It does not execute retrieval, call providers,
alter prompts, persist data, or change runtime search behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping

from core.controller_action_envelope import (
    ASK_USER_CLARIFICATION,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    action_can_satisfy_evidence_class,
    controller_action_names,
)
from core.controller_state_reducer import (
    ControllerBudgetClass,
    controller_budget_descriptors,
)
from core.mode_policy import ModePolicy, RunMode, mode_policy_for

CONTROLLER_BUDGET_STATE_SCHEMA_VERSION = "controller_budget_state_ag31_v1"
CONTROLLER_BUDGET_ACTION_GATE_SCHEMA_VERSION = (
    "controller_budget_action_gate_ag31_v1"
)

SUPPORTED_BUDGET_ACTIONS = (
    RETRIEVE_TARGETED,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_SUFFICIENT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    ASK_USER_CLARIFICATION,
    REQUEST_SOCIAL_SIGNAL_CHECK,
)

_RETRIEVAL_SPEND_ACTIONS = {
    RETRIEVE_TARGETED,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
}
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


class MarginalValueLevel(str, Enum):
    """Ordered qualitative levels used by the offline action gate."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarginalValueCostTier(str, Enum):
    """Coarse cost vocabulary for one bounded action."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarginalValueDecisionStatus(str, Enum):
    """Stable decision status for the passive gate."""

    APPROVED = "approved"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ControllerBudgetHardCaps:
    """Mode-owned ceilings mirrored for controller budget reasoning."""

    mode: str
    max_iterations: int
    max_queries: int
    results_per_query: int
    top_chunks: int
    search_depth: str
    live_call_cap: int = 0
    provider_routing_boundary: str = "orchestrator_owned"
    depth_routing_boundary: str = "mode_or_orchestrator_owned"

    @classmethod
    def from_mode_policy(
        cls,
        mode: str | RunMode | ModePolicy | None,
    ) -> ControllerBudgetHardCaps:
        """Build hard caps from the existing passive mode policy."""

        policy = mode if isinstance(mode, ModePolicy) else mode_policy_for(mode)
        return cls(
            mode=policy.mode.value,
            max_iterations=policy.max_iterations,
            max_queries=policy.max_queries,
            results_per_query=policy.results_per_query,
            top_chunks=policy.top_chunks,
            search_depth=policy.search_depth,
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self)


@dataclass(frozen=True)
class ControllerBudgetSpent:
    """Already-spent budget facts supplied by an offline fixture or reducer."""

    retrieval_iterations: int = 0
    targeted_retrieval_actions: int = 0
    weak_corpus_recovery_attempts: int = 0
    source_class_recovery_attempts: int = 0
    conflict_resolution_actions: int = 0
    social_side_packet_requests: int = 0
    live_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self)


@dataclass(frozen=True)
class ControllerBudgetAllowance:
    """Controller-owned reserve/allowance facts inside mode hard caps."""

    retrieval_action_reserve: int = 0
    targeted_retrieval_reserve: int = 0
    weak_corpus_recovery_reserve: int = 0
    source_class_recovery_reserve: int = 0
    conflict_resolution_reserve: int = 0
    clarification_allowed: bool = True
    social_side_packet_placeholder_allowed: bool = False
    live_call_placeholder_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self)


@dataclass(frozen=True)
class ControllerBudgetRemaining:
    """Derived remaining allowance after hard caps and spent counters."""

    iteration_hard_cap_remaining: int
    retrieval_action_reserve_remaining: int
    targeted_retrieval_remaining: int
    weak_corpus_recovery_remaining: int
    source_class_recovery_remaining: int
    conflict_resolution_remaining: int
    social_side_packet_placeholder_remaining: int
    live_call_placeholder_remaining: int

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self)


@dataclass(frozen=True)
class MarginalValueDecision:
    """Inputs and result vocabulary for one marginal-value budget decision."""

    proposed_action: str
    contract_family: str
    contract_obligation: str
    missing_contract_items: tuple[str, ...] = ()
    centrality: MarginalValueLevel = MarginalValueLevel.LOW
    evidence_gap_severity: MarginalValueLevel = MarginalValueLevel.LOW
    redundancy_risk: MarginalValueLevel = MarginalValueLevel.LOW
    conflict_risk: MarginalValueLevel = MarginalValueLevel.LOW
    expected_value: MarginalValueLevel = MarginalValueLevel.LOW
    cost_tier: MarginalValueCostTier = MarginalValueCostTier.LOW
    remaining_allowance: Mapping[str, int] = field(default_factory=dict)
    status: MarginalValueDecisionStatus = MarginalValueDecisionStatus.SKIPPED
    approved: bool = False
    rationale: str = ""
    stop_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(self)


@dataclass(frozen=True)
class ControllerBudgetState:
    """Offline state consumed by the AG-31 marginal-value gate."""

    hard_caps: ControllerBudgetHardCaps
    spent: ControllerBudgetSpent = field(default_factory=ControllerBudgetSpent)
    allowance: ControllerBudgetAllowance = field(
        default_factory=ControllerBudgetAllowance
    )
    proposed_action: str = RETRIEVE_TARGETED
    contract_family: str = "general_factual_answer"
    contract_obligation: str = "answer_contract"
    missing_contract_items: tuple[str, ...] = ()
    centrality: MarginalValueLevel = MarginalValueLevel.LOW
    evidence_gap_severity: MarginalValueLevel = MarginalValueLevel.LOW
    redundancy_risk: MarginalValueLevel = MarginalValueLevel.LOW
    conflict_risk: MarginalValueLevel = MarginalValueLevel.LOW
    expected_value: MarginalValueLevel = MarginalValueLevel.LOW
    cost_tier: MarginalValueCostTier = MarginalValueCostTier.LOW
    requires_official_or_legal_evidence: bool = False
    weak_corpus: bool = False
    social_signal_requested: bool = False
    protected_provider_depth_routing_boundary: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mode(
        cls,
        mode: str | RunMode | ModePolicy | None,
        **kwargs: Any,
    ) -> ControllerBudgetState:
        """Build a state from existing mode caps without changing those caps."""

        return cls(
            hard_caps=ControllerBudgetHardCaps.from_mode_policy(mode),
            **kwargs,
        )

    def remaining(self) -> ControllerBudgetRemaining:
        """Return deterministic remaining budget fields."""

        hard_remaining = max(
            0,
            int(self.hard_caps.max_iterations or 0)
            - int(self.spent.retrieval_iterations or 0),
        )
        retrieval_reserve_remaining = max(
            0,
            min(
                hard_remaining,
                int(self.allowance.retrieval_action_reserve or 0)
                - int(self.spent.targeted_retrieval_actions or 0)
                - int(self.spent.source_class_recovery_attempts or 0)
                - int(self.spent.weak_corpus_recovery_attempts or 0)
                - int(self.spent.conflict_resolution_actions or 0),
            ),
        )
        return ControllerBudgetRemaining(
            iteration_hard_cap_remaining=hard_remaining,
            retrieval_action_reserve_remaining=retrieval_reserve_remaining,
            targeted_retrieval_remaining=max(
                0,
                min(
                    hard_remaining,
                    int(self.allowance.targeted_retrieval_reserve or 0)
                    - int(self.spent.targeted_retrieval_actions or 0),
                ),
            ),
            weak_corpus_recovery_remaining=max(
                0,
                min(
                    hard_remaining,
                    int(self.allowance.weak_corpus_recovery_reserve or 0)
                    - int(self.spent.weak_corpus_recovery_attempts or 0),
                ),
            ),
            source_class_recovery_remaining=max(
                0,
                min(
                    hard_remaining,
                    int(self.allowance.source_class_recovery_reserve or 0)
                    - int(self.spent.source_class_recovery_attempts or 0),
                ),
            ),
            conflict_resolution_remaining=max(
                0,
                min(
                    hard_remaining,
                    int(self.allowance.conflict_resolution_reserve or 0)
                    - int(self.spent.conflict_resolution_actions or 0),
                ),
            ),
            social_side_packet_placeholder_remaining=(
                1
                if self.allowance.social_side_packet_placeholder_allowed
                and self.spent.social_side_packet_requests < 1
                else 0
            ),
            live_call_placeholder_remaining=(
                1
                if self.allowance.live_call_placeholder_allowed
                and self.hard_caps.live_call_cap > self.spent.live_calls
                else 0
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_BUDGET_STATE_SCHEMA_VERSION,
            "hard_caps": self.hard_caps.to_dict(),
            "spent": self.spent.to_dict(),
            "allowance": self.allowance.to_dict(),
            "remaining": self.remaining().to_dict(),
            "proposed_action": self.proposed_action,
            "contract_family": self.contract_family,
            "contract_obligation": self.contract_obligation,
            "missing_contract_items": list(_copy_string_tuple(self.missing_contract_items)),
            "centrality": self.centrality.value,
            "evidence_gap_severity": self.evidence_gap_severity.value,
            "redundancy_risk": self.redundancy_risk.value,
            "conflict_risk": self.conflict_risk.value,
            "expected_value": self.expected_value.value,
            "cost_tier": self.cost_tier.value,
            "requires_official_or_legal_evidence": (
                self.requires_official_or_legal_evidence
            ),
            "weak_corpus": self.weak_corpus,
            "social_signal_requested": self.social_signal_requested,
            "protected_provider_depth_routing_boundary": (
                self.protected_provider_depth_routing_boundary
            ),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerBudgetActionGateResult:
    """JSON-safe result for one passive budget gate evaluation."""

    state: ControllerBudgetState
    decision: MarginalValueDecision
    supported_actions: tuple[str, ...] = SUPPORTED_BUDGET_ACTIONS
    ag27_budget_classes: tuple[str, ...] = field(
        default_factory=lambda: tuple(item.value for item in ControllerBudgetClass)
    )
    runtime_behavior_changed: bool = False
    controller_drives_runtime: bool = False
    live_side_effects: bool = False
    protected_surfaces_preserved: bool = True
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_BUDGET_ACTION_GATE_SCHEMA_VERSION,
            "state": self.state.to_dict(),
            "decision": self.decision.to_dict(),
            "supported_actions": list(self.supported_actions),
            "ag27_budget_classes": list(self.ag27_budget_classes),
            "runtime_behavior_changed": self.runtime_behavior_changed,
            "controller_drives_runtime": self.controller_drives_runtime,
            "live_side_effects": self.live_side_effects,
            "protected_surfaces_preserved": self.protected_surfaces_preserved,
            "warnings": list(self.warnings),
            "metadata": {
                "offline_only": True,
                "uses_ag25_action_names": True,
                "aligns_with_ag27_budget_descriptors": True,
                "provider_routing_boundary": (
                    self.state.hard_caps.provider_routing_boundary
                ),
                "depth_routing_boundary": self.state.hard_caps.depth_routing_boundary,
            },
        }


def evaluate_controller_budget_action_gate(
    state: ControllerBudgetState | Mapping[str, Any],
) -> ControllerBudgetActionGateResult:
    """Recommend spend/skip/stop for one bounded controller action offline."""

    budget_state = coerce_controller_budget_state(state)
    action = budget_state.proposed_action
    remaining = budget_state.remaining()
    warnings = _alignment_warnings()

    decision = _base_decision(budget_state, remaining)
    if action not in SUPPORTED_BUDGET_ACTIONS:
        decision = _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.BLOCKED,
            approved=False,
            stop_reason="unsupported_action",
            rationale="The proposed action is not in the AG-31 supported action set.",
        )
    elif action not in controller_action_names():
        decision = _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.BLOCKED,
            approved=False,
            stop_reason="not_ag25_action",
            rationale="The proposed action is not registered as an AG-25 action.",
        )
    elif action == REQUEST_SOCIAL_SIGNAL_CHECK:
        decision = _social_decision(budget_state, remaining, decision)
    elif action == ASK_USER_CLARIFICATION:
        decision = _clarification_decision(budget_state, decision)
    elif action == STOP_SUFFICIENT:
        decision = _stop_sufficient_decision(budget_state, decision)
    elif action == STOP_INSUFFICIENT_WITH_CAVEAT:
        decision = _stop_insufficient_decision(budget_state, decision)
    elif _action_allowance(action, remaining) <= 0:
        decision = _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.BLOCKED,
            approved=False,
            stop_reason="budget_or_reserve_exhausted",
            rationale="The action is inside the mode hard cap model, but no bounded reserve remains for it.",
        )
    elif _redundant_or_low_value(budget_state):
        decision = _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="redundant_or_low_marginal_value",
            rationale="Remaining budget exists, but the proposed search is redundant or unlikely to satisfy a central contract gap.",
        )
    elif action == RECOVER_MISSING_SOURCE_CLASS:
        decision = _source_class_decision(budget_state, decision)
    elif action == RECOVER_WEAK_CORPUS:
        decision = _weak_corpus_decision(budget_state, decision)
    elif action == RESOLVE_CONFLICT:
        decision = _conflict_decision(budget_state, decision)
    elif action == RETRIEVE_TARGETED:
        decision = _targeted_retrieval_decision(budget_state, decision)

    return ControllerBudgetActionGateResult(
        state=budget_state,
        decision=decision,
        warnings=warnings,
    )


def coerce_controller_budget_state(
    state: ControllerBudgetState | Mapping[str, Any],
) -> ControllerBudgetState:
    """Coerce mappings from tests/docs into the AG-31 state object."""

    if isinstance(state, ControllerBudgetState):
        return state
    if not isinstance(state, Mapping):
        raise TypeError("controller budget gate requires a budget state mapping")
    hard_caps = state.get("hard_caps")
    if isinstance(hard_caps, ControllerBudgetHardCaps):
        caps = hard_caps
    elif isinstance(hard_caps, Mapping):
        caps = ControllerBudgetHardCaps(**_dataclass_kwargs(ControllerBudgetHardCaps, hard_caps))
    else:
        caps = ControllerBudgetHardCaps.from_mode_policy(state.get("mode", RunMode.BALANCED))

    spent = state.get("spent")
    allowance = state.get("allowance")
    return ControllerBudgetState(
        hard_caps=caps,
        spent=(
            spent
            if isinstance(spent, ControllerBudgetSpent)
            else ControllerBudgetSpent(**_dataclass_kwargs(ControllerBudgetSpent, spent))
        ),
        allowance=(
            allowance
            if isinstance(allowance, ControllerBudgetAllowance)
            else ControllerBudgetAllowance(
                **_dataclass_kwargs(ControllerBudgetAllowance, allowance)
            )
        ),
        proposed_action=str(state.get("proposed_action") or RETRIEVE_TARGETED),
        contract_family=str(state.get("contract_family") or "general_factual_answer"),
        contract_obligation=str(state.get("contract_obligation") or "answer_contract"),
        missing_contract_items=_copy_string_tuple(state.get("missing_contract_items")),
        centrality=_coerce_level(state.get("centrality"), MarginalValueLevel.LOW),
        evidence_gap_severity=_coerce_level(
            state.get("evidence_gap_severity"),
            MarginalValueLevel.LOW,
        ),
        redundancy_risk=_coerce_level(state.get("redundancy_risk"), MarginalValueLevel.LOW),
        conflict_risk=_coerce_level(state.get("conflict_risk"), MarginalValueLevel.LOW),
        expected_value=_coerce_level(state.get("expected_value"), MarginalValueLevel.LOW),
        cost_tier=_coerce_cost(state.get("cost_tier"), MarginalValueCostTier.LOW),
        requires_official_or_legal_evidence=bool(
            state.get("requires_official_or_legal_evidence", False)
        ),
        weak_corpus=bool(state.get("weak_corpus", False)),
        social_signal_requested=bool(state.get("social_signal_requested", False)),
        protected_provider_depth_routing_boundary=bool(
            state.get("protected_provider_depth_routing_boundary", True)
        ),
        metadata=_mapping(state.get("metadata")),
    )


def _source_class_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if not state.missing_contract_items:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="no_specific_missing_source_class",
            rationale="Source-class recovery requires a named missing evidence/source obligation.",
        )
    if state.requires_official_or_legal_evidence or _central_gap(state):
        return _approve(
            decision,
            "A bounded source-class recovery is justified by a central missing official/legal/current evidence obligation.",
        )
    return _replace_decision(
        decision,
        status=MarginalValueDecisionStatus.SKIPPED,
        approved=False,
        stop_reason="source_class_gap_not_central",
        rationale="The missing source class is not central enough to spend a bounded recovery action.",
    )


def _weak_corpus_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if not state.weak_corpus:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="corpus_not_marked_weak",
            rationale="Weak-corpus recovery is reserved for an explicitly weak evidence corpus.",
        )
    return _approve(
        decision,
        "One bounded weak-corpus recovery is justified by a weak evidence state and remaining reserve.",
    )


def _conflict_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if _rank(state.conflict_risk) < _rank(MarginalValueLevel.HIGH):
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="conflict_not_material",
            rationale="Conflict-resolution retrieval is reserved for material conflicting evidence.",
        )
    return _approve(
        decision,
        "A bounded conflict-resolution action is justified by high conflict risk on a central obligation.",
    )


def _targeted_retrieval_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if not _central_gap(state):
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="no_central_contract_gap",
            rationale="Targeted retrieval requires a central answer-contract or evidence gap.",
        )
    return _approve(
        decision,
        "A bounded targeted retrieval action is justified by a central gap, low redundancy, and remaining reserve.",
    )


def _social_decision(
    state: ControllerBudgetState,
    remaining: ControllerBudgetRemaining,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if not state.social_signal_requested:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="social_signal_not_contract_requested",
            rationale="Social signal remains a future side-packet and was not requested by the contract.",
        )
    if remaining.social_side_packet_placeholder_remaining <= 0:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.BLOCKED,
            approved=False,
            stop_reason="social_side_packet_placeholder_unavailable",
            rationale="Social signal is future/side-packet only and no placeholder allowance is available.",
        )
    if any(
        not action_can_satisfy_evidence_class(REQUEST_SOCIAL_SIGNAL_CHECK, item)
        for item in state.missing_contract_items
    ):
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="social_signal_cannot_satisfy_factual_or_official_gap",
            rationale="Social signal can remain a future side-packet, but it cannot satisfy factual, official, legal, or current-primary evidence.",
        )
    return _replace_decision(
        decision,
        status=MarginalValueDecisionStatus.SKIPPED,
        approved=False,
        stop_reason="future_side_packet_only",
        rationale="Social signal is represented only as a future side-packet placeholder in AG-31.",
    )


def _clarification_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if not state.allowance.clarification_allowed:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.BLOCKED,
            approved=False,
            stop_reason="clarification_not_allowed",
            rationale="Clarification was not allowed by the supplied offline allowance.",
        )
    if not state.missing_contract_items:
        return _replace_decision(
            decision,
            status=MarginalValueDecisionStatus.SKIPPED,
            approved=False,
            stop_reason="no_missing_item_to_clarify",
            rationale="Clarification requires a specific missing obligation or ambiguity.",
        )
    return _approve(
        decision,
        "A safe clarification posture is available without spending retrieval budget.",
    )


def _stop_sufficient_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if (
        not state.missing_contract_items
        and _rank(state.evidence_gap_severity) <= _rank(MarginalValueLevel.LOW)
        and _rank(state.conflict_risk) <= _rank(MarginalValueLevel.LOW)
    ):
        return _approve(
            decision,
            "The evidence state satisfies central obligations; stop sufficient is the highest-value action.",
        )
    return _replace_decision(
        decision,
        status=MarginalValueDecisionStatus.SKIPPED,
        approved=False,
        stop_reason="central_gap_or_conflict_remains",
        rationale="Sufficient stop is skipped because a material gap or conflict remains.",
    )


def _stop_insufficient_decision(
    state: ControllerBudgetState,
    decision: MarginalValueDecision,
) -> MarginalValueDecision:
    if state.missing_contract_items or _rank(state.evidence_gap_severity) >= _rank(MarginalValueLevel.MEDIUM):
        return _approve(
            decision,
            "The remaining gap should be carried as an explicit caveat rather than spending low-value or unavailable budget.",
        )
    return _replace_decision(
        decision,
        status=MarginalValueDecisionStatus.SKIPPED,
        approved=False,
        stop_reason="insufficient_caveat_not_needed",
        rationale="No material gap requires an insufficient-with-caveat posture.",
    )


def _base_decision(
    state: ControllerBudgetState,
    remaining: ControllerBudgetRemaining,
) -> MarginalValueDecision:
    return MarginalValueDecision(
        proposed_action=state.proposed_action,
        contract_family=state.contract_family,
        contract_obligation=state.contract_obligation,
        missing_contract_items=_copy_string_tuple(state.missing_contract_items),
        centrality=state.centrality,
        evidence_gap_severity=state.evidence_gap_severity,
        redundancy_risk=state.redundancy_risk,
        conflict_risk=state.conflict_risk,
        expected_value=state.expected_value,
        cost_tier=state.cost_tier,
        remaining_allowance=remaining.to_dict(),
        rationale="No budget decision has been evaluated.",
    )


def _approve(decision: MarginalValueDecision, rationale: str) -> MarginalValueDecision:
    return _replace_decision(
        decision,
        status=MarginalValueDecisionStatus.APPROVED,
        approved=True,
        stop_reason=None,
        rationale=rationale,
    )


def _replace_decision(
    decision: MarginalValueDecision,
    **updates: Any,
) -> MarginalValueDecision:
    values = decision.to_dict()
    values.update(updates)
    return MarginalValueDecision(
        proposed_action=values["proposed_action"],
        contract_family=values["contract_family"],
        contract_obligation=values["contract_obligation"],
        missing_contract_items=_copy_string_tuple(values["missing_contract_items"]),
        centrality=_coerce_level(values["centrality"], MarginalValueLevel.LOW),
        evidence_gap_severity=_coerce_level(
            values["evidence_gap_severity"],
            MarginalValueLevel.LOW,
        ),
        redundancy_risk=_coerce_level(values["redundancy_risk"], MarginalValueLevel.LOW),
        conflict_risk=_coerce_level(values["conflict_risk"], MarginalValueLevel.LOW),
        expected_value=_coerce_level(values["expected_value"], MarginalValueLevel.LOW),
        cost_tier=_coerce_cost(values["cost_tier"], MarginalValueCostTier.LOW),
        remaining_allowance=_mapping(values["remaining_allowance"]),
        status=(
            values["status"]
            if isinstance(values["status"], MarginalValueDecisionStatus)
            else MarginalValueDecisionStatus(str(values["status"]))
        ),
        approved=bool(values["approved"]),
        rationale=str(values["rationale"]),
        stop_reason=values["stop_reason"],
    )


def _action_allowance(
    action: str,
    remaining: ControllerBudgetRemaining,
) -> int:
    if action == RETRIEVE_TARGETED:
        return min(
            remaining.retrieval_action_reserve_remaining,
            remaining.targeted_retrieval_remaining,
        )
    if action == RECOVER_MISSING_SOURCE_CLASS:
        return min(
            remaining.retrieval_action_reserve_remaining,
            remaining.source_class_recovery_remaining,
        )
    if action == RECOVER_WEAK_CORPUS:
        return min(
            remaining.retrieval_action_reserve_remaining,
            remaining.weak_corpus_recovery_remaining,
        )
    if action == RESOLVE_CONFLICT:
        return min(
            remaining.retrieval_action_reserve_remaining,
            remaining.conflict_resolution_remaining,
        )
    return 0 if action in _RETRIEVAL_SPEND_ACTIONS else 1


def _central_gap(state: ControllerBudgetState) -> bool:
    return (
        bool(state.missing_contract_items)
        and _rank(state.centrality) >= _rank(MarginalValueLevel.MEDIUM)
        and _rank(state.evidence_gap_severity) >= _rank(MarginalValueLevel.MEDIUM)
        and _rank(state.expected_value) >= _rank(MarginalValueLevel.MEDIUM)
    )


def _redundant_or_low_value(state: ControllerBudgetState) -> bool:
    if _rank(state.redundancy_risk) >= _rank(MarginalValueLevel.HIGH):
        return True
    return _rank(state.expected_value) <= _rank(MarginalValueLevel.LOW) and _rank(
        state.evidence_gap_severity
    ) <= _rank(MarginalValueLevel.LOW)


def _alignment_warnings() -> tuple[str, ...]:
    descriptors = controller_budget_descriptors()
    missing = [
        budget_class.value
        for budget_class in ControllerBudgetClass
        if budget_class.value not in descriptors
    ]
    return tuple(f"missing_ag27_budget_descriptor:{item}" for item in missing)


def _coerce_level(
    value: Any,
    default: MarginalValueLevel,
) -> MarginalValueLevel:
    if isinstance(value, MarginalValueLevel):
        return value
    try:
        return MarginalValueLevel(str(value or default.value))
    except ValueError:
        return default


def _coerce_cost(
    value: Any,
    default: MarginalValueCostTier,
) -> MarginalValueCostTier:
    if isinstance(value, MarginalValueCostTier):
        return value
    try:
        return MarginalValueCostTier(str(value or default.value))
    except ValueError:
        return default


def _rank(value: MarginalValueLevel) -> int:
    order = {
        MarginalValueLevel.NONE: 0,
        MarginalValueLevel.LOW: 1,
        MarginalValueLevel.MEDIUM: 2,
        MarginalValueLevel.HIGH: 3,
    }
    return order[value]


def _dataclass_kwargs(cls: type[Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    names = getattr(cls, "__dataclass_fields__", {})
    return {key: value[key] for key in names if key in value}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _copy_string_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple, set)):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
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
    return str(value)


__all__ = [
    "CONTROLLER_BUDGET_ACTION_GATE_SCHEMA_VERSION",
    "CONTROLLER_BUDGET_STATE_SCHEMA_VERSION",
    "SUPPORTED_BUDGET_ACTIONS",
    "ControllerBudgetActionGateResult",
    "ControllerBudgetAllowance",
    "ControllerBudgetHardCaps",
    "ControllerBudgetRemaining",
    "ControllerBudgetSpent",
    "ControllerBudgetState",
    "MarginalValueCostTier",
    "MarginalValueDecision",
    "MarginalValueDecisionStatus",
    "MarginalValueLevel",
    "coerce_controller_budget_state",
    "evaluate_controller_budget_action_gate",
]
