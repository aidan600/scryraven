"""RunKernel-owned evidence custody ledger for AG-91J.

The ledger consumes sanitized runtime observations and records candidate-level
custody, source requirements, requirement links, final-evidence compatibility
gaps, and subordinate official/current custody projections. It does not call
providers, models, prompts, retrieval, ranking, citation formatting, persistence,
or orchestration code.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.official_current_source_custody import (
    OfficialCurrentCustodyStatus,
    OfficialCurrentSourceCustodyState,
)

EVIDENCE_LEDGER_SCHEMA_VERSION = "evidence_ledger_ag91j_v1"
EVIDENCE_LEDGER_TRACE_KEY = "evidence_ledger"
COMPONENT_SCOPED_SOURCE_CUSTODY_SCHEMA_VERSION = (
    "component_scoped_source_custody_ag_custody_01_v1"
)
COMPONENT_SCOPED_SOURCE_CUSTODY_TRACE_KEY = "component_scoped_source_custody"
COMPONENT_SCOPED_SOURCE_CUSTODY_NEXT_CONSUMER = (
    "component evidence/citation binding"
)
FETCH_READ_CANDIDATE_CUSTODY_SCHEMA_VERSION = (
    "fetch_read_candidate_custody_ag_evidence_ledger_candidate_custody_01_v1"
)
FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY = "fetch_read_candidate_custody"
FETCH_READ_CANDIDATE_CUSTODY_NEXT_CONSUMER = "evidence-relative analysis packet"

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"


class CandidateDisposition(str, Enum):
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED = "rejected"
    CONTEXTUAL = "contextual"
    LOWER_TIER = "lower_tier"
    UNREADABLE = "unreadable"
    UNFETCHABLE = "unfetchable"
    DROPPED = "dropped"
    PROPOSED = "proposed"
    HELPER_ASSESSED = "helper_assessed"


class CandidateCustodyKind(str, Enum):
    FACT = "fact"
    HELPER_ASSESSMENT = "helper_assessment"
    PROPOSAL = "proposal"


class SourceRequirementStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"
    NOT_OBSERVABLE = "not_observable"


class EvidenceCustodyGapType(str, Enum):
    MISSING_CANDIDATE_IDENTITY = "missing_candidate_identity"
    MISSING_READABLE_SOURCE = "missing_readable_source"
    MISSING_SOURCE_CLASS_FIT = "missing_source_class_fit"
    MISSING_OFFICIAL_CURRENT_CANDIDATE = "missing_official_current_candidate"
    LEGACY_AGGREGATE_ONLY_PATH = "legacy_aggregate_only_path"
    HELPER_CONTROLLER_ASSESSMENT_NOT_PROMOTABLE = (
        "helper_controller_assessment_not_promotable"
    )
    CANDIDATE_DROPPED_WITHOUT_DISPOSITION = "candidate_dropped_without_disposition"
    FINAL_EVIDENCE_SELECTED_WITHOUT_LEDGER_CUSTODY = (
        "final_evidence_selected_without_ledger_custody"
    )
    MISSING_COMPONENT_SOURCE_CANDIDATE = "missing_component_source_candidate"
    UNFETCHED_OR_UNREAD_COMPONENT_CANDIDATE = (
        "unfetched_or_unread_component_candidate"
    )
    MISSING_SOURCE_BOUND_VALUE = "missing_source_bound_value"
    UNSUPPORTED_NUMERIC_VALUE = "unsupported_numeric_value"


_MAX_LIST_ITEMS = 50
_MAX_TEXT_CHARS = 260
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_text",
    "full_trace",
    "log",
    "model_response",
    "output_packet",
    "password",
    "prompt",
    "provider_payload",
    "raw_",
    "secret",
    "snippet",
    "token",
)
_SENSITIVE_EXACT_KEYS = frozenset(
    {
        "full_text",
        "raw_text",
        "snippet",
        "snippets",
        "source_text",
        "text",
        "key",
    }
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)
_SENSITIVE_VALUE_MARKERS = (
    "RAW_PROMPT",
    "RAW_PROVIDER_PAYLOAD",
    "RAW_MODEL_RESPONSE",
    "PRIVATE_LOG",
    "DB_CACHE_ROW",
    "FULL_TRACE",
)
_STRONG_REQUIREMENT_KINDS = frozenset(
    {
        "official",
        "current",
        "legal",
        "canonical",
        "source_bound",
        "official_current",
        "official_current_legal",
    }
)
_STRONG_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
        "historical_legal_text",
    }
)
_STRONG_SOURCE_TIERS = frozenset({"official", "primary", "canonical"})
_WEAK_SOURCE_CLASSES = frozenset(
    {
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
_WEAK_SOURCE_TIERS = frozenset(
    {
        "secondary",
        "trusted_community",
        "social_or_forum",
        "context",
        "analysis",
        "low_trust_commercial",
        "content_mill",
    }
)
_BAD_READABILITY = frozenset(
    {
        "unreadable",
        "fetch_failed",
        "not_readable",
        "blocked",
        "unfetchable",
        "no_readable_text",
    }
)
_BAD_CURRENTNESS = frozenset(
    {
        "stale",
        "outdated",
        "historical_only",
        "off_topic",
        "not_current",
    }
)


@dataclass(frozen=True, slots=True)
class CandidateCustodyRecord:
    candidate_id: str
    record_kind: CandidateCustodyKind | str
    disposition: CandidateDisposition | str
    reason: str | None = None
    source: str | None = None
    requirement_id: str | None = None
    observation_id: str | None = None

    def __post_init__(self) -> None:
        kind = _coerce_enum(
            CandidateCustodyKind,
            self.record_kind,
            CandidateCustodyKind.FACT.value,
        )
        disposition = _coerce_enum(
            CandidateDisposition,
            self.disposition,
            CandidateDisposition.UNKNOWN.value,
        )
        if not _clean_token(self.candidate_id):
            raise ValueError("candidate custody records require candidate_id")
        object.__setattr__(self, "record_kind", kind)
        object.__setattr__(self, "disposition", disposition)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "candidate_id": _clean_token(self.candidate_id),
            "record_kind": self.record_kind.value,
            "disposition": self.disposition.value,
            "reason": _clean_text(self.reason),
            "source": _clean_text(self.source, limit=120),
            "requirement_id": _clean_token(self.requirement_id),
            "observation_id": _clean_token(self.observation_id),
        }
        return _compact(payload)


@dataclass(slots=True)
class EvidenceCandidate:
    candidate_id: str
    url: str | None = None
    normalized_source_identity: str | None = None
    title: str | None = None
    domain: str | None = None
    source_label: str | None = None
    provider_name: str | None = None
    provider_role: str | None = None
    retrieval_pass_id: str | None = None
    query_ref: str | None = None
    action_ref: str | None = None
    source_tier: str | None = None
    source_class: str | None = None
    currentness_signal: str | None = None
    evidence_material_type: str | None = None
    readable_status: str | None = None
    fetchable_status: str | None = None
    fact_disposition: CandidateDisposition = CandidateDisposition.UNKNOWN
    helper_assessment: str | None = None
    proposal_disposition: str | None = None
    disposition_reason: str | None = None
    eligible_for_stronger_obligation: bool = False
    contextual_only: bool = False
    lower_tier: bool = False
    final_evidence_eligible: bool | str = UNKNOWN

    def merge(self, update: Mapping[str, Any]) -> None:
        for field_name in (
            "url",
            "normalized_source_identity",
            "title",
            "domain",
            "source_label",
            "provider_name",
            "provider_role",
            "retrieval_pass_id",
            "query_ref",
            "action_ref",
            "source_tier",
            "source_class",
            "currentness_signal",
            "evidence_material_type",
            "readable_status",
            "fetchable_status",
            "disposition_reason",
        ):
            current = getattr(self, field_name)
            incoming = update.get(field_name)
            if current in (None, "", UNKNOWN) and incoming not in (None, "", UNKNOWN):
                setattr(self, field_name, _clean_text(incoming))

        for field_name in ("contextual_only", "lower_tier"):
            if bool(update.get(field_name)):
                setattr(self, field_name, True)
        if update.get("final_evidence_eligible") not in (None, "", UNKNOWN):
            self.final_evidence_eligible = bool(update.get("final_evidence_eligible"))
        if update.get("eligible_for_stronger_obligation") is not None:
            self.eligible_for_stronger_obligation = bool(
                update.get("eligible_for_stronger_obligation")
            )
        else:
            self.eligible_for_stronger_obligation = (
                self.eligible_for_stronger_obligation
                or _strong_source_candidate(self)
            )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "candidate_id": _clean_token(self.candidate_id),
                "url": _clean_text(self.url, limit=500),
                "normalized_source_identity": _clean_text(
                    self.normalized_source_identity, limit=500
                ),
                "title": _clean_text(self.title),
                "domain": _clean_text(self.domain, limit=160),
                "source_label": _clean_text(self.source_label),
                "provider_name": _clean_text(self.provider_name, limit=120),
                "provider_role": _clean_text(self.provider_role, limit=120),
                "retrieval_pass_id": _clean_token(self.retrieval_pass_id),
                "query_ref": _clean_text(self.query_ref),
                "action_ref": _clean_token(self.action_ref),
                "source_tier": _clean_token(self.source_tier),
                "source_class": _clean_token(self.source_class),
                "currentness_signal": _clean_token(self.currentness_signal),
                "evidence_material_type": _clean_token(self.evidence_material_type),
                "readable_status": _clean_token(self.readable_status),
                "fetchable_status": _clean_token(self.fetchable_status),
                "fact_disposition": self.fact_disposition.value,
                "helper_assessment": _clean_text(self.helper_assessment),
                "proposal_disposition": _clean_text(self.proposal_disposition),
                "disposition_reason": _clean_text(self.disposition_reason),
                "eligible_for_stronger_obligation": bool(
                    self.eligible_for_stronger_obligation
                ),
                "contextual_only": bool(self.contextual_only),
                "lower_tier": bool(self.lower_tier),
                "final_evidence_eligible": self.final_evidence_eligible,
            }
        )


@dataclass(frozen=True, slots=True)
class SourceObligationLink:
    requirement_id: str
    candidate_id: str
    link_reason: str | None = None
    link_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "requirement_id": _clean_token(self.requirement_id),
                "candidate_id": _clean_token(self.candidate_id),
                "link_reason": _clean_text(self.link_reason),
                "link_status": _clean_token(self.link_status),
            }
        )


@dataclass(slots=True)
class SourceRequirementRecord:
    requirement_id: str
    requirement_kind: str
    origin_ref: str | None = None
    component_id: str | None = None
    source_obligation_id: str | None = None
    run_id: str | None = None
    request_id: str | None = None
    answer_contract_version: str | None = None
    answer_contract_digest: str | None = None
    recovery_authorization_id: str | None = None
    recovery_authorization_digest: str | None = None
    required_source_class: str | None = None
    required_source_tier: str | None = None
    required_currentness: str | None = None
    required_evidence_material_type: str | None = None
    linked_candidate_ids: list[str] = field(default_factory=list)
    status: SourceRequirementStatus = SourceRequirementStatus.UNKNOWN
    reason: str | None = None
    aggregate_counts_insufficient: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = _compact(
            {
                "requirement_id": _clean_token(self.requirement_id),
                "requirement_kind": _clean_token(self.requirement_kind),
                "origin_ref": _clean_text(self.origin_ref),
                "component_id": _clean_token(self.component_id),
                "source_obligation_id": _clean_token(self.source_obligation_id),
                "run_id": _clean_text(self.run_id, limit=160),
                "request_id": _clean_text(
                    self.request_id,
                    limit=160,
                ),
                "answer_contract_version": _clean_text(
                    self.answer_contract_version,
                    limit=160,
                ),
                "answer_contract_digest": _clean_text(
                    self.answer_contract_digest,
                    limit=160,
                ),
                "recovery_authorization_id": _clean_token(
                    self.recovery_authorization_id
                ),
                "recovery_authorization_digest": _clean_token(
                    self.recovery_authorization_digest
                ),
                "required_source_class": _clean_token(self.required_source_class),
                "required_source_tier": _clean_token(self.required_source_tier),
                "required_currentness": _clean_token(self.required_currentness),
                "required_evidence_material_type": _clean_token(
                    self.required_evidence_material_type
                ),
                "status": self.status.value,
                "reason": _clean_text(self.reason),
                "aggregate_counts_insufficient": bool(
                    self.aggregate_counts_insufficient
                ),
            }
        )
        payload["linked_candidate_ids"] = list(self.linked_candidate_ids)
        return payload


@dataclass(frozen=True, slots=True)
class EvidenceCustodyGap:
    gap_type: EvidenceCustodyGapType | str
    requirement_id: str | None = None
    candidate_id: str | None = None
    reason: str | None = None
    source_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gap_type",
            _coerce_enum(
                EvidenceCustodyGapType,
                self.gap_type,
                EvidenceCustodyGapType.MISSING_CANDIDATE_IDENTITY.value,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _compact(
            {
                "gap_type": self.gap_type.value,
                "requirement_id": _clean_token(self.requirement_id),
                "candidate_id": _clean_token(self.candidate_id),
                "reason": _clean_text(self.reason),
                "source_ref": _clean_text(self.source_ref),
            }
        )


@dataclass(frozen=True, slots=True)
class EvidenceLedgerProjection:
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _safe_mapping(dict(self.payload))


@dataclass(frozen=True, slots=True)
class EvidenceLedgerObservation:
    observation_id: str
    source: str
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = _safe_mapping(self.payload)
        payload["observation_id"] = _clean_token(self.observation_id)
        payload["observation_source"] = _clean_text(self.source, limit=120)
        return payload


@dataclass(slots=True)
class EvidenceLedger:
    candidates: dict[str, EvidenceCandidate] = field(default_factory=dict)
    custody_records: list[CandidateCustodyRecord] = field(default_factory=list)
    requirements: dict[str, SourceRequirementRecord] = field(default_factory=dict)
    links: list[SourceObligationLink] = field(default_factory=list)
    gaps: list[EvidenceCustodyGap] = field(default_factory=list)
    final_evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    observation_refs: list[dict[str, Any]] = field(default_factory=list)
    component_source_custody: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    fetch_read_candidate_custody: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )

    def reduce_observation(
        self,
        observation: Mapping[str, Any] | EvidenceLedgerObservation,
    ) -> "EvidenceLedger":
        payload = (
            observation.to_dict()
            if isinstance(observation, EvidenceLedgerObservation)
            else _safe_mapping(observation)
        )
        observation_id = _clean_token(payload.get("observation_id")) or (
            f"evidence-ledger-observation:{len(self.observation_refs) + 1}"
        )
        source = _clean_text(payload.get("observation_source"), limit=120) or UNKNOWN
        if any(
            ref.get("observation_id") == observation_id for ref in self.observation_refs
        ):
            return self
        self.observation_refs.append(
            {"observation_id": observation_id, "source": source}
        )
        for requirement in _list(payload.get("requirements") or payload.get("source_requirements")):
            self._admit_requirement(requirement)
        for candidate in _list(payload.get("candidates")):
            self._admit_candidate(candidate, observation_id=observation_id, source=source)
        for link in _list(payload.get("requirement_links") or payload.get("links")):
            self._link_candidate(
                _clean_token(link.get("requirement_id")),
                _clean_token(link.get("candidate_id")),
                reason=_clean_text(link.get("link_reason")),
                status=_clean_token(link.get("link_status")),
            )
        self._admit_aggregate_counts(payload.get("aggregate_counts"))
        for gap in _list(payload.get("custody_gaps") or payload.get("gaps")):
            self._admit_gap_record(gap, source=source)
        self._admit_final_evidence(payload.get("final_evidence"))
        for custody in _list(payload.get("component_source_custody")):
            self._admit_component_source_custody(custody)
        for custody in _list(payload.get("fetch_read_candidate_custody")):
            self._admit_fetch_read_candidate_custody(custody)
        self._evaluate_requirements()
        return self

    def record_component_scoped_source_custody_from_offline_search_executor_bridge(
        self,
        bridge_projection: Mapping[str, Any] | None,
        *,
        observation_id: str = "component-scoped-source-custody:offline-bridge",
    ) -> dict[str, Any]:
        """Consume offline SearchExecutor bridge observations into ledger custody."""

        observation = (
            build_component_scoped_source_custody_observation_from_offline_search_executor_bridge(
                bridge_projection=bridge_projection,
                observation_id=observation_id,
            )
        )
        self.reduce_observation(observation)
        return self.to_component_scoped_source_custody_projection()

    def to_projection(self) -> EvidenceLedgerProjection:
        official_current_projection = self.to_official_current_source_custody()
        gap_payloads = [gap.to_dict() for gap in self.gaps]
        payload = {
            "schema_version": EVIDENCE_LEDGER_SCHEMA_VERSION,
            "trace_key": EVIDENCE_LEDGER_TRACE_KEY,
            "owner": "RunKernel.EvidenceLedger",
            "canonical_state": True,
            "diagnostic_only": False,
            "storage_only": False,
            "trace_only": False,
            "sanitized": True,
            "aggregate_counts_are_authoritative_for_custody": False,
            "candidate_count": len(self.candidates),
            "requirement_count": len(self.requirements),
            "custody_record_count": len(self.custody_records),
            "candidate_records": [
                candidate.to_dict()
                for candidate in sorted(
                    self.candidates.values(), key=lambda item: item.candidate_id
                )
            ],
            "custody_records": [record.to_dict() for record in self.custody_records],
            "source_requirements": [
                requirement.to_dict()
                for requirement in sorted(
                    self.requirements.values(), key=lambda item: item.requirement_id
                )
            ],
            "requirement_links": [link.to_dict() for link in self.links],
            "custody_gaps": gap_payloads,
            "final_evidence_refs": list(self.final_evidence_refs),
            "observation_refs": list(self.observation_refs),
            "official_current_source_custody": official_current_projection.to_dict(),
            "component_scoped_source_custody": (
                self.to_component_scoped_source_custody_projection()
            ),
            "fetch_read_candidate_custody": (
                self.to_fetch_read_candidate_custody_projection()
            ),
            "compatibility": {
                "controller_evidence_ledger_status": "compatibility_only_subordinate",
                "allocation_result_candidate_custody_status": (
                    "admitted_as_sanitized_observation_input_when_present"
                ),
                "legacy_aggregate_only_authority_status": "demoted_not_satisfying",
                "final_evidence_compatibility_gap_count": len(
                    [
                        gap
                        for gap in gap_payloads
                        if gap.get("gap_type")
                        == EvidenceCustodyGapType.FINAL_EVIDENCE_SELECTED_WITHOUT_LEDGER_CUSTODY.value
                    ]
                ),
            },
        }
        return EvidenceLedgerProjection(payload)

    def to_component_scoped_source_custody_projection(self) -> dict[str, Any]:
        components = [
            _safe_mapping(record)
            for record in sorted(
                self.component_source_custody.values(),
                key=lambda item: str(item.get("component_id") or ""),
            )
        ]
        custody_gaps = [
            gap
            for component in components
            for gap in _list(component.get("custody_gaps"))
            if isinstance(gap, Mapping)
        ]
        obligation_statuses = [
            obligation.get("source_obligation_status")
            for component in components
            for obligation in _list(component.get("source_obligation_refs"))
            if isinstance(obligation, Mapping)
        ]
        payload = {
            "schema_version": COMPONENT_SCOPED_SOURCE_CUSTODY_SCHEMA_VERSION,
            "trace_key": COMPONENT_SCOPED_SOURCE_CUSTODY_TRACE_KEY,
            "owner": "RunKernel.EvidenceLedger",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "offline_bridge_consumer": True,
            "component_count": len(components),
            "source_obligation_count": sum(
                _positive_int(component.get("source_obligation_count"))
                for component in components
            ),
            "candidate_link_count": sum(
                _positive_int(component.get("candidate_link_count"))
                for component in components
            ),
            "per_component_custody": components,
            "custody_gaps": custody_gaps,
            "custody_gap_count": len(custody_gaps),
            "unsatisfied_obligation_statuses": [
                status
                for status in obligation_statuses
                if status
                in {
                    "unsatisfied",
                    "pending_candidate",
                    "missing_candidate",
                    "blocked_by_unfetched_or_unread_candidate",
                }
            ],
            "next_consumer": COMPONENT_SCOPED_SOURCE_CUSTODY_NEXT_CONSUMER,
            "candidate_links_are_evidence": False,
            "source_obligation_satisfied": False,
            "source_obligations_satisfied_by_candidate_presence": False,
            "evidence_bound": False,
            "citation_bound": False,
            "answer_value_bound": False,
            "full_component_success": False,
            "partial_user_answer_candidate": False,
            "final_answer_allowed": False,
            "author_payload_ready": False,
            "behavior_boundary_flags": _component_custody_false_flags(),
        }
        return _safe_mapping(payload)

    def to_fetch_read_candidate_custody_projection(self) -> dict[str, Any]:
        records = [
            _fetch_read_candidate_custody_record(record)
            for record in sorted(
                self.fetch_read_candidate_custody.values(),
                key=lambda item: (
                    str(item.get("candidate_id") or ""),
                    str(item.get("reference_id") or ""),
                ),
            )
        ]
        records = [record for record in records if record]
        custody_gaps = [
            _fetch_read_candidate_custody_gap(record)
            for record in records
            if record.get("fetch_read_status") != "readable"
        ]
        custody_gaps = [gap for gap in custody_gaps if gap]
        payload = {
            "schema_version": FETCH_READ_CANDIDATE_CUSTODY_SCHEMA_VERSION,
            "trace_key": FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY,
            "owner": "RunKernel.EvidenceLedger",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "fetch_read_packet_consumer": True,
            "candidate_content_custody_visible": bool(records),
            "custody_record_count": len(records),
            "readable_record_count": sum(
                1 for record in records if record.get("fetch_read_status") == "readable"
            ),
            "unreadable_record_count": sum(
                1 for record in records if record.get("fetch_read_status") != "readable"
            ),
            "fetch_read_candidate_custody_records": records,
            "custody_gaps": custody_gaps,
            "custody_gap_count": len(custody_gaps),
            "source_obligation_candidate_ids_are_lineage_only": True,
            "source_obligation_candidate_ids_satisfy_requirements": False,
            "candidate_content_custody_is_semantic_support": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "component_coverage_created": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
            "partial_answer_ready": False,
            "product_correctness_claimed": False,
            "next_consumer": FETCH_READ_CANDIDATE_CUSTODY_NEXT_CONSUMER,
            "behavior_boundary_flags": _fetch_read_candidate_custody_false_flags(),
        }
        return _safe_mapping(payload)

    def to_official_current_source_custody(self) -> OfficialCurrentSourceCustodyState:
        state = OfficialCurrentSourceCustodyState()
        for requirement in self.requirements.values():
            required_class = _clean_token(requirement.required_source_class)
            if required_class not in _STRONG_SOURCE_CLASSES:
                continue
            state = state.require(required_class, requirement_id=requirement.requirement_id)
            if requirement.aggregate_counts_insufficient:
                state = state.record_candidate_aggregate_only(
                    requirement.requirement_id,
                    reason="evidence_ledger_aggregate_counts_without_candidate_identity",
                    attempt_id="evidence_ledger_requirement_projection",
                )
            for candidate_id in requirement.linked_candidate_ids:
                candidate = self.candidates.get(candidate_id)
                if candidate is None:
                    state = state.record_candidate_identity_missing(
                        requirement.requirement_id,
                        reason="linked_candidate_missing_from_evidence_ledger",
                        attempt_id="evidence_ledger_requirement_projection",
                    )
                    continue
                state = state.record_candidate_returned(
                    requirement.requirement_id,
                    candidate_id=candidate.candidate_id,
                    attempt_id="evidence_ledger_requirement_projection",
                )
                if _candidate_satisfies_requirement(candidate, requirement):
                    status = (
                        OfficialCurrentCustodyStatus.CANDIDATE_PARTIALLY_ACCEPTED
                        if candidate.fact_disposition
                        is CandidateDisposition.PARTIALLY_ACCEPTED
                        else OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED
                    )
                elif _bad_readability(candidate):
                    status = OfficialCurrentCustodyStatus.CANDIDATE_UNREADABLE
                else:
                    status = OfficialCurrentCustodyStatus.CANDIDATE_REJECTED
                state = state.record_candidate_disposition(
                    requirement.requirement_id,
                    status=status,
                    candidate_id=candidate.candidate_id,
                    reason=_candidate_requirement_rejection_reason(
                        candidate, requirement
                    ),
                    attempt_id="evidence_ledger_requirement_projection",
                )
        return state.finalize_requirements()

    def _admit_requirement(self, record: Any) -> None:
        if not isinstance(record, Mapping):
            return
        requirement_id = _clean_token(
            record.get("requirement_id")
            or record.get("custody_requirement_id")
            or record.get("source_class")
            or record.get("required_source_class")
        )
        if not requirement_id:
            return
        if ":" not in requirement_id and _clean_token(record.get("required_source_class")):
            requirement_id = f"source_requirement:{requirement_id}"
        requirement = self.requirements.get(requirement_id)
        if requirement is None:
            requirement = SourceRequirementRecord(
                requirement_id=requirement_id,
                requirement_kind=_requirement_kind(record),
                origin_ref=_clean_text(
                    record.get("origin_ref")
                    or record.get("answer_contract_ref")
                    or record.get("source_obligation_ref")
                ),
                component_id=_clean_token(record.get("component_id")),
                source_obligation_id=_clean_token(
                    record.get("source_obligation_id")
                ),
                run_id=_clean_text(
                    record.get("run_id"),
                    limit=160,
                ),
                request_id=_clean_text(
                    record.get("request_id"),
                    limit=160,
                ),
                answer_contract_version=_clean_text(
                    record.get("answer_contract_version"),
                    limit=160,
                ),
                answer_contract_digest=_clean_text(
                    record.get("answer_contract_digest"),
                    limit=160,
                ),
                recovery_authorization_id=_clean_token(
                    record.get("recovery_authorization_id")
                ),
                recovery_authorization_digest=_clean_token(
                    record.get("recovery_authorization_digest")
                ),
                required_source_class=_clean_token(
                    record.get("required_source_class") or record.get("source_class")
                ),
                required_source_tier=_clean_token(record.get("required_source_tier")),
                required_currentness=_clean_token(record.get("required_currentness")),
                required_evidence_material_type=_clean_token(
                    record.get("required_evidence_material_type")
                    or record.get("required_material_type")
                ),
                aggregate_counts_insufficient=bool(
                    record.get("aggregate_counts_insufficient")
                ),
            )
            self.requirements[requirement_id] = requirement
        else:
            incoming_kind = _requirement_kind(record)
            if (
                requirement.requirement_kind in {"general", "unknown"}
                and incoming_kind not in {"general", "unknown"}
            ):
                requirement.requirement_kind = incoming_kind
            if not requirement.origin_ref:
                requirement.origin_ref = _clean_text(
                    record.get("origin_ref")
                    or record.get("answer_contract_ref")
                    or record.get("source_obligation_ref")
                )
            for field_name in (
                "component_id",
                "source_obligation_id",
                "run_id",
                "request_id",
                "answer_contract_version",
                "answer_contract_digest",
                "recovery_authorization_id",
                "recovery_authorization_digest",
            ):
                current = getattr(requirement, field_name)
                incoming = (
                    _clean_text(
                        record.get(field_name),
                        limit=160,
                    )
                    if field_name
                    in {
                        "run_id",
                        "request_id",
                        "answer_contract_version",
                        "answer_contract_digest",
                    }
                    else _clean_token(record.get(field_name))
                )
                if current and incoming and current != incoming:
                    raise ValueError(
                        "source requirement exact lineage binding conflict: "
                        f"{field_name}"
                    )
                if not current and incoming:
                    setattr(requirement, field_name, incoming)
            if not requirement.required_source_class:
                requirement.required_source_class = _clean_token(
                    record.get("required_source_class") or record.get("source_class")
                )
            if not requirement.required_evidence_material_type:
                requirement.required_evidence_material_type = _clean_token(
                    record.get("required_evidence_material_type")
                    or record.get("required_material_type")
                )
            if not requirement.required_source_tier:
                requirement.required_source_tier = _clean_token(
                    record.get("required_source_tier")
                )
            if not requirement.required_currentness:
                requirement.required_currentness = _clean_token(
                    record.get("required_currentness")
                )
            requirement.aggregate_counts_insufficient = (
                requirement.aggregate_counts_insufficient
                or bool(record.get("aggregate_counts_insufficient"))
            )
        linked = _list(record.get("linked_candidate_ids"))
        for candidate_id in linked:
            self._link_candidate(
                requirement_id,
                _clean_token(candidate_id),
                reason="requirement_declared_link",
            )

    def _admit_candidate(
        self,
        record: Any,
        *,
        observation_id: str,
        source: str,
    ) -> None:
        if not isinstance(record, Mapping):
            return
        if record.get("aggregate_only") is True:
            self._gap(
                EvidenceCustodyGapType.LEGACY_AGGREGATE_ONLY_PATH,
                requirement_id=_clean_token(record.get("requirement_id")),
                reason=_clean_text(record.get("reason"))
                or "aggregate candidate observation has no candidate identity",
                source_ref=source,
            )
            req = self.requirements.get(_clean_token(record.get("requirement_id")))
            if req is not None:
                req.aggregate_counts_insufficient = True
            return
        candidate_id = _candidate_id(record, index=len(self.candidates) + 1)
        if not candidate_id:
            self._gap(
                EvidenceCustodyGapType.MISSING_CANDIDATE_IDENTITY,
                requirement_id=_clean_token(record.get("requirement_id")),
                reason="candidate observation lacked stable candidate id/url/title",
                source_ref=source,
            )
            return
        update = _candidate_update(record, candidate_id=candidate_id)
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            candidate = EvidenceCandidate(candidate_id=candidate_id)
            self.candidates[candidate_id] = candidate
        candidate.merge(update)

        record_kind = _record_kind(record)
        disposition = _candidate_disposition(record)
        if record_kind is CandidateCustodyKind.FACT:
            candidate.fact_disposition = disposition
            candidate.disposition_reason = (
                _clean_text(record.get("reason") or record.get("disposition_reason"))
                or candidate.disposition_reason
            )
        elif record_kind is CandidateCustodyKind.HELPER_ASSESSMENT:
            candidate.helper_assessment = disposition.value
            self._gap(
                EvidenceCustodyGapType.HELPER_CONTROLLER_ASSESSMENT_NOT_PROMOTABLE,
                candidate_id=candidate_id,
                requirement_id=_clean_token(record.get("requirement_id")),
                reason="helper assessment recorded but not promoted as fact",
                source_ref=source,
            )
        else:
            candidate.proposal_disposition = disposition.value

        self.custody_records.append(
            CandidateCustodyRecord(
                candidate_id=candidate_id,
                record_kind=record_kind,
                disposition=disposition,
                reason=_clean_text(
                    record.get("reason")
                    or record.get("disposition_reason")
                    or record.get("rejection_reason")
                ),
                source=source,
                requirement_id=_clean_token(record.get("requirement_id")),
                observation_id=observation_id,
            )
        )
        requirement_ids = _candidate_requirement_ids(record)
        for requirement_id in requirement_ids:
            self._link_candidate(
                requirement_id,
                candidate_id,
                reason=_clean_text(record.get("link_reason"))
                or "candidate_observation_link",
                status=disposition.value,
            )
        candidate_already_has_requirement_lineage = any(
            link.candidate_id == candidate_id for link in self.links
        )
        if not requirement_ids and not candidate_already_has_requirement_lineage:
            for requirement in self.requirements.values():
                if _candidate_satisfies_requirement(candidate, requirement):
                    self._link_candidate(
                        requirement.requirement_id,
                        candidate_id,
                        reason="selected_candidate_matches_existing_requirement",
                        status=disposition.value,
                    )
        if disposition is CandidateDisposition.DROPPED:
            self._gap(
                EvidenceCustodyGapType.CANDIDATE_DROPPED_WITHOUT_DISPOSITION,
                candidate_id=candidate_id,
                requirement_id=next(iter(requirement_ids), None),
                reason="candidate dropped before accepted/rejected disposition",
                source_ref=source,
            )
        if _bad_readability(candidate):
            self._gap(
                EvidenceCustodyGapType.MISSING_READABLE_SOURCE,
                candidate_id=candidate_id,
                requirement_id=next(iter(requirement_ids), None),
                reason="candidate is not readable/fetchable",
                source_ref=source,
            )

    def _link_candidate(
        self,
        requirement_id: str | None,
        candidate_id: str | None,
        *,
        reason: str | None = None,
        status: str | None = None,
    ) -> None:
        if not requirement_id or not candidate_id:
            return
        requirement = self.requirements.get(requirement_id)
        if requirement is None:
            requirement = SourceRequirementRecord(
                requirement_id=requirement_id,
                requirement_kind=_kind_for_requirement_id(requirement_id),
                required_source_class=_required_class_for_requirement_id(requirement_id),
            )
            self.requirements[requirement_id] = requirement
        if candidate_id not in requirement.linked_candidate_ids:
            requirement.linked_candidate_ids.append(candidate_id)
        existing_link_index = next(
            (
                index
                for index, link in enumerate(self.links)
                if link.requirement_id == requirement_id
                and link.candidate_id == candidate_id
            ),
            None,
        )
        if existing_link_index is None:
            self.links.append(
                SourceObligationLink(
                    requirement_id=requirement_id,
                    candidate_id=candidate_id,
                    link_reason=reason,
                    link_status=status,
                )
            )
        elif status in {"accepted", "partially_accepted"} and (
            self.links[existing_link_index].link_status
            not in {"accepted", "partially_accepted"}
        ):
            self.links[existing_link_index] = SourceObligationLink(
                requirement_id=requirement_id,
                candidate_id=candidate_id,
                link_reason=reason,
                link_status=status,
            )

    def _admit_aggregate_counts(self, value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for requirement_id, count in value.items():
            req_id = _clean_token(requirement_id)
            if not req_id:
                continue
            try:
                positive = int(count or 0) > 0
            except (TypeError, ValueError):
                positive = False
            if not positive:
                continue
            requirement = self.requirements.get(req_id)
            if requirement is None:
                requirement = SourceRequirementRecord(
                    requirement_id=req_id,
                    requirement_kind=_kind_for_requirement_id(req_id),
                    required_source_class=_required_class_for_requirement_id(req_id),
                )
                self.requirements[req_id] = requirement
            requirement.aggregate_counts_insufficient = True
            self._gap(
                EvidenceCustodyGapType.LEGACY_AGGREGATE_ONLY_PATH,
                requirement_id=req_id,
                reason="aggregate count observed without candidate identity",
                source_ref="aggregate_counts",
            )

    def _admit_final_evidence(self, value: Any) -> None:
        for index, evidence in enumerate(_list(value), start=1):
            if not isinstance(evidence, Mapping):
                continue
            candidate_id = _candidate_id(evidence, index=index)
            ref = _compact(
                {
                    "candidate_id": candidate_id,
                    "source_id": evidence.get("source_id"),
                    "url": _clean_text(evidence.get("url"), limit=500),
                    "title": _clean_text(evidence.get("title")),
                    "position": index,
                }
            )
            self.final_evidence_refs.append(ref)
            if not candidate_id or candidate_id not in self.candidates:
                self._gap(
                    EvidenceCustodyGapType.FINAL_EVIDENCE_SELECTED_WITHOUT_LEDGER_CUSTODY,
                    candidate_id=candidate_id,
                    reason="final evidence selected before ledger candidate custody",
                    source_ref="final_evidence",
                )

    def _admit_gap_record(self, record: Any, *, source: str) -> None:
        if not isinstance(record, Mapping):
            return
        gap_type = _coerce_enum(
            EvidenceCustodyGapType,
            record.get("gap_type"),
            EvidenceCustodyGapType.MISSING_CANDIDATE_IDENTITY.value,
        )
        self._gap(
            gap_type,
            requirement_id=_clean_token(record.get("requirement_id")),
            candidate_id=_clean_token(record.get("candidate_id")),
            reason=_clean_text(record.get("reason")),
            source_ref=_clean_text(record.get("source_ref")) or source,
        )

    def _admit_component_source_custody(self, record: Any) -> None:
        if not isinstance(record, Mapping):
            return
        component_id = _clean_component_id(record.get("component_id"))
        if not component_id:
            return
        safe_record = _component_source_custody_record(record)
        if safe_record:
            self.component_source_custody[component_id] = safe_record

    def _admit_fetch_read_candidate_custody(self, record: Any) -> None:
        if not isinstance(record, Mapping):
            return
        safe_record = _fetch_read_candidate_custody_record(record)
        if not safe_record:
            return
        key = (
            _clean_text(safe_record.get("reference_id"), limit=320)
            or _clean_text(safe_record.get("candidate_id"), limit=320)
            or f"fetch-read-candidate-custody:{len(self.fetch_read_candidate_custody) + 1}"
        )
        self.fetch_read_candidate_custody[key] = safe_record

    def _evaluate_requirements(self) -> None:
        for requirement in self.requirements.values():
            linked_candidates = [
                self.candidates[candidate_id]
                for candidate_id in requirement.linked_candidate_ids
                if candidate_id in self.candidates
            ]
            satisfying = [
                candidate
                for candidate in linked_candidates
                if _candidate_satisfies_requirement(candidate, requirement)
            ]
            if satisfying:
                requirement.status = SourceRequirementStatus.SATISFIED
                requirement.reason = "linked_candidate_satisfies_requirement"
                continue
            if linked_candidates:
                requirement.status = SourceRequirementStatus.UNSATISFIED
                requirement.reason = "no_linked_candidate_satisfies_requirement"
                if _strong_requirement(requirement):
                    self._gap(
                        EvidenceCustodyGapType.MISSING_SOURCE_CLASS_FIT,
                        requirement_id=requirement.requirement_id,
                        reason="linked candidates are lower-tier, stale, unreadable, or off-class",
                        source_ref="requirement_evaluation",
                    )
                continue
            if requirement.aggregate_counts_insufficient:
                requirement.status = SourceRequirementStatus.UNSATISFIED
                requirement.reason = "aggregate_counts_cannot_satisfy_custody"
                continue
            if _clean_text(requirement.origin_ref, limit=120) and (
                "offline_search_executor_bridge" in requirement.origin_ref
            ):
                requirement.status = SourceRequirementStatus.UNSATISFIED
                requirement.reason = "component_source_custody_missing_candidate"
                continue
            if _strong_requirement(requirement):
                requirement.status = SourceRequirementStatus.UNSATISFIED
                requirement.reason = "missing_official_current_candidate"
                self._gap(
                    EvidenceCustodyGapType.MISSING_OFFICIAL_CURRENT_CANDIDATE,
                    requirement_id=requirement.requirement_id,
                    reason="no linked candidate identity satisfies stronger obligation",
                    source_ref="requirement_evaluation",
                )
            else:
                requirement.status = SourceRequirementStatus.UNKNOWN
                requirement.reason = "requirement_has_no_linked_candidate_observation"

    def _gap(
        self,
        gap_type: EvidenceCustodyGapType,
        *,
        requirement_id: str | None = None,
        candidate_id: str | None = None,
        reason: str | None = None,
        source_ref: str | None = None,
    ) -> None:
        gap = EvidenceCustodyGap(
            gap_type=gap_type,
            requirement_id=requirement_id,
            candidate_id=candidate_id,
            reason=reason,
            source_ref=source_ref,
        )
        payload = gap.to_dict()
        if payload not in [existing.to_dict() for existing in self.gaps]:
            self.gaps.append(gap)


def build_evidence_ledger_observation_from_runtime(
    *,
    observation_id: str,
    observation_source: str,
    source_class_recovery_telemetry: Mapping[str, Any] | None = None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    final_evidence_selected: bool = False,
) -> EvidenceLedgerObservation:
    """Build a sanitized ledger observation from existing runtime projections."""

    telemetry = _safe_mapping(source_class_recovery_telemetry)
    custody = telemetry.get("official_current_source_custody")
    requirements: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    aggregate_counts: dict[str, int] = {}

    if isinstance(custody, Mapping):
        for requirement in _list(custody.get("requirements")):
            req_id = _clean_token(requirement.get("requirement_id"))
            source_class = _clean_token(requirement.get("source_class"))
            if not req_id:
                continue
            requirements.append(
                {
                    "requirement_id": req_id,
                    "requirement_kind": _kind_for_source_class(source_class),
                    "required_source_class": source_class,
                    "origin_ref": "official_current_source_custody",
                    "aggregate_counts_insufficient": False,
                }
            )
        for record in _list(custody.get("records")):
            req_id = _clean_token(record.get("requirement_id"))
            candidate_id = _clean_token(record.get("candidate_id"))
            status = _clean_token(record.get("status"))
            if status == OfficialCurrentCustodyStatus.CANDIDATE_AGGREGATE_ONLY.value:
                aggregate_counts[req_id] = aggregate_counts.get(req_id, 0) + 1
                continue
            if not candidate_id:
                continue
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "requirement_id": req_id,
                    "disposition": _disposition_from_official_current_status(status),
                    "record_kind": CandidateCustodyKind.FACT.value,
                    "reason": record.get("disposition_reason"),
                    "source_class": record.get("source_class")
                    or _required_class_for_requirement_id(req_id),
                    "eligible_for_stronger_obligation": status
                    in {
                        OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED.value,
                        OfficialCurrentCustodyStatus.CANDIDATE_PARTIALLY_ACCEPTED.value,
                    },
                }
            )
            links.append(
                {
                    "requirement_id": req_id,
                    "candidate_id": candidate_id,
                    "link_reason": "official_current_source_custody_record",
                    "link_status": status,
                }
            )

    source_candidates = []
    for index, source in enumerate(final_top_evidence or (), start=1):
        if not isinstance(source, Mapping):
            continue
        candidate_id = _candidate_id(source, index=index)
        if not candidate_id:
            continue
        source_custody_requirement_id = _clean_token(
            source.get("source_custody_requirement_id")
            or source.get("custody_requirement_id")
        )
        source_custody_required_class = _clean_token(
            source.get("required_source_class")
            or source.get("source_custody_required_source_class")
        )
        if source_custody_requirement_id and source_custody_required_class:
            requirements.append(
                {
                    "requirement_id": source_custody_requirement_id,
                    "requirement_kind": _kind_for_source_class(
                        source_custody_required_class
                    ),
                    "required_source_class": source_custody_required_class,
                    "required_source_tier": source.get("required_source_tier"),
                    "required_currentness": source.get("required_currentness"),
                    "required_evidence_material_type": source.get(
                        "required_evidence_material_type"
                    ),
                    "origin_ref": "source_custody_policy",
                    "aggregate_counts_insufficient": False,
                }
            )
            links.append(
                {
                    "requirement_id": source_custody_requirement_id,
                    "candidate_id": candidate_id,
                    "link_reason": source.get("source_custody_admission_reason")
                    or "source_custody_policy_candidate",
                    "link_status": "selected" if final_evidence_selected else "observed",
                }
            )
        selected_disposition = (
            CandidateDisposition.ACCEPTED.value
            if final_evidence_selected
            else CandidateDisposition.OBSERVED.value
        )
        stronger_obligation_eligible = (
            bool(final_evidence_selected)
            if source.get("component_gap_recovery_semantic_coverage_committed")
            is True
            else source.get("eligible_for_stronger_obligation")
        )
        source_candidates.append(
            {
                "candidate_id": candidate_id,
                "source_id": source.get("source_id"),
                "url": source.get("url"),
                "title": source.get("title"),
                "domain": source.get("domain") or source.get("normalized_domain"),
                "provider_name": source.get("provider_name")
                or source.get("provider"),
                "provider_role": source.get("provider_role")
                or source.get("_provider_role"),
                "retrieval_pass_id": source.get("retrieval_pass_id")
                or source.get("retrieval_stage"),
                "query_ref": source.get("query_ref")
                or source.get("query_preview")
                or source.get("query"),
                "source_tier": source.get("source_tier"),
                "source_class": source.get("source_class"),
                "currentness_signal": source.get("currentness_signal")
                or source.get("currentness"),
                "evidence_material_type": _evidence_material_type(source),
                "full_page_fetched": source.get("full_page_fetched"),
                "snippet_only": source.get("snippet_only"),
                "readable_status": source.get("readable_status")
                or source.get("readability_status")
                or "readable",
                "fetchable_status": source.get("fetchable_status")
                or source.get("fetch_status"),
                "disposition": selected_disposition,
                "record_kind": CandidateCustodyKind.FACT.value,
                "eligible_for_stronger_obligation": (
                    stronger_obligation_eligible
                ),
                "final_evidence_eligible": bool(final_evidence_selected),
            }
        )
    candidates.extend(source_candidates)

    payload: dict[str, Any] = {
        "observation_id": observation_id,
        "observation_source": observation_source,
        "requirements": requirements,
        "candidates": candidates,
        "requirement_links": links,
        "aggregate_counts": aggregate_counts,
    }
    if final_evidence_selected:
        payload["final_evidence"] = list(final_top_evidence or ())
    return EvidenceLedgerObservation(
        observation_id=observation_id,
        source=observation_source,
        payload=payload,
    )


def build_evidence_ledger_observation_from_run_contract(
    *,
    observation_id: str,
    contract_projection: Mapping[str, Any] | None,
    run_id: str | None = None,
    request_id: str | None = None,
    answer_contract_version: str | None = None,
    answer_contract_digest: str | None = None,
) -> EvidenceLedgerObservation:
    """Build ledger source requirements from canonical RunAuthority contract state."""

    projection = _safe_mapping(contract_projection)
    contract_id = _clean_token(projection.get("contract_id")) or "unknown_contract"
    requirements: list[dict[str, Any]] = []
    kind_aliases = {
        "official_current": "official_current",
        "legal_primary": "legal",
        "canonical_docs": "canonical",
        "source_bound_numeric": "source_bound",
        "academic": "academic",
        "user_document": "user_document",
        "reputable_secondary": "general",
    }
    for requirement in _list(projection.get("source_requirements")):
        if not isinstance(requirement, Mapping):
            continue
        req_id = _clean_token(requirement.get("requirement_id"))
        source_class = _clean_token(requirement.get("required_source_class"))
        if not req_id or not source_class:
            continue
        requirement_kind = _clean_token(requirement.get("requirement_kind"))
        requirements.append(
            {
                "requirement_id": req_id,
                "requirement_kind": kind_aliases.get(
                    requirement_kind,
                    requirement_kind or "general",
                ),
                "origin_ref": f"RunKernel.RunAuthorityContract:{contract_id}",
                "component_id": requirement.get("component_id"),
                "source_obligation_id": (
                    requirement.get("source_obligation_id")
                    or requirement.get("obligation_id")
                ),
                "run_id": (
                    requirement.get("run_id")
                    or projection.get("run_id")
                    or run_id
                ),
                "request_id": (
                    requirement.get("request_id")
                    or projection.get("request_id")
                    or request_id
                ),
                "answer_contract_version": (
                    requirement.get("answer_contract_version")
                    or projection.get("accepted_contract_version")
                    or projection.get("contract_version")
                    or answer_contract_version
                ),
                "answer_contract_digest": (
                    requirement.get("answer_contract_digest")
                    or projection.get("accepted_contract_digest")
                    or projection.get("contract_digest")
                    or answer_contract_digest
                ),
                "required_source_class": source_class,
                "required_source_tier": requirement.get("required_source_tier"),
                "required_currentness": requirement.get("required_currentness"),
                "aggregate_counts_insufficient": False,
            }
        )
    return EvidenceLedgerObservation(
        observation_id=observation_id,
        source="run_authority_contract",
        payload={
            "observation_id": observation_id,
            "observation_source": "run_authority_contract",
            "requirements": requirements,
            "contract_id": contract_id,
            "owner": "RunKernel.RunAuthorityContract",
        },
    )


def build_component_scoped_source_custody_observation_from_offline_search_executor_bridge(
    *,
    bridge_projection: Mapping[str, Any] | None,
    observation_id: str,
) -> EvidenceLedgerObservation:
    """Build ledger-owned component custody from the offline SearchExecutor bridge."""

    bridge = _safe_mapping(bridge_projection)
    requirements: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    component_custody: list[dict[str, Any]] = []

    for component in _list(bridge.get("component_observations")):
        if not isinstance(component, Mapping):
            continue
        component_record = _component_custody_from_bridge_component(component)
        if not component_record:
            continue
        component_custody.append(component_record)
        for obligation in _list(component_record.get("source_obligation_refs")):
            if not isinstance(obligation, Mapping):
                continue
            requirement_id = _clean_token(obligation.get("source_obligation_id"))
            if not requirement_id:
                continue
            requirements.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_kind": _requirement_kind_from_obligation(
                        obligation
                    ),
                    "origin_ref": (
                        "offline_search_executor_bridge:"
                        f"{component_record.get('component_id')}"
                    ),
                    "required_source_class": obligation.get("required_source_class")
                    or obligation.get("source_class"),
                    "aggregate_counts_insufficient": False,
                }
            )
        for candidate in _list(component_record.get("candidate_links")):
            if not isinstance(candidate, Mapping):
                continue
            candidate_id = _clean_token(candidate.get("candidate_id"))
            requirement_id = _clean_token(candidate.get("source_obligation_id"))
            if not candidate_id:
                continue
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "requirement_id": requirement_id,
                    "url": candidate.get("url"),
                    "domain": candidate.get("domain"),
                    "title": candidate.get("title"),
                    "source_class": candidate.get("source_class_hint")
                    or candidate.get("required_source_class"),
                    "record_kind": CandidateCustodyKind.PROPOSAL.value,
                    "disposition": CandidateDisposition.PROPOSED.value,
                    "reason": "offline bridge candidate link only",
                    "fetchable_status": "not_fetched",
                    "readable_status": "not_read",
                    "eligible_for_stronger_obligation": False,
                    "final_evidence_eligible": False,
                }
            )
            if requirement_id:
                links.append(
                    {
                        "requirement_id": requirement_id,
                        "candidate_id": candidate_id,
                        "link_reason": "offline_bridge_component_candidate_link",
                        "link_status": "blocked_by_unfetched_or_unread_candidate",
                    }
                )
        for gap in _list(component_record.get("custody_gaps")):
            if isinstance(gap, Mapping):
                gaps.append(dict(gap))

    return EvidenceLedgerObservation(
        observation_id=observation_id,
        source="offline_search_executor_bridge_component_source_custody",
        payload={
            "observation_id": observation_id,
            "observation_source": (
                "offline_search_executor_bridge_component_source_custody"
            ),
            "requirements": requirements,
            "candidates": candidates,
            "requirement_links": links,
            "custody_gaps": gaps,
            "component_source_custody": component_custody,
            "owner": "RunKernel.EvidenceLedger",
        },
    )


def source_class_facts_from_evidence_ledger_projection(
    projection: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Return AnswerContract-ready source-class facts from ledger projection."""

    if not isinstance(projection, Mapping):
        return {"present": (), "missing": ()}
    requirements = _list(projection.get("source_requirements"))
    present: list[str] = []
    missing: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            continue
        source_class = _clean_token(requirement.get("required_source_class"))
        status = _clean_token(requirement.get("status"))
        if not source_class:
            continue
        if status == SourceRequirementStatus.SATISFIED.value:
            _append_unique(present, source_class)
        elif status in {
            SourceRequirementStatus.UNSATISFIED.value,
            SourceRequirementStatus.PARTIALLY_SATISFIED.value,
        }:
            _append_unique(missing, source_class)
    return {"present": tuple(present), "missing": tuple(missing)}


