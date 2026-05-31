"""Controller-owned weak/off-topic/failure-card gate contract.

This module is deliberately passive: it receives already-computed gate facts,
normalizes them into Controller-owned state, and exposes a mechanical handoff for
legacy orchestrator consumers. It does not retrieve, call models, build prompts,
select citations, persist sessions, or change final-answer behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

WEAK_FAILURE_GATE_SCHEMA_VERSION = "AG76D-WG.v1"
WEAK_FAILURE_GATE_TRACE_KEY = "weak_failure_gate_contract"


def _string_list(values: Sequence[Any] | None) -> list[str]:
    return [str(v) for v in (values or [])]


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


@dataclass(frozen=True)
class AnalystGateDescriptor:
    """Controller-owned copy of already-computed Analyst admission posture."""

    analyst_skipped: bool
    analyst_skip_reason: str | None
    post_retrieval_fast_path_used: bool
    pre_analyst_gate_signals: tuple[str, ...] = field(default_factory=tuple)
    analyst_skipped_after_economist: bool = False
    analyst_after_economist_skip_reason: str | None = None
    economist_output_used_as_analysis: bool = False
    controller_owned: bool = True
    legacy_runtime_branch: str = "pre_analyst_retrieval_gate"

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "analyst_skipped": bool(self.analyst_skipped),
            "analyst_skip_reason": self.analyst_skip_reason,
            "post_retrieval_fast_path_used": bool(self.post_retrieval_fast_path_used),
            "pre_analyst_gate_signals": list(self.pre_analyst_gate_signals),
            "analyst_skipped_after_economist": bool(self.analyst_skipped_after_economist),
            "analyst_after_economist_skip_reason": self.analyst_after_economist_skip_reason,
            "economist_output_used_as_analysis": bool(self.economist_output_used_as_analysis),
            "legacy_runtime_branch": self.legacy_runtime_branch,
            "mechanical_handoff_only": True,
        }


@dataclass(frozen=True)
class FailureCardGateDescriptor:
    """Controller-owned copy of already-computed failure-card posture."""

    should_show: bool
    reason: str
    payload: dict[str, Any]
    controller_owned: bool = True
    legacy_runtime_branch: str = "failure_card_payload"

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "should_show": bool(self.should_show),
            "reason": self.reason,
            "payload": deepcopy(self.payload),
            "payload_summary": {
                "keys": sorted(str(k) for k in self.payload),
                "corpus_state": self.payload.get("corpus_state"),
                "empty_entity": bool(self.payload.get("empty_entity")),
                "retrieval_retry_used": bool(self.payload.get("retrieval_retry_used")),
                "useful_content": bool(self.payload.get("useful_content")),
            },
            "legacy_runtime_branch": self.legacy_runtime_branch,
            "mechanical_handoff_only": True,
        }


@dataclass(frozen=True)
class WeakFailureGateState:
    """Controller-owned weak/off-topic/failure-card gate state."""

    corpus_state: str
    corpus_weak: bool
    corpus_state_forced: bool
    weak_corpus_recovery_considered: bool
    weak_corpus_recovery_used: bool
    weak_corpus_recovery_skip_reason: str | None
    weak_corpus_recovery_queries: tuple[str, ...]
    weak_corpus_recovery_decision: str
    weak_corpus_recovery_reason: str
    weak_corpus_recovery_blockers: tuple[str, ...]
    useful_content: bool
    useful_content_reason: str
    response_displayable: bool
    evidence_sufficient: bool
    answer_class: str
    failure_card: FailureCardGateDescriptor
    analyst_gate: AnalystGateDescriptor
    run_id: str | None = None
    iteration: int | None = None
    retrieval_loop_ref: dict[str, Any] = field(default_factory=dict)
    router_query_preparation_ref: dict[str, Any] = field(default_factory=dict)
    retrieval_stop_decision_ref: dict[str, Any] = field(default_factory=dict)
    answer_outcome_ref: dict[str, Any] = field(default_factory=dict)
    source_obligation_ref: dict[str, Any] = field(default_factory=dict)
    schema_version: str = WEAK_FAILURE_GATE_SCHEMA_VERSION
    controller_owned: bool = True

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            WEAK_FAILURE_GATE_TRACE_KEY: {
                "schema_version": self.schema_version,
                "controller_owned": bool(self.controller_owned),
                "run_id": self.run_id,
                "iteration": self.iteration,
                "corpus_state": self.corpus_state,
                "corpus_weak": bool(self.corpus_weak),
                "corpus_state_forced": bool(self.corpus_state_forced),
                "weak_corpus_recovery_considered": bool(self.weak_corpus_recovery_considered),
                "weak_corpus_recovery_used": bool(self.weak_corpus_recovery_used),
                "weak_corpus_recovery_skip_reason": self.weak_corpus_recovery_skip_reason,
                "weak_corpus_recovery_queries": list(self.weak_corpus_recovery_queries),
                "weak_corpus_recovery_decision": self.weak_corpus_recovery_decision,
                "weak_corpus_recovery_reason": self.weak_corpus_recovery_reason,
                "weak_corpus_recovery_blockers": list(self.weak_corpus_recovery_blockers),
                "off_topic": self.corpus_state == "OFF_TOPIC",
                "no_good_evidence": not bool(self.evidence_sufficient),
                "failure_card": self.failure_card.to_trace(),
                "useful_content": bool(self.useful_content),
                "useful_content_reason": self.useful_content_reason,
                "response_displayable": bool(self.response_displayable),
                "evidence_sufficient": bool(self.evidence_sufficient),
                "answer_class": self.answer_class,
                "analyst_gate": self.analyst_gate.to_trace(),
                "retrieval_loop_ref": deepcopy(self.retrieval_loop_ref),
                "router_query_preparation_ref": deepcopy(self.router_query_preparation_ref),
                "retrieval_stop_decision_ref": deepcopy(self.retrieval_stop_decision_ref),
                "answer_outcome_ref": deepcopy(self.answer_outcome_ref),
                "source_obligation_ref": deepcopy(self.source_obligation_ref),
                "controller_answer_contract_relationship": (
                    "Weak/off-topic/failure-card gate facts are Controller-owned; "
                    "AnswerContract/Author consume unchanged legacy facts."
                ),
                "trace_visibility": {
                    "additive_only": True,
                    "legacy_trace_fields_preserved": True,
                    "owned_by": "Controller",
                },
                "did_change_analyst_behavior": False,
                "did_change_author_behavior": False,
                "did_change_citation_behavior": False,
                "did_change_final_answer_behavior": False,
                "did_change_prompt_behavior": False,
                "did_call_provider_or_search": False,
                "did_change_db_or_run_outcome_shape": False,
                "mechanical_executor_boundary": True,
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.to_trace_fragment()[WEAK_FAILURE_GATE_TRACE_KEY])


@dataclass(frozen=True)
class WeakFailureGateExecutionEnvelope:
    """Mechanical handoff that exposes legacy gate outputs without deciding them."""

    failure_card_payload: dict[str, Any]
    useful_content: bool
    useful_content_reason: str
    response_displayable: bool
    evidence_sufficient: bool
    answer_class: str
    analyst_skipped: bool
    analyst_skip_reason: str | None
    post_retrieval_fast_path_used: bool
    pre_analyst_gate_signals: tuple[str, ...]
    controller_owned: bool = True
    mechanical_handoff_only: bool = True


def build_analyst_gate_descriptor(
    *,
    pre_analyst_gate: Mapping[str, Any],
    post_economist_gate: Mapping[str, Any] | None = None,
) -> AnalystGateDescriptor:
    post = post_economist_gate or {}
    return AnalystGateDescriptor(
        analyst_skipped=bool(pre_analyst_gate.get("analyst_skipped")),
        analyst_skip_reason=pre_analyst_gate.get("analyst_skip_reason"),
        post_retrieval_fast_path_used=bool(
            pre_analyst_gate.get("post_retrieval_fast_path_used")
        ),
        pre_analyst_gate_signals=tuple(
            _string_list(pre_analyst_gate.get("pre_analyst_gate_signals"))
        ),
        analyst_skipped_after_economist=bool(
            post.get("analyst_skipped_after_economist", False)
        ),
        analyst_after_economist_skip_reason=post.get(
            "analyst_after_economist_skip_reason"
        ),
        economist_output_used_as_analysis=bool(
            post.get("economist_output_used_as_analysis", False)
        ),
    )


def build_failure_card_gate_descriptor(
    *, failure_card_payload: Mapping[str, Any]
) -> FailureCardGateDescriptor:
    payload = _mapping(failure_card_payload)
    return FailureCardGateDescriptor(
        should_show=bool(payload.get("show")),
        reason=str(payload.get("reason") or ""),
        payload=payload,
    )


def build_weak_failure_gate_state(
    *,
    corpus_state: str,
    corpus_weak: bool,
    corpus_state_forced: bool,
    weak_corpus_recovery_considered: bool,
    weak_corpus_recovery_used: bool,
    weak_corpus_recovery_skip_reason: str | None,
    weak_corpus_recovery_queries: Sequence[Any] | None,
    weak_corpus_recovery_decision: str,
    weak_corpus_recovery_reason: str,
    weak_corpus_recovery_blockers: Sequence[Any] | None,
    useful_content: bool,
    useful_content_reason: str,
    response_displayable: bool,
    evidence_sufficient: bool,
    answer_class: str,
    failure_card_payload: Mapping[str, Any],
    analyst_gate: AnalystGateDescriptor,
    run_id: str | None = None,
    iteration: int | None = None,
    retrieval_loop_state: Any | None = None,
    router_query_preparation_state: Any | None = None,
    retrieval_stop_decision: Any | None = None,
    answer_outcome_ref: Mapping[str, Any] | None = None,
    source_obligation_ref: Mapping[str, Any] | None = None,
) -> WeakFailureGateState:
    retrieval_loop_ref = {}
    if retrieval_loop_state is not None and hasattr(retrieval_loop_state, "to_controller_state"):
        retrieval_loop_ref = retrieval_loop_state.to_controller_state()
    router_ref = {}
    if router_query_preparation_state is not None and hasattr(
        router_query_preparation_state, "to_controller_state"
    ):
        router_ref = router_query_preparation_state.to_controller_state()
    stop_ref = {}
    if retrieval_stop_decision is not None:
        if hasattr(retrieval_stop_decision, "to_trace"):
            stop_ref = retrieval_stop_decision.to_trace()
        elif isinstance(retrieval_stop_decision, Mapping):
            stop_ref = _mapping(retrieval_stop_decision)
    return WeakFailureGateState(
        corpus_state=str(corpus_state),
        corpus_weak=bool(corpus_weak),
        corpus_state_forced=bool(corpus_state_forced),
        weak_corpus_recovery_considered=bool(weak_corpus_recovery_considered),
        weak_corpus_recovery_used=bool(weak_corpus_recovery_used),
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        weak_corpus_recovery_queries=tuple(_string_list(weak_corpus_recovery_queries)),
        weak_corpus_recovery_decision=str(weak_corpus_recovery_decision),
        weak_corpus_recovery_reason=str(weak_corpus_recovery_reason),
        weak_corpus_recovery_blockers=tuple(_string_list(weak_corpus_recovery_blockers)),
        useful_content=bool(useful_content),
        useful_content_reason=str(useful_content_reason),
        response_displayable=bool(response_displayable),
        evidence_sufficient=bool(evidence_sufficient),
        answer_class=str(answer_class),
        failure_card=build_failure_card_gate_descriptor(
            failure_card_payload=failure_card_payload
        ),
        analyst_gate=analyst_gate,
        run_id=run_id,
        iteration=iteration,
        retrieval_loop_ref=retrieval_loop_ref,
        router_query_preparation_ref=router_ref,
        retrieval_stop_decision_ref=stop_ref,
        answer_outcome_ref=_mapping(answer_outcome_ref),
        source_obligation_ref=_mapping(source_obligation_ref),
    )


def execute_weak_failure_gate_handoff(
    state: WeakFailureGateState,
) -> WeakFailureGateExecutionEnvelope:
    """Return legacy gate outputs from Controller-owned state without policy logic."""

    return WeakFailureGateExecutionEnvelope(
        failure_card_payload=deepcopy(state.failure_card.payload),
        useful_content=bool(state.useful_content),
        useful_content_reason=state.useful_content_reason,
        response_displayable=bool(state.response_displayable),
        evidence_sufficient=bool(state.evidence_sufficient),
        answer_class=state.answer_class,
        analyst_skipped=bool(state.analyst_gate.analyst_skipped),
        analyst_skip_reason=state.analyst_gate.analyst_skip_reason,
        post_retrieval_fast_path_used=bool(
            state.analyst_gate.post_retrieval_fast_path_used
        ),
        pre_analyst_gate_signals=tuple(state.analyst_gate.pre_analyst_gate_signals),
    )
