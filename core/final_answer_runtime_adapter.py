"""Runtime adapter for AG-89D FinalAnswerPacket construction and projection."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

from core.citation_source_handoff_contract import build_citation_source_handoff_state
from core.final_answer_packet import (
    FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION,
    FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION,
    FINAL_ANSWER_PACKET_TRACE_KEY,
    FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    ClaimPosture,
    EvidenceAuthorityStatus,
    FinalAnswerAuthorInputPayload,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
    FinalEvidenceRecord,
    SourceObligationRecord,
    SourceObligationStatus,
    semantic_packet_evidence_binding_digest,
)
from core.official_current_source_custody import OfficialCurrentSourceCustodyState
from core.run_authority_projection_refs import (
    RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER,
    canonical_sufficiency_judgment_projection,
    compact_sufficiency_judgment_ref,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
)

_MAX_SEMANTIC_REF_ITEMS = 80
_ORIGIN_EVIDENCE_REF_KIND = "evidence_ledger_candidate"
_ORIGIN_ID_KEYS = (
    "evidence_ref_id",
    "evidence_id",
    "candidate_id",
    "evidence_ledger_candidate_id",
    "candidate_ref_id",
    "source_candidate_id",
)
_SOURCE_IDENTITY_KEYS = (
    "url",
    "source_url",
    "normalized_source_identity",
    "source_identity",
)
_ACCEPTED_CANDIDATE_DISPOSITIONS = frozenset(
    {"accepted", "observed", "partially_accepted", "unknown"}
)
_REJECTED_CANDIDATE_DISPOSITIONS = frozenset(
    {"rejected", "dropped", "unreadable", "unfetchable"}
)
_READABLE_CANDIDATE_STATUSES = frozenset({"readable", "available", "ok", "unknown"})
_STALE_CURRENTNESS_SIGNALS = frozenset({"stale", "outdated", "expired", "superseded"})
_SOURCE_OBLIGATION_TOPOLOGY_SCHEMA_VERSION = (
    "final_answer_packet_source_obligation_topology_safe_v1"
)
_TOPOLOGY_SOURCE_OBLIGATION_KINDS = frozenset(
    {
        "official_current",
        "legal_current_primary",
        "canonical_documentation",
        "primary_source_documents",
        "source_bound_numeric",
        "date_bound_currentness",
        "peer_reviewed",
        "reputable_secondary",
        "conflict_resolution",
        "user_document",
        "no_special_obligation",
        "supporting_fact",
    }
)
_TOPOLOGY_EVIDENCE_LEDGER_REQUIREMENT_KINDS = frozenset(
    {
        "official_current",
        "legal",
        "canonical",
        "source_bound",
        "academic",
        "general",
        "current",
        "user_document",
    }
)
_TOPOLOGY_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
        "historical_legal_text",
        "sourced_numeric_values",
        "secondary",
        "secondary_only",
        "secondary_analysis",
        "reputable_secondary",
        "social_signal",
        "social_or_forum",
        "community",
        "context",
    }
)
_TOPOLOGY_SOURCE_TIERS = frozenset(
    {
        "official",
        "primary",
        "canonical",
        "secondary",
        "trusted_community",
        "social_or_forum",
        "context",
        "analysis",
        "low_trust_commercial",
        "content_mill",
    }
)
_TOPOLOGY_CURRENTNESS_POSTURES = frozenset(
    {
        "current",
        "official_current",
        "stale",
        "outdated",
        "historical_only",
        "off_topic",
        "not_current",
        "not_evaluated",
        "unknown",
    }
)
_TOPOLOGY_READABLE_STATUSES = frozenset(
    {
        "readable",
        "unreadable",
        "fetch_failed",
        "not_readable",
        "blocked",
        "unfetchable",
        "no_readable_text",
        "not_read",
        "not_evaluated",
        "unknown",
    }
)
_TOPOLOGY_BLOCKER_CODES = frozenset(
    {
        "candidate_not_readable_or_fetchable",
        "candidate_material_type_does_not_satisfy_requirement",
        "lower_tier_or_contextual_candidate_cannot_satisfy_stronger_obligation",
        "stale_or_off_topic_candidate_cannot_satisfy_current_obligation",
        "candidate_not_eligible_for_stronger_obligation",
        "candidate_source_class_does_not_match_requirement",
        "candidate_source_tier_does_not_match_requirement",
        "candidate_not_accepted_for_requirement",
        "no_linked_candidate_satisfies_requirement",
        "requirement_has_no_linked_candidate_observation",
        "requirement_not_observed",
        "ambiguous_authoritative_ledger_binding",
        "requirement_partially_satisfied",
        "unrecognized_qualification_blocker",
    }
)
_TOPOLOGY_KIND_BY_RUN_CONTRACT_REQUIREMENT_KIND = {
    "official_current": "official_current",
    "legal_primary": "legal_current_primary",
    "canonical_docs": "canonical_documentation",
    "source_bound_numeric": "source_bound_numeric",
    "academic": "peer_reviewed",
    "reputable_secondary": "reputable_secondary",
    "user_document": "user_document",
}


def _hash_or_none(text: Any) -> tuple[str | None, int | None]:
    if text is None:
        return None, None
    value = str(text or "")
    if not value:
        return None, 0
    from hashlib import sha256

    return sha256(value.encode("utf-8")).hexdigest(), len(value)


def _normalize_source_identity(value: Any) -> str:
    text = _clean_text(value, limit=500) or ""
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.netloc:
        return text.casefold().rstrip("/")
    return urlunparse(
        (
            parsed.scheme.casefold() or "https",
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            "",
            parsed.query,
            "",
        )
    )


def _passage_candidate_identity_keys(passage: Mapping[str, Any]) -> frozenset[str]:
    keys = {
        token
        for token in (_clean_token(passage.get(key), limit=200) for key in _ORIGIN_ID_KEYS)
        if token
    }
    for key in _SOURCE_IDENTITY_KEYS:
        identity = _normalize_source_identity(passage.get(key))
        if identity:
            keys.add(f"candidate:{sha256(identity.encode('utf-8')).hexdigest()[:16]}")
    source_id = _clean_token(passage.get("source_id"), limit=120)
    if source_id:
        keys.add(f"source-id:{source_id}")
    return frozenset(keys)


def _candidate_record_is_bindable(
    candidate: Mapping[str, Any],
    *,
    passage: Mapping[str, Any],
) -> bool:
    disposition = (
        _clean_token(
            candidate.get("fact_disposition")
            or candidate.get("disposition")
            or candidate.get("status")
        )
        or "unknown"
    ).casefold()
    if disposition in _REJECTED_CANDIDATE_DISPOSITIONS:
        return False
    if disposition not in _ACCEPTED_CANDIDATE_DISPOSITIONS:
        return False
    readable = (
        _clean_token(
            candidate.get("readable_status") or candidate.get("readability_status")
        )
        or "readable"
    ).casefold()
    if readable not in _READABLE_CANDIDATE_STATUSES:
        return False
    if candidate.get("contextual_only") is True:
        return False
    if candidate.get("lower_tier") is True:
        return False
    currentness = (
        _clean_token(candidate.get("currentness_signal"))
        or _clean_token(passage.get("currentness_signal"))
        or _clean_token(passage.get("currentness"))
    )
    if currentness and currentness.casefold() in _STALE_CURRENTNESS_SIGNALS:
        return False
    return True


def _candidate_records_from_ledger(projection: Any) -> tuple[Mapping[str, Any], ...]:
    ledger = _evidence_ledger_projection_from_any(projection)
    if not ledger:
        return ()
    records = ledger.get("candidate_records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return ()
    return tuple(dict(item) for item in records if isinstance(item, Mapping))


def _origin_evidence_ref_from_ledger_candidate(
    passage: Mapping[str, Any],
    *,
    evidence_ledger_projection: Any,
) -> tuple[str | None, str | None]:
    candidates = _candidate_records_from_ledger(evidence_ledger_projection)
    if not candidates:
        return None, None

    passage_candidate_keys = _passage_candidate_identity_keys(passage)
    source_id = _clean_token(passage.get("source_id"), limit=120)
    passage_identities = {
        identity
        for identity in (
            _normalize_source_identity(passage.get(key))
            for key in _SOURCE_IDENTITY_KEYS
        )
        if identity
    }

    bindable_candidates = [
        candidate
        for candidate in candidates
        if _clean_token(candidate.get("candidate_id"), limit=200)
        and _candidate_record_is_bindable(
            candidate,
            passage=passage,
        )
    ]
    for candidate in bindable_candidates:
        candidate_id = _clean_token(
            candidate.get("candidate_id"),
            limit=200,
        )
        if candidate_id in passage_candidate_keys:
            return candidate_id, _ORIGIN_EVIDENCE_REF_KIND

    for candidate in bindable_candidates:
        candidate_id = _clean_token(candidate.get("candidate_id"), limit=200)
        candidate_identities = {
            identity
            for identity in (
                _normalize_source_identity(candidate.get(key))
                for key in _SOURCE_IDENTITY_KEYS
            )
            if identity
        }
        if passage_identities and passage_identities.intersection(candidate_identities):
            return candidate_id, _ORIGIN_EVIDENCE_REF_KIND
        candidate_source_id = _clean_token(candidate.get("source_id"), limit=120)
        if source_id and candidate_source_id and source_id == candidate_source_id:
            return candidate_id, _ORIGIN_EVIDENCE_REF_KIND
    return None, None


def _evidence_record_from_passage(
    passage: Mapping[str, Any],
    *,
    position: int,
    packet_id: str,
    evidence_ledger_projection: Any = None,
    status: EvidenceAuthorityStatus = EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
    reason: str | None = None,
) -> FinalEvidenceRecord:
    text_hash, text_length = _hash_or_none(passage.get("text"))
    source_id = passage.get("source_id")
    evidence_id = f"{packet_id}:e{position}"
    origin_ref_id, origin_ref_kind = _origin_evidence_ref_from_ledger_candidate(
        passage,
        evidence_ledger_projection=evidence_ledger_projection,
    )
    return FinalEvidenceRecord(
        evidence_id=evidence_id,
        status=status,
        position=position,
        source_id=source_id,
        url=str(passage.get("url") or "") or None,
        title=str(passage.get("title") or "") or None,
        source_tier=str(passage.get("source_tier") or "") or None,
        source_class=str(passage.get("source_class") or "") or None,
        text_hash=text_hash,
        text_length=text_length,
        reason=reason,
        origin_evidence_ref_id=origin_ref_id,
        origin_evidence_ref_kind=origin_ref_kind,
    )


def _citation_record_for_evidence(
    record: FinalEvidenceRecord,
    *,
    sufficiency_constrained: bool = False,
    satisfied_source_classes: frozenset[str] = frozenset(),
) -> CitationEligibilityRecord:
    if record.source_id is None:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="source_id_missing",
        )
    if not record.url:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="source_url_missing",
        )
    if (
        sufficiency_constrained
        and satisfied_source_classes
        and _contract_requirement_key(record.source_class) not in satisfied_source_classes
    ):
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="not_supported_by_sufficiency_satisfied_obligation",
        )
    if sufficiency_constrained and not satisfied_source_classes:
        return CitationEligibilityRecord(
            citation_id=f"{record.evidence_id}:citation",
            evidence_id=record.evidence_id,
            source_id=record.source_id,
            status=CitationEligibilityStatus.CITATION_INELIGIBLE,
            requirement=CitationRequirementStatus.CITATION_OPTIONAL,
            reason="sufficiency_has_no_satisfied_source_obligation",
        )
    return CitationEligibilityRecord(
        citation_id=f"{record.evidence_id}:citation",
        evidence_id=record.evidence_id,
        source_id=record.source_id,
        status=CitationEligibilityStatus.CITATION_ELIGIBLE,
        requirement=CitationRequirementStatus.CITATION_OPTIONAL,
    )


def _custody_projection_from_any(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, OfficialCurrentSourceCustodyState):
        return value.to_dict()
    if isinstance(value, Mapping):
        if "official_current_source_custody" in value:
            nested = value.get("official_current_source_custody")
            return dict(nested) if isinstance(nested, Mapping) else {}
        return dict(value)
    return {}


def _evidence_ledger_projection_from_any(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("owner") == "RunKernel.EvidenceLedger":
        return dict(value)
    return {}


def _source_obligations_from_custody(projection: Any) -> tuple[SourceObligationRecord, ...]:
    """Parse OfficialCurrentSourceCustodyState for historical/unit callers.

    Ordinary PRODUCT assembly no longer supplies telemetry custody here.
    EvidenceLedger projections may still carry a nested compatibility view.
    """

    custody_projection = _custody_projection_from_any(projection)
    if not custody_projection:
        return ()
    state = OfficialCurrentSourceCustodyState.from_projection(custody_projection)
    obligations: list[SourceObligationRecord] = []
    for requirement in state.requirements():
        status = (
            SourceObligationStatus.SATISFIED
            if requirement.satisfied
            else SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
        )
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"final-answer:{requirement.requirement_id}",
                source_class=requirement.source_class,
                status=status,
                custody_requirement_id=requirement.requirement_id,
                satisfied_candidate_ids=tuple(requirement.satisfied_candidate_ids),
                reason=requirement.unsatisfied_reason,
            )
        )
    return tuple(obligations)


def _source_obligations_from_answer_contract(
    projection: Any,
) -> tuple[SourceObligationRecord, ...]:
    if projection is None:
        return ()
    if hasattr(projection, "fulfillment_handoff"):
        projection = getattr(projection, "fulfillment_handoff")
    if hasattr(projection, "to_dict"):
        projection = projection.to_dict()
    if hasattr(projection, "to_controller_state"):
        projection = projection.to_controller_state()
    if not isinstance(projection, Mapping):
        return ()

    satisfied_source_classes: list[str] = []
    for key in (
        "fulfilled_source_classes",
        "satisfied_source_classes",
        "source_classes_present",
    ):
        value = projection.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                text = str(item or "").strip()
                if text and text not in satisfied_source_classes:
                    satisfied_source_classes.append(text)

    source_classes: list[str] = []
    for key in (
        "unfulfilled_source_classes",
        "missing_source_classes",
        "unfulfilled_obligations",
        "missing_information",
    ):
        value = projection.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                text = str(item or "").strip()
                if text and text not in source_classes:
                    source_classes.append(text)

    obligations: list[SourceObligationRecord] = []
    for index, source_class in enumerate(satisfied_source_classes, start=1):
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"answer-contract:satisfied:{index}:{source_class}",
                source_class=source_class,
                status=SourceObligationStatus.SATISFIED,
                reason="answer_contract_fulfilled_source_obligation",
            )
        )
    for index, source_class in enumerate(source_classes, start=1):
        obligations.append(
            SourceObligationRecord(
                obligation_id=f"answer-contract:{index}:{source_class}",
                source_class=source_class,
                status=SourceObligationStatus.MISSING_REQUIRED_SOURCE,
                reason="answer_contract_unfulfilled_source_obligation",
            )
        )
    return tuple(obligations)


def _contract_requirement_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _missing_status_for_contract_requirement(
    requirement: Mapping[str, Any],
) -> SourceObligationStatus:
    kind = str(requirement.get("requirement_kind") or "").strip()
    if kind == "official_current":
        return SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    if kind == "source_bound_numeric":
        return SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING
    return SourceObligationStatus.MISSING_REQUIRED_SOURCE


def _matching_source_obligation_records(
    requirement: Mapping[str, Any],
    obligations: Sequence[SourceObligationRecord],
) -> tuple[SourceObligationRecord, ...]:
    requirement_id = _contract_requirement_key(requirement.get("requirement_id"))
    source_class = _contract_requirement_key(requirement.get("required_source_class"))
    exact_matches: list[SourceObligationRecord] = []
    if requirement_id:
        for obligation in obligations:
            obligation_ids = (
                _contract_requirement_key(obligation.custody_requirement_id),
                _contract_requirement_key(obligation.obligation_id),
            )
            if any(
                value == requirement_id or value.endswith(f":{requirement_id}")
                for value in obligation_ids
                if value
            ):
                exact_matches.append(obligation)
    if exact_matches:
        return tuple(exact_matches)
    return tuple(
        obligation
        for obligation in obligations
        if source_class
        and _contract_requirement_key(obligation.source_class) == source_class
    )


def _source_obligations_from_run_contract(
    projection: Any,
    *,
    existing_obligations: Sequence[SourceObligationRecord] = (),
) -> tuple[SourceObligationRecord, ...]:
    if not isinstance(projection, Mapping):
        return ()
    if projection.get("owner") != "RunKernel.RunAuthorityContract":
        return ()
    obligations: list[SourceObligationRecord] = []
    for index, requirement in enumerate(projection.get("source_requirements") or (), start=1):
        if not isinstance(requirement, Mapping):
            continue
        if str(requirement.get("strictness") or "") != "required":
            continue
        source_class = str(requirement.get("required_source_class") or "").strip()
        if not source_class:
            continue
        if _matching_source_obligation_records(requirement, existing_obligations):
            continue
        obligations.append(
            SourceObligationRecord(
                obligation_id=(
                    f"run-contract:{index}:"
                    f"{requirement.get('requirement_id') or source_class}"
                ),
                source_class=source_class,
                status=_missing_status_for_contract_requirement(requirement),
                custody_requirement_id=requirement.get("requirement_id"),
                reason="run_authority_contract_required_source_obligation",
            )
        )
    return tuple(obligations)


def _dedupe_source_obligations(
    obligations: Sequence[SourceObligationRecord],
) -> tuple[SourceObligationRecord, ...]:
    """Remove only repeated canonical identities, never class-level semantics."""

    out: list[SourceObligationRecord] = []
    seen: set[tuple[str, str]] = set()
    for obligation in obligations:
        identity = (
            _contract_requirement_key(obligation.custody_requirement_id)
            or _contract_requirement_key(obligation.obligation_id)
        )
        key = (identity, obligation.status.value)
        if key not in seen:
            out.append(obligation)
            seen.add(key)
    return tuple(out)


def _sufficiency_projection_from_any(value: Any) -> dict[str, Any]:
    return canonical_sufficiency_judgment_projection(value)


def _semantic_projection_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _topology_token(value: Any, *, allowed: frozenset[str]) -> str:
    token = (_clean_token(value, limit=160) or "").casefold()
    return token if token in allowed else "not_observed"


def _topology_identifiers(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    values: list[str] = []
    for item in value:
        identifier = _clean_token(item, limit=240)
        if identifier and identifier not in values:
            values.append(identifier)
    return tuple(values[:_MAX_SEMANTIC_REF_ITEMS])


def _topology_opaque_ref(value: Any, *, prefix: str) -> str:
    identifier = _clean_token(value, limit=240)
    if not identifier:
        return "not_observed"
    digest = sha256(f"{prefix}:{identifier}".encode("utf-8")).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _topology_status(ledger_requirement: Mapping[str, Any] | None) -> str:
    status = _clean_token((ledger_requirement or {}).get("status"))
    if status == "satisfied":
        return "satisfied"
    if status == "partially_satisfied":
        return "partial"
    return "missing"


def _topology_candidate_fact(candidate: Mapping[str, Any]) -> dict[str, Any]:
    citation_eligible = candidate.get("citation_eligible")
    return {
        "candidate_ref": _topology_opaque_ref(
            candidate.get("candidate_id"),
            prefix="candidate",
        ),
        "source_tier": _topology_token(
            candidate.get("source_tier"),
            allowed=_TOPOLOGY_SOURCE_TIERS,
        ),
        "source_class": _topology_token(
            candidate.get("source_class") or candidate.get("source_class_hint"),
            allowed=_TOPOLOGY_SOURCE_CLASSES,
        ),
        "currentness_posture": _topology_token(
            candidate.get("currentness_signal") or candidate.get("currentness"),
            allowed=_TOPOLOGY_CURRENTNESS_POSTURES,
        ),
        "eligible_for_stronger_obligation": (
            candidate.get("eligible_for_stronger_obligation")
            if isinstance(candidate.get("eligible_for_stronger_obligation"), bool)
            else None
        ),
        "readable_status": _topology_token(
            candidate.get("readable_status"),
            allowed=_TOPOLOGY_READABLE_STATUSES,
        ),
        "citation_eligible": (
            citation_eligible if isinstance(citation_eligible, bool) else None
        ),
    }


def _topology_ledger_requirement(
    *,
    ledger_requirements: Sequence[Mapping[str, Any]],
    requirement_id: str | None,
    source_obligation_id: str | None = None,
    component_id: str | None = None,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Resolve one authoritative ledger record without class-based coalescing."""

    matches = [
        dict(item)
        for item in ledger_requirements
        if _clean_token(item.get("requirement_id")) == requirement_id
    ]
    if source_obligation_id:
        matches = [
            item
            for item in matches
            if _clean_token(item.get("source_obligation_id"))
            == source_obligation_id
        ]
    if component_id:
        matches = [
            item
            for item in matches
            if _clean_token(item.get("component_id")) == component_id
        ]
    if len(matches) == 1:
        return matches[0], ()
    if not matches:
        return {}, ("requirement_not_observed",)
    return {}, ("ambiguous_authoritative_ledger_binding",)


