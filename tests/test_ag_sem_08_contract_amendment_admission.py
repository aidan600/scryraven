from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.component_coverage_record import (
    ComponentCoverageRecord,
    ConflictPosture,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
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
from core.contract_amendment_admission_runtime import (
    CONTRACT_AMENDMENT_ADMISSION_SCHEMA_VERSION,
    CONTRACT_AMENDMENT_ADMISSION_STAGE,
    ContractAmendmentAdmissionError,
    build_contract_amendment_admission_projection,
    build_contract_amendment_admission_state,
)
from core.contract_amendment_record import (
    AffectedComponentRef,
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    CoverageInvalidationCandidateRef,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    StaleCoverageCandidatePosture,
    UserConfirmationPosture,
    WeakeningPosture,
)
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    QuestionMeaningRecord,
    RequirementPosture,
    ResolverKind,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SupportKind,
)
from core.semantic_observation_foundation import (
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "contract_amendment_admission_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-08-offline"
REQUEST_ID = "request:sem-08"
COMPONENT_ID = "component:reported-total"
EVIDENCE_ID = "evidence:public-record-notice"
COVERAGE_RECORD_ID = "coverage:reported-total"
AMENDMENT_RECORD_ID = "amendment:reported-total-caveat"
SOURCE_REQUIREMENT_ID = "source_requirement:reported_total"


def _slot() -> SemanticSlot:
    return SemanticSlot(
        slot_id="slot:reporting-period",
        slot_kind=SemanticSlotKind.TIME_PERIOD,
        status=SemanticSlotStatus.EXPLICIT,
        selected_value="2026",
        materiality=Materiality.MATERIAL,
    )


def _component() -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=COMPONENT_ID,
        component_revision="1",
        user_facing_label="Reported total",
        user_facing_question="What is the reported total for the requested period?",
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=("state the bounded value", "bind it to evidence"),
        semantic_slot_ids=("slot:reporting-period",),
        source_obligation_candidate_ids=(
            SOURCE_REQUIREMENT_ID,
        ),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        materiality=Materiality.MATERIAL,
    )


def _qmr() -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:reported-total",
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-08",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-08-test",
        intent="Answer the reported-total question.",
        requested_output="Concise answer with primary-source support.",
        semantic_slots=(_slot(),),
        answer_components=(_component(),),
        metadata={"safe_note": "kept"},
    ).require_valid()


def _accept_contract(kernel: RunKernel) -> dict[str, object]:
    qmr = _qmr()
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=qmr.record_id,
        parent_proposal_digest=qmr.record_digest,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        status=RunStageStatus.COMPLETED,
        payload={"question_meaning_record": qmr.to_dict()},
    )
    kernel.reduce(observation)
    return kernel.state.initial_answer_contract


def _seed_evidence_ledger(kernel: RunKernel, *, candidate_id: str = EVIDENCE_ID) -> None:
    accepted = kernel.state.initial_answer_contract
    kernel.state.evidence_ledger.reduce_observation(
        {
            "observation_id": f"evidence-seed:{candidate_id}",
            "observation_source": "offline_fixture",
            "requirements": [
                {
                    "requirement_id": SOURCE_REQUIREMENT_ID,
                    "requirement_kind": "official_current",
                    "component_id": COMPONENT_ID,
                    "source_obligation_id": SOURCE_REQUIREMENT_ID,
                    "run_id": RUN_ID,
                    "request_id": REQUEST_ID,
                    "answer_contract_version": accepted[
                        "accepted_contract_version"
                    ],
                    "answer_contract_digest": accepted[
                        "accepted_contract_digest"
                    ],
                    "required_source_class": "primary_source_documents",
                    "required_source_tier": "primary",
                    "required_currentness": "current",
                }
            ],
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "url": "https://example.org/public-record-notice",
                    "title": "Public record notice",
                    "source_class": "primary_source_documents",
                    "source_tier": "primary",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "fetchable_status": "fetchable",
                    "disposition": "accepted",
                    "record_kind": "fact",
                    "eligible_for_stronger_obligation": True,
                    "final_evidence_eligible": True,
                    "requirement_id": SOURCE_REQUIREMENT_ID,
                }
            ],
        }
    )


