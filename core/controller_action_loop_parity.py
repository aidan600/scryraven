"""Offline controller action-loop parity harness for AG-26.

This module replays already-shaped controller facts through the AG-25 action
envelope. It does not execute retrieval, choose providers, alter prompts,
persist data, call models, or change runtime authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping

from core.answer_contract_controller import AnswerControllerActionResult
from core.answer_contract_pipeline_adapter import (
    PipelineAnswerContractFacts,
    adapt_pipeline_facts_to_answer_contract_controller,
)
from core.controller_action_envelope import (
    OFFICIAL_OR_LEGAL_SOURCE_CLASSES,
    RECOVER_MISSING_SOURCE_CLASS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    STOP_SUFFICIENT,
    ControllerActionAuthority,
    ControllerActionEnvelope,
    envelope_from_answer_contract_action_result,
    envelope_from_retrieval_stop_decision,
    envelope_from_source_class_recovery_decision,
    envelope_from_weak_corpus_recovery_decision,
    get_controller_action_descriptor,
    social_signal_placeholder_envelope,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopControllerInput,
    RetrievalStopDecision,
    decide_retrieval_stop,
)
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerInput,
    SourceClassRecoveryDecision,
    decide_source_class_recovery,
)
from core.weak_corpus_controller import (
    WeakCorpusRecoveryControllerInput,
    WeakCorpusRecoveryDecision,
    decide_weak_corpus_recovery,
)

CONTROLLER_ACTION_LOOP_PARITY_SCHEMA_VERSION = "controller_action_loop_parity_v1"

OFFICIAL_LEGAL_RECOVERY_LIMITATION_GAP = "official_legal_recovery_limited_ag22"
SOCIAL_SIGNAL_SIDE_PACKET_ONLY_GAP = "social_signal_future_side_packet_only"
ACTIVE_RETRIEVAL_STOP_CONTINUE_GAP = "active_retrieval_stop_continue_not_runtime_owned"
ACTIVE_STOP_SUFFICIENT_GAP = "active_stop_sufficient_not_runtime_owned"
SNAPSHOT_DECISION_MISMATCH_GAP = "snapshot_decision_mismatch"
UNKNOWN_ENVELOPE_ACTION_GAP = "unknown_envelope_action"

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


class ControllerActionLoopParityStatus(str, Enum):
    """Compact replay status for the offline parity harness."""

    REPLAYED = "replayed"
    REPLAYED_WITH_KNOWN_GAPS = "replayed_with_known_gaps"
    NOT_REPRESENTABLE = "not_representable"
    NO_ACTIONS = "no_actions"


@dataclass(frozen=True)
class ControllerActionLoopParityGap:
    """Known representational gap surfaced by the offline replay."""

    code: str
    reason: str
    action_name: str | None = None
    represented_by_envelope: bool = True
    blocks_runtime_promotion: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "reason": self.reason,
            "action_name": self.action_name,
            "represented_by_envelope": self.represented_by_envelope,
            "blocks_runtime_promotion": self.blocks_runtime_promotion,
            "metadata": _json_safe(self.metadata),
        }


@dataclass(frozen=True)
class ControllerActionLoopParityFacts:
    """Synthetic or trace-shaped facts for the offline parity replay."""

    weak_corpus_snapshot: WeakCorpusRecoveryControllerInput | None = None
    weak_corpus_decision: WeakCorpusRecoveryDecision | None = None
    source_class_snapshot: SourceClassRecoveryControllerInput | None = None
    source_class_decision: SourceClassRecoveryDecision | None = None
    retrieval_stop_snapshot: RetrievalStopControllerInput | None = None
    retrieval_stop_decision: RetrievalStopDecision | None = None
    retrieval_stop_authority: ControllerActionAuthority = ControllerActionAuthority.SHADOW
    retrieval_stop_stage: str | None = None
    retrieval_stop_mode: str | None = None
    answer_contract_action_history: tuple[AnswerControllerActionResult, ...] = ()
    answer_contract_pipeline_facts: PipelineAnswerContractFacts | None = None
    include_social_signal_placeholder: bool = False
    social_signal_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControllerActionLoopParityResult:
    """Ordered AG-25 envelopes plus compact parity metadata."""

    envelopes: tuple[ControllerActionEnvelope, ...]
    gaps: tuple[ControllerActionLoopParityGap, ...] = ()
    answer_contract_fulfillment: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> ControllerActionLoopParityStatus:
        if not self.envelopes:
            return (
                ControllerActionLoopParityStatus.NOT_REPRESENTABLE
                if self.gaps
                else ControllerActionLoopParityStatus.NO_ACTIONS
            )
        if any(not gap.represented_by_envelope for gap in self.gaps):
            return ControllerActionLoopParityStatus.NOT_REPRESENTABLE
        if self.gaps:
            return ControllerActionLoopParityStatus.REPLAYED_WITH_KNOWN_GAPS
        return ControllerActionLoopParityStatus.REPLAYED

    @property
    def compact_action_history(self) -> tuple[dict[str, Any], ...]:
        history: list[dict[str, Any]] = []
        for index, envelope in enumerate(self.envelopes, start=1):
            payload = envelope.to_dict()
            history.append(
                {
                    "index": index,
                    "name": payload["name"],
                    "status": payload["status"],
                    "authority": payload["authority"],
                    "side_effect_class": payload["side_effect_class"],
                    "reason": payload["reason"],
                    "skip_reason": payload["skip_reason"],
                    "handoff_boundary": payload["handoff_boundary"],
                }
            )
        return tuple(history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_ACTION_LOOP_PARITY_SCHEMA_VERSION,
            "status": self.status.value,
            "action_count": len(self.envelopes),
            "actions": list(self.compact_action_history),
            "envelopes": [envelope.to_dict() for envelope in self.envelopes],
            "gaps": [gap.to_dict() for gap in self.gaps],
            "answer_contract_fulfillment": _json_safe(
                self.answer_contract_fulfillment
            ),
            "metadata": _json_safe(self.metadata),
        }


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


def _decision_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    return _json_safe(value)


def _append_envelope(
    envelopes: list[ControllerActionEnvelope],
    gaps: list[ControllerActionLoopParityGap],
    envelope: ControllerActionEnvelope,
) -> None:
    try:
        get_controller_action_descriptor(envelope.name)
    except KeyError:
        gaps.append(
            ControllerActionLoopParityGap(
                code=UNKNOWN_ENVELOPE_ACTION_GAP,
                reason="The AG-25 registry does not know this action name.",
                action_name=envelope.name,
                represented_by_envelope=False,
            )
        )
        return
    envelopes.append(envelope)


def _mismatch_gap(
    *,
    action_name: str,
    supplied: Any,
    recomputed: Any,
) -> ControllerActionLoopParityGap:
    return ControllerActionLoopParityGap(
        code=SNAPSHOT_DECISION_MISMATCH_GAP,
        reason=(
            "A supplied controller decision differs from the decision recomputed "
            "from the supplied offline snapshot."
        ),
        action_name=action_name,
        metadata={
            "supplied_decision": _decision_payload(supplied),
            "recomputed_decision": _decision_payload(recomputed),
        },
    )


def _weak_corpus_decision_from_facts(
    facts: ControllerActionLoopParityFacts,
    gaps: list[ControllerActionLoopParityGap],
) -> WeakCorpusRecoveryDecision | None:
    if facts.weak_corpus_snapshot is None:
        return facts.weak_corpus_decision

    recomputed = decide_weak_corpus_recovery(facts.weak_corpus_snapshot)
    if (
        facts.weak_corpus_decision is not None
        and facts.weak_corpus_decision.to_dict() != recomputed.to_dict()
    ):
        gaps.append(
            _mismatch_gap(
                action_name="recover_weak_corpus",
                supplied=facts.weak_corpus_decision,
                recomputed=recomputed,
            )
        )
    return facts.weak_corpus_decision or recomputed


def _source_class_decision_from_facts(
    facts: ControllerActionLoopParityFacts,
    gaps: list[ControllerActionLoopParityGap],
) -> SourceClassRecoveryDecision | None:
    if facts.source_class_snapshot is None:
        return facts.source_class_decision

    recomputed = decide_source_class_recovery(facts.source_class_snapshot)
    if (
        facts.source_class_decision is not None
        and facts.source_class_decision.to_dict() != recomputed.to_dict()
    ):
        gaps.append(
            _mismatch_gap(
                action_name=RECOVER_MISSING_SOURCE_CLASS,
                supplied=facts.source_class_decision,
                recomputed=recomputed,
            )
        )
    return facts.source_class_decision or recomputed


def _retrieval_stop_decision_from_facts(
    facts: ControllerActionLoopParityFacts,
    gaps: list[ControllerActionLoopParityGap],
) -> RetrievalStopDecision | None:
    if facts.retrieval_stop_snapshot is None:
        return facts.retrieval_stop_decision

    recomputed = decide_retrieval_stop(facts.retrieval_stop_snapshot)
    if (
        facts.retrieval_stop_decision is not None
        and facts.retrieval_stop_decision.to_dict() != recomputed.to_dict()
    ):
        gaps.append(
            _mismatch_gap(
                action_name="retrieval_stop",
                supplied=facts.retrieval_stop_decision,
                recomputed=recomputed,
            )
        )
    return facts.retrieval_stop_decision or recomputed


def _source_class_gap_or_none(
    decision: SourceClassRecoveryDecision,
) -> ControllerActionLoopParityGap | None:
    classes = {str(item).casefold() for item in decision.missing_expected_source_classes}
    reason = str(decision.reason or "")
    if not (classes & set(OFFICIAL_OR_LEGAL_SOURCE_CLASSES) or reason.startswith("answer_contract_")):
        return None
    return ControllerActionLoopParityGap(
        code=OFFICIAL_LEGAL_RECOVERY_LIMITATION_GAP,
        reason=(
            "Official/legal source recovery is represented as a limited "
            "source-class action; AG-22 did not prove final official/current-primary "
            "source quality from allowed artifacts."
        ),
        action_name=RECOVER_MISSING_SOURCE_CLASS,
        metadata={
            "missing_expected_source_classes": decision.missing_expected_source_classes,
            "decision": decision.decision.value,
            "ag22_limitation": True,
        },
    )


def _retrieval_stop_gap_or_none(
    decision: RetrievalStopDecision,
    authority: ControllerActionAuthority,
) -> ControllerActionLoopParityGap | None:
    if authority is not ControllerActionAuthority.ACTIVE:
        return None
    if decision.decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL:
        return ControllerActionLoopParityGap(
            code=ACTIVE_RETRIEVAL_STOP_CONTINUE_GAP,
            reason=(
                "Current runtime does not let retrieval-stop active authority "
                "dispatch continuation; continuation remains orchestrator-owned."
            ),
            action_name=RETRIEVE_TARGETED,
            metadata={"decision": decision.decision.value},
        )
    if decision.decision is RetrievalStopControllerDecision.PROCEED_TO_SYNTHESIS:
        return ControllerActionLoopParityGap(
            code=ACTIVE_STOP_SUFFICIENT_GAP,
            reason=(
                "Current runtime treats sufficient-evidence retrieval-stop as "
                "shadow/passive; synthesis remains a legacy runtime branch."
            ),
            action_name=STOP_SUFFICIENT,
            metadata={"decision": decision.decision.value},
        )
    return None


def replay_offline_controller_action_loop(
    facts: ControllerActionLoopParityFacts,
) -> ControllerActionLoopParityResult:
    """Replay current controller-shaped decisions through AG-25 envelopes."""
    envelopes: list[ControllerActionEnvelope] = []
    gaps: list[ControllerActionLoopParityGap] = []
    answer_contract_fulfillment: Mapping[str, Any] | None = None

    weak_corpus_decision = _weak_corpus_decision_from_facts(facts, gaps)
    if weak_corpus_decision is not None:
        _append_envelope(
            envelopes,
            gaps,
            envelope_from_weak_corpus_recovery_decision(
                weak_corpus_decision,
                snapshot=facts.weak_corpus_snapshot,
            ),
        )

    source_class_decision = _source_class_decision_from_facts(facts, gaps)
    if source_class_decision is not None:
        source_gap = _source_class_gap_or_none(source_class_decision)
        if source_gap is not None:
            gaps.append(source_gap)
        _append_envelope(
            envelopes,
            gaps,
            envelope_from_source_class_recovery_decision(source_class_decision),
        )

    retrieval_stop_decision = _retrieval_stop_decision_from_facts(facts, gaps)
    if retrieval_stop_decision is not None:
        retrieval_gap = _retrieval_stop_gap_or_none(
            retrieval_stop_decision,
            facts.retrieval_stop_authority,
        )
        if retrieval_gap is not None:
            gaps.append(retrieval_gap)
        _append_envelope(
            envelopes,
            gaps,
            envelope_from_retrieval_stop_decision(
                retrieval_stop_decision,
                authority=facts.retrieval_stop_authority,
                stage=facts.retrieval_stop_stage,
                mode=facts.retrieval_stop_mode,
            ),
        )

    answer_contract_actions: list[AnswerControllerActionResult] = []
    if facts.answer_contract_pipeline_facts is not None:
        adapter_result = adapt_pipeline_facts_to_answer_contract_controller(
            facts.answer_contract_pipeline_facts
        )
        answer_contract_actions.extend(adapter_result.state.action_history)
        answer_contract_fulfillment = adapter_result.fulfillment_handoff.to_dict()
    answer_contract_actions.extend(facts.answer_contract_action_history)
    for action in answer_contract_actions:
        _append_envelope(
            envelopes,
            gaps,
            envelope_from_answer_contract_action_result(action),
        )

    if facts.include_social_signal_placeholder:
        gaps.append(
            ControllerActionLoopParityGap(
                code=SOCIAL_SIGNAL_SIDE_PACKET_ONLY_GAP,
                reason=(
                    "Social signal remains a future Author-safe side-packet "
                    "placeholder with no runtime provider wiring."
                ),
                action_name=REQUEST_SOCIAL_SIGNAL_CHECK,
                metadata={"ordinary_evidence_eligible": False},
            )
        )
        _append_envelope(
            envelopes,
            gaps,
            social_signal_placeholder_envelope(
                reason=facts.social_signal_reason
                or "Social signal check remains future side-packet only.",
            ),
        )

    metadata = {
        "offline_only": True,
        "runtime_behavior_changed": False,
        "live_side_effects": False,
        "uses_ag25_action_envelope": True,
        **dict(facts.metadata),
    }
    return ControllerActionLoopParityResult(
        envelopes=tuple(envelopes),
        gaps=tuple(gaps),
        answer_contract_fulfillment=answer_contract_fulfillment,
        metadata=metadata,
    )


def run_offline_controller_action_loop_parity(
    facts: ControllerActionLoopParityFacts,
) -> ControllerActionLoopParityResult:
    """Compatibility alias for the AG-26 parity replay entrypoint."""
    return replay_offline_controller_action_loop(facts)


__all__ = [
    "ACTIVE_RETRIEVAL_STOP_CONTINUE_GAP",
    "ACTIVE_STOP_SUFFICIENT_GAP",
    "CONTROLLER_ACTION_LOOP_PARITY_SCHEMA_VERSION",
    "OFFICIAL_LEGAL_RECOVERY_LIMITATION_GAP",
    "SNAPSHOT_DECISION_MISMATCH_GAP",
    "SOCIAL_SIGNAL_SIDE_PACKET_ONLY_GAP",
    "UNKNOWN_ENVELOPE_ACTION_GAP",
    "ControllerActionLoopParityFacts",
    "ControllerActionLoopParityGap",
    "ControllerActionLoopParityResult",
    "ControllerActionLoopParityStatus",
    "replay_offline_controller_action_loop",
    "run_offline_controller_action_loop_parity",
]
