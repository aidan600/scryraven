"""Governed fixture-backed follow-up search authorization and reentry loop.

This helper is a runtime seam, not a durable packet. It consumes validated
``FollowupSearchIntentPacket`` proposals, asks RunKernel to authorize bounded
follow-up search work, and then accepts fixture-only candidate/read material
back through the existing packet and reducer chain.

It never dispatches live search, calls providers or brokers, fetches URLs,
retrieves, calls models, creates Author input, creates FinalAnswerPacket state,
decides Sufficiency, or mutates ``current_answer_contract``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.analysis_gap_followup_search_packet import validate_followup_search_intent_packet
from core.component_coverage_record import (
    ComponentCoverageRecord,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageLineage,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
)
from core.component_coverage_reduction_runtime import evidence_ledger_projection_digest
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (
    build_evidence_relative_analysis_packet,
    validate_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
    validate_fetch_read_content_packet,
)
from core.followup_search_authorization_runtime import (
    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
    build_followup_search_authorization_observation_payload,
)
from core.run_kernel import Observation, ObservationType, RunKernelTransitionError, RunStageStatus
from core.search_result_candidate_packet import (
    SearchResultCandidatePacket,
    SearchResultCandidateRecord,
    validate_search_result_candidate_packet,
)
from core.semantic_observation_admission_bridge import (
    SemanticObservationAdmissionBridgeResult,
    admit_semantic_observations_from_analysis_support_findings,
)

FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER = (
    "followup_search_authorization_loop_ag_followup_search_authorization_reentry_01"
)


class FollowupSearchAuthorizationLoopError(ValueError):
    """Raised when the governed follow-up search loop cannot proceed."""


@dataclass(frozen=True, slots=True)
class FollowupSearchAuthorizationResult:
    """Compact runtime result for one RunKernel-authorized follow-up search."""

    authorization_action_id: str
    authorization_projection: Mapping[str, Any]
    latest_authorization: Mapping[str, Any]
    authorized_work_identity: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_kind": "followup_search_authorization_result",
            "durable_packet": False,
            "helper": FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER,
            "authorization_action_id": self.authorization_action_id,
            "latest_authorization": dict(self.latest_authorization),
            "authorized_work_identity": dict(self.authorized_work_identity),
            "authorization_projection": dict(self.authorization_projection),
            "proposal_packet_authorizes_search_by_itself": False,
            "live_dispatch_allowed": False,
            "fixture_reentry_only": True,
        }


@dataclass(frozen=True, slots=True)
class FollowupSearchReentryResult:
    """Compact runtime result for fixture-backed follow-up search reentry."""

    authorization_result: FollowupSearchAuthorizationResult
    candidate_packet: Mapping[str, Any]
    fetch_read_packet: Mapping[str, Any]
    ledger_projection: Mapping[str, Any]
    analysis_packet: Mapping[str, Any]
    semantic_admission_results: tuple[SemanticObservationAdmissionBridgeResult, ...]
    coverage_projection: Mapping[str, Any]
    unresolved_component_posture: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_kind": "followup_search_reentry_result",
            "durable_packet": False,
            "helper": FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER,
            "authorization": self.authorization_result.to_dict(),
            "candidate_packet_ref": {
                "packet_id": self.candidate_packet.get("packet_id"),
                "packet_digest": self.candidate_packet.get("packet_digest"),
                "candidate_count": self.candidate_packet.get("candidate_count"),
            },
            "fetch_read_packet_ref": {
                "packet_id": self.fetch_read_packet.get("packet_id"),
                "packet_digest": self.fetch_read_packet.get("packet_digest"),
                "reference_count": self.fetch_read_packet.get("reference_count"),
            },
            "analysis_packet_ref": {
                "packet_id": self.analysis_packet.get("packet_id"),
                "packet_digest": self.analysis_packet.get("packet_digest"),
            },
            "semantic_observation_admission_count": len(
                self.semantic_admission_results
            ),
            "coverage_projection": dict(self.coverage_projection),
            "unresolved_component_posture": dict(self.unresolved_component_posture),
            "live_dispatch_allowed": False,
            "provider_called": False,
            "broker_called": False,
            "model_called": False,
            "author_input_created": False,
            "final_answer_packet_created": False,
            "sufficiency_decided": False,
        }


def authorize_followup_search_work(
    *,
    run_kernel: Any,
    followup_search_intent_packet: Mapping[str, Any],
    mode: str = "Balanced",
    proposal_ids: Sequence[str] = (),
    logical_depth: int = 1,
    unresolved_blocker_ids: Sequence[str] = (),
    new_evidence_expected: bool = True,
    extra_recovery_authorized: bool = False,
) -> FollowupSearchAuthorizationResult:
    """Ask RunKernel to authorize bounded follow-up search work."""

    packet = validate_followup_search_intent_packet(followup_search_intent_packet)
    try:
        action = run_kernel.authorize_followup_search(
            followup_search_intent_packet=packet,
            mode=mode,
            proposal_ids=proposal_ids,
            logical_depth=logical_depth,
            unresolved_blocker_ids=unresolved_blocker_ids,
            new_evidence_expected=new_evidence_expected,
            extra_recovery_authorized=extra_recovery_authorized,
        )
        observation_payload = build_followup_search_authorization_observation_payload(
            action_id=action.action_id,
            action_inputs=action.inputs,
        )
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.FOLLOWUP_SEARCH_AUTHORIZED,
                status=RunStageStatus.COMPLETED,
                payload=observation_payload,
            )
        )
    except RunKernelTransitionError as exc:
        raise FollowupSearchAuthorizationLoopError(str(exc)) from exc
    projection = dict(run_kernel.state.projections[FOLLOWUP_SEARCH_AUTHORIZATION_STAGE])
    latest = dict(projection["latest_authorization"])
    work = _latest_work_identity(projection)
    return FollowupSearchAuthorizationResult(
        authorization_action_id=action.action_id,
        authorization_projection=projection,
        latest_authorization=latest,
        authorized_work_identity=work,
    )


def run_fixture_followup_search_reentry_loop(
    *,
    run_kernel: Any,
    followup_search_intent_packet: Mapping[str, Any],
    fixture_candidates: Sequence[Mapping[str, Any]],
    fixture_fetch_read_materials: Sequence[Mapping[str, Any]],
    mode: str = "Balanced",
    proposal_ids: Sequence[str] = (),
    logical_depth: int = 1,
    unresolved_blocker_ids: Sequence[str] = (),
    analyst_repass_outcome: str = "support",
) -> FollowupSearchReentryResult:
    """Authorize and re-enter fixture-backed follow-up search material."""

    authorization = authorize_followup_search_work(
        run_kernel=run_kernel,
        followup_search_intent_packet=followup_search_intent_packet,
        mode=mode,
        proposal_ids=proposal_ids,
        logical_depth=logical_depth,
        unresolved_blocker_ids=unresolved_blocker_ids,
    )
    candidate_packet = build_fixture_search_result_candidate_packet(
        authorization_result=authorization,
        fixture_candidates=fixture_candidates,
    )
    fetch_read_packet = build_fixture_fetch_read_content_packet(
        candidate_packet=candidate_packet,
        fixture_fetch_read_materials=fixture_fetch_read_materials,
    )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=run_kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    analysis_packet = build_followup_reentry_analysis_packet(
        ledger_projection=ledger_projection,
        analyst_repass_outcome=analyst_repass_outcome,
        followup_handoff_digest=authorization.authorized_work_identity.get(
            "handoff_digest"
        ),
    )

    semantic_results: tuple[SemanticObservationAdmissionBridgeResult, ...] = ()
    coverage_projection: dict[str, Any] = {}
    unresolved_posture: dict[str, Any] = {}
    if _has_support_finding(analysis_packet):
        semantic_results = admit_semantic_observations_from_analysis_support_findings(
            run_kernel=run_kernel,
            evidence_relative_analysis_packet=analysis_packet,
            fetch_read_content_packet=fetch_read_packet,
        )
        coverage_projection = reduce_component_coverage_from_admitted_followup_support(
            run_kernel=run_kernel,
            admission_result=semantic_results[0],
        )
    else:
        unresolved_posture = unresolved_component_posture_from_analysis_packet(
            analysis_packet
        )

    return FollowupSearchReentryResult(
        authorization_result=authorization,
        candidate_packet=candidate_packet,
        fetch_read_packet=fetch_read_packet,
        ledger_projection=ledger_projection,
        analysis_packet=analysis_packet,
        semantic_admission_results=semantic_results,
        coverage_projection=coverage_projection,
        unresolved_component_posture=unresolved_posture,
    )


def build_fixture_search_result_candidate_packet(
    *,
    authorization_result: FollowupSearchAuthorizationResult,
    fixture_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a SearchResultCandidatePacket from fixture candidate material."""

    work = authorization_result.authorized_work_identity
    task_records = [_safe_mapping(item) for item in work.get("search_task_records") or ()]
    if not task_records:
        raise FollowupSearchAuthorizationLoopError(
            "authorized follow-up search work has no search_task_records"
        )
    fixture_list = [_safe_mapping(item) for item in fixture_candidates]
    if not fixture_list:
        raise FollowupSearchAuthorizationLoopError(
            "fixture reentry requires at least one fixture candidate"
        )
    current_ref = _safe_mapping(work.get("parent_current_contract_ref"))
    handoff_ref = {
        "handoff_id": work.get("handoff_id"),
        "handoff_digest": work.get("handoff_digest"),
        "schema_version": work.get("schema_version"),
        "dedupe_key": work.get("work_dedupe_key"),
        "contract_parent_kind": "current_answer_contract",
        "parent_current_contract_ref": current_ref,
    }
    records = []
    for index, fixture in enumerate(fixture_list, start=1):
        task = task_records[(index - 1) % len(task_records)]
        candidate_id = (
            _clean_token(fixture.get("candidate_id"), limit=320)
            or f"followup-search-candidate:{_clean_token(task.get('search_task_id'), limit=180)}:{index}"
        )
        candidate_digest = _digest_json(
            {
                "candidate_id": candidate_id,
                "title": fixture.get("title"),
                "url": fixture.get("url"),
                "domain": fixture.get("domain"),
                "search_task_id": task.get("search_task_id"),
            }
        )
        record = SearchResultCandidateRecord(
            run_id=str(work["run_id"]),
            request_id=str(work["request_id"]),
            current_answer_contract_ref=current_ref,
            search_executor_handoff_ref=handoff_ref,
            search_task_id=str(task["search_task_id"]),
            query_intent_id=_clean_token(task.get("query_intent_id"), limit=260),
            component_id=_clean_token(task.get("component_id"), limit=260),
            source_obligation_candidate_ids=_text_tuple(
                fixture.get("source_obligation_candidate_ids"),
                limit=260,
            ),
            provider_authorized="fixture_followup_search",
            provider_used="fixture_followup_search",
            provider_call_index=1,
            result_rank=index,
            title=str(fixture["title"]),
            url=str(fixture["url"]),
            domain=str(fixture["domain"]),
            snippet=_clean_text(fixture.get("snippet"), limit=500),
            published_or_observed_date=_clean_token(
                fixture.get("published_or_observed_date"),
                limit=80,
            ),
            candidate_id=candidate_id,
            candidate_digest=candidate_digest,
        ).to_dict()
        records.append(record)
    packet = SearchResultCandidatePacket(
        run_id=str(work["run_id"]),
        request_id=str(work["request_id"]),
        current_answer_contract_ref=current_ref,
        search_executor_handoff_ref=handoff_ref,
        selected_search_task_ids=[record["search_task_id"] for record in records],
        provider_authorized="fixture_followup_search",
        provider_used="fixture_followup_search",
        candidate_records=records,
    ).to_dict()
    return validate_search_result_candidate_packet(packet)


