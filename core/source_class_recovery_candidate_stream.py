"""Runner-owned recovered/source-class candidate stream assembly.

This module mechanically assembles candidates already produced by source-class
recovery execution or Controller-authorized allocation custody. It does not
classify, fit, select final evidence, prompt, cite, retrieve, or route providers.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from core.allocation_candidate_selection_activation import (
    allocation_result_candidates_for_existing_selection_corridor,
)

SOURCE_CLASS_RECOVERY_RETRIEVAL_STAGE = "source_class_recovery"

SourceClassStagePredicate = Callable[[Mapping[str, Any]], bool]
AllocationCandidateSource = Callable[[Mapping[str, Any] | None], list[dict[str, Any]]]


def is_source_class_recovery_passage(
    passage: Mapping[str, Any],
    *,
    retrieval_stage: str = SOURCE_CLASS_RECOVERY_RETRIEVAL_STAGE,
) -> bool:
    """Return whether a passage belongs to the source-class recovery stage."""

    return passage.get("retrieval_stage") == retrieval_stage


def source_class_recovery_passage_candidates(
    *,
    all_passages: Iterable[Mapping[str, Any]] | None,
    stage_predicate: SourceClassStagePredicate | None = None,
) -> list[Mapping[str, Any]]:
    """Return source-class recovery passage candidates in existing order."""

    predicate = stage_predicate or is_source_class_recovery_passage
    return [
        passage
        for passage in all_passages or ()
        if isinstance(passage, Mapping) and predicate(passage)
    ]


def runner_owned_recovered_candidate_stream(
    *,
    all_passages: Iterable[Mapping[str, Any]] | None,
    lifecycle_trace: Mapping[str, Any] | None,
    allocation_candidate_source: AllocationCandidateSource | None = (
        allocation_result_candidates_for_existing_selection_corridor
    ),
    stage_predicate: SourceClassStagePredicate | None = None,
) -> list[Mapping[str, Any]]:
    """Return recovered/source-class candidates for existing selection.

    Source-class recovery passage records are preserved first, followed by
    Controller-authorized allocation candidates from the existing custody
    corridor.
    """

    candidates = source_class_recovery_passage_candidates(
        all_passages=all_passages,
        stage_predicate=stage_predicate,
    )
    if allocation_candidate_source is not None:
        candidates.extend(allocation_candidate_source(lifecycle_trace))
    return candidates


__all__ = [
    "SOURCE_CLASS_RECOVERY_RETRIEVAL_STAGE",
    "is_source_class_recovery_passage",
    "runner_owned_recovered_candidate_stream",
    "source_class_recovery_passage_candidates",
]