def _content_ref(accepted: dict[str, object]) -> SanitizedContentReference:
    component_ref = accepted["accepted_answer_component_refs"][0]
    return SanitizedContentReference(
        content_ref_id="content:reported-total-value",
        evidence_ref_id=EVIDENCE_ID,
        admitted_evidence_ref=EVIDENCE_ID,
        source_id="source:public-record",
        source_digest="source-digest-sem-08",
        source_url="https://example.org/public-record-notice",
        source_title="Public record notice",
        source_domain="example.org",
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text="The 2026 reported total is 1,284 records.",
        page=1,
        section="Annual totals",
        char_range_start=10,
        char_range_end=60,
        extraction_method="offline_fixture",
        worker_kind="bounded_reader",
        currentness="current_for_2026",
        observed_at="2026-06-22T00:00:00Z",
        metadata={"safe_note": "kept"},
    )


def _observation(accepted: dict[str, object]) -> SemanticObservation:
    component_ref = accepted["accepted_answer_component_refs"][0]
    return SemanticObservation(
        observation_id="observation:supports-reported-total",
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        contract_version=accepted["accepted_contract_version"],
        contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        evidence_refs=(EVIDENCE_ID,),
        content_refs=("content:reported-total-value",),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value="1,284 records",
        normalization_fit="annual record counts",
        scope_fit="calendar year 2026",
        assumption_fit="uses source wording without runtime admission",
        inference_depth=0,
        metadata={"safe_review_note": "passive observation"},
    )


def _admit(
    kernel: RunKernel,
    accepted: dict[str, object],
    observation: SemanticObservation,
    content_ref: SanitizedContentReference,
) -> None:
    component_ref = accepted["accepted_answer_component_refs"][0]
    action = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation.observation_id,
        semantic_observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload={
            "semantic_observation": observation.to_dict(),
            "sanitized_content_references": [content_ref.to_dict()],
        },
    )
    kernel.reduce(reduce_observation)


def _ledger_binding(kernel: RunKernel) -> EvidenceLedgerSnapshotBinding:
    projection = kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        ref["observation_id"]
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, dict) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{RUN_ID}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        source_requirement_ids=(SOURCE_REQUIREMENT_ID,),
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _coverage_record(
    accepted: dict[str, object],
    observation: SemanticObservation,
    content_ref: SanitizedContentReference,
    kernel: RunKernel,
) -> ComponentCoverageRecord:
    component_ref = accepted["accepted_answer_component_refs"][0]
    obs_ref = SemanticObservationCoverageRef(
        observation_id=observation.observation_id,
        observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        support_status="supports",
        support_posture=SupportPosture.DIRECT,
        content_refs=("content:reported-total-value",),
        accepted=True,
    )
    content_binding = ContentReferenceCoverageBinding.from_content_reference(content_ref)
    return ComponentCoverageRecord(
        record_id=COVERAGE_RECORD_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-08",
        accepted_contract_version=accepted["accepted_contract_version"],
        accepted_contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(kernel),
        coverage_state=CoverageState.SATISFIED,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.SATISFIED,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(obs_ref,),
        content_reference_bindings=(content_binding,),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        conflict_posture=ConflictPosture.NONE,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=(),
        required_caveats=("Currentness remains evidence-bound.",),
        prohibited_upgrades=("Do not replace official value with estimate.",),
        followup_need=FollowupNeed.NONE,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        stale=False,
        metadata={"safe_note": "kept"},
    )


def _reduce_coverage(
    kernel: RunKernel,
    accepted: dict[str, object],
    record: ComponentCoverageRecord,
) -> None:
    component_ref = accepted["accepted_answer_component_refs"][0]
    action = kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
        status=RunStageStatus.COMPLETED,
        payload={"component_coverage_record": payload},
    )
    kernel.reduce(reduce_observation)


