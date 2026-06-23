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
from core.component_coverage_reduction_runtime import (
    COMPONENT_COVERAGE_REDUCTION_SCHEMA_VERSION,
    COMPONENT_COVERAGE_REDUCTION_STAGE,
    ComponentCoverageReductionError,
    build_component_coverage_reduction_projection,
    build_component_coverage_reduction_state,
    evidence_ledger_projection_digest,
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
RUNTIME_MODULE = ROOT / "core" / "component_coverage_reduction_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-07-offline"
REQUEST_ID = "request:sem-07"
COMPONENT_ID = "component:reported-total"
EVIDENCE_ID = "evidence:public-record-notice"
COVERAGE_RECORD_ID = "coverage:reported-total"


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
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        materiality=Materiality.MATERIAL,
    )


def _qmr() -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:reported-total",
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-07",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-07-test",
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
    kernel.state.evidence_ledger.reduce_observation(
        {
            "observation_id": f"evidence-seed:{candidate_id}",
            "observation_source": "offline_fixture",
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "url": "https://example.org/public-record-notice",
                    "title": "Public record notice",
                    "source_class": "primary",
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
        source_digest="source-digest-sem-07",
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


def _start_admitted_kernel() -> tuple[RunKernel, dict[str, object], SemanticObservation, SanitizedContentReference]:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    _admit(kernel, accepted, observation, content_ref)
    return kernel, accepted, observation, content_ref


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
        source_requirement_ids=(),
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _coverage_record(
    accepted: dict[str, object],
    observation: SemanticObservation,
    content_ref: SanitizedContentReference,
    kernel: RunKernel,
    *,
    coverage_state: CoverageState = CoverageState.SATISFIED,
    semantic_support_status: SemanticSupportStatus = SemanticSupportStatus.SUPPORTED,
    source_obligation_status: SourceObligationStatus = SourceObligationStatus.NOT_APPLICABLE,
    content_availability_status: ContentAvailabilityStatus = ContentAvailabilityStatus.AVAILABLE,
    evidence_custody_status: EvidenceCustodyStatus = EvidenceCustodyStatus.CUSTODIED,
    evidence_basis: tuple[EvidenceBasis, ...] | None = None,
    observation_refs: tuple[SemanticObservationCoverageRef, ...] | None = None,
    content_bindings: tuple[ContentReferenceCoverageBinding, ...] | None = None,
    remaining_unknowns: tuple[str, ...] = (),
    required_caveats: tuple[str, ...] = ("Currentness remains evidence-bound.",),
    followup_need: FollowupNeed = FollowupNeed.NONE,
    mode_budget_posture: ModeBudgetPosture = ModeBudgetPosture.AVAILABLE,
    conflict_posture: ConflictPosture = ConflictPosture.NONE,
    currentness_posture: CurrentnessPosture = CurrentnessPosture.CURRENT,
    stale: bool = False,
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
        request_digest="request-digest-sem-07",
        accepted_contract_version=accepted["accepted_contract_version"],
        accepted_contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(kernel),
        coverage_state=coverage_state,
        semantic_support_status=semantic_support_status,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=source_obligation_status,
        content_availability_status=content_availability_status,
        evidence_custody_status=evidence_custody_status,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=observation_refs if observation_refs is not None else (obs_ref,),
        content_reference_bindings=content_bindings if content_bindings is not None else (content_binding,),
        evidence_basis=evidence_basis
        if evidence_basis is not None
        else (
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        conflict_posture=conflict_posture,
        currentness_posture=currentness_posture,
        remaining_unknowns=remaining_unknowns,
        required_caveats=required_caveats,
        prohibited_upgrades=("Do not replace official value with estimate.",),
        followup_need=followup_need,
        mode_budget_posture=mode_budget_posture,
        stale=stale,
        metadata={"safe_note": "kept", "raw_prompt": "SENTINEL_RAW_PROMPT"},
    )


def _reseal_coverage(record: ComponentCoverageRecord) -> dict[str, object]:
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    return payload


def _reduce(
    kernel: RunKernel,
    accepted: dict[str, object],
    record: ComponentCoverageRecord,
    *,
    coverage_record_id: str | None = None,
    coverage_record_digest: str | None = None,
    component_revision: str | None = None,
    component_digest: str | None = None,
    payload: dict[str, object] | None = None,
) -> Observation:
    component_ref = accepted["accepted_answer_component_refs"][0]
    action = kernel.authorize_component_coverage_reduction(
        coverage_record_id=coverage_record_id if coverage_record_id is not None else record.record_id,
        coverage_record_digest=(
            coverage_record_digest if coverage_record_digest is not None else record.record_digest
        ),
        answer_component_id=component_ref["component_id"],
        component_revision=component_revision or component_ref["component_revision"],
        component_digest=component_digest or component_ref["component_digest"],
    )
    if payload is None:
        payload = {"component_coverage_record": _reseal_coverage(record)}
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    kernel.reduce(reduce_observation)
    return reduce_observation


def test_authorized_reduction_creates_canonical_state_projection_history() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)

    _reduce(kernel, accepted, record)

    state = kernel.state.component_coverage_state
    projection = kernel.state.component_coverage_projection
    assert state["schema_version"] == COMPONENT_COVERAGE_REDUCTION_SCHEMA_VERSION
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"]
    assert state["coverage_record_id"] == COVERAGE_RECORD_ID
    assert state["coverage_record_digest"] == record.record_digest
    assert state["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert state["coverage_state"] == "satisfied"
    assert state["coverage_reduction_digest"]
    assert state["lineage"]["created_by"] == "RunKernel.ComponentCoverageReduction"
    assert state["lineage"]["reducer_action_id"] == state["authorized_action_id"]
    assert kernel.state.component_coverage_history[-1] == projection
    assert kernel.state.projections[COMPONENT_COVERAGE_REDUCTION_STAGE] == projection
    assert kernel.state.stage_statuses[COMPONENT_COVERAGE_REDUCTION_STAGE] is RunStageStatus.COMPLETED


def test_reduction_requires_accepted_initial_answer_contract() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    with pytest.raises(RunKernelTransitionError, match="accepted initial answer contract"):
        kernel.authorize_component_coverage_reduction(
            coverage_record_id=COVERAGE_RECORD_ID,
            coverage_record_digest="d" * 64,
            answer_component_id=COMPONENT_ID,
            component_revision="1",
            component_digest="c" * 64,
        )


def test_reduction_requires_admitted_semantic_observation_for_component() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    observation = _observation(accepted)
    content_ref = _content_ref(accepted)
    record = _coverage_record(accepted, observation, content_ref, kernel)
    with pytest.raises(RunKernelTransitionError, match="at least one admitted"):
        kernel.authorize_component_coverage_reduction(
            coverage_record_id=record.record_id,
            coverage_record_digest=record.record_digest,
            answer_component_id=COMPONENT_ID,
            component_revision="1",
            component_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        )


def test_action_binding_for_record_id_digest_contract_component_is_exact() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    with pytest.raises(RunKernelTransitionError, match="coverage_record_id binding"):
        _reduce(kernel, accepted, record, coverage_record_id="coverage:not-this")

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    with pytest.raises(RunKernelTransitionError, match="coverage_record_digest binding"):
        _reduce(kernel, accepted, record, coverage_record_digest="0" * 64)


def test_coverage_record_foreign_run_id_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    foreign = replace(record, run_id="run:foreign")
    payload = _reseal_coverage(foreign)
    with pytest.raises(RunKernelTransitionError, match="run_id does not match"):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": payload})


def test_coverage_record_foreign_request_id_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    foreign = replace(record, request_id="request:foreign")
    payload = _reseal_coverage(foreign)
    with pytest.raises(RunKernelTransitionError, match="request_id does not match"):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": payload})


def test_coverage_record_matching_run_and_request_reduces_successfully() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    assert record.run_id == RUN_ID
    assert record.request_id == REQUEST_ID
    _reduce(kernel, accepted, record)
    state = kernel.state.component_coverage_state
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID


def test_recomputed_coverage_record_digest_rejects_tampered_payload() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    tampered = _reseal_coverage(record)
    tampered["required_caveats"] = ["Tampered caveat."]
    with pytest.raises(RunKernelTransitionError, match="coverage record digest does not match"):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": tampered})


def test_contract_version_or_digest_mismatch_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    payload = record.to_dict(include_validation=False)
    payload["accepted_contract_digest"] = "f" * 64
    with pytest.raises(
        RunKernelTransitionError,
        match="accepted_contract_digest|coverage record digest",
    ):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": payload})

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    payload = record.to_dict(include_validation=False)
    payload["accepted_contract_version"] = "9.9-other"
    with pytest.raises(
        RunKernelTransitionError,
        match="accepted_contract_version|coverage record digest",
    ):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": payload})


def test_component_id_revision_digest_mismatch_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    with pytest.raises(RunKernelTransitionError, match="component_revision"):
        _reduce(kernel, accepted, record, component_revision="99")

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    with pytest.raises(RunKernelTransitionError, match="component_digest"):
        _reduce(kernel, accepted, record, component_digest="e" * 64)


def test_unadmitted_observation_ref_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    foreign_ref = SemanticObservationCoverageRef(
        observation_id="observation:not-admitted",
        observation_digest="a" * 64,
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        support_status="supports",
        support_posture=SupportPosture.DIRECT,
        content_refs=("content:reported-total-value",),
        accepted=True,
    )
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        observation_refs=(foreign_ref,),
    )
    with pytest.raises(RunKernelTransitionError, match="is not admitted"):
        _reduce(kernel, accepted, record)


def test_stale_observation_digest_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    stale_ref = SemanticObservationCoverageRef(
        observation_id=observation.observation_id,
        observation_digest="0" * 64,
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        support_status="supports",
        support_posture=SupportPosture.DIRECT,
        content_refs=("content:reported-total-value",),
        accepted=True,
    )
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        observation_refs=(stale_ref,),
    )
    with pytest.raises(RunKernelTransitionError, match="stale observation digest"):
        _reduce(kernel, accepted, record)


def test_content_reference_binding_without_admitted_content_ref_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    obs_ref = SemanticObservationCoverageRef(
        observation_id=observation.observation_id,
        observation_digest=observation.observation_digest,
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        support_status="supports",
        support_posture=SupportPosture.DIRECT,
        content_refs=("content:foreign-ref",),
        accepted=True,
    )
    foreign_binding = ContentReferenceCoverageBinding(
        content_ref_id="content:foreign-ref",
        content_digest="b" * 64,
        evidence_ref_id=EVIDENCE_ID,
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
    )
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        observation_refs=(obs_ref,),
        content_bindings=(foreign_binding,),
    )
    with pytest.raises(RunKernelTransitionError, match="unadmitted content ref"):
        _reduce(kernel, accepted, record)


