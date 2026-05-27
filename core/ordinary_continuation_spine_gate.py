"""Bounded ordinary-continuation spine gate adapter.

This module owns the bounded ordinary-continuation gate composition for the
currently promoted evaluator ``new_queries``, expander ``component_queries``,
and scout ``directed_queries`` paths. Retrieval-stop ordinary continuation
remains passive here.

It consumes already-computed controller facts and returns JSON-safe scheduling
decisions. It does not execute retrieval, choose providers, choose depth,
generate queries, build prompts, or alter final-answer handoffs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.controller_action_envelope import (
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)
from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    ControllerLoopSpineResult,
    build_controller_loop_spine_result,
)
from core.evidence_integration_checkpoint import (
    evidence_integration_checkpoint_unavailable_trace,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    ORDINARY_CONTINUATION_TRACE_KEY,
    SCOUT_DIRECTED_QUERIES,
    build_ordinary_continuation_candidate,
    mark_ordinary_continuation_candidate_spine_authorized,
)


@dataclass(frozen=True)
class EvaluatorContinuationSpineGateFacts:
    """Already-computed facts needed to compose evaluator gate authorization."""

    evaluator_queries: tuple[str, ...]
    prior_queries: tuple[str, ...]
    current_iteration: int
    max_iterations: int
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    source_class_lifecycle_trace: dict[str, Any]
    weak_corpus_lifecycle_trace: dict[str, Any] | None = None
    conflict_resolution_lifecycle_trace: dict[str, Any] | None = None
    ordinary_continuation_candidate_trace: dict[str, Any] | None = None
    targeted_retrieval_lifecycle_trace: dict[str, Any] | None = None

    @classmethod
    def from_traces(
        cls,
        *,
        evaluator_queries: list[str] | tuple[str, ...],
        prior_queries: list[str] | tuple[str, ...],
        current_iteration: int,
        max_iterations: int,
        checkpoint_trace: Mapping[str, Any],
        checkpoint_handoff: Mapping[str, Any],
        source_class_lifecycle_trace: Mapping[str, Any] | None,
        weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
        conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
        ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
        targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
    ) -> EvaluatorContinuationSpineGateFacts:
        return cls(
            evaluator_queries=_compact_strings(evaluator_queries),
            prior_queries=_compact_strings(prior_queries),
            current_iteration=max(0, int(current_iteration or 0)),
            max_iterations=max(0, int(max_iterations or 0)),
            checkpoint_trace=_json_safe_mapping(checkpoint_trace),
            checkpoint_handoff=_json_safe_mapping(checkpoint_handoff),
            source_class_lifecycle_trace=_json_safe_mapping(
                source_class_lifecycle_trace
            ),
            weak_corpus_lifecycle_trace=(
                _json_safe_mapping(weak_corpus_lifecycle_trace)
                if weak_corpus_lifecycle_trace is not None
                else None
            ),
            conflict_resolution_lifecycle_trace=(
                _json_safe_mapping(conflict_resolution_lifecycle_trace)
                if conflict_resolution_lifecycle_trace is not None
                else None
            ),
            ordinary_continuation_candidate_trace=(
                _json_safe_mapping(ordinary_continuation_candidate_trace)
                if ordinary_continuation_candidate_trace is not None
                else None
            ),
            targeted_retrieval_lifecycle_trace=(
                _json_safe_mapping(targeted_retrieval_lifecycle_trace)
                if targeted_retrieval_lifecycle_trace is not None
                else None
            ),
        )


@dataclass(frozen=True)
class EvaluatorContinuationSpinePregateResult:
    """Candidate and first spine pass used before targeted lifecycle assembly."""

    ordinary_continuation_candidate_trace: dict[str, Any]
    controller_loop_spine_result: ControllerLoopSpineResult


@dataclass(frozen=True)
class EvaluatorContinuationSpineGateOutput:
    """Scheduling decision returned to the runtime shell."""

    authorized: bool
    authorized_queries: list[str]
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    targeted_retrieval_lifecycle_trace: dict[str, Any]
    ordinary_continuation_candidate_trace: dict[str, Any]
    evaluator_continuation_spine_gate_trace: dict[str, Any]
    checkpoint_decided: bool
    fallback_preserves_legacy: bool
    reason: str


@dataclass(frozen=True)
class ExpanderContinuationSpineGateFacts:
    """Already-computed facts needed to compose expander gate authorization."""

    component_queries: tuple[str, ...]
    prior_queries: tuple[str, ...]
    current_iteration: int
    max_iterations: int
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    source_class_lifecycle_trace: dict[str, Any]
    weak_corpus_lifecycle_trace: dict[str, Any] | None = None
    conflict_resolution_lifecycle_trace: dict[str, Any] | None = None
    ordinary_continuation_candidate_trace: dict[str, Any] | None = None
    targeted_retrieval_lifecycle_trace: dict[str, Any] | None = None

    @classmethod
    def from_traces(
        cls,
        *,
        component_queries: list[str] | tuple[str, ...],
        prior_queries: list[str] | tuple[str, ...],
        current_iteration: int,
        max_iterations: int,
        checkpoint_trace: Mapping[str, Any],
        checkpoint_handoff: Mapping[str, Any],
        source_class_lifecycle_trace: Mapping[str, Any] | None,
        weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
        conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
        ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
        targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
    ) -> ExpanderContinuationSpineGateFacts:
        return cls(
            component_queries=_compact_strings(component_queries),
            prior_queries=_compact_strings(prior_queries),
            current_iteration=max(0, int(current_iteration or 0)),
            max_iterations=max(0, int(max_iterations or 0)),
            checkpoint_trace=_json_safe_mapping(checkpoint_trace),
            checkpoint_handoff=_json_safe_mapping(checkpoint_handoff),
            source_class_lifecycle_trace=_json_safe_mapping(
                source_class_lifecycle_trace
            ),
            weak_corpus_lifecycle_trace=(
                _json_safe_mapping(weak_corpus_lifecycle_trace)
                if weak_corpus_lifecycle_trace is not None
                else None
            ),
            conflict_resolution_lifecycle_trace=(
                _json_safe_mapping(conflict_resolution_lifecycle_trace)
                if conflict_resolution_lifecycle_trace is not None
                else None
            ),
            ordinary_continuation_candidate_trace=(
                _json_safe_mapping(ordinary_continuation_candidate_trace)
                if ordinary_continuation_candidate_trace is not None
                else None
            ),
            targeted_retrieval_lifecycle_trace=(
                _json_safe_mapping(targeted_retrieval_lifecycle_trace)
                if targeted_retrieval_lifecycle_trace is not None
                else None
            ),
        )


@dataclass(frozen=True)
class ExpanderContinuationSpinePregateResult:
    """Candidate and first spine pass used before targeted lifecycle assembly."""

    ordinary_continuation_candidate_trace: dict[str, Any]
    controller_loop_spine_result: ControllerLoopSpineResult


@dataclass(frozen=True)
class ExpanderContinuationSpineGateOutput:
    """Scheduling decision returned to the runtime shell."""

    authorized: bool
    authorized_queries: list[str]
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    targeted_retrieval_lifecycle_trace: dict[str, Any]
    ordinary_continuation_candidate_trace: dict[str, Any]
    expander_continuation_spine_gate_trace: dict[str, Any]
    checkpoint_decided: bool
    fallback_preserves_legacy: bool
    reason: str


@dataclass(frozen=True)
class ScoutContinuationSpineGateFacts:
    """Already-computed facts needed to compose scout gate authorization."""

    scout_queries: tuple[str, ...]
    prior_queries: tuple[str, ...]
    current_iteration: int
    max_iterations: int
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    source_class_lifecycle_trace: dict[str, Any]
    weak_corpus_lifecycle_trace: dict[str, Any] | None = None
    conflict_resolution_lifecycle_trace: dict[str, Any] | None = None
    ordinary_continuation_candidate_trace: dict[str, Any] | None = None
    targeted_retrieval_lifecycle_trace: dict[str, Any] | None = None

    @classmethod
    def from_traces(
        cls,
        *,
        scout_queries: list[str] | tuple[str, ...],
        prior_queries: list[str] | tuple[str, ...],
        current_iteration: int,
        max_iterations: int,
        checkpoint_trace: Mapping[str, Any],
        checkpoint_handoff: Mapping[str, Any],
        source_class_lifecycle_trace: Mapping[str, Any] | None,
        weak_corpus_lifecycle_trace: Mapping[str, Any] | None = None,
        conflict_resolution_lifecycle_trace: Mapping[str, Any] | None = None,
        ordinary_continuation_candidate_trace: Mapping[str, Any] | None = None,
        targeted_retrieval_lifecycle_trace: Mapping[str, Any] | None = None,
    ) -> ScoutContinuationSpineGateFacts:
        return cls(
            scout_queries=_compact_strings(scout_queries),
            prior_queries=_compact_strings(prior_queries),
            current_iteration=max(0, int(current_iteration or 0)),
            max_iterations=max(0, int(max_iterations or 0)),
            checkpoint_trace=_json_safe_mapping(checkpoint_trace),
            checkpoint_handoff=_json_safe_mapping(checkpoint_handoff),
            source_class_lifecycle_trace=_json_safe_mapping(
                source_class_lifecycle_trace
            ),
            weak_corpus_lifecycle_trace=(
                _json_safe_mapping(weak_corpus_lifecycle_trace)
                if weak_corpus_lifecycle_trace is not None
                else None
            ),
            conflict_resolution_lifecycle_trace=(
                _json_safe_mapping(conflict_resolution_lifecycle_trace)
                if conflict_resolution_lifecycle_trace is not None
                else None
            ),
            ordinary_continuation_candidate_trace=(
                _json_safe_mapping(ordinary_continuation_candidate_trace)
                if ordinary_continuation_candidate_trace is not None
                else None
            ),
            targeted_retrieval_lifecycle_trace=(
                _json_safe_mapping(targeted_retrieval_lifecycle_trace)
                if targeted_retrieval_lifecycle_trace is not None
                else None
            ),
        )


@dataclass(frozen=True)
class ScoutContinuationSpinePregateResult:
    """Candidate and first spine pass used before targeted lifecycle assembly."""

    ordinary_continuation_candidate_trace: dict[str, Any]
    controller_loop_spine_result: ControllerLoopSpineResult


@dataclass(frozen=True)
class ScoutContinuationSpineGateOutput:
    """Scheduling decision returned to the runtime shell."""

    authorized: bool
    authorized_queries: list[str]
    checkpoint_trace: dict[str, Any]
    checkpoint_handoff: dict[str, Any]
    targeted_retrieval_lifecycle_trace: dict[str, Any]
    ordinary_continuation_candidate_trace: dict[str, Any]
    scout_continuation_spine_gate_trace: dict[str, Any]
    checkpoint_decided: bool
    fallback_preserves_legacy: bool
    reason: str


def evaluator_continuation_spine_gate_defaults() -> dict[str, Any]:
    """Return the AG-44C default not-evaluated gate trace."""
    return {
        "available": False,
        "reason": "not_evaluated",
        "targeted_retrieval_dispatch_authorized": False,
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": [],
        "query_provenance": None,
    }


def evaluator_continuation_spine_gate_exception_trace() -> dict[str, Any]:
    """Return the AG-44C exception trace without changing fallback behavior."""
    trace = evaluator_continuation_spine_gate_defaults()
    trace["reason"] = "evaluator_continuation_gate_exception"
    return trace


def expander_continuation_spine_gate_defaults() -> dict[str, Any]:
    """Return the AG-45A default not-evaluated gate trace."""
    return {
        "available": False,
        "reason": "not_evaluated",
        "targeted_retrieval_dispatch_authorized": False,
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": [],
        "query_provenance": None,
    }


def expander_continuation_spine_gate_exception_trace() -> dict[str, Any]:
    """Return an exception trace that blocks expander scheduling."""
    trace = expander_continuation_spine_gate_defaults()
    trace["reason"] = "expander_continuation_gate_exception"
    return trace


def scout_continuation_spine_gate_defaults() -> dict[str, Any]:
    """Return the AG-45C default not-evaluated gate trace."""
    return {
        "available": False,
        "reason": "not_evaluated",
        "targeted_retrieval_dispatch_authorized": False,
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": [],
        "query_provenance": None,
    }


def scout_continuation_spine_gate_exception_trace() -> dict[str, Any]:
    """Return an exception trace that blocks scout scheduling."""
    trace = scout_continuation_spine_gate_defaults()
    trace["reason"] = "scout_continuation_gate_exception"
    return trace


def build_evaluator_continuation_candidate(
    *,
    evaluator_queries: list[str] | tuple[str, ...],
    prior_queries: list[str] | tuple[str, ...],
    current_iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Return the bounded evaluator ordinary-continuation candidate."""
    facts = EvaluatorContinuationSpineGateFacts.from_traces(
        evaluator_queries=evaluator_queries,
        prior_queries=prior_queries,
        current_iteration=current_iteration,
        max_iterations=max_iterations,
        checkpoint_trace={},
        checkpoint_handoff={},
        source_class_lifecycle_trace={},
    )
    return _evaluator_candidate_from_facts(facts)