def _topology_ledger_requirement_by_component_obligation(
    *,
    ledger_requirements: Sequence[Mapping[str, Any]],
    source_obligation_id: str,
    component_id: str | None,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Resolve an accepted component source obligation by its exact ownership."""

    matches = [
        dict(item)
        for item in ledger_requirements
        if _clean_token(item.get("source_obligation_id")) == source_obligation_id
    ]
    component_matches = matches
    if component_id:
        component_matches = [
            item
            for item in matches
            if _clean_token(item.get("component_id")) == component_id
        ]
    if len(component_matches) == 1:
        return component_matches[0], ()
    # The accepted source-obligation ID is the canonical semantic identity.
    # A uniquely owned ledger row may therefore remain authoritative even when
    # a compatibility component projection does not reproduce its raw ID.
    if len(matches) == 1:
        return matches[0], ()
    if not matches:
        return {}, ("requirement_not_observed",)
    return {}, ("ambiguous_authoritative_ledger_binding",)


def _topology_ledger_requirement_for_run_contract(
    *,
    ledger_requirements: Sequence[Mapping[str, Any]],
    requirement: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Bind one run-contract row through exact IDs, then full owned posture."""

    requirement_id = _clean_token(requirement.get("requirement_id"), limit=240)
    exact, errors = _topology_ledger_requirement(
        ledger_requirements=ledger_requirements,
        requirement_id=requirement_id,
    )
    if exact or errors != ("requirement_not_observed",):
        return exact, errors
    contract_kind = (
        _clean_token(requirement.get("requirement_kind")) or ""
    ).casefold()
    expected_ledger_kind = {
        "official_current": "official_current",
        "legal_primary": "legal",
        "canonical_docs": "canonical",
        "source_bound_numeric": "source_bound",
        "academic": "academic",
        "reputable_secondary": "general",
        "user_document": "user_document",
    }.get(contract_kind)
    required_class = _clean_token(requirement.get("required_source_class"))
    required_tier = _clean_token(requirement.get("required_source_tier"))
    required_currentness = _clean_token(requirement.get("required_currentness"))
    structural_matches = [
        dict(item)
        for item in ledger_requirements
        if not _clean_token(item.get("component_id"))
        and not _clean_token(item.get("source_obligation_id"))
        and _clean_token(item.get("requirement_kind")) == expected_ledger_kind
        and _clean_token(item.get("required_source_class")) == required_class
        and _clean_token(item.get("required_source_tier")) == required_tier
        and _clean_token(item.get("required_currentness")) == required_currentness
    ]
    if len(structural_matches) == 1:
        return structural_matches[0], ()
    if len(structural_matches) > 1:
        return {}, ("ambiguous_authoritative_ledger_binding",)
    return {}, errors


def _topology_blocker_codes(
    *,
    status: str,
    ledger_requirement: Mapping[str, Any],
    binding_errors: Sequence[str],
) -> list[str]:
    if status == "satisfied":
        return []
    values = [*binding_errors, ledger_requirement.get("reason")]
    codes: list[str] = []
    for value in values:
        code = (_clean_token(value, limit=180) or "").casefold()
        if not code:
            continue
        if code not in _TOPOLOGY_BLOCKER_CODES:
            code = "unrecognized_qualification_blocker"
        if code not in codes:
            codes.append(code)
    if not codes:
        codes.append(
            "requirement_partially_satisfied"
            if status == "partial"
            else "no_linked_candidate_satisfies_requirement"
        )
    return codes


def _source_obligation_topology_entry(
    *,
    obligation_id: str,
    obligation_kind: str,
    owning_scope: str,
    component_id: str | None,
    expected_requirement: Mapping[str, Any],
    ledger_requirement: Mapping[str, Any],
    binding_errors: Sequence[str],
    candidate_records_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    status = _topology_status(ledger_requirement)
    candidate_ids = _topology_identifiers(
        ledger_requirement.get("linked_candidate_ids")
    )
    candidate_facts = [
        _topology_candidate_fact(candidate_records_by_id[candidate_id])
        for candidate_id in candidate_ids
        if candidate_id in candidate_records_by_id
    ]
    required_source_class = (
        ledger_requirement.get("required_source_class")
        or expected_requirement.get("required_source_class")
    )
    required_source_tier = (
        ledger_requirement.get("required_source_tier")
        or expected_requirement.get("required_source_tier")
    )
    required_currentness = (
        ledger_requirement.get("required_currentness")
        or expected_requirement.get("required_currentness")
    )
    return {
        "source_obligation_ref": _topology_opaque_ref(
            obligation_id,
            prefix="source_obligation",
        ),
        "obligation_kind": _topology_token(
            obligation_kind,
            allowed=_TOPOLOGY_SOURCE_OBLIGATION_KINDS,
        ),
        "evidence_ledger_requirement_kind": _topology_token(
            ledger_requirement.get("requirement_kind"),
            allowed=_TOPOLOGY_EVIDENCE_LEDGER_REQUIREMENT_KINDS,
        ),
        "owning_scope": owning_scope,
        "owning_component_ref": (
            _topology_opaque_ref(component_id, prefix="component")
            if component_id
            else "not_observed"
        ),
        "required_source_class": _topology_token(
            required_source_class,
            allowed=_TOPOLOGY_SOURCE_CLASSES,
        ),
        "required_source_tier": _topology_token(
            required_source_tier,
            allowed=_TOPOLOGY_SOURCE_TIERS,
        ),
        "required_temporal_posture": _topology_token(
            required_currentness,
            allowed=_TOPOLOGY_CURRENTNESS_POSTURES,
        ),
        "status": status,
        "satisfying_evidence_count": len(candidate_ids) if status == "satisfied" else 0,
        "candidate_evidence_binding_count": len(candidate_ids),
        "qualification_blocker_reason_codes": _topology_blocker_codes(
            status=status,
            ledger_requirement=ledger_requirement,
            binding_errors=binding_errors,
        ),
        "candidate_qualification_facts": candidate_facts,
    }


def _source_obligation_topology_projection(
    *,
    accepted_answer_contract_projection: Any,
    run_contract_projection: Any,
    evidence_ledger_projection: Any,
) -> dict[str, Any]:
    """Expose authoritative source-obligation rows without source content.

    This is a packet observability projection only.  It never changes
    qualification, sufficiency, citation, or final-answer policy.
    """

    accepted_contract = (
        dict(accepted_answer_contract_projection)
        if isinstance(accepted_answer_contract_projection, Mapping)
        else {}
    )
    run_contract = (
        dict(run_contract_projection)
        if isinstance(run_contract_projection, Mapping)
        else {}
    )
    ledger = _evidence_ledger_projection_from_any(evidence_ledger_projection)
    ledger_requirements = [
        dict(item)
        for item in ledger.get("source_requirements") or ()
        if isinstance(item, Mapping)
    ]
    candidate_records_by_id = {
        candidate_id: dict(item)
        for item in ledger.get("candidate_records") or ()
        if isinstance(item, Mapping)
        for candidate_id in (_clean_token(item.get("candidate_id")),)
        if candidate_id
    }
    obligations: list[dict[str, Any]] = []
    seen_component_owners: set[tuple[str, str | None]] = set()
    for raw_obligation in accepted_contract.get(
        "accepted_source_obligation_refs",
        (),
    ):
        if not isinstance(raw_obligation, Mapping):
            continue
        obligation_id = _clean_token(
            raw_obligation.get("source_obligation_id")
            or raw_obligation.get("candidate_id"),
            limit=240,
        )
        if not obligation_id:
            continue
        component_ids = _topology_identifiers(raw_obligation.get("component_ids"))
        for component_id in component_ids or (None,):
            owner_key = (obligation_id, component_id)
            if owner_key in seen_component_owners:
                continue
            seen_component_owners.add(owner_key)
            ledger_requirement, binding_errors = (
                _topology_ledger_requirement_by_component_obligation(
                    ledger_requirements=ledger_requirements,
                    source_obligation_id=obligation_id,
                    component_id=component_id,
                )
            )
            obligations.append(
                _source_obligation_topology_entry(
                    obligation_id=obligation_id,
                    obligation_kind=str(
                        raw_obligation.get("kind")
                        or raw_obligation.get("obligation_kind")
                        or ""
                    ),
                    owning_scope="component",
                    component_id=component_id,
                    expected_requirement=raw_obligation,
                    ledger_requirement=ledger_requirement,
                    binding_errors=binding_errors,
                    candidate_records_by_id=candidate_records_by_id,
                )
            )

    seen_run_requirement_ids: set[str] = set()
    for raw_requirement in run_contract.get("source_requirements") or ():
        if not isinstance(raw_requirement, Mapping):
            continue
        if _clean_token(raw_requirement.get("strictness")) != "required":
            continue
        requirement_id = _clean_token(raw_requirement.get("requirement_id"), limit=240)
        if not requirement_id or requirement_id in seen_run_requirement_ids:
            continue
        seen_run_requirement_ids.add(requirement_id)
        ledger_requirement, binding_errors = _topology_ledger_requirement_for_run_contract(
            ledger_requirements=ledger_requirements,
            requirement=raw_requirement,
        )
        run_kind = (_clean_token(raw_requirement.get("requirement_kind")) or "").casefold()
        obligations.append(
            _source_obligation_topology_entry(
                obligation_id=requirement_id,
                obligation_kind=_TOPOLOGY_KIND_BY_RUN_CONTRACT_REQUIREMENT_KIND.get(
                    run_kind,
                    run_kind,
                ),
                owning_scope="run_contract",
                component_id=None,
                expected_requirement=raw_requirement,
                ledger_requirement=ledger_requirement,
                binding_errors=binding_errors,
                candidate_records_by_id=candidate_records_by_id,
            )
        )

    return {
        "schema_version": _SOURCE_OBLIGATION_TOPOLOGY_SCHEMA_VERSION,
        "available": bool(obligations),
        "evidence_ledger_available": bool(ledger_requirements),
        "evidence_ledger_requirement_count": len(ledger_requirements),
        "accepted_obligation_count": len(obligations),
        "satisfied_obligation_count": sum(
            item["status"] == "satisfied" for item in obligations
        ),
        "partial_obligation_count": sum(
            item["status"] == "partial" for item in obligations
        ),
        "missing_obligation_count": sum(
            item["status"] == "missing" for item in obligations
        ),
        "obligations": obligations,
    }


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _token_list(value: Any, *, limit: int = 160) -> list[str]:
    out: list[str] = []
    for item in _list(value):
        token = _clean_token(item, limit=limit)
        if token and token not in out:
            out.append(token)
    return out[:_MAX_SEMANTIC_REF_ITEMS]


def _stable_json_digest(value: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _component_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        component_id = _clean_token(item.get("component_id"))
        component_digest = _clean_token(item.get("component_digest"), limit=128)
        if component_id and component_digest:
            refs.append(
                {
                    "component_id": component_id,
                    "component_digest": component_digest,
                }
            )
    return refs[:_MAX_SEMANTIC_REF_ITEMS]


def _coverage_record_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        coverage_record_id = _clean_token(item.get("coverage_record_id"))
        coverage_record_digest = _clean_token(
            item.get("coverage_record_digest"),
            limit=128,
        )
        answer_component_id = _clean_token(item.get("answer_component_id"))
        if coverage_record_id and coverage_record_digest and answer_component_id:
            refs.append(
                {
                    "coverage_record_id": coverage_record_id,
                    "coverage_record_digest": coverage_record_digest,
                    "answer_component_id": answer_component_id,
                }
            )
    return refs[:_MAX_SEMANTIC_REF_ITEMS]


def _semantic_observation_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        observation_id = _clean_token(item.get("observation_id"))
        observation_digest = _clean_token(item.get("observation_digest"), limit=128)
        if observation_id and observation_digest:
            refs.append(
                {
                    "observation_id": observation_id,
                    "observation_digest": observation_digest,
                }
            )
    return refs[:_MAX_SEMANTIC_REF_ITEMS]


def _semantic_source_ref_bindings(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        origin_evidence_ref_id = _clean_token(
            item.get("origin_evidence_ref_id"),
            limit=200,
        )
        origin_evidence_ref_kind = _clean_token(
            item.get("origin_evidence_ref_kind") or _ORIGIN_EVIDENCE_REF_KIND,
            limit=120,
        )
        content_ref_id = _clean_token(item.get("content_ref_id"))
        content_digest = _clean_token(item.get("content_digest"), limit=128)
        coverage_record_id = _clean_token(item.get("coverage_record_id"))
        coverage_record_digest = _clean_token(
            item.get("coverage_record_digest"),
            limit=128,
        )
        component_id = _clean_token(item.get("component_id"))
        component_digest = _clean_token(item.get("component_digest"), limit=128)
        if (
            origin_evidence_ref_id
            and origin_evidence_ref_kind
            and content_ref_id
            and content_digest
            and coverage_record_id
            and coverage_record_digest
            and component_id
            and component_digest
        ):
            refs.append(
                {
                    "origin_evidence_ref_id": origin_evidence_ref_id,
                    "origin_evidence_ref_kind": origin_evidence_ref_kind,
                    "content_ref_id": content_ref_id,
                    "content_digest": content_digest,
                    "coverage_record_id": coverage_record_id,
                    "coverage_record_digest": coverage_record_digest,
                    "component_id": component_id,
                    "component_digest": component_digest,
                }
            )
    return refs[:_MAX_SEMANTIC_REF_ITEMS]


def _semantic_state_facts_digest(
    *,
    summary: Mapping[str, Any],
    consumption: Mapping[str, Any],
) -> str | None:
    for source in (summary, consumption):
        digest = str(source.get("semantic_state_facts_digest") or "").strip()
        if digest:
            return digest[:128]
    return None


def _semantic_ref_projection_from_sufficiency(projection: Any) -> dict[str, Any]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return {}
    consumption = _semantic_projection_mapping(sufficiency.get("semantic_consumption"))
    semantic_ref_projection = _semantic_projection_mapping(
        consumption.get("semantic_ref_projection")
    )
    if (
        semantic_ref_projection.get("schema_version")
        != SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION
    ):
        return {}
    if semantic_ref_projection.get("available") is not True:
        return {}
    if semantic_ref_projection.get("content_refs_available") is not True:
        return {}
    if semantic_ref_projection.get("coverage_refs_available") is not True:
        return {}

    semantic_state_digest = _clean_token(
        semantic_ref_projection.get("semantic_state_facts_digest"),
        limit=128,
    )
    accepted_contract_digest = _clean_token(
        semantic_ref_projection.get("accepted_contract_digest"),
        limit=128,
    )
    accepted_contract_version = _clean_token(
        semantic_ref_projection.get("accepted_contract_version")
    )
    component_refs = _component_refs(semantic_ref_projection.get("component_refs"))
    coverage_refs = _coverage_record_refs(
        semantic_ref_projection.get("coverage_record_refs")
    )
    observation_refs = _semantic_observation_refs(
        semantic_ref_projection.get("semantic_observation_refs")
    )
    content_ref_ids = _token_list(
        semantic_ref_projection.get("sanitized_content_ref_ids")
    )
    content_ref_digests = _token_list(
        semantic_ref_projection.get("content_ref_digests"),
        limit=128,
    )
    semantic_ref_evidence_ids = _token_list(
        semantic_ref_projection.get("evidence_ids")
    )
    semantic_source_ref_bindings = _semantic_source_ref_bindings(
        semantic_ref_projection.get("semantic_source_ref_bindings")
    )
    source_obligation_refs = _token_list(
        semantic_ref_projection.get("source_obligation_refs")
    )

    if (
        not semantic_state_digest
        or not accepted_contract_digest
        or not content_ref_ids
        or not content_ref_digests
        or not coverage_refs
    ):
        return {}

    safe_sufficiency_projection: dict[str, Any] = {
        "schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "available": True,
        "semantic_state_facts_digest": semantic_state_digest,
        "accepted_contract_version": accepted_contract_version,
        "accepted_contract_digest": accepted_contract_digest,
        "component_refs": component_refs,
        "coverage_record_refs": coverage_refs,
        "semantic_observation_refs": observation_refs,
        "sanitized_content_ref_ids": content_ref_ids,
        "content_ref_digests": content_ref_digests,
        "evidence_ids": semantic_ref_evidence_ids,
        "semantic_source_ref_bindings": semantic_source_ref_bindings,
        "source_obligation_refs": source_obligation_refs,
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    return {
        key: value
        for key, value in safe_sufficiency_projection.items()
        if value not in (None, "", [], {})
    }


def _author_materialization_content_refs(
    *,
    source_projection: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[FinalEvidenceRecord],
) -> list[dict[str, Any]]:
    if not final_top_evidence or not evidence_records:
        return []
    evidence_by_origin = {
        record.origin_evidence_ref_id: record
        for record in evidence_records
        if record.status is EvidenceAuthorityStatus.EVIDENCE_ALLOWED
        and record.origin_evidence_ref_id
    }
    passages_by_position = {
        index: passage
        for index, passage in enumerate(final_top_evidence, start=1)
        if isinstance(passage, Mapping)
    }
    material_refs: list[dict[str, Any]] = []
    for binding in source_projection.get("semantic_source_ref_bindings") or ():
        if not isinstance(binding, Mapping):
            continue
        origin_id = _clean_token(binding.get("origin_evidence_ref_id"), limit=200)
        record = evidence_by_origin.get(origin_id)
        if record is None or not record.position:
            continue
        passage = passages_by_position.get(record.position)
        if not passage:
            continue
        bounded_text = _clean_text(passage.get("text"), limit=2000)
        if not bounded_text:
            continue
        material_ref = {
            "content_ref_id": binding["content_ref_id"],
            "content_digest": binding["content_digest"],
            "evidence_ref_id": origin_id,
            "admitted_evidence_ref": origin_id,
            "origin_evidence_ref_id": origin_id,
            "origin_evidence_ref_kind": (
                binding.get("origin_evidence_ref_kind")
                or _ORIGIN_EVIDENCE_REF_KIND
            ),
            "packet_evidence_id": record.evidence_id,
            "answer_component_id": binding["component_id"],
            "component_id": binding["component_id"],
            "component_digest": binding["component_digest"],
            "component_contract_digest": binding["component_digest"],
            "accepted_contract_version": source_projection.get(
                "accepted_contract_version"
            ),
            "accepted_contract_digest": source_projection.get(
                "accepted_contract_digest"
            ),
            "coverage_record_id": binding["coverage_record_id"],
            "coverage_record_digest": binding["coverage_record_digest"],
            "content_kind": "bounded_excerpt",
            "bounded_text": bounded_text,
            "source_id": record.source_id,
            "source_url": record.url,
            "source_title": record.title,
            "source_domain": record.domain,
            "citation_eligibility_posture": "packet_evidence_pending",
            "sanitized": True,
            "bounded": True,
            "raw_content_retained": False,
            "raw_provider_payload_retained": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "private_logs_retained": False,
            "db_cache_rows_retained": False,
            "full_trace_retained": False,
            "secrets_returned": False,
            "raw_content_included": False,
            "raw_prompt_included": False,
            "provider_payload_included": False,
            "final_text_included": False,
            "trace_only": True,
            "accepted_authority": False,
        }
        material_refs.append(material_ref)
    return material_refs[:_MAX_SEMANTIC_REF_ITEMS]


def _fap_semantic_content_coverage_projection(
    projection: Any,
    *,
    final_top_evidence: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[FinalEvidenceRecord],
) -> dict[str, Any]:
    source_projection = _semantic_ref_projection_from_sufficiency(projection)
    if not source_projection:
        return {}
    fap_projection: dict[str, Any] = {
        "schema_version": (
            FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION
        ),
        "available": True,
        "source_authority": "RunAuthoritySufficiency.semantic_ref_projection",
        "source_schema_version": SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
        "source_projection_digest": _stable_json_digest(source_projection),
        "semantic_state_facts_digest": source_projection[
            "semantic_state_facts_digest"
        ],
        "accepted_contract_version": source_projection.get(
            "accepted_contract_version"
        ),
        "accepted_contract_digest": source_projection["accepted_contract_digest"],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }
    for source_key, packet_key in (
        ("component_refs", "component_refs"),
        ("coverage_record_refs", "coverage_record_refs"),
        ("semantic_observation_refs", "semantic_observation_refs"),
        ("sanitized_content_ref_ids", "sanitized_content_ref_ids"),
        ("content_ref_digests", "content_ref_digests"),
        ("evidence_ids", "semantic_ref_evidence_ids"),
        ("semantic_source_ref_bindings", "semantic_source_ref_bindings"),
        ("source_obligation_refs", "source_obligation_refs"),
    ):
        value = source_projection.get(source_key)
        if value not in (None, "", [], {}):
            fap_projection[packet_key] = value
    material_refs = _author_materialization_content_refs(
        source_projection=source_projection,
        final_top_evidence=final_top_evidence,
        evidence_records=evidence_records,
    )
    if material_refs:
        fap_projection["author_materialization_content_refs"] = material_refs
    return fap_projection


def _semantic_packet_evidence_bindings(
    *,
    evidence_records: Sequence[FinalEvidenceRecord],
    semantic_content_coverage_ref_projection: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    if semantic_content_coverage_ref_projection.get("available") is not True:
        return ()

    allowed_by_origin: dict[str, FinalEvidenceRecord] = {}
    for record in evidence_records:
        if record.status is not EvidenceAuthorityStatus.EVIDENCE_ALLOWED:
            continue
        origin_id = _clean_token(record.origin_evidence_ref_id, limit=200)
        if origin_id and origin_id not in allowed_by_origin:
            allowed_by_origin[origin_id] = record

    semantic_origin_ids = _token_list(
        semantic_content_coverage_ref_projection.get("semantic_ref_evidence_ids"),
        limit=200,
    )
    source_bindings = _semantic_source_ref_bindings(
        semantic_content_coverage_ref_projection.get("semantic_source_ref_bindings")
    )
    source_origin_ids = [
        row["origin_evidence_ref_id"]
        for row in source_bindings
        if row.get("origin_evidence_ref_id")
    ]
    required_origin_ids = tuple(
        dict.fromkeys([*semantic_origin_ids, *source_origin_ids])
    )
    if not required_origin_ids:
        raise ValueError(
            "available semantic content coverage projection requires semantic evidence refs"
        )
    if not source_bindings:
        raise ValueError(
            "available semantic content coverage projection requires row-wise semantic source bindings"
        )

    missing = [
        origin_id
        for origin_id in required_origin_ids
        if origin_id not in allowed_by_origin
    ]
    if missing:
        raise ValueError(
            "semantic packet evidence binding mismatch: unresolved origin evidence refs "
            + ", ".join(missing)
        )

    rows: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for source_row in source_bindings:
        origin_id = source_row["origin_evidence_ref_id"]
        record = allowed_by_origin.get(origin_id)
        if record is None:
            raise ValueError(
                "semantic packet evidence binding mismatch: unresolved origin evidence ref "
                + origin_id
            )
        row = {
            "schema_version": (
                FINAL_ANSWER_PACKET_SEMANTIC_PACKET_EVIDENCE_BINDING_SCHEMA_VERSION
            ),
            "origin_evidence_ref_id": origin_id,
            "origin_evidence_ref_kind": (
                source_row.get("origin_evidence_ref_kind")
                or _ORIGIN_EVIDENCE_REF_KIND
            ),
            "packet_evidence_id": record.evidence_id,
            "content_ref_id": source_row["content_ref_id"],
            "content_digest": source_row["content_digest"],
            "coverage_record_id": source_row["coverage_record_id"],
            "coverage_record_digest": source_row["coverage_record_digest"],
            "component_id": source_row["component_id"],
            "component_digest": source_row["component_digest"],
        }
        row["binding_digest"] = semantic_packet_evidence_binding_digest(row)
        dedupe_key = (
            str(row["origin_evidence_ref_id"]),
            str(row["packet_evidence_id"]),
            str(row["content_ref_id"]),
            str(row["coverage_record_id"]),
        )
        if dedupe_key not in seen:
            rows.append(row)
            seen.add(dedupe_key)
    return tuple(rows)


def _semantic_field_from_sources(
    key: str,
    *,
    consumption: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> Any | None:
    if key in consumption:
        return consumption[key]
    if consumption:
        return None
    if key in summary:
        return summary[key]
    return None


def _compact_semantic_authority_ref(projection: Any) -> dict[str, Any]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return {}

    summary = _semantic_projection_mapping(
        sufficiency.get("semantic_state_facts_summary")
    )
    consumption = _semantic_projection_mapping(sufficiency.get("semantic_consumption"))

    digest = _semantic_state_facts_digest(summary=summary, consumption=consumption)
    if not digest:
        return {}

    ref: dict[str, Any] = {
        "schema_version": FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
        "available": True,
        "sufficiency_semantic_consumed": True,
        "authority_owner": RUN_AUTHORITY_SUFFICIENCY_JUDGMENT_OWNER,
        "semantic_state_facts_digest": digest,
    }

    summary_schema = _semantic_field_from_sources(
        "schema_version",
        consumption=consumption,
        summary=summary,
    )
    if summary_schema is not None and str(summary_schema).strip():
        ref["semantic_summary_schema_version"] = str(summary_schema).strip()

    for key in (
        "required_component_count",
        "covered_component_count",
        "satisfied_coverage_count",
        "blocker_count",
    ):
        value = _semantic_field_from_sources(
            key,
            consumption=consumption,
            summary=summary,
        )
        if value is not None:
            ref[key] = value

    required = ref.get("required_component_count")
    covered = ref.get("covered_component_count")
    if (
        "required_component_count" in ref
        and "covered_component_count" in ref
        and isinstance(required, int)
        and isinstance(covered, int)
    ):
        ref["missing_component_count"] = max(0, required - covered)

    for key in ("blocker_codes", "direct_answer_blocked", "finalization_blocked"):
        value = _semantic_field_from_sources(
            key,
            consumption=consumption,
            summary=summary,
        )
        if value is not None:
            ref[key] = value

    judgment_ref = compact_sufficiency_judgment_ref(sufficiency)
    if judgment_ref:
        ref["sufficiency_judgment_ref"] = judgment_ref

    return ref


def _status_for_sufficiency_obligation(
    obligation: Mapping[str, Any],
) -> SourceObligationStatus:
    kind = str(obligation.get("requirement_kind") or "").strip()
    if kind == "source_bound_numeric":
        return SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING
    if kind == "official_current":
        return SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED
    return SourceObligationStatus.MISSING_REQUIRED_SOURCE


def _source_obligations_from_sufficiency(
    projection: Any,
) -> tuple[SourceObligationRecord, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_obligations: list[Mapping[str, Any]] = []
    for key in (
        "missing_required_obligations",
        "partial_obligations",
        "satisfied_obligations",
    ):
        value = packet_inputs.get(key)
        if value is None:
            value = sufficiency.get(key) or ()
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            raw_obligations.extend(item for item in value if isinstance(item, Mapping))
    obligations: list[SourceObligationRecord] = []
    for index, item in enumerate(raw_obligations, start=1):
        source_class = str(
            item.get("required_source_class")
            or item.get("source_class")
            or item.get("requirement_kind")
            or "required_source"
        ).strip()
        if not source_class:
            continue
        status_value = str(item.get("status") or "").strip()
        if status_value == "satisfied":
            status = SourceObligationStatus.SATISFIED
        elif status_value == "partial":
            status = SourceObligationStatus.PARTIAL
        else:
            status = _status_for_sufficiency_obligation(item)
        canonical_requirement_id = str(
            item.get("requirement_id")
            or item.get("source_obligation_id")
            or source_class
        ).strip()
        obligations.append(
            SourceObligationRecord(
                obligation_id=(
                    "run-sufficiency:"
                    f"{canonical_requirement_id or index}"
                ),
                source_class=source_class,
                status=status,
                custody_requirement_id=canonical_requirement_id or None,
                satisfied_candidate_ids=tuple(
                    str(candidate)
                    for candidate in item.get("satisfied_candidate_ids", ())
                    if str(candidate or "").strip()
                ),
                reason=str(item.get("reason") or "run_sufficiency_judgment"),
            )
        )
    return tuple(obligations)


def _claim_postures_from_sufficiency(
    projection: Any,
) -> tuple[ClaimPosture, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_postures = packet_inputs.get("claim_postures") or ()
    out: list[ClaimPosture] = []
    for item in raw_postures:
        try:
            posture = ClaimPosture(str(item))
        except ValueError:
            continue
        if posture not in out:
            out.append(posture)
    return tuple(out)


def _sufficiency_readiness(
    projection: Any,
) -> tuple[FinalAnswerReadinessStatus, tuple[str, ...]] | None:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return None
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    raw_status = (
        "blocked"
        if packet_inputs.get("final_answer_allowed") is False
        else None
    ) or (
        packet_inputs.get("readiness_status")
        or (
            "blocked"
            if sufficiency.get("final_answer_allowed") is False
            else None
        )
        or (
            "insufficient_authorized"
            if sufficiency.get("final_answer_posture")
            in {"partial_answer", "insufficient_answer", "failure_card"}
            else "author_ready"
        )
    )
    try:
        readiness_status = FinalAnswerReadinessStatus(str(raw_status))
    except ValueError:
        readiness_status = FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    reasons = packet_inputs.get("readiness_reasons") or sufficiency.get(
        "readiness_reasons",
        (),
    )
    return readiness_status, tuple(
        dict.fromkeys(str(item) for item in reasons if str(item or "").strip())
    )


def _sufficiency_packet_inputs(projection: Any) -> dict[str, Any]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return {}
    packet_inputs = sufficiency.get("final_packet_inputs")
    return dict(packet_inputs) if isinstance(packet_inputs, Mapping) else {}


def _sufficiency_packet_items(
    projection: Any,
    key: str,
) -> tuple[str, ...]:
    sufficiency = _sufficiency_projection_from_any(projection)
    if not sufficiency:
        return ()
    packet_inputs = (
        sufficiency.get("final_packet_inputs")
        if isinstance(sufficiency.get("final_packet_inputs"), Mapping)
        else {}
    )
    value = packet_inputs.get(key) or sufficiency.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item or "").strip())
    return ()


def _sufficiency_packet_mappings(
    projection: Any,
    key: str,
) -> tuple[Mapping[str, Any], ...]:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(dict(item) for item in value if isinstance(item, Mapping))
    sufficiency = _sufficiency_projection_from_any(projection)
    fallback = sufficiency.get(key) if sufficiency else ()
    if isinstance(fallback, Sequence) and not isinstance(fallback, (str, bytes)):
        return tuple(dict(item) for item in fallback if isinstance(item, Mapping))
    return ()


def _sufficiency_packet_text(
    projection: Any,
    key: str,
) -> str | None:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if value is None:
        value = _sufficiency_projection_from_any(projection).get(key) if _sufficiency_projection_from_any(projection) else None
    text = str(value or "").strip()
    return text or None


def _sufficiency_packet_bool(
    projection: Any,
    key: str,
) -> bool | None:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    if isinstance(value, bool):
        return value
    sufficiency = _sufficiency_projection_from_any(projection)
    value = sufficiency.get(key) if sufficiency else None
    return value if isinstance(value, bool) else None


def _sufficiency_packet_mapping(
    projection: Any,
    key: str,
) -> dict[str, Any]:
    packet_inputs = _sufficiency_packet_inputs(projection)
    value = packet_inputs.get(key)
    return dict(value) if isinstance(value, Mapping) else {}


def _sufficiency_author_ref(projection: Any) -> dict[str, Any]:
    return compact_sufficiency_judgment_ref(projection)


def _custody_summary(projection: Any) -> dict[str, Any]:
    custody_projection = _custody_projection_from_any(projection)
    evidence_ledger_projection = _evidence_ledger_projection_from_any(projection)
    custody_authority = (
        "RunKernel.EvidenceLedger"
        if evidence_ledger_projection
        else "OfficialCurrentSourceCustodyState"
    )
    if not custody_projection:
        return {"available": False, "custody_authority": custody_authority}
    state = OfficialCurrentSourceCustodyState.from_projection(custody_projection)
    requirements = state.requirements()
    summary = {
        "available": True,
        "custody_authority": custody_authority,
        "requirements": [requirement.to_dict() for requirement in requirements],
        "satisfied_source_classes": [r.source_class for r in requirements if r.satisfied],
        "unsatisfied_source_classes": [r.source_class for r in requirements if not r.satisfied],
    }
    if evidence_ledger_projection:
        custody_gaps = list(evidence_ledger_projection.get("custody_gaps") or ())
        final_gap_types = [
            gap.get("gap_type")
            for gap in custody_gaps
            if isinstance(gap, Mapping)
            and gap.get("gap_type")
            == "final_evidence_selected_without_ledger_custody"
        ]
        summary.update(
            {
                "evidence_ledger_candidate_count": evidence_ledger_projection.get(
                    "candidate_count", 0
                ),
                "evidence_ledger_requirement_count": evidence_ledger_projection.get(
                    "requirement_count", 0
                ),
                "custody_gap_types": [
                    gap.get("gap_type")
                    for gap in custody_gaps
                    if isinstance(gap, Mapping) and gap.get("gap_type")
                ],
                "final_evidence_compatibility_gap_count": len(final_gap_types),
            }
        )
    return summary


def _postures(
    *,
    evidence_sufficient: bool | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    conflicts_present: bool | None,
    synth_was_insufficient: bool | None,
    source_obligations: Sequence[SourceObligationRecord],
) -> tuple[ClaimPosture, ...]:
    out: list[ClaimPosture] = []
    if evidence_sufficient is True:
        out.append(ClaimPosture.DIRECTLY_SOURCED)
    if corpus_weak:
        out.append(ClaimPosture.WEAK_CORPUS_AUTHORIZED)
    if failure_card_payload and failure_card_payload.get("show"):
        out.append(ClaimPosture.FAILURE_CARD_AUTHORIZED)
    if evidence_sufficient is False or synth_was_insufficient:
        out.append(ClaimPosture.INSUFFICIENT_EVIDENCE)
    if conflicts_present:
        out.append(ClaimPosture.CONFLICT_PRESERVED)
    if any(
        o.status
        in {
            SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED,
            SourceObligationStatus.MISSING_REQUIRED_SOURCE,
            SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING,
        }
        for o in source_obligations
    ):
        out.append(ClaimPosture.INSUFFICIENT_EVIDENCE)
    if not out:
        out.append(ClaimPosture.DIRECTLY_SOURCED)
    return tuple(dict.fromkeys(out))


def _mandatory_caveats(
    *,
    author_notes: str | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    source_obligations: Sequence[SourceObligationRecord],
    synth_was_insufficient: bool | None,
) -> tuple[str, ...]:
    caveats: list[str] = []
    if author_notes:
        caveats.append("legacy_author_notes_present")
    if corpus_weak:
        caveats.append("weak_corpus_must_be_caveated")
    if synth_was_insufficient:
        caveats.append("synthesis_insufficient_must_be_caveated")
    if failure_card_payload and failure_card_payload.get("show"):
        reason = failure_card_payload.get("reason") or "failure_card"
        caveats.append(f"failure_card_authorized:{reason}")
    for obligation in source_obligations:
        if obligation.status is SourceObligationStatus.OFFICIAL_CURRENT_UNSATISFIED:
            caveats.append(f"official_current_unsatisfied:{obligation.source_class}")
        elif obligation.status is SourceObligationStatus.MISSING_REQUIRED_SOURCE:
            caveats.append(f"missing_required_source:{obligation.source_class}")
        elif obligation.status is SourceObligationStatus.SOURCE_BOUND_VALUE_MISSING:
            caveats.append(f"source_bound_value_missing:{obligation.source_class}")
    return tuple(dict.fromkeys(caveats))


def _contract_final_posture_items(
    projection: Any,
    key: str,
) -> tuple[str, ...]:
    if not isinstance(projection, Mapping):
        return ()
    policy = projection.get("final_posture_policy")
    if not isinstance(policy, Mapping):
        return ()
    value = policy.get(key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item or "").strip())
    return ()


def _is_missing_source_caveat(caveat: str) -> bool:
    lowered = caveat.casefold()
    return any(marker in lowered for marker in ("missing", "absent", "unavailable", "unknown"))


def _unresolved_contract_requirement_markers(
    projection: Any,
    source_obligations: Sequence[SourceObligationRecord],
) -> frozenset[str]:
    if not isinstance(projection, Mapping):
        return frozenset()
    markers: set[str] = set()
    for requirement in projection.get("source_requirements") or ():
        if not isinstance(requirement, Mapping):
            continue
        if str(requirement.get("strictness") or "") != "required":
            continue
        matches = _matching_source_obligation_records(requirement, source_obligations)
        if not matches:
            continue
        if any(
            obligation.status is not SourceObligationStatus.SATISFIED
            for obligation in matches
        ):
            markers.update(
                marker
                for marker in (
                    _contract_requirement_key(requirement.get("requirement_id")),
                    _contract_requirement_key(requirement.get("requirement_kind")),
                    _contract_requirement_key(requirement.get("required_source_class")),
                )
                if marker
            )
    return frozenset(markers)


def _missing_source_caveat_applies(
    caveat: str,
    *,
    unresolved_markers: frozenset[str],
) -> bool:
    if not _is_missing_source_caveat(caveat):
        return True
    if not unresolved_markers:
        return False
    lowered = caveat.casefold()
    marker_groups = (
        (
            ("official_current", "official"),
            ("official_current", "official_current_rules", "current_primary_or_official"),
        ),
        (("source_bound", "numeric"), ("source_bound_numeric",)),
        (("legal", "regulatory"), ("legal_primary", "legal_or_regulatory_text")),
        (("canonical", "docs"), ("canonical_docs", "primary_source_documents")),
        (("user_document", "document"), ("user_document",)),
        (("academic", "literature"), ("academic", "academic_primary_literature")),
    )
    for caveat_terms, related_markers in marker_groups:
        if any(term in lowered for term in caveat_terms):
            return bool(unresolved_markers.intersection(related_markers))
    return True


def _contract_mandatory_caveats(
    projection: Any,
    *,
    source_obligations: Sequence[SourceObligationRecord],
) -> tuple[str, ...]:
    caveats = _contract_final_posture_items(projection, "mandatory_caveats")
    if not caveats:
        return ()
    unresolved_markers = _unresolved_contract_requirement_markers(
        projection,
        source_obligations,
    )
    return tuple(
        caveat
        for caveat in caveats
        if _missing_source_caveat_applies(
            caveat,
            unresolved_markers=unresolved_markers,
        )
    )


def _readiness(
    *,
    evidence_records: Sequence[FinalEvidenceRecord],
    source_obligations: Sequence[SourceObligationRecord],
    evidence_sufficient: bool | None,
    corpus_weak: bool | None,
    failure_card_payload: Mapping[str, Any] | None,
    synth_was_insufficient: bool | None,
) -> tuple[FinalAnswerReadinessStatus, tuple[str, ...]]:
    reasons: list[str] = []
    if not evidence_records:
        reasons.append("no_final_evidence_available")
    if evidence_sufficient is False:
        reasons.append("evidence_sufficient_false")
    if corpus_weak:
        reasons.append("weak_corpus_authorized")
    if synth_was_insufficient:
        reasons.append("synthesis_insufficient_authorized")
    if failure_card_payload and failure_card_payload.get("show"):
        reasons.append("failure_card_authorized")
    if any(
        obligation.status is not SourceObligationStatus.SATISFIED
        for obligation in source_obligations
    ):
        reasons.append("source_obligations_missing_or_unsatisfied")
    if reasons:
        return FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED, tuple(
            dict.fromkeys(reasons)
        )
    return FinalAnswerReadinessStatus.AUTHOR_READY, ()


def build_final_answer_packet(
    *,
    run_id: str,
    final_evidence: Sequence[Mapping[str, Any]] | None,
    author_evidence: Sequence[Mapping[str, Any]] | None = None,
    ordered_sources: Sequence[Any] | None = None,
    unique_source_urls: Mapping[str, Any] | None = None,
    final_answer_source_telemetry: Mapping[str, Any] | None = None,
    source_obligation_projection: Any | None = None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    answer_contract_projection: Any | None = None,
    accepted_answer_contract_projection: Any | None = None,
    run_contract_projection: Any | None = None,
    sufficiency_judgment_projection: Any | None = None,
    query_lineage_refs: Mapping[str, Any] | None = None,
    evidence_sufficient: bool | None = None,
    corpus_weak: bool | None = None,
    failure_card_payload: Mapping[str, Any] | None = None,
    conflicts_present: bool | None = None,
    synth_was_insufficient: bool | None = None,
    author_notes: str | None = None,
) -> FinalAnswerPacket:
    packet_id = f"final-answer-packet-{run_id}"
    sufficiency_projection = _sufficiency_projection_from_any(
        sufficiency_judgment_projection
    )
    sufficiency_missing_required = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "missing_required_obligations",
    )
    sufficiency_partial = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "partial_obligations",
    )
    sufficiency_satisfied = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "satisfied_obligations",
    )
    sufficiency_constrained_citations = bool(
        sufficiency_projection and (sufficiency_missing_required or sufficiency_partial)
    )
    satisfied_source_classes = frozenset(
        _contract_requirement_key(
            item.get("required_source_class")
            or item.get("source_class")
            or item.get("requirement_kind")
        )
        for item in sufficiency_satisfied
        if isinstance(item, Mapping)
    )
    canonical_evidence_ledger_projection = _evidence_ledger_projection_from_any(
        evidence_ledger_projection or source_obligation_projection
    )
    evidence_records = tuple(
        _evidence_record_from_passage(
            passage,
            position=index,
            packet_id=packet_id,
            evidence_ledger_projection=canonical_evidence_ledger_projection,
        )
        for index, passage in enumerate(final_evidence or (), start=1)
    )
    citation_records = tuple(
        _citation_record_for_evidence(
            record,
            sufficiency_constrained=sufficiency_constrained_citations,
            satisfied_source_classes=satisfied_source_classes,
        )
        for record in evidence_records
    )
    custody_source_obligations = _source_obligations_from_custody(
        source_obligation_projection
    )
    # The RunAuthority sufficiency judgment is the final semantic authority
    # when available.  Its exact ledger-backed records supersede the legacy
    # answer-contract source-class compatibility summary.
    answer_contract_source_obligations = (
        ()
        if sufficiency_projection
        else _source_obligations_from_answer_contract(answer_contract_projection)
    )
    contract_source_obligations = (
        ()
        if sufficiency_projection
        else _source_obligations_from_run_contract(
            run_contract_projection,
            existing_obligations=(
                custody_source_obligations + answer_contract_source_obligations
            ),
        )
    )
    sufficiency_source_obligations = _source_obligations_from_sufficiency(
        sufficiency_judgment_projection
    )
    source_obligations = _dedupe_source_obligations(
        custody_source_obligations
        + answer_contract_source_obligations
        + contract_source_obligations
        + sufficiency_source_obligations
    )
    source_obligation_topology = _source_obligation_topology_projection(
        accepted_answer_contract_projection=accepted_answer_contract_projection,
        run_contract_projection=run_contract_projection,
        evidence_ledger_projection=(
            canonical_evidence_ledger_projection
            or evidence_ledger_projection
            or source_obligation_projection
        ),
    )
    author_evidence_ids = []
    author_urls = {str(p.get("url") or "") for p in (author_evidence or ())}
    for record in evidence_records:
        if not author_urls or (record.url and record.url in author_urls):
            author_evidence_ids.append(record.evidence_id)
    author_refs = {
        "status": "author_input_ready",
        "author_evidence_ids": author_evidence_ids,
        "author_evidence_count": len(author_evidence or ()),
        "ordered_sources": list(ordered_sources or ()),
        "unique_source_urls": dict(unique_source_urls or {}),
        "final_answer_source_telemetry": dict(final_answer_source_telemetry or {}),
    }
    sufficiency_ref = _sufficiency_author_ref(sufficiency_judgment_projection)
    if sufficiency_ref:
        author_refs["sufficiency_judgment_ref"] = sufficiency_ref
        author_refs["final_answer_posture"] = sufficiency_ref.get(
            "final_answer_posture"
        )
        author_refs["sufficiency_decision"] = sufficiency_ref.get("decision")
    prohibited = [
        "do_not_upgrade_citation_ineligible_evidence",
        "do_not_treat_missing_official_current_custody_as_satisfied",
    ]
    if source_obligations:
        prohibited.append("do_not_infer_source_obligation_satisfaction_from_citation_presence")
    prohibited.extend(
        _contract_final_posture_items(
            run_contract_projection,
            "prohibited_upgrades",
        )
    )
    custody_summary = _custody_summary(source_obligation_projection)
    if custody_summary.get("final_evidence_compatibility_gap_count"):
        prohibited.append("do_not_treat_uncustodied_final_evidence_as_ledger_proof")
    if not evidence_records:
        prohibited.append("do_not_present_unsourced_claims_as_supported")
    readiness_status, readiness_reasons = _readiness(
        evidence_records=evidence_records,
        source_obligations=source_obligations,
        evidence_sufficient=evidence_sufficient,
        corpus_weak=corpus_weak,
        failure_card_payload=failure_card_payload,
        synth_was_insufficient=synth_was_insufficient,
    )
    sufficiency_readiness = _sufficiency_readiness(sufficiency_judgment_projection)
    if sufficiency_readiness is not None:
        readiness_status, readiness_reasons = sufficiency_readiness
    sufficiency_postures = _claim_postures_from_sufficiency(
        sufficiency_judgment_projection
    )
    legacy_postures = (
        ()
        if sufficiency_postures
        else _postures(
            evidence_sufficient=evidence_sufficient,
            corpus_weak=corpus_weak,
            failure_card_payload=failure_card_payload,
            conflicts_present=conflicts_present,
            synth_was_insufficient=synth_was_insufficient,
            source_obligations=source_obligations,
        )
    )
    claim_postures = tuple(dict.fromkeys(sufficiency_postures + legacy_postures))
    sufficiency_mandatory = _sufficiency_packet_items(
        sufficiency_judgment_projection,
        "mandatory_caveats",
    )
    sufficiency_prohibited = _sufficiency_packet_items(
        sufficiency_judgment_projection,
        "prohibited_upgrades",
    )
    prohibited.extend(sufficiency_prohibited)
    final_answer_allowed = _sufficiency_packet_bool(
        sufficiency_judgment_projection,
        "final_answer_allowed",
    )
    if final_answer_allowed is None:
        final_answer_allowed = True
    sufficiency_decision = _sufficiency_packet_text(
        sufficiency_judgment_projection,
        "decision",
    )
    final_answer_posture = _sufficiency_packet_text(
        sufficiency_judgment_projection,
        "final_answer_posture",
    )
    required_satisfied = _sufficiency_packet_bool(
        sufficiency_judgment_projection,
        "required_obligations_satisfied",
    )
    missing_required = sufficiency_missing_required
    partial_obligations = sufficiency_partial
    satisfied_obligations = sufficiency_satisfied
    source_bound_unknowns = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "source_bound_numeric_unknowns",
    )
    source_bound_resolutions = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "source_bound_numeric_resolutions",
    )
    behavior_boundary_flags = _sufficiency_packet_mapping(
        sufficiency_judgment_projection,
        "behavior_boundary_flags",
    )
    direct_component_entries = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "direct_component_entries",
    )
    admitted_synthesis_entries = _sufficiency_packet_mappings(
        sufficiency_judgment_projection,
        "admitted_synthesis_entries",
    )
    multicomponent_graph_readiness = _sufficiency_packet_text(
        sufficiency_judgment_projection,
        "multicomponent_graph_readiness",
    )
    multicomponent_limitations = _sufficiency_packet_items(
        sufficiency_judgment_projection,
        "multicomponent_limitations",
    )
    component_readiness = dict(
        sufficiency_projection.get("component_readiness")
        if isinstance(sufficiency_projection.get("component_readiness"), Mapping)
        else {}
    ) or _sufficiency_packet_mapping(
        sufficiency_judgment_projection,
        "component_readiness",
    )
    if component_readiness:
        author_refs["component_readiness"] = component_readiness
        if component_readiness.get("unready_component_count"):
            prohibited.append("do_not_treat_component_candidate_presence_as_readiness")
            prohibited.append("do_not_create_author_payload_from_unready_components")
    if final_answer_allowed is False:
        readiness_status = FinalAnswerReadinessStatus.BLOCKED
        readiness_reasons = tuple(
            dict.fromkeys((*readiness_reasons, "final_answer_not_allowed"))
        )
    semantic_authority_ref = _compact_semantic_authority_ref(
        sufficiency_judgment_projection
    )
    semantic_content_coverage_ref_projection = (
        _fap_semantic_content_coverage_projection(
            sufficiency_judgment_projection,
            final_top_evidence=final_evidence or (),
            evidence_records=evidence_records,
        )
    )
    semantic_packet_evidence_bindings = _semantic_packet_evidence_bindings(
        evidence_records=evidence_records,
        semantic_content_coverage_ref_projection=(
            semantic_content_coverage_ref_projection
        ),
    )
    return FinalAnswerPacket(
        packet_id=packet_id,
        evidence_records=evidence_records,
        citation_records=citation_records,
        source_obligations=source_obligations,
        source_obligation_topology=source_obligation_topology,
        official_current_custody_summary=custody_summary,
        sufficiency_decision=sufficiency_decision,
        final_answer_posture=final_answer_posture,
        final_answer_allowed=bool(final_answer_allowed),
        required_obligations_satisfied=required_satisfied,
        missing_required_obligations=missing_required,
        partial_obligations=partial_obligations,
        satisfied_obligations=satisfied_obligations,
        source_bound_numeric_unknowns=source_bound_unknowns,
        source_bound_numeric_resolutions=source_bound_resolutions,
        behavior_boundary_flags=behavior_boundary_flags,
        claim_postures=claim_postures,
        mandatory_caveats=tuple(
            dict.fromkeys(
                _mandatory_caveats(
                    author_notes=author_notes,
                    corpus_weak=corpus_weak,
                    failure_card_payload=failure_card_payload,
                    source_obligations=source_obligations,
                    synth_was_insufficient=synth_was_insufficient,
                )
                + _contract_mandatory_caveats(
                    run_contract_projection,
                    source_obligations=source_obligations,
                )
                + sufficiency_mandatory
            )
        ),
        prohibited_upgrades=tuple(dict.fromkeys(prohibited)),
        author_input_refs=author_refs,
        query_lineage_refs=dict(query_lineage_refs or {}),
        readiness_status=readiness_status,
        readiness_reasons=readiness_reasons,
        semantic_authority_ref=semantic_authority_ref,
        semantic_content_coverage_ref_projection=(
            semantic_content_coverage_ref_projection
        ),
        semantic_packet_evidence_bindings=semantic_packet_evidence_bindings,
        direct_component_entries=direct_component_entries,
        admitted_synthesis_entries=admitted_synthesis_entries,
        multicomponent_graph_readiness=multicomponent_graph_readiness,
        multicomponent_limitations=multicomponent_limitations,
    )