def test_content_digest_evidence_ref_component_mismatch_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    bad_binding = ContentReferenceCoverageBinding.from_content_reference(content_ref)
    bad_binding = ContentReferenceCoverageBinding(
        content_ref_id=bad_binding.content_ref_id,
        content_digest="0" * 64,
        evidence_ref_id=bad_binding.evidence_ref_id,
        answer_component_id=bad_binding.answer_component_id,
        component_revision=bad_binding.component_revision,
        component_contract_digest=bad_binding.component_contract_digest,
        answer_bearing=True,
        availability_status=ContentAvailabilityStatus.AVAILABLE,
    )
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        content_bindings=(bad_binding,),
    )
    with pytest.raises(RunKernelTransitionError, match="content digest does not match admitted content"):
        _reduce(kernel, accepted, record)

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    bad_binding = ContentReferenceCoverageBinding(
        content_ref_id=content_ref.content_ref_id,
        content_digest=content_ref.content_digest,
        evidence_ref_id="evidence:foreign",
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        answer_bearing=True,
        availability_status=ContentAvailabilityStatus.AVAILABLE,
    )
    record = _coverage_record(accepted, observation, content_ref, kernel, content_bindings=(bad_binding,))
    with pytest.raises(RunKernelTransitionError, match="absent from EvidenceLedger custody"):
        _reduce(kernel, accepted, record)


