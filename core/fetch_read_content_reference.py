"""Durable bounded fetch/read content references.

This module consumes the durable ``SearchResultCandidatePacket`` handoff plus
caller-supplied sanitized fetch/read material.  It does not fetch pages, call
providers, retrieve, admit EvidenceLedger custody, create citations, decide
semantic support, decide Sufficiency, create FinalAnswerPacket material, or
create Author input.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.search_result_candidate_packet import (
    search_result_candidate_packet_ref_from_packet,
    validate_search_result_candidate_packet,
)

FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION = (
    "fetch_read_content_packet_ag_fetch_read_content_reference_01_v1"
)
SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION = (
    "sanitized_content_reference_ag_fetch_read_content_reference_01_v1"
)
FETCH_READ_CONTENT_PACKET_TRACE_KEY = "fetch_read_content_packet"
FETCH_READ_CONTENT_PACKET_OWNER = "RunKernel.FetchReadContentPacket"
FETCH_READ_CONTENT_PACKET_KIND = "fetch_read_content_packet"
FETCH_READ_CONTENT_RECORD_KIND = "sanitized_content_reference"
FETCH_READ_CONTENT_PACKET_POSTURE = (
    "bounded_fetch_read_content_identity_handoff_before_evidence_ledger_custody"
)
FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS = 2_000
BOUNDED_TEXT_SELECTION_CONTEXT_POSTURES = frozenset(
    {
        "single_contiguous_window",
    }
)

FETCH_READ_STATUSES = frozenset(
    {
        "readable",
        "unreadable",
        "failed",
        "skipped",
        "blocked",
    }
)

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_pdf_bytes_retained",
        "raw_pdf_text_retained",
        "raw_headers_retained",
        "raw_prompt_retained",
        "evidence_ledger_admitted",
        "citation_created",
        "citation_eligible",
        "source_obligation_satisfied",
        "semantic_observation_created",
        "analyst_report_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    }
)

_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "body",
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
        "redirect_chain",
        "request_header",
        "request_headers",
        "response_header",
        "response_headers",
        "secret",
        "secrets",
        "serper_api_key",
        "serper_payload",
        "token",
        "unbounded_content",
        "unbounded_page_text",
        "unbounded_text",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "analyst_material",
        "analyst_report",
        "answer",
        "answer_material",
        "author_input",
        "author_material",
        "citation",
        "citation_source",
        "citation_sources",
        "citations",
        "component_coverage",
        "coverage",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_record",
        "evidence_ledger_records",
        "evidence_sources",
        "fap",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "source_obligation_claim",
        "source_obligation_satisfaction",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_CLOSED_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_page_content_retained": False,
    "raw_page_text_retained": False,
    "raw_headers_retained": False,
    "raw_prompt_retained": False,
    "evidence_ledger_admitted": False,
    "citation_created": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "semantic_observation_created": False,
    "analyst_report_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

_POSTURE_TRUE_FLAGS = {
    "closed_surface": True,
    "non_evidence": True,
    "not_evidence_ledger_custody": True,
    "not_semantic_support": True,
    "not_citation_eligible": True,
    "not_source_obligation_satisfaction": True,
    "not_sufficient": True,
    "not_final_answer_material": True,
    "not_author_input": True,
}

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_FALSE_FLAGS,
        "admitted_to_evidence_ledger",
        "answer_ready",
        "analyst_report_ready",
        "author_executor_invoked",
        "author_input_ready",
        "citation_rendered",
        "content_citation_eligible",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "final_answer_ready",
        "readiness_decided",
        "retrieval_executed",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)

_REQUIRED_REFERENCE_KEYS = (
    "run_id",
    "request_id",
    "current_answer_contract_ref",
    "current_answer_contract_digest",
    "search_executor_handoff_ref",
    "search_executor_handoff_digest",
    "search_result_candidate_packet_ref",
    "search_result_candidate_packet_digest",
    "candidate_id",
    "candidate_digest",
    "search_task_id",
    "provider_authorized",
    "provider_used",
    "provider_call_index",
    "result_rank",
    "candidate_title",
    "candidate_url",
    "candidate_domain",
    "fetch_read_status",
    "reference_id",
    "reference_digest",
)


class FetchReadContentReferenceError(ValueError):
    """Raised when fetch/read content reference construction opens a surface."""


@dataclass(frozen=True, slots=True)
class BoundedTextSelection:
    """One bounded, source-derived readable-text window plus safe selector metadata."""

    bounded_text: str
    bounded_text_char_count: int
    bounded_text_digest: str
    selection_strategy: str
    required_anchor_count: int
    matched_anchors: tuple[str, ...]
    matched_anchor_count: int
    missing_anchors: tuple[str, ...]
    selected_window_start_offset: int
    selected_window_end_offset: int
    expected_value_token_kinds: tuple[str, ...] = ()
    matched_value_token_kinds: tuple[str, ...] = ()
    matched_value_token_kind_count: int = 0
    missing_value_token_kinds: tuple[str, ...] = ()
    value_token_guidance_consumed: bool = False
    local_context_posture: str = "single_contiguous_window"
    anti_anchor_laundering_passed: bool = True
    not_semantic_support: bool = True
    not_citation_eligible: bool = True
    not_source_obligation_satisfied: bool = True

    def to_metadata(self) -> dict[str, Any]:
        return {
            "bounded_text_char_count": self.bounded_text_char_count,
            "bounded_text_digest": self.bounded_text_digest,
            "selection_strategy": self.selection_strategy,
            "required_anchor_count": self.required_anchor_count,
            "matched_anchors": list(self.matched_anchors),
            "matched_anchor_count": self.matched_anchor_count,
            "missing_anchors": list(self.missing_anchors),
            "expected_value_token_kinds": list(self.expected_value_token_kinds),
            "matched_value_token_kinds": list(self.matched_value_token_kinds),
            "matched_value_token_kind_count": self.matched_value_token_kind_count,
            "missing_value_token_kinds": list(self.missing_value_token_kinds),
            "value_token_guidance_consumed": self.value_token_guidance_consumed,
            "selected_window_start_offset": self.selected_window_start_offset,
            "selected_window_end_offset": self.selected_window_end_offset,
            "local_context_posture": self.local_context_posture,
            "anti_anchor_laundering_passed": self.anti_anchor_laundering_passed,
            "not_semantic_support": self.not_semantic_support,
            "not_citation_eligible": self.not_citation_eligible,
            "not_source_obligation_satisfied": self.not_source_obligation_satisfied,
        }


@dataclass(frozen=True, slots=True)
class _AnchorMatch:
    group_index: int
    label: str
    term: str
    start: int
    end: int


def select_bounded_answer_bearing_text(
    readable_text: str,
    max_chars: int = FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
    required_or_preferred_anchors: Sequence[Any] = (),
    expected_value_token_kinds: Sequence[str] = (),
    component_text: str | None = None,
    claim_under_test: str | None = None,
) -> BoundedTextSelection:
    """Select one coherent bounded window from sanitized readable text.

    The selector is deterministic and local: it consumes only already-sanitized
    readable text and optional caller-supplied anchor groups.  It never stitches
    distant fragments together.  Missing anchors remain missing in the metadata
    so downstream semantic checks can fail honestly.
    """

    del component_text, claim_under_test
    if max_chars <= 0:
        raise FetchReadContentReferenceError("bounded text selector requires positive max_chars")
    collapsed = _collapse_readable_text(readable_text)
    bounded_limit = min(max_chars, FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS)
    anchor_groups = _normalize_anchor_groups(required_or_preferred_anchors)
    value_token_kinds = _normalize_value_token_kinds(expected_value_token_kinds)
    if not collapsed:
        return _selection_from_window(
            text="",
            start=0,
            end=0,
            anchor_groups=anchor_groups,
            matches=(),
            expected_value_token_kinds=value_token_kinds,
            strategy="empty_readable_text",
        )
    matches = _anchor_matches(collapsed, anchor_groups)
    if len(collapsed) <= bounded_limit:
        strategy = (
            "full_text_within_cap"
            if matches or not anchor_groups
            else "full_text_within_cap_no_anchor_match"
        )
        return _selection_from_window(
            text=collapsed,
            start=0,
            end=len(collapsed),
            anchor_groups=anchor_groups,
            matches=matches,
            expected_value_token_kinds=value_token_kinds,
            strategy=strategy,
        )

    best: tuple[tuple[int, int, int, int, int, int], int, int, tuple[_AnchorMatch, ...]] | None = None
    for start in _candidate_window_starts(
        matches,
        text=collapsed,
        expected_value_token_kinds=value_token_kinds,
        text_length=len(collapsed),
        max_chars=bounded_limit,
    ):
        end = min(len(collapsed), start + bounded_limit)
        window_matches = tuple(match for match in matches if start <= match.start and match.end <= end)
        matched_group_count = len({match.group_index for match in window_matches})
        occurrence_count = len(window_matches)
        anchor_span = _window_anchor_span(window_matches)
        full_match = int(bool(anchor_groups) and matched_group_count == len(anchor_groups))
        matched_value_kind_count = len(
            set(_value_token_kind_counts(collapsed[start:end])) & set(value_token_kinds)
        )
        score = (
            full_match,
            matched_group_count,
            matched_value_kind_count,
            occurrence_count,
            -anchor_span,
            -start,
        )
        candidate = (score, start, end, window_matches)
        if best is None or score > best[0]:
            best = candidate

    if best is None:
        return _selection_from_window(
            text=collapsed,
            start=0,
            end=bounded_limit,
            anchor_groups=anchor_groups,
            matches=(),
            expected_value_token_kinds=value_token_kinds,
            strategy="prefix_fallback_no_candidate_window",
        )
    _score, start, end, window_matches = best
    matched_group_count = len({match.group_index for match in window_matches})
    strategy = (
        "answer_anchor_single_contiguous_window"
        if matched_group_count == len(anchor_groups)
        else "best_available_anchor_single_contiguous_window"
    )
    return _selection_from_window(
        text=collapsed,
        start=start,
        end=end,
        anchor_groups=anchor_groups,
        matches=window_matches,
        expected_value_token_kinds=value_token_kinds,
        strategy=strategy,
    )


@dataclass(frozen=True, slots=True)
class SanitizedContentReference:
    """One sanitized fetch/read content identity reference.

    This current shape is deliberately separate from the older AG-SEM passive
    ``SanitizedContentReference`` because it is pre-EvidenceLedger and bound to
    a ``SearchResultCandidatePacket`` lineage.
    """

    candidate_record: Mapping[str, Any]
    sanitized_fetch_read_material: Mapping[str, Any]
    search_result_candidate_packet_ref: Mapping[str, Any]
    packet_id: str | None = None
    packet_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        candidate = _safe_mapping(self.candidate_record)
        material = _sanitized_material_or_error(
            self.sanitized_fetch_read_material,
            candidate=candidate,
        )
        packet_ref = _candidate_packet_ref_or_error(
            self.search_result_candidate_packet_ref
        )
        _validate_candidate_binding(candidate, material)
        _validate_optional_lineage_claims(
            candidate=candidate,
            material=material,
            search_result_candidate_packet_ref=packet_ref,
        )
        text_payload = _bounded_text_payload(material)
        attempted_url = _clean_url(material.get("attempted_url"))
        provider_reported_url = _clean_url(material.get("provider_reported_url"))
        resolved_url = _clean_url(material.get("resolved_url"))
        final_url = _clean_url(material.get("final_url"))
        canonical_url = _clean_url(material.get("canonical_url"))
        resolved_domain = (
            _clean_domain(material.get("resolved_domain"))
            or _domain_from_url(resolved_url)
            or _domain_from_url(final_url)
            or _domain_from_url(canonical_url)
            or _domain_from_url(attempted_url)
        )
        _validate_url_domain_binding(
            candidate=candidate,
            material=material,
            attempted_url=attempted_url,
            provider_reported_url=provider_reported_url,
            resolved_url=resolved_url,
            final_url=final_url,
            canonical_url=canonical_url,
            resolved_domain=resolved_domain,
        )
        status = _fetch_read_status(material.get("fetch_read_status"))
        if status in {"failed", "unreadable", "blocked"}:
            if not (
                _clean_token(material.get("read_error_code"), limit=120)
                or _clean_text(material.get("failure_reason"), limit=500)
            ):
                raise FetchReadContentReferenceError(
                    "failed or unreadable fetch/read reference requires failure reason"
                )
        pdf_text_extraction_attempted = (
            material.get("pdf_text_extraction_attempted") is True
        )
        official_artifact_read_support = (
            material.get("official_artifact_read_support") is True
        )
        reference_base = _without_empty(
            {
                "schema_version": SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION,
                "record_kind": FETCH_READ_CONTENT_RECORD_KIND,
                "record_posture": FETCH_READ_CONTENT_PACKET_POSTURE,
                "run_id": _required_token(
                    candidate.get("run_id"),
                    "reference requires run_id",
                ),
                "request_id": _required_token(
                    candidate.get("request_id"),
                    "reference requires request_id",
                ),
                "current_answer_contract_ref": _safe_mapping(
                    candidate.get("current_answer_contract_ref")
                ),
                "current_answer_contract_digest": _required_token(
                    candidate.get("current_answer_contract_digest"),
                    "reference requires current_answer_contract_digest",
                    limit=128,
                ),
                "search_executor_handoff_ref": _safe_mapping(
                    candidate.get("search_executor_handoff_ref")
                ),
                "search_executor_handoff_digest": _required_token(
                    candidate.get("search_executor_handoff_digest"),
                    "reference requires search_executor_handoff_digest",
                    limit=128,
                ),
                "search_result_candidate_packet_ref": packet_ref,
                "search_result_candidate_packet_digest": packet_ref["packet_digest"],
                "search_result_candidate_record_digest": _required_token(
                    candidate.get("record_digest"),
                    "reference requires candidate record_digest",
                    limit=128,
                ),
                "candidate_id": _required_token(
                    candidate.get("candidate_id"),
                    "reference requires candidate_id",
                    limit=320,
                ),
                "candidate_digest": _required_token(
                    candidate.get("candidate_digest"),
                    "reference requires candidate_digest",
                    limit=128,
                ),
                "search_task_id": _required_token(
                    candidate.get("search_task_id"),
                    "reference requires search_task_id",
                    limit=260,
                ),
                "query_intent_id": _clean_token(
                    candidate.get("query_intent_id"),
                    limit=260,
                ),
                "component_id": _clean_token(
                    candidate.get("component_id"),
                    limit=260,
                ),
                "source_obligation_candidate_ids": _text_list(
                    candidate.get("source_obligation_candidate_ids")
                ),
                "provider_authorized": _required_token(
                    candidate.get("provider_authorized"),
                    "reference requires provider_authorized",
                ),
                "provider_used": _required_token(
                    candidate.get("provider_used"),
                    "reference requires provider_used",
                ),
                "provider_call_index": _positive_int(
                    candidate.get("provider_call_index"),
                    "reference requires provider_call_index",
                ),
                "result_rank": _positive_int(
                    candidate.get("result_rank"),
                    "reference requires result_rank",
                ),
                "candidate_title": _required_token(
                    candidate.get("title"),
                    "reference requires candidate title",
                    limit=220,
                ),
                "candidate_url": _required_url(
                    candidate.get("url"),
                    "reference requires candidate url",
                ),
                "candidate_domain": _required_domain(
                    candidate.get("domain"),
                    "reference requires candidate domain",
                ),
                "candidate_published_or_observed_date": _clean_token(
                    candidate.get("published_or_observed_date"),
                    limit=80,
                ),
                "fetch_read_status": status,
                "content_acquisition_mode": _clean_token(
                    material.get("content_acquisition_mode"),
                    limit=120,
                ),
                "content_acquisition_provider": _clean_token(
                    material.get("content_acquisition_provider"),
                    limit=80,
                ),
                "provider_extracted_source_content": (
                    material.get("provider_extracted_source_content") is True
                    or None
                ),
                "provider_extracted_source_text_digest": _clean_token(
                    material.get("provider_extracted_source_text_digest"),
                    limit=128,
                ),
                "provider_extracted_source_text_bounded": (
                    material.get("provider_extracted_source_text_bounded") is True
                    or None
                ),
                "provider_extracted_source_text_sanitized": (
                    material.get("provider_extracted_source_text_sanitized") is True
                    or None
                ),
                "official_artifact_read_support": (
                    official_artifact_read_support or None
                ),
                "official_artifact_type": _clean_token(
                    material.get("official_artifact_type"),
                    limit=80,
                ),
                "official_artifact_read_support_status": _clean_token(
                    material.get("official_artifact_read_support_status"),
                    limit=120,
                ),
                "official_artifact_read_support_source": _clean_token(
                    material.get("official_artifact_read_support_source"),
                    limit=120,
                ),
                "official_artifact_read_support_bounded": (
                    material.get("official_artifact_read_support_bounded") is True
                    if official_artifact_read_support
                    else None
                ),
                "official_artifact_read_support_sanitized": (
                    material.get("official_artifact_read_support_sanitized") is True
                    if official_artifact_read_support
                    else None
                ),
                "official_artifact_read_support_raw_content_retained": False
                if official_artifact_read_support
                else None,
                "official_artifact_read_support_creates_source_authority": False
                if official_artifact_read_support
                else None,
                "official_artifact_read_support_satisfies_source_obligation": False
                if official_artifact_read_support
                else None,
                "official_artifact_read_support_citation_eligible": False
                if official_artifact_read_support
                else None,
                "official_artifact_read_support_claims_correctness": False
                if official_artifact_read_support
                else None,
                "pdf_text_extraction_attempted": True
                if pdf_text_extraction_attempted
                else None,
                "pdf_text_extraction_status": _clean_token(
                    material.get("pdf_text_extraction_status"),
                    limit=80,
                )
                if pdf_text_extraction_attempted
                else None,
                "pdf_text_extraction_char_count": _optional_int(
                    material.get("pdf_text_extraction_char_count")
                )
                if pdf_text_extraction_attempted
                else None,
                "pdf_text_extraction_page_count": _optional_int(
                    material.get("pdf_text_extraction_page_count")
                )
                if pdf_text_extraction_attempted
                else None,
                "raw_pdf_bytes_retained": False
                if pdf_text_extraction_attempted
                else None,
                "raw_pdf_text_retained": False
                if pdf_text_extraction_attempted
                else None,
                "bounded_text_retained": (
                    material.get("bounded_text_retained") is True
                )
                if pdf_text_extraction_attempted
                else None,
                "pdf_parsing_opened": (
                    material.get("pdf_parsing_opened") is True
                    if pdf_text_extraction_attempted
                    else False
                )
                if official_artifact_read_support or pdf_text_extraction_attempted
                else None,
                "ocr_opened": False
                if official_artifact_read_support or pdf_text_extraction_attempted
                else None,
                "browser_automation_opened": False
                if official_artifact_read_support or pdf_text_extraction_attempted
                else None,
                "external_service_used": False
                if pdf_text_extraction_attempted
                else None,
                "heavy_document_parser_dependency_added": False
                if official_artifact_read_support or pdf_text_extraction_attempted
                else None,
                "original_source_url": _clean_url(material.get("original_source_url")),
                "original_source_title": _clean_text(
                    material.get("original_source_title"),
                    limit=300,
                ),
                "original_source_domain": _clean_domain(
                    material.get("original_source_domain")
                ),
                "attempted_url": attempted_url,
                "provider_reported_url": provider_reported_url,
                "resolved_url": resolved_url,
                "final_url": final_url,
                "canonical_url": canonical_url,
                "resolved_domain": resolved_domain,
                "content_type": _clean_token(
                    material.get("content_type"),
                    limit=160,
                ),
                "http_status": _http_status(material.get("http_status")),
                "retrieved_or_observed_at": _clean_token(
                    material.get("retrieved_or_observed_at"),
                    limit=80,
                ),
                "published_or_observed_date": _clean_token(
                    material.get("published_or_observed_date"),
                    limit=80,
                ),
                "content_title": _clean_text(
                    material.get("content_title") or material.get("title"),
                    limit=300,
                ),
                "content_length": _optional_int(material.get("content_length")),
                "read_error_code": _clean_token(
                    material.get("read_error_code"),
                    limit=120,
                ),
                "failure_reason": _clean_text(
                    material.get("failure_reason"),
                    limit=500,
                ),
                "redirect_chain_digest": _clean_token(
                    material.get("redirect_chain_digest"),
                    limit=128,
                ),
                "redirect_count": _optional_int(material.get("redirect_count")),
                **text_payload,
                **_bounded_text_selection_payload(material, text_payload),
                **_POSTURE_TRUE_FLAGS,
                **_CLOSED_FALSE_FLAGS,
            }
        )
        reference_digest = _digest_json(_reference_digest_payload(reference_base))
        reference_id = (
            "sanitized-content-reference:"
            f"{_clean_token(reference_base['request_id'], limit=120)}:"
            f"{reference_digest[:16]}"
        )
        reference = {
            **reference_base,
            "reference_id": reference_id,
            "reference_digest": reference_digest,
        }
        packet_id = _clean_token(self.packet_id, limit=260)
        packet_digest = _clean_token(self.packet_digest, limit=128)
        if packet_id and packet_digest:
            reference["packet_id"] = packet_id
            reference["packet_digest"] = packet_digest
        _validate_sanitized_content_reference(reference)
        return reference


FetchReadContentRecord = SanitizedContentReference


@dataclass(frozen=True, slots=True)
class FetchReadContentPacket:
    """Durable packet of bounded non-evidence fetch/read content references."""

    candidate_packet: Mapping[str, Any]
    sanitized_fetch_read_records: Sequence[Mapping[str, Any]]
    selected_candidate_ids: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        candidate_packet = validate_search_result_candidate_packet(self.candidate_packet)
        packet_ref = _candidate_packet_ref_or_error(
            search_result_candidate_packet_ref_from_packet(candidate_packet)
        )
        candidates = _candidate_records_by_id(candidate_packet)
        sanitized_records = _safe_list(self.sanitized_fetch_read_records)
        if not sanitized_records:
            raise FetchReadContentReferenceError(
                "fetch/read packet requires at least one sanitized record"
            )
        selected_ids = _ordered_unique(
            self.selected_candidate_ids
            or [record.get("candidate_id") for record in sanitized_records]
        )
        if len(selected_ids) != len(sanitized_records):
            raise FetchReadContentReferenceError(
                "selected fetch/read candidates must be unique"
            )
        references = []
        for material in sanitized_records:
            safe_material = _sanitized_material_or_error(material)
            candidate_id = _required_token(
                safe_material.get("candidate_id"),
                "sanitized fetch/read record requires candidate_id",
                limit=320,
            )
            candidate = candidates.get(candidate_id)
            if candidate is None:
                raise FetchReadContentReferenceError(
                    "sanitized fetch/read record is not bound to a candidate"
                )
            references.append(
                build_sanitized_content_reference_from_candidate(
                    candidate,
                    safe_material,
                    search_result_candidate_packet_ref=packet_ref,
                )
            )
        built_ids = [reference["candidate_id"] for reference in references]
        if selected_ids != built_ids:
            raise FetchReadContentReferenceError(
                "selected candidate order does not match sanitized records"
            )
        packet_base = _without_empty(
            {
                "schema_version": FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION,
                "packet_kind": FETCH_READ_CONTENT_PACKET_KIND,
                "trace_key": FETCH_READ_CONTENT_PACKET_TRACE_KEY,
                "owner": FETCH_READ_CONTENT_PACKET_OWNER,
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_posture": FETCH_READ_CONTENT_PACKET_POSTURE,
                "run_id": _required_token(
                    candidate_packet.get("run_id"),
                    "fetch/read packet requires run_id",
                ),
                "request_id": _required_token(
                    candidate_packet.get("request_id"),
                    "fetch/read packet requires request_id",
                ),
                "current_answer_contract_ref": _candidate_packet_contract_ref(
                    candidate_packet
                ),
                "current_answer_contract_digest": _required_token(
                    _candidate_packet_contract_ref(candidate_packet).get(
                        "contract_digest"
                    ),
                    "fetch/read packet requires current_answer_contract_digest",
                    limit=128,
                ),
                "search_executor_handoff_ref": _safe_mapping(
                    candidate_packet.get("search_executor_handoff_ref")
                ),
                "search_executor_handoff_digest": _required_token(
                    candidate_packet.get("search_executor_handoff_digest"),
                    "fetch/read packet requires search_executor_handoff_digest",
                    limit=128,
                ),
                "search_result_candidate_packet_ref": packet_ref,
                "search_result_candidate_packet_digest": packet_ref["packet_digest"],
                "selected_candidate_ids": selected_ids,
                "reference_count": len(references),
                "reference_records": references,
                **_POSTURE_TRUE_FLAGS,
                **_CLOSED_FALSE_FLAGS,
            }
        )
        packet_digest = _digest_json(_packet_digest_payload(packet_base))
        packet_id = (
            "fetch-read-content-packet:"
            f"{_clean_token(packet_base['request_id'], limit=120)}:"
            f"{packet_digest[:16]}"
        )
        packet = {
            **packet_base,
            "packet_id": packet_id,
            "packet_digest": packet_digest,
            "reference_records": [
                {
                    **reference,
                    "packet_id": packet_id,
                    "packet_digest": packet_digest,
                }
                for reference in references
            ],
        }
        validate_fetch_read_content_packet(packet)
        return packet


def build_fetch_read_content_packet_from_candidate_packet(
    candidate_packet: Mapping[str, Any],
    sanitized_fetch_read_records: Sequence[Mapping[str, Any]],
    *,
    selected_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a durable fetch/read content packet from selected candidates."""

    return FetchReadContentPacket(
        candidate_packet=candidate_packet,
        sanitized_fetch_read_records=sanitized_fetch_read_records,
        selected_candidate_ids=selected_candidate_ids,
    ).to_dict()


