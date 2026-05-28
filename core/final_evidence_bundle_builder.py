"""Mechanical final evidence bundle assembly helpers.

This module preserves the final evidence/source-ID packaging previously built
inline by ``pipeline_orchestrator.py``. It does not select providers, retrieve,
classify, prompt, or choose citation behavior.
"""

from __future__ import annotations

from collections.abc import (
    Callable,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
)
from dataclasses import dataclass, field
from typing import Any

Passage = MutableMapping[str, Any]
FilterTopEvidence = Callable[[MutableSequence[Passage], int, int], list[Passage]]
PlausibleDomainPredicate = Callable[[str], bool]
RecoveredEvidenceVisibility = Callable[..., list[Passage]]


@dataclass(slots=True)
class FinalEvidenceSourceIdentity:
    """Stable URL-to-source-ID assignment output."""

    unique_source_urls: dict[str, int]
    ordered_sources: list[str]


@dataclass(slots=True)
class FinalEvidenceSourceTelemetry:
    """Observer input package for final source telemetry and snapshots."""

    source_ids: list[Any]
    unique_source_url_count: int
    ordered_sources: list[str]
    final_evidence_count: int
    final_answer_source_telemetry: dict[str, Any] = field(default_factory=dict)
    final_evidence_snapshot_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FinalEvidenceBundle:
    """Mechanical final evidence bundle consumed by the orchestrator."""

    final_top_evidence: list[Passage]
    unique_source_urls: dict[str, int]
    ordered_sources: list[str]
    evidence_block: str
    cached_prefix: str
    author_evidence: list[Passage] = field(default_factory=list)
    author_evidence_block: str = ""
    final_source_telemetry: FinalEvidenceSourceTelemetry | None = None


@dataclass(slots=True)
class FinalEvidenceBundleInputs:
    """Inputs for rebuilding the final evidence bundle without policy decisions."""

    all_passages: MutableSequence[Passage]
    top_chunks: int
    max_domain_chunks: int
    filter_top_evidence: FilterTopEvidence
    is_plausible_domain: PlausibleDomainPredicate
    current_date: str
    query: str
    active_source_class_recovery_lifecycle: Mapping[str, Any] | None = None
    recovered_evidence_visibility: RecoveredEvidenceVisibility | None = None
    reserve_limit: int = 1


def assign_stable_source_ids(
    final_top_evidence: Iterable[Passage],
    *,
    is_plausible_domain: PlausibleDomainPredicate,
) -> FinalEvidenceSourceIdentity:
    """Assign source IDs by first URL occurrence, preserving prior formatting."""
    unique_source_urls: dict[str, int] = {}
    ordered_sources: list[str] = []
    next_source_id = 1

    for passage in final_top_evidence:
        url = passage["url"]
        if url not in unique_source_urls:
            unique_source_urls[url] = next_source_id
            if is_plausible_domain(url):
                ordered_sources.append(
                    f"- [{next_source_id}] [{passage['title']}]({url})"
                )
            next_source_id += 1
        passage["source_id"] = unique_source_urls[url]

    return FinalEvidenceSourceIdentity(
        unique_source_urls=unique_source_urls,
        ordered_sources=ordered_sources,
    )


def build_ordered_sources(
    final_top_evidence: Iterable[Passage],
    *,
    is_plausible_domain: PlausibleDomainPredicate,
) -> list[str]:
    """Return ordered Sources-list lines after assigning stable source IDs."""
    return assign_stable_source_ids(
        final_top_evidence,
        is_plausible_domain=is_plausible_domain,
    ).ordered_sources


def build_evidence_block(final_top_evidence: Iterable[Mapping[str, Any]]) -> str:
    """Build the exact final evidence block text consumed by prompts."""
    return "\n\n".join(
        f"[Source {p['source_id']}] {p['title']}\nURL: {p['url']}\nExcerpt: {p['text'][:1200]}"
        for p in final_top_evidence
    )


def build_cached_prefix(
    *,
    evidence_block: str,
    current_date: str,
    query: str,
) -> str:
    """Build the exact cached prefix seed text."""
    return (
        f"<evidence_block>\n{evidence_block}\n</evidence_block>\n\n"
        f"Today is {current_date}.\nUser's Original Prompt: {query}\n"
    )