def build_expander_continuation_candidate(
    *,
    component_queries: list[str] | tuple[str, ...],
    prior_queries: list[str] | tuple[str, ...],
    current_iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Return the bounded expander ordinary-continuation candidate."""
    facts = ExpanderContinuationSpineGateFacts.from_traces(
        component_queries=component_queries,
        prior_queries=prior_queries,
        current_iteration=current_iteration,
        max_iterations=max_iterations,
        checkpoint_trace={},
        checkpoint_handoff={},
        source_class_lifecycle_trace={},
    )
    return _expander_candidate_from_facts(facts)


def build_scout_continuation_candidate(
    *,
    scout_queries: list[str] | tuple[str, ...],
    prior_queries: list[str] | tuple[str, ...],
    current_iteration: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Return the bounded scout ordinary-continuation candidate."""
    facts = ScoutContinuationSpineGateFacts.from_traces(
        scout_queries=scout_queries,
        prior_queries=prior_queries,
        current_iteration=current_iteration,
        max_iterations=max_iterations,
        checkpoint_trace={},
        checkpoint_handoff={},
        source_class_lifecycle_trace={},
    )
    return _scout_candidate_from_facts(facts)


def build_evaluator_continuation_spine_pregate(
    facts: EvaluatorContinuationSpineGateFacts,
) -> EvaluatorContinuationSpinePregateResult:
    """Build the evaluator candidate and first spine pass."""
    candidate = _evaluator_candidate_from_facts(facts)
    spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=candidate,
        )
    )
    return EvaluatorContinuationSpinePregateResult(
        ordinary_continuation_candidate_trace=candidate,
        controller_loop_spine_result=spine_result,
    )