def build_fetch_read_content_packet_from_navigation(
    *,
    run_id: str,
    request_id: str,
    answer_contract_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    source_obligation_ref: Mapping[str, Any],
    navigation_lineage: Mapping[str, Any],
    terminal_receipt_ref: Mapping[str, Any],
    custody_authorization_ref: Mapping[str, Any],
    sanitized_material: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the navigation-origin branch of the existing FetchRead family."""

    from core.searchos_navigation_runtime import (
        validate_navigation_destination_for_binding,
    )

    material = _safe_mapping(sanitized_material)
    if _fetch_read_status(material.get("fetch_read_status")) != "readable":
        raise FetchReadContentReferenceError("navigation content is not readable")
    text_payload = _bounded_text_payload(material)
    if not text_payload:
        raise FetchReadContentReferenceError("navigation content is empty")
    contract = _safe_mapping(answer_contract_ref)
    lineage = _safe_mapping(navigation_lineage)
    required_lineage = (
        "slot_ref",
        "navigation_option_ref",
        "navigation_selection_ref",
        "destination_binding_ref",
        "parent_read_custody_ref",
    )
    if any(not _safe_mapping(lineage.get(key)) for key in required_lineage):
        raise FetchReadContentReferenceError("navigation lineage is incomplete")
    attempted_url = validate_navigation_destination_for_binding(
        material.get("attempted_url"), lineage["destination_binding_ref"]
    )
    reference_base = {
        "schema_version": SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION,
        "record_kind": FETCH_READ_CONTENT_RECORD_KIND,
        "record_posture": FETCH_READ_CONTENT_PACKET_POSTURE,
        "origin": "searchos_navigation",
        "run_id": _required_token(run_id, "navigation reference requires run_id"),
        "request_id": _required_token(
            request_id, "navigation reference requires request_id"
        ),
        "current_answer_contract_ref": contract,
        "current_answer_contract_digest": _required_token(
            contract.get("contract_digest"),
            "navigation reference requires contract digest",
            limit=128,
        ),
        "component_ref": _safe_mapping(component_ref),
        "source_obligation_ref": _safe_mapping(source_obligation_ref),
        **{key: _safe_mapping(lineage[key]) for key in required_lineage},
        "terminal_receipt_ref": _safe_mapping(terminal_receipt_ref),
        "custody_authorization_ref": _safe_mapping(custody_authorization_ref),
        "fetch_read_status": "readable",
        "attempted_url": attempted_url,
        "provider_reported_url": _clean_url(material.get("provider_reported_url")),
        "resolved_url": _clean_url(material.get("resolved_url")),
        "final_url": _clean_url(material.get("final_url")),
        "canonical_url": _clean_url(material.get("canonical_url")),
        "content_type": _clean_token(material.get("content_type"), limit=160),
        "retrieved_or_observed_at": _clean_token(
            material.get("retrieved_or_observed_at"), limit=80
        ),
        "content_title": _clean_text(material.get("content_title"), limit=300),
        **text_payload,
        **_POSTURE_TRUE_FLAGS,
        **_CLOSED_FALSE_FLAGS,
    }
    reference_digest = _digest_json(_reference_digest_payload(reference_base))
    reference = {
        **reference_base,
        "reference_id": (
            f"sanitized-content-reference:{request_id}:{reference_digest[:16]}"
        ),
        "reference_digest": reference_digest,
    }
    packet_base = {
        "schema_version": FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION,
        "packet_kind": FETCH_READ_CONTENT_PACKET_KIND,
        "trace_key": FETCH_READ_CONTENT_PACKET_TRACE_KEY,
        "owner": FETCH_READ_CONTENT_PACKET_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "packet_posture": FETCH_READ_CONTENT_PACKET_POSTURE,
        "origin": "searchos_navigation",
        "run_id": reference_base["run_id"],
        "request_id": reference_base["request_id"],
        "current_answer_contract_ref": contract,
        "current_answer_contract_digest": reference_base[
            "current_answer_contract_digest"
        ],
        "reference_count": 1,
        "reference_records": [reference],
        **_POSTURE_TRUE_FLAGS,
        **_CLOSED_FALSE_FLAGS,
    }
    packet_digest = _digest_json(_packet_digest_payload(packet_base))
    packet_id = f"fetch-read-content-packet:{request_id}:{packet_digest[:16]}"
    packet = {
        **packet_base,
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "reference_records": [
            {**reference, "packet_id": packet_id, "packet_digest": packet_digest}
        ],
    }
    return validate_fetch_read_content_packet(packet)


def reduce_candidate_packet_and_sanitized_reads_to_fetch_read_packet(
    candidate_packet: Mapping[str, Any],
    sanitized_fetch_read_records: Sequence[Mapping[str, Any]],
    *,
    selected_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Reducer alias for the candidate-packet plus sanitized-read seam."""

    return build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        sanitized_fetch_read_records,
        selected_candidate_ids=selected_candidate_ids,
    )


