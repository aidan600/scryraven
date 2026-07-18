"""Durable non-evidence search-result candidate packet.

This module reduces the existing live-search-validation candidate output into a
closed-surface packet that downstream fetch/read phases can consume later.  The
records are discovery candidates only: they are not evidence, fetched content,
citations, source-obligation satisfaction, Sufficiency input, FinalAnswerPacket
material, or Author material.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION = (
    "search_result_candidate_packet_ag_search_result_candidate_packet_01_v1"
)
SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION = (
    "search_result_candidate_record_ag_search_result_candidate_packet_01_v1"
)
SEARCH_RESULT_CANDIDATE_PACKET_TRACE_KEY = "search_result_candidate_packet"
SEARCH_RESULT_CANDIDATE_PACKET_OWNER = "RunKernel.SearchResultCandidatePacket"
SEARCH_RESULT_CANDIDATE_PACKET_KIND = "search_result_candidate_packet"
SEARCH_RESULT_CANDIDATE_RECORD_KIND = "search_result_candidate_record"
SEARCH_RESULT_CANDIDATE_PACKET_POSTURE = (
    "non_evidence_candidate_discovery_handoff_before_fetch_read"
)
ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION = (
    "search_result_candidate_packet_ordinary_query_provider_v1"
)
ORDINARY_SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION = (
    "search_result_candidate_record_ordinary_query_provider_v1"
)
SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER = (
    "ordinary_query_provider"
)
ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION = 1
ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_MAX_CANDIDATES = 40
ORDINARY_SEARCH_RESULT_CANDIDATE_MAX_CONTRIBUTOR_REFS = 8
ORDINARY_SEARCH_RESULT_CANDIDATE_SNIPPET_MAX_CHARS = 500

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
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
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "serper_api_key",
        "serper_payload",
        "token",
        "unbounded_text",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "answer",
        "author_input",
        "author_material",
        "citation",
        "citation_source",
        "citation_sources",
        "citations",
        "content_fetched_from_url",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_admission",
        "evidence_sources",
        "fap",
        "fetched_content",
        "final_answer",
        "final_answer_packet",
        "read_content",
        "retrieved_content",
        "semantic_observation",
        "source_obligation_claim",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_CLOSED_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "fetched_content_included": False,
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "read_executed": False,
    "evidence_ledger_admitted": False,
    "evidence_created": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

_POSTURE_TRUE_FLAGS = {
    "closed_surface": True,
    "non_evidence": True,
    "not_fetched": True,
    "not_read": True,
    "not_citation": True,
    "not_citation_eligible": True,
    "not_sufficient": True,
    "not_source_obligation_satisfaction": True,
}

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_FALSE_FLAGS,
        "answer_ready",
        "author_executor_invoked",
        "broker_called",
        "citation_rendered",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "fetch_executed",
        "final_answer_ready",
        "live_provider_call_executed",
        "live_search_called",
        "provider_payload_retained",
        "readiness_decided",
        "retrieval_executed",
        "search_candidate_sufficient",
        "source_obligation_support_created",
    }
)

_REQUIRED_RECORD_KEYS = (
    "run_id",
    "request_id",
    "search_task_id",
    "provider_authorized",
    "provider_used",
    "provider_call_index",
    "result_rank",
    "title",
    "url",
    "domain",
    "candidate_id",
    "candidate_digest",
)


class SearchResultCandidatePacketError(ValueError):
    """Raised when a candidate packet or record would open a closed surface."""


@dataclass(frozen=True, slots=True)
class SearchResultCandidateRecord:
    """One sanitized search-result discovery record.

    The record intentionally preserves candidate lineage and search metadata
    only. It does not carry fetched/read content or evidence material.
    """

    run_id: str
    request_id: str
    current_answer_contract_ref: Mapping[str, Any]
    search_executor_handoff_ref: Mapping[str, Any]
    search_task_id: str
    provider_authorized: str
    provider_used: str
    provider_call_index: int
    result_rank: int
    title: str
    url: str
    domain: str
    candidate_id: str
    candidate_digest: str
    validation_id: str | None = None
    parent_live_search_validation_ref: Mapping[str, Any] = field(
        default_factory=dict
    )
    query_intent_id: str | None = None
    component_id: str | None = None
    source_obligation_candidate_ids: Sequence[str] = field(default_factory=tuple)
    snippet: str | None = None
    published_or_observed_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        contract_ref = _contract_ref_or_error(self.current_answer_contract_ref)
        handoff_ref = _handoff_ref_or_error(self.search_executor_handoff_ref)
        record = _without_empty(
            {
                "schema_version": SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION,
                "record_kind": SEARCH_RESULT_CANDIDATE_RECORD_KIND,
                "record_posture": SEARCH_RESULT_CANDIDATE_PACKET_POSTURE,
                "run_id": _required_token(self.run_id, "record requires run_id"),
                "request_id": _required_token(
                    self.request_id,
                    "record requires request_id",
                ),
                "current_answer_contract_ref": contract_ref,
                "current_answer_contract_digest": contract_ref["contract_digest"],
                "search_executor_handoff_ref": handoff_ref,
                "search_executor_handoff_digest": handoff_ref["handoff_digest"],
                "parent_live_search_validation_ref": _safe_mapping(
                    self.parent_live_search_validation_ref
                ),
                "validation_id": _clean_token(self.validation_id, limit=260),
                "search_task_id": _required_token(
                    self.search_task_id,
                    "record requires search_task_id",
                    limit=260,
                ),
                "query_intent_id": _clean_token(self.query_intent_id, limit=260),
                "component_id": _clean_token(self.component_id, limit=260),
                "source_obligation_candidate_ids": _text_list(
                    self.source_obligation_candidate_ids
                ),
                "provider_authorized": _required_token(
                    self.provider_authorized,
                    "record requires provider_authorized",
                ),
                "provider_used": _required_token(
                    self.provider_used,
                    "record requires provider_used",
                ),
                "provider_call_index": _positive_int(
                    self.provider_call_index,
                    "record requires provider_call_index",
                ),
                "result_rank": _positive_int(
                    self.result_rank,
                    "record requires result_rank",
                ),
                "title": _required_token(
                    self.title,
                    "record requires title",
                    limit=220,
                ),
                "url": _required_url(self.url),
                "domain": _clean_domain(self.domain) or _domain_from_url(self.url),
                "snippet": _clean_text(self.snippet, limit=500),
                "published_or_observed_date": _clean_token(
                    self.published_or_observed_date,
                    limit=80,
                ),
                "candidate_id": _required_token(
                    self.candidate_id,
                    "record requires candidate_id",
                    limit=320,
                ),
                "candidate_digest": _required_token(
                    self.candidate_digest,
                    "record requires candidate_digest",
                    limit=128,
                ),
                **_POSTURE_TRUE_FLAGS,
                **_CLOSED_FALSE_FLAGS,
            }
        )
        record["record_digest"] = _digest_json(_record_digest_payload(record))
        return record


@dataclass(frozen=True, slots=True)
class SearchResultCandidatePacket:
    """Durable packet of non-evidence search-result candidates."""

    run_id: str
    request_id: str
    current_answer_contract_ref: Mapping[str, Any]
    search_executor_handoff_ref: Mapping[str, Any]
    candidate_records: Sequence[Mapping[str, Any]]
    selected_search_task_ids: Sequence[str] = field(default_factory=tuple)
    provider_authorized: str | None = None
    provider_used: str | None = None
    parent_live_search_validation_ref: Mapping[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        contract_ref = _contract_ref_or_error(self.current_answer_contract_ref)
        handoff_ref = _handoff_ref_or_error(self.search_executor_handoff_ref)
        records = [_safe_mapping(record) for record in self.candidate_records]
        selected_task_ids = _ordered_unique(
            self.selected_search_task_ids
            or [record.get("search_task_id") for record in records]
        )
        provider_authorized = (
            _clean_token(self.provider_authorized)
            or _first_token(records, "provider_authorized")
        )
        provider_used = (
            _clean_token(self.provider_used) or _first_token(records, "provider_used")
        )
        packet_base = _without_empty(
            {
                "schema_version": SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION,
                "packet_kind": SEARCH_RESULT_CANDIDATE_PACKET_KIND,
                "trace_key": SEARCH_RESULT_CANDIDATE_PACKET_TRACE_KEY,
                "owner": SEARCH_RESULT_CANDIDATE_PACKET_OWNER,
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_posture": SEARCH_RESULT_CANDIDATE_PACKET_POSTURE,
                "run_id": _required_token(self.run_id, "packet requires run_id"),
                "request_id": _required_token(
                    self.request_id,
                    "packet requires request_id",
                ),
                "current_answer_contract_ref": contract_ref,
                "current_answer_contract_digest": contract_ref["contract_digest"],
                "search_executor_handoff_ref": handoff_ref,
                "search_executor_handoff_digest": handoff_ref["handoff_digest"],
                "parent_live_search_validation_ref": _safe_mapping(
                    self.parent_live_search_validation_ref
                ),
                "selected_search_task_ids": selected_task_ids,
                "provider_authorized": provider_authorized,
                "provider_used": provider_used,
                "candidate_count": len(records),
                "candidate_records": records,
                **_POSTURE_TRUE_FLAGS,
                **_CLOSED_FALSE_FLAGS,
            }
        )
        packet_digest = _digest_json(_packet_digest_payload(packet_base))
        packet_id = (
            "search-result-candidate-packet:"
            f"{_clean_token(packet_base['request_id'], limit=120)}:"
            f"{packet_digest[:16]}"
        )
        packet = {
            **packet_base,
            "packet_id": packet_id,
            "packet_digest": packet_digest,
        }
        validate_search_result_candidate_packet(packet)
        return packet


def reduce_live_search_validation_candidates_to_packet(
    live_search_validation_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Reduce a live-search-validation state/output shape into a packet."""

    return build_search_result_candidate_packet_from_live_search_validation_output(
        live_search_validation_output
    )