def _candidate_update(record: Mapping[str, Any], *, candidate_id: str) -> dict[str, Any]:
    url = _clean_text(record.get("url") or record.get("source_url"), limit=500)
    source_class = _clean_token(record.get("source_class"))
    source_tier = _clean_token(record.get("source_tier"))
    lower_tier = (
        bool(record.get("contextual_only"))
        or source_class in _WEAK_SOURCE_CLASSES
        or source_tier in _WEAK_SOURCE_TIERS
    )
    domain = _clean_text(record.get("domain") or record.get("normalized_domain"), limit=160)
    if not domain:
        domain = _domain_from_url(url)
    return {
        "candidate_id": candidate_id,
        "url": url,
        "normalized_source_identity": _normalize_identity(
            record.get("normalized_source_identity") or url or candidate_id
        ),
        "title": _clean_text(record.get("title")),
        "domain": domain,
        "source_label": _clean_text(record.get("source_label") or record.get("label")),
        "provider_name": _clean_text(record.get("provider_name") or record.get("provider")),
        "provider_role": _clean_text(record.get("provider_role"), limit=120),
        "retrieval_pass_id": _clean_token(record.get("retrieval_pass_id")),
        "query_ref": _clean_text(
            record.get("query_ref")
            or record.get("query_preview")
            or record.get("query")
        ),
        "action_ref": _clean_token(record.get("action_ref") or record.get("action_id")),
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": _clean_token(
            record.get("currentness_signal") or record.get("currentness")
        ),
        "evidence_material_type": _evidence_material_type(record),
        "readable_status": _clean_token(
            record.get("readable_status") or record.get("readability_status")
        ),
        "fetchable_status": _clean_token(
            record.get("fetchable_status") or record.get("fetch_status")
        ),
        "disposition_reason": _clean_text(
            record.get("reason")
            or record.get("disposition_reason")
            or record.get("rejection_reason")
        ),
        "eligible_for_stronger_obligation": record.get(
            "eligible_for_stronger_obligation"
        ),
        "contextual_only": bool(record.get("contextual_only")) or lower_tier,
        "lower_tier": lower_tier,
        "final_evidence_eligible": record.get("final_evidence_eligible", UNKNOWN),
    }


