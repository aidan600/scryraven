"""Runtime-shaped answer-contract handoff adapter.

This module builds the AG-4 fulfillment handoff from facts the runtime has
already computed. It does not call providers, models, prompts, retrieval,
storage, routing, Streamlit, or orchestration code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any

from core.answer_contract_controller import (
    AnswerContractFulfillment,
    AnswerControllerCaps,
    AnswerControllerState,
    attach_answer_controller_state,
)
from core.answer_contract_pipeline_adapter import (
    PipelineAnswerContractAdapterResult,
    PipelineAnswerContractFacts,
    PipelineControllerDecisionFacts,
    PipelineEvidenceFacts,
    PipelineEvidenceReferenceFact,
    PipelineRouterFacts,
    adapt_pipeline_facts_to_answer_contract_controller,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)
from core.run_controller import RunController
from core.source_class_recovery_controller import (
    SOURCE_CLASS_RECOVERY_PROVIDER_ROLE,
    SourceClassRecoveryControllerDecision,
    SourceClassRecoveryDecision,
)

ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY = "answer_contract_fulfillment_handoff"

_NO_ACTION_SOURCE_CLASS_REASONS = {
    "not_recommended",
    "no_missing_expected_source_class",
}
_SOURCE_CLASS_TRACE_PREFIX = "active_source_class_recovery_"
_SOURCE_CLASS_GAP_STATUSES = {
    "expected_but_only_secondary",
    "unsatisfied",
}
_SOURCE_CLASS_STATUS_ALIASES = {
    "archival_primary_text": "primary_or_archival",
    "historical_legal_text": "primary_or_archival",
    "primary_source_documents": "primary_or_archival",
}
_MAX_EVIDENCE_REFERENCES = 5
_MAX_REFERENCE_TEXT = 180


def _copy_string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _limited_text(value: Any, *, limit: int = _MAX_REFERENCE_TEXT) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _bool_from_mapping(mapping: Mapping[str, Any], key: str) -> bool:
    return bool(mapping.get(key))


def _source_class_for_tier(source_tier: Any) -> str | None:
    tier = str(source_tier or "").strip().casefold()
    if tier == "official":
        return "official_current_rules"
    if tier in {"secondary", "trusted_community"}:
        return "reputable_secondary"
    if tier == "social_or_forum":
        return "social_signal"
    return tier or None


def _source_classes_present_from_runtime(
    *,
    source_tier_counts: Mapping[str, Any],
    source_class_recovery_telemetry: Mapping[str, Any],
) -> tuple[str, ...]:
    present: list[str] = []
    if int(source_tier_counts.get("official", 0) or 0) > 0:
        present.extend(("official_current_rules", "current_primary_or_official"))
    if int(source_tier_counts.get("secondary", 0) or 0) > 0:
        present.append("reputable_secondary")
    if int(source_tier_counts.get("trusted_community", 0) or 0) > 0:
        present.append("reputable_secondary")
    if int(source_tier_counts.get("social_or_forum", 0) or 0) > 0:
        present.append("social_signal")

    missing = {
        str(item).casefold()
        for item in _copy_string_tuple(
            source_class_recovery_telemetry.get("missing_expected_source_classes")
        )
    }
    return tuple(item for item in _copy_string_tuple(present) if item.casefold() not in missing)


def _source_classes_missing_from_runtime(
    *,
    source_class_recovery_telemetry: Mapping[str, Any],
    active_source_class_recovery_lifecycle: Mapping[str, Any],
) -> tuple[str, ...]:
    lifecycle_missing = active_source_class_recovery_lifecycle.get(
        f"{_SOURCE_CLASS_TRACE_PREFIX}missing_classes"
    )
    telemetry_missing = source_class_recovery_telemetry.get(
        "missing_expected_source_classes"
    )
    return _copy_string_tuple(
        tuple(_copy_string_tuple(lifecycle_missing))
        + tuple(_copy_string_tuple(telemetry_missing))
    )


def _current_source_classes_missing_from_runtime(
    source_class_recovery_telemetry: Mapping[str, Any],
) -> tuple[str, ...]:
    status_gaps: list[str] = []
    satisfaction_status = source_class_recovery_telemetry.get(
        "source_class_satisfaction_status"
    )
    if isinstance(satisfaction_status, Mapping):
        for source_class, status in satisfaction_status.items():
            if str(status or "").casefold() not in _SOURCE_CLASS_GAP_STATUSES:
                continue
            normalized = str(source_class or "").strip()
            mapped = _SOURCE_CLASS_STATUS_ALIASES.get(
                normalized.casefold(),
                normalized,
            )
            if mapped:
                status_gaps.append(mapped)
    explicit_missing = _copy_string_tuple(
        source_class_recovery_telemetry.get("missing_expected_source_classes")
    )
    return _copy_string_tuple(tuple(explicit_missing) + tuple(status_gaps))


def _source_class_decision_name(
    *,
    eligible: bool,
    skip_reason: str | None,
) -> SourceClassRecoveryControllerDecision:
    if eligible:
        return SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    if skip_reason in _NO_ACTION_SOURCE_CLASS_REASONS:
        return SourceClassRecoveryControllerDecision.NO_ACTION
    return SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON


def source_class_recovery_decision_from_runtime_trace(
    *,
    source_class_recovery_telemetry: Mapping[str, Any] | None,
    active_source_class_recovery_lifecycle: Mapping[str, Any] | None,
) -> SourceClassRecoveryDecision | None:
    """Map existing source-class lifecycle fields into the controller decision."""
    lifecycle = _copy_mapping(active_source_class_recovery_lifecycle)
    telemetry = _copy_mapping(source_class_recovery_telemetry)
    considered = _bool_from_mapping(lifecycle, f"{_SOURCE_CLASS_TRACE_PREFIX}considered")
    if not considered:
        return None

    eligible = _bool_from_mapping(lifecycle, f"{_SOURCE_CLASS_TRACE_PREFIX}eligible")
    skip_reason = lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}skip_reason")
    reason = (
        (
            telemetry.get("source_class_recovery_reason")
            or lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}reason")
        )
        if eligible
        else None if skip_reason is None else str(skip_reason)
    )
    blockers = _copy_string_tuple(
        lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}blockers")
    )
    if not eligible and not blockers and skip_reason:
        blockers = (str(skip_reason),)

    return SourceClassRecoveryDecision(
        decision=_source_class_decision_name(
            eligible=eligible,
            skip_reason=None if skip_reason is None else str(skip_reason),
        ),
        reason=None if reason is None else str(reason),
        blockers=blockers,
        missing_expected_source_classes=_source_classes_missing_from_runtime(
            source_class_recovery_telemetry=telemetry,
            active_source_class_recovery_lifecycle=lifecycle,
        ),
        queries=_copy_string_tuple(
            lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}queries")
            or telemetry.get("source_class_recovery_queries")
        ),
        provider_role=(
            SOURCE_CLASS_RECOVERY_PROVIDER_ROLE
            if eligible
            else None
        ),
        search_depth=(
            None
            if not eligible
            else _limited_text(lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}search_depth"))
        ),
        attempt_count=max(
            0,
            int(lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}attempt_count") or 0),
        ),
    )


def _retrieval_decision_from_runtime_telemetry(
    *,
    prefix: str,
    telemetry: Mapping[str, Any],
) -> RetrievalStopDecision | None:
    if telemetry.get(f"retrieval_stop_{prefix}_available") is not True:
        return None
    raw_decision = telemetry.get(f"retrieval_stop_{prefix}_decision")
    if not raw_decision:
        return None
    try:
        decision = RetrievalStopControllerDecision(str(raw_decision))
    except ValueError:
        return None
    if decision is RetrievalStopControllerDecision.CONTINUE_RETRIEVAL:
        return None

    reason = _limited_text(telemetry.get(f"retrieval_stop_{prefix}_reason")) or decision.value
    blockers = _copy_string_tuple(telemetry.get(f"retrieval_stop_{prefix}_blockers"))
    return RetrievalStopDecision(
        decision=decision,
        reason=reason,
        blockers=blockers,
    )


def retrieval_stop_decision_from_runtime_trace(
    *,
    retrieval_stop_active_telemetry: Mapping[str, Any] | None,
    retrieval_stop_shadow_telemetry: Mapping[str, Any] | None,
) -> RetrievalStopDecision | None:
    """Return the existing runtime stop decision without recomputing retrieval policy."""
    active = _retrieval_decision_from_runtime_telemetry(
        prefix="active",
        telemetry=_copy_mapping(retrieval_stop_active_telemetry),
    )
    if active is not None:
        return active
    return _retrieval_decision_from_runtime_telemetry(
        prefix="shadow",
        telemetry=_copy_mapping(retrieval_stop_shadow_telemetry),
    )


def _flatten_queries_by_iteration(
    queries_by_iteration: Mapping[Any, Sequence[Any]] | None,
) -> tuple[str, ...]:
    queries: list[Any] = []
    for key in sorted((queries_by_iteration or {}).keys(), key=str):
        queries.extend((queries_by_iteration or {}).get(key) or ())
    return _copy_string_tuple(queries)


def _runtime_evidence_references(
    final_top_evidence: Sequence[Mapping[str, Any]] | None,
) -> tuple[PipelineEvidenceReferenceFact, ...]:
    references: list[PipelineEvidenceReferenceFact] = []
    for index, passage in enumerate(final_top_evidence or (), start=1):
        if not isinstance(passage, Mapping):
            continue
        source_id = passage.get("source_id") or index
        reference = _limited_text(f"source:{source_id}", limit=40)
        if not reference:
            continue
        title = _limited_text(passage.get("title"))
        url = _limited_text(passage.get("url"), limit=220)
        summary = "; ".join(item for item in (title, url) if item) or None
        references.append(
            PipelineEvidenceReferenceFact(
                reference=reference,
                source_class=_source_class_for_tier(passage.get("source_tier")),
                summary=summary,
            )
        )
        if len(references) >= _MAX_EVIDENCE_REFERENCES:
            break
    return tuple(references)


@dataclass(frozen=True)
class RuntimeAnswerContractFacts:
    """Runtime-shaped facts already available after retrieval/synthesis."""

    query: str
    intent: str | None = None
    report_type: str | None = None
    query_type: str | None = None
    mode: str | None = None
    current_date: str | None = None
    core_topic: str | None = None
    answer_goal: str | None = None
    evidence_available: bool = False
    evidence_sufficient: bool = False
    source_tier_counts: Mapping[str, Any] = field(default_factory=dict)
    source_class_recovery_telemetry: Mapping[str, Any] = field(default_factory=dict)
    active_source_class_recovery_lifecycle: Mapping[str, Any] = field(default_factory=dict)
    weak_corpus: bool = False
    weak_corpus_reason: str | None = None
    conflicts_present: bool = False
    conflict_notes: Sequence[Any] = ()
    resolving_queries: Sequence[Any] = ()
    next_queries: Sequence[Any] = ()
    weak_corpus_recovery_considered: bool = False
    weak_corpus_recovery_used: bool = False
    weak_corpus_recovery_skip_reason: str | None = None
    retrieval_stop_shadow_telemetry: Mapping[str, Any] = field(default_factory=dict)
    retrieval_stop_active_telemetry: Mapping[str, Any] = field(default_factory=dict)
    queries_by_iteration: Mapping[Any, Sequence[Any]] = field(default_factory=dict)
    final_top_evidence: Sequence[Mapping[str, Any]] = ()
    fulfilled_obligations: Sequence[Any] = ()
    partial_obligations: Sequence[Any] = ()
    unfulfilled_obligations: Sequence[Any] = ()
    missing_information: Sequence[Any] = ()
    warnings_to_analyst_or_author: Sequence[Any] = ()
    evidence_integration_checkpoint: Mapping[str, Any] = field(default_factory=dict)
    iteration: int = 1
    max_iterations: int = 3
    max_recovery_attempts: int = 1


@dataclass(frozen=True)
class RuntimeAnswerContractHandoffResult:
    """Runtime handoff result plus the underlying passive adapter output."""

    adapter_result: PipelineAnswerContractAdapterResult

    @property
    def state(self) -> AnswerControllerState:
        return self.adapter_result.state

    @property
    def fulfillment_handoff(self) -> AnswerContractFulfillment:
        return self.adapter_result.fulfillment_handoff

    def execution_trace_fragment(self) -> dict[str, Any]:
        return {
            ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY: (
                self.fulfillment_handoff.to_dict()
            )
        }


def _pipeline_facts_from_runtime(
    facts: RuntimeAnswerContractFacts,
) -> PipelineAnswerContractFacts:
    source_class_decision = source_class_recovery_decision_from_runtime_trace(
        source_class_recovery_telemetry=facts.source_class_recovery_telemetry,
        active_source_class_recovery_lifecycle=facts.active_source_class_recovery_lifecycle,
    )
    retrieval_stop_decision = retrieval_stop_decision_from_runtime_trace(
        retrieval_stop_active_telemetry=facts.retrieval_stop_active_telemetry,
        retrieval_stop_shadow_telemetry=facts.retrieval_stop_shadow_telemetry,
    )
    source_tier_counts = _copy_mapping(facts.source_tier_counts)
    source_class_recovery_telemetry = _copy_mapping(
        facts.source_class_recovery_telemetry
    )
    source_class_lifecycle = _copy_mapping(
        facts.active_source_class_recovery_lifecycle
    )
    source_classes_missing = _current_source_classes_missing_from_runtime(
        source_class_recovery_telemetry
    )
    weak_corpus_reason = (
        facts.weak_corpus_reason
        or facts.weak_corpus_recovery_skip_reason
        or ("weak_corpus" if facts.weak_corpus else None)
    )

    return PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query=facts.query,
            intent=facts.intent,
            report_type=facts.report_type,
            query_type=facts.query_type,
            mode=facts.mode,
            current_date=facts.current_date,
            core_topic=facts.core_topic,
            answer_goal=facts.answer_goal,
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=bool(facts.evidence_available),
            evidence_sufficient=bool(facts.evidence_sufficient),
            source_classes_present=_source_classes_present_from_runtime(
                source_tier_counts=source_tier_counts,
                source_class_recovery_telemetry=source_class_recovery_telemetry,
            ),
            source_classes_missing=source_classes_missing,
            derive_missing_source_classes=True,
            fulfilled_obligations=_copy_string_tuple(facts.fulfilled_obligations),
            partial_obligations=_copy_string_tuple(facts.partial_obligations),
            unfulfilled_obligations=_copy_string_tuple(facts.unfulfilled_obligations),
            missing_information=_copy_string_tuple(
                tuple(facts.missing_information) + tuple(source_classes_missing)
            ),
            approved_targeted_queries=_copy_string_tuple(
                source_class_lifecycle.get(f"{_SOURCE_CLASS_TRACE_PREFIX}queries")
                or source_class_recovery_telemetry.get(
                    "source_class_recovery_queries"
                )
            ),
            prior_queries=_flatten_queries_by_iteration(facts.queries_by_iteration),
            next_query_redundant=(
                (
                    facts.retrieval_stop_active_telemetry.get(
                        "retrieval_stop_active_decision"
                    )
                    == RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES.value
                )
                or (
                    facts.retrieval_stop_shadow_telemetry.get(
                        "retrieval_stop_shadow_decision"
                    )
                    == RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES.value
                )
            ),
            next_queries=_copy_string_tuple(facts.next_queries),
            weak_corpus=bool(facts.weak_corpus),
            weak_corpus_reason=weak_corpus_reason,
            conflicts_present=bool(facts.conflicts_present),
            conflict_notes=_copy_string_tuple(facts.conflict_notes),
            resolving_queries=_copy_string_tuple(facts.resolving_queries),
            evidence_references=_runtime_evidence_references(facts.final_top_evidence),
            warnings_to_analyst_or_author=_copy_string_tuple(
                facts.warnings_to_analyst_or_author
            ),
        ),
        decisions=PipelineControllerDecisionFacts(
            source_class_recovery_decisions=(
                () if source_class_decision is None else (source_class_decision,)
            ),
            retrieval_stop_decisions=(
                () if retrieval_stop_decision is None else (retrieval_stop_decision,)
            ),
        ),
        caps=AnswerControllerCaps(
            max_iterations=max(1, int(facts.max_iterations or 1)),
            max_recovery_attempts=max(0, int(facts.max_recovery_attempts or 0)),
        ),
        iteration=max(1, int(facts.iteration or 1)),
    )


def _checkpoint_reference_from_runtime(
    checkpoint: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a compact AG-32 checkpoint handoff reference when supplied."""

    payload = _copy_mapping(checkpoint)
    if not payload:
        return None
    if payload.get("schema_version") == "evidence_integration_checkpoint_handoff_ag32_v1":
        return {
            "schema_version": "evidence_integration_checkpoint_handoff_ag32_v1",
            "action_name": _limited_text(payload.get("action_name"), limit=80),
            "reason": _limited_text(payload.get("reason")),
            "contract_gap_addressed": _limited_text(
                payload.get("contract_gap_addressed")
            ),
            "expected_value": _limited_text(payload.get("expected_value"), limit=40),
            "budget_rationale": _limited_text(payload.get("budget_rationale")),
            "side_packet_placeholder_only": bool(
                payload.get("side_packet_placeholder_only")
            ),
            "ordinary_evidence_allowed": bool(
                payload.get("ordinary_evidence_allowed", True)
            ),
            "shadow_mode": True,
            "runtime_behavior_changed": False,
            "consumer": "answer_contract_fulfillment_handoff",
            "promotion_criteria": _limited_text(payload.get("promotion_criteria")),
            "deletion_criteria": _limited_text(payload.get("deletion_criteria")),
        }

    decision = payload.get("decision")
    if isinstance(decision, Mapping):
        return _checkpoint_reference_from_runtime(decision)
    return None