def build_sanitized_content_reference_from_candidate(
    candidate_record: Mapping[str, Any],
    sanitized_fetch_read_material: Mapping[str, Any],
    *,
    search_result_candidate_packet_ref: Mapping[str, Any],
    packet_id: str | None = None,
    packet_digest: str | None = None,
) -> dict[str, Any]:
    """Build one pre-custody sanitized content reference from one candidate."""

    return SanitizedContentReference(
        candidate_record=candidate_record,
        sanitized_fetch_read_material=sanitized_fetch_read_material,
        search_result_candidate_packet_ref=search_result_candidate_packet_ref,
        packet_id=packet_id,
        packet_digest=packet_digest,
    ).to_dict()


def validate_fetch_read_content_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a sanitized fetch/read content packet."""

    raw = _required_mapping(packet, "fetch/read content packet")
    _reject_forbidden_surface_claims(raw, context="fetch/read content packet")
    safe = _safe_mapping(raw)
    if safe.get("schema_version") != FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION:
        raise FetchReadContentReferenceError("fetch/read packet schema mismatch")
    if safe.get("packet_kind") != FETCH_READ_CONTENT_PACKET_KIND:
        raise FetchReadContentReferenceError("fetch/read packet kind mismatch")
    if safe.get("owner") != FETCH_READ_CONTENT_PACKET_OWNER:
        raise FetchReadContentReferenceError("fetch/read packet owner mismatch")
    if safe.get("packet_posture") != FETCH_READ_CONTENT_PACKET_POSTURE:
        raise FetchReadContentReferenceError("fetch/read packet posture mismatch")
    _validate_closed_flags(safe, context="fetch/read packet")
    _validate_posture_flags(safe, context="fetch/read packet")
    run_id = _required_token(safe.get("run_id"), "fetch/read packet requires run_id")
    request_id = _required_token(
        safe.get("request_id"),
        "fetch/read packet requires request_id",
    )
    if safe.get("origin") == "searchos_navigation":
        return _validate_navigation_fetch_read_packet(
            safe,
            run_id=run_id,
            request_id=request_id,
        )
    contract_ref = _safe_mapping(safe.get("current_answer_contract_ref"))
    handoff_ref = _safe_mapping(safe.get("search_executor_handoff_ref"))
    if not contract_ref or not handoff_ref:
        raise FetchReadContentReferenceError(
            "fetch/read packet requires contract and handoff refs"
        )
    if safe.get("current_answer_contract_digest") != contract_ref.get(
        "contract_digest"
    ):
        raise FetchReadContentReferenceError(
            "fetch/read packet current_answer_contract digest mismatch"
        )
    if safe.get("search_executor_handoff_digest") != handoff_ref.get(
        "handoff_digest"
    ):
        raise FetchReadContentReferenceError(
            "fetch/read packet SearchExecutorHandoff digest mismatch"
        )
    packet_ref = _candidate_packet_ref_or_error(
        safe.get("search_result_candidate_packet_ref")
    )
    if safe.get("search_result_candidate_packet_digest") != packet_ref[
        "packet_digest"
    ]:
        raise FetchReadContentReferenceError(
            "fetch/read packet candidate packet digest mismatch"
        )
    references = _safe_list(safe.get("reference_records"))
    if safe.get("reference_count") != len(references):
        raise FetchReadContentReferenceError(
            "fetch/read packet reference_count mismatch"
        )
    selected_candidate_ids = _ordered_unique(safe.get("selected_candidate_ids"))
    if len(selected_candidate_ids) != len(references):
        raise FetchReadContentReferenceError(
            "fetch/read packet selected candidate count mismatch"
        )
    seen_reference_ids: set[str] = set()
    seen_candidate_ids: set[str] = set()
    for reference in references:
        validated = _validate_sanitized_content_reference(
            reference,
            run_id=run_id,
            request_id=request_id,
            current_answer_contract_ref=contract_ref,
            search_executor_handoff_ref=handoff_ref,
            search_result_candidate_packet_ref=packet_ref,
            packet_id=safe.get("packet_id"),
            packet_digest=safe.get("packet_digest"),
        )
        reference_id = str(validated["reference_id"])
        candidate_id = str(validated["candidate_id"])
        if reference_id in seen_reference_ids:
            raise FetchReadContentReferenceError(
                "fetch/read packet duplicate reference_id"
            )
        if candidate_id in seen_candidate_ids:
            raise FetchReadContentReferenceError(
                "fetch/read packet duplicate candidate_id"
            )
        seen_reference_ids.add(reference_id)
        seen_candidate_ids.add(candidate_id)
    if selected_candidate_ids != [reference["candidate_id"] for reference in references]:
        raise FetchReadContentReferenceError(
            "fetch/read packet selected candidate order mismatch"
        )
    declared_digest = _required_token(
        safe.get("packet_digest"),
        "fetch/read packet requires packet_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_packet_digest_payload(safe)):
        raise FetchReadContentReferenceError("fetch/read packet digest mismatch")
    expected_packet_id = (
        "fetch-read-content-packet:"
        f"{_clean_token(request_id, limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_packet_id:
        raise FetchReadContentReferenceError("fetch/read packet id mismatch")
    return safe


def _validate_navigation_fetch_read_packet(
    safe: Mapping[str, Any], *, run_id: str, request_id: str
) -> dict[str, Any]:
    from core.searchos_navigation_runtime import (
        validate_navigation_destination_binding_ref,
        validate_navigation_destination_for_binding,
    )

    contract = _safe_mapping(safe.get("current_answer_contract_ref"))
    if safe.get("current_answer_contract_digest") != contract.get(
        "contract_digest"
    ):
        raise FetchReadContentReferenceError("navigation packet contract mismatch")
    references = _safe_list(safe.get("reference_records"))
    if safe.get("reference_count") != 1 or len(references) != 1:
        raise FetchReadContentReferenceError("navigation packet requires one reference")
    reference = _safe_mapping(references[0])
    if (
        reference.get("origin") != "searchos_navigation"
        or reference.get("schema_version")
        != SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION
        or reference.get("record_kind") != FETCH_READ_CONTENT_RECORD_KIND
        or reference.get("record_posture") != FETCH_READ_CONTENT_PACKET_POSTURE
        or reference.get("run_id") != run_id
        or reference.get("request_id") != request_id
        or _safe_mapping(reference.get("current_answer_contract_ref")) != contract
    ):
        raise FetchReadContentReferenceError("navigation reference lineage mismatch")
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
    ):
        if not _safe_mapping(reference.get(key)):
            raise FetchReadContentReferenceError("navigation reference is incomplete")
    validate_navigation_destination_binding_ref(
        reference["destination_binding_ref"]
    )
    if reference.get("fetch_read_status") != "readable":
        raise FetchReadContentReferenceError("navigation reference is not readable")
    validate_navigation_destination_for_binding(
        reference.get("attempted_url"),
        reference["destination_binding_ref"],
    )
    _validate_closed_flags(reference, context="navigation content reference")
    _validate_posture_flags(reference, context="navigation content reference")
    _validate_bounded_text_digest(reference)
    declared_reference_digest = _required_token(
        reference.get("reference_digest"),
        "navigation reference requires digest",
        limit=128,
    )
    if declared_reference_digest != _digest_json(
        _reference_digest_payload(reference)
    ) or reference.get("reference_id") != (
        f"sanitized-content-reference:{request_id}:{declared_reference_digest[:16]}"
    ):
        raise FetchReadContentReferenceError("navigation reference identity mismatch")
    declared_packet_digest = _required_token(
        safe.get("packet_digest"),
        "navigation packet requires digest",
        limit=128,
    )
    if (
        reference.get("packet_id") != safe.get("packet_id")
        or reference.get("packet_digest") != declared_packet_digest
        or declared_packet_digest != _digest_json(_packet_digest_payload(safe))
        or safe.get("packet_id")
        != f"fetch-read-content-packet:{request_id}:{declared_packet_digest[:16]}"
    ):
        raise FetchReadContentReferenceError("navigation packet identity mismatch")
    return _safe_mapping(safe)


def fetch_read_content_packet_ref_from_packet(
    packet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the compact downstream reference for a fetch/read content packet."""

    safe = _safe_mapping(packet)
    packet_id = _clean_token(safe.get("packet_id"), limit=260)
    packet_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if not packet_id or not packet_digest:
        return {}
    return {
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "schema_version": _clean_token(safe.get("schema_version")),
        "reference_count": _bounded_int(safe.get("reference_count")),
    }


