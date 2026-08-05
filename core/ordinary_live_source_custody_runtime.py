"""Default-off ordinary run_pipeline source-custody integration.

This helper consumes an independently produced ``AcquisitionNeedProposalV1``
only when one is explicitly supplied. A selected candidate or candidate URL is
provenance, not a material need. Without a proposal the helper returns a normal
``not_needed`` result before any RunKernel acquisition action or transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from core.acquisition_adapters import AcquisitionTransports
from core.acquisition_contracts import AcquisitionArtifact
from core.acquisition_control import (
    AcquisitionCapabilityDecisionObservationV1,
    AcquisitionControlError,
    AcquisitionNeedProposalV1,
    AcquisitionRouteObservationV1,
    AcquisitionTerminalReceiptV1,
    AcquisitionWorkOrderV1,
    validate_selected_candidate_material_need_proposal,
)
from core.authorized_acquisition_runtime import (
    execute_acquisition_capability_decision_action,
    execute_acquisition_custody_authorization_action,
    execute_acquisition_route_action,
    execute_acquisition_terminal_reduction_action,
    execute_acquisition_work_order_admission_action,
    execute_authorized_acquisition_work_order,
)
from core.cap_enforcement import (
    AttemptReservation,
    ExternalCallFamily,
    RunCapExceeded,
    RunCapPolicy,
)
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
from core.run_kernel import RunKernel, RunKernelTransitionError
from core.search_result_candidate_packet import (
    SearchResultCandidatePacketError,
    validate_search_result_candidate_packet,
)

ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY = "ordinary_live_source_custody"
ORDINARY_LIVE_SOURCE_CUSTODY_PHASE = "AG-ORDINARY-LIVE-SOURCE-CUSTODY-INTEGRATION-01"
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
    acquisition_need_proposal: AcquisitionNeedProposalV1 | None = None,
    available_providers: Mapping[str, object] | None = None,
    acquisition_transports: AcquisitionTransports | None = None,
    cap_policy: RunCapPolicy | None = None,
    before_transport: Callable[..., AttemptReservation | None] | None = None,
    required_or_preferred_anchors: Sequence[Any] = (),
    component_text: str | None = None,
    claim_under_test: str | None = None,
) -> OrdinaryLiveSourceCustodyResult:
    """Consume an explicit need or leave selected-candidate provenance inert."""

    base = _base_projection(
        parent_run_id=parent_run_id,
        parent_request_id=parent_request_id,
    )
    fetch_read_attempted = 0
    fetch_read_completed = 0
    try:
        if acquisition_need_proposal is None:
            return OrdinaryLiveSourceCustodyResult(
                projection=_not_needed_projection(
                    base,
                    candidate_packet_present=candidate_packet is not None,
                    run_kernel=run_kernel,
                )
            )
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
        availability = _read_availability(
            available_providers=available_providers,
        )
        authority_snapshot = run_kernel.acquisition_authority_snapshot()
        proposal = validate_selected_candidate_material_need_proposal(
            proposal=acquisition_need_proposal,
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            candidate_packet=packet,
            selected_candidate=selected_candidate,
            authority_snapshot=authority_snapshot,
        )
        capability_action = run_kernel.authorize_acquisition_capability_decision(proposal=proposal)
        capability_result = execute_acquisition_capability_decision_action(
            capability_action,
            proposal=proposal,
            authority_snapshot=authority_snapshot,
            acquisition_control_state=(run_kernel.state.acquisition_control_state),
        )
        run_kernel.reduce(capability_result.observation)
        decision = capability_result.decision
        if decision.decision_status != "accepted":
            _reduce_blocked_acquisition_decision(
                run_kernel=run_kernel,
                proposal=proposal,
                decision=decision,
            )
            raise OrdinaryLiveSourceCustodyError(
                decision.block_code or "acquisition_capability_blocked",
                "RunKernel blocked the post-discovery acquisition capability",
            )

        work_order_action = run_kernel.authorize_acquisition_work_order_admission(
            capability_decision_ref=decision.ref()
        )
        work_order_result = execute_acquisition_work_order_admission_action(
            work_order_action,
            proposal=proposal,
            decision=decision,
            acquisition_control_state=(run_kernel.state.acquisition_control_state),
        )
        run_kernel.reduce(work_order_result.observation)
        work_order = work_order_result.work_order

        route_action = run_kernel.authorize_acquisition_route(
            work_order_ref=work_order.ref(),
            provider_availability=availability,
        )
        route_result = execute_acquisition_route_action(
            route_action,
            work_order=work_order,
            available_providers=availability,
            acquisition_control_state=(run_kernel.state.acquisition_control_state),
        )
        run_kernel.reduce(route_result.observation)
        route_decision = route_result.route_decision
        route_observation = route_result.route_observation
        if route_observation.terminal_status != "selected":
            _reduce_blocked_acquisition_route(
                run_kernel=run_kernel,
                work_order=work_order,
                route_observation=route_observation,
            )
            raise OrdinaryLiveSourceCustodyError(
                route_observation.block_code or "acquisition_route_blocked",
                "core.routing returned a blocked acquisition route",
            )

        execution_action = run_kernel.authorize_acquisition_execution(
            work_order_ref=work_order.ref(),
            route_observation_ref=route_observation.ref(),
        )
        if cap_policy is not None and cap_policy.bounded and before_transport is None:
            raise RunCapExceeded(
                "unaccounted_read_transport",
                family=ExternalCallFamily.READ,
            )
        execution_result = execute_authorized_acquisition_work_order(
            execution_action,
            run_kernel=run_kernel,
            work_order=work_order,
            route_observation=route_observation,
            route_decision=route_decision,
            transports=acquisition_transports,
            before_transport=(
                before_transport
                if before_transport is not None
                else cap_policy.mark_fetch_read_operation
                if cap_policy is not None
                else None
            ),
        )
        run_kernel.reduce(execution_result.observation)
        execution_observation = execution_result.execution_observation
        execution = execution_result.execution_result
        fetch_read_attempted = execution.provider_calls_attempted
        fetch_read_completed = execution.provider_calls_completed

        terminal_action = run_kernel.authorize_acquisition_terminal_reduction(
            execution_observation_ref=execution_observation.ref()
        )
        terminal_result = execute_acquisition_terminal_reduction_action(
            terminal_action,
            acquisition_control_state=(run_kernel.state.acquisition_control_state),
            work_order=work_order,
            route_observation=route_observation,
            execution_observation=execution_observation,
        )
        run_kernel.reduce(terminal_result.observation)
        terminal_receipt = terminal_result.terminal_receipt
        execution_result.raise_deferred_error()
        if not execution.succeeded or len(execution.artifacts) != 1:
            raise OrdinaryLiveSourceCustodyError(
                _read_failure_seam(execution.failure_code or execution.block_code),
                execution.detail or "typed READ acquisition failed closed",
            )
        custody_action = run_kernel.authorize_acquisition_custody_consumption(
            terminal_receipt_ref=terminal_receipt.ref()
        )
        custody_result = execute_acquisition_custody_authorization_action(
            custody_action,
            work_order=work_order,
            route_observation=route_observation,
            terminal_receipt=terminal_receipt,
            custody_consumer="core.ordinary_live_source_custody_runtime",
            acquisition_control_state=(run_kernel.state.acquisition_control_state),
        )
        run_kernel.reduce(custody_result.observation)
        custody_authorization = custody_result.custody_authorization
        artifact = execution.artifacts[0]
        raw_fetch_read = _read_artifact_for_existing_custody(artifact)
        material, bounded_selection = _sanitized_material_from_fetch_read(
            raw_fetch_read,
            selected_candidate=selected_candidate,
            required_or_preferred_anchors=required_or_preferred_anchors,
            component_text=component_text,
            claim_under_test=claim_under_test,
        )
        run_kernel.require_current_acquisition_custody_authorization(custody_authorization.ref())
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
            observation_id=(f"{packet['run_id']}:evidence-ledger:ordinary-live-source-custody-integration-01"),
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
                "acquisition_need_proposal_ref": proposal.ref(),
                "acquisition_capability_decision_ref": decision.ref(),
                "acquisition_work_order_ref": work_order.ref(),
                "acquisition_route_observation_ref": route_observation.ref(),
                "acquisition_execution_observation_ref": (execution_observation.ref()),
                "acquisition_terminal_receipt_ref": terminal_receipt.ref(),
                "acquisition_custody_authorization_ref": (custody_authorization.ref()),
                "acquisition_control_owner": "RunKernel",
                "acquisition_provider_selection_owner": "core.routing",
                "acquisition_mechanical_adapter_owner": ("core.acquisition_adapters"),
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
                "bounded_content_char_count": (bounded_selection.bounded_text_char_count),
                "bounded_content_digest": bounded_selection.bounded_text_digest,
                "bounded_content_selector_metadata": (bounded_selection.to_metadata()),
                "fetch_read_content_packet_ref": (fetch_read_content_packet_ref_from_packet(fetch_read_packet)),
                "sanitized_content_reference_ref": (_content_reference_ref(reference)),
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
    except AcquisitionControlError as exc:
        return OrdinaryLiveSourceCustodyResult(
            projection=_fail_projection(
                base,
                exc.code,
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
    except RunCapExceeded:
        raise
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


def _reduce_blocked_acquisition_decision(
    *,
    run_kernel: RunKernel,
    proposal: AcquisitionNeedProposalV1,
    decision: AcquisitionCapabilityDecisionObservationV1,
) -> AcquisitionTerminalReceiptV1 | None:
    if decision.block_code not in {
        "focused_extract_requester_not_installed",
        "map_candidate_reentry_not_installed",
        "crawl_page_custody_not_installed",
        "premium_sequential_acquisition_not_licensed",
    }:
        return None
    action = run_kernel.authorize_acquisition_terminal_reduction(capability_decision_ref=decision.ref())
    result = execute_acquisition_terminal_reduction_action(
        action,
        acquisition_control_state=run_kernel.state.acquisition_control_state,
        proposal=proposal,
        decision=decision,
    )
    run_kernel.reduce(result.observation)
    return result.terminal_receipt


def _reduce_blocked_acquisition_route(
    *,
    run_kernel: RunKernel,
    work_order: AcquisitionWorkOrderV1,
    route_observation: AcquisitionRouteObservationV1,
) -> AcquisitionTerminalReceiptV1:
    action = run_kernel.authorize_acquisition_terminal_reduction(route_observation_ref=route_observation.ref())
    result = execute_acquisition_terminal_reduction_action(
        action,
        acquisition_control_state=run_kernel.state.acquisition_control_state,
        work_order=work_order,
        route_observation=route_observation,
    )
    run_kernel.reduce(result.observation)
    return result.terminal_receipt


def _read_availability(
    *,
    available_providers: Mapping[str, object] | None,
) -> dict[str, bool]:
    return {
        "linkup": bool((available_providers or {}).get("linkup")),
        "tavily": bool((available_providers or {}).get("tavily")),
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
        "read_provider_reported_url_mismatch": "offline_fetch_read_result_invalid",
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
            "provider_reported_url": artifact.provider_reported_url,
            "resolved_url": artifact.resolved_url,
            "final_url": artifact.final_url,
            "canonical_url": artifact.canonical_url,
            "resolved_domain": (
                str(artifact.final_url or "").split("/", 3)[2]
                if str(artifact.final_url or "").startswith(("http://", "https://"))
                else None
            ),
            "http_status": artifact.http_status,
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
    material = _without_empty(
        {
            "candidate_id": selected_candidate.get("candidate_id"),
            "candidate_digest": selected_candidate.get("candidate_digest"),
            "fetch_read_status": status,
            "attempted_url": _clean_url(raw.get("attempted_url")) or candidate_url,
            "provider_reported_url": _clean_url(raw.get("provider_reported_url")),
            "resolved_url": _clean_url(raw.get("resolved_url")),
            "final_url": _clean_url(raw.get("final_url")),
            "canonical_url": _clean_url(raw.get("canonical_url")),
            "resolved_domain": _clean_text(
                raw.get("resolved_domain"),
                limit=260,
            ),
            "http_status": _optional_http_status(raw),
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
            "content_length": (_bounded_int(raw.get("content_length")) or len(sanitized_text or "")),
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
            f"{context} includes diagnostic-shaped source authority fields: " + ", ".join(diagnostic_keys),
        )


def _reject_fetch_read_closed_surface_keys(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & (_DIAGNOSTIC_AUTHORITY_KEYS | _RAW_OR_PRIVATE_KEYS | _CLOSED_AUTHORITY_KEYS))
    if forbidden:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_invalid",
            "ordinary source custody fetch/read result opens closed fields: " + ", ".join(forbidden),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise OrdinaryLiveSourceCustodyError(
            "offline_fetch_read_result_invalid",
            "ordinary source custody fetch/read result opens closed claims: " + ", ".join(dangerous),
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
            "fetch_read_content_packet_id": first.get("fetch_read_content_packet_id"),
            "fetch_read_content_packet_digest": first.get("fetch_read_content_packet_digest"),
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
        "bounded_content_payload_retained": _safe_mapping(custody.get("behavior_boundary_flags")).get(
            "bounded_content_payload_retained", False
        ),
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


def _not_needed_projection(
    base: Mapping[str, Any],
    *,
    candidate_packet_present: bool,
    run_kernel: RunKernel | None,
) -> dict[str, Any]:
    return {
        **dict(base),
        "evaluated": True,
        "ran": False,
        "failed_closed": False,
        "status": "not_needed",
        "operation_started": False,
        "candidate_packet_present": candidate_packet_present,
        "candidate_selection_creates_material_need": False,
        "acquisition_need_proposal_created": False,
        "acquisition_work_order_created": False,
        "acquisition_route_created": False,
        "exact_url_cap_charged": False,
        "exact_url_transport_attempted": False,
        "fetch_read_attempted_count": 0,
        "fetch_read_completed_count": 0,
        "evidence_ledger_custody_count": 0,
        **_closed_surface_counts(),
        **_zero_call_counts(),
        **_child_kernel_projection(run_kernel=run_kernel),
        "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
        **_CLOSED_FALSE_FLAGS,
        "explicit_non_proofs": list(_NON_PROOFS),
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
            "parent_request_id": str(run_kernel.state.request.get("parent_request_id") or ""),
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


def _optional_http_status(value: Mapping[str, Any]) -> int | None:
    raw = value.get("http_status") if "http_status" in value else value.get("status_code")
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if 100 <= parsed <= 599 else None


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
    return {key: value for key, value in payload.items() if value is not None and value != [] and value != {}}


__all__ = [
    "ORDINARY_LIVE_SOURCE_CUSTODY_MODE",
    "ORDINARY_LIVE_SOURCE_CUSTODY_PHASE",
    "ORDINARY_LIVE_SOURCE_CUSTODY_TRACE_KEY",
    "OrdinaryLiveSourceCustodyResult",
    "execute_ordinary_live_source_custody",
    "ordinary_live_source_custody_disabled_projection",
]
