"""Controller-owned authoritative-source action readiness.

This helper composes the existing authoritative-source adapters into one named
action-readiness seam. It does not retrieve, choose providers, choose depth,
rank/filter sources, alter prompts, cite sources, or affect final answers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.authoritative_source_answer_contract_projection import (
    project_authoritative_source_state_to_answer_contract_fields,
)
from core.authoritative_source_obligations import (
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
)
from core.authority_lifecycle_contract import (
    AuthorityEvidenceFitState,
    AuthoritySatisfactionState,
)
from core.authority_lifecycle_execution import (
    sync_authority_lifecycle_execution_from_source_class_trace,
)
from core.authority_lifecycle_runtime_arbitration import (
    AuthorityRuntimeArbitration,
    build_authority_runtime_arbitration,
)
from core.corpus_state import CorpusState
from core.legal_current_authority_fit import (
    LegalCurrentEvidenceFact,
    build_legal_current_primary_authority_fit,
)
from core.official_canonical_recovery_execution_admission import (
    OfficialCanonicalRecoveryExecutionAdmissionResult,
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    OfficialCanonicalRecoveryQueryAcquisitionResult,
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_source_obligation_bridge import (
    OfficialSourceObligationBridgeResult,
    apply_official_source_obligation_bridge,
)
from core.run_authority_search_judgment_consumers import (
    apply_search_judgment_to_source_class_recovery_recommendation,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    apply_answer_contract_source_class_recovery_gap_trigger,
)
from core.source_class_recovery_lifecycle import (
    record_source_class_recovery_lifecycle,
)

AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY = "authoritative_source_action_trace"
AUTHORITATIVE_SOURCE_ACTION_SCHEMA_VERSION = "authoritative_source_action_ag66b_v1"

_RECOVER_MISSING_SOURCE_CLASS = "recover_missing_source_class"
_DEFAULT_MAX_RECOVERY_ATTEMPTS = 1

_ALLOWED_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_CANONICAL_ACQUISITION_PATH_VISIBLE_KEY = (
    "official_canonical_acquisition_path_visible"
)
_OFFICIAL_CANONICAL_ACQUISITION_PATH_VISIBILITY_SOURCE_KEY = (
    "official_canonical_acquisition_path_visibility_source"
)
_AUTHORITY_CLASS_BY_SOURCE_CLASS = {
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "archival_primary_text": PRIMARY_SOURCE_DOCUMENTS,
}
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)
_PROTECTED_MARKERS = (
    "database",
    "db row",
    "full_trace",
    "private log",
    "provider_payload",
    "raw prompt",
    "raw_prompt",
    "raw_provider",
    "secret",
)


class AuthoritativeSourceActionName(str, Enum):
    """Stable AG-66B action names."""

    SOURCE_CLASS_RECOVERY = "source_class_recovery"
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class AuthoritativeSourceActionFacts:
    """Sanitized facts already available to the orchestrator/controller path."""

    query: str | None = None
    intent: str | None = None
    report_type: str | None = None
    query_type: str | None = None
    core_topic: str | None = None
    primary_entity: str | None = None
    recommendation: Mapping[str, Any] | None = None
    source_class_observability: Mapping[str, Any] | None = None
    source_class_evidence_signals: Mapping[str, Any] | None = None
    run_search_judgment_projection: Mapping[str, Any] | None = None
    obligation_facts: Mapping[str, Any] | None = None
    answer_contract_family: str | None = None
    answer_contract_source_classes_missing: Sequence[Any] = ()
    answer_contract_unfulfilled_items: Sequence[Any] = ()
    answer_contract_partial_items: Sequence[Any] = ()
    answer_contract_recovery_query_candidates: Sequence[Any] = ()
    corpus_state: str | None = None
    corpus_weak: bool = False
    weak_corpus_recovery_considered: bool = False
    weak_corpus_recovery_used: bool = False
    weak_corpus_recovery_skip_reason: str | None = None
    evidence_checkpoint_action_name: str | None = None
    current_search_depth: str | None = None
    iteration_budget_available: bool = False
    answer_contract_source_class_slot_available: bool = False
    provider_policy_reusable: bool = True
    provider_swap_required: bool = False
    search_depth_reusable: bool = True
    search_depth_escalation_required: bool = False
    retrieve_to_anchor_recommended: bool = False
    ordinary_continuation_path_active: bool = False
    pre_analyst_phase: bool = True
    author_phase: bool = False
    query_redundancy_skipped: bool = False
    iteration_budget_hard_exhausted: bool = False
    terminal_stop_approved: bool = False
    existing_acquisition_blockers: Sequence[Any] = ()
    existing_admission_blockers: Sequence[Any] = ()
    prior_recovery_attempt_count: int = 0
    max_recovery_attempts: int = _DEFAULT_MAX_RECOVERY_ATTEMPTS
    ordinary_iteration_budget_remaining: int = 0
    legal_current_requirement_id: str | None = None
    legal_current_jurisdiction: str | None = None
    legal_current_anchor: str | None = None
    legal_current_temporal_anchor: str | None = None
    legal_current_evidence_facts: Sequence[LegalCurrentEvidenceFact | Mapping[str, Any]] = ()


@dataclass(frozen=True)
class AuthoritativeSourceActionDecision:
    """Compact trace-safe action decision for existing executors."""

    action_name: AuthoritativeSourceActionName
    approved: bool
    reason: str | None = None
    blockers: tuple[str, ...] = ()
    required_source_classes: tuple[str, ...] = ()
    recovery_queries: tuple[str, ...] = ()
    action_envelope: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _safe_value(
            {
                "action_name": self.action_name.value,
                "approved": self.approved,
                "reason": self.reason,
                "blockers": list(self.blockers),
                "required_source_classes": list(self.required_source_classes),
                "recovery_queries": list(self.recovery_queries),
                "action_envelope": dict(self.action_envelope),
            }
        )


@dataclass(frozen=True)
class AuthoritativeSourceActionResult:
    """Authoritative-source obligation state plus existing action handoff."""

    recommendation: dict[str, Any]
    obligation_state: AuthoritativeSourceObligationState
    trace_safe_projection: dict[str, Any]
    action_decision: AuthoritativeSourceActionDecision
    active_source_class_recovery_lifecycle: dict[str, Any]
    official_canonical_recovery_execution_admitted: bool = False
    official_source_obligation_bridge_trace: dict[str, Any] | None = None
    official_canonical_recovery_query_acquisition_trace: dict[str, Any] | None = None
    official_canonical_recovery_execution_admission_trace: dict[str, Any] | None = None
    legal_current_primary_projection: dict[str, Any] | None = None
    authority_lifecycle_trace: dict[str, Any] | None = None
    trace: dict[str, Any] = field(default_factory=dict)


def build_authoritative_source_obligation_state_and_action(
    controller: RunController,
    *,
    facts: AuthoritativeSourceActionFacts,
    logger: Any | None = None,
) -> AuthoritativeSourceActionResult:
    """Build authoritative-source obligation state and existing action readiness."""

    recommendation = _safe_mapping(facts.recommendation)
    preexisting_source_gap_signal = _source_class_gap_signal_present(recommendation)
    observability = _safe_mapping(facts.source_class_observability)
    recommendation = apply_search_judgment_to_source_class_recovery_recommendation(
        recommendation,
        search_judgment_projection=facts.run_search_judgment_projection,
        query=facts.query,
        core_topic=facts.core_topic,
        primary_entity=facts.primary_entity,
    )
    runtime_trace = _runtime_trace(facts, recommendation, observability)

    recommendation = _apply_answer_contract_gap_trigger(
        recommendation=recommendation,
        facts=facts,
        logger=logger,
    )
    recommendation = apply_search_judgment_to_source_class_recovery_recommendation(
        recommendation,
        search_judgment_projection=facts.run_search_judgment_projection,
        query=facts.query,
        core_topic=facts.core_topic,
        primary_entity=facts.primary_entity,
    )
    recommendation = _suppress_promoted_recovery_for_owned_non_source_class_path(
        recommendation=recommendation,
        facts=facts,
        preexisting_source_gap_signal=preexisting_source_gap_signal,
    )

    bridge_trace: dict[str, Any] | None = None
    bridge_result = _try_bridge(
        recommendation=recommendation,
        runtime_trace=runtime_trace,
        obligation_facts=facts.obligation_facts,
        logger=logger,
    )
    if bridge_result is not None:
        pre_bridge_reason = _clean_text(
            recommendation.get("source_class_recovery_reason"), limit=220
        )
        recommendation = bridge_result.recommendation
        if (
            pre_bridge_reason
            and pre_bridge_reason.startswith("answer_contract_")
            and str(recommendation.get("source_class_recovery_reason") or "").startswith(
                "official_source_obligation_bridge:"
            )
        ):
            recommendation = {
                **recommendation,
                "source_class_recovery_reason": pre_bridge_reason,
            }
        bridge_trace = bridge_result.trace
    recommendation = _suppress_promoted_recovery_for_owned_non_source_class_path(
        recommendation=recommendation,
        facts=facts,
        preexisting_source_gap_signal=preexisting_source_gap_signal,
    )

    authority_arbitration = _authority_runtime_arbitration(
        facts=facts,
        recommendation=recommendation,
        observability=observability,
        legal_projection=None,
    )
    acquisition_trace: dict[str, Any] | None = None
    acquisition_runtime_trace = {
        **_runtime_trace(facts, recommendation, observability),
        **authority_arbitration.to_trace_fields(),
    }
    acquisition_result = _try_query_acquisition(
        recommendation=recommendation,
        runtime_trace=acquisition_runtime_trace,
        obligation_facts=facts.obligation_facts,
        existing_blockers=_acquisition_blockers(
            facts,
            authority_arbitration=authority_arbitration,
        ),
        logger=logger,
    )
    if acquisition_result is not None:
        recommendation = acquisition_result.recommendation
        acquisition_trace = acquisition_result.trace
    recommendation = _promote_official_canonical_acquisition_path_visibility(
        recommendation,
        facts=facts,
        observability=observability,
        authority_arbitration=authority_arbitration,
    )
    authority_arbitration = _authority_runtime_arbitration(
        facts=facts,
        recommendation=recommendation,
        observability=observability,
        legal_projection=None,
    )

    admission_trace: dict[str, Any] | None = None
    admitted = False
    admission_runtime_trace = {
        **_runtime_trace(facts, recommendation, observability),
        **authority_arbitration.to_trace_fields(),
    }
    admission_result = _try_execution_admission(
        recommendation=recommendation,
        runtime_trace=admission_runtime_trace,
        obligation_facts=facts.obligation_facts,
        existing_blockers=_admission_blockers(
            facts,
            authority_arbitration=authority_arbitration,
        ),
        prior_recovery_attempt_count=facts.prior_recovery_attempt_count,
        max_recovery_attempts=facts.max_recovery_attempts,
        ordinary_iteration_budget_remaining=facts.ordinary_iteration_budget_remaining,
        logger=logger,
    )
    if admission_result is not None:
        admitted = bool(admission_result.source_class_recovery_execution_admitted)
        admission_trace = admission_result.trace

    lifecycle_corpus_state, lifecycle_corpus_weak, lifecycle_weak_skip = (
        _source_class_lifecycle_corpus_facts(
            facts,
            authority_arbitration=authority_arbitration,
        )
    )
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals=_safe_mapping(
            facts.source_class_evidence_signals
        ),
        corpus_state=lifecycle_corpus_state,
        corpus_weak=lifecycle_corpus_weak,
        weak_corpus_recovery_considered=facts.weak_corpus_recovery_considered,
        weak_corpus_recovery_used=facts.weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=lifecycle_weak_skip,
        current_search_depth=facts.current_search_depth,
        iteration_budget_available=facts.iteration_budget_available,
        answer_contract_source_class_slot_available=(
            facts.answer_contract_source_class_slot_available
        ),
        official_canonical_source_class_slot_available=admitted,
        provider_policy_reusable=facts.provider_policy_reusable,
        provider_swap_required=facts.provider_swap_required,
        search_depth_reusable=facts.search_depth_reusable,
        search_depth_escalation_required=facts.search_depth_escalation_required,
        retrieve_to_anchor_recommended=False,
        pre_analyst_phase=facts.pre_analyst_phase,
        author_phase=facts.author_phase,
    )
    lifecycle.update(authority_arbitration.to_trace_fields())
    sync_authority_lifecycle_execution_from_source_class_trace(lifecycle)

    obligation_state = _build_authoritative_obligation_state(
        recommendation=recommendation,
        observability=observability,
        legal_projection=None,
    )
    legal_projection = _build_legal_current_projection(facts)
    if legal_projection is not None:
        obligation_state = _build_authoritative_obligation_state(
            recommendation=recommendation,
            observability=observability,
            legal_projection=legal_projection,
        )
    trace_safe_projection = (
        project_authoritative_source_state_to_answer_contract_fields(
            obligation_state
        ).to_dict()
    )
    action_decision = _action_decision_from_lifecycle(lifecycle)
    trace = _action_trace(
        facts=facts,
        recommendation=recommendation,
        projection=trace_safe_projection,
        action_decision=action_decision,
        lifecycle=lifecycle,
        admitted=admitted,
        bridge_trace=bridge_trace,
        acquisition_trace=acquisition_trace,
        admission_trace=admission_trace,
        legal_projection=legal_projection,
        authority_arbitration=authority_arbitration,
    )
    return AuthoritativeSourceActionResult(
        recommendation=recommendation,
        obligation_state=obligation_state,
        trace_safe_projection=trace_safe_projection,
        action_decision=action_decision,
        active_source_class_recovery_lifecycle=lifecycle,
        official_canonical_recovery_execution_admitted=admitted,
        official_source_obligation_bridge_trace=bridge_trace,
        official_canonical_recovery_query_acquisition_trace=acquisition_trace,
        official_canonical_recovery_execution_admission_trace=admission_trace,
        legal_current_primary_projection=legal_projection,
        authority_lifecycle_trace=authority_arbitration.to_trace_fields(),
        trace=trace,
    )


def build_authoritative_source_action(
    controller: RunController,
    *,
    facts: AuthoritativeSourceActionFacts,
    logger: Any | None = None,
) -> AuthoritativeSourceActionResult:
    """Compatibility alias for the named AG-66B helper."""

    return build_authoritative_source_obligation_state_and_action(
        controller,
        facts=facts,
        logger=logger,
    )


def _apply_answer_contract_gap_trigger(
    *,
    recommendation: Mapping[str, Any],
    facts: AuthoritativeSourceActionFacts,
    logger: Any | None,
) -> dict[str, Any]:
    try:
        return apply_answer_contract_source_class_recovery_gap_trigger(
            recommendation=dict(recommendation),
            answer_contract_family=facts.answer_contract_family,
            answer_contract_source_classes_missing=(
                facts.answer_contract_source_classes_missing
            ),
            answer_contract_unfulfilled_items=facts.answer_contract_unfulfilled_items,
            answer_contract_partial_items=facts.answer_contract_partial_items,
            query=facts.query,
            core_topic=facts.core_topic,
            primary_entity=facts.primary_entity,
        )
    except Exception as exc:
        _warn(
            logger,
            "Non-fatal answer-contract source-class recovery trigger omitted: %s",
            exc,
        )
        return dict(recommendation)


def _source_class_gap_signal_present(recommendation: Mapping[str, Any]) -> bool:
    return bool(
        recommendation.get("source_class_recovery_recommended")
        or recommendation.get("source_class_underfire_shadow")
        or recommendation.get("source_class_gap_candidates")
        or recommendation.get("missing_expected_source_classes")
    )


def _suppress_promoted_recovery_for_owned_non_source_class_path(
    *,
    recommendation: Mapping[str, Any],
    facts: AuthoritativeSourceActionFacts,
    preexisting_source_gap_signal: bool,
) -> dict[str, Any]:
    if preexisting_source_gap_signal:
        return dict(recommendation)
    if not recommendation.get("run_authority_search_judgment_promoted_recovery"):
        return dict(recommendation)
    blocker_reason: str | None = None
    if facts.retrieve_to_anchor_recommended:
        if _regulatory_authority_context(facts):
            return dict(recommendation)
        blocker_reason = "retrieve_to_anchor_recommendation"
    elif facts.ordinary_continuation_path_active:
        blocker_reason = "ordinary_continuation_path"
    if blocker_reason is None:
        return dict(recommendation)
    out = dict(recommendation)
    if not (
        out.get("source_class_recovery_recommended")
        or out.get("missing_expected_source_classes")
        or out.get("source_class_recovery_queries")
    ):
        return out
    out["source_class_recovery_recommended"] = False
    out["missing_expected_source_classes"] = []
    out["source_class_recovery_queries"] = []
    out["source_class_recovery_query_count"] = 0
    out["source_class_recovery_reason"] = None
    out["authority_lifecycle_required_recovery_allowed"] = False
    out["run_authority_search_judgment_recovery_blocked_by"] = blocker_reason
    return _safe_value(out)


def _regulatory_authority_context(facts: AuthoritativeSourceActionFacts) -> bool:
    values = (
        facts.intent,
        facts.report_type,
        facts.query_type,
        facts.answer_contract_family,
        facts.query,
        facts.core_topic,
    )
    text = " ".join(str(value or "").casefold() for value in values)
    return any(
        marker in text
        for marker in (
            "regulatory",
            "regulation",
            "legal",
            "statutory",
            "statute",
            " act ",
            "current official rules",
        )
    )


def _try_bridge(
    *,
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    obligation_facts: Mapping[str, Any] | None,
    logger: Any | None,
) -> OfficialSourceObligationBridgeResult | None:
    try:
        return apply_official_source_obligation_bridge(
            recommendation=recommendation,
            runtime_trace=runtime_trace,
            obligation_facts=obligation_facts,
        )
    except Exception as exc:
        _warn(logger, "Non-fatal official-source obligation bridge omitted: %s", exc)
        return None


def _try_query_acquisition(
    *,
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    obligation_facts: Mapping[str, Any] | None,
    existing_blockers: Iterable[Any],
    logger: Any | None,
) -> OfficialCanonicalRecoveryQueryAcquisitionResult | None:
    try:
        return apply_official_canonical_recovery_query_acquisition(
            recommendation=recommendation,
            runtime_trace=runtime_trace,
            obligation_facts=obligation_facts,
            existing_blockers=existing_blockers,
        )
    except Exception as exc:
        _warn(
            logger,
            "Non-fatal official/canonical recovery-query acquisition omitted: %s",
            exc,
        )
        return None


def _try_execution_admission(
    *,
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    obligation_facts: Mapping[str, Any] | None,
    existing_blockers: Iterable[Any],
    prior_recovery_attempt_count: int,
    max_recovery_attempts: int,
    ordinary_iteration_budget_remaining: int,
    logger: Any | None,
) -> OfficialCanonicalRecoveryExecutionAdmissionResult | None:
    try:
        return build_official_canonical_recovery_execution_admission(
            recommendation=recommendation,
            runtime_trace=runtime_trace,
            obligation_facts=obligation_facts,
            existing_blockers=existing_blockers,
            prior_recovery_attempt_count=prior_recovery_attempt_count,
            max_recovery_attempts=max_recovery_attempts,
            ordinary_iteration_budget_remaining=ordinary_iteration_budget_remaining,
        )
    except Exception as exc:
        _warn(
            logger,
            "Non-fatal official/canonical recovery-execution admission omitted: %s",
            exc,
        )
        return None


def _promote_official_canonical_acquisition_path_visibility(
    recommendation: Mapping[str, Any],
    *,
    facts: AuthoritativeSourceActionFacts,
    observability: Mapping[str, Any],
    authority_arbitration: AuthorityRuntimeArbitration | None,
) -> dict[str, Any]:
    """Promote already-visible official/canonical recovery queries to control."""

    out = dict(recommendation)
    if out.get(_OFFICIAL_CANONICAL_ACQUISITION_PATH_VISIBLE_KEY) is True:
        return out
    if _acquisition_blockers(
        facts,
        authority_arbitration=authority_arbitration,
    ) or _admission_blockers(
        facts,
        authority_arbitration=authority_arbitration
        or _authority_runtime_arbitration(
            facts=facts,
            recommendation=out,
            observability=observability,
            legal_projection=None,
        ),
    ):
        return out
    reason = str(out.get("source_class_recovery_reason") or "")
    trigger_fields = set(_string_tuple(out.get("source_class_recovery_trigger_fields")))
    if (
        reason.startswith("official_canonical_recovery_query_acquisition:")
        or "official_canonical_recovery_query_acquisition" in trigger_fields
    ):
        return out
    missing = {
        item
        for item in _string_tuple(out.get("missing_expected_source_classes"))
        if _clean_token(item) in _ALLOWED_SOURCE_CLASSES
    }
    if not missing:
        return out
    if not _string_tuple(out.get("source_class_recovery_queries")):
        return out
    if not out.get("source_class_recovery_recommended"):
        return out
    out[_OFFICIAL_CANONICAL_ACQUISITION_PATH_VISIBLE_KEY] = True
    out[_OFFICIAL_CANONICAL_ACQUISITION_PATH_VISIBILITY_SOURCE_KEY] = (
        "action_readiness_visible_recovery_queries"
    )
    out["source_class_recovery_trigger_fields"] = list(
        _append_unique_strings(
            out.get("source_class_recovery_trigger_fields"),
            ("official_canonical_acquisition_path_visibility",),
        )
    )
    return out


def _source_class_lifecycle_corpus_facts(
    facts: AuthoritativeSourceActionFacts,
    *,
    authority_arbitration: AuthorityRuntimeArbitration | None,
) -> tuple[str | None, bool, str | None]:
    if (
        authority_arbitration is not None
        and authority_arbitration.required_recovery_allowed
    ):
        return CorpusState.HEALTHY.value, False, None
    if (
        facts.evidence_checkpoint_action_name == _RECOVER_MISSING_SOURCE_CLASS
        and facts.weak_corpus_recovery_skip_reason == "checkpoint_action_not_approved"
    ):
        return CorpusState.HEALTHY.value, False, None
    return facts.corpus_state, bool(facts.corpus_weak), facts.weak_corpus_recovery_skip_reason


def _runtime_trace(
    facts: AuthoritativeSourceActionFacts,
    recommendation: Mapping[str, Any],
    observability: Mapping[str, Any],
) -> dict[str, Any]:
    return _safe_value(
        {
            "query_preview": _clean_text(facts.query, limit=200),
            "intent": facts.intent,
            "query_type": facts.query_type,
            "report_type": facts.report_type,
            "core_topic": facts.core_topic,
            "primary_entity": facts.primary_entity,
            "corpus_weak": bool(facts.corpus_weak),
            "weak_corpus_recovery_used": bool(facts.weak_corpus_recovery_used),
            "query_redundancy_skipped": bool(facts.query_redundancy_skipped),
            "terminal_stop_approved": bool(facts.terminal_stop_approved),
            "run_authority_search_judgment": _search_judgment_trace_ref(
                facts.run_search_judgment_projection
            ),
            "candidate_query_previews": list(
                _string_tuple(facts.answer_contract_recovery_query_candidates)
            ),
            "candidate_query_source": (
                "answer_contract_evidence_state"
                if facts.answer_contract_recovery_query_candidates
                else None
            ),
            **dict(recommendation),
            **dict(observability),
        }
    )


def _search_judgment_trace_ref(
    projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _safe_mapping(projection)
    if payload.get("owner") != "RunKernel.RunAuthoritySearchJudgment":
        return {}
    return _safe_value(
        {
            "owner": payload.get("owner"),
            "judgment_id": payload.get("judgment_id"),
            "decision": payload.get("decision"),
            "classifications": payload.get("classifications", []),
            "target_source_classes": payload.get("target_source_classes", []),
            "consumed_by": "authoritative_source_action",
            "canonical_state": payload.get("canonical_state"),
            "trace_only": payload.get("trace_only"),
        }
    )


def _acquisition_blockers(
    facts: AuthoritativeSourceActionFacts,
    *,
    authority_arbitration: AuthorityRuntimeArbitration | None,
) -> tuple[str, ...]:
    blockers = _string_tuple(facts.existing_acquisition_blockers)
    if blockers:
        return _filter_authority_runtime_blockers(
            blockers,
            authority_arbitration=authority_arbitration,
        )
    _state, lifecycle_corpus_weak, _skip = _source_class_lifecycle_corpus_facts(
        facts,
        authority_arbitration=authority_arbitration,
    )
    out: list[str] = []
    if facts.weak_corpus_recovery_used:
        out.append("weak_corpus_recovery_owns_path")
    if lifecycle_corpus_weak:
        out.append("blocked_by_corpus_weak")
    if facts.iteration_budget_hard_exhausted:
        out.append("blocked_by_iteration_budget")
    if facts.query_redundancy_skipped:
        out.append("blocked_by_redundant_query")
    return _filter_authority_runtime_blockers(
        out,
        authority_arbitration=authority_arbitration,
    )


def _admission_blockers(
    facts: AuthoritativeSourceActionFacts,
    *,
    authority_arbitration: AuthorityRuntimeArbitration | None,
) -> tuple[str, ...]:
    blockers = _string_tuple(facts.existing_admission_blockers)
    if blockers:
        return _filter_authority_runtime_blockers(
            blockers,
            authority_arbitration=authority_arbitration,
        )
    _state, lifecycle_corpus_weak, _skip = _source_class_lifecycle_corpus_facts(
        facts,
        authority_arbitration=authority_arbitration,
    )
    out: list[str] = []
    if facts.weak_corpus_recovery_used:
        out.append("weak_corpus_recovery_owns_path")
    if lifecycle_corpus_weak:
        out.append("blocked_by_corpus_weak")
    if facts.terminal_stop_approved:
        out.append("terminal_stop_approved")
    return _filter_authority_runtime_blockers(
        out,
        authority_arbitration=authority_arbitration,
    )


def _filter_authority_runtime_blockers(
    blockers: Iterable[Any],
    *,
    authority_arbitration: AuthorityRuntimeArbitration | None,
) -> tuple[str, ...]:
    if authority_arbitration is None:
        return _string_tuple(blockers)
    return authority_arbitration.filter_blockers(blockers)


def _build_authoritative_obligation_state(
    *,
    recommendation: Mapping[str, Any],
    observability: Mapping[str, Any],
    legal_projection: Mapping[str, Any] | None,
) -> AuthoritativeSourceObligationState:
    source_classes = _required_source_classes(recommendation, observability)
    requirements = tuple(
        requirement
        for source_class in source_classes
        if (requirement := _requirement_for_source_class(source_class)) is not None
    )
    fits = list(_evidence_fits_for_source_classes(source_classes, observability))
    if legal_projection is not None:
        fits.extend(_legal_projection_fits(legal_projection))
    return AuthoritativeSourceObligationState.evaluate(requirements, fits)


def _authority_runtime_arbitration(
    *,
    facts: AuthoritativeSourceActionFacts,
    recommendation: Mapping[str, Any],
    observability: Mapping[str, Any],
    legal_projection: Mapping[str, Any] | None,
) -> AuthorityRuntimeArbitration:
    obligation_state = _build_authoritative_obligation_state(
        recommendation=recommendation,
        observability=observability,
        legal_projection=legal_projection,
    )
    missing = obligation_state.missing_authority_requirements()
    requirement = missing[0] if missing else None
    required_classes = (
        requirement.required_authority_classes
        if requirement is not None
        else _required_source_classes(recommendation, observability)
    )
    requirement_id = (
        requirement.requirement_id
        if requirement is not None
        else (required_classes[0] if required_classes else "authority_not_required")
    )
    required_authority = (
        required_classes[0] if required_classes else "authority_not_required"
    )
    recovery_queries = _string_tuple(
        recommendation.get("source_class_recovery_queries")
    ) or _string_tuple(facts.answer_contract_recovery_query_candidates)
    required_recovery = bool(requirement is not None)
    recovery_action_allowed = bool(
        required_recovery and recommendation.get("source_class_recovery_recommended")
    )
    satisfied = (
        obligation_state.satisfaction_for(requirement_id).status
        if requirement is not None and requirement_id in obligation_state.satisfactions
        else None
    )
    return build_authority_runtime_arbitration(
        requirement_id=requirement_id,
        required_authority=required_authority,
        claim_type=_clean_text(facts.query_type, limit=80)
        or _clean_text(facts.report_type, limit=80)
        or "authority_requirement",
        required_recovery=required_recovery,
        recovery_queries=recovery_queries,
        required_source_classes=required_classes,
        recovery_action_allowed=recovery_action_allowed,
        terminal_stop_approved=bool(facts.terminal_stop_approved),
        weak_corpus_recovery_used=bool(facts.weak_corpus_recovery_used),
        corpus_weak=bool(facts.corpus_weak),
        existing_evidence_fit=(
            AuthorityEvidenceFitState.AUTHORITY_SATISFYING
            if satisfied is not None and satisfied.value == "fulfilled"
            else AuthorityEvidenceFitState.MISSING
        ),
        satisfaction_state=(
            AuthoritySatisfactionState.SATISFIED
            if satisfied is not None and satisfied.value == "fulfilled"
            else AuthoritySatisfactionState.UNSATISFIED
        ),
        explicit_blockers=_authority_lifecycle_blockers(
            facts=facts,
            recommendation=recommendation,
        ),
        insufficient_partial_posture=_authority_insufficient_partial_posture(
            recommendation
        ),
    )


def _authority_lifecycle_blockers(
    *,
    facts: AuthoritativeSourceActionFacts,
    recommendation: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    blockers: list[Mapping[str, Any]] = []
    for source in (
        recommendation.get("authority_lifecycle_blockers"),
        facts.obligation_facts.get("authority_lifecycle_blockers")
        if isinstance(facts.obligation_facts, Mapping)
        else None,
    ):
        if not isinstance(source, (list, tuple)):
            continue
        for item in source:
            if isinstance(item, Mapping):
                blockers.append(item)
    return tuple(blockers)


def _authority_insufficient_partial_posture(
    recommendation: Mapping[str, Any],
) -> bool:
    return (
        _clean_token(recommendation.get("authority_lifecycle_final_posture"))
        == "insufficient_partial"
    )


def _required_source_classes(
    recommendation: Mapping[str, Any],
    observability: Mapping[str, Any],
) -> tuple[str, ...]:
    classes: list[str] = []
    for source in (recommendation, observability):
        for key in (
            "missing_expected_source_classes",
            "source_class_gap_candidates",
            "unfulfilled_source_classes",
            "partial_source_classes",
        ):
            for item in _string_tuple(source.get(key)):
                token = _clean_token(item)
                if token and token in _ALLOWED_SOURCE_CLASSES and token not in classes:
                    classes.append(token)
    return tuple(classes)


def _requirement_for_source_class(source_class: str) -> AuthorityRequirement | None:
    if source_class == "official_current_rules":
        return AuthorityRequirement.official_current(source_class)
    if source_class in {"legal_or_regulatory_text", "current_primary_or_official"}:
        return AuthorityRequirement.legal_current_primary(source_class)
    if source_class in {"primary_source_documents", "archival_primary_text"}:
        return AuthorityRequirement.canonical_project_doc(source_class)
    return None


def _evidence_fits_for_source_classes(
    source_classes: Iterable[str],
    observability: Mapping[str, Any],
) -> tuple[AuthorityEvidenceFit, ...]:
    status_by_class = observability.get("source_class_satisfaction_status")
    strong_counts = observability.get("source_class_strong_satisfaction_counts")
    fits: list[AuthorityEvidenceFit] = []
    for source_class in source_classes:
        requirement = _requirement_for_source_class(source_class)
        authority_class = _AUTHORITY_CLASS_BY_SOURCE_CLASS.get(source_class)
        if requirement is None or authority_class is None:
            continue
        status = _clean_token(
            status_by_class.get(source_class)
            if isinstance(status_by_class, Mapping)
            else None
        )
        if _positive_count(strong_counts, source_class) or status == "satisfied_strong":
            fits.append(
                AuthorityEvidenceFit.authoritative(
                    requirement.requirement_id,
                    f"{source_class}:satisfied_strong",
                    authority_class,
                )
            )
        elif status in {"expected_but_only_secondary", "satisfied_weak"}:
            fits.append(
                AuthorityEvidenceFit.lower_tier_context(
                    requirement.requirement_id,
                    f"{source_class}:secondary_only",
                    REPUTABLE_SECONDARY,
                    mismatch_reason=status,
                )
            )
    return tuple(fits)


def _build_legal_current_projection(
    facts: AuthoritativeSourceActionFacts,
) -> dict[str, Any] | None:
    if not (
        facts.legal_current_requirement_id
        or facts.legal_current_jurisdiction
        or facts.legal_current_evidence_facts
    ):
        return None
    result = build_legal_current_primary_authority_fit(
        requirement_id=facts.legal_current_requirement_id
        or "legal_current_primary",
        jurisdiction=facts.legal_current_jurisdiction,
        current_anchor=facts.legal_current_anchor,
        temporal_anchor=facts.legal_current_temporal_anchor,
        subject=facts.core_topic or facts.primary_entity,
        evidence_facts=facts.legal_current_evidence_facts,
    )
    return result.to_projection()


def _legal_projection_fits(
    legal_projection: Mapping[str, Any],
) -> tuple[AuthorityEvidenceFit, ...]:
    requirement = legal_projection.get("requirement")
    if not isinstance(requirement, Mapping):
        return ()
    requirement_id = _clean_text(requirement.get("requirement_id"), limit=80)
    if not requirement_id:
        return ()
    fits: list[AuthorityEvidenceFit] = []
    for fit in legal_projection.get("evidence_fits") or ():
        if not isinstance(fit, Mapping):
            continue
        evidence_id = _clean_text(fit.get("evidence_id"), limit=80) or "legal-evidence"
        if fit.get("satisfies_authority") is True:
            fits.append(
                AuthorityEvidenceFit.authoritative(
                    requirement_id,
                    evidence_id,
                    _clean_token(fit.get("observed_source_class"))
                    or LEGAL_OR_REGULATORY_TEXT,
                )
            )
        elif fit.get("context_allowed") is True:
            fits.append(
                AuthorityEvidenceFit.lower_tier_context(
                    requirement_id,
                    evidence_id,
                    _clean_token(fit.get("observed_source_class"))
                    or REPUTABLE_SECONDARY,
                    mismatch_reason=_clean_text(
                        fit.get("mismatch_reason"), limit=120
                    ),
                )
            )
    return tuple(fits)


def _action_decision_from_lifecycle(
    lifecycle: Mapping[str, Any],
) -> AuthoritativeSourceActionDecision:
    approved = bool(lifecycle.get("active_source_class_recovery_eligible"))
    return AuthoritativeSourceActionDecision(
        action_name=(
            AuthoritativeSourceActionName.SOURCE_CLASS_RECOVERY
            if approved
            else AuthoritativeSourceActionName.NO_ACTION
        ),
        approved=approved,
        reason=_clean_text(
            lifecycle.get("active_source_class_recovery_reason")
            or lifecycle.get("active_source_class_recovery_skip_reason"),
            limit=180,
        ),
        blockers=_string_tuple(lifecycle.get("active_source_class_recovery_blockers")),
        required_source_classes=_string_tuple(
            lifecycle.get("active_source_class_recovery_missing_classes")
        ),
        recovery_queries=_string_tuple(
            lifecycle.get("active_source_class_recovery_queries")
        ),
        action_envelope=_safe_mapping(
            lifecycle.get("active_source_class_recovery_action_envelope")
        ),
    )


def _action_trace(
    *,
    facts: AuthoritativeSourceActionFacts,
    recommendation: Mapping[str, Any],
    projection: Mapping[str, Any],
    action_decision: AuthoritativeSourceActionDecision,
    lifecycle: Mapping[str, Any],
    admitted: bool,
    bridge_trace: Mapping[str, Any] | None,
    acquisition_trace: Mapping[str, Any] | None,
    admission_trace: Mapping[str, Any] | None,
    legal_projection: Mapping[str, Any] | None,
    authority_arbitration: AuthorityRuntimeArbitration,
) -> dict[str, Any]:
    return _safe_value(
        {
            "schema_version": AUTHORITATIVE_SOURCE_ACTION_SCHEMA_VERSION,
            "trace_safe": True,
            "helper": "build_authoritative_source_obligation_state_and_action",
            "obligation_projection": dict(projection),
            "action_decision": action_decision.to_dict(),
            "source_class_lifecycle_summary": {
                "eligible": lifecycle.get("active_source_class_recovery_eligible"),
                "used": lifecycle.get("active_source_class_recovery_used"),
                "execution_attempted": lifecycle.get(
                    "active_source_class_recovery_execution_attempted"
                ),
                "official_canonical_admitted": admitted,
                "skip_reason": lifecycle.get(
                    "active_source_class_recovery_skip_reason"
                ),
                "blockers": lifecycle.get("active_source_class_recovery_blockers"),
            },
            "recommendation_summary": {
                "source_class_recovery_recommended": recommendation.get(
                    "source_class_recovery_recommended"
                ),
                "missing_expected_source_classes": recommendation.get(
                    "missing_expected_source_classes"
                ),
                "source_class_recovery_query_count": recommendation.get(
                    "source_class_recovery_query_count"
                ),
                "source_class_recovery_reason": recommendation.get(
                    "source_class_recovery_reason"
                ),
                "run_authority_search_judgment_ref": recommendation.get(
                    "run_authority_search_judgment_ref"
                ),
                "run_authority_search_judgment_consumed": recommendation.get(
                    "run_authority_search_judgment_consumed"
                ),
            },
            "adapter_traces_present": {
                "official_source_obligation_bridge": bridge_trace is not None,
                "official_canonical_query_acquisition": acquisition_trace is not None,
                "official_canonical_execution_admission": admission_trace is not None,
                "legal_current_primary": legal_projection is not None,
            },
            "authority_lifecycle_arbitration": (
                authority_arbitration.to_trace_fields()
            ),
            "existing_blockers": {
                "acquisition": list(
                    _acquisition_blockers(
                        facts,
                        authority_arbitration=authority_arbitration,
                    )
                ),
                "admission": list(
                    _admission_blockers(
                        facts,
                        authority_arbitration=authority_arbitration,
                    )
                ),
            },
            "protected_surface": {
                "provider_policy_unchanged": True,
                "provider_selection_unchanged": True,
                "depth_policy_unchanged": True,
                "retrieval_ranking_filtering_unchanged": True,
                "query_wording_unchanged_except_existing_adapter": True,
                "prompt_unchanged": True,
                "citation_behavior_unchanged": True,
                "final_answer_behavior_unchanged": True,
                "followup_behavior_unchanged": True,
                "author_behavior_unchanged": True,
                "analyst_behavior_unchanged": True,
                "economist_behavior_unchanged": True,
                "scrutineer_behavior_unchanged": True,
                "projection_used_as_control_input": False,
            },
            "control_inputs": {
                "recommendation",
                "source_class_observability",
                "existing_blockers",
                "controller_state_prior_attempt_count",
                "authority_lifecycle",
            },
            "control_inputs_exclude": [
                "obligation_projection",
                "trace_safe_projection",
                "trace fields",
            ],
        }
    )


def _positive_count(value: Any, key: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        return int(value.get(key, 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def _string_tuple(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    values = value.values() if isinstance(value, Mapping) else value
    if values is None or isinstance(values, (str, bytes)):
        return ()
    try:
        iterable = tuple(values)
    except TypeError:
        return ()
    for item in iterable:
        text = _clean_text(item, limit=240)
        key = text.casefold() if text else ""
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _append_unique_strings(
    value: Any,
    additions: Iterable[str],
) -> tuple[str, ...]:
    out = list(_string_tuple(value))
    seen = {item.casefold() for item in out}
    for item in additions:
        text = _clean_text(item, limit=120)
        key = text.casefold() if text else ""
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        text_key = str(key)
        if _is_sensitive_key(text_key):
            continue
        out[text_key] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:40]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:40]]
    return _clean_text(value, limit=300)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if _contains_protected_marker(text):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _contains_protected_marker(value: str) -> bool:
    folded = value.casefold()
    return any(marker in folded for marker in _PROTECTED_MARKERS)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _warn(logger: Any | None, message: str, exc: Exception) -> None:
    if logger is not None and hasattr(logger, "warning"):
        logger.warning(message, exc)


__all__ = [
    "AUTHORITATIVE_SOURCE_ACTION_SCHEMA_VERSION",
    "AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY",
    "AuthoritativeSourceActionDecision",
    "AuthoritativeSourceActionFacts",
    "AuthoritativeSourceActionName",
    "AuthoritativeSourceActionResult",
    "build_authoritative_source_action",
    "build_authoritative_source_obligation_state_and_action",
]