def _trigger_refs() -> AmendmentTriggerRefs:
    return AmendmentTriggerRefs(
        semantic_observation_refs=("observation:supports-reported-total",),
        evidence_refs=(EVIDENCE_ID,),
        sanitized_content_refs=("content:reported-total-value",),
        component_coverage_refs=(COVERAGE_RECORD_ID,),
        gap_refs=("gap:currentness",),
    )


def _operation(
    *,
    operation_kind: AmendmentOperationKind = AmendmentOperationKind.ADD_CAVEAT,
    payload: dict[str, object] | None = None,
) -> AmendmentOperation:
    return AmendmentOperation(
        operation_id=f"operation:{operation_kind.value}",
        operation_kind=operation_kind,
        operation_payload=payload if payload is not None else {"caveat": "Currentness remains evidence-bound."},
        metadata={"safe_note": "kept"},
    )


def _coverage_candidate(
    kernel: RunKernel | None = None,
    *,
    coverage_record_digest: str | None = None,
    coverage_record_id: str = COVERAGE_RECORD_ID,
    answer_component_id: str = COMPONENT_ID,
    reason: str = "component revision or material slot changed",
) -> CoverageInvalidationCandidateRef:
    digest = coverage_record_digest
    if digest is None and kernel is not None and kernel.state.component_coverage_history:
        digest = str(kernel.state.component_coverage_history[-1]["coverage_record_digest"])
    if digest is None:
        raise ValueError("coverage candidate requires kernel or explicit coverage_record_digest")
    return CoverageInvalidationCandidateRef(
        coverage_record_id=coverage_record_id,
        coverage_record_digest=digest,
        answer_component_id=answer_component_id,
        reason=reason,
    )


def _amendment_record(
    accepted: dict[str, object],
    *,
    trigger_refs: AmendmentTriggerRefs | None = None,
    disposition: ProposalDisposition = ProposalDisposition.PROPOSED,
    materiality: MaterialityPosture = MaterialityPosture.NON_MATERIAL,
    coverage_candidates: tuple[CoverageInvalidationCandidateRef, ...] = (),
    stale_posture: StaleCoverageCandidatePosture = StaleCoverageCandidatePosture.NOT_APPLICABLE,
    accepted_contract_ref: str | None = None,
    rejection_reasons: tuple[str, ...] = (),
    blocking_reasons: tuple[str, ...] = (),
    operations: tuple[AmendmentOperation, ...] | None = None,
    affected_component_refs: tuple[AffectedComponentRef, ...] | None = None,
) -> ContractAmendmentRecord:
    component_ref = accepted["accepted_answer_component_refs"][0]
    contract_version = str(accepted["accepted_contract_version"])
    default_affected = (
        AffectedComponentRef(
            component_id=component_ref["component_id"],
            component_revision=component_ref["component_revision"],
            component_digest=component_ref["component_digest"],
        ),
    )
    return ContractAmendmentRecord(
        amendment_record_id=AMENDMENT_RECORD_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-08",
        parent_contract_version=contract_version,
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        parent_question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        accepted_contract_ref=accepted_contract_ref
        if accepted_contract_ref is not None
        else f"contract:{contract_version}:accepted",
        trigger_refs=trigger_refs if trigger_refs is not None else _trigger_refs(),
        affected_component_refs=(
            affected_component_refs if affected_component_refs is not None else default_affected
        ),
        operations=operations if operations is not None else (_operation(),),
        materiality=materiality,
        user_confirmation_posture=UserConfirmationPosture.NOT_REQUIRED,
        monotonicity=MonotonicityPosture.PRESERVES,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=disposition,
        candidate_invalidated_coverage_refs=coverage_candidates,
        stale_coverage_candidate_posture=stale_posture,
        required_caveats=("Currentness remains evidence-bound.",),
        prohibited_upgrades=("Do not promote the candidate amendment to accepted authority.",),
        rejection_reasons=rejection_reasons,
        blocking_reasons=blocking_reasons,
        metadata={"safe_note": "kept", "raw_prompt": "SENTINEL_RAW_PROMPT"},
    )