def build_fixture_fetch_read_content_packet(
    *,
    candidate_packet: Mapping[str, Any],
    fixture_fetch_read_materials: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a FetchReadContentPacket from fixture read material."""

    candidate_packet = validate_search_result_candidate_packet(candidate_packet)
    materials = []
    fixture_list = [_safe_mapping(item) for item in fixture_fetch_read_materials]
    if not fixture_list:
        raise FollowupSearchAuthorizationLoopError(
            "fixture reentry requires at least one fixture fetch/read material"
        )
    records = candidate_packet["candidate_records"]
    if len(fixture_list) != len(records):
        raise FollowupSearchAuthorizationLoopError(
            "fixture fetch/read material count must match candidate count"
        )
    for candidate, material in zip(records, fixture_list, strict=True):
        materials.append(_material_for_candidate(candidate, candidate_packet, material))
    packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        materials,
    )
    return validate_fetch_read_content_packet(packet)


def build_followup_reentry_analysis_packet(
    *,
    ledger_projection: Mapping[str, Any],
    analyst_repass_outcome: str,
    followup_handoff_digest: str | None = None,
) -> dict[str, Any]:
    """Build an EvidenceRelativeAnalysisPacket for fixture re-pass."""

    all_records = _custody_records(ledger_projection)
    records = _filter_records_by_handoff_digest(
        all_records,
        followup_handoff_digest=followup_handoff_digest,
    )
    analysis_projection = _ledger_projection_for_records(
        ledger_projection,
        records=records,
    )
    contract_ref = _contract_ref_from_custody(records)
    outcome = str(analyst_repass_outcome or "support").casefold()
    proposals: list[dict[str, Any]] = []
    readable = [record for record in records if record.get("fetch_read_status") == "readable"]
    if outcome == "support" and readable:
        proposals.append(_support_proposal(readable[0]))
    elif outcome in {"stale", "currentness"} and readable:
        proposals.append(
            _analysis_gap_proposal(
                readable[0],
                "currentness_concern",
                information_needed="Fixture follow-up evidence is stale or not current enough.",
            )
        )
    elif outcome in {"contradictory", "contradiction", "contested"} and readable:
        proposals.append(
            _analysis_gap_proposal(
                readable[0],
                "possible_contradiction",
                information_needed="Fixture follow-up evidence remains contradictory.",
            )
        )
    elif outcome in {"insufficient", "missing_fact"} and readable:
        proposals.append(
            _analysis_gap_proposal(
                readable[0],
                "missing_fact",
                information_needed="Fixture follow-up evidence does not resolve the missing fact.",
            )
        )
    packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=analysis_projection,
        analyst_proposal_records=proposals,
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref.get("contract_digest"),
    )
    return validate_evidence_relative_analysis_packet(packet)


def reduce_component_coverage_from_admitted_followup_support(
    *,
    run_kernel: Any,
    admission_result: SemanticObservationAdmissionBridgeResult,
) -> dict[str, Any]:
    """Reduce ComponentCoverage from an admitted follow-up support observation."""

    record = _coverage_record_for_admission(
        run_kernel=run_kernel,
        admission_result=admission_result,
    )
    component_ref = _initial_component_ref(run_kernel)
    action = run_kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={
            "followup_search_authorization_reentry_helper": (
                FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER
            )
        },
    )
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": payload},
        )
    )
    return dict(run_kernel.state.component_coverage_projection)


def unresolved_component_posture_from_analysis_packet(
    analysis_packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Return blocked/follow-up-required/contested posture without coverage."""

    packet = validate_evidence_relative_analysis_packet(analysis_packet)
    gaps = [
        _safe_mapping(item)
        for item in _safe_mapping(packet.get("analyst_report")).get(
            "analysis_gap_proposals",
            [],
        )
        if isinstance(item, Mapping)
    ]
    gap_kinds = [gap.get("gap_kind") for gap in gaps]
    contested = any(kind == "possible_contradiction" for kind in gap_kinds)
    stale = any(kind == "currentness_concern" for kind in gap_kinds)
    return {
        "posture": "contested" if contested else "blocked",
        "coverage_state": "contested" if contested else "blocked",
        "semantic_support_status": "unknown",
        "followup_need": "required",
        "currentness_posture": "stale_or_unknown" if stale else "unknown",
        "analysis_gap_count": len(gaps),
        "gap_kinds": gap_kinds,
        "coverage_reduced": False,
        "support_admitted": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
    }


def _coverage_record_for_admission(
    *,
    run_kernel: Any,
    admission_result: SemanticObservationAdmissionBridgeResult,
) -> ComponentCoverageRecord:
    component_ref = _initial_component_ref(run_kernel)
    ledger_binding = _ledger_binding(run_kernel)
    observation = admission_result.semantic_observation
    content_ref = admission_result.sanitized_content_reference
    return ComponentCoverageRecord(
        record_id=(
            "coverage:followup-search-reentry:"
            f"{observation.observation_digest[:16]}"
        ),
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=run_kernel.state.initial_answer_contract[
            "parent_question_meaning_record_digest"
        ],
        accepted_contract_version=run_kernel.state.initial_answer_contract[
            "accepted_contract_version"
        ],
        accepted_contract_digest=run_kernel.state.initial_answer_contract[
            "accepted_contract_digest"
        ],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=ledger_binding,
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(
            SemanticObservationCoverageRef.from_observation(observation),
        ),
        content_reference_bindings=(
            ContentReferenceCoverageBinding.from_content_reference(content_ref),
        ),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=(
            "source-obligation candidate ids remain lineage only",
            "fixture follow-up support does not create citation eligibility",
        ),
        required_caveats=(
            "Do not upgrade fixture follow-up custody to final evidence.",
        ),
        prohibited_upgrades=(
            "Do not treat follow-up attempt status as support.",
            "Do not create Sufficiency, FAP, Author, or citation state.",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        lineage=CoverageLineage(
            created_by=FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER,
            created_from=(
                "followup_search_authorization",
                "fixture_search_result_candidate_packet",
                "fetch_read_content_packet",
                "evidence_ledger_custody",
                "evidence_relative_analysis_packet",
                "admitted_semantic_observation",
            ),
        ),
        metadata={
            "phase": "AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01",
            "helper": FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER,
            "fixture_backed_execution": True,
        },
    ).require_valid()


def _ledger_binding(run_kernel: Any) -> EvidenceLedgerSnapshotBinding:
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        ref["observation_id"]
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{run_kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _material_for_candidate(
    candidate: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
    material: Mapping[str, Any],
) -> dict[str, Any]:
    status = _clean_token(material.get("fetch_read_status"), limit=80) or "readable"
    base = {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": candidate_packet["run_id"],
        "request_id": candidate_packet["request_id"],
        "current_answer_contract_digest": candidate_packet[
            "current_answer_contract_digest"
        ],
        "search_executor_handoff_digest": candidate_packet[
            "search_executor_handoff_digest"
        ],
        "search_result_candidate_packet_id": candidate_packet["packet_id"],
        "search_result_candidate_packet_digest": candidate_packet["packet_digest"],
        "fetch_read_status": status,
        "attempted_url": candidate["url"],
        "resolved_url": material.get("resolved_url") or candidate["url"],
        "resolved_domain": material.get("resolved_domain") or candidate["domain"],
        "content_type": material.get("content_type") or "text/html",
        "http_status": material.get("http_status") or (200 if status == "readable" else None),
        "retrieved_or_observed_at": material.get("retrieved_or_observed_at")
        or "2026-06-28T00:00:00Z",
        "published_or_observed_date": material.get("published_or_observed_date"),
        "content_title": material.get("content_title") or candidate["title"],
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }
    if status == "readable":
        bounded_text = _clean_text(
            material.get("bounded_text")
            or "Bounded sanitized follow-up fixture evidence for this component.",
            limit=1_900,
        )
        base.update(
            {
                "bounded_text": bounded_text,
                "bounded_text_sanitized": True,
                "bounded_text_bounded": True,
                "bounded_text_char_count": len(str(bounded_text)),
            }
        )
    else:
        base.update(
            {
                "read_error_code": material.get("read_error_code") or status,
                "failure_reason": material.get("failure_reason")
                or "fixture follow-up material did not provide readable support",
            }
        )
        base.pop("http_status", None)
    extra = {
        key: value
        for key, value in material.items()
        if key
        not in {
            "candidate_id",
            "candidate_digest",
            "run_id",
            "request_id",
        }
    }
    merged = {**base, **extra}
    if merged.get("fetch_read_status") != "readable":
        for key in (
            "bounded_text",
            "bounded_text_sanitized",
            "bounded_text_bounded",
            "bounded_text_char_count",
        ):
            merged.pop(key, None)
    return merged


def _support_proposal(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "component_id": record["component_id"],
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "proposal_summary": "Follow-up fixture evidence supports the missing component.",
        "reason": "fixture-backed Analyst re-pass over new custody identity",
    }


def _analysis_gap_proposal(
    record: Mapping[str, Any],
    kind: str,
    *,
    information_needed: str,
) -> dict[str, Any]:
    return {
        "proposal_kind": "analysis_gap",
        "gap_kind": kind,
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "component_id": record["component_id"],
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "information_needed": information_needed,
        "proposed_search_direction": "Keep the component blocked and seek a better follow-up source.",
        "proposed_query_hint": f"{kind} governed follow-up search fixture",
        "required_source_class_hint": "official_current_rules",
        "required_source_tier_hint": "primary",
        "required_currentness_hint": "current",
        "priority_hint": "high",
    }


def _custody_records(ledger_projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    custody = _safe_mapping(ledger_projection.get("fetch_read_candidate_custody"))
    return [
        dict(record)
        for record in custody.get("fetch_read_candidate_custody_records") or ()
        if isinstance(record, Mapping)
    ]


def _filter_records_by_handoff_digest(
    records: Sequence[Mapping[str, Any]],
    *,
    followup_handoff_digest: str | None,
) -> list[dict[str, Any]]:
    digest = _clean_token(followup_handoff_digest, limit=128)
    if not digest:
        return [dict(record) for record in records]
    filtered = [
        dict(record)
        for record in records
        if _clean_token(record.get("search_executor_handoff_digest"), limit=128)
        == digest
    ]
    if not filtered:
        raise FollowupSearchAuthorizationLoopError(
            "follow-up reentry analysis found no custody records for authorized work"
        )
    return filtered


def _ledger_projection_for_records(
    ledger_projection: Mapping[str, Any],
    *,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    projection = _safe_mapping(ledger_projection)
    custody = _safe_mapping(projection.get("fetch_read_candidate_custody"))
    custody["fetch_read_candidate_custody_records"] = [dict(record) for record in records]
    custody["custody_record_count"] = len(records)
    custody["readable_record_count"] = sum(
        1 for record in records if record.get("fetch_read_status") == "readable"
    )
    custody["unreadable_record_count"] = sum(
        1 for record in records if record.get("fetch_read_status") != "readable"
    )
    projection["fetch_read_candidate_custody"] = custody
    return projection


def _contract_ref_from_custody(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    for record in records:
        ref = _safe_mapping(record.get("current_answer_contract_ref"))
        digest = (
            ref.get("contract_digest")
            or record.get("current_answer_contract_digest")
        )
        version = ref.get("contract_version")
        if digest and version:
            return {
                "source": ref.get("source") or "current_answer_contract",
                "contract_version": version,
                "contract_digest": digest,
            }
    raise FollowupSearchAuthorizationLoopError(
        "follow-up reentry analysis requires current_answer_contract custody lineage"
    )


def _initial_component_ref(run_kernel: Any) -> Mapping[str, Any]:
    components = run_kernel.state.initial_answer_contract["accepted_answer_component_refs"]
    if not components:
        raise FollowupSearchAuthorizationLoopError(
            "follow-up coverage reduction requires accepted answer component refs"
        )
    return components[0]


def _latest_work_identity(projection: Mapping[str, Any]) -> dict[str, Any]:
    latest = _safe_mapping(projection.get("latest_authorization"))
    latest_handoff = latest.get("handoff_id")
    for item in reversed(_safe_list(projection.get("authorized_work_identities"))):
        work = _safe_mapping(item)
        if work.get("handoff_id") == latest_handoff:
            return work
    raise FollowupSearchAuthorizationLoopError(
        "follow-up authorization projection has no authorized work identity"
    )


def _has_support_finding(packet: Mapping[str, Any]) -> bool:
    report = _safe_mapping(packet.get("analyst_report"))
    return any(
        isinstance(finding, Mapping)
        and finding.get("proposal_kind") == "possible_support_proposal"
        for finding in report.get("findings") or ()
    )


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_token(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_token(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER",
    "FollowupSearchAuthorizationLoopError",
    "FollowupSearchAuthorizationResult",
    "FollowupSearchReentryResult",
    "authorize_followup_search_work",
    "build_fixture_fetch_read_content_packet",
    "build_fixture_search_result_candidate_packet",
    "build_followup_reentry_analysis_packet",
    "reduce_component_coverage_from_admitted_followup_support",
    "run_fixture_followup_search_reentry_loop",
    "unresolved_component_posture_from_analysis_packet",
]
