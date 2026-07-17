"""Default-off ordinary run_pipeline source-custody integration.

This helper consumes the in-memory ``SearchResultCandidatePacket`` produced by
the ordinary candidate handoff repair, requests typed ``READ`` routing,
dispatches one selected adapter, builds the existing fetch/read content packet,
and reduces candidate/content custody through the existing EvidenceLedger
reducer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.acquisition_adapters import AcquisitionTransports, dispatch_acquisition
from core.acquisition_contracts import AcquisitionArtifact, AcquisitionRequest
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (
    BoundedTextSelection,
    FetchReadContentReferenceError,
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    select_bounded_answer_bearing_text,
    validate_fetch_read_content_packet,
)
from core.routing import (
    AcquisitionCapability,
    ProviderCapabilityRequest,
    route_provider_capability,
)
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.search_result_candidate_packet import (
    SearchResultCandidatePacketError,
    validate_search_result_candidate_packet,
)

ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY = "ordinary_live_source_custody"
ORDINARY_LIVE_SOURCE_CUSTODY_PHASE = (
    "AG-ORDINARY-LIVE-SOURCE-CUSTODY-INTEGRATION-01"
)
ORDINARY_LIVE_SOURCE_CUSTODY_MODE = "REPAIR"

_CHILD_OWNER = "ordinary_live_candidate_handoff_run_kernel"
_CHILD_LIFETIME = "in_memory_for_single_run_pipeline_invocation"
_CHILD_STATE_OWNED = (
    "SearchPlanner/current_answer_contract/SearchExecutorHandoff",
    "live_search_validation_state",
    "SearchResultCandidatePacket lineage",
    "FetchReadContentPacket/SanitizedContentReference custody lineage",
    "EvidenceLedger candidate/content custody for the selected candidate",
)
_CHILD_STATE_NOT_OWNED = (
    "ordinary answer semantic slots",
    "SemanticObservation",
    "ComponentCoverage",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "citation eligibility/rendering",
    "source-obligation satisfaction",
    "answer text",
)
_MAIN_KERNEL_LIMITATION = (
    "The main answer RunKernel still owns ordinary answer flow; this bounded "
    "child keeps acquisition/source-custody state from occupying answer "
    "semantic slots until the ordinary semantic/coverage integration phase."
)
_FUTURE_CONSOLIDATION = (
    "Temporary architecture debt: consolidate into the main ordinary RunKernel "
    "after AG-ORDINARY-LIVE-SEMANTIC-COVERAGE-INTEGRATION-01 wires semantic "
    "support and ComponentCoverage into the ordinary path."
)

_DIAGNOSTIC_AUTHORITY_KEYS = frozenset(
    {
        "ordinary_retrieval_results",
        "provider_diagnostic",
        "provider_diagnostics",
        "retrieval_diagnostic",
        "retrieval_diagnostics",
        "retrieval_result",
        "retrieval_results",
        "search_diagnostic",
        "search_diagnostics",
        "top_passage",
        "top_passages",
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
        "page_content",
        "page_text",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_cookies",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_response_headers",
        "raw_search_response",
        "raw_text",
        "raw_trace",
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
_CLOSED_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "analyst_report",
        "answer",
        "answer_material",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "citation",
        "citation_record",
        "citation_records",
        "citation_source",
        "citation_sources",
        "citations",
        "component_coverage",
        "component_satisfaction",
        "coverage",
        "evidence_relative_support",
        "fap",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "semantic_support",
        "source_obligation_claim",
        "source_obligation_satisfaction",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "admitted_to_evidence_ledger",
        "admitted_source",
        "analyst_report_created",
        "answer_ready",
        "author_input_created",
        "citation_created",
        "citation_eligible",
        "citation_rendered",
        "component_coverage_created",
        "component_satisfaction_created",
        "content_citation_eligible",
        "evidence_admitted",
        "final_answer_packet_created",
        "final_answer_ready",
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

_CLOSED_FALSE_FLAGS = {
    "raw_html_retained": False,
    "raw_headers_retained": False,
    "raw_response_headers_retained": False,
    "raw_cookies_retained": False,
    "raw_page_text_retained": False,
    "raw_page_content_retained": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "semantic_observation_created": False,
    "component_coverage_created": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

_NON_PROOFS = (
    "no live provider/search/broker/fetch/model call",
    "no retrieval diagnostics promoted into source authority",
    "no semantic support or SemanticObservation admission",
    "no ComponentCoverage reduction",
    "no citation eligibility or citation rendering",
    "no source-obligation satisfaction",
    "no SufficiencyReadiness or FinalAnswerPacket proof",
    "no Author or AuthorProse behavior",
    "no answer text or product correctness claim",
)


class OrdinaryLiveSourceCustodyError(ValueError):
    """Raised internally when ordinary source custody must fail closed."""

    def __init__(self, first_failed_seam: str, message: str) -> None:
        super().__init__(message)
        self.first_failed_seam = first_failed_seam


@dataclass(frozen=True, slots=True)
class OrdinaryLiveSourceCustodyResult:
    projection: dict[str, Any]
    fetch_read_content_packet: dict[str, Any] | None = None
    sanitized_content_reference: dict[str, Any] | None = None
    evidence_ledger_projection: dict[str, Any] | None = None


def ordinary_live_source_custody_disabled_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
        "phase": ORDINARY_LIVE_SOURCE_CUSTODY_PHASE,
        "mode": ORDINARY_LIVE_SOURCE_CUSTODY_MODE,
        "enabled": False,
        "ran": False,
        "failed_closed": False,
        "status": "disabled",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
    }


def execute_ordinary_live_source_custody(
    *,
    run_kernel: RunKernel | None,
    parent_run_id: str,
    parent_request_id: str,
    candidate_packet: Mapping[str, Any] | None,
    fetch_read: Callable[..., Mapping[str, Any]] | None,
    available_providers: Mapping[str, object] | None = None,
    acquisition_transports: AcquisitionTransports | None = None,
    required_or_preferred_anchors: Sequence[Any] = (),
    component_text: str | None = None,
    claim_under_test: str | None = None,
) -> OrdinaryLiveSourceCustodyResult:
    """Route and reduce one selected candidate into existing fetch/read custody."""

    base = _base_projection(
        parent_run_id=parent_run_id,
        parent_request_id=parent_request_id,
    )
    fetch_read_attempted = 0
    fetch_read_completed = 0
    try:
        if candidate_packet is None:
            raise OrdinaryLiveSourceCustodyError(
                "search_result_candidate_packet_missing",
                "ordinary source custody requires SearchResultCandidatePacket",
            )
        _reject_diagnostic_authority_keys(
            candidate_packet,
            context="SearchResultCandidatePacket",
        )
        packet = validate_search_result_candidate_packet(candidate_packet)
        if run_kernel is None:
            raise OrdinaryLiveSourceCustodyError(
                "ordinary_candidate_handoff_run_kernel_missing",
                "ordinary source custody requires the in-memory candidate RunKernel",
            )
        selected_candidate = _selected_candidate_from_packet(packet)
        transports = _source_custody_transports(
            selected_candidate=selected_candidate,
            fetch_read=fetch_read,
            acquisition_transports=acquisition_transports,
        )
        availability = _read_availability(
            available_providers=available_providers,
            fetch_read=fetch_read,
            transports=transports,
        )
        route_decision = route_provider_capability(
            ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
            availability,
        )
        request = AcquisitionRequest(
            acquisition_job_id=(
                f"{packet['run_id']}:read:{selected_candidate['candidate_id']}"
            ),
            parent_acquisition_job_id=str(packet.get("packet_id") or ""),
            route_decision=route_decision,
            selected_urls=(str(selected_candidate["url"]),),
            max_retained_characters=20_000,
            candidate_reference=str(selected_candidate["candidate_id"]),
        )
        execution = dispatch_acquisition(request, transports=transports)
        fetch_read_attempted = execution.provider_calls_attempted
        fetch_read_completed = execution.provider_calls_completed
        if not execution.succeeded or len(execution.artifacts) != 1:
            raise OrdinaryLiveSourceCustodyError(
                _read_failure_seam(execution.failure_code or execution.block_code),
                execution.detail or "typed READ acquisition failed closed",
            )
        artifact = execution.artifacts[0]
        raw_fetch_read = _read_artifact_for_existing_custody(artifact)
        material, bounded_selection = _sanitized_material_from_fetch_read(
            raw_fetch_read,
            selected_candidate=selected_candidate,
            required_or_preferred_anchors=required_or_preferred_anchors,
            component_text=component_text,
            claim_under_test=claim_under_test,
        )
        fetch_read_packet = validate_fetch_read_content_packet(
            build_fetch_read_content_packet_from_candidate_packet(
                packet,
                [material],
                selected_candidate_ids=[str(selected_candidate["candidate_id"])],
            )
        )
        reference = dict(fetch_read_packet["reference_records"][0])
        ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
            run_kernel=run_kernel,
            fetch_read_content_packet=fetch_read_packet,
            observation_id=(
                f"{packet['run_id']}:evidence-ledger:"
                "ordinary-live-source-custody-integration-01"
            ),
        )
        ledger_summary = _ledger_summary(ledger_projection)
        projection = _without_empty(
            {
                **base,
                "ran": True,
                "failed_closed": False,
                "status": "source_custody_reduced",
                "first_failed_seam": None,
                "source_candidate": _source_candidate_projection(selected_candidate),
                "source_selected_from_search_result_candidate_packet": True,
                "source_authority_source": "SearchResultCandidatePacket",
                "read_route_decision": route_decision.to_trace(),
                "read_acquisition_job": execution.to_trace(),
                "read_selected_provider": route_decision.selected_provider,
                "read_selected_operation": route_decision.operation,
                "read_selected_variant": route_decision.variant,
                "retrieval_diagnostics_used_as_source_authority": False,
                "fetch_read_attempted_count": fetch_read_attempted,
                "fetch_read_completed_count": fetch_read_completed,
                "raw_html_retained": False,
                "raw_headers_retained": False,
                "raw_response_headers_retained": False,
                "raw_cookies_retained": False,
                "raw_page_text_retained": False,
                "raw_page_content_retained": False,
                "bounded_content_char_count": (
                    bounded_selection.bounded_text_char_count
                ),
                "bounded_content_digest": bounded_selection.bounded_text_digest,
                "bounded_content_selector_metadata": (
                    bounded_selection.to_metadata()
                ),
                "fetch_read_content_packet_ref": (
                    fetch_read_content_packet_ref_from_packet(fetch_read_packet)
                ),
                "sanitized_content_reference_ref": (
                    _content_reference_ref(reference)
                ),
                "evidence_ledger_custody_ref": ledger_summary.get("ref"),
                "evidence_ledger_custody_projection_summary": ledger_summary,
                "evidence_ledger_custody_count": ledger_summary.get(
                    "custody_record_count",
                    0,
                ),
                **_closed_surface_counts(),
                **_zero_call_counts(),
                **_child_kernel_projection(run_kernel=run_kernel),
                "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
                **_CLOSED_FALSE_FLAGS,
                "explicit_non_proofs": list(_NON_PROOFS),
            }
        )
        return OrdinaryLiveSourceCustodyResult(
            projection=projection,
            fetch_read_content_packet=fetch_read_packet,
            sanitized_content_reference=reference,
            evidence_ledger_projection=ledger_projection,
        )
    except OrdinaryLiveSourceCustodyError as exc:
        return OrdinaryLiveSourceCustodyResult(
            projection=_fail_projection(
                base,
                exc.first_failed_seam,
                str(exc),
                fetch_read_attempted=fetch_read_attempted,
                fetch_read_completed=fetch_read_completed,
                run_kernel=run_kernel,
            )
        )
    except (FetchReadContentReferenceError, SearchResultCandidatePacketError) as exc:
        return OrdinaryLiveSourceCustodyResult(
            projection=_fail_projection(
                base,
                "fetch_read_content_packet_rejected",
                str(exc),
                fetch_read_attempted=fetch_read_attempted,
                fetch_read_completed=fetch_read_completed,
                run_kernel=run_kernel,
            )
        )
    except RunKernelTransitionError as exc:
        return OrdinaryLiveSourceCustodyResult(
            projection=_fail_projection(
                base,
                "evidence_ledger_reducer_rejected_custody",
                str(exc),
                fetch_read_attempted=fetch_read_attempted,
                fetch_read_completed=fetch_read_completed,
                run_kernel=run_kernel,
            )
        )
    except Exception as exc:
        return OrdinaryLiveSourceCustodyResult(
            projection=_fail_projection(
                base,
                "ordinary_live_source_custody_exception",
                str(exc),
                fetch_read_attempted=fetch_read_attempted,
                fetch_read_completed=fetch_read_completed,
                run_kernel=run_kernel,
            )
        )


def _source_custody_transports(
    *,
    selected_candidate: Mapping[str, Any],
    fetch_read: Callable[..., Mapping[str, Any]] | None,
    acquisition_transports: AcquisitionTransports | None,
) -> AcquisitionTransports | None:
    if acquisition_transports is None and fetch_read is None:
        return None
    configured = acquisition_transports or AcquisitionTransports()
    linkup_fetch = configured.linkup_fetch
    if linkup_fetch is None and fetch_read is not None:

        def legacy_linkup_fetch(payload: dict[str, Any]) -> Mapping[str, Any]:
            source_url = str(payload.get("url") or selected_candidate["url"])
            raw = fetch_read(
                candidate=dict(selected_candidate),
                source_url=source_url,
                source_candidate_ref=_source_candidate_ref(selected_candidate),
            )
            material = dict(raw) if isinstance(raw, Mapping) else {}
            material.setdefault(
                "markdown",
                material.get("sanitized_text") or material.get("readable_text"),
            )
            return material

        linkup_fetch = legacy_linkup_fetch
    return AcquisitionTransports(
        linkup_fetch=linkup_fetch,
        tavily_extract=configured.tavily_extract,
        tavily_map=configured.tavily_map,
        tavily_crawl=configured.tavily_crawl,
        linkup_deep_search=configured.linkup_deep_search,
    )


def _read_availability(
    *,
    available_providers: Mapping[str, object] | None,
    fetch_read: Callable[..., Mapping[str, Any]] | None,
    transports: AcquisitionTransports | None,
) -> dict[str, bool]:
    if available_providers is not None:
        return {
            "linkup": bool(available_providers.get("linkup")),
            "tavily": bool(available_providers.get("tavily")),
        }
    return {
        "linkup": bool(fetch_read or (transports and transports.linkup_fetch)),
        "tavily": bool(transports and transports.tavily_extract),
    }


def _read_failure_seam(code: str | None) -> str:
    mapping = {
        "provider_response_closed_fields_rejected": "offline_fetch_read_result_invalid",
        "read_material_empty_or_unreadable": "offline_fetch_read_result_unreadable",
        "read_http_status_unreadable": "offline_fetch_read_result_unreadable",
        "read_provider_reported_failure": "offline_fetch_read_result_unreadable",
        "read_result_cardinality_invalid": "offline_fetch_read_result_unreadable",
        "read_requested_url_mismatch": "offline_fetch_read_result_invalid",
        "read_attempted_url_mismatch": "offline_fetch_read_result_invalid",
        "selected_adapter_transport_unavailable": "offline_fetch_read_dependency_missing",
    }
    return mapping.get(code or "", "typed_read_dispatch_failed")


def _read_artifact_for_existing_custody(
    artifact: AcquisitionArtifact,
) -> dict[str, Any]:
    return _without_empty(
        {
            "fetch_read_status": "readable",
            "attempted_url": artifact.attempted_url,
            "resolved_url": artifact.resolved_url,
            "final_url": artifact.final_url,
            "canonical_url": artifact.canonical_url,
            "resolved_domain": (
                str(artifact.final_url or "").split("/", 3)[2]
                if str(artifact.final_url or "").startswith(("http://", "https://"))
                else None
            ),
            "http_status": artifact.http_status or 200,
            "content_type": artifact.content_type,
            "retrieved_or_observed_at": artifact.observed_at,
            "content_title": artifact.title,
            "content_length": artifact.retained_character_count,
            "sanitized_text": artifact.retained_text,
            "acquisition_job_id": artifact.acquisition_job_id,
            "acquisition_provider": artifact.provider,
            "acquisition_operation": artifact.operation,
            "acquisition_variant": artifact.provider_variant,
        }
    )


def _selected_candidate_from_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    records = _safe_list(packet.get("candidate_records"))
    if not records:
        raise OrdinaryLiveSourceCustodyError(
            "search_result_candidate_packet_empty",
            "ordinary source custody requires at least one candidate record",
        )
    ordered = sorted(
        (_safe_mapping(record) for record in records),
        key=lambda record: _bounded_int(record.get("result_rank")) or 10**9,
    )
    selected = ordered[0]
    if not selected.get("candidate_id") or not selected.get("url"):
        raise OrdinaryLiveSourceCustodyError(
            "search_result_candidate_record_invalid",
            "ordinary source custody selected candidate is missing identity or URL",
        )
    return selected


def _sanitized_material_from_fetch_read(
    raw_fetch_read: Mapping[str, Any],
    *,
    selected_candidate: Mapping[str, Any],
    required_or_preferred_anchors: Sequence[Any],
    component_text: str | None,
    claim_under_test: str | None,
) -> tuple[dict[str, Any], BoundedTextSelection]:
    raw = _safe_mapping(raw_fetch_read)
    if not raw:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_missing",
            "ordinary source custody fetch/read dependency returned no material",
        )
    _reject_fetch_read_closed_surface_keys(raw)
    status = _fetch_read_status(raw)
    sanitized_text = _clean_text(
        raw.get("sanitized_text") or raw.get("readable_text"),
        limit=100_000,
    )
    if status == "readable" and not sanitized_text:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_unreadable",
            "ordinary source custody requires sanitized readable text",
        )
    selection = select_bounded_answer_bearing_text(
        sanitized_text or "",
        required_or_preferred_anchors=required_or_preferred_anchors,
        component_text=component_text,
        claim_under_test=claim_under_test,
    )
    candidate_url = str(selected_candidate["url"])
    candidate_domain = str(selected_candidate.get("domain") or "")
    material = _without_empty(
        {
            "candidate_id": selected_candidate.get("candidate_id"),
            "candidate_digest": selected_candidate.get("candidate_digest"),
            "fetch_read_status": status,
            "attempted_url": _clean_url(raw.get("attempted_url")) or candidate_url,
            "resolved_url": _clean_url(raw.get("resolved_url")) or candidate_url,
            "final_url": _clean_url(raw.get("final_url")) or candidate_url,
            "canonical_url": _clean_url(raw.get("canonical_url")) or candidate_url,
            "resolved_domain": (
                _clean_text(raw.get("resolved_domain"), limit=260)
                or candidate_domain
            ),
            "http_status": _bounded_int(
                raw.get("http_status") or raw.get("status_code")
            ),
            "content_type": _clean_text(raw.get("content_type"), limit=160),
            "retrieved_or_observed_at": _clean_text(
                raw.get("retrieved_or_observed_at"),
                limit=80,
            ),
            "published_or_observed_date": _clean_text(
                raw.get("published_or_observed_date"),
                limit=80,
            ),
            "content_title": _clean_text(
                raw.get("content_title") or raw.get("title"),
                limit=300,
            ),
            "content_length": (
                _bounded_int(raw.get("content_length"))
                or len(sanitized_text or "")
            ),
            "read_error_code": _clean_text(raw.get("read_error_code"), limit=120),
            "failure_reason": _clean_text(raw.get("failure_reason"), limit=500),
            "redirect_chain_digest": _clean_text(
                raw.get("redirect_chain_digest"),
                limit=128,
            ),
            "redirect_count": _bounded_int(raw.get("redirect_count")),
            "bounded_text": selection.bounded_text,
            "bounded_text_sanitized": True,
            "bounded_text_bounded": True,
            "bounded_character_count": selection.bounded_text_char_count,
            "excerpt_digest": selection.bounded_text_digest,
            "bounded_text_selection": selection.to_metadata(),
        }
    )
    return material, selection


def _fetch_read_status(raw: Mapping[str, Any]) -> str:
    status = str(raw.get("fetch_read_status") or raw.get("status") or "").casefold()
    status = status.strip()
    if status not in {"readable", "unreadable", "failed", "skipped", "blocked"}:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_status_invalid",
            "ordinary source custody fetch/read result has invalid status",
        )
    return status


def _reject_diagnostic_authority_keys(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    diagnostic_keys = sorted(keys & _DIAGNOSTIC_AUTHORITY_KEYS)
    if diagnostic_keys:
        raise OrdinaryLiveSourceCustodyError(
            "diagnostic_source_authority_rejected",
            f"{context} includes diagnostic-shaped source authority fields: "
            + ", ".join(diagnostic_keys),
        )


def _reject_fetch_read_closed_surface_keys(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(
        keys
        & (_DIAGNOSTIC_AUTHORITY_KEYS | _RAW_OR_PRIVATE_KEYS | _CLOSED_AUTHORITY_KEYS)
    )
    if forbidden:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_invalid",
            "ordinary source custody fetch/read result opens closed fields: "
            + ", ".join(forbidden),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_invalid",
            "ordinary source custody fetch/read result opens closed claims: "
            + ", ".join(dangerous),
        )


def _source_candidate_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "candidate_id": candidate.get("candidate_id"),
            "candidate_digest": candidate.get("candidate_digest"),
            "record_digest": candidate.get("record_digest"),
            "rank": candidate.get("result_rank"),
            "title": candidate.get("title"),
            "domain": candidate.get("domain"),
            "url": candidate.get("url"),
        }
    )


def _source_candidate_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return _source_candidate_ref(candidate)


def _content_reference_ref(reference: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(reference)
    selection = _safe_mapping(safe.get("bounded_text_selection"))
    return _without_empty(
        {
            "reference_id": safe.get("reference_id"),
            "reference_digest": safe.get("reference_digest"),
            "candidate_id": safe.get("candidate_id"),
            "candidate_digest": safe.get("candidate_digest"),
            "fetch_read_status": safe.get("fetch_read_status"),
            "bounded_text_char_count": safe.get("bounded_character_count"),
            "bounded_text_digest": safe.get("excerpt_digest"),
            "bounded_text_selection": selection,
        }
    )


def _ledger_summary(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    if not projection:
        return {
            "ref": {},
            "custody_record_count": 0,
            "readable_record_count": 0,
            "candidate_content_custody_visible": False,
        }
    ledger = _safe_mapping(projection)
    custody = _safe_mapping(ledger.get("fetch_read_candidate_custody"))
    records = _safe_list(custody.get("fetch_read_candidate_custody_records"))
    first = _safe_mapping(records[0]) if records else {}
    ref = _without_empty(
        {
            "ledger_owner": ledger.get("owner"),
            "ledger_schema_version": ledger.get("schema_version"),
            "trace_key": custody.get("trace_key"),
            "custody_record_id": first.get("reference_id"),
            "custody_record_digest": first.get("reference_digest"),
            "fetch_read_content_packet_id": first.get(
                "fetch_read_content_packet_id"
            ),
            "fetch_read_content_packet_digest": first.get(
                "fetch_read_content_packet_digest"
            ),
        }
    )
    return {
        "ref": ref,
        "schema_version": custody.get("schema_version"),
        "owner": custody.get("owner"),
        "candidate_content_custody_visible": custody.get(
            "candidate_content_custody_visible",
            False,
        ),
        "custody_record_count": custody.get("custody_record_count", 0),
        "readable_record_count": custody.get("readable_record_count", 0),
        "unreadable_record_count": custody.get("unreadable_record_count", 0),
        "candidate_content_custody_is_semantic_support": custody.get(
            "candidate_content_custody_is_semantic_support",
            False,
        ),
        "citation_eligible": custody.get("citation_eligible", False),
        "source_obligation_satisfied": custody.get(
            "source_obligation_satisfied",
            False,
        ),
        "component_coverage_created": custody.get(
            "component_coverage_created",
            False,
        ),
        "sufficiency_decided": custody.get("sufficiency_decided", False),
        "final_answer_packet_created": custody.get(
            "final_answer_packet_created",
            False,
        ),
        "author_input_created": custody.get("author_input_created", False),
        "bounded_content_payload_retained": _safe_mapping(
            custody.get("behavior_boundary_flags")
        ).get("bounded_content_payload_retained", False),
    }


def _base_projection(*, parent_run_id: str, parent_request_id: str) -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY,
        "phase": ORDINARY_LIVE_SOURCE_CUSTODY_PHASE,
        "mode": ORDINARY_LIVE_SOURCE_CUSTODY_MODE,
        "repair_verdict_target": "YES",
        "enabled": True,
        "ran": False,
        "failed_closed": False,
        "first_failed_seam": None,
        "status": "not_run",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "product_path_affected": "ordinary run_pipeline",
        "default_disabled": True,
        "parent_run_id": parent_run_id,
        "parent_request_id": parent_request_id,
        "source_selected_from_search_result_candidate_packet": False,
        "retrieval_diagnostics_used_as_source_authority": False,
        "projection_to_runkernel_rehydration": False,
        "product_code_imports_scripts_ag": False,
        **_zero_call_counts(),
    }


def _fail_projection(
    base: Mapping[str, Any],
    first_failed_seam: str,
    reason: str,
    *,
    fetch_read_attempted: int,
    fetch_read_completed: int,
    run_kernel: RunKernel | None,
) -> dict[str, Any]:
    return {
        **dict(base),
        "ran": False,
        "failed_closed": True,
        "status": "failed_closed",
        "first_failed_seam": first_failed_seam,
        "failure_reason": _clean_text(reason, limit=400),
        "source_authority_source": "none",
        "fetch_read_attempted_count": fetch_read_attempted,
        "fetch_read_completed_count": fetch_read_completed,
        "fetch_read_content_packet_ref": {},
        "sanitized_content_reference_ref": {},
        "evidence_ledger_custody_ref": {},
        "evidence_ledger_custody_count": 0,
        **_closed_surface_counts(),
        **_zero_call_counts(),
        **_child_kernel_projection(run_kernel=run_kernel),
        "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        **_CLOSED_FALSE_FLAGS,
        "explicit_non_proofs": list(_NON_PROOFS),
    }


def _child_kernel_projection(*, run_kernel: RunKernel | None) -> dict[str, Any]:
    if run_kernel is None:
        return {
            "child_kernel_used": False,
            "child_kernel_owner": _CHILD_OWNER,
            "child_kernel_lifetime": _CHILD_LIFETIME,
            "child_kernel_state_owned": list(_CHILD_STATE_OWNED),
            "child_kernel_state_not_owned": list(_CHILD_STATE_NOT_OWNED),
            "child_kernel_main_kernel_limitation": _MAIN_KERNEL_LIMITATION,
            "child_kernel_temporary_architecture_debt": True,
            "child_kernel_future_consolidation_path": _FUTURE_CONSOLIDATION,
        }
    return {
        "child_kernel_used": True,
        "child_kernel_owner": _CHILD_OWNER,
        "child_kernel_lifetime": _CHILD_LIFETIME,
        "child_kernel_parent_lineage": {
            "parent_run_id": str(run_kernel.state.request.get("parent_run_id") or ""),
            "parent_request_id": str(
                run_kernel.state.request.get("parent_request_id") or ""
            ),
            "child_run_id": run_kernel.state.run_id,
            "child_request_id": run_kernel.state.request_id,
        },
        "child_kernel_state_owned": list(_CHILD_STATE_OWNED),
        "child_kernel_state_not_owned": list(_CHILD_STATE_NOT_OWNED),
        "child_kernel_main_kernel_limitation": _MAIN_KERNEL_LIMITATION,
        "child_kernel_temporary_architecture_debt": True,
        "child_kernel_future_consolidation_path": _FUTURE_CONSOLIDATION,
    }


def _zero_call_counts() -> dict[str, int]:
    return {
        "provider_search_calls": 0,
        "search_calls": 0,
        "broker_calls": 0,
        "model_calls": 0,
        "retrieval_calls": 0,
    }


def _closed_surface_counts() -> dict[str, int]:
    return {
        "semantic_observation_admissions": 0,
        "component_coverage_reductions": 0,
        "citation_eligibility_decisions": 0,
        "citation_rendering_decisions": 0,
        "source_obligation_satisfaction_decisions": 0,
        "sufficiency_readiness_reductions": 0,
        "final_answer_packet_creations": 0,
        "author_authorprose_invocations": 0,
    }


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_url(value: Any) -> str | None:
    text = _clean_text(value, limit=1_000)
    if not text or not text.startswith(("http://", "https://")):
        return None
    return text


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


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


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


__all__ = [
    "ORDINARY_LIVE_SOURCE_CUSTODY_MODE",
    "ORDINARY_LIVE_SOURCE_CUSTODY_PHASE",
    "ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY",
    "OrdinaryLiveSourceCustodyResult",
    "execute_ordinary_live_source_custody",
    "ordinary_live_source_custody_disabled_projection",
]
