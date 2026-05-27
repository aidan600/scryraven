"""Passive run controller data shapes.

This module intentionally contains only records and serialization helpers. It
does not call providers, build prompts, choose routing, or alter retrieval.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any]) -> list[Any]:
    return deepcopy(list(value))


@dataclass
class RetrievalAction:
    """Passive record of an existing or recommended retrieval-related action."""

    name: str
    queries: list[str] = field(default_factory=list)
    provider: str | None = None
    provider_role: str | None = None
    search_depth: str | None = None
    results_per_query: int | None = None
    active: bool = False
    shadow: bool = True
    reason: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        return _copy_mapping(self.trace_fields)


@dataclass
class ControllerDecision:
    """Passive diagnostic record of a decision computed elsewhere."""

    name: str
    active: bool = False
    shadow: bool = True
    reason: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    recommended_actions: list[RetrievalAction | dict[str, Any] | str] = field(
        default_factory=list
    )
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        return _copy_mapping(self.trace_fields)


@dataclass
class CorpusAssessment:
    """Snapshot of already-computed corpus quality signals."""

    state: str | None = None
    weak: bool | None = None
    reason: str | None = None
    utilization_rate: float | None = None
    utilization_threshold: float | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        return _copy_mapping(self.trace_fields)


@dataclass
class ControllerState:
    """Durable passive state for one pipeline invocation."""

    session_id: str | None = None
    run_id: str | None = None
    query: str | None = None
    mode: str | None = None
    current_date: str | None = None
    core_topic: str | None = None
    intent: str | None = None
    complexity: str | None = None
    corpus: CorpusAssessment = field(default_factory=CorpusAssessment)
    route_fields: dict[str, Any] = field(default_factory=dict)
    provider_call_records: list[dict[str, Any]] = field(default_factory=list)
    recovery_action_records: list[RetrievalAction] = field(default_factory=list)
    analyst_skip_record: ControllerDecision | None = None
    active_source_class_recovery_considered: bool = False
    active_source_class_recovery_eligible: bool = False
    active_source_class_recovery_used: bool = False
    active_source_class_recovery_execution_attempted: bool = False
    active_source_class_recovery_reason: str | None = None
    active_source_class_recovery_skip_reason: str | None = None
    active_source_class_recovery_blockers: list[str] = field(default_factory=list)
    active_source_class_recovery_missing_classes: list[str] = field(default_factory=list)
    active_source_class_recovery_queries: list[str] = field(default_factory=list)
    active_source_class_recovery_result_count: int = 0
    active_source_class_recovery_new_url_count: int = 0
    active_source_class_recovery_provider_role: str | None = None
    active_source_class_recovery_search_depth: str | None = None
    active_source_class_recovery_attempt_count: int = 0
    answer_contract: dict[str, Any] | None = None
    answer_contract_evidence_state_summary: dict[str, Any] = field(default_factory=dict)
    answer_contract_missing_information: list[str] = field(default_factory=list)
    answer_contract_action_history: list[dict[str, Any]] = field(default_factory=list)
    answer_contract_recovery_attempts: dict[str, int] = field(default_factory=dict)
    answer_contract_stop_state: dict[str, Any] | None = None
    answer_contract_revisions: list[dict[str, Any]] = field(default_factory=list)
    answer_contract_fulfillment_handoff: dict[str, Any] | None = None
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_provider_call_record(self, record: Mapping[str, Any]) -> None:
        self.provider_call_records.append(_copy_mapping(record))

    def record_recovery_action(self, action: RetrievalAction) -> None:
        self.recovery_action_records.append(deepcopy(action))

    def record_analyst_skip(self, decision: ControllerDecision) -> None:
        self.analyst_skip_record = deepcopy(decision)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        fragment = _copy_mapping(self.trace_fields)
        fragment.update(self.corpus.to_trace_fragment())
        if self.analyst_skip_record is not None:
            fragment.update(self.analyst_skip_record.to_trace_fragment())
        for action in self.recovery_action_records:
            fragment.update(action.to_trace_fragment())
        return fragment


@dataclass
class EvidenceRegistry:
    """Passive snapshots of evidence already collected by the pipeline."""

    passages: list[dict[str, Any]] = field(default_factory=list)
    seen_urls: list[str] = field(default_factory=list)
    collected_images: list[str] = field(default_factory=list)
    source_ids: list[Any] = field(default_factory=list)
    source_tier_snapshots: list[dict[str, Any]] = field(default_factory=list)
    domain_snapshots: list[dict[str, Any]] = field(default_factory=list)
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_passage(self, passage: Mapping[str, Any]) -> None:
        self.passages.append(_copy_mapping(passage))

    def record_passages(self, passages: Sequence[Mapping[str, Any]]) -> None:
        for passage in passages:
            self.record_passage(passage)

    def record_seen_url(self, url: str) -> None:
        self.seen_urls.append(deepcopy(url))

    def record_seen_urls(self, urls: Sequence[str]) -> None:
        for url in urls:
            self.record_seen_url(url)

    def record_collected_image(self, image_url: str) -> None:
        self.collected_images.append(deepcopy(image_url))

    def record_collected_images(self, image_urls: Sequence[str]) -> None:
        for image_url in image_urls:
            self.record_collected_image(image_url)

    def record_source_id(self, source_id: Any) -> None:
        self.source_ids.append(deepcopy(source_id))

    def record_source_ids(self, source_ids: Sequence[Any]) -> None:
        for source_id in source_ids:
            self.record_source_id(source_id)

    def record_source_tier_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        self.source_tier_snapshots.append(_copy_mapping(snapshot))

    def record_domain_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        self.domain_snapshots.append(_copy_mapping(snapshot))

    def snapshot_passages(self) -> list[dict[str, Any]]:
        return _copy_sequence(self.passages)

    def snapshot_seen_urls(self) -> list[str]:
        return _copy_sequence(self.seen_urls)

    def snapshot_collected_images(self) -> list[str]:
        return _copy_sequence(self.collected_images)

    def snapshot_source_ids(self) -> list[Any]:
        return _copy_sequence(self.source_ids)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        return _copy_mapping(self.trace_fields)


@dataclass
class StageLedger:
    """Append-only passive ledger for already-computed stage facts."""

    retrieval_actions: list[RetrievalAction] = field(default_factory=list)
    query_records: list[dict[str, Any]] = field(default_factory=list)
    provider_records: list[dict[str, Any]] = field(default_factory=list)
    decision_records: list[ControllerDecision] = field(default_factory=list)
    fact_records: list[dict[str, Any]] = field(default_factory=list)
    trace_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_retrieval_action(self, action: RetrievalAction) -> None:
        self.retrieval_actions.append(deepcopy(action))

    def record_query(
        self,
        *,
        stage: str,
        query: str,
        iteration: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.query_records.append(
            {
                "stage": stage,
                "query": query,
                "iteration": iteration,
                "metadata": _copy_mapping(metadata),
            }
        )

    def record_provider_fact(
        self,
        *,
        stage: str,
        provider: str,
        provider_role: str | None = None,
        success: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.provider_records.append(
            {
                "stage": stage,
                "provider": provider,
                "provider_role": provider_role,
                "success": success,
                "metadata": _copy_mapping(metadata),
            }
        )

    def record_decision(self, decision: ControllerDecision) -> None:
        self.decision_records.append(deepcopy(decision))

    def record_fact(
        self,
        *,
        stage: str,
        name: str,
        value: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self.fact_records.append(
            {
                "stage": stage,
                "name": name,
                "value": deepcopy(value),
                "metadata": _copy_mapping(metadata),
            }
        )

    def snapshot_retrieval_actions(self) -> list[dict[str, Any]]:
        return [action.to_dict() for action in self.retrieval_actions]

    def snapshot_decisions(self) -> list[dict[str, Any]]:
        return [decision.to_dict() for decision in self.decision_records]

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        fragment = _copy_mapping(self.trace_fields)
        for action in self.retrieval_actions:
            fragment.update(action.to_trace_fragment())
        for decision in self.decision_records:
            fragment.update(decision.to_trace_fragment())
        return fragment


@dataclass
class RunController:
    """Lightweight passive container over state, evidence, and stage ledger."""

    state: ControllerState = field(default_factory=ControllerState)
    evidence: EvidenceRegistry = field(default_factory=EvidenceRegistry)
    ledger: StageLedger = field(default_factory=StageLedger)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_retrieval_action(self, action: RetrievalAction) -> None:
        self.ledger.record_retrieval_action(action)

    def record_decision(self, decision: ControllerDecision) -> None:
        self.ledger.record_decision(decision)

    def snapshot_state(self) -> dict[str, Any]:
        return self.state.to_dict()

    def snapshot_evidence(self) -> dict[str, Any]:
        return self.evidence.to_dict()

    def snapshot_ledger(self) -> dict[str, Any]:
        return self.ledger.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def to_trace_fragment(self) -> dict[str, Any]:
        fragment = self.state.to_trace_fragment()
        fragment.update(self.evidence.to_trace_fragment())
        fragment.update(self.ledger.to_trace_fragment())
        return fragment


__all__ = [
    "ControllerDecision",
    "ControllerState",
    "CorpusAssessment",
    "EvidenceRegistry",
    "RetrievalAction",
    "RunController",
    "StageLedger",
]