def _candidate_records_by_id(candidate_packet: Mapping[str, Any]) -> dict[str, Any]:
    records = _safe_list(candidate_packet.get("candidate_records"))
    by_id: dict[str, Any] = {}
    seen_digests: set[str] = set()
    for record in records:
        safe = _candidate_record_for_fetch_read(candidate_packet, record)
        candidate_id = _required_token(
            safe.get("candidate_id"),
            "candidate record requires candidate_id",
            limit=320,
        )
        candidate_digest = _required_token(
            safe.get("candidate_digest"),
            "candidate record requires candidate_digest",
            limit=128,
        )
        if candidate_id in by_id or candidate_digest in seen_digests:
            raise FetchReadContentReferenceError(
                "candidate packet contains duplicate selected candidate"
            )
        by_id[candidate_id] = safe
        seen_digests.add(candidate_digest)
    return by_id


def _candidate_packet_contract_ref(
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    return _safe_mapping(
        candidate_packet.get("current_answer_contract_ref")
        or candidate_packet.get("answer_contract_ref")
    )


def _candidate_record_for_fetch_read(
    candidate_packet: Mapping[str, Any],
    record: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(record)
    if safe.get("origin_kind") != "ordinary_query_provider":
        return safe
    contract_ref = _candidate_packet_contract_ref(candidate_packet)
    handoff_ref = _safe_mapping(candidate_packet.get("search_executor_handoff_ref"))
    source_result_ref = _safe_mapping(safe.get("source_result_ref"))
    url = _required_url(
        safe.get("normalized_url"),
        "ordinary content reference requires candidate url",
    )
    domain = _required_domain(
        safe.get("domain") or _domain_from_url(url),
        "ordinary content reference requires candidate domain",
    )
    return _without_empty(
        {
            **safe,
            "current_answer_contract_ref": contract_ref,
            "current_answer_contract_digest": contract_ref.get(
                "contract_digest"
            ),
            "search_executor_handoff_ref": handoff_ref,
            "search_executor_handoff_digest": handoff_ref.get("handoff_digest"),
            "search_task_id": source_result_ref.get("source_result_id"),
            "provider_call_index": safe.get("provider_call_ordinal"),
            "result_rank": safe.get("provider_result_rank"),
            "title": safe.get("title") or domain,
            "url": url,
            "domain": domain,
        }
    )


def _validate_sanitized_content_reference(
    reference: Mapping[str, Any],
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    current_answer_contract_ref: Mapping[str, Any] | None = None,
    search_executor_handoff_ref: Mapping[str, Any] | None = None,
    search_result_candidate_packet_ref: Mapping[str, Any] | None = None,
    packet_id: str | None = None,
    packet_digest: str | None = None,
) -> dict[str, Any]:
    raw = _required_mapping(reference, "sanitized content reference")
    _reject_forbidden_surface_claims(raw, context="sanitized content reference")
    safe = _safe_mapping(raw)
    if safe.get("schema_version") != SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION:
        raise FetchReadContentReferenceError("content reference schema mismatch")
    if safe.get("record_kind") != FETCH_READ_CONTENT_RECORD_KIND:
        raise FetchReadContentReferenceError("content reference kind mismatch")
    if safe.get("record_posture") != FETCH_READ_CONTENT_PACKET_POSTURE:
        raise FetchReadContentReferenceError("content reference posture mismatch")
    _validate_closed_flags(safe, context="content reference")
    _validate_posture_flags(safe, context="content reference")
    for key in _REQUIRED_REFERENCE_KEYS:
        if safe.get(key) in (None, ""):
            raise FetchReadContentReferenceError(f"content reference requires {key}")
    if run_id is not None and safe.get("run_id") != run_id:
        raise FetchReadContentReferenceError("content reference run_id mismatch")
    if request_id is not None and safe.get("request_id") != request_id:
        raise FetchReadContentReferenceError("content reference request_id mismatch")
    contract_ref = _safe_mapping(safe.get("current_answer_contract_ref"))
    handoff_ref = _safe_mapping(safe.get("search_executor_handoff_ref"))
    if current_answer_contract_ref is not None and contract_ref != _safe_mapping(
        current_answer_contract_ref
    ):
        raise FetchReadContentReferenceError(
            "content reference current_answer_contract ref mismatch"
        )
    if search_executor_handoff_ref is not None and handoff_ref != _safe_mapping(
        search_executor_handoff_ref
    ):
        raise FetchReadContentReferenceError(
            "content reference SearchExecutorHandoff ref mismatch"
        )
    packet_ref = _candidate_packet_ref_or_error(
        safe.get("search_result_candidate_packet_ref")
    )
    if search_result_candidate_packet_ref is not None and packet_ref != _safe_mapping(
        search_result_candidate_packet_ref
    ):
        raise FetchReadContentReferenceError(
            "content reference candidate packet ref mismatch"
        )
    if safe.get("search_result_candidate_packet_digest") != packet_ref[
        "packet_digest"
    ]:
        raise FetchReadContentReferenceError(
            "content reference candidate packet digest mismatch"
        )
    if safe.get("current_answer_contract_digest") != contract_ref.get(
        "contract_digest"
    ):
        raise FetchReadContentReferenceError(
            "content reference current_answer_contract digest mismatch"
        )
    if safe.get("search_executor_handoff_digest") != handoff_ref.get(
        "handoff_digest"
    ):
        raise FetchReadContentReferenceError(
            "content reference SearchExecutorHandoff digest mismatch"
        )
    if packet_id is not None and safe.get("packet_id") != packet_id:
        raise FetchReadContentReferenceError("content reference packet_id mismatch")
    if packet_digest is not None and safe.get("packet_digest") != packet_digest:
        raise FetchReadContentReferenceError(
            "content reference packet_digest mismatch"
        )
    _fetch_read_status(safe.get("fetch_read_status"))
    _required_url(safe.get("candidate_url"), "content reference requires candidate url")
    _required_domain(
        safe.get("candidate_domain"),
        "content reference requires candidate domain",
    )
    _positive_int(
        safe.get("provider_call_index"),
        "content reference requires provider_call_index",
    )
    _positive_int(safe.get("result_rank"), "content reference requires result_rank")
    if safe.get("bounded_text"):
        _validate_bounded_text_digest(safe)
    if safe.get("bounded_text_selection"):
        _validate_bounded_text_selection_metadata(safe["bounded_text_selection"], safe)
    declared_digest = _required_token(
        safe.get("reference_digest"),
        "content reference requires reference_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_reference_digest_payload(safe)):
        raise FetchReadContentReferenceError("content reference digest mismatch")
    expected_reference_id = (
        "sanitized-content-reference:"
        f"{_clean_token(safe.get('request_id'), limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if safe.get("reference_id") != expected_reference_id:
        raise FetchReadContentReferenceError("content reference id mismatch")
    return safe


def _sanitized_material_or_error(
    material: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _required_mapping(material, "sanitized fetch/read material")
    _reject_forbidden_surface_claims(raw, context="sanitized fetch/read material")
    safe = _safe_mapping(raw)
    _fetch_read_status(safe.get("fetch_read_status"))
    _required_token(
        safe.get("candidate_id"),
        "sanitized fetch/read material requires candidate_id",
        limit=320,
    )
    _required_token(
        safe.get("candidate_digest"),
        "sanitized fetch/read material requires candidate_digest",
        limit=128,
    )
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if key in safe and safe.get(key) is not expected:
            raise FetchReadContentReferenceError(
                f"sanitized fetch/read material must keep {key} false"
            )
    if candidate is not None:
        _validate_candidate_binding(candidate, safe)
    _bounded_text_payload(safe)
    return safe


def _validate_candidate_binding(
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
) -> None:
    if material.get("candidate_id") != candidate.get("candidate_id"):
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material candidate_id mismatch"
        )
    if material.get("candidate_digest") != candidate.get("candidate_digest"):
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material candidate_digest mismatch"
        )


def _validate_optional_lineage_claims(
    *,
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
    search_result_candidate_packet_ref: Mapping[str, Any],
) -> None:
    lineage_pairs = (
        ("run_id", "run_id", 160),
        ("request_id", "request_id", 160),
        ("current_answer_contract_digest", "current_answer_contract_digest", 128),
        ("search_executor_handoff_digest", "search_executor_handoff_digest", 128),
    )
    for material_key, candidate_key, limit in lineage_pairs:
        material_value = _clean_token(material.get(material_key), limit=limit)
        if material_value and material_value != _clean_token(
            candidate.get(candidate_key),
            limit=limit,
        ):
            raise FetchReadContentReferenceError(
                f"sanitized fetch/read material {material_key} mismatch"
            )
    packet_digest = _clean_token(
        material.get("search_result_candidate_packet_digest"),
        limit=128,
    )
    if packet_digest and packet_digest != search_result_candidate_packet_ref[
        "packet_digest"
    ]:
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material candidate packet digest mismatch"
        )
    packet_id = _clean_token(
        material.get("search_result_candidate_packet_id"),
        limit=260,
    )
    if packet_id and packet_id != search_result_candidate_packet_ref["packet_id"]:
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material candidate packet id mismatch"
        )


def _validate_url_domain_binding(
    *,
    candidate: Mapping[str, Any],
    material: Mapping[str, Any],
    attempted_url: str | None,
    provider_reported_url: str | None,
    resolved_url: str | None,
    final_url: str | None,
    canonical_url: str | None,
    resolved_domain: str | None,
) -> None:
    candidate_url = _required_url(
        candidate.get("url"),
        "content reference requires candidate url",
    )
    _required_domain(
        candidate.get("domain") or _domain_from_url(candidate_url),
        "content reference requires candidate domain",
    )
    status = _fetch_read_status(material.get("fetch_read_status"))
    if status == "readable" and not any(
        (
            attempted_url,
            provider_reported_url,
            resolved_url,
            final_url,
            canonical_url,
            resolved_domain,
        )
    ):
        raise FetchReadContentReferenceError(
            "readable content reference requires URL or domain identity"
        )
    if attempted_url and _normalized_url(attempted_url) != _normalized_url(
        candidate_url
    ):
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material attempted_url does not match candidate URL"
        )
    # Provider-reported, resolved, final, canonical, and resolved-domain facts
    # are optional provenance. They never replace requested/attempted identity
    # and may differ without invalidating the authorized READ.