def build_search_result_candidate_packet_from_live_validation_state(
    validation_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a candidate packet from reduced live-search-validation state."""

    state = _required_mapping(validation_state, "live search validation state")
    _reject_forbidden_surface_claims(
        state,
        context="live search validation state",
    )
    return _build_packet_from_source(
        source=state,
        current_ref=state.get("parent_current_contract_ref"),
        handoff_ref=state.get("parent_search_executor_handoff_ref"),
        candidates=state.get("search_result_candidates"),
        selected_search_task_ids=state.get("selected_search_task_ids"),
        provider_authorized=state.get("provider_authorized"),
        provider_used=state.get("provider_used"),
        parent_validation_ref=_live_search_validation_ref_from_state(state),
    )


def build_search_result_candidate_packet_from_live_search_validation_output(
    live_search_validation_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a candidate packet from existing validation output shapes.

    Accepted inputs are the PR1 observation payload, reduced validation state,
    validation projection, or the PR2/LIVE-RUN-01 output packet. All inputs must
    already be sanitized; raw/private or authority-bearing keys fail closed.
    """

    output = _required_mapping(
        live_search_validation_output,
        "live search validation output",
    )
    if isinstance(output.get("live_search_validation"), Mapping):
        return build_search_result_candidate_packet_from_live_validation_state(
            _safe_mapping(output["live_search_validation"])
        )
    _reject_forbidden_surface_claims(
        output,
        context="live search validation output",
    )
    current_ref = output.get("parent_current_contract_ref") or output.get(
        "current_answer_contract_ref"
    )
    handoff_ref = output.get("parent_search_executor_handoff_ref") or output.get(
        "search_executor_handoff_ref"
    )
    parent_validation_ref = (
        _safe_mapping(output.get("parent_live_search_validation_ref"))
        or _safe_mapping(output.get("live_search_validation_ref"))
        or _live_search_validation_ref_from_state(output)
        or _live_search_validation_ref_from_candidates(
            output.get("search_result_candidates")
        )
    )
    return _build_packet_from_source(
        source=output,
        current_ref=current_ref,
        handoff_ref=handoff_ref,
        candidates=output.get("search_result_candidates"),
        selected_search_task_ids=output.get("selected_search_task_ids"),
        provider_authorized=output.get("provider_authorized"),
        provider_used=output.get("provider_used"),
        parent_validation_ref=parent_validation_ref,
    )


def build_search_result_candidate_record_from_live_candidate(
    candidate: Mapping[str, Any],
    *,
    current_answer_contract_ref: Mapping[str, Any] | None = None,
    search_executor_handoff_ref: Mapping[str, Any] | None = None,
    parent_live_search_validation_ref: Mapping[str, Any] | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    provider_authorized: str | None = None,
    provider_used: str | None = None,
) -> dict[str, Any]:
    """Build one durable record from one live-validation candidate."""

    raw = _required_mapping(candidate, "search result candidate")
    _reject_forbidden_surface_claims(raw, context="search result candidate")
    for key in _REQUIRED_RECORD_KEYS:
        if key not in raw or raw.get(key) in (None, ""):
            raise SearchResultCandidatePacketError(
                f"search result candidate requires {key}"
            )
    _validate_live_candidate_digest(raw)
    record = SearchResultCandidateRecord(
        run_id=_required_token(
            run_id or raw.get("run_id"),
            "record requires run_id",
        ),
        request_id=_required_token(
            request_id or raw.get("request_id"),
            "record requires request_id",
        ),
        current_answer_contract_ref=(
            current_answer_contract_ref or raw.get("parent_current_contract_ref")
        ),
        search_executor_handoff_ref=(
            search_executor_handoff_ref
            or raw.get("parent_search_executor_handoff_ref")
        ),
        parent_live_search_validation_ref=parent_live_search_validation_ref or {},
        validation_id=_clean_token(raw.get("validation_id"), limit=260),
        search_task_id=_required_token(
            raw.get("search_task_id"),
            "record requires search_task_id",
            limit=260,
        ),
        query_intent_id=_clean_token(raw.get("query_intent_id"), limit=260),
        component_id=_clean_token(raw.get("component_id"), limit=260),
        source_obligation_candidate_ids=_text_list(
            raw.get("source_obligation_candidate_ids")
        ),
        provider_authorized=_required_token(
            provider_authorized or raw.get("provider_authorized"),
            "record requires provider_authorized",
        ),
        provider_used=_required_token(
            provider_used or raw.get("provider_used"),
            "record requires provider_used",
        ),
        provider_call_index=_positive_int(
            raw.get("provider_call_index"),
            "record requires provider_call_index",
        ),
        result_rank=_positive_int(
            raw.get("result_rank"),
            "record requires result_rank",
        ),
        title=_required_token(raw.get("title"), "record requires title", limit=220),
        url=_required_url(raw.get("url")),
        domain=_clean_domain(raw.get("domain")) or _domain_from_url(str(raw["url"])),
        snippet=_clean_text(raw.get("snippet"), limit=500),
        published_or_observed_date=_clean_token(
            raw.get("published_or_observed_date"),
            limit=80,
        ),
        candidate_id=_required_token(
            raw.get("candidate_id"),
            "record requires candidate_id",
            limit=320,
        ),
        candidate_digest=_required_token(
            raw.get("candidate_digest"),
            "record requires candidate_digest",
            limit=128,
        ),
    ).to_dict()
    _validate_candidate_record(record)
    return record


def build_search_result_candidate_packet_from_ordinary_discovery(
    *,
    run_id: str,
    request_id: str,
    search_executor_handoff_ref: Mapping[str, Any],
    source_result_identity_set_ref: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_candidate_inputs_digest: str,
    answer_contract_ref: Mapping[str, Any] | None = None,
    packet_revision: int = ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION,
) -> dict[str, Any]:
    """Build the sole candidate packet from already-resolved ordinary results.

    The source-result and material identities must already exist.  This builder
    validates and consumes those references; it never reconstructs identity
    from URL/title/snippet fields and never performs acquisition or fetch work.
    """

    clean_run_id = _required_token(run_id, "ordinary packet requires run_id")
    clean_request_id = _required_token(
        request_id,
        "ordinary packet requires request_id",
    )
    if packet_revision != ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet requires revision 1"
        )
    if isinstance(candidates, str | bytes) or not isinstance(candidates, Sequence):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet requires candidate mappings"
        )
    if not candidates:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet requires at least one selected candidate"
        )
    if len(candidates) > ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_MAX_CANDIDATES:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet exceeds the 40-candidate cap"
        )
    expected_candidate_inputs_digest = ordinary_candidate_inputs_digest(
        candidates
    )
    if selected_candidate_inputs_digest != expected_candidate_inputs_digest:
        raise SearchResultCandidatePacketError(
            "ordinary packet candidate-input authorization digest mismatch"
        )
    identity_set_ref = _ordinary_identity_set_ref_or_error(
        source_result_identity_set_ref
    )
    handoff_ref = _ordinary_handoff_ref_or_error(search_executor_handoff_ref)
    if (
        handoff_ref["source_result_identity_set_ref"]
        != identity_set_ref
    ):
        raise SearchResultCandidatePacketError(
            "ordinary packet identity-set ref does not match handoff"
        )
    contract_ref = _optional_contract_ref(answer_contract_ref)
    handoff_contract_ref = _safe_mapping(handoff_ref.get("answer_contract_ref"))
    if handoff_contract_ref != contract_ref:
        raise SearchResultCandidatePacketError(
            "ordinary packet answer-contract ref does not match handoff"
        )
    records = [
        build_search_result_candidate_record_from_ordinary_candidate(
            candidate,
            run_id=clean_run_id,
            request_id=clean_request_id,
            search_executor_handoff_ref=handoff_ref,
            answer_contract_ref=contract_ref,
        )
        for candidate in candidates
    ]
    ordered_candidate_record_digests_digest = (
        _ordinary_ordered_candidate_record_digests_digest(records)
    )
    selected_source_refs = [
        _safe_mapping(record.get("source_result_ref")) for record in records
    ]
    if selected_source_refs != _safe_list(
        handoff_ref.get("selected_source_result_refs")
    ):
        raise SearchResultCandidatePacketError(
            "ordinary packet selected source refs do not match handoff order"
        )
    if len(selected_source_refs) > identity_set_ref["source_result_identity_count"]:
        raise SearchResultCandidatePacketError(
            "ordinary packet selects more results than the identity set"
        )
    full_selected_source_result_refs_digest = _digest_json(
        selected_source_refs
    )
    packet_base = _without_empty(
        {
            "schema_version": (
                ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION
            ),
            "packet_kind": SEARCH_RESULT_CANDIDATE_PACKET_KIND,
            "trace_key": SEARCH_RESULT_CANDIDATE_PACKET_TRACE_KEY,
            "owner": SEARCH_RESULT_CANDIDATE_PACKET_OWNER,
            "origin_kind": (
                SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER
            ),
            "packet_revision": ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION,
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "packet_posture": SEARCH_RESULT_CANDIDATE_PACKET_POSTURE,
            "run_id": clean_run_id,
            "request_id": clean_request_id,
            "answer_contract_ref": contract_ref,
            "search_executor_handoff_ref": handoff_ref,
            "search_executor_handoff_digest": handoff_ref["handoff_digest"],
            "source_result_identity_set_ref": identity_set_ref,
            "selected_source_result_refs": selected_source_refs,
            "full_selected_source_result_refs_digest": (
                full_selected_source_result_refs_digest
            ),
            "selected_candidate_inputs_digest": (
                expected_candidate_inputs_digest
            ),
            "candidate_count": len(records),
            "ordered_candidate_record_digests_digest": (
                ordered_candidate_record_digests_digest
            ),
            "candidate_records": records,
            **_POSTURE_TRUE_FLAGS,
            **_CLOSED_FALSE_FLAGS,
            **_ordinary_closed_runtime_fields(),
        }
    )
    packet_digest = ordinary_search_result_candidate_packet_binding_digest(
        packet_base
    )
    packet = {
        **packet_base,
        "packet_id": (
            "search-result-candidate-packet:"
            f"{_clean_token(clean_request_id, limit=120)}:"
            f"{packet_digest[:16]}"
        ),
        "packet_digest": packet_digest,
    }
    return validate_ordinary_search_result_candidate_packet(packet)


