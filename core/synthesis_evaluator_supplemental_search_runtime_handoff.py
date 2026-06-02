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


@dataclass
class RuntimeSynthesisEvaluatorSupplementalSearchFactCollector:
    """Small mutable collector for already-computed runtime facts.

    The collector keeps synthesis-evaluator supplemental-search defaulting and
    final fact construction out of the orchestrator while preserving the legacy
    branch decisions exactly. Its methods only record facts that have already
    happened in the legacy path.
    """

    eligible: bool = False
    skip_reason: str | None = "legacy_complexity_or_fast_path_gate_not_authorized"
    completeness_posture: CompletenessPosture | str = CompletenessPosture.SKIPPED
    deficiency_text: str | None = None
    parse_error_ref: Mapping[str, Any] = field(default_factory=dict)
    supplemental_queries: list[RuntimeSupplementalQueryFact] = field(default_factory=list)
    supplemental_search_admission_posture: SupplementalSearchAdmissionPosture | str = (
        SupplementalSearchAdmissionPosture.SKIPPED
    )
    supplemental_search_admitted: bool = False
    supplemental_search_admission_reason: str | None = None
    supplemental_provider_role: str | None = None
    supplemental_providers: Sequence[Any] = field(default_factory=tuple)
    supplemental_search_depth: str | None = None
    supplemental_evidence: Sequence[Any] = field(default_factory=tuple)
    final_evidence_rebuild_reason: str | None = None
    analyst_rerun_triggered: bool = False
    author_hedge_note_emitted: bool = False

    def mark_eligible(self) -> None:
        self.eligible = True
        self.skip_reason = None

    def mark_strong_retrieval_skipped(self) -> None:
        self.skip_reason = "strong_retrieval_sufficient_no_supplemental_check"

    def mark_parse_failed(self, error: Exception) -> None:
        self.completeness_posture = CompletenessPosture.PARSE_FAILED
        self.parse_error_ref = {
            "error_type": type(error).__name__,
            "behavior": "legacy_defaults_to_sufficient",
        }

    def mark_completeness(self, *, sufficient: bool, deficiency_text: str | None) -> None:
        self.completeness_posture = (
            CompletenessPosture.SUFFICIENT if sufficient else CompletenessPosture.INSUFFICIENT
        )
        if not sufficient:
            self.deficiency_text = deficiency_text

    def record_supplemental_queries(self, queries: Sequence[Any]) -> None:
        self.supplemental_queries = [
            RuntimeSupplementalQueryFact(
                query_id=f"synthesis-evaluator-supplemental-query-{index + 1}",
                query_text=str(query),
                source_evaluator_decision="insufficient",
                source_deficiency_id="synthesis-evaluator-deficiency",
            )
            for index, query in enumerate(queries)
        ]

    def record_author_hedge_note(self) -> None:
        self.author_hedge_note_emitted = True

    def record_dispatch(
        self,
        *,
        providers: Sequence[Any],
        search_depth: str | None,
        provider_role: str = "supplemental_search",
    ) -> None:
        self.supplemental_provider_role = provider_role
        self.supplemental_providers = tuple(str(provider) for provider in (providers or ()))
        self.supplemental_search_depth = search_depth
        self.supplemental_search_admission_posture = SupplementalSearchAdmissionPosture.ADMITTED
        self.supplemental_search_admitted = True
        self.supplemental_search_admission_reason = "insufficient_with_supplemental_queries"

    def record_evidence(self, evidence: Sequence[Any]) -> None:
        self.supplemental_search_admission_posture = SupplementalSearchAdmissionPosture.COMPLETED
        self.supplemental_evidence = tuple(evidence or ())

    def record_final_evidence_rebuild(self) -> None:
        self.final_evidence_rebuild_reason = "supplemental_evidence_added"

    def record_analyst_rerun(self) -> None:
        self.analyst_rerun_triggered = True

    def build_facts(
        self,
        *,
        run_id: str,
        synth_was_insufficient: bool,
        results_per_query: int | None,
        delta_urls_supplemental: int,
        supplemental_ran: bool,
        final_evidence: Sequence[Any],
        ordered_source_count: int,
        unique_source_url_count: int,
        answer_contract_available: bool,
    ) -> RuntimeSynthesisEvaluatorSupplementalSearchFacts:
        deficiency_id = (
            "synthesis-evaluator-deficiency" if self.deficiency_text else None
        )
        return RuntimeSynthesisEvaluatorSupplementalSearchFacts(
            run_id=run_id,
            eligible=self.eligible,
            run_gate="legacy_synthesis_evaluator_supplemental_search_gate",
            completeness_posture=self.completeness_posture,
            requested=self.eligible,
            sufficient_evidence_available=not synth_was_insufficient,
            skip_reason=self.skip_reason,
            deficiency_id=deficiency_id,
            deficiency_text=self.deficiency_text,
            parse_error_ref=self.parse_error_ref,
            supplemental_queries=tuple(self.supplemental_queries),
            supplemental_search_admission_posture=self.supplemental_search_admission_posture,
            supplemental_search_admitted=self.supplemental_search_admitted,
            supplemental_search_admission_reason=self.supplemental_search_admission_reason,
            supplemental_provider_role=self.supplemental_provider_role,
            supplemental_providers=self.supplemental_providers,
            supplemental_search_depth=self.supplemental_search_depth,
            supplemental_results_per_query=results_per_query,
            supplemental_evidence=self.supplemental_evidence,
            supplemental_evidence_ref={
                "delta_urls_supplemental": delta_urls_supplemental,
                "supplemental_ran": supplemental_ran,
            },
            final_evidence_bundle_id=f"{run_id}:final_evidence",
            final_evidence=final_evidence,
            final_evidence_ref={
                "final_evidence_count": len(final_evidence),
                "ordered_source_count": ordered_source_count,
                "unique_source_url_count": unique_source_url_count,
            },
            final_evidence_rebuild_reason=self.final_evidence_rebuild_reason,
            analyst_rerun_posture=(
                AnalystRerunAdmissionPosture.TRIGGERED
                if self.analyst_rerun_triggered
                else AnalystRerunAdmissionPosture.SKIPPED
            ),
            analyst_rerun_admitted=self.analyst_rerun_triggered,
            analyst_rerun_triggered=self.analyst_rerun_triggered,
            analyst_rerun_trigger_reason=(
                "supplemental_evidence_added" if self.analyst_rerun_triggered else None
            ),
            analyst_pass_ref=(
                {"stage": "analyst_supplemental"}
                if self.analyst_rerun_triggered
                else {}
            ),
            author_hedge_note_emitted=self.author_hedge_note_emitted,
            author_note_ref={"source": "legacy_synthesis_evaluator_author_note"},
            answer_contract_ref={
                "trace_key": "answer_contract_runtime_handoff",
                "available": answer_contract_available,
            },
            analyst_author_handoff_ref={
                "trace_key": "analyst_author_handoff_contract"
            },
            citation_source_handoff_ref={
                "trace_key": "citation_source_handoff_contract"
            },
        )

    def to_trace_fragment(self, **build_fact_kwargs: Any) -> dict[str, Any]:
        return runtime_synthesis_evaluator_supplemental_search_trace_fragment(
            self.build_facts(**build_fact_kwargs)
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
    "RuntimeSynthesisEvaluatorSupplementalSearchFactCollector",
    "RuntimeSynthesisEvaluatorSupplementalSearchFacts",
    "build_runtime_synthesis_evaluator_supplemental_search_handoff",
    "runtime_synthesis_evaluator_supplemental_search_trace_fragment",
]
