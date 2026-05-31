"""Controller-owned Analyst/Author handoff contract.

This module is deliberately passive and deterministic. It receives facts already
computed by the runtime, copies their identities into Controller-owned state, and
returns a mechanical legacy-compatible handoff. It does not build prompt text,
call providers, retrieve, select citations, persist sessions, or change Analyst,
Author, final-answer, citation, provider/search, DB, run-output, or cache
behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

ANALYST_AUTHOR_HANDOFF_SCHEMA_VERSION = "AG76D-AA.v1"
ANALYST_AUTHOR_HANDOFF_TRACE_KEY = "analyst_author_handoff_contract"


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    return tuple(str(item) for item in (value or ()))


def _hash_text(value: Any) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _evidence_identity(evidence: Sequence[Mapping[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    identities: list[dict[str, Any]] = []
    for index, item in enumerate(evidence or ()):  # preserve order exactly
        identities.append(
            {
                "position": index,
                "source_id": item.get("source_id"),
                "url": item.get("url"),
                "title": item.get("title"),
                "score": item.get("score"),
                "source_tier": item.get("source_tier"),
                "source_class": item.get("source_class"),
                "text_hash": _hash_text(item.get("text", "")),
                "text_length": len(str(item.get("text", "") or "")),
            }
        )
    return tuple(identities)


def _state_ref(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_controller_state"):
        return value.to_controller_state()
    if hasattr(value, "to_trace_fragment"):
        return value.to_trace_fragment()
    if hasattr(value, "execution_trace_fragment"):
        return value.execution_trace_fragment()
    if hasattr(value, "to_trace"):
        return value.to_trace()
    if isinstance(value, Mapping):
        return _copy_mapping(value)
    return {"ref_type": type(value).__name__}


@dataclass(frozen=True)
class AnalystAdmissionDescriptor:
    """Controller-owned copy of already-computed Analyst admission posture."""

    analyst_should_run: bool
    analyst_skipped: bool
    analyst_skip_reason: str | None
    post_retrieval_fast_path_used: bool
    pre_analyst_gate_signals: tuple[str, ...] = field(default_factory=tuple)
    analyst_skipped_after_economist: bool = False
    analyst_after_economist_skip_reason: str | None = None
    economist_output_used_as_analysis: bool = False
    controller_owned: bool = True
    legacy_runtime_branch: str = "pre_analyst_gate_contract"

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "analyst_should_run": bool(self.analyst_should_run),
            "analyst_skipped": bool(self.analyst_skipped),
            "analyst_skip_reason": self.analyst_skip_reason,
            "post_retrieval_fast_path_used": bool(self.post_retrieval_fast_path_used),
            "pre_analyst_gate_signals": list(self.pre_analyst_gate_signals),
            "analyst_skipped_after_economist": bool(self.analyst_skipped_after_economist),
            "analyst_after_economist_skip_reason": self.analyst_after_economist_skip_reason,
            "economist_output_used_as_analysis": bool(self.economist_output_used_as_analysis),
            "legacy_runtime_branch": self.legacy_runtime_branch,
            "mechanical_handoff_only": True,
        }


@dataclass(frozen=True)
class AnalystEvidenceContextDescriptor:
    """Identity of the Analyst evidence/context package without prompt text."""

    evidence_identity: tuple[dict[str, Any], ...]
    evidence_count: int
    context_prefix_hash: str | None = None
    context_prefix_length: int | None = None
    linkup_block_included: bool = False
    quantitative_packet_injected: bool = False
    missing_target_metric_directive_emitted: bool = False
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "evidence_count": int(self.evidence_count),
            "evidence_identity": deepcopy(list(self.evidence_identity)),
            "context_prefix_hash": self.context_prefix_hash,
            "context_prefix_length": self.context_prefix_length,
            "linkup_block_included": bool(self.linkup_block_included),
            "quantitative_packet_injected": bool(self.quantitative_packet_injected),
            "missing_target_metric_directive_emitted": bool(
                self.missing_target_metric_directive_emitted
            ),
            "prompt_text_included": False,
        }


@dataclass(frozen=True)
class UnsupportedDirectiveDescriptor:
    """Already-computed unsupported/weak/failure-card directive posture."""

    unsupported_retrieval_directive_active: bool
    weak_evidence_directive_active: bool
    failure_card_directive_active: bool
    analyst_skip_reason: str | None = None
    failure_card_reason: str | None = None
    author_notes_hash: str | None = None
    author_notes_length: int | None = None
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "unsupported_retrieval_directive_active": bool(
                self.unsupported_retrieval_directive_active
            ),
            "weak_evidence_directive_active": bool(self.weak_evidence_directive_active),
            "failure_card_directive_active": bool(self.failure_card_directive_active),
            "analyst_skip_reason": self.analyst_skip_reason,
            "failure_card_reason": self.failure_card_reason,
            "author_notes_hash": self.author_notes_hash,
            "author_notes_length": self.author_notes_length,
            "directive_text_included": False,
            "mechanical_handoff_only": True,
        }


@dataclass(frozen=True)
class AuthorEvidenceHandoffDescriptor:
    """Identity of the Author evidence handoff package."""

    author_evidence_identity: tuple[dict[str, Any], ...]
    selected_evidence_identity: tuple[dict[str, Any], ...]
    final_evidence_identity: tuple[dict[str, Any], ...]
    ordered_source_count: int
    unique_source_url_count: int
    author_evidence_block_hash: str | None = None
    author_evidence_block_length: int | None = None
    source_telemetry_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "author_evidence_count": len(self.author_evidence_identity),
            "selected_evidence_count": len(self.selected_evidence_identity),
            "final_evidence_count": len(self.final_evidence_identity),
            "author_evidence_identity": deepcopy(list(self.author_evidence_identity)),
            "selected_evidence_identity": deepcopy(list(self.selected_evidence_identity)),
            "final_evidence_identity": deepcopy(list(self.final_evidence_identity)),
            "ordered_source_count": int(self.ordered_source_count),
            "unique_source_url_count": int(self.unique_source_url_count),
            "author_evidence_block_hash": self.author_evidence_block_hash,
            "author_evidence_block_length": self.author_evidence_block_length,
            "source_telemetry_ref": deepcopy(self.source_telemetry_ref),
            "citation_behavior_included": False,
        }


@dataclass(frozen=True)
class AuthorPromptInputDescriptor:
    """Metadata for Author prompt inputs without prompt text."""

    prompt_hash: str
    prompt_length: int
    complexity: str
    author_system_prompt_key: str
    author_effort: str
    includes_analysis: bool
    includes_ordered_sources: bool
    includes_recency_notes: bool
    includes_author_notes: bool
    image_context_active: bool
    citation_source_list_identity: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "prompt_hash": self.prompt_hash,
            "prompt_length": int(self.prompt_length),
            "complexity": self.complexity,
            "author_system_prompt_key": self.author_system_prompt_key,
            "author_effort": self.author_effort,
            "includes_analysis": bool(self.includes_analysis),
            "includes_ordered_sources": bool(self.includes_ordered_sources),
            "includes_recency_notes": bool(self.includes_recency_notes),
            "includes_author_notes": bool(self.includes_author_notes),
            "image_context_active": bool(self.image_context_active),
            "citation_source_list_identity": deepcopy(self.citation_source_list_identity),
            "prompt_text_included": False,
        }


@dataclass(frozen=True)
class AnalystAuthorHandoffState:
    """Controller-owned Analyst/Author handoff state."""

    analyst_admission: AnalystAdmissionDescriptor
    analyst_evidence_context: AnalystEvidenceContextDescriptor
    unsupported_directives: UnsupportedDirectiveDescriptor
    author_evidence_handoff: AuthorEvidenceHandoffDescriptor
    author_prompt_input: AuthorPromptInputDescriptor
    run_id: str | None = None
    pre_analyst_gate_ref: dict[str, Any] = field(default_factory=dict)
    weak_failure_gate_ref: dict[str, Any] = field(default_factory=dict)
    retrieval_loop_ref: dict[str, Any] = field(default_factory=dict)
    router_query_preparation_ref: dict[str, Any] = field(default_factory=dict)
    answer_contract_ref: dict[str, Any] = field(default_factory=dict)
    final_evidence_ref: dict[str, Any] = field(default_factory=dict)
    trace_visibility: dict[str, Any] = field(default_factory=dict)
    schema_version: str = ANALYST_AUTHOR_HANDOFF_SCHEMA_VERSION
    controller_owned: bool = True

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            ANALYST_AUTHOR_HANDOFF_TRACE_KEY: {
                "schema_version": self.schema_version,
                "controller_owned": bool(self.controller_owned),
                "run_id": self.run_id,
                "analyst_admission": self.analyst_admission.to_trace(),
                "analyst_evidence_context": self.analyst_evidence_context.to_trace(),
                "unsupported_directives": self.unsupported_directives.to_trace(),
                "author_evidence_handoff": self.author_evidence_handoff.to_trace(),
                "author_prompt_input": self.author_prompt_input.to_trace(),
                "pre_analyst_gate_ref": deepcopy(self.pre_analyst_gate_ref),
                "weak_failure_gate_ref": deepcopy(self.weak_failure_gate_ref),
                "retrieval_loop_ref": deepcopy(self.retrieval_loop_ref),
                "router_query_preparation_ref": deepcopy(self.router_query_preparation_ref),
                "answer_contract_ref": deepcopy(self.answer_contract_ref),
                "final_evidence_ref": deepcopy(self.final_evidence_ref),
                "trace_visibility": {
                    "additive_only": True,
                    "legacy_trace_fields_preserved": True,
                    "owned_by": "Controller",
                    **deepcopy(self.trace_visibility),
                },
                "did_change_analyst_behavior": False,
                "did_change_author_behavior": False,
                "did_change_final_answer_behavior": False,
                "did_change_citation_behavior": False,
                "did_change_prompt_text": False,
                "did_change_provider_search_query_behavior": False,
                "did_change_db_session_run_outcome_shape": False,
                "did_change_cache_behavior": False,
                "mechanical_executor_boundary": True,
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.to_trace_fragment()[ANALYST_AUTHOR_HANDOFF_TRACE_KEY])


@dataclass(frozen=True)
class AnalystAuthorExecutionEnvelope:
    """Legacy-compatible mechanical outputs from Controller-owned handoff state."""

    analyst_should_run: bool
    analyst_skipped: bool
    analyst_skip_reason: str | None
    post_retrieval_fast_path_used: bool
    pre_analyst_gate_signals: tuple[str, ...]
    author_system_prompt_key: str
    author_effort: str
    controller_owned: bool = True
    mechanical_handoff_only: bool = True


def build_analyst_author_handoff_state(
    *,
    run_id: str | None = None,
    analyst_skipped: bool,
    analyst_skip_reason: str | None,
    post_retrieval_fast_path_used: bool,
    pre_analyst_gate_signals: Sequence[Any] | None = None,
    analyst_skipped_after_economist: bool = False,
    analyst_after_economist_skip_reason: str | None = None,
    economist_output_used_as_analysis: bool = False,
    analyst_evidence: Sequence[Mapping[str, Any]] | None = None,
    analyst_context_prefix: str | None = None,
    linkup_block_included: bool = False,
    quantitative_packet_injected: bool = False,
    missing_target_metric_directive_emitted: bool = False,
    corpus_weak: bool = False,
    failure_card_payload: Mapping[str, Any] | None = None,
    author_notes: str | None = None,
    author_evidence: Sequence[Mapping[str, Any]] | None = None,
    selected_evidence: Sequence[Mapping[str, Any]] | None = None,
    final_evidence: Sequence[Mapping[str, Any]] | None = None,
    ordered_sources: Sequence[Any] | None = None,
    unique_source_urls: Mapping[str, Any] | None = None,
    author_evidence_block: str | None = None,
    source_telemetry_ref: Mapping[str, Any] | None = None,
    author_prompt: str,
    complexity: str,
    author_system_prompt_key: str,
    author_effort: str,
    includes_analysis: bool,
    includes_recency_notes: bool,
    includes_author_notes: bool,
    image_context_active: bool,
    pre_analyst_gate_ref: Any | None = None,
    weak_failure_gate_state: Any | None = None,
    retrieval_loop_state: Any | None = None,
    router_query_preparation_state: Any | None = None,
    answer_contract_ref: Any | None = None,
    final_evidence_ref: Mapping[str, Any] | None = None,
) -> AnalystAuthorHandoffState:
    """Build Controller-owned state from already-computed handoff facts."""

    gate_ref = _state_ref(pre_analyst_gate_ref)
    weak_ref = _state_ref(weak_failure_gate_state)
    retrieval_ref = _state_ref(retrieval_loop_state)
    router_ref = _state_ref(router_query_preparation_state)
    answer_ref = _state_ref(answer_contract_ref)
    source_ref = _copy_mapping(source_telemetry_ref)
    selected = selected_evidence if selected_evidence is not None else final_evidence
    final = final_evidence if final_evidence is not None else selected_evidence
    failure_payload = _copy_mapping(failure_card_payload)

    admission = AnalystAdmissionDescriptor(
        analyst_should_run=not bool(analyst_skipped),
        analyst_skipped=bool(analyst_skipped),
        analyst_skip_reason=analyst_skip_reason,
        post_retrieval_fast_path_used=bool(post_retrieval_fast_path_used),
        pre_analyst_gate_signals=_string_tuple(pre_analyst_gate_signals),
        analyst_skipped_after_economist=bool(analyst_skipped_after_economist),
        analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
        economist_output_used_as_analysis=bool(economist_output_used_as_analysis),
    )
    analyst_context = AnalystEvidenceContextDescriptor(
        evidence_identity=_evidence_identity(analyst_evidence),
        evidence_count=len(analyst_evidence or ()),
        context_prefix_hash=_hash_text(analyst_context_prefix) if analyst_context_prefix is not None else None,
        context_prefix_length=(len(analyst_context_prefix) if analyst_context_prefix is not None else None),
        linkup_block_included=bool(linkup_block_included),
        quantitative_packet_injected=bool(quantitative_packet_injected),
        missing_target_metric_directive_emitted=bool(missing_target_metric_directive_emitted),
    )
    directives = UnsupportedDirectiveDescriptor(
        unsupported_retrieval_directive_active=bool(analyst_skipped),
        weak_evidence_directive_active=bool(corpus_weak),
        failure_card_directive_active=bool(failure_payload.get("show")),
        analyst_skip_reason=analyst_skip_reason,
        failure_card_reason=(
            str(failure_payload.get("reason")) if failure_payload.get("reason") is not None else None
        ),
        author_notes_hash=_hash_text(author_notes) if author_notes is not None else None,
        author_notes_length=(len(author_notes) if author_notes is not None else None),
    )
    author_handoff = AuthorEvidenceHandoffDescriptor(
        author_evidence_identity=_evidence_identity(author_evidence),
        selected_evidence_identity=_evidence_identity(selected),
        final_evidence_identity=_evidence_identity(final),
        ordered_source_count=len(ordered_sources or ()),
        unique_source_url_count=len(unique_source_urls or {}),
        author_evidence_block_hash=(
            _hash_text(author_evidence_block) if author_evidence_block is not None else None
        ),
        author_evidence_block_length=(
            len(author_evidence_block) if author_evidence_block is not None else None
        ),
        source_telemetry_ref=source_ref,
    )
    prompt_input = AuthorPromptInputDescriptor(
        prompt_hash=_hash_text(author_prompt),
        prompt_length=len(author_prompt),
        complexity=str(complexity),
        author_system_prompt_key=str(author_system_prompt_key),
        author_effort=str(author_effort),
        includes_analysis=bool(includes_analysis),
        includes_ordered_sources=bool(ordered_sources),
        includes_recency_notes=bool(includes_recency_notes),
        includes_author_notes=bool(includes_author_notes),
        image_context_active=bool(image_context_active),
        citation_source_list_identity={
            "ordered_source_count": len(ordered_sources or ()),
            "ordered_source_hash": _hash_text("\n".join(str(s) for s in (ordered_sources or ()))),
        },
    )
    return AnalystAuthorHandoffState(
        analyst_admission=admission,
        analyst_evidence_context=analyst_context,
        unsupported_directives=directives,
        author_evidence_handoff=author_handoff,
        author_prompt_input=prompt_input,
        run_id=run_id,
        pre_analyst_gate_ref=gate_ref,
        weak_failure_gate_ref=weak_ref,
        retrieval_loop_ref=retrieval_ref,
        router_query_preparation_ref=router_ref,
        answer_contract_ref=answer_ref,
        final_evidence_ref=_copy_mapping(final_evidence_ref),
    )


def execute_analyst_author_handoff(
    state: AnalystAuthorHandoffState,
) -> AnalystAuthorExecutionEnvelope:
    """Return legacy handoff values without making product decisions."""

    return AnalystAuthorExecutionEnvelope(
        analyst_should_run=bool(state.analyst_admission.analyst_should_run),
        analyst_skipped=bool(state.analyst_admission.analyst_skipped),
        analyst_skip_reason=state.analyst_admission.analyst_skip_reason,
        post_retrieval_fast_path_used=bool(
            state.analyst_admission.post_retrieval_fast_path_used
        ),
        pre_analyst_gate_signals=tuple(
            state.analyst_admission.pre_analyst_gate_signals
        ),
        author_system_prompt_key=state.author_prompt_input.author_system_prompt_key,
        author_effort=state.author_prompt_input.author_effort,
    )
