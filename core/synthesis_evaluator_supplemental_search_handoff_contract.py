"""Passive synthesis-evaluator supplemental-search handoff contract.

AG-76D-SES records facts the legacy synthesis-evaluator supplemental-search
path has already computed or exposed to downstream runtime branches. The module
is purely representational: it does not evaluate completeness, generate
supplemental queries, call providers/search/retrieval, rebuild evidence, re-run
Analyst, alter Author notes/prose, format citations, persist sessions, touch
cache, or wire runtime orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_SCHEMA_VERSION = "AG76D-SES.v1"
SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY = (
    "synthesis_evaluator_supplemental_search_handoff"
)
SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_CONSUMER = (
    "future_controller_owned_synthesis_evaluator_supplemental_search_handoff"
)

NO_BEHAVIOR_CHANGE_FLAGS: Mapping[str, bool] = {
    "evaluator_behavior_changed": False,
    "prompt_behavior_changed": False,
    "provider_behavior_changed": False,
    "search_behavior_changed": False,
    "retrieval_behavior_changed": False,
    "analyst_behavior_changed": False,
    "author_behavior_changed": False,
    "author_prompt_behavior_changed": False,
    "author_prose_behavior_changed": False,
    "citation_behavior_changed": False,
    "db_session_runoutcome_behavior_changed": False,
    "cache_behavior_changed": False,
    "pipeline_orchestrator_behavior_changed": False,
    "live_validation_behavior_changed": False,
}


class CompletenessPosture(str, Enum):
    """Stable completeness posture emitted by legacy evaluation."""

    SKIPPED = "skipped"
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    PARSE_FAILED = "parse_failed"


class SupplementalSearchAdmissionPosture(str, Enum):
    """Stable admission posture for supplemental search dispatch."""

    ADMITTED = "admitted"
    NOT_ADMITTED = "not_admitted"
    SKIPPED = "skipped"
    COMPLETED = "completed"


class AnalystRerunAdmissionPosture(str, Enum):
    """Stable admission posture for Analyst re-run / re-analysis."""

    ADMITTED = "admitted"
    NOT_ADMITTED = "not_admitted"
    TRIGGERED = "triggered"
    SKIPPED = "skipped"


class AuthorNoteIdentity(str, Enum):
    """Stable identities for synthesis-evaluator-originating Author notes."""

    HEDGE_WHERE_DATA_MISSING = "hedge_appropriately_where_data_is_missing"


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _text_tuple(value: Sequence[Any] | None, *, limit: int = 240) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in value or ():
        text = _text(item, limit=limit)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return _json_safe(dict(value or {}))


@dataclass(frozen=True)
class SynthesisEvaluatorRunEligibilityDescriptor:
    """Run eligibility and gate facts for the legacy synthesis evaluator."""

    eligible: bool
    run_gate: str
    requested: bool | None = None
    sufficient_evidence_available: bool | None = None
    skip_reason: str | None = None
    already_computed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "eligible": self.eligible,
                "run_gate": _text(self.run_gate, limit=160),
                "requested": self.requested,
                "sufficient_evidence_available": self.sufficient_evidence_available,
                "skip_reason": _text(self.skip_reason, limit=240),
                "already_computed": self.already_computed,
                "changes_evaluator_behavior": False,
            }
        )


@dataclass(frozen=True)
class CompletenessEvaluationDescriptor:
    """Already-computed completeness posture and deficiency identity."""

    posture: CompletenessPosture | str
    deficiency_id: str | None = None
    deficiency_text: str | None = None
    evaluator_decision_ref: Mapping[str, Any] = field(default_factory=dict)
    parse_error_ref: Mapping[str, Any] = field(default_factory=dict)
    raw_evaluator_output_ref: Mapping[str, Any] = field(default_factory=dict)
    already_computed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "posture": _enum_value(self.posture),
                "deficiency_id": _text(self.deficiency_id, limit=120),
                "deficiency_text": _text(self.deficiency_text, limit=600),
                "evaluator_decision_ref": _mapping(self.evaluator_decision_ref),
                "parse_error_ref": _mapping(self.parse_error_ref),
                "raw_evaluator_output_ref": _mapping(self.raw_evaluator_output_ref),
                "already_computed": self.already_computed,
                "changes_evaluator_output": False,
                "prompt_text_included": False,
            }
        )


@dataclass(frozen=True)
class SupplementalQueryDescriptor:
    """Identity of a supplemental query from the evaluator decision."""

    query_id: str
    query_text: str
    source_evaluator_decision: str | None = None
    source_deficiency_id: str | None = None
    evaluator_decision_ref: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "query_id": _text(self.query_id, limit=120),
                "query_text": _text(self.query_text, limit=500),
                "source_evaluator_decision": _text(
                    self.source_evaluator_decision, limit=160
                ),
                "source_deficiency_id": _text(self.source_deficiency_id, limit=120),
                "evaluator_decision_ref": _mapping(self.evaluator_decision_ref),
                "changes_query_generation_behavior": False,
            }
        )


@dataclass(frozen=True)
class SupplementalSearchDescriptor:
    """Supplemental search admission and protected provider/depth posture."""

    admission_posture: SupplementalSearchAdmissionPosture | str
    admitted: bool
    provider_role: str | None = None
    providers: tuple[str, ...] = ()
    search_depth: str | None = None
    results_per_query: int | None = None
    admission_reason: str | None = None
    protected_legacy_provider_depth_posture: bool = True
    already_computed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "providers", _text_tuple(self.providers, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "admission_posture": _enum_value(self.admission_posture),
                "admitted": self.admitted,
                "admission_reason": _text(self.admission_reason, limit=240),
                "provider_role": _text(self.provider_role, limit=120),
                "providers": list(self.providers),
                "search_depth": _text(self.search_depth, limit=80),
                "results_per_query": self.results_per_query,
                "protected_legacy_provider_depth_posture": (
                    self.protected_legacy_provider_depth_posture
                ),
                "already_computed": self.already_computed,
                "changes_provider_search_depth_behavior": False,
            }
        )


@dataclass(frozen=True)
class SupplementalEvidenceDescriptor:
    """Identity of supplemental evidence accepted by the legacy path."""

    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    urls: tuple[str, ...] = ()
    evidence_count: int | None = None
    evidence_ref: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", _text_tuple(self.evidence_ids, limit=120))
        object.__setattr__(self, "source_ids", _text_tuple(self.source_ids, limit=120))
        object.__setattr__(self, "urls", _text_tuple(self.urls, limit=500))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "evidence_ids": list(self.evidence_ids),
                "source_ids": list(self.source_ids),
                "urls": list(self.urls),
                "evidence_count": self.evidence_count,
                "evidence_ref": _mapping(self.evidence_ref),
                "changes_retrieval_behavior": False,
            }
        )


@dataclass(frozen=True)
class FinalEvidenceRebuildDescriptor:
    """Identity of final evidence after the already-computed rebuild."""

    final_evidence_bundle_id: str | None = None
    final_evidence_ids: tuple[str, ...] = ()
    final_source_ids: tuple[str, ...] = ()
    final_evidence_ref: Mapping[str, Any] = field(default_factory=dict)
    rebuild_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "final_evidence_ids", _text_tuple(self.final_evidence_ids, limit=120)
        )
        object.__setattr__(self, "final_source_ids", _text_tuple(self.final_source_ids, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "final_evidence_bundle_id": _text(
                    self.final_evidence_bundle_id, limit=160
                ),
                "final_evidence_ids": list(self.final_evidence_ids),
                "final_source_ids": list(self.final_source_ids),
                "final_evidence_ref": _mapping(self.final_evidence_ref),
                "rebuild_reason": _text(self.rebuild_reason, limit=240),
                "changes_final_evidence_selection_behavior": False,
            }
        )


@dataclass(frozen=True)
class AnalystRerunDescriptor:
    """Analyst re-run / re-analysis admission posture, not an executor."""

    posture: AnalystRerunAdmissionPosture | str
    rerun_admitted: bool = False
    rerun_triggered: bool = False
    trigger_reason: str | None = None
    analyst_pass_ref: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "posture": _enum_value(self.posture),
                "rerun_admitted": self.rerun_admitted,
                "rerun_triggered": self.rerun_triggered,
                "trigger_reason": _text(self.trigger_reason, limit=240),
                "analyst_pass_ref": _mapping(self.analyst_pass_ref),
                "changes_analyst_behavior": False,
            }
        )


@dataclass(frozen=True)
class AuthorNoteDescriptor:
    """Author note identity without prompt/prose mutation."""

    note_id: str
    identity: AuthorNoteIdentity | str
    source_deficiency_id: str | None = None
    hedge_where_data_missing: bool = False
    note_ref: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "note_id": _text(self.note_id, limit=120),
                "identity": _enum_value(self.identity),
                "source_deficiency_id": _text(self.source_deficiency_id, limit=120),
                "hedge_where_data_missing": self.hedge_where_data_missing,
                "note_ref": _mapping(self.note_ref),
                "prompt_text_included": False,
                "changes_author_prompt_or_prose_behavior": False,
            }
        )


@dataclass(frozen=True)
class SynthesisEvaluatorSupplementalSearchExecutionEnvelope:
    """Mechanical execution envelope for a future Controller-owned consumer."""

    consumer: str = SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_CONSUMER
    trace_key: str = SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY
    mechanical_executor_boundary: bool = True
    runtime_wiring_active: bool = False
    behavior_change_authorized: bool = False
    live_validation_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "consumer": self.consumer,
                "trace_key": self.trace_key,
                "mechanical_executor_boundary": self.mechanical_executor_boundary,
                "runtime_wiring_active": self.runtime_wiring_active,
                "behavior_change_authorized": self.behavior_change_authorized,
                "live_validation_performed": self.live_validation_performed,
            }
        )


@dataclass(frozen=True)
class SynthesisEvaluatorSupplementalSearchHandoffState:
    """Controller-owned passive supplemental-search handoff representation."""

    run_id: str
    eligibility: SynthesisEvaluatorRunEligibilityDescriptor
    completeness: CompletenessEvaluationDescriptor
    supplemental_queries: tuple[SupplementalQueryDescriptor, ...] = ()
    supplemental_search: SupplementalSearchDescriptor | None = None
    supplemental_evidence: SupplementalEvidenceDescriptor | None = None
    final_evidence_rebuild: FinalEvidenceRebuildDescriptor | None = None
    analyst_rerun: AnalystRerunDescriptor | None = None
    author_notes: tuple[AuthorNoteDescriptor, ...] = ()
    answer_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    citation_source_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    execution_envelope: SynthesisEvaluatorSupplementalSearchExecutionEnvelope = field(
        default_factory=SynthesisEvaluatorSupplementalSearchExecutionEnvelope
    )
    schema_version: str = SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_SCHEMA_VERSION
    trace_key: str = SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF_TRACE_KEY

    def to_controller_state(self) -> dict[str, Any]:
        return _json_safe(
            {
                "schema_version": self.schema_version,
                "run_id": _text(self.run_id, limit=120),
                "trace_key": self.trace_key,
                "eligibility": self.eligibility.to_dict(),
                "completeness": self.completeness.to_dict(),
                "supplemental_queries": [
                    query.to_dict() for query in self.supplemental_queries
                ],
                "supplemental_search": (
                    self.supplemental_search.to_dict()
                    if self.supplemental_search is not None
                    else None
                ),
                "supplemental_evidence": (
                    self.supplemental_evidence.to_dict()
                    if self.supplemental_evidence is not None
                    else None
                ),
                "final_evidence_rebuild": (
                    self.final_evidence_rebuild.to_dict()
                    if self.final_evidence_rebuild is not None
                    else None
                ),
                "analyst_rerun": (
                    self.analyst_rerun.to_dict() if self.analyst_rerun is not None else None
                ),
                "author_notes": [note.to_dict() for note in self.author_notes],
                "handoff_refs": {
                    "answer_contract_ref": _mapping(self.answer_contract_ref),
                    "analyst_author_handoff_ref": _mapping(self.analyst_author_handoff_ref),
                    "citation_source_handoff_ref": _mapping(self.citation_source_handoff_ref),
                },
                "execution_envelope": self.execution_envelope.to_dict(),
                "no_behavior_change_flags": dict(NO_BEHAVIOR_CHANGE_FLAGS),
            }
        )

    def to_trace_fragment(self) -> dict[str, Any]:
        return {self.trace_key: self.to_controller_state()}
