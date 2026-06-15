"""Mechanical orchestrator adapter for authoritative-source action readiness.

This module keeps pipeline orchestration thin around the named authoritative
source action seam. It collects already-computed orchestrator facts, calls the
action builder, and assembles trace fragments. It does not decide authority
posture, retrieve, route providers, choose depth, alter prompts, or affect final
answers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from core.authoritative_source_action import (
    AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY,
    AuthoritativeSourceActionFacts,
    AuthoritativeSourceActionResult,
    build_authoritative_source_obligation_state_and_action,
)
from core.controller_loop_spine import ControllerLoopSpineInput
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
)
from core.official_source_obligation_bridge import (
    OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY,
)
from core.run_controller import RunController

_TERMINAL_STOP_APPROVED_KEY = "terminal_stop" + "_approved"
_SEARCH_WORK_SHADOW_LANE_TRACE_KEY = "search_work_shadow_lane_projection"


@dataclass(frozen=True)
class AuthoritativeSourceActionOrchestratorHandoff:
    """Compatibility runtime values produced by the lifecycle adapter seam."""

    action_result: AuthoritativeSourceActionResult

    @property
    def recommendation(self) -> dict[str, Any]:
        return self.action_result.recommendation

    @property
    def active_source_class_recovery_lifecycle(self) -> dict[str, Any]:
        return self.action_result.active_source_class_recovery_lifecycle

    @property
    def official_canonical_recovery_execution_admitted(self) -> bool:
        return self.action_result.official_canonical_recovery_execution_admitted

    @property
    def official_source_obligation_bridge_trace(self) -> dict[str, Any] | None:
        return self.action_result.official_source_obligation_bridge_trace

    @property
    def official_canonical_recovery_query_acquisition_trace(
        self,
    ) -> dict[str, Any] | None:
        return self.action_result.official_canonical_recovery_query_acquisition_trace

    @property
    def official_canonical_recovery_execution_admission_trace(
        self,
    ) -> dict[str, Any] | None:
        return self.action_result.official_canonical_recovery_execution_admission_trace

    @property
    def authoritative_source_action_trace(self) -> dict[str, Any]:
        return self.action_result.trace

    def compatibility_runtime_values(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        bool,
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, Any],
    ]:
        return (
            self.recommendation,
            self.active_source_class_recovery_lifecycle,
            self.official_canonical_recovery_execution_admitted,
            self.official_source_obligation_bridge_trace,
            self.official_canonical_recovery_query_acquisition_trace,
            self.official_canonical_recovery_execution_admission_trace,
            self.authoritative_source_action_trace,
        )

    def legacy_runtime_values(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        bool,
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, Any],
    ]:
        return self.compatibility_runtime_values()


def build_authoritative_source_action_facts_from_orchestrator_state(
    controller: RunController,
    *,
    orchestrator_state: Mapping[str, Any],
) -> AuthoritativeSourceActionFacts:
    """Collect sanitized action-builder facts from existing orchestrator locals."""

    source_tier = _mapping(orchestrator_state.get("_source_tier_recovery_lifecycle"))
    source_domain = _mapping(
        orchestrator_state.get("_source_domain_recovery_lifecycle")
    )
    answer_contract_result = orchestrator_state.get(
        "_pre_recovery_answer_contract_result"
    )
    recommendation = _mapping(
        orchestrator_state.get("_source_class_recovery_lifecycle_recommendation")
    )
    checkpoint_trace = _mapping(
        orchestrator_state.get("evidence_integration_checkpoint_trace")
    )
    anchor_packet = _mapping(orchestrator_state.get("anchor_packet_telemetry"))
    nested_anchor_packet = _mapping(anchor_packet.get("anchor_packet"))
    ordinary_continuation = _mapping(
        orchestrator_state.get("ordinary_continuation_candidate_trace")
    )
    retrieval_batch_dispatch = _mapping(
        orchestrator_state.get("retrieval_batch_dispatch_trace")
    )
    evaluator_gate = _mapping(
        orchestrator_state.get("evaluator_continuation_spine_gate_trace")
    )
    expander_gate = _mapping(
        orchestrator_state.get("expander_continuation_spine_gate_trace")
    )
    scout_gate = _mapping(orchestrator_state.get("scout_continuation_spine_gate_trace"))
    conflict_resolution = _mapping(
        orchestrator_state.get("active_conflict_resolution_lifecycle")
    )
    scout_fired = bool(orchestrator_state.get("scout_fired"))
    iterations_run = _int_value(orchestrator_state.get("iterations_run"))
    max_iterations = _int_value(orchestrator_state.get("max_iterations"))
    waste_flags = set(_sequence(orchestrator_state.get("waste_flags")))
    run_kernel = orchestrator_state.get("run_kernel")
    run_kernel_state = getattr(run_kernel, "state", None)
    run_kernel_projections = _mapping(getattr(run_kernel_state, "projections", None))

    return AuthoritativeSourceActionFacts(
        query=_string_or_none(orchestrator_state.get("query")),
        intent=_string_or_none(orchestrator_state.get("intent")),
        report_type=_string_or_none(orchestrator_state.get("report_type")),
        query_type=_string_or_none(orchestrator_state.get("query_type")),
        core_topic=_string_or_none(orchestrator_state.get("core_topic")),
        primary_entity=_string_or_none(orchestrator_state.get("primary_entity")),
        recommendation=recommendation,
        source_class_observability=_mapping(
            orchestrator_state.get(
                "_source_class_recovery_answer_contract_observability"
            )
        ),
        source_class_evidence_signals=source_class_recovery_evidence_signals(
            source_tier_recovery_lifecycle=source_tier,
            source_domain_recovery_lifecycle=source_domain,
        ),
        search_work_official_current_recovery_projection=_mapping(
            run_kernel_projections.get(_SEARCH_WORK_SHADOW_LANE_TRACE_KEY)
        ),
        run_search_judgment_projection=_mapping(
            orchestrator_state.get("search_judgment_projection")
        ),
        answer_contract_family=_answer_contract_family(answer_contract_result),
        answer_contract_source_classes_missing=(
            _answer_contract_source_classes_missing(answer_contract_result)
        ),
        answer_contract_unfulfilled_items=_answer_contract_unfulfilled_items(
            answer_contract_result
        ),
        answer_contract_partial_items=_answer_contract_partial_items(
            answer_contract_result
        ),
        answer_contract_recovery_query_candidates=(
            _answer_contract_recovery_query_candidates(answer_contract_result)
        ),
        corpus_state=_string_or_none(orchestrator_state.get("corpus_state")),
        corpus_weak=bool(orchestrator_state.get("corpus_weak")),
        weak_corpus_recovery_considered=bool(
            orchestrator_state.get("weak_corpus_recovery_considered")
        ),
        weak_corpus_recovery_used=bool(
            orchestrator_state.get("weak_corpus_recovery_used")
        ),
        weak_corpus_recovery_skip_reason=_string_or_none(
            orchestrator_state.get("weak_corpus_recovery_skip_reason")
        ),
        evidence_checkpoint_action_name=_checkpoint_action_name(checkpoint_trace),
        current_search_depth=_string_or_none(
            orchestrator_state.get("current_search_depth_for_recovery")
        ),
        iteration_budget_available=iterations_run < max_iterations,
        answer_contract_source_class_slot_available=max_iterations > 1,
        retrieve_to_anchor_recommended=(
            (
                anchor_packet.get("anchor_packet_next_action") == "retrieve_to_anchor"
                or nested_anchor_packet.get("next_action") == "retrieve_to_anchor"
            )
            and not _source_class_gap_signal_present(recommendation)
        ),
        provider_policy_reusable=bool(
            orchestrator_state.get("provider_policy_reusable", True)
        ),
        provider_swap_required=bool(
            orchestrator_state.get("provider_swap_required", False)
        ),
        search_depth_reusable=bool(
            orchestrator_state.get("search_depth_reusable", True)
        ),
        search_depth_escalation_required=bool(
            orchestrator_state.get("search_depth_escalation_required", False)
        ),
        ordinary_continuation_path_active=(
            _ordinary_continuation_path_active(
                ordinary_continuation=ordinary_continuation,
                retrieval_batch_dispatch=retrieval_batch_dispatch,
                evaluator_gate=evaluator_gate,
                expander_gate=expander_gate,
                scout_gate=scout_gate,
                scout_fired=scout_fired,
            )
            and not _source_class_gap_signal_present(recommendation)
        ),
        conflict_resolution_owns_path=bool(
            orchestrator_state.get("conflict_resolution_owns_path")
            or conflict_resolution.get("active_conflict_resolution_used")
            or conflict_resolution.get("active_conflict_resolution_eligible")
        ),
        query_redundancy_skipped="query_redundancy_skipped" in waste_flags,
        iteration_budget_hard_exhausted=(
            iterations_run >= max_iterations and max_iterations <= 1
        ),
        terminal_stop_approved=bool(checkpoint_trace.get(_TERMINAL_STOP_APPROVED_KEY)),
        prior_recovery_attempt_count=_prior_recovery_attempt_count(controller),
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=max(0, max_iterations - iterations_run),
    )


def build_authoritative_source_action_orchestrator_handoff(
    controller: RunController,
    *,
    orchestrator_state: Mapping[str, Any],
    logger: Any | None = None,
) -> AuthoritativeSourceActionOrchestratorHandoff:
    """Build facts, call the named action seam, and return legacy handoff values."""

    facts = build_authoritative_source_action_facts_from_orchestrator_state(
        controller,
        orchestrator_state=orchestrator_state,
    )
    return AuthoritativeSourceActionOrchestratorHandoff(
        build_authoritative_source_obligation_state_and_action(
            controller,
            facts=facts,
            logger=logger,
        )
    )


def source_class_recovery_evidence_signals(
    *,
    source_tier_recovery_lifecycle: Mapping[str, Any],
    source_domain_recovery_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the compact evidence-signal payload consumed by the controller."""

    return {
        "source_tier_counts": source_tier_recovery_lifecycle.get(
            "source_tier_counts"
        ),
        "source_domain_counts": source_domain_recovery_lifecycle.get(
            "source_domain_counts"
        ),
        "top_source_domains": source_domain_recovery_lifecycle.get(
            "top_source_domains"
        ),
        "unique_source_domain_count": source_domain_recovery_lifecycle.get(
            "unique_source_domain_count"
        ),
        "on_domain_source_count": source_domain_recovery_lifecycle.get(
            "on_domain_source_count"
        ),
        "off_domain_source_count": source_domain_recovery_lifecycle.get(
            "off_domain_source_count"
        ),
        "official_evidence_found": source_tier_recovery_lifecycle.get(
            "official_evidence_found"
        ),
        "community_signal_found": source_tier_recovery_lifecycle.get(
            "community_signal_found"
        ),
        "low_trust_sources_found": source_tier_recovery_lifecycle.get(
            "low_trust_sources_found"
        ),
        "pollution_detected": source_tier_recovery_lifecycle.get(
            "pollution_detected"
        ),
    }