def build_expander_continuation_spine_pregate(
    facts: ExpanderContinuationSpineGateFacts,
) -> ExpanderContinuationSpinePregateResult:
    """Build the expander candidate and first spine pass."""
    candidate = _expander_candidate_from_facts(facts)
    spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=candidate,
        )
    )
    return ExpanderContinuationSpinePregateResult(
        ordinary_continuation_candidate_trace=candidate,
        controller_loop_spine_result=spine_result,
    )


def build_scout_continuation_spine_pregate(
    facts: ScoutContinuationSpineGateFacts,
) -> ScoutContinuationSpinePregateResult:
    """Build the scout candidate and first spine pass."""
    candidate = _scout_candidate_from_facts(facts)
    spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=candidate,
        )
    )
    return ScoutContinuationSpinePregateResult(
        ordinary_continuation_candidate_trace=candidate,
        controller_loop_spine_result=spine_result,
    )


def authorize_evaluator_continuation_spine_gate(
    facts: EvaluatorContinuationSpineGateFacts,
) -> EvaluatorContinuationSpineGateOutput:
    """Authorize bounded evaluator continuation or return AG-44C fallback."""
    ordinary_candidate = (
        dict(facts.ordinary_continuation_candidate_trace)
        if facts.ordinary_continuation_candidate_trace is not None
        else _evaluator_candidate_from_facts(facts)
    )
    final_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=ordinary_candidate,
            targeted_retrieval_lifecycle_trace=(
                facts.targeted_retrieval_lifecycle_trace
            ),
        )
    )
    packet = dict(final_spine_result.trace_packet)
    authorized = (
        final_spine_result.dispatch_authorization.authorized_action_name
        == RETRIEVE_TARGETED
    )
    authorized_queries = [
        str(query)
        for query in packet.get("targeted_retrieval_authorized_queries", [])
        if str(query).strip()
    ]
    gate_trace = _evaluator_gate_trace_from_packet(
        packet=packet,
        authorized=authorized,
        authorized_queries=authorized_queries,
        authorized_action_name=(
            final_spine_result.dispatch_authorization.authorized_action_name
        ),
    )
    targeted_trace = _json_safe_mapping(facts.targeted_retrieval_lifecycle_trace)
    checkpoint_trace = dict(packet)
    checkpoint_handoff = dict(facts.checkpoint_handoff)

    if authorized:
        ordinary_candidate = mark_ordinary_continuation_candidate_spine_authorized(
            ordinary_candidate,
            used=True,
        )
        targeted_trace = {
            **targeted_trace,
            "targeted_retrieval_candidate_used": True,
        }
        checkpoint_trace[ORDINARY_CONTINUATION_TRACE_KEY] = dict(ordinary_candidate)
        return EvaluatorContinuationSpineGateOutput(
            authorized=True,
            authorized_queries=list(authorized_queries),
            checkpoint_trace=checkpoint_trace,
            checkpoint_handoff=checkpoint_handoff,
            targeted_retrieval_lifecycle_trace=targeted_trace,
            ordinary_continuation_candidate_trace=ordinary_candidate,
            evaluator_continuation_spine_gate_trace=gate_trace,
            checkpoint_decided=True,
            fallback_preserves_legacy=False,
            reason=str(gate_trace.get("reason") or "authorized"),
        )

    if packet.get("checkpoint_action_name") not in {
        STOP_INSUFFICIENT_WITH_CAVEAT,
        STOP_SUFFICIENT,
    }:
        return EvaluatorContinuationSpineGateOutput(
            authorized=False,
            authorized_queries=list(facts.evaluator_queries),
            checkpoint_trace=evidence_integration_checkpoint_unavailable_trace(
                "evaluator_continuation_gate_not_authorized_legacy_preserved"
            ),
            checkpoint_handoff={},
            targeted_retrieval_lifecycle_trace=targeted_trace,
            ordinary_continuation_candidate_trace=ordinary_candidate,
            evaluator_continuation_spine_gate_trace=gate_trace,
            checkpoint_decided=False,
            fallback_preserves_legacy=True,
            reason="evaluator_continuation_gate_not_authorized_legacy_preserved",
        )

    return EvaluatorContinuationSpineGateOutput(
        authorized=False,
        authorized_queries=[],
        checkpoint_trace=checkpoint_trace,
        checkpoint_handoff=checkpoint_handoff,
        targeted_retrieval_lifecycle_trace=targeted_trace,
        ordinary_continuation_candidate_trace=ordinary_candidate,
        evaluator_continuation_spine_gate_trace=gate_trace,
        checkpoint_decided=True,
        fallback_preserves_legacy=False,
        reason=str(gate_trace.get("reason") or "terminal_stop_preserved"),
    )


