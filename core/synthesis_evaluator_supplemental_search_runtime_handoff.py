"""Runtime adapter for passive synthesis-evaluator supplemental-search handoff.

AG-76D-SES-R1 consumes facts that the legacy synthesis-evaluator
supplemental-search runtime path has already computed and projects them into the
AG-76D-SES Controller-owned handoff contract. It is intentionally
representation-only: it does not evaluate completeness, generate queries, call
providers/search/retrieval, rebuild evidence, re-run Analyst, alter Author
notes/prose, format citations, persist sessions, touch cache, or perform live
validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from core.synthesis_evaluator_supplemental_search_handoff_contract import (
    AnalystRerunAdmissionPosture,
    AnalystRerunDescriptor,
    AuthorNoteDescriptor,
    AuthorNoteIdentity,
    CompletenessEvaluationDescriptor,
    CompletenessPosture,
    FinalEvidenceRebuildDescriptor,
    SupplementalEvidenceDescriptor,
    SupplementalQueryDescriptor,
    SupplementalSearchAdmissionPosture,
    SupplementalSearchDescriptor,
    SynthesisEvaluatorRunEligibilityDescriptor,
    SynthesisEvaluatorSupplementalSearchExecutionEnvelope,
    SynthesisEvaluatorSupplementalSearchHandoffState,
)


def _text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    return text[:limit] if text else None


def _dedupe_text(values: Sequence[Any] | None, *, limit: int = 240) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = _text(value, limit=limit)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _evidence_value(item: Any, *names: str) -> Any:
    if isinstance(item, Mapping):
        for name in names:
            if name in item:
                return item.get(name)
    for name in names:
        if hasattr(item, name):
            return getattr(item, name)
    return None


def _evidence_identity(item: Any, index: int, *, prefix: str) -> tuple[str, str | None, str | None]:
    evidence_id = _evidence_value(item, "evidence_id", "id", "source_id", "url", "link")
    source_id = _evidence_value(item, "source_id", "id")
    url = _evidence_value(item, "url", "link")
    return (
        str(evidence_id or f"{prefix}-{index + 1}"),
        _text(source_id, limit=120),
        _text(url, limit=500),
    )


@dataclass(frozen=True)
class RuntimeSupplementalQueryFact:
    """Already-computed supplemental-query identity from the evaluator path."""

    query_text: str
    query_id: str | None = None
    source_evaluator_decision: str | None = None
    source_deficiency_id: str | None = None
    evaluator_decision_ref: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeSynthesisEvaluatorSupplementalSearchFacts:
    """Facts observed from the legacy synthesis-evaluator supplemental path."""

    run_id: str
    eligible: bool
    run_gate: str
    completeness_posture: CompletenessPosture | str
    requested: bool | None = None
    sufficient_evidence_available: bool | None = None
    skip_reason: str | None = None
    deficiency_id: str | None = None
    deficiency_text: str | None = None
    evaluator_decision_ref: Mapping[str, Any] = field(default_factory=dict)
    parse_error_ref: Mapping[str, Any] = field(default_factory=dict)
    raw_evaluator_output_ref: Mapping[str, Any] = field(default_factory=dict)
    supplemental_queries: Sequence[RuntimeSupplementalQueryFact] = ()
    supplemental_search_admission_posture: SupplementalSearchAdmissionPosture | str = (
        SupplementalSearchAdmissionPosture.SKIPPED
    )
    supplemental_search_admitted: bool = False
    supplemental_search_admission_reason: str | None = None
    supplemental_provider_role: str | None = None
    supplemental_providers: Sequence[Any] = ()
    supplemental_search_depth: str | None = None
    supplemental_results_per_query: int | None = None
    supplemental_evidence: Sequence[Any] = ()
    supplemental_evidence_ref: Mapping[str, Any] = field(default_factory=dict)
    final_evidence_bundle_id: str | None = None
    final_evidence: Sequence[Any] = ()
    final_evidence_ref: Mapping[str, Any] = field(default_factory=dict)
    final_evidence_rebuild_reason: str | None = None
    analyst_rerun_posture: AnalystRerunAdmissionPosture | str = (
        AnalystRerunAdmissionPosture.SKIPPED
    )
    analyst_rerun_admitted: bool = False
    analyst_rerun_triggered: bool = False
    analyst_rerun_trigger_reason: str | None = None
    analyst_pass_ref: Mapping[str, Any] = field(default_factory=dict)
    author_hedge_note_emitted: bool = False
    author_note_ref: Mapping[str, Any] = field(default_factory=dict)
    answer_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    citation_source_handoff_ref: Mapping[str, Any] = field(default_factory=dict)


def _query_descriptors(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> tuple[SupplementalQueryDescriptor, ...]:
    return tuple(
        SupplementalQueryDescriptor(
            query_id=query.query_id or f"synthesis-evaluator-supplemental-query-{index + 1}",
            query_text=query.query_text,
            source_evaluator_decision=query.source_evaluator_decision,
            source_deficiency_id=query.source_deficiency_id or facts.deficiency_id,
            evaluator_decision_ref=query.evaluator_decision_ref or facts.evaluator_decision_ref,
        )
        for index, query in enumerate(facts.supplemental_queries)
    )


def _supplemental_evidence_descriptor(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> SupplementalEvidenceDescriptor | None:
    if not facts.supplemental_evidence and not facts.supplemental_evidence_ref:
        return None
    evidence_ids: list[str] = []
    source_ids: list[str] = []
    urls: list[str] = []
    for index, item in enumerate(facts.supplemental_evidence):
        evidence_id, source_id, url = _evidence_identity(
            item, index, prefix="supplemental-evidence"
        )
        evidence_ids.append(evidence_id)
        if source_id:
            source_ids.append(source_id)
        if url:
            urls.append(url)
    return SupplementalEvidenceDescriptor(
        evidence_ids=_dedupe_text(evidence_ids, limit=120),
        source_ids=_dedupe_text(source_ids, limit=120),
        urls=_dedupe_text(urls, limit=500),
        evidence_count=len(facts.supplemental_evidence),
        evidence_ref=facts.supplemental_evidence_ref,
    )


def _final_evidence_rebuild_descriptor(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> FinalEvidenceRebuildDescriptor | None:
    if not facts.final_evidence and not facts.final_evidence_bundle_id and not facts.final_evidence_ref:
        return None
    evidence_ids: list[str] = []
    source_ids: list[str] = []
    for index, item in enumerate(facts.final_evidence):
        evidence_id, source_id, _url = _evidence_identity(
            item, index, prefix="final-evidence"
        )
        evidence_ids.append(evidence_id)
        if source_id:
            source_ids.append(source_id)
    return FinalEvidenceRebuildDescriptor(
        final_evidence_bundle_id=facts.final_evidence_bundle_id,
        final_evidence_ids=_dedupe_text(evidence_ids, limit=120),
        final_source_ids=_dedupe_text(source_ids, limit=120),
        final_evidence_ref=facts.final_evidence_ref,
        rebuild_reason=facts.final_evidence_rebuild_reason,
    )


def _author_notes(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> tuple[AuthorNoteDescriptor, ...]:
    if not facts.author_hedge_note_emitted:
        return ()
    return (
        AuthorNoteDescriptor(
            note_id="synthesis-evaluator-hedge-missing-data",
            identity=AuthorNoteIdentity.HEDGE_WHERE_DATA_MISSING,
            source_deficiency_id=facts.deficiency_id,
            hedge_where_data_missing=True,
            note_ref=facts.author_note_ref,
        ),
    )


def build_runtime_synthesis_evaluator_supplemental_search_handoff(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> SynthesisEvaluatorSupplementalSearchHandoffState:
    """Build the passive handoff from legacy runtime facts without side effects."""
    return SynthesisEvaluatorSupplementalSearchHandoffState(
        run_id=facts.run_id,
        eligibility=SynthesisEvaluatorRunEligibilityDescriptor(
            eligible=facts.eligible,
            run_gate=facts.run_gate,
            requested=facts.requested,
            sufficient_evidence_available=facts.sufficient_evidence_available,
            skip_reason=facts.skip_reason,
        ),
        completeness=CompletenessEvaluationDescriptor(
            posture=facts.completeness_posture,
            deficiency_id=facts.deficiency_id,
            deficiency_text=facts.deficiency_text,
            evaluator_decision_ref=facts.evaluator_decision_ref,
            parse_error_ref=facts.parse_error_ref,
            raw_evaluator_output_ref=facts.raw_evaluator_output_ref,
        ),
        supplemental_queries=_query_descriptors(facts),
        supplemental_search=SupplementalSearchDescriptor(
            admission_posture=facts.supplemental_search_admission_posture,
            admitted=facts.supplemental_search_admitted,
            provider_role=facts.supplemental_provider_role,
            providers=_dedupe_text(facts.supplemental_providers, limit=120),
            search_depth=facts.supplemental_search_depth,
            results_per_query=facts.supplemental_results_per_query,
            admission_reason=facts.supplemental_search_admission_reason,
        ),
        supplemental_evidence=_supplemental_evidence_descriptor(facts),
        final_evidence_rebuild=_final_evidence_rebuild_descriptor(facts),
        analyst_rerun=AnalystRerunDescriptor(
            posture=facts.analyst_rerun_posture,
            rerun_admitted=facts.analyst_rerun_admitted,
            rerun_triggered=facts.analyst_rerun_triggered,
            trigger_reason=facts.analyst_rerun_trigger_reason,
            analyst_pass_ref=_mapping(facts.analyst_pass_ref),
        ),
        author_notes=_author_notes(facts),
        answer_contract_ref=facts.answer_contract_ref,
        analyst_author_handoff_ref=facts.analyst_author_handoff_ref,
        citation_source_handoff_ref=facts.citation_source_handoff_ref,
        execution_envelope=SynthesisEvaluatorSupplementalSearchExecutionEnvelope(
            runtime_wiring_active=True,
            behavior_change_authorized=False,
            live_validation_performed=False,
        ),
    )


def runtime_synthesis_evaluator_supplemental_search_trace_fragment(
    facts: RuntimeSynthesisEvaluatorSupplementalSearchFacts,
) -> dict[str, Any]:
    """Return the JSON-safe trace fragment for runtime attachment."""
    return build_runtime_synthesis_evaluator_supplemental_search_handoff(
        facts
    ).to_trace_fragment()


__all__ = [
    "RuntimeSupplementalQueryFact",
    "RuntimeSynthesisEvaluatorSupplementalSearchFacts",
    "build_runtime_synthesis_evaluator_supplemental_search_handoff",
    "runtime_synthesis_evaluator_supplemental_search_trace_fragment",
]
