"""Proposal-only follow-up search intent packet for Analyst gaps.

This module consumes a validated ``EvidenceRelativeAnalysisPacket`` and its
``analyst_report.analysis_gap_proposals``.  It creates bounded, reviewable
follow-up search intent proposals only; it does not authorize search, build query
plans, create SearchExecutorHandoff state, dispatch providers, fetch/read,
retrieve, admit evidence, mutate contracts, decide sufficiency, create
FinalAnswerPacket state, or create Author input.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.evidence_relative_analysis_packet import (
    EvidenceRelativeAnalysisPacketError,
    validate_evidence_relative_analysis_packet,
)

FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION = (
    "followup_search_intent_packet_ag_analysis_gap_followup_search_01_v1"
)
ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION = (
    "analysis_gap_search_proposal_ag_analysis_gap_followup_search_01_v1"
)
FOLLOWUP_SEARCH_INTENT_PACKET_KIND = "followup_search_intent_packet"
FOLLOWUP_SEARCH_INTENT_PACKET_TRACE_KEY = "followup_search_intent_packet"
FOLLOWUP_SEARCH_INTENT_PACKET_OWNER = "RunKernel.FollowupSearchIntentPacket"
ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE = "proposal_only_followup_search_intent"
NON_SEARCHABLE_REVIEW_GAP = "non_searchable_review_gap"

GAP_KIND_TO_FOLLOWUP_INTENT = {
    "missing_readable_source": "replacement_readable_source_search",
    "unreadable_source": "replacement_readable_source_search",
    "missing_fact": "targeted_fact_search",
    "currentness_concern": "official_current_or_currentness_verification_search",
    "scope_mismatch": "scoped_disambiguation_search",
    "possible_contradiction": "reconciliation_or_source_comparison_search",
    "analysis_gap": "targeted_analysis_gap_search",
}

_CLOSED_FALSE_FLAGS = {
    "authorized": False,
    "query_plan_created": False,
    "search_executor_handoff_created": False,
    "search_dispatched": False,
    "provider_called": False,
    "broker_called": False,
    "model_called": False,
    "retrieval_executed": False,
    "fetch_read_executed": False,
    "search_result_candidate_packet_created": False,
    "fetch_read_content_packet_created": False,
    "evidence_ledger_admitted": False,
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
    "contract_mutated": False,
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
        "current_answer_contract",
        "evidence",
        "evidence_sources",
        "fap",
        "final_answer",
        "final_answer_packet",
        "final_claim",
        "query_plan",
        "query_task",
        "query_tasks",
        "search_executor_handoff",
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
        "admitted_to_evidence_ledger",
        "answer_ready",
        "author_input_ready",
        "authorization_ready",
        "authorized_for_search",
        "broker_invoked",
        "candidate_discovered",
        "citation_rendered",
        "component_satisfied",
        "content_citation_eligible",
        "coverage_decision",
        "evidence_admitted",
        "evidence_created",
        "evidence_ledger_custody_created",
        "fetch_read_content_packet_built",
        "final_answer_ready",
        "final_evidence_eligible",
        "live_provider_called",
        "live_search_executed",
        "provider_calls_executed",
        "query_plan_activated",
        "readiness_decided",
        "search_executed",
        "search_result_candidate_packet_built",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)


class FollowupSearchIntentPacketError(ValueError):
    """Raised when a follow-up search intent packet opens a closed surface."""


@dataclass(frozen=True, slots=True)
class FollowupSearchIntentPacket:
    """Standalone proposal packet from Analyst gaps to search-intent review."""

    evidence_relative_analysis_packet: Mapping[str, Any]
    current_answer_contract_ref: Mapping[str, Any] | None = None
    current_answer_contract_digest: str | None = None
    mode_budget_hints: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return build_followup_search_intent_packet(
            evidence_relative_analysis_packet=self.evidence_relative_analysis_packet,
            current_answer_contract_ref=self.current_answer_contract_ref,
            current_answer_contract_digest=self.current_answer_contract_digest,
            mode_budget_hints=self.mode_budget_hints,
        )


def build_followup_search_intent_packet(
    *,
    evidence_relative_analysis_packet: Mapping[str, Any],
    current_answer_contract_ref: Mapping[str, Any] | None = None,
    current_answer_contract_digest: str | None = None,
    mode_budget_hints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a proposal-only packet from validated Analyst gap proposals."""

    try:
        analysis_packet = validate_evidence_relative_analysis_packet(
            evidence_relative_analysis_packet
        )
    except EvidenceRelativeAnalysisPacketError as exc:
        raise FollowupSearchIntentPacketError(
            f"evidence-relative analysis packet validation failed: {exc}"
        ) from exc

    _reject_forbidden_surface_claims(
        mode_budget_hints or {},
        context="mode/budget hints",
    )
    hints = _safe_mapping(mode_budget_hints)
    contract_ref, contract_digest = _contract_binding(
        analysis_packet=analysis_packet,
        current_answer_contract_ref=current_answer_contract_ref,
        current_answer_contract_digest=current_answer_contract_digest,
    )
    report = _required_mapping(analysis_packet.get("analyst_report"), "analyst report")
    analysis_ref = _analysis_packet_ref(analysis_packet)
    report_ref = _analyst_report_ref(report)
    findings = _finding_index(report)
    proposals = [
        _proposal_from_gap(
            gap,
            index=index,
            analysis_packet=analysis_packet,
            analysis_ref=analysis_ref,
            report_ref=report_ref,
            findings=findings,
            current_answer_contract_ref=contract_ref,
            current_answer_contract_digest=contract_digest,
            mode_budget_hints=hints,
        )
        for index, gap in enumerate(
            _safe_list(report.get("analysis_gap_proposals"))
        )
    ]
    search_count = sum(
        1
        for proposal in proposals
        if proposal.get("followup_intent_kind") != NON_SEARCHABLE_REVIEW_GAP
    )
    ready_count = sum(
        1
        for proposal in proposals
        if proposal.get("ready_for_authorization_review") is True
    )
    packet_base = _without_empty(
        {
            "schema_version": FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION,
            "packet_kind": FOLLOWUP_SEARCH_INTENT_PACKET_KIND,
            "trace_key": FOLLOWUP_SEARCH_INTENT_PACKET_TRACE_KEY,
            "owner": FOLLOWUP_SEARCH_INTENT_PACKET_OWNER,
            "proposal_only": True,
            "canonical_state": False,
            "reduced_state": False,
            "run_id": _clean_token(analysis_packet.get("run_id"), limit=160),
            "request_id": _clean_token(analysis_packet.get("request_id"), limit=160),
            "current_answer_contract_ref": contract_ref,
            "current_answer_contract_digest": contract_digest,
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "analyst_report_ref": report_ref,
            "analyst_report_id": report_ref.get("report_id"),
            "analyst_report_digest": report_ref.get("report_digest"),
            "analysis_gap_search_proposals": proposals,
            "proposal_count": len(proposals),
            "analysis_gap_proposal_count": len(proposals),
            "followup_search_intent_proposal_count": search_count,
            "review_ready_proposal_count": ready_count,
            "non_searchable_review_gap_count": len(proposals) - search_count,
            "inert_mode_budget_hints": hints,
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    packet_digest = _digest_json(_packet_digest_payload(packet_base))
    packet_id = (
        "followup-search-intent-packet:"
        f"{_clean_token(packet_base.get('request_id'), limit=120)}:"
        f"{packet_digest[:16]}"
    )
    packet = {
        **packet_base,
        "packet_id": packet_id,
        "packet_digest": packet_digest,
    }
    return validate_followup_search_intent_packet(packet)


def validate_followup_search_intent_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a packet and return a sanitized copy."""

    safe = _required_mapping(packet, "follow-up search intent packet")
    _reject_raw_private_only(safe, context="follow-up search intent packet")
    if safe.get("schema_version") != FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION:
        raise FollowupSearchIntentPacketError("follow-up packet schema mismatch")
    if safe.get("packet_kind") != FOLLOWUP_SEARCH_INTENT_PACKET_KIND:
        raise FollowupSearchIntentPacketError("follow-up packet kind mismatch")
    if safe.get("owner") != FOLLOWUP_SEARCH_INTENT_PACKET_OWNER:
        raise FollowupSearchIntentPacketError("follow-up packet owner mismatch")
    if safe.get("proposal_only") is not True:
        raise FollowupSearchIntentPacketError("follow-up packet must be proposal-only")
    if safe.get("canonical_state") is not False or safe.get("reduced_state") is not False:
        raise FollowupSearchIntentPacketError(
            "follow-up packet must remain standalone proposal state"
        )
    _validate_closed_flags(safe, context="follow-up packet")
    proposals = [
        _required_mapping(item, "analysis gap search proposal")
        for item in _safe_list(safe.get("analysis_gap_search_proposals"))
    ]
    if _bounded_int(safe.get("proposal_count")) != len(proposals):
        raise FollowupSearchIntentPacketError("follow-up proposal count mismatch")
    if _bounded_int(safe.get("analysis_gap_proposal_count")) != len(proposals):
        raise FollowupSearchIntentPacketError("analysis gap proposal count mismatch")
    search_count = sum(
        1
        for proposal in proposals
        if proposal.get("followup_intent_kind") != NON_SEARCHABLE_REVIEW_GAP
    )
    ready_count = sum(
        1
        for proposal in proposals
        if proposal.get("ready_for_authorization_review") is True
    )
    if _bounded_int(safe.get("followup_search_intent_proposal_count")) != search_count:
        raise FollowupSearchIntentPacketError("search intent proposal count mismatch")
    if _bounded_int(safe.get("review_ready_proposal_count")) != ready_count:
        raise FollowupSearchIntentPacketError("review-ready proposal count mismatch")
    if _bounded_int(safe.get("non_searchable_review_gap_count")) != (
        len(proposals) - search_count
    ):
        raise FollowupSearchIntentPacketError("non-searchable gap count mismatch")
    for proposal in proposals:
        _validate_proposal(proposal)
    declared_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if declared_digest != _digest_json(_packet_digest_payload(safe)):
        raise FollowupSearchIntentPacketError("follow-up packet digest mismatch")
    expected_id = (
        "followup-search-intent-packet:"
        f"{_clean_token(safe.get('request_id'), limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_id:
        raise FollowupSearchIntentPacketError("follow-up packet id mismatch")
    return safe


def followup_search_intent_packet_ref_from_packet(
    packet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact downstream reference for review-only routing."""

    safe = _safe_mapping(packet)
    packet_id = _clean_token(safe.get("packet_id"), limit=260)
    packet_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if not packet_id or not packet_digest:
        return {}
    return _without_empty(
        {
            "packet_id": packet_id,
            "packet_digest": packet_digest,
            "schema_version": _clean_token(safe.get("schema_version"), limit=160),
            "proposal_count": _bounded_int(safe.get("proposal_count")),
            "review_ready_proposal_count": _bounded_int(
                safe.get("review_ready_proposal_count")
            ),
            "authorized": False,
            "search_dispatched": False,
        }
    )


def _proposal_from_gap(
    gap: Any,
    *,
    index: int,
    analysis_packet: Mapping[str, Any],
    analysis_ref: Mapping[str, Any],
    report_ref: Mapping[str, Any],
    findings: Mapping[str, Mapping[str, Any]],
    current_answer_contract_ref: Mapping[str, Any],
    current_answer_contract_digest: str | None,
    mode_budget_hints: Mapping[str, Any],
) -> dict[str, Any]:
    gap_record = _required_mapping(gap, "analysis gap proposal")
    _reject_forbidden_surface_claims(
        gap_record,
        context="analysis gap proposal",
    )
    source_gap_kind = _required_token(
        gap_record.get("gap_kind") or gap_record.get("source_gap_kind"),
        "analysis gap proposal requires gap_kind",
        limit=120,
    )
    followup_intent_kind = _followup_intent_kind(gap_record)
    finding = _matching_finding(gap_record, findings)
    custody_ref = _custody_ref(gap_record, analysis_packet)
    fetch_read_packet_id = _lineage_token(
        "fetch_read_content_packet_id",
        gap_record,
        finding,
        limit=320,
    )
    fetch_read_packet_digest = _lineage_token(
        "fetch_read_content_packet_digest",
        gap_record,
        finding,
        limit=128,
    )
    search_candidate_packet_id = _lineage_token(
        "search_result_candidate_packet_id",
        gap_record,
        finding,
        limit=320,
    )
    search_candidate_packet_digest = _lineage_token(
        "search_result_candidate_packet_digest",
        gap_record,
        finding,
        limit=128,
    )
    trigger_reference_digest = _lineage_token(
        "trigger_reference_digest",
        gap_record,
        finding,
        fallback_keys=("reference_digest",),
        limit=128,
    )
    trigger_candidate_id = _lineage_token(
        "trigger_candidate_id",
        gap_record,
        finding,
        fallback_keys=("candidate_id",),
        limit=320,
    )
    trigger_reference_id = _lineage_token(
        "trigger_reference_id",
        gap_record,
        finding,
        fallback_keys=("reference_id",),
        limit=320,
    )
    proposal_base = _without_empty(
        {
            "schema_version": ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION,
            "proposal_posture": ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE,
            "proposal_only": True,
            "source_gap_id": _clean_token(gap_record.get("gap_id"), limit=320),
            "source_gap_digest": _clean_token(
                gap_record.get("gap_digest"),
                limit=128,
            ),
            "source_gap_kind": source_gap_kind,
            "followup_intent_kind": followup_intent_kind,
            "search_intent_proposed": followup_intent_kind
            != NON_SEARCHABLE_REVIEW_GAP,
            "non_searchable_review_gap": followup_intent_kind
            == NON_SEARCHABLE_REVIEW_GAP,
            "trigger_candidate_id": trigger_candidate_id,
            "trigger_candidate_digest": _lineage_token(
                "trigger_candidate_digest",
                gap_record,
                finding,
                fallback_keys=("candidate_digest",),
                limit=128,
            ),
            "trigger_reference_id": trigger_reference_id,
            "trigger_reference_digest": trigger_reference_digest,
            "trigger_finding_id": _clean_token(
                gap_record.get("trigger_finding_id")
                or finding.get("finding_id"),
                limit=320,
            ),
            "candidate_id": trigger_candidate_id,
            "candidate_digest": _lineage_token(
                "candidate_digest",
                gap_record,
                finding,
                fallback_keys=("trigger_candidate_digest",),
                limit=128,
            ),
            "reference_id": trigger_reference_id,
            "reference_digest": trigger_reference_digest,
            "evidence_relative_analysis_packet_ref": _safe_mapping(analysis_ref),
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "analyst_report_ref": _safe_mapping(report_ref),
            "analyst_report_id": report_ref.get("report_id"),
            "analyst_report_digest": report_ref.get("report_digest"),
            "evidence_ledger_custody_projection_ref": custody_ref,
            "evidence_ledger_custody_projection_digest": _clean_token(
                custody_ref.get("projection_digest"),
                limit=128,
            ),
            "fetch_read_content_packet_ref": _packet_ref(
                fetch_read_packet_id,
                fetch_read_packet_digest,
            ),
            "fetch_read_content_packet_id": fetch_read_packet_id,
            "fetch_read_content_packet_digest": fetch_read_packet_digest,
            "search_result_candidate_packet_ref": _packet_ref(
                search_candidate_packet_id,
                search_candidate_packet_digest,
            ),
            "search_result_candidate_packet_id": search_candidate_packet_id,
            "search_result_candidate_packet_digest": search_candidate_packet_digest,
            "search_result_candidate_record_digest": _lineage_token(
                "search_result_candidate_record_digest",
                gap_record,
                finding,
                limit=128,
            ),
            "component_id": _lineage_token(
                "component_id",
                gap_record,
                finding,
                limit=260,
            ),
            "source_obligation_candidate_ids": _ordered_unique(
                [
                    *_text_list(gap_record.get("source_obligation_candidate_ids")),
                    *_text_list(finding.get("source_obligation_candidate_ids")),
                ]
            ),
            "source_obligation_candidate_ids_are_lineage_only": True,
            "information_needed": _clean_text(
                gap_record.get("information_needed")
                or gap_record.get("reason"),
                limit=600,
            ),
            "search_direction": _search_direction(
                gap_record,
                followup_intent_kind=followup_intent_kind,
            ),
            "proposed_query_hint": _clean_text(
                gap_record.get("proposed_query_hint")
                or gap_record.get("query_hint"),
                limit=360,
            ),
            "required_source_class_hint": _hint_or_default(
                gap_record,
                "required_source_class_hint",
                "required_source_class",
                default=_default_source_class_hint(source_gap_kind),
            ),
            "required_source_tier_hint": _hint_or_default(
                gap_record,
                "required_source_tier_hint",
                "required_source_tier",
                default=_default_source_tier_hint(source_gap_kind),
            ),
            "required_currentness_hint": _hint_or_default(
                gap_record,
                "required_currentness_hint",
                "required_currentness",
                default=_default_currentness_hint(source_gap_kind),
            ),
            "priority_hint": _hint_or_default(
                gap_record,
                "priority_hint",
                "priority",
                default=_default_priority_hint(source_gap_kind),
            ),
            "budget_hint": _budget_hint(gap_record, mode_budget_hints),
            "current_answer_contract_ref": _safe_mapping(current_answer_contract_ref),
            "current_answer_contract_digest": current_answer_contract_digest,
            **_CLOSED_FALSE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        }
    )
    review_blockers = _authorization_review_blockers(proposal_base)
    proposal_base = _without_empty(
        {
            **proposal_base,
            "ready_for_authorization_review": not review_blockers,
            "authorization_review_blockers": review_blockers,
        }
    )
    proposal_digest = _digest_json(_proposal_digest_payload(proposal_base))
    source_gap_id = _clean_token(proposal_base.get("source_gap_id"), limit=120)
    proposal_id = (
        "analysis-gap-search-proposal:"
        f"{source_gap_id or index}:{proposal_digest[:16]}"
    )
    proposal = {
        **proposal_base,
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
    }
    _validate_proposal(proposal)
    return proposal


def _validate_proposal(proposal: Mapping[str, Any]) -> None:
    _reject_raw_private_only(proposal, context="analysis gap search proposal")
    if proposal.get("schema_version") != ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION:
        raise FollowupSearchIntentPacketError("proposal schema mismatch")
    if proposal.get("proposal_posture") != ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE:
        raise FollowupSearchIntentPacketError("proposal posture mismatch")
    _validate_closed_flags(proposal, context="analysis gap search proposal")
    source_kind = _clean_token(proposal.get("source_gap_kind"), limit=120)
    if source_kind not in {*GAP_KIND_TO_FOLLOWUP_INTENT, "analysis_missing"}:
        raise FollowupSearchIntentPacketError("proposal source gap kind mismatch")
    for key in (
        "source_gap_id",
        "source_gap_digest",
        "trigger_reference_id",
        "trigger_reference_digest",
        "evidence_relative_analysis_packet_id",
        "evidence_relative_analysis_packet_digest",
        "analyst_report_id",
        "analyst_report_digest",
    ):
        if not _clean_token(proposal.get(key), limit=320):
            raise FollowupSearchIntentPacketError(f"proposal requires {key}")
    expected_ready = not _authorization_review_blockers(proposal)
    expected_blockers = _authorization_review_blockers(proposal)
    if _text_list(proposal.get("authorization_review_blockers"), limit=320) != (
        expected_blockers
    ):
        raise FollowupSearchIntentPacketError(
            "proposal authorization-review blockers mismatch"
        )
    if proposal.get("ready_for_authorization_review") is not expected_ready:
        raise FollowupSearchIntentPacketError(
            "proposal review-readiness binding mismatch"
        )
    declared_digest = _clean_token(proposal.get("proposal_digest"), limit=128)
    if declared_digest != _digest_json(_proposal_digest_payload(proposal)):
        raise FollowupSearchIntentPacketError("proposal digest mismatch")
    expected_id = (
        "analysis-gap-search-proposal:"
        f"{_clean_token(proposal.get('source_gap_id'), limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if proposal.get("proposal_id") != expected_id:
        raise FollowupSearchIntentPacketError("proposal id mismatch")


def _followup_intent_kind(gap: Mapping[str, Any]) -> str:
    kind = _clean_token(gap.get("gap_kind") or gap.get("source_gap_kind"), limit=120)
    if kind == "analysis_missing":
        if _clean_text(
            gap.get("proposed_search_direction")
            or gap.get("search_direction")
            or gap.get("proposed_query_hint")
            or gap.get("query_hint"),
            limit=600,
        ):
            return "targeted_analysis_gap_search"
        return NON_SEARCHABLE_REVIEW_GAP
    if kind in GAP_KIND_TO_FOLLOWUP_INTENT:
        return GAP_KIND_TO_FOLLOWUP_INTENT[kind]
    raise FollowupSearchIntentPacketError(f"unsupported analysis gap kind: {kind}")


def _search_direction(
    gap: Mapping[str, Any],
    *,
    followup_intent_kind: str,
) -> str | None:
    explicit = _clean_text(
        gap.get("proposed_search_direction") or gap.get("search_direction"),
        limit=600,
    )
    if explicit:
        return explicit
    if followup_intent_kind == NON_SEARCHABLE_REVIEW_GAP:
        return None
    return followup_intent_kind.replace("_", " ")


def _authorization_review_blockers(proposal: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    required = {
        "source_gap_id": proposal.get("source_gap_id"),
        "source_gap_digest": proposal.get("source_gap_digest"),
        "source_gap_kind": proposal.get("source_gap_kind"),
        "followup_intent_kind": proposal.get("followup_intent_kind"),
        "trigger_reference_id": proposal.get("trigger_reference_id"),
        "trigger_reference_digest": proposal.get("trigger_reference_digest"),
        "evidence_relative_analysis_packet_id": proposal.get(
            "evidence_relative_analysis_packet_id"
        ),
        "evidence_relative_analysis_packet_digest": proposal.get(
            "evidence_relative_analysis_packet_digest"
        ),
        "analyst_report_id": proposal.get("analyst_report_id"),
        "analyst_report_digest": proposal.get("analyst_report_digest"),
        "current_answer_contract_ref": proposal.get("current_answer_contract_ref"),
        "current_answer_contract_digest": proposal.get(
            "current_answer_contract_digest"
        ),
    }
    for key, value in required.items():
        if value in (None, "", {}, []):
            blockers.append(f"missing_{key}")
    if proposal.get("followup_intent_kind") == NON_SEARCHABLE_REVIEW_GAP:
        blockers.append("gap_does_not_propose_search_intent")
    return blockers


def _contract_binding(
    *,
    analysis_packet: Mapping[str, Any],
    current_answer_contract_ref: Mapping[str, Any] | None,
    current_answer_contract_digest: str | None,
) -> tuple[dict[str, Any], str | None]:
    packet_ref = _contract_ref_or_empty(analysis_packet.get("current_answer_contract_ref"))
    supplied_ref = _contract_ref_or_empty(current_answer_contract_ref)
    packet_digest = _clean_token(
        analysis_packet.get("current_answer_contract_digest"),
        limit=128,
    )
    supplied_digest = _clean_token(current_answer_contract_digest, limit=128)
    supplied_ref_digest = _contract_digest_from_ref(supplied_ref)
    packet_ref_digest = _contract_digest_from_ref(packet_ref)
    if supplied_ref and packet_ref and supplied_ref != packet_ref:
        raise FollowupSearchIntentPacketError(
            "current_answer_contract_ref does not match analysis packet"
        )
    digest_values = {
        item
        for item in (
            packet_digest,
            supplied_digest,
            supplied_ref_digest,
            packet_ref_digest,
        )
        if item
    }
    if len(digest_values) > 1:
        raise FollowupSearchIntentPacketError(
            "current_answer_contract_digest does not match analysis packet"
        )
    digest = supplied_digest or supplied_ref_digest or packet_ref_digest or packet_digest
    return supplied_ref or packet_ref, digest


def _contract_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    digest = _clean_token(
        ref.get("contract_digest")
        or ref.get("current_contract_digest")
        or ref.get("accepted_contract_digest"),
        limit=128,
    )
    version = _clean_token(
        ref.get("contract_version")
        or ref.get("current_contract_version")
        or ref.get("accepted_contract_version"),
        limit=160,
    )
    if not digest or not version:
        return {}
    return {
        "source": _clean_token(ref.get("source"), limit=160)
        or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _contract_digest_from_ref(ref: Mapping[str, Any]) -> str | None:
    return _clean_token(
        ref.get("contract_digest")
        or ref.get("current_contract_digest")
        or ref.get("accepted_contract_digest"),
        limit=128,
    )


def _analysis_packet_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "packet_id": _clean_token(packet.get("packet_id"), limit=320),
            "packet_digest": _clean_token(packet.get("packet_digest"), limit=128),
            "schema_version": _clean_token(packet.get("schema_version"), limit=160),
            "packet_kind": _clean_token(packet.get("packet_kind"), limit=160),
        }
    )


def _analyst_report_ref(report: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "report_id": _clean_token(report.get("report_id"), limit=320),
            "report_digest": _clean_token(report.get("report_digest"), limit=128),
            "schema_version": _clean_token(report.get("schema_version"), limit=160),
        }
    )


def _finding_index(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for item in _safe_list(report.get("findings")):
        finding = _safe_mapping(item)
        finding_id = _clean_token(finding.get("finding_id"), limit=320)
        reference_id = _clean_token(finding.get("reference_id"), limit=320)
        if finding_id:
            out[f"finding:{finding_id}"] = finding
        if reference_id and f"reference:{reference_id}" not in out:
            out[f"reference:{reference_id}"] = finding
    return out


def _matching_finding(
    gap: Mapping[str, Any],
    findings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    finding_id = _clean_token(gap.get("trigger_finding_id"), limit=320)
    if finding_id:
        match = findings.get(f"finding:{finding_id}")
        if match:
            return _safe_mapping(match)
    reference_id = _clean_token(
        gap.get("trigger_reference_id") or gap.get("reference_id"),
        limit=320,
    )
    if reference_id:
        return _safe_mapping(findings.get(f"reference:{reference_id}"))
    return {}


def _custody_ref(
    gap: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
) -> dict[str, Any]:
    return _safe_mapping(
        gap.get("evidence_ledger_custody_projection_ref")
        or analysis_packet.get("fetch_read_candidate_custody_ref")
    )


def _lineage_token(
    key: str,
    gap: Mapping[str, Any],
    finding: Mapping[str, Any],
    *,
    fallback_keys: Sequence[str] = (),
    limit: int = 160,
) -> str | None:
    for name in (key, *fallback_keys):
        text = _clean_token(gap.get(name), limit=limit)
        if text:
            return text
    for name in (key, *fallback_keys):
        text = _clean_token(finding.get(name), limit=limit)
        if text:
            return text
    return None


def _packet_ref(packet_id: str | None, packet_digest: str | None) -> dict[str, Any]:
    if not packet_id or not packet_digest:
        return {}
    return {"packet_id": packet_id, "packet_digest": packet_digest}


def _hint_or_default(
    gap: Mapping[str, Any],
    *keys: str,
    default: str | None,
) -> str | None:
    for key in keys:
        text = _clean_token(gap.get(key), limit=260)
        if text:
            return text
    return default


def _default_source_class_hint(kind: str | None) -> str | None:
    return {
        "missing_readable_source": "readable_replacement_source",
        "unreadable_source": "readable_replacement_source",
        "missing_fact": "fact_bearing_source",
        "currentness_concern": "official_current_or_primary_source",
        "scope_mismatch": "scope_disambiguating_source",
        "possible_contradiction": "comparison_or_reconciliation_source",
        "analysis_gap": "analysis_bearing_source",
        "analysis_missing": "analysis_bearing_source",
    }.get(str(kind or ""))


def _default_source_tier_hint(kind: str | None) -> str | None:
    if kind in {
        "missing_readable_source",
        "unreadable_source",
        "currentness_concern",
        "possible_contradiction",
    }:
        return "primary_or_official_preferred"
    return None


def _default_currentness_hint(kind: str | None) -> str | None:
    if kind == "currentness_concern":
        return "current_or_official_current"
    if kind in {"missing_readable_source", "unreadable_source"}:
        return "same_or_better_currentness_than_trigger"
    return None


def _default_priority_hint(kind: str | None) -> str | None:
    if kind in {"missing_readable_source", "unreadable_source"}:
        return "high"
    if kind in {"missing_fact", "currentness_concern", "possible_contradiction"}:
        return "medium"
    return "review"


def _budget_hint(
    gap: Mapping[str, Any],
    mode_budget_hints: Mapping[str, Any],
) -> Any:
    explicit = gap.get("budget_hint") or gap.get("proposal_budget_hint")
    if explicit not in (None, "", {}, []):
        return _json_safe(explicit)
    hints = _safe_mapping(mode_budget_hints)
    if hints.get("budget_hint") not in (None, "", {}, []):
        return hints["budget_hint"]
    compact = _without_empty(
        {
            "mode_hint": hints.get("mode_hint") or hints.get("mode"),
            "max_followup_searches": hints.get("max_followup_searches"),
            "max_query_hints": hints.get("max_query_hints"),
        }
    )
    return compact or None


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise FollowupSearchIntentPacketError(f"{context} must keep {key} false")
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if flags.get(key) is not expected:
            raise FollowupSearchIntentPacketError(
                f"{context} closed_surface_flags must keep {key} false"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FollowupSearchIntentPacketError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    _reject_raw_private_only(value, context=context)
    keys = _collect_keys(value)
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise FollowupSearchIntentPacketError(
            f"{context} includes closed authority fields: " + ", ".join(authority)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FollowupSearchIntentPacketError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _reject_raw_private_only(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise FollowupSearchIntentPacketError(
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
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise FollowupSearchIntentPacketError(f"{label} must be a mapping")
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
        raise FollowupSearchIntentPacketError(message)
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


def _proposal_digest_payload(proposal: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(proposal)
    payload.pop("proposal_id", None)
    payload.pop("proposal_digest", None)
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
    "ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE",
    "ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION",
    "FOLLOWUP_SEARCH_INTENT_PACKET_KIND",
    "FOLLOWUP_SEARCH_INTENT_PACKET_OWNER",
    "FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION",
    "FOLLOWUP_SEARCH_INTENT_PACKET_TRACE_KEY",
    "GAP_KIND_TO_FOLLOWUP_INTENT",
    "FollowupSearchIntentPacket",
    "FollowupSearchIntentPacketError",
    "build_followup_search_intent_packet",
    "followup_search_intent_packet_ref_from_packet",
    "validate_followup_search_intent_packet",
]
