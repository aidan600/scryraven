"""Passive EvidenceRegistry mirror for final orchestrator evidence snapshots.

This helper records already-final pipeline evidence into RunController.evidence.
It does not select, rank, retrieve, route, prompt, call providers, or assemble
persisted telemetry.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from core.run_controller import RunController


def _snapshot_passages(
    passages: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    return [deepcopy(dict(passage)) for passage in (passages or [])]


def _snapshot_sequence(values: Iterable[Any] | None) -> list[Any]:
    if values is None:
        return []
    return deepcopy(list(values))


def _source_ids_already_on_passages(passages: Iterable[Mapping[str, Any]]) -> list[Any]:
    return [
        deepcopy(passage["source_id"])
        for passage in passages
        if "source_id" in passage
    ]


def record_final_evidence_snapshot(
    controller: RunController,
    *,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
    seen_urls: Iterable[str] | None,
    collected_images: Iterable[str] | None,
) -> RunController:
    """Mirror already-final evidence into the passive EvidenceRegistry."""
    passage_snapshot = _snapshot_passages(final_top_evidence)

    controller.evidence.passages = _snapshot_sequence(passage_snapshot)
    controller.evidence.seen_urls = _snapshot_sequence(seen_urls)
    controller.evidence.collected_images = _snapshot_sequence(collected_images)
    controller.evidence.source_ids = _source_ids_already_on_passages(
        passage_snapshot
    )
    return controller


__all__ = ["record_final_evidence_snapshot"]