def authorize_expander_continuation_spine_gate(
    facts: ExpanderContinuationSpineGateFacts,
) -> ExpanderContinuationSpineGateOutput:
    """Authorize bounded expander continuation or block scheduling."""
    ordinary_candidate = (
        dict(facts.ordinary_continuation_candidate_trace)
        if facts.ordinary_continuation_candidate_trace is not None
        else _expander_candidate_from_facts(facts)
    )
    final_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=ordinary_candidate,
            targeted_retrieval_lifecycle_trace=(
                facts.targeted_retrieval_lifecycle_trace
            ),
        )
    )
    packet = dict(final_spine_result.trace_packet)
    authorized = (
        final_spine_result.dispatch_authorization.authorized_action_name
        == RETRIEVE_TARGETED
    )
    authorized_queries = [
        str(query)
        for query in packet.get("targeted_retrieval_authorized_queries", [])
        if str(query).strip()
    ]
    gate_trace = _expander_gate_trace_from_packet(
        packet=packet,
        authorized=authorized,
        authorized_queries=authorized_queries,
        authorized_action_name=(
            final_spine_result.dispatch_authorization.authorized_action_name
        ),
    )
    targeted_trace = _json_safe_mapping(facts.targeted_retrieval_lifecycle_trace)
    checkpoint_trace = dict(packet)
    checkpoint_handoff = dict(facts.checkpoint_handoff)

    if authorized:
        ordinary_candidate = mark_ordinary_continuation_candidate_spine_authorized(
            ordinary_candidate,
            used=True,
        )
        targeted_trace = {
            **targeted_trace,
            "targeted_retrieval_candidate_used": True,
        }
        checkpoint_trace[ORDINARY_CONTINUATION_TRACE_KEY] = dict(ordinary_candidate)
        return ExpanderContinuationSpineGateOutput(
            authorized=True,
            authorized_queries=list(authorized_queries),
            checkpoint_trace=checkpoint_trace,
            checkpoint_handoff=checkpoint_handoff,
            targeted_retrieval_lifecycle_trace=targeted_trace,
            ordinary_continuation_candidate_trace=ordinary_candidate,
            expander_continuation_spine_gate_trace=gate_trace,
            checkpoint_decided=True,
            fallback_preserves_legacy=False,
            reason=str(gate_trace.get("reason") or "authorized"),
        )

    return ExpanderContinuationSpineGateOutput(
        authorized=False,
        authorized_queries=[],
        checkpoint_trace=checkpoint_trace,
        checkpoint_handoff=checkpoint_handoff,
        targeted_retrieval_lifecycle_trace=targeted_trace,
        ordinary_continuation_candidate_trace=ordinary_candidate,
        expander_continuation_spine_gate_trace=gate_trace,
        checkpoint_decided=True,
        fallback_preserves_legacy=False,
        reason=str(gate_trace.get("reason") or "expander_gate_not_authorized"),
    )