def _evidence_material_type(record: Mapping[str, Any]) -> str | None:
    explicit = _clean_token(
        record.get("evidence_material_type")
        or record.get("material_type")
        or record.get("source_material_type")
    )
    if explicit:
        return explicit
    if record.get("full_page_fetched") is True:
        return "full_page_fetched"
    if record.get("snippet_only") is True:
        return "snippet_only"
    return None


def _candidate_disposition(record: Mapping[str, Any]) -> CandidateDisposition:
    raw = _clean_token(
        record.get("disposition")
        or record.get("fit_disposition")
        or record.get("final_disposition")
        or record.get("status")
    )
    aliases = {
        "candidate_accepted": CandidateDisposition.ACCEPTED.value,
        "candidate_partially_accepted": CandidateDisposition.PARTIALLY_ACCEPTED.value,
        "candidate_rejected": CandidateDisposition.REJECTED.value,
        "promoted_final_authority_evidence": CandidateDisposition.ACCEPTED.value,
        "matched_selected": CandidateDisposition.ACCEPTED.value,
        "rejected_with_reason": CandidateDisposition.REJECTED.value,
        "context": CandidateDisposition.CONTEXTUAL.value,
        "secondary": CandidateDisposition.LOWER_TIER.value,
        "candidate_returned": CandidateDisposition.OBSERVED.value,
    }
    raw = aliases.get(raw, raw)
    return _coerce_enum(CandidateDisposition, raw, CandidateDisposition.OBSERVED.value)


