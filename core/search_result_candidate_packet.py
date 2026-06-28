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


def validate_search_result_candidate_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and return a sanitized candidate packet."""

    raw = _required_mapping(packet, "search result candidate packet")
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
    return {
        "packet_id": packet_id,
        "packet_digest": packet_digest,
        "schema_version": _clean_token(safe.get("schema_version")),
        "candidate_count": _bounded_int(safe.get("candidate_count")),
    }


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


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
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
    "build_search_result_candidate_record_from_live_candidate",
    "reduce_live_search_validation_candidates_to_packet",
    "search_result_candidate_packet_ref_from_packet",
    "validate_search_result_candidate_packet",
]