def authorize_scout_continuation_spine_gate(
    facts: ScoutContinuationSpineGateFacts,
) -> ScoutContinuationSpineGateOutput:
    """Authorize bounded scout continuation or block scheduling."""
    ordinary_candidate = (
        dict(facts.ordinary_continuation_candidate_trace)
        if facts.ordinary_continuation_candidate_trace is not None
        else _scout_candidate_from_facts(facts)
    )
    final_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=facts.checkpoint_trace,
            source_class_lifecycle_trace=facts.source_class_lifecycle_trace,
            weak_corpus_lifecycle_trace=facts.weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=(
                facts.conflict_resolution_lifecycle_trace
            ),
            ordinary_continuation_candidate_trace=ordinary_candidate,
            targeted_retrieval_lifecycle_trace=(
                facts.targeted_retrieval_lifecycle_trace
            ),
        )
    )
    packet = dict(final_spine_result.trace_packet)
    authorized = (
        final_spine_result.dispatch_authorization.authorized_action_name
        == RETRIEVE_TARGETED
    )
    authorized_queries = [
        str(query)
        for query in packet.get("targeted_retrieval_authorized_queries", [])
        if str(query).strip()
    ]
    gate_trace = _scout_gate_trace_from_packet(
        packet=packet,
        authorized=authorized,
        authorized_queries=authorized_queries,
        authorized_action_name=(
            final_spine_result.dispatch_authorization.authorized_action_name
        ),
    )
    targeted_trace = _json_safe_mapping(facts.targeted_retrieval_lifecycle_trace)
    checkpoint_trace = dict(packet)
    checkpoint_handoff = dict(facts.checkpoint_handoff)

    if authorized:
        ordinary_candidate = mark_ordinary_continuation_candidate_spine_authorized(
            ordinary_candidate,
            used=True,
        )
        targeted_trace = {
            **targeted_trace,
            "targeted_retrieval_candidate_used": True,
        }
        checkpoint_trace[ORDINARY_CONTINUATION_TRACE_KEY] = dict(ordinary_candidate)
        return ScoutContinuationSpineGateOutput(
            authorized=True,
            authorized_queries=list(authorized_queries),
            checkpoint_trace=checkpoint_trace,
            checkpoint_handoff=checkpoint_handoff,
            targeted_retrieval_lifecycle_trace=targeted_trace,
            ordinary_continuation_candidate_trace=ordinary_candidate,
            scout_continuation_spine_gate_trace=gate_trace,
            checkpoint_decided=True,
            fallback_preserves_legacy=False,
            reason=str(gate_trace.get("reason") or "authorized"),
        )

    return ScoutContinuationSpineGateOutput(
        authorized=False,
        authorized_queries=[],
        checkpoint_trace=checkpoint_trace,
        checkpoint_handoff=checkpoint_handoff,
        targeted_retrieval_lifecycle_trace=targeted_trace,
        ordinary_continuation_candidate_trace=ordinary_candidate,
        scout_continuation_spine_gate_trace=gate_trace,
        checkpoint_decided=True,
        fallback_preserves_legacy=False,
        reason=str(gate_trace.get("reason") or "scout_gate_not_authorized"),
    )


