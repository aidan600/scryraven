"""Consume retained custody/content into current-path semantic coverage.

This module is product-owned support for the default-off semantic coverage
status path. It consumes retained ``FetchReadContentPacket`` bounded sanitized
content and EvidenceLedger custody, creates an existing
``possible_support_proposal`` Analyst finding shape, then uses the existing
SemanticObservation admission bridge and ComponentCoverage reducer.

It does not call providers, brokers, search, fetch/read, retrieval, models,
scripts, citation rendering, Sufficiency, FAP, Author, or answer text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_record import (
    ComponentCoverageRecord,
    ConflictPosture,
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
from core.evidence_ledger_candidate_custody import EvidenceLedgerCandidateCustodyError
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (
    EvidenceRelativeAnalysisPacketError,
    build_evidence_relative_analysis_packet,
    evidence_relative_analysis_packet_ref_from_packet,
)
from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_observation_admission_bridge import (
    SemanticObservationAdmissionBridgeError,
    SemanticObservationAdmissionBridgeResult,
    admit_semantic_observations_from_analysis_support_findings,
)

RETAINED_CUSTODY_ANALYST_SUPPORT_PHASE = (
    "AG-SEMANTIC-COVERAGE-CONSUMER-REPAIR-01"
)
SUPPORTED_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
SUPPORTED_SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"

BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING = (
    "BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING"
)
BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER = (
    "BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER"
)
BLOCKED_SEMANTIC_OBSERVATION_ADMISSION = (
    "BLOCKED_SEMANTIC_OBSERVATION_ADMISSION"
)
BLOCKED_COMPONENT_COVERAGE_BINDING = "BLOCKED_COMPONENT_COVERAGE_BINDING"
BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING = (
    "BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING"
)


class RetainedCustodyAnalystSupportProposalError(ValueError):
    """Raised when retained custody cannot be safely consumed."""

    def __init__(
        self,
        blocker: str,
        detail: str,
        *,
        next_surface: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail
        self.next_surface = next_surface or _next_surface_for(blocker)


@dataclass(frozen=True, slots=True)
class RetainedCustodySemanticCoverageResult:
    """Compact result for the status path; not a durable product packet."""

    support_proposal: Mapping[str, Any]
    evidence_relative_analysis_packet: Mapping[str, Any]
    semantic_admission_result: SemanticObservationAdmissionBridgeResult
    component_coverage_projection: Mapping[str, Any]
    retained_contract_ref: Mapping[str, Any]
    compact_contract_reconstruction_ref: Mapping[str, Any]
    evidence_ledger_projection: Mapping[str, Any]

    @property
    def analyst_finding(self) -> Mapping[str, Any]:
        return self.semantic_admission_result.analyst_finding

    @property
    def analysis_packet_ref(self) -> Mapping[str, Any]:
        return evidence_relative_analysis_packet_ref_from_packet(
            self.evidence_relative_analysis_packet
        )

    @property
    def semantic_observation_ref(self) -> dict[str, Any]:
        observation = self.semantic_admission_result.semantic_observation
        return {
            "observation_id": observation.observation_id,
            "observation_digest": observation.observation_digest,
            "content_refs": list(observation.content_refs),
            "evidence_refs": list(observation.evidence_refs),
        }

    @property
    def component_coverage_ref(self) -> dict[str, Any]:
        projection = _safe_mapping(self.component_coverage_projection)
        return _without_empty(
            {
                "coverage_record_id": projection.get("coverage_record_id"),
                "coverage_record_digest": projection.get("coverage_record_digest"),
                "coverage_state": projection.get("coverage_state"),
                "semantic_support_status": projection.get(
                    "semantic_support_status"
                ),
                "source_obligation_status": projection.get(
                    "source_obligation_status"
                ),
            }
        )


def build_retained_custody_semantic_coverage(
    *,
    fetch_read_content_packet: Mapping[str, Any],
    expected_candidate_id: str | None = None,
    expected_reference_id: str | None = None,
) -> RetainedCustodySemanticCoverageResult:
    """Build one retained-content Analyst proposal and reduce coverage."""

    try:
        fetch_packet = validate_fetch_read_content_packet(fetch_read_content_packet)
        reference = _selected_readable_reference(
            fetch_packet,
            expected_candidate_id=expected_candidate_id,
            expected_reference_id=expected_reference_id,
        )
        _require_supported_lane(reference)
        _require_retained_bounded_content(reference)

        run_kernel = RunKernel.start(
            run_id=str(fetch_packet["run_id"]),
            request_id=str(fetch_packet["request_id"]),
        )
        contract_ref = _contract_ref(reference)
        compact_contract = _compact_retained_contract(
            run_id=str(fetch_packet["run_id"]),
            request_id=str(fetch_packet["request_id"]),
            contract_ref=contract_ref,
            reference=reference,
        )
        _install_compact_contract(run_kernel, compact_contract)
        ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
            run_kernel=run_kernel,
            fetch_read_content_packet=fetch_packet,
        )
    except RetainedCustodyAnalystSupportProposalError:
        raise
    except (FetchReadContentReferenceError, EvidenceLedgerCandidateCustodyError) as exc:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
            str(exc),
        ) from exc
    except (KeyError, RunKernelTransitionError, ValueError) as exc:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
            f"retained custody setup failed: {exc}",
        ) from exc

    try:
        support_proposal = _source_bound_support_proposal(
            reference=reference,
            evidence_ledger_projection=ledger_projection,
        )
        analysis_packet = build_evidence_relative_analysis_packet(
            evidence_ledger_projection=_analysis_ledger_projection(ledger_projection),
            analyst_proposal_records=[support_proposal],
            run_id=run_kernel.state.run_id,
            request_id=run_kernel.state.request_id,
            current_answer_contract_ref=contract_ref,
            current_answer_contract_digest=contract_ref["contract_digest"],
        )
    except (
        EvidenceRelativeAnalysisPacketError,
        RetainedCustodyAnalystSupportProposalError,
    ) as exc:
        detail = str(exc)
        blocker = (
            exc.blocker
            if isinstance(exc, RetainedCustodyAnalystSupportProposalError)
            else BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER
        )
        raise RetainedCustodyAnalystSupportProposalError(
            blocker,
            detail,
        ) from exc

    try:
        findings = _safe_list(_safe_mapping(analysis_packet.get("analyst_report")).get("findings"))
        if len(findings) != 1:
            raise SemanticObservationAdmissionBridgeError(
                "retained Analyst proposal did not create exactly one finding"
            )
        admitted = admit_semantic_observations_from_analysis_support_findings(
            run_kernel=run_kernel,
            evidence_relative_analysis_packet=analysis_packet,
            fetch_read_content_packet=fetch_packet,
            finding_ids=(str(findings[0]["finding_id"]),),
        )
        if len(admitted) != 1:
            raise SemanticObservationAdmissionBridgeError(
                "retained Analyst support proposal did not admit exactly one observation"
            )
        admission_result = admitted[0]
    except (SemanticObservationAdmissionBridgeError, RunKernelTransitionError) as exc:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_SEMANTIC_OBSERVATION_ADMISSION,
            str(exc),
        ) from exc

    try:
        coverage_projection = _reduce_component_coverage(
            run_kernel=run_kernel,
            admission_result=admission_result,
        )
    except (RunKernelTransitionError, ValueError) as exc:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_COMPONENT_COVERAGE_BINDING,
            str(exc),
        ) from exc

    return RetainedCustodySemanticCoverageResult(
        support_proposal=support_proposal,
        evidence_relative_analysis_packet=analysis_packet,
        semantic_admission_result=admission_result,
        component_coverage_projection=coverage_projection,
        retained_contract_ref=contract_ref,
        compact_contract_reconstruction_ref={
            "compact_contract_reconstructed": True,
            "reconstruction_source": "retained compact current_answer_contract_ref",
            "contract_digest": compact_contract["accepted_contract_digest"],
            "component_id": SUPPORTED_COMPONENT_ID,
            "component_digest": compact_contract["accepted_answer_component_refs"][0][
                "component_digest"
            ],
        },
        evidence_ledger_projection=ledger_projection,
    )


def _selected_readable_reference(
    fetch_packet: Mapping[str, Any],
    *,
    expected_candidate_id: str | None,
    expected_reference_id: str | None,
) -> dict[str, Any]:
    references = [
        _safe_mapping(item)
        for item in _safe_list(fetch_packet.get("reference_records"))
        if isinstance(item, Mapping)
    ]
    if not references:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
            "retained fetch/read packet has no sanitized content references",
        )
    for reference in references:
        if reference.get("fetch_read_status") != "readable":
            continue
        if expected_candidate_id and reference.get("candidate_id") != expected_candidate_id:
            continue
        if expected_reference_id and reference.get("reference_id") != expected_reference_id:
            continue
        return reference
    raise RetainedCustodyAnalystSupportProposalError(
        BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
        "retained fetch/read packet has no matching readable bounded content reference",
    )


def _require_supported_lane(reference: Mapping[str, Any]) -> None:
    component_id = _clean_token(reference.get("component_id"), limit=260)
    source_ids = _text_tuple(reference.get("source_obligation_candidate_ids"), limit=260)
    if component_id != SUPPORTED_COMPONENT_ID:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING,
            "retained reference is not bound to the adult passport fee component",
        )
    if SUPPORTED_SOURCE_OBLIGATION_ID not in source_ids:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING,
            "retained reference is not bound to the official passport fee source obligation",
        )


def _require_retained_bounded_content(reference: Mapping[str, Any]) -> None:
    if reference.get("bounded_text_sanitized") is not True:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
            "retained bounded content is not marked sanitized",
        )
    if reference.get("bounded_text_bounded") is not True:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
            "retained bounded content is not marked bounded",
        )
    if not _clean_text(reference.get("bounded_text"), limit=20_000):
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
            "retained bounded sanitized content is missing",
        )
    if not _clean_token(reference.get("excerpt_digest"), limit=128):
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
            "retained bounded sanitized content digest is missing",
        )
    selection = _safe_mapping(reference.get("bounded_text_selection"))
    required_count = _bounded_int(selection.get("required_anchor_count"))
    matched_count = _bounded_int(selection.get("matched_anchor_count"))
    missing_anchors = _safe_list(selection.get("missing_anchors"))
    if required_count > 0 and (missing_anchors or matched_count < required_count):
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
            "retained bounded content selection did not match required anchors",
        )


def _source_bound_support_proposal(
    *,
    reference: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    record = _custody_record_for_reference(
        evidence_ledger_projection=evidence_ledger_projection,
        reference_id=str(reference.get("reference_id") or ""),
    )
    for key in (
        "reference_id",
        "reference_digest",
        "candidate_id",
        "candidate_digest",
        "search_result_candidate_packet_digest",
    ):
        if _clean_token(record.get(key), limit=320) != _clean_token(
            reference.get(key),
            limit=320,
        ):
            raise RetainedCustodyAnalystSupportProposalError(
                BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
                f"retained custody/reference {key} mismatch",
            )
    for record_key, reference_key in (
        ("fetch_read_content_packet_id", "packet_id"),
        ("fetch_read_content_packet_digest", "packet_digest"),
    ):
        if _clean_token(record.get(record_key), limit=320) != _clean_token(
            reference.get(reference_key),
            limit=320,
        ):
            raise RetainedCustodyAnalystSupportProposalError(
                BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
                f"retained custody/reference {record_key} mismatch",
            )
    if _clean_token(record.get("component_id"), limit=260) != SUPPORTED_COMPONENT_ID:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING,
            "EvidenceLedger custody is not bound to the adult passport fee component",
        )
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_id": record.get("fetch_read_content_packet_id"),
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_id": record.get(
            "search_result_candidate_packet_id"
        ),
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "search_result_candidate_record_digest": record.get(
            "search_result_candidate_record_digest"
        ),
        "component_id": SUPPORTED_COMPONENT_ID,
        "source_obligation_candidate_ids": [SUPPORTED_SOURCE_OBLIGATION_ID],
        "proposal_summary": (
            "Retained bounded sanitized passport-fee source content supports the "
            "adult U.S. passport book renewal fee component."
        ),
        "reason": (
            "Readable retained bounded sanitized content is source-bound to the "
            "passport-fee component and official-source obligation lane."
        ),
    }


def _reduce_component_coverage(
    *,
    run_kernel: RunKernel,
    admission_result: SemanticObservationAdmissionBridgeResult,
) -> dict[str, Any]:
    observation = admission_result.semantic_observation
    content_ref = admission_result.sanitized_content_reference
    component_ref = _component_ref(run_kernel, observation.answer_component_id)
    record = ComponentCoverageRecord(
        record_id=(
            "coverage:retained-passport-fee:"
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
        evidence_ledger_binding=_ledger_binding(run_kernel),
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
        conflict_posture=ConflictPosture.UNKNOWN,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=(
            "source obligation remains unsatisfied and lineage-only",
            "coverage is bounded to the retained passport-fee lane only",
        ),
        required_caveats=(
            "Do not upgrade ComponentCoverage to source-obligation satisfaction.",
            "Do not upgrade semantic support to citation eligibility or rendering.",
        ),
        prohibited_upgrades=(
            "Do not create Sufficiency, FAP, Author, citation, answer, or "
            "product-correctness claims.",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        lineage=CoverageLineage(
            created_by=RETAINED_CUSTODY_ANALYST_SUPPORT_PHASE,
            created_from=(
                "retained_fetch_read_content_packet",
                "evidence_ledger_candidate_content_custody",
                "evidence_relative_analysis_packet",
                "admitted_semantic_observation",
            ),
        ),
        metadata={
            "phase": RETAINED_CUSTODY_ANALYST_SUPPORT_PHASE,
            "runtime_consumer": "proplex.live_semantic_coverage_status",
            "semantic_support_source": "retained_bounded_sanitized_content",
            "source_obligation_satisfied": False,
            "citation_eligible": False,
        },
    ).require_valid()
    action = run_kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={"phase": RETAINED_CUSTODY_ANALYST_SUPPORT_PHASE},
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


def _install_compact_contract(
    run_kernel: RunKernel,
    compact_contract: Mapping[str, Any],
) -> None:
    projection = _compact_contract_projection(compact_contract)
    run_kernel.state.initial_answer_contract = dict(compact_contract)
    run_kernel.state.initial_answer_contract_projection = projection
    run_kernel.state.initial_answer_contract_history.append(dict(projection))
    run_kernel.state.current_answer_contract = dict(compact_contract)
    run_kernel.state.current_answer_contract_projection = dict(projection)
    run_kernel.state.current_answer_contract_history.append(dict(projection))


def _compact_retained_contract(
    *,
    run_id: str,
    request_id: str,
    contract_ref: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    contract_version = _required_token(
        contract_ref.get("contract_version"),
        "retained contract ref requires contract_version",
    )
    contract_digest = _required_token(
        contract_ref.get("contract_digest"),
        "retained contract ref requires contract_digest",
        limit=128,
    )
    component_digest = _digest_json(
        {
            "contract_digest": contract_digest,
            "component_id": SUPPORTED_COMPONENT_ID,
            "source_obligation_candidate_ids": [SUPPORTED_SOURCE_OBLIGATION_ID],
            "reference_digest": reference.get("reference_digest"),
        }
    )
    qmr_digest = _digest_json(
        {
            "contract_digest": contract_digest,
            "component_digest": component_digest,
            "request_id": request_id,
            "retained_lane": "adult-passport-book-renewal-fee",
        }
    )
    return {
        "schema_version": "retained_compact_initial_answer_contract_v1",
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_id,
        "request_id": request_id,
        "accepted_contract_version": contract_version,
        "accepted_contract_digest": contract_digest,
        "parent_question_meaning_record_id": (
            f"retained-qmr:{request_id}:adult-passport-fee"
        ),
        "parent_question_meaning_record_digest": qmr_digest,
        "parent_proposal_schema_version": "retained_compact_contract_ref",
        "accepted_answer_component_refs": [
            {
                "component_id": SUPPORTED_COMPONENT_ID,
                "component_revision": "retained-passport-fee-1",
                "component_digest": component_digest,
                "requirement_posture": "required",
                "materiality": "material",
                "allowed_support_kinds": ["direct"],
                "source_obligation_candidate_ids": [
                    SUPPORTED_SOURCE_OBLIGATION_ID
                ],
                "mandatory_caveats": [
                    "Source-obligation satisfaction remains closed."
                ],
                "prohibited_upgrades": [
                    "Do not claim citation eligibility, source-obligation "
                    "satisfaction, Sufficiency, FAP, Author, answer text, or "
                    "product correctness."
                ],
            }
        ],
        "accepted_semantic_slot_refs": [],
        "material_ambiguity_count": 0,
        "material_ambiguity_preserved": True,
        "material_ambiguity_resolved": False,
        "retained_compact_contract_reconstruction": True,
        "retained_contract_ref": dict(contract_ref),
    }


def _compact_contract_projection(compact_contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": compact_contract.get("run_id"),
        "request_id": compact_contract.get("request_id"),
        "accepted_contract_version": compact_contract.get(
            "accepted_contract_version"
        ),
        "accepted_contract_digest": compact_contract.get("accepted_contract_digest"),
        "accepted_answer_component_refs": [
            dict(item)
            for item in compact_contract.get("accepted_answer_component_refs") or ()
            if isinstance(item, Mapping)
        ],
        "retained_compact_contract_reconstruction": True,
    }


def _contract_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    ref = _safe_mapping(reference.get("current_answer_contract_ref"))
    version = _clean_token(ref.get("contract_version"), limit=160)
    digest = _clean_token(
        ref.get("contract_digest")
        or reference.get("current_answer_contract_digest"),
        limit=128,
    )
    if not version or not digest:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING,
            "retained bounded content lacks current contract ref/digest",
        )
    return {
        "source": ref.get("source") or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _analysis_ledger_projection(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    records = [
        _safe_mapping(item)
        for item in _safe_list(custody.get("fetch_read_candidate_custody_records"))
        if isinstance(item, Mapping)
    ]
    if not records:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
            "EvidenceLedger projection has no retained fetch/read custody records",
        )
    return {
        "fetch_read_candidate_custody": {
            key: custody.get(key)
            for key in (
                "trace_key",
                "custody_record_count",
                "readable_record_count",
                "fetch_read_candidate_custody_records",
            )
            if key in custody
        }
    }


def _custody_record_for_reference(
    *,
    evidence_ledger_projection: Mapping[str, Any],
    reference_id: str,
) -> dict[str, Any]:
    custody = _safe_mapping(
        evidence_ledger_projection.get("fetch_read_candidate_custody")
    )
    records = [
        _safe_mapping(item)
        for item in _safe_list(custody.get("fetch_read_candidate_custody_records"))
        if isinstance(item, Mapping)
    ]
    for record in records:
        if record.get("reference_id") == reference_id:
            if record.get("fetch_read_status") != "readable":
                raise RetainedCustodyAnalystSupportProposalError(
                    BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING,
                    "retained EvidenceLedger custody is not readable",
                )
            return record
    raise RetainedCustodyAnalystSupportProposalError(
        BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
        "EvidenceLedger custody record is missing for retained reference",
    )


def _component_ref(run_kernel: RunKernel, component_id: str) -> dict[str, Any]:
    for ref in run_kernel.state.initial_answer_contract.get(
        "accepted_answer_component_refs",
        [],
    ):
        if isinstance(ref, Mapping) and ref.get("component_id") == component_id:
            return dict(ref)
    raise RetainedCustodyAnalystSupportProposalError(
        BLOCKED_COMPONENT_COVERAGE_BINDING,
        "ComponentCoverage requires the retained component in accepted contract",
    )


def _ledger_binding(run_kernel: RunKernel) -> EvidenceLedgerSnapshotBinding:
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        str(ref["observation_id"])
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


def _next_surface_for(blocker: str) -> str:
    return {
        BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING: (
            "retained bounded sanitized content"
        ),
        BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING: (
            "component/source-obligation retained lane binding"
        ),
        BLOCKED_SEMANTIC_OBSERVATION_ADMISSION: (
            "SemanticObservation admission"
        ),
        BLOCKED_COMPONENT_COVERAGE_BINDING: "ComponentCoverage binding",
    }.get(blocker, "Analyst support proposal consumer")


def _required_token(value: Any, label: str, *, limit: int = 160) -> str:
    token = _clean_token(value, limit=limit)
    if not token:
        raise RetainedCustodyAnalystSupportProposalError(
            BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER,
            label,
        )
    return token


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, depth=depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    return _clean_text(value, limit=300)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


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


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        token = _clean_token(value, limit=limit)
        return (token,) if token else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    for item in value:
        token = _clean_token(item, limit=limit)
        if token:
            out.append(token)
    return tuple(out)


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


__all__ = [
    "BLOCKED_ANALYST_SUPPORT_PROPOSAL_CONSUMER",
    "BLOCKED_COMPONENT_COVERAGE_BINDING",
    "BLOCKED_COMPONENT_SOURCE_OBLIGATION_BINDING",
    "BLOCKED_RETAINED_BOUNDED_CONTENT_MISSING",
    "BLOCKED_SEMANTIC_OBSERVATION_ADMISSION",
    "RetainedCustodyAnalystSupportProposalError",
    "RetainedCustodySemanticCoverageResult",
    "build_retained_custody_semantic_coverage",
]
