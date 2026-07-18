"""Truthful post-DISCOVER candidate resolution and RunKernel handoff.

This runtime consumes identities and material that already exist.  It performs
no provider call, fetch/read, exact-URL transport, evidence admission, or
acquisition proposal.  The orchestrator remains responsible only for the
authorize -> invoke -> reduce sequence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.discovery_source_result import (
    DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP,
    DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP,
    DiscoveryResultMaterialStore,
    DiscoverySourceResultError,
    normalize_discovery_result_url,
)
from core.run_kernel import (
    ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)
from core.search_executor_handoff_runtime import (
    ORDINARY_SEARCH_EXECUTOR_HANDOFF_EXECUTION_MODE,
    ORDINARY_SEARCH_EXECUTOR_HANDOFF_REVISION,
    ORDINARY_SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
    SEARCH_EXECUTOR_HANDOFF_ORIGIN_ORDINARY_QUERY_PROVIDER,
    SEARCH_EXECUTOR_HANDOFF_OWNER,
    OrdinarySearchExecutorHandoffInput,
    SearchExecutorHandoffRuntimeError,
    build_ordinary_search_executor_handoff,
    build_ordinary_search_executor_handoff_projection,
    ordinary_handoff_ref_from_handoff_state,
    validate_ordinary_search_executor_handoff_binding,
)
from core.search_result_candidate_packet import (
    ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION,
    SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER,
    SearchResultCandidatePacketError,
    build_search_result_candidate_packet_from_ordinary_discovery,
    ordinary_candidate_inputs_digest,
    search_result_candidate_packet_ref_from_packet,
    validate_ordinary_search_result_candidate_packet_binding,
)

ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_SCHEMA_VERSION = (
    "ordinary_discovery_candidate_handoff_convergence_01_v1"
)
ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY = (
    "ordinary_discovery_candidate_handoff"
)
ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_OWNER = (
    "RunKernel.OrdinaryDiscoveryCandidateHandoff"
)
ORDINARY_DISCOVERY_PACKET_REVISION = 1
ORDINARY_DISCOVERY_PACKET_ABSOLUTE_CANDIDATE_CAP = 40


class OrdinaryDiscoveryCandidateHandoffError(ValueError):
    """Raised when selected discovery lineage cannot be reduced truthfully."""


@dataclass(frozen=True, slots=True)
class PreparedOrdinaryDiscoverySelection:
    candidates: tuple[Mapping[str, Any], ...]
    query_plan_ref: Mapping[str, Any]
    provider_plan_ref: Mapping[str, Any]
    selected_source_result_refs: tuple[Mapping[str, Any], ...]
    selected_query_plan_item_refs: tuple[Mapping[str, Any], ...]
    provider_plan_record_refs: tuple[Mapping[str, Any], ...]
    provider_route_refs: tuple[Mapping[str, Any], ...]
    retrieval_action_refs: tuple[Mapping[str, Any], ...]

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


@dataclass(frozen=True, slots=True)
class OrdinaryDiscoveryCandidateHandoffExecution:
    packet: Mapping[str, Any]
    handoff: Mapping[str, Any]
    projection: Mapping[str, Any]
    observation: Observation


@dataclass(frozen=True, slots=True)
class OrdinaryDiscoveryAuthoritySnapshot:
    """Current canonical plan membership used to reject stale selected refs."""

    query_plan_ref: Mapping[str, Any]
    query_plan_item_refs: tuple[Mapping[str, Any], ...]
    provider_plan_ref: Mapping[str, Any]
    provider_routes: tuple[Mapping[str, Any], ...]


def build_ordinary_discovery_authority_snapshot(
    *,
    query_plan: Any,
    provider_plan: Any,
) -> OrdinaryDiscoveryAuthoritySnapshot:
    """Read current QueryPlan/ProviderPlan membership without creating authority."""

    if not callable(getattr(query_plan, "to_ref", None)):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery requires the current QueryPlan owner"
        )
    discovery_membership = getattr(
        query_plan,
        "authorized_discovery_item_refs",
        None,
    )
    if not callable(discovery_membership):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery requires QueryPlan-owned discovery membership"
        )
    query_item_refs = tuple(discovery_membership())
    if not query_item_refs:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery QueryPlan has no authorized item refs"
        )
    if not callable(getattr(provider_plan, "to_ref", None)):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery requires the current ProviderPlan owner"
        )
    provider_routes: list[dict[str, Any]] = []
    for record in tuple(getattr(provider_plan, "records", ())):
        if not all(
            callable(getattr(record, method, None))
            for method in ("to_ref", "route_ref")
        ):
            continue
        providers = tuple(str(item) for item in getattr(record, "providers", ()))
        if len(providers) != 1:
            raise OrdinaryDiscoveryCandidateHandoffError(
                "ordinary discovery ProviderPlan route must name one provider"
            )
        provider_routes.append(
            {
                "provider_plan_record_ref": record.to_ref(),
                "provider_route_ref": record.route_ref(),
                "provider": providers[0],
            }
        )
    if not provider_routes:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery ProviderPlan has no completed route refs"
        )
    return OrdinaryDiscoveryAuthoritySnapshot(
        query_plan_ref=query_plan.to_ref(),
        query_plan_item_refs=query_item_refs,
        provider_plan_ref=provider_plan.to_ref(),
        provider_routes=tuple(provider_routes),
    )


def prepare_ordinary_discovery_selection(
    *,
    final_top_evidence: Sequence[Mapping[str, Any]],
    discovery_result_store: DiscoveryResultMaterialStore,
    selected_candidate_cap: int,
    authority_snapshot: OrdinaryDiscoveryAuthoritySnapshot,
) -> PreparedOrdinaryDiscoverySelection:
    """Resolve ranked passages back to their pre-ranking source identities."""

    cap = max(
        0,
        min(
            int(selected_candidate_cap),
            ORDINARY_DISCOVERY_PACKET_ABSOLUTE_CANDIDATE_CAP,
        ),
    )
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    selected_identities: list[Any] = []

    for passage in final_top_evidence:
        if len(candidates) >= cap:
            break
        if not isinstance(passage, Mapping):
            continue
        raw_url = str(passage.get("url") or "")
        try:
            normalized_url = normalize_discovery_result_url(raw_url)
        except DiscoverySourceResultError:
            continue
        source_result_ref = passage.get("source_result_ref")
        if not isinstance(source_result_ref, Mapping):
            # A passage whose URL belongs to the canonical store has lost
            # lineage and must never be reconstructed from ranked text.
            if discovery_result_store.ref_for_url(normalized_url):
                raise OrdinaryDiscoveryCandidateHandoffError(
                    "selected canonical passage lost its source-result ref"
                )
            continue
        if normalized_url in seen_urls:
            continue
        identity = discovery_result_store.identity_for_ref(source_result_ref)
        if identity is None or identity.ref() != dict(source_result_ref):
            raise OrdinaryDiscoveryCandidateHandoffError(
                "selected source-result ref does not resolve"
            )
        if identity.normalized_url != normalized_url:
            raise OrdinaryDiscoveryCandidateHandoffError(
                "selected passage URL does not match source-result identity"
            )
        _validate_identity_authority_membership(
            identity=identity,
            authority_snapshot=authority_snapshot,
        )
        material_ref = passage.get("source_material_ref")
        material = discovery_result_store.material_for_ref(source_result_ref)
        if (
            material is None
            or not isinstance(material_ref, Mapping)
            or material.ref() != dict(material_ref)
        ):
            raise OrdinaryDiscoveryCandidateHandoffError(
                "selected source-result material ref does not resolve"
            )

        contributor_facts = discovery_result_store.contributors_for_url(
            normalized_url
        )
        selected_rank = len(candidates) + 1
        candidates.append(
            {
                **material.candidate_fields(),
                "source_result_ref": identity.ref(),
                "source_material_ref": material.ref(),
                "provider": identity.provider,
                "provider_authorized": identity.provider,
                "provider_call_ordinal": identity.provider_call_ordinal,
                "provider_result_rank": identity.result_rank,
                "selected_candidate_rank": selected_rank,
                "normalized_url": identity.normalized_url,
                "relevance_score": float(passage.get("score", 0.0)),
                "scoring_provenance": {
                    "ranking_method": "existing_discovery_passage_ranking",
                    "relevance_score": float(passage.get("score", 0.0)),
                    "rrf_score": float(passage.get("rrf_score", 0.0)),
                    "credibility": float(passage.get("credibility", 0.0)),
                    "chunk_digest": str(passage.get("chunk_digest") or ""),
                },
                "contributing_source_result_refs": list(
                    contributor_facts.get(
                        "contributing_source_result_refs", ()
                    )
                ),
                "contributor_overflow_count": int(
                    contributor_facts.get("contributor_overflow_count", 0)
                ),
                "full_contributor_digest": contributor_facts.get(
                    "full_contributor_digest"
                ),
            }
        )
        selected_identities.append(identity)
        seen_urls.add(normalized_url)

    return PreparedOrdinaryDiscoverySelection(
        candidates=tuple(candidates),
        query_plan_ref=dict(authority_snapshot.query_plan_ref),
        provider_plan_ref=dict(authority_snapshot.provider_plan_ref),
        selected_source_result_refs=tuple(
            identity.ref() for identity in selected_identities
        ),
        selected_query_plan_item_refs=_ordered_unique_refs(
            identity.query_plan_item_ref for identity in selected_identities
        ),
        provider_plan_record_refs=_ordered_unique_refs(
            identity.provider_plan_record_ref for identity in selected_identities
        ),
        provider_route_refs=_ordered_unique_refs(
            identity.provider_route_ref for identity in selected_identities
        ),
        retrieval_action_refs=_ordered_unique_refs(
            identity.retrieval_action_ref for identity in selected_identities
        ),
    )


def build_ordinary_discovery_candidate_action_inputs(
    *,
    run_id: str,
    request_id: str,
    source_result_identity_set_ref: Mapping[str, Any],
    selection: PreparedOrdinaryDiscoverySelection,
    answer_contract_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the exact ref-only RunKernel authorization input."""

    selected_refs = [
        dict(item) for item in selection.selected_source_result_refs
    ]
    retained_selected_refs = selected_refs[
        :DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP
    ]
    return _without_empty(
        {
            "schema_version": ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_SCHEMA_VERSION,
            "run_id": str(run_id),
            "request_id": str(request_id),
            "query_plan_ref": dict(selection.query_plan_ref),
            "provider_plan_ref": dict(selection.provider_plan_ref),
            "source_result_identity_set_ref": dict(
                source_result_identity_set_ref
            ),
            "selected_source_result_refs": retained_selected_refs,
            "selected_source_result_refs_retained_count": len(
                retained_selected_refs
            ),
            "selected_source_result_ref_overflow_count": max(
                0, len(selected_refs) - len(retained_selected_refs)
            ),
            "full_selected_source_result_refs_digest": _digest_json(
                selected_refs
            ),
            "selected_candidate_count": selection.candidate_count,
            "selected_candidate_inputs_digest": ordinary_candidate_inputs_digest(
                selection.candidates
            ),
            "selected_query_plan_item_count": len(
                selection.selected_query_plan_item_refs
            ),
            "selected_query_plan_item_refs_digest": _digest_json(
                selection.selected_query_plan_item_refs
            ),
            "provider_plan_record_count": len(
                selection.provider_plan_record_refs
            ),
            "provider_plan_record_refs_digest": _digest_json(
                selection.provider_plan_record_refs
            ),
            "provider_route_count": len(selection.provider_route_refs),
            "provider_route_refs_digest": _digest_json(
                selection.provider_route_refs
            ),
            "retrieval_action_count": len(selection.retrieval_action_refs),
            "retrieval_action_refs_digest": _digest_json(
                selection.retrieval_action_refs
            ),
            "packet_revision": ORDINARY_DISCOVERY_PACKET_REVISION,
            "answer_contract_ref": dict(answer_contract_ref or {}),
            "provider_calls_already_completed": True,
            "provider_call_caused_by_handoff": False,
            "acquisition_need_proposal_created": False,
            "exact_url_transport_executed": False,
            "exact_url_cap_charged": False,
            "urls_fetched": 0,
        }
    )