def test_satisfied_coverage_based_only_on_non_semantic_basis_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        evidence_basis=(EvidenceBasis.CANDIDATE_DISCOVERY, EvidenceBasis.IDS_OR_DIGESTS_ONLY),
    )
    with pytest.raises(RunKernelTransitionError, match="cannot be based solely"):
        _reduce(kernel, accepted, record)


def test_satisfied_coverage_without_answer_bearing_available_content_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    bad_binding = ContentReferenceCoverageBinding(
        content_ref_id=content_ref.content_ref_id,
        content_digest=content_ref.content_digest,
        evidence_ref_id=EVIDENCE_ID,
        answer_component_id=COMPONENT_ID,
        component_revision="1",
        component_contract_digest=accepted["accepted_answer_component_refs"][0]["component_digest"],
        answer_bearing=False,
        availability_status=ContentAvailabilityStatus.MISSING,
    )
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        content_bindings=(bad_binding,),
        content_availability_status=ContentAvailabilityStatus.MISSING,
    )
    with pytest.raises(RunKernelTransitionError, match="answer-bearing"):
        _reduce(kernel, accepted, record)


def test_satisfied_coverage_without_evidence_ledger_custody_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        evidence_custody_status=EvidenceCustodyStatus.UNBOUND,
    )
    with pytest.raises(RunKernelTransitionError, match="EvidenceLedger custody"):
        _reduce(kernel, accepted, record)


def test_conflicted_or_followup_required_coverage_cannot_present_as_satisfied() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        coverage_state=CoverageState.SATISFIED,
        conflict_posture=ConflictPosture.PRESENT,
        remaining_unknowns=("scope boundary",),
        followup_need=FollowupNeed.REQUIRED,
    )
    with pytest.raises(RunKernelTransitionError, match="unresolved conflict|remaining unknowns|follow-up"):
        _reduce(kernel, accepted, record)