def _evaluator_candidate_from_facts(
    facts: EvaluatorContinuationSpineGateFacts,
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=EVALUATOR_NEXT_QUERIES,
        ordinary_next_queries=facts.evaluator_queries,
        query_provenance=EVALUATOR_NEXT_QUERIES,
        prior_queries=facts.prior_queries,
        conflict_resolving_queries=(),
        current_iteration=facts.current_iteration,
        max_iterations=facts.max_iterations,
        considered=True,
    ).to_dict()


def _expander_candidate_from_facts(
    facts: ExpanderContinuationSpineGateFacts,
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=EXPANDER_COMPONENT_QUERIES,
        ordinary_next_queries=facts.component_queries,
        query_provenance=EXPANDER_COMPONENT_QUERIES,
        prior_queries=facts.prior_queries,
        conflict_resolving_queries=(),
        current_iteration=facts.current_iteration,
        max_iterations=facts.max_iterations,
        considered=True,
    ).to_dict()


def _scout_candidate_from_facts(
    facts: ScoutContinuationSpineGateFacts,
) -> dict[str, Any]:
    return build_ordinary_continuation_candidate(
        source_path=SCOUT_DIRECTED_QUERIES,
        ordinary_next_queries=facts.scout_queries,
        query_provenance=SCOUT_DIRECTED_QUERIES,
        prior_queries=facts.prior_queries,
        conflict_resolving_queries=(),
        current_iteration=facts.current_iteration,
        max_iterations=facts.max_iterations,
        considered=True,
    ).to_dict()