def execute_ordinary_discovery_candidate_handoff_action(
    *,
    action: AuthorizedAction,
    selection: PreparedOrdinaryDiscoverySelection,
    discovery_result_store: DiscoveryResultMaterialStore,
    authority_snapshot: OrdinaryDiscoveryAuthoritySnapshot,
    answer_contract_ref: Mapping[str, Any] | None = None,
) -> OrdinaryDiscoveryCandidateHandoffExecution:
    """Build one ordinary-origin handoff and the sole canonical packet."""

    kernel_action = validate_authorized_action(
        action,
        action_type=ActionType.ORDINARY_DISCOVERY_CANDIDATE_HANDOFF,
        stage=ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_STAGE,
        expected_observation_type=(
            ObservationType.ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_CREATED
        ),
    )
    if not selection.candidates:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate handoff requires a selected source result"
        )
    _validate_selection_against_material_store(
        selection=selection,
        discovery_result_store=discovery_result_store,
        authority_snapshot=authority_snapshot,
    )
    identity_set_ref = discovery_result_store.identity_set_ref()
    expected_inputs = build_ordinary_discovery_candidate_action_inputs(
        run_id=kernel_action.run_id,
        request_id=str(kernel_action.inputs.get("request_id") or ""),
        source_result_identity_set_ref=identity_set_ref,
        selection=selection,
        answer_contract_ref=answer_contract_ref,
    )
    if dict(kernel_action.inputs) != expected_inputs:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate action binding is stale or mismatched"
        )

    handoff = build_ordinary_search_executor_handoff(
        OrdinarySearchExecutorHandoffInput(
            run_id=kernel_action.run_id,
            request_id=expected_inputs["request_id"],
            answer_contract_ref=dict(answer_contract_ref or {}),
            query_plan_ref=selection.query_plan_ref,
            selected_query_plan_item_refs=(
                selection.selected_query_plan_item_refs
            ),
            provider_plan_ref=selection.provider_plan_ref,
            provider_plan_record_refs=selection.provider_plan_record_refs,
            provider_route_refs=selection.provider_route_refs,
            retrieval_action_refs=selection.retrieval_action_refs,
            source_result_identity_set_ref=identity_set_ref,
            selected_source_result_refs=selection.selected_source_result_refs,
        ),
        authorized_action_id=kernel_action.action_id,
    )
    handoff_ref = ordinary_handoff_ref_from_handoff_state(handoff)
    packet = build_search_result_candidate_packet_from_ordinary_discovery(
        run_id=kernel_action.run_id,
        request_id=expected_inputs["request_id"],
        search_executor_handoff_ref=handoff_ref,
        source_result_identity_set_ref=identity_set_ref,
        candidates=selection.candidates,
        selected_candidate_inputs_digest=expected_inputs[
            "selected_candidate_inputs_digest"
        ],
        answer_contract_ref=answer_contract_ref,
        packet_revision=ORDINARY_DISCOVERY_PACKET_REVISION,
    )
    packet_ref = search_result_candidate_packet_ref_from_packet(packet)
    discovery_projection = discovery_result_store.runkernel_projection(
        selected_refs=(),
        packet_ref=packet_ref,
    )
    handoff_projection = build_ordinary_search_executor_handoff_projection(
        handoff_state=handoff
    )
    retained_selected_refs = [
        dict(item) for item in selection.selected_source_result_refs[
            :DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP
        ]
    ]
    projection = {
        "schema_version": ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_SCHEMA_VERSION,
        "trace_key": ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY,
        "owner": ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_OWNER,
        "canonical_state": True,
        "run_id": kernel_action.run_id,
        "request_id": expected_inputs["request_id"],
        "authorized_action_id": kernel_action.action_id,
        "search_executor_handoff_ref": _compact_handoff_ref(
            handoff_projection
        ),
        "search_result_candidate_packet_ref": packet_ref,
        "source_result_identity_set_ref": identity_set_ref,
        "selected_source_result_refs": retained_selected_refs,
        "selected_source_result_refs_retained_count": len(
            retained_selected_refs
        ),
        "selected_source_result_ref_overflow_count": max(
            0, selection.candidate_count - len(retained_selected_refs)
        ),
        "full_selected_source_result_refs_digest": _digest_json(
            selection.selected_source_result_refs
        ),
        "selected_candidate_count": selection.candidate_count,
        "packet_revision": ORDINARY_DISCOVERY_PACKET_REVISION,
        "discovery_result_state": discovery_projection,
        "candidate_packets_created": 1,
        "selected_candidates_handed_off": selection.candidate_count,
        "provider_calls_already_completed": True,
        "provider_call_caused_by_handoff": False,
        "acquisition_need_proposal_created": False,
        "read_work_order_created": False,
        "focused_extract_work_order_created": False,
        "exact_url_transport_executed": False,
        "exact_url_cap_charged": False,
        "urls_fetched": 0,
    }
    projection["canonical_result_ref_state_byte_cap"] = (
        DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP
    )
    projection["canonical_result_ref_state_bytes"] = 0
    while True:
        projection_bytes = len(_canonical_json(projection).encode("utf-8"))
        if projection["canonical_result_ref_state_bytes"] == projection_bytes:
            break
        projection["canonical_result_ref_state_bytes"] = projection_bytes
    if projection_bytes > DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery canonical ref state exceeds 16 KiB"
        )
    observation = Observation.from_action(
        kernel_action,
        observation_type=(
            ObservationType.ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_CREATED
        ),
        status=RunStageStatus.COMPLETED,
        payload={
            "search_executor_handoff": handoff_projection,
            ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY: projection,
        },
    )
    return OrdinaryDiscoveryCandidateHandoffExecution(
        packet=packet,
        handoff=handoff,
        projection=projection,
        observation=observation,
    )


