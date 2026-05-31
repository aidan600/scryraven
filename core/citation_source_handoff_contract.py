"""Controller-owned citation/source-list handoff contract.

This module is deliberately passive and deterministic. It receives citation and
source-list facts already computed by the runtime/final evidence bundle builder,
copies their identities into Controller-owned state, and returns a mechanical
legacy-compatible handoff envelope. It does not assign source IDs, format
citations, select citations, build Author prompt text, call providers, retrieve,
persist sessions, or change final-answer behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

CITATION_SOURCE_HANDOFF_SCHEMA_VERSION = "AG76D-CIT.v1"
CITATION_SOURCE_HANDOFF_TRACE_KEY = "citation_source_handoff_contract"


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any] | None) -> tuple[Any, ...]:
    return tuple(deepcopy(list(value or ())))


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _hash_lines(lines: Sequence[Any] | None) -> str:
    return _hash_text("\n".join(str(line) for line in (lines or ())))


def _domain_from_url(url: Any) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    without_scheme = text.split("://", 1)[-1]
    domain = without_scheme.split("/", 1)[0].split("?", 1)[0].strip().lower()
    return domain or None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _evidence_identity(
    evidence: Sequence[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], ...]:
    identity: list[dict[str, Any]] = []
    for index, passage in enumerate(evidence or (), 1):
        source_id = passage.get("source_id")
        url = passage.get("url")
        text = str(passage.get("text") or "")
        identity.append(
            {
                "position": index,
                "source_id": source_id,
                "url": url,
                "title": passage.get("title"),
                "domain": _domain_from_url(url),
                "text_hash": _hash_text(text) if text else None,
                "text_length": len(text),
                "source_tier": passage.get("source_tier"),
                "source_class": passage.get("source_class"),
            }
        )
    return tuple(identity)


def _source_id_mapping(
    *,
    final_evidence: Sequence[Mapping[str, Any]] | None,
    unique_source_urls: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    first_seen: dict[str, Mapping[str, Any]] = {}
    for passage in final_evidence or ():
        url = str(passage.get("url") or "")
        if url and url not in first_seen:
            first_seen[url] = passage

    rows: list[dict[str, Any]] = []
    for url, source_id in sorted(
        _copy_mapping(unique_source_urls).items(),
        key=lambda item: (_safe_int(item[1]) is None, _safe_int(item[1]) or 0, str(item[0])),
    ):
        passage = first_seen.get(str(url), {})
        rows.append(
            {
                "source_id": source_id,
                "url": url,
                "title": passage.get("title"),
                "domain": _domain_from_url(url),
                "first_final_evidence_position": (
                    next(
                        (
                            idx
                            for idx, item in enumerate(final_evidence or (), 1)
                            if str(item.get("url") or "") == str(url)
                        ),
                        None,
                    )
                ),
            }
        )
    return tuple(rows)


def _duplicate_reuse_facts(
    final_evidence: Sequence[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], ...]:
    by_url: dict[str, dict[str, Any]] = {}
    for index, passage in enumerate(final_evidence or (), 1):
        url = str(passage.get("url") or "")
        if not url:
            continue
        bucket = by_url.setdefault(
            url,
            {
                "url": url,
                "source_id": passage.get("source_id"),
                "positions": [],
                "duplicate_count": 0,
            },
        )
        bucket["positions"].append(index)
        if bucket.get("source_id") is None:
            bucket["source_id"] = passage.get("source_id")
    facts: list[dict[str, Any]] = []
    for bucket in by_url.values():
        positions = list(bucket["positions"])
        if len(positions) <= 1:
            continue
        facts.append(
            {
                "url": bucket["url"],
                "source_id": bucket["source_id"],
                "positions": positions,
                "duplicate_count": len(positions) - 1,
                "source_id_reused": True,
            }
        )
    return tuple(facts)


def _state_ref(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _copy_mapping(value)
    if hasattr(value, "to_controller_state"):
        return _copy_mapping(value.to_controller_state())
    if hasattr(value, "to_trace_fragment"):
        fragment = value.to_trace_fragment()
        if isinstance(fragment, Mapping):
            if len(fragment) == 1:
                only = next(iter(fragment.values()))
                if isinstance(only, Mapping):
                    return _copy_mapping(only)
            return _copy_mapping(fragment)
    if hasattr(value, "execution_trace_fragment"):
        fragment = value.execution_trace_fragment()
        return _copy_mapping(fragment if isinstance(fragment, Mapping) else {})
    return {"ref_type": type(value).__name__}


@dataclass(frozen=True)
class SourceIdentityDescriptor:
    """Identity of final source references exposed to citation/source-list surfaces."""

    source_identity: tuple[dict[str, Any], ...]
    source_id_mapping: tuple[dict[str, Any], ...]
    duplicate_url_reuse_facts: tuple[dict[str, Any], ...]
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "source_count": len(self.source_identity),
            "source_identity": deepcopy(list(self.source_identity)),
            "source_id_mapping": deepcopy(list(self.source_id_mapping)),
            "duplicate_url_reuse_facts": deepcopy(list(self.duplicate_url_reuse_facts)),
            "source_id_assignment_included": False,
            "source_id_reuse_behavior_changed": False,
        }


@dataclass(frozen=True)
class OrderedSourceListDescriptor:
    """Identity of already-built ordered Sources-list lines."""

    ordered_sources: tuple[Any, ...]
    ordered_source_hash: str
    ordered_source_count: int
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "ordered_sources": deepcopy(list(self.ordered_sources)),
            "ordered_source_hash": self.ordered_source_hash,
            "ordered_source_count": int(self.ordered_source_count),
            "source_list_formatting_included": False,
            "source_ordering_behavior_changed": False,
        }


@dataclass(frozen=True)
class CitationEligibilityDescriptor:
    """Citation-eligible source references copied from final/Author evidence."""

    final_evidence_refs: tuple[dict[str, Any], ...]
    selected_evidence_refs: tuple[dict[str, Any], ...]
    author_evidence_refs: tuple[dict[str, Any], ...]
    citation_eligible_source_ids: tuple[Any, ...]
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "final_evidence_refs": deepcopy(list(self.final_evidence_refs)),
            "selected_evidence_refs": deepcopy(list(self.selected_evidence_refs)),
            "author_evidence_refs": deepcopy(list(self.author_evidence_refs)),
            "citation_eligible_source_ids": deepcopy(list(self.citation_eligible_source_ids)),
            "citation_selection_included": False,
        }


@dataclass(frozen=True)
class CitationObservationDescriptor:
    """Final citation observations already computed by the runtime."""

    final_answer_source_telemetry: dict[str, Any] = field(default_factory=dict)
    final_citation_observation_refs: tuple[Any, ...] = ()
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "final_answer_source_telemetry": deepcopy(self.final_answer_source_telemetry),
            "final_citation_observation_refs": deepcopy(
                list(self.final_citation_observation_refs)
            ),
            "final_citation_observation_count": len(self.final_citation_observation_refs),
            "final_answer_citation_observation_included": True,
            "citation_formatting_included": False,
        }


@dataclass(frozen=True)
class AuthorSourceInputDescriptor:
    """Identity of Author evidence/source inputs without prompt text."""

    evidence_block_hash: str | None = None
    evidence_block_length: int | None = None
    cached_prefix_hash: str | None = None
    cached_prefix_length: int | None = None
    author_evidence_block_hash: str | None = None
    author_evidence_block_length: int | None = None
    author_prompt_input_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "evidence_block_hash": self.evidence_block_hash,
            "evidence_block_length": self.evidence_block_length,
            "cached_prefix_hash": self.cached_prefix_hash,
            "cached_prefix_length": self.cached_prefix_length,
            "author_evidence_block_hash": self.author_evidence_block_hash,
            "author_evidence_block_length": self.author_evidence_block_length,
            "author_prompt_input_ref": deepcopy(self.author_prompt_input_ref),
            "prompt_text_included": False,
            "author_prompt_behavior_changed": False,
        }


@dataclass(frozen=True)
class CitationSourceHandoffState:
    """Controller-owned citation/source-list handoff state."""

    source_identity: SourceIdentityDescriptor
    ordered_source_list: OrderedSourceListDescriptor
    citation_eligibility: CitationEligibilityDescriptor
    citation_observations: CitationObservationDescriptor
    author_source_inputs: AuthorSourceInputDescriptor
    run_id: str | None = None
    final_evidence_bundle_ref: dict[str, Any] = field(default_factory=dict)
    ledger_ref: dict[str, Any] = field(default_factory=dict)
    answer_contract_ref: dict[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: dict[str, Any] = field(default_factory=dict)
    source_telemetry_ref: dict[str, Any] = field(default_factory=dict)
    trace_visibility: dict[str, Any] = field(default_factory=dict)
    schema_version: str = CITATION_SOURCE_HANDOFF_SCHEMA_VERSION
    controller_owned: bool = True

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            CITATION_SOURCE_HANDOFF_TRACE_KEY: {
                "schema_version": self.schema_version,
                "controller_owned": bool(self.controller_owned),
                "run_id": self.run_id,
                "source_identity": self.source_identity.to_trace(),
                "ordered_source_list": self.ordered_source_list.to_trace(),
                "citation_eligibility": self.citation_eligibility.to_trace(),
                "citation_observations": self.citation_observations.to_trace(),
                "author_source_inputs": self.author_source_inputs.to_trace(),
                "final_evidence_bundle_ref": deepcopy(self.final_evidence_bundle_ref),
                "ledger_ref": deepcopy(self.ledger_ref),
                "answer_contract_ref": deepcopy(self.answer_contract_ref),
                "analyst_author_handoff_ref": deepcopy(
                    self.analyst_author_handoff_ref
                ),
                "source_telemetry_ref": deepcopy(self.source_telemetry_ref),
                "trace_visibility": {
                    "additive_only": True,
                    "legacy_trace_fields_preserved": True,
                    "owned_by": "Controller",
                    **deepcopy(self.trace_visibility),
                },
                "did_change_citation_formatting": False,
                "did_change_citation_selection": False,
                "did_change_final_answer_prose": False,
                "did_change_author_behavior": False,
                "did_change_prompt_text": False,
                "did_change_provider_search_query_behavior": False,
                "did_change_db_session_run_outcome_shape": False,
                "did_change_cache_behavior": False,
                "mechanical_executor_boundary": True,
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.to_trace_fragment()[CITATION_SOURCE_HANDOFF_TRACE_KEY])


@dataclass(frozen=True)
class CitationSourceExecutionEnvelope:
    """Legacy-compatible mechanical citation/source-list handoff values."""

    unique_source_urls: dict[str, Any]
    ordered_sources: list[Any]
    final_answer_source_telemetry: dict[str, Any]
    controller_owned: bool = True
    mechanical_handoff_only: bool = True


def build_citation_source_handoff_state(
    *,
    run_id: str | None = None,
    final_evidence: Sequence[Mapping[str, Any]] | None = None,
    selected_evidence: Sequence[Mapping[str, Any]] | None = None,
    author_evidence: Sequence[Mapping[str, Any]] | None = None,
    unique_source_urls: Mapping[str, Any] | None = None,
    ordered_sources: Sequence[Any] | None = None,
    evidence_block: str | None = None,
    cached_prefix: str | None = None,
    author_evidence_block: str | None = None,
    final_answer_source_telemetry: Mapping[str, Any] | None = None,
    final_citation_observation_refs: Sequence[Any] | None = None,
    final_evidence_bundle_ref: Mapping[str, Any] | None = None,
    ledger_ref: Any | None = None,
    answer_contract_ref: Any | None = None,
    analyst_author_handoff_state: Any | None = None,
    source_telemetry_ref: Mapping[str, Any] | None = None,
) -> CitationSourceHandoffState:
    """Build Controller-owned state from already-computed source/citation facts."""

    final_refs = _evidence_identity(final_evidence)
    selected_refs = _evidence_identity(
        selected_evidence if selected_evidence is not None else final_evidence
    )
    author_refs = _evidence_identity(author_evidence)
    citation_source_ids: list[Any] = []
    seen_ids: set[str] = set()
    for ref in final_refs:
        source_id = ref.get("source_id")
        key = str(source_id)
        if source_id is not None and key not in seen_ids:
            citation_source_ids.append(source_id)
            seen_ids.add(key)

    analyst_ref = _state_ref(analyst_author_handoff_state)
    author_prompt_input_ref = _copy_mapping(analyst_ref.get("author_prompt_input", {}))

    return CitationSourceHandoffState(
        run_id=run_id,
        source_identity=SourceIdentityDescriptor(
            source_identity=final_refs,
            source_id_mapping=_source_id_mapping(
                final_evidence=final_evidence,
                unique_source_urls=unique_source_urls,
            ),
            duplicate_url_reuse_facts=_duplicate_reuse_facts(final_evidence),
        ),
        ordered_source_list=OrderedSourceListDescriptor(
            ordered_sources=_copy_sequence(ordered_sources),
            ordered_source_hash=_hash_lines(ordered_sources),
            ordered_source_count=len(ordered_sources or ()),
        ),
        citation_eligibility=CitationEligibilityDescriptor(
            final_evidence_refs=final_refs,
            selected_evidence_refs=selected_refs,
            author_evidence_refs=author_refs,
            citation_eligible_source_ids=tuple(citation_source_ids),
        ),
        citation_observations=CitationObservationDescriptor(
            final_answer_source_telemetry=_copy_mapping(final_answer_source_telemetry),
            final_citation_observation_refs=_copy_sequence(
                final_citation_observation_refs
                if final_citation_observation_refs is not None
                else _copy_mapping(final_answer_source_telemetry).get(
                    "final_answer_source_ids_used",
                    (),
                )
            ),
        ),
        author_source_inputs=AuthorSourceInputDescriptor(
            evidence_block_hash=_hash_text(evidence_block) if evidence_block is not None else None,
            evidence_block_length=len(evidence_block) if evidence_block is not None else None,
            cached_prefix_hash=_hash_text(cached_prefix) if cached_prefix is not None else None,
            cached_prefix_length=len(cached_prefix) if cached_prefix is not None else None,
            author_evidence_block_hash=(
                _hash_text(author_evidence_block)
                if author_evidence_block is not None
                else None
            ),
            author_evidence_block_length=(
                len(author_evidence_block) if author_evidence_block is not None else None
            ),
            author_prompt_input_ref=author_prompt_input_ref,
        ),
        final_evidence_bundle_ref=_copy_mapping(final_evidence_bundle_ref),
        ledger_ref=_state_ref(ledger_ref),
        answer_contract_ref=_state_ref(answer_contract_ref),
        analyst_author_handoff_ref=analyst_ref,
        source_telemetry_ref=_copy_mapping(source_telemetry_ref),
    )


def execute_citation_source_handoff(
    state: CitationSourceHandoffState,
) -> CitationSourceExecutionEnvelope:
    """Return legacy handoff values without making citation decisions."""

    return CitationSourceExecutionEnvelope(
        unique_source_urls={
            str(item["url"]): item["source_id"]
            for item in state.source_identity.source_id_mapping
            if item.get("url") is not None
        },
        ordered_sources=list(state.ordered_source_list.ordered_sources),
        final_answer_source_telemetry=deepcopy(
            state.citation_observations.final_answer_source_telemetry
        ),
    )


__all__ = [
    "CITATION_SOURCE_HANDOFF_SCHEMA_VERSION",
    "CITATION_SOURCE_HANDOFF_TRACE_KEY",
    "AuthorSourceInputDescriptor",
    "CitationEligibilityDescriptor",
    "CitationObservationDescriptor",
    "CitationSourceExecutionEnvelope",
    "CitationSourceHandoffState",
    "OrderedSourceListDescriptor",
    "SourceIdentityDescriptor",
    "build_citation_source_handoff_state",
    "execute_citation_source_handoff",
]