def _evaluator_gate_trace_from_packet(
    *,
    packet: Mapping[str, Any],
    authorized: bool,
    authorized_queries: list[str],
    authorized_action_name: str | None,
) -> dict[str, Any]:
    return {
        "available": True,
        "reason": packet.get("targeted_retrieval_gate_reason"),
        "checkpoint_action_name": packet.get("checkpoint_action_name"),
        "authorized_action_name": authorized_action_name,
        "targeted_retrieval_dispatch_authorized": bool(authorized),
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": list(authorized_queries) if authorized else [],
        "query_provenance": packet.get(
            "targeted_retrieval_authorized_query_provenance"
        ),
    }


def _expander_gate_trace_from_packet(
    *,
    packet: Mapping[str, Any],
    authorized: bool,
    authorized_queries: list[str],
    authorized_action_name: str | None,
) -> dict[str, Any]:
    return {
        "available": True,
        "reason": packet.get("targeted_retrieval_gate_reason"),
        "checkpoint_action_name": packet.get("checkpoint_action_name"),
        "authorized_action_name": authorized_action_name,
        "targeted_retrieval_dispatch_authorized": bool(authorized),
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": list(authorized_queries) if authorized else [],
        "query_provenance": packet.get(
            "targeted_retrieval_authorized_query_provenance"
        ),
    }