def _reseal_amendment(record: ContractAmendmentRecord) -> dict[str, object]:
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    return payload


def _start_admitted_kernel_with_coverage() -> tuple[RunKernel, dict[str, object], ContractAmendmentRecord]:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    _admit(kernel, accepted, observation, content_ref)
    coverage = _coverage_record(accepted, observation, content_ref, kernel)
    _reduce_coverage(kernel, accepted, coverage)
    record = _amendment_record(accepted)
    return kernel, accepted, record


def _admit_amendment(
    kernel: RunKernel,
    accepted: dict[str, object],
    record: ContractAmendmentRecord,
    *,
    amendment_record_id: str | None = None,
    amendment_record_digest: str | None = None,
    payload: dict[str, object] | None = None,
) -> Observation:
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=amendment_record_id if amendment_record_id is not None else record.amendment_record_id,
        amendment_record_digest=(
            amendment_record_digest if amendment_record_digest is not None else record.record_digest
        ),
    )
    if payload is None:
        payload = {"contract_amendment_record": _reseal_amendment(record)}
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    kernel.reduce(reduce_observation)
    return reduce_observation


def test_authorized_admission_creates_canonical_state_projection_history() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()

    _admit_amendment(kernel, accepted, record)

    state = kernel.state.contract_amendment_admission_state
    projection = kernel.state.contract_amendment_admission_projection
    assert state["schema_version"] == CONTRACT_AMENDMENT_ADMISSION_SCHEMA_VERSION
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"]
    assert state["amendment_record_id"] == AMENDMENT_RECORD_ID
    assert state["amendment_record_digest"] == record.record_digest
    assert state["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert state["disposition"] == "proposed"
    assert state["admission_digest"]
    assert state["lineage"]["created_by"] == "RunKernel.ContractAmendmentAdmission"
    assert state["lineage"]["reducer_action_id"] == state["authorized_action_id"]
    assert kernel.state.contract_amendment_admission_history[-1] == projection
    assert kernel.state.projections[CONTRACT_AMENDMENT_ADMISSION_STAGE] == projection
    assert kernel.state.stage_statuses[CONTRACT_AMENDMENT_ADMISSION_STAGE] is RunStageStatus.COMPLETED


def test_admission_requires_accepted_initial_answer_contract() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    with pytest.raises(RunKernelTransitionError, match="accepted initial answer contract"):
        kernel.authorize_contract_amendment_admission(
            amendment_record_id=AMENDMENT_RECORD_ID,
            amendment_record_digest="d" * 64,
        )


def test_action_binding_for_record_id_digest_contract_is_exact() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    with pytest.raises(RunKernelTransitionError, match="amendment_record_id binding"):
        _admit_amendment(kernel, accepted, record, amendment_record_id="amendment:not-this")

    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    with pytest.raises(RunKernelTransitionError, match="amendment_record_digest binding"):
        _admit_amendment(kernel, accepted, record, amendment_record_digest="0" * 64)


def test_amendment_record_foreign_run_id_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    foreign = replace(record, run_id="run:foreign")
    payload = _reseal_amendment(foreign)
    with pytest.raises(RunKernelTransitionError, match="run_id does not match"):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": payload})


def test_amendment_record_foreign_request_id_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    foreign = replace(record, request_id="request:foreign")
    payload = _reseal_amendment(foreign)
    with pytest.raises(RunKernelTransitionError, match="request_id does not match"):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": payload})


def test_amendment_record_matching_run_and_request_admits_successfully() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    assert record.run_id == RUN_ID
    assert record.request_id == REQUEST_ID
    _admit_amendment(kernel, accepted, record)
    state = kernel.state.contract_amendment_admission_state
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID


def test_recomputed_amendment_record_digest_rejects_tampered_payload() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    tampered = _reseal_amendment(record)
    tampered["required_caveats"] = ["Tampered caveat."]
    with pytest.raises(RunKernelTransitionError, match="amendment record digest does not match"):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": tampered})


def test_parent_contract_version_or_digest_mismatch_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    payload = record.to_dict(include_validation=False)
    payload["parent_contract_digest"] = "f" * 64
    with pytest.raises(
        RunKernelTransitionError,
        match="parent_contract_digest|amendment record digest",
    ):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": payload})

    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    payload = record.to_dict(include_validation=False)
    payload["parent_contract_version"] = "9.9-other"
    with pytest.raises(
        RunKernelTransitionError,
        match="parent_contract_version|amendment record digest",
    ):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": payload})


def test_unadmitted_semantic_observation_trigger_ref_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    bad_trigger = AmendmentTriggerRefs(
        semantic_observation_refs=("observation:not-admitted",),
        evidence_refs=(EVIDENCE_ID,),
        sanitized_content_refs=("content:reported-total-value",),
        component_coverage_refs=(COVERAGE_RECORD_ID,),
    )
    bad_record = _amendment_record(accepted, trigger_refs=bad_trigger)
    with pytest.raises(RunKernelTransitionError, match="is not admitted"):
        _admit_amendment(kernel, accepted, bad_record)


def test_unreduced_coverage_trigger_ref_is_rejected() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    _admit(kernel, accepted, observation, content_ref)
    record = _amendment_record(accepted)
    with pytest.raises(RunKernelTransitionError, match="is not reduced"):
        _admit_amendment(kernel, accepted, record)


def test_unadmitted_content_ref_trigger_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    bad_trigger = AmendmentTriggerRefs(
        semantic_observation_refs=("observation:supports-reported-total",),
        evidence_refs=(EVIDENCE_ID,),
        sanitized_content_refs=("content:foreign-ref",),
        component_coverage_refs=(COVERAGE_RECORD_ID,),
    )
    bad_record = _amendment_record(accepted, trigger_refs=bad_trigger)
    with pytest.raises(RunKernelTransitionError, match="is not cited"):
        _admit_amendment(kernel, accepted, bad_record)


def test_evidence_ref_absent_from_ledger_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    bad_trigger = AmendmentTriggerRefs(
        semantic_observation_refs=("observation:supports-reported-total",),
        evidence_refs=("evidence:foreign",),
        sanitized_content_refs=("content:reported-total-value",),
        component_coverage_refs=(COVERAGE_RECORD_ID,),
    )
    bad_record = _amendment_record(accepted, trigger_refs=bad_trigger)
    with pytest.raises(RunKernelTransitionError, match="absent from EvidenceLedger custody"):
        _admit_amendment(kernel, accepted, bad_record)


def test_rejected_disposition_may_be_admitted_when_valid() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    rejected = _amendment_record(
        accepted,
        disposition=ProposalDisposition.REJECTED,
        rejection_reasons=("Candidate caveat is not warranted by evidence.",),
    )
    _admit_amendment(kernel, accepted, rejected)
    state = kernel.state.contract_amendment_admission_state
    assert state["disposition"] == "rejected"
    assert state["rejection_reasons"] == ["Candidate caveat is not warranted by evidence."]


def test_blocked_disposition_may_be_admitted_when_valid() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    blocked = _amendment_record(
        accepted,
        disposition=ProposalDisposition.BLOCKED,
        blocking_reasons=("Mode budget exhausted for material amendment.",),
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    blocked = replace(
        blocked,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    _admit_amendment(kernel, accepted, blocked)
    state = kernel.state.contract_amendment_admission_state
    assert state["disposition"] == "blocked"
    assert state["blocking_reasons"] == ["Mode budget exhausted for material amendment."]


def test_exact_amendment_admission_replay_is_mutation_free() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    _admit_amendment(kernel, accepted, record)
    observation_count = len(kernel.state.observations)
    history_before = list(kernel.state.contract_amendment_admission_history)

    replay = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )

    assert replay["status"] == "exact_replay"
    assert replay["work_authorized"] is False
    assert replay["contract_amendment_admission"] == history_before[0]
    assert kernel.state.contract_amendment_admission_history == history_before
    assert len(kernel.state.observations) == observation_count


def test_candidate_invalidated_coverage_refs_remain_represented_only() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    material = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    material = replace(
        material,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    _admit_amendment(kernel, accepted, material)
    candidate = kernel.state.contract_amendment_admission_state["candidate_invalidated_coverage_refs"][0]
    assert candidate["represented_only"] is True
    assert candidate["coverage_invalidation_applied"] is False


def test_no_contract_mutation_coverage_invalidation_or_stale_marking() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    contract_before = json.dumps(kernel.state.initial_answer_contract, sort_keys=True)
    coverage_before = json.dumps(kernel.state.component_coverage_state, sort_keys=True)
    _admit_amendment(kernel, accepted, record)
    assert json.dumps(kernel.state.initial_answer_contract, sort_keys=True) == contract_before
    assert json.dumps(kernel.state.component_coverage_state, sort_keys=True) == coverage_before
    assert kernel.state.component_coverage_state.get("stale") is not True

    projection = kernel.state.contract_amendment_admission_projection
    for flag in (
        "contract_mutation_applied",
        "coverage_invalidation_applied",
        "coverage_marked_stale",
        "initial_answer_contract_mutated",
        "amendment_applied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "search_judgment_decided",
        "query_plan_activated",
        "search_work_plan_activated",
        "followup_authorized",
        "citation_behavior_changed",
        "provider_search_behavior_changed",
        "runtime_behavior_changed",
    ):
        assert projection[flag] is False
    assert projection["live_validation_not_run"] is True


def test_accepted_contract_ref_optional_validation() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    valid = _amendment_record(
        accepted,
        accepted_contract_ref=f"contract:{accepted['accepted_contract_version']}:accepted",
    )
    _admit_amendment(kernel, accepted, valid)
    assert (
        kernel.state.contract_amendment_admission_state["accepted_contract_ref"]
        == f"contract:{accepted['accepted_contract_version']}:accepted"
    )

    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    invalid = _amendment_record(accepted, accepted_contract_ref="contract:wrong:accepted")
    with pytest.raises(RunKernelTransitionError, match="accepted_contract_ref"):
        _admit_amendment(kernel, accepted, invalid)


def test_projection_and_admission_digest_are_deterministic() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    inputs = {
        "amendment_record_id": record.amendment_record_id,
        "amendment_record_digest": record.record_digest,
        "parent_contract_digest": accepted["accepted_contract_digest"],
        "parent_contract_version": accepted["accepted_contract_version"],
        "accepted_contract_digest": accepted["accepted_contract_digest"],
        "accepted_contract_version": accepted["accepted_contract_version"],
        "request_id": REQUEST_ID,
    }
    payload = {"contract_amendment_record": _reseal_amendment(record)}
    state_one = build_contract_amendment_admission_state(
        action_id="action:sem-08-deterministic",
        action_inputs=inputs,
        amendment_payload=payload,
        accepted_contract=accepted,
        admission_history=kernel.state.semantic_observation_admission_history,
        coverage_history=kernel.state.component_coverage_history,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    state_two = build_contract_amendment_admission_state(
        action_id="action:sem-08-deterministic",
        action_inputs=inputs,
        amendment_payload=payload,
        accepted_contract=accepted,
        admission_history=kernel.state.semantic_observation_admission_history,
        coverage_history=kernel.state.component_coverage_history,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    projection_one = build_contract_amendment_admission_projection(admission_state=state_one)
    projection_two = build_contract_amendment_admission_projection(admission_state=state_two)
    assert state_one["admission_digest"] == state_two["admission_digest"]
    assert json.dumps(projection_one, sort_keys=True) == json.dumps(projection_two, sort_keys=True)


def test_sensitive_fields_are_scrubbed_and_closed_authority_is_rejected() -> None:
    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    _admit_amendment(kernel, accepted, record)
    projection = kernel.state.contract_amendment_admission_projection
    assert "raw_prompt" not in json.dumps(projection)

    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    payload = {"contract_amendment_record": _reseal_amendment(record), "sufficiency_judgment": {"x": 1}}
    with pytest.raises(RunKernelTransitionError, match="closed authority fields"):
        _admit_amendment(kernel, accepted, record, payload=payload)

    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    tampered = _reseal_amendment(record)
    tampered["passive"] = False
    with pytest.raises(RunKernelTransitionError, match="must remain passive"):
        _admit_amendment(kernel, accepted, record, payload={"contract_amendment_record": tampered})


def test_builder_requires_accepted_contract() -> None:
    with pytest.raises(ContractAmendmentAdmissionError, match="accepted initial answer contract"):
        build_contract_amendment_admission_state(
            action_id="action:sem-08",
            action_inputs={},
            amendment_payload={"contract_amendment_record": {"amendment_record_id": "x"}},
            accepted_contract={},
            admission_history=[],
            coverage_history=[],
            evidence_ledger_projection={},
            run_id=RUN_ID,
            request_id=REQUEST_ID,
        )


def test_record_failing_validate_is_rejected() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    invalid = _amendment_record(accepted, trigger_refs=AmendmentTriggerRefs())
    with pytest.raises(RunKernelTransitionError, match="trigger ref|trigger_refs"):
        _admit_amendment(kernel, accepted, invalid)


def _secondary_observation(
    accepted: dict[str, object],
    *,
    observation_id: str = "observation:secondary-support",
    content_ref_id: str = "content:secondary-value",
) -> tuple[SemanticObservation, SanitizedContentReference]:
    component_ref = accepted["accepted_answer_component_refs"][0]
    content_ref = SanitizedContentReference(
        content_ref_id=content_ref_id,
        evidence_ref_id=EVIDENCE_ID,
        admitted_evidence_ref=EVIDENCE_ID,
        source_id="source:public-record-secondary",
        source_digest="source-digest-sem-08-secondary",
        source_url="https://example.org/public-record-notice-secondary",
        source_title="Public record notice secondary",
        source_domain="example.org",
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text="Secondary bounded excerpt.",
        page=2,
        section="Secondary totals",
        char_range_start=5,
        char_range_end=40,
        extraction_method="offline_fixture",
        worker_kind="bounded_reader",
        currentness="current_for_2026",
        observed_at="2026-06-22T00:00:00Z",
        metadata={"safe_note": "secondary"},
    )
    observation = SemanticObservation(
        observation_id=observation_id,
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        contract_version=accepted["accepted_contract_version"],
        contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_contract_digest=component_ref["component_digest"],
        evidence_refs=(EVIDENCE_ID,),
        content_refs=(content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value="secondary value",
        normalization_fit="secondary normalization",
        scope_fit="calendar year 2026 secondary",
        assumption_fit="secondary assumption",
        inference_depth=0,
        metadata={"safe_review_note": "secondary observation"},
    )
    return observation, content_ref


def test_content_ref_from_non_cited_admitted_observation_is_rejected() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    secondary_observation, secondary_content_ref = _secondary_observation(accepted)
    _admit(kernel, accepted, secondary_observation, secondary_content_ref)
    bad_trigger = AmendmentTriggerRefs(
        semantic_observation_refs=("observation:supports-reported-total",),
        evidence_refs=(EVIDENCE_ID,),
        sanitized_content_refs=("content:secondary-value",),
        component_coverage_refs=(COVERAGE_RECORD_ID,),
    )
    bad_record = _amendment_record(accepted, trigger_refs=bad_trigger)
    with pytest.raises(RunKernelTransitionError, match="is not cited"):
        _admit_amendment(kernel, accepted, bad_record)


def test_candidate_invalidated_coverage_ref_missing_coverage_record_id_is_rejected() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    missing_id = CoverageInvalidationCandidateRef(
        coverage_record_id="",
        coverage_record_digest=kernel.state.component_coverage_history[-1]["coverage_record_digest"],
        answer_component_id=COMPONENT_ID,
        reason="component revision or material slot changed",
    )
    material = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(missing_id,),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    material = replace(
        material,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    with pytest.raises(RunKernelTransitionError, match="requires coverage_record_id"):
        _admit_amendment(kernel, accepted, material)


def test_candidate_invalidated_coverage_ref_stale_digest_is_rejected() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    stale = CoverageInvalidationCandidateRef(
        coverage_record_id=COVERAGE_RECORD_ID,
        coverage_record_digest="0" * 64,
        answer_component_id=COMPONENT_ID,
        reason="component revision or material slot changed",
    )
    material = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(stale,),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    material = replace(
        material,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    with pytest.raises(RunKernelTransitionError, match="stale coverage digest"):
        _admit_amendment(kernel, accepted, material)


def test_affected_component_unknown_component_id_rejected_for_revise() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    revise = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
        operations=(
            AmendmentOperation(
                operation_id="operation:revise_component",
                operation_kind=AmendmentOperationKind.REVISE_COMPONENT,
                operation_payload={"component_change": "revise wording"},
                component_revision_changed=True,
                component_digest_changed=True,
            ),
        ),
        affected_component_refs=(
            AffectedComponentRef(
                component_id="component:unknown",
                component_revision="1",
                component_digest="d" * 64,
            ),
        ),
    )
    revise = replace(
        revise,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    with pytest.raises(RunKernelTransitionError, match="is not in accepted contract"):
        _admit_amendment(kernel, accepted, revise)


def test_affected_component_wrong_revision_digest_rejected_without_change_flags() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    component_ref = accepted["accepted_answer_component_refs"][0]
    revise = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
        operations=(
            AmendmentOperation(
                operation_id="operation:revise_component",
                operation_kind=AmendmentOperationKind.REVISE_COMPONENT,
                operation_payload={"component_change": "revise wording"},
            ),
        ),
        affected_component_refs=(
            AffectedComponentRef(
                component_id=component_ref["component_id"],
                component_revision="99",
                component_digest="f" * 64,
            ),
        ),
    )
    revise = replace(
        revise,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    with pytest.raises(
        RunKernelTransitionError,
        match="revision does not match|digest does not match",
    ):
        _admit_amendment(kernel, accepted, revise)


def test_add_component_new_id_allowed_without_contract_mutation() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    new_component_id = "component:new-reporting-slot"
    add_component = _amendment_record(
        accepted,
        materiality=MaterialityPosture.MATERIAL,
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
        operations=(
            AmendmentOperation(
                operation_id="operation:add_component",
                operation_kind=AmendmentOperationKind.ADD_COMPONENT,
                operation_payload={"component_id": new_component_id},
            ),
        ),
        affected_component_refs=(
            AffectedComponentRef(
                component_id=new_component_id,
                component_revision="1",
                component_digest="a" * 64,
            ),
        ),
    )
    add_component = replace(
        add_component,
        user_confirmation_posture=UserConfirmationPosture.EXPLICIT_USER_CONFIRMATION,
    )
    contract_before = json.dumps(kernel.state.initial_answer_contract, sort_keys=True)
    _admit_amendment(kernel, accepted, add_component)
    assert json.dumps(kernel.state.initial_answer_contract, sort_keys=True) == contract_before
    assert kernel.state.contract_amendment_admission_state["amendment_record_id"] == AMENDMENT_RECORD_ID


def test_static_guard_keeps_live_and_authority_surfaces_closed() -> None:
    runtime_source = RUNTIME_MODULE.read_text(encoding="utf-8")
    kernel_source = RUN_KERNEL.read_text(encoding="utf-8")
    tree = ast.parse(runtime_source)
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.final_answer_runtime_adapter",
        "core.final_answer_packet_runtime",
        "core.followup_sufficiency_recheck_runtime",
        "core.search_judgment",
        "core.sufficiency_judgment",
    }
    forbidden_called_names = {
        "run_pipeline",
        "authorize_search",
        "execute_author",
        "search_web",
        "retrieve",
        "apply_contract_amendment",
        "invalidate_coverage",
    }
    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(forbidden_called_names)
    assert "CONTRACT_AMENDMENT_ADMIT" in kernel_source
    assert "build_contract_amendment_admission_state" in kernel_source
    assert "requests." not in runtime_source
    assert "openai" not in runtime_source
    assert "brave_reconnaissance" not in runtime_source
    assert ".env" not in runtime_source
