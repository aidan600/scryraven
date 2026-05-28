"""Observer-facing diagnostics/projection handoff for source-class recovery.

The helpers here gather facts already produced by source-class recovery and
final evidence packaging. They do not decide recovery posture, source
sufficiency, final evidence, Author behavior, or citation behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.source_class_recovery import build_recovery_source_quality_diagnostics
from core.source_class_recovery_candidate_stream import (
    source_class_recovery_passage_candidates,
)


@dataclass(frozen=True)
class SourceClassRecoveryProjectionHandoff:
    """Recovered/source-class facts for diagnostics and passive projections."""

    recovered_source_class_passages: list[Mapping[str, Any]]
    recovery_source_quality_diagnostics: dict[str, Any]


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


__all__ = [
    "SourceClassRecoveryProjectionHandoff",
    "build_source_class_recovery_projection_handoff",
]