def test_duplicate_coverage_record_id_or_digest_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    _reduce(kernel, accepted, record)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        _reduce(kernel, accepted, record)


def test_non_satisfied_coverage_preserves_caveats_and_unknowns() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        coverage_state=CoverageState.PARTIAL,
        semantic_support_status=SemanticSupportStatus.PARTIAL,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.PARTIAL,
        evidence_custody_status=EvidenceCustodyStatus.PARTIAL,
        evidence_basis=(EvidenceBasis.SEMANTIC_OBSERVATION,),
        remaining_unknowns=("official notice wording",),
        required_caveats=("Partial support only.",),
        followup_need=FollowupNeed.OPTIONAL,
    )
    _reduce(kernel, accepted, record)
    state = kernel.state.component_coverage_state
    assert state["coverage_state"] == "partial"
    assert state["remaining_unknowns"] == ["official notice wording"]
    assert state["required_caveats"] == ["Partial support only."]
    assert state["followup_need"] == "optional"
    assert state["followup_authorized"] is False


def test_no_amendment_sufficiency_packet_author_search_followup_state() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    _reduce(kernel, accepted, record)

    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_judgment == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_authorization_state == {}

    projection = kernel.state.component_coverage_projection
    for flag in (
        "amendment_created",
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


def test_projection_and_coverage_reduction_digest_are_deterministic() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    inputs = {
        "coverage_record_id": record.record_id,
        "coverage_record_digest": record.record_digest,
        "accepted_contract_digest": accepted["accepted_contract_digest"],
        "accepted_contract_version": accepted["accepted_contract_version"],
        "answer_component_id": COMPONENT_ID,
        "component_revision": "1",
        "component_digest": accepted["accepted_answer_component_refs"][0]["component_digest"],
        "request_id": REQUEST_ID,
    }
    payload = {"component_coverage_record": _reseal_coverage(record)}
    state_one = build_component_coverage_reduction_state(
        action_id="action:sem-07-deterministic",
        action_inputs=inputs,
        coverage_payload=payload,
        accepted_contract=accepted,
        admission_history=kernel.state.semantic_observation_admission_history,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    state_two = build_component_coverage_reduction_state(
        action_id="action:sem-07-deterministic",
        action_inputs=inputs,
        coverage_payload=payload,
        accepted_contract=accepted,
        admission_history=kernel.state.semantic_observation_admission_history,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    projection_one = build_component_coverage_reduction_projection(coverage_state=state_one)
    projection_two = build_component_coverage_reduction_projection(coverage_state=state_two)
    assert state_one["coverage_reduction_digest"] == state_two["coverage_reduction_digest"]
    assert json.dumps(projection_one, sort_keys=True) == json.dumps(projection_two, sort_keys=True)


def test_sensitive_fields_are_scrubbed_and_closed_authority_is_rejected() -> None:
    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    _reduce(kernel, accepted, record)
    projection = kernel.state.component_coverage_projection
    assert "raw_prompt" not in json.dumps(projection)

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    payload = {"component_coverage_record": _reseal_coverage(record), "sufficiency_judgment": {"x": 1}}
    with pytest.raises(RunKernelTransitionError, match="closed authority fields"):
        _reduce(kernel, accepted, record, payload=payload)

    kernel, accepted, observation, content_ref = _start_admitted_kernel()
    record = _coverage_record(accepted, observation, content_ref, kernel)
    tampered = _reseal_coverage(record)
    tampered["passive"] = False
    with pytest.raises(RunKernelTransitionError, match="must remain passive"):
        _reduce(kernel, accepted, record, payload={"component_coverage_record": tampered})


def test_builder_requires_accepted_contract() -> None:
    with pytest.raises(ComponentCoverageReductionError, match="accepted initial answer contract"):
        build_component_coverage_reduction_state(
            action_id="action:sem-07",
            action_inputs={},
            coverage_payload={"component_coverage_record": {"record_id": "x"}},
            accepted_contract={},
            admission_history=[],
            evidence_ledger_projection={},
            run_id=RUN_ID,
            request_id=REQUEST_ID,
        )


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
        "reduce_coverage",
    }
    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(forbidden_called_names)
    assert "COMPONENT_COVERAGE_REDUCE" in kernel_source
    assert "build_component_coverage_reduction_state" in kernel_source
    assert "requests." not in runtime_source
    assert "openai" not in runtime_source
    assert "brave_reconnaissance" not in runtime_source
    assert ".env" not in runtime_source