def build_runtime_answer_contract_handoff(
    facts: RuntimeAnswerContractFacts,
    *,
    controller: RunController | None = None,
) -> RuntimeAnswerContractHandoffResult:
    """Build and optionally attach a compact runtime fulfillment handoff."""
    adapter_result = adapt_pipeline_facts_to_answer_contract_controller(
        _pipeline_facts_from_runtime(facts)
    )
    checkpoint_reference = _checkpoint_reference_from_runtime(
        facts.evidence_integration_checkpoint
    )
    if checkpoint_reference is not None:
        fulfillment = replace(
            adapter_result.fulfillment_handoff,
            evidence_integration_checkpoint=checkpoint_reference,
        )
        adapter_result.state.fulfillment_handoff_draft = fulfillment
        adapter_result = replace(adapter_result, fulfillment_handoff=fulfillment)
    if controller is not None:
        attach_answer_controller_state(
            controller,
            adapter_result.state,
            fulfillment=adapter_result.fulfillment_handoff,
        )
    return RuntimeAnswerContractHandoffResult(adapter_result=adapter_result)


__all__ = [
    "ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY",
    "RuntimeAnswerContractFacts",
    "RuntimeAnswerContractHandoffResult",
    "build_runtime_answer_contract_handoff",
    "retrieval_stop_decision_from_runtime_trace",
    "source_class_recovery_decision_from_runtime_trace",
]
