from __future__ import annotations

import ast
import json
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
from core.sufficiency_semantic_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_CONSUMPTION_SCHEMA_VERSION,
    SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "sufficiency_semantic_consumption_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-09-offline"
REQUEST_ID = "request:sem-09"
COMPONENT_ID = "component:reported-total"
EVIDENCE_ID = "evidence:public-record-notice"
COVERAGE_RECORD_ID = "coverage:reported-total"
SEMANTIC_CONSUMPTION_ID = "semantic-consumption:reported-total"


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
        request_digest="request-digest-sem-09",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-09-test",
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
        source_digest="source-digest-sem-09",
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
    stale: bool = False,
    coverage_state: CoverageState = CoverageState.SATISFIED,
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
        request_digest="request-digest-sem-09",
        accepted_contract_version=accepted["accepted_contract_version"],
        accepted_contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(kernel),
        coverage_state=coverage_state,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.NOT_APPLICABLE,
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
        stale=stale,
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


def _start_kernel_with_coverage(
    *,
    stale: bool = False,
    coverage_state: CoverageState = CoverageState.SATISFIED,
) -> tuple[RunKernel, dict[str, object], ComponentCoverageRecord]:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    _admit(kernel, accepted, observation, content_ref)
    resolved_state = CoverageState.STALE if stale else coverage_state
    record = _coverage_record(
        accepted,
        observation,
        content_ref,
        kernel,
        stale=stale,
        coverage_state=resolved_state,
    )
    _reduce_coverage(kernel, accepted, record)
    return kernel, accepted, record


def _consume(
    kernel: RunKernel,
    *,
    semantic_consumption_id: str = SEMANTIC_CONSUMPTION_ID,
    payload: dict[str, object] | None = None,
) -> None:
    action = kernel.authorize_sufficiency_semantic_consumption(
        semantic_consumption_id=semantic_consumption_id,
    )
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.SUFFICIENCY_SEMANTIC_CONSUMED,
        status=RunStageStatus.COMPLETED,
        payload=payload or {"consumption_scope": "canonical_semantic_stack"},
    )
    kernel.reduce(reduce_observation)


def test_authorized_consumption_creates_canonical_state_projection_history() -> None:
    kernel, accepted, record = _start_kernel_with_coverage()

    _consume(kernel)

    state = kernel.state.sufficiency_semantic_consumption_state
    projection = kernel.state.sufficiency_semantic_consumption_projection
    assert state["schema_version"] == SUFFICIENCY_SEMANTIC_CONSUMPTION_SCHEMA_VERSION
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["semantic_consumption_id"] == SEMANTIC_CONSUMPTION_ID
    assert state["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert state["semantic_consumption_digest"]
    assert state["consumption_posture"] == "semantic_stack_bound"
    assert state["recommended_next_step"] == "sufficiency_judgment_input_assembly"
    assert state["consumed_coverage_refs"][0]["coverage_record_id"] == record.record_id
    assert state["consumed_coverage_refs"][0]["coverage_record_digest"] == record.record_digest
    assert state["component_coverage_summary"]["satisfied"] == 1
    assert state["initial_answer_contract_mutated"] is False
    assert state["coverage_marked_stale"] is False
    assert state["amendment_applied"] is False
    assert state["sufficiency_decided"] is False
    assert state["lineage"]["created_by"] == "RunKernel.SufficiencySemanticConsumption"
    assert kernel.state.sufficiency_semantic_consumption_history[-1] == projection
    assert kernel.state.projections[SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE] == projection
    assert kernel.state.stage_statuses[SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE] is RunStageStatus.COMPLETED


def test_consumption_requires_accepted_initial_answer_contract() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    with pytest.raises(RunKernelTransitionError, match="accepted initial answer contract"):
        kernel.authorize_sufficiency_semantic_consumption(
            semantic_consumption_id=SEMANTIC_CONSUMPTION_ID,
        )


def test_consumption_requires_admitted_semantic_observation() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    _accept_contract(kernel)
    with pytest.raises(RunKernelTransitionError, match="at least one admitted"):
        kernel.authorize_sufficiency_semantic_consumption(
            semantic_consumption_id=SEMANTIC_CONSUMPTION_ID,
        )


def test_consumption_requires_reduced_component_coverage() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    _admit(kernel, accepted, observation, content_ref)
    with pytest.raises(RunKernelTransitionError, match="at least one reduced"):
        kernel.authorize_sufficiency_semantic_consumption(
            semantic_consumption_id=SEMANTIC_CONSUMPTION_ID,
        )


def test_duplicate_semantic_consumption_id_is_rejected() -> None:
    kernel, _accepted, _record = _start_kernel_with_coverage()
    _consume(kernel)
    with pytest.raises(RunKernelTransitionError, match="already recorded"):
        _consume(kernel)


def test_stale_coverage_is_consumed_without_marking_stale_or_mutating_history() -> None:
    kernel, accepted, record = _start_kernel_with_coverage(stale=True)
    coverage_before = json.dumps(kernel.state.component_coverage_history, sort_keys=True)
    contract_before = json.dumps(kernel.state.initial_answer_contract, sort_keys=True)

    _consume(kernel)

    assert json.dumps(kernel.state.component_coverage_history, sort_keys=True) == coverage_before
    assert json.dumps(kernel.state.initial_answer_contract, sort_keys=True) == contract_before
    state = kernel.state.sufficiency_semantic_consumption_state
    assert state["component_coverage_summary"]["stale_present"] is True
    assert state["consumed_coverage_refs"][0]["stale"] is True
    assert state["consumed_coverage_refs"][0]["coverage_state"] == "stale"
    assert state["consumed_coverage_refs"][0]["coverage_marked_stale"] is False
    assert state["coverage_marked_stale"] is False
    assert kernel.state.component_coverage_history[-1]["stale"] is True


def test_payload_with_forbidden_authority_field_is_rejected() -> None:
    kernel, _accepted, _record = _start_kernel_with_coverage()
    with pytest.raises(RunKernelTransitionError, match="forbidden authority field"):
        _consume(
            kernel,
            payload={"sufficiency_judgment": {"decision": "ready_direct"}},
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
        "core.run_authority_sufficiency_runtime",
        "core.search_judgment",
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
    assert "SUFFICIENCY_SEMANTIC_CONSUME" in kernel_source
    assert "build_sufficiency_semantic_consumption_state" in kernel_source
    assert "requests." not in runtime_source
    assert "openai" not in runtime_source
    assert "brave_reconnaissance" not in runtime_source
    assert ".env" not in runtime_source
