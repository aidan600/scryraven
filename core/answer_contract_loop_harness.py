"""Offline answer-contract controller loop harness.

The AG-3 harness runs the AG-1 controller against fixture-provided outcomes.
It is deliberately bounded and deterministic: no live providers, models,
prompts, retrieval, storage, caches, generated outputs, or orchestration.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from typing import Any, Sequence

from core.answer_contract_controller import (
    AnswerContractFulfillment,
    AnswerControllerActionName,
    AnswerControllerActionResult,
    AnswerControllerState,
    AnswerControllerStopDecision,
    AnswerControllerStopReason,
    EvidenceReference,
    EvidenceStateSummary,
    MarginalValueJudgment,
    apply_answer_controller_action_result,
    build_answer_contract_fulfillment,
    decide_answer_controller_action,
    decide_answer_controller_stop,
)
from core.answer_contract_pipeline_adapter import (
    PipelineAnswerContractFacts,
    adapt_pipeline_facts_to_answer_contract_controller,
)

ActionExecutor = Callable[
    [AnswerControllerState, AnswerControllerActionResult],
    "SimulatedActionOutcome",
]

_STOP_ACTIONS = {
    AnswerControllerActionName.STOP_SUFFICIENT,
    AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
}
_EVIDENCE_FIELD_NAMES = {item.name for item in fields(EvidenceStateSummary)}


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


@dataclass(frozen=True)
class SimulatedActionOutcome:
    """Fixture-provided result for one offline controller action."""

    evidence_state_delta: Mapping[str, Any] = field(default_factory=dict)
    evidence_used: tuple[EvidenceReference, ...] = ()
    warnings_to_analyst_or_author: tuple[str, ...] = ()
    stable_reason_code: str = "simulated_action_applied"
    no_op_reason: str | None = None
    stop_loop: bool = False


class FixtureDrivenActionExecutor:
    """Deterministic action executor backed by per-action outcome queues."""

    def __init__(
        self,
        outcomes_by_action: Mapping[AnswerControllerActionName | str, Sequence[SimulatedActionOutcome]] | None = None,
    ) -> None:
        self._outcomes_by_action: dict[str, list[SimulatedActionOutcome]] = {
            (key.value if isinstance(key, AnswerControllerActionName) else str(key)): list(value)
            for key, value in (outcomes_by_action or {}).items()
        }

    def __call__(
        self,
        state: AnswerControllerState,
        action: AnswerControllerActionResult,
    ) -> SimulatedActionOutcome:
        del state
        key = action.action_name.value
        outcomes = self._outcomes_by_action.get(key) or []
        if outcomes:
            return outcomes.pop(0)
        reason = f"no_simulated_outcome_for_{key}"
        return SimulatedActionOutcome(
            stable_reason_code=reason,
            no_op_reason=reason,
            stop_loop=True,
        )


@dataclass(frozen=True)
class AnswerControllerLoopResult:
    """Final offline loop state plus compact fulfillment handoff."""

    final_state: AnswerControllerState
    fulfillment_handoff: AnswerContractFulfillment
    evidence_used: tuple[EvidenceReference, ...]
    simulated_outcomes: tuple[SimulatedActionOutcome, ...]

    @property
    def action_history(self) -> tuple[AnswerControllerActionResult, ...]:
        return tuple(self.final_state.action_history)

    @property
    def stopped_by(self) -> str | None:
        return self.fulfillment_handoff.stop_reason


def _normalize_evidence_delta_value(current_value: Any, new_value: Any) -> Any:
    if isinstance(current_value, tuple):
        return _copy_string_tuple(new_value)
    if isinstance(current_value, bool):
        return bool(new_value)
    if new_value is None:
        return None
    return str(new_value) if isinstance(current_value, str | type(None)) else deepcopy(new_value)


def _apply_evidence_state_delta(
    state: AnswerControllerState,
    delta: Mapping[str, Any],
) -> AnswerControllerState:
    evidence_updates: dict[str, Any] = {}
    for key, value in delta.items():
        if key not in _EVIDENCE_FIELD_NAMES:
            continue
        current_value = getattr(state.evidence_state_summary, key)
        evidence_updates[key] = _normalize_evidence_delta_value(current_value, value)

    if evidence_updates:
        state.evidence_state_summary = replace(state.evidence_state_summary, **evidence_updates)

    if "missing_information" in evidence_updates:
        state.missing_information = list(
            _copy_string_tuple(
                tuple(state.missing_information) + tuple(evidence_updates["missing_information"])
            )
        )
    return state


def _build_stop_action_from_decision(
    stop_decision: AnswerControllerStopDecision,
    *,
    iteration: int,
) -> AnswerControllerActionResult:
    action_name = (
        AnswerControllerActionName.STOP_SUFFICIENT
        if stop_decision.reason is AnswerControllerStopReason.EVIDENCE_SUFFICIENT
        else AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    )
    return AnswerControllerActionResult(
        action_name=action_name,
        reason=stop_decision.public_rationale,
        preconditions=stop_decision.structured_checks,
        stable_reason_code=stop_decision.reason.value,
        iteration=iteration,
        next_state_delta={
            "stop_state": {
                "reason": stop_decision.reason.value,
                "final_answer_posture": stop_decision.final_answer_posture,
            }
        },
    )


def _mark_offline_stop(
    state: AnswerControllerState,
    *,
    reason: AnswerControllerStopReason,
    rationale: str,
    structured_checks: Sequence[str],
) -> None:
    if state.stop_state is not None:
        return
    state.stop_state = AnswerControllerStopDecision(
        should_stop=True,
        reason=reason,
        public_rationale=rationale,
        final_answer_posture=state.active_contract.answer_posture_if_partial,
        structured_checks=_copy_string_tuple(structured_checks),
    )


def run_offline_answer_controller_loop(
    initial_state: AnswerControllerState,
    executor: ActionExecutor | None = None,
    *,
    initial_evidence_used: Sequence[EvidenceReference] = (),
    initial_warnings_to_analyst_or_author: Sequence[str] = (),
    marginal_value_judgments_by_iteration: Mapping[int, MarginalValueJudgment] | None = None,
    max_decisions: int | None = None,
) -> AnswerControllerLoopResult:
    """Run a bounded offline loop from state snapshot to fulfillment handoff."""
    state = deepcopy(initial_state)
    action_executor = executor or FixtureDrivenActionExecutor()
    evidence_used = list(initial_evidence_used)
    warnings = list(initial_warnings_to_analyst_or_author)
    simulated_outcomes: list[SimulatedActionOutcome] = []
    decision_limit = max(1, int(max_decisions or (state.caps.max_iterations + 2)))

    while len(state.action_history) < decision_limit:
        marginal_value_judgment = (marginal_value_judgments_by_iteration or {}).get(state.iteration)
        if marginal_value_judgment is not None:
            stop_decision = decide_answer_controller_stop(
                state,
                marginal_value_judgment=marginal_value_judgment,
            )
            if stop_decision.should_stop:
                action = _build_stop_action_from_decision(stop_decision, iteration=state.iteration)
                state = apply_answer_controller_action_result(state, action)
                break

        action = decide_answer_controller_action(state)
        state = apply_answer_controller_action_result(state, action)
        state = _apply_evidence_state_delta(state, action.next_state_delta)

        if action.action_name in _STOP_ACTIONS:
            break

        outcome = action_executor(state, action)
        simulated_outcomes.append(outcome)
        evidence_used.extend(outcome.evidence_used)
        warnings.extend(outcome.warnings_to_analyst_or_author)
        state = _apply_evidence_state_delta(state, outcome.evidence_state_delta)

        no_op_reason = action.skip_reason_or_none or outcome.no_op_reason
        if no_op_reason:
            _mark_offline_stop(
                state,
                reason=AnswerControllerStopReason.NO_USEFUL_NEW_QUERY,
                rationale=f"Offline simulated action made no state-changing progress: {no_op_reason}.",
                structured_checks=("offline_simulated_noop", no_op_reason),
            )
            break
        if outcome.stop_loop:
            stop_decision = decide_answer_controller_stop(state)
            _mark_offline_stop(
                state,
                reason=stop_decision.reason if stop_decision.should_stop else AnswerControllerStopReason.NO_USEFUL_NEW_QUERY,
                rationale=stop_decision.public_rationale,
                structured_checks=stop_decision.structured_checks,
            )
            break

        state.iteration = max(state.iteration + 1, action.iteration + 1)

    else:
        _mark_offline_stop(
            state,
            reason=AnswerControllerStopReason.MAX_ITERATIONS,
            rationale="The offline controller loop reached its decision cap.",
            structured_checks=("offline_decision_cap",),
        )

    fulfillment = build_answer_contract_fulfillment(
        state,
        evidence_used=evidence_used,
        warnings_to_Analyst_or_Author=warnings,
    )
    state.fulfillment_handoff_draft = fulfillment
    return AnswerControllerLoopResult(
        final_state=state,
        fulfillment_handoff=fulfillment,
        evidence_used=tuple(evidence_used),
        simulated_outcomes=tuple(simulated_outcomes),
    )


def run_offline_answer_controller_loop_from_pipeline_facts(
    facts: PipelineAnswerContractFacts,
    executor: ActionExecutor | None = None,
    *,
    marginal_value_judgments_by_iteration: Mapping[int, MarginalValueJudgment] | None = None,
    max_decisions: int | None = None,
) -> AnswerControllerLoopResult:
    """Adapt pipeline facts, then run the bounded fixture-driven loop."""
    adapted = adapt_pipeline_facts_to_answer_contract_controller(facts)
    return run_offline_answer_controller_loop(
        adapted.state,
        executor,
        initial_evidence_used=adapted.evidence_used,
        initial_warnings_to_analyst_or_author=facts.evidence.warnings_to_analyst_or_author,
        marginal_value_judgments_by_iteration=marginal_value_judgments_by_iteration,
        max_decisions=max_decisions,
    )


__all__ = [
    "AnswerControllerLoopResult",
    "FixtureDrivenActionExecutor",
    "SimulatedActionOutcome",
    "run_offline_answer_controller_loop",
    "run_offline_answer_controller_loop_from_pipeline_facts",
]