def _bounded_text_payload(material: Mapping[str, Any]) -> dict[str, Any]:
    has_text = "bounded_text" in material and material.get("bounded_text") not in (
        None,
        "",
    )
    has_excerpt = "bounded_excerpt" in material and material.get(
        "bounded_excerpt"
    ) not in (None, "")
    if has_text and has_excerpt:
        if _clean_text(material.get("bounded_text"), limit=10_000) != _clean_text(
            material.get("bounded_excerpt"),
            limit=10_000,
        ):
            raise FetchReadContentReferenceError(
                "sanitized fetch/read material has conflicting bounded text fields"
            )
    if not has_text and not has_excerpt:
        return {}
    marker_sanitized = any(
        material.get(key) is True
        for key in (
            "bounded_text_sanitized",
            "bounded_excerpt_sanitized",
            "sanitized",
        )
    )
    marker_bounded = any(
        material.get(key) is True
        for key in (
            "bounded_text_bounded",
            "bounded_excerpt_bounded",
            "bounded",
            "bounded_text_explicitly_bounded",
        )
    ) or any(
        key in material
        for key in (
            "bounded_text_char_count",
            "bounded_excerpt_char_count",
            "bounded_character_count",
        )
    )
    if not marker_sanitized or not marker_bounded:
        raise FetchReadContentReferenceError(
            "bounded text must be explicitly sanitized and bounded"
        )
    bounded_text = _clean_text(
        material.get("bounded_text") if has_text else material.get("bounded_excerpt"),
        limit=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS + 1,
    )
    if not bounded_text:
        return {}
    if len(bounded_text) > FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS:
        raise FetchReadContentReferenceError(
            "bounded text exceeds fetch/read content reference limit"
        )
    declared_count = (
        _optional_int(material.get("bounded_character_count"))
        or _optional_int(material.get("bounded_text_char_count"))
        or _optional_int(material.get("bounded_excerpt_char_count"))
    )
    bounded_character_count = len(bounded_text)
    if declared_count is not None and declared_count != bounded_character_count:
        raise FetchReadContentReferenceError("bounded text character count mismatch")
    excerpt_digest = _digest_json({"bounded_text": bounded_text})
    for key in ("excerpt_digest", "content_digest"):
        declared_digest = _clean_token(material.get(key), limit=128)
        if declared_digest and declared_digest != excerpt_digest:
            raise FetchReadContentReferenceError(f"{key} mismatch")
    return {
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_character_count": bounded_character_count,
        "excerpt_digest": excerpt_digest,
    }


