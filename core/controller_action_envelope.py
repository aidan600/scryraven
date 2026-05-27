"""Pure controller action envelope and registry for AG-25.

The shapes in this module describe controller-shaped decisions that already
exist in the runtime or answer-contract loop. They do not execute retrieval,
choose providers, alter prompts, persist data, call models, or route control
flow.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.answer_contract_controller import (
    AnswerControllerActionName,
    AnswerControllerActionResult,
)
from core.conflict_resolution_controller import (
    CONFLICT_RESOLUTION_PROVIDER_ROLE,
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    SourceClassRecoveryDecision,
)
from core.weak_corpus_controller import (
    WEAK_CORPUS_RECOVERY_PROVIDER_ROLE,
    WeakCorpusRecoveryControllerDecision,
    WeakCorpusRecoveryControllerInput,
    WeakCorpusRecoveryDecision,
)

CONTROLLER_ACTION_ENVELOPE_SCHEMA_VERSION = "controller_action_envelope_v1"

DIAGNOSE_QUESTION = AnswerControllerActionName.DIAGNOSE_QUESTION.value
SET_OR_UPDATE_ANSWER_CONTRACT = (
    AnswerControllerActionName.SET_OR_UPDATE_ANSWER_CONTRACT.value
)
INSPECT_EVIDENCE_STATE = AnswerControllerActionName.INSPECT_EVIDENCE_STATE.value
IDENTIFY_MISSING_INFORMATION = (
    AnswerControllerActionName.IDENTIFY_MISSING_INFORMATION.value
)
GENERATE_TARGETED_QUERIES = AnswerControllerActionName.GENERATE_TARGETED_QUERIES.value
RECOVER_WEAK_CORPUS = AnswerControllerActionName.RECOVER_WEAK_CORPUS.value
RESOLVE_CONFLICT = AnswerControllerActionName.RESOLVE_CONFLICT.value
DECOMPOSE_QUANTITATIVE_QUESTION = (
    AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION.value
)
ASK_USER_CLARIFICATION = AnswerControllerActionName.ASK_USER_CLARIFICATION.value
RECOVER_MISSING_SOURCE_CLASS = (
    AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value
)
RETRIEVE_TARGETED = AnswerControllerActionName.RETRIEVE_TARGETED.value
STOP_SUFFICIENT = AnswerControllerActionName.STOP_SUFFICIENT.value
STOP_INSUFFICIENT_WITH_CAVEAT = (
    AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT.value
)
REQUEST_SOCIAL_SIGNAL_CHECK = (
    AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK.value
)
RUN_SCRUTINEER_REVIEW = AnswerControllerActionName.RUN_SCRUTINEER_REVIEW.value
HANDOFF_TO_ANALYST = AnswerControllerActionName.HANDOFF_TO_ANALYST.value

OFFICIAL_OR_LEGAL_SOURCE_CLASSES = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
)

SOCIAL_SIGNAL_SIDE_PACKET_CLASSES = (
    "social_signal_side_packet",
    "social_perception_side_packet",
)

SOCIAL_SIGNAL_DISALLOWED_EVIDENCE_CLASSES = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
    "official_or_primary_evidence",
    "primary_evidence",
    "factual_evidence",
    "ordinary_factual_evidence",
)

SOURCE_CLASS_TRACE_KEYS = (
    "active_source_class_recovery_considered",
    "active_source_class_recovery_eligible",
    "active_source_class_recovery_used",
    "active_source_class_recovery_reason",
    "active_source_class_recovery_skip_reason",
    "active_source_class_recovery_blockers",
    "active_source_class_recovery_missing_classes",
    "active_source_class_recovery_queries",
    "active_source_class_recovery_provider_role",
    "active_source_class_recovery_search_depth",
    "active_source_class_recovery_attempt_count",
)

WEAK_CORPUS_TRACE_KEYS = (
    "weak_corpus_recovery_decision",
    "weak_corpus_recovery_reason",
    "weak_corpus_recovery_blockers",
    "weak_corpus_recovery_used",
    "weak_corpus_recovery_queries",
)

CONFLICT_RESOLUTION_TRACE_KEYS = (
    "active_conflict_resolution_considered",
    "active_conflict_resolution_eligible",
    "active_conflict_resolution_used",
    "active_conflict_resolution_reason",
    "active_conflict_resolution_skip_reason",
    "active_conflict_resolution_blockers",
    "active_conflict_resolution_conflict_notes",
    "active_conflict_resolution_queries",
    "active_conflict_resolution_provider_role",
    "active_conflict_resolution_search_depth",
    "active_conflict_resolution_attempt_count",
    "active_conflict_resolution_stage",
)

ANSWER_CONTRACT_TRACE_KEYS = (
    "answer_contract_action_history",
    "answer_contract_fulfillment_handoff",
)

_SENSITIVE_KEYS = {
    "api_key",
    "cache",
    "db_row",
    "full_trace",
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
}


class ControllerActionStatus(str, Enum):
    """Stable action result vocabulary."""

    APPROVED = "approved"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    SHADOW = "shadow"
    COMPLETED = "completed"
    FAILED = "failed"
    INFORMATIONAL = "informational"


class ControllerActionAuthority(str, Enum):
    """Where the action currently has authority."""

    ACTIVE = "active"
    PASSIVE = "passive"
    SHADOW = "shadow"
    FUTURE = "future"


class ControllerActionSideEffectClass(str, Enum):
    """Coarse side-effect class for an action envelope."""

    NONE = "none"
    RETRIEVAL = "retrieval"
    STOP = "stop"
    HANDOFF_ONLY = "handoff_only"
    SOCIAL_SIDE_PACKET = "social_side_packet"
    REVIEW_ONLY = "review_only"


class ControllerActionHandoffBoundary(str, Enum):
    """Boundary for material that can be handed onward."""

    HIDDEN = "hidden"
    SANITIZED_SUMMARY_ONLY = "sanitized_summary_only"
    ORDINARY_EVIDENCE_ELIGIBLE = "ordinary_evidence_eligible"
    FINAL_ANSWER_POSTURE_ONLY = "final_answer_posture_only"


@dataclass(frozen=True)
class ControllerActionDescriptor:
    """Registry descriptor for a controller action name."""

    name: str
    owner: str
    authority: ControllerActionAuthority
    side_effect_class: ControllerActionSideEffectClass
    executor: str | None
    handoff_boundary: ControllerActionHandoffBoundary
    known_limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "owner": self.owner,
            "authority": self.authority.value,
            "side_effect_class": self.side_effect_class.value,
            "executor": self.executor,
            "handoff_boundary": self.handoff_boundary.value,
            "known_limitations": list(self.known_limitations),
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerActionEnvelope:
    """Compact JSON-safe action envelope shared by controller-shaped decisions."""

    name: str
    status: ControllerActionStatus
    authority: ControllerActionAuthority
    reason: str | None = None
    skip_reason: str | None = None
    blockers: tuple[str, ...] = ()
    input_summary: dict[str, Any] = field(default_factory=dict)
    approved_work: dict[str, Any] = field(default_factory=dict)
    executor: str | None = None
    side_effect_class: ControllerActionSideEffectClass = (
        ControllerActionSideEffectClass.NONE
    )
    output_delta: dict[str, Any] = field(default_factory=dict)
    trace_keys: tuple[str, ...] = ()
    handoff_boundary: ControllerActionHandoffBoundary = (
        ControllerActionHandoffBoundary.HIDDEN
    )
    safety_notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_ACTION_ENVELOPE_SCHEMA_VERSION,
            "name": self.name,
            "status": self.status.value,
            "authority": self.authority.value,
            "reason": self.reason,
            "skip_reason": self.skip_reason,
            "blockers": list(self.blockers),
            "input_summary": _json_safe(self.input_summary),
            "approved_work": _json_safe(self.approved_work),
            "executor": self.executor,
            "side_effect_class": self.side_effect_class.value,
            "output_delta": _json_safe(self.output_delta),
            "trace_keys": list(self.trace_keys),
            "handoff_boundary": self.handoff_boundary.value,
            "safety_notes": list(self.safety_notes),
            "metadata": _json_safe(self.metadata),
        }


def _enum_value(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _copy_string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    out: list[str] = []
    for item in value:
        text = " ".join(str(item or "").strip().split())
        if text:
            out.append(text)
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


def _merge_metadata(*items: Mapping[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for item in items:
        if item:
            merged.update(deepcopy(dict(item)))
    return _json_safe(merged)


def _descriptor(name: str) -> ControllerActionDescriptor:
    try:
        return _ACTION_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"unknown controller action: {name}") from exc


def _inactive_side_effect(
    status: ControllerActionStatus,
    side_effect_class: ControllerActionSideEffectClass,
) -> ControllerActionSideEffectClass:
    if status in {
        ControllerActionStatus.BLOCKED,
        ControllerActionStatus.SKIPPED,
        ControllerActionStatus.INFORMATIONAL,
    }:
        return ControllerActionSideEffectClass.NONE
    return side_effect_class


def _inactive_executor(
    status: ControllerActionStatus,
    executor: str | None,
) -> str | None:
    if status in {
        ControllerActionStatus.BLOCKED,
        ControllerActionStatus.SKIPPED,
        ControllerActionStatus.INFORMATIONAL,
    }:
        return None
    return executor


def _source_class_status(
    decision: SourceClassRecoveryDecision,
) -> ControllerActionStatus:
    decision_value = _enum_value(decision.decision)
    if (
        decision_value
        == SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY.value
    ):
        return ControllerActionStatus.APPROVED
    if decision_value == SourceClassRecoveryControllerDecision.NO_ACTION.value:
        return ControllerActionStatus.SKIPPED
    return ControllerActionStatus.BLOCKED


def _weak_corpus_status(
    decision: WeakCorpusRecoveryDecision,
) -> ControllerActionStatus:
    decision_value = _enum_value(decision.decision)
    if (
        decision_value
        == WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY.value
    ):
        return ControllerActionStatus.APPROVED
    if decision_value == WeakCorpusRecoveryControllerDecision.NO_ACTION.value:
        return ControllerActionStatus.SKIPPED
    return ControllerActionStatus.BLOCKED


def _conflict_resolution_status(
    decision: ConflictResolutionDecision,
) -> ControllerActionStatus:
    decision_value = _enum_value(decision.decision)
    if (
        decision_value
        == ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION.value
    ):
        return ControllerActionStatus.APPROVED
    if decision_value == ConflictResolutionControllerDecision.NO_ACTION.value:
        return ControllerActionStatus.SKIPPED
    return ControllerActionStatus.BLOCKED


def _legal_source_recovery_notes(
    missing_classes: Sequence[str],
    reason: str | None,
) -> tuple[str, ...]:
    normalized = {str(item).casefold() for item in missing_classes}
    if normalized & set(OFFICIAL_OR_LEGAL_SOURCE_CLASSES) or str(
        reason or ""
    ).startswith("answer_contract_"):
        return (
            "official/legal recovery remains a limited source-class action; "
            "AG-22 live validation did not prove final official/current-primary "
            "source quality from allowed artifacts",
        )
    return ()


def _retrieval_stop_trace_keys(authority: ControllerActionAuthority) -> tuple[str, ...]:
    prefix = "retrieval_stop_shadow"
    if authority is ControllerActionAuthority.ACTIVE:
        prefix = "retrieval_stop_active"
    return (
        f"{prefix}_available",
        f"{prefix}_decision",
        f"{prefix}_reason",
        f"{prefix}_blockers",
        f"{prefix}_next_query_count",
        f"{prefix}_stage",
        f"{prefix}_mode",
    )


def _retrieval_stop_name(decision: RetrievalStopDecision) -> str:
    decision_value = _enum_value(decision.decision)
    if decision_value == RetrievalStopControllerDecision.CONTINUE_RETRIEVAL.value:
        return RETRIEVE_TARGETED
    if decision_value == RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS.value:
        return STOP_SUFFICIENT
    return STOP_INSUFFICIENT_WITH_CAVEAT


def _retrieval_stop_status(
    decision: RetrievalStopDecision,
    authority: ControllerActionAuthority,
) -> ControllerActionStatus:
    if authority is ControllerActionAuthority.SHADOW:
        return ControllerActionStatus.INFORMATIONAL
    decision_value = _enum_value(decision.decision)
    if decision_value == RetrievalStopControllerDecision.CONTINUE_RETRIEVAL.value:
        return ControllerActionStatus.APPROVED
    if decision_value == RetrievalStopControllerDecision.BLOCKED_WITH_REASON.value:
        return ControllerActionStatus.BLOCKED
    return ControllerActionStatus.COMPLETED


def _retrieval_stop_side_effect(
    name: str,
    status: ControllerActionStatus,
    descriptor: ControllerActionDescriptor,
) -> ControllerActionSideEffectClass:
    if status is ControllerActionStatus.INFORMATIONAL:
        return ControllerActionSideEffectClass.NONE
    if name == RETRIEVE_TARGETED and status is ControllerActionStatus.APPROVED:
        return ControllerActionSideEffectClass.RETRIEVAL
    if name in {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT} and status in {
        ControllerActionStatus.COMPLETED,
        ControllerActionStatus.APPROVED,
    }:
        return ControllerActionSideEffectClass.STOP
    return _inactive_side_effect(status, descriptor.side_effect_class)


def _retrieval_stop_boundary(
    name: str,
    descriptor: ControllerActionDescriptor,
) -> ControllerActionHandoffBoundary:
    if name in {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}:
        return ControllerActionHandoffBoundary.FINAL_ANSWER_POSTURE_ONLY
    return descriptor.handoff_boundary


def _answer_action_status(
    action: AnswerControllerActionResult,
) -> ControllerActionStatus:
    name = _enum_value(action.action_name)
    if action.skip_reason_or_none:
        return ControllerActionStatus.SKIPPED
    if name in {STOP_SUFFICIENT, STOP_INSUFFICIENT_WITH_CAVEAT}:
        return ControllerActionStatus.COMPLETED
    return ControllerActionStatus.APPROVED


def _answer_action_side_effect(
    status: ControllerActionStatus,
    descriptor: ControllerActionDescriptor,
) -> ControllerActionSideEffectClass:
    if status is ControllerActionStatus.SKIPPED:
        return ControllerActionSideEffectClass.NONE
    return descriptor.side_effect_class


_ACTION_REGISTRY: dict[str, ControllerActionDescriptor] = {
    DIAGNOSE_QUESTION: ControllerActionDescriptor(
        name=DIAGNOSE_QUESTION,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.NONE,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.HIDDEN,
        known_limitations=(
            "offline/passive contract action only",
        ),
    ),
    SET_OR_UPDATE_ANSWER_CONTRACT: ControllerActionDescriptor(
        name=SET_OR_UPDATE_ANSWER_CONTRACT,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.HANDOFF_ONLY,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "contract updates remain answer-contract state only",
        ),
    ),
    INSPECT_EVIDENCE_STATE: ControllerActionDescriptor(
        name=INSPECT_EVIDENCE_STATE,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.NONE,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.HIDDEN,
        known_limitations=(
            "describes already-computed evidence facts only",
        ),
    ),
    IDENTIFY_MISSING_INFORMATION: ControllerActionDescriptor(
        name=IDENTIFY_MISSING_INFORMATION,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.HANDOFF_ONLY,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "does not request live clarification or new retrieval by itself",
        ),
    ),
    GENERATE_TARGETED_QUERIES: ControllerActionDescriptor(
        name=GENERATE_TARGETED_QUERIES,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.NONE,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.HIDDEN,
        known_limitations=(
            "query generation vocabulary only; retrieval remains a separate action",
        ),
    ),
    RECOVER_WEAK_CORPUS: ControllerActionDescriptor(
        name=RECOVER_WEAK_CORPUS,
        owner="weak_corpus_controller",
        authority=ControllerActionAuthority.ACTIVE,
        side_effect_class=ControllerActionSideEffectClass.RETRIEVAL,
        executor="core.pipeline_orchestrator:weak_corpus_recovery_branch",
        handoff_boundary=ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE,
        known_limitations=(
            "one first-pass attempt only",
            "execution remains inside orchestrator control flow",
            "does not choose providers, routing, depth, prompts, or persistence",
        ),
    ),
    RECOVER_MISSING_SOURCE_CLASS: ControllerActionDescriptor(
        name=RECOVER_MISSING_SOURCE_CLASS,
        owner="source_class_recovery_controller",
        authority=ControllerActionAuthority.ACTIVE,
        side_effect_class=ControllerActionSideEffectClass.RETRIEVAL,
        executor="core.source_class_recovery_executor:execute_source_class_recovery_action",
        handoff_boundary=ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE,
        known_limitations=(
            "one bounded source-class attempt only",
            "reuses current providers and search depth",
            "official/legal recovery remains limited by AG-22 visibility gap",
        ),
    ),
    RETRIEVE_TARGETED: ControllerActionDescriptor(
        name=RETRIEVE_TARGETED,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.RETRIEVAL,
        executor="core.pipeline_orchestrator:existing_retrieval_loop",
        handoff_boundary=ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE,
        known_limitations=(
            "answer-contract action vocabulary is not the runtime scheduler yet",
            "provider routing and search depth remain orchestrator-owned",
        ),
    ),
    RESOLVE_CONFLICT: ControllerActionDescriptor(
        name=RESOLVE_CONFLICT,
        owner="conflict_resolution_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.RETRIEVAL,
        executor="core.conflict_resolution_executor:execute_conflict_resolution_action",
        handoff_boundary=ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE,
        known_limitations=(
            "AG-37B adds checkpoint dispatch plumbing, but normal runtime has no conflict fact producer yet",
            "execution must use conflict_resolution provider_role",
            "does not choose providers, routing, depth, prompts, or persistence",
            "ordinary next_queries are not resolving_queries",
        ),
        metadata={
            "active_runtime_dispatch": False,
            "checkpoint_dispatch_plumbing": True,
            "blocked_on": "conflict_state_production",
            "provider_role": CONFLICT_RESOLUTION_PROVIDER_ROLE,
            "query_source": "resolving_queries_only",
        },
    ),
    DECOMPOSE_QUANTITATIVE_QUESTION: ControllerActionDescriptor(
        name=DECOMPOSE_QUANTITATIVE_QUESTION,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.HANDOFF_ONLY,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "descriptive only; does not expose raw Economist or quantitative packet material",
        ),
    ),
    STOP_SUFFICIENT: ControllerActionDescriptor(
        name=STOP_SUFFICIENT,
        owner="retrieval_stop_controller",
        authority=ControllerActionAuthority.SHADOW,
        side_effect_class=ControllerActionSideEffectClass.STOP,
        executor="core.pipeline_orchestrator:legacy_synthesis_branch",
        handoff_boundary=ControllerActionHandoffBoundary.FINAL_ANSWER_POSTURE_ONLY,
        known_limitations=(
            "retrieval-stop sufficient branch is shadow/passive in current runtime",
        ),
    ),
    STOP_INSUFFICIENT_WITH_CAVEAT: ControllerActionDescriptor(
        name=STOP_INSUFFICIENT_WITH_CAVEAT,
        owner="retrieval_stop_controller",
        authority=ControllerActionAuthority.ACTIVE,
        side_effect_class=ControllerActionSideEffectClass.STOP,
        executor="core.pipeline_orchestrator:legacy_terminal_stop_branches",
        handoff_boundary=ControllerActionHandoffBoundary.FINAL_ANSWER_POSTURE_ONLY,
        known_limitations=(
            "active only for already-terminal no-query or budget-exhausted branches",
            "does not own continuation dispatch or recovery sequencing",
        ),
    ),
    REQUEST_SOCIAL_SIGNAL_CHECK: ControllerActionDescriptor(
        name=REQUEST_SOCIAL_SIGNAL_CHECK,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.FUTURE,
        side_effect_class=ControllerActionSideEffectClass.SOCIAL_SIDE_PACKET,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "placeholder only; no social runtime provider integration",
            "side-packet perception signal only",
            "cannot satisfy official, legal, current-primary, or factual evidence",
            "cannot enter ordinary factual evidence",
        ),
        metadata={
            "ordinary_evidence_eligible": False,
            "disallowed_evidence_classes": SOCIAL_SIGNAL_DISALLOWED_EVIDENCE_CLASSES,
        },
    ),
    RUN_SCRUTINEER_REVIEW: ControllerActionDescriptor(
        name=RUN_SCRUTINEER_REVIEW,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.REVIEW_ONLY,
        executor="existing_scrutineer_boundary:not_controller_dispatched",
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "answer-contract can represent the review need, but does not rewrite Scrutineer policy",
        ),
    ),
    HANDOFF_TO_ANALYST: ControllerActionDescriptor(
        name=HANDOFF_TO_ANALYST,
        owner="answer_contract_runtime_handoff",
        authority=ControllerActionAuthority.PASSIVE,
        side_effect_class=ControllerActionSideEffectClass.HANDOFF_ONLY,
        executor="existing_analyst_author_handoff_boundary",
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "protected handoff surface; envelope is descriptive only",
        ),
    ),
    ASK_USER_CLARIFICATION: ControllerActionDescriptor(
        name=ASK_USER_CLARIFICATION,
        owner="answer_contract_controller",
        authority=ControllerActionAuthority.FUTURE,
        side_effect_class=ControllerActionSideEffectClass.HANDOFF_ONLY,
        executor=None,
        handoff_boundary=ControllerActionHandoffBoundary.SANITIZED_SUMMARY_ONLY,
        known_limitations=(
            "future interaction action; not wired into current runtime loop",
        ),
    ),
}


def controller_action_registry() -> dict[str, dict[str, Any]]:
    """Return the JSON-safe registry keyed by action name."""
    return {
        name: _ACTION_REGISTRY[name].to_dict()
        for name in sorted(_ACTION_REGISTRY)
    }


def controller_action_names() -> tuple[str, ...]:
    """Return stable registry action names."""
    return tuple(sorted(_ACTION_REGISTRY))


def get_controller_action_descriptor(name: str) -> ControllerActionDescriptor:
    """Return one registry descriptor by action name."""
    return _descriptor(str(name))


def envelope_from_source_class_recovery_decision(
    decision: SourceClassRecoveryDecision,
    *,
    input_summary: Mapping[str, Any] | None = None,
    trace_keys: Sequence[str] = SOURCE_CLASS_TRACE_KEYS,
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Represent a source-class recovery decision as an action envelope."""
    descriptor = _descriptor(RECOVER_MISSING_SOURCE_CLASS)
    status = _source_class_status(decision)
    side_effect = _inactive_side_effect(status, descriptor.side_effect_class)
    executor = _inactive_executor(status, descriptor.executor)
    approved = status is ControllerActionStatus.APPROVED
    skip_reason = None if approved else decision.reason or _enum_value(decision.decision)
    safety_notes = descriptor.known_limitations + _legal_source_recovery_notes(
        decision.missing_expected_source_classes,
        decision.reason,
    )

    return ControllerActionEnvelope(
        name=RECOVER_MISSING_SOURCE_CLASS,
        status=status,
        authority=ControllerActionAuthority.ACTIVE,
        reason=decision.reason,
        skip_reason=skip_reason,
        blockers=_copy_string_tuple(decision.blockers),
        input_summary={
            "missing_expected_source_classes": decision.missing_expected_source_classes,
            "query_count": len(decision.queries),
            "attempt_count": decision.attempt_count,
            **dict(input_summary or {}),
        },
        approved_work=(
            {
                "queries": decision.queries,
                "provider_role": decision.provider_role,
                "search_depth": decision.search_depth,
                "missing_expected_source_classes": (
                    decision.missing_expected_source_classes
                ),
                "attempt_count": decision.attempt_count,
            }
            if approved
            else {}
        ),
        executor=executor,
        side_effect_class=side_effect,
        output_delta=(
            {
                "recover_missing_source_class_attempted": approved,
                "attempt_count": decision.attempt_count,
            }
            if approved
            else {}
        ),
        trace_keys=_copy_string_tuple(trace_keys),
        handoff_boundary=descriptor.handoff_boundary,
        safety_notes=safety_notes,
        metadata=_merge_metadata(
            {
                "controller_decision": _enum_value(decision.decision),
                "provider_role": decision.provider_role,
                "known_action_descriptor": descriptor.name,
            },
            metadata,
        ),
    )


