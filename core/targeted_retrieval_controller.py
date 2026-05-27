"""Pure targeted-retrieval candidate and lifecycle controller.

This module defines the offline lifecycle boundary for future ordinary
targeted retrieval ownership. It consumes only sanitized, already-computed
continuation facts and never generates queries, chooses providers, chooses
search depth, executes retrieval, persists state, calls models, or promotes
runtime dispatch.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

TARGETED_RETRIEVAL_STAGE = "targeted_retrieval"

TARGETED_RETRIEVAL_TRACE_FIELDS = (
    "targeted_retrieval_candidate_considered",
    "targeted_retrieval_candidate_eligible",
    "targeted_retrieval_candidate_used",
    "targeted_retrieval_candidate_reason",
    "targeted_retrieval_candidate_skip_reason",
    "targeted_retrieval_candidate_blockers",
    "targeted_retrieval_candidate_queries",
    "targeted_retrieval_candidate_query_provenance",
    "targeted_retrieval_candidate_conflict_resolving_queries",
    "targeted_retrieval_candidate_prior_query_count",
    "targeted_retrieval_candidate_redundancy_overlap",
    "targeted_retrieval_candidate_targeted_budget_remaining",
    "targeted_retrieval_candidate_attempt_count",
    "targeted_retrieval_candidate_lifecycle_phase",
    "targeted_retrieval_candidate_stage",
    "targeted_retrieval_candidate_currentness_gap_detected",
    "targeted_retrieval_candidate_official_current_source_gap",
    "targeted_retrieval_candidate_legal_or_regulatory_current_event_gap",
    "targeted_retrieval_candidate_reputable_news_or_primary_update_needed",
    "targeted_retrieval_candidate_final_answer_should_caveat_missing_current_source",
)

_ALLOWED_QUERY_PROVENANCE = frozenset(
    {
        "answer_contract_approved_targeted_queries",
        "evaluator",
        "evaluator_next_queries",
        "expander",
        "expander_component_queries",
        "fixture",
        "retrieval_stop_continue",
        "scout",
        "scout_directed_queries",
    }
)
_ALLOWED_LIFECYCLE_PHASES = frozenset({"pre_analyst", "pre_author"})
_REDUNDANT_OVERLAP_THRESHOLD = 0.7
_SKIP_REASON_PRIORITY = (
    "query_generation_required",
    "no_material_contract_gap",
    "blocked_by_source_class_recovery",
    "blocked_by_weak_corpus_recovery",
    "blocked_by_conflict_resolution",
    "blocked_by_terminal_stop",
    "blocked_by_social_signal",
    "blocked_by_scrutineer",
    "blocked_by_clarification",
    "blocked_by_legal_source_repair_required",
    "blocked_by_currentness_gap",
    "blocked_by_official_current_source_gap",
    "blocked_by_legal_or_regulatory_current_event_gap",
    "blocked_by_reputable_news_or_primary_update_needed",
    "already_attempted_for_gap",
    "blocked_by_wrong_phase",
    "blocked_by_iteration_budget",
    "blocked_by_provider_policy_change_required",
    "blocked_by_search_depth_policy_change_required",
    "redundant_with_prior_queries",
    "no_approved_queries",
    "query_provenance_not_allowed",
)
_NO_ACTION_REASONS = {"no_material_contract_gap"}
_SENSITIVE_METADATA_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db_row",
        "full_trace",
        "password",
        "prompt",
        "provider_payload",
        "raw_provider_payload",
        "raw_prompt",
        "raw_trace",
        "secret",
        "token",
    }
)


class TargetedRetrievalControllerDecision(str, Enum):
    """Stable targeted-retrieval lifecycle decision values."""

    NO_ACTION = "no_action"
    BLOCKED_WITH_REASON = "blocked_with_reason"
    APPROVE_TARGETED_RETRIEVAL_CANDIDATE = (
        "approve_targeted_retrieval_candidate"
    )


@dataclass(frozen=True)
class TargetedRetrievalCandidate:
    """Sanitized ordinary targeted-retrieval candidate facts."""

    material_contract_gap: str | None
    ordinary_next_queries: tuple[str, ...] = ()
    query_provenance: str | None = None
    query_generation_complete: bool = False
    prior_queries: tuple[str, ...] = ()
    conflict_resolving_queries: tuple[str, ...] = ()
    redundancy_status: str | None = None
    redundancy_overlap: float | None = None
    iteration: int = 0
    max_iterations: int = 0
    targeted_budget_remaining: int = 0
    lifecycle_phase: str = "pre_analyst"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_contract_gap": self.material_contract_gap,
            "ordinary_next_queries": list(self.ordinary_next_queries),
            "query_provenance": self.query_provenance,
            "query_generation_complete": bool(self.query_generation_complete),
            "prior_query_count": len(self.prior_queries),
            "prior_queries": list(self.prior_queries),
            "conflict_resolving_queries": list(self.conflict_resolving_queries),
            "redundancy_status": self.redundancy_status,
            "redundancy_overlap": self.redundancy_overlap,
            "iteration": max(0, int(self.iteration or 0)),
            "max_iterations": max(0, int(self.max_iterations or 0)),
            "targeted_budget_remaining": max(
                0,
                int(self.targeted_budget_remaining or 0),
            ),
            "lifecycle_phase": self.lifecycle_phase,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class TargetedRetrievalControllerInput:
    """Compact lifecycle input from already-computed continuation facts."""

    material_contract_gap_remaining: bool
    material_contract_gap: str | None = None
    approved_ordinary_next_queries: tuple[str, ...] = ()
    query_provenance: str | None = None
    query_generation_complete: bool = False
    prior_queries: tuple[str, ...] = ()
    next_queries_redundant: bool = False
    redundancy_status: str | None = None
    redundancy_overlap: float | None = None
    iteration: int = 0
    max_iterations: int = 0
    targeted_budget_remaining: int = 0
    prior_attempted_for_gap: bool = False
    source_class_recovery_owns_path: bool = False
    weak_corpus_recovery_owns_path: bool = False
    conflict_resolution_owns_path: bool = False
    terminal_stop_owns_path: bool = False
    social_signal_owns_path: bool = False
    scrutineer_owns_path: bool = False
    clarification_owns_path: bool = False
    source_class_blockers: tuple[str, ...] = ()
    weak_corpus_blockers: tuple[str, ...] = ()
    conflict_blockers: tuple[str, ...] = ()
    provider_policy_reusable: bool = True
    provider_policy_change_required: bool = False
    provider_swap_required: bool = False
    search_depth_reusable: bool = True
    search_depth_policy_change_required: bool = False
    search_depth_escalation_required: bool = False
    legal_source_repair_required: bool = False
    currentness_gap_detected: bool = False
    official_current_source_gap: bool = False
    legal_or_regulatory_current_event_gap: bool = False
    reputable_news_or_primary_update_needed: bool = False
    final_answer_should_caveat_missing_current_source: bool = False
    lifecycle_phase: str = "pre_analyst"
    conflict_resolving_queries: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_candidate(self) -> TargetedRetrievalCandidate:
        return TargetedRetrievalCandidate(
            material_contract_gap=(
                self.material_contract_gap
                if self.material_contract_gap_remaining
                else None
            ),
            ordinary_next_queries=self.approved_ordinary_next_queries,
            query_provenance=self.query_provenance,
            query_generation_complete=self.query_generation_complete,
            prior_queries=self.prior_queries,
            conflict_resolving_queries=self.conflict_resolving_queries,
            redundancy_status=self.redundancy_status,
            redundancy_overlap=self.redundancy_overlap,
            iteration=self.iteration,
            max_iterations=self.max_iterations,
            targeted_budget_remaining=self.targeted_budget_remaining,
            lifecycle_phase=self.lifecycle_phase,
            metadata=deepcopy(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_contract_gap_remaining": bool(
                self.material_contract_gap_remaining
            ),
            "material_contract_gap": self.material_contract_gap,
            "approved_ordinary_next_queries": list(
                self.approved_ordinary_next_queries
            ),
            "query_provenance": self.query_provenance,
            "query_generation_complete": bool(self.query_generation_complete),
            "prior_queries": list(self.prior_queries),
            "next_queries_redundant": bool(self.next_queries_redundant),
            "redundancy_status": self.redundancy_status,
            "redundancy_overlap": self.redundancy_overlap,
            "iteration": max(0, int(self.iteration or 0)),
            "max_iterations": max(0, int(self.max_iterations or 0)),
            "targeted_budget_remaining": max(
                0,
                int(self.targeted_budget_remaining or 0),
            ),
            "prior_attempted_for_gap": bool(self.prior_attempted_for_gap),
            "path_owners": {
                "source_class_recovery": bool(
                    self.source_class_recovery_owns_path
                ),
                "weak_corpus_recovery": bool(
                    self.weak_corpus_recovery_owns_path
                ),
                "conflict_resolution": bool(
                    self.conflict_resolution_owns_path
                ),
                "terminal_stop": bool(self.terminal_stop_owns_path),
                "social_signal": bool(self.social_signal_owns_path),
                "scrutineer": bool(self.scrutineer_owns_path),
                "clarification": bool(self.clarification_owns_path),
            },
            "source_class_blockers": list(self.source_class_blockers),
            "weak_corpus_blockers": list(self.weak_corpus_blockers),
            "conflict_blockers": list(self.conflict_blockers),
            "provider_policy_reusable": bool(self.provider_policy_reusable),
            "provider_policy_change_required": bool(
                self.provider_policy_change_required
            ),
            "provider_swap_required": bool(self.provider_swap_required),
            "search_depth_reusable": bool(self.search_depth_reusable),
            "search_depth_policy_change_required": bool(
                self.search_depth_policy_change_required
            ),
            "search_depth_escalation_required": bool(
                self.search_depth_escalation_required
            ),
            "legal_source_repair_required": bool(
                self.legal_source_repair_required
            ),
            "currentness_gap_detected": bool(self.currentness_gap_detected),
            "official_current_source_gap": bool(
                self.official_current_source_gap
            ),
            "legal_or_regulatory_current_event_gap": bool(
                self.legal_or_regulatory_current_event_gap
            ),
            "reputable_news_or_primary_update_needed": bool(
                self.reputable_news_or_primary_update_needed
            ),
            "final_answer_should_caveat_missing_current_source": bool(
                self.final_answer_should_caveat_missing_current_source
            ),
            "lifecycle_phase": self.lifecycle_phase,
            "conflict_resolving_queries": list(self.conflict_resolving_queries),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class TargetedRetrievalDecision:
    """Controller-owned decision over an ordinary targeted candidate."""

    decision: TargetedRetrievalControllerDecision
    reason: str | None
    blockers: tuple[str, ...] = ()
    ordinary_next_queries: tuple[str, ...] = ()
    query_provenance: str | None = None
    conflict_resolving_queries: tuple[str, ...] = ()
    attempt_count: int = 0
    stage: str | None = None

    @property
    def approved(self) -> bool:
        return self.decision is (
            TargetedRetrievalControllerDecision.APPROVE_TARGETED_RETRIEVAL_CANDIDATE
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "ordinary_next_queries": list(self.ordinary_next_queries),
            "query_provenance": self.query_provenance,
            "conflict_resolving_queries": list(self.conflict_resolving_queries),
            "attempt_count": max(0, int(self.attempt_count or 0)),
            "stage": self.stage,
        }


@dataclass(frozen=True)
class TargetedRetrievalLifecycle:
    """Trace-friendly passive lifecycle object for a targeted candidate."""

    snapshot: TargetedRetrievalControllerInput
    candidate: TargetedRetrievalCandidate
    decision: TargetedRetrievalDecision

    def to_trace_fields(self) -> dict[str, Any]:
        approved = self.decision.approved
        considered = bool(
            self.snapshot.material_contract_gap_remaining
            or self.snapshot.approved_ordinary_next_queries
        )
        return _trace_payload(
            considered=considered,
            eligible=approved,
            used=False,
            reason=self.decision.reason,
            skip_reason=None if approved else self.decision.reason,
            blockers=list(self.decision.blockers),
            queries=list(self.decision.ordinary_next_queries),
            query_provenance=self.decision.query_provenance,
            conflict_resolving_queries=list(
                self.decision.conflict_resolving_queries
            ),
            prior_query_count=len(self.snapshot.prior_queries),
            redundancy_overlap=self.snapshot.redundancy_overlap,
            targeted_budget_remaining=self.snapshot.targeted_budget_remaining,
            attempt_count=self.decision.attempt_count,
            lifecycle_phase=self.snapshot.lifecycle_phase,
            stage=self.decision.stage if approved else None,
            currentness_gap_detected=self.snapshot.currentness_gap_detected,
            official_current_source_gap=(
                self.snapshot.official_current_source_gap
            ),
            legal_or_regulatory_current_event_gap=(
                self.snapshot.legal_or_regulatory_current_event_gap
            ),
            reputable_news_or_primary_update_needed=(
                self.snapshot.reputable_news_or_primary_update_needed
            ),
            final_answer_should_caveat_missing_current_source=(
                self.snapshot.final_answer_should_caveat_missing_current_source
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "candidate": self.candidate.to_dict(),
            "decision": self.decision.to_dict(),
            "trace_fields": self.to_trace_fields(),
        }


def _copy_string_tuple(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        text = _clean_text(item, limit=300)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    return text[:limit] if text else None


def _clean_phase(value: Any) -> str:
    text = _clean_text(value, limit=80)
    if not text:
        return "pre_analyst"
    return text.casefold().replace("-", "_").replace(" ", "_")


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=80)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _clean_overlap(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").strip().casefold()
    return text.startswith("raw_") or text in _SENSITIVE_METADATA_KEYS


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _json_safe_metadata(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe_value(item) for item in sorted(value, key=str)]
    return str(value)


def _json_safe_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in dict(metadata or {}).items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _json_safe_value(value)
    return out


def _first_skip_reason(blockers: tuple[str, ...]) -> str | None:
    for reason in _SKIP_REASON_PRIORITY:
        if reason in blockers:
            return reason
    return blockers[0] if blockers else None


def _is_redundant(snapshot: TargetedRetrievalControllerInput) -> bool:
    if snapshot.next_queries_redundant:
        return True
    status = str(snapshot.redundancy_status or "").strip().casefold()
    if status in {"redundant", "duplicate", "overlapping"}:
        return True
    overlap = snapshot.redundancy_overlap
    return overlap is not None and overlap >= _REDUNDANT_OVERLAP_THRESHOLD


def _trace_payload(
    *,
    considered: bool,
    eligible: bool,
    used: bool,
    reason: str | None,
    skip_reason: str | None,
    blockers: list[str],
    queries: list[str],
    query_provenance: str | None,
    conflict_resolving_queries: list[str],
    prior_query_count: int,
    redundancy_overlap: float | None,
    targeted_budget_remaining: int,
    attempt_count: int,
    lifecycle_phase: str,
    stage: str | None,
    currentness_gap_detected: bool,
    official_current_source_gap: bool,
    legal_or_regulatory_current_event_gap: bool,
    reputable_news_or_primary_update_needed: bool,
    final_answer_should_caveat_missing_current_source: bool,
) -> dict[str, Any]:
    return {
        "targeted_retrieval_candidate_considered": bool(considered),
        "targeted_retrieval_candidate_eligible": bool(eligible),
        "targeted_retrieval_candidate_used": bool(used),
        "targeted_retrieval_candidate_reason": reason,
        "targeted_retrieval_candidate_skip_reason": skip_reason,
        "targeted_retrieval_candidate_blockers": list(blockers),
        "targeted_retrieval_candidate_queries": list(queries),
        "targeted_retrieval_candidate_query_provenance": query_provenance,
        "targeted_retrieval_candidate_conflict_resolving_queries": list(
            conflict_resolving_queries
        ),
        "targeted_retrieval_candidate_prior_query_count": max(
            0,
            int(prior_query_count or 0),
        ),
        "targeted_retrieval_candidate_redundancy_overlap": redundancy_overlap,
        "targeted_retrieval_candidate_targeted_budget_remaining": max(
            0,
            int(targeted_budget_remaining or 0),
        ),
        "targeted_retrieval_candidate_attempt_count": max(
            0,
            int(attempt_count or 0),
        ),
        "targeted_retrieval_candidate_lifecycle_phase": lifecycle_phase,
        "targeted_retrieval_candidate_stage": stage,
        "targeted_retrieval_candidate_currentness_gap_detected": bool(
            currentness_gap_detected
        ),
        "targeted_retrieval_candidate_official_current_source_gap": bool(
            official_current_source_gap
        ),
        "targeted_retrieval_candidate_legal_or_regulatory_current_event_gap": bool(
            legal_or_regulatory_current_event_gap
        ),
        "targeted_retrieval_candidate_reputable_news_or_primary_update_needed": bool(
            reputable_news_or_primary_update_needed
        ),
        "targeted_retrieval_candidate_final_answer_should_caveat_missing_current_source": bool(
            final_answer_should_caveat_missing_current_source
        ),
    }


def build_targeted_retrieval_controller_input(
    *,
    material_contract_gap_remaining: bool,
    material_contract_gap: str | None = None,
    approved_ordinary_next_queries: list[str] | tuple[str, ...] = (),
    query_provenance: str | None = None,
    query_generation_complete: bool = False,
    prior_queries: list[str] | tuple[str, ...] = (),
    next_queries_redundant: bool = False,
    redundancy_status: str | None = None,
    redundancy_overlap: float | None = None,
    iteration: int = 0,
    max_iterations: int = 0,
    targeted_budget_remaining: int = 0,
    prior_attempted_for_gap: bool = False,
    source_class_recovery_owns_path: bool = False,
    weak_corpus_recovery_owns_path: bool = False,
    conflict_resolution_owns_path: bool = False,
    terminal_stop_owns_path: bool = False,
    social_signal_owns_path: bool = False,
    scrutineer_owns_path: bool = False,
    clarification_owns_path: bool = False,
    source_class_blockers: list[str] | tuple[str, ...] = (),
    weak_corpus_blockers: list[str] | tuple[str, ...] = (),
    conflict_blockers: list[str] | tuple[str, ...] = (),
    provider_policy_reusable: bool = True,
    provider_policy_change_required: bool = False,
    provider_swap_required: bool = False,
    search_depth_reusable: bool = True,
    search_depth_policy_change_required: bool = False,
    search_depth_escalation_required: bool = False,
    legal_source_repair_required: bool = False,
    currentness_gap_detected: bool = False,
    official_current_source_gap: bool = False,
    legal_or_regulatory_current_event_gap: bool = False,
    reputable_news_or_primary_update_needed: bool = False,
    final_answer_should_caveat_missing_current_source: bool = False,
    lifecycle_phase: str = "pre_analyst",
    conflict_resolving_queries: list[str] | tuple[str, ...] = (),
    metadata: Mapping[str, Any] | None = None,
) -> TargetedRetrievalControllerInput:
    """Build a sanitized targeted-retrieval snapshot from known facts."""
    return TargetedRetrievalControllerInput(
        material_contract_gap_remaining=bool(material_contract_gap_remaining),
        material_contract_gap=_clean_text(material_contract_gap, limit=180),
        approved_ordinary_next_queries=_copy_string_tuple(
            approved_ordinary_next_queries
        ),
        query_provenance=_clean_token(query_provenance),
        query_generation_complete=bool(query_generation_complete),
        prior_queries=_copy_string_tuple(prior_queries),
        next_queries_redundant=bool(next_queries_redundant),
        redundancy_status=_clean_token(redundancy_status)
        if redundancy_status is not None
        else None,
        redundancy_overlap=_clean_overlap(redundancy_overlap),
        iteration=max(0, int(iteration or 0)),
        max_iterations=max(0, int(max_iterations or 0)),
        targeted_budget_remaining=max(0, int(targeted_budget_remaining or 0)),
        prior_attempted_for_gap=bool(prior_attempted_for_gap),
        source_class_recovery_owns_path=bool(source_class_recovery_owns_path),
        weak_corpus_recovery_owns_path=bool(weak_corpus_recovery_owns_path),
        conflict_resolution_owns_path=bool(conflict_resolution_owns_path),
        terminal_stop_owns_path=bool(terminal_stop_owns_path),
        social_signal_owns_path=bool(social_signal_owns_path),
        scrutineer_owns_path=bool(scrutineer_owns_path),
        clarification_owns_path=bool(clarification_owns_path),
        source_class_blockers=_copy_string_tuple(source_class_blockers),
        weak_corpus_blockers=_copy_string_tuple(weak_corpus_blockers),
        conflict_blockers=_copy_string_tuple(conflict_blockers),
        provider_policy_reusable=bool(provider_policy_reusable),
        provider_policy_change_required=bool(provider_policy_change_required),
        provider_swap_required=bool(provider_swap_required),
        search_depth_reusable=bool(search_depth_reusable),
        search_depth_policy_change_required=bool(
            search_depth_policy_change_required
        ),
        search_depth_escalation_required=bool(search_depth_escalation_required),
        legal_source_repair_required=bool(legal_source_repair_required),
        currentness_gap_detected=bool(currentness_gap_detected),
        official_current_source_gap=bool(official_current_source_gap),
        legal_or_regulatory_current_event_gap=bool(
            legal_or_regulatory_current_event_gap
        ),
        reputable_news_or_primary_update_needed=bool(
            reputable_news_or_primary_update_needed
        ),
        final_answer_should_caveat_missing_current_source=bool(
            final_answer_should_caveat_missing_current_source
        ),
        lifecycle_phase=_clean_phase(lifecycle_phase),
        conflict_resolving_queries=_copy_string_tuple(conflict_resolving_queries),
        metadata=deepcopy(dict(metadata or {})),
    )


def decide_targeted_retrieval(
    snapshot: TargetedRetrievalControllerInput,
) -> TargetedRetrievalDecision:
    """Return no_action, blocked_with_reason, or an approved passive candidate."""
    blockers: list[str] = []

    if not snapshot.query_generation_complete:
        blockers.append("query_generation_required")
    if not snapshot.material_contract_gap_remaining:
        blockers.append("no_material_contract_gap")
    if not snapshot.approved_ordinary_next_queries:
        blockers.append("no_approved_queries")
    if snapshot.query_provenance not in _ALLOWED_QUERY_PROVENANCE:
        blockers.append("query_provenance_not_allowed")
    if _is_redundant(snapshot):
        blockers.append("redundant_with_prior_queries")
    if (
        snapshot.targeted_budget_remaining <= 0
        or snapshot.iteration >= snapshot.max_iterations
    ):
        blockers.append("blocked_by_iteration_budget")
    if snapshot.source_class_recovery_owns_path:
        blockers.append("blocked_by_source_class_recovery")
    if snapshot.weak_corpus_recovery_owns_path:
        blockers.append("blocked_by_weak_corpus_recovery")
    if snapshot.conflict_resolution_owns_path:
        blockers.append("blocked_by_conflict_resolution")
    if snapshot.terminal_stop_owns_path:
        blockers.append("blocked_by_terminal_stop")
    if snapshot.social_signal_owns_path:
        blockers.append("blocked_by_social_signal")
    if snapshot.scrutineer_owns_path:
        blockers.append("blocked_by_scrutineer")
    if snapshot.clarification_owns_path:
        blockers.append("blocked_by_clarification")
    if (
        not snapshot.provider_policy_reusable
        or snapshot.provider_policy_change_required
        or snapshot.provider_swap_required
    ):
        blockers.append("blocked_by_provider_policy_change_required")
    if (
        not snapshot.search_depth_reusable
        or snapshot.search_depth_policy_change_required
        or snapshot.search_depth_escalation_required
    ):
        blockers.append("blocked_by_search_depth_policy_change_required")
    if snapshot.legal_source_repair_required:
        blockers.append("blocked_by_legal_source_repair_required")
    if snapshot.currentness_gap_detected:
        blockers.append("blocked_by_currentness_gap")
    if snapshot.official_current_source_gap:
        blockers.append("blocked_by_official_current_source_gap")
    if snapshot.legal_or_regulatory_current_event_gap:
        blockers.append("blocked_by_legal_or_regulatory_current_event_gap")
    if snapshot.reputable_news_or_primary_update_needed:
        blockers.append("blocked_by_reputable_news_or_primary_update_needed")
    if snapshot.lifecycle_phase not in _ALLOWED_LIFECYCLE_PHASES:
        blockers.append("blocked_by_wrong_phase")
    if snapshot.prior_attempted_for_gap:
        blockers.append("already_attempted_for_gap")

    blocker_tuple = tuple(blockers)
    eligible = not blocker_tuple
    attempt_count = 1 if eligible else (1 if snapshot.prior_attempted_for_gap else 0)

    if eligible:
        return TargetedRetrievalDecision(
            decision=(
                TargetedRetrievalControllerDecision
                .APPROVE_TARGETED_RETRIEVAL_CANDIDATE
            ),
            reason="targeted_retrieval_candidate_available",
            ordinary_next_queries=snapshot.approved_ordinary_next_queries,
            query_provenance=snapshot.query_provenance,
            conflict_resolving_queries=snapshot.conflict_resolving_queries,
            attempt_count=attempt_count,
            stage=TARGETED_RETRIEVAL_STAGE,
        )

    reason = _first_skip_reason(blocker_tuple)
    decision = (
        TargetedRetrievalControllerDecision.NO_ACTION
        if reason in _NO_ACTION_REASONS
        else TargetedRetrievalControllerDecision.BLOCKED_WITH_REASON
    )
    return TargetedRetrievalDecision(
        decision=decision,
        reason=reason,
        blockers=blocker_tuple,
        ordinary_next_queries=snapshot.approved_ordinary_next_queries,
        query_provenance=snapshot.query_provenance,
        conflict_resolving_queries=snapshot.conflict_resolving_queries,
        attempt_count=attempt_count,
    )


def build_targeted_retrieval_lifecycle(
    snapshot: TargetedRetrievalControllerInput,
) -> TargetedRetrievalLifecycle:
    """Return the passive lifecycle object for a targeted-retrieval candidate."""
    return TargetedRetrievalLifecycle(
        snapshot=snapshot,
        candidate=snapshot.to_candidate(),
        decision=decide_targeted_retrieval(snapshot),
    )


def targeted_retrieval_lifecycle_defaults() -> dict[str, Any]:
    """Return default targeted_retrieval_candidate_* trace fields."""
    return _trace_payload(
        considered=False,
        eligible=False,
        used=False,
        reason="not_evaluated",
        skip_reason="not_evaluated",
        blockers=["not_evaluated"],
        queries=[],
        query_provenance=None,
        conflict_resolving_queries=[],
        prior_query_count=0,
        redundancy_overlap=None,
        targeted_budget_remaining=0,
        attempt_count=0,
        lifecycle_phase="not_evaluated",
        stage=None,
        currentness_gap_detected=False,
        official_current_source_gap=False,
        legal_or_regulatory_current_event_gap=False,
        reputable_news_or_primary_update_needed=False,
        final_answer_should_caveat_missing_current_source=False,
    )


__all__ = [
    "TARGETED_RETRIEVAL_STAGE",
    "TARGETED_RETRIEVAL_TRACE_FIELDS",
    "TargetedRetrievalCandidate",
    "TargetedRetrievalControllerDecision",
    "TargetedRetrievalControllerInput",
    "TargetedRetrievalDecision",
    "TargetedRetrievalLifecycle",
    "build_targeted_retrieval_controller_input",
    "build_targeted_retrieval_lifecycle",
    "decide_targeted_retrieval",
    "targeted_retrieval_lifecycle_defaults",
]