def _record_kind(record: Mapping[str, Any]) -> CandidateCustodyKind:
    raw = _clean_token(record.get("record_kind") or record.get("custody_kind"))
    return _coerce_enum(CandidateCustodyKind, raw, CandidateCustodyKind.FACT.value)


def _candidate_requirement_ids(record: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for value in (
        record.get("requirement_id"),
        record.get("custody_requirement_id"),
    ):
        clean = _clean_token(value)
        if clean:
            _append_unique(out, clean)
    for value in _list(record.get("linked_requirement_ids")):
        clean = _clean_token(value)
        if clean:
            _append_unique(out, clean)
    return out


def _candidate_satisfies_requirement(
    candidate: EvidenceCandidate,
    requirement: SourceRequirementRecord,
) -> bool:
    if candidate.fact_disposition not in {
        CandidateDisposition.ACCEPTED,
        CandidateDisposition.PARTIALLY_ACCEPTED,
    }:
        return False
    if _bad_readability(candidate):
        return False
    required_material = _clean_token(requirement.required_evidence_material_type)
    if required_material and _clean_token(candidate.evidence_material_type) != required_material:
        return False
    if _strong_requirement(requirement):
        if candidate.contextual_only or candidate.lower_tier:
            return False
        if not candidate.eligible_for_stronger_obligation:
            return False
        if _clean_token(candidate.currentness_signal) in _BAD_CURRENTNESS:
            return False
    required_class = _clean_token(requirement.required_source_class)
    if required_class and required_class not in {UNKNOWN, NOT_OBSERVABLE}:
        candidate_class = _clean_token(candidate.source_class)
        candidate_tier = _clean_token(candidate.source_tier)
        if required_class == "official_current_rules" and candidate_tier in _STRONG_SOURCE_TIERS:
            return True
        if required_class == "current_primary_or_official" and candidate_class in {
            "official_current_rules",
            "legal_or_regulatory_text",
            "primary_source_documents",
        }:
            return True
        if candidate_class != required_class:
            return False
    required_tier = _clean_token(requirement.required_source_tier)
    if required_tier and not _source_tier_satisfies_requirement(
        candidate,
        requirement,
    ):
        return False
    return True


def _candidate_requirement_rejection_reason(
    candidate: EvidenceCandidate,
    requirement: SourceRequirementRecord,
) -> str:
    if _bad_readability(candidate):
        return "candidate_not_readable_or_fetchable"
    required_material = _clean_token(requirement.required_evidence_material_type)
    if required_material and _clean_token(candidate.evidence_material_type) != required_material:
        return "candidate_material_type_does_not_satisfy_requirement"
    if _strong_requirement(requirement):
        if candidate.contextual_only or candidate.lower_tier:
            return "lower_tier_or_contextual_candidate_cannot_satisfy_stronger_obligation"
        if _clean_token(candidate.currentness_signal) in _BAD_CURRENTNESS:
            return "stale_or_off_topic_candidate_cannot_satisfy_current_obligation"
        if not candidate.eligible_for_stronger_obligation:
            return "candidate_not_eligible_for_stronger_obligation"
    if _clean_token(requirement.required_source_class) and (
        _clean_token(candidate.source_class) != _clean_token(requirement.required_source_class)
    ):
        if not (
            _clean_token(requirement.required_source_class) == "official_current_rules"
            and _clean_token(candidate.source_tier) in _STRONG_SOURCE_TIERS
        ) and not (
            _clean_token(requirement.required_source_class)
            == "current_primary_or_official"
            and _clean_token(candidate.source_class)
            in {
                "official_current_rules",
                "legal_or_regulatory_text",
                "primary_source_documents",
            }
        ):
            return "candidate_source_class_does_not_match_requirement"
    if _clean_token(requirement.required_source_tier) and not (
        _source_tier_satisfies_requirement(candidate, requirement)
    ):
        return "candidate_source_tier_does_not_match_requirement"
    return candidate.disposition_reason or "candidate_not_accepted_for_requirement"


def _source_tier_satisfies_requirement(
    candidate: EvidenceCandidate,
    requirement: SourceRequirementRecord,
) -> bool:
    required_tier = _clean_token(requirement.required_source_tier)
    candidate_tier = _clean_token(candidate.source_tier)
    if not required_tier:
        return True
    if candidate_tier == required_tier:
        return True
    return _canonical_technical_docs_tier_compatible(
        candidate,
        requirement,
        required_tier=required_tier,
        candidate_tier=candidate_tier,
    )


def _canonical_technical_docs_tier_compatible(
    candidate: EvidenceCandidate,
    requirement: SourceRequirementRecord,
    *,
    required_tier: str,
    candidate_tier: str,
) -> bool:
    if required_tier != "canonical" or candidate_tier not in {"official", "primary"}:
        return False
    required_class = _clean_token(requirement.required_source_class)
    if required_class != "primary_source_documents":
        return False
    if _clean_token(candidate.source_class) != "primary_source_documents":
        return False
    requirement_id = _clean_token(requirement.requirement_id)
    if requirement_id == "run_contract:canonical_docs":
        return True
    return _clean_token(requirement.requirement_kind) == "canonical_docs"


def _strong_requirement(requirement: SourceRequirementRecord) -> bool:
    return (
        _clean_token(requirement.requirement_kind) in _STRONG_REQUIREMENT_KINDS
        or _clean_token(requirement.required_source_class) in _STRONG_SOURCE_CLASSES
        or _clean_token(requirement.required_source_tier) in _STRONG_SOURCE_TIERS
        or _clean_token(requirement.required_currentness) in {"current", "official_current"}
    )


def _strong_source_candidate(candidate: EvidenceCandidate) -> bool:
    return (
        _clean_token(candidate.source_class) in _STRONG_SOURCE_CLASSES
        or _clean_token(candidate.source_class) == "sourced_numeric_values"
        or _clean_token(candidate.source_tier) in _STRONG_SOURCE_TIERS
        or (_clean_text(candidate.domain, limit=160) or "").endswith(".gov")
    ) and _clean_token(candidate.currentness_signal) not in _BAD_CURRENTNESS


def source_taxonomy_quality_facts(
    *, source_class: Any = None, source_tier: Any = None
) -> dict[str, Any]:
    """Project the canonical source taxonomy without changing ledger policy.

    This deliberately classifies source class and source tier independently.
    Consumers may require a positive strong fact, but must not treat an unknown
    value as strong or silently substitute one dimension for the other.
    """

    normalized_class = _clean_token(source_class) or "unknown"
    normalized_tier = _clean_token(source_tier) or "unknown"

    def strength(
        value: str, *, strong: frozenset[str], weak: frozenset[str]
    ) -> str:
        if value in strong:
            return "strong"
        if value in weak:
            return "weak"
        return "unknown"

    class_strength = strength(
        normalized_class,
        strong=_STRONG_SOURCE_CLASSES | {"sourced_numeric_values"},
        weak=_WEAK_SOURCE_CLASSES,
    )
    tier_strength = strength(
        normalized_tier,
        strong=_STRONG_SOURCE_TIERS,
        weak=_WEAK_SOURCE_TIERS,
    )
    return {
        "source_class": normalized_class,
        "source_tier": normalized_tier,
        "source_class_strength": class_strength,
        "source_tier_strength": tier_strength,
    }


def _bad_readability(candidate: EvidenceCandidate) -> bool:
    return (
        _clean_token(candidate.readable_status) in _BAD_READABILITY
        or _clean_token(candidate.fetchable_status) in _BAD_READABILITY
    )


def _requirement_kind(record: Mapping[str, Any]) -> str:
    raw = _clean_token(record.get("requirement_kind") or record.get("kind"))
    if raw:
        return raw
    return _kind_for_source_class(
        _clean_token(record.get("required_source_class") or record.get("source_class"))
    )


def _kind_for_requirement_id(requirement_id: str) -> str:
    source_class = _required_class_for_requirement_id(requirement_id)
    return _kind_for_source_class(source_class)


def _kind_for_source_class(source_class: str | None) -> str:
    source_class = _clean_token(source_class)
    if source_class in {"official_current_rules", "current_primary_or_official"}:
        return "official_current"
    if source_class in {"legal_or_regulatory_text", "historical_legal_text"}:
        return "legal"
    if source_class in {"primary_source_documents", "archival_primary_text"}:
        return "canonical"
    return "general"


def _required_class_for_requirement_id(requirement_id: str | None) -> str | None:
    value = _clean_token(requirement_id)
    if not value:
        return None
    if value.startswith("official_current_source:"):
        return value.split(":", 1)[1]
    if value in _STRONG_SOURCE_CLASSES:
        return value
    return None


def _disposition_from_official_current_status(status: str | None) -> str:
    if status == OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED.value:
        return CandidateDisposition.ACCEPTED.value
    if status == OfficialCurrentCustodyStatus.CANDIDATE_PARTIALLY_ACCEPTED.value:
        return CandidateDisposition.PARTIALLY_ACCEPTED.value
    if status == OfficialCurrentCustodyStatus.CANDIDATE_UNREADABLE.value:
        return CandidateDisposition.UNREADABLE.value
    if status == OfficialCurrentCustodyStatus.CANDIDATE_RETURNED.value:
        return CandidateDisposition.OBSERVED.value
    return CandidateDisposition.REJECTED.value


def _candidate_id(record: Mapping[str, Any], *, index: int) -> str:
    explicit = _clean_token(record.get("candidate_id"))
    if explicit:
        return explicit
    for key in ("url", "source_url", "normalized_source_identity", "source_identity"):
        value = _normalize_identity(record.get(key))
        if value:
            return f"candidate:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"
    source_id = _clean_token(record.get("source_id"))
    if source_id:
        return f"source-id:{source_id}"
    title = _clean_text(record.get("title"))
    if title:
        return f"title:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:16]}"
    return ""


def _normalize_identity(value: Any) -> str:
    text = _clean_text(value, limit=500) or ""
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.netloc:
        return text.casefold()
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


def _domain_from_url(value: Any) -> str | None:
    parsed = urlparse(str(value or "").strip())
    return parsed.netloc.casefold() or None


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        if _is_sensitive_key(key_text):
            continue
        safe = _safe_value(item)
        if safe is not None:
            out[key_text] = safe
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in list(value)[:_MAX_LIST_ITEMS]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:_MAX_LIST_ITEMS]]
    text = _clean_text(value)
    if any(pattern.search(text or "") for pattern in _SECRET_VALUE_PATTERNS):
        return None
    return text


