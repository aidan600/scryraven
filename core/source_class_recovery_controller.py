"""Minimal active controller decision for source-class recovery.

The controller owns one post-retrieval decision: whether existing
source-class recovery should run. It does not retrieve, route providers,
choose providers, alter prompts, rank sources, persist data, or call models.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

SOURCE_CLASS_RECOVERY_PROVIDER_ROLE = "source_class_recovery"

SOURCE_CLASS_CONTROLLER_EVIDENCE_SIGNAL_KEYS = (
    "source_tier_counts",
    "source_domain_counts",
    "top_source_domains",
    "unique_source_domain_count",
    "on_domain_source_count",
    "off_domain_source_count",
    "official_evidence_found",
    "community_signal_found",
    "low_trust_sources_found",
    "pollution_detected",
)

_MAX_ACTIVE_RECOVERY_QUERIES = 2
_WEAK_CORPUS_STATES = {"OFF_TOPIC", "ESTIMATE_FROM_PRIORS"}
_SKIP_REASON_PRIORITY = (
    "not_evaluated",
    "already_attempted",
    "blocked_by_author_phase",
    "blocked_by_post_analyst_phase",
    "blocked_by_weak_corpus_recovery",
    "blocked_by_corpus_weak",
    "blocked_by_iteration_budget",
    "blocked_by_provider_policy_change_required",
    "blocked_by_search_depth_escalation_required",
    "blocked_by_retrieve_to_anchor_recommendation",
    "no_recovery_queries",
    "not_recommended",
    "no_missing_expected_source_class",
)
_NO_ACTION_REASONS = {"not_recommended", "no_missing_expected_source_class"}
_ANSWER_CONTRACT_RECOVERY_REASON_PREFIXES = (
    "answer_contract_official_gap:",
    "answer_contract_legal_text_gap:",
    "answer_contract_current_primary_gap:",
)
_ANSWER_CONTRACT_OFFICIAL_OR_LEGAL_CLASSES = {
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
}
_LEGAL_AUTHORITY_DOMAINS = {
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "regulations.gov",
    "congress.gov",
    "law.cornell.edu",
    "eur-lex.europa.eu",
}


class SourceClassRecoveryControllerDecision(str, Enum):
    """Stable source-class recovery decision values."""

    NO_ACTION = "no_action"
    BLOCKED_WITH_REASON = "blocked_with_reason"
    RUN_SOURCE_CLASS_RECOVERY = "run_source_class_recovery"


@dataclass(frozen=True)
class SourceClassRecoveryActionEnvelope:
    """Trace-safe controller action envelope for missing source-class recovery."""

    action_type: str
    required_source_class: tuple[str, ...] = ()
    obligation_status: str = "unknown"
    recovery_reason: str | None = None
    current_evidence_status: str = "unknown"
    allowed_action: bool = False
    budget_attempt_context: dict[str, Any] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    stop_posture_if_unmet: str | None = None
    trace_safe_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "required_source_class": list(self.required_source_class),
            "obligation_status": self.obligation_status,
            "recovery_reason": self.recovery_reason,
            "current_evidence_status": self.current_evidence_status,
            "allowed_action": self.allowed_action,
            "budget_attempt_context": deepcopy(self.budget_attempt_context),
            "blockers": list(self.blockers),
            "stop_posture_if_unmet": self.stop_posture_if_unmet,
            "trace_safe_summary": self.trace_safe_summary,
        }


@dataclass(frozen=True)
class SourceClassRecoveryControllerInput:
    """Compact post-main-retrieval snapshot for the controller decision."""

    recommendation_evaluated: bool
    recommended: bool
    missing_expected_source_classes: tuple[str, ...] = ()
    recovery_queries: tuple[str, ...] = ()
    recommendation_reason: str | None = None
    evidence_signals: dict[str, Any] = field(default_factory=dict)
    corpus_state: str | None = None
    corpus_weak: bool = False
    weak_corpus_recovery_considered: bool = False
    weak_corpus_recovery_used: bool = False
    weak_corpus_recovery_skip_reason: str | None = None
    current_search_depth: str | None = None
    iteration_budget_available: bool = False
    answer_contract_source_class_slot_available: bool = False
    official_canonical_source_class_slot_available: bool = False
    provider_policy_reusable: bool = True
    provider_swap_required: bool = False
    search_depth_reusable: bool = True
    search_depth_escalation_required: bool = False
    retrieve_to_anchor_recommended: bool = False
    pre_analyst_phase: bool = True
    author_phase: bool = False
    prior_attempt_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_evaluated": self.recommendation_evaluated,
            "recommended": self.recommended,
            "missing_expected_source_classes": list(
                self.missing_expected_source_classes
            ),
            "recovery_queries": list(self.recovery_queries),
            "recommendation_reason": self.recommendation_reason,
            "evidence_signals": deepcopy(self.evidence_signals),
            "corpus_state": self.corpus_state,
            "corpus_weak": self.corpus_weak,
            "weak_corpus_recovery_considered": self.weak_corpus_recovery_considered,
            "weak_corpus_recovery_used": self.weak_corpus_recovery_used,
            "weak_corpus_recovery_skip_reason": self.weak_corpus_recovery_skip_reason,
            "current_search_depth": self.current_search_depth,
            "iteration_budget_available": self.iteration_budget_available,
            "answer_contract_source_class_slot_available": (
                self.answer_contract_source_class_slot_available
            ),
            "official_canonical_source_class_slot_available": (
                self.official_canonical_source_class_slot_available
            ),
            "provider_policy_reusable": self.provider_policy_reusable,
            "provider_swap_required": self.provider_swap_required,
            "search_depth_reusable": self.search_depth_reusable,
            "search_depth_escalation_required": self.search_depth_escalation_required,
            "retrieve_to_anchor_recommended": self.retrieve_to_anchor_recommended,
            "pre_analyst_phase": self.pre_analyst_phase,
            "author_phase": self.author_phase,
            "prior_attempt_count": self.prior_attempt_count,
        }


@dataclass(frozen=True)
class SourceClassRecoveryDecision:
    """Controller-owned decision and approved action parameters."""

    decision: SourceClassRecoveryControllerDecision
    reason: str | None
    blockers: tuple[str, ...] = ()
    missing_expected_source_classes: tuple[str, ...] = ()
    queries: tuple[str, ...] = ()
    provider_role: str | None = None
    search_depth: str | None = None
    attempt_count: int = 0
    action_envelope: SourceClassRecoveryActionEnvelope | None = None

    @property
    def approved(self) -> bool:
        return self.decision is (
            SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "missing_expected_source_classes": list(
                self.missing_expected_source_classes
            ),
            "queries": list(self.queries),
            "provider_role": self.provider_role,
            "search_depth": self.search_depth,
            "attempt_count": self.attempt_count,
        }


def _obligation_status(snapshot: SourceClassRecoveryControllerInput) -> str:
    if not snapshot.recommendation_evaluated:
        return "unknown"
    if snapshot.recommended and snapshot.missing_expected_source_classes:
        return "required"
    return "not_required"


def _current_evidence_status(
    snapshot: SourceClassRecoveryControllerInput,
    blockers: tuple[str, ...],
) -> str:
    if blockers:
        return "blocked_missing_required_source_class"
    if snapshot.recommended and snapshot.missing_expected_source_classes:
        return "missing_required_source_class"
    return "required_source_class_not_missing"


def _stop_posture_if_unmet(snapshot: SourceClassRecoveryControllerInput) -> str | None:
    if not snapshot.missing_expected_source_classes:
        return None
    return "stop_insufficient_with_caveat"


def _action_summary(
    *,
    eligible: bool,
    reason: str | None,
    blockers: tuple[str, ...],
) -> str:
    if eligible:
        return "Controller approved bounded missing-source-class recovery."
    if blockers:
        return "Controller blocked missing-source-class recovery: " + blockers[0]
    if reason:
        return "Controller did not approve missing-source-class recovery: " + reason
    return "Controller did not approve missing-source-class recovery."


def build_source_class_recovery_action_envelope(
    snapshot: SourceClassRecoveryControllerInput,
    decision: SourceClassRecoveryControllerDecision,
    *,
    reason: str | None,
    blockers: tuple[str, ...],
    attempt_count: int,
    provider_role: str | None,
    search_depth: str | None,
) -> SourceClassRecoveryActionEnvelope:
    """Build the controller-owned action envelope consumed by the executor seam."""
    eligible = decision is SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    return SourceClassRecoveryActionEnvelope(
        action_type="recover_missing_source_class",
        required_source_class=snapshot.missing_expected_source_classes,
        obligation_status=_obligation_status(snapshot),
        recovery_reason=reason,
        current_evidence_status=_current_evidence_status(snapshot, blockers),
        allowed_action=eligible,
        budget_attempt_context={
            "attempt_count": max(0, int(attempt_count or 0)),
            "current_search_depth": search_depth,
            "provider_role": provider_role,
            "iteration_budget_available": bool(snapshot.iteration_budget_available),
            "answer_contract_source_class_slot_available": bool(
                snapshot.answer_contract_source_class_slot_available
            ),
            "official_canonical_source_class_slot_available": bool(
                snapshot.official_canonical_source_class_slot_available
            ),
        },
        blockers=blockers,
        stop_posture_if_unmet=_stop_posture_if_unmet(snapshot),
        trace_safe_summary=_action_summary(
            eligible=eligible,
            reason=reason,
            blockers=blockers,
        ),
    )


def _copy_string_list(value: Any, *, cap: int | None = None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if cap is not None and len(out) >= cap:
            break
    return tuple(out)


def _copy_evidence_signals(signals: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(signals[key])
        for key in SOURCE_CLASS_CONTROLLER_EVIDENCE_SIGNAL_KEYS
        if key in signals
    }


def _corpus_is_weak(*, corpus_state: str | None, corpus_weak: bool) -> bool:
    return bool(corpus_weak) or str(corpus_state or "") in _WEAK_CORPUS_STATES


def _first_skip_reason(blockers: tuple[str, ...]) -> str | None:
    for reason in _SKIP_REASON_PRIORITY:
        if reason in blockers:
            return reason
    return blockers[0] if blockers else None


def _uses_answer_contract_source_class_slot(
    snapshot: SourceClassRecoveryControllerInput,
) -> bool:
    if not snapshot.answer_contract_source_class_slot_available:
        return False
    reason = str(snapshot.recommendation_reason or "")
    return reason.startswith(_ANSWER_CONTRACT_RECOVERY_REASON_PREFIXES)


def _uses_official_canonical_source_class_slot(
    snapshot: SourceClassRecoveryControllerInput,
) -> bool:
    if not snapshot.official_canonical_source_class_slot_available:
        return False
    return bool(
        set(snapshot.missing_expected_source_classes)
        & _ANSWER_CONTRACT_OFFICIAL_OR_LEGAL_CLASSES
        or set(snapshot.missing_expected_source_classes)
        & {"primary_source_documents", "archival_primary_text"}
    )


def _positive_count(value: Any, key: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        return int(value.get(key, 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def _domain_values(signals: Mapping[str, Any]) -> tuple[str, ...]:
    domains: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        clean = " ".join(str(value or "").strip().casefold().split())
        if clean and clean not in seen:
            seen.add(clean)
            domains.append(clean[4:] if clean.startswith("www.") else clean)

    source_domain_counts = signals.get("source_domain_counts")
    if isinstance(source_domain_counts, Mapping):
        for domain in source_domain_counts:
            add(domain)
    top_source_domains = signals.get("top_source_domains")
    if isinstance(top_source_domains, list):
        for row in top_source_domains:
            if isinstance(row, Mapping):
                add(row.get("domain"))
    return tuple(domains)


def _authority_domain_present(signals: Mapping[str, Any]) -> bool:
    for domain in _domain_values(signals):
        if (
            domain.endswith(".gov")
            or domain.endswith(".mil")
            or domain.endswith(".int")
            or domain.endswith(".europa.eu")
            or domain in _LEGAL_AUTHORITY_DOMAINS
        ):
            return True
    return False


def _has_useful_official_or_legal_evidence(
    signals: Mapping[str, Any],
) -> bool:
    return bool(signals.get("official_evidence_found")) or _positive_count(
        signals.get("source_tier_counts"),
        "official",
    ) or _authority_domain_present(signals)


def _can_run_official_legal_source_class_after_weak_corpus(
    snapshot: SourceClassRecoveryControllerInput,
) -> bool:
    if not (
        _uses_answer_contract_source_class_slot(snapshot)
        or _uses_official_canonical_source_class_slot(snapshot)
    ):
        return False
    if not snapshot.weak_corpus_recovery_used:
        return False
    if snapshot.weak_corpus_recovery_skip_reason not in {None, "not_weak_corpus"}:
        return False
    if not (
        set(snapshot.missing_expected_source_classes)
        & _ANSWER_CONTRACT_OFFICIAL_OR_LEGAL_CLASSES
    ):
        return False
    return not _has_useful_official_or_legal_evidence(snapshot.evidence_signals)


def build_source_class_recovery_controller_input(
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
    prior_attempt_count: int,
    answer_contract_source_class_slot_available: bool = False,
    official_canonical_source_class_slot_available: bool = False,
    provider_policy_reusable: bool = True,
    provider_swap_required: bool = False,
    search_depth_reusable: bool = True,
    search_depth_escalation_required: bool = False,
    retrieve_to_anchor_recommended: bool = False,
    pre_analyst_phase: bool = True,
    author_phase: bool = False,
) -> SourceClassRecoveryControllerInput:
    """Build the compact controller input from existing retrieval facts."""
    telemetry = recommendation or {}
    return SourceClassRecoveryControllerInput(
        recommendation_evaluated=bool(recommendation_evaluated),
        recommended=bool(telemetry.get("source_class_recovery_recommended")),
        missing_expected_source_classes=_copy_string_list(
            telemetry.get("missing_expected_source_classes")
        ),
        recovery_queries=_copy_string_list(
            telemetry.get("source_class_recovery_queries"),
            cap=_MAX_ACTIVE_RECOVERY_QUERIES,
        ),
        recommendation_reason=(
            None
            if telemetry.get("source_class_recovery_reason") is None
            else str(telemetry.get("source_class_recovery_reason"))
        ),
        evidence_signals=_copy_evidence_signals(source_class_evidence_signals),
        corpus_state=corpus_state,
        corpus_weak=bool(corpus_weak),
        weak_corpus_recovery_considered=bool(weak_corpus_recovery_considered),
        weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth=(
            str(current_search_depth) if current_search_depth is not None else None
        ),
        iteration_budget_available=bool(iteration_budget_available),
        answer_contract_source_class_slot_available=bool(
            answer_contract_source_class_slot_available
        ),
        official_canonical_source_class_slot_available=bool(
            official_canonical_source_class_slot_available
        ),
        provider_policy_reusable=bool(provider_policy_reusable),
        provider_swap_required=bool(provider_swap_required),
        search_depth_reusable=bool(search_depth_reusable),
        search_depth_escalation_required=bool(search_depth_escalation_required),
        retrieve_to_anchor_recommended=bool(retrieve_to_anchor_recommended),
        pre_analyst_phase=bool(pre_analyst_phase),
        author_phase=bool(author_phase),
        prior_attempt_count=max(0, int(prior_attempt_count or 0)),
    )


def decide_source_class_recovery(
    snapshot: SourceClassRecoveryControllerInput,
) -> SourceClassRecoveryDecision:
    """Return no_action, blocked_with_reason, or run_source_class_recovery."""
    blockers: list[str] = []
    official_legal_gap_after_weak_corpus = (
        _can_run_official_legal_source_class_after_weak_corpus(snapshot)
    )

    if not snapshot.recommendation_evaluated:
        blockers.append("not_evaluated")
    if snapshot.recommendation_evaluated and not snapshot.recommended:
        blockers.append("not_recommended")
    if (
        snapshot.recommendation_evaluated
        and snapshot.recommended
        and not snapshot.missing_expected_source_classes
    ):
        blockers.append("no_missing_expected_source_class")
    if (
        snapshot.recommendation_evaluated
        and snapshot.recommended
        and not snapshot.recovery_queries
    ):
        blockers.append("no_recovery_queries")
    if snapshot.prior_attempt_count > 0:
        blockers.append("already_attempted")

    weak_recovery_owns_path = snapshot.weak_corpus_recovery_used or (
        snapshot.weak_corpus_recovery_considered
        and snapshot.weak_corpus_recovery_skip_reason not in {None, "not_weak_corpus"}
    )
    if weak_recovery_owns_path and not official_legal_gap_after_weak_corpus:
        blockers.append("blocked_by_weak_corpus_recovery")
    elif _corpus_is_weak(
        corpus_state=snapshot.corpus_state,
        corpus_weak=snapshot.corpus_weak,
    ) and not official_legal_gap_after_weak_corpus:
        blockers.append("blocked_by_corpus_weak")
    if (
        not snapshot.iteration_budget_available
        and not _uses_answer_contract_source_class_slot(snapshot)
        and not _uses_official_canonical_source_class_slot(snapshot)
    ):
        blockers.append("blocked_by_iteration_budget")
    if not snapshot.provider_policy_reusable or snapshot.provider_swap_required:
        blockers.append("blocked_by_provider_policy_change_required")
    if (
        not snapshot.search_depth_reusable
        or snapshot.search_depth_escalation_required
    ):
        blockers.append("blocked_by_search_depth_escalation_required")
    if snapshot.retrieve_to_anchor_recommended:
        blockers.append("blocked_by_retrieve_to_anchor_recommendation")
    if snapshot.author_phase:
        blockers.append("blocked_by_author_phase")
    elif not snapshot.pre_analyst_phase:
        blockers.append("blocked_by_post_analyst_phase")

    blocker_tuple = tuple(blockers)
    eligible = snapshot.recommendation_evaluated and not blocker_tuple
    attempt_count = snapshot.prior_attempt_count + (1 if eligible else 0)
    reason = None if eligible else _first_skip_reason(blocker_tuple)

    if eligible:
        decision = SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
        reason = snapshot.recommendation_reason
        provider_role = SOURCE_CLASS_RECOVERY_PROVIDER_ROLE
        search_depth = snapshot.current_search_depth
    elif reason in _NO_ACTION_REASONS:
        decision = SourceClassRecoveryControllerDecision.NO_ACTION
        provider_role = None
        search_depth = None
    else:
        decision = SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON
        provider_role = None
        search_depth = None

    return SourceClassRecoveryDecision(
        decision=decision,
        reason=reason,
        blockers=blocker_tuple,
        missing_expected_source_classes=snapshot.missing_expected_source_classes,
        queries=snapshot.recovery_queries,
        provider_role=provider_role,
        search_depth=search_depth,
        attempt_count=attempt_count,
        action_envelope=build_source_class_recovery_action_envelope(
            snapshot,
            decision,
            reason=reason,
            blockers=blocker_tuple,
            attempt_count=attempt_count,
            provider_role=provider_role,
            search_depth=search_depth,
        ),
    )


__all__ = [
    "SOURCE_CLASS_CONTROLLER_EVIDENCE_SIGNAL_KEYS",
    "SOURCE_CLASS_RECOVERY_PROVIDER_ROLE",
    "SourceClassRecoveryActionEnvelope",
    "SourceClassRecoveryControllerDecision",
    "SourceClassRecoveryControllerInput",
    "SourceClassRecoveryDecision",
    "build_source_class_recovery_action_envelope",
    "build_source_class_recovery_controller_input",
    "decide_source_class_recovery",
]