def authoritative_source_action_trace_fragment(
    *,
    authoritative_source_action_trace: Mapping[str, Any] | None,
    official_source_obligation_bridge_trace: Mapping[str, Any] | None,
    official_canonical_recovery_query_acquisition_trace: Mapping[str, Any] | None,
    official_canonical_recovery_execution_admission_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Attach authoritative-source action and legacy adapter traces if present."""

    fragment: dict[str, Any] = {}
    if isinstance(authoritative_source_action_trace, Mapping):
        fragment[AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY] = dict(
            authoritative_source_action_trace
        )
    if isinstance(official_source_obligation_bridge_trace, Mapping):
        fragment[OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY] = dict(
            official_source_obligation_bridge_trace
        )
    if isinstance(official_canonical_recovery_query_acquisition_trace, Mapping):
        fragment[OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY] = dict(
            official_canonical_recovery_query_acquisition_trace
        )
    if isinstance(official_canonical_recovery_execution_admission_trace, Mapping):
        fragment[OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY] = dict(
            official_canonical_recovery_execution_admission_trace
        )
    return fragment


def _checkpoint_action_name(checkpoint_trace: Mapping[str, Any]) -> str | None:
    return ControllerLoopSpineInput.from_traces(
        checkpoint_trace=checkpoint_trace
    ).checkpoint_action.action_name


def _answer_contract_family(answer_contract_result: Any) -> str | None:
    contract = getattr(
        getattr(answer_contract_result, "adapter_result", None),
        "contract",
        None,
    )
    family = getattr(contract, "family", None)
    value = getattr(family, "value", family)
    return _string_or_none(value)


def _answer_contract_source_classes_missing(
    answer_contract_result: Any,
) -> tuple[Any, ...]:
    evidence_state = getattr(getattr(answer_contract_result, "state", None), "evidence_state_summary", None)
    return _sequence(getattr(evidence_state, "source_classes_missing", ()))


def _answer_contract_unfulfilled_items(answer_contract_result: Any) -> tuple[Any, ...]:
    handoff = getattr(answer_contract_result, "fulfillment_handoff", None)
    return _sequence(getattr(handoff, "unfulfilled_items", ()))


def _answer_contract_partial_items(answer_contract_result: Any) -> tuple[Any, ...]:
    handoff = getattr(answer_contract_result, "fulfillment_handoff", None)
    return _sequence(getattr(handoff, "partial_items", ()))


def _answer_contract_recovery_query_candidates(
    answer_contract_result: Any,
) -> tuple[Any, ...]:
    evidence_state = getattr(
        getattr(answer_contract_result, "state", None),
        "evidence_state_summary",
        None,
    )
    return _sequence(getattr(evidence_state, "next_queries", ()))


def _prior_recovery_attempt_count(controller: RunController) -> int:
    state = getattr(controller, "state", None)
    return _int_value(getattr(state, "active_source_class_recovery_attempt_count", 0))


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _source_class_gap_signal_present(recommendation: Mapping[str, Any]) -> bool:
    return bool(
        recommendation.get("source_class_recovery_recommended")
        or recommendation.get("source_class_underfire_shadow")
        or recommendation.get("source_class_gap_candidates")
        or recommendation.get("missing_expected_source_classes")
    )


def _ordinary_continuation_path_active(
    *,
    ordinary_continuation: Mapping[str, Any],
    retrieval_batch_dispatch: Mapping[str, Any],
    evaluator_gate: Mapping[str, Any],
    expander_gate: Mapping[str, Any],
    scout_gate: Mapping[str, Any],
    scout_fired: bool = False,
) -> bool:
    if scout_fired:
        return True
    if ordinary_continuation.get("used"):
        return True
    for gate in (evaluator_gate, expander_gate, scout_gate):
        if gate.get("targeted_retrieval_dispatch_authorized"):
            return True
    return False


def _sequence(value: Any) -> tuple[Any, ...]:
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _int_value(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


__all__ = [
    "AuthoritativeSourceActionOrchestratorHandoff",
    "authoritative_source_action_trace_fragment",
    "build_authoritative_source_action_facts_from_orchestrator_state",
    "build_authoritative_source_action_orchestrator_handoff",
    "source_class_recovery_evidence_signals",
]
