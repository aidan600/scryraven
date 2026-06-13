"""Bounded pre-recovery checkpoint and loop-spine stage adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.controller_loop_spine import (
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
    reconcile_retrieval_dispatch_runtime_checkpoint_trace,
)
from core.evidence_integration_checkpoint import (
    build_evidence_integration_checkpoint_trace,
    decide_evidence_integration_checkpoint,
    evidence_integration_checkpoint_unavailable_trace,
)
from core.lifecycle_trace_projection import (
    build_evidence_integration_snapshot_from_runtime,
    conflict_resolution_lifecycle_facts,
)
from core.retrieval_batch_dispatch import RETRIEVAL_BATCH_DISPATCH_TRACE_KEY
from core.retrieval_stop_trace_projection import (
    build_ordinary_continuation_trace_projection,
)
from core.source_class_authority_runtime_adapter import (
    source_class_recovery_action_approved,
    source_class_recovery_checkpoint_refresh_allowed,
)
from core.targeted_retrieval_controller import targeted_retrieval_lifecycle_defaults
from core.targeted_retrieval_runtime_adapter import (
    build_targeted_retrieval_lifecycle_from_runtime,
    compact_runtime_strings,
)


@dataclass(frozen=True)
class RetrievalAuthorityStageResult:
    """Typed handoff from pre-recovery trace assembly back to the orchestrator."""

    evidence_integration_checkpoint_trace: dict[str, Any]
    evidence_integration_checkpoint_handoff: dict[str, Any]
    evidence_integration_checkpoint_decided: bool
    ordinary_continuation_candidate_trace: dict[str, Any]
    targeted_retrieval_lifecycle_trace: dict[str, Any]
    authorized_spine_action: str | None


def build_retrieval_authority_stage(
    *,
    answer_contract_result: Any,
    source_class_recovery_recommendation: dict[str, Any],
    active_source_class_recovery_lifecycle: dict[str, Any],
    active_conflict_resolution_lifecycle: dict[str, Any],
    conflict_resolution_decision: Any,
    weak_corpus_lifecycle_trace: dict[str, Any] | None,
    evidence_integration_checkpoint_trace: dict[str, Any],
    evidence_integration_checkpoint_handoff: dict[str, Any],
    evidence_integration_checkpoint_decided: bool,
    ordinary_continuation_candidate_trace: dict[str, Any],
    retrieval_stop_shadow_telemetry: dict[str, Any],
    retrieval_stop_active_telemetry: dict[str, Any],
    strategy: str,
    is_sufficient: bool,
    corpus_weak: bool,
    corpus_state: str,
    weak_corpus_recovery_used: bool,
    weak_corpus_recovery_attempted: bool,
    weak_corpus_recovery_skip_reason: str | None,
    iterations_run: int,
    max_iterations: int,
    conflict_resolving_queries: list[str] | tuple[str, ...] = (),
    retrieval_batch_dispatch_trace: dict[str, Any] | None = None,
    evaluator_continuation_spine_gate_trace: dict[str, Any] | None = None,
    expander_continuation_spine_gate_trace: dict[str, Any] | None = None,
    scout_continuation_spine_gate_trace: dict[str, Any] | None = None,
    logger: Any | None = None,
) -> RetrievalAuthorityStageResult:
    if (
        evidence_integration_checkpoint_decided
        and source_class_recovery_checkpoint_refresh_allowed(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            active_source_class_recovery_lifecycle=(
                active_source_class_recovery_lifecycle
            ),
        )
    ):
        evidence_integration_checkpoint_decided = False

    if not evidence_integration_checkpoint_decided:
        try:
            snapshot = build_evidence_integration_snapshot_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_recommendation=(
                    source_class_recovery_recommendation
                ),
                active_source_class_recovery_lifecycle=(
                    active_source_class_recovery_lifecycle
                ),
                strategy=strategy,
                is_sufficient=is_sufficient,
                corpus_weak=corpus_weak,
                corpus_state=corpus_state,
                weak_corpus_recovery_used=weak_corpus_recovery_used,
                weak_corpus_recovery_attempted=weak_corpus_recovery_attempted,
                weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                iterations_run=iterations_run,
                max_iterations=max_iterations,
            )
            decision = decide_evidence_integration_checkpoint(snapshot)
            evidence_integration_checkpoint_trace = (
                build_evidence_integration_checkpoint_trace(
                    snapshot=snapshot,
                    decision=decision,
                    legacy_runtime_branch="existing_source_class_lifecycle",
                )
            )
            evidence_integration_checkpoint_handoff = (
                decision.to_handoff_reference()
            )
            evidence_integration_checkpoint_decided = True
        except Exception as exc:
            _warn(
                logger,
                "Non-fatal evidence-integration checkpoint omitted: %s",
                exc,
            )
            evidence_integration_checkpoint_trace = (
                evidence_integration_checkpoint_unavailable_trace(
                    "checkpoint_exception"
                )
            )
            if (
                source_class_recovery_action_approved(
                    active_source_class_recovery_lifecycle
                )
                and getattr(answer_contract_result, "adapter_result", None)
                is not None
            ):
                evidence_integration_checkpoint_trace[
                    "official_canonical_checkpoint_exception_fallback_allowed"
                ] = True
                evidence_integration_checkpoint_trace[
                    "official_canonical_checkpoint_exception_fallback_source"
                ] = "authoritative_source_action_handoff"
            evidence_integration_checkpoint_handoff = {}
            evidence_integration_checkpoint_decided = True

    ordinary_continuation_candidate_trace = (
        build_ordinary_continuation_trace_projection(
            existing_candidate_trace=ordinary_continuation_candidate_trace,
            evidence_state=(
                getattr(
                    getattr(answer_contract_result, "state", None),
                    "evidence_state_summary",
                    None,
                )
            ),
            compact_runtime_strings_fn=compact_runtime_strings,
            conflict_resolving_queries=conflict_resolving_queries,
            current_iteration=iterations_run,
            max_iterations=max_iterations,
        )
    )
    conflict_lifecycle_trace = conflict_resolution_lifecycle_facts(
        decision=conflict_resolution_decision,
        lifecycle_trace=active_conflict_resolution_lifecycle,
    )
    controller_loop_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            source_class_lifecycle_trace=active_source_class_recovery_lifecycle,
            weak_corpus_lifecycle_trace=weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=conflict_lifecycle_trace,
            ordinary_continuation_candidate_trace=(
                ordinary_continuation_candidate_trace
            ),
        ),
    )
    evidence_integration_checkpoint_trace = controller_loop_spine_result.trace_packet
    try:
        targeted_retrieval_lifecycle_trace = (
            build_targeted_retrieval_lifecycle_from_runtime(
                answer_contract_result=answer_contract_result,
                source_class_recovery_telemetry=(
                    source_class_recovery_recommendation
                ),
                active_source_class_recovery_lifecycle=(
                    active_source_class_recovery_lifecycle
                ),
                weak_corpus_lifecycle_trace=weak_corpus_lifecycle_trace,
                active_conflict_resolution_lifecycle=(
                    active_conflict_resolution_lifecycle
                ),
                retrieval_stop_shadow_telemetry=retrieval_stop_shadow_telemetry,
                retrieval_stop_active_telemetry=retrieval_stop_active_telemetry,
                controller_loop_spine_result=controller_loop_spine_result,
                ordinary_continuation_candidate_trace=(
                    ordinary_continuation_candidate_trace
                ),
                max_iterations=max_iterations,
            )
        )
    except Exception as exc:
        _warn(
            logger,
            "Non-fatal targeted-retrieval passive lifecycle omitted: %s",
            exc,
        )
        targeted_retrieval_lifecycle_trace = targeted_retrieval_lifecycle_defaults()

    controller_loop_spine_result = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            source_class_lifecycle_trace=active_source_class_recovery_lifecycle,
            weak_corpus_lifecycle_trace=weak_corpus_lifecycle_trace,
            conflict_resolution_lifecycle_trace=conflict_lifecycle_trace,
            ordinary_continuation_candidate_trace=(
                ordinary_continuation_candidate_trace
            ),
            targeted_retrieval_lifecycle_trace=targeted_retrieval_lifecycle_trace,
        ),
    )
    evidence_integration_checkpoint_trace = controller_loop_spine_result.trace_packet
    targeted_gate_trace = _authorized_targeted_gate_trace(
        retrieval_batch_dispatch_trace=retrieval_batch_dispatch_trace or {},
        evaluator_continuation_spine_gate_trace=(
            evaluator_continuation_spine_gate_trace or {}
        ),
        expander_continuation_spine_gate_trace=(
            expander_continuation_spine_gate_trace or {}
        ),
        scout_continuation_spine_gate_trace=scout_continuation_spine_gate_trace
        or {},
    )
    if targeted_gate_trace is not None:
        (
            evidence_integration_checkpoint_trace,
            ordinary_continuation_candidate_trace,
            targeted_retrieval_lifecycle_trace,
        ) = reconcile_retrieval_dispatch_runtime_checkpoint_trace(
            checkpoint_trace=evidence_integration_checkpoint_trace,
            ordinary_continuation_candidate_trace=ordinary_continuation_candidate_trace,
            targeted_retrieval_lifecycle_trace=targeted_retrieval_lifecycle_trace,
            authorized_gate_trace=targeted_gate_trace,
        )
        evidence_integration_checkpoint_trace[
            "expander_continuation_spine_gate_trace"
        ] = dict(expander_continuation_spine_gate_trace or {})
        evidence_integration_checkpoint_trace[
            "evaluator_continuation_spine_gate_trace"
        ] = dict(evaluator_continuation_spine_gate_trace or {})
        evidence_integration_checkpoint_trace[
            "scout_continuation_spine_gate_trace"
        ] = dict(scout_continuation_spine_gate_trace or {})
        evidence_integration_checkpoint_trace[
            "authorized_continuation_spine_gate_trace"
        ] = dict(targeted_gate_trace)
    if (retrieval_batch_dispatch_trace or {}).get("considered"):
        evidence_integration_checkpoint_trace[RETRIEVAL_BATCH_DISPATCH_TRACE_KEY] = (
            dict(retrieval_batch_dispatch_trace or {})
        )

    return RetrievalAuthorityStageResult(
        evidence_integration_checkpoint_trace=evidence_integration_checkpoint_trace,
        evidence_integration_checkpoint_handoff=evidence_integration_checkpoint_handoff,
        evidence_integration_checkpoint_decided=evidence_integration_checkpoint_decided,
        ordinary_continuation_candidate_trace=ordinary_continuation_candidate_trace,
        targeted_retrieval_lifecycle_trace=targeted_retrieval_lifecycle_trace,
        authorized_spine_action=(
            controller_loop_spine_result.dispatch_authorization.authorized_action_name
        ),
    )


def _authorized_targeted_gate_trace(
    *,
    retrieval_batch_dispatch_trace: dict[str, Any],
    evaluator_continuation_spine_gate_trace: dict[str, Any],
    expander_continuation_spine_gate_trace: dict[str, Any],
    scout_continuation_spine_gate_trace: dict[str, Any],
) -> dict[str, Any] | None:
    if not retrieval_batch_dispatch_trace.get("dispatch_authorized"):
        return None
    if scout_continuation_spine_gate_trace.get(
        "targeted_retrieval_dispatch_authorized"
    ):
        return scout_continuation_spine_gate_trace
    if expander_continuation_spine_gate_trace.get(
        "targeted_retrieval_dispatch_authorized"
    ):
        return expander_continuation_spine_gate_trace
    if evaluator_continuation_spine_gate_trace.get(
        "targeted_retrieval_dispatch_authorized"
    ):
        return evaluator_continuation_spine_gate_trace
    return None


def _warn(logger: Any | None, message: str, *args: Any) -> None:
    if logger is not None and hasattr(logger, "warning"):
        logger.warning(message, *args)