def envelope_from_weak_corpus_recovery_decision(
    decision: WeakCorpusRecoveryDecision,
    *,
    snapshot: WeakCorpusRecoveryControllerInput | None = None,
    input_summary: Mapping[str, Any] | None = None,
    trace_keys: Sequence[str] = WEAK_CORPUS_TRACE_KEYS,
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Represent a weak-corpus recovery decision as an action envelope."""
    descriptor = _descriptor(RECOVER_WEAK_CORPUS)
    status = _weak_corpus_status(decision)
    side_effect = _inactive_side_effect(status, descriptor.side_effect_class)
    executor = _inactive_executor(status, descriptor.executor)
    approved = status is ControllerActionStatus.APPROVED
    skip_reason = None if approved else decision.reason
    snapshot_summary: dict[str, Any] = {}
    budget_metadata: dict[str, Any] = {
        "one_attempt_only": True,
        "budget_owner": "orchestrator_iteration_budget",
        "execution_owner": "pipeline_orchestrator_weak_corpus_branch",
    }
    if snapshot is not None:
        snapshot_summary = {
            "corpus_state": snapshot.corpus_state,
            "corpus_weak": snapshot.corpus_weak,
            "iteration": snapshot.iteration,
            "max_iterations": snapshot.max_iterations,
            "prior_attempted": snapshot.prior_attempted,
            "readable_passage_count": snapshot.readable_passage_count,
            "query_count": len(snapshot.recovery_queries),
        }
        budget_metadata.update(
            {
                "iteration": snapshot.iteration,
                "max_iterations": snapshot.max_iterations,
                "prior_attempted": snapshot.prior_attempted,
                "readable_passage_count": snapshot.readable_passage_count,
            }
        )

    return ControllerActionEnvelope(
        name=RECOVER_WEAK_CORPUS,
        status=status,
        authority=ControllerActionAuthority.ACTIVE,
        reason=decision.reason,
        skip_reason=skip_reason,
        blockers=_copy_string_tuple(decision.blockers),
        input_summary={
            **snapshot_summary,
            "approved_query_count": len(decision.queries),
            **dict(input_summary or {}),
        },
        approved_work=(
            {
                "queries": decision.queries,
                "provider_role": WEAK_CORPUS_RECOVERY_PROVIDER_ROLE,
            }
            if approved
            else {}
        ),
        executor=executor,
        side_effect_class=side_effect,
        output_delta={"recover_weak_corpus_attempted": approved} if approved else {},
        trace_keys=_copy_string_tuple(trace_keys),
        handoff_boundary=descriptor.handoff_boundary,
        safety_notes=descriptor.known_limitations,
        metadata=_merge_metadata(
            budget_metadata,
            {
                "controller_decision": _enum_value(decision.decision),
                "known_action_descriptor": descriptor.name,
            },
            metadata,
        ),
    )


def envelope_from_conflict_resolution_decision(
    decision: ConflictResolutionDecision,
    *,
    input_summary: Mapping[str, Any] | None = None,
    trace_keys: Sequence[str] = CONFLICT_RESOLUTION_TRACE_KEYS,
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Represent a passive conflict-resolution decision as an action envelope."""
    descriptor = _descriptor(RESOLVE_CONFLICT)
    status = _conflict_resolution_status(decision)
    side_effect = _inactive_side_effect(status, descriptor.side_effect_class)
    executor = _inactive_executor(status, descriptor.executor)
    approved = status is ControllerActionStatus.APPROVED
    skip_reason = None if approved else decision.reason

    return ControllerActionEnvelope(
        name=RESOLVE_CONFLICT,
        status=status,
        authority=ControllerActionAuthority.PASSIVE,
        reason=decision.reason,
        skip_reason=skip_reason,
        blockers=_copy_string_tuple(decision.blockers),
        input_summary={
            "conflict_note_count": len(decision.conflict_notes),
            "resolving_query_count": len(decision.queries),
            "attempt_count": decision.attempt_count,
            **dict(input_summary or {}),
        },
        approved_work=(
            {
                "queries": decision.queries,
                "provider_role": CONFLICT_RESOLUTION_PROVIDER_ROLE,
                "search_depth": decision.search_depth,
                "stage": decision.stage,
                "attempt_count": decision.attempt_count,
            }
            if approved
            else {}
        ),
        executor=executor,
        side_effect_class=side_effect,
        output_delta=(
            {
                "resolve_conflict_attempted": False,
                "active_runtime_dispatch": False,
            }
            if approved
            else {}
        ),
        trace_keys=_copy_string_tuple(trace_keys),
        handoff_boundary=descriptor.handoff_boundary,
        safety_notes=descriptor.known_limitations,
        metadata=_merge_metadata(
            {
                "controller_decision": _enum_value(decision.decision),
                "known_action_descriptor": descriptor.name,
                "active_runtime_dispatch": False,
                "query_source": "resolving_queries_only",
                "provider_role": CONFLICT_RESOLUTION_PROVIDER_ROLE,
            },
            metadata,
        ),
    )


def envelope_from_retrieval_stop_decision(
    decision: RetrievalStopDecision,
    *,
    authority: ControllerActionAuthority = ControllerActionAuthority.SHADOW,
    stage: str | None = None,
    mode: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Represent a retrieval-stop decision as an action envelope."""
    name = _retrieval_stop_name(decision)
    descriptor = _descriptor(name)
    status = _retrieval_stop_status(decision, authority)
    side_effect = _retrieval_stop_side_effect(name, status, descriptor)
    executor = _inactive_executor(status, descriptor.executor)
    boundary = _retrieval_stop_boundary(name, descriptor)
    approved_work = {}
    if name == RETRIEVE_TARGETED and status is ControllerActionStatus.APPROVED:
        approved_work = {
            "queries": decision.next_queries,
            "query_source": decision.query_source,
        }
    posture = (
        "answer from sufficient evidence"
        if name == STOP_SUFFICIENT
        else "answer with caveats"
        if name == STOP_INSUFFICIENT_WITH_CAVEAT
        else None
    )

    return ControllerActionEnvelope(
        name=name,
        status=status,
        authority=authority,
        reason=decision.reason,
        skip_reason=decision.reason if status is ControllerActionStatus.BLOCKED else None,
        blockers=_copy_string_tuple(decision.blockers),
        input_summary={
            "next_query_count": len(decision.next_queries),
            "query_source": decision.query_source,
            "redundancy_score": decision.redundancy_score,
            "stage": stage,
            "mode": mode,
        },
        approved_work=approved_work,
        executor=executor,
        side_effect_class=side_effect,
        output_delta=(
            {
                "stop_state": {
                    "controller_decision": _enum_value(decision.decision),
                    "reason": decision.reason,
                    "final_answer_posture": posture,
                }
            }
            if posture and status is not ControllerActionStatus.INFORMATIONAL
            else {}
        ),
        trace_keys=_retrieval_stop_trace_keys(authority),
        handoff_boundary=boundary,
        safety_notes=descriptor.known_limitations,
        metadata=_merge_metadata(
            {
                "controller_decision": _enum_value(decision.decision),
                "known_action_descriptor": descriptor.name,
            },
            metadata,
        ),
    )


def envelope_from_answer_contract_action_result(
    action: AnswerControllerActionResult,
    *,
    authority: ControllerActionAuthority = ControllerActionAuthority.PASSIVE,
    trace_keys: Sequence[str] = ANSWER_CONTRACT_TRACE_KEYS,
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Represent one answer-contract action result without changing semantics."""
    name = _enum_value(action.action_name)
    descriptor = _descriptor(name)
    status = _answer_action_status(action)
    side_effect = _answer_action_side_effect(status, descriptor)
    executor = _inactive_executor(status, descriptor.executor)
    approved_work = {}
    if action.approved_queries_or_none:
        approved_work["queries"] = action.approved_queries_or_none
    if action.contract_items_affected:
        approved_work["contract_items_affected"] = action.contract_items_affected

    return ControllerActionEnvelope(
        name=name,
        status=status,
        authority=authority,
        reason=action.reason,
        skip_reason=action.skip_reason_or_none,
        blockers=(
            (action.skip_reason_or_none,) if action.skip_reason_or_none else ()
        ),
        input_summary={
            "preconditions": action.preconditions,
            "iteration": action.iteration,
            "stable_reason_code": action.stable_reason_code,
        },
        approved_work=approved_work,
        executor=executor,
        side_effect_class=side_effect,
        output_delta=action.next_state_delta,
        trace_keys=_copy_string_tuple(trace_keys),
        handoff_boundary=descriptor.handoff_boundary,
        safety_notes=descriptor.known_limitations,
        metadata=_merge_metadata(
            {
                "stable_reason_code": action.stable_reason_code,
                "approved": action.approved,
                "known_action_descriptor": descriptor.name,
            },
            metadata,
        ),
    )


def envelopes_from_answer_contract_action_history(
    action_history: Sequence[AnswerControllerActionResult],
    *,
    authority: ControllerActionAuthority = ControllerActionAuthority.PASSIVE,
) -> tuple[ControllerActionEnvelope, ...]:
    """Represent an answer-contract action history as envelopes."""
    return tuple(
        envelope_from_answer_contract_action_result(action, authority=authority)
        for action in action_history
    )


def social_signal_placeholder_envelope(
    *,
    reason: str = "Social signal check is represented as a future side-packet action.",
    metadata: Mapping[str, Any] | None = None,
) -> ControllerActionEnvelope:
    """Return the future social-signal placeholder envelope."""
    descriptor = _descriptor(REQUEST_SOCIAL_SIGNAL_CHECK)
    return ControllerActionEnvelope(
        name=REQUEST_SOCIAL_SIGNAL_CHECK,
        status=ControllerActionStatus.INFORMATIONAL,
        authority=ControllerActionAuthority.FUTURE,
        reason=reason,
        input_summary={
            "ordinary_evidence_eligible": False,
            "disallowed_evidence_classes": SOCIAL_SIGNAL_DISALLOWED_EVIDENCE_CLASSES,
        },
        approved_work={
            "side_packet": "author_safe_social_signal_summary_only",
            "eligible_side_packet_classes": SOCIAL_SIGNAL_SIDE_PACKET_CLASSES,
        },
        executor=None,
        side_effect_class=descriptor.side_effect_class,
        output_delta={
            "social_signal_status": "placeholder_future_action",
            "ordinary_evidence_eligible": False,
        },
        trace_keys=ANSWER_CONTRACT_TRACE_KEYS,
        handoff_boundary=descriptor.handoff_boundary,
        safety_notes=descriptor.known_limitations,
        metadata=_merge_metadata(
            {
                "known_action_descriptor": descriptor.name,
                "cannot_satisfy_evidence_classes": (
                    SOCIAL_SIGNAL_DISALLOWED_EVIDENCE_CLASSES
                ),
            },
            metadata,
        ),
    )


def action_can_enter_ordinary_evidence(action_name: str) -> bool:
    """Return whether an action's output can enter ordinary factual evidence."""
    descriptor = _descriptor(str(action_name))
    return (
        descriptor.handoff_boundary
        is ControllerActionHandoffBoundary.ORDINARY_EVIDENCE_ELIGIBLE
    )


def action_can_satisfy_evidence_class(action_name: str, evidence_class: str) -> bool:
    """Return whether an action can satisfy an evidence class by boundary only."""
    normalized_action = str(action_name)
    normalized_class = str(evidence_class or "").strip().casefold()
    if normalized_action == REQUEST_SOCIAL_SIGNAL_CHECK:
        return normalized_class in SOCIAL_SIGNAL_SIDE_PACKET_CLASSES
    return action_can_enter_ordinary_evidence(normalized_action)


__all__ = [
    "ANSWER_CONTRACT_TRACE_KEYS",
    "ASK_USER_CLARIFICATION",
    "CONFLICT_RESOLUTION_TRACE_KEYS",
    "CONTROLLER_ACTION_ENVELOPE_SCHEMA_VERSION",
    "DECOMPOSE_QUANTITATIVE_QUESTION",
    "DIAGNOSE_QUESTION",
    "GENERATE_TARGETED_QUERIES",
    "HANDOFF_TO_ANALYST",
    "IDENTIFY_MISSING_INFORMATION",
    "INSPECT_EVIDENCE_STATE",
    "OFFICIAL_OR_LEGAL_SOURCE_CLASSES",
    "RECOVER_MISSING_SOURCE_CLASS",
    "RECOVER_WEAK_CORPUS",
    "REQUEST_SOCIAL_SIGNAL_CHECK",
    "RETRIEVE_TARGETED",
    "RESOLVE_CONFLICT",
    "RUN_SCRUTINEER_REVIEW",
    "SET_OR_UPDATE_ANSWER_CONTRACT",
    "SOCIAL_SIGNAL_DISALLOWED_EVIDENCE_CLASSES",
    "SOCIAL_SIGNAL_SIDE_PACKET_CLASSES",
    "SOURCE_CLASS_TRACE_KEYS",
    "STOP_INSUFFICIENT_WITH_CAVEAT",
    "STOP_SUFFICIENT",
    "WEAK_CORPUS_TRACE_KEYS",
    "ControllerActionAuthority",
    "ControllerActionDescriptor",
    "ControllerActionEnvelope",
    "ControllerActionHandoffBoundary",
    "ControllerActionSideEffectClass",
    "ControllerActionStatus",
    "action_can_enter_ordinary_evidence",
    "action_can_satisfy_evidence_class",
    "controller_action_names",
    "controller_action_registry",
    "envelope_from_answer_contract_action_result",
    "envelope_from_conflict_resolution_decision",
    "envelope_from_retrieval_stop_decision",
    "envelope_from_source_class_recovery_decision",
    "envelope_from_weak_corpus_recovery_decision",
    "envelopes_from_answer_contract_action_history",
    "get_controller_action_descriptor",
    "social_signal_placeholder_envelope",
]