def build_search_result_candidate_record_from_ordinary_candidate(
    candidate: Mapping[str, Any],
    *,
    run_id: str,
    request_id: str,
    search_executor_handoff_ref: Mapping[str, Any],
    answer_contract_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one ordinary packet record from pre-existing identity/material refs."""

    raw = _required_mapping(candidate, "ordinary search-result candidate")
    _reject_forbidden_surface_claims(raw, context="ordinary search-result candidate")
    source_result_ref = _ordinary_source_result_ref_or_error(
        raw.get("source_result_ref") or raw.get("source_identity_ref") or raw
    )
    source_material_input = _safe_mapping(
        raw.get("source_material_ref") or raw.get("material_ref")
    )
    if raw.get("material_class") and not source_material_input.get(
        "material_class"
    ):
        source_material_input["material_class"] = raw.get("material_class")
    source_material_ref = _ordinary_source_material_ref_or_error(
        source_material_input
    )
    provider_used = _required_token(
        raw.get("provider_used") or raw.get("provider"),
        "ordinary candidate requires provider",
        limit=120,
    )
    provider_authorized = _required_token(
        raw.get("provider_authorized") or provider_used,
        "ordinary candidate requires authorized provider",
        limit=120,
    )
    provider_call_ordinal = _positive_int(
        raw.get("provider_call_ordinal")
        or raw.get("provider_call_index")
        or raw.get("call_ordinal"),
        "ordinary candidate requires provider call ordinal",
    )
    provider_result_rank = _positive_int(
        raw.get("provider_result_rank") or raw.get("result_rank"),
        "ordinary candidate requires provider result rank",
    )
    selected_candidate_rank = _positive_int(
        raw.get("selected_candidate_rank") or raw.get("selected_rank"),
        "ordinary candidate requires selected candidate rank",
    )
    url = _required_url(raw.get("normalized_url") or raw.get("url"))
    title = _clean_text(raw.get("title"), limit=220)
    relevance_score = _ordinary_score_or_error(
        raw.get("relevance_score")
        if raw.get("relevance_score") is not None
        else raw.get("ranking_score", raw.get("score"))
    )
    scoring_provenance = _ordinary_scoring_provenance_or_error(raw)
    contributor_refs, overflow_count, overflow_digest = (
        _ordinary_contributor_refs(raw)
    )
    handoff_ref = _ordinary_handoff_ref_or_error(search_executor_handoff_ref)
    contract_ref = _optional_contract_ref(answer_contract_ref)
    candidate_core = _without_empty(
        {
            "source_result_ref": source_result_ref,
            "source_material_ref": source_material_ref,
            "selected_candidate_rank": selected_candidate_rank,
            "search_executor_handoff_ref": handoff_ref,
        }
    )
    candidate_digest = _digest_json(candidate_core)
    record = _without_empty(
        {
            "schema_version": (
                ORDINARY_SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION
            ),
            "record_kind": SEARCH_RESULT_CANDIDATE_RECORD_KIND,
            "record_posture": SEARCH_RESULT_CANDIDATE_PACKET_POSTURE,
            "origin_kind": (
                SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER
            ),
            "packet_revision": ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION,
            "run_id": _required_token(run_id, "ordinary record requires run_id"),
            "request_id": _required_token(
                request_id,
                "ordinary record requires request_id",
            ),
            "answer_contract_ref": contract_ref,
            "search_executor_handoff_ref": handoff_ref,
            "search_executor_handoff_digest": handoff_ref["handoff_digest"],
            "source_result_ref": source_result_ref,
            "source_material_ref": source_material_ref,
            "provider_authorized": provider_authorized,
            "provider_used": provider_used,
            "provider_call_ordinal": provider_call_ordinal,
            "provider_result_rank": provider_result_rank,
            "selected_candidate_rank": selected_candidate_rank,
            "title": title,
            "normalized_url": url,
            "domain": _clean_domain(raw.get("domain")) or _domain_from_url(url),
            "snippet": _clean_text(
                raw.get("snippet"),
                limit=ORDINARY_SEARCH_RESULT_CANDIDATE_SNIPPET_MAX_CHARS,
            ),
            "published_or_observed_date": _clean_token(
                raw.get("published_or_observed_date") or raw.get("date"),
                limit=80,
            ),
            "relevance_score": relevance_score,
            "scoring_provenance": scoring_provenance,
            "contributing_source_result_refs": contributor_refs,
            "contributor_ref_count": len(contributor_refs),
            "contributor_overflow_count": overflow_count,
            "contributor_overflow_digest": overflow_digest,
            "candidate_id": (
                "search-result-candidate:ordinary:"
                f"{source_result_ref['source_result_id']}:"
                f"{selected_candidate_rank}"
            ),
            "candidate_digest": candidate_digest,
            **_POSTURE_TRUE_FLAGS,
            **_CLOSED_FALSE_FLAGS,
            **_ordinary_closed_runtime_fields(),
        }
    )
    record["record_digest"] = _digest_json(_record_digest_payload(record))
    _validate_ordinary_candidate_record(record)
    return record


def validate_ordinary_search_result_candidate_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the ordinary-origin branch under the canonical packet owner."""

    raw = _required_mapping(packet, "ordinary search-result candidate packet")
    _reject_forbidden_surface_claims(
        raw,
        context="ordinary search-result candidate packet",
    )
    safe = _safe_mapping(raw)
    if (
        safe.get("schema_version")
        != ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION
    ):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet schema mismatch"
        )
    if safe.get("packet_kind") != SEARCH_RESULT_CANDIDATE_PACKET_KIND:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet kind mismatch"
        )
    if safe.get("owner") != SEARCH_RESULT_CANDIDATE_PACKET_OWNER:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet owner mismatch"
        )
    if (
        safe.get("origin_kind")
        != SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER
    ):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet origin mismatch"
        )
    if (
        safe.get("packet_revision")
        != ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION
    ):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet revision mismatch"
        )
    if safe.get("packet_posture") != SEARCH_RESULT_CANDIDATE_PACKET_POSTURE:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet posture mismatch"
        )
    _validate_closed_flags(safe, context="ordinary candidate packet")
    _validate_posture_flags(safe, context="ordinary candidate packet")
    _validate_ordinary_closed_runtime_fields(
        safe,
        context="ordinary candidate packet",
    )
    run_id = _required_token(safe.get("run_id"), "ordinary packet requires run_id")
    request_id = _required_token(
        safe.get("request_id"),
        "ordinary packet requires request_id",
    )
    contract_ref = _optional_contract_ref(safe.get("answer_contract_ref"))
    handoff_ref = _ordinary_handoff_ref_or_error(
        safe.get("search_executor_handoff_ref")
    )
    if safe.get("search_executor_handoff_digest") != handoff_ref["handoff_digest"]:
        raise SearchResultCandidatePacketError(
            "ordinary packet handoff digest mismatch"
        )
    if _safe_mapping(handoff_ref.get("answer_contract_ref")) != contract_ref:
        raise SearchResultCandidatePacketError(
            "ordinary packet contract ref does not match handoff"
        )
    identity_set_ref = _ordinary_identity_set_ref_or_error(
        safe.get("source_result_identity_set_ref")
    )
    if (
        _safe_mapping(handoff_ref.get("source_result_identity_set_ref"))
        != identity_set_ref
    ):
        raise SearchResultCandidatePacketError(
            "ordinary packet identity-set ref does not match handoff"
        )
    records = _safe_list(safe.get("candidate_records"))
    if not records:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet requires candidate records"
        )
    if len(records) > ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_MAX_CANDIDATES:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet exceeds the 40-candidate cap"
        )
    if safe.get("candidate_count") != len(records):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet candidate_count mismatch"
        )
    selected_refs = [
        _ordinary_source_result_ref_or_error(item)
        for item in _safe_list(safe.get("selected_source_result_refs"))
    ]
    if len(selected_refs) != len(records):
        raise SearchResultCandidatePacketError(
            "ordinary packet selected-source count mismatch"
        )
    if selected_refs != _safe_list(handoff_ref.get("selected_source_result_refs")):
        raise SearchResultCandidatePacketError(
            "ordinary packet selected-source refs do not match handoff"
        )
    selected_source_refs_digest = _digest_json(selected_refs)
    if safe.get("full_selected_source_result_refs_digest") != (
        selected_source_refs_digest
    ):
        raise SearchResultCandidatePacketError(
            "ordinary packet selected-source digest mismatch"
        )
    _required_sha256(
        safe.get("selected_candidate_inputs_digest"),
        "ordinary packet requires selected candidate-input digest",
    )
    if len(selected_refs) > identity_set_ref["source_result_identity_count"]:
        raise SearchResultCandidatePacketError(
            "ordinary packet selected-source count exceeds identity set"
        )
    seen_source_ids: set[str] = set()
    seen_selected_ranks: set[int] = set()
    for index, record in enumerate(records, start=1):
        _validate_ordinary_candidate_record(
            record,
            run_id=run_id,
            request_id=request_id,
            answer_contract_ref=contract_ref,
            search_executor_handoff_ref=handoff_ref,
            expected_source_result_ref=selected_refs[index - 1],
        )
        source_id = _safe_mapping(record.get("source_result_ref")).get(
            "source_result_id"
        )
        selected_rank = _positive_int(
            record.get("selected_candidate_rank"),
            "ordinary record requires selected candidate rank",
        )
        if source_id in seen_source_ids:
            raise SearchResultCandidatePacketError(
                "ordinary candidate packet contains duplicate source-result refs"
            )
        if selected_rank in seen_selected_ranks:
            raise SearchResultCandidatePacketError(
                "ordinary candidate packet contains duplicate selected ranks"
            )
        if selected_rank != index:
            raise SearchResultCandidatePacketError(
                "ordinary candidate packet selected ranks must be contiguous"
            )
        seen_source_ids.add(str(source_id))
        seen_selected_ranks.add(selected_rank)
    ordered_candidate_record_digests_digest = (
        _ordinary_ordered_candidate_record_digests_digest(records)
    )
    if safe.get("ordered_candidate_record_digests_digest") != (
        ordered_candidate_record_digests_digest
    ):
        raise SearchResultCandidatePacketError(
            "ordinary packet ordered candidate-record digest mismatch"
        )
    declared_digest = _required_token(
        safe.get("packet_digest"),
        "ordinary candidate packet requires packet_digest",
        limit=128,
    )
    if declared_digest != (
        ordinary_search_result_candidate_packet_binding_digest(safe)
    ):
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet digest mismatch"
        )
    expected_packet_id = (
        "search-result-candidate-packet:"
        f"{_clean_token(request_id, limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_packet_id:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet id mismatch"
        )
    return safe