def validate_ordinary_discovery_candidate_reduction(
    *,
    action_inputs: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    action_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate a ref-only observation for RunKernel reduction."""

    if set(observation_payload) != {
        "search_executor_handoff",
        ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY,
    }:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery observation contains an unknown surface"
        )
    handoff_projection = _validate_compact_handoff_projection(
        _mapping(observation_payload.get("search_executor_handoff")),
        action_inputs=action_inputs,
        run_id=run_id,
        request_id=request_id,
        action_id=action_id,
    )
    projection = _mapping(
        observation_payload.get(
            ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY
        )
    )
    if projection.get("schema_version") != (
        ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_SCHEMA_VERSION
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery handoff projection schema mismatch"
        )
    if projection.get("owner") != ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_OWNER:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery handoff projection owner mismatch"
        )
    if projection.get("run_id") != run_id or projection.get(
        "request_id"
    ) != request_id:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery handoff scope mismatch"
        )
    if projection.get("authorized_action_id") != action_id:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery handoff action mismatch"
        )
    _require_only_keys(
        projection,
        allowed=_ordinary_projection_allowed_keys(),
        required=_ordinary_projection_allowed_keys(),
        label="ordinary discovery canonical projection",
    )
    for key in (
        "source_result_identity_set_ref",
        "selected_source_result_refs",
        "selected_source_result_refs_retained_count",
        "selected_source_result_ref_overflow_count",
        "full_selected_source_result_refs_digest",
        "selected_candidate_count",
        "packet_revision",
    ):
        if projection.get(key) != action_inputs.get(key):
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary discovery handoff stale {key} binding"
            )
    compact_handoff_ref = _compact_handoff_ref(handoff_projection)
    if projection.get("search_executor_handoff_ref") != compact_handoff_ref:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery compact handoff ref is stale"
        )
    packet_ref = _mapping(
        projection.get("search_result_candidate_packet_ref")
    )
    _validate_packet_ref(
        packet_ref,
        action_inputs=action_inputs,
        handoff_ref=compact_handoff_ref,
    )
    if packet_ref.get("packet_revision") != ORDINARY_DISCOVERY_PACKET_REVISION:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate packet revision mismatch"
        )
    if packet_ref.get("source_result_identity_set_ref") != action_inputs.get(
        "source_result_identity_set_ref"
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate packet identity-set binding mismatch"
        )
    if projection.get("candidate_packets_created") != 1 or projection.get(
        "selected_candidates_handed_off"
    ) != action_inputs.get("selected_candidate_count"):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery packet/selection telemetry is inconsistent"
        )
    discovery_state = _mapping(projection.get("discovery_result_state"))
    _validate_discovery_result_state(
        discovery_state,
        identity_set_ref=_mapping(
            action_inputs.get("source_result_identity_set_ref")
        ),
        packet_ref=packet_ref,
    )
    declared_bytes = projection.get("canonical_result_ref_state_bytes")
    measured_projection = dict(projection)
    measured_projection["canonical_result_ref_state_bytes"] = 0
    while True:
        measured_bytes = len(
            _canonical_json(measured_projection).encode("utf-8")
        )
        if measured_projection["canonical_result_ref_state_bytes"] == measured_bytes:
            break
        measured_projection["canonical_result_ref_state_bytes"] = measured_bytes
    if declared_bytes != measured_bytes or measured_bytes > (
        DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery RunKernel projection byte measurement is invalid"
        )
    _validate_closed_projection(projection)
    return (
        dict(handoff_projection),
        dict(handoff_projection),
        dict(projection),
    )


def _validate_closed_projection(projection: Mapping[str, Any]) -> None:
    forbidden_text_keys = {
        "text",
        "snippet",
        "excerpt",
        "raw_content",
        "embedding",
        "chunks",
        "provider_payload",
    }
    keys = _collect_keys(projection)
    if keys & forbidden_text_keys:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery RunKernel projection contains provider text"
        )
    for key, expected in {
        "acquisition_need_proposal_created": False,
        "read_work_order_created": False,
        "focused_extract_work_order_created": False,
        "exact_url_transport_executed": False,
        "exact_url_cap_charged": False,
        "urls_fetched": 0,
    }.items():
        if projection.get(key) != expected:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary discovery handoff must keep {key}={expected!r}"
            )


_HANDOFF_CLOSED_KEYS = frozenset(
    {
        "provider_call_caused_by_handoff",
        "retrieval_action_caused_by_handoff",
        "acquisition_need_proposal_created",
        "exact_url_transport_executed",
        "exact_url_fetch_executed",
        "fetch_read_retrieval_executed",
        "read_executed",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "citation_eligible",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
    }
)

_DISCOVERY_STATE_CLOSED_KEYS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_payload_retained",
        "provider_result_text_in_identity",
        "fetch_read_executed",
        "fetch_read_retrieval_executed",
        "exact_url_fetch_read_executed",
        "separate_exact_url_transport_performed",
        "read_executed",
        "exact_url_acquisition_executed",
        "exact_url_cap_charged",
        "acquisition_need_proposal_created",
        "evidence_created",
        "evidence_ledger_admitted",
        "evidence_authority",
        "citation_eligible",
        "citation_created",
        "citation_authority",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "downstream_answer_authority",
        "product_correctness_claimed",
    }
)


def _validate_compact_handoff_projection(
    handoff: Mapping[str, Any],
    *,
    action_inputs: Mapping[str, Any],
    run_id: str,
    request_id: str,
    action_id: str,
) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "origin_kind",
        "handoff_revision",
        "trace_key",
        "owner",
        "handoff_id",
        "handoff_digest",
        "dedupe_key",
        "run_id",
        "request_id",
        "authorized_action_id",
        "answer_contract_ref",
        "query_plan_ref",
        "selected_query_plan_item_count",
        "selected_query_plan_item_refs_digest",
        "provider_plan_ref",
        "provider_plan_record_count",
        "provider_plan_record_refs_digest",
        "provider_route_count",
        "provider_route_refs_digest",
        "retrieval_action_count",
        "retrieval_action_refs_digest",
        "source_result_identity_set_ref",
        "selected_source_result_count",
        "full_selected_source_result_refs_digest",
        "execution_mode",
        "discovery_provider_calls_preceded_handoff",
        "search_executor_handoff_created",
        *_HANDOFF_CLOSED_KEYS,
    }
    _require_only_keys(
        handoff,
        allowed=allowed,
        required=allowed - {"answer_contract_ref"},
        label="ordinary SearchExecutor compact handoff",
    )
    for key, expected in {
        "schema_version": ORDINARY_SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
        "origin_kind": SEARCH_EXECUTOR_HANDOFF_ORIGIN_ORDINARY_QUERY_PROVIDER,
        "handoff_revision": ORDINARY_SEARCH_EXECUTOR_HANDOFF_REVISION,
        "owner": SEARCH_EXECUTOR_HANDOFF_OWNER,
        "run_id": run_id,
        "request_id": request_id,
        "authorized_action_id": action_id,
        "execution_mode": ORDINARY_SEARCH_EXECUTOR_HANDOFF_EXECUTION_MODE,
        "discovery_provider_calls_preceded_handoff": True,
        "search_executor_handoff_created": True,
    }.items():
        if handoff.get(key) != expected:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary SearchExecutor compact handoff has stale {key}"
            )
    for key in _HANDOFF_CLOSED_KEYS:
        if handoff.get(key) is not False:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary SearchExecutor compact handoff must keep {key}=False"
            )
    bindings = {
        "answer_contract_ref": action_inputs.get("answer_contract_ref", {}),
        "query_plan_ref": action_inputs.get("query_plan_ref"),
        "provider_plan_ref": action_inputs.get("provider_plan_ref"),
        "source_result_identity_set_ref": action_inputs.get(
            "source_result_identity_set_ref"
        ),
        "selected_source_result_count": action_inputs.get(
            "selected_candidate_count"
        ),
        "full_selected_source_result_refs_digest": action_inputs.get(
            "full_selected_source_result_refs_digest"
        ),
        "selected_query_plan_item_count": action_inputs.get(
            "selected_query_plan_item_count"
        ),
        "selected_query_plan_item_refs_digest": action_inputs.get(
            "selected_query_plan_item_refs_digest"
        ),
        "provider_plan_record_count": action_inputs.get(
            "provider_plan_record_count"
        ),
        "provider_plan_record_refs_digest": action_inputs.get(
            "provider_plan_record_refs_digest"
        ),
        "provider_route_count": action_inputs.get("provider_route_count"),
        "provider_route_refs_digest": action_inputs.get(
            "provider_route_refs_digest"
        ),
        "retrieval_action_count": action_inputs.get("retrieval_action_count"),
        "retrieval_action_refs_digest": action_inputs.get(
            "retrieval_action_refs_digest"
        ),
    }
    for key, expected in bindings.items():
        if handoff.get(key, {}) != expected:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary SearchExecutor compact handoff binding mismatch: {key}"
            )
    for key in ("handoff_digest", "dedupe_key"):
        _require_sha256(handoff.get(key), key)
    if not str(handoff.get("handoff_id") or "").startswith(
        "search-executor-handoff:ordinary:"
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary SearchExecutor compact handoff id is invalid"
        )
    try:
        validate_ordinary_search_executor_handoff_binding(handoff)
    except SearchExecutorHandoffRuntimeError as exc:
        raise OrdinaryDiscoveryCandidateHandoffError(str(exc)) from exc
    return dict(handoff)


def _validate_packet_ref(
    packet_ref: Mapping[str, Any],
    *,
    action_inputs: Mapping[str, Any],
    handoff_ref: Mapping[str, Any],
) -> None:
    allowed = {
        "packet_id",
        "packet_digest",
        "schema_version",
        "run_id",
        "request_id",
        "candidate_count",
        "origin_kind",
        "packet_revision",
        "full_selected_source_result_refs_digest",
        "selected_candidate_inputs_digest",
        "ordered_candidate_record_digests_digest",
        "source_result_identity_set_ref",
        "search_executor_handoff_ref",
    }
    _require_only_keys(
        packet_ref,
        allowed=allowed,
        required=allowed,
        label="ordinary candidate packet ref",
    )
    for key, expected in {
        "schema_version": ORDINARY_SEARCH_RESULT_CANDIDATE_PACKET_SCHEMA_VERSION,
        "origin_kind": SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER,
        "packet_revision": ORDINARY_DISCOVERY_PACKET_REVISION,
        "run_id": action_inputs.get("run_id"),
        "request_id": action_inputs.get("request_id"),
        "candidate_count": action_inputs.get("selected_candidate_count"),
        "full_selected_source_result_refs_digest": action_inputs.get(
            "full_selected_source_result_refs_digest"
        ),
        "selected_candidate_inputs_digest": action_inputs.get(
            "selected_candidate_inputs_digest"
        ),
        "source_result_identity_set_ref": action_inputs.get(
            "source_result_identity_set_ref"
        ),
        "search_executor_handoff_ref": handoff_ref,
    }.items():
        if packet_ref.get(key) != expected:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary candidate packet ref binding mismatch: {key}"
            )
    _require_sha256(packet_ref.get("packet_digest"), "packet_digest")
    _require_sha256(
        packet_ref.get("ordered_candidate_record_digests_digest"),
        "ordered_candidate_record_digests_digest",
    )
    if not str(packet_ref.get("packet_id") or "").startswith(
        "search-result-candidate-packet:"
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate packet ref id is invalid"
        )
    try:
        validate_ordinary_search_result_candidate_packet_binding(packet_ref)
    except SearchResultCandidatePacketError as exc:
        raise OrdinaryDiscoveryCandidateHandoffError(str(exc)) from exc


def _validate_discovery_result_state(
    state: Mapping[str, Any],
    *,
    identity_set_ref: Mapping[str, Any],
    packet_ref: Mapping[str, Any],
) -> None:
    base_keys = {
        "schema_version",
        "owner",
        "source_result_identity_set_ref",
        "source_result_identity_run_cap",
        "source_result_identity_canonical_byte_cap",
        "source_result_identity_canonical_bytes",
        "selected_source_result_refs",
        "selected_source_result_count",
        "selected_source_result_refs_retained_count",
        "selected_source_result_ref_overflow_count",
        "full_selected_source_result_refs_digest",
        "search_result_candidate_packet_ref",
        "projection_byte_cap",
        "disposition_counts",
    }
    allowed = base_keys | set(_DISCOVERY_STATE_CLOSED_KEYS)
    _require_only_keys(
        state,
        allowed=allowed,
        required=allowed,
        label="ordinary discovery result state",
    )
    if state.get("source_result_identity_set_ref") != identity_set_ref:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery state identity set is stale"
        )
    nested_packet_ref = {
        key: packet_ref[key]
        for key in (
            "packet_id",
            "packet_digest",
            "schema_version",
            "packet_revision",
            "run_id",
            "request_id",
            "full_selected_source_result_refs_digest",
            "selected_candidate_inputs_digest",
            "ordered_candidate_record_digests_digest",
        )
        if key in packet_ref
    }
    if state.get("search_result_candidate_packet_ref") != nested_packet_ref:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery state packet ref is stale"
        )
    if state.get("projection_byte_cap") != (
        DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery state projection cap is stale"
        )
    if state.get("selected_source_result_refs") != [] or state.get(
        "selected_source_result_count"
    ) != 0:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery nested state must not duplicate selected refs"
        )
    for key in _DISCOVERY_STATE_CLOSED_KEYS:
        if state.get(key) is not False:
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"ordinary discovery state must keep {key}=False"
            )
    disposition = _mapping(state.get("disposition_counts"))
    if set(disposition) != {
        "primary_url_material_retained",
        "duplicate_url_material_retained",
        "invalid_result_url",
        "provider_call_result_overflow",
        "identity_run_cap_overflow",
        "identity_byte_cap_overflow",
    } or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in disposition.values()
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary discovery state disposition counts are invalid"
        )


def _ordinary_projection_allowed_keys() -> set[str]:
    return {
        "schema_version",
        "trace_key",
        "owner",
        "canonical_state",
        "run_id",
        "request_id",
        "authorized_action_id",
        "search_executor_handoff_ref",
        "search_result_candidate_packet_ref",
        "source_result_identity_set_ref",
        "selected_source_result_refs",
        "selected_source_result_refs_retained_count",
        "selected_source_result_ref_overflow_count",
        "full_selected_source_result_refs_digest",
        "selected_candidate_count",
        "packet_revision",
        "discovery_result_state",
        "candidate_packets_created",
        "selected_candidates_handed_off",
        "provider_calls_already_completed",
        "provider_call_caused_by_handoff",
        "acquisition_need_proposal_created",
        "read_work_order_created",
        "focused_extract_work_order_created",
        "exact_url_transport_executed",
        "exact_url_cap_charged",
        "urls_fetched",
        "canonical_result_ref_state_byte_cap",
        "canonical_result_ref_state_bytes",
    }


def _require_only_keys(
    value: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    keys = {str(key) for key in value}
    if not required.issubset(keys) or not keys.issubset(allowed):
        raise OrdinaryDiscoveryCandidateHandoffError(
            f"{label} has missing or unknown fields"
        )


def _require_sha256(value: Any, label: str) -> str:
    token = str(value or "").casefold()
    if len(token) != 64 or any(
        character not in "0123456789abcdef" for character in token
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            f"{label} must be a SHA-256 digest"
        )
    return token


def _validate_identity_authority_membership(
    *,
    identity: Any,
    authority_snapshot: OrdinaryDiscoveryAuthoritySnapshot,
) -> None:
    query_plan_ref = dict(authority_snapshot.query_plan_ref)
    if identity.query_plan_ref.get("query_plan_id") != query_plan_ref.get(
        "query_plan_id"
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected source result belongs to a stale QueryPlan"
        )
    identity_item_key = _query_item_membership_key(identity.query_plan_item_ref)
    current_item = next(
        (
            item
            for item in authority_snapshot.query_plan_item_refs
            if _query_item_membership_key(item) == identity_item_key
        ),
        None,
    )
    if current_item is None:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected source result QueryPlan item is stale or absent"
        )
    if str(current_item.get("query_plan_role") or "") != identity.query_role or int(
        current_item.get("iteration") or 0
    ) != identity.iteration:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected source result QueryPlan role/iteration is stale"
        )
    provider_plan_ref = dict(authority_snapshot.provider_plan_ref)
    if identity.provider_plan_ref.get("provider_plan_id") != (
        provider_plan_ref.get("provider_plan_id")
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected source result belongs to a stale ProviderPlan"
        )
    route_matches = any(
        dict(route.get("provider_plan_record_ref") or {})
        == dict(identity.provider_plan_record_ref)
        and dict(route.get("provider_route_ref") or {})
        == dict(identity.provider_route_ref)
        and str(route.get("provider") or "") == identity.provider
        for route in authority_snapshot.provider_routes
    )
    if not route_matches:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected source result provider route is stale or mismatched"
        )


def _validate_selection_against_material_store(
    *,
    selection: PreparedOrdinaryDiscoverySelection,
    discovery_result_store: DiscoveryResultMaterialStore,
    authority_snapshot: OrdinaryDiscoveryAuthoritySnapshot,
) -> None:
    if len(selection.candidates) != len(selection.selected_source_result_refs):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected candidate/ref counts do not match"
        )
    resolved_identities: list[Any] = []
    for selected_rank, (candidate, source_ref) in enumerate(
        zip(
            selection.candidates,
            selection.selected_source_result_refs,
            strict=True,
        ),
        start=1,
    ):
        identity = discovery_result_store.identity_for_ref(source_ref)
        material = discovery_result_store.material_for_ref(source_ref)
        if identity is None or material is None:
            raise OrdinaryDiscoveryCandidateHandoffError(
                "selected candidate no longer resolves to discovery custody"
            )
        resolved_identities.append(identity)
        _validate_identity_authority_membership(
            identity=identity,
            authority_snapshot=authority_snapshot,
        )
        expected_material_fields = material.candidate_fields()
        exact_checks = {
            "source_result_ref": identity.ref(),
            "source_material_ref": material.ref(),
            "provider": identity.provider,
            "provider_authorized": identity.provider,
            "provider_call_ordinal": identity.provider_call_ordinal,
            "provider_result_rank": identity.result_rank,
            "selected_candidate_rank": selected_rank,
            "normalized_url": identity.normalized_url,
            "url": expected_material_fields["url"],
            "domain": expected_material_fields["domain"],
            "material_ref": expected_material_fields["material_ref"],
            "material_class": expected_material_fields["material_class"],
            "material_digest": expected_material_fields["material_digest"],
            "title": expected_material_fields["title"],
            "snippet": expected_material_fields["snippet"],
        }
        if expected_material_fields.get("published_or_observed_date"):
            exact_checks["published_or_observed_date"] = (
                expected_material_fields["published_or_observed_date"]
            )
        for key, expected in exact_checks.items():
            if _plain(candidate.get(key)) != _plain(expected):
                raise OrdinaryDiscoveryCandidateHandoffError(
                    f"selected candidate has stale or fabricated {key}"
                )
    if not resolved_identities:
        raise OrdinaryDiscoveryCandidateHandoffError(
            "ordinary candidate execution requires resolved identities"
        )
    if _plain(selection.query_plan_ref) != _plain(
        authority_snapshot.query_plan_ref
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected candidate QueryPlan aggregate is stale"
        )
    if _plain(selection.provider_plan_ref) != _plain(
        authority_snapshot.provider_plan_ref
    ):
        raise OrdinaryDiscoveryCandidateHandoffError(
            "selected candidate ProviderPlan aggregate is stale"
        )
    expected_aggregates = {
        "selected_source_result_refs": tuple(
            identity.ref() for identity in resolved_identities
        ),
        "selected_query_plan_item_refs": _ordered_unique_refs(
            identity.query_plan_item_ref for identity in resolved_identities
        ),
        "provider_plan_record_refs": _ordered_unique_refs(
            identity.provider_plan_record_ref for identity in resolved_identities
        ),
        "provider_route_refs": _ordered_unique_refs(
            identity.provider_route_ref for identity in resolved_identities
        ),
        "retrieval_action_refs": _ordered_unique_refs(
            identity.retrieval_action_ref for identity in resolved_identities
        ),
    }
    for field_name, expected in expected_aggregates.items():
        if _plain(getattr(selection, field_name)) != _plain(expected):
            raise OrdinaryDiscoveryCandidateHandoffError(
                f"selected candidate {field_name} aggregate is stale"
            )


def _ordered_unique_refs(
    values: Sequence[Mapping[str, Any]] | Any,
) -> tuple[Mapping[str, Any], ...]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, Mapping):
            continue
        safe = dict(value)
        key = _canonical_json(safe)
        if key in seen:
            continue
        seen.add(key)
        out.append(safe)
    return tuple(out)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _compact_handoff_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "handoff_id": value.get("handoff_id"),
            "handoff_digest": value.get("handoff_digest"),
            "schema_version": value.get("schema_version"),
            "origin_kind": value.get("origin_kind"),
            "handoff_revision": value.get("handoff_revision"),
        }
    )


def _without_empty(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != {} and item != []
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest_json(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _query_item_membership_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(value.get("query_plan_item_id") or ""),
        str(value.get("query_plan_item_digest") or ""),
        str(value.get("query_digest") or ""),
    )


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).casefold() for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


__all__ = [
    "ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_OWNER",
    "ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_SCHEMA_VERSION",
    "ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY",
    "ORDINARY_DISCOVERY_PACKET_ABSOLUTE_CANDIDATE_CAP",
    "ORDINARY_DISCOVERY_PACKET_REVISION",
    "OrdinaryDiscoveryCandidateHandoffError",
    "OrdinaryDiscoveryCandidateHandoffExecution",
    "OrdinaryDiscoveryAuthoritySnapshot",
    "PreparedOrdinaryDiscoverySelection",
    "build_ordinary_discovery_authority_snapshot",
    "build_ordinary_discovery_candidate_action_inputs",
    "execute_ordinary_discovery_candidate_handoff_action",
    "prepare_ordinary_discovery_selection",
    "validate_ordinary_discovery_candidate_reduction",
]