def derive_author_input_payload(
    packet: FinalAnswerPacket,
    *,
    prompt: str,
    author_system_prompt_key: str,
    author_effort: str,
    author_provider: str | None = None,
    author_model: str | None = None,
) -> tuple[FinalAnswerPacket, FinalAnswerAuthorInputPayload]:
    refs = packet.author_input_refs if isinstance(packet.author_input_refs, Mapping) else {}
    payload = packet.to_author_input_payload(
        prompt=prompt,
        author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort,
        author_provider=author_provider,
        author_model=author_model,
        author_evidence_ids=refs.get("author_evidence_ids") if isinstance(refs.get("author_evidence_ids"), Sequence) else None,
    )
    return packet.with_author_input_payload(payload), payload


def final_answer_packet_trace_fragment(packet: FinalAnswerPacket) -> dict[str, Any]:
    return packet.to_trace_fragment()


def final_answer_packet_compatibility_refs(
    packet: FinalAnswerPacket,
    *,
    final_evidence_snapshot_recorded: bool | None = None,
) -> dict[str, Any]:
    """Return legacy final-evidence/citation refs derived from FinalAnswerPacket.

    AG-89E keeps the old handoff reference shapes only as compatibility
    projections.  Counts, source IDs, ordered sources, and source telemetry are
    read from the packet rather than reconstructed by the orchestrator.
    """

    projection = packet.to_legacy_citation_handoff_inputs()
    final_evidence_count = len(packet.evidence_allowed)
    unique_source_url_count = len(projection["unique_source_urls"])
    base_ref: dict[str, Any] = {
        "packet_id": packet.packet_id,
        "final_evidence_count": final_evidence_count,
        "authority": FINAL_ANSWER_PACKET_TRACE_KEY,
    }
    ledger_ref = dict(base_ref)
    if final_evidence_snapshot_recorded is not None:
        ledger_ref["final_evidence_snapshot_recorded"] = bool(
            final_evidence_snapshot_recorded
        )
    author_evidence_count = packet.author_input_refs.get("author_evidence_count")
    if author_evidence_count is None:
        author_evidence_count = len(packet.author_input_refs.get("author_evidence_ids", ()))
    return {
        "final_evidence_ref": {
            **base_ref,
            "author_evidence_count": int(author_evidence_count),
            "ordered_source_count": len(projection["ordered_sources"]),
            "unique_source_url_count": unique_source_url_count,
            "trace_mode": "final_answer_packet_compatibility_projection",
        },
        "ledger_ref": ledger_ref,
        "source_telemetry_ref": {
            **base_ref,
            "source_ids": [
                record.source_id
                for record in packet.evidence_allowed
                if record.source_id is not None
            ],
            "unique_source_url_count": unique_source_url_count,
            "ordered_sources": projection["ordered_sources"],
            "final_answer_source_telemetry": projection[
                "final_answer_source_telemetry"
            ],
        },
        "final_evidence_bundle_ref": {
            **base_ref,
            "citation_eligible_count": len(packet.citation_eligible),
        },
    }