def validate_search_result_candidate_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and return a sanitized candidate packet."""

    raw = _required_mapping(packet, "search result candidate packet")
    if raw.get("schema_version") == (
        ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION
    ):
        return validate_ordinary_search_result_candidate_packet(raw)
    _reject_forbidden_surface_claims(raw, context="search result candidate packet")
    safe = _safe_mapping(raw)
    if safe.get("schema_version") != SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION:
        raise SearchResultCandidatePacketError("candidate packet schema mismatch")
    if safe.get("packet_kind") != SEARCH_RESULT_CANDIDATE_PACKET_KIND:
        raise SearchResultCandidatePacketError("candidate packet kind mismatch")
    if safe.get("owner") != SEARCH_RESULT_CANDIDATE_PACKET_OWNER:
        raise SearchResultCandidatePacketError("candidate packet owner mismatch")
    if safe.get("packet_posture") != SEARCH_RESULT_CANDIDATE_PACKET_POSTURE:
        raise SearchResultCandidatePacketError("candidate packet posture mismatch")
    _validate_closed_flags(safe, context="candidate packet")
    _validate_posture_flags(safe, context="candidate packet")
    run_id = _required_token(safe.get("run_id"), "packet requires run_id")
    request_id = _required_token(safe.get("request_id"), "packet requires request_id")
    contract_ref = _contract_ref_or_error(safe.get("current_answer_contract_ref"))
    handoff_ref = _handoff_ref_or_error(safe.get("search_executor_handoff_ref"))
    if safe.get("current_answer_contract_digest") != contract_ref["contract_digest"]:
        raise SearchResultCandidatePacketError(
            "candidate packet current_answer_contract digest mismatch"
        )
    if safe.get("search_executor_handoff_digest") != handoff_ref["handoff_digest"]:
        raise SearchResultCandidatePacketError(
            "candidate packet SearchExecutorHandoff digest mismatch"
        )
    handoff_parent = _safe_mapping(handoff_ref.get("parent_current_contract_ref"))
    if handoff_parent and handoff_parent != contract_ref:
        raise SearchResultCandidatePacketError(
            "candidate packet handoff is not bound to current_answer_contract"
        )
    records = _safe_list(safe.get("candidate_records"))
    if safe.get("candidate_count") != len(records):
        raise SearchResultCandidatePacketError(
            "candidate packet candidate_count mismatch"
        )
    selected_ids = set(_ordered_unique(safe.get("selected_search_task_ids")))
    for record in records:
        _validate_candidate_record(
            record,
            run_id=run_id,
            request_id=request_id,
            current_answer_contract_ref=contract_ref,
            search_executor_handoff_ref=handoff_ref,
            selected_search_task_ids=selected_ids,
        )
    declared_digest = _required_token(
        safe.get("packet_digest"),
        "candidate packet requires packet_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_packet_digest_payload(safe)):
        raise SearchResultCandidatePacketError("candidate packet digest mismatch")
    expected_packet_id = (
        "search-result-candidate-packet:"
        f"{_clean_token(request_id, limit=120)}:"
        f"{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_packet_id:
        raise SearchResultCandidatePacketError("candidate packet id mismatch")
    return safe


def search_result_candidate_packet_ref_from_packet(
    packet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the compact downstream reference for a candidate packet."""

    safe = _safe_mapping(packet)
    packet_id = _clean_token(safe.get("packet_id"), limit=260)
    packet_digest = _clean_token(safe.get("packet_digest"), limit=128)
    if not packet_id or not packet_digest:
        return {}
    full_handoff_ref = _safe_mapping(safe.get("search_executor_handoff_ref"))
    compact_handoff_ref = _without_empty(
        {
            "handoff_id": full_handoff_ref.get("handoff_id"),
            "handoff_digest": full_handoff_ref.get("handoff_digest"),
            "schema_version": full_handoff_ref.get("schema_version"),
            "origin_kind": full_handoff_ref.get("origin_kind"),
            "handoff_revision": full_handoff_ref.get("handoff_revision"),
        }
    )
    return _without_empty({
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "schema_version": _clean_token(safe.get("schema_version")),
        "run_id": _clean_token(safe.get("run_id"), limit=260),
        "request_id": _clean_token(safe.get("request_id"), limit=260),
        "candidate_count": _bounded_int(safe.get("candidate_count")),
        "origin_kind": _clean_token(safe.get("origin_kind")),
        "packet_revision": _bounded_int(safe.get("packet_revision")),
        "full_selected_source_result_refs_digest": _clean_token(
            safe.get("full_selected_source_result_refs_digest"),
            limit=128,
        ),
        "selected_candidate_inputs_digest": _clean_token(
            safe.get("selected_candidate_inputs_digest"),
            limit=128,
        ),
        "ordered_candidate_record_digests_digest": _clean_token(
            safe.get("ordered_candidate_record_digests_digest"),
            limit=128,
        ),
        "source_result_identity_set_ref": _safe_mapping(
            safe.get("source_result_identity_set_ref")
        ),
        "search_executor_handoff_ref": compact_handoff_ref,
    })