def _scout_gate_trace_from_packet(
    *,
    packet: Mapping[str, Any],
    authorized: bool,
    authorized_queries: list[str],
    authorized_action_name: str | None,
) -> dict[str, Any]:
    return {
        "available": True,
        "reason": packet.get("targeted_retrieval_gate_reason"),
        "checkpoint_action_name": packet.get("checkpoint_action_name"),
        "authorized_action_name": authorized_action_name,
        "targeted_retrieval_dispatch_authorized": bool(authorized),
        "targeted_retrieval_executor_dispatched": False,
        "authorized_queries": list(authorized_queries) if authorized else [],
        "query_provenance": packet.get(
            "targeted_retrieval_authorized_query_provenance"
        ),
    }


def _json_safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in dict(value or {}).items():
        if isinstance(item, Mapping):
            safe[str(key)] = _json_safe_mapping(item)
        elif isinstance(item, tuple):
            safe[str(key)] = list(item)
        else:
            safe[str(key)] = item
    return safe


def _compact_strings(value: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = " ".join(str(item or "").strip().split())[:300]
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


__all__ = [
    "EvaluatorContinuationSpineGateFacts",
    "EvaluatorContinuationSpineGateOutput",
    "EvaluatorContinuationSpinePregateResult",
    "ExpanderContinuationSpineGateFacts",
    "ExpanderContinuationSpineGateOutput",
    "ExpanderContinuationSpinePregateResult",
    "ScoutContinuationSpineGateFacts",
    "ScoutContinuationSpineGateOutput",
    "ScoutContinuationSpinePregateResult",
    "authorize_expander_continuation_spine_gate",
    "authorize_evaluator_continuation_spine_gate",
    "authorize_scout_continuation_spine_gate",
    "build_expander_continuation_candidate",
    "build_expander_continuation_spine_pregate",
    "build_evaluator_continuation_candidate",
    "build_evaluator_continuation_spine_pregate",
    "build_scout_continuation_candidate",
    "build_scout_continuation_spine_pregate",
    "expander_continuation_spine_gate_defaults",
    "expander_continuation_spine_gate_exception_trace",
    "evaluator_continuation_spine_gate_defaults",
    "evaluator_continuation_spine_gate_exception_trace",
    "scout_continuation_spine_gate_defaults",
    "scout_continuation_spine_gate_exception_trace",
]