def _bounded_text_selection_payload(
    material: Mapping[str, Any],
    text_payload: Mapping[str, Any],
) -> dict[str, Any]:
    raw = material.get("bounded_text_selection")
    if not raw:
        return {}
    metadata = _safe_mapping(raw)
    _validate_bounded_text_selection_metadata(metadata, text_payload)
    return {"bounded_text_selection": metadata}


def _validate_bounded_text_selection_metadata(
    metadata: Mapping[str, Any],
    reference_or_text_payload: Mapping[str, Any],
) -> None:
    safe = _safe_mapping(metadata)
    allowed = {
        "bounded_text_char_count",
        "bounded_text_digest",
        "selection_strategy",
        "required_anchor_count",
        "matched_anchors",
        "matched_anchor_count",
        "missing_anchors",
        "expected_value_token_kinds",
        "matched_value_token_kinds",
        "matched_value_token_kind_count",
        "missing_value_token_kinds",
        "value_token_guidance_consumed",
        "selected_window_start_offset",
        "selected_window_end_offset",
        "local_context_posture",
        "anti_anchor_laundering_passed",
        "not_semantic_support",
        "not_citation_eligible",
        "not_source_obligation_satisfied",
    }
    extra = sorted(set(safe) - allowed)
    if extra:
        raise FetchReadContentReferenceError(
            "bounded text selection metadata contains unsupported keys: "
            + ", ".join(extra)
        )
    if safe.get("local_context_posture") not in BOUNDED_TEXT_SELECTION_CONTEXT_POSTURES:
        raise FetchReadContentReferenceError("bounded text selection context posture mismatch")
    for key in (
        "anti_anchor_laundering_passed",
        "not_semantic_support",
        "not_citation_eligible",
        "not_source_obligation_satisfied",
    ):
        if safe.get(key) is not True:
            raise FetchReadContentReferenceError(f"bounded text selection metadata requires {key}")
    count = _optional_int(safe.get("bounded_text_char_count"))
    if count != reference_or_text_payload.get("bounded_character_count"):
        raise FetchReadContentReferenceError("bounded text selection character count mismatch")
    if safe.get("bounded_text_digest") != reference_or_text_payload.get("excerpt_digest"):
        raise FetchReadContentReferenceError("bounded text selection digest mismatch")
    start = _optional_int(safe.get("selected_window_start_offset"))
    end = _optional_int(safe.get("selected_window_end_offset"))
    if start is None or end is None or start < 0 or end < start:
        raise FetchReadContentReferenceError("bounded text selection offsets invalid")
    if end - start != count:
        raise FetchReadContentReferenceError("bounded text selection offsets do not match bounded count")
    required_count = _optional_int(safe.get("required_anchor_count"))
    matched_count = _optional_int(safe.get("matched_anchor_count"))
    if required_count is None or matched_count is None or matched_count > required_count:
        raise FetchReadContentReferenceError("bounded text selection anchor counts invalid")
    matched = _text_list(safe.get("matched_anchors"), limit=120)
    missing = _text_list(safe.get("missing_anchors"), limit=120)
    if matched_count != len(matched):
        raise FetchReadContentReferenceError("bounded text selection matched anchor count mismatch")
    if required_count != len(matched) + len(missing):
        raise FetchReadContentReferenceError("bounded text selection required anchor count mismatch")
    expected_value_kinds = _text_list(safe.get("expected_value_token_kinds"), limit=40)
    matched_value_kinds = _text_list(safe.get("matched_value_token_kinds"), limit=40)
    missing_value_kinds = _text_list(safe.get("missing_value_token_kinds"), limit=40)
    matched_value_count = _optional_int(safe.get("matched_value_token_kind_count"))
    if matched_value_count is None or matched_value_count != len(matched_value_kinds):
        raise FetchReadContentReferenceError("bounded text selection value-token count mismatch")
    if len(expected_value_kinds) != len(matched_value_kinds) + len(missing_value_kinds):
        raise FetchReadContentReferenceError("bounded text selection value-token expectation mismatch")
    if bool(expected_value_kinds) != (safe.get("value_token_guidance_consumed") is True):
        raise FetchReadContentReferenceError("bounded text selection value-token guidance flag mismatch")


