"""Ordinary semantic producer runtime for AG-SEM-11.

Builds passive AG-SEM-01..03 proposals from ordinary offline runtime facts and
commits them through the RunKernel semantic producer bundle boundary immediately
before RunAuthority Sufficiency. AG-SEM-MULTI-01 extends the
producer to a bounded loop over deterministic answer-component candidates while
leaving all final readiness decisions to Sufficiency.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.component_coverage_record import (
    ComponentCoverageRecord,
    ConflictPosture,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
)
from core.component_coverage_reduction_runtime import (
    build_component_coverage_reduction_state,
    evidence_ledger_projection_digest,
    ledger_qualification_blockers_for_satisfied_coverage,
)
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.initial_answer_contract_acceptance_runtime import (
    build_initial_answer_contract_acceptance_state,
)
from core.query_shape_contract_resolution import ComponentCandidate, QueryShapeAssessment
from core.search_work_query_shape_runtime import (
    DeterministicSearchWorkRuntimeInput,
    build_deterministic_search_work_runtime_records,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    QuestionMeaningRecord,
    RequirementPosture,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SupportKind,
)
from core.semantic_observation_admission_runtime import (
    build_semantic_observation_admission_state,
)
from core.semantic_observation_foundation import (
    MAX_BOUNDED_TEXT_CHARS,
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)

ORDINARY_SEMANTIC_PRODUCER_SCHEMA_VERSION = "ordinary_semantic_producer_ag_sem_11_v1"
ORDINARY_SEMANTIC_PRODUCER_RESOLVER_VERSION = "ag-sem-11-query-shape-seeded"
ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP = 5
_PREFLIGHT_ACTION_ID = "preflight:ag-sem-11-ordinary-semantic-producer"

SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE = "query_shape_classifier_unavailable"
SKIP_REASON_MULTIPART_ASSESSMENT = "multipart_assessment"
SKIP_REASON_COMPONENT_CAP_EXCEEDED = "component_cap_exceeded"
SKIP_REASON_BINDABLE_PASSAGE_MISSING = "bindable_passage_missing"
SKIP_REASON_CONTRACT_PREFLIGHT_FAILED = "contract_preflight_failed"
SKIP_REASON_ADMISSION_PREFLIGHT_FAILED = "admission_preflight_failed"
SKIP_REASON_COVERAGE_PREFLIGHT_FAILED = "coverage_preflight_failed"
SKIP_REASON_PREFLIGHT_FAILED = "preflight_failed"
SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT = (
    "canonical_semantic_state_already_present"
)
SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING = (
    "accepted_answer_contract_missing"
)

_ACCEPTED_DISPOSITIONS = frozenset({"accepted", "observed", "partially_accepted"})
_READABLE_STATUSES = frozenset({"readable", "available", "ok"})


class OrdinarySemanticProducerHandoffStatus(str, Enum):
    SKIPPED = "skipped"
    COMMITTED = "committed"


class OrdinarySemanticProducerTransactionError(RuntimeError):
    """Raised when the semantic producer bundle fails before atomic commit."""


@dataclass(frozen=True, slots=True)
class BindableFinalPassage:
    passage: dict[str, Any]
    evidence_ref_id: str
    candidate_record: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OrdinarySemanticProducerComponentBundle:
    answer_component_id: str
    semantic_observation: SemanticObservation
    sanitized_content_references: tuple[SanitizedContentReference, ...]
    component_coverage_record: ComponentCoverageRecord
    dry_run_admission_projection: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OrdinarySemanticProducerBundle:
    question_meaning_record: QuestionMeaningRecord
    component_bundles: tuple[OrdinarySemanticProducerComponentBundle, ...]
    dry_run_accepted_contract: dict[str, Any]

    @property
    def semantic_observation(self) -> SemanticObservation:
        return self.component_bundles[0].semantic_observation

    @property
    def sanitized_content_references(self) -> tuple[SanitizedContentReference, ...]:
        return tuple(
            ref
            for component_bundle in self.component_bundles
            for ref in component_bundle.sanitized_content_references
        )

    @property
    def component_coverage_record(self) -> ComponentCoverageRecord:
        return self.component_bundles[0].component_coverage_record

    @property
    def dry_run_admission_projection(self) -> dict[str, Any]:
        return self.component_bundles[0].dry_run_admission_projection


@dataclass(frozen=True, slots=True)
class OrdinarySemanticProducerHandoffResult:
    status: OrdinarySemanticProducerHandoffStatus
    skipped_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OrdinarySemanticProducerPreflightResult:
    bundle: OrdinarySemanticProducerBundle | None
    skipped_reason: str | None = None


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_url(value: Any) -> str | None:
    text = _clean_text(value, limit=400)
    if not text:
        return None
    return text.casefold().rstrip("/")


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    return _clean_token(host, limit=120)


def _request_digest(*, query: str, run_id: str) -> str:
    payload = f"{_clean_text(query, limit=360) or ''}|{run_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _passage_candidate_id(passage: Mapping[str, Any], *, index: int) -> str | None:
    explicit = _clean_token(passage.get("candidate_id"))
    if explicit:
        return explicit
    for key in ("url", "source_url", "normalized_source_identity", "source_identity"):
        value = _normalize_url(passage.get(key))
        if value:
            return f"candidate:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"
    source_id = _clean_token(passage.get("source_id"))
    if source_id:
        return f"source-id:{source_id}"
    title = _clean_text(passage.get("title"))
    if title:
        return f"title:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:16]}"
    if index > 0:
        return f"passage:{index}"
    return None


def _search_work_plan_uses_real_query_shape_classifier(
    search_work_plan: Mapping[str, Any],
) -> bool:
    metadata = _safe_mapping(search_work_plan.get("metadata"))
    construction_metadata = _safe_mapping(metadata.get("construction_metadata"))
    if construction_metadata.get("implements_query_shape_classifier") is True:
        return True
    if construction_metadata.get("runtime_shadow_scaffolding") is True:
        return False
    if _clean_token(construction_metadata.get("fallback_reason")):
        return False
    return metadata.get("implements_query_shape_classifier") is True


def _semantic_slot_for_component(
    *,
    component: ComponentCandidate,
    route_facts: Mapping[str, Any],
) -> SemanticSlot:
    topic = (
        _clean_text(component.user_facing_subquestion, limit=220)
        or _clean_text(route_facts.get("core_topic"), limit=220)
        or "primary topic"
    )
    return SemanticSlot(
        slot_id=f"slot:{component.component_id}:entity",
        slot_kind=SemanticSlotKind.ENTITY,
        status=SemanticSlotStatus.EXPLICIT,
        selected_value=topic,
        materiality=Materiality.MATERIAL,
    )


def _answer_component_from_candidate(
    candidate: ComponentCandidate,
    *,
    semantic_slot_ids: tuple[str, ...],
) -> AnswerComponentContract:
    label = _clean_text(candidate.user_facing_subquestion, limit=120) or "Primary component"
    question = _clean_text(candidate.user_facing_subquestion, limit=300) or label
    component_id = _clean_token(candidate.component_id) or "component-1"
    if not component_id.startswith("component:"):
        component_id = f"component:{component_id}"
    query_shape_obligation_ids = tuple(
        obligation_id
        for obligation_id in (
            _clean_token(item) for item in candidate.source_obligation_candidate_ids
        )
        if obligation_id
    )
    # Query-shape classification can expose several overlapping obligation
    # candidates for one user-facing fact (for example, an official current
    # numeric value). A direct answer component owns one exact source need;
    # the QMR retains the complete query-shape candidate set separately.
    obligation_ids = query_shape_obligation_ids[:1]
    source_obligation_label = _direct_source_obligation_label(obligation_ids)
    return AnswerComponentContract(
        component_id=component_id,
        user_facing_label=label,
        user_facing_question=question,
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=(
            f"state the bounded {source_obligation_label} answer",
            "bind it to custodied evidence",
        ),
        semantic_slot_ids=semantic_slot_ids,
        source_obligation_candidate_ids=obligation_ids,
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        mandatory_caveats=("Answer remains evidence-bound.",),
        prohibited_upgrades=(f"Do not replace {source_obligation_label} evidence with an estimate.",),
        materiality=Materiality.MATERIAL,
        metadata={
            "phase": "AG-SEM-11",
            "deterministic_runtime": True,
            "query_shape_source_obligation_candidate_ids": list(
                query_shape_obligation_ids
            ),
            "exact_source_obligation_projection": (
                len(query_shape_obligation_ids) > 1
            ),
        },
    )


def _direct_source_obligation_label(obligation_ids: Sequence[str]) -> str:
    normalized = {
        (obligation_id or "").casefold().removeprefix("obligation:")
        for obligation_id in obligation_ids
    }
    if "official_current" in normalized:
        return "official current"
    if "legal_current_primary" in normalized:
        return "primary legal"
    if "canonical_documentation" in normalized:
        return "canonical documentation"
    if "source_bound_numeric" in normalized:
        return "source-bound numeric"
    if "reputable_secondary" in normalized:
        return "reputable source-bound"
    return "source-bound"


def _component_matching_text(component: AnswerComponentContract) -> str:
    text = _clean_text(component.user_facing_question, limit=300) or (
        _clean_text(component.user_facing_label, limit=200) or ""
    )
    lowered = text.casefold()
    marker = " say about "
    if marker in lowered:
        text = text[lowered.index(marker) + len(marker) :]
    lowered = text.casefold()
    for prefix in ("answer the ",):
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            break
    lowered = text.casefold()
    suffix = " component."
    if lowered.endswith(suffix):
        text = text[: -len(suffix)]
    return _clean_text(text, limit=300) or component.component_id


def build_question_meaning_record_from_search_work_plan(
    *,
    assessment: QueryShapeAssessment,
    route_facts: Mapping[str, Any],
    run_contract_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
    query: str,
    requested_mode: str,
) -> QuestionMeaningRecord | None:
    component_candidates = tuple(assessment.component_candidates)
    if not component_candidates or len(component_candidates) > ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP:
        return None
    slots: list[SemanticSlot] = []
    components: list[AnswerComponentContract] = []
    for candidate in component_candidates:
        slot = _semantic_slot_for_component(component=candidate, route_facts=route_facts)
        slots.append(slot)
        components.append(
            _answer_component_from_candidate(
                candidate,
                semantic_slot_ids=(slot.slot_id,),
            )
        )
    intent = (
        _clean_text(route_facts.get("intent"), limit=200)
        or _clean_text(query, limit=200)
        or "Answer the user question."
    )
    contract_id = _clean_token(run_contract_projection.get("contract_id")) or run_id
    return QuestionMeaningRecord.from_query_shape_assessment(
        record_id=f"qmr:{contract_id}:ag-sem-11",
        run_id=run_id,
        request_id=request_id,
        request_digest=_request_digest(query=query, run_id=run_id),
        requested_mode=_clean_token(requested_mode) or "balanced",
        intent=intent,
        requested_output="Concise evidence-bound answer for the required components.",
        semantic_slots=tuple(slots),
        answer_components=tuple(components),
        assessment=assessment,
        resolver_version=ORDINARY_SEMANTIC_PRODUCER_RESOLVER_VERSION,
        metadata={
            "phase": "AG-SEM-MULTI-01",
            "ordinary_semantic_producer": True,
            "bounded_component_cap": ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP,
            "explicit_factual_component_list": bool(
                _safe_mapping(assessment.metadata).get(
                    "explicit_factual_component_list"
                )
            ),
            "requested_synthesis_directive": _clean_text(
                _safe_mapping(assessment.metadata).get(
                    "requested_synthesis_directive"
                ),
                limit=360,
            ),
        },
    ).require_valid()


def _ledger_candidate_index(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in evidence_ledger_projection.get("candidate_records") or ():
        if not isinstance(record, Mapping):
            continue
        candidate_id = _clean_token(record.get("candidate_id"))
        if candidate_id:
            index[candidate_id] = dict(record)
        url = _normalize_url(record.get("url"))
        if url:
            index.setdefault(url, dict(record))
    return index


_STALE_CURRENTNESS_SIGNALS = frozenset({"stale", "outdated", "expired", "superseded"})
_IMPLICIT_COMPATIBILITY_LINK_REASON = (
    "selected_candidate_matches_existing_requirement"
)


def _candidate_is_bindable(
    candidate: Mapping[str, Any],
    *,
    passage: Mapping[str, Any] | None = None,
) -> bool:
    disposition = (_clean_token(candidate.get("fact_disposition")) or "unknown").casefold()
    if disposition in {"rejected", "dropped", "unreadable", "unfetchable"}:
        return False
    if disposition and disposition not in _ACCEPTED_DISPOSITIONS and disposition != "unknown":
        return False
    readable = (_clean_token(candidate.get("readable_status")) or "readable").casefold()
    if readable not in _READABLE_STATUSES:
        return False
    if candidate.get("contextual_only") is True:
        return False
    if candidate.get("lower_tier") is True:
        return False
    currentness = (
        _clean_token(candidate.get("currentness_signal"))
        or (_clean_token(passage.get("currentness_signal")) if passage else None)
        or (_clean_token(passage.get("currentness")) if passage else None)
    )
    if currentness and currentness.casefold() in _STALE_CURRENTNESS_SIGNALS:
        return False
    return True


def select_bindable_final_passage(
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
) -> BindableFinalPassage | None:
    if not final_top_evidence:
        return None
    candidate_index = _ledger_candidate_index(evidence_ledger_projection)
    for index, raw_passage in enumerate(final_top_evidence, start=1):
        if not isinstance(raw_passage, Mapping):
            continue
        passage = dict(raw_passage)
        bounded_text = _clean_text(passage.get("text"), limit=MAX_BOUNDED_TEXT_CHARS)
        if not bounded_text:
            continue
        candidate_id = _passage_candidate_id(passage, index=index)
        if not candidate_id:
            continue
        candidate = candidate_index.get(candidate_id)
        if candidate is None:
            url = _normalize_url(passage.get("url"))
            if url:
                candidate = candidate_index.get(url)
        if candidate is None or not _candidate_is_bindable(candidate, passage=passage):
            continue
        evidence_ref_id = _clean_token(candidate.get("candidate_id")) or candidate_id
        return BindableFinalPassage(
            passage=passage,
            evidence_ref_id=evidence_ref_id,
            candidate_record=dict(candidate),
        )
    return None


def _token_overlap_score(
    *,
    component_ref: Mapping[str, Any],
    bindable: BindableFinalPassage,
    component_text: str | None = None,
) -> int:
    label_text = (
        component_text
        or " ".join(
            str(value or "")
            for value in (
                component_ref.get("user_facing_label"),
                component_ref.get("user_facing_question"),
            )
        )
    ).casefold()
    passage_text = " ".join(
        str(value or "")
        for value in (
            bindable.passage.get("title"),
            bindable.passage.get("text"),
        )
    ).casefold()
    tokens = {
        token.strip(".,:;!?()[]")
        for token in label_text.split()
        if len(token.strip(".,:;!?()[]")) >= 4
    }
    return sum(1 for token in tokens if token and token in passage_text)


def _bindable_final_passages(
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
) -> tuple[BindableFinalPassage, ...]:
    if not final_top_evidence:
        return ()
    bindables: list[BindableFinalPassage] = []
    candidate_index = _ledger_candidate_index(evidence_ledger_projection)
    for index, raw_passage in enumerate(final_top_evidence, start=1):
        if not isinstance(raw_passage, Mapping):
            continue
        passage = dict(raw_passage)
        bounded_text = _clean_text(passage.get("text"), limit=MAX_BOUNDED_TEXT_CHARS)
        if not bounded_text:
            continue
        candidate_id = _passage_candidate_id(passage, index=index)
        if not candidate_id:
            continue
        candidate = candidate_index.get(candidate_id)
        if candidate is None:
            url = _normalize_url(passage.get("url"))
            if url:
                candidate = candidate_index.get(url)
        if candidate is None or not _candidate_is_bindable(candidate, passage=passage):
            continue
        evidence_ref_id = _clean_token(candidate.get("candidate_id")) or candidate_id
        bindables.append(
            BindableFinalPassage(
                passage=passage,
                evidence_ref_id=evidence_ref_id,
                candidate_record=dict(candidate),
            )
        )
    return tuple(bindables)


def select_bindable_final_passages_for_components(
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
    component_refs: Sequence[Mapping[str, Any]],
    component_text_by_id: Mapping[str, str] | None = None,
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    answer_contract_version: Any = None,
    answer_contract_digest: str | None = None,
) -> dict[str, BindableFinalPassage]:
    bindables = _bindable_final_passages(final_top_evidence, evidence_ledger_projection)
    if not bindables:
        return {}
    obligation_signatures = [
        tuple(
            obligation_id
            for obligation_id in (
                _clean_token(item)
                for item in (
                    ref.get("source_obligation_candidate_ids")
                    or ref.get("source_obligation_candidate_refs")
                    or ()
                )
            )
            if obligation_id
        )
        for ref in component_refs
        if isinstance(ref, Mapping)
    ]
    shared_obligation_shape = len(component_refs) > 1 and len(set(obligation_signatures)) < len(component_refs)
    used_evidence_refs: set[str] = set()
    selected: dict[str, BindableFinalPassage] = {}
    for component_ref in component_refs:
        component_id = _clean_token(component_ref.get("component_id"))
        if not component_id:
            continue
        obligation_ids = tuple(
            obligation_id
            for obligation_id in (
                _clean_token(item)
                for item in (
                    component_ref.get("source_obligation_candidate_ids")
                    or component_ref.get("source_obligation_candidate_refs")
                    or ()
                )
            )
            if obligation_id
        )
        scored: list[tuple[int, int, BindableFinalPassage]] = []
        for order, bindable in enumerate(bindables):
            source_requirement_ids = _exact_owned_source_requirement_ids_for_candidate(
                evidence_ledger_projection,
                evidence_ref_id=bindable.evidence_ref_id,
                component_id=component_id,
                source_obligation_candidate_ids=obligation_ids,
                run_id=run_id,
                request_id=request_id,
                answer_contract_version=answer_contract_version,
                answer_contract_digest=answer_contract_digest,
            )
            score = _token_overlap_score(
                component_ref=component_ref,
                bindable=bindable,
                component_text=(
                    _clean_text((component_text_by_id or {}).get(component_id), limit=500)
                    if component_text_by_id
                    else None
                ),
            )
            if shared_obligation_shape and score <= 0:
                continue
            if source_requirement_ids:
                score += 100
            if bindable.evidence_ref_id not in used_evidence_refs:
                score += 10
            scored.append((score, -order, bindable))
        if not scored:
            continue
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected_bindable = scored[0][2]
        selected[component_id] = selected_bindable
        used_evidence_refs.add(selected_bindable.evidence_ref_id)
    return selected


def source_requirement_ids_for_component_candidate(
    evidence_ledger_projection: Mapping[str, Any],
    *,
    evidence_ref_id: str,
    component_id: str | None = None,
    source_obligation_candidate_ids: Sequence[str] = (),
    run_id: str | None = None,
    request_id: str | None = None,
    answer_contract_version: Any = None,
    answer_contract_digest: str | None = None,
    ignore_satisfied_provider_job_historical_gaps: bool = False,
) -> tuple[str, ...]:
    """Expose exact scoped preflight or retained unscoped compatibility lookup."""

    lookup = (
        _exact_owned_source_requirement_ids_for_candidate
        if component_id
        else _compatibility_source_requirement_ids_for_candidate
    )
    return lookup(
        evidence_ledger_projection,
        evidence_ref_id=evidence_ref_id,
        **(
            {
                "component_id": component_id,
                "run_id": run_id,
                "request_id": request_id,
                "answer_contract_version": answer_contract_version,
                "answer_contract_digest": answer_contract_digest,
            }
            if component_id
            else {}
        ),
        source_obligation_candidate_ids=source_obligation_candidate_ids,
        ignore_satisfied_provider_job_historical_gaps=(
            ignore_satisfied_provider_job_historical_gaps
        ),
    )


def _accepted_component_ref(
    accepted_contract: Mapping[str, Any],
    answer_component_id: str,
) -> Mapping[str, Any]:
    for component_ref in accepted_contract.get("accepted_answer_component_refs") or ():
        if (
            isinstance(component_ref, Mapping)
            and _clean_token(component_ref.get("component_id")) == answer_component_id
        ):
            return component_ref
    raise KeyError(f"accepted component ref not found: {answer_component_id}")


def build_sanitized_content_reference_from_passage(
    *,
    passage: Mapping[str, Any],
    evidence_ref_id: str,
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any] | None = None,
    content_ref_id: str,
) -> SanitizedContentReference:
    if component_ref is None:
        component_ref = accepted_contract["accepted_answer_component_refs"][0]
    url = _clean_text(passage.get("url"), limit=400)
    title = _clean_text(passage.get("title"), limit=220) or "Selected evidence"
    source_id = _clean_token(passage.get("source_id"))
    bounded_text = _clean_text(passage.get("text"), limit=MAX_BOUNDED_TEXT_CHARS)
    if not bounded_text:
        raise ValueError("sanitized content reference requires bounded passage text")
    metadata: dict[str, Any] = {
        "phase": "AG-SEM-11",
        "ordinary_semantic_producer": True,
    }
    if passage.get("bounded_text_digest"):
        metadata["bounded_text_digest"] = passage.get(
            "bounded_text_digest"
        )
    return SanitizedContentReference(
        content_ref_id=content_ref_id,
        evidence_ref_id=evidence_ref_id,
        admitted_evidence_ref=evidence_ref_id,
        source_id=source_id,
        source_digest=(
            hashlib.sha256(f"{url or title}".encode("utf-8")).hexdigest()[:16]
            if url or title
            else None
        ),
        source_url=url,
        source_title=title,
        source_domain=_domain_from_url(url),
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        question_meaning_record_id=accepted_contract["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted_contract["parent_question_meaning_record_digest"],
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=bounded_text,
        extraction_method="ordinary_semantic_producer_final_top_evidence",
        worker_kind="bounded_passage_projection",
        currentness=_clean_token(passage.get("currentness_signal") or passage.get("currentness")),
        metadata=metadata,
    ).require_valid()


def _requirement_ids_blocked_by_custody_gaps(
    evidence_ledger_projection: Mapping[str, Any],
    *,
    ignore_satisfied_provider_job_historical_gaps: bool = False,
) -> set[str]:
    current_status_by_id = {
        _clean_token(item.get("requirement_id")): (
            _clean_token(item.get("status")) or ""
        ).casefold()
        for item in evidence_ledger_projection.get("source_requirements") or ()
        if isinstance(item, Mapping) and _clean_token(item.get("requirement_id"))
    }
    blocked: set[str] = set()
    for gap in evidence_ledger_projection.get("custody_gaps") or ():
        if not isinstance(gap, Mapping):
            continue
        requirement_id = _clean_token(gap.get("requirement_id"))
        if (
            ignore_satisfied_provider_job_historical_gaps
            and requirement_id
            and requirement_id.startswith("provider_job_requirement:")
            and current_status_by_id.get(requirement_id) == "satisfied"
        ):
            continue
        if requirement_id:
            blocked.add(requirement_id)
    return blocked


def _requirement_matches_obligation_candidate(
    requirement: Mapping[str, Any],
    obligation_candidate_id: str,
) -> bool:
    obligation = (_clean_token(obligation_candidate_id) or "").casefold()
    if not obligation:
        return False
    requirement_id = (_clean_token(requirement.get("requirement_id")) or "").casefold()
    if obligation in requirement_id or obligation.removeprefix("obligation:") in requirement_id:
        return True
    obligation_kind = obligation.split(":", 1)[-1]
    requirement_kind = (_clean_token(requirement.get("requirement_kind")) or "").casefold()
    if obligation_kind and requirement_kind == obligation_kind:
        return True
    origin_ref = (_clean_token(requirement.get("origin_ref")) or "").casefold()
    if obligation_kind and obligation_kind in origin_ref:
        return True
    return False


def _compatibility_source_requirement_ids_for_candidate(
    evidence_ledger_projection: Mapping[str, Any],
    *,
    evidence_ref_id: str,
    source_obligation_candidate_ids: Sequence[str] = (),
    ignore_satisfied_provider_job_historical_gaps: bool = False,
) -> tuple[str, ...]:
    """Retained non-authoritative lookup for legacy unscoped callers only."""

    normalized_evidence_ref = _clean_token(evidence_ref_id) or ""
    if not normalized_evidence_ref:
        return ()

    requirements_by_id: dict[str, dict[str, Any]] = {}
    for requirement in evidence_ledger_projection.get("source_requirements") or ():
        if not isinstance(requirement, Mapping):
            continue
        requirement_id = _clean_token(requirement.get("requirement_id"))
        if requirement_id:
            requirements_by_id[requirement_id] = dict(requirement)

    linked_requirement_ids: list[str] = []
    for link in evidence_ledger_projection.get("requirement_links") or ():
        if not isinstance(link, Mapping):
            continue
        if _clean_token(link.get("candidate_id")) != normalized_evidence_ref:
            continue
        requirement_id = _clean_token(link.get("requirement_id"))
        if requirement_id:
            linked_requirement_ids.append(requirement_id)

    if not linked_requirement_ids:
        for requirement_id, requirement in requirements_by_id.items():
            linked_candidates = requirement.get("linked_candidate_ids") or ()
            if normalized_evidence_ref in {
                _clean_token(candidate_id)
                for candidate_id in linked_candidates
                if _clean_token(candidate_id)
            }:
                linked_requirement_ids.append(requirement_id)

    ordered_linked: list[str] = []
    seen: set[str] = set()
    for requirement_id in linked_requirement_ids:
        if requirement_id not in seen:
            seen.add(requirement_id)
            ordered_linked.append(requirement_id)

    obligation_ids = tuple(
        obligation_id
        for obligation_id in (_clean_token(item) for item in source_obligation_candidate_ids)
        if obligation_id
    )
    satisfied_linked: list[str] = []
    for requirement_id in ordered_linked:
        requirement = requirements_by_id.get(requirement_id)
        if requirement is None:
            continue
        if (_clean_token(requirement.get("status")) or "").casefold() != "satisfied":
            continue
        if obligation_ids and not any(
            _requirement_matches_obligation_candidate(requirement, obligation_id)
            for obligation_id in obligation_ids
        ):
            continue
        satisfied_linked.append(requirement_id)
    blocked_requirement_ids = _requirement_ids_blocked_by_custody_gaps(
        evidence_ledger_projection,
        ignore_satisfied_provider_job_historical_gaps=(
            ignore_satisfied_provider_job_historical_gaps
        ),
    )
    return tuple(
        requirement_id
        for requirement_id in dict.fromkeys(satisfied_linked)
        if requirement_id not in blocked_requirement_ids
    )


def _owned_identity(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .casefold()
        .replace("-", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def _exact_owned_source_requirement_ids_for_candidate(
    evidence_ledger_projection: Mapping[str, Any],
    *,
    evidence_ref_id: str,
    component_id: str,
    source_obligation_candidate_ids: Sequence[str],
    run_id: str | None,
    request_id: str | None,
    answer_contract_version: Any,
    answer_contract_digest: str | None,
    ignore_satisfied_provider_job_historical_gaps: bool = False,
) -> tuple[str, ...]:
    """Return only unique, explicitly linked, exact-owned satisfied rows."""

    candidate_id = _clean_token(evidence_ref_id)
    component_identity = _owned_identity(component_id)
    run_identity = _owned_identity(run_id)
    request_identity = _owned_identity(request_id)
    contract_version = _clean_token(answer_contract_version)
    contract_digest = _clean_token(answer_contract_digest)
    obligation_identities = {
        identity
        for item in source_obligation_candidate_ids
        if (identity := _owned_identity(item))
    }
    if (
        not candidate_id
        or not component_identity
        or not obligation_identities
        or not run_identity
        or not request_identity
        or not contract_version
        or not contract_digest
    ):
        return ()

    candidate_rows = [
        dict(item)
        for item in evidence_ledger_projection.get("candidate_records") or ()
        if isinstance(item, Mapping)
        and _clean_token(item.get("candidate_id")) == candidate_id
    ]
    if len(candidate_rows) != 1:
        return ()
    if (
        _clean_token(
            candidate_rows[0].get("fact_disposition")
            or candidate_rows[0].get("disposition")
        )
        or ""
    ).casefold() != "accepted":
        return ()

    requirement_rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_ledger_projection.get("source_requirements") or ():
        if not isinstance(item, Mapping):
            continue
        requirement_id = _clean_token(item.get("requirement_id"))
        if requirement_id:
            requirement_rows_by_id.setdefault(requirement_id, []).append(dict(item))

    accepted_links_by_requirement_id: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_ledger_projection.get("requirement_links") or ():
        if not isinstance(item, Mapping):
            continue
        if _clean_token(item.get("candidate_id")) != candidate_id:
            continue
        requirement_id = _clean_token(item.get("requirement_id"))
        if requirement_id:
            accepted_links_by_requirement_id.setdefault(
                requirement_id, []
            ).append(dict(item))

    blocked_requirement_ids = _requirement_ids_blocked_by_custody_gaps(
        evidence_ledger_projection,
        ignore_satisfied_provider_job_historical_gaps=(
            ignore_satisfied_provider_job_historical_gaps
        ),
    )
    exact_ids: list[str] = []
    for requirement_id, links in accepted_links_by_requirement_id.items():
        rows = requirement_rows_by_id.get(requirement_id, [])
        if (
            len(rows) != 1
            or len(links) != 1
            or (_clean_token(links[0].get("link_status")) or "").casefold()
            != "accepted"
            or (
                _clean_token(links[0].get("link_reason")) or ""
            ).casefold()
            == _IMPLICIT_COMPATIBILITY_LINK_REASON
        ):
            continue
        requirement = rows[0]
        if (
            (_clean_token(requirement.get("status")) or "").casefold()
            != "satisfied"
            or _owned_identity(requirement.get("component_id"))
            != component_identity
            or _owned_identity(requirement.get("source_obligation_id"))
            not in obligation_identities
            or _owned_identity(requirement.get("run_id"))
            != run_identity
            or _owned_identity(requirement.get("request_id"))
            != request_identity
            or _clean_token(requirement.get("answer_contract_version"))
            != contract_version
            or _clean_token(requirement.get("answer_contract_digest"))
            != contract_digest
            or requirement_id in blocked_requirement_ids
        ):
            continue
        exact_ids.append(requirement_id)
    preferred = tuple(
        requirement_id
        for requirement_id in exact_ids
        if requirement_id.startswith("searchos_semantic_requirement:")
    )
    return preferred or tuple(exact_ids)


def _source_requirements_by_id(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    requirements: dict[str, dict[str, Any]] = {}
    for requirement in evidence_ledger_projection.get("source_requirements") or ():
        if not isinstance(requirement, Mapping):
            continue
        requirement_id = _clean_token(requirement.get("requirement_id"))
        if requirement_id:
            requirements[requirement_id] = dict(requirement)
    return requirements


def _coverage_currentness_posture(
    evidence_ledger_projection: Mapping[str, Any],
    *,
    source_requirement_ids: Sequence[str],
) -> CurrentnessPosture:
    if not source_requirement_ids:
        return CurrentnessPosture.NOT_TIME_SENSITIVE
    requirements = _source_requirements_by_id(evidence_ledger_projection)
    for requirement_id in source_requirement_ids:
        requirement = requirements.get(requirement_id, {})
        currentness = (
            _clean_token(requirement.get("required_currentness"))
            or _clean_token(requirement.get("currentness_requirement"))
        )
        if currentness and currentness.casefold() in {"current", "official_current"}:
            return CurrentnessPosture.CURRENT
    return CurrentnessPosture.NOT_TIME_SENSITIVE


def _direct_coverage_boundary_text(
    *,
    currentness_posture: CurrentnessPosture,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    caveats = ["Answer remains evidence-bound."]
    if currentness_posture is CurrentnessPosture.CURRENT:
        caveats.append("Currentness remains evidence-bound.")
    return (
        tuple(caveats),
        ("Do not replace direct source-bound evidence with an estimate.",),
    )


def build_semantic_observation_and_content_refs(
    *,
    accepted_contract: Mapping[str, Any],
    bindable: BindableFinalPassage,
    component_ref: Mapping[str, Any] | None = None,
) -> tuple[SemanticObservation, tuple[SanitizedContentReference, ...]]:
    if component_ref is None:
        component_ref = accepted_contract["accepted_answer_component_refs"][0]
    component_id = _clean_token(component_ref.get("component_id")) or "component"
    content_ref_id = f"content:{component_id}:{bindable.evidence_ref_id}"
    content_ref = build_sanitized_content_reference_from_passage(
        passage=bindable.passage,
        evidence_ref_id=bindable.evidence_ref_id,
        accepted_contract=accepted_contract,
        component_ref=component_ref,
        content_ref_id=content_ref_id,
    )
    claim = _clean_text(bindable.passage.get("text"), limit=180) or "supported by selected evidence"
    observation = SemanticObservation(
        observation_id=f"observation:{component_id}:{bindable.evidence_ref_id}",
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted_contract["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted_contract["parent_question_meaning_record_digest"],
        contract_version=accepted_contract["accepted_contract_version"],
        contract_digest=accepted_contract["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        evidence_refs=(bindable.evidence_ref_id,),
        content_refs=(content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value=claim,
        normalization_fit="direct source-bound wording",
        scope_fit="answer component",
        assumption_fit="bounded selected evidence excerpt",
        inference_depth=0,
        metadata={"phase": "AG-SEM-MULTI-01", "ordinary_semantic_producer": True},
    ).require_valid()
    return observation, (content_ref,)


def build_component_coverage_proposal(
    *,
    accepted_contract: Mapping[str, Any],
    observation: SemanticObservation,
    content_ref: SanitizedContentReference,
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
    query: str,
    ignore_satisfied_provider_job_historical_gaps: bool = False,
) -> ComponentCoverageRecord | None:
    component_ref = _accepted_component_ref(
        accepted_contract,
        observation.answer_component_id,
    )
    source_obligation_candidate_ids = tuple(
        obligation_id
        for obligation_id in (
            _clean_token(item)
            for item in (
                component_ref.get("source_obligation_candidate_ids")
                or component_ref.get("source_obligation_candidate_refs")
                or ()
            )
        )
        if obligation_id
    )
    has_source_obligations = bool(source_obligation_candidate_ids)
    if has_source_obligations:
        if not observation.evidence_refs:
            return None
        source_requirement_ids = _exact_owned_source_requirement_ids_for_candidate(
            evidence_ledger_projection,
            evidence_ref_id=observation.evidence_refs[0],
            component_id=component_ref["component_id"],
            source_obligation_candidate_ids=source_obligation_candidate_ids,
            run_id=run_id,
            request_id=request_id,
            answer_contract_version=accepted_contract[
                "accepted_contract_version"
            ],
            answer_contract_digest=accepted_contract[
                "accepted_contract_digest"
            ],
            ignore_satisfied_provider_job_historical_gaps=(
                ignore_satisfied_provider_job_historical_gaps
            ),
        )
        if not source_requirement_ids:
            return None
        source_obligation_status = SourceObligationStatus.SATISFIED
    else:
        source_requirement_ids = ()
        source_obligation_status = SourceObligationStatus.NOT_APPLICABLE
    currentness_posture = _coverage_currentness_posture(
        evidence_ledger_projection,
        source_requirement_ids=source_requirement_ids,
    )
    caveats, prohibited_upgrades = _direct_coverage_boundary_text(
        currentness_posture=currentness_posture,
    )
    ledger_digest = evidence_ledger_projection_digest(evidence_ledger_projection)
    observation_refs = (
        SemanticObservationCoverageRef(
            observation_id=observation.observation_id,
            observation_digest=observation.observation_digest,
            answer_component_id=component_ref["component_id"],
            component_revision=component_ref["component_revision"],
            component_contract_digest=component_ref["component_digest"],
            support_status="supports",
            support_posture=SupportPosture.DIRECT,
            content_refs=(content_ref.content_ref_id,),
            accepted=True,
        ),
    )
    content_binding = ContentReferenceCoverageBinding.from_content_reference(content_ref)
    ledger_binding = EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{run_id}:{ledger_digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=ledger_digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        source_requirement_ids=source_requirement_ids,
        ledger_observation_refs=tuple(
            _clean_token(ref.get("observation_id"))
            for ref in evidence_ledger_projection.get("observation_refs") or ()
            if isinstance(ref, Mapping) and _clean_token(ref.get("observation_id"))
        ),
        version_validity=VersionValidity.VALID,
    )
    record = ComponentCoverageRecord(
        record_id=f"coverage:{component_ref['component_id']}",
        run_id=run_id,
        request_id=request_id,
        request_digest=_request_digest(query=query, run_id=run_id),
        accepted_contract_version=accepted_contract["accepted_contract_version"],
        accepted_contract_digest=accepted_contract["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=ledger_binding,
        coverage_state=CoverageState.SATISFIED,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=source_obligation_status,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=observation_refs,
        content_reference_bindings=(content_binding,),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        conflict_posture=ConflictPosture.NONE,
        currentness_posture=currentness_posture,
        required_caveats=caveats,
        prohibited_upgrades=prohibited_upgrades,
        followup_need=FollowupNeed.NONE,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        stale=False,
        metadata={"phase": "AG-SEM-11", "ordinary_semantic_producer": True},
    ).require_valid()
    blockers = ledger_qualification_blockers_for_satisfied_coverage(
        coverage=record.to_dict(),
        evidence_ledger_projection=evidence_ledger_projection,
        accepted_component=component_ref,
        extra_evidence_refs=observation.evidence_refs,
    )
    if blockers:
        return None
    return record


def _dry_run_accepted_contract(
    *,
    qmr: QuestionMeaningRecord,
    run_id: str,
    request_id: str,
) -> dict[str, Any] | None:
    try:
        return build_initial_answer_contract_acceptance_state(
            action_id=_PREFLIGHT_ACTION_ID,
            action_inputs={
                "parent_question_meaning_record_id": qmr.record_id,
                "parent_proposal_digest": qmr.record_digest,
                "request_id": request_id,
            },
            question_meaning_record=qmr.to_dict(),
            run_id=run_id,
            request_id=request_id,
        )
    except Exception:
        return None


def _dry_run_admission_projection(
    *,
    accepted_contract: Mapping[str, Any],
    observation: SemanticObservation,
    content_refs: Sequence[SanitizedContentReference],
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
) -> dict[str, Any] | None:
    component_ref = _accepted_component_ref(
        accepted_contract,
        observation.answer_component_id,
    )
    try:
        state = build_semantic_observation_admission_state(
            action_id=_PREFLIGHT_ACTION_ID,
            action_inputs={
                "semantic_observation_id": observation.observation_id,
                "semantic_observation_digest": observation.observation_digest,
                "accepted_contract_digest": accepted_contract["accepted_contract_digest"],
                "accepted_contract_version": accepted_contract["accepted_contract_version"],
                "answer_component_id": component_ref["component_id"],
                "component_revision": component_ref["component_revision"],
                "component_digest": component_ref["component_digest"],
                "request_id": request_id,
            },
            observation_payload={
                "semantic_observation": observation.to_dict(),
                "sanitized_content_references": [ref.to_dict() for ref in content_refs],
            },
            accepted_contract=accepted_contract,
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=run_id,
            request_id=request_id,
        )
    except Exception:
        return None
    return dict(state)


def _dry_run_coverage_state(
    *,
    accepted_contract: Mapping[str, Any],
    admission_projection: Mapping[str, Any],
    coverage_record: ComponentCoverageRecord,
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
) -> dict[str, Any] | None:
    component_ref = _accepted_component_ref(
        accepted_contract,
        coverage_record.answer_component_id,
    )
    try:
        return build_component_coverage_reduction_state(
            action_id=_PREFLIGHT_ACTION_ID,
            action_inputs={
                "coverage_record_id": coverage_record.record_id,
                "coverage_record_digest": coverage_record.record_digest,
                "accepted_contract_digest": accepted_contract["accepted_contract_digest"],
                "accepted_contract_version": accepted_contract["accepted_contract_version"],
                "answer_component_id": component_ref["component_id"],
                "component_revision": component_ref["component_revision"],
                "component_digest": component_ref["component_digest"],
                "request_id": request_id,
            },
            coverage_payload={"component_coverage_record": coverage_record.to_dict()},
            accepted_contract=accepted_contract,
            admission_history=[admission_projection],
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=run_id,
            request_id=request_id,
        )
    except Exception:
        return None


def preflight_ordinary_semantic_producer_bundle(
    *,
    search_work_plan: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None,
    run_contract_projection: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
    query: str,
    requested_mode: str | None = None,
) -> OrdinarySemanticProducerPreflightResult:
    if not _search_work_plan_uses_real_query_shape_classifier(search_work_plan):
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE,
        )
    contract_id = _clean_token(run_contract_projection.get("contract_id")) or run_id
    route_facts = _safe_mapping(route_projection)
    try:
        records = build_deterministic_search_work_runtime_records(
            DeterministicSearchWorkRuntimeInput(
                contract_id=contract_id,
                run_contract_projection=run_contract_projection,
                route_facts=route_facts,
                requested_mode=requested_mode or run_contract_projection.get("selected_depth"),
                selected_depth=run_contract_projection.get("selected_depth"),
                safe_query_preview=query,
            )
        )
    except Exception:
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_PREFLIGHT_FAILED,
        )
    component_count = len(records.query_shape_assessment.component_candidates)
    if component_count > ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP:
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_COMPONENT_CAP_EXCEEDED,
        )
    qmr = build_question_meaning_record_from_search_work_plan(
        assessment=records.query_shape_assessment,
        route_facts=route_facts,
        run_contract_projection=run_contract_projection,
        run_id=run_id,
        request_id=request_id,
        query=query,
        requested_mode=requested_mode or str(run_contract_projection.get("selected_depth") or "balanced"),
    )
    if qmr is None:
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_PREFLIGHT_FAILED,
        )
    accepted_contract = _dry_run_accepted_contract(
        qmr=qmr,
        run_id=run_id,
        request_id=request_id,
    )
    if accepted_contract is None:
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_CONTRACT_PREFLIGHT_FAILED,
        )
    component_refs = tuple(
        component_ref
        for component_ref in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(component_ref, Mapping) and _clean_token(component_ref.get("component_id"))
    )
    component_text_by_id = {
        component.component_id: _component_matching_text(component)
        for component in qmr.answer_components
    }
    selected_bindables = select_bindable_final_passages_for_components(
        final_top_evidence,
        evidence_ledger_projection,
        component_refs,
        component_text_by_id=component_text_by_id,
        run_id=run_id,
        request_id=request_id,
        answer_contract_version=accepted_contract[
            "accepted_contract_version"
        ],
        answer_contract_digest=accepted_contract[
            "accepted_contract_digest"
        ],
    )
    if not selected_bindables:
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=SKIP_REASON_BINDABLE_PASSAGE_MISSING,
        )
    component_bundles: list[OrdinarySemanticProducerComponentBundle] = []
    saw_admission_failure = False
    saw_coverage_failure = False
    for component_ref in component_refs:
        component_id = _clean_token(component_ref.get("component_id"))
        if not component_id:
            continue
        bindable = selected_bindables.get(component_id)
        if bindable is None:
            continue
        try:
            observation, content_refs = build_semantic_observation_and_content_refs(
                accepted_contract=accepted_contract,
                bindable=bindable,
                component_ref=component_ref,
            )
        except Exception:
            saw_admission_failure = True
            continue
        admission_projection = _dry_run_admission_projection(
            accepted_contract=accepted_contract,
            observation=observation,
            content_refs=content_refs,
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=run_id,
            request_id=request_id,
        )
        if admission_projection is None:
            saw_admission_failure = True
            continue
        coverage_record = build_component_coverage_proposal(
            accepted_contract=accepted_contract,
            observation=observation,
            content_ref=content_refs[0],
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=run_id,
            request_id=request_id,
            query=query,
        )
        if coverage_record is None:
            saw_coverage_failure = True
            continue
        if (
            _dry_run_coverage_state(
                accepted_contract=accepted_contract,
                admission_projection=admission_projection,
                coverage_record=coverage_record,
                evidence_ledger_projection=evidence_ledger_projection,
                run_id=run_id,
                request_id=request_id,
            )
            is None
        ):
            saw_coverage_failure = True
            continue
        component_bundles.append(
            OrdinarySemanticProducerComponentBundle(
                answer_component_id=component_id,
                semantic_observation=observation,
                sanitized_content_references=content_refs,
                component_coverage_record=coverage_record,
                dry_run_admission_projection=admission_projection,
            )
        )
    if not component_bundles:
        skipped_reason = (
            SKIP_REASON_ADMISSION_PREFLIGHT_FAILED
            if saw_admission_failure and not saw_coverage_failure
            else SKIP_REASON_COVERAGE_PREFLIGHT_FAILED
        )
        return OrdinarySemanticProducerPreflightResult(
            bundle=None,
            skipped_reason=skipped_reason,
        )
    return OrdinarySemanticProducerPreflightResult(
        bundle=OrdinarySemanticProducerBundle(
            question_meaning_record=qmr,
            component_bundles=tuple(component_bundles),
            dry_run_accepted_contract=accepted_contract,
        ),
    )


def build_ordinary_semantic_producer_bundle(
    *,
    search_work_plan: Mapping[str, Any],
    route_projection: Mapping[str, Any] | None,
    run_contract_projection: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_ledger_projection: Mapping[str, Any],
    run_id: str,
    request_id: str,
    query: str,
    requested_mode: str | None = None,
) -> OrdinarySemanticProducerBundle | None:
    return preflight_ordinary_semantic_producer_bundle(
        search_work_plan=search_work_plan,
        route_projection=route_projection,
        run_contract_projection=run_contract_projection,
        final_top_evidence=final_top_evidence,
        evidence_ledger_projection=evidence_ledger_projection,
        run_id=run_id,
        request_id=request_id,
        query=query,
        requested_mode=requested_mode,
    ).bundle


def _semantic_state_already_present(run_kernel: Any) -> bool:
    state = run_kernel.state
    return bool(
        state.initial_answer_contract
        or state.semantic_observation_admission_history
        or state.component_coverage_history
    )


def execute_ordinary_semantic_producer_handoff_from_scope(
    run_kernel: Any,
    runtime_scope: Mapping[str, Any],
) -> OrdinarySemanticProducerHandoffResult:
    del runtime_scope
    if _semantic_state_already_present(run_kernel):
        return OrdinarySemanticProducerHandoffResult(
            status=OrdinarySemanticProducerHandoffStatus.SKIPPED,
            skipped_reason=SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT,
        )
    return OrdinarySemanticProducerHandoffResult(
        status=OrdinarySemanticProducerHandoffStatus.SKIPPED,
        skipped_reason=SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING,
    )


__all__ = [
    "ORDINARY_SEMANTIC_PRODUCER_RESOLVER_VERSION",
    "ORDINARY_SEMANTIC_PRODUCER_SCHEMA_VERSION",
    "ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP",
    "SKIP_REASON_ADMISSION_PREFLIGHT_FAILED",
    "SKIP_REASON_BINDABLE_PASSAGE_MISSING",
    "SKIP_REASON_CANONICAL_SEMANTIC_STATE_ALREADY_PRESENT",
    "SKIP_REASON_COMPONENT_CAP_EXCEEDED",
    "SKIP_REASON_CONTRACT_PREFLIGHT_FAILED",
    "SKIP_REASON_COVERAGE_PREFLIGHT_FAILED",
    "SKIP_REASON_MULTIPART_ASSESSMENT",
    "SKIP_REASON_PREFLIGHT_FAILED",
    "SKIP_REASON_QUERY_SHAPE_CLASSIFIER_UNAVAILABLE",
    "SKIP_REASON_ACCEPTED_ANSWER_CONTRACT_MISSING",
    "BindableFinalPassage",
    "OrdinarySemanticProducerBundle",
    "OrdinarySemanticProducerComponentBundle",
    "OrdinarySemanticProducerHandoffResult",
    "OrdinarySemanticProducerHandoffStatus",
    "OrdinarySemanticProducerPreflightResult",
    "OrdinarySemanticProducerTransactionError",
    "build_component_coverage_proposal",
    "build_ordinary_semantic_producer_bundle",
    "build_question_meaning_record_from_search_work_plan",
    "build_sanitized_content_reference_from_passage",
    "build_semantic_observation_and_content_refs",
    "execute_ordinary_semantic_producer_handoff_from_scope",
    "preflight_ordinary_semantic_producer_bundle",
    "select_bindable_final_passage",
    "select_bindable_final_passages_for_components",
    "source_requirement_ids_for_component_candidate",
]
