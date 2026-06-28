"""Proposal-only evidence-relative Analyst report packet.

This module builds the first current meaning packet after EvidenceLedger
fetch/read custody.  It consumes custody IDs and digests plus injected offline
Analyst proposal records; it does not call models, providers, search, retrieval,
SemanticObservation admission, ComponentCoverage, Sufficiency, FinalAnswerPacket,
or Author surfaces.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION = (
    "evidence_relative_analysis_packet_ag_analyst_evidence_relative_report_01_v1"
)
ANALYST_REPORT_SCHEMA_VERSION = (
    "analyst_report_ag_analyst_evidence_relative_report_01_v1"
)
EVIDENCE_RELATIVE_ANALYSIS_PACKET_KIND = "evidence_relative_analysis_packet"
EVIDENCE_RELATIVE_ANALYSIS_PACKET_TRACE_KEY = "evidence_relative_analysis_packet"
EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER = "RunKernel.EvidenceRelativeAnalysisPacket"
ANALYST_REPORT_POSTURE = "proposal_only_evidence_relative_analysis"
FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY = "fetch_read_candidate_custody"

FINDING_PROPOSAL_KINDS = frozenset(
    {
        "apparent_relevance",
        "possible_support_proposal",
        "possible_contradiction",
        "caveat_proposal",
        "missing_fact",
        "currentness_concern",
        "scope_mismatch",
        "analysis_gap",
    }
)

GAP_KINDS = frozenset(
    {
        "analysis_missing",
        "analysis_gap",
        "missing_fact",
        "currentness_concern",
        "scope_mismatch",
        "unreadable_source",
        "missing_readable_source",
    }
)

READABLE_STATUS = "readable"

_CLOSED_FALSE_FLAGS = {
    "semantic_observation_admitted": False,
    "component_coverage_created": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
    "provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "model_called": False,
    "search_dispatched": False,
    "query_plan_created": False,
    "search_executor_handoff_created": False,
}

_PER_COMPONENT_FALSE_FLAGS = {
    "component_satisfied": False,
    "component_coverage_created": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "sufficiency_decided": False,
}

_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "body",
        "bounded_excerpt",
        "bounded_text",
        "cache",
        "cache_row",
        "cookie",
        "cookies",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "header",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "page_content",
        "page_corpus",
        "page_text",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "request_header",
        "request_headers",
        "response_header",
        "response_headers",
        "secret",
        "secrets",
        "snippet",
        "source_text",
        "text",
        "token",
        "unbounded_content",
        "unbounded_page_text",
        "unbounded_text",
    }
)

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "bounded_content_payload_retained",
        "private_payload_retained",
        "raw_content_retained",
        "raw_headers_retained",
        "raw_model_response_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "answer",
        "answer_material",
        "answer_ready",
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
        "coverage_state",
        "evidence_sources",
        "fap",
        "final_answer",
        "final_answer_packet",
        "final_claim",
        "semantic_observation",
        "semantic_observations",
        "source_obligation_claim",
        "source_obligation_satisfaction",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_FALSE_FLAGS,
        *_PER_COMPONENT_FALSE_FLAGS,
        "analyst_report_ready",
        "answer_ready",
        "author_input_ready",
        "citation_rendered",
        "component_satisfied",
        "content_citation_eligible",
        "coverage_decision",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "final_answer_ready",
        "final_evidence_eligible",
        "readiness_decided",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)

_REQUIRED_CUSTODY_KEYS = (
    "candidate_id",
    "reference_id",
    "reference_digest",
    "fetch_read_status",
)


class EvidenceRelativeAnalysisPacketError(ValueError):
    """Raised when evidence-relative analysis would open a closed surface."""


@dataclass(frozen=True, slots=True)
class EvidenceRelativeAnalysisPacket:
    """Standalone proposal-only packet over EvidenceLedger custody."""

    evidence_ledger_projection: Mapping[str, Any]
    analyst_proposal_records: Sequence[Mapping[str, Any]] = field(
        default_factory=tuple
    )
    run_id: str | None = None
    request_id: str | None = None
    current_answer_contract_ref: Mapping[str, Any] | None = None
    current_answer_contract_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return build_evidence_relative_analysis_packet(
            evidence_ledger_projection=self.evidence_ledger_projection,
            analyst_proposal_records=self.analyst_proposal_records,
            run_id=self.run_id,
            request_id=self.request_id,
            current_answer_contract_ref=self.current_answer_contract_ref,
            current_answer_contract_digest=self.current_answer_contract_digest,
        )


def build_evidence_relative_analysis_packet(
    *,
    evidence_ledger_projection: Mapping[str, Any],
    analyst_proposal_records: Sequence[Mapping[str, Any]] = (),
    run_id: str | None = None,
    request_id: str | None = None,
    current_answer_contract_ref: Mapping[str, Any] | None = None,
    current_answer_contract_digest: str | None = None,
) -> dict[str, Any]:
    """Build an ``EvidenceRelativeAnalysisPacket`` from ledger custody.

    ``analyst_proposal_records`` are offline/test-injected proposal facts.  They
    may point at readable custody; unreadable custody is represented only by gap
    proposals.
    """

    _reject_forbidden_surface_claims(
        evidence_ledger_projection,
        context="EvidenceLedger projection",
    )
    ledger_projection = _required_mapping(
        evidence_ledger_projection,
        "evidence ledger projection",
    )
    custody_projection = _custody_projection_from_ledger(ledger_projection)
    custody_records = _custody_records(custody_projection)
    custody_by_reference = _custody_index(custody_records)
    proposals = _proposal_records_or_error(analyst_proposal_records)
    run_id_value, request_id_value = _run_request_identity(
        records=custody_records,
        run_id=run_id,
        request_id=request_id,
    )
    contract_ref, contract_digest = _contract_binding(
        records=custody_records,
        current_answer_contract_ref=current_answer_contract_ref,
        current_answer_contract_digest=current_answer_contract_digest,
    )
    ledger_digest = _digest_json(ledger_projection)
    custody_digest = _digest_json(custody_projection)
    findings: list[dict[str, Any]] = []
    supplied_gap_records: list[dict[str, Any]] = []

    for index, proposal in enumerate(proposals):
        proposal_kind = _clean_token(
            proposal.get("proposal_kind")
            or proposal.get("finding_kind")
            or proposal.get("gap_kind"),
            limit=120,
        )
        if not proposal_kind:
            raise EvidenceRelativeAnalysisPacketError(
                "analyst proposal requires proposal_kind or gap_kind"
            )
        if proposal_kind in FINDING_PROPOSAL_KINDS:
            finding = _finding_from_proposal(
                proposal,
                index=index,
                custody_by_reference=custody_by_reference,
                custody_projection_digest=custody_digest,
            )
            findings.append(finding)
            if proposal_kind == "analysis_gap":
                supplied_gap_records.append(
                    _gap_from_proposal(
                        proposal,
                        index=index,
                        custody_by_reference=custody_by_reference,
                        custody_projection_digest=custody_digest,
                        trigger_finding_id=finding["finding_id"],
                    )
                )
            continue
        if proposal_kind in GAP_KINDS:
            supplied_gap_records.append(
                _gap_from_proposal(
                    proposal,
                    index=index,
                    custody_by_reference=custody_by_reference,
                    custody_projection_digest=custody_digest,
                )
            )
            continue
        raise EvidenceRelativeAnalysisPacketError(
            f"unsupported evidence-relative proposal kind: {proposal_kind}"
        )

    findings_by_reference = {
        finding["reference_id"]
        for finding in findings
        if _clean_token(finding.get("reference_id"), limit=320)
    }
    auto_gaps = _automatic_gap_proposals(
        custody_records=custody_records,
        findings_by_reference=findings_by_reference,
        custody_projection_digest=custody_digest,
    )
    gaps = _dedupe_by_id([*supplied_gap_records, *auto_gaps], key="gap_id")
    report = _analyst_report(
        run_id=run_id_value,
        request_id=request_id_value,
        findings=findings,
        gaps=gaps,
        custody_records=custody_records,
    )
    packet_base = _without_empty(
        {
            "schema_version": EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION,
            "packet_kind": EVIDENCE_RELATIVE_ANALYSIS_PACKET_KIND,
            "trace_key": EVIDENCE_RELATIVE_ANALYSIS_PACKET_TRACE_KEY,
            "owner": EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER,
            "canonical_state": False,
            "reduced_state": False,
            "proposal_only": True,
            "trace_only": False,
            "storage_only": False,
            "packet_posture": ANALYST_REPORT_POSTURE,
            "run_id": run_id_value,
            "request_id": request_id_value,
            "current_answer_contract_ref": contract_ref,
            "current_answer_contract_digest": contract_digest,
            "evidence_ledger_ref": {
                "schema_version": _clean_token(
                    ledger_projection.get("schema_version"),
                    limit=160,
                ),
                "trace_key": _clean_token(ledger_projection.get("trace_key"), limit=120),
                "owner": _clean_token(ledger_projection.get("owner"), limit=160),
                "projection_digest": ledger_digest,
            },
            "evidence_ledger_projection_digest": ledger_digest,
            "fetch_read_candidate_custody_ref": {
                "schema_version": _clean_token(
                    custody_projection.get("schema_version"),
                    limit=160,
                ),
                "trace_key": FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY,
                "projection_digest": custody_digest,
                "custody_record_count": len(custody_records),
                "readable_record_count": sum(
                    1
                    for record in custody_records
                    if record.get("fetch_read_status") == READABLE_STATUS
                ),
                "unreadable_record_count": sum(
                    1
                    for record in custody_records
                    if record.get("fetch_read_status") != READABLE_STATUS
                ),
            },
            "fetch_read_candidate_custody_count": len(custody_records),
            "analyst_report": report,
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    packet_digest = _digest_json(_packet_digest_payload(packet_base))
    packet_id = (
        "evidence-relative-analysis-packet:"
        f"{_clean_token(request_id_value, limit=120)}:{packet_digest[:16]}"
    )
    packet = {**packet_base, "packet_id": packet_id, "packet_digest": packet_digest}
    return validate_evidence_relative_analysis_packet(packet)


def validate_evidence_relative_analysis_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a packet and return a sanitized copy."""

    safe = _required_mapping(packet, "evidence-relative analysis packet")
    _reject_raw_private_only(safe, context="evidence-relative analysis packet")
    if safe.get("schema_version") != EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION:
        raise EvidenceRelativeAnalysisPacketError("analysis packet schema mismatch")
    if safe.get("packet_kind") != EVIDENCE_RELATIVE_ANALYSIS_PACKET_KIND:
        raise EvidenceRelativeAnalysisPacketError("analysis packet kind mismatch")
    if safe.get("owner") != EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER:
        raise EvidenceRelativeAnalysisPacketError("analysis packet owner mismatch")
    if safe.get("packet_posture") != ANALYST_REPORT_POSTURE:
        raise EvidenceRelativeAnalysisPacketError("analysis packet posture mismatch")
    if safe.get("canonical_state") is not False or safe.get("reduced_state") is not False:
        raise EvidenceRelativeAnalysisPacketError(
            "analysis packet must remain standalone proposal state"
        )
    _validate_closed_flags(safe, context="analysis packet")
    report = _required_mapping(safe.get("analyst_report"), "analyst report")
    _validate_report(report)
    if report.get("report_digest") != _digest_json(_report_digest_payload(report)):
        raise EvidenceRelativeAnalysisPacketError("analyst report digest mismatch")
    declared_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if declared_digest != _digest_json(_packet_digest_payload(safe)):
        raise EvidenceRelativeAnalysisPacketError("analysis packet digest mismatch")
    expected_id = (
        "evidence-relative-analysis-packet:"
        f"{_clean_token(safe.get('request_id'), limit=120)}:{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_id:
        raise EvidenceRelativeAnalysisPacketError("analysis packet id mismatch")
    return safe


def evidence_relative_analysis_packet_ref_from_packet(
    packet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact downstream reference for this proposal packet."""

    safe = _safe_mapping(packet)
    packet_id = _clean_token(safe.get("packet_id"), limit=260)
    packet_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if not packet_id or not packet_digest:
        return {}
    return _without_empty(
        {
            "packet_id": packet_id,
            "packet_digest": packet_digest,
            "schema_version": _clean_token(safe.get("schema_version")),
            "report_id": _clean_token(
                _safe_mapping(safe.get("analyst_report")).get("report_id"),
                limit=260,
            ),
            "report_digest": _clean_token(
                _safe_mapping(safe.get("analyst_report")).get("report_digest"),
                limit=128,
            ),
            "finding_count": _bounded_int(
                _safe_mapping(safe.get("analyst_report")).get("finding_count")
            ),
            "analysis_gap_count": _bounded_int(
                _safe_mapping(safe.get("analyst_report")).get(
                    "analysis_gap_proposal_count"
                )
            ),
        }
    )


def _analyst_report(
    *,
    run_id: str,
    request_id: str,
    findings: Sequence[Mapping[str, Any]],
    gaps: Sequence[Mapping[str, Any]],
    custody_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    analyzed_refs = {
        finding.get("reference_id")
        for finding in findings
        if _clean_token(finding.get("reference_id"), limit=320)
    }
    readable_refs = {
        record.get("reference_id")
        for record in custody_records
        if record.get("fetch_read_status") == READABLE_STATUS
    }
    unreadable_gap_count = sum(
        1
        for gap in gaps
        if gap.get("gap_kind") in {"unreadable_source", "missing_readable_source"}
    )
    report_base = _without_empty(
        {
            "schema_version": ANALYST_REPORT_SCHEMA_VERSION,
            "report_posture": ANALYST_REPORT_POSTURE,
            "proposal_only": True,
            "run_id": run_id,
            "request_id": request_id,
            "findings": list(findings),
            "finding_count": len(findings),
            "per_component_relevance_proposals": _per_component_proposals(findings),
            "contradictions": _subset_findings(
                findings,
                {"possible_contradiction"},
            ),
            "caveats": _subset_findings(
                findings,
                {"caveat_proposal", "currentness_concern", "scope_mismatch"},
            ),
            "analysis_gap_proposals": list(gaps),
            "analysis_gap_proposal_count": len(gaps),
            "analyzed_custody_record_count": len(analyzed_refs),
            "unanalyzed_custody_record_count": len(readable_refs - analyzed_refs),
            "unreadable_custody_gap_count": unreadable_gap_count,
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    report_digest = _digest_json(_report_digest_payload(report_base))
    report_id = (
        "analyst-report:"
        f"{_clean_token(request_id, limit=120)}:{report_digest[:16]}"
    )
    return {**report_base, "report_id": report_id, "report_digest": report_digest}


def _finding_from_proposal(
    proposal: Mapping[str, Any],
    *,
    index: int,
    custody_by_reference: Mapping[str, Mapping[str, Any]],
    custody_projection_digest: str,
) -> dict[str, Any]:
    kind = _required_token(
        proposal.get("proposal_kind") or proposal.get("finding_kind"),
        "finding proposal requires proposal_kind",
        limit=120,
    )
    if kind not in FINDING_PROPOSAL_KINDS:
        raise EvidenceRelativeAnalysisPacketError(
            f"unsupported finding proposal kind: {kind}"
        )
    record = _bound_custody_record(proposal, custody_by_reference)
    if record.get("fetch_read_status") != READABLE_STATUS and kind in {
        "apparent_relevance",
        "possible_support_proposal",
        "possible_contradiction",
        "caveat_proposal",
        "currentness_concern",
        "scope_mismatch",
    }:
        raise EvidenceRelativeAnalysisPacketError(
            f"{kind} requires readable custody"
        )
    finding_base = _without_empty(
        {
            "finding_posture": ANALYST_REPORT_POSTURE,
            "proposal_kind": kind,
            "candidate_id": record.get("candidate_id"),
            "candidate_digest": record.get("candidate_digest"),
            "reference_id": record.get("reference_id"),
            "reference_digest": record.get("reference_digest"),
            "fetch_read_content_packet_id": record.get("fetch_read_content_packet_id"),
            "fetch_read_content_packet_digest": record.get(
                "fetch_read_content_packet_digest"
            ),
            "search_result_candidate_packet_id": record.get(
                "search_result_candidate_packet_id"
            ),
            "search_result_candidate_packet_digest": record.get(
                "search_result_candidate_packet_digest"
            ),
            "search_result_candidate_record_digest": record.get(
                "search_result_candidate_record_digest"
            ),
            "evidence_ledger_custody_projection_ref": {
                "trace_key": FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY,
                "projection_digest": custody_projection_digest,
            },
            "component_id": _clean_token(
                proposal.get("component_id") or record.get("component_id"),
                limit=260,
            ),
            "source_obligation_candidate_ids": _text_list(
                proposal.get("source_obligation_candidate_ids")
                or record.get("source_obligation_candidate_ids"),
                limit=260,
            ),
            "candidate_url": record.get("candidate_url"),
            "candidate_domain": record.get("candidate_domain"),
            "candidate_title": record.get("candidate_title"),
            "excerpt_digest": record.get("excerpt_digest"),
            "bounded_character_count": _bounded_int(
                record.get("bounded_character_count")
            ),
            "proposal_summary": _clean_text(
                proposal.get("proposal_summary")
                or proposal.get("summary")
                or proposal.get("reason"),
                limit=500,
            ),
            "reason": _clean_text(proposal.get("reason"), limit=500),
            "contradicts_reference_id": _clean_token(
                proposal.get("contradicts_reference_id"),
                limit=320,
            ),
            "contradicts_finding_id": _clean_token(
                proposal.get("contradicts_finding_id"),
                limit=260,
            ),
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    finding_digest = _digest_json(_finding_digest_payload(finding_base))
    finding_id = (
        "evidence-relative-finding:"
        f"{_clean_token(record.get('reference_id'), limit=120)}:"
        f"{finding_digest[:16]}"
    )
    finding = {
        **finding_base,
        "finding_id": finding_id,
        "finding_digest": finding_digest,
    }
    _validate_finding(finding)
    return finding


def _gap_from_proposal(
    proposal: Mapping[str, Any],
    *,
    index: int,
    custody_by_reference: Mapping[str, Mapping[str, Any]],
    custody_projection_digest: str,
    trigger_finding_id: str | None = None,
) -> dict[str, Any]:
    kind = _clean_token(
        proposal.get("gap_kind") or proposal.get("proposal_kind"),
        limit=120,
    )
    if kind == "analysis_gap":
        kind = _clean_token(proposal.get("gap_kind"), limit=120) or "analysis_gap"
    if kind not in GAP_KINDS:
        raise EvidenceRelativeAnalysisPacketError(
            f"unsupported analysis gap kind: {kind}"
        )
    record = _bound_custody_record(proposal, custody_by_reference)
    return _gap_record(
        kind=kind,
        reason=_clean_text(proposal.get("reason"), limit=500)
        or "offline Analyst proposed an evidence-relative analysis gap",
        information_needed=_clean_text(proposal.get("information_needed"), limit=500),
        proposed_search_direction=_clean_text(
            proposal.get("proposed_search_direction"),
            limit=500,
        ),
        proposed_query_hint=_clean_text(proposal.get("proposed_query_hint"), limit=300),
        trigger_finding_id=trigger_finding_id
        or _clean_token(proposal.get("trigger_finding_id"), limit=260),
        record=record,
        custody_projection_digest=custody_projection_digest,
        index=index,
    )


def _automatic_gap_proposals(
    *,
    custody_records: Sequence[Mapping[str, Any]],
    findings_by_reference: set[Any],
    custody_projection_digest: str,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for index, record in enumerate(custody_records):
        reference_id = record.get("reference_id")
        status = record.get("fetch_read_status")
        if status == READABLE_STATUS and reference_id not in findings_by_reference:
            gaps.append(
                _gap_record(
                    kind="analysis_missing",
                    reason="readable custody record has no supplied Analyst proposal",
                    information_needed="evidence-relative meaning still needs Analyst review",
                    record=record,
                    custody_projection_digest=custody_projection_digest,
                    index=index,
                )
            )
            continue
        if status != READABLE_STATUS:
            gaps.append(
                _gap_record(
                    kind=(
                        "unreadable_source"
                        if status == "unreadable"
                        else "missing_readable_source"
                    ),
                    reason=_clean_text(record.get("failure_reason"), limit=500)
                    or _clean_text(record.get("read_error_code"), limit=120)
                    or "fetch/read custody record is not readable",
                    information_needed="a readable source or replacement source is needed before analysis support",
                    record=record,
                    custody_projection_digest=custody_projection_digest,
                    index=index,
                )
            )
    return gaps


def _gap_record(
    *,
    kind: str,
    reason: str,
    information_needed: str | None,
    record: Mapping[str, Any],
    custody_projection_digest: str,
    index: int,
    proposed_search_direction: str | None = None,
    proposed_query_hint: str | None = None,
    trigger_finding_id: str | None = None,
) -> dict[str, Any]:
    gap_base = _without_empty(
        {
            "gap_kind": kind,
            "trigger_candidate_id": record.get("candidate_id"),
            "trigger_reference_id": record.get("reference_id"),
            "trigger_finding_id": trigger_finding_id,
            "candidate_id": record.get("candidate_id"),
            "reference_id": record.get("reference_id"),
            "reference_digest": record.get("reference_digest"),
            "component_id": record.get("component_id"),
            "source_obligation_candidate_ids": _text_list(
                record.get("source_obligation_candidate_ids"),
                limit=260,
            ),
            "fetch_read_status": record.get("fetch_read_status"),
            "failure_reason": _clean_text(record.get("failure_reason"), limit=500),
            "read_error_code": _clean_token(record.get("read_error_code"), limit=120),
            "reason": reason,
            "information_needed": information_needed,
            "proposed_search_direction": proposed_search_direction,
            "proposed_query_hint": proposed_query_hint,
            "evidence_ledger_custody_projection_ref": {
                "trace_key": FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY,
                "projection_digest": custody_projection_digest,
            },
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    gap_digest = _digest_json(_gap_digest_payload(gap_base))
    gap_id = (
        "evidence-relative-gap:"
        f"{_clean_token(record.get('reference_id'), limit=120) or index}:"
        f"{gap_digest[:16]}"
    )
    gap = {**gap_base, "gap_id": gap_id, "gap_digest": gap_digest}
    _validate_gap(gap)
    return gap


def _per_component_proposals(
    findings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for finding in findings:
        component_id = _clean_token(finding.get("component_id"), limit=260)
        if component_id:
            grouped.setdefault(component_id, []).append(finding)
    entries: list[dict[str, Any]] = []
    for component_id in sorted(grouped):
        component_findings = grouped[component_id]
        entries.append(
            {
                "component_id": component_id,
                "proposal_kinds": _ordered_unique(
                    finding.get("proposal_kind") for finding in component_findings
                ),
                "finding_ids": _ordered_unique(
                    finding.get("finding_id") for finding in component_findings
                ),
                "candidate_ids": _ordered_unique(
                    finding.get("candidate_id") for finding in component_findings
                ),
                "reference_ids": _ordered_unique(
                    finding.get("reference_id") for finding in component_findings
                ),
                "source_obligation_candidate_ids": _ordered_unique(
                    item
                    for finding in component_findings
                    for item in _text_list(
                        finding.get("source_obligation_candidate_ids"),
                        limit=260,
                    )
                ),
                **_CLOSED_FALSE_FLAGS,
                **_PER_COMPONENT_FALSE_FLAGS,
                "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            }
        )
    return entries


def _subset_findings(
    findings: Sequence[Mapping[str, Any]],
    kinds: set[str],
) -> list[dict[str, Any]]:
    return [
        {
            "finding_id": finding.get("finding_id"),
            "finding_digest": finding.get("finding_digest"),
            "proposal_kind": finding.get("proposal_kind"),
            "candidate_id": finding.get("candidate_id"),
            "reference_id": finding.get("reference_id"),
            "component_id": finding.get("component_id"),
            "reason": finding.get("reason"),
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
        for finding in findings
        if finding.get("proposal_kind") in kinds
    ]


def _custody_projection_from_ledger(ledger_projection: Mapping[str, Any]) -> dict[str, Any]:
    projection = _safe_mapping(ledger_projection.get("fetch_read_candidate_custody"))
    if not projection:
        raise EvidenceRelativeAnalysisPacketError(
            "EvidenceLedger projection requires fetch_read_candidate_custody"
        )
    if projection.get("trace_key") not in (
        None,
        "",
        FETCH_READ_CANDIDATE_CUSTODY_TRACE_KEY,
    ):
        raise EvidenceRelativeAnalysisPacketError(
            "fetch/read candidate custody trace_key mismatch"
        )
    return projection


def _custody_records(custody_projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = [
        _safe_mapping(record)
        for record in _safe_list(
            custody_projection.get("fetch_read_candidate_custody_records")
        )
    ]
    records = [record for record in records if record]
    declared_count = custody_projection.get("custody_record_count")
    if declared_count is not None and _bounded_int(declared_count) != len(records):
        raise EvidenceRelativeAnalysisPacketError(
            "fetch/read custody record count mismatch"
        )
    declared_readable = custody_projection.get("readable_record_count")
    if declared_readable is not None and _bounded_int(declared_readable) != sum(
        1 for record in records if record.get("fetch_read_status") == READABLE_STATUS
    ):
        raise EvidenceRelativeAnalysisPacketError(
            "fetch/read readable custody count mismatch"
        )
    for record in records:
        _reject_forbidden_surface_claims(record, context="fetch/read custody record")
        missing = [key for key in _REQUIRED_CUSTODY_KEYS if not record.get(key)]
        if missing:
            raise EvidenceRelativeAnalysisPacketError(
                "fetch/read custody record missing keys: " + ", ".join(missing)
            )
    return records


def _custody_index(
    custody_records: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for record in custody_records:
        reference_id = _clean_token(record.get("reference_id"), limit=320)
        if not reference_id:
            continue
        if reference_id in out:
            raise EvidenceRelativeAnalysisPacketError(
                f"duplicate custody reference_id: {reference_id}"
            )
        out[reference_id] = record
    return out


def _bound_custody_record(
    proposal: Mapping[str, Any],
    custody_by_reference: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    reference_id = _required_token(
        proposal.get("reference_id") or proposal.get("trigger_reference_id"),
        "analyst proposal requires reference_id",
        limit=320,
    )
    record = custody_by_reference.get(reference_id)
    if record is None:
        raise EvidenceRelativeAnalysisPacketError(
            f"analyst proposal references unknown custody reference: {reference_id}"
        )
    bindings = (
        ("candidate_id", 320),
        ("candidate_digest", 128),
        ("reference_digest", 128),
        ("fetch_read_content_packet_id", 320),
        ("fetch_read_content_packet_digest", 128),
        ("search_result_candidate_packet_id", 320),
        ("search_result_candidate_packet_digest", 128),
    )
    for key, limit in bindings:
        claimed = _clean_token(proposal.get(key), limit=limit)
        if claimed and claimed != _clean_token(record.get(key), limit=limit):
            raise EvidenceRelativeAnalysisPacketError(
                f"analyst proposal {key} does not match custody record"
            )
    return record


def _proposal_records_or_error(
    analyst_proposal_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    proposals = _safe_list(analyst_proposal_records)
    out: list[dict[str, Any]] = []
    for proposal in proposals:
        if not isinstance(proposal, Mapping):
            raise EvidenceRelativeAnalysisPacketError(
                "analyst proposal records must be mappings"
            )
        _reject_forbidden_surface_claims(proposal, context="analyst proposal record")
        out.append(_safe_mapping(proposal))
    return out


def _run_request_identity(
    *,
    records: Sequence[Mapping[str, Any]],
    run_id: str | None,
    request_id: str | None,
) -> tuple[str, str]:
    record_run_ids = _ordered_unique(record.get("run_id") for record in records)
    record_request_ids = _ordered_unique(record.get("request_id") for record in records)
    clean_run_id = _clean_token(run_id, limit=160) or (
        record_run_ids[0] if len(record_run_ids) == 1 else None
    )
    clean_request_id = _clean_token(request_id, limit=160) or (
        record_request_ids[0] if len(record_request_ids) == 1 else None
    )
    if not clean_run_id or not clean_request_id:
        raise EvidenceRelativeAnalysisPacketError(
            "analysis packet requires run_id and request_id"
        )
    if run_id and record_run_ids and any(item != clean_run_id for item in record_run_ids):
        raise EvidenceRelativeAnalysisPacketError("run_id does not match custody records")
    if request_id and record_request_ids and any(
        item != clean_request_id for item in record_request_ids
    ):
        raise EvidenceRelativeAnalysisPacketError(
            "request_id does not match custody records"
        )
    return clean_run_id, clean_request_id


def _contract_binding(
    *,
    records: Sequence[Mapping[str, Any]],
    current_answer_contract_ref: Mapping[str, Any] | None,
    current_answer_contract_digest: str | None,
) -> tuple[dict[str, Any], str | None]:
    record_digests = _ordered_unique(
        record.get("current_answer_contract_digest") for record in records
    )
    digest = _clean_token(current_answer_contract_digest, limit=128) or (
        record_digests[0] if len(record_digests) == 1 else None
    )
    if current_answer_contract_digest and record_digests and any(
        item != digest for item in record_digests
    ):
        raise EvidenceRelativeAnalysisPacketError(
            "current_answer_contract_digest does not match custody records"
        )
    record_ref = {}
    for record in records:
        ref = _safe_mapping(record.get("current_answer_contract_ref"))
        if ref:
            record_ref = ref
            break
    supplied_ref = _safe_mapping(current_answer_contract_ref)
    contract_ref = supplied_ref or record_ref
    if supplied_ref and record_ref and supplied_ref != record_ref:
        raise EvidenceRelativeAnalysisPacketError(
            "current_answer_contract_ref does not match custody records"
        )
    return contract_ref, digest


def _validate_report(report: Mapping[str, Any]) -> None:
    if report.get("schema_version") != ANALYST_REPORT_SCHEMA_VERSION:
        raise EvidenceRelativeAnalysisPacketError("analyst report schema mismatch")
    if report.get("report_posture") != ANALYST_REPORT_POSTURE:
        raise EvidenceRelativeAnalysisPacketError("analyst report posture mismatch")
    _validate_closed_flags(report, context="analyst report")
    findings = _safe_list(report.get("findings"))
    gaps = _safe_list(report.get("analysis_gap_proposals"))
    if _bounded_int(report.get("finding_count")) != len(findings):
        raise EvidenceRelativeAnalysisPacketError("analyst report finding count mismatch")
    if _bounded_int(report.get("analysis_gap_proposal_count")) != len(gaps):
        raise EvidenceRelativeAnalysisPacketError(
            "analyst report analysis gap count mismatch"
        )
    for finding in findings:
        _validate_finding(_required_mapping(finding, "analyst finding"))
    for gap in gaps:
        _validate_gap(_required_mapping(gap, "analysis gap proposal"))
    for entry in _safe_list(report.get("per_component_relevance_proposals")):
        _validate_per_component_entry(
            _required_mapping(entry, "per-component relevance proposal")
        )


def _validate_finding(finding: Mapping[str, Any]) -> None:
    _reject_raw_private_only(finding, context="analyst finding")
    kind = _clean_token(finding.get("proposal_kind"), limit=120)
    if kind not in FINDING_PROPOSAL_KINDS:
        raise EvidenceRelativeAnalysisPacketError("analyst finding kind mismatch")
    for key in (
        "candidate_id",
        "reference_id",
        "reference_digest",
        "finding_id",
        "finding_digest",
    ):
        if not _clean_token(finding.get(key), limit=320):
            raise EvidenceRelativeAnalysisPacketError(
                f"analyst finding requires {key}"
            )
    _validate_closed_flags(finding, context="analyst finding")
    if finding.get("finding_digest") != _digest_json(_finding_digest_payload(finding)):
        raise EvidenceRelativeAnalysisPacketError("analyst finding digest mismatch")


def _validate_gap(gap: Mapping[str, Any]) -> None:
    _reject_raw_private_only(gap, context="analysis gap proposal")
    kind = _clean_token(gap.get("gap_kind"), limit=120)
    if kind not in GAP_KINDS:
        raise EvidenceRelativeAnalysisPacketError("analysis gap kind mismatch")
    for key in ("gap_id", "gap_digest", "trigger_reference_id", "reference_digest"):
        if not _clean_token(gap.get(key), limit=320):
            raise EvidenceRelativeAnalysisPacketError(f"analysis gap requires {key}")
    _validate_closed_flags(gap, context="analysis gap proposal")
    if gap.get("gap_digest") != _digest_json(_gap_digest_payload(gap)):
        raise EvidenceRelativeAnalysisPacketError("analysis gap digest mismatch")


def _validate_per_component_entry(entry: Mapping[str, Any]) -> None:
    for key, expected in _PER_COMPONENT_FALSE_FLAGS.items():
        if entry.get(key) is not expected:
            raise EvidenceRelativeAnalysisPacketError(
                f"per-component relevance proposal must keep {key} false"
            )
    _validate_closed_flags(entry, context="per-component relevance proposal")


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise EvidenceRelativeAnalysisPacketError(f"{context} must keep {key} false")
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if flags.get(key) is not expected:
            raise EvidenceRelativeAnalysisPacketError(
                f"{context} closed_surface_flags must keep {key} false"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise EvidenceRelativeAnalysisPacketError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    _reject_raw_private_only(value, context=context)
    keys = _collect_keys(value)
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise EvidenceRelativeAnalysisPacketError(
            f"{context} includes closed authority fields: " + ", ".join(authority)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise EvidenceRelativeAnalysisPacketError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _reject_raw_private_only(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise EvidenceRelativeAnalysisPacketError(
            f"{context} contains raw/private fields: " + ", ".join(raw_or_private)
        )


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


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


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None and hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise EvidenceRelativeAnalysisPacketError(f"{label} must be a mapping")
    return _safe_mapping(value)


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 7:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=900)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_key_token(key, limit=120)
            if not clean_key:
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise EvidenceRelativeAnalysisPacketError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _clean_key_token(value: Any, *, limit: int = 120) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_token(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_token(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _ordered_unique(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, bytes):
        items = []
    else:
        try:
            items = list(value)
        except TypeError:
            items = []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_token(item, limit=320)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _dedupe_by_id(
    records: Sequence[Mapping[str, Any]],
    *,
    key: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        record_key = _clean_token(record.get(key), limit=320)
        if record_key and record_key in seen:
            continue
        if record_key:
            seen.add(record_key)
        out.append(dict(record))
    return out


def _finding_digest_payload(finding: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(finding)
    payload.pop("finding_id", None)
    payload.pop("finding_digest", None)
    return payload


def _gap_digest_payload(gap: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(gap)
    payload.pop("gap_id", None)
    payload.pop("gap_digest", None)
    return payload


def _report_digest_payload(report: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(report)
    payload.pop("report_id", None)
    payload.pop("report_digest", None)
    return payload


def _packet_digest_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(packet)
    payload.pop("packet_id", None)
    payload.pop("packet_digest", None)
    return payload


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ANALYST_REPORT_POSTURE",
    "ANALYST_REPORT_SCHEMA_VERSION",
    "EVIDENCE_RELATIVE_ANALYSIS_PACKET_KIND",
    "EVIDENCE_RELATIVE_ANALYSIS_PACKET_OWNER",
    "EVIDENCE_RELATIVE_ANALYSIS_PACKET_SCHEMA_VERSION",
    "EVIDENCE_RELATIVE_ANALYSIS_PACKET_TRACE_KEY",
    "EvidenceRelativeAnalysisPacket",
    "EvidenceRelativeAnalysisPacketError",
    "build_evidence_relative_analysis_packet",
    "evidence_relative_analysis_packet_ref_from_packet",
    "validate_evidence_relative_analysis_packet",
]