def build_packet_derived_citation_source_handoff_state(
    packet: FinalAnswerPacket,
    *,
    run_id: str | None = None,
    answer_contract_ref: Any | None = None,
    analyst_author_handoff_state: Any | None = None,
    ledger_ref: Any | None = None,
    source_telemetry_ref: Mapping[str, Any] | None = None,
    run_kernel_final_answer_ref: Mapping[str, Any] | None = None,
):
    """Demote legacy citation/source handoff inputs behind FinalAnswerPacket."""

    projection = packet.to_legacy_citation_handoff_inputs()
    compatibility_refs = final_answer_packet_compatibility_refs(packet)
    resolved_ledger_ref = ledger_ref or compatibility_refs["ledger_ref"]
    if run_kernel_final_answer_ref:
        resolved_ledger_ref = {
            **dict(resolved_ledger_ref),
            "run_kernel_final_answer_ref": dict(run_kernel_final_answer_ref),
        }
    return build_citation_source_handoff_state(
        run_id=run_id,
        final_evidence=projection["final_evidence"],
        selected_evidence=projection["selected_evidence"],
        author_evidence=projection["author_evidence"],
        unique_source_urls=projection["unique_source_urls"],
        ordered_sources=projection["ordered_sources"],
        final_answer_source_telemetry=projection["final_answer_source_telemetry"],
        final_citation_observation_refs=projection["final_citation_observation_refs"],
        final_evidence_bundle_ref=compatibility_refs["final_evidence_bundle_ref"],
        ledger_ref=resolved_ledger_ref,
        answer_contract_ref=answer_contract_ref,
        analyst_author_handoff_state=analyst_author_handoff_state,
        source_telemetry_ref=source_telemetry_ref or compatibility_refs["source_telemetry_ref"],
    )


__all__ = [
    "build_final_answer_packet",
    "build_packet_derived_citation_source_handoff_state",
    "final_answer_packet_compatibility_refs",
    "derive_author_input_payload",
    "final_answer_packet_trace_fragment",
]