def _build_packet_from_source(
    *,
    source: Mapping[str, Any],
    current_ref: Any,
    handoff_ref: Any,
    candidates: Any,
    selected_search_task_ids: Any,
    provider_authorized: Any,
    provider_used: Any,
    parent_validation_ref: Mapping[str, Any],
) -> dict[str, Any]:
    source_map = _safe_mapping(source)
    candidate_list = _safe_list(candidates)
    claimed_count = source_map.get("candidate_count")
    if claimed_count is not None and _bounded_int(claimed_count) != len(candidate_list):
        raise SearchResultCandidatePacketError(
            "candidate packet source candidate_count mismatch"
        )
    contract_ref = _contract_ref_or_error(current_ref)
    executor_handoff_ref = _handoff_ref_or_error(handoff_ref)
    selected_ids = _ordered_unique(
        selected_search_task_ids
        or [candidate.get("search_task_id") for candidate in candidate_list]
    )
    records = [
        build_search_result_candidate_record_from_live_candidate(
            candidate,
            current_answer_contract_ref=contract_ref,
            search_executor_handoff_ref=executor_handoff_ref,
            parent_live_search_validation_ref=parent_validation_ref,
            run_id=source_map.get("run_id"),
            request_id=source_map.get("request_id"),
            provider_authorized=provider_authorized,
            provider_used=provider_used,
        )
        for candidate in candidate_list
    ]
    return SearchResultCandidatePacket(
        run_id=_required_token(source_map.get("run_id"), "packet requires run_id"),
        request_id=_required_token(
            source_map.get("request_id"),
            "packet requires request_id",
        ),
        current_answer_contract_ref=contract_ref,
        search_executor_handoff_ref=executor_handoff_ref,
        parent_live_search_validation_ref=parent_validation_ref,
        selected_search_task_ids=selected_ids,
        provider_authorized=provider_authorized,
        provider_used=provider_used,
        candidate_records=records,
    ).to_dict()