def _clean_text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    if any(marker in text for marker in _SENSITIVE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        return ""
    return text.casefold().replace("-", "_").replace(" ", "_")[:limit]


def _is_sensitive_key(key: Any) -> bool:
    text = str(key or "").casefold()
    if text in _SENSITIVE_EXACT_KEYS:
        return True
    return any(marker in text for marker in _SENSITIVE_KEY_MARKERS)


def _list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)[:_MAX_LIST_ITEMS]
    return []


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _append_unique(target: list[str], value: str | None) -> None:
    if value and value not in target:
        target.append(value)


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _clean_component_id(value: Any, *, limit: int = 160) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        return ""
    return text.replace(" ", "_")[:limit]


def _component_custody_from_bridge_component(
    component: Mapping[str, Any],
) -> dict[str, Any]:
    component_id = _clean_component_id(component.get("component_id"))
    if not component_id:
        return {}
    obligations = [
        _source_obligation_ref_from_bridge(component_id, obligation)
        for obligation in _list(component.get("source_obligation_refs"))
        if isinstance(obligation, Mapping)
    ]
    obligations = [obligation for obligation in obligations if obligation]
    candidates = [
        _candidate_link_from_bridge(component_id, candidate)
        for candidate in _list(component.get("candidate_observation_refs"))
        if isinstance(candidate, Mapping)
    ]
    candidates = [candidate for candidate in candidates if candidate]
    candidate_obligation_ids = {
        _clean_token(candidate.get("source_obligation_id"))
        for candidate in candidates
        if _clean_token(candidate.get("source_obligation_id"))
    }
    gaps: list[dict[str, Any]] = []
    for obligation in obligations:
        obligation_id = _clean_token(obligation.get("source_obligation_id"))
        linked = obligation_id in candidate_obligation_ids
        obligation["source_obligation_status"] = (
            "blocked_by_unfetched_or_unread_candidate"
            if linked
            else "missing_candidate"
        )
        obligation["source_obligation_satisfied"] = False
        gaps.append(
            {
                "gap_type": (
                    EvidenceCustodyGapType.UNFETCHED_OR_UNREAD_COMPONENT_CANDIDATE.value
                    if linked
                    else EvidenceCustodyGapType.MISSING_COMPONENT_SOURCE_CANDIDATE.value
                ),
                "requirement_id": obligation_id,
                "reason": (
                    "offline bridge candidate is not fetched or read"
                    if linked
                    else "source obligation has no offline bridge candidate"
                ),
                "source_ref": f"offline_search_executor_bridge:{component_id}",
            }
        )
    return _safe_mapping(
        {
            "component_id": component_id,
            "component_id_normalized": _clean_token(component_id),
            "source_obligation_refs": obligations,
            "candidate_links": candidates,
            "custody_gaps": gaps,
            "source_obligation_count": len(obligations),
            "candidate_link_count": len(candidates),
            "candidate_links_are_evidence": False,
            "source_obligation_satisfied": False,
            "source_obligations_satisfied_by_candidate_presence": False,
            "evidence_bound": False,
            "citation_bound": False,
            "answer_value_bound": False,
            "full_component_success": False,
            "partial_user_answer_candidate": False,
            "final_answer_allowed": False,
            "author_payload_ready": False,
        }
    )


