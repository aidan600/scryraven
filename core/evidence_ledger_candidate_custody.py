"""Fetch/read packet custody builder for EvidenceLedger.

This module admits validated ``FetchReadContentPacket`` /
``SanitizedContentReference`` records into EvidenceLedger candidate/content
custody. It preserves fetch/read lineage only; it does not create semantic
support, citations, source-obligation satisfaction, coverage, Sufficiency,
FinalAnswerPacket material, Author input, partial readiness, or product
correctness claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateDisposition,
    EvidenceLedger,
    EvidenceLedgerObservation,
)
from core.fetch_read_content_reference import (
    FETCH_READ_CONTENT_PACKET_V2_SCHEMA_VERSION,
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)
from core.searchos_navigation_runtime import (
    SearchOSNavigationPacketCommitRegistry,
)

FETCH_READ_CANDIDATE_CUSTODY_OBSERVATION_SOURCE = (
    "fetch_read_content_packet_candidate_custody"
)

_FETCH_READ_STATUSES = frozenset(
    {
        "readable",
        "unreadable",
        "failed",
        "skipped",
        "blocked",
    }
)

_FORBIDDEN_UPGRADE_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "analyst_material",
        "analyst_report",
        "author_input",
        "author_material",
        "citation",
        "citation_source",
        "citation_sources",
        "citations",
        "component_coverage",
        "component_coverage_record",
        "component_coverage_records",
        "coverage",
        "evidence",
        "evidence_sources",
        "final_answer",
        "final_answer_packet",
        "final_evidence",
        "linked_requirement_ids",
        "requirement_id",
        "requirement_links",
        "requirements",
        "satisfied_requirement_ids",
        "satisfied_requirements",
        "semantic_observation",
        "semantic_observations",
        "source_obligation_claim",
        "source_obligation_satisfaction",
        "source_obligation_support",
        "source_requirements",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "admitted_to_evidence_ledger",
        "admitted_source",
        "analyst_report_created",
        "analyst_report_ready",
        "answer_ready",
        "author_input_created",
        "author_input_ready",
        "citation_created",
        "citation_eligible",
        "citation_rendered",
        "component_coverage_created",
        "content_citation_eligible",
        "eligible_for_stronger_obligation",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "final_answer_packet_created",
        "final_answer_ready",
        "final_evidence_eligible",
        "partial_answer_ready",
        "product_correctness_claimed",
        "readiness_decided",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_satisfied",
        "source_obligation_support_created",
        "sufficiency_decided",
    }
)


class EvidenceLedgerCandidateCustodyError(ValueError):
    """Raised when fetch/read custody would upgrade into a closed surface."""


@dataclass(frozen=True, slots=True)
class NavigationEvidenceLedgerAdmissionResult:
    """Atomically admitted v2 ledger plus the first exact-URL observation."""

    evidence_ledger: EvidenceLedger
    observation: EvidenceLedgerObservation
    evidence_ledger_custody_ref: Mapping[str, Any]
    committed_fetch_read_packet: Mapping[str, Any]


def build_evidence_ledger_observation_from_fetch_read_content_packet(
    fetch_read_content_packet: Mapping[str, Any],
    *,
    observation_id: str | None = None,
) -> EvidenceLedgerObservation:
    """Build a sanitized EvidenceLedger observation from a fetch/read packet."""

    if (
        isinstance(fetch_read_content_packet, Mapping)
        and fetch_read_content_packet.get("schema_version") == FETCH_READ_CONTENT_PACKET_V2_SCHEMA_VERSION
    ):
        packet = validate_fetch_read_content_packet(fetch_read_content_packet)
        if packet.get("physical_acquisition_origin") == ("navigation_candidate"):
            raise EvidenceLedgerCandidateCustodyError("navigation v2 custody requires a transient packet commit ref")
        observation, _ = _navigation_observation_from_packet(
            packet,
            observation_id=observation_id,
        )
        return observation

    _reject_upgrade_claims(
        fetch_read_content_packet,
        context="fetch/read content packet",
    )
    packet = validate_fetch_read_content_packet(fetch_read_content_packet)
    _reject_upgrade_claims(packet, context="fetch/read content packet")

    packet_ref = fetch_read_content_packet_ref_from_packet(packet)
    observation_id = observation_id or (
        f"{packet['run_id']}:evidence-ledger:fetch-read-candidate-custody:"
        f"{packet['packet_digest'][:16]}"
    )
    custody_records = [
        _custody_record_from_reference(reference, packet=packet, packet_ref=packet_ref)
        for reference in packet["reference_records"]
    ]
    candidates = [
        _candidate_record_from_reference(reference)
        for reference in packet["reference_records"]
    ]
    payload = {
        "observation_id": observation_id,
        "observation_source": FETCH_READ_CANDIDATE_CUSTODY_OBSERVATION_SOURCE,
        "owner": "RunKernel.EvidenceLedger",
        "fetch_read_content_packet_ref": packet_ref,
        "source_obligation_candidate_ids_are_lineage_only": True,
        "candidate_content_custody_is_semantic_support": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "component_coverage_created": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
        "candidates": candidates,
        "fetch_read_candidate_custody": custody_records,
    }
    return EvidenceLedgerObservation(
        observation_id=observation_id,
        source=FETCH_READ_CANDIDATE_CUSTODY_OBSERVATION_SOURCE,
        payload=payload,
    )


def admit_navigation_packet_commit_to_evidence_ledger(
    *,
    evidence_ledger: EvidenceLedger,
    packet_registry: SearchOSNavigationPacketCommitRegistry,
    packet_commit_ref: Mapping[str, Any],
    observation_id: str | None = None,
) -> NavigationEvidenceLedgerAdmissionResult:
    """Atomically admit a local v2 packet and first publish its exact URL."""

    if not isinstance(evidence_ledger, EvidenceLedger):
        raise EvidenceLedgerCandidateCustodyError(
            "navigation custody requires EvidenceLedger"
        )
    if not isinstance(packet_registry, SearchOSNavigationPacketCommitRegistry):
        raise EvidenceLedgerCandidateCustodyError(
            "navigation custody requires transient packet registry"
        )
    try:
        local_packet = packet_registry.resolve(packet_commit_ref)
        packet = validate_fetch_read_content_packet(local_packet)
        observation, custody_ref = _navigation_observation_from_packet(
            packet,
            observation_id=observation_id,
        )
        trial = deepcopy(evidence_ledger)
        trial.reduce_observation(observation)
    except Exception:
        packet_registry.discard(packet_commit_ref)
        raise
    committed = packet_registry.commit_success(packet_commit_ref)
    return NavigationEvidenceLedgerAdmissionResult(
        evidence_ledger=trial,
        observation=observation,
        evidence_ledger_custody_ref=custody_ref,
        committed_fetch_read_packet=committed,
    )


def validate_navigation_evidence_ledger_observation(
    *,
    fetch_read_content_packet: Mapping[str, Any],
    observation: Mapping[str, Any],
    evidence_ledger_custody_ref: Mapping[str, Any],
) -> EvidenceLedgerObservation:
    """Rebuild and verify the successful v2 custody observation exactly."""

    packet = validate_fetch_read_content_packet(fetch_read_content_packet)
    observed = dict(observation)
    observation_id = str(observed.get("observation_id") or "")
    if not observation_id:
        raise EvidenceLedgerCandidateCustodyError(
            "navigation ledger observation identity missing"
        )
    expected, expected_custody_ref = _navigation_observation_from_packet(
        packet,
        observation_id=observation_id,
    )
    if (
        expected.to_dict() != observed
        or expected_custody_ref != dict(evidence_ledger_custody_ref)
    ):
        raise EvidenceLedgerCandidateCustodyError(
            "navigation ledger observation does not match committed packet"
        )
    return expected


def _navigation_observation_from_packet(
    packet: Mapping[str, Any],
    *,
    observation_id: str | None,
) -> tuple[EvidenceLedgerObservation, dict[str, str]]:
    if packet.get("schema_version") != FETCH_READ_CONTENT_PACKET_V2_SCHEMA_VERSION:
        raise EvidenceLedgerCandidateCustodyError("v2 custody requires fetch/read packet v2")
    origin = str(packet.get("physical_acquisition_origin") or "")
    if origin not in {"discovery_candidate", "navigation_candidate"}:
        raise EvidenceLedgerCandidateCustodyError("v2 custody physical acquisition origin invalid")
    references = packet.get("reference_records")
    if not isinstance(references, list) or len(references) != 1:
        raise EvidenceLedgerCandidateCustodyError("v2 custody requires one sanitized reference")
    reference = dict(references[0])
    packet_ref = fetch_read_content_packet_ref_from_packet(packet)
    candidate_id = (
        f"navigation-physical-source:{packet['physical_identity_digest'][:24]}"
        if origin == "navigation_candidate"
        else str(
            dict(packet.get("discovery_candidate_ref") or {}).get("candidate_id")
            or (f"discovery-physical-source:{packet['physical_identity_digest'][:24]}")
        )
    )
    custody_core = {
        "fetch_read_content_packet_ref": packet_ref,
        "physical_acquisition_ref": packet["physical_acquisition_ref"],
        "physical_acquisition_origin": origin,
        "candidate_id": candidate_id,
        "sanitized_content_reference_ref": {
            "sanitized_content_reference_id": reference["sanitized_content_reference_id"],
            "sanitized_content_reference_digest": reference["sanitized_content_reference_digest"],
        },
        "physical_identity_digest": packet["physical_identity_digest"],
        "full_destination_digest": packet["full_destination_digest"],
        "durable_source_url": packet["durable_source_url"],
        "attempted_url": packet["attempted_url"],
    }
    custody_digest = _stable_digest(custody_core)
    custody_ref = {
        "evidence_ledger_custody_id": (f"evidence-ledger-{origin}-custody:{custody_digest[:24]}"),
        "evidence_ledger_custody_digest": custody_digest,
    }
    observation_identity = observation_id or (
        f"{packet['run_id']}:evidence-ledger:{origin}-custody:{custody_digest[:20]}"
    )
    custody_record = {
        "record_kind": "fetch_read_candidate_custody",
        "candidate_id": candidate_id,
        "candidate_digest": packet["full_destination_digest"],
        "reference_id": reference["sanitized_content_reference_id"],
        "reference_digest": reference["sanitized_content_reference_digest"],
        "run_id": packet["run_id"],
        "request_id": packet["request_id"],
        "fetch_read_content_packet_ref": packet_ref,
        "fetch_read_content_packet_id": packet["fetch_read_content_packet_id"],
        "fetch_read_content_packet_digest": packet["fetch_read_content_packet_digest"],
        "evidence_ledger_custody_ref": custody_ref,
        "physical_acquisition_ref": packet["physical_acquisition_ref"],
        "physical_acquisition_origin": origin,
        "operation_identity_key": packet["operation_identity_key"],
        "physical_identity_digest": packet["physical_identity_digest"],
        "full_destination_digest": packet["full_destination_digest"],
        "attempted_source_full_digest": packet["attempted_source_full_digest"],
        "attempted_url": packet["attempted_url"],
        "durable_source_url": packet["durable_source_url"],
        "candidate_url": packet["durable_source_url"],
        "candidate_domain": packet["source_domain"],
        "candidate_title": reference.get("content_title") or packet["source_domain"],
        "fetch_read_status": "readable",
        "disposition": CandidateDisposition.OBSERVED.value,
        "bounded_content_present": True,
        "bounded_character_count": reference["bounded_character_count"],
        "excerpt_digest": reference["bounded_text_digest"],
        "retained_digest": packet["retained_digest"],
        "retained_character_count": packet["retained_character_count"],
        "lineage_only": True,
        "eligible_for_stronger_obligation": False,
        "final_evidence_eligible": False,
        "semantic_support_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
    }
    if origin == "navigation_candidate":
        custody_record.update(
            {
                "navigation_destination_binding_ref": packet["navigation_destination_binding_ref"],
                "navigation_edge_ref": packet["navigation_edge_ref"],
                "navigation_selection_ref": packet["navigation_selection_ref"],
                "navigation_lineage_snapshot_ref": packet["navigation_lineage_snapshot_ref"],
                "representative_contributor_ref": packet["representative_contributor_ref"],
                "parent_custody_ref": packet["parent_custody_ref"],
            }
        )
    else:
        custody_record.update(
            {
                "physical_source_binding_ref": packet["physical_source_binding_ref"],
                "discovery_candidate_ref": packet["discovery_candidate_ref"],
                "search_result_candidate_packet_ref": packet["search_result_candidate_packet_ref"],
            }
        )
    observation_source = f"{origin}_fetch_read_content_packet_candidate_custody"
    payload = {
        "observation_id": observation_identity,
        "observation_source": (observation_source),
        "owner": "RunKernel.EvidenceLedger",
        "fetch_read_content_packet_ref": packet_ref,
        "evidence_ledger_custody_ref": custody_ref,
        "durable_source_commit_boundary": True,
        "candidates": [
            {
                "candidate_id": candidate_id,
                "url": packet["durable_source_url"],
                "normalized_source_identity": packet["durable_source_url"],
                "domain": packet["source_domain"],
                "title": custody_record["candidate_title"],
                "provider_name": reference.get("provider"),
                "readable_status": "readable",
                "fetchable_status": "fetchable",
                "record_kind": CandidateCustodyKind.FACT.value,
                "disposition": CandidateDisposition.OBSERVED.value,
                "eligible_for_stronger_obligation": False,
                "final_evidence_eligible": False,
            }
        ],
        "fetch_read_candidate_custody": [custody_record],
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "semantic_support_created": False,
    }
    return (
        EvidenceLedgerObservation(
            observation_id=observation_identity,
            source=observation_source,
            payload=payload,
        ),
        custody_ref,
    )


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _candidate_record_from_reference(reference: Mapping[str, Any]) -> dict[str, Any]:
    status = _fetch_read_status(reference)
    return _without_empty(
        {
            "candidate_id": reference.get("candidate_id"),
            "url": reference.get("candidate_url"),
            "domain": reference.get("candidate_domain"),
            "title": reference.get("candidate_title"),
            "readable_status": _readable_status_for(status),
            "fetchable_status": _fetchable_status_for(status),
            "record_kind": CandidateCustodyKind.FACT.value,
            "disposition": _disposition_for(status),
            "reason": _reason_for(reference),
            "eligible_for_stronger_obligation": False,
            "final_evidence_eligible": False,
        }
    )


def _custody_record_from_reference(
    reference: Mapping[str, Any],
    *,
    packet: Mapping[str, Any],
    packet_ref: Mapping[str, Any],
) -> dict[str, Any]:
    status = _fetch_read_status(reference)
    return _without_empty(
        {
            "record_kind": "fetch_read_candidate_custody",
            "run_id": reference.get("run_id"),
            "request_id": reference.get("request_id"),
            "current_answer_contract_ref": reference.get(
                "current_answer_contract_ref"
            ),
            "current_answer_contract_digest": reference.get(
                "current_answer_contract_digest"
            ),
            "search_executor_handoff_ref": reference.get(
                "search_executor_handoff_ref"
            ),
            "search_executor_handoff_digest": reference.get(
                "search_executor_handoff_digest"
            ),
            "search_result_candidate_packet_ref": reference.get(
                "search_result_candidate_packet_ref"
            ),
            "search_result_candidate_packet_id": (
                reference.get("search_result_candidate_packet_ref") or {}
            ).get("packet_id"),
            "search_result_candidate_packet_digest": reference.get(
                "search_result_candidate_packet_digest"
            ),
            "fetch_read_content_packet_ref": packet_ref,
            "fetch_read_content_packet_id": packet.get("packet_id"),
            "fetch_read_content_packet_digest": packet.get("packet_digest"),
            "candidate_id": reference.get("candidate_id"),
            "candidate_digest": reference.get("candidate_digest"),
            "search_result_candidate_record_digest": reference.get(
                "search_result_candidate_record_digest"
            ),
            "reference_id": reference.get("reference_id"),
            "reference_digest": reference.get("reference_digest"),
            "search_task_id": reference.get("search_task_id"),
            "query_intent_id": reference.get("query_intent_id"),
            "component_id": reference.get("component_id"),
            "source_obligation_candidate_ids": reference.get(
                "source_obligation_candidate_ids"
            ),
            "candidate_title": reference.get("candidate_title"),
            "candidate_url": reference.get("candidate_url"),
            "candidate_domain": reference.get("candidate_domain"),
            "attempted_url": reference.get("attempted_url"),
            "provider_reported_url": reference.get("provider_reported_url"),
            "resolved_url": reference.get("resolved_url"),
            "final_url": reference.get("final_url"),
            "canonical_url": reference.get("canonical_url"),
            "resolved_domain": reference.get("resolved_domain"),
            "fetch_read_status": status,
            "disposition": _disposition_for(status),
            "bounded_content_present": bool(reference.get("excerpt_digest")),
            "bounded_character_count": _bounded_int(
                reference.get("bounded_character_count")
            ),
            "excerpt_digest": reference.get("excerpt_digest"),
            "read_error_code": reference.get("read_error_code"),
            "failure_reason": reference.get("failure_reason"),
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
    )


def _fetch_read_status(reference: Mapping[str, Any]) -> str:
    status = str(reference.get("fetch_read_status") or "").strip().casefold()
    if status not in _FETCH_READ_STATUSES:
        raise EvidenceLedgerCandidateCustodyError("unknown fetch/read status")
    return status


def _disposition_for(status: str) -> str:
    if status == "readable":
        return CandidateDisposition.OBSERVED.value
    if status in {"failed", "blocked", "skipped"}:
        return CandidateDisposition.UNFETCHABLE.value
    return CandidateDisposition.UNREADABLE.value


def _readable_status_for(status: str) -> str:
    if status == "readable":
        return "readable"
    if status == "unreadable":
        return "unreadable"
    if status == "blocked":
        return "blocked"
    return "not_readable"


def _fetchable_status_for(status: str) -> str:
    if status == "readable":
        return "fetchable"
    if status == "failed":
        return "fetch_failed"
    if status in {"blocked", "skipped"}:
        return "unfetchable"
    return "fetchable"


def _reason_for(reference: Mapping[str, Any]) -> str:
    status = _fetch_read_status(reference)
    if status == "readable":
        return "bounded fetch/read content reference observed"
    return str(
        reference.get("failure_reason")
        or reference.get("read_error_code")
        or "fetch/read reference is not readable"
    )


def _reject_upgrade_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_UPGRADE_KEYS)
    if forbidden:
        raise EvidenceLedgerCandidateCustodyError(
            f"{context} includes closed custody upgrade fields: "
            + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise EvidenceLedgerCandidateCustodyError(
            f"{context} opens closed custody upgrade claims: "
            + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


__all__ = [
    "FETCH_READ_CANDIDATE_CUSTODY_OBSERVATION_SOURCE",
    "EvidenceLedgerCandidateCustodyError",
    "NavigationEvidenceLedgerAdmissionResult",
    "admit_navigation_packet_commit_to_evidence_ledger",
    "build_evidence_ledger_observation_from_fetch_read_content_packet",
]