def _validate_candidate_record(
    record: Mapping[str, Any],
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    current_answer_contract_ref: Mapping[str, Any] | None = None,
    search_executor_handoff_ref: Mapping[str, Any] | None = None,
    selected_search_task_ids: set[str] | None = None,
) -> None:
    safe = _safe_mapping(record)
    if safe.get("schema_version") != SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION:
        raise SearchResultCandidatePacketError("candidate record schema mismatch")
    if safe.get("record_kind") != SEARCH_RESULT_CANDIDATE_RECORD_KIND:
        raise SearchResultCandidatePacketError("candidate record kind mismatch")
    if safe.get("record_posture") != SEARCH_RESULT_CANDIDATE_PACKET_POSTURE:
        raise SearchResultCandidatePacketError("candidate record posture mismatch")
    _validate_closed_flags(safe, context="candidate record")
    _validate_posture_flags(safe, context="candidate record")
    for key in _REQUIRED_RECORD_KEYS:
        if safe.get(key) in (None, ""):
            raise SearchResultCandidatePacketError(
                f"candidate record requires {key}"
            )
    record_run_id = _required_token(safe.get("run_id"), "record requires run_id")
    record_request_id = _required_token(
        safe.get("request_id"),
        "record requires request_id",
    )
    if run_id is not None and record_run_id != run_id:
        raise SearchResultCandidatePacketError("candidate record run_id mismatch")
    if request_id is not None and record_request_id != request_id:
        raise SearchResultCandidatePacketError(
            "candidate record request_id mismatch"
        )
    contract_ref = _contract_ref_or_error(safe.get("current_answer_contract_ref"))
    handoff_ref = _handoff_ref_or_error(safe.get("search_executor_handoff_ref"))
    if current_answer_contract_ref is not None and contract_ref != _safe_mapping(
        current_answer_contract_ref
    ):
        raise SearchResultCandidatePacketError(
            "candidate record current_answer_contract ref mismatch"
        )
    if search_executor_handoff_ref is not None and handoff_ref != _safe_mapping(
        search_executor_handoff_ref
    ):
        raise SearchResultCandidatePacketError(
            "candidate record SearchExecutorHandoff ref mismatch"
        )
    if safe.get("current_answer_contract_digest") != contract_ref["contract_digest"]:
        raise SearchResultCandidatePacketError(
            "candidate record current_answer_contract digest mismatch"
        )
    if safe.get("search_executor_handoff_digest") != handoff_ref["handoff_digest"]:
        raise SearchResultCandidatePacketError(
            "candidate record SearchExecutorHandoff digest mismatch"
        )
    task_id = _required_token(
        safe.get("search_task_id"),
        "candidate record requires search_task_id",
        limit=260,
    )
    if selected_search_task_ids is not None and task_id not in selected_search_task_ids:
        raise SearchResultCandidatePacketError(
            "candidate record task is not selected"
        )
    _positive_int(
        safe.get("provider_call_index"),
        "record requires provider_call_index",
    )
    _positive_int(safe.get("result_rank"), "record requires result_rank")
    _required_url(safe.get("url"))
    if not _clean_domain(safe.get("domain")):
        raise SearchResultCandidatePacketError("candidate record requires domain")
    declared_digest = _required_token(
        safe.get("record_digest"),
        "candidate record requires record_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_record_digest_payload(safe)):
        raise SearchResultCandidatePacketError("candidate record digest mismatch")


def _validate_ordinary_candidate_record(
    record: Mapping[str, Any],
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    answer_contract_ref: Mapping[str, Any] | None = None,
    search_executor_handoff_ref: Mapping[str, Any] | None = None,
    expected_source_result_ref: Mapping[str, Any] | None = None,
) -> None:
    safe = _safe_mapping(record)
    if safe.get("schema_version") != ORDINARY_SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION:
        raise SearchResultCandidatePacketError("ordinary candidate record schema mismatch")
    if safe.get("record_kind") != SEARCH_RESULT_CANDIDATE_RECORD_KIND:
        raise SearchResultCandidatePacketError("ordinary candidate record kind mismatch")
    if safe.get("origin_kind") != SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER:
        raise SearchResultCandidatePacketError("ordinary candidate record origin mismatch")
    _validate_closed_flags(safe, context="ordinary candidate record")
    _validate_posture_flags(safe, context="ordinary candidate record")
    _validate_ordinary_closed_runtime_fields(safe, context="ordinary candidate record")
    record_run_id = _required_token(safe.get("run_id"), "ordinary record requires run_id")
    record_request_id = _required_token(safe.get("request_id"), "ordinary record requires request_id")
    if run_id is not None and record_run_id != run_id:
        raise SearchResultCandidatePacketError("ordinary candidate record run_id mismatch")
    if request_id is not None and record_request_id != request_id:
        raise SearchResultCandidatePacketError("ordinary candidate record request_id mismatch")
    contract_ref = _optional_contract_ref(safe.get("answer_contract_ref"))
    if answer_contract_ref is not None and contract_ref != _safe_mapping(answer_contract_ref):
        raise SearchResultCandidatePacketError("ordinary candidate record contract ref mismatch")
    handoff_ref = _ordinary_handoff_ref_or_error(safe.get("search_executor_handoff_ref"))
    if search_executor_handoff_ref is not None and handoff_ref != _safe_mapping(search_executor_handoff_ref):
        raise SearchResultCandidatePacketError("ordinary candidate record handoff ref mismatch")
    if safe.get("search_executor_handoff_digest") != handoff_ref["handoff_digest"]:
        raise SearchResultCandidatePacketError("ordinary candidate record handoff digest mismatch")
    source_ref = _ordinary_source_result_ref_or_error(safe.get("source_result_ref"))
    if expected_source_result_ref is not None and source_ref != _safe_mapping(expected_source_result_ref):
        raise SearchResultCandidatePacketError("ordinary candidate source-result ref mismatch")
    _ordinary_source_material_ref_or_error(safe.get("source_material_ref"))
    _required_token(safe.get("provider_used"), "ordinary candidate requires provider")
    _required_token(safe.get("provider_authorized"), "ordinary candidate requires authorized provider")
    _positive_int(safe.get("provider_call_ordinal"), "ordinary candidate requires provider call ordinal")
    _positive_int(safe.get("provider_result_rank"), "ordinary candidate requires provider result rank")
    selected_rank = _positive_int(safe.get("selected_candidate_rank"), "ordinary candidate requires selected rank")
    _required_url(safe.get("normalized_url"))
    if safe.get("title") not in (None, ""):
        _clean_text(safe.get("title"), limit=220)
    _ordinary_score_or_error(safe.get("relevance_score"))
    if not _safe_mapping(safe.get("scoring_provenance")):
        raise SearchResultCandidatePacketError("ordinary candidate requires scoring provenance")
    refs = [_ordinary_source_result_ref_or_error(item) for item in _safe_list(safe.get("contributing_source_result_refs"))]
    if len(refs) > ORDINARY_SEARCH_RESULT_CANDIDATE_MAX_CONTRIBUTOR_REFS:
        raise SearchResultCandidatePacketError("ordinary candidate contributor cap exceeded")
    if safe.get("contributor_ref_count") != len(refs):
        raise SearchResultCandidatePacketError("ordinary candidate contributor count mismatch")
    overflow_count = _bounded_int(safe.get("contributor_overflow_count"))
    overflow_digest = _clean_token(safe.get("contributor_overflow_digest"), limit=128)
    if (overflow_count > 0) != bool(overflow_digest):
        raise SearchResultCandidatePacketError("ordinary candidate overflow count/digest mismatch")
    expected_candidate_id = f"search-result-candidate:ordinary:{source_ref['source_result_id']}:{selected_rank}"
    if safe.get("candidate_id") != expected_candidate_id:
        raise SearchResultCandidatePacketError("ordinary candidate id mismatch")
    candidate_core = _without_empty({
        "source_result_ref": source_ref,
        "source_material_ref": _safe_mapping(safe.get("source_material_ref")),
        "selected_candidate_rank": selected_rank,
        "search_executor_handoff_ref": handoff_ref,
    })
    if safe.get("candidate_digest") != _digest_json(candidate_core):
        raise SearchResultCandidatePacketError("ordinary candidate digest mismatch")
    if safe.get("record_digest") != _digest_json(_record_digest_payload(safe)):
        raise SearchResultCandidatePacketError("ordinary candidate record digest mismatch")


def _ordinary_handoff_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("origin_kind") != SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER:
        raise SearchResultCandidatePacketError("ordinary packet requires ordinary-origin handoff ref")
    handoff_id = _required_token(ref.get("handoff_id"), "ordinary packet requires handoff id", limit=260)
    handoff_digest = _required_token(ref.get("handoff_digest"), "ordinary packet requires handoff digest", limit=128)
    query_plan_ref = _ordinary_named_digest_ref(ref.get("query_plan_ref"), "query_plan_id", "query_plan_digest", "QueryPlan")
    provider_plan_ref = _ordinary_named_digest_ref(ref.get("provider_plan_ref"), "provider_plan_id", "provider_plan_digest", "ProviderPlan")
    identity_set_ref = _ordinary_identity_set_ref_or_error(ref.get("source_result_identity_set_ref"))
    selected_refs = [_ordinary_source_result_ref_or_error(item) for item in _safe_list(ref.get("selected_source_result_refs"))]
    if not selected_refs or len(selected_refs) > ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_MAX_CANDIDATES:
        raise SearchResultCandidatePacketError("ordinary handoff ref requires bounded selected source refs")
    retrieval_refs = _safe_list(ref.get("retrieval_action_refs"))
    if not retrieval_refs or any(
        not _clean_token(_safe_mapping(item).get("action_id"))
        or not _clean_token(
            _safe_mapping(item).get("retrieval_action_digest"),
            limit=128,
        )
        for item in retrieval_refs
    ):
        raise SearchResultCandidatePacketError("ordinary handoff ref requires retrieval action refs")
    return _without_empty({
        "handoff_id": handoff_id,
        "handoff_digest": handoff_digest,
        "schema_version": _clean_token(ref.get("schema_version")),
        "origin_kind": SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER,
        "handoff_revision": _bounded_int(ref.get("handoff_revision")),
        "dedupe_key": _clean_token(ref.get("dedupe_key"), limit=128),
        "answer_contract_ref": _optional_contract_ref(ref.get("answer_contract_ref")),
        "query_plan_ref": query_plan_ref,
        "selected_query_plan_item_refs": _safe_list(ref.get("selected_query_plan_item_refs")),
        "provider_plan_ref": provider_plan_ref,
        "provider_plan_record_refs": _safe_list(ref.get("provider_plan_record_refs")),
        "provider_route_refs": _safe_list(ref.get("provider_route_refs")),
        "retrieval_action_refs": retrieval_refs,
        "source_result_identity_set_ref": identity_set_ref,
        "selected_source_result_refs": selected_refs,
        "selected_source_result_count": len(selected_refs),
    })


def _ordinary_named_digest_ref(value: Any, id_key: str, digest_key: str, label: str) -> dict[str, Any]:
    ref = _safe_mapping(value)
    ref_id = _required_token(ref.get(id_key), f"ordinary packet requires {label} ref id", limit=260)
    digest = _required_token(ref.get(digest_key), f"ordinary packet requires {label} ref digest", limit=128)
    return _without_empty({id_key: ref_id, digest_key: digest, "schema_version": _clean_token(ref.get("schema_version")), "revision": ref.get("revision")})


def _ordinary_identity_set_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    identity_set_id = _required_token(ref.get("source_result_identity_set_id") or ref.get("identity_set_id"), "ordinary packet requires identity-set id", limit=260)
    digest = _required_token(ref.get("source_result_identity_set_digest") or ref.get("identity_set_digest"), "ordinary packet requires identity-set digest", limit=128)
    count = _bounded_int(ref.get("source_result_identity_count") if ref.get("source_result_identity_count") is not None else ref.get("identity_count", ref.get("count")))
    if count < 1 or count > 128:
        raise SearchResultCandidatePacketError("ordinary packet identity-set count must be between 1 and 128")
    return _without_empty({"source_result_identity_set_id": identity_set_id, "source_result_identity_set_digest": digest, "source_result_identity_count": count, "schema_version": _clean_token(ref.get("schema_version"))})


def _ordinary_source_result_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    source_id = _required_token(ref.get("source_result_id") or ref.get("identity_id"), "ordinary candidate requires source-result id", limit=320)
    digest = _required_token(ref.get("source_result_digest") or ref.get("identity_digest"), "ordinary candidate requires source-result digest", limit=128)
    return _without_empty({"source_result_id": source_id, "source_result_digest": digest, "schema_version": _clean_token(ref.get("schema_version")), "revision": ref.get("revision")})


def _ordinary_source_material_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    material_id = _required_token(ref.get("source_material_id") or ref.get("material_id"), "ordinary candidate requires source-material id", limit=320)
    digest = _required_token(ref.get("source_material_digest") or ref.get("material_digest"), "ordinary candidate requires source-material digest", limit=128)
    return _without_empty({"source_material_id": material_id, "source_material_digest": digest, "material_class": _clean_token(ref.get("material_class"), limit=120), "schema_version": _clean_token(ref.get("schema_version"))})


def _optional_contract_ref(value: Any) -> dict[str, Any]:
    return _contract_ref_or_error(value) if _safe_mapping(value) else {}


def _ordinary_score_or_error(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise SearchResultCandidatePacketError("ordinary candidate requires relevance score") from exc
    if not isfinite(score):
        raise SearchResultCandidatePacketError("ordinary candidate relevance score must be finite")
    return score


def _ordinary_scoring_provenance_or_error(candidate: Mapping[str, Any]) -> dict[str, Any]:
    provenance = _safe_mapping(candidate.get("scoring_provenance") or candidate.get("ranking_provenance") or candidate.get("scoring_provenance_ref"))
    if not provenance:
        provenance = _without_empty({key: candidate.get(key) for key in ("relevance_score", "ranking_score", "semantic_score", "rrf_score", "cross_encoder_score", "ranking_method")})
    _reject_forbidden_surface_claims(provenance, context="ordinary candidate scoring provenance")
    if not provenance or len(json.dumps(provenance, sort_keys=True)) > 4096:
        raise SearchResultCandidatePacketError("ordinary candidate requires bounded scoring provenance")
    return provenance


def _ordinary_contributor_refs(candidate: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int, str | None]:
    raw_refs = _safe_list(candidate.get("contributing_source_result_refs") or candidate.get("contributor_refs"))
    normalized = [_ordinary_source_result_ref_or_error(item) for item in raw_refs]
    kept = normalized[:ORDINARY_SEARCH_RESULT_CANDIDATE_MAX_CONTRIBUTOR_REFS]
    omitted = normalized[ORDINARY_SEARCH_RESULT_CANDIDATE_MAX_CONTRIBUTOR_REFS:]
    declared_count = _bounded_int(candidate.get("contributor_overflow_count"))
    declared_digest = _clean_token(
        candidate.get("contributor_overflow_digest")
        or candidate.get("full_contributor_digest"),
        limit=128,
    )
    if omitted:
        if declared_count not in (0, len(omitted)) or (declared_digest and declared_digest != _digest_json(omitted)):
            raise SearchResultCandidatePacketError("ordinary candidate contributor overflow metadata mismatch")
        return kept, len(omitted), _digest_json(omitted)
    if declared_count > 0 and not declared_digest:
        raise SearchResultCandidatePacketError("ordinary candidate overflow digest required")
    return kept, declared_count, declared_digest if declared_count > 0 else None


def _ordinary_closed_runtime_fields() -> dict[str, Any]:
    return {"acquisition_need_proposal_created": False, "exact_url_transport_executed": False, "exact_url_cap_charged": False, "urls_fetched": 0}


def _validate_ordinary_closed_runtime_fields(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _ordinary_closed_runtime_fields().items():
        if value.get(key) != expected:
            raise SearchResultCandidatePacketError(f"{context} must keep {key} at {expected!r}")


def _validate_live_candidate_digest(candidate: Mapping[str, Any]) -> None:
    declared_digest = _required_token(
        candidate.get("candidate_digest"),
        "search result candidate requires candidate_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_live_candidate_digest_payload(candidate)):
        raise SearchResultCandidatePacketError(
            "search result candidate digest mismatch"
        )


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise SearchResultCandidatePacketError(f"{context} must keep {key} false")
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if key in flags and flags.get(key) is not expected:
            raise SearchResultCandidatePacketError(
                f"{context} closed surface flag {key} must be false"
            )


def _validate_posture_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _POSTURE_TRUE_FLAGS.items():
        if value.get(key) is not expected:
            raise SearchResultCandidatePacketError(f"{context} must keep {key} true")


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise SearchResultCandidatePacketError(
            f"{context} contains raw/private fields: "
            + ", ".join(raw_or_private)
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise SearchResultCandidatePacketError(
            f"{context} includes closed authority fields: " + ", ".join(authority)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchResultCandidatePacketError(
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


def _live_search_validation_ref_from_state(value: Any) -> dict[str, Any]:
    state = _safe_mapping(value)
    validation_id = _clean_token(state.get("validation_id"), limit=260)
    validation_digest = _clean_token(state.get("validation_digest"), limit=128)
    if not validation_id:
        return {}
    return _without_empty(
        {
            "validation_id": validation_id,
            "validation_digest": validation_digest,
            "schema_version": _clean_token(state.get("schema_version")),
            "dedupe_key": _clean_token(state.get("dedupe_key"), limit=128),
            "provider_used": _clean_token(state.get("provider_used")),
            "candidate_count": _bounded_int(state.get("candidate_count")),
        }
    )


def _live_search_validation_ref_from_candidates(value: Any) -> dict[str, Any]:
    candidates = _safe_list(value)
    validation_ids = _ordered_unique(
        candidate.get("validation_id")
        for candidate in candidates
        if isinstance(candidate, Mapping)
    )
    if len(validation_ids) != 1:
        return {}
    return {
        "validation_id": validation_ids[0],
        "candidate_count": len(candidates),
    }


def _contract_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    version = _clean_token(
        ref.get("contract_version")
        or ref.get("accepted_contract_version")
        or ref.get("current_contract_version")
    )
    digest = _clean_token(
        ref.get("contract_digest")
        or ref.get("accepted_contract_digest")
        or ref.get("current_contract_digest"),
        limit=128,
    )
    if not version or not digest:
        raise SearchResultCandidatePacketError(
            "candidate packet requires current_answer_contract ref/digest"
        )
    return {
        "source": _clean_token(ref.get("source")) or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _handoff_ref_or_error(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    handoff_id = _clean_token(ref.get("handoff_id"), limit=260)
    handoff_digest = _clean_token(ref.get("handoff_digest"), limit=128)
    if not handoff_id or not handoff_digest:
        raise SearchResultCandidatePacketError(
            "candidate packet requires SearchExecutorHandoff ref/digest"
        )
    return _without_empty(
        {
            "handoff_id": handoff_id,
            "handoff_digest": handoff_digest,
            "schema_version": _clean_token(ref.get("schema_version")),
            "dedupe_key": _clean_token(ref.get("dedupe_key"), limit=128),
            "contract_parent_kind": _clean_token(ref.get("contract_parent_kind")),
            "parent_current_contract_ref": _safe_mapping(
                ref.get("parent_current_contract_ref")
            ),
            "parent_initial_contract_ref": _safe_mapping(
                ref.get("parent_initial_contract_ref")
            ),
        }
    )


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchResultCandidatePacketError(f"{label} must be a mapping")
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
        return _clean_token(value, limit=900)
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
        raise SearchResultCandidatePacketError(message)
    return text


def _required_url(value: Any) -> str:
    url = _required_token(value, "record requires url", limit=700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SearchResultCandidatePacketError("record requires http(s) url")
    return url


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise SearchResultCandidatePacketError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


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


def _domain_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    return parsed.netloc.lower() or None


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
        text = _clean_token(item, limit=260)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _first_token(records: Sequence[Mapping[str, Any]], key: str) -> str | None:
    for record in records:
        token = _clean_token(_safe_mapping(record).get(key))
        if token:
            return token
    return None


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _live_candidate_digest_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(candidate)
    payload.pop("candidate_digest", None)
    return payload


def _record_digest_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(record)
    payload.pop("record_digest", None)
    return payload


def _packet_digest_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(packet)
    payload.pop("packet_id", None)
    payload.pop("packet_digest", None)
    return payload


def ordinary_candidate_inputs_digest(
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    """Digest the exact bounded selected inputs authorized for packet build."""

    if isinstance(candidates, str | bytes) or not isinstance(
        candidates, Sequence
    ):
        raise SearchResultCandidatePacketError(
            "ordinary candidate inputs must be a sequence"
        )
    values = list(candidates)
    if not values or any(not isinstance(item, Mapping) for item in values):
        raise SearchResultCandidatePacketError(
            "ordinary candidate inputs must contain mappings"
        )
    return _digest_json(values)


def _ordinary_compact_handoff_binding_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    return _without_empty(
        {
            "handoff_id": ref.get("handoff_id"),
            "handoff_digest": ref.get("handoff_digest"),
            "schema_version": ref.get("schema_version"),
            "origin_kind": ref.get("origin_kind"),
            "handoff_revision": ref.get("handoff_revision"),
        }
    )


def _ordinary_packet_binding_basis(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(value)
    selected_refs = _safe_list(safe.get("selected_source_result_refs"))
    if selected_refs:
        selected_refs_digest = _digest_json(selected_refs)
        if safe.get("full_selected_source_result_refs_digest") not in (
            None,
            selected_refs_digest,
        ):
            raise SearchResultCandidatePacketError(
                "ordinary packet selected-source binding digest mismatch"
            )
    else:
        selected_refs_digest = _required_sha256(
            safe.get("full_selected_source_result_refs_digest"),
            "ordinary packet requires selected-source binding digest",
        )
    candidate_inputs_digest = _required_sha256(
        safe.get("selected_candidate_inputs_digest"),
        "ordinary packet requires selected candidate-input digest",
    )
    records = _safe_list(safe.get("candidate_records"))
    if records:
        ordered_record_digests_digest = (
            _ordinary_ordered_candidate_record_digests_digest(records)
        )
        if safe.get("ordered_candidate_record_digests_digest") not in (
            None,
            ordered_record_digests_digest,
        ):
            raise SearchResultCandidatePacketError(
                "ordinary packet ordered candidate-record binding digest mismatch"
            )
    else:
        ordered_record_digests_digest = _required_sha256(
            safe.get("ordered_candidate_record_digests_digest"),
            "ordinary packet requires ordered candidate-record binding digest",
        )
    candidate_count = _positive_int(
        safe.get("candidate_count"),
        "ordinary packet requires candidate_count",
    )
    return {
        "schema_version": safe.get("schema_version"),
        "origin_kind": safe.get("origin_kind"),
        "packet_revision": safe.get("packet_revision"),
        "run_id": safe.get("run_id"),
        "request_id": safe.get("request_id"),
        "search_executor_handoff_ref": (
            _ordinary_compact_handoff_binding_ref(
                safe.get("search_executor_handoff_ref")
            )
        ),
        "source_result_identity_set_ref": _safe_mapping(
            safe.get("source_result_identity_set_ref")
        ),
        "candidate_count": candidate_count,
        "full_selected_source_result_refs_digest": selected_refs_digest,
        "selected_candidate_inputs_digest": candidate_inputs_digest,
        "ordered_candidate_record_digests_digest": (
            ordered_record_digests_digest
        ),
    }


def _ordinary_ordered_candidate_record_digests_digest(
    records: Sequence[Mapping[str, Any]],
) -> str:
    """Bind ordered bounded records without retaining their text in RunKernel."""

    record_digests = [
        _required_sha256(
            _safe_mapping(record).get("record_digest"),
            "ordinary packet candidate record requires record_digest",
        )
        for record in records
    ]
    if not record_digests:
        raise SearchResultCandidatePacketError(
            "ordinary packet requires ordered candidate record digests"
        )
    return _digest_json(record_digests)


def ordinary_search_result_candidate_packet_binding_digest(
    value: Mapping[str, Any],
) -> str:
    """Return the text-free packet identity digest RunKernel can rederive."""

    return _digest_json(_ordinary_packet_binding_basis(value))


def validate_ordinary_search_result_candidate_packet_binding(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a full or compact packet ref against its bounded bindings."""

    safe = _safe_mapping(value)
    declared_digest = _required_sha256(
        safe.get("packet_digest"),
        "ordinary packet requires packet_digest",
    )
    expected_digest = ordinary_search_result_candidate_packet_binding_digest(
        safe
    )
    if declared_digest != expected_digest:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet binding digest mismatch"
        )
    request_id = _required_token(
        safe.get("request_id"),
        "ordinary packet requires request_id",
    )
    expected_id = (
        "search-result-candidate-packet:"
        f"{_clean_token(request_id, limit=120)}:{declared_digest[:16]}"
    )
    if safe.get("packet_id") != expected_id:
        raise SearchResultCandidatePacketError(
            "ordinary candidate packet binding id mismatch"
        )
    return safe


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _required_sha256(value: Any, message: str) -> str:
    digest = _required_token(value, message, limit=128).casefold()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise SearchResultCandidatePacketError(message)
    return digest


__all__ = [
    "ORDINARY_SEARCH_RESULT_CANDIDATE_MAX_CONTRIBUTOR_REFS",
    "ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_MAX_CANDIDATES",
    "ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_REVISION",
    "ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION",
    "ORDINARY_SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION",
    "ORDINARY_SEARCH_RESULT_CANDIDATE_SNIPPET_MAX_CHARS",
    "SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER",
    "SEARCH_RESULT_CANDIDATE_PACKET_KIND",
    "SEARCH_RESULT_CANDIDATE_PACKET_OWNER",
    "SEARCH_RESULT_CANDIDATE_PACKET_POSTURE",
    "SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION",
    "SEARCH_RESULT_CANDIDATE_PACKET_TRACE_KEY",
    "SEARCH_RESULT_CANDIDATE_RECORD_KIND",
    "SEARCH_RESULT_CANDIDATE_RECORD_SCHEMA_VERSION",
    "SearchResultCandidatePacket",
    "SearchResultCandidatePacketError",
    "SearchResultCandidateRecord",
    "build_search_result_candidate_packet_from_live_search_validation_output",
    "build_search_result_candidate_packet_from_live_validation_state",
    "build_search_result_candidate_packet_from_ordinary_discovery",
    "build_search_result_candidate_record_from_live_candidate",
    "build_search_result_candidate_record_from_ordinary_candidate",
    "reduce_live_search_validation_candidates_to_packet",
    "ordinary_candidate_inputs_digest",
    "ordinary_search_result_candidate_packet_binding_digest",
    "search_result_candidate_packet_ref_from_packet",
    "validate_search_result_candidate_packet",
    "validate_ordinary_search_result_candidate_packet",
    "validate_ordinary_search_result_candidate_packet_binding",
]