def _source_obligation_ref_from_bridge(
    component_id: str,
    obligation: Mapping[str, Any],
) -> dict[str, Any]:
    obligation_id = _clean_component_id(
        obligation.get("source_obligation_id")
        or obligation.get("requirement_id")
        or f"{component_id}:source-requirement"
    )
    if not obligation_id:
        return {}
    source_class = _clean_token(
        obligation.get("required_source_class")
        or obligation.get("source_class")
        or obligation.get("search_constraint")
    )
    return _safe_mapping(
        {
            "component_id": component_id,
            "source_obligation_id": obligation_id,
            "source": obligation.get("source") or "offline_search_executor_bridge",
            "kind": obligation.get("kind") or _kind_for_source_class(source_class),
            "required_source_class": source_class,
            "source_obligation_satisfied": False,
            "status": "unsatisfied",
        }
    )


def _candidate_link_from_bridge(
    component_id: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    ledger_shape = _safe_mapping(candidate.get("evidence_ledger_candidate_observation"))
    candidate_id = _clean_component_id(
        ledger_shape.get("candidate_id") or candidate.get("candidate_id")
    )
    if not candidate_id:
        return {}
    obligation_id = _clean_component_id(
        ledger_shape.get("source_obligation_id")
        or candidate.get("source_obligation_id")
        or candidate.get("requirement_id")
    )
    return _safe_mapping(
        {
            "component_id": component_id,
            "candidate_id": candidate_id,
            "source_obligation_id": obligation_id,
            "url": ledger_shape.get("url") or candidate.get("url"),
            "domain": ledger_shape.get("domain") or candidate.get("domain"),
            "title": ledger_shape.get("title") or candidate.get("title"),
            "source_class_hint": ledger_shape.get("source_class_hint")
            or candidate.get("source_class_hint")
            or candidate.get("source_class"),
            "candidate_kind": "offline_bridge_candidate_observation",
            "custody_status": "blocked_by_unfetched_or_unread_candidate",
            "fetched": False,
            "read": False,
            "evidence_ledger_admitted": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "semantic_coverage": False,
            "final_evidence": False,
            "evidence_bound": False,
            "citation_bound": False,
            "answer_value_bound": False,
            "full_component_success": False,
            "partial_user_answer_candidate": False,
            "final_answer_allowed": False,
            "author_payload_ready": False,
        }
    )


def _component_source_custody_record(record: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(record)
    component_id = _clean_component_id(safe.get("component_id"))
    if not component_id:
        return {}
    safe["component_id"] = component_id
    safe["candidate_links_are_evidence"] = False
    safe["source_obligations_satisfied_by_candidate_presence"] = False
    for field_name in (
        "evidence_bound",
        "citation_bound",
        "answer_value_bound",
        "full_component_success",
        "partial_user_answer_candidate",
        "final_answer_allowed",
        "author_payload_ready",
    ):
        safe[field_name] = False
    return safe


def _fetch_read_candidate_custody_record(record: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = _clean_text(record.get("candidate_id"), limit=320)
    reference_id = _clean_text(record.get("reference_id"), limit=320)
    navigation_origin = record.get("origin") == "searchos_navigation"
    if not reference_id or (not navigation_origin and not candidate_id):
        return {}
    if navigation_origin and any(
        not _safe_mapping(record.get(key))
        for key in (
            "component_ref",
            "source_obligation_ref",
            "slot_ref",
            "navigation_option_ref",
            "navigation_selection_ref",
            "destination_binding_ref",
            "parent_read_custody_ref",
            "terminal_receipt_ref",
            "custody_authorization_ref",
        )
    ):
        return {}
    status = _clean_token(record.get("fetch_read_status"), limit=80)
    if status not in {"readable", "unreadable", "failed", "skipped", "blocked"}:
        status = "unreadable"
    disposition = _clean_token(record.get("disposition"), limit=80)
    if disposition not in {
        CandidateDisposition.OBSERVED.value,
        CandidateDisposition.UNREADABLE.value,
        CandidateDisposition.UNFETCHABLE.value,
    }:
        disposition = (
            CandidateDisposition.OBSERVED.value
            if status == "readable"
            else CandidateDisposition.UNREADABLE.value
        )
    payload = {
        "record_kind": "fetch_read_candidate_custody",
        "origin": "searchos_navigation" if navigation_origin else None,
        "candidate_id": candidate_id,
        "candidate_digest": _clean_text(record.get("candidate_digest"), limit=128),
        "search_result_candidate_record_digest": _clean_text(
            record.get("search_result_candidate_record_digest"),
            limit=128,
        ),
        "reference_id": reference_id,
        "reference_digest": _clean_text(record.get("reference_digest"), limit=128),
        "run_id": _clean_text(record.get("run_id"), limit=160),
        "request_id": _clean_text(record.get("request_id"), limit=160),
        "current_answer_contract_ref": _safe_mapping(
            record.get("current_answer_contract_ref")
        ),
        "current_answer_contract_digest": _clean_text(
            record.get("current_answer_contract_digest"),
            limit=128,
        ),
        "component_ref": _safe_mapping(record.get("component_ref")),
        "source_obligation_ref": _safe_mapping(
            record.get("source_obligation_ref")
        ),
        "slot_ref": _safe_mapping(record.get("slot_ref")),
        "navigation_option_ref": _safe_mapping(
            record.get("navigation_option_ref")
        ),
        "navigation_selection_ref": _safe_mapping(
            record.get("navigation_selection_ref")
        ),
        "destination_binding_ref": _safe_mapping(
            record.get("destination_binding_ref")
        ),
        "parent_read_custody_ref": _safe_mapping(
            record.get("parent_read_custody_ref")
        ),
        "terminal_receipt_ref": _safe_mapping(
            record.get("terminal_receipt_ref")
        ),
        "custody_authorization_ref": _safe_mapping(
            record.get("custody_authorization_ref")
        ),
        "search_executor_handoff_ref": _safe_mapping(
            record.get("search_executor_handoff_ref")
        ),
        "search_executor_handoff_digest": _clean_text(
            record.get("search_executor_handoff_digest"),
            limit=128,
        ),
        "search_result_candidate_packet_ref": _safe_mapping(
            record.get("search_result_candidate_packet_ref")
        ),
        "search_result_candidate_packet_id": _clean_text(
            record.get("search_result_candidate_packet_id"),
            limit=320,
        ),
        "search_result_candidate_packet_digest": _clean_text(
            record.get("search_result_candidate_packet_digest"),
            limit=128,
        ),
        "fetch_read_content_packet_ref": _safe_mapping(
            record.get("fetch_read_content_packet_ref")
        ),
        "fetch_read_content_packet_id": _clean_text(
            record.get("fetch_read_content_packet_id"),
            limit=320,
        ),
        "fetch_read_content_packet_digest": _clean_text(
            record.get("fetch_read_content_packet_digest"),
            limit=128,
        ),
        "search_task_id": _clean_text(record.get("search_task_id"), limit=260),
        "query_intent_id": _clean_text(record.get("query_intent_id"), limit=260),
        "component_id": _clean_text(record.get("component_id"), limit=260),
        "source_obligation_candidate_ids": _clean_text_list(
            record.get("source_obligation_candidate_ids"),
            limit=260,
        ),
        "candidate_title": _clean_text(record.get("candidate_title")),
        "candidate_url": _clean_text(record.get("candidate_url"), limit=700),
        "candidate_domain": _clean_text(record.get("candidate_domain"), limit=260),
        "attempted_url": _clean_text(record.get("attempted_url"), limit=700),
        "provider_reported_url": _clean_text(
            record.get("provider_reported_url"),
            limit=700,
        ),
        "resolved_url": _clean_text(record.get("resolved_url"), limit=700),
        "final_url": _clean_text(record.get("final_url"), limit=700),
        "canonical_url": _clean_text(record.get("canonical_url"), limit=700),
        "resolved_domain": _clean_text(record.get("resolved_domain"), limit=260),
        "fetch_read_status": status,
        "disposition": disposition,
        "bounded_content_present": bool(record.get("bounded_content_present")),
        "bounded_character_count": _positive_int(
            record.get("bounded_character_count")
        ),
        "excerpt_digest": _clean_text(record.get("excerpt_digest"), limit=128),
        "read_error_code": _clean_text(record.get("read_error_code"), limit=120),
        "failure_reason": _clean_text(record.get("failure_reason"), limit=500),
        "lineage_only": True,
        "eligible_for_stronger_obligation": False,
        "final_evidence_eligible": False,
        "semantic_support_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "component_coverage_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
    }
    return _compact(payload)


def _fetch_read_candidate_custody_gap(record: Mapping[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "gap_type": EvidenceCustodyGapType.MISSING_READABLE_SOURCE.value,
            "candidate_id": _clean_text(record.get("candidate_id"), limit=320),
            "reference_id": _clean_text(record.get("reference_id"), limit=320),
            "fetch_read_status": _clean_token(record.get("fetch_read_status")),
            "read_error_code": _clean_text(record.get("read_error_code"), limit=120),
            "failure_reason": _clean_text(record.get("failure_reason"), limit=500),
            "reason": _clean_text(record.get("failure_reason"), limit=500)
            or "fetch/read reference is not readable",
            "source_ref": _clean_text(
                record.get("fetch_read_content_packet_id"),
                limit=320,
            ),
        }
    )


def _clean_text_list(value: Any, *, limit: int = 160) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _list(value):
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _requirement_kind_from_obligation(obligation: Mapping[str, Any]) -> str:
    return (
        _clean_token(obligation.get("kind"))
        or _kind_for_source_class(_clean_token(obligation.get("required_source_class")))
        or "general"
    )


def _component_custody_false_flags() -> dict[str, bool]:
    return {
        "live_search_executed": False,
        "provider_selected": False,
        "provider_called": False,
        "model_called": False,
        "fetch_read_executed": False,
        "retrieval_executed": False,
        "evidence_ledger_admitted": False,
        "citation_rendering_performed": False,
        "author_called": False,
        "candidate_links_are_evidence": False,
        "source_obligations_satisfied_by_candidate_presence": False,
        "evidence_bound": False,
        "citation_bound": False,
        "answer_value_bound": False,
        "full_component_success": False,
        "partial_user_answer_candidate": False,
        "final_answer_allowed": False,
        "author_payload_ready": False,
    }


def _fetch_read_candidate_custody_false_flags() -> dict[str, bool]:
    return {
        "semantic_support_created": False,
        "citation_eligible": False,
        "citation_created": False,
        "source_obligation_satisfied": False,
        "source_obligations_satisfied_by_candidate_presence": False,
        "component_coverage_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
        "bounded_content_payload_retained": False,
        "private_payload_retained": False,
    }


def _coerce_enum(enum_cls: type[Enum], value: Any, default: str) -> Any:
    raw = value.value if isinstance(value, Enum) else _clean_token(value)
    try:
        return enum_cls(raw or default)
    except ValueError:
        return enum_cls(default)


__all__ = [
    "COMPONENT_SCOPED_SOURCE_CUSTODY_NEXT_CONSUMER",
    "COMPONENT_SCOPED_SOURCE_CUSTODY_SCHEMA_VERSION",
    "COMPONENT_SCOPED_SOURCE_CUSTODY_TRACE_KEY",
    "EVIDENCE_LEDGER_SCHEMA_VERSION",
    "EVIDENCE_LEDGER_TRACE_KEY",
    "FETCH_READ_CANDIDATE_CUSTODY_NEXT_CONSUMER",
    "FETCH_READ_CANDIDATE_CUSTODY_SCHEMA_VERSION",
    "FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY",
    "CandidateCustodyKind",
    "CandidateCustodyRecord",
    "CandidateDisposition",
    "EvidenceCandidate",
    "EvidenceCustodyGap",
    "EvidenceCustodyGapType",
    "EvidenceLedger",
    "EvidenceLedgerObservation",
    "EvidenceLedgerProjection",
    "SourceObligationLink",
    "SourceRequirementRecord",
    "SourceRequirementStatus",
    "build_component_scoped_source_custody_observation_from_offline_search_executor_bridge",
    "build_evidence_ledger_observation_from_run_contract",
    "build_evidence_ledger_observation_from_runtime",
    "source_class_facts_from_evidence_ledger_projection",
    "source_taxonomy_quality_facts",
]