def slice_author_evidence(
    final_top_evidence: list[Passage],
    precision_count: int,
) -> list[Passage]:
    """Return the Author precision evidence slice."""
    return final_top_evidence[:precision_count]


def build_author_evidence_block(
    author_evidence: Iterable[Mapping[str, Any]],
) -> str:
    """Build the exact Author precision evidence block text."""
    return build_evidence_block(author_evidence)


def attach_author_evidence(
    bundle: FinalEvidenceBundle,
    *,
    precision_count: int,
) -> FinalEvidenceBundle:
    """Package Author evidence on an already-built final evidence bundle."""
    author_evidence = slice_author_evidence(bundle.final_top_evidence, precision_count)
    bundle.author_evidence = author_evidence
    bundle.author_evidence_block = build_author_evidence_block(author_evidence)
    return bundle


def build_final_source_telemetry_inputs(
    *,
    final_top_evidence: list[Passage],
    unique_source_urls: Mapping[str, int],
    ordered_sources: Iterable[str],
    seen_urls: Iterable[str] | None = None,
    collected_images: Iterable[str] | None = None,
    final_answer_source_telemetry: Mapping[str, Any] | None = None,
) -> FinalEvidenceSourceTelemetry:
    """Package final source observer inputs without changing their values."""
    snapshot_payload: dict[str, Any] = {}
    if seen_urls is not None or collected_images is not None:
        snapshot_payload = {
            "final_top_evidence": final_top_evidence,
            "seen_urls": list(seen_urls or []),
            "collected_images": list(collected_images or []),
        }

    return FinalEvidenceSourceTelemetry(
        source_ids=[
            passage["source_id"]
            for passage in final_top_evidence
            if "source_id" in passage
        ],
        unique_source_url_count=len(unique_source_urls),
        ordered_sources=list(ordered_sources),
        final_evidence_count=len(final_top_evidence),
        final_answer_source_telemetry=dict(final_answer_source_telemetry or {}),
        final_evidence_snapshot_payload=snapshot_payload,
    )


def build_final_evidence_bundle(
    inputs: FinalEvidenceBundleInputs,
    *,
    linkup_block: str = "",
) -> FinalEvidenceBundle:
    """Build final evidence, source IDs, source lines, and prompt blocks."""
    inputs.all_passages.sort(key=lambda x: x.get("score", 0), reverse=True)
    final_top_evidence = inputs.filter_top_evidence(
        inputs.all_passages,
        inputs.top_chunks,
        inputs.max_domain_chunks,
    )
    if inputs.recovered_evidence_visibility is not None:
        final_top_evidence = inputs.recovered_evidence_visibility(
            final_top_evidence=final_top_evidence,
            all_passages=inputs.all_passages,
            lifecycle_trace=inputs.active_source_class_recovery_lifecycle,
            max_final_evidence=inputs.top_chunks,
            reserve_limit=inputs.reserve_limit,
        )

    source_identity = assign_stable_source_ids(
        final_top_evidence,
        is_plausible_domain=inputs.is_plausible_domain,
    )
    evidence_block = build_evidence_block(final_top_evidence)
    cached_prefix = build_cached_prefix(
        evidence_block=evidence_block,
        current_date=inputs.current_date,
        query=inputs.query,
    )
    if linkup_block:
        cached_prefix += linkup_block

    return FinalEvidenceBundle(
        final_top_evidence=final_top_evidence,
        unique_source_urls=source_identity.unique_source_urls,
        ordered_sources=source_identity.ordered_sources,
        evidence_block=evidence_block,
        cached_prefix=cached_prefix,
        final_source_telemetry=build_final_source_telemetry_inputs(
            final_top_evidence=final_top_evidence,
            unique_source_urls=source_identity.unique_source_urls,
            ordered_sources=source_identity.ordered_sources,
        ),
    )


__all__ = [
    "FinalEvidenceBundle",
    "FinalEvidenceBundleInputs",
    "FinalEvidenceSourceIdentity",
    "FinalEvidenceSourceTelemetry",
    "assign_stable_source_ids",
    "attach_author_evidence",
    "build_author_evidence_block",
    "build_cached_prefix",
    "build_evidence_block",
    "build_final_evidence_bundle",
    "build_final_source_telemetry_inputs",
    "build_ordered_sources",
    "slice_author_evidence",
]