def _validate_bounded_text_digest(reference: Mapping[str, Any]) -> None:
    text = _clean_text(
        reference.get("bounded_text"),
        limit=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS + 1,
    )
    if not text:
        return
    if reference.get("bounded_text_sanitized") is not True:
        raise FetchReadContentReferenceError(
            "content reference bounded text must be sanitized"
        )
    if reference.get("bounded_text_bounded") is not True:
        raise FetchReadContentReferenceError(
            "content reference bounded text must be bounded"
        )
    if reference.get("bounded_character_count") != len(text):
        raise FetchReadContentReferenceError(
            "content reference bounded text character count mismatch"
        )
    if reference.get("excerpt_digest") != _digest_json({"bounded_text": text}):
        raise FetchReadContentReferenceError("content reference excerpt digest mismatch")


def _candidate_packet_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    packet_id = _clean_token(ref.get("packet_id"), limit=260)
    packet_digest = _clean_token(ref.get("packet_digest"), limit=128)
    if not packet_id or not packet_digest:
        raise FetchReadContentReferenceError(
            "fetch/read content reference requires SearchResultCandidatePacket ref"
        )
    return _without_empty(
        {
            "packet_id": packet_id,
            "packet_digest": packet_digest,
            "schema_version": _clean_token(ref.get("schema_version")),
            "candidate_count": _bounded_int(ref.get("candidate_count")),
        }
    )


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise FetchReadContentReferenceError(f"{context} must keep {key} false")
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if key in flags and flags.get(key) is not expected:
            raise FetchReadContentReferenceError(
                f"{context} closed surface flag {key} must be false"
            )


