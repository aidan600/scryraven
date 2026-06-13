"""Observer-facing diagnostics/projection handoff for source-class recovery.

The helpers here gather facts already produced by source-class recovery and
final evidence packaging. They do not decide recovery posture, source
sufficiency, final evidence, Author behavior, or citation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.final_evidence_bundle_builder import (
    FinalEvidenceBundle,
    post_final_source_class_handoff_from_final_evidence_bundle,
)
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)
from core.source_class_authority_runtime_adapter import (
    source_class_recovery_authority_blocker_reasons,
)
from core.source_class_recovery import (
    build_recovery_source_quality_diagnostics,
    build_source_class_observability_telemetry,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_candidate_stream import (
    source_class_recovery_passage_candidates,
)
from core.source_classifier import source_domain_telemetry, source_tier_telemetry


@dataclass(frozen=True)
class SourceClassRecoveryProjectionHandoff:
    """Recovered/source-class facts for diagnostics and passive projections."""

    recovered_source_class_passages: list[Mapping[str, Any]]
    recovery_source_quality_diagnostics: dict[str, Any]


@dataclass(frozen=True)
class PostFinalSourceClassProjectionHandoff:
    """Post-final source-class telemetry for observer/reducer consumers."""

    source_tier_exec: dict[str, Any]
    source_domain_exec: dict[str, Any]
    source_class_recovery_telemetry: dict[str, Any]
    source_class_evidence_bundle_observability_telemetry: dict[str, Any]
    source_class_observability_telemetry: dict[str, Any]
    official_source_obligation_bridge_trace: dict[str, Any]
    source_class_projection_handoff: SourceClassRecoveryProjectionHandoff
    runtime_source_class_recovery_telemetry: dict[str, Any]
    runtime_active_source_class_recovery_lifecycle: dict[str, Any]


@dataclass(frozen=True)
class PostFinalSourceClassRuntimeProjection:
    """Post-final projection values plus reduced EvidenceLedger projection."""

    handoff: PostFinalSourceClassProjectionHandoff
    evidence_ledger_projection: dict[str, Any]


def build_source_class_recovery_projection_handoff(
    *,
    all_passages: Iterable[Mapping[str, Any]] | None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    final_source_class_counts: Mapping[str, Any] | None = None,
) -> SourceClassRecoveryProjectionHandoff:
    """Build the diagnostics/projection handoff without altering behavior."""

    recovered_source_class_passages = source_class_recovery_passage_candidates(
        all_passages=all_passages,
    )
    recovery_source_quality_diagnostics: dict[str, Any] = {}
    if recovered_source_class_passages:
        recovery_source_quality_diagnostics = build_recovery_source_quality_diagnostics(
            recovered_source_class_passages,
            final_top_evidence=final_top_evidence,
            final_source_class_counts=final_source_class_counts,
        )
    return SourceClassRecoveryProjectionHandoff(
        recovered_source_class_passages=recovered_source_class_passages,
        recovery_source_quality_diagnostics=recovery_source_quality_diagnostics,
    )


def build_post_final_source_class_projection_handoff(
    *,
    all_passages: Iterable[Mapping[str, Any]],
    final_evidence_bundle: FinalEvidenceBundle,
    final_answer_source_ids: Iterable[Any] | None,
    query: str,
    current_date: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet: Mapping[str, Any],
    active_source_class_recovery_lifecycle: Mapping[str, Any],
    logger: Any | None = None,
) -> PostFinalSourceClassProjectionHandoff:
    """Build post-final source-class observer state from canonical/bundle inputs."""

    source_tier_exec = source_tier_telemetry(all_passages)
    source_domain_exec = source_domain_telemetry(
        all_passages,
        domain_anchor=primary_entity or core_topic,
    )
    source_class_recovery_telemetry = build_source_class_recovery_recommendation(
        query=query,
        current_date=current_date,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet,
        source_tier_counts=source_tier_exec["source_tier_counts"],
        source_domain_counts=source_domain_exec["source_domain_counts"],
        top_source_domains=source_domain_exec["top_source_domains"],
        official_evidence_found=source_tier_exec["official_evidence_found"],
    )
    source_class_evidence_bundle_observability_telemetry = (
        build_source_class_observability_telemetry(
            query=query,
            intent=intent,
            report_type=report_type,
            query_type=query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            anchor_packet=anchor_packet,
            final_top_evidence=final_evidence_bundle.final_top_evidence,
            final_answer_source_ids=None,
        )
    )
    source_class_observability_telemetry = build_source_class_observability_telemetry(
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet,
        final_top_evidence=final_evidence_bundle.final_top_evidence,
        final_answer_source_ids=final_answer_source_ids,
    )
    official_source_obligation_bridge_trace: dict[str, Any] = {}
    try:
        bridge_result = apply_official_source_obligation_bridge(
            recommendation=source_class_recovery_telemetry,
            runtime_trace={
                "query_preview": (query or "")[:200],
                "intent": intent,
                "query_type": query_type,
                "report_type": report_type,
                **source_class_recovery_telemetry,
                **source_class_observability_telemetry,
            },
            existing_blockers=source_class_recovery_authority_blocker_reasons(
                active_source_class_recovery_lifecycle
            ),
        )
        source_class_recovery_telemetry = bridge_result.recommendation
        official_source_obligation_bridge_trace = bridge_result.trace
    except Exception as exc:
        if logger is not None:
            logger.warning(
                "Non-fatal official-source obligation bridge omitted: %s",
                exc,
            )
    source_class_projection_handoff = build_source_class_recovery_projection_handoff(
        all_passages=all_passages,
        final_top_evidence=final_evidence_bundle.final_top_evidence,
        final_source_class_counts=source_class_observability_telemetry.get(
            "source_class_strong_satisfaction_counts"
        ),
    )
    runtime_lifecycle = dict(active_source_class_recovery_lifecycle)
    if source_class_projection_handoff.recovery_source_quality_diagnostics:
        runtime_lifecycle.update(
            source_class_projection_handoff.recovery_source_quality_diagnostics
        )
    post_final = post_final_source_class_handoff_from_final_evidence_bundle(
        final_evidence_bundle,
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        source_class_observability_telemetry=source_class_observability_telemetry,
        active_source_class_recovery_lifecycle=runtime_lifecycle,
    )
    return PostFinalSourceClassProjectionHandoff(
        source_tier_exec=source_tier_exec,
        source_domain_exec=source_domain_exec,
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        source_class_evidence_bundle_observability_telemetry=(
            source_class_evidence_bundle_observability_telemetry
        ),
        source_class_observability_telemetry=source_class_observability_telemetry,
        official_source_obligation_bridge_trace=official_source_obligation_bridge_trace,
        source_class_projection_handoff=source_class_projection_handoff,
        runtime_source_class_recovery_telemetry=(
            post_final.source_class_recovery_telemetry
        ),
        runtime_active_source_class_recovery_lifecycle=(
            post_final.active_source_class_recovery_lifecycle
        ),
    )


def execute_post_final_source_class_projection_from_scope(
    runtime_scope: Mapping[str, Any],
    *,
    logger: Any | None = None,
    recommendation_recorder: Any,
) -> PostFinalSourceClassRuntimeProjection:
    """Build post-final projection, mirror it, and reduce observer facts."""

    from core.evidence_ledger_lifecycle import (
        reduce_post_final_source_obligations_into_evidence_ledger,
    )

    handoff = build_post_final_source_class_projection_handoff(
        all_passages=runtime_scope["all_passages"],
        final_evidence_bundle=runtime_scope["final_evidence_bundle"],
        final_answer_source_ids=runtime_scope["final_answer_source_telemetry"].get(
            "final_answer_source_ids_used"
        ),
        query=runtime_scope["query"],
        current_date=runtime_scope["current_date"],
        intent=runtime_scope["intent"],
        report_type=runtime_scope["report_type"],
        query_type=runtime_scope["query_type"],
        core_topic=runtime_scope["core_topic"],
        primary_entity=runtime_scope["primary_entity"],
        anchor_packet=runtime_scope["anchor_packet_telemetry"],
        active_source_class_recovery_lifecycle=runtime_scope[
            "active_source_class_recovery_lifecycle"
        ],
        logger=logger,
    )
    runtime_scope["active_source_class_recovery_lifecycle"].update(
        handoff.source_class_projection_handoff.recovery_source_quality_diagnostics
    )
    source_tier_exec = handoff.source_tier_exec
    source_domain_exec = handoff.source_domain_exec
    recommendation_recorder(
        runtime_scope["_run_controller_mirror"],
        source_class_recovery_telemetry=handoff.source_class_recovery_telemetry,
        source_class_evidence_signals={
            "source_tier_counts": source_tier_exec["source_tier_counts"],
            "source_domain_counts": source_domain_exec["source_domain_counts"],
            "top_source_domains": source_domain_exec["top_source_domains"],
            "unique_source_domain_count": source_domain_exec["unique_source_domain_count"],
            "on_domain_source_count": source_domain_exec["on_domain_source_count"],
            "off_domain_source_count": source_domain_exec["off_domain_source_count"],
            "official_evidence_found": source_tier_exec["official_evidence_found"],
            "community_signal_found": source_tier_exec["community_signal_found"],
            "low_trust_sources_found": source_tier_exec["low_trust_sources_found"],
            "pollution_detected": source_tier_exec["pollution_detected"],
        },
    )
    evidence_ledger_projection = reduce_post_final_source_obligations_into_evidence_ledger(
        run_kernel=runtime_scope["run_kernel"],
        run_id=runtime_scope["run_id"],
        source_class_recovery_telemetry={
            **handoff.runtime_source_class_recovery_telemetry,
            **handoff.source_class_observability_telemetry,
        },
        final_top_evidence=runtime_scope["final_top_evidence"],
    )
    return PostFinalSourceClassRuntimeProjection(
        handoff=handoff,
        evidence_ledger_projection=evidence_ledger_projection,
    )


__all__ = [
    "PostFinalSourceClassProjectionHandoff",
    "PostFinalSourceClassRuntimeProjection",
    "SourceClassRecoveryProjectionHandoff",
    "build_post_final_source_class_projection_handoff",
    "execute_post_final_source_class_projection_from_scope",
    "build_source_class_recovery_projection_handoff",
]