def _validate_posture_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _POSTURE_TRUE_FLAGS.items():
        if value.get(key) is not expected:
            raise FetchReadContentReferenceError(f"{context} must keep {key} true")


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise FetchReadContentReferenceError(
            f"{context} contains raw/private fields: "
            + ", ".join(raw_or_private)
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise FetchReadContentReferenceError(
            f"{context} includes closed authority fields: " + ", ".join(authority)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FetchReadContentReferenceError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
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


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FetchReadContentReferenceError(f"{label} must be a mapping")
    return value


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
        return _clean_token(value, limit=2_100)
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
    return _clean_token(value, limit=300)


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise FetchReadContentReferenceError(message)
    return text


def _required_url(value: Any, message: str) -> str:
    url = _required_token(value, message, limit=700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FetchReadContentReferenceError("content reference requires http(s) url")
    return url


def _clean_url(value: Any) -> str | None:
    url = _clean_token(value, limit=700)
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FetchReadContentReferenceError(
            "sanitized fetch/read material URL requires http(s)"
        )
    return url


def _required_domain(value: Any, message: str) -> str:
    domain = _clean_domain(value)
    if not domain:
        raise FetchReadContentReferenceError(message)
    return domain


def _fetch_read_status(value: Any) -> str:
    status = _required_token(
        value,
        "sanitized fetch/read material requires fetch_read_status",
        limit=80,
    ).casefold()
    if status not in FETCH_READ_STATUSES:
        raise FetchReadContentReferenceError("fetch_read_status is not allowed")
    return status


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise FetchReadContentReferenceError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise FetchReadContentReferenceError("expected bounded integer") from exc
    if parsed < 0:
        raise FetchReadContentReferenceError("expected non-negative integer")
    return parsed


def _http_status(value: Any) -> int | None:
    if value in (None, ""):
        return None
    status = _optional_int(value)
    if status is None or not 100 <= status <= 599:
        raise FetchReadContentReferenceError("http_status must be between 100 and 599")
    return status


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    return _clean_token(value, limit=limit)


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_key_token(value: Any, *, limit: int = 120) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    return parsed.netloc.lower() or None


def _normalized_url(value: str) -> str:
    parsed = urlparse(value)
    query = f"?{parsed.query}" if parsed.query else ""
    return (
        f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        f"{parsed.path.rstrip('/')}{query}"
    )


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


def _collapse_readable_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_anchor_groups(anchors: Sequence[Any]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    groups: list[tuple[str, tuple[str, ...]]] = []
    for anchor in anchors:
        if isinstance(anchor, str):
            alternatives = tuple(
                item.strip()
                for item in re.split(r"\s+/\s+|\|", anchor)
                if item.strip()
            )
        elif isinstance(anchor, Sequence):
            alternatives = tuple(str(item).strip() for item in anchor if str(item).strip())
        else:
            alternatives = (str(anchor).strip(),) if str(anchor).strip() else ()
        normalized = tuple(dict.fromkeys(alternatives))
        if not normalized:
            continue
        label = "/".join(normalized)
        groups.append((label, normalized))
    return tuple(groups)


def _anchor_matches(
    text: str,
    anchor_groups: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[_AnchorMatch, ...]:
    matches: list[_AnchorMatch] = []
    for group_index, (label, alternatives) in enumerate(anchor_groups):
        for term in alternatives:
            for match in _iter_anchor_term_matches(text, term):
                matches.append(
                    _AnchorMatch(
                        group_index=group_index,
                        label=label,
                        term=term,
                        start=match.start(),
                        end=match.end(),
                    )
                )
    return tuple(sorted(matches, key=lambda item: (item.start, item.end, item.group_index, item.term)))


def _iter_anchor_term_matches(text: str, term: str) -> tuple[re.Match[str], ...]:
    normalized = " ".join(str(term or "").split())
    if not normalized:
        return ()
    if normalized.startswith("$") and normalized[1:].isdigit():
        pattern = rf"(?<!\w)\$\s*{re.escape(normalized[1:])}\b"
    else:
        escaped = re.escape(normalized).replace(r"\ ", r"\s+")
        prefix = r"\b" if normalized[0].isalnum() else r"(?<!\w)"
        suffix = r"\b" if normalized[-1].isalnum() else r"(?!\w)"
        pattern = f"{prefix}{escaped}{suffix}"
    return tuple(re.finditer(pattern, text, flags=re.IGNORECASE))


_VALUE_TOKEN_KIND_PATTERNS = {
    "currency": r"\$\s?\d{1,6}(?:,\d{3})*(?:\.\d{2})?",
    "percent": r"\b\d{1,3}(?:\.\d+)?%",
    "date_like": r"\b(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?\b",
    "number": r"\b\d+(?:,\d{3})*(?:\.\d+)?\b",
}


def _normalize_value_token_kinds(kinds: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for kind in kinds:
        normalized = _normalize_key(kind)
        if normalized in _VALUE_TOKEN_KIND_PATTERNS and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return tuple(out)


def _value_token_kind_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind, pattern in _VALUE_TOKEN_KIND_PATTERNS.items():
        matches = {match.group(0) for match in re.finditer(pattern, text)}
        if matches:
            counts[kind] = len(matches)
    return counts


def _iter_value_token_spans(
    text: str,
    expected_value_token_kinds: Sequence[str],
) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    for kind in expected_value_token_kinds:
        pattern = _VALUE_TOKEN_KIND_PATTERNS.get(kind)
        if not pattern:
            continue
        spans.extend((match.start(), match.end()) for match in re.finditer(pattern, text))
    return tuple(sorted(set(spans)))


def _candidate_window_starts(
    matches: Sequence[_AnchorMatch],
    *,
    text: str,
    expected_value_token_kinds: Sequence[str],
    text_length: int,
    max_chars: int,
) -> tuple[int, ...]:
    starts = {0, max(0, text_length - max_chars)}
    context_margin = min(240, max_chars // 4)
    for match in matches:
        for raw in (
            match.start,
            match.start - context_margin,
            match.start - (max_chars // 3),
            match.end - max_chars,
        ):
            starts.add(_clamp_window_start(raw, text_length=text_length, max_chars=max_chars))
    for start, end in _iter_value_token_spans(text, expected_value_token_kinds):
        for raw in (
            start,
            start - context_margin,
            start - (max_chars // 3),
            end - max_chars,
        ):
            starts.add(_clamp_window_start(raw, text_length=text_length, max_chars=max_chars))
    return tuple(sorted(starts))


def _clamp_window_start(value: int, *, text_length: int, max_chars: int) -> int:
    latest = max(0, text_length - max_chars)
    return max(0, min(latest, value))


def _window_anchor_span(matches: Sequence[_AnchorMatch]) -> int:
    if not matches:
        return 0
    return max(match.end for match in matches) - min(match.start for match in matches)


def _selection_from_window(
    *,
    text: str,
    start: int,
    end: int,
    anchor_groups: Sequence[tuple[str, tuple[str, ...]]],
    matches: Sequence[_AnchorMatch],
    expected_value_token_kinds: Sequence[str],
    strategy: str,
) -> BoundedTextSelection:
    bounded_text = text[start:end].rstrip()
    end = start + len(bounded_text)
    matched_indices = {match.group_index for match in matches if start <= match.start and match.end <= end}
    matched_anchors = tuple(
        label
        for index, (label, _alternatives) in enumerate(anchor_groups)
        if index in matched_indices
    )
    missing_anchors = tuple(
        label
        for index, (label, _alternatives) in enumerate(anchor_groups)
        if index not in matched_indices
    )
    value_counts = _value_token_kind_counts(bounded_text)
    expected_value_kinds = tuple(expected_value_token_kinds)
    matched_value_kinds = tuple(kind for kind in expected_value_kinds if value_counts.get(kind))
    missing_value_kinds = tuple(kind for kind in expected_value_kinds if kind not in matched_value_kinds)
    return BoundedTextSelection(
        bounded_text=bounded_text,
        bounded_text_char_count=len(bounded_text),
        bounded_text_digest=_digest_json({"bounded_text": bounded_text}),
        selection_strategy=strategy,
        required_anchor_count=len(anchor_groups),
        matched_anchors=matched_anchors,
        matched_anchor_count=len(matched_anchors),
        missing_anchors=missing_anchors,
        expected_value_token_kinds=expected_value_kinds,
        matched_value_token_kinds=matched_value_kinds,
        matched_value_token_kind_count=len(matched_value_kinds),
        missing_value_token_kinds=missing_value_kinds,
        value_token_guidance_consumed=bool(expected_value_kinds),
        selected_window_start_offset=start,
        selected_window_end_offset=end,
    )


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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _reference_digest_payload(reference: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(reference)
    payload.pop("reference_id", None)
    payload.pop("reference_digest", None)
    payload.pop("packet_id", None)
    payload.pop("packet_digest", None)
    return payload


def _packet_digest_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(packet)
    payload.pop("packet_id", None)
    payload.pop("packet_digest", None)
    if isinstance(payload.get("reference_records"), list):
        payload["reference_records"] = [
            _reference_for_packet_digest(reference)
            for reference in payload["reference_records"]
        ]
    return payload


def _reference_for_packet_digest(reference: Any) -> dict[str, Any]:
    payload = _safe_mapping(reference)
    payload.pop("packet_id", None)
    payload.pop("packet_digest", None)
    return payload


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS",
    "FETCH_READ_CONTENT_PACKET_KIND",
    "FETCH_READ_CONTENT_PACKET_OWNER",
    "FETCH_READ_CONTENT_PACKET_POSTURE",
    "FETCH_READ_CONTENT_PACKET_SCHEMA_VERSION",
    "FETCH_READ_CONTENT_PACKET_TRACE_KEY",
    "FETCH_READ_CONTENT_RECORD_KIND",
    "FETCH_READ_STATUSES",
    "BOUNDED_TEXT_SELECTION_CONTEXT_POSTURES",
    "BoundedTextSelection",
    "FetchReadContentPacket",
    "FetchReadContentRecord",
    "FetchReadContentReferenceError",
    "SANITIZED_CONTENT_REFERENCE_SCHEMA_VERSION",
    "SanitizedContentReference",
    "build_fetch_read_content_packet_from_candidate_packet",
    "build_fetch_read_content_packet_from_navigation",
    "build_sanitized_content_reference_from_candidate",
    "fetch_read_content_packet_ref_from_packet",
    "reduce_candidate_packet_and_sanitized_reads_to_fetch_read_packet",
    "select_bounded_answer_bearing_text",
    "validate_fetch_read_content_packet",
]
